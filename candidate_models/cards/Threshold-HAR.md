# Threshold-HAR — Self Stats
_universe=`clean_core` · primary horizon h=22 · predictions=`execution/data/predictions/Threshold-HAR.parquet` · generated 2026-06-03T22:04:53Z_

_Self-only metrics — no leaderboard rank, no DM test, no MCS, no §9 status._
_Cross-model comparison is produced by the final `rv_eval.evaluator` pass._

## Tier-1 pooled by horizon (§3)
| model | horizon | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Threshold-HAR | 1 | 20800 | 0.2844 | 0.7475 | 0.5984 | -0.2471 | 0.8923 | 0.4911 | 0.0000 |
| Threshold-HAR | 5 | 20760 | 0.1839 | 0.5707 | 0.4428 | -0.1326 | 0.8954 | 0.5211 | 0.0002 |
| Threshold-HAR | 10 | 20710 | 0.2075 | 0.5700 | 0.4324 | -0.1157 | 0.9051 | 0.5391 | 0.0003 |
| Threshold-HAR | 22 | 20590 | 0.3508 | 0.6168 | 0.4527 | -0.1054 | 0.9119 | 0.5585 | 0.0008 |
| Threshold-HAR | 42 | 20390 | 0.4681 | 0.6916 | 0.4996 | -0.1045 | 0.9063 | 0.5550 | 0.0015 |

## §5 IV-incremental skill (per horizon)
| model | horizon | n | slope | t_slope | sign_acc | qlike_model | qlike_iv | qlike_gain_vs_iv |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Threshold-HAR | 1 | 20800 | 0.8234 | 51.5034 | 0.6900 | 0.2844 | 0.3273 | 0.0429 |
| Threshold-HAR | 5 | 20760 | 1.2254 | 58.2620 | 0.6385 | 0.1839 | 0.2079 | 0.0240 |
| Threshold-HAR | 10 | 20710 | 1.1476 | 36.3172 | 0.5802 | 0.2075 | 0.2187 | 0.0113 |
| Threshold-HAR | 22 | 20590 | 0.4812 | 16.3223 | 0.5116 | 0.3508 | 0.3397 | -0.0111 |
| Threshold-HAR | 42 | 20390 | 0.5064 | 19.5139 | 0.4927 | 0.4681 | 0.4701 | 0.0020 |

## §6 Conditional bias by IV-percentile bucket (h=22)
| model | horizon | iv_pctile_bucket | n | qlike | log_bias |
| --- | --- | --- | --- | --- | --- |
| Threshold-HAR | 22 | 0 | 5239 | 0.1923 | -0.1607 |
| Threshold-HAR | 22 | 1 | 3448 | 0.3539 | -0.1593 |
| Threshold-HAR | 22 | 2 | 3439 | 0.5216 | -0.1059 |
| Threshold-HAR | 22 | 3 | 3531 | 0.3880 | -0.0777 |
| Threshold-HAR | 22 | 4 | 4933 | 0.3712 | -0.0285 |

## §6 Post-shock calibration (h=22)
| model | horizon | bias_all | qlike_all | bias_postshock | qlike_postshock | n_postshock | trap_flag |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Threshold-HAR | 22 | -0.1054 | 0.3508 | -0.0586 | 0.3933 | 3914 |  |

## Per-ticker Tier-1 at h=22
| model | horizon | ticker | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Threshold-HAR | 22 | EEM | 2059 | 0.2512 | 0.5722 | 0.4268 | -0.0555 | 0.8985 | 0.5867 | 0.0007 |
| Threshold-HAR | 22 | GLD | 2059 | 0.1579 | 0.4837 | 0.3542 | -0.0262 | 0.8810 | 0.5129 | 0.0003 |
| Threshold-HAR | 22 | HYG | 2059 | 0.8505 | 0.8785 | 0.6954 | -0.4182 | 0.9475 | 0.5478 | 0.0002 |
| Threshold-HAR | 22 | IWM | 2059 | 0.3156 | 0.5545 | 0.3961 | 0.0150 | 0.9077 | 0.5532 | 0.0009 |
| Threshold-HAR | 22 | QQQ | 2059 | 0.3164 | 0.6278 | 0.4702 | -0.0801 | 0.8970 | 0.5590 | 0.0009 |
| Threshold-HAR | 22 | SPY | 2059 | 0.4560 | 0.6924 | 0.5203 | -0.0835 | 0.8936 | 0.5585 | 0.0007 |
| Threshold-HAR | 22 | TLT | 2059 | 0.2044 | 0.4763 | 0.3299 | -0.0246 | 0.9194 | 0.5134 | 0.0003 |
| Threshold-HAR | 22 | XLE | 2059 | 0.2829 | 0.5449 | 0.3956 | -0.0982 | 0.9296 | 0.5551 | 0.0015 |
| Threshold-HAR | 22 | XLF | 2059 | 0.3667 | 0.6233 | 0.4765 | -0.1728 | 0.9398 | 0.5993 | 0.0010 |
| Threshold-HAR | 22 | XLK | 2059 | 0.3066 | 0.6145 | 0.4620 | -0.1100 | 0.9053 | 0.5993 | 0.0011 |

## Pooled by group
| model | group | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Threshold-HAR | emerging_markets | 10325 | 0.2896 | 0.6811 | 0.5167 | -0.1324 | 0.8880 | 0.5298 | 0.0005 |
| Threshold-HAR | high_yield_credit | 10325 | 0.5875 | 0.8496 | 0.6727 | -0.3937 | 0.9307 | 0.5545 | 0.0001 |
| Threshold-HAR | oil_and_energy | 10325 | 0.2451 | 0.5527 | 0.4091 | -0.1148 | 0.9126 | 0.5366 | 0.0011 |
| Threshold-HAR | precious_metals | 10325 | 0.2182 | 0.6198 | 0.4671 | -0.0991 | 0.8722 | 0.4923 | 0.0003 |
| Threshold-HAR | us_cyclicals_sector | 10325 | 0.2872 | 0.6149 | 0.4730 | -0.1799 | 0.9333 | 0.5709 | 0.0007 |
| Threshold-HAR | us_large_cap_equity | 20650 | 0.3143 | 0.6619 | 0.5076 | -0.1213 | 0.8929 | 0.5260 | 0.0006 |
| Threshold-HAR | us_rates_and_ig_credit | 10325 | 0.2040 | 0.5533 | 0.4088 | -0.0796 | 0.8935 | 0.5039 | 0.0002 |
| Threshold-HAR | us_small_cap_equity | 10325 | 0.2590 | 0.5592 | 0.4108 | -0.0348 | 0.8993 | 0.5377 | 0.0007 |
| Threshold-HAR | us_technology_sector | 10325 | 0.2634 | 0.6222 | 0.4789 | -0.1359 | 0.9063 | 0.5504 | 0.0008 |

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
fallback). It is never recomputed on the predict slice. HARD threshold `= 0.5` (the median of the
expanding percentile), **frozen by spec** — no grid, no inner-CV, no OOS peeking:

    regime = HIGH if vix_epctile >= 0.5 else LOW

`post_shock` (targets.parquet, not in X) is deliberately NOT used, per CATALOG §4.

**Features / derived columns.** Base regressors (per regime): `HAR_FEATURES + IV_FEATURES` =
`log_rv_d, log_rv_w, log_rv_m, log_iv, iv_slope, skew_25d, vix, vix3m, vix_slope, vvix` (+
intercept), OLS on `log(target_var)`. Derived/joined: `vix_epctile` (expanding VIX percentile,
regime selector only — not a regressor).

**Per-regime fallback.** A regime with `< 40` train rows for a (ticker, horizon) falls back to the
pooled / all-regime HAR fit (computed on every train row); the pooled fit also routes any predict
row whose regime lacked a usable fit. **clean_core fallback count (full-history fit proxy): 0.**
All 10 tickers x 5 horizons fitted; both LOW (139,396) and HIGH (94,819) regimes exercised. Note:
the walk-forward refits monthly on expanding windows, so a few early/short-history folds may have
triggered transient fallbacks not captured by the full-history proxy; none produced missing rows.

**Coverage.** clean_core: all 10 tickers x 5 horizons present, 104,000 OOS rows,
span 2018-01-02 .. 2026-05-21. No tickers/horizons uncovered.

**Reproducibility.** Deterministic (pure OLS via `np.linalg.lstsq`); no stochastic component, no RNG
seed needed. Libraries: python 3.12.13, numpy 2.4.6, polars 1.41.1, scipy 1.17.1. Device: macOS
15.3.1 arm64 (Apple Silicon), CPU. Wall-time: clean_core walk-forward 25.8s (both universes upsert
one parquet).

**Coverage / calibration warnings.** cov90 in [0.892, 0.912] across horizons (slightly under
nominal 0.90 at h=1, on target by h>=10); cov50 ~0.49-0.56. Persistent mild negative log_bias
(over-forecast in log space) strongest in high_yield_credit (HYG, log_bias -0.42). §5 IV-gain
positive at h=1,5,10,42 but marginally negative at the primary h=22 (qlike_gain_vs_iv = -0.0111).
