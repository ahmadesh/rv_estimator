# STAR-HAR — Self Stats
_universe=`clean_core` · primary horizon h=22 · predictions=`execution/data/predictions/STAR-HAR.parquet` · generated 2026-06-03T22:10:41Z_

_Self-only metrics — no leaderboard rank, no DM test, no MCS, no §9 status._
_Cross-model comparison is produced by the final `rv_eval.evaluator` pass._

## Tier-1 pooled by horizon (§3)
| model | horizon | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| STAR-HAR | 1 | 20810 | 0.3084 | 0.8013 | 0.6417 | -0.3114 | 0.8932 | 0.4838 | 0.0000 |
| STAR-HAR | 5 | 20770 | 0.2025 | 0.6227 | 0.4894 | -0.1986 | 0.8937 | 0.5058 | 0.0002 |
| STAR-HAR | 10 | 20720 | 0.2185 | 0.6213 | 0.4840 | -0.1881 | 0.9013 | 0.5141 | 0.0003 |
| STAR-HAR | 22 | 20600 | 0.3146 | 0.6615 | 0.5057 | -0.1921 | 0.9060 | 0.5296 | 0.0008 |
| STAR-HAR | 42 | 20400 | 0.4147 | 0.7226 | 0.5427 | -0.2027 | 0.9092 | 0.5338 | 0.0016 |

## §5 IV-incremental skill (per horizon)
| model | horizon | n | slope | t_slope | sign_acc | qlike_model | qlike_iv | qlike_gain_vs_iv |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| STAR-HAR | 1 | 20810 | 1.2307 | 54.8851 | 0.6145 | 0.3084 | 0.3277 | 0.0193 |
| STAR-HAR | 5 | 20770 | 1.1395 | 59.6745 | 0.5687 | 0.2025 | 0.2079 | 0.0054 |
| STAR-HAR | 10 | 20720 | 0.8353 | 37.1362 | 0.5211 | 0.2185 | 0.2187 | 0.0002 |
| STAR-HAR | 22 | 20600 | 0.3293 | 12.5996 | 0.4830 | 0.3146 | 0.3397 | 0.0251 |
| STAR-HAR | 42 | 20400 | 0.3015 | 12.2954 | 0.4666 | 0.4147 | 0.4699 | 0.0552 |

## §6 Conditional bias by IV-percentile bucket (h=22)
| model | horizon | iv_pctile_bucket | n | qlike | log_bias |
| --- | --- | --- | --- | --- | --- |
| STAR-HAR | 22 | 0 | 5240 | 0.1775 | -0.2328 |
| STAR-HAR | 22 | 1 | 3448 | 0.2966 | -0.2263 |
| STAR-HAR | 22 | 2 | 3439 | 0.4367 | -0.1905 |
| STAR-HAR | 22 | 3 | 3533 | 0.3612 | -0.1680 |
| STAR-HAR | 22 | 4 | 4940 | 0.3543 | -0.1435 |

## §6 Post-shock calibration (h=22)
| model | horizon | bias_all | qlike_all | bias_postshock | qlike_postshock | n_postshock | trap_flag |
| --- | --- | --- | --- | --- | --- | --- | --- |
| STAR-HAR | 22 | -0.1921 | 0.3146 | -0.2547 | 0.3600 | 3921 |  |

## Per-ticker Tier-1 at h=22
| model | horizon | ticker | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| STAR-HAR | 22 | EEM | 2060 | 0.2307 | 0.6664 | 0.5448 | -0.3025 | 0.8893 | 0.4869 | 0.0008 |
| STAR-HAR | 22 | GLD | 2060 | 0.1825 | 0.5576 | 0.4411 | -0.1618 | 0.8553 | 0.4665 | 0.0004 |
| STAR-HAR | 22 | HYG | 2060 | 0.6567 | 0.9654 | 0.7842 | -0.5749 | 0.9330 | 0.5107 | 0.0002 |
| STAR-HAR | 22 | IWM | 2060 | 0.2613 | 0.5771 | 0.4391 | -0.1063 | 0.9150 | 0.5180 | 0.0010 |
| STAR-HAR | 22 | QQQ | 2060 | 0.3040 | 0.6091 | 0.4493 | -0.0081 | 0.8922 | 0.5947 | 0.0009 |
| STAR-HAR | 22 | SPY | 2060 | 0.3932 | 0.7248 | 0.5751 | -0.2212 | 0.9107 | 0.5218 | 0.0007 |
| STAR-HAR | 22 | TLT | 2060 | 0.1986 | 0.5170 | 0.3805 | -0.0837 | 0.8961 | 0.5005 | 0.0003 |
| STAR-HAR | 22 | XLE | 2060 | 0.2632 | 0.5466 | 0.3966 | -0.0884 | 0.9223 | 0.5908 | 0.0015 |
| STAR-HAR | 22 | XLF | 2060 | 0.3471 | 0.7222 | 0.5943 | -0.3554 | 0.9422 | 0.5272 | 0.0011 |
| STAR-HAR | 22 | XLK | 2060 | 0.3088 | 0.6094 | 0.4519 | -0.0188 | 0.9039 | 0.5791 | 0.0011 |

## Pooled by group
| model | group | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| STAR-HAR | emerging_markets | 10330 | 0.2875 | 0.7782 | 0.6258 | -0.3615 | 0.8798 | 0.4632 | 0.0006 |
| STAR-HAR | high_yield_credit | 10330 | 0.5220 | 0.9305 | 0.7593 | -0.5405 | 0.9193 | 0.5112 | 0.0001 |
| STAR-HAR | oil_and_energy | 10330 | 0.2402 | 0.5623 | 0.4173 | -0.1102 | 0.9119 | 0.5582 | 0.0011 |
| STAR-HAR | precious_metals | 10330 | 0.2425 | 0.6883 | 0.5384 | -0.2333 | 0.8660 | 0.4557 | 0.0003 |
| STAR-HAR | us_cyclicals_sector | 10330 | 0.2935 | 0.7017 | 0.5669 | -0.3316 | 0.9316 | 0.5330 | 0.0008 |
| STAR-HAR | us_large_cap_equity | 20660 | 0.3038 | 0.6788 | 0.5251 | -0.1491 | 0.8990 | 0.5291 | 0.0006 |
| STAR-HAR | us_rates_and_ig_credit | 10330 | 0.2069 | 0.5867 | 0.4472 | -0.1294 | 0.8917 | 0.4927 | 0.0002 |
| STAR-HAR | us_small_cap_equity | 10330 | 0.2361 | 0.5870 | 0.4499 | -0.1303 | 0.9055 | 0.5207 | 0.0007 |
| STAR-HAR | us_technology_sector | 10330 | 0.2770 | 0.6222 | 0.4728 | -0.0523 | 0.9027 | 0.5401 | 0.0008 |

---

## Model metadata (human-only fields, MODEL_PLAN §5)

- **Model:** STAR-HAR (Smooth-Transition HAR), catalog model 30, Track E. File `candidate_models/star_har.py`, class `STARHAR`, `name="STAR-HAR"`. Pattern P1 (`_AttachMixin` + `_LinearLogHAR`).
- **Transition variable:** `vix_pctile` — EXPANDING percentile rank of the VIX level, per ticker, over the full point-in-time series (for each row, mean(at-or-before-date vix <= today's vix), in (0,1]). Built ONCE on the full `inputs.parquet` series and JOINed by (ticker,date) via `_AttachMixin` (leak-safe; never recomputed on the predict slice). `vix` is in inputs.parquet.
- **Transition form:** logistic `g = 1 / (1 + exp(-slope·(vix_pctile − threshold)))`, in [0,1]. g→0 calm regime, g→1 stressed regime.
- **Frozen hyperparameters (catalog spec, NOT tuned on OOS):** slope = 10.0, threshold = 0.5 (median percentile).
- **Interaction columns:** `log_rv_d__x_g`, `log_rv_w__x_g`, `log_rv_m__x_g` = each HAR feature × g. Built AFTER the join (HAR features live on X post-`build_features`, not in raw inputs).
- **Features used (`needs`):** `log_rv_d, log_rv_w, log_rv_m` (HAR_FEATURES) + `vix_pctile` + the 3 interaction columns. One log-OLS per (ticker,horizon) on this augmented design; lognormal quantiles via base `_LinearLogHAR`.
- **Coverage:** all 10 clean_core tickers × all 5 horizons {1,5,10,22,42}; 2081 rows per (ticker,h=22). No coverage warnings.
- **OOS span:** 2018-01-02 → 2026-05-21. clean_core OOS rows: 104,050.
- **Wall-clock:** ~10.3 s (clean_core walk-forward). **Device:** CPU (no GPU). **Seed:** none required (deterministic OLS; np.random only in synthetic test, seed=0).
- **Libraries:** python 3.12.13, polars 1.41.1, numpy 2.4.6, scipy 1.17.1; macOS-15.3.1-arm64 (Apple Silicon arm).
