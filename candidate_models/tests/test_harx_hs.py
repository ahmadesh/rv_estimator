"""Smoke test for HARX-HeteroSigma (catalog model 25, Pattern P2).

Synthetic 3-ticker x 500-day panel run through `build_features` (so X carries the
HAR_FEATURES + IV_FEATURES + sqrt_rq the model needs). Asserts predict returns the
required output columns, finite positive rv_hat, monotone quantiles, and that the
predictive sigma actually VARIES per row (the hetero-sigma head is engaged, not a
single constant width).
"""

from __future__ import annotations

import numpy as np
import polars as pl

from candidate_models.harx_hs import HARXHeteroSigma
from rv_eval import config as C
from rv_eval.features import build_features

REQUIRED = ["ticker", "date", "horizon", "rv_hat", "sigma",
            "q05", "q10", "q25", "q50", "q75", "q90", "q95"]


def _synth_panel(n_tickers: int = 3, n_days: int = 500, seed: int = 0):
    rng = np.random.default_rng(seed)
    dates = pl.date_range(pl.date(2010, 1, 1), pl.date(2025, 1, 1), "1d", eager=True)
    dates = dates.filter(dates.dt.weekday() <= 5).head(n_days)
    rows_in, rows_y = [], []
    for ti in range(n_tickers):
        tk = f"T{ti}"
        logh = np.log(2e-4)
        rv = np.empty(n_days)
        ret = np.empty(n_days)
        for d in range(n_days):
            logh = -0.5 + 0.92 * logh + 0.05 * rng.standard_normal()
            h = np.exp(logh)
            ret[d] = np.sqrt(h) * rng.standard_normal()
            rv[d] = h * np.exp(0.3 * rng.standard_normal())
        iv30 = np.sqrt(np.maximum(rv, 1e-8)) * (1.0 + 0.2 * rng.standard_normal(n_days))
        iv30 = np.maximum(iv30, 1e-4)
        rq = rv * rv * (1.0 + 0.5 * rng.random(n_days))      # quarticity ~ rv^2 scale
        vix = 15.0 + 50.0 * np.sqrt(np.maximum(rv, 0)) + 2.0 * rng.standard_normal(n_days)
        rows_in.append(pl.DataFrame({
            "ticker": [tk] * n_days, "date": dates,
            "ret_cc": ret, "total_rv": rv,
            "rs_plus": rv * 0.5, "rs_minus": rv * 0.5, "jump": rv * 0.1,
            "rq": rq,
            "iv_30d": iv30, "iv_60d": iv30 * 1.02, "iv_90d": iv30 * 1.04,
            "iv_slope": np.full(n_days, 0.01), "skew_25d": rng.standard_normal(n_days) * 0.1,
            "vix": vix, "vix3m": vix * 1.05, "vix_slope": rng.standard_normal(n_days) * 0.5,
            "vvix": 90.0 + 10.0 * rng.standard_normal(n_days),
            "vix9d": vix * 0.98, "vix9d_slope": rng.standard_normal(n_days) * 0.5,
        }))
        for h in C.HORIZONS:
            tv = np.array([rv[i + 1:i + 1 + h].sum() if i + 1 + h <= n_days else np.nan
                           for i in range(n_days)])
            rows_y.append(pl.DataFrame({
                "ticker": [tk] * n_days, "date": dates,
                "horizon": [h] * n_days, "target_var": tv,
            }).drop_nulls("target_var").filter(pl.col("target_var").is_not_nan()))
    inputs = pl.concat(rows_in)
    X = build_features(inputs)
    return X, pl.concat(rows_y)


def test_predict_schema_and_finite():
    X, y = _synth_panel()
    m = HARXHeteroSigma()
    m.fit(X, y)
    assert len(m.state) > 0, "model fit no (ticker, horizon) keys"
    pred = m.predict(X)
    assert not pred.is_empty()
    for c in REQUIRED:
        assert c in pred.columns, f"missing output column {c}"
    rv = pred["rv_hat"].to_numpy()
    assert np.all(np.isfinite(rv)) and np.all(rv > 0)
    assert np.all(pred["sigma"].to_numpy() >= 0)
    qs = pred.select(["q05", "q10", "q25", "q50", "q75", "q90", "q95"]).to_numpy()
    assert np.all(np.diff(qs, axis=1) >= -1e-9)


def test_sigma_is_heteroskedastic():
    """The whole point of the model: sigma must vary across rows within a key."""
    X, y = _synth_panel()
    m = HARXHeteroSigma()
    m.fit(X, y)
    pred = m.predict(X)
    # pick one (ticker, horizon) and confirm sigma is not a single constant
    one = pred.filter((pl.col("ticker") == "T0") & (pl.col("horizon") == C.PRIMARY_HORIZON))
    s = one["sigma"].to_numpy()
    assert s.size > 10
    assert np.std(s) > 0, "sigma is constant — hetero-sigma head not engaged"


def test_horizons_covered():
    X, y = _synth_panel()
    m = HARXHeteroSigma()
    m.fit(X, y)
    pred = m.predict(X)
    covered = set(pred["horizon"].unique().to_list())
    assert covered.issubset(set(C.HORIZONS))
    assert len(covered) >= 1
