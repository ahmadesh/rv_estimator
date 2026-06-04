# HAR-GARCH — Self Stats
_universe=`hard_cases` · primary horizon h=22 · predictions=`execution/data/predictions/HAR-GARCH.parquet` · generated 2026-06-03T21:59:10Z_

_Self-only metrics — no leaderboard rank, no DM test, no MCS, no §9 status._
_Cross-model comparison is produced by the final `rv_eval.evaluator` pass._

## Tier-1 pooled by horizon (§3)
| model | horizon | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-GARCH | 1 | 8196 | 0.3469 | 0.7803 | 0.6116 | -0.2604 | 0.8975 | 0.5144 | 0.0004 |
| HAR-GARCH | 5 | 8153 | 0.2787 | 0.6689 | 0.5089 | -0.1768 | 0.8835 | 0.5059 | 0.0019 |
| HAR-GARCH | 10 | 8108 | 0.2837 | 0.6642 | 0.5019 | -0.1502 | 0.8566 | 0.4878 | 0.0040 |
| HAR-GARCH | 22 | 8048 | 0.3099 | 0.6786 | 0.5179 | -0.1384 | 0.8463 | 0.4689 | 0.0087 |
| HAR-GARCH | 42 | 7905 | 0.3320 | 0.6788 | 0.5135 | -0.1056 | 0.8158 | 0.4441 | 0.0152 |

## §5 IV-incremental skill (per horizon)
| model | horizon | n | slope | t_slope | sign_acc | qlike_model | qlike_iv | qlike_gain_vs_iv |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-GARCH | 1 | 7906 | 0.8754 | 24.7700 | 0.6886 | 0.3390 | 0.3595 | 0.0205 |
| HAR-GARCH | 5 | 7863 | 0.7374 | 24.0150 | 0.6487 | 0.2755 | 0.2624 | -0.0131 |
| HAR-GARCH | 10 | 7838 | 0.7619 | 28.2730 | 0.6127 | 0.2794 | 0.2542 | -0.0252 |
| HAR-GARCH | 22 | 7778 | 0.4511 | 28.0889 | 0.5594 | 0.3086 | 0.2732 | -0.0355 |
| HAR-GARCH | 42 | 7657 | 0.8101 | 55.9569 | 0.5584 | 0.3374 | 0.3134 | -0.0239 |

## §6 Conditional bias by IV-percentile bucket (h=22)
| model | horizon | iv_pctile_bucket | n | qlike | log_bias |
| --- | --- | --- | --- | --- | --- |
| HAR-GARCH | 22 | 0 | 2078 | 0.3256 | -0.2378 |
| HAR-GARCH | 22 | 1 | 1264 | 0.2642 | -0.1484 |
| HAR-GARCH | 22 | 2 | 1355 | 0.2626 | -0.0854 |
| HAR-GARCH | 22 | 3 | 1460 | 0.2713 | -0.1133 |
| HAR-GARCH | 22 | 4 | 1727 | 0.3899 | -0.0287 |

## §6 Post-shock calibration (h=22)
| model | horizon | bias_all | qlike_all | bias_postshock | qlike_postshock | n_postshock | trap_flag |
| --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-GARCH | 22 | -0.1384 | 0.3099 | -0.1867 | 0.3245 | 1487 |  |

## Per-ticker Tier-1 at h=22
| model | horizon | ticker | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-GARCH | 22 | IBIT | 517 | 0.2279 | 0.7709 | 0.6419 | -0.5029 | 0.7060 | 0.4023 | 0.0041 |
| HAR-GARCH | 22 | KRE | 2087 | 0.3544 | 0.6120 | 0.4420 | -0.0725 | 0.8955 | 0.4916 | 0.0018 |
| HAR-GARCH | 22 | MSOS | 1270 | 0.2784 | 0.6568 | 0.4981 | 0.0368 | 0.7850 | 0.5016 | 0.0071 |
| HAR-GARCH | 22 | USO | 2087 | 0.2677 | 0.6037 | 0.4527 | -0.0084 | 0.8117 | 0.4097 | 0.0029 |
| HAR-GARCH | 22 | UVXY | 2087 | 0.3469 | 0.7919 | 0.6404 | -0.3507 | 0.9037 | 0.5022 | 0.0235 |

## Pooled by group
| model | group | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-GARCH | crypto | 2633 | 0.3098 | 0.8437 | 0.6837 | -0.4932 | 0.8333 | 0.4577 | 0.0027 |
| HAR-GARCH | long_volatility_vix | 10465 | 0.3256 | 0.7750 | 0.6211 | -0.3071 | 0.8710 | 0.4757 | 0.0159 |
| HAR-GARCH | oil_and_energy | 10465 | 0.3030 | 0.6734 | 0.5108 | -0.0943 | 0.8332 | 0.4433 | 0.0022 |
| HAR-GARCH | us_cannabis | 6382 | 0.3155 | 0.6701 | 0.5004 | -0.0418 | 0.8413 | 0.5265 | 0.0050 |
| HAR-GARCH | us_cyclicals_sector | 10465 | 0.2987 | 0.6020 | 0.4414 | -0.0933 | 0.8951 | 0.5159 | 0.0013 |

---

## Model build notes (human-only fields, MODEL_PLAN §5)

**Model.** HAR-GARCH (catalog model 26, Track D, Pattern P2). File
`candidate_models/har_garch.py`, class `HARGARCH`, base `_PerKeyModel`. Fit per
`(ticker, horizon)`.

**Mean model.** Direct-h log-OLS HAR: `log(target_var) ~ 1 + log_rv_d + log_rv_w + log_rv_m`
(`needs = HAR_FEATURES`). `rv_hat = exp(mu + 0.5*s_t^2)` (lognormal mean).

**Variance model (GARCH spec — frozen by catalog, no OOS tuning).** `arch` GARCH on the
HAR **log-residual** series:
- `mean="Zero"`, `vol="GARCH"`, `p=1`, `q=1`, `dist="normal"`.
- Asymmetry order `o ∈ {0, 1}` (GARCH(1,1) vs GJR-GARCH(1,1,1)) chosen per (ticker,h) on
  **TRAIN-only BIC** — no OOS leakage.
- Residuals scaled ×100 (`rescale=False`); predictive log-sd `s_t` = sqrt of the h-step
  conditional-variance forecast from the last train origin (constant within a monthly
  refit block; never peeks at test residuals). `s_t` tethered to `[0.1×,10×]` of the OLS
  resid sd, clipped to `[1e-3, 5.0]`.

**Fit settings.** `fit(disp="off", show_warning=False, options={"maxiter": 200})`, warnings
silenced, every fit in try/except. `min_obs = 100`.

**Fallback discipline + count.** GARCH fit failure / degenerate residuals ⇒ fall back to
the constant HAR in-sample residual sd (counted in `self.fallbacks`); a single
non-convergent key never aborts the run.
- On the final full-history fold (representative): **hard_cases — 25/25 keys fitted, 0
  fallbacks**; spec mix = 18× GARCH(1,1), 7× GJR-GARCH(1,1,1). No (ticker,horizon) fell
  back. (Hard-case tickers IBIT/MSOS/UVXY have shorter histories but still exceed the
  50-obs residual minimum on every OOS fold; run-level fallbacks are near zero.)

**Refit frequency.** Harness default (monthly, expanding). Full per-(ticker,h) arch refit
every fold — no reduction needed.

**Coverage.** Hard-case names (UVXY especially) are the stress set; intervals are wider
and the HAR mean bias more pronounced than clean_core. Inspect the per-ticker rows above
for UVXY/MSOS/IBIT calibration. The GARCH layer adds the time-varying widening; residual
mean bias is HAR-inherited, not GARCH-induced.

**Reproducibility.** No stochasticity (analytic GARCH h-step forecast, deterministic
optimiser).

**Environment.** arch 8.0.0, numpy 2.4.6, polars 1.41.1, scipy 1.17.1, Python 3.12.13.
Device: macOS-15.3.1 arm64 (Apple Silicon), CPU only.

**Wall-time.** hard_cases walk-forward: **45.6 s** (clean_core: 145.0 s). OOS predictions:
hard_cases 40,810 rows (span 2018-01-02 → 2026-05-22).

**Coverage gaps.** None — all 5 hard_cases tickers (IBIT, KRE, MSOS, USO, UVXY) covered at
all five horizons.
