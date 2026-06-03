# LSTMRV — Model Card (hard_cases)

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
- Coverage: 142,495 OOS rows (both universes) cover all 15 scored tickers × 5 horizons {1,5,10,22,42}, min date 2018-01-02; `rv_hat` finite & >0, quantiles monotone. Among the hard cases, IBIT (1,225 rows; 224 at h=22) and MSOS (6,010 rows; 1,181 at h=22) are thin due to short IV-feature history.
- Convergence notes: no per-ticker fit failures. NOTE the predict-context fix: the first full walk-forward produced ZERO predictions because the harness passes `predict()` only the ~21-day test-month slice, which is shorter than the 60-day window, so every fold had n < WINDOW and emitted nothing. The model was fixed to cache the last 59 raw feature rows per ticker during `fit()` and prepend them at `predict()` time, giving every test date its full backward-only (leakage-safe) window; a regression test reproduces the small-slice contract.

---

# LSTMRV — Self Stats
_universe=`hard_cases` · primary horizon h=22 · predictions=`execution/data/predictions/LSTMRV.parquet` · generated 2026-06-01T18:42:59Z_

_Self-only metrics — no leaderboard rank, no DM test, no MCS, no §9 status._
_Cross-model comparison is produced by the final `rv_eval.evaluator` pass._

## Tier-1 pooled by horizon (§3)
| model | horizon | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LSTMRV | 1 | 7689 | 0.4499 | 1.1532 | 0.7782 | -0.4770 | 0.8672 | 0.4986 | 0.0039 |
| LSTMRV | 5 | 7669 | 0.3238 | 0.8339 | 0.5608 | -0.2077 | 0.8506 | 0.5083 | 0.0061 |
| LSTMRV | 10 | 7644 | 0.3138 | 0.7596 | 0.5260 | -0.1547 | 0.8281 | 0.5072 | 0.0075 |
| LSTMRV | 22 | 7584 | 0.3383 | 0.7194 | 0.5194 | -0.0890 | 0.8006 | 0.4722 | 0.0119 |
| LSTMRV | 42 | 7484 | 0.3595 | 0.7202 | 0.5276 | -0.0668 | 0.7618 | 0.4308 | 0.0185 |

## §5 IV-incremental skill (per horizon)
| model | horizon | n | slope | t_slope | sign_acc | qlike_model | qlike_iv | qlike_gain_vs_iv |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LSTMRV | 1 | 7689 | -0.0002 | -0.2247 | 0.6330 | 0.4499 | 0.3567 | -0.0933 |
| LSTMRV | 5 | 7669 | 0.0056 | 2.0269 | 0.6458 | 0.3238 | 0.2613 | -0.0626 |
| LSTMRV | 10 | 7644 | 0.0154 | 2.5966 | 0.6154 | 0.3138 | 0.2538 | -0.0600 |
| LSTMRV | 22 | 7584 | 0.1203 | 10.5015 | 0.5708 | 0.3383 | 0.2749 | -0.0634 |
| LSTMRV | 42 | 7484 | 0.3800 | 31.1016 | 0.5810 | 0.3595 | 0.3169 | -0.0426 |

## §6 Conditional bias by IV-percentile bucket (h=22)
| model | horizon | iv_pctile_bucket | n | qlike | log_bias |
| --- | --- | --- | --- | --- | --- |
| LSTMRV | 22 | 0 | 1849 | 0.3089 | -0.2057 |
| LSTMRV | 22 | 1 | 1228 | 0.2547 | -0.1069 |
| LSTMRV | 22 | 2 | 1335 | 0.2691 | -0.0873 |
| LSTMRV | 22 | 3 | 1451 | 0.3490 | -0.0590 |
| LSTMRV | 22 | 4 | 1721 | 0.4743 | 0.0224 |

## §6 Post-shock calibration (h=22)
| model | horizon | bias_all | qlike_all | bias_postshock | qlike_postshock | n_postshock | trap_flag |
| --- | --- | --- | --- | --- | --- | --- | --- |
| LSTMRV | 22 | -0.0890 | 0.3383 | -0.0609 | 0.3899 | 1413 |  |

## Per-ticker Tier-1 at h=22
| model | horizon | ticker | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LSTMRV | 22 | IBIT | 224 | 0.1661 | 0.6393 | 0.5192 | -0.1596 | 0.6295 | 0.1875 | 0.0025 |
| LSTMRV | 22 | KRE | 2060 | 0.3550 | 0.5852 | 0.4066 | -0.0526 | 0.8796 | 0.5485 | 0.0017 |
| LSTMRV | 22 | MSOS | 1181 | 0.4372 | 0.9633 | 0.6703 | 0.1989 | 0.5614 | 0.2887 | 0.0233 |
| LSTMRV | 22 | USO | 2060 | 0.2514 | 0.6157 | 0.4469 | -0.0685 | 0.8432 | 0.5150 | 0.0033 |
| LSTMRV | 22 | UVXY | 2059 | 0.3706 | 0.7795 | 0.6183 | -0.3034 | 0.8349 | 0.4891 | 0.0251 |

## Pooled by group
| model | group | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LSTMRV | crypto | 1150 | 0.3273 | 1.0226 | 0.7191 | -0.3701 | 0.5739 | 0.2183 | 0.0020 |
| LSTMRV | long_volatility_vix | 10325 | 0.3800 | 0.9040 | 0.6831 | -0.3873 | 0.8589 | 0.4921 | 0.0183 |
| LSTMRV | oil_and_energy | 10330 | 0.3035 | 0.7566 | 0.5423 | -0.1904 | 0.8594 | 0.5172 | 0.0029 |
| LSTMRV | us_cannabis | 5935 | 0.5127 | 1.2042 | 0.7265 | -0.0510 | 0.6298 | 0.3427 | 0.0216 |
| LSTMRV | us_cyclicals_sector | 10330 | 0.3020 | 0.5916 | 0.4260 | -0.0895 | 0.8858 | 0.5523 | 0.0013 |
