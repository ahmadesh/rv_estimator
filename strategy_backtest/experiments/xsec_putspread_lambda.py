"""Fill-capture curve (improvement lever I1 / spec §8.1).

The frozen book's cross→mid gap is +0.27 Sharpe and §6.6 showed the model's alpha over a trivial
SPY/QQQ pair lives entirely in that gap. This sweep makes the execution requirement explicit:
parameterize every entry fill as

    fill(λ) = mid + λ · (cross − mid),      λ=0 mid … λ=1 crossing the whole half-spread

and re-price BOTH books (frozen top-2 walk; unconditional SPY/QQQ pair) on the same λ grid.
Candidate selection is built once under the frozen (cross) conventions, so per book only the
entry pricing moves. The deliverables:

  * Sharpe-vs-λ curve per book,
  * the model book's edge over the pair per λ (IR of the monthly difference),
  * the breakeven λ* where the model stops beating the pair — the number a live execution desk
    must beat for the model to be worth running (shadow-run pass criterion).

Run:  XS_DATA_ROOT=strategy_backtest/data_wide XS_TOPK=2 XS_TRADEABLE=1 XS_MIN_SCORE=0.0 \
      .venv/bin/python -m strategy_backtest.experiments.xsec_putspread_lambda
"""

from __future__ import annotations

import datetime as dt
import math

import numpy as np
import polars as pl

from strategy_backtest.backtest import engine, marks
from strategy_backtest.backtest import config as cfg
from strategy_backtest.experiments import xsec_putspread_topk as xt
from strategy_backtest.experiments import xsec_putspread_fixed as xf

OUT_MD = cfg.RESULTS_ROOT / "xsec_putspread_lambda.md"
LAMBDAS = [0.0, 0.25, 0.5, 0.75, 1.0]

_LAM = {"v": 1.0}
_orig_fill = marks._fill


def _lam_fill(price_bid: float, price_ask: float, opening: bool, qty: int) -> float:
    mid = 0.5 * (price_bid + price_ask)
    short = qty < 0
    buy = (not short) if opening else short
    cross = price_ask if buy else price_bid
    return mid + _LAM["v"] * (cross - mid)


def _monthly(led: pl.DataFrame) -> pl.DataFrame:
    d = led.group_by(pl.col("exit_date").alias("date")).agg(pnl=pl.col("pnl").sum()).sort("date")
    alld = pl.DataFrame({"date": pl.date_range(d["date"].min(), d["date"].max(), "1d", eager=True)})
    return (alld.join(d, on="date", how="left").fill_null(0.0)
            .group_by(pl.col("date").dt.truncate("1mo").alias("m")).agg(pl.col("pnl").sum()).sort("m"))


def main() -> None:
    cfg.FILL = "cross"                       # selection walks under frozen conventions
    cand_model = xt.build_candidates()
    cand_pair = xf.build_candidates()
    print(f"model candidates {cand_model.height}, pair candidates {cand_pair.height}")

    marks._fill = _lam_fill
    rows = []
    monthly = {}
    try:
        for lam in LAMBDAS:
            _LAM["v"] = lam
            cfg.FILL = "lambda"              # anything not "mid" routes through _fill's cross path
            row = {"lam": lam}
            for name, cand in (("model", cand_model), ("pair", cand_pair)):
                led = engine.run_book(cand, arm="hold")
                mo = _monthly(led)
                r = mo["pnl"].to_numpy()
                row[f"{name}_sharpe"] = float(r.mean() / r.std(ddof=1) * math.sqrt(12))
                row[f"{name}_pnl"] = float(led["pnl"].sum())
                row[f"{name}_n"] = led.height
                monthly[(name, lam)] = mo
            j = monthly[("model", lam)].join(monthly[("pair", lam)], on="m", how="inner",
                                             suffix="_p")
            d = (j["pnl"] - j["pnl_p"]).to_numpy()
            row["alpha_yr"] = float(d.mean() * 12)
            row["alpha_ir"] = float(d.mean() / d.std(ddof=1) * math.sqrt(12))
            rows.append(row)
            print(f"λ={lam:.2f}  model {row['model_sharpe']:.2f} (${row['model_pnl']:,.0f}) "
                  f"pair {row['pair_sharpe']:.2f} (${row['pair_pnl']:,.0f}) "
                  f"alpha ${row['alpha_yr']:,.0f}/yr IR {row['alpha_ir']:.2f}")
    finally:
        marks._fill = _orig_fill

    L = ["# Fill-capture curve — Sharpe vs execution quality λ (improvement I1)", "",
         "_fill = mid + λ·(cross − mid); λ=0 perfect mid, λ=1 full crossing. Same frozen candidate"
         f" sets at every λ · generated {dt.date.today()}_", "",
         "| λ | model Sharpe | model P&L | pair Sharpe | pair P&L | model−pair alpha $/yr | alpha IR |",
         "| --- | --- | --- | --- | --- | --- | --- |"]
    for r in rows:
        L.append(f"| {r['lam']:.2f} | **{r['model_sharpe']:.2f}** | ${r['model_pnl']:,.0f} "
                 f"| {r['pair_sharpe']:.2f} | ${r['pair_pnl']:,.0f} "
                 f"| ${r['alpha_yr']:,.0f} | {r['alpha_ir']:.2f} |")
    L += ["", "Breakeven read: the λ where alpha ≈ 0 is the execution quality the desk must beat",
          "for the model book to earn its complexity over the trivial pair.", ""]
    OUT_MD.write_text("\n".join(L) + "\n")
    print(f"-> {OUT_MD}")


if __name__ == "__main__":
    main()
