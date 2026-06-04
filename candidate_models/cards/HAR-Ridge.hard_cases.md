# HAR-Ridge — Self Stats
_universe=`hard_cases` · primary horizon h=22 · predictions=`execution/data/predictions/HAR-Ridge.parquet` · generated 2026-06-03T18:27:47Z_

_Self-only metrics — no leaderboard rank, no DM test, no MCS, no §9 status._
_Cross-model comparison is produced by the final `rv_eval.evaluator` pass._

## Tier-1 pooled by horizon (§3)
| model | horizon | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-Ridge | 1 | 7636 | 0.5168 | 0.7194 | 0.5595 | -0.2118 | 0.8916 | 0.5162 | 0.0005 |
| HAR-Ridge | 5 | 7595 | 0.2482 | 0.6248 | 0.4693 | -0.1309 | 0.8798 | 0.5074 | 0.0022 |
| HAR-Ridge | 10 | 7548 | 0.2573 | 0.6238 | 0.4613 | -0.1054 | 0.8733 | 0.5166 | 0.0046 |
| HAR-Ridge | 22 | 7488 | 0.3035 | 0.6292 | 0.4682 | -0.0600 | 0.8532 | 0.4935 | 0.0086 |
| HAR-Ridge | 42 | 7347 | 0.3495 | 0.6663 | 0.4867 | -0.0264 | 0.8319 | 0.4746 | 0.0786 |

## §5 IV-incremental skill (per horizon)
| model | horizon | n | slope | t_slope | sign_acc | qlike_model | qlike_iv | qlike_gain_vs_iv |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-Ridge | 1 | 7636 | 0.1758 | 23.7463 | 0.7596 | 0.5168 | 0.3563 | -0.1605 |
| HAR-Ridge | 5 | 7595 | 0.1783 | 18.8417 | 0.7145 | 0.2482 | 0.2630 | 0.0148 |
| HAR-Ridge | 10 | 7548 | 0.0198 | 3.9540 | 0.6726 | 0.2573 | 0.2551 | -0.0022 |
| HAR-Ridge | 22 | 7488 | 0.9219 | 34.8872 | 0.6289 | 0.3035 | 0.2738 | -0.0297 |
| HAR-Ridge | 42 | 7347 | -0.0000 | -0.0781 | 0.6125 | 0.3495 | 0.3189 | -0.0305 |

## §6 Conditional bias by IV-percentile bucket (h=22)
| model | horizon | iv_pctile_bucket | n | qlike | log_bias |
| --- | --- | --- | --- | --- | --- |
| HAR-Ridge | 22 | 0 | 1814 | 0.3108 | -0.1072 |
| HAR-Ridge | 22 | 1 | 1208 | 0.2527 | -0.0639 |
| HAR-Ridge | 22 | 2 | 1318 | 0.2456 | -0.0292 |
| HAR-Ridge | 22 | 3 | 1442 | 0.2628 | -0.0799 |
| HAR-Ridge | 22 | 4 | 1706 | 0.4109 | -0.0140 |

## §6 Post-shock calibration (h=22)
| model | horizon | bias_all | qlike_all | bias_postshock | qlike_postshock | n_postshock | trap_flag |
| --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-Ridge | 22 | -0.0600 | 0.3035 | -0.0596 | 0.3741 | 1396 |  |

## Per-ticker Tier-1 at h=22
| model | horizon | ticker | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-Ridge | 22 | IBIT | 224 | 0.1160 | 0.4992 | 0.3885 | -0.1111 | 0.6741 | 0.3795 | 0.0018 |
| HAR-Ridge | 22 | KRE | 2036 | 0.3675 | 0.5859 | 0.4005 | -0.0364 | 0.9283 | 0.5899 | 0.0017 |
| HAR-Ridge | 22 | MSOS | 1158 | 0.2530 | 0.6095 | 0.4832 | 0.2070 | 0.7021 | 0.3964 | 0.0073 |
| HAR-Ridge | 22 | USO | 2036 | 0.2719 | 0.5724 | 0.4064 | 0.0245 | 0.8212 | 0.4754 | 0.0029 |
| HAR-Ridge | 22 | UVXY | 2034 | 0.3204 | 0.7397 | 0.5980 | -0.3146 | 0.9159 | 0.4828 | 0.0226 |

## Pooled by group
| model | group | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-Ridge | crypto | 1151 | 0.1808 | 0.6508 | 0.5059 | -0.2536 | 0.8349 | 0.4509 | 0.0016 |
| HAR-Ridge | long_volatility_vix | 10200 | 0.3060 | 0.7508 | 0.6066 | -0.3158 | 0.8954 | 0.4779 | 0.0158 |
| HAR-Ridge | oil_and_energy | 10210 | 0.4473 | 0.6422 | 0.4618 | -0.0486 | 0.8347 | 0.4665 | 0.0481 |
| HAR-Ridge | us_cannabis | 5843 | 0.2966 | 0.6352 | 0.4831 | 0.0955 | 0.7814 | 0.4619 | 0.0052 |
| HAR-Ridge | us_cyclicals_sector | 10210 | 0.2922 | 0.5664 | 0.4009 | -0.0587 | 0.9208 | 0.5897 | 0.0012 |

---
## Model build notes (human-only, MODEL_PLAN §5)
**Model** `HAR-Ridge` · file `candidate_models/har_shrink.py:HARRidge` · Pattern P2 (`_PerKeyModel` over `_AttachMixin`). Same spec as the clean_core card.

**Mean model.** Per-(ticker, horizon) Ridge log-OLS on the HAR-MAX (model 18) kitchen-sink matrix (~25 cols), lognormal-mean corrected `rv_hat = exp(mu + 0.5·s²)`. Feature list identical to the clean_core card (HAR_RS_FEATURES + IV_FEATURES + sqrt_rq + Track-13..17 derived; `vrp_lag` uses `iv_30d²`, no `post_shock`/`iv2`).

**Hyperparameter selection.** `RidgeCV(alphas=np.logspace(-3,3,25), cv=TimeSeriesSplit(n_splits=5))` on the TRAIN slice only. Features standardised inside the fit. `sigma` = dof-aware in-sample log-residual std.
**Selected HP (final full-hard_cases fit, 25 keys):** alpha min/median/max = 0.001 / 177.8 / 1000 — stronger ridge shrinkage than clean_core (higher median alpha), consistent with the noisier hard-case series.

**Env / repro.** python 3.12.13 · numpy 2.4.6 · polars 1.41.1 · scipy 1.17.1 · scikit-learn 1.8.0 · macOS-15.3.1 arm64 (CPU). RidgeCV deterministic; fixed TimeSeriesSplit.

**Wall-clock.** hard_cases 103.9s (clean_core 298.0s).

**Coverage / warnings.** Full coverage — all 5 hard-case tickers (UVXY, MSOS, IBIT, USO, KRE) × 5 horizons. 37,989 OOS rows (span 2018-01-02 → 2026-05-21). No convergence failures, no dropped keys.
