"""Stage the evaluation-universe raw data off the external drive into ``execution/data/raw/``.

Copy-only (never moves the source; mirrors the ingest scripts' convention). Idempotent:
a destination that already matches the source size is skipped unless ``--force``.

  - minute + daily OHLCV bars        for the 15 scored tickers
  - ORATS option chains (all years)  for all 17 tickers (incl. SPX, VIX feature sources)
  - corp actions (splits/dividends/ticker_events) filtered to the 17 tickers
  - market_holidays calendar

Usage:
    python -m rv_eval.setup.data_stage                 # stage everything
    python -m rv_eval.setup.data_stage --tickers SPY   # subset
    python -m rv_eval.setup.data_stage --force          # re-copy even if present
"""

from __future__ import annotations

import argparse
import csv
import shutil
import time
from pathlib import Path

import polars as pl
import pyarrow.parquet as pq

from rv_eval import config as C


def _num_rows(path: Path) -> int:
    """Row count from the parquet footer (no full read)."""
    try:
        return pq.ParquetFile(path).metadata.num_rows
    except Exception:
        return -1


def _copy(src: Path, dst: Path, force: bool) -> dict | None:
    """Copy one parquet file; return a manifest row, or None if the source is missing."""
    if not src.exists():
        return {"dataset": dst.parent.name, "src": str(src), "dst": str(dst),
                "bytes": 0, "rows": 0, "status": "MISSING"}
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() and not force and dst.stat().st_size == src.stat().st_size:
        status = "skip"
    else:
        shutil.copy2(src, dst)  # copy2 preserves mtime
        status = "copied"
    return {"dataset": dst.parent.parent.name if dst.parent.name.startswith("ticker=") else dst.parent.name,
            "src": str(src), "dst": str(dst),
            "bytes": dst.stat().st_size, "rows": _num_rows(dst), "status": status}


def stage_bars(tickers: list[str], force: bool) -> list[dict]:
    rows: list[dict] = []
    for t in tickers:
        rows.append(_copy(C.MINUTE_LAKE / f"ticker={t}" / "data.parquet",
                          C.RAW_MINUTE / f"ticker={t}" / "data.parquet", force))
        rows.append(_copy(C.DAILY_LAKE / f"ticker={t}" / "data.parquet",
                          C.RAW_DAILY / f"ticker={t}" / "data.parquet", force))
    return rows


def stage_orats(tickers: list[str], force: bool) -> list[dict]:
    rows: list[dict] = []
    for t in tickers:
        src_dir = C.ORATS_LAKE / f"ticker={t}"
        # year=*/data.parquet — the ._* AppleDouble entries do not match "year=*".
        year_files = sorted(src_dir.glob("year=*/data.parquet"))
        if not year_files:
            rows.append({"dataset": "orats", "src": str(src_dir), "dst": "",
                         "bytes": 0, "rows": 0, "status": "MISSING"})
            continue
        for src in year_files:
            dst = C.RAW_ORATS / f"ticker={t}" / src.parent.name / "data.parquet"
            rows.append(_copy(src, dst, force))
    return rows


def stage_corp_actions(tickers: list[str]) -> list[dict]:
    """Filter the three global corp-action tables down to the eval universe."""
    rows: list[dict] = []
    C.RAW_CORP.mkdir(parents=True, exist_ok=True)
    keep = set(tickers)
    for name in ("splits", "dividends", "ticker_events"):
        src = C.CORP_ACTIONS_LAKE / f"{name}.parquet"
        dst = C.RAW_CORP / f"{name}.parquet"
        if not src.exists():
            rows.append({"dataset": "corp_actions", "src": str(src), "dst": str(dst),
                         "bytes": 0, "rows": 0, "status": "MISSING"})
            continue
        df = pl.read_parquet(src).filter(pl.col("ticker").is_in(keep))
        df.write_parquet(dst)
        rows.append({"dataset": "corp_actions", "src": str(src), "dst": str(dst),
                     "bytes": dst.stat().st_size, "rows": df.height, "status": "filtered"})
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tickers", nargs="*", default=None,
                    help="subset of scored tickers (ORATS still staged for SPX/VIX). Default: all.")
    ap.add_argument("--force", action="store_true", help="re-copy even if destination matches.")
    args = ap.parse_args()

    scored = list(args.tickers) if args.tickers else list(C.SCORED_TICKERS)
    orats_tickers = scored + [t for t in C.FEATURE_SOURCES if t not in scored]

    t0 = time.time()
    manifest: list[dict] = []
    print(f"Staging bars for {len(scored)} scored tickers ...")
    manifest += stage_bars(scored, args.force)
    print(f"Staging ORATS chains for {len(orats_tickers)} tickers ...")
    manifest += stage_orats(orats_tickers, args.force)
    print("Staging corp actions + holidays ...")
    manifest += stage_corp_actions(orats_tickers)
    manifest.append(_copy(C.MARKET_HOLIDAYS, C.RAW_HOLIDAYS, args.force))

    C.STAGE_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    with C.STAGE_MANIFEST.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["dataset", "src", "dst", "bytes", "rows", "status"])
        w.writeheader()
        w.writerows(manifest)

    total_bytes = sum(r["bytes"] for r in manifest)
    total_rows = sum(max(r["rows"], 0) for r in manifest)
    missing = [r for r in manifest if r["status"] == "MISSING"]
    by_status: dict[str, int] = {}
    for r in manifest:
        by_status[r["status"]] = by_status.get(r["status"], 0) + 1
    print(f"\nManifest: {C.STAGE_MANIFEST}")
    print(f"  files={len(manifest)} {by_status}  size={total_bytes/1e9:.2f} GB  rows={total_rows:,}")
    if missing:
        print(f"  WARNING: {len(missing)} missing sources: {[Path(m['src']).name for m in missing][:8]}")
    print(f"Done in {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
