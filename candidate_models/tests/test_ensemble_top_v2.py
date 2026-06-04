"""Synthetic tests for EnsembleTopK-v2 (catalog §21).

Exercises the leakage-safe regime-conditional weighting + top-K on toy component frames
written to a temporary predictions dir, with a temporary targets parquet so the regime
label and the past-performance scoring are fully controlled. No real data is touched.
"""

from __future__ import annotations

import numpy as np
import polars as pl
import pytest

import candidate_models.ensemble_top_v2 as etv2
from candidate_models.ensemble_top_v2 import EnsembleTopKV2, _QCOLS

HORIZONS = (1, 5, 10, 22, 42)


def _toy_targets(tmp_path, dates, tickers, bucket_of):
    """A targets parquet: one regime bucket per (ticker,date), target_var long by horizon."""
    rng = np.random.default_rng(0)
    rows = []
    for tk in tickers:
        for d in dates:
            for h in HORIZONS:
                rows.append(
                    dict(ticker=tk, date=d, horizon=h,
                         target_var=float(0.02 + 0.01 * rng.random()),
                         iv_pctile_bucket=bucket_of(tk, d))
                )
    t = pl.DataFrame(rows)
    p = tmp_path / "targets.parquet"
    t.write_parquet(p)
    return t, p


def _toy_component(name, dates, tickers, rv_fn, sigma=0.01):
    rows = []
    for tk in tickers:
        for d in dates:
            for h in HORIZONS:
                rows.append(dict(ticker=tk, date=d, horizon=h,
                                 rv_hat=float(rv_fn(tk, d, h)), sigma=float(sigma)))
    return name, pl.DataFrame(rows)


@pytest.fixture
def env(tmp_path, monkeypatch):
    """Point the module at a temp predictions dir + temp targets, with a small pool."""
    pred_dir = tmp_path / "predictions"
    pred_dir.mkdir()
    monkeypatch.setattr(etv2, "PRED_DIR", pred_dir)
    monkeypatch.setattr(etv2.C, "TARGETS_PARQUET", tmp_path / "targets.parquet")
    return tmp_path, pred_dir


def _write(pred_dir, name, df):
    df.with_columns(model=pl.lit(name)).write_parquet(pred_dir / f"{name}.parquet")


def test_better_component_gets_more_weight(env, monkeypatch):
    tmp_path, pred_dir = env
    dates = list(pl.date_range(pl.date(2018, 1, 1), pl.date(2019, 12, 31),
                               interval="1d", eager=True))
    tickers = ["SPY", "QQQ"]
    truth = 0.025  # constant target so a constant forecaster can be exactly right

    def bucket_of(tk, d):
        return 0
    _, _ = _toy_targets(tmp_path, dates, tickers, bucket_of)
    # override target_var to a constant so "good" component is provably better
    t = pl.read_parquet(tmp_path / "targets.parquet").with_columns(
        target_var=pl.lit(truth))
    t.write_parquet(tmp_path / "targets.parquet")

    # restrict pool to two known names
    monkeypatch.setattr(etv2, "CANDIDATE_POOL", ["GOOD", "BAD"])
    monkeypatch.setattr(etv2, "TOP_K", 2)
    _write(pred_dir, *_toy_component("GOOD", dates, tickers, lambda tk, d, h: truth))
    _write(pred_dir, *_toy_component("BAD", dates, tickers, lambda tk, d, h: truth * 4))

    m = EnsembleTopKV2()
    X = pl.DataFrame({"ticker": ["SPY"] * len(dates), "date": dates})
    # y_train = all targets (the "past")
    y = pl.read_parquet(tmp_path / "targets.parquet")
    m.fit(X, y)
    w = m._wpool[22]
    assert w["GOOD"] > w["BAD"], f"better component must get more weight: {w}"
    assert abs(sum(w.values()) - 1.0) < 1e-9


def test_regime_conditional_weights_differ(env, monkeypatch):
    """A component good only in bucket 0 should outweigh in bucket 0, lose in bucket 4."""
    tmp_path, pred_dir = env
    dates = list(pl.date_range(pl.date(2017, 1, 1), pl.date(2019, 12, 31),
                               interval="1d", eager=True))
    tickers = ["SPY", "QQQ", "IWM"]
    # half the dates bucket 0, half bucket 4 (deterministic split)
    cut = dates[len(dates) // 2]

    def bucket_of(tk, d):
        return 0 if d < cut else 4
    t, _ = _toy_targets(tmp_path, dates, tickers, bucket_of)
    # make target depend on bucket so A is accurate in bucket0, B accurate in bucket4
    t = t.with_columns(
        target_var=pl.when(pl.col("iv_pctile_bucket") == 0).then(0.02).otherwise(0.08))
    t.write_parquet(tmp_path / "targets.parquet")

    monkeypatch.setattr(etv2, "CANDIDATE_POOL", ["A", "B"])
    monkeypatch.setattr(etv2, "TOP_K", 2)
    monkeypatch.setattr(etv2, "MIN_CELL_OBS", 10)
    _write(pred_dir, *_toy_component("A", dates, tickers, lambda tk, d, h: 0.02))
    _write(pred_dir, *_toy_component("B", dates, tickers, lambda tk, d, h: 0.08))

    m = EnsembleTopKV2()
    X = pl.DataFrame({"ticker": ["SPY"] * len(dates), "date": dates})
    m.fit(X, pl.read_parquet(tmp_path / "targets.parquet"))
    w0 = m._wregime[(22, 0)]
    w4 = m._wregime[(22, 4)]
    assert w0["A"] > w0["B"], f"A should win bucket0: {w0}"
    assert w4["B"] > w4["A"], f"B should win bucket4: {w4}"


def test_no_leakage_weights_change_with_train_window(env, monkeypatch):
    """Weights estimated on an earlier y_train must NOT see later (test-window) targets.

    We fit on a window where component A is best, then prove that adding *future* rows where
    B is best (rows the walk-forward would withhold) changes the weights — i.e. fit() only
    uses the y it is handed, never the full sample.
    """
    tmp_path, pred_dir = env
    dates = list(pl.date_range(pl.date(2017, 1, 1), pl.date(2019, 12, 31),
                               interval="1d", eager=True))
    tickers = ["SPY", "QQQ"]
    mid = dates[len(dates) // 2]

    def bucket_of(tk, d):
        return 0
    t, _ = _toy_targets(tmp_path, dates, tickers, bucket_of)
    # early target=0.02 (A right), late target=0.10 (B right)
    t = t.with_columns(
        target_var=pl.when(pl.col("date") < mid).then(0.02).otherwise(0.10))
    t.write_parquet(tmp_path / "targets.parquet")

    monkeypatch.setattr(etv2, "CANDIDATE_POOL", ["A", "B"])
    monkeypatch.setattr(etv2, "TOP_K", 2)
    _write(pred_dir, *_toy_component("A", dates, tickers, lambda tk, d, h: 0.02))
    _write(pred_dir, *_toy_component("B", dates, tickers, lambda tk, d, h: 0.10))

    m = EnsembleTopKV2()
    yfull = pl.read_parquet(tmp_path / "targets.parquet")
    X = pl.DataFrame({"ticker": ["SPY"] * len(dates), "date": dates})

    # fit only on the EARLY half (the leakage-safe train window) -> A should win
    y_early = yfull.filter(pl.col("date") < mid)
    m.fit(X, y_early)
    w_early = m._wpool[22]
    # fit on the full sample -> B's good late rows pull weight toward B
    m.fit(X, yfull)
    w_full = m._wpool[22]
    assert w_early["A"] > w_full["A"], (
        "weights must depend on the y_train window (no full-sample peeking): "
        f"early={w_early} full={w_full}")


def test_predict_output_contract(env, monkeypatch):
    tmp_path, pred_dir = env
    dates = list(pl.date_range(pl.date(2017, 1, 1), pl.date(2019, 12, 31),
                               interval="1d", eager=True))
    tickers = ["SPY", "QQQ"]
    rng = np.random.default_rng(1)

    def bucket_of(tk, d):
        return int(rng.integers(0, 5))
    # stable bucket per (ticker,date)
    bmap = {(tk, d): int(rng.integers(0, 5)) for tk in tickers for d in dates}
    _, _ = _toy_targets(tmp_path, dates, tickers, lambda tk, d: bmap[(tk, d)])

    monkeypatch.setattr(etv2, "CANDIDATE_POOL", ["A", "B", "Cc"])
    monkeypatch.setattr(etv2, "TOP_K", 3)
    monkeypatch.setattr(etv2, "MIN_CELL_OBS", 10)
    _write(pred_dir, *_toy_component("A", dates, tickers,
                                     lambda tk, d, h: 0.02 + 0.001 * h))
    _write(pred_dir, *_toy_component("B", dates, tickers,
                                     lambda tk, d, h: 0.03 + 0.001 * h))
    _write(pred_dir, *_toy_component("Cc", dates, tickers,
                                     lambda tk, d, h: 0.025 + 0.001 * h))

    m = EnsembleTopKV2()
    y = pl.read_parquet(tmp_path / "targets.parquet")
    train_dates = [d for d in dates if d < dates[len(dates) // 2]]
    test_dates = [d for d in dates if d >= dates[len(dates) // 2]]
    Xtr = pl.DataFrame({"ticker": ["SPY"] * len(train_dates), "date": train_dates})
    m.fit(Xtr, y.filter(pl.col("date") < dates[len(dates) // 2]))
    Xte = pl.DataFrame(
        {"ticker": ["SPY"] * len(test_dates) + ["QQQ"] * len(test_dates),
         "date": test_dates * 2})
    out = m.predict(Xte)

    assert not out.is_empty()
    assert out.columns == ["ticker", "date", "horizon", "rv_hat", "sigma", *_QCOLS]
    rv = out["rv_hat"].to_numpy()
    assert np.all(np.isfinite(rv)) and np.all(rv > 0)
    assert np.all(np.isfinite(out["sigma"].to_numpy())) and np.all(out["sigma"].to_numpy() >= 0)
    # monotone quantiles row-wise
    qmat = out.select(_QCOLS).to_numpy()
    assert np.all(np.diff(qmat, axis=1) >= -1e-12), "quantiles must be non-decreasing"
    assert set(out["horizon"].unique().to_list()) <= set(HORIZONS)


def test_min_components_drops_thin_keys(env, monkeypatch):
    """A key with only one component available must be dropped (never imputed)."""
    tmp_path, pred_dir = env
    dates = list(pl.date_range(pl.date(2017, 1, 1), pl.date(2018, 6, 30),
                               interval="1d", eager=True))
    tickers = ["SPY"]
    _, _ = _toy_targets(tmp_path, dates, tickers, lambda tk, d: 0)

    monkeypatch.setattr(etv2, "CANDIDATE_POOL", ["A", "B"])
    monkeypatch.setattr(etv2, "TOP_K", 2)
    _write(pred_dir, *_toy_component("A", dates, tickers, lambda tk, d, h: 0.02))
    # B only covers a single date -> most keys have just A
    one = dates[:1]
    _write(pred_dir, *_toy_component("B", one, tickers, lambda tk, d, h: 0.02))

    m = EnsembleTopKV2()
    X = pl.DataFrame({"ticker": ["SPY"] * len(dates), "date": dates})
    m.fit(X, pl.read_parquet(tmp_path / "targets.parquet"))
    out = m.predict(X)
    if not out.is_empty():
        # only the single date where both A and B exist may survive
        assert out["date"].unique().to_list() == one
