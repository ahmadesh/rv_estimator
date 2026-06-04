# HARX-HS — Self Stats
_universe=`hard_cases` · primary horizon h=22 · predictions=`execution/data/predictions/HARX-HS.parquet` · generated 2026-06-03T17:52:17Z_

_Self-only metrics — no leaderboard rank, no DM test, no MCS, no §9 status._
_Cross-model comparison is produced by the final `rv_eval.evaluator` pass._

## Tier-1 pooled by horizon (§3)
| model | horizon | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HARX-HS | 1 | 7729 | 0.3256 | 0.7017 | 0.5384 | -0.0870 | 0.5875 | 0.2661 | 0.0006 |
| HARX-HS | 5 | 7709 | 0.2586 | 0.6034 | 0.4456 | -0.0380 | 0.5697 | 0.2587 | 0.0027 |
| HARX-HS | 10 | 7663 | 0.2674 | 0.6031 | 0.4424 | -0.0168 | 0.5515 | 0.2559 | 0.0049 |
| HARX-HS | 22 | 7581 | 0.3041 | 0.6113 | 0.4500 | 0.0221 | 0.5357 | 0.2424 | 0.0096 |
| HARX-HS | 42 | 7440 | 0.3466 | 0.6335 | 0.4628 | 0.0573 | 0.5413 | 0.2297 | 0.0165 |

## §5 IV-incremental skill (per horizon)
| model | horizon | n | slope | t_slope | sign_acc | qlike_model | qlike_iv | qlike_gain_vs_iv |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HARX-HS | 1 | 7729 | 0.0907 | 15.6874 | 0.7689 | 0.3256 | 0.3570 | 0.0314 |
| HARX-HS | 5 | 7709 | 0.1212 | 15.9793 | 0.7425 | 0.2586 | 0.2620 | 0.0034 |
| HARX-HS | 10 | 7663 | 0.2075 | 13.8376 | 0.7120 | 0.2674 | 0.2546 | -0.0128 |
| HARX-HS | 22 | 7581 | 0.9356 | 35.4312 | 0.6759 | 0.3041 | 0.2750 | -0.0291 |
| HARX-HS | 42 | 7440 | 0.9999 | 59.9062 | 0.6609 | 0.3466 | 0.3178 | -0.0288 |

## §6 Conditional bias by IV-percentile bucket (h=22)
| model | horizon | iv_pctile_bucket | n | qlike | log_bias |
| --- | --- | --- | --- | --- | --- |
| HARX-HS | 22 | 0 | 1848 | 0.3205 | -0.0027 |
| HARX-HS | 22 | 1 | 1228 | 0.2584 | 0.0244 |
| HARX-HS | 22 | 2 | 1335 | 0.2548 | 0.0655 |
| HARX-HS | 22 | 3 | 1451 | 0.2590 | -0.0233 |
| HARX-HS | 22 | 4 | 1719 | 0.3952 | 0.0517 |

## §6 Post-shock calibration (h=22)
| model | horizon | bias_all | qlike_all | bias_postshock | qlike_postshock | n_postshock | trap_flag |
| --- | --- | --- | --- | --- | --- | --- | --- |
| HARX-HS | 22 | 0.0221 | 0.3041 | 0.0194 | 0.3413 | 1410 |  |

## Per-ticker Tier-1 at h=22
| model | horizon | ticker | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HARX-HS | 22 | IBIT | 224 | 0.1529 | 0.5656 | 0.4641 | -0.0926 | 0.3259 | 0.1652 | 0.0028 |
| HARX-HS | 22 | KRE | 2059 | 0.3802 | 0.5835 | 0.3915 | 0.0552 | 0.6105 | 0.2647 | 0.0018 |
| HARX-HS | 22 | MSOS | 1181 | 0.2746 | 0.6336 | 0.5101 | 0.2517 | 0.4725 | 0.2312 | 0.0084 |
| HARX-HS | 22 | USO | 2059 | 0.2343 | 0.5439 | 0.3897 | 0.0511 | 0.5211 | 0.2302 | 0.0030 |
| HARX-HS | 22 | UVXY | 2058 | 0.3311 | 0.6889 | 0.5329 | -0.1592 | 0.5345 | 0.2473 | 0.0253 |

## Pooled by group
| model | group | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HARX-HS | crypto | 1172 | 0.2220 | 0.6678 | 0.5200 | -0.1307 | 0.4369 | 0.1706 | 0.0021 |
| HARX-HS | long_volatility_vix | 10320 | 0.3175 | 0.7064 | 0.5500 | -0.1616 | 0.5491 | 0.2359 | 0.0179 |
| HARX-HS | oil_and_energy | 10325 | 0.2674 | 0.6047 | 0.4431 | 0.0017 | 0.5380 | 0.2442 | 0.0024 |
| HARX-HS | us_cannabis | 5980 | 0.3194 | 0.6354 | 0.4864 | 0.1685 | 0.5199 | 0.2498 | 0.0057 |
| HARX-HS | us_cyclicals_sector | 10325 | 0.3134 | 0.5700 | 0.3944 | 0.0286 | 0.6202 | 0.2818 | 0.0013 |

---

## Human-only fields (MODEL_PLAN §5)

**Model.** HARX-HeteroSigma — catalog model 25, Track D, Pattern P2 (`_PerKeyModel`).
File `candidate_models/harx_hs.py`, class `HARXHeteroSigma`, `name="HARX-HS"`.

**Mean model (unchanged from HAR-X).** Per-(ticker, horizon) OLS of `log(target_var)` on an
intercept + `HAR_FEATURES + IV_FEATURES`. `rv_hat = exp(mu + 0.5*s_t^2)`.

**Hetero-sigma head.** Per key, regress `log(resid^2 + eps)` on `[1, log_sqrt_rq, vix, vvix,
vix9d_slope]`; predictive log-sd `s_t = clip(sqrt(exp(b'z_t)), 1e-3, 5.0)` (per-row). Base
`_PerKeyModel.predict` applies `sigma`/lognormal quantiles elementwise — no harness change.

**Derived columns used.** `log_sqrt_rq` = row-wise `log(max(sqrt_rq,1e-12))` (no window → leak-free,
no `_AttachMixin`). `vix`, `vvix`, `vix9d_slope` pass through from `inputs.parquet`. Uses in-X IV
features only, never `targets.iv2`/`post_shock` (catalog §4).

**Frozen hyperparameters + selection note.** No CV search. Regressor set fixed by catalog spec;
`eps=1e-12`, `s_floor=1e-3`, `s_cap=5.0` are stability constants. `min_obs=100`. No OOS/other-model
peeking.

**Convergence / fallback.** Final full-history fit: **hard_cases 25/25 keys fit the head, 0
fallbacks**. Degenerate-head fallback to homoskedastic HAR-X sd is recorded on `self.warnings` if it
ever triggers.

**Coverage.** Full coverage — all 5 hard_cases tickers × 5 horizons present; no key dropped or
imputed. cov90≈0.54–0.59 pooled (narrower than nominal — a calibration note for the comparison pass).

**Reproducibility.** Deterministic (no RNG, no seed). polars 1.41.1, numpy 2.4.6, scipy 1.17.1,
Python 3.12.13. Device: CPU (Apple Silicon arm64, macOS 15.3.1).
Wall-time: hard_cases walk-forward ≈5.0s (38,497 OOS rows).
