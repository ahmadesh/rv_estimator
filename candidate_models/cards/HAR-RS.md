# HAR-RS — Model Card

## Identity
- Model number (from MODEL_PLAN.md): 5
- Class: candidate_models.har_rs:HARRS
- Tier: Modern HAR (semivariance + jump)
- Implemented by: swarm worker, 2026-06-01

## Configuration
- Features used (list, by name): log_rv_d, log_rv_w, log_rv_m, rs_minus_5d, rs_plus_5d, jump_5d (= HAR_RS_FEATURES)
- Hyperparameters (key=value, one per line — the FROZEN values used): none (plain per-(ticker, horizon) log-OLS via _LinearLogHAR; min_obs=100 inherited)
- HP selection (models 8–11): N/A — model 5 has no free hyperparameters.
- Library version(s): python 3.12.13, numpy 2.4.6, polars 1.41.1, scipy 1.17.1
- Random seed (if applicable): N/A (deterministic OLS via numpy.linalg.lstsq)

## Training
- Universes run: clean_core, hard_cases
- Walk-forward folds: monthly refit, expanding window, OOS 2018-01-02 .. 2026-05-22 (per rv_eval.config)
- Wall-clock time: clean_core 8s, hard_cases 4s
- Device: cpu (Apple Silicon arm64, macOS 15.3.1)
- Convergence notes / per-ticker warnings: no convergence warnings (closed-form OLS). Full (ticker × horizon) coverage — all 15 tickers × all 5 horizons present, no cells dropped or imputed. Shorter-history tickers have fewer OOS rows: IBIT 2,713 and MSOS 6,462 (vs 10,545 for full-history tickers); all 5 horizons still covered for both.
- OOS row counts: clean_core 105,450; hard_cases 40,810; file total 146,260.

# HAR-RS — Self Stats
_universe=`clean_core` · primary horizon h=22 · predictions=`execution/data/predictions/HAR-RS.parquet` · generated 2026-06-01T03:09:42Z_

_Self-only metrics — no leaderboard rank, no DM test, no MCS, no §9 status._
_Cross-model comparison is produced by the final `rv_eval.evaluator` pass._

## Tier-1 pooled by horizon (§3)
| model | horizon | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-RS | 1 | 21080 | 0.3199 | 0.7943 | 0.6287 | -0.2572 | 0.8910 | 0.4952 | 0.0001 |
| HAR-RS | 5 | 21040 | 0.2127 | 0.6212 | 0.4788 | -0.1494 | 0.8964 | 0.5280 | 0.0002 |
| HAR-RS | 10 | 20990 | 0.2291 | 0.6194 | 0.4730 | -0.1432 | 0.9047 | 0.5473 | 0.0004 |
| HAR-RS | 22 | 20870 | 0.3265 | 0.6621 | 0.4983 | -0.1578 | 0.9134 | 0.5651 | 0.0009 |
| HAR-RS | 42 | 20670 | 0.4223 | 0.7303 | 0.5373 | -0.1805 | 0.9194 | 0.5817 | 0.0017 |

## §5 IV-incremental skill (per horizon)
| model | horizon | n | slope | t_slope | sign_acc | qlike_model | qlike_iv | qlike_gain_vs_iv |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-RS | 1 | 20820 | 0.0161 | 12.2341 | 0.6351 | 0.3195 | 0.3276 | 0.0082 |
| HAR-RS | 5 | 20780 | 0.0401 | 14.6545 | 0.5960 | 0.2130 | 0.2079 | -0.0051 |
| HAR-RS | 10 | 20730 | 0.0323 | 7.6087 | 0.5517 | 0.2299 | 0.2187 | -0.0113 |
| HAR-RS | 22 | 20610 | -0.0182 | -3.1391 | 0.5116 | 0.3281 | 0.3396 | 0.0115 |
| HAR-RS | 42 | 20410 | -0.0285 | -4.4168 | 0.4990 | 0.4258 | 0.4697 | 0.0439 |

## §6 Conditional bias by IV-percentile bucket (h=22)
| model | horizon | iv_pctile_bucket | n | qlike | log_bias |
| --- | --- | --- | --- | --- | --- |
| HAR-RS | 22 | 0 | 5500 | 0.1790 | -0.2212 |
| HAR-RS | 22 | 1 | 3449 | 0.3080 | -0.2024 |
| HAR-RS | 22 | 2 | 3439 | 0.4476 | -0.1560 |
| HAR-RS | 22 | 3 | 3533 | 0.3742 | -0.1113 |
| HAR-RS | 22 | 4 | 4949 | 0.3853 | -0.0909 |

## §6 Post-shock calibration (h=22)
| model | horizon | bias_all | qlike_all | bias_postshock | qlike_postshock | n_postshock | trap_flag |
| --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-RS | 22 | -0.1578 | 0.3265 | -0.2460 | 0.3994 | 3986 |  |

## Per-ticker Tier-1 at h=22
| model | horizon | ticker | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-RS | 22 | EEM | 2087 | 0.2360 | 0.6541 | 0.5351 | -0.3025 | 0.9612 | 0.6488 | 0.0007 |
| HAR-RS | 22 | GLD | 2087 | 0.1816 | 0.5404 | 0.4180 | -0.1079 | 0.8682 | 0.4940 | 0.0004 |
| HAR-RS | 22 | HYG | 2087 | 0.6535 | 0.9907 | 0.8177 | -0.6345 | 0.9732 | 0.6914 | 0.0002 |
| HAR-RS | 22 | IWM | 2087 | 0.2969 | 0.5890 | 0.4327 | -0.0426 | 0.8951 | 0.4950 | 0.0013 |
| HAR-RS | 22 | QQQ | 2087 | 0.2842 | 0.6256 | 0.4776 | -0.0814 | 0.9281 | 0.6320 | 0.0010 |
| HAR-RS | 22 | SPY | 2087 | 0.4440 | 0.7225 | 0.5493 | -0.0931 | 0.8912 | 0.5041 | 0.0008 |
| HAR-RS | 22 | TLT | 2087 | 0.2208 | 0.5547 | 0.3819 | -0.0463 | 0.8821 | 0.5031 | 0.0007 |
| HAR-RS | 22 | XLE | 2087 | 0.2822 | 0.5551 | 0.3970 | -0.0511 | 0.9099 | 0.5745 | 0.0016 |
| HAR-RS | 22 | XLF | 2087 | 0.3656 | 0.6616 | 0.5215 | -0.1959 | 0.9281 | 0.5597 | 0.0011 |
| HAR-RS | 22 | XLK | 2087 | 0.3004 | 0.6070 | 0.4524 | -0.0230 | 0.8965 | 0.5486 | 0.0011 |

## Pooled by group
| model | group | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-RS | emerging_markets | 10465 | 0.2928 | 0.7537 | 0.6041 | -0.3196 | 0.9324 | 0.5830 | 0.0005 |
| HAR-RS | high_yield_credit | 10465 | 0.5072 | 0.9347 | 0.7610 | -0.5348 | 0.9579 | 0.6475 | 0.0001 |
| HAR-RS | oil_and_energy | 10465 | 0.2616 | 0.5715 | 0.4176 | -0.0754 | 0.8977 | 0.5433 | 0.0012 |
| HAR-RS | precious_metals | 10465 | 0.2396 | 0.6682 | 0.5164 | -0.1809 | 0.8700 | 0.4743 | 0.0003 |
| HAR-RS | us_cyclicals_sector | 10465 | 0.3105 | 0.6563 | 0.5097 | -0.1922 | 0.9251 | 0.5652 | 0.0008 |
| HAR-RS | us_large_cap_equity | 20930 | 0.3203 | 0.6923 | 0.5266 | -0.1190 | 0.8989 | 0.5432 | 0.0007 |
| HAR-RS | us_rates_and_ig_credit | 10465 | 0.2249 | 0.6210 | 0.4470 | -0.0967 | 0.8817 | 0.5037 | 0.0005 |
| HAR-RS | us_small_cap_equity | 10465 | 0.2644 | 0.5977 | 0.4446 | -0.0726 | 0.8911 | 0.5055 | 0.0009 |
| HAR-RS | us_technology_sector | 10465 | 0.2753 | 0.6297 | 0.4793 | -0.0670 | 0.8956 | 0.5237 | 0.0008 |
