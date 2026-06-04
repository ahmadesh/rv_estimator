"""Smoke + invariant tests for Threshold-HAR (CATALOG §3 model 29).

Synthetic 3-ticker x 500-day panel. Asserts: required output columns, finite rv_hat>0,
monotone quantiles, BOTH regimes get exercised in fit, and a sparse regime falls back to the
pooled fit. Runs entirely on the synthetic X (the _AttachMixin synthetic-X fallback path), so it
never touches inputs.parquet.
"""

from __future__ import annotations

import numpy as np
import polars as pl

from rv_eval import config as C
from rv_eval.model_contract import Q_COLS
from candidate_models.threshold_har import ThresholdHAR, _REGIME_COL, _THRESHOLD

_REQUIRED = ["ticker", "date", "horizon", "rv_hat", "sigma"] + Q_COLS
_FEATS = ["log_rv_d", "log_rv_w", "log_rv_m",
          "log_iv", "iv_slope", "skew_25d", "vix", "vix3m", "vix_slope", "vvix"]


def _panel(seed: int = 0, n_days: int = 500, tickers=("AAA", "BBB", "CCC")):
    rng = np.random.default_rng(seed)
    frames = []
    real_dates = (
        pl.datetime_range(pl.datetime(2010, 1, 1), pl.datetime(2030, 1, 1), interval="1d", eager=True)
        .head(n_days)
        .dt.date()
    )
    for t in tickers:
        lv = rng.normal(-9, 0.6, n_days)
        vix = np.clip(15 + 10 * np.cumsum(rng.normal(0, 0.05, n_days)) + rng.normal(0, 2, n_days), 8, 80)
        frames.append(pl.DataFrame({
            "ticker": [t] * n_days,
            "date": real_dates,
            "log_rv_d": lv,
            "log_rv_w": lv + rng.normal(0, 0.1, n_days),
            "log_rv_m": lv + rng.normal(0, 0.1, n_days),
            "log_iv": rng.normal(-4.5, 0.3, n_days),
            "iv_slope": rng.normal(0, 0.05, n_days),
            "skew_25d": rng.normal(0, 0.1, n_days),
            "vix": vix,
            "vix3m": vix + rng.normal(1, 1, n_days),
            "vix_slope": rng.normal(0, 1, n_days),
            "vvix": rng.normal(90, 10, n_days),
            "vix9d_slope": rng.normal(0, 1, n_days),
        }))
    X = pl.concat(frames)
    # targets: long by horizon; target_var ~ exp(log_rv_d) scaled by horizon, positive.
    yrows = []
    for h in C.HORIZONS:
        tv = np.exp(X["log_rv_d"].to_numpy()) * h * np.exp(np.random.default_rng(h).normal(0, 0.2, X.height))
        yrows.append(X.select("ticker", "date").with_columns(
            horizon=pl.lit(h, dtype=pl.Int64), target_var=pl.Series(tv)))
    y = pl.concat(yrows)
    return X, y


def test_required_columns_and_positivity():
    X, y = _panel()
    m = ThresholdHAR()
    m.fit(X, y)
    pred = m.predict(X)
    assert pred.height > 0
    for c in _REQUIRED:
        assert c in pred.columns, f"missing column {c}"
    rv = pred["rv_hat"].to_numpy()
    assert np.all(np.isfinite(rv)) and np.all(rv > 0)
    assert np.all(np.isfinite(pred["sigma"].to_numpy()))


def test_monotone_quantiles():
    X, y = _panel()
    m = ThresholdHAR()
    m.fit(X, y)
    pred = m.predict(X)
    qmat = pred.select(Q_COLS).to_numpy()
    diffs = np.diff(qmat, axis=1)
    assert np.all(diffs >= -1e-9), "quantiles not non-decreasing"


def test_both_regimes_exercised():
    X, y = _panel()
    m = ThresholdHAR()
    m.fit(X, y)
    # Every (ticker,horizon) state should carry both a low and a high regime entry, and across
    # the panel both regimes must have nonzero training rows somewhere.
    assert len(m.state) > 0
    low_total = sum(v for (tk, h, lab), v in m.regime_counts.items() if lab == "low")
    high_total = sum(v for (tk, h, lab), v in m.regime_counts.items() if lab == "high")
    assert low_total > 0 and high_total > 0, "both regimes must be exercised in fit"


def test_sparse_regime_falls_back_to_pooled():
    # Force a sparse HIGH regime: pin vix so its expanding percentile is essentially always
    # below threshold for one ticker -> the high regime gets < _MIN_REGIME_OBS rows -> fallback.
    X, y = _panel()
    # Make ticker AAA monotonically increasing vix: expanding pctile -> ~1 always (all-high),
    # so its LOW regime is sparse and falls back.
    X = X.with_columns(
        pl.when(pl.col("ticker") == "AAA")
        .then(pl.int_range(0, pl.len()).over("ticker").cast(pl.Float64) * 0.1 + 10.0)
        .otherwise(pl.col("vix"))
        .alias("vix")
    )
    m = ThresholdHAR()
    m.fit(X, y)
    assert m.fallbacks > 0, "a sparse regime must trigger a pooled fallback"
    # And the pooled fallback means low and pooled betas coincide for AAA where low was sparse.
    aaa_states = [(h, st) for (tk, h), st in m.state.items() if tk == "AAA"]
    assert aaa_states, "AAA should have fitted states"
    found = False
    for h, st in aaa_states:
        if np.allclose(st["low"][0], st["pooled"][0]):
            found = True
    assert found, "AAA low regime should fall back to pooled betas"
