# HAR-MAX — Self Stats
_universe=`clean_core` · primary horizon h=22 · predictions=`execution/data/predictions/HAR-MAX.parquet` · generated 2026-06-03T18:32:48Z_

_Self-only metrics — no leaderboard rank, no DM test, no MCS, no §9 status._
_Cross-model comparison is produced by the final `rv_eval.evaluator` pass._

## Tier-1 pooled by horizon (§3)
| model | horizon | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-MAX | 1 | 20570 | 0.2755 | 0.7163 | 0.5692 | -0.2052 | 0.8927 | 0.4959 | 0.0000 |
| HAR-MAX | 5 | 20530 | 0.1791 | 0.5494 | 0.4240 | -0.1033 | 0.8969 | 0.5207 | 0.0002 |
| HAR-MAX | 10 | 20480 | 0.2043 | 0.5577 | 0.4225 | -0.0918 | 0.9014 | 0.5358 | 0.0003 |
| HAR-MAX | 22 | 20360 | 0.3571 | 0.6163 | 0.4537 | -0.0934 | 0.9083 | 0.5439 | 0.0008 |
| HAR-MAX | 42 | 20160 | 0.4972 | 0.6953 | 0.4990 | -0.0968 | 0.9055 | 0.5554 | 0.0017 |

## §5 IV-incremental skill (per horizon)
| model | horizon | n | slope | t_slope | sign_acc | qlike_model | qlike_iv | qlike_gain_vs_iv |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-MAX | 1 | 20570 | 0.4814 | 46.2644 | 0.7173 | 0.2755 | 0.3278 | 0.0523 |
| HAR-MAX | 5 | 20530 | 0.3209 | 35.0590 | 0.6752 | 0.1791 | 0.2087 | 0.0296 |
| HAR-MAX | 10 | 20480 | 0.2514 | 17.5327 | 0.6135 | 0.2043 | 0.2201 | 0.0158 |
| HAR-MAX | 22 | 20360 | -0.0173 | -0.9753 | 0.5179 | 0.3571 | 0.3419 | -0.0153 |
| HAR-MAX | 42 | 20160 | -0.0515 | -6.3782 | 0.5016 | 0.4972 | 0.4743 | -0.0229 |

## §6 Conditional bias by IV-percentile bucket (h=22)
| model | horizon | iv_pctile_bucket | n | qlike | log_bias |
| --- | --- | --- | --- | --- | --- |
| HAR-MAX | 22 | 0 | 5149 | 0.1897 | -0.1402 |
| HAR-MAX | 22 | 1 | 3408 | 0.3528 | -0.1476 |
| HAR-MAX | 22 | 2 | 3412 | 0.5255 | -0.1036 |
| HAR-MAX | 22 | 3 | 3497 | 0.3892 | -0.0686 |
| HAR-MAX | 22 | 4 | 4894 | 0.3961 | -0.0171 |

## §6 Post-shock calibration (h=22)
| model | horizon | bias_all | qlike_all | bias_postshock | qlike_postshock | n_postshock | trap_flag |
| --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-MAX | 22 | -0.0934 | 0.3571 | -0.0433 | 0.4263 | 3871 |  |

## Per-ticker Tier-1 at h=22
| model | horizon | ticker | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-MAX | 22 | EEM | 2036 | 0.2661 | 0.5810 | 0.4322 | -0.0493 | 0.8929 | 0.5648 | 0.0007 |
| HAR-MAX | 22 | GLD | 2036 | 0.1414 | 0.4619 | 0.3399 | -0.0173 | 0.8900 | 0.5275 | 0.0003 |
| HAR-MAX | 22 | HYG | 2036 | 0.8371 | 0.8349 | 0.6551 | -0.3382 | 0.9406 | 0.5609 | 0.0002 |
| HAR-MAX | 22 | IWM | 2036 | 0.3267 | 0.5628 | 0.3998 | 0.0239 | 0.8973 | 0.5383 | 0.0010 |
| HAR-MAX | 22 | QQQ | 2036 | 0.3080 | 0.6253 | 0.4715 | -0.0657 | 0.8929 | 0.5511 | 0.0009 |
| HAR-MAX | 22 | SPY | 2036 | 0.4896 | 0.7032 | 0.5232 | -0.0695 | 0.8954 | 0.5437 | 0.0007 |
| HAR-MAX | 22 | TLT | 2036 | 0.2145 | 0.4897 | 0.3455 | -0.0302 | 0.9121 | 0.4646 | 0.0003 |
| HAR-MAX | 22 | XLE | 2036 | 0.2956 | 0.5543 | 0.4004 | -0.0831 | 0.9140 | 0.5467 | 0.0016 |
| HAR-MAX | 22 | XLF | 2036 | 0.3815 | 0.6401 | 0.4956 | -0.1848 | 0.9411 | 0.5820 | 0.0010 |
| HAR-MAX | 22 | XLK | 2036 | 0.3110 | 0.6252 | 0.4743 | -0.1197 | 0.9067 | 0.5594 | 0.0011 |

## Pooled by group
| model | group | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-MAX | emerging_markets | 10210 | 0.2932 | 0.6725 | 0.5096 | -0.1081 | 0.8891 | 0.5252 | 0.0005 |
| HAR-MAX | high_yield_credit | 10210 | 0.6059 | 0.8006 | 0.6229 | -0.3066 | 0.9274 | 0.5520 | 0.0001 |
| HAR-MAX | oil_and_energy | 10210 | 0.2497 | 0.5530 | 0.4062 | -0.0952 | 0.9029 | 0.5328 | 0.0012 |
| HAR-MAX | precious_metals | 10210 | 0.2001 | 0.5987 | 0.4493 | -0.0941 | 0.8841 | 0.5112 | 0.0002 |
| HAR-MAX | us_cyclicals_sector | 10210 | 0.2949 | 0.6146 | 0.4740 | -0.1763 | 0.9322 | 0.5648 | 0.0008 |
| HAR-MAX | us_large_cap_equity | 20420 | 0.3201 | 0.6524 | 0.4951 | -0.0950 | 0.8910 | 0.5284 | 0.0006 |
| HAR-MAX | us_rates_and_ig_credit | 10210 | 0.2071 | 0.5508 | 0.4079 | -0.0682 | 0.8926 | 0.4807 | 0.0002 |
| HAR-MAX | us_small_cap_equity | 10210 | 0.2668 | 0.5570 | 0.4053 | -0.0173 | 0.8929 | 0.5359 | 0.0008 |
| HAR-MAX | us_technology_sector | 10210 | 0.2610 | 0.6138 | 0.4711 | -0.1270 | 0.9056 | 0.5425 | 0.0008 |

---

## Human-only build record (MODEL_PLAN §5)

**File / class / pattern.** `candidate_models/har_max.py:HARMAX` · `name="HAR-MAX"` ·
Pattern P1 (`_AttachMixin` + `_LinearLogHAR`), catalog model 18. Per-(ticker, horizon)
ordinary least squares of `log(target_var)` on 31 features + intercept; lognormal
quantiles via `_lognormal_quantiles`. Deliberately over-parameterised OLS overfit
baseline — the yardstick the Track-B shrinkage models (HAR-ENet/Ridge, model 19, which
reuse this exact feature matrix) must beat.

**Features (31 = 15 pass-through + 16 derived).**
- *Pass-through (already in X via `build_features`/`inputs.parquet`):*
  `HAR_RS_FEATURES` = log_rv_d, log_rv_w, log_rv_m, rs_minus_5d, rs_plus_5d, jump_5d;
  `IV_FEATURES` = log_iv, iv_slope, skew_25d, vix, vix3m, vix_slope, vvix; plus sqrt_rq,
  vix9d_slope.
- *Derived in `_max_panel`, built once on the full point-in-time series and joined by
  (ticker, date) — never recomputed on the predict slice:* lev_d/lev_w/lev_m (signed
  downside ret_cc roll-means, 13 LHAR); sj_5d, abs_sj_5d (5d signed-jump rs_plus−rs_minus,
  14 HAR-SJ); iv_curv, iv_ts_30_90, vrp_lag (= iv_30d²−total_rv, point-in-time), vrp_mom
  (15 HAR-IVTS); log_park_d/w, log_gk_d/w (16 HAR-Range); log_vol_surprise,
  log_txn_surprise, overnight_share (17 HAR-Act). Logs floored at 1e-12 (parkinson/gk/
  volume/transactions can be 0). VRP uses iv_30d² (in X), not targets.iv2 (catalog §4).

**Hyperparameters.** None. No regularization, no cross-validation, no tuning — this is a
plain OLS overfit baseline by design (catalog §3 model 18). `min_obs=100` (inherited
`_LinearLogHAR` gate). No HP-selection step performed.

**Seed.** No stochastic component (deterministic `np.linalg.lstsq`); test uses
`np.random.default_rng(0)`.

**Environment.** python 3.12.13 · polars 1.41.1 · numpy 2.4.6 · scipy 1.17.1
(sklearn 1.8.0 present but unused here). Device: CPU (Darwin 24.3.0, Apple). No GPU.

**Wall-clock.** clean_core walk-forward 17.3s (102,850 OOS preds);
hard_cases 8.8s (37,989 OOS preds). Span 2018-01-02 → 2026-05-21.

**Coverage.** Full — all 10 clean-core and all 5 hard-case tickers × all 5 horizons
(1/5/10/22/42), no missing (ticker, horizon) cell. All rv_hat finite and >0. No
convergence issues (OLS), no dropped/imputed keys.

**Warnings / notes.** Coverage cov90 runs slightly rich (≈0.89–0.91 vs 0.90 nominal) and
cov50 high (≈0.50–0.56); a persistent negative log_bias (over-prediction in log space) at
all horizons, worst on HYG (−0.34) and XLF (−0.18). §5 IV-incremental skill is positive at
short horizons (h=1: +0.052 QLIKE gain vs IV, sign_acc 0.72) but turns negative at the
primary h=22 (−0.015) and h=42 (−0.023) — the over-parameterised fit does not beat raw IV²
at long horizons, exactly the overfit signature this baseline is meant to expose.
