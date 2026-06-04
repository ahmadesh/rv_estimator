"""HAR-ENet / HAR-Ridge — shrinkage HAR on the kitchen-sink feature matrix.

Iteration-2 model 19 (ITER2_MODEL_CATALOG.md §3, Track B / Pattern P2 over `_AttachMixin`).
Two classes share this file:

  HARENet  · name="HAR-ENet"  · ElasticNetCV  (priority)
  HARRidge · name="HAR-Ridge" · RidgeCV

Both fit per-(ticker, horizon) a *penalised* log-OLS of `log(target_var)` on the SAME wide
feature matrix as HAR-MAX (model 18): the union of the Track-A 13-17 derived blocks plus
`HAR_RS_FEATURES + IV_FEATURES + ["sqrt_rq"]`, deduped. HAR-MAX is the deliberately
over-parameterised OLS baseline; these two are its shrinkage counterparts whose job is to
beat it out-of-sample by regularising the (~25-feature) design.

Reference: shrinkage-HAR (Elsevier S105905602400306X, 2024).

== Feature matrix (same as model 18) ==
- Track 13 (leverage)   : lev_d, lev_w, lev_m            = rolling_mean(min(ret_cc,0),{1,5,22})
- Track 14 (signed jump): sj_5d, abs_sj_5d               = rolling_mean(rs_plus-rs_minus,5), |.|
- Track 15 (IV-TS / VRP): iv_curv, iv_ts_30_90, vrp_lag, vrp_mom
- Track 16 (range)      : log_park_d/w, log_gk_d/w       = log(rolling_mean(parkinson/gk,{1,5}))
- Track 17 (activity)   : log_vol_surprise, log_txn_surprise, overnight_share
- plus HAR_RS_FEATURES + IV_FEATURES + ["sqrt_rq"] (all produced by build_features, in X)

All rolling/shift derivations are computed ONCE on the FULL series from inputs.parquet and
JOINED by (ticker, date) via `_AttachMixin._derive`, never recomputed on the one-month
predict slice (which would null leading rows / mis-rank windows). `vrp_lag` uses `iv_30d**2`
(in X), NOT `targets.iv2` (CATALOG §4 discrepancy 2). `overnight_share` = rv_overnight/total_rv
is point-in-time. The systematic regime cols (vix9d_slope etc.) flow through build_features; we
do not add them to `needs` here (HAR-MAX's column list does not include them — §3 entry 18).

== Hyperparameter discipline (this is a shrinkage model) ==
The penalty strength is chosen by a TIME-ORDERED inner cross-validation on the TRAIN slice
ONLY (sklearn `TimeSeriesSplit`, n_splits=5), never by peeking at OOS rows or other models'
results. Features are standardised inside the fit (mean/sd stored from the train slice and
re-applied at predict). `sigma` is the in-sample log-residual std of the fitted model. The
selected alpha / l1_ratio per (ticker, horizon) is recorded on `self.warnings` for the card.

  HAR-ENet : ElasticNetCV(l1_ratio in {.1,.3,.5,.7,.9,.95,.99,1.0}, 50-pt alpha path, cv=TSS5)
  HAR-Ridge: RidgeCV(alpha logspace(-3,3,25), cv=TSS5)
"""

from __future__ import annotations

import warnings

import numpy as np
import polars as pl
from sklearn.linear_model import ElasticNetCV, RidgeCV
from sklearn.model_selection import TimeSeriesSplit

from candidate_models._base_v2 import _AttachMixin, _KEYS
from rv_eval.features import HAR_RS_FEATURES, IV_FEATURES
from rv_eval.model_contract import _PerKeyModel

_FLOOR = 1e-12  # matches features.py / har_cj.py log-floor

# --- derived (rolling / shift / ratio) columns: the union of tracks 13-17 ----------------
_LEV = ["lev_d", "lev_w", "lev_m"]                        # 13 leverage
_SJ = ["sj_5d", "abs_sj_5d"]                              # 14 signed jump
_IVTS = ["iv_curv", "iv_ts_30_90", "vrp_lag", "vrp_mom"]  # 15 IV term structure + VRP
_RANGE = ["log_park_d", "log_park_w", "log_gk_d", "log_gk_w"]   # 16 range estimators
_ACT = ["log_vol_surprise", "log_txn_surprise", "overnight_share"]  # 17 activity / overnight
_DERIVED = _LEV + _SJ + _IVTS + _RANGE + _ACT

# Pass-through (already produced by build_features, present on X). Dedupe vs derived.
_PASSTHROUGH = list(dict.fromkeys(HAR_RS_FEATURES + IV_FEATURES + ["sqrt_rq"]))

# Full kitchen-sink feature list (deduped, order-stable) — identical to HAR-MAX (model 18).
_NEEDS = list(dict.fromkeys(_PASSTHROUGH + _DERIVED))


def _maxmatrix_panel(src: pl.DataFrame) -> pl.DataFrame:
    """Full-history derived columns (tracks 13-17), per ticker, trailing/point-in-time.

    Built once on the FULL series and joined by (ticker, date); mirrors the trailing-window
    discipline of features.build_features / har_cj.py::_attach so a value is identical
    regardless of which fold slice the row lands in. min_samples on the weekly/monthly windows
    nulls the leading rows exactly like the harness's own HAR roll-means.
    """
    down = pl.min_horizontal(pl.col("ret_cc"), pl.lit(0.0))
    return (
        src.sort("ticker", "date")
        .with_columns(_down=down)
        .with_columns(
            # 13 — signed downside-return aggregates
            lev_d=pl.col("_down").rolling_mean(1, min_samples=1).over("ticker"),
            lev_w=pl.col("_down").rolling_mean(5, min_samples=5).over("ticker"),
            lev_m=pl.col("_down").rolling_mean(22, min_samples=22).over("ticker"),
            # 14 — weekly signed jump (rs_plus - rs_minus) and its magnitude
            sj_5d=(pl.col("rs_plus") - pl.col("rs_minus"))
            .rolling_mean(5, min_samples=5).over("ticker"),
            # 15 — IV term-structure curvature/slope + point-in-time VRP (iv_30d**2, not iv2)
            iv_curv=pl.col("iv_30d") - 2.0 * pl.col("iv_60d") + pl.col("iv_90d"),
            iv_ts_30_90=pl.col("iv_90d") - pl.col("iv_30d"),
            vrp_lag=pl.col("iv_30d") ** 2 - pl.col("total_rv"),
            # 16 — log range-estimator roll-means (parkinson / gk)
            log_park_d=pl.col("parkinson").rolling_mean(1, min_samples=1).over("ticker")
            .clip(lower_bound=_FLOOR).log(),
            log_park_w=pl.col("parkinson").rolling_mean(5, min_samples=5).over("ticker")
            .clip(lower_bound=_FLOOR).log(),
            log_gk_d=pl.col("gk").rolling_mean(1, min_samples=1).over("ticker")
            .clip(lower_bound=_FLOOR).log(),
            log_gk_w=pl.col("gk").rolling_mean(5, min_samples=5).over("ticker")
            .clip(lower_bound=_FLOOR).log(),
            # 17 — log volume/transaction surprise vs 22d mean; overnight RV share
            log_vol_surprise=pl.col("volume").clip(lower_bound=_FLOOR).log()
            - pl.col("volume").rolling_mean(22, min_samples=22).over("ticker")
            .clip(lower_bound=_FLOOR).log(),
            log_txn_surprise=pl.col("transactions").clip(lower_bound=_FLOOR).log()
            - pl.col("transactions").rolling_mean(22, min_samples=22).over("ticker")
            .clip(lower_bound=_FLOOR).log(),
            overnight_share=pl.col("rv_overnight")
            / pl.col("total_rv").clip(lower_bound=_FLOOR),
        )
        .with_columns(
            abs_sj_5d=pl.col("sj_5d").abs(),
            vrp_mom=pl.col("vrp_lag") - pl.col("vrp_lag").shift(5).over("ticker"),
        )
        .select(_KEYS + _DERIVED)
    )


class _ShrinkHAR(_AttachMixin, _PerKeyModel):
    """Per-(ticker, horizon) penalised log-OLS on the HAR-MAX feature matrix.

    Subclass sets `_make_cv()` -> an unfitted sklearn CV regressor with a time-ordered inner
    CV (TimeSeriesSplit). The mean is the lognormal-corrected exp(mu + 0.5 s^2) — consistent
    with `_LinearLogHAR` / the benchmarks. `sigma` is the in-sample log-residual std.
    """

    needs = _NEEDS
    min_obs = 100              # need enough train rows for a 5-fold time-series CV of ~25 feats
    _CV_SPLITS = 5

    def fit(self, X: pl.DataFrame, y: pl.DataFrame) -> None:
        # record selected hyperparameters per (ticker, horizon) for the card
        self.warnings: dict[tuple[str, int], str] = {}
        super().fit(X, y)

    def _make_cv(self, n: int):  # pragma: no cover - abstract
        raise NotImplementedError

    def _record(self, sub: pl.DataFrame, h: int, est) -> None:
        tk = sub["ticker"][0]
        if isinstance(est, ElasticNetCV):
            self.warnings[(tk, h)] = (
                f"alpha={est.alpha_:.4g}, l1_ratio={est.l1_ratio_:.3g}"
            )
        elif isinstance(est, RidgeCV):
            self.warnings[(tk, h)] = f"alpha={float(est.alpha_):.4g}"

    def _fit_one(self, sub: pl.DataFrame, h: int):
        sub = sub.sort("date")                       # time order for the inner TimeSeriesSplit
        Xm = sub.select(self.needs).to_numpy().astype(float)
        ylog = np.log(sub["target_var"].to_numpy().astype(float))
        # standardise on the train slice; store mu/sd to re-apply at predict
        mu = Xm.mean(axis=0)
        sd = Xm.std(axis=0)
        sd = np.where(sd < 1e-12, 1.0, sd)           # guard constant columns
        Xs = (Xm - mu) / sd
        est = self._make_cv(Xs.shape[0])
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            est.fit(Xs, ylog)
        resid = ylog - est.predict(Xs)
        # dof-aware residual sd; fall back to plain std then a floor
        k = int(np.sum(np.abs(est.coef_) > 0)) + 1
        dof = max(resid.size - k, 1)
        s = float(np.sqrt(np.sum(resid ** 2) / dof)) if resid.size > k else float(np.std(resid))
        if not np.isfinite(s) or s <= 0:
            s = 0.5
        self._record(sub, h, est)
        return (est, mu, sd, max(s, 1e-3))

    def _predict_one(self, state, sub: pl.DataFrame, h: int):
        est, mu, sd, s = state
        Xm = sub.select(self.needs).to_numpy().astype(float)
        Xs = (Xm - mu) / sd
        # sklearn.predict rejects NaN, so score only the complete rows and leave the
        # incomplete ones (leading rolling-window nulls) as NaN -> dropped by the base filter.
        ok = np.isfinite(Xs).all(axis=1)
        mulog = np.full(sub.height, np.nan)
        if ok.any():
            mulog[ok] = est.predict(Xs[ok])
        m = np.exp(mulog + 0.5 * s * s)              # lognormal mean (QLIKE-optimal)
        return m, np.full(sub.height, s, dtype=float)

    # P1 derive hook (shared by both subclasses) ---------------------------------------
    def _derive(self, src: pl.DataFrame) -> pl.DataFrame:
        return _maxmatrix_panel(src)


class HARENet(_ShrinkHAR):
    """Elastic-Net-shrunk HAR-MAX. Penalty + l1-ratio by time-ordered inner CV (priority)."""

    name = "HAR-ENet"
    _L1_RATIOS = [0.1, 0.3, 0.5, 0.7, 0.9, 0.95, 0.99, 1.0]
    _SEED = 0

    def _make_cv(self, n: int):
        n_splits = max(2, min(self._CV_SPLITS, n - 1))
        return ElasticNetCV(
            l1_ratio=self._L1_RATIOS,
            n_alphas=50,
            cv=TimeSeriesSplit(n_splits=n_splits),
            max_iter=20000,
            tol=1e-4,
            random_state=self._SEED,
            n_jobs=1,
        )


class HARRidge(_ShrinkHAR):
    """Ridge-shrunk HAR-MAX. Penalty by time-ordered inner CV (RidgeCV over a log-grid)."""

    name = "HAR-Ridge"
    _ALPHAS = np.logspace(-3, 3, 25)

    def _make_cv(self, n: int):
        n_splits = max(2, min(self._CV_SPLITS, n - 1))
        return RidgeCV(alphas=self._ALPHAS, cv=TimeSeriesSplit(n_splits=n_splits))
