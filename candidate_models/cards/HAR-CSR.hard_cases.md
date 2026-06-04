# HAR-CSR — Self Stats
_universe=`hard_cases` · primary horizon h=22 · predictions=`execution/data/predictions/HAR-CSR.parquet` · generated 2026-06-03T21:43:47Z_

_Self-only metrics — no leaderboard rank, no DM test, no MCS, no §9 status._
_Cross-model comparison is produced by the final `rv_eval.evaluator` pass._

## Build notes (human-only fields — MODEL_PLAN §5)
- **Model:** ITER2 catalog §3 model 20 — HAR-CSR (complete-subset regression). Class `HARCSR`,
  `name="HAR-CSR"`, file `candidate_models/har_csr.py`. Pattern P2 over `_PerKeyModel`.
- **Features used (K=8, all pass-through from `build_features`, no derived/rolling join):**
  `log_rv_d, log_rv_w, log_rv_m, rs_minus_5d, jump_5d, log_iv, vix, sqrt_rq`.
- **Subset scheme (FROZEN by catalog spec, not OOS-tuned):** k=4 of K=8 ⇒ C(8,4)=**70** complete
  subsets = the catalog cap exactly ⇒ FULL enumeration, **no sampling / no seed draw** (seeded
  `rng(0)` fallback wired only as a guard if C(K,k) ever exceeds `_MAX_SUBSETS=70`). Point
  forecast = equal-weight mean of the 70 per-subset lognormal means; log-sd = mean of per-subset
  in-sample log-residual sds.
- **Library versions:** numpy 2.4.6, scipy 1.17.1, polars 1.41.1, scikit-learn 1.8.0 (sklearn
  not used — plain `np.linalg.lstsq`).
- **Wall-time / device:** hard_cases walk-forward 17.3s (38,512 OOS preds). Device: Apple Silicon
  arm64 (macOS 15.3.1), single process.
- **Coverage warnings:** all 5 hard-case tickers × 5 horizons covered, OOS span
  2018-01-02 → 2026-05-21. **IBIT** (224 rows at h=22) and **MSOS** (1181) have short live
  histories ⇒ small per-ticker n and noisier coverage (IBIT cov90≈0.76). **USO / oil_and_energy
  pinball is enormous at h≥10** (USO h=22 pinball ≈ 1.6e4; group ≈ 1.8e4): a handful of extreme
  oil-RV outlier days (2020 negative-oil shock) blow up the level-space pinball and `log_rmse`
  (USO log_rmse 1.09) even though pooled QLIKE stays ≈0.28 — this is an outlier-driven
  level-metric artifact, not a calibration failure of the central forecast. Persistent negative
  `log_bias` (shrinkage center-pull), strongest on UVXY (-0.34) and post-shock (-0.23). No NaN
  rows, no dropped (ticker,horizon).

## Tier-1 pooled by horizon (§3)
| model | horizon | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-CSR | 1 | 7732 | 0.3234 | 0.8017 | 0.5997 | -0.2682 | 0.9014 | 0.5243 | 0.0150 |
| HAR-CSR | 5 | 7712 | 0.2590 | 0.6892 | 0.4875 | -0.1733 | 0.8998 | 0.5354 | 0.2198 |
| HAR-CSR | 10 | 7666 | 0.2685 | 0.8177 | 0.4800 | -0.1531 | 0.8963 | 0.5407 | 14326.6744 |
| HAR-CSR | 22 | 7584 | 0.2914 | 0.7927 | 0.4794 | -0.1109 | 0.8912 | 0.5256 | 4458.9726 |
| HAR-CSR | 42 | 7443 | 0.3217 | 0.8051 | 0.4875 | -0.0754 | 0.8716 | 0.5118 | 5659.1409 |

## §5 IV-incremental skill (per horizon)
| model | horizon | n | slope | t_slope | sign_acc | qlike_model | qlike_iv | qlike_gain_vs_iv |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-CSR | 1 | 7732 | -0.0000 | -0.5308 | 0.7363 | 0.3234 | 0.3574 | 0.0339 |
| HAR-CSR | 5 | 7712 | -0.0000 | -0.9892 | 0.6909 | 0.2590 | 0.2620 | 0.0030 |
| HAR-CSR | 10 | 7666 | -0.0000 | -0.0006 | 0.6462 | 0.2685 | 0.2546 | -0.0140 |
| HAR-CSR | 22 | 7584 | -0.0000 | -0.0053 | 0.5990 | 0.2914 | 0.2749 | -0.0165 |
| HAR-CSR | 42 | 7443 | -0.0000 | -0.0055 | 0.5968 | 0.3217 | 0.3177 | -0.0041 |

## §6 Conditional bias by IV-percentile bucket (h=22)
| model | horizon | iv_pctile_bucket | n | qlike | log_bias |
| --- | --- | --- | --- | --- | --- |
| HAR-CSR | 22 | 0 | 1849 | 0.2956 | -0.1619 |
| HAR-CSR | 22 | 1 | 1228 | 0.2370 | -0.1004 |
| HAR-CSR | 22 | 2 | 1335 | 0.2381 | -0.0573 |
| HAR-CSR | 22 | 3 | 1451 | 0.2517 | -0.0922 |
| HAR-CSR | 22 | 4 | 1721 | 0.4006 | -0.1208 |

## §6 Post-shock calibration (h=22)
| model | horizon | bias_all | qlike_all | bias_postshock | qlike_postshock | n_postshock | trap_flag |
| --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-CSR | 22 | -0.1109 | 0.2914 | -0.2314 | 0.3690 | 1413 |  |

## Per-ticker Tier-1 at h=22
| model | horizon | ticker | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-CSR | 22 | IBIT | 224 | 0.1289 | 0.5458 | 0.4372 | -0.1783 | 0.7634 | 0.3750 | 0.0020 |
| HAR-CSR | 22 | KRE | 2060 | 0.3252 | 0.5795 | 0.4130 | -0.0617 | 0.9359 | 0.6029 | 0.0017 |
| HAR-CSR | 22 | MSOS | 1181 | 0.2217 | 0.5704 | 0.4228 | 0.1321 | 0.8383 | 0.5402 | 0.0069 |
| HAR-CSR | 22 | USO | 2060 | 0.2831 | 1.0930 | 0.4522 | -0.0679 | 0.8631 | 0.5000 | 16415.9171 |
| HAR-CSR | 22 | UVXY | 2059 | 0.3236 | 0.7511 | 0.6102 | -0.3351 | 0.9189 | 0.4818 | 0.0226 |

## Pooled by group
| model | group | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-CSR | crypto | 1172 | 0.1802 | 0.6460 | 0.5051 | -0.2413 | 0.8686 | 0.4514 | 0.0014 |
| HAR-CSR | long_volatility_vix | 10325 | 0.3202 | 0.7837 | 0.6336 | -0.3560 | 0.9056 | 0.4865 | 0.0159 |
| HAR-CSR | oil_and_energy | 10330 | 0.3060 | 1.0245 | 0.5070 | -0.1279 | 0.8625 | 0.4900 | 17983.3227 |
| HAR-CSR | us_cannabis | 5980 | 0.2745 | 0.6155 | 0.4455 | 0.0313 | 0.8607 | 0.5492 | 0.0049 |
| HAR-CSR | us_cyclicals_sector | 10330 | 0.2752 | 0.5744 | 0.4168 | -0.0865 | 0.9294 | 0.6026 | 0.0012 |
