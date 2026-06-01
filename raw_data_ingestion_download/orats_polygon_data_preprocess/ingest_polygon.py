#!/usr/bin/env python3
"""
Polygon minute-aggregate CSV.gz -> Parquet ingest + compact pipeline.

Sibling of ingest_orats.py; same "separate per ticker" idea applied to Polygon
US-stocks minute aggregate bars. Key differences vs ORATS: the source is gzipped
CSV (Polars reads it directly, so no copy/unzip sandbox), and the final layout is
ONE file per ticker spanning all years (no year= sub-partition).

Input  : /Volumes/Ex-Disk/polygon/us_stocks_sip/minute_aggs_v1/<YEAR>/<MM>/<YYYY-MM-DD>.csv.gz
Staging: /Volumes/Ex-Disk/polygon_parquet_staging/year=YYYY/YYYYMMDD.parquet
Output : /Volumes/Ex-Disk/polygon_parquet/ticker=X/data.parquet  (Hive, all years)
State  : /Volumes/Ex-Disk/polygon_parquet/_state/ingest_manifest.csv

Each daily file holds ALL tickers (~1.5M rows / ~10k tickers in 2024). Schema is
stable 2003->2026:  ticker, volume, open, close, high, low, window_start, transactions
where window_start is int64 nanoseconds since the Unix epoch (UTC).

Phases
------
ingest  : For each batch of N daily files: read .csv.gz -> staging parquet (per day,
          partitioned by year). Resumable via manifest.
compact : Scan ALL staging across ALL years; for each ticker batch, fan out into
          ticker=X/data.parquet. Resumable per ticker (skips tickers already written).
          Staging is kept unless --prune-staging is passed.

DuckDB read pattern
-------------------
    SELECT *
    FROM read_parquet(
        '/Volumes/Ex-Disk/polygon_parquet/ticker=*/data.parquet',
        hive_partitioning = true
    )
    WHERE ticker = 'SPY'
      AND window_start BETWEEN '2024-01-02' AND '2024-01-03';

Usage
-----
    python ingest_polygon.py ingest                  # all years, resumable
    python ingest_polygon.py ingest --years 2024     # subset
    python ingest_polygon.py ingest --limit 3        # smoke test
    python ingest_polygon.py compact                 # all years -> one file/ticker
    python ingest_polygon.py compact --ticker-batch 500 --prune-staging
    python ingest_polygon.py status                  # manifest summary
    python ingest_polygon.py inspect-schema          # column drift across years
"""

from __future__ import annotations

import argparse
import collections
import csv
import gzip
import hashlib
import os
import sys
import shutil
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

try:
    import polars as pl  # noqa: F401  used by ingest/compact; inspect-schema works without it
except ImportError:
    pl = None  # type: ignore[assignment]


def _require_polars() -> None:
    if pl is None:
        sys.exit("polars not installed. Run: pip install 'polars>=1.0' pyarrow")


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
    log_path = LOG_DIR / f"{ts}_polygon_{cmd_name}.log"
    f = open(log_path, "a", buffering=1, encoding="utf-8")
    sys.stdout = _Tee(sys.__stdout__, f)
    sys.stderr = _Tee(sys.__stderr__, f)
    print(f"[log] writing to {log_path}")
    print(f"[log] argv: {' '.join(sys.argv)}")
    return log_path


# Polygon flat-file layout mirrors as <base>/<dataset>/... where dataset is e.g.
# "us_stocks_sip/minute_aggs_v1" or "us_stocks_sip/day_aggs_v1". The output and
# staging trees mirror the same <dataset> path so multiple datasets coexist
# without ticker= collisions and each keeps its own _state/ manifest.
SOURCE_BASE = Path("/Volumes/Ex-Disk/polygon")
OUTPUT_BASE = Path("/Volumes/Ex-Disk/polygon_parquet")
STAGING_BASE = Path("/Volumes/Ex-Disk/polygon_parquet_staging")
DEFAULT_DATASET = "us_stocks_sip/minute_aggs_v1"

BATCH_SIZE = 20            # daily files per manifest checkpoint during ingest


def resolve_paths(args) -> tuple[Path, Path, Path]:
    """Resolve (source, output, staging). Explicit --source/--output/--staging win;
    otherwise derive each as <base>/<dataset>."""
    ds = getattr(args, "dataset", None) or DEFAULT_DATASET
    source = Path(args.source) if getattr(args, "source", None) else SOURCE_BASE / ds
    output = Path(args.output) if getattr(args, "output", None) else OUTPUT_BASE / ds
    staging = Path(args.staging) if getattr(args, "staging", None) else STAGING_BASE / ds
    return source, output, staging


# Raw CSV schema (column, dtype-name). dtype-name resolved lazily so this module
# loads without polars (needed for inspect-schema, status, --help).
CSV_SCHEMA_SPEC: list[tuple[str, str]] = [
    ("ticker",       "Utf8"),
    # volume is Float64, not Int64: from 2026-02-23 onward Polygon writes volume
    # with decimals and it is genuinely fractional (~29% of rows), e.g.
    # "20704.401604". Earlier eras are whole numbers but parse fine as Float64.
    # Keeping one dtype across all years is required — Polars scan_parquet cannot
    # mix Int64 and Float64 for the same column across files (not even via
    # cast_options, which won't upcast int->float).
    ("volume",       "Float64"),
    ("open",         "Float64"),
    ("close",        "Float64"),
    ("high",         "Float64"),
    ("low",          "Float64"),
    ("window_start", "Int64"),   # nanoseconds since epoch, UTC
    ("transactions", "Int64"),   # stays integer in all eras
]
CSV_RAW_COLS: list[str] = [c for c, _ in CSV_SCHEMA_SPEC]

# Canonical OHLCV column order for staging. window_start is converted to a UTC
# Datetime; ticker is carried in staging and dropped from per-ticker output.
STAGING_COLS: list[str] = [
    "ticker",
    "window_start",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "transactions",
]


def polars_schema_overrides() -> dict:
    return {col: getattr(pl, dt) for col, dt in CSV_SCHEMA_SPEC}


def quality_filter_expr():
    """Row-keep predicate. Works on both raw-after-conversion and staging frames:
    identifiers present and a positive close price. Volume may legitimately be 0."""
    return (
        pl.col("ticker").is_not_null()
        & pl.col("window_start").is_not_null()
        & pl.col("close").is_not_null()
        & (pl.col("close") > 0)
    )


@dataclass(frozen=True)
class DayInfo:
    path: Path
    name: str        # 2024-01-02.csv.gz
    trade_date: str  # YYYYMMDD
    year: int


def parse_day_name(p: Path) -> DayInfo:
    date_str = p.name.split(".")[0]          # 2024-01-02
    ymd = date_str.replace("-", "")          # 20240102
    return DayInfo(path=p, name=p.name, trade_date=ymd, year=int(ymd[:4]))


def _real_files(it):
    """Filter out macOS AppleDouble sidecars (._* files) seen on non-APFS volumes."""
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


def discover_days(source_root: Path, years: list[int]) -> list[DayInfo]:
    days: list[DayInfo] = []
    for y in years:
        d = source_root / str(y)
        if not d.exists():
            print(f"warn: year dir not found: {d}", file=sys.stderr)
            continue
        # files live one level deep under month dirs: <year>/<MM>/<YYYY-MM-DD>.csv.gz
        days.extend(
            parse_day_name(p) for p in sorted(_real_files(d.glob("*/*.csv.gz")))
        )
    return days


# ----- manifest -------------------------------------------------------------

MANIFEST_COLS = ["trade_date", "file_name", "year", "status", "rows", "updated_at", "error"]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_manifest(manifest_path: Path) -> dict[str, dict]:
    if not manifest_path.exists():
        return {}
    with manifest_path.open() as f:
        return {row["trade_date"]: row for row in csv.DictReader(f)}


def write_manifest(manifest_path: Path, rows: dict[str, dict]) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = manifest_path.with_suffix(".tmp")
    with tmp.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=MANIFEST_COLS)
        w.writeheader()
        for r in sorted(rows.values(), key=lambda x: x.get("trade_date", "")):
            w.writerow({c: r.get(c, "") for c in MANIFEST_COLS})
    tmp.replace(manifest_path)


def set_status(
    manifest: dict, di: DayInfo, *, status: str, rows: int = 0, error: str = ""
) -> None:
    manifest[di.trade_date] = {
        "trade_date": di.trade_date,
        "file_name": di.name,
        "year": str(di.year),
        "status": status,
        "rows": str(rows),
        "updated_at": now_iso(),
        "error": error,
    }


# ----- ingest ---------------------------------------------------------------

def read_csv_day(csv_path: Path) -> pl.DataFrame:
    """Read one daily .csv.gz into the canonical staging frame (Polars decompresses
    gzip transparently). Convert window_start ns -> UTC Datetime, quality-filter,
    and sort by ticker so row-group stats enable cheap ticker pruning at compact."""
    df = pl.read_csv(
        csv_path,
        schema_overrides=polars_schema_overrides(),
        null_values=["", "NA", "NaN"],
        truncate_ragged_lines=True,
        infer_schema_length=10_000,
    )

    df = df.with_columns(
        pl.from_epoch(pl.col("window_start"), time_unit="ns").dt.replace_time_zone("UTC")
    )

    before = df.height
    df = df.filter(quality_filter_expr())
    dropped = before - df.height
    if dropped:
        print(f"    dropped {dropped:,}/{before:,} row(s) failing quality filter")

    return df.select(STAGING_COLS).sort("ticker")


def ingest_batch(
    batch: list[DayInfo],
    staging: Path,
    manifest: dict,
    manifest_path: Path,
) -> None:
    for di in batch:
        try:
            df = read_csv_day(di.path)
            year_dir = staging / f"year={di.year}"
            year_dir.mkdir(parents=True, exist_ok=True)
            out = year_dir / f"{di.trade_date}.parquet"
            tmp = out.with_suffix(".parquet.tmp")
            df.write_parquet(tmp, compression="snappy", statistics=True)
            tmp.replace(out)
            set_status(manifest, di, status="ingested", rows=df.height)
            print(f"  ingested {di.name}  rows={df.height:,}")
        except Exception as e:
            set_status(manifest, di, status="failed", error=f"convert: {e}")
            print(f"  FAILED convert {di.name}: {e}", file=sys.stderr)

    # persist manifest after each batch
    write_manifest(manifest_path, manifest)


def cmd_ingest(args: argparse.Namespace) -> None:
    _require_polars()
    source, output, staging = resolve_paths(args)
    print(f"dataset paths:\n  source={source}\n  output={output}\n  staging={staging}")
    manifest_path = output / "_state" / "ingest_manifest.csv"

    for d in (output, staging, manifest_path.parent):
        d.mkdir(parents=True, exist_ok=True)

    manifest = load_manifest(manifest_path)
    years = resolve_years(source, args.years, args.start_year, args.end_year)
    all_days = discover_days(source, years)
    years_seen = sorted({d.year for d in all_days})
    print(f"discovered {len(all_days)} day file(s) across years {years_seen}")

    todo: list[DayInfo] = []
    healed = 0
    for di in all_days:
        status = manifest.get(di.trade_date, {}).get("status")
        if status == "compacted":
            continue  # final state — output exists in ticker=X/data.parquet
        if status == "ingested":
            # Self-heal: re-ingest if the staging file went missing.
            expected = staging / f"year={di.year}" / f"{di.trade_date}.parquet"
            if expected.exists():
                continue
            healed += 1
        todo.append(di)
    if healed:
        print(f"self-heal: {healed} day(s) marked 'ingested' but staging missing — will re-ingest")
    if args.limit:
        todo = todo[: args.limit]
    print(f"to process: {len(todo)}  (already done: {len(all_days) - len(todo)})")

    n_batches = (len(todo) + BATCH_SIZE - 1) // BATCH_SIZE
    for i in range(0, len(todo), BATCH_SIZE):
        batch = todo[i : i + BATCH_SIZE]
        idx = i // BATCH_SIZE + 1
        print(f"\nbatch {idx}/{n_batches}: {batch[0].name} … {batch[-1].name}")
        t0 = time.time()
        ingest_batch(batch, staging, manifest, manifest_path)
        print(f"  batch done in {time.time() - t0:.1f}s")


# ----- compact --------------------------------------------------------------

def chunked(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i : i + n]


def cmd_compact(args: argparse.Namespace) -> None:
    """Fan all staging days into one Parquet file per ticker, using Polars'
    streaming partitioned sink (pl.PartitionByKey) over alphabetical TICKER RANGES.

    Why ranges and not one global sink: the dataset is ~8B rows / ~40k tickers on a
    16 GB machine. `per_partition_sort_by` buffers each partition before writing, so
    a single global sink accumulates ~the whole dataset and gets OOM-killed (it does
    spill, but the in-memory working set still scaled past 16 GB at 8B rows). Running
    the sink over ~1000-ticker ranges keeps each pass at roughly one-year scale
    (~a few hundred M rows), which is memory-safe (~1-2 GB RSS, validated). Each
    ticker is still written exactly once (ranges are disjoint) — no intermediate
    files, no merge step.

    Output: <output>/ticker=X/data.parquet — sorted by window_start, ticker dropped
    (encoded in the Hive path). Resumable: a range whose tickers all already have a
    data.parquet is skipped.

    Spill: the sink spills to the Polars temp dir; the system temp volume is usually
    too small, so we point POLARS_TEMP_DIR at a roomy dir via --spill-dir.
    """
    _require_polars()
    _, output, staging_root = resolve_paths(args)
    print(f"dataset paths:\n  output={output}\n  staging={staging_root}")
    manifest_path = output / "_state" / "ingest_manifest.csv"
    manifest = load_manifest(manifest_path)
    chunk = args.ticker_chunk or 1000

    if not staging_root.exists():
        print(f"no staging root: {staging_root}")
        return

    # Redirect Polars spill to a roomy volume (set before any heavy Polars work).
    spill_dir = Path(args.spill_dir) if args.spill_dir else (output.parent / "polars_spill_tmp")
    spill_dir.mkdir(parents=True, exist_ok=True)
    os.environ["POLARS_TEMP_DIR"] = str(spill_dir)

    # Tidy macOS AppleDouble sidecars so they don't get scanned.
    for sidecar in staging_root.glob("year=*/._*"):
        sidecar.unlink(missing_ok=True)

    day_files = sorted(_real_files(staging_root.glob("year=*/*.parquet")))
    if not day_files:
        print("0 staging files, nothing to compact")
        return
    day_paths = [str(f) for f in day_files]
    print(f"compacting {len(day_files)} staging day file(s) -> one file per ticker")
    print(f"  spill dir: {spill_dir}")

    # Discover tickers with a STREAMING unique (memory-safe; non-streaming OOMs).
    print("  discovering tickers (streaming unique)...")
    t_disc = time.time()
    tickers = (
        pl.scan_parquet(day_paths)
        .filter(quality_filter_expr())
        .select("ticker")
        .unique()
        .collect(engine="streaming")["ticker"]
        .sort()
        .to_list()
    )
    ranges = list(chunked(tickers, chunk))
    print(f"  {len(tickers)} unique ticker(s) -> {len(ranges)} range(s) of <= {chunk} "
          f"in {time.time() - t_disc:.0f}s")

    # The output volume may be case-insensitive (macOS HFS+/exFAT), so two tickers
    # differing only by case (e.g. preferred-share "BCpC" vs common "BCPC") would
    # map to the same ticker=X dir and silently overwrite each other. Detect those
    # and give the colliding ones a hash-suffixed dir so all data is preserved.
    by_lower: dict[str, list[str]] = collections.defaultdict(list)
    for t in tickers:
        by_lower[t.lower()].append(t)
    collision = {t for grp in by_lower.values() if len(grp) > 1 for t in grp}
    if collision:
        print(f"  WARNING: {len(collision)} ticker(s) collide case-insensitively on this "
              f"filesystem; hash-suffixing their dirs to avoid overwrite:")
        for grp in sorted([g for g in by_lower.values() if len(g) > 1]):
            print(f"    {sorted(grp)}")

    def _reldir(t: str) -> str:
        if t in collision:
            h = hashlib.blake2s(t.encode(), digest_size=3).hexdigest()
            return f"ticker={t}__{h}"
        return f"ticker={t}"

    def _file_path(ctx) -> Path:
        # ctx.keys[0].str_value is the ticker value; lay it out Hive-style.
        return Path(_reldir(ctx.keys[0].str_value)) / "data.parquet"

    output.mkdir(parents=True, exist_ok=True)
    for i, rng in enumerate(ranges, 1):
        lo, hi = rng[0], rng[-1]
        # Resumable: skip a range whose every ticker file already exists.
        if all((output / _reldir(t) / "data.parquet").exists() for t in rng):
            print(f"  range {i}/{len(ranges)} [{lo}..{hi}]: all present, skip")
            continue
        t0 = time.time()
        # Range predicate (ticker in [lo, hi]) prunes row groups cheaply because
        # staging is sorted by ticker; the range is a contiguous slice of all tickers.
        (
            pl.scan_parquet(day_paths)
            .filter(quality_filter_expr() & (pl.col("ticker") >= lo) & (pl.col("ticker") <= hi))
            .sink_parquet(
                pl.PartitionByKey(
                    output,
                    by="ticker",
                    include_key=False,                 # ticker encoded in the path
                    per_partition_sort_by="window_start",
                    file_path=_file_path,
                ),
                compression="snappy",
                statistics=True,
                mkdir=True,
                engine="streaming",
            )
        )
        print(f"  range {i}/{len(ranges)} [{lo}..{hi}]: {len(rng)} tickers in {time.time() - t0:.0f}s")

    n_out = len(_real_files(output.glob("ticker=*")))
    print(f"  done: {n_out} ticker file(s)")

    # Mark every staging day compacted (persist BEFORE any pruning).
    for f in day_files:
        td = f.stem  # YYYYMMDD
        if td in manifest:
            manifest[td]["status"] = "compacted"
            manifest[td]["updated_at"] = now_iso()
    write_manifest(manifest_path, manifest)

    shutil.rmtree(spill_dir, ignore_errors=True)  # best-effort scratch cleanup

    if args.prune_staging:
        # ignore_errors: on non-APFS volumes macOS AppleDouble (._*) sidecars can
        # vanish mid-walk and raise FileNotFoundError. The data is already safely
        # written to output (verified above), so best-effort deletion is fine.
        shutil.rmtree(staging_root, ignore_errors=True)
        print(f"  pruned staging {staging_root}")
    else:
        print("  staging retained (pass --prune-staging to delete it)")


# ----- recast-staging -------------------------------------------------------

def cmd_recast_staging(args: argparse.Namespace) -> None:
    """One-off schema-drift fix: rewrite any staging file whose `volume` is not
    Float64 (i.e. ingested before the dtype fix) so all staging is uniform and
    compact's cross-file scan won't hit an Int64/Float64 mismatch. Idempotent:
    files already Float64 are skipped. Reads parquet (fast) — no CSV re-parse."""
    _require_polars()
    _, _, staging_root = resolve_paths(args)
    if not staging_root.exists():
        print(f"no staging root: {staging_root}")
        return
    files = sorted(_real_files(staging_root.glob("year=*/*.parquet")))
    print(f"scanning {len(files)} staging file(s) for volume dtype != Float64")
    fixed = 0
    for i, f in enumerate(files, 1):
        schema = pl.read_parquet_schema(f)
        if schema.get("volume") == pl.Float64:
            continue
        df = pl.read_parquet(f).with_columns(pl.col("volume").cast(pl.Float64))
        tmp = f.with_suffix(".parquet.tmp")
        df.write_parquet(tmp, compression="snappy", statistics=True)
        tmp.replace(f)
        fixed += 1
        if fixed % 200 == 0:
            print(f"  recast {fixed} file(s) so far ({i}/{len(files)})")
    print(f"recast {fixed} file(s) to Float64 volume ({len(files) - fixed} already OK)")


# ----- status ---------------------------------------------------------------

def cmd_status(args: argparse.Namespace) -> None:
    _, output, _ = resolve_paths(args)
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
            print(f"  {r['file_name']}: {r['error']}")
        if len(failed) > 20:
            print(f"  ... and {len(failed) - 20} more")


# ----- inspect-schema (stdlib only) -----------------------------------------

def read_gz_csv_header(path: Path) -> list[str]:
    """Return the column list from a gzipped CSV — streams only the first line."""
    with gzip.open(path, "rt", encoding="utf-8", errors="replace") as f:
        header_line = f.readline()
    return [c.strip() for c in header_line.rstrip("\r\n").split(",")]


def cmd_inspect_schema(args: argparse.Namespace) -> None:
    """For each year, read the header of one daily file and group years by schema."""
    source, _, _ = resolve_paths(args)
    years = resolve_years(source, args.years, args.start_year, args.end_year)
    if not years:
        sys.exit(f"no year dirs found under {source}")

    per_year: list[tuple[int, str, list[str]]] = []
    for y in years:
        d = source / str(y)
        files = sorted(_real_files(d.glob("*/*.csv.gz"))) if d.exists() else []
        if not files:
            print(f"  year {y}: no daily files", file=sys.stderr)
            continue
        z = files[0]
        try:
            cols = read_gz_csv_header(z)
            per_year.append((y, z.name, cols))
            print(f"  year {y}: {z.name}  ({len(cols)} cols)")
        except Exception as e:
            print(f"  year {y}: ERROR reading {z.name}: {e}", file=sys.stderr)

    if not per_year:
        sys.exit("no headers read")

    print("\n=== schema groups (consecutive years with identical column lists) ===")
    groups: list[dict] = []
    for y, zname, cols in per_year:
        key = tuple(cols)
        if groups and groups[-1]["key"] == key:
            groups[-1]["years"].append(y)
        else:
            groups.append({"key": key, "cols": cols, "years": [y], "first_file": zname})

    prev_cols: list[str] = []
    for i, g in enumerate(groups, 1):
        ys = g["years"]
        y_str = f"{ys[0]}" if len(ys) == 1 else f"{ys[0]}–{ys[-1]}"
        print(f"\n--- group {i}: years {y_str}  ({len(g['cols'])} cols, sample: {g['first_file']}) ---")
        if i == 1:
            print("  columns: " + ", ".join(g["cols"]))
        else:
            prev_set, cur_set = set(prev_cols), set(g["cols"])
            added = [c for c in g["cols"] if c not in prev_set]
            removed = [c for c in prev_cols if c not in cur_set]
            if added:
                print(f"  + added   ({len(added)}): {', '.join(added)}")
            if removed:
                print(f"  - removed ({len(removed)}): {', '.join(removed)}")
            if not added and not removed:
                print("  ~ same columns, possibly reordered")
        prev_cols = g["cols"]

    # vs the baseline this script parses with
    print("\n=== vs. baseline CSV_SCHEMA_SPEC in this script ===")
    baseline_set = set(CSV_RAW_COLS)
    print(f"  baseline cols ({len(CSV_RAW_COLS)}): {', '.join(CSV_RAW_COLS)}")
    for g in groups:
        ys = g["years"]
        y_str = f"{ys[0]}" if len(ys) == 1 else f"{ys[0]}–{ys[-1]}"
        csv_only = [c for c in g["cols"] if c not in baseline_set]
        baseline_only = [c for c in CSV_RAW_COLS if c not in set(g["cols"])]
        flag = "OK " if not csv_only and not baseline_only else "DRIFT"
        print(f"  [{flag}] years {y_str}: csv-only={csv_only or '[]'}  baseline-only={baseline_only or '[]'}")


# ----- main -----------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sp = p.add_subparsers(dest="cmd", required=True)

    def add_dataset_args(sub, *, source=False, output=False, staging=False):
        sub.add_argument("--dataset", default=DEFAULT_DATASET,
                         help=f"<asset_class>/<dataset> under the bases (default {DEFAULT_DATASET}); "
                              "e.g. us_stocks_sip/day_aggs_v1")
        if source:
            sub.add_argument("--source", help="explicit source dir (overrides --dataset)")
        if output:
            sub.add_argument("--output", help="explicit output dir (overrides --dataset)")
        if staging:
            sub.add_argument("--staging", help="explicit staging dir (overrides --dataset)")

    pi = sp.add_parser("ingest", help="read daily .csv.gz -> staging parquet")
    add_dataset_args(pi, source=True, output=True, staging=True)
    pi.add_argument("--years", type=int, nargs="*", help="explicit list of years (overrides --start-year/--end-year)")
    pi.add_argument("--start-year", type=int, help="ingest from this year onward (inclusive)")
    pi.add_argument("--end-year", type=int, help="ingest up to this year (inclusive)")
    pi.add_argument("--limit", type=int, help="cap day files for a smoke test")
    pi.set_defaults(func=cmd_ingest)

    pc = sp.add_parser("compact", help="fan all staging into ticker=X/data.parquet (streaming sink)")
    add_dataset_args(pc, output=True, staging=True)
    pc.add_argument("--spill-dir", help="Polars spill/temp dir (default: <output>/../polars_spill_tmp). Needs lots of free space on a roomy volume.")
    pc.add_argument("--ticker-chunk", type=int, help="tickers per streaming-sink pass (default 1000); lower if a pass OOMs")
    pc.add_argument("--prune-staging", action="store_true", help="delete staging after a full compact")
    pc.set_defaults(func=cmd_compact)

    prc = sp.add_parser(
        "recast-staging",
        help="normalize staging volume column to Float64 (one-off 2026 schema-drift fix)",
    )
    add_dataset_args(prc, staging=True)
    prc.set_defaults(func=cmd_recast_staging)

    ps = sp.add_parser("status", help="manifest summary")
    add_dataset_args(ps, output=True)
    ps.set_defaults(func=cmd_status)

    pin = sp.add_parser(
        "inspect-schema",
        help="read 1 daily header per year and report column drift (stdlib only)",
    )
    add_dataset_args(pin, source=True)
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
