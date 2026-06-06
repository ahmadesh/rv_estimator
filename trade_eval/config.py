"""Strategy configuration for the Stage-1 trading evaluation.

Everything path-, universe-, horizon-, and protocol-related is reused from `rv_eval.config`
(the forecasting study's single source of truth) so the trading layer never re-hard-codes a
ticker list, group map, or OOS window. Only the *strategy* knobs — gate thresholds, sizing,
costs, management rules, and the model shortlist — live here, and they are set **once** and
never fit on the OOS P&L being scored (STAGE1_TRADING_EVAL_PLAN.md §6).
"""

from __future__ import annotations

import os
from pathlib import Path

from rv_eval import config as C

# --------------------------------------------------------------------------- reused from rv_eval
PREDICTIONS_ROOT = C.PREDICTIONS_ROOT          # execution/data/predictions/<model>.parquet
TARGETS_PARQUET = C.TARGETS_PARQUET            # truth + iv2 + iv_pctile_bucket + post_shock
INPUTS_PARQUET = C.INPUTS_PARQUET              # daily point-in-time store (total_rv path)
GROUP = C.GROUP                                # ticker -> correlation group
CLEAN_CORE = C.CLEAN_CORE                      # 10 liquid names
HARD_CASES = C.HARD_CASES                      # 5 thin / short-history names
OOS_START = C.OOS_START                        # "2018-01-01"
TRADING_DAYS_PER_YEAR = C.TRADING_DAYS_PER_YEAR

# --------------------------------------------------------------------------- outputs
REPO_ROOT = C.REPO_ROOT
RESULTS_ROOT = REPO_ROOT / "trade_eval" / "results"
LEDGER_ROOT = RESULTS_ROOT / "ledger"          # per-trade rows
PORTFOLIO_ROOT = RESULTS_ROOT / "portfolio"    # one-per-group daily P&L series
MANIFEST_PARQUET = RESULTS_ROOT / "manifest.parquet"   # every (model,h,ablation) cell evaluated

# --------------------------------------------------------------------------- model shortlist (§1.1)
# clean_core path (10 liquid names) and the short-history sleeve (5 thin names). Filenames
# verified against execution/data/predictions/. "IV-only" is computed, has no prediction file.
PRIMARY = "EnsembleTopK"            # frozen production primary
FALLBACK = "HAR-X"                  # transparent simple fallback
SLEEVE = ("HAR-Shrink2Group", "PanelHAR-FE")   # pooled hard-case sleeve
SHORT_H_CANDIDATE = "HAR-ENet"     # §5 short-horizon directional candidate (h in {5,10} only)
BENCHMARK = "IV-only"              # the fair-vol null; vrp = iv2 - trailing_RV

SHORTLIST: tuple[str, ...] = (PRIMARY, FALLBACK, *SLEEVE, SHORT_H_CANDIDATE, BENCHMARK)

# HAR-ENet is only a candidate at the short horizons where the §5 directional edge survives.
HORIZON_RESTRICT: dict[str, tuple[int, ...]] = {SHORT_H_CANDIDATE: (5, 10)}

# --------------------------------------------------------------------------- horizons (A8 sweep §2.5)
HORIZON_TRADE: tuple[int, ...] = (5, 10, 22)     # ~{7,14,30} DTE; 22 is primary
PRIMARY_HORIZON = C.PRIMARY_HORIZON              # 22
# Non-overlapping entry cadence per horizon: a fresh, non-overlapping h-day block. h=22 ≈ the
# monthly roll the forecasting study refits on, so entries align with the frozen folds.
ROLL_CADENCE: dict[int, int] = {h: h for h in HORIZON_TRADE}

# --------------------------------------------------------------------------- direction / sizing (§2.3)
SIGN_SHORT = +1                  # short-vol: collect when realized var lands below implied
BASE_NOTIONAL = 1.0              # Stage-1 abstraction; real strikes are Stage-2
K = 1.0                          # risk-aversion scale in size ∝ vrp_score / (K · σ²_pred)
SIZE_CAP = 3.0                   # max units of base_notional per position
REDUCE_MULT = 0.5               # "reduce" gate state -> half size
# σ²_pred risk scale: "sigma" uses the predictive log-sd; "qspread" uses (q95-q05) (A5 variant).
RISK_SCALE_DEFAULT = "sigma"

# --------------------------------------------------------------------------- regime gate (§2.2)
# Gate "avoid" percentile. Default 0.80; overridable via env (additive sweep knob, same pattern as
# STAGE2_RESULTS_ROOT) so a tuning worker can sweep the gate without editing the file. Absent env ->
# unchanged 0.80, so the default codepath (W2/W4) is identical.
DISP_PCTILE = float(os.environ.get("TRADE_EVAL_DISP_PCTILE", "0.80"))  # >trailing q-pctile -> avoid
DISP_MIN_PERIODS = 252          # min trailing obs before the dispersion pctile is trusted
DISP_TERCILE_LO, DISP_TERCILE_HI = 1.0 / 3.0, 2.0 / 3.0   # mid tercile -> "reduce"
IV_CHEAP_BUCKETS = (0, 1)       # low IV-percentile buckets -> "reduce"

# --------------------------------------------------------------------------- structure map (§2.4)
# Stage-1 collapses the per-group structure map (short put / put-spread / iron-fly / one-sided /
# call-wing) to the variance proxy with a per-group notional haircut. Defined-risk / thin names
# trade smaller; UVXY is "call-wing only / no naked short put" (it stresses the gate, not VRP),
# so it carries the smallest haircut. Real strikes are instantiated in Stage-2.
STRUCTURE_HAIRCUT_DEFAULT = 1.0
STRUCTURE_HAIRCUT: dict[str, float] = {
    "KRE": 0.75, "USO": 0.75, "HYG": 0.5, "MSOS": 0.35, "IBIT": 0.35, "UVXY": 0.25,
}

# --------------------------------------------------------------------------- costs (§3)
# Flat per-group bps haircut on turnover·notional. Wider for thin / structural-decay names.
C_BPS_DEFAULT = 5.0
# Round-trip turnover multiple (open + close). Cost is charged as a fraction of the premium
# sold (size·iv2), keeping it in the same variance units as the P&L it is subtracted from.
COST_ROUND_TRIP = 2.0
C_BPS: dict[str, float] = {
    "MSOS": 25.0, "IBIT": 20.0, "UVXY": 20.0, "USO": 10.0, "KRE": 10.0,
}
# Sweep grid for the later cost-sensitivity / break-even readout (§4.3). Not scored here.
C_BPS_SWEEP: tuple[float, ...] = (0.0, 2.5, 5.0, 10.0, 20.0)

# --------------------------------------------------------------------------- management overlay (§3.5, A9)
TAKE_FRAC = 0.6                 # profit-take when mark P&L >= TAKE_FRAC · capturable premium
STOP_MULT = 2.0                 # stop when mark loss > STOP_MULT · credit (premium)
# variance stop also fires when accrued realized var over [t,t+k] already exceeds entry iv2.

# --------------------------------------------------------------------------- benchmark sizing (§1.1)
BENCH_TRAIL_RV_H_MULT = 1       # IV-only trailing RV window = h trading days
BENCH_SIZE = "flat"            # {"flat","iv_pctile"} — the fair-vol null sizes flat by default

# --------------------------------------------------------------------------- controls (A7)
RANDOM_ENTRY_SEED = 0           # deterministic random-entry control
RANDOM_ENTRY_RATE = 0.5         # fraction of eligible slots randomly entered


def c_bps_for(ticker: str) -> float:
    """Per-group cost haircut in bps (wider for thin / structural-decay names)."""
    return C_BPS.get(ticker, C_BPS_DEFAULT)


def structure_haircut_for(ticker: str) -> float:
    """Per-group notional haircut from the §2.4 structure map (defined-risk / thin -> smaller)."""
    return STRUCTURE_HAIRCUT.get(ticker, STRUCTURE_HAIRCUT_DEFAULT)


def horizons_for(model: str) -> tuple[int, ...]:
    """Horizons a model is run at — most run the full sweep; HAR-ENet is short-h only."""
    return HORIZON_RESTRICT.get(model, HORIZON_TRADE)


def prediction_path(model: str) -> Path:
    """On-disk frozen prediction parquet for a forecaster (IV-only has none)."""
    return PREDICTIONS_ROOT / f"{model}.parquet"
