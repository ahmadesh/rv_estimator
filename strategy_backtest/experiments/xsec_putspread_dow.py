"""Day-of-week cadence experiment for the frozen cross-sectional put-spread book.

The frozen spec (§2.3) rolls "every 5th trading day of the prediction calendar" (`ROLL_EVERY=5`).
That anchors to a trading-day *count*, so the actual entry weekday drifts across Mon–Fri as holidays
shift the count. This experiment asks two questions:

  1. What are the full P&L / Sharpe numbers if we instead trade a FIXED weekday every week
     (e.g. every Monday)?
  2. Which weekday produces the best results?

The ONLY thing that changes vs the frozen run is the set of cohort dates. Everything else — the
universe, the de-biased score, the score>0 gate, the tradeable-walk top-2 selection, the structure,
sizing, fills, settlement, and the stats — is imported verbatim from `xsec_putspread_topk` so the
comparison is apples-to-apples. We reproduce the frozen settings (TOPK=2, TRADEABLE=1, MIN_SCORE=0)
by default.

Holiday handling: a fixed weekday isn't tradeable every week (MLK/Presidents/Memorial/Labor Mondays,
etc.). For target weekday W we pick, within each ISO week, the exact-W trading day if it exists, else
the nearest *later* trading day that week, else the nearest earlier one. That keeps ~one cohort/week
just like roll-5, only re-phased onto W.

Run:  .venv/bin/python -m strategy_backtest.experiments.xsec_putspread_dow
Writes results/xsec_putspread_dow_report.md (+ per-weekday cross-fill trade ledgers).
"""

from __future__ import annotations

import datetime as dt
import os

# Reproduce the frozen run's knobs before importing the base module (it reads these at import).
os.environ.setdefault("XS_DATA_ROOT", "strategy_backtest/data_wide")
os.environ.setdefault("XS_TOPK", "2")
os.environ.setdefault("XS_TRADEABLE", "1")
os.environ.setdefault("XS_MIN_SCORE", "0.0")

import polars as pl

from strategy_backtest.backtest import engine, pit
from strategy_backtest.backtest import config as cfg
from strategy_backtest.experiments import xsec_putspread_topk as base

WD_NAMES = {1: "Mon", 2: "Tue", 3: "Wed", 4: "Thu", 5: "Fri"}


def _base_panel() -> pl.DataFrame:
    """The per-(ticker, date) score panel BEFORE any cadence filter.

    Mirrors `base.build_candidates` lines up to the ROLL_EVERY block so the score/de-bias/exclusion
    are identical; we then apply our own cadence instead of `i % ROLL_EVERY == 0`.
    """
    targets = pl.read_parquet(base.TARGETS_PARQUET).filter(pl.col("horizon") == 22).select(
        "ticker", "date", "iv2", "target_var")
    preds = pl.read_parquet(base.PREDICTIONS_PARQUET).filter(pl.col("horizon") == 22).select(
        "ticker", "date", "rv_hat", "sigma", "fold_id")
    fc = preds.join(targets.select("ticker", "date", "target_var"), on=["ticker", "date"], how="left")
    fc = pit.trailing_debias(fc, "rv_hat", "target_var", embargo=22, min_periods=126)
    fc = fc.with_columns(
        rv_hat_cal=pl.when(pl.col("log_bias").is_not_null())
        .then(pl.col("rv_hat") * pl.col("log_bias").exp()).otherwise(pl.col("rv_hat")))
    p = targets.join(fc.select("ticker", "date", "rv_hat_cal", "sigma", "fold_id"),
                     on=["ticker", "date"], how="inner")
    p = p.filter(~pl.col("ticker").is_in(base.EXCLUDE))
    p = p.filter((pl.col("iv2") > 0) & (pl.col("rv_hat_cal") > 0)).with_columns(
        score=(pl.col("iv2").log() - pl.col("rv_hat_cal").log()),
        vrp_rel=((pl.col("iv2") - pl.col("rv_hat_cal")) / pl.col("iv2")).clip(lower_bound=0.05))
    return p


def _project(sel: pl.DataFrame) -> pl.DataFrame:
    """The engine-ready candidate projection (identical to base.build_candidates tail)."""
    return sel.with_columns(
        group=pl.col("ticker").replace_strict(base.GROUP),
        horizon=pl.lit(22), segment=pl.lit("xsec"),
        size_units=pl.lit(1.0), vrp_score=pl.col("iv2") - pl.col("rv_hat_cal"),
        dispersion=pl.col("sigma") / pl.col("rv_hat_cal"), ivrank=pl.lit(None, dtype=pl.Float64),
    ).select("ticker", "date", "group", "segment", "horizon", "iv2", "vrp_score", "vrp_rel",
             "dispersion", "sigma", "fold_id", "size_units", "ivrank")


def _cohort_dates(cal: pl.DataFrame, cadence) -> pl.DataFrame:
    """Return the `date` frame of cohort roll dates for a given cadence.

    cadence == "roll5": the frozen every-5th-trading-day rule (baseline).
    cadence in 1..5:    fixed ISO weekday W (1=Mon..5=Fri) with holiday fallback to nearest
                        later-then-earlier trading day within the same ISO week.
    """
    if cadence == "roll5":
        c = cal.with_columns(i=pl.int_range(pl.len()))
        return c.filter(pl.col("i") % base.ROLL_EVERY == 0).select("date")
    target = int(cadence)
    c = cal.with_columns(
        wd=pl.col("date").dt.weekday(),
        iy=pl.col("date").dt.iso_year(),
        iw=pl.col("date").dt.week(),
    ).with_columns(
        # exact weekday best (0); else prefer later in the week (1,2,..); else earlier (+10 penalty)
        pref=pl.when(pl.col("wd") >= target)
        .then(pl.col("wd") - target)
        .otherwise(target - pl.col("wd") + 10))
    pick = (c.sort(["iy", "iw", "pref", "date"])
            .group_by(["iy", "iw"], maintain_order=True)
            .first())
    return pick.select("date").sort("date")


def build_candidates(cadence) -> pl.DataFrame:
    p = _base_panel()
    cal = p.select("date").unique().sort("date")
    wk = _cohort_dates(cal, cadence)
    pw = p.join(wk, on="date", how="inner")
    pw = pw.join(pw.group_by("date").agg(n=pl.len()), on="date").filter(
        pl.col("n") >= base.MIN_NAMES_XS)
    pw = pw.filter(pl.col("score") > base.MIN_SCORE) if base.MIN_SCORE > float("-inf") else pw
    pw = pw.with_columns(rk=pl.col("score").rank("ordinal", descending=True).over("date"))
    sel = base._select_tradeable(pw) if base.TRADEABLE_RANK else pw.filter(pl.col("rk") <= base.TOP_K)
    return _project(sel)


def run_cadence(cadence) -> dict:
    cand = build_candidates(cadence)
    arms = {}
    for fill in ("cross", "mid"):
        cfg.FILL = fill
        led = engine.run_book(cand, arm="hold")
        arms[fill] = {"led": led, "s": base._stats(led)}
    cfg.FILL = "cross"
    return {"cohorts": cand["date"].n_unique(), "arms": arms}


def main() -> None:
    cadences = [1, 2, 3, 4, 5, "roll5"]
    results = {}
    for cad in cadences:
        label = WD_NAMES.get(cad, "roll5")
        print(f"== cadence {label} ==")
        res = run_cadence(cad)
        results[cad] = res
        for fill in ("cross", "mid"):
            s = res["arms"][fill]["s"]
            print(f"   {fill}: {res['cohorts']} cohorts, {s['n']} trades, "
                  f"pnl ${s['pnl']:,.0f}, Sharpe(mo) {s['sharpe']:.2f}")
        # save the cross-fill ledger per weekday for drill-down
        tag = WD_NAMES.get(cad, "roll5").lower()
        res["arms"]["cross"]["led"].write_csv(
            cfg.RESULTS_ROOT / f"xsec_putspread_dow_{tag}_trades.csv")

    era_hdr = " | ".join(f"{lo}–{hi}" for lo, hi in base.ERAS)
    lines = [
        "# Day-of-week cadence experiment — frozen cross-sectional put-spread book",
        "",
        f"_Frozen spec varied on cadence ONLY (universe/score/gate/tradeable-walk/structure/sizing/"
        f"fills identical). TOPK={base.TOP_K}, TRADEABLE={int(base.TRADEABLE_RANK)}, "
        f"MIN_SCORE={base.MIN_SCORE}, NAV ${cfg.NAV/1e6:.0f}M, b={cfg.RISK_BUDGET} · "
        f"generated {dt.date.today()}_",
        "",
        "`roll5` = the frozen every-5th-trading-day baseline (weekday floats). `Mon..Fri` = fixed "
        "ISO weekday with holiday fallback to the nearest later/earlier trading day that week.",
        "",
        "## Cross fills (worst case)",
        "",
        f"| cadence | cohorts | trades | pnl | Sharpe(mo) | maxDD | win | {era_hdr} |",
        "| --- | --- | --- | --- | --- | --- | --- | " + " | ".join("---" for _ in base.ERAS) + " |",
    ]
    for cad in cadences:
        label = WD_NAMES.get(cad, "roll5")
        s = results[cad]["arms"]["cross"]["s"]
        eras = " | ".join(f"{s[str(lo)]:.2f}" for lo, _ in base.ERAS)
        lines.append(f"| {label} | {results[cad]['cohorts']} | {s['n']} | ${s['pnl']:,.0f} | "
                     f"**{s['sharpe']:.2f}** | ${s['maxdd']:,.0f} | {s['win']*100:.0f}% | {eras} |")
    lines += ["", "## Mid fills (best case)", "",
              f"| cadence | cohorts | trades | pnl | Sharpe(mo) | maxDD | win | {era_hdr} |",
              "| --- | --- | --- | --- | --- | --- | --- | " + " | ".join("---" for _ in base.ERAS) + " |"]
    for cad in cadences:
        label = WD_NAMES.get(cad, "roll5")
        s = results[cad]["arms"]["mid"]["s"]
        eras = " | ".join(f"{s[str(lo)]:.2f}" for lo, _ in base.ERAS)
        lines.append(f"| {label} | {results[cad]['cohorts']} | {s['n']} | ${s['pnl']:,.0f} | "
                     f"**{s['sharpe']:.2f}** | ${s['maxdd']:,.0f} | {s['win']*100:.0f}% | {eras} |")

    out = cfg.RESULTS_ROOT / "xsec_putspread_dow_report.md"
    out.write_text("\n".join(lines) + "\n")
    print(f"-> {out}")


if __name__ == "__main__":
    main()
