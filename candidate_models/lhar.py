"""LHAR — Leverage-HAR (ITER2 catalog §3, model 13).

Corsi-Renò (2012) leverage HAR: realized volatility responds asymmetrically to
the sign of past returns — negative returns ("bad news") raise future volatility
more than positive returns of the same magnitude (the leverage effect). We
augment the standard log-HAR (`HAR_FEATURES`) with day/week/month trailing means
of the *signed downside return* `min(ret_cc, 0)`:

    lev_d = rolling_mean(min(ret_cc,0), 1)   # today's downside return (=min(ret_cc,0))
    lev_w = rolling_mean(min(ret_cc,0), 5)    # weekly downside-return aggregate
    lev_m = rolling_mean(min(ret_cc,0), 22)   # monthly downside-return aggregate

These are signed (<= 0) regressors; a more-negative value (a recent drawdown)
pushes the log-RV forecast up via a negative OLS coefficient. Plain log-OLS, no
free hyperparameters — the inherited `_LinearLogHAR` machinery does per-(ticker,
horizon) OLS and generates lognormal quantiles consistently with the benchmarks.

`ret_cc` (close-to-close log return) lives in `inputs.parquet` and survives
`features.build_features` untouched, so it is present on X. The three downside
roll-means are NOT in features.py — they are derived here on the FULL series and
joined by (ticker, date) via `_AttachMixin`, leaving features.py untouched and
avoiding the predict-slice rolling-window leakage trap.
"""

from __future__ import annotations

import polars as pl

from rv_eval.features import HAR_FEATURES
from rv_eval.model_contract import _LinearLogHAR

from candidate_models._base_v2 import _AttachMixin

# Derived columns this model adds to X (signed downside-return aggregates).
_LEV_FEATURES = ["lev_d", "lev_w", "lev_m"]
_KEYS = ["ticker", "date"]


def _lev_panel(src: pl.DataFrame) -> pl.DataFrame:
    """Full-history day/week/month means of the signed downside return.

    Mirrors how features.build_features computes its trailing HAR roll-means: the
    rolling means are evaluated per ticker on the FULL point-in-time series, so a
    given (ticker, date) always gets the same value regardless of which fold slice
    it later lands in. Windows are trailing (include today) so every value uses
    only at-or-before-date rows -> no leakage. w=1 is just min(ret_cc, 0).
    """
    down = pl.min_horizontal(pl.col("ret_cc"), pl.lit(0.0))
    return (
        src.sort("ticker", "date")
        .with_columns(_down=down)
        .with_columns(
            lev_d=pl.col("_down").rolling_mean(1, min_samples=1).over("ticker"),
            lev_w=pl.col("_down").rolling_mean(5, min_samples=5).over("ticker"),
            lev_m=pl.col("_down").rolling_mean(22, min_samples=22).over("ticker"),
        )
        .select(_KEYS + _LEV_FEATURES)
    )


class LHAR(_AttachMixin, _LinearLogHAR):
    name = "LHAR"
    needs = HAR_FEATURES + _LEV_FEATURES

    def _derive(self, src: pl.DataFrame) -> pl.DataFrame:
        return _lev_panel(src)
