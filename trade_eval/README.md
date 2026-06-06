# trade_eval — Stage-1 trading-evaluation pipeline

Turns the **frozen** RV forecasters into short-vol variance-proxy backtest results, so the
economic value of each forecast (gate / sizing / management) can be scored downstream. This is
the operational half of [`STAGE1_TRADING_EVAL_PLAN.md`](STAGE1_TRADING_EVAL_PLAN.md); it mirrors
the `rv_eval/` forecasting pipeline's conventions (polars, config-driven, leakage-safe, tested).

**This layer does no training and no refits.** It consumes only the artifacts the forecasting
study already produced:

| Input | Path | Used for |
|---|---|---|
| Frozen predictions | `execution/data/predictions/<model>.parquet` | `rv_hat`, `sigma`, `q05…q95` per `(ticker,date,horizon)` |
| Truth + benchmark | `execution/data/targets.parquet` | `target_var`, `iv2`, `iv_pctile_bucket`, `post_shock` |
| Daily RV path | `execution/data/inputs.parquet` | `total_rv` for the §3.5 variance-accrual mark + trading calendar |

## Leakage model

The walk-forward purge/embargo is **already baked into the predictions** (`fold_id`/dates), so
we inherit it for free. The *only* new leakage surface is **strategy thresholds**, and they are
confined to `pit.py`:

- the dispersion (`sigma/rv_hat`) 80th-pctile gate and its terciles, and the IV-only
  benchmark's trailing RV, are all **trailing/expanding point-in-time** — a value at `t` sees
  only rows dated `≤ t`. `tests/test_leakage.py` pins this: appending a future spike never
  changes a past threshold.
- `iv_pctile_bucket` / `post_shock` are already point-in-time in `targets.parquet` and reused as-is.
- strategy constants (`K`, `SIZE_CAP`, `C_BPS`, `TAKE_FRAC`, …) are config set once, never fit
  on the OOS P&L being scored.

## Pipeline

```
forecast(rv_hat, σ, q05..q95) ⋈ truth → vrp_score → regime gate → size → P&L (hold or managed) → portfolio
        signals.py                      signals.py   signals.py   backtest.py / management.py   portfolio.py
```

| Module | Role |
|---|---|
| `config.py` | strategy knobs; reuses paths/universe/group/horizons from `rv_eval.config` |
| `pit.py` | point-in-time helpers (leakage core): `trailing_pctile`, `trailing_rv` |
| `signals.py` | `vrp_score`, regime gate `{trade,reduce,avoid}`, inverse-risk size; `StrategyConfig` holds the ablation toggles |
| `benchmark.py` | IV-only null: synthesizes a predictions-shaped frame with `rv_hat := trailing_RV` |
| `backtest.py` | terminal variance-proxy payoff `size·sign·(iv2−target_var)−cost`; per-trade ledger |
| `management.py` | §3.5 daily variance-accrual mark + early-exit rules (A9 managed book) |
| `portfolio.py` | one-position-per-group composition → daily portfolio P&L series |
| `ablations.py` | registry of `StrategyConfig` cells (A2/A3/A5/A7/A9); A1/A4/A6/A8 are grid contrasts |
| `run.py` | drives the `model × horizon × ablation` grid → `results/` + `manifest.parquet` |

## Running

```bash
.venv/bin/python -m trade_eval.run                                 # full default shortlist grid
.venv/bin/python -m trade_eval.run --models EnsembleTopK,IV-only --horizons 22
.venv/bin/python -m trade_eval.run --models all                    # every prediction file on disk
.venv/bin/python -m trade_eval.run --ablations baseline,A9_managed
.venv/bin/python -m pytest trade_eval/tests/ -q
```

Default shortlist (§1.1): `EnsembleTopK`, `HAR-X`, `HAR-Shrink2Group`, `PanelHAR-FE`,
`HAR-ENet` (h∈{5,10} only) and the `IV-only` benchmark — **104 cells** over the 2018→2026 OOS folds.

## Outputs (`trade_eval/results/`, gitignored)

- `ledger/<model>__h<h>__<ablation>.parquet` — one row per trade (`entry_date`, `gate`, `size`,
  `vrp_score`, `iv2`, `target_var`, `gross_pnl`, `cost`, `pnl`, `exit_k/reason/date`, `managed`).
- `portfolio/<model>__h<h>__<ablation>.parquet` — daily one-per-group P&L series.
- `manifest.parquet` — every cell evaluated; the count feeds the later DSR multiple-testing deflation.

## Ablation map (how each §5 contrast is produced)

| Ablation | How it is realized |
|---|---|
| A1 forecast vs IV-only | model cells vs the `IV-only` cells |
| A2 gate on/off | `baseline` vs `A2_no_gate` |
| A3 sizing on/off | `baseline` vs `A3_flat_size` |
| A4 sleeve vs clean-core (hard names) | compare sleeve models vs clean-core models on `hard_cases` (eval-time slice) |
| A5 σ vs quantile-spread size | `baseline` vs `A5_qspread` |
| A6 EnsembleTopK vs HAR-X | the two model cells |
| A7 controls | `A7_random`, `A7_always` |
| A8 horizon sweep | the `h ∈ {5,10,22}` grid |
| A9 managed vs hold | `baseline` vs `A9_managed` |

## Deferred (next phase — not in this pipeline)

The §4 economic **scoring** — Deflated Sharpe, CVaR(95/99), max-drawdown, Sortino, turnover/cost
break-even, P&L-series DM + Hansen SPA with a stationary block bootstrap (block ≥ 22), and the
A1–A9 attribution / go-no-go tables (§5, §7, §8) — runs on these result files later. The reuse
base for that phase is `rv_eval/metrics/` (`tier2.diebold_mariano`, the MCS block bootstrap).

## Stage-1 abstractions (made exact in Stage-2 ORATS)

Variance-payoff proxy (no strikes/greeks/smile); flat per-group bps cost as a fraction of
premium sold; the management mark approximates remaining carry as `iv2·(h−k)/h`; structures
collapse to a per-group notional haircut. These are enough to **rank** models, not to price a
book — Stage-2 instantiates real option marks.
