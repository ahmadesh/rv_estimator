"""Smoke test for HAR-SJ (signed-jump HAR), candidate_models/har_sj.py model 14.

Synthetic 3-ticker x 500-day panel. Asserts the exact output schema, finite positive
rv_hat, and monotone quantiles, and that the derived signed-jump columns are joined into
X (the _AttachMixin fallback path, where X itself is the full series).
"""

from __future__ import annotations

import datetime as dt

import numpy as np
import polars as pl

from candidate_models.har_sj import HARSJ, _SJ_FEATURES
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
    rng = np.random.default_rng(14)

    x_rows, y_rows = [], []
    for tk in tickers:
        log_rv_d = rng.normal(-8.0, 0.5, n)
        rv = np.exp(log_rv_d)
        # Realized semivariances summing roughly to total RV, with a mild sign asymmetry.
        rs_plus = rv * rng.uniform(0.3, 0.7, n)
        rs_minus = rv - rs_plus
        x = pl.DataFrame({
            "ticker": [tk] * n, "date": dates,
            "log_rv_d": log_rv_d,
            "log_rv_w": log_rv_d + rng.normal(0, 0.1, n),
            "log_rv_m": log_rv_d + rng.normal(0, 0.1, n),
            "rs_plus": rs_plus,
            "rs_minus": rs_minus,
        })
        # Weekly semivariance roll-means that features.build_features would supply on X.
        x = x.with_columns(
            rs_plus_5d=pl.col("rs_plus").rolling_mean(5, min_samples=5).over("ticker"),
            rs_minus_5d=pl.col("rs_minus").rolling_mean(5, min_samples=5).over("ticker"),
        )
        x_rows.append(x)
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


def test_har_sj_schema_and_quantiles():
    X, y = _synthetic_panel()
    m = HARSJ()
    m.fit(X, y)
    pred = m.predict(X)
    _assert_valid(pred)


def test_har_sj_derives_and_joins():
    X, _ = _synthetic_panel()
    m = HARSJ()
    attached = m._attach(X)
    for c in _SJ_FEATURES:
        assert c not in X.columns, f"{c} must be derived, not raw"
        assert c in attached.columns, f"{c} must be joined into X"
    # abs_sj_5d is the magnitude of sj_5d wherever both are defined.
    chk = attached.drop_nulls(_SJ_FEATURES)
    assert chk.height > 0
    diff = (chk["abs_sj_5d"] - chk["sj_5d"].abs()).abs().max()
    assert diff < 1e-12
