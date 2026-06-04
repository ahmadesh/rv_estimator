# EnsembleTopK-v2 — Self Stats
_universe=`hard_cases` · primary horizon h=22 · predictions=`execution/data/predictions/EnsembleTopK-v2.parquet` · generated 2026-06-04T02:24:58Z_

_Self-only metrics — no leaderboard rank, no DM test, no MCS, no §9 status._
_Cross-model comparison is produced by the final `rv_eval.evaluator` pass._

## Tier-1 pooled by horizon (§3)
| model | horizon | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EnsembleTopK-v2 | 1 | 7659 | 0.2979 | 0.7086 | 0.5532 | -0.1966 | 0.8886 | 0.5080 | 0.0005 |
| EnsembleTopK-v2 | 5 | 7667 | 0.2394 | 0.6086 | 0.4571 | -0.1190 | 0.8795 | 0.5061 | 0.0021 |
| EnsembleTopK-v2 | 10 | 7738 | 0.2443 | 0.6131 | 0.4573 | -0.1077 | 0.8781 | 0.5075 | 0.0038 |
| EnsembleTopK-v2 | 22 | 7644 | 0.2930 | 0.7545 | 0.4672 | -0.0701 | 0.8654 | 0.5122 | 407.7215 |
| EnsembleTopK-v2 | 42 | 7593 | 0.3408 | 0.7808 | 0.4826 | -0.0410 | 0.8578 | 0.5001 | 489.3601 |

## §5 IV-incremental skill (per horizon)
| model | horizon | n | slope | t_slope | sign_acc | qlike_model | qlike_iv | qlike_gain_vs_iv |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EnsembleTopK-v2 | 1 | 7658 | 0.1213 | 15.8289 | 0.7643 | 0.2979 | 0.3581 | 0.0602 |
| EnsembleTopK-v2 | 5 | 7662 | 0.1091 | 17.2538 | 0.7236 | 0.2394 | 0.2616 | 0.0221 |
| EnsembleTopK-v2 | 10 | 7641 | 0.1564 | 13.2027 | 0.6752 | 0.2442 | 0.2512 | 0.0070 |
| EnsembleTopK-v2 | 22 | 7524 | -0.0000 | -0.0260 | 0.6415 | 0.2953 | 0.2722 | -0.0230 |
| EnsembleTopK-v2 | 42 | 7468 | -0.0000 | -0.0282 | 0.6292 | 0.3435 | 0.3182 | -0.0252 |

## §6 Conditional bias by IV-percentile bucket (h=22)
| model | horizon | iv_pctile_bucket | n | qlike | log_bias |
| --- | --- | --- | --- | --- | --- |
| EnsembleTopK-v2 | 22 | 0 | 1926 | 0.3168 | -0.1140 |
| EnsembleTopK-v2 | 22 | 1 | 1214 | 0.2586 | -0.0524 |
| EnsembleTopK-v2 | 22 | 2 | 1322 | 0.2316 | -0.0059 |
| EnsembleTopK-v2 | 22 | 3 | 1434 | 0.2351 | -0.0636 |
| EnsembleTopK-v2 | 22 | 4 | 1685 | 0.3918 | -0.0673 |

## §6 Post-shock calibration (h=22)
| model | horizon | bias_all | qlike_all | bias_postshock | qlike_postshock | n_postshock | trap_flag |
| --- | --- | --- | --- | --- | --- | --- | --- |
| EnsembleTopK-v2 | 22 | -0.0701 | 0.2930 | -0.1211 | 0.3776 | 1400 | ✓ |

## Per-ticker Tier-1 at h=22
| model | horizon | ticker | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EnsembleTopK-v2 | 22 | IBIT | 287 | 0.1480 | 0.5872 | 0.4796 | -0.2468 | 0.6237 | 0.3728 | 0.0024 |
| EnsembleTopK-v2 | 22 | KRE | 2033 | 0.3723 | 0.5840 | 0.3993 | -0.0288 | 0.9449 | 0.6119 | 0.0017 |
| EnsembleTopK-v2 | 22 | MSOS | 1258 | 0.2356 | 0.6097 | 0.4868 | 0.1601 | 0.7194 | 0.3824 | 0.0068 |
| EnsembleTopK-v2 | 22 | USO | 2033 | 0.2785 | 1.0210 | 0.4373 | -0.0308 | 0.8431 | 0.4939 | 1532.9916 |
| EnsembleTopK-v2 | 22 | UVXY | 2033 | 0.2844 | 0.6914 | 0.5510 | -0.2682 | 0.9326 | 0.5307 | 0.0190 |

## Pooled by group
| model | group | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EnsembleTopK-v2 | crypto | 1486 | 0.1909 | 0.6769 | 0.5315 | -0.2951 | 0.8055 | 0.4246 | 0.0023 |
| EnsembleTopK-v2 | long_volatility_vix | 10181 | 0.2866 | 0.7187 | 0.5728 | -0.2692 | 0.8995 | 0.5001 | 0.0139 |
| EnsembleTopK-v2 | oil_and_energy | 10181 | 0.2884 | 0.8302 | 0.4773 | -0.0637 | 0.8407 | 0.4670 | 671.0733 |
| EnsembleTopK-v2 | us_cannabis | 6272 | 0.2648 | 0.6064 | 0.4631 | 0.0478 | 0.8219 | 0.4770 | 0.0047 |
| EnsembleTopK-v2 | us_cyclicals_sector | 10181 | 0.2983 | 0.5703 | 0.4058 | -0.0560 | 0.9236 | 0.5834 | 0.0012 |

---

## MODEL_PLAN §5 — build provenance (human fields)

**Model.** `candidate_models/ensemble_top_v2.py:EnsembleTopKV2` · `name="EnsembleTopK-v2"` ·
catalog ITER2_MODEL_CATALOG.md §3 #21 · pattern **P3** (post-hoc combiner, reads component
prediction parquets; `fit` learns only combination weights, no statistical state of its own).

**Component set actually used (eligible pool).** Catalog §21 = "iter-1 winners + best new
Track-A/B/D models". Eligible pool (15 models):
- iter-1 winners: `HAR-RS-IV-Q`, `HARQ`, `HAR-RS`, `HAR-CJ`.
- Track A: `LHAR`, `HAR-SJ`, `HAR-IVTS`, `HAR-Range`, `HAR-Act`, `HAR-MAX`.
- Track B: `HAR-ENet`, `HAR-Ridge`, `HAR-CSR`.
- Track D: `HARX-HS`, `HAR-GARCH`, `HAR-QR`, `VRP-Spread`.
Excluded by design: iter-1 `EnsembleTopK` and this model itself; baselines `RW`/`EWMA`/`HAR`/`HAR-X`;
blow-up models `RealizedGARCH`/`GuyonLekeufackPDV`; iter-1 non-winners `LSTMRV`/`XGBHARRSIV`;
Track-C (`PanelHAR-FE`,`HAR-Shrink2Group`,`HAR-GVF`) and Track-E (`Threshold-HAR`,`STAR-HAR`,`MS-HAR`),
which are outside the §21 "A/B/D" remit.

**How top-K is chosen (`TOP_K=5`).** Per *horizon*, at every monthly refit, rank the eligible pool
by **trailing discounted-MSE** on the purged/embargoed `y_train` and keep the best 5. Membership is
time-varying and horizon-specific.

**Regime-conditional weighting scheme + lookback.** Per (horizon, `iv_pctile_bucket`) cell, the
top-K are combined with **inverse-discounted-MSE softmax** weights
`w_c ∝ exp(-log(dMSE_c)/T)`, `T=1.0`, where the error is the **squared log-error**
`(log rv_hat − log target_var)²`, **exponentially time-decayed** with `HALF_LIFE_DAYS=252`.
**Lookback = expanding** (all history before the test block, decay-weighted). Cells with
`< MIN_CELL_OBS=200` rows or `< 2` components fall back to the regime-pooled horizon weights.
Combined `sigma` = sqrt(weighted within-variance + weighted between-model dispersion); quantiles
via `_lognormal_quantiles` (monotone).

**Leakage controls.** Weights are learned only in `fit` from purged+embargoed `y_train`; the decay
discounts but never reaches past the test block; `predict` only looks up frozen (horizon,bucket)
weights and never sees a realized target; `iv_pctile_bucket` is a trailing point-in-time observable
(1 distinct value per ticker,date); keys with `< MIN_COMPONENTS=2` top-K forecasts are dropped,
never imputed. See `candidate_models/tests/test_ensemble_top_v2.py` for the leakage / monotonicity /
regime-weight unit tests.

**Reproducibility.** Deterministic (no RNG, no seed needed; closed-form weighted average).
- Library versions: python 3.12.13 · polars 1.41.1 · numpy 2.4.6 · scipy 1.17.1.
- Device: macOS-15.3.1 arm64 (Apple Silicon), CPU only.
- Wall-clock: clean_core 10.0 s + hard_cases 6.7 s walk-forward (both foreground).

**Coverage.** Full: all 5 hard-case tickers (UVXY, MSOS, IBIT, USO, KRE), all horizons
{1,5,10,22,42}; 38,676 hard_cases OOS rows (of 140,566 total). rv_hat finite & >0, quantiles
monotone, sigma finite ≥0 across every row. Component availability was 100% over the eligible pool,
so `MIN_COMPONENTS` never forced a drop. No tickers/horizons missing.
