"""Smoke tests for the iteration-2 shared bases (`candidate_models/_base_v2.py`).

Exercises all three reuse patterns on a synthetic 3-ticker x 500-day panel via tiny concrete
subclasses, asserting the exact output schema, finite positive rv_hat, and monotone quantiles.
"""

from __future__ import annotations

import datetime as dt

import numpy as np
import polars as pl

from candidate_models._base_v2 import _AttachMixin, _PooledLinearHAR, _QuantileModel
from rv_eval import config as C
from rv_eval.features import HAR_FEATURES
from rv_eval.model_contract import _LinearLogHAR

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
        x_rows.append(pl.DataFrame({
            "ticker": [tk] * n, "date": dates,
            "log_rv_d": log_rv_d,
            "log_rv_w": log_rv_d + rng.normal(0, 0.1, n),
            "log_rv_m": log_rv_d + rng.normal(0, 0.1, n),
            "ret_cc": rng.normal(0.0, 0.01, n),     # signed daily return (for _AttachMixin demo)
        }))
        for h in C.HORIZONS:
            y_rows.append(pl.DataFrame({
                "ticker": [tk] * n, "date": dates,
                "horizon": np.full(n, h, np.int32),
                "target_var": np.exp(log_rv_d + np.log(h) + rng.normal(0, 0.3, n)),
            }))
    return pl.concat(x_rows), pl.concat(y_rows)


def _assert_valid(pred: pl.DataFrame):
    assert not pred.is_empty(), "model produced no predictions"
    for col in _REQUIRED_COLS:
        assert col in pred.columns, f"missing required column: {col}"
    assert pred.select(_REQUIRED_COLS).columns == _REQUIRED_COLS
    rv_hat = pred["rv_hat"].to_numpy()
    assert np.isfinite(rv_hat).all() and (rv_hat > 0).all(), "rv_hat must be finite and positive"
    q = pred.select("q05", "q10", "q25", "q50", "q75", "q90", "q95").to_numpy()
    assert (np.diff(q, axis=1) >= -1e-9).all(), "quantiles must be non-decreasing"
    assert set(pred["horizon"].unique().to_list()) <= set(C.HORIZONS)


# --- P1: _AttachMixin + _LinearLogHAR -------------------------------------------------
class _DemoLHAR(_AttachMixin, _LinearLogHAR):
    name = "demo-lhar"
    needs = HAR_FEATURES + ["lev_d"]

    def _derive(self, src: pl.DataFrame) -> pl.DataFrame:
        return src.sort("ticker", "date").select(
            "ticker", "date",
            lev_d=pl.col("ret_cc").clip(upper_bound=0.0).rolling_mean(5, min_samples=5).over("ticker"),
        )


def test_attach_mixin_derives_and_joins():
    X, y = _synthetic_panel()
    m = _DemoLHAR()
    m.fit(X, y)
    pred = m.predict(X)
    _assert_valid(pred)
    # The derived column is joined into X, not present in raw X.
    assert "lev_d" not in X.columns
    assert "lev_d" in m._attach(X).columns


# --- P3: _PooledLinearHAR --------------------------------------------------------------
class _DemoPanel(_PooledLinearHAR):
    name = "demo-panel"
    needs = HAR_FEATURES


def test_pooled_linear_har_schema():
    X, y = _synthetic_panel()
    m = _DemoPanel()
    m.fit(X, y)
    pred = m.predict(X)
    _assert_valid(pred)
    # One pooled fit per horizon, with a shared slope vector and per-ticker intercepts.
    st = m.state[22]
    assert len(st["slopes"]) == len(HAR_FEATURES)
    assert set(st["intercepts"]) == {"AAA", "BBB", "CCC"}


def test_pooled_unseen_ticker_falls_back():
    X, y = _synthetic_panel()
    m = _DemoPanel()
    m.fit(X, y)
    # A ticker never seen in fit still predicts via the global-mean intercept fallback.
    unseen = X.filter(pl.col("ticker") == "AAA").with_columns(ticker=pl.lit("ZZZ"))
    pred = m.predict(unseen)
    _assert_valid(pred)


# --- P3: _QuantileModel (direct quantiles) --------------------------------------------
class _DemoQuantile(_QuantileModel):
    name = "demo-qr"
    needs = HAR_FEATURES

    def _design(self, sub: pl.DataFrame) -> np.ndarray:
        x = sub.select(self.needs).to_numpy().astype(float)
        return np.column_stack([np.ones(x.shape[0]), x])

    def _fit_one(self, sub: pl.DataFrame, h: int):
        A = self._design(sub)
        ylog = np.log(sub["target_var"].to_numpy().astype(float))
        beta, *_ = np.linalg.lstsq(A, ylog, rcond=None)
        resid = ylog - A @ beta
        qlevels = np.quantile(resid, C.QUANTILES)        # empirical residual quantiles
        return beta, float(np.std(resid)), qlevels

    def _predict_q(self, state, sub: pl.DataFrame, h: int):
        beta, s, qlevels = state
        mu = self._design(sub) @ beta
        m = np.exp(mu + 0.5 * s * s)
        from rv_eval.model_contract import Q_COLS
        q = {c: np.exp(mu + qlevels[i]) for i, c in enumerate(Q_COLS)}
        return m, m * np.sqrt(np.expm1(min(s * s, 50.0))), q


def test_quantile_model_direct_quantiles():
    X, y = _synthetic_panel()
    m = _DemoQuantile()
    m.fit(X, y)
    pred = m.predict(X)
    _assert_valid(pred)
