"""Tier-2 battery (eval plan §4) — finalists only, confirmation not iteration driver.

Diebold-Mariano (Newey-West HAC, accounting for the h-horizon overlap) and the Hansen-Lunde-Nason
Model Confidence Set via a moving-block bootstrap. The overlapping h-horizon targets make the loss
differential strongly dependent, so these are reported as confirmation of a Tier-1 signal.
"""

from __future__ import annotations

import numpy as np
import polars as pl
from scipy.stats import norm

_EPS = 1e-12


def _qlike(rv: np.ndarray, hat: np.ndarray) -> np.ndarray:
    rv = np.maximum(rv, _EPS); hat = np.maximum(hat, _EPS)
    r = rv / hat
    return r - np.log(r) - 1.0


def diebold_mariano(d: np.ndarray, h: int) -> tuple[float, float]:
    """DM stat & two-sided p-value for a loss differential `d` (model_a - model_b), HAC lag h-1."""
    n = d.size
    dbar = d.mean()
    lag = max(h - 1, 0)
    gamma0 = np.var(d)
    var = gamma0
    for k in range(1, lag + 1):
        cov = np.cov(d[k:], d[:-k])[0, 1]
        var += 2.0 * (1.0 - k / (lag + 1)) * cov
    se = np.sqrt(max(var, _EPS) / n)
    stat = dbar / se
    return float(stat), float(2 * (1 - norm.cdf(abs(stat))))


def _aligned_losses(scored: pl.DataFrame, horizon: int, loss: str = "qlike") -> tuple[list[str], np.ndarray]:
    """Loss matrix (n_obs × n_models) on the keys common to every model, for one horizon."""
    sub = scored.filter(pl.col("horizon") == horizon)
    wide = sub.pivot(values=loss, index=["ticker", "date"], on="model", aggregate_function="first")
    wide = wide.drop_nulls()
    models = [c for c in wide.columns if c not in ("ticker", "date")]
    return models, wide.select(models).to_numpy()


def dm_matrix(scored: pl.DataFrame, horizon: int) -> pl.DataFrame:
    """Pairwise DM p-values (and signed mean loss diff) for one horizon."""
    models, L = _aligned_losses(scored, horizon)
    rows = []
    for i, a in enumerate(models):
        for j, b in enumerate(models):
            if i == j:
                continue
            stat, p = diebold_mariano(L[:, i] - L[:, j], horizon)
            rows.append({"horizon": horizon, "model_a": a, "model_b": b,
                         "mean_loss_diff": float((L[:, i] - L[:, j]).mean()),
                         "dm_stat": stat, "p_value": p})
    return pl.DataFrame(rows)


def _block_bootstrap_idx(n: int, block: int, B: int, rng: np.random.Generator) -> np.ndarray:
    n_blocks = int(np.ceil(n / block))
    starts = rng.integers(0, n - block + 1, size=(B, n_blocks))
    idx = (starts[:, :, None] + np.arange(block)[None, None, :]).reshape(B, -1)[:, :n]
    return idx


def model_confidence_set(scored: pl.DataFrame, horizon: int, alpha: float = 0.10,
                         block: int | None = None, B: int = 1000, seed: int = 0) -> pl.DataFrame:
    """Hansen-Lunde-Nason MCS (T_max variant) via moving-block bootstrap, for one horizon."""
    models, L = _aligned_losses(scored, horizon)
    if len(models) < 2:
        return pl.DataFrame()
    n = L.shape[0]
    block = block or max(horizon, 5)
    rng = np.random.default_rng(seed)
    bidx = _block_bootstrap_idx(n, block, B, rng)
    boot_means = np.stack([L[bidx[b]].mean(axis=0) for b in range(B)])  # (B, M)

    alive = list(range(len(models)))
    result: dict[str, float] = {}
    running_p = 0.0
    while len(alive) > 1:
        Lm = L[:, alive].mean(axis=0)
        bm = boot_means[:, alive]
        d = Lm - Lm.mean()                              # relative loss vs set average
        d_b = bm - bm.mean(axis=1, keepdims=True)
        var = ((d_b - d) ** 2).mean(axis=0)
        t = d / np.sqrt(np.maximum(var, _EPS))
        t_b = (d_b - d) / np.sqrt(np.maximum(var, _EPS))
        T = t.max()
        T_b = t_b.max(axis=1)
        p = float((T_b >= T).mean())
        running_p = max(running_p, p)
        if p >= alpha:
            break
        worst = alive[int(np.argmax(t))]
        result[models[worst]] = running_p
        alive.remove(worst)
    for i in alive:
        result[models[i]] = max(running_p, alpha)       # survivors: in the set at level alpha
    return pl.DataFrame({
        "horizon": horizon,
        "model": list(result.keys()),
        "mcs_pvalue": list(result.values()),
    }).with_columns(in_mcs=pl.col("mcs_pvalue") >= alpha).sort("mcs_pvalue", descending=True)
