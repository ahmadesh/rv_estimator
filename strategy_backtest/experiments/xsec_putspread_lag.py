"""One-day signal→fill lag test on the frozen cross-sectional put-spread book (hole-dig A1).

Frozen-spec caveat §6.4: the score is computed from the SAME EOD chain the trade fills on. If a
name ranks top-2 partly because its quotes are temporarily blown out or stale (inflated IV mark →
inflated score → we "sell" at that same inflated mark), part of the backtest edge is quote noise a
live trader can never capture.

The attack: lag the ENTIRE score one trading day per ticker — score used on entry date t is
log(iv2_{t-1}) − log(rv_hat_cal_{t-1}) — while the gate (score>0), ranking, tradeable-walk,
structure, sizing, fills and settlement all run on the entry-day (t) chain exactly as frozen.
This is executable live (compute signal at t−1 close, trade at t close), so:

    lag-all Sharpe ≈ frozen  ⇒  §6.4 defused, the edge is real richness, not same-day coupling
    lag-all Sharpe collapses ⇒  the headline leans on quote artifacts; decompose next
                                (XS_LAG_PART=iv lags only iv2; =rv lags only rv_hat_cal)

Run:  XS_DATA_ROOT=strategy_backtest/data_wide XS_TOPK=2 XS_TRADEABLE=1 XS_MIN_SCORE=0.0 \
      XS_TAG=_lag1 .venv/bin/python -m strategy_backtest.experiments.xsec_putspread_lag
"""

from __future__ import annotations

import datetime as dt
import os

import polars as pl

from strategy_backtest.backtest import engine, pit
from strategy_backtest.backtest import config as cfg

from strategy_backtest.experiments.xsec_putspread_topk import (
    ERAS,
    EXCLUDE,
    GROUP,
    MIN_NAMES_XS,
    MIN_SCORE,
    PREDICTIONS_PARQUET,
    ROLL_EVERY,
    TARGETS_PARQUET,
    TOP_K,
    TRADEABLE_RANK,
    _select_tradeable,
    _stats,
)

TAG = os.environ.get("XS_TAG", "_lag1")
LAG_PART = os.environ.get("XS_LAG_PART", "all")     # all | iv | rv — which score input is lagged
MAX_STALE_DAYS = 7                                  # drop a lagged obs older than this (calendar)


def build_candidates() -> pl.DataFrame:
    """Frozen panel construction, with the score inputs shifted one trading day per ticker."""
    targets = pl.read_parquet(TARGETS_PARQUET).filter(pl.col("horizon") == 22).select(
        "ticker", "date", "iv2", "target_var")
    preds = pl.read_parquet(PREDICTIONS_PARQUET).filter(pl.col("horizon") == 22).select(
        "ticker", "date", "rv_hat", "sigma", "fold_id")
    fc = preds.join(targets.select("ticker", "date", "target_var"), on=["ticker", "date"], how="left")
    fc = pit.trailing_debias(fc, "rv_hat", "target_var", embargo=22, min_periods=126)
    fc = fc.with_columns(
        rv_hat_cal=pl.when(pl.col("log_bias").is_not_null())
        .then(pl.col("rv_hat") * pl.col("log_bias").exp()).otherwise(pl.col("rv_hat")))
    p = targets.join(fc.select("ticker", "date", "rv_hat_cal", "sigma", "fold_id"),
                     on=["ticker", "date"], how="inner")
    p = p.filter(~pl.col("ticker").is_in(EXCLUDE))
    p = p.filter((pl.col("iv2") > 0) & (pl.col("rv_hat_cal") > 0))

    # The lag: signal inputs observed at the PREVIOUS prediction date for this ticker.
    p = p.sort("ticker", "date").with_columns(
        iv2_sig=pl.col("iv2").shift(1).over("ticker"),
        rv_sig=pl.col("rv_hat_cal").shift(1).over("ticker"),
        sig_date=pl.col("date").shift(1).over("ticker"),
    )
    if LAG_PART == "iv":
        p = p.with_columns(rv_sig=pl.col("rv_hat_cal"))
    elif LAG_PART == "rv":
        p = p.with_columns(iv2_sig=pl.col("iv2"))
    p = p.filter(
        pl.col("iv2_sig").is_not_null() & pl.col("rv_sig").is_not_null()
        & ((pl.col("date") - pl.col("sig_date")).dt.total_days() <= MAX_STALE_DAYS)
    ).with_columns(
        score=(pl.col("iv2_sig").log() - pl.col("rv_sig").log()),
        vrp_rel=((pl.col("iv2_sig") - pl.col("rv_sig")) / pl.col("iv2_sig")).clip(lower_bound=0.05),
    )

    cal = p.select("date").unique().sort("date").with_columns(i=pl.int_range(pl.len()))
    wk = cal.filter(pl.col("i") % ROLL_EVERY == 0).select("date")
    pw = p.join(wk, on="date", how="inner")
    pw = pw.join(pw.group_by("date").agg(n=pl.len()), on="date").filter(pl.col("n") >= MIN_NAMES_XS)
    pw = pw.filter(pl.col("score") > MIN_SCORE) if MIN_SCORE > float("-inf") else pw
    pw = pw.with_columns(rk=pl.col("score").rank("ordinal", descending=True).over("date"))
    sel = _select_tradeable(pw) if TRADEABLE_RANK else pw.filter(pl.col("rk") <= TOP_K)
    return pl.DataFrame(sel).with_columns(
        group=pl.col("ticker").replace_strict(GROUP),
        horizon=pl.lit(22), segment=pl.lit("xsec"),
        size_units=pl.lit(1.0), vrp_score=pl.col("iv2_sig") - pl.col("rv_sig"),
        dispersion=pl.col("sigma") / pl.col("rv_hat_cal"), ivrank=pl.lit(None, dtype=pl.Float64),
    ).select("ticker", "date", "group", "segment", "horizon", "iv2", "vrp_score", "vrp_rel",
             "dispersion", "sigma", "fold_id", "size_units", "ivrank")


def main() -> None:
    cand = build_candidates()
    print(f"lag={LAG_PART}: candidates {cand.height} ({cand['date'].n_unique()} weekly dates, top-{TOP_K})")

    arms = {}
    for fill in ("cross", "mid"):
        cfg.FILL = fill
        led = engine.run_book(cand, arm="hold")
        arms[fill] = {"led": led, "s": _stats(led)}
        print(f"  fill={fill}: {led.height} trades, pnl ${arms[fill]['s']['pnl']:,.0f}, "
              f"Sharpe(mo) {arms[fill]['s']['sharpe']:.2f}")
    cfg.FILL = "cross"
    arms["cross"]["led"].write_csv(cfg.RESULTS_ROOT / f"xsec_putspread_trades{TAG}.csv")

    lines = [
        "# One-day signal→fill lag test (hole-dig A1)",
        "",
        f"_score from each ticker's previous trading day (lag part: {LAG_PART}), entry/fills on the"
        f" entry-day chain; everything else identical to the frozen spec · generated {dt.date.today()}_",
        "",
        "Frozen reference: cross **0.66** ($1.92M) / mid **0.93** ($2.71M), 1524 trades.",
        "",
        "| fill | trades | pnl | Sharpe(mo) | maxDD | win | " + " | ".join(f"{lo}–{hi}" for lo, hi in ERAS) + " |",
        "| --- | --- | --- | --- | --- | --- | " + " | ".join("---" for _ in ERAS) + " |",
    ]
    for fill in ("cross", "mid"):
        s = arms[fill]["s"]
        eras = " | ".join(f"{s[str(lo)]:.2f}" for lo, _ in ERAS)
        lines.append(f"| {fill} | {s['n']} | ${s['pnl']:,.0f} | **{s['sharpe']:.2f}** | "
                     f"${s['maxdd']:,.0f} | {s['win']*100:.0f}% | {eras} |")
    lines += ["", "## By ticker (cross fills)", "", "| ticker | n | pnl |", "| --- | --- | --- |"]
    by_t = arms["cross"]["led"].group_by("ticker").agg(n=pl.len(), pnl=pl.col("pnl").sum()).sort(
        "pnl", descending=True)
    for r in by_t.iter_rows(named=True):
        lines.append(f"| {r['ticker']} | {r['n']} | ${r['pnl']:,.0f} |")
    (cfg.RESULTS_ROOT / f"xsec_putspread_report{TAG}.md").write_text("\n".join(lines) + "\n")
    print(f"-> results/xsec_putspread_report{TAG}.md")


if __name__ == "__main__":
    main()
