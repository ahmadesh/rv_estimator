"""Self-stats CLI — produce a single-model model card without cross-model comparison.

This is the tool swarm workers run after their walkforward completes (per MODEL_PLAN.md §2
step 8). It joins the worker's own predictions parquet to the precomputed targets, computes
the per-model panels that ARE meaningful in isolation, and writes a markdown model card.

Crucially this CLI does **not**:
  * touch ``registry.parquet`` (no Progression pollution)
  * compute §9 status (requires the HAR baseline in the same eval set)
  * compute Tier-2 DM matrix / Model Confidence Set (degenerate with one model)
  * produce a leaderboard / ranks

Those belong to the full cross-model evaluator (``rv_eval.evaluator``) run once at the end
of the swarm.

Usage:
    python -m rv_eval.selfstats --pred execution/data/predictions/HAR-RS.parquet \\
        --out candidate_models/cards/HAR-RS.md
    python -m rv_eval.selfstats --pred ... --universe clean_core --json /tmp/HAR-RS.json
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import polars as pl

from rv_eval import config as C
from rv_eval.metrics import calibration, iv_diagnostic, tier1
from rv_eval.report import md_table


def compute_self_stats(pred_path: Path, truth_path: Path, universe: str,
                       horizons: list[int]) -> tuple[str, dict[str, pl.DataFrame]]:
    """Return (model_name, dict of per-panel tables) for a single prediction file."""
    preds = pl.read_parquet(pred_path)
    if "model" not in preds.columns:
        preds = preds.with_columns(model=pl.lit(pred_path.stem))
    model_names = preds["model"].unique().to_list()
    if len(model_names) != 1:
        raise SystemExit(f"selfstats expects exactly one model in {pred_path}, "
                         f"found {model_names}. Use rv_eval.evaluator for multi-model frames.")
    model_name = model_names[0]

    truth = pl.read_parquet(truth_path)
    keep = set(C.tickers_for(universe))
    preds = preds.filter(pl.col("ticker").is_in(keep) & pl.col("horizon").is_in(horizons))
    truth = truth.filter(pl.col("ticker").is_in(keep) & pl.col("horizon").is_in(horizons))

    scored = preds.join(truth, on=["ticker", "date", "horizon"], how="inner")
    if scored.is_empty():
        raise SystemExit(f"No overlap between {pred_path.name} and truth for universe={universe}.")
    scored = tier1.add_pointwise(scored)

    stats = {
        "tier1_by_h": tier1.summarize(scored, ["model", "horizon"]),
        "tier1_by_ticker": tier1.summarize(scored, ["model", "horizon", "ticker"]),
        "tier1_by_group": tier1.summarize(scored, ["model", "group"]),
        "iv_diag": iv_diagnostic.iv_diagnostic(scored, ["model", "horizon"]),
        "cond_ivbucket": calibration.conditional_table(scored, "iv_pctile_bucket"),
        "postshock": calibration.post_shock_flags(scored),
    }
    return model_name, stats


def write_card(model_name: str, stats: dict[str, pl.DataFrame],
               out_path: Path, universe: str, pred_path: Path) -> None:
    h = C.PRIMARY_HORIZON
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    cond_iv_h = stats["cond_ivbucket"].filter(pl.col("horizon") == h)
    postshock_h = stats["postshock"].filter(pl.col("horizon") == h)
    by_ticker_h = stats["tier1_by_ticker"].filter(pl.col("horizon") == h)

    parts = [
        f"# {model_name} — Self Stats",
        f"_universe=`{universe}` · primary horizon h={h} · predictions=`{pred_path}` · generated {ts}_\n",
        "_Self-only metrics — no leaderboard rank, no DM test, no MCS, no §9 status._",
        "_Cross-model comparison is produced by the final `rv_eval.evaluator` pass._\n",
        "## Tier-1 pooled by horizon (§3)",
        md_table(stats["tier1_by_h"]), "",
        "## §5 IV-incremental skill (per horizon)",
        md_table(stats["iv_diag"]), "",
        f"## §6 Conditional bias by IV-percentile bucket (h={h})",
        md_table(cond_iv_h) if not cond_iv_h.is_empty() else "_no data_", "",
        f"## §6 Post-shock calibration (h={h})",
        md_table(postshock_h) if not postshock_h.is_empty() else "_no data_", "",
        f"## Per-ticker Tier-1 at h={h}",
        md_table(by_ticker_h) if not by_ticker_h.is_empty() else "_no data_", "",
        "## Pooled by group",
        md_table(stats["tier1_by_group"]), "",
    ]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(parts))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pred", required=True, help="path to a single predictions parquet")
    ap.add_argument("--truth", default=str(C.TARGETS_PARQUET))
    ap.add_argument("--out", required=True, help="output card .md path")
    ap.add_argument("--universe", default="clean_core",
                    choices=["clean_core", "hard_cases", "all"])
    ap.add_argument("--horizons", nargs="*", type=int, default=list(C.HORIZONS))
    ap.add_argument("--json", default=None,
                    help="optional: also write raw self-stats tables as JSON")
    args = ap.parse_args()

    pred_path = Path(args.pred)
    out_path = Path(args.out)
    model_name, stats = compute_self_stats(pred_path, Path(args.truth),
                                           args.universe, args.horizons)
    write_card(model_name, stats, out_path, args.universe, pred_path)
    if args.json:
        json_path = Path(args.json)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(
            {k: v.to_dicts() for k, v in stats.items()}, indent=2, default=str))
    print(f"Self-stats card -> {out_path}")


if __name__ == "__main__":
    main()
