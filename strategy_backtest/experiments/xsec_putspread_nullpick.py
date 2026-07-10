"""Random-pick P&L null for the frozen book (hole-dig A5).

§4.3 established the *signal* isn't luck (permutation test in score space). §6.6 then showed a
no-model SPY/QQQ book ties the frozen book at cross fills. The missing test is in REALIZED P&L
space with the full frozen machinery: how much does picking the 2 *richest* gated names beat
picking 2 *random* gated names?

Null replication = the frozen book with ONE change: within each weekly cohort (same score>0 gate,
same ≥7-name date validity), the ranked order is replaced by a uniform random permutation before
the tradeable-walk (walk the shuffled list, keep the first 2 that fill). Engine, structure,
sizing, margin cap, cross fills — identical. N_REPS replications ⇒ null distributions of monthly
Sharpe and total P&L; report the frozen book's percentile in each.

Read: frozen ≈ null median  ⇒ the gate+structure+universe carries the book; selection adds nothing
      frozen ≫ null (p<0.05) ⇒ cross-sectional selection pays in dollars, not just in rank-IC.

Run:  XS_DATA_ROOT=strategy_backtest/data_wide XS_TOPK=2 XS_TRADEABLE=1 XS_MIN_SCORE=0.0 \
      .venv/bin/python -m strategy_backtest.experiments.xsec_putspread_nullpick
"""

from __future__ import annotations

import datetime as dt
import os
from functools import lru_cache

import numpy as np
import polars as pl

from strategy_backtest.backtest import chains, engine, marks, pit, structures
from strategy_backtest.backtest import config as cfg
from strategy_backtest.backtest.contracts import EntryContext
from strategy_backtest.experiments.xsec_putspread_topk import (
    EXCLUDE, GROUP, MIN_NAMES_XS, MIN_SCORE, PREDICTIONS_PARQUET, ROLL_EVERY,
    TARGETS_PARQUET, TOP_K, _stats,
)

N_REPS = int(os.environ.get("XS_NULL_REPS", "100"))
SEED = 20260709

# 16GB machine: the default chain caches (64 ticker-year frames + 8192 day slices) are multi-GB;
# shrink both for this long-running job (cache misses cost re-reads, which is fine).
from functools import lru_cache as _lru
chains._load_ticker_year = _lru(maxsize=32)(chains._load_ticker_year.__wrapped__)
chains.day_chain = _lru(maxsize=4096)(chains.day_chain.__wrapped__)
OUT_MD = cfg.RESULTS_ROOT / "xsec_putspread_nullpick.md"
OUT_CSV = cfg.RESULTS_ROOT / "xsec_putspread_nullpick_reps.csv"

FROZEN_CROSS = {"sharpe": 0.66, "pnl": 1_915_757.0}


@lru_cache(maxsize=200_000)
def openable(tk: str, d: dt.date) -> bool:
    """Same check as xsec_putspread_topk._select_tradeable._openable, memoized across reps."""
    ch = chains.locate_expiry(tk, d)
    if ch is None:
        return False
    ctx = EntryContext(ticker=tk, group=GROUP[tk], entry_date=d, expiry=ch.expiry,
                       horizon=22, spot=ch.spot, signal={})
    legs = structures.put_credit_spread_legs(ch, ctx)
    if not legs:
        return False
    try:
        marks.open_trade(ch, legs, ctx)
        return True
    except marks.Rejected:
        return False


def gated_panel() -> pl.DataFrame:
    """The frozen book's weekly gated cohort panel (everything before the ranking step)."""
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
    p = p.filter((pl.col("iv2") > 0) & (pl.col("rv_hat_cal") > 0)).with_columns(
        score=(pl.col("iv2").log() - pl.col("rv_hat_cal").log()),
        vrp_rel=((pl.col("iv2") - pl.col("rv_hat_cal")) / pl.col("iv2")).clip(lower_bound=0.05))
    cal = p.select("date").unique().sort("date").with_columns(i=pl.int_range(pl.len()))
    wk = cal.filter(pl.col("i") % ROLL_EVERY == 0).select("date")
    pw = p.join(wk, on="date", how="inner")
    pw = pw.join(pw.group_by("date").agg(n=pl.len()), on="date").filter(pl.col("n") >= MIN_NAMES_XS)
    pw = pw.filter(pl.col("score") > MIN_SCORE) if MIN_SCORE > float("-inf") else pw
    return pw.sort("date", "ticker")


def walk_random(pw: pl.DataFrame, rng: np.random.Generator) -> pl.DataFrame:
    rows: list[dict] = []
    for (_d,), sub in pw.group_by("date", maintain_order=True):
        order = rng.permutation(sub.height)
        filled = 0
        for i in order:
            if filled >= TOP_K:
                break
            r = sub.row(int(i), named=True)
            if openable(r["ticker"], r["date"]):
                rows.append(r)
                filled += 1
    sel = pl.DataFrame(rows)
    return sel.with_columns(
        group=pl.col("ticker").replace_strict(GROUP),
        horizon=pl.lit(22), segment=pl.lit("xsec"),
        size_units=pl.lit(1.0), vrp_score=pl.col("iv2") - pl.col("rv_hat_cal"),
        dispersion=pl.col("sigma") / pl.col("rv_hat_cal"), ivrank=pl.lit(None, dtype=pl.Float64),
    ).select("ticker", "date", "group", "segment", "horizon", "iv2", "vrp_score", "vrp_rel",
             "dispersion", "sigma", "fold_id", "size_units", "ivrank")


def main() -> None:
    cfg.FILL = "cross"
    pw = gated_panel()
    print(f"gated panel: {pw.height} rows, {pw['date'].n_unique()} weekly cohorts; reps={N_REPS}")
    rng = np.random.default_rng(SEED)
    reps = []
    for k in range(N_REPS):
        cand = walk_random(pw, rng)
        led = engine.run_book(cand, arm="hold")
        s = _stats(led)
        reps.append({"rep": k, "n": s["n"], "pnl": s["pnl"], "sharpe": s["sharpe"],
                     "maxdd": s["maxdd"], "win": s["win"]})
        if (k + 1) % 10 == 0:
            arr = np.array([r["sharpe"] for r in reps])
            print(f"  rep {k+1}: null Sharpe mean {arr.mean():.2f} ± {arr.std():.2f}")
    df = pl.DataFrame(reps)
    df.write_csv(OUT_CSV)

    sh, pnl = df["sharpe"].to_numpy(), df["pnl"].to_numpy()
    pct_sh = float((sh < FROZEN_CROSS["sharpe"]).mean()) * 100
    pct_pnl = float((pnl < FROZEN_CROSS["pnl"]).mean()) * 100
    q = lambda v, p: float(np.percentile(v, p))
    L = ["# Random-pick P&L null (hole-dig A5)", "",
         f"_{N_REPS} replications; per weekly cohort, the score-rank is replaced by a random"
         " permutation before the identical tradeable-walk; score>0 gate, engine, sizing, cross"
         f" fills all frozen · generated {dt.date.today()}_", "",
         f"Frozen book (cross): Sharpe {FROZEN_CROSS['sharpe']:.2f}, P&L ${FROZEN_CROSS['pnl']:,.0f}.",
         "",
         "| metric | null mean | null p5 | null p50 | null p95 | frozen | frozen percentile |",
         "| --- | --- | --- | --- | --- | --- | --- |",
         f"| Sharpe (monthly) | {sh.mean():.2f} | {q(sh,5):.2f} | {q(sh,50):.2f} | {q(sh,95):.2f} "
         f"| **{FROZEN_CROSS['sharpe']:.2f}** | **{pct_sh:.0f}%** |",
         f"| total P&L | ${pnl.mean():,.0f} | ${q(pnl,5):,.0f} | ${q(pnl,50):,.0f} "
         f"| ${q(pnl,95):,.0f} | **${FROZEN_CROSS['pnl']:,.0f}** | **{pct_pnl:.0f}%** |", ""]
    OUT_MD.write_text("\n".join(L) + "\n")
    print(f"frozen percentile: Sharpe {pct_sh:.0f}%, P&L {pct_pnl:.0f}%  -> {OUT_MD}")


if __name__ == "__main__":
    main()
