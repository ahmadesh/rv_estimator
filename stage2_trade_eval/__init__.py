"""Stage-2 option-marks trading-evaluation framework.

Where `trade_eval/` scores forecasters on a **variance proxy** (`pnl = iv2 - target_var`), this
package re-runs the promoted short-vol books on **real ORATS EOD option marks** — true strikes,
bid/ask fills, greeks, settlement — so the economic readouts (DSR / CVaR / drawdown) are on
dollars a desk could actually have earned. It operationalizes Part D of
`STAGE2_STRATEGY_REFINEMENT_PLAN.md`.

Design goal: **reusable to try the ideas in the plan.** Three things are pluggable via small
registered classes, exactly mirroring how `rv_eval.model_contract.Model` lets you drop in a new
forecaster:

  * a `Structure`      — how a gated signal becomes option legs (straddle, strangle, condor, …);
  * a `ManagementArm`  — when to leave a live trade (hold, mechanical terminal-week, IV re-gate);
  * a `HedgeMode`      — whether/how to delta-hedge along the path (none, terminal-band, …).

The entry **gating and sizing are reused verbatim** from the validated `trade_eval` layer
(`prepare_scored` + `select_entries`), so the only new surface is the option-space P&L. The
engine emits a ledger with the **same schema** `trade_eval.portfolio` / `reports.score_stage1`
already consume, so all downstream scoring carries over unchanged.

Nothing here refits a forecaster; predictions are frozen (`execution/data/predictions/`).
"""
