"""ORATS EOD chain access — load, locate an expiry, relocate legs along the path.

Raw layout (confirmed on disk): `execution/data/raw/orats/ticker=<T>/year=<Y>/data.parquet`,
one row per (trade_date, expirDate, strike) carrying BOTH the call and put (c*/p* columns), a
single shared `delta` = the CALL delta (put delta = call_delta - 1), shared `vega`/`gamma`, and
`stkPx` spot. We normalize to a tidy per-strike frame and cache per (ticker, year).

Everything here is strictly point-in-time: a trade only ever reads chains dated on or after its
entry, and marking on day t reads only the day-t chain (the engine enforces it; this module just
serves whatever date it is asked for).
"""

from __future__ import annotations

import datetime as dt
from functools import lru_cache

import polars as pl

from stage2_trade_eval import config as cfg
from stage2_trade_eval.contracts import ExpiryChain

# Tidy column set we expose downstream (renamed from raw ORATS).
_RAW = [
    "trade_date", "expirDate", "strike", "stkPx", "delta", "vega", "gamma", "theta",
    "cBidPx", "cAskPx", "pBidPx", "pAskPx", "cValue", "pValue", "cOi", "pOi", "cVolu", "pVolu",
]


@lru_cache(maxsize=64)
def _load_ticker_year(ticker: str, year: int) -> pl.DataFrame | None:
    """Read & tidy one ticker-year ORATS parquet (cached). None if absent."""
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
    }).with_columns(
        put_delta=(pl.col("call_delta") - 1.0),
        ptheta=pl.col("ctheta"),                 # ORATS ships one theta; adequate for hedging marks
    )


@lru_cache(maxsize=8192)
def day_chain(ticker: str, trade_date: dt.date) -> pl.DataFrame:
    """All option rows for `ticker` on `trade_date` (tidy, all expiries). Empty if no data.

    Cached per (ticker, trade_date): the hot path (path-marking) relocates several legs on the
    SAME day, so memoizing the day slice turns N_legs full-frame filters into one filter + lookups.
    """
    df = _load_ticker_year(ticker, trade_date.year)
    if df is None:
        return pl.DataFrame()
    return df.filter(pl.col("trade_date") == trade_date)


def locate_expiry(ticker: str, trade_date: dt.date, target_dte: int = cfg.TARGET_DTE,
                  tol: tuple[int, int] = cfg.DTE_TOLERANCE) -> ExpiryChain | None:
    """Pick the listed expiry nearest `target_dte` calendar days; None if none in tolerance.

    Liquidity is NOT filtered here (a structure may want strikes the body doesn't); per-leg
    liquidity is enforced at fill time in `marks.py`.
    """
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


def relocate(ticker: str, trade_date: dt.date, expiry: dt.date, strike: float, right: str
             ) -> dict | None:
    """Find ONE leg's row on a later date (same expiry+strike+right); None if not listed/halted.

    Returns a dict with bid/ask/mid + greeks for that leg, plus the day's spot. Used to mark the
    path and to price an early close.
    """
    day = day_chain(ticker, trade_date)
    if day.is_empty():
        return None
    row = day.filter((pl.col("expiry") == expiry) & (pl.col("strike") == strike))
    if row.is_empty():
        return None
    r = row.row(0, named=True)
    if right == "C":
        bid, ask, mid, delta = r["cbid"], r["cask"], r["cmid"], r["call_delta"]
    else:
        bid, ask, mid, delta = r["pbid"], r["pask"], r["pmid"], r["put_delta"]
    return {
        "bid": _f(bid), "ask": _f(ask), "mid": _f(mid), "delta": _f(delta),
        "vega": _f(r["vega"]), "gamma": _f(r["gamma"]), "spot": _f(r["spot"]),
        "oi": r["oi_c"] if right == "C" else r["oi_p"],
        "vol": r["vol_c"] if right == "C" else r["vol_p"],
    }


def leg_quote_from_chain(chain: ExpiryChain, strike: float, right: str) -> dict | None:
    """Same as `relocate` but off an already-loaded `ExpiryChain` (entry-day fast path)."""
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


def _f(x) -> float:
    return float(x) if x is not None else float("nan")
