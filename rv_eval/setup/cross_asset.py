"""Cross-asset systematic-regime features from proxy ETF daily closes.

All series are *systematic* (one value per date, broadcast to every ticker) and
point-in-time (every column at date `t` uses only closes at-or-before `t`). They feed
the shrinkage / pooling / regime models in `planning_docs/research/rv_har_extensions_plan.md`
as cheap cross-asset regime regressors — not as free per-ticker OLS terms.

Why ETF proxies instead of raw FRED macro series: the proxies (LQD/HYG/UUP/SHY/IEF/TLT)
are already on the Polygon daily lake back to 2003-2008, are tradeable and point-in-time
clean, and a *return spread* between two of them is exactly the risk-regime signal we want.

  credit_spread  log(LQD/HYG)              IG-vs-HY price level; RISES in credit stress.
  credit_mom     r20(HYG) - r20(LQD)       HY-minus-IG 20d return; NEGATIVE in stress.
  usd_mom        r20(UUP)                  broad-USD 20d return; risk-off proxy.
  rates_mom      r20(TLT) - r20(SHY)       long-minus-short duration 20d return;
                                           POSITIVE when the curve rallies / rates fall.

`r20(X)_t = log(close_t) - log(close_{t-20})` (20 trading days ≈ 1 month).
"""

from __future__ import annotations

from datetime import date

import polars as pl

from rv_eval import config as C

# Proxy ETFs (read from the Polygon daily lake; none of these split in the sample window).
_PROXIES = ("HYG", "LQD", "UUP", "TLT", "SHY")
_MOM_WINDOW = 20  # trading days for the momentum/return-spread features

# Real fund-inception dates. The lake carries spurious pre-inception rows under reused
# tickers (e.g. "HYG" shows ~$25 in 2004, but iShares HYG launched 2007-04-11), which
# would corrupt the credit features — drop anything before inception.
_INCEPTION: dict[str, date] = {
    "HYG": date(2007, 4, 11),
    "LQD": date(2002, 7, 26),
    "UUP": date(2007, 2, 20),
    "TLT": date(2002, 7, 26),
    "SHY": date(2002, 7, 26),
}


def _proxy_log_close(ticker: str) -> pl.DataFrame:
    """Daily log-close for one proxy ETF, keyed by trading `date` (UTC date == trade date)."""
    path = C.DAILY_LAKE / f"ticker={ticker}" / "data.parquet"
    return (
        pl.scan_parquet(path)
        .select(
            pl.col("window_start").dt.convert_time_zone("America/New_York").dt.date().alias("date"),
            pl.col("close"),
        )
        .filter((pl.col("close") > 0) & (pl.col("date") >= _INCEPTION[ticker]))
        .group_by("date").agg(pl.col("close").last())   # guard against dup rows
        .sort("date")
        .select("date", pl.col("close").log().alias(f"log_{ticker}"))
        .collect()
    )


def cross_asset_features() -> pl.DataFrame:
    """Date-keyed cross-asset regime features (credit / USD / rates momentum + credit level)."""
    df = _proxy_log_close(_PROXIES[0])
    for tk in _PROXIES[1:]:
        df = df.join(_proxy_log_close(tk), on="date", how="full", coalesce=True)
    df = df.sort("date")

    w = _MOM_WINDOW
    df = df.with_columns(
        # 20-day log returns per proxy (trailing; null until w prior closes exist).
        **{f"r20_{tk}": (pl.col(f"log_{tk}") - pl.col(f"log_{tk}").shift(w)) for tk in _PROXIES}
    )
    out = df.select(
        "date",
        credit_spread=pl.col("log_LQD") - pl.col("log_HYG"),
        credit_mom=pl.col("r20_HYG") - pl.col("r20_LQD"),
        usd_mom=pl.col("r20_UUP"),
        rates_mom=pl.col("r20_TLT") - pl.col("r20_SHY"),
    )
    return out.sort("date")


if __name__ == "__main__":
    f = cross_asset_features()
    print(f"cross_asset: {f.height} dates, range {f['date'].min()} -> {f['date'].max()}")
    print(f.describe())
    print(f.tail(3))
