# HAR-GARCH — Self Stats
_universe=`clean_core` · primary horizon h=22 · predictions=`execution/data/predictions/HAR-GARCH.parquet` · generated 2026-06-03T21:59:10Z_

_Self-only metrics — no leaderboard rank, no DM test, no MCS, no §9 status._
_Cross-model comparison is produced by the final `rv_eval.evaluator` pass._

## Tier-1 pooled by horizon (§3)
| model | horizon | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-GARCH | 1 | 21080 | 0.3180 | 0.7953 | 0.6318 | -0.2646 | 0.8911 | 0.4953 | 0.0000 |
| HAR-GARCH | 5 | 21040 | 0.2050 | 0.6107 | 0.4747 | -0.1401 | 0.8861 | 0.5031 | 0.0002 |
| HAR-GARCH | 10 | 20990 | 0.2226 | 0.6033 | 0.4636 | -0.1181 | 0.8833 | 0.5024 | 0.0003 |
| HAR-GARCH | 22 | 20870 | 0.3320 | 0.6395 | 0.4800 | -0.1061 | 0.8726 | 0.4875 | 0.0008 |
| HAR-GARCH | 42 | 20670 | 0.4480 | 0.6892 | 0.5023 | -0.1002 | 0.8674 | 0.4883 | 0.0015 |

## §5 IV-incremental skill (per horizon)
| model | horizon | n | slope | t_slope | sign_acc | qlike_model | qlike_iv | qlike_gain_vs_iv |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-GARCH | 1 | 20820 | 0.8876 | 55.2276 | 0.6228 | 0.3176 | 0.3276 | 0.0101 |
| HAR-GARCH | 5 | 20780 | 0.6347 | 62.0161 | 0.5984 | 0.2051 | 0.2079 | 0.0028 |
| HAR-GARCH | 10 | 20730 | 0.6880 | 36.5229 | 0.5641 | 0.2232 | 0.2187 | -0.0046 |
| HAR-GARCH | 22 | 20610 | 0.2277 | 8.7006 | 0.5310 | 0.3337 | 0.3396 | 0.0059 |
| HAR-GARCH | 42 | 20410 | 0.1933 | 8.8681 | 0.5372 | 0.4521 | 0.4697 | 0.0176 |

## §6 Conditional bias by IV-percentile bucket (h=22)
| model | horizon | iv_pctile_bucket | n | qlike | log_bias |
| --- | --- | --- | --- | --- | --- |
| HAR-GARCH | 22 | 0 | 5500 | 0.1796 | -0.1487 |
| HAR-GARCH | 22 | 1 | 3449 | 0.3232 | -0.1418 |
| HAR-GARCH | 22 | 2 | 3439 | 0.4717 | -0.1081 |
| HAR-GARCH | 22 | 3 | 3533 | 0.3777 | -0.0806 |
| HAR-GARCH | 22 | 4 | 4949 | 0.3778 | -0.0509 |

## §6 Post-shock calibration (h=22)
| model | horizon | bias_all | qlike_all | bias_postshock | qlike_postshock | n_postshock | trap_flag |
| --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-GARCH | 22 | -0.1061 | 0.3320 | -0.2010 | 0.3799 | 3986 |  |

## Per-ticker Tier-1 at h=22
| model | horizon | ticker | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-GARCH | 22 | EEM | 2087 | 0.2298 | 0.6260 | 0.4990 | -0.2022 | 0.8773 | 0.4820 | 0.0007 |
| HAR-GARCH | 22 | GLD | 2087 | 0.1831 | 0.5374 | 0.4152 | -0.0875 | 0.8222 | 0.4245 | 0.0004 |
| HAR-GARCH | 22 | HYG | 2087 | 0.6819 | 0.8966 | 0.7138 | -0.4552 | 0.9483 | 0.5697 | 0.0002 |
| HAR-GARCH | 22 | IWM | 2087 | 0.2942 | 0.5801 | 0.4313 | -0.0268 | 0.8481 | 0.4552 | 0.0010 |
| HAR-GARCH | 22 | QQQ | 2087 | 0.3065 | 0.6155 | 0.4628 | -0.0135 | 0.8975 | 0.5673 | 0.0009 |
| HAR-GARCH | 22 | SPY | 2087 | 0.4423 | 0.7206 | 0.5551 | -0.0941 | 0.8654 | 0.4835 | 0.0007 |
| HAR-GARCH | 22 | TLT | 2087 | 0.2146 | 0.5124 | 0.3707 | -0.0067 | 0.8342 | 0.4274 | 0.0003 |
| HAR-GARCH | 22 | XLE | 2087 | 0.2841 | 0.5514 | 0.3914 | -0.0246 | 0.8769 | 0.5103 | 0.0015 |
| HAR-GARCH | 22 | XLF | 2087 | 0.3776 | 0.6573 | 0.5088 | -0.1517 | 0.8807 | 0.4528 | 0.0011 |
| HAR-GARCH | 22 | XLK | 2087 | 0.3058 | 0.6093 | 0.4517 | 0.0010 | 0.8754 | 0.5022 | 0.0011 |

## Pooled by group
| model | group | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-GARCH | emerging_markets | 10465 | 0.2878 | 0.7486 | 0.5899 | -0.2781 | 0.8948 | 0.4970 | 0.0005 |
| HAR-GARCH | high_yield_credit | 10465 | 0.5318 | 0.8426 | 0.6650 | -0.3793 | 0.9196 | 0.5445 | 0.0001 |
| HAR-GARCH | oil_and_energy | 10465 | 0.2577 | 0.5683 | 0.4151 | -0.0649 | 0.8797 | 0.5038 | 0.0011 |
| HAR-GARCH | precious_metals | 10465 | 0.2415 | 0.6745 | 0.5208 | -0.1812 | 0.8578 | 0.4542 | 0.0003 |
| HAR-GARCH | us_cyclicals_sector | 10465 | 0.3158 | 0.6578 | 0.5069 | -0.1761 | 0.8984 | 0.5109 | 0.0008 |
| HAR-GARCH | us_large_cap_equity | 20930 | 0.3265 | 0.6830 | 0.5224 | -0.0903 | 0.8785 | 0.5045 | 0.0006 |
| HAR-GARCH | us_rates_and_ig_credit | 10465 | 0.2205 | 0.5852 | 0.4372 | -0.0702 | 0.8471 | 0.4531 | 0.0002 |
| HAR-GARCH | us_small_cap_equity | 10465 | 0.2607 | 0.5928 | 0.4445 | -0.0680 | 0.8634 | 0.4765 | 0.0007 |
| HAR-GARCH | us_technology_sector | 10465 | 0.2773 | 0.6324 | 0.4819 | -0.0628 | 0.8837 | 0.5044 | 0.0008 |

---

## Model build notes (human-only fields, MODEL_PLAN §5)

**Model.** HAR-GARCH (catalog model 26, Track D, Pattern P2). File
`candidate_models/har_garch.py`, class `HARGARCH`, base `_PerKeyModel`. Fit per
`(ticker, horizon)`.

**Mean model.** Direct-h log-OLS HAR: `log(target_var) ~ 1 + log_rv_d + log_rv_w + log_rv_m`
(`needs = HAR_FEATURES`). Point forecast `rv_hat = exp(mu + 0.5*s_t^2)` (lognormal mean).
Mean OLS is solved by `np.linalg.lstsq` and never fails.

**Variance model (GARCH spec — frozen by catalog, no OOS tuning).** `arch` GARCH on the
HAR **log-residual** series `e_t = log(target_var_t) - mu_t`:
- `mean="Zero"`, `vol="GARCH"`, `p=1`, `q=1`, `dist="normal"`.
- Asymmetry order `o ∈ {0, 1}` chosen **per (ticker,h) on TRAIN-only BIC**: GARCH(1,1)
  (`o=0`) vs GJR-GARCH(1,1,1) (`o=1`). No OOS data informs the choice.
- Residuals scaled ×100 before fitting (`rescale=False`); arch is ill-conditioned on
  tiny RV-scale residuals (mirrors `realized_garch.py`).
- Predictive log-sd `s_t` = sqrt of the **h-step-ahead** conditional-variance forecast
  (`fr.forecast(horizon=h).variance[-1,-1] / 100^2`) from the last train origin. Constant
  within a refit block (one monthly forecast origin; never peeks at test residuals).
- `s_t` is tethered to `[0.1×, 10×]` of the OLS constant residual sd, then clipped to
  `[1e-3, 5.0]`.

**Fit settings.** `arch_model(...).fit(disp="off", show_warning=False, options={"maxiter": 200})`,
all warnings silenced, every fit wrapped in try/except. `min_obs = 100` per (ticker,h).

**Fallback discipline + count.** If the GARCH fit fails / is non-finite / the residual
series is degenerate (n<50, near-zero variance, non-finite), the key FALLS BACK to the
**constant HAR in-sample residual sd** (constant-variance forecast) and is counted in
`self.fallbacks`. A single non-convergent key never aborts the run.
- On the final full-history fold (representative): **clean_core — 50/50 keys fitted, 0
  fallbacks**; spec mix = 25× GARCH(1,1), 25× GJR-GARCH(1,1,1). No (ticker,horizon) fell
  back. (Earlier short-history folds may occasionally fall back; the run-level total is
  near zero — the residual series is always long and well-conditioned.)

**Refit frequency.** Unchanged from the harness default (`REFIT_FREQ="monthly"`,
`TRAIN_WINDOW="expanding"`). Full per-(ticker,horizon) arch refit every fold — no
reduction was needed (see wall-time below).

**Coverage.** 90% interval coverage (`cov90`) sits ~0.87–0.89 (slightly narrow at short
horizons), `cov50` ~0.49–0.50 (well centered). A persistent negative `log_bias`
(~ -0.10 to -0.26) is inherited from the HAR mean (under-prediction in high-vol /
post-shock states), not from the GARCH layer; HYG is the worst-calibrated ticker
(cov90 0.95, strong negative bias). The GARCH layer widens intervals in turbulent
regimes relative to the constant-sd HAR but does not correct the mean bias.

**Reproducibility.** No stochasticity — the GARCH h-step forecast is analytic (no Monte
Carlo). `arch` L-BFGS-B/SLSQP optimiser is deterministic from fixed inits.

**Environment.** arch 8.0.0, numpy 2.4.6, polars 1.41.1, scipy 1.17.1, Python 3.12.13.
Device: macOS-15.3.1 arm64 (Apple Silicon), CPU only.

**Wall-time.** clean_core walk-forward: **145.0 s**; hard_cases: **45.6 s** (foreground,
synchronous). OOS predictions: clean_core 105,450 rows; hard_cases 40,810 rows
(span 2018-01-02 → 2026-05-22).

**Coverage gaps.** None — all 10 clean_core and all 5 hard_cases tickers covered at all
five horizons (1, 5, 10, 22, 42).
