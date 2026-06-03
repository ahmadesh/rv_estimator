# Orchestrator Prompt — Sequential RV Model Swarm

> Paste everything in the fenced block below into the orchestrator LLM (your main
> Claude Code session). It drives a swarm of Opus 4.8 subagents **one at a time**,
> building all 13 models (0–12) from `rv_eval/MODEL_PLAN.md`, and survives credit
> interruptions by checkpointing to a durable ledger.

```
You are the ORCHESTRATOR of a sequential model-building swarm. You spawn ONE Opus 4.8
subagent at a time, each building exactly one forecasting model, until all 13 models
(0–12) in rv_eval/MODEL_PLAN.md §4 have written their predictions and model cards.
You build NOTHING yourself and you run NO comparison — you spawn, validate, record, repeat.

== AUTHORITATIVE REFERENCES (read these first, once) ==
- rv_eval/MODEL_PLAN.md            — the per-model build contract (§2 steps, §4 catalog, §5 card, §8 hygiene)
- execution_plan/SWARM_KICKOFF.md  — §B worker prompt template + Rules of Engagement; §C build order
- rv_eval/model_contract.py, rv_eval/features.py, rv_eval/config.py  — the harness the workers use
The cross-model comparison (planning_docs/execution/COMPARISON_PLAN.md, evaluator.py) is OUT OF
SCOPE. Do not run it. Stop when all 13 models are done and report.

== PRE-FLIGHT (once, at the very start; skip silently if already true) ==
1. Confirm candidate_models/ exists with __init__.py, tests/__init__.py, cards/. Create if missing.
2. Confirm the venv resolves: `uv sync --extra dev`. All model libs are already in pyproject.toml.
   Workers must NEVER touch the env — you own this step.
3. Confirm execution/data/inputs.parquet and targets.parquet exist (the panel is prebuilt).
4. Create/open the progress ledger (next section).

== DURABLE PROGRESS LEDGER (this is what makes you resumable) ==
Maintain execution_plan/swarm_progress.md as a table with one row per model 0–12:

| model | name | class spec | status | parquet rows | cards | last_update | notes |
|------|------|-----------|--------|-------------|-------|-------------|-------|

status ∈ {pending, building, done, failed}. On EVERY resume, your FIRST act is to read this
ledger and the filesystem to reconstruct state — never trust memory, you may have been wiped
mid-run. A model is `done` only if its validation gate (below) passes. Update the row to
`building` before you spawn, and to `done`/`failed` immediately when the subagent returns and
you have validated. Write the ledger to disk after every state change.

== BUILD ORDER (strict; one model at a time) ==
0, 1, 2, 3  (benchmarks — pre-coded in model_contract.py, worker only runs + cards),
then 4, 5, 6, 7, 8, 9, 10, 11  (candidates, any order),
then 12  (Ensemble — spawn ONLY after 4–11 are all `done`; it reads their parquets off disk).
Before each spawn, re-check the ledger: if the model is already `done`, skip it.

== PER-MODEL LOOP ==
For the next `pending` model N in order:
  1. Mark it `building` in the ledger; save.
  2. Spawn ONE subagent (general-purpose) with the SPAWN PROMPT below, {MODEL_NUMBER}=N.
     The subagent starts from scratch with no context — the prompt must be fully self-contained.
  3. When it returns, run the VALIDATION GATE. If it passes, mark `done` with rows/cards/notes.
     If it fails, apply the FAILURE POLICY.
  4. Run `git status --porcelain` and confirm the subagent changed ONLY:
     candidate_models/<its-file>.py, candidate_models/tests/test_<its-model>.py,
     candidate_models/cards/<its-name>.md(+.hard_cases.md). Predictions are gitignored.
     If anything under rv_eval/, pyproject.toml, uv.lock, or another worker's file changed,
     REVERT it (git checkout) and re-run the worker; the harness must stay pristine.
  5. Save ledger; proceed to the next model.

== SPAWN PROMPT (send this to each subagent; fill {MODEL_NUMBER}) ==
Copy execution_plan/SWARM_KICKOFF.md §B verbatim (the fenced worker template, including the
RULES OF ENGAGEMENT and the benchmark branch), with {MODEL_NUMBER} replaced by N. Prepend one
line: "You are a fresh worker with no prior context. Read the files named below before coding."
Do not summarize the template — paste it whole so the subagent has every instruction.

== VALIDATION GATE (a model is `done` only if ALL pass) ==
- execution/data/predictions/<name>.parquet exists and has a `model` column equal to <name>.
- It contains all horizons {1,5,10,22,42} and rows for the clean_core tickers (10). hard_cases
  tickers (up to 5) may be partially missing ONLY for legitimately data-starved names
  (IBIT, MSOS) or documented convergence failures — never silently for clean_core.
- rv_hat is finite and > 0 on every row; quantiles q05..q95 are non-decreasing.
- Both cards exist and are non-empty: candidate_models/cards/<name>.md and <name>.hard_cases.md.
- The subagent reported its smoke test passed.
(You may verify cheaply with a tiny polars read; do NOT run evaluator.py or selfstats yourself.)

== FAILURE POLICY ==
- Hard build failure (no parquet, import error, smoke test fails): retry the SAME model ONCE
  with a fresh subagent, passing the prior failure summary. If it fails twice, mark `failed`
  with the reason and MOVE ON — a missing model is dropped from the later comparison, not fatal.
- Partial coverage (some hard_cases tickers/horizons absent due to thin data or non-convergence):
  this is EXPECTED and acceptable. Mark `done`; ensure the worker noted the gaps in its card.
- Never impute missing predictions. Never relax OOS hygiene to "fix" coverage.

== CREDIT / USAGE-LIMIT HANDLING (the 4-hour wait) ==
You and your subagents cannot run while credit is exhausted, so resumption must be checkpoint-
driven, not held in memory:
  1. Treat any usage-limit / billing / rate-limit / credit-exhausted error (from a spawn or any
     tool call) as a CHECKPOINT signal. Immediately finish writing the ledger (mark the in-flight
     model back to `pending` if its gate hasn't passed) so a cold restart loses nothing.
  2. Schedule your own resumption. Credit windows typically reset on a ~4-hour cadence, so wait
     until credit is restored, then continue from the ledger. If your runtime exposes a scheduler
     (ScheduleWakeup, a cron/schedule skill, or being run under /loop), use it: re-arm a wake-up
     roughly hourly, and on each wake do a TRIVIAL probe (e.g. `git status`). If the probe fails
     with a limit error, re-arm and wait again; the moment it succeeds, resume the per-model loop.
     This resumes as soon as credit returns and in all cases within ~4 hours.
  3. On resume, RE-READ the ledger + filesystem before doing anything. Do not re-spawn a model
     whose validation gate already passes. The walk-forward upserts, so re-running a half-done
     model is safe, but skipping a finished one saves credit.

== STOP CONDITION ==
When all of models 0–12 are `done` or twice-`failed`, write a final summary to the ledger
(per-model status, parquet row counts, coverage gaps, total wall time) and STOP. Do NOT run the
comparison pass — that is a separate, human-triggered step.
```
