"""Smoke tests for HAR-GARCH (catalog model 26, candidate_models/har_garch.py).

Synthetic 3-ticker x 500-day panel. Asserts the exact output schema, finite
positive rv_hat, monotone lognormal quantiles, and that a (ticker,horizon) whose
residuals defeat the GARCH fit falls back gracefully to the constant HAR sd
without aborting or producing junk.
"""

from __future__ import annotations

import datetime as dt

import numpy as np
import polars as pl

from candidate_models.har_garch import HARGARCH, _fit_garch_on_resid
from rv_eval import config as C

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


def test_schema_and_quantiles():
    X, y = _synthetic_panel()
    m = HARGARCH()
    m.fit(X, y)
    pred = m.predict(X)
    _assert_valid(pred)
    # Each (ticker, horizon) that has enough obs produced a fitted state.
    assert len(m.state) == 3 * len(C.HORIZONS)


def test_records_fit_specs_and_fallback_counter_exists():
    X, y = _synthetic_panel()
    m = HARGARCH()
    m.fit(X, y)
    # The bookkeeping the card needs is populated for every fitted key.
    assert set(m.fit_specs.keys()) == set(m.state.keys())
    allowed = {"GARCH(1,1)", "GJR-GARCH(1,1,1)", "constant-sd (fallback)"}
    assert set(m.fit_specs.values()) <= allowed
    # fallbacks dict exists and only ever holds keys that are also fitted keys.
    assert set(m.fallbacks.keys()) <= set(m.state.keys())


def test_nonconvergent_fit_falls_back_gracefully():
    # A degenerate (near-constant) residual series defeats the GARCH fit; the helper
    # must return None so the model uses the constant HAR sd instead of crashing.
    resid = np.full(300, 1e-9) + np.random.default_rng(1).normal(0, 1e-12, 300)
    assert _fit_garch_on_resid(resid, 22) is None


def test_constant_within_block_per_row_sigma():
    # Predictive log-sd is constant within a refit block (single GARCH forecast origin):
    # rv_hat varies row to row (driven by the HAR mean) but sigma/rv_hat ratio is stable.
    X, y = _synthetic_panel()
    m = HARGARCH()
    m.fit(X, y)
    pred = m.predict(X)
    sub = pred.filter((pl.col("ticker") == "AAA") & (pl.col("horizon") == 22))
    ratio = (sub["sigma"] / sub["rv_hat"]).to_numpy()
    assert np.allclose(ratio, ratio[0], rtol=1e-6), "sigma/rv_hat should be constant within block"
