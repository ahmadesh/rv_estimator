# HAR-RS-IV-Q — Model Card

## Identity
- Model number (from MODEL_PLAN.md): 7
- Class: `candidate_models.har_rs_iv_q:HARRSIVQ`
- Tier: Modern HAR (research doc's recommended primary / strongest linear baseline)
- Implemented by: swarm worker, 2026-05-31

## Configuration
- Features used (14, deduplicated, first-seen order = `HAR_RS_FEATURES + IV_FEATURES + ["sqrt_rq"]`):
  `log_rv_d`, `log_rv_w`, `log_rv_m`, `rs_minus_5d`, `rs_plus_5d`, `jump_5d`,
  `log_iv`, `iv_slope`, `skew_25d`, `vix`, `vix3m`, `vix_slope`, `vvix`, `sqrt_rq`.
  (No column repeated across the three groups, so dedup dropped nothing — all 14 retained.)
- Hyperparameters: **none** — plain per-(ticker, horizon) log-OLS via `_LinearLogHAR`.
  Intercept + the 14 features above; `sigma` = OLS log-residual std (ddof = n_params).
- HP selection (models 8–11): N/A — model 7 has no free hyperparameters; not tuned.
- Library version(s): python 3.12.13, numpy 2.4.6, scipy 1.17.1, polars 1.41.1.
- Random seed: N/A (deterministic OLS via `numpy.linalg.lstsq`).

## Training
- Universes run: clean_core (10 tickers), hard_cases (5 tickers).
- Refit cadence / protocol: monthly refit, expanding window, OOS_START=2018-01-01 (per `rv_eval.config`); folds owned by the walk-forward harness.
- Wall-clock time: clean_core ≈ 10 s, hard_cases ≈ 5 s.
- Device: cpu (Apple Silicon, macOS-15.3.1-arm64; OLS is CPU-only).
- OOS rows: clean_core 104,000 · hard_cases 38,497 · total 142,497. All 15 scored tickers covered, all 5 horizons (1,5,10,22,42).
- Convergence notes / per-ticker warnings:
  - No fit failures; OLS converged for every (ticker, horizon).
  - **IV-feature nulls drop rows (never imputed):** the model `needs` the IV block
    (`log_iv, iv_slope, skew_25d, vix, vix3m, vix_slope, vvix`), so any (ticker, date) with a
    null IV feature is excluded from both fit and predict. This shortens hard-case coverage:
    **IBIT** predicts only 2025-05-01 → 2026-05-21 (1,247 rows; ~1y of options/IV history) and
    **MSOS** only 2021-06-01 → 2026-05-21 (6,055 rows). UVXY is near-full (10,395 rows). No
    clean_core ticker is materially shortened.

---

# HAR-RS-IV-Q — Self Stats
_universe=`clean_core` · primary horizon h=22 · predictions=`execution/data/predictions/HAR-RS-IV-Q.parquet` · generated 2026-06-01T03:18:24Z_

_Self-only metrics — no leaderboard rank, no DM test, no MCS, no §9 status._
_Cross-model comparison is produced by the final `rv_eval.evaluator` pass._

## Tier-1 pooled by horizon (§3)
| model | horizon | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-RS-IV-Q | 1 | 20800 | 0.2818 | 0.7420 | 0.5931 | -0.2411 | 0.8923 | 0.4930 | 0.0000 |
| HAR-RS-IV-Q | 5 | 20760 | 0.1813 | 0.5627 | 0.4368 | -0.1263 | 0.8967 | 0.5223 | 0.0002 |
| HAR-RS-IV-Q | 10 | 20710 | 0.2057 | 0.5613 | 0.4266 | -0.1101 | 0.9081 | 0.5380 | 0.0003 |
| HAR-RS-IV-Q | 22 | 20590 | 0.3458 | 0.6092 | 0.4480 | -0.1031 | 0.9165 | 0.5607 | 0.0008 |
| HAR-RS-IV-Q | 42 | 20390 | 0.4680 | 0.6827 | 0.4910 | -0.1031 | 0.9133 | 0.5689 | 0.0016 |

## §5 IV-incremental skill (per horizon)
| model | horizon | n | slope | t_slope | sign_acc | qlike_model | qlike_iv | qlike_gain_vs_iv |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-RS-IV-Q | 1 | 20800 | 0.4829 | 47.1293 | 0.7047 | 0.2818 | 0.3273 | 0.0455 |
| HAR-RS-IV-Q | 5 | 20760 | 0.5006 | 37.9129 | 0.6574 | 0.1813 | 0.2079 | 0.0265 |
| HAR-RS-IV-Q | 10 | 20710 | 0.3456 | 18.5229 | 0.6019 | 0.2057 | 0.2187 | 0.0130 |
| HAR-RS-IV-Q | 22 | 20590 | 0.0334 | 1.7476 | 0.5217 | 0.3458 | 0.3397 | -0.0061 |
| HAR-RS-IV-Q | 42 | 20390 | 0.0075 | 0.4691 | 0.5043 | 0.4680 | 0.4701 | 0.0021 |

## §6 Conditional bias by IV-percentile bucket (h=22)
| model | horizon | iv_pctile_bucket | n | qlike | log_bias |
| --- | --- | --- | --- | --- | --- |
| HAR-RS-IV-Q | 22 | 0 | 5239 | 0.1838 | -0.1473 |
| HAR-RS-IV-Q | 22 | 1 | 3448 | 0.3488 | -0.1619 |
| HAR-RS-IV-Q | 22 | 2 | 3439 | 0.5105 | -0.1183 |
| HAR-RS-IV-Q | 22 | 3 | 3531 | 0.3688 | -0.0807 |
| HAR-RS-IV-Q | 22 | 4 | 4933 | 0.3846 | -0.0204 |

## §6 Post-shock calibration (h=22)
| model | horizon | bias_all | qlike_all | bias_postshock | qlike_postshock | n_postshock | trap_flag |
| --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-RS-IV-Q | 22 | -0.1031 | 0.3458 | -0.0497 | 0.4124 | 3914 |  |

## Per-ticker Tier-1 at h=22
| model | horizon | ticker | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-RS-IV-Q | 22 | EEM | 2059 | 0.2566 | 0.5733 | 0.4269 | -0.0541 | 0.9000 | 0.5784 | 0.0007 |
| HAR-RS-IV-Q | 22 | GLD | 2059 | 0.1427 | 0.4615 | 0.3370 | -0.0147 | 0.8970 | 0.5381 | 0.0003 |
| HAR-RS-IV-Q | 22 | HYG | 2059 | 0.8343 | 0.8303 | 0.6487 | -0.3617 | 0.9582 | 0.5964 | 0.0002 |
| HAR-RS-IV-Q | 22 | IWM | 2059 | 0.3118 | 0.5507 | 0.3915 | 0.0181 | 0.9077 | 0.5508 | 0.0010 |
| HAR-RS-IV-Q | 22 | QQQ | 2059 | 0.2959 | 0.6166 | 0.4659 | -0.0831 | 0.8995 | 0.5653 | 0.0009 |
| HAR-RS-IV-Q | 22 | SPY | 2059 | 0.4583 | 0.7007 | 0.5222 | -0.0875 | 0.9019 | 0.5537 | 0.0007 |
| HAR-RS-IV-Q | 22 | TLT | 2059 | 0.2057 | 0.4795 | 0.3342 | -0.0356 | 0.9189 | 0.4881 | 0.0003 |
| HAR-RS-IV-Q | 22 | XLE | 2059 | 0.2839 | 0.5492 | 0.3990 | -0.0988 | 0.9271 | 0.5440 | 0.0015 |
| HAR-RS-IV-Q | 22 | XLF | 2059 | 0.3719 | 0.6281 | 0.4839 | -0.1782 | 0.9446 | 0.6163 | 0.0010 |
| HAR-RS-IV-Q | 22 | XLK | 2059 | 0.2972 | 0.6162 | 0.4710 | -0.1352 | 0.9102 | 0.5760 | 0.0011 |

## Pooled by group
| model | group | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-RS-IV-Q | emerging_markets | 10325 | 0.2911 | 0.6755 | 0.5099 | -0.1180 | 0.8926 | 0.5317 | 0.0005 |
| HAR-RS-IV-Q | high_yield_credit | 10325 | 0.5823 | 0.8039 | 0.6293 | -0.3374 | 0.9400 | 0.5840 | 0.0001 |
| HAR-RS-IV-Q | oil_and_energy | 10325 | 0.2471 | 0.5561 | 0.4112 | -0.1172 | 0.9096 | 0.5351 | 0.0011 |
| HAR-RS-IV-Q | precious_metals | 10325 | 0.2037 | 0.6036 | 0.4525 | -0.0929 | 0.8857 | 0.5086 | 0.0002 |
| HAR-RS-IV-Q | us_cyclicals_sector | 10325 | 0.2945 | 0.6177 | 0.4752 | -0.1772 | 0.9344 | 0.5831 | 0.0008 |
| HAR-RS-IV-Q | us_large_cap_equity | 20650 | 0.3093 | 0.6615 | 0.5068 | -0.1266 | 0.8925 | 0.5248 | 0.0006 |
| HAR-RS-IV-Q | us_rates_and_ig_credit | 10325 | 0.2040 | 0.5529 | 0.4090 | -0.0851 | 0.8996 | 0.4938 | 0.0002 |
| HAR-RS-IV-Q | us_small_cap_equity | 10325 | 0.2582 | 0.5560 | 0.4072 | -0.0292 | 0.8999 | 0.5382 | 0.0007 |
| HAR-RS-IV-Q | us_technology_sector | 10325 | 0.2594 | 0.6249 | 0.4841 | -0.1594 | 0.9063 | 0.5397 | 0.0008 |
