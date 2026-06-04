# HAR-Act — Self Stats
_universe=`hard_cases` · primary horizon h=22 · predictions=`execution/data/predictions/HAR-Act.parquet` · generated 2026-06-03T21:51:51Z_

_Self-only metrics — no leaderboard rank, no DM test, no MCS, no §9 status._
_Cross-model comparison is produced by the final `rv_eval.evaluator` pass._

## Tier-1 pooled by horizon (§3)
| model | horizon | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-Act | 1 | 8196 | 0.3259 | 0.7504 | 0.5896 | -0.2434 | 0.9004 | 0.5271 | 0.0004 |
| HAR-Act | 5 | 8153 | 0.2665 | 0.6487 | 0.4949 | -0.1637 | 0.8930 | 0.5188 | 0.0019 |
| HAR-Act | 10 | 8108 | 0.2745 | 0.6520 | 0.4949 | -0.1513 | 0.8783 | 0.5074 | 0.0039 |
| HAR-Act | 22 | 8048 | 0.3002 | 0.6574 | 0.5031 | -0.1277 | 0.8668 | 0.4847 | 0.0084 |
| HAR-Act | 42 | 7905 | 0.3251 | 0.6650 | 0.5056 | -0.1059 | 0.8464 | 0.4767 | 0.0147 |

## §5 IV-incremental skill (per horizon)
| model | horizon | n | slope | t_slope | sign_acc | qlike_model | qlike_iv | qlike_gain_vs_iv |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-Act | 1 | 7906 | 0.9853 | 30.6746 | 0.7133 | 0.3187 | 0.3595 | 0.0408 |
| HAR-Act | 5 | 7863 | 0.7835 | 24.4302 | 0.6660 | 0.2630 | 0.2624 | -0.0006 |
| HAR-Act | 10 | 7838 | 0.8008 | 28.8534 | 0.6165 | 0.2724 | 0.2542 | -0.0182 |
| HAR-Act | 22 | 7778 | 0.8221 | 40.1305 | 0.5735 | 0.3004 | 0.2732 | -0.0272 |
| HAR-Act | 42 | 7657 | 0.9289 | 61.3186 | 0.5630 | 0.3304 | 0.3134 | -0.0170 |

## §6 Conditional bias by IV-percentile bucket (h=22)
| model | horizon | iv_pctile_bucket | n | qlike | log_bias |
| --- | --- | --- | --- | --- | --- |
| HAR-Act | 22 | 0 | 2078 | 0.3171 | -0.2342 |
| HAR-Act | 22 | 1 | 1264 | 0.2548 | -0.1400 |
| HAR-Act | 22 | 2 | 1355 | 0.2504 | -0.0837 |
| HAR-Act | 22 | 3 | 1460 | 0.2711 | -0.1027 |
| HAR-Act | 22 | 4 | 1727 | 0.3790 | -0.0146 |

## §6 Post-shock calibration (h=22)
| model | horizon | bias_all | qlike_all | bias_postshock | qlike_postshock | n_postshock | trap_flag |
| --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-Act | 22 | -0.1277 | 0.3002 | -0.1652 | 0.3184 | 1487 |  |

## Per-ticker Tier-1 at h=22
| model | horizon | ticker | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-Act | 22 | IBIT | 517 | 0.2140 | 0.7345 | 0.6156 | -0.4578 | 0.7311 | 0.4217 | 0.0038 |
| HAR-Act | 22 | KRE | 2087 | 0.3495 | 0.6060 | 0.4395 | -0.0964 | 0.9358 | 0.5716 | 0.0017 |
| HAR-Act | 22 | MSOS | 1270 | 0.2592 | 0.6304 | 0.4836 | 0.0509 | 0.8181 | 0.4606 | 0.0068 |
| HAR-Act | 22 | USO | 2087 | 0.2673 | 0.5932 | 0.4433 | -0.0031 | 0.8256 | 0.4384 | 0.0028 |
| HAR-Act | 22 | UVXY | 2087 | 0.3303 | 0.7564 | 0.6107 | -0.3104 | 0.9023 | 0.4744 | 0.0227 |

## Pooled by group
| model | group | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-Act | crypto | 2633 | 0.2950 | 0.8469 | 0.6895 | -0.5194 | 0.8488 | 0.4888 | 0.0026 |
| HAR-Act | long_volatility_vix | 10465 | 0.3128 | 0.7556 | 0.6094 | -0.2993 | 0.8952 | 0.4894 | 0.0154 |
| HAR-Act | oil_and_energy | 10465 | 0.2968 | 0.6475 | 0.4896 | -0.0639 | 0.8372 | 0.4515 | 0.0022 |
| HAR-Act | us_cannabis | 6382 | 0.2887 | 0.6324 | 0.4794 | -0.0197 | 0.8502 | 0.5047 | 0.0047 |
| HAR-Act | us_cyclicals_sector | 10465 | 0.2921 | 0.5917 | 0.4348 | -0.1077 | 0.9230 | 0.5712 | 0.0012 |

---

## Model card (human fields — MODEL_PLAN §5)

**Model:** `candidate_models/har_act.py:HARAct` · `name="HAR-Act"` · catalog model 17 (Track A, Pattern P1).
**Base:** `_AttachMixin` + `_LinearLogHAR` (per-(ticker, horizon) OLS of `log(target_var)`, lognormal quantiles via `_lognormal_quantiles`).

### Features used
`needs = HAR_FEATURES + ["log_vol_surprise", "log_txn_surprise", "overnight_share"]`
- `HAR_FEATURES = [log_rv_d, log_rv_w, log_rv_m]` — built by `rv_eval.features.build_features` (unchanged).

### Derived columns (`_derive` on the FULL series, joined by (ticker, date) via `_AttachMixin`)
All source columns live in `inputs.parquet` and pass through `build_features` untouched.
- **`log_vol_surprise` = log(volume) − log(rolling_mean(volume, 22).over(ticker))** — today's log volume minus the log of its trailing 22-day mean. Source: `volume`.
- **`log_txn_surprise` = log(transactions) − log(rolling_mean(transactions, 22).over(ticker))** — same for trade count. Source: `transactions` (cast Float64).
- **`overnight_share` = rv_overnight / total_rv when total_rv > 0 else null** — overnight variance share (gap risk). Source: `rv_overnight`, `total_rv`.

All catalog-named columns are present in `inputs.parquet` — no proxies needed.

### Leakage / rolling-feature handling
The 22-day activity means are built **once on the full `inputs.parquet` series** per ticker and **joined by (ticker, date)** through `_AttachMixin` — never recomputed on the one-month predict slice. Trailing windows include only at-or-before-date rows.

### Reproducibility
- Library versions: python 3.12.13, polars 1.41.1, numpy 2.4.6, scipy 1.17.1.
- Seed: none required — plain log-OLS, no stochastic component.
- Device: macOS-15.3.1-arm64 (Apple Silicon, arm64), CPU only.
- Wall-clock (walk-forward): clean_core 9.0s, hard_cases 4.4s.
- OOS rows: hard_cases 40,810 (clean_core 105,450; total file 146,260). OOS span 2018-01-02 → 2026-05-22.

### Coverage
Full coverage on this universe: all 5 hard_cases tickers (UVXY, MSOS, IBIT, USO, KRE) × all 5 horizons (1, 5, 10, 22, 42). No tickers/horizons dropped.

### Coverage warnings
On the hard-cases universe cov90 runs a touch light for some energy/cannabis names (e.g. oil_and_energy 0.837, us_cannabis 0.850) while remaining near nominal elsewhere; pooled log_bias is mildly negative. Plain-log-OLS calibration traits, left for the comparison pass; no per-model tuning applied.
