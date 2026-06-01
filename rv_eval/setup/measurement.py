"""Measurement layer: raw 5-min bars -> daily realized-volatility estimators.

Per (ticker, day) from RTH 5-minute log returns (eval plan §2 / methods §2):
  RV (intraday), BV (bipower), jump = max(RV-BV, 0), RS+/RS- (semivariance),
  RQ (quarticity), plus the overnight (close->open) squared return split/dividend
  adjusted, and the Hansen-Lunde total RV = RV_intraday + r_overnight^2.

Sessions/half-days are detected empirically from the data (the staged holiday file is
forward-looking only): a day's observed last RTH bar classifies it as a regular (78 five-min
buckets) or early-close (~42) session, and the expected-bar count scales accordingly so
< 95% coverage marks a low-confidence day rather than a false missing-data failure.
"""

from __future__ import annotations

import math

import polars as pl

from rv_eval import config as C

_MU1 = math.sqrt(2.0 / math.pi)          # E|Z| for standard normal
_BV_SCALE = 1.0 / (_MU1 * _MU1)           # = pi/2, bipower variation scaling
_RTH_OPEN_MIN = C.RTH_OPEN[0] * 60 + C.RTH_OPEN[1]    # 570
_RTH_CLOSE_MIN = C.RTH_CLOSE[0] * 60 + C.RTH_CLOSE[1]  # 960
_REGULAR_LAST_MOD = 955   # last bar window_start >= 15:55 ET => regular close
_EARLY_LAST_MOD = 790     # last bar window_start <= 13:10 ET => early (half-day) close
_HALF_EXPECTED = (13 * 60 - _RTH_OPEN_MIN) // C.BAR_MINUTES   # 09:30->13:00 = 42 buckets


def _corp_adjustments(ticker: str) -> pl.DataFrame:
    """Per-date split ratio (from/to) and cash dividend for the overnight adjustment."""
    frames = []
    splits_path = C.RAW_CORP / "splits.parquet"
    if splits_path.exists():
        s = (
            pl.read_parquet(splits_path)
            .filter(pl.col("ticker") == ticker)
            .with_columns(date=pl.col("execution_date").str.to_date(strict=False),
                          split_ratio=pl.col("split_from") / pl.col("split_to"))
            .group_by("date").agg(split_ratio=pl.col("split_ratio").product())
        )
        frames.append(s)
    divs_path = C.RAW_CORP / "dividends.parquet"
    if divs_path.exists():
        d = (
            pl.read_parquet(divs_path)
            .filter(pl.col("ticker") == ticker)
            .with_columns(date=pl.col("ex_dividend_date").str.to_date(strict=False))
            .group_by("date").agg(div_cash=pl.col("cash_amount").sum())
        )
        frames.append(d)
    if not frames:
        return pl.DataFrame(schema={"date": pl.Date, "split_ratio": pl.Float64, "div_cash": pl.Float64})
    out = frames[0]
    for f in frames[1:]:
        out = out.join(f, on="date", how="full", coalesce=True)
    for col, default in (("split_ratio", 1.0), ("div_cash", 0.0)):
        if col not in out.columns:
            out = out.with_columns(pl.lit(default).alias(col))
    return out.select("date", "split_ratio", "div_cash")


def daily_measures(ticker: str) -> pl.DataFrame:
    """Compute the daily realized-measure table for one ticker from staged minute bars."""
    minute_path = C.RAW_MINUTE / f"ticker={ticker}" / "data.parquet"
    if not minute_path.exists():
        raise FileNotFoundError(f"no staged minute bars for {ticker}: {minute_path}")

    bars = (
        pl.scan_parquet(minute_path)
        .select("window_start", "open", "close")
        .with_columns(et=pl.col("window_start").dt.convert_time_zone(C.ET_TZ))
        .with_columns(date=pl.col("et").dt.date(),
                      mod=pl.col("et").dt.hour().cast(pl.Int32) * 60
                          + pl.col("et").dt.minute().cast(pl.Int32))
        .filter((pl.col("mod") >= _RTH_OPEN_MIN) & (pl.col("mod") < _RTH_CLOSE_MIN)
                & (pl.col("close") > 0) & (pl.col("open") > 0))
        .with_columns(bucket=((pl.col("mod") - _RTH_OPEN_MIN) // C.BAR_MINUTES).cast(pl.Int32))
        .collect()
    )
    if bars.is_empty():
        return pl.DataFrame()

    # Day-level open/close/last-bar (sorted explicitly so first/last are unambiguous).
    day = bars.group_by("date").agg(
        day_open=pl.col("open").sort_by("et").first(),
        day_close=pl.col("close").sort_by("et").last(),
        last_mod=pl.col("mod").max(),
    ).sort("date")

    # Last close in each 5-min bucket -> intraday return path (open -> first bucket -> ...).
    bk = (
        bars.group_by("date", "bucket")
        .agg(close=pl.col("close").sort_by("et").last())
        .sort("date", "bucket")
        .join(day.select("date", "day_open"), on="date")
    )
    bk = bk.with_columns(
        logc=pl.col("close").log(),
        is_first=pl.col("bucket") == pl.col("bucket").min().over("date"),
    )
    bk = bk.with_columns(
        ret=pl.when(pl.col("is_first"))
        .then(pl.col("logc") - pl.col("day_open").log())
        .otherwise(pl.col("logc") - pl.col("logc").shift(1).over("date"))
    )
    bk = bk.with_columns(abs_ret=pl.col("ret").abs())
    bk = bk.with_columns(bipow=pl.col("abs_ret") * pl.col("abs_ret").shift(1).over("date"))

    meas = bk.group_by("date").agg(
        rv_intraday=(pl.col("ret") ** 2).sum(),
        rs_plus=(pl.col("ret").pow(2) * (pl.col("ret") > 0)).sum(),
        rs_minus=(pl.col("ret").pow(2) * (pl.col("ret") < 0)).sum(),
        rq_sum=(pl.col("ret") ** 4).sum(),
        bipow_sum=pl.col("bipow").sum(),
        n_returns=pl.len(),
    ).with_columns(
        bv=_BV_SCALE * pl.col("bipow_sum"),
        rq=(pl.col("n_returns") / 3.0) * pl.col("rq_sum"),
    ).with_columns(
        jump=(pl.col("rv_intraday") - pl.col("bv")).clip(lower_bound=0.0),
    )

    # Session classification + well-behaved flag (expected bars scaled to the session).
    day = day.with_columns(
        session=pl.when(pl.col("last_mod") >= _REGULAR_LAST_MOD).then(pl.lit("regular"))
        .when(pl.col("last_mod") <= _EARLY_LAST_MOD).then(pl.lit("half"))
        .otherwise(pl.lit("partial")),
    ).with_columns(
        expected_bars=pl.when(pl.col("session") == "regular").then(C.FULL_SESSION_5MIN_BARS)
        .when(pl.col("session") == "half").then(_HALF_EXPECTED)
        .otherwise(C.FULL_SESSION_5MIN_BARS),
    )

    # Overnight return (split + dividend adjusted) and total RV.
    corp = _corp_adjustments(ticker)
    day = day.join(corp, on="date", how="left").with_columns(
        split_ratio=pl.col("split_ratio").fill_null(1.0) if "split_ratio" in corp.columns else pl.lit(1.0),
        div_cash=pl.col("div_cash").fill_null(0.0) if "div_cash" in corp.columns else pl.lit(0.0),
    ).sort("date")
    day = day.with_columns(prev_close=pl.col("day_close").shift(1))
    day = day.with_columns(adj_prev_close=pl.col("prev_close") * pl.col("split_ratio"))
    day = day.with_columns(
        overnight_ret=((pl.col("day_open") + pl.col("div_cash")) / pl.col("adj_prev_close")).log(),
        intraday_ret=(pl.col("day_close") / pl.col("day_open")).log(),
    ).with_columns(
        rv_overnight=pl.col("overnight_ret") ** 2,
        ret_cc=pl.col("overnight_ret") + (pl.col("day_close") / pl.col("day_open")).log(),
    )

    out = (
        day.join(meas, on="date", how="inner")
        .with_columns(
            ticker=pl.lit(ticker),
            bar_count=pl.col("n_returns"),
            rth_rv=pl.col("rv_intraday"),
            total_rv=pl.col("rv_intraday") + pl.col("rv_overnight").fill_null(0.0),
            well_behaved=(pl.col("session") != "partial")
            & (pl.col("n_returns") >= C.MIN_BAR_FRACTION * pl.col("expected_bars")),
        )
        .select(
            "ticker", "date",
            "rv_intraday", "rth_rv", "rv_overnight", "total_rv",
            "bv", "jump", "rs_plus", "rs_minus", "rq",
            "overnight_ret", "ret_cc", "day_open", "day_close",
            "bar_count", "expected_bars", "session", "well_behaved",
        )
        .sort("date")
    )
    return out


if __name__ == "__main__":
    import sys

    tk = sys.argv[1] if len(sys.argv) > 1 else "SPY"
    df = daily_measures(tk)
    ann = (df["total_rv"] * C.TRADING_DAYS_PER_YEAR).sqrt()
    print(df.tail(5))
    print(f"\n{tk}: {df.height} days  {df['date'].min()}..{df['date'].max()}")
    print(f"  well-behaved: {df['well_behaved'].sum()} / {df.height}")
    print(f"  annualized total-vol: median={ann.median():.3f}  p05={ann.quantile(0.05):.3f}  p95={ann.quantile(0.95):.3f}")
