"""Point-in-time helpers — the leakage core of the trading layer.

The walk-forward purge/embargo is already baked into the frozen predictions, so the *only*
new leakage surface in Stage-1 is strategy thresholds. Every threshold this layer computes
must use **only rows dated <= t** — never the full OOS sample. These helpers enforce that:
they are pure (sorted, trailing/expanding) and are the single place the no-look-ahead property
is asserted, so `tests/test_leakage.py` can pin it down by checking that appending a future row
never changes a past output.
"""

from __future__ import annotations

import polars as pl

# A window larger than any plausible per-ticker history turns polars' fixed-window rolling
# aggregations into an *expanding* (all-prior-rows-incl-current) aggregation — which is exactly
# a trailing/point-in-time statistic: it can see the present and the past, never the future.
_EXPANDING = 10_000_000


def trailing_pctile(
    df: pl.DataFrame,
    value_col: str,
    q: float,
    *,
    by: str = "ticker",
    date_col: str = "date",
    min_periods: int = 252,
    out_col: str | None = None,
) -> pl.DataFrame:
    """Expanding (point-in-time) q-quantile of ``value_col`` within each ``by`` group.

    The value at row t is the q-quantile over all rows of the same group dated <= t (the current
    row included — that uses the present, not the future). Rows before ``min_periods`` of history
    get a null threshold so callers can decline to gate on an untrusted statistic. No pre-OOS
    seeding is possible here because the quantity (e.g. forecast dispersion) only exists on the
    OOS prediction rows; the trailing-expanding basis is the §6-sanctioned alternative.
    """
    out_col = out_col or f"{value_col}_p{int(q * 100)}"
    df = df.sort([by, date_col])
    return df.with_columns(
        pl.col(value_col)
        .rolling_quantile(
            quantile=q, interpolation="linear", window_size=_EXPANDING, min_samples=min_periods
        )
        .over(by)
        .alias(out_col)
    )


def trailing_rv(
    inputs: pl.DataFrame,
    h: int,
    *,
    by: str = "ticker",
    date_col: str = "date",
    rv_col: str = "total_rv",
    out_col: str = "trailing_rv",
) -> pl.DataFrame:
    """Point-in-time trailing realized variance over the past ``h`` trading days per ticker.

    Summing the daily RV over [t-h+1, t] gives a realized-variance figure in the same
    horizon-variance units as ``iv2`` / ``target_var``, known at t and using no future data.
    This is the realized comparator the IV-only benchmark sells against (vrp = iv2 - trailing_RV).
    """
    inputs = inputs.sort([by, date_col])
    return inputs.with_columns(
        pl.col(rv_col)
        .rolling_sum(window_size=h, min_samples=h)
        .over(by)
        .alias(out_col)
    )
