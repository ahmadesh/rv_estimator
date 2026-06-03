# HAR-X — Model Card (hard_cases)

## Identity
- Model number (from MODEL_PLAN.md): 3
- Class: `rv_eval.model_contract:HARX`
- model `name`: `HAR-X`
- Tier: Baseline (reference benchmark; modern-HAR extension with IV/VIX exogenous regressors)
- Implemented by: pre-coded in `rv_eval/model_contract.py`. Run 2026-05-31 by swarm worker.

## Configuration
- Features used (by name): `HAR_FEATURES + IV_FEATURES` = `log_rv_d`, `log_rv_w`, `log_rv_m`, `log_iv`, `iv_slope`, `skew_25d`, `vix`, `vix3m`, `vix_slope`, `vvix` (10 regressors + intercept).
- Hyperparameters: none. Per-(ticker, horizon) log-OLS (`_LinearLogHAR`, `min_obs=100`).
- HP selection: N/A.
- Library versions: python 3.12.13, numpy 2.4.6, scipy 1.17.1, polars 1.41.1.
- Random seed: N/A (deterministic OLS).

## Training
- Universes run: clean_core, hard_cases (this card scores hard_cases only).
- Walk-forward: purged + embargoed monthly-refit rolling-origin (expanding), OOS_START=2018-01-01, span 2018-01-02 → 2026-05-21.
- Wall-clock time: hard_cases 4.4s (clean_core 9.4s).
- Device: cpu (Apple Silicon, macOS-15.3.1-arm64).
- Prediction parquet: `execution/data/predictions/HAR-X.parquet` (shared file; 38,497 hard_cases rows of 142,497 total).
- Convergence notes / per-ticker warnings:
  - No OLS convergence failures.
  - **KRE, USO, UVXY: full coverage** (~2,058–2,080 OOS rows × 5 horizons; UVXY missing 1 row vs others).
  - **IBIT: severely data-starved (BTC ETF, ~2y of options coverage).** Only ~266 OOS rows at h=1, shrinking to 245 (h=10/22) and 225 (h=42). Its `log_iv`/`iv_slope`/`skew_25d` are null on 313 of 686 OOS feature rows; those rows are **dropped, never imputed**. Interval coverage at h=22 is poor (cov90=0.50, cov50=0.25) on the thin sample — flagged for the comparison reader.
  - **MSOS: thin (cannabis ETF).** ~1,202 OOS rows at h=22 vs the 2,080 of a full ticker; `log_iv` null on 100 of 1,437 OOS feature rows (dropped). Shows positive log_bias (+0.196 at h=22) and weak interval coverage (cov90=0.70).
  - Where IV features are missing the entire row is excluded from fit and predict (the `_LinearLogHAR` design matrix carries NaN, and `_PerKeyModel` drops non-finite predictions). No imputation anywhere.

# HAR-X — Self Stats
_universe=`hard_cases` · primary horizon h=22 · predictions=`execution/data/predictions/HAR-X.parquet` · generated 2026-06-01T03:03:07Z_

_Self-only metrics — no leaderboard rank, no DM test, no MCS, no §9 status._
_Cross-model comparison is produced by the final `rv_eval.evaluator` pass._

## Tier-1 pooled by horizon (§3)
| model | horizon | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-X | 1 | 7729 | 0.3038 | 0.7390 | 0.5804 | -0.2400 | 0.8898 | 0.5016 | 0.0006 |
| HAR-X | 5 | 7709 | 0.2440 | 0.6243 | 0.4714 | -0.1434 | 0.8782 | 0.5103 | 0.0023 |
| HAR-X | 10 | 7663 | 0.2515 | 0.6208 | 0.4675 | -0.1160 | 0.8657 | 0.5011 | 0.0043 |
| HAR-X | 22 | 7581 | 0.2839 | 0.6235 | 0.4725 | -0.0723 | 0.8524 | 0.4757 | 0.0086 |
| HAR-X | 42 | 7440 | 0.3233 | 0.6404 | 0.4826 | -0.0344 | 0.8367 | 0.4664 | 0.0150 |

## §5 IV-incremental skill (per horizon)
| model | horizon | n | slope | t_slope | sign_acc | qlike_model | qlike_iv | qlike_gain_vs_iv |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-X | 1 | 7729 | 0.0709 | 15.4316 | 0.7424 | 0.3038 | 0.3570 | 0.0532 |
| HAR-X | 5 | 7709 | 0.0925 | 15.0746 | 0.7096 | 0.2440 | 0.2620 | 0.0180 |
| HAR-X | 10 | 7663 | 0.1351 | 11.0831 | 0.6708 | 0.2515 | 0.2546 | 0.0031 |
| HAR-X | 22 | 7581 | 0.8783 | 30.6866 | 0.6225 | 0.2839 | 0.2750 | -0.0090 |
| HAR-X | 42 | 7440 | 1.0658 | 58.2346 | 0.6087 | 0.3233 | 0.3178 | -0.0055 |

## §6 Conditional bias by IV-percentile bucket (h=22)
| model | horizon | iv_pctile_bucket | n | qlike | log_bias |
| --- | --- | --- | --- | --- | --- |
| HAR-X | 22 | 0 | 1848 | 0.2980 | -0.1015 |
| HAR-X | 22 | 1 | 1228 | 0.2407 | -0.0728 |
| HAR-X | 22 | 2 | 1335 | 0.2392 | -0.0287 |
| HAR-X | 22 | 3 | 1451 | 0.2453 | -0.1141 |
| HAR-X | 22 | 4 | 1719 | 0.3670 | -0.0391 |

## §6 Post-shock calibration (h=22)
| model | horizon | bias_all | qlike_all | bias_postshock | qlike_postshock | n_postshock | trap_flag |
| --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-X | 22 | -0.0723 | 0.2839 | -0.0665 | 0.3231 | 1410 |  |

## Per-ticker Tier-1 at h=22
| model | horizon | ticker | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-X | 22 | IBIT | 224 | 0.1511 | 0.5680 | 0.4660 | -0.1176 | 0.5000 | 0.2545 | 0.0024 |
| HAR-X | 22 | KRE | 2059 | 0.3452 | 0.5842 | 0.4116 | -0.0514 | 0.9286 | 0.5809 | 0.0017 |
| HAR-X | 22 | MSOS | 1181 | 0.2454 | 0.6114 | 0.4965 | 0.1964 | 0.6952 | 0.3378 | 0.0072 |
| HAR-X | 22 | USO | 2059 | 0.2220 | 0.5436 | 0.3970 | -0.0097 | 0.8402 | 0.4682 | 0.0027 |
| HAR-X | 22 | UVXY | 2058 | 0.3212 | 0.7384 | 0.5960 | -0.3051 | 0.9169 | 0.4810 | 0.0229 |

## Pooled by group
| model | group | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-X | crypto | 1172 | 0.2187 | 0.6989 | 0.5452 | -0.2206 | 0.7193 | 0.3840 | 0.0019 |
| HAR-X | long_volatility_vix | 10320 | 0.3088 | 0.7577 | 0.6090 | -0.3134 | 0.8949 | 0.4766 | 0.0160 |
| HAR-X | oil_and_energy | 10325 | 0.2521 | 0.6151 | 0.4590 | -0.0814 | 0.8444 | 0.4675 | 0.0021 |
| HAR-X | us_cannabis | 5980 | 0.2853 | 0.6264 | 0.4882 | 0.0829 | 0.7804 | 0.4276 | 0.0049 |
| HAR-X | us_cyclicals_sector | 10325 | 0.2869 | 0.5761 | 0.4158 | -0.0789 | 0.9206 | 0.5786 | 0.0012 |
