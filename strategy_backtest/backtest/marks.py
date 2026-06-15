"""Fills, settlement and frictions — the per-trade P&L math for a hold-to-expiry book (§8.4).

Cashflow accounting (sign-unambiguous), per ONE unit:
    realized P&L = Sigma_i qty_i * (intrinsic_at_expiry_i - entry_fill_i) * multiplier - commissions

  * entry fill: short leg (qty<0) sells @ bid, long leg (qty>0) buys @ ask   (cross the spread)
  * expiry:     each leg settles at intrinsic on the expiry-day spot          (no spread crossed)

`max credit` (per unit) = net premium received = -Sigma qty_i * entry_fill_i; it is the take-profit
denominator (unused here — hold only) and, with the strike width, gives the defined-risk max loss
(width - credit) that drives sizing and the margin cap.
"""

from __future__ import annotations

import datetime as dt

from strategy_backtest.backtest import chains
from strategy_backtest.backtest import config as cfg
from strategy_backtest.backtest.contracts import EntryContext, ExpiryChain, Leg


class Rejected(Exception):
    """A leg/structure failed a liquidity or credit filter at entry (skip the trade) — gate G7."""


def _liquid(q: dict | None, min_oi: int) -> bool:
    if q is None:
        return False
    bid, ask, mid = q["bid"], q["ask"], q["mid"]
    if not (bid >= 0 and ask > 0 and mid > 0):
        return False
    if q.get("oi", 0) is not None and q["oi"] < min_oi:
        return False
    if cfg.MIN_VOLUME and (q.get("vol", 0) or 0) < cfg.MIN_VOLUME:
        return False
    if (ask - bid) / mid > cfg.MAX_REL_SPREAD:
        return False
    return True


def _fill(price_bid: float, price_ask: float, opening: bool, qty: int) -> float:
    """Per-share fill price, crossing the spread (+ optional slippage), or MID for diagnostics."""
    if cfg.FILL == "mid":
        return 0.5 * (price_bid + price_ask)
    short = qty < 0
    buy = (not short) if opening else short      # opening short -> sell @ bid; long -> buy @ ask
    px = price_ask if buy else price_bid
    tick = cfg.SLIPPAGE_TICKS * 0.01
    return px + (tick if buy else -tick)


def open_trade(chain: ExpiryChain, legs: list[Leg], ctx: EntryContext) -> dict:
    """Price the entry; raise `Rejected` on any failed liquidity / credit-width filter (G7).

    Returns per-leg entry fills + max credit, strike width, defined-risk max loss (width - credit)
    and the entry commission — all per ONE unit.
    """
    fills, quotes = [], []
    short_strikes, long_strikes = [], []
    for lg in legs:
        q = chains.leg_quote_from_chain(chain, lg.strike, lg.right)
        min_oi = cfg.MIN_OI_SHORT if lg.qty < 0 else cfg.MIN_OI_WING   # short ≥50, wing ≥10
        if not _liquid(q, min_oi):
            raise Rejected(f"illiquid leg {lg.right}{lg.strike}")
        fills.append(_fill(q["bid"], q["ask"], opening=True, qty=lg.qty))
        quotes.append(q)
        (short_strikes if lg.qty < 0 else long_strikes).append(lg.strike)

    credit = -sum(lg.qty * f for lg, f in zip(legs, fills))
    if credit < cfg.MIN_NET_CREDIT:
        raise Rejected(f"credit {credit:.3f} < min")

    width = 0.0
    if long_strikes and short_strikes:
        width = max(min(abs(ls - s) for ls in long_strikes) for s in short_strikes)
        if width > 0 and credit / width < cfg.MIN_CREDIT_TO_WIDTH:
            raise Rejected(f"credit/width {credit / width:.3f} < min")
    max_loss = (width - credit) if width > 0 else float("inf")
    commission = cfg.COMMISSION_PER_CONTRACT * len(legs)

    return {
        "legs": legs, "entry_fills": fills, "credit": credit,
        "width": width, "max_loss": max_loss, "entry_commission": commission,
        "entry_delta": sum(lg.qty * q["delta"] for lg, q in zip(legs, quotes)),
        "short_strike": short_strikes[0] if short_strikes else float("nan"),
        "wing_strike": long_strikes[0] if long_strikes else float("nan"),
    }


def mark_close(chain: ExpiryChain, legs: list[Leg], entry_fills: list[float]) -> dict | None:
    """Mark an open spread on a later day's chain — for the managed-exit daily path (§5).

    Returns, per ONE unit:
      * `markpnl_mid`    : P&L marked at the chain MID (smooth, gap-free) = Σ qty·(mid − entry_fill).
                           This is what the exit triggers compare against (X1 take, X5 stop) so a wide
                           bid/ask doesn't fire a trigger spuriously.
      * `leg_val_close`  : P&L if we actually CLOSE here, crossing the spread (buy back short @ ask,
                           sell wing @ bid, + slippage) = Σ qty·(close_fill − entry_fill). This is the
                           realised leg value the ledger books, mirroring `settle_at_expiry`'s `leg_val`.
      * `close_commission`: per-unit commission to close (one round per leg).
      * `spot`           : underlying on the mark day (for the breach flag / variance context).
    None if any leg can't be re-quoted on this chain (caller carries the last good mark forward).
    """
    quotes = []
    for lg in legs:
        q = chains.leg_quote_from_chain(chain, lg.strike, lg.right)
        if q is None or not (q["mid"] > 0 and q["ask"] > 0):
            return None
        quotes.append(q)
    markpnl_mid = sum(lg.qty * (q["mid"] - f) for lg, q, f in zip(legs, quotes, entry_fills))
    close_fills = [_fill(q["bid"], q["ask"], opening=False, qty=lg.qty)
                   for lg, q in zip(legs, quotes)]
    leg_val_close = sum(lg.qty * (cf - f) for lg, cf, f in zip(legs, close_fills, entry_fills))
    commission = cfg.COMMISSION_PER_CONTRACT * len(legs)
    return {"markpnl_mid": markpnl_mid, "leg_val_close": leg_val_close,
            "close_commission": commission, "spot": chain.spot}


def _intrinsic(right: str, strike: float, spot: float) -> float:
    return max(spot - strike, 0.0) if right == "C" else max(strike - spot, 0.0)


def settle_at_expiry(ticker: str, ctx: EntryContext, opened: dict) -> dict | None:
    """Per-unit realised leg value at expiry settlement (intrinsic on the expiry-day spot).

    Returns dict with per-unit leg P&L, the settlement spot, and whether the short strike was
    breached. None if the settlement spot can't be located at all.
    """
    spot = chains.settlement_spot(ticker, ctx.expiry)
    if spot is None:
        return None
    legs, fills = opened["legs"], opened["entry_fills"]
    leg_val = sum(lg.qty * (_intrinsic(lg.right, lg.strike, spot) - f)
                  for lg, f in zip(legs, fills))
    breached = spot < opened["short_strike"]
    return {"leg_val": leg_val, "settle_spot": spot, "breached": breached}
