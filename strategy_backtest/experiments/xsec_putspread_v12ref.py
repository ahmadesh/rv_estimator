"""v1.2 combined confirmation run — fixed-Monday cadence + OI-cap 0.25 sizing.

Pre-registered in `conclusion/LIVE_DEPLOYMENT_SPEC.md` §4.1: the two v1.2 changes vs the frozen
v1.0 book (Monday entry from the cadence study; the v1.1a OI cap) were each backtested separately
but never together. This runs the exact combined configuration ONCE, both fill bounds. It is a
confirmation run, not a tuning run — no parameter may change in response to it; abort threshold
is cross Sharpe < 0.66 (the v1.0 baseline).

Composition (nothing new):
  - cohorts/selection: `xsec_putspread_dow.build_candidates(1)` — fixed Monday with holiday
    fallback, otherwise the frozen score/gate/tradeable-walk verbatim;
  - sizing cap: `xsec_putspread_oicap`'s rule verbatim — contracts ≤ 0.25 × min(leg OI) at entry,
    applied by wrapping `engine._open_candidate`; candidates are built BEFORE patching, exactly
    like the oicap run, so the tradeable-walk is identical to the published v1.1a methodology.
    (The G7 wing-OI ≥ 10 floor means the 0.25 cap can never round below 1 contract, so the cap
    cannot create skips the walk should have absorbed.)

Run:  .venv/bin/python -m strategy_backtest.experiments.xsec_putspread_v12ref
Writes results/xsec_putspread_v12ref.md (+ cross/mid trade ledgers).
"""

from __future__ import annotations

import datetime as dt
import os

# Reproduce the frozen run's knobs before importing the base module (it reads these at import).
os.environ.setdefault("XS_DATA_ROOT", "strategy_backtest/data_wide")
os.environ.setdefault("XS_TOPK", "2")
os.environ.setdefault("XS_TRADEABLE", "1")
os.environ.setdefault("XS_MIN_SCORE", "0.0")

from strategy_backtest.backtest import chains, engine
from strategy_backtest.backtest import config as cfg
from strategy_backtest.experiments import xsec_putspread_topk as base
from strategy_backtest.experiments import xsec_putspread_dow as dow

OI_FRAC = 0.25
MONDAY = 1
OUT_MD = cfg.RESULTS_ROOT / "xsec_putspread_v12ref.md"

_orig_open = engine._open_candidate


def _capped_open(row: dict):
    c = _orig_open(row)
    if c is None:
        return c
    ch = chains.locate_expiry(row["ticker"], row["date"])
    ois = []
    for lg in c["opened"]["legs"]:
        q = chains.leg_quote_from_chain(ch, lg.strike, lg.right)
        if q is None or q.get("oi") is None:
            return None
        ois.append(float(q["oi"]))
    c["n_raw"] = min(c["n_raw"], OI_FRAC * min(ois))
    if c["n_raw"] < 0.5:                      # rounds to zero contracts — not tradeable at this size
        return None
    return c


def main() -> None:
    cfg.FILL = "cross"
    cand = dow.build_candidates(MONDAY)
    cohorts = cand["date"].n_unique()
    print(f"candidates: {cand.height}, Monday cohorts: {cohorts}")

    engine._open_candidate = _capped_open
    stats = {}
    try:
        for fill in ("cross", "mid"):
            cfg.FILL = fill
            led = engine.run_book(cand, arm="hold")
            led.write_csv(cfg.RESULTS_ROOT / f"xsec_putspread_v12ref_trades_{fill}.csv")
            s = base._stats(led)
            stats[fill] = s
            print(f"   {fill}: {s['n']} trades, pnl ${s['pnl']:,.0f}, Sharpe(mo) {s['sharpe']:.2f}, "
                  f"maxDD ${s['maxdd']:,.0f}, win {s['win']*100:.0f}%, "
                  f"mean margin ${s['mean_margin']:,.0f}")
    finally:
        engine._open_candidate = _orig_open
        cfg.FILL = "cross"

    era_hdr = " | ".join(f"{lo}–{hi}" for lo, hi in base.ERAS)
    L = [
        "# v1.2 combined confirmation run — Monday cadence + OI-cap 0.25",
        "",
        f"_Pre-registered in `conclusion/LIVE_DEPLOYMENT_SPEC.md` §4.1 · frozen machinery, cadence"
        f" and sizing-cap changed together, nothing else · TOPK={base.TOP_K},"
        f" TRADEABLE={int(base.TRADEABLE_RANK)}, MIN_SCORE={base.MIN_SCORE},"
        f" NAV ${cfg.NAV/1e6:.0f}M, b={cfg.RISK_BUDGET}, OI_FRAC={OI_FRAC}"
        f" · generated {dt.date.today()}_",
        "",
        f"| fill | cohorts | trades | pnl | Sharpe(mo) | maxDD | win | mean margin/trade | {era_hdr} |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | "
        + " | ".join("---" for _ in base.ERAS) + " |",
    ]
    for fill in ("cross", "mid"):
        s = stats[fill]
        eras = " | ".join(f"{s[str(lo)]:.2f}" for lo, _ in base.ERAS)
        L.append(f"| {fill} | {cohorts} | {s['n']} | ${s['pnl']:,.0f} | **{s['sharpe']:.2f}** | "
                 f"${s['maxdd']:,.0f} | {s['win']*100:.0f}% | ${s['mean_margin']:,.0f} | {eras} |")
    L += ["",
          "Reference points: v1.0 frozen 0.66 cross / 0.93 mid; OI-cap-only 0.89 / 1.06; "
          "Monday-only 0.78 / 1.04. Abort threshold (pre-registered): cross < 0.66.",
          "",
          "Ledgers: `xsec_putspread_v12ref_trades_{cross,mid}.csv`."]
    OUT_MD.write_text("\n".join(L) + "\n")
    print(f"-> {OUT_MD}")


if __name__ == "__main__":
    main()
