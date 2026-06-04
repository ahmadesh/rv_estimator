"""Smoke tests for HAR-GVF (`candidate_models/har_globalfactor.py`, catalog model 24).

Synthetic 3-ticker x 500-day panel. Asserts the exact output schema, finite positive
rv_hat, monotone quantiles, and — the model-specific invariant — that the global
volatility factor (`log_gvf`) is BUILT and IDENTICAL across tickers on any given date.
"""

from __future__ import annotations

import datetime as dt

import numpy as np
import polars as pl

from candidate_models.har_globalfactor import HARGlobalFactor, _gvf_panel
from rv_eval import config as C

_REQUIRED_COLS = [
    "ticker", "date", "horizon", "rv_hat", "sigma",
    "q05", "q10", "q25", "q50", "q75", "q90", "q95",
]


def _synthetic_panel(n_days: int = 500, tickers=("AAA", "BBB", "CCC")):
    dates = pl.date_range(dt.date(2010, 1, 1), dt.date(2015, 12, 31), interval="1d", eager=True)
    dates = dates.filter(dates.dt.weekday() <= 5)[:n_days]
    n = dates.len()
    rng = np.random.default_rng(0)

    x_rows, y_rows = [], []
    for tk in tickers:
        log_rv_d = rng.normal(-8.0, 0.5, n)
        total_rv = np.exp(log_rv_d)
        x_rows.append(pl.DataFrame({
            "ticker": [tk] * n, "date": dates,
            "total_rv": total_rv,                          # GVF basket source column
            "log_rv_d": log_rv_d,
            "log_rv_w": log_rv_d + rng.normal(0, 0.1, n),
            "log_rv_m": log_rv_d + rng.normal(0, 0.1, n),
        }))
        for h in C.HORIZONS:
            y_rows.append(pl.DataFrame({
                "ticker": [tk] * n, "date": dates,
                "horizon": np.full(n, h, np.int32),
                "target_var": np.exp(log_rv_d + np.log(h) + rng.normal(0, 0.3, n)),
            }))
    return pl.concat(x_rows), pl.concat(y_rows)


def _assert_valid(pred: pl.DataFrame):
    assert not pred.is_empty(), "model produced no predictions"
    for col in _REQUIRED_COLS:
        assert col in pred.columns, f"missing required column: {col}"
    assert pred.select(_REQUIRED_COLS).columns == _REQUIRED_COLS
    rv_hat = pred["rv_hat"].to_numpy()
    assert np.isfinite(rv_hat).all() and (rv_hat > 0).all(), "rv_hat must be finite and positive"
    q = pred.select("q05", "q10", "q25", "q50", "q75", "q90", "q95").to_numpy()
    assert (np.diff(q, axis=1) >= -1e-9).all(), "quantiles must be non-decreasing"
    assert set(pred["horizon"].unique().to_list()) <= set(C.HORIZONS)


def test_schema_finite_monotone():
    X, y = _synthetic_panel()
    m = HARGlobalFactor()
    m.fit(X, y)
    pred = m.predict(X)
    _assert_valid(pred)


def test_global_factor_built_and_identical_across_tickers():
    X, y = _synthetic_panel()
    m = HARGlobalFactor()
    attached = m._attach(X)
    assert "log_gvf" in attached.columns, "global factor column must be built"
    assert "log_gvf" not in X.columns, "factor is derived, not a raw X column"
    # On every date the factor must be identical across all tickers (joined by date).
    spread = (
        attached.group_by("date")
        .agg((pl.col("log_gvf").max() - pl.col("log_gvf").min()).alias("rng"))
    )
    assert spread["rng"].max() <= 1e-12, "global factor must be identical across tickers per date"
    # And it must be the cross-sectional mean of total_rv (in log space).
    expect = (
        X.group_by("date").agg(pl.col("total_rv").mean().alias("gvf"))
        .with_columns(exp_log=pl.col("gvf").log())
    )
    got = attached.group_by("date").agg(pl.col("log_gvf").first()).join(expect, on="date")
    assert np.allclose(got["log_gvf"].to_numpy(), got["exp_log"].to_numpy(), atol=1e-9)


def test_basket_restricted_to_clean_core():
    # A panel containing BOTH a clean-core name and a hard-case name: the factor must be
    # computed from the clean-core basket ONLY (hard names never contaminate it).
    X, _ = _synthetic_panel(tickers=("SPY", "UVXY"))
    tab = _gvf_panel(X)
    # Factor == SPY's own total_rv (the only clean-core name in the basket), NOT the
    # SPY/UVXY average.
    spy = X.filter(pl.col("ticker") == "SPY").with_columns(pl.col("total_rv").log().alias("spy_log"))
    merged = tab.unique(subset=["date"]).join(spy.select("date", "spy_log"), on="date")
    assert np.allclose(merged["log_gvf"].to_numpy(), merged["spy_log"].to_numpy(), atol=1e-9), \
        "GVF basket must exclude hard-case tickers (clean_core only)"
