"""Smoke test for XGBHARRSIV: synthetic 3-ticker x 500-day panel -> required columns, finite rv_hat."""

from __future__ import annotations

import datetime as dt

import numpy as np
import polars as pl

from candidate_models.xgb_har import XGBHARRSIV
from rv_eval import config as C
from rv_eval.features import HAR_RS_FEATURES, IV_FEATURES

_REQUIRED_COLS = [
    "ticker", "date", "horizon", "rv_hat", "sigma",
    "q05", "q10", "q25", "q50", "q75", "q90", "q95",
]

# Deduplicated needs the model declares: HAR_RS + IV + sqrt_rq, first-seen order preserved.
_EXPECTED_NEEDS = HAR_RS_FEATURES + IV_FEATURES + ["sqrt_rq"]


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
        cols = {
            "ticker": [tk] * n, "date": dates,
            # HAR-RS block
            "log_rv_d": log_rv_d,
            "log_rv_w": log_rv_d + rng.normal(0, 0.1, n),
            "log_rv_m": log_rv_d + rng.normal(0, 0.1, n),
            "rs_minus_5d": 0.5 * rv_d * rng.uniform(0.8, 1.2, n),
            "rs_plus_5d": 0.5 * rv_d * rng.uniform(0.8, 1.2, n),
            "jump_5d": 0.1 * rv_d * rng.uniform(0.0, 1.0, n),
            # IV block
            "log_iv": log_rv_d + rng.normal(0, 0.2, n),
            "iv_slope": rng.normal(0, 0.05, n),
            "skew_25d": rng.normal(0, 0.1, n),
            "vix": np.abs(rng.normal(18, 4, n)),
            "vix3m": np.abs(rng.normal(19, 4, n)),
            "vix_slope": rng.normal(0, 1.0, n),
            "vvix": np.abs(rng.normal(90, 10, n)),
            # quarticity term
            "sqrt_rq": np.sqrt(rv_d) * rng.uniform(0.8, 1.2, n),
        }
        x_rows.append(pl.DataFrame(cols))
        for h in C.HORIZONS:
            y_rows.append(pl.DataFrame({
                "ticker": [tk] * n, "date": dates,
                "horizon": np.full(n, h, np.int32),
                "target_var": np.exp(log_rv_d + np.log(h) + rng.normal(0, 0.3, n)),
            }))
    return pl.concat(x_rows), pl.concat(y_rows)


def test_needs_are_deduplicated_in_order():
    assert XGBHARRSIV.name == "XGBHARRSIV"
    needs = XGBHARRSIV.needs
    assert needs == _EXPECTED_NEEDS, needs
    assert len(needs) == len(set(needs)), "needs must be deduplicated"


def test_xgb_har_predict_schema_and_finite():
    X, y = _synthetic_panel()

    m = XGBHARRSIV()
    m.fit(X, y)
    pred = m.predict(X)

    assert not pred.is_empty(), "XGBHARRSIV produced no predictions on the synthetic panel"
    for col in _REQUIRED_COLS:
        assert col in pred.columns, f"missing required column: {col}"
    assert pred.select(_REQUIRED_COLS).columns == _REQUIRED_COLS

    rv_hat = pred["rv_hat"].to_numpy()
    assert np.isfinite(rv_hat).all(), "rv_hat must be finite"
    assert (rv_hat > 0).all(), "rv_hat must be positive (target_var units)"
    assert set(pred["horizon"].unique().to_list()) <= set(C.HORIZONS)
