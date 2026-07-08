"""Split-cadence experiment: 1 spread on Monday + 1 spread on Thursday (still 2 spreads/week).

Motivation: the frozen book opens both weekly spreads on a SINGLE entry day (top-2 of that day's
cohort). This asks whether spreading the same two-spread weekly budget across TWO entry days —
top-1 richest tradeable name on Monday, top-1 again on Thursday — improves risk-adjusted return by
diversifying entry timing (different spot, different 30-DTE window, staggered expiries) without
changing gross exposure.

Everything except WHICH dates/how-many-per-date is identical to the frozen book. We reuse the frozen
tradeable-walk: since it keeps names in score-rank order, the top-1 pick for a date is simply the
first name it kept, so one k=2 walk per weekday yields BOTH the split arm's top-1 and the single-day
top-2 comparators for free.

Arms reported (all: universe/score/gate/structure/sizing/fills identical to frozen):
  * split      : Mon top-1  +  Thu top-1        (2 spreads/week, 2 entry days)   <- the new idea
  * Mon top-2  : Mon top-2                       (2 spreads/week, 1 entry day)
  * Thu top-2  : Thu top-2                       (2 spreads/week, 1 entry day)
  * roll5 top-2: frozen every-5th-day baseline   (for reference; from the dow report)

Run:  .venv/bin/python -m strategy_backtest.experiments.xsec_putspread_split
Writes results/xsec_putspread_split_report.md (+ split cross-fill ledger).
"""

from __future__ import annotations

import datetime as dt

import polars as pl

from strategy_backtest.backtest import engine
from strategy_backtest.backtest import config as cfg
from strategy_backtest.experiments import xsec_putspread_dow as dow
from strategy_backtest.experiments import xsec_putspread_topk as base


def _walk(p: pl.DataFrame, cal: pl.DataFrame, weekday: int) -> pl.DataFrame:
    """Frozen tradeable-walk (top-2, rk preserved) for one fixed weekday's cohorts."""
    wk = dow._cohort_dates(cal, weekday)
    pw = p.join(wk, on="date", how="inner")
    pw = pw.join(pw.group_by("date").agg(n=pl.len()), on="date").filter(
        pl.col("n") >= base.MIN_NAMES_XS)
    pw = pw.filter(pl.col("score") > base.MIN_SCORE)
    pw = pw.with_columns(rk=pl.col("score").rank("ordinal", descending=True).over("date"))
    return base._select_tradeable(pw)          # first up-to-2 tradeable per date, in rk order


def _top1(sel: pl.DataFrame) -> pl.DataFrame:
    """The single richest tradeable name per date (first kept row of the rank-ordered walk)."""
    return sel.sort("date", "rk").group_by("date", maintain_order=True).first()


def _run(cand: pl.DataFrame) -> dict:
    arms = {}
    for fill in ("cross", "mid"):
        cfg.FILL = fill
        led = engine.run_book(cand, arm="hold")
        arms[fill] = {"led": led, "s": base._stats(led)}
    cfg.FILL = "cross"
    return arms


def main() -> None:
    assert base.TOP_K == 2, "walk must keep 2 so we can derive top-1 and top-2"
    p = dow._base_panel()
    cal = p.select("date").unique().sort("date")

    mon_sel = _walk(p, cal, 1)     # Monday cohorts, top-2 tradeable
    thu_sel = _walk(p, cal, 4)     # Thursday cohorts, top-2 tradeable

    split_cand = dow._project(pl.concat([_top1(mon_sel), _top1(thu_sel)]).sort("date", "ticker"))
    mon2_cand = dow._project(mon_sel)
    thu2_cand = dow._project(thu_sel)

    arms = {
        "split (Mon#1 + Thu#1)": _run(split_cand),
        "Mon top-2": _run(mon2_cand),
        "Thu top-2": _run(thu2_cand),
    }
    cands = {"split (Mon#1 + Thu#1)": split_cand, "Mon top-2": mon2_cand, "Thu top-2": thu2_cand}

    for name, a in arms.items():
        for fill in ("cross", "mid"):
            s = a[fill]["s"]
            print(f"{name:24s} {fill}: {s['n']:4d} trades, ${s['pnl']:>11,.0f}, "
                  f"Sharpe {s['sharpe']:.2f}, maxDD ${s['maxdd']:,.0f}")
    arms["split (Mon#1 + Thu#1)"]["cross"]["led"].write_csv(
        cfg.RESULTS_ROOT / "xsec_putspread_split_trades.csv")

    era_hdr = " | ".join(f"{lo}–{hi}" for lo, hi in base.ERAS)
    lines = [
        "# Split-cadence experiment — 1 spread Monday + 1 spread Thursday",
        "",
        f"_Frozen book, 2 spreads/week, varying only entry timing. `split` = top-1 richest tradeable "
        f"name each of Mon & Thu; `Mon/Thu top-2` = both spreads on one day. "
        f"NAV ${cfg.NAV/1e6:.0f}M, b={cfg.RISK_BUDGET} · generated {dt.date.today()}_",
        "",
    ]
    for fill, title in (("cross", "Cross fills (worst case)"), ("mid", "Mid fills (best case)")):
        lines += [f"## {title}", "",
                  f"| arm | entry-days | trades | pnl | Sharpe(mo) | maxDD | win | {era_hdr} |",
                  "| --- | --- | --- | --- | --- | --- | --- | " + " | ".join("---" for _ in base.ERAS) + " |"]
        for name, a in arms.items():
            s = a[fill]["s"]
            ed = cands[name]["date"].n_unique()
            eras = " | ".join(f"{s[str(lo)]:.2f}" for lo, _ in base.ERAS)
            lines.append(f"| {name} | {ed} | {s['n']} | ${s['pnl']:,.0f} | **{s['sharpe']:.2f}** | "
                         f"${s['maxdd']:,.0f} | {s['win']*100:.0f}% | {eras} |")
        lines += ["", "_roll5 top-2 baseline (frozen): cross 0.66 / mid 0.93 — see "
                  "`xsec_putspread_dow_report.md`._", ""]

    out = cfg.RESULTS_ROOT / "xsec_putspread_split_report.md"
    out.write_text("\n".join(lines) + "\n")
    print(f"-> {out}")


if __name__ == "__main__":
    main()
