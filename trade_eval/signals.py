"""Output -> trading-signal map (STAGE1_TRADING_EVAL_PLAN.md §1.2 / §2).

Turns the frozen per-row forecast (`rv_hat`, `sigma`, `q05..q95`) plus the regime columns
already in `targets.parquet` (`iv2`, `iv_pctile_bucket`, `post_shock`) into the three strategy
decisions — conditional-VRP score, regime gate `{trade,reduce,avoid}`, and position size — that
the backtest consumes. Every threshold that needs calibration (the dispersion percentile /
terciles) is computed point-in-time via `pit.py`, so nothing here can see future data.

A `StrategyConfig` carries the ablation toggles (gate on/off, sizing forecast/flat, sigma vs
quantile-spread risk scale). Sizing is expressed in **dimensionless relative** units — premium
richness `vrp/iv2` divided by a dimensionless dispersion `sigma` (or `(q95-q05)/rv_hat`) — so the
inverse-risk fraction is naturally O(1) and the A3/A5 sizing ablations actually move size rather
than saturating the cap. The absolute level (set by `K`, `BASE_NOTIONAL`) is a fixed constant,
never fit on the OOS P&L (§6); only the *relative* sizing carries forecast information.
"""

from __future__ import annotations

from dataclasses import dataclass

import polars as pl

from trade_eval import config as cfg
from trade_eval import pit


@dataclass(frozen=True)
class StrategyConfig:
    """Ablation toggles for one backtest cell. Set once; never tuned on OOS P&L."""

    name: str = "baseline"
    use_gate: bool = True                 # A2: regime gate on/off
    sizing: str = "forecast"              # A3: {"forecast","flat"}
    risk_scale: str = cfg.RISK_SCALE_DEFAULT  # A5: {"sigma","qspread"}
    entry: str = "signal"                 # A7: {"signal","random","always"}
    manage: bool = False                  # A9: intra-trade daily re-gating on/off
    is_benchmark: bool = False            # IV-only null (vrp from trailing RV, flat size)


# Columns the backtest / portfolio rely on downstream of build_signals.
SIGNAL_COLS = [
    "vrp_score", "dispersion", "gate", "gate_mult", "risk_rel", "size", "structure_haircut",
]


def _gate_expr(scored: pl.DataFrame, sc: StrategyConfig) -> pl.DataFrame:
    """Attach the `{trade,reduce,avoid}` regime gate and its size multiplier (§2.2)."""
    if not sc.use_gate:
        # A2-off: every eligible row trades at full size; no regime gating at all.
        return scored.with_columns(
            gate=pl.lit("trade"), gate_mult=pl.lit(1.0)
        )

    iv_cheap = pl.col("iv_pctile_bucket").is_in(list(cfg.IV_CHEAP_BUCKETS))
    if sc.is_benchmark:
        # The IV-only null has no forecast dispersion; its gate keys only on post_shock /
        # vrp sign and the IV-percentile bucket (the fair-vol comparator's own regime signals).
        avoid = pl.col("post_shock").fill_null(False) | (pl.col("vrp_score") <= 0)
        reduce = iv_cheap.fill_null(False)
    else:
        disp_hot = pl.col("dispersion") > pl.col("disp_p80")        # null threshold -> False
        mid_tercile = (pl.col("dispersion") >= pl.col("disp_p33")) & (
            pl.col("dispersion") <= pl.col("disp_p67")
        )
        avoid = (
            pl.col("post_shock").fill_null(False)
            | (pl.col("vrp_score") <= 0)
            | disp_hot.fill_null(False)
        )
        reduce = iv_cheap.fill_null(False) | mid_tercile.fill_null(False)

    gate = (
        pl.when(avoid).then(pl.lit("avoid"))
        .when(reduce).then(pl.lit("reduce"))
        .otherwise(pl.lit("trade"))
    )
    gate_mult = (
        pl.when(avoid).then(pl.lit(0.0))
        .when(reduce).then(pl.lit(cfg.REDUCE_MULT))
        .otherwise(pl.lit(1.0))
    )
    return scored.with_columns(gate=gate, gate_mult=gate_mult)


def build_signals(scored: pl.DataFrame, sc: StrategyConfig) -> pl.DataFrame:
    """Augment a (predictions ⋈ targets) frame for ONE horizon with the strategy signals.

    `scored` must carry: ticker, date, group, horizon, rv_hat, sigma, q05..q95, iv2,
    iv_pctile_bucket, post_shock (the benchmark path supplies rv_hat := trailing_RV upstream).
    Returns the frame with `SIGNAL_COLS` added.
    """
    scored = scored.with_columns(
        vrp_score=(pl.col("iv2") - pl.col("rv_hat")),
        dispersion=(pl.col("sigma") / pl.col("rv_hat")),
        qspread_rel=((pl.col("q95") - pl.col("q05")) / pl.col("rv_hat")),
    )

    # Point-in-time dispersion percentile + terciles (per ticker, expanding). Benchmark has a
    # degenerate constant sigma=0 so these are unused on that path (gate uses only post_shock/IV).
    scored = pit.trailing_pctile(
        scored, "dispersion", cfg.DISP_PCTILE, min_periods=cfg.DISP_MIN_PERIODS, out_col="disp_p80"
    )
    scored = pit.trailing_pctile(
        scored, "dispersion", cfg.DISP_TERCILE_LO, min_periods=cfg.DISP_MIN_PERIODS, out_col="disp_p33"
    )
    scored = pit.trailing_pctile(
        scored, "dispersion", cfg.DISP_TERCILE_HI, min_periods=cfg.DISP_MIN_PERIODS, out_col="disp_p67"
    )

    scored = _gate_expr(scored, sc)

    # Relative inverse-risk size. "flat" sizing (A3-off) is a constant unit scaled only by the
    # gate; "forecast" sizing keys on the dimensionless dispersion (sigma) or quantile spread (A5).
    risk_rel = pl.col("dispersion") if sc.risk_scale == "sigma" else pl.col("qspread_rel")
    vrp_rel = (pl.col("vrp_score") / pl.col("iv2")).clip(lower_bound=0.0)
    if sc.sizing == "flat" or sc.is_benchmark:
        size_raw = pl.lit(1.0)
        risk_out = pl.lit(float("nan"))
    else:
        size_raw = (vrp_rel / (cfg.K * (risk_rel**2))).clip(lower_bound=0.0, upper_bound=cfg.SIZE_CAP)
        risk_out = risk_rel

    haircut = pl.col("ticker").replace_strict(
        cfg.STRUCTURE_HAIRCUT, default=cfg.STRUCTURE_HAIRCUT_DEFAULT, return_dtype=pl.Float64
    )

    scored = scored.with_columns(
        risk_rel=risk_out,
        structure_haircut=haircut,
        size=(cfg.BASE_NOTIONAL * size_raw * pl.col("gate_mult") * haircut),
    )
    return scored
