"""P&L wiring + the §3.5 fidelity claim, on a controlled synthetic panel.

Two contracts:
  1. hold-to-expiry books exactly `size · sign_short · (iv2 − target_var) − cost`;
  2. when no management rule fires, the managed daily variance-accrual mark at expiry collapses
     to the hold-to-expiry payoff (the overlay only ever *changes* P&L by exiting early).

The panel is constructed so target_var == Σ daily total_rv over the window, which is what makes
the terminal accrual identity exact; management thresholds are pushed to infinity so the
no-exit branch is the one under test.
"""

from __future__ import annotations

import datetime as dt

import polars as pl

from trade_eval import backtest, config as cfg
from trade_eval.signals import StrategyConfig

H = 5
TICKER = "SPY"           # must be in cfg.GROUP
TOTAL_RV = 2e-5
TARGET_VAR = H * TOTAL_RV  # 1e-4, by construction == accrued realized var over the window
IV2 = 1e-3                 # rich premium so vrp>0 and the variance stop never binds
RV_HAT = TARGET_VAR        # point forecast (value is irrelevant to the identities)


def _panel(n_days: int = 26):
    base = dt.date(2018, 1, 2)
    dates = [base + dt.timedelta(days=i) for i in range(n_days)]
    inputs = pl.DataFrame({
        "ticker": [TICKER] * n_days, "date": dates, "total_rv": [TOTAL_RV] * n_days,
    })
    # The last H dates have no complete forward window, so (as in real targets) target_var is null
    # there and those rows drop out of common support on both the hold and managed paths.
    tvar = [TARGET_VAR] * (n_days - H) + [None] * H
    targets = pl.DataFrame({
        "ticker": [TICKER] * n_days, "date": dates, "horizon": [H] * n_days,
        "group": [cfg.GROUP[TICKER]] * n_days,
        "target_var": tvar, "iv2": [IV2] * n_days,
        "iv_pctile_bucket": [3] * n_days,        # not cheap -> not "reduce"
        "post_shock": [False] * n_days,
    })
    q = {c: [RV_HAT] * n_days for c in ["q05", "q10", "q25", "q50", "q75", "q90", "q95"]}
    preds = pl.DataFrame({
        "ticker": [TICKER] * n_days, "date": dates, "horizon": [H] * n_days,
        "rv_hat": [RV_HAT] * n_days, "sigma": [1e-7] * n_days, **q,
        "fold_id": [0] * n_days, "model": ["SYNTH"] * n_days,
    })
    return preds, targets, inputs


def test_hold_to_expiry_books_the_terminal_variance_payoff():
    preds, targets, inputs = _panel()
    led = backtest.run_cell(preds, targets, inputs, StrategyConfig(name="baseline"), "SYNTH")
    assert led.height > 0
    expect_gross = led["size"] * cfg.SIGN_SHORT * (led["iv2"] - led["target_var"])
    assert (led["gross_pnl"] - expect_gross).abs().max() < 1e-15
    assert (led["pnl"] - (led["gross_pnl"] - led["cost"])).abs().max() < 1e-15
    assert led["gross_pnl"].min() > 0  # rich premium, low realized -> short vol profits


def test_managed_no_exit_equals_hold_to_expiry(monkeypatch):
    # Disable profit-take / stop so the only path is "held to k=H"; gate is "trade" throughout
    # (no post_shock, tiny dispersion, rich vrp), so risk-off never fires either.
    monkeypatch.setattr(cfg, "TAKE_FRAC", 1e9)
    monkeypatch.setattr(cfg, "STOP_MULT", 1e9)
    preds, targets, inputs = _panel()

    hold = backtest.run_cell(preds, targets, inputs, StrategyConfig(name="baseline"), "SYNTH")
    managed = backtest.run_cell(
        preds, targets, inputs, StrategyConfig(name="A9_managed", manage=True), "SYNTH"
    )

    assert managed.height == hold.height
    assert (managed["exit_reason"] == "expiry").all()
    j = hold.select("entry_date", hold_pnl="pnl").join(
        managed.select("entry_date", mgd_pnl="pnl"), on="entry_date", how="inner"
    )
    assert j.height == hold.height
    assert (j["hold_pnl"] - j["mgd_pnl"]).abs().max() < 1e-12
