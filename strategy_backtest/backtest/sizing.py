"""Position sizing — inverse-risk fractional Kelly -> dollar risk -> whole contracts (design §7).

The sizing chain, per candidate trade i (multiplier m = 100, width W, net credit C):
    u          = clip(c_K * vrp_rel / disp^2, 0, U_max)        # signals.build_signals
    R          = u * b * NAV                                    # target dollar risk
    maxloss_c  = (W - C) * m                                    # max loss per contract ($)
    n_raw      = R / maxloss_c                                  # raw (fractional) contracts
    group cap  : scale a group's trades pro-rata if sum(n_i * maxloss_c,i) > GROUP_MARGIN_CAP * NAV
    contracts  = floor(n_raw)                                   # whole contracts; skip if 0

`ROUND_TO_CONTRACTS=False` keeps fractional contracts (NAV-independent attribution run).
"""

from __future__ import annotations

from strategy_backtest.backtest import config as cfg


def maxloss_per_contract(width: float, credit: float) -> float:
    """Defined-risk max loss per contract in dollars = (W - C) * multiplier."""
    return (width - credit) * cfg.CONTRACT_MULTIPLIER


def raw_contracts(u: float, maxloss_c: float) -> float:
    """Fractional contracts before the group cap / rounding: R / maxloss_c = u*b*NAV / maxloss_c."""
    if u <= 0 or maxloss_c <= 0:
        return 0.0
    return (u * cfg.RISK_BUDGET * cfg.NAV) / maxloss_c


def apply_group_cap(candidates: list[dict]) -> None:
    """Scale a correlation group's trades pro-rata so summed margin <= GROUP_MARGIN_CAP * NAV.

    Mutates each candidate dict in place, setting `n_capped`. `candidates` is the set of trades that
    will be open simultaneously within ONE correlation group (engine groups by (group, roll-date)).
    Each carries `n_raw` and `maxloss_c`.
    """
    budget = cfg.GROUP_MARGIN_CAP * cfg.NAV
    used = sum(c["n_raw"] * c["maxloss_c"] for c in candidates)
    scale = min(1.0, budget / used) if used > 0 else 1.0
    for c in candidates:
        c["n_capped"] = c["n_raw"] * scale


def finalize_contracts(n_capped: float) -> float:
    """Whole contracts off the capped raw count (or fractional if rounding is disabled).

    CONTRACT_ROUNDING="nearest" (round-half-up) is the default — plain floor systematically
    under-deploys expensive names (n_raw≈1.4 -> 1) and distorts the per-name risk distribution
    (suggestion D). "floor" preserves the pre-fix behaviour. Skip-if-zero is handled by the caller.
    """
    if not cfg.ROUND_TO_CONTRACTS:
        return float(n_capped)
    if n_capped <= 0:
        return 0.0
    if cfg.CONTRACT_ROUNDING == "floor":
        return float(int(n_capped))
    return float(int(n_capped + 0.5))        # round-half-up
