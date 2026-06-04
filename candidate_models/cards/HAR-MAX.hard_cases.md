# HAR-MAX — Self Stats
_universe=`hard_cases` · primary horizon h=22 · predictions=`execution/data/predictions/HAR-MAX.parquet` · generated 2026-06-03T18:32:49Z_

_Self-only metrics — no leaderboard rank, no DM test, no MCS, no §9 status._
_Cross-model comparison is produced by the final `rv_eval.evaluator` pass._

## Tier-1 pooled by horizon (§3)
| model | horizon | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-MAX | 1 | 7636 | 3.2904 | 0.7360 | 0.5684 | -0.2085 | 0.8829 | 0.5010 | 0.0005 |
| HAR-MAX | 5 | 7595 | 1.7570 | 0.6458 | 0.4756 | -0.1142 | 0.8620 | 0.4926 | 0.0024 |
| HAR-MAX | 10 | 7548 | 0.2961 | 0.6479 | 0.4776 | -0.0900 | 0.8429 | 0.4873 | 0.0051 |
| HAR-MAX | 22 | 7488 | 0.4050 | 0.6694 | 0.4886 | -0.0411 | 0.8297 | 0.4701 | 0.0092 |
| HAR-MAX | 42 | 7347 | 0.4699 | 0.7098 | 0.5068 | -0.0039 | 0.8119 | 0.4594 | 0.7209 |

## §5 IV-incremental skill (per horizon)
| model | horizon | n | slope | t_slope | sign_acc | qlike_model | qlike_iv | qlike_gain_vs_iv |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-MAX | 1 | 7636 | 0.1033 | 19.8582 | 0.7534 | 3.2904 | 0.3563 | -2.9341 |
| HAR-MAX | 5 | 7595 | 0.1045 | 17.4707 | 0.7203 | 1.7570 | 0.2630 | -1.4940 |
| HAR-MAX | 10 | 7548 | 0.0087 | 2.9389 | 0.6787 | 0.2961 | 0.2551 | -0.0410 |
| HAR-MAX | 22 | 7488 | 0.3679 | 18.4836 | 0.6262 | 0.4050 | 0.2738 | -0.1312 |
| HAR-MAX | 42 | 7347 | -0.0000 | -0.1621 | 0.6152 | 0.4699 | 0.3189 | -0.1509 |

## §6 Conditional bias by IV-percentile bucket (h=22)
| model | horizon | iv_pctile_bucket | n | qlike | log_bias |
| --- | --- | --- | --- | --- | --- |
| HAR-MAX | 22 | 0 | 1814 | 0.3179 | -0.0721 |
| HAR-MAX | 22 | 1 | 1208 | 0.2554 | -0.0588 |
| HAR-MAX | 22 | 2 | 1318 | 0.2594 | -0.0273 |
| HAR-MAX | 22 | 3 | 1442 | 0.2688 | -0.0966 |
| HAR-MAX | 22 | 4 | 1706 | 0.8313 | 0.0407 |

## §6 Post-shock calibration (h=22)
| model | horizon | bias_all | qlike_all | bias_postshock | qlike_postshock | n_postshock | trap_flag |
| --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-MAX | 22 | -0.0411 | 0.4050 | 0.0067 | 0.7735 | 1396 |  |

## Per-ticker Tier-1 at h=22
| model | horizon | ticker | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-MAX | 22 | IBIT | 224 | 0.1605 | 0.5924 | 0.4366 | -0.0892 | 0.5804 | 0.3125 | 0.0027 |
| HAR-MAX | 22 | KRE | 2036 | 0.3763 | 0.5929 | 0.4071 | -0.0412 | 0.9244 | 0.5796 | 0.0017 |
| HAR-MAX | 22 | MSOS | 1158 | 0.7220 | 0.8040 | 0.6009 | 0.2681 | 0.6174 | 0.2850 | 0.0091 |
| HAR-MAX | 22 | USO | 2036 | 0.3582 | 0.5850 | 0.4090 | 0.0285 | 0.8109 | 0.4700 | 0.0030 |
| HAR-MAX | 22 | UVXY | 2034 | 0.3271 | 0.7406 | 0.5917 | -0.2814 | 0.9022 | 0.4833 | 0.0237 |

## Pooled by group
| model | group | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-MAX | crypto | 1151 | 0.2267 | 0.7093 | 0.5318 | -0.2153 | 0.7133 | 0.3658 | 0.0018 |
| HAR-MAX | long_volatility_vix | 10200 | 0.3057 | 0.7439 | 0.5956 | -0.2867 | 0.8896 | 0.4806 | 0.0164 |
| HAR-MAX | oil_and_energy | 10210 | 2.8411 | 0.6582 | 0.4641 | -0.0457 | 0.8316 | 0.4648 | 0.5102 |
| HAR-MAX | us_cannabis | 5843 | 2.0182 | 0.7793 | 0.5762 | 0.1503 | 0.6978 | 0.3697 | 0.0060 |
| HAR-MAX | us_cyclicals_sector | 10210 | 0.2948 | 0.5715 | 0.4062 | -0.0700 | 0.9173 | 0.5789 | 0.0013 |

---

## Human-only build record (MODEL_PLAN §5)

**File / class / pattern.** `candidate_models/har_max.py:HARMAX` · `name="HAR-MAX"` ·
Pattern P1 (`_AttachMixin` + `_LinearLogHAR`), catalog model 18. Per-(ticker, horizon)
OLS of `log(target_var)` on 31 features + intercept; lognormal quantiles. Deliberately
over-parameterised OLS overfit baseline; reuses the same feature matrix as model 19
(HAR-ENet/Ridge).

**Features (31 = 15 pass-through + 16 derived).** Pass-through `HAR_RS_FEATURES` +
`IV_FEATURES` + sqrt_rq + vix9d_slope (all in X). Derived in `_max_panel`, built once on
the full point-in-time series and joined by (ticker, date): lev_d/w/m (13 LHAR); sj_5d,
abs_sj_5d (14 HAR-SJ); iv_curv, iv_ts_30_90, vrp_lag=iv_30d²−total_rv, vrp_mom (15
HAR-IVTS); log_park_d/w, log_gk_d/w (16 HAR-Range); log_vol_surprise, log_txn_surprise,
overnight_share (17 HAR-Act). Logs floored at 1e-12. VRP uses iv_30d² (in X), not
targets.iv2 (catalog §4).

**Hyperparameters.** None — no regularization, no CV, no tuning (overfit baseline by
design). `min_obs=100` inherited gate. No HP-selection step.

**Seed.** Deterministic `np.linalg.lstsq`; no stochastic component.

**Environment.** python 3.12.13 · polars 1.41.1 · numpy 2.4.6 · scipy 1.17.1.
Device: CPU (Darwin 24.3.0, Apple). No GPU.

**Wall-clock.** hard_cases walk-forward 8.8s (37,989 OOS preds); clean_core 17.3s.
Span 2018-01-02 → 2026-05-21.

**Coverage.** All 5 hard-case tickers (UVXY, MSOS, IBIT, USO, KRE) × all 5 horizons
present. Note thin-history tickers have far fewer OOS rows at h=22: IBIT n=224, MSOS
n=1158 (late listings) vs ~2036 for KRE/USO/UVXY — driven by the `min_obs=100` train gate
and shorter panels, not imputed. All rv_hat finite and >0; no convergence failures.

**Warnings / notes.** As expected for an unregularized kitchen-sink fit on hard cases, tail
behaviour is poor: pooled QLIKE blows up on oil_and_energy/USO (group QLIKE 2.84, pinball
0.51) and us_cannabis/MSOS (group QLIKE 2.02) — heavy right-tail RV the lognormal mean
over-shoots after over-fit slopes. Coverage is too thin (under-dispersed) for the
short-history / crypto / cannabis names (IBIT cov90 0.58, MSOS cov90 0.62, cov50 ≈0.29–0.31
vs 0.50 nominal). UVXY shows large negative log_bias (−0.28). These are the overfit
pathologies this baseline is meant to surface for the shrinkage models to fix.
