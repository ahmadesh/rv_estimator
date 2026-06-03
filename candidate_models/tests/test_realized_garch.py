"""Smoke test for the Realized GARCH (HHS 2012) model.

Synthetic 3-ticker x 500-day panel with `ret_cc` (the plan's `ret_close`) and
`rv_d`. Asserts predict returns the required output columns and finite, positive
rv_hat for the covered keys.
"""

from __future__ import annotations

import numpy as np
import polars as pl

from candidate_models.realized_garch import RealizedGARCH
from rv_eval import config as C

REQUIRED = ["ticker", "date", "horizon", "rv_hat", "sigma",
            "q05", "q10", "q25", "q50", "q75", "q90", "q95"]


def _synth_panel(n_tickers: int = 3, n_days: int = 500, seed: int = 0):
    rng = np.random.default_rng(seed)
    dates = pl.date_range(pl.date(2010, 1, 1), pl.date(2025, 1, 1), "1d", eager=True)
    dates = dates.filter(dates.dt.weekday() <= 5).head(n_days)
    rows_in, rows_y = [], []
    for ti in range(n_tickers):
        tk = f"T{ti}"
        # simple log-GARCH-ish volatility path so a R-GARCH has signal to fit
        logh = np.log(2e-4)
        rv = np.empty(n_days)
        ret = np.empty(n_days)
        for d in range(n_days):
            logh = -0.5 + 0.92 * logh + 0.05 * rng.standard_normal()
            h = np.exp(logh)
            ret[d] = np.sqrt(h) * rng.standard_normal()
            rv[d] = h * np.exp(0.3 * rng.standard_normal())  # noisy realized measure
        rows_in.append(pl.DataFrame({
            "ticker": [tk] * n_days, "date": dates,
            "ret_cc": ret, "total_rv": rv, "rv_d": rv,
        }))
        # build forward-sum targets for each horizon
        for h in C.HORIZONS:
            tv = np.array([rv[i + 1:i + 1 + h].sum() if i + 1 + h <= n_days else np.nan
                           for i in range(n_days)])
            rows_y.append(pl.DataFrame({
                "ticker": [tk] * n_days, "date": dates,
                "horizon": [h] * n_days, "target_var": tv,
            }).drop_nulls("target_var"))
    return pl.concat(rows_in), pl.concat(rows_y)


def test_predict_schema_and_finite():
    X, y = _synth_panel()
    m = RealizedGARCH()
    m.fit(X, y)
    assert len(m.state) > 0, "model fit no (ticker, horizon) keys"
    pred = m.predict(X)
    assert not pred.is_empty()
    for c in REQUIRED:
        assert c in pred.columns, f"missing output column {c}"
    rv = pred["rv_hat"].to_numpy()
    assert np.all(np.isfinite(rv)) and np.all(rv > 0)
    assert np.all(pred["sigma"].to_numpy() >= 0)
    # quantiles are monotone non-decreasing
    qs = pred.select(["q05", "q10", "q25", "q50", "q75", "q90", "q95"]).to_numpy()
    assert np.all(np.diff(qs, axis=1) >= -1e-9)


def test_horizons_covered():
    X, y = _synth_panel()
    m = RealizedGARCH()
    m.fit(X, y)
    pred = m.predict(X)
    covered = set(pred["horizon"].unique().to_list())
    assert covered.issubset(set(C.HORIZONS))
    assert len(covered) >= 1
