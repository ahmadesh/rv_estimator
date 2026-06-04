# HAR-SJ — Self Stats
_universe=`clean_core` · primary horizon h=22 · predictions=`execution/data/predictions/HAR-SJ.parquet` · generated 2026-06-03T18:03:39Z_

_Self-only metrics — no leaderboard rank, no DM test, no MCS, no §9 status._
_Cross-model comparison is produced by the final `rv_eval.evaluator` pass._

## Tier-1 pooled by horizon (§3)
| model | horizon | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-SJ | 1 | 21080 | 0.3192 | 0.7926 | 0.6282 | -0.2570 | 0.8907 | 0.4946 | 0.0001 |
| HAR-SJ | 5 | 21040 | 0.2113 | 0.6191 | 0.4780 | -0.1488 | 0.8975 | 0.5280 | 0.0002 |
| HAR-SJ | 10 | 20990 | 0.2273 | 0.6178 | 0.4727 | -0.1435 | 0.9053 | 0.5469 | 0.0004 |
| HAR-SJ | 22 | 20870 | 0.3255 | 0.6624 | 0.4990 | -0.1599 | 0.9122 | 0.5652 | 0.0009 |
| HAR-SJ | 42 | 20670 | 0.4216 | 0.7314 | 0.5389 | -0.1836 | 0.9188 | 0.5806 | 0.0017 |

## §5 IV-incremental skill (per horizon)
| model | horizon | n | slope | t_slope | sign_acc | qlike_model | qlike_iv | qlike_gain_vs_iv |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-SJ | 1 | 20820 | 0.0232 | 12.3561 | 0.6357 | 0.3187 | 0.3276 | 0.0089 |
| HAR-SJ | 5 | 20780 | 0.0364 | 13.4752 | 0.5961 | 0.2115 | 0.2079 | -0.0036 |
| HAR-SJ | 10 | 20730 | 0.0191 | 5.6544 | 0.5514 | 0.2280 | 0.2187 | -0.0094 |
| HAR-SJ | 22 | 20610 | -0.0207 | -4.1443 | 0.5106 | 0.3271 | 0.3396 | 0.0125 |
| HAR-SJ | 42 | 20410 | -0.0375 | -5.6259 | 0.4975 | 0.4251 | 0.4697 | 0.0446 |

## §6 Conditional bias by IV-percentile bucket (h=22)
| model | horizon | iv_pctile_bucket | n | qlike | log_bias |
| --- | --- | --- | --- | --- | --- |
| HAR-SJ | 22 | 0 | 5500 | 0.1792 | -0.2226 |
| HAR-SJ | 22 | 1 | 3449 | 0.3074 | -0.2036 |
| HAR-SJ | 22 | 2 | 3439 | 0.4472 | -0.1558 |
| HAR-SJ | 22 | 3 | 3533 | 0.3734 | -0.1116 |
| HAR-SJ | 22 | 4 | 4949 | 0.3818 | -0.0970 |

## §6 Post-shock calibration (h=22)
| model | horizon | bias_all | qlike_all | bias_postshock | qlike_postshock | n_postshock | trap_flag |
| --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-SJ | 22 | -0.1599 | 0.3255 | -0.2519 | 0.3948 | 3986 |  |

## Per-ticker Tier-1 at h=22
| model | horizon | ticker | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-SJ | 22 | EEM | 2087 | 0.2360 | 0.6556 | 0.5364 | -0.3048 | 0.9617 | 0.6493 | 0.0007 |
| HAR-SJ | 22 | GLD | 2087 | 0.1817 | 0.5408 | 0.4183 | -0.1086 | 0.8673 | 0.4902 | 0.0004 |
| HAR-SJ | 22 | HYG | 2087 | 0.6526 | 0.9945 | 0.8212 | -0.6410 | 0.9717 | 0.6881 | 0.0002 |
| HAR-SJ | 22 | IWM | 2087 | 0.2940 | 0.5897 | 0.4352 | -0.0470 | 0.8908 | 0.5002 | 0.0012 |
| HAR-SJ | 22 | QQQ | 2087 | 0.2870 | 0.6331 | 0.4774 | -0.0821 | 0.9272 | 0.6344 | 0.0012 |
| HAR-SJ | 22 | SPY | 2087 | 0.4363 | 0.7129 | 0.5503 | -0.1000 | 0.8888 | 0.5017 | 0.0007 |
| HAR-SJ | 22 | TLT | 2087 | 0.2205 | 0.5537 | 0.3810 | -0.0449 | 0.8826 | 0.5007 | 0.0007 |
| HAR-SJ | 22 | XLE | 2087 | 0.2814 | 0.5544 | 0.3963 | -0.0506 | 0.9075 | 0.5750 | 0.0016 |
| HAR-SJ | 22 | XLF | 2087 | 0.3653 | 0.6615 | 0.5214 | -0.1961 | 0.9281 | 0.5611 | 0.0011 |
| HAR-SJ | 22 | XLK | 2087 | 0.2999 | 0.6072 | 0.4526 | -0.0236 | 0.8965 | 0.5515 | 0.0011 |

## Pooled by group
| model | group | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-SJ | emerging_markets | 10465 | 0.2923 | 0.7542 | 0.6048 | -0.3202 | 0.9325 | 0.5813 | 0.0005 |
| HAR-SJ | high_yield_credit | 10465 | 0.5060 | 0.9370 | 0.7631 | -0.5383 | 0.9576 | 0.6456 | 0.0002 |
| HAR-SJ | oil_and_energy | 10465 | 0.2588 | 0.5701 | 0.4169 | -0.0756 | 0.8973 | 0.5453 | 0.0011 |
| HAR-SJ | precious_metals | 10465 | 0.2396 | 0.6675 | 0.5161 | -0.1803 | 0.8705 | 0.4727 | 0.0003 |
| HAR-SJ | us_cyclicals_sector | 10465 | 0.3106 | 0.6560 | 0.5095 | -0.1920 | 0.9257 | 0.5667 | 0.0008 |
| HAR-SJ | us_large_cap_equity | 20930 | 0.3180 | 0.6896 | 0.5266 | -0.1220 | 0.8993 | 0.5414 | 0.0007 |
| HAR-SJ | us_rates_and_ig_credit | 10465 | 0.2242 | 0.6179 | 0.4459 | -0.0951 | 0.8823 | 0.5031 | 0.0005 |
| HAR-SJ | us_small_cap_equity | 10465 | 0.2621 | 0.5976 | 0.4458 | -0.0759 | 0.8878 | 0.5050 | 0.0009 |
| HAR-SJ | us_technology_sector | 10465 | 0.2757 | 0.6288 | 0.4784 | -0.0643 | 0.8961 | 0.5262 | 0.0008 |

---

## Build provenance (human-only fields)

**Model.** `candidate_models/har_sj.py:HARSJ` · `name="HAR-SJ"` · pattern P1 (Linear-log HAR + derived join). Per-(ticker, horizon) OLS of `log(target_var)` via the inherited `_LinearLogHAR` (lognormal mean correction; lognormal quantiles via `_lognormal_quantiles`). Ref: Patton & Sheppard (2015), *Good Volatility, Bad Volatility*.

**Features used (`needs`).** `["log_rv_d", "log_rv_w", "log_rv_m", "rs_minus_5d", "rs_plus_5d", "sj_5d", "abs_sj_5d"]` — the HAR-RS block minus the unsigned `jump_5d` (replaced by the signed terms), plus two derived signed-jump columns. `log_rv_*`, `rs_plus_5d`, `rs_minus_5d` come from `features.build_features`; `rs_plus`/`rs_minus` are raw inputs.

**Derived columns (built once on full series, joined by (ticker,date) via `_AttachMixin`).**
- `sj_5d  = rolling_mean(rs_plus - rs_minus, 5, min_samples=5).over(ticker)` — weekly signed-jump (good minus bad variation).
- `abs_sj_5d = |sj_5d|` — its magnitude.
Trailing window is computed on the full point-in-time series (never recomputed on the one-month walk-forward slice), so no leakage and no null-leading-row corruption.

**Hyperparameters.** None free. Fixed structural choices: signed-jump window = 5 trading days (weekly, matching the existing HAR-RS `rs_*_5d` cadence in `features.py`); `min_obs=100` (inherited `_LinearLogHAR` default). No tuning performed — nothing selected on OOS or via cross-model peeking.

**Seed.** None (deterministic OLS via `numpy.linalg.lstsq`; no stochastic component).

**Coverage.** All 15 scored tickers x 5 horizons covered; no tickers/horizons dropped. All rv_hat finite and > 0; quantiles monotone (enforced by lognormal construction). No convergence issues (closed-form OLS).

**Environment.** python 3.12.13 · numpy 2.4.6 · polars 1.41.1 · scipy 1.17.1. Device: CPU (Apple arm64, macOS 15.3.1). 

**Wall-clock.** clean_core walk-forward ~9.6s (105,450 OOS preds); hard_cases ~4.9s (40,810 OOS preds). Combined parquet: 146,260 rows, span 2018-01-02 to 2026-05-22.
