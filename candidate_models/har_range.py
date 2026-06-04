"""HAR-Range — HAR augmented with log range-based volatility estimators (model 16).

Range-based variance estimators (Parkinson 1980; Garman-Klass 1980; and the
Yang-Zhang / Rogers-Satchell family) extract information from the intraday
high/low/open/close that 5-minute realized variance misses, and they are far
less noisy than squared close-to-close returns. Following the Yang-Zhang line of
work, we augment the standard HAR lags of total RV (`HAR_FEATURES`) with daily
and weekly trailing means of the Parkinson and Garman-Klass estimators, in log
space (variance is multiplicative / right-skewed; log stabilises the OLS exactly
as `features.py` does for its HAR lags). Plain log-OLS, no free hyperparameters:
the inherited `_LinearLogHAR` does per-(ticker, horizon) OLS and emits lognormal
quantiles consistently with the benchmarks.

`parkinson`, `gk`, `rs` already live in `inputs.parquet` (per setup/measurement.py)
and survive `features.build_features` untouched, so the raw estimators are present
on X. The four derived log roll-means (w in {1, 5}; w=1 is just log of the daily
estimator) are NOT in `features.py` — they are derived here via the `_AttachMixin`
join pattern (built once on the full series, joined by (ticker, date)), leaving
`features.py` and the rest of `rv_eval/` untouched.

THE rolling-feature rule: the walk-forward hands `predict` only a one-month test
slice, so a `rolling_mean(5)` computed *inside* predict would be null/mis-ranked
for its leading rows. `_AttachMixin` builds the trailing windows once on the full
`inputs.parquet` series (with the synthetic-X fallback for the smoke test) and
joins by (ticker, date). Parkinson/GK can be exactly 0 (e.g. a flat session, or
the 15 / 333 zero rows observed in inputs) so they are floored before log, the
same way `features.py` / `har_cj.py` floor their logs.
"""

from __future__ import annotations

import polars as pl

from rv_eval.features import HAR_FEATURES
from rv_eval.model_contract import _LinearLogHAR

from candidate_models._base_v2 import _AttachMixin

# Derived columns this model adds to X (log trailing means of the range estimators).
_RANGE_FEATURES = ["log_park_d", "log_park_w", "log_gk_d", "log_gk_w"]
_FLOOR = 1e-12  # matches features.py / har_cj.py log-floor; parkinson/gk can be exactly 0.
_KEYS = ["ticker", "date"]


def _range_panel(inputs: pl.DataFrame) -> pl.DataFrame:
    """Build full-history day/week log trailing means of Parkinson & Garman-Klass.

    Mirrors how `features.build_features` computes its trailing HAR roll-means: the
    rolling means are evaluated per ticker on the FULL point-in-time series, so a
    given (ticker, date) always gets the same value regardless of which fold slice
    it later lands in. Windows are trailing (include today) so every value uses
    only at-or-before-date rows -> no leakage. w=1 (`*_d`) is the plain log of the
    daily estimator (rolling_mean of window 1).
    """
    return (
        inputs.sort("ticker", "date")
        .with_columns(
            log_park_d=pl.col("parkinson").rolling_mean(1, min_samples=1).over("ticker")
            .clip(lower_bound=_FLOOR).log(),
            log_park_w=pl.col("parkinson").rolling_mean(5, min_samples=5).over("ticker")
            .clip(lower_bound=_FLOOR).log(),
            log_gk_d=pl.col("gk").rolling_mean(1, min_samples=1).over("ticker")
            .clip(lower_bound=_FLOOR).log(),
            log_gk_w=pl.col("gk").rolling_mean(5, min_samples=5).over("ticker")
            .clip(lower_bound=_FLOOR).log(),
        )
        .select(_KEYS + _RANGE_FEATURES)
    )


class HARRange(_AttachMixin, _LinearLogHAR):
    name = "HAR-Range"
    needs = HAR_FEATURES + _RANGE_FEATURES

    def _derive(self, src: pl.DataFrame) -> pl.DataFrame:
        """Full-history range-estimator table; cached + joined by `_AttachMixin`."""
        return _range_panel(src)
