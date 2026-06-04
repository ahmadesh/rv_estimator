"""Smoke test for HAR-MAX: synthetic 3-ticker x 500-day panel.

Asserts predict() returns the required schema, finite rv_hat>0, and monotone quantiles.
The synthetic panel carries every raw column `HARMAX._derive` consumes (ret_cc, rs_plus,
rs_minus, iv_30d/60d/90d, total_rv, parkinson, gk, volume, transactions, rv_overnight) so
the `_AttachMixin` smoke-test fallback (`_derive(X)`) rebuilds the full series from X. It
also carries the pass-through feature columns (HAR_RS, IV, sqrt_rq, vix9d_slope). Some
exactly-zero parkinson/gk/volume rows exercise the log-floor.
"""

from __future__ import annotations

import datetime as dt

import numpy as np
import polars as pl

from candidate_models.har_max import HARMAX, _DERIVED, _PASSTHROUGH
from rv_eval import config as C

_REQUIRED_COLS = [
    "ticker", "date", "horizon", "rv_hat", "sigma",
    "q05", "q10", "q25", "q50", "q75", "q90", "q95",
]
_Q = ["q05", "q10", "q25", "q50", "q75", "q90", "q95"]


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
        iv30 = np.sqrt(np.clip(rv_d * 252.0, 1e-9, None)) + rng.uniform(0.0, 0.05, n)
        # exactly-zero range/volume days exercise the log floor in _derive.
        park = rv_d * rng.uniform(0.0, 1.2, n)
        park[rng.uniform(size=n) < 0.1] = 0.0
        gk = rv_d * rng.uniform(0.0, 1.2, n)
        gk[rng.uniform(size=n) < 0.1] = 0.0
        vol = rng.uniform(1e5, 1e7, n)
        vol[rng.uniform(size=n) < 0.05] = 0.0
        rs_plus = 0.5 * rv_d * rng.uniform(0.0, 1.0, n)
        rs_minus = rv_d - rs_plus
        x = pl.DataFrame({
            "ticker": [tk] * n, "date": dates,
            # pass-through HAR_RS_FEATURES
            "log_rv_d": log_rv_d,
            "log_rv_w": log_rv_d + rng.normal(0, 0.1, n),
            "log_rv_m": log_rv_d + rng.normal(0, 0.1, n),
            "rs_minus_5d": rs_minus, "rs_plus_5d": rs_plus,
            "jump_5d": 0.1 * rv_d * rng.uniform(0.0, 1.0, n),
            # pass-through IV_FEATURES
            "log_iv": np.log(iv30), "iv_slope": rng.normal(0, 0.02, n),
            "skew_25d": rng.normal(0, 0.05, n), "vix": rng.uniform(10, 40, n),
            "vix3m": rng.uniform(12, 38, n), "vix_slope": rng.normal(0, 1.0, n),
            "vvix": rng.uniform(70, 130, n),
            "sqrt_rq": np.sqrt(np.clip(rv_d ** 2, 0, None)),
            "vix9d_slope": rng.normal(0, 1.0, n),
            # raw columns _derive needs
            "ret_cc": rng.normal(0, 0.01, n),
            "rs_plus": rs_plus, "rs_minus": rs_minus,
            "iv_30d": iv30, "iv_60d": iv30 + rng.uniform(0, 0.03, n),
            "iv_90d": iv30 + rng.uniform(0, 0.05, n),
            "total_rv": rv_d,
            "parkinson": park, "gk": gk,
            "volume": vol, "transactions": rng.uniform(1e3, 1e5, n),
            "rv_overnight": 0.2 * rv_d * rng.uniform(0.0, 1.0, n),
        })
        x_rows.append(x)
        for h in C.HORIZONS:
            y_rows.append(pl.DataFrame({
                "ticker": [tk] * n, "date": dates,
                "horizon": np.full(n, h, np.int32),
                "target_var": np.exp(log_rv_d + np.log(h) + rng.normal(0, 0.3, n)),
            }))
    return pl.concat(x_rows), pl.concat(y_rows)


def test_har_max_schema_finite_monotone():
    assert HARMAX.name == "HAR-MAX"
    assert HARMAX.needs == _PASSTHROUGH + _DERIVED
    assert len(set(HARMAX.needs)) == len(HARMAX.needs), "needs must be deduped"

    X, y = _synthetic_panel()
    m = HARMAX()
    m.fit(X, y)
    pred = m.predict(X)

    assert not pred.is_empty(), "HAR-MAX produced no predictions on the synthetic panel"
    for col in _REQUIRED_COLS:
        assert col in pred.columns, f"missing required column: {col}"

    rv_hat = pred["rv_hat"].to_numpy()
    assert np.isfinite(rv_hat).all(), "rv_hat must be finite"
    assert (rv_hat > 0).all(), "rv_hat must be positive (target_var units)"
    assert set(pred["horizon"].unique().to_list()) <= set(C.HORIZONS)

    qmat = pred.select(_Q).to_numpy()
    diffs = np.diff(qmat, axis=1)
    assert (diffs >= -1e-9).all(), "quantiles must be non-decreasing q05<=...<=q95"
