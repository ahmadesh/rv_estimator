"""Stage-1 trading-evaluation layer for frozen RV forecasters.

Consumes the frozen prediction parquets (`execution/data/predictions/<model>.parquet`),
truth/benchmark (`targets.parquet`), and the daily RV path (`inputs.parquet`) and turns
each forecaster into a short-vol variance-proxy backtest. This package does NO training and
NO refits (STAGE1_TRADING_EVAL_PLAN.md §6) — the walk-forward purge/embargo is already baked
into the predictions; the only new leakage surface is strategy thresholds, which `pit.py`
keeps strictly point-in-time.

The DSR/CVaR/DM economic *scoring* of the results is a deferred next phase; this package only
produces the per-trade ledger and daily portfolio P&L series the scoring will consume.
"""
