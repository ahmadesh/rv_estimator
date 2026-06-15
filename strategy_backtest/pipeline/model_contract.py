"""The model contract + reference benchmark models.

A forecasting model implements::

    class MyModel(Model):
        name = "my-model"
        def fit(self, X: pl.DataFrame, y: pl.DataFrame) -> None: ...   # X=features, y=targets
        def predict(self, X: pl.DataFrame) -> pl.DataFrame: ...        # X=features (no targets)

  X  — point-in-time feature matrix (one row per ticker,date) from `features.build_features`.
  y  — targets, long by horizon: ticker, date, horizon, target_var (+ vol/overnight/intraday).
  predict returns: ticker, date, horizon, rv_hat, sigma, q05..q95  (rv_hat in target_var units).

The walk-forward harness owns the train/test split; models never see future rows at predict.
The benchmarks below (RW, EWMA, HAR, HAR-X) are the §5 yardsticks. `IV-as-forecast` needs no
model — IV² already lives in the targets table and the evaluator compares against it directly.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np
import polars as pl
from scipy.stats import norm

from strategy_backtest.pipeline import config as C
from strategy_backtest.pipeline.features import HAR_FEATURES, IV_FEATURES

Q_COLS = [f"q{int(round(p * 100)):02d}" for p in C.QUANTILES]
_Z = norm.ppf(C.QUANTILES)


def _lognormal_quantiles(m: np.ndarray, s: np.ndarray) -> dict[str, np.ndarray]:
    """Quantiles of a lognormal with mean `m` (level) and log-sd `s`."""
    m = np.maximum(m, 1e-12)
    s = np.maximum(s, 1e-6)
    mu = np.log(m) - 0.5 * s * s
    return {col: np.exp(mu + z * s) for col, z in zip(Q_COLS, _Z)}


class Model(ABC):
    """Interface every forecasting model implements; the walk-forward harness drives it."""

    name: str = "model"

    @abstractmethod
    def fit(self, X: pl.DataFrame, y: pl.DataFrame) -> None: ...

    @abstractmethod
    def predict(self, X: pl.DataFrame) -> pl.DataFrame: ...


class _PerKeyModel(Model):
    """Shared machinery: fit/predict independently per (ticker, horizon), lognormal intervals."""

    horizons = C.HORIZONS
    needs: list[str] = []   # feature columns that must be non-null to fit/predict
    min_obs: int = 60

    def fit(self, X: pl.DataFrame, y: pl.DataFrame) -> None:
        self.state: dict[tuple[str, int], object] = {}
        for h in self.horizons:
            yh = y.filter(pl.col("horizon") == h).select("ticker", "date", "target_var")
            xy = X.join(yh, on=["ticker", "date"], how="inner")
            for (tk,), sub in xy.partition_by("ticker", as_dict=True).items():
                sub = sub.drop_nulls(self.needs + ["target_var"]).filter(pl.col("target_var") > 0)
                if sub.height >= self.min_obs:
                    self.state[(tk, h)] = self._fit_one(sub, h)

    def predict(self, X: pl.DataFrame) -> pl.DataFrame:
        out: list[pl.DataFrame] = []
        for h in self.horizons:
            for (tk,), sub in X.partition_by("ticker", as_dict=True).items():
                st = self.state.get((tk, h))
                if st is None:
                    continue
                sub = sub.sort("date")
                m, s = self._predict_one(st, sub, h)
                if not np.isfinite(m).any():
                    continue
                sigma = m * np.sqrt(np.expm1(np.minimum(s * s, 50.0)))
                data = {
                    "ticker": sub["ticker"], "date": sub["date"],
                    "horizon": np.full(sub.height, h, dtype=np.int32),
                    "rv_hat": m, "sigma": sigma,
                }
                data.update(_lognormal_quantiles(m, s))
                fr = pl.DataFrame(data).filter(
                    pl.col("rv_hat").is_finite() & (pl.col("rv_hat") > 0)
                )
                out.append(fr)
        if not out:
            return pl.DataFrame()
        return pl.concat(out).sort("ticker", "horizon", "date")

    # --- subclass hooks -----------------------------------------------------
    def _fit_one(self, sub: pl.DataFrame, h: int): ...
    def _predict_one(self, state, sub: pl.DataFrame, h: int) -> tuple[np.ndarray, np.ndarray]: ...


class _NaiveScaled(_PerKeyModel):
    """RV_hat = h * (a daily RV proxy). Used for Random-Walk and EWMA benchmarks."""

    source: str = "rv_d"
    min_obs = 30

    def _fit_one(self, sub: pl.DataFrame, h: int):
        src = sub[self.source].to_numpy()
        tgt = sub["target_var"].to_numpy()
        ok = (src > 0) & (tgt > 0)
        resid = np.log(tgt[ok]) - np.log(h * src[ok])
        return float(np.std(resid)) if resid.size > 2 else 0.5

    def _predict_one(self, state, sub: pl.DataFrame, h: int):
        src = sub[self.source].to_numpy().astype(float)
        s = float(state)
        # Lognormal-mean correction (exp(½σ²)) so rv_hat is the QLIKE-optimal mean forecast,
        # matching _LinearLogHAR; without it h·src is the median and biases QLIKE low.
        m = np.where(src > 0, h * src * np.exp(0.5 * s * s), np.nan)
        return m, np.full(sub.height, s, dtype=float)


class _LinearLogHAR(_PerKeyModel):
    """Direct-h forecast: OLS of log(target_var) on `needs` features (+ intercept), per key."""

    min_obs = 100

    def _design(self, sub: pl.DataFrame) -> np.ndarray:
        x = sub.select(self.needs).to_numpy().astype(float)
        return np.column_stack([np.ones(x.shape[0]), x])

    def _fit_one(self, sub: pl.DataFrame, h: int):
        A = self._design(sub)
        y = np.log(sub["target_var"].to_numpy().astype(float))
        beta, *_ = np.linalg.lstsq(A, y, rcond=None)
        resid = y - A @ beta
        s = float(np.std(resid, ddof=A.shape[1])) if resid.size > A.shape[1] else 0.5
        return (beta, max(s, 1e-3))

    def _predict_one(self, state, sub: pl.DataFrame, h: int):
        beta, s = state
        mu = self._design(sub) @ beta          # NaN propagates where a feature is null
        m = np.exp(mu + 0.5 * s * s)            # lognormal mean
        return m, np.full(sub.height, s, dtype=float)


# --------------------------------------------------------------------------- benchmarks
class RandomWalk(_NaiveScaled):
    name = "RW"
    source = "rv_d"
    needs = ["rv_d"]


class EWMA(_NaiveScaled):
    name = "EWMA"
    source = "ewma_rv"
    needs = ["ewma_rv"]


class HAR(_LinearLogHAR):
    name = "HAR"
    needs = HAR_FEATURES


class HARX(_LinearLogHAR):
    name = "HAR-X"
    needs = HAR_FEATURES + IV_FEATURES


# Default model the walk-forward exercises end-to-end.
HARReference = HAR

BENCHMARKS = [RandomWalk, EWMA, HAR, HARX]
