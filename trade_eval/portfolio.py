"""Portfolio composition — one position per correlation group (STAGE1_TRADING_EVAL_PLAN.md §2.1).

A short-vol book must not stack correlated names: at most one open position per `config.GROUP`.
When several tickers in a group enter on the same roll date, the slot goes to the richest signal
(highest `vrp_score`) — a decision made entirely from t-dated information, so it adds no
look-ahead. The composed result is a **daily portfolio P&L series** (each trade's net P&L
realized on its exit date) plus the open-position count, which is the series the deferred
DSR/CVaR/drawdown scoring (with an overlap-aware block bootstrap) consumes.
"""

from __future__ import annotations

import polars as pl

DAILY_COLS = ["model", "horizon", "ablation", "date", "pnl", "n_positions", "gross_pnl", "cost"]


def select_one_per_group(ledger: pl.DataFrame) -> pl.DataFrame:
    """Keep one trade per (group, entry_date): the highest-`vrp_score` candidate."""
    if ledger.is_empty():
        return ledger
    return (
        ledger.sort(["group", "entry_date", "vrp_score"], descending=[False, False, True])
        .group_by(["group", "entry_date"], maintain_order=True)
        .first()
    )


def to_daily_portfolio(ledger: pl.DataFrame) -> pl.DataFrame:
    """Compose the per-trade ledger into a daily one-per-group portfolio P&L series.

    Each trade's net P&L is booked on its exit (realization) date; days with no realization carry
    zero. Returned series is per (model, horizon, ablation) over the book's own covered dates.
    """
    if ledger.is_empty():
        return pl.DataFrame(schema={c: pl.Utf8 for c in DAILY_COLS})
    book = select_one_per_group(ledger)
    keys = ["model", "horizon", "ablation"]
    return (
        book.group_by([*keys, "exit_date"])
        .agg(
            pnl=pl.col("pnl").sum(),
            gross_pnl=pl.col("gross_pnl").sum(),
            cost=pl.col("cost").sum(),
            n_positions=pl.len(),
        )
        .rename({"exit_date": "date"})
        .select(DAILY_COLS)
        .sort(keys + ["date"])
    )
