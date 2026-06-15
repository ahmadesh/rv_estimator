"""Per-trade engine — open each gated candidate on ORATS, size, hold to expiry, settle (design §6, §9).

Flow (entry gating + sizing units are decided upstream in `signals`; the only surface here is the
option-space P&L of a hold-to-expiry put-credit spread):

    candidate (gated, size_units>0)
      -> chains.locate_expiry          : the ~30-DTE expiry in [25,45] DTE   (or skip)
      -> structures.put_credit_spread  : 0.25d short / 0.10d wing legs        (or skip)
      -> marks.open_trade              : entry fills, credit, width, max_loss (G7 liquidity / credit)
      -> sizing                        : n_raw = u*b*NAV/maxloss_c ; group-margin cap ; floor
      -> marks.settle_at_expiry        : intrinsic settlement on expiry-day spot
      -> ledger row (dollars; %-NAV)

The ledger is a flat per-trade table — the artifact the CSV, the daily P&L series and the scorecard
all consume.
"""

from __future__ import annotations

import polars as pl

from strategy_backtest.backtest import chains, management, marks, sizing, structures
from strategy_backtest.backtest import config as cfg
from strategy_backtest.backtest.contracts import EntryContext

LEDGER_COLS = [
    "ticker", "group", "segment", "entry_date", "expiry", "dte", "horizon", "fold_id",
    "short_strike", "wing_strike", "width", "credit", "max_loss", "maxloss_c",
    "ivrank", "vrp_score", "vrp_rel", "dispersion", "size_units", "n_raw", "contracts",
    "entry_spot", "settle_spot", "breached", "exit_date", "exit_reason",
    "gross_pnl", "cost", "pnl", "pnl_pct_nav",
]


def _open_candidate(row: dict) -> dict | None:
    """Pass 1: locate expiry, build legs, open the spread, compute n_raw. None to skip the trade."""
    ticker, entry_date = row["ticker"], row["date"]
    chain = chains.locate_expiry(ticker, entry_date)
    if chain is None:
        return None
    ctx = EntryContext(
        ticker=ticker, group=row["group"], entry_date=entry_date, expiry=chain.expiry,
        horizon=int(row["horizon"]), spot=chain.spot,
        signal={k: row.get(k) for k in ("vrp_score", "vrp_rel", "sigma", "iv2",
                                         "dispersion", "size_units", "fold_id")},
    )
    legs = structures.put_credit_spread_legs(chain, ctx)
    if not legs:
        return None
    try:
        opened = marks.open_trade(chain, legs, ctx)         # raises Rejected on G7 failure
    except marks.Rejected:
        return None

    maxloss_c = sizing.maxloss_per_contract(opened["width"], opened["credit"])
    n_raw = sizing.raw_contracts(float(row["size_units"]), maxloss_c)
    if n_raw <= 0:
        return None
    return {"row": row, "ctx": ctx, "opened": opened, "maxloss_c": maxloss_c, "n_raw": n_raw}


def _exit_result(ctx: EntryContext, opened: dict, arm: str,
                 panel: management.DailyPanel | None) -> dict | None:
    """Resolve a trade's exit for the chosen arm — uniform contract for both arms.

    hold           : settle at expiry intrinsic (the §5 primary / benchmark).
    managed[_no_x3]: walk the daily mark path, first-trigger-wins (§5.1; managed_no_x3 drops X3).
    Returns {exit_date, exit_reason, leg_val, settle_spot, breached, close_commission} or None.
    """
    if arm == "hold":
        settled = marks.settle_at_expiry(ctx.ticker, ctx, opened)
        if settled is None:
            return None
        return {"exit_date": ctx.expiry, "exit_reason": "expiry", "leg_val": settled["leg_val"],
                "settle_spot": settled["settle_spot"], "breached": settled["breached"],
                "close_commission": 0.0}
    return management.manage_trade(ctx, opened, panel, drop_x3=(arm == "managed_no_x3"))


def _build_row(cand: dict, contracts: float, res: dict) -> dict:
    """Build the ledger row from a sized trade (contracts) and its resolved exit (`res`)."""
    row, ctx, opened = cand["row"], cand["ctx"], cand["opened"]
    mult = cfg.CONTRACT_MULTIPLIER
    gross = contracts * (res["leg_val"] * mult)              # realised leg value (intrinsic or close mark)
    cost = contracts * (opened["entry_commission"] + res["close_commission"])   # entry + any close
    pnl = gross - cost
    return {
        "ticker": ctx.ticker, "group": ctx.group, "segment": row["segment"],
        "entry_date": ctx.entry_date, "expiry": ctx.expiry,
        "dte": int((ctx.expiry - ctx.entry_date).days), "horizon": ctx.horizon,
        "fold_id": row.get("fold_id"),
        "short_strike": float(opened["short_strike"]), "wing_strike": float(opened["wing_strike"]),
        "width": float(opened["width"]), "credit": float(opened["credit"]),
        "max_loss": float(opened["max_loss"]), "maxloss_c": float(cand["maxloss_c"]),
        "ivrank": _f(row.get("ivrank")), "vrp_score": _f(row.get("vrp_score")),
        "vrp_rel": _f(row.get("vrp_rel")), "dispersion": _f(row.get("dispersion")),
        "size_units": _f(row.get("size_units")), "n_raw": float(cand["n_raw"]),
        "contracts": float(contracts), "entry_spot": float(ctx.spot),
        "settle_spot": float(res["settle_spot"]), "breached": bool(res["breached"]),
        "exit_date": res["exit_date"], "exit_reason": res["exit_reason"],
        "gross_pnl": float(gross), "cost": float(cost), "pnl": float(pnl),
        "pnl_pct_nav": float(pnl / cfg.NAV),
    }


def run_book(candidates: pl.DataFrame, arm: str | None = None,
             panel: management.DailyPanel | None = None) -> pl.DataFrame:
    """Backtest the whole book on one exit arm; return the per-trade ledger (LEDGER_COLS schema).

    `candidates` are the gated, sized roll-date entries (size_units > 0) for both segments.
    `arm` ∈ {"hold","managed","managed_no_x3"} (default cfg.EXIT_ARM). The managed arms need the
    daily trigger `panel` (built once via management.load_panel()); it is loaded lazily if omitted.
    """
    arm = arm or cfg.EXIT_ARM
    if arm not in ("hold", "managed", "managed_no_x3"):
        raise ValueError(f"unknown exit arm {arm!r}")
    if arm != "hold" and panel is None:
        panel = management.load_panel()

    gated = candidates.filter(pl.col("size_units") > 0)
    if gated.is_empty():
        return pl.DataFrame(schema={c: pl.Utf8 for c in LEDGER_COLS})

    # Pass 1: open every candidate (G7 + strike/expiry availability filter here).
    opened: list[dict] = []
    for row in gated.iter_rows(named=True):
        cand = _open_candidate(row)
        if cand is not None:
            opened.append(cand)
    if not opened:
        return pl.DataFrame(schema={c: pl.Utf8 for c in LEDGER_COLS})

    # Pass 2a: resolve each trade's exit per ONE unit (independent of contracts) so we know its
    # realization (exit_date) before sizing — the concurrent-margin sim needs it to free margin.
    for c in opened:
        c["res"] = _exit_result(c["ctx"], c["opened"], arm, panel)
    opened = [c for c in opened if c["res"] is not None]
    if not opened:
        return pl.DataFrame(schema={c: pl.Utf8 for c in LEDGER_COLS})

    # Pass 2b: CONCURRENT per-group margin cap (design §7.1.5, extended for overlapping entries).
    # Walk entries in date order; a group's open margin is what earlier still-open trades committed
    # (freed once their exit_date passes). Same-day same-group entries pro-rate the *remaining* budget.
    rows = _book_with_margin(opened)
    if not rows:
        return pl.DataFrame(schema={c: pl.Utf8 for c in LEDGER_COLS})
    # infer_schema_length=None: scan ALL rows — early degraded rows carry fold_id=None (would infer
    # a Null column and reject later int fold_ids under weekly cadence's longer degraded run).
    return pl.DataFrame(rows, infer_schema_length=None).select(LEDGER_COLS).sort("entry_date", "ticker")


def _book_with_margin(opened: list[dict]) -> list[dict]:
    """Chronological concurrent-margin booking: cap *overlapping* per-group margin at the group cap.

    `opened` each carry ctx, opened (entry fills), maxloss_c, n_raw, and a resolved exit `res`. We
    process by entry_date; `open_margin[group]` is the margin of still-open trades (exit_date past the
    current entry_date is freed). Within a (date, group) batch the remaining budget is pro-rated, then
    rounded to whole contracts. This makes the 20%/group cap bind across weekly-overlapping trades,
    not just same-day ones.
    """
    from itertools import groupby

    budget = cfg.GROUP_MARGIN_CAP * cfg.NAV
    opened.sort(key=lambda c: (c["ctx"].entry_date, c["ctx"].group, c["ctx"].ticker))
    open_positions: list[list] = []          # [exit_date, group, margin] for still-open trades
    rows: list[dict] = []

    for entry_date, day_iter in groupby(opened, key=lambda c: c["ctx"].entry_date):
        day_cands = list(day_iter)
        open_positions = [p for p in open_positions if p[0] > entry_date]     # free expired margin
        committed: dict[str, float] = {}
        for ex_d, grp, m in open_positions:
            committed[grp] = committed.get(grp, 0.0) + m

        by_g: dict[str, list[dict]] = {}
        for c in day_cands:
            by_g.setdefault(c["ctx"].group, []).append(c)
        for grp, cs in by_g.items():
            remaining = budget - committed.get(grp, 0.0)
            desired = sum(c["n_raw"] * c["maxloss_c"] for c in cs)
            if desired <= 0:
                continue
            scale = max(0.0, min(1.0, remaining / desired))
            for c in cs:
                contracts = sizing.finalize_contracts(c["n_raw"] * scale)
                if contracts <= 0:
                    continue
                margin = contracts * c["maxloss_c"]
                rows.append(_build_row(c, contracts, c["res"]))
                open_positions.append([c["res"]["exit_date"], grp, margin])
    return rows


def _f(x) -> float:
    return float(x) if x is not None else float("nan")
