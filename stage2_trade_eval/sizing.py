"""Position sizing — fractional Kelly on the VRP edge (plan §C.4 / §A.5).

Stage-1's inverse-risk size is `vrp_rel / (K·dispersion²)` — algebraically `edge/variance`, i.e.
**Kelly with fraction 1/K**. So adopting fractional Kelly is a *recalibration* of the validated
sizer, not a new one: we reuse the entry `size` field `trade_eval.select_entries` already produced
(gate-applied, inverse-risk) and rescale it by the structure-family Kelly fraction, then clamp.

Kelly is fragile to edge mis-estimation, so: fraction capped well below 1, a hard size cap, and the
gate has already zeroed negative-edge names *before* we ever size them.
"""

from __future__ import annotations

from stage2_trade_eval import config as cfg


def kelly_units(entry_size: float, structure: str) -> float:
    """Sized units for one trade.

    `entry_size` is the `trade_eval` inverse-risk size (already ∝ vrp/σ², gate-applied, ≥0). We
    treat it as the full-Kelly proposal and trade a fraction `c` of it, capped at SIZE_CAP.
    """
    if entry_size is None or entry_size <= 0:
        return 0.0
    c = cfg.kelly_c_for(structure)
    return float(min(c * entry_size, cfg.SIZE_CAP))


def units_to_contracts(units: float, credit: float, margin_per_unit: float) -> float:
    """Optionally convert continuous units to integer contracts off NAV/margin (plan §C.4).

    When `ROUND_TO_CONTRACTS` is off we keep continuous units (clean signal attribution, matches
    Stage-1); when on we cap by the per-group margin budget and floor to whole contracts.
    """
    if not cfg.ROUND_TO_CONTRACTS:
        return units
    if margin_per_unit <= 0:
        return units
    budget = cfg.NAV * cfg.GROUP_MARGIN_CAP
    max_by_margin = budget / (margin_per_unit * cfg.CONTRACT_MULTIPLIER)
    return float(max(0, int(min(units, max_by_margin))))
