"""Point-in-time trailing statistics — the leakage core of the gate thresholds.

Every threshold the gate uses (IVrank, dispersion percentile) is an *expanding* trailing statistic
that can see only rows dated <= t within each ticker, so appending a future row never changes a past
value. A window larger than any plausible per-ticker history turns polars' fixed-window rolling into
an expanding (all-prior-rows-incl-current) aggregation = exactly a point-in-time statistic.
"""

from __future__ import annotations

import numpy as np
import polars as pl

_EXPANDING = 10_000_000


def trailing_pctile(df: pl.DataFrame, value_col: str, q: float, *, by: str = "ticker",
                    date_col: str = "date", min_periods: int = 252,
                    out_col: str | None = None) -> pl.DataFrame:
    """Expanding (PIT) q-quantile of `value_col` within each `by` group.

    Row t = the q-quantile over all same-group rows dated <= t (current row included). Rows with
    fewer than `min_periods` of history get a null threshold so callers can decline to gate on an
    untrusted statistic.
    """
    out_col = out_col or f"{value_col}_p{int(q * 100)}"
    df = df.sort([by, date_col])
    return df.with_columns(
        pl.col(value_col)
        .rolling_quantile(quantile=q, interpolation="linear",
                          window_size=_EXPANDING, min_samples=min_periods)
        .over(by)
        .alias(out_col)
    )


def _expanding_rank(x: np.ndarray, min_periods: int) -> np.ndarray:
    """Expanding percentile rank of x[i] among the non-null values of x[:i+1].

    rank[i] = (#{j<=i : x[j] is finite and x[j] <= x[i]}) / (#{j<=i : x[j] is finite});
    NaN where x[i] is null or fewer than `min_periods` finite values have been seen. O(n log n)
    via an order-statistic count, robust to leading nulls (iv only exists once ORATS starts).
    """
    n = x.size
    out = np.full(n, np.nan)
    seen: list[float] = []                     # finite values so far, kept sorted
    import bisect
    for i in range(n):
        xi = x[i]
        if np.isfinite(xi):
            cnt = len(seen)                    # finite values strictly before i
            le = bisect.bisect_right(seen, xi) # how many seen-so-far are <= xi
            total = cnt + 1                     # include current
            if total >= min_periods:
                out[i] = (le + 1) / total       # +1 counts xi itself (<= xi)
            bisect.insort(seen, xi)
    return out


def trailing_rank(df: pl.DataFrame, value_col: str, *, by: str = "ticker",
                  date_col: str = "date", min_periods: int = 252,
                  out_col: str | None = None) -> pl.DataFrame:
    """Expanding (PIT) percentile RANK of `value_col` within each `by` group (in [0, 1]).

    Row t = fraction of same-group rows dated <= t whose (finite) value is <= the value at t. This
    is the IVrank used by gate G2 (today's iv_30d vs its own trailing-year history). Null before
    `min_periods` of trusted history, and on rows where the value itself is null.
    """
    out_col = out_col or f"{value_col}_rank"
    df = df.sort([by, date_col])
    parts = []
    for (_, sub) in df.group_by(by, maintain_order=True):
        x = sub[value_col].to_numpy().astype(float)
        parts.append(sub.with_columns(pl.Series(out_col, _expanding_rank(x, min_periods))))
    return pl.concat(parts, how="vertical")


def trailing_debias(df: pl.DataFrame, pred_col: str, target_col: str, *, embargo: int,
                    by: str = "ticker", date_col: str = "date", min_periods: int = 126,
                    out_col: str = "log_bias") -> pl.DataFrame:
    """Point-in-time per-ticker log-bias of a forecast vs its realised target (de-bias core, §10.B).

    EnsembleTopK `rv_hat` over-predicts forward RV on 2010+ (median log bias ≈ +0.27), which biases
    `vrp = iv2 − rv_hat` low and floors `vrp_rel` at 0.05 — suppressing the σ-sizer's gradation. This
    returns an expanding median of the *matured* log forecast error

        log_err = log(target_var) − log(rv_hat)              (negative when rv_hat over-predicts)

    using only forecasts whose h-day realisation has already closed: the error series is shifted
    forward `embargo` rows per ticker (= the forecast horizon) before the expanding median, so row t
    sees only forecasts dated ≤ t−h. The caller applies `rv_hat_cal = rv_hat · exp(log_bias)` (a
    downward correction when rv_hat ran high). Null (→ no correction) until `min_periods` matured obs.
    Leakage-safe: a future realisation never enters a past row.
    """
    df = df.sort([by, date_col])
    df = df.with_columns(
        _logerr=pl.when((pl.col(target_col) > 0) & (pl.col(pred_col) > 0))
        .then(pl.col(target_col).log() - pl.col(pred_col).log())
        .otherwise(None)
    )
    df = df.with_columns(_matured=pl.col("_logerr").shift(embargo).over(by))
    df = df.with_columns(
        pl.col("_matured")
        .rolling_median(window_size=_EXPANDING, min_samples=min_periods)
        .over(by)
        .alias(out_col)
    )
    return df.drop("_logerr", "_matured")


def trailing_rv(inputs: pl.DataFrame, h: int, *, by: str = "ticker", date_col: str = "date",
                rv_col: str = "total_rv", out_col: str = "trailing_rv") -> pl.DataFrame:
    """Point-in-time trailing realized variance over the past `h` trading days per ticker.

    Summing daily RV over [t-h+1, t] gives a realized-variance figure in the same horizon-variance
    units as `iv2`, known at t and using no future data. This is the rv_hat the degraded GFC book
    sells against (vrp = iv2 - trailing_RV) in place of the forecaster.
    """
    inputs = inputs.sort([by, date_col])
    return inputs.with_columns(
        pl.col(rv_col).rolling_sum(window_size=h, min_samples=h).over(by).alias(out_col)
    )
