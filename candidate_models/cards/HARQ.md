# HARQ — Model Card (clean_core)

## Identity
- Model number (from MODEL_PLAN.md): 4
- Class: candidate_models.harq:HARQ
- Tier: Modern HAR (quarticity-corrected, Bollerslev–Patton–Quaedvlieg 2016)
- Implemented by: swarm worker, 2026-05-31

## Configuration
- Features used (list, by name): log_rv_d, log_rv_w, log_rv_m, sqrt_rq  (= HARQ_FEATURES = HAR_FEATURES + ["sqrt_rq"])
- Hyperparameters (key=value): none — plain per-(ticker, horizon) log-OLS via `_LinearLogHAR` (intercept + 4 features, lognormal-mean correction). No free hyperparameters.
- HP selection (models 8–11): N/A for models 0–7.
- Library version(s): python 3.12.13, numpy 2.4.6, polars 1.41.1, scipy 1.17.1 (only numpy used for the OLS solve)
- Random seed (if applicable): N/A (deterministic least-squares fit)

## Training
- Universes run: clean_core, hard_cases (this card = clean_core)
- Walk-forward folds: 101 (monthly refit, expanding window; shared across both universes)
- Wall-clock time: clean_core 0m 08.0s, hard_cases 0m 04.0s (wall, `/usr/bin/time -p`)
- Device: cpu (Apple M4, arm64; numpy linalg.lstsq)
- Convergence notes / per-ticker warnings: none. OLS solves cleanly for every (ticker, horizon); `min_obs=100` guard (inherited) never tripped on clean_core. All 10 clean_core tickers × 5 horizons covered; rv_hat finite and >0 everywhere.

## Coverage
- clean_core OOS rows: 105,450 (10 tickers × 5 horizons, span 2018-01-02 … 2026-05-22)
- Tickers/horizons NOT covered (dropped, never imputed): none on clean_core.

---

# HARQ — Self Stats
_universe=`clean_core` · primary horizon h=22 · predictions=`execution/data/predictions/HARQ.parquet` · generated 2026-06-01T03:06:45Z_

_Self-only metrics — no leaderboard rank, no DM test, no MCS, no §9 status._
_Cross-model comparison is produced by the final `rv_eval.evaluator` pass._

## Tier-1 pooled by horizon (§3)
| model | horizon | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HARQ | 1 | 21080 | 0.3177 | 0.7892 | 0.6281 | -0.2593 | 0.8931 | 0.4971 | 0.0000 |
| HARQ | 5 | 21040 | 0.2102 | 0.6160 | 0.4790 | -0.1525 | 0.8985 | 0.5273 | 0.0002 |
| HARQ | 10 | 20990 | 0.2256 | 0.6143 | 0.4738 | -0.1475 | 0.9066 | 0.5489 | 0.0003 |
| HARQ | 22 | 20870 | 0.3226 | 0.6590 | 0.5003 | -0.1641 | 0.9160 | 0.5644 | 0.0008 |
| HARQ | 42 | 20670 | 0.4200 | 0.7283 | 0.5401 | -0.1877 | 0.9213 | 0.5823 | 0.0016 |

## §5 IV-incremental skill (per horizon)
| model | horizon | n | slope | t_slope | sign_acc | qlike_model | qlike_iv | qlike_gain_vs_iv |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HARQ | 1 | 20820 | 0.3835 | 39.0500 | 0.6298 | 0.3172 | 0.3276 | 0.0104 |
| HARQ | 5 | 20780 | 0.4214 | 39.4544 | 0.5895 | 0.2104 | 0.2079 | -0.0025 |
| HARQ | 10 | 20730 | 0.2653 | 22.2582 | 0.5466 | 0.2263 | 0.2187 | -0.0076 |
| HARQ | 22 | 20610 | 0.0880 | 5.8056 | 0.5071 | 0.3241 | 0.3396 | 0.0155 |
| HARQ | 42 | 20410 | 0.0728 | 4.6835 | 0.4946 | 0.4234 | 0.4697 | 0.0462 |

## §6 Conditional bias by IV-percentile bucket (h=22)
| model | horizon | iv_pctile_bucket | n | qlike | log_bias |
| --- | --- | --- | --- | --- | --- |
| HARQ | 22 | 0 | 5500 | 0.1817 | -0.2210 |
| HARQ | 22 | 1 | 3449 | 0.3125 | -0.2078 |
| HARQ | 22 | 2 | 3439 | 0.4461 | -0.1647 |
| HARQ | 22 | 3 | 3533 | 0.3706 | -0.1296 |
| HARQ | 22 | 4 | 4949 | 0.3661 | -0.0948 |

## §6 Post-shock calibration (h=22)
| model | horizon | bias_all | qlike_all | bias_postshock | qlike_postshock | n_postshock | trap_flag |
| --- | --- | --- | --- | --- | --- | --- | --- |
| HARQ | 22 | -0.1641 | 0.3226 | -0.2509 | 0.3784 | 3986 |  |

## Per-ticker Tier-1 at h=22
| model | horizon | ticker | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HARQ | 22 | EEM | 2087 | 0.2329 | 0.6656 | 0.5463 | -0.3236 | 0.9612 | 0.6507 | 0.0007 |
| HARQ | 22 | GLD | 2087 | 0.1801 | 0.5384 | 0.4201 | -0.1097 | 0.8730 | 0.4792 | 0.0004 |
| HARQ | 22 | HYG | 2087 | 0.6585 | 0.9984 | 0.8251 | -0.6435 | 0.9722 | 0.6967 | 0.0002 |
| HARQ | 22 | IWM | 2087 | 0.2872 | 0.5814 | 0.4323 | -0.0502 | 0.8975 | 0.5041 | 0.0011 |
| HARQ | 22 | QQQ | 2087 | 0.2829 | 0.6133 | 0.4719 | -0.0723 | 0.9329 | 0.6315 | 0.0008 |
| HARQ | 22 | SPY | 2087 | 0.4328 | 0.7131 | 0.5515 | -0.1048 | 0.8936 | 0.5046 | 0.0007 |
| HARQ | 22 | TLT | 2087 | 0.2094 | 0.5113 | 0.3714 | -0.0322 | 0.8869 | 0.4983 | 0.0003 |
| HARQ | 22 | XLE | 2087 | 0.2784 | 0.5513 | 0.3953 | -0.0527 | 0.9099 | 0.5707 | 0.0015 |
| HARQ | 22 | XLF | 2087 | 0.3677 | 0.6745 | 0.5331 | -0.2164 | 0.9281 | 0.5587 | 0.0011 |
| HARQ | 22 | XLK | 2087 | 0.2960 | 0.6081 | 0.4564 | -0.0359 | 0.9046 | 0.5501 | 0.0011 |

## Pooled by group
| model | group | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HARQ | emerging_markets | 10465 | 0.2890 | 0.7626 | 0.6137 | -0.3389 | 0.9328 | 0.5840 | 0.0005 |
| HARQ | high_yield_credit | 10465 | 0.5104 | 0.9392 | 0.7644 | -0.5388 | 0.9579 | 0.6485 | 0.0002 |
| HARQ | oil_and_energy | 10465 | 0.2563 | 0.5684 | 0.4172 | -0.0796 | 0.8993 | 0.5428 | 0.0011 |
| HARQ | precious_metals | 10465 | 0.2389 | 0.6666 | 0.5172 | -0.1805 | 0.8739 | 0.4707 | 0.0003 |
| HARQ | us_cyclicals_sector | 10465 | 0.3128 | 0.6665 | 0.5188 | -0.2089 | 0.9244 | 0.5636 | 0.0008 |
| HARQ | us_large_cap_equity | 20930 | 0.3151 | 0.6786 | 0.5233 | -0.1173 | 0.9022 | 0.5447 | 0.0006 |
| HARQ | us_rates_and_ig_credit | 10465 | 0.2175 | 0.5824 | 0.4366 | -0.0845 | 0.8855 | 0.5015 | 0.0002 |
| HARQ | us_small_cap_equity | 10465 | 0.2585 | 0.5942 | 0.4453 | -0.0799 | 0.8922 | 0.5100 | 0.0008 |
| HARQ | us_technology_sector | 10465 | 0.2744 | 0.6320 | 0.4832 | -0.0771 | 0.8997 | 0.5277 | 0.0008 |
