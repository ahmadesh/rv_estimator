# EnsembleTopK-v2 — Self Stats
_universe=`clean_core` · primary horizon h=22 · predictions=`execution/data/predictions/EnsembleTopK-v2.parquet` · generated 2026-06-04T02:24:58Z_

_Self-only metrics — no leaderboard rank, no DM test, no MCS, no §9 status._
_Cross-model comparison is produced by the final `rv_eval.evaluator` pass._

## Tier-1 pooled by horizon (§3)
| model | horizon | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EnsembleTopK-v2 | 1 | 20360 | 0.2766 | 0.7118 | 0.5650 | -0.1855 | 0.8800 | 0.4812 | 0.0000 |
| EnsembleTopK-v2 | 5 | 20320 | 0.1764 | 0.5466 | 0.4225 | -0.0968 | 0.8839 | 0.4998 | 0.0002 |
| EnsembleTopK-v2 | 10 | 20490 | 0.1997 | 0.5481 | 0.4148 | -0.0866 | 0.8968 | 0.5199 | 0.0003 |
| EnsembleTopK-v2 | 22 | 20190 | 0.3458 | 0.6010 | 0.4393 | -0.0970 | 0.9128 | 0.5518 | 0.0008 |
| EnsembleTopK-v2 | 42 | 19780 | 0.4842 | 0.6803 | 0.4854 | -0.0929 | 0.9094 | 0.5564 | 0.0016 |

## §5 IV-incremental skill (per horizon)
| model | horizon | n | slope | t_slope | sign_acc | qlike_model | qlike_iv | qlike_gain_vs_iv |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EnsembleTopK-v2 | 1 | 20360 | 0.6091 | 50.2706 | 0.7311 | 0.2766 | 0.3291 | 0.0525 |
| EnsembleTopK-v2 | 5 | 20320 | 0.6541 | 47.5373 | 0.6824 | 0.1764 | 0.2086 | 0.0323 |
| EnsembleTopK-v2 | 10 | 20490 | 0.5477 | 25.7809 | 0.6257 | 0.1997 | 0.2164 | 0.0166 |
| EnsembleTopK-v2 | 22 | 20190 | -0.0065 | -0.2294 | 0.5426 | 0.3458 | 0.3373 | -0.0085 |
| EnsembleTopK-v2 | 42 | 19780 | -0.0190 | -0.9052 | 0.5210 | 0.4842 | 0.4781 | -0.0061 |

## §6 Conditional bias by IV-percentile bucket (h=22)
| model | horizon | iv_pctile_bucket | n | qlike | log_bias |
| --- | --- | --- | --- | --- | --- |
| EnsembleTopK-v2 | 22 | 0 | 5201 | 0.1786 | -0.1262 |
| EnsembleTopK-v2 | 22 | 1 | 3411 | 0.3448 | -0.1392 |
| EnsembleTopK-v2 | 22 | 2 | 3382 | 0.5238 | -0.1049 |
| EnsembleTopK-v2 | 22 | 3 | 3486 | 0.3748 | -0.0753 |
| EnsembleTopK-v2 | 22 | 4 | 4710 | 0.3819 | -0.0444 |

## §6 Post-shock calibration (h=22)
| model | horizon | bias_all | qlike_all | bias_postshock | qlike_postshock | n_postshock | trap_flag |
| --- | --- | --- | --- | --- | --- | --- | --- |
| EnsembleTopK-v2 | 22 | -0.0970 | 0.3458 | -0.0653 | 0.4099 | 3759 |  |

## Per-ticker Tier-1 at h=22
| model | horizon | ticker | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EnsembleTopK-v2 | 22 | EEM | 2019 | 0.2537 | 0.5701 | 0.4242 | -0.0675 | 0.9009 | 0.5745 | 0.0007 |
| EnsembleTopK-v2 | 22 | GLD | 2019 | 0.1500 | 0.4740 | 0.3465 | -0.0161 | 0.8737 | 0.5106 | 0.0003 |
| EnsembleTopK-v2 | 22 | HYG | 2019 | 0.8462 | 0.8336 | 0.6454 | -0.3516 | 0.9495 | 0.5844 | 0.0002 |
| EnsembleTopK-v2 | 22 | IWM | 2019 | 0.3076 | 0.5444 | 0.3866 | 0.0079 | 0.9133 | 0.5384 | 0.0009 |
| EnsembleTopK-v2 | 22 | QQQ | 2019 | 0.2913 | 0.5945 | 0.4414 | -0.0502 | 0.8990 | 0.5636 | 0.0008 |
| EnsembleTopK-v2 | 22 | SPY | 2019 | 0.4450 | 0.6745 | 0.5051 | -0.0878 | 0.9034 | 0.5463 | 0.0007 |
| EnsembleTopK-v2 | 22 | TLT | 2019 | 0.2135 | 0.4871 | 0.3384 | -0.0225 | 0.9049 | 0.4735 | 0.0003 |
| EnsembleTopK-v2 | 22 | XLE | 2019 | 0.2821 | 0.5311 | 0.3791 | -0.0874 | 0.9262 | 0.5523 | 0.0015 |
| EnsembleTopK-v2 | 22 | XLF | 2019 | 0.3700 | 0.6210 | 0.4773 | -0.1895 | 0.9460 | 0.5983 | 0.0010 |
| EnsembleTopK-v2 | 22 | XLK | 2019 | 0.2989 | 0.5985 | 0.4487 | -0.1052 | 0.9113 | 0.5760 | 0.0011 |

## Pooled by group
| model | group | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EnsembleTopK-v2 | emerging_markets | 10114 | 0.2895 | 0.6675 | 0.5060 | -0.1113 | 0.8851 | 0.5170 | 0.0005 |
| EnsembleTopK-v2 | high_yield_credit | 10114 | 0.5944 | 0.7927 | 0.6134 | -0.3048 | 0.9283 | 0.5607 | 0.0001 |
| EnsembleTopK-v2 | oil_and_energy | 10114 | 0.2439 | 0.5377 | 0.3920 | -0.0880 | 0.9017 | 0.5225 | 0.0011 |
| EnsembleTopK-v2 | precious_metals | 10114 | 0.2078 | 0.6021 | 0.4538 | -0.0848 | 0.8692 | 0.4868 | 0.0002 |
| EnsembleTopK-v2 | us_cyclicals_sector | 10114 | 0.2894 | 0.6054 | 0.4644 | -0.1699 | 0.9293 | 0.5571 | 0.0008 |
| EnsembleTopK-v2 | us_large_cap_equity | 20228 | 0.3036 | 0.6353 | 0.4825 | -0.0891 | 0.8879 | 0.5183 | 0.0006 |
| EnsembleTopK-v2 | us_rates_and_ig_credit | 10114 | 0.2070 | 0.5464 | 0.4035 | -0.0583 | 0.8805 | 0.4724 | 0.0002 |
| EnsembleTopK-v2 | us_small_cap_equity | 10114 | 0.2553 | 0.5466 | 0.3981 | -0.0198 | 0.8919 | 0.5240 | 0.0007 |
| EnsembleTopK-v2 | us_technology_sector | 10114 | 0.2587 | 0.5986 | 0.4564 | -0.1036 | 0.9028 | 0.5387 | 0.0008 |

---

## MODEL_PLAN §5 — build provenance (human fields)

**Model.** `candidate_models/ensemble_top_v2.py:EnsembleTopKV2` · `name="EnsembleTopK-v2"` ·
catalog ITER2_MODEL_CATALOG.md §3 #21 · pattern **P3** (post-hoc combiner, reads component
prediction parquets; `fit` learns only combination weights, no statistical state of its own).

**Component set actually used (eligible pool).** Catalog §21 = "iter-1 winners + best new
Track-A/B/D models". Eligible pool (15 models):
- iter-1 winners: `HAR-RS-IV-Q`, `HARQ`, `HAR-RS`, `HAR-CJ` (the four the iter-1 EnsembleTopK converged to).
- Track A (feature blocks): `LHAR`, `HAR-SJ`, `HAR-IVTS`, `HAR-Range`, `HAR-Act`, `HAR-MAX`.
- Track B (shrinkage/combine): `HAR-ENet`, `HAR-Ridge`, `HAR-CSR`.
- Track D (calibration/distribution): `HARX-HS`, `HAR-GARCH`, `HAR-QR`, `VRP-Spread`.
Excluded by design: iter-1 `EnsembleTopK` and this model itself (never their own components);
raw baselines `RW`/`EWMA`/`HAR`/`HAR-X`; the two blow-up models `RealizedGARCH`/`GuyonLekeufackPDV`;
iter-1 non-winners `LSTMRV`/`XGBHARRSIV`; Track-C pooling (`PanelHAR-FE`,`HAR-Shrink2Group`,`HAR-GVF`)
and Track-E regime (`Threshold-HAR`,`STAR-HAR`,`MS-HAR`) which are outside the §21 "A/B/D" remit.

**How top-K is chosen (`TOP_K=5`).** Per *horizon*, at every monthly refit, rank the eligible
pool by **trailing discounted-MSE** on the purged/embargoed `y_train` and keep the best `TOP_K=5`.
Membership is therefore time-varying and horizon-specific. Example (last refit, clean_core):
- h=1: `HARX-HS, HAR-MAX, HAR-Ridge, HAR-ENet, HAR-CJ`
- h=22: `HARX-HS, HAR-IVTS, HAR-Ridge, HAR-RS-IV-Q, HAR-ENet`
- h=42: `HARX-HS, HAR-GARCH, HAR-Ridge, HAR-ENet, HAR-IVTS`

**Regime-conditional weighting scheme + lookback.** For each (horizon, regime bucket) cell the
top-K are combined with **inverse-discounted-MSE softmax** weights:
`w_c ∝ exp(-log(dMSE_c)/T)`, `T=SOFTMAX_TEMP=1.0`. The error is the **squared log-error**
`(log rv_hat − log target_var)²` (scale-free across tickers/horizons, QLIKE-aligned dispersion),
**discounted** by an exponential time-decay with `HALF_LIFE_DAYS=252` (≈1y) so recent regimes
dominate. **Lookback = expanding** (fold start `lo=0`, the harness default), i.e. all panel history
strictly before the test block, decay-weighted. The regime label is `iv_pctile_bucket`
(5 buckets, `IV_PCTILE_BUCKETS`) from `targets.parquet`. A (horizon,bucket) cell with
`< MIN_CELL_OBS=200` scored rows or `< MIN_COMPONENTS=2` components falls back to the
regime-pooled horizon weights. All 25 (5 horizons × 5 buckets) cells were populated in the
last fold. The combined `sigma` = sqrt(weighted within-model variance + weighted between-model
dispersion); quantiles regenerated via `_lognormal_quantiles` (monotone by construction).

**Leakage controls.**
1. Weights are estimated **only in `fit(X_train, y_train)`**; `y_train` is already purged +
   embargoed by the walk-forward (target window ends ≥`EMBARGO_EXTRA` days before the test block).
2. The time-decay discounts old errors but **every scored row predates the test block** — no
   full-sample or future peeking (covered by `test_no_leakage_weights_change_with_train_window`).
3. `predict` never sees a realized target; it only looks up frozen (horizon, bucket) weights.
4. The regime label `iv_pctile_bucket` is a **trailing** IV-percentile rank, constant across
   horizons for a given (ticker,date) — a point-in-time observable known at prediction time,
   not derived from the future target (verified: 1 distinct bucket per (ticker,date)).
5. A key is combined only where ≥`MIN_COMPONENTS=2` of its bucket's top-K have a finite forecast;
   thin keys are dropped, never imputed.

**Reproducibility.** Deterministic (no RNG): combination is closed-form weighted averaging, so
no seed is required. Component parquets are static inputs.
- Library versions: python 3.12.13 · polars 1.41.1 · numpy 2.4.6 · scipy 1.17.1.
- Device: macOS-15.3.1 arm64 (Apple Silicon), CPU only.
- Wall-clock: clean_core 10.0 s + hard_cases 6.7 s walk-forward (both foreground).

**Coverage.** Full: all 15 scored tickers, all horizons {1,5,10,22,42}; 140,566 OOS rows total
(clean_core 101,890 + hard_cases 38,676; this card's universe shown above). rv_hat finite & >0,
quantiles monotone, sigma finite ≥0 across every row. No tickers/horizons dropped. Component
availability was 100% over the eligible pool, so `MIN_COMPONENTS` never forced a drop.
