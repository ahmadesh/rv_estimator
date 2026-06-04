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
  combination is an arithmetic mean of rv_hat in level space, RealizedGARCH (rv_hat up to ~1e21)
  and GuyonLekeufackPDV — the two worst standalone candidates — dragged the ensemble mean past
  RandomWalk. They were dropped; XGBHARRSIV/LSTMRV dropped as dilutive. What remains is the top-K.
- Combination scheme: equal-weight MEAN of component rv_hat per (ticker, date, horizon);
  sigma = sqrt(mean(component_sigma^2) + var(component_rv_hat)); quantiles via `_lognormal_quantiles`.
- Availability rule: a key is kept only if >= 2 components have a prediction; otherwise dropped (never imputed).
- Hyperparameters: NONE. Random seed: N/A (deterministic combiner).

## Training
- Universes run: clean_core, hard_cases. Device: cpu. fit() is a no-op.
- Wall-clock time: clean_core ~4.0s, hard_cases ~3.7s (CPU).
- Coverage: 146,260 OOS rows total (105,450 clean_core + 40,810 hard_cases);
  142,497 keys used all 4 components, 3,763 used 3 — the >=2 floor never binds, no key dropped.

_universe=`hard_cases` · primary horizon h=22 · predictions=`execution/data/predictions/EnsembleTopK.parquet` · generated 2026-06-03T00:40:00Z_

_Self-only metrics — no leaderboard rank, no DM test, no MCS, no §9 status._
_Cross-model comparison is produced by the final `rv_eval.evaluator` pass._

## Tier-1 pooled by horizon (§3)
| model | horizon | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EnsembleTopK | 1 | 8196 | 0.3248 | 0.7664 | 0.6012 | -0.2733 | 0.9057 | 0.5359 | 0.0004 |
| EnsembleTopK | 5 | 8153 | 0.2600 | 0.6498 | 0.4924 | -0.1768 | 0.9014 | 0.5366 | 0.0020 |
| EnsembleTopK | 10 | 8108 | 0.2677 | 0.6657 | 0.4895 | -0.1637 | 0.8908 | 0.5339 | 0.0088 |
| EnsembleTopK | 22 | 8048 | 0.2907 | 0.6556 | 0.4915 | -0.1301 | 0.8815 | 0.5153 | 0.0099 |
| EnsembleTopK | 42 | 7905 | 0.3232 | 0.6784 | 0.4994 | -0.1009 | 0.8591 | 0.4908 | 0.0307 |

## §5 IV-incremental skill (per horizon)
| model | horizon | n | slope | t_slope | sign_acc | qlike_model | qlike_iv | qlike_gain_vs_iv |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EnsembleTopK | 1 | 7906 | 0.1272 | 12.4847 | 0.7127 | 0.3168 | 0.3595 | 0.0427 |
| EnsembleTopK | 5 | 7863 | 0.1409 | 11.2969 | 0.6686 | 0.2564 | 0.2624 | 0.0060 |
| EnsembleTopK | 10 | 7838 | -0.0008 | -1.9550 | 0.6258 | 0.2652 | 0.2542 | -0.0111 |
| EnsembleTopK | 22 | 7778 | -0.0006 | -0.2816 | 0.5797 | 0.2914 | 0.2732 | -0.0182 |
| EnsembleTopK | 42 | 7657 | -0.0007 | -1.6876 | 0.5718 | 0.3289 | 0.3134 | -0.0155 |

## §6 Conditional bias by IV-percentile bucket (h=22)
| model | horizon | iv_pctile_bucket | n | qlike | log_bias |
| --- | --- | --- | --- | --- | --- |
| EnsembleTopK | 22 | 0 | 2078 | 0.3074 | -0.2223 |
| EnsembleTopK | 22 | 1 | 1264 | 0.2411 | -0.1302 |
| EnsembleTopK | 22 | 2 | 1355 | 0.2357 | -0.0756 |
| EnsembleTopK | 22 | 3 | 1460 | 0.2505 | -0.1135 |
| EnsembleTopK | 22 | 4 | 1727 | 0.3887 | -0.0493 |

## §6 Post-shock calibration (h=22)
| model | horizon | bias_all | qlike_all | bias_postshock | qlike_postshock | n_postshock | trap_flag |
| --- | --- | --- | --- | --- | --- | --- | --- |
| EnsembleTopK | 22 | -0.1301 | 0.2907 | -0.1758 | 0.3290 | 1487 |  |

## Per-ticker Tier-1 at h=22
| model | horizon | ticker | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EnsembleTopK | 22 | IBIT | 517 | 0.1865 | 0.6831 | 0.5561 | -0.3911 | 0.7582 | 0.4507 | 0.0034 |
| EnsembleTopK | 22 | KRE | 2087 | 0.3481 | 0.6012 | 0.4338 | -0.0885 | 0.9382 | 0.5870 | 0.0017 |
| EnsembleTopK | 22 | MSOS | 1270 | 0.2230 | 0.5971 | 0.4652 | 0.0442 | 0.8315 | 0.5307 | 0.0066 |
| EnsembleTopK | 22 | USO | 2087 | 0.2645 | 0.6333 | 0.4361 | -0.0228 | 0.8515 | 0.4734 | 0.0091 |
| EnsembleTopK | 22 | UVXY | 2087 | 0.3265 | 0.7500 | 0.6045 | -0.3205 | 0.9157 | 0.4921 | 0.0226 |

## Pooled by group
| model | group | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EnsembleTopK | crypto | 2633 | 0.2788 | 0.8203 | 0.6569 | -0.4789 | 0.8629 | 0.5104 | 0.0024 |
| EnsembleTopK | long_volatility_vix | 10465 | 0.3103 | 0.7592 | 0.6132 | -0.3216 | 0.9056 | 0.5008 | 0.0154 |
| EnsembleTopK | oil_and_energy | 10465 | 0.2932 | 0.6943 | 0.4912 | -0.0927 | 0.8566 | 0.4763 | 0.0195 |
| EnsembleTopK | us_cannabis | 6382 | 0.2726 | 0.6180 | 0.4679 | -0.0207 | 0.8588 | 0.5409 | 0.0046 |
| EnsembleTopK | us_cyclicals_sector | 10465 | 0.2921 | 0.5914 | 0.4339 | -0.1075 | 0.9256 | 0.5831 | 0.0012 |
