# HAR — Model Card

## Identity
- Model number (from MODEL_PLAN.md): 2
- Class: `rv_eval.model_contract:HAR`
- Model `name`: `HAR`
- Tier: Baseline (this is the §9 anchor baseline — must be in the predictions set)
- Implemented by: pre-coded benchmark (no implementation work); run 2026-05-31

## Configuration
- Features used (HAR_FEATURES): `log_rv_d`, `log_rv_w`, `log_rv_m`
- Model form: per-(ticker, horizon) OLS of `log(target_var)` on HAR lags + intercept; direct-h forecast; lognormal-mean correction `exp(mu + 0.5 s^2)` for `rv_hat`. Base class `_LinearLogHAR`, `min_obs = 100`.
- Hyperparameters: none (plain log-OLS — no free hyperparameters, per MODEL_PLAN §4)
- HP selection: N/A (model 2 has no tunable hyperparameters)
- Random seed: N/A (deterministic least-squares fit)
- Library versions: python 3.12.13, numpy 2.4.6, scipy 1.17.1, polars 1.41.1

## Training
- Universes run: clean_core, hard_cases
- Wall-clock time: clean_core 7.8s, hard_cases 4.1s
- Device: cpu (Apple Silicon arm64, macOS 15.3.1)
- OOS span: 2018-01-02 .. 2026-05-22
- Predictions parquet: `execution/data/predictions/HAR.parquet`
- Rows: 146,260 total (clean_core 105,450 + hard_cases 40,810)
- Coverage: all 15 scored tickers × all 5 horizons. No tickers/horizons dropped or imputed.
- Convergence notes: none — closed-form OLS, no iterative fit, no NaN/convergence warnings. IBIT has fewer rows (2,713; OOS effectively begins 2024-03 due to ~2y options history) but all 5 horizons fit; this is data availability, not a coverage gap.

---
_universe=`clean_core` · primary horizon h=22 · predictions=`execution/data/predictions/HAR.parquet` · generated 2026-06-01T03:00:58Z_

_Self-only metrics — no leaderboard rank, no DM test, no MCS, no §9 status._
_Cross-model comparison is produced by the final `rv_eval.evaluator` pass._

## Tier-1 pooled by horizon (§3)
| model | horizon | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR | 1 | 21080 | 0.3198 | 0.7934 | 0.6312 | -0.2629 | 0.8921 | 0.4963 | 0.0000 |
| HAR | 5 | 21040 | 0.2114 | 0.6188 | 0.4812 | -0.1552 | 0.8978 | 0.5278 | 0.0002 |
| HAR | 10 | 20990 | 0.2267 | 0.6166 | 0.4760 | -0.1501 | 0.9061 | 0.5483 | 0.0003 |
| HAR | 22 | 20870 | 0.3232 | 0.6607 | 0.5020 | -0.1663 | 0.9156 | 0.5644 | 0.0008 |
| HAR | 42 | 20670 | 0.4204 | 0.7295 | 0.5415 | -0.1895 | 0.9211 | 0.5820 | 0.0015 |

## §5 IV-incremental skill (per horizon)
| model | horizon | n | slope | t_slope | sign_acc | qlike_model | qlike_iv | qlike_gain_vs_iv |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR | 1 | 20820 | 1.1802 | 50.1134 | 0.6248 | 0.3194 | 0.3276 | 0.0083 |
| HAR | 5 | 20780 | 1.0334 | 47.9905 | 0.5870 | 0.2116 | 0.2079 | -0.0037 |
| HAR | 10 | 20730 | 0.6923 | 27.9997 | 0.5437 | 0.2274 | 0.2187 | -0.0087 |
| HAR | 22 | 20610 | 0.2814 | 10.0128 | 0.5058 | 0.3247 | 0.3396 | 0.0149 |
| HAR | 42 | 20410 | 0.3176 | 11.8683 | 0.4918 | 0.4238 | 0.4697 | 0.0459 |

## §6 Conditional bias by IV-percentile bucket (h=22)
| model | horizon | iv_pctile_bucket | n | qlike | log_bias |
| --- | --- | --- | --- | --- | --- |
| HAR | 22 | 0 | 5500 | 0.1833 | -0.2187 |
| HAR | 22 | 1 | 3449 | 0.3147 | -0.2091 |
| HAR | 22 | 2 | 3439 | 0.4470 | -0.1683 |
| HAR | 22 | 3 | 3533 | 0.3708 | -0.1372 |
| HAR | 22 | 4 | 4949 | 0.3646 | -0.0977 |

## §6 Post-shock calibration (h=22)
| model | horizon | bias_all | qlike_all | bias_postshock | qlike_postshock | n_postshock | trap_flag |
| --- | --- | --- | --- | --- | --- | --- | --- |
| HAR | 22 | -0.1663 | 0.3232 | -0.2534 | 0.3782 | 3986 |  |

## Per-ticker Tier-1 at h=22
| model | horizon | ticker | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR | 22 | EEM | 2087 | 0.2377 | 0.6801 | 0.5584 | -0.3350 | 0.9598 | 0.6397 | 0.0008 |
| HAR | 22 | GLD | 2087 | 0.1807 | 0.5407 | 0.4226 | -0.1112 | 0.8678 | 0.4763 | 0.0004 |
| HAR | 22 | HYG | 2087 | 0.6580 | 0.9982 | 0.8248 | -0.6434 | 0.9722 | 0.6967 | 0.0002 |
| HAR | 22 | IWM | 2087 | 0.2867 | 0.5784 | 0.4322 | -0.0527 | 0.8970 | 0.5117 | 0.0010 |
| HAR | 22 | QQQ | 2087 | 0.2835 | 0.6138 | 0.4725 | -0.0738 | 0.9344 | 0.6320 | 0.0008 |
| HAR | 22 | SPY | 2087 | 0.4344 | 0.7157 | 0.5544 | -0.1098 | 0.8941 | 0.5046 | 0.0007 |
| HAR | 22 | TLT | 2087 | 0.2094 | 0.5112 | 0.3714 | -0.0321 | 0.8869 | 0.4988 | 0.0003 |
| HAR | 22 | XLE | 2087 | 0.2776 | 0.5509 | 0.3945 | -0.0529 | 0.9109 | 0.5759 | 0.0015 |
| HAR | 22 | XLF | 2087 | 0.3680 | 0.6753 | 0.5336 | -0.2171 | 0.9276 | 0.5577 | 0.0011 |
| HAR | 22 | XLK | 2087 | 0.2958 | 0.6075 | 0.4560 | -0.0352 | 0.9056 | 0.5501 | 0.0011 |

## Pooled by group
| model | group | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR | emerging_markets | 10465 | 0.2942 | 0.7760 | 0.6250 | -0.3509 | 0.9305 | 0.5820 | 0.0006 |
| HAR | high_yield_credit | 10465 | 0.5098 | 0.9391 | 0.7642 | -0.5385 | 0.9581 | 0.6487 | 0.0002 |
| HAR | oil_and_energy | 10465 | 0.2562 | 0.5686 | 0.4171 | -0.0803 | 0.8999 | 0.5461 | 0.0011 |
| HAR | precious_metals | 10465 | 0.2421 | 0.6717 | 0.5210 | -0.1829 | 0.8708 | 0.4690 | 0.0003 |
| HAR | us_cyclicals_sector | 10465 | 0.3132 | 0.6674 | 0.5195 | -0.2098 | 0.9241 | 0.5624 | 0.0008 |
| HAR | us_large_cap_equity | 20930 | 0.3167 | 0.6810 | 0.5257 | -0.1206 | 0.9023 | 0.5438 | 0.0006 |
| HAR | us_rates_and_ig_credit | 10465 | 0.2181 | 0.5838 | 0.4378 | -0.0857 | 0.8849 | 0.5007 | 0.0002 |
| HAR | us_small_cap_equity | 10465 | 0.2579 | 0.5925 | 0.4457 | -0.0829 | 0.8916 | 0.5119 | 0.0007 |
| HAR | us_technology_sector | 10465 | 0.2741 | 0.6316 | 0.4829 | -0.0766 | 0.9001 | 0.5271 | 0.0008 |
