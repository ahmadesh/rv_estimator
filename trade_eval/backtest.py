"""Stage-1 variance-proxy backtest engine (STAGE1_TRADING_EVAL_PLAN.md §3).

The fast, model-ranking layer. For one `(model, horizon, ablation)` cell it joins the frozen
forecast to truth, builds the strategy signals, opens one position per non-overlapping `h`-day
block, and books the terminal variance payoff

    pnl = size · sign_short · (iv2_t − target_var_t) − cost

(or, when the management overlay is on, the early-exit P&L from `management.py`). It emits a
**per-trade ledger** — the atomic result the later DSR/CVaR scoring and the portfolio
composition consume. No estimation, no refits: every input row is frozen and point-in-time.
"""

from __future__ import annotations

import polars as pl

from trade_eval import config as cfg
from trade_eval import management
from trade_eval.signals import StrategyConfig, build_signals

# Truth columns pulled from targets.parquet onto each forecast row.
_TRUTH_COLS = ["group", "target_var", "iv2", "iv_pctile_bucket", "post_shock"]

LEDGER_COLS = [
    "model", "horizon", "ablation", "ticker", "group", "entry_date", "fold_id",
    "gate", "size", "vrp_score", "iv2", "target_var",
    "gross_pnl", "cost", "pnl", "managed", "exit_k", "exit_reason", "exit_date",
]


def prepare_scored(preds_h: pl.DataFrame, targets: pl.DataFrame, sc: StrategyConfig) -> pl.DataFrame:
    """Inner-join one horizon's forecasts to truth and attach the strategy signals.

    Inner join = common support only; missing cells are dropped, never imputed (§6 coverage
    honesty). The returned frame carries a gate/size for *every* date (not just roll dates) so the
    A9 management overlay can re-gate intra-trade off the same point-in-time signals.
    """
    h = int(preds_h["horizon"][0])
    truth = targets.filter(pl.col("horizon") == h).select("ticker", "date", "horizon", *_TRUTH_COLS)
    scored = preds_h.join(truth, on=["ticker", "date", "horizon"], how="inner").drop_nulls(
        ["rv_hat", "iv2", "target_var"]
    )
    return build_signals(scored, sc)


def select_entries(scored: pl.DataFrame, h: int, sc: StrategyConfig) -> pl.DataFrame:
    """Pick non-overlapping roll-date entries and apply the entry-mode (A7 controls).

    Entries fall on every `ROLL_CADENCE[h]`-th trading day per ticker, so holding windows do not
    overlap within a name. The entry mode decides which roll dates take a position and how it is
    sized: `signal` follows the gate/size; `always` sells every roll date flat (pure short-vol
    carry control); `random` sells a deterministic random subset flat (luck control).
    """
    cadence = cfg.ROLL_CADENCE[h]
    scored = scored.sort("ticker", "date").with_columns(
        _cidx=pl.int_range(pl.len()).over("ticker")
    )
    roll = scored.filter((pl.col("_cidx") % cadence) == 0)

    haircut = pl.col("structure_haircut")
    if sc.entry == "signal":
        enter = pl.col("size") > 0
        eff_size = pl.col("size")
    elif sc.entry == "always":
        enter = pl.lit(True)
        eff_size = cfg.BASE_NOTIONAL * haircut          # flat, gate ignored
    elif sc.entry == "random":
        rng = pl.col("date").hash(seed=cfg.RANDOM_ENTRY_SEED) % 1000 / 1000.0
        enter = rng < cfg.RANDOM_ENTRY_RATE
        eff_size = cfg.BASE_NOTIONAL * haircut
    else:  # pragma: no cover - guarded by ablation registry
        raise ValueError(f"unknown entry mode {sc.entry!r}")

    return (
        roll.with_columns(enter=enter, eff_size=eff_size)
        .filter(pl.col("enter") & (pl.col("eff_size") > 0))
        .with_columns(size=pl.col("eff_size"), entry_date=pl.col("date"))
        .drop("eff_size", "enter", "_cidx")  # _cidx was scored-row order; downstream re-derives
    )                                        # its own calendar index from inputs, avoid collision


def _cost(size: pl.Expr, iv2: pl.Expr, ticker: pl.Expr) -> pl.Expr:
    """Per-trade cost: round-trip bps of the premium sold (variance units, like the P&L)."""
    c_bps = ticker.replace_strict(cfg.C_BPS, default=cfg.C_BPS_DEFAULT, return_dtype=pl.Float64)
    return (c_bps * 1e-4) * cfg.COST_ROUND_TRIP * size * iv2


def _exit_dates_hold(entries: pl.DataFrame, inputs: pl.DataFrame, h: int) -> pl.DataFrame:
    """Map each entry to the trading date `h` days forward (its hold-to-expiry realization date)."""
    cal = (
        inputs.select("ticker", "date")
        .sort("ticker", "date")
        .with_columns(_cidx=pl.int_range(pl.len()).over("ticker"))
    )
    ent = entries.join(
        cal.select("ticker", pl.col("date").alias("entry_date"), "_cidx"),
        on=["ticker", "entry_date"], how="left",
    )
    exit_cal = cal.select("ticker", pl.col("_cidx").alias("_exit_cidx"), pl.col("date").alias("exit_date"))
    return ent.with_columns(_exit_cidx=pl.col("_cidx") + h).join(
        exit_cal, on=["ticker", "_exit_cidx"], how="left"
    ).drop("_cidx", "_exit_cidx")


def _hold_to_expiry(entries: pl.DataFrame, inputs: pl.DataFrame, h: int) -> pl.DataFrame:
    """Terminal-payoff P&L; the position is held the full `h` days."""
    return _exit_dates_hold(entries, inputs, h).with_columns(
        gross_pnl=(pl.col("size") * cfg.SIGN_SHORT * (pl.col("iv2") - pl.col("target_var"))),
        cost=_cost(pl.col("size"), pl.col("iv2"), pl.col("ticker")),
        managed=pl.lit(False),
        exit_k=pl.lit(h, dtype=pl.Int64),
        exit_reason=pl.lit("expiry"),
    )


def run_cell(
    preds_h: pl.DataFrame,
    targets: pl.DataFrame,
    inputs: pl.DataFrame,
    sc: StrategyConfig,
    model: str,
) -> pl.DataFrame:
    """Backtest one `(model, horizon, ablation)` cell; return the per-trade ledger."""
    h = int(preds_h["horizon"][0])
    scored = prepare_scored(preds_h, targets, sc)
    if scored.is_empty():
        return pl.DataFrame(schema={c: pl.Utf8 for c in LEDGER_COLS})
    entries = select_entries(scored, h, sc)
    if entries.is_empty():
        return pl.DataFrame(schema={c: pl.Utf8 for c in LEDGER_COLS})

    if sc.manage:
        entries = management.managed_pnl(entries, scored, inputs, h, sc)
    else:
        entries = _hold_to_expiry(entries, inputs, h)

    entries = entries.with_columns(
        pnl=(pl.col("gross_pnl") - pl.col("cost")),
        model=pl.lit(model),
        ablation=pl.lit(sc.name),
    )
    return entries.select(LEDGER_COLS).sort("ticker", "entry_date")
