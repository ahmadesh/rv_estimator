# RealizedGARCH — Model Card (hard_cases)

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

_universe=`hard_cases` · primary horizon h=22 · predictions=`execution/data/predictions/RealizedGARCH.parquet` · generated 2026-06-01T04:36:29Z_

_Self-only metrics — no leaderboard rank, no DM test, no MCS, no §9 status._
_Cross-model comparison is produced by the final `rv_eval.evaluator` pass._

## Tier-1 pooled by horizon (§3)
| model | horizon | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| RealizedGARCH | 1 | 8235 | 0.5942 | 1.2415 | 1.0560 | -0.8359 | 0.0007 | 0.0001 | 0.0011 |
| RealizedGARCH | 5 | 8196 | 1.0545 | 1.9641 | 1.8143 | -1.7563 | 0.1529 | 0.0487 | 0.0091 |
| RealizedGARCH | 10 | 8151 | 2.0204 | 3.0612 | 2.9352 | -2.9239 | 0.0726 | 0.0189 | 0.0463 |
| RealizedGARCH | 22 | 8068 | 3.8996 | 4.9882 | 4.8855 | -4.8855 | 0.0108 | 0.0014 | 0.5768 |
| RealizedGARCH | 42 | 7948 | 5.6752 | 6.7679 | 6.6727 | -6.6727 | 0.0000 | 0.0000 | 6.1083 |

## §5 IV-incremental skill (per horizon)
| model | horizon | n | slope | t_slope | sign_acc | qlike_model | qlike_iv | qlike_gain_vs_iv |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| RealizedGARCH | 1 | 7925 | -0.0824 | -2.7776 | 0.3948 | 0.5933 | 0.3600 | -0.2333 |
| RealizedGARCH | 5 | 7886 | -0.0255 | -4.8780 | 0.2560 | 1.0593 | 0.2624 | -0.7969 |
| RealizedGARCH | 10 | 7861 | -0.0259 | -10.3869 | 0.2539 | 2.0187 | 0.2543 | -1.7644 |
| RealizedGARCH | 22 | 7778 | -0.0091 | -13.8056 | 0.2823 | 3.8946 | 0.2732 | -3.6214 |
| RealizedGARCH | 42 | 7678 | -0.0050 | -22.0804 | 0.3141 | 5.6673 | 0.3139 | -5.3535 |

## §6 Conditional bias by IV-percentile bucket (h=22)
| model | horizon | iv_pctile_bucket | n | qlike | log_bias |
| --- | --- | --- | --- | --- | --- |
| RealizedGARCH | 22 | 0 | 2078 | 4.2211 | -5.2121 |
| RealizedGARCH | 22 | 1 | 1264 | 4.0872 | -5.0771 |
| RealizedGARCH | 22 | 2 | 1355 | 3.9410 | -4.9295 |
| RealizedGARCH | 22 | 3 | 1460 | 3.8392 | -4.8243 |
| RealizedGARCH | 22 | 4 | 1727 | 3.3727 | -4.3476 |

## §6 Post-shock calibration (h=22)
| model | horizon | bias_all | qlike_all | bias_postshock | qlike_postshock | n_postshock | trap_flag |
| --- | --- | --- | --- | --- | --- | --- | --- |
| RealizedGARCH | 22 | -4.8855 | 3.8996 | -4.5110 | 3.5321 | 1492 |  |

## Per-ticker Tier-1 at h=22
| model | horizon | ticker | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| RealizedGARCH | 22 | IBIT | 537 | 4.0613 | 5.0805 | 5.0539 | -5.0539 | 0.0000 | 0.0000 | 0.5487 |
| RealizedGARCH | 22 | KRE | 2087 | 4.6943 | 5.7338 | 5.6891 | -5.6891 | 0.0048 | 0.0000 | 0.3844 |
| RealizedGARCH | 22 | MSOS | 1270 | 3.4081 | 4.4422 | 4.3926 | -4.3926 | 0.0000 | 0.0000 | 0.6348 |
| RealizedGARCH | 22 | USO | 2087 | 4.2716 | 5.3234 | 5.2630 | -5.2630 | 0.0043 | 0.0000 | 0.4099 |
| RealizedGARCH | 22 | UVXY | 2087 | 2.9904 | 4.0404 | 3.9609 | -3.9609 | 0.0326 | 0.0053 | 0.9083 |

## Pooled by group
| model | group | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| RealizedGARCH | crypto | 2735 | 2.6118 | 4.0963 | 3.4363 | -3.3929 | 0.0464 | 0.0143 | 1.3132 |
| RealizedGARCH | long_volatility_vix | 10465 | 2.1052 | 3.3890 | 2.8799 | -2.7775 | 0.0880 | 0.0246 | 1.7256 |
| RealizedGARCH | oil_and_energy | 10465 | 2.8458 | 4.3769 | 3.6884 | -3.6416 | 0.0353 | 0.0111 | 1.1083 |
| RealizedGARCH | us_cannabis | 6468 | 2.2863 | 3.6662 | 3.0979 | -3.0489 | 0.0479 | 0.0142 | 1.3422 |
| RealizedGARCH | us_cyclicals_sector | 10465 | 3.1370 | 4.7084 | 3.9913 | -3.9548 | 0.0202 | 0.0058 | 1.1213 |
