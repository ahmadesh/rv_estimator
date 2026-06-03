# EWMA — Model Card

## Identity
- Model number (from MODEL_PLAN.md): 1
- Class: rv_eval.model_contract:EWMA
- Tier: Baseline (reference benchmark — already coded in the harness)
- Implemented by: swarm worker, run 2026-05-31

## Configuration
- Features used (by name): `ewma_rv`
- Hyperparameters (frozen):
  - lambda = 0.94 (RiskMetrics convention; NOT tuned)
- Forecast rule: `rv_hat = h * ewma_rv`, lognormal-mean corrected (`m = h * src * exp(0.5 * s^2)`); `sigma` = std of log-residuals on the fit window. Quantiles via `_lognormal_quantiles(m, s)`.
- HP selection: N/A — EWMA has no free hyperparameters. λ=0.94 is the fixed RiskMetrics convention per MODEL_PLAN §4.1 / §4 "Hyperparameter selection" and is not searched.
- Library versions: python 3.12.13, polars 1.41.1, numpy 2.4.6
- Random seed: N/A (deterministic, no stochastic fitting)

## Training
- Universes run: clean_core (SPY, QQQ, IWM, XLK, XLF, XLE, TLT, GLD, HYG, EEM), hard_cases (UVXY, MSOS, IBIT, USO, KRE)
- Walk-forward: purged + embargoed monthly-refit rolling-origin (harness default), OOS_START=2018-01-01, span 2018-01-02 to 2026-05-22, horizons {1,5,10,22,42}
- New OOS preds: clean_core 105,450 rows; hard_cases 41,760 rows; combined file 147,210 rows
- Wall-clock time: clean_core 6.5s; hard_cases 3.6s
- Device: cpu
- Convergence notes / per-ticker warnings: none — closed-form scaling, no optimizer. All 15 tickers × 5 horizons covered; `rv_hat` 100% finite across the full prediction set.

---

# EWMA — Self Stats
_universe=`clean_core` · primary horizon h=22 · predictions=`execution/data/predictions/EWMA.parquet` · generated 2026-06-01T02:58:50Z_

_Self-only metrics — no leaderboard rank, no DM test, no MCS, no §9 status._
_Cross-model comparison is produced by the final `rv_eval.evaluator` pass._

## Tier-1 pooled by horizon (§3)
| model | horizon | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EWMA | 1 | 21080 | 0.4410 | 1.0959 | 0.8989 | -0.6912 | 0.8681 | 0.4546 | 0.0000 |
| EWMA | 5 | 21040 | 0.2900 | 0.8108 | 0.6458 | -0.4152 | 0.8918 | 0.5208 | 0.0002 |
| EWMA | 10 | 20990 | 0.2938 | 0.7803 | 0.6126 | -0.3606 | 0.8960 | 0.5509 | 0.0004 |
| EWMA | 22 | 20870 | 0.3841 | 0.8090 | 0.6193 | -0.3264 | 0.8967 | 0.5743 | 0.0010 |
| EWMA | 42 | 20670 | 0.5323 | 0.8812 | 0.6567 | -0.3148 | 0.8975 | 0.5907 | 0.0020 |

## §5 IV-incremental skill (per horizon)
| model | horizon | n | slope | t_slope | sign_acc | qlike_model | qlike_iv | qlike_gain_vs_iv |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EWMA | 1 | 20820 | 0.2655 | 18.6758 | 0.3600 | 0.4407 | 0.3276 | -0.1130 |
| EWMA | 5 | 20780 | 0.1470 | 13.4530 | 0.4176 | 0.2906 | 0.2079 | -0.0827 |
| EWMA | 10 | 20730 | 0.0379 | 3.7121 | 0.4280 | 0.2949 | 0.2187 | -0.0762 |
| EWMA | 22 | 20610 | -0.1109 | -12.6055 | 0.4289 | 0.3861 | 0.3396 | -0.0465 |
| EWMA | 42 | 20410 | -0.1026 | -14.9762 | 0.4262 | 0.5369 | 0.4697 | -0.0672 |

## §6 Conditional bias by IV-percentile bucket (h=22)
| model | horizon | iv_pctile_bucket | n | qlike | log_bias |
| --- | --- | --- | --- | --- | --- |
| EWMA | 22 | 0 | 5500 | 0.2092 | -0.3291 |
| EWMA | 22 | 1 | 3449 | 0.3379 | -0.3522 |
| EWMA | 22 | 2 | 3439 | 0.4740 | -0.3270 |
| EWMA | 22 | 3 | 3533 | 0.4535 | -0.3419 |
| EWMA | 22 | 4 | 4949 | 0.4986 | -0.2937 |

## §6 Post-shock calibration (h=22)
| model | horizon | bias_all | qlike_all | bias_postshock | qlike_postshock | n_postshock | trap_flag |
| --- | --- | --- | --- | --- | --- | --- | --- |
| EWMA | 22 | -0.3264 | 0.3841 | -0.3523 | 0.4925 | 3986 |  |

## Per-ticker Tier-1 at h=22
| model | horizon | ticker | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EWMA | 22 | EEM | 2087 | 0.2860 | 0.8143 | 0.6772 | -0.4706 | 0.9621 | 0.7163 | 0.0010 |
| EWMA | 22 | GLD | 2087 | 0.1945 | 0.5703 | 0.4466 | -0.1097 | 0.8539 | 0.4595 | 0.0004 |
| EWMA | 22 | HYG | 2087 | 0.7952 | 1.3339 | 1.1569 | -1.0023 | 0.9794 | 0.7892 | 0.0003 |
| EWMA | 22 | IWM | 2087 | 0.3473 | 0.6785 | 0.5122 | -0.1819 | 0.8534 | 0.5122 | 0.0012 |
| EWMA | 22 | QQQ | 2087 | 0.3538 | 0.8297 | 0.6711 | -0.4041 | 0.9300 | 0.6397 | 0.0011 |
| EWMA | 22 | SPY | 2087 | 0.5193 | 0.8633 | 0.6704 | -0.2862 | 0.8495 | 0.4916 | 0.0009 |
| EWMA | 22 | TLT | 2087 | 0.2217 | 0.5696 | 0.4131 | -0.1323 | 0.8864 | 0.4873 | 0.0004 |
| EWMA | 22 | XLE | 2087 | 0.3322 | 0.6297 | 0.4649 | -0.1583 | 0.8946 | 0.5601 | 0.0018 |
| EWMA | 22 | XLF | 2087 | 0.4341 | 0.7703 | 0.6017 | -0.2852 | 0.8960 | 0.5688 | 0.0013 |
| EWMA | 22 | XLK | 2087 | 0.3566 | 0.7536 | 0.5785 | -0.2327 | 0.8620 | 0.5180 | 0.0014 |

## Pooled by group
| model | group | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EWMA | emerging_markets | 10465 | 0.3700 | 0.9762 | 0.7950 | -0.5990 | 0.9467 | 0.6353 | 0.0007 |
| EWMA | high_yield_credit | 10465 | 0.7577 | 1.3726 | 1.1944 | -1.0577 | 0.9803 | 0.7546 | 0.0002 |
| EWMA | oil_and_energy | 10465 | 0.3189 | 0.6699 | 0.5086 | -0.2293 | 0.8824 | 0.5253 | 0.0014 |
| EWMA | precious_metals | 10465 | 0.2603 | 0.7535 | 0.5792 | -0.2735 | 0.8472 | 0.4540 | 0.0003 |
| EWMA | us_cyclicals_sector | 10465 | 0.4028 | 0.8116 | 0.6376 | -0.3623 | 0.8976 | 0.5313 | 0.0010 |
| EWMA | us_large_cap_equity | 20930 | 0.4228 | 0.9072 | 0.7251 | -0.4364 | 0.8800 | 0.5212 | 0.0007 |
| EWMA | us_rates_and_ig_credit | 10465 | 0.2399 | 0.6774 | 0.5085 | -0.2428 | 0.8702 | 0.4730 | 0.0003 |
| EWMA | us_small_cap_equity | 10465 | 0.3289 | 0.7245 | 0.5602 | -0.2611 | 0.8551 | 0.4806 | 0.0009 |
| EWMA | us_technology_sector | 10465 | 0.3541 | 0.8119 | 0.6361 | -0.3247 | 0.8602 | 0.4833 | 0.0010 |
