"""HAR-Shrink2Group — per-ticker HAR coefficients shrunk toward the pooled β (catalog model 23).

Track C, Pattern P3 (direct `Model` impl; breaks the per-ticker-independence assumption because
the *target* of the shrinkage is a panel-pooled coefficient vector). This is the "safer than 22"
middle ground between a fully independent per-ticker HAR (`_PerKeyModel`, high variance on thin
tickers) and the fully pooled PanelHAR-FE (model 22, high bias if a ticker's HAR shape differs
from the panel): each ticker gets its OWN OLS β, then those coefficients are shrunk *toward* the
pooled β by a single intensity ``w`` per horizon::

    beta_shrunk(ticker, h) = (1 - w_h) * beta_ticker(ticker, h) + w_h * beta_pooled(ticker, h)

(exactly the catalog form: ``w`` is the weight ON the pooled vector, in [0, 1]).

Coefficient alignment. The per-ticker OLS coefficient vector is ``[intercept, slope_1.. slope_F]``
on `_NEEDS`. The pooled fit (`_base_v2.fit_pooled`) has a per-ticker fixed-effect **intercept**
plus a **single shared slope vector**, so the pooled coefficient vector *for that ticker* is
``[fe_intercept(ticker), shared_slope_1.. shared_slope_F]`` — same length/order as the per-ticker
vector. Unseen-ticker / thin-ticker pooled-intercept fallback (group-mean then global-mean) is
reused from `pooled_mu`'s logic; here we read it off the fitted pooled state directly.

Shrinkage intensity ``w_h`` is a hyperparameter chosen by a **leakage-safe, time-ordered inner
CV on the TRAIN slice only** (never OOS, never another model). At each monthly refit the inner CV
re-selects ``w_h`` from a fixed grid by pooled (across tickers) held-out log-MSE; ties / empty
folds fall back to ``w=1`` (full pooling, the conservative panel estimate). A ticker with fewer
than ``min_ticker_obs`` train rows for a horizon has no stable own-β, so it uses the pooled β
outright (equivalent to ``w=1`` for that ticker) — it never errors.

Features: the same pooled block as PanelHAR-FE, `HAR_RS_FEATURES + IV_FEATURES`, all produced
point-in-time by `features.build_features` from `inputs.parquet` (no `_AttachMixin`/rolling
recompute on the predict slice, so no leakage from window features). Lognormal predictive
distribution via `_emit_lognormal` (level mean `exp(mu + s^2/2)`, log-sd `s` = shrunk-model
in-sample residual std), identical schema to the benchmarks.
"""

from __future__ import annotations

import numpy as np
import polars as pl

from candidate_models._base_v2 import _emit_lognormal, fit_pooled
from rv_eval import config as C
from rv_eval.features import HAR_RS_FEATURES, IV_FEATURES
from rv_eval.model_contract import Model

_KEYS = ["ticker", "date"]
# Same pooled slope block as PanelHAR-FE (model 22) — apples-to-apples shrinkage target.
_NEEDS = HAR_RS_FEATURES + IV_FEATURES

# Shrinkage-intensity grid (weight on the pooled vector). w=0 -> pure per-ticker OLS,
# w=1 -> pure pooled. Selected per horizon by inner CV on TRAIN only.
_W_GRID = (0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0)
_N_CV_FOLDS = 4            # time-ordered expanding inner folds on the TRAIN slice
_MIN_TICKER_OBS = 100      # < this many train rows for a (ticker,h) -> use pooled β outright
_MIN_POOLED_OBS = 200      # mirror _PooledLinearHAR.min_pooled_obs (gates a horizon's fit)


def _design(feat: np.ndarray) -> np.ndarray:
    """[1, features] design matrix (intercept first), matching the pooled coef order."""
    return np.column_stack([np.ones(feat.shape[0]), feat])


def _ols_beta(feat: np.ndarray, ylog: np.ndarray) -> np.ndarray:
    """Per-ticker OLS coefficients [intercept, slopes] for log(target_var)."""
    A = _design(feat)
    beta, *_ = np.linalg.lstsq(A, ylog, rcond=None)
    return beta


def _pooled_beta_for(state: dict, ticker: str) -> np.ndarray:
    """Pooled coefficient vector for one ticker: [fe_intercept, shared_slopes].

    FE intercept fallback for unseen/thin tickers: ticker intercept -> group-mean -> global-mean
    (same precedence as `_base_v2.pooled_mu`). Slopes are shared across the panel.
    """
    b0 = state["intercepts"].get(ticker)
    if b0 is None:
        b0 = state["grp_int"].get(C.GROUP.get(ticker, "_"), state["glob_int"])
    return np.concatenate([[b0], state["slopes"]])


class HARShrink2Group(Model):
    """Per-ticker HAR β shrunk toward the panel-pooled β; intensity `w` by inner-CV (model 23)."""

    name = "HAR-Shrink2Group"
    horizons = C.HORIZONS
    needs = _NEEDS
    min_ticker_obs = _MIN_TICKER_OBS
    min_pooled_obs = _MIN_POOLED_OBS

    # ------------------------------------------------------------------ fit
    def fit(self, X: pl.DataFrame, y: pl.DataFrame) -> None:
        # state[h] = {"pooled": pooled_state, "beta": {ticker: shrunk_beta}, "s": {ticker: log_sd},
        #             "w": chosen_weight, "needs": _NEEDS}
        self.state: dict[int, dict] = {}
        self.chosen_w: dict[int, float] = {}
        self.warnings: dict[str, str] = {}

        for h in self.horizons:
            yh = y.filter(pl.col("horizon") == h).select("ticker", "date", "target_var")
            xy = (
                X.join(yh, on=_KEYS, how="inner")
                .drop_nulls(self.needs + ["target_var"])
                .filter(pl.col("target_var") > 0)
                .sort("ticker", "date")
            )
            if xy.height < self.min_pooled_obs:
                continue

            # Per-ticker (feat, ylog) blocks reused by both CV and the final fit.
            blocks: dict[str, tuple[np.ndarray, np.ndarray]] = {}
            for (tk,), sub in xy.partition_by("ticker", as_dict=True).items():
                sub = sub.sort("date")
                feat = sub.select(self.needs).to_numpy().astype(float)
                ylog = np.log(sub["target_var"].to_numpy().astype(float))
                blocks[tk] = (feat, ylog)

            # 1) choose the shrinkage intensity w by time-ordered inner CV on TRAIN only.
            w = self._select_w(xy, blocks)
            self.chosen_w[h] = w

            # 2) final fit on the whole train slice: pooled β + per-ticker β -> shrink.
            pooled = fit_pooled(xy, self.needs)
            betas: dict[str, np.ndarray] = {}
            sds: dict[str, float] = {}
            for tk, (feat, ylog) in blocks.items():
                b_pool = _pooled_beta_for(pooled, tk)
                if feat.shape[0] >= self.min_ticker_obs:
                    b_tick = _ols_beta(feat, ylog)
                    b = (1.0 - w) * b_tick + w * b_pool
                else:
                    b = b_pool          # thin ticker -> pooled β outright (no own-β variance)
                    self.warnings[f"{tk}@h{h}"] = (
                        f"thin ({feat.shape[0]}<{self.min_ticker_obs}) -> pooled beta")
                betas[tk] = b
                resid = ylog - _design(feat) @ b
                sds[tk] = float(np.std(resid)) if resid.size > b.size else pooled["s"]

            self.state[h] = {
                "pooled": pooled, "beta": betas, "s": sds, "w": w, "needs": self.needs,
            }

    def _select_w(self, xy: pl.DataFrame, blocks: dict) -> float:
        """Time-ordered expanding inner CV on the TRAIN slice; return the pooled-loss-min w.

        Folds split each ticker's own time series so every validation row is strictly after its
        training rows (no inner leakage). Loss is pooled across tickers (log-MSE on held-out).
        Falls back to w=1 (full pooling) if the panel is too thin to CV.
        """
        # Per-fold (train-end, val-window) index fractions, expanding.
        # Use ticker-level time splits so val is always after train within each ticker.
        fold_losses = {w: 0.0 for w in _W_GRID}
        fold_counts = {w: 0 for w in _W_GRID}

        for f in range(_N_CV_FOLDS):
            # expanding train fraction: 1/(F+1) .. F/(F+1); val = next slice.
            tr_frac = (f + 1) / (_N_CV_FOLDS + 1)
            va_frac = (f + 2) / (_N_CV_FOLDS + 1)

            tr_blocks: dict[str, tuple[np.ndarray, np.ndarray]] = {}
            va_blocks: dict[str, tuple[np.ndarray, np.ndarray]] = {}
            tr_rows = []
            for tk, (feat, ylog) in blocks.items():
                n = feat.shape[0]
                i_tr = int(round(n * tr_frac))
                i_va = int(round(n * va_frac))
                if i_tr < 30 or i_va <= i_tr:        # need some train + a non-empty val window
                    continue
                tr_blocks[tk] = (feat[:i_tr], ylog[:i_tr])
                va_blocks[tk] = (feat[i_tr:i_va], ylog[i_tr:i_va])
                tr_rows.append((tk, i_tr))

            if not va_blocks:
                continue
            # Pooled fit on the inner-train portion (rebuild xy subset for fit_pooled).
            xy_tr = self._subset_xy(xy, tr_rows)
            if xy_tr is None or xy_tr.height < self.min_pooled_obs:
                continue
            pooled_tr = fit_pooled(xy_tr, self.needs)

            # Per-ticker own-β on inner-train; evaluate each w on inner-val.
            tick_beta: dict[str, np.ndarray] = {}
            pool_beta: dict[str, np.ndarray] = {}
            for tk, (feat, ylog) in tr_blocks.items():
                pool_beta[tk] = _pooled_beta_for(pooled_tr, tk)
                tick_beta[tk] = (_ols_beta(feat, ylog)
                                 if feat.shape[0] >= self.min_ticker_obs else pool_beta[tk])

            for w in _W_GRID:
                se = 0.0
                cnt = 0
                for tk, (vfeat, vy) in va_blocks.items():
                    b = (1.0 - w) * tick_beta[tk] + w * pool_beta[tk]
                    pred = _design(vfeat) @ b
                    err = vy - pred
                    se += float(np.sum(err * err))
                    cnt += err.size
                if cnt:
                    fold_losses[w] += se
                    fold_counts[w] += cnt

        # No usable inner folds -> conservative full pooling.
        if not any(fold_counts.values()):
            return 1.0
        mse = {w: (fold_losses[w] / fold_counts[w]) for w in _W_GRID if fold_counts[w] > 0}
        # tie-break toward MORE pooling (larger w) for stability.
        best = min(mse.values())
        best_ws = [w for w, v in mse.items() if v <= best + 1e-12]
        return max(best_ws)

    @staticmethod
    def _subset_xy(xy: pl.DataFrame, tr_rows: list[tuple[str, int]]) -> pl.DataFrame | None:
        """Per-ticker first-`i_tr` rows of `xy` (sorted by date) for the inner-train pooled fit."""
        parts = []
        for tk, i_tr in tr_rows:
            sub = xy.filter(pl.col("ticker") == tk).sort("date").head(i_tr)
            if sub.height:
                parts.append(sub)
        if not parts:
            return None
        return pl.concat(parts)

    # -------------------------------------------------------------- predict
    def predict(self, X: pl.DataFrame) -> pl.DataFrame:
        out: list[pl.DataFrame] = []
        for h in self.horizons:
            st = self.state.get(h)
            if st is None:
                continue
            pooled = st["pooled"]
            for (tk,), sub in X.partition_by("ticker", as_dict=True).items():
                sub = sub.sort("date")
                feat = sub.select(self.needs).to_numpy().astype(float)
                beta = st["beta"].get(tk)
                if beta is None:                     # ticker unseen in this fold's train
                    beta = _pooled_beta_for(pooled, tk)
                    s = pooled["s"]
                else:
                    s = st["s"].get(tk, pooled["s"])
                s = max(float(s), 1e-3)
                mu = _design(feat) @ beta            # NaN propagates where a feature is null
                m = np.exp(mu + 0.5 * s * s)         # lognormal mean
                if not np.isfinite(m).any():
                    continue
                out.append(_emit_lognormal(sub, h, m, np.full(sub.height, s)))
        if not out:
            return pl.DataFrame()
        return pl.concat(out).sort("ticker", "horizon", "date")
