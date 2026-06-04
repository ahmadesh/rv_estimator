# LHAR — Self Stats
_universe=`hard_cases` · primary horizon h=22 · predictions=`execution/data/predictions/LHAR.parquet` · generated 2026-06-03T18:00:08Z_

_Self-only metrics — no leaderboard rank, no DM test, no MCS, no §9 status._
_Cross-model comparison is produced by the final `rv_eval.evaluator` pass._

## Tier-1 pooled by horizon (§3)
| model | horizon | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LHAR | 1 | 8196 | 0.3368 | 0.7698 | 0.6039 | -0.2604 | 0.8992 | 0.5217 | 0.0004 |
| LHAR | 5 | 8153 | 0.2710 | 0.6628 | 0.5043 | -0.1736 | 0.8875 | 0.5131 | 0.0020 |
| LHAR | 10 | 8108 | 0.2780 | 0.6652 | 0.5016 | -0.1596 | 0.8728 | 0.5060 | 0.0041 |
| LHAR | 22 | 8048 | 0.3031 | 0.6684 | 0.5089 | -0.1290 | 0.8639 | 0.4929 | 0.0087 |
| LHAR | 42 | 7905 | 0.3277 | 0.6750 | 0.5128 | -0.1018 | 0.8444 | 0.4721 | 0.0153 |

## §5 IV-incremental skill (per horizon)
| model | horizon | n | slope | t_slope | sign_acc | qlike_model | qlike_iv | qlike_gain_vs_iv |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LHAR | 1 | 7906 | 0.7791 | 23.3389 | 0.7036 | 0.3307 | 0.3595 | 0.0288 |
| LHAR | 5 | 7863 | 0.6535 | 22.3819 | 0.6598 | 0.2674 | 0.2624 | -0.0051 |
| LHAR | 10 | 7838 | 0.5557 | 23.2264 | 0.6124 | 0.2755 | 0.2542 | -0.0213 |
| LHAR | 22 | 7778 | 0.6377 | 33.5663 | 0.5728 | 0.3020 | 0.2732 | -0.0289 |
| LHAR | 42 | 7657 | 0.7673 | 52.7043 | 0.5639 | 0.3328 | 0.3134 | -0.0194 |

## §6 Conditional bias by IV-percentile bucket (h=22)
| model | horizon | iv_pctile_bucket | n | qlike | log_bias |
| --- | --- | --- | --- | --- | --- |
| LHAR | 22 | 0 | 2078 | 0.3099 | -0.2282 |
| LHAR | 22 | 1 | 1264 | 0.2456 | -0.1356 |
| LHAR | 22 | 2 | 1355 | 0.2520 | -0.0702 |
| LHAR | 22 | 3 | 1460 | 0.2740 | -0.0863 |
| LHAR | 22 | 4 | 1727 | 0.3984 | -0.0412 |

## §6 Post-shock calibration (h=22)
| model | horizon | bias_all | qlike_all | bias_postshock | qlike_postshock | n_postshock | trap_flag |
| --- | --- | --- | --- | --- | --- | --- | --- |
| LHAR | 22 | -0.1290 | 0.3031 | -0.1970 | 0.3221 | 1487 |  |

## Per-ticker Tier-1 at h=22
| model | horizon | ticker | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LHAR | 22 | IBIT | 517 | 0.2353 | 0.7908 | 0.6627 | -0.5415 | 0.6963 | 0.4236 | 0.0043 |
| LHAR | 22 | KRE | 2087 | 0.3311 | 0.6062 | 0.4429 | -0.0928 | 0.9291 | 0.5692 | 0.0018 |
| LHAR | 22 | MSOS | 1270 | 0.2739 | 0.6414 | 0.4929 | 0.0696 | 0.8063 | 0.4591 | 0.0070 |
| LHAR | 22 | USO | 2087 | 0.2780 | 0.6170 | 0.4492 | -0.0099 | 0.8289 | 0.4605 | 0.0036 |
| LHAR | 22 | UVXY | 2087 | 0.3346 | 0.7547 | 0.6063 | -0.3029 | 0.9104 | 0.4868 | 0.0228 |

## Pooled by group
| model | group | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LHAR | crypto | 2633 | 0.3006 | 0.8627 | 0.7082 | -0.5544 | 0.8355 | 0.4812 | 0.0028 |
| LHAR | long_volatility_vix | 10465 | 0.3194 | 0.7683 | 0.6179 | -0.3115 | 0.8980 | 0.4909 | 0.0155 |
| LHAR | oil_and_energy | 10465 | 0.3083 | 0.6723 | 0.5006 | -0.0779 | 0.8359 | 0.4559 | 0.0028 |
| LHAR | us_cannabis | 6382 | 0.3064 | 0.6468 | 0.4895 | -0.0111 | 0.8400 | 0.4920 | 0.0049 |
| LHAR | us_cyclicals_sector | 10465 | 0.2806 | 0.5936 | 0.4380 | -0.1032 | 0.9177 | 0.5682 | 0.0013 |

---

## Model provenance (human-only, MODEL_PLAN §5)

**Model.** LHAR — leverage-HAR (Corsi-Renò 2012). Per-(ticker, horizon) OLS of
`log(target_var)` on HAR lags plus signed-downside-return aggregates. Base:
`_AttachMixin` + `_LinearLogHAR` (Pattern P1). File: `candidate_models/lhar.py`,
class `LHAR`, `name="LHAR"`.

**Features used.** `needs = HAR_FEATURES + ["lev_d","lev_w","lev_m"]`
= `["log_rv_d","log_rv_w","log_rv_m","lev_d","lev_w","lev_m"]` plus the OLS intercept.

**Derived columns (built on FULL series, joined by (ticker,date) — leak-safe).**
From `inputs.parquet::ret_cc`:
- `lev_d = rolling_mean(min(ret_cc,0), 1)`
- `lev_w = rolling_mean(min(ret_cc,0), 5)`
- `lev_m = rolling_mean(min(ret_cc,0), 22)`

Built once via `_AttachMixin._derive` on the full series and joined by (ticker,date) —
never recomputed on the predict slice.

**Hyperparameters.** None (plain OLS). Gates: `min_obs=100`, `horizons=(1,5,10,22,42)`.
No HP selection performed.

**Quantiles / sigma.** Lognormal via `_lognormal_quantiles(m, s)`, `s` = in-sample
log-residual std per ticker×horizon.

**Seed.** None at fit/predict (deterministic).

**Coverage.** All 5 hard_cases tickers (UVXY, MSOS, IBIT, USO, KRE) × all 5 horizons
predicted; no drops, no imputation. rv_hat finite and > 0 everywhere. 40,810 OOS rows,
span 2018-01-02 → 2026-05-22. IBIT/MSOS have shorter histories (fewer rows) but still
clear `min_obs`.

**Warnings.** Negative log-bias on the high-vol names (IBIT, UVXY: bias ≈ -0.31 to
-0.55) and under-coverage (cov90 ≈ 0.84 on crypto/oil) — expected for log-OLS on
fat-tailed hard cases; flagged for the comparison pass, not corrected here.

**Environment.** python 3.12.13 · polars 1.41.1 · numpy 2.4.6. Device: CPU, Apple
arm64 (macOS-15.3.1-arm64). Wall-clock: hard_cases walk-forward ≈ 4.9 s.
