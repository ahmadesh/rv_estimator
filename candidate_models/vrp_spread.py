"""Model 28 — VRP-Spread head (ITER2_MODEL_CATALOG §3, Track D, Pattern P3).

A DIRECT-QUANTILE model. Instead of forecasting realized variance directly, it
forecasts the **variance-risk-premium spread**

    s_h = iv2_h - rv_h        with   iv2_h = iv_30d**2 * (h / 252)

— the gap between the (point-in-time, in-X) implied variance for horizon `h` and the
realized variance over the next `h` days (`target_var`). The spread mean-reverts, so a
HAR-style level OLS on trailing spread aggregates + IV-curve / regime state predicts
`ŝ_h`, and the variance forecast is recovered by

    rv_hat = max(iv2_h - ŝ_h, floor).

`iv2_h` reproduces `targets.iv2` exactly (rel-err 0, corr 1 — verified), but is built
from `iv_30d` which IS in X, so `predict` never touches the targets table (§4 leakage
note). The spread can be negative, so the mean is fit in **level** space (OLS), never log.

Quantiles are emitted **directly** (this BYPASSES `_lognormal_quantiles`): empirical
quantiles of the level-space spread residual are added to `ŝ_h`, then mapped back through
`rv = iv2_h - s`. Because that map flips the ordering, the rv-quantile grid is re-sorted to
be non-decreasing (the `_QuantileModel` base does `maximum.accumulate`), every rv-quantile
and `rv_hat` is floored to a tiny positive value, and `sigma` is the (positive) level
residual sd of the spread — a sensible dispersion proxy for downstream sizing.

Derived trailing features (`_derive`, built ONCE on the full inputs series and joined by
(ticker, date) — never recomputed on the one-month predict slice):
  vrp_d/w/m  — HAR-style trailing means of the daily VRP proxy iv_30d**2/252 - total_rv.
Curve / regime features come from X directly (point-in-time, no derivation needed):
  iv_curv = iv_30d - 2*iv_60d + iv_90d ; iv_ts_30_90 = iv_90d - iv_30d ; vix9d_slope.
"""

from __future__ import annotations

import numpy as np
import polars as pl

from rv_eval import config as C
from rv_eval.model_contract import Q_COLS

from candidate_models._base_v2 import _AttachMixin, _QuantileModel

_KEYS = ["ticker", "date"]
_FLOOR = 1e-12                      # absolute positive floor for rv_hat / rv quantiles
_ANNUAL = float(C.TRADING_DAYS_PER_YEAR)

# Scale-aware clamp anchors (frozen by construction, leakage-safe; see _predict_q):
#   rv_hat / rv quantiles are clipped into [FLOOR_FRAC*p05(train target_var),
#                                           CAP_MULT*max(iv2_h, p95(train target_var))].
# FLOOR_FRAC stops an over-shooting spread (ŝ -> iv2) from collapsing rv_hat to ~0 (which
# would explode QLIKE); CAP_MULT caps the rare absurd upside. Conservative defaults — NOT
# tuned against OOS.
FLOOR_FRAC = 0.25
CAP_MULT = 4.0

# Trailing daily-VRP HAR aggregates this model derives and joins into X.
_VRP_FEATURES = ["vrp_d", "vrp_w", "vrp_m"]
# Raw IV term-structure / regime columns (in X) the design block reads point-in-time.
_RAW_STATE = ["iv_30d", "iv_60d", "iv_90d", "vix9d_slope"]
# IV-curve / term-slope regressors BUILT inside _design from the raw IV tenors (not in X,
# so deliberately NOT in `needs` — `needs` gates the drop_nulls and must list X columns only).
_STATE_FEATURES = ["iv_curv", "iv_ts_30_90", "vix9d_slope"]
# `needs` (non-null gate at fit/predict): the joined VRP cols + raw X columns only.
NEEDS = _VRP_FEATURES + _RAW_STATE


def _vrp_panel(inputs: pl.DataFrame) -> pl.DataFrame:
    """HAR-style trailing means of the daily VRP proxy, point-in-time on the full series.

    The daily VRP proxy is iv_30d**2 * (1/252) - total_rv: the one-day implied variance
    minus realized daily variance. Trailing means over {1,5,22} days mirror how
    `features.build_features` / `har_cj.py::_cj_panel` build their HAR roll-means — each
    (ticker, date) gets a value depending only on at-or-before-date rows, so the result is
    identical regardless of which fold slice the row later lands in (no leakage).
    """
    return (
        inputs.sort("ticker", "date")
        .with_columns(_vrp_d=(pl.col("iv_30d") ** 2) / _ANNUAL - pl.col("total_rv"))
        .with_columns(
            vrp_d=pl.col("_vrp_d").rolling_mean(1, min_samples=1).over("ticker"),
            vrp_w=pl.col("_vrp_d").rolling_mean(5, min_samples=5).over("ticker"),
            vrp_m=pl.col("_vrp_d").rolling_mean(22, min_samples=22).over("ticker"),
        )
        .select(_KEYS + _VRP_FEATURES)
    )


class VRPSpread(_AttachMixin, _QuantileModel):
    """VRP-spread head: level-OLS mean-reversion on the spread, direct quantiles.

    `_AttachMixin` joins the derived `vrp_d/w/m` columns; `_QuantileModel` drives the
    per-(ticker, horizon) fit/predict loop and enforces monotone quantiles. The fit is
    LEVEL OLS (not log) because the spread can be negative.
    """

    name = "VRP-Spread"
    needs = NEEDS
    min_obs = 100                  # need a stable level-OLS + residual-quantile grid

    # --- derived-feature hook (built once on full series, joined by key) ----------------
    def _derive(self, src: pl.DataFrame) -> pl.DataFrame:
        return _vrp_panel(src)

    # --- helpers ------------------------------------------------------------------------
    @staticmethod
    def _iv2(sub: pl.DataFrame, h: int) -> np.ndarray:
        """Point-in-time implied variance for horizon h in target_var (h-day-sum) units."""
        iv = sub["iv_30d"].to_numpy().astype(float)
        return iv * iv * (h / _ANNUAL)

    def _design(self, sub: pl.DataFrame) -> np.ndarray:
        # iv_curv and iv_ts are built point-in-time from the IV term structure already in X.
        feat = sub.with_columns(
            iv_curv=pl.col("iv_30d") - 2.0 * pl.col("iv_60d") + pl.col("iv_90d"),
            iv_ts_30_90=pl.col("iv_90d") - pl.col("iv_30d"),
        ).select(_VRP_FEATURES + _STATE_FEATURES).to_numpy().astype(float)
        return np.column_stack([np.ones(feat.shape[0]), feat])

    # --- per-(ticker, horizon) fit ------------------------------------------------------
    def _fit_one(self, sub: pl.DataFrame, h: int):
        A = self._design(sub)
        iv2 = self._iv2(sub, h)
        tv = sub["target_var"].to_numpy().astype(float)
        spread = iv2 - tv                                          # level space, may be < 0
        beta, *_ = np.linalg.lstsq(A, spread, rcond=None)
        resid = spread - A @ beta
        # Empirical residual quantiles for the DIRECT spread-quantile grid (level space).
        qlev = np.quantile(resid, C.QUANTILES) if resid.size > A.shape[1] else np.zeros(len(C.QUANTILES))
        s = float(np.std(resid, ddof=A.shape[1])) if resid.size > A.shape[1] else 0.5
        # In-sample target_var scale anchors. The recovered rv = iv2 - ŝ is clamped into
        # [lo, hi] at predict so an over-shooting spread can't drive rv_hat to the 1e-12 floor
        # (which would explode QLIKE) nor balloon it. Anchors are frozen by CONSTRUCTION from
        # the TRAIN slice only (FLOOR_FRAC/CAP_MULT below) — no OOS peeking, no inner CV.
        lo = float(np.quantile(tv, 0.05))
        hi = float(np.quantile(tv, 0.95))
        return beta, qlev, max(s, 1e-9), max(lo, _FLOOR), max(hi, _FLOOR)

    # --- per-(ticker, horizon) predict (direct quantiles) -------------------------------
    def _predict_q(self, state, sub: pl.DataFrame, h: int):
        beta, qlev, s, tv_lo, tv_hi = state
        iv2 = self._iv2(sub, h)
        s_hat = self._design(sub) @ beta                  # ŝ_h ; NaN propagates where feature null

        # Scale-aware bounds for the recovered variance forecast. Realized variance is
        # non-negative (so the spread cannot exceed iv2), and rarely exceeds a few × the
        # point-in-time implied variance; the lower anchor keeps a collapsing spread from
        # producing a near-zero rv_hat that would blow up QLIKE.
        lo = np.full(sub.height, FLOOR_FRAC * tv_lo)
        hi = np.maximum(CAP_MULT * iv2, CAP_MULT * tv_hi)

        def _clamp(x):
            return np.clip(x, lo, hi)

        rv_hat = _clamp(iv2 - s_hat)
        # Spread quantiles -> rv quantiles. rv = iv2 - spread FLIPS the ordering, so the
        # p-th spread quantile is the (1-p)-th rv quantile. The QUANTILES grid is symmetric
        # about 0.5, so mapping rv-column i to the REVERSED spread-residual quantile (qlev[-1-i])
        # yields a correctly non-decreasing rv-quantile grid (q05<=...<=q95). nq = len(QUANTILES).
        nq = len(qlev)
        q = {col: _clamp(iv2 - (s_hat + qlev[nq - 1 - i])) for i, col in enumerate(Q_COLS)}
        # sigma: positive spread dispersion proxy (level residual sd), broadcast per row.
        sigma = np.full(sub.height, s, dtype=float)
        return rv_hat, sigma, q
