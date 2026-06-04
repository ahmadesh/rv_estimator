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
  no raw OHLC derivation was needed. `rs` (Rogers-Satchell) is present but unused per the model-16
  spec. Both estimators can be exactly 0 → floored at 1e-12 before log.
- Hyperparameters: none (plain per-(ticker,horizon) log-OLS via inherited `_LinearLogHAR`).
- HP selection: N/A (no tunable hyperparameters; nothing to leak).
- Library versions: python 3.12.13, polars 1.41.1, numpy 2.4.6, scipy 1.17.1.
- Random seed: N/A (deterministic OLS; seed=0 used only in the synthetic smoke test).

## Training
- Universes run: clean_core, hard_cases
- Wall-clock time: clean_core ≈ 9.8s, hard_cases ≈ 4.7s (walk-forward, monthly refit, expanding window)
- Device: cpu (Apple Silicon arm64, macOS 15.3.1)
- OOS rows: 40,810 (hard_cases) of 146,260 total; span 2018-01-02 → 2026-05-22.
- Coverage: all 5 hard_cases tickers (UVXY, MSOS, IBIT, USO, KRE) and all 5 horizons covered.
- Convergence notes: none — OLS via `np.linalg.lstsq`, no failures.
- Coverage warnings: 90% interval coverage is materially below nominal on the extreme-tail names
  (cov90 ≈ 0.34–0.46 at short horizons; e.g. UVXY/MSOS), the expected lognormal-interval
  under-coverage in fat-tailed regimes. Point QLIKE at h=22 ≈ 0.31. Flagged for the comparison
  pass; not tuned (no hyperparameters).

---

# HAR-Range — Self Stats
_universe=`hard_cases` · primary horizon h=22 · predictions=`execution/data/predictions/HAR-Range.parquet` · generated 2026-06-03T21:47:23Z_

_Self-only metrics — no leaderboard rank, no DM test, no MCS, no §9 status._
_Cross-model comparison is produced by the final `rv_eval.evaluator` pass._

## Tier-1 pooled by horizon (§3)
| model | horizon | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-Range | 1 | 8196 | 0.3332 | 0.7503 | 0.5881 | -0.2384 | 0.9009 | 0.5306 | 0.0004 |
| HAR-Range | 5 | 8153 | 0.2715 | 0.6485 | 0.4939 | -0.1521 | 0.8911 | 0.5151 | 0.0020 |
| HAR-Range | 10 | 8108 | 0.2800 | 0.6495 | 0.4901 | -0.1384 | 0.8790 | 0.5133 | 0.0040 |
| HAR-Range | 22 | 8048 | 0.3068 | 0.6551 | 0.4963 | -0.1155 | 0.8685 | 0.4985 | 0.0084 |
| HAR-Range | 42 | 7905 | 0.3387 | 0.6660 | 0.5037 | -0.0948 | 0.8443 | 0.4781 | 0.0148 |

## §5 IV-incremental skill (per horizon)
| model | horizon | n | slope | t_slope | sign_acc | qlike_model | qlike_iv | qlike_gain_vs_iv |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-Range | 1 | 7906 | 1.1020 | 29.5840 | 0.7193 | 0.3264 | 0.3595 | 0.0331 |
| HAR-Range | 5 | 7863 | 0.7206 | 21.8527 | 0.6696 | 0.2673 | 0.2624 | -0.0049 |
| HAR-Range | 10 | 7838 | 0.7356 | 26.2678 | 0.6244 | 0.2782 | 0.2542 | -0.0240 |
| HAR-Range | 22 | 7778 | 0.7995 | 38.7003 | 0.5778 | 0.3076 | 0.2732 | -0.0344 |
| HAR-Range | 42 | 7657 | 0.9117 | 59.5379 | 0.5697 | 0.3445 | 0.3134 | -0.0311 |

## §6 Conditional bias by IV-percentile bucket (h=22)
| model | horizon | iv_pctile_bucket | n | qlike | log_bias |
| --- | --- | --- | --- | --- | --- |
| HAR-Range | 22 | 0 | 2078 | 0.3186 | -0.2274 |
| HAR-Range | 22 | 1 | 1264 | 0.2554 | -0.1302 |
| HAR-Range | 22 | 2 | 1355 | 0.2513 | -0.0784 |
| HAR-Range | 22 | 3 | 1460 | 0.2755 | -0.0945 |
| HAR-Range | 22 | 4 | 1727 | 0.4047 | -0.0000 |

## §6 Post-shock calibration (h=22)
| model | horizon | bias_all | qlike_all | bias_postshock | qlike_postshock | n_postshock | trap_flag |
| --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-Range | 22 | -0.1155 | 0.3068 | -0.1411 | 0.3359 | 1487 |  |

## Per-ticker Tier-1 at h=22
| model | horizon | ticker | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-Range | 22 | IBIT | 517 | 0.1925 | 0.6738 | 0.5380 | -0.3568 | 0.7505 | 0.4855 | 0.0034 |
| HAR-Range | 22 | KRE | 2087 | 0.3543 | 0.6045 | 0.4333 | -0.0896 | 0.9358 | 0.5817 | 0.0017 |
| HAR-Range | 22 | MSOS | 1270 | 0.2659 | 0.6359 | 0.4898 | 0.0498 | 0.8213 | 0.4646 | 0.0069 |
| HAR-Range | 22 | USO | 2087 | 0.2849 | 0.5974 | 0.4396 | 0.0138 | 0.8189 | 0.4509 | 0.0029 |
| HAR-Range | 22 | UVXY | 2087 | 0.3345 | 0.7576 | 0.6096 | -0.3116 | 0.9090 | 0.4868 | 0.0228 |

## Pooled by group
| model | group | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-Range | crypto | 2633 | 0.2804 | 0.8139 | 0.6505 | -0.4561 | 0.8412 | 0.5006 | 0.0025 |
| HAR-Range | long_volatility_vix | 10465 | 0.3182 | 0.7565 | 0.6093 | -0.2963 | 0.8977 | 0.4965 | 0.0155 |
| HAR-Range | oil_and_energy | 10465 | 0.3122 | 0.6503 | 0.4874 | -0.0476 | 0.8359 | 0.4525 | 0.0022 |
| HAR-Range | us_cannabis | 6382 | 0.3005 | 0.6361 | 0.4810 | -0.0168 | 0.8505 | 0.5003 | 0.0048 |
| HAR-Range | us_cyclicals_sector | 10465 | 0.2970 | 0.5931 | 0.4336 | -0.1040 | 0.9226 | 0.5791 | 0.0012 |
