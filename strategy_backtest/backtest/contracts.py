"""Atomic position types — Leg, EntryContext, ExpiryChain (ported, trimmed to what the v2 book uses).

The headline book holds to expiry, so no daily MarkRow / management / hedge contracts are needed:
a trade is fully described by its legs, entry fills, and intrinsic settlement at expiry.
"""

from __future__ import annotations

from dataclasses import dataclass

import polars as pl


@dataclass(frozen=True)
class Leg:
    """One option leg of a structure, per ONE structure unit.

    qty < 0 = short (sell), qty > 0 = long (buy). `right` is 'C' or 'P'. `strike` is absolute.
    The engine multiplies qty by the sized number of contracts and the contract multiplier.
    """

    right: str
    strike: float
    qty: int

    def __post_init__(self) -> None:
        if self.right not in ("C", "P"):
            raise ValueError(f"right must be 'C'/'P', got {self.right!r}")


@dataclass(frozen=True)
class EntryContext:
    """Entry-dated, point-in-time facts a structure may use. No field is ever from after entry."""

    ticker: str
    group: str
    entry_date: object       # datetime.date
    expiry: object           # datetime.date
    horizon: int
    spot: float
    signal: dict             # vrp_score, vrp_rel, sigma, iv2, size_units, dispersion, fold_id


@dataclass(frozen=True)
class ExpiryChain:
    """One (trade_date, expiry) slice of the ORATS surface, sorted by strike.

    Guaranteed columns: strike, call_delta, put_delta, cbid, cask, pbid, pask, cmid, pmid,
    vega, gamma, oi_c, oi_p, vol_c, vol_p, spot. `strike_by_delta` picks a strike by |delta|.
    """

    trade_date: object
    expiry: object
    spot: float
    df: pl.DataFrame

    def strike_by_delta(self, right: str, target_abs_delta: float) -> float | None:
        if self.df.is_empty():
            return None
        col = "call_delta" if right == "C" else "put_delta"
        d = self.df.with_columns(_err=(pl.col(col).abs() - target_abs_delta).abs()).sort("_err")
        return float(d["strike"][0])
