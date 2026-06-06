"""Framework-level correctness pins (no ORATS load needed for most).

  * registries are populated and discoverable by name;
  * structures emit well-formed, ordered legs;
  * the marking P&L identity holds: a HELD short put's terminal P&L == credit − intrinsic;
  * fills cross the spread in the right direction (short sells low / buys back high).

The end-to-end ORATS path (locate_expiry -> mark_path) is exercised by `test_smoke.py`, which is
skipped automatically when the raw lake is absent.
"""

from __future__ import annotations

from stage2_trade_eval import config as cfg
from stage2_trade_eval import marks
from stage2_trade_eval.contracts import (
    HEDGES, MANAGEMENT, STRUCTURES, EntryContext, ExpiryChain, get_structure,
)
# populate registries
from stage2_trade_eval import structures, management, hedge  # noqa: F401

import datetime as dt
import polars as pl


def _chain(spot=100.0):
    # symmetric toy surface: deltas straddle 0.5 at ATM; bid/ask 1-wide.
    rows = []
    for strike in range(80, 121):
        call_delta = max(0.01, min(0.99, 0.5 - (strike - spot) * 0.02))
        rows.append({
            "strike": float(strike), "call_delta": call_delta, "put_delta": call_delta - 1.0,
            "cbid": 2.0, "cask": 2.2, "pbid": 2.0, "pask": 2.2, "cmid": 2.1, "pmid": 2.1,
            "vega": 0.1, "gamma": 0.01, "ctheta": -0.05, "ptheta": -0.05,
            "oi_c": 1000, "oi_p": 1000, "vol_c": 100, "vol_p": 100, "spot": spot,
        })
    return ExpiryChain(trade_date=dt.date(2020, 1, 2), expiry=dt.date(2020, 2, 1), spot=spot,
                       df=pl.DataFrame(rows).sort("strike"))


def test_registries_populated():
    assert {"short_strangle", "short_straddle", "iron_condor", "iron_fly",
            "put_credit_spread"} <= set(STRUCTURES)
    assert {"hold", "forecast_regate", "mechanical_terminal", "iv_regate"} <= set(MANAGEMENT)
    assert {"none", "terminal_band", "full_band"} <= set(HEDGES)


def test_structures_well_formed():
    chain, ctx = _chain(), _ctx()
    ic = get_structure("iron_condor").legs(chain, ctx)
    assert len(ic) == 4
    ks = [lg.strike for lg in ic]
    assert ks == sorted(ks)                       # long put < short put < short call < long call
    assert sum(lg.qty for lg in ic) == 0          # balanced
    assert all(lg.qty != 0 for lg in ic)
    sg = get_structure("short_strangle").legs(chain, ctx)
    assert len(sg) == 2 and all(lg.qty == -1 for lg in sg)


def test_credit_and_pnl_identity():
    chain, ctx = _chain(), _ctx()
    legs = get_structure("short_strangle").legs(chain, ctx)
    opened = marks.open_trade(chain, legs, ctx)
    # short legs sell @ bid (2.0 each) -> credit ~= 4.0 (two legs), minus nothing
    assert opened["credit"] > 0
    # held-to-expiry, both expire worthless if spot stays inside the strikes:
    # realized leg value = Σ qty*(intrinsic - entry_fill); intrinsic=0 -> value = -Σ qty*fill = credit
    val, comm = marks.close_value_synthetic(opened, spot_at_expiry=ctx.spot)
    assert abs(val - opened["credit"]) < 1e-9


def test_fill_direction():
    # opening a short sells at the (lower) bid; closing buys back at the (higher) ask.
    assert marks._fill(2.0, 2.2, opening=True, qty=-1) == 2.0
    assert marks._fill(2.0, 2.2, opening=False, qty=-1) == 2.2
    # opening a long buys at ask; closing sells at bid.
    assert marks._fill(2.0, 2.2, opening=True, qty=+1) == 2.2
    assert marks._fill(2.0, 2.2, opening=False, qty=+1) == 2.0


def _ctx():
    return EntryContext(
        ticker="SPY", group="g", entry_date=dt.date(2020, 1, 2), expiry=dt.date(2020, 2, 1),
        horizon=22, spot=100.0,
        signal={"vrp_score": 1e-3, "sigma": 1e-3, "iv2": 2e-3, "gate": "trade",
                "size": 1.0, "dispersion": 0.5, "target_var": 1e-3, "fold_id": 0},
    )
