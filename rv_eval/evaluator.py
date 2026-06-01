"""Evaluator CLI — the decoupled scoring step: truth + predictions -> all evaluations + report.

Joins one or more prediction files to the precomputed targets (truth), runs the Tier-1 bundle
(§3), the IV conditional diagnostic (§5), conditional calibration (§6), optional Tier-2 (§4), and
the §9 status, then writes report.html / report.md / metrics.json and updates the run registry.

**This is the cross-model comparison tool.** Per-model self-stats during swarm building should
use ``rv_eval.selfstats`` instead — that CLI does not write to the registry, does not compute
§9 status, and does not produce degenerate DM / MCS panels. See MODEL_PLAN.md §6.

Usage:
    python -m rv_eval.evaluator                                  # score all predictions, tier 1
    python -m rv_eval.evaluator --pred execution/data/predictions/HAR.parquet --tier 2
    python -m rv_eval.evaluator --universe clean_core --out execution/reports/run1
    python -m rv_eval.evaluator --no-registry --out /tmp/debug    # partial run, no Progression pollution
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

import polars as pl

from rv_eval import config as C
from rv_eval.metrics import calibration, iv_diagnostic, status, tier1, tier2
from rv_eval.metrics.status import BASELINE as STATUS_BASELINE
from rv_eval.report import build_report


def _load_predictions(paths: list[Path]) -> pl.DataFrame:
    frames = []
    for p in paths:
        df = pl.read_parquet(p)
        if "model" not in df.columns:
            df = df.with_columns(model=pl.lit(p.stem))
        frames.append(df)
    return pl.concat(frames, how="diagonal_relaxed")


def evaluate(truth: pl.DataFrame, preds: pl.DataFrame, tier: int,
             horizons: list[int], universe: str, out_dir: Path,
             write_registry: bool = True) -> dict:
    keep = set(C.tickers_for(universe))
    preds = preds.filter(pl.col("ticker").is_in(keep) & pl.col("horizon").is_in(horizons))
    truth = truth.filter(pl.col("ticker").is_in(keep) & pl.col("horizon").is_in(horizons))

    models_present = sorted(preds["model"].unique().to_list()) if preds.height else []
    if STATUS_BASELINE not in models_present:
        print(f"WARNING: baseline {STATUS_BASELINE!r} missing from predictions "
              f"(present: {models_present}). §9 status will be 'no_baseline' for all models. "
              f"Run the HAR benchmark before relying on the verdict.", file=sys.stderr)

    scored = preds.join(truth, on=["ticker", "date", "horizon"], how="inner")
    if scored.is_empty():
        raise SystemExit("No overlap between predictions and truth — check tickers/horizons.")
    scored = tier1.add_pointwise(scored)

    rc = tier1.rank_correlation(scored)
    tables = {
        "tier1_overall": tier1.summarize(scored, ["model"]),
        "tier1_by_h": tier1.summarize(scored, ["model", "horizon"]),
        "tier1_by_ticker": tier1.summarize(scored, ["model", "horizon", "ticker"]),
        "tier1_by_group": tier1.summarize(scored, ["model", "group"]),
        "rankcorr": (rc.group_by(["model", "horizon"]).agg(pl.col("rank_corr").mean()).sort(["model", "horizon"])
                     if not rc.is_empty() else rc),
        "cond_ivbucket": calibration.conditional_table(scored, "iv_pctile_bucket"),
        "postshock_flags": calibration.post_shock_flags(scored),
        "iv_diag": iv_diagnostic.iv_diagnostic(scored, ["model", "horizon"]),
    }
    tables["status"] = status.assign(tables["tier1_by_h"], tables["iv_diag"], tables["postshock_flags"])

    if tier >= 2:
        tables["dm"] = pl.concat([tier2.dm_matrix(scored, h) for h in horizons], how="diagonal_relaxed")
        tables["mcs"] = pl.concat([tier2.model_confidence_set(scored, h, B=500) for h in horizons],
                                  how="diagonal_relaxed")

    meta = build_report(scored, tables, out_dir, tier, write_registry=write_registry)
    return {"meta": meta, "tables": tables}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--truth", default=str(C.TARGETS_PARQUET))
    ap.add_argument("--pred", nargs="*", default=None,
                    help="prediction parquet(s); default = all in execution/data/predictions/")
    ap.add_argument("--out", default=None, help="report dir; default = execution/reports/run-<ts>")
    ap.add_argument("--tier", type=int, default=1, choices=[1, 2])
    ap.add_argument("--horizons", nargs="*", type=int, default=list(C.HORIZONS))
    ap.add_argument("--universe", default="all", choices=["clean_core", "hard_cases", "all"])
    ap.add_argument("--no-registry", action="store_true",
                    help="don't append this run to registry.parquet (use for partial/debug runs "
                         "to avoid polluting the Progression panel)")
    args = ap.parse_args()

    pred_paths = ([Path(p) for p in args.pred] if args.pred
                  else sorted(C.PREDICTIONS_ROOT.glob("*.parquet")))
    if not pred_paths:
        raise SystemExit(f"No prediction files found in {C.PREDICTIONS_ROOT}")
    truth = pl.read_parquet(args.truth)
    preds = _load_predictions(pred_paths)

    out_dir = Path(args.out) if args.out else (
        C.REPORTS_ROOT / f"run-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}")
    res = evaluate(truth, preds, args.tier, args.horizons, args.universe, out_dir,
                   write_registry=not args.no_registry)

    print(f"\nModels scored: {sorted(preds['model'].unique().to_list())}")
    print(f"Report -> {res['meta']['out']}  (run {res['meta']['run_id']})")
    print("\nVerdict (§9):")
    print(res["tables"]["status"].select("model", "status", "n_improved", "n_broke", "mean_qlike"))


if __name__ == "__main__":
    main()
