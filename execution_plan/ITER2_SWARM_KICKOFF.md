# Iteration-2 Model Swarm — Kickoff Prompts

The iter-2 analogue of `SWARM_KICKOFF.md`. Holds (A) the one-time pre-flight, (B) the reusable
per-worker prompt, and (C) the wave schedule. The per-model build contract is
`execution_plan/ITER2_MODEL_CATALOG.md`; the generic build steps + card template are reused from
`rv_eval/MODEL_PLAN.md` §2/§5. Same harness as iter-1 — **no edits to `rv_eval/`.**

The cross-model comparison (`evaluator.py`, `planning_docs/execution/COMPARISON_PLAN.md`) is **out of
scope for every worker** and runs once, separately, under the re-weighted gate
(`planning_docs/research/rv_har_extensions_plan.md` §4).

---

## A. Pre-flight (run ONCE, before spawning model workers)

1. Venv is complete (`uv sync --extra dev`): scikit-learn, arch, statsmodels, scipy, numpy, polars
   all present. Workers NEVER run `uv`/`pip`.
2. `execution/data/inputs.parquet` has the six new systematic columns (vix9d, vix9d_slope,
   credit_spread, credit_mom, usd_mom, rates_mom). If not: `python -m rv_eval.setup._add_systematic_cols`.
3. **Wave-0 infra worker** builds `candidate_models/_base_v2.py` (CATALOG §2) and its smoke test.
   Once validated it is **frozen** — every later worker imports it read-only.
4. iter-1 prediction parquets remain on disk (model 21 / EnsembleTopK-v2 reads them).

---

## B. Per-worker prompt template

> Copy verbatim into each worker. Replace **`{MODEL_NUMBER}`** with the catalog number (13–32, or
> "Wave-0 infra"). Change nothing else.

```
You are ONE worker in a sequential iteration-2 swarm. Build exactly ONE model and stop.
You start cold — read the files named below before coding.

Your assignment: model {MODEL_NUMBER} from execution_plan/ITER2_MODEL_CATALOG.md §3
(or, if {MODEL_NUMBER} == "Wave-0 infra", build candidate_models/_base_v2.py per CATALOG §2).

== RULES OF ENGAGEMENT (hard constraints — violating these corrupts the swarm) ==
WRITE ONLY these files (your sandbox):
  - candidate_models/<your-file>.py
  - candidate_models/tests/test_<your-model>.py
  - candidate_models/cards/<your-name>.md  and  <your-name>.hard_cases.md
  (The Wave-0 infra worker instead writes ONLY candidate_models/_base_v2.py + its test.)
NEVER edit: anything under rv_eval/ (the harness: model_contract.py, features.py, config.py,
  walkforward.py, selfstats.py, setup/), candidate_models/_base_v2.py (frozen after Wave 0),
  pyproject.toml, uv.lock, the .venv, another worker's file, or any predictions parquet by hand.
NEVER run: `uv sync`/`uv add`/`pip install` (env is complete — if an import fails, STOP and report),
  `evaluator.py`, the comparison pass, or any OTHER model's walk-forward.
Reading is fine and REQUIRED: rv_eval/model_contract.py, rv_eval/features.py, rv_eval/config.py,
  candidate_models/_base_v2.py, the CATALOG §1 (reuse patterns) and your §3 entry, plus the named
  reference impl for your pattern (har_cj.py for P1, realized_garch.py for P2, ensemble_top.py for P3).
  Do NOT tune toward other models' results — hyperparameters are frozen by leakage-safe inner CV on
  the TRAIN slice only, never by peeking at OOS or other models.

== THE CRITICAL ROLLING-FEATURE RULE (most common way to get this wrong) ==
The walk-forward hands predict() ONLY the one-month test slice. Any trailing-window feature
(rolling_mean over days, expanding percentile, shift) computed on that slice is WRONG (null leading
rows / wrong ranks). Build such features ONCE on the FULL series from inputs.parquet and JOIN them by
(ticker, date) — use _base_v2._AttachMixin and supply `_derive(inputs)`, mirroring har_cj.py::_attach
(including its fallback to building from X for the synthetic smoke test). Columns already in
inputs.parquet (incl. vix9d/credit_*/etc.) need no derivation — they arrive in X via build_features.

== DATA LOCATION GOTCHAS (CATALOG §4) ==
- post_shock and iv2 are in targets.parquet, NOT in X. predict() never sees them.
  → For an IV-variance feature use iv_30d**2 (iv_30d is in X). For a regime split use a vix
    percentile or sign(vix9d_slope), not post_shock.
- SPX/VIX RV is not in inputs.parquet (only the 15 scored tickers). A "market RV factor" must be the
  clean-core cross-sectional mean of total_rv per date (leak-free), not SPX RV.

== BUILD STEPS (full generic detail in rv_eval/MODEL_PLAN.md §2) ==
1. Read the harness files + your CATALOG entry + your pattern's reference impl.
2. Write candidate_models/<file>.py implementing the Class named in CATALOG §3. Pick the base per the
   entry: _LinearLogHAR (+_AttachMixin) for P1, _PerKeyModel for P2, the _base_v2 bases or Model ABC
   for P3. Set a filesystem-safe `name` EXACTLY as listed (it is your prediction filename + card path).
   predict(X) MUST return: ticker, date, horizon, rv_hat, sigma, q05,q10,q25,q50,q75,q90,q95.
   Use _lognormal_quantiles(m,s) unless your entry emits quantiles directly (27/28) — then keep them
   non-decreasing. rv_hat in target_var units, finite, > 0. sigma may be per-row (25/26).
3. Write candidate_models/tests/test_<your-model>.py: synthetic 3-ticker × 500-day panel; assert
   predict returns the required columns, finite rv_hat>0, monotone quantiles. Run by EXPLICIT path:
     .venv/bin/python -m pytest candidate_models/tests/test_<your-model>.py -q
4. Run the walk-forward on BOTH universes (upserts ONE parquet):
     .venv/bin/python -m rv_eval.walkforward --model candidate_models.<file>:<Class> --universe clean_core
     .venv/bin/python -m rv_eval.walkforward --model candidate_models.<file>:<Class> --universe hard_cases
   Output: execution/data/predictions/<your-name>.parquet
5. Generate the two self-only cards (NOT evaluator.py):
     .venv/bin/python -m rv_eval.selfstats --pred execution/data/predictions/<your-name>.parquet \
         --out candidate_models/cards/<your-name>.md --universe clean_core
     .venv/bin/python -m rv_eval.selfstats --pred execution/data/predictions/<your-name>.parquet \
         --out candidate_models/cards/<your-name>.hard_cases.md --universe hard_cases
6. Augment each card with the human-only fields from MODEL_PLAN §5 (features/derived columns used,
   frozen hyperparameters + HP-selection note, library versions, seed, wall-time, device, any
   convergence / per-ticker / coverage warnings).
7. STOP. Report: file path, Class, model `name`, prediction parquet path, OOS row count, wall-clock per
   universe, device, and any tickers/horizons you could NOT cover (convergence/thin-data/min_obs —
   dropped, never imputed). No cross-model commentary; no comparison.
```

---

## C. Wave schedule

Sequential within a wave; gate each wave before the next. (The orchestrator may run independent models
in a wave back-to-back; only model 21 has a hard dependency.)

| Wave | Items | Note |
|---|---|---|
| 0 | `_base_v2.py` infra | shared mixins/bases; frozen after validation |
| 1 | 25, 15, 13, 14, 19, 18, 28 | highest-EV: hetero-σ, IV-TS/VRP, leverage, signed-jump, shrinkage, kitchen-sink, VRP head |
| 2 | 22, 23, 24, 27, 20, 16, 17, 26, then **21** | pooling, quantile, CSR, range/activity, HAR-GARCH; **EnsembleTopK-v2 LAST** (reads components' parquets) |
| 3 | 29, 30, 31 | regime/threshold/STAR/MS-HAR (31 gated hard) |
| after | — | comparison pass + re-weighted gate (human-triggered, separate) |

Each worker writes its own `predictions/<name>.parquet` → no write contention. The only shared state
to protect is the venv / pyproject / uv.lock / `_base_v2.py`, which the Rules of Engagement forbid
non-infra workers from touching.
