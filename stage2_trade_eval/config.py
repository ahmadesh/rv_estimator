"""Stage-2 configuration — option engine knobs only.

Universe, horizons, OOS window, group map and the entry gate/sizing all come from the upstream
single sources of truth (`rv_eval.config`, `trade_eval.config`) so nothing is re-hard-coded. Only
the *option-mechanics* knobs — DTE targeting, strike selection, fills, frictions, sizing, margin —
live here, and they are set **once**, never fit on the OOS being scored (plan §A.3).
"""

from __future__ import annotations

import os
from pathlib import Path

from rv_eval import config as C
from trade_eval import config as T

# --------------------------------------------------------------------------- reused upstream
RAW_ORATS = C.RAW_ORATS                      # execution/data/raw/orats/ticker=<T>/year=<Y>/data.parquet
PREDICTIONS_ROOT = C.PREDICTIONS_ROOT
TARGETS_PARQUET = C.TARGETS_PARQUET
INPUTS_PARQUET = C.INPUTS_PARQUET
GROUP = C.GROUP
CLEAN_CORE = C.CLEAN_CORE                     # the 10 core ETFs — Stage-2 default universe
HARD_CASES = C.HARD_CASES
OOS_START = C.OOS_START
PRIMARY_HORIZON = C.PRIMARY_HORIZON           # 22 (~30 DTE) — the only horizon that trades (plan §0)
TRADING_DAYS_PER_YEAR = C.TRADING_DAYS_PER_YEAR

# Roles carried from Stage-1 (plan §B.3): EnsembleTopK primary, HAR-X graceful-degrade fallback.
PRIMARY = T.PRIMARY
FALLBACK = T.FALLBACK
BENCHMARK = T.BENCHMARK                        # "IV-only" — rebuilt in OPTION space as the null

# --------------------------------------------------------------------------- outputs
REPO_ROOT = C.REPO_ROOT
# Output root is overridable via env so parallel run-workers can write to isolated subdirs
# (default unchanged -> existing behavior / already-written artifacts preserved).
RESULTS_ROOT = Path(os.environ.get("STAGE2_RESULTS_ROOT", str(REPO_ROOT / "stage2_trade_eval" / "results")))
LEDGER_ROOT = RESULTS_ROOT / "ledger"
PORTFOLIO_ROOT = RESULTS_ROOT / "portfolio"
MANIFEST_PARQUET = RESULTS_ROOT / "manifest.parquet"

# --------------------------------------------------------------------------- expiry / DTE targeting
# Enter the listed expiry nearest this many CALENDAR days (≈ 22 trading days = the h=22 roll).
TARGET_DTE = 30
DTE_TOLERANCE = (21, 45)                       # acceptable expiry window; outside -> no trade that day

# --------------------------------------------------------------------------- strike selection (by |delta|)
# Structures pick strikes off the entry-day chain's option delta (calls: `delta`; puts: `delta-1`).
SHORT_DELTA = 0.20                             # short leg ≈ 1σ (16-25Δ band typical)
WING_DELTA = 0.07                              # long protective wing for defined-risk structures
STRADDLE_DELTA = 0.50                          # ATM leg for straddle / iron-fly body

# --------------------------------------------------------------------------- fills & frictions (plan §C.7)
# Conservative: cross the spread on both entry and any early close; expiry settles at intrinsic.
FILL = "cross"                                 # {"cross" (bid/ask), "mid"} — "mid" for diagnostics only
CONTRACT_MULTIPLIER = 100.0                    # equity-option multiplier ($ per 1.00 of premium)
COMMISSION_PER_CONTRACT = 0.65                 # per leg, per contract, each transaction
SLIPPAGE_TICKS = 0.0                           # extra adverse ticks on top of bid/ask (stress knob)

# --------------------------------------------------------------------------- liquidity filters (reject illiquid legs)
MIN_OI = 50                                    # min open interest on every leg
MIN_VOLUME = 0                                 # min daily volume on every leg (0 = ignore)
MAX_REL_SPREAD = 0.35                          # reject a leg if (ask-bid)/mid exceeds this
MIN_NET_CREDIT = 0.05                          # reject a structure whose net credit is below this ($/share)
MIN_CREDIT_TO_WIDTH = 0.10                     # defined-risk: reject if credit/width below this

# --------------------------------------------------------------------------- sizing — fractional Kelly (plan §C.4)
# size_units = clip( KELLY_C * edge/variance , 0, SIZE_CAP ). The entry `size` from trade_eval is
# already inverse-risk (∝ vrp/σ²) = Kelly form; KELLY_C re-scales it, NAV/contracts handled below.
# Kelly fractions + size cap. Defaults 0.30 / 0.15 / 3.0; each overridable via env (additive sweep
# knobs, same pattern as STAGE2_RESULTS_ROOT). Absent env -> defaults unchanged (W2/W4 unaffected).
KELLY_C_DEFINED = float(os.environ.get("STAGE2_KELLY_C_DEFINED", "0.30"))  # defined-risk Kelly frac
KELLY_C_NAKED = float(os.environ.get("STAGE2_KELLY_C_NAKED", "0.15"))      # naked: half-Kelly (tail)
SIZE_CAP = float(os.environ.get("STAGE2_SIZE_CAP", "3.0"))                 # max size units

# --------------------------------------------------------------------------- account / margin (plan §E)
NAV = 1_000_000.0                               # account base for %-NAV P&L and buying-power caps
RISK_BUDGET = 0.01                              # target risk fraction of NAV per unit size
GROUP_MARGIN_CAP = 0.20                         # max fraction of NAV margin in any one correlation group
ROUND_TO_CONTRACTS = False                      # True -> integer contracts off NAV; False -> continuous units

# --------------------------------------------------------------------------- management (plan §B.2 / §C.5)
TERMINAL_DTE = 12                               # below this DTE the terminal-week manager becomes active
TAKE_FRAC = T.TAKE_FRAC                         # profit-take at this fraction of max capturable credit
STOP_MULT = T.STOP_MULT                         # naked stop at loss > STOP_MULT * credit

# --------------------------------------------------------------------------- hedging (plan §C.6)
DELTA_BAND = 0.10                               # re-hedge when |position delta| > DELTA_BAND * (NAV/spot-equiv)
HEDGE_COST_BPS = 1.0                            # round-trip share-hedge cost, bps of traded notional

# --------------------------------------------------------------------------- default grid (plan §D / §E milestones)
DEFAULT_MODELS = (PRIMARY, FALLBACK, BENCHMARK)
DEFAULT_STRUCTURES = ("iron_condor", "short_strangle")     # defined-risk workhorse + naked overlay
DEFAULT_MANAGEMENT = ("hold", "mechanical_terminal")
DEFAULT_HEDGE = ("none",)


def kelly_c_for(structure: str) -> float:
    """Kelly fraction by structure family — naked carries half the defined-risk fraction."""
    from stage2_trade_eval.structures import is_defined_risk
    return KELLY_C_DEFINED if is_defined_risk(structure) else KELLY_C_NAKED
