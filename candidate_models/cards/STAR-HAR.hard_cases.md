# STAR-HAR — Self Stats
_universe=`hard_cases` · primary horizon h=22 · predictions=`execution/data/predictions/STAR-HAR.parquet` · generated 2026-06-03T22:10:41Z_

_Self-only metrics — no leaderboard rank, no DM test, no MCS, no §9 status._
_Cross-model comparison is produced by the final `rv_eval.evaluator` pass._

## Tier-1 pooled by horizon (§3)
| model | horizon | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| STAR-HAR | 1 | 8067 | 0.3368 | 0.7854 | 0.6192 | -0.2973 | 0.8986 | 0.5127 | 0.0004 |
| STAR-HAR | 5 | 8005 | 0.2716 | 0.6742 | 0.5169 | -0.2079 | 0.8851 | 0.5057 | 0.0020 |
| STAR-HAR | 10 | 7980 | 0.2747 | 0.6728 | 0.5132 | -0.1891 | 0.8697 | 0.4992 | 0.0040 |
| STAR-HAR | 22 | 7920 | 0.2936 | 0.6740 | 0.5158 | -0.1535 | 0.8606 | 0.4811 | 0.0086 |
| STAR-HAR | 42 | 7781 | 0.3129 | 0.6682 | 0.5081 | -0.1155 | 0.8449 | 0.4738 | 0.0149 |

## §5 IV-incremental skill (per horizon)
| model | horizon | n | slope | t_slope | sign_acc | qlike_model | qlike_iv | qlike_gain_vs_iv |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| STAR-HAR | 1 | 7903 | 1.0092 | 30.9184 | 0.6857 | 0.3295 | 0.3596 | 0.0301 |
| STAR-HAR | 5 | 7860 | 0.7907 | 25.4790 | 0.6382 | 0.2676 | 0.2625 | -0.0052 |
| STAR-HAR | 10 | 7835 | 0.8077 | 29.3913 | 0.5958 | 0.2715 | 0.2543 | -0.0173 |
| STAR-HAR | 22 | 7775 | 0.8073 | 38.9361 | 0.5483 | 0.2904 | 0.2732 | -0.0172 |
| STAR-HAR | 42 | 7654 | 0.8931 | 59.6939 | 0.5567 | 0.3150 | 0.3135 | -0.0015 |

## §6 Conditional bias by IV-percentile bucket (h=22)
| model | horizon | iv_pctile_bucket | n | qlike | log_bias |
| --- | --- | --- | --- | --- | --- |
| STAR-HAR | 22 | 0 | 1973 | 0.3072 | -0.2713 |
| STAR-HAR | 22 | 1 | 1263 | 0.2448 | -0.1621 |
| STAR-HAR | 22 | 2 | 1355 | 0.2445 | -0.1019 |
| STAR-HAR | 22 | 3 | 1460 | 0.2623 | -0.1235 |
| STAR-HAR | 22 | 4 | 1725 | 0.3646 | -0.0372 |

## §6 Post-shock calibration (h=22)
| model | horizon | bias_all | qlike_all | bias_postshock | qlike_postshock | n_postshock | trap_flag |
| --- | --- | --- | --- | --- | --- | --- | --- |
| STAR-HAR | 22 | -0.1535 | 0.2936 | -0.1954 | 0.2998 | 1461 |  |

## Per-ticker Tier-1 at h=22
| model | horizon | ticker | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| STAR-HAR | 22 | IBIT | 496 | 0.2702 | 0.8543 | 0.6851 | -0.5321 | 0.6552 | 0.4093 | 0.0056 |
| STAR-HAR | 22 | KRE | 2060 | 0.3166 | 0.6075 | 0.4511 | -0.1261 | 0.9286 | 0.5544 | 0.0017 |
| STAR-HAR | 22 | MSOS | 1244 | 0.2628 | 0.6263 | 0.4702 | 0.0882 | 0.8135 | 0.4920 | 0.0069 |
| STAR-HAR | 22 | USO | 2060 | 0.2528 | 0.5902 | 0.4448 | -0.0266 | 0.8364 | 0.4417 | 0.0029 |
| STAR-HAR | 22 | UVXY | 2060 | 0.3357 | 0.7853 | 0.6381 | -0.3627 | 0.8947 | 0.4578 | 0.0232 |

## Pooled by group
| model | group | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| STAR-HAR | crypto | 2511 | 0.3181 | 0.9106 | 0.7369 | -0.5846 | 0.8136 | 0.4906 | 0.0031 |
| STAR-HAR | long_volatility_vix | 10330 | 0.3259 | 0.7999 | 0.6519 | -0.3756 | 0.8876 | 0.4631 | 0.0158 |
| STAR-HAR | oil_and_energy | 10330 | 0.2893 | 0.6567 | 0.4986 | -0.0976 | 0.8384 | 0.4478 | 0.0022 |
| STAR-HAR | us_cannabis | 6252 | 0.3003 | 0.6294 | 0.4674 | 0.0149 | 0.8472 | 0.5219 | 0.0048 |
| STAR-HAR | us_cyclicals_sector | 10330 | 0.2722 | 0.5967 | 0.4461 | -0.1378 | 0.9191 | 0.5576 | 0.0012 |

---

## Model metadata (human-only fields, MODEL_PLAN §5)

- **Model:** STAR-HAR (Smooth-Transition HAR), catalog model 30, Track E. File `candidate_models/star_har.py`, class `STARHAR`, `name="STAR-HAR"`. Pattern P1 (`_AttachMixin` + `_LinearLogHAR`).
- **Transition variable:** `vix_pctile` — EXPANDING percentile rank of the VIX level, per ticker, over the full point-in-time series (for each row, mean(at-or-before-date vix <= today's vix), in (0,1]). Built ONCE on the full `inputs.parquet` series and JOINed by (ticker,date) via `_AttachMixin` (leak-safe; never recomputed on the predict slice). `vix` is in inputs.parquet.
- **Transition form:** logistic `g = 1 / (1 + exp(-slope·(vix_pctile − threshold)))`, in [0,1]. g→0 calm regime, g→1 stressed regime.
- **Frozen hyperparameters (catalog spec, NOT tuned on OOS):** slope = 10.0, threshold = 0.5 (median percentile).
- **Interaction columns:** `log_rv_d__x_g`, `log_rv_w__x_g`, `log_rv_m__x_g` = each HAR feature × g. Built AFTER the join (HAR features live on X post-`build_features`, not in raw inputs).
- **Features used (`needs`):** `log_rv_d, log_rv_w, log_rv_m` (HAR_FEATURES) + `vix_pctile` + the 3 interaction columns. One log-OLS per (ticker,horizon) on this augmented design; lognormal quantiles via base `_LinearLogHAR`.
- **Coverage:** all 5 hard_cases tickers (UVXY, MSOS, IBIT, USO, KRE) × all 5 horizons {1,5,10,22,42}. Shorter histories (IBIT n=496, MSOS n=1244 at h=22) reflect later listing dates, not a model gap. No coverage warnings.
- **OOS span:** 2018-01-02 → 2026-05-21. hard_cases OOS rows: 40,128.
- **Wall-clock:** ~5.6 s (hard_cases walk-forward). **Device:** CPU (no GPU). **Seed:** none required (deterministic OLS; np.random only in synthetic test, seed=0).
- **Libraries:** python 3.12.13, polars 1.41.1, numpy 2.4.6, scipy 1.17.1; macOS-15.3.1-arm64 (Apple Silicon arm).
