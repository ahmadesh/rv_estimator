"""One-off migration: add the new systematic regime columns to an existing inputs.parquet
without recomputing the (expensive) per-ticker realized-measure layer.

The added columns (`vix9d`, `vix9d_slope`, `credit_spread`, `credit_mom`, `usd_mom`,
`rates_mom`) are all *systematic* — one value per date, broadcast to every ticker — so a
date-keyed left-join reproduces exactly what a full `prepare_panel` rebuild would write.
`prepare_panel.INPUT_COLS` has been updated so future rebuilds include them natively;
this script just back-fills the current file. Idempotent: drops the columns first if present.

    python -m rv_eval.setup._add_systematic_cols
"""

from __future__ import annotations

import shutil

import polars as pl

from rv_eval import config as C
from rv_eval.setup.iv_features import systematic_features
from rv_eval.setup.prepare_panel import INPUT_COLS

_NEW = ["vix9d", "vix9d_slope", "credit_spread", "credit_mom", "usd_mom", "rates_mom"]


def main() -> None:
    src = C.INPUTS_PARQUET
    inputs = pl.read_parquet(src)
    n0, cols0 = inputs.height, set(inputs.columns)

    sysf = systematic_features().select("date", *_NEW)
    inputs = inputs.drop([c for c in _NEW if c in inputs.columns])  # idempotent re-run
    out = inputs.join(sysf, on="date", how="left").select(INPUT_COLS)

    assert out.height == n0, f"row count changed {n0} -> {out.height}"
    assert cols0 - set(_NEW) <= set(out.columns), "lost a pre-existing column"

    bak = src.with_suffix(".parquet.bak")
    if not bak.exists():
        shutil.copy2(src, bak)
        print(f"backed up -> {bak}")
    out.write_parquet(src)

    cov = out.filter(pl.col("ticker") == "SPY").select(
        *[pl.col(c).is_not_null().mean().round(3).alias(c) for c in _NEW]
    )
    print(f"wrote {src}  ({out.height:,} rows, {len(out.columns)} cols)")
    print("SPY non-null coverage of new cols:")
    print(cov)
    spy = out.filter(pl.col("ticker") == "SPY")
    starts = {c: spy.filter(pl.col(c).is_not_null())["date"].min() for c in ["vix9d", "credit_spread"]}
    print(f"first non-null date (SPY): {starts}")


if __name__ == "__main__":
    main()
