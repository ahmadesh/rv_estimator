# MS-HAR — Self Stats
_universe=`clean_core` · primary horizon h=22 · predictions=`execution/data/predictions/MS-HAR.parquet` · generated 2026-06-04T02:17:08Z_

_Self-only metrics — no leaderboard rank, no DM test, no MCS, no §9 status._
_Cross-model comparison is produced by the final `rv_eval.evaluator` pass._

## Tier-1 pooled by horizon (§3)
| model | horizon | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MS-HAR | 1 | 21080 | 0.3256 | 0.8070 | 0.6420 | -0.2763 | 0.9085 | 0.5286 | 0.0000 |
| MS-HAR | 5 | 21040 | 0.2712 | 0.6941 | 0.5360 | -0.0818 | 0.7885 | 0.4321 | 0.0002 |
| MS-HAR | 10 | 20990 | 0.2916 | 0.7129 | 0.5336 | -0.0617 | 0.7825 | 0.4182 | 0.0004 |
| MS-HAR | 22 | 20870 | 0.3704 | 0.8181 | 0.6080 | -0.1308 | 0.7592 | 0.3792 | 0.0009 |
| MS-HAR | 42 | 20670 | 0.7045 | 0.9164 | 0.6485 | -0.1169 | 0.7417 | 0.3621 | 0.0020 |

## §5 IV-incremental skill (per horizon)
| model | horizon | n | slope | t_slope | sign_acc | qlike_model | qlike_iv | qlike_gain_vs_iv |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MS-HAR | 1 | 20820 | 0.7645 | 53.1370 | 0.6209 | 0.3254 | 0.3276 | 0.0023 |
| MS-HAR | 5 | 20780 | 0.7378 | 45.9611 | 0.5909 | 0.2718 | 0.2079 | -0.0639 |
| MS-HAR | 10 | 20730 | 0.2733 | 21.0429 | 0.5862 | 0.2928 | 0.2187 | -0.0741 |
| MS-HAR | 22 | 20610 | 0.0875 | 7.3169 | 0.5275 | 0.3717 | 0.3396 | -0.0321 |
| MS-HAR | 42 | 20410 | -0.0129 | -2.1430 | 0.5091 | 0.7112 | 0.4697 | -0.2415 |

## §6 Conditional bias by IV-percentile bucket (h=22)
| model | horizon | iv_pctile_bucket | n | qlike | log_bias |
| --- | --- | --- | --- | --- | --- |
| MS-HAR | 22 | 0 | 5500 | 0.2331 | -0.1036 |
| MS-HAR | 22 | 1 | 3449 | 0.3192 | -0.1302 |
| MS-HAR | 22 | 2 | 3439 | 0.3993 | -0.1196 |
| MS-HAR | 22 | 3 | 3533 | 0.4590 | -0.1610 |
| MS-HAR | 22 | 4 | 4949 | 0.4753 | -0.1475 |

## §6 Post-shock calibration (h=22)
| model | horizon | bias_all | qlike_all | bias_postshock | qlike_postshock | n_postshock | trap_flag |
| --- | --- | --- | --- | --- | --- | --- | --- |
| MS-HAR | 22 | -0.1308 | 0.3704 | -0.2458 | 0.4457 | 3986 |  |

## Per-ticker Tier-1 at h=22
| model | horizon | ticker | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MS-HAR | 22 | EEM | 2087 | 0.2901 | 0.8215 | 0.6097 | -0.1944 | 0.8553 | 0.4691 | 0.0009 |
| MS-HAR | 22 | GLD | 2087 | 0.2311 | 0.6166 | 0.4802 | -0.0134 | 0.6253 | 0.2731 | 0.0005 |
| MS-HAR | 22 | HYG | 2087 | 0.6971 | 1.2943 | 0.9849 | -0.4642 | 0.9454 | 0.4581 | 0.0003 |
| MS-HAR | 22 | IWM | 2087 | 0.2971 | 0.6808 | 0.5447 | -0.0832 | 0.7063 | 0.3115 | 0.0011 |
| MS-HAR | 22 | QQQ | 2087 | 0.3799 | 0.8622 | 0.6546 | -0.1752 | 0.8495 | 0.4868 | 0.0011 |
| MS-HAR | 22 | SPY | 2087 | 0.4901 | 0.8539 | 0.6598 | -0.0911 | 0.7053 | 0.3517 | 0.0008 |
| MS-HAR | 22 | TLT | 2087 | 0.2762 | 0.5882 | 0.4316 | -0.0443 | 0.7302 | 0.3828 | 0.0004 |
| MS-HAR | 22 | XLE | 2087 | 0.3011 | 0.6629 | 0.4985 | -0.0299 | 0.7350 | 0.3464 | 0.0018 |
| MS-HAR | 22 | XLF | 2087 | 0.3624 | 0.7964 | 0.5978 | -0.1653 | 0.7580 | 0.4011 | 0.0013 |
| MS-HAR | 22 | XLK | 2087 | 0.3790 | 0.7794 | 0.6181 | -0.0466 | 0.6818 | 0.3115 | 0.0014 |

## Pooled by group
| model | group | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MS-HAR | emerging_markets | 10465 | 0.3550 | 0.8624 | 0.6552 | -0.2453 | 0.8730 | 0.4837 | 0.0007 |
| MS-HAR | high_yield_credit | 10465 | 0.7399 | 1.1034 | 0.7940 | -0.3736 | 0.9419 | 0.5161 | 0.0003 |
| MS-HAR | oil_and_energy | 10465 | 0.3236 | 0.6501 | 0.4851 | -0.0447 | 0.7810 | 0.4084 | 0.0014 |
| MS-HAR | precious_metals | 10465 | 0.3102 | 0.7435 | 0.5815 | -0.0883 | 0.6792 | 0.3194 | 0.0003 |
| MS-HAR | us_cyclicals_sector | 10465 | 0.3953 | 0.7629 | 0.5704 | -0.1322 | 0.8001 | 0.4522 | 0.0010 |
| MS-HAR | us_large_cap_equity | 20930 | 0.4165 | 0.8147 | 0.6221 | -0.1227 | 0.8032 | 0.4445 | 0.0007 |
| MS-HAR | us_rates_and_ig_credit | 10465 | 0.2639 | 0.6424 | 0.4851 | -0.0669 | 0.7748 | 0.4077 | 0.0003 |
| MS-HAR | us_small_cap_equity | 10465 | 0.3288 | 0.6821 | 0.5266 | -0.0669 | 0.7513 | 0.3740 | 0.0008 |
| MS-HAR | us_technology_sector | 10465 | 0.3664 | 0.7544 | 0.5923 | -0.0732 | 0.7559 | 0.3930 | 0.0010 |

---

## Model card (human-only fields — MODEL_PLAN §5)

**Model.** MS-HAR (CATALOG §3 model 31, Track E3). A direct-h HAR regression of
`log(target_var)` on `HAR_FEATURES = [log_rv_d, log_rv_w, log_rv_m]` (+ intercept) whose
**regression coefficients and innovation variance switch between two latent regimes** driven by a
first-order 2-state Markov chain (2x2 transition matrix `P`). Estimated per (ticker, horizon) by a
hand-rolled **EM** (Hamilton-1989 forward filter + Kim-1994 smoother in the E-step; weighted-LS
coefficient + weighted-variance updates and smoothed-joint transition update in the M-step). The
predictive density is the **regime-probability-weighted mixture of two lognormals**; the emitted
`rv_hat`/`sigma` are the mixture's first two level moments, and `q05..q95` are
`_lognormal_quantiles` of a single lognormal matched to those two moments (monotone by
construction). Pattern P3 (bespoke fit) implemented via `_PerKeyModel`'s per-key loop + the
lognormal emission. File `candidate_models/ms_har.py:MSHAR`, `name="MS-HAR"`.

**Regime spec + EM settings (frozen, not OOS-tuned).** Regimes = **2** (fixed by the catalog
spec). EM iteration cap `_MAX_ITER = 80` with relative log-likelihood tolerance early-stop
`_TOL = 1e-4`. Innovation-variance floor `_VAR_FLOOR = 1e-6`; emitted-log-sd floor
`_S_FLOOR = 1e-3`. Init: pooled-OLS residual median-split seeds the two regimes;
`P0 = [[0.95,0.05],[0.10,0.90]]`, `pi0 = [0.5,0.5]`. A regime that ever holds
`< _MIN_REGIME_FRAC = 0.05` of smoothed mass during EM is declared **degenerate** and triggers the
single-regime fallback. `min_obs = 120` train rows to attempt a fit.

**LEAKAGE / state rule.** All regime params + `P` are estimated on the TRAIN slice only. The
predictive regime weights `w` are the smoothed state probabilities of the **last train row**
propagated one Markov step forward (`w = pi_last`, refreshed at each origin); `w` is shared across
all predict rows of a (ticker,h) — it is the only point-in-time-legal origin information. HAR
features pass through `build_features` (no recompute on the predict slice). `post_shock`/`iv2`
(targets-only) are not used.

**Single-regime fallback (counted).** On EM non-convergence, a degenerate/empty regime, a
non-finite likelihood, or any numerical exception, the (ticker,horizon) FALLS BACK to a
single-regime HAR (plain log-OLS, lognormal-mean forecast) and is recorded on `self.fallbacks`.
**Full-history fit proxy (clean_core):** 50/50 (ticker,horizon) keys fitted; **49 two-regime, 1
single-regime fallback** (one degenerate-regime key). Within the monthly walk-forward, early
short-history folds may trigger additional transient single-regime fallbacks (counted per fold);
none produced missing rows — all 10 tickers x 5 horizons are present in OOS.

**REFIT-CADENCE REDUCTION (documented speed compromise).** A full EM is too costly to repeat for
every monthly walk-forward fold (~100 folds x 50 keys). A full EM is therefore re-run only every
`_REFIT_EVERY = 6` fit-calls per (ticker,horizon); intervening folds **reuse the last-good warm
betas/`s2`/`P`** and refresh only the cheap predictive origin weights `w` via a single
Hamilton-filter forward pass over the new (expanding) train tail (no M-step). This keeps the
predictive mixture adapting to the latest origin while amortizing the EM cost roughly 6x. The
betas/transition matrix thus lag by up to 5 monthly refits between full EMs. `_REFIT_EVERY` is
frozen in the source, never selected on OOS. Single-EM cost (largest slice, SPY h=22, n=5669):
**0.37s**.

**Coverage.** clean_core: all 10 tickers x 5 horizons present, 105,450 OOS rows, span
2018-01-02 .. 2026-05-22. No tickers/horizons uncovered.

**Coverage / calibration warnings.** The mixture-matched single-lognormal emission is **markedly
under-dispersed at longer horizons**: cov90 falls from ~0.91 (h=1) to ~0.74 (h=42) and cov50 from
~0.53 to ~0.36 — the two-moment lognormal match understates the mixture's tail mass. log_bias is
mildly negative (-0.06 .. -0.28). These miscalibrations are a direct cost of collapsing the
two-component mixture to one lognormal for the quantile wrapper.

**Reproducibility.** numpy seed `_SEED = 0` (only the init jitter is stochastic; EM itself is
deterministic given init). Libraries: numpy 2.4.6, polars 1.41.1, scipy 1.17.1, statsmodels 0.14.6
(MarkovRegression available but **not used** — the hand-rolled vectorized EM is faster and gives
direct control of the iter cap / mixture forecast). Python 3.12.13. Device: macOS arm64 (Apple
Silicon), CPU, single-threaded. Wall-time: clean_core walk-forward **555.8s** (~9.3 min);
hard_cases **132.0s** (~2.2 min).

## HARD-GATE VERDICT (vs cheap regime models 29/30 + single-regime HAR) — self-stats only

**Verdict: MS-HAR DOES NOT beat the cheap regime baselines, nor the single-regime HAR. It LOSES on
QLIKE at EVERY horizon (clean_core, pooled), and also on log_rmse and calibration. Per the catalog
("reject if it doesn't beat the cheap regime models"), this model is a REJECT candidate; the human
comparison pass decides final rejection.**

Pooled QLIKE by horizon, clean_core (lower is better):

| h | MS-HAR (31) | Threshold-HAR (29) | STAR-HAR (30) | single-regime HAR | MS-HAR best of 3 baselines? |
|---|---|---|---|---|---|
| 1  | 0.3256 | 0.2844 | 0.3084 | 0.3198 | NO (worst) |
| 5  | 0.2712 | 0.1839 | 0.2025 | 0.2114 | NO (worst) |
| 10 | 0.2916 | 0.2075 | 0.2185 | 0.2267 | NO (worst) |
| 22 | 0.3704 | 0.3508 | 0.3146 | 0.3232 | NO (worst) |
| 42 | 0.7045 | 0.4681 | 0.4147 | 0.4204 | NO (worst, large gap) |

At the **primary horizon h=22**, MS-HAR QLIKE 0.3704 vs Threshold-HAR 0.3508, STAR-HAR 0.3146,
single-regime HAR 0.3232 — MS-HAR is the **worst** of the four. The gap blows out at h=42
(0.7045 vs ~0.42). MS-HAR is also worse on log_rmse at every horizon (e.g. h=22: 0.818 vs HAR
0.661) and is **under-calibrated** (cov90 0.74-0.91 vs HAR's 0.89-0.92). The added EM machinery
(2-state switching, ~9 min/universe vs ~25s for Threshold-HAR) buys **negative** skill here. The
likely culprits: (a) the two-moment single-lognormal collapse of the mixture loses the very
regime-tail information the model exists to capture, and (b) the refit-cadence reduction means the
switching params lag the origin between full EMs. Even granting those, the point forecast (QLIKE)
is dominated, so the recommendation is REJECT vs the cheaper regime models.
