# VRP-Spread — Self Stats
_universe=`hard_cases` · primary horizon h=22 · predictions=`execution/data/predictions/VRP-Spread.parquet` · generated 2026-06-03T21:11:57Z_

_Self-only metrics — no leaderboard rank, no DM test, no MCS, no §9 status._
_Cross-model comparison is produced by the final `rv_eval.evaluator` pass._

## Tier-1 pooled by horizon (§3)
| model | horizon | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| VRP-Spread | 1 | 6840 | 0.9715 | 0.9942 | 0.7653 | -0.0923 | 0.8620 | 0.4265 | 0.0005 |
| VRP-Spread | 5 | 6820 | 0.5861 | 0.8310 | 0.6240 | -0.0557 | 0.8504 | 0.4374 | 0.0024 |
| VRP-Spread | 10 | 6775 | 0.5686 | 0.7944 | 0.5845 | -0.0584 | 0.8466 | 0.4359 | 0.0048 |
| VRP-Spread | 22 | 6694 | 0.6920 | 0.8031 | 0.5785 | -0.0312 | 0.8324 | 0.4174 | 0.0102 |
| VRP-Spread | 42 | 6550 | 0.8756 | 0.8338 | 0.5829 | 0.0121 | 0.8125 | 0.4281 | 0.0186 |

## §5 IV-incremental skill (per horizon)
| model | horizon | n | slope | t_slope | sign_acc | qlike_model | qlike_iv | qlike_gain_vs_iv |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| VRP-Spread | 1 | 6840 | 0.8501 | 30.7415 | 0.6550 | 0.9715 | 0.3548 | -0.6167 |
| VRP-Spread | 5 | 6820 | 0.8922 | 23.5200 | 0.6370 | 0.5861 | 0.2576 | -0.3285 |
| VRP-Spread | 10 | 6775 | 0.6363 | 13.8408 | 0.6226 | 0.5686 | 0.2518 | -0.3168 |
| VRP-Spread | 22 | 6694 | 0.5412 | 13.8285 | 0.5980 | 0.6920 | 0.2772 | -0.4149 |
| VRP-Spread | 42 | 6550 | 0.7610 | 29.4342 | 0.6159 | 0.8756 | 0.3324 | -0.5431 |

## §6 Conditional bias by IV-percentile bucket (h=22)
| model | horizon | iv_pctile_bucket | n | qlike | log_bias |
| --- | --- | --- | --- | --- | --- |
| VRP-Spread | 22 | 0 | 1536 | 0.5774 | -0.0264 |
| VRP-Spread | 22 | 1 | 1039 | 0.6291 | -0.0360 |
| VRP-Spread | 22 | 2 | 1193 | 0.5720 | -0.0012 |
| VRP-Spread | 22 | 3 | 1330 | 0.4081 | -0.1070 |
| VRP-Spread | 22 | 4 | 1596 | 1.1697 | 0.0079 |

## §6 Post-shock calibration (h=22)
| model | horizon | bias_all | qlike_all | bias_postshock | qlike_postshock | n_postshock | trap_flag |
| --- | --- | --- | --- | --- | --- | --- | --- |
| VRP-Spread | 22 | -0.0312 | 0.6920 | -0.0457 | 0.7315 | 1257 |  |

## Per-ticker Tier-1 at h=22
| model | horizon | ticker | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| VRP-Spread | 22 | IBIT | 204 | 0.0835 | 0.3936 | 0.3010 | -0.0304 | 0.9461 | 0.6471 | 0.0015 |
| VRP-Spread | 22 | KRE | 1853 | 0.4481 | 0.6247 | 0.4321 | -0.0451 | 0.8996 | 0.4220 | 0.0020 |
| VRP-Spread | 22 | MSOS | 953 | 0.5980 | 0.8021 | 0.6095 | 0.0640 | 0.6076 | 0.1899 | 0.0088 |
| VRP-Spread | 22 | USO | 1853 | 1.3572 | 1.0083 | 0.7110 | 0.0611 | 0.8154 | 0.4026 | 0.0043 |
| VRP-Spread | 22 | UVXY | 1831 | 0.3825 | 0.7629 | 0.6074 | -0.1602 | 0.8859 | 0.5205 | 0.0262 |

## Pooled by group
| model | group | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| VRP-Spread | crypto | 1068 | 0.1551 | 0.5575 | 0.4185 | -0.1217 | 0.9504 | 0.5993 | 0.0010 |
| VRP-Spread | long_volatility_vix | 9185 | 0.7146 | 0.9205 | 0.7185 | -0.1003 | 0.8786 | 0.4980 | 0.0184 |
| VRP-Spread | oil_and_energy | 9295 | 1.1586 | 0.9765 | 0.7061 | -0.0326 | 0.8203 | 0.4188 | 0.0033 |
| VRP-Spread | us_cannabis | 4836 | 0.5500 | 0.7787 | 0.5845 | -0.0321 | 0.6638 | 0.2527 | 0.0060 |
| VRP-Spread | us_cyclicals_sector | 9295 | 0.5060 | 0.7117 | 0.5062 | -0.0029 | 0.9044 | 0.4435 | 0.0014 |

---

## Human-only fields (MODEL_PLAN §5)

**Model.** Model 28 — VRP-Spread head (ITER2 catalog §3, Track D, Pattern P3, direct-quantile). `candidate_models/vrp_spread.py:VRPSpread`, `name="VRP-Spread"`. Bases: `_AttachMixin` + `_QuantileModel` (emits q05..q95 DIRECTLY, BYPASSES the lognormal wrapper).

**What it forecasts.** The variance-risk-premium spread `s_h = iv2_h - rv_h`, with `iv2_h = iv_30d**2 * (h/252)` (point-in-time implied variance, target_var/h-day-sum units). Per-(ticker,horizon) **level-space OLS** (spread can be negative → NOT log) of `s_h`; variance forecast recovered as `rv_hat = clamp(iv2_h - ŝ_h)`. `iv2_h` matches `targets.iv2` exactly but is built from `iv_30d` (in X), so predict() never touches the targets table.

**Features used.**
- Derived & joined (built once on full inputs series, joined by (ticker,date) via `_AttachMixin._derive`): `vrp_d/w/m` = HAR-style trailing means (windows {1,5,22}) of the daily VRP proxy `iv_30d**2/252 - total_rv`.
- Built point-in-time inside `_design` from raw IV tenors: `iv_curv = iv_30d - 2*iv_60d + iv_90d`, `iv_ts_30_90 = iv_90d - iv_30d`.
- Raw X columns: `vix9d_slope`. (`needs` non-null gate: `vrp_d/w/m, iv_30d, iv_60d, iv_90d, vix9d_slope`.)

**Direct quantiles.** Empirical level-space spread-residual quantiles added to `ŝ_h`, back-mapped via `rv = iv2_h - s`; the map FLIPS ordering, so rv-column i uses the REVERSED residual quantile `qlev[-1-i]` (symmetric QUANTILES grid) for a non-decreasing rv grid (`maximum.accumulate` in the base is a final guard). All rv-quantiles and rv_hat clamped finite & positive. `sigma` = level residual sd of the spread.

**Frozen hyperparameters + HP-selection note.** No fitted/tuned hyperparameters; OLS coefs + residual-quantile grid estimated per (ticker,horizon) on each fold's TRAIN slice only. Two by-construction clamp constants (NOT tuned, no inner CV, no OOS peeking): `FLOOR_FRAC=0.25`, `CAP_MULT=4.0`; rv_hat and every rv-quantile clipped into `[FLOOR_FRAC*p05(train target_var), CAP_MULT*max(iv2_h, p95(train target_var))]` (anchors from TRAIN slice only). Lower anchor prevents QLIKE blow-up from a collapsing rv_hat; upper anchor caps rare absurd upside.

**Determinism / seed.** Fully deterministic (least-squares + empirical quantiles); no RNG / seed.

**Coverage.** All 5 hard-case tickers (UVXY, MSOS, IBIT, USO, KRE) × all 5 horizons covered; none dropped (min_obs=100 satisfied). No convergence warnings (closed-form OLS).

**Library versions / device.** python 3.12.13, polars 1.41.1, numpy 2.4.6, scipy 1.17.1. Device: CPU (macOS 15.3.1, arm64 / Apple silicon).

**Wall-clock (full walk-forward, this run).** hard_cases ≈ 4.9 s (clean_core ≈ 10.0 s). OOS rows: hard_cases 34,054; clean_core 93,700 (file total 127,754).

**Calibration / warnings.** hard_cases pooled coverage: cov90 ≈ 0.81–0.86, cov50 ≈ 0.42–0.44 (targets 0.90/0.50 — mildly narrow). No QLIKE blow-ups after the scale-aware clamp (pooled QLIKE 0.57–0.97 across horizons). Long-horizon (h=42) coverage drifts lower (cov90 ≈ 0.81), expected for the high-vol regime-prone hard-case names.
