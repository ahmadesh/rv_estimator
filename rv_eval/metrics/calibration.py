"""Conditional calibration (eval plan §6) — catch the model that is unbiased on average
but biased exactly when it matters (after vol spikes / in high-IV regimes).

Consumes a scored frame that already has the Tier-1 pointwise columns (`qlike`, `log_err`).
"""

from __future__ import annotations

import polars as pl

from rv_eval.metrics.tier1 import add_pointwise

# A meaningful average over-/under-prediction in log space.
_BIAS_TOL = 0.10


def _ensure_pointwise(scored: pl.DataFrame) -> pl.DataFrame:
    return scored if "log_err" in scored.columns else add_pointwise(scored)


def conditional_table(scored: pl.DataFrame, regime_col: str) -> pl.DataFrame:
    """QLIKE and signed bias per (model, horizon, regime bucket)."""
    s = _ensure_pointwise(scored).filter(pl.col(regime_col).is_not_null())
    return (
        s.group_by(["model", "horizon", regime_col])
        .agg(n=pl.len(), qlike=pl.col("qlike").mean(), log_bias=pl.col("log_err").mean())
        .sort(["model", "horizon", regime_col])
    )


def post_shock_flags(scored: pl.DataFrame) -> pl.DataFrame:
    """Per (model, horizon): overall vs post-shock bias, flagging the §6 trap."""
    s = _ensure_pointwise(scored)
    overall = s.group_by(["model", "horizon"]).agg(
        bias_all=pl.col("log_err").mean(), qlike_all=pl.col("qlike").mean())
    shock = (
        s.filter(pl.col("post_shock")).group_by(["model", "horizon"])
        .agg(bias_postshock=pl.col("log_err").mean(),
             qlike_postshock=pl.col("qlike").mean(), n_postshock=pl.len())
    )
    out = overall.join(shock, on=["model", "horizon"], how="left")
    return out.with_columns(
        trap_flag=(pl.col("bias_all").abs() < _BIAS_TOL)
        & (pl.col("bias_postshock").abs() >= _BIAS_TOL)
    ).sort(["model", "horizon"])
