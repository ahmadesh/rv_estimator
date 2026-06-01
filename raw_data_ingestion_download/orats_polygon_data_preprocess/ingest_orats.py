#!/usr/bin/env python3
"""
ORATS CSV -> Parquet ingest + compact pipeline.

Input  : /Volumes/Ex-Disk/orats/<YEAR>/ORATS_SMV_Strikes_YYYYMMDD.zip
Sandbox: ./orats_data_preprocess/orats_data_sandbox/  (ephemeral; copies only, never moves)
Staging: /Volumes/Ex-Disk/orats_parquet_staging/year=YYYY/YYYYMMDD.parquet
Output : /Volumes/Ex-Disk/orats_parquet/ticker=X/year=Y/data.parquet  (Hive)
State  : /Volumes/Ex-Disk/orats_parquet/_state/ingest_manifest.csv

Phases
------
ingest  : For each batch of N zips: copy -> unzip -> CSV -> staging parquet -> delete copies.
compact : For each year with staging files: read all daily staging, fan out by ticker into
          ticker=X/year=Y/data.parquet, then delete the year's staging dir.

DuckDB read pattern
-------------------
    SELECT *
    FROM read_parquet(
        '/Volumes/Ex-Disk/orats_parquet/ticker=*/year=*/data.parquet',
        hive_partitioning = true
    )
    WHERE ticker = 'SPY' AND year = 2024;

Usage
-----
    python ingest_orats.py ingest                   # all years, resumable
    python ingest_orats.py ingest --years 2024      # subset
    python ingest_orats.py ingest --limit 20        # smoke test
    python ingest_orats.py compact                  # all years currently in staging
    python ingest_orats.py compact --years 2024
    python ingest_orats.py status                   # manifest summary
"""

from __future__ import annotations

import argparse
import csv
import io
import shutil
import sys
import time
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

try:
    import polars as pl  # noqa: F401  used by ingest/compact; inspect-schema works without it
except ImportError:
    pl = None  # type: ignore[assignment]


def _require_polars() -> None:
    if pl is None:
        sys.exit(
            "polars not installed. Run: pip install 'polars>=1.0' pyarrow"
        )


# ----- logging --------------------------------------------------------------

LOG_DIR = Path(__file__).resolve().parent / "logs"


class _Tee:
    """Duplicate writes to a tty stream and a log file. Log lines get a [HH:MM:SS] prefix."""

    def __init__(self, tty, file_obj):
        self.tty = tty
        self.file = file_obj
        self._line_start = True

    def write(self, s: str) -> int:
        self.tty.write(s)
        if not s:
            return 0
        buf: list[str] = []
        for ch in s:
            if self._line_start and ch not in ("\n", "\r"):
                buf.append(f"[{datetime.now().strftime('%H:%M:%S')}] ")
                self._line_start = False
            buf.append(ch)
            if ch == "\n":
                self._line_start = True
        self.file.write("".join(buf))
        return len(s)

    def flush(self) -> None:
        self.tty.flush()
        self.file.flush()

    def isatty(self) -> bool:
        return getattr(self.tty, "isatty", lambda: False)()


def setup_log(cmd_name: str) -> Path:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%dT%H%M%S")
    log_path = LOG_DIR / f"{ts}_{cmd_name}.log"
    f = open(log_path, "a", buffering=1, encoding="utf-8")
    sys.stdout = _Tee(sys.__stdout__, f)
    sys.stderr = _Tee(sys.__stderr__, f)
    print(f"[log] writing to {log_path}")
    print(f"[log] argv: {' '.join(sys.argv)}")
    return log_path


SOURCE_ROOT = Path("/Volumes/Ex-Disk/orats")
SANDBOX_DEFAULT = Path(
    "/Users/ahmade/Documents/rv_estimator/orats_data_preprocess/orats_data_sandbox"
)
OUTPUT_DEFAULT = Path("/Volumes/Ex-Disk/orats_parquet")
STAGING_DEFAULT = Path("/Volumes/Ex-Disk/orats_parquet_staging")

BATCH_SIZE = 10
COMPACT_TICKER_BATCH = 200  # tickers per pass during compact; bounds peak RAM
DATE_FMT = "%-m/%-d/%Y"  # platform-dependent; we use strict=False, falls back to %m/%d/%Y


# Schema spec as (column, dtype-name). Dtype-name is a key into _DTYPE_MAP, resolved
# lazily inside read_csv_day so this module loads without polars installed
# (needed for inspect-schema, status, --help, etc.).
CSV_SCHEMA_SPEC: list[tuple[str, str]] = [
    ("ticker",           "Utf8"),
    ("cOpra",            "Utf8"),
    ("pOpra",            "Utf8"),
    ("stkPx",            "Float64"),
    ("expirDate",        "Utf8"),
    ("yte",              "Float64"),
    ("strike",           "Float64"),
    ("cVolu",            "Int64"),
    ("cOi",              "Int64"),
    ("pVolu",            "Int64"),
    ("pOi",              "Int64"),
    ("cBidPx",           "Float64"),
    ("cValue",           "Float64"),
    ("cAskPx",           "Float64"),
    ("pBidPx",           "Float64"),
    ("pValue",           "Float64"),
    ("pAskPx",           "Float64"),
    ("cBidIv",           "Float64"),
    ("cMidIv",           "Float64"),
    ("cAskIv",           "Float64"),
    ("smoothSmvVol",     "Float64"),
    ("pBidIv",           "Float64"),
    ("pMidIv",           "Float64"),
    ("pAskIv",           "Float64"),
    ("iRate",            "Float64"),
    ("divRate",          "Float64"),
    ("residualRateData", "Float64"),
    ("delta",            "Float64"),
    ("gamma",            "Float64"),
    ("theta",            "Float64"),
    ("vega",             "Float64"),
    ("rho",              "Float64"),
    ("phi",              "Float64"),
    ("driftlessTheta",   "Float64"),
    ("extVol",           "Float64"),
    ("extCTheo",         "Float64"),
    ("extPTheo",         "Float64"),
    ("spot_px",          "Float64"),
    ("trade_date",       "Utf8"),
]
CSV_BASELINE_COLS: list[str] = [c for c, _ in CSV_SCHEMA_SPEC]


def polars_schema_overrides() -> dict:
    return {col: getattr(pl, dt) for col, dt in CSV_SCHEMA_SPEC}


def quality_filter_expr():
    """Row-keep predicate: identifier fields must be present, and at least one of
    call-value / put-value must be non-null. Other columns (greeks, IV, etc.)
    can be null and the row is kept."""
    return (
        pl.col("ticker").is_not_null()
        & pl.col("expirDate").is_not_null()
        & pl.col("strike").is_not_null()
        & pl.col("trade_date").is_not_null()
        & (pl.col("cValue").is_not_null() | pl.col("pValue").is_not_null())
    )


@dataclass(frozen=True)
class ZipInfo:
    path: Path
    name: str
    trade_date: str  # YYYYMMDD
    year: int


def parse_zip_name(p: Path) -> ZipInfo:
    ymd = p.stem.rsplit("_", 1)[1]  # ORATS_SMV_Strikes_YYYYMMDD
    return ZipInfo(path=p, name=p.name, trade_date=ymd, year=int(ymd[:4]))


def _real_files(it):
    """Filter out macOS AppleDouble sidecars (._* files) that appear on non-APFS volumes."""
    return [p for p in it if not p.name.startswith("._")]


def all_source_years(source_root: Path) -> list[int]:
    return sorted(
        int(d.name) for d in source_root.iterdir() if d.is_dir() and d.name.isdigit()
    )


def resolve_years(
    source_root: Path,
    years: list[int] | None,
    start_year: int | None,
    end_year: int | None,
) -> list[int]:
    if years:
        return sorted(years)
    available = all_source_years(source_root)
    lo = start_year if start_year is not None else (available[0] if available else 0)
    hi = end_year if end_year is not None else (available[-1] if available else 0)
    return [y for y in available if lo <= y <= hi]


def discover_zips(source_root: Path, years: list[int]) -> list[ZipInfo]:
    zips: list[ZipInfo] = []
    for y in years:
        d = source_root / str(y)
        if not d.exists():
            print(f"warn: year dir not found: {d}", file=sys.stderr)
            continue
        zips.extend(
            parse_zip_name(p) for p in sorted(_real_files(d.glob("ORATS_SMV_Strikes_*.zip")))
        )
    return zips


# ----- manifest -------------------------------------------------------------

MANIFEST_COLS = ["zip_name", "trade_date", "year", "status", "rows", "updated_at", "error"]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_manifest(manifest_path: Path) -> dict[str, dict]:
    if not manifest_path.exists():
        return {}
    with manifest_path.open() as f:
        return {row["zip_name"]: row for row in csv.DictReader(f)}


def write_manifest(manifest_path: Path, rows: dict[str, dict]) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = manifest_path.with_suffix(".tmp")
    with tmp.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=MANIFEST_COLS)
        w.writeheader()
        # write sorted by trade_date for human-readability
        for r in sorted(rows.values(), key=lambda x: x.get("trade_date", "")):
            w.writerow({c: r.get(c, "") for c in MANIFEST_COLS})
    tmp.replace(manifest_path)


def set_status(
    manifest: dict, zi: ZipInfo, *, status: str, rows: int = 0, error: str = ""
) -> None:
    manifest[zi.name] = {
        "zip_name": zi.name,
        "trade_date": zi.trade_date,
        "year": str(zi.year),
        "status": status,
        "rows": str(rows),
        "updated_at": now_iso(),
        "error": error,
    }


# ----- ingest ---------------------------------------------------------------

def clean_dir(d: Path) -> None:
    if d.exists():
        for child in d.iterdir():
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
    else:
        d.mkdir(parents=True, exist_ok=True)


def read_csv_day(csv_path: Path) -> pl.DataFrame:
    df = pl.read_csv(
        csv_path,
        schema_overrides=polars_schema_overrides(),
        null_values=["", "NA", "NaN"],
        truncate_ragged_lines=True,
        infer_schema_length=10_000,
    )

    # Normalize to canonical 39-col schema: pre-2022 ORATS files lack cOpra/pOpra.
    # Add missing columns as nulls so all staging parquets share one schema
    # (avoids needing union_by_name=true on DuckDB cross-era reads).
    overrides = polars_schema_overrides()
    have = set(df.columns)
    missing = [c for c, _ in CSV_SCHEMA_SPEC if c not in have]
    if missing:
        df = df.with_columns(
            [pl.lit(None, dtype=overrides[c]).alias(c) for c in missing]
        )

    df = df.with_columns(
        pl.col("trade_date").str.strptime(pl.Date, "%m/%d/%Y", strict=False),
        pl.col("expirDate").str.strptime(pl.Date, "%m/%d/%Y", strict=False),
    )

    before = df.height
    df = df.filter(quality_filter_expr())
    dropped = before - df.height
    if dropped:
        print(f"    dropped {dropped:,}/{before:,} row(s) failing quality filter")

    # Project to canonical column order and sort by ticker so row-group stats
    # enable cheap ticker pruning during the compact phase.
    return df.select(CSV_BASELINE_COLS).sort("ticker")


def ingest_batch(
    batch: list[ZipInfo],
    sandbox: Path,
    staging: Path,
    manifest: dict,
    manifest_path: Path,
) -> None:
    clean_dir(sandbox)
    copied: list[Path] = []

    # 1) copy zips
    for zi in batch:
        dst = sandbox / zi.name
        shutil.copy2(zi.path, dst)
        copied.append(dst)

    # 2) extract all
    extracted_csvs: list[tuple[ZipInfo, Path]] = []
    for dst_zip, zi in zip(copied, batch):
        try:
            with zipfile.ZipFile(dst_zip) as zf:
                zf.extractall(sandbox)
            csv_name = f"ORATS_SMV_Strikes_{zi.trade_date}.csv"
            csv_path = sandbox / csv_name
            if not csv_path.exists():
                fallback = next(iter(_real_files(sandbox.glob(f"*{zi.trade_date}*.csv"))), None)
                if fallback is None:
                    raise FileNotFoundError(f"csv not found after extract: {zi.name}")
                csv_path = fallback
            extracted_csvs.append((zi, csv_path))
        except Exception as e:
            set_status(manifest, zi, status="failed", error=f"extract: {e}")
            print(f"  FAILED extract {zi.name}: {e}", file=sys.stderr)

    # 3) convert each CSV -> staging parquet
    for zi, csv_path in extracted_csvs:
        try:
            df = read_csv_day(csv_path)
            year_dir = staging / f"year={zi.year}"
            year_dir.mkdir(parents=True, exist_ok=True)
            out = year_dir / f"{zi.trade_date}.parquet"
            tmp = out.with_suffix(".parquet.tmp")
            df.write_parquet(tmp, compression="snappy", statistics=True)
            tmp.replace(out)
            set_status(manifest, zi, status="ingested", rows=df.height)
            print(f"  ingested {zi.name}  rows={df.height:,}")
        except Exception as e:
            set_status(manifest, zi, status="failed", error=f"convert: {e}")
            print(f"  FAILED convert {zi.name}: {e}", file=sys.stderr)
        finally:
            csv_path.unlink(missing_ok=True)

    # 4) wipe sandbox (removes copied zips + any stray files like __MACOSX)
    clean_dir(sandbox)

    # 5) persist manifest after each batch
    write_manifest(manifest_path, manifest)


def cmd_ingest(args: argparse.Namespace) -> None:
    _require_polars()
    source = Path(args.source)
    sandbox = Path(args.sandbox)
    output = Path(args.output)
    staging = Path(args.staging)
    manifest_path = output / "_state" / "ingest_manifest.csv"

    for d in (output, staging, sandbox, manifest_path.parent):
        d.mkdir(parents=True, exist_ok=True)

    manifest = load_manifest(manifest_path)
    years = resolve_years(source, args.years, args.start_year, args.end_year)
    all_zips = discover_zips(source, years)
    years_seen = sorted({z.year for z in all_zips})
    print(f"discovered {len(all_zips)} zip(s) across years {years_seen}")

    todo: list[ZipInfo] = []
    healed = 0
    for z in all_zips:
        status = manifest.get(z.name, {}).get("status")
        if status == "compacted":
            continue  # final state — output exists in ticker=X/year=Y; trust the manifest
        if status == "ingested":
            # Self-heal: if staging file is missing (deleted, lost disk, etc.),
            # re-ingest rather than skipping silently.
            expected = staging / f"year={z.year}" / f"{z.trade_date}.parquet"
            if expected.exists():
                continue
            healed += 1
        todo.append(z)
    if healed:
        print(f"self-heal: {healed} day(s) marked 'ingested' but staging missing — will re-ingest")
    if args.limit:
        todo = todo[: args.limit]
    print(f"to process: {len(todo)}  (already done: {len(all_zips) - len(todo)})")

    n_batches = (len(todo) + BATCH_SIZE - 1) // BATCH_SIZE
    for i in range(0, len(todo), BATCH_SIZE):
        batch = todo[i : i + BATCH_SIZE]
        idx = i // BATCH_SIZE + 1
        print(f"\nbatch {idx}/{n_batches}: {batch[0].name} … {batch[-1].name}")
        t0 = time.time()
        ingest_batch(batch, sandbox, staging, manifest, manifest_path)
        print(f"  batch done in {time.time() - t0:.1f}s")


# ----- compact --------------------------------------------------------------

def chunked(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i : i + n]


def compact_year(
    year: int,
    output: Path,
    staging_root: Path,
    manifest: dict,
    manifest_path: Path,
) -> None:
    staging = staging_root / f"year={year}"
    if not staging.exists():
        print(f"year {year}: no staging dir, skipping")
        return

    day_files = sorted(_real_files(staging.glob("*.parquet")))
    if not day_files:
        print(f"year {year}: 0 staging files, skipping")
        return

    # Clean up macOS AppleDouble sidecars (._*) so they don't accumulate. Harmless
    # to keep, but removing keeps the staging dir tidy and avoids future confusion.
    for sidecar in staging.glob("._*"):
        sidecar.unlink(missing_ok=True)

    print(f"\ncompacting year {year}: {len(day_files)} staging file(s)")
    day_paths = [str(f) for f in day_files]

    # Quality filter is applied at scan time as a defensive measure: ingest runs
    # before this filter existed may have written rows with null ticker / null
    # critical columns into staging. Report the drop count once up front.
    total_rows = pl.scan_parquet(day_paths).select(pl.len()).collect().item()
    kept_rows = (
        pl.scan_parquet(day_paths).filter(quality_filter_expr()).select(pl.len()).collect().item()
    )
    dropped = total_rows - kept_rows
    if dropped:
        pct = 100 * dropped / total_rows if total_rows else 0
        print(f"  quality filter: dropping {dropped:,}/{total_rows:,} rows ({pct:.3f}%)")

    # discover tickers (post-filter, so nulls are already excluded)
    tickers = sorted(
        pl.scan_parquet(day_paths)
        .filter(quality_filter_expr())
        .select("ticker")
        .unique()
        .collect()["ticker"]
        .to_list()
    )
    print(f"  {len(tickers)} unique ticker(s)")

    for i, tbatch in enumerate(chunked(tickers, COMPACT_TICKER_BATCH), 1):
        t0 = time.time()
        df = (
            pl.scan_parquet(day_paths)
            .filter(quality_filter_expr() & pl.col("ticker").is_in(tbatch))
            .collect()
            .sort(["ticker", "trade_date", "expirDate", "strike"])
        )
        for (tname,), part in df.group_by("ticker", maintain_order=True):
            out_dir = output / f"ticker={tname}" / f"year={year}"
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path = out_dir / "data.parquet"
            tmp = out_path.with_suffix(".parquet.tmp")
            # drop ticker column: it's encoded in the partition path (Hive convention)
            part.drop("ticker").write_parquet(
                tmp, compression="snappy", statistics=True
            )
            tmp.replace(out_path)
        print(
            f"  ticker batch {i}: {len(tbatch)} tickers, "
            f"{df.height:,} rows in {time.time() - t0:.1f}s"
        )

    # mark days compacted in manifest, persist BEFORE deleting staging
    for f in day_files:
        zname = f"ORATS_SMV_Strikes_{f.stem}.zip"
        if zname in manifest:
            manifest[zname]["status"] = "compacted"
            manifest[zname]["updated_at"] = now_iso()
    write_manifest(manifest_path, manifest)

    shutil.rmtree(staging)
    print(f"  removed {staging}")


def cmd_compact(args: argparse.Namespace) -> None:
    _require_polars()
    output = Path(args.output)
    staging_root = Path(args.staging)
    manifest_path = output / "_state" / "ingest_manifest.csv"
    manifest = load_manifest(manifest_path)

    if staging_root.exists():
        staged_years = sorted(
            int(d.name.split("=")[1])
            for d in staging_root.iterdir()
            if d.is_dir() and d.name.startswith("year=")
        )
    else:
        staged_years = []

    if args.years:
        years = sorted(set(args.years) & set(staged_years))
    else:
        lo = args.start_year if args.start_year is not None else (staged_years[0] if staged_years else 0)
        hi = args.end_year if args.end_year is not None else (staged_years[-1] if staged_years else 0)
        years = [y for y in staged_years if lo <= y <= hi]

    print(f"compacting years: {years}")
    for y in years:
        compact_year(y, output, staging_root, manifest, manifest_path)


# ----- status ---------------------------------------------------------------

def cmd_status(args: argparse.Namespace) -> None:
    output = Path(args.output)
    manifest = load_manifest(output / "_state" / "ingest_manifest.csv")
    if not manifest:
        print("manifest empty")
        return
    by_year_status: dict[tuple[str, str], int] = {}
    for row in manifest.values():
        key = (row["year"], row["status"])
        by_year_status[key] = by_year_status.get(key, 0) + 1
    print(f"{'year':<6} {'status':<12} {'count':>8}")
    for (year, status), n in sorted(by_year_status.items()):
        print(f"{year:<6} {status:<12} {n:>8}")
    failed = [r for r in manifest.values() if r["status"] == "failed"]
    if failed:
        print("\nfailed:")
        for r in failed[:20]:
            print(f"  {r['zip_name']}: {r['error']}")
        if len(failed) > 20:
            print(f"  ... and {len(failed) - 20} more")


# ----- inspect-schema (stdlib only) -----------------------------------------

def read_zip_csv_header(zip_path: Path) -> list[str]:
    """Return the column list from the (single) CSV inside `zip_path`.

    Streams from the archive — only decompresses the first chunk needed for
    the header line, so it's fast even on 60 MB+ zips.
    """
    with zipfile.ZipFile(zip_path) as zf:
        members = [m for m in zf.namelist() if m.lower().endswith(".csv")]
        if not members:
            raise RuntimeError(f"no csv member in {zip_path.name}")
        with zf.open(members[0]) as raw:
            text = io.TextIOWrapper(raw, encoding="utf-8", errors="replace")
            header_line = text.readline()
    return [c.strip() for c in header_line.rstrip("\r\n").split(",")]


def cmd_inspect_schema(args: argparse.Namespace) -> None:
    """For each year, read the header of one zip and group years by schema."""
    source = Path(args.source)
    years = resolve_years(source, args.years, args.start_year, args.end_year)
    if not years:
        sys.exit(f"no year dirs found under {source}")

    per_year: list[tuple[int, str, list[str]]] = []  # (year, zip_name, cols)
    for y in years:
        d = source / str(y)
        if not d.exists():
            print(f"  year {y}: dir not found", file=sys.stderr)
            continue
        zips = sorted(_real_files(d.glob("ORATS_SMV_Strikes_*.zip")))
        if not zips:
            print(f"  year {y}: no zips", file=sys.stderr)
            continue
        z = zips[0]
        try:
            cols = read_zip_csv_header(z)
            per_year.append((y, z.name, cols))
            print(f"  year {y}: {z.name}  ({len(cols)} cols)")
        except Exception as e:
            print(f"  year {y}: ERROR reading {z.name}: {e}", file=sys.stderr)

    if not per_year:
        sys.exit("no headers read")

    # Group consecutive years with identical column tuples
    print("\n=== schema groups (consecutive years with identical column lists) ===")
    groups: list[dict] = []
    for y, zname, cols in per_year:
        key = tuple(cols)
        if groups and groups[-1]["key"] == key:
            groups[-1]["years"].append(y)
        else:
            groups.append({"key": key, "cols": cols, "years": [y], "first_zip": zname})

    union_order: list[str] = []
    seen: set[str] = set()
    for g in groups:
        for c in g["cols"]:
            if c not in seen:
                seen.add(c)
                union_order.append(c)

    prev_cols: list[str] = []
    for i, g in enumerate(groups, 1):
        ys = g["years"]
        y_str = f"{ys[0]}" if len(ys) == 1 else f"{ys[0]}–{ys[-1]}"
        print(f"\n--- group {i}: years {y_str}  ({len(g['cols'])} cols, sample zip: {g['first_zip']}) ---")
        if i == 1:
            print("  columns: " + ", ".join(g["cols"]))
        else:
            prev_set = set(prev_cols)
            cur_set = set(g["cols"])
            added = [c for c in g["cols"] if c not in prev_set]
            removed = [c for c in prev_cols if c not in cur_set]
            reordered = (
                [c for c in g["cols"] if c in prev_set] != [c for c in prev_cols if c in cur_set]
            )
            if added:
                print(f"  + added   ({len(added)}): {', '.join(added)}")
            if removed:
                print(f"  - removed ({len(removed)}): {', '.join(removed)}")
            if reordered and not added and not removed:
                print("  ~ same columns but different order")
            if not (added or removed or reordered):
                print("  (no diff vs previous group — should not happen)")
        prev_cols = g["cols"]

    # Matrix: column x year-group presence
    print("\n=== presence matrix (✓ present, · missing) ===")
    headers = [f"g{i+1}" for i in range(len(groups))]
    print(f"{'column':<22} " + " ".join(f"{h:>4}" for h in headers))
    for col in union_order:
        marks = [
            "  ✓ " if col in set(g["cols"]) else "  · "
            for g in groups
        ]
        print(f"{col:<22} " + "".join(marks))

    # Schema-vs-code-baseline check
    print("\n=== vs. baseline CSV_SCHEMA_SPEC in this script ===")
    baseline = CSV_BASELINE_COLS
    baseline_set = set(baseline)
    print(f"  baseline cols: {len(baseline)}")
    for g in groups:
        ys = g["years"]
        y_str = f"{ys[0]}" if len(ys) == 1 else f"{ys[0]}–{ys[-1]}"
        in_csv_not_baseline = [c for c in g["cols"] if c not in baseline_set]
        in_baseline_not_csv = [c for c in baseline if c not in set(g["cols"])]
        flag = "OK " if not in_csv_not_baseline and not in_baseline_not_csv else "DRIFT"
        print(f"  [{flag}] years {y_str}: "
              f"csv-only={in_csv_not_baseline or '[]'}  baseline-only={in_baseline_not_csv or '[]'}")


# ----- main -----------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sp = p.add_subparsers(dest="cmd", required=True)

    pi = sp.add_parser("ingest", help="copy zips, extract, convert to staging parquet")
    pi.add_argument("--source", default=str(SOURCE_ROOT))
    pi.add_argument("--sandbox", default=str(SANDBOX_DEFAULT))
    pi.add_argument("--output", default=str(OUTPUT_DEFAULT))
    pi.add_argument("--staging", default=str(STAGING_DEFAULT))
    pi.add_argument("--years", type=int, nargs="*", help="explicit list of years (overrides --start-year/--end-year)")
    pi.add_argument("--start-year", type=int, help="ingest from this year onward (inclusive)")
    pi.add_argument("--end-year", type=int, help="ingest up to this year (inclusive)")
    pi.add_argument("--limit", type=int, help="cap zips for a smoke test")
    pi.set_defaults(func=cmd_ingest)

    pc = sp.add_parser("compact", help="fan staging into ticker=X/year=Y/data.parquet")
    pc.add_argument("--output", default=str(OUTPUT_DEFAULT))
    pc.add_argument("--staging", default=str(STAGING_DEFAULT))
    pc.add_argument("--years", type=int, nargs="*", help="explicit list of years (overrides --start-year/--end-year)")
    pc.add_argument("--start-year", type=int, help="compact from this year onward")
    pc.add_argument("--end-year", type=int, help="compact up to this year")
    pc.set_defaults(func=cmd_compact)

    ps = sp.add_parser("status", help="manifest summary")
    ps.add_argument("--output", default=str(OUTPUT_DEFAULT))
    ps.set_defaults(func=cmd_status)

    pin = sp.add_parser(
        "inspect-schema",
        help="read 1 zip header per year and report column drift across years (stdlib only)",
    )
    pin.add_argument("--source", default=str(SOURCE_ROOT))
    pin.add_argument("--years", type=int, nargs="*")
    pin.add_argument("--start-year", type=int)
    pin.add_argument("--end-year", type=int)
    pin.set_defaults(func=cmd_inspect_schema)

    return p


def main() -> None:
    args = build_parser().parse_args()
    setup_log(args.cmd)
    t0 = time.time()
    try:
        args.func(args)
        print(f"[log] {args.cmd} finished OK in {time.time() - t0:.1f}s")
    except SystemExit:
        raise
    except BaseException as e:
        print(f"[log] {args.cmd} FAILED after {time.time() - t0:.1f}s: {type(e).__name__}: {e}",
              file=sys.stderr)
        raise


if __name__ == "__main__":
    main()
