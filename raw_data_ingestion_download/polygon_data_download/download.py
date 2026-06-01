#!/usr/bin/env python3
"""Massive.com (Polygon) REST downloader for reference, corporate-action and
fundamental stock data — everything on the Stocks Advanced plan that is NOT
price bars (already on disk as flat files) and NOT quotes/trades/Tier-4 text.

Universe
--------
The "attempt all" union of every ticker partition in the two parquet lakes:
    /Volumes/Ex-Disk/orats_parquet/ticker=<SYM>/...   (ORATS options)
    /Volumes/Ex-Disk/polygon_parquet/ticker=<SYM>/...  (Polygon minute bars)
Symbols that aren't recognized stock tickers (indices, crypto, some ETFs) simply
come back empty and are marked `empty` in the manifest rather than pre-filtered.

Storage  (root: ./polygon_parquet/ by default — staged locally while the drive
is busy; mirrors the drive's polygon_parquet/ layout so it merges back cleanly.
Override with --output-root. Parquet + snappy.)
-------
  reference/all_tickers.parquet        reference/exchanges.parquet
  reference/overview.parquet           reference/ticker_types.parquet
  reference/market_holidays.parquet
  corporate_actions/splits.parquet     corporate_actions/dividends.parquet
  corporate_actions/ticker_events.parquet
  fundamentals/<dataset>/ticker=<SYM>/data.parquet   (6 per-ticker datasets)

Single-file datasets (global sweeps + 1-row/ticker tables) are one scannable
parquet each; the six large per-ticker fundamentals/short time-series get one
file per ticker (Hive layout, matching the existing lakes) for atomic resume.

State (CSV, in repo data/)
-----
  data/polygon_universe.csv          union of lake tickers
  data/polygon_download_manifest.csv per (ticker, dataset): status/rows/error

Usage
-----
  python -m polygon_data_download.download build-universe
  python -m polygon_data_download.download reference
  python -m polygon_data_download.download corporate-actions
  python -m polygon_data_download.download fundamentals --workers 8
  python -m polygon_data_download.download fundamentals --tickers AAPL MSFT --limit 5
  python -m polygon_data_download.download status
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

try:
    import polars as pl
except ImportError:
    pl = None  # type: ignore[assignment]

try:
    from polygon_data_download.polygon_client import (
        PolygonClient,
        PolygonHTTPError,
        load_api_key,
    )
except ModuleNotFoundError:  # allow running as a plain script too
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from polygon_data_download.polygon_client import (
        PolygonClient,
        PolygonHTTPError,
        load_api_key,
    )


# ----- paths ----------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
LOG_DIR = Path(__file__).resolve().parent / "logs"

# Lakes scanned by build-universe (read-only; on the external drive).
ORATS_LAKE = Path("/Volumes/Ex-Disk/orats_parquet")
POLY_LAKE = Path("/Volumes/Ex-Disk/polygon_parquet")

# Default output root. Staged LOCALLY for now (external drive busy) and mirrors
# the drive's polygon_parquet/ layout, so the reference/, corporate_actions/ and
# fundamentals/ subtrees can later be merged onto the drive with e.g.:
#     rsync -a polygon_parquet/ /Volumes/Ex-Disk/polygon_parquet/
# Override at runtime with --output-root (e.g. point straight at the drive).
OUTPUT_ROOT = REPO_ROOT / "polygon_parquet"

UNIVERSE_CSV = DATA_DIR / "polygon_universe.csv"
MANIFEST_CSV = DATA_DIR / "polygon_download_manifest.csv"

CHECKPOINT_EVERY = 200  # tickers between manifest writes during long runs


def _require_polars() -> None:
    if pl is None:
        sys.exit("polars not installed. Run: pip install 'polars>=1.36' pyarrow")


# ----- logging (mirrors orats_data_preprocess/ingest_*.py) ------------------

class _Tee:
    """Duplicate writes to a tty stream and a log file with a [HH:MM:SS] prefix."""

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


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ----- manifest (keyed by (ticker, dataset)) --------------------------------

MANIFEST_COLS = ["ticker", "dataset", "status", "rows", "updated_at", "error"]
ALL = "__ALL__"  # sentinel ticker for global / one-shot datasets


def load_manifest() -> dict[tuple[str, str], dict]:
    if not MANIFEST_CSV.exists():
        return {}
    with MANIFEST_CSV.open() as f:
        return {(r["ticker"], r["dataset"]): r for r in csv.DictReader(f)}


def write_manifest(rows: dict[tuple[str, str], dict]) -> None:
    MANIFEST_CSV.parent.mkdir(parents=True, exist_ok=True)
    tmp = MANIFEST_CSV.with_suffix(".tmp")
    with tmp.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=MANIFEST_COLS)
        w.writeheader()
        for r in sorted(rows.values(), key=lambda x: (x.get("dataset", ""), x.get("ticker", ""))):
            w.writerow({c: r.get(c, "") for c in MANIFEST_COLS})
    tmp.replace(MANIFEST_CSV)


def set_status(
    manifest: dict, ticker: str, dataset: str, *, status: str, rows: int = 0, error: str = ""
) -> None:
    manifest[(ticker, dataset)] = {
        "ticker": ticker,
        "dataset": dataset,
        "status": status,
        "rows": str(rows),
        "updated_at": now_iso(),
        "error": error[:300],
    }


# ----- parquet helpers ------------------------------------------------------

def _df_from_records(records: list[dict]) -> "pl.DataFrame":
    """Build a DataFrame from heterogeneous JSON dicts. infer_schema_length=None
    scans all rows so varying keys unify (missing -> null); nested dicts/lists
    become Struct/List columns, which Parquet stores fine."""
    return pl.from_dicts(records, infer_schema_length=None)


def write_single_parquet(records: list[dict], out_path: Path) -> int:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df = _df_from_records(records)
    tmp = out_path.with_suffix(".parquet.tmp")
    df.write_parquet(tmp, compression="snappy", statistics=True)
    tmp.replace(out_path)
    return df.height


def write_ticker_parquet(records: list[dict], out_path: Path) -> int:
    """Per-ticker Hive file. Drop a literal `ticker` column if present — the
    value is encoded in the partition path (matches the existing lakes)."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df = _df_from_records(records)
    if "ticker" in df.columns:
        df = df.drop("ticker")
    tmp = out_path.with_suffix(".parquet.tmp")
    df.write_parquet(tmp, compression="snappy", statistics=True)
    tmp.replace(out_path)
    return df.height


# ----- universe -------------------------------------------------------------

def scan_lake_tickers(lake: Path) -> set[str]:
    """Cheap: read `ticker=<SYM>` partition directory names; no parquet reads."""
    if not lake.exists():
        print(f"warn: lake not found: {lake}", file=sys.stderr)
        return set()
    out = set()
    for d in lake.glob("ticker=*"):
        if d.is_dir():
            out.add(d.name.split("=", 1)[1])
    return out


def cmd_build_universe(args: argparse.Namespace) -> None:
    orats = scan_lake_tickers(Path(args.orats_lake))
    poly = scan_lake_tickers(Path(args.poly_lake))
    union = sorted(orats | poly)
    print(f"orats tickers: {len(orats):,}  polygon tickers: {len(poly):,}  union: {len(union):,}")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = UNIVERSE_CSV.with_suffix(".tmp")
    with tmp.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ticker", "in_orats", "in_polygon", "source"])
        for t in union:
            io, ip = t in orats, t in poly
            src = "both" if io and ip else ("orats" if io else "polygon")
            w.writerow([t, int(io), int(ip), src])
    tmp.replace(UNIVERSE_CSV)
    print(f"wrote {UNIVERSE_CSV}  ({len(union):,} tickers)")


def normalize_ticker_for_api(ticker: str) -> str:
    """Lake partitions use `_` for share classes (ORATS writes BF_A); Massive's
    API expects a dot (BF.A). Normalize only for the request — output partitions
    and the manifest keep the original lake form so joins to the bars line up."""
    return ticker.replace("_", ".")


def load_universe(args: argparse.Namespace) -> list[str]:
    if getattr(args, "tickers", None):
        return list(args.tickers)
    if not UNIVERSE_CSV.exists():
        sys.exit(f"{UNIVERSE_CSV} not found — run `build-universe` first (or pass --tickers).")
    with UNIVERSE_CSV.open() as f:
        tickers = [r["ticker"] for r in csv.DictReader(f)]
    if getattr(args, "limit", None):
        tickers = tickers[: args.limit]
    return tickers


# ----- generic per-ticker drivers -------------------------------------------

def _pending(manifest: dict, dataset: str, tickers: list[str], out_path_fn, force: bool) -> list[str]:
    """Filter to tickers still needing work. `downloaded` is skipped only if its
    output exists (self-heal); `empty` is terminal; `failed`/new are retried."""
    todo = []
    for t in tickers:
        row = manifest.get((t, dataset))
        st = row.get("status") if row else None
        if not force and st in ("empty", "unavailable"):
            continue
        if not force and st == "downloaded":
            if out_path_fn is None or out_path_fn(t).exists():
                continue
        todo.append(t)
    return todo


def run_per_ticker_files(
    client: PolygonClient,
    manifest: dict,
    dataset: str,
    tickers: list[str],
    fetch: Callable[[PolygonClient, str], list[dict]],
    out_path_fn: Callable[[str], Path],
    workers: int,
    force: bool,
) -> None:
    """Each ticker -> its own Hive parquet. Workers fetch+write; the main thread
    owns the manifest and checkpoints periodically."""
    todo = _pending(manifest, dataset, tickers, out_path_fn, force)
    print(f"[{dataset}] {len(todo)} to fetch  (skipping {len(tickers) - len(todo)} done/empty)")

    def work(t: str) -> tuple[str, int, str]:
        try:
            records = fetch(client, t)
        except PolygonHTTPError as e:
            if e.status_code in (400, 404):
                return ("unavailable", 0, "")  # bad/dead ticker — terminal, don't retry
            return ("failed", 0, str(e))
        except Exception as e:  # noqa: BLE001 — record and move on
            return ("failed", 0, str(e))
        if not records:
            return ("empty", 0, "")
        try:
            n = write_ticker_parquet(records, out_path_fn(t))
        except Exception as e:  # noqa: BLE001
            return ("failed", 0, f"write: {e}")
        return ("downloaded", n, "")

    done = 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(work, t): t for t in todo}
        for fut in as_completed(futs):
            t = futs[fut]
            status, n, err = fut.result()
            set_status(manifest, t, dataset, status=status, rows=n, error=err)
            done += 1
            if status == "failed":
                print(f"  FAILED {dataset} {t}: {err}", file=sys.stderr)
            if done % CHECKPOINT_EVERY == 0:
                write_manifest(manifest)
                print(f"  [{dataset}] {done}/{len(todo)} processed")
    write_manifest(manifest)


def run_per_ticker_single_file(
    client: PolygonClient,
    manifest: dict,
    dataset: str,
    tickers: list[str],
    fetch: Callable[[PolygonClient, str], list[dict]],
    out_path: Path,
    workers: int,
    force: bool,
    dedup_subset: Optional[list[str]] = None,
) -> None:
    """Per-ticker fetch accumulated into ONE parquet (overview, ticker_events).

    `dedup_subset` is the set of columns identifying a unique row. For overview
    that is ["ticker"] (one row per ticker); for ticker_events a ticker can have
    several rows, so it must include the event-identifying columns — otherwise a
    ["ticker"] dedup would silently drop a ticker's 2nd+ rename events.
    The file is rewritten at every checkpoint (file FIRST, then manifest) so an
    interrupted run never marks a ticker `downloaded` without its data on disk.
    New rows merge onto the existing file (diagonally; schema drift tolerated)."""
    todo = _pending(manifest, dataset, tickers, None, force)
    print(f"[{dataset}] {len(todo)} to fetch  (skipping {len(tickers) - len(todo)} done/empty/unavailable)")

    base = pl.read_parquet(out_path) if (out_path.exists() and not force) else None
    pending_rows: list[dict] = []

    def flush() -> None:
        """Persist accumulated rows to the single file, THEN the manifest, so the
        manifest never claims more than what is durably on disk."""
        nonlocal base, pending_rows
        if pending_rows:
            df_new = _df_from_records(pending_rows)
            base = pl.concat([base, df_new], how="diagonal_relaxed") if base is not None else df_new
            if dedup_subset and set(dedup_subset).issubset(set(base.columns)):
                base = base.unique(subset=dedup_subset, keep="last")
            out_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = out_path.with_suffix(".parquet.tmp")
            base.write_parquet(tmp, compression="snappy", statistics=True)
            tmp.replace(out_path)
            pending_rows = []
        write_manifest(manifest)

    def work(t: str) -> tuple[str, list[dict], str]:
        try:
            records = fetch(client, t)
        except PolygonHTTPError as e:
            if e.status_code in (400, 404):
                return ("unavailable", [], "")  # bad/dead ticker — terminal, don't retry
            return ("failed", [], str(e))
        except Exception as e:  # noqa: BLE001
            return ("failed", [], str(e))
        return (("downloaded", records, "") if records else ("empty", [], ""))

    done = 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(work, t): t for t in todo}
        for fut in as_completed(futs):
            t = futs[fut]
            status, records, err = fut.result()
            set_status(manifest, t, dataset, status=status, rows=len(records), error=err)
            pending_rows.extend(records)
            done += 1
            if status == "failed":
                print(f"  FAILED {dataset} {t}: {err}", file=sys.stderr)
            if done % CHECKPOINT_EVERY == 0:
                flush()
                print(f"  [{dataset}] {done}/{len(todo)} processed")
    flush()
    print(f"  [{dataset}] {out_path} now has {base.height if base is not None else 0:,} rows")


# ----- reference ------------------------------------------------------------

def _write_one_shot(client, manifest, dataset, path, params, out_path, force, bare_list=False):
    if not force and manifest.get((ALL, dataset), {}).get("status") == "downloaded" and out_path.exists():
        print(f"[{dataset}] already present — skip (use --force to refetch)")
        return
    try:
        body = client.get_json(path, params)
        records = body if bare_list else (body.get("results") or [])
        n = write_single_parquet(records, out_path)
        set_status(manifest, ALL, dataset, status="downloaded", rows=n)
        print(f"[{dataset}] wrote {out_path}  ({n:,} rows)")
    except Exception as e:  # noqa: BLE001
        set_status(manifest, ALL, dataset, status="failed", error=str(e))
        print(f"  FAILED {dataset}: {e}", file=sys.stderr)
    write_manifest(manifest)


def _sweep_all_tickers(client, manifest, ref_dir, force):
    dataset = "all_tickers"
    out_path = ref_dir / "all_tickers.parquet"
    if not force and manifest.get((ALL, dataset), {}).get("status") == "downloaded" \
            and out_path.exists():
        print("[all_tickers] already present — skip (use --force to refetch)")
        return
    try:
        records: list[dict] = []
        for active in ("true", "false"):
            cnt = 0
            for it in client.paginate(
                "/v3/reference/tickers",
                {"market": "stocks", "active": active, "limit": 1000, "order": "asc", "sort": "ticker"},
            ):
                records.append(it)
                cnt += 1
            print(f"  active={active}: {cnt:,} tickers")
        n = write_single_parquet(records, out_path)
        set_status(manifest, ALL, dataset, status="downloaded", rows=n)
        print(f"[all_tickers] wrote {out_path}  ({n:,} rows)")
    except Exception as e:  # noqa: BLE001
        set_status(manifest, ALL, dataset, status="failed", error=str(e))
        print(f"  FAILED all_tickers: {e}", file=sys.stderr)
    write_manifest(manifest)


def cmd_reference(args: argparse.Namespace) -> None:
    _require_polars()
    client = make_client(args)
    manifest = load_manifest()
    ref = Path(args.output_root) / "reference"
    sel = set(args.datasets) if args.datasets else None

    def want(d):
        return sel is None or d in sel

    if want("exchanges"):
        _write_one_shot(client, manifest, "exchanges", "/v3/reference/exchanges",
                        {"asset_class": "stocks"}, ref / "exchanges.parquet", args.force)
    if want("ticker_types"):
        _write_one_shot(client, manifest, "ticker_types", "/v3/reference/tickers/types",
                        {"asset_class": "stocks"}, ref / "ticker_types.parquet", args.force)
    if want("market_holidays"):
        _write_one_shot(client, manifest, "market_holidays", "/v1/marketstatus/upcoming",
                        None, ref / "market_holidays.parquet", args.force, bare_list=True)
    if want("all_tickers"):
        _sweep_all_tickers(client, manifest, ref, args.force)
    if want("overview"):
        tickers = load_universe(args)
        run_per_ticker_single_file(
            client, manifest, "overview", tickers,
            fetch=_fetch_overview,
            out_path=ref / "overview.parquet", workers=args.workers, force=args.force,
            dedup_subset=["ticker"],
        )


def _fetch_overview(client: PolygonClient, ticker: str) -> list[dict]:
    res = client.get_json(f"/v3/reference/tickers/{normalize_ticker_for_api(ticker)}").get("results")
    return [res] if res else []


# ----- corporate actions ----------------------------------------------------

def _sweep_global(client, manifest, dataset, path, out_path, force, params=None):
    if not force and manifest.get((ALL, dataset), {}).get("status") == "downloaded" and out_path.exists():
        print(f"[{dataset}] already present — skip (use --force to refetch)")
        return
    try:
        records = list(client.paginate(path, params or {"limit": 1000}))
        n = write_single_parquet(records, out_path)
        set_status(manifest, ALL, dataset, status="downloaded", rows=n)
        print(f"[{dataset}] wrote {out_path}  ({n:,} rows)")
    except Exception as e:  # noqa: BLE001
        set_status(manifest, ALL, dataset, status="failed", error=str(e))
        print(f"  FAILED {dataset}: {e}", file=sys.stderr)
    write_manifest(manifest)


def _fetch_ticker_events(client: PolygonClient, ticker: str) -> list[dict]:
    res = client.get_json(f"/vX/reference/tickers/{normalize_ticker_for_api(ticker)}/events").get("results") or {}
    name = res.get("name")
    rows = []
    for ev in res.get("events", []) or []:
        rows.append({
            "ticker": ticker,
            "name": name,
            "event_date": ev.get("date"),
            "type": ev.get("type"),
            "ticker_change_to": (ev.get("ticker_change") or {}).get("ticker"),
        })
    return rows


def cmd_corporate_actions(args: argparse.Namespace) -> None:
    _require_polars()
    client = make_client(args)
    manifest = load_manifest()
    ca = Path(args.output_root) / "corporate_actions"
    sel = set(args.datasets) if args.datasets else None

    def want(d):
        return sel is None or d in sel

    if want("splits"):
        _sweep_global(client, manifest, "splits", "/stocks/v1/splits",
                      ca / "splits.parquet", args.force,
                      params={"limit": 1000, "order": "asc", "sort": "execution_date"})
    if want("dividends"):
        _sweep_global(client, manifest, "dividends", "/stocks/v1/dividends",
                      ca / "dividends.parquet", args.force,
                      params={"limit": 1000, "order": "asc", "sort": "ex_dividend_date"})
    if want("ticker_events"):
        tickers = load_universe(args)
        run_per_ticker_single_file(
            client, manifest, "ticker_events", tickers,
            fetch=_fetch_ticker_events, out_path=ca / "ticker_events.parquet",
            workers=args.workers, force=args.force,
            dedup_subset=["ticker", "event_date", "type", "ticker_change_to"],
        )


# ----- fundamentals ---------------------------------------------------------

# dataset -> (endpoint path, ticker query-param name)
FUND_DATASETS: dict[str, tuple[str, str]] = {
    "income_statements": ("/stocks/financials/v1/income-statements", "tickers"),
    "balance_sheets": ("/stocks/financials/v1/balance-sheets", "tickers"),
    "cash_flow": ("/stocks/financials/v1/cash-flow-statements", "tickers"),
    "ratios": ("/stocks/financials/v1/ratios", "ticker"),
    "short_interest": ("/stocks/v1/short-interest", "ticker"),
    "short_volume": ("/stocks/v1/short-volume", "ticker"),
}


def _make_fund_fetch(path: str, ticker_param: str) -> Callable[[PolygonClient, str], list[dict]]:
    def fetch(client: PolygonClient, ticker: str) -> list[dict]:
        return list(client.paginate(path, {ticker_param: normalize_ticker_for_api(ticker), "limit": 50000}))
    return fetch


def cmd_fundamentals(args: argparse.Namespace) -> None:
    _require_polars()
    client = make_client(args)
    manifest = load_manifest()
    fund = Path(args.output_root) / "fundamentals"
    sel = args.datasets or list(FUND_DATASETS)
    tickers = load_universe(args)
    print(f"universe: {len(tickers):,} tickers  datasets: {sel}  workers: {args.workers}")
    for dataset in sel:
        if dataset not in FUND_DATASETS:
            print(f"warn: unknown fundamentals dataset {dataset!r} — skipping", file=sys.stderr)
            continue
        path, tparam = FUND_DATASETS[dataset]
        run_per_ticker_files(
            client, manifest, dataset, tickers,
            fetch=_make_fund_fetch(path, tparam),
            out_path_fn=lambda t, d=dataset: fund / d / f"ticker={t}" / "data.parquet",
            workers=args.workers, force=args.force,
        )


# ----- status ---------------------------------------------------------------

def cmd_status(args: argparse.Namespace) -> None:
    manifest = load_manifest()
    if not manifest:
        print("manifest empty")
        return
    counts: dict[tuple[str, str], int] = {}
    rows_by_ds: dict[str, int] = {}
    for r in manifest.values():
        counts[(r["dataset"], r["status"])] = counts.get((r["dataset"], r["status"]), 0) + 1
        try:
            rows_by_ds[r["dataset"]] = rows_by_ds.get(r["dataset"], 0) + int(r.get("rows") or 0)
        except ValueError:
            pass
    print(f"{'dataset':<22} {'status':<12} {'count':>8}")
    for (ds, st), n in sorted(counts.items()):
        print(f"{ds:<22} {st:<12} {n:>8}")
    print("\nrows downloaded by dataset:")
    for ds, n in sorted(rows_by_ds.items()):
        print(f"  {ds:<22} {n:>12,}")
    failed = [r for r in manifest.values() if r["status"] == "failed"]
    if failed:
        print(f"\nfailed ({len(failed)}):")
        for r in failed[:20]:
            print(f"  {r['dataset']} {r['ticker']}: {r['error']}")
        if len(failed) > 20:
            print(f"  ... and {len(failed) - 20} more")


# ----- client + CLI ---------------------------------------------------------

def make_client(args: argparse.Namespace) -> PolygonClient:
    key = load_api_key(getattr(args, "api_key", None))
    return PolygonClient(
        key,
        base_url=getattr(args, "base_url", None) or "https://api.massive.com",
        throttle=getattr(args, "throttle", 0.0),
    )


def _add_common(p: argparse.ArgumentParser, *, per_ticker: bool) -> None:
    p.add_argument("--api-key", help="override POLYGON_API_KEY/.env")
    p.add_argument("--base-url", help="API base (default https://api.massive.com)")
    p.add_argument("--output-root", default=str(OUTPUT_ROOT),
                   help=f"where to write parquet (default {OUTPUT_ROOT}); point at the drive to write there directly")
    p.add_argument("--throttle", type=float, default=0.0, help="seconds to sleep before each request")
    p.add_argument("--force", action="store_true", help="refetch even if already downloaded")
    p.add_argument("--datasets", nargs="*", help="subset of this command's datasets")
    if per_ticker:
        p.add_argument("--tickers", nargs="*", help="explicit tickers (overrides universe)")
        p.add_argument("--limit", type=int, help="cap universe size for a smoke test")
        p.add_argument("--workers", type=int, default=8, help="concurrent requests (default 8)")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = p.add_subparsers(dest="cmd", required=True)

    pu = sp.add_parser("build-universe", help="union lake ticker= dirs -> data/polygon_universe.csv")
    pu.add_argument("--orats-lake", default=str(ORATS_LAKE))
    pu.add_argument("--poly-lake", default=str(POLY_LAKE))
    pu.set_defaults(func=cmd_build_universe)

    pr = sp.add_parser("reference", help="exchanges, ticker_types, market_holidays, all_tickers, overview")
    _add_common(pr, per_ticker=True)
    pr.set_defaults(func=cmd_reference)

    pc = sp.add_parser("corporate-actions", help="splits, dividends (global sweep) + ticker_events (per ticker)")
    _add_common(pc, per_ticker=True)
    pc.set_defaults(func=cmd_corporate_actions)

    pf = sp.add_parser("fundamentals", help="income/balance/cashflow/ratios/short-interest/short-volume per ticker")
    _add_common(pf, per_ticker=True)
    pf.set_defaults(func=cmd_fundamentals)

    ps = sp.add_parser("status", help="manifest summary")
    ps.set_defaults(func=cmd_status)

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
    except BaseException as e:  # noqa: BLE001
        print(f"[log] {args.cmd} FAILED after {time.time() - t0:.1f}s: {type(e).__name__}: {e}",
              file=sys.stderr)
        raise


if __name__ == "__main__":
    main()
