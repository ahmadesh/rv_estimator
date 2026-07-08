"""Split cadence, ASYMMETRIC exclusion: Thursday excludes that week's Monday pick; Monday is free.

Variant of `xsec_putspread_split_excl.py`. There the exclusion ran both ways (each entry skips the
previous entry's pick). Here only Thursday defers to Monday:

  * Monday: top-1 richest tradeable name, NO exclusion (may repeat last Thursday's name).
  * Thursday: top-1 richest tradeable name, but SKIP the name Monday just opened this week.

Rationale: the symmetric rule fired on 36% of dates and cost ~0.1 Sharpe by forcing Monday off the
richest name too. Monday was the strong day; keep it unconstrained and only diversify the Thursday
add-on away from the already-open Monday name.

Everything else is the frozen book. Selection is still sequential (Thursday depends on Monday), so we
walk the merged Mon+Thu date stream carrying the current week's Monday pick.

Run:  .venv/bin/python -m strategy_backtest.experiments.xsec_putspread_split_thuexcl
Writes results/xsec_putspread_split_thuexcl_report.md (+ cross-fill ledger).
"""

from __future__ import annotations

import datetime as dt

import polars as pl

from strategy_backtest.backtest import engine
from strategy_backtest.backtest import config as cfg
from strategy_backtest.experiments import xsec_putspread_dow as dow
from strategy_backtest.experiments import xsec_putspread_topk as base
from strategy_backtest.experiments.xsec_putspread_split_excl import _openable, _run


def sequential_select_thuonly(p: pl.DataFrame, cal: pl.DataFrame) -> tuple[pl.DataFrame, dict]:
    mon_dates = dow._cohort_dates(cal, 1).with_columns(slot=pl.lit("mon"))
    thu_dates = dow._cohort_dates(cal, 4).with_columns(slot=pl.lit("thu"))
    entry = pl.concat([mon_dates, thu_dates]).sort("date")
    pw = p.join(entry, on="date", how="inner")
    pw = pw.join(pw.group_by("date").agg(n=pl.len()), on="date").filter(
        pl.col("n") >= base.MIN_NAMES_XS)
    pw = pw.filter(pl.col("score") > base.MIN_SCORE)
    pw = pw.with_columns(rk=pl.col("score").rank("ordinal", descending=True).over("date"))

    picks: list[dict] = []
    mon_pick: str | None = None       # this week's Monday pick (the only thing Thursday excludes)
    n_dates = n_excl_bound = n_empty = 0
    for (_d,), sub in pw.sort("date", "rk").group_by("date", maintain_order=True):
        n_dates += 1
        slot = sub["slot"][0]
        exclude = mon_pick if slot == "thu" else None
        chosen, skipped = None, False
        for r in sub.iter_rows(named=True):
            if exclude is not None and r["ticker"] == exclude and not skipped:
                skipped = True
                continue
            if _openable(r["ticker"], r["date"]):
                chosen = r
                break
        if skipped and chosen is not None:
            n_excl_bound += 1
        if chosen is None:
            n_empty += 1
            if slot == "mon":
                mon_pick = None       # empty Monday => nothing for Thursday to exclude
            continue
        picks.append(chosen)
        if slot == "mon":
            mon_pick = chosen["ticker"]
    diag = {"entry_dates": n_dates, "excl_bound": n_excl_bound, "empty_dates": n_empty}
    return pl.DataFrame(picks), diag


def main() -> None:
    p = dow._base_panel()
    cal = p.select("date").unique().sort("date")

    sel, diag = sequential_select_thuonly(p, cal)
    cand = dow._project(sel)
    print(f"entry dates {diag['entry_dates']}, Thu-exclusion bit on {diag['excl_bound']}, "
          f"empty {diag['empty_dates']}, picks {sel.height}")

    arms = _run(cand)
    for fill in ("cross", "mid"):
        s = arms[fill]["s"]
        print(f"  {fill}: {s['n']} trades, ${s['pnl']:,.0f}, Sharpe {s['sharpe']:.2f}, "
              f"maxDD ${s['maxdd']:,.0f}")
    arms["led"].write_csv(cfg.RESULTS_ROOT / "xsec_putspread_split_thuexcl_trades.csv")

    era_hdr = " | ".join(f"{lo}–{hi}" for lo, hi in base.ERAS)
    lines = [
        "# Split cadence + THURSDAY-ONLY exclusion — Mon free, Thu skips that week's Monday name",
        "",
        f"_Monday picks the richest tradeable name with no constraint; Thursday picks the richest "
        f"tradeable name EXCEPT the one Monday opened this week. Frozen book otherwise. "
        f"NAV ${cfg.NAV/1e6:.0f}M, b={cfg.RISK_BUDGET} · generated {dt.date.today()}_",
        "",
        f"_Diagnostics: {diag['entry_dates']} entry dates; the Thursday exclusion changed the pick on "
        f"{diag['excl_bound']} of them; {diag['empty_dates']} dates opened nothing._",
        "",
        f"| fill | trades | pnl | Sharpe(mo) | maxDD | win | {era_hdr} |",
        "| --- | --- | --- | --- | --- | --- | " + " | ".join("---" for _ in base.ERAS) + " |",
    ]
    for fill in ("cross", "mid"):
        s = arms[fill]["s"]
        eras = " | ".join(f"{s[str(lo)]:.2f}" for lo, _ in base.ERAS)
        lines.append(f"| {fill} | {s['n']} | ${s['pnl']:,.0f} | **{s['sharpe']:.2f}** | "
                     f"${s['maxdd']:,.0f} | {s['win']*100:.0f}% | {eras} |")
    lines += ["",
              "### Reference (prior experiments, same NAV/b)",
              "",
              "| arm | Sharpe cross | Sharpe mid | maxDD cross |",
              "| --- | --- | --- | --- |",
              "| Mon top-2 (both on Monday) | 0.78 | 1.04 | $433k |",
              "| split, no exclusion | 0.75 | 1.01 | $571k |",
              "| split + symmetric exclusion | 0.67 | 0.94 | $449k |",
              "| roll5 top-2 (frozen baseline) | 0.66 | 0.93 | $443k |",
              ""]
    out = cfg.RESULTS_ROOT / "xsec_putspread_split_thuexcl_report.md"
    out.write_text("\n".join(lines) + "\n")
    print(f"-> {out}")


if __name__ == "__main__":
    main()
