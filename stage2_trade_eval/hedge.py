"""Delta-hedge modes (plan §C.6) — default light; an explicit ablation axis.

  none           — never hedge. Default for defined-risk (capped tail; hedging eats the credit).
  terminal_band  — hedge to flat only when |position delta| breaches DELTA_BAND, and only in the
                   terminal week (dte <= TERMINAL_DTE). Recommended for the naked strangle overlay.
  full_band      — band-hedge over the whole life (converts P&L toward pure vol/gamma-theta).

A hedge re-balances to the target share position; the engine books hedge P&L as
shares_held · (spot_{t} − spot_{t-1}) and a per-share commission proxy on rebalances. Add a mode
by implementing `hedge_shares(day, state, ctx) -> target_shares` and registering it.
"""

from __future__ import annotations

from stage2_trade_eval import config as cfg
from stage2_trade_eval.contracts import EntryContext, HedgeMode, HedgeState, MarkRow, register_hedge


@register_hedge
class NoHedge(HedgeMode):
    name = "none"

    def hedge_shares(self, day: MarkRow, state: HedgeState, ctx: EntryContext) -> float:
        return 0.0


class _BandHedge(HedgeMode):
    """Hedge to flat when |position delta| (in share-equivalents) breaches the band."""

    name = "_band"
    terminal_only = False

    def hedge_shares(self, day: MarkRow, state: HedgeState, ctx: EntryContext) -> float:
        if self.terminal_only and day.dte > cfg.TERMINAL_DTE:
            return state.shares  # leave the current hedge untouched outside the terminal week
        # position delta in shares = option pos_delta · multiplier; band scaled to a $NAV notional.
        pos_shares = day.pos_delta * cfg.CONTRACT_MULTIPLIER
        band_shares = cfg.DELTA_BAND * (cfg.NAV / max(day.spot, 1e-6)) / cfg.CONTRACT_MULTIPLIER
        if abs(pos_shares + state.shares) <= band_shares:
            return state.shares                       # inside band -> no rebalance
        return -pos_shares                            # hedge to flat


@register_hedge
class TerminalBand(_BandHedge):
    name = "terminal_band"
    terminal_only = True


@register_hedge
class FullBand(_BandHedge):
    name = "full_band"
    terminal_only = False
