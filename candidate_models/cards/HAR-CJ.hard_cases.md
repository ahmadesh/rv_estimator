# HAR-CJ — Model Card

## Identity
- Model number (from MODEL_PLAN.md): 6
- Class: candidate_models.har_cj:HARCJ
- Tier: Modern HAR
- Implemented by: swarm worker (2026-06-01)

## Configuration
- Features used (by name):
  - `HAR_FEATURES`: `log_rv_d`, `log_rv_w`, `log_rv_m` (pre-baked in features.py)
  - Derived continuous-component log-BV roll-means (built INSIDE har_cj.py from the `bv` column,
    trailing/include-today rolling means per ticker over the full series): `log_bv_d` (w=1, = log(bv)),
    `log_bv_w` (w=5), `log_bv_m` (w=22)
  - Derived jump term (built inside har_cj.py from the `jump` column): `log_jump_d`
  - `bv` and `jump` come from inputs.parquet (setup/measurement.py); features.py is UNTOUCHED.
  - BV/jump are floored at 1e-12 before log (they can be exactly 0), matching features.py.
- Hyperparameters: none (plain per-(ticker, horizon) log-OLS via `_LinearLogHAR`). No tuning.
- HP selection (models 8–11): N/A for model 6.
- Library version(s): python 3.12.13, polars 1.41.1, numpy 2.4.6, scipy 1.17.1
- Random seed: N/A (deterministic OLS)

## Training
- Universes run: clean_core, hard_cases
- Walk-forward folds: 101 monthly-refit folds (shared across both universes)
- Wall-clock time: clean_core 9.2s, hard_cases 4.7s (real)
- Device: cpu
- Convergence notes / per-ticker warnings:
  - No convergence concerns (closed-form least squares).
  - `bv`/`jump` have zero nulls across the inputs panel — no hard-case ticker had BV/jump missing;
    no rows dropped for that reason, none imputed.
  - IBIT short history: 2,713 rows total (517 at h=22); MSOS thin: 6,462 rows total (1,270 at h=22).
    UVXY/USO/KRE full (10,545 rows each). Coverage identical to sibling HAR-RS/HARQ — data-driven,
    not a model drop. hard_cases predictions = 40,810 rows.
- Derived-column injection: HARCJ.fit/predict call `_attach(X)`, which builds the log-BV roll-means +
  log_jump_d ONCE over each ticker's full series (from inputs.parquet) and LEFT-JOINs by (ticker, date)
  — never recomputes rolling means on the per-fold slice (which would null out leading-21 rows and drop
  them). Synthetic-test keys not in inputs.parquet fall back to building straight from X.

# HAR-CJ — Self Stats
_universe=`hard_cases` · primary horizon h=22 · predictions=`execution/data/predictions/HAR-CJ.parquet` · generated 2026-06-01T03:14:55Z_

_Self-only metrics — no leaderboard rank, no DM test, no MCS, no §9 status._
_Cross-model comparison is produced by the final `rv_eval.evaluator` pass._

## Tier-1 pooled by horizon (§3)
| model | horizon | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-CJ | 1 | 8196 | 0.3303 | 0.7476 | 0.5874 | -0.2422 | 0.9024 | 0.5304 | 0.0004 |
| HAR-CJ | 5 | 8153 | 0.2692 | 0.6436 | 0.4891 | -0.1512 | 0.8923 | 0.5236 | 0.0019 |
| HAR-CJ | 10 | 8108 | 0.2784 | 0.6454 | 0.4858 | -0.1363 | 0.8797 | 0.5184 | 0.0039 |
| HAR-CJ | 22 | 8048 | 0.3132 | 0.6526 | 0.4917 | -0.1080 | 0.8672 | 0.4993 | 0.0084 |
| HAR-CJ | 42 | 7905 | 0.3546 | 0.6687 | 0.5013 | -0.0811 | 0.8387 | 0.4810 | 0.0148 |

## §5 IV-incremental skill (per horizon)
| model | horizon | n | slope | t_slope | sign_acc | qlike_model | qlike_iv | qlike_gain_vs_iv |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-CJ | 1 | 7906 | 0.9927 | 29.6625 | 0.7183 | 0.3223 | 0.3595 | 0.0372 |
| HAR-CJ | 5 | 7863 | 0.7513 | 23.0153 | 0.6773 | 0.2654 | 0.2624 | -0.0030 |
| HAR-CJ | 10 | 7838 | 0.7464 | 26.7790 | 0.6360 | 0.2765 | 0.2542 | -0.0223 |
| HAR-CJ | 22 | 7778 | 0.7898 | 38.4965 | 0.5948 | 0.3146 | 0.2732 | -0.0415 |
| HAR-CJ | 42 | 7657 | 0.9032 | 59.0686 | 0.5812 | 0.3614 | 0.3134 | -0.0480 |

## §6 Conditional bias by IV-percentile bucket (h=22)
| model | horizon | iv_pctile_bucket | n | qlike | log_bias |
| --- | --- | --- | --- | --- | --- |
| HAR-CJ | 22 | 0 | 2078 | 0.3265 | -0.2307 |
| HAR-CJ | 22 | 1 | 1264 | 0.2624 | -0.1211 |
| HAR-CJ | 22 | 2 | 1355 | 0.2524 | -0.0679 |
| HAR-CJ | 22 | 3 | 1460 | 0.2718 | -0.0895 |
| HAR-CJ | 22 | 4 | 1727 | 0.4236 | 0.0195 |

## §6 Post-shock calibration (h=22)
| model | horizon | bias_all | qlike_all | bias_postshock | qlike_postshock | n_postshock | trap_flag |
| --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-CJ | 22 | -0.1080 | 0.3132 | -0.1036 | 0.3569 | 1487 |  |

## Per-ticker Tier-1 at h=22
| model | horizon | ticker | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-CJ | 22 | IBIT | 517 | 0.1959 | 0.6880 | 0.5446 | -0.3542 | 0.7408 | 0.4468 | 0.0035 |
| HAR-CJ | 22 | KRE | 2087 | 0.3776 | 0.6059 | 0.4317 | -0.0911 | 0.9401 | 0.5793 | 0.0017 |
| HAR-CJ | 22 | MSOS | 1270 | 0.2446 | 0.6118 | 0.4657 | 0.0619 | 0.8063 | 0.4906 | 0.0066 |
| HAR-CJ | 22 | USO | 2087 | 0.2969 | 0.5970 | 0.4354 | 0.0338 | 0.8222 | 0.4528 | 0.0030 |
| HAR-CJ | 22 | UVXY | 2087 | 0.3359 | 0.7576 | 0.6108 | -0.3092 | 0.9075 | 0.4839 | 0.0229 |

## Pooled by group
| model | group | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-CJ | crypto | 2633 | 0.2899 | 0.8280 | 0.6559 | -0.4538 | 0.8299 | 0.4903 | 0.0026 |
| HAR-CJ | long_volatility_vix | 10465 | 0.3176 | 0.7558 | 0.6094 | -0.2990 | 0.8979 | 0.4923 | 0.0156 |
| HAR-CJ | oil_and_energy | 10465 | 0.3181 | 0.6448 | 0.4795 | -0.0287 | 0.8375 | 0.4597 | 0.0023 |
| HAR-CJ | us_cannabis | 6382 | 0.2846 | 0.6242 | 0.4725 | -0.0155 | 0.8455 | 0.5202 | 0.0046 |
| HAR-CJ | us_cyclicals_sector | 10465 | 0.3106 | 0.5927 | 0.4322 | -0.1061 | 0.9241 | 0.5796 | 0.0012 |
