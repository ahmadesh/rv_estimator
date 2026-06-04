"""HAR-Act — HAR augmented with trading-activity / overnight features (model 17).

Trading activity carries volatility information that the RV path alone misses
(Bollerslev et al., "Risk Everywhere"): an abnormal volume / transaction-count
day signals an information shock that tends to persist into future variance, and
the share of variance accrued *overnight* (gap risk) is its own slow-moving state
variable. Following that line of work we augment the standard HAR lags of total
RV (`HAR_FEATURES`) with two activity-*surprise* terms and the overnight variance
share. Plain log-OLS, no free hyperparameters: the inherited `_LinearLogHAR` does
per-(ticker, horizon) OLS and emits lognormal quantiles consistently with the
benchmarks.

Derived columns (all built from inputs.parquet base columns):

  log_vol_surprise = log(volume) - log(rolling_mean(volume, 22))      # log volume vs trailing 22d mean
  log_txn_surprise = log(transactions) - log(rolling_mean(transactions, 22))   # same for trade count
  overnight_share  = rv_overnight / total_rv                          # fraction of variance from the gap

`volume`, `transactions`, `rv_overnight`, `total_rv` all live in `inputs.parquet`
(per setup/measurement.py) and survive `features.build_features` untouched, so the
raw columns are present on X. The three derived columns are NOT in `features.py` —
they are derived here via the `_AttachMixin` join pattern (built ONCE on the full
series, joined by (ticker, date)), leaving `features.py` and the rest of `rv_eval/`
untouched.

THE rolling-feature rule: the trailing 22d activity means are the leakage risk.
The walk-forward hands `predict` only a one-month test slice, so a
`rolling_mean(22)` computed *inside* predict would be null/mis-ranked for its
leading 21 rows. `_AttachMixin` builds the trailing windows once on the full
`inputs.parquet` series (with the synthetic-X fallback for the smoke test) and
joins by (ticker, date), so every (ticker, date) gets the same point-in-time value
regardless of which fold slice it lands in. The 22d windows are trailing (include
today) so every value uses only at-or-before-date rows -> no leakage.

Floors / guards (matching features.py / har_cj.py log-flooring conventions):
  - volume (min 100) and transactions (min 1) are strictly positive in inputs, but
    are floored before log anyway for robustness on arbitrary slices.
  - rv_overnight can be 0 or null (911 zero, 15 null rows in inputs) and total_rv
    can be 0 (4 rows): overnight_share is computed safely (null when total_rv<=0)
    and the leading null is left for the join (rows with null features are dropped
    by the base fit's drop_nulls, mirroring the other HAR models).
"""

from __future__ import annotations

import polars as pl

from rv_eval.features import HAR_FEATURES
from rv_eval.model_contract import _LinearLogHAR

from candidate_models._base_v2 import _AttachMixin

# Derived columns this model adds to X (activity surprise + overnight share).
_ACT_FEATURES = ["log_vol_surprise", "log_txn_surprise", "overnight_share"]
_FLOOR = 1e-12  # matches features.py / har_cj.py log-floor.
_ACT_WINDOW = 22  # trailing month of activity for the surprise baseline.
_KEYS = ["ticker", "date"]


def _act_panel(inputs: pl.DataFrame) -> pl.DataFrame:
    """Build full-history activity-surprise + overnight-share table.

    Mirrors how `features.build_features` computes its trailing HAR roll-means: the
    rolling means are evaluated per ticker on the FULL point-in-time series, so a
    given (ticker, date) always gets the same value regardless of which fold slice
    it later lands in. The 22d windows are trailing (include today) so every value
    uses only at-or-before-date rows -> no leakage.

    Surprise = log(level) - log(trailing 22d mean of the level). The mean is
    computed on the raw (un-logged) level then logged, i.e. a *ratio* in log space
    (log of today's activity over its trailing average), which is the standard
    activity-surprise construction.
    """
    volume = pl.col("volume").clip(lower_bound=_FLOOR)
    txn = pl.col("transactions").cast(pl.Float64).clip(lower_bound=_FLOOR)
    return (
        inputs.sort("ticker", "date")
        .with_columns(
            log_vol_surprise=(
                volume.log()
                - pl.col("volume").rolling_mean(_ACT_WINDOW, min_samples=_ACT_WINDOW)
                .over("ticker").clip(lower_bound=_FLOOR).log()
            ),
            log_txn_surprise=(
                txn.log()
                - pl.col("transactions").cast(pl.Float64)
                .rolling_mean(_ACT_WINDOW, min_samples=_ACT_WINDOW)
                .over("ticker").clip(lower_bound=_FLOOR).log()
            ),
            # Overnight variance share; null where total_rv is non-positive (gap is
            # undefined) so the base fit drops those rows the same as any null feature.
            overnight_share=pl.when(pl.col("total_rv") > 0)
            .then(pl.col("rv_overnight") / pl.col("total_rv"))
            .otherwise(None),
        )
        .select(_KEYS + _ACT_FEATURES)
    )


class HARAct(_AttachMixin, _LinearLogHAR):
    name = "HAR-Act"
    needs = HAR_FEATURES + _ACT_FEATURES

    def _derive(self, src: pl.DataFrame) -> pl.DataFrame:
        """Full-history activity table; cached + joined by `_AttachMixin`."""
        return _act_panel(src)
