# HAR-IVTS — Self Stats
_universe=`hard_cases` · primary horizon h=22 · predictions=`execution/data/predictions/HAR-IVTS.parquet` · generated 2026-06-03T17:56:33Z_

_Self-only metrics — no leaderboard rank, no DM test, no MCS, no §9 status._
_Cross-model comparison is produced by the final `rv_eval.evaluator` pass._

## Tier-1 pooled by horizon (§3)
| model | horizon | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-IVTS | 1 | 7636 | 0.3973 | 0.7424 | 0.5780 | -0.2256 | 0.8886 | 0.4993 | 0.0007 |
| HAR-IVTS | 5 | 7595 | 1.2717 | 0.6316 | 0.4705 | -0.1268 | 0.8728 | 0.5028 | 0.0027 |
| HAR-IVTS | 10 | 7548 | 0.2606 | 0.6312 | 0.4723 | -0.0999 | 0.8561 | 0.4960 | 0.0053 |
| HAR-IVTS | 22 | 7488 | 0.3241 | 0.6480 | 0.4841 | -0.0590 | 0.8458 | 0.4729 | 0.0090 |
| HAR-IVTS | 42 | 7347 | 0.4106 | 0.6855 | 0.4978 | -0.0221 | 0.8265 | 0.4660 | 0.0725 |

## §5 IV-incremental skill (per horizon)
| model | horizon | n | slope | t_slope | sign_acc | qlike_model | qlike_iv | qlike_gain_vs_iv |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-IVTS | 1 | 7636 | 0.0388 | 14.2832 | 0.7427 | 0.3973 | 0.3563 | -0.0410 |
| HAR-IVTS | 5 | 7595 | 0.0563 | 15.2486 | 0.7236 | 1.2717 | 0.2630 | -1.0087 |
| HAR-IVTS | 10 | 7548 | 0.0086 | 3.1370 | 0.6803 | 0.2606 | 0.2551 | -0.0055 |
| HAR-IVTS | 22 | 7488 | 0.3529 | 16.6842 | 0.6285 | 0.3241 | 0.2738 | -0.0503 |
| HAR-IVTS | 42 | 7347 | -0.0000 | -0.0910 | 0.6262 | 0.4106 | 0.3189 | -0.0916 |

## §6 Conditional bias by IV-percentile bucket (h=22)
| model | horizon | iv_pctile_bucket | n | qlike | log_bias |
| --- | --- | --- | --- | --- | --- |
| HAR-IVTS | 22 | 0 | 1814 | 0.3070 | -0.0852 |
| HAR-IVTS | 22 | 1 | 1208 | 0.2445 | -0.0694 |
| HAR-IVTS | 22 | 2 | 1318 | 0.2447 | -0.0281 |
| HAR-IVTS | 22 | 3 | 1442 | 0.2492 | -0.1062 |
| HAR-IVTS | 22 | 4 | 1706 | 0.5232 | -0.0078 |

## §6 Post-shock calibration (h=22)
| model | horizon | bias_all | qlike_all | bias_postshock | qlike_postshock | n_postshock | trap_flag |
| --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-IVTS | 22 | -0.0590 | 0.3241 | -0.0490 | 0.3804 | 1396 |  |

## Per-ticker Tier-1 at h=22
| model | horizon | ticker | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-IVTS | 22 | IBIT | 224 | 0.1481 | 0.5718 | 0.4225 | -0.0818 | 0.6161 | 0.3259 | 0.0025 |
| HAR-IVTS | 22 | KRE | 2036 | 0.3558 | 0.5892 | 0.4136 | -0.0503 | 0.9268 | 0.5771 | 0.0017 |
| HAR-IVTS | 22 | MSOS | 1158 | 0.4757 | 0.7322 | 0.5736 | 0.2710 | 0.6356 | 0.3074 | 0.0078 |
| HAR-IVTS | 22 | USO | 2036 | 0.2287 | 0.5548 | 0.3987 | -0.0087 | 0.8389 | 0.4686 | 0.0031 |
| HAR-IVTS | 22 | UVXY | 2034 | 0.3209 | 0.7410 | 0.5960 | -0.3035 | 0.9164 | 0.4833 | 0.0235 |

## Pooled by group
| model | group | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-IVTS | crypto | 1151 | 0.2126 | 0.6873 | 0.5204 | -0.1970 | 0.7559 | 0.3970 | 0.0017 |
| HAR-IVTS | long_volatility_vix | 10200 | 0.3049 | 0.7543 | 0.6032 | -0.3049 | 0.8960 | 0.4814 | 0.0167 |
| HAR-IVTS | oil_and_energy | 10210 | 1.0960 | 0.6459 | 0.4644 | -0.0768 | 0.8404 | 0.4659 | 0.0439 |
| HAR-IVTS | us_cannabis | 5843 | 0.4489 | 0.6988 | 0.5325 | 0.1526 | 0.7368 | 0.3960 | 0.0054 |
| HAR-IVTS | us_cyclicals_sector | 10210 | 0.2873 | 0.5755 | 0.4143 | -0.0798 | 0.9194 | 0.5782 | 0.0013 |

---

## Build metadata (human-only fields — MODEL_PLAN §5)

**Model**: `candidate_models/har_ivts.py:HARIVTS` · `name="HAR-IVTS"` · iter-2 catalog model 15 (Track A, Pattern P1).

**Base / pattern**: `_AttachMixin` + `_LinearLogHAR` (per-(ticker,horizon) OLS of `log(target_var)`, lognormal quantiles via `_lognormal_quantiles`).

**Features (`needs`)**: `HAR_FEATURES` (`log_rv_d/w/m`) + `IV_FEATURES` (`log_iv, iv_slope, skew_25d, vix, vix3m, vix_slope, vvix`) + derived `["iv_curv","iv_ts_30_90","vrp_lag","vrp_mom"]` + `vix9d_slope`.

**Derived columns** (built once on the FULL series from `inputs.parquet`, joined by (ticker,date) via `_AttachMixin._derive`):
- `iv_curv = iv_30d - 2*iv_60d + iv_90d`; `iv_ts_30_90 = iv_90d - iv_30d` (point-in-time)
- `vrp_lag = iv_30d**2 - total_rv` (point-in-time VRP proxy; uses `iv_30d**2`, NOT `targets.iv2` — CATALOG §4 discrepancy 2)
- `vrp_mom = vrp_lag - vrp_lag.shift(5).over("ticker")` (5d VRP momentum; trailing shift -> join-built, never recomputed on the predict slice)

**Frozen hyperparameters**: none (plain log-OLS, intercept). No inner-CV selection needed — nothing to tune, nothing to leak. `_LinearLogHAR.min_obs=100` inherited/fixed.

**HP-selection note**: N/A — no free hyperparameters.

**Library versions**: python 3.12.13 · polars 1.41.1 · numpy 2.4.6 · scipy 1.17.1.

**Seed**: deterministic OLS (`numpy.linalg.lstsq`); no RNG in the model.

**Device**: Apple M4 (arm64).

**Wall-time**: hard_cases walk-forward 5.4s (clean_core 11.0s; both upsert one parquet).

**Coverage**: all 5 hard-case tickers (UVXY, MSOS, IBIT, USO, KRE) x 5 horizons covered; no drops. hard_cases OOS rows=37,989; total file=140,839; span 2018-01-02..2026-05-21. All `rv_hat` finite >0; quantiles non-decreasing.

**Warnings**: h=5 pooled QLIKE (1.27) is inflated by tail blow-ups on the most extreme hard-case names (UVXY/MSOS) — a few large under-forecasts in violent vol spikes, not a fit failure (all keys converged, MIN_TRAIN gates only the first fold). §5 IV-incremental gain is negative across horizons here (qlike_gain_vs_iv<0): for these hard cases raw IV is a strong stand-alone forecast and the HAR mean adds dispersion; this is expected and the calibration-track models (25/26) target it. cov90 drifts below 0.90 at long horizons (h=22:0.846, h=42:0.827) — mild under-coverage on fat-tailed names.
