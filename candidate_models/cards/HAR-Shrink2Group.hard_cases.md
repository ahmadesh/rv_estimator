# HAR-Shrink2Group — Self Stats
_universe=`hard_cases` · primary horizon h=22 · predictions=`execution/data/predictions/HAR-Shrink2Group.parquet` · generated 2026-06-03T21:21:02Z_

_Self-only metrics — no leaderboard rank, no DM test, no MCS, no §9 status._
_Cross-model comparison is produced by the final `rv_eval.evaluator` pass._

## Tier-1 pooled by horizon (§3)
| model | horizon | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-Shrink2Group | 1 | 7949 | 0.3073 | 0.7364 | 0.5778 | -0.2324 | 0.8913 | 0.5105 | 0.0005 |
| HAR-Shrink2Group | 5 | 7929 | 0.2408 | 0.6142 | 0.4629 | -0.1396 | 0.8881 | 0.5211 | 0.0021 |
| HAR-Shrink2Group | 10 | 7904 | 0.2454 | 0.6072 | 0.4524 | -0.1163 | 0.8822 | 0.5288 | 0.0041 |
| HAR-Shrink2Group | 22 | 7844 | 0.2751 | 0.6066 | 0.4534 | -0.0782 | 0.8788 | 0.5054 | 0.0083 |
| HAR-Shrink2Group | 42 | 7744 | 0.3121 | 0.6284 | 0.4647 | -0.0489 | 0.8614 | 0.4956 | 0.0151 |

## §5 IV-incremental skill (per horizon)
| model | horizon | n | slope | t_slope | sign_acc | qlike_model | qlike_iv | qlike_gain_vs_iv |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-Shrink2Group | 1 | 7949 | 0.1250 | 15.6884 | 0.7415 | 0.3073 | 0.3617 | 0.0544 |
| HAR-Shrink2Group | 5 | 7929 | 0.1832 | 17.1448 | 0.7141 | 0.2408 | 0.2635 | 0.0227 |
| HAR-Shrink2Group | 10 | 7904 | 0.2498 | 14.4670 | 0.6733 | 0.2454 | 0.2550 | 0.0097 |
| HAR-Shrink2Group | 22 | 7844 | 0.7496 | 30.1886 | 0.6215 | 0.2751 | 0.2736 | -0.0014 |
| HAR-Shrink2Group | 42 | 7744 | 0.4949 | 34.8735 | 0.6089 | 0.3121 | 0.3143 | 0.0022 |

## §6 Conditional bias by IV-percentile bucket (h=22)
| model | horizon | iv_pctile_bucket | n | qlike | log_bias |
| --- | --- | --- | --- | --- | --- |
| HAR-Shrink2Group | 22 | 0 | 1978 | 0.2888 | -0.0853 |
| HAR-Shrink2Group | 22 | 1 | 1278 | 0.2346 | -0.0766 |
| HAR-Shrink2Group | 22 | 2 | 1369 | 0.2270 | -0.0453 |
| HAR-Shrink2Group | 22 | 3 | 1471 | 0.2487 | -0.1139 |
| HAR-Shrink2Group | 22 | 4 | 1748 | 0.3490 | -0.0672 |

## §6 Post-shock calibration (h=22)
| model | horizon | bias_all | qlike_all | bias_postshock | qlike_postshock | n_postshock | trap_flag |
| --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-Shrink2Group | 22 | -0.0782 | 0.2751 | -0.1259 | 0.3028 | 1469 | ✓ |

## Per-ticker Tier-1 at h=22
| model | horizon | ticker | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-Shrink2Group | 22 | IBIT | 352 | 0.1236 | 0.4928 | 0.4005 | -0.0787 | 0.7614 | 0.3949 | 0.0023 |
| HAR-Shrink2Group | 22 | KRE | 2059 | 0.3350 | 0.5750 | 0.4037 | -0.0569 | 0.9325 | 0.5979 | 0.0016 |
| HAR-Shrink2Group | 22 | MSOS | 1316 | 0.1833 | 0.5429 | 0.4272 | 0.0553 | 0.8252 | 0.4590 | 0.0060 |
| HAR-Shrink2Group | 22 | USO | 2059 | 0.2331 | 0.5546 | 0.4013 | -0.0031 | 0.8456 | 0.4633 | 0.0031 |
| HAR-Shrink2Group | 22 | UVXY | 2058 | 0.3417 | 0.7308 | 0.5809 | -0.2600 | 0.9125 | 0.5034 | 0.0228 |

## Pooled by group
| model | group | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-Shrink2Group | crypto | 1790 | 0.1828 | 0.5974 | 0.4699 | -0.1411 | 0.8123 | 0.4520 | 0.0015 |
| HAR-Shrink2Group | long_volatility_vix | 10320 | 0.3265 | 0.7538 | 0.6010 | -0.2810 | 0.8968 | 0.4946 | 0.0158 |
| HAR-Shrink2Group | oil_and_energy | 10325 | 0.2628 | 0.6277 | 0.4634 | -0.0769 | 0.8477 | 0.4642 | 0.0028 |
| HAR-Shrink2Group | us_cannabis | 6610 | 0.2397 | 0.5833 | 0.4427 | -0.0049 | 0.8536 | 0.5083 | 0.0042 |
| HAR-Shrink2Group | us_cyclicals_sector | 10325 | 0.2781 | 0.5689 | 0.4107 | -0.0858 | 0.9260 | 0.5914 | 0.0012 |

---

## Build provenance (human-only fields — MODEL_PLAN §5)

**Model.** `candidate_models/har_shrink2group.py:HARShrink2Group`, `name="HAR-Shrink2Group"`
(catalog model 23, Track C, Pattern P3). Per-(ticker, horizon) OLS β shrunk toward the
panel-pooled β: `beta_shrunk = (1-w)·beta_ticker + w·beta_pooled` (catalog form; `w` = weight on
pooled, in [0,1]). Pooled β = `[fe_intercept, shared_slopes]` from frozen `_base_v2.fit_pooled`;
per-ticker β = own `[intercept, slopes]` OLS. Lognormal predictive via `_emit_lognormal`. See the
sibling `HAR-Shrink2Group.md` (clean_core) for the full model/feature/HP description.

**Features used.** `HAR_RS_FEATURES + IV_FEATURES` (13 slopes + intercept), all point-in-time from
`features.build_features`. No `_AttachMixin`/derived rolling columns; no targets-only fields.

**Frozen hyperparameters.** Shrinkage intensity `w_h` per horizon, selected by a time-ordered
expanding inner CV (4 folds) on the TRAIN slice only (grid `{0.0..1.0}`, ties → more pooling),
re-selected at every monthly refit; never tuned on OOS or other models. Structural constants:
`min_ticker_obs=100` (thin (ticker,h) → pooled β outright), `min_pooled_obs=200`, `s`-floor 1e-3.

**Coverage.** Full: all 5 hard_cases tickers (UVXY, MSOS, IBIT, USO, KRE) × all 5 horizons
{1,5,10,22,42}, 7,949 rows each → 39,745 hard_cases OOS rows (143,745 total across both
universes). All `rv_hat` finite and > 0; quantiles monotone. No tickers/horizons dropped; 0
thin-ticker fallbacks on the real panel.

**Reproducibility.** Deterministic (lstsq + fixed-fraction inner CV, no RNG); seed N/A. Libraries:
numpy 2.4.6, polars 1.41.1, scipy 1.17.1, python 3.12.13. Device: CPU (Darwin 24.3.0).
Wall-clock: hard_cases 12.9s (clean_core 39.3s). Smoke test: 3 passed.
