# HAR-Shrink2Group — Self Stats
_universe=`clean_core` · primary horizon h=22 · predictions=`execution/data/predictions/HAR-Shrink2Group.parquet` · generated 2026-06-03T21:21:02Z_

_Self-only metrics — no leaderboard rank, no DM test, no MCS, no §9 status._
_Cross-model comparison is produced by the final `rv_eval.evaluator` pass._

## Tier-1 pooled by horizon (§3)
| model | horizon | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-Shrink2Group | 1 | 20800 | 0.2829 | 0.7414 | 0.5930 | -0.2380 | 0.8956 | 0.4953 | 0.0000 |
| HAR-Shrink2Group | 5 | 20760 | 0.1826 | 0.5620 | 0.4355 | -0.1224 | 0.9007 | 0.5316 | 0.0002 |
| HAR-Shrink2Group | 10 | 20710 | 0.2057 | 0.5604 | 0.4256 | -0.1065 | 0.9125 | 0.5479 | 0.0003 |
| HAR-Shrink2Group | 22 | 20590 | 0.3361 | 0.6060 | 0.4451 | -0.1022 | 0.9187 | 0.5789 | 0.0008 |
| HAR-Shrink2Group | 42 | 20390 | 0.4494 | 0.6757 | 0.4852 | -0.1148 | 0.9209 | 0.5872 | 0.0015 |

## §5 IV-incremental skill (per horizon)
| model | horizon | n | slope | t_slope | sign_acc | qlike_model | qlike_iv | qlike_gain_vs_iv |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-Shrink2Group | 1 | 20800 | 0.7603 | 52.3716 | 0.7038 | 0.2829 | 0.3273 | 0.0444 |
| HAR-Shrink2Group | 5 | 20760 | 0.7249 | 46.2914 | 0.6600 | 0.1826 | 0.2079 | 0.0253 |
| HAR-Shrink2Group | 10 | 20710 | 0.5553 | 25.5048 | 0.6039 | 0.2057 | 0.2187 | 0.0130 |
| HAR-Shrink2Group | 22 | 20590 | 0.1795 | 5.8767 | 0.5338 | 0.3361 | 0.3397 | 0.0036 |
| HAR-Shrink2Group | 42 | 20390 | 0.2525 | 8.7536 | 0.5010 | 0.4494 | 0.4701 | 0.0207 |

## §6 Conditional bias by IV-percentile bucket (h=22)
| model | horizon | iv_pctile_bucket | n | qlike | log_bias |
| --- | --- | --- | --- | --- | --- |
| HAR-Shrink2Group | 22 | 0 | 5239 | 0.1812 | -0.1260 |
| HAR-Shrink2Group | 22 | 1 | 3448 | 0.3307 | -0.1460 |
| HAR-Shrink2Group | 22 | 2 | 3439 | 0.4912 | -0.1102 |
| HAR-Shrink2Group | 22 | 3 | 3531 | 0.3719 | -0.0831 |
| HAR-Shrink2Group | 22 | 4 | 4933 | 0.3708 | -0.0544 |

## §6 Post-shock calibration (h=22)
| model | horizon | bias_all | qlike_all | bias_postshock | qlike_postshock | n_postshock | trap_flag |
| --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-Shrink2Group | 22 | -0.1022 | 0.3361 | -0.0990 | 0.3930 | 3914 |  |

## Per-ticker Tier-1 at h=22
| model | horizon | ticker | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-Shrink2Group | 22 | EEM | 2059 | 0.2548 | 0.5726 | 0.4277 | -0.0469 | 0.9014 | 0.5799 | 0.0007 |
| HAR-Shrink2Group | 22 | GLD | 2059 | 0.1423 | 0.4688 | 0.3469 | -0.0258 | 0.8912 | 0.5508 | 0.0003 |
| HAR-Shrink2Group | 22 | HYG | 2059 | 0.7656 | 0.8509 | 0.6696 | -0.4178 | 0.9645 | 0.6115 | 0.0002 |
| HAR-Shrink2Group | 22 | IWM | 2059 | 0.3096 | 0.5496 | 0.3918 | -0.0083 | 0.9184 | 0.5585 | 0.0009 |
| HAR-Shrink2Group | 22 | QQQ | 2059 | 0.2973 | 0.6059 | 0.4566 | -0.0708 | 0.9019 | 0.5872 | 0.0008 |
| HAR-Shrink2Group | 22 | SPY | 2059 | 0.4505 | 0.6907 | 0.5207 | -0.0931 | 0.9053 | 0.5610 | 0.0007 |
| HAR-Shrink2Group | 22 | TLT | 2059 | 0.1847 | 0.4666 | 0.3259 | -0.0442 | 0.9247 | 0.5376 | 0.0003 |
| HAR-Shrink2Group | 22 | XLE | 2059 | 0.2815 | 0.5296 | 0.3763 | -0.0547 | 0.9262 | 0.5843 | 0.0014 |
| HAR-Shrink2Group | 22 | XLF | 2059 | 0.3801 | 0.6357 | 0.4929 | -0.1884 | 0.9437 | 0.6090 | 0.0010 |
| HAR-Shrink2Group | 22 | XLK | 2059 | 0.2948 | 0.5932 | 0.4430 | -0.0720 | 0.9097 | 0.6095 | 0.0011 |

## Pooled by group
| model | group | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-Shrink2Group | emerging_markets | 10325 | 0.2896 | 0.6728 | 0.5085 | -0.1086 | 0.8930 | 0.5342 | 0.0005 |
| HAR-Shrink2Group | high_yield_credit | 10325 | 0.5490 | 0.8178 | 0.6456 | -0.3824 | 0.9495 | 0.5991 | 0.0001 |
| HAR-Shrink2Group | oil_and_energy | 10325 | 0.2432 | 0.5420 | 0.3957 | -0.0899 | 0.9135 | 0.5574 | 0.0011 |
| HAR-Shrink2Group | precious_metals | 10325 | 0.2040 | 0.6122 | 0.4626 | -0.1075 | 0.8877 | 0.5133 | 0.0002 |
| HAR-Shrink2Group | us_cyclicals_sector | 10325 | 0.2993 | 0.6220 | 0.4788 | -0.1816 | 0.9345 | 0.5873 | 0.0008 |
| HAR-Shrink2Group | us_large_cap_equity | 20650 | 0.3094 | 0.6525 | 0.4998 | -0.1192 | 0.8999 | 0.5389 | 0.0006 |
| HAR-Shrink2Group | us_rates_and_ig_credit | 10325 | 0.1893 | 0.5470 | 0.4052 | -0.0986 | 0.9056 | 0.5121 | 0.0002 |
| HAR-Shrink2Group | us_small_cap_equity | 10325 | 0.2560 | 0.5541 | 0.4063 | -0.0455 | 0.9062 | 0.5430 | 0.0007 |
| HAR-Shrink2Group | us_technology_sector | 10325 | 0.2581 | 0.6100 | 0.4674 | -0.1174 | 0.9064 | 0.5554 | 0.0008 |

---

## Build provenance (human-only fields — MODEL_PLAN §5)

**Model.** `candidate_models/har_shrink2group.py:HARShrink2Group`, `name="HAR-Shrink2Group"`
(catalog model 23, Track C, Pattern P3 — direct `Model` impl). Per-(ticker, horizon) OLS of
`log(target_var)` whose coefficient vector is **shrunk toward the panel-pooled coefficient
vector**: `beta_shrunk = (1-w)·beta_ticker + w·beta_pooled` (the exact catalog form; `w` =
weight on the pooled vector, in [0,1]). The pooled β for a ticker is `[fe_intercept(ticker),
shared_slopes]` from the frozen Wave-0 `_base_v2.fit_pooled` (ticker fixed-effect intercept +
single shared slope vector, no global intercept); the per-ticker β is its own
`[intercept, slopes]` OLS. Coefficient vectors are length-aligned (`1 + 13`). Lognormal
predictive distribution via `_base_v2._emit_lognormal`: level mean `m = exp(mu + s²/2)`, log-sd
`s` = the shrunk model's in-sample residual std per (ticker, horizon).

**Features used.** `HAR_RS_FEATURES + IV_FEATURES` =
`[log_rv_d, log_rv_w, log_rv_m, rs_minus_5d, rs_plus_5d, jump_5d, log_iv, iv_slope, skew_25d,
vix, vix3m, vix_slope, vvix]` (13 slopes + intercept) — identical block to PanelHAR-FE (model
22) so the shrinkage is apples-to-apples. **No `_AttachMixin` / derived rolling columns**: every
feature is produced point-in-time by `rv_eval.features.build_features(inputs.parquet)`, so there
is no rolling recomputation on the predict slice and no window-feature leakage. `post_shock` /
`iv2` (targets-only, §4) are not used; IV regressors are the in-X ORATS transforms.

**Frozen hyperparameters + HP-selection note.** One hyperparameter: the shrinkage intensity
`w_h` per horizon, chosen from the grid `{0.0, 0.1, …, 1.0}` by a **time-ordered expanding inner
CV (4 folds) on the TRAIN slice only** — pooled (across tickers) held-out log-MSE, ties broken
toward MORE pooling (larger w). It is re-selected at every monthly refit on that fold's train
data; **never** tuned on OOS or against other models. On a representative late-expanding train
slice (all data < 2024-01) the selected weights were
`w = {h1:0.50, h5:0.60, h10:0.60, h22:0.80, h42:0.90}` — i.e. progressively MORE shrinkage to
the panel at longer horizons (noisier per-ticker estimates), which is the intended behaviour.
Structural (non-tuned) constants: `min_ticker_obs=100` (a (ticker,h) with fewer train rows uses
the pooled β outright — w=1 for it, recorded in `self.warnings`), `min_pooled_obs=200` (gates a
horizon's fit), inner-CV folds `=4`, `s`-floor `1e-3`.

**Fallbacks.** Thin (ticker,h): pooled β outright. Ticker unseen in a fold's train: pooled β via
the group-mean → global-mean FE-intercept fallback (`_pooled_beta_for`, mirrors
`_base_v2.pooled_mu`). Neither errors. On the real panel there were **0 thin-ticker fallbacks**
(all 15 tickers clear `min_ticker_obs` at every refit/horizon).

**Coverage.** Full: all 10 clean_core tickers (here) + all 5 hard_cases (sibling card) × all 5
horizons {1,5,10,22,42}. 104,000 OOS rows clean_core (143,745 total across both universes). All
`rv_hat` finite and > 0; quantiles monotone (enforced in `_emit_lognormal`). No tickers/horizons
dropped.

**Warnings / calibration.** Mild negative `log_bias` (under-prediction) across horizons (-0.24 at
h=1 shrinking to ~-0.10 at h≥10), concentrated on HYG (h=22 bias -0.42, qlike 0.77 — the credit
ETF with the most idiosyncratic HAR shape). cov90 ≈ 0.90–0.92 near nominal; cov50 modestly
over-wide at long horizons. §5 IV-incremental QLIKE gain positive at every horizon (h=22 gain
+0.0036, vs PanelHAR-FE's -0.0028 — the shrinkage recovers a small positive IV edge at the
primary horizon). No convergence issues (closed-form lstsq).

**Reproducibility.** Deterministic — lstsq + a fixed-fraction time-ordered inner CV, no RNG;
seed N/A (numpy default_rng used only in the synthetic smoke test, seed=0). Libraries: numpy
2.4.6, polars 1.41.1, scipy 1.17.1, python 3.12.13. Device: CPU (Darwin 24.3.0, local `.venv`).
Wall-clock (walk-forward, monthly refit 2018-01..2026-05): clean_core 39.3s, hard_cases 12.9s.
Smoke test `candidate_models/tests/test_har_shrink2group.py`: 3 passed.
