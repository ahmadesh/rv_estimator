"""End-to-end smoke test on real ORATS (auto-skipped when the raw lake is absent).

Runs ONE small cell — EnsembleTopK, h=22, iron_condor / hold / none — over a short slice and
asserts the engine produces a well-formed ledger that `trade_eval.portfolio` can compose. This is
a wiring/shape check, not an economic claim.
"""

from __future__ import annotations

import polars as pl
import pytest

from stage2_trade_eval import config as cfg

pytestmark = pytest.mark.skipif(
    not (cfg.RAW_ORATS / "ticker=SPY").exists(),
    reason="ORATS raw lake not present",
)


def test_one_cell_end_to_end():
    from trade_eval import portfolio
    from stage2_trade_eval import engine
    from stage2_trade_eval import structures, management, hedge  # noqa: F401

    targets = pl.read_parquet(cfg.TARGETS_PARQUET)
    inputs = pl.read_parquet(cfg.INPUTS_PARQUET)
    preds = pl.read_parquet(cfg.PREDICTIONS_ROOT / f"{cfg.PRIMARY}.parquet")
    # keep it fast: SPY only, one year of entries
    preds_h = preds.filter(
        (pl.col("horizon") == cfg.PRIMARY_HORIZON)
        & (pl.col("ticker") == "SPY")
        & (pl.col("date") >= pl.date(2020, 1, 1)) & (pl.col("date") < pl.date(2021, 1, 1))
    )
    assert not preds_h.is_empty(), "no SPY 2020 h22 predictions to test"

    ledger = engine.run_cell(preds_h, targets, inputs, cfg.PRIMARY,
                             "iron_condor", "hold", "none")
    assert set(engine.LEDGER_COLS) == set(ledger.columns)
    if ledger.is_empty():
        pytest.skip("no trades cleared liquidity/credit filters in the slice")
    assert ledger["size"].min() > 0
    assert ledger["exit_date"].null_count() == 0
    daily = portfolio.to_daily_portfolio(ledger)
    assert not daily.is_empty()
    assert daily["pnl"].is_finite().all()
