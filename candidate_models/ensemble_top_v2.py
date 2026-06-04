"""Model 21 — EnsembleTopK-v2: regime-conditional, leakage-safe post-hoc combiner.

ITER2_MODEL_CATALOG.md §3 (#21). A POST-HOC combiner like `ensemble_top.py`, but with
**regime-conditional / discounted-MSE weights** instead of an equal-weight mean:

  * The component pool is the iter-1 *winners* (the four HAR-family models the iter-1
    `EnsembleTopK` settled on) plus the best new Track-A/B/D iter-2 models. The iter-1
    `EnsembleTopK` itself, the raw baselines (RW/EWMA/HAR/HAR-X), the two blow-up models
    (RealizedGARCH, GuyonLekeufackPDV) and the Track-C/E pooled/regime models are NOT
    eligible (see CANDIDATE_POOL).

  * **Top-K** membership is chosen *per horizon* from each component's PAST out-of-sample
    discounted-MSE — never the full sample, never the test row's realized target.

  * **Weights are regime-conditional**: for each (horizon, iv-percentile bucket) the top-K
    components are combined with inverse-discounted-MSE softmax weights, again estimated only
    from PAST realized rows. The regime label is `iv_pctile_bucket` from `targets.parquet`,
    a trailing-IV-percentile rank that is point-in-time observable at prediction time
    (constant across horizons for a given (ticker,date); see card).

Leakage controls (the critical risk for an ensemble — see card §"Leakage controls"):
  - `fit(X_train, y_train)` is the ONLY place weights are estimated. `y_train` is already
    purged + embargoed by the walk-forward (target window ends >= EMBARGO_EXTRA days before
    the test block). We score each component's rv_hat against those PAST realized targets,
    keyed (ticker,date,horizon), restricted to the fit set's keys.
  - A time-decay (`HALF_LIFE_DAYS`) discounts older errors so the weights track the recent
    regime, but every scored row still predates the test block.
  - `predict(X_test)` only LOOKS UP the frozen weights by (horizon, regime bucket); it never
    sees a realized target. The regime bucket is read from `targets.parquet` (point-in-time).
  - A key is combined only where >= MIN_COMPONENTS of its bucket's top-K have a finite
    forecast; otherwise it is dropped, never imputed.
"""

from __future__ import annotations

import numpy as np
import polars as pl

from rv_eval import config as C
from rv_eval.model_contract import Model, _lognormal_quantiles

# --------------------------------------------------------------------------- config
# Eligible component pool (catalog §21: iter-1 winners + best new A/B/D models).
#   iter-1 winners — the four the iter-1 EnsembleTopK converged to (top of pooled QLIKE
#   on BOTH universes): the genuine HAR-family top-K.
ITER1_WINNERS: list[str] = ["HAR-RS-IV-Q", "HARQ", "HAR-RS", "HAR-CJ"]
#   best new iter-2 models from Tracks A (feature blocks), B (shrinkage/combine), D (calib).
#   NOTE: Track C (pooling) and Track E (regime) are out of the §21 "A/B/D" remit; the
#   blow-up models (RealizedGARCH, PDV) and iter-1 non-winners (LSTM/XGB) are excluded by
#   design, and the iter-1 EnsembleTopK / this model are never their own components.
TRACK_A: list[str] = ["LHAR", "HAR-SJ", "HAR-IVTS", "HAR-Range", "HAR-Act", "HAR-MAX"]
TRACK_B: list[str] = ["HAR-ENet", "HAR-Ridge", "HAR-CSR"]
TRACK_D: list[str] = ["HARX-HS", "HAR-GARCH", "HAR-QR", "VRP-Spread"]

CANDIDATE_POOL: list[str] = ITER1_WINNERS + TRACK_A + TRACK_B + TRACK_D

# Top-K components kept per horizon (chosen leakage-safely from past discounted-MSE).
TOP_K: int = 5
# Minimum components with a finite forecast for a key to be combined (else dropped).
MIN_COMPONENTS: int = 2
# Exponential time-decay half-life (trading days) for the discounted-MSE weighting.
HALF_LIFE_DAYS: float = 252.0
# Softmax temperature on the (negative) discounted-MSE when forming regime weights.
SOFTMAX_TEMP: float = 1.0
# Minimum past scored rows in a (horizon, bucket) cell to trust its regime-specific weights;
# below this we fall back to the horizon-level (regime-pooled) weights.
MIN_CELL_OBS: int = 200
# Regime label column (point-in-time observable) read from targets.parquet.
REGIME_COL: str = "iv_pctile_bucket"

PRED_DIR = C.PREDICTIONS_ROOT
_QCOLS = ["q05", "q10", "q25", "q50", "q75", "q90", "q95"]


def _load_components() -> dict[str, pl.DataFrame]:
    """Read every available eligible component parquet once (ticker,date,horizon,rv_hat,sigma)."""
    out: dict[str, pl.DataFrame] = {}
    for comp in CANDIDATE_POOL:
        path = PRED_DIR / f"{comp}.parquet"
        if not path.exists():
            continue
        df = (
            pl.read_parquet(path)
            .select("ticker", "date", "horizon", "rv_hat", "sigma")
            .filter(
                pl.col("rv_hat").is_finite() & (pl.col("rv_hat") > 0)
                & pl.col("sigma").is_finite() & (pl.col("sigma") >= 0)
            )
        )
        if not df.is_empty():
            out[comp] = df
    return out


def _regime_table() -> pl.DataFrame:
    """Point-in-time regime label per (ticker,date) from targets (constant across horizons)."""
    t = (
        pl.read_parquet(C.TARGETS_PARQUET)
        .select("ticker", "date", REGIME_COL)
        .unique(["ticker", "date"], keep="first")
    )
    return t


class EnsembleTopKV2(Model):
    """Regime-conditional, leakage-safe discounted-MSE ensemble of the component pool."""

    name = "EnsembleTopK-v2"

    def __init__(self) -> None:
        # Loaded once, reused across folds (the parquets are static; we only ever restrict
        # them by the fold's date range, so caching introduces no leakage).
        self._components = _load_components()
        self._regime = _regime_table()
        # Per-fold frozen weights:
        #   topk[h]                  -> ordered list of the top-K component names for horizon h
        #   wregime[(h, bucket)]     -> {comp: weight}  (regime-specific)
        #   wpool[h]                 -> {comp: weight}  (regime-pooled fallback)
        self._topk: dict[int, list[str]] = {}
        self._wregime: dict[tuple[int, int], dict[str, float]] = {}
        self._wpool: dict[int, dict[str, float]] = {}

    # ------------------------------------------------------------------ weighting
    def _scored(self, y_train: pl.DataFrame) -> pl.DataFrame:
        """Per-(component,horizon,date,ticker) squared log-error on the PAST (y_train) rows.

        We score in log space (log rv_hat vs log target_var) because the forecasts span
        many orders of magnitude across tickers/horizons; squared log-error is the scale-free
        analogue of QLIKE dispersion and keeps a single blow-up row from dominating the weight.
        """
        yh = (
            y_train.select("ticker", "date", "horizon", "target_var")
            .filter(pl.col("target_var") > 0)
        )
        if yh.is_empty():
            return pl.DataFrame()
        yh = yh.join(self._regime, on=["ticker", "date"], how="left")
        ref_date = yh["date"].max()

        frames: list[pl.DataFrame] = []
        for comp, df in self._components.items():
            j = df.join(yh, on=["ticker", "date", "horizon"], how="inner")
            if j.is_empty():
                continue
            age = (pl.lit(ref_date) - pl.col("date")).dt.total_days().cast(pl.Float64)
            decay = (-np.log(2.0) / HALF_LIFE_DAYS)
            j = j.with_columns(
                sqerr=(pl.col("rv_hat").log() - pl.col("target_var").log()).pow(2),
                w_decay=(decay * age).exp(),
                component=pl.lit(comp),
            )
            frames.append(j.select("component", "horizon", REGIME_COL, "sqerr", "w_decay"))
        if not frames:
            return pl.DataFrame()
        return pl.concat(frames, how="vertical")

    @staticmethod
    def _weights_from_dmse(dmse: dict[str, float]) -> dict[str, float]:
        """Inverse-discounted-MSE softmax weights over a {comp: dmse} mapping."""
        comps = list(dmse.keys())
        vals = np.array([dmse[c] for c in comps], dtype=float)
        # score = -log(dmse): lower error -> higher weight; softmax with temperature.
        score = -np.log(np.maximum(vals, 1e-12)) / max(SOFTMAX_TEMP, 1e-6)
        score -= score.max()
        ex = np.exp(score)
        w = ex / ex.sum()
        return {c: float(wi) for c, wi in zip(comps, w)}

    def fit(self, X: pl.DataFrame, y: pl.DataFrame) -> None:
        # Reset per-fold frozen weights.
        self._topk, self._wregime, self._wpool = {}, {}, {}
        scored = self._scored(y)
        if scored.is_empty():
            return

        for h in C.HORIZONS:
            sh = scored.filter(pl.col("horizon") == h)
            if sh.is_empty():
                continue
            # Discounted-MSE per component (regime-pooled) -> rank -> top-K.
            pooled = (
                sh.group_by("component")
                .agg(
                    dmse=(pl.col("sqerr") * pl.col("w_decay")).sum()
                    / pl.col("w_decay").sum(),
                    n=pl.len(),
                )
                .sort("dmse")
            )
            order = pooled["component"].to_list()
            topk = order[:TOP_K]
            if not topk:
                continue
            self._topk[h] = topk

            pooled_d = dict(zip(pooled["component"].to_list(), pooled["dmse"].to_list()))
            self._wpool[h] = self._weights_from_dmse({c: pooled_d[c] for c in topk})

            # Regime-conditional weights: per (horizon, bucket) discounted-MSE over the top-K.
            shk = sh.filter(pl.col("component").is_in(topk))
            cell = (
                shk.drop_nulls(REGIME_COL)
                .group_by(REGIME_COL, "component")
                .agg(
                    dmse=(pl.col("sqerr") * pl.col("w_decay")).sum()
                    / pl.col("w_decay").sum(),
                    n=pl.len(),
                )
            )
            for bucket in cell[REGIME_COL].unique().to_list():
                cb = cell.filter(pl.col(REGIME_COL) == bucket)
                if cb["n"].sum() < MIN_CELL_OBS or cb.height < MIN_COMPONENTS:
                    continue  # thin cell -> fall back to the pooled weights at predict time
                dmap = dict(zip(cb["component"].to_list(), cb["dmse"].to_list()))
                self._wregime[(h, int(bucket))] = self._weights_from_dmse(dmap)

    # ------------------------------------------------------------------ predict
    def predict(self, X: pl.DataFrame) -> pl.DataFrame:
        keys = X.select("ticker", "date").unique()
        if keys.is_empty() or not self._topk:
            return pl.DataFrame()

        # All eligible component forecasts on this fold's keys, with the (observable) regime.
        frames: list[pl.DataFrame] = []
        pool = set().union(*self._topk.values()) if self._topk else set()
        for comp in pool:
            df = self._components.get(comp)
            if df is None:
                continue
            j = df.join(keys, on=["ticker", "date"], how="inner")
            if j.is_empty():
                continue
            frames.append(j.with_columns(component=pl.lit(comp)))
        if not frames:
            return pl.DataFrame()
        stacked = pl.concat(frames, how="vertical").join(
            self._regime, on=["ticker", "date"], how="left"
        )

        # Build the per-(horizon, regime) weight to attach to each component row.
        rows = stacked.to_dict(as_series=False)
        n = len(rows["ticker"])
        comp_arr = rows["component"]
        h_arr = rows["horizon"]
        bkt_arr = rows[REGIME_COL]
        w_out = np.zeros(n, dtype=float)
        for i in range(n):
            h = int(h_arr[i])
            topk = self._topk.get(h)
            if not topk or comp_arr[i] not in topk:
                continue
            b = bkt_arr[i]
            wmap = None
            if b is not None and (h, int(b)) in self._wregime:
                wmap = self._wregime[(h, int(b))]
            if wmap is None:
                wmap = self._wpool.get(h)
            if wmap is not None:
                w_out[i] = wmap.get(comp_arr[i], 0.0)

        stacked = stacked.with_columns(w=pl.Series("w", w_out)).filter(pl.col("w") > 0)
        if stacked.is_empty():
            return pl.DataFrame()

        # Weighted combination per (ticker,date,horizon) over its available top-K components.
        combined = (
            stacked.group_by("ticker", "date", "horizon")
            .agg(
                wsum=pl.col("w").sum(),
                rv_num=(pl.col("w") * pl.col("rv_hat")).sum(),
                var_num=(pl.col("w") * pl.col("sigma").pow(2)).sum(),
                # between-model dispersion (weighted around the weighted mean)
                rv2_num=(pl.col("w") * pl.col("rv_hat").pow(2)).sum(),
                n_comp=pl.len(),
            )
            .filter((pl.col("n_comp") >= MIN_COMPONENTS) & (pl.col("wsum") > 0))
        )
        if combined.is_empty():
            return pl.DataFrame()

        m = (combined["rv_num"] / combined["wsum"]).to_numpy().astype(float)
        within = (combined["var_num"] / combined["wsum"]).to_numpy().astype(float)
        ex2 = (combined["rv2_num"] / combined["wsum"]).to_numpy().astype(float)
        between = np.maximum(ex2 - m * m, 0.0)          # weighted Var of component rv_hat
        sigma = np.sqrt(np.maximum(within + between, 0.0))

        # Back out the log-sd consistent with sigma = m * sqrt(expm1(s^2)).
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
        cols = ["ticker", "date", "horizon", "rv_hat", "sigma", *_QCOLS]
        return out.select(cols).sort("ticker", "horizon", "date")
