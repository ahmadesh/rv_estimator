# LSTMRV — Model Card

## Identity
- Model number (from MODEL_PLAN.md): 10
- Class: `candidate_models.lstm_rv:LSTMRV`
- Tier: DL
- Implemented by: card generated 2026-06-01 (model code/predictions pre-existing & validated)

## Configuration
- Window features (8, 60-day rolling window):
  - `log_rv_d`, `log_iv`, `vix`, `vix_slope`, `iv_slope`, `skew_25d`, `rs_minus_5d`, `rs_plus_5d`
- Window length: 60 days. One shared multi-head LSTM per ticker (one linear head per horizon over horizons {1,5,10,22,42}).
- Target: `log(target_var)`; `rv_hat = exp(mu + 0.5*sigma^2)` (lognormal-mean back-transform), quantiles via `_lognormal_quantiles`.
- Hyperparameters (FROZEN — tune-once-then-freeze):
  - `hidden=64`
  - `num_layers=1`
  - `dropout=0.1`
  - `lr=5e-4`
- Fixed params (not gridded):
  - `batch_size=64`
  - optimizer `Adam`
  - `epochs`: chosen per fit by early stopping (patience 8) on a 10% time-ordered within-train tail; cap 80.
- `sigma`: per-horizon residual std of `log(target_var)` on the held-out 10% tail (floored at 1e-3).
- HP selection (model 10): leakage-safe tune-once-then-freeze. Search-train = `date < 2016-01-01`; validation block = `[2016-01-01, 2018-01-01)` (2016–2017, no OOS read). Grid = 24 points: `hidden∈{32,64,128}` × `num_layers∈{1,2}` × `dropout∈{0.1,0.2}` × `lr∈{5e-4,1e-3}`, tuned on `HPTUNE_DL_SUBSET` (SPY, QQQ, TLT, XLE) to bound compute. Selection metric = pooled QLIKE @ h=22. Chosen = `(hidden=64, num_layers=1, dropout=0.1, lr=5e-4)` with validation QLIKE@h22 = 0.210004; grid initial point `(64,2,0.1,1e-3)` scored 0.412826. All 2-layer configs scored 0.36–0.87; 1-layer clearly wins. Recorded in `candidate_models/lstm_rv.py` docstring and `candidate_models/_tune_lstm.py` (tuning run 2026-06-01).
- Library version(s): torch 2.12.0
- Random seed: torch=0, numpy=0

## Training
- Universes run: clean_core, hard_cases
- Wall-clock time: clean_core 10999s, hard_cases 2999s
- Device: mps
- Coverage: 142,495 OOS rows cover all 15 scored tickers × 5 horizons {1,5,10,22,42}, min date 2018-01-02; `rv_hat` finite & >0, quantiles monotone. IBIT (1,225 rows) and MSOS (6,010 rows) are thin due to short IV-feature history.
- Convergence notes: no per-ticker fit failures. NOTE the predict-context fix: the first full walk-forward produced ZERO predictions because the harness passes `predict()` only the ~21-day test-month slice, which is shorter than the 60-day window, so every fold had n < WINDOW and emitted nothing. The model was fixed to cache the last 59 raw feature rows per ticker during `fit()` and prepend them at `predict()` time, giving every test date its full backward-only (leakage-safe) window; a regression test reproduces the small-slice contract.

---

# LSTMRV — Self Stats
_universe=`clean_core` · primary horizon h=22 · predictions=`execution/data/predictions/LSTMRV.parquet` · generated 2026-06-01T18:42:59Z_

_Self-only metrics — no leaderboard rank, no DM test, no MCS, no §9 status._
_Cross-model comparison is produced by the final `rv_eval.evaluator` pass._

## Tier-1 pooled by horizon (§3)
| model | horizon | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LSTMRV | 1 | 20810 | 0.3366 | 0.8641 | 0.6701 | -0.3330 | 0.8963 | 0.4952 | 0.0001 |
| LSTMRV | 5 | 20770 | 0.2143 | 0.6323 | 0.4802 | -0.1592 | 0.8874 | 0.5111 | 0.0002 |
| LSTMRV | 10 | 20720 | 0.2311 | 0.6158 | 0.4609 | -0.1370 | 0.8796 | 0.5167 | 0.0004 |
| LSTMRV | 22 | 20600 | 0.3716 | 0.6537 | 0.4764 | -0.1163 | 0.8520 | 0.5020 | 0.0009 |
| LSTMRV | 42 | 20400 | 0.4997 | 0.7445 | 0.5328 | -0.1388 | 0.8149 | 0.4835 | 0.0018 |

## §5 IV-incremental skill (per horizon)
| model | horizon | n | slope | t_slope | sign_acc | qlike_model | qlike_iv | qlike_gain_vs_iv |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LSTMRV | 1 | 20810 | 0.0087 | 8.4541 | 0.6170 | 0.3366 | 0.3277 | -0.0089 |
| LSTMRV | 5 | 20770 | 0.0288 | 12.2832 | 0.5947 | 0.2143 | 0.2079 | -0.0063 |
| LSTMRV | 10 | 20720 | 0.0191 | 5.1766 | 0.5495 | 0.2311 | 0.2187 | -0.0124 |
| LSTMRV | 22 | 20600 | -0.0345 | -5.1222 | 0.5098 | 0.3716 | 0.3397 | -0.0319 |
| LSTMRV | 42 | 20400 | -0.0557 | -7.0159 | 0.4839 | 0.4997 | 0.4699 | -0.0298 |

## §6 Conditional bias by IV-percentile bucket (h=22)
| model | horizon | iv_pctile_bucket | n | qlike | log_bias |
| --- | --- | --- | --- | --- | --- |
| LSTMRV | 22 | 0 | 5240 | 0.1964 | -0.1981 |
| LSTMRV | 22 | 1 | 3448 | 0.3625 | -0.1714 |
| LSTMRV | 22 | 2 | 3439 | 0.5231 | -0.1228 |
| LSTMRV | 22 | 3 | 3533 | 0.4134 | -0.0623 |
| LSTMRV | 22 | 4 | 4940 | 0.4286 | -0.0250 |

## §6 Post-shock calibration (h=22)
| model | horizon | bias_all | qlike_all | bias_postshock | qlike_postshock | n_postshock | trap_flag |
| --- | --- | --- | --- | --- | --- | --- | --- |
| LSTMRV | 22 | -0.1163 | 0.3716 | -0.0568 | 0.4257 | 3921 |  |

## Per-ticker Tier-1 at h=22
| model | horizon | ticker | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LSTMRV | 22 | EEM | 2060 | 0.2611 | 0.6099 | 0.4667 | -0.1556 | 0.8359 | 0.4951 | 0.0008 |
| LSTMRV | 22 | GLD | 2060 | 0.1765 | 0.5347 | 0.4062 | -0.1064 | 0.7383 | 0.4447 | 0.0004 |
| LSTMRV | 22 | HYG | 2060 | 0.9020 | 0.9165 | 0.7058 | -0.3502 | 0.8617 | 0.4626 | 0.0002 |
| LSTMRV | 22 | IWM | 2060 | 0.3176 | 0.5569 | 0.3954 | 0.0159 | 0.8859 | 0.5316 | 0.0010 |
| LSTMRV | 22 | QQQ | 2060 | 0.3301 | 0.7014 | 0.4934 | -0.0250 | 0.8602 | 0.4772 | 0.0015 |
| LSTMRV | 22 | SPY | 2060 | 0.4538 | 0.7246 | 0.5555 | -0.1484 | 0.8772 | 0.5495 | 0.0007 |
| LSTMRV | 22 | TLT | 2060 | 0.2182 | 0.5632 | 0.3768 | -0.0857 | 0.8364 | 0.5112 | 0.0006 |
| LSTMRV | 22 | XLE | 2060 | 0.3115 | 0.5526 | 0.3967 | -0.0753 | 0.8840 | 0.5165 | 0.0015 |
| LSTMRV | 22 | XLF | 2060 | 0.4148 | 0.6647 | 0.5119 | -0.1809 | 0.8592 | 0.4796 | 0.0011 |
| LSTMRV | 22 | XLK | 2060 | 0.3307 | 0.6195 | 0.4557 | -0.0510 | 0.8816 | 0.5524 | 0.0011 |

## Pooled by group
| model | group | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LSTMRV | emerging_markets | 10330 | 0.3055 | 0.7390 | 0.5685 | -0.2356 | 0.8525 | 0.4851 | 0.0006 |
| LSTMRV | high_yield_credit | 10330 | 0.6576 | 0.9071 | 0.6978 | -0.3619 | 0.8754 | 0.4707 | 0.0002 |
| LSTMRV | oil_and_energy | 10330 | 0.2685 | 0.5737 | 0.4229 | -0.1135 | 0.8833 | 0.5089 | 0.0011 |
| LSTMRV | precious_metals | 10330 | 0.2386 | 0.6832 | 0.5236 | -0.2044 | 0.7923 | 0.4389 | 0.0003 |
| LSTMRV | us_cyclicals_sector | 10330 | 0.3342 | 0.6638 | 0.5113 | -0.1950 | 0.8744 | 0.5022 | 0.0008 |
| LSTMRV | us_large_cap_equity | 20660 | 0.3502 | 0.7708 | 0.5626 | -0.1662 | 0.8754 | 0.5137 | 0.0009 |
| LSTMRV | us_rates_and_ig_credit | 10330 | 0.2371 | 0.6891 | 0.4815 | -0.1756 | 0.8576 | 0.5142 | 0.0005 |
| LSTMRV | us_small_cap_equity | 10330 | 0.2687 | 0.5766 | 0.4230 | -0.0455 | 0.8873 | 0.5370 | 0.0007 |
| LSTMRV | us_technology_sector | 10330 | 0.2897 | 0.6438 | 0.4885 | -0.1077 | 0.8891 | 0.5331 | 0.0008 |
