# EWMA — Model Card (hard_cases)

## Identity
- Model number (from MODEL_PLAN.md): 1
- Class: rv_eval.model_contract:EWMA
- Tier: Baseline (reference benchmark — already coded in the harness)
- Implemented by: swarm worker, run 2026-05-31

## Configuration
- Features used (by name): `ewma_rv`
- Hyperparameters (frozen):
  - lambda = 0.94 (RiskMetrics convention; NOT tuned)
- Forecast rule: `rv_hat = h * ewma_rv`, lognormal-mean corrected; `sigma` = std of log-residuals; quantiles via `_lognormal_quantiles(m, s)`.
- HP selection: N/A — no free hyperparameters; λ=0.94 fixed by RiskMetrics convention.
- Library versions: python 3.12.13, polars 1.41.1, numpy 2.4.6
- Random seed: N/A (deterministic)

## Training
- Universe (this card): hard_cases (UVXY, MSOS, IBIT, USO, KRE)
- Walk-forward: purged + embargoed monthly-refit rolling-origin, OOS_START=2018-01-01, horizons {1,5,10,22,42}
- New OOS preds: hard_cases 41,760 rows (combined file 147,210 rows)
- Wall-clock time: hard_cases 3.6s
- Device: cpu
- Convergence notes / per-ticker warnings: none — closed-form, no optimizer. All 5 hard-case tickers × 5 horizons covered, `rv_hat` finite. IBIT (short options history) and MSOS (thin) ran without issue since EWMA only needs `ewma_rv` (no IV features); coverage limited only by each ticker's own price history within the OOS window.

---

# EWMA — Self Stats
_universe=`hard_cases` · primary horizon h=22 · predictions=`execution/data/predictions/EWMA.parquet` · generated 2026-06-01T02:58:50Z_

_Self-only metrics — no leaderboard rank, no DM test, no MCS, no §9 status._
_Cross-model comparison is produced by the final `rv_eval.evaluator` pass._

## Tier-1 pooled by horizon (§3)
| model | horizon | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EWMA | 1 | 8373 | 0.4748 | 1.1089 | 0.8893 | -0.6790 | 0.8582 | 0.4387 | 0.0006 |
| EWMA | 5 | 8339 | 0.3450 | 0.8255 | 0.6532 | -0.3955 | 0.8701 | 0.4749 | 0.0024 |
| EWMA | 10 | 8314 | 0.3386 | 0.7795 | 0.6099 | -0.3209 | 0.8768 | 0.4912 | 0.0048 |
| EWMA | 22 | 8234 | 0.3662 | 0.7612 | 0.5869 | -0.2398 | 0.8759 | 0.4983 | 0.0105 |
| EWMA | 42 | 8100 | 0.4016 | 0.7682 | 0.5786 | -0.1800 | 0.8544 | 0.5127 | 0.0193 |

## §5 IV-incremental skill (per horizon)
| model | horizon | n | slope | t_slope | sign_acc | qlike_model | qlike_iv | qlike_gain_vs_iv |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EWMA | 1 | 7955 | 0.0671 | 2.6906 | 0.4725 | 0.4433 | 0.3620 | -0.0813 |
| EWMA | 5 | 7935 | 0.0895 | 4.8552 | 0.5133 | 0.3343 | 0.2634 | -0.0710 |
| EWMA | 10 | 7910 | 0.0698 | 4.3243 | 0.5143 | 0.3340 | 0.2549 | -0.0791 |
| EWMA | 22 | 7850 | 0.0005 | 0.0361 | 0.5032 | 0.3664 | 0.2735 | -0.0929 |
| EWMA | 42 | 7739 | 0.0791 | 7.0562 | 0.5041 | 0.4069 | 0.3146 | -0.0923 |

## §6 Conditional bias by IV-percentile bucket (h=22)
| model | horizon | iv_pctile_bucket | n | qlike | log_bias |
| --- | --- | --- | --- | --- | --- |
| EWMA | 22 | 0 | 2085 | 0.3542 | -0.2440 |
| EWMA | 22 | 1 | 1279 | 0.3009 | -0.2110 |
| EWMA | 22 | 2 | 1369 | 0.3025 | -0.1978 |
| EWMA | 22 | 3 | 1471 | 0.3415 | -0.2505 |
| EWMA | 22 | 4 | 1752 | 0.5054 | -0.2395 |

## §6 Post-shock calibration (h=22)
| model | horizon | bias_all | qlike_all | bias_postshock | qlike_postshock | n_postshock | trap_flag |
| --- | --- | --- | --- | --- | --- | --- | --- |
| EWMA | 22 | -0.2398 | 0.3662 | -0.3377 | 0.4202 | 1535 |  |

## Per-ticker Tier-1 at h=22
| model | horizon | ticker | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EWMA | 22 | IBIT | 620 | 0.2209 | 0.7697 | 0.6281 | -0.4441 | 0.9726 | 0.6548 | 0.0044 |
| EWMA | 22 | KRE | 2087 | 0.4040 | 0.6938 | 0.5208 | -0.2042 | 0.9176 | 0.5443 | 0.0021 |
| EWMA | 22 | MSOS | 1353 | 0.2507 | 0.6844 | 0.5526 | -0.1622 | 0.8293 | 0.4353 | 0.0075 |
| EWMA | 22 | USO | 2087 | 0.2956 | 0.6812 | 0.5135 | -0.1266 | 0.8179 | 0.4312 | 0.0033 |
| EWMA | 22 | UVXY | 2087 | 0.5170 | 0.9277 | 0.7363 | -0.3780 | 0.8936 | 0.5137 | 0.0300 |

## Pooled by group
| model | group | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EWMA | crypto | 3132 | 0.4210 | 1.1608 | 0.8957 | -0.7449 | 0.9687 | 0.6373 | 0.0032 |
| EWMA | long_volatility_vix | 10465 | 0.5003 | 1.0168 | 0.8193 | -0.5114 | 0.8755 | 0.4785 | 0.0210 |
| EWMA | oil_and_energy | 10465 | 0.3383 | 0.7771 | 0.5970 | -0.2495 | 0.8081 | 0.4211 | 0.0026 |
| EWMA | us_cannabis | 6833 | 0.2969 | 0.7421 | 0.5913 | -0.2775 | 0.8493 | 0.4540 | 0.0051 |
| EWMA | us_cyclicals_sector | 10465 | 0.3644 | 0.7222 | 0.5558 | -0.2764 | 0.8991 | 0.5217 | 0.0015 |
