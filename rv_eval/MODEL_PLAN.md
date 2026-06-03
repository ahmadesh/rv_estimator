# RV Forecasting — Model Build & Evaluation Guide

> **Audience.** This document is a build-and-run guide for a *swarm* of LLM workers. Each worker takes one numbered model from §4, implements it, trains it via the existing walk-forward harness, and writes its predictions to disk. Each worker also writes a small model card with self-only stats. **Workers do not invoke `evaluator.py`.** Comparison of the resulting predictions is a separate coordinator pass run once after the swarm — see **`planning_docs/execution/COMPARISON_PLAN.md`**. **No accept/reject judgment is made here** — that comes later from the comparison report.
>
> **Starting state.** Predictions and reports have been cleared — the swarm starts from scratch. No model (not even the reference benchmarks) has trained predictions on disk; every model 0–12 must be *run* to populate `execution/data/predictions/`. The benchmark *classes* (0–3) already exist in `rv_eval/model_contract.py`; the new candidates (4–12) must be written.
>
> **Why this split.** The `evaluator` is built end-to-end for cross-model scoring: every table (leaderboard, §9 status, DM matrix, MCS, Progression panel) is keyed by `model`. Running it on a single prediction file gives degenerate cross-model panels and (critically) a `no_baseline`/`rejected` §9 status because `status.assign()` (`metrics/status.py`) computes its baseline from the `HAR` row in the predictions set. Per-worker eval also writes to `registry.parquet` (append-only), which would corrupt the Progression panel that diffs against prior runs. So workers stop at `predictions/<name>.parquet` + a self-stats card, and a single final pass (`planning_docs/execution/COMPARISON_PLAN.md`) does all comparison.

## 1. Context

This plan sits on top of the `rv_eval/` harness (see `README.md` §End-to-end flow). The harness is finished:

- `setup/prepare_panel.py` → `execution/data/inputs.parquet` + `targets.parquet` (one-shot).
- `walkforward.py` → drives any `Model` subclass via a purged + embargoed monthly-refit rolling-origin loop.
- `evaluator.py --tier 2` → joins predictions to targets and emits `report.html / .md / metrics.json` + §9 status.

The goal is to populate a **comprehensive sweep** of 13 models (4 reference benchmarks already coded + 9 new candidates to build) so the downstream comparison pass (`planning_docs/execution/COMPARISON_PLAN.md`) can decide which work. Predictions start empty: every model must be run to generate its parquet. Each worker is independent — the models can be built in parallel.

## 2. Per-Worker Build Contract

A worker assigned model `N` performs exactly these steps:

1. **Read** `rv_eval/model_contract.py` to confirm the `Model` ABC. Subclass `_PerKeyModel` (or `_LinearLogHAR` for log-OLS HAR-family models) — these base classes provide free per-(ticker, horizon) fitting, lognormal-quantile generation, and `min_obs` guards.
2. **Read** `rv_eval/features.py` for pre-baked feature groups (`HAR_FEATURES`, `HARQ_FEATURES`, `HAR_RS_FEATURES`, `IV_FEATURES`) and `build_features()`. Do not re-engineer features that already exist.
3. **Write** one file at the path listed in §4 (`candidate_models/<file>:<ClassName>`). LOC budgets are guidance, not limits.
4. **Add the file's required library** to `pyproject.toml` if missing (e.g., `xgboost`, `arch`, `torch`, `scipy`). Run `uv sync --extra dev`.
5. **Write a smoke test** at `candidate_models/tests/test_<model>.py`: synthetic 3-ticker × 500-day panel; assert `predict` returns the required columns and finite `rv_hat`.
6. **Run the walk-forward** on `clean_core`:
   ```bash
   .venv/bin/python -m rv_eval.walkforward --model candidate_models.<file>:<ClassName> --universe clean_core
   ```
   Output: `execution/data/predictions/<model-name>.parquet`. The walkforward appends a single parquet (one file per model run), keyed by `(ticker, date, horizon)`.
7. **Run the walk-forward on `hard_cases`** too. Same command, `--universe hard_cases`. The walkforward **upserts** into the same `predictions/<name>.parquet`: it replaces only the rows for the tickers in this run and preserves the rest, so the clean_core and hard_cases predictions accumulate in one file (keyed by `ticker, date, horizon`, with a `model` column). Re-running a universe just refreshes its rows. (Equivalently, run once with `--universe all`.)
8. **Generate the model card** with self-only stats. **Do NOT call `evaluator.py`.** Use the dedicated CLI:
   ```bash
   .venv/bin/python -m rv_eval.selfstats \
       --pred execution/data/predictions/<model-name>.parquet \
       --out candidate_models/cards/<model-name>.md \
       --universe clean_core
   ```
   `rv_eval.selfstats` produces only the per-model panels that are meaningful in isolation (Tier-1 by horizon / ticker / group, §5 IV-incremental skill, §6 conditional bias by IV bucket, §6 post-shock calibration). It does **not** write to `registry.parquet`, compute §9 status, or render leaderboard/DM/MCS panels — those are inherently cross-model and belong to the comparison pass (`planning_docs/execution/COMPARISON_PLAN.md`). Run a second time with `--universe hard_cases --out candidate_models/cards/<model-name>.hard_cases.md` for the hard-cases card.
9. **Augment the card** with the human-only fields from the template in §5 (features used, hyperparameters, train wall-time, device, convergence notes). Append them above the auto-generated sections written by `selfstats`.
10. **Stop.** Do not modify other models or write any cross-model commentary. The comparison happens in the separate coordinator pass — see `planning_docs/execution/COMPARISON_PLAN.md`.

### Output schema (must match exactly)

`predict(X)` returns: `ticker, date, horizon, rv_hat, sigma, q05, q10, q25, q50, q75, q90, q95`. Use `_lognormal_quantiles(m, s)` from `model_contract.py` to generate quantiles consistently with the existing benchmarks. `rv_hat` is in `target_var` units (horizon variance = sum of next-h daily total-RVs).

### Reuse, don't reinvent

| Need | Use |
|---|---|
| Model ABC | `rv_eval.model_contract.Model` |
| Per-key state + quantile machinery | `rv_eval.model_contract._PerKeyModel` |
| Log-OLS HAR template (just set `needs = [...]`) | `rv_eval.model_contract._LinearLogHAR` |
| Lognormal quantile generation | `rv_eval.model_contract._lognormal_quantiles(m, s)` |
| Feature builder (already invoked by walkforward) | `rv_eval.features.build_features(inputs)` |
| Pre-baked feature constants | `HAR_FEATURES`, `HARQ_FEATURES`, `HAR_RS_FEATURES`, `IV_FEATURES` |
| Universe / horizons / OOS config | `rv_eval.config` |

## 3. GPU & Compute

- **HAR variants (4–7), PDV (11), Ensemble (12):** CPU only, < 1 min per ticker.
- **Realized GARCH (8):** CPU only, per-ticker MLE; ~30 s per ticker.
- **XGBoost (9):** CPU is fine (one booster per ticker × horizon, ~100k rows max). If a GPU is desired, set `tree_method="hist"` and `device="cuda"` / `device="mps"`.
- **LSTM (10):** Use GPU if available. On this machine (Apple Silicon, Darwin 24.3.0), use the **MPS backend** via PyTorch: `device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")`. Move both model and tensors to `device`. Fall back to CPU if MPS unavailable. Expected wall time on MPS: ~2–5 min per ticker (60 epochs × 15 refits).

## 4. Model Catalog

Models 0–3 are the reference benchmarks. Their classes already exist in `rv_eval/model_contract.py` and run as-is — no implementation work — but they still must be **run** to generate predictions (none are on disk). A coordinator can run all four at once: `walkforward.py --benchmarks --universe all`.

### 0. RandomWalk *(coded; run to generate predictions)*
Class: `rv_eval.model_contract:RandomWalk`. Feature: `rv_d`. `rv_hat = h * rv_d` (lognormal-mean corrected). Sigma from log-residual std.

### 1. EWMA *(coded; run to generate predictions)*
Class: `rv_eval.model_contract:EWMA`. Feature: `ewma_rv` (λ=0.94). `rv_hat = h * ewma_rv` (lognormal-mean corrected).

### 2. HAR *(coded; run to generate predictions)*
Class: `rv_eval.model_contract:HAR`. Features: `HAR_FEATURES`. Per-(ticker, h) OLS of `log(target_var)` on HAR lags. **This is the §9 baseline** — it must be in the predictions set for the comparison pass to anchor.

### 3. HAR-X *(coded; run to generate predictions)*
Class: `rv_eval.model_contract:HARX`. Features: `HAR_FEATURES + IV_FEATURES`.

### 4. HARQ — Quarticity-Corrected HAR
- File: `candidate_models/harq.py:HARQ`. Base: `_LinearLogHAR`. Budget: ~10 LOC.
- Features: `HARQ_FEATURES` = `HAR_FEATURES + ["sqrt_rq"]`.
- Library: numpy.
- Implementation: subclass `_LinearLogHAR`, set `name = "HARQ"`, set `needs = HARQ_FEATURES`. Done.

### 5. HAR-RS — Semivariance HAR + jump
- File: `candidate_models/har_rs.py:HARRS`. Base: `_LinearLogHAR`. Budget: ~10 LOC.
- Features: `HAR_RS_FEATURES` = `[log_rv_d, log_rv_w, log_rv_m, rs_minus_5d, rs_plus_5d, jump_5d]`.
- Implementation: subclass, set `needs = HAR_RS_FEATURES`.

### 6. HAR-CJ — Continuous + Jump Decomposition
- File: `candidate_models/har_cj.py:HARCJ`. Base: `_LinearLogHAR`. Budget: ~25 LOC.
- Features needed: `log_bv_d`, `log_bv_w`, `log_bv_m`, `log_jump_d`, plus `HAR_FEATURES`.
- Note: `bv` is in `inputs.parquet` (per `setup/measurement.py`). Build the three log-BV roll-means **inside the model file** with `pl.col("bv").rolling_mean(w).over("ticker").log()`. Keep `features.py` untouched.

### 7. HAR-RS-IV-Q — Modern HAR
- File: `candidate_models/har_rs_iv_q.py:HARRSIVQ`. Base: `_LinearLogHAR`. Budget: ~10 LOC.
- Features: `HAR_RS_FEATURES + IV_FEATURES + ["sqrt_rq"]` (deduplicated).
- This is the research doc's recommended primary; treat it as the strongest linear baseline.

### 8. Realized GARCH
- File: `candidate_models/realized_garch.py:RealizedGARCH`. Base: `_PerKeyModel`. Budget: ~80 LOC.
- Library: `arch` (Hansen-Huang-Shek 2012 spec; use `arch_model(...)` + measurement equation, or hand-roll the joint likelihood).
- Inputs at predict: `ret_close`, `rv_d` (both in `inputs.parquet`).
- Approach:
  - In `_fit_one(X, y)`: fit a 1-step daily R-GARCH per (ticker, horizon).
  - In `_predict_one(X)`: for horizon `h`, simulate forward conditional-variance paths (closed-form GARCH; Monte Carlo bootstrap for R-GARCH with ~1000 paths). Set `rv_hat = E[Σ_{t+1..t+h} σ²_s]`.
  - `sigma` = log-std of simulated horizon sums.
- Numerical robustness: clip `omega` to a small positive floor; if MLE fails to converge for a ticker, fall back to plain GARCH(1,1) and log a warning in the model card.

### 9. XGBoost on HAR-RS + IV features
- File: `candidate_models/xgb_har.py:XGBHARRSIV`. Base: `_PerKeyModel`. Budget: ~100 LOC.
- Library: `xgboost`.
- Features: same matrix as model 7 (`HAR_RS_FEATURES + IV_FEATURES + ["sqrt_rq"]`).
- Target: `log(target_var)`. One booster per (ticker, horizon).
- **Hyperparameters: tune-once-then-freeze** (see "Hyperparameter selection" below). Grid over `max_depth`, `learning_rate`, `min_child_weight`; the values below are the grid's *initial point*, not the frozen answer. Fixed at initial: `subsample=0.8, colsample_bytree=0.8, reg_lambda=1.0, objective="reg:squarederror"`. `n_estimators` is not gridded — early-stop on a 10% time-ordered within-train tail (cap 2000).
- `sigma` = residual std on the held-out tail.

### 10. LSTM on multi-feature window
- File: `candidate_models/lstm_rv.py:LSTMRV`. Base: `_PerKeyModel` (one network per ticker, multi-head over horizons). Budget: ~250 LOC.
- Library: `torch` (use MPS backend per §3).
- Inputs: rolling 60-day window of `[log_rv_d, log_iv, vix, vix_slope, iv_slope, skew_25d, rs_minus_5d, rs_plus_5d]` — these are the "macro covariates" DL needs to beat HAR.
- Architecture: LSTM(hidden, num_layers, dropout) → linear head per horizon → `log(target_var)`.
- **Hyperparameters: tune-once-then-freeze** (see "Hyperparameter selection" below). Grid over `hidden`, `num_layers`, `dropout`, `lr`; initial point = `hidden=64, num_layers=2, dropout=0.1, lr=1e-3`. Fixed: `batch_size=64`, Adam. `epochs` is not gridded — early-stop on a 10% time-ordered within-train tail (cap 80).
- Training: MSE on log target.
- `sigma` = residual std on held-out tail.
- **Hard-case note:** IBIT (~2 y of options coverage) and MSOS (thin) are data-starved. Run them anyway; the model card should call out where the network failed to converge or produced NaN.

### 11. Guyon-Lekeufack 4-factor PDV
- File: `candidate_models/pdv_glek.py:GuyonLekeufackPDV`. Base: `_PerKeyModel`. Budget: ~150 LOC.
- Library: `scipy.optimize`.
- Spec: `σ_t² = β₀ + β₁ R1_t + β₂ √R2_t`, where
  - `R1_t = (1-θ) Σ K_short(t-s) r_s + θ Σ K_long(t-s) r_s` (trend factor)
  - `R2_t = (1-θ') Σ K_short'(t-s) r_s² + θ' Σ K_long'(t-s) r_s²` (activity factor)
  - Kernels: exponentials with short/long half-lives.
- Parameters per ticker: `(β₀, β₁, β₂, θ, θ', λ_short, λ_long, λ_short', λ_long')` — 9 scalars, all fit by `scipy.optimize` (not gridded). Initialize the kernel half-lives at short≈8d, long≈250d (both factor pairs); these only seed the optimizer. No grid search unless convergence is poor — if so, note it in the card.
- Fit by minimizing log-MSE on daily RV (one-step). For horizon `h`, simulate forward by bootstrapping residuals over `h` steps × ~500 paths and summing.
- Inputs: `ret_close`, `rv_d`.

### 12. Equal-weight ensemble of top-K
- File: `candidate_models/ensemble_top.py:EnsembleTopK`. Base: `Model` (not `_PerKeyModel`). Budget: ~60 LOC.
- **Post-hoc combiner — run only after all components have produced predictions on disk.**
- At predict time: read `execution/data/predictions/<name>.parquet` for each component, equal-weight mean of `rv_hat`, propagate `sigma` as `sqrt(mean(component sigmas²) + var(component means))`, regenerate quantiles via `_lognormal_quantiles`. `fit` is a no-op.
- Components are hard-coded in a `COMPONENTS = [...]` list at the top of the file. **Default for the first swarm pass:** all models that produced a valid predictions parquet other than the baselines (i.e., 4, 5, 6, 7, 8, 9, 10, 11). The component list can be refined after the comparison.

### Hyperparameter selection — tune-once-then-freeze (models 8–11)

Models 0–7 have **no free hyperparameters** (RW/EWMA are fixed; EWMA's λ=0.94 is the RiskMetrics convention and is *not* tuned; HAR-family are plain log-OLS) — run them as-is. Only the ML/DL/PDV models have structural knobs, and tuning them is what makes the comparison fair: a hand-picked config that loses tells you nothing about the *method*. Tuning is **leakage-safe by protocol**, not by trust:

1. **Split (pre-OOS only).** Search-train = `date < C.HPTUNE_VAL_START` (`2016-01-01`); validation = `[HPTUNE_VAL_START, OOS_START)` = 2016–2017. No `date ≥ OOS_START` (2018) is ever read during tuning.
2. **Search.** For each grid point: fit on search-train, score **pooled QLIKE at the primary horizon (h=22)** on the validation block, keep the best. Tune **globally** — one frozen HP set for all tickers/horizons, not per-ticker (cheaper, less overfit). For the LSTM, tune on the representative subset `C.HPTUNE_DL_SUBSET` (`SPY, QQQ, TLT, XLE`) to bound compute.
3. **Freeze.** Hard-code the winning values in the model class. Record the grid, validation block, metric, and chosen values in the model card.
4. **Run.** Execute the normal walk-forward with frozen HPs. The 2016–2017 validation dates are now legitimately reused as *training* rows for OOS folds — not leakage (they were never test rows, and no OOS data informed the HPs).

`n_estimators` (XGBoost) and `epochs` (LSTM) are **not** gridded — they are chosen per-fit by early stopping on a within-train time-ordered tail (already leakage-safe), with a generous cap. If compute is tight, running only the **initial point** of a grid is an acceptable fallback (state it in the card).

| Model | Grid (initial point in **bold**) | Fixed at initial | Chosen by early-stop |
|---|---|---|---|
| 9 XGBoost | `max_depth∈{3,`**`4`**`,6}` · `learning_rate∈{0.03,`**`0.05`**`,0.1}` · `min_child_weight∈{5,`**`10`**`,20}` → 27 pts | `subsample=0.8`, `colsample_bytree=0.8`, `reg_lambda=1.0`, `objective="reg:squarederror"` | `n_estimators` (cap 2000) |
| 10 LSTM | `hidden∈{32,`**`64`**`,128}` · `num_layers∈{1,`**`2`**`}` · `dropout∈{`**`0.1`**`,0.2}` · `lr∈{5e-4,`**`1e-3`**`}` → 24 pts | `batch_size=64`, Adam, 60-day window | `epochs` (cap 80) |
| 11 PDV | none (9 scalars fit by `scipy.optimize`) | kernel half-lives seeded short≈8d, long≈250d | — |
| 8 R-GARCH | none (params via MLE) | HHS(2012) spec; fall back to GARCH(1,1) on non-convergence | — |

### Optional stretch — ViT on IV surface
Out of scope for this swarm. Defer until the comparison pass (`planning_docs/execution/COMPARISON_PLAN.md`) motivates it.

## 5. Model-Card Template (per model)

Each worker writes `candidate_models/cards/<model-name>.md` with the following sections (filled in from its own run):

```markdown
# <model-name> — Model Card

## Identity
- Model number (from MODEL_PLAN.md): N
- Class: candidate_models.<file>:<ClassName>
- Tier: <Baseline | Modern HAR | GARCH | ML | DL | PDV | Ensemble>
- Implemented by: <worker-id or timestamp>

## Configuration
- Features used (list, by name): ...
- Hyperparameters (key=value, one per line — the FROZEN values used): ...
- HP selection (models 8–11): validation block (e.g. 2016–2017), grid searched, selection metric (pooled QLIKE @ h=22), chosen point; or "initial point only — not searched". N/A for models 0–7.
- Library version(s): ...
- Random seed (if applicable): ...

## Training
- Universes run: clean_core, hard_cases
- Walk-forward folds: <N>
- Wall-clock time: <clean_core: Xm Ys, hard_cases: Xm Ys>
- Device: <cpu | mps | cuda>
- Convergence notes / per-ticker warnings: ...

## OOS self-stats (this model alone — no ranks, no DM, no MCS, no §9 status)
- QLIKE pooled by horizon (h=1, 5, 10, 22, 42): ...
- §5 IV-incremental skill at h=22 (slope, sign-accuracy, qlike_gain_vs_iv): ...
- §6 conditional bias by IV-pctile bucket at h=22: ...
- §6 post-shock bias at h=22: ...
- 50% / 90% interval coverage at h=22: ...

## Per-ticker QLIKE at h=22
| ticker | qlike | notes |
|---|---|---|
| ... | ... | ... |

## Anomalies / things the next reader should know
- ...

## Reproduce
```bash
.venv/bin/python -m rv_eval.walkforward --model candidate_models.<file>:<ClassName> --universe clean_core
.venv/bin/python -m rv_eval.walkforward --model candidate_models.<file>:<ClassName> --universe hard_cases
.venv/bin/python -m rv_eval.selfstats --pred execution/data/predictions/<model-name>.parquet \
    --out candidate_models/cards/<model-name>.md --universe clean_core
.venv/bin/python -m rv_eval.selfstats --pred execution/data/predictions/<model-name>.parquet \
    --out candidate_models/cards/<model-name>.hard_cases.md --universe hard_cases
```
```

Per-model cards are deliberately self-contained: they make no claims about relative ranking against other models. That is the job of the comparison pass (`planning_docs/execution/COMPARISON_PLAN.md`).

## 6. Reporting strategy — what the existing code forces

The user's question was whether each worker should evaluate-and-report and *then* compare, or whether workers should only train/predict and the eval happens once over all of them. **The existing `evaluator.py` + `report.py` force the second choice.** Concretely:

| Panel in the existing report | Keyed by | Behavior on a single-model eval |
|---|---|---|
| QLIKE leaderboard (`fig_leaderboard`) | model | Single bar — useless |
| `tier1_overall`, `tier1_by_h`, `tier1_by_ticker`, `tier1_by_group` | model | Work for absolute numbers (one model row) |
| `iv_diag` (§5) | model × horizon | Works for absolute numbers |
| `cond_ivbucket`, `postshock_flags` (§6) | model × bucket | Works for absolute numbers |
| `dm` matrix (§4 Tier-2) | model × model | Degenerate 1×1 — useless |
| `mcs` Model Confidence Set | over models | Trivially {self} — useless |
| `status` (§9) | model vs HAR baseline | **All non-HAR models get `rejected`** because `status.assign()` joins to the `HAR` row in `tier1_by_h`; if HAR isn't in the predictions set, `qlike_base` is null and `n_improved` defaults to 0 |
| Progression panel | rows in `registry.parquet` | Each worker append would *corrupt* this (next worker sees the prior worker as "baseline") |

So per-worker `evaluator` invocation is wasteful (re-joins truth, re-renders empty cross-model panels) and actively harmful (registry pollution, false §9 status). The right architecture is:

- **During swarm (§2–§5):** each worker builds + trains + writes predictions parquet + runs `python -m rv_eval.selfstats --pred ... --out cards/<name>.md` to produce a self-only card. No `evaluator.py`, no `registry.parquet`. The `selfstats` CLI emits exactly the panels listed above as "works for absolute numbers".
- **After swarm (`planning_docs/execution/COMPARISON_PLAN.md`):** one `evaluator.py` invocation reads all `predictions/*.parquet` together and produces the comparative report. This is the only place leaderboards, DM matrices, MCS, §9 status, and Progression are computed.

If a coordinator wants a partial leaderboard mid-swarm to monitor progress, running `evaluator --tier 1 --no-registry --out /tmp/peek` at any time is safe — `--no-registry` avoids polluting the Progression diff, `--tier 1` skips the expensive DM/MCS pass. The evaluator now also warns to stderr when the HAR baseline is missing from the predictions set, and `metrics/status.py` returns `status="no_baseline"` rather than silently mass-rejecting every model.

## 7. Final Comparison Step → moved to `planning_docs/execution/COMPARISON_PLAN.md`

The cross-model comparison of predictions (the single coordinator `evaluator` pass: §9 status,
QLIKE leaderboard, §5 IV-incremental skill, §6 conditional bias, Diebold-Mariano, Model Confidence
Set, Progression) is **out of scope for the swarm** and now lives in its own guide:
**`planning_docs/execution/COMPARISON_PLAN.md`**. Run it once, after every model 0–12 has written its predictions. **No
selection is made by the swarm** — those reports are the input to a separate human/LLM review.

## 8. OOS Hygiene (applies to every worker)

- Never look at or train on data with `date ≥ OOS_START` (`2018-01-01`). The walkforward enforces this structurally; the human/worker must too.
- **Hyperparameter tuning** uses only the pre-OOS validation block `[HPTUNE_VAL_START, OOS_START)` (2016–2017); the search-train slice is everything before it. No OOS data ever informs a hyperparameter (see §4 "Hyperparameter selection").
- Early-stopping tails (XGBoost, LSTM) must come from within-train slices, never the OOS window.
- Random seeds: set `torch.manual_seed(0)`, `numpy.random.seed(0)`, `xgboost`'s `seed=0` for reproducibility. Note the seed and the frozen hyperparameters in the model card.
- **Missing predictions are dropped, never imputed.** If a model yields no row for a `(ticker, date, horizon)` — convergence failure, thin data, null features, or a `min_obs` guard — leave it absent. The evaluator inner-joins predictions to truth, so that cell is simply excluded from every comparison (DM/MCS compare only the common support). Record which tickers/horizons a model could not cover in the card so the comparison reader knows the coverage differs.

## 9. References

- `planning_docs/research/rv_forecasting_methods.md` — the research doc this plan operationalizes.
- Corsi (2009) HAR; Bollerslev, Patton, Quaedvlieg (2016) HARQ; Patton & Sheppard (2015) HAR-RS.
- Hansen, Huang, Shek (2012) Realized GARCH.
- Guyon & Lekeufack (2023) "Volatility is (mostly) path-dependent"; Gazzani & Guyon (2024) 4-factor PDV.
- 2024-2025 horse-races: TiDE/DeepAR beat HAR with macro covariates (MDPI 2025); "HARd to Beat" (arXiv 2406.08041); Moreno-Pino & Zohren (2024) dilated causal CNN for RV.
