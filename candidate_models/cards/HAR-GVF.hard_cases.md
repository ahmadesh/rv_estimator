# HAR-GVF — Self Stats
_universe=`hard_cases` · primary horizon h=22 · predictions=`execution/data/predictions/HAR-GVF.parquet` · generated 2026-06-03T21:25:15Z_

_Self-only metrics — no leaderboard rank, no DM test, no MCS, no §9 status._
_Cross-model comparison is produced by the final `rv_eval.evaluator` pass._

## Tier-1 pooled by horizon (§3)
| model | horizon | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-GVF | 1 | 8196 | 0.3423 | 0.7734 | 0.6066 | -0.2598 | 0.8974 | 0.5210 | 0.0004 |
| HAR-GVF | 5 | 8153 | 0.2738 | 0.6620 | 0.5039 | -0.1747 | 0.8892 | 0.5175 | 0.0020 |
| HAR-GVF | 10 | 8108 | 0.2783 | 0.6615 | 0.5016 | -0.1603 | 0.8770 | 0.5123 | 0.0040 |
| HAR-GVF | 22 | 8048 | 0.2985 | 0.6614 | 0.5071 | -0.1343 | 0.8672 | 0.4924 | 0.0085 |
| HAR-GVF | 42 | 7905 | 0.3211 | 0.6653 | 0.5074 | -0.1053 | 0.8493 | 0.4756 | 0.0148 |

## §5 IV-incremental skill (per horizon)
| model | horizon | n | slope | t_slope | sign_acc | qlike_model | qlike_iv | qlike_gain_vs_iv |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-GVF | 1 | 7906 | 0.9202 | 24.3171 | 0.6986 | 0.3337 | 0.3595 | 0.0258 |
| HAR-GVF | 5 | 7863 | 0.7007 | 21.3837 | 0.6522 | 0.2706 | 0.2624 | -0.0082 |
| HAR-GVF | 10 | 7838 | 0.7208 | 26.2029 | 0.6138 | 0.2759 | 0.2542 | -0.0217 |
| HAR-GVF | 22 | 7778 | 0.7725 | 38.2072 | 0.5665 | 0.2982 | 0.2732 | -0.0250 |
| HAR-GVF | 42 | 7657 | 0.8890 | 59.6919 | 0.5600 | 0.3259 | 0.3134 | -0.0124 |

## §6 Conditional bias by IV-percentile bucket (h=22)
| model | horizon | iv_pctile_bucket | n | qlike | log_bias |
| --- | --- | --- | --- | --- | --- |
| HAR-GVF | 22 | 0 | 2078 | 0.3153 | -0.2452 |
| HAR-GVF | 22 | 1 | 1264 | 0.2468 | -0.1482 |
| HAR-GVF | 22 | 2 | 1355 | 0.2467 | -0.0850 |
| HAR-GVF | 22 | 3 | 1460 | 0.2644 | -0.1088 |
| HAR-GVF | 22 | 4 | 1727 | 0.3865 | -0.0140 |

## §6 Post-shock calibration (h=22)
| model | horizon | bias_all | qlike_all | bias_postshock | qlike_postshock | n_postshock | trap_flag |
| --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-GVF | 22 | -0.1343 | 0.2985 | -0.1731 | 0.3254 | 1487 |  |

## Per-ticker Tier-1 at h=22
| model | horizon | ticker | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-GVF | 22 | IBIT | 517 | 0.2233 | 0.7620 | 0.6376 | -0.5157 | 0.7137 | 0.4410 | 0.0039 |
| HAR-GVF | 22 | KRE | 2087 | 0.3405 | 0.6122 | 0.4484 | -0.0995 | 0.9300 | 0.5697 | 0.0017 |
| HAR-GVF | 22 | MSOS | 1270 | 0.2596 | 0.6322 | 0.4837 | 0.0473 | 0.8126 | 0.4898 | 0.0069 |
| HAR-GVF | 22 | USO | 2087 | 0.2594 | 0.5923 | 0.4455 | -0.0126 | 0.8318 | 0.4403 | 0.0028 |
| HAR-GVF | 22 | UVXY | 2087 | 0.3378 | 0.7579 | 0.6092 | -0.3067 | 0.9109 | 0.4816 | 0.0229 |

## Pooled by group
| model | group | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-GVF | crypto | 2633 | 0.3056 | 0.8692 | 0.7082 | -0.5637 | 0.8431 | 0.4968 | 0.0027 |
| HAR-GVF | long_volatility_vix | 10465 | 0.3252 | 0.7696 | 0.6190 | -0.3040 | 0.8978 | 0.4872 | 0.0156 |
| HAR-GVF | oil_and_energy | 10465 | 0.2953 | 0.6560 | 0.4969 | -0.0808 | 0.8352 | 0.4521 | 0.0022 |
| HAR-GVF | us_cannabis | 6382 | 0.2954 | 0.6317 | 0.4755 | -0.0111 | 0.8518 | 0.5150 | 0.0047 |
| HAR-GVF | us_cyclicals_sector | 10465 | 0.2917 | 0.6029 | 0.4454 | -0.1132 | 0.9191 | 0.5677 | 0.0013 |

---

## Build provenance (human-only fields, MODEL_PLAN §5)

- **File / Class:** `candidate_models/har_globalfactor.py` · `HARGlobalFactor` · `name="HAR-GVF"`
- **Pattern:** P1 — `_AttachMixin` + `_LinearLogHAR` (plain per-(ticker,horizon) log-OLS, no free hyperparameters).
- **Features used (`needs`):** `HAR_FEATURES` = [`log_rv_d`, `log_rv_w`, `log_rv_m`] + derived [`log_gvf`].
- **Derived column:** `log_gvf = log(max(gvf_t, 1e-12))`, where `gvf_t = mean over the clean-core basket of total_rv on date t`.
- **Factor-basket definition:** cross-sectional MEAN of `total_rv` across the `CLEAN_CORE` tickers (SPY, QQQ, IWM, XLK, XLF, XLE, TLT, GLD, HYG, EEM), per DATE, joined by date alone. **Critically, for the hard_cases universe the basket is STILL the clean-core cross-section** — the five hard names (UVXY, MSOS, IBIT, USO, KRE) are NOT in the factor basket (adding them would leak/contaminate it). The factor table is built once on the full inputs.parquet series and joined by (ticker,date).
- **Leakage controls:** factor and HAR roll-means built ONCE on the full series and joined; never recomputed on the predict slice.
- **Coverage:** full — all 5 hard_cases tickers × {1,5,10,22,42}; no missing (ticker,horizon) cells. No coverage warnings.
- **OOS rows (this universe / hard_cases):** 40,810 · span 2018-01-02 → 2026-05-22.
- **Seed:** none (deterministic OLS; no stochastic component).
- **Wall-clock:** hard_cases walk-forward 4.1 s.
- **Device:** macOS-15.3.1-arm64 (Apple Silicon, 10 cores), CPU only.
- **Library versions:** python 3.12.13 · polars 1.41.1 · numpy 2.4.6 · scipy 1.17.1.
