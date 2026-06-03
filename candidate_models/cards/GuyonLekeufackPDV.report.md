# GuyonLekeufackPDV — Modeling Report

**Model number:** 11 · **Class:** `candidate_models.pdv_glek:GuyonLekeufackPDV` · **Tier:** PDV

## Overview

GuyonLekeufackPDV is the 4-factor Path-Dependent Volatility (PDV) model of
**Guyon & Lekeufack (2023)** "Volatility is (mostly) path-dependent" and
**Gazzani & Guyon (2024)**, fit per `(ticker, horizon)`. Its central idea is that
today's spot variance is, to a good approximation, an explicit and parsimonious
*function of the recent path of returns* — not a latent state evolving on its own,
but a deterministic readout of two path-features: a signed **trend** feature and a
**activity** (squared-return) feature, each built from a fast and a slow
exponential kernel. The model fits nine scalars by direct numerical optimization,
then produces multi-step horizon forecasts by Monte-Carlo bootstrapping the fitted
one-step residuals forward and summing the simulated daily variances. Where the
optimizer fails it falls back to a reduced fixed-kernel fit before dropping a key.

## Modeling approach & rationale

The model implements the parsimonious 4-factor PDV specification (MODEL_PLAN §4
model 11; §9 references Guyon & Lekeufack 2023 / Gazzani & Guyon 2024):

    sigma_t^2 = beta0 + beta1 * R1_t + beta2 * sqrt(R2_t)

with two path-features driving spot variance:

- **trend factor** `R1_t = (1-theta)  * EWMA_short(r)  + theta  * EWMA_long(r)`
- **activity factor** `R2_t = (1-theta') * EWMA_short'(r^2) + theta' * EWMA_long'(r^2)`

Here `r_s` is the daily close-to-close return (`ret_cc`, the plan's `ret_close`).
Each EWMA is an exponential kernel: a short half-life kernel captures the fast,
recent path and a long half-life kernel the slow, persistent path; `theta`/`theta'`
mix the two. `R1` is *signed* — it carries the asymmetric "trend": a run of
negative returns pushes `R1` negative and, through `beta1`, raises variance,
reproducing the leverage effect as a path functional. `R2` is built from squared
returns and is always non-negative, entering through its square root so that
`beta2 * sqrt(R2)` behaves like a recent realized volatility level. Each weighted
path-sum is maintained by the O(1) recursion `e_t = lambda * e_{t-1} + z_t`
(`lambda = exp(-ln2 / half_life)`), so there is no O(t^2) convolution.

Why path-dependence should forecast RV: Guyon & Lekeufack (2023) show empirically
that the bulk of spot-variance variation across equity indices is explained by
exactly these two path-features — a weighted average of past returns (trend) and a
weighted average of past squared returns (activity) — with the short-kernel terms
giving rapid response to recent shocks and the long-kernel terms giving the slow
mean-reverting "memory" that produces volatility clustering and long-range
persistence. Because variance is treated as a *deterministic function of the
observable return path* rather than a latent process, the one-step model is cheap
to fit, and the path-features supply both the volatility-clustering and the
leverage asymmetry that a HAR/GARCH would model separately. The Gazzani & Guyon
(2024) 4-factor form is the version operationalized here.

## Features & inputs

Two columns from the inputs panel:

- `ret_cc` — daily close-to-close return (the plan's `ret_close`); used as `r_s`,
  feeding the trend factor directly and the activity factor as `r_s^2`. Falls back
  to a `ret_close` column if `ret_cc` is absent.
- `rv_d` — daily realized variance (= `total_rv`); the fit target for the one-step
  objective and the empirical level the bootstrap residuals are formed against.

Returns are coerced to finite (NaN → 0); the realized variance is floored above
zero (`_EPS = 1e-12`) before any log. The two path-features `R1`, `R2` are *not*
pre-computed external features — they are built inside the model from `ret_cc` via
the EWMA-style kernel recursions, recomputed for each candidate parameter vector
during the optimization (the kernel half-lives are themselves free parameters, so
the EWMA decays change as the optimizer moves). No HAR lags or IV features are
used: this is a pure return + realized-variance path model.

## Design & implementation

- **Estimation.** Per `(ticker, horizon)` fit of the nine scalars
  `(beta0, beta1, beta2, theta, theta', lambda_s1, lambda_l1, lambda_s2, lambda_l2)`
  by `scipy.optimize.minimize`, method **L-BFGS-B**, `maxiter = 300`, with bounds
  `beta0 >= 0`, `beta1` free, `beta2 >= 0`, `theta, theta' in [0,1]`, and each
  lambda confined to the range implied by half-lives in `[1.5, 1000]` trading days.
  The objective is the **one-step log-MSE on daily RV**:
  `mean( (log(sigma_t^2 + eps) - log(rv_d_t + eps))^2 )`, with `sigma_t^2` floored
  at `eps = 1e-12` (necessary because the signed `beta1 * R1` term can drive the
  raw variance negative).
- **Forward simulation.** There is no closed form for the multi-step variance, so
  for horizon `h` the model **Monte-Carlo bootstraps ~500 paths**. One-step
  *multiplicative* residuals are formed on the variance scale,
  `e_t = rv_d_t / max(sigma_t^2, floor)` (mean ≈ 1), and each step: (1) computes the
  variance forecast `sigma^2` from the current per-path EWMA states `(R1, R2)`;
  (2) draws a bootstrapped residual to give a simulated daily realized variance
  `rv_sim = sigma^2 * e`, accumulated into the horizon sum; (3) advances the four
  EWMA states with a simulated return `r_sim = sqrt(rv_sim) * Rademacher(±1)` (the
  random sign carries the trend factor, `r_sim^2 = rv_sim` feeds the activity
  factor). Then `rv_hat = mean over paths of the horizon variance sum`, and
  `sigma = std over paths of log(horizon-variance sum)` — the log-std used to form
  the lognormal quantile band (`_lognormal_quantiles`), with `sigma` clipped to
  `[1e-3, 5.0]`.
- **Seeding.** `numpy.random.default_rng(0)` (seed 0), re-seeded per predict call,
  fixes the bootstrap draws for reproducibility. `_N_PATHS = 500` in the real
  walk-forward (the smoke test monkeypatches a smaller count). `min_obs = 100`.
- **Convergence / fallback policy.** Full 9-scalar L-BFGS-B fit → on optimizer
  failure or a non-finite/degenerate objective, a **fixed-kernel 5-scalar fallback**
  (freeze the four half-lives at their 8d/250d seeds and re-fit only
  `(beta0, beta1, beta2, theta, theta')`) → if that also fails the key is
  **dropped, never imputed** (no row emitted for it). The variant used per key is
  recorded on `self.warnings` at fit time.
- **Library versions.** scipy 1.17.1; numpy; polars. **Device:** cpu.

## Hyperparameters & selection

There is **no hyperparameter grid and no tune-once-then-freeze step** for this
model — the §4 selection table lists "none (9 scalars fit by `scipy.optimize`)"
for model 11. All nine scalars, including the four kernel half-lives, are fit by
the optimizer per `(ticker, horizon)`. The short ≈ 8-day and long ≈ 250-day
half-lives **only seed** the optimizer (and the fixed-kernel fallback freezes the
half-lives at exactly those seeds); they were not chosen against any validation
block. The only other fixed quantities are numerical safeguards / reproducibility
settings: the variance floor `eps = 1e-12`, the half-life bounds `[1.5, 1000]`
days, `maxiter = 300`, `_N_PATHS = 500`, the `sigma` clip `[1e-3, 5.0]`, the numpy
seed 0, and `min_obs = 100`. None of these were selected against OOS or validation
data.

## Self-only results interpretation

All numbers below are this model's own OOS self-stats, read from
`GuyonLekeufackPDV.md` (clean_core) and `GuyonLekeufackPDV.hard_cases.md`. They
describe the model in isolation — no ranking against other models.

**QLIKE across horizons (pooled).**

| horizon | QLIKE clean_core | QLIKE hard_cases |
|---|---|---|
| 1  | 0.819 | 0.658 |
| 5  | 1.405 | 0.571 |
| 10 | 1.453 | 0.524 |
| 22 | **1.700** | **0.485** |
| 42 | 1.584 | 0.457 |

The **headline QLIKE@h22 is 1.700 (clean_core) / 0.485 (hard_cases)**. The two
universes tell opposite horizon stories. On **clean_core**, QLIKE worsens with
horizon (0.82 → 1.70 at h=22, easing slightly to 1.58 at h=42), and `log_bias` is
persistently negative and growing more so (−0.44 at h=1 to −1.14 at h=42) — the
model under-forecasts the level, increasingly at long horizons. On **hard_cases**,
QLIKE actually *improves* monotonically with horizon (0.66 → 0.46) and the negative
bias narrows (−0.19 → −0.07); the high-volatility hard names are forecast more
reliably at longer horizons here. The clean_core pooled QLIKE is heavily inflated
by one ticker (see below); the per-ticker view is far more favorable than the pool.

**§5 IV-incremental skill (h=22).** The model adds **no** incremental skill over
the implied-volatility-as-forecast benchmark on either universe at h=22:
`qlike_gain_vs_iv = −1.374` (clean_core) / −0.221 (hard_cases). On clean_core the
regression slope of truth on the model forecast is essentially zero with t ≈ 0 at
every horizon, and sign-accuracy hovers near 0.46–0.51 — the long-horizon
clean_core forecasts carry little usable signal relative to IV. On **hard_cases**,
by contrast, the slope is positive and strongly significant and *grows* with
horizon (slope 0.54, t = 33.4 at h=22; slope 0.71, t = 50.2 at h=42), with
sign-accuracy 0.55–0.63 — so on the hard names the PDV forecast does track truth,
even though it still does not beat IV outright.

**§6 conditional bias by IV bucket (h=22).** On clean_core the negative `log_bias`
is largest in the *low*-IV buckets (−1.71 in bucket 0, rising toward −0.46 in the
top bucket), while QLIKE is worst in the highest-IV bucket (2.66 in bucket 4 vs
~1.3–1.6 elsewhere). On hard_cases the pattern is similar in shape but milder: bias
runs −0.48 (bucket 0) → +0.42 (bucket 4) and QLIKE is well-behaved (0.25–0.35)
until the top IV bucket, where it rises to 1.17. The model tends to under-forecast
in calm regimes and is least accurate in the most stressed (high-IV) regime.

**§6 post-shock calibration (h=22).** Post-shock, the negative bias *narrows*
(clean_core −1.09 → −0.54; hard_cases flips from −0.12 to +0.34) while QLIKE rises
(clean_core 1.70 → 2.83 over n=3986 post-shock points; hard_cases 0.48 → 1.16 over
n=1499). No post-shock **trap** flag fired on either universe. So immediately after
a shock the model corrects its level bias but is noticeably less accurate, the
familiar pattern of forecasts struggling around regime transitions.

**Interval coverage (h=22).** Coverage is below nominal on clean_core: cov90 = 0.576
and cov50 = 0.257 (targets 0.90 / 0.50), consistent with the negative level bias and
the lognormal bands sitting low. On hard_cases coverage is similar (cov90 = 0.619,
cov50 = 0.291). Coverage degrades with horizon on clean_core (cov90 0.79 at h=1 →
0.50 at h=42). The intervals are too narrow / too low rather than catastrophically
collapsed.

**Strong vs weak tickers/horizons.** On clean_core the model is well-calibrated for
the broad-index and macro names — **TLT** (QLIKE 0.39), **GLD** (0.29), **EEM**
(0.43), **XLE/QQQ/XLF** (~0.60–0.70) at h=22 — and is least accurate on **XLK**
(2.51) and **SPY** (1.24). The single dominant problem is **HYG**, whose h=22 QLIKE
is **9.54** with `log_bias = −10.46` and near-zero coverage (cov90 = 0.079); this
one key drives the `high_yield_credit` group QLIKE to 7.59 and is the reason the
clean_core *pooled* QLIKE looks far worse than the typical per-ticker number. Among
hard cases the model is strongest on **IBIT** (h=22 QLIKE 0.17), **MSOS** (0.24)
and **UVXY** (0.41), and weakest on **USO** (0.80); the crypto group (0.29) and
cannabis group (0.31) are well-behaved.

## Coverage & limitations

- **Full key coverage, no drops.** The predictions parquet has **146,471 OOS rows**
  covering all 15 scored tickers × 5 horizons {1, 5, 10, 22, 42}, min date
  2018-01-02, with every `rv_hat` finite and > 0 and quantiles monotone. **No
  `(ticker, horizon)` was dropped** — every key fit under either the full 9-scalar
  PDV or the fixed-kernel 5-scalar fallback.
- **Fallback split not recoverable from the parquet.** The model records the chosen
  variant (full vs fixed-kernel fallback vs dropped) per key on `self.warnings` at
  fit time, but that in-memory dict is not persisted, and the predictions parquet
  carries no fit-variant column. The exact count of full vs fixed-kernel fallback
  fits is therefore **not recoverable from the artifacts** and is not reconstructed
  here (doing so would require re-running the walk-forward, which is out of scope).
- **HYG is the dominant anomaly (clean_core).** HYG's h=22 fit produces a severe
  low bias (`log_bias = −10.46`, QLIKE 9.54), inflating the pooled clean_core QLIKE
  and the `high_yield_credit` group well above the per-ticker norm. A downstream
  reader should treat the clean_core *pooled* QLIKE as HYG-contaminated and prefer
  the per-ticker / per-group breakdown.
- **Thin hard cases.** **IBIT** and **MSOS** have shorter histories and reduced h=22
  support (IBIT n=537, MSOS n=1293 at h=22 on hard_cases) versus the ~2087-row
  full-history tickers; their favorable QLIKE rests on fewer observations.
- **No IV-incremental skill at h=22 on either universe**, and a persistent negative
  level bias on clean_core that grows with horizon — the long-horizon clean_core
  point forecasts and intervals should be read with that low bias in mind.

## Reproduction

```bash
.venv/bin/python -m rv_eval.walkforward --model candidate_models.pdv_glek:GuyonLekeufackPDV --universe clean_core
.venv/bin/python -m rv_eval.walkforward --model candidate_models.pdv_glek:GuyonLekeufackPDV --universe hard_cases
.venv/bin/python -m rv_eval.selfstats --pred execution/data/predictions/GuyonLekeufackPDV.parquet \
    --out candidate_models/cards/GuyonLekeufackPDV.md --universe clean_core
.venv/bin/python -m rv_eval.selfstats --pred execution/data/predictions/GuyonLekeufackPDV.parquet \
    --out candidate_models/cards/GuyonLekeufackPDV.hard_cases.md --universe hard_cases
```
