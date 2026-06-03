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
  - BV/jump are floored at 1e-12 before log (they can be exactly 0 — e.g. a session with no detected
    jump), matching the log-floor convention in features.py.
- Hyperparameters: none (plain per-(ticker, horizon) log-OLS via `_LinearLogHAR`). No tuning.
- HP selection (models 8–11): N/A for model 6.
- Library version(s): python 3.12.13, polars 1.41.1, numpy 2.4.6, scipy 1.17.1
- Random seed: N/A (deterministic OLS; no stochastic component)

## Training
- Universes run: clean_core, hard_cases
- Walk-forward folds: 101 monthly-refit folds (shared across both universes)
- Wall-clock time: clean_core 9.2s, hard_cases 4.7s (real time; user/sys higher due to polars threads)
- Device: cpu
- Convergence notes / per-ticker warnings:
  - No convergence concerns (closed-form least squares).
  - `bv` and `jump` have zero nulls across the entire inputs panel — no ticker had BV/jump missing,
    so NO rows were dropped for that reason (none imputed either).
  - IBIT covered only from ~2024 (short options/RV history): 2,713 rows total, 517 at h=22. MSOS thin:
    6,462 rows total, 1,270 at h=22. These coverage limits are identical to sibling HAR-family models
    (HAR-RS / HARQ) and are purely a data-availability effect, not a model drop.
  - Full coverage of all 15 scored tickers × 5 horizons; total predictions = 146,260 rows
    (105,450 clean_core + 40,810 hard_cases).
- How the derived columns were injected into X: HARCJ overrides `fit`/`predict` to call `_attach(X)`
  before delegating to `super()`. `_attach` builds the log-BV roll-means + log_jump_d ONCE over each
  ticker's FULL series (from inputs.parquet) and LEFT-JOINs them onto the X slice by (ticker, date).
  Joining (rather than recomputing on the per-fold slice) is essential: the walk-forward hands
  fit/predict only a train slice or a one-month test slice, so a rolling_mean(22) computed on that
  slice alone would be null for its leading 21 rows and those rows would be dropped at predict
  (NaN propagates through `_LinearLogHAR._design`). The first build attempt computed on the slice and
  produced only ~41 unique OOS dates; the join fix restores full ~2,109-date coverage matching HAR-RS.
  If X carries (ticker, date) keys absent from inputs.parquet (the synthetic smoke test), `_attach`
  falls back to building the table straight from X, which there IS the full series.

# HAR-CJ — Self Stats
_universe=`clean_core` · primary horizon h=22 · predictions=`execution/data/predictions/HAR-CJ.parquet` · generated 2026-06-01T03:14:55Z_

_Self-only metrics — no leaderboard rank, no DM test, no MCS, no §9 status._
_Cross-model comparison is produced by the final `rv_eval.evaluator` pass._

## Tier-1 pooled by horizon (§3)
| model | horizon | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-CJ | 1 | 21080 | 0.3043 | 0.7367 | 0.5853 | -0.1933 | 0.8923 | 0.5012 | 0.0000 |
| HAR-CJ | 5 | 21040 | 0.2057 | 0.5844 | 0.4507 | -0.1044 | 0.9009 | 0.5297 | 0.0002 |
| HAR-CJ | 10 | 20990 | 0.2257 | 0.5876 | 0.4478 | -0.1023 | 0.9067 | 0.5558 | 0.0003 |
| HAR-CJ | 22 | 20870 | 0.3451 | 0.6396 | 0.4755 | -0.1222 | 0.9142 | 0.5738 | 0.0008 |
| HAR-CJ | 42 | 20670 | 0.4716 | 0.7156 | 0.5154 | -0.1436 | 0.9190 | 0.5945 | 0.0015 |

## §5 IV-incremental skill (per horizon)
| model | horizon | n | slope | t_slope | sign_acc | qlike_model | qlike_iv | qlike_gain_vs_iv |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-CJ | 1 | 20820 | 1.3157 | 46.2028 | 0.6760 | 0.3044 | 0.3276 | 0.0232 |
| HAR-CJ | 5 | 20780 | 0.6871 | 25.4168 | 0.6244 | 0.2063 | 0.2079 | 0.0016 |
| HAR-CJ | 10 | 20730 | 0.4046 | 13.7743 | 0.5785 | 0.2269 | 0.2187 | -0.0082 |
| HAR-CJ | 22 | 20610 | 0.1460 | 5.0927 | 0.5320 | 0.3472 | 0.3396 | -0.0076 |
| HAR-CJ | 42 | 20410 | 0.2667 | 9.1733 | 0.5120 | 0.4760 | 0.4697 | -0.0064 |

## §6 Conditional bias by IV-percentile bucket (h=22)
| model | horizon | iv_pctile_bucket | n | qlike | log_bias |
| --- | --- | --- | --- | --- | --- |
| HAR-CJ | 22 | 0 | 5500 | 0.1802 | -0.1694 |
| HAR-CJ | 22 | 1 | 3449 | 0.3301 | -0.1457 |
| HAR-CJ | 22 | 2 | 3439 | 0.4909 | -0.1139 |
| HAR-CJ | 22 | 3 | 3533 | 0.3947 | -0.0974 |
| HAR-CJ | 22 | 4 | 4949 | 0.4020 | -0.0768 |

## §6 Post-shock calibration (h=22)
| model | horizon | bias_all | qlike_all | bias_postshock | qlike_postshock | n_postshock | trap_flag |
| --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-CJ | 22 | -0.1222 | 0.3451 | -0.1694 | 0.4237 | 3986 |  |

## Per-ticker Tier-1 at h=22
| model | horizon | ticker | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-CJ | 22 | EEM | 2087 | 0.2533 | 0.6007 | 0.4648 | -0.1647 | 0.9483 | 0.6814 | 0.0007 |
| HAR-CJ | 22 | GLD | 2087 | 0.1680 | 0.5092 | 0.3843 | -0.0727 | 0.8721 | 0.5137 | 0.0003 |
| HAR-CJ | 22 | HYG | 2087 | 0.7196 | 0.9555 | 0.7775 | -0.5582 | 0.9713 | 0.6689 | 0.0002 |
| HAR-CJ | 22 | IWM | 2087 | 0.3051 | 0.5752 | 0.4236 | -0.0350 | 0.9018 | 0.5180 | 0.0010 |
| HAR-CJ | 22 | QQQ | 2087 | 0.2961 | 0.6066 | 0.4597 | -0.0710 | 0.9291 | 0.6411 | 0.0008 |
| HAR-CJ | 22 | SPY | 2087 | 0.4506 | 0.7117 | 0.5480 | -0.0914 | 0.8874 | 0.5065 | 0.0007 |
| HAR-CJ | 22 | TLT | 2087 | 0.2251 | 0.5060 | 0.3599 | 0.0115 | 0.8836 | 0.4940 | 0.0003 |
| HAR-CJ | 22 | XLE | 2087 | 0.3237 | 0.5468 | 0.3792 | -0.0215 | 0.9138 | 0.5918 | 0.0015 |
| HAR-CJ | 22 | XLF | 2087 | 0.3987 | 0.6590 | 0.5132 | -0.2013 | 0.9329 | 0.5573 | 0.0010 |
| HAR-CJ | 22 | XLK | 2087 | 0.3106 | 0.6021 | 0.4450 | -0.0178 | 0.9023 | 0.5654 | 0.0011 |

## Pooled by group
| model | group | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-CJ | emerging_markets | 10465 | 0.3007 | 0.6883 | 0.5346 | -0.1712 | 0.9269 | 0.6056 | 0.0005 |
| HAR-CJ | high_yield_credit | 10465 | 0.5579 | 0.8954 | 0.7154 | -0.4527 | 0.9531 | 0.6304 | 0.0001 |
| HAR-CJ | oil_and_energy | 10465 | 0.2776 | 0.5529 | 0.3956 | -0.0430 | 0.9057 | 0.5622 | 0.0011 |
| HAR-CJ | precious_metals | 10465 | 0.2272 | 0.6367 | 0.4873 | -0.1403 | 0.8742 | 0.4879 | 0.0003 |
| HAR-CJ | us_cyclicals_sector | 10465 | 0.3253 | 0.6440 | 0.4958 | -0.1916 | 0.9250 | 0.5678 | 0.0008 |
| HAR-CJ | us_large_cap_equity | 20930 | 0.3201 | 0.6595 | 0.5051 | -0.0978 | 0.9014 | 0.5489 | 0.0006 |
| HAR-CJ | us_rates_and_ig_credit | 10465 | 0.2218 | 0.5643 | 0.4187 | -0.0318 | 0.8851 | 0.5000 | 0.0002 |
| HAR-CJ | us_small_cap_equity | 10465 | 0.2684 | 0.5788 | 0.4301 | -0.0558 | 0.8944 | 0.5200 | 0.0007 |
| HAR-CJ | us_technology_sector | 10465 | 0.2800 | 0.6123 | 0.4620 | -0.0498 | 0.8983 | 0.5361 | 0.0008 |
