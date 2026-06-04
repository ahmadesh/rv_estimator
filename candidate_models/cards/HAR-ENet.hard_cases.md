# HAR-ENet — Self Stats
_universe=`hard_cases` · primary horizon h=22 · predictions=`execution/data/predictions/HAR-ENet.parquet` · generated 2026-06-03T18:27:46Z_

_Self-only metrics — no leaderboard rank, no DM test, no MCS, no §9 status._
_Cross-model comparison is produced by the final `rv_eval.evaluator` pass._

## Tier-1 pooled by horizon (§3)
| model | horizon | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-ENet | 1 | 7636 | 0.3217 | 0.7157 | 0.5584 | -0.2102 | 0.8918 | 0.5111 | 0.0005 |
| HAR-ENet | 5 | 7595 | 0.2436 | 0.6169 | 0.4632 | -0.1295 | 0.8837 | 0.5111 | 0.0021 |
| HAR-ENet | 10 | 7548 | 0.2556 | 0.6200 | 0.4576 | -0.1023 | 0.8755 | 0.5140 | 0.0055 |
| HAR-ENet | 22 | 7488 | 0.2889 | 0.6186 | 0.4617 | -0.0578 | 0.8608 | 0.4923 | 0.0085 |
| HAR-ENet | 42 | 7347 | 0.3295 | 0.6395 | 0.4757 | -0.0302 | 0.8359 | 0.4924 | 0.0151 |

## §5 IV-incremental skill (per horizon)
| model | horizon | n | slope | t_slope | sign_acc | qlike_model | qlike_iv | qlike_gain_vs_iv |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-ENet | 1 | 7636 | 0.1944 | 23.4782 | 0.7651 | 0.3217 | 0.3563 | 0.0346 |
| HAR-ENet | 5 | 7595 | 0.2329 | 20.0049 | 0.7211 | 0.2436 | 0.2630 | 0.0194 |
| HAR-ENet | 10 | 7548 | 0.0014 | 0.9280 | 0.6708 | 0.2556 | 0.2551 | -0.0005 |
| HAR-ENet | 22 | 7488 | 0.9202 | 36.1490 | 0.6303 | 0.2889 | 0.2738 | -0.0152 |
| HAR-ENet | 42 | 7347 | 0.9981 | 56.7863 | 0.6181 | 0.3295 | 0.3189 | -0.0106 |

## §6 Conditional bias by IV-percentile bucket (h=22)
| model | horizon | iv_pctile_bucket | n | qlike | log_bias |
| --- | --- | --- | --- | --- | --- |
| HAR-ENet | 22 | 0 | 1814 | 0.3049 | -0.1115 |
| HAR-ENet | 22 | 1 | 1208 | 0.2433 | -0.0676 |
| HAR-ENet | 22 | 2 | 1318 | 0.2398 | -0.0252 |
| HAR-ENet | 22 | 3 | 1442 | 0.2546 | -0.0716 |
| HAR-ENet | 22 | 4 | 1706 | 0.3713 | -0.0074 |

## §6 Post-shock calibration (h=22)
| model | horizon | bias_all | qlike_all | bias_postshock | qlike_postshock | n_postshock | trap_flag |
| --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-ENet | 22 | -0.0578 | 0.2889 | -0.0506 | 0.3289 | 1396 |  |

## Per-ticker Tier-1 at h=22
| model | horizon | ticker | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-ENet | 22 | IBIT | 224 | 0.1231 | 0.5166 | 0.4241 | -0.1632 | 0.6250 | 0.3036 | 0.0019 |
| HAR-ENet | 22 | KRE | 2036 | 0.3535 | 0.5786 | 0.3987 | -0.0299 | 0.9283 | 0.5918 | 0.0017 |
| HAR-ENet | 22 | MSOS | 1158 | 0.2467 | 0.5976 | 0.4764 | 0.2347 | 0.7211 | 0.3895 | 0.0071 |
| HAR-ENet | 22 | USO | 2036 | 0.2332 | 0.5423 | 0.3877 | 0.0082 | 0.8414 | 0.4833 | 0.0027 |
| HAR-ENet | 22 | UVXY | 2034 | 0.3225 | 0.7392 | 0.5945 | -0.3068 | 0.9184 | 0.4808 | 0.0225 |

## Pooled by group
| model | group | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-ENet | crypto | 1151 | 0.1815 | 0.6445 | 0.5124 | -0.2528 | 0.7932 | 0.4196 | 0.0015 |
| HAR-ENet | long_volatility_vix | 10200 | 0.3060 | 0.7504 | 0.6055 | -0.3177 | 0.8973 | 0.4804 | 0.0155 |
| HAR-ENet | oil_and_energy | 10210 | 0.2829 | 0.6175 | 0.4507 | -0.0560 | 0.8432 | 0.4727 | 0.0033 |
| HAR-ENet | us_cannabis | 5843 | 0.2872 | 0.6159 | 0.4676 | 0.1152 | 0.7933 | 0.4659 | 0.0049 |
| HAR-ENet | us_cyclicals_sector | 10210 | 0.2864 | 0.5634 | 0.4004 | -0.0573 | 0.9214 | 0.5914 | 0.0012 |

---
## Model build notes (human-only, MODEL_PLAN §5)
**Model** `HAR-ENet` · file `candidate_models/har_shrink.py:HARENet` · Pattern P2 (`_PerKeyModel` over `_AttachMixin`). Same spec as the clean_core card.

**Mean model.** Per-(ticker, horizon) ElasticNet log-OLS on the HAR-MAX (model 18) kitchen-sink matrix (~25 cols), lognormal-mean corrected `rv_hat = exp(mu + 0.5·s²)`. Feature list identical to the clean_core card (HAR_RS_FEATURES + IV_FEATURES + sqrt_rq + Track-13..17 derived; `vrp_lag` uses `iv_30d²`, no `post_shock`/`iv2`).

**Hyperparameter selection.** `ElasticNetCV` with `TimeSeriesSplit(n_splits=5)` on the TRAIN slice only (50-pt alpha path, l1_ratio ∈ {.1,.3,.5,.7,.9,.95,.99,1.0}, max_iter=20000). Features standardised inside the fit. `sigma` = dof-aware in-sample log-residual std.
**Selected HP (final full-hard_cases fit, 25 keys):** alpha min/median/max = 0.000962 / 0.0317 / 0.899; l1_ratio counts = {1.0:10, 0.1:7, 0.3:4, 0.5:2, 0.9:2}. Stronger shrinkage than clean_core (larger median alpha) reflecting the noisier hard-case series.

**Env / repro.** python 3.12.13 · numpy 2.4.6 · polars 1.41.1 · scipy 1.17.1 · scikit-learn 1.8.0 · macOS-15.3.1 arm64 (CPU, n_jobs=1). Seed `random_state=0`.

**Wall-clock.** hard_cases 183.5s (clean_core 567.3s).

**Coverage / warnings.** Full coverage — all 5 hard-case tickers (UVXY, MSOS, IBIT, USO, KRE) × 5 horizons. 37,989 OOS rows (span 2018-01-02 → 2026-05-21). No convergence failures, no dropped keys. Expect wider dispersion / weaker calibration than clean_core given UVXY/MSOS/IBIT regime breaks — see the tables above.
