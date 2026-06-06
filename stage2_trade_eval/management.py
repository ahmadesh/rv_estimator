"""Management arms — when to leave a live trade (plan §B.2).

  hold                 (H1) — never exit early; ride to expiry settlement. The promoted baseline.
  forecast_regate      (H2) — exit when the re-evaluated FORECAST gate flips to 'avoid' any day.
                              (Stage-1 A9; expected churn loser — kept to confirm under real marks.)
  mechanical_terminal  (H3) — model-free terminal-week manager: in the last TERMINAL_DTE days,
                              take profit at TAKE_FRAC·credit, variance-stop (accrued RV > entry
                              iv2), or naked stop (loss > STOP_MULT·credit). ★ the one to beat H1.
  iv_regate            (H4) — like H3 but the terminal trigger also fires on an IV-only re-gate.

Add an arm: implement `exit_on(path, ctx) -> (k, reason) | None` and register it. `path` is the
per-day MarkRow frame (mtm/pos_delta/accrued_rv/iv2/gate/dte), k ascending.
"""

from __future__ import annotations

import polars as pl

from stage2_trade_eval import config as cfg
from stage2_trade_eval.contracts import EntryContext, ManagementArm, register_management


@register_management
class Hold(ManagementArm):
    name = "hold"

    def exit_on(self, path: pl.DataFrame, ctx: EntryContext) -> tuple[int, str] | None:
        return None


@register_management
class ForecastRegate(ManagementArm):
    """H2 — daily forecast re-gate (the Stage-1 A9 redux)."""

    name = "forecast_regate"

    def exit_on(self, path: pl.DataFrame, ctx: EntryContext) -> tuple[int, str] | None:
        hit = path.filter(pl.col("gate") == "avoid").sort("k")
        if hit.is_empty():
            return None
        return int(hit["k"][0]), "risk_off"


@register_management
class MechanicalTerminal(ManagementArm):
    """H3 — model-free terminal-week management (the user's idea, the one to beat hold)."""

    name = "mechanical_terminal"
    naked_stop = True   # apply the naked-loss stop (set False for defined-risk-only books)

    def exit_on(self, path: pl.DataFrame, ctx: EntryContext) -> tuple[int, str] | None:
        credit = float(path["credit"][0]) if path.height else 0.0
        if credit <= 0:
            return None
        take = path.filter(pl.col("mtm") >= cfg.TAKE_FRAC * credit).sort("k")
        var_stop = path.filter(
            (pl.col("dte") <= cfg.TERMINAL_DTE) & (pl.col("accrued_rv") > pl.col("iv2"))
        ).sort("k")
        triggers: list[tuple[int, str]] = []
        if not take.is_empty():
            triggers.append((int(take["k"][0]), "take"))
        if not var_stop.is_empty():
            triggers.append((int(var_stop["k"][0]), "variance_stop"))
        if self.naked_stop:
            stop = path.filter(pl.col("mtm") <= -cfg.STOP_MULT * credit).sort("k")
            if not stop.is_empty():
                triggers.append((int(stop["k"][0]), "stop"))
        return min(triggers, key=lambda t: t[0]) if triggers else None


@register_management
class IvRegate(MechanicalTerminal):
    """H4 — H3 plus an IV-only terminal re-gate trigger (gate=='avoid' inside the terminal week)."""

    name = "iv_regate"

    def exit_on(self, path: pl.DataFrame, ctx: EntryContext) -> tuple[int, str] | None:
        base = super().exit_on(path, ctx)
        ivg = path.filter((pl.col("dte") <= cfg.TERMINAL_DTE) & (pl.col("gate") == "avoid")).sort("k")
        cands = [base] if base else []
        if not ivg.is_empty():
            cands.append((int(ivg["k"][0]), "iv_regate"))
        return min(cands, key=lambda t: t[0]) if cands else None
