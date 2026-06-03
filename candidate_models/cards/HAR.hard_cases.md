# HAR — Model Card (hard_cases)

## Identity
- Model number (from MODEL_PLAN.md): 2
- Class: `rv_eval.model_contract:HAR`
- Model `name`: `HAR`
- Tier: Baseline (the §9 anchor baseline)
- Implemented by: pre-coded benchmark (no implementation work); run 2026-05-31

## Configuration
- Features used (HAR_FEATURES): `log_rv_d`, `log_rv_w`, `log_rv_m`
- Model form: per-(ticker, horizon) OLS of `log(target_var)` on HAR lags + intercept; direct-h, lognormal-mean corrected. Base class `_LinearLogHAR`, `min_obs = 100`.
- Hyperparameters: none (plain log-OLS — no free hyperparameters)
- HP selection: N/A
- Random seed: N/A (deterministic)
- Library versions: python 3.12.13, numpy 2.4.6, scipy 1.17.1, polars 1.41.1

## Training
- Universes run: clean_core, hard_cases (this card covers hard_cases)
- Wall-clock time: hard_cases 4.1s (clean_core 7.8s)
- Device: cpu (Apple Silicon arm64, macOS 15.3.1)
- OOS span: 2018-01-02 .. 2026-05-22
- Predictions parquet: `execution/data/predictions/HAR.parquet`
- Rows: hard_cases 40,810 (of 146,260 total in the shared parquet)
- Coverage: all 5 hard-case tickers × all 5 horizons fit. None dropped/imputed.
  - IBIT: data-starved (~2y options); OOS begins 2024-03 (h=1/5) to 2024-05 (h=42); ~517–559 rows/horizon. All horizons covered; closed-form OLS converged.
  - MSOS: thin but covered (1,270 rows at h=22).
- Convergence notes: none — closed-form OLS, no iterative fit, no NaN/convergence warnings.

---
_universe=`hard_cases` · primary horizon h=22 · predictions=`execution/data/predictions/HAR.parquet` · generated 2026-06-01T03:00:59Z_

_Self-only metrics — no leaderboard rank, no DM test, no MCS, no §9 status._
_Cross-model comparison is produced by the final `rv_eval.evaluator` pass._

## Tier-1 pooled by horizon (§3)
| model | horizon | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR | 1 | 8196 | 0.3419 | 0.7751 | 0.6092 | -0.2648 | 0.8981 | 0.5198 | 0.0004 |
| HAR | 5 | 8153 | 0.2752 | 0.6635 | 0.5058 | -0.1788 | 0.8912 | 0.5186 | 0.0019 |
| HAR | 10 | 8108 | 0.2797 | 0.6623 | 0.5037 | -0.1637 | 0.8775 | 0.5102 | 0.0039 |
| HAR | 22 | 8048 | 0.2985 | 0.6631 | 0.5097 | -0.1393 | 0.8668 | 0.4876 | 0.0084 |
| HAR | 42 | 7905 | 0.3201 | 0.6683 | 0.5115 | -0.1165 | 0.8491 | 0.4732 | 0.0147 |

## §5 IV-incremental skill (per horizon)
| model | horizon | n | slope | t_slope | sign_acc | qlike_model | qlike_iv | qlike_gain_vs_iv |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR | 1 | 7906 | 0.9328 | 25.2140 | 0.6939 | 0.3352 | 0.3595 | 0.0243 |
| HAR | 5 | 7863 | 0.7470 | 23.0104 | 0.6482 | 0.2721 | 0.2624 | -0.0097 |
| HAR | 10 | 7838 | 0.7727 | 28.1140 | 0.6064 | 0.2773 | 0.2542 | -0.0232 |
| HAR | 22 | 7778 | 0.8087 | 39.6595 | 0.5595 | 0.2984 | 0.2732 | -0.0252 |
| HAR | 42 | 7657 | 0.9237 | 61.1887 | 0.5536 | 0.3249 | 0.3134 | -0.0115 |

## §6 Conditional bias by IV-percentile bucket (h=22)
| model | horizon | iv_pctile_bucket | n | qlike | log_bias |
| --- | --- | --- | --- | --- | --- |
| HAR | 22 | 0 | 2078 | 0.3137 | -0.2501 |
| HAR | 22 | 1 | 1264 | 0.2487 | -0.1522 |
| HAR | 22 | 2 | 1355 | 0.2488 | -0.0916 |
| HAR | 22 | 3 | 1460 | 0.2642 | -0.1114 |
| HAR | 22 | 4 | 1727 | 0.3860 | -0.0188 |

## §6 Post-shock calibration (h=22)
| model | horizon | bias_all | qlike_all | bias_postshock | qlike_postshock | n_postshock | trap_flag |
| --- | --- | --- | --- | --- | --- | --- | --- |
| HAR | 22 | -0.1393 | 0.2985 | -0.1839 | 0.3200 | 1487 |  |

## Per-ticker Tier-1 at h=22
| model | horizon | ticker | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR | 22 | IBIT | 517 | 0.2168 | 0.7520 | 0.6329 | -0.5132 | 0.7195 | 0.4468 | 0.0038 |
| HAR | 22 | KRE | 2087 | 0.3425 | 0.6137 | 0.4505 | -0.1041 | 0.9305 | 0.5611 | 0.0017 |
| HAR | 22 | MSOS | 1270 | 0.2600 | 0.6292 | 0.4811 | 0.0507 | 0.8228 | 0.4780 | 0.0069 |
| HAR | 22 | USO | 2087 | 0.2665 | 0.6018 | 0.4537 | -0.0181 | 0.8261 | 0.4356 | 0.0029 |
| HAR | 22 | UVXY | 2087 | 0.3303 | 0.7589 | 0.6119 | -0.3189 | 0.9070 | 0.4820 | 0.0227 |

## Pooled by group
| model | group | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR | crypto | 2633 | 0.2959 | 0.8544 | 0.6992 | -0.5510 | 0.8507 | 0.5009 | 0.0026 |
| HAR | long_volatility_vix | 10465 | 0.3205 | 0.7711 | 0.6209 | -0.3150 | 0.8969 | 0.4885 | 0.0154 |
| HAR | oil_and_energy | 10465 | 0.3026 | 0.6644 | 0.5044 | -0.0865 | 0.8332 | 0.4493 | 0.0022 |
| HAR | us_cannabis | 6382 | 0.2953 | 0.6318 | 0.4766 | -0.0166 | 0.8562 | 0.5096 | 0.0047 |
| HAR | us_cyclicals_sector | 10465 | 0.2926 | 0.6049 | 0.4479 | -0.1185 | 0.9194 | 0.5643 | 0.0013 |
