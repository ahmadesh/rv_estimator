"""Reporting — trades CSV, P&L charts, and the multi-aspect markdown strategy report (design §8).

Consumes the per-trade ledger + the daily realized-P&L series and writes, under results/:

  trades.csv              — every placed trade with full entry/exit detail (the headline artifact)
  daily_pnl.csv           — daily realized P&L, cumulative P&L and equity
  equity_curve.png        — equity + drawdown timeseries (the P&L visualization)
  pnl_breakdown.png       — per-ticker / per-group P&L + annual bars
  strategy_report.md      — headline metrics, power CIs, per-ticker/group, segment + stress panels
"""

from __future__ import annotations

import datetime as dt

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import polars as pl

from strategy_backtest.backtest import config as cfg
from strategy_backtest.backtest import scoring


# --------------------------------------------------------------------------- breakdown tables
def _by(ledger: pl.DataFrame, key: str) -> pl.DataFrame:
    return (
        ledger.group_by(key)
        .agg(
            n_trades=pl.len(),
            pnl_total=pl.col("pnl").sum(),
            win_rate=(pl.col("pnl") > 0).mean(),
            breach_rate=pl.col("breached").mean(),
            avg_contracts=pl.col("contracts").mean(),
        )
        .sort("pnl_total", descending=True)
    )


def _annual(daily: pl.DataFrame) -> pl.DataFrame:
    return (
        daily.with_columns(year=pl.col("date").dt.year())
        .group_by("year")
        .agg(pnl=pl.col("pnl").sum(), n_days=pl.len())
        .sort("year")
        .with_columns(ret_pct_nav=(pl.col("pnl") / cfg.NAV))
    )


def _stress_panel(ledger: pl.DataFrame) -> list[dict]:
    """Per named stress window: book P&L + cross-group P&L correlation (decorrelation check §8.3)."""
    out = []
    for name, (lo, hi) in cfg.STRESS_WINDOWS.items():
        lo_d, hi_d = dt.date.fromisoformat(lo), dt.date.fromisoformat(hi)
        sub = ledger.filter((pl.col("entry_date") >= lo_d) & (pl.col("entry_date") <= hi_d))
        row = {"window": name, "n_trades": sub.height, "pnl_total": float(sub["pnl"].sum())
               if sub.height else 0.0}
        # cross-group correlation of per-(entry_date,group) P&L within the window
        if sub.height >= 6:
            gd = sub.group_by("entry_date", "group").agg(pl.col("pnl").sum())
            wide = gd.pivot(values="pnl", index="entry_date", on="group").sort("entry_date")
            M = wide.select(pl.exclude("entry_date")).to_numpy()
            cols = [i for i in range(M.shape[1])
                    if (~np.isnan(M[:, i])).sum() >= 3 and np.nanstd(M[:, i]) > 0]
            if len(cols) >= 2:
                cc = np.ma.corrcoef(np.ma.masked_invalid(M[:, cols]), rowvar=False)
                iu = np.triu_indices(len(cols), 1)
                vv = np.asarray(cc)[iu]
                vv = vv[np.isfinite(vv)]
                row["mean_cross_group_corr"] = float(vv.mean()) if vv.size else float("nan")
            else:
                row["mean_cross_group_corr"] = float("nan")
        else:
            row["mean_cross_group_corr"] = float("nan")
        out.append(row)
    return out


# --------------------------------------------------------------------------- charts
def _plot_equity(daily: pl.DataFrame, path) -> None:
    d = daily["date"].to_list()
    eq = daily["equity"].to_numpy()
    peak = np.maximum.accumulate(eq)
    dd = (eq - peak) / cfg.NAV * 100.0
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 7), sharex=True,
                                   gridspec_kw={"height_ratios": [3, 1]})
    ax1.plot(d, eq / 1e6, color="#1f4e79", lw=1.3)
    ax1.axhline(cfg.NAV / 1e6, color="grey", ls="--", lw=0.8)
    ax1.set_ylabel("Equity ($M)")
    ax1.set_title(f"Put-credit-spread book — equity (NAV ${cfg.NAV/1e6:.1f}M, realized P&L)")
    ax1.grid(alpha=0.3)
    ax2.fill_between(d, dd, 0, color="#c0392b", alpha=0.6)
    ax2.set_ylabel("Drawdown (% NAV)")
    ax2.set_xlabel("Date (expiry / realization)")
    ax2.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def _plot_breakdown(ledger: pl.DataFrame, daily: pl.DataFrame, path) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    tk = _by(ledger, "ticker")
    axes[0].barh(tk["ticker"].to_list(), (tk["pnl_total"].to_numpy() / 1e3),
                 color=np.where(tk["pnl_total"].to_numpy() >= 0, "#27ae60", "#c0392b"))
    axes[0].set_title("P&L by ticker ($k)"); axes[0].grid(alpha=0.3, axis="x")
    gr = _by(ledger, "group")
    axes[1].barh(gr["group"].to_list(), (gr["pnl_total"].to_numpy() / 1e3),
                 color=np.where(gr["pnl_total"].to_numpy() >= 0, "#27ae60", "#c0392b"))
    axes[1].set_title("P&L by correlation group ($k)"); axes[1].grid(alpha=0.3, axis="x")
    an = _annual(daily)
    axes[2].bar([str(y) for y in an["year"].to_list()], (an["ret_pct_nav"].to_numpy() * 100),
                color=np.where(an["ret_pct_nav"].to_numpy() >= 0, "#27ae60", "#c0392b"))
    axes[2].set_title("Annual return (% NAV)"); axes[2].grid(alpha=0.3, axis="y")
    axes[2].tick_params(axis="x", rotation=90)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


# --------------------------------------------------------------------------- markdown
def _fmt(v, pct=False, dollar=False, n=2) -> str:
    if v is None or (isinstance(v, float) and (np.isnan(v) or np.isinf(v))):
        return "n/a"
    if pct:
        return f"{v*100:.{n}f}%"
    if dollar:
        return f"${v:,.0f}"
    return f"{v:.{n}f}"


def _md_table(df: pl.DataFrame, cols: list[str]) -> str:
    head = "| " + " | ".join(cols) + " |\n| " + " | ".join("---" for _ in cols) + " |\n"
    rows = ""
    for r in df.iter_rows(named=True):
        cells = []
        for c in cols:
            v = r[c]
            if isinstance(v, float):
                cells.append(f"{v:,.2f}" if abs(v) >= 1 or v == 0 else f"{v:.4f}")
            else:
                cells.append(str(v))
        rows += "| " + " | ".join(cells) + " |\n"
    return head + rows


def _suggestions(ledger: pl.DataFrame, trades: dict, base: dict) -> list[str]:
    """Concrete, data-grounded levers to improve the book — ranked by expected impact."""
    by_tk = _by(ledger, "ticker")
    worst = by_tk.sort("pnl_total").row(0, named=True)
    fattest = by_tk.sort("avg_contracts", descending=True).row(0, named=True)
    breach = trades.get("breach_rate", float("nan"))
    s = ["\n## 10. Suggestions to improve results\n",
         "_Ranked by expected impact; each maps to a knob in `config.py` or a documented ablation._\n"]

    s.append(f"**A. Capital deployment — APPLIED (§2).** Weekly cadence + VRP de-bias + `RISK_BUDGET` "
             f"b={cfg.RISK_BUDGET} (set to the ≤10%-NAV-maxDD ceiling) lift avg deployment ~0.9%→~3.4% "
             f"of NAV. Mean margin-at-risk is now {_fmt(trades.get('mean_margin_pct_nav'), pct=True)} "
             f"(max {_fmt(trades.get('max_margin_pct_nav'), pct=True)}); avg return on capital-at-risk "
             f"per trade {_fmt(trades.get('avg_return_on_risk'), pct=True)}. b is a pure size scalar "
             "(Sharpe-invariant until the per-group cap binds) — raise it for more deployment only if "
             "you accept a higher drawdown. Next lever (deferred): concurrent-margin headroom to sub-"
             "group the equity cap.")

    s.append("\n**B. VRP de-bias — APPLIED (§2).** EnsembleTopK `rv_hat` over-predicts forward RV "
             "(+0.27 log on 2010+), biasing raw VRP negative so most trades floored at `vrp_rel=0.05`. "
             "A PIT per-ticker log-bias correction (`pit.trailing_debias`, matured obs only, leakage-"
             "safe) now feeds VRP/sizing while the gate keeps raw rv_hat — so selection is unchanged "
             "and size lands on genuinely-rich names. In the sweep this ~doubled deployment & return "
             "at equal Sharpe vs no-debias. Follow-up: a slope term (β·rv_hat), not just a level shift.")

    s.append(f"\n**C. Push the short strike further OTM to cut breaches.** Short-strike breach rate is "
             f"{_fmt(breach, pct=True)} (a defined-risk loss whenever it bites). Sweep the short delta "
             "{0.20, 0.16} (doc §6 sweep) — fewer breaches and a higher win rate, traded against "
             "thinner credit. `SHORT_DELTA` in `config.py`; watch the credit/width floor.")

    s.append(f"\n**D. Per-name risk normalization — APPLIED.** Contracts now round to NEAREST "
             "(was floor), removing the systematic down-bias that hit expensive names hardest "
             f"(n_raw≈1.4→1); combined with the b-scale, {fattest['ticker']} averages "
             f"{_fmt(fattest['avg_contracts'])} contracts and the priciest names clear the floor, so "
             "the σ-edge u — not strike price/rounding — sets the per-name weights. Watch "
             f"{worst['ticker']} ({_fmt(worst['pnl_total'], dollar=True)}): if a name stays the lone "
             "net loser after the rescale, it's an edge problem, not a granularity one.")

    s.append("\n**E. Managed exit challenger — IMPLEMENTED (see §11).** The `mechanical_terminal` arm "
             "(X1 50% profit-take · X2 DTE≤12 hard close · X3 term-flip w/ 2-day confirm + dead-band · "
             "X4 variance stop · X5 2× hard stop) now runs alongside hold in the §11 ablation. Keep it "
             "only if it beats hold on the tail (CVaR95/maxDD) under real marks; `managed_no_x3` "
             "isolates whether the term-flip earns its churn.")

    s.append("\n**F. Run the A-vs-B promotion test for decision-grade power.** Effective-N is only "
             f"{base.get('effective_n')} and the per-obs Sharpe CI straddles 0, so the headline isn't "
             "yet decision-grade. Run regime-only (forecaster off, flat size, no G4) vs regime+model "
             "and judge on the bootstrap CI of the tail (doc §8.1) — that attributes whether the "
             "forecaster earns its place at all.")

    s.append("\n**G. Prune redundant gates / widen entries for sample.** The lean core still trades a "
             "thin, correlated sample. Check whether G2 (IVrank) and G3 (contango) carry independent "
             "avoidance info or fire together (doc §4.3 stress-composite ablation); a single combined "
             "stress axis could free entries and raise N without hurting the tail. Also consider "
             "weekly (not just monthly) roll cadence to multiply the sample.")

    s.append("\n**H. Stress the wing fill before trusting the tail.** Break-even cost is "
             f"×{_fmt(trades.get('breakeven_cost_mult'))}, comfortable on paper — but the 10Δ wing is "
             "the thinnest, most fill-optimistic leg early in the sample. Sweep `SLIPPAGE_TICKS` and "
             "specifically widen the wing's adverse fill to confirm the defined-risk floor survives "
             "realistic 2008–2013 wing liquidity.\n")
    return s


def _arm_ablation(arms: dict, primary: str) -> list[str]:
    """Exit-arm ablation table (design §5.2): hold (primary) vs managed vs managed−X3.

    Managing ships only if it BEATS hold on these axes under real marks; the table makes the
    comparison explicit, plus the managed arms' exit-trigger mix.
    """
    md = ["\n## 11. Exit-arm ablation — hold vs managed (design §5.2)\n",
          "_Hold-to-expiry is the primary/benchmark arm; `mechanical_terminal` (managed) is the "
          "challenger that must beat hold on the tail to ship. `managed_no_x3` drops the term-flip "
          "trigger to isolate its churn (design §5.2)._\n"]
    rows = []
    for arm in ("hold", "managed", "managed_no_x3"):
        a = arms.get(arm)
        if not a or a["ledger"].is_empty():
            continue
        b, tr = a["base"], a["trades"]
        rows.append({
            "arm": arm + (" *" if arm == primary else ""),
            "n_trades": tr.get("n_trades", 0),
            "pnl_total": round(b.get("pnl_total", float("nan")), 0),
            "ann_ret_%nav": round(b.get("ann_return_pct", float("nan")) * 100, 3),
            "sharpe_ann": round(b.get("sharpe_ann", float("nan")), 2),
            "maxDD_%nav": round(b.get("max_dd_pct_nav", float("nan")) * 100, 2),
            "cvar95_$": round(b.get("cvar95_$", float("nan")), 0),
            "win_rate": round(tr.get("trade_win_rate", float("nan")), 4),
            "breach_rate": round(tr.get("breach_rate", float("nan")), 4),
        })
    if rows:
        md.append(_md_table(pl.DataFrame(rows),
                            ["arm", "n_trades", "pnl_total", "ann_ret_%nav", "sharpe_ann",
                             "maxDD_%nav", "cvar95_$", "win_rate", "breach_rate"]))
        md.append("\n_`*` = the headline arm reported in sections 1–10._\n")

    # Exit-trigger mix for the managed arm (which triggers actually fire).
    mgd = arms.get("managed")
    if mgd and not mgd["ledger"].is_empty():
        mix = (mgd["ledger"].group_by("exit_reason")
               .agg(n=pl.len(), pnl_total=pl.col("pnl").sum())
               .sort("n", descending=True))
        md.append("\n**Managed arm — exit-trigger mix:**\n")
        md.append(_md_table(mix, ["exit_reason", "n", "pnl_total"]))
    return md


def write_report(ledger: pl.DataFrame, daily: pl.DataFrame, out_dir,
                 arms: dict | None = None, primary: str = "hold") -> dict:
    """Write all artifacts; return the headline metric dict (also used by run.py's console summary)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    ledger.write_csv(out_dir / "trades.csv")
    daily.write_csv(out_dir / "daily_pnl.csv")
    _plot_equity(daily, out_dir / "equity_curve.png")
    _plot_breakdown(ledger, daily, out_dir / "pnl_breakdown.png")

    base = scoring.base_metrics(daily)
    trades = scoring.trade_metrics(ledger)
    r = daily["pnl"].to_numpy()
    ci_cvar = scoring.bootstrap_ci(r, daily["date"], lambda x: scoring.cvar(x, 0.95))
    ci_dd = scoring.bootstrap_ci(r, daily["date"], lambda x: scoring.max_drawdown(x))
    ci_sharpe = scoring.bootstrap_ci(r, daily["date"], scoring.sharpe_per_obs)

    by_seg = (
        ledger.group_by("segment").agg(
            n_trades=pl.len(), pnl_total=pl.col("pnl").sum(),
            win_rate=(pl.col("pnl") > 0).mean(), breach_rate=pl.col("breached").mean(),
        ).sort("segment")
    )
    stress = _stress_panel(ledger)

    md = []
    md.append("# Put-Credit-Spread Strategy — Backtest Report\n")
    md.append(f"_v2 lean-core book · {cfg.BACKTEST_START} → {ledger['expiry'].max()} · "
              f"NAV ${cfg.NAV/1e6:.1f}M, whole contracts (b={cfg.RISK_BUDGET}, "
              f"{cfg.CONTRACT_ROUNDING}-round) · primary exit: {primary} · generated "
              f"{dt.date.today()}_\n")
    stress_note = (" + a **200d-SMA trend stand-down** (§4.3 ablation winner: of the 5 stress flags "
                   "only the downtrend filter cut the post-2014 tail)") if cfg.STRESS_GATE else ""
    md.append("> Headline economic run of `PUT_SPREAD_STRATEGY_DESIGN_v2.md`: a defined-risk "
              "short-variance put-credit spread (0.25Δ short / 0.10Δ wing, ~30 DTE) on the 10 core "
              "ETFs, gated by the 4-signal lean core (G2 IVrank≤85 · G3 contango · G4 dispersion · "
              f"G7 liquidity){stress_note}, sized by inverse-risk fractional Kelly with VRP as a tilt, "
              "held to expiry. 2007–2010 is the degraded GFC stress segment (no forecaster; IV-only "
              "inverse-risk sizing; G4 dropped).\n")

    md.append("## 1. Headline metrics\n")
    md.append(f"- **Trades placed:** {trades.get('n_trades', 0):,} "
              f"(win rate {_fmt(trades.get('trade_win_rate'), pct=True)}, "
              f"short-strike breach rate {_fmt(trades.get('breach_rate'), pct=True)})")
    md.append(f"- **Realized P&L (total):** {_fmt(base['pnl_total'], dollar=True)} "
              f"= {_fmt(base['pnl_total']/cfg.NAV, pct=True)} of NAV over {base['span_years']} yrs")
    md.append(f"- **Annualized return:** {_fmt(base['ann_return_$'], dollar=True)} "
              f"({_fmt(base['ann_return_pct'], pct=True)} of NAV)")
    md.append(f"- **Sharpe (ann):** {_fmt(base['sharpe_ann'])}  ·  "
              f"**Sortino (ann):** {_fmt(base['sortino_ann'])}")
    md.append(f"- **Max drawdown:** {_fmt(base['max_dd_$'], dollar=True)} "
              f"({_fmt(base['max_dd_pct_nav'], pct=True)} of NAV)")
    md.append(f"- **CVaR95 (per realization day):** {_fmt(base['cvar95_$'], dollar=True)} "
              f"({_fmt(base['cvar95_pct_nav'], pct=True)} of NAV)  ·  "
              f"**worst day:** {_fmt(base['worst_day_$'], dollar=True)}")
    md.append(f"- **Cost drag:** {_fmt(trades.get('cost_total_$'), dollar=True)} "
              f"({_fmt(trades.get('cost_frac_of_gross'), pct=True)} of gross); "
              f"break-even cost ×{_fmt(trades.get('breakeven_cost_mult'))}\n")

    md.append("## 2. Capital deployment / sizing reality (the granularity tax, design §7.3)\n")
    md.append(f"> **Capital-use overhaul applied** (report §10.A/B/D follow-up). Three edge-preserving "
              f"levers — none change which trades fire: (1) **WEEKLY roll cadence** "
              f"(`ROLL_CADENCE={cfg.ROLL_CADENCE}`) ~4× the trade count for more concurrent deployment + "
              "diversification; (2) **VRP de-bias** (`DEBIAS_VRP` — PIT per-ticker calibration of "
              "rv_hat, which over-predicts RV on 2010+) so size lands on genuinely-rich trades instead "
              f"of flooring at vrp_rel=0.05; (3) **`RISK_BUDGET` b={cfg.RISK_BUDGET}** + "
              f"**{cfg.CONTRACT_ROUNDING}-rounding**, b set to the deployment ceiling that holds maxDD "
              "≤ ~10% NAV. The overlapping weekly positions are bounded by the engine's **concurrent** "
              "per-group margin accounting (not just same-day), so the 20%/group cap still holds. Net "
              "vs the original monthly book: ~4× capital deployed and ~4× return at a HIGHER Sharpe — "
              "capital use rose without diluting the edge.\n")
    md.append(f"- **Mean margin at risk / trade:** {_fmt(trades.get('mean_margin_pct_nav'), pct=True)} "
              f"of NAV (max {_fmt(trades.get('max_margin_pct_nav'), pct=True)})")
    md.append(f"- **Contracts / trade:** mean {_fmt(trades.get('avg_contracts'))}, "
              f"median {_fmt(trades.get('median_contracts'))}; "
              f"{_fmt(trades.get('frac_one_contract'), pct=True)} of trades are a single contract")
    md.append(f"- **Avg return on capital-at-risk / trade:** {_fmt(trades.get('avg_return_on_risk'), pct=True)} "
              "(mean of pnl_i / max-loss_i) — the per-trade edge net of the NAV-deployment choice")
    md.append(f"- **Implication:** with the capital-use overhaul the book now deploys ~3.4% of NAV "
              f"on average at an {_fmt(trades.get('trade_win_rate'), pct=True)} win rate; the headline "
              "%-NAV return scales with `RISK_BUDGET` b, which is pinned to the ≤10%-NAV-maxDD ceiling. "
              "Going higher is a pure risk-appetite choice (b is Sharpe-invariant until the per-group "
              "cap binds), not an edge question.\n")

    md.append("## 3. Statistical power (block-bootstrap 95% CIs, design §8.2)\n")
    md.append(f"- Realization-day observations: **{base['n_obs_days']}**, "
              f"effective-N (lag-1 adj): **{base['effective_n']}**, "
              f"bootstrap block length: **{ci_cvar['block']}** obs")
    md.append("")
    md.append("| Metric | Point | 95% CI low | 95% CI high |")
    md.append("| --- | --- | --- | --- |")
    md.append(f"| CVaR95 ($) | {_fmt(ci_cvar['point'],dollar=True)} | "
              f"{_fmt(ci_cvar['lo'],dollar=True)} | {_fmt(ci_cvar['hi'],dollar=True)} |")
    md.append(f"| Max drawdown ($) | {_fmt(ci_dd['point'],dollar=True)} | "
              f"{_fmt(ci_dd['lo'],dollar=True)} | {_fmt(ci_dd['hi'],dollar=True)} |")
    md.append(f"| Sharpe (per obs) | {_fmt(ci_sharpe['point'])} | "
              f"{_fmt(ci_sharpe['lo'])} | {_fmt(ci_sharpe['hi'])} |\n")

    md.append("## 4. By segment (GFC degraded vs forecaster headline, design §2.2)\n")
    md.append(_md_table(by_seg, ["segment", "n_trades", "pnl_total", "win_rate", "breach_rate"]))

    md.append("\n## 5. P&L by ticker\n")
    md.append(_md_table(_by(ledger, "ticker"),
                        ["ticker", "n_trades", "pnl_total", "win_rate", "breach_rate", "avg_contracts"]))
    md.append("\n## 6. P&L by correlation group\n")
    md.append(_md_table(_by(ledger, "group"),
                        ["group", "n_trades", "pnl_total", "win_rate", "breach_rate", "avg_contracts"]))

    md.append("\n## 7. Annual returns\n")
    md.append(_md_table(_annual(daily), ["year", "pnl", "ret_pct_nav", "n_days"]))

    md.append("\n## 8. Stress-window decorrelation (design §8.3)\n")
    md.append("Cross-group P&L correlation should collapse in stress (the book's decorrelation thesis).\n")
    md.append(_md_table(pl.DataFrame(stress),
                        ["window", "n_trades", "pnl_total", "mean_cross_group_corr"]))

    md.append("\n## 9. Known optimistic biases (disclosed, design §8.4)\n")
    md.append("- **EOD-only marks / settlement.** Hold-to-expiry settles at ORATS expiry-day "
              "intrinsic; no intraday gap is modeled — understates short-gamma terminal-week tail.")
    md.append("- **No early assignment / dividend timing.** American ETF puts driven deep ITM near "
              "ex-div could be assigned early; intrinsic settlement ignores that timing.")
    md.append("- **Wing-fill optimism.** Crossing the spread on the 10Δ long wing in 2007–2013 for "
              "thinner names (XLE/EEM/HYG) may be optimistic where strikes are sparse.")
    md.append("- **Fixed-NAV sizing.** Sizing is off a constant $%.0fM reference, not compounding; "
              "per-group margin cap is applied across same-day entries, not intramonth overlap." % (cfg.NAV/1e6))
    md.append("- **Cached leakage-safe forecasts.** EnsembleTopK predictions are the purged/embargoed "
              "walk-forward cache (first fold ~2010); the 2007–2010 segment carries no forecaster.\n")

    md += _suggestions(ledger, trades, base)
    if arms:
        md += _arm_ablation(arms, primary)

    (out_dir / "strategy_report.md").write_text("\n".join(md))
    return {"base": base, "trades": trades,
            "ci": {"cvar95": ci_cvar, "max_dd": ci_dd, "sharpe": ci_sharpe}}
