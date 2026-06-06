"""Optional user drop-in zone — register your own ideas here without touching framework files.

This module is imported by `run.py` after the built-ins, so anything you register here is
discoverable by `--structures/--management/--hedge`. It is the intended place to prototype the
plan's experiments (E1–E5, new structures, alternative managers) so the core stays stable.

Example — a 1σ-by-IV strangle and a 25% profit-take arm:

    from stage2_trade_eval.contracts import (
        Leg, Structure, ManagementArm, register_structure, register_management,
    )

    @register_structure
    class WideStrangle(Structure):
        name = "wide_strangle"
        defined_risk = False
        def legs(self, chain, ctx):
            kp = chain.strike_by_delta("P", 0.10)
            kc = chain.strike_by_delta("C", 0.10)
            return [Leg("P", kp, -1), Leg("C", kc, -1)] if kp and kc and kp < kc else []

Leave the body empty to register nothing.
"""

from __future__ import annotations

import os

import polars as pl

from stage2_trade_eval import config as cfg


# =====================================================================================
# E3 — leakage-safe PIT σ-recalibration overlay (plan §A.4 E3)
# =====================================================================================
#
# The Stage-1 report flags h=22 forecast-dispersion *under-coverage*: the predictive `sigma`
# is too tight, so the gate/size mis-judge the tail. E3 applies a MONOTONE scale to sigma,
#
#       sigma'  =  a_t · sigma ,     a_t > 0 ,
#
# where `a_t` is a point-in-time conformal scale that re-centers the empirical coverage of the
# *standardized residual*  z = (target_var − rv_hat) / sigma  back to nominal. Concretely we take
# `a_t` = a trailing high quantile of |z| over PAST, settled residuals (a conformal radius): if
# realized outcomes are landing outside ±sigma more often than nominal, |z| has fat trailing
# quantiles and a_t > 1 widens sigma; if sigma is already well-calibrated, a_t ≈ 1.
#
# ------------------------- LEAKAGE PROOF (the non-negotiable part) -------------------------
# `target_var[s]` is the realized variance over the FORWARD window [s, s+h]. It is therefore only
# *observable* at date s+h, never at s. A scale used at decision date t may only consume residuals
# whose outcome window is entirely in the past: s + h ≤ t. We enforce a strictly stronger lag by
# shifting each ticker's residual series back by LAG = h + 1 (= 23 trading days at h=22) BEFORE the
# trailing/expanding statistic is formed, and additionally only emit a_t once `min_periods` settled
# residuals exist. Hence the basis for a_t at row t uses residuals from rows ≤ t − (h+1), so the
# entry-day [t, t+h] outcome (and the h−1 partially-overlapping prior windows) can never enter a_t.
# The assertion below pins LAG ≥ h + 1 so a refactor that weakens the lag fails loudly.
# ------------------------------------------------------------------------------------------------

_EXPANDING = 10_000_000          # window larger than any ticker history -> expanding (PIT) aggregation
_RECAL_Q = 0.90                  # conformal coverage radius: trailing 90th pctile of |z|
_RECAL_MIN_PERIODS = 252         # don't trust the scale until a year of settled residuals exists
_A_FLOOR, _A_CEIL = 0.5, 3.0     # clamp the monotone scale to a sane band (avoid degenerate blow-ups)


def recalibrate_sigma_pit(preds: pl.DataFrame, targets: pl.DataFrame, h: int) -> pl.DataFrame:
    """Return `preds` with `sigma` replaced by `a_t · sigma`, `a_t` a PIT conformal scale.

    Leakage-safe by construction (see module proof): the residual basis is lagged by `h + 1`
    trading days per ticker, so no [t, t+h] realization can reach the scale used at t. Rows without
    enough settled history keep `a_t = 1` (identity), i.e. the overlay never *tightens* on thin data.
    """
    lag = h + 1
    # Hard guard: the lag MUST be at least h + 1 so the forward outcome window cannot leak.
    assert lag >= h + 1, f"E3 leakage guard: residual lag {lag} < h+1 ({h + 1}) — would leak [t,t+h]"

    truth = (
        targets.filter(pl.col("horizon") == h)
        .select("ticker", "date", "target_var")
    )
    df = preds.join(truth, on=["ticker", "date"], how="left").sort("ticker", "date")

    # standardized residual z = (realized − forecast) / sigma  (only defined where sigma>0)
    df = df.with_columns(
        _absz=pl.when(pl.col("sigma") > 0)
        .then((pl.col("target_var") - pl.col("rv_hat")).abs() / pl.col("sigma"))
        .otherwise(None)
    )
    # LAG the residual series back by (h+1) rows per ticker BEFORE any trailing stat: the value at
    # row t now only sees residuals settled at/by t-(h+1) -> no forward-window leakage.
    df = df.with_columns(_absz_lagged=pl.col("_absz").shift(lag).over("ticker"))

    # expanding (point-in-time) high quantile of the LAGGED |z| = conformal scale a_t
    a = (
        pl.col("_absz_lagged")
        .rolling_quantile(quantile=_RECAL_Q, interpolation="linear",
                          window_size=_EXPANDING, min_samples=_RECAL_MIN_PERIODS)
        .over("ticker")
    )
    df = df.with_columns(
        sigma=(pl.col("sigma") * a.fill_null(1.0).clip(_A_FLOOR, _A_CEIL))
    )
    return df.drop("_absz", "_absz_lagged", "target_var")


def maybe_recalibrate_sigma(preds: pl.DataFrame, targets: pl.DataFrame, h: int) -> pl.DataFrame:
    """E3 hook: apply the PIT σ-recalibration overlay iff STAGE2_E3_SIGMA_RECAL is set.

    Default (env unset) -> identity, so W2/W4 and every other sweep are byte-for-byte unaffected.
    """
    if os.environ.get("STAGE2_E3_SIGMA_RECAL", "0") not in ("1", "true", "True"):
        return preds
    return recalibrate_sigma_pit(preds, targets, h)


def maybe_register_extra() -> None:
    """Hook called once by `run.py`; add `register_*` imports/classes above and call them here."""
    return
