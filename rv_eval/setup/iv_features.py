"""Implied-volatility & systematic-regime features from ORATS option chains.

Per ticker, per trade_date (all point-in-time, known at t):
  - ATM IV at 30/60/90 calendar days (smoothed-vol curve, interpolated across expiries)
  - term-structure slope (90d - 30d)
  - 25-delta skew (downside put IV - upside call IV)
  - ORATS `extVol` vendor forecast at ~30d (a comparator)

Systematic regime (broadcast to every ticker by date):
  - VIX (SPX 30d ATM) / VIX3M (SPX 90d ATM) / slope, and a VVIX-like vol-of-vol (VIX 30d ATM).

ORATS `smoothSmvVol` is the smoothed per-strike IV; `delta` is the call delta in [0,1] so
ATM ~= 0.5, 25-delta call ~= 0.25, 25-delta put ~= 0.75.
"""

from __future__ import annotations

import polars as pl

from rv_eval import config as C

_YR = 365.0


def _load_chain(ticker: str) -> pl.DataFrame:
    """Staged ORATS chain for one ticker, pruned to the ATM/skew region and ≤6mo tenor."""
    files = sorted((C.RAW_ORATS / f"ticker={ticker}").glob("year=*/data.parquet"))
    if not files:
        raise FileNotFoundError(f"no staged ORATS chain for {ticker}")
    return (
        pl.scan_parquet(files)
        .select("trade_date", "yte", "strike", "stkPx", "delta", "smoothSmvVol", "extVol")
        .filter(
            (pl.col("smoothSmvVol").is_not_null()) & (pl.col("smoothSmvVol") > 0)
            & (pl.col("stkPx") > 0) & (pl.col("delta").is_not_null())
            & (pl.col("delta") >= 0.10) & (pl.col("delta") <= 0.90)
            & (pl.col("yte") >= 0.01) & (pl.col("yte") <= 0.50)
        )
        .with_columns(dte=pl.col("yte") * _YR)
        .collect()
    )


def _atm_term_points(chain: pl.DataFrame) -> pl.DataFrame:
    """One ATM point per (trade_date, expiry): vol & extVol at the strike nearest spot."""
    return (
        chain.with_columns(adiff=(pl.col("strike") - pl.col("stkPx")).abs())
        .sort("adiff")
        .group_by("trade_date", "dte")
        .agg(atm_vol=pl.col("smoothSmvVol").first(), atm_ext=pl.col("extVol").first())
    )


def _skew_per_date(chain: pl.DataFrame) -> pl.DataFrame:
    """25-delta skew (put IV - call IV) from the expiry nearest 30 days."""
    near = chain.with_columns(tdiff=(pl.col("dte") - 30.0).abs())
    # the single expiry per trade_date closest to 30d
    expiry = (
        near.sort("tdiff").group_by("trade_date").agg(dte=pl.col("dte").first())
    )
    near = near.join(expiry, on=["trade_date", "dte"], how="inner")
    call = (
        near.with_columns(d=(pl.col("delta") - 0.25).abs())
        .sort("d").group_by("trade_date").agg(call25=pl.col("smoothSmvVol").first())
    )
    put = (
        near.with_columns(d=(pl.col("delta") - 0.75).abs())
        .sort("d").group_by("trade_date").agg(put25=pl.col("smoothSmvVol").first())
    )
    return call.join(put, on="trade_date", how="inner").with_columns(
        skew_25d=pl.col("put25") - pl.col("call25")
    ).select("trade_date", "skew_25d")


def _interp(points: pl.DataFrame, col: str, tenor_days: int, out_name: str) -> pl.DataFrame:
    """Linear-in-DTE interpolation of `col` to a target tenor, per trade_date.

    Flat extrapolation when the tenor falls outside the available expiry range.
    """
    lo = (
        points.filter(pl.col("dte") <= tenor_days).sort("dte")
        .group_by("trade_date").agg(dte_lo=pl.col("dte").last(), v_lo=pl.col(col).last())
    )
    hi = (
        points.filter(pl.col("dte") >= tenor_days).sort("dte")
        .group_by("trade_date").agg(dte_hi=pl.col("dte").first(), v_hi=pl.col(col).first())
    )
    j = lo.join(hi, on="trade_date", how="full", coalesce=True)
    val = (
        pl.when(pl.col("dte_lo").is_null()).then(pl.col("v_hi"))
        .when(pl.col("dte_hi").is_null()).then(pl.col("v_lo"))
        .when(pl.col("dte_hi") == pl.col("dte_lo")).then(pl.col("v_lo"))
        .otherwise(
            pl.col("v_lo")
            + (pl.col("v_hi") - pl.col("v_lo"))
            * (tenor_days - pl.col("dte_lo")) / (pl.col("dte_hi") - pl.col("dte_lo"))
        )
    )
    return j.select("trade_date", val.alias(out_name))


def iv_features(ticker: str) -> pl.DataFrame:
    """Per-date IV term-structure + skew features for one ticker (date column = `date`)."""
    chain = _load_chain(ticker)
    atm = _atm_term_points(chain)
    out = _interp(atm, "atm_vol", 30, "iv_30d")
    for tenor, name in ((60, "iv_60d"), (90, "iv_90d")):
        out = out.join(_interp(atm, "atm_vol", tenor, name), on="trade_date", how="full", coalesce=True)
    out = out.join(_interp(atm, "atm_ext", 30, "ext_vol"), on="trade_date", how="full", coalesce=True)
    out = out.join(_skew_per_date(chain), on="trade_date", how="left")
    out = out.with_columns(iv_slope=pl.col("iv_90d") - pl.col("iv_30d"))
    return out.rename({"trade_date": "date"}).sort("date").with_columns(ticker=pl.lit(ticker))


def systematic_features() -> pl.DataFrame:
    """Market-wide regime series, keyed by date.

      vix / vix3m / vix_slope   SPX 30d / 90d ATM IV and their slope.
      vix9d / vix9d_slope       SPX 9d ATM IV (short end) and 9d-30d slope
                                (negative = front-end backwardation / stress).
      vvix                      VIX 30d ATM IV (vol-of-vol).
      credit_spread / credit_mom / usd_mom / rates_mom
                                cross-asset regime proxies (see cross_asset.py).
    """
    from rv_eval.setup.cross_asset import cross_asset_features

    spx = iv_features("SPX").select(
        "date", pl.col("iv_30d").alias("vix"), pl.col("iv_90d").alias("vix3m"),
        pl.col("iv_slope").alias("vix_slope"),
    )
    # Short-end VIX: interpolate the SPX ATM term curve to 9 days (reuses the IV machinery).
    spx_atm = _atm_term_points(_load_chain("SPX"))
    vix9d = _interp(spx_atm, "atm_vol", 9, "vix9d").rename({"trade_date": "date"})
    vvix = iv_features("VIX").select("date", pl.col("iv_30d").alias("vvix"))

    out = (
        spx.join(vix9d, on="date", how="full", coalesce=True)
        .join(vvix, on="date", how="full", coalesce=True)
        .join(cross_asset_features(), on="date", how="left")
        .with_columns(vix9d_slope=pl.col("vix9d") - pl.col("vix"))
        .sort("date")
    )
    return out


if __name__ == "__main__":
    import sys

    tk = sys.argv[1] if len(sys.argv) > 1 else "SPY"
    df = iv_features(tk)
    print(df.tail(5))
    print(f"{tk}: {df.height} dates; iv_30d median={df['iv_30d'].median():.3f} "
          f"skew_25d median={df['skew_25d'].median():.3f}")
    if tk == "SPY":
        sysf = systematic_features()
        print("\nsystematic tail:")
        print(sysf.tail(3))
