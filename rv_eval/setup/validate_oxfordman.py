"""§2 measurement validation: compare our RTH RV(5-min) against a published reference.

The reference is the Oxford-Man / Stevens "Realized Library" (free, one-time download — the
series for the S&P 500 is keyed `.SPX`, which our SPY ETF tracks closely). This is the one step
that needs an external file; everything else in the pipeline is local.

  Download: https://realized.oxfordman.ox.ac.uk  (now hosted by the Quant Strats lab, Stevens
  Institute). Provide the CSV/parquet via --ref.

Spec (eval plan §2): compare RTH RV (not the overnight-augmented total RV) on **well-behaved**
days only; report the ≤5% tolerance pass rate and document the **signed** microstructure bias.

Usage:
    python -m rv_eval.setup.validate_oxfordman --ref oxfordman.csv
    python -m rv_eval.setup.validate_oxfordman --ref lib.csv --ref-symbol .SPX --ref-col rv5 --ticker SPY
"""

from __future__ import annotations

import argparse
import sys

import polars as pl

from rv_eval import config as C

_INSTRUCTIONS = """\
No reference file provided (or not found). The Oxford-Man/Stevens Realized Library is a free
one-time download; pass it with --ref. Expected columns: a date, a symbol (e.g. '.SPX'), and a
5-min RV column (e.g. 'rv5'). Use --ref-symbol / --ref-col / --date-col to match your file.
"""


def _load_ref(path: str, symbol: str, col: str, date_col: str) -> pl.DataFrame:
    ref = pl.read_csv(path) if path.endswith(".csv") else pl.read_parquet(path)
    cols = {c.lower(): c for c in ref.columns}
    # Locate symbol column if present.
    sym_col = next((cols[c] for c in ("symbol", "ticker", "name") if c in cols), None)
    if sym_col is not None:
        ref = ref.filter(pl.col(sym_col).cast(pl.Utf8) == symbol)
    if col not in ref.columns:
        sys.exit(f"--ref-col '{col}' not in reference columns: {ref.columns}")
    dcol = date_col if date_col in ref.columns else next(iter(ref.columns))
    return (
        ref.with_columns(date=pl.col(dcol).cast(pl.Utf8).str.slice(0, 10).str.to_date(strict=False))
        .select("date", pl.col(col).cast(pl.Float64).alias("ref_rv"))
        .drop_nulls()
    )


def validate(ticker: str, ref: pl.DataFrame) -> dict:
    ours = (
        pl.read_parquet(C.INPUTS_PARQUET)
        .filter((pl.col("ticker") == ticker) & pl.col("well_behaved"))
        .select("date", "rth_rv")
    )
    j = ours.join(ref, on="date", how="inner").filter(
        (pl.col("rth_rv") > 0) & (pl.col("ref_rv") > 0)
    )
    if j.is_empty():
        sys.exit("No overlapping well-behaved days between our RV and the reference.")
    j = j.with_columns(ratio=pl.col("rth_rv") / pl.col("ref_rv"))
    within5 = (j["ratio"] - 1.0).abs() <= 0.05
    # signed bias in vol space (sqrt) is more interpretable than variance
    bias_var = (j["rth_rv"] - j["ref_rv"]).mean() / j["ref_rv"].mean()
    return {
        "n_days": j.height,
        "median_ratio": float(j["ratio"].median()),
        "pct_within_5pct": float(within5.mean()),
        "signed_bias_var": float(bias_var),
        "corr": float(pl.corr(j["rth_rv"], j["ref_rv"], method="spearman")),
        "span": (str(j["date"].min()), str(j["date"].max())),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ref", default=None, help="path to the Oxford-Man/Stevens realized library file")
    ap.add_argument("--ticker", default="SPY")
    ap.add_argument("--ref-symbol", default=".SPX")
    ap.add_argument("--ref-col", default="rv5")
    ap.add_argument("--date-col", default="date")
    args = ap.parse_args()

    if not args.ref:
        print(_INSTRUCTIONS)
        return
    ref = _load_ref(args.ref, args.ref_symbol, args.ref_col, args.date_col)
    res = validate(args.ticker, ref)
    print(f"Oxford-Man validation — {args.ticker} RTH RV vs {args.ref_symbol}/{args.ref_col}")
    for k, v in res.items():
        print(f"  {k}: {v}")
    ok = res["pct_within_5pct"] >= 0.80  # most well-behaved days should pass
    print(f"  VERDICT: {'PASS' if ok else 'REVIEW'} "
          f"(signed variance bias {res['signed_bias_var']:+.1%}; "
          f"a small negative bias is expected from dropping the open auction / first ticks)")


if __name__ == "__main__":
    main()
