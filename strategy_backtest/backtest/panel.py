"""Build the roll-date candidate panel for both segments (design §2.2, §3, §4).

Assembles, per (ticker, date):
  * regime columns        — iv_30d, iv_slope (= iv_90d - iv_30d), vix, vix3m  (from inputs)
  * implied variance       — iv2, target_var                                   (from targets, h=22)
  * forecast / proxy       — rv_hat, sigma  (EnsembleTopK, >=2010)  OR  trailing RV (degraded)
  * PIT trailing stats     — IVrank (G2), dispersion 80th-pctile (G4)

then picks non-overlapping monthly roll dates (every ROLL_CADENCE trading days per ticker, anchored
at the 2007 backtest start) and runs the lean-core gate + sizing per segment. The two segments:

  * degraded (2007 -> 2010-01-04) : no forecaster -> rv_hat = trailing RV, IV-only inverse-risk size,
                                     G4 dropped (the GFC co-equal stress test).
  * forecaster (>= 2010-01-04)    : full EnsembleTopK, full lean-core gate.
"""

from __future__ import annotations

import datetime as dt

import polars as pl

from strategy_backtest.backtest import config as cfg
from strategy_backtest.backtest import pit, signals

_H = cfg.PRIMARY_HORIZON
_START = dt.date.fromisoformat(cfg.BACKTEST_START)
_HEADLINE = dt.date.fromisoformat(cfg.HEADLINE_START)


def _load() -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame]:
    inputs = pl.read_parquet(cfg.INPUTS_PARQUET).select(
        "ticker", "date", "group", "iv_30d", "iv_slope", "vix", "vix3m", "total_rv",
        "skew_25d", "vvix", "credit_mom", "ret_cc",        # stress-composite inputs (§4.3)
    )
    targets = pl.read_parquet(cfg.TARGETS_PARQUET).filter(pl.col("horizon") == _H).select(
        "ticker", "date", "iv2", "target_var"
    )
    preds = pl.read_parquet(cfg.PREDICTIONS_PARQUET).filter(pl.col("horizon") == _H).select(
        "ticker", "date", "rv_hat", "sigma", "fold_id"
    )
    return inputs, targets, preds


_STRESS_FLAGS = ["st_skew", "st_vvix", "st_credit", "st_sma", "st_shock"]
_STRESS_MAP = {"skew": "st_skew", "vvix": "st_vvix", "credit": "st_credit",
               "sma": "st_sma", "shock": "st_shock"}


def _stress_flags(inputs: pl.DataFrame) -> pl.DataFrame:
    """Compute the five PIT stress sub-flags (design §4.3) on the daily panel, per ticker.

    All are point-in-time (trailing windows / expanding percentiles only). A null threshold (warm-up)
    yields a null comparison → filled False, so an untrusted statistic never fabricates a stand-down.
      st_skew   : 25Δ skew above its own trailing p90 (priced crash risk)
      st_vvix   : vol-of-vol above trailing p90 (regime uncertainty rising)
      st_credit : exogenous credit momentum above trailing p80 (credit stress; LQD/HY-OAS proxy)
      st_sma    : price index below its own 200-day SMA (downtrend)
      st_shock  : recent (STRESS_SHOCK_WINDOW-day) min close-close return below trailing p2.5 (post-shock)
    """
    df = inputs.sort(["ticker", "date"])
    df = df.with_columns(
        _pxidx=pl.col("ret_cc").fill_null(0.0).cum_sum().over("ticker").exp(),
        _shock_min=pl.col("ret_cc").rolling_min(window_size=cfg.STRESS_SHOCK_WINDOW,
                                                 min_samples=1).over("ticker"),
    )
    df = df.with_columns(
        _sma=pl.col("_pxidx").rolling_mean(window_size=cfg.STRESS_SMA_WINDOW,
                                           min_samples=cfg.STRESS_SMA_WINDOW).over("ticker")
    )
    df = pit.trailing_pctile(df, "skew_25d", cfg.STRESS_SKEW_P,
                             min_periods=cfg.STRESS_MIN_PERIODS, out_col="_skew_thr")
    df = pit.trailing_pctile(df, "vvix", cfg.STRESS_VVIX_P,
                             min_periods=cfg.STRESS_MIN_PERIODS, out_col="_vvix_thr")
    df = pit.trailing_pctile(df, "credit_mom", cfg.STRESS_CREDIT_P,
                             min_periods=cfg.STRESS_MIN_PERIODS, out_col="_credit_thr")
    df = pit.trailing_pctile(df, "ret_cc", cfg.STRESS_SHOCK_P,
                             min_periods=cfg.STRESS_MIN_PERIODS, out_col="_shock_thr")
    return df.with_columns(
        st_skew=(pl.col("skew_25d") > pl.col("_skew_thr")).fill_null(False),
        st_vvix=(pl.col("vvix") > pl.col("_vvix_thr")).fill_null(False),
        st_credit=(pl.col("credit_mom") > pl.col("_credit_thr")).fill_null(False),
        st_sma=(pl.col("_pxidx") < pl.col("_sma")).fill_null(False),
        st_shock=(pl.col("_shock_min") < pl.col("_shock_thr")).fill_null(False),
    ).drop("_pxidx", "_shock_min", "_sma", "_skew_thr", "_vvix_thr", "_credit_thr", "_shock_thr")


def apply_stress(df: pl.DataFrame, components) -> pl.DataFrame:
    """Veto entries where any active stress sub-flag fires: set size_units→0, stress=True, gate&=~stress.

    `components` is the active subset of STRESS_MAP keys; empty → no veto (stress=False everywhere).
    Used both by the production path (via cfg.STRESS_COMPONENTS) and the §4.3 ablation script.
    """
    cols = [_STRESS_MAP[c] for c in components if c in _STRESS_MAP]
    if not cols:
        return df.with_columns(stress=pl.lit(False))
    expr = pl.lit(False)
    for c in cols:
        expr = expr | pl.col(c)
    return df.with_columns(stress=expr).with_columns(
        size_units=pl.when(pl.col("stress")).then(0.0).otherwise(pl.col("size_units")),
        gate=(pl.col("gate") & ~pl.col("stress")),
    )


def _roll_dates(inputs: pl.DataFrame) -> pl.DataFrame:
    """Per-ticker non-overlapping roll dates: every ROLL_CADENCE-th trading day from 2007."""
    cal = (
        inputs.filter(pl.col("date") >= _START)
        .select("ticker", "date").unique().sort("ticker", "date")
        .with_columns(_cidx=pl.int_range(pl.len()).over("ticker"))
    )
    return cal.filter((pl.col("_cidx") % cfg.ROLL_CADENCE) == 0).select("ticker", "date")


def build_candidates() -> pl.DataFrame:
    """Return the concatenated, gated, sized roll-date candidate frame for the whole backtest."""
    inputs, targets, preds = _load()

    # --- PIT IVrank (G2) over the full daily iv_30d history, per ticker.
    inputs = pit.trailing_rank(inputs, "iv_30d", min_periods=cfg.DISP_MIN_PERIODS, out_col="ivrank")
    # --- trailing RV (degraded rv_hat) over h=22 days.
    inputs = pit.trailing_rv(inputs, _H, out_col="trailing_rv")
    # --- PIT stress-composite sub-flags (§4.3), carried into candidates for the gate + ablation.
    inputs = _stress_flags(inputs)

    daily = inputs.join(targets, on=["ticker", "date"], how="left")
    roll = _roll_dates(inputs)

    # ----------------------------------------------------------------- forecaster segment (>=2010)
    # De-bias rv_hat for sizing (§10.B): PIT per-ticker log-bias vs realised target_var -> rv_hat_cal,
    # used ONLY for VRP. The gate (incl. G4) keeps raw rv_hat, so trade SELECTION is unchanged.
    fc = preds.join(targets.select("ticker", "date", "target_var"), on=["ticker", "date"], how="left")
    if cfg.DEBIAS_VRP:
        fc = pit.trailing_debias(fc, "rv_hat", "target_var", embargo=cfg.DEBIAS_EMBARGO,
                                 min_periods=cfg.DEBIAS_MIN_PERIODS, out_col="log_bias")
        fc = fc.with_columns(
            rv_hat_cal=pl.when(pl.col("log_bias").is_not_null())
            .then(pl.col("rv_hat") * pl.col("log_bias").exp())
            .otherwise(pl.col("rv_hat"))
        )
    else:
        fc = fc.with_columns(rv_hat_cal=pl.col("rv_hat"))
    fc = fc.with_columns(dispersion_raw=(pl.col("sigma") / pl.col("rv_hat")))
    fc = pit.trailing_pctile(fc, "dispersion_raw", cfg.DISP_PCTILE,
                             min_periods=cfg.DISP_MIN_PERIODS, out_col="disp_p80")
    fc_roll = (
        roll.filter(pl.col("date") >= _HEADLINE)
        .join(daily, on=["ticker", "date"], how="inner")
        .join(fc.select("ticker", "date", "rv_hat", "rv_hat_cal", "sigma", "fold_id", "disp_p80"),
              on=["ticker", "date"], how="inner")
        .with_columns(horizon=pl.lit(_H), segment=pl.lit("forecaster"),
                      rv_hat_vrp=pl.col("rv_hat_cal"))
        .drop_nulls(["iv2", "rv_hat"])
    )
    fc_sig = signals.build_signals(fc_roll, "forecaster")

    # ----------------------------------------------------------------- degraded segment (2007-2010)
    dg_roll = (
        roll.filter(pl.col("date") < _HEADLINE)
        .join(daily, on=["ticker", "date"], how="inner")
        .with_columns(
            horizon=pl.lit(_H), segment=pl.lit("degraded"),
            rv_hat=pl.col("trailing_rv"), rv_hat_vrp=pl.col("trailing_rv"),
            sigma=pl.lit(None, dtype=pl.Float64),
            fold_id=pl.lit(None, dtype=pl.Int64), disp_p80=pl.lit(None, dtype=pl.Float64),
        )
        .drop_nulls(["iv2", "rv_hat"])
    )
    dg_sig = signals.build_signals(dg_roll, "degraded")

    keep = [
        "ticker", "date", "group", "segment", "horizon", "iv2", "rv_hat", "rv_hat_vrp",
        "sigma", "fold_id", "iv_30d", "iv_slope", "vix", "vix3m", "ivrank", "target_var",
        *_STRESS_FLAGS,
        *signals.SIGNAL_COLS,
    ]
    out = pl.concat([dg_sig.select(keep), fc_sig.select(keep)], how="vertical_relaxed")
    # Stress composite (§4.3): veto entries when active when STRESS_GATE — ablation decides the subset.
    active = cfg.STRESS_COMPONENTS if cfg.STRESS_GATE else ()
    out = apply_stress(out, active)
    return out.sort("date", "ticker")
