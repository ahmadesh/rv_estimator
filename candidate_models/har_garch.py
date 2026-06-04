"""HAR-GARCH — ITER2 catalog model 26 (Track D, Pattern P2).

A two-stage per-(ticker, horizon) model:

  1. **Mean model — direct-h HAR in log space.** Exactly the iter-1 HAR benchmark
     (`_LinearLogHAR`): OLS of ``log(target_var)`` on ``HAR_FEATURES`` (+ intercept).
     This gives the point forecast ``rv_hat = exp(mu + 0.5 * s_t^2)`` (lognormal mean).

  2. **Variance model — GARCH(1,1) / GJR on the HAR log-residuals.** The iter-1 HAR
     uses a *constant* in-sample residual sd ``s``. Here we instead fit a conditional-
     variance model (``arch``) on the train log-residual series
     ``e_t = log(target_var_t) - mu_t`` so the predictive log-sd ``s_t`` is
     **time-varying** — high right after a vol shock, decaying back toward the
     unconditional level. The h-step-ahead GARCH variance forecast from the last
     train origin sets the predictive log-sd used for the whole test block (one
     monthly refit ⇒ one forecast origin per block; never peeks at test residuals).

Why GARCH on the *residual* series rather than on returns? The HAR mean already
removes the predictable trailing-RV signal; what remains is the forecast-error
process, and its volatility clusters (errors are large in turbulent regimes). A
GARCH on those errors is the canonical "light state-space" calibration layer the
catalog asks for (model 26), and is the residual analogue of the heteroskedastic
``HARX-HS`` head (model 25).

GARCH spec (frozen by the catalog, no OOS tuning):
  - ``mean="Zero"`` (residuals are already mean-removed by the HAR OLS),
  - ``vol="GARCH", p=1, o={0|1}, q=1`` — GARCH(1,1), or GJR-GARCH(1,1,1) when the
    asymmetry term improves the **in-sample (train-only)** BIC. The o-order choice
    is made per (ticker,h) on TRAIN data only — never on OOS.
  - ``dist="normal"``. Residuals are rescaled (×100) before fitting because ``arch``
    is ill-conditioned on tiny daily-RV-scale residuals (mirrors realized_garch.py).

Robustness / fallback discipline (mirrors realized_garch.py):
  - Every ``arch`` fit is wrapped in try/except with ``disp="off"``, a finite
    ``options={"maxiter": ...}`` cap, and warnings silenced. ``rescale=False`` with
    an explicit ×100 scale.
  - If the GARCH fit fails / is non-finite / non-stationary, we FALL BACK to the
    plain HAR constant in-sample residual sd (``s`` = std of train residuals) — a
    constant-variance forecast — and count it. A single non-convergent (ticker,h)
    therefore NEVER aborts the run and still produces valid predictions.
  - The mean OLS itself never fails (lstsq); only the variance layer can fall back.

Per-row sigma: the base ``_PerKeyModel.predict`` applies the log-sd ``s`` elementwise,
so returning a length-n ``s`` array (here constant within a test block — the single
h-step GARCH forecast) needs no harness change.

Library: arch 8.0.0. Seed: numpy default (the GARCH forecast is analytic, no MC).
"""

from __future__ import annotations

import warnings

import numpy as np
import polars as pl

from rv_eval.features import HAR_FEATURES
from rv_eval.model_contract import _PerKeyModel

_SCALE = 100.0          # arch is ill-conditioned on tiny RV-scale residuals; fit in scaled space
_MAXITER = 200          # finite cap on the arch optimiser
_S_FLOOR = 1e-3         # floor on the predictive log-sd
_S_CEIL = 5.0           # ceiling on the predictive log-sd (guard pathological forecasts)


def _ols_log_mean(sub: pl.DataFrame, needs: list[str]):
    """Direct-h log-OLS HAR mean. Returns (beta, residuals, const_s)."""
    x = sub.select(needs).to_numpy().astype(float)
    A = np.column_stack([np.ones(x.shape[0]), x])
    y = np.log(sub["target_var"].to_numpy().astype(float))
    beta, *_ = np.linalg.lstsq(A, y, rcond=None)
    resid = y - A @ beta
    s = float(np.std(resid, ddof=A.shape[1])) if resid.size > A.shape[1] else 0.5
    return beta, resid, max(s, _S_FLOOR)


def _fit_garch_on_resid(resid: np.ndarray, h: int):
    """Fit GARCH(1,1) (and GJR) on the residual series; return the h-step-ahead log-sd.

    The arch h-step variance forecast is for the *one-step* (daily) residual variance
    at the forecast origin + h. The HAR target/residual is already a direct-h object,
    so we use the forecast-origin conditional variance as the predictive variance of
    the (single) direct-h residual: we take the variance forecast at the last horizon
    step (the variance that applies to the test block sitting h days ahead of train_end).

    Returns (s_t, kind) or None on failure.
    """
    from arch.univariate import arch_model

    r = resid.astype(float) * _SCALE
    if not np.all(np.isfinite(r)) or r.size < 50 or np.std(r) < 1e-8:
        return None

    best = None
    for o in (0, 1):                     # GARCH(1,1) vs GJR-GARCH(1,1,1); pick by TRAIN BIC
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                am = arch_model(r, mean="Zero", vol="GARCH", p=1, o=o, q=1,
                                dist="normal", rescale=False)
                fr = am.fit(disp="off", show_warning=False,
                            options={"maxiter": _MAXITER})
        except Exception:
            continue
        bic = getattr(fr, "bic", np.inf)
        if not np.isfinite(bic):
            continue
        if best is None or bic < best[0]:
            best = (bic, fr, o)

    if best is None:
        return None

    _, fr, o = best
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            fc = fr.forecast(horizon=h, reindex=False)
        # forecast.variance: (n_obs_used, h); last origin row, h-step-ahead variance.
        var_h = float(np.asarray(fc.variance)[-1, -1]) / (_SCALE * _SCALE)
    except Exception:
        return None
    if not np.isfinite(var_h) or var_h <= 0:
        return None
    s_t = float(np.sqrt(var_h))
    kind = "GJR-GARCH(1,1,1)" if o == 1 else "GARCH(1,1)"
    return s_t, kind


class HARGARCH(_PerKeyModel):
    """HAR mean + GARCH(1,1)/GJR conditional-variance layer on the log-residuals.

    Per (ticker, horizon): direct-h log-OLS HAR mean, then an ``arch`` GARCH/GJR fit
    on the HAR log-residuals giving a time-varying predictive log-sd ``s_t``. Falls
    back to the HAR constant in-sample residual sd when the GARCH fit fails; the count
    and which keys fell back are recorded on ``self.fallbacks`` for the model card.
    """

    name = "HAR-GARCH"
    needs = HAR_FEATURES
    min_obs = 100

    def fit(self, X: pl.DataFrame, y: pl.DataFrame) -> None:
        self.fallbacks: dict[tuple[str, int], str] = {}
        self.fit_specs: dict[tuple[str, int], str] = {}
        super().fit(X, y)

    def _fit_one(self, sub: pl.DataFrame, h: int):
        sub = sub.sort("date")
        tk = sub["ticker"][0]
        beta, resid, const_s = _ols_log_mean(sub, self.needs)

        res = _fit_garch_on_resid(resid, h)
        if res is None:
            self.fallbacks[(tk, h)] = "fallback: constant HAR residual sd (GARCH fit failed)"
            s_t = const_s
            self.fit_specs[(tk, h)] = "constant-sd (fallback)"
        else:
            s_t, kind = res
            s_t = float(np.clip(s_t, const_s * 0.1, const_s * 10.0))  # tether to OLS resid scale
            self.fit_specs[(tk, h)] = kind
        s_t = float(np.clip(s_t, _S_FLOOR, _S_CEIL))
        return (beta, s_t)

    def _predict_one(self, state, sub: pl.DataFrame, h: int):
        beta, s_t = state
        x = sub.select(self.needs).to_numpy().astype(float)
        A = np.column_stack([np.ones(x.shape[0]), x])
        mu = A @ beta                                  # NaN propagates where a feature is null
        m = np.exp(mu + 0.5 * s_t * s_t)               # lognormal mean
        return m, np.full(sub.height, s_t, dtype=float)
