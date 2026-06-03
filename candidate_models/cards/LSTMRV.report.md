# LSTMRV — Modeling Report

**Model number:** 10 · **Class:** `candidate_models.lstm_rv:LSTMRV` · **Tier:** DL

## Overview

LSTMRV is a recurrent neural network — a Long Short-Term Memory (LSTM) net — read
over a trailing 60-day window of realized-volatility and macro-covariate features.
It is the deep-learning-tier entry in the candidate set: a nonlinear,
sequence-aware, macro-covariate-aware alternative to the linear HAR family. Rather
than regressing log realized variance on a handful of hand-built HAR lags, it lets
the network learn its own representation of the recent volatility path and the
implied-volatility term structure, and emit a forecast of `log(target_var)` for
every horizon at once from a per-horizon linear head.

## Modeling approach & rationale

The model fits one shared multi-head LSTM per ticker. Each network consumes a
60-day window of eight features — the path of realized volatility plus the
implied-vol "macro covariates" (VIX level/slope, IV level/slope, skew) and signed
semivariance — and predicts `log(target_var)` jointly across the horizons
{1, 5, 10, 22, 42} through one linear head per horizon. Predictions are
back-transformed to `target_var` units with the lognormal-mean correction
`rv_hat = exp(mu + 0.5*sigma^2)` (matching the QLIKE-optimal mean forecast used by
the benchmarks rather than the median), and dressed with lognormal quantiles via
`_lognormal_quantiles`, keeping the interval construction comparable across the
candidate set.

Why posit that a deep recurrent model with macro covariates can beat HAR: the HAR
family (Corsi 2009; Patton & Sheppard 2015 for the semivariance/jump extension) is
*linear* in log-RV over fixed daily/weekly/monthly aggregates. It cannot represent
interactions or regime dependence — for example, that the predictive weight on
recent realized variance should shift when the VIX term structure inverts, or that
the implied-vol surface carries forward-looking information the realized path does
not. An LSTM over a window of RV *plus* implied-vol covariates can in principle
learn those nonlinear, state-dependent dynamics directly from the sequence. This is
the thesis of the recent 2024–2025 horse-race literature: TiDE/DeepAR-style models
augmented with macro covariates have been reported to beat HAR (MDPI 2025), and
Moreno-Pino & Zohren (2024) show a dilated causal CNN improving on HAR for RV.

That said, the evidence is genuinely mixed and the report should be candid about it:
the "HARd to Beat" study (arXiv 2406.08041) finds that across many assets and
horizons the plain HAR is a stubbornly strong baseline that sophisticated deep
models frequently fail to beat out-of-sample once estimation noise and overfitting
are accounted for. LSTMRV is therefore best read as a fair, like-for-like test of
whether a recurrent net on a macro-covariate window buys anything over HAR — not as
a model expected a priori to dominate.

## Features & inputs

The 60-day window stacks eight features per day (all confirmed present in
`rv_eval/features.build_features`; any non-finite row is dropped from the kept
forecasts):

- **Realized-vol path (1):** `log_rv_d` — the daily realized variance in log space,
  the sequence the LSTM tracks; its recent trajectory is the core HAR signal.
- **Implied-vol term structure (4):** `log_iv` (option-implied vol level),
  `iv_slope` (IV term-structure slope), `vix` (index-level implied vol), and
  `vix_slope` (VIX term-structure slope). These are the forward-looking "macro
  covariates" — the market's own variance forecast and its term structure — that DL
  is posited to exploit beyond the realized path.
- **Skew (1):** `skew_25d` — the 25-delta implied skew, carrying information about
  downside/tail risk priced into options.
- **Signed semivariance (2):** `rs_minus_5d` and `rs_plus_5d` — the downside and
  upside realized semivariance over 5 days, letting the net distinguish
  bad-volatility from good-volatility regimes (the Patton-Sheppard intuition).

Target: `log(target_var)` — the log of the sum of the next-`h` daily realized
variances.

## Design & implementation

- **Architecture.** `LSTM(input=8, hidden=64, num_layers=1, dropout=0.1,
  batch_first=True)` → dropout on the last time-step hidden state → one
  `nn.Linear(64, 1)` head per horizon, concatenated to a `(batch, 5)` output of
  `log(target_var)` predictions. With `num_layers=1` the inter-layer LSTM dropout is
  inert (it applies only between stacked layers); the explicit `nn.Dropout(0.1)` on
  the pooled hidden state still regularizes.
- **One shared multi-head net per ticker.** State is keyed by `(ticker, horizon)` to
  preserve the `_PerKeyModel` contract, but every horizon for a ticker points at the
  same network with its own head index — so the network is fit once per ticker and
  shares representation across horizons.
- **Device.** MPS if available else CPU (MODEL_PLAN §3); both the network and all
  tensors are moved to the device. This run used **MPS** (Apple Silicon).
- **Standardization.** Per ticker, computed on the fit slice only: each feature is
  centered/scaled by its fit-slice mean/std (std floored at 1e-8) before windowing.
  The same `(mu, sd)` is reused at predict time — no OOS statistic leaks in.
- **Early stopping & sigma.** Training is masked MSE on the log target with Adam
  (lr 5e-4, batch 64). The last 10% (time-ordered) of the windowed training samples
  is held out as a within-train tail; training early-stops on its masked MSE
  (patience 8, cap 80 epochs), and the per-horizon `sigma` is the residual std of
  `log(target_var)` on that tail (floored at 1e-3). The tail is strictly within-train
  — never the OOS window — so it is leakage-safe.
- **Quantiles.** `sigma` feeds both the lognormal-mean back-transform and
  `_lognormal_quantiles(m, s)`, producing q05…q95 consistently with the benchmarks.
- **`min_obs = 120`**; a ticker with too few windowed samples (< 20 windows or < 5
  training windows) is simply skipped rather than fit on noise.

**The key implementation lesson — the predict-window-context bug and fix.** The
first full walk-forward produced **zero** predictions. The cause: the walk-forward
harness passes `predict()` only the current test-month slice (~21 rows per ticker),
but the model needs a full 60-day window to make any forecast. With only ~21 rows,
every fold had `n < WINDOW` and emitted nothing — a silent, total failure. The fix
caches, during `fit()`, the last `WINDOW-1 = 59` **raw** feature rows per ticker
(stored pre-standardization in `self._ctx`); at `predict()` time these are
prepended to the test slice so each test date has its full 60-day backward-looking
window. This is leakage-safe by construction: the cached rows are strictly *before*
the upcoming test block (they are the tail of the fit slice), the windows are
backward-only, and any test row whose own feature vector is non-finite is still
dropped (context is used only to form the window, never to impute a kept forecast).
A regression test (`candidate_models/tests/test_lstm_rv.py`) reproduces the
small-slice contract so this failure mode cannot silently return.

## Hyperparameters & selection

The structural hyperparameters were chosen by the **leakage-safe
tune-once-then-freeze protocol** (MODEL_PLAN §4 "Hyperparameter selection", models
8–11) and hard-coded in the model class.

**Frozen winner:** `hidden=64`, `num_layers=1`, `dropout=0.1`, `lr=5e-4`.

**Protocol** (from `candidate_models/_tune_lstm.py`, tuning run 2026-06-01):

- **Grid (24 points):** `hidden ∈ {32, 64, 128}` × `num_layers ∈ {1, 2}` ×
  `dropout ∈ {0.1, 0.2}` × `lr ∈ {5e-4, 1e-3}`. The grid's *initial point* (the
  plan's bold cell) is `(hidden=64, num_layers=2, dropout=0.1, lr=1e-3)` — a
  starting guess, not the answer.
- **Subset.** To bound DL compute, tuning ran only on `HPTUNE_DL_SUBSET` = (SPY,
  QQQ, TLT, XLE) — a representative cross-section. The frozen HPs are then applied
  globally to all tickers.
- **Split (pre-OOS only):** search-train = rows with `date < HPTUNE_VAL_START`
  (2016-01-01); validation = `[HPTUNE_VAL_START, OOS_START)` = **2016–2017**. The
  tuner asserts the validation block lies entirely within 2016–2017 and below the
  OOS start; **no `date ≥ 2018` (OOS) is read during tuning**, and even the
  validation context features stop strictly before 2018.
- **Procedure:** for each grid point, fit one LSTM per subset-ticker on search-train
  (windows ending strictly before 2016-01-01), early-stop on a within-search-train
  time-ordered 10% tail, predict h=22 over the validation block, and pool QLIKE@h22
  across the subset; keep the lowest.
- **Result:** the **winner `(64, 1, 0.1, 5e-4)` scored validation QLIKE@h22 =
  0.210004**, nearly halving the **initial point `(64, 2, 0.1, 1e-3)` at 0.412826**.
  The decisive factor was **depth: every 1-layer config clustered around ~0.21,
  while every 2-layer config scored 0.36–0.87** — a single LSTM layer clearly wins,
  consistent with the small per-ticker sample sizes not supporting a deeper recurrent
  stack.

Crucially, **2016–2017 was never an OOS test row.** Once the HPs were frozen, those
dates are reused only as *training* rows for the OOS walk-forward folds, which is
not leakage because no `date ≥ 2018` ever informed the hyperparameters. `epochs` is
not part of the grid; it is set per fit by early stopping (cap 80), itself
leakage-safe.

## Self-only results interpretation

All numbers below are this model's own OOS self-stats from `LSTMRV.md` (clean_core)
and `LSTMRV.hard_cases.md`. Self-contained — no ranking against other models.

**QLIKE across horizons (pooled).**

| horizon | QLIKE clean_core | QLIKE hard_cases |
|---|---|---|
| 1  | 0.337 | 0.450 |
| 5  | 0.214 | 0.324 |
| 10 | 0.231 | 0.314 |
| 22 | **0.372** | **0.338** |
| 42 | 0.500 | 0.360 |

The **headline QLIKE@h22 is 0.372 (clean_core) / 0.338 (hard_cases)**. The
horizon profile has the characteristic RV-forecasting shape: QLIKE is highest at
h=1 (0.337), bottoms in the mid-horizons (h=5 minimum at 0.214 on clean_core), and
rises again toward h=42 (0.500). `log_bias` is mildly negative throughout
(clean_core −0.333 at h=1 shrinking to −0.116 at h=22, with a small uptick to
−0.139 at h=42), i.e. a persistent mild low-bias rather than a long-horizon
collapse. Hard_cases QLIKE is flatter across horizons (0.31–0.45) with a less
negative long-horizon bias (−0.067 at h=42).

**§5 IV-incremental skill.** Read in isolation, the LSTM does **not** add
incremental skill over the IV-as-forecast benchmark at any horizon:
`qlike_gain_vs_iv` is **negative everywhere** (clean_core −0.009 at h=1, −0.006 at
h=5, −0.012 at h=10, −0.032 at h=22, −0.030 at h=42; hard_cases similar, −0.09 to
−0.04). The regression slope of the realized target on the model's incremental
signal is small and positive at short horizons (0.009 at h=1, 0.029 at h=5) but
turns *negative* at h=22/h=42 on clean_core (−0.034, −0.056, both significant). In
plain terms: on its own numbers, the model tracks implied vol but does not
out-forecast it — the network has not extracted skill beyond what the IV covariates
already encode. (On hard_cases the h=22/h=42 slopes are strongly positive — 0.12 /
0.38 — i.e. the signal co-moves with truth there, but the QLIKE gain is still
negative.)

**§6 conditional bias by IV bucket (h=22).** Bias rotates monotonically with the IV
regime. On clean_core `log_bias` moves from −0.198 in the lowest IV bucket to
−0.025 in the highest, with QLIKE rising from 0.196 (bucket 0) to a peak of 0.523
(bucket 2) then 0.429 (bucket 4). So the model under-forecasts most in calm regimes
and is closest to unbiased in high-IV regimes — and is hardest in the mid/high IV
buckets. Hard_cases shows the same rotation (−0.206 → +0.022) and is hardest in the
top bucket (QLIKE 0.474).

**§6 post-shock calibration (h=22).** Post-shock the bias stays mildly negative
(clean_core −0.116 → −0.057; hard_cases −0.089 → −0.061) and QLIKE rises modestly
(clean_core 0.372 → 0.426; hard_cases 0.338 → 0.390). **No post-shock trap flag
fired on either universe** — the model does not over-forecast and blow up
immediately after a vol spike; it stays mildly low-biased throughout, which is the
better failure mode.

**Interval coverage (h=22).** Coverage is reasonably calibrated on clean_core:
cov90 = 0.852 and cov50 = 0.502 (targets 0.90 / 0.50) — close at the 50% band and
slightly narrow at the 90% band. Coverage is best at short horizons (cov90 0.896 at
h=1) and degrades toward h=42 (cov90 0.815). Hard_cases h=22 is narrower (cov90 =
0.801, cov50 = 0.472) and degrades further on the thin names (see below).

**Strong vs weak tickers/horizons.** Strongest at the mid-horizons (h=5/h=10) and
on rates/precious-metals names — e.g. **GLD** (h=22 QLIKE 0.177, the best clean_core
key) and **TLT** (0.218). The large-cap tech/equity names are also solid (QQQ 0.330,
XLK 0.331). Weakest on **HYG** (h=22 QLIKE 0.902, the worst clean_core key, with
`log_bias` −0.350 and a 0.658 group QLIKE for high-yield credit). Among hard cases,
h=22 QLIKE is moderate (IBIT 0.166, USO 0.251, KRE 0.355, UVXY 0.371, MSOS 0.437),
but interval coverage on the thin/illiquid names is poor (IBIT cov90 0.630 / cov50
0.188; MSOS cov90 0.561 / cov50 0.289), and MSOS carries a positive h=22 `log_bias`
(+0.199, over-forecasting).

## Coverage & limitations

- **Full key coverage.** 142,495 OOS rows cover all 15 scored tickers × 5 horizons
  {1,5,10,22,42}, min date 2018-01-02; `rv_hat` finite & > 0, quantiles monotone. No
  per-ticker fit failures or NaN forecasts.
- **Thin hard cases.** **IBIT (1,225 rows total; 224 at h=22)** and **MSOS (6,010
  rows total; 1,181 at h=22)** have short IV-feature histories, so they have far
  fewer rows than the ~2,060-per-horizon clean_core names. Their interval coverage
  is poor (IBIT h=22 cov90 0.630 / cov50 0.188; MSOS cov90 0.561 / cov50 0.289) — the
  expected consequence of estimating `sigma` from a short held-out tail on a thin,
  noisy series. MSOS also over-forecasts at h=22 (log_bias +0.199).
- **No skill over raw IV in isolation.** Across all horizons `qlike_gain_vs_iv` is
  negative — on its own numbers the model does not beat the implied-vol benchmark.
  Whether the recurrent representation adds anything net of the linear HAR/IV
  baselines is a question for the comparison pass, not this card.
- **Compute / convergence.** Training is expensive on MPS (clean_core 10,999s ≈ 3.1h;
  hard_cases 2,999s ≈ 0.8h) because of 15 monthly refits × per-ticker fits. No
  convergence failures or non-finite outputs were observed; early stopping kept
  epoch counts well under the 80-cap. The one earlier failure mode — zero predictions
  from the predict-window-context bug — is now fixed and regression-tested (see
  Design & implementation).

## Reproduction

```bash
.venv/bin/python -m rv_eval.walkforward --model candidate_models.lstm_rv:LSTMRV --universe clean_core
.venv/bin/python -m rv_eval.walkforward --model candidate_models.lstm_rv:LSTMRV --universe hard_cases
.venv/bin/python -m rv_eval.selfstats --pred execution/data/predictions/LSTMRV.parquet \
    --out candidate_models/cards/LSTMRV.md --universe clean_core
.venv/bin/python -m rv_eval.selfstats --pred execution/data/predictions/LSTMRV.parquet \
    --out candidate_models/cards/LSTMRV.hard_cases.md --universe hard_cases

# Hyperparameter tuning (tune-once-then-freeze; standalone, not part of the harness):
.venv/bin/python -m candidate_models._tune_lstm
```
