"""Smoke test for LHAR (leverage-HAR): synthetic 3-ticker x 500-day panel.

Asserts predict returns the required columns, finite rv_hat>0, monotone
quantiles. The panel carries raw `ret_cc` (as in inputs.parquet) plus the
HAR_FEATURES; LHAR derives lev_d/w/m (signed downside-return roll-means)
internally on the full series via _AttachMixin. We include positive returns to
verify they are floored to 0 (only the downside matters).
"""

from __future__ import annotations

import datetime as dt

import numpy as np
import polars as pl

from candidate_models.lhar import LHAR, _LEV_FEATURES
from rv_eval import config as C
from rv_eval.features import HAR_FEATURES

_REQUIRED_COLS = [
    "ticker", "date", "horizon", "rv_hat", "sigma",
    "q05", "q10", "q25", "q50", "q75", "q90", "q95",
]
_Q_GRID = ["q05", "q10", "q25", "q50", "q75", "q90", "q95"]


def _synthetic_panel(n_days: int = 500):
    tickers = ["AAA", "BBB", "CCC"]
    dates = pl.date_range(dt.date(2010, 1, 1), dt.date(2015, 12, 31), interval="1d", eager=True)
    dates = dates.filter(dates.dt.weekday() <= 5)[:n_days]
    n = dates.len()
    rng = np.random.default_rng(0)

    x_rows, y_rows = [], []
    for tk in tickers:
        log_rv_d = rng.normal(-8.0, 0.5, n)
        # Close-to-close returns: mix of up/down days to exercise the min(ret_cc,0) floor.
        ret_cc = rng.normal(0.0, 0.012, n)
        x_rows.append(pl.DataFrame({
            "ticker": [tk] * n, "date": dates,
            "log_rv_d": log_rv_d,
            "log_rv_w": log_rv_d + rng.normal(0, 0.1, n),
            "log_rv_m": log_rv_d + rng.normal(0, 0.1, n),
            "ret_cc": ret_cc,
        }))
        for h in C.HORIZONS:
            y_rows.append(pl.DataFrame({
                "ticker": [tk] * n, "date": dates,
                "horizon": np.full(n, h, np.int32),
                "target_var": np.exp(log_rv_d + np.log(h) + rng.normal(0, 0.3, n)),
            }))
    return pl.concat(x_rows), pl.concat(y_rows)


def test_lhar_predict_schema_and_finite():
    assert LHAR.name == "LHAR"
    assert LHAR.needs == HAR_FEATURES + _LEV_FEATURES
    X, y = _synthetic_panel()

    m = LHAR()
    m.fit(X, y)
    pred = m.predict(X)

    assert not pred.is_empty(), "LHAR produced no predictions on the synthetic panel"
    for col in _REQUIRED_COLS:
        assert col in pred.columns, f"missing required column: {col}"
    assert pred.select(_REQUIRED_COLS).columns == _REQUIRED_COLS

    rv_hat = pred["rv_hat"].to_numpy()
    assert np.isfinite(rv_hat).all(), "rv_hat must be finite"
    assert (rv_hat > 0).all(), "rv_hat must be positive (target_var units)"
    assert set(pred["horizon"].unique().to_list()) <= set(C.HORIZONS)

    # Quantiles must be non-decreasing across the grid, row by row.
    qmat = pred.select(_Q_GRID).to_numpy()
    assert np.all(np.diff(qmat, axis=1) >= -1e-12), "quantiles must be non-decreasing"


def test_lhar_downside_only():
    """lev_* aggregates the *downside* return only: positive ret_cc -> 0 contribution."""
    src = pl.DataFrame({
        "ticker": ["AAA"] * 5,
        "date": pl.date_range(dt.date(2010, 1, 1), dt.date(2010, 1, 5), interval="1d", eager=True),
        "ret_cc": [0.02, -0.01, 0.03, -0.04, 0.05],
    })
    from candidate_models.lhar import _lev_panel
    tab = _lev_panel(src).sort("date")
    # lev_d on day 1 (ret=+0.02) is floored to 0; day 2 (ret=-0.01) is -0.01.
    assert tab["lev_d"][0] == 0.0
    assert abs(tab["lev_d"][1] - (-0.01)) < 1e-12
