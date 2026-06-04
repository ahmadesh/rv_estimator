"""Smoke test for HAR-IVTS: synthetic 3-ticker x 500-day panel.

Asserts predict returns the required schema, finite rv_hat>0, and monotone quantiles.
The panel carries the raw IV-tenor + total_rv columns the model's `_derive` needs
(iv_30d/iv_60d/iv_90d, total_rv) plus the non-derived X feature columns in `needs`
(HAR_FEATURES, IV_FEATURES, vix9d_slope). With out-of-panel keys the `_AttachMixin`
falls back to building the derived table straight from X (the full synthetic series).
"""

from __future__ import annotations

import datetime as dt

import numpy as np
import polars as pl

from candidate_models.har_ivts import HARIVTS, _IVTS_FEATURES
from rv_eval import config as C
from rv_eval.features import HAR_FEATURES, IV_FEATURES

_REQUIRED_COLS = [
    "ticker", "date", "horizon", "rv_hat", "sigma",
    "q05", "q10", "q25", "q50", "q75", "q90", "q95",
]
_Q_COLS = ["q05", "q10", "q25", "q50", "q75", "q90", "q95"]


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
        total_rv = rv_d
        # IV tenors (annualised vol level ~ sqrt of daily var scaled up); keep positive.
        iv_30d = np.abs(np.sqrt(rv_d * 252) + rng.normal(0, 0.02, n)) + 0.05
        iv_60d = iv_30d + rng.normal(0.005, 0.01, n)
        iv_90d = iv_60d + rng.normal(0.005, 0.01, n)
        x_rows.append(pl.DataFrame({
            "ticker": [tk] * n, "date": dates,
            "log_rv_d": log_rv_d,
            "log_rv_w": log_rv_d + rng.normal(0, 0.1, n),
            "log_rv_m": log_rv_d + rng.normal(0, 0.1, n),
            # IV_FEATURES columns:
            "log_iv": np.log(iv_30d),
            "iv_slope": rng.normal(0, 0.01, n),
            "skew_25d": rng.normal(0, 0.05, n),
            "vix": np.abs(rng.normal(0.18, 0.05, n)),
            "vix3m": np.abs(rng.normal(0.19, 0.05, n)),
            "vix_slope": rng.normal(0, 0.01, n),
            "vvix": np.abs(rng.normal(0.9, 0.1, n)),
            # raw cols for _derive:
            "iv_30d": iv_30d,
            "iv_60d": iv_60d,
            "iv_90d": iv_90d,
            "total_rv": total_rv,
            # systematic passthrough:
            "vix9d_slope": rng.normal(0, 0.01, n),
        }))
        for h in C.HORIZONS:
            y_rows.append(pl.DataFrame({
                "ticker": [tk] * n, "date": dates,
                "horizon": np.full(n, h, np.int32),
                "target_var": np.exp(log_rv_d + np.log(h) + rng.normal(0, 0.3, n)),
            }))
    return pl.concat(x_rows), pl.concat(y_rows)


def test_har_ivts_predict_schema_and_finite():
    assert HARIVTS.name == "HAR-IVTS"
    assert HARIVTS.needs == HAR_FEATURES + IV_FEATURES + _IVTS_FEATURES + ["vix9d_slope"]
    X, y = _synthetic_panel()

    m = HARIVTS()
    m.fit(X, y)
    pred = m.predict(X)

    assert not pred.is_empty(), "HAR-IVTS produced no predictions on the synthetic panel"
    for col in _REQUIRED_COLS:
        assert col in pred.columns, f"missing required column: {col}"
    assert pred.select(_REQUIRED_COLS).columns == _REQUIRED_COLS

    rv_hat = pred["rv_hat"].to_numpy()
    assert np.isfinite(rv_hat).all(), "rv_hat must be finite"
    assert (rv_hat > 0).all(), "rv_hat must be positive (target_var units)"
    assert set(pred["horizon"].unique().to_list()) <= set(C.HORIZONS)

    # Monotone non-decreasing quantiles row-wise.
    qmat = pred.select(_Q_COLS).to_numpy()
    assert np.all(np.diff(qmat, axis=1) >= -1e-9), "quantiles must be non-decreasing"
    assert np.isfinite(qmat).all(), "quantiles must be finite"


def test_har_ivts_derive_columns():
    X, _ = _synthetic_panel(120)
    tab = HARIVTS()._derive(X)
    assert tab.columns == ["ticker", "date"] + _IVTS_FEATURES
    # iv_ts_30_90 = iv_90d - iv_30d should be point-in-time (no nulls).
    assert tab["iv_ts_30_90"].null_count() == 0
    # vrp_mom is a 5-row shift per ticker -> 5 leading nulls per ticker.
    assert tab["vrp_mom"].null_count() == 5 * 3
