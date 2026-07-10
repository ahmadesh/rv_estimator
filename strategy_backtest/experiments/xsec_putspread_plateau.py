"""Robustness plateau map around the frozen config (hole-dig A4).

The frozen spec's §6.1 admits its knobs (0.25Δ/0.10Δ, ~30 DTE, score>0) were chosen on the same
sample it reports, but never measures how sharp that selection is. This driver re-runs the ENTIRE
frozen book at each one-at-a-time neighbor of the frozen config:

    SHORT_DELTA  0.25 -> {0.20, 0.30}
    WING_DELTA   0.10 -> {0.05, 0.15}
    TARGET_DTE   30 [25,45] -> {21 [15,35], 45 [35,60]}
    XS_MIN_SCORE 0.0 -> {-0.10, +0.10}

Read: if the frozen cell sits on a PLATEAU (neighbors within ~0.1 Sharpe), the config is robust
and the multiplicity haircut is modest; if it is a SPIKE, the headline is a selected maximum and
the honest expectation is the neighborhood mean, not the peak.

Single process (chain caches stay warm across variants). ~6 min.
Run:  XS_DATA_ROOT=strategy_backtest/data_wide XS_TOPK=2 XS_TRADEABLE=1 XS_MIN_SCORE=0.0 \
      .venv/bin/python -m strategy_backtest.experiments.xsec_putspread_plateau
"""

from __future__ import annotations

import datetime as dt

from strategy_backtest.backtest import chains, engine
from strategy_backtest.backtest import config as cfg
from strategy_backtest.experiments import xsec_putspread_topk as xt

OUT_MD = cfg.RESULTS_ROOT / "xsec_putspread_plateau.md"

FROZEN = dict(short_delta=0.25, wing_delta=0.10, dte=(30, (25, 45)), min_score=0.0)
VARIANTS: list[tuple[str, dict]] = [
    ("frozen", {}),
    ("shortΔ 0.20", dict(short_delta=0.20)),
    ("shortΔ 0.30", dict(short_delta=0.30)),
    ("wingΔ 0.05", dict(wing_delta=0.05)),
    ("wingΔ 0.15", dict(wing_delta=0.15)),
    ("DTE 21 [15,35]", dict(dte=(21, (15, 35)))),
    ("DTE 45 [35,60]", dict(dte=(45, (35, 60)))),
    ("gate −0.10", dict(min_score=-0.10)),
    ("gate +0.10", dict(min_score=+0.10)),
]


def apply(over: dict) -> None:
    v = {**FROZEN, **over}
    cfg.SHORT_DELTA = v["short_delta"]
    cfg.WING_DELTA = v["wing_delta"]
    cfg.TARGET_DTE, cfg.DTE_TOLERANCE = v["dte"]
    # locate_expiry bound its defaults at import — re-point them at the new knobs
    chains.locate_expiry.__defaults__ = (cfg.TARGET_DTE, cfg.DTE_TOLERANCE)
    xt.MIN_SCORE = v["min_score"]


def main() -> None:
    results = []
    for name, over in VARIANTS:
        apply(over)
        cand = xt.build_candidates()
        row = {"name": name, "n_cand": cand.height}
        for fill in ("cross", "mid"):
            cfg.FILL = fill
            led = engine.run_book(cand, arm="hold")
            s = xt._stats(led)
            row[f"{fill}_sharpe"] = s["sharpe"]
            row[f"{fill}_pnl"] = s["pnl"]
            row[f"{fill}_maxdd"] = s["maxdd"]
            row[f"{fill}_n"] = s["n"]
        results.append(row)
        print(f"{name:16s} cross {row['cross_sharpe']:.2f} (${row['cross_pnl']:,.0f}) "
              f"mid {row['mid_sharpe']:.2f} (${row['mid_pnl']:,.0f}) trades {row['cross_n']}")

    L = ["# Robustness plateau map around the frozen config (hole-dig A4)", "",
         f"_one-at-a-time neighbors, full frozen machinery re-run per cell · generated {dt.date.today()}_",
         "",
         "| variant | trades | cross Sharpe | cross P&L | cross maxDD | mid Sharpe | mid P&L |",
         "| --- | --- | --- | --- | --- | --- | --- |"]
    for r in results:
        L.append(f"| {r['name']} | {r['cross_n']} | **{r['cross_sharpe']:.2f}** "
                 f"| ${r['cross_pnl']:,.0f} | ${r['cross_maxdd']:,.0f} "
                 f"| **{r['mid_sharpe']:.2f}** | ${r['mid_pnl']:,.0f} |")
    neigh = [r for r in results if r["name"] != "frozen"]
    for fill in ("cross", "mid"):
        vals = [r[f"{fill}_sharpe"] for r in neigh]
        f0 = next(r for r in results if r["name"] == "frozen")[f"{fill}_sharpe"]
        L += ["", f"**{fill}**: frozen {f0:.2f} · neighborhood mean {sum(vals)/len(vals):.2f} "
              f"· min {min(vals):.2f} · max {max(vals):.2f}"]
    OUT_MD.write_text("\n".join(L) + "\n")
    print(f"-> {OUT_MD}")


if __name__ == "__main__":
    main()
