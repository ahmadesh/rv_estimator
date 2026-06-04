# HAR-Ridge — Self Stats
_universe=`clean_core` · primary horizon h=22 · predictions=`execution/data/predictions/HAR-Ridge.parquet` · generated 2026-06-03T18:27:46Z_

_Self-only metrics — no leaderboard rank, no DM test, no MCS, no §9 status._
_Cross-model comparison is produced by the final `rv_eval.evaluator` pass._

## Tier-1 pooled by horizon (§3)
| model | horizon | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-Ridge | 1 | 20570 | 0.2770 | 0.7189 | 0.5712 | -0.2067 | 0.8925 | 0.4933 | 0.0000 |
| HAR-Ridge | 5 | 20530 | 0.1816 | 0.5535 | 0.4286 | -0.1046 | 0.8959 | 0.5174 | 0.0002 |
| HAR-Ridge | 10 | 20480 | 0.2079 | 0.5598 | 0.4239 | -0.0910 | 0.9043 | 0.5361 | 0.0003 |
| HAR-Ridge | 22 | 20360 | 0.3488 | 0.6110 | 0.4492 | -0.0902 | 0.9093 | 0.5531 | 0.0008 |
| HAR-Ridge | 42 | 20160 | 0.4755 | 0.6831 | 0.4909 | -0.0904 | 0.9103 | 0.5617 | 0.0016 |

## §5 IV-incremental skill (per horizon)
| model | horizon | n | slope | t_slope | sign_acc | qlike_model | qlike_iv | qlike_gain_vs_iv |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-Ridge | 1 | 20570 | 0.5869 | 47.7078 | 0.7142 | 0.2770 | 0.3278 | 0.0508 |
| HAR-Ridge | 5 | 20530 | 0.5703 | 42.7983 | 0.6672 | 0.1816 | 0.2087 | 0.0270 |
| HAR-Ridge | 10 | 20480 | 0.2847 | 18.2067 | 0.6062 | 0.2079 | 0.2201 | 0.0122 |
| HAR-Ridge | 22 | 20360 | -0.0445 | -2.7808 | 0.5370 | 0.3488 | 0.3419 | -0.0069 |
| HAR-Ridge | 42 | 20160 | -0.0556 | -2.9764 | 0.5264 | 0.4755 | 0.4743 | -0.0012 |

## §6 Conditional bias by IV-percentile bucket (h=22)
| model | horizon | iv_pctile_bucket | n | qlike | log_bias |
| --- | --- | --- | --- | --- | --- |
| HAR-Ridge | 22 | 0 | 5149 | 0.1811 | -0.1398 |
| HAR-Ridge | 22 | 1 | 3408 | 0.3391 | -0.1373 |
| HAR-Ridge | 22 | 2 | 3412 | 0.5216 | -0.0962 |
| HAR-Ridge | 22 | 3 | 3497 | 0.3826 | -0.0570 |
| HAR-Ridge | 22 | 4 | 4894 | 0.3872 | -0.0248 |

## §6 Post-shock calibration (h=22)
| model | horizon | bias_all | qlike_all | bias_postshock | qlike_postshock | n_postshock | trap_flag |
| --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-Ridge | 22 | -0.0902 | 0.3488 | -0.0573 | 0.4117 | 3871 |  |

## Per-ticker Tier-1 at h=22
| model | horizon | ticker | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-Ridge | 22 | EEM | 2036 | 0.2481 | 0.5748 | 0.4320 | -0.0615 | 0.8959 | 0.5643 | 0.0007 |
| HAR-Ridge | 22 | GLD | 2036 | 0.1409 | 0.4614 | 0.3395 | -0.0216 | 0.8910 | 0.5378 | 0.0003 |
| HAR-Ridge | 22 | HYG | 2036 | 0.8107 | 0.8306 | 0.6530 | -0.3482 | 0.9450 | 0.5575 | 0.0002 |
| HAR-Ridge | 22 | IWM | 2036 | 0.3052 | 0.5509 | 0.3924 | 0.0167 | 0.9032 | 0.5511 | 0.0009 |
| HAR-Ridge | 22 | QQQ | 2036 | 0.3129 | 0.6173 | 0.4554 | -0.0163 | 0.8851 | 0.5732 | 0.0009 |
| HAR-Ridge | 22 | SPY | 2036 | 0.4618 | 0.6931 | 0.5194 | -0.0776 | 0.9003 | 0.5516 | 0.0007 |
| HAR-Ridge | 22 | TLT | 2036 | 0.2149 | 0.4893 | 0.3439 | -0.0298 | 0.9067 | 0.4774 | 0.0003 |
| HAR-Ridge | 22 | XLE | 2036 | 0.2936 | 0.5535 | 0.3990 | -0.0813 | 0.9209 | 0.5496 | 0.0016 |
| HAR-Ridge | 22 | XLF | 2036 | 0.3735 | 0.6378 | 0.4973 | -0.1954 | 0.9416 | 0.5830 | 0.0010 |
| HAR-Ridge | 22 | XLK | 2036 | 0.3262 | 0.6186 | 0.4605 | -0.0868 | 0.9032 | 0.5855 | 0.0011 |

## Pooled by group
| model | group | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-Ridge | emerging_markets | 10210 | 0.2811 | 0.6709 | 0.5112 | -0.1218 | 0.8892 | 0.5244 | 0.0005 |
| HAR-Ridge | high_yield_credit | 10210 | 0.5923 | 0.8015 | 0.6250 | -0.3132 | 0.9286 | 0.5493 | 0.0001 |
| HAR-Ridge | oil_and_energy | 10210 | 0.2495 | 0.5529 | 0.4060 | -0.0937 | 0.9058 | 0.5325 | 0.0012 |
| HAR-Ridge | precious_metals | 10210 | 0.2018 | 0.6030 | 0.4537 | -0.1025 | 0.8830 | 0.5082 | 0.0002 |
| HAR-Ridge | us_cyclicals_sector | 10210 | 0.2912 | 0.6165 | 0.4780 | -0.1869 | 0.9340 | 0.5636 | 0.0008 |
| HAR-Ridge | us_large_cap_equity | 20420 | 0.3130 | 0.6450 | 0.4896 | -0.0794 | 0.8917 | 0.5324 | 0.0006 |
| HAR-Ridge | us_rates_and_ig_credit | 10210 | 0.2074 | 0.5523 | 0.4100 | -0.0716 | 0.8946 | 0.4877 | 0.0002 |
| HAR-Ridge | us_small_cap_equity | 10210 | 0.2522 | 0.5499 | 0.4029 | -0.0245 | 0.8998 | 0.5365 | 0.0007 |
| HAR-Ridge | us_technology_sector | 10210 | 0.2729 | 0.6085 | 0.4620 | -0.0947 | 0.9058 | 0.5547 | 0.0008 |

---
## Model build notes (human-only, MODEL_PLAN §5)
**Model** `HAR-Ridge` · file `candidate_models/har_shrink.py:HARRidge` · Pattern P2 (`_PerKeyModel` over `_AttachMixin`).

**Mean model.** Per-(ticker, horizon) Ridge regression of `log(target_var)` on the HAR-MAX (model 18) kitchen-sink feature matrix (~25 cols, deduped), lognormal-mean corrected `rv_hat = exp(mu + 0.5·s²)`.

**Features used (`needs`, deduped):** identical to HAR-ENet — pass-through `HAR_RS_FEATURES + IV_FEATURES + sqrt_rq` plus the Track-13..17 derived block (`lev_d/w/m`, `sj_5d/abs_sj_5d`, `iv_curv/iv_ts_30_90/vrp_lag/vrp_mom`, `log_park_d/w`, `log_gk_d/w`, `log_vol_surprise/log_txn_surprise/overnight_share`). All rolling/shift/ratio columns are built once on the full series and joined by (ticker,date) via `_AttachMixin._derive`. `vrp_lag` uses `iv_30d²` (in X), not `targets.iv2`; no `post_shock`/`iv2`.

**Hyperparameter selection (shrinkage discipline).** Penalty chosen by a **time-ordered inner CV on the TRAIN slice only** — `RidgeCV(alphas=np.logspace(-3,3,25), cv=TimeSeriesSplit(n_splits=5))`. No OOS rows or other models' results consulted. Features standardised inside the fit (μ/σ from the train slice, re-applied at predict). `sigma` = dof-aware in-sample log-residual std.
**Selected HP (final full-clean_core fit, 50 keys):** alpha min/median/max = 0.001 / 31.62 / 1000 (wide spread; many keys land at the strong-shrinkage end of the log-grid).

**Env / repro.** python 3.12.13 · numpy 2.4.6 · polars 1.41.1 · scipy 1.17.1 · scikit-learn 1.8.0 · macOS-15.3.1 arm64 (Apple Silicon, CPU). RidgeCV is deterministic (no RNG); the fixed TimeSeriesSplit makes the fit reproducible.

**Wall-clock.** clean_core 298.0s · hard_cases 103.9s (walk-forward, monthly refit, expanding window).

**Coverage / warnings.** Full coverage — all 15 scored tickers × 5 horizons on both universes. clean_core 102,850 OOS rows; hard_cases 37,989 OOS rows (span 2018-01-02 → 2026-05-21). No convergence failures, no dropped (ticker,horizon).
