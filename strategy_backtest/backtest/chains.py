"""ORATS EOD chain access — load, locate an expiry, relocate a leg, read the settlement spot.

Raw layout: `back-test-data/orats/ticker=<T>/year=<Y>/data.parquet`, one row per
(trade_date, expirDate, strike) carrying BOTH call and put (c*/p*), a shared `delta` = the CALL
delta (put delta = call_delta - 1), shared vega/gamma, and `stkPx` spot. We normalise to a tidy
per-strike frame and cache per (ticker, year).

Strictly point-in-time: a trade reads only chains dated on or after its entry; settlement reads the
expiry-day chain. This module just serves whatever date it is asked for; the engine enforces order.
"""

from __future__ import annotations

import datetime as dt
from functools import lru_cache

import polars as pl

from strategy_backtest.backtest import config as cfg
from strategy_backtest.backtest.contracts import ExpiryChain

_RAW = [
    "trade_date", "expirDate", "strike", "stkPx", "delta", "vega", "gamma", "theta",
    "cBidPx", "cAskPx", "pBidPx", "pAskPx", "cValue", "pValue", "cOi", "pOi", "cVolu", "pVolu",
]


@lru_cache(maxsize=64)
def _load_ticker_year(ticker: str, year: int) -> pl.DataFrame | None:
    path = cfg.RAW_ORATS / f"ticker={ticker}" / f"year={year}" / "data.parquet"
    if not path.exists():
        return None
    df = pl.read_parquet(path, columns=_RAW)
    return df.rename({
        "expirDate": "expiry", "stkPx": "spot",
        "delta": "call_delta", "theta": "ctheta",
        "cBidPx": "cbid", "cAskPx": "cask", "pBidPx": "pbid", "pAskPx": "pask",
        "cValue": "cmid", "pValue": "pmid", "cOi": "oi_c", "pOi": "oi_p",
        "cVolu": "vol_c", "pVolu": "vol_p",
    }).with_columns(put_delta=(pl.col("call_delta") - 1.0))


@lru_cache(maxsize=8192)
def day_chain(ticker: str, trade_date: dt.date) -> pl.DataFrame:
    """All option rows for `ticker` on `trade_date` (tidy, all expiries). Empty if no data."""
    df = _load_ticker_year(ticker, trade_date.year)
    if df is None:
        return pl.DataFrame()
    return df.filter(pl.col("trade_date") == trade_date)


def locate_expiry(ticker: str, trade_date: dt.date, target_dte: int = cfg.TARGET_DTE,
                  tol: tuple[int, int] = cfg.DTE_TOLERANCE) -> ExpiryChain | None:
    """Pick the listed expiry nearest `target_dte` calendar days; None if none in tolerance."""
    day = day_chain(ticker, trade_date)
    if day.is_empty():
        return None
    exps = (
        day.select("expiry").unique()
        .with_columns(dte=(pl.col("expiry") - pl.lit(trade_date)).dt.total_days())
        .filter((pl.col("dte") >= tol[0]) & (pl.col("dte") <= tol[1]))
        .with_columns(err=(pl.col("dte") - target_dte).abs())
        .sort("err")
    )
    if exps.is_empty():
        return None
    expiry = exps["expiry"][0]
    sl = day.filter(pl.col("expiry") == expiry).sort("strike")
    spot = float(sl["spot"][0])
    return ExpiryChain(trade_date=trade_date, expiry=expiry, spot=spot, df=sl)


def expiry_slice(ticker: str, trade_date: dt.date, expiry: dt.date) -> ExpiryChain | None:
    """Re-locate an already-chosen `expiry` on a *later* trade date (managed-exit daily mark, §5).

    Unlike `locate_expiry` (which picks the nearest-DTE expiry at entry), this serves a fixed expiry
    so an open spread can be marked day by day. None if that session/expiry isn't listed (the caller
    carries the last good mark forward).
    """
    day = day_chain(ticker, trade_date)
    if day.is_empty():
        return None
    sl = day.filter(pl.col("expiry") == expiry).sort("strike")
    if sl.is_empty():
        return None
    return ExpiryChain(trade_date=trade_date, expiry=expiry, spot=float(sl["spot"][0]), df=sl)


def leg_quote_from_chain(chain: ExpiryChain, strike: float, right: str) -> dict | None:
    """Bid/ask/mid + greeks for one leg off an already-loaded ExpiryChain (entry-day fast path)."""
    row = chain.df.filter(pl.col("strike") == strike)
    if row.is_empty():
        return None
    r = row.row(0, named=True)
    if right == "C":
        bid, ask, mid, delta = r["cbid"], r["cask"], r["cmid"], r["call_delta"]
    else:
        bid, ask, mid, delta = r["pbid"], r["pask"], r["pmid"], r["put_delta"]
    return {
        "bid": _f(bid), "ask": _f(ask), "mid": _f(mid), "delta": _f(delta),
        "vega": _f(r["vega"]), "gamma": _f(r["gamma"]), "spot": chain.spot,
        "oi": r["oi_c"] if right == "C" else r["oi_p"],
        "vol": r["vol_c"] if right == "C" else r["vol_p"],
    }


def settlement_spot(ticker: str, expiry: dt.date, lookback: int = 5) -> float | None:
    """Underlying spot at expiry for intrinsic settlement.

    Reads `stkPx` off the expiry-day chain (constant across strikes); if that exact session is
    missing (holiday/halt), walks back up to `lookback` calendar days to the last listed session.
    """
    for back in range(lookback + 1):
        d = expiry - dt.timedelta(days=back)
        day = day_chain(ticker, d)
        if not day.is_empty():
            return float(day["spot"][0])
    return None


def _f(x) -> float:
    return float(x) if x is not None else float("nan")
