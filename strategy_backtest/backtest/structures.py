"""The put-credit-spread structure (the only structure the v2 book trades, design §6).

A structure ONLY picks strikes (by |delta| off the entry chain) and returns the legs for one unit;
fills, settlement, greeks and sizing are the engine's job.
"""

from __future__ import annotations

from strategy_backtest.backtest import config as cfg
from strategy_backtest.backtest.contracts import EntryContext, ExpiryChain, Leg


def put_credit_spread_legs(chain: ExpiryChain, ctx: EntryContext) -> list[Leg]:
    """Sell ~SHORT_DELTA (0.25) put, buy ~WING_DELTA (0.10) put. Defined-risk, hard left-tail floor.

    Returns [] (skip the trade) if acceptable strikes can't be located or aren't ordered
    wing < short (a degenerate/illiquid surface).
    """
    kps = chain.strike_by_delta("P", cfg.SHORT_DELTA)
    kpl = chain.strike_by_delta("P", cfg.WING_DELTA)
    if kps is None or kpl is None or kpl >= kps:
        return []
    return [Leg("P", kpl, +1), Leg("P", kps, -1)]
