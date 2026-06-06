"""IV-only benchmark — the fair-vol null (STAGE1_TRADING_EVAL_PLAN.md §1.1, A1).

"Sell vol when IV² > trailing RV; size flat." There is no forecaster here: we synthesize a
predictions-shaped frame so the *same* signal/backtest path consumes it. `rv_hat` is set to the
point-in-time trailing realized variance (so `vrp_score = iv2 - rv_hat` becomes `iv2 - trailing_RV`),
`sigma`/quantiles are degenerate (the benchmark never sizes on dispersion), and the gate keys only
on `post_shock` / IV-percentile. This is the bar every forecaster must beat (DM/SPA reference);
beating *random walk* is explicitly not the bar.
"""

from __future__ import annotations

import polars as pl

from trade_eval import config as cfg
from trade_eval import pit

NAME = cfg.BENCHMARK  # "IV-only"


def build_predictions(targets: pl.DataFrame, inputs: pl.DataFrame) -> pl.DataFrame:
    """Predictions-shaped IV-only frame over the OOS window, per traded horizon.

    Mirrors the frozen prediction schema (ticker·date·horizon·rv_hat·sigma·q05..q95·fold_id·model)
    so `run.py` can treat the benchmark exactly like any model. `rv_hat := trailing_RV` is strictly
    point-in-time (past `h` days), so the null carries no look-ahead either.
    """
    oos = pl.lit(cfg.OOS_START).str.to_date()
    frames: list[pl.DataFrame] = []
    for h in cfg.HORIZON_TRADE:
        trv = pit.trailing_rv(inputs, h).select("ticker", "date", "trailing_rv")
        tgt_h = targets.filter((pl.col("horizon") == h) & (pl.col("date") >= oos))
        df = (
            tgt_h.join(trv, on=["ticker", "date"], how="inner")
            .filter(pl.col("trailing_rv").is_not_null() & pl.col("iv2").is_not_null())
            .select(
                "ticker", "date", "horizon",
                rv_hat=pl.col("trailing_rv"),
                sigma=pl.lit(0.0),
                q05=pl.col("trailing_rv"), q10=pl.col("trailing_rv"), q25=pl.col("trailing_rv"),
                q50=pl.col("trailing_rv"), q75=pl.col("trailing_rv"), q90=pl.col("trailing_rv"),
                q95=pl.col("trailing_rv"),
                fold_id=pl.lit(-1, dtype=pl.Int32),
                model=pl.lit(NAME),
            )
        )
        frames.append(df)
    return pl.concat(frames).sort("ticker", "horizon", "date")
