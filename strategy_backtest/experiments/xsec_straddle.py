"""Cross-sectional vol RV — long/short delta-hedged straddle book (Stage-B prototype).

Motivated by the 2026-06-11 review (`results/BACKTEST_REVIEW_AND_VERDICT.md`): the EnsembleTopK
cross-sectional VRP *ranking* is era-stable, while the aggregate short-vol book died post-2018.
This backtest trades the ranking market-neutral-ish:

    each week: rank the 10 names by score = log(iv2) - log(rv_hat_cal)   (de-biased, PIT)
        SHORT ~ATM straddles on the K richest   (earn when RV < IV)
        LONG  ~ATM straddles on the K cheapest  (earn when RV > IV)
    equal $vega per name; delta-hedged daily at EOD with the underlying; held to expiry
    (~30 DTE, intrinsic settlement = no exit spread). True daily MTM P&L — option legs marked
    at MID, entry crossed at bid/ask, commissions per leg, hedge friction per share traded.

Honest-risk basis: unlike the put-spread book, the daily series here is mark-to-market, so the
Sharpe/maxDD include intra-trade swings. Short straddles are NOT defined-risk: the daily hedge
bounds delta but not gamma — the report panel includes worst-day / CVaR for exactly that reason.

Run:  .venv/bin/python -m strategy_backtest.experiments.xsec_straddle
Writes results/xsec_straddle_report.md (+ xsec_straddle_daily.csv, xsec_straddle_positions.csv).
"""

from __future__ import annotations

import datetime as dt
import math
import time

import numpy as np
import polars as pl

from strategy_backtest.backtest import chains, pit
from strategy_backtest.backtest import config as cfg

# --------------------------------------------------------------------------- knobs (set once)
K_SIDE = 3                      # names per side (of 10)
ROLL_EVERY = 5                  # trading days between cohorts (weekly)
VEGA_TARGET = 1_000.0           # $ vega per name per cohort (scale-free for Sharpe)
MIN_PERIODS_DEBIAS = 126
SCORE_EMBARGO = 22
MAX_REL_SPREAD = 0.35           # same G7 leg filter as the put-spread book
MIN_OI = 10                     # per leg
COMMISSION = 0.65               # $/contract/leg at entry (expiry settle is free)
HEDGE_BP = 1.0                  # one-way underlying friction on hedge trades (bp of traded $)
MIN_NAMES_XS = 8                # need >= this many names with data to rank a date
RESULTS = cfg.RESULTS_ROOT


# --------------------------------------------------------------------------- signal panel
def build_baskets() -> pl.DataFrame:
    """Weekly cohort baskets: (date, ticker, side) with side=+1 short vol / -1 long vol."""
    targets = pl.read_parquet(cfg.TARGETS_PARQUET).filter(pl.col("horizon") == 22).select(
        "ticker", "date", "iv2", "target_var")
    preds = pl.read_parquet(cfg.PREDICTIONS_PARQUET).filter(pl.col("horizon") == 22).select(
        "ticker", "date", "rv_hat")
    fc = preds.join(targets.select("ticker", "date", "target_var"), on=["ticker", "date"], how="left")
    fc = pit.trailing_debias(fc, "rv_hat", "target_var", embargo=SCORE_EMBARGO,
                             min_periods=MIN_PERIODS_DEBIAS)
    fc = fc.with_columns(
        rv_hat_cal=pl.when(pl.col("log_bias").is_not_null())
        .then(pl.col("rv_hat") * pl.col("log_bias").exp()).otherwise(pl.col("rv_hat")))
    p = targets.join(fc.select("ticker", "date", "rv_hat_cal"), on=["ticker", "date"], how="inner")
    p = p.filter((pl.col("iv2") > 0) & (pl.col("rv_hat_cal") > 0)).with_columns(
        score=(pl.col("iv2").log() - pl.col("rv_hat_cal").log()))

    cal = p.select("date").unique().sort("date").with_columns(i=pl.int_range(pl.len()))
    wk = cal.filter(pl.col("i") % ROLL_EVERY == 0).select("date")
    pw = p.join(wk, on="date", how="inner")
    pw = pw.join(pw.group_by("date").agg(n=pl.len()), on="date").filter(pl.col("n") >= MIN_NAMES_XS)
    pw = pw.with_columns(rk=pl.col("score").rank("ordinal").over("date"))
    pw = pw.with_columns(
        side=pl.when(pl.col("rk") > pl.col("n") - K_SIDE).then(1)
        .when(pl.col("rk") <= K_SIDE).then(-1).otherwise(0))
    return pw.filter(pl.col("side") != 0).select("date", "ticker", "side", "score").sort("date", "ticker")


# --------------------------------------------------------------------------- one position
def _atm_strike(chain) -> float | None:
    """Strike nearest the spot (ATM straddle)."""
    if chain.df.is_empty():
        return None
    d = chain.df.with_columns(_err=(pl.col("strike") - chain.spot).abs()).sort("_err")
    return float(d["strike"][0])


def _leg_ok(q: dict | None) -> bool:
    if q is None:
        return False
    if not (q["bid"] >= 0 and q["ask"] > 0 and q["mid"] > 0):
        return False
    oi = q.get("oi")
    if oi is not None and oi < MIN_OI:
        return False
    return (q["ask"] - q["bid"]) / q["mid"] <= MAX_REL_SPREAD


def open_straddle(ticker: str, date: dt.date, side: int) -> dict | None:
    """Open a ~30-DTE ATM straddle: side=+1 sells (short vol), -1 buys. None if illiquid/missing.

    Returns the position dict the daily walker consumes: legs, qty sign, contracts (vega-sized,
    fractional), entry fills (crossed), entry commission, and the entry-day mid mark.
    """
    chain = chains.locate_expiry(ticker, date)
    if chain is None:
        return None
    k = _atm_strike(chain)
    if k is None:
        return None
    qc = chains.leg_quote_from_chain(chain, k, "C")
    qp = chains.leg_quote_from_chain(chain, k, "P")
    if not (_leg_ok(qc) and _leg_ok(qp)):
        return None
    vega_c = qc["vega"]                                  # BS vega is C==P at the same strike
    if not (vega_c and vega_c > 0):
        return None
    straddle_vega = 2.0 * vega_c * 100.0                 # $ vega per contract
    contracts = VEGA_TARGET / straddle_vega
    qty = -side                                           # short vol -> sell both legs
    fill_c = qc["bid"] if qty < 0 else qc["ask"]
    fill_p = qp["bid"] if qty < 0 else qp["ask"]
    mid0 = qc["mid"] + qp["mid"]
    delta0 = qc["delta"] + qp["delta"]                    # straddle delta per share
    return {
        "ticker": ticker, "side": side, "entry_date": date, "expiry": chain.expiry,
        "strike": k, "contracts": contracts, "qty": qty,
        "entry_fill": fill_c + fill_p, "mid": mid0, "delta": delta0, "spot": chain.spot,
        "entry_commission": COMMISSION * 2 * contracts,
    }


def walk_position(pos: dict) -> tuple[list[tuple[dt.date, float]], dict] | None:
    """Daily MTM P&L of one delta-hedged straddle, entry -> expiry-intrinsic settlement.

    Day 0 books the entry-spread cost (crossed fill vs mid) + commission; each later day books the
    option mark move (at MID) plus the hedge leg (yesterday's hedge shares x spot move, minus
    hedge friction on the rebalance). Missing chain days carry the last mark/delta forward.
    Returns (daily [(date, pnl$)], summary row) or None if settlement is impossible.
    """
    tk, expiry = pos["ticker"], pos["expiry"]
    mult = pos["contracts"] * 100.0
    qty = pos["qty"]

    spot_settle = chains.settlement_spot(tk, expiry)
    if spot_settle is None:
        return None

    days = [d for d in _trade_dates(tk) if pos["entry_date"] < d <= expiry]
    out: list[tuple[dt.date, float]] = []

    # entry day: crossing cost vs mid + commission + initial hedge friction
    spread_cost = abs(pos["mid"] - pos["entry_fill"]) * mult         # fill is worse than mid by construction
    last_mid, last_delta, last_spot = pos["mid"], pos["delta"], pos["spot"]
    hedge_sh = -qty * last_delta * mult                               # shares offsetting position delta
    hedge_cost0 = abs(hedge_sh) * last_spot * (HEDGE_BP / 1e4)
    out.append((pos["entry_date"], -spread_cost - pos["entry_commission"] - hedge_cost0))
    tot_hedge_cost = hedge_cost0

    for d in days:
        is_exp = d == expiry or d == days[-1]
        ch = chains.expiry_slice(tk, d, expiry)
        q_c = q_p = None
        if ch is not None:
            q_c = chains.leg_quote_from_chain(ch, pos["strike"], "C")
            q_p = chains.leg_quote_from_chain(ch, pos["strike"], "P")
        have_mark = (q_c is not None and q_p is not None
                     and q_c["mid"] > 0 and q_p["mid"] > 0)
        if is_exp:
            spot = spot_settle
            mid = max(spot - pos["strike"], 0.0) + max(pos["strike"] - spot, 0.0)
        elif have_mark:
            spot = ch.spot
            mid = q_c["mid"] + q_p["mid"]
        else:
            continue                                                  # carry mark forward
        opt_pnl = qty * (mid - last_mid) * mult
        hdg_pnl = hedge_sh * (spot - last_spot)
        # rebalance hedge to the new delta (friction on shares traded)
        if is_exp:
            new_delta = 0.0
        elif have_mark:
            new_delta = q_c["delta"] + q_p["delta"]
        else:
            new_delta = last_delta
        new_hedge = -qty * new_delta * mult
        trade_sh = abs(new_hedge - hedge_sh)
        cost = trade_sh * spot * (HEDGE_BP / 1e4)
        tot_hedge_cost += cost
        out.append((d, opt_pnl + hdg_pnl - cost))
        last_mid, last_delta, last_spot, hedge_sh = mid, new_delta, spot, new_hedge
        if is_exp:
            break

    pnl_total = sum(v for _, v in out)
    summary = {
        "ticker": tk, "side": pos["side"], "entry_date": pos["entry_date"], "expiry": expiry,
        "strike": pos["strike"], "contracts": pos["contracts"],
        "entry_straddle": pos["entry_fill"], "pnl": pnl_total, "hedge_cost": tot_hedge_cost,
    }
    return out, summary


_DATES_CACHE: dict[str, list[dt.date]] = {}


def _trade_dates(ticker: str) -> list[dt.date]:
    if ticker not in _DATES_CACHE:
        df = pl.read_parquet(cfg.INPUTS_PARQUET).filter(pl.col("ticker") == ticker)
        _DATES_CACHE[ticker] = sorted(df["date"].to_list())
    return _DATES_CACHE[ticker]


# --------------------------------------------------------------------------- book runner
def main() -> None:
    t0 = time.time()
    baskets = build_baskets()
    print(f"baskets: {baskets['date'].n_unique()} weekly cohorts, {baskets.height} slots")

    daily: dict[dt.date, float] = {}
    rows: list[dict] = []
    n_skip = 0
    for r in baskets.iter_rows(named=True):
        pos = open_straddle(r["ticker"], r["date"], r["side"])
        if pos is None:
            n_skip += 1
            continue
        res = walk_position(pos)
        if res is None:
            n_skip += 1
            continue
        series, summary = res
        for d, v in series:
            daily[d] = daily.get(d, 0.0) + v
        rows.append(summary)
    print(f"positions: {len(rows)} opened, {n_skip} skipped ({time.time()-t0:.0f}s)")

    led = pl.DataFrame(rows).sort("entry_date", "ticker")
    dser = pl.DataFrame({"date": list(daily.keys()), "pnl": list(daily.values())}).sort("date")
    led.write_csv(RESULTS / "xsec_straddle_positions.csv")
    dser.write_csv(RESULTS / "xsec_straddle_daily.csv")
    _report(led, dser)
    print(f"done ({time.time()-t0:.0f}s) -> results/xsec_straddle_report.md")


def _metrics(dser: pl.DataFrame) -> dict:
    r = dser["pnl"].to_numpy()
    n_yrs = max((dser["date"].max() - dser["date"].min()).days / 365.25, 1e-9)
    ppy = len(r) / n_yrs
    sh = r.mean() / r.std(ddof=1) * math.sqrt(ppy) if r.std(ddof=1) > 0 else 0.0
    eq = np.cumsum(r)
    dd = float(np.max(np.maximum.accumulate(eq) - eq))
    q = np.quantile(r, 0.05)
    return {"sharpe": sh, "pnl": float(r.sum()), "ann": float(r.mean() * ppy), "maxdd": dd,
            "cvar95": float(r[r <= q].mean()), "worst": float(r.min()), "n": len(r)}


def _report(led: pl.DataFrame, dser: pl.DataFrame) -> None:
    m = _metrics(dser)
    gross_vega = VEGA_TARGET * 2 * K_SIDE          # $ vega deployed per weekly cohort
    lines = [
        "# Cross-sectional vol RV — L/S delta-hedged straddles (Stage-B prototype)",
        "",
        f"_{led['entry_date'].min()} → {led['expiry'].max()} · weekly cohorts · K={K_SIDE}/side · "
        f"${VEGA_TARGET:,.0f} vega/name · daily MTM (mid marks, crossed entries, "
        f"{HEDGE_BP:.0f}bp hedge friction) · generated {dt.date.today()}_",
        "",
        "## Headline (true daily MTM basis)",
        "",
        f"- positions: {led.height:,} (short {int((led['side']==1).sum())} / long {int((led['side']==-1).sum())})",
        f"- total P&L: ${m['pnl']:,.0f}  ·  ann ${m['ann']:,.0f} per ${gross_vega:,.0f} gross vega/cohort",
        f"- **Sharpe (daily, ann): {m['sharpe']:.2f}**",
        f"- maxDD ${m['maxdd']:,.0f} · CVaR95/day ${m['cvar95']:,.0f} · worst day ${m['worst']:,.0f}",
        "",
        "## By era",
        "",
        "| era | pnl | sharpe |",
        "| --- | --- | --- |",
    ]
    for lo, hi in [(2010, 2013), (2014, 2017), (2018, 2021), (2022, 2026)]:
        sub = dser.filter(pl.col("date").dt.year().is_between(lo, hi))
        if sub.height > 50:
            mm = _metrics(sub)
            lines.append(f"| {lo}–{hi} | ${mm['pnl']:,.0f} | {mm['sharpe']:.2f} |")
    lines += ["", "## By side", ""]
    for s, lab in [(1, "short vol (rich)"), (-1, "long vol (cheap)")]:
        sub = led.filter(pl.col("side") == s)
        lines.append(f"- {lab}: n={sub.height}, pnl ${sub['pnl'].sum():,.0f}, "
                     f"win {(sub['pnl']>0).mean()*100:.0f}%")
    lines += ["", "## By ticker", "", "| ticker | n | pnl | short_n | long_n |", "| --- | --- | --- | --- | --- |"]
    by_t = led.group_by("ticker").agg(
        n=pl.len(), pnl=pl.col("pnl").sum(),
        s=(pl.col("side") == 1).sum(), l=(pl.col("side") == -1).sum()).sort("pnl", descending=True)
    for r in by_t.iter_rows(named=True):
        lines.append(f"| {r['ticker']} | {r['n']} | ${r['pnl']:,.0f} | {r['s']} | {r['l']} |")
    (RESULTS / "xsec_straddle_report.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
