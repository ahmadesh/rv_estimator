# XGBHARRSIV — Model Card

## Identity
- Model number (from MODEL_PLAN.md): 9
- Class: `candidate_models.xgb_har:XGBHARRSIV`
- Tier: ML
- Implemented by: card generated 2026-05-31 (model code/predictions pre-existing & validated)

## Configuration
- Features used (14, deduped `HAR_RS_FEATURES + IV_FEATURES + ["sqrt_rq"]`):
  - HAR-RS block: `log_rv_d`, `log_rv_w`, `log_rv_m`, `rs_minus_5d`, `rs_plus_5d`, `jump_5d`
  - IV block: `log_iv`, `iv_slope`, `skew_25d`, `vix`, `vix3m`, `vix_slope`, `vvix`
  - Realized quarticity: `sqrt_rq`
- Target: `log(target_var)`; one xgboost booster per (ticker, horizon). `rv_hat = exp(mu + 0.5*sigma^2)` (lognormal-mean back-transform), quantiles via `_lognormal_quantiles`.
- Hyperparameters (FROZEN — tune-once-then-freeze):
  - `max_depth=3`
  - `learning_rate=0.03`
  - `min_child_weight=20`
- Fixed params (not gridded):
  - `subsample=0.8`
  - `colsample_bytree=0.8`
  - `reg_lambda=1.0`
  - `objective=reg:squarederror`
  - `tree_method=hist`
  - `seed=0`
- `n_estimators`: chosen per fit by early stopping (`early_stopping_rounds=50`) on a 10% time-ordered within-train tail; cap 2000.
- `sigma`: residual std of `log(target_var)` on that same held-out 10% tail (floored at 1e-3).
- HP selection (model 9): leakage-safe tune-once-then-freeze. Search-train = `date < 2016-01-01`; validation block = `[2016-01-01, 2018-01-01)` (2016–2017, no OOS read). Grid = 27 points: `max_depth∈{3,4,6}` × `learning_rate∈{0.03,0.05,0.1}` × `min_child_weight∈{5,10,20}`. One global booster pooled across scored tickers fit at h=22 per grid point; selection metric = pooled QLIKE @ h=22. Chosen = `(max_depth=3, learning_rate=0.03, min_child_weight=20)` with validation QLIKE@h22 = 0.146970; grid initial point `(4, 0.05, 10)` scored 0.158985. Recorded in `candidate_models/xgb_har.py` docstring and `candidate_models/_tune_xgb.py` (tuning run 2026-05-31).
- Library version(s): xgboost 3.2.0
- Random seed: 0

## Training
- Universes run: clean_core, hard_cases
- Wall-clock time: clean_core 698s, hard_cases 264s
- Device: cpu (`tree_method=hist`)
- Coverage: 144,527 OOS rows cover all 15 scored tickers × 5 horizons {1,5,10,22,42}, min date 2018-01-02; none dropped. IBIT and MSOS have shorter histories (fewer rows) but full horizon coverage.
- Convergence notes: no per-ticker failures; `rv_hat` finite & >0, quantiles monotone.

---

# XGBHARRSIV — Self Stats
_universe=`clean_core` · primary horizon h=22 · predictions=`execution/data/predictions/XGBHARRSIV.parquet` · generated 2026-06-01T06:58:07Z_

_Self-only metrics — no leaderboard rank, no DM test, no MCS, no §9 status._
_Cross-model comparison is produced by the final `rv_eval.evaluator` pass._

## Tier-1 pooled by horizon (§3)
| model | horizon | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| XGBHARRSIV | 1 | 21080 | 0.2953 | 0.7627 | 0.6058 | -0.2554 | 0.8941 | 0.4988 | 0.0000 |
| XGBHARRSIV | 5 | 21040 | 0.2033 | 0.5949 | 0.4570 | -0.1336 | 0.8850 | 0.5146 | 0.0002 |
| XGBHARRSIV | 10 | 20990 | 0.2395 | 0.6023 | 0.4535 | -0.1131 | 0.8718 | 0.5128 | 0.0003 |
| XGBHARRSIV | 22 | 20870 | 0.3977 | 0.6596 | 0.4845 | -0.0954 | 0.8486 | 0.4877 | 0.0008 |
| XGBHARRSIV | 42 | 20670 | 0.5343 | 0.7465 | 0.5410 | -0.0840 | 0.7898 | 0.4685 | 0.0017 |

## §5 IV-incremental skill (per horizon)
| model | horizon | n | slope | t_slope | sign_acc | qlike_model | qlike_iv | qlike_gain_vs_iv |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| XGBHARRSIV | 1 | 20820 | 1.5860 | 50.7162 | 0.6882 | 0.2918 | 0.3276 | 0.0359 |
| XGBHARRSIV | 5 | 20780 | 0.9243 | 30.9016 | 0.6348 | 0.2002 | 0.2079 | 0.0076 |
| XGBHARRSIV | 10 | 20730 | 0.3831 | 13.5479 | 0.5762 | 0.2367 | 0.2187 | -0.0181 |
| XGBHARRSIV | 22 | 20610 | 0.0932 | 4.5539 | 0.5269 | 0.3964 | 0.3396 | -0.0568 |
| XGBHARRSIV | 42 | 20410 | 0.1488 | 8.2541 | 0.5065 | 0.5355 | 0.4697 | -0.0658 |

## §6 Conditional bias by IV-percentile bucket (h=22)
| model | horizon | iv_pctile_bucket | n | qlike | log_bias |
| --- | --- | --- | --- | --- | --- |
| XGBHARRSIV | 22 | 0 | 5500 | 0.2135 | -0.2472 |
| XGBHARRSIV | 22 | 1 | 3449 | 0.3592 | -0.1906 |
| XGBHARRSIV | 22 | 2 | 3439 | 0.5427 | -0.1206 |
| XGBHARRSIV | 22 | 3 | 3533 | 0.3996 | -0.0356 |
| XGBHARRSIV | 22 | 4 | 4949 | 0.5273 | 0.1146 |

## §6 Post-shock calibration (h=22)
| model | horizon | bias_all | qlike_all | bias_postshock | qlike_postshock | n_postshock | trap_flag |
| --- | --- | --- | --- | --- | --- | --- | --- |
| XGBHARRSIV | 22 | -0.0954 | 0.3977 | 0.0558 | 0.5586 | 3986 |  |

## Per-ticker Tier-1 at h=22
| model | horizon | ticker | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| XGBHARRSIV | 22 | EEM | 2087 | 0.2614 | 0.6208 | 0.4741 | -0.1491 | 0.8500 | 0.4753 | 0.0007 |
| XGBHARRSIV | 22 | GLD | 2087 | 0.1809 | 0.5609 | 0.4295 | -0.1692 | 0.7518 | 0.4447 | 0.0004 |
| XGBHARRSIV | 22 | HYG | 2087 | 0.9590 | 0.8961 | 0.6944 | -0.3431 | 0.8428 | 0.4471 | 0.0002 |
| XGBHARRSIV | 22 | IWM | 2087 | 0.3132 | 0.5711 | 0.4116 | 0.0396 | 0.8740 | 0.4753 | 0.0010 |
| XGBHARRSIV | 22 | QQQ | 2087 | 0.5022 | 0.7140 | 0.5091 | 0.0853 | 0.8280 | 0.5060 | 0.0010 |
| XGBHARRSIV | 22 | SPY | 2087 | 0.4540 | 0.7251 | 0.5458 | -0.1021 | 0.8826 | 0.5438 | 0.0007 |
| XGBHARRSIV | 22 | TLT | 2087 | 0.2269 | 0.5227 | 0.3759 | -0.0217 | 0.8481 | 0.4777 | 0.0003 |
| XGBHARRSIV | 22 | XLE | 2087 | 0.3171 | 0.5875 | 0.4262 | -0.0932 | 0.8778 | 0.4839 | 0.0017 |
| XGBHARRSIV | 22 | XLF | 2087 | 0.4013 | 0.6935 | 0.5282 | -0.2093 | 0.8668 | 0.4547 | 0.0011 |
| XGBHARRSIV | 22 | XLK | 2087 | 0.3613 | 0.6214 | 0.4504 | 0.0091 | 0.8639 | 0.5683 | 0.0011 |

## Pooled by group
| model | group | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| XGBHARRSIV | emerging_markets | 10465 | 0.2979 | 0.7223 | 0.5596 | -0.2145 | 0.8522 | 0.4798 | 0.0006 |
| XGBHARRSIV | high_yield_credit | 10465 | 0.6957 | 0.8746 | 0.6753 | -0.3426 | 0.8573 | 0.4797 | 0.0001 |
| XGBHARRSIV | oil_and_energy | 10465 | 0.2662 | 0.5864 | 0.4330 | -0.1051 | 0.8780 | 0.4971 | 0.0013 |
| XGBHARRSIV | precious_metals | 10465 | 0.2341 | 0.6772 | 0.5240 | -0.2204 | 0.7961 | 0.4427 | 0.0003 |
| XGBHARRSIV | us_cyclicals_sector | 10465 | 0.3047 | 0.6641 | 0.5072 | -0.2145 | 0.8670 | 0.4957 | 0.0008 |
| XGBHARRSIV | us_large_cap_equity | 20930 | 0.3711 | 0.7004 | 0.5267 | -0.0674 | 0.8640 | 0.5149 | 0.0006 |
| XGBHARRSIV | us_rates_and_ig_credit | 10465 | 0.2321 | 0.5937 | 0.4446 | -0.0868 | 0.8570 | 0.4954 | 0.0002 |
| XGBHARRSIV | us_small_cap_equity | 10465 | 0.2618 | 0.5741 | 0.4229 | -0.0096 | 0.8665 | 0.5046 | 0.0008 |
| XGBHARRSIV | us_technology_sector | 10465 | 0.2977 | 0.6212 | 0.4635 | -0.0379 | 0.8793 | 0.5409 | 0.0008 |
