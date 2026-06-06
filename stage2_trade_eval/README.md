# stage2_trade_eval — option-marks strategy framework

Re-runs the Stage-1-promoted short-vol books on **real ORATS EOD option marks** (true strikes,
bid/ask fills, greeks, settlement) instead of the variance proxy `iv2 − target_var`. It
operationalizes **Part D** of [`STAGE2_STRATEGY_REFINEMENT_PLAN.md`](STAGE2_STRATEGY_REFINEMENT_PLAN.md)
and is built to be **reusable for the ideas in that plan**: every idea is a small registered class.

## What's reused vs new

- **Reused (unchanged):** the *entry gate* and *inverse-risk size* from `trade_eval`
  (`prepare_scored` + `select_entries`), the frozen forecasts, the one-position-per-group portfolio
  composition (`trade_eval.portfolio`), and the DSR/CVaR scoring (`trade_eval.reports.score_stage1`).
- **New (this package):** the option-space P&L — strike selection, fills/frictions, daily marking,
  management, delta-hedging — emitted as a ledger with the **same schema** the scoring already eats.

## The three plug points (mirror `rv_eval.model_contract.Model`)

| Contract | Question it answers | Plan ref | Built-ins |
|---|---|---|---|
| `Structure` | gated signal → which option legs? | §C.2 | `iron_condor`, `iron_fly`, `put_credit_spread` (defined-risk); `short_strangle`, `short_straddle` (naked) |
| `ManagementArm` | when to leave a live trade? | §B.2 | `hold` (H1), `forecast_regate` (H2), `mechanical_terminal` (H3 ★), `iv_regate` (H4) |
| `HedgeMode` | delta-hedge along the path? | §C.6 | `none`, `terminal_band`, `full_band` |

A `Structure` only ever picks strikes and returns `Leg`s for **one unit**; fills, marking, greeks,
settlement, sizing and frictions are the engine's job — so adding an idea touches one method.

## Layout

```
config.py        knobs only (DTE, deltas, fills, frictions, Kelly, margin); universe/gate reused upstream
contracts.py     Leg / EntryContext / ExpiryChain / MarkRow + the 3 ABCs + registries
chains.py        ORATS load + locate_expiry + relocate-a-leg (point-in-time)
structures.py    the 5 built-in structures            (@register_structure)
management.py    the 4 built-in arms                   (@register_management)
hedge.py         the 3 built-in hedge modes            (@register_hedge)
sizing.py        fractional-Kelly units (reuses the validated trade_eval size)
marks.py         fills / daily mid-marks / settlement / liquidity & credit filters
engine.py        run_cell(): one (model,h,structure,mgmt,hedge) book -> ledger
run.py           CLI grid driver -> results/{ledger,portfolio,manifest}
contributing.py  drop your own register_* ideas here (E1-E5, new structures) without touching core
tests/           framework pins + auto-skipped ORATS smoke
```

## Run

```bash
# default grid: {EnsembleTopK, HAR-X, IV-only} × {iron_condor, short_strangle} × {hold, mechanical_terminal} × {none}
.venv/bin/python -m stage2_trade_eval.run

# the management A/B from plan §B.2, condor only, hold-to-expiry vs terminal mechanics
.venv/bin/python -m stage2_trade_eval.run --models EnsembleTopK \
    --structures iron_condor --management hold,mechanical_terminal,forecast_regate --hedge none

.venv/bin/python -m stage2_trade_eval.run --list          # show registered plug-ins
.venv/bin/python -m pytest stage2_trade_eval/tests -q     # framework + ORATS smoke
```

Outputs land in `stage2_trade_eval/results/{ledger,portfolio}/<model>__h<h>__<struct>__<mgmt>__<hedge>.parquet`
plus `manifest.parquet`. Score them with the existing harness (point it at this `results/` dir).

## Add a new idea (example: a wider strangle + a 25%-take arm)

Put this in `contributing.py` (or any imported module):

```python
from stage2_trade_eval.contracts import Leg, Structure, register_structure

@register_structure
class WideStrangle(Structure):
    name = "wide_strangle"; defined_risk = False
    def legs(self, chain, ctx):
        kp = chain.strike_by_delta("P", 0.10); kc = chain.strike_by_delta("C", 0.10)
        return [Leg("P", kp, -1), Leg("C", kc, -1)] if kp and kc and kp < kc else []
```

then `--structures wide_strangle`. Managers and hedges extend the same way.

## P&L conventions

- Realized P&L per unit = `Σ qtyᵢ·(close_fillᵢ − entry_fillᵢ)·multiplier`, **fills cross the spread**
  (short sells @ bid / buys back @ ask); expiry settles at intrinsic. Intermediate marks use **mid**
  so management/hedge decisions aren't double-charged the spread.
- `gross_pnl` is **net of bid/ask**; `cost` holds commissions + slippage + hedge rebalancing. `pnl`
  is in **dollars for the sized position**; set `config.ROUND_TO_CONTRACTS`/`NAV` for integer-contract
  buying-power realism.
- Sizing is **fractional Kelly** = `c · (trade_eval inverse-risk size)`, capped (plan §A.5/§C.4).

## Status & limits

Working end-to-end on the confirmed ORATS lake (2007→2026, all core ETFs). **It is a framework, not
a validated result** — before trusting numbers: validate strike/structure selection against data
(plan M1), confirm the leakage guard on every path mark, and re-deflate DSR by the **new** Stage-2
trial count. The ~125-obs power caveat from Stage-1 persists: real marks add realism, not
observations. The IV-only benchmark is rebuilt **in option space** — beating it (not the variance
proxy) is the bar.
