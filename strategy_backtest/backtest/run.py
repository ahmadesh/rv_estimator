"""Run the full v2 put-credit-spread backtest, 2007 -> 2026 (design §0, §9).

    .venv/bin/python -m strategy_backtest.backtest.run

Builds the roll-date candidate panel (both segments), backtests every gated/sized trade on ORATS
marks held to expiry, composes the daily realized-P&L series, and writes the trades CSV, P&L charts
and the multi-aspect markdown report under `strategy_backtest/results/`.
"""

from __future__ import annotations

import time

import polars as pl

from strategy_backtest.backtest import config as cfg
from strategy_backtest.backtest import engine, management, panel, portfolio, report
from strategy_backtest.backtest import scoring

_ARMS = ("hold", "managed", "managed_no_x3")


def main() -> None:
    t0 = time.time()
    print(f"[1/4] building candidate panel ({cfg.BACKTEST_START} → {cfg.BACKTEST_END}) ...")
    candidates = panel.build_candidates()
    n_roll = candidates.height
    n_gated = int((candidates["size_units"] > 0).sum())
    by_seg = candidates.group_by("segment").agg(
        roll=pl.len(), gated=(pl.col("size_units") > 0).sum()).sort("segment")
    print(f"      {n_roll:,} roll-date candidates, {n_gated:,} pass the gate")
    for r in by_seg.iter_rows(named=True):
        print(f"        {r['segment']:11s}: {r['roll']:5,} candidates  {r['gated']:5,} gated")

    print("[2/4] opening / sizing trades on ORATS, all exit arms (hold + managed ablation, §5.2) ...")
    daily_panel = management.load_panel()
    arms: dict[str, dict] = {}
    for arm in _ARMS:
        led = engine.run_book(candidates, arm=arm, panel=daily_panel)
        dly = portfolio.to_daily(led)
        arms[arm] = {"ledger": led, "daily": dly,
                     "base": scoring.base_metrics(dly) if not dly.is_empty() else {},
                     "trades": scoring.trade_metrics(led)}
        print(f"      {arm:14s}: {led.height:,} trades")

    primary = cfg.EXIT_ARM
    ledger, daily = arms[primary]["ledger"], arms[primary]["daily"]
    if ledger.is_empty():
        print("      no trades — aborting (check chain coverage / gate thresholds)")
        return

    print(f"[3/4] composing daily P&L series (primary arm: {primary}) ...")

    print("[4/4] writing report + charts ...")
    res = report.write_report(ledger, daily, cfg.RESULTS_ROOT, arms=arms, primary=primary)

    b, tr = res["base"], res["trades"]
    ci = res["ci"]
    print("\n" + "=" * 68)
    print(f"  PUT-CREDIT-SPREAD BACKTEST — {tr['n_trades']:,} trades, "
          f"{b['span_years']} yrs, NAV ${cfg.NAV/1e6:.1f}M")
    print("=" * 68)
    print(f"  Total P&L        : ${b['pnl_total']:,.0f}  ({b['pnl_total']/cfg.NAV*100:+.1f}% NAV)")
    print(f"  Ann return       : ${b['ann_return_$']:,.0f}  ({b['ann_return_pct']*100:+.2f}% NAV)")
    print(f"  Sharpe / Sortino : {b['sharpe_ann']:.2f} / {b['sortino_ann']:.2f}")
    print(f"  Max drawdown     : ${b['max_dd_$']:,.0f}  ({b['max_dd_pct_nav']*100:.1f}% NAV)  "
          f"[95% CI ${ci['max_dd']['lo']:,.0f} .. ${ci['max_dd']['hi']:,.0f}]")
    print(f"  CVaR95 / day     : ${b['cvar95_$']:,.0f}  "
          f"[95% CI ${ci['cvar95']['lo']:,.0f} .. ${ci['cvar95']['hi']:,.0f}]")
    print(f"  Trade win rate   : {tr['trade_win_rate']*100:.1f}%   "
          f"breach rate {tr['breach_rate']*100:.1f}%")
    print(f"  Effective-N days : {b['effective_n']}  (of {b['n_obs_days']} obs)")
    print(f"  Break-even cost  : ×{tr['breakeven_cost_mult']:.1f}")
    print("=" * 68)
    print(f"  artifacts -> {cfg.RESULTS_ROOT}")
    print(f"    trades.csv · daily_pnl.csv · equity_curve.png · pnl_breakdown.png · strategy_report.md")
    print(f"  ({time.time()-t0:.1f}s)")


if __name__ == "__main__":
    main()
