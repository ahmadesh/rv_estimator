"""Self-contained smoke test for model 12, the equal-weight EnsembleTopK combiner.

Creates tiny fake component prediction parquets in tmp_path, points the model's
COMPONENTS / PRED_DIR at them, and verifies the combination math and output schema.
"""

from __future__ import annotations

import datetime as dt

import numpy as np
import polars as pl

import candidate_models.ensemble_top as ens
from candidate_models.ensemble_top import EnsembleTopK

Q_COLS = ["q05", "q10", "q25", "q50", "q75", "q90", "q95"]
REQUIRED = ["ticker", "date", "horizon", "rv_hat", "sigma"] + Q_COLS


def _fake_component(name: str, rows: list[dict]) -> pl.DataFrame:
    return pl.DataFrame(
        [
            {
                "ticker": r["ticker"],
                "date": r["date"],
                "horizon": np.int32(r["horizon"]),
                "rv_hat": float(r["rv_hat"]),
                "sigma": float(r["sigma"]),
                "model": name,
            }
            for r in rows
        ]
    )


def test_ensemble_combines_equal_weight(tmp_path, monkeypatch):
    d0 = dt.date(2020, 1, 2)
    d1 = dt.date(2020, 1, 3)

    # Three fake components. Key (AAA, d0, h=1) has all 3; (AAA, d1, h=1) has only 1
    # (only A) -> must be dropped (< MIN_COMPONENTS). (BBB, d0, h=22) has 2 -> kept.
    a = _fake_component("A", [
        {"ticker": "AAA", "date": d0, "horizon": 1, "rv_hat": 0.0001, "sigma": 0.00002},
        {"ticker": "AAA", "date": d1, "horizon": 1, "rv_hat": 0.0005, "sigma": 0.00010},
        {"ticker": "BBB", "date": d0, "horizon": 22, "rv_hat": 0.0020, "sigma": 0.00050},
    ])
    b = _fake_component("B", [
        {"ticker": "AAA", "date": d0, "horizon": 1, "rv_hat": 0.0002, "sigma": 0.00004},
        {"ticker": "BBB", "date": d0, "horizon": 22, "rv_hat": 0.0030, "sigma": 0.00070},
    ])
    c = _fake_component("C", [
        {"ticker": "AAA", "date": d0, "horizon": 1, "rv_hat": 0.0003, "sigma": 0.00006},
    ])

    a.write_parquet(tmp_path / "A.parquet")
    b.write_parquet(tmp_path / "B.parquet")
    c.write_parquet(tmp_path / "C.parquet")

    monkeypatch.setattr(ens, "COMPONENTS", ["A", "B", "C"])
    monkeypatch.setattr(ens, "PRED_DIR", tmp_path)

    # X is the feature matrix: one row per (ticker, date), no horizon column.
    X = pl.DataFrame({"ticker": ["AAA", "AAA", "BBB"], "date": [d0, d1, d0]})

    m = EnsembleTopK()
    m.fit(X, pl.DataFrame())  # no-op
    out = m.predict(X)

    # Schema: exactly the 12 required columns.
    assert out.columns == REQUIRED

    # The single-component key (AAA, d1) is dropped (< 2 components).
    keys = set(zip(out["ticker"], out["date"].cast(pl.Utf8), out["horizon"]))
    assert ("AAA", "2020-01-02", 1) in keys
    assert ("BBB", "2020-01-02", 22) in keys
    assert ("AAA", "2020-01-03", 1) not in keys
    assert out.height == 2

    # Finite, positive rv_hat.
    assert out["rv_hat"].is_finite().all()
    assert (out["rv_hat"] > 0).all()

    # Monotone quantiles row-wise.
    qv = out.select(Q_COLS).to_numpy()
    assert np.all(np.diff(qv, axis=1) >= 0)

    # q50 finite and bracketed by q05/q95.
    assert (out["q05"] <= out["q50"]).all()
    assert (out["q50"] <= out["q95"]).all()

    # rv_hat is the equal-weight mean of the available components.
    row = out.filter((pl.col("ticker") == "AAA") & (pl.col("horizon") == 1)).row(0, named=True)
    expected_mean = (0.0001 + 0.0002 + 0.0003) / 3.0
    assert abs(row["rv_hat"] - expected_mean) < 1e-12

    # sigma = sqrt(mean(sigma^2) + var(rv_hat)) over the 3 components.
    comp_rv = np.array([0.0001, 0.0002, 0.0003])
    comp_sig = np.array([0.00002, 0.00004, 0.00006])
    expected_sigma = np.sqrt(np.mean(comp_sig ** 2) + np.var(comp_rv, ddof=0))
    assert abs(row["sigma"] - expected_sigma) < 1e-12

    # BBB key: mean of the 2 components present.
    rowb = out.filter(pl.col("ticker") == "BBB").row(0, named=True)
    assert abs(rowb["rv_hat"] - (0.0020 + 0.0030) / 2.0) < 1e-12
