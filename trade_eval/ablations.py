"""Ablation registry (STAGE1_TRADING_EVAL_PLAN.md §5).

Each ablation toggles **one** signal and becomes one backtest cell. Two kinds:

  - *config-delta ablations* (A2 gate, A3 sizing, A5 risk scale, A7 controls, A9 management)
    are `StrategyConfig` variants enumerated here;
  - *grid ablations* (A1 forecast-vs-IV-only, A4 sleeve-vs-clean-core, A6 ensemble-vs-fallback,
    A8 horizon) need no toggle — they fall out of running multiple models / horizons and are
    composed at scoring time, so they live in `run.py`'s grid and the manifest, not here.

The DSR multiple-testing deflation later counts every cell produced; `cells_for` is the single
place that enumeration is defined.
"""

from __future__ import annotations

from trade_eval import config as cfg
from trade_eval.signals import StrategyConfig

# Baseline: regime gate on, forecast σ-sizing, signal entry, hold-to-expiry.
BASELINE = StrategyConfig(name="baseline")

# Config-delta ablations for a real forecaster.
MODEL_ABLATIONS: tuple[StrategyConfig, ...] = (
    BASELINE,
    StrategyConfig(name="A2_no_gate", use_gate=False),          # A2: gate off
    StrategyConfig(name="A3_flat_size", sizing="flat"),         # A3: forecast sizing off
    StrategyConfig(name="A5_qspread", risk_scale="qspread"),    # A5: quantile-spread risk scale
    StrategyConfig(name="A7_random", entry="random"),           # A7 control: random entry
    StrategyConfig(name="A7_always", entry="always"),           # A7 control: always-sell carry
    StrategyConfig(name="A9_managed", manage=True),             # A9: daily re-gating overlay
)

# The IV-only null: it has no forecast dispersion, so only the entry-vs-management contrast (A9)
# and the hold baseline are meaningful; both flagged `is_benchmark`.
BENCHMARK_ABLATIONS: tuple[StrategyConfig, ...] = (
    StrategyConfig(name="baseline", is_benchmark=True),
    StrategyConfig(name="A9_managed", is_benchmark=True, manage=True),
)


def cells_for(model: str, names: tuple[str, ...] | None = None) -> list[StrategyConfig]:
    """Strategy cells to run for a model, optionally filtered to a subset of ablation names."""
    cells = BENCHMARK_ABLATIONS if model == cfg.BENCHMARK else MODEL_ABLATIONS
    if names is not None:
        cells = tuple(c for c in cells if c.name in names)
    return list(cells)
