"""Concrete option structures (plan §C.2) — each maps a gated signal to legs.

Defined-risk workhorse: `iron_condor`, `iron_fly`, `put_credit_spread`.
Naked higher-octane:    `short_strangle`, `short_straddle`.

A structure ONLY picks strikes (by |delta| off the entry chain) and returns `Leg`s for one unit;
fills, marking, greeks, settlement and sizing are the engine's job. Add a new idea by writing one
`legs()` method and decorating with `@register_structure` — nothing else changes.
"""

from __future__ import annotations

from stage2_trade_eval import config as cfg
from stage2_trade_eval.contracts import (
    EntryContext, ExpiryChain, Leg, Structure, register_structure,
)


def is_defined_risk(name: str) -> bool:
    """Whether a registered structure caps its loss (drives Kelly fraction & margin)."""
    from stage2_trade_eval.contracts import STRUCTURES
    cls = STRUCTURES.get(name)
    return bool(cls.defined_risk) if cls is not None else True


# --------------------------------------------------------------------------- naked (undefined tail)
@register_structure
class ShortStrangle(Structure):
    """Sell a ~SHORT_DELTA put and call. Closest to the pure variance short; naked tail."""

    name = "short_strangle"
    defined_risk = False

    def legs(self, chain: ExpiryChain, ctx: EntryContext) -> list[Leg]:
        kp = chain.strike_by_delta("P", cfg.SHORT_DELTA)
        kc = chain.strike_by_delta("C", cfg.SHORT_DELTA)
        if kp is None or kc is None or kp >= kc:
            return []
        return [Leg("P", kp, -1), Leg("C", kc, -1)]


@register_structure
class ShortStraddle(Structure):
    """Sell the ATM put and call (max premium, max gamma). Naked tail."""

    name = "short_straddle"
    defined_risk = False

    def legs(self, chain: ExpiryChain, ctx: EntryContext) -> list[Leg]:
        k = chain.strike_by_delta("C", cfg.STRADDLE_DELTA)
        if k is None:
            return []
        return [Leg("P", k, -1), Leg("C", k, -1)]


# --------------------------------------------------------------------------- defined-risk (capped)
@register_structure
class IronCondor(Structure):
    """Short ~SHORT_DELTA strangle + long ~WING_DELTA wings. Caps the exact tail the gate avoids."""

    name = "iron_condor"
    defined_risk = True

    def legs(self, chain: ExpiryChain, ctx: EntryContext) -> list[Leg]:
        kps = chain.strike_by_delta("P", cfg.SHORT_DELTA)
        kpl = chain.strike_by_delta("P", cfg.WING_DELTA)
        kcs = chain.strike_by_delta("C", cfg.SHORT_DELTA)
        kcl = chain.strike_by_delta("C", cfg.WING_DELTA)
        if None in (kps, kpl, kcs, kcl) or not (kpl < kps < kcs < kcl):
            return []
        return [Leg("P", kpl, +1), Leg("P", kps, -1), Leg("C", kcs, -1), Leg("C", kcl, +1)]


@register_structure
class IronFly(Structure):
    """Short ATM straddle body + long ~WING_DELTA wings. More premium than the condor, still capped."""

    name = "iron_fly"
    defined_risk = True

    def legs(self, chain: ExpiryChain, ctx: EntryContext) -> list[Leg]:
        kb = chain.strike_by_delta("C", cfg.STRADDLE_DELTA)
        kpl = chain.strike_by_delta("P", cfg.WING_DELTA)
        kcl = chain.strike_by_delta("C", cfg.WING_DELTA)
        if None in (kb, kpl, kcl) or not (kpl < kb < kcl):
            return []
        return [Leg("P", kpl, +1), Leg("P", kb, -1), Leg("C", kb, -1), Leg("C", kcl, +1)]


@register_structure
class PutCreditSpread(Structure):
    """Sell ~SHORT_DELTA put, buy ~WING_DELTA put. Directional downside-vol sale with a hard floor."""

    name = "put_credit_spread"
    defined_risk = True

    def legs(self, chain: ExpiryChain, ctx: EntryContext) -> list[Leg]:
        kps = chain.strike_by_delta("P", cfg.SHORT_DELTA)
        kpl = chain.strike_by_delta("P", cfg.WING_DELTA)
        if kps is None or kpl is None or kpl >= kps:
            return []
        return [Leg("P", kpl, +1), Leg("P", kps, -1)]
