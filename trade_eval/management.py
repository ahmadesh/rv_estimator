"""Intra-trade management overlay — daily re-gating (STAGE1_TRADING_EVAL_PLAN.md §3.5, A9).

A short-gamma book should not be opened at the monthly roll and blindly held to expiry: a fresh
forecast and a fresh gate exist on every day of the trade's life. This module marks each open
position **daily** along its path using the variance-accrual mark — realized variance accrued so
far plus the remaining implied carry at the prevailing iv2 — and fires the management rules off
that mark:

  - risk-off exit : the re-evaluated gate flips to `avoid` mid-trade,
  - profit-take   : mark P&L >= TAKE_FRAC · capturable premium,
  - variance stop : accrued realized var already exceeds the entry iv2, or mark loss > STOP_MULT·credit.

The mark is an approximation (no greeks / smile / assignment — that is Stage-2 ORATS); it is
enough to rank a managed overlay against hold-to-expiry. By construction the k=h mark with no
exit equals the terminal payoff against the accrued realized variance, which `tests/` pins down.
"""

from __future__ import annotations

import polars as pl

from trade_eval import config as cfg
from trade_eval.signals import StrategyConfig


def _cost_expr() -> pl.Expr:
    """Round-trip cost as bps of premium sold — identical charge to the hold-to-expiry path."""
    c_bps = pl.col("ticker").replace_strict(cfg.C_BPS, default=cfg.C_BPS_DEFAULT, return_dtype=pl.Float64)
    return (c_bps * 1e-4) * cfg.COST_ROUND_TRIP * pl.col("size") * pl.col("iv2")


def managed_pnl(
    entries: pl.DataFrame,
    scored: pl.DataFrame,
    inputs: pl.DataFrame,
    h: int,
    sc: StrategyConfig,
) -> pl.DataFrame:
    """Attach managed gross P&L + exit info to `entries` via the daily variance-accrual mark."""
    # Per-ticker trading calendar from the daily RV path, with the prevailing iv2 and the
    # point-in-time gate (re-evaluated each day from the same signals) joined on.
    cal = (
        inputs.select("ticker", "date", "total_rv")
        .sort("ticker", "date")
        .with_columns(_cidx=pl.int_range(pl.len()).over("ticker"))
        .join(
            scored.filter(pl.col("horizon") == h).select("ticker", "date", "iv2", "gate"),
            on=["ticker", "date"], how="left",
        )
        .rename({"iv2": "iv2_t"})
        .with_columns(_cmax=pl.col("_cidx").max().over("ticker"))
    )

    ent = entries.with_row_index("trade_id").join(
        cal.select("ticker", pl.col("date").alias("entry_date"), "_cidx", "_cmax"),
        on=["ticker", "entry_date"], how="left",
    )
    # Keep only trades whose full h-day path exists (matches target_var availability on the hold path).
    ent = ent.filter((pl.col("_cidx") + h) <= pl.col("_cmax")).rename({"_cidx": "_cidx_e"})

    calp = cal.select(
        "ticker", pl.col("_cidx").alias("_pcidx"),
        pl.col("date").alias("path_date"), "total_rv", "iv2_t", "gate",
    )
    path = (
        ent.select("trade_id", "ticker", "size", pl.col("iv2").alias("iv2_entry"), "_cidx_e")
        .with_columns(k=pl.int_ranges(1, h + 1))
        .explode("k")
        .with_columns(_pcidx=pl.col("_cidx_e") + pl.col("k"))
        .join(calp, on=["ticker", "_pcidx"], how="left")
        .sort("trade_id", "k")
    )

    premium = pl.col("size") * pl.col("iv2_entry")            # max capturable credit
    # Prevailing iv2 may be missing on the last days of the sample (truth ends before the daily
    # calendar); assume the carry is unchanged from entry there. This also avoids null·0 at k=h.
    iv2_prevailing = pl.col("iv2_t").fill_null(pl.col("iv2_entry"))
    path = path.with_columns(accrued_rv=pl.col("total_rv").cum_sum().over("trade_id")).with_columns(
        mark_value=(pl.col("accrued_rv") + iv2_prevailing * (h - pl.col("k")) / h),
    ).with_columns(
        mark_pnl=(pl.col("size") * cfg.SIGN_SHORT * (pl.col("iv2_entry") - pl.col("mark_value"))),
    ).with_columns(
        _risk_off=(pl.col("gate") == "avoid"),
        _stop=((pl.col("accrued_rv") > pl.col("iv2_entry"))
               | (pl.col("mark_pnl") < -cfg.STOP_MULT * premium)),
        _take=(pl.col("mark_pnl") >= cfg.TAKE_FRAC * premium),
    ).with_columns(
        _exit=(pl.col("_risk_off").fill_null(False) | pl.col("_stop") | pl.col("_take")),
        reason=(
            pl.when(pl.col("_risk_off").fill_null(False)).then(pl.lit("risk_off"))
            .when(pl.col("_stop")).then(pl.lit("stop"))
            .when(pl.col("_take")).then(pl.lit("take"))
            .otherwise(pl.lit("expiry"))
        ),
    )

    # First firing day per trade (else hold to k=h).
    exit_k = (
        path.filter(pl.col("_exit")).group_by("trade_id").agg(pl.col("k").min().alias("exit_k"))
    )
    path = path.join(exit_k, on="trade_id", how="left").with_columns(
        exit_k=pl.col("exit_k").fill_null(h)
    )
    sel = path.filter(pl.col("k") == pl.col("exit_k")).select(
        "trade_id",
        gross_pnl=pl.col("mark_pnl"),
        exit_k=pl.col("exit_k"),
        exit_reason=pl.col("reason"),
        exit_date=pl.col("path_date"),
    )

    return (
        ent.join(sel, on="trade_id", how="left")
        .with_columns(cost=_cost_expr(), managed=pl.lit(True))
        .drop("trade_id", "_cidx_e", "_cmax")
    )
