# HAR-SJ — Self Stats
_universe=`hard_cases` · primary horizon h=22 · predictions=`execution/data/predictions/HAR-SJ.parquet` · generated 2026-06-03T18:03:40Z_

_Self-only metrics — no leaderboard rank, no DM test, no MCS, no §9 status._
_Cross-model comparison is produced by the final `rv_eval.evaluator` pass._

## Tier-1 pooled by horizon (§3)
| model | horizon | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-SJ | 1 | 8196 | 0.3457 | 0.7930 | 0.6192 | -0.2800 | 0.8946 | 0.5182 | 0.0005 |
| HAR-SJ | 5 | 8153 | 0.2797 | 0.6818 | 0.5133 | -0.1828 | 0.8859 | 0.5153 | 0.0025 |
| HAR-SJ | 10 | 8108 | 0.2874 | 0.7010 | 0.5114 | -0.1714 | 0.8733 | 0.5073 | 0.0188 |
| HAR-SJ | 22 | 8048 | 0.3046 | 0.6838 | 0.5107 | -0.1387 | 0.8647 | 0.4894 | 0.0144 |
| HAR-SJ | 42 | 7905 | 0.3300 | 0.7024 | 0.5167 | -0.1117 | 0.8445 | 0.4700 | 0.0854 |

## §5 IV-incremental skill (per horizon)
| model | horizon | n | slope | t_slope | sign_acc | qlike_model | qlike_iv | qlike_gain_vs_iv |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-SJ | 1 | 7906 | 0.1437 | 14.7051 | 0.6924 | 0.3371 | 0.3595 | 0.0224 |
| HAR-SJ | 5 | 7863 | 0.0093 | 1.8795 | 0.6494 | 0.2759 | 0.2624 | -0.0136 |
| HAR-SJ | 10 | 7838 | -0.0006 | -2.0656 | 0.6054 | 0.2853 | 0.2542 | -0.0311 |
| HAR-SJ | 22 | 7778 | -0.0020 | -1.4711 | 0.5642 | 0.3059 | 0.2732 | -0.0328 |
| HAR-SJ | 42 | 7657 | -0.0004 | -2.1457 | 0.5621 | 0.3361 | 0.3134 | -0.0227 |

## §6 Conditional bias by IV-percentile bucket (h=22)
| model | horizon | iv_pctile_bucket | n | qlike | log_bias |
| --- | --- | --- | --- | --- | --- |
| HAR-SJ | 22 | 0 | 2078 | 0.3138 | -0.2452 |
| HAR-SJ | 22 | 1 | 1264 | 0.2483 | -0.1452 |
| HAR-SJ | 22 | 2 | 1355 | 0.2513 | -0.0809 |
| HAR-SJ | 22 | 3 | 1460 | 0.2685 | -0.1038 |
| HAR-SJ | 22 | 4 | 1727 | 0.4148 | -0.0569 |

## §6 Post-shock calibration (h=22)
| model | horizon | bias_all | qlike_all | bias_postshock | qlike_postshock | n_postshock | trap_flag |
| --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-SJ | 22 | -0.1387 | 0.3046 | -0.2262 | 0.3530 | 1487 |  |

## Per-ticker Tier-1 at h=22
| model | horizon | ticker | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-SJ | 22 | IBIT | 517 | 0.1916 | 0.7001 | 0.5660 | -0.4013 | 0.7215 | 0.4313 | 0.0035 |
| HAR-SJ | 22 | KRE | 2087 | 0.3436 | 0.6131 | 0.4476 | -0.0977 | 0.9286 | 0.5688 | 0.0018 |
| HAR-SJ | 22 | MSOS | 1270 | 0.2742 | 0.6770 | 0.5060 | 0.0155 | 0.8031 | 0.4717 | 0.0089 |
| HAR-SJ | 22 | USO | 2087 | 0.2841 | 0.6702 | 0.4610 | -0.0303 | 0.8323 | 0.4480 | 0.0249 |
| HAR-SJ | 22 | UVXY | 2087 | 0.3326 | 0.7601 | 0.6129 | -0.3171 | 0.9061 | 0.4768 | 0.0227 |

## Pooled by group
| model | group | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-SJ | crypto | 2633 | 0.2936 | 0.8499 | 0.6848 | -0.5079 | 0.8431 | 0.4820 | 0.0024 |
| HAR-SJ | long_volatility_vix | 10465 | 0.3212 | 0.7740 | 0.6237 | -0.3165 | 0.8944 | 0.4867 | 0.0156 |
| HAR-SJ | oil_and_energy | 10465 | 0.3179 | 0.7341 | 0.5161 | -0.1016 | 0.8339 | 0.4531 | 0.0711 |
| HAR-SJ | us_cannabis | 6382 | 0.3095 | 0.6812 | 0.5025 | -0.0444 | 0.8406 | 0.4966 | 0.0065 |
| HAR-SJ | us_cyclicals_sector | 10465 | 0.2931 | 0.6039 | 0.4456 | -0.1126 | 0.9172 | 0.5678 | 0.0013 |

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

**Coverage.** All 5 hard-case tickers (UVXY, MSOS, IBIT, USO, KRE) x 5 horizons covered; no tickers/horizons dropped. All rv_hat finite and > 0; quantiles monotone (enforced by lognormal construction). No convergence issues (closed-form OLS).

**Environment.** python 3.12.13 · numpy 2.4.6 · polars 1.41.1 · scipy 1.17.1. Device: CPU (Apple arm64, macOS 15.3.1).

**Wall-clock.** clean_core walk-forward ~9.6s (105,450 OOS preds); hard_cases ~4.9s (40,810 OOS preds). Combined parquet: 146,260 rows, span 2018-01-02 to 2026-05-22.
