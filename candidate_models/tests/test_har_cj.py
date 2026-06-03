"""Smoke test for HAR-CJ: synthetic 3-ticker x 500-day panel -> required columns, finite rv_hat.

The panel carries raw `bv` and `jump` columns (as in inputs.parquet) plus the
HAR_FEATURES the model also consumes; HARCJ derives log_bv_d/w/m + log_jump_d
internally. We seed some exactly-zero jump days to exercise the log-floor.
"""

from __future__ import annotations

import datetime as dt

import numpy as np
import polars as pl

from candidate_models.har_cj import HARCJ, _CJ_FEATURES
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
        # Continuous part (BV) is most of total RV; jump is a small non-negative residual.
        jump = 0.1 * rv_d * rng.uniform(0.0, 1.0, n)
        jump[rng.uniform(size=n) < 0.3] = 0.0  # exactly-zero jump days -> exercise log floor
        bv = np.clip(rv_d - jump, 0.0, None)
        x_rows.append(pl.DataFrame({
            "ticker": [tk] * n, "date": dates,
            "log_rv_d": log_rv_d,
            "log_rv_w": log_rv_d + rng.normal(0, 0.1, n),
            "log_rv_m": log_rv_d + rng.normal(0, 0.1, n),
            "bv": bv,
            "jump": jump,
        }))
        for h in C.HORIZONS:
            y_rows.append(pl.DataFrame({
                "ticker": [tk] * n, "date": dates,
                "horizon": np.full(n, h, np.int32),
                "target_var": np.exp(log_rv_d + np.log(h) + rng.normal(0, 0.3, n)),
            }))
    return pl.concat(x_rows), pl.concat(y_rows)


def test_har_cj_predict_schema_and_finite():
    assert HARCJ.name == "HAR-CJ"
    assert HARCJ.needs == HAR_FEATURES + _CJ_FEATURES
    X, y = _synthetic_panel()

    m = HARCJ()
    m.fit(X, y)
    pred = m.predict(X)

    assert not pred.is_empty(), "HAR-CJ produced no predictions on the synthetic panel"
    for col in _REQUIRED_COLS:
        assert col in pred.columns, f"missing required column: {col}"
    assert pred.select(_REQUIRED_COLS).columns == _REQUIRED_COLS

    rv_hat = pred["rv_hat"].to_numpy()
    assert np.isfinite(rv_hat).all(), "rv_hat must be finite"
    assert (rv_hat > 0).all(), "rv_hat must be positive (target_var units)"
    assert set(pred["horizon"].unique().to_list()) <= set(C.HORIZONS)
