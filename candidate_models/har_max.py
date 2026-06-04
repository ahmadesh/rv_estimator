"""HAR-MAX — kitchen-sink OLS baseline (ITER2 catalog §3, model 18).

A **deliberately over-parameterised** plain log-OLS HAR. Its sole job is to be the
OLS-overfit yardstick that the Track-B shrinkage models (HAR-ENet / HAR-Ridge, model
19) must beat: it pours the *union of every Track-A derived block* (models 13–17) plus
the realized-semivariance HAR-RS block, the full IV feature group and `sqrt_rq` into a
single per-(ticker, horizon) ordinary-least-squares fit of `log(target_var)`. There is
NO regularization, NO cross-validation, NO hyperparameter tuning — that is the point.

Pattern P1 (linear-log HAR + derived join), built on `_LinearLogHAR` + `_AttachMixin`.
All trailing-window / shift / cross-tenor derived columns are computed ONCE on the full
point-in-time series from `inputs.parquet` and joined by (ticker, date) — never recomputed
on the one-month predict slice (which would null/mis-rank the leading rows). `_derive`
concatenates the five Track-A derivations, mirroring `har_cj.py::_cj_panel`.

Feature inventory (deduped, ~25 cols):

  Pass-through (already in X via build_features / inputs):
    HAR_RS_FEATURES = log_rv_d, log_rv_w, log_rv_m, rs_minus_5d, rs_plus_5d, jump_5d
    IV_FEATURES     = log_iv, iv_slope, skew_25d, vix, vix3m, vix_slope, vvix
    sqrt_rq, vix9d_slope

  Derived here (trailing windows on the full series, point-in-time):
    13 LHAR     : lev_d, lev_w, lev_m        (signed downside-return roll-means of ret_cc)
    14 HAR-SJ   : sj_5d, abs_sj_5d           (5d signed-jump = rs_plus-rs_minus, and |.|)
    15 HAR-IVTS : iv_curv, iv_ts_30_90, vrp_lag, vrp_mom
                                              (IV curvature/term-slope; VRP=iv_30d**2-total_rv,
                                               and its 5d momentum)
    16 HAR-Range: log_park_d, log_park_w, log_gk_d, log_gk_w   (log roll-means of parkinson/gk)
    17 HAR-Act  : log_vol_surprise, log_txn_surprise, overnight_share

VRP uses `iv_30d**2` (point-in-time, present in X) — NOT `targets.iv2`, which predict()
never sees (catalog §4). The "market factor" / SPX-RV concerns of model 24 do not apply
here. Logs are floored at 1e-12 exactly as features.py / har_cj.py do (parkinson, gk,
volume, transactions can be 0 on a thin session).
"""

from __future__ import annotations

import polars as pl

from rv_eval import config as C
from rv_eval.features import HAR_RS_FEATURES, IV_FEATURES
from rv_eval.model_contract import _LinearLogHAR

from candidate_models._base_v2 import _AttachMixin

_KEYS = ["ticker", "date"]
_FLOOR = 1e-12  # matches features.py / har_cj.py log-floor; raw measures can be exactly 0.

# --- derived blocks (union of Track-A models 13-17) ------------------------
_LEV = ["lev_d", "lev_w", "lev_m"]                                  # 13 LHAR
_SJ = ["sj_5d", "abs_sj_5d"]                                        # 14 HAR-SJ
_IVTS = ["iv_curv", "iv_ts_30_90", "vrp_lag", "vrp_mom"]           # 15 HAR-IVTS
_RANGE = ["log_park_d", "log_park_w", "log_gk_d", "log_gk_w"]      # 16 HAR-Range
_ACT = ["log_vol_surprise", "log_txn_surprise", "overnight_share"]  # 17 HAR-Act

_DERIVED = _LEV + _SJ + _IVTS + _RANGE + _ACT

# Pass-through columns: realized-semivariance HAR block + full IV block + sqrt_rq +
# the systematic vix9d_slope (already in X; referenced by raw name per catalog §1/§4).
_PASSTHROUGH = HAR_RS_FEATURES + IV_FEATURES + ["sqrt_rq", "vix9d_slope"]


def _max_panel(src: pl.DataFrame) -> pl.DataFrame:
    """Build all Track-A derived columns once on the FULL point-in-time series.

    Every window is trailing (includes today) and computed per ticker over the whole
    series, so a given (ticker, date) gets the same value regardless of which fold slice
    it later lands in — no leakage, no null leading rows on the predict slice. Mirrors
    `features.build_features` (min_samples=w for week/month means) and `har_cj.py`.
    """
    return (
        src.sort("ticker", "date")
        .with_columns(
            # 13 LHAR — signed downside-return aggregates (Corsi-Renò 2012).
            _neg_ret=pl.min_horizontal("ret_cc", pl.lit(0.0)),
            # 14 HAR-SJ — daily signed-jump proxy (Patton-Sheppard 2015).
            _sj_daily=(pl.col("rs_plus") - pl.col("rs_minus")),
            # 15 HAR-IVTS — IV term-structure curvature / slope; point-in-time VRP.
            iv_curv=(pl.col("iv_30d") - 2.0 * pl.col("iv_60d") + pl.col("iv_90d")),
            iv_ts_30_90=(pl.col("iv_90d") - pl.col("iv_30d")),
            vrp_lag=(pl.col("iv_30d") ** 2 - pl.col("total_rv")),
        )
        .with_columns(
            lev_d=pl.col("_neg_ret").rolling_mean(1, min_samples=1).over("ticker"),
            lev_w=pl.col("_neg_ret").rolling_mean(5, min_samples=5).over("ticker"),
            lev_m=pl.col("_neg_ret").rolling_mean(22, min_samples=22).over("ticker"),
            sj_5d=pl.col("_sj_daily").rolling_mean(5, min_samples=5).over("ticker"),
            # 16 HAR-Range — log roll-means of Parkinson / Garman-Klass (Yang-Zhang).
            log_park_d=pl.col("parkinson").rolling_mean(1, min_samples=1).over("ticker")
            .clip(lower_bound=_FLOOR).log(),
            log_park_w=pl.col("parkinson").rolling_mean(5, min_samples=5).over("ticker")
            .clip(lower_bound=_FLOOR).log(),
            log_gk_d=pl.col("gk").rolling_mean(1, min_samples=1).over("ticker")
            .clip(lower_bound=_FLOOR).log(),
            log_gk_w=pl.col("gk").rolling_mean(5, min_samples=5).over("ticker")
            .clip(lower_bound=_FLOOR).log(),
            # 17 HAR-Act — activity surprises + overnight share (Bollerslev).
            log_vol_surprise=(
                pl.col("volume").clip(lower_bound=_FLOOR).log()
                - pl.col("volume").rolling_mean(22, min_samples=22).over("ticker")
                .clip(lower_bound=_FLOOR).log()
            ),
            log_txn_surprise=(
                pl.col("transactions").clip(lower_bound=_FLOOR).log()
                - pl.col("transactions").rolling_mean(22, min_samples=22).over("ticker")
                .clip(lower_bound=_FLOOR).log()
            ),
            overnight_share=pl.col("rv_overnight") / pl.col("total_rv"),
        )
        .with_columns(
            abs_sj_5d=pl.col("sj_5d").abs(),
            # 15 VRP momentum — change in the point-in-time VRP over 5 trading days.
            vrp_mom=(pl.col("vrp_lag") - pl.col("vrp_lag").shift(5).over("ticker")),
        )
        .select(_KEYS + _DERIVED)
    )


class HARMAX(_AttachMixin, _LinearLogHAR):
    """Kitchen-sink HAR: plain log-OLS over the union of all Track-A blocks (no shrinkage)."""

    name = "HAR-MAX"
    needs = _PASSTHROUGH + _DERIVED

    def _derive(self, src: pl.DataFrame) -> pl.DataFrame:
        return _max_panel(src)
