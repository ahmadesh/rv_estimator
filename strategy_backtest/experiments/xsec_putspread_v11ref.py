"""Reference runs for STRATEGY_SPEC_v1.1_DRAFT — the two pre-registered arms.

    v1.1a : frozen v1.0 + OI-cap (contracts ≤ 0.25 × min(short OI, wing OI))
    v1.1b : v1.1a + TARGET_DTE 45 [35, 60]

v1.1a's number exists in `xsec_putspread_oicap.md` (0.25 row); v1.1b's combined cell was never
measured (OI-cap and DTE-45 were each one-at-a-time sweeps). This runs both arms through the
frozen machinery so the draft spec carries its own reproducible reference table. These are the
LAST in-sample numbers before the §7 shadow run; nothing here is tuned further.

Run:  XS_DATA_ROOT=strategy_backtest/data_wide XS_TOPK=2 XS_TRADEABLE=1 XS_MIN_SCORE=0.0 \
      .venv/bin/python -m strategy_backtest.experiments.xsec_putspread_v11ref
"""

from __future__ import annotations

import datetime as dt
import math

from strategy_backtest.backtest import chains, engine
from strategy_backtest.backtest import config as cfg
from strategy_backtest.experiments import xsec_putspread_topk as xt
from strategy_backtest.experiments.xsec_putspread_oicap import _capped_open, _FRAC

OUT_MD = cfg.RESULTS_ROOT / "xsec_putspread_v11ref.md"
ARMS = [
    ("v1.1a  OI-cap 0.25, DTE 30 [25,45]", 0.25, (30, (25, 45))),
    ("v1.1b  OI-cap 0.25, DTE 45 [35,60]", 0.25, (45, (35, 60))),
]


def main() -> None:
    engine._open_candidate = _capped_open
    rows = []
    for name, frac, (dte, tol) in ARMS:
        cfg.TARGET_DTE, cfg.DTE_TOLERANCE = dte, tol
        chains.locate_expiry.__defaults__ = (dte, tol)
        _FRAC["v"] = frac
        cfg.FILL = "cross"
        cand = xt.build_candidates()
        row = {"name": name, "cand": cand.height}
        for fill in ("cross", "mid"):
            cfg.FILL = fill
            led = engine.run_book(cand, arm="hold")
            s = xt._stats(led)
            row[fill] = s
        rows.append(row)
        print(f"{name}: cross {row['cross']['sharpe']:.2f} (${row['cross']['pnl']:,.0f}, "
              f"maxDD ${row['cross']['maxdd']:,.0f})  mid {row['mid']['sharpe']:.2f} "
              f"(${row['mid']['pnl']:,.0f})")
        if name.startswith("v1.1b"):
            led.write_csv(cfg.RESULTS_ROOT / "xsec_putspread_trades_v11b.csv")

    L = ["# v1.1 draft — reference runs (both pre-registered arms)", "",
         f"_frozen machinery + OI-cap 0.25 (a) and + DTE 45 (b) · generated {dt.date.today()}_", "",
         "Frozen v1.0 reference: cross 0.66 / mid 0.93; true-MTM basis 0.55.", "",
         "| arm | trades | cross Sharpe | cross P&L | cross maxDD | mid Sharpe | mid P&L | "
         + " | ".join(f"{lo}–{hi}" for lo, hi in xt.ERAS) + " (cross) |",
         "| --- | --- | --- | --- | --- | --- | --- | " + " | ".join("---" for _ in xt.ERAS) + " |"]
    for r in rows:
        eras = " | ".join(f"{r['cross'][str(lo)]:.2f}" for lo, _ in xt.ERAS)
        L.append(f"| {r['name']} | {r['cross']['n']} | **{r['cross']['sharpe']:.2f}** "
                 f"| ${r['cross']['pnl']:,.0f} | ${r['cross']['maxdd']:,.0f} "
                 f"| **{r['mid']['sharpe']:.2f}** | ${r['mid']['pnl']:,.0f} | {eras} |")
    OUT_MD.write_text("\n".join(L) + "\n")
    print(f"-> {OUT_MD}")


if __name__ == "__main__":
    main()
