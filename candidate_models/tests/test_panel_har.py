"""Smoke tests for PanelHAR-FE (candidate_models/panel_har.py, catalog model 22).

Synthetic 3-ticker x 500-day panel carrying the full pooled feature set (HAR-RS + IV). Asserts:
the exact output schema, finite positive rv_hat, monotone quantiles, that pooling produces ONE
shared slope vector per horizon with a per-ticker intercept, and that a test ticker unseen in
fit still predicts via the group/global-mean intercept fallback (never errors).

Run by explicit path:
    .venv/bin/python -m pytest candidate_models/tests/test_panel_har.py -q
"""

from __future__ import annotations

import datetime as dt

import numpy as np
import polars as pl

from candidate_models.panel_har import PanelHARFE
from rv_eval import config as C
from rv_eval.features import HAR_RS_FEATURES, IV_FEATURES

_REQUIRED_COLS = [
    "ticker", "date", "horizon", "rv_hat", "sigma",
    "q05", "q10", "q25", "q50", "q75", "q90", "q95",
]
_NEEDS = HAR_RS_FEATURES + IV_FEATURES


def _synthetic_panel(n_days: int = 500):
    tickers = ["AAA", "BBB", "CCC"]
    dates = pl.date_range(dt.date(2010, 1, 1), dt.date(2016, 12, 31), interval="1d", eager=True)
    dates = dates.filter(dates.dt.weekday() <= 5)[:n_days]
    n = dates.len()
    rng = np.random.default_rng(0)

    x_rows, y_rows = [], []
    for lvl, tk in enumerate(tickers):
        # Ticker-specific level (-8, -7.5, -7) -> exercises the fixed-effect intercepts.
        log_rv_d = rng.normal(-8.0 + 0.5 * lvl, 0.5, n)
        feats = {
            "log_rv_d": log_rv_d,
            "log_rv_w": log_rv_d + rng.normal(0, 0.1, n),
            "log_rv_m": log_rv_d + rng.normal(0, 0.1, n),
            "rs_minus_5d": np.exp(log_rv_d) * rng.uniform(0.3, 0.7, n),
            "rs_plus_5d": np.exp(log_rv_d) * rng.uniform(0.3, 0.7, n),
            "jump_5d": np.exp(log_rv_d) * rng.uniform(0.0, 0.2, n),
            "log_iv": log_rv_d * 0.5 - 3.0 + rng.normal(0, 0.1, n),
            "iv_slope": rng.normal(0.0, 0.02, n),
            "skew_25d": rng.normal(0.0, 0.05, n),
            "vix": rng.uniform(12.0, 30.0, n),
            "vix3m": rng.uniform(13.0, 28.0, n),
            "vix_slope": rng.normal(0.0, 0.5, n),
            "vvix": rng.uniform(80.0, 120.0, n),
        }
        assert set(feats) == set(_NEEDS)
        x_rows.append(pl.DataFrame({"ticker": [tk] * n, "date": dates, **feats}))
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


def test_schema_and_pooling():
    X, y = _synthetic_panel()
    m = PanelHARFE()
    m.fit(X, y)
    pred = m.predict(X)
    _assert_valid(pred)
    # name preserved exactly (becomes the prediction filename / card path).
    assert m.name == "PanelHAR-FE"
    # One pooled fit per horizon: a single shared slope vector + per-ticker FE intercepts.
    st = m.state[C.PRIMARY_HORIZON]
    assert len(st["slopes"]) == len(_NEEDS)
    assert set(st["intercepts"]) == {"AAA", "BBB", "CCC"}


def test_unseen_ticker_falls_back_to_pooled_intercept():
    X, y = _synthetic_panel()
    m = PanelHARFE()
    m.fit(X, y)
    # A ticker never seen in fit must still predict (group-mean then global-mean intercept),
    # never error.
    unseen = X.filter(pl.col("ticker") == "AAA").with_columns(ticker=pl.lit("ZZZ"))
    pred = m.predict(unseen)
    _assert_valid(pred)
    assert set(pred["ticker"].unique().to_list()) == {"ZZZ"}
