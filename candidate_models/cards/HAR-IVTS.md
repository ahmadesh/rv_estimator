# HAR-IVTS — Self Stats
_universe=`clean_core` · primary horizon h=22 · predictions=`execution/data/predictions/HAR-IVTS.parquet` · generated 2026-06-03T17:56:33Z_

_Self-only metrics — no leaderboard rank, no DM test, no MCS, no §9 status._
_Cross-model comparison is produced by the final `rv_eval.evaluator` pass._

## Tier-1 pooled by horizon (§3)
| model | horizon | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-IVTS | 1 | 20570 | 0.2822 | 0.7365 | 0.5874 | -0.2294 | 0.8925 | 0.4925 | 0.0000 |
| HAR-IVTS | 5 | 20530 | 0.1790 | 0.5567 | 0.4310 | -0.1164 | 0.8955 | 0.5201 | 0.0002 |
| HAR-IVTS | 10 | 20480 | 0.2009 | 0.5591 | 0.4256 | -0.1027 | 0.9049 | 0.5361 | 0.0003 |
| HAR-IVTS | 22 | 20360 | 0.3432 | 0.6105 | 0.4517 | -0.1025 | 0.9141 | 0.5541 | 0.0008 |
| HAR-IVTS | 42 | 20160 | 0.4698 | 0.6836 | 0.4952 | -0.1074 | 0.9132 | 0.5581 | 0.0015 |

## §5 IV-incremental skill (per horizon)
| model | horizon | n | slope | t_slope | sign_acc | qlike_model | qlike_iv | qlike_gain_vs_iv |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-IVTS | 1 | 20570 | 0.4943 | 49.3497 | 0.7053 | 0.2822 | 0.3278 | 0.0456 |
| HAR-IVTS | 5 | 20530 | 0.4988 | 49.3106 | 0.6665 | 0.1790 | 0.2087 | 0.0297 |
| HAR-IVTS | 10 | 20480 | 0.5617 | 31.9010 | 0.6016 | 0.2009 | 0.2201 | 0.0192 |
| HAR-IVTS | 22 | 20360 | 0.3170 | 8.5121 | 0.5132 | 0.3432 | 0.3419 | -0.0013 |
| HAR-IVTS | 42 | 20160 | 0.0438 | 1.3855 | 0.4947 | 0.4698 | 0.4743 | 0.0045 |

## §6 Conditional bias by IV-percentile bucket (h=22)
| model | horizon | iv_pctile_bucket | n | qlike | log_bias |
| --- | --- | --- | --- | --- | --- |
| HAR-IVTS | 22 | 0 | 5149 | 0.1849 | -0.1416 |
| HAR-IVTS | 22 | 1 | 3408 | 0.3521 | -0.1557 |
| HAR-IVTS | 22 | 2 | 3412 | 0.5095 | -0.1146 |
| HAR-IVTS | 22 | 3 | 3497 | 0.3726 | -0.0843 |
| HAR-IVTS | 22 | 4 | 4894 | 0.3664 | -0.0290 |

## §6 Post-shock calibration (h=22)
| model | horizon | bias_all | qlike_all | bias_postshock | qlike_postshock | n_postshock | trap_flag |
| --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-IVTS | 22 | -0.1025 | 0.3432 | -0.0600 | 0.3873 | 3871 |  |

## Per-ticker Tier-1 at h=22
| model | horizon | ticker | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-IVTS | 22 | EEM | 2036 | 0.2511 | 0.5771 | 0.4327 | -0.0642 | 0.8983 | 0.5732 | 0.0007 |
| HAR-IVTS | 22 | GLD | 2036 | 0.1445 | 0.4657 | 0.3413 | -0.0163 | 0.8954 | 0.5285 | 0.0003 |
| HAR-IVTS | 22 | HYG | 2036 | 0.8437 | 0.8471 | 0.6660 | -0.3574 | 0.9391 | 0.5619 | 0.0002 |
| HAR-IVTS | 22 | IWM | 2036 | 0.3036 | 0.5502 | 0.3950 | 0.0161 | 0.9057 | 0.5437 | 0.0009 |
| HAR-IVTS | 22 | QQQ | 2036 | 0.3006 | 0.6171 | 0.4658 | -0.0716 | 0.8944 | 0.5658 | 0.0008 |
| HAR-IVTS | 22 | SPY | 2036 | 0.4441 | 0.6871 | 0.5197 | -0.0818 | 0.8983 | 0.5526 | 0.0007 |
| HAR-IVTS | 22 | TLT | 2036 | 0.2119 | 0.4863 | 0.3391 | -0.0250 | 0.9190 | 0.4877 | 0.0003 |
| HAR-IVTS | 22 | XLE | 2036 | 0.2814 | 0.5425 | 0.3929 | -0.0963 | 0.9293 | 0.5639 | 0.0015 |
| HAR-IVTS | 22 | XLF | 2036 | 0.3625 | 0.6317 | 0.4922 | -0.1884 | 0.9470 | 0.5909 | 0.0010 |
| HAR-IVTS | 22 | XLK | 2036 | 0.2881 | 0.6116 | 0.4722 | -0.1402 | 0.9145 | 0.5727 | 0.0011 |

## Pooled by group
| model | group | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-IVTS | emerging_markets | 10210 | 0.2880 | 0.6807 | 0.5152 | -0.1263 | 0.8882 | 0.5286 | 0.0005 |
| HAR-IVTS | high_yield_credit | 10210 | 0.6043 | 0.8169 | 0.6393 | -0.3356 | 0.9259 | 0.5539 | 0.0001 |
| HAR-IVTS | oil_and_energy | 10210 | 0.2417 | 0.5479 | 0.4046 | -0.1115 | 0.9133 | 0.5401 | 0.0011 |
| HAR-IVTS | precious_metals | 10210 | 0.2050 | 0.6046 | 0.4538 | -0.0930 | 0.8850 | 0.5074 | 0.0002 |
| HAR-IVTS | us_cyclicals_sector | 10210 | 0.2851 | 0.6155 | 0.4770 | -0.1821 | 0.9357 | 0.5705 | 0.0008 |
| HAR-IVTS | us_large_cap_equity | 20420 | 0.3037 | 0.6491 | 0.4986 | -0.1096 | 0.8932 | 0.5284 | 0.0006 |
| HAR-IVTS | us_rates_and_ig_credit | 10210 | 0.2115 | 0.5562 | 0.4101 | -0.0709 | 0.8954 | 0.4880 | 0.0002 |
| HAR-IVTS | us_small_cap_equity | 10210 | 0.2494 | 0.5513 | 0.4065 | -0.0295 | 0.9000 | 0.5342 | 0.0007 |
| HAR-IVTS | us_technology_sector | 10210 | 0.2509 | 0.6146 | 0.4785 | -0.1506 | 0.9100 | 0.5409 | 0.0008 |

---

## Build metadata (human-only fields — MODEL_PLAN §5)

**Model**: `candidate_models/har_ivts.py:HARIVTS` · `name="HAR-IVTS"` · iter-2 catalog model 15 (Track A, Pattern P1).

**Base / pattern**: `_AttachMixin` + `_LinearLogHAR` (per-(ticker,horizon) OLS of `log(target_var)`, lognormal quantiles via `_lognormal_quantiles`).

**Features (`needs`)**: `HAR_FEATURES` (`log_rv_d/w/m`) + `IV_FEATURES` (`log_iv, iv_slope, skew_25d, vix, vix3m, vix_slope, vvix`) + derived `["iv_curv","iv_ts_30_90","vrp_lag","vrp_mom"]` + `vix9d_slope` (systematic passthrough, raw name from inputs.parquet).

**Derived columns** (built once on the FULL series from `inputs.parquet`, joined by (ticker,date) via `_AttachMixin._derive`; smoke-test fallback rebuilds from X):
- `iv_curv = iv_30d - 2*iv_60d + iv_90d` (term-structure curvature, point-in-time)
- `iv_ts_30_90 = iv_90d - iv_30d` (30->90 IV slope, point-in-time)
- `vrp_lag = iv_30d**2 - total_rv` (point-in-time VRP proxy; uses `iv_30d**2`, NOT `targets.iv2` which is not in X — CATALOG §4 discrepancy 2)
- `vrp_mom = vrp_lag - vrp_lag.shift(5).over("ticker")` (5d VRP momentum; trailing shift -> must be join-built, not recomputed on the predict slice)

**Frozen hyperparameters**: none. Plain log-OLS with intercept; no tuned hyperparameters, so no inner-CV selection was needed (nothing to leak). `_LinearLogHAR.min_obs=100` (inherited, fixed).

**HP-selection note**: N/A — no free hyperparameters. The four derived columns are fixed analytic transforms (Corsi-style HAR structure + VRP definition), not tuned.

**Library versions**: python 3.12.13 · polars 1.41.1 · numpy 2.4.6 · scipy 1.17.1.

**Seed**: deterministic (OLS via `numpy.linalg.lstsq`); no stochastic components, so no RNG seed needed. Test uses `numpy.default_rng(0)`.

**Device**: Apple M4 (arm64), single-process polars/numpy.

**Wall-time**: clean_core walk-forward 11.0s; hard_cases walk-forward 5.4s (both universes upsert one parquet).

**Coverage**: all 15 scored tickers x 5 horizons covered; no convergence/thin-data drops. clean_core OOS rows=102,850; hard_cases OOS rows=37,989; total file=140,839; span 2018-01-02..2026-05-21. All `rv_hat` finite and >0; quantiles non-decreasing by construction (lognormal wrapper).

**Warnings**: HYG shows the largest negative log_bias (h=22 ~ -0.357) and elevated QLIKE (0.84) at h=22 — a known thin-IV / credit-proxy ticker; not a convergence failure. §5 IV-incremental gain is positive at short horizons (h=1..10) and ~flat/slightly negative at h=22 (qlike_gain_vs_iv=-0.0013), as expected where IV is already near-optimal at the 30-DTE tenor.
