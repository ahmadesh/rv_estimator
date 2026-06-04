# Threshold-HAR — Self Stats
_universe=`hard_cases` · primary horizon h=22 · predictions=`execution/data/predictions/Threshold-HAR.parquet` · generated 2026-06-03T22:04:53Z_

_Self-only metrics — no leaderboard rank, no DM test, no MCS, no §9 status._
_Cross-model comparison is produced by the final `rv_eval.evaluator` pass._

## Tier-1 pooled by horizon (§3)
| model | horizon | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Threshold-HAR | 1 | 7729 | 0.3075 | 0.7436 | 0.5866 | -0.2486 | 0.8869 | 0.4964 | 0.0004 |
| Threshold-HAR | 5 | 7709 | 0.2506 | 0.6327 | 0.4784 | -0.1488 | 0.8673 | 0.5053 | 0.0020 |
| Threshold-HAR | 10 | 7663 | 0.2634 | 0.6333 | 0.4765 | -0.1149 | 0.8485 | 0.4942 | 0.0042 |
| Threshold-HAR | 22 | 7581 | 0.3051 | 0.6419 | 0.4816 | -0.0630 | 0.8329 | 0.4704 | 0.0089 |
| Threshold-HAR | 42 | 7440 | 0.3481 | 0.6603 | 0.4921 | -0.0193 | 0.8144 | 0.4626 | 0.0159 |

## §5 IV-incremental skill (per horizon)
| model | horizon | n | slope | t_slope | sign_acc | qlike_model | qlike_iv | qlike_gain_vs_iv |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Threshold-HAR | 1 | 7729 | 0.2875 | 24.5486 | 0.7370 | 0.3075 | 0.3570 | 0.0495 |
| Threshold-HAR | 5 | 7709 | 0.5241 | 24.2987 | 0.7049 | 0.2506 | 0.2620 | 0.0114 |
| Threshold-HAR | 10 | 7663 | 0.4788 | 14.1815 | 0.6569 | 0.2634 | 0.2546 | -0.0088 |
| Threshold-HAR | 22 | 7581 | 0.9109 | 31.0615 | 0.6142 | 0.3051 | 0.2750 | -0.0302 |
| Threshold-HAR | 42 | 7440 | 0.9255 | 51.6525 | 0.6147 | 0.3481 | 0.3178 | -0.0303 |

## §6 Conditional bias by IV-percentile bucket (h=22)
| model | horizon | iv_pctile_bucket | n | qlike | log_bias |
| --- | --- | --- | --- | --- | --- |
| Threshold-HAR | 22 | 0 | 1848 | 0.3035 | -0.1020 |
| Threshold-HAR | 22 | 1 | 1228 | 0.2547 | -0.0727 |
| Threshold-HAR | 22 | 2 | 1335 | 0.2538 | -0.0191 |
| Threshold-HAR | 22 | 3 | 1451 | 0.2563 | -0.1078 |
| Threshold-HAR | 22 | 4 | 1719 | 0.4241 | -0.0102 |

## §6 Post-shock calibration (h=22)
| model | horizon | bias_all | qlike_all | bias_postshock | qlike_postshock | n_postshock | trap_flag |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Threshold-HAR | 22 | -0.0630 | 0.3051 | -0.0458 | 0.3660 | 1410 |  |

## Per-ticker Tier-1 at h=22
| model | horizon | ticker | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Threshold-HAR | 22 | IBIT | 224 | 0.2056 | 0.6936 | 0.5168 | -0.1391 | 0.5045 | 0.2723 | 0.0034 |
| Threshold-HAR | 22 | KRE | 2059 | 0.3546 | 0.5901 | 0.4124 | -0.0497 | 0.9233 | 0.5867 | 0.0017 |
| Threshold-HAR | 22 | MSOS | 1181 | 0.3031 | 0.6717 | 0.5486 | 0.1986 | 0.6401 | 0.3031 | 0.0079 |
| Threshold-HAR | 22 | USO | 2059 | 0.2315 | 0.5509 | 0.4011 | 0.0031 | 0.8290 | 0.4745 | 0.0029 |
| Threshold-HAR | 22 | UVXY | 2058 | 0.3413 | 0.7448 | 0.5891 | -0.2841 | 0.8926 | 0.4674 | 0.0232 |

## Pooled by group
| model | group | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Threshold-HAR | crypto | 1172 | 0.2781 | 0.8198 | 0.6149 | -0.2715 | 0.6604 | 0.3507 | 0.0027 |
| Threshold-HAR | long_volatility_vix | 10320 | 0.3195 | 0.7604 | 0.6090 | -0.3059 | 0.8784 | 0.4667 | 0.0160 |
| Threshold-HAR | oil_and_energy | 10325 | 0.2626 | 0.6195 | 0.4617 | -0.0692 | 0.8407 | 0.4690 | 0.0023 |
| Threshold-HAR | us_cannabis | 5980 | 0.3174 | 0.6603 | 0.5179 | 0.0828 | 0.7360 | 0.4055 | 0.0053 |
| Threshold-HAR | us_cyclicals_sector | 10325 | 0.2904 | 0.5802 | 0.4181 | -0.0848 | 0.9197 | 0.5843 | 0.0012 |

---

## Model card (human-only fields — MODEL_PLAN §5)

**Model.** Threshold-HAR (CATALOG §3 model 29). Two-regime HARD-threshold (TAR-style) HAR-X:
separate log-OLS HAR-X coefficients fit per regime, `predict` routes each row to its regime's
coefficients. Pattern P2 (`_PerKeyModel` + `_AttachMixin`), per (ticker, horizon).

**Regime variable + threshold scheme.** Regime is the **expanding percentile of `vix`** (an
observable column in X, point-in-time). For each (ticker, date) the value is the fraction of that
ticker's at-or-before-date `vix` observations that are <= today's `vix` — an *expanding* (not
rolling) rank in [0,1], computed **once on the full series** from `inputs.parquet` and **joined by
(ticker, date)** via `_AttachMixin._derive` (mirrors `har_cj.py::_attach`, incl. the synthetic-X
fallback). It is never recomputed on the predict slice. HARD threshold `= 0.5` (median of the
expanding percentile), **frozen by spec** — no grid, no inner-CV, no OOS peeking:

    regime = HIGH if vix_epctile >= 0.5 else LOW

`post_shock` (targets.parquet, not in X) is deliberately NOT used, per CATALOG §4.

**Features / derived columns.** Base regressors (per regime): `HAR_FEATURES + IV_FEATURES` =
`log_rv_d, log_rv_w, log_rv_m, log_iv, iv_slope, skew_25d, vix, vix3m, vix_slope, vvix` (+
intercept), OLS on `log(target_var)`. Derived/joined: `vix_epctile` (expanding VIX percentile,
regime selector only — not a regressor).

**Per-regime fallback.** A regime with `< 40` train rows for a (ticker, horizon) falls back to the
pooled / all-regime HAR fit; the pooled fit also routes any predict row whose regime lacked a
usable fit. **hard_cases fallback count (full-history fit proxy): 0.** All 5 tickers x 5 horizons
fitted; both LOW (42,902) and HIGH (30,123) regimes exercised. Short-history tickers (IBIT, MSOS)
have fewer OOS dates but full horizon coverage; the monthly-refit walk-forward may have triggered
transient early-fold fallbacks not captured by the full-history proxy — none produced missing rows.

**Coverage.** hard_cases: all 5 tickers x 5 horizons present, 38,497 OOS rows (IBIT 1,247; MSOS
6,055; UVXY 10,395; KRE/USO 10,400 each — counts reflect listing history), span
2018-01-02 .. 2026-05-21. No tickers/horizons uncovered.

**Reproducibility.** Deterministic (pure OLS via `np.linalg.lstsq`); no stochastic component, no RNG
seed needed. Libraries: python 3.12.13, numpy 2.4.6, polars 1.41.1, scipy 1.17.1. Device: macOS
15.3.1 arm64 (Apple Silicon), CPU. Wall-time: hard_cases walk-forward 11.2s.

**Coverage / calibration warnings.** Stress universe: cov90 well below nominal for crypto (IBIT
0.66) and us_cannabis (MSOS 0.74) — interval calibration weak on the most extreme/short-history
names; long_volatility_vix (UVXY) cov90 0.88. Mild over-forecast (negative log_bias) for most
groups; us_cannabis slightly under-forecasts (+0.083).

