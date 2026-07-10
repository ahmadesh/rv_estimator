"""Statistics layer on the frozen book (hole-digs A6 crash-beta, A9 recency, A4b honest-Sharpe).

Three pure-stats attacks on the frozen ledger + signal panel (no new backtests):

  A6  crash-beta   — monthly P&L regressed on SPY return, a downside term min(SPY,0), and ΔVIX
                     (Newey-West t's): how much of the book is priced crash-factor compensation
                     vs residual alpha? The deployment case rests on the residual.
  A9  recency      — per-year cohort rank-IC and top-2 selection edge (same construction as spec
                     §4.3): is the cross-sectional edge decaying into 2025–26?
  A4b honest Sharpe— stationary-bootstrap CI on the monthly Sharpe + deflated Sharpe (Bailey &
                     López de Prado) against the DOCUMENTED family of tried variants (18 cross-fill
                     trials from §5 + cadence/fixed/straddle docs; plus an N=40 scenario for the
                     undocumented forks).

Reads conclusion/frozen_run_trades.csv (cross fills) + data_wide panel.
Writes results/frozen_stats.md.

Run:  .venv/bin/python -m strategy_backtest.experiments.frozen_stats
"""

from __future__ import annotations

import datetime as dt
import math

import numpy as np
import polars as pl

from strategy_backtest.backtest import config as cfg, pit

LEDGER = cfg.SB_ROOT / "conclusion" / "frozen_run_trades.csv"
FEATURES = cfg.SB_ROOT / "data_wide" / "features.parquet"
TARGETS = cfg.SB_ROOT / "data_wide" / "targets.parquet"
PREDICTIONS = cfg.SB_ROOT / "data_wide" / "predictions" / "EnsembleTopK.parquet"
OUT_MD = cfg.RESULTS_ROOT / "frozen_stats.md"

# Documented cross-fill Sharpes of the variant family tried on this sample (spec §5, §4.2, §6.6,
# CADENCE_EXPERIMENTS master table): frozen, Mon/Thu/Tue/Wed/Fri, split×3, 9-name, no-walk,
# group-distinct, K4, K6, trailing-RV, L/S straddle, short straddle, fixed SPY/QQQ.
TRIAL_SHARPES_ANN = [0.66, 0.78, 0.71, 0.55, 0.48, 0.52, 0.75, 0.67, 0.67,
                     0.68, 0.43, 0.54, 0.29, 0.20, 0.02, -0.50, 0.70, 0.67]


def monthly_pnl() -> pl.DataFrame:
    led = pl.read_csv(LEDGER, try_parse_dates=True)
    d = led.group_by(pl.col("exit_date").alias("date")).agg(pnl=pl.col("pnl").sum()).sort("date")
    alld = pl.DataFrame({"date": pl.date_range(d["date"].min(), d["date"].max(), "1d", eager=True)})
    full = alld.join(d, on="date", how="left").fill_null(0.0)
    return full.group_by(pl.col("date").dt.truncate("1mo").alias("m")).agg(
        pl.col("pnl").sum()).sort("m")


def newey_west_ols(y: np.ndarray, X: np.ndarray, lags: int = 3):
    Xc = np.column_stack([np.ones(len(y)), X])
    beta, *_ = np.linalg.lstsq(Xc, y, rcond=None)
    u = y - Xc @ beta
    XtX_inv = np.linalg.inv(Xc.T @ Xc)
    S = (Xc * u[:, None]).T @ (Xc * u[:, None])
    for l in range(1, lags + 1):
        w = 1 - l / (lags + 1)
        G = (Xc[l:] * u[l:, None]).T @ (Xc[:-l] * u[:-l, None])
        S += w * (G + G.T)
    V = XtX_inv @ S @ XtX_inv
    return beta, beta / np.sqrt(np.diag(V))


def spearman(a: np.ndarray, b: np.ndarray) -> float:
    ra = np.argsort(np.argsort(a)).astype(float)
    rb = np.argsort(np.argsort(b)).astype(float)
    if ra.std() == 0 or rb.std() == 0:
        return float("nan")
    return float(np.corrcoef(ra, rb)[0, 1])


def cohort_panel() -> pl.DataFrame:
    """Weekly gated cohorts with score and realized richness (spec §4.3 construction)."""
    targets = pl.read_parquet(TARGETS).filter(pl.col("horizon") == 22).select(
        "ticker", "date", "iv2", "target_var")
    preds = pl.read_parquet(PREDICTIONS).filter(pl.col("horizon") == 22).select(
        "ticker", "date", "rv_hat", "sigma", "fold_id")
    fc = preds.join(targets.select("ticker", "date", "target_var"), on=["ticker", "date"], how="left")
    fc = pit.trailing_debias(fc, "rv_hat", "target_var", embargo=22, min_periods=126)
    fc = fc.with_columns(
        rv_hat_cal=pl.when(pl.col("log_bias").is_not_null())
        .then(pl.col("rv_hat") * pl.col("log_bias").exp()).otherwise(pl.col("rv_hat")))
    p = targets.join(fc.select("ticker", "date", "rv_hat_cal"), on=["ticker", "date"], how="inner")
    p = p.filter(pl.col("ticker") != "HYG")
    p = p.filter((pl.col("iv2") > 0) & (pl.col("rv_hat_cal") > 0) & (pl.col("target_var") > 0))
    p = p.with_columns(
        score=(pl.col("iv2").log() - pl.col("rv_hat_cal").log()),
        realized=(pl.col("iv2").log() - pl.col("target_var").log()))
    cal = p.select("date").unique().sort("date").with_columns(i=pl.int_range(pl.len()))
    wk = cal.filter(pl.col("i") % 5 == 0).select("date")
    pw = p.join(wk, on="date", how="inner").filter(pl.col("score") > 0.0)
    return pw.join(pw.group_by("date").agg(n=pl.len()), on="date").filter(pl.col("n") >= 7)


def main() -> None:
    mo = monthly_pnl()
    r = mo["pnl"].to_numpy() / cfg.NAV                      # monthly return on NAV
    T = len(r)
    sr_m = r.mean() / r.std(ddof=1)
    L = ["# Frozen-book statistics layer (A6 crash-beta · A9 recency · honest Sharpe)", "",
         f"_cross-fill ledger, {T} months · generated {dt.date.today()}_", ""]

    # ---------------------------------------------------------------- A6 crash beta
    spy = (pl.read_parquet(FEATURES, columns=["ticker", "date", "ret_cc", "vix"])
           .filter(pl.col("ticker") == "SPY")
           .group_by(pl.col("date").dt.truncate("1mo").alias("m"))
           .agg(spy_ret=pl.col("ret_cc").sum(), vix_eom=pl.col("vix").last() * 100)
           .sort("m").with_columns(dvix=pl.col("vix_eom").diff()))
    j = mo.join(spy, on="m", how="inner").drop_nulls()
    y = j["pnl"].to_numpy() / cfg.NAV
    spy_r = j["spy_ret"].to_numpy()
    X = np.column_stack([spy_r, np.minimum(spy_r, 0.0), j["dvix"].to_numpy() / 100.0])
    beta, tstat = newey_west_ols(y, X)
    resid_ann = beta[0] * 12 * cfg.NAV
    L += ["## A6 — crash-factor attribution (monthly, Newey-West lags=3)", "",
          "`pnl%NAV ~ α + β1·SPY + β2·min(SPY,0) + β3·ΔVIX`", "",
          "| term | coef | t |", "| --- | --- | --- |",
          f"| α (monthly) | {beta[0]*100:.3f}% NAV (${beta[0]*cfg.NAV:,.0f}/mo, ${resid_ann:,.0f}/yr) | **{tstat[0]:.2f}** |",
          f"| β SPY | {beta[1]:.3f} | {tstat[1]:.2f} |",
          f"| β min(SPY,0) (crash convexity) | {beta[2]:.3f} | {tstat[2]:.2f} |",
          f"| β ΔVIX (per vol pt/100) | {beta[3]:.4f} | {tstat[3]:.2f} |", "",
          f"R² = {1 - np.var(y - np.column_stack([np.ones(len(y)), X]) @ beta) / np.var(y):.2f}. "
          "α is the P&L left after paying for equity/crash/vol-of-vol beta.", ""]

    # ---------------------------------------------------------------- A9 recency
    pw = cohort_panel()
    ics, edges_ = [], []
    for (d,), sub in pw.group_by("date", maintain_order=True):
        s = sub["score"].to_numpy()
        z = sub["realized"].to_numpy()
        ics.append({"date": d, "ic": spearman(s, z),
                    "edge": float(z[np.argsort(-s)[:2]].mean() - z.mean())})
    icd = pl.DataFrame(ics).drop_nulls().with_columns(y=pl.col("date").dt.year())
    L += ["## A9 — is the cross-sectional edge decaying? (per-year cohort rank-IC)", "",
          "| year | cohorts | mean rank-IC | IC>0 share | top-2 selection edge |",
          "| --- | --- | --- | --- | --- |"]
    for (yy,), g in icd.group_by("y", maintain_order=True):
        L.append(f"| {yy} | {g.height} | {g['ic'].mean():+.3f} | {(g['ic'] > 0).mean()*100:.0f}% "
                 f"| {g['edge'].mean():+.3f} |")
    full_ic = icd["ic"].mean()
    last2 = icd.filter(pl.col("date") >= icd["date"].max() - dt.timedelta(days=730))
    L += ["", f"Full-sample mean IC {full_ic:+.3f}; trailing-2y mean IC {last2['ic'].mean():+.3f} "
          f"({last2.height} cohorts, IC>0 {(last2['ic'] > 0).mean()*100:.0f}% of weeks).", ""]

    # ---------------------------------------------------------------- honest Sharpe
    rng = np.random.default_rng(7)
    B, mean_block = 4000, 6
    boot = np.empty(B)
    for b in range(B):
        idx, out = rng.integers(T), []
        while len(out) < T:
            ln = rng.geometric(1 / mean_block)
            out.extend(range(idx, idx + ln))
            idx = rng.integers(T)
        v = r[np.array(out[:T]) % T]
        boot[b] = v.mean() / v.std(ddof=1) * math.sqrt(12)
    trials_m = np.array(TRIAL_SHARPES_ANN) / math.sqrt(12)
    g3 = float(((r - r.mean()) ** 3).mean() / r.std(ddof=0) ** 3)
    g4 = float(((r - r.mean()) ** 4).mean() / r.std(ddof=0) ** 4)
    gamma = 0.5772156649

    def dsr(n_trials: int, var_scale: float = 1.0) -> float:
        from statistics import NormalDist
        nd = NormalDist()
        sd = trials_m.std(ddof=1) * var_scale
        sr0 = sd * ((1 - gamma) * nd.inv_cdf(1 - 1 / n_trials)
                    + gamma * nd.inv_cdf(1 - 1 / (n_trials * math.e)))
        z = (sr_m - sr0) * math.sqrt(T - 1) / math.sqrt(1 - g3 * sr_m + (g4 - 1) / 4 * sr_m ** 2)
        return nd.cdf(z)

    L += ["## Honest Sharpe — bootstrap CI + deflated Sharpe", "",
          f"- observed Sharpe (ann.) **{sr_m*math.sqrt(12):.2f}**; stationary-bootstrap 90% CI "
          f"[{np.percentile(boot,5):.2f}, {np.percentile(boot,95):.2f}] "
          f"(mean block {mean_block} months, B={B})",
          f"- monthly skew {g3:.2f}, kurtosis {g4:.1f}",
          f"- deflated Sharpe (prob. the true SR > 0 after selection among trials):",
          f"    - N=18 documented variants (trial-SR sd {trials_m.std(ddof=1)*math.sqrt(12):.2f} ann.): "
          f"**DSR = {dsr(18):.2f}**",
          f"    - N=40 (undocumented forks scenario): **DSR = {dsr(40):.2f}**", ""]

    OUT_MD.write_text("\n".join(L) + "\n")
    print(f"-> {OUT_MD}")


if __name__ == "__main__":
    main()
