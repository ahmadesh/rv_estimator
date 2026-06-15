"""Self-contained v2 put-credit-spread backtest (tier 3 of the put-spread plan).

Reads the cached features + EnsembleTopK forecasts under `strategy_backtest/data/` and the raw
ORATS chains under `strategy_backtest/back-test-data/orats/`, and runs the lean-core, hold-to-expiry
put-credit-spread book described in `plan_docs/PUT_SPREAD_STRATEGY_DESIGN_v2.md`. Entry point:

    .venv/bin/python -m strategy_backtest.backtest.run
"""
