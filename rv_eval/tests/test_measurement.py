"""Measurement-layer correctness on a synthetic 5-min session with a known price path."""

from __future__ import annotations

import datetime as dt

import numpy as np
import polars as pl
import pytest

from rv_eval import config as C
from rv_eval.setup import measurement as meas


def _write_session(tmp: "pathlib.Path", closes: np.ndarray) -> None:  # noqa: F821
    """One winter (EST = UTC-5) RTH session of 1-min bars from a close path."""
    n = closes.shape[0]
    ts = pl.datetime_range(
        dt.datetime(2021, 1, 4, 14, 30), dt.datetime(2021, 1, 4, 14, 30) + dt.timedelta(minutes=n - 1),
        interval="1m", time_zone="UTC", eager=True,
    )
    df = pl.DataFrame({
        "window_start": ts, "open": closes, "high": closes, "low": closes,
        "close": closes, "volume": np.ones(n), "transactions": np.ones(n, dtype=np.int64),
    })
    out = tmp / "ticker=TEST" / "data.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(out)


def _expected_rv(closes: np.ndarray) -> float:
    """Reference RV: open -> 5-min bucket closes (bucket k ends at minute 5k+4)."""
    bucket_close = closes[4::5]                      # 390 mins -> 78 buckets
    path = np.concatenate([[closes[0]], bucket_close])
    r = np.diff(np.log(path))
    return float(np.sum(r ** 2))


@pytest.fixture()
def _patch(tmp_path, monkeypatch):
    monkeypatch.setattr(C, "RAW_MINUTE", tmp_path / "minute")
    monkeypatch.setattr(C, "RAW_CORP", tmp_path / "corp")  # no corp files -> no adjustment
    return tmp_path / "minute"


def test_rv_matches_reference_and_decomposition(_patch):
    rng = np.random.default_rng(0)
    closes = 100.0 * np.exp(np.cumsum(rng.normal(0, 1e-3, 390)))
    _write_session(_patch, closes)

    m = meas.daily_measures("TEST")
    assert m.height == 1
    row = m.row(0, named=True)

    # RV equals the independent reference.
    assert row["rv_intraday"] == pytest.approx(_expected_rv(closes), rel=1e-9)
    # Semivariance decomposition: RS+ + RS- == RV.
    assert row["rs_plus"] + row["rs_minus"] == pytest.approx(row["rv_intraday"], rel=1e-9)
    # Full regular session -> well-behaved, 78 buckets.
    assert row["bar_count"] == 78 and row["well_behaved"] is True
    # Bipower is a (jump-robust) estimate of the same order as RV.
    assert 0 < row["bv"] < 5 * row["rv_intraday"]


def test_monotone_path_has_no_downside_semivariance(_patch):
    closes = np.linspace(100.0, 110.0, 390)          # strictly increasing -> all up returns
    _write_session(_patch, closes)
    row = meas.daily_measures("TEST").row(0, named=True)
    assert row["rs_minus"] == pytest.approx(0.0, abs=1e-12)
    assert row["rs_plus"] == pytest.approx(row["rv_intraday"], rel=1e-9)
