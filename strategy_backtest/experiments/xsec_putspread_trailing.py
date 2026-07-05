"""Ablation backtest: the frozen top-K put-spread book scored on TRAILING RV instead of the model.

Identical to xsec_putspread_topk in every respect EXCEPT the RV forecast used to build the score:
  model  : score = log(iv2) - log(rv_hat_cal)      (EnsembleTopK, de-biased -- the frozen book)
  trail  : score = log(iv2) - log(trailing_22d_RV) (sum of past 22 daily total_rv, no model)
Same universe, cadence, score>0 gate, tradeable-walk, structure, sizing, fills, settlement. The
ONLY thing that changes is which names the ranking selects, so any Sharpe gap is attributable to
the forecaster's cross-sectional contribution over a trivial trailing average.

Runs BOTH predictors x {cross, mid} in one process and prints a side-by-side table, so the model's
0.66/0.93 is re-verified in the same run. Needs the raw ORATS chains staged (see §3.1 of the spec).

Run:  XS_DATA_ROOT=strategy_backtest/data_wide XS_TOPK=2 XS_TRADEABLE=1 XS_MIN_SCORE=0.0 \
      .venv/bin/python -m strategy_backtest.experiments.xsec_putspread_trailing
"""
from __future__ import annotations
import polars as pl

from strategy_backtest.experiments import xsec_putspread_topk as X
from strategy_backtest.backtest import engine, pit
from strategy_backtest.backtest import config as cfg

ERAS = X.ERAS


def _build(predictor: str) -> pl.DataFrame:
    """X.build_candidates, but with `score` from the chosen RV predictor. predictor in {model,trail}."""
    targets = pl.read_parquet(X.TARGETS_PARQUET).filter(pl.col("horizon") == 22).select(
        "ticker", "date", "iv2", "target_var")
    preds = pl.read_parquet(X.PREDICTIONS_PARQUET).filter(pl.col("horizon") == 22).select(
        "ticker", "date", "rv_hat", "sigma", "fold_id")
    fc = preds.join(targets.select("ticker", "date", "target_var"), on=["ticker", "date"], how="left")
    fc = pit.trailing_debias(fc, "rv_hat", "target_var", embargo=22, min_periods=126)
    fc = fc.with_columns(
        rv_hat_cal=pl.when(pl.col("log_bias").is_not_null())
        .then(pl.col("rv_hat") * pl.col("log_bias").exp()).otherwise(pl.col("rv_hat")))

    if predictor == "trail":
        inp = pl.read_parquet(X._DATA_ROOT / "inputs.parquet").select("ticker", "date", "total_rv")
        inp = pit.trailing_rv(inp, h=22, rv_col="total_rv", out_col="rv_pred")
        fc = fc.join(inp.select("ticker", "date", "rv_pred"), on=["ticker", "date"], how="left")
    else:
        fc = fc.with_columns(rv_pred=pl.col("rv_hat_cal"))

    p = targets.join(fc.select("ticker", "date", "rv_pred", "sigma", "fold_id"),
                     on=["ticker", "date"], how="inner")
    p = p.filter(~pl.col("ticker").is_in(X.EXCLUDE))
    p = p.filter((pl.col("iv2") > 0) & (pl.col("rv_pred") > 0)).with_columns(
        score=(pl.col("iv2").log() - pl.col("rv_pred").log()),
        vrp_rel=((pl.col("iv2") - pl.col("rv_pred")) / pl.col("iv2")).clip(lower_bound=0.05))

    cal = p.select("date").unique().sort("date").with_columns(i=pl.int_range(pl.len()))
    wk = cal.filter(pl.col("i") % X.ROLL_EVERY == 0).select("date")
    pw = p.join(wk, on="date", how="inner")
    pw = pw.join(pw.group_by("date").agg(n=pl.len()), on="date").filter(pl.col("n") >= X.MIN_NAMES_XS)
    pw = pw.filter(pl.col("score") > X.MIN_SCORE) if X.MIN_SCORE > float("-inf") else pw
    pw = pw.with_columns(rk=pl.col("score").rank("ordinal", descending=True).over("date"))
    sel = X._select_tradeable(pw) if X.TRADEABLE_RANK else pw.filter(pl.col("rk") <= X.TOP_K)
    return sel.with_columns(
        group=pl.col("ticker").replace_strict(X.GROUP),
        horizon=pl.lit(22), segment=pl.lit("xsec"),
        size_units=pl.lit(1.0), vrp_score=pl.col("iv2") - pl.col("rv_pred"),
        dispersion=pl.col("sigma") / pl.col("rv_pred"), ivrank=pl.lit(None, dtype=pl.Float64),
    ).select("ticker", "date", "group", "segment", "horizon", "iv2", "vrp_score", "vrp_rel",
             "dispersion", "sigma", "fold_id", "size_units", "ivrank")


def main() -> None:
    results = {}
    for predictor in ("model", "trail"):
        cand = _build(predictor)
        print(f"[{predictor}] candidates: {cand.height} ({cand['date'].n_unique()} weekly dates)")
        for fill in ("cross", "mid"):
            cfg.FILL = fill
            led = engine.run_book(cand, arm="hold")
            results[(predictor, fill)] = X._stats(led)

    hdr = "| predictor | fill | trades | P&L | Sharpe | maxDD | win | " + \
          " | ".join(f"{lo}-{hi}" for lo, hi in ERAS) + " |"
    print("\n" + hdr)
    print("| --- | --- | --- | --- | --- | --- | --- | " + " | ".join("---" for _ in ERAS) + " |")
    for predictor in ("model", "trail"):
        for fill in ("cross", "mid"):
            s = results[(predictor, fill)]
            eras = " | ".join(f"{s[str(lo)]:.2f}" for lo, _ in ERAS)
            print(f"| {predictor} | {fill} | {s['n']} | ${s['pnl']:,.0f} | **{s['sharpe']:.2f}** | "
                  f"${s['maxdd']:,.0f} | {s['win']*100:.0f}% | {eras} |")


if __name__ == "__main__":
    main()
