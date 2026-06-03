# RV Model Swarm — Kickoff Prompts

This file holds (A) the one-time coordinator pre-flight, (B) the reusable per-worker
prompt template, and (C) the wave schedule. The full build contract lives in
`rv_eval/MODEL_PLAN.md`; this file is the operational wrapper that keeps 3 concurrent
Opus 4.8 workers from colliding on shared state.

The cross-model comparison (`evaluator.py`, `planning_docs/execution/COMPARISON_PLAN.md`)
is **out of scope for every worker** and runs once, separately, after all predictions exist.

---

## A. Coordinator pre-flight (run ONCE, before spawning any worker)

Already done in repo setup:
- `candidate_models/` package scaffold exists (`__init__.py`, `tests/__init__.py`, `cards/`).
- `uv sync --extra dev` has materialized the venv. **All model libs (`arch`, `xgboost`,
  `torch`, `scipy`, `scikit-learn`, `statsmodels`) are already in `pyproject.toml`.**

Still to do before the swarm:
1. **Spawn workers** per the wave schedule in §C — including one worker per benchmark
   (models 0–3). Every model in the catalog, benchmark or candidate, is produced by its
   own independent worker so each prediction parquet has uniform provenance. Benchmarks
   are not run centrally by the coordinator.

---

## B. Per-worker prompt template

> Copy this verbatim into each worker. Replace **`{MODEL_NUMBER}`** with the catalog
> number (4–12). Change nothing else.

```
You are ONE worker in a parallel swarm. Build exactly ONE model and stop.

Your assignment: model {MODEL_NUMBER} from rv_eval/MODEL_PLAN.md §4.

== RULES OF ENGAGEMENT (hard constraints — violating these corrupts the swarm) ==
WRITE ONLY these files (your sandbox):
  - candidate_models/<your-file>.py
  - candidate_models/tests/test_<your-model>.py
  - candidate_models/cards/<your-name>.md  and  <your-name>.hard_cases.md
NEVER edit: anything under rv_eval/ (the harness), features.py, config.py,
  model_contract.py, pyproject.toml, uv.lock, the .venv, another worker's file,
  or any predictions parquet by hand.
NEVER run: `uv sync` / `uv add` / `pip install` (the env is already complete —
  if an import fails, STOP and report; do not modify the environment),
  `evaluator.py`, the comparison pass, or any OTHER model's walk-forward.
Reading is fine and expected: you MUST read model_contract.py, features.py, config.py,
  and MODEL_PLAN.md §2–§5. Reading another model's prediction parquet is harmless and
  is REQUIRED only for model 12 (the ensemble). Do not tune toward other models' results;
  hyperparameters are frozen by the leakage-safe protocol in MODEL_PLAN §4, not by peeking.

== IF YOUR MODEL IS A BENCHMARK (0–3): RandomWalk / EWMA / HAR / HAR-X ==
These are ALREADY CODED in rv_eval/model_contract.py — there is no file or test to write.
Skip build steps 1–4 below. Go straight to step 5 (run the walk-forward) using the existing
class, e.g. `--model rv_eval.model_contract:HAR`, then steps 6–8 (cards, report). Your
prediction `name` is the class's existing `name` attr (RW, EWMA, HAR, HAR-X).

== BUILD STEPS (candidate models 4–12; full detail in MODEL_PLAN.md §2) ==
1. Read rv_eval/model_contract.py (the Model ABC + base classes), rv_eval/features.py
   (pre-baked feature groups — do NOT re-engineer existing features), rv_eval/config.py.
2. Write candidate_models/<file>.py implementing the class named in §4 for model {MODEL_NUMBER}.
   Subclass _LinearLogHAR (HAR-family) or _PerKeyModel (everything else). Set a
   filesystem-safe `name` attribute — it becomes your prediction FILENAME and must match
   the <your-name> used in your card paths.
   predict(X) MUST return exactly: ticker, date, horizon, rv_hat, sigma, q05,q10,q25,q50,q75,q90,q95.
   Use _lognormal_quantiles(m, s) from model_contract.py. rv_hat is in target_var units.
3. Write candidate_models/tests/test_<your-model>.py: synthetic 3-ticker × 500-day panel;
   assert predict returns the required columns and finite rv_hat. Run it by EXPLICIT path
   (testpaths only covers rv_eval/tests):
     .venv/bin/python -m pytest candidate_models/tests/test_<your-model>.py -q
4. For models 8–11 only: tune-once-then-freeze on the 2016–2017 validation block per
   MODEL_PLAN §4 "Hyperparameter selection", then hard-code the frozen values. Models 0–7
   have no free hyperparameters. Set seeds (torch=0, numpy=0, xgboost seed=0).
5. Run the walk-forward on BOTH universes (writes ONE parquet, upserted per ticker):
     .venv/bin/python -m rv_eval.walkforward --model candidate_models.<file>:<Class> --universe clean_core
     .venv/bin/python -m rv_eval.walkforward --model candidate_models.<file>:<Class> --universe hard_cases
   (Equivalently `--universe all`.) Output: execution/data/predictions/<your-name>.parquet
6. Generate the two self-only cards (NOT evaluator.py):
     .venv/bin/python -m rv_eval.selfstats --pred execution/data/predictions/<your-name>.parquet \
         --out candidate_models/cards/<your-name>.md --universe clean_core
     .venv/bin/python -m rv_eval.selfstats --pred execution/data/predictions/<your-name>.parquet \
         --out candidate_models/cards/<your-name>.hard_cases.md --universe hard_cases
7. Augment each card with the human-only fields from MODEL_PLAN §5 (features used, frozen
   hyperparameters + HP-selection note, library versions, seed, wall-time, device,
   convergence/per-ticker warnings).
8. STOP. Report back: your file path, class, model `name`, prediction parquet path, OOS row
   count, wall-clock per universe, device, and any tickers/horizons you could NOT cover
   (convergence failures, thin data, min_obs guards — these are dropped, never imputed).
   Do not write any cross-model commentary or run any comparison.
```

---

## C. Wave schedule (3 workers at a time)

Models 4–11 are independent and can run in any grouping. **Model 12 (Ensemble) is a
post-hoc combiner that reads 4–11's parquets off disk — it must run only after they finish.**

| Wave | Models | Note |
|---|---|---|
| 1 | 0, 1, 2 | benchmarks RW / EWMA / HAR — pre-coded, worker only runs + cards |
| 2 | 3, 4, 5 | HAR-X (pre-coded) + HARQ, HAR-RS — fast HAR-family |
| 3 | 6, 7, 8 | HAR-CJ, HAR-RS-IV-Q, R-GARCH |
| 4 | 9, 10, 11 | XGBoost, LSTM (MPS), PDV — heavier |
| 5 | 12 | Ensemble — ONLY after 4–11 predictions all exist on disk |
| after | — | comparison pass (`planning_docs/execution/COMPARISON_PLAN.md`), run once, separately |

Each worker writes its own `predictions/<name>.parquet`, so there is no write contention
in the predictions dir. The only shared state to protect is the venv / pyproject /
uv.lock — which the Rules of Engagement forbid workers from touching.
