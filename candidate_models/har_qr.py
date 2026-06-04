"""HAR-QR — direct quantile-regression HAR (iteration-2 model 27).

ITER2_MODEL_CATALOG.md §3, Track D / Pattern P3 over `_base_v2._QuantileModel`.

Unlike every other HAR model in this repo, HAR-QR does **not** assume a lognormal
predictive law and does **not** call `_lognormal_quantiles`. It fits, per
(ticker, horizon), one linear **quantile regression** for each target quantile
``tau in C.QUANTILES = {0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95}`` of the realized
variance `target_var` on the HAR feature block, and emits the seven quantiles
DIRECTLY. This optimises the pinball loss / interval coverage by construction rather
than backing intervals out of a parametric mean+sigma.

== Feature block ==
The A-feature set (`HAR_FEATURES = [log_rv_d, log_rv_w, log_rv_m]`), all produced by
`build_features` and already present on X. These are pass-through columns (no trailing
window / shift computed here), so no `_AttachMixin._derive` join is needed.

== Target space ==
The regressions predict `target_var` in **level (variance) units** directly (not log),
so the emitted quantiles are already in `target_var` units. A linear quantile fit in
level space can occasionally produce a non-positive low quantile or a non-positive
median; we clip a tiny positive floor (`_VAR_FLOOR`) so every emitted quantile and
`rv_hat` stay finite and strictly positive (the contract).

== Monotonicity (critical) ==
Quantile regressions fit independently per tau can CROSS (a higher-tau prediction
below a lower-tau one on some rows). The base `_QuantileModel.predict` applies the
standard rearrangement fix (`np.maximum.accumulate` across the ordered Q_COLS grid),
guaranteeing q05<=q10<=q25<=q50<=q75<=q90<=q95 on EVERY row. We additionally record
the per-fit crossing rate on `self.warnings` for the card.

== Point forecast & spread ==
`rv_hat` = q50 (the catalog's "mean proxy"; median is the robust central forecast for
a directly-fit quantile model), floored positive. `sigma` = a positive spread proxy
`(q90 - q10) / 2.563` — the Gaussian-equivalent sd implied by the 10/90 interval width
(z_0.90 - z_0.10 = 2.5631), floored positive for downstream sizing.

== Hyperparameters ==
`sklearn.linear_model.QuantileRegressor` with a small fixed L1 penalty `alpha`
(BY-CONSTRUCTION, not OOS-tuned) and `solver="highs"`. The penalty is frozen across
all (ticker, horizon) keys; it is a mild regulariser for the ~3-feature design, not a
quantity selected against any out-of-sample signal. `fit_intercept=True`. Seed is
irrelevant (the highs LP solver is deterministic) but recorded for completeness.
"""

from __future__ import annotations

import warnings

import numpy as np
import polars as pl
from sklearn.linear_model import QuantileRegressor

from candidate_models._base_v2 import _QuantileModel
from rv_eval import config as C
from rv_eval.features import HAR_FEATURES
from rv_eval.model_contract import Q_COLS

_VAR_FLOOR = 1e-12          # positive floor for quantiles / rv_hat in target_var (variance) units
# z_0.90 - z_0.10 = 2.5631 -> (q90 - q10) / 2.563 is the Gaussian-equivalent sd of the 10/90 band.
_IQ_Z = 2.563
_SIGMA_FLOOR = 1e-8


class HARQR(_QuantileModel):
    """Per-(ticker, horizon) direct quantile-regression HAR (model 27)."""

    name = "HAR-QR"
    needs = list(HAR_FEATURES)
    horizons = C.HORIZONS
    min_obs = 100                 # enough rows to fit 7 quantile regressions of ~3 features
    quantiles = C.QUANTILES       # tau grid, aligned 1:1 with Q_COLS
    _ALPHA = 1e-3                 # fixed L1 penalty (by construction, NOT OOS-tuned)
    _SEED = 0

    def fit(self, X: pl.DataFrame, y: pl.DataFrame) -> None:
        # crossing-rate diagnostics per (ticker, horizon) for the card
        self.warnings: dict[tuple[str, int], str] = {}
        super().fit(X, y)

    def _fit_one(self, sub: pl.DataFrame, h: int):
        """Fit one QuantileRegressor per target tau on the HAR block (level-space target_var)."""
        sub = sub.sort("date")
        Xm = sub.select(self.needs).to_numpy().astype(float)
        yv = sub["target_var"].to_numpy().astype(float)
        models: list[QuantileRegressor] = []
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            for tau in self.quantiles:
                qr = QuantileRegressor(
                    quantile=float(tau),
                    alpha=self._ALPHA,
                    fit_intercept=True,
                    solver="highs",
                )
                qr.fit(Xm, yv)
                models.append(qr)
        # in-sample crossing rate (before rearrangement) for the card
        preds = np.column_stack([m.predict(Xm) for m in models])
        cross_rate = float(np.mean(np.any(np.diff(preds, axis=1) < 0, axis=1)))
        tk = sub["ticker"][0]
        self.warnings[(tk, h)] = f"crossing_rate={cross_rate:.4f}, n={sub.height}"
        return models

    def _predict_q(self, state, sub: pl.DataFrame, h: int):
        """Return (m, s, {qcol: ndarray}) with quantiles emitted directly in variance units.

        The base `_QuantileModel.predict` rearranges the grid (np.maximum.accumulate) to
        guarantee monotonicity, then drops non-finite / non-positive rv_hat rows.
        """
        models: list[QuantileRegressor] = state
        Xm = sub.select(self.needs).to_numpy().astype(float)
        ok = np.isfinite(Xm).all(axis=1)         # leading rolling-window nulls -> NaN passthrough

        n = sub.height
        qpred = {c: np.full(n, np.nan) for c in Q_COLS}
        if ok.any():
            for c, m in zip(Q_COLS, models):
                vals = m.predict(Xm[ok])
                qpred[c][ok] = np.maximum(vals, _VAR_FLOOR)   # positive floor in variance units

        # rv_hat = q50 (median point forecast); sigma = (q90 - q10)/2.563 spread proxy.
        m_point = np.maximum(qpred["q50"], _VAR_FLOOR)
        spread = (qpred["q90"] - qpred["q10"]) / _IQ_Z
        s = np.where(np.isfinite(spread), np.maximum(spread, _SIGMA_FLOOR), _SIGMA_FLOOR)
        return m_point, s, qpred
