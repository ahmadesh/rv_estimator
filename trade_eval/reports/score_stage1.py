"""Stage-1 economic scoring layer (STAGE1_TRADING_EVAL_PLAN.md §4-§8).

Pure scoring of the FROZEN backtest result files under trade_eval/results/.
No refits, no pipeline changes. Reads ledger/<cell>.parquet + portfolio/<cell>.parquet
+ manifest.parquet and emits:

  trade_eval/reports/scorecard.parquet     -- per (model,horizon,ablation) economic scorecard
  trade_eval/reports/attribution.parquet   -- A1-A9 marginal contributions (significance-tested)
  trade_eval/reports/_scoring_dump.json    -- structured tables used to author the .md

Headline statistic is the Deflated Sharpe Ratio (Bailey/Lopez de Prado), deflated by the
N = 104-cell trial count. Every headline number carries a significance test and its deflation.
Reuses the HAC + moving-block machinery from rv_eval.metrics.tier2.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import polars as pl
from scipy.stats import norm

from rv_eval import config as C
from rv_eval.metrics.tier2 import diebold_mariano, _block_bootstrap_idx

RESULTS = Path("trade_eval/results")
LEDGER = RESULTS / "ledger"
PORT = RESULTS / "portfolio"
OUT = Path("trade_eval/reports")
OUT.mkdir(parents=True, exist_ok=True)

TPY = C.TRADING_DAYS_PER_YEAR  # 252
EULER = 0.5772156649015329
HARD = set(C.HARD_CASES)
CLEAN = set(C.CLEAN_CORE)
N_TRIALS = 104                 # manifest cell count -> DSR deflation
C_BPS_DEFAULT = 5.0
C_BPS_SWEEP = (0.0, 2.5, 5.0, 10.0, 20.0)
BOOT_B = 4000
SEED = 7

MODELS = ["EnsembleTopK", "HAR-X", "HAR-Shrink2Group", "PanelHAR-FE", "HAR-ENet", "IV-only"]
HORIZONS = [5, 10, 22]
ABLATIONS = ["baseline", "A2_no_gate", "A3_flat_size", "A5_qspread",
             "A7_random", "A7_always", "A9_managed"]


def cell(model: str, h: int, ab: str) -> str:
    return f"{model}__h{h}__{ab}"


def load_port(model: str, h: int, ab: str) -> pl.DataFrame | None:
    p = PORT / f"{cell(model,h,ab)}.parquet"
    if not p.exists():
        return None
    return pl.read_parquet(p).select("date", "pnl", "gross_pnl", "cost", "n_positions").sort("date")


def load_ledger(model: str, h: int, ab: str) -> pl.DataFrame | None:
    p = LEDGER / f"{cell(model,h,ab)}.parquet"
    if not p.exists():
        return None
    return pl.read_parquet(p)


# ----------------------------------------------------------------------------- core stats
def _span_years(dates: pl.Series) -> float:
    d = dates.sort()
    days = (d.max() - d.min()).days
    return max(days / 365.25, 1e-9)


def _periods_per_year(dates: pl.Series) -> float:
    return len(dates) / _span_years(dates)


def sharpe_per_obs(r: np.ndarray) -> float:
    sd = r.std(ddof=1)
    return float(r.mean() / sd) if sd > 0 else 0.0


def _moments(r: np.ndarray) -> tuple[float, float]:
    """Pearson skew (g1) and kurtosis (non-excess, normal=3)."""
    n = r.size
    m = r.mean()
    s = r.std(ddof=0)
    if s == 0:
        return 0.0, 3.0
    g1 = float(((r - m) ** 3).mean() / s ** 3)
    g2 = float(((r - m) ** 4).mean() / s ** 4)
    return g1, g2


def dsr(r: np.ndarray, sr_trials_var: float, n_trials: int) -> dict:
    """Deflated Sharpe Ratio (Bailey & Lopez de Prado 2014).

    sr_trials_var = variance of the per-observation Sharpe estimates across all trials.
    Returns the probability that the true (per-obs) SR exceeds the deflated benchmark SR0.
    """
    n = r.size
    sr = sharpe_per_obs(r)
    g1, g2 = _moments(r)
    # expected maximum Sharpe across N independent trials under the null SR=0
    z1 = norm.ppf(1.0 - 1.0 / n_trials)
    z2 = norm.ppf(1.0 - 1.0 / (n_trials * math.e))
    sr0 = math.sqrt(max(sr_trials_var, 1e-18)) * ((1.0 - EULER) * z1 + EULER * z2)
    denom = math.sqrt(max(1.0 - g1 * sr + (g2 - 1.0) / 4.0 * sr * sr, 1e-12))
    stat = (sr - sr0) * math.sqrt(max(n - 1, 1)) / denom
    return {"sr_obs": sr, "sr0": sr0, "dsr": float(norm.cdf(stat)),
            "dsr_stat": float(stat), "skew": g1, "kurt": g2}


def cvar(r: np.ndarray, q: float) -> float:
    """Mean of the worst (1-q) tail of P&L (a loss, i.e. negative). q in (0,1)."""
    if r.size == 0:
        return float("nan")
    thr = np.quantile(r, 1.0 - q)
    tail = r[r <= thr]
    return float(tail.mean()) if tail.size else float(thr)


def max_drawdown(r: np.ndarray) -> float:
    eq = np.cumsum(r)
    peak = np.maximum.accumulate(eq)
    return float(np.max(peak - eq)) if eq.size else 0.0


def worst_k(r: np.ndarray, k: int) -> float:
    if r.size < k:
        return float(r.sum())
    csum = np.convolve(r, np.ones(k), mode="valid")
    return float(csum.min())


def sortino_per_obs(r: np.ndarray) -> tuple[float, float]:
    dn = np.minimum(r, 0.0)
    dd = math.sqrt((dn ** 2).mean())
    return (float(r.mean() / dd) if dd > 0 else 0.0), dd


def base_metrics(port: pl.DataFrame) -> dict:
    r = port["pnl"].to_numpy()
    dates = port["date"]
    ppy = _periods_per_year(dates)
    sr = sharpe_per_obs(r)
    sortino, dd_dev = sortino_per_obs(r)
    wins = r[r > 0]
    losses = r[r < 0]
    return {
        "n_obs": int(r.size),
        "span_years": round(_span_years(dates), 2),
        "ppy": round(ppy, 2),
        "mean_obs": float(r.mean()),
        "ann_return": float(r.mean() * ppy),
        "vol_ann": float(r.std(ddof=1) * math.sqrt(ppy)),
        "sharpe_ann": float(sr * math.sqrt(ppy)),
        "sortino_ann": float(sortino * math.sqrt(ppy)),
        "dd_dev": dd_dev,
        "cvar95": cvar(r, 0.95),
        "cvar99": cvar(r, 0.99),
        "worst_day": float(r.min()),
        "worst_20": worst_k(r, 20),
        "max_dd": max_drawdown(r),
        "hit_rate": float((r > 0).mean()),
        "avg_win": float(wins.mean()) if wins.size else 0.0,
        "avg_loss": float(losses.mean()) if losses.size else 0.0,
        "pnl_total": float(r.sum()),
    }


# ----------------------------------------------------------------------------- significance
def hac_dm(delta: np.ndarray, lag: int) -> tuple[float, float]:
    """One-sided HAC (Newey-West) test of mean(delta) > 0. Returns (stat, p_one_sided)."""
    n = delta.size
    if n < 3:
        return 0.0, 1.0
    dbar = delta.mean()
    gamma0 = np.var(delta)
    var = gamma0
    for k in range(1, lag + 1):
        if k >= n:
            break
        cov = np.cov(delta[k:], delta[:-k])[0, 1]
        var += 2.0 * (1.0 - k / (lag + 1)) * cov
    se = math.sqrt(max(var, 1e-18) / n)
    stat = dbar / se
    return float(stat), float(1.0 - norm.cdf(stat))


def block_len_obs(dates: pl.Series) -> int:
    """Moving-block length in OBSERVATION units that covers >=22 calendar days.

    The portfolio series is already at the roll cadence (each obs aggregates ~h days),
    so a block of >=22 *calendar* days is a small number of observations.
    """
    d = dates.sort()
    gaps = d.diff().dt.total_days().drop_nulls()
    g = float(gaps.median()) if len(gaps) else 22.0
    return max(2, int(math.ceil(22.0 / max(g, 1.0))))


def boot_mean_pvalue(delta: np.ndarray, block: int, B: int = BOOT_B, seed: int = SEED) -> float:
    """Stationary/moving-block bootstrap one-sided p for H0: mean(delta) <= 0."""
    n = delta.size
    if n < 3:
        return 1.0
    rng = np.random.default_rng(seed)
    idx = _block_bootstrap_idx(n, min(block, n), B, rng)
    bm = delta[idx].mean(axis=1)
    return float((bm <= 0.0).mean())


def boot_metric_diff_pvalue(a: np.ndarray, b: np.ndarray, metric, block: int,
                            B: int = BOOT_B, seed: int = SEED) -> tuple[float, float]:
    """Paired block-bootstrap of metric(a) - metric(b). Higher metric = better.

    Returns (observed_diff, p_one_sided) for H0: diff <= 0 (a not better than b).
    a, b are aligned (same dates). Blocks are drawn jointly to preserve pairing & autocorr.
    """
    n = a.size
    if n < 3:
        return float(metric(a) - metric(b)), 1.0
    obs = metric(a) - metric(b)
    rng = np.random.default_rng(seed)
    idx = _block_bootstrap_idx(n, min(block, n), B, rng)
    diffs = np.array([metric(a[ix]) - metric(b[ix]) for ix in idx])
    # recenter null at 0
    p = float(((diffs - obs) >= obs).mean()) if obs >= 0 else float(((diffs - obs) <= obs).mean())
    return float(obs), p


# ----------------------------------------------------------------------------- 1. SCORECARD
def build_scorecard() -> pl.DataFrame:
    # first pass: per-obs Sharpe of every cell -> trial variance for DSR deflation
    sr_list = []
    cells = []
    for model in MODELS:
        for h in HORIZONS:
            for ab in ABLATIONS:
                port = load_port(model, h, ab)
                if port is None or port.height < 3:
                    continue
                r = port["pnl"].to_numpy()
                sr_list.append(sharpe_per_obs(r))
                cells.append((model, h, ab))
    sr_trials_var = float(np.var(np.array(sr_list), ddof=1))

    rows = []
    for model, h, ab in cells:
        port = load_port(model, h, ab)
        led = load_ledger(model, h, ab)
        r = port["pnl"].to_numpy()
        m = base_metrics(port)
        d = dsr(r, sr_trials_var, N_TRIALS)
        m.update(d)
        m["model"], m["horizon"], m["ablation"] = model, h, ab
        m["is_benchmark"] = (model == "IV-only")
        m["dte"] = {5: 7, 10: 14, 22: 30}[h]

        # cost / turnover from ledger
        if led is not None and led.height:
            g = float(led["gross_pnl"].sum())
            c = float(led["cost"].sum())
            m["gross_total"] = g
            m["cost_total"] = c
            m["cost_frac_of_gross"] = c / abs(g) if g != 0 else float("nan")
            # cost is linear in c_bps; baseline uses per-group bps (default 5). break-even
            # multiple on the *current* cost vector, expressed as default-name bps equivalent.
            m["breakeven_cbps"] = (g / c) * C_BPS_DEFAULT if c > 0 else float("inf")
            # net annualized return across the c_bps sweep (scale whole cost vector by cbps/5)
            ppy = m["ppy"]
            sweep = {}
            net_dates = led.group_by("entry_date").agg(
                pl.col("gross_pnl").sum().alias("g"), pl.col("cost").sum().alias("c"))
            gg = net_dates["g"].to_numpy(); cc = net_dates["c"].to_numpy()
            for cb in C_BPS_SWEEP:
                net = gg - cc * (cb / C_BPS_DEFAULT)
                sweep[f"ann_ret_cbps_{cb}"] = float(net.mean() * (net.size / m["span_years"]))
            m.update(sweep)
        else:
            m["gross_total"] = m["cost_total"] = float("nan")
            m["cost_frac_of_gross"] = m["breakeven_cbps"] = float("nan")
        rows.append(m)

    df = pl.DataFrame(rows)
    df = df.with_columns(pl.lit(sr_trials_var).alias("sr_trials_var"),
                         pl.lit(N_TRIALS).alias("n_trials_deflation"))
    return df


# ----------------------------------------------------------------------------- 2. vs IV-only (A1)
def vs_ivonly() -> list[dict]:
    out = []
    for model in [m for m in MODELS if m != "IV-only"]:
        for h in HORIZONS:
            mp = load_port(model, h, "baseline")
            iv = load_port("IV-only", h, "baseline")
            if mp is None or iv is None:
                continue
            j = mp.select("date", "pnl").join(
                iv.select("date", pl.col("pnl").alias("pnl_iv")), on="date", how="inner").sort("date")
            if j.height < 5:
                continue
            a = j["pnl"].to_numpy(); b = j["pnl_iv"].to_numpy()
            delta = a - b
            blk = block_len_obs(j["date"])
            lag = max(1, blk - 1)
            stat, p_dm = hac_dm(delta, lag)
            p_boot = boot_mean_pvalue(delta, blk)
            out.append({
                "model": model, "horizon": h, "n_common": j.height,
                "mean_delta": float(delta.mean()),
                "ann_delta": float(delta.mean() * (j.height / _span_years(j["date"]))),
                "sharpe_model": sharpe_per_obs(a), "sharpe_iv": sharpe_per_obs(b),
                "cvar95_model": cvar(a, 0.95), "cvar95_iv": cvar(b, 0.95),
                "maxdd_model": max_drawdown(a), "maxdd_iv": max_drawdown(b),
                "dm_stat": stat, "dm_p_onesided": p_dm, "boot_p_onesided": p_boot,
                "block_obs": blk,
            })
    return out


# ----------------------------------------------------------------------------- 3. ablation attribution
def _paired(model, h, ab_a, ab_b):
    pa = load_port(model, h, ab_a)
    pb = load_port(model, h, ab_b)
    if pa is None or pb is None:
        return None
    j = pa.select("date", pl.col("pnl").alias("a")).join(
        pb.select("date", pl.col("pnl").alias("b")), on="date", how="inner").sort("date")
    if j.height < 5:
        return None
    return j


def attribution() -> list[dict]:
    out = []
    contrasts = [
        ("A2_gate", "baseline", "A2_no_gate", "gate on vs off"),
        ("A3_sizing", "baseline", "A3_flat_size", "forecast size vs flat"),
        ("A5_qspread", "A5_qspread", "baseline", "quantile-spread vs sigma size"),
        ("A9_managed", "A9_managed", "baseline", "managed vs hold-to-expiry"),
    ]
    for model in [m for m in MODELS if m != "IV-only"]:
        for h in HORIZONS:
            for tag, ab_a, ab_b, desc in contrasts:
                j = _paired(model, h, ab_a, ab_b)
                if j is None:
                    continue
                a = j["a"].to_numpy(); b = j["b"].to_numpy()
                blk = block_len_obs(j["date"])
                lag = max(1, blk - 1)
                # mean-return marginal
                stat, p_dm = hac_dm(a - b, lag)
                p_boot_mean = boot_mean_pvalue(a - b, blk)
                # CVaR95 marginal (less-negative = better): metric = cvar95 (higher better)
                cv_obs, p_cv = boot_metric_diff_pvalue(a, b, lambda x: cvar(x, 0.95), blk)
                # Sharpe marginal
                sh_obs, p_sh = boot_metric_diff_pvalue(a, b, sharpe_per_obs, blk)
                out.append({
                    "ablation": tag, "model": model, "horizon": h, "desc": desc,
                    "n_common": j.height,
                    "mean_delta": float((a - b).mean()),
                    "dCVaR95": cv_obs, "p_dCVaR95": p_cv,
                    "dSharpe": sh_obs, "p_dSharpe": p_sh,
                    "dMaxDD": max_drawdown(b) - max_drawdown(a),  # positive = a has smaller DD
                    "dm_stat_mean": stat, "p_mean_onesided": p_dm, "boot_p_mean": p_boot_mean,
                })
    return out


# ----------------------------------------------------------------------------- 4. A7 controls
def controls() -> list[dict]:
    out = []
    for model in [m for m in MODELS if m != "IV-only"]:
        for h in HORIZONS:
            base = load_port(model, h, "baseline")
            if base is None:
                continue
            rb = base["pnl"].to_numpy()
            row = {"model": model, "horizon": h,
                   "sharpe_base": base_metrics(base)["sharpe_ann"],
                   "cvar95_base": cvar(rb, 0.95)}
            for ctl in ("A7_random", "A7_always"):
                p = load_port(model, h, ctl)
                if p is None:
                    row[f"sharpe_{ctl}"] = float("nan"); row[f"cvar95_{ctl}"] = float("nan"); continue
                rc = p["pnl"].to_numpy()
                row[f"sharpe_{ctl}"] = base_metrics(p)["sharpe_ann"]
                row[f"cvar95_{ctl}"] = cvar(rc, 0.95)
            out.append(row)
    return out


# ----------------------------------------------------------------------------- 5. A4 sleeve vs core on hard_cases
def _hardcase_series(model, h, ab="baseline"):
    led = load_ledger(model, h, ab)
    if led is None:
        return None
    sub = led.filter(pl.col("ticker").is_in(list(HARD)))
    if sub.height < 5:
        return None
    # one-per-group book proxy: sum pnl per entry_date over hard names
    s = sub.group_by("entry_date").agg(pl.col("pnl").sum().alias("pnl")).sort("entry_date")
    return s.rename({"entry_date": "date"})


def a4_sleeve() -> list[dict]:
    out = []
    sleeve = ["HAR-Shrink2Group", "PanelHAR-FE"]
    core = ["EnsembleTopK", "HAR-X"]
    for h in HORIZONS:
        for model in sleeve + core:
            s = _hardcase_series(model, h)
            if s is None:
                continue
            r = s["pnl"].to_numpy()
            out.append({
                "horizon": h, "model": model,
                "role": "sleeve" if model in sleeve else "clean_core",
                "n_obs": int(r.size), "sharpe_ann": base_metrics(s)["sharpe_ann"],
                "cvar95": cvar(r, 0.95), "max_dd": max_drawdown(r),
                "pnl_total": float(r.sum()), "mean_obs": float(r.mean()),
            })
    return out


# ----------------------------------------------------------------------------- 6. portfolio stress
def stress_panel() -> list[dict]:
    out = []
    for model in MODELS:
        for h in [22]:  # primary book
            led = load_ledger(model, h, "baseline")
            if led is None:
                continue
            # group x date matrix from the ledger (sum trades per group per entry_date)
            gd = (led.group_by("entry_date", "group")
                     .agg(pl.col("pnl").sum().alias("pnl")))
            wide = gd.pivot(values="pnl", index="entry_date", on="group", aggregate_function="first").sort("entry_date")
            book = wide.select(pl.exclude("entry_date")).sum_horizontal()
            wide = wide.with_columns(book.alias("_book"))
            n = wide.height
            kk = min(20, max(5, n // 5))
            stress_dates = wide.sort("_book").head(kk)["entry_date"]
            calm_dates = wide.sort("_book", descending=True).head(n - kk)["entry_date"]
            gcols = [c for c in wide.columns if c not in ("entry_date", "_book")]

            def mean_corr(sel: pl.DataFrame) -> float:
                M = sel.select(gcols).to_numpy()
                # keep columns with >=3 non-null and nonzero variance
                vals = []
                cols = []
                for i, c in enumerate(gcols):
                    col = M[:, i]
                    mask = ~np.isnan(col)
                    if mask.sum() >= 3 and np.nanstd(col) > 0:
                        cols.append(i)
                if len(cols) < 2:
                    return float("nan")
                sub = M[:, cols]
                cc = np.ma.corrcoef(np.ma.masked_invalid(sub), rowvar=False)
                iu = np.triu_indices(len(cols), 1)
                vv = np.asarray(cc)[iu]
                vv = vv[np.isfinite(vv)]
                return float(vv.mean()) if vv.size else float("nan")

            stress = wide.filter(pl.col("entry_date").is_in(stress_dates))
            calm = wide.filter(pl.col("entry_date").is_in(calm_dates))
            rbook = wide["_book"].to_numpy()
            out.append({
                "model": model, "horizon": h,
                "worst20_book": worst_k(np.sort(rbook), 20) if rbook.size >= 20 else float(rbook.sum()),
                "corr_stress": mean_corr(stress), "corr_calm": mean_corr(calm),
                "n_stress_days": kk, "n_book_days": n,
            })
    return out


# ----------------------------------------------------------------------------- run
def main():
    sc = build_scorecard()
    sc.write_parquet(OUT / "scorecard.parquet")

    a1 = vs_ivonly()
    attr = attribution()
    ctl = controls()
    a4 = a4_sleeve()
    stress = stress_panel()

    pl.DataFrame(attr).write_parquet(OUT / "attribution.parquet")

    dump = {
        "sr_trials_var": float(sc["sr_trials_var"][0]),
        "n_trials": N_TRIALS,
        "vs_ivonly": a1, "attribution": attr, "controls": ctl,
        "a4_sleeve": a4, "stress": stress,
    }
    (OUT / "_scoring_dump.json").write_text(json.dumps(dump, indent=2, default=str))

    # ---- console summary
    pl.Config.set_tbl_rows(60); pl.Config.set_tbl_cols(20); pl.Config.set_tbl_width_chars(220)
    print("\n================= DSR deflation: sr_trials_var=%.5f  N=%d =================" %
          (dump["sr_trials_var"], N_TRIALS))

    print("\n=== SCORECARD (baseline cells) — led by DSR + CVaR ===")
    print(sc.filter(pl.col("ablation") == "baseline").select(
        "model", "horizon", "dte", "n_obs", "sharpe_ann", "dsr", "dsr_stat",
        "cvar95", "cvar99", "max_dd", "ann_return", "breakeven_cbps"
    ).sort("horizon", "model"))

    print("\n=== A1: model baseline vs IV-only (common support) ===")
    print(pl.DataFrame(a1).select(
        "model", "horizon", "n_common", "ann_delta", "sharpe_model", "sharpe_iv",
        "cvar95_model", "cvar95_iv", "dm_stat", "dm_p_onesided", "boot_p_onesided").sort("horizon", "model"))

    print("\n=== A2/A3/A5/A9 attribution (marginal, significance-tested) ===")
    print(pl.DataFrame(attr).select(
        "ablation", "model", "horizon", "mean_delta", "dCVaR95", "p_dCVaR95",
        "dSharpe", "p_dSharpe", "boot_p_mean").sort("ablation", "horizon", "model"))

    print("\n=== A7 controls vs baseline (Sharpe/CVaR) ===")
    print(pl.DataFrame(ctl).sort("horizon", "model"))

    print("\n=== A4 sleeve vs clean-core on HARD_CASES ===")
    print(pl.DataFrame(a4).sort("horizon", "role", "model"))

    print("\n=== Portfolio stress (h=22 book) ===")
    print(pl.DataFrame(stress).sort("model"))

    print("\nWROTE:", OUT / "scorecard.parquet", OUT / "attribution.parquet", OUT / "_scoring_dump.json")


if __name__ == "__main__":
    main()
