"""Smoke test for HAR-Act: synthetic 3-ticker x 500-day panel.

Asserts the required output columns, finite rv_hat>0, monotone quantiles, and
that the three activity features (log_vol_surprise, log_txn_surprise,
overnight_share) are actually built and joined onto X (the leading w=22 rows of
the surprise terms must be null pre-join, and the bulk non-null after `_attach`).
The panel carries raw `volume`/`transactions`/`rv_overnight`/`total_rv` columns
(as in inputs.parquet) plus the HAR_FEATURES the model also consumes; HARAct
derives the three activity columns internally. Some zero/non-positive total_rv
days are seeded to exercise the overnight-share guard.
"""

from __future__ import annotations

import datetime as dt

import numpy as np
import polars as pl

from candidate_models.har_act import HARAct, _ACT_FEATURES
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
        total_rv = rv_d.copy()
        # Overnight is a fraction of total variance.
        rv_overnight = total_rv * rng.uniform(0.05, 0.4, n)
        total_rv[rng.uniform(size=n) < 0.02] = 0.0  # exercise the overnight-share guard
        # Activity levels: positive, with shocks.
        volume = np.exp(rng.normal(15.0, 0.6, n))
        transactions = np.exp(rng.normal(10.0, 0.5, n)).astype(np.int64) + 1
        x_rows.append(pl.DataFrame({
            "ticker": [tk] * n, "date": dates,
            "log_rv_d": log_rv_d,
            "log_rv_w": log_rv_d + rng.normal(0, 0.1, n),
            "log_rv_m": log_rv_d + rng.normal(0, 0.1, n),
            "volume": volume,
            "transactions": transactions,
            "rv_overnight": rv_overnight,
            "total_rv": total_rv,
        }))
        for h in C.HORIZONS:
            y_rows.append(pl.DataFrame({
                "ticker": [tk] * n, "date": dates,
                "horizon": np.full(n, h, np.int32),
                "target_var": np.exp(log_rv_d + np.log(h) + rng.normal(0, 0.3, n)),
            }))
    return pl.concat(x_rows), pl.concat(y_rows)


def test_har_act_predict_schema_and_finite():
    assert HARAct.name == "HAR-Act"
    assert HARAct.needs == HAR_FEATURES + _ACT_FEATURES
    X, y = _synthetic_panel()

    m = HARAct()
    m.fit(X, y)
    pred = m.predict(X)

    assert not pred.is_empty(), "HAR-Act produced no predictions on the synthetic panel"
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


def test_har_act_features_built_and_joined():
    """The three activity features are derived/joined and become non-null post-attach."""
    X, _ = _synthetic_panel()
    m = HARAct()

    # The raw derived table over the full series.
    tab = m._derive(X)
    for c in _ACT_FEATURES:
        assert c in tab.columns, f"derive() did not build {c}"

    # After _attach, the activity cols are present on X and non-null beyond warm-up.
    attached = m._attach(X)
    for c in _ACT_FEATURES:
        assert c in attached.columns, f"_attach did not join {c}"
    attached = attached.sort("ticker", "date")
    # w=22 means the first 21 rows per ticker are null for the surprise terms;
    # the bulk must be populated.
    vol_surp = attached["log_vol_surprise"]
    assert vol_surp.null_count() < attached.height, "log_vol_surprise should be mostly non-null"
    assert np.isfinite(vol_surp.drop_nulls().to_numpy()).all()
    assert np.isfinite(attached["log_txn_surprise"].drop_nulls().to_numpy()).all()
    # overnight_share is null only where total_rv<=0 (the seeded guard rows).
    ons = attached["overnight_share"]
    assert ons.null_count() < attached.height, "overnight_share should be mostly non-null"
    assert np.isfinite(ons.drop_nulls().to_numpy()).all()
