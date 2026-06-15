"""Cross-sectional rank-selected put-credit-spread book — the Stage-B pivot candidate.

The 2026-06-11 review found the EnsembleTopK cross-sectional VRP *ranking* era-stable while the
trade-everything-gated book died post-2018, and the straddle prototype (`xsec_straddle.py`) showed
the short side carries all the dollar edge but ATM-straddle friction is ruinous. This book combines
the validated pieces:

    each week: rank the universe by score = log(iv2) - log(rv_hat_cal)   (de-biased, PIT)
        trade put-credit spreads (0.25d/0.10d, ~30 DTE, hold to expiry) on the TOP_K richest
        names only — selection, not size-tilt. Flat sizing (size_units=1), engine group-margin cap.

    No G2/G3/G4 gates: the ranking replaces them (they collapse the cross-section to ~1 name/date).
    G7 liquidity/credit still applies at fill time. HYG is excluded ex-ante on liquidity grounds
    (median ATM half-spread 6.1% of premium vs 0.5-2.7% for the rest; it hogs ~45% of top-2 slots
    and mostly rejects, wasting basket capacity).

Runs both fill assumptions (cross = worst case, mid = best case); reality is in between.

Run:  .venv/bin/python -m strategy_backtest.experiments.xsec_putspread_topk
Writes results/xsec_putspread_report.md (+ xsec_putspread_trades.csv for the cross arm).
"""

from __future__ import annotations

import datetime as dt
import math
import os
from pathlib import Path

import numpy as np
import polars as pl

from strategy_backtest.backtest import engine, pit, portfolio
from strategy_backtest.backtest import config as cfg
from strategy_backtest.pipeline import config as pcfg

# Env overrides for the breadth experiments (defaults reproduce the original 9-name run):
#   XS_DATA_ROOT  — read targets/predictions from this cache (e.g. strategy_backtest/data_wide)
#   XS_TOPK       — names per weekly roll date
#   XS_TAG        — suffix for the report/trades artifacts
#   XS_TRADEABLE  — "1": rank within the TRADEABLE set (walk the ranked list, try to open each
#                   0.25/0.10 spread on the entry chain, take the first K that fill — PIT: uses
#                   only entry-day liquidity). Fixes untradeable names hogging basket slots
#                   (e.g. XLP: 113 top-2 selections, 7 fills) on the wide universe.
#   XS_MIN_SCORE  — absolute-richness floor on the de-biased log score (e.g. "0.0": only sell
#                   names the model says are rich outright, not just rich-ranked).
TOP_K = int(os.environ.get("XS_TOPK", 2))
TRADEABLE_RANK = os.environ.get("XS_TRADEABLE", "0") == "1"
MIN_SCORE = float(os.environ.get("XS_MIN_SCORE", "-inf"))
ROLL_EVERY = 5                  # trading days between cohorts
EXCLUDE = ("HYG",)              # ex-ante liquidity exclusion (see module docstring)
MIN_NAMES_XS = 7                # names needed to rank a date
ERAS = [(2010, 2013), (2014, 2017), (2018, 2021), (2022, 2026)]
TAG = os.environ.get("XS_TAG", "")

_DATA_ROOT = Path(os.environ.get("XS_DATA_ROOT", str(cfg.DATA_ROOT)))
TARGETS_PARQUET = _DATA_ROOT / "targets.parquet"
PREDICTIONS_PARQUET = _DATA_ROOT / "predictions" / "EnsembleTopK.parquet"
# group map: pipeline config carries the breadth-extension names; backtest config the core 10
GROUP = {**cfg.GROUP, **pcfg.GROUP}


def build_candidates() -> pl.DataFrame:
    """Full-universe weekly rank panel -> engine-ready top-K candidate frame."""
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

    cal = p.select("date").unique().sort("date").with_columns(i=pl.int_range(pl.len()))
    wk = cal.filter(pl.col("i") % ROLL_EVERY == 0).select("date")
    pw = p.join(wk, on="date", how="inner")
    pw = pw.join(pw.group_by("date").agg(n=pl.len()), on="date").filter(pl.col("n") >= MIN_NAMES_XS)
    pw = pw.filter(pl.col("score") > MIN_SCORE) if MIN_SCORE > float("-inf") else pw
    pw = pw.with_columns(rk=pl.col("score").rank("ordinal", descending=True).over("date"))
    sel = _select_tradeable(pw) if TRADEABLE_RANK else pw.filter(pl.col("rk") <= TOP_K)
    return sel.with_columns(
        group=pl.col("ticker").replace_strict(GROUP),
        horizon=pl.lit(22), segment=pl.lit("xsec"),
        size_units=pl.lit(1.0), vrp_score=pl.col("iv2") - pl.col("rv_hat_cal"),
        dispersion=pl.col("sigma") / pl.col("rv_hat_cal"), ivrank=pl.lit(None, dtype=pl.Float64),
    ).select("ticker", "date", "group", "segment", "horizon", "iv2", "vrp_score", "vrp_rel",
             "dispersion", "sigma", "fold_id", "size_units", "ivrank")


def _select_tradeable(pw: pl.DataFrame) -> pl.DataFrame:
    """Walk each date's ranked list and keep the first TOP_K names whose spread actually opens.

    Openability uses only the entry-day chain (locate expiry -> strikes -> G7 fill filters), so the
    screen is point-in-time — it is exactly what a live trader observes before committing a slot.
    """
    from strategy_backtest.backtest import chains, marks, structures
    from strategy_backtest.backtest.contracts import EntryContext

    def _openable(tk: str, d) -> bool:
        ch = chains.locate_expiry(tk, d)
        if ch is None:
            return False
        ctx = EntryContext(ticker=tk, group=GROUP[tk], entry_date=d, expiry=ch.expiry,
                           horizon=22, spot=ch.spot, signal={})
        legs = structures.put_credit_spread_legs(ch, ctx)
        if not legs:
            return False
        try:
            marks.open_trade(ch, legs, ctx)
            return True
        except marks.Rejected:
            return False

    rows: list[dict] = []
    for (_d,), sub in pw.sort("date", "rk").group_by("date", maintain_order=True):
        filled = 0
        for r in sub.iter_rows(named=True):
            if filled >= TOP_K:
                break
            if _openable(r["ticker"], r["date"]):
                rows.append(r)
                filled += 1
    return pl.DataFrame(rows)


def _monthly(led: pl.DataFrame) -> pl.DataFrame:
    d = portfolio.to_daily(led)
    allm = pl.DataFrame({"date": pl.date_range(d["date"].min(), d["date"].max(), "1d", eager=True)})
    full = allm.join(d.select("date", "pnl"), on="date", how="left").fill_null(0.0)
    return full.group_by(pl.col("date").dt.truncate("1mo").alias("m")).agg(pl.col("pnl").sum()).sort("m")


def _stats(led: pl.DataFrame) -> dict:
    mo = _monthly(led)
    r = mo["pnl"].to_numpy()
    eq = np.cumsum(r)
    out = {
        "n": led.height, "pnl": float(led["pnl"].sum()),
        "sharpe": float(r.mean() / r.std(ddof=1) * math.sqrt(12)),
        "maxdd": float(np.max(np.maximum.accumulate(eq) - eq)),
        "win": float((led["pnl"] > 0).mean()),
        "mean_margin": float((led["contracts"] * led["maxloss_c"]).mean()),
    }
    for lo, hi in ERAS:
        f = mo.filter(pl.col("m").dt.year().is_between(lo, hi))["pnl"].to_numpy()
        out[f"{lo}"] = float(f.mean() / f.std(ddof=1) * math.sqrt(12)) if len(f) > 6 else float("nan")
    return out


def main() -> None:
    cand = build_candidates()
    print(f"candidates: {cand.height} ({cand['date'].n_unique()} weekly dates, top-{TOP_K})")

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
        "# Cross-sectional top-K put-credit-spread book (pivot candidate)",
        "",
        f"_top-{TOP_K} of {{universe minus {','.join(EXCLUDE)}}} by de-biased log-VRP score, weekly, "
        f"0.25d/0.10d ~30DTE hold-to-expiry, flat sizing (b={cfg.RISK_BUDGET}, NAV ${cfg.NAV/1e6:.0f}M) "
        f"· generated {dt.date.today()}_",
        "",
        "> EXPLORATORY: structure/K/exclusions were chosen on this same sample (see",
        "> `XSEC_PIVOT_FINDINGS.md` for the multiplicity discussion and the pre-registration protocol",
        "> required before any deployment decision). The daily series is realization-dated (no MTM).",
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
