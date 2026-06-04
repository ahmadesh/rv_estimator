"""Smoke tests for HAR-Shrink2Group (candidate_models/har_shrink2group.py, catalog model 23).

Synthetic 3-ticker x 500-day panel carrying the full pooled feature set (HAR-RS + IV). Asserts:
the exact output schema, finite positive rv_hat, monotone quantiles, that a shrinkage intensity
`w in [0,1]` is selected per horizon by the inner CV (TRAIN-only), and that a thin / unseen ticker
falls back to the pooled coefficient vector (never errors).

Run by explicit path:
    .venv/bin/python -m pytest candidate_models/tests/test_har_shrink2group.py -q
"""

from __future__ import annotations

import datetime as dt

import numpy as np
import polars as pl

from candidate_models.har_shrink2group import HARShrink2Group, _NEEDS, _pooled_beta_for
from rv_eval import config as C

_REQUIRED_COLS = [
    "ticker", "date", "horizon", "rv_hat", "sigma",
    "q05", "q10", "q25", "q50", "q75", "q90", "q95",
]


def _synthetic_panel(n_days: int = 500, tickers=("AAA", "BBB", "CCC")):
    dates = pl.date_range(dt.date(2010, 1, 1), dt.date(2016, 12, 31), interval="1d", eager=True)
    dates = dates.filter(dates.dt.weekday() <= 5)[:n_days]
    n = dates.len()
    rng = np.random.default_rng(0)

    x_rows, y_rows = [], []
    for lvl, tk in enumerate(tickers):
        # Ticker-specific level + slope -> exercises both per-ticker fit and shrinkage.
        log_rv_d = rng.normal(-8.0 + 0.5 * lvl, 0.5, n)
        feats = {
            "log_rv_d": log_rv_d,
            "log_rv_w": log_rv_d + rng.normal(0, 0.1, n),
            "log_rv_m": log_rv_d + rng.normal(0, 0.1, n),
            "rs_minus_5d": np.exp(log_rv_d) * rng.uniform(0.3, 0.7, n),
            "rs_plus_5d": np.exp(log_rv_d) * rng.uniform(0.3, 0.7, n),
            "jump_5d": np.exp(log_rv_d) * rng.uniform(0.0, 0.2, n),
            "log_iv": log_rv_d * 0.5 - 3.0 + rng.normal(0, 0.1, n),
            "iv_slope": rng.normal(0.0, 0.02, n),
            "skew_25d": rng.normal(0.0, 0.05, n),
            "vix": rng.uniform(12.0, 30.0, n),
            "vix3m": rng.uniform(13.0, 28.0, n),
            "vix_slope": rng.normal(0.0, 0.5, n),
            "vvix": rng.uniform(80.0, 120.0, n),
        }
        assert set(feats) == set(_NEEDS)
        x_rows.append(pl.DataFrame({"ticker": [tk] * n, "date": dates, **feats}))
        for h in C.HORIZONS:
            y_rows.append(pl.DataFrame({
                "ticker": [tk] * n, "date": dates,
                "horizon": np.full(n, h, np.int32),
                "target_var": np.exp((0.7 + 0.05 * lvl) * log_rv_d + np.log(h)
                                     + rng.normal(0, 0.3, n)),
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


def test_schema_and_shrinkage_weight():
    X, y = _synthetic_panel()
    m = HARShrink2Group()
    m.fit(X, y)
    pred = m.predict(X)
    _assert_valid(pred)
    assert m.name == "HAR-Shrink2Group"
    # A shrinkage intensity in [0,1] is selected per horizon by the inner CV.
    for h in C.HORIZONS:
        assert h in m.chosen_w
        assert 0.0 <= m.chosen_w[h] <= 1.0
    # Shrunk per-ticker beta has length 1(intercept)+F(slopes).
    st = m.state[C.PRIMARY_HORIZON]
    assert len(st["beta"]["AAA"]) == 1 + len(_NEEDS)
    assert set(st["beta"]) == {"AAA", "BBB", "CCC"}


def test_unseen_ticker_falls_back_to_pooled():
    X, y = _synthetic_panel()
    m = HARShrink2Group()
    m.fit(X, y)
    # A ticker never seen in fit must still predict via the pooled coefficient vector, not error.
    unseen = X.filter(pl.col("ticker") == "AAA").with_columns(ticker=pl.lit("ZZZ"))
    pred = m.predict(unseen)
    _assert_valid(pred)
    assert set(pred["ticker"].unique().to_list()) == {"ZZZ"}


def test_thin_ticker_uses_pooled_beta():
    """A ticker with < min_ticker_obs train rows uses the pooled beta outright (w=1 for it)."""
    X, y = _synthetic_panel(n_days=400, tickers=("AAA", "BBB", "CCC"))
    # Make CCC thin: keep only its first 40 dates (< min_ticker_obs=100), full history for AAA/BBB.
    thin_dates = (
        X.filter(pl.col("ticker") == "CCC").sort("date")["date"].unique().sort()[:40].to_list()
    )
    Xthin = X.filter((pl.col("ticker") != "CCC") | pl.col("date").is_in(thin_dates))
    ythin = y.filter((pl.col("ticker") != "CCC") | pl.col("date").is_in(thin_dates))
    m = HARShrink2Group()
    m.fit(Xthin, ythin)
    h = C.PRIMARY_HORIZON
    st = m.state[h]
    # CCC's stored beta must equal its pooled beta exactly (no own-β blended in).
    b_pooled = _pooled_beta_for(st["pooled"], "CCC")
    assert np.allclose(st["beta"]["CCC"], b_pooled), "thin ticker must use pooled beta outright"
    # And it still predicts validly.
    pred = m.predict(Xthin)
    _assert_valid(pred)
    assert "CCC" in pred["ticker"].unique().to_list()
