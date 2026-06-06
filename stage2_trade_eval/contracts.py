"""The extension contracts + registries — the framework's plug points.

To try a new idea from the plan you implement ONE small class and register it; the engine
discovers it by name. Three contracts, three registries:

    @register_structure
    class MyStructure(Structure):
        name = "my_structure"
        defined_risk = True
        def legs(self, chain: ExpiryChain, ctx: EntryContext) -> list[Leg]: ...

    @register_management
    class MyArm(ManagementArm):
        name = "my_arm"
        def exit_on(self, path: pl.DataFrame, ctx: EntryContext) -> tuple[int, str] | None: ...

    @register_hedge
    class MyHedge(HedgeMode):
        name = "my_hedge"
        def hedge_shares(self, day: MarkRow, state: HedgeState, ctx: EntryContext) -> float: ...

`Leg` is the atomic unit every structure emits; the engine handles fills, marking, greeks,
settlement, frictions and sizing generically, so a structure only ever decides *which legs*.
This mirrors `rv_eval`'s `Model` ABC (fit/predict) — one interface, many drop-ins.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Callable

import polars as pl


# --------------------------------------------------------------------------- atomic position unit
@dataclass(frozen=True)
class Leg:
    """One option leg of a structure, per ONE structure unit.

    qty < 0 = short (sell), qty > 0 = long (buy). `right` is 'C' or 'P'. `strike` is absolute.
    The engine multiplies qty by the sized number of units and by the contract multiplier.
    """

    right: str            # 'C' | 'P'
    strike: float
    qty: int              # signed; -1 short one, +1 long one

    def __post_init__(self) -> None:
        if self.right not in ("C", "P"):
            raise ValueError(f"right must be 'C'/'P', got {self.right!r}")


# --------------------------------------------------------------------------- entry context handed to a structure
@dataclass(frozen=True)
class EntryContext:
    """Everything point-in-time a structure / arm / hedge may use at and after entry.

    `signal` carries the frozen-forecast decision fields already computed by `trade_eval`
    (vrp_score, sigma, iv2, gate, size, dispersion). `spot` is entry-day underlying. No row here
    is ever from after `entry_date` (leakage guard lives in the engine; this object only exposes
    entry-dated facts plus the chosen expiry).
    """

    ticker: str
    group: str
    entry_date: object            # datetime.date
    expiry: object                # datetime.date
    horizon: int
    spot: float
    signal: dict                  # vrp_score, sigma, iv2, gate, size, dispersion, target_var, fold_id


# --------------------------------------------------------------------------- a located expiry's chain slice
@dataclass(frozen=True)
class ExpiryChain:
    """One (trade_date, expiry) slice of the ORATS surface, sorted by strike.

    Columns guaranteed: strike, call_delta, put_delta, cbid, cask, pbid, pask, cmid, pmid,
    vega, gamma, ctheta, ptheta, oi_c, oi_p, vol_c, vol_p, spot. Helpers pick strikes by |delta|.
    """

    trade_date: object
    expiry: object
    spot: float
    df: pl.DataFrame

    def strike_by_delta(self, right: str, target_abs_delta: float) -> float | None:
        """Strike whose option |delta| is closest to `target_abs_delta` (right='C'|'P')."""
        if self.df.is_empty():
            return None
        col = "call_delta" if right == "C" else "put_delta"
        d = self.df.with_columns(_err=(pl.col(col).abs() - target_abs_delta).abs()).sort("_err")
        return float(d["strike"][0])


# --------------------------------------------------------------------------- a single daily mark row
@dataclass(frozen=True)
class MarkRow:
    """One day on a live trade's path (handed to managers/hedges)."""

    k: int                # trading days since entry (1..H)
    dte: int              # calendar days to expiry
    date: object
    spot: float
    mtm: float            # per-unit mark-to-market P&L (mid marks), pre-frictions, pre-hedge
    pos_delta: float      # per-unit signed position delta (option legs only)
    accrued_rv: float     # realized variance accrued entry->today (for the variance stop)
    iv2: float            # prevailing entry-tenor implied variance
    gate: str | None      # re-evaluated forecast gate that day (for the A9/H2 arm)
    credit: float         # max capturable credit per unit (entry)


@dataclass
class HedgeState:
    """Mutable per-trade hedge accumulator (shares held, realized hedge P&L)."""

    shares: float = 0.0
    pnl: float = 0.0
    last_spot: float | None = None


# --------------------------------------------------------------------------- the three contracts
class Structure(ABC):
    """Maps a gated signal -> option legs. `defined_risk` gates Kelly fraction & margin model."""

    name: str = "structure"
    defined_risk: bool = True

    @abstractmethod
    def legs(self, chain: ExpiryChain, ctx: EntryContext) -> list[Leg]:
        """Return the legs for ONE unit, or [] to skip (e.g. no acceptable strikes)."""


class ManagementArm(ABC):
    """Decides early exit. `exit_on` returns (k, reason) or None to hold to expiry."""

    name: str = "management"

    @abstractmethod
    def exit_on(self, path: pl.DataFrame, ctx: EntryContext) -> tuple[int, str] | None:
        """`path` is the per-day MarkRow frame for this trade (k ascending)."""


class HedgeMode(ABC):
    """Decides the hedge share target each day. `none` returns 0 always."""

    name: str = "hedge"

    @abstractmethod
    def hedge_shares(self, day: MarkRow, state: HedgeState, ctx: EntryContext) -> float:
        """Target hedge share position (signed) AFTER today; engine books the delta vs `state`."""


# --------------------------------------------------------------------------- registries
STRUCTURES: dict[str, type[Structure]] = {}
MANAGEMENT: dict[str, type[ManagementArm]] = {}
HEDGES: dict[str, type[HedgeMode]] = {}


def _register(reg: dict, cls):
    if cls.name in reg:
        raise ValueError(f"duplicate registration {cls.name!r} in {reg}")
    reg[cls.name] = cls
    return cls


def register_structure(cls: type[Structure]) -> type[Structure]:
    return _register(STRUCTURES, cls)


def register_management(cls: type[ManagementArm]) -> type[ManagementArm]:
    return _register(MANAGEMENT, cls)


def register_hedge(cls: type[HedgeMode]) -> type[HedgeMode]:
    return _register(HEDGES, cls)


def get_structure(name: str) -> Structure:
    return STRUCTURES[name]()


def get_management(name: str) -> ManagementArm:
    return MANAGEMENT[name]()


def get_hedge(name: str) -> HedgeMode:
    return HEDGES[name]()
