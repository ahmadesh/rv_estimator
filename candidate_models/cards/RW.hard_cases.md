# RW — Model Card (hard_cases)

## Identity
- Model number (from MODEL_PLAN.md): 0
- Class: rv_eval.model_contract:RandomWalk (benchmark — already coded; no candidate file written)
- Tier: Baseline
- Implemented by: swarm worker, 2026-05-31

## Configuration
- Features used (list, by name): rv_d. rv_hat = h * rv_d, lognormal-mean corrected. Sigma from per-(ticker,horizon) log-residual std.
- Hyperparameters (key=value): none — RandomWalk has no free hyperparameters. min_obs=30.
- HP selection (models 8–11): N/A — model 0 is not tuned.
- Library version(s): python 3.12.13, numpy 2.4.6, scipy 1.17.1, polars 1.41.1
- Random seed: N/A — deterministic.

## Training
- Universes run: clean_core, hard_cases (this card = hard_cases)
- Walk-forward folds: monthly refit, expanding window, OOS span 2018-01-02 → 2026-05-22 (purged + embargoed; EMBARGO_EXTRA=1).
- Wall-clock time: clean_core: 6.7s, hard_cases: 3.5s
- Device: cpu
- Convergence notes / per-ticker warnings: No convergence step (naive model). All 5 hard-case tickers covered at every horizon, but IBIT (~2y options history; 620 rows at h=22, 3,212 total) and MSOS (thin; 1,353 rows at h=22) are genuinely short series. No rows imputed — coverage differs from the dense tickers and matters for the comparison pass's common-support joins.

## OOS self-stats (this model alone)
- QLIKE pooled by horizon (h=1/5/10/22/42): 0.4544 / 0.4286 / 0.4736 / 0.6054 / 0.7006.
- §5 IV-incremental skill at h=22: slope=-0.0137, t=-3.93, sign_acc=0.5748, qlike_gain_vs_iv=-0.3019 (IV-as-forecast clearly beats RW on the hard cases).
- §6 conditional bias by IV-pctile bucket at h=22 (log_bias, buckets 0→4): +0.1017 / +0.0466 / +0.0312 / -0.1257 / -0.3246.
- §6 post-shock bias at h=22: bias_all=-0.0655, bias_postshock=-0.5533 (n=1,535), trap_flag=✓.
- 50% / 90% interval coverage at h=22: cov50=0.4864, cov90=0.8643.

## Per-ticker QLIKE at h=22 (hard_cases)
| ticker | qlike | notes |
|---|---|---|
| IBIT | 0.7075 | n=620 (short history); strong neg bias -0.414 |
| KRE | 0.5298 | |
| MSOS | 0.4287 | n=1353 (thin) |
| USO | 0.5473 | only ticker with positive bias (+0.072) |
| UVXY | 0.8235 | worst qlike; high-vol VIX product, large pinball 0.036 |

## Anomalies / things the next reader should know
- RW is the comparison floor; it has no IV awareness and loses to IV-as-forecast at all horizons on the hard cases.
- IBIT and MSOS have materially fewer OOS rows — relevant for common-support joins downstream.

## Reproduce
```bash
.venv/bin/python -m rv_eval.walkforward --model rv_eval.model_contract:RandomWalk --universe clean_core
.venv/bin/python -m rv_eval.walkforward --model rv_eval.model_contract:RandomWalk --universe hard_cases
.venv/bin/python -m rv_eval.selfstats --pred execution/data/predictions/RW.parquet --out candidate_models/cards/RW.md --universe clean_core
.venv/bin/python -m rv_eval.selfstats --pred execution/data/predictions/RW.parquet --out candidate_models/cards/RW.hard_cases.md --universe hard_cases
```

---

# RW — Self Stats
_universe=`hard_cases` · primary horizon h=22 · predictions=`/Users/ahmade/Documents/rv_estimator/execution/data/predictions/RW.parquet` · generated 2026-06-01T02:56:16Z_

_Self-only metrics — no leaderboard rank, no DM test, no MCS, no §9 status._
_Cross-model comparison is produced by the final `rv_eval.evaluator` pass._

## Tier-1 pooled by horizon (§3)
| model | horizon | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| RW | 1 | 8373 | 0.4544 | 0.9873 | 0.7493 | -0.3826 | 0.8956 | 0.5389 | 0.0005 |
| RW | 5 | 8339 | 0.4286 | 0.8596 | 0.6487 | -0.1568 | 0.8854 | 0.5184 | 0.0027 |
| RW | 10 | 8314 | 0.4736 | 0.8792 | 0.6650 | -0.1118 | 0.8759 | 0.5029 | 0.0057 |
| RW | 22 | 8234 | 0.6054 | 0.9210 | 0.6976 | -0.0655 | 0.8643 | 0.4864 | 0.0133 |
| RW | 42 | 8100 | 0.7006 | 0.9632 | 0.7283 | -0.0304 | 0.8570 | 0.4694 | 0.0258 |

## §5 IV-incremental skill (per horizon)
| model | horizon | n | slope | t_slope | sign_acc | qlike_model | qlike_iv | qlike_gain_vs_iv |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| RW | 1 | 7955 | 0.2183 | 28.9281 | 0.6378 | 0.4168 | 0.3620 | -0.0549 |
| RW | 5 | 7935 | 0.0894 | 17.3680 | 0.6381 | 0.4059 | 0.2634 | -0.1425 |
| RW | 10 | 7910 | 0.0377 | 8.6747 | 0.6091 | 0.4582 | 0.2549 | -0.2033 |
| RW | 22 | 7850 | -0.0137 | -3.9260 | 0.5748 | 0.5754 | 0.2735 | -0.3019 |
| RW | 42 | 7739 | -0.0146 | -5.0674 | 0.5547 | 0.6621 | 0.3146 | -0.3475 |

## §6 Conditional bias by IV-percentile bucket (h=22)
| model | horizon | iv_pctile_bucket | n | qlike | log_bias |
| --- | --- | --- | --- | --- | --- |
| RW | 22 | 0 | 2085 | 0.7209 | 0.1017 |
| RW | 22 | 1 | 1279 | 0.4895 | 0.0466 |
| RW | 22 | 2 | 1369 | 0.5339 | 0.0312 |
| RW | 22 | 3 | 1471 | 0.5205 | -0.1257 |
| RW | 22 | 4 | 1752 | 0.5820 | -0.3246 |

## §6 Post-shock calibration (h=22)
| model | horizon | bias_all | qlike_all | bias_postshock | qlike_postshock | n_postshock | trap_flag |
| --- | --- | --- | --- | --- | --- | --- | --- |
| RW | 22 | -0.0655 | 0.6054 | -0.5533 | 0.5613 | 1535 | ✓ |

## Per-ticker Tier-1 at h=22
| model | horizon | ticker | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| RW | 22 | IBIT | 620 | 0.7075 | 1.1077 | 0.8493 | -0.4143 | 0.9548 | 0.5952 | 0.0085 |
| RW | 22 | KRE | 2087 | 0.5298 | 0.7905 | 0.5803 | -0.0607 | 0.8970 | 0.5256 | 0.0024 |
| RW | 22 | MSOS | 1353 | 0.4287 | 0.8409 | 0.6339 | -0.0424 | 0.8640 | 0.5351 | 0.0106 |
| RW | 22 | USO | 2087 | 0.5473 | 0.8805 | 0.6768 | 0.0719 | 0.8055 | 0.3896 | 0.0045 |
| RW | 22 | UVXY | 2087 | 0.8235 | 1.0600 | 0.8318 | -0.1188 | 0.8639 | 0.4801 | 0.0362 |

## Pooled by group
| model | group | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| RW | crypto | 3132 | 0.7799 | 1.3043 | 0.9907 | -0.6386 | 0.9579 | 0.6242 | 0.0061 |
| RW | long_volatility_vix | 10465 | 0.6361 | 1.0041 | 0.7909 | -0.1807 | 0.8749 | 0.4864 | 0.0257 |
| RW | oil_and_energy | 10465 | 0.5355 | 0.9125 | 0.7034 | -0.0418 | 0.8235 | 0.4197 | 0.0033 |
| RW | us_cannabis | 6833 | 0.4246 | 0.8232 | 0.6163 | -0.1174 | 0.8841 | 0.5492 | 0.0075 |
| RW | us_cyclicals_sector | 10465 | 0.4178 | 0.7589 | 0.5642 | -0.1046 | 0.8990 | 0.5383 | 0.0018 |
