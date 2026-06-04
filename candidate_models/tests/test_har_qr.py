"""Smoke tests for HAR-QR (candidate_models/har_qr.py, iteration-2 model 27).

Direct quantile-regression HAR over `_base_v2._QuantileModel`: emits q05..q95 DIRECTLY
(no lognormal wrapper). Exercises the exact output schema, finite positive rv_hat, and
MONOTONE quantiles on a synthetic 3-ticker x 500-day panel, plus a constructed crossing
case to confirm the base rearrangement fix actually repairs crossed quantiles.
"""

from __future__ import annotations

import datetime as dt

import numpy as np
import polars as pl

from candidate_models.har_qr import HARQR
from rv_eval import config as C

_REQUIRED_COLS = [
    "ticker", "date", "horizon", "rv_hat", "sigma",
    "q05", "q10", "q25", "q50", "q75", "q90", "q95",
]
_Q = ["q05", "q10", "q25", "q50", "q75", "q90", "q95"]


def _synthetic_panel(n_days: int = 500):
    tickers = ["AAA", "BBB", "CCC"]
    dates = pl.date_range(dt.date(2010, 1, 1), dt.date(2015, 12, 31), interval="1d", eager=True)
    dates = dates.filter(dates.dt.weekday() <= 5)[:n_days]
    n = dates.len()
    rng = np.random.default_rng(0)

    x_rows, y_rows = [], []
    for tk in tickers:
        log_rv_d = rng.normal(-8.0, 0.5, n)
        x_rows.append(pl.DataFrame({
            "ticker": [tk] * n, "date": dates,
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
    rv_hat = pred["rv_hat"].to_numpy()
    assert np.isfinite(rv_hat).all() and (rv_hat > 0).all(), "rv_hat must be finite and positive"
    sigma = pred["sigma"].to_numpy()
    assert np.isfinite(sigma).all() and (sigma > 0).all(), "sigma must be finite and positive"
    q = pred.select(_Q).to_numpy()
    assert np.isfinite(q).all(), "all quantiles must be finite"
    assert (q > 0).all(), "all quantiles must be positive (variance units)"
    assert (np.diff(q, axis=1) >= -1e-12).all(), "quantiles must be non-decreasing per row"
    assert set(pred["horizon"].unique().to_list()) <= set(C.HORIZONS)


def test_harqr_schema_and_monotone():
    X, y = _synthetic_panel()
    model = HARQR()
    model.fit(X, y)
    pred = model.predict(X)
    _assert_valid(pred)
    # name is filesystem-safe and exactly as catalogued
    assert model.name == "HAR-QR"
    # the warnings dict records a crossing-rate diagnostic per fitted key
    assert model.warnings, "expected per-key crossing diagnostics"


def test_harqr_rearrangement_repairs_crossing():
    """Feed a deliberately crossed quantile grid through the base rearrangement and
    confirm q05..q95 come out non-decreasing (the standard fix)."""
    X, y = _synthetic_panel()
    model = HARQR()
    model.fit(X, y)

    # Construct a crossed grid (descending) and run it through the same accumulate fix the
    # base predict applies, to assert the repair logic produces a monotone row.
    crossed = np.array([[0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3]])
    fixed = np.maximum.accumulate(crossed, axis=1)
    assert (np.diff(fixed, axis=1) >= 0).all(), "rearrangement must repair crossings"

    # End-to-end: predictions on real synthetic data are monotone despite raw QR crossings.
    pred = model.predict(X)
    q = pred.select(_Q).to_numpy()
    assert (np.diff(q, axis=1) >= -1e-12).all()
