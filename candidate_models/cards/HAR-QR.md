# HAR-QR — Self Stats
_universe=`clean_core` · primary horizon h=22 · predictions=`execution/data/predictions/HAR-QR.parquet` · generated 2026-06-04T02:00:57Z_

_Self-only metrics — no leaderboard rank, no DM test, no MCS, no §9 status._
_Cross-model comparison is produced by the final `rv_eval.evaluator` pass._

## Tier-1 pooled by horizon (§3)
| model | horizon | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-QR | 1 | 21080 | 858528.0184 | 3.4262 | 1.3214 | 0.6906 | 0.8874 | 0.4721 | 0.0000 |
| HAR-QR | 5 | 21040 | 4317981.0909 | 3.6629 | 1.2413 | 0.7703 | 0.8909 | 0.4753 | 0.0002 |
| HAR-QR | 10 | 20990 | 7036210.1387 | 3.5855 | 1.1732 | 0.7405 | 0.8947 | 0.4729 | 0.0004 |
| HAR-QR | 22 | 20870 | 14841464.5459 | 3.4876 | 1.1113 | 0.7079 | 0.9040 | 0.4732 | 0.0008 |
| HAR-QR | 42 | 20670 | 27440603.4886 | 3.3033 | 1.0313 | 0.6480 | 0.9003 | 0.4945 | 0.0016 |

## §5 IV-incremental skill (per horizon)
| model | horizon | n | slope | t_slope | sign_acc | qlike_model | qlike_iv | qlike_gain_vs_iv |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-QR | 1 | 20820 | -1.0889 | -40.8985 | 0.6604 | 846080.9250 | 0.3276 | -846080.5973 |
| HAR-QR | 5 | 20780 | -0.7691 | -41.3857 | 0.6078 | 4286644.8442 | 0.2079 | -4286644.6363 |
| HAR-QR | 10 | 20730 | -0.3669 | -20.7542 | 0.5866 | 7004757.4367 | 0.2187 | -7004757.2181 |
| HAR-QR | 22 | 20610 | 0.0974 | 6.1075 | 0.5721 | 14937622.9727 | 0.3396 | -14937622.6331 |
| HAR-QR | 42 | 20410 | 0.3391 | 18.2578 | 0.5774 | 27790165.3137 | 0.4697 | -27790164.8440 |

## §6 Conditional bias by IV-percentile bucket (h=22)
| model | horizon | iv_pctile_bucket | n | qlike | log_bias |
| --- | --- | --- | --- | --- | --- |
| HAR-QR | 22 | 0 | 5500 | 30656415.5796 | 1.4289 |
| HAR-QR | 22 | 1 | 3449 | 23674237.5701 | 0.9445 |
| HAR-QR | 22 | 2 | 3439 | 15604500.8962 | 0.5197 |
| HAR-QR | 22 | 3 | 3533 | 965348.7782 | 0.1715 |
| HAR-QR | 22 | 4 | 4949 | 485790.7033 | 0.2553 |

## §6 Post-shock calibration (h=22)
| model | horizon | bias_all | qlike_all | bias_postshock | qlike_postshock | n_postshock | trap_flag |
| --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-QR | 22 | 0.7079 | 14841464.5459 | 0.0948 | 743687.6387 | 3986 |  |

## Per-ticker Tier-1 at h=22
| model | horizon | ticker | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-QR | 22 | EEM | 2087 | 13655620.4169 | 1.4703 | 0.5881 | 0.1407 | 0.9051 | 0.4662 | 0.0008 |
| HAR-QR | 22 | GLD | 2087 | 28287009.3425 | 3.8724 | 1.1916 | 0.8428 | 0.8256 | 0.4011 | 0.0004 |
| HAR-QR | 22 | HYG | 2087 | 48911794.7183 | 9.3226 | 5.2459 | 4.4882 | 0.8682 | 0.4792 | 0.0002 |
| HAR-QR | 22 | IWM | 2087 | 7927503.6034 | 1.7433 | 0.6031 | 0.2526 | 0.9243 | 0.5141 | 0.0010 |
| HAR-QR | 22 | QQQ | 2087 | 0.4547 | 0.6855 | 0.4991 | 0.2191 | 0.9214 | 0.4878 | 0.0009 |
| HAR-QR | 22 | SPY | 2087 | 14865830.2819 | 2.0782 | 0.7642 | 0.2977 | 0.9109 | 0.4792 | 0.0007 |
| HAR-QR | 22 | TLT | 2087 | 0.2543 | 0.5292 | 0.3821 | 0.1324 | 0.8826 | 0.4308 | 0.0003 |
| HAR-QR | 22 | XLE | 2087 | 8798463.0099 | 1.1513 | 0.4659 | 0.1521 | 0.9200 | 0.5098 | 0.0017 |
| HAR-QR | 22 | XLF | 2087 | 25968422.9548 | 2.7753 | 0.9082 | 0.3890 | 0.9478 | 0.4940 | 0.0012 |
| HAR-QR | 22 | XLK | 2087 | 0.4225 | 0.6566 | 0.4649 | 0.1639 | 0.9344 | 0.4696 | 0.0011 |

## Pooled by group
| model | group | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-QR | emerging_markets | 10465 | 9983233.7338 | 2.4819 | 0.8661 | 0.3150 | 0.8887 | 0.4707 | 0.0006 |
| HAR-QR | high_yield_credit | 10465 | 46200693.6002 | 8.7930 | 4.9569 | 4.2295 | 0.8597 | 0.4786 | 0.0002 |
| HAR-QR | oil_and_energy | 10465 | 3178056.0336 | 1.1575 | 0.4986 | 0.1300 | 0.9127 | 0.5026 | 0.0012 |
| HAR-QR | precious_metals | 10465 | 17439972.3191 | 3.8644 | 1.3030 | 0.8496 | 0.8375 | 0.4163 | 0.0003 |
| HAR-QR | us_cyclicals_sector | 10465 | 16547419.5591 | 2.9634 | 0.9918 | 0.4328 | 0.9310 | 0.5194 | 0.0009 |
| HAR-QR | us_large_cap_equity | 20930 | 4580683.8467 | 1.9777 | 0.7388 | 0.3013 | 0.9074 | 0.4791 | 0.0006 |
| HAR-QR | us_rates_and_ig_credit | 10465 | 12647.4635 | 0.6490 | 0.4471 | 0.1140 | 0.8832 | 0.4570 | 0.0002 |
| HAR-QR | us_small_cap_equity | 10465 | 5665909.6737 | 2.1583 | 0.7070 | 0.3025 | 0.9044 | 0.4983 | 0.0008 |
| HAR-QR | us_technology_sector | 10465 | 131462.7304 | 0.8837 | 0.5157 | 0.1410 | 0.9225 | 0.4742 | 0.0008 |

## Provenance (MODEL_PLAN §5 — appended by orchestrator; build worker died before writing cards)

- **Features:** `HAR_FEATURES = [log_rv_d, log_rv_w, log_rv_m]` (pass-through from `build_features`, no `_AttachMixin` join).
- **Target space:** level / variance units (`target_var`), NOT log. Seven independent quantile regressions per (ticker, horizon), τ ∈ {.05,.10,.25,.50,.75,.90,.95}. Quantiles emitted directly (no lognormal wrapper); `_QuantileModel.predict` applies `np.maximum.accumulate` rearrangement so the grid is monotone on every row. `rv_hat=q50`; `sigma=(q90−q10)/2.563`. Positive floor `_VAR_FLOOR=1e-12`.
- **Hyperparameters (frozen, by-construction, NOT OOS-tuned):** `sklearn.linear_model.QuantileRegressor(alpha=1e-3, fit_intercept=True, solver="highs")`. Seed 0 (LP solver deterministic).
- **Validation:** 146,260 OOS rows (clean_core 105,450 + hard_cases 40,810); 10/10 clean_core + 5 hard tickers × {1,5,10,22,42}; rv_hat finite & >0; quantiles monotone & finite. Smoke test 2/2.
- **Libraries:** python 3.12.13, scikit-learn (QuantileRegressor/highs), numpy 2.4.6, polars 1.41.1. Device: CPU, Apple arm64.
- **Wall-time:** clean_core **10,888.6 s (≈3.0 h)**, hard_cases **2,244.2 s (≈37 min)**. Run in foreground by the orchestrator after the build worker backgrounded-and-exited without finishing.
- **⚠ Runtime cause:** `QuantileRegressor(solver="highs")` formulates each fit as a linear program whose size scales with the number of training rows (~2·n LP variables). On the expanding-window walk-forward (monthly refits, ~90 folds) the training set grows to thousands of rows, and 7 such LPs are solved per (ticker,horizon) per fold across 50 keys → hundreds of thousands of ever-larger LP solves. Swapping to `statsmodels.regression.quantile_regression.QuantReg` (IRLS) would cut this to minutes; left as-is since predictions are complete and valid. Candidate optimization for any rerun.
- **⚠ Quality flag (for comparison pass, not a gate failure):** level-space QR is badly miscalibrated on several heavy-tailed names — pooled QLIKE explodes to 1e6–1e7 for HYG/GLD/SPY/IWM/XLE/XLF (q50 level-extrapolation), while log-space-friendly names (QQQ/TLT/XLK) stay O(0.4). Interval coverage is reasonable (cov90≈0.88–0.93) but the point/QLIKE behavior suggests a log-target QR variant would be the fix. Flagged for the re-weighted comparison gate.
