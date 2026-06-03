# XGBHARRSIV — Modeling Report

**Model number:** 9 · **Class:** `candidate_models.xgb_har:XGBHARRSIV` · **Tier:** ML

## Overview

XGBHARRSIV is a gradient-boosted regression-tree model (XGBoost) trained on the
HAR-RS + implied-volatility feature matrix — the same regressor block as the
strongest linear baseline, model 7 (HAR-RS-IV-Q). One booster is fit per
`(ticker, horizon)`, regressing `log(target_var)` on the feature matrix; the
prediction is exponentiated back to `target_var` units via the lognormal-mean
correction and dressed with lognormal quantiles consistent with the benchmarks.
The core idea is to keep model 7's proven, leakage-safe feature set but replace
the linear log-OLS mapping with a flexible non-linear tree ensemble, so the
forecaster can capture interactions and regime-dependent effects (e.g. between
the HAR realized blocks and the VIX/skew block) that a linear HAR cannot.

## Modeling approach & rationale

The model is XGBoost gradient-boosted trees on the deduped
`HAR_RS_FEATURES + IV_FEATURES + ["sqrt_rq"]` matrix (MODEL_PLAN §4 model 9),
one booster per `(ticker, horizon)` targeting `log(target_var)`. Predictions are
back-transformed with the lognormal-mean correction
`rv_hat = exp(mu + 0.5*sigma^2)` (so `rv_hat` is the QLIKE-optimal mean forecast,
matching the linear HAR benchmarks rather than the median), and quantiles are
produced by `_lognormal_quantiles` exactly as for the benchmark models — keeping
the interval construction comparable across the candidate set.

Why this should help RV forecasting: the HAR family (Corsi 2009; Patton &
Sheppard 2015 for the semivariance/jump extension) is a *linear* model in
log-RV. It cannot represent interactions — for instance, that the predictive
weight on recent realized variance should differ when the VIX term structure is
inverted, or that the jump component matters more in some regimes than others.
Gradient-boosted trees are a natural non-linear alternative on the *same*
features: they partition the feature space and can capture those threshold and
interaction effects without hand-specifying them, while early stopping and
shrinkage control overfit. This makes XGBHARRSIV the ML-tier counterpart to the
linear HAR family — a fair, like-for-like test of whether non-linearity buys
anything over the strongest linear HAR (model 7) on identical inputs.

## Features & inputs

The model uses the deduped union
`HAR_RS_FEATURES + IV_FEATURES + ["sqrt_rq"]` — 14 features (all non-null
required to fit/predict; NaNs propagate to a dropped row):

- **HAR-RS block (6):** `log_rv_d`, `log_rv_w`, `log_rv_m`, `rs_minus_5d`,
  `rs_plus_5d`, `jump_5d`
- **IV block (7):** `log_iv`, `iv_slope`, `skew_25d`, `vix`, `vix3m`,
  `vix_slope`, `vvix`
- **Realized quarticity (1):** `sqrt_rq`

Target: `log(target_var)` (the sum of the next-`h` daily realized variances, in
log space).

## Design & implementation

- **One booster per `(ticker, horizon)`** via `xgboost.XGBRegressor`.
- **Fixed (non-gridded) params:** `objective="reg:squarederror"`,
  `subsample=0.8`, `colsample_bytree=0.8`, `reg_lambda=1.0`,
  `tree_method="hist"`, `seed=0`.
- **`n_estimators` by early stopping:** capped at 2000
  (`_N_ESTIMATORS_CAP = 2000`), chosen per fit by early stopping
  (`early_stopping_rounds=50`) on a **10% time-ordered within-train tail**
  (`_VAL_TAIL_FRAC = 0.10`). The split sorts each key by date, holds out the last
  10% as the eval set, and trains on the leading 90% — leakage-safe because the
  tail is still within-train (never the OOS window). A guard keeps a sane training
  core when a key is short.
- **`sigma`:** residual std of `log(target_var)` on that same held-out tail
  (floored at `1e-3`). `sigma` feeds both the lognormal-mean back-transform and the
  quantile construction.
- **Prediction:** `mu = model.predict(X)`; `rv_hat = exp(mu + 0.5*sigma^2)`. A NaN
  in any feature propagates to a NaN prediction, which the harness drops.
- **`min_obs = 100`.**
- **Library version:** xgboost 3.2.0. **Device:** cpu (`tree_method="hist"`).
- **Random seed:** 0 (numpy and xgboost).

## Hyperparameters & selection

The structural hyperparameters were chosen by the **leakage-safe
tune-once-then-freeze protocol** (MODEL_PLAN §4 "Hyperparameter selection",
models 8–11) and are then hard-coded in the model class.

**Frozen HPs:** `max_depth=3`, `learning_rate=0.03`, `min_child_weight=20`.

**Protocol** (from the XGB card and `candidate_models/_tune_xgb.py`, tuning run
2026-05-31):

- **Grid (27 points):** `max_depth ∈ {3, 4, 6}` × `learning_rate ∈ {0.03, 0.05, 0.1}`
  × `min_child_weight ∈ {5, 10, 20}`. The grid's *initial point* (the plan's bold
  cell) is `(max_depth=4, learning_rate=0.05, min_child_weight=10)` — that is the
  starting guess, not the answer.
- **Split (pre-OOS only):** search-train = rows with `date < HPTUNE_VAL_START`
  (2016-01-01); validation = `[HPTUNE_VAL_START, OOS_START)` = **2016–2017**.
  No `date ≥ OOS_START` (2018) is read during tuning, and `_tune_xgb.py` asserts
  the validation block lies entirely within 2016–2017 and below the OOS start.
- **Procedure:** for each grid point, fit ONE global booster (pooled across all
  scored tickers) on search-train at the primary horizon **h=22**
  (`HPTUNE_METRIC_HORIZON`), with `n_estimators` chosen by early stopping on a
  within-search-train time-ordered 10% tail; score **pooled QLIKE @ h=22** on the
  validation block; keep the lowest. Tuning is global (one HP set for all
  tickers/horizons), not per-key.
- **Result:** the **winner `(3, 0.03, 20)` scored validation QLIKE@h22 = 0.146970**,
  beating the **initial point `(4, 0.05, 10)` at 0.158985** — a meaningful
  improvement that justifies a deeper-shrinkage, shallower-tree, higher-
  min-child-weight configuration (more regularized than the initial guess).

Crucially, the **2016–2017 validation block was never an OOS test row.** Once the
HPs were frozen, those dates are reused only as *training* rows for the OOS
walk-forward folds — which is not leakage, because no `date ≥ 2018` ever informed
the hyperparameters. `n_estimators` is not part of the grid; it is set per fit by
early stopping (cap 2000), itself leakage-safe.

## Self-only results interpretation

All numbers below are this model's own OOS self-stats from `XGBHARRSIV.md`
(clean_core) and `XGBHARRSIV.hard_cases.md`. Self-contained — no ranking against
other models.

**QLIKE across horizons (pooled).**

| horizon | QLIKE clean_core | QLIKE hard_cases |
|---|---|---|
| 1  | 0.295 | 0.321 |
| 5  | 0.203 | 0.271 |
| 10 | 0.240 | 0.288 |
| 22 | **0.398** | **0.331** |
| 42 | 0.534 | 0.397 |

The **headline QLIKE@h22 is 0.398 (clean_core) / 0.331 (hard_cases)**. QLIKE is
best in the mid-horizons (h=5 is the minimum at 0.203 on clean_core) and rises
again toward h=42, a typical RV-forecasting shape. `log_bias` is small and
negative throughout (−0.26 at h=1 to −0.08 at h=42 on clean_core), i.e. only a
mild low bias that shrinks with horizon — a very different, far better-calibrated
regime than a model that collapses at long horizons.

**§5 IV-incremental skill.** XGBHARRSIV adds clear incremental skill over the
IV-as-forecast benchmark at *short* horizons and loses it at *long* horizons. On
clean_core, `qlike_gain_vs_iv` is **+0.036 at h=1** and **+0.008 at h=5**
(positive = beats IV), with a strongly significant positive regression slope
(slope 1.586, t≈50.7 at h=1; slope 0.924, t≈30.9 at h=5) and sign-accuracy 0.688 /
0.635. By h=22 the gain turns negative (−0.057) and at h=42 −0.066, with the slope
shrinking toward zero (0.093 at h=22). Hard_cases shows the same pattern (gain
+0.039 at h=1, negative from h=5 on). Read in isolation: the model's edge over raw
implied vol is concentrated at the short horizons where realized-variance dynamics
dominate, and fades at the monthly+ horizons where IV is itself a strong forecast.

**§6 conditional bias by IV bucket (h=22).** Bias rotates with the IV regime:
on clean_core `log_bias` moves from −0.247 in the lowest IV bucket to +0.115 in
the highest, with QLIKE rising from 0.214 (bucket 0) to 0.527 (bucket 4). So the
model slightly *under*-forecasts in calm regimes and slightly *over*-forecasts in
high-IV regimes, and is hardest in the top IV bucket. Hard_cases is similar
(−0.234 → +0.187; QLIKE 0.297 → 0.515).

**§6 post-shock calibration (h=22).** Post-shock, the bias flips from mildly
negative to mildly positive (clean_core −0.095 → +0.056; hard_cases −0.055 →
+0.116) and QLIKE rises (clean_core 0.398 → 0.559; hard_cases 0.331 → 0.458).
On **hard_cases the post-shock trap flag fired (✓)** — the model over-forecasts and
loses accuracy in the days right after a vol spike for the hard-case tickers
(notably the volatility/leverage names); no trap flag fired on clean_core.

**Interval coverage (h=22).** Coverage is reasonably well calibrated, unusually so
for this candidate set. On clean_core, cov90 = 0.849 and cov50 = 0.488 (targets
0.90 / 0.50) — slightly narrow at the 90% band but close at the 50% band. Coverage
is best at short horizons (cov90 0.894 at h=1) and degrades toward h=42 (cov90
0.790). Hard_cases h=22 cov90 = 0.801 / cov50 = 0.454.

**Strong vs weak tickers/horizons.** Strongest at the mid-horizons (h=5/h=10) and
on rates/precious-metals names — e.g. **GLD** (h=22 QLIKE 0.181) and **TLT** (0.227)
on clean_core. Weakest on **HYG** (h=22 QLIKE 0.959, the worst clean_core key, with
`log_bias` −0.343 and a 0.696 group QLIKE for high-yield credit) and at the top IV
bucket / post-shock window. Among hard cases, h=22 QLIKE is uniformly moderate
(IBIT 0.159, MSOS 0.296, USO 0.319, UVXY 0.358, KRE 0.355), though coverage on the
thin/illiquid names is poor (see below).

## Coverage & limitations

- **Full key coverage, no drops.** Per the cards, 144,527 OOS rows cover all 15
  scored tickers × 5 horizons {1,5,10,22,42} (min date 2018-01-02); none dropped,
  `rv_hat` finite & > 0, quantiles monotone. No per-`(ticker, horizon)` fit failures.
- **Thin hard cases.** IBIT and MSOS have shorter histories and so fewer rows
  (IBIT n=224, MSOS n=1207 at h=22 on hard_cases) though with full horizon
  coverage. Their **interval coverage is poor**: IBIT h=22 cov90 = 0.308 /
  cov50 = 0.143 and MSOS cov90 = 0.618 / cov50 = 0.310 — far from target, the
  natural consequence of estimating per-key `sigma` from a short held-out tail.
  MSOS also carries a positive h=22 `log_bias` (+0.317), over-forecasting.
- **Post-shock over-forecasting on hard cases.** The h=22 post-shock trap flag
  (✓ on hard_cases) means the model degrades right after vol spikes for the
  hard-case universe; a downstream reader should note the model is least reliable
  immediately post-shock and in the highest IV bucket.
- **Long-horizon IV gap.** At h=22 and h=42 the model does not beat the
  IV-as-forecast benchmark in isolation (`qlike_gain_vs_iv` negative); its edge is
  a short-horizon phenomenon.

## Reproduction

```bash
.venv/bin/python -m rv_eval.walkforward --model candidate_models.xgb_har:XGBHARRSIV --universe clean_core
.venv/bin/python -m rv_eval.walkforward --model candidate_models.xgb_har:XGBHARRSIV --universe hard_cases
.venv/bin/python -m rv_eval.selfstats --pred execution/data/predictions/XGBHARRSIV.parquet \
    --out candidate_models/cards/XGBHARRSIV.md --universe clean_core
.venv/bin/python -m rv_eval.selfstats --pred execution/data/predictions/XGBHARRSIV.parquet \
    --out candidate_models/cards/XGBHARRSIV.hard_cases.md --universe hard_cases

# Hyperparameter tuning (tune-once-then-freeze; standalone, not part of the harness):
.venv/bin/python -m candidate_models._tune_xgb
```
