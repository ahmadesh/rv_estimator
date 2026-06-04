# Iteration-2 Orchestrator Prompt — Modern-HAR Extensions Swarm

> Paste the fenced block into the orchestrator LLM (your main Claude Code session). It drives a
> swarm of Opus 4.8 subagents building the **iteration-2** models (13–32) from
> `execution_plan/ITER2_MODEL_CATALOG.md`, on the same harness as iter-1, and survives credit
> interruptions via a durable ledger. It is the iter-2 analogue of `ORCHESTRATOR_PROMPT.md`.

```
You are the ORCHESTRATOR of a sequential iteration-2 model-building swarm. You spawn ONE Opus 4.8
subagent at a time, each building exactly one forecasting model from
execution_plan/ITER2_MODEL_CATALOG.md, until all iter-2 models (Wave-0 infra + models 13–32) have
written predictions and model cards. You build NOTHING yourself and run NO comparison.

== AUTHORITATIVE REFERENCES (read first, once) ==
- execution_plan/ITER2_MODEL_CATALOG.md   — the iter-2 per-model spec (§1 reuse patterns, §2 Wave-0
                                            infra, §3 catalog, §4 discrepancies, §5 eval)
- execution_plan/ITER2_SWARM_KICKOFF.md    — §B worker template + Rules of Engagement; §C wave schedule
- rv_eval/MODEL_PLAN.md §2,§5              — the build-contract steps + card template (reused verbatim)
- rv_eval/model_contract.py, features.py, config.py; candidate_models/har_cj.py (the _attach join
  pattern), candidate_models/ensemble_top.py (post-hoc pattern)  — the harness the workers reuse
The comparison pass (planning_docs/execution/COMPARISON_PLAN.md, evaluator.py) is OUT OF SCOPE.
Stop when all iter-2 models are done and report.

== PRE-FLIGHT (once; skip silently if already true) ==
1. Confirm candidate_models/ exists with __init__.py, tests/__init__.py, cards/.
2. Confirm the venv resolves: `uv sync --extra dev`. All libs needed (scikit-learn, arch,
   statsmodels, scipy, numpy, polars) are already present — workers NEVER touch the env.
3. Confirm execution/data/inputs.parquet has the six new systematic columns
   (vix9d, vix9d_slope, credit_spread, credit_mom, usd_mom, rates_mom). If absent, run
   `python -m rv_eval.setup._add_systematic_cols` ONCE yourself, then proceed.
4. Confirm the iter-1 predictions still exist on disk (the ensemble-v2, model 21, reads them).
5. Create/open the ledger execution_plan/iter2_swarm_progress.md.

== WAVE-0 INFRA (must complete before ANY model 13–32) ==
candidate_models/_base_v2.py per CATALOG §2 (_AttachMixin, _PooledLinearHAR, _QuantileModel) with a
synthetic smoke test. This is the ONLY new file outside a per-model sandbox.
  - If the ledger already marks W0 `done` AND the file imports + its smoke test passes, SKIP this step
    (it is pre-built and FROZEN — do not re-spawn, do not edit). As of 2026-06-03 this is the case:
    candidate_models/_base_v2.py + tests/test_base_v2.py exist (4 tests pass), so a fresh run goes
    straight to Wave 1.
  - Otherwise spawn ONE infra subagent to build it, validate it imports and its smoke test passes,
    mark it done in the ledger, then freeze it.
Either way, later workers import it READ-ONLY and must not edit it.

== DURABLE PROGRESS LEDGER (makes you resumable) ==
Maintain execution_plan/iter2_swarm_progress.md, one row per item (Wave-0 infra, then 13–32):

| model | name | file:Class | track | status | parquet rows | cards | last_update | notes |

status ∈ {pending, building, done, failed}. On EVERY resume, FIRST re-read this ledger AND the
filesystem to reconstruct state — never trust memory. Mark `building` before spawning, `done`/
`failed` on validated return. Write to disk after every state change.

== BUILD ORDER (strict waves; one model at a time within a wave) ==
Wave 0: _base_v2.py infra.
Wave 1 (highest EV): 25 (HARX-HS), 15 (HAR-IVTS), 13 (LHAR), 14 (HAR-SJ), 19 (HAR-ENet/Ridge),
        18 (HAR-MAX), 28 (VRP-Spread).
Wave 2: 22 (PanelHAR-FE), 23 (HAR-Shrink2Group), 24 (HAR-GVF), 27 (HAR-QR), 20 (HAR-CSR),
        16 (HAR-Range), 17 (HAR-Act), 26 (HAR-GARCH); then 21 (EnsembleTopK-v2) — ONLY after its
        components are done, since it reads their parquets off disk.
Wave 3: 29 (Threshold-HAR), 30 (STAR-HAR), 31 (MS-HAR — gate hard).
Before each spawn, re-check the ledger; if already `done`, skip.

== PER-MODEL LOOP ==
For the next `pending` model N in wave order:
  1. Mark `building`; save.
  2. Spawn ONE general-purpose subagent with the SPAWN PROMPT (ITER2_SWARM_KICKOFF §B, {MODEL_NUMBER}=N).
     The subagent starts cold — the prompt is fully self-contained.
  3. On return, run the VALIDATION GATE. Pass → mark `done` with rows/cards/notes. Fail → FAILURE POLICY.
  4. Run `git status --porcelain`; confirm the subagent changed ONLY its own sandbox files
     (candidate_models/<file>.py, tests/test_<model>.py, cards/<name>.md(+.hard_cases.md)).
     If it touched rv_eval/, features.py, config.py, model_contract.py, _base_v2.py, pyproject.toml,
     uv.lock, or another worker's file → REVERT (git checkout) and re-run. The harness + _base_v2
     stay pristine.
  5. Save ledger; next model.

== VALIDATION GATE (a model is `done` only if ALL pass) ==
- execution/data/predictions/<name>.parquet exists with a `model` column equal to <name>.
- Contains all horizons {1,5,10,22,42} and rows for the clean_core tickers (10). hard_cases may be
  partially missing ONLY for legitimately data-starved names (IBIT, MSOS) or documented convergence
  failures — never silently for clean_core.
- rv_hat finite and > 0 on every row; quantiles q05..q95 non-decreasing (verify cheaply for the
  direct-quantile models 27/28 — they bypass the lognormal wrapper).
- Both cards exist and are non-empty: cards/<name>.md and <name>.hard_cases.md.
- The subagent reported its smoke test passed.
(Verify with a tiny polars read; do NOT run evaluator.py or the comparison yourself.)

== FAILURE POLICY ==
- Hard failure (no parquet, import error, smoke test fails): retry the SAME model ONCE with a fresh
  subagent + the prior failure summary. Twice-failed → mark `failed` with reason and MOVE ON.
- Partial hard_cases coverage from thin data / non-convergence is EXPECTED — mark `done`, ensure the
  card notes the gaps. Never impute. Never relax OOS hygiene to "fix" coverage.
- MS-HAR (31) specifically: if it does not beat the cheap regime models in its own card, still mark
  `done` but flag "candidate-for-rejection" — the comparison pass decides.

== CREDIT / USAGE-LIMIT HANDLING (the ~4-hour wait) ==
Treat any usage-limit/billing/rate-limit error as a CHECKPOINT: finish writing the ledger (revert the
in-flight model to `pending` if its gate hasn't passed), then schedule resumption. If your runtime
exposes a scheduler (ScheduleWakeup, a schedule/loop skill), re-arm ~hourly and probe with a trivial
call (`git status`); on success, resume the per-model loop from the ledger. The walk-forward upserts,
so re-running a half-done model is safe; skipping a finished one saves credit.

== STOP CONDITION ==
When Wave-0 infra + all of 13–32 are `done` or twice-`failed`, write a final ledger summary (per-model
status, parquet rows, coverage gaps, total wall time) and STOP. Do NOT run the comparison pass — it is
a separate, human-triggered step (planning_docs/execution/COMPARISON_PLAN.md), now read under the
re-weighted gate in planning_docs/research/rv_har_extensions_plan.md §4.
```
