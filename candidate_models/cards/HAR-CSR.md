# HAR-CSR — Self Stats
_universe=`clean_core` · primary horizon h=22 · predictions=`execution/data/predictions/HAR-CSR.parquet` · generated 2026-06-03T21:43:47Z_

_Self-only metrics — no leaderboard rank, no DM test, no MCS, no §9 status._
_Cross-model comparison is produced by the final `rv_eval.evaluator` pass._

## Build notes (human-only fields — MODEL_PLAN §5)
- **Model:** ITER2 catalog §3 model 20 — HAR-CSR (complete-subset regression). Class `HARCSR`,
  `name="HAR-CSR"`, file `candidate_models/har_csr.py`. Pattern P2 over `_PerKeyModel`
  (per-(ticker,horizon) fit; no `_AttachMixin` needed — see features below).
- **Features used (K=8, all pass-through from `build_features`, no derived/rolling join):**
  `log_rv_d, log_rv_w, log_rv_m` (HAR lags), `rs_minus_5d, jump_5d` (downside-semivariance + jump),
  `log_iv, vix` (implied-variance level + VIX), `sqrt_rq` (realized-quarticity / HAR-Q term).
  All eight already carry their trailing-window construction from `build_features` on the full
  point-in-time series, so the predict slice is leak-free with no `(ticker,date)` join required.
- **Subset scheme (FROZEN by catalog spec, not OOS-tuned):** k=4 out of K=8 ⇒ C(8,4)=**70**
  complete subsets. This equals the catalog cap (≤70) **exactly**, so the estimator is the FULL
  complete-subset average — **no random sampling, no seed-dependent draw**. (A seeded
  `np.random.default_rng(0)` sample of `_MAX_SUBSETS=70` is wired as a guard only if a future
  feature-set change pushed C(K,k) above 70; never triggered here.) Subset list is fixed at
  import and identical across every (ticker, horizon) and fold. Point forecast = equal-weight
  mean of the 70 per-subset lognormal means (averaging in level/QLIKE-mean space); predictive
  log-sd = mean of per-subset in-sample log-residual sds.
- **Library versions:** Python `.venv`; numpy 2.4.6, scipy 1.17.1, polars 1.41.1, scikit-learn
  1.8.0 (sklearn not used by this model — plain `np.linalg.lstsq` OLS).
- **Wall-time / device:** clean_core walk-forward 53.7s (104,050 OOS preds). Device: Apple
  Silicon arm64 (macOS 15.3.1), single process.
- **Coverage:** all 10 clean-core tickers × all 5 horizons covered, full OOS span
  2018-01-02 → 2026-05-21. cov90 ≈ 0.90–0.92 (slightly over at long h), cov50 ≈ 0.51–0.58.
  Persistent negative `log_bias` (≈ -0.13 to -0.26, strongest at h=1 and on HYG) — the
  complete-subset shrinkage pulls forecasts toward the center, under-predicting in the right
  tail; expected for an averaged-OLS shrinkage estimator. No coverage failures or NaN rows.

## Tier-1 pooled by horizon (§3)
| model | horizon | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-CSR | 1 | 20810 | 0.2979 | 0.7781 | 0.6126 | -0.2580 | 0.9053 | 0.5099 | 0.0003 |
| HAR-CSR | 5 | 20770 | 0.1918 | 0.5916 | 0.4517 | -0.1426 | 0.9121 | 0.5498 | 0.0004 |
| HAR-CSR | 10 | 20720 | 0.2096 | 0.5866 | 0.4419 | -0.1301 | 0.9187 | 0.5649 | 0.0006 |
| HAR-CSR | 22 | 20600 | 0.3227 | 0.6268 | 0.4625 | -0.1354 | 0.9229 | 0.5766 | 0.0011 |
| HAR-CSR | 42 | 20400 | 0.4256 | 0.6908 | 0.5005 | -0.1481 | 0.9245 | 0.5844 | 0.0018 |

## §5 IV-incremental skill (per horizon)
| model | horizon | n | slope | t_slope | sign_acc | qlike_model | qlike_iv | qlike_gain_vs_iv |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-CSR | 1 | 20810 | 0.0002 | 3.2577 | 0.6845 | 0.2979 | 0.3277 | 0.0298 |
| HAR-CSR | 5 | 20770 | 0.0013 | 4.0394 | 0.6355 | 0.1918 | 0.2079 | 0.0161 |
| HAR-CSR | 10 | 20720 | 0.0006 | 1.1580 | 0.5797 | 0.2096 | 0.2187 | 0.0092 |
| HAR-CSR | 22 | 20600 | -0.0020 | -2.1368 | 0.5226 | 0.3227 | 0.3397 | 0.0170 |
| HAR-CSR | 42 | 20400 | -0.0071 | -3.3020 | 0.5006 | 0.4256 | 0.4699 | 0.0444 |

## §6 Conditional bias by IV-percentile bucket (h=22)
| model | horizon | iv_pctile_bucket | n | qlike | log_bias |
| --- | --- | --- | --- | --- | --- |
| HAR-CSR | 22 | 0 | 5240 | 0.1706 | -0.1864 |
| HAR-CSR | 22 | 1 | 3448 | 0.3087 | -0.1815 |
| HAR-CSR | 22 | 2 | 3439 | 0.4627 | -0.1412 |
| HAR-CSR | 22 | 3 | 3533 | 0.3650 | -0.0944 |
| HAR-CSR | 22 | 4 | 4940 | 0.3661 | -0.0744 |

## §6 Post-shock calibration (h=22)
| model | horizon | bias_all | qlike_all | bias_postshock | qlike_postshock | n_postshock | trap_flag |
| --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-CSR | 22 | -0.1354 | 0.3227 | -0.1547 | 0.3790 | 3921 |  |

## Per-ticker Tier-1 at h=22
| model | horizon | ticker | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-CSR | 22 | EEM | 2060 | 0.2308 | 0.5879 | 0.4557 | -0.1533 | 0.9141 | 0.5689 | 0.0007 |
| HAR-CSR | 22 | GLD | 2060 | 0.1555 | 0.4948 | 0.3757 | -0.0882 | 0.9010 | 0.5364 | 0.0003 |
| HAR-CSR | 22 | HYG | 2060 | 0.7045 | 0.8903 | 0.7148 | -0.4915 | 0.9650 | 0.5922 | 0.0002 |
| HAR-CSR | 22 | IWM | 2060 | 0.2798 | 0.5503 | 0.3993 | -0.0266 | 0.9238 | 0.5563 | 0.0011 |
| HAR-CSR | 22 | QQQ | 2060 | 0.3051 | 0.6157 | 0.4496 | -0.0311 | 0.8947 | 0.6097 | 0.0011 |
| HAR-CSR | 22 | SPY | 2060 | 0.4266 | 0.6921 | 0.5253 | -0.1167 | 0.9155 | 0.5723 | 0.0008 |
| HAR-CSR | 22 | TLT | 2060 | 0.2101 | 0.5742 | 0.3653 | -0.0761 | 0.9194 | 0.5063 | 0.0030 |
| HAR-CSR | 22 | XLE | 2060 | 0.2704 | 0.5296 | 0.3796 | -0.0731 | 0.9311 | 0.6160 | 0.0015 |
| HAR-CSR | 22 | XLF | 2060 | 0.3492 | 0.6534 | 0.5231 | -0.2584 | 0.9524 | 0.5908 | 0.0011 |
| HAR-CSR | 22 | XLK | 2060 | 0.2951 | 0.5896 | 0.4365 | -0.0391 | 0.9121 | 0.6165 | 0.0011 |

## Pooled by group
| model | group | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-CSR | emerging_markets | 10330 | 0.2772 | 0.6962 | 0.5386 | -0.2047 | 0.9077 | 0.5364 | 0.0005 |
| HAR-CSR | high_yield_credit | 10330 | 0.5292 | 0.8636 | 0.6951 | -0.4613 | 0.9521 | 0.5918 | 0.0001 |
| HAR-CSR | oil_and_energy | 10330 | 0.2403 | 0.5429 | 0.3977 | -0.0907 | 0.9253 | 0.5866 | 0.0011 |
| HAR-CSR | precious_metals | 10330 | 0.2138 | 0.6308 | 0.4834 | -0.1617 | 0.8955 | 0.5106 | 0.0003 |
| HAR-CSR | us_cyclicals_sector | 10330 | 0.2868 | 0.6424 | 0.5064 | -0.2412 | 0.9432 | 0.5903 | 0.0008 |
| HAR-CSR | us_large_cap_equity | 20660 | 0.3101 | 0.6724 | 0.5040 | -0.1126 | 0.9045 | 0.5580 | 0.0008 |
| HAR-CSR | us_rates_and_ig_credit | 10330 | 0.2156 | 0.6474 | 0.4381 | -0.1227 | 0.9065 | 0.5053 | 0.0024 |
| HAR-CSR | us_small_cap_equity | 10330 | 0.2435 | 0.5584 | 0.4116 | -0.0502 | 0.9164 | 0.5602 | 0.0008 |
| HAR-CSR | us_technology_sector | 10330 | 0.2634 | 0.6072 | 0.4605 | -0.0722 | 0.9109 | 0.5722 | 0.0008 |
