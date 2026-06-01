"""Walk-forward purge + embargo: no training row's forward target window may reach the test block."""

from __future__ import annotations

import datetime as dt

import numpy as np
import polars as pl

from rv_eval import config as C
from rv_eval.model_contract import Model
from rv_eval.walkforward import run


class _Recorder(Model):
    """Captures the (train y, test X) handed in at each fold for leakage inspection."""

    name = "recorder"

    def __init__(self):
        self.fits: list[pl.DataFrame] = []
        self.tests: list[pl.DataFrame] = []

    def fit(self, X, y):
        self.fits.append(y)

    def predict(self, X):
        self.tests.append(X)
        return pl.DataFrame()  # no predictions needed for the leakage check


def _synthetic_panel():
    dates = pl.date_range(dt.date(2014, 1, 1), dt.date(2019, 12, 31), interval="1d", eager=True)
    dates = dates.filter(dates.dt.weekday() <= 5)  # weekdays ~ trading calendar
    n = dates.len()
    rng = np.random.default_rng(1)
    X = pl.DataFrame({"ticker": ["T"] * n, "date": dates, "rv_d": rng.uniform(1e-4, 1e-3, n)})
    rows = []
    for h in C.HORIZONS:
        rows.append(pl.DataFrame({
            "ticker": ["T"] * n, "date": dates, "horizon": np.full(n, h, np.int32),
            "target_var": rng.uniform(1e-4, 1e-3, n),
        }))
    return X, pl.concat(rows)


def test_purge_and_embargo_no_leakage():
    X, y = _synthetic_panel()
    cal = {d: i for i, d in enumerate(X.sort("date")["date"].to_list())}
    rec = _Recorder()
    run(rec, X, y)

    assert rec.fits, "walk-forward produced no folds"
    for y_train, X_test in zip(rec.fits, rec.tests):
        ts = min(cal[d] for d in X_test["date"].to_list())
        # every test date is out-of-sample
        assert ts >= C.MIN_TRAIN_DAYS
        for h in C.HORIZONS:
            yh = y_train.filter(pl.col("horizon") == h)
            if yh.is_empty():
                continue
            train_max = max(cal[d] for d in yh["date"].to_list())
            # forward target window (train_max+h) must end before the embargo gap
            assert train_max + h <= ts - C.EMBARGO_EXTRA
