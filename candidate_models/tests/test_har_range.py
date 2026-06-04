"""Smoke test for HAR-Range: synthetic 3-ticker x 500-day panel.

Asserts the required output columns, finite rv_hat>0, monotone quantiles, and
that the four log range-estimator features are actually built and joined onto X
(the leading w=5 rows must be null pre-join, and non-null after `_attach`). The
panel carries raw `parkinson`/`gk` columns (as in inputs.parquet) plus the
HAR_FEATURES the model also consumes; HARRange derives log_park_d/w + log_gk_d/w
internally. Some exactly-zero range days are seeded to exercise the log-floor.
"""

from __future__ import annotations

import datetime as dt

import numpy as np
import polars as pl

from candidate_models.har_range import HARRange, _RANGE_FEATURES
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
        rv_d = np.exp(log_rv_d)
        # Range estimators are noisy non-negative proxies of the same daily variance.
        parkinson = rv_d * rng.uniform(0.5, 1.5, n)
        gk = rv_d * rng.uniform(0.5, 1.5, n)
        parkinson[rng.uniform(size=n) < 0.05] = 0.0  # exactly-zero days -> exercise log floor
        gk[rng.uniform(size=n) < 0.05] = 0.0
        x_rows.append(pl.DataFrame({
            "ticker": [tk] * n, "date": dates,
            "log_rv_d": log_rv_d,
            "log_rv_w": log_rv_d + rng.normal(0, 0.1, n),
            "log_rv_m": log_rv_d + rng.normal(0, 0.1, n),
            "parkinson": parkinson,
            "gk": gk,
        }))
        for h in C.HORIZONS:
            y_rows.append(pl.DataFrame({
                "ticker": [tk] * n, "date": dates,
                "horizon": np.full(n, h, np.int32),
                "target_var": np.exp(log_rv_d + np.log(h) + rng.normal(0, 0.3, n)),
            }))
    return pl.concat(x_rows), pl.concat(y_rows)


def test_har_range_predict_schema_and_finite():
    assert HARRange.name == "HAR-Range"
    assert HARRange.needs == HAR_FEATURES + _RANGE_FEATURES
    X, y = _synthetic_panel()

    m = HARRange()
    m.fit(X, y)
    pred = m.predict(X)

    assert not pred.is_empty(), "HAR-Range produced no predictions on the synthetic panel"
    for col in _REQUIRED_COLS:
        assert col in pred.columns, f"missing required column: {col}"
    assert pred.select(_REQUIRED_COLS).columns == _REQUIRED_COLS

    rv_hat = pred["rv_hat"].to_numpy()
    assert np.isfinite(rv_hat).all(), "rv_hat must be finite"
    assert (rv_hat > 0).all(), "rv_hat must be positive (target_var units)"
    assert set(pred["horizon"].unique().to_list()) <= set(C.HORIZONS)

    # Monotone (non-decreasing) quantiles per row.
    q_cols = ["q05", "q10", "q25", "q50", "q75", "q90", "q95"]
    qmat = pred.select(q_cols).to_numpy()
    assert np.all(np.diff(qmat, axis=1) >= -1e-9), "quantiles must be non-decreasing"


def test_har_range_features_built_and_joined():
    """The four log range features are derived/joined and become non-null post-attach."""
    X, _ = _synthetic_panel()
    m = HARRange()

    # The raw derived table over the full series.
    tab = m._derive(X)
    for c in _RANGE_FEATURES:
        assert c in tab.columns, f"derive() did not build {c}"

    # After _attach, the range cols are present on X and non-null beyond the warm-up.
    attached = m._attach(X)
    for c in _RANGE_FEATURES:
        assert c in attached.columns, f"_attach did not join {c}"
    # w=5 means the first 4 rows per ticker are null; the bulk must be populated.
    park_w = attached.sort("ticker", "date")["log_park_w"]
    assert park_w.null_count() < attached.height, "log_park_w should be mostly non-null"
    assert np.isfinite(attached["log_park_d"].drop_nulls().to_numpy()).all()
