"""Compute-once: assemble the inputs + targets panels from staged raw data.

  inputs.parquet  — comprehensive point-in-time base store (the only file model.py reads):
                    realized measures + range-based vols + per-ticker IV + systematic regime.
  targets.parquet — forward-h realized targets + IV^2 + regime tags (truth; long by horizon).

Usage:
    python -m rv_eval.setup.prepare_panel                 # all scored tickers
    python -m rv_eval.setup.prepare_panel --tickers SPY QQQ
"""

from __future__ import annotations

import argparse
import time

import polars as pl

from rv_eval import config as C
from rv_eval.setup.iv_features import iv_features, systematic_features
from rv_eval.setup.measurement import daily_measures
from rv_eval.setup.range_vol import range_measures
from rv_eval.setup.targets import build_targets

# Order of columns in inputs.parquet (comprehensive base store).
INPUT_COLS = [
    "ticker", "date", "group",
    # realized (5-min)
    "rv_intraday", "rth_rv", "rv_overnight", "total_rv",
    "bv", "jump", "rs_plus", "rs_minus", "rq",
    "overnight_ret", "ret_cc",
    # range-based + activity
    "parkinson", "gk", "rs", "volume", "transactions",
    # implied vol (per ticker)
    "iv_30d", "iv_60d", "iv_90d", "iv_slope", "skew_25d", "ext_vol",
    # systematic regime
    "vix", "vix3m", "vix_slope", "vvix",
    # quality
    "bar_count", "session", "well_behaved",
]


def build_inputs(tickers: list[str]) -> pl.DataFrame:
    sysf = systematic_features()
    frames = []
    for tk in tickers:
        m = daily_measures(tk)
        if m.is_empty():
            print(f"  {tk}: no measures, skipping")
            continue
        r = range_measures(tk).drop("ticker")
        iv = iv_features(tk).drop("ticker")
        df = (
            m.join(r, on="date", how="left")
            .join(iv, on="date", how="left")
            .join(sysf, on="date", how="left")
            .with_columns(group=pl.lit(C.GROUP[tk]))
            .select(INPUT_COLS)
        )
        frames.append(df)
        print(f"  {tk}: {df.height} days  IV-coverage {df['iv_30d'].is_not_null().mean():.2f}")
    return pl.concat(frames).sort("ticker", "date")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tickers", nargs="*", default=None, help="subset; default all scored.")
    args = ap.parse_args()
    tickers = list(args.tickers) if args.tickers else list(C.SCORED_TICKERS)

    t0 = time.time()
    print(f"Building inputs for {len(tickers)} tickers ...")
    inputs = build_inputs(tickers)
    C.INPUTS_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    inputs.write_parquet(C.INPUTS_PARQUET)
    print(f"  -> {C.INPUTS_PARQUET}  ({inputs.height:,} rows)")

    print("Building targets ...")
    targets = build_targets(
        inputs.select("ticker", "date", "group", "total_rv", "rv_overnight",
                      "rv_intraday", "iv_30d", "iv_60d")
    )
    targets.write_parquet(C.TARGETS_PARQUET)
    print(f"  -> {C.TARGETS_PARQUET}  ({targets.height:,} rows, horizons {sorted(targets['horizon'].unique().to_list())})")
    print(f"Done in {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
