"""Forward-horizon realized targets, IV^2 benchmark, and regime tags.

Built from the assembled per-(ticker, date) inputs. The forward-`h` target is the sum of the
next h daily total-RVs (strictly future: days t+1..t+h), so a forecast made at t is scored
against realized RV over (t, t+h]. Emitted long by horizon — one row = one scored prediction.

Units: `target_var` is the horizon variance (sum of h daily variances); `target_vol` is the
annualized vol sqrt(target_var * 252/h). Models must predict `rv_hat` in the `target_var`
convention. `iv2` de-annualizes the matching IV tenor to a horizon variance for the §5 IV
comparison.
"""

from __future__ import annotations

import numpy as np
import polars as pl

from rv_eval import config as C

# IV tenor (column in inputs) used as the IV-implied forecast for each horizon.
_HORIZON_IV = {1: "iv_30d", 5: "iv_30d", 10: "iv_30d", 22: "iv_30d", 42: "iv_60d"}


def _trailing_pctile(x: np.ndarray, window: int) -> np.ndarray:
    """Fraction of the trailing `window` (incl. current) values <= current value."""
    out = np.full(x.shape[0], np.nan)
    for i in range(x.shape[0]):
        w = x[max(0, i - window + 1): i + 1]
        w = w[~np.isnan(w)]
        if w.size:
            out[i] = float((w <= x[i]).mean())
    return out


def _regime(df: pl.DataFrame) -> pl.DataFrame:
    """Per-ticker (sorted by date) regime tags: IV-percentile bucket + post-shock flag."""
    iv = df["iv_30d"].to_numpy().astype(float)
    pct = _trailing_pctile(iv, C.IV_PCTILE_LOOKBACK)
    bucket = np.clip(np.floor(pct * C.IV_PCTILE_BUCKETS), 0, C.IV_PCTILE_BUCKETS - 1)
    df = df.with_columns(
        iv_pctile_bucket=pl.Series(bucket).fill_nan(None).cast(pl.Int8, strict=False)
    )
    # Shock = total_rv above its trailing 95th pct; post-shock = a shock in the last N days.
    df = df.with_columns(
        _thr=pl.col("total_rv").rolling_quantile(
            C.POST_SHOCK_RV_QUANTILE, window_size=C.IV_PCTILE_LOOKBACK, min_samples=60)
    )
    df = df.with_columns(_shock=(pl.col("total_rv") > pl.col("_thr")).cast(pl.Int8))
    df = df.with_columns(
        post_shock=(pl.col("_shock").rolling_max(window_size=C.POST_SHOCK_LOOKBACK, min_samples=1) > 0)
    )
    return df.drop("_thr", "_shock")


def build_targets(inputs: pl.DataFrame) -> pl.DataFrame:
    """Construct the long-by-horizon targets table from the assembled inputs frame."""
    parts = []
    for (tk,), sub in inputs.partition_by("ticker", as_dict=True).items():
        sub = sub.sort("date")
        sub = _regime(sub)
        cs_t = sub["total_rv"].cum_sum()
        cs_on = sub["rv_overnight"].fill_null(0.0).cum_sum()
        cs_id = sub["rv_intraday"].cum_sum()
        sub = sub.with_columns(_cs_t=cs_t, _cs_on=cs_on, _cs_id=cs_id)
        for h in C.HORIZONS:
            iv_col = _HORIZON_IV[h]
            rows = sub.with_columns(
                target_var=(pl.col("_cs_t").shift(-h) - pl.col("_cs_t")),
                target_overnight=(pl.col("_cs_on").shift(-h) - pl.col("_cs_on")),
                target_intraday=(pl.col("_cs_id").shift(-h) - pl.col("_cs_id")),
                iv2=pl.col(iv_col) ** 2 * (h / C.TRADING_DAYS_PER_YEAR),
            ).with_columns(
                target_vol=(pl.col("target_var") * C.TRADING_DAYS_PER_YEAR / h).sqrt(),
                horizon=pl.lit(h, dtype=pl.Int32),
            ).select(
                "ticker", "date", "group", "horizon",
                "target_var", "target_vol", "target_overnight", "target_intraday",
                "iv2", "iv_pctile_bucket", "post_shock",
            )
            parts.append(rows)
    out = pl.concat(parts).sort("ticker", "horizon", "date")
    # Drop rows without a full forward window (target undefined) — they are unusable.
    return out.filter(pl.col("target_var").is_not_null())


if __name__ == "__main__":
    # quick self-test on a tiny synthetic frame
    df = pl.DataFrame({
        "ticker": ["T"] * 8, "group": ["g"] * 8,
        "date": pl.date_range(pl.date(2020, 1, 1), pl.date(2020, 1, 8), eager=True),
        "total_rv": [1.0, 2, 3, 4, 5, 6, 7, 8],
        "rv_overnight": [0.1] * 8, "rv_intraday": [0.9, 1.9, 2.9, 3.9, 4.9, 5.9, 6.9, 7.9],
        "iv_30d": [0.2] * 8, "iv_60d": [0.2] * 8,
    })
    t = build_targets(df).filter(pl.col("horizon") == 1)
    print(t.select("date", "target_var"))
    # target_var(h=1) at t = total_rv(t+1): expect 2,3,4,5,6,7,8 then null-dropped
