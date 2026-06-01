"""Optional model-side feature builder: expand the inputs base store into a wide,
parameterized, point-in-time feature matrix that a model selects among.

Every column uses only data at-or-before its row's date (trailing rolling windows), so building
this on the full series before the walk-forward split introduces no leakage. Models may use these
columns, ignore them, or add their own; the benchmarks in `model_contract.py` consume them.
"""

from __future__ import annotations

import polars as pl

from rv_eval import config as C

EWMA_LAMBDA = 0.94          # RiskMetrics decay for the EWMA-RV feature
HAR_WINDOWS = (5, 22, 66)   # week / month / quarter HAR component windows


def _roll_mean(col: str, w: int) -> pl.Expr:
    return pl.col(col).rolling_mean(window_size=w, min_samples=w).over("ticker").alias(f"{col}_{w}d")


def build_features(inputs: pl.DataFrame) -> pl.DataFrame:
    """Augment the inputs frame with HAR/EWMA/semivariance/IV-transform features."""
    df = inputs.sort("ticker", "date")

    df = df.with_columns(
        rv_d=pl.col("total_rv"),
        # HAR component averages (trailing, include today)
        *[_roll_mean("total_rv", w) for w in HAR_WINDOWS],
        rs_minus_5d=pl.col("rs_minus").rolling_mean(5, min_samples=5).over("ticker"),
        rs_plus_5d=pl.col("rs_plus").rolling_mean(5, min_samples=5).over("ticker"),
        jump_5d=pl.col("jump").rolling_mean(5, min_samples=5).over("ticker"),
        sqrt_rq=pl.col("rq").clip(lower_bound=0.0).sqrt(),
        ewma_rv=pl.col("total_rv").ewm_mean(alpha=1.0 - EWMA_LAMBDA, adjust=False).over("ticker"),
    )
    # Standard HAR names: rv_w (5d), rv_m (22d), rv_q (66d).
    df = df.rename({"total_rv_5d": "rv_w", "total_rv_22d": "rv_m", "total_rv_66d": "rv_q"})

    # Log transforms (variance is multiplicative / right-skewed; log space stabilises HAR).
    for src, dst in (("rv_d", "log_rv_d"), ("rv_w", "log_rv_w"),
                     ("rv_m", "log_rv_m"), ("rv_q", "log_rv_q"), ("iv_30d", "log_iv")):
        df = df.with_columns(pl.col(src).clip(lower_bound=1e-12).log().alias(dst))

    return df


# Convenience column groups a model (or benchmark) can request.
HAR_FEATURES = ["log_rv_d", "log_rv_w", "log_rv_m"]
HARQ_FEATURES = HAR_FEATURES + ["sqrt_rq"]
HAR_RS_FEATURES = ["log_rv_d", "log_rv_w", "log_rv_m", "rs_minus_5d", "rs_plus_5d", "jump_5d"]
IV_FEATURES = ["log_iv", "iv_slope", "skew_25d", "vix", "vix3m", "vix_slope", "vvix"]


def cached_features() -> pl.DataFrame:
    """Build (and cache) the feature matrix from the inputs panel."""
    inputs = pl.read_parquet(C.INPUTS_PARQUET)
    feats = build_features(inputs)
    feats.write_parquet(C.FEATURES_PARQUET)
    return feats


if __name__ == "__main__":
    f = cached_features()
    print(f"features: {f.height:,} rows, {len(f.columns)} cols -> {C.FEATURES_PARQUET}")
    print([c for c in f.columns if c not in pl.read_parquet(C.INPUTS_PARQUET).columns])
