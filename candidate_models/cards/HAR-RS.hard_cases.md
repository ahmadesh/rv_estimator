# HAR-RS — Model Card

## Identity
- Model number (from MODEL_PLAN.md): 5
- Class: candidate_models.har_rs:HARRS
- Tier: Modern HAR (semivariance + jump)
- Implemented by: swarm worker, 2026-06-01

## Configuration
- Features used (list, by name): log_rv_d, log_rv_w, log_rv_m, rs_minus_5d, rs_plus_5d, jump_5d (= HAR_RS_FEATURES)
- Hyperparameters (key=value, one per line — the FROZEN values used): none (plain per-(ticker, horizon) log-OLS via _LinearLogHAR; min_obs=100 inherited)
- HP selection (models 8–11): N/A — model 5 has no free hyperparameters.
- Library version(s): python 3.12.13, numpy 2.4.6, polars 1.41.1, scipy 1.17.1
- Random seed (if applicable): N/A (deterministic OLS via numpy.linalg.lstsq)

## Training
- Universes run: clean_core, hard_cases
- Walk-forward folds: monthly refit, expanding window, OOS 2018-01-02 .. 2026-05-22 (per rv_eval.config)
- Wall-clock time: clean_core 8s, hard_cases 4s
- Device: cpu (Apple Silicon arm64, macOS 15.3.1)
- Convergence notes / per-ticker warnings: no convergence warnings (closed-form OLS). Full (ticker × horizon) coverage on hard_cases — UVXY, MSOS, IBIT, USO, KRE all present at all 5 horizons, none dropped or imputed. Shorter-history hard cases have fewer OOS rows: IBIT 2,713 and MSOS 6,462 (vs 10,545 for UVXY/USO/KRE).
- OOS row counts: clean_core 105,450; hard_cases 40,810; file total 146,260.

# HAR-RS — Self Stats
_universe=`hard_cases` · primary horizon h=22 · predictions=`execution/data/predictions/HAR-RS.parquet` · generated 2026-06-01T03:09:42Z_

_Self-only metrics — no leaderboard rank, no DM test, no MCS, no §9 status._
_Cross-model comparison is produced by the final `rv_eval.evaluator` pass._

## Tier-1 pooled by horizon (§3)
| model | horizon | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-RS | 1 | 8196 | 0.4008 | 0.7992 | 0.6190 | -0.2753 | 0.8951 | 0.5216 | 0.0005 |
| HAR-RS | 5 | 8153 | 0.2961 | 0.6834 | 0.5130 | -0.1799 | 0.8863 | 0.5148 | 0.0026 |
| HAR-RS | 10 | 8108 | 0.2883 | 0.7006 | 0.5112 | -0.1697 | 0.8731 | 0.5059 | 0.0431 |
| HAR-RS | 22 | 8048 | 0.3047 | 0.6860 | 0.5106 | -0.1382 | 0.8636 | 0.4889 | 0.0212 |
| HAR-RS | 42 | 7905 | 0.3339 | 0.7059 | 0.5180 | -0.1087 | 0.8412 | 0.4691 | 0.1153 |

## §5 IV-incremental skill (per horizon)
| model | horizon | n | slope | t_slope | sign_acc | qlike_model | qlike_iv | qlike_gain_vs_iv |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-RS | 1 | 7906 | 0.0815 | 8.2078 | 0.6950 | 0.3950 | 0.3595 | -0.0355 |
| HAR-RS | 5 | 7863 | 0.0038 | 0.9744 | 0.6499 | 0.2937 | 0.2624 | -0.0313 |
| HAR-RS | 10 | 7838 | -0.0002 | -2.1515 | 0.6055 | 0.2863 | 0.2542 | -0.0321 |
| HAR-RS | 22 | 7778 | -0.0015 | -2.5238 | 0.5661 | 0.3062 | 0.2732 | -0.0330 |
| HAR-RS | 42 | 7657 | -0.0003 | -2.2854 | 0.5629 | 0.3400 | 0.3134 | -0.0266 |

## §6 Conditional bias by IV-percentile bucket (h=22)
| model | horizon | iv_pctile_bucket | n | qlike | log_bias |
| --- | --- | --- | --- | --- | --- |
| HAR-RS | 22 | 0 | 2078 | 0.3135 | -0.2477 |
| HAR-RS | 22 | 1 | 1264 | 0.2478 | -0.1448 |
| HAR-RS | 22 | 2 | 1355 | 0.2509 | -0.0819 |
| HAR-RS | 22 | 3 | 1460 | 0.2667 | -0.1032 |
| HAR-RS | 22 | 4 | 1727 | 0.4181 | -0.0513 |

## §6 Post-shock calibration (h=22)
| model | horizon | bias_all | qlike_all | bias_postshock | qlike_postshock | n_postshock | trap_flag |
| --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-RS | 22 | -0.1382 | 0.3047 | -0.2204 | 0.3571 | 1487 |  |

## Per-ticker Tier-1 at h=22
| model | horizon | ticker | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-RS | 22 | IBIT | 517 | 0.1911 | 0.6994 | 0.5670 | -0.4023 | 0.7215 | 0.4255 | 0.0035 |
| HAR-RS | 22 | KRE | 2087 | 0.3437 | 0.6133 | 0.4476 | -0.0980 | 0.9305 | 0.5644 | 0.0018 |
| HAR-RS | 22 | MSOS | 1270 | 0.2690 | 0.6517 | 0.4926 | 0.0328 | 0.7984 | 0.4843 | 0.0074 |
| HAR-RS | 22 | USO | 2087 | 0.2855 | 0.6877 | 0.4627 | -0.0326 | 0.8313 | 0.4480 | 0.0518 |
| HAR-RS | 22 | UVXY | 2087 | 0.3349 | 0.7654 | 0.6184 | -0.3226 | 0.9037 | 0.4729 | 0.0230 |

## Pooled by group
| model | group | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-RS | crypto | 2633 | 0.2885 | 0.8451 | 0.6806 | -0.5076 | 0.8424 | 0.4770 | 0.0024 |
| HAR-RS | long_volatility_vix | 10465 | 0.3831 | 0.7866 | 0.6300 | -0.3162 | 0.8929 | 0.4826 | 0.0157 |
| HAR-RS | oil_and_energy | 10465 | 0.3182 | 0.7453 | 0.5174 | -0.1027 | 0.8333 | 0.4539 | 0.1185 |
| HAR-RS | us_cannabis | 6382 | 0.3074 | 0.6569 | 0.4910 | -0.0241 | 0.8383 | 0.5081 | 0.0051 |
| HAR-RS | us_cyclicals_sector | 10465 | 0.2932 | 0.6046 | 0.4464 | -0.1143 | 0.9181 | 0.5655 | 0.0013 |
