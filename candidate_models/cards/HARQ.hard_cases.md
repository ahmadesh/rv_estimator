# HARQ — Model Card (hard_cases)

## Identity
- Model number (from MODEL_PLAN.md): 4
- Class: candidate_models.harq:HARQ
- Tier: Modern HAR (quarticity-corrected, Bollerslev–Patton–Quaedvlieg 2016)
- Implemented by: swarm worker, 2026-05-31

## Configuration
- Features used (list, by name): log_rv_d, log_rv_w, log_rv_m, sqrt_rq  (= HARQ_FEATURES = HAR_FEATURES + ["sqrt_rq"])
- Hyperparameters (key=value): none — plain per-(ticker, horizon) log-OLS via `_LinearLogHAR`. No free hyperparameters.
- HP selection (models 8–11): N/A for models 0–7.
- Library version(s): python 3.12.13, numpy 2.4.6, polars 1.41.1, scipy 1.17.1 (only numpy used for the OLS solve)
- Random seed (if applicable): N/A (deterministic least-squares fit)

## Training
- Universes run: clean_core, hard_cases (this card = hard_cases)
- Walk-forward folds: 101 (monthly refit, expanding window; shared across both universes)
- Wall-clock time: clean_core 0m 08.0s, hard_cases 0m 04.0s (wall, `/usr/bin/time -p`)
- Device: cpu (Apple M4, arm64; numpy linalg.lstsq)
- Convergence notes / per-ticker warnings: OLS solves cleanly for all 5 hard-case tickers × 5 horizons. No NaN/non-finite rv_hat. Data-starved tickers have shorter OOS support (IBIT ~2,713 rows total; MSOS ~6,462) because their histories are short, but all 5 horizons are present for both — the `min_obs=100` guard was satisfied. Predictions are dropped, never imputed, where rows are absent (none missing on this universe given the available histories).

## Coverage
- hard_cases OOS rows: 40,810 (5 tickers × 5 horizons, span 2018-01-02 … 2026-05-22)
- Per-ticker total rows: KRE/USO/UVXY 10,545 each; MSOS 6,462; IBIT 2,713.
- Tickers/horizons NOT covered (dropped, never imputed): none — all 5 tickers cover all 5 horizons. Shorter spans for IBIT and MSOS reflect their available history, not a model failure.

---

# HARQ — Self Stats
_universe=`hard_cases` · primary horizon h=22 · predictions=`execution/data/predictions/HARQ.parquet` · generated 2026-06-01T03:06:46Z_

_Self-only metrics — no leaderboard rank, no DM test, no MCS, no §9 status._
_Cross-model comparison is produced by the final `rv_eval.evaluator` pass._

## Tier-1 pooled by horizon (§3)
| model | horizon | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HARQ | 1 | 8196 | 0.3495 | 0.7806 | 0.6117 | -0.2667 | 0.8974 | 0.5195 | 0.0005 |
| HARQ | 5 | 8153 | 0.2773 | 0.6662 | 0.5074 | -0.1786 | 0.8897 | 0.5182 | 0.0020 |
| HARQ | 10 | 8108 | 0.2811 | 0.6665 | 0.5053 | -0.1648 | 0.8768 | 0.5091 | 0.0043 |
| HARQ | 22 | 8048 | 0.2996 | 0.6653 | 0.5101 | -0.1395 | 0.8662 | 0.4867 | 0.0087 |
| HARQ | 42 | 7905 | 0.3224 | 0.6749 | 0.5133 | -0.1179 | 0.8486 | 0.4732 | 0.0178 |

## §5 IV-incremental skill (per horizon)
| model | horizon | n | slope | t_slope | sign_acc | qlike_model | qlike_iv | qlike_gain_vs_iv |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HARQ | 1 | 7906 | 0.0089 | 1.8895 | 0.6920 | 0.3430 | 0.3595 | 0.0165 |
| HARQ | 5 | 7863 | 0.3502 | 14.0857 | 0.6487 | 0.2742 | 0.2624 | -0.0119 |
| HARQ | 10 | 7838 | 0.0243 | 3.3331 | 0.6060 | 0.2788 | 0.2542 | -0.0246 |
| HARQ | 22 | 7778 | 0.3659 | 23.5456 | 0.5603 | 0.2996 | 0.2732 | -0.0265 |
| HARQ | 42 | 7657 | 0.0055 | 2.3931 | 0.5523 | 0.3274 | 0.3134 | -0.0140 |

## §6 Conditional bias by IV-percentile bucket (h=22)
| model | horizon | iv_pctile_bucket | n | qlike | log_bias |
| --- | --- | --- | --- | --- | --- |
| HARQ | 22 | 0 | 2078 | 0.3131 | -0.2487 |
| HARQ | 22 | 1 | 1264 | 0.2486 | -0.1505 |
| HARQ | 22 | 2 | 1355 | 0.2495 | -0.0905 |
| HARQ | 22 | 3 | 1460 | 0.2653 | -0.1111 |
| HARQ | 22 | 4 | 1727 | 0.3909 | -0.0265 |

## §6 Post-shock calibration (h=22)
| model | horizon | bias_all | qlike_all | bias_postshock | qlike_postshock | n_postshock | trap_flag |
| --- | --- | --- | --- | --- | --- | --- | --- |
| HARQ | 22 | -0.1395 | 0.2996 | -0.1914 | 0.3266 | 1487 |  |

## Per-ticker Tier-1 at h=22
| model | horizon | ticker | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HARQ | 22 | IBIT | 517 | 0.2125 | 0.7408 | 0.6235 | -0.4927 | 0.7176 | 0.4391 | 0.0037 |
| HARQ | 22 | KRE | 2087 | 0.3426 | 0.6138 | 0.4506 | -0.1041 | 0.9305 | 0.5616 | 0.0017 |
| HARQ | 22 | MSOS | 1270 | 0.2606 | 0.6322 | 0.4827 | 0.0481 | 0.8181 | 0.4756 | 0.0070 |
| HARQ | 22 | USO | 2087 | 0.2699 | 0.6112 | 0.4555 | -0.0234 | 0.8275 | 0.4375 | 0.0037 |
| HARQ | 22 | UVXY | 2087 | 0.3317 | 0.7599 | 0.6128 | -0.3177 | 0.9066 | 0.4796 | 0.0228 |

## Pooled by group
| model | group | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HARQ | crypto | 2633 | 0.2941 | 0.8527 | 0.6975 | -0.5451 | 0.8496 | 0.4945 | 0.0026 |
| HARQ | long_volatility_vix | 10465 | 0.3231 | 0.7726 | 0.6220 | -0.3135 | 0.8958 | 0.4874 | 0.0155 |
| HARQ | oil_and_energy | 10465 | 0.3059 | 0.6781 | 0.5084 | -0.0928 | 0.8324 | 0.4508 | 0.0051 |
| HARQ | us_cannabis | 6382 | 0.3048 | 0.6349 | 0.4783 | -0.0155 | 0.8544 | 0.5081 | 0.0048 |
| HARQ | us_cyclicals_sector | 10465 | 0.2927 | 0.6053 | 0.4483 | -0.1192 | 0.9194 | 0.5643 | 0.0013 |
