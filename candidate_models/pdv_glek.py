"""Guyon-Lekeufack 4-factor Path-Dependent Volatility (PDV) — MODEL_PLAN.md §4 model 11.

Guyon & Lekeufack (2023) "Volatility is (mostly) path-dependent" / Gazzani & Guyon
(2024) 4-factor PDV. Spot variance is an explicit, parsimonious function of the
*path* of past returns through two path-features built from exponential kernels:

    sigma_t^2 = beta0 + beta1 * R1_t + beta2 * sqrt(R2_t)

    R1_t = (1 - theta)  * sum_s K_short (t-s) r_s    + theta  * sum_s K_long (t-s) r_s      (trend)
    R2_t = (1 - theta') * sum_s K_short'(t-s) r_s^2  + theta' * sum_s K_long'(t-s) r_s^2    (activity)

`r_s` is the daily close-to-close return (`ret_cc`; the plan calls it `ret_close`).
The two kernels in each factor are exponentials with a short and a long half-life,
so each weighted path-sum is just an EWMA and is maintained by an O(1) recursion
(no O(t^2) convolution): for decay lambda, EWMA_t = lambda * EWMA_{t-1} + r_t.

PARAMETERS per (ticker, horizon) — 9 scalars, ALL fit by `scipy.optimize`
(L-BFGS-B), NO grid search:

    (beta0, beta1, beta2, theta, theta', lambda_short, lambda_long, lambda_short', lambda_long')

The lambdas are parameterised in the optimizer as exponential *decays* derived
from half-lives via lambda = exp(-ln(2) / half_life). To keep the optimizer in a
well-scaled space we fit each lambda through the half-life it implies, seeded at:

    short half-life ~ 8 trading days   -> lambda_short  = exp(-ln2/8)   ~ 0.917
    long  half-life ~ 250 trading days -> lambda_long   = exp(-ln2/250) ~ 0.99723

(same seeds for both the trend pair and the activity pair). These only SEED the
optimizer; the half-lives themselves are free parameters.

BOUNDS (clipping for numerical robustness):
    beta0  >= 0 (variance floor)              theta, theta'  in [0, 1]
    beta1  free                               half-lives     in [1.5, 1000] days
    beta2  >= 0                               -> lambdas in (exp(-ln2/1.5), exp(-ln2/1000))

FIT objective — one-step log-MSE on daily RV: minimise
    mean( ( log(sigma_t^2 + eps) - log(rv_d_t + eps) )^2 )
over the in-sample path. sigma_t^2 is the model variance, rv_d_t the realized
daily variance (`rv_d` = total_rv). beta1 can attach to the (signed) trend factor,
so sigma_t^2 is floored at a small positive value before the log.

HORIZON forecast (h-step). No closed form, so for horizon h we MONTE-CARLO
bootstrap the fitted ONE-STEP standardised residuals: with one-step fit residuals
on the variance scale e_t = rv_d_t / max(sigma_t^2, floor) (multiplicative,
mean ~ 1), we simulate h steps x N_PATHS paths. Each step:
  1. variance forecast sigma_t^2 from the current EWMA states (R1, R2),
  2. realized variance draw rv_sim = sigma_t^2 * bootstrap(e), summed into the
     horizon variance,
  3. a simulated return r_sim = sqrt(rv_sim) * Rademacher(+/-1) advances the four
     EWMA states (sign carries the trend factor; r_sim^2 = rv_sim feeds activity).
Then:
    rv_hat = mean over paths of sum_{step=1..h} rv_sim   (target_var units)
    sigma  = std over paths of log(horizon-variance sum)  (log-std for lognormal q's)

N_PATHS (smoke test): small (see test, monkeypatched). N_PATHS (real walk-forward):
500. `numpy.random.seed(0)` / a seeded Generator(0) fixes the bootstrap.

CONVERGENCE HANDLING. If L-BFGS-B raises or returns a non-finite objective for a
(ticker, horizon), we FALL BACK to a fixed-kernel reduced fit: freeze the four
half-lives at their seeds and re-optimise only (beta0, beta1, beta2, theta, theta')
(5 linear-ish scalars). If that also fails the key is DROPPED (never imputed) —
the base `_PerKeyModel` stores no state and `predict` yields no row for it. The
variant used per key is recorded on `self.warnings` for the model card.
"""

from __future__ import annotations

import warnings

import numpy as np
import polars as pl
from scipy.optimize import minimize

from rv_eval.model_contract import _PerKeyModel

_SEED = 0
_N_PATHS = 500            # paths the real walk-forward uses; the smoke test shrinks this
_EPS = 1e-12              # variance floor before any log
_LN2 = np.log(2.0)

# half-life seeds (trading days) -> exponential decays lambda = exp(-ln2 / hl)
_HL_SHORT = 8.0
_HL_LONG = 250.0
_HL_MIN = 1.5
_HL_MAX = 1000.0

_RET_COL = "ret_cc"       # plan calls this `ret_close`; the panel column is `ret_cc`
_RET_COL_ALT = "ret_close"
_RV_COL = "rv_d"          # realized daily variance (= total_rv)


def _hl_to_lambda(hl: float) -> float:
    return float(np.exp(-_LN2 / hl))


def _series(sub: pl.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Aligned (returns, realized-variance) arrays, date-sorted, cleaned."""
    sub = sub.sort("date")
    rcol = _RET_COL if _RET_COL in sub.columns else _RET_COL_ALT
    r = sub[rcol].to_numpy().astype(float)
    x = sub[_RV_COL].to_numpy().astype(float)
    r = np.where(np.isfinite(r), r, 0.0)
    x = np.where(np.isfinite(x) & (x > 0), x, _EPS)
    return r, x


def _ewma_path(z: np.ndarray, lam: float) -> np.ndarray:
    """Causal EWMA state e_t = lam * e_{t-1} + z_t (uses only s <= t)."""
    out = np.empty(z.size)
    acc = 0.0
    for t in range(z.size):
        acc = lam * acc + z[t]
        out[t] = acc
    return out


def _variance_path(params: np.ndarray, r: np.ndarray) -> np.ndarray:
    """In-sample one-step variance path sigma_t^2 for the 9-scalar PDV model."""
    b0, b1, b2, th1, th2, ls1, ll1, ls2, ll2 = params
    r2 = r * r
    R1 = (1.0 - th1) * _ewma_path(r, ls1) + th1 * _ewma_path(r, ll1)
    R2 = (1.0 - th2) * _ewma_path(r2, ls2) + th2 * _ewma_path(r2, ll2)
    var = b0 + b1 * R1 + b2 * np.sqrt(np.maximum(R2, 0.0))
    return np.maximum(var, _EPS)


def _logmse(params: np.ndarray, r: np.ndarray, x: np.ndarray) -> float:
    var = _variance_path(params, r)
    if not np.all(np.isfinite(var)):
        return 1e12
    d = np.log(var + _EPS) - np.log(x + _EPS)
    val = float(np.mean(d * d))
    return val if np.isfinite(val) else 1e12


# parameter order: b0, b1, b2, theta, theta', lam_s1, lam_l1, lam_s2, lam_l2
_LAM_LO = _hl_to_lambda(_HL_MIN)     # fastest decay (smallest half-life)
_LAM_HI = _hl_to_lambda(_HL_MAX)     # slowest decay (largest half-life)
_BOUNDS = [
    (0.0, None),          # beta0 >= 0
    (None, None),         # beta1 free
    (0.0, None),          # beta2 >= 0
    (0.0, 1.0),           # theta
    (0.0, 1.0),           # theta'
    (_LAM_LO, _LAM_HI),   # lambda_short  (trend)
    (_LAM_LO, _LAM_HI),   # lambda_long   (trend)
    (_LAM_LO, _LAM_HI),   # lambda_short' (activity)
    (_LAM_LO, _LAM_HI),   # lambda_long'  (activity)
]


def _seed_params(x: np.ndarray) -> np.ndarray:
    base = float(np.mean(x))
    return np.array([
        max(base * 0.5, _EPS),  # beta0 ~ half mean variance
        0.0,                    # beta1
        max(base * 0.5, _EPS),  # beta2
        0.5, 0.5,               # theta, theta'
        _hl_to_lambda(_HL_SHORT), _hl_to_lambda(_HL_LONG),
        _hl_to_lambda(_HL_SHORT), _hl_to_lambda(_HL_LONG),
    ])


def _fit_full(r: np.ndarray, x: np.ndarray, maxiter: int):
    """Fit all 9 scalars. Returns optimized params or None."""
    p0 = _seed_params(x)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            res = minimize(_logmse, p0, args=(r, x), method="L-BFGS-B",
                           bounds=_BOUNDS, options={"maxiter": maxiter})
    except Exception:
        return None
    if not np.isfinite(res.fun) or res.fun >= 1e11:
        return None
    return res.x.copy()


def _fit_fixed_kernel(r: np.ndarray, x: np.ndarray, maxiter: int):
    """Fallback: freeze the 4 half-lives at seeds, fit only (b0,b1,b2,theta,theta')."""
    lam_s, lam_l = _hl_to_lambda(_HL_SHORT), _hl_to_lambda(_HL_LONG)
    fixed = (lam_s, lam_l, lam_s, lam_l)

    def obj(p5: np.ndarray) -> float:
        return _logmse(np.concatenate([p5, fixed]), r, x)

    p0 = _seed_params(x)[:5]
    bnds = _BOUNDS[:5]
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            res = minimize(obj, p0, method="L-BFGS-B", bounds=bnds,
                           options={"maxiter": maxiter})
    except Exception:
        return None
    if not np.isfinite(res.fun) or res.fun >= 1e11:
        return None
    return np.concatenate([res.x, fixed])


def _last_states(params: np.ndarray, r: np.ndarray) -> tuple[float, float, float, float]:
    """Final EWMA states (R-component sums) to seed the forward simulation."""
    _, _, _, _, _, ls1, ll1, ls2, ll2 = params
    r2 = r * r
    return (
        float(_ewma_path(r, ls1)[-1]),
        float(_ewma_path(r, ll1)[-1]),
        float(_ewma_path(r2, ls2)[-1]),
        float(_ewma_path(r2, ll2)[-1]),
    )


def _forecast(params: np.ndarray, states, resid: np.ndarray, h: int,
              rng, n_paths: int) -> tuple[float, float]:
    """Bootstrap the one-step residuals h steps x n_paths and sum the daily variances."""
    b0, b1, b2, th1, th2, ls1, ll1, ls2, ll2 = params
    s_s1, s_l1, s_s2, s_l2 = states
    e_s1 = np.full(n_paths, s_s1)   # short-trend EWMA state per path
    e_l1 = np.full(n_paths, s_l1)   # long-trend
    e_s2 = np.full(n_paths, s_s2)   # short-activity
    e_l2 = np.full(n_paths, s_l2)   # long-activity
    cumvar = np.zeros(n_paths)
    for _ in range(h):
        R1 = (1.0 - th1) * e_s1 + th1 * e_l1
        R2 = (1.0 - th2) * e_s2 + th2 * e_l2
        var = b0 + b1 * R1 + b2 * np.sqrt(np.maximum(R2, 0.0))
        var = np.maximum(var, _EPS)
        # multiplicative residual bootstrap -> simulated daily realized variance
        mult = resid[rng.integers(0, resid.size, size=n_paths)]
        rv_sim = np.maximum(var * mult, _EPS)
        cumvar += rv_sim
        # simulated return advances the EWMA states (random sign for the trend factor)
        sign = rng.integers(0, 2, size=n_paths) * 2 - 1
        r_sim = sign * np.sqrt(rv_sim)
        e_s1 = ls1 * e_s1 + r_sim
        e_l1 = ll1 * e_l1 + r_sim
        e_s2 = ls2 * e_s2 + rv_sim     # r_sim^2 == rv_sim
        e_l2 = ll2 * e_l2 + rv_sim
    m = float(np.mean(cumvar))
    s = float(np.std(np.log(np.maximum(cumvar, _EPS))))
    return m, s


class GuyonLekeufackPDV(_PerKeyModel):
    """Guyon-Lekeufack / Gazzani-Guyon 4-factor PDV, fit per (ticker, horizon).

    9 scalars fit by scipy L-BFGS-B (log-MSE on daily RV); horizon variance by a
    seeded multiplicative residual bootstrap. Falls back to a fixed-kernel 5-scalar
    fit on optimizer failure; drops the key if even that fails (recorded on
    `self.warnings`).
    """

    name = "GuyonLekeufackPDV"
    needs = [_RV_COL]              # ret column handled in _series (ret_cc / ret_close)
    min_obs = 100
    n_paths = _N_PATHS
    maxiter = 300

    def fit(self, X: pl.DataFrame, y: pl.DataFrame) -> None:
        self.warnings: dict[tuple[str, int], str] = {}
        super().fit(X, y)

    def _fit_one(self, sub: pl.DataFrame, h: int):
        r, x = _series(sub)
        if r.size < self.min_obs:
            return None
        tk = sub["ticker"][0]
        params = _fit_full(r, x, self.maxiter)
        if params is None:
            params = _fit_fixed_kernel(r, x, self.maxiter)
            if params is None:
                self.warnings[(tk, h)] = "dropped: full and fixed-kernel PDV fits both failed"
                return None
            self.warnings[(tk, h)] = "fallback: fixed-kernel 5-scalar fit (full 9-scalar failed)"
        # one-step multiplicative residuals (var scale, mean ~ 1) for the bootstrap
        var = _variance_path(params, r)
        resid = x / np.maximum(var, _EPS)
        resid = resid[np.isfinite(resid) & (resid > 0)]
        if resid.size < 2:
            resid = np.array([1.0])
        states = _last_states(params, r)
        return (params, states, resid)

    def _predict_one(self, state, sub: pl.DataFrame, h: int):
        n = sub.height
        if state is None:
            return np.full(n, np.nan), np.full(n, np.nan)
        params, states, resid = state
        rng = np.random.default_rng(_SEED)
        m, s = _forecast(params, states, resid, h, rng, self.n_paths)
        if not np.isfinite(m) or m <= 0:
            return np.full(n, np.nan), np.full(n, np.nan)
        s = float(np.clip(s, 1e-3, 5.0))
        return np.full(n, m, dtype=float), np.full(n, s, dtype=float)
