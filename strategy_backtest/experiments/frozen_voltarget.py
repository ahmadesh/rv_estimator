"""Vol-targeted book sizing on the frozen book's true MTM path (improvement I3).

Classic short-vol hygiene: de-lever after vol spikes, re-lever in calm — WITHOUT touching
selection (the rejected per-name tilts operated at name resolution; this operates at BOOK
resolution). Now testable because hole-dig A3 produced the daily MTM series.

Rule (PIT): daily leverage m_t = clip(sigma_target / vol_hat_{t-1}, M_MIN, M_MAX), where
vol_hat is an EWMA (RiskMetrics lambda=0.94) of the base book's daily MTM P&L vol, LAGGED one
day, and sigma_target is set to the base book's full-sample vol so mean leverage ~= 1 (pure
reshaping, no free scale-up). Scaled P&L' = m_t x P&L. Two rebalance cadences: daily (upper
bound — pretends the book can be rescaled costlessly every day) and monthly (closer to what
weekly entries + b-scaling can implement: m fixed within each calendar month).

CAVEATS (honest): portfolio-level approximation — real implementation scales NEW entries' b by
m (existing spreads can't be resized costlessly), so live impact is a smoothed version of the
monthly arm; ignores contract rounding and the group-margin cap's nonlinearity.

Reads results/frozen_mtm_daily.csv. Writes results/frozen_voltarget.md.
Run:  .venv/bin/python -m strategy_backtest.experiments.frozen_voltarget
"""

from __future__ import annotations

import datetime as dt
import math

import numpy as np
import polars as pl

from strategy_backtest.backtest import config as cfg

IN_CSV = cfg.RESULTS_ROOT / "frozen_mtm_daily.csv"
OUT_MD = cfg.RESULTS_ROOT / "frozen_voltarget.md"
LAM = 0.94
M_MIN, M_MAX = 0.3, 3.0
ERAS = [(2010, 2013), (2014, 2017), (2018, 2021), (2022, 2026)]


def stats(dates: np.ndarray, pnl: np.ndarray) -> dict:
    df = pl.DataFrame({"date": dates, "pnl": pnl})
    mo = df.group_by(pl.col("date").dt.truncate("1mo").alias("m")).agg(pl.col("pnl").sum()).sort("m")
    r = mo["pnl"].to_numpy()
    eq = pnl.cumsum()
    out = {"sharpe": float(r.mean() / r.std(ddof=1) * math.sqrt(12)),
           "pnl": float(pnl.sum()),
           "maxdd": float(np.max(np.maximum.accumulate(eq) - eq))}
    for lo, hi in ERAS:
        f = mo.filter(pl.col("m").dt.year().is_between(lo, hi))["pnl"].to_numpy()
        out[f"{lo}"] = float(f.mean() / f.std(ddof=1) * math.sqrt(12)) if len(f) > 6 else float("nan")
    return out


def main() -> None:
    d = pl.read_csv(IN_CSV, try_parse_dates=True).sort("date")
    dates = d["date"].to_numpy()
    r = d["mtm_pnl"].to_numpy().astype(float)
    n = len(r)

    # EWMA variance, lagged: vol_hat[t] uses r[0..t-1]
    var = np.empty(n)
    var[0] = r[: 63].var()                      # warmup seed (first quarter, PIT enough for t=0)
    for t in range(1, n):
        var[t] = LAM * var[t - 1] + (1 - LAM) * r[t - 1] ** 2
    vol_hat = np.sqrt(var)
    sigma_target = r.std(ddof=1)
    m_daily = np.clip(sigma_target / np.maximum(vol_hat, 1e-9), M_MIN, M_MAX)

    # monthly cadence: freeze m at each month's first session
    mo_key = pl.Series(dates).dt.truncate("1mo").to_numpy()
    m_monthly = np.empty(n)
    cur = None
    for t in range(n):
        if cur is None or mo_key[t] != mo_key[t - 1]:
            cur = m_daily[t]
        m_monthly[t] = cur

    arms = {
        "base (MTM, m=1)": np.ones(n),
        "vol-target daily": m_daily,
        "vol-target monthly": m_monthly,
    }
    L = ["# Vol-targeted sizing on the frozen book's MTM path (improvement I3)", "",
         f"_EWMA(λ={LAM}) book-vol, 1-day lag, m∈[{M_MIN},{M_MAX}], σ_target = base full-sample vol"
         f" (mean-leverage≈1) · generated {dt.date.today()}_", "",
         "| arm | mean m | Sharpe(mo) | P&L | maxDD (daily) | "
         + " | ".join(f"{lo}–{hi}" for lo, hi in ERAS) + " |",
         "| --- | --- | --- | --- | --- | " + " | ".join("---" for _ in ERAS) + " |"]
    for name, m in arms.items():
        s = stats(dates, m * r)
        eras = " | ".join(f"{s[str(lo)]:.2f}" for lo, _ in ERAS)
        L.append(f"| {name} | {m.mean():.2f} | **{s['sharpe']:.2f}** | ${s['pnl']:,.0f} "
                 f"| ${s['maxdd']:,.0f} | {eras} |")
        print(f"{name:22s} mean_m {m.mean():.2f}  Sharpe {s['sharpe']:.2f}  "
              f"pnl ${s['pnl']:,.0f}  maxDD ${s['maxdd']:,.0f}")
    L += ["", "Caveats: portfolio-level approximation (live version scales NEW entries only;",
          "existing spreads can't be resized costlessly); ignores contract rounding and the",
          "group-margin cap. The monthly arm is the implementable read.", ""]
    OUT_MD.write_text("\n".join(L) + "\n")
    print(f"-> {OUT_MD}")


if __name__ == "__main__":
    main()
