# EnsembleTopK — Self Stats

## Identity
- Model number (from MODEL_PLAN.md): 12
- Class: candidate_models.ensemble_top:EnsembleTopK
- Tier: Ensemble
- Implemented by: swarm worker, 2026-06-01; components refined in the comparison pass, 2026-06-02.

## Configuration
- Type: post-hoc equal-weight ensemble (combiner over component prediction parquets).
- Components (top-K = 4, refined after the comparison pass — MODEL_PLAN §4.12):
  HAR-RS-IV-Q, HARQ, HAR-RS, HAR-CJ.
  The first swarm pass equal-weighted all 8 non-baseline candidates (models 4–11). Because the
  combination is an arithmetic mean of rv_hat in level space, the two candidates whose forecasts
  blow up — RealizedGARCH (rv_hat up to ~1e21 at h=42) and GuyonLekeufackPDV — dragged the mean
  to ~1e18 and the ensemble scored worse than RandomWalk (pooled QLIKE ~2.6). Both are also the
  two worst standalone candidates by pooled QLIKE on both universes, so they were dropped, not
  clipped. XGBHARRSIV and LSTMRV were dropped too (no blow-up, but they trail the HAR-family four
  by a clear margin and only dilute the combiner). What remains is the genuine top-K.
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
- Wall-clock time: clean_core ~4.0s, hard_cases ~3.7s (CPU).
- Device: cpu.
- Components found/used (all 4 present on disk): HAR-RS-IV-Q, HARQ, HAR-RS, HAR-CJ.
- Coverage: 146,260 OOS rows total across both universes (105,450 clean_core + 40,810 hard_cases).
  Per-key component count: 142,497 keys used all 4 components; 3,763 keys used exactly 3.
  The 4 HAR-family components have near-identical coverage, so the >=2-component floor never binds and no key is dropped.

_universe=`clean_core` · primary horizon h=22 · predictions=`execution/data/predictions/EnsembleTopK.parquet` · generated 2026-06-03T00:39:59Z_

_Self-only metrics — no leaderboard rank, no DM test, no MCS, no §9 status._
_Cross-model comparison is produced by the final `rv_eval.evaluator` pass._

## Tier-1 pooled by horizon (§3)
| model | horizon | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EnsembleTopK | 1 | 21080 | 0.2956 | 0.7586 | 0.6050 | -0.2491 | 0.9067 | 0.5130 | 0.0000 |
| EnsembleTopK | 5 | 21040 | 0.1939 | 0.5864 | 0.4550 | -0.1422 | 0.9153 | 0.5518 | 0.0002 |
| EnsembleTopK | 10 | 20990 | 0.2130 | 0.5864 | 0.4496 | -0.1343 | 0.9213 | 0.5697 | 0.0003 |
| EnsembleTopK | 22 | 20870 | 0.3241 | 0.6343 | 0.4755 | -0.1452 | 0.9271 | 0.5911 | 0.0008 |
| EnsembleTopK | 42 | 20670 | 0.4305 | 0.7058 | 0.5156 | -0.1635 | 0.9293 | 0.6099 | 0.0015 |

## §5 IV-incremental skill (per horizon)
| model | horizon | n | slope | t_slope | sign_acc | qlike_model | qlike_iv | qlike_gain_vs_iv |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EnsembleTopK | 1 | 20820 | 0.1021 | 22.0172 | 0.6701 | 0.2951 | 0.3276 | 0.0325 |
| EnsembleTopK | 5 | 20780 | 0.2232 | 26.6843 | 0.6192 | 0.1940 | 0.2079 | 0.0138 |
| EnsembleTopK | 10 | 20730 | 0.1810 | 15.2068 | 0.5651 | 0.2138 | 0.2187 | 0.0049 |
| EnsembleTopK | 22 | 20610 | 0.0068 | 0.4368 | 0.5183 | 0.3258 | 0.3396 | 0.0138 |
| EnsembleTopK | 42 | 20410 | -0.0025 | -0.1565 | 0.4956 | 0.4342 | 0.4697 | 0.0355 |

## §6 Conditional bias by IV-percentile bucket (h=22)
| model | horizon | iv_pctile_bucket | n | qlike | log_bias |
| --- | --- | --- | --- | --- | --- |
| EnsembleTopK | 22 | 0 | 5500 | 0.1751 | -0.1963 |
| EnsembleTopK | 22 | 1 | 3449 | 0.3158 | -0.1859 |
| EnsembleTopK | 22 | 2 | 3439 | 0.4603 | -0.1446 |
| EnsembleTopK | 22 | 3 | 3533 | 0.3678 | -0.1116 |
| EnsembleTopK | 22 | 4 | 4949 | 0.3698 | -0.0843 |

## §6 Post-shock calibration (h=22)
| model | horizon | bias_all | qlike_all | bias_postshock | qlike_postshock | n_postshock | trap_flag |
| --- | --- | --- | --- | --- | --- | --- | --- |
| EnsembleTopK | 22 | -0.1452 | 0.3241 | -0.1969 | 0.3870 | 3986 |  |

## Per-ticker Tier-1 at h=22
| model | horizon | ticker | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EnsembleTopK | 22 | EEM | 2087 | 0.2296 | 0.6098 | 0.4855 | -0.2242 | 0.9569 | 0.6895 | 0.0007 |
| EnsembleTopK | 22 | GLD | 2087 | 0.1617 | 0.5026 | 0.3835 | -0.0829 | 0.8951 | 0.5299 | 0.0003 |
| EnsembleTopK | 22 | HYG | 2087 | 0.6873 | 0.9406 | 0.7670 | -0.5615 | 0.9751 | 0.6996 | 0.0002 |
| EnsembleTopK | 22 | IWM | 2087 | 0.2928 | 0.5670 | 0.4159 | -0.0335 | 0.9138 | 0.5295 | 0.0010 |
| EnsembleTopK | 22 | QQQ | 2087 | 0.2807 | 0.6053 | 0.4633 | -0.0857 | 0.9334 | 0.6449 | 0.0008 |
| EnsembleTopK | 22 | SPY | 2087 | 0.4373 | 0.7052 | 0.5386 | -0.1023 | 0.9023 | 0.5343 | 0.0007 |
| EnsembleTopK | 22 | TLT | 2087 | 0.2108 | 0.5092 | 0.3580 | -0.0346 | 0.9123 | 0.5223 | 0.0003 |
| EnsembleTopK | 22 | XLE | 2087 | 0.2823 | 0.5403 | 0.3851 | -0.0624 | 0.9248 | 0.5999 | 0.0015 |
| EnsembleTopK | 22 | XLF | 2087 | 0.3669 | 0.6483 | 0.5097 | -0.2051 | 0.9425 | 0.5803 | 0.0010 |
| EnsembleTopK | 22 | XLK | 2087 | 0.2919 | 0.5976 | 0.4487 | -0.0596 | 0.9147 | 0.5807 | 0.0011 |

## Pooled by group
| model | group | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EnsembleTopK | emerging_markets | 10465 | 0.2773 | 0.7079 | 0.5584 | -0.2511 | 0.9380 | 0.6159 | 0.0005 |
| EnsembleTopK | high_yield_credit | 10465 | 0.5201 | 0.8897 | 0.7170 | -0.4766 | 0.9591 | 0.6545 | 0.0001 |
| EnsembleTopK | oil_and_energy | 10465 | 0.2510 | 0.5518 | 0.4033 | -0.0857 | 0.9160 | 0.5695 | 0.0011 |
| EnsembleTopK | precious_metals | 10465 | 0.2198 | 0.6357 | 0.4878 | -0.1558 | 0.8894 | 0.5076 | 0.0003 |
| EnsembleTopK | us_cyclicals_sector | 10465 | 0.3017 | 0.6383 | 0.4959 | -0.1999 | 0.9377 | 0.5845 | 0.0008 |
| EnsembleTopK | us_large_cap_equity | 20930 | 0.3054 | 0.6632 | 0.5093 | -0.1265 | 0.9150 | 0.5642 | 0.0006 |
| EnsembleTopK | us_rates_and_ig_credit | 10465 | 0.2120 | 0.5773 | 0.4249 | -0.0846 | 0.9059 | 0.5216 | 0.0002 |
| EnsembleTopK | us_small_cap_equity | 10465 | 0.2539 | 0.5730 | 0.4261 | -0.0667 | 0.9104 | 0.5330 | 0.0007 |
| EnsembleTopK | us_technology_sector | 10465 | 0.2627 | 0.6138 | 0.4697 | -0.0960 | 0.9125 | 0.5538 | 0.0008 |
