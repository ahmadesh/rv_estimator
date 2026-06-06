"""Fills, marking, settlement and frictions — the generic per-trade P&L math (plan §C.7).

Cashflow accounting (sign-unambiguous):
    realized P&L (per unit) = Σ_i qty_i · (close_fill_i − entry_fill_i) · multiplier − commissions

  * entry fill: short leg (qty<0) sells @ bid, long leg (qty>0) buys @ ask   (cross the spread)
  * close fill: short buys back @ ask, long sells @ bid                        (cross again)
  * expiry:     close_fill = intrinsic (no spread)
  * intermediate marks use MID, so management/hedge decisions aren't double-charged the spread.

`max credit` (per unit) = Σ over short legs of entry_fill − Σ over long legs of entry_fill, i.e.
the net premium received; it is the denominator for the take-profit rule and the naked stop.
"""

from __future__ import annotations

import datetime as dt

from stage2_trade_eval import chains
from stage2_trade_eval import config as cfg
from stage2_trade_eval.contracts import EntryContext, ExpiryChain, Leg


class Rejected(Exception):
    """A leg/structure failed a liquidity or credit filter at entry (skip the trade)."""


def _liquid(q: dict) -> bool:
    if q is None:
        return False
    bid, ask, mid = q["bid"], q["ask"], q["mid"]
    if not (bid >= 0 and ask > 0 and mid > 0):
        return False
    if q.get("oi", 0) is not None and q["oi"] < cfg.MIN_OI:
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
    # opening short -> sell @ bid; opening long -> buy @ ask; closing flips.
    buy = (not short) if opening else short
    px = price_ask if buy else price_bid
    tick = cfg.SLIPPAGE_TICKS * 0.01
    return px + (tick if buy else -tick)


def open_trade(chain: ExpiryChain, legs: list[Leg], ctx: EntryContext) -> dict:
    """Price the entry; raise `Rejected` on any failed leg or the credit/width filters.

    Returns: per-leg entry fills + the structure's max credit, max loss (width − credit for
    defined-risk), and entry commission — all per ONE unit.
    """
    fills, quotes, width = [], [], 0.0
    short_strikes, long_strikes = [], []
    for lg in legs:
        q = chains.leg_quote_from_chain(chain, lg.strike, lg.right)
        if not _liquid(q):
            raise Rejected(f"illiquid leg {lg.right}{lg.strike}")
        f = _fill(q["bid"], q["ask"], opening=True, qty=lg.qty)
        fills.append(f)
        quotes.append(q)
        (short_strikes if lg.qty < 0 else long_strikes).append(lg.strike)

    # net credit (per unit) = premium received on shorts − premium paid on longs
    credit = -sum(lg.qty * f for lg, f in zip(legs, fills))
    if credit < cfg.MIN_NET_CREDIT:
        raise Rejected(f"credit {credit:.3f} < min")

    # defined-risk width = distance from a short strike to its protective wing (max over wings)
    if long_strikes and short_strikes:
        width = max(
            min(abs(ls - s) for ls in long_strikes) for s in short_strikes
        )
        if width > 0 and credit / width < cfg.MIN_CREDIT_TO_WIDTH:
            raise Rejected(f"credit/width {credit/width:.3f} < min")
    max_loss = (width - credit) if width > 0 else float("inf")
    commission = cfg.COMMISSION_PER_CONTRACT * len(legs)

    return {
        "legs": legs, "entry_fills": fills, "credit": credit,
        "width": width, "max_loss": max_loss, "entry_commission": commission,
        "entry_delta": sum(lg.qty * q["delta"] for lg, q in zip(legs, quotes)),
    }


def _intrinsic(right: str, strike: float, spot: float) -> float:
    return max(spot - strike, 0.0) if right == "C" else max(strike - spot, 0.0)


def mark_path(ticker: str, ctx: EntryContext, opened: dict, path_dates: list[dt.date],
              accrued_rv: list[float], gates: list[str | None], iv2_path: list[float]):
    """Build the per-day mark series for a live trade (mid marks, per unit).

    Returns list of dicts (one per day k=1..H): date, dte, spot, mtm, pos_delta, accrued_rv,
    iv2, gate, credit. The final day is the expiry-settlement mark (intrinsic). Days where a leg
    cannot be relocated fall back to the previous day's mark (halt/again-listed gap).
    """
    legs, fills, credit = opened["legs"], opened["entry_fills"], opened["credit"]
    expiry = ctx.expiry
    out, prev = [], None
    for k, d in enumerate(path_dates, start=1):
        settle = d >= expiry
        leg_vals, leg_deltas, spot = [], [], ctx.spot
        ok = True
        for lg, f in zip(legs, fills):
            if settle:
                # settle at intrinsic on the prevailing spot
                q = chains.relocate(ticker, min(d, expiry), expiry, lg.strike, lg.right)
                spot = q["spot"] if q else (prev["spot"] if prev else ctx.spot)
                val = _intrinsic(lg.right, lg.strike, spot)
                leg_vals.append(lg.qty * (val - f))
                leg_deltas.append(lg.qty * (1.0 if (lg.right == "C" and spot > lg.strike) else
                                            (-1.0 if (lg.right == "P" and spot < lg.strike) else 0.0)))
            else:
                q = chains.relocate(ticker, d, expiry, lg.strike, lg.right)
                if q is None or not (q["mid"] > 0):
                    ok = False
                    break
                spot = q["spot"]
                leg_vals.append(lg.qty * (q["mid"] - f))
                leg_deltas.append(lg.qty * q["delta"])
        if not ok:
            if prev is None:
                continue
            out.append({**prev, "k": k, "date": d})
            prev = out[-1]
            continue
        dte = max((expiry - d).days, 0)
        row = {
            "k": k, "dte": dte, "date": d, "spot": spot,
            "mtm": sum(leg_vals), "pos_delta": sum(leg_deltas),
            "accrued_rv": accrued_rv[k - 1] if k - 1 < len(accrued_rv) else float("nan"),
            "iv2": iv2_path[k - 1] if k - 1 < len(iv2_path) else ctx.signal.get("iv2", float("nan")),
            "gate": gates[k - 1] if k - 1 < len(gates) else None,
            "credit": credit,
        }
        out.append(row)
        prev = row
        if settle:
            break
    return out


def close_value_synthetic(opened: dict, spot_at_expiry: float) -> tuple[float, float]:
    """Per-unit realized leg value at expiry for a GIVEN spot (no ORATS lookup; used by tests).

    value = Σ qty_i·(intrinsic_i − entry_fill_i); for a short book that expires worthless this
    equals the entry credit — the P&L identity `tests/` pins down.
    """
    legs, fills = opened["legs"], opened["entry_fills"]
    val = sum(lg.qty * (_intrinsic(lg.right, lg.strike, spot_at_expiry) - f)
              for lg, f in zip(legs, fills))
    return val, 0.0


def close_value(ticker: str, ctx: EntryContext, opened: dict, exit_date: dt.date, exit_k: int):
    """Per-unit realized leg value + close commission for an EARLY exit (cross the spread)."""
    legs, fills = opened["legs"], opened["entry_fills"]
    expiry = ctx.expiry
    val = 0.0
    if exit_date >= expiry:
        # settled at intrinsic
        q0 = chains.relocate(ticker, min(exit_date, expiry), expiry, legs[0].strike, legs[0].right)
        spot = q0["spot"] if q0 else ctx.spot
        for lg, f in zip(legs, fills):
            val += lg.qty * (_intrinsic(lg.right, lg.strike, spot) - f)
        return val, 0.0  # no close commission on expiry settlement
    for lg, f in zip(legs, fills):
        q = chains.relocate(ticker, exit_date, expiry, lg.strike, lg.right)
        if q is None:
            cf = 0.0  # cannot relocate -> assume marked-out at last mid via mtm fallback upstream
        else:
            cf = _fill(q["bid"], q["ask"], opening=False, qty=lg.qty)
        val += lg.qty * (cf - f)
    commission = cfg.COMMISSION_PER_CONTRACT * len(legs)
    return val, commission
