"""Range-based daily variance estimators from daily OHLC bars.

Alternative volatility proxies / sanity cross-checks alongside the 5-min realized measures
(methods §2). All are daily *variance* estimates (square of a vol), comparable to RV:
  - Parkinson (1980)        — high/low range only
  - Garman-Klass (1980)     — high/low + open/close, more efficient
  - Rogers-Satchell (1991)  — drift-independent, uses O/H/L/C
"""

from __future__ import annotations

import math

import polars as pl

from strategy_backtest.pipeline import config as C

_PARK = 1.0 / (4.0 * math.log(2.0))
_GK_C = 2.0 * math.log(2.0) - 1.0

# RTH window in ET minutes-of-day: 09:30 (570) inclusive -> 16:00 (960) exclusive.
_RTH_OPEN_MIN = C.RTH_OPEN[0] * 60 + C.RTH_OPEN[1]
_RTH_CLOSE_MIN = C.RTH_CLOSE[0] * 60 + C.RTH_CLOSE[1]


def _daily_ohlc_lf(ticker: str) -> pl.LazyFrame:
    """Daily OHLCV bar keyed by ET `date`.

    Prefers the staged Polygon daily bar; for the core ETF universe (no daily bars in the
    raw-only mirror — those are cross-asset proxies only) it aggregates the staged 1-min bars
    over the RTH session. Either source yields the same ``date, open, high, low, close,
    volume, transactions`` contract the range estimators consume.
    """
    daily_path = C.RAW_DAILY / f"ticker={ticker}" / "data.parquet"
    if daily_path.exists():
        return (
            pl.scan_parquet(daily_path)
            .select("window_start", "open", "high", "low", "close", "volume", "transactions")
            .with_columns(date=pl.col("window_start").dt.convert_time_zone(C.ET_TZ).dt.date())
            .drop("window_start")
        )

    minute_path = C.RAW_MINUTE / f"ticker={ticker}" / "data.parquet"
    if not minute_path.exists():
        raise FileNotFoundError(
            f"no staged daily or minute bars for {ticker}: {daily_path} / {minute_path}")
    et = pl.col("window_start").dt.convert_time_zone(C.ET_TZ)
    return (
        pl.scan_parquet(minute_path)
        .select("window_start", "open", "high", "low", "close", "volume", "transactions")
        .with_columns(date=et.dt.date(),
                      _mod=(et.dt.hour().cast(pl.Int32) * 60 + et.dt.minute().cast(pl.Int32)))
        .filter((pl.col("_mod") >= _RTH_OPEN_MIN) & (pl.col("_mod") < _RTH_CLOSE_MIN))
        .sort("window_start")
        .group_by("date")
        .agg(
            open=pl.col("open").first(),
            high=pl.col("high").max(),
            low=pl.col("low").min(),
            close=pl.col("close").last(),
            volume=pl.col("volume").sum(),
            transactions=pl.col("transactions").sum(),
        )
    )


def range_measures(ticker: str) -> pl.DataFrame:
    """Daily Parkinson / Garman-Klass / Rogers-Satchell variance for one ticker."""
    df = (
        _daily_ohlc_lf(ticker)
        .filter((pl.col("open") > 0) & (pl.col("high") > 0)
                & (pl.col("low") > 0) & (pl.col("close") > 0))
        .with_columns(
            hl=(pl.col("high") / pl.col("low")).log(),
            co=(pl.col("close") / pl.col("open")).log(),
            hc=(pl.col("high") / pl.col("close")).log(),
            ho=(pl.col("high") / pl.col("open")).log(),
            lc=(pl.col("low") / pl.col("close")).log(),
            lo=(pl.col("low") / pl.col("open")).log(),
        )
        .with_columns(
            parkinson=_PARK * pl.col("hl") ** 2,
            gk=0.5 * pl.col("hl") ** 2 - _GK_C * pl.col("co") ** 2,
            rs=pl.col("hc") * pl.col("ho") + pl.col("lc") * pl.col("lo"),
        )
        .select("date", "parkinson", "gk", "rs", "volume", "transactions")
        .sort("date")
        .collect()
    )
    return df.with_columns(ticker=pl.lit(ticker))


if __name__ == "__main__":
    import sys

    tk = sys.argv[1] if len(sys.argv) > 1 else "SPY"
    df = range_measures(tk)
    print(df.tail(5))
    ann = (df["gk"] * C.TRADING_DAYS_PER_YEAR).sqrt()
    print(f"{tk}: {df.height} days; GK annualized-vol median={ann.median():.3f}")
