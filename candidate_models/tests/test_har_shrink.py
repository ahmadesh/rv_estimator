"""Smoke test for HAR-ENet / HAR-Ridge (model 19): synthetic 3-ticker x 500-day panel.

Asserts, for EACH class, that predict returns the required schema, finite rv_hat>0, and
monotone quantiles. The panel carries the raw columns the model's `_derive` needs (ret_cc,
rs_plus, rs_minus, iv_30d/60d/90d, total_rv, parkinson, gk, volume, transactions,
rv_overnight) plus the non-derived X feature columns in `needs` (HAR_RS_FEATURES,
IV_FEATURES, sqrt_rq). With out-of-panel keys the `_AttachMixin` falls back to building the
derived table straight from X (the full synthetic series).
"""

from __future__ import annotations

import datetime as dt

import numpy as np
import polars as pl
import pytest

from candidate_models.har_shrink import HARENet, HARRidge, _DERIVED, _NEEDS
from rv_eval import config as C
from rv_eval.features import HAR_RS_FEATURES, IV_FEATURES

_REQUIRED_COLS = [
    "ticker", "date", "horizon", "rv_hat", "sigma",
    "q05", "q10", "q25", "q50", "q75", "q90", "q95",
]
_Q_COLS = ["q05", "q10", "q25", "q50", "q75", "q90", "q95"]


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
        total_rv = rv_d
        iv_30d = np.abs(np.sqrt(rv_d * 252) + rng.normal(0, 0.02, n)) + 0.05
        iv_60d = iv_30d + rng.normal(0.005, 0.01, n)
        iv_90d = iv_60d + rng.normal(0.005, 0.01, n)
        rs_plus = rv_d * np.abs(rng.normal(0.5, 0.1, n))
        rs_minus = rv_d * np.abs(rng.normal(0.5, 0.1, n))
        x_rows.append(pl.DataFrame({
            "ticker": [tk] * n, "date": dates,
            # HAR_RS_FEATURES (passthrough, in X):
            "log_rv_d": log_rv_d,
            "log_rv_w": log_rv_d + rng.normal(0, 0.1, n),
            "log_rv_m": log_rv_d + rng.normal(0, 0.1, n),
            "rs_minus_5d": rs_minus + rng.normal(0, 1e-6, n),
            "rs_plus_5d": rs_plus + rng.normal(0, 1e-6, n),
            "jump_5d": np.abs(rng.normal(0, 1e-5, n)),
            # IV_FEATURES (passthrough, in X):
            "log_iv": np.log(iv_30d),
            "iv_slope": rng.normal(0, 0.01, n),
            "skew_25d": rng.normal(0, 0.05, n),
            "vix": np.abs(rng.normal(0.18, 0.05, n)),
            "vix3m": np.abs(rng.normal(0.19, 0.05, n)),
            "vix_slope": rng.normal(0, 0.01, n),
            "vvix": np.abs(rng.normal(0.9, 0.1, n)),
            # sqrt_rq (passthrough):
            "sqrt_rq": np.abs(rng.normal(0.01, 0.002, n)),
            # raw cols the _derive hook needs:
            "iv_30d": iv_30d,
            "iv_60d": iv_60d,
            "iv_90d": iv_90d,
            "total_rv": total_rv,
            "ret_cc": rng.normal(0, 0.01, n),
            "rs_plus": rs_plus,
            "rs_minus": rs_minus,
            "parkinson": rv_d * np.abs(rng.normal(1.0, 0.1, n)),
            "gk": rv_d * np.abs(rng.normal(1.0, 0.1, n)),
            "volume": np.abs(rng.normal(1e6, 1e5, n)),
            "transactions": np.abs(rng.normal(1e4, 1e3, n)),
            "rv_overnight": rv_d * np.abs(rng.normal(0.3, 0.05, n)),
        }))
        for h in C.HORIZONS:
            y_rows.append(pl.DataFrame({
                "ticker": [tk] * n, "date": dates,
                "horizon": np.full(n, h, np.int32),
                "target_var": np.exp(log_rv_d + np.log(h) + rng.normal(0, 0.3, n)),
            }))
    return pl.concat(x_rows), pl.concat(y_rows)


@pytest.mark.parametrize("cls,name", [(HARENet, "HAR-ENet"), (HARRidge, "HAR-Ridge")])
def test_shrink_predict_schema_and_finite(cls, name):
    assert cls.name == name
    assert cls.needs == _NEEDS
    X, y = _synthetic_panel()

    m = cls()
    m.fit(X, y)
    pred = m.predict(X)

    assert not pred.is_empty(), f"{name} produced no predictions on the synthetic panel"
    for col in _REQUIRED_COLS:
        assert col in pred.columns, f"missing required column: {col}"
    assert pred.select(_REQUIRED_COLS).columns == _REQUIRED_COLS

    rv_hat = pred["rv_hat"].to_numpy()
    assert np.isfinite(rv_hat).all(), "rv_hat must be finite"
    assert (rv_hat > 0).all(), "rv_hat must be positive (target_var units)"
    assert set(pred["horizon"].unique().to_list()) <= set(C.HORIZONS)

    qmat = pred.select(_Q_COLS).to_numpy()
    assert np.all(np.diff(qmat, axis=1) >= -1e-9), "quantiles must be non-decreasing"
    assert np.isfinite(qmat).all(), "quantiles must be finite"

    # hyperparameters recorded for the card
    assert m.warnings, "selected hyperparameters should be recorded per (ticker, horizon)"


def test_derive_columns():
    X, _ = _synthetic_panel(120)
    tab = HARENet()._derive(X)
    assert tab.columns == ["ticker", "date"] + _DERIVED
    # iv_ts_30_90 is point-in-time (no nulls); vrp_mom is a 5-row shift -> 5 leading nulls/ticker.
    assert tab["iv_ts_30_90"].null_count() == 0
    assert tab["vrp_mom"].null_count() == 5 * 3
    # lev_m is a 22-window roll-mean -> 21 leading nulls/ticker.
    assert tab["lev_m"].null_count() == 21 * 3
