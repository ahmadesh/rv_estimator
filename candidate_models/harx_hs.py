"""HARX-HeteroSigma — HAR-X mean with an explicit heteroskedastic log-variance head.

ITER2 catalog model 25 (Track D, Pattern P2). The cheapest, highest-leverage
calibration fix: keep the proven HAR-X *mean* forecast, but replace its single
in-sample residual-sd `s` with a **per-row, observation-conditional** predictive
log-sd `s_t`. The level mean `rv_hat` is unchanged from HAR-X; only the width of
the predictive distribution (sigma, q05..q95) is made state-dependent, so days the
model "knows" are noisy (high realized-quarticity, high VIX/VVIX, term-structure
inversion) get wider intervals.

Spec, per (ticker, horizon):

  mean model (HAR-X, log-OLS):
      log(target_var) = a0 + a' [HAR_FEATURES + IV_FEATURES] + e
  log-variance model (the hetero-sigma head):
      log(e_t^2 + eps) = b0 + b' z_t + nu_t ,   z_t = [log_sqrt_rq, vix, vvix, vix9d_slope]
  predictive log-sd:
      s_t = clip( sqrt( exp( b0 + b' z_t ) ), s_floor, s_cap )

`_predict_one` returns `(m, s_t)` with `s_t` a length-n array; the base
`_PerKeyModel.predict` already applies `sigma = m*sqrt(expm1(s_t^2))` and the
lognormal quantiles elementwise, so a per-row `s` needs NO harness change
(catalog §4.4 / model_contract.py::_PerKeyModel.predict).

All variance-head regressors are point-in-time and already in X:
`vix`/`vvix`/`vix9d_slope` pass through `build_features` from inputs.parquet, and
`sqrt_rq` is produced by `build_features` (`log_sqrt_rq` is a row-wise log of it,
no trailing window → no leakage, computed safely on the predict slice). No
`_AttachMixin` / join is needed. If a variance regressor is entirely missing in a
fit slice it is dropped from `z` for that key (recorded on `self.warnings`); if the
head cannot be fit at all the model falls back to the HAR-X homoskedastic `s`.

Hyperparameters are fixed by construction (no CV search): the regressor set is the
catalog-specified `[log_sqrt_rq, vix, vvix, vix9d_slope]`; `eps`, `s_floor`,
`s_cap` are numerical-stability constants, not tuned to any data split.
"""

from __future__ import annotations

import numpy as np
import polars as pl

from rv_eval.features import HAR_FEATURES, IV_FEATURES
from rv_eval.model_contract import _PerKeyModel

# Variance-head regressors (catalog §3 model 25). `log_sqrt_rq` is derived row-wise
# from `sqrt_rq` (in X via build_features); the rest pass through from inputs.parquet.
_VAR_RAW = ["sqrt_rq", "vix", "vvix", "vix9d_slope"]

_EPS = 1e-12        # floor inside log(e^2 + eps) so zero residuals are well defined
_S_FLOOR = 1e-3     # min predictive log-sd (matches _LinearLogHAR's floor)
_S_CAP = 5.0        # max predictive log-sd (guard against runaway head extrapolation)


def _log_sqrt_rq(sub: pl.DataFrame) -> np.ndarray:
    """Row-wise log of sqrt_rq with a positive floor (no trailing window → leak-free)."""
    v = sub["sqrt_rq"].to_numpy().astype(float)
    return np.log(np.maximum(v, _EPS))


def _var_design(sub: pl.DataFrame) -> np.ndarray:
    """Variance-head design [1, log_sqrt_rq, vix, vvix, vix9d_slope]."""
    cols = [_log_sqrt_rq(sub)]
    for c in ["vix", "vvix", "vix9d_slope"]:
        cols.append(sub[c].to_numpy().astype(float))
    return np.column_stack([np.ones(sub.height), *cols])


class HARXHeteroSigma(_PerKeyModel):
    """HAR-X mean + log-variance head giving a per-row predictive sigma (catalog 25)."""

    name = "HARX-HS"
    needs = HAR_FEATURES + IV_FEATURES + _VAR_RAW
    min_obs = 100

    def fit(self, X: pl.DataFrame, y: pl.DataFrame) -> None:
        self.warnings: dict[tuple[str, int], str] = {}
        super().fit(X, y)

    # --- mean model design (HAR-X) -----------------------------------------
    def _mean_design(self, sub: pl.DataFrame) -> np.ndarray:
        x = sub.select(HAR_FEATURES + IV_FEATURES).to_numpy().astype(float)
        return np.column_stack([np.ones(x.shape[0]), x])

    def _fit_one(self, sub: pl.DataFrame, h: int):
        # 1) HAR-X mean in log space.
        A = self._mean_design(sub)
        ylog = np.log(sub["target_var"].to_numpy().astype(float))
        beta, *_ = np.linalg.lstsq(A, ylog, rcond=None)
        resid = ylog - A @ beta
        # Homoskedastic fallback sd (used if the variance head can't be fit).
        s_homo = float(np.std(resid, ddof=A.shape[1])) if resid.size > A.shape[1] else 0.5
        s_homo = max(s_homo, _S_FLOOR)

        # 2) Log-variance head: regress log(resid^2 + eps) on z.
        Z = _var_design(sub)
        log_e2 = np.log(resid * resid + _EPS)
        gamma = None
        if np.all(np.isfinite(Z)) and Z.shape[0] > Z.shape[1] + 1:
            try:
                g, *_ = np.linalg.lstsq(Z, log_e2, rcond=None)
                if np.all(np.isfinite(g)):
                    gamma = g
            except Exception:
                gamma = None
        if gamma is None:
            self.warnings[(sub["ticker"][0], h)] = (
                "hetero-sigma head not fit (degenerate/missing regressors); "
                "fell back to homoskedastic HAR-X sigma"
            )
        return (beta, gamma, s_homo)

    def _predict_one(self, state, sub: pl.DataFrame, h: int):
        beta, gamma, s_homo = state
        mu = self._mean_design(sub) @ beta          # NaN propagates where a feature is null
        if gamma is not None:
            Z = _var_design(sub)
            log_var = Z @ gamma
            s = np.sqrt(np.exp(np.clip(log_var, -50.0, 50.0)))
            # Where any variance regressor is null, fall back to the homoskedastic sd.
            s = np.where(np.isfinite(s), s, s_homo)
        else:
            s = np.full(sub.height, s_homo, dtype=float)
        s = np.clip(s, _S_FLOOR, _S_CAP)
        m = np.exp(mu + 0.5 * s * s)                # per-row lognormal mean
        return m, s
