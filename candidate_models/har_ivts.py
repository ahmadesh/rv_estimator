"""HAR-IVTS — IV term structure + variance-risk-premium (VRP) state.

Iteration-2 model 15 (ITER2_MODEL_CATALOG.md §3, Track A / Pattern P1). A linear-log
HAR augmented with the option-implied **term structure** and a point-in-time **VRP**
state that directly encodes the variance-risk-premium mean-reversion documented for the
VIX term structure -> RV link (S1057521922001600).

Derived columns (built once on the FULL series, joined by (ticker, date) so the
walk-forward's one-month predict slice never recomputes a trailing window):

  iv_curv     = iv_30d - 2*iv_60d + iv_90d          # curvature of the IV term structure
  iv_ts_30_90 = iv_90d - iv_30d                      # 30->90 IV slope (contango/backwardation)
  vrp_lag     = iv_30d**2 - total_rv                 # point-in-time VRP proxy (level space)
  vrp_mom     = vrp_lag - vrp_lag.shift(5)           # 5d VRP momentum (per ticker)

`vrp_lag` uses **iv_30d²** (in X), NOT `targets.iv2` (which is in targets.parquet and so
never reaches predict — see CATALOG §4 discrepancy 2). `iv_curv`/`iv_ts_30_90` are pure
point-in-time transforms of three X columns (no window), and `vrp_lag` is point-in-time
too, but `vrp_mom` is a 5-row trailing shift, so the whole block is built on the full
series and joined — the same join discipline as har_cj.py::_attach, packaged by
`_AttachMixin`. `vix9d_slope` is already in X (a systematic regime column passed straight
through build_features) and is added to `needs` by raw name.

Plain log-OLS, no free hyperparameters — `_LinearLogHAR` does per-(ticker, horizon) OLS
of log(target_var) and emits lognormal quantiles consistently with the benchmarks.
"""

from __future__ import annotations

import polars as pl

from candidate_models._base_v2 import _AttachMixin
from rv_eval.features import HAR_FEATURES, IV_FEATURES
from rv_eval.model_contract import _LinearLogHAR

_KEYS = ["ticker", "date"]
# Derived IV-term-structure + VRP-state columns this model adds to X.
_IVTS_FEATURES = ["iv_curv", "iv_ts_30_90", "vrp_lag", "vrp_mom"]


class HARIVTS(_AttachMixin, _LinearLogHAR):
    name = "HAR-IVTS"
    # HAR lags + the X IV block + derived term-structure/VRP cols + the systematic
    # term-slope regime (vix9d_slope arrives in X via build_features, raw name).
    needs = HAR_FEATURES + IV_FEATURES + _IVTS_FEATURES + ["vix9d_slope"]

    def _derive(self, src: pl.DataFrame) -> pl.DataFrame:
        """Full-history IV-term-structure + VRP-state table, joined by (ticker, date).

        iv_curv / iv_ts_30_90 / vrp_lag are point-in-time (no window); vrp_mom is a 5-row
        trailing shift per ticker, so it is computed here on each ticker's whole series and
        joined, never recomputed on a fold slice (which would null its leading 5 rows).
        """
        return (
            src.sort("ticker", "date")
            .with_columns(
                iv_curv=pl.col("iv_30d") - 2.0 * pl.col("iv_60d") + pl.col("iv_90d"),
                iv_ts_30_90=pl.col("iv_90d") - pl.col("iv_30d"),
                vrp_lag=pl.col("iv_30d") ** 2 - pl.col("total_rv"),
            )
            .with_columns(
                vrp_mom=pl.col("vrp_lag") - pl.col("vrp_lag").shift(5).over("ticker"),
            )
            .select(_KEYS + _IVTS_FEATURES)
        )
