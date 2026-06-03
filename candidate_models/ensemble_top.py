"""Model 12 — Equal-weight ensemble of the non-baseline candidate forecasters.

A POST-HOC COMBINER (MODEL_PLAN §4 model 12). It owns no statistical state of its
own: `fit` is a no-op and `predict` reads each component model's predictions parquet
from `execution/data/predictions/`, restricts them to the (ticker, date, horizon) keys
present in the walk-forward's `X_test`, and combines them:

  * rv_hat   = equal-weight MEAN of the components' rv_hat available for a key.
  * sigma    = sqrt( mean(component_sigma^2) + var(component_rv_hat) )
               i.e. within-model variance (average) + between-model dispersion.
  * q05..q95 = regenerated via `_lognormal_quantiles(m, s)` with m = combined rv_hat and
               the log-space sd `s = sqrt(log(1 + (sigma / rv_hat)^2))` — the exact inverse
               of the level-sigma convention used by `_PerKeyModel`
               (`sigma = m * sqrt(expm1(s^2))`), so the quantiles are monotone and centered
               on rv_hat.

A key is combined only where at least MIN_COMPONENTS (2) components have a prediction;
keys with fewer available components are dropped, never imputed (MODEL_PLAN §8).
"""

from __future__ import annotations

import numpy as np
import polars as pl

from rv_eval import config as C
from rv_eval.model_contract import Model, _lognormal_quantiles

# The 8 non-baseline candidates (MODEL_PLAN §4 models 4-11). Hard-coded by design.
COMPONENTS: list[str] = [
    "HARQ",
    "HAR-RS",
    "HAR-CJ",
    "HAR-RS-IV-Q",
    "RealizedGARCH",
    "XGBHARRSIV",
    "LSTMRV",
    "GuyonLekeufackPDV",
]

# Minimum number of components that must have a prediction for a key to keep it.
MIN_COMPONENTS: int = 2

# Where the component prediction parquets live.
PRED_DIR = C.PREDICTIONS_ROOT


class EnsembleTopK(Model):
    """Equal-weight post-hoc ensemble of the COMPONENTS' predictions."""

    name = "EnsembleTopK"

    def fit(self, X: pl.DataFrame, y: pl.DataFrame) -> None:  # noqa: D401
        # No-op: the ensemble has no parameters to learn.
        pass

    def predict(self, X: pl.DataFrame) -> pl.DataFrame:
        # Keys this fold is responsible for (one row per ticker,date in the feature matrix).
        keys = X.select("ticker", "date").unique()
        if keys.is_empty():
            return pl.DataFrame()

        frames: list[pl.DataFrame] = []
        for comp in COMPONENTS:
            path = PRED_DIR / f"{comp}.parquet"
            if not path.exists():
                continue
            df = pl.read_parquet(path).select(
                "ticker", "date", "horizon", "rv_hat", "sigma"
            )
            # Restrict to this fold's keys (join on ticker,date; horizons fan out).
            df = df.join(keys, on=["ticker", "date"], how="inner").filter(
                pl.col("rv_hat").is_finite()
                & (pl.col("rv_hat") > 0)
                & pl.col("sigma").is_finite()
                & (pl.col("sigma") >= 0)
            )
            if df.is_empty():
                continue
            frames.append(df)

        if not frames:
            return pl.DataFrame()

        stacked = pl.concat(frames, how="vertical")

        # Equal-weight combination per (ticker, date, horizon) over available components.
        combined = (
            stacked.group_by("ticker", "date", "horizon")
            .agg(
                rv_hat=pl.col("rv_hat").mean(),
                mean_var=pl.col("sigma").pow(2).mean(),     # within-model variance (avg)
                between_var=pl.col("rv_hat").var(ddof=0),   # between-model dispersion
                n_comp=pl.len(),
            )
            .filter(pl.col("n_comp") >= MIN_COMPONENTS)
        )
        if combined.is_empty():
            return pl.DataFrame()

        m = combined["rv_hat"].to_numpy().astype(float)
        # between_var is null when only one row (filtered out) -> here always >= 2, but guard NaN.
        between = np.nan_to_num(combined["between_var"].to_numpy().astype(float), nan=0.0)
        within = combined["mean_var"].to_numpy().astype(float)
        sigma = np.sqrt(np.maximum(within + between, 0.0))

        # Back out the log-space sd consistent with sigma = m * sqrt(expm1(s^2)).
        m_safe = np.maximum(m, 1e-12)
        s = np.sqrt(np.log1p(np.minimum((sigma / m_safe) ** 2, 1e12)))
        s = np.maximum(s, 1e-6)

        data = {
            "ticker": combined["ticker"],
            "date": combined["date"],
            "horizon": combined["horizon"].cast(pl.Int32),
            "rv_hat": m,
            "sigma": sigma,
        }
        data.update(_lognormal_quantiles(m, s))
        out = pl.DataFrame(data).filter(
            pl.col("rv_hat").is_finite() & (pl.col("rv_hat") > 0)
        )
        cols = ["ticker", "date", "horizon", "rv_hat", "sigma",
                "q05", "q10", "q25", "q50", "q75", "q90", "q95"]
        return out.select(cols).sort("ticker", "horizon", "date")
