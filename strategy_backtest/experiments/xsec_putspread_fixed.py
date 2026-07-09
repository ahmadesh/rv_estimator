"""Fixed-universe baseline for the frozen cross-sectional put-spread book.

Ablation question: how much of the frozen book's edge comes from the model's *cross-sectional
selection* (rank all ~29 names, gate score>0, tradeable-walk, take the 2 richest) versus simply
mechanically shorting vol on the two most liquid index ETFs every week?

This baseline holds EVERYTHING else identical to the frozen spec — same weekly cadence
(ROLL_EVERY=5, MIN_NAMES_XS still gates the date), same 0.25/0.10 ~30DTE put-credit spread,
hold-to-expiry, flat sizing (b=0.02, NAV $2M), same engine group-margin cap, same G7 fill filters,
both fill assumptions (cross/mid) — and changes ONLY the name-selection step:

    frozen : each weekly date, rank the universe by score = log(iv2) - log(rv_hat_cal),
             gate score>0, walk the ranked list, take the first 2 that fill.
    fixed  : each weekly date, trade SPY and QQQ. No ranking, no score gate. (The forecast cache
             is still read so the two names carry the same PIT score columns the engine expects,
             but the score is NOT used to select or gate.)

FIXED_UNIVERSE and an optional score>0 gate are env-configurable:
    XS_FIXED      — comma list of always-traded tickers (default "SPY,QQQ")
    XS_FIXED_GATE — "1" to additionally require score>0 on each name that week (default off:
                    the honest "no model at all" baseline trades the pair unconditionally)

Run:  XS_DATA_ROOT=strategy_backtest/data_wide XS_TAG=_fixed_spyqqq \
      .venv/bin/python -m strategy_backtest.experiments.xsec_putspread_fixed
"""

from __future__ import annotations

import datetime as dt
import os
from pathlib import Path

import polars as pl

from strategy_backtest.backtest import engine, pit
from strategy_backtest.backtest import config as cfg

# Reuse the frozen book's panel construction knobs, reporting, and engine wiring verbatim.
from strategy_backtest.experiments.xsec_putspread_topk import (
    ERAS,
    EXCLUDE,
    GROUP,
    MIN_NAMES_XS,
    PREDICTIONS_PARQUET,
    ROLL_EVERY,
    TARGETS_PARQUET,
    _stats,
)

FIXED_UNIVERSE = tuple(
    t.strip().upper() for t in os.environ.get("XS_FIXED", "SPY,QQQ").split(",") if t.strip()
)
FIXED_GATE = os.environ.get("XS_FIXED_GATE", "0") == "1"
TAG = os.environ.get("XS_TAG", "_fixed")


def build_candidates() -> pl.DataFrame:
    """Same PIT scored panel as the frozen book, but SELECT the fixed universe every week."""
    targets = pl.read_parquet(TARGETS_PARQUET).filter(pl.col("horizon") == 22).select(
        "ticker", "date", "iv2", "target_var")
    preds = pl.read_parquet(PREDICTIONS_PARQUET).filter(pl.col("horizon") == 22).select(
        "ticker", "date", "rv_hat", "sigma", "fold_id")
    fc = preds.join(targets.select("ticker", "date", "target_var"), on=["ticker", "date"], how="left")
    fc = pit.trailing_debias(fc, "rv_hat", "target_var", embargo=22, min_periods=126)
    fc = fc.with_columns(
        rv_hat_cal=pl.when(pl.col("log_bias").is_not_null())
        .then(pl.col("rv_hat") * pl.col("log_bias").exp()).otherwise(pl.col("rv_hat")))
    p = targets.join(fc.select("ticker", "date", "rv_hat_cal", "sigma", "fold_id"),
                     on=["ticker", "date"], how="inner")
    p = p.filter(~pl.col("ticker").is_in(EXCLUDE))
    p = p.filter((pl.col("iv2") > 0) & (pl.col("rv_hat_cal") > 0)).with_columns(
        score=(pl.col("iv2").log() - pl.col("rv_hat_cal").log()),
        vrp_rel=((pl.col("iv2") - pl.col("rv_hat_cal")) / pl.col("iv2")).clip(lower_bound=0.05))

    # Same weekly cadence and same date-validity gate (>=MIN_NAMES_XS names have data that day) so
    # the traded calendar is identical to the frozen book — only the name choice differs.
    cal = p.select("date").unique().sort("date").with_columns(i=pl.int_range(pl.len()))
    wk = cal.filter(pl.col("i") % ROLL_EVERY == 0).select("date")
    pw = p.join(wk, on="date", how="inner")
    pw = pw.join(pw.group_by("date").agg(n=pl.len()), on="date").filter(pl.col("n") >= MIN_NAMES_XS)

    sel = pw.filter(pl.col("ticker").is_in(FIXED_UNIVERSE))
    if FIXED_GATE:
        sel = sel.filter(pl.col("score") > 0.0)

    return sel.with_columns(
        group=pl.col("ticker").replace_strict(GROUP),
        horizon=pl.lit(22), segment=pl.lit("xsec"),
        size_units=pl.lit(1.0), vrp_score=pl.col("iv2") - pl.col("rv_hat_cal"),
        dispersion=pl.col("sigma") / pl.col("rv_hat_cal"), ivrank=pl.lit(None, dtype=pl.Float64),
    ).select("ticker", "date", "group", "segment", "horizon", "iv2", "vrp_score", "vrp_rel",
             "dispersion", "sigma", "fold_id", "size_units", "ivrank")


def main() -> None:
    cand = build_candidates()
    uni = ",".join(FIXED_UNIVERSE)
    print(f"fixed universe: {uni}  gate(score>0)={FIXED_GATE}")
    print(f"candidates: {cand.height} ({cand['date'].n_unique()} weekly dates)")

    arms = {}
    for fill in ("cross", "mid"):
        cfg.FILL = fill
        led = engine.run_book(cand, arm="hold")
        arms[fill] = {"led": led, "s": _stats(led)}
        print(f"  fill={fill}: {led.height} trades, pnl ${arms[fill]['s']['pnl']:,.0f}, "
              f"Sharpe(mo) {arms[fill]['s']['sharpe']:.2f}")
    cfg.FILL = "cross"
    arms["cross"]["led"].write_csv(cfg.RESULTS_ROOT / f"xsec_putspread_trades{TAG}.csv")

    lines = [
        "# Fixed-universe baseline put-credit-spread book (SPY/QQQ, no selection)",
        "",
        f"_always trade {{{uni}}} every weekly date{' when score>0' if FIXED_GATE else ' unconditionally'}, "
        f"0.25d/0.10d ~30DTE hold-to-expiry, flat sizing (b={cfg.RISK_BUDGET}, NAV ${cfg.NAV/1e6:.0f}M) "
        f"· generated {dt.date.today()}_",
        "",
        "> BASELINE: everything (cadence, structure, sizing, fills, G7 filters) matches the frozen",
        "> spec; ONLY the name-selection is replaced by a fixed pair. Compare against the frozen",
        "> tradeable-walk top-2 (cross 0.66 / mid 0.93) to read the value of cross-sectional selection.",
        "",
        "| fill | trades | pnl | Sharpe(mo) | maxDD | win | " + " | ".join(f"{lo}–{hi}" for lo, hi in ERAS) + " |",
        "| --- | --- | --- | --- | --- | --- | " + " | ".join("---" for _ in ERAS) + " |",
    ]
    for fill in ("cross", "mid"):
        s = arms[fill]["s"]
        eras = " | ".join(f"{s[str(lo)]:.2f}" for lo, _ in ERAS)
        lines.append(f"| {fill} | {s['n']} | ${s['pnl']:,.0f} | **{s['sharpe']:.2f}** | "
                     f"${s['maxdd']:,.0f} | {s['win']*100:.0f}% | {eras} |")
    lines += ["", "## By ticker (cross fills)", "", "| ticker | n | pnl |", "| --- | --- | --- |"]
    by_t = arms["cross"]["led"].group_by("ticker").agg(n=pl.len(), pnl=pl.col("pnl").sum()).sort(
        "pnl", descending=True)
    for r in by_t.iter_rows(named=True):
        lines.append(f"| {r['ticker']} | {r['n']} | ${r['pnl']:,.0f} |")
    (cfg.RESULTS_ROOT / f"xsec_putspread_report{TAG}.md").write_text("\n".join(lines) + "\n")
    print(f"-> results/xsec_putspread_report{TAG}.md")


if __name__ == "__main__":
    main()
