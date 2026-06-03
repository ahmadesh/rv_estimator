# GuyonLekeufackPDV — Model Card

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
_universe=`clean_core` · primary horizon h=22 · predictions=`execution/data/predictions/GuyonLekeufackPDV.parquet` · generated 2026-06-01T15:57:18Z_

_Self-only metrics — no leaderboard rank, no DM test, no MCS, no §9 status._
_Cross-model comparison is produced by the final `rv_eval.evaluator` pass._

## Tier-1 pooled by horizon (§3)
| model | horizon | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GuyonLekeufackPDV | 1 | 21080 | 0.8185 | 1.8809 | 0.9883 | -0.4364 | 0.7905 | 0.3969 | 15.9745 |
| GuyonLekeufackPDV | 5 | 21040 | 1.4046 | 3.7875 | 1.4234 | -0.9082 | 0.6395 | 0.2895 | 994.8664 |
| GuyonLekeufackPDV | 10 | 20990 | 1.4529 | 3.9598 | 1.4600 | -0.9698 | 0.6182 | 0.2700 | 1424.6804 |
| GuyonLekeufackPDV | 22 | 20870 | 1.6998 | 4.4460 | 1.5992 | -1.0900 | 0.5762 | 0.2570 | 4153.5836 |
| GuyonLekeufackPDV | 42 | 20670 | 1.5840 | 4.6215 | 1.6722 | -1.1390 | 0.5043 | 0.2206 | 3115.8360 |

## §5 IV-incremental skill (per horizon)
| model | horizon | n | slope | t_slope | sign_acc | qlike_model | qlike_iv | qlike_gain_vs_iv |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GuyonLekeufackPDV | 1 | 20820 | -0.0000 | -0.0005 | 0.5093 | 0.8230 | 0.3276 | -0.4954 |
| GuyonLekeufackPDV | 5 | 20780 | -0.0000 | -0.0001 | 0.4594 | 1.4106 | 0.2079 | -1.2027 |
| GuyonLekeufackPDV | 10 | 20730 | -0.0000 | -0.0001 | 0.4554 | 1.4662 | 0.2187 | -1.2475 |
| GuyonLekeufackPDV | 22 | 20610 | -0.0000 | -0.0000 | 0.4795 | 1.7139 | 0.3396 | -1.3743 |
| GuyonLekeufackPDV | 42 | 20410 | -0.0000 | -0.0000 | 0.4897 | 1.5925 | 0.4697 | -1.1228 |

## §6 Conditional bias by IV-percentile bucket (h=22)
| model | horizon | iv_pctile_bucket | n | qlike | log_bias |
| --- | --- | --- | --- | --- | --- |
| GuyonLekeufackPDV | 22 | 0 | 5500 | 1.4133 | -1.7070 |
| GuyonLekeufackPDV | 22 | 1 | 3449 | 1.2566 | -1.4019 |
| GuyonLekeufackPDV | 22 | 2 | 3439 | 1.5902 | -1.1267 |
| GuyonLekeufackPDV | 22 | 3 | 3533 | 1.3408 | -0.6761 |
| GuyonLekeufackPDV | 22 | 4 | 4949 | 2.6594 | -0.4568 |

## §6 Post-shock calibration (h=22)
| model | horizon | bias_all | qlike_all | bias_postshock | qlike_postshock | n_postshock | trap_flag |
| --- | --- | --- | --- | --- | --- | --- | --- |
| GuyonLekeufackPDV | 22 | -1.0900 | 1.6998 | -0.5439 | 2.8326 | 3986 |  |

## Per-ticker Tier-1 at h=22
| model | horizon | ticker | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GuyonLekeufackPDV | 22 | EEM | 2087 | 0.4278 | 0.7227 | 0.5591 | -0.1389 | 0.7499 | 0.3584 | 0.0009 |
| GuyonLekeufackPDV | 22 | GLD | 2087 | 0.2908 | 0.7141 | 0.5695 | -0.2492 | 0.6100 | 0.2602 | 0.0005 |
| GuyonLekeufackPDV | 22 | HYG | 2087 | 9.5379 | 13.8289 | 10.4889 | -10.4561 | 0.0786 | 0.0139 | 41535.8217 |
| GuyonLekeufackPDV | 22 | IWM | 2087 | 0.6948 | 0.7952 | 0.5779 | 0.0364 | 0.6133 | 0.3067 | 0.0013 |
| GuyonLekeufackPDV | 22 | QQQ | 2087 | 0.6098 | 0.7859 | 0.5961 | 0.0890 | 0.6670 | 0.3124 | 0.0011 |
| GuyonLekeufackPDV | 22 | SPY | 2087 | 1.2425 | 1.1513 | 0.7578 | -0.0551 | 0.5549 | 0.2592 | 0.0051 |
| GuyonLekeufackPDV | 22 | TLT | 2087 | 0.3878 | 0.6427 | 0.4743 | 0.1039 | 0.6354 | 0.2746 | 0.0004 |
| GuyonLekeufackPDV | 22 | XLE | 2087 | 0.6012 | 0.7812 | 0.5898 | -0.0271 | 0.5635 | 0.2463 | 0.0022 |
| GuyonLekeufackPDV | 22 | XLF | 2087 | 0.7003 | 0.8921 | 0.6993 | -0.3052 | 0.6483 | 0.2271 | 0.0014 |
| GuyonLekeufackPDV | 22 | XLK | 2087 | 2.5051 | 1.0021 | 0.6796 | 0.1022 | 0.6416 | 0.3115 | 0.0014 |

## Pooled by group
| model | group | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GuyonLekeufackPDV | emerging_markets | 10465 | 0.5564 | 1.0078 | 0.7003 | -0.2145 | 0.7235 | 0.3373 | 0.0694 |
| GuyonLekeufackPDV | high_yield_credit | 10465 | 7.5903 | 11.9134 | 8.3677 | -8.2545 | 0.2616 | 0.1250 | 19327.4320 |
| GuyonLekeufackPDV | oil_and_energy | 10465 | 0.5767 | 0.7891 | 0.6090 | -0.0414 | 0.6200 | 0.2649 | 0.0016 |
| GuyonLekeufackPDV | precious_metals | 10465 | 0.3778 | 0.8140 | 0.6479 | -0.2743 | 0.6730 | 0.3060 | 0.0004 |
| GuyonLekeufackPDV | us_cyclicals_sector | 10465 | 0.6627 | 0.8866 | 0.6971 | -0.3065 | 0.6864 | 0.2935 | 0.0010 |
| GuyonLekeufackPDV | us_large_cap_equity | 20930 | 0.9278 | 0.9964 | 0.7183 | -0.0226 | 0.6419 | 0.3004 | 0.0018 |
| GuyonLekeufackPDV | us_rates_and_ig_credit | 10465 | 0.4495 | 0.7194 | 0.5385 | 0.0381 | 0.6819 | 0.3260 | 0.0003 |
| GuyonLekeufackPDV | us_small_cap_equity | 10465 | 0.6486 | 0.7996 | 0.5946 | -0.0011 | 0.6565 | 0.3040 | 0.0010 |
| GuyonLekeufackPDV | us_technology_sector | 10465 | 1.1875 | 0.9298 | 0.6816 | 0.0256 | 0.6765 | 0.3137 | 0.0010 |
