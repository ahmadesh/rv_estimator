"""Tier-1 metrics (eval plan §3) — the cheap bundle that gates every iteration.

Operates on a long "scored" frame: predictions joined to truth, with at least
  ticker, group, horizon, model, rv_hat, target_var (+ sigma, q05..q95) per row.
QLIKE is the primary loss (on variance); log-RMSE/MAE are the non-QLIKE second opinion.
"""

from __future__ import annotations

import polars as pl

from rv_eval import config as C

_EPS = 1e-12


def add_pointwise(scored: pl.DataFrame) -> pl.DataFrame:
    """Attach per-row loss/calibration columns used by every Tier-1 summary."""
    rv = pl.col("target_var").clip(lower_bound=_EPS)
    hat = pl.col("rv_hat").clip(lower_bound=_EPS)
    ratio = rv / hat
    out = scored.with_columns(
        qlike=ratio - ratio.log() - 1.0,
        log_err=rv.log() - hat.log(),                 # signed: <0 over-predict
    ).with_columns(
        sq_log_err=pl.col("log_err") ** 2,
        abs_log_err=pl.col("log_err").abs(),
    )
    if {"q05", "q95", "q25", "q75"}.issubset(out.columns):
        out = out.with_columns(
            in90=((rv >= pl.col("q05")) & (rv <= pl.col("q95"))).cast(pl.Float64),
            in50=((rv >= pl.col("q25")) & (rv <= pl.col("q75"))).cast(pl.Float64),
        )
    # Pinball / quantile loss averaged over the quantile grid.
    pin_terms = []
    for p in C.QUANTILES:
        col = f"q{int(round(p * 100)):02d}"
        if col in out.columns:
            d = pl.col("target_var") - pl.col(col)
            pin_terms.append(pl.max_horizontal(p * d, (p - 1.0) * d))
    if pin_terms:
        out = out.with_columns(pinball=sum(pin_terms) / len(pin_terms))
    return out


def summarize(scored: pl.DataFrame, by: list[str]) -> pl.DataFrame:
    """Aggregate the pointwise columns to a metric table grouped by `by`."""
    aggs = [
        pl.len().alias("n"),
        pl.col("qlike").mean().alias("qlike"),
        pl.col("sq_log_err").mean().sqrt().alias("log_rmse"),
        pl.col("abs_log_err").mean().alias("log_mae"),
        pl.col("log_err").mean().alias("log_bias"),   # signed; <0 = over-predict
    ]
    if "in90" in scored.columns:
        aggs += [pl.col("in90").mean().alias("cov90"), pl.col("in50").mean().alias("cov50")]
    if "pinball" in scored.columns:
        aggs.append(pl.col("pinball").mean().alias("pinball"))
    return scored.group_by(by).agg(aggs).sort(by)


def rank_correlation(scored: pl.DataFrame) -> pl.DataFrame:
    """Within-group cross-sectional Spearman corr of forecast vs realized (per model, horizon).

    For each (model, horizon, group, date) with ≥3 tickers, rank R̂V vs RV across tickers and
    average the daily Spearman correlations — groundwork for picking one name per group (§3).
    """
    rows = []
    for (model, h, grp), sub in scored.partition_by(["model", "horizon", "group"], as_dict=True).items():
        daily = []
        for (_d,), day in sub.partition_by(["date"], as_dict=True).items():
            if day.height >= 3:
                daily.append(pl.Series(day["rv_hat"]).rank().corr(
                    pl.Series(day["target_var"]).rank()))
        daily = [c for c in daily if c is not None]
        if daily:
            rows.append({"model": model, "horizon": h, "group": grp,
                         "rank_corr": float(sum(daily) / len(daily)), "n_days": len(daily)})
    return pl.DataFrame(rows)
