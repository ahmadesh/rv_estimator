# PanelHAR-FE — Self Stats
_universe=`clean_core` · primary horizon h=22 · predictions=`execution/data/predictions/PanelHAR-FE.parquet` · generated 2026-06-03T21:16:12Z_

_Self-only metrics — no leaderboard rank, no DM test, no MCS, no §9 status._
_Cross-model comparison is produced by the final `rv_eval.evaluator` pass._

## Tier-1 pooled by horizon (§3)
| model | horizon | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| PanelHAR-FE | 1 | 20800 | 0.2882 | 0.7421 | 0.5955 | -0.2394 | 0.8965 | 0.5098 | 0.0000 |
| PanelHAR-FE | 5 | 20760 | 0.1836 | 0.5611 | 0.4348 | -0.1221 | 0.9054 | 0.5438 | 0.0002 |
| PanelHAR-FE | 10 | 20710 | 0.2063 | 0.5566 | 0.4229 | -0.1056 | 0.9183 | 0.5621 | 0.0003 |
| PanelHAR-FE | 22 | 20590 | 0.3425 | 0.5977 | 0.4410 | -0.1025 | 0.9219 | 0.5978 | 0.0008 |
| PanelHAR-FE | 42 | 20390 | 0.4617 | 0.6639 | 0.4787 | -0.1156 | 0.9244 | 0.6082 | 0.0015 |

## §5 IV-incremental skill (per horizon)
| model | horizon | n | slope | t_slope | sign_acc | qlike_model | qlike_iv | qlike_gain_vs_iv |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| PanelHAR-FE | 1 | 20800 | 0.7129 | 52.2036 | 0.6908 | 0.2882 | 0.3273 | 0.0391 |
| PanelHAR-FE | 5 | 20760 | 0.7065 | 46.9325 | 0.6530 | 0.1836 | 0.2079 | 0.0242 |
| PanelHAR-FE | 10 | 20710 | 0.5484 | 26.1080 | 0.6005 | 0.2063 | 0.2187 | 0.0124 |
| PanelHAR-FE | 22 | 20590 | 0.1854 | 6.2040 | 0.5336 | 0.3425 | 0.3397 | -0.0028 |
| PanelHAR-FE | 42 | 20390 | 0.2476 | 8.8192 | 0.5052 | 0.4617 | 0.4701 | 0.0084 |

## §6 Conditional bias by IV-percentile bucket (h=22)
| model | horizon | iv_pctile_bucket | n | qlike | log_bias |
| --- | --- | --- | --- | --- | --- |
| PanelHAR-FE | 22 | 0 | 5239 | 0.1830 | -0.1187 |
| PanelHAR-FE | 22 | 1 | 3448 | 0.3460 | -0.1443 |
| PanelHAR-FE | 22 | 2 | 3439 | 0.5127 | -0.1120 |
| PanelHAR-FE | 22 | 3 | 3531 | 0.3642 | -0.0890 |
| PanelHAR-FE | 22 | 4 | 4933 | 0.3753 | -0.0593 |

## §6 Post-shock calibration (h=22)
| model | horizon | bias_all | qlike_all | bias_postshock | qlike_postshock | n_postshock | trap_flag |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PanelHAR-FE | 22 | -0.1025 | 0.3425 | -0.1072 | 0.4007 | 3914 |  |

## Per-ticker Tier-1 at h=22
| model | horizon | ticker | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| PanelHAR-FE | 22 | EEM | 2059 | 0.2538 | 0.5745 | 0.4307 | -0.0568 | 0.9072 | 0.5954 | 0.0007 |
| PanelHAR-FE | 22 | GLD | 2059 | 0.1368 | 0.4803 | 0.3673 | -0.1031 | 0.9466 | 0.6790 | 0.0003 |
| PanelHAR-FE | 22 | HYG | 2059 | 0.8484 | 0.7818 | 0.5889 | -0.2462 | 0.8878 | 0.4415 | 0.0002 |
| PanelHAR-FE | 22 | IWM | 2059 | 0.2985 | 0.5517 | 0.3988 | -0.0480 | 0.9398 | 0.6260 | 0.0010 |
| PanelHAR-FE | 22 | QQQ | 2059 | 0.2975 | 0.6048 | 0.4546 | -0.0642 | 0.8995 | 0.5833 | 0.0008 |
| PanelHAR-FE | 22 | SPY | 2059 | 0.4586 | 0.6845 | 0.5118 | -0.0638 | 0.8839 | 0.5255 | 0.0007 |
| PanelHAR-FE | 22 | TLT | 2059 | 0.1768 | 0.4813 | 0.3468 | -0.1272 | 0.9675 | 0.6955 | 0.0003 |
| PanelHAR-FE | 22 | XLE | 2059 | 0.2715 | 0.5348 | 0.3884 | -0.0977 | 0.9495 | 0.6639 | 0.0015 |
| PanelHAR-FE | 22 | XLF | 2059 | 0.3875 | 0.6279 | 0.4813 | -0.1562 | 0.9276 | 0.5610 | 0.0010 |
| PanelHAR-FE | 22 | XLK | 2059 | 0.2956 | 0.5919 | 0.4408 | -0.0622 | 0.9092 | 0.6066 | 0.0011 |

## Pooled by group
| model | group | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| PanelHAR-FE | emerging_markets | 10325 | 0.2959 | 0.6677 | 0.5052 | -0.0893 | 0.8804 | 0.5269 | 0.0005 |
| PanelHAR-FE | high_yield_credit | 10325 | 0.5999 | 0.7654 | 0.5822 | -0.2524 | 0.8776 | 0.4711 | 0.0001 |
| PanelHAR-FE | oil_and_energy | 10325 | 0.2371 | 0.5541 | 0.4125 | -0.1416 | 0.9494 | 0.6449 | 0.0011 |
| PanelHAR-FE | precious_metals | 10325 | 0.2060 | 0.6113 | 0.4695 | -0.1300 | 0.9027 | 0.5633 | 0.0002 |
| PanelHAR-FE | us_cyclicals_sector | 10325 | 0.3036 | 0.6208 | 0.4753 | -0.1722 | 0.9314 | 0.5682 | 0.0008 |
| PanelHAR-FE | us_large_cap_equity | 20650 | 0.3120 | 0.6512 | 0.4973 | -0.1100 | 0.8975 | 0.5342 | 0.0006 |
| PanelHAR-FE | us_rates_and_ig_credit | 10325 | 0.1848 | 0.5582 | 0.4220 | -0.1583 | 0.9417 | 0.6125 | 0.0002 |
| PanelHAR-FE | us_small_cap_equity | 10325 | 0.2489 | 0.5615 | 0.4175 | -0.0916 | 0.9395 | 0.6189 | 0.0007 |
| PanelHAR-FE | us_technology_sector | 10325 | 0.2584 | 0.6115 | 0.4681 | -0.1170 | 0.9145 | 0.5668 | 0.0008 |

---

## Build provenance (human-only fields — MODEL_PLAN §5)

**Model.** `candidate_models/panel_har.py:PanelHARFE`, `name="PanelHAR-FE"` (catalog model 22,
Track C, Pattern P3). Pooled log-OLS of `log(target_var)` per horizon **across all tickers in the
TRAIN slice**, with a **ticker fixed-effect intercept** (one dummy per train ticker, no global
intercept) and a **single shared slope vector**. Built on the frozen Wave-0 base
`_base_v2._PooledLinearHAR` / `fit_pooled` / `pooled_mu` (FE design matrix, lstsq fit, lognormal
predictive quantiles, unseen-ticker fallback). Lognormal predictive distribution: level mean
`m = exp(mu + s^2/2)`, log-sd `s` = pooled in-sample residual std (per horizon), quantiles via
`_lognormal_quantiles`.

**Features used (the pooled slope block).** `HAR_RS_FEATURES + IV_FEATURES` =
`[log_rv_d, log_rv_w, log_rv_m, rs_minus_5d, rs_plus_5d, jump_5d,` `log_iv, iv_slope, skew_25d,
vix, vix3m, vix_slope, vvix]` (13 slopes). **No derived/`_AttachMixin` columns** — every feature
comes straight from `rv_eval.features.build_features(inputs.parquet)` point-in-time, so there is
no rolling recomputation on the predict slice and no leakage risk from window features. `post_shock`
/ `iv2` (targets-only) are not used; the IV regressors are the in-X ORATS transforms.

**Fixed effects / pooling discipline.** FE intercepts and the shared slopes are estimated on the
TRAIN slice only at each monthly refit. A test ticker unseen in train falls back to its
group-mean intercept (`C.GROUP`), then the global-mean intercept — verified by
`test_unseen_ticker_falls_back_to_pooled_intercept`. Per-horizon pooling (separate fit for
h in {1,5,10,22,42}). `min_pooled_obs=200` (base default) gates a horizon's fit.

**Frozen hyperparameters + HP-selection note.** None. Plain pooled OLS — no penalty, no shrinkage
weight, no tuned window. Nothing was selected on any validation block; there is nothing to leak.
(`min_pooled_obs=200`, `s`-floor `1e-3` are structural base constants, not tuned.)

**Coverage.** Full: all 15 scored tickers (10 clean_core here + 5 hard_cases in the sibling card)
x all 5 horizons. 104,000 OOS rows in clean_core (143,745 total across both universes). All
`rv_hat` finite and > 0; quantiles monotone (enforced by the base). No horizons/tickers dropped.

**Warnings.** Mild negative `log_bias` (under-prediction) across horizons, largest at h=1
(-0.24) and on HYG (-0.25); cov90 ~0.90-0.92 (near nominal), cov50 slightly over-wide at long
horizons. No convergence issues (closed-form lstsq). §5 IV-incremental QLIKE gain is positive at
h=1/5/10/42 and ~flat (-0.003) at h=22.

**Reproducibility.** Deterministic (lstsq, no RNG) — seed N/A. Libraries: numpy 2.4.6,
polars 1.41.1, scipy 1.17.1, python 3.12.13. Device: CPU (Darwin 24.3.0, local .venv).
Wall-clock: clean_core 9.1s, hard_cases 3.3s (walk-forward, monthly refit 2018-01..2026-05).
