# HAR-X — Model Card

## Identity
- Model number (from MODEL_PLAN.md): 3
- Class: `rv_eval.model_contract:HARX`
- model `name`: `HAR-X`
- Tier: Baseline (reference benchmark; modern-HAR extension with IV/VIX exogenous regressors)
- Implemented by: pre-coded in `rv_eval/model_contract.py` (no implementation work). Run 2026-05-31 by swarm worker.

## Configuration
- Features used (by name): `HAR_FEATURES + IV_FEATURES` =
  - HAR: `log_rv_d`, `log_rv_w`, `log_rv_m`
  - IV/VIX: `log_iv`, `iv_slope`, `skew_25d`, `vix`, `vix3m`, `vix_slope`, `vvix`
  - (10 regressors + intercept)
- Hyperparameters: none (free). Per-(ticker, horizon) OLS of `log(target_var)` on the regressors above (`_LinearLogHAR`). `min_obs=100`. Lognormal-mean correction `exp(mu + 0.5*s^2)` for `rv_hat`; `sigma` from in-sample log-residual std.
- HP selection: N/A (model 3 has no free hyperparameters).
- Library versions: python 3.12.13, numpy 2.4.6, scipy 1.17.1, polars 1.41.1.
- Random seed: N/A (deterministic OLS via `numpy.linalg.lstsq`).

## Training
- Universes run: clean_core, hard_cases
- Walk-forward: purged + embargoed monthly-refit rolling-origin (expanding window), OOS_START=2018-01-01, span 2018-01-02 → 2026-05-21.
- Wall-clock time: clean_core 9.4s, hard_cases 4.4s (per `/usr/bin/time -p real`).
- Device: cpu (Apple Silicon, macOS-15.3.1-arm64).
- Prediction parquet: `execution/data/predictions/HAR-X.parquet`, 142,497 rows total (104,000 clean_core + 38,497 hard_cases), all rows `model="HAR-X"`.
- Convergence notes / per-ticker warnings:
  - No OLS convergence failures; every (ticker, horizon) with ≥100 obs fit.
  - **Coverage is full for all 10 clean_core tickers** (2,080 OOS rows × 5 horizons each).
  - Rows are dropped (never imputed) wherever an IV feature is null — see hard_cases card for IBIT/MSOS; clean_core tickers lose only ~27–30 OOS warmup rows per ticker (HAR rolling-window + IV NaN at the OOS boundary).

# HAR-X — Self Stats
_universe=`clean_core` · primary horizon h=22 · predictions=`execution/data/predictions/HAR-X.parquet` · generated 2026-06-01T03:03:07Z_

_Self-only metrics — no leaderboard rank, no DM test, no MCS, no §9 status._
_Cross-model comparison is produced by the final `rv_eval.evaluator` pass._

## Tier-1 pooled by horizon (§3)
| model | horizon | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-X | 1 | 20800 | 0.2818 | 0.7429 | 0.5939 | -0.2429 | 0.8927 | 0.4933 | 0.0000 |
| HAR-X | 5 | 20760 | 0.1795 | 0.5613 | 0.4359 | -0.1263 | 0.8982 | 0.5221 | 0.0002 |
| HAR-X | 10 | 20710 | 0.2020 | 0.5587 | 0.4253 | -0.1094 | 0.9097 | 0.5397 | 0.0003 |
| HAR-X | 22 | 20590 | 0.3386 | 0.6050 | 0.4464 | -0.1029 | 0.9175 | 0.5648 | 0.0007 |
| HAR-X | 42 | 20390 | 0.4587 | 0.6775 | 0.4900 | -0.1036 | 0.9154 | 0.5696 | 0.0015 |

## §5 IV-incremental skill (per horizon)
| model | horizon | n | slope | t_slope | sign_acc | qlike_model | qlike_iv | qlike_gain_vs_iv |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-X | 1 | 20800 | 0.6430 | 49.2039 | 0.7030 | 0.2818 | 0.3273 | 0.0455 |
| HAR-X | 5 | 20760 | 0.9086 | 55.9563 | 0.6558 | 0.1795 | 0.2079 | 0.0283 |
| HAR-X | 10 | 20710 | 0.9404 | 36.7620 | 0.5990 | 0.2020 | 0.2187 | 0.0167 |
| HAR-X | 22 | 20590 | 0.5397 | 15.3806 | 0.5186 | 0.3386 | 0.3397 | 0.0012 |
| HAR-X | 42 | 20390 | 0.4874 | 15.8257 | 0.5028 | 0.4587 | 0.4701 | 0.0114 |

## §6 Conditional bias by IV-percentile bucket (h=22)
| model | horizon | iv_pctile_bucket | n | qlike | log_bias |
| --- | --- | --- | --- | --- | --- |
| HAR-X | 22 | 0 | 5239 | 0.1830 | -0.1391 |
| HAR-X | 22 | 1 | 3448 | 0.3485 | -0.1559 |
| HAR-X | 22 | 2 | 3439 | 0.5088 | -0.1146 |
| HAR-X | 22 | 3 | 3531 | 0.3670 | -0.0851 |
| HAR-X | 22 | 4 | 4933 | 0.3578 | -0.0320 |

## §6 Post-shock calibration (h=22)
| model | horizon | bias_all | qlike_all | bias_postshock | qlike_postshock | n_postshock | trap_flag |
| --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-X | 22 | -0.1029 | 0.3386 | -0.0588 | 0.3771 | 3914 |  |

## Per-ticker Tier-1 at h=22
| model | horizon | ticker | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-X | 22 | EEM | 2059 | 0.2467 | 0.5759 | 0.4324 | -0.0676 | 0.9004 | 0.5755 | 0.0007 |
| HAR-X | 22 | GLD | 2059 | 0.1417 | 0.4624 | 0.3389 | -0.0216 | 0.8917 | 0.5372 | 0.0003 |
| HAR-X | 22 | HYG | 2059 | 0.8198 | 0.8306 | 0.6505 | -0.3668 | 0.9582 | 0.5969 | 0.0002 |
| HAR-X | 22 | IWM | 2059 | 0.3000 | 0.5438 | 0.3881 | 0.0144 | 0.9126 | 0.5551 | 0.0009 |
| HAR-X | 22 | QQQ | 2059 | 0.2938 | 0.6131 | 0.4630 | -0.0765 | 0.8980 | 0.5634 | 0.0008 |
| HAR-X | 22 | SPY | 2059 | 0.4459 | 0.6864 | 0.5170 | -0.0827 | 0.9024 | 0.5556 | 0.0007 |
| HAR-X | 22 | TLT | 2059 | 0.2061 | 0.4786 | 0.3332 | -0.0310 | 0.9213 | 0.4968 | 0.0003 |
| HAR-X | 22 | XLE | 2059 | 0.2744 | 0.5400 | 0.3914 | -0.0957 | 0.9330 | 0.5580 | 0.0014 |
| HAR-X | 22 | XLF | 2059 | 0.3658 | 0.6297 | 0.4900 | -0.1918 | 0.9451 | 0.6173 | 0.0010 |
| HAR-X | 22 | XLK | 2059 | 0.2915 | 0.6040 | 0.4595 | -0.1095 | 0.9121 | 0.5925 | 0.0011 |

## Pooled by group
| model | group | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-X | emerging_markets | 10325 | 0.2856 | 0.6781 | 0.5140 | -0.1273 | 0.8920 | 0.5298 | 0.0005 |
| HAR-X | high_yield_credit | 10325 | 0.5742 | 0.8055 | 0.6322 | -0.3447 | 0.9403 | 0.5833 | 0.0001 |
| HAR-X | oil_and_energy | 10325 | 0.2406 | 0.5493 | 0.4066 | -0.1151 | 0.9142 | 0.5396 | 0.0011 |
| HAR-X | precious_metals | 10325 | 0.2051 | 0.6067 | 0.4558 | -0.0984 | 0.8838 | 0.5061 | 0.0002 |
| HAR-X | us_cyclicals_sector | 10325 | 0.2909 | 0.6197 | 0.4789 | -0.1881 | 0.9346 | 0.5827 | 0.0007 |
| HAR-X | us_large_cap_equity | 20650 | 0.3041 | 0.6542 | 0.5028 | -0.1210 | 0.8950 | 0.5264 | 0.0006 |
| HAR-X | us_rates_and_ig_credit | 10325 | 0.2043 | 0.5518 | 0.4080 | -0.0821 | 0.9006 | 0.4961 | 0.0002 |
| HAR-X | us_small_cap_equity | 10325 | 0.2500 | 0.5512 | 0.4048 | -0.0314 | 0.9026 | 0.5401 | 0.0007 |
| HAR-X | us_technology_sector | 10325 | 0.2560 | 0.6172 | 0.4778 | -0.1434 | 0.9083 | 0.5469 | 0.0008 |
