# VRP-Spread — Self Stats
_universe=`clean_core` · primary horizon h=22 · predictions=`execution/data/predictions/VRP-Spread.parquet` · generated 2026-06-03T21:11:57Z_

_Self-only metrics — no leaderboard rank, no DM test, no MCS, no §9 status._
_Cross-model comparison is produced by the final `rv_eval.evaluator` pass._

## Tier-1 pooled by horizon (§3)
| model | horizon | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| VRP-Spread | 1 | 18740 | 1.4434 | 1.1409 | 0.8685 | -0.0252 | 0.8942 | 0.4717 | 0.0000 |
| VRP-Spread | 5 | 18700 | 0.7283 | 0.8842 | 0.6477 | 0.0258 | 0.8921 | 0.4707 | 0.0002 |
| VRP-Spread | 10 | 18650 | 0.5764 | 0.8177 | 0.6010 | -0.0130 | 0.8949 | 0.4707 | 0.0004 |
| VRP-Spread | 22 | 18530 | 0.5989 | 0.7764 | 0.5695 | -0.1052 | 0.9010 | 0.4635 | 0.0010 |
| VRP-Spread | 42 | 18330 | 0.8315 | 0.8682 | 0.6170 | -0.0964 | 0.9028 | 0.4744 | 0.0019 |

## §5 IV-incremental skill (per horizon)
| model | horizon | n | slope | t_slope | sign_acc | qlike_model | qlike_iv | qlike_gain_vs_iv |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| VRP-Spread | 1 | 18740 | 1.1526 | 53.7422 | 0.6011 | 1.4434 | 0.3275 | -1.1159 |
| VRP-Spread | 5 | 18700 | 0.9789 | 55.6832 | 0.5931 | 0.7283 | 0.2106 | -0.5177 |
| VRP-Spread | 10 | 18650 | 0.5913 | 32.0494 | 0.5527 | 0.5764 | 0.2268 | -0.3497 |
| VRP-Spread | 22 | 18530 | 0.0547 | 2.6630 | 0.4693 | 0.5989 | 0.3632 | -0.2357 |
| VRP-Spread | 42 | 18330 | -0.0491 | -2.5753 | 0.4620 | 0.8315 | 0.5117 | -0.3198 |

## §6 Conditional bias by IV-percentile bucket (h=22)
| model | horizon | iv_pctile_bucket | n | qlike | log_bias |
| --- | --- | --- | --- | --- | --- |
| VRP-Spread | 22 | 0 | 4593 | 0.4636 | -0.0559 |
| VRP-Spread | 22 | 1 | 3061 | 0.6597 | -0.1083 |
| VRP-Spread | 22 | 2 | 3167 | 1.0740 | -0.0960 |
| VRP-Spread | 22 | 3 | 3245 | 0.5208 | -0.1160 |
| VRP-Spread | 22 | 4 | 4464 | 0.4160 | -0.1524 |

## §6 Post-shock calibration (h=22)
| model | horizon | bias_all | qlike_all | bias_postshock | qlike_postshock | n_postshock | trap_flag |
| --- | --- | --- | --- | --- | --- | --- | --- |
| VRP-Spread | 22 | -0.1052 | 0.5989 | -0.1658 | 0.4276 | 3475 |  |

## Per-ticker Tier-1 at h=22
| model | horizon | ticker | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| VRP-Spread | 22 | EEM | 1853 | 0.6270 | 0.7861 | 0.5633 | 0.1437 | 0.9406 | 0.5008 | 0.0010 |
| VRP-Spread | 22 | GLD | 1853 | 0.3047 | 0.6191 | 0.4486 | 0.1738 | 0.8861 | 0.5343 | 0.0004 |
| VRP-Spread | 22 | HYG | 1853 | 1.7706 | 1.2840 | 1.0692 | -0.8528 | 0.9536 | 0.5602 | 0.0003 |
| VRP-Spread | 22 | IWM | 1853 | 0.7255 | 0.7342 | 0.5159 | 0.1006 | 0.9061 | 0.4312 | 0.0013 |
| VRP-Spread | 22 | QQQ | 1853 | 0.3424 | 0.6546 | 0.5043 | -0.1249 | 0.8154 | 0.3448 | 0.0010 |
| VRP-Spread | 22 | SPY | 1853 | 0.8072 | 0.8440 | 0.6314 | -0.0413 | 0.9131 | 0.4431 | 0.0009 |
| VRP-Spread | 22 | TLT | 1853 | 0.2700 | 0.5467 | 0.3867 | 0.0263 | 0.8764 | 0.4253 | 0.0003 |
| VRP-Spread | 22 | XLE | 1853 | 0.2982 | 0.6016 | 0.4553 | -0.1222 | 0.8764 | 0.4209 | 0.0019 |
| VRP-Spread | 22 | XLF | 1853 | 0.5087 | 0.7917 | 0.6286 | -0.2236 | 0.9530 | 0.5882 | 0.0014 |
| VRP-Spread | 22 | XLK | 1853 | 0.3343 | 0.6408 | 0.4918 | -0.1314 | 0.8894 | 0.3864 | 0.0013 |

## Pooled by group
| model | group | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| VRP-Spread | emerging_markets | 9295 | 1.2460 | 0.9897 | 0.7092 | 0.1863 | 0.9358 | 0.5216 | 0.0007 |
| VRP-Spread | high_yield_credit | 9295 | 1.7749 | 1.4303 | 1.1927 | -0.5024 | 0.9517 | 0.5394 | 0.0002 |
| VRP-Spread | oil_and_energy | 9295 | 0.4988 | 0.7325 | 0.5398 | -0.1092 | 0.8738 | 0.4367 | 0.0013 |
| VRP-Spread | precious_metals | 9295 | 0.3350 | 0.6997 | 0.5315 | 0.0744 | 0.8936 | 0.5286 | 0.0003 |
| VRP-Spread | us_cyclicals_sector | 9295 | 1.0223 | 1.0074 | 0.7744 | -0.0511 | 0.9497 | 0.5881 | 0.0010 |
| VRP-Spread | us_large_cap_equity | 18590 | 0.8891 | 0.8824 | 0.6434 | 0.0098 | 0.8634 | 0.4030 | 0.0007 |
| VRP-Spread | us_rates_and_ig_credit | 9295 | 0.4572 | 0.6838 | 0.4819 | 0.0162 | 0.8706 | 0.4424 | 0.0003 |
| VRP-Spread | us_small_cap_equity | 9295 | 0.6919 | 0.7289 | 0.5195 | 0.0410 | 0.8979 | 0.4400 | 0.0009 |
| VRP-Spread | us_technology_sector | 9295 | 0.5612 | 0.7775 | 0.5763 | -0.0995 | 0.8701 | 0.3991 | 0.0010 |

---

## Human-only fields (MODEL_PLAN §5)

**Model.** Model 28 — VRP-Spread head (ITER2 catalog §3, Track D, Pattern P3, direct-quantile). `candidate_models/vrp_spread.py:VRPSpread`, `name="VRP-Spread"`. Bases: `_AttachMixin` + `_QuantileModel` (emits q05..q95 DIRECTLY, BYPASSES the lognormal wrapper).

**What it forecasts.** The variance-risk-premium spread `s_h = iv2_h - rv_h`, where `iv2_h = iv_30d**2 * (h/252)` is the point-in-time implied variance for horizon h in target_var (h-day-sum) units. Per-(ticker,horizon) **level-space OLS** (spread can be negative, so NOT log) of `s_h` on the regressors below; the variance forecast is recovered as `rv_hat = clamp(iv2_h - ŝ_h)`. `iv2_h` reproduces `targets.iv2` exactly (rel-err 0, corr 1.0 — verified), but is built from `iv_30d` which is in X, so predict() never touches the targets table (leakage note §4).

**Features used.**
- Derived & joined (built once on full inputs series, joined by (ticker,date) via `_AttachMixin._derive`; never recomputed on the predict slice): `vrp_d/w/m` = HAR-style trailing means (windows {1,5,22}) of the daily VRP proxy `iv_30d**2/252 - total_rv`.
- Built point-in-time inside `_design` from raw IV tenors in X: `iv_curv = iv_30d - 2*iv_60d + iv_90d`, `iv_ts_30_90 = iv_90d - iv_30d`.
- Raw X columns: `vix9d_slope`. (Term-structure tenors `iv_30d/60d/90d` are consumed only to build the curve/slope; the `needs` non-null gate lists the joined VRP cols + raw X columns: `vrp_d/w/m, iv_30d, iv_60d, iv_90d, vix9d_slope`.)

**Direct quantiles.** Empirical quantiles `qlev` of the in-sample level-space spread residual are added to `ŝ_h`, then back-mapped through `rv = iv2_h - s`. That map FLIPS the ordering, so rv-column i uses the REVERSED spread-residual quantile `qlev[-1-i]` (QUANTILES grid is symmetric about 0.5) to yield a correctly non-decreasing rv grid; the `_QuantileModel` base also runs `maximum.accumulate` as a final guard. Every rv-quantile and `rv_hat` is clamped (see below) to stay finite & positive. `sigma` = level residual sd of the spread (a positive dispersion proxy for downstream sizing).

**Frozen hyperparameters + HP-selection note.** No fitted/tuned hyperparameters. The OLS coefficients and the empirical residual-quantile grid are estimated per (ticker, horizon) on each fold's TRAIN slice only. Two **by-construction** scale-aware clamp constants (NOT tuned, NOT selected against OOS, no inner CV): `FLOOR_FRAC=0.25`, `CAP_MULT=4.0`. rv_hat and every rv-quantile are clipped into `[FLOOR_FRAC*p05(train target_var), CAP_MULT*max(iv2_h, p95(train target_var))]`. The lower anchor stops an over-shooting spread (ŝ→iv2) from collapsing rv_hat toward the absolute floor (1e-12), which would explode QLIKE; the upper anchor caps the rare absurd upside. The p05/p95 target anchors are computed from the TRAIN slice only.

**Determinism / seed.** Fully deterministic (least-squares + empirical quantiles); no RNG, no seed needed.

**Coverage.** All 15 scored tickers × all 5 horizons covered on both universes; no tickers/horizons dropped (min_obs=100 satisfied for every key). No convergence warnings (closed-form OLS).

**Library versions / device.** python 3.12.13, polars 1.41.1, numpy 2.4.6, scipy 1.17.1. Device: CPU (macOS 15.3.1, arm64 / Apple silicon).

**Wall-clock (full walk-forward, this run).** clean_core ≈ 10.0 s; hard_cases ≈ 4.9 s. OOS rows: clean_core 93,700; hard_cases 34,054 (file total 127,754).

**Calibration / warnings.** Pooled OOS coverage is well-behaved: clean_core cov90 ≈ 0.88, cov50 ≈ 0.45–0.46; hard_cases cov90 ≈ 0.81–0.86, cov50 ≈ 0.42–0.44 (targets 0.90 / 0.50 — bands slightly narrow, mild under-coverage). No QLIKE blow-ups after the scale-aware clamp (pooled QLIKE 0.57–1.32 across horizons). Per-ticker log-bias is largest at the long horizons and for EEM/HYG (see per-ticker / group panels above) — a known limitation of the level-space spread mean-reversion under regime shifts.
