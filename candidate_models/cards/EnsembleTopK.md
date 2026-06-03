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
- Coverage: 146,448 OOS rows total across both universes (105,450 clean_core + 40,998 hard_cases).
  Per-key component count: 142,389 keys used all 8 components; ~3,900 keys used 5-7; 188 keys used exactly 2.
  Keys dropped for <2 components: 23 (all MSOS, where only a single component produced a prediction).

_universe=`clean_core` · primary horizon h=22 · predictions=`execution/data/predictions/EnsembleTopK.parquet` · generated 2026-06-01T18:48:47Z_

_Self-only metrics — no leaderboard rank, no DM test, no MCS, no §9 status._
_Cross-model comparison is produced by the final `rv_eval.evaluator` pass._

## Tier-1 pooled by horizon (§3)
| model | horizon | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EnsembleTopK | 1 | 21080 | 0.4801 | 1.6226 | 0.8952 | -0.6614 | 0.8944 | 0.4848 | 1.1635 |
| EnsembleTopK | 5 | 21040 | 0.9857 | 3.4164 | 1.5261 | -1.4359 | 0.9450 | 0.7347 | 72.2635 |
| EnsembleTopK | 10 | 20990 | 1.5869 | 3.8989 | 2.3572 | -2.3190 | 0.9596 | 0.6846 | 100.7940 |
| EnsembleTopK | 22 | 20870 | 3.6992 | 6.0591 | 4.6327 | -4.6236 | 0.7001 | 0.0988 | 541454.0962 |
| EnsembleTopK | 42 | 20670 | 6.2457 | 9.9208 | 7.2003 | -7.1905 | 0.1660 | 0.0673 | 593709076394910.6250 |

## §5 IV-incremental skill (per horizon)
| model | horizon | n | slope | t_slope | sign_acc | qlike_model | qlike_iv | qlike_gain_vs_iv |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EnsembleTopK | 1 | 20820 | -0.0000 | -0.0042 | 0.4708 | 0.4807 | 0.3276 | -0.1530 |
| EnsembleTopK | 5 | 20780 | -0.0000 | -0.0007 | 0.3197 | 0.9854 | 0.2079 | -0.7775 |
| EnsembleTopK | 10 | 20730 | -0.0000 | -0.0007 | 0.3250 | 1.5897 | 0.2187 | -1.3711 |
| EnsembleTopK | 22 | 20610 | -0.0000 | -0.0000 | 0.3541 | 3.7058 | 0.3396 | -3.3662 |
| EnsembleTopK | 42 | 20410 | -0.0000 | -0.0000 | 0.3666 | 6.2545 | 0.4697 | -5.7848 |

## §6 Conditional bias by IV-percentile bucket (h=22)
| model | horizon | iv_pctile_bucket | n | qlike | log_bias |
| --- | --- | --- | --- | --- | --- |
| EnsembleTopK | 22 | 0 | 5500 | 3.8794 | -4.8188 |
| EnsembleTopK | 22 | 1 | 3449 | 3.7483 | -4.6831 |
| EnsembleTopK | 22 | 2 | 3439 | 3.7704 | -4.7026 |
| EnsembleTopK | 22 | 3 | 3533 | 3.6066 | -4.5361 |
| EnsembleTopK | 22 | 4 | 4949 | 3.4813 | -4.3727 |

## §6 Post-shock calibration (h=22)
| model | horizon | bias_all | qlike_all | bias_postshock | qlike_postshock | n_postshock | trap_flag |
| --- | --- | --- | --- | --- | --- | --- | --- |
| EnsembleTopK | 22 | -4.6236 | 3.6992 | -4.4306 | 3.5298 | 3986 |  |

## Per-ticker Tier-1 at h=22
| model | horizon | ticker | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EnsembleTopK | 22 | EEM | 2087 | 4.3353 | 8.7959 | 5.0038 | -4.9296 | 0.7892 | 0.3905 | 5411633.4830 |
| EnsembleTopK | 22 | GLD | 2087 | 3.3854 | 4.4173 | 4.3684 | -4.3684 | 0.5611 | 0.0292 | 0.0135 |
| EnsembleTopK | 22 | HYG | 2087 | 8.0506 | 12.3961 | 8.9423 | -8.9272 | 0.5980 | 0.2669 | 2907.3413 |
| EnsembleTopK | 22 | IWM | 2087 | 2.7977 | 3.8288 | 3.7627 | -3.7627 | 0.8184 | 0.0340 | 0.0180 |
| EnsembleTopK | 22 | QQQ | 2087 | 2.9486 | 3.9942 | 3.9178 | -3.9178 | 0.7355 | 0.0585 | 0.0176 |
| EnsembleTopK | 22 | SPY | 2087 | 3.4496 | 4.5130 | 4.4271 | -4.4271 | 0.6052 | 0.0359 | 0.0161 |
| EnsembleTopK | 22 | TLT | 2087 | 3.3060 | 4.3309 | 4.2880 | -4.2880 | 0.4274 | 0.0120 | 0.0124 |
| EnsembleTopK | 22 | XLE | 2087 | 2.6134 | 3.6394 | 3.5710 | -3.5691 | 0.8975 | 0.0537 | 0.0212 |
| EnsembleTopK | 22 | XLF | 2087 | 3.2409 | 4.2837 | 4.2148 | -4.2148 | 0.7657 | 0.0422 | 0.0197 |
| EnsembleTopK | 22 | XLK | 2087 | 2.8646 | 3.9057 | 3.8311 | -3.8311 | 0.8031 | 0.0652 | 0.0191 |

## Pooled by group
| model | group | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EnsembleTopK | emerging_markets | 10465 | 3.3923 | 10.4229 | 3.9946 | -3.8857 | 0.8624 | 0.4848 | 1172667617764136.0000 |
| EnsembleTopK | high_yield_credit | 10465 | 6.5826 | 10.9718 | 7.3755 | -7.3214 | 0.6646 | 0.3114 | 46337.4417 |
| EnsembleTopK | oil_and_energy | 10465 | 1.6945 | 3.1099 | 2.3901 | -2.3197 | 0.7747 | 0.4593 | 0.0651 |
| EnsembleTopK | precious_metals | 10465 | 2.1758 | 3.7381 | 2.9258 | -2.8419 | 0.6871 | 0.3803 | 0.0539 |
| EnsembleTopK | us_cyclicals_sector | 10465 | 2.0835 | 3.6148 | 2.8180 | -2.7493 | 0.7443 | 0.4255 | 0.0696 |
| EnsembleTopK | us_large_cap_equity | 20930 | 2.0720 | 3.6104 | 2.8087 | -2.7314 | 0.7221 | 0.4104 | 0.0605 |
| EnsembleTopK | us_rates_and_ig_credit | 10465 | 2.1079 | 3.6652 | 2.8488 | -2.7775 | 0.6679 | 0.4053 | 0.0487 |
| EnsembleTopK | us_small_cap_equity | 10465 | 1.8098 | 3.2599 | 2.5184 | -2.4461 | 0.7570 | 0.4402 | 0.0593 |
| EnsembleTopK | us_technology_sector | 10465 | 1.8550 | 3.3190 | 2.5712 | -2.4893 | 0.7481 | 0.4291 | 0.0632 |
