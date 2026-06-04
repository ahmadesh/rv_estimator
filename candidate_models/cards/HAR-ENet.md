# HAR-ENet — Self Stats
_universe=`clean_core` · primary horizon h=22 · predictions=`execution/data/predictions/HAR-ENet.parquet` · generated 2026-06-03T18:27:46Z_

_Self-only metrics — no leaderboard rank, no DM test, no MCS, no §9 status._
_Cross-model comparison is produced by the final `rv_eval.evaluator` pass._

## Tier-1 pooled by horizon (§3)
| model | horizon | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-ENet | 1 | 20570 | 0.2755 | 0.7179 | 0.5707 | -0.2072 | 0.8931 | 0.4961 | 0.0000 |
| HAR-ENet | 5 | 20530 | 0.1800 | 0.5513 | 0.4264 | -0.1042 | 0.8989 | 0.5221 | 0.0002 |
| HAR-ENet | 10 | 20480 | 0.2067 | 0.5558 | 0.4205 | -0.0936 | 0.9093 | 0.5415 | 0.0003 |
| HAR-ENet | 22 | 20360 | 0.3406 | 0.6056 | 0.4449 | -0.1001 | 0.9171 | 0.5623 | 0.0008 |
| HAR-ENet | 42 | 20160 | 0.4543 | 0.6747 | 0.4859 | -0.1059 | 0.9172 | 0.5706 | 0.0015 |

## §5 IV-incremental skill (per horizon)
| model | horizon | n | slope | t_slope | sign_acc | qlike_model | qlike_iv | qlike_gain_vs_iv |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-ENet | 1 | 20570 | 0.4834 | 45.7244 | 0.7197 | 0.2755 | 0.3278 | 0.0523 |
| HAR-ENet | 5 | 20530 | 0.6678 | 54.2101 | 0.6771 | 0.1800 | 0.2087 | 0.0287 |
| HAR-ENet | 10 | 20480 | 0.4569 | 25.3515 | 0.6121 | 0.2067 | 0.2201 | 0.0134 |
| HAR-ENet | 22 | 20360 | -0.0567 | -1.8730 | 0.5399 | 0.3406 | 0.3419 | 0.0012 |
| HAR-ENet | 42 | 20160 | 0.0415 | 1.5953 | 0.5257 | 0.4543 | 0.4743 | 0.0200 |

## §6 Conditional bias by IV-percentile bucket (h=22)
| model | horizon | iv_pctile_bucket | n | qlike | log_bias |
| --- | --- | --- | --- | --- | --- |
| HAR-ENet | 22 | 0 | 5149 | 0.1778 | -0.1559 |
| HAR-ENet | 22 | 1 | 3408 | 0.3300 | -0.1542 |
| HAR-ENet | 22 | 2 | 3412 | 0.5052 | -0.1104 |
| HAR-ENet | 22 | 3 | 3497 | 0.3789 | -0.0679 |
| HAR-ENet | 22 | 4 | 4894 | 0.3772 | -0.0195 |

## §6 Post-shock calibration (h=22)
| model | horizon | bias_all | qlike_all | bias_postshock | qlike_postshock | n_postshock | trap_flag |
| --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-ENet | 22 | -0.1001 | 0.3406 | -0.0534 | 0.4046 | 3871 |  |

## Per-ticker Tier-1 at h=22
| model | horizon | ticker | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-ENet | 22 | EEM | 2036 | 0.2587 | 0.5711 | 0.4252 | -0.0572 | 0.9023 | 0.5825 | 0.0007 |
| HAR-ENet | 22 | GLD | 2036 | 0.1419 | 0.4661 | 0.3448 | -0.0416 | 0.8939 | 0.5285 | 0.0003 |
| HAR-ENet | 22 | HYG | 2036 | 0.7850 | 0.8370 | 0.6569 | -0.3662 | 0.9533 | 0.5496 | 0.0002 |
| HAR-ENet | 22 | IWM | 2036 | 0.2976 | 0.5451 | 0.3913 | -0.0039 | 0.9194 | 0.5530 | 0.0009 |
| HAR-ENet | 22 | QQQ | 2036 | 0.3068 | 0.6041 | 0.4437 | -0.0223 | 0.8910 | 0.5791 | 0.0008 |
| HAR-ENet | 22 | SPY | 2036 | 0.4538 | 0.6868 | 0.5138 | -0.0820 | 0.9062 | 0.5624 | 0.0007 |
| HAR-ENet | 22 | TLT | 2036 | 0.2043 | 0.4814 | 0.3368 | -0.0438 | 0.9194 | 0.5093 | 0.0003 |
| HAR-ENet | 22 | XLE | 2036 | 0.2881 | 0.5361 | 0.3841 | -0.0816 | 0.9327 | 0.5810 | 0.0014 |
| HAR-ENet | 22 | XLF | 2036 | 0.3643 | 0.6367 | 0.4992 | -0.2084 | 0.9440 | 0.5806 | 0.0011 |
| HAR-ENet | 22 | XLK | 2036 | 0.3059 | 0.6046 | 0.4535 | -0.0938 | 0.9086 | 0.5972 | 0.0011 |

## Pooled by group
| model | group | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-ENet | emerging_markets | 10210 | 0.2836 | 0.6680 | 0.5070 | -0.1221 | 0.8947 | 0.5316 | 0.0005 |
| HAR-ENet | high_yield_credit | 10210 | 0.5670 | 0.8000 | 0.6257 | -0.3266 | 0.9340 | 0.5515 | 0.0001 |
| HAR-ENet | oil_and_energy | 10210 | 0.2438 | 0.5393 | 0.3939 | -0.0878 | 0.9131 | 0.5515 | 0.0011 |
| HAR-ENet | precious_metals | 10210 | 0.2041 | 0.6048 | 0.4568 | -0.1100 | 0.8857 | 0.5049 | 0.0002 |
| HAR-ENet | us_cyclicals_sector | 10210 | 0.2821 | 0.6162 | 0.4796 | -0.1962 | 0.9359 | 0.5679 | 0.0008 |
| HAR-ENet | us_large_cap_equity | 20420 | 0.3059 | 0.6398 | 0.4864 | -0.0879 | 0.8948 | 0.5359 | 0.0006 |
| HAR-ENet | us_rates_and_ig_credit | 10210 | 0.2070 | 0.5517 | 0.4098 | -0.0847 | 0.8993 | 0.4920 | 0.0002 |
| HAR-ENet | us_small_cap_equity | 10210 | 0.2461 | 0.5435 | 0.3978 | -0.0302 | 0.9093 | 0.5474 | 0.0007 |
| HAR-ENet | us_technology_sector | 10210 | 0.2624 | 0.5986 | 0.4539 | -0.0902 | 0.9089 | 0.5646 | 0.0008 |

---
## Model build notes (human-only, MODEL_PLAN §5)
**Model** `HAR-ENet` · file `candidate_models/har_shrink.py:HARENet` · Pattern P2 (`_PerKeyModel` over `_AttachMixin`).

**Mean model.** Per-(ticker, horizon) ElasticNet regression of `log(target_var)` on the HAR-MAX (model 18) kitchen-sink feature matrix (~25 cols, deduped), lognormal-mean corrected `rv_hat = exp(mu + 0.5·s²)`.

**Features used (`needs`, deduped, order-stable):**
- Pass-through (in X via `build_features`): `HAR_RS_FEATURES` (`log_rv_d, log_rv_w, log_rv_m, rs_minus_5d, rs_plus_5d, jump_5d`) + `IV_FEATURES` (`log_iv, iv_slope, skew_25d, vix, vix3m, vix_slope, vvix`) + `sqrt_rq`.
- Derived (built once on the full series from `inputs.parquet`, joined by (ticker,date) via `_AttachMixin._derive`):
  - leverage (13): `lev_d/w/m = rolling_mean(min(ret_cc,0),{1,5,22})`
  - signed jump (14): `sj_5d = rolling_mean(rs_plus-rs_minus,5)`, `abs_sj_5d`
  - IV-TS/VRP (15): `iv_curv, iv_ts_30_90, vrp_lag=iv_30d²-total_rv, vrp_mom=vrp_lag-vrp_lag.shift(5)`
  - range (16): `log_park_d/w, log_gk_d/w = log(rolling_mean(parkinson/gk,{1,5}))`
  - activity (17): `log_vol_surprise, log_txn_surprise` (log minus 22d log-mean), `overnight_share = rv_overnight/total_rv`
- `vrp_lag` uses `iv_30d²` (in X), **not** `targets.iv2` (CATALOG §4 #2). No `post_shock`/`iv2` used.

**Hyperparameter selection (shrinkage discipline).** Penalty chosen by a **time-ordered inner CV on the TRAIN slice only** — `sklearn.model_selection.TimeSeriesSplit(n_splits=5)` inside `ElasticNetCV` (50-point alpha path, `l1_ratio ∈ {.1,.3,.5,.7,.9,.95,.99,1.0}`, `max_iter=20000`, `tol=1e-4`). No OOS rows or other models' results are consulted. Features standardised inside the fit (μ/σ from the train slice, re-applied at predict). `sigma` = dof-aware in-sample log-residual std.
**Selected HP (final full-clean_core fit, 50 keys):** alpha min/median/max = 0.00138 / 0.0143 / 0.255; l1_ratio counts = {1.0:34, 0.5:4, 0.1:4, 0.7:3, 0.9:3, 0.3:2} (mostly pure-Lasso, some elastic mix). Per-(ticker,h) values recorded on `self.warnings` at fit time.

**Env / repro.** python 3.12.13 · numpy 2.4.6 · polars 1.41.1 · scipy 1.17.1 · scikit-learn 1.8.0 · macOS-15.3.1 arm64 (Apple Silicon, CPU, n_jobs=1). Seed: `random_state=0` (ElasticNetCV). Deterministic given the fixed TimeSeriesSplit.

**Wall-clock.** clean_core 567.3s · hard_cases 183.5s (walk-forward, monthly refit, expanding window).

**Coverage / warnings.** Full coverage — all 15 scored tickers × 5 horizons predicted on both universes. clean_core 102,850 OOS rows; hard_cases 37,989 OOS rows (span 2018-01-02 → 2026-05-21). No convergence failures, no dropped (ticker,horizon). Coverage note: 90% PI coverage runs ~0.89–0.92 and 50% PI ~0.49–0.57 across horizons (mild over-coverage at long h); negative log_bias indicates a small low bias typical of the lognormal-mean HAR family.
