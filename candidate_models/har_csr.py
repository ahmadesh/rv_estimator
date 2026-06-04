"""HAR-CSR — complete-subset regression HAR (ITER2 catalog §3, model 20, Track B / P2).

Complete-subset regression (Elliott-Gargano-Timmermann 2013; HAR-CSR, Elsevier
S0957417421008356): instead of fitting one OLS on all `K` regressors, fit ALL OLS
models that use exactly `k` of the `K` regressors (each an intercept + that k-subset),
and AVERAGE their forecasts. The equal-weighted average over the complete set of
k-subsets is a shrinkage device — it dominates the single full-K OLS out-of-sample by
trading a little bias for a large variance reduction, with no tuning of penalty
strengths.

== Feature set (the curated K=8 "HAR" regressors) ==
All EIGHT are pass-through columns already produced by `features.build_features`, so
they are present on X at fit/predict with NO derived rolling-window joins required (the
rolling means were already built once, point-in-time, on the full series inside
build_features). No `_AttachMixin` is needed and there is no leakage risk from the
predict slice:

    log_rv_d, log_rv_w, log_rv_m   — the three classic HAR lags (day / week / month)
    rs_minus_5d, jump_5d           — downside-semivariance + jump (RV decomposition)
    log_iv, vix                    — option-implied variance level + the VIX
    sqrt_rq                        — realized-quarticity (HAR-Q measurement-error term)

== Subset scheme (FROZEN by the catalog spec, not by OOS peeking) ==
k = 4 out of K = 8  =>  C(8,4) = 70 complete subsets, EXACTLY the catalog cap (≤70).
So we enumerate ALL 70 subsets — no random sampling, no seed-dependent draw, the full
complete-subset estimator. (Guard: if a future feature-set change pushed the subset
count above `_MAX_SUBSETS`, we would fall back to a seeded random sample of that many
subsets; with K=8,k=4 that branch is never taken.) The subset list is identical across
every (ticker, horizon) and every fold — fixed at import time.

== Fit / predict (Pattern P2 over `_PerKeyModel`) ==
Per (ticker, horizon) we run, for each of the 70 subsets, a plain log-OLS of
`log(target_var)` on `[1] + subset` (the same machinery as `_LinearLogHAR`). Each
subset s gives a lognormal-mean forecast `m_s = exp(mu_s + 0.5 * sigma_s^2)`; the
HAR-CSR point forecast is the equal-weight average `mean_s m_s` (averaging in level
space, the QLIKE-optimal mean target, consistent with the benchmarks). The predictive
log-sd `s` is taken as the mean of the per-subset in-sample log-residual sds — a simple,
finite proxy used only for the lognormal quantile spread. rv_hat is finite and > 0;
quantiles come from `_lognormal_quantiles`.

Rows with any null among the 8 features (none expected — all pass-through, fully
populated after the warm-up handled inside build_features) propagate NaN and are
dropped by the base `predict` filter.
"""

from __future__ import annotations

from itertools import combinations

import numpy as np
import polars as pl

from rv_eval.model_contract import _PerKeyModel

# Curated K=8 HAR regressor set — all pass-through columns from build_features.
_FEATURES = [
    "log_rv_d", "log_rv_w", "log_rv_m",   # classic HAR lags
    "rs_minus_5d", "jump_5d",             # downside semivariance + jump
    "log_iv", "vix",                      # implied-variance level + VIX
    "sqrt_rq",                            # realized quarticity (HAR-Q term)
]
_K_SUBSET = 4                  # subset size k
_MAX_SUBSETS = 70             # catalog cap (C(8,4) == 70 -> full enumeration, no sampling)
_SEED = 0                     # only used if a feature-set change forced random sampling


def _build_subsets() -> list[tuple[int, ...]]:
    """All k-of-K column-index subsets, capped at `_MAX_SUBSETS` (seeded sample if over)."""
    allsub = list(combinations(range(len(_FEATURES)), _K_SUBSET))
    if len(allsub) <= _MAX_SUBSETS:
        return allsub                     # C(8,4) == 70 -> complete enumeration
    rng = np.random.default_rng(_SEED)    # never taken for K=8, k=4; kept for robustness
    idx = rng.choice(len(allsub), size=_MAX_SUBSETS, replace=False)
    return [allsub[i] for i in sorted(idx.tolist())]


_SUBSETS = _build_subsets()               # frozen at import (same for every key / fold)


class HARCSR(_PerKeyModel):
    """Complete-subset-regression HAR: average the OLS forecasts over all k-of-K subsets."""

    name = "HAR-CSR"
    needs = _FEATURES
    min_obs = 100                          # enough rows for a stable 5-coef OLS per subset

    def _fit_one(self, sub: pl.DataFrame, h: int):
        Xm = sub.select(self.needs).to_numpy().astype(float)   # (n, K)
        ylog = np.log(sub["target_var"].to_numpy().astype(float))
        n = Xm.shape[0]
        betas: list[np.ndarray] = []
        s_list: list[float] = []
        for cols in _SUBSETS:
            A = np.column_stack([np.ones(n), Xm[:, list(cols)]])   # intercept + k features
            beta, *_ = np.linalg.lstsq(A, ylog, rcond=None)
            resid = ylog - A @ beta
            dof = A.shape[1]
            s = float(np.std(resid, ddof=dof)) if resid.size > dof else float(np.std(resid))
            if not np.isfinite(s) or s <= 0:
                s = 0.5
            betas.append(beta)
            s_list.append(max(s, 1e-3))
        s_bar = float(np.mean(s_list))
        return (betas, max(s_bar, 1e-3))

    def _predict_one(self, state, sub: pl.DataFrame, h: int):
        betas, s = state
        Xm = sub.select(self.needs).to_numpy().astype(float)   # (n, K); NaN -> NaN forecast
        n = Xm.shape[0]
        acc = np.zeros(n)                                       # running sum of subset means
        for beta, cols in zip(betas, _SUBSETS):
            A = np.column_stack([np.ones(n), Xm[:, list(cols)]])
            mu = A @ beta
            acc += np.exp(mu + 0.5 * s * s)                    # per-subset lognormal mean
        m = acc / len(betas)                                   # equal-weight complete-subset avg
        return m, np.full(n, s, dtype=float)
