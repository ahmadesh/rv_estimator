"""Smoke test for model 28 — VRP-Spread (direct-quantile head).

Synthetic 3-ticker x 500-day panel; asserts the predict output schema, finite positive
rv_hat, MONOTONE quantiles (the critical direct-quantile contract), and that the derived
trailing VRP columns are joined into X rather than recomputed on the slice.
"""

from __future__ import annotations

import datetime as dt

import numpy as np
import polars as pl

from candidate_models.vrp_spread import VRPSpread, _VRP_FEATURES
from rv_eval import config as C

_REQUIRED_COLS = [
    "ticker", "date", "horizon", "rv_hat", "sigma",
    "q05", "q10", "q25", "q50", "q75", "q90", "q95",
]


def _synthetic_panel(n_days: int = 500):
    tickers = ["AAA", "BBB", "CCC"]
    dates = pl.date_range(dt.date(2010, 1, 1), dt.date(2015, 12, 31), interval="1d", eager=True)
    dates = dates.filter(dates.dt.weekday() <= 5)[:n_days]
    n = dates.len()
    rng = np.random.default_rng(7)

    x_rows, y_rows = [], []
    for tk in tickers:
        iv_30d = np.abs(rng.normal(0.20, 0.05, n)) + 0.05         # plausible IV level
        total_rv = np.abs(rng.normal(iv_30d ** 2 / 252.0, 1e-4, n)) + 1e-6
        x_rows.append(pl.DataFrame({
            "ticker": [tk] * n, "date": dates,
            "iv_30d": iv_30d,
            "iv_60d": iv_30d + rng.normal(0.005, 0.005, n),
            "iv_90d": iv_30d + rng.normal(0.010, 0.005, n),
            "vix9d_slope": rng.normal(0.0, 0.02, n),
            "total_rv": total_rv,                                  # for _derive fallback
        }))
        for h in C.HORIZONS:
            # realized var over h days ~ h * daily var, with VRP-like discount + noise
            tv = h * (iv_30d ** 2 / 252.0) * np.abs(rng.normal(0.8, 0.2, n)) + 1e-6
            y_rows.append(pl.DataFrame({
                "ticker": [tk] * n, "date": dates,
                "horizon": np.full(n, h, np.int32),
                "target_var": tv,
            }))
    return pl.concat(x_rows), pl.concat(y_rows)


def _assert_valid(pred: pl.DataFrame):
    assert not pred.is_empty(), "model produced no predictions"
    for col in _REQUIRED_COLS:
        assert col in pred.columns, f"missing required column: {col}"
    assert pred.select(_REQUIRED_COLS).columns == _REQUIRED_COLS
    rv_hat = pred["rv_hat"].to_numpy()
    assert np.isfinite(rv_hat).all() and (rv_hat > 0).all(), "rv_hat must be finite and positive"
    sigma = pred["sigma"].to_numpy()
    assert np.isfinite(sigma).all() and (sigma >= 0).all(), "sigma must be finite and non-negative"
    q = pred.select("q05", "q10", "q25", "q50", "q75", "q90", "q95").to_numpy()
    assert np.isfinite(q).all(), "quantiles must be finite"
    assert (q > 0).all(), "quantiles must be positive"
    assert (np.diff(q, axis=1) >= -1e-9).all(), "quantiles must be non-decreasing (MONOTONE)"
    assert set(pred["horizon"].unique().to_list()) <= set(C.HORIZONS)


def test_vrp_spread_schema_and_monotone_quantiles():
    X, y = _synthetic_panel()
    m = VRPSpread()
    m.fit(X, y)
    pred = m.predict(X)
    _assert_valid(pred)


def test_vrp_spread_derives_and_joins():
    X, y = _synthetic_panel()
    m = VRPSpread()
    # Derived trailing-VRP columns are NOT in raw X; they are joined by _attach.
    for c in _VRP_FEATURES:
        assert c not in X.columns
    attached = m._attach(X)
    for c in _VRP_FEATURES:
        assert c in attached.columns
