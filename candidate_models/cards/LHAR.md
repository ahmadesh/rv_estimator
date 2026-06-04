# LHAR — Self Stats
_universe=`clean_core` · primary horizon h=22 · predictions=`execution/data/predictions/LHAR.parquet` · generated 2026-06-03T18:00:08Z_

_Self-only metrics — no leaderboard rank, no DM test, no MCS, no §9 status._
_Cross-model comparison is produced by the final `rv_eval.evaluator` pass._

## Tier-1 pooled by horizon (§3)
| model | horizon | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LHAR | 1 | 21080 | 0.3109 | 0.7805 | 0.6183 | -0.2499 | 0.8916 | 0.4967 | 0.0001 |
| LHAR | 5 | 21040 | 0.2049 | 0.6071 | 0.4707 | -0.1442 | 0.8969 | 0.5284 | 0.0002 |
| LHAR | 10 | 20990 | 0.2213 | 0.6085 | 0.4677 | -0.1415 | 0.9052 | 0.5480 | 0.0004 |
| LHAR | 22 | 20870 | 0.3207 | 0.6567 | 0.4978 | -0.1605 | 0.9155 | 0.5631 | 0.0008 |
| LHAR | 42 | 20670 | 0.4182 | 0.7276 | 0.5397 | -0.1846 | 0.9205 | 0.5771 | 0.0016 |

## §5 IV-incremental skill (per horizon)
| model | horizon | n | slope | t_slope | sign_acc | qlike_model | qlike_iv | qlike_gain_vs_iv |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LHAR | 1 | 20820 | 0.0335 | 20.2668 | 0.6497 | 0.3104 | 0.3276 | 0.0172 |
| LHAR | 5 | 20780 | 0.1169 | 39.6596 | 0.6051 | 0.2051 | 0.2079 | 0.0028 |
| LHAR | 10 | 20730 | 0.1154 | 23.4719 | 0.5592 | 0.2221 | 0.2187 | -0.0034 |
| LHAR | 22 | 20610 | 0.0106 | 1.2228 | 0.5124 | 0.3222 | 0.3396 | 0.0173 |
| LHAR | 42 | 20410 | -0.0340 | -3.2085 | 0.4923 | 0.4216 | 0.4697 | 0.0481 |

## §6 Conditional bias by IV-percentile bucket (h=22)
| model | horizon | iv_pctile_bucket | n | qlike | log_bias |
| --- | --- | --- | --- | --- | --- |
| LHAR | 22 | 0 | 5500 | 0.1802 | -0.2101 |
| LHAR | 22 | 1 | 3449 | 0.3097 | -0.1980 |
| LHAR | 22 | 2 | 3439 | 0.4536 | -0.1496 |
| LHAR | 22 | 3 | 3533 | 0.3767 | -0.1199 |
| LHAR | 22 | 4 | 4949 | 0.3523 | -0.1160 |

## §6 Post-shock calibration (h=22)
| model | horizon | bias_all | qlike_all | bias_postshock | qlike_postshock | n_postshock | trap_flag |
| --- | --- | --- | --- | --- | --- | --- | --- |
| LHAR | 22 | -0.1605 | 0.3207 | -0.2620 | 0.3617 | 3986 |  |

## Per-ticker Tier-1 at h=22
| model | horizon | ticker | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LHAR | 22 | EEM | 2087 | 0.2407 | 0.6836 | 0.5608 | -0.3346 | 0.9578 | 0.6368 | 0.0008 |
| LHAR | 22 | GLD | 2087 | 0.1726 | 0.5321 | 0.4168 | -0.1092 | 0.8725 | 0.4729 | 0.0004 |
| LHAR | 22 | HYG | 2087 | 0.6562 | 0.9990 | 0.8267 | -0.6467 | 0.9722 | 0.6943 | 0.0002 |
| LHAR | 22 | IWM | 2087 | 0.2799 | 0.5707 | 0.4270 | -0.0418 | 0.8984 | 0.4988 | 0.0010 |
| LHAR | 22 | QQQ | 2087 | 0.2855 | 0.6088 | 0.4667 | -0.0690 | 0.9358 | 0.6354 | 0.0008 |
| LHAR | 22 | SPY | 2087 | 0.4286 | 0.7043 | 0.5422 | -0.1015 | 0.8955 | 0.5012 | 0.0008 |
| LHAR | 22 | TLT | 2087 | 0.2126 | 0.5152 | 0.3736 | -0.0292 | 0.8855 | 0.4983 | 0.0003 |
| LHAR | 22 | XLE | 2087 | 0.2745 | 0.5493 | 0.3943 | -0.0487 | 0.9080 | 0.5755 | 0.0015 |
| LHAR | 22 | XLF | 2087 | 0.3637 | 0.6624 | 0.5174 | -0.1904 | 0.9243 | 0.5640 | 0.0012 |
| LHAR | 22 | XLK | 2087 | 0.2928 | 0.6047 | 0.4522 | -0.0343 | 0.9051 | 0.5534 | 0.0011 |

## Pooled by group
| model | group | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LHAR | emerging_markets | 10465 | 0.2966 | 0.7781 | 0.6264 | -0.3490 | 0.9298 | 0.5787 | 0.0006 |
| LHAR | high_yield_credit | 10465 | 0.5076 | 0.9369 | 0.7628 | -0.5398 | 0.9564 | 0.6435 | 0.0002 |
| LHAR | oil_and_energy | 10465 | 0.2502 | 0.5650 | 0.4147 | -0.0726 | 0.8960 | 0.5413 | 0.0011 |
| LHAR | precious_metals | 10465 | 0.2366 | 0.6670 | 0.5175 | -0.1816 | 0.8716 | 0.4698 | 0.0003 |
| LHAR | us_cyclicals_sector | 10465 | 0.3020 | 0.6485 | 0.5004 | -0.1833 | 0.9233 | 0.5667 | 0.0009 |
| LHAR | us_large_cap_equity | 20930 | 0.3093 | 0.6660 | 0.5107 | -0.1072 | 0.9026 | 0.5473 | 0.0006 |
| LHAR | us_rates_and_ig_credit | 10465 | 0.2204 | 0.5859 | 0.4395 | -0.0832 | 0.8839 | 0.4977 | 0.0002 |
| LHAR | us_small_cap_equity | 10465 | 0.2503 | 0.5773 | 0.4329 | -0.0651 | 0.8920 | 0.5048 | 0.0007 |
| LHAR | us_technology_sector | 10465 | 0.2653 | 0.6205 | 0.4729 | -0.0726 | 0.9004 | 0.5275 | 0.0008 |

---

## Model provenance (human-only, MODEL_PLAN §5)

**Model.** LHAR — leverage-HAR (Corsi-Renò 2012). Per-(ticker, horizon) OLS of
`log(target_var)` on HAR lags plus signed-downside-return aggregates. Base:
`_AttachMixin` + `_LinearLogHAR` (Pattern P1). File: `candidate_models/lhar.py`,
class `LHAR`, `name="LHAR"`.

**Features used.** `needs = HAR_FEATURES + ["lev_d","lev_w","lev_m"]`
= `["log_rv_d","log_rv_w","log_rv_m","lev_d","lev_w","lev_m"]` plus the OLS intercept.

**Derived columns (built on FULL series, joined by (ticker,date) — leak-safe).**
From `inputs.parquet::ret_cc` (close-to-close log return):
- `lev_d = rolling_mean(min(ret_cc,0), 1)` (= today's downside return)
- `lev_w = rolling_mean(min(ret_cc,0), 5)`
- `lev_m = rolling_mean(min(ret_cc,0), 22)`

Trailing windows include today; built once via `_AttachMixin._derive` on the full
point-in-time series and joined — never recomputed on the predict slice. `min_samples`
matches the window so leading rows are null (dropped at fit, propagate at predict),
exactly as `features.py`/`har_cj.py` do.

**Hyperparameters.** None. Plain OLS, no regularisation, no tuning. Inherited gates:
`min_obs=100` (per ticker×horizon to fit), `horizons=(1,5,10,22,42)`. No HP selection
was performed (nothing to select) — no train/OOS peeking possible.

**Quantiles / sigma.** Lognormal via `_lognormal_quantiles(m, s)` where `s` =
in-sample log-residual std (per ticker×horizon), `m = exp(mu + 0.5 s^2)`. Quantiles
verified non-decreasing in the smoke test.

**Seed.** None used at fit/predict (deterministic OLS). Test panel uses `np.random.default_rng(0)`.

**Coverage.** All 10 clean_core tickers × all 5 horizons predicted; no
convergence/thin-data drops, no imputation. rv_hat finite and > 0 on every row.
105,450 OOS rows (clean_core), span 2018-01-02 → 2026-05-22.

**Warnings.** Negative log-bias across horizons (under-prediction of variance), most
pronounced for HYG and EEM and in the post-shock window (bias_postshock -0.262 at
h=22) — typical of log-OLS HAR; flagged for the comparison pass, not corrected here.
cov90 mildly over-covers at long horizons (~0.92 at h=42).

**Environment.** python 3.12.13 · polars 1.41.1 · numpy 2.4.6 (scipy via
`rv_eval.model_contract`). Device: CPU, Apple arm64 (macOS-15.3.1-arm64).
Wall-clock: clean_core walk-forward ≈ 9.6 s (both fit+predict, all folds/horizons).
