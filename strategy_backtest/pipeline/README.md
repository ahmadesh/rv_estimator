# pipeline — reusable feature/forecaster store for the put-spread backtest

Builds the **cache-once, reuse-everywhere** layer the strategy ablations read. Copied & customized
from `rv_eval/` + `candidate_models/` (imports repointed to `strategy_backtest.pipeline.*`). See
`plan_docs/BACKTEST_DATA_SPEC.md` and `PUT_SPREAD_STRATEGY_DESIGN_v2.md` §3.

## Why a cache (not per-fold rebuild)

Every tier-1 regressor is a **trailing-window** function of raw data ≤ `t`, so building it once over
full history is **bit-identical** to rebuilding it per fold (verified: a truncated rebuild equals the
full-history panel exactly, EWMA included). Tier-2 forecasts come from the same purged/embargoed
walk-forward harness, so caching their *output* changes nothing. Only tier-3 strategy ablations re-run.

## Build (run from repo root; uses `.venv/bin/python`)

```bash
# Tier 1 — PIT panel + targets, then the wide feature matrix
.venv/bin/python -m strategy_backtest.pipeline.setup.prepare_panel
.venv/bin/python -m strategy_backtest.pipeline.features

# Tier 2 — 4 HAR components THEN the ensemble (order matters: ensemble reads component files)
for m in candidate_models.harq:HARQ candidate_models.har_rs:HARRS \
         candidate_models.har_cj:HARCJ candidate_models.har_rs_iv_q:HARRSIVQ \
         candidate_models.ensemble_top:EnsembleTopK ; do
  .venv/bin/python -m strategy_backtest.pipeline.walkforward \
      --model strategy_backtest.pipeline.$m --universe clean_core
done

# Tier 2 ablation — 8y-rolling variant into a sibling dir, kept as EnsembleTopK__roll8y.parquet
SB_TRAIN_WINDOW=rolling SB_PREDICTIONS_ROOT=strategy_backtest/data/predictions_roll8y \
  <repeat the 5 walkforward commands>
mv strategy_backtest/data/predictions_roll8y/EnsembleTopK.parquet \
   strategy_backtest/data/predictions/EnsembleTopK__roll8y.parquet
```

## Outputs — the cache contract (`strategy_backtest/data/`, gitignored)

| File | Grain | Used by tier 3 for |
|---|---|---|
| `features.parquet` | one row per `(ticker, date)`, 52 cols | gates G2/G3 (`iv_30d`,`iv_slope`,`vix`,`vix3m`,`skew_25d`), variance accrual (`total_rv`), VRP (`iv_30d`) |
| `predictions/EnsembleTopK.parquet` | `(ticker, date, horizon)` | `rv_hat`/`sigma` → VRP-tilt sizing + G4 dispersion gate |
| `predictions/EnsembleTopK__roll8y.parquet` | same | §3 expanding-vs-rolling ablation |
| `inputs.parquet`, `targets.parquet`, `predictions/HAR*.parquet` | — | intermediates (targets = training only) |

Per-strike **ORATS chains stay raw** in `back-test-data/orats/` — tier 3 reads them live at entry &
marking; they are not flattened into the panel.

## Customizations vs upstream `rv_eval`

- `config.py` — `RAW_ROOT`→`back-test-data/`, `DATA_ROOT`→`strategy_backtest/data/`,
  `OOS_START=2010-01-01`, `SCORED_TICKERS=CLEAN_CORE`. Env overrides: `SB_RAW_ROOT`, `SB_DATA_ROOT`,
  `SB_OOS_START`, `SB_TRAIN_WINDOW`, `SB_ROLLING_TRAIN_DAYS` (default 8y), `SB_PREDICTIONS_ROOT`.
- `setup/range_vol.py` — added a **minute→daily-OHLC RTH fallback**: the mirror's `daily/` holds only
  cross-asset proxies, so the 10 core tickers' Parkinson/GK/RS are derived from their 1-min bars.
- `setup/cross_asset.py` — reads `RAW_DAILY` (the mirror) instead of the Ex-Disk `DAILY_LAKE`.

## Verify

`features` PIT-identity (truncated == full), ensemble keys all `n_comp≥2` with `rv_hat>0`/`sigma≥0`/
monotone tails, first prediction ≥2010, h=22 cov90 ≈ 0.93. See the build log / design §3.5.
