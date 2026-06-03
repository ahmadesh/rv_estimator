# RW — Model Card

## Identity
- Model number (from MODEL_PLAN.md): 0
- Class: rv_eval.model_contract:RandomWalk (benchmark — already coded; no candidate file written)
- Tier: Baseline
- Implemented by: swarm worker, 2026-05-31

## Configuration
- Features used (list, by name): rv_d (daily realized variance). Forecast is rv_hat = h * rv_d, lognormal-mean corrected (× exp(½σ²)). Sigma from the log-residual std of log(target_var) vs log(h·rv_d), fit per (ticker, horizon).
- Hyperparameters (key=value, one per line — the FROZEN values used): none — RandomWalk has no free hyperparameters. min_obs=30 (per-key fit guard inherited from _NaiveScaled).
- HP selection (models 8–11): N/A — model 0 has no tunable hyperparameters; no validation block was used.
- Library version(s): python 3.12.13, numpy 2.4.6, scipy 1.17.1, polars 1.41.1
- Random seed (if applicable): N/A — deterministic (closed-form OLS-free naive scaling; no stochastic fitting).

## Training
- Universes run: clean_core, hard_cases
- Walk-forward folds: monthly refit, expanding window, OOS span 2018-01-02 → 2026-05-22 (purged + embargoed per rv_eval.config; EMBARGO_EXTRA=1, gap = h + 1).
- Wall-clock time: clean_core: 6.7s, hard_cases: 3.5s
- Device: cpu
- Convergence notes / per-ticker warnings: No convergence step (naive model). All 15 scored tickers covered at every horizon. Reduced row counts where option/price history starts late or is thin: IBIT (~2y history; 620 rows at h=22, 3,212 total) and MSOS (thin; 1,353 rows at h=22). These are genuinely short series, not dropped cells — no rows imputed.

## OOS self-stats (this model alone — no ranks, no DM, no MCS, no §9 status)
- QLIKE pooled by horizon (clean_core h=1/5/10/22/42): 0.4219 / 0.3540 / 0.4014 / 0.5895 / 0.7709. (hard_cases: 0.4544 / 0.4286 / 0.4736 / 0.6054 / 0.7006 — see RW.hard_cases.md.)
- §5 IV-incremental skill at h=22 (clean_core): slope=0.0333, t=11.32, sign_acc=0.5355, qlike_gain_vs_iv=-0.2504 (IV-as-forecast beats RW at h=22, as expected for a naive benchmark).
- §6 conditional bias by IV-pctile bucket at h=22 (clean_core log_bias, buckets 0→4): +0.0814 / +0.0107 / -0.0356 / -0.1124 / -0.3243 (RW over-forecasts in low-IV, under-forecasts in high-IV — classic naive mean-reversion miss).
- §6 post-shock bias at h=22 (clean_core): bias_all=-0.0786, bias_postshock=-0.4831 (n=3,986), trap_flag=✓ (RW lags the post-shock vol decay, under-forecasting strongly).
- 50% / 90% interval coverage at h=22 (clean_core): cov50=0.4869, cov90=0.8779 (both modestly under-cover the nominal 0.50 / 0.90).

## Per-ticker QLIKE at h=22 (clean_core)
| ticker | qlike | notes |
|---|---|---|
| EEM | 0.6159 | |
| GLD | 0.5243 | |
| HYG | 0.9493 | strongest neg bias (-0.357); over-covers |
| IWM | 0.4863 | |
| QQQ | 0.5054 | |
| SPY | 0.8031 | |
| TLT | 0.4425 | |
| XLE | 0.4246 | |
| XLF | 0.6149 | |
| XLK | 0.5293 | |

(hard_cases per-ticker h=22: IBIT 0.7075 [n=620], KRE 0.5298, MSOS 0.4287 [n=1353], USO 0.5473, UVXY 0.8235 — see RW.hard_cases.md.)

## Anomalies / things the next reader should know
- RW is the simplest scored model and the floor for the comparison; it has no IV awareness, so it is expected to lose to IV-as-forecast and HAR-family at longer horizons (qlike_gain_vs_iv is negative at every horizon).
- IBIT and MSOS have materially fewer OOS rows (short / thin series). Coverage differs from the other tickers — relevant for the comparison pass's common-support joins.
- The predictions parquet at execution/data/predictions/RW.parquet was overwritten fresh this run (per-ticker upsert); it now contains exactly the RW model rows for all 15 scored tickers (147,210 rows total).

## Reproduce
```bash
.venv/bin/python -m rv_eval.walkforward --model rv_eval.model_contract:RandomWalk --universe clean_core
.venv/bin/python -m rv_eval.walkforward --model rv_eval.model_contract:RandomWalk --universe hard_cases
.venv/bin/python -m rv_eval.selfstats --pred execution/data/predictions/RW.parquet --out candidate_models/cards/RW.md --universe clean_core
.venv/bin/python -m rv_eval.selfstats --pred execution/data/predictions/RW.parquet --out candidate_models/cards/RW.hard_cases.md --universe hard_cases
```

---

# RW — Self Stats
_universe=`clean_core` · primary horizon h=22 · predictions=`/Users/ahmade/Documents/rv_estimator/execution/data/predictions/RW.parquet` · generated 2026-06-01T02:56:16Z_

_Self-only metrics — no leaderboard rank, no DM test, no MCS, no §9 status._
_Cross-model comparison is produced by the final `rv_eval.evaluator` pass._

## Tier-1 pooled by horizon (§3)
| model | horizon | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| RW | 1 | 21080 | 0.4219 | 0.9756 | 0.7576 | -0.3656 | 0.8869 | 0.4995 | 0.0000 |
| RW | 5 | 21040 | 0.3540 | 0.8182 | 0.6308 | -0.1227 | 0.8802 | 0.4895 | 0.0002 |
| RW | 10 | 20990 | 0.4014 | 0.8342 | 0.6422 | -0.0884 | 0.8798 | 0.4835 | 0.0005 |
| RW | 22 | 20870 | 0.5895 | 0.8911 | 0.6808 | -0.0786 | 0.8779 | 0.4869 | 0.0011 |
| RW | 42 | 20670 | 0.7709 | 0.9709 | 0.7348 | -0.0924 | 0.8773 | 0.4978 | 0.0024 |

## §5 IV-incremental skill (per horizon)
| model | horizon | n | slope | t_slope | sign_acc | qlike_model | qlike_iv | qlike_gain_vs_iv |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| RW | 1 | 20820 | 0.2086 | 41.5448 | 0.5849 | 0.4213 | 0.3276 | -0.0936 |
| RW | 5 | 20780 | 0.2027 | 57.7592 | 0.5945 | 0.3535 | 0.2079 | -0.1457 |
| RW | 10 | 20730 | 0.1243 | 37.1400 | 0.5670 | 0.4010 | 0.2187 | -0.1824 |
| RW | 22 | 20610 | 0.0333 | 11.3150 | 0.5355 | 0.5899 | 0.3396 | -0.2504 |
| RW | 42 | 20410 | 0.0055 | 2.2886 | 0.5200 | 0.7752 | 0.4697 | -0.3055 |

## §6 Conditional bias by IV-percentile bucket (h=22)
| model | horizon | iv_pctile_bucket | n | qlike | log_bias |
| --- | --- | --- | --- | --- | --- |
| RW | 22 | 0 | 5500 | 0.4775 | 0.0814 |
| RW | 22 | 1 | 3449 | 0.6928 | 0.0107 |
| RW | 22 | 2 | 3439 | 0.8362 | -0.0356 |
| RW | 22 | 3 | 3533 | 0.6137 | -0.1124 |
| RW | 22 | 4 | 4949 | 0.4535 | -0.3243 |

## §6 Post-shock calibration (h=22)
| model | horizon | bias_all | qlike_all | bias_postshock | qlike_postshock | n_postshock | trap_flag |
| --- | --- | --- | --- | --- | --- | --- | --- |
| RW | 22 | -0.0786 | 0.5895 | -0.4831 | 0.4979 | 3986 | ✓ |

## Per-ticker Tier-1 at h=22
| model | horizon | ticker | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| RW | 22 | EEM | 2087 | 0.6159 | 1.0147 | 0.7963 | -0.1049 | 0.8884 | 0.4557 | 0.0013 |
| RW | 22 | GLD | 2087 | 0.5243 | 0.9347 | 0.7394 | 0.0060 | 0.8519 | 0.4097 | 0.0006 |
| RW | 22 | HYG | 2087 | 0.9493 | 1.0050 | 0.7554 | -0.3570 | 0.9535 | 0.6162 | 0.0003 |
| RW | 22 | IWM | 2087 | 0.4863 | 0.7851 | 0.5924 | -0.0120 | 0.8658 | 0.4720 | 0.0014 |
| RW | 22 | QQQ | 2087 | 0.5054 | 0.8875 | 0.6871 | -0.1341 | 0.9003 | 0.5261 | 0.0012 |
| RW | 22 | SPY | 2087 | 0.8031 | 0.9715 | 0.7563 | -0.0278 | 0.8356 | 0.4590 | 0.0009 |
| RW | 22 | TLT | 2087 | 0.4425 | 0.8147 | 0.6297 | -0.0183 | 0.8620 | 0.4518 | 0.0005 |
| RW | 22 | XLE | 2087 | 0.4246 | 0.7429 | 0.5513 | -0.0111 | 0.8649 | 0.4873 | 0.0022 |
| RW | 22 | XLF | 2087 | 0.6149 | 0.8479 | 0.6379 | -0.0908 | 0.8931 | 0.5079 | 0.0014 |
| RW | 22 | XLK | 2087 | 0.5293 | 0.8625 | 0.6624 | -0.0356 | 0.8634 | 0.4835 | 0.0015 |

## Pooled by group
| model | group | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| RW | emerging_markets | 10465 | 0.6164 | 1.0709 | 0.8420 | -0.2095 | 0.8808 | 0.4558 | 0.0009 |
| RW | high_yield_credit | 10465 | 0.7051 | 0.9885 | 0.7524 | -0.3686 | 0.9420 | 0.6045 | 0.0002 |
| RW | oil_and_energy | 10465 | 0.3717 | 0.7379 | 0.5523 | -0.0635 | 0.8683 | 0.4921 | 0.0016 |
| RW | precious_metals | 10465 | 0.5557 | 1.0386 | 0.8153 | -0.1602 | 0.8652 | 0.4346 | 0.0005 |
| RW | us_cyclicals_sector | 10465 | 0.4800 | 0.8208 | 0.6209 | -0.1374 | 0.8977 | 0.5223 | 0.0011 |
| RW | us_large_cap_equity | 20930 | 0.5345 | 0.9034 | 0.7015 | -0.1369 | 0.8732 | 0.4879 | 0.0008 |
| RW | us_rates_and_ig_credit | 10465 | 0.4122 | 0.8604 | 0.6696 | -0.1191 | 0.8703 | 0.4649 | 0.0004 |
| RW | us_small_cap_equity | 10465 | 0.4017 | 0.7680 | 0.5806 | -0.0657 | 0.8669 | 0.4821 | 0.0010 |
| RW | us_technology_sector | 10465 | 0.4533 | 0.8492 | 0.6551 | -0.1016 | 0.8667 | 0.4825 | 0.0011 |
