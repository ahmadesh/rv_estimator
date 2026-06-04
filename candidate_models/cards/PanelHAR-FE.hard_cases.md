# PanelHAR-FE — Self Stats
_universe=`hard_cases` · primary horizon h=22 · predictions=`execution/data/predictions/PanelHAR-FE.parquet` · generated 2026-06-03T21:16:12Z_

_Self-only metrics — no leaderboard rank, no DM test, no MCS, no §9 status._
_Cross-model comparison is produced by the final `rv_eval.evaluator` pass._

## Tier-1 pooled by horizon (§3)
| model | horizon | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| PanelHAR-FE | 1 | 7949 | 0.3182 | 0.7315 | 0.5749 | -0.2204 | 0.8870 | 0.5162 | 0.0004 |
| PanelHAR-FE | 5 | 7929 | 0.2478 | 0.6065 | 0.4575 | -0.1281 | 0.8878 | 0.5346 | 0.0019 |
| PanelHAR-FE | 10 | 7904 | 0.2464 | 0.5939 | 0.4436 | -0.1036 | 0.8860 | 0.5415 | 0.0039 |
| PanelHAR-FE | 22 | 7844 | 0.2755 | 0.5979 | 0.4468 | -0.0760 | 0.8913 | 0.5368 | 0.0082 |
| PanelHAR-FE | 42 | 7744 | 0.3069 | 0.6182 | 0.4575 | -0.0550 | 0.8986 | 0.5230 | 0.0144 |

## §5 IV-incremental skill (per horizon)
| model | horizon | n | slope | t_slope | sign_acc | qlike_model | qlike_iv | qlike_gain_vs_iv |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| PanelHAR-FE | 1 | 7949 | 0.5727 | 24.5172 | 0.7376 | 0.3182 | 0.3617 | 0.0435 |
| PanelHAR-FE | 5 | 7929 | 0.7457 | 24.8872 | 0.7113 | 0.2478 | 0.2635 | 0.0157 |
| PanelHAR-FE | 10 | 7904 | 0.8688 | 28.5355 | 0.6761 | 0.2464 | 0.2550 | 0.0086 |
| PanelHAR-FE | 22 | 7844 | 0.8684 | 37.5243 | 0.6225 | 0.2755 | 0.2736 | -0.0018 |
| PanelHAR-FE | 42 | 7744 | 0.9889 | 57.3046 | 0.6033 | 0.3069 | 0.3143 | 0.0074 |

## §6 Conditional bias by IV-percentile bucket (h=22)
| model | horizon | iv_pctile_bucket | n | qlike | log_bias |
| --- | --- | --- | --- | --- | --- |
| PanelHAR-FE | 22 | 0 | 1978 | 0.2934 | -0.0790 |
| PanelHAR-FE | 22 | 1 | 1278 | 0.2342 | -0.0756 |
| PanelHAR-FE | 22 | 2 | 1369 | 0.2212 | -0.0507 |
| PanelHAR-FE | 22 | 3 | 1471 | 0.2560 | -0.1149 |
| PanelHAR-FE | 22 | 4 | 1748 | 0.3443 | -0.0598 |

## §6 Post-shock calibration (h=22)
| model | horizon | bias_all | qlike_all | bias_postshock | qlike_postshock | n_postshock | trap_flag |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PanelHAR-FE | 22 | -0.0760 | 0.2755 | -0.1354 | 0.2924 | 1469 | ✓ |

## Per-ticker Tier-1 at h=22
| model | horizon | ticker | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| PanelHAR-FE | 22 | IBIT | 352 | 0.1123 | 0.4867 | 0.3925 | -0.1331 | 0.9091 | 0.5682 | 0.0020 |
| PanelHAR-FE | 22 | KRE | 2059 | 0.3269 | 0.5692 | 0.4000 | -0.0572 | 0.9301 | 0.6066 | 0.0016 |
| PanelHAR-FE | 22 | MSOS | 1316 | 0.1804 | 0.5429 | 0.4282 | 0.0013 | 0.8739 | 0.5433 | 0.0059 |
| PanelHAR-FE | 22 | USO | 2059 | 0.2239 | 0.5475 | 0.4101 | -0.0387 | 0.9121 | 0.5644 | 0.0026 |
| PanelHAR-FE | 22 | UVXY | 2058 | 0.3643 | 0.7138 | 0.5516 | -0.1717 | 0.8397 | 0.4300 | 0.0229 |

## Pooled by group
| model | group | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| PanelHAR-FE | crypto | 1790 | 0.1757 | 0.5834 | 0.4585 | -0.1459 | 0.9056 | 0.5313 | 0.0014 |
| PanelHAR-FE | long_volatility_vix | 10320 | 0.3544 | 0.7372 | 0.5767 | -0.2021 | 0.8370 | 0.4319 | 0.0157 |
| PanelHAR-FE | oil_and_energy | 10325 | 0.2586 | 0.6219 | 0.4701 | -0.0998 | 0.8913 | 0.5284 | 0.0021 |
| PanelHAR-FE | us_cannabis | 6610 | 0.2317 | 0.5740 | 0.4338 | -0.0326 | 0.8982 | 0.5637 | 0.0040 |
| PanelHAR-FE | us_cyclicals_sector | 10325 | 0.2717 | 0.5681 | 0.4124 | -0.0983 | 0.9340 | 0.6095 | 0.0012 |

---

## Build provenance (human-only fields — MODEL_PLAN §5)

**Model.** `candidate_models/panel_har.py:PanelHARFE`, `name="PanelHAR-FE"` (catalog model 22,
Track C, Pattern P3). Pooled log-OLS of `log(target_var)` per horizon across all tickers in the
TRAIN slice, with a ticker fixed-effect intercept (no global intercept) and a single shared slope
vector. Built on frozen `_base_v2._PooledLinearHAR` / `fit_pooled` / `pooled_mu`. Lognormal
predictive distribution (`m = exp(mu + s^2/2)`, pooled per-horizon residual log-sd `s`).

**Features used (pooled slopes).** `HAR_RS_FEATURES + IV_FEATURES` =
`[log_rv_d, log_rv_w, log_rv_m, rs_minus_5d, rs_plus_5d, jump_5d,` `log_iv, iv_slope, skew_25d,
vix, vix3m, vix_slope, vvix]` (13 slopes). No derived/`_AttachMixin` columns — all from
`build_features(inputs.parquet)`, point-in-time, no rolling recompute on the predict slice.

**Fixed effects / pooling discipline.** FE intercepts + shared slopes estimated TRAIN-only at each
monthly refit; per-horizon pooling. Note: the hard_cases universe pools only its 5 tickers
(UVXY, MSOS, IBIT, USO, KRE) within each fold — the FE intercepts and slopes are NOT shared with
clean_core (the walk-forward fits per universe). Unseen-ticker fallback (group-mean then
global-mean intercept) verified in tests.

**Frozen hyperparameters + HP-selection note.** None — plain pooled OLS, no penalty/shrinkage/tuned
window. Nothing selected on any validation block; nothing to leak. (`min_pooled_obs=200`,
`s`-floor `1e-3` are structural base constants.)

**Coverage.** Full: all 5 hard_cases tickers x all 5 horizons, 39,745 OOS rows. All `rv_hat`
finite and > 0; quantiles monotone. No tickers/horizons dropped.

**Warnings.** Hard-cases stress: very high RV/IV tickers (UVXY) — expect wider QLIKE and possible
under-prediction in tails; coverage/bias panels above are the authoritative read. No convergence
issues (closed-form lstsq).

**Reproducibility.** Deterministic (lstsq, no RNG) — seed N/A. numpy 2.4.6, polars 1.41.1,
scipy 1.17.1, python 3.12.13. Device: CPU (Darwin 24.3.0). Wall-clock: hard_cases 3.3s
(clean_core 9.1s in the sibling run), walk-forward monthly refit 2018-01..2026-05.
