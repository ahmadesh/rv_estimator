# EnsembleTopK — Report (Model 12)

## Overview

EnsembleTopK is the equal-weight ensemble of the eight non-baseline realized-volatility
forecasters in this swarm (MODEL_PLAN §4, model 12). It is a **post-hoc combiner**: it learns
nothing of its own and instead reads the predictions each component model has already written to
`execution/data/predictions/`, then averages them on a common (ticker, date, horizon) support. Its
`predict` produces the same 12-column schema (`ticker, date, horizon, rv_hat, sigma, q05..q95`) as
every other model, so the downstream comparison pass scores it identically. This report covers the
clean_core and hard_cases walk-forwards and the self-only statistics in the two accompanying cards
(`EnsembleTopK.md`, `EnsembleTopK.hard_cases.md`). It makes no cross-model ranking claims — that is
the job of the separate comparison pass.

## Modeling approach & rationale

Combining a diverse set of forecasters is the canonical way to buy robustness without committing to
any single specification being correct. The eight components are deliberately heterogeneous: linear
HAR-family regressions (HARQ, HAR-RS, HAR-CJ, HAR-RS-IV-Q), a parametric volatility model
(RealizedGARCH), a gradient-boosted tree (XGBHARRSIV), a recurrent network (LSTMRV), and a
path-dependent volatility model (GuyonLekeufackPDV). Their errors are driven by different
inductive biases — functional form, feature set, estimation method — so their idiosyncratic
mistakes are imperfectly correlated. An equal-weight mean exploits exactly this: averaging
forecasts whose errors are not perfectly correlated reduces the variance of the combined forecast,
and an unweighted mean is the well-known "1/N" baseline that is notoriously hard to beat out of
sample precisely because estimating optimal weights adds estimation noise that usually overwhelms
the theoretical gain. Equal weighting therefore needs no tuning, cannot overfit weights to the OOS
window, and is the natural first-pass combiner before the comparison motivates anything fancier.
The component list is the default specified in MODEL_PLAN §4: all of models 4-11, the non-baseline
candidates. It is hard-coded at the top of `ensemble_top.py` and can be refined after comparison.

## Components & combination math

For each (ticker, date, horizon) key, the ensemble looks at the subset of the eight components that
produced a (finite, positive `rv_hat`, finite non-negative `sigma`) prediction for that key, and
computes:

- **Point forecast**: `rv_hat = mean(component rv_hat)` — a plain equal-weight average in
  `target_var` units (horizon variance).
- **Uncertainty**: `sigma = sqrt( mean(component_sigma^2) + var(component_rv_hat) )`. The first term
  is the average *within-model* predictive variance (each component's own stated uncertainty); the
  second is the *between-model* dispersion (how much the components disagree on the point). This is
  the standard law-of-total-variance decomposition for a mixture: total variance = average
  conditional variance + variance of the conditional means. When the components agree, sigma is
  driven by their individual sigmas; when they disagree, the dispersion term widens the interval,
  which is the desired behavior.
- **Quantiles**: regenerated from scratch with `_lognormal_quantiles(m, s)` from
  `model_contract.py`, using `m = rv_hat` and a log-space sd `s = sqrt(log(1 + (sigma/rv_hat)^2))`.
  This `s` is the exact inverse of the level-sigma convention the per-key models use
  (`sigma = m * sqrt(expm1(s^2))`), so the regenerated quantiles are monotone and centered on the
  combined `rv_hat` and stay consistent with how the components themselves were quantized.

**Min-2-components rule**: a key is kept only if at least two components cover it. A single
component is not an "ensemble," so such keys are dropped rather than passed through or imputed
(MODEL_PLAN §8: missing predictions are dropped, never imputed). The combination is always over the
components *available* for each key — all eight are not required.

## Design & implementation

`EnsembleTopK` subclasses the `Model` ABC (not `_PerKeyModel`, since there is no per-key fitting).
`fit(X, y)` is a no-op. `predict(X)` takes the fold's feature matrix `X` (one row per ticker,date,
no horizon column), extracts its unique (ticker, date) keys, reads each component parquet, restricts
each to those keys via an inner join (the components already carry all five horizons, which fan out
naturally), stacks them, groups by (ticker, date, horizon), and applies the math above. Because the
join is to *this fold's* keys, the walk-forward harness's per-fold `predict(X_test)` returns
combined predictions only for that fold — the ensemble inherits the harness's leakage guards for
free (it never reads anything the components were not themselves allowed to use). The combiner is
fully vectorized in polars/numpy; the only cost is reading eight parquets and one group-by, hence
the ~6-7s wall-clock per universe.

## Hyperparameters

None. Weights are equal (1/N over available components), the min-2-components threshold is fixed,
and there is no validation block or grid search. Nothing in the model is fit to OOS data.

## Self-only results interpretation

These are absolute, self-only numbers — no ranking against other models.

**QLIKE by horizon (clean_core)**: 0.48 (h=1), 0.99 (h=5), 1.59 (h=10), 3.70 (h=22), 6.25 (h=42).
**QLIKE by horizon (hard_cases)**: 0.37 (h=1), 0.36 (h=5), 0.71 (h=10), 2.02 (h=22), 3.66 (h=42).
QLIKE rises monotonically with horizon, as expected: longer horizons are intrinsically harder and
the lognormal interval machinery is stretched further. Notably the hard_cases QLIKE is *lower* than
clean_core at every horizon, largely because several hard-case names (UVXY, MSOS) sit at high vol
levels where the QLIKE loss is more forgiving in relative terms.

**IV-incremental skill at h=22**: `qlike_gain_vs_iv` is negative in both universes (-3.37 clean_core,
-1.72 hard_cases), i.e. the ensemble's point forecast does not beat the option-implied IV² forecast
on QLIKE at the long horizon, and the regression slope on IV is essentially zero/negative. This is a
known weakness of the components rolled up: the linear HAR members and the average are conservative
and bias *low* at long horizons (see below), where IV's forward-looking content is most valuable.
At h=1 the gain is much closer to flat (-0.15 clean_core, -0.01 hard_cases).

**Conditional bias by IV bucket (h=22)**: `log_bias` is uniformly negative (-4.4 to -4.8 clean_core;
-2.4 to -3.2 hard_cases), so the ensemble under-predicts realized variance at the long horizon
across all IV-percentile buckets, with the largest under-prediction in the lowest IV bucket. The
bias shrinks (toward zero) as IV percentile rises. This downward h=22 bias is the dominant
limitation and is inherited from the lognormal-mean / averaging behavior of the components rather
than introduced by the combiner.

**Post-shock calibration (h=22)**: bias and QLIKE are slightly *better* post-shock than overall
(clean_core: -4.43 vs -4.62 bias, 3.53 vs 3.70 QLIKE; hard_cases similar), and the trap_flag is not
set — the ensemble does not blow up in the days after a vol spike.

**Coverage / calibration (h=22)**: 90% interval coverage is 0.70 (clean_core) / 0.97 (hard_cases)
and 50% coverage is 0.10 (clean_core) / 0.31 (hard_cases). The short horizons are well-calibrated
(cov90 ≈ 0.89-0.99), but at h=22 and especially h=42 the clean_core 50%/90% intervals are too
narrow (cov90 collapses to 0.17 at h=42), consistent with the long-horizon downward point bias
pulling the lognormal mass below realized variance. Hard_cases intervals are wider and better
covered at mid horizons but also thin out at h=42.

**Strengths**: low, monotone QLIKE at short/mid horizons; well-behaved post-shock; robust by
construction (no single component dominates); the dispersion term widens intervals exactly when the
components disagree. **Weaknesses**: long-horizon (h=22, h=42) downward bias and under-coverage; no
incremental skill over IV² at the long horizon.

## Coverage & limitations

All eight components were present on disk and used. Of the combined keys, 142,389 used all eight
components, ~3,900 used five to seven (where a component such as LSTMRV, HAR-RS-IV-Q, or XGBHARRSIV
lacked a prediction for that key), and 188 used exactly two. **23 keys were dropped** for having
fewer than two components available — all of them MSOS, the thin US-cannabis name where only a
single component produced a forecast. IBIT (crypto, ~2y of options coverage) and MSOS are the
thinnest names: IBIT has only 537 rows at h=22, MSOS 1,270. The ensemble is only as good as its
components on these names, and the dropped MSOS keys mean its hard_cases coverage there is slightly
below the components' union. No values are ever imputed.

## Reproduction

```bash
.venv/bin/python -m pytest candidate_models/tests/test_ensemble_top.py -q
.venv/bin/python -m rv_eval.walkforward --model candidate_models.ensemble_top:EnsembleTopK --universe clean_core
.venv/bin/python -m rv_eval.walkforward --model candidate_models.ensemble_top:EnsembleTopK --universe hard_cases
.venv/bin/python -m rv_eval.selfstats --pred execution/data/predictions/EnsembleTopK.parquet \
    --out candidate_models/cards/EnsembleTopK.md --universe clean_core
.venv/bin/python -m rv_eval.selfstats --pred execution/data/predictions/EnsembleTopK.parquet \
    --out candidate_models/cards/EnsembleTopK.hard_cases.md --universe hard_cases
```

Requires the eight component prediction parquets to already exist in
`execution/data/predictions/`. The combiner is deterministic; CPU; ~6-7s per universe.
