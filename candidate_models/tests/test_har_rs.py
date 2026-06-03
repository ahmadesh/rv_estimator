"""Smoke test for HAR-RS: synthetic 3-ticker x 500-day panel -> required columns, finite rv_hat."""

from __future__ import annotations

import datetime as dt

import numpy as np
import polars as pl

from candidate_models.har_rs import HARRS
from rv_eval import config as C
from rv_eval.features import HAR_RS_FEATURES

_REQUIRED_COLS = [
    "ticker", "date", "horizon", "rv_hat", "sigma",
    "q05", "q10", "q25", "q50", "q75", "q90", "q95",
]


def _synthetic_panel(n_days: int = 500):
    tickers = ["AAA", "BBB", "CCC"]
    dates = pl.date_range(dt.date(2010, 1, 1), dt.date(2015, 12, 31), interval="1d", eager=True)
    dates = dates.filter(dates.dt.weekday() <= 5)[:n_days]
    n = dates.len()
    rng = np.random.default_rng(0)

    x_rows, y_rows = [], []
    for tk in tickers:
        # HAR_RS features: log_rv_d, log_rv_w, log_rv_m, rs_minus_5d, rs_plus_5d, jump_5d.
        log_rv_d = rng.normal(-8.0, 0.5, n)
        rv_d = np.exp(log_rv_d)
        x_rows.append(pl.DataFrame({
            "ticker": [tk] * n, "date": dates,
            "log_rv_d": log_rv_d,
            "log_rv_w": log_rv_d + rng.normal(0, 0.1, n),
            "log_rv_m": log_rv_d + rng.normal(0, 0.1, n),
            "rs_minus_5d": 0.5 * rv_d * rng.uniform(0.8, 1.2, n),
            "rs_plus_5d": 0.5 * rv_d * rng.uniform(0.8, 1.2, n),
            "jump_5d": 0.1 * rv_d * rng.uniform(0.0, 1.0, n),
        }))
        for h in C.HORIZONS:
            y_rows.append(pl.DataFrame({
                "ticker": [tk] * n, "date": dates,
                "horizon": np.full(n, h, np.int32),
                "target_var": np.exp(log_rv_d + np.log(h) + rng.normal(0, 0.3, n)),
            }))
    return pl.concat(x_rows), pl.concat(y_rows)


def test_har_rs_predict_schema_and_finite():
    assert HARRS.needs == HAR_RS_FEATURES
    assert HARRS.name == "HAR-RS"
    X, y = _synthetic_panel()

    m = HARRS()
    m.fit(X, y)
    pred = m.predict(X)

    assert not pred.is_empty(), "HAR-RS produced no predictions on the synthetic panel"
    for col in _REQUIRED_COLS:
        assert col in pred.columns, f"missing required column: {col}"
    assert pred.select(_REQUIRED_COLS).columns == _REQUIRED_COLS

    rv_hat = pred["rv_hat"].to_numpy()
    assert np.isfinite(rv_hat).all(), "rv_hat must be finite"
    assert (rv_hat > 0).all(), "rv_hat must be positive (target_var units)"
    assert set(pred["horizon"].unique().to_list()) <= set(C.HORIZONS)
