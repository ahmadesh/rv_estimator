# HAR-Act — Self Stats
_universe=`clean_core` · primary horizon h=22 · predictions=`execution/data/predictions/HAR-Act.parquet` · generated 2026-06-03T21:51:51Z_

_Self-only metrics — no leaderboard rank, no DM test, no MCS, no §9 status._
_Cross-model comparison is produced by the final `rv_eval.evaluator` pass._

## Tier-1 pooled by horizon (§3)
| model | horizon | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-Act | 1 | 21080 | 0.3034 | 0.7487 | 0.5949 | -0.2135 | 0.8944 | 0.5032 | 0.0000 |
| HAR-Act | 5 | 21040 | 0.2033 | 0.5912 | 0.4581 | -0.1228 | 0.9002 | 0.5365 | 0.0002 |
| HAR-Act | 10 | 20990 | 0.2219 | 0.5953 | 0.4572 | -0.1222 | 0.9075 | 0.5574 | 0.0003 |
| HAR-Act | 22 | 20870 | 0.3268 | 0.6455 | 0.4873 | -0.1430 | 0.9155 | 0.5693 | 0.0008 |
| HAR-Act | 42 | 20670 | 0.4353 | 0.7192 | 0.5284 | -0.1685 | 0.9216 | 0.5870 | 0.0015 |

## §5 IV-incremental skill (per horizon)
| model | horizon | n | slope | t_slope | sign_acc | qlike_model | qlike_iv | qlike_gain_vs_iv |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-Act | 1 | 20820 | 1.2096 | 48.7194 | 0.6687 | 0.3033 | 0.3276 | 0.0243 |
| HAR-Act | 5 | 20780 | 0.9716 | 42.2651 | 0.6167 | 0.2036 | 0.2079 | 0.0043 |
| HAR-Act | 10 | 20730 | 0.6815 | 25.9543 | 0.5700 | 0.2227 | 0.2187 | -0.0040 |
| HAR-Act | 22 | 20610 | 0.2954 | 9.8449 | 0.5237 | 0.3284 | 0.3396 | 0.0111 |
| HAR-Act | 42 | 20410 | 0.3096 | 10.8709 | 0.5012 | 0.4391 | 0.4697 | 0.0306 |

## §6 Conditional bias by IV-percentile bucket (h=22)
| model | horizon | iv_pctile_bucket | n | qlike | log_bias |
| --- | --- | --- | --- | --- | --- |
| HAR-Act | 22 | 0 | 5500 | 0.1813 | -0.1902 |
| HAR-Act | 22 | 1 | 3449 | 0.3102 | -0.1805 |
| HAR-Act | 22 | 2 | 3439 | 0.4716 | -0.1419 |
| HAR-Act | 22 | 3 | 3533 | 0.3772 | -0.1125 |
| HAR-Act | 22 | 4 | 4949 | 0.3635 | -0.0871 |

## §6 Post-shock calibration (h=22)
| model | horizon | bias_all | qlike_all | bias_postshock | qlike_postshock | n_postshock | trap_flag |
| --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-Act | 22 | -0.1430 | 0.3268 | -0.2201 | 0.3788 | 3986 |  |

## Per-ticker Tier-1 at h=22
| model | horizon | ticker | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-Act | 22 | EEM | 2087 | 0.2326 | 0.6295 | 0.5042 | -0.2498 | 0.9559 | 0.6608 | 0.0007 |
| HAR-Act | 22 | GLD | 2087 | 0.1769 | 0.5315 | 0.4125 | -0.1003 | 0.8716 | 0.4897 | 0.0004 |
| HAR-Act | 22 | HYG | 2087 | 0.6493 | 0.9635 | 0.7966 | -0.6006 | 0.9746 | 0.6986 | 0.0002 |
| HAR-Act | 22 | IWM | 2087 | 0.2922 | 0.5739 | 0.4256 | -0.0398 | 0.8999 | 0.5165 | 0.0010 |
| HAR-Act | 22 | QQQ | 2087 | 0.2933 | 0.6110 | 0.4664 | -0.0615 | 0.9291 | 0.6406 | 0.0008 |
| HAR-Act | 22 | SPY | 2087 | 0.4427 | 0.7093 | 0.5475 | -0.0986 | 0.8869 | 0.5026 | 0.0007 |
| HAR-Act | 22 | TLT | 2087 | 0.2107 | 0.5062 | 0.3659 | -0.0188 | 0.8893 | 0.4959 | 0.0003 |
| HAR-Act | 22 | XLE | 2087 | 0.2837 | 0.5442 | 0.3868 | -0.0442 | 0.9138 | 0.5783 | 0.0015 |
| HAR-Act | 22 | XLF | 2087 | 0.3813 | 0.6625 | 0.5201 | -0.2018 | 0.9305 | 0.5529 | 0.0011 |
| HAR-Act | 22 | XLK | 2087 | 0.3050 | 0.6021 | 0.4477 | -0.0149 | 0.9037 | 0.5568 | 0.0011 |

## Pooled by group
| model | group | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-Act | emerging_markets | 10465 | 0.2865 | 0.7169 | 0.5685 | -0.2508 | 0.9323 | 0.5973 | 0.0005 |
| HAR-Act | high_yield_credit | 10465 | 0.5110 | 0.9033 | 0.7313 | -0.4928 | 0.9584 | 0.6569 | 0.0001 |
| HAR-Act | oil_and_energy | 10465 | 0.2549 | 0.5550 | 0.4050 | -0.0672 | 0.9036 | 0.5490 | 0.0011 |
| HAR-Act | precious_metals | 10465 | 0.2331 | 0.6541 | 0.5069 | -0.1666 | 0.8728 | 0.4790 | 0.0003 |
| HAR-Act | us_cyclicals_sector | 10465 | 0.3132 | 0.6461 | 0.5000 | -0.1904 | 0.9263 | 0.5658 | 0.0008 |
| HAR-Act | us_large_cap_equity | 20930 | 0.3156 | 0.6620 | 0.5086 | -0.0985 | 0.9024 | 0.5498 | 0.0006 |
| HAR-Act | us_rates_and_ig_credit | 10465 | 0.2140 | 0.5702 | 0.4260 | -0.0658 | 0.8881 | 0.5068 | 0.0002 |
| HAR-Act | us_small_cap_equity | 10465 | 0.2584 | 0.5787 | 0.4319 | -0.0618 | 0.8932 | 0.5147 | 0.0007 |
| HAR-Act | us_technology_sector | 10465 | 0.2742 | 0.6128 | 0.4650 | -0.0476 | 0.8983 | 0.5359 | 0.0008 |

---

## Model card (human fields — MODEL_PLAN §5)

**Model:** `candidate_models/har_act.py:HARAct` · `name="HAR-Act"` · catalog model 17 (Track A, Pattern P1).
**Base:** `_AttachMixin` + `_LinearLogHAR` (per-(ticker, horizon) OLS of `log(target_var)`, lognormal quantiles via `_lognormal_quantiles`).

### Features used
`needs = HAR_FEATURES + ["log_vol_surprise", "log_txn_surprise", "overnight_share"]`
- `HAR_FEATURES = [log_rv_d, log_rv_w, log_rv_m]` — built by `rv_eval.features.build_features` (unchanged).

### Derived columns (`_derive` on the FULL series, joined by (ticker, date) via `_AttachMixin`)
All source columns live in `inputs.parquet` and pass through `build_features` untouched.
- **`log_vol_surprise` = log(volume) − log(rolling_mean(volume, 22).over(ticker))** — today's log volume minus the log of its trailing 22-day mean (an activity surprise / abnormal-volume signal). Source: `volume` (min 100 in inputs, always > 0). Window is trailing (includes today); leading 21 rows per ticker are null and dropped by the base fit's `drop_nulls`.
- **`log_txn_surprise` = log(transactions) − log(rolling_mean(transactions, 22).over(ticker))** — same construction for trade count. Source: `transactions` (Int64, min 1 in inputs; cast to Float64 before the rolling mean / log).
- **`overnight_share` = rv_overnight / total_rv when total_rv > 0 else null** — fraction of daily variance accrued overnight (gap risk). Source: `rv_overnight`, `total_rv`. Guarded: null where `total_rv ≤ 0` (4 such rows in inputs) or `rv_overnight` is null (15 rows); null rows are dropped by the base fit.

All catalog-named columns (`volume`, `transactions`, `rv_overnight`, `total_rv`) are present in `inputs.parquet` — no proxies needed.

### Leakage / rolling-feature handling
The 22-day activity means are the leakage risk. They are built **once on the full `inputs.parquet` series** per ticker and **joined by (ticker, date)** through `_AttachMixin` — never recomputed on the one-month predict slice. Trailing windows include only at-or-before-date rows. Synthetic-X fallback (`_derive(X)`) is exercised by the smoke test.

### Reproducibility
- Library versions: python 3.12.13, polars 1.41.1, numpy 2.4.6, scipy 1.17.1.
- Seed: none required — plain log-OLS, no stochastic component (test uses `np.random.default_rng(0)` only for the synthetic panel).
- Device: macOS-15.3.1-arm64 (Apple Silicon, arm64), CPU only.
- Wall-clock (walk-forward): clean_core 9.0s, hard_cases 4.4s.
- OOS rows: clean_core 105,450; hard_cases 40,810; total 146,260. OOS span 2018-01-02 → 2026-05-22.

### Coverage
Full coverage on this universe: all 10 clean_core tickers × all 5 horizons (1, 5, 10, 22, 42). No tickers/horizons dropped.

### Coverage warnings
cov90 runs slightly rich for several names (e.g. HYG 0.975, EEM 0.956) and the pooled log_bias is negative across horizons (−0.12 to −0.21), i.e. the level forecast is somewhat low / intervals wide — a known plain-log-OLS calibration trait, left for the comparison pass; no per-model tuning applied.
