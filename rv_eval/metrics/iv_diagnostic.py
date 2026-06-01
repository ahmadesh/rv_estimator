"""IV comparison & the conditional incremental-skill diagnostic (eval plan §0 / §5).

The single most important question for a vol-premium strategy: does the model add information
*beyond* IV? We compute, per (model, horizon):

  spread_model    = IV² − R̂V_model          (model says how rich IV is)
  realized_spread = IV² − RV_realized         (how rich IV actually was)

and test whether spread_model predicts realized_spread (slope > 0, sign accuracy > 0.5), plus
the head-to-head QLIKE of the model vs treating IV² as the forecast.
"""

from __future__ import annotations

import numpy as np
import polars as pl

_EPS = 1e-12


def _qlike(rv: np.ndarray, hat: np.ndarray) -> float:
    rv = np.maximum(rv, _EPS)
    hat = np.maximum(hat, _EPS)
    r = rv / hat
    return float(np.mean(r - np.log(r) - 1.0))


def iv_diagnostic(scored: pl.DataFrame, by: list[str] | None = None) -> pl.DataFrame:
    """Per-group IV comparison + conditional incremental-skill regression."""
    by = by or ["model", "horizon"]
    have_iv = scored.filter(pl.col("iv2").is_not_null() & (pl.col("iv2") > 0))
    rows = []
    for key, sub in have_iv.partition_by(by, as_dict=True).items():
        rv = sub["target_var"].to_numpy().astype(float)
        hat = sub["rv_hat"].to_numpy().astype(float)
        iv2 = sub["iv2"].to_numpy().astype(float)
        spread = iv2 - hat
        realized = iv2 - rv
        n = rv.size
        # OLS realized ~ a + b*spread (b>0 => model's "IV richness" call has skill)
        A = np.column_stack([np.ones(n), spread])
        beta, *_ = np.linalg.lstsq(A, realized, rcond=None)
        resid = realized - A @ beta
        s2 = (resid @ resid) / max(n - 2, 1)
        cov = s2 * np.linalg.pinv(A.T @ A)
        t_b = beta[1] / np.sqrt(max(cov[1, 1], _EPS))
        sign_acc = float(np.mean(np.sign(spread) == np.sign(realized)))
        rec = dict(zip(by, key if isinstance(key, tuple) else (key,)))
        rec.update(
            n=n, slope=float(beta[1]), t_slope=float(t_b), sign_acc=sign_acc,
            qlike_model=_qlike(rv, hat), qlike_iv=_qlike(rv, iv2),
        )
        rec["qlike_gain_vs_iv"] = rec["qlike_iv"] - rec["qlike_model"]  # >0 model beats IV
        rows.append(rec)
    return pl.DataFrame(rows).sort(by)
