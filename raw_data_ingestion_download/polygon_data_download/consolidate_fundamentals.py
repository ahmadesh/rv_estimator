#!/usr/bin/env python3
"""Consolidate per-ticker fundamentals parquet files into one file per dataset.

The download writes `fundamentals/<dataset>/ticker=<SYM>/data.parquet` (good on
APFS, matches the bars lake). On the exFAT external drive (128 KB clusters) those
55k tiny files balloon ~15x and copy slowly, so for the drive we merge each
dataset into a single `fundamentals/<dataset>.parquet` with `ticker` as the first
column, sorted by ticker (+ the period/date key) so per-ticker reads still prune
row-groups. Schemas are unified diagonally (per-ticker files can differ in which
optional line items are present).
"""
from __future__ import annotations

import glob
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import polars as pl

BASE = "polygon_parquet/fundamentals"
DATASETS = ["income_statements", "balance_sheets", "cash_flow",
            "ratios", "short_interest", "short_volume"]
# date-ish key per dataset to sort within a ticker (for row-group pruning on reads)
DATE_KEYS = ["period_end", "settlement_date", "date", "filing_date"]
EXPECTED = {  # manifest row-sums, for verification (verified 2026-05-27)
    "income_statements": 546998, "balance_sheets": 307576, "cash_flow": 528997,
    "ratios": 4690, "short_interest": 1785765, "short_volume": 5444626,
}
# NOTE: short_interest reaches 1785765 only after recovering the CPN/CpN
# case-collision (case-insensitive APFS merged ticker=CPN/ and ticker=CpN/ into
# one dir, losing CPN's 5 rows). The consolidated file was patched in place by
# re-fetching both tickers; a from-per-ticker-dirs rerun would land at 1785760.


def read_one(f: str) -> pl.DataFrame:
    ticker = f.split("ticker=")[1].split("/")[0]
    return pl.read_parquet(f).with_columns(pl.lit(ticker).alias("ticker"))


def main() -> None:
    grand = 0
    for ds in DATASETS:
        t0 = time.time()
        files = sorted(glob.glob(f"{BASE}/{ds}/ticker=*/data.parquet"))
        if not files:
            print(f"{ds:18} no files — skip"); continue
        with ThreadPoolExecutor(max_workers=8) as ex:
            parts = list(ex.map(read_one, files))
        df = pl.concat(parts, how="diagonal_relaxed")
        sort_keys = ["ticker"] + [c for c in DATE_KEYS if c in df.columns]
        df = df.sort(sort_keys)
        df = df.select(["ticker"] + [c for c in df.columns if c != "ticker"])
        out = f"{BASE}/{ds}.parquet"
        tmp = out + ".tmp"
        df.write_parquet(tmp, compression="snappy", statistics=True)
        os.replace(tmp, out)
        exp = EXPECTED.get(ds)
        ok = "OK" if exp is None or df.height == exp else f"!! expected {exp}"
        print(f"{ds:18} files={len(files):6}  rows={df.height:>9,}  "
              f"{os.path.getsize(out)/1e6:6.1f} MB  {time.time()-t0:5.1f}s  [{ok}]")
        grand += df.height
    print(f"{'TOTAL':18} rows={grand:>9,}")


if __name__ == "__main__":
    sys.exit(main())
