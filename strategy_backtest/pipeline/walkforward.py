"""Purged + embargoed rolling-origin walk-forward (eval plan §10).

Slices the precomputed panel by date and drives a model's fit/predict — it never recomputes
targets. Refit monthly (configurable); the test block is the dates until the next refit, so each
OOS date is predicted exactly once by the model fit at the start of its month.

Leakage guards on the trading-day index:
  - Purge:   a training row at date d is kept for horizon h only if its forward target window
             (d+1..d+h) ends at least EMBARGO_EXTRA days before the test block starts.
  - Embargo: the EMBARGO_EXTRA-day gap above, applied per horizon (gap = h + EMBARGO_EXTRA).

Usage:
    python -m strategy_backtest.pipeline.walkforward                                   # default HAR reference
    python -m strategy_backtest.pipeline.walkforward --model strategy_backtest.pipeline.model_contract:HARX --universe clean_core
    python -m strategy_backtest.pipeline.walkforward --benchmarks --universe clean_core   # all reference models
"""

from __future__ import annotations

import argparse
import importlib
import time

import polars as pl

from strategy_backtest.pipeline import config as C
from strategy_backtest.pipeline.features import build_features
from strategy_backtest.pipeline.model_contract import BENCHMARKS, Model


def load_model(spec: str) -> Model:
    module_name, cls_name = spec.split(":")
    cls = getattr(importlib.import_module(module_name), cls_name)
    return cls()


def _merge_predictions(path, new: pl.DataFrame, name: str) -> pl.DataFrame:
    """Upsert `new` into any existing predictions file for this model.

    Predictions are keyed by (ticker, date, horizon). A run only ever touches the tickers
    in its `--universe`, so running e.g. ``clean_core`` then ``hard_cases`` for the same model
    *accumulates* rather than clobbering: rows for tickers in this run are replaced, all other
    tickers are preserved. Re-running the same universe simply refreshes its rows.
    """
    if new.is_empty():
        return new
    new_tickers = set(new["ticker"].unique().to_list())
    if path.exists():
        old = pl.read_parquet(path)
        if "model" not in old.columns:        # tolerate legacy files written before the model col
            old = old.with_columns(model=pl.lit(name))
        old = old.filter(~pl.col("ticker").is_in(new_tickers))
        combined = pl.concat([old, new], how="diagonal_relaxed")
    else:
        combined = new
    return combined.unique(["model", "ticker", "date", "horizon"], keep="last").sort(
        "ticker", "horizon", "date")


def _with_idx(df: pl.DataFrame, idx: pl.DataFrame) -> pl.DataFrame:
    return df.join(idx, on="date", how="inner")


def _refit_starts(idx: pl.DataFrame) -> list[int]:
    """First trading-day index of each month at/after OOS_START with enough training history."""
    oos = (
        idx.filter(pl.col("date") >= pl.lit(C.OOS_START).str.to_date())
        .with_columns(ym=pl.col("date").dt.strftime("%Y-%m"))
        .group_by("ym").agg(date_idx=pl.col("date_idx").min())
        .sort("date_idx")
    )
    return [i for i in oos["date_idx"].to_list() if i >= C.MIN_TRAIN_DAYS]


def run(model: Model, X: pl.DataFrame, y: pl.DataFrame) -> pl.DataFrame:
    """Roll the walk-forward for one model; return pooled OOS predictions."""
    cal = X.select("date").unique().sort("date").with_row_index("date_idx")
    Xi = _with_idx(X, cal)
    yi = _with_idx(y, cal)
    starts = _refit_starts(cal)
    last_idx = int(cal["date_idx"].max())

    preds: list[pl.DataFrame] = []
    for fold_id, ts in enumerate(starts):
        te = starts[fold_id + 1] if fold_id + 1 < len(starts) else last_idx + 1
        lo = ts - C.ROLLING_TRAIN_DAYS if C.TRAIN_WINDOW == "rolling" else 0

        X_train = Xi.filter((pl.col("date_idx") >= lo) & (pl.col("date_idx") < ts))
        # Per-horizon purge + embargo: keep train target rows whose window ends before the gap.
        y_train = pl.concat([
            yi.filter((pl.col("horizon") == h) & (pl.col("date_idx") >= lo)
                      & (pl.col("date_idx") <= ts - h - C.EMBARGO_EXTRA))
            for h in C.HORIZONS
        ])
        X_test = Xi.filter((pl.col("date_idx") >= ts) & (pl.col("date_idx") < te))
        if y_train.is_empty() or X_test.is_empty():
            continue

        model.fit(X_train.drop("date_idx"), y_train.drop("date_idx"))
        fp = model.predict(X_test.drop("date_idx"))
        if not fp.is_empty():
            preds.append(fp.with_columns(fold_id=pl.lit(fold_id, dtype=pl.Int32)))

    if not preds:
        return pl.DataFrame()
    return pl.concat(preds).unique(["ticker", "date", "horizon"], keep="last").sort(
        "ticker", "horizon", "date")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model", default="strategy_backtest.pipeline.model_contract:HARReference")
    ap.add_argument("--benchmarks", action="store_true", help="run all reference benchmarks")
    ap.add_argument("--universe", default="all", choices=["clean_core", "hard_cases", "all"])
    args = ap.parse_args()

    X = build_features(pl.read_parquet(C.INPUTS_PARQUET))
    y = pl.read_parquet(C.TARGETS_PARQUET)
    keep = set(C.tickers_for(args.universe))
    X = X.filter(pl.col("ticker").is_in(keep))
    y = y.filter(pl.col("ticker").is_in(keep))

    models = [c() for c in BENCHMARKS] if args.benchmarks else [load_model(args.model)]
    C.PREDICTIONS_ROOT.mkdir(parents=True, exist_ok=True)
    for m in models:
        t0 = time.time()
        p = run(m, X, y)
        if not p.is_empty():
            p = p.with_columns(model=pl.lit(m.name))     # name travels with the data, not the filename
        out = C.PREDICTIONS_ROOT / f"{m.name}.parquet"
        merged = _merge_predictions(out, p, m.name)
        merged.write_parquet(out)
        span = (str(p["date"].min()), str(p["date"].max())) if not p.is_empty() else ("-", "-")
        print(f"{m.name:6s}: {p.height:7,} new OOS preds (file now {merged.height:,})  "
              f"span={span}  -> {out}  ({time.time()-t0:.1f}s)")


if __name__ == "__main__":
    main()
