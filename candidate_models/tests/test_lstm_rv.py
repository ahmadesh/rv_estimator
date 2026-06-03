"""Smoke test for LSTMRV: synthetic 3-ticker x 500-day panel -> required columns, finite rv_hat.

Kept small/fast: the network is shrunk (tiny hidden, few epochs) by overriding the
frozen class constants on a subclass so the test runs in seconds.
"""

from __future__ import annotations

import datetime as dt

import numpy as np
import polars as pl

from candidate_models import lstm_rv
from candidate_models.lstm_rv import LSTMRV, WINDOW_FEATURES
from rv_eval import config as C

_REQUIRED_COLS = [
    "ticker", "date", "horizon", "rv_hat", "sigma",
    "q05", "q10", "q25", "q50", "q75", "q90", "q95",
]


class _TinyLSTMRV(LSTMRV):
    """Shrunk variant so the smoke test is fast."""
    HIDDEN = 8
    NUM_LAYERS = 1
    DROPOUT = 0.0
    LR = 1e-2


def _synthetic_panel(n_days: int = 500):
    tickers = ["AAA", "BBB", "CCC"]
    dates = pl.date_range(dt.date(2010, 1, 1), dt.date(2016, 12, 31), interval="1d", eager=True)
    dates = dates.filter(dates.dt.weekday() <= 5)[:n_days]
    n = dates.len()
    rng = np.random.default_rng(0)

    x_rows, y_rows = [], []
    for tk in tickers:
        log_rv_d = rng.normal(-8.0, 0.5, n)
        rv_d = np.exp(log_rv_d)
        cols = {
            "ticker": [tk] * n, "date": dates,
            "log_rv_d": log_rv_d,
            "log_iv": log_rv_d + rng.normal(0, 0.2, n),
            "vix": np.abs(rng.normal(18, 4, n)),
            "vix_slope": rng.normal(0, 1.0, n),
            "iv_slope": rng.normal(0, 0.05, n),
            "skew_25d": rng.normal(0, 0.1, n),
            "rs_minus_5d": 0.5 * rv_d * rng.uniform(0.8, 1.2, n),
            "rs_plus_5d": 0.5 * rv_d * rng.uniform(0.8, 1.2, n),
        }
        x_rows.append(pl.DataFrame(cols))
        for h in C.HORIZONS:
            y_rows.append(pl.DataFrame({
                "ticker": [tk] * n, "date": dates,
                "horizon": np.full(n, h, np.int32),
                "target_var": np.exp(log_rv_d + np.log(h) + rng.normal(0, 0.3, n)),
            }))
    return pl.concat(x_rows), pl.concat(y_rows)


def test_needs_and_window_features():
    assert LSTMRV.name == "LSTMRV"
    assert LSTMRV.needs == WINDOW_FEATURES
    assert WINDOW_FEATURES == [
        "log_rv_d", "log_iv", "vix", "vix_slope", "iv_slope",
        "skew_25d", "rs_minus_5d", "rs_plus_5d",
    ]
    # device must resolve to a real torch device (mps or cpu)
    assert lstm_rv.DEVICE.type in ("mps", "cpu")


def test_lstm_predict_schema_and_finite():
    X, y = _synthetic_panel()

    m = _TinyLSTMRV()
    # epochs are read from the module constant; shrink it for a fast smoke run
    orig = lstm_rv.MAX_EPOCHS
    lstm_rv.MAX_EPOCHS = 2
    try:
        m.fit(X, y)
        pred = m.predict(X)
    finally:
        lstm_rv.MAX_EPOCHS = orig

    assert not pred.is_empty(), "LSTMRV produced no predictions on the synthetic panel"
    for col in _REQUIRED_COLS:
        assert col in pred.columns, f"missing required column: {col}"
    assert pred.select(_REQUIRED_COLS).columns == _REQUIRED_COLS

    rv_hat = pred["rv_hat"].to_numpy()
    assert np.isfinite(rv_hat).all(), "rv_hat must be finite"
    assert (rv_hat > 0).all(), "rv_hat must be positive (target_var units)"
    assert set(pred["horizon"].unique().to_list()) <= set(C.HORIZONS)


def test_lstm_walkforward_slice_contract():
    """Reproduce the harness's slice contract: predict() gets ONLY a short test month
    (n < WINDOW=60) per ticker, with no in-slice 60-day history. Before the context-
    caching fix this returned an empty frame (every fold all-NaN -> empty parquet).
    """
    X, y = _synthetic_panel(n_days=360)

    # split like the walk-forward: fit on the first ~330 days, predict on the LAST ~21.
    all_dates = X["date"].unique().sort()
    n_test = 21
    test_dates = all_dates[-n_test:]
    train_cut = all_dates[-n_test]  # first test date

    X_train = X.filter(pl.col("date") < train_cut)
    y_train = y.filter(pl.col("date") < train_cut)
    X_test = X.filter(pl.col("date").is_in(test_dates.to_list()))

    # sanity: each ticker's test slice is shorter than WINDOW (the bug trigger)
    per_ticker = X_test.group_by("ticker").len()["len"].to_list()
    assert all(c < lstm_rv.WINDOW for c in per_ticker), per_ticker

    m = _TinyLSTMRV()
    orig = lstm_rv.MAX_EPOCHS
    lstm_rv.MAX_EPOCHS = 2
    try:
        m.fit(X_train, y_train)
        pred = m.predict(X_test)
    finally:
        lstm_rv.MAX_EPOCHS = orig

    assert not pred.is_empty(), "LSTMRV produced NO predictions on the short test slice (the bug)"
    for col in _REQUIRED_COLS:
        assert col in pred.columns, f"missing required column: {col}"
    rv_hat = pred["rv_hat"].to_numpy()
    assert np.isfinite(rv_hat).all(), "rv_hat must be finite on the test slice"
    assert (rv_hat > 0).all(), "rv_hat must be positive (target_var units)"
    # predictions must land on the test dates only, one per (ticker, horizon, date)
    assert set(pred["date"].unique().to_list()) <= set(test_dates.to_list())
    assert set(pred["horizon"].unique().to_list()) <= set(C.HORIZONS)
