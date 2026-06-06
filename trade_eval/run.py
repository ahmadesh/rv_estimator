"""Stage-1 result driver — produce backtest results for the model × horizon × ablation grid.

Consumes only frozen prediction parquets (and the synthesized IV-only benchmark); for every
cell it writes a per-trade ledger and a daily one-per-group portfolio P&L series, and records
the cell in a manifest (the count feeds the later DSR multiple-testing deflation, §6). It
computes **no economic metrics** — DSR / CVaR / DM / SPA scoring is the deferred next phase.

Usage:
    python -m trade_eval.run                                   # full default shortlist grid
    python -m trade_eval.run --models EnsembleTopK,IV-only --horizons 22
    python -m trade_eval.run --models all                      # every prediction file on disk
    python -m trade_eval.run --ablations baseline,A9_managed
"""

from __future__ import annotations

import argparse
import time
from datetime import datetime, timezone

import polars as pl

from trade_eval import ablations, backtest, benchmark, portfolio
from trade_eval import config as cfg


def _resolve_models(arg: str) -> list[str]:
    if arg == "shortlist":
        return list(cfg.SHORTLIST)
    if arg == "all":
        files = sorted(p.stem for p in cfg.PREDICTIONS_ROOT.glob("*.parquet"))
        return [*files, cfg.BENCHMARK]
    return [m.strip() for m in arg.split(",") if m.strip()]


def _load_predictions(model: str, targets: pl.DataFrame, inputs: pl.DataFrame) -> pl.DataFrame:
    if model == cfg.BENCHMARK:
        return benchmark.build_predictions(targets, inputs)
    path = cfg.prediction_path(model)
    if not path.exists():
        raise FileNotFoundError(f"no prediction file for {model!r}: {path}")
    return pl.read_parquet(path)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--models", default="shortlist",
                    help="'shortlist' (default), 'all', or comma-separated model names")
    ap.add_argument("--horizons", default=None,
                    help="comma-separated horizons (default: each model's configured sweep)")
    ap.add_argument("--ablations", default=None,
                    help="comma-separated ablation names (default: all registered for the model)")
    ap.add_argument("--no-manifest", action="store_true",
                    help="skip writing manifest.parquet (for race-free parallel per-model "
                         "orchestration; rebuild the manifest centrally afterward)")
    args = ap.parse_args()

    models = _resolve_models(args.models)
    req_horizons = (
        tuple(int(h) for h in args.horizons.split(",")) if args.horizons else None
    )
    req_ablations = tuple(args.ablations.split(",")) if args.ablations else None

    targets = pl.read_parquet(cfg.TARGETS_PARQUET)
    inputs = pl.read_parquet(cfg.INPUTS_PARQUET)
    cfg.LEDGER_ROOT.mkdir(parents=True, exist_ok=True)
    cfg.PORTFOLIO_ROOT.mkdir(parents=True, exist_ok=True)

    manifest: list[dict] = []
    run_ts = datetime.now(timezone.utc).isoformat(timespec="seconds")

    for model in models:
        preds = _load_predictions(model, targets, inputs)
        horizons = cfg.horizons_for(model)
        if req_horizons is not None:
            horizons = tuple(h for h in horizons if h in req_horizons)

        for h in horizons:
            preds_h = preds.filter(pl.col("horizon") == h)
            if preds_h.is_empty():
                continue
            for sc in ablations.cells_for(model, req_ablations):
                t0 = time.time()
                ledger = backtest.run_cell(preds_h, targets, inputs, sc, model)
                daily = portfolio.to_daily_portfolio(ledger)

                stem = f"{model}__h{h}__{sc.name}"
                ledger.write_parquet(cfg.LEDGER_ROOT / f"{stem}.parquet")
                daily.write_parquet(cfg.PORTFOLIO_ROOT / f"{stem}.parquet")

                manifest.append({
                    "model": model, "horizon": h, "ablation": sc.name,
                    "is_benchmark": sc.is_benchmark, "managed": sc.manage,
                    "n_trades": ledger.height, "n_days": daily.height,
                    "pnl_sum": float(ledger["pnl"].sum()) if ledger.height else 0.0,
                    "run_ts": run_ts,
                })
                print(f"{model:18s} h={h:<2d} {sc.name:14s}: "
                      f"{ledger.height:5,} trades  {daily.height:4,} days  ({time.time()-t0:.1f}s)")

    if args.no_manifest:
        print(f"\n{len(manifest)} cells this run -> {cfg.RESULTS_ROOT}  (manifest write skipped)")
        return

    man = pl.DataFrame(manifest)
    cfg.MANIFEST_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    # Upsert by cell key so incremental reruns refresh their cells instead of clobbering the
    # full-grid manifest the DSR multiple-testing deflation later counts.
    keys = ["model", "horizon", "ablation"]
    if cfg.MANIFEST_PARQUET.exists() and not man.is_empty():
        old = pl.read_parquet(cfg.MANIFEST_PARQUET)
        man = pl.concat([old, man], how="diagonal_relaxed").unique(keys, keep="last")
    man = man.sort(keys)
    man.write_parquet(cfg.MANIFEST_PARQUET)
    print(f"\n{len(manifest)} cells this run -> {cfg.RESULTS_ROOT}  "
          f"(manifest now {man.height} cells: {cfg.MANIFEST_PARQUET})")


if __name__ == "__main__":
    main()
