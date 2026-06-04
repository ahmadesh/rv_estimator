"""Smoke test for HAR-CSR (model 20): synthetic 3-ticker x 500-day panel.

Asserts predict returns the required schema, finite rv_hat>0, monotone quantiles, and that
the complete-subset enumeration is exactly C(8,4)=70 subsets (the catalog cap, no sampling).
All 8 HAR-CSR features are pass-through columns from build_features, so the synthetic X just
carries them directly (no derived-rolling join is involved).
"""

from __future__ import annotations

import datetime as dt
from math import comb

import numpy as np
import polars as pl

from candidate_models.har_csr import HARCSR, _FEATURES, _K_SUBSET, _SUBSETS
from rv_eval import config as C

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
        iv_30d = np.abs(np.sqrt(rv_d * 252) + rng.normal(0, 0.02, n)) + 0.05
        x_rows.append(pl.DataFrame({
            "ticker": [tk] * n, "date": dates,
            "log_rv_d": log_rv_d,
            "log_rv_w": log_rv_d + rng.normal(0, 0.1, n),
            "log_rv_m": log_rv_d + rng.normal(0, 0.1, n),
            "rs_minus_5d": rv_d * np.abs(rng.normal(0.5, 0.1, n)),
            "jump_5d": np.abs(rng.normal(0, 1e-5, n)),
            "log_iv": np.log(iv_30d),
            "vix": np.abs(rng.normal(0.18, 0.05, n)),
            "sqrt_rq": np.abs(rng.normal(0.01, 0.002, n)),
        }))
        for h in C.HORIZONS:
            y_rows.append(pl.DataFrame({
                "ticker": [tk] * n, "date": dates,
                "horizon": np.full(n, h, np.int32),
                "target_var": np.exp(log_rv_d + np.log(h) + rng.normal(0, 0.3, n)),
            }))
    return pl.concat(x_rows), pl.concat(y_rows)


def test_subset_scheme_is_complete():
    assert len(_FEATURES) == 8
    assert _K_SUBSET == 4
    # Complete enumeration: C(8,4) == 70, the catalog cap exactly (no sampling).
    assert len(_SUBSETS) == comb(8, 4) == 70
    assert len(set(_SUBSETS)) == 70                       # all distinct
    for cols in _SUBSETS:
        assert len(cols) == 4 and max(cols) < 8


def test_csr_predict_schema_and_finite():
    assert HARCSR.name == "HAR-CSR"
    assert HARCSR.needs == _FEATURES
    X, y = _synthetic_panel()

    m = HARCSR()
    m.fit(X, y)
    pred = m.predict(X)

    assert not pred.is_empty(), "HAR-CSR produced no predictions on the synthetic panel"
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
