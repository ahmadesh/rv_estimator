"""Shared base classes for the iteration-2 (Modern-HAR Extensions) model wave.

These factor out the three reuse patterns named in
`execution_plan/ITER2_MODEL_CATALOG.md` §1/§2, so each iter-2 model file stays a thin
subclass. **This module imports only from `rv_eval` and never edits it** — the harness
(`model_contract.py`, `features.py`, `config.py`, `walkforward.py`) stays pristine.

  _AttachMixin       P1 — add trailing-window derived features by building them once on the
                     FULL series and joining by (ticker, date) (generalises har_cj.py::_attach).
  _PooledLinearHAR   P3 — pooled log-OLS per horizon ACROSS tickers with ticker fixed-effect
                     intercepts + shared slopes (breaks _PerKeyModel's per-ticker independence).
  _QuantileModel     P3 — per-(ticker,h) model that emits q05..q95 DIRECTLY (bypasses the
                     lognormal wrapper), enforcing monotone quantiles.

All three keep the exact output schema and reuse `_lognormal_quantiles` / `Q_COLS` so
predictions drop straight into the walk-forward + `selfstats` + evaluator unchanged.
"""

from __future__ import annotations

import numpy as np
import polars as pl

from rv_eval import config as C
from rv_eval.model_contract import Model, Q_COLS, _PerKeyModel, _lognormal_quantiles

_KEYS = ["ticker", "date"]


def _emit_lognormal(sub: pl.DataFrame, h: int, m: np.ndarray, s: np.ndarray) -> pl.DataFrame:
    """Standard (rv_hat, sigma, q05..q95) row block for one (ticker, horizon) slice.

    Mirrors `_PerKeyModel.predict` exactly: level sigma from the log-sd `s` (scalar or
    per-row array), lognormal quantiles, drop non-finite / non-positive rv_hat.
    """
    s = np.asarray(s, dtype=float)
    sigma = m * np.sqrt(np.expm1(np.minimum(s * s, 50.0)))
    data = {
        "ticker": sub["ticker"], "date": sub["date"],
        "horizon": np.full(sub.height, h, dtype=np.int32),
        "rv_hat": m, "sigma": sigma,
    }
    data.update(_lognormal_quantiles(m, s))
    return pl.DataFrame(data).filter(pl.col("rv_hat").is_finite() & (pl.col("rv_hat") > 0))


# --------------------------------------------------------------------------- P1
class _AttachMixin:
    """Add derived trailing-window features safely under the walk-forward slicing.

    The walk-forward hands `fit`/`predict` only a train- or one-month-test slice, so a
    `rolling_mean`/`shift`/expanding-rank computed on that slice alone is wrong (null or
    mis-ranked leading rows). Subclasses therefore implement::

        def _derive(self, src: pl.DataFrame) -> pl.DataFrame:   # returns [ticker, date, *cols]
            ...   # trailing windows over the FULL series, per ticker, point-in-time

    The mixin builds that table once on the full `inputs.parquet`, caches it, and JOINS it
    into X by (ticker, date). When X carries keys absent from `inputs.parquet` (the synthetic
    smoke test, where X already IS the full series) it rebuilds the table straight from X.

    Use with a `_PerKeyModel`/`_LinearLogHAR` base via MRO, e.g.
    `class LHAR(_AttachMixin, _LinearLogHAR): ...` — `_attach` runs before the base fit/predict.
    """

    _derived_cache: pl.DataFrame | None = None

    def _derive(self, src: pl.DataFrame) -> pl.DataFrame:  # pragma: no cover - abstract
        raise NotImplementedError("subclass must implement _derive(src) -> [ticker, date, *cols]")

    def _full_table(self) -> pl.DataFrame:
        if self._derived_cache is None:
            self._derived_cache = self._derive(pl.read_parquet(C.INPUTS_PARQUET))
        return self._derived_cache

    def _attach(self, X: pl.DataFrame) -> pl.DataFrame:
        tab = self._full_table()
        keys = X.select(_KEYS).unique()
        covered = keys.join(tab.select(_KEYS), on=_KEYS, how="inner").height
        if covered < keys.height:           # smoke test / out-of-panel keys: X is the full series
            tab = self._derive(X)
        drop = [c for c in tab.columns if c in X.columns and c not in _KEYS]
        return X.drop(drop).join(tab, on=_KEYS, how="left")

    def fit(self, X: pl.DataFrame, y: pl.DataFrame) -> None:
        super().fit(self._attach(X), y)     # type: ignore[misc]

    def predict(self, X: pl.DataFrame) -> pl.DataFrame:
        return super().predict(self._attach(X))   # type: ignore[misc]


# --------------------------------------------------------------------------- P3 (pooling)
def fit_pooled(xy: pl.DataFrame, needs: list[str]) -> dict:
    """Pooled log-OLS across tickers: ticker fixed-effect intercepts + shared slopes.

    `xy` must already be cleaned (no nulls in `needs`+target_var, target_var>0) for one
    horizon. Returns a fitted-state dict reusable by both PanelHAR-FE and the shrink-to-pooled
    model. Unseen tickers at predict fall back to their group-mean, then global-mean intercept.
    """
    tickers = xy["ticker"].unique().sort().to_list()
    t_index = {t: i for i, t in enumerate(tickers)}
    feat = xy.select(needs).to_numpy().astype(float)
    ylog = np.log(xy["target_var"].to_numpy().astype(float))
    tcodes = np.fromiter((t_index[t] for t in xy["ticker"].to_list()), dtype=int, count=xy.height)

    nT, nF = len(tickers), feat.shape[1]
    design = np.zeros((xy.height, nT + nF))
    design[np.arange(xy.height), tcodes] = 1.0      # one intercept dummy per ticker (no global)
    design[:, nT:] = feat
    beta, *_ = np.linalg.lstsq(design, ylog, rcond=None)
    slopes = beta[nT:]
    intercepts = {t: float(beta[i]) for t, i in t_index.items()}

    resid = ylog - design @ beta
    dof = max(resid.size - (nT + nF), 1)
    s = float(np.sqrt(np.sum(resid ** 2) / dof)) if resid.size > nT + nF else 0.5

    grp: dict[str, list[float]] = {}
    for t, iv in intercepts.items():
        grp.setdefault(C.GROUP.get(t, "_"), []).append(iv)
    grp_int = {g: float(np.mean(v)) for g, v in grp.items()}
    glob_int = float(np.mean(list(intercepts.values()))) if intercepts else 0.0
    return {"intercepts": intercepts, "slopes": slopes, "s": max(s, 1e-3),
            "grp_int": grp_int, "glob_int": glob_int, "needs": needs}


def pooled_mu(state: dict, ticker: str, feat: np.ndarray) -> np.ndarray:
    """Linear predictor log E[var] for one ticker's feature block, with FE fallback."""
    b0 = state["intercepts"].get(ticker)
    if b0 is None:
        b0 = state["grp_int"].get(C.GROUP.get(ticker, "_"), state["glob_int"])
    return b0 + feat @ state["slopes"]


class _PooledLinearHAR(Model):
    """Panel HAR: one pooled log-OLS per horizon across all fit-set tickers (P3).

    Cannot subclass `_PerKeyModel` (that loops per ticker independently) — pooling is the
    whole point. Reuses `_lognormal_quantiles` / the standard schema via `_emit_lognormal`.
    """

    name = "pooled-har"
    horizons = C.HORIZONS
    needs: list[str] = []
    min_pooled_obs = 200

    def fit(self, X: pl.DataFrame, y: pl.DataFrame) -> None:
        self.state: dict[int, dict] = {}
        for h in self.horizons:
            yh = y.filter(pl.col("horizon") == h).select("ticker", "date", "target_var")
            xy = (
                X.join(yh, on=_KEYS, how="inner")
                .drop_nulls(self.needs + ["target_var"]).filter(pl.col("target_var") > 0)
            )
            if xy.height >= self.min_pooled_obs:
                self.state[h] = fit_pooled(xy, self.needs)

    def predict(self, X: pl.DataFrame) -> pl.DataFrame:
        out: list[pl.DataFrame] = []
        for h in self.horizons:
            st = self.state.get(h)
            if st is None:
                continue
            for (tk,), sub in X.partition_by("ticker", as_dict=True).items():
                sub = sub.sort("date")
                feat = sub.select(self.needs).to_numpy().astype(float)
                mu = pooled_mu(st, tk, feat)                 # NaN propagates where features null
                s = st["s"]
                m = np.exp(mu + 0.5 * s * s)
                if not np.isfinite(m).any():
                    continue
                out.append(_emit_lognormal(sub, h, m, np.full(sub.height, s)))
        if not out:
            return pl.DataFrame()
        return pl.concat(out).sort("ticker", "horizon", "date")


# --------------------------------------------------------------------------- P3 (quantiles)
class _QuantileModel(_PerKeyModel):
    """Per-(ticker, horizon) model that emits q05..q95 DIRECTLY (no lognormal wrapper).

    Subclass implements the usual `_fit_one(sub, h) -> state` plus::

        def _predict_q(self, state, sub, h) -> tuple[m, s, dict[qcol -> ndarray]]:
            ...   # m = point forecast, s = level predictive sd, q = grid of quantile arrays

    `predict` enforces non-decreasing quantiles across the grid and drops non-positive rv_hat.
    """

    def predict(self, X: pl.DataFrame) -> pl.DataFrame:
        out: list[pl.DataFrame] = []
        for h in self.horizons:
            for (tk,), sub in X.partition_by("ticker", as_dict=True).items():
                st = self.state.get((tk, h))
                if st is None:
                    continue
                sub = sub.sort("date")
                m, s, q = self._predict_q(st, sub, h)
                if not np.isfinite(m).any():
                    continue
                qmat = np.maximum.accumulate(           # monotone q05<=...<=q95
                    np.column_stack([np.asarray(q[c], dtype=float) for c in Q_COLS]), axis=1)
                data = {
                    "ticker": sub["ticker"], "date": sub["date"],
                    "horizon": np.full(sub.height, h, dtype=np.int32),
                    "rv_hat": np.asarray(m, dtype=float), "sigma": np.asarray(s, dtype=float),
                }
                data.update({c: qmat[:, i] for i, c in enumerate(Q_COLS)})
                fr = pl.DataFrame(data).filter(pl.col("rv_hat").is_finite() & (pl.col("rv_hat") > 0))
                out.append(fr)
        if not out:
            return pl.DataFrame()
        return pl.concat(out).sort("ticker", "horizon", "date")

    def _predict_q(self, state, sub: pl.DataFrame, h: int):  # pragma: no cover - abstract
        raise NotImplementedError
