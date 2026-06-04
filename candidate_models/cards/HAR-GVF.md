# HAR-GVF — Self Stats
_universe=`clean_core` · primary horizon h=22 · predictions=`execution/data/predictions/HAR-GVF.parquet` · generated 2026-06-03T21:25:15Z_

_Self-only metrics — no leaderboard rank, no DM test, no MCS, no §9 status._
_Cross-model comparison is produced by the final `rv_eval.evaluator` pass._

## Tier-1 pooled by horizon (§3)
| model | horizon | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-GVF | 1 | 21080 | 0.3187 | 0.7984 | 0.6349 | -0.2729 | 0.8907 | 0.4950 | 0.0000 |
| HAR-GVF | 5 | 21040 | 0.2103 | 0.6222 | 0.4845 | -0.1626 | 0.8974 | 0.5234 | 0.0002 |
| HAR-GVF | 10 | 20990 | 0.2263 | 0.6203 | 0.4791 | -0.1561 | 0.9048 | 0.5441 | 0.0003 |
| HAR-GVF | 22 | 20870 | 0.3252 | 0.6631 | 0.5042 | -0.1686 | 0.9143 | 0.5598 | 0.0008 |
| HAR-GVF | 42 | 20670 | 0.4249 | 0.7333 | 0.5443 | -0.1905 | 0.9201 | 0.5783 | 0.0015 |

## §5 IV-incremental skill (per horizon)
| model | horizon | n | slope | t_slope | sign_acc | qlike_model | qlike_iv | qlike_gain_vs_iv |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-GVF | 1 | 20820 | 1.1259 | 51.3553 | 0.6226 | 0.3182 | 0.3276 | 0.0095 |
| HAR-GVF | 5 | 20780 | 1.0348 | 51.0455 | 0.5825 | 0.2105 | 0.2079 | -0.0026 |
| HAR-GVF | 10 | 20730 | 0.7197 | 30.1243 | 0.5381 | 0.2269 | 0.2187 | -0.0083 |
| HAR-GVF | 22 | 20610 | 0.2939 | 10.4506 | 0.5041 | 0.3267 | 0.3396 | 0.0129 |
| HAR-GVF | 42 | 20410 | 0.3000 | 11.3217 | 0.4913 | 0.4284 | 0.4697 | 0.0413 |

## §6 Conditional bias by IV-percentile bucket (h=22)
| model | horizon | iv_pctile_bucket | n | qlike | log_bias |
| --- | --- | --- | --- | --- | --- |
| HAR-GVF | 22 | 0 | 5500 | 0.1841 | -0.2214 |
| HAR-GVF | 22 | 1 | 3449 | 0.3157 | -0.2109 |
| HAR-GVF | 22 | 2 | 3439 | 0.4532 | -0.1700 |
| HAR-GVF | 22 | 3 | 3533 | 0.3760 | -0.1384 |
| HAR-GVF | 22 | 4 | 4949 | 0.3635 | -0.1012 |

## §6 Post-shock calibration (h=22)
| model | horizon | bias_all | qlike_all | bias_postshock | qlike_postshock | n_postshock | trap_flag |
| --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-GVF | 22 | -0.1686 | 0.3252 | -0.2524 | 0.3747 | 3986 |  |

## Per-ticker Tier-1 at h=22
| model | horizon | ticker | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-GVF | 22 | EEM | 2087 | 0.2408 | 0.7003 | 0.5813 | -0.3816 | 0.9612 | 0.6172 | 0.0008 |
| HAR-GVF | 22 | GLD | 2087 | 0.1832 | 0.5496 | 0.4317 | -0.1302 | 0.8630 | 0.4662 | 0.0004 |
| HAR-GVF | 22 | HYG | 2087 | 0.6608 | 0.9965 | 0.8225 | -0.6375 | 0.9727 | 0.6929 | 0.0002 |
| HAR-GVF | 22 | IWM | 2087 | 0.2842 | 0.5753 | 0.4283 | -0.0388 | 0.8965 | 0.5036 | 0.0010 |
| HAR-GVF | 22 | QQQ | 2087 | 0.2858 | 0.6150 | 0.4726 | -0.0712 | 0.9305 | 0.6306 | 0.0008 |
| HAR-GVF | 22 | SPY | 2087 | 0.4363 | 0.7155 | 0.5536 | -0.1090 | 0.8936 | 0.5046 | 0.0007 |
| HAR-GVF | 22 | TLT | 2087 | 0.2096 | 0.5123 | 0.3717 | -0.0288 | 0.8855 | 0.4940 | 0.0003 |
| HAR-GVF | 22 | XLE | 2087 | 0.2780 | 0.5499 | 0.3933 | -0.0503 | 0.9109 | 0.5759 | 0.0015 |
| HAR-GVF | 22 | XLF | 2087 | 0.3692 | 0.6752 | 0.5335 | -0.2161 | 0.9276 | 0.5592 | 0.0011 |
| HAR-GVF | 22 | XLK | 2087 | 0.3043 | 0.6083 | 0.4533 | -0.0228 | 0.9018 | 0.5544 | 0.0011 |

## Pooled by group
| model | group | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-GVF | emerging_markets | 10465 | 0.2919 | 0.7961 | 0.6475 | -0.4050 | 0.9285 | 0.5606 | 0.0006 |
| HAR-GVF | high_yield_credit | 10465 | 0.5131 | 0.9469 | 0.7725 | -0.5521 | 0.9568 | 0.6400 | 0.0002 |
| HAR-GVF | oil_and_energy | 10465 | 0.2553 | 0.5664 | 0.4150 | -0.0760 | 0.9001 | 0.5467 | 0.0011 |
| HAR-GVF | precious_metals | 10465 | 0.2439 | 0.6803 | 0.5291 | -0.2025 | 0.8663 | 0.4633 | 0.0003 |
| HAR-GVF | us_cyclicals_sector | 10465 | 0.3133 | 0.6678 | 0.5200 | -0.2120 | 0.9246 | 0.5633 | 0.0008 |
| HAR-GVF | us_large_cap_equity | 20930 | 0.3178 | 0.6812 | 0.5256 | -0.1193 | 0.9017 | 0.5431 | 0.0006 |
| HAR-GVF | us_rates_and_ig_credit | 10465 | 0.2177 | 0.5833 | 0.4371 | -0.0814 | 0.8850 | 0.5008 | 0.0002 |
| HAR-GVF | us_small_cap_equity | 10465 | 0.2564 | 0.5893 | 0.4418 | -0.0713 | 0.8916 | 0.5097 | 0.0007 |
| HAR-GVF | us_technology_sector | 10465 | 0.2794 | 0.6308 | 0.4802 | -0.0634 | 0.8976 | 0.5287 | 0.0008 |

---

## Build provenance (human-only fields, MODEL_PLAN §5)

- **File / Class:** `candidate_models/har_globalfactor.py` · `HARGlobalFactor` · `name="HAR-GVF"`
- **Pattern:** P1 — `_AttachMixin` + `_LinearLogHAR` (plain per-(ticker,horizon) log-OLS, no free hyperparameters).
- **Features used (`needs`):** `HAR_FEATURES` = [`log_rv_d`, `log_rv_w`, `log_rv_m`] + derived [`log_gvf`].
- **Derived column:** `log_gvf = log(max(gvf_t, 1e-12))`, where `gvf_t = mean over the clean-core basket of total_rv on date t`.
- **Factor-basket definition:** the cross-sectional MEAN of `total_rv` across the `CLEAN_CORE` tickers (read from `rv_eval.config.CLEAN_CORE`: SPY, QQQ, IWM, XLK, XLF, XLE, TLT, GLD, HYG, EEM), computed per DATE and joined by date alone (broadcast identical across tickers). The basket is the clean-core cross-section **even when scoring hard_cases** — hard names are never added to the basket (they would contaminate / leak the factor). SPX/VIX RV is not in inputs.parquet, so this per-date mean is the systematic factor (no fitted loadings → leak-free, same as a ticker’s own total_rv).
- **Leakage controls:** factor and HAR roll-means are built ONCE on the full series (`inputs.parquet`) and joined by (ticker,date); never recomputed on the one-month predict slice. Synthetic-X fallback in `_gvf_panel` rebuilds from X for the smoke test.
- **Coverage:** full — all 10 clean_core tickers × {1,5,10,22,42}; no missing (ticker,horizon) cells. No coverage warnings.
- **OOS rows (this universe / clean_core):** 105,450 · span 2018-01-02 → 2026-05-22.
- **Seed:** none (deterministic OLS via numpy.linalg.lstsq; no stochastic component).
- **Wall-clock:** clean_core walk-forward 8.3 s.
- **Device:** macOS-15.3.1-arm64 (Apple Silicon, 10 cores), CPU only.
- **Library versions:** python 3.12.13 · polars 1.41.1 · numpy 2.4.6 · scipy 1.17.1.
