"""STAR-HAR — Smooth-Transition HAR (ITER2_MODEL_CATALOG.md §3 model 30, Track E, P1).

A smooth-transition autoregressive (STAR) variant of the HAR: instead of a hard
regime split (Threshold-HAR, model 29), the HAR coefficients vary *smoothly* with an
observable volatility-regime state via a logistic transition weight.

State variable (the transition variable):
    `vix_pctile` — the EXPANDING percentile rank of the VIX level, per ticker, over the
    FULL point-in-time series. It is a trailing feature (rank of today's vix among all
    at-or-before-today vix values), so it is leak-safe: each (ticker, date) gets the same
    value regardless of which fold slice it later lands in.

Transition weight (smooth, in [0, 1]):
    `g = 1 / (1 + exp(-SLOPE * (vix_pctile - THRESHOLD)))`
    a logistic of the state, with the slope/threshold FROZEN by the catalog spec
    (THRESHOLD=0.5 = the median percentile, SLOPE=10 = a moderately sharp but still smooth
    transition). g -> 0 in calm regimes (low vix percentile), g -> 1 in stressed regimes.

Design:
    For each base HAR feature f in HAR_FEATURES we add the interaction column f * g. The
    fitted model is ONE log-OLS per (ticker, horizon) on
        HAR_FEATURES  +  [f * g for f in HAR_FEATURES]  +  [vix_pctile]
    so the effective HAR slope on feature f is `beta_f + beta_{f×g} * g(state)` — a smooth
    blend of a calm-regime slope and a stressed-regime slope. One OLS, cheaper and smoother
    than the hard threshold split (model 29). Ref: smooth-transition HAR / STAR.

Reuse pattern P1: `_AttachMixin` builds the derived columns once on the full
`inputs.parquet` series and JOINs them into X by (ticker, date) at fit/predict (mirroring
har_cj.py::_attach, incl. the synthetic-X fallback), and `_LinearLogHAR` does the
per-(ticker, horizon) log-OLS + lognormal quantiles. No edits to rv_eval/.

`vix` lives in inputs.parquet (and survives build_features), so it is present to build the
expanding percentile from. The interaction/percentile columns are NOT in features.py — they
are derived here, leaving features.py untouched.
"""

from __future__ import annotations

import polars as pl

from rv_eval.features import HAR_FEATURES
from rv_eval.model_contract import _LinearLogHAR

from candidate_models._base_v2 import _AttachMixin

# Frozen logistic-transition hyperparameters (catalog spec; not tuned on OOS).
_SLOPE = 10.0       # logistic steepness on the [0,1] percentile state — smooth, not a hard step
_THRESHOLD = 0.5    # transition centred at the median (50th) expanding vix percentile

_STATE_COL = "vix_pctile"                                   # the observable transition variable
_WEIGHT_COL = "star_g"                                      # the logistic transition weight in [0,1]
_INTERACT = [f"{f}__x_g" for f in HAR_FEATURES]             # HAR feature x transition weight
_STAR_FEATURES = [_STATE_COL] + _INTERACT
_KEYS = ["ticker", "date"]


def _star_panel(src: pl.DataFrame) -> pl.DataFrame:
    """Build the full-history transition STATE + logistic WEIGHT from `vix`.

    `vix_pctile` is the EXPANDING percentile rank of vix per ticker: for each row, the
    fraction of at-or-before-date vix observations <= today's vix, in (0, 1]. Evaluated on
    the FULL series so every (ticker, date) is point-in-time (uses only past+current vix)
    and stable across fold slices. NEVER recompute on a one-month predict slice (it would
    misrank the leading rows). `star_g` is the logistic transition weight in [0, 1].

    Only `vix` is needed here (it is in inputs.parquet), so this derive-and-join is leak-safe
    via `_AttachMixin`. The HAR x weight interaction columns are formed AFTER the join, in
    `STARHAR._attach`, from the HAR features (which live on X post-`build_features`, not in
    raw inputs.parquet).
    """
    df = src.sort("ticker", "date")
    # Expanding percentile rank of vix, per ticker, point-in-time (only past+current rows):
    # for each row, mean(at-or-before-date vix <= today's vix) in (0, 1].
    df = df.with_columns(
        pl.col("vix")
        .map_batches(_expanding_pctile, return_dtype=pl.Float64)
        .over("ticker")
        .alias(_STATE_COL)
    )
    # Logistic transition weight in [0, 1].
    df = df.with_columns(
        (1.0 / (1.0 + (-_SLOPE * (pl.col(_STATE_COL) - _THRESHOLD)).exp())).alias(_WEIGHT_COL)
    )
    # NaN (where vix was null) -> polars null so the base fit's drop_nulls(needs) removes those
    # rows; a float NaN would otherwise survive drop_nulls and poison the OLS design matrix.
    df = df.with_columns(
        pl.col(_STATE_COL).fill_nan(None), pl.col(_WEIGHT_COL).fill_nan(None)
    )
    return df.select(_KEYS + [_STATE_COL, _WEIGHT_COL])


def _expanding_pctile(s: pl.Series) -> pl.Series:
    """Expanding percentile of a series: for each i, mean(x[:i+1] <= x[i]) (in (0,1])."""
    import numpy as np

    x = s.to_numpy().astype(float)
    out = np.empty(x.shape[0], dtype=float)
    for i in range(x.shape[0]):
        window = x[: i + 1]
        cur = x[i]
        if not np.isfinite(cur):
            out[i] = np.nan
            continue
        finite = window[np.isfinite(window)]
        out[i] = float(np.mean(finite <= cur)) if finite.size else np.nan
    return pl.Series(out)


class STARHAR(_AttachMixin, _LinearLogHAR):
    """Smooth-transition HAR: HAR features interacted with a logistic vix-percentile weight."""

    name = "STAR-HAR"
    needs = HAR_FEATURES + _STAR_FEATURES

    # Expose the frozen transition spec + derived-column names for the card / tests.
    transition_variable = _STATE_COL
    transition_slope = _SLOPE
    transition_threshold = _THRESHOLD
    weight_col = _WEIGHT_COL
    interaction_cols = _INTERACT

    def _derive(self, src: pl.DataFrame) -> pl.DataFrame:
        return _star_panel(src)

    def _attach(self, X: pl.DataFrame) -> pl.DataFrame:
        # First join the leak-safe state + weight (built once on the full series), then form
        # the HAR x weight interaction columns from the HAR features present on X.
        Xj = super()._attach(X)
        return Xj.with_columns(
            *[(pl.col(f) * pl.col(_WEIGHT_COL)).alias(name)
              for f, name in zip(HAR_FEATURES, _INTERACT)]
        )
