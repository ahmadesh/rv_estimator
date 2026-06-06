"""Stage-2 economic scoring layer (STAGE2_STRATEGY_REFINEMENT_PLAN.md Part D / §C-§E).

Pure scoring of the FROZEN Stage-2 option-marks result files under
`stage2_trade_eval/results/`. No refits, no engine changes. Reads
ledger/<cell>.parquet + portfolio/<cell>.parquet + manifest.parquet and emits, into
`stage2_trade_eval/results/`:

  scorecard.parquet     -- per (model, horizon, ablation) economic scorecard
  attribution.parquet   -- per cell vs option-space IV-only null (DM + block bootstrap)
  verdicts.parquet      -- headline Go/No-Go verdict per non-benchmark cell
  _scoring_dump.json    -- structured tables behind the parquets

Differences from Stage-1 (`trade_eval/reports/score_stage1.py`), which this adapts:
  * Points at `stage2_trade_eval/results/`, NOT the Stage-1 trade_eval paths.
  * P&L is in DOLLARS for the sized position (the ledger's `pnl`), not variance units.
  * The null / benchmark is the **option-space** IV-only book (`model="IV-only"`, same
    structure, flat size, no gate) — "beating an option IV-only seller is the bar",
    NOT the variance-proxy IV-only.
  * N_TRIALS is the **live** Stage-2 manifest cell count read at runtime (DO NOT hardcode
    104); the DSR re-deflates by that count.

Reuses the HAC Diebold-Mariano + moving-block bootstrap machinery from
`rv_eval.metrics.tier2` (`diebold_mariano`, `_block_bootstrap_idx`).
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

from stage2_trade_eval import config as cfg

RESULTS = cfg.RESULTS_ROOT
LEDGER = cfg.LEDGER_ROOT
PORT = cfg.PORTFOLIO_ROOT
MANIFEST = cfg.MANIFEST_PARQUET
OUT = RESULTS                       # scorecard/attribution/verdicts land back in results/
OUT.mkdir(parents=True, exist_ok=True)

TPY = C.TRADING_DAYS_PER_YEAR       # 252
EULER = 0.5772156649015329
BENCHMARK = cfg.BENCHMARK           # "IV-only" — option-space null
BOOT_B = 4000
SEED = 7

# DTE label for the primary horizon family (purely cosmetic, mirrors Stage-1 spirit).
_DTE_BY_H = {5: 7, 10: 14, 22: 30}


# --------------------------------------------------------------------------- IO
def _stem(model: str, h: int, ab: str) -> str:
    return f"{model}__h{h}__{ab}"


def load_port(model: str, h: int, ab: str) -> pl.DataFrame | None:
    p = PORT / f"{_stem(model, h, ab)}.parquet"
    if not p.exists():
        return None
    df = pl.read_parquet(p)
    if df.height == 0:
        return None
    return df.select("date", "pnl", "gross_pnl", "cost", "n_positions").sort("date")


def load_ledger(model: str, h: int, ab: str) -> pl.DataFrame | None:
    p = LEDGER / f"{_stem(model, h, ab)}.parquet"
    if not p.exists():
        return None
    df = pl.read_parquet(p)
    return df if df.height else None


def load_manifest() -> pl.DataFrame:
    if not MANIFEST.exists():
        raise FileNotFoundError(f"no Stage-2 manifest at {MANIFEST}; run the grid first")
    return pl.read_parquet(MANIFEST)


def n_trials_live() -> int:
    """DSR deflation count = the ACTUAL Stage-2 manifest cell count (NOT hardcoded 104).

    Counts unique (model, horizon, ablation) cells in the live manifest — the multiple-testing
    surface = models × horizons × structures × mgmt-arms × hedge-modes × any tuned configs.
    """
    man = load_manifest()
    return int(man.select(["model", "horizon", "ablation"]).unique().height)


# --------------------------------------------------------------------------- core stats
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
    m = r.mean()
    s = r.std(ddof=0)
    if s == 0:
        return 0.0, 3.0
    g1 = float(((r - m) ** 3).mean() / s ** 3)
    g2 = float(((r - m) ** 4).mean() / s ** 4)
    return g1, g2


def dsr(r: np.ndarray, sr_trials_var: float, n_trials: int) -> dict:
    """Deflated Sharpe Ratio (Bailey & Lopez de Prado 2014), deflated by `n_trials`.

    `sr_trials_var` = variance of the per-observation Sharpe estimates across all trials.
    Returns P(true per-obs SR > deflated benchmark SR0).
    """
    n = r.size
    sr = sharpe_per_obs(r)
    g1, g2 = _moments(r)
    z1 = norm.ppf(1.0 - 1.0 / n_trials)
    z2 = norm.ppf(1.0 - 1.0 / (n_trials * math.e))
    sr0 = math.sqrt(max(sr_trials_var, 1e-18)) * ((1.0 - EULER) * z1 + EULER * z2)
    denom = math.sqrt(max(1.0 - g1 * sr + (g2 - 1.0) / 4.0 * sr * sr, 1e-12))
    stat = (sr - sr0) * math.sqrt(max(n - 1, 1)) / denom
    return {"sr_obs": sr, "sr0": sr0, "dsr": float(norm.cdf(stat)),
            "dsr_stat": float(stat), "skew": g1, "kurt": g2}


def cvar(r: np.ndarray, q: float) -> float:
    """Mean of the worst (1-q) tail of $-P&L (a loss, negative). q in (0,1)."""
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


# --------------------------------------------------------------------------- significance
def block_len_obs(dates: pl.Series) -> int:
    """Moving-block length in OBSERVATION units covering >=22 calendar days.

    The portfolio series is at the roll cadence (each obs aggregates ~h days), so a block of
    >=22 *calendar* days is a small number of observations.
    """
    d = dates.sort()
    gaps = d.diff().dt.total_days().drop_nulls()
    g = float(gaps.median()) if len(gaps) else 22.0
    return max(2, int(math.ceil(22.0 / max(g, 1.0))))


def boot_mean_pvalue(delta: np.ndarray, block: int, B: int = BOOT_B, seed: int = SEED) -> float:
    """Moving-block bootstrap one-sided p for H0: mean(delta) <= 0 (model not better than null).

    Reuses `_block_bootstrap_idx` from rv_eval.metrics.tier2.
    """
    n = delta.size
    if n < 3:
        return 1.0
    rng = np.random.default_rng(seed)
    idx = _block_bootstrap_idx(n, min(block, n), B, rng)
    bm = delta[idx].mean(axis=1)
    return float((bm <= 0.0).mean())


def hac_dm_onesided(delta: np.ndarray, h: int) -> tuple[float, float]:
    """One-sided HAC (Newey-West) test of mean(delta) > 0, reusing tier2.diebold_mariano.

    `diebold_mariano` returns (stat, two_sided_p) with HAC lag h-1; convert to the one-sided
    p for H1: mean(delta) > 0.
    """
    if delta.size < 3:
        return 0.0, 1.0
    stat, _ = diebold_mariano(delta, h)
    return float(stat), float(1.0 - norm.cdf(stat))


# --------------------------------------------------------------------------- cell enumeration
def enumerate_cells(man: pl.DataFrame) -> list[tuple[str, int, str, bool]]:
    """(model, horizon, ablation, is_benchmark) for every manifest cell with a portfolio file."""
    cells = []
    for row in man.select(["model", "horizon", "ablation", "is_benchmark"]).unique().iter_rows(named=True):
        model, h, ab = row["model"], int(row["horizon"]), row["ablation"]
        if load_port(model, h, ab) is None:
            continue
        cells.append((model, h, ab, bool(row["is_benchmark"])))
    return cells


def _structure_of(ablation: str) -> str:
    """Structure family = first component of the `structure__management__hedge` ablation key."""
    return ablation.split("__", 1)[0]


def _benchmark_for(structure: str, h: int) -> pl.DataFrame | None:
    """Option-space IV-only null for a structure: model=IV-only, same structure, flat/hold/none.

    The benchmark book is rebuilt in option space with the same structure but flat size and no
    gate (engine runs `model="IV-only"`). Match on the structure family at horizon `h`; prefer a
    `hold__none` management/hedge if present, else any IV-only cell on that structure.
    """
    cand = [BENCHMARK, h]
    # exact hold__none first
    exact = load_port(BENCHMARK, h, f"{structure}__hold__none")
    if exact is not None:
        return exact
    # else any IV-only cell sharing the structure family
    if not MANIFEST.exists():
        return None
    man = load_manifest()
    matches = (man.filter((pl.col("model") == BENCHMARK) & (pl.col("horizon") == h))
                  .filter(pl.col("ablation").str.starts_with(f"{structure}__")))
    for ab in matches["ablation"].unique().to_list():
        p = load_port(BENCHMARK, h, ab)
        if p is not None:
            return p
    return None


# --------------------------------------------------------------------------- 1. SCORECARD
def build_scorecard(cells: list, n_trials: int) -> pl.DataFrame:
    # first pass: per-obs Sharpe of every cell -> trial variance for DSR deflation
    sr_list = []
    for model, h, ab, _ in cells:
        port = load_port(model, h, ab)
        if port is None or port.height < 3:
            continue
        sr_list.append(sharpe_per_obs(port["pnl"].to_numpy()))
    sr_trials_var = float(np.var(np.array(sr_list), ddof=1)) if len(sr_list) > 1 else 0.0

    rows = []
    for model, h, ab, is_bench in cells:
        port = load_port(model, h, ab)
        if port is None or port.height < 1:
            continue
        led = load_ledger(model, h, ab)
        r = port["pnl"].to_numpy()
        m = base_metrics(port)
        if r.size >= 3:
            m.update(dsr(r, sr_trials_var, n_trials))
        else:
            m.update({"sr_obs": sharpe_per_obs(r), "sr0": float("nan"),
                      "dsr": float("nan"), "dsr_stat": float("nan"),
                      "skew": float("nan"), "kurt": float("nan")})
        m["model"], m["horizon"], m["ablation"] = model, h, ab
        m["structure"] = _structure_of(ab)
        m["is_benchmark"] = is_bench
        m["dte"] = _DTE_BY_H.get(h, h)

        if led is not None and led.height:
            g = float(led["gross_pnl"].sum())
            c = float(led["cost"].sum())
            m["gross_total"] = g
            m["cost_total"] = c
            m["cost_frac_of_gross"] = c / abs(g) if g != 0 else float("nan")
            m["n_trades"] = int(led.height)
        else:
            m["gross_total"] = m["cost_total"] = float("nan")
            m["cost_frac_of_gross"] = float("nan")
            m["n_trades"] = 0
        rows.append(m)

    df = pl.DataFrame(rows)
    df = df.with_columns(pl.lit(sr_trials_var).alias("sr_trials_var"),
                         pl.lit(n_trials).alias("n_trials_deflation"))
    return df


# --------------------------------------------------------------------------- 2. vs option IV-only null
def attribution(cells: list) -> list[dict]:
    """Per non-benchmark cell vs the option-space IV-only null (same structure): DM + bootstrap."""
    out = []
    for model, h, ab, is_bench in cells:
        if is_bench or model == BENCHMARK:
            continue
        mp = load_port(model, h, ab)
        structure = _structure_of(ab)
        iv = _benchmark_for(structure, h)
        if mp is None or iv is None:
            continue
        j = (mp.select("date", "pnl").join(
                iv.select("date", pl.col("pnl").alias("pnl_iv")), on="date", how="inner")
             .sort("date"))
        if j.height < 1:
            continue
        a = j["pnl"].to_numpy()
        b = j["pnl_iv"].to_numpy()
        delta = a - b
        blk = block_len_obs(j["date"])
        stat, p_dm = hac_dm_onesided(delta, h)
        p_boot = boot_mean_pvalue(delta, blk)
        out.append({
            "model": model, "horizon": h, "ablation": ab, "structure": structure,
            "benchmark": BENCHMARK,
            "n_common": j.height,
            "mean_delta": float(delta.mean()),
            "ann_delta": float(delta.mean() * (j.height / _span_years(j["date"]))),
            "sharpe_model": sharpe_per_obs(a), "sharpe_iv": sharpe_per_obs(b),
            "cvar95_model": cvar(a, 0.95), "cvar95_iv": cvar(b, 0.95),
            "maxdd_model": max_drawdown(a), "maxdd_iv": max_drawdown(b),
            "worst20_model": worst_k(a, 20), "worst20_iv": worst_k(b, 20),
            "dm_stat": stat, "dm_p_onesided": p_dm, "boot_p_onesided": p_boot,
            "block_obs": blk,
        })
    return out


# --------------------------------------------------------------------------- 3. verdicts
def verdicts(sc: pl.DataFrame, attr: list[dict]) -> list[dict]:
    """Headline Go/No-Go fields per non-benchmark cell: DSR + tail + beat-IV significance.

    NO ranking / interpretation — just the assembled headline statistics the report consumes.
    """
    attr_idx = {(a["model"], a["horizon"], a["ablation"]): a for a in attr}
    out = []
    for row in sc.iter_rows(named=True):
        if row["is_benchmark"]:
            continue
        key = (row["model"], row["horizon"], row["ablation"])
        a = attr_idx.get(key)
        out.append({
            "model": row["model"], "horizon": row["horizon"], "ablation": row["ablation"],
            "structure": row["structure"],
            "n_obs": row["n_obs"], "n_trades": row["n_trades"],
            "dsr": row["dsr"], "dsr_stat": row["dsr_stat"],
            "sharpe_ann": row["sharpe_ann"], "ann_return": row["ann_return"],
            "cvar95": row["cvar95"], "cvar99": row["cvar99"],
            "max_dd": row["max_dd"], "worst_20": row["worst_20"],
            "beat_iv_mean_delta": a["mean_delta"] if a else float("nan"),
            "beat_iv_dm_p": a["dm_p_onesided"] if a else float("nan"),
            "beat_iv_boot_p": a["boot_p_onesided"] if a else float("nan"),
            "n_trials_deflation": row["n_trials_deflation"],
        })
    return out


# --------------------------------------------------------------------------- run
def main():
    man = load_manifest()
    n_trials = n_trials_live()
    cells = enumerate_cells(man)

    sc = build_scorecard(cells, n_trials)
    sc.write_parquet(OUT / "scorecard.parquet")

    attr = attribution(cells)
    pl.DataFrame(attr).write_parquet(OUT / "attribution.parquet")

    verd = verdicts(sc, attr)
    pl.DataFrame(verd).write_parquet(OUT / "verdicts.parquet")

    dump = {
        "sr_trials_var": float(sc["sr_trials_var"][0]) if sc.height else float("nan"),
        "n_trials": n_trials,
        "benchmark": BENCHMARK,
        "n_cells_scored": len(cells),
        "scorecard": sc.to_dicts(),
        "attribution": attr,
        "verdicts": verd,
    }
    (OUT / "_scoring_dump.json").write_text(json.dumps(dump, indent=2, default=str))

    # ---- console summary
    pl.Config.set_tbl_rows(60); pl.Config.set_tbl_cols(20); pl.Config.set_tbl_width_chars(220)
    print("\n===== Stage-2 DSR deflation: sr_trials_var=%.6g  N_TRIALS=%d (LIVE manifest) =====" %
          (dump["sr_trials_var"], n_trials))

    print("\n=== SCORECARD ($-P&L per sized position) ===")
    print(sc.select(
        "model", "horizon", "structure", "ablation", "n_obs", "n_trades",
        "sharpe_ann", "dsr", "dsr_stat", "cvar95", "cvar99", "max_dd",
        "worst_20", "ann_return", "is_benchmark"
    ).sort("horizon", "model", "ablation"))

    if attr:
        print("\n=== vs OPTION-SPACE IV-only null (same structure) — DM + bootstrap ===")
        print(pl.DataFrame(attr).select(
            "model", "horizon", "structure", "n_common", "ann_delta",
            "sharpe_model", "sharpe_iv", "cvar95_model", "cvar95_iv",
            "dm_stat", "dm_p_onesided", "boot_p_onesided").sort("horizon", "model"))
    else:
        print("\n=== vs OPTION-SPACE IV-only null: no non-benchmark cell with a matching null ===")

    print("\nWROTE:",
          OUT / "scorecard.parquet", OUT / "attribution.parquet",
          OUT / "verdicts.parquet", OUT / "_scoring_dump.json")


if __name__ == "__main__":
    main()
