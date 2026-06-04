"""Threshold-HAR — regime-switching HAR with HARD threshold regimes (CATALOG §3 model 29).

A self-exciting threshold (TAR-style) HAR: instead of one set of HAR coefficients, we fit
*separate* HAR-X coefficients in each of two HARD regimes defined by an **observable state**,
and `predict` routes each row to its regime's coefficients. This captures the well-documented
fact that RV persistence and the IV->RV mapping differ sharply between calm and stressed
markets (e.g. higher persistence / different leverage in high-vol regimes).

== The regime variable (THE critical leakage risk for this model) ==
The split MUST use an observable that `predict` actually receives in X. We use the **VIX
expanding percentile** (point-in-time rank of `vix` within each ticker's own history up to and
including the current date). This is a trailing/expanding feature, so — exactly like the
HAR-CJ roll-means — it is built ONCE on the FULL series from `inputs.parquet` and JOINED by
(ticker, date) via `_AttachMixin`, never recomputed on the one-month predict slice. We do NOT
use `post_shock` (it lives in targets.parquet, not X; CATALOG §4).

  regime = HIGH  if  vix_epctile >= THRESHOLD  else  LOW       (THRESHOLD = 0.5, frozen)

THRESHOLD = 0.5 (the median of the expanding percentile) is fixed by the spec — a hard split
into the lower- and upper-half VIX-history regimes. No OOS peeking, no grid tuned on test.

== Fitting ==
Per (ticker, horizon): split the TRAIN rows by regime and fit a plain log-OLS of
log(target_var) on `HAR_FEATURES + IV_FEATURES` (+ intercept) within each regime. A regime with
fewer than `_MIN_REGIME_OBS` train rows for that (ticker, horizon) FALLS BACK to the pooled /
all-regime HAR fit (fit on every train row regardless of regime) — never errors, never imputes.
The pooled fit is always computed and is also the route for any predict row whose features are
present but whose regime had no usable train fit.

`predict` evaluates each row with its own regime's beta; rows in a sparse regime use the pooled
beta. Quantiles come from the per-regime log-residual sd via `_lognormal_quantiles`.
"""

from __future__ import annotations

import numpy as np
import polars as pl

from rv_eval import config as C
from rv_eval.features import HAR_FEATURES, IV_FEATURES
from candidate_models._base_v2 import _AttachMixin
from rv_eval.model_contract import _PerKeyModel

_KEYS = ["ticker", "date"]
_REGIME_COL = "vix_epctile"          # expanding percentile of vix, point-in-time
_THRESHOLD = 0.5                     # frozen hard threshold (median of expanding percentile)
_MIN_REGIME_OBS = 40                 # below this a regime falls back to the pooled HAR fit
_BASE_FEATURES = HAR_FEATURES + IV_FEATURES


def _epctile_panel(inputs: pl.DataFrame) -> pl.DataFrame:
    """Full-history expanding percentile of `vix` per ticker (point-in-time, leak-safe).

    For each (ticker, date) row the value is the fraction of that ticker's at-or-before-date
    `vix` observations that are <= today's `vix` — i.e. an expanding (not rolling) rank in
    [0, 1]. Computed once over each ticker's whole series so a given (ticker, date) always gets
    the same value regardless of the fold slice it later lands in. Uses only at-or-before-date
    rows -> no leakage. `vix` is common across tickers but ranked per ticker keeps the regime
    definition consistent with the per-(ticker,horizon) fit loop.
    """
    return (
        inputs.sort("ticker", "date")
        # Expanding fraction of at-or-before-date rows with vix <= current vix, per ticker.
        .with_columns(
            pl.col("vix")
            .map_batches(_expanding_pctile, return_dtype=pl.Float64)
            .over("ticker")
            .alias(_REGIME_COL)
        )
        .select(_KEYS + [_REGIME_COL])
    )


def _expanding_pctile(vix: pl.Series) -> pl.Series:
    """Expanding fraction of prior+current values <= each value (point-in-time percentile)."""
    v = vix.to_numpy().astype(float)
    n = v.size
    out = np.empty(n, dtype=float)
    for i in range(n):
        window = v[: i + 1]
        finite = window[np.isfinite(window)]
        if finite.size == 0 or not np.isfinite(v[i]):
            out[i] = 0.5  # neutral when vix missing -> deterministic regime assignment
        else:
            out[i] = float(np.mean(finite <= v[i]))
    return pl.Series(out)


def _fit_ols(sub: pl.DataFrame):
    """Plain log-OLS of log(target_var) on _BASE_FEATURES (+intercept). Returns (beta, s) or None."""
    sub = sub.drop_nulls(_BASE_FEATURES + ["target_var"]).filter(pl.col("target_var") > 0)
    if sub.height < 2:
        return None
    x = sub.select(_BASE_FEATURES).to_numpy().astype(float)
    A = np.column_stack([np.ones(x.shape[0]), x])
    yl = np.log(sub["target_var"].to_numpy().astype(float))
    beta, *_ = np.linalg.lstsq(A, yl, rcond=None)
    resid = yl - A @ beta
    s = float(np.std(resid, ddof=A.shape[1])) if resid.size > A.shape[1] else 0.5
    return (beta, max(s, 1e-3))


class ThresholdHAR(_AttachMixin, _PerKeyModel):
    """Two-regime (hard threshold) HAR-X, regime = VIX expanding-percentile >= 0.5.

    Per (ticker, horizon): one log-OLS in the LOW-vol regime, one in the HIGH-vol regime, plus a
    pooled all-regime fit used both as the fallback for a sparse regime and to route any row whose
    regime lacked a usable fit. The number of (ticker, horizon, regime) cells that fell back to
    pooled is recorded on `self.fallbacks` for the model card.
    """

    name = "Threshold-HAR"
    needs = _BASE_FEATURES + [_REGIME_COL]
    min_obs = 100

    def _derive(self, src: pl.DataFrame) -> pl.DataFrame:
        return _epctile_panel(src)

    def fit(self, X: pl.DataFrame, y: pl.DataFrame) -> None:
        self.fallbacks: int = 0
        self.regime_counts: dict[tuple[str, int, str], int] = {}
        super().fit(X, y)   # _AttachMixin.fit -> attaches regime col -> _PerKeyModel.fit

    def _fit_one(self, sub: pl.DataFrame, h: int):
        # `sub` already has nulls in needs (incl. regime col) + target_var dropped by base.
        tk = sub["ticker"][0]
        pooled = _fit_ols(sub)
        if pooled is None:
            return None
        reg = sub[_REGIME_COL].to_numpy().astype(float)
        is_high = reg >= _THRESHOLD
        low_sub = sub.filter(pl.Series(~is_high))
        high_sub = sub.filter(pl.Series(is_high))

        def _regime_fit(rsub, label):
            self.regime_counts[(tk, h, label)] = rsub.height
            if rsub.height >= _MIN_REGIME_OBS:
                fit = _fit_ols(rsub)
                if fit is not None:
                    return fit
            self.fallbacks += 1
            return pooled  # sparse / failed regime -> pooled all-regime fit

        return {
            "low": _regime_fit(low_sub, "low"),
            "high": _regime_fit(high_sub, "high"),
            "pooled": pooled,
        }

    def _design(self, sub: pl.DataFrame) -> np.ndarray:
        x = sub.select(_BASE_FEATURES).to_numpy().astype(float)
        return np.column_stack([np.ones(x.shape[0]), x])

    def _predict_one(self, state, sub: pl.DataFrame, h: int):
        n = sub.height
        if state is None:
            return np.full(n, np.nan), np.full(n, np.nan)
        A = self._design(sub)
        reg = sub[_REGIME_COL].to_numpy().astype(float)
        # default neutral (->low) when regime missing; deterministic.
        is_high = np.where(np.isfinite(reg), reg >= _THRESHOLD, False)

        beta_low, s_low = state["low"]
        beta_high, s_high = state["high"]
        beta = np.where(is_high[:, None], beta_high[None, :], beta_low[None, :])
        s_row = np.where(is_high, s_high, s_low)

        mu = np.einsum("ij,ij->i", A, beta)   # row-wise dot with its regime's beta
        m = np.exp(mu + 0.5 * s_row * s_row)   # lognormal mean
        return m, s_row.astype(float)
