# MS-HAR — Self Stats
_universe=`hard_cases` · primary horizon h=22 · predictions=`execution/data/predictions/MS-HAR.parquet` · generated 2026-06-04T02:17:08Z_

_Self-only metrics — no leaderboard rank, no DM test, no MCS, no §9 status._
_Cross-model comparison is produced by the final `rv_eval.evaluator` pass._

## Tier-1 pooled by horizon (§3)
| model | horizon | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MS-HAR | 1 | 8153 | 0.3560 | 0.8008 | 0.6276 | -0.2728 | 0.9209 | 0.5755 | 0.0004 |
| MS-HAR | 5 | 8112 | 0.3848 | 0.7580 | 0.5650 | -0.0687 | 0.7263 | 0.3736 | 0.0024 |
| MS-HAR | 10 | 8065 | 0.3817 | 0.7383 | 0.5547 | -0.0495 | 0.6843 | 0.3440 | 0.0046 |
| MS-HAR | 22 | 8005 | 0.4187 | 0.7876 | 0.6037 | -0.0837 | 0.6195 | 0.2912 | 0.0103 |
| MS-HAR | 42 | 7863 | 0.4966 | 0.8021 | 0.6180 | -0.0394 | 0.5607 | 0.2631 | 0.0182 |

## §5 IV-incremental skill (per horizon)
| model | horizon | n | slope | t_slope | sign_acc | qlike_model | qlike_iv | qlike_gain_vs_iv |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MS-HAR | 1 | 7883 | 0.8888 | 23.2377 | 0.6803 | 0.3485 | 0.3594 | 0.0109 |
| MS-HAR | 5 | 7842 | 0.3652 | 14.2672 | 0.6489 | 0.3785 | 0.2619 | -0.1165 |
| MS-HAR | 10 | 7817 | 0.4727 | 20.2572 | 0.6343 | 0.3796 | 0.2539 | -0.1257 |
| MS-HAR | 22 | 7757 | 0.5699 | 32.6686 | 0.5619 | 0.4163 | 0.2731 | -0.1432 |
| MS-HAR | 42 | 7637 | 0.6494 | 46.8346 | 0.5408 | 0.5033 | 0.3129 | -0.1904 |

## §6 Conditional bias by IV-percentile bucket (h=22)
| model | horizon | iv_pctile_bucket | n | qlike | log_bias |
| --- | --- | --- | --- | --- | --- |
| MS-HAR | 22 | 0 | 2059 | 0.4547 | -0.1556 |
| MS-HAR | 22 | 1 | 1262 | 0.3742 | -0.0710 |
| MS-HAR | 22 | 2 | 1355 | 0.3735 | -0.0465 |
| MS-HAR | 22 | 3 | 1460 | 0.3667 | -0.0673 |
| MS-HAR | 22 | 4 | 1727 | 0.4819 | -0.0099 |

## §6 Post-shock calibration (h=22)
| model | horizon | bias_all | qlike_all | bias_postshock | qlike_postshock | n_postshock | trap_flag |
| --- | --- | --- | --- | --- | --- | --- | --- |
| MS-HAR | 22 | -0.0837 | 0.4187 | -0.1284 | 0.3946 | 1482 | ✓ |

## Per-ticker Tier-1 at h=22
| model | horizon | ticker | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MS-HAR | 22 | IBIT | 495 | 0.3078 | 0.9330 | 0.7682 | -0.5991 | 0.4505 | 0.1677 | 0.0071 |
| MS-HAR | 22 | KRE | 2087 | 0.4793 | 0.7618 | 0.5630 | -0.0647 | 0.7298 | 0.3690 | 0.0022 |
| MS-HAR | 22 | MSOS | 1249 | 0.4395 | 0.8110 | 0.6341 | 0.0137 | 0.5372 | 0.2362 | 0.0097 |
| MS-HAR | 22 | USO | 2087 | 0.3317 | 0.7291 | 0.5742 | 0.0023 | 0.5232 | 0.2314 | 0.0036 |
| MS-HAR | 22 | UVXY | 2087 | 0.4588 | 0.8167 | 0.6166 | -0.1247 | 0.6948 | 0.3354 | 0.0261 |

## Pooled by group
| model | group | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MS-HAR | crypto | 2527 | 0.3466 | 0.8734 | 0.6989 | -0.3804 | 0.6363 | 0.3332 | 0.0044 |
| MS-HAR | long_volatility_vix | 10465 | 0.4414 | 0.8325 | 0.6435 | -0.1684 | 0.7495 | 0.3865 | 0.0178 |
| MS-HAR | oil_and_energy | 10465 | 0.3830 | 0.7567 | 0.5876 | -0.0533 | 0.6404 | 0.3159 | 0.0028 |
| MS-HAR | us_cannabis | 6276 | 0.4117 | 0.7833 | 0.5894 | -0.0308 | 0.6334 | 0.3534 | 0.0067 |
| MS-HAR | us_cyclicals_sector | 10465 | 0.4081 | 0.7108 | 0.5271 | -0.0656 | 0.7796 | 0.4287 | 0.0016 |

---

## Model card (human-only fields — MODEL_PLAN §5)

**Model.** MS-HAR (CATALOG §3 model 31, Track E3). 2-state Markov-switching direct-h HAR regression
of `log(target_var)` on `HAR_FEATURES` (+ intercept), state-dependent coefficients + innovation
variance, 2x2 transition matrix; hand-rolled EM (Hamilton filter + Kim smoother). Regime-weighted
mixture-of-two-lognormals predictive density, collapsed to a moment-matched single lognormal for
`_lognormal_quantiles`. File `candidate_models/ms_har.py:MSHAR`, `name="MS-HAR"`. See the
`MS-HAR.md` (clean_core) card for the full spec, EM settings, leakage rule, and refit-cadence
compromise — identical here.

**Regime spec + EM settings.** 2 regimes (frozen), `_MAX_ITER=80`, `_TOL=1e-4`,
`_MIN_REGIME_FRAC=0.05`, `min_obs=120`, `_REFIT_EVERY=6` (full EM every 6th fold per key; warm
reuse + cheap origin-weight refresh otherwise). numpy seed `_SEED=0`.

**Fallback (counted).** Full-history fit proxy (hard_cases): **25/25 (ticker,horizon) keys fitted,
all 25 two-regime, 0 single-regime fallback.** No transient fold-level fallback produced missing
rows.

**Coverage.** hard_cases: all 5 tickers x 5 horizons present, 40,598 OOS rows, span
2018-01-02 .. 2026-05-22. No tickers/horizons uncovered.

**Coverage / calibration warnings.** Severe under-dispersion at longer horizons on the stress
universe: cov90 drops to ~0.56 (h=42) and cov50 to ~0.26 — worse than on clean_core. The
two-moment lognormal collapse of the mixture is the main driver.

**Reproducibility.** numpy 2.4.6, polars 1.41.1, scipy 1.17.1, statsmodels 0.14.6 (not used),
python 3.12.13. Device: macOS arm64 CPU. Wall-time hard_cases walk-forward **132.0s**.

## HARD-GATE VERDICT (hard_cases, self-stats only)

**Verdict: REJECT candidate on hard_cases too.** Direct hard_cases cards for Threshold-HAR/STAR-HAR
were not read by this worker (no cross-model file access beyond the gate), but MS-HAR's hard_cases
pooled QLIKE is **higher (worse)** than its own clean_core QLIKE at every horizon and shows the
same monotone calibration decay, consistent with the clean_core verdict that the EM switching
machinery does not earn its cost. Pooled QLIKE by horizon (hard_cases): h1=0.356, h5=0.385,
h10=0.382, h22=0.419, h42=0.497; cov90 0.56-0.92 (badly under-nominal for h>=5). The human
comparison pass owns the final cross-model rejection.
