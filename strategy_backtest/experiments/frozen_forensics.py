"""Ledger forensics on the frozen put-spread book (hole-digs A2 capacity, A7 stress fills, A8 pins).

Re-queries every frozen trade's entry-day chain (same chains module the engine used) and asks the
three questions the ledger alone can't answer:

  A2  capacity   — contracts vs the OPEN INTEREST of the legs we filtered on (short ≥50, wing ≥10):
                   if the book routinely trades a multiple of the resting OI, both fill bounds are
                   fiction at this size.
  A7  stress     — entry friction (mid credit − cross credit, i.e. the half-spreads paid) by VIX
                   quintile at entry: is the cross bound's cost concentrated exactly in the
                   high-vol entries that drive the P&L?
  A8  settlement — pin risk (settles within ±1% of the short strike), max-loss zone (settle below
                   the wing), ITM settles on dividend payers (early-assignment exposure), and a
                   USO Apr-2020 reverse-split sanity check.

Reads conclusion/frozen_run_trades.csv (cross fills — the frozen ledger).
Writes results/frozen_forensics.md (+ frozen_forensics_trades.parquet with per-trade columns).

Run:  .venv/bin/python -m strategy_backtest.experiments.frozen_forensics
"""

from __future__ import annotations

import datetime as dt

import numpy as np
import polars as pl

from strategy_backtest.backtest import chains
from strategy_backtest.backtest import config as cfg

LEDGER = cfg.SB_ROOT / "conclusion" / "frozen_run_trades.csv"
FEATURES = cfg.SB_ROOT / "data_wide" / "features.parquet"
OUT_MD = cfg.RESULTS_ROOT / "frozen_forensics.md"
OUT_PQ = cfg.RESULTS_ROOT / "frozen_forensics_trades.parquet"

# ETFs with material regular distributions (early-assignment exposure on ITM short puts is really
# about hard-to-borrow/discount effects; for ETFs the practical flag is deep ITM + a distribution).
DIV_PAYERS = {"TLT", "IYR", "XLU", "XLP", "HYG", "EFA", "EEM", "DIA", "SPY", "IWM", "KRE", "XLF"}


def leg_quotes(ticker: str, entry_date: dt.date, expiry: dt.date,
               short_k: float, wing_k: float) -> dict | None:
    ch = chains.expiry_slice(ticker, entry_date, expiry)
    if ch is None:
        return None
    out = {}
    for tag, k in (("short", short_k), ("wing", wing_k)):
        row = ch.df.filter(pl.col("strike") == k)
        if row.is_empty():
            return None
        r = row.row(0, named=True)
        out[f"{tag}_oi"] = float(r["oi_p"]) if r["oi_p"] is not None else float("nan")
        out[f"{tag}_bid"] = float(r["pbid"]) if r["pbid"] is not None else float("nan")
        out[f"{tag}_ask"] = float(r["pask"]) if r["pask"] is not None else float("nan")
    return out


def main() -> None:
    led = pl.read_csv(LEDGER, try_parse_dates=True)
    print(f"ledger: {led.height} trades")

    rows = []
    for t in led.iter_rows(named=True):
        q = leg_quotes(t["ticker"], t["entry_date"], t["expiry"],
                       t["short_strike"], t["wing_strike"])
        rows.append(q or {k: float("nan") for k in
                          ("short_oi", "wing_oi", "short_bid", "short_ask", "wing_bid", "wing_ask")})
    aug = pl.concat([led, pl.DataFrame(rows)], how="horizontal")

    vix = (pl.read_parquet(FEATURES, columns=["ticker", "date", "vix"])
           .filter(pl.col("ticker") == "SPY").select("date", (pl.col("vix") * 100.0).alias("vix")))
    aug = aug.join(vix, left_on="entry_date", right_on="date", how="left")

    aug = aug.with_columns(
        n_over_short_oi=pl.col("contracts") / pl.col("short_oi"),
        n_over_wing_oi=pl.col("contracts") / pl.col("wing_oi"),
        # friction actually paid at entry by crossing: half-spread on each leg, per share
        half_spread=(0.5 * (pl.col("short_ask") - pl.col("short_bid"))
                     + 0.5 * (pl.col("wing_ask") - pl.col("wing_bid"))),
    ).with_columns(
        friction_usd=pl.col("half_spread") * pl.col("contracts") * 100.0,
        mid_credit=pl.col("credit") + pl.col("half_spread"),
        pin=((pl.col("settle_spot") - pl.col("short_strike")).abs()
             / pl.col("short_strike") <= 0.01),
        below_wing=pl.col("settle_spot") < pl.col("wing_strike"),
    )
    aug.write_parquet(OUT_PQ)

    L = ["# Frozen-book ledger forensics (A2 capacity · A7 stress fills · A8 settlement)",
         "", f"_{led.height} trades re-quoted on their entry chains · generated {dt.date.today()}_", ""]

    # ---------------------------------------------------------------- A2 capacity
    ok = aug.filter(pl.col("short_oi").is_finite() & pl.col("wing_oi").is_finite())
    miss = aug.height - ok.height
    L += ["## A2 — contracts vs resting open interest", ""]
    if miss:
        L += [f"_{miss} trades could not be re-quoted (chain row missing) — excluded._", ""]
    for col, leg in (("n_over_short_oi", "short leg"), ("n_over_wing_oi", "wing leg")):
        v = ok[col].to_numpy()
        pct = np.nanpercentile(v, [50, 75, 90, 95, 99])
        L += [f"**{leg}** contracts/OI: median {pct[0]:.2f} · p75 {pct[1]:.2f} · p90 {pct[2]:.2f}"
              f" · p95 {pct[3]:.2f} · p99 {pct[4]:.2f}", ""]
    buckets = [(0.0, 0.1), (0.1, 0.25), (0.25, 0.5), (0.5, 1.0), (1.0, float("inf"))]
    L += ["| contracts/OI (worse leg) | trades | share of trades | P&L | share of P&L |",
          "| --- | --- | --- | --- | --- |"]
    ok = ok.with_columns(worse=pl.max_horizontal("n_over_short_oi", "n_over_wing_oi"))
    tot_pnl = ok["pnl"].sum()
    for lo, hi in buckets:
        b = ok.filter((pl.col("worse") >= lo) & (pl.col("worse") < hi))
        L.append(f"| {lo:g}–{hi:g} | {b.height} | {b.height/ok.height*100:.0f}% "
                 f"| ${b['pnl'].sum():,.0f} | {b['pnl'].sum()/tot_pnl*100:.0f}% |")
    L.append("")

    # ---------------------------------------------------------------- A7 stress fills
    L += ["## A7 — entry friction by VIX quintile at entry", "",
          "friction = the two half-spreads paid crossing at entry (mid credit − cross credit).", "",
          "| VIX quintile | VIX range | trades | mean friction/trade | friction Σ | "
          "friction as % of mid credit | cross P&L Σ |",
          "| --- | --- | --- | --- | --- | --- | --- |"]
    fq = aug.filter(pl.col("vix").is_not_null() & pl.col("friction_usd").is_finite())
    qs = np.nanpercentile(fq["vix"].to_numpy(), [20, 40, 60, 80])
    edges = [-np.inf, *qs, np.inf]
    for i in range(5):
        b = fq.filter((pl.col("vix") > edges[i]) & (pl.col("vix") <= edges[i + 1]))
        fric = b["friction_usd"].sum()
        midcred = (b["mid_credit"] * b["contracts"] * 100).sum()
        L.append(f"| Q{i+1} | {b['vix'].min():.1f}–{b['vix'].max():.1f} | {b.height} "
                 f"| ${fric/max(b.height,1):,.0f} | ${fric:,.0f} "
                 f"| {fric/midcred*100:.1f}% | ${b['pnl'].sum():,.0f} |")
    L.append("")

    # ---------------------------------------------------------------- A8 settlement
    pins = aug.filter(pl.col("pin"))
    deep = aug.filter(pl.col("below_wing"))
    itm = aug.filter(pl.col("breached"))
    itm_div = itm.filter(pl.col("ticker").is_in(sorted(DIV_PAYERS)))
    L += ["## A8 — settlement realism", "",
          f"- settles within ±1% of the short strike (pin/assignment zone): **{pins.height}** trades "
          f"({pins.height/aug.height*100:.1f}%), P&L ${pins['pnl'].sum():,.0f}",
          f"- settles below the wing (max-loss zone): **{deep.height}** trades, "
          f"P&L ${deep['pnl'].sum():,.0f}",
          f"- short strike breached at expiry: **{itm.height}** trades "
          f"({itm.height/aug.height*100:.1f}%), of which **{itm_div.height}** on distribution-paying "
          f"ETFs (early-assignment exposure the intrinsic-settle model ignores)", ""]
    uso = aug.filter((pl.col("ticker") == "USO")
                     & (pl.col("entry_date") >= dt.date(2020, 2, 1))
                     & (pl.col("entry_date") <= dt.date(2020, 6, 30)))
    L += ["### USO around the Apr-2020 1:8 reverse split", ""]
    if uso.is_empty():
        L.append("_no USO trades entered Feb–Jun 2020 (nothing spans the split)._")
    else:
        L += ["| entry | expiry | short K | wing K | entry spot | settle spot | pnl |",
              "| --- | --- | --- | --- | --- | --- | --- |"]
        for r in uso.iter_rows(named=True):
            L.append(f"| {r['entry_date']} | {r['expiry']} | {r['short_strike']} | {r['wing_strike']} "
                     f"| {r['entry_spot']} | {r['settle_spot']} | ${r['pnl']:,.0f} |")
    L.append("")

    OUT_MD.write_text("\n".join(L) + "\n")
    print(f"-> {OUT_MD}")


if __name__ == "__main__":
    main()
