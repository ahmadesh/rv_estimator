# XGBHARRSIV — Model Card (hard_cases)

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
_universe=`hard_cases` · primary horizon h=22 · predictions=`execution/data/predictions/XGBHARRSIV.parquet` · generated 2026-06-01T06:58:07Z_

_Self-only metrics — no leaderboard rank, no DM test, no MCS, no §9 status._
_Cross-model comparison is produced by the final `rv_eval.evaluator` pass._

## Tier-1 pooled by horizon (§3)
| model | horizon | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| XGBHARRSIV | 1 | 7840 | 0.3210 | 0.7535 | 0.5887 | -0.2409 | 0.8879 | 0.5114 | 0.0004 |
| XGBHARRSIV | 5 | 7820 | 0.2714 | 0.6564 | 0.4955 | -0.1486 | 0.8710 | 0.5063 | 0.0020 |
| XGBHARRSIV | 10 | 7774 | 0.2877 | 0.6595 | 0.4930 | -0.1139 | 0.8442 | 0.4973 | 0.0043 |
| XGBHARRSIV | 22 | 7692 | 0.3312 | 0.6724 | 0.5043 | -0.0552 | 0.8006 | 0.4537 | 0.0094 |
| XGBHARRSIV | 42 | 7551 | 0.3966 | 0.6999 | 0.5223 | 0.0143 | 0.7294 | 0.3945 | 0.0168 |

## §5 IV-incremental skill (per horizon)
| model | horizon | n | slope | t_slope | sign_acc | qlike_model | qlike_iv | qlike_gain_vs_iv |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| XGBHARRSIV | 1 | 7735 | 1.3361 | 37.3687 | 0.7427 | 0.3179 | 0.3573 | 0.0394 |
| XGBHARRSIV | 5 | 7715 | 0.8828 | 25.1911 | 0.6979 | 0.2684 | 0.2619 | -0.0065 |
| XGBHARRSIV | 10 | 7669 | 0.5981 | 21.1184 | 0.6344 | 0.2850 | 0.2545 | -0.0305 |
| XGBHARRSIV | 22 | 7587 | 0.6684 | 32.1597 | 0.5846 | 0.3296 | 0.2748 | -0.0548 |
| XGBHARRSIV | 42 | 7446 | 0.8187 | 53.0459 | 0.5998 | 0.3977 | 0.3176 | -0.0802 |

## §6 Conditional bias by IV-percentile bucket (h=22)
| model | horizon | iv_pctile_bucket | n | qlike | log_bias |
| --- | --- | --- | --- | --- | --- |
| XGBHARRSIV | 22 | 0 | 1954 | 0.2967 | -0.2339 |
| XGBHARRSIV | 22 | 1 | 1229 | 0.2426 | -0.1203 |
| XGBHARRSIV | 22 | 2 | 1335 | 0.2632 | -0.0449 |
| XGBHARRSIV | 22 | 3 | 1451 | 0.2976 | -0.0565 |
| XGBHARRSIV | 22 | 4 | 1723 | 0.5145 | 0.1872 |

## §6 Post-shock calibration (h=22)
| model | horizon | bias_all | qlike_all | bias_postshock | qlike_postshock | n_postshock | trap_flag |
| --- | --- | --- | --- | --- | --- | --- | --- |
| XGBHARRSIV | 22 | -0.0552 | 0.3312 | 0.1155 | 0.4582 | 1433 | ✓ |

## Per-ticker Tier-1 at h=22
| model | horizon | ticker | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| XGBHARRSIV | 22 | IBIT | 224 | 0.1594 | 0.5960 | 0.5014 | -0.0992 | 0.3080 | 0.1429 | 0.0032 |
| XGBHARRSIV | 22 | KRE | 2087 | 0.3549 | 0.5909 | 0.4028 | -0.0027 | 0.8884 | 0.5496 | 0.0018 |
| XGBHARRSIV | 22 | MSOS | 1207 | 0.2961 | 0.6401 | 0.5051 | 0.3173 | 0.6181 | 0.3099 | 0.0081 |
| XGBHARRSIV | 22 | USO | 2087 | 0.3194 | 0.6367 | 0.4627 | -0.0177 | 0.8409 | 0.4715 | 0.0034 |
| XGBHARRSIV | 22 | UVXY | 2087 | 0.3581 | 0.7980 | 0.6473 | -0.3558 | 0.8309 | 0.4566 | 0.0244 |

## Pooled by group
| model | group | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| XGBHARRSIV | crypto | 1172 | 0.2097 | 0.6926 | 0.5612 | -0.2060 | 0.5145 | 0.2415 | 0.0021 |
| XGBHARRSIV | long_volatility_vix | 10465 | 0.3315 | 0.7985 | 0.6476 | -0.3657 | 0.8527 | 0.4600 | 0.0164 |
| XGBHARRSIV | oil_and_energy | 10465 | 0.3397 | 0.6885 | 0.5080 | -0.0861 | 0.8526 | 0.4848 | 0.0026 |
| XGBHARRSIV | us_cannabis | 6110 | 0.3341 | 0.6569 | 0.5049 | 0.1628 | 0.7056 | 0.3990 | 0.0057 |
| XGBHARRSIV | us_cyclicals_sector | 10465 | 0.2969 | 0.5822 | 0.4119 | -0.0265 | 0.8831 | 0.5442 | 0.0014 |
