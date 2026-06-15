"""Portfolio composition — book each trade's P&L on its expiry (realization) date (design §8).

Unlike the Stage-1 one-position-per-group abstraction, the v2 economic book holds every gated,
sized trade simultaneously (the per-group margin cap in §7 already controls correlation), so the
daily series sums all trades realizing on a given date. Sizing is off a fixed reference NAV, so the
equity curve is NAV + cumulative realized P&L.
"""

from __future__ import annotations

import polars as pl

from strategy_backtest.backtest import config as cfg

DAILY_COLS = ["date", "pnl", "gross_pnl", "cost", "n_positions", "cum_pnl", "equity"]


def to_daily(ledger: pl.DataFrame) -> pl.DataFrame:
    """Daily realized-P&L series indexed by the realization (exit) date, with cumulative P&L + equity.

    The realization date is `exit_date` — = expiry for the hold arm, but an earlier close for managed
    trades (§5). Falls back to `expiry` if a ledger predates the exit_date column.
    """
    if ledger.is_empty():
        return pl.DataFrame(schema={c: pl.Float64 for c in DAILY_COLS})
    date_col = "exit_date" if "exit_date" in ledger.columns else "expiry"
    daily = (
        ledger.group_by(pl.col(date_col).alias("date"))
        .agg(
            pnl=pl.col("pnl").sum(),
            gross_pnl=pl.col("gross_pnl").sum(),
            cost=pl.col("cost").sum(),
            n_positions=pl.len(),
        )
        .sort("date")
        .with_columns(cum_pnl=pl.col("pnl").cum_sum())
        .with_columns(equity=(pl.lit(cfg.NAV) + pl.col("cum_pnl")))
    )
    return daily.select(DAILY_COLS)
