"""Smoke tests for STAR-HAR (candidate_models/star_har.py, catalog model 30).

Synthetic 3-ticker x 500-day panel. Asserts the exact output schema, finite positive
rv_hat, monotone quantiles, that the logistic transition weight is in [0, 1], and that the
HAR x transition-weight interaction columns are built and joined into X.
"""

from __future__ import annotations

import datetime as dt

import numpy as np
import polars as pl

from candidate_models.star_har import (
    STARHAR,
    _INTERACT,
    _STATE_COL,
    _WEIGHT_COL,
    _star_panel,
)
from rv_eval import config as C
from rv_eval.features import HAR_FEATURES

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
        log_rv_d = rng.normal(-8.0, 0.5, n)
        x_rows.append(pl.DataFrame({
            "ticker": [tk] * n, "date": dates,
            "log_rv_d": log_rv_d,
            "log_rv_w": log_rv_d + rng.normal(0, 0.1, n),
            "log_rv_m": log_rv_d + rng.normal(0, 0.1, n),
            "vix": np.exp(rng.normal(2.9, 0.3, n)),   # ~18 mean VIX, the transition state source
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


def test_star_har_schema():
    X, y = _synthetic_panel()
    m = STARHAR()
    m.fit(X, y)
    pred = m.predict(X)
    _assert_valid(pred)


def test_transition_weight_in_unit_interval():
    X, _ = _synthetic_panel()
    panel = _star_panel(X)
    g = panel[_WEIGHT_COL].to_numpy()
    g = g[np.isfinite(g)]
    assert g.size > 0
    assert (g >= 0.0).all() and (g <= 1.0).all(), "logistic transition weight must be in [0, 1]"
    # The expanding percentile state is itself in (0, 1].
    p = panel[_STATE_COL].to_numpy()
    p = p[np.isfinite(p)]
    assert (p > 0.0).all() and (p <= 1.0 + 1e-9).all()


def test_interaction_columns_built_and_joined():
    X, _ = _synthetic_panel()
    m = STARHAR()
    attached = m._attach(X)
    # Interaction columns + state column are joined into X (not in raw X).
    for c in _INTERACT + [_STATE_COL]:
        assert c not in X.columns
        assert c in attached.columns, f"{c} not joined into X"
    # Each interaction equals base HAR feature * transition weight.
    for f, name in zip(HAR_FEATURES, _INTERACT):
        lhs = attached[name].to_numpy()
        rhs = (attached[f].to_numpy() * attached[_WEIGHT_COL].to_numpy())
        ok = np.isfinite(lhs) & np.isfinite(rhs)
        assert np.allclose(lhs[ok], rhs[ok]), f"{name} != {f} * {_WEIGHT_COL}"


def test_expanding_pctile_is_trailing():
    # The expanding percentile must be point-in-time: the first row is always 1.0
    # (it is the only/largest seen so far), and the global max row is 1.0.
    X, _ = _synthetic_panel()
    panel = _star_panel(X).sort("ticker", "date")
    first = panel.group_by("ticker").first()
    assert np.allclose(first[_STATE_COL].to_numpy(), 1.0)
