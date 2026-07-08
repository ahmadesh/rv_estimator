"""Split cadence WITH prior-pick exclusion: Mon top-1 + Thu top-1, but each entry day skips the
name the previous entry day just opened.

Rationale: in `xsec_putspread_split.py` the two entry days pick independently, so Thursday can
re-short the same name Monday already holds — concentrating single-name risk. That book had a WORSE
maxDD than putting both spreads on Monday. This variant tests whether forbidding the immediate
repeat (Thursday excludes Monday's pick; Monday excludes last Thursday's pick) recovers the
diversification that name-overlap was eating.

Because the pick on day N now depends on the pick on day N-1, selection is sequential: we merge the
Mon & Thu cohort dates into one chronological stream and walk it, carrying `prev_pick`. Each date we
rank its cohort, walk down the tradeable list skipping `prev_pick`, and keep the first name that
opens. Everything else (universe/score/gate/structure/sizing/fills) is the frozen book.

Run:  .venv/bin/python -m strategy_backtest.experiments.xsec_putspread_split_excl
Writes results/xsec_putspread_split_excl_report.md (+ cross-fill ledger).
"""

from __future__ import annotations

import datetime as dt

import polars as pl

from strategy_backtest.backtest import chains, marks, structures, engine
from strategy_backtest.backtest import config as cfg
from strategy_backtest.backtest.contracts import EntryContext
from strategy_backtest.experiments import xsec_putspread_dow as dow
from strategy_backtest.experiments import xsec_putspread_topk as base


def _openable(tk: str, d) -> bool:
    """Point-in-time openability on the entry-day chain (identical to base._select_tradeable)."""
    ch = chains.locate_expiry(tk, d)
    if ch is None:
        return False
    ctx = EntryContext(ticker=tk, group=base.GROUP[tk], entry_date=d, expiry=ch.expiry,
                       horizon=22, spot=ch.spot, signal={})
    legs = structures.put_credit_spread_legs(ch, ctx)
    if not legs:
        return False
    try:
        marks.open_trade(ch, legs, ctx)
        return True
    except marks.Rejected:
        return False


def sequential_select(p: pl.DataFrame, cal: pl.DataFrame, days=(1, 4)) -> tuple[pl.DataFrame, dict]:
    entry_dates = pl.concat([dow._cohort_dates(cal, wd) for wd in days]).unique().sort("date")
    pw = p.join(entry_dates, on="date", how="inner")
    pw = pw.join(pw.group_by("date").agg(n=pl.len()), on="date").filter(
        pl.col("n") >= base.MIN_NAMES_XS)
    pw = pw.filter(pl.col("score") > base.MIN_SCORE)
    pw = pw.with_columns(rk=pl.col("score").rank("ordinal", descending=True).over("date"))

    picks: list[dict] = []
    prev: str | None = None
    n_dates = 0
    n_excl_bound = 0            # times the top tradeable name WAS the excluded prev (rule bit)
    n_empty = 0                 # dates where nothing opened at all
    for (_d,), sub in pw.sort("date", "rk").group_by("date", maintain_order=True):
        n_dates += 1
        chosen = None
        skipped_prev = False
        for r in sub.iter_rows(named=True):
            if r["ticker"] == prev and not skipped_prev:
                skipped_prev = True          # skip exactly the previous entry's pick
                continue
            if _openable(r["ticker"], r["date"]):
                # did excluding prev change the choice? only if prev would have been openable & first
                chosen = r
                break
        if skipped_prev and chosen is not None:
            n_excl_bound += 1
        if chosen is None:
            n_empty += 1
            continue
        picks.append(chosen)
        prev = chosen["ticker"]
    diag = {"entry_dates": n_dates, "excl_bound": n_excl_bound, "empty_dates": n_empty}
    return pl.DataFrame(picks), diag


def _run(cand: pl.DataFrame) -> dict:
    arms = {}
    for fill in ("cross", "mid"):
        cfg.FILL = fill
        led = engine.run_book(cand, arm="hold")
        arms[fill] = {"s": base._stats(led)}
        if fill == "cross":
            arms["led"] = led
    cfg.FILL = "cross"
    return arms


def main() -> None:
    p = dow._base_panel()
    cal = p.select("date").unique().sort("date")

    sel, diag = sequential_select(p, cal, days=(1, 4))
    cand = dow._project(sel)
    print(f"entry dates {diag['entry_dates']}, exclusion bit on {diag['excl_bound']}, "
          f"empty (nothing opened) {diag['empty_dates']}, picks {sel.height}")

    arms = _run(cand)
    for fill in ("cross", "mid"):
        s = arms[fill]["s"]
        print(f"  {fill}: {s['n']} trades, ${s['pnl']:,.0f}, Sharpe {s['sharpe']:.2f}, "
              f"maxDD ${s['maxdd']:,.0f}")
    arms["led"].write_csv(cfg.RESULTS_ROOT / "xsec_putspread_split_excl_trades.csv")

    era_hdr = " | ".join(f"{lo}–{hi}" for lo, hi in base.ERAS)
    lines = [
        "# Split cadence + prior-pick exclusion — Mon top-1 + Thu top-1, no immediate repeat",
        "",
        f"_Each entry day skips the name the previous entry day opened (Thu excludes Mon; Mon excludes "
        f"last Thu). Frozen book otherwise. NAV ${cfg.NAV/1e6:.0f}M, b={cfg.RISK_BUDGET} · "
        f"generated {dt.date.today()}_",
        "",
        f"_Diagnostics: {diag['entry_dates']} entry dates; the exclusion changed the pick on "
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
              "### Reference (from prior experiments, same NAV/b)",
              "",
              "| arm | Sharpe cross | Sharpe mid | maxDD cross |",
              "| --- | --- | --- | --- |",
              "| split, no exclusion (Mon#1+Thu#1) | 0.75 | 1.01 | $571k |",
              "| Mon top-2 (both on Monday) | 0.78 | 1.04 | $433k |",
              "| roll5 top-2 (frozen baseline) | 0.66 | 0.93 | $443k |",
              ""]
    out = cfg.RESULTS_ROOT / "xsec_putspread_split_excl_report.md"
    out.write_text("\n".join(lines) + "\n")
    print(f"-> {out}")


if __name__ == "__main__":
    main()
