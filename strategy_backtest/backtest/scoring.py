"""Economic scoring + statistical-power discipline (design §8.2 / §8.3).

Pure functions over the daily realized-P&L series and the per-trade ledger. Headline metrics mirror
the upstream `reports.score_stage1` (Sharpe/Sortino, CVaR95/99, maxDD, ann. return, hit rate) and
add the §8.2 power discipline: trade count, an effective-N for the serially/cross-correlated sample,
and a block bootstrap that puts CONFIDENCE INTERVALS on CVaR95 and maxDD — the design's promotion
bar is a CI, never a point estimate.
"""

from __future__ import annotations

import math

import numpy as np
import polars as pl

from strategy_backtest.backtest import config as cfg

TPY = cfg.TRADING_DAYS_PER_YEAR


# --------------------------------------------------------------------------- core stats
def _span_years(dates: pl.Series) -> float:
    d = dates.sort()
    return max((d.max() - d.min()).days / 365.25, 1e-9)


def _ppy(dates: pl.Series) -> float:
    return len(dates) / _span_years(dates)


def sharpe_per_obs(r: np.ndarray) -> float:
    sd = r.std(ddof=1)
    return float(r.mean() / sd) if sd > 0 else 0.0


def sortino_per_obs(r: np.ndarray) -> float:
    dn = np.minimum(r, 0.0)
    dd = math.sqrt((dn ** 2).mean())
    return float(r.mean() / dd) if dd > 0 else 0.0


def cvar(r: np.ndarray, q: float) -> float:
    """Mean of the worst (1-q) tail of P&L (negative = a loss)."""
    if r.size == 0:
        return float("nan")
    thr = np.quantile(r, 1.0 - q)
    tail = r[r <= thr]
    return float(tail.mean()) if tail.size else float(thr)


def max_drawdown(equity_or_pnl: np.ndarray, *, is_pnl: bool = True) -> float:
    """Max peak-to-trough drawdown in dollars (returned as a positive number)."""
    eq = np.cumsum(equity_or_pnl) if is_pnl else equity_or_pnl
    if eq.size == 0:
        return 0.0
    peak = np.maximum.accumulate(eq)
    return float(np.max(peak - eq))


def effective_n(r: np.ndarray) -> float:
    """Effective sample size accounting for lag-1 serial dependence: N*(1-rho1)/(1+rho1)."""
    n = r.size
    if n < 3:
        return float(n)
    r0 = r - r.mean()
    denom = float((r0 ** 2).sum())
    rho1 = float((r0[1:] * r0[:-1]).sum() / denom) if denom > 0 else 0.0
    rho1 = max(min(rho1, 0.999), -0.999)
    return float(n * (1.0 - rho1) / (1.0 + rho1))


# --------------------------------------------------------------------------- block bootstrap
def _block_idx(n: int, block: int, B: int, rng: np.random.Generator) -> np.ndarray:
    """Moving-block bootstrap index matrix (B x n): preserves serial/overlap structure."""
    block = max(1, min(block, n))
    n_blocks = int(math.ceil(n / block))
    starts = rng.integers(0, n - block + 1, size=(B, n_blocks))
    offs = np.arange(block)
    idx = (starts[:, :, None] + offs[None, None, :]).reshape(B, -1)[:, :n]
    return idx


def _block_len(dates: pl.Series, cal_days: int = 22) -> int:
    """Moving-block length (in observations) covering >= `cal_days` calendar days of overlap."""
    d = dates.sort()
    gaps = d.diff().dt.total_days().drop_nulls()
    g = float(gaps.median()) if len(gaps) else float(cal_days)
    return max(2, int(math.ceil(cal_days / max(g, 1.0))))


def bootstrap_ci(r: np.ndarray, dates: pl.Series, metric, *, B: int = cfg.BOOT_B,
                 seed: int = cfg.BOOT_SEED, alpha: float = 0.05) -> dict:
    """Block-bootstrap (point, lo, hi) CI for `metric(r)` at the (1-alpha) level."""
    n = r.size
    point = float(metric(r))
    if n < 5:
        return {"point": point, "lo": float("nan"), "hi": float("nan"), "block": 0}
    block = _block_len(dates)
    rng = np.random.default_rng(seed)
    idx = _block_idx(n, block, B, rng)
    vals = np.array([metric(r[ix]) for ix in idx])
    lo, hi = np.nanquantile(vals, [alpha / 2, 1 - alpha / 2])
    return {"point": point, "lo": float(lo), "hi": float(hi), "block": block}


# --------------------------------------------------------------------------- headline scorecard
def base_metrics(daily: pl.DataFrame) -> dict:
    """Full headline metric block off the daily realized-P&L series."""
    r = daily["pnl"].to_numpy()
    dates = daily["date"]
    ppy = _ppy(dates)
    wins, losses = r[r > 0], r[r < 0]
    sr = sharpe_per_obs(r)
    nav = cfg.NAV
    return {
        "n_obs_days": int(r.size),
        "span_years": round(_span_years(dates), 2),
        "ppy": round(ppy, 2),
        "pnl_total": float(r.sum()),
        "ann_return_$": float(r.mean() * ppy),
        "ann_return_pct": float(r.mean() * ppy / nav),
        "vol_ann_$": float(r.std(ddof=1) * math.sqrt(ppy)),
        "sharpe_ann": float(sr * math.sqrt(ppy)),
        "sortino_ann": float(sortino_per_obs(r) * math.sqrt(ppy)),
        "cvar95_$": cvar(r, 0.95),
        "cvar99_$": cvar(r, 0.99),
        "cvar95_pct_nav": cvar(r, 0.95) / nav,
        "worst_day_$": float(r.min()),
        "max_dd_$": max_drawdown(r),
        "max_dd_pct_nav": max_drawdown(r) / nav,
        "hit_rate": float((r > 0).mean()),
        "avg_win_$": float(wins.mean()) if wins.size else 0.0,
        "avg_loss_$": float(losses.mean()) if losses.size else 0.0,
        "effective_n": round(effective_n(r), 1),
    }


def trade_metrics(ledger: pl.DataFrame) -> dict:
    """Trade-level summary off the per-trade ledger (count, win rate, breach rate, cost drag)."""
    if ledger.is_empty():
        return {}
    pnl = ledger["pnl"].to_numpy()
    g = float(ledger["gross_pnl"].sum())
    c = float(ledger["cost"].sum())
    margin = (ledger["contracts"] * ledger["maxloss_c"]).to_numpy()      # max-loss $ per trade
    return {
        "n_trades": int(ledger.height),
        "trade_win_rate": float((pnl > 0).mean()),
        "breach_rate": float(ledger["breached"].mean()),
        "avg_contracts": float(ledger["contracts"].mean()),
        "median_contracts": float(ledger["contracts"].median()),
        "frac_one_contract": float((ledger["contracts"] == 1).mean()),
        "mean_margin_pct_nav": float(margin.mean() / cfg.NAV),
        "max_margin_pct_nav": float(margin.max() / cfg.NAV),
        "median_size_units": float(ledger["size_units"].median()),
        # average per-trade return on its own capital-at-risk (pnl_i / maxloss_i), defined-risk ROC
        "avg_return_on_risk": float((pnl / np.where(margin > 0, margin, np.nan)).mean()),
        "gross_total_$": g,
        "cost_total_$": c,
        "cost_frac_of_gross": (c / abs(g)) if g != 0 else float("nan"),
        "breakeven_cost_mult": (g / c) if c > 0 else float("inf"),
    }
