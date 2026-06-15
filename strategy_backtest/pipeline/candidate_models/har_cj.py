"""HAR-CJ — Continuous + Jump decomposition (MODEL_PLAN.md §4 model 6).

Andersen-Bollerslev-Diebold (2007) HAR-CJ: decompose total RV into a continuous
component (proxied by bipower variation, BV) and a jump component, on the theory
that the continuous part is far more persistent than jumps. We regress
log(target_var) on the standard HAR lags of total RV (`HAR_FEATURES`) *plus*
day/week/month log-BV roll-means (continuous persistence) and a daily log-jump
term. Plain log-OLS, no free hyperparameters — the inherited `_LinearLogHAR`
machinery does per-(ticker, horizon) OLS and generates lognormal quantiles
consistently with the benchmarks.

`bv` and `jump` live in `inputs.parquet` (per setup/measurement.py) and survive
`features.build_features` untouched, so they are present on X at fit/predict. The
three log-BV roll-means (w in {1,5,22}; w=1 is just log(bv)) and the daily
log-jump are NOT in features.py — they are derived here, leaving features.py
untouched. BV/jump are floored before log (they can be exactly 0: e.g. a session
with no detected jump gives jump==0) the same way features.py floors its logs.
"""

from __future__ import annotations

import polars as pl

from strategy_backtest.pipeline import config as C
from strategy_backtest.pipeline.features import HAR_FEATURES
from strategy_backtest.pipeline.model_contract import _LinearLogHAR

# Derived columns this model adds to X (continuous-component + jump decomposition).
_CJ_FEATURES = ["log_bv_d", "log_bv_w", "log_bv_m", "log_jump_d"]
_FLOOR = 1e-12  # matches features.py log-floor; BV/jump can be exactly 0.
_KEYS = ["ticker", "date"]


def _cj_panel(inputs: pl.DataFrame) -> pl.DataFrame:
    """Build the full-history day/week/month log-BV roll-means + daily log-jump.

    Mirrors how features.build_features computes its trailing HAR roll-means: the
    rolling means are evaluated per ticker on the FULL point-in-time series, so a
    given (ticker, date) always gets the same value regardless of which fold slice
    it later lands in. Windows are trailing (include today) so every value uses
    only at-or-before-date rows -> no leakage. w=1 is plain log(bv).
    """
    return (
        inputs.sort("ticker", "date")
        .with_columns(
            log_bv_d=pl.col("bv").rolling_mean(1, min_samples=1).over("ticker")
            .clip(lower_bound=_FLOOR).log(),
            log_bv_w=pl.col("bv").rolling_mean(5, min_samples=5).over("ticker")
            .clip(lower_bound=_FLOOR).log(),
            log_bv_m=pl.col("bv").rolling_mean(22, min_samples=22).over("ticker")
            .clip(lower_bound=_FLOOR).log(),
            log_jump_d=pl.col("jump").clip(lower_bound=_FLOOR).log(),
        )
        .select(_KEYS + _CJ_FEATURES)
    )


class HARCJ(_LinearLogHAR):
    name = "HAR-CJ"
    needs = HAR_FEATURES + _CJ_FEATURES

    _cj: pl.DataFrame | None = None  # lazily-built full-history CJ table (cached on the instance)

    def _full_cj(self) -> pl.DataFrame:
        """Full-history CJ table from inputs.parquet, built once and cached."""
        if self._cj is None:
            self._cj = _cj_panel(pl.read_parquet(C.INPUTS_PARQUET))
        return self._cj

    def _attach(self, X: pl.DataFrame) -> pl.DataFrame:
        """Inject the derived CJ columns into X by joining the full-history table.

        Joining (not recomputing on the slice) is what keeps the roll-means correct:
        the walk-forward hands fit/predict only a train- or one-month-test slice, so a
        rolling_mean computed on that slice alone would be null for its leading 21 rows.
        We instead compute the roll-means once over each ticker's whole series and join
        by (ticker, date). If X carries (ticker, date) keys absent from inputs.parquet
        (the synthetic smoke test), fall back to building the table straight from X,
        which there IS the full series.
        """
        cj = self._full_cj()
        keys = X.select(_KEYS).unique()
        covered = keys.join(cj.select(_KEYS), on=_KEYS, how="inner").height
        if covered < keys.height:
            cj = _cj_panel(X)
        return X.join(cj, on=_KEYS, how="left")

    def fit(self, X: pl.DataFrame, y: pl.DataFrame) -> None:
        super().fit(self._attach(X), y)

    def predict(self, X: pl.DataFrame) -> pl.DataFrame:
        return super().predict(self._attach(X))
