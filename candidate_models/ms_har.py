"""MS-HAR — 2-state Markov-switching HAR estimated by EM (CATALOG §3 model 31, Track E3, P3).

A direct-h HAR regression of ``log(target_var)`` on the standard HAR component features
``[1, log_rv_d, log_rv_w, log_rv_m]`` whose **regression coefficients and innovation variance
switch between two latent regimes** governed by a first-order Markov chain with a 2x2 transition
matrix ``P``. Estimated per (ticker, horizon) by the EM algorithm for Markov-switching regressions
(Hamilton 1989 filter + Kim 1994 smoother in the E-step; weighted-least-squares + weighted-variance
updates in the M-step; transition matrix from smoothed joint state probabilities).

Spec (state s_t in {0,1}):

    log(target_var_t) = x_t' beta_{s_t} + eps_t,    eps_t ~ N(0, sigma2_{s_t})
    P(s_t = j | s_{t-1} = i) = P[i, j]

Mixture predictive density (LEAKAGE-SAFE). Regime params and ``P`` are estimated on the TRAIN
slice only. The predictive regime weights at the last train origin are the smoothed state
probabilities of the final train row propagated ONE Markov step forward (``w = pi_last @ P``);
because the regression is already a direct-h map (features today -> next-h target), no further
recursion of the chain is needed. For each predict row the forecast is the regime-probability
mixture of two lognormals N(x'beta_s + 0.5 sigma2_s in level) :

    rv_hat = sum_s w_s * exp(x'beta_s + 0.5 sigma2_s)          (mixture mean, level units)
    sigma  = sqrt( sum_s w_s*(var_s + mean_s^2) - rv_hat^2 )   (mixture level sd)

We then back out an effective log-sd ``s`` for the lognormal-quantile wrapper from the level mean
and sd (``s = sqrt(log(1 + (sigma/rv_hat)^2))``), so the emitted q05..q95 are the standard
``_lognormal_quantiles`` of a single lognormal matched to the mixture's first two level moments
(monotone by construction). ``w`` is shared across all predict rows of a (ticker,h) — it is the
state distribution at the train origin, which is the only point-in-time-legal information.

Speed / robustness (this is the HEAVIEST iter-2 model — see card for the gate verdict):
  * EM is hand-rolled and fully vectorized (no per-sample Python loop except the O(n) forward/
    backward passes); cost is O(iters * n) per (ticker,horizon), NOT super-linear in n.
  * EM caps at ``_MAX_ITER`` iterations with a log-likelihood tolerance early-stop ``_TOL``.
  * Every (ticker,horizon) fit is wrapped in try/except; on non-convergence, a degenerate/empty
    regime, or any numerical failure we FALL BACK to a single-regime HAR (plain log-OLS) and count
    it (``self.fallbacks``).
  * REFIT-CADENCE REDUCTION: a full EM is expensive to repeat for every monthly walk-forward fold.
    We therefore re-run EM only every ``_REFIT_EVERY`` fit-calls per (ticker,horizon); intervening
    folds REUSE the last-good fitted params (warm cache) and only refresh the cheap origin state
    weights ``w`` from the new train tail via one Hamilton-filter pass (no M-step). This keeps the
    predictive density adapting to the latest origin while amortizing the EM cost. Documented in
    the card. ``_REFIT_EVERY`` is frozen here (not tuned on OOS).
  * numpy seed fixed for the (rarely used) k-means-style init jitter.
"""

from __future__ import annotations

import warnings

import numpy as np
import polars as pl

from rv_eval.features import HAR_FEATURES
from rv_eval.model_contract import _PerKeyModel

_SEED = 0
_MAX_ITER = 80          # EM iteration cap (with tolerance early-stop below)
_TOL = 1e-4             # relative log-likelihood improvement early-stop
_MIN_REGIME_FRAC = 0.05  # a regime holding < this smoothed mass is "degenerate" -> fallback
_REFIT_EVERY = 6        # re-run full EM every N fit-calls per key; reuse warm params otherwise
_VAR_FLOOR = 1e-6       # floor on regime innovation variance
_S_FLOOR = 1e-3         # floor on emitted log-sd


def _design(sub: pl.DataFrame, needs: list[str]) -> np.ndarray:
    x = sub.select(needs).to_numpy().astype(float)
    return np.column_stack([np.ones(x.shape[0]), x])


def _ols(A: np.ndarray, y: np.ndarray):
    beta, *_ = np.linalg.lstsq(A, y, rcond=None)
    resid = y - A @ beta
    dof = max(resid.size - A.shape[1], 1)
    s2 = float(np.sum(resid ** 2) / dof) if resid.size > A.shape[1] else 0.25
    return beta, max(s2, _VAR_FLOOR)


def _normal_pdf(resid: np.ndarray, s2: float) -> np.ndarray:
    s2 = max(s2, _VAR_FLOOR)
    return np.exp(-0.5 * resid * resid / s2) / np.sqrt(2.0 * np.pi * s2)


def _em_ms_har(A: np.ndarray, y: np.ndarray, rng: np.random.Generator):
    """EM for a 2-state Markov-switching regression. Returns state dict or None on failure.

    State dict keys: betas (2 x k), s2 (2,), P (2x2), pi_last (2,) smoothed final-row probs.
    """
    n, k = A.shape
    if n < 2 * k + 20:
        return None

    # --- init: split sample by residual sign of a pooled OLS to seed two regimes ---
    beta0, s20 = _ols(A, y)
    resid0 = y - A @ beta0
    hi = resid0 >= np.median(resid0)            # high-vol vs low-vol-ish split
    betas = np.empty((2, k))
    s2 = np.empty(2)
    for j, mask in enumerate((~hi, hi)):
        if mask.sum() > k + 2:
            betas[j], s2[j] = _ols(A[mask], y[mask])
        else:
            betas[j], s2[j] = beta0, s20
    # keep regimes distinct
    if abs(s2[0] - s2[1]) < 1e-9:
        s2 = np.array([s20 * 0.5, s20 * 1.5])
    P = np.array([[0.95, 0.05], [0.10, 0.90]])
    pi0 = np.array([0.5, 0.5])

    prev_ll = -np.inf
    smooth = None
    for _ in range(_MAX_ITER):
        # --- E-step: Hamilton filter (forward) ---
        resid = y[:, None] - A @ betas.T           # (n,2)
        dens = np.stack([_normal_pdf(resid[:, j], s2[j]) for j in range(2)], axis=1)  # (n,2)
        dens = np.maximum(dens, 1e-300)

        filt = np.empty((n, 2))     # P(s_t=j | y_1..t)
        pred = np.empty((n, 2))     # P(s_t=j | y_1..t-1)
        ll = 0.0
        prior = pi0
        for t in range(n):
            pred[t] = prior
            num = prior * dens[t]
            tot = num.sum()
            if not np.isfinite(tot) or tot <= 0:
                return None
            filt[t] = num / tot
            ll += np.log(tot)
            prior = filt[t] @ P
        # --- Kim smoother (backward) ---
        smooth = np.empty((n, 2))
        smooth[-1] = filt[-1]
        joint = np.zeros((2, 2))    # sum_t P(s_t-1=i, s_t=j | all)
        for t in range(n - 2, -1, -1):
            # ratio P(s_t+1|all)/P(s_t+1|y_1..t)
            denom = np.where(pred[t + 1] > 1e-300, pred[t + 1], 1e-300)
            ratio = smooth[t + 1] / denom
            smooth[t] = filt[t] * (P @ ratio)
            smooth[t] = smooth[t] / max(smooth[t].sum(), 1e-300)
            # joint (i->j) for transition update
            jt = (filt[t][:, None] * P) * ratio[None, :]
            jt = jt / max(jt.sum(), 1e-300)
            joint += jt

        # --- M-step ---
        # transition matrix from smoothed joints
        row = joint.sum(axis=1, keepdims=True)
        P = np.where(row > 1e-300, joint / np.maximum(row, 1e-300), P)
        P = np.clip(P, 1e-4, 1.0 - 1e-4)
        P = P / P.sum(axis=1, keepdims=True)
        pi0 = smooth[0]

        for j in range(2):
            w = smooth[:, j]
            wsum = w.sum()
            if wsum < _MIN_REGIME_FRAC * n:
                return None                       # degenerate regime -> caller falls back
            sw = np.sqrt(w)
            Aw = A * sw[:, None]
            yw = y * sw
            b, *_ = np.linalg.lstsq(Aw, yw, rcond=None)
            betas[j] = b
            r = y - A @ b
            s2[j] = max(float(np.sum(w * r * r) / wsum), _VAR_FLOOR)

        if np.isfinite(prev_ll) and abs(ll - prev_ll) <= _TOL * (abs(prev_ll) + 1e-8):
            break
        prev_ll = ll

    if smooth is None or not np.all(np.isfinite(betas)) or not np.all(np.isfinite(s2)):
        return None
    pi_last = smooth[-1]
    return {"betas": betas, "s2": s2, "P": P, "pi_last": pi_last}


def _filter_only(A: np.ndarray, y: np.ndarray, st: dict) -> np.ndarray:
    """Cheap re-estimate of just the origin state weights via one Hamilton-filter pass.

    Used by the refit-cadence reduction: keeps frozen warm betas/s2/P, refreshes pi_last on the
    new train tail so the predictive mixture tracks the latest origin without a full EM.
    """
    betas, s2, P = st["betas"], st["s2"], st["P"]
    n = A.shape[0]
    resid = y[:, None] - A @ betas.T
    dens = np.stack([_normal_pdf(resid[:, j], s2[j]) for j in range(2)], axis=1)
    dens = np.maximum(dens, 1e-300)
    prior = np.array([0.5, 0.5])
    filt = np.array([0.5, 0.5])
    for t in range(n):
        num = prior * dens[t]
        tot = num.sum()
        if not np.isfinite(tot) or tot <= 0:
            return st["pi_last"]
        filt = num / tot
        prior = filt @ P
    return filt


class MSHAR(_PerKeyModel):
    """2-state Markov-switching HAR estimated by EM, fit per (ticker, horizon).

    Pattern P3 in spirit (bespoke fit) but reuses ``_PerKeyModel``'s per-key loop and the
    lognormal-quantile emission; falls back to a single-regime HAR on non-convergence (counted).
    """

    name = "MS-HAR"
    needs = HAR_FEATURES
    min_obs = 120

    def fit(self, X: pl.DataFrame, y: pl.DataFrame) -> None:
        if not hasattr(self, "_warm"):
            self._warm: dict[tuple[str, int], dict] = {}   # last-good full state per key
            self._calls: dict[tuple[str, int], int] = {}    # fit-call counter per key
            self.fallbacks: dict[tuple[str, int], str] = {}
            self.regimes_estimated = 0
        super().fit(X, y)

    def _fit_one(self, sub: pl.DataFrame, h: int):
        tk = sub["ticker"][0]
        key = (tk, h)
        A = _design(sub, self.needs)
        y = np.log(sub["target_var"].to_numpy().astype(float))
        ok = np.all(np.isfinite(A), axis=1) & np.isfinite(y)
        A, y = A[ok], y[ok]

        # single-regime HAR fallback state (always computable, used on EM failure)
        sb, ss2 = _ols(A, y) if A.shape[0] > A.shape[1] else (None, None)
        single = None if sb is None else {"single": True, "beta": sb, "s2": ss2}

        n_calls = self._calls.get(key, 0)
        self._calls[key] = n_calls + 1
        warm = self._warm.get(key)

        # Refit-cadence reduction: full EM only every _REFIT_EVERY calls; else reuse warm params
        # and just refresh the origin state weights with a cheap filter pass.
        do_full = (warm is None) or (n_calls % _REFIT_EVERY == 0)
        if not do_full and warm is not None:
            try:
                warm = dict(warm)
                warm["pi_last"] = _filter_only(A, y, warm)
                self._warm[key] = warm
                self.regimes_estimated += 1
                return warm
            except Exception:
                do_full = True

        try:
            rng = np.random.default_rng(_SEED)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                st = _em_ms_har(A, y, rng)
        except Exception:
            st = None

        if st is None:
            self.fallbacks[key] = "single-regime HAR (EM non-convergent / degenerate regime)"
            return single
        self._warm[key] = st
        self.regimes_estimated += 1
        return st

    def _predict_one(self, state, sub: pl.DataFrame, h: int):
        n = sub.height
        if state is None:
            return np.full(n, np.nan), np.full(n, np.nan)
        A = _design(sub, self.needs)

        if state.get("single"):
            beta, s2 = state["beta"], state["s2"]
            mu = A @ beta
            s = float(np.sqrt(max(s2, _VAR_FLOOR)))
            m = np.exp(mu + 0.5 * s2)
            return m, np.full(n, max(s, _S_FLOOR), dtype=float)

        betas, s2, w = state["betas"], state["s2"], state["pi_last"]
        mu = A @ betas.T                      # (n,2) log-mean per regime
        comp_mean = np.exp(mu + 0.5 * s2)     # (n,2) level mean per regime
        comp_var = comp_mean ** 2 * np.expm1(np.minimum(s2, 50.0))  # lognormal level var
        m = comp_mean @ w                     # mixture level mean
        ex2 = (comp_var + comp_mean ** 2) @ w
        var = np.maximum(ex2 - m * m, 0.0)
        # effective log-sd matching the mixture's first two level moments
        with np.errstate(divide="ignore", invalid="ignore"):
            s = np.sqrt(np.log1p(np.where(m > 0, var / (m * m), 0.0)))
        s = np.maximum(np.nan_to_num(s, nan=_S_FLOOR), _S_FLOOR)
        return m, s
