"""The trading layer's only new leakage surface is strategy thresholds (STAGE1 §6).

These tests pin the no-look-ahead property of `pit.py` the way the whole layer relies on it:
a *future* row must never change a *past* threshold. If `trailing_pctile`/`trailing_rv` ever
regressed to a full-sample statistic, appending a future spike would shift earlier rows and
these assertions would fail.
"""

from __future__ import annotations

import datetime as dt

import polars as pl

from trade_eval import pit


def _frame(values: list[float]) -> pl.DataFrame:
    base = dt.date(2018, 1, 1)
    return pl.DataFrame({
        "ticker": ["A"] * len(values),
        "date": [base + dt.timedelta(days=i) for i in range(len(values))],
        "total_rv": values,
        "v": values,
    })


def test_trailing_pctile_ignores_the_future():
    df = _frame([1.0, 2.0, 3.0, 4.0, 5.0])
    fut = _frame([1.0, 2.0, 3.0, 4.0, 5.0, 1e6])  # same history + a huge future spike

    past = pit.trailing_pctile(df, "v", 0.8, min_periods=1)["v_p80"].to_list()
    with_future = pit.trailing_pctile(fut, "v", 0.8, min_periods=1)["v_p80"].to_list()

    # The first 5 (past) thresholds must be byte-identical whether or not the spike exists later.
    assert with_future[:5] == past
    # And the threshold is expanding: monotone non-decreasing on an increasing series.
    assert past == sorted(past)


def test_trailing_pctile_min_periods_warmup_is_null():
    df = _frame([1.0, 2.0, 3.0])
    out = pit.trailing_pctile(df, "v", 0.8, min_periods=2)["v_p80"].to_list()
    assert out[0] is None  # untrusted until min_periods of history -> caller declines to gate


def test_trailing_rv_ignores_the_future():
    df = _frame([1.0, 1.0, 1.0, 1.0])
    fut = _frame([1.0, 1.0, 1.0, 1.0, 1e6])

    past = pit.trailing_rv(df, 3)["trailing_rv"].to_list()
    with_future = pit.trailing_rv(fut, 3)["trailing_rv"].to_list()

    assert with_future[:4] == past
    assert past[:2] == [None, None]   # warmup before the window is full
    assert past[2] == 3.0 and past[3] == 3.0
