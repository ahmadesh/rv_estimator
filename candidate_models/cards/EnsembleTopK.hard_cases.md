# EnsembleTopK — Self Stats

## Identity
- Model number (from MODEL_PLAN.md): 12
- Class: candidate_models.ensemble_top:EnsembleTopK
- Tier: Ensemble
- Implemented by: swarm worker, 2026-06-01

## Configuration
- Type: post-hoc equal-weight ensemble (combiner over component prediction parquets).
- Components (8 — MODEL_PLAN §4 models 4-11, the non-baseline candidates):
  HARQ, HAR-RS, HAR-CJ, HAR-RS-IV-Q, RealizedGARCH, XGBHARRSIV, LSTMRV, GuyonLekeufackPDV.
- Combination scheme (per (ticker, date, horizon) key, over the components AVAILABLE for that key):
  - rv_hat = equal-weight MEAN of component rv_hat.
  - sigma  = sqrt( mean(component_sigma^2) + var(component_rv_hat) )   [within-model variance + between-model dispersion].
  - q05..q95 = `_lognormal_quantiles(m, s)` with m = combined rv_hat and log-sd
    s = sqrt(log(1 + (sigma/rv_hat)^2))  (exact inverse of the `_PerKeyModel` level-sigma convention).
- Availability rule: a key is kept only if >= 2 components have a prediction for it; otherwise dropped (never imputed).
- Hyperparameters: NONE (equal weights, fixed min-2-components rule). No HP selection / no validation block — N/A.
- Library versions: polars, numpy, scipy (as pinned in uv.lock); scipy.stats.norm via model_contract.
- Random seed: N/A (deterministic combiner).

## Training
- Universes run: clean_core, hard_cases.
- Walk-forward: fit() is a no-op; predict() reads component parquets and joins on this fold's (ticker, date) keys.
- Wall-clock time: clean_core ~6.8s, hard_cases ~6.5s (CPU).
- Device: cpu.
- Components found/used (all 8 present on disk): HARQ, HAR-RS, HAR-CJ, HAR-RS-IV-Q, RealizedGARCH, XGBHARRSIV, LSTMRV, GuyonLekeufackPDV.
- Coverage (hard_cases): 40,998 OOS rows. IBIT is thin (537 rows at h=22, ~2y of options coverage); MSOS thin
  (1,270 rows at h=22). Keys dropped for <2 components: 23, all MSOS (only a single component produced a prediction there).

_universe=`hard_cases` · primary horizon h=22 · predictions=`execution/data/predictions/EnsembleTopK.parquet` · generated 2026-06-01T18:48:48Z_

_Self-only metrics — no leaderboard rank, no DM test, no MCS, no §9 status._
_Cross-model comparison is produced by the final `rv_eval.evaluator` pass._

## Tier-1 pooled by horizon (§3)
| model | horizon | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EnsembleTopK | 1 | 8235 | 0.3746 | 0.9541 | 0.7231 | -0.4687 | 0.9044 | 0.5138 | 0.0006 |
| EnsembleTopK | 5 | 8196 | 0.3635 | 0.9588 | 0.8016 | -0.6549 | 0.9605 | 0.6986 | 0.0024 |
| EnsembleTopK | 10 | 8151 | 0.7081 | 1.5126 | 1.3732 | -1.3046 | 0.9860 | 0.7858 | 0.0080 |
| EnsembleTopK | 22 | 8068 | 2.0151 | 3.0753 | 2.9270 | -2.9192 | 0.9674 | 0.3075 | 0.0407 |
| EnsembleTopK | 42 | 7948 | 3.6625 | 4.7811 | 4.6433 | -4.6433 | 0.4424 | 0.0370 | 0.4258 |

## §5 IV-incremental skill (per horizon)
| model | horizon | n | slope | t_slope | sign_acc | qlike_model | qlike_iv | qlike_gain_vs_iv |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EnsembleTopK | 1 | 7925 | 0.0215 | 3.7538 | 0.6250 | 0.3674 | 0.3600 | -0.0074 |
| EnsembleTopK | 5 | 7886 | 0.0935 | 7.1040 | 0.3970 | 0.3599 | 0.2624 | -0.0975 |
| EnsembleTopK | 10 | 7861 | -0.0018 | -2.1988 | 0.2951 | 0.6993 | 0.2543 | -0.4450 |
| EnsembleTopK | 22 | 7778 | -0.0244 | -7.1260 | 0.2832 | 1.9968 | 0.2732 | -1.7236 |
| EnsembleTopK | 42 | 7678 | -0.0067 | -9.1346 | 0.3141 | 3.6399 | 0.3139 | -3.3260 |

## §6 Conditional bias by IV-percentile bucket (h=22)
| model | horizon | iv_pctile_bucket | n | qlike | log_bias |
| --- | --- | --- | --- | --- | --- |
| EnsembleTopK | 22 | 0 | 2078 | 2.3065 | -3.2436 |
| EnsembleTopK | 22 | 1 | 1264 | 2.1536 | -3.0822 |
| EnsembleTopK | 22 | 2 | 1355 | 2.0155 | -2.9337 |
| EnsembleTopK | 22 | 3 | 1460 | 1.9375 | -2.8340 |
| EnsembleTopK | 22 | 4 | 1727 | 1.5610 | -2.3967 |

## §6 Post-shock calibration (h=22)
| model | horizon | bias_all | qlike_all | bias_postshock | qlike_postshock | n_postshock | trap_flag |
| --- | --- | --- | --- | --- | --- | --- | --- |
| EnsembleTopK | 22 | -2.9192 | 2.0151 | -2.5784 | 1.7151 | 1492 |  |

## Per-ticker Tier-1 at h=22
| model | horizon | ticker | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EnsembleTopK | 22 | IBIT | 537 | 2.3711 | 3.3827 | 3.3280 | -3.3280 | 0.9274 | 0.1881 | 0.0614 |
| EnsembleTopK | 22 | KRE | 2087 | 2.6812 | 3.7093 | 3.6416 | -3.6416 | 0.9535 | 0.0910 | 0.0245 |
| EnsembleTopK | 22 | MSOS | 1270 | 1.5407 | 2.5278 | 2.4291 | -2.4291 | 0.9504 | 0.4787 | 0.0386 |
| EnsembleTopK | 22 | USO | 2087 | 2.3002 | 3.3300 | 3.2389 | -3.2378 | 0.9693 | 0.1543 | 0.0280 |
| EnsembleTopK | 22 | UVXY | 2087 | 1.2609 | 2.2089 | 2.1003 | -2.0714 | 1.0000 | 0.6037 | 0.0656 |

## Pooled by group
| model | group | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EnsembleTopK | crypto | 2735 | 1.5844 | 2.8791 | 2.2956 | -2.2278 | 0.8260 | 0.4099 | 0.1585 |
| EnsembleTopK | long_volatility_vix | 10465 | 1.0119 | 2.0247 | 1.6474 | -1.5328 | 0.9553 | 0.4816 | 0.1126 |
| EnsembleTopK | oil_and_energy | 10465 | 1.5574 | 2.8849 | 2.2372 | -2.1387 | 0.7950 | 0.4499 | 0.0785 |
| EnsembleTopK | us_cannabis | 6468 | 1.1851 | 2.3122 | 1.8068 | -1.6931 | 0.8956 | 0.4983 | 0.0898 |
| EnsembleTopK | us_cyclicals_sector | 10465 | 1.7504 | 3.1587 | 2.4482 | -2.3748 | 0.7940 | 0.4821 | 0.0751 |
