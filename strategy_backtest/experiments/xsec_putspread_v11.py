"""v1.1 candidate: pair-core + non-pair overlay (improvement I2 / spec §8.6) — ex-ante spec.

Spec §6.6/§8.6 finding: the no-model SPY/QQQ book ties the frozen book at cross fills and is only
0.60 monthly-correlated with it; a 50/50 monthly blend beat both. The natural design, written down
BEFORE this run and executed once:

    CORE    : sell the frozen 0.25Δ/0.10Δ ~30DTE put spread on SPY and QQQ every weekly cohort
              date, unconditionally (no score gate), b=0.02 each — the §6.6 fixed baseline verbatim.
    OVERLAY : the frozen top-2 tradeable-walk (score>0 gate) on the universe MINUS {SPY, QQQ}
              (and HYG as ever) — the model trades only where it adds names the core doesn't own.
    BOOK    : one combined ledger through one engine pass, so the concurrent 20%-of-NAV group
              margin cap binds across sleeves (core and overlay can share a group, e.g. XLK with
              the pair's us_large_cap_equity neighbors).

MULTIPLICITY: this design was motivated by results observed on this same 2010–26 sample. It is a
v1.1 *candidate* carrying fresh multiplicity debt — it must clear the §7 shadow-run protocol
ex-ante, never be retro-fitted into v1.0's evaluation.

Run:  XS_DATA_ROOT=strategy_backtest/data_wide XS_TOPK=2 XS_TRADEABLE=1 XS_MIN_SCORE=0.0 \
      .venv/bin/python -m strategy_backtest.experiments.xsec_putspread_v11
"""

from __future__ import annotations

import datetime as dt
import math

import polars as pl

from strategy_backtest.backtest import engine
from strategy_backtest.backtest import config as cfg
from strategy_backtest.experiments import xsec_putspread_topk as xt
from strategy_backtest.experiments import xsec_putspread_fixed as xf

OUT_MD = cfg.RESULTS_ROOT / "xsec_putspread_v11.md"
PAIR = ("SPY", "QQQ")
ERAS = xt.ERAS


def _monthly(led: pl.DataFrame) -> pl.DataFrame:
    d = led.group_by(pl.col("exit_date").alias("date")).agg(pnl=pl.col("pnl").sum()).sort("date")
    alld = pl.DataFrame({"date": pl.date_range(d["date"].min(), d["date"].max(), "1d", eager=True)})
    return (alld.join(d, on="date", how="left").fill_null(0.0)
            .group_by(pl.col("date").dt.truncate("1mo").alias("m")).agg(pl.col("pnl").sum()).sort("m"))


def main() -> None:
    cfg.FILL = "cross"
    core = xf.build_candidates()                       # unconditional SPY/QQQ, weekly
    orig_exclude = xt.EXCLUDE
    xt.EXCLUDE = tuple(set(orig_exclude) | set(PAIR))  # overlay universe drops the pair
    try:
        overlay = xt.build_candidates()
    finally:
        xt.EXCLUDE = orig_exclude
    combined = pl.concat([
        core.with_columns(pl.col("fold_id").cast(pl.Int64)),
        overlay.with_columns(pl.col("fold_id").cast(pl.Int64)),
    ]).sort("date", "ticker")
    print(f"core {core.height} + overlay {overlay.height} = {combined.height} candidates")

    out: dict[str, dict] = {}
    for fill in ("cross", "mid"):
        cfg.FILL = fill
        led = engine.run_book(combined, arm="hold")
        s = xt._stats(led)
        core_led = led.filter(pl.col("ticker").is_in(PAIR))
        ov_led = led.filter(~pl.col("ticker").is_in(PAIR))
        mo = _monthly(core_led).join(_monthly(ov_led), on="m", how="inner", suffix="_ov")
        corr = float(pl.DataFrame(mo).select(pl.corr("pnl", "pnl_ov"))[0, 0])
        out[fill] = {"s": s, "led": led, "corr": corr,
                     "core_pnl": float(core_led["pnl"].sum()),
                     "ov_pnl": float(ov_led["pnl"].sum()),
                     "core_n": core_led.height, "ov_n": ov_led.height}
        print(f"  fill={fill}: {s['n']} trades, pnl ${s['pnl']:,.0f}, Sharpe {s['sharpe']:.2f} "
              f"(core ${out[fill]['core_pnl']:,.0f} / overlay ${out[fill]['ov_pnl']:,.0f}, "
              f"sleeve corr {corr:.2f})")
    cfg.FILL = "cross"
    out["cross"]["led"].write_csv(cfg.RESULTS_ROOT / "xsec_putspread_trades_v11.csv")

    L = ["# v1.1 candidate — pair-core + non-pair overlay (I2, ex-ante design)", "",
         f"_core: SPY+QQQ every weekly date unconditionally; overlay: frozen top-2 walk on universe"
         f" minus pair; ONE engine pass (shared concurrent margin cap) · generated {dt.date.today()}_",
         "",
         "> Carries fresh multiplicity debt (§8.6): a candidate for the §7 protocol, not a v1.0 result.",
         "",
         "Reference: frozen v1.0 cross **0.66** / mid **0.93**; fixed pair cross 0.67 / mid 0.77.",
         "",
         "| fill | trades | pnl | Sharpe(mo) | maxDD | win | core P&L | overlay P&L | sleeve corr | "
         + " | ".join(f"{lo}–{hi}" for lo, hi in ERAS) + " |",
         "| --- | --- | --- | --- | --- | --- | --- | --- | --- | " + " | ".join("---" for _ in ERAS) + " |"]
    for fill in ("cross", "mid"):
        s = out[fill]["s"]
        eras = " | ".join(f"{s[str(lo)]:.2f}" for lo, _ in ERAS)
        L.append(f"| {fill} | {s['n']} | ${s['pnl']:,.0f} | **{s['sharpe']:.2f}** | ${s['maxdd']:,.0f} "
                 f"| {s['win']*100:.0f}% | ${out[fill]['core_pnl']:,.0f} | ${out[fill]['ov_pnl']:,.0f} "
                 f"| {out[fill]['corr']:.2f} | {eras} |")
    L += ["", "## By ticker (cross fills)", "", "| ticker | n | pnl |", "| --- | --- | --- |"]
    by_t = out["cross"]["led"].group_by("ticker").agg(n=pl.len(), pnl=pl.col("pnl").sum()).sort(
        "pnl", descending=True)
    for r in by_t.iter_rows(named=True):
        L.append(f"| {r['ticker']} | {r['n']} | ${r['pnl']:,.0f} |")
    OUT_MD.write_text("\n".join(L) + "\n")
    print(f"-> {OUT_MD}")


if __name__ == "__main__":
    main()
