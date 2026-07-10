"""Daily mark-to-market re-marking of the frozen book (hole-dig A3).

Spec caveat §6.2: the frozen Sharpe/maxDD book P&L at REALIZATION (exit date) — a 30-DTE spread
sold before a crash shows no loss until its expiry. This re-marks every frozen trade daily at the
chain MID and rebuilds the book's true MTM path:

    per trade, per day t in (entry, exit):  P_t = contracts·100·(credit − S_t) − entry cost,
    where S_t = short_put_mid − wing_put_mid off that day's chain (ORATS expiry_slice; missing
    session/strike carries the last mark forward). The exit-day increment forces P_T to the
    ledger's realized P&L, so total P&L is identical to the frozen headline by construction —
    only the PATH (and hence monthly Sharpe, maxDD) changes.

Writes results/frozen_mtm_daily.csv (date, mtm_pnl, realized_pnl) + results/frozen_mtm.md.

Run:  .venv/bin/python -m strategy_backtest.experiments.frozen_mtm
"""

from __future__ import annotations

import datetime as dt
import math
from collections import defaultdict

import numpy as np
import polars as pl

from strategy_backtest.backtest import chains
from strategy_backtest.backtest import config as cfg

LEDGER = cfg.SB_ROOT / "conclusion" / "frozen_run_trades.csv"
FEATURES = cfg.SB_ROOT / "data_wide" / "features.parquet"
OUT_CSV = cfg.RESULTS_ROOT / "frozen_mtm_daily.csv"
OUT_MD = cfg.RESULTS_ROOT / "frozen_mtm.md"
ERAS = [(2010, 2013), (2014, 2017), (2018, 2021), (2022, 2026)]


def spread_mid(ticker: str, d: dt.date, expiry: dt.date, short_k: float, wing_k: float) -> float | None:
    ch = chains.expiry_slice(ticker, d, expiry)
    if ch is None:
        return None
    sm = ch.df.filter(pl.col("strike") == short_k)
    wm = ch.df.filter(pl.col("strike") == wing_k)
    if sm.is_empty() or wm.is_empty():
        return None
    s, w = sm["pmid"][0], wm["pmid"][0]
    if s is None or w is None or not (s > 0):
        return None
    return float(s) - float(w)


def sharpe_monthly(daily: pl.DataFrame, col: str) -> tuple[float, float, pl.DataFrame]:
    mo = daily.group_by(pl.col("date").dt.truncate("1mo").alias("m")).agg(
        pl.col(col).sum()).sort("m")
    r = mo[col].to_numpy()
    sr = float(r.mean() / r.std(ddof=1) * math.sqrt(12))
    eq = daily[col].to_numpy().cumsum()
    mdd = float(np.max(np.maximum.accumulate(eq) - eq))
    return sr, mdd, mo


def main() -> None:
    led = pl.read_csv(LEDGER, try_parse_dates=True).sort("ticker", "entry_date")
    caldates = (pl.read_parquet(FEATURES, columns=["ticker", "date"])
                .filter(pl.col("ticker") == "SPY")["date"].sort().to_list())
    cal = {d: i for i, d in enumerate(caldates)}
    print(f"{led.height} trades, {len(caldates)} calendar days")

    mtm = defaultdict(float)          # date -> book MTM increment
    realized = defaultdict(float)     # date -> realized (exit-booked) pnl
    skipped = 0
    for t in led.iter_rows(named=True):
        e, x = t["entry_date"], t["exit_date"]
        realized[x] += t["pnl"]
        if e not in cal:              # entry off the SPY calendar (shouldn't happen)
            mtm[x] += t["pnl"]
            skipped += 1
            continue
        mult = t["contracts"] * 100.0
        p_prev = 0.0
        i = cal[e]
        while i < len(caldates) and caldates[i] < x:
            d = caldates[i]
            s = spread_mid(t["ticker"], d, t["expiry"], t["short_strike"], t["wing_strike"])
            if s is not None:
                p = mult * (t["credit"] - s) - t["cost"]
                mtm[d] += p - p_prev
                p_prev = p
            i += 1
        mtm[x] += t["pnl"] - p_prev   # settle to the ledger's realized number

    days = sorted(set(mtm) | set(realized))
    daily = pl.DataFrame({
        "date": days,
        "mtm_pnl": [mtm.get(d, 0.0) for d in days],
        "realized_pnl": [realized.get(d, 0.0) for d in days],
    })
    daily.write_csv(OUT_CSV)

    sr_m, dd_m, mo_m = sharpe_monthly(daily, "mtm_pnl")
    sr_r, dd_r, _ = sharpe_monthly(daily, "realized_pnl")
    # worst months and daily tails under MTM
    mo_m = mo_m.rename({"mtm_pnl": "pnl"}).sort("pnl")
    worst = [f"{r['m'].strftime('%Y-%m')} ${r['pnl']:,.0f}" for r in mo_m.head(5).iter_rows(named=True)]
    dtail = np.percentile(daily["mtm_pnl"].to_numpy(), [0.5, 1, 5])

    L = ["# True mark-to-market path of the frozen book (hole-dig A3)", "",
         f"_daily MID re-marks of all {led.height} frozen trades (cross entry, ledger-realized totals"
         f" preserved) · generated {dt.date.today()}_", "",
         "| basis | Sharpe (monthly) | maxDD (daily path) |",
         "| --- | --- | --- |",
         f"| realization-dated (the frozen headline basis) | {sr_r:.2f} | ${dd_r:,.0f} |",
         f"| **true MTM** | **{sr_m:.2f}** | **${dd_m:,.0f}** |", "",
         f"- worst MTM months: {'; '.join(worst)}",
         f"- MTM daily P&L tails: p0.5 ${dtail[0]:,.0f} · p1 ${dtail[1]:,.0f} · p5 ${dtail[2]:,.0f}",
         f"- ({skipped} trades booked at exit only — entry off calendar)", "",
         "Total P&L is identical to the frozen headline by construction; only the path differs.",
         "Era Sharpes (MTM): " + " · ".join(
             f"{lo}–{hi}: "
             + f"{_era_sr(daily, lo, hi):.2f}" for lo, hi in ERAS), ""]
    OUT_MD.write_text("\n".join(L) + "\n")
    print(f"MTM Sharpe {sr_m:.2f} maxDD ${dd_m:,.0f}  |  realized Sharpe {sr_r:.2f} maxDD ${dd_r:,.0f}")
    print(f"-> {OUT_MD}")


def _era_sr(daily: pl.DataFrame, lo: int, hi: int) -> float:
    mo = (daily.filter(pl.col("date").dt.year().is_between(lo, hi))
          .group_by(pl.col("date").dt.truncate("1mo")).agg(pl.col("mtm_pnl").sum()))
    r = mo["mtm_pnl"].to_numpy()
    return float(r.mean() / r.std(ddof=1) * math.sqrt(12)) if len(r) > 6 else float("nan")


if __name__ == "__main__":
    main()
