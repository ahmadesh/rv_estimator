"""XGBoost on HAR-RS + IV features (MODEL_PLAN.md §4 model 9).

One gradient-boosted tree ensemble per (ticker, horizon) regressing
``log(target_var)`` on the same feature matrix as the strongest linear baseline
(model 7): the semivariance/jump HAR block, the implied-vol block, and the
realized-quarticity term — i.e. ``HAR_RS_FEATURES + IV_FEATURES + ["sqrt_rq"]``.
The booster is a flexible, non-linear function of those regressors; predictions
are exponentiated back to ``target_var`` units and dressed with lognormal
quantiles consistently with the benchmarks (`_lognormal_quantiles`).

`n_estimators` is chosen per fit by early stopping on a 10% time-ordered
within-train tail (leakage-safe; cap 2000). `sigma` is the residual std of
``log(target_var)`` on that same held-out tail.

Fixed params (MODEL_PLAN §4 table): subsample=0.8, colsample_bytree=0.8,
reg_lambda=1.0, objective="reg:squarederror", seed=0, tree_method="hist".

=============================================================================
HYPERPARAMETER SELECTION — tune-once-then-freeze (MODEL_PLAN §4)
=============================================================================
Grid (27 points):
    max_depth        ∈ {3, 4, 6}
    learning_rate    ∈ {0.03, 0.05, 0.1}
    min_child_weight ∈ {5, 10, 20}
Initial point (grid bold in the plan): max_depth=4, learning_rate=0.05,
    min_child_weight=10.
Split (leakage-safe, pre-OOS only):
    search-train = rows with date <  HPTUNE_VAL_START (2016-01-01)
    validation   = rows in [HPTUNE_VAL_START, OOS_START) = 2016-2017
    (no date >= OOS_START / 2018 is read during tuning)
Procedure: for each grid point fit ONE global booster (pooled across all
    SCORED_TICKERS) on search-train at the primary horizon h=22
    (= HPTUNE_METRIC_HORIZON), with early stopping on a within-search-train
    time-ordered 10% tail; score pooled QLIKE at h=22 on the validation block;
    keep the lowest. Metric: QLIKE = mean( rv/rv_hat - log(rv/rv_hat) - 1 ),
    rv_hat = exp(pred + 0.5*sigma^2) (lognormal-mean forecast).
Metric: pooled QLIKE @ h=22 (HPTUNE_METRIC_HORIZON).

CHOSEN (frozen below) — see _tune_xgb.py / tuning run 2026-05-31:
    max_depth=3, learning_rate=0.03, min_child_weight=20
Validation QLIKE @ h22:
    winner            (3, 0.03, 20) = 0.146970
    initial point     (4, 0.05, 10) = 0.158985
=============================================================================
"""

from __future__ import annotations

import numpy as np
import polars as pl
import xgboost as xgb

from rv_eval.features import HAR_RS_FEATURES, IV_FEATURES
from rv_eval.model_contract import _PerKeyModel

_SEED = 0
_VAL_TAIL_FRAC = 0.10        # time-ordered within-train tail for early stopping + sigma
_N_ESTIMATORS_CAP = 2000
_EARLY_STOPPING_ROUNDS = 50


def _dedup(seq: list[str]) -> list[str]:
    """Drop repeats while preserving first-seen order."""
    seen: set[str] = set()
    return [c for c in seq if not (c in seen or seen.add(c))]


class XGBHARRSIV(_PerKeyModel):
    """Gradient-boosted trees on the HAR-RS + IV + sqrt_rq feature block.

    One xgboost booster per (ticker, horizon) predicting log(target_var); rv_hat
    is the lognormal-mean back-transform, sigma the held-out-tail residual std.
    """

    name = "XGBHARRSIV"
    needs = _dedup(HAR_RS_FEATURES + IV_FEATURES + ["sqrt_rq"])
    min_obs = 100

    # --- frozen hyperparameters (tune-once-then-freeze; see module docstring) ---
    MAX_DEPTH = 3
    LEARNING_RATE = 0.03
    MIN_CHILD_WEIGHT = 20

    def _params(self) -> dict:
        return {
            "objective": "reg:squarederror",
            "max_depth": self.MAX_DEPTH,
            "learning_rate": self.LEARNING_RATE,
            "min_child_weight": self.MIN_CHILD_WEIGHT,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "reg_lambda": 1.0,
            "tree_method": "hist",
            "seed": _SEED,
        }

    def _fit_one(self, sub: pl.DataFrame, h: int):
        sub = sub.sort("date")
        X = sub.select(self.needs).to_numpy().astype(np.float64)
        y = np.log(sub["target_var"].to_numpy().astype(np.float64))

        n = X.shape[0]
        n_val = max(1, int(round(n * _VAL_TAIL_FRAC)))
        if n - n_val < self.min_obs // 2:           # keep a sane training core
            n_val = max(1, n - self.min_obs // 2)
        X_tr, y_tr = X[:-n_val], y[:-n_val]
        X_val, y_val = X[-n_val:], y[-n_val:]

        model = xgb.XGBRegressor(
            n_estimators=_N_ESTIMATORS_CAP,
            early_stopping_rounds=_EARLY_STOPPING_ROUNDS,
            **self._params(),
        )
        model.fit(X_tr, y_tr, eval_set=[(X_val, y_val)], verbose=False)

        # residual std on the held-out tail (sigma in log space)
        resid = y_val - model.predict(X_val)
        s = float(np.std(resid)) if resid.size > 1 else 0.5
        return (model, max(s, 1e-3))

    def _predict_one(self, state, sub: pl.DataFrame, h: int):
        model, s = state
        X = sub.select(self.needs).to_numpy().astype(np.float64)
        mu = model.predict(X).astype(np.float64)        # NaN propagates where a feature is null
        m = np.exp(mu + 0.5 * s * s)                     # lognormal mean -> target_var units
        return m, np.full(sub.height, s, dtype=float)
