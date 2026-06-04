# HARX-HS — Self Stats
_universe=`clean_core` · primary horizon h=22 · predictions=`execution/data/predictions/HARX-HS.parquet` · generated 2026-06-03T17:52:16Z_

_Self-only metrics — no leaderboard rank, no DM test, no MCS, no §9 status._
_Cross-model comparison is produced by the final `rv_eval.evaluator` pass._

## Tier-1 pooled by horizon (§3)
| model | horizon | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HARX-HS | 1 | 20800 | 0.3048 | 0.7051 | 0.5533 | -0.0801 | 0.5970 | 0.2668 | 0.0000 |
| HARX-HS | 5 | 20760 | 0.1896 | 0.5456 | 0.4160 | -0.0251 | 0.6064 | 0.2744 | 0.0002 |
| HARX-HS | 10 | 20710 | 0.2160 | 0.5447 | 0.4021 | -0.0068 | 0.6169 | 0.2822 | 0.0003 |
| HARX-HS | 22 | 20590 | 0.3798 | 0.5902 | 0.4185 | 0.0206 | 0.6194 | 0.2757 | 0.0008 |
| HARX-HS | 42 | 20390 | 0.5258 | 0.6601 | 0.4562 | 0.0395 | 0.6239 | 0.2825 | 0.0016 |

## §5 IV-incremental skill (per horizon)
| model | horizon | n | slope | t_slope | sign_acc | qlike_model | qlike_iv | qlike_gain_vs_iv |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HARX-HS | 1 | 20800 | 0.7441 | 48.3899 | 0.7349 | 0.3048 | 0.3273 | 0.0225 |
| HARX-HS | 5 | 20760 | 0.9621 | 53.3967 | 0.6909 | 0.1896 | 0.2079 | 0.0182 |
| HARX-HS | 10 | 20710 | 0.9413 | 34.5416 | 0.6568 | 0.2160 | 0.2187 | 0.0028 |
| HARX-HS | 22 | 20590 | 0.5407 | 15.6941 | 0.6103 | 0.3798 | 0.3397 | -0.0400 |
| HARX-HS | 42 | 20390 | 0.5757 | 19.2636 | 0.5845 | 0.5258 | 0.4701 | -0.0557 |

## §6 Conditional bias by IV-percentile bucket (h=22)
| model | horizon | iv_pctile_bucket | n | qlike | log_bias |
| --- | --- | --- | --- | --- | --- |
| HARX-HS | 22 | 0 | 5239 | 0.1988 | -0.0077 |
| HARX-HS | 22 | 1 | 3448 | 0.3941 | -0.0289 |
| HARX-HS | 22 | 2 | 3439 | 0.5850 | 0.0097 |
| HARX-HS | 22 | 3 | 3531 | 0.4024 | 0.0350 |
| HARX-HS | 22 | 4 | 4933 | 0.4026 | 0.0824 |

## §6 Post-shock calibration (h=22)
| model | horizon | bias_all | qlike_all | bias_postshock | qlike_postshock | n_postshock | trap_flag |
| --- | --- | --- | --- | --- | --- | --- | --- |
| HARX-HS | 22 | 0.0206 | 0.3798 | 0.0549 | 0.4203 | 3914 |  |

## Per-ticker Tier-1 at h=22
| model | horizon | ticker | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HARX-HS | 22 | EEM | 2059 | 0.2751 | 0.5739 | 0.4198 | 0.0512 | 0.6265 | 0.2608 | 0.0008 |
| HARX-HS | 22 | GLD | 2059 | 0.1514 | 0.4636 | 0.3316 | 0.0431 | 0.5823 | 0.2831 | 0.0004 |
| HARX-HS | 22 | HYG | 2059 | 0.9652 | 0.7554 | 0.5502 | -0.1230 | 0.6469 | 0.2681 | 0.0002 |
| HARX-HS | 22 | IWM | 2059 | 0.3339 | 0.5548 | 0.3876 | 0.1126 | 0.6153 | 0.2725 | 0.0010 |
| HARX-HS | 22 | QQQ | 2059 | 0.3271 | 0.6087 | 0.4399 | 0.0500 | 0.6027 | 0.2914 | 0.0009 |
| HARX-HS | 22 | SPY | 2059 | 0.5103 | 0.6840 | 0.4915 | 0.0656 | 0.6270 | 0.2831 | 0.0007 |
| HARX-HS | 22 | TLT | 2059 | 0.2165 | 0.4783 | 0.3325 | 0.0306 | 0.5542 | 0.2404 | 0.0003 |
| HARX-HS | 22 | XLE | 2059 | 0.2919 | 0.5294 | 0.3672 | -0.0038 | 0.6076 | 0.2768 | 0.0015 |
| HARX-HS | 22 | XLF | 2059 | 0.4052 | 0.6009 | 0.4376 | -0.0364 | 0.6610 | 0.2618 | 0.0011 |
| HARX-HS | 22 | XLK | 2059 | 0.3210 | 0.5933 | 0.4270 | 0.0158 | 0.6702 | 0.3191 | 0.0011 |

## Pooled by group
| model | group | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HARX-HS | emerging_markets | 10325 | 0.3186 | 0.6629 | 0.4937 | 0.0089 | 0.6161 | 0.2704 | 0.0006 |
| HARX-HS | high_yield_credit | 10325 | 0.6642 | 0.7351 | 0.5432 | -0.1195 | 0.6331 | 0.2842 | 0.0001 |
| HARX-HS | oil_and_energy | 10325 | 0.2550 | 0.5362 | 0.3841 | -0.0251 | 0.6084 | 0.2714 | 0.0011 |
| HARX-HS | precious_metals | 10325 | 0.2244 | 0.5893 | 0.4374 | 0.0082 | 0.5934 | 0.2760 | 0.0003 |
| HARX-HS | us_cyclicals_sector | 10325 | 0.3166 | 0.5915 | 0.4351 | -0.0476 | 0.6513 | 0.2885 | 0.0008 |
| HARX-HS | us_large_cap_equity | 20650 | 0.3379 | 0.6426 | 0.4786 | 0.0107 | 0.6036 | 0.2732 | 0.0006 |
| HARX-HS | us_rates_and_ig_credit | 10325 | 0.2166 | 0.5415 | 0.3968 | 0.0030 | 0.5727 | 0.2550 | 0.0002 |
| HARX-HS | us_small_cap_equity | 10325 | 0.2756 | 0.5541 | 0.3981 | 0.0650 | 0.6087 | 0.2772 | 0.0007 |
| HARX-HS | us_technology_sector | 10325 | 0.2772 | 0.5997 | 0.4472 | -0.0209 | 0.6354 | 0.2938 | 0.0008 |

---

## Human-only fields (MODEL_PLAN §5)

**Model.** HARX-HeteroSigma — catalog model 25, Track D, Pattern P2 (`_PerKeyModel`).
File `candidate_models/harx_hs.py`, class `HARXHeteroSigma`, `name="HARX-HS"`.

**Mean model (unchanged from HAR-X).** Per-(ticker, horizon) OLS of `log(target_var)` on an
intercept + `HAR_FEATURES + IV_FEATURES`
(`log_rv_d, log_rv_w, log_rv_m, log_iv, iv_slope, skew_25d, vix, vix3m, vix_slope, vvix`).
`rv_hat = exp(mu + 0.5*s_t^2)` (per-row lognormal mean).

**Hetero-sigma head (the only addition).** Per key, regress `log(resid^2 + eps)` of the mean
model on `[1, log_sqrt_rq, vix, vvix, vix9d_slope]`; predictive log-sd
`s_t = clip( sqrt(exp(b'z_t)), 1e-3, 5.0 )` — a per-row width replacing HAR-X's single
in-sample residual sd. Base `_PerKeyModel.predict` applies `sigma`/lognormal quantiles
elementwise, so the length-n `s_t` needs no harness change.

**Derived columns used.** `log_sqrt_rq` = `log(max(sqrt_rq, 1e-12))`, a **row-wise** transform of
`sqrt_rq` (produced by `build_features`) — no trailing window, so leak-free and computed directly
on the predict slice (no `_AttachMixin` join needed). `vix`, `vvix`, `vix9d_slope` pass through
`build_features` from `inputs.parquet`. Per catalog §4, the IV-variance proxy uses `iv_30d`-derived
features in X, never `targets.iv2`/`post_shock`.

**Frozen hyperparameters + selection note.** No data-driven CV search. The variance-head regressor
set `[log_sqrt_rq, vix, vvix, vix9d_slope]` is fixed by the catalog spec. `eps=1e-12`,
`s_floor=1e-3`, `s_cap=5.0` are numerical-stability constants, not tuned to any split. `min_obs=100`
(inherited HAR-X gate). No OOS or other-model results were peeked.

**Convergence / fallback.** The head is fit by `numpy.linalg.lstsq`; if its design is degenerate or a
regressor is entirely missing for a key it falls back to the homoskedastic HAR-X sd (recorded on
`self.warnings`). On the final full-history fit: **clean_core 50/50 keys fit the head, 0 fallbacks**.

**Coverage.** Full coverage — all 10 clean_core tickers × 5 horizons present; no key dropped or
imputed. cov90≈0.60–0.62 / cov50≈0.27–0.32 pooled: the head widens conditionally but intervals
remain narrower than nominal (a calibration observation for the comparison pass, not a defect).

**Reproducibility.** Deterministic (OLS least-squares, no RNG) — no seed required.
polars 1.41.1, numpy 2.4.6, scipy 1.17.1 (`norm.ppf` via the harness only), Python 3.12.13.
sklearn/arch not used. Device: CPU (Apple Silicon arm64, macOS 15.3.1).
Wall-time: clean_core walk-forward ≈10.2s (104,000 OOS rows).
