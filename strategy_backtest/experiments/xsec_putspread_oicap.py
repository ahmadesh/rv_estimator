"""OI-capped sizing variant (improvement I5, born from forensics hole-dig A2).

frozen_forensics.md found 31% of frozen trades are LARGER than the worse leg's resting open
interest (wing p95 ≈ 9.7× OI) — and that bucket nets ≈ −3% of book P&L, while 80% of P&L sits in
trades under 0.25× OI. So the backtest books size that could not have traded, and loses nothing
by refusing it.

This variant keeps the frozen spec identical (selection, structure, fills, margin cap) and adds
ONE sizing rule at entry:  contracts ≤ OI_FRAC × min(short-leg OI, wing OI); a trade whose cap
rounds to zero contracts is skipped. Sweep OI_FRAC ∈ {0.10, 0.25, 0.50, ∞}.

If Sharpe holds (or rises) at 0.25, the capacity-feasible book is at least as good as the
headline and the A2 hole closes with a spec-change candidate for v1.1.

Run:  XS_DATA_ROOT=strategy_backtest/data_wide XS_TOPK=2 XS_TRADEABLE=1 XS_MIN_SCORE=0.0 \
      .venv/bin/python -m strategy_backtest.experiments.xsec_putspread_oicap
"""

from __future__ import annotations

import datetime as dt
import math

import polars as pl

from strategy_backtest.backtest import chains, engine
from strategy_backtest.backtest import config as cfg
from strategy_backtest.experiments import xsec_putspread_topk as xt

OUT_MD = cfg.RESULTS_ROOT / "xsec_putspread_oicap.md"
FRACS = [0.10, 0.25, 0.50, float("inf")]

_FRAC = {"v": float("inf")}
_orig_open = engine._open_candidate


def _capped_open(row: dict):
    c = _orig_open(row)
    if c is None or not math.isfinite(_FRAC["v"]):
        return c
    ch = chains.locate_expiry(row["ticker"], row["date"])
    ois = []
    for lg in c["opened"]["legs"]:
        q = chains.leg_quote_from_chain(ch, lg.strike, lg.right)
        if q is None or q.get("oi") is None:
            return None
        ois.append(float(q["oi"]))
    cap = _FRAC["v"] * min(ois)
    c["n_raw"] = min(c["n_raw"], cap)
    if c["n_raw"] < 0.5:                      # rounds to zero contracts — not tradeable at this size
        return None
    return c


def main() -> None:
    cfg.FILL = "cross"
    cand = xt.build_candidates()
    print(f"candidates: {cand.height}")

    engine._open_candidate = _capped_open
    rows = []
    try:
        for frac in FRACS:
            _FRAC["v"] = frac
            row = {"frac": frac}
            for fill in ("cross", "mid"):
                cfg.FILL = fill
                led = engine.run_book(cand, arm="hold")
                s = xt._stats(led)
                row[f"{fill}_sharpe"] = s["sharpe"]
                row[f"{fill}_pnl"] = s["pnl"]
                row[f"{fill}_maxdd"] = s["maxdd"]
                row[f"{fill}_n"] = s["n"]
                row[f"{fill}_margin"] = s["mean_margin"]
            rows.append(row)
            print(f"OI_FRAC={frac}  cross {row['cross_sharpe']:.2f} (${row['cross_pnl']:,.0f}, "
                  f"{row['cross_n']} trades)  mid {row['mid_sharpe']:.2f} (${row['mid_pnl']:,.0f})")
    finally:
        engine._open_candidate = _orig_open

    L = ["# OI-capped sizing (improvement I5 — closes capacity hole A2)", "",
         "_frozen book + one rule: contracts ≤ OI_FRAC × min(leg OI) at entry; zero-contract trades"
         f" skipped · generated {dt.date.today()}_", "",
         "| OI_FRAC | trades | cross Sharpe | cross P&L | cross maxDD | mean margin/trade "
         "| mid Sharpe | mid P&L |",
         "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for r in rows:
        tag = "∞ (frozen)" if not math.isfinite(r["frac"]) else f"{r['frac']:.2f}"
        L.append(f"| {tag} | {r['cross_n']} | **{r['cross_sharpe']:.2f}** | ${r['cross_pnl']:,.0f} "
                 f"| ${r['cross_maxdd']:,.0f} | ${r['cross_margin']:,.0f} "
                 f"| **{r['mid_sharpe']:.2f}** | ${r['mid_pnl']:,.0f} |")
    OUT_MD.write_text("\n".join(L) + "\n")
    print(f"-> {OUT_MD}")


if __name__ == "__main__":
    main()
