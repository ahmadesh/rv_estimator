"""Realized GARCH — Hansen, Huang & Shek (2012) (MODEL_PLAN.md §4 model 8).

The Realized GARCH(1,1) model of HHS(2012) couples a daily return equation, a
log-linear GARCH recursion driven by a *realized measure* of variance, and a
measurement equation that ties the realized measure back to the latent
conditional variance (with a leverage function). With the realized measure on
the right-hand side of the GARCH recursion, the conditional variance reacts to
intraday information rather than only to squared daily returns — which is the
whole point of HHS(2012).

Spec (the "RealGARCH(1,1)" log/log specification, HHS §2):

    return eq.       r_t   = sqrt(h_t) * z_t,           z_t ~ N(0,1)
    GARCH eq.        log h_t = omega + beta*log h_{t-1} + gamma*log x_{t-1}
    measurement eq.  log x_t = xi + phi*log h_t + tau(z_t) + u_t,   u_t ~ N(0, su2)
    leverage         tau(z)  = tau1*z + tau2*(z^2 - 1)

    r_t = daily close-to-close return (`ret_cc`; the plan's `ret_close`).
    x_t = realized measure of daily variance (`rv_d` = total_rv), same units as r_t^2.

Parameters per (ticker, horizon): theta = (omega, beta, gamma, xi, phi, tau1,
tau2, su2). They are estimated jointly by maximum likelihood (HHS eq. 2.7):

    L = -1/2 * sum_t [ log h_t + r_t^2/h_t + log su2 + u_t^2/su2 ]

We optimise with scipy. `omega` is clipped to a small positive floor for
numerical stability; if the joint MLE fails to converge (or is degenerate) for a
(ticker, horizon) we FALL BACK to a plain Gaussian GARCH(1,1) on returns via
`arch` and record the fallback. If even the fallback fails, that (ticker,
horizon) is DROPPED (never imputed) — the base `_PerKeyModel` simply stores no
state, so `predict` yields no row for it.

Horizon forecast. There is no clean closed form for the multi-step variance of a
log/log Realized GARCH, so for horizon h we Monte-Carlo bootstrap ~1000 paths of
the joint (log h, log x) recursion h steps forward, drawing z ~ N(0,1) and
u ~ N(0, su2) at each step, and sum the simulated conditional variances:

    rv_hat = E[ sum_{s=t+1..t+h} h_s ]   (target_var units = sum of next-h daily RVs)
    sigma  = std( log( sum_s h_s ) )      (log-std of the simulated horizon sums)

For the GARCH(1,1) fallback the same MC bootstrap is run on the standard
variance recursion (h1 closed form would do for h, but MC keeps one code path
and a consistent `sigma`). numpy seed is fixed to 0 for reproducibility.
"""

from __future__ import annotations

import warnings

import numpy as np
import polars as pl
from scipy.optimize import minimize

from rv_eval.model_contract import _PerKeyModel

_SEED = 0
_N_PATHS = 1000
_OMEGA_FLOOR = 1e-8        # small positive floor on the GARCH intercept
_H_FLOOR = 1e-12           # floor on conditional variance / realized measure before log
_RET_COL = "ret_cc"        # plan calls this `ret_close`; the panel column is `ret_cc`
_RV_COL = "rv_d"           # realized measure (= total_rv)


def _series(sub: pl.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Pull aligned (returns, realized-measure) arrays, sorted by date, RV floored > 0."""
    sub = sub.sort("date")
    r = sub[_RET_COL].to_numpy().astype(float)
    x = sub[_RV_COL].to_numpy().astype(float)
    x = np.where(np.isfinite(x) & (x > 0), x, _H_FLOOR)
    r = np.where(np.isfinite(r), r, 0.0)
    return r, x


def _rgarch_nll(theta: np.ndarray, r: np.ndarray, x: np.ndarray, h0: float) -> float:
    """Joint negative log-likelihood of the RealGARCH(1,1) log/log model (HHS eq. 2.7)."""
    omega, beta, gamma, xi, phi, tau1, tau2, su2 = theta
    su2 = max(su2, 1e-10)
    n = r.size
    logx = np.log(np.maximum(x, _H_FLOOR))
    logh = np.empty(n)
    logh[0] = np.log(max(h0, _H_FLOOR))
    for t in range(1, n):
        logh[t] = omega + beta * logh[t - 1] + gamma * logx[t - 1]
        if not np.isfinite(logh[t]):
            return 1e12
    logh = np.clip(logh, -50.0, 50.0)
    h = np.exp(logh)
    z = r / np.sqrt(h)
    tau = tau1 * z + tau2 * (z * z - 1.0)
    u = logx - (xi + phi * logh + tau)
    ll = -0.5 * np.sum(logh + r * r / h + np.log(su2) + u * u / su2)
    return -ll if np.isfinite(ll) else 1e12


def _fit_rgarch(r: np.ndarray, x: np.ndarray):
    """MLE the RealGARCH(1,1). Returns (theta, h_last) or None on failure."""
    h0 = float(np.mean(x))
    # init: persistent variance, measurement ~ identity, mild leverage.
    theta0 = np.array([0.05, 0.55, 0.40, 0.0, 1.0, -0.05, 0.05, float(np.var(np.log(np.maximum(x, _H_FLOOR))))])
    theta0[7] = max(theta0[7], 1e-4)
    bounds = [
        (-5.0, 5.0),      # omega
        (0.0, 0.9999),    # beta
        (0.0, 2.0),       # gamma
        (-5.0, 5.0),      # xi
        (0.01, 3.0),      # phi
        (-2.0, 2.0),      # tau1
        (-2.0, 2.0),      # tau2
        (1e-6, 10.0),     # su2
    ]
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            res = minimize(_rgarch_nll, theta0, args=(r, x, h0), method="L-BFGS-B",
                           bounds=bounds, options={"maxiter": 500})
    except Exception:
        return None
    if not res.success and not np.isfinite(res.fun):
        return None
    theta = res.x.copy()
    theta[0] = max(theta[0], np.log(_OMEGA_FLOOR))  # floor omega in log-variance space
    # reconstruct the last conditional variance to seed the forecast recursion
    omega, beta, gamma = theta[0], theta[1], theta[2]
    logx = np.log(np.maximum(x, _H_FLOOR))
    logh = np.log(max(h0, _H_FLOOR))
    for t in range(1, r.size):
        logh = omega + beta * logh + gamma * logx[t - 1]
    logh = float(np.clip(logh, -50.0, 50.0))
    if not np.isfinite(logh) or not np.isfinite(res.fun) or res.fun >= 1e11:
        return None
    return theta, np.exp(logh), float(logx[-1])


def _fit_garch11(r: np.ndarray):
    """Plain Gaussian GARCH(1,1) fallback via `arch`. Returns (params, h_last) or None."""
    from arch.univariate import arch_model
    try:
        scale = 100.0  # arch is ill-conditioned on tiny daily returns; fit in % space
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            am = arch_model(r * scale, mean="Zero", vol="GARCH", p=1, q=1, dist="normal",
                            rescale=False)
            fr = am.fit(disp="off", show_warning=False)
        omega = max(float(fr.params["omega"]), _OMEGA_FLOOR) / (scale * scale)
        alpha = float(fr.params["alpha[1]"])
        beta = float(fr.params["beta[1]"])
        cv = fr.conditional_volatility[-1] / scale
        h_last = float(cv * cv)
        if not np.all(np.isfinite([omega, alpha, beta, h_last])):
            return None
        r_last = float(r[-1])
        return (omega, alpha, beta), h_last, r_last
    except Exception:
        return None


def _forecast_rgarch(theta, h_last, logx_last, h: int, rng) -> tuple[float, float]:
    omega, beta, gamma, xi, phi, tau1, tau2, su2 = theta
    su = np.sqrt(max(su2, 1e-10))
    logh = np.full(_N_PATHS, np.log(max(h_last, _H_FLOOR)))
    logx = np.full(_N_PATHS, logx_last)
    cumsum = np.zeros(_N_PATHS)
    for _ in range(h):
        logh = omega + beta * logh + gamma * logx
        logh = np.clip(logh, -50.0, 50.0)
        hs = np.exp(logh)
        cumsum += hs
        z = rng.standard_normal(_N_PATHS)
        u = su * rng.standard_normal(_N_PATHS)
        logx = xi + phi * logh + tau1 * z + tau2 * (z * z - 1.0) + u
    return float(np.mean(cumsum)), float(np.std(np.log(np.maximum(cumsum, _H_FLOOR))))


def _forecast_garch11(params, h_last, r_last, h: int, rng) -> tuple[float, float]:
    omega, alpha, beta = params
    h_state = np.full(_N_PATHS, max(h_last, _H_FLOOR))
    eps_prev = np.full(_N_PATHS, r_last)
    cumsum = np.zeros(_N_PATHS)
    for _ in range(h):
        h_state = omega + alpha * eps_prev * eps_prev + beta * h_state
        h_state = np.maximum(h_state, _H_FLOOR)
        cumsum += h_state
        eps_prev = np.sqrt(h_state) * rng.standard_normal(_N_PATHS)
    return float(np.mean(cumsum)), float(np.std(np.log(np.maximum(cumsum, _H_FLOOR))))


class RealizedGARCH(_PerKeyModel):
    """Hansen-Huang-Shek (2012) Realized GARCH, fit per (ticker, horizon) by MLE.

    Falls back to a plain GARCH(1,1) when the joint MLE fails to converge; the
    chosen variant per key is recorded on `self.warnings` for the model card.
    """

    name = "RealizedGARCH"
    needs = [_RET_COL, _RV_COL]
    min_obs = 100

    def fit(self, X: pl.DataFrame, y: pl.DataFrame) -> None:
        self.warnings: dict[tuple[str, int], str] = {}
        super().fit(X, y)

    def _fit_one(self, sub: pl.DataFrame, h: int):
        r, x = _series(sub)
        if r.size < self.min_obs:
            return None
        fit = _fit_rgarch(r, x)
        if fit is not None:
            theta, h_last, logx_last = fit
            return ("rgarch", theta, h_last, logx_last)
        # fall back to plain GARCH(1,1)
        if not hasattr(self, "warnings"):
            self.warnings = {}
        fb = _fit_garch11(r)
        if fb is not None:
            params, h_last, r_last = fb
            self.warnings[(sub["ticker"][0], h)] = "fallback: GARCH(1,1) (R-GARCH MLE failed)"
            return ("garch11", params, h_last, r_last)
        self.warnings[(sub["ticker"][0], h)] = "dropped: both R-GARCH and GARCH(1,1) failed"
        return None

    def _predict_one(self, state, sub: pl.DataFrame, h: int):
        if state is None:
            n = sub.height
            return np.full(n, np.nan), np.full(n, np.nan)
        rng = np.random.default_rng(_SEED)
        kind = state[0]
        if kind == "rgarch":
            _, theta, h_last, logx_last = state
            m, s = _forecast_rgarch(theta, h_last, logx_last, h, rng)
        else:
            _, params, h_last, r_last = state
            m, s = _forecast_garch11(params, h_last, r_last, h, rng)
        n = sub.height
        if not np.isfinite(m) or m <= 0:
            return np.full(n, np.nan), np.full(n, np.nan)
        s = float(np.clip(s, 1e-3, 5.0))
        return np.full(n, m, dtype=float), np.full(n, s, dtype=float)
