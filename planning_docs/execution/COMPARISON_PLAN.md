# RV Forecasting — Prediction Comparison Guide

> **Audience.** This is the **single coordinator pass** run *once*, after the model-building swarm
> (`MODEL_PLAN.md`) has finished and every model has written its predictions to
> `execution/data/predictions/`. The swarm only builds, trains, and predicts — it never invokes
> `evaluator.py`. This doc owns all cross-model scoring: leaderboard, §9 status, Diebold-Mariano,
> Model Confidence Set, and the Progression panel. **No selection is made in this guide** — the
> reports it produces are the input to a separate human/LLM review.

## 1. Why comparison is a separate pass (not per-worker)

The `evaluator` is built end-to-end for cross-model scoring: every table (leaderboard, §9 status,
DM matrix, MCS, Progression panel) is keyed by `model`. Running it on a single prediction file
gives degenerate cross-model panels and a `no_baseline`/`rejected` §9 status, and per-worker eval
would append to `registry.parquet` and corrupt the Progression panel that diffs against prior runs.
See `MODEL_PLAN.md` §6 for the full table of which panels are meaningful in isolation (handled by
`rv_eval.selfstats` per worker) versus which are inherently cross-model (handled here).

## 2. Preconditions

- **All four reference benchmarks** (`RandomWalk`, `EWMA`, `HAR`, `HAR-X`) have been run via
  `walkforward.py` so their parquets are in `execution/data/predictions/`. Their classes already
  live in `rv_eval/model_contract.py`; the swarm/coordinator just runs them — they are *not*
  pre-trained, predictions start empty. Without `HAR` present, §9 status returns `no_baseline`
  for every model and the Progression panel can't anchor.
- **Every candidate model 4–12** has written its parquet (one file per model, keyed by
  `ticker, date, horizon`, with a `model` column). Each file already contains both universes if the
  worker ran `clean_core` and `hard_cases` (the walk-forward upserts per ticker into one file).

A quick precondition check:

```bash
ls execution/data/predictions/        # expect RW, EWMA, HAR, HAR-X + every candidate (4..12)
```

## 3. The comparison run

```bash
# 1. score every non-ensemble model on clean_core
.venv/bin/python -m rv_eval.evaluator --tier 2 --universe clean_core \
    --out execution/reports/swarm_clean_core_$(date +%Y%m%dT%H%M%SZ)/

# 2. same on hard_cases
.venv/bin/python -m rv_eval.evaluator --tier 2 --universe hard_cases \
    --out execution/reports/swarm_hard_cases_$(date +%Y%m%dT%H%M%SZ)/

# 3. build the ensemble (model 12) using whatever predictions are on disk
.venv/bin/python -m rv_eval.walkforward --model candidate_models.ensemble_top:EnsembleTopK --universe clean_core
.venv/bin/python -m rv_eval.walkforward --model candidate_models.ensemble_top:EnsembleTopK --universe hard_cases

# 4. re-score with the ensemble included
.venv/bin/python -m rv_eval.evaluator --tier 2 --universe clean_core \
    --out execution/reports/swarm_with_ensemble_$(date +%Y%m%dT%H%M%SZ)/
.venv/bin/python -m rv_eval.evaluator --tier 2 --universe hard_cases \
    --out execution/reports/swarm_with_ensemble_hardcases_$(date +%Y%m%dT%H%M%SZ)/
```

The ensemble (model 12) is a post-hoc combiner, so it is built **after** its components have
predictions on disk — hence steps 3–4 run separately from steps 1–2.

## 4. What the reports contain

Each `evaluator` run writes `report.html`, `report.md`, and `metrics.json` to its `--out` dir, and
(unless `--no-registry`) appends headline rows to `execution/reports/registry.parquet`:

- **§9 status per model** — `benchmark` / `research_candidate` / `rejected` (or `no_baseline` if
  `HAR` is absent). The verdict is anchored on the **primary horizon** (h=22): a model is rejected
  only if it breaks the primary horizon or springs the §6 post-shock trap; `research_candidate`
  additionally requires improving QLIKE and beating IV² (§5). Off-horizon breaks are reported in
  `n_broke` but do not by themselves reject.
- **QLIKE leaderboard** — pooled and per-horizon, model vs benchmarks vs IV².
- **§5 IV-incremental skill** — does the model add information beyond IV²? (slope > 0, sign acc > 0.5).
- **§6 conditional bias** — by IV-percentile bucket and post-shock.
- **Diebold-Mariano matrix** (Newey-West HAC) and **Model Confidence Set** (Tier-2 confirmation).
- **Progression panel** — signed Δ QLIKE vs prior `registry.parquet` runs.

**Coverage caveat.** Models differ in coverage — a thin-chain ticker, a convergence failure, or a `min_obs` guard can leave a model with no prediction for some `(ticker, date, horizon)` cells (MODEL_PLAN §8). The evaluator inner-joins to truth, so pooled Tier-1 numbers are over each model's *own* covered cells, while DM/MCS compare models only on their *common* support. When two models' coverage differs materially, weight the head-to-head DM/MCS over the pooled leaderboard, and check the per-model cards for the documented gaps.

## 5. Monitoring mid-swarm (optional)

A coordinator wanting a partial leaderboard before the swarm finishes can run a safe peek that does
not pollute the Progression diff and skips the expensive DM/MCS pass:

```bash
.venv/bin/python -m rv_eval.evaluator --tier 1 --no-registry --out /tmp/peek
```

The evaluator warns to stderr when the `HAR` baseline is missing, and `metrics/status.py` returns
`status="no_baseline"` rather than silently mass-rejecting every model.

## 6. References

- `MODEL_PLAN.md` — the swarm build/train/predict guide this comparison pass consumes.
- `README.md` §End-to-end flow — the harness this sits on top of.
- `planning_docs/research/rv_forecasting_methods.md` — the research doc both plans operationalize.
