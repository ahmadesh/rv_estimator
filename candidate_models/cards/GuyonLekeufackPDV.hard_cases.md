# GuyonLekeufackPDV — Model Card (hard_cases)

## Identity
- Model number (from MODEL_PLAN.md): 11
- Class: `candidate_models.pdv_glek:GuyonLekeufackPDV`
- Tier: PDV
- Implemented by: swarm worker (card generated 2026-06-01)

## Configuration
- Features used (list, by name): `ret_cc` (the plan's `ret_close`; falls back to `ret_close` if `ret_cc` absent), `rv_d` (daily realized variance = `total_rv`).
- 4-factor PDV spec (per (ticker, horizon)): `σ_t² = β₀ + β₁·R1_t + β₂·√R2_t`, where
  - `R1_t = (1-θ)·EWMA_short(r) + θ·EWMA_long(r)` (signed **trend** factor on close-to-close returns `r`),
  - `R2_t = (1-θ')·EWMA_short'(r²) + θ'·EWMA_long'(r²)` (**activity** factor on squared returns),
  - each EWMA is an exponential kernel maintained by the O(1) recursion `e_t = λ·e_{t-1} + z_t`.
- Parameters: 9 scalars `(β₀, β₁, β₂, θ, θ', λ_short, λ_long, λ_short', λ_long')`, **all fit by `scipy.optimize.minimize` (L-BFGS-B) — NO grid search**. Lambdas fit via the half-lives they imply.
- Hyperparameters (key=value — the FROZEN values used):
  - optimizer = scipy.optimize.minimize, method = L-BFGS-B, maxiter = 300
  - half-life seed (short) ≈ 8 trading days → λ_short = exp(-ln2/8) ≈ 0.917 (seeds optimizer only)
  - half-life seed (long) ≈ 250 trading days → λ_long = exp(-ln2/250) ≈ 0.99723 (seeds optimizer only)
  - bounds: β₀ ≥ 0; β₁ free; β₂ ≥ 0; θ, θ' ∈ [0, 1]; half-lives ∈ [1.5, 1000] days (i.e. λ ∈ [exp(-ln2/1.5), exp(-ln2/1000)])
  - fit objective = one-step log-MSE on `rv_d`: mean((log(σ_t²+ε) − log(rv_d_t+ε))²), ε = 1e-12
  - horizon forecast = multiplicative residual bootstrap, n_paths = 500
- HP selection (models 8–11): **none gridded** — the 9 scalars are all fit by the optimizer; the 8d/250d half-lives only *seed* it. No validation-block grid search was run (the §4 table lists "none" for model 11).
- Library version(s): scipy 1.17.1; numpy, polars (panel I/O).
- Random seed: numpy `Generator(0)` (seed 0) fixes the bootstrap draws.

## Training
- Universes run: clean_core, hard_cases
- Walk-forward folds: per the standard `rv_eval.walkforward` schedule; 146,471 OOS rows total covering all 15 scored tickers × 5 horizons {1,5,10,22,42}, min date 2018-01-02.
- Wall-clock time: clean_core 11129 s (≈ 185 min), hard_cases 2604 s (≈ 43 min)
- Device: cpu
- Convergence notes / per-ticker warnings: convergence policy is full 9-scalar L-BFGS-B fit, then a fixed-kernel 5-scalar fallback (4 half-lives frozen at seeds, only (β₀,β₁,β₂,θ,θ') re-fit) on optimizer failure/non-finite objective, then **drop** the key (never impute) if even the fallback fails. The variant used per key is recorded on `self.warnings` at fit time. All 146,471 rows cover all 15 tickers × 5 horizons with **none dropped**. The per-key full-vs-fixed-kernel split is **not recoverable from the predictions parquet** (the parquet carries no fit-variant column, and `self.warnings` is in-memory at fit time only), so it is not reported here rather than invented.

---

# GuyonLekeufackPDV — Self Stats
_universe=`hard_cases` · primary horizon h=22 · predictions=`execution/data/predictions/GuyonLekeufackPDV.parquet` · generated 2026-06-01T15:57:18Z_

_Self-only metrics — no leaderboard rank, no DM test, no MCS, no §9 status._
_Cross-model comparison is produced by the final `rv_eval.evaluator` pass._

## Tier-1 pooled by horizon (§3)
| model | horizon | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GuyonLekeufackPDV | 1 | 8235 | 0.6584 | 0.9470 | 0.7334 | -0.1865 | 0.7979 | 0.4270 | 0.0006 |
| GuyonLekeufackPDV | 5 | 8196 | 0.5712 | 0.8469 | 0.6453 | -0.1350 | 0.6878 | 0.3175 | 0.0027 |
| GuyonLekeufackPDV | 10 | 8151 | 0.5242 | 0.8325 | 0.6360 | -0.1506 | 0.6754 | 0.3050 | 0.0053 |
| GuyonLekeufackPDV | 22 | 8091 | 0.4848 | 0.7963 | 0.6066 | -0.1176 | 0.6190 | 0.2906 | 0.0106 |
| GuyonLekeufackPDV | 42 | 7948 | 0.4572 | 0.7543 | 0.5697 | -0.0713 | 0.5761 | 0.2636 | 0.0183 |

## §5 IV-incremental skill (per horizon)
| model | horizon | n | slope | t_slope | sign_acc | qlike_model | qlike_iv | qlike_gain_vs_iv |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GuyonLekeufackPDV | 1 | 7925 | -0.1344 | -3.8157 | 0.6279 | 0.6605 | 0.3600 | -0.3004 |
| GuyonLekeufackPDV | 5 | 7886 | 0.1111 | 4.8483 | 0.5789 | 0.5767 | 0.2624 | -0.3144 |
| GuyonLekeufackPDV | 10 | 7861 | 0.2035 | 10.1612 | 0.5418 | 0.5297 | 0.2543 | -0.2754 |
| GuyonLekeufackPDV | 22 | 7801 | 0.5408 | 33.3522 | 0.5493 | 0.4940 | 0.2735 | -0.2205 |
| GuyonLekeufackPDV | 42 | 7678 | 0.7143 | 50.1873 | 0.5991 | 0.4669 | 0.3139 | -0.1531 |

## §6 Conditional bias by IV-percentile bucket (h=22)
| model | horizon | iv_pctile_bucket | n | qlike | log_bias |
| --- | --- | --- | --- | --- | --- |
| GuyonLekeufackPDV | 22 | 0 | 2084 | 0.3186 | -0.4848 |
| GuyonLekeufackPDV | 22 | 1 | 1270 | 0.2494 | -0.3176 |
| GuyonLekeufackPDV | 22 | 2 | 1364 | 0.2676 | -0.1464 |
| GuyonLekeufackPDV | 22 | 3 | 1462 | 0.3496 | -0.0518 |
| GuyonLekeufackPDV | 22 | 4 | 1727 | 1.1710 | 0.4210 |

## §6 Post-shock calibration (h=22)
| model | horizon | bias_all | qlike_all | bias_postshock | qlike_postshock | n_postshock | trap_flag |
| --- | --- | --- | --- | --- | --- | --- | --- |
| GuyonLekeufackPDV | 22 | -0.1176 | 0.4848 | 0.3432 | 1.1591 | 1499 |  |

## Per-ticker Tier-1 at h=22
| model | horizon | ticker | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GuyonLekeufackPDV | 22 | IBIT | 537 | 0.1704 | 0.5786 | 0.4541 | -0.1281 | 0.8268 | 0.4451 | 0.0029 |
| GuyonLekeufackPDV | 22 | KRE | 2087 | 0.4735 | 0.7159 | 0.5055 | -0.0442 | 0.7072 | 0.3685 | 0.0021 |
| GuyonLekeufackPDV | 22 | MSOS | 1293 | 0.2431 | 0.6273 | 0.5192 | 0.1396 | 0.4841 | 0.1671 | 0.0077 |
| GuyonLekeufackPDV | 22 | USO | 2087 | 0.8016 | 0.8444 | 0.6047 | 0.1123 | 0.5860 | 0.2520 | 0.0045 |
| GuyonLekeufackPDV | 22 | UVXY | 2087 | 0.4099 | 0.9501 | 0.8029 | -0.5777 | 0.5937 | 0.2880 | 0.0290 |

## Pooled by group
| model | group | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GuyonLekeufackPDV | crypto | 2735 | 0.2851 | 0.6988 | 0.5435 | -0.1938 | 0.8512 | 0.4801 | 0.0021 |
| GuyonLekeufackPDV | long_volatility_vix | 10465 | 0.5330 | 1.0111 | 0.8319 | -0.5018 | 0.6064 | 0.2723 | 0.0203 |
| GuyonLekeufackPDV | oil_and_energy | 10465 | 0.7767 | 0.8634 | 0.6337 | 0.0680 | 0.6388 | 0.2953 | 0.0032 |
| GuyonLekeufackPDV | us_cannabis | 6491 | 0.3124 | 0.6837 | 0.5423 | 0.0557 | 0.6101 | 0.2704 | 0.0053 |
| GuyonLekeufackPDV | us_cyclicals_sector | 10465 | 0.5178 | 0.7377 | 0.5356 | -0.0650 | 0.7626 | 0.3862 | 0.0015 |
