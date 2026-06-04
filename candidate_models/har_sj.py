"""HAR-SJ — Signed-Jump HAR (ITER2_MODEL_CATALOG.md §3 model 14).

Patton-Sheppard (2015, "Good Volatility, Bad Volatility"): the *sign* of the jump
component carries information for future volatility beyond the raw realized
semivariances. Negative ("bad") jumps forecast higher future RV than positive
("good") jumps of equal magnitude. We capture this with a trailing *signed jump*
measure derived from the realized semivariances already in the inputs store:

    signed_jump_t = rs_plus_t - rs_minus_t          (good minus bad variation)
    sj_5d         = rolling_mean(signed_jump, 5)     (weekly signed-jump average)
    abs_sj_5d     = |sj_5d|                           (its magnitude)

The mean model is a HAR on log(target_var) using the realized-semivariance HAR
block (HAR_RS_FEATURES *minus* the unsigned `jump_5d`, which the signed terms
replace) plus the two derived signed-jump columns. Plain per-(ticker, horizon)
log-OLS via the inherited `_LinearLogHAR`; no free hyperparameters.

`rs_plus` / `rs_minus` live in `inputs.parquet` (per setup/measurement.py) and the
HAR_RS_FEATURES roll-means (`rs_plus_5d`, `rs_minus_5d`, `log_rv_*`) are produced by
`features.build_features`, so they are present on X at fit/predict untouched. The two
signed-jump roll-means are NOT in features.py — they are derived here on the FULL
series and joined by (ticker, date) via `_AttachMixin`, so the trailing window is
never (wrongly) recomputed on a one-month walk-forward slice.
"""

from __future__ import annotations

import polars as pl

from rv_eval.features import HAR_RS_FEATURES
from rv_eval.model_contract import _LinearLogHAR

from candidate_models._base_v2 import _AttachMixin, _KEYS

# Derived columns this model adds to X (trailing signed-jump + its magnitude).
_SJ_FEATURES = ["sj_5d", "abs_sj_5d"]
# HAR-RS block with the unsigned weekly jump dropped (the signed terms replace it).
_RS_BASE = [c for c in HAR_RS_FEATURES if c != "jump_5d"]


def _sj_panel(src: pl.DataFrame) -> pl.DataFrame:
    """Full-history weekly signed-jump average + its absolute value, per ticker.

    Mirrors how features.build_features computes its trailing HAR roll-means: the
    rolling mean is evaluated per ticker on the FULL point-in-time series (trailing,
    includes today, min_samples=5 so leading rows are null exactly as the other
    weekly features), so a given (ticker, date) always gets the same value regardless
    of which fold slice it later lands in -> no leakage.
    """
    return (
        src.sort("ticker", "date")
        .with_columns(
            sj_5d=(pl.col("rs_plus") - pl.col("rs_minus"))
            .rolling_mean(5, min_samples=5).over("ticker"),
        )
        .with_columns(abs_sj_5d=pl.col("sj_5d").abs())
        .select(_KEYS + _SJ_FEATURES)
    )


class HARSJ(_AttachMixin, _LinearLogHAR):
    name = "HAR-SJ"
    needs = _RS_BASE + _SJ_FEATURES

    def _derive(self, src: pl.DataFrame) -> pl.DataFrame:
        return _sj_panel(src)
