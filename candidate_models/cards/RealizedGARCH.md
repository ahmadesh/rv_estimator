# RealizedGARCH — Model Card

## Identity
- Model number (from MODEL_PLAN.md): 8
- Class: candidate_models.realized_garch:RealizedGARCH
- Tier: GARCH
- Implemented by: card generated 2026-05-31 (model code & predictions pre-existing and validated)

## Configuration
- Features used (list, by name): `ret_cc` (daily close-to-close return; the plan's `ret_close`), `rv_d` (daily realized measure of variance = `total_rv`).
- Spec: Realized GARCH(1,1), Hansen-Huang-Shek (2012), log/log "RealGARCH(1,1)" specification. Parameters per (ticker, horizon) `theta = (omega, beta, gamma, xi, phi, tau1, tau2, su2)` estimated jointly by maximum likelihood (HHS eq. 2.7) with `scipy.optimize.minimize`, method=L-BFGS-B, maxiter=500.
  - return eq.:      `r_t = sqrt(h_t) * z_t`, `z_t ~ N(0,1)`
  - GARCH eq.:       `log h_t = omega + beta*log h_{t-1} + gamma*log x_{t-1}`
  - measurement eq.: `log x_t = xi + phi*log h_t + tau(z_t) + u_t`, `u_t ~ N(0, su2)`
  - leverage:        `tau(z) = tau1*z + tau2*(z^2 - 1)`
  - joint NLL:       `L = -1/2 * sum_t [ log h_t + r_t^2/h_t + log su2 + u_t^2/su2 ]`
- Horizon forecast: Monte-Carlo bootstrap of the joint `(log h, log x)` recursion `h` steps forward, drawing `z ~ N(0,1)` and `u ~ N(0, su2)` per step. `rv_hat = E[ sum_{s=t+1..t+h} h_s ]`; `sigma = std( log( sum_s h_s ) )`, clipped to `[1e-3, 5.0]`.
- MC bootstrap path count: 1000 paths (`_N_PATHS = 1000`).
- omega floor: `_OMEGA_FLOOR = 1e-8`, applied as `theta[0] = max(theta[0], log(1e-8))` in log-variance space; GARCH(1,1)-fallback omega floored at `1e-8` directly. Conditional-variance / realized-measure floor before log: `_H_FLOOR = 1e-12`.
- Hyperparameters (FROZEN): all 8 R-GARCH params are estimated per (ticker, horizon) by MLE — there are no tunable hyperparameters. `min_obs = 100`.
- HP selection (models 8-11): N/A — no hyperparameter grid. Parameters obtained via MLE, not a validation-block search.
- GARCH(1,1) fallback: if the joint R-GARCH MLE fails to converge or is degenerate, fall back to a plain Gaussian GARCH(1,1) on returns via the `arch` library (`arch.univariate.arch_model`, mean="Zero", vol="GARCH", p=1, q=1, dist="normal"; returns scaled by 100 for conditioning). If even the fallback fails, that (ticker, horizon) is DROPPED (never imputed) — `predict` yields no row for it.
- Library version(s): arch 8.0.0; scipy.optimize (L-BFGS-B); numpy; polars.
- Random seed (if applicable): numpy seed = 0 (`np.random.default_rng(0)`, re-seeded per predict call for reproducibility).

## Training
- Universes run: clean_core, hard_cases
- Walk-forward folds: per-(ticker, horizon) MLE refit within the existing walk-forward harness (not re-run for this card).
- Wall-clock time: clean_core 2236s (~37m 16s), hard_cases 77s (per-ticker MLE).
- Device: cpu
- Convergence notes / per-ticker warnings: The model records the chosen variant per (ticker, horizon) on `self.warnings` — `"rgarch"` for full Realized GARCH, `"fallback: GARCH(1,1)"` when the joint MLE fails, `"dropped"` if both fail. The per-key R-GARCH-vs-GARCH(1,1) split is NOT recoverable from the predictions parquet alone and is not reconstructed here (would require re-running the walk-forward, which this task explicitly forbids). What is verifiable from the parquet: 146,448 OOS rows covering all 15 scored tickers x 5 horizons {1,5,10,22,42}, with all `rv_hat` finite and > 0 — i.e. NO (ticker, horizon) was dropped; every key converged under either the full R-GARCH MLE or the GARCH(1,1) fallback.

## OOS self-stats (this model alone — no ranks, no DM, no MCS, no §9 status)

_universe=`clean_core` · primary horizon h=22 · predictions=`execution/data/predictions/RealizedGARCH.parquet` · generated 2026-06-01T04:36:27Z_

_Self-only metrics — no leaderboard rank, no DM test, no MCS, no §9 status._
_Cross-model comparison is produced by the final `rv_eval.evaluator` pass._

## Tier-1 pooled by horizon (§3)
| model | horizon | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| RealizedGARCH | 1 | 21080 | 0.7567 | 1.5934 | 1.3373 | -1.1873 | 0.0004 | 0.0002 | 0.0002 |
| RealizedGARCH | 5 | 21040 | 1.3846 | 2.3385 | 2.1677 | -2.1121 | 0.0817 | 0.0260 | 0.0020 |
| RealizedGARCH | 10 | 20990 | 2.5571 | 3.5898 | 3.4008 | -3.3643 | 0.0528 | 0.0183 | 0.0130 |
| RealizedGARCH | 22 | 20870 | 5.1018 | 6.4146 | 5.7568 | -5.7168 | 0.0525 | 0.0223 | 8960928.5710 |
| RealizedGARCH | 42 | 20670 | 8.1996 | 10.7798 | 8.4941 | -8.4426 | 0.0584 | 0.0167 | 9793856419372202.0000 |

## §5 IV-incremental skill (per horizon)
| model | horizon | n | slope | t_slope | sign_acc | qlike_model | qlike_iv | qlike_gain_vs_iv |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| RealizedGARCH | 1 | 20820 | -0.0027 | -0.4890 | 0.3196 | 0.7572 | 0.3276 | -0.4296 |
| RealizedGARCH | 5 | 20780 | -0.0011 | -2.5692 | 0.3243 | 1.3848 | 0.2079 | -1.1770 |
| RealizedGARCH | 10 | 20730 | -0.0009 | -3.5304 | 0.3390 | 2.5564 | 0.2187 | -2.3377 |
| RealizedGARCH | 22 | 20610 | -0.0000 | -0.0000 | 0.3654 | 5.1108 | 0.3396 | -4.7713 |
| RealizedGARCH | 42 | 20410 | -0.0000 | -0.0000 | 0.3754 | 8.2207 | 0.4697 | -7.7510 |

## §6 Conditional bias by IV-percentile bucket (h=22)
| model | horizon | iv_pctile_bucket | n | qlike | log_bias |
| --- | --- | --- | --- | --- | --- |
| RealizedGARCH | 22 | 0 | 5500 | 4.8788 | -5.6853 |
| RealizedGARCH | 22 | 1 | 3449 | 5.1311 | -5.7202 |
| RealizedGARCH | 22 | 2 | 3439 | 5.4611 | -5.8813 |
| RealizedGARCH | 22 | 3 | 3533 | 5.0519 | -5.9476 |
| RealizedGARCH | 22 | 4 | 4949 | 5.1153 | -5.4702 |

## §6 Post-shock calibration (h=22)
| model | horizon | bias_all | qlike_all | bias_postshock | qlike_postshock | n_postshock | trap_flag |
| --- | --- | --- | --- | --- | --- | --- | --- |
| RealizedGARCH | 22 | -5.7168 | 5.1018 | -5.5284 | 5.3088 | 3986 |  |

## Per-ticker Tier-1 at h=22
| model | horizon | ticker | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| RealizedGARCH | 22 | EEM | 2087 | 5.5279 | 9.9792 | 6.3655 | -6.3588 | 0.0479 | 0.0297 | 89609283.5149 |
| RealizedGARCH | 22 | GLD | 2087 | 5.4322 | 6.4638 | 6.4301 | -6.4301 | 0.0000 | 0.0000 | 0.2111 |
| RealizedGARCH | 22 | HYG | 2087 | 4.6463 | 2.9822 | 2.3881 | -1.9944 | 0.4581 | 0.1931 | 0.0112 |
| RealizedGARCH | 22 | IWM | 2087 | 4.8185 | 5.8582 | 5.8139 | -5.8139 | 0.0000 | 0.0000 | 0.2951 |
| RealizedGARCH | 22 | QQQ | 2087 | 4.9756 | 6.0230 | 5.9716 | -5.9716 | 0.0000 | 0.0000 | 0.2826 |
| RealizedGARCH | 22 | SPY | 2087 | 5.4842 | 6.5399 | 6.4813 | -6.4813 | 0.0048 | 0.0000 | 0.2408 |
| RealizedGARCH | 22 | TLT | 2087 | 5.3509 | 6.3783 | 6.3486 | -6.3486 | 0.0000 | 0.0000 | 0.2031 |
| RealizedGARCH | 22 | XLE | 2087 | 4.6192 | 5.6598 | 5.6134 | -5.6134 | 0.0048 | 0.0000 | 0.3470 |
| RealizedGARCH | 22 | XLF | 2087 | 5.2749 | 6.3188 | 6.2716 | -6.2716 | 0.0072 | 0.0000 | 0.2978 |
| RealizedGARCH | 22 | XLK | 2087 | 4.8883 | 5.9337 | 5.8840 | -5.8840 | 0.0024 | 0.0000 | 0.3061 |

## Pooled by group
| model | group | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| RealizedGARCH | emerging_markets | 10465 | 4.4423 | 11.2251 | 5.2689 | -5.2421 | 0.0462 | 0.0145 | 19344387230543708.0000 |
| RealizedGARCH | high_yield_credit | 10465 | 4.1906 | 4.8501 | 2.7127 | -2.3562 | 0.2895 | 0.1089 | 745154.4354 |
| RealizedGARCH | oil_and_energy | 10465 | 3.0648 | 4.6465 | 3.9256 | -3.8918 | 0.0168 | 0.0032 | 1.0108 |
| RealizedGARCH | precious_metals | 10465 | 3.5912 | 5.2939 | 4.4745 | -4.4418 | 0.0190 | 0.0057 | 0.8037 |
| RealizedGARCH | us_cyclicals_sector | 10465 | 3.5136 | 5.1793 | 4.3842 | -4.3494 | 0.0237 | 0.0054 | 1.0128 |
| RealizedGARCH | us_large_cap_equity | 20930 | 3.4973 | 5.1626 | 4.3676 | -4.3243 | 0.0244 | 0.0074 | 0.9035 |
| RealizedGARCH | us_rates_and_ig_credit | 10465 | 3.5388 | 5.2293 | 4.4246 | -4.3996 | 0.0086 | 0.0030 | 0.7582 |
| RealizedGARCH | us_small_cap_equity | 10465 | 3.2148 | 4.8157 | 4.0822 | -4.0484 | 0.0134 | 0.0042 | 0.9209 |
| RealizedGARCH | us_technology_sector | 10465 | 3.2559 | 4.8711 | 4.1229 | -4.0842 | 0.0248 | 0.0072 | 0.9585 |
