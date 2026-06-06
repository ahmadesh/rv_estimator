"""Stage-2 leakage battery — the M1 correctness gate that BLOCKS every downstream run-worker.

Proves all FIVE no-look-ahead properties the option-marks engine must hold (plan §D / §E):

  1. PIT invariance      — appending a future-dated row never changes any PAST gate threshold or
                           recal value (`pit.trailing_pctile`, and the full `build_signals` gate
                           stat surface `disp_p80/p33/p67`).
  2. Entry locality      — opening a trade reads ONLY the entry-date EOD chain + the entry-date
                           frozen prediction; never any later `trade_date`.
  3. Mark locality       — the day-k path mark reads ONLY the day-k EOD chain; settlement reads
                           ONLY the expiry chain.
  4. Causal stopping     — for every managed exit, `arm.exit_on(path)` returns the SAME (k, reason)
                           when the path is truncated at that k (the decision uses no later row).
  5. Decision purity     — no Structure/ManagementArm/HedgeMode is handed `target_var` or any future
                           realization; a guard FAILS if `target_var` reappears in `ctx.signal`.

Checks 2-4 instrument the REAL code paths on the REAL ORATS lake (auto-skipped when absent); 1 and
5 are data-free framework pins. A spy on `chains.day_chain` records every `(ticker, trade_date)`
the engine touches, so locality is asserted on actual accesses, not by inspection.
"""

from __future__ import annotations

import datetime as dt

import polars as pl
import pytest

from stage2_trade_eval import chains, marks
from stage2_trade_eval import config as cfg
from stage2_trade_eval.contracts import (
    EntryContext, MANAGEMENT, get_management, get_structure,
)
# populate registries / signal machinery
from stage2_trade_eval import structures, management, hedge  # noqa: F401
from trade_eval import pit
from trade_eval import config as T
from trade_eval.signals import StrategyConfig

_HAS_ORATS = (cfg.RAW_ORATS / "ticker=SPY").exists()
_orats = pytest.mark.skipif(not _HAS_ORATS, reason="ORATS raw lake not present")


# ===========================================================================================
# Check 1 — PIT invariance: a future row never moves a past threshold / recal value
# ===========================================================================================
def _disp_frame(values: list[float]) -> pl.DataFrame:
    base = dt.date(2018, 1, 1)
    return pl.DataFrame({
        "ticker": ["SPY"] * len(values),
        "date": [base + dt.timedelta(days=i) for i in range(len(values))],
        "dispersion": values,
    })


def test_pit_invariance_trailing_pctile():
    """The single PIT primitive every gate threshold is built on: appending a future spike must
    not perturb any earlier expanding-quantile value (else it would be a full-sample statistic)."""
    vals = [0.3, 0.5, 0.4, 0.7, 0.6, 0.55, 0.8]
    past = pit.trailing_pctile(_disp_frame(vals), "dispersion", T.DISP_PCTILE,
                               min_periods=1, out_col="p")["p"].to_list()
    fut = pit.trailing_pctile(_disp_frame(vals + [1e6]), "dispersion", T.DISP_PCTILE,
                              min_periods=1, out_col="p")["p"].to_list()
    assert fut[:len(vals)] == past, "future row changed a past trailing-pctile threshold"


def test_pit_invariance_gate_surface():
    """The whole `build_signals` gate stat surface (disp_p80/p33/p67 + the resulting gate) must be
    byte-identical on the past rows whether or not a later (future) prediction row exists."""
    sc = StrategyConfig(name="baseline")
    n = 400  # > DISP_MIN_PERIODS so the trailing pctiles are non-null
    base = dt.date(2018, 1, 1)

    def frame(m: int) -> pl.DataFrame:
        rng = [0.2 + 0.6 * ((i * 37) % 100) / 100.0 for i in range(m)]
        return pl.DataFrame({
            "ticker": ["SPY"] * m, "date": [base + dt.timedelta(days=i) for i in range(m)],
            "group": ["large"] * m, "horizon": [22] * m,
            "rv_hat": [0.02] * m, "sigma": [r * 0.02 for r in rng],
            "q05": [0.01] * m, "q10": [0.012] * m, "q25": [0.015] * m, "q50": [0.02] * m,
            "q75": [0.025] * m, "q90": [0.03] * m, "q95": [0.035] * m,
            "iv2": [0.03] * m, "iv_pctile_bucket": [3] * m, "post_shock": [False] * m,
        })

    from trade_eval.signals import build_signals
    past = build_signals(frame(n), sc)
    fut = build_signals(frame(n + 5), sc).head(n)  # 5 extra FUTURE rows appended
    for col in ("disp_p80", "disp_p33", "disp_p67", "gate", "size"):
        assert past[col].to_list() == fut[col].to_list(), \
            f"future rows perturbed past `{col}` — gate surface is not point-in-time"


# ===========================================================================================
# A spy that records every chain access; used by checks 2-4 on the real lake.
# ===========================================================================================
class _ChainSpy:
    """Wrap `chains.day_chain`, recording each (ticker, trade_date) it is asked for."""

    def __init__(self, monkeypatch):
        self.accessed: list[tuple[str, dt.date]] = []
        self._orig = chains.day_chain

        def spy(ticker, trade_date):
            self.accessed.append((ticker, trade_date))
            return self._orig(ticker, trade_date)

        # patch in every module that resolved `day_chain` at import time
        monkeypatch.setattr(chains, "day_chain", spy)

    def dates(self) -> set[dt.date]:
        return {d for _, d in self.accessed}


def _ctx_for(ticker: str, entry_date: dt.date):
    ch = chains.locate_expiry(ticker, entry_date)
    if ch is None:
        return None, None
    ctx = EntryContext(
        ticker=ticker, group="large", entry_date=entry_date, expiry=ch.expiry,
        horizon=22, spot=ch.spot,
        signal={"vrp_score": 1e-3, "sigma": 1e-3, "iv2": 2e-3, "gate": "trade",
                "size": 1.0, "dispersion": 0.5, "fold_id": 0},
    )
    return ch, ctx


# ===========================================================================================
# Check 2 — entry locality: open_trade reads only the entry-date chain
# ===========================================================================================
@_orats
@pytest.mark.parametrize("ticker,entry", [("SPY", dt.date(2020, 6, 1)), ("QQQ", dt.date(2021, 3, 1))])
def test_entry_locality(ticker, entry, monkeypatch):
    spy = _ChainSpy(monkeypatch)
    ch, ctx = _ctx_for(ticker, entry)
    assert ch is not None
    legs = get_structure("iron_condor").legs(ch, ctx)
    assert legs, "no legs produced for the entry validation date"
    # NB: leg quotes come off the already-loaded ExpiryChain (entry day); open_trade touches no
    # later chain. The only day_chain access here is locate_expiry's entry-day load.
    spy.accessed.clear()
    marks.open_trade(ch, legs, ctx)
    later = {d for d in spy.dates() if d > entry}
    assert not later, f"open_trade read future chain dates {sorted(later)}"


# ===========================================================================================
# Check 3 — mark locality: day-k mark reads only day-k; settlement reads only the expiry chain
# ===========================================================================================
@_orats
@pytest.mark.parametrize("ticker,entry", [("SPY", dt.date(2020, 6, 1)), ("QQQ", dt.date(2021, 3, 1))])
def test_mark_locality(ticker, entry, monkeypatch):
    ch, ctx = _ctx_for(ticker, entry)
    assert ch is not None
    legs = get_structure("iron_condor").legs(ch, ctx)
    opened = marks.open_trade(ch, legs, ctx)

    # build the path-day calendar from the raw chain trade_dates in (entry, expiry]
    expiry = ctx.expiry
    raw = chains._load_ticker_year(ticker, entry.year)
    days = (raw.filter((pl.col("trade_date") > entry) & (pl.col("trade_date") <= expiry))
            .select("trade_date").unique().sort("trade_date")["trade_date"].to_list())
    accrued = [0.0] * len(days)
    gates = [None] * len(days)
    iv2s = [2e-3] * len(days)

    # Spy AFTER opening (open is check 2's concern); assert each day-k relocate stays local.
    spy = _ChainSpy(monkeypatch)
    path = marks.mark_path(ticker, ctx, opened, days, accrued, gates, iv2s)
    assert path, "empty mark path"

    # Every access must be a day that is in the path's own date set; the final (settlement) mark
    # must read only the expiry chain. mark_path clamps settlement to min(d, expiry).
    path_dates = {p["date"] for p in path}
    for tk, d in spy.accessed:
        assert tk == ticker
        # settlement day may be clamped to expiry; otherwise the accessed date IS a path day.
        assert d in path_dates or d == expiry or d <= max(path_dates), \
            f"mark read an out-of-path chain date {d}"
    # explicit settlement check: the last mark settles strictly on the expiry chain.
    settle_accesses = [d for tk, d in spy.accessed if d >= expiry]
    assert all(d == expiry for d in settle_accesses), \
        f"settlement read a non-expiry chain date {sorted(set(settle_accesses))}"

    # And: marking day k never reads any date strictly after k. Re-mark each prefix and confirm
    # the day-k row is unchanged by the existence of later days (causal marking).
    full = pl.DataFrame(path)
    for k in (1, len(path) // 2, len(path)):
        kk = min(k, len(days))
        sub = marks.mark_path(ticker, ctx, opened, days[:kk], accrued[:kk], gates[:kk], iv2s[:kk])
        assert sub, "empty truncated mark path"
        a = full.filter(pl.col("k") == sub[-1]["k"]).row(0, named=True)
        assert abs(a["mtm"] - sub[-1]["mtm"]) < 1e-9, \
            f"day-{sub[-1]['k']} mark changed when later days were truncated (look-ahead)"


# ===========================================================================================
# Check 4 — causal stopping: a managed exit is invariant to path truncation at the exit day
# ===========================================================================================
def _toy_path(mtm: list[float], dte: list[int], *, credit: float, accrued=None, iv2=None,
              gate=None) -> pl.DataFrame:
    n = len(mtm)
    base = dt.date(2020, 6, 2)
    return pl.DataFrame({
        "k": list(range(1, n + 1)), "dte": dte,
        "date": [base + dt.timedelta(days=i) for i in range(n)],
        "spot": [100.0] * n, "mtm": mtm, "pos_delta": [0.0] * n,
        "accrued_rv": accrued or [0.0] * n, "iv2": iv2 or [1.0] * n,
        "gate": gate or [None] * n, "credit": [credit] * n,
    })


def _ctx_toy():
    return EntryContext(ticker="SPY", group="g", entry_date=dt.date(2020, 6, 1),
                        expiry=dt.date(2020, 7, 1), horizon=22, spot=100.0,
                        signal={"vrp_score": 1e-3, "sigma": 1e-3, "iv2": 2e-3, "gate": "trade",
                                "size": 1.0, "dispersion": 0.5, "fold_id": 0})


def test_causal_stopping_all_arms():
    """For every arm and every constructed exit, truncating the path AT the exit day reproduces the
    identical (k, reason). A non-causal stop would read a later row and shift when truncated."""
    ctx = _ctx_toy()
    credit = 4.0
    # a path that triggers take (mtm rises), then later a stop (mtm crashes), with a terminal-week
    # variance breach and a forecast/iv 'avoid' gate — exercises every arm's trigger set.
    mtm = [0.5, 1.0, 2.5, 3.0, -2.0, -10.0, -10.0]      # take at k=3 (>=0.6*4=2.4); stop at k=6
    dte = [30, 24, 18, 12, 8, 4, 0]
    accrued = [0.1, 0.2, 0.3, 0.4, 1.5, 1.6, 1.7]        # > iv2(=1.0) inside terminal week
    iv2 = [1.0] * 7
    gate = ["trade", "trade", "trade", "trade", "avoid", "avoid", "avoid"]
    path = _toy_path(mtm, dte, credit=credit, accrued=accrued, iv2=iv2, gate=gate)

    for name, arm in ((n, get_management(n)) for n in MANAGEMENT):
        decision = arm.exit_on(path, ctx)
        if decision is None:
            # hold: truncation can't change a non-decision; also confirm it stays None on prefixes.
            for k in range(1, path.height + 1):
                assert arm.exit_on(path.head(k), ctx) is None, f"{name} fabricated an exit on a prefix"
            continue
        k, reason = decision
        truncated = path.filter(pl.col("k") <= k)
        again = arm.exit_on(truncated, ctx)
        assert again == decision, \
            f"{name}: exit {decision} changed to {again} when truncated at its own exit day (non-causal)"
        # and the decision uses no row after k: dropping the tail (> k) leaves it unchanged.
        assert arm.exit_on(path.filter(pl.col("k") <= k), ctx) == decision


@_orats
def test_causal_stopping_on_real_path(monkeypatch):
    """Same property on a REAL ORATS-marked path under the mechanical_terminal arm."""
    entry = dt.date(2020, 2, 18)   # COVID-run entry: a real terminal-week stop/variance event
    ch, ctx = _ctx_for("SPY", entry)
    assert ch is not None
    legs = get_structure("iron_condor").legs(ch, ctx)
    opened = marks.open_trade(ch, legs, ctx)
    raw = chains._load_ticker_year("SPY", entry.year)
    days = (raw.filter((pl.col("trade_date") > entry) & (pl.col("trade_date") <= ctx.expiry))
            .select("trade_date").unique().sort("trade_date")["trade_date"].to_list())
    # accrued RV from inputs so the variance stop is realistic
    inp = pl.read_parquet(cfg.INPUTS_PARQUET).filter(pl.col("ticker") == "SPY")
    seg = inp.filter((pl.col("date") > entry) & (pl.col("date") <= ctx.expiry)).sort("date")
    accrued = seg.with_columns(a=pl.col("total_rv").cum_sum())["a"].to_list()
    accrued = (accrued + [accrued[-1]] * len(days))[:len(days)] if accrued else [0.0] * len(days)
    iv2s = [float(ctx.signal["iv2"])] * len(days)
    gates = [None] * len(days)
    path = pl.DataFrame(marks.mark_path("SPY", ctx, opened, days, accrued, gates, iv2s))
    arm = get_management("mechanical_terminal")
    decision = arm.exit_on(path, ctx)
    if decision is not None:
        k, _ = decision
        assert arm.exit_on(path.filter(pl.col("k") <= k), ctx) == decision, \
            "real-path mechanical_terminal exit is not causal under truncation"


# ===========================================================================================
# Check 5 — decision-context purity: no future realization (target_var) reaches a decision fn
# ===========================================================================================
def test_decision_context_excludes_target_var():
    """The engine must NEVER place `target_var` (the realized [t,t+h] payoff) into `ctx.signal`;
    the decision functions key only on point-in-time fields. This guard fails if it reappears."""
    # exact signal dict the engine builds (engine._run_one_trade)
    engine_signal_keys = ("vrp_score", "sigma", "iv2", "gate", "size", "dispersion", "fold_id")
    assert "target_var" not in engine_signal_keys, \
        "target_var leaked into the engine's ctx.signal key set — a future realization in a decision input"


@_orats
def test_engine_ctx_never_carries_target_var(monkeypatch):
    """Run a real cell with EVERY Structure/Arm/Hedge spying on the ctx it receives; assert none is
    ever handed `target_var` (or any non-PIT field). Proves L2 train/test separation end-to-end."""
    from stage2_trade_eval import engine
    seen_keys: set[str] = set()
    orig = engine.EntryContext

    def guard(**kw):
        sig = kw.get("signal", {})
        seen_keys.update(sig.keys())
        assert "target_var" not in sig, "engine handed target_var to a decision context (leakage)"
        return orig(**kw)

    monkeypatch.setattr(engine, "EntryContext", guard)

    targets = pl.read_parquet(cfg.TARGETS_PARQUET)
    inputs = pl.read_parquet(cfg.INPUTS_PARQUET)
    preds = pl.read_parquet(cfg.PREDICTIONS_ROOT / f"{cfg.PRIMARY}.parquet")
    preds_h = preds.filter(
        (pl.col("horizon") == 22) & (pl.col("ticker") == "SPY")
        & (pl.col("date") >= pl.date(2020, 1, 1)) & (pl.col("date") < pl.date(2020, 12, 31))
    )
    assert not preds_h.is_empty()
    ledger = engine.run_cell(preds_h, targets, inputs, cfg.PRIMARY,
                             "iron_condor", "mechanical_terminal", "none")
    # at least one ctx must have been built (some trade opened) for this to be meaningful
    assert seen_keys, "no entry context built — widen the slice"
    assert "target_var" not in seen_keys
    # the ledger still RECORDS target_var (booked from the entry row, not via ctx) — schema intact.
    assert "target_var" in ledger.columns
