# HAR-RS — Modeling Report

**Identity.** Model 5 · class `candidate_models.har_rs:HARRS` (name `HAR-RS`) · Tier: Modern HAR (semivariance + jump).

## Overview

HAR-RS is plain log-OLS HAR with the daily variation split into its *signed* pieces plus a jump term. The single idea it adds over HAR is **directional and jump asymmetry**: not all of yesterday's variation predicts tomorrow's variance equally. Downside (negative-return) variation — the "leverage" side — typically forecasts future RV more strongly and more persistently than upside variation, and discontinuous jump variation is far less persistent than continuous variation. HAR-RS lets the regression assign separate coefficients to these components instead of forcing one daily coefficient on their sum.

## Modeling approach & rationale

HAR-RS follows Patton & Sheppard (2015), who decompose realized variance into realized *semivariances* — `RS⁻` from negative intraday returns and `RS⁺` from positive ones — and show that the downside component is the dominant predictor of future volatility, capturing the well-documented leverage effect at the realized-measure level. It keeps the weekly and monthly log-RV HAR components for long-memory persistence but replaces (here, augments) the daily lag with the signed semivariance pieces and a separate jump term, on the theory that downside variation and continuous variation are persistent while upside variation and jumps decay quickly. Allowing the OLS to weight `RS⁻` more heavily than `RS⁺` and to discount the jump term should sharpen the conditional forecast, especially around volatility increases driven by price drops. It remains a single linear log-OLS with the same estimator and lognormal back-transform as HAR, so any gain is attributable to the decomposition, not to added functional flexibility.

## Features & inputs

`HAR_RS_FEATURES` = `log_rv_d`, `log_rv_w`, `log_rv_m`, `rs_minus_5d`, `rs_plus_5d`, `jump_5d` — six regressors plus an intercept. `log_rv_d/w/m` are the Corsi day/week/month log-RV components. `rs_minus_5d` and `rs_plus_5d` are 5-day trailing roll-means of the negative- and positive-return realized semivariances (the signed-variation block). `jump_5d` is the 5-day trailing roll-mean of the daily jump component, isolating discontinuous variation. All six are point-in-time columns built in `features.py`; the model adds nothing of its own.

## Design & implementation

HAR-RS subclasses `_LinearLogHAR` and sets only `name = "HAR-RS"` and `needs = HAR_RS_FEATURES`. Per `(ticker, horizon)` it runs a direct-h OLS of `log(target_var)` on the six regressors + intercept via `numpy.linalg.lstsq`, storing `beta` and the residual log-sd `s` (`ddof = n_params`, `min_obs = 100`). At predict time `mu = design @ beta`, `m = exp(mu + ½ s²)` is the lognormal-mean forecast (`rv_hat`), `sigma = m·sqrt(expm1(s²))`, quantiles via `_lognormal_quantiles(m, s)`. **No free hyperparameters** — deterministic log-OLS, identical machinery to the benchmarks. Rows where any feature is null propagate NaN through the design matrix and are dropped, never imputed.

## Self-only results interpretation

**QLIKE across horizons.** On clean_core, pooled QLIKE is 0.3199 / 0.2127 / 0.2291 / 0.3265 / 0.4223 at h = 1 / 5 / 10 / 22 / 42 — the standard HAR-family curve, lowest at h=5 and rising into the long horizons. Headline **QLIKE@h22 = 0.3265** (hard_cases 0.3047). On hard_cases the curve is flatter (0.4008 → 0.3339) and improves with horizon.

**Calibration / coverage.** Well calibrated on clean_core: at h=22 cov50 = 0.5651, cov90 = 0.9134 (the 90% band slightly conservative). Hard_cases at h=22 is a touch under nominal (cov50 = 0.4889, cov90 = 0.8636).

**Conditional bias.** A consistent mild under-forecast shrinking toward zero as IV rises. At h=22 (clean_core) log_bias by IV-percentile bucket is −0.2212 / −0.2024 / −0.1560 / −0.1113 / −0.0909 (buckets 0→4) — worst in the lowest-IV regime, best-calibrated in the highest. Hard_cases mirrors this (−0.2477 → −0.0513).

**Post-shock behavior.** At h=22 bias_all = −0.1578 vs bias_postshock = −0.2460 (n=3,986, clean_core): the under-forecast deepens in the 5 days after a vol spike, though the **trap flag does NOT fire**. Hard_cases is milder (−0.1382 → −0.2204).

**Across tickers (h=22, clean_core).** Strongest on GLD (0.1816), TLT (0.2208), EEM (0.2360), XLE (0.2822). The dominant weak spot is **HYG (0.6535)** — the highest per-ticker QLIKE with a large negative bias (−0.6345), reflecting HYG's spike-prone credit-stress dynamics. SPY (0.4440) is next weakest. On hard_cases, UVXY (0.3349) and KRE (0.3437) are weakest; IBIT (0.1911) is nominally low on a small n=517 sample.

**IV-incremental skill.** At h=22 `qlike_gain_vs_iv = +0.0115` (clean_core) — HAR-RS edges IV-as-forecast at the primary horizon, with the gain growing at h=42 (+0.0439). Notably the regression slope on the IV signal at h=22/42 is slightly negative (−0.018 / −0.029), i.e. the variance-decomposition features already absorb most of what IV would add at long horizons. At the short horizons it is roughly even with IV (−0.005 at h=5, −0.011 at h=10). Sign-accuracy is 0.64 at h=1. On hard_cases `qlike_gain_vs_iv` is negative at every horizon (IV-as-forecast wins there), reflecting how informative listed-option IV is for the volatile hard-case names.

## Coverage & limitations

- **Full coverage on all 10 clean_core tickers**, 105,450 OOS rows (≈2,087 per ticker × 5 horizons), span 2018-01-02 … 2026-05-22. No cells dropped; `min_obs=100` never tripped.
- **Full (ticker × horizon) coverage on hard_cases** (40,810 rows), but IBIT (~2,713 rows total, 517 at h=22) and MSOS (~6,462 rows, 1,270 at h=22) are data-starved by their short histories, not by any model drop. IBIT's interval coverage at h=22 is poor (cov90 = 0.7215) on the thin sample.
- A measurement-table anomaly to flag for the comparison reader: the hard_cases pinball numbers are unusually large at the longer horizons (USO drives a 0.0518 per-ticker pinball at h=22 and the oil_and_energy group pinball is 0.1185) — this is concentrated in USO's quantile spread, worth checking against sibling models in the cross-model pass.
- Because HAR-RS uses no IV features it loses no rows to IV nulls — its support equals the full variance-path support (identical to HAR/HARQ), broader than the IV-using models. The comparison's common-support join must account for this.

## Reproduction

```bash
.venv/bin/python -m rv_eval.walkforward --model candidate_models.har_rs:HARRS --universe clean_core
.venv/bin/python -m rv_eval.walkforward --model candidate_models.har_rs:HARRS --universe hard_cases
.venv/bin/python -m rv_eval.selfstats --pred execution/data/predictions/HAR-RS.parquet --out candidate_models/cards/HAR-RS.md --universe clean_core
.venv/bin/python -m rv_eval.selfstats --pred execution/data/predictions/HAR-RS.parquet --out candidate_models/cards/HAR-RS.hard_cases.md --universe hard_cases
```
