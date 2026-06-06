"""Stage-2 cell driver — run one (model, horizon, structure, management, hedge) book on ORATS.

Flow per gated entry (entry GATING + inverse-risk SIZE are reused verbatim from `trade_eval`, so
the only new surface is the option-space P&L):

    trade_eval.prepare_scored / select_entries   ->  gated roll-date candidates (vrp, σ, gate, size)
    chains.locate_expiry                          ->  the ~30 DTE expiry
    Structure.legs + marks.open_trade             ->  legs, entry fills, credit, max-loss   (or skip)
    sizing.kelly_units                            ->  sized units (fractional Kelly)
    marks.mark_path                               ->  daily mid-mark path (mtm, delta, accrued RV, gate)
    ManagementArm.exit_on                         ->  early exit (k, reason) or hold-to-expiry
    HedgeMode (walk the path)                     ->  hedge share P&L + rebalance cost
    marks.close_value                             ->  realized leg value at exit (fills cross spread)

Emits a per-trade ledger with the SAME columns `trade_eval.portfolio` / `reports.score_stage1`
consume, so all downstream DSR/CVaR scoring carries over unchanged. P&L is in DOLLARS for the sized
position; `gross_pnl` is net of bid/ask (fills cross the spread), `cost` holds commissions +
slippage + hedge rebalancing.
"""

from __future__ import annotations

import datetime as dt

import polars as pl

from trade_eval import backtest as t_backtest
from trade_eval.signals import StrategyConfig

from stage2_trade_eval import chains, marks, sizing
from stage2_trade_eval import config as cfg
from stage2_trade_eval.contracts import (
    EntryContext, HedgeState, MarkRow, get_hedge, get_management, get_structure,
)

LEDGER_COLS = t_backtest.LEDGER_COLS   # exact schema trade_eval.portfolio expects


# --------------------------------------------------------------------------- per-ticker lookups
def _ticker_calendar(inputs: pl.DataFrame, ticker: str) -> pl.DataFrame:
    return (
        inputs.filter(pl.col("ticker") == ticker)
        .select("date", "total_rv").sort("date")
    )


def _path_inputs(cal: pl.DataFrame, gate_iv: pl.DataFrame, entry_date: dt.date, expiry: dt.date):
    """Trading dates in (entry_date, expiry], with accrued RV, prevailing gate and iv2 per day."""
    seg = cal.filter((pl.col("date") > entry_date) & (pl.col("date") <= expiry))
    if seg.is_empty():
        return [], [], [], []
    seg = seg.with_columns(accrued_rv=pl.col("total_rv").cum_sum()).join(
        gate_iv, on="date", how="left"
    )
    dates = seg["date"].to_list()
    accrued = seg["accrued_rv"].to_list()
    gates = seg["gate"].to_list()
    iv2s = seg["iv2"].to_list()
    return dates, accrued, gates, iv2s


# --------------------------------------------------------------------------- one trade
def _run_one_trade(row: dict, structure, manager, hedger, cal: pl.DataFrame, gate_iv: pl.DataFrame):
    ticker, entry_date = row["ticker"], row["entry_date"]
    chain = chains.locate_expiry(ticker, entry_date)
    if chain is None:
        return None
    ctx = EntryContext(
        ticker=ticker, group=row["group"], entry_date=entry_date, expiry=chain.expiry,
        horizon=int(row["horizon"]), spot=chain.spot,
        # NB: `target_var` (the realized [t,t+h] outcome) is DELIBERATELY excluded — it is a future
        # realization, payoff-only. Decision code (Structure/Arm/Hedge) must never see it; the engine
        # books it into the ledger straight from the entry row below, not via ctx. Only entry-dated,
        # point-in-time fields are exposed here.
        signal={k: row.get(k) for k in
                ("vrp_score", "sigma", "iv2", "gate", "size", "dispersion", "fold_id")},
    )
    # L2 leakage guard (non-negotiable): the realized [t,t+h] payoff must never reach a decision
    # function. If a refactor ever lets `target_var` (or another future realization) into the
    # decision context, fail loudly here rather than silently leak it into a Structure/Arm/Hedge.
    assert "target_var" not in ctx.signal, "target_var (a future realization) leaked into ctx.signal"
    legs = structure.legs(chain, ctx)
    if not legs:
        return None
    try:
        opened = marks.open_trade(chain, legs, ctx)
    except marks.Rejected:
        return None

    units = sizing.kelly_units(row.get("size"), structure.name)
    if units <= 0:
        return None
    units = sizing.units_to_contracts(units, opened["credit"], opened["max_loss"])
    if units <= 0:
        return None

    dates, accrued, gates, iv2s = _path_inputs(cal, gate_iv, entry_date, chain.expiry)
    if not dates:
        return None
    path = marks.mark_path(ticker, ctx, opened, dates, accrued, gates, iv2s)
    if not path:
        return None
    path_df = pl.DataFrame(path)

    decision = manager.exit_on(path_df, ctx)
    if decision is None:
        exit_k, reason = path[-1]["k"], "expiry"
    else:
        exit_k, reason = decision
    exit_row = next(p for p in path if p["k"] == exit_k)
    exit_date = exit_row["date"]

    # hedge P&L walking the path up to (and including) exit
    hedge_pnl, hedge_cost = _walk_hedge(path, exit_k, hedger, ctx)

    # realized option value at exit (fills cross spread), per unit
    leg_val, close_comm = marks.close_value(ticker, ctx, opened, exit_date, exit_k)

    mult = cfg.CONTRACT_MULTIPLIER
    gross = units * (leg_val * mult + hedge_pnl)
    cost = units * (opened["entry_commission"] + close_comm) + hedge_cost
    pnl = gross - cost

    return {
        "model": None, "horizon": int(row["horizon"]), "ablation": None,
        "ticker": ticker, "group": row["group"], "entry_date": entry_date,
        "fold_id": row.get("fold_id"), "gate": row.get("gate"), "size": float(units),
        "vrp_score": float(row.get("vrp_score") or 0.0), "iv2": float(row.get("iv2") or 0.0),
        "target_var": float(row.get("target_var") or 0.0),
        "gross_pnl": float(gross), "cost": float(cost), "pnl": float(pnl),
        "managed": decision is not None, "exit_k": int(exit_k),
        "exit_reason": reason, "exit_date": exit_date,
    }


def _walk_hedge(path: list[dict], exit_k: int, hedger, ctx: EntryContext):
    """Accumulate hedge share P&L and rebalance cost up to exit (per unit, $)."""
    state = HedgeState(last_spot=ctx.spot)
    cost = 0.0
    for p in path:
        if p["k"] > exit_k:
            break
        if state.last_spot is not None:
            state.pnl += state.shares * (p["spot"] - state.last_spot)
        mr = MarkRow(k=p["k"], dte=p["dte"], date=p["date"], spot=p["spot"], mtm=p["mtm"],
                     pos_delta=p["pos_delta"], accrued_rv=p["accrued_rv"], iv2=p["iv2"],
                     gate=p["gate"], credit=p["credit"])
        target = hedger.hedge_shares(mr, state, ctx)
        dshares = target - state.shares
        if dshares:
            cost += abs(dshares) * p["spot"] * cfg.HEDGE_COST_BPS * 1e-4
        state.shares = target
        state.last_spot = p["spot"]
    return state.pnl, cost


# --------------------------------------------------------------------------- cell
def run_cell(preds_h: pl.DataFrame, targets: pl.DataFrame, inputs: pl.DataFrame,
             model: str, structure_name: str, management_name: str, hedge_name: str,
             sc: StrategyConfig | None = None) -> pl.DataFrame:
    """Backtest one option-space cell; return the per-trade ledger (LEDGER_COLS schema)."""
    sc = sc or StrategyConfig(name="baseline", is_benchmark=(model == cfg.BENCHMARK))
    structure = get_structure(structure_name)
    manager = get_management(management_name)
    hedger = get_hedge(hedge_name)
    h = int(preds_h["horizon"][0])
    ablation = f"{structure_name}__{management_name}__{hedge_name}"

    scored = t_backtest.prepare_scored(preds_h, targets, sc)
    if scored.is_empty():
        return pl.DataFrame(schema={c: pl.Utf8 for c in LEDGER_COLS})
    entries = t_backtest.select_entries(scored, h, sc)
    # restrict to the core ETF universe (Stage-2 scope) unless the caller widened it
    entries = entries.filter(pl.col("ticker").is_in(list(cfg.CLEAN_CORE)))
    if entries.is_empty():
        return pl.DataFrame(schema={c: pl.Utf8 for c in LEDGER_COLS})

    # daily gate + iv2 per (ticker,date) for path re-gating / variance stop
    gate_iv_all = scored.filter(pl.col("horizon") == h).select("ticker", "date", "gate", "iv2")

    rows: list[dict] = []
    for ticker, ent_t in entries.group_by("ticker"):
        tk = ticker[0] if isinstance(ticker, tuple) else ticker
        cal = _ticker_calendar(inputs, tk)
        gate_iv = gate_iv_all.filter(pl.col("ticker") == tk).select("date", "gate", "iv2")
        for row in ent_t.iter_rows(named=True):
            rec = _run_one_trade(row, structure, manager, hedger, cal, gate_iv)
            if rec is not None:
                rec["model"], rec["ablation"] = model, ablation
                rows.append(rec)

    if not rows:
        return pl.DataFrame(schema={c: pl.Utf8 for c in LEDGER_COLS})
    return pl.DataFrame(rows).select(LEDGER_COLS).sort("ticker", "entry_date")
