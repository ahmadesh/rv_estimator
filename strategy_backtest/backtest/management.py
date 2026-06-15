"""Managed-exit arm — the `mechanical_terminal` challenger to hold-to-expiry (design §5).

Hold-to-expiry (the primary arm, `engine.settle_at_expiry`) only ever looks at the entry-day chain
and the expiry-day spot. The managed arm instead walks the **daily mark path** from entry+1 to expiry
and exits on the first trigger that fires (first-trigger-wins, evaluated once per day at EOD):

    X1  profit target   mark P&L >= TAKE_FRAC * credit            (bank the winner before terminal gamma)
    X5  hard stop        mark loss >= HARD_STOP_MULT * credit      (capped by the wing anyway)
    X4  variance stop    Σ realized var since entry  >  entry iv2  (model-free; doc §5.1 X4)
    X3  term-flip        iv_slope < -X3_DEADBAND for X3_CONFIRM_DAYS consecutive days (round-trip cost)
    X2  terminal         hard close at DTE <= TERMINAL_DTE_HARD     (no soft tier — resolved 2026-06-08)
    X7  expiry           else settle at intrinsic                  (= the hold arm)

Triggers are evaluated on the chain MID (smooth, gap-free) so a wide bid/ask never fires a trigger
spuriously; the actual close is filled by crossing the spread (`marks.mark_close`). `manage_trade`
returns the same realized leg value contract the hold path produces, so the engine books either arm
identically.

DISCLOSED BIASES (carry over from §8.4, plus managed-specific):
  * EOD-only path: a gap-down blows past X5/X4 and we can only act at the *next* EOD — understates the
    short-gamma tail (the DTE<=12 hard close mitigates, doesn't remove).
  * X3 round-trip cost is modeled as a doubled close commission (close + notional reopen); the reopen
    *spread* is not separately repriced (the next monthly roll is a separate candidate).
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

import polars as pl

from strategy_backtest.backtest import chains, marks
from strategy_backtest.backtest import config as cfg
from strategy_backtest.backtest.contracts import EntryContext


@dataclass
class DailyPanel:
    """Per-(ticker, date) daily series the managed triggers need (iv_slope for X3, total_rv for X4)."""

    iv_slope: dict[str, dict[dt.date, float]]
    total_rv: dict[str, dict[dt.date, float]]
    dates: dict[str, list[dt.date]]

    def trade_dates(self, ticker: str, after: dt.date, upto: dt.date) -> list[dt.date]:
        """Sorted trading dates in (after, upto] for `ticker` — the days the trade is marked."""
        return [d for d in self.dates.get(ticker, ()) if after < d <= upto]


def load_panel() -> DailyPanel:
    """Build the daily trigger panel from inputs.parquet (one read, cached by the caller)."""
    df = (
        pl.read_parquet(cfg.INPUTS_PARQUET)
        .select("ticker", "date", "iv_slope", "total_rv")
        .sort("ticker", "date")
    )
    iv_slope: dict[str, dict[dt.date, float]] = {}
    total_rv: dict[str, dict[dt.date, float]] = {}
    dates: dict[str, list[dt.date]] = {}
    for (tk,), sub in df.group_by("ticker", maintain_order=True):
        ds = sub["date"].to_list()
        dates[tk] = ds
        iv_slope[tk] = dict(zip(ds, sub["iv_slope"].to_list()))
        total_rv[tk] = dict(zip(ds, sub["total_rv"].to_list()))
    return DailyPanel(iv_slope=iv_slope, total_rv=total_rv, dates=dates)


def _exit(d: dt.date, reason: str, mk: dict, short_strike: float, *, roundtrip: bool = False) -> dict:
    """Build the managed-exit result from an early-close mark (mirrors settle_at_expiry's contract)."""
    close_comm = mk["close_commission"] * (2.0 if roundtrip else 1.0)   # X3 round-trip = close + reopen
    return {
        "exit_date": d, "exit_reason": reason,
        "leg_val": mk["leg_val_close"], "settle_spot": mk["spot"],
        "breached": mk["spot"] < short_strike, "close_commission": close_comm,
    }


def manage_trade(ctx: EntryContext, opened: dict, panel: DailyPanel,
                 *, drop_x3: bool = False) -> dict | None:
    """Walk the daily mark path entry+1 -> expiry; return the first-trigger exit (or expiry settle).

    Result dict: exit_date, exit_reason, leg_val (per-unit realized vs entry fills), settle_spot,
    breached (short ITM at exit), close_commission (per-unit, $). None if expiry can't be settled.
    """
    legs, fills = opened["legs"], opened["entry_fills"]
    credit, short_k = opened["credit"], opened["short_strike"]
    iv2_entry = float(ctx.signal["iv2"])
    take_lvl = cfg.TAKE_FRAC * credit
    stop_lvl = -cfg.HARD_STOP_MULT * credit

    accrued_rv = 0.0
    x3_streak = 0
    for d in panel.trade_dates(ctx.ticker, ctx.entry_date, ctx.expiry):
        rv_d = panel.total_rv.get(ctx.ticker, {}).get(d)
        if rv_d is not None:
            accrued_rv += rv_d
        slope = panel.iv_slope.get(ctx.ticker, {}).get(d)

        chain = chains.expiry_slice(ctx.ticker, d, ctx.expiry)
        mk = marks.mark_close(chain, legs, fills) if chain is not None else None

        if mk is not None:
            if mk["markpnl_mid"] >= take_lvl:                       # X1 profit target
                return _exit(d, "X1_take", mk, short_k)
            if mk["markpnl_mid"] <= stop_lvl:                       # X5 hard stop
                return _exit(d, "X5_hardstop", mk, short_k)
            if accrued_rv > iv2_entry:                              # X4 variance stop (model-free)
                return _exit(d, "X4_varstop", mk, short_k)

        if not drop_x3 and slope is not None:                      # X3 term-flip (confirmed + dead-band)
            x3_streak = x3_streak + 1 if slope < -cfg.X3_DEADBAND else 0
            if x3_streak >= cfg.X3_CONFIRM_DAYS and mk is not None:
                return _exit(d, "X3_termflip", mk, short_k, roundtrip=True)

        if (ctx.expiry - d).days <= cfg.TERMINAL_DTE_HARD and mk is not None:   # X2 terminal hard close
            return _exit(d, "X2_terminal", mk, short_k)

    # X7 — held to expiry, settle at intrinsic (identical to the hold arm).
    settled = marks.settle_at_expiry(ctx.ticker, ctx, opened)
    if settled is None:
        return None
    return {
        "exit_date": ctx.expiry, "exit_reason": "expiry",
        "leg_val": settled["leg_val"], "settle_spot": settled["settle_spot"],
        "breached": settled["breached"], "close_commission": 0.0,
    }
