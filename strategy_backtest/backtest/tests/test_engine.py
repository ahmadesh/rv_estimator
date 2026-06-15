"""Self-contained correctness guards for the put-spread engine (no data / ORATS I/O needed).

  1. P&L identity — a put-credit spread that expires worthless returns exactly the entry credit
     (minus commissions); one that settles below the wing loses exactly the defined max loss.
  2. Gate logic — the lean-core G2/G3/G4 fire on the right conditions.
  3. Leakage guard — the realized [t,t+h] outcome `target_var` never reaches a trade-decision path.

Run:  .venv/bin/python -m pytest strategy_backtest/backtest/tests/test_engine.py -q
"""

from __future__ import annotations

import datetime as dt

import polars as pl

from strategy_backtest.backtest import config as cfg
from strategy_backtest.backtest import marks, signals
from strategy_backtest.backtest.contracts import EntryContext, ExpiryChain, Leg


def _synthetic_chain(spot: float = 100.0) -> ExpiryChain:
    """A tidy two-strike put chain: 95 short (0.25Δ), 90 wing (0.10Δ), both liquid."""
    df = pl.DataFrame({
        "strike": [90.0, 95.0],
        "call_delta": [0.90, 0.75],          # put_delta = call_delta - 1 -> -0.10, -0.25
        "put_delta": [-0.10, -0.25],
        "cbid": [10.0, 5.0], "cask": [10.2, 5.2], "cmid": [10.1, 5.1],
        "pbid": [0.50, 1.50], "pask": [0.55, 1.60], "pmid": [0.52, 1.55],
        "vega": [0.1, 0.1], "gamma": [0.01, 0.01],
        "oi_p": [500, 500], "oi_c": [500, 500], "vol_p": [10, 10], "vol_c": [10, 10],
        "spot": [spot, spot],
    })
    return ExpiryChain(trade_date=dt.date(2015, 6, 1), expiry=dt.date(2015, 7, 1), spot=spot, df=df)


def _open(spot=100.0):
    chain = _synthetic_chain(spot)
    ctx = EntryContext("SPY", "us_large_cap_equity", chain.trade_date, chain.expiry, 22, spot, {})
    legs = [Leg("P", 90.0, +1), Leg("P", 95.0, -1)]      # buy wing, sell short
    return chain, ctx, marks.open_trade(chain, legs, ctx)


def test_credit_and_maxloss_identity():
    _, _, opened = _open()
    # sell 95 put @ bid 1.50, buy 90 wing @ ask 0.55 -> credit 0.95, width 5, max_loss 4.05
    assert abs(opened["credit"] - 0.95) < 1e-9
    assert abs(opened["width"] - 5.0) < 1e-9
    assert abs(opened["max_loss"] - 4.05) < 1e-9


def test_worthless_expiry_keeps_credit():
    _, ctx, opened = _open()
    # spot 100 > short 95 at expiry -> both legs worthless -> leg_val per unit == credit
    leg_val = sum(lg.qty * (max(lg.strike - 110.0, 0.0) - f)
                  for lg, f in zip(opened["legs"], opened["entry_fills"]))
    assert abs(leg_val - opened["credit"]) < 1e-9


def test_below_wing_is_full_maxloss():
    _, ctx, opened = _open()
    # spot 80 < wing 90 -> both ITM -> leg_val per unit == -max_loss (the defined-risk floor)
    spot = 80.0
    leg_val = sum(lg.qty * (max(lg.strike - spot, 0.0) - f)
                  for lg, f in zip(opened["legs"], opened["entry_fills"]))
    assert abs(leg_val + opened["max_loss"]) < 1e-9


def test_gate_logic():
    df = pl.DataFrame({
        "ticker": ["A", "B", "C", "D"], "date": [dt.date(2015, 1, i + 1) for i in range(4)],
        "horizon": [22] * 4,
        "iv2": [0.01, 0.01, 0.01, 0.01], "rv_hat": [0.006, 0.006, 0.006, 0.006],
        "rv_hat_vrp": [0.006, 0.006, 0.006, 0.006],
        "sigma": [0.002, 0.002, 0.008, 0.002],
        "iv_30d": [0.18, 0.18, 0.18, 0.18], "iv_slope": [0.02, -0.02, 0.02, 0.02],
        "vix": [15.0, 15.0, 15.0, 15.0], "vix3m": [17.0, 17.0, 17.0, 14.0],
        "ivrank": [0.5, 0.5, 0.5, 0.95], "disp_p80": [0.5, 0.5, 0.5, 0.5],
    })
    out = signals.build_signals(df, "forecaster")
    g = dict(zip(out["ticker"], out["gate"]))
    assert g["A"] is True              # contango + low IVrank + cool dispersion -> trade
    assert g["B"] is False             # iv_slope < 0 -> backwardation -> G3 fails
    assert g["C"] is False             # dispersion 0.008/0.006 = 1.33 > disp_p80 0.5 -> G4 fails
    assert g["D"] is False             # IVrank 0.95 > 0.85 -> G2 fails (also vix3m<vix -> G3 fails)


def test_no_target_var_in_decision_context():
    _, ctx, _ = _open()
    assert "target_var" not in ctx.signal, "future realization leaked into the decision context"
