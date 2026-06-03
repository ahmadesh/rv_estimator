# HAR-RS-IV-Q — Model Card (hard_cases)

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
- HP selection (models 8–11): N/A — model 7 has no free hyperparameters; not tuned.
- Library version(s): python 3.12.13, numpy 2.4.6, scipy 1.17.1, polars 1.41.1.
- Random seed: N/A (deterministic OLS via `numpy.linalg.lstsq`).

## Training
- Universes run: clean_core, hard_cases (this card: hard_cases = UVXY, MSOS, IBIT, USO, KRE).
- Refit cadence / protocol: monthly refit, expanding window, OOS_START=2018-01-01.
- Wall-clock time: hard_cases ≈ 5 s (clean_core ≈ 10 s).
- Device: cpu (Apple Silicon, macOS-15.3.1-arm64).
- OOS rows (hard_cases): 38,497. Per ticker: KRE 10,400 · USO 10,400 · UVXY 10,395 · MSOS 6,055 · IBIT 1,247. All 5 horizons (1,5,10,22,42).
- Convergence notes / per-ticker warnings:
  - No fit failures; OLS converged for every (ticker, horizon).
  - **IV-feature nulls drop rows (never imputed):** rows where any IV feature
    (`log_iv, iv_slope, skew_25d, vix, vix3m, vix_slope, vvix`) is null are excluded from fit
    and predict. Effect on hard cases:
    - **IBIT** — only 2025-05-01 → 2026-05-21 (1,247 rows; ~1y options/IV history). Earlier OOS dates dropped, never imputed.
    - **MSOS** — only 2021-06-01 → 2026-05-21 (6,055 rows; thin/late IV coverage). Earlier dates dropped, never imputed.
    - UVXY/USO/KRE — near-full coverage.

---

# HAR-RS-IV-Q — Self Stats
_universe=`hard_cases` · primary horizon h=22 · predictions=`execution/data/predictions/HAR-RS-IV-Q.parquet` · generated 2026-06-01T03:18:25Z_

_Self-only metrics — no leaderboard rank, no DM test, no MCS, no §9 status._
_Cross-model comparison is produced by the final `rv_eval.evaluator` pass._

## Tier-1 pooled by horizon (§3)
| model | horizon | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-RS-IV-Q | 1 | 7729 | 0.3094 | 0.7469 | 0.5847 | -0.2419 | 0.8880 | 0.4971 | 0.0006 |
| HAR-RS-IV-Q | 5 | 7709 | 0.2621 | 0.6331 | 0.4755 | -0.1444 | 0.8733 | 0.5072 | 0.0023 |
| HAR-RS-IV-Q | 10 | 7663 | 0.2578 | 0.6373 | 0.4735 | -0.1233 | 0.8592 | 0.4976 | 0.0052 |
| HAR-RS-IV-Q | 22 | 7581 | 0.2901 | 0.6341 | 0.4754 | -0.0748 | 0.8524 | 0.4743 | 0.0092 |
| HAR-RS-IV-Q | 42 | 7440 | 0.3391 | 0.6716 | 0.4915 | -0.0339 | 0.8323 | 0.4667 | 0.0314 |

## §5 IV-incremental skill (per horizon)
| model | horizon | n | slope | t_slope | sign_acc | qlike_model | qlike_iv | qlike_gain_vs_iv |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-RS-IV-Q | 1 | 7729 | 0.0640 | 13.3644 | 0.7425 | 0.3094 | 0.3570 | 0.0477 |
| HAR-RS-IV-Q | 5 | 7709 | 0.0934 | 14.0543 | 0.7076 | 0.2621 | 0.2620 | -0.0000 |
| HAR-RS-IV-Q | 10 | 7663 | 0.0060 | 1.1910 | 0.6633 | 0.2578 | 0.2546 | -0.0032 |
| HAR-RS-IV-Q | 22 | 7581 | 0.1501 | 10.4215 | 0.6200 | 0.2901 | 0.2750 | -0.0151 |
| HAR-RS-IV-Q | 42 | 7440 | -0.0006 | -0.7131 | 0.6117 | 0.3391 | 0.3178 | -0.0213 |

## §6 Conditional bias by IV-percentile bucket (h=22)
| model | horizon | iv_pctile_bucket | n | qlike | log_bias |
| --- | --- | --- | --- | --- | --- |
| HAR-RS-IV-Q | 22 | 0 | 1848 | 0.3000 | -0.1029 |
| HAR-RS-IV-Q | 22 | 1 | 1228 | 0.2405 | -0.0706 |
| HAR-RS-IV-Q | 22 | 2 | 1335 | 0.2445 | -0.0299 |
| HAR-RS-IV-Q | 22 | 3 | 1451 | 0.2518 | -0.1136 |
| HAR-RS-IV-Q | 22 | 4 | 1719 | 0.3828 | -0.0496 |

## §6 Post-shock calibration (h=22)
| model | horizon | bias_all | qlike_all | bias_postshock | qlike_postshock | n_postshock | trap_flag |
| --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-RS-IV-Q | 22 | -0.0748 | 0.2901 | -0.0842 | 0.3509 | 1410 |  |

## Per-ticker Tier-1 at h=22
| model | horizon | ticker | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-RS-IV-Q | 22 | IBIT | 224 | 0.1588 | 0.5927 | 0.4781 | -0.1387 | 0.5045 | 0.2679 | 0.0026 |
| HAR-RS-IV-Q | 22 | KRE | 2059 | 0.3477 | 0.5863 | 0.4102 | -0.0491 | 0.9281 | 0.5818 | 0.0017 |
| HAR-RS-IV-Q | 22 | MSOS | 1181 | 0.2533 | 0.6249 | 0.5025 | 0.1912 | 0.6994 | 0.3201 | 0.0075 |
| HAR-RS-IV-Q | 22 | USO | 2059 | 0.2329 | 0.5716 | 0.4037 | -0.0180 | 0.8388 | 0.4658 | 0.0046 |
| HAR-RS-IV-Q | 22 | UVXY | 2058 | 0.3252 | 0.7404 | 0.5965 | -0.3030 | 0.9159 | 0.4864 | 0.0231 |

## Pooled by group
| model | group | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-RS-IV-Q | crypto | 1172 | 0.2198 | 0.7089 | 0.5493 | -0.2254 | 0.7142 | 0.3669 | 0.0019 |
| HAR-RS-IV-Q | long_volatility_vix | 10320 | 0.3122 | 0.7600 | 0.6104 | -0.3120 | 0.8923 | 0.4744 | 0.0162 |
| HAR-RS-IV-Q | oil_and_energy | 10325 | 0.2616 | 0.6487 | 0.4669 | -0.0918 | 0.8425 | 0.4680 | 0.0148 |
| HAR-RS-IV-Q | us_cannabis | 5980 | 0.3261 | 0.6562 | 0.5046 | 0.0823 | 0.7676 | 0.4151 | 0.0052 |
| HAR-RS-IV-Q | us_cyclicals_sector | 10325 | 0.2886 | 0.5779 | 0.4157 | -0.0782 | 0.9199 | 0.5804 | 0.0012 |
