"""The v2 lean-core entry gate + VRP-tilt sizing (design §4, §7).

Turns a per-(ticker, date) frame carrying the forecast (rv_hat, sigma) — or, for the degraded GFC
segment, trailing RV in place of the forecast — plus the regime columns (iv_30d, iv_slope, vix,
vix3m, the PIT IVrank and dispersion percentile) into the two decisions the engine consumes:

    gate        : bool   — all primary gates pass (G7 liquidity is enforced later, at fill time)
    size_units  : float  — inverse-risk fractional-Kelly sizing units u (0 when gated out)

Two modes:
  * "forecaster"  — headline book (>=2010): rv_hat/sigma from EnsembleTopK; G4 dispersion gate live;
                    disp = sigma/rv_hat.
  * "degraded"    — GFC book (2007–2010): rv_hat = trailing RV, no sigma; G4 dropped; IV-only
                    inverse-risk sizing with disp_iv = iv_30d / IV_REF.

Every gate is point-in-time. A null trailing threshold (insufficient history) cannot gate, so it
passes — never fabricates a stand-down it has no basis for.
"""

from __future__ import annotations

import polars as pl

from strategy_backtest.backtest import config as cfg

SIGNAL_COLS = [
    "vrp_score", "vrp_rel", "dispersion", "g2_ivrank", "g3_contango",
    "g4_disp", "gate", "size_units",
]


def build_signals(df: pl.DataFrame, mode: str) -> pl.DataFrame:
    """Augment a roll-date candidate frame with the lean-core gate + sizing units.

    Required columns: ticker, date, horizon, iv2, iv_30d, iv_slope, vix, vix3m, rv_hat, rv_hat_vrp,
    ivrank. For mode="forecaster" also: sigma, disp_p80. The frame must already carry the PIT trailing
    statistics (`ivrank`, `disp_p80`) joined from the full daily panel.

    VRP uses `rv_hat_vrp` (the de-biased forecast, §10.B) so size reflects genuine richness; the G4
    dispersion gate keeps the RAW `rv_hat` so the de-bias never changes which trades fire.
    """
    if mode not in ("forecaster", "degraded"):
        raise ValueError(f"unknown signal mode {mode!r}")

    df = df.with_columns(
        vrp_score=(pl.col("iv2") - pl.col("rv_hat_vrp")),
        vrp_rel=((pl.col("iv2") - pl.col("rv_hat_vrp")) / pl.col("iv2"))
        .clip(lower_bound=cfg.VRP_FLOOR),
    )

    # --- G2: IV not in stress. IVrank <= 0.85. Null rank (warmup) -> cannot gate -> pass.
    g2 = (pl.col("ivrank") <= cfg.GATE_IVRANK_MAX) | pl.col("ivrank").is_null()
    # --- G3: term structure in contango. own iv_slope > 0 AND vix3m > vix.
    g3 = (pl.col("iv_slope") > 0) & (pl.col("vix3m") > pl.col("vix"))

    if mode == "forecaster":
        df = df.with_columns(dispersion=(pl.col("sigma") / pl.col("rv_hat")))
        # --- G4: forecast dispersion not hot. disp <= trailing-80th-pctile. Null -> pass.
        g4 = (pl.col("dispersion") <= pl.col("disp_p80")) | pl.col("disp_p80").is_null()
        disp2 = pl.col("dispersion") ** 2
    else:
        # No forecaster: IV-only inverse-risk. dispersion proxy = iv_30d / IV_REF (dimensionless).
        df = df.with_columns(dispersion=(pl.col("iv_30d") / cfg.IV_REF))
        g4 = pl.lit(True)                       # G4 cannot be evaluated without the forecaster
        disp2 = pl.col("dispersion") ** 2

    gate = g2 & g3 & g4
    u = (cfg.KELLY_C * pl.col("vrp_rel") / disp2).clip(lower_bound=0.0, upper_bound=cfg.SIZE_CAP)

    return df.with_columns(
        g2_ivrank=g2, g3_contango=g3, g4_disp=g4, gate=gate,
        size_units=pl.when(gate).then(u).otherwise(0.0),
    )
