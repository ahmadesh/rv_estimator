# HAR-Range — Model Card

## Identity
- Model number (from ITER2_MODEL_CATALOG.md §3): 16 (Track A — new linear feature blocks)
- Class: `candidate_models.har_range:HARRange`
- Tier: Modern HAR (linear-log HAR + derived trailing-window join, Pattern P1)
- Implemented by: iter-2 swarm worker (model 16), 2026-06-03

## Configuration
- Features used (by name): `HAR_FEATURES = [log_rv_d, log_rv_w, log_rv_m]` (pre-baked in `features.py`)
  plus four derived range features `[log_park_d, log_park_w, log_gk_d, log_gk_w]`.
- Derived feature formulas (built once on the full series in `_range_panel`, joined by (ticker,date)
  via `_AttachMixin`; trailing windows include today → point-in-time, no leakage):
  - `log_park_d = log( clip(rolling_mean(parkinson, 1).over(ticker), lower=1e-12) )`
  - `log_park_w = log( clip(rolling_mean(parkinson, 5).over(ticker), lower=1e-12) )`
  - `log_gk_d   = log( clip(rolling_mean(gk, 1).over(ticker),        lower=1e-12) )`
  - `log_gk_w   = log( clip(rolling_mean(gk, 5).over(ticker),        lower=1e-12) )`
- Source OHLC/range columns: `parkinson` (Parkinson high-low estimator) and `gk` (Garman-Klass
  open-high-low-close estimator) are precomputed in `inputs.parquet` (per `setup/measurement.py`);
  no raw OHLC derivation was needed. `rs` (Rogers-Satchell) is present in inputs but not used by
  this model per the catalog §3 spec for model 16. Both estimators can be exactly 0 (15 zero rows
  each in inputs) → floored at 1e-12 before log, matching `features.py` / `har_cj.py`.
- Hyperparameters: none (plain per-(ticker,horizon) log-OLS via inherited `_LinearLogHAR`).
- HP selection: N/A (no tunable hyperparameters; nothing to leak).
- Library versions: python 3.12.13, polars 1.41.1, numpy 2.4.6, scipy 1.17.1.
- Random seed: N/A (deterministic OLS; seed=0 used only in the synthetic smoke test).

## Training
- Universes run: clean_core, hard_cases
- Wall-clock time: clean_core ≈ 9.8s, hard_cases ≈ 4.7s (walk-forward, monthly refit, expanding window)
- Device: cpu (Apple Silicon arm64, macOS 15.3.1)
- OOS rows: 105,450 (clean_core) + 40,810 (hard_cases) = 146,260 total; span 2018-01-02 → 2026-05-22.
- Coverage: all 10 clean_core + 5 hard_cases tickers and all 5 horizons (1,5,10,22,42) covered; no
  tickers/horizons dropped.
- Convergence notes: none — OLS via `np.linalg.lstsq`, no failures.
- Coverage warnings: clean_core 90% interval coverage is near nominal (cov90 ≈ 0.89–0.92 across
  horizons). Hard_cases shows the expected interval under-coverage on the extreme-tail names
  (cov90 falls to ≈ 0.34–0.46 at the short horizons for UVXY/MSOS), consistent with the lognormal
  parametric interval being too thin for those regimes — flagged for the comparison pass, not tuned.

---

# HAR-Range — Self Stats
_universe=`clean_core` · primary horizon h=22 · predictions=`execution/data/predictions/HAR-Range.parquet` · generated 2026-06-03T21:47:23Z_

_Self-only metrics — no leaderboard rank, no DM test, no MCS, no §9 status._
_Cross-model comparison is produced by the final `rv_eval.evaluator` pass._

## Tier-1 pooled by horizon (§3)
| model | horizon | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-Range | 1 | 21080 | 0.3090 | 0.7569 | 0.6020 | -0.2230 | 0.8928 | 0.5035 | 0.0000 |
| HAR-Range | 5 | 21040 | 0.2048 | 0.5952 | 0.4619 | -0.1254 | 0.9006 | 0.5341 | 0.0002 |
| HAR-Range | 10 | 20990 | 0.2237 | 0.5974 | 0.4575 | -0.1217 | 0.9077 | 0.5533 | 0.0003 |
| HAR-Range | 22 | 20870 | 0.3332 | 0.6474 | 0.4856 | -0.1413 | 0.9150 | 0.5712 | 0.0008 |
| HAR-Range | 42 | 20670 | 0.4370 | 0.7180 | 0.5237 | -0.1619 | 0.9214 | 0.5865 | 0.0015 |

## §5 IV-incremental skill (per horizon)
| model | horizon | n | slope | t_slope | sign_acc | qlike_model | qlike_iv | qlike_gain_vs_iv |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-Range | 1 | 20820 | 1.4637 | 49.0190 | 0.6621 | 0.3089 | 0.3276 | 0.0188 |
| HAR-Range | 5 | 20780 | 0.9380 | 34.8488 | 0.6135 | 0.2051 | 0.2079 | 0.0028 |
| HAR-Range | 10 | 20730 | 0.5480 | 18.6364 | 0.5652 | 0.2246 | 0.2187 | -0.0059 |
| HAR-Range | 22 | 20610 | 0.2135 | 6.9585 | 0.5205 | 0.3350 | 0.3396 | 0.0046 |
| HAR-Range | 42 | 20410 | 0.3565 | 11.8674 | 0.5066 | 0.4408 | 0.4697 | 0.0289 |

## §6 Conditional bias by IV-percentile bucket (h=22)
| model | horizon | iv_pctile_bucket | n | qlike | log_bias |
| --- | --- | --- | --- | --- | --- |
| HAR-Range | 22 | 0 | 5500 | 0.1820 | -0.1898 |
| HAR-Range | 22 | 1 | 3449 | 0.3316 | -0.1757 |
| HAR-Range | 22 | 2 | 3439 | 0.4673 | -0.1366 |
| HAR-Range | 22 | 3 | 3533 | 0.3834 | -0.1087 |
| HAR-Range | 22 | 4 | 4949 | 0.3732 | -0.0898 |

## §6 Post-shock calibration (h=22)
| model | horizon | bias_all | qlike_all | bias_postshock | qlike_postshock | n_postshock | trap_flag |
| --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-Range | 22 | -0.1413 | 0.3332 | -0.2101 | 0.3884 | 3986 |  |

## Per-ticker Tier-1 at h=22
| model | horizon | ticker | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-Range | 22 | EEM | 2087 | 0.2329 | 0.6086 | 0.4766 | -0.2101 | 0.9569 | 0.6881 | 0.0007 |
| HAR-Range | 22 | GLD | 2087 | 0.1774 | 0.5263 | 0.4069 | -0.0916 | 0.8740 | 0.4926 | 0.0004 |
| HAR-Range | 22 | HYG | 2087 | 0.7032 | 0.9870 | 0.8081 | -0.6180 | 0.9698 | 0.6881 | 0.0002 |
| HAR-Range | 22 | IWM | 2087 | 0.2908 | 0.5732 | 0.4245 | -0.0378 | 0.9003 | 0.5122 | 0.0010 |
| HAR-Range | 22 | QQQ | 2087 | 0.2952 | 0.6102 | 0.4638 | -0.0609 | 0.9296 | 0.6373 | 0.0008 |
| HAR-Range | 22 | SPY | 2087 | 0.4431 | 0.7085 | 0.5459 | -0.0939 | 0.8898 | 0.5089 | 0.0007 |
| HAR-Range | 22 | TLT | 2087 | 0.2242 | 0.5065 | 0.3611 | -0.0046 | 0.8884 | 0.4988 | 0.0003 |
| HAR-Range | 22 | XLE | 2087 | 0.2888 | 0.5472 | 0.3894 | -0.0428 | 0.9066 | 0.5750 | 0.0015 |
| HAR-Range | 22 | XLF | 2087 | 0.3764 | 0.6658 | 0.5252 | -0.2132 | 0.9286 | 0.5525 | 0.0011 |
| HAR-Range | 22 | XLK | 2087 | 0.2994 | 0.6058 | 0.4545 | -0.0397 | 0.9066 | 0.5587 | 0.0011 |

## Pooled by group
| model | group | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-Range | emerging_markets | 10465 | 0.2838 | 0.6980 | 0.5455 | -0.2100 | 0.9295 | 0.6064 | 0.0005 |
| HAR-Range | high_yield_credit | 10465 | 0.5274 | 0.9195 | 0.7411 | -0.5062 | 0.9549 | 0.6441 | 0.0001 |
| HAR-Range | oil_and_energy | 10465 | 0.2594 | 0.5597 | 0.4089 | -0.0690 | 0.9007 | 0.5443 | 0.0011 |
| HAR-Range | precious_metals | 10465 | 0.2344 | 0.6510 | 0.5032 | -0.1585 | 0.8748 | 0.4769 | 0.0003 |
| HAR-Range | us_cyclicals_sector | 10465 | 0.3137 | 0.6520 | 0.5066 | -0.2031 | 0.9259 | 0.5645 | 0.0008 |
| HAR-Range | us_large_cap_equity | 20930 | 0.3203 | 0.6685 | 0.5128 | -0.1024 | 0.9025 | 0.5495 | 0.0006 |
| HAR-Range | us_rates_and_ig_credit | 10465 | 0.2213 | 0.5682 | 0.4219 | -0.0512 | 0.8872 | 0.5077 | 0.0002 |
| HAR-Range | us_small_cap_equity | 10465 | 0.2583 | 0.5820 | 0.4350 | -0.0641 | 0.8945 | 0.5163 | 0.0007 |
| HAR-Range | us_technology_sector | 10465 | 0.2715 | 0.6210 | 0.4740 | -0.0800 | 0.9019 | 0.5363 | 0.0008 |
