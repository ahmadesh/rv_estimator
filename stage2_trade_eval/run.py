"""Stage-2 result driver — run the (model × structure × management × hedge) grid on ORATS marks.

Mirrors `trade_eval/run.py`: for every cell it writes a per-trade ledger and a daily one-per-group
portfolio P&L series (reusing `trade_eval.portfolio`), and records the cell in a manifest whose
count feeds the DSR multiple-testing deflation. Scoring (DSR/CVaR/DM) is the deferred next phase and
reuses the existing `trade_eval.reports.score_stage1` machinery on these parquets.

Usage:
    python -m stage2_trade_eval.run                                   # default grid (plan §E)
    python -m stage2_trade_eval.run --models EnsembleTopK,IV-only --horizons 22
    python -m stage2_trade_eval.run --structures iron_condor,short_strangle \
                                    --management hold,mechanical_terminal --hedge none
    python -m stage2_trade_eval.run --list                            # print the registries
"""

from __future__ import annotations

import argparse
import itertools
import time
from datetime import date, datetime, timezone

import polars as pl

# Held-out confirmation set boundary (plan §A.3): the validation/tuning window ends here.
# Any run with --end beyond this is refused to protect the frozen 2022-01→2026-05 test set.
_VALIDATION_END = date(2021, 12, 31)

from trade_eval import benchmark, portfolio
from trade_eval import config as T

from stage2_trade_eval import config as cfg
from stage2_trade_eval import engine
# import side effects: populate the registries
from stage2_trade_eval import structures as _structures   # noqa: F401
from stage2_trade_eval import management as _management    # noqa: F401
from stage2_trade_eval import hedge as _hedge              # noqa: F401
from stage2_trade_eval.contributing import (  # optional user drop-ins / E3 overlay
    maybe_recalibrate_sigma, maybe_register_extra,
)
from stage2_trade_eval.contracts import HEDGES, MANAGEMENT, STRUCTURES


def _load_predictions(model: str, targets: pl.DataFrame, inputs: pl.DataFrame) -> pl.DataFrame:
    if model == cfg.BENCHMARK:
        return benchmark.build_predictions(targets, inputs)
    path = cfg.PREDICTIONS_ROOT / f"{model}.parquet"
    if not path.exists():
        raise FileNotFoundError(f"no prediction file for {model!r}: {path}")
    return pl.read_parquet(path)


def _window(preds: pl.DataFrame, start, end) -> pl.DataFrame:
    """Filter prediction rows to the [start, end] trade-date window (inclusive).

    Applied identically to forecaster and IV-only benchmark frames (both carry a `date` trade-date
    column). When both bounds are None this is a no-op, so callers that pass no window (e.g. W2/W4)
    are completely unaffected.
    """
    if start is None and end is None:
        return preds
    expr = pl.lit(True)
    if start is not None:
        expr = expr & (pl.col("date") >= start)
    if end is not None:
        expr = expr & (pl.col("date") <= end)
    return preds.filter(expr)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--models", default=",".join(cfg.DEFAULT_MODELS))
    ap.add_argument("--horizons", default=str(cfg.PRIMARY_HORIZON))
    ap.add_argument("--structures", default=",".join(cfg.DEFAULT_STRUCTURES))
    ap.add_argument("--management", default=",".join(cfg.DEFAULT_MANAGEMENT))
    ap.add_argument("--hedge", default=",".join(cfg.DEFAULT_HEDGE))
    ap.add_argument("--start", default=None,
                    help="optional inclusive trade-date lower bound (YYYY-MM-DD) on predictions")
    ap.add_argument("--end", default=None,
                    help="optional inclusive trade-date upper bound (YYYY-MM-DD) on predictions; "
                         "refused if beyond the 2021-12-31 validation window")
    ap.add_argument("--list", action="store_true", help="print registered plug-ins and exit")
    args = ap.parse_args()

    # Date-window parse + OOS guard (plan §A.3). Absent --end -> no filtering, no assertion, so the
    # default (W2/W4) codepath is byte-for-byte unchanged.
    start = date.fromisoformat(args.start) if args.start else None
    end = date.fromisoformat(args.end) if args.end else None
    if end is not None and end > _VALIDATION_END:
        raise SystemExit(
            f"refusing to run: --end {end} is beyond the validation window {_VALIDATION_END} "
            f"(the 2022-01→2026-05 set is held out; never run/score it during tuning)"
        )

    maybe_register_extra()
    if args.list:
        print("structures :", ", ".join(sorted(STRUCTURES)))
        print("management :", ", ".join(sorted(MANAGEMENT)))
        print("hedge      :", ", ".join(sorted(HEDGES)))
        return

    models = [m.strip() for m in args.models.split(",") if m.strip()]
    horizons = [int(h) for h in args.horizons.split(",")]
    structs = [s.strip() for s in args.structures.split(",")]
    mgmts = [m.strip() for m in args.management.split(",")]
    hedges = [h.strip() for h in args.hedge.split(",")]

    targets = pl.read_parquet(cfg.TARGETS_PARQUET)
    inputs = pl.read_parquet(cfg.INPUTS_PARQUET)
    cfg.LEDGER_ROOT.mkdir(parents=True, exist_ok=True)
    cfg.PORTFOLIO_ROOT.mkdir(parents=True, exist_ok=True)

    manifest: list[dict] = []
    run_ts = datetime.now(timezone.utc).isoformat(timespec="seconds")

    for model in models:
        preds = _window(_load_predictions(model, targets, inputs), start, end)
        for h in horizons:
            preds_h = preds.filter(pl.col("horizon") == h)
            if preds_h.is_empty():
                continue
            # E3 σ-recalibration overlay (no-op unless STAGE2_E3_SIGMA_RECAL is set); benchmark has
            # degenerate sigma=0 so the overlay leaves it untouched.
            if model != cfg.BENCHMARK:
                preds_h = maybe_recalibrate_sigma(preds_h, targets, h)
            for struct, mgmt, hg in itertools.product(structs, mgmts, hedges):
                t0 = time.time()
                ledger = engine.run_cell(preds_h, targets, inputs, model, struct, mgmt, hg)
                daily = portfolio.to_daily_portfolio(ledger)
                ablation = f"{struct}__{mgmt}__{hg}"
                stem = f"{model}__h{h}__{ablation}"
                ledger.write_parquet(cfg.LEDGER_ROOT / f"{stem}.parquet")
                daily.write_parquet(cfg.PORTFOLIO_ROOT / f"{stem}.parquet")
                manifest.append({
                    "model": model, "horizon": h, "ablation": ablation,
                    "structure": struct, "management": mgmt, "hedge": hg,
                    "is_benchmark": model == cfg.BENCHMARK,
                    "n_trades": ledger.height, "n_days": daily.height,
                    "pnl_sum": float(ledger["pnl"].sum()) if ledger.height else 0.0,
                    "run_ts": run_ts,
                })
                print(f"{model:14s} h={h:<2d} {ablation:38s}: "
                      f"{ledger.height:5,} trades  {daily.height:4,} days  ({time.time()-t0:.1f}s)")

    if not manifest:
        print("no cells produced — check models/horizons/universe coverage")
        return
    man = pl.DataFrame(manifest)
    keys = ["model", "horizon", "ablation"]
    if cfg.MANIFEST_PARQUET.exists():
        old = pl.read_parquet(cfg.MANIFEST_PARQUET)
        man = pl.concat([old, man], how="diagonal_relaxed").unique(keys, keep="last")
    man.sort(keys).write_parquet(cfg.MANIFEST_PARQUET)
    print(f"\n{len(manifest)} cells this run -> {cfg.RESULTS_ROOT}  "
          f"(manifest now {man.height} cells)")


if __name__ == "__main__":
    main()
