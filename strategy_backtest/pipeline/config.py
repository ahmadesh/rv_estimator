"""Central configuration for the put-spread backtest feature/forecaster pipeline.

Customized copy of ``rv_eval/config.py`` for ``strategy_backtest/``. The only substantive
deltas vs the upstream config are:

  * paths — ``RAW_ROOT`` points at the raw-only mirror ``strategy_backtest/back-test-data/``
    and ``DATA_ROOT`` points at the reusable cache ``strategy_backtest/data/`` (distinct from
    the upstream ``execution/data`` so the two never collide);
  * ``OOS_START`` extended to 2010 so the walk-forward predictions span the design's headline
    window (~2010 -> present); ``MIN_TRAIN_DAYS = 252*3`` from the 2007 ORATS floor pushes the
    first IV-aware fold to ~2010-2011 naturally (do NOT lower it — design v2 §2.2);
  * ``SCORED_TICKERS`` trimmed to ``CLEAN_CORE`` (the mirror has no HARD_CASES).

Everything else (universe groups, horizons, sessions, regime knobs) is verbatim so the copied
measurement / IV / feature / walk-forward code reads it unchanged.
"""

from __future__ import annotations

import os
from pathlib import Path

# --------------------------------------------------------------------------- paths
# strategy_backtest/pipeline/config.py -> parents[1] = strategy_backtest/
SB_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SB_ROOT.parent

# Source lakes on the external drive (kept only as a documented fallback; this backtest reads
# exclusively from the local mirror below).
EXDISK = Path(os.environ.get("RV_EXDISK", "/Volumes/Ex-Disk"))

# Raw-only mirror — matches the rv_eval RAW_* contract (verified against BACKTEST_DATA_SPEC.md).
RAW_ROOT = Path(os.environ.get("SB_RAW_ROOT", SB_ROOT / "back-test-data"))
RAW_MINUTE = RAW_ROOT / "minute"                                 # ticker=<T>/data.parquet
RAW_DAILY = RAW_ROOT / "daily"                                   # ticker=<T>/data.parquet
RAW_ORATS = RAW_ROOT / "orats"                                   # ticker=<T>/year=<Y>/data.parquet
RAW_CORP = RAW_ROOT / "corp_actions"                             # splits/dividends/ticker_events.parquet
RAW_HOLIDAYS = RAW_ROOT / "market_holidays.parquet"

# Reusable cache (gitignored) — the tier-1 panel + tier-2 predictions live here.
DATA_ROOT = Path(os.environ.get("SB_DATA_ROOT", SB_ROOT / "data"))
INPUTS_PARQUET = DATA_ROOT / "inputs.parquet"                    # tier-1 point-in-time base store
TARGETS_PARQUET = DATA_ROOT / "targets.parquet"                 # forward-RV targets (long by horizon)
FEATURES_PARQUET = DATA_ROOT / "features.parquet"              # tier-1 wide feature matrix
# tier-2 walk-forward forecasts (override the dir for ablation variants, e.g. the 8y-rolling run)
PREDICTIONS_ROOT = Path(os.environ.get("SB_PREDICTIONS_ROOT", DATA_ROOT / "predictions"))

# --------------------------------------------------------------------------- universe
# Clean core — the 10 names the strategy trades.
CLEAN_CORE: tuple[str, ...] = (
    "SPY", "QQQ", "IWM", "XLK", "XLF", "XLE", "TLT", "GLD", "HYG", "EEM",
)
# No hard cases in this mirror.
HARD_CASES: tuple[str, ...] = ()
# Index chains used only as feature sources (never scored as forecast targets).
FEATURE_SOURCES: tuple[str, ...] = ("SPX", "VIX")

# Optional universe extension (breadth experiments, e.g. the 2026-06 cross-sectional pivot):
# comma-separated tickers already staged in the mirror. Off unless the env var is set, so the
# original 10-name builds stay byte-reproducible.
EXTRA_TICKERS: tuple[str, ...] = tuple(
    t for t in os.environ.get("SB_EXTRA_TICKERS", "").split(",") if t
)

# Tickers whose RV/targets are produced and scored.
SCORED_TICKERS: tuple[str, ...] = CLEAN_CORE + HARD_CASES + EXTRA_TICKERS
# Everything that must be staged off the drive.
ALL_TICKERS: tuple[str, ...] = SCORED_TICKERS + FEATURE_SOURCES

# Correlation-group map (verbatim from rv_eval.config; extra entries are harmless).
GROUP: dict[str, str] = {
    "SPY": "us_large_cap_equity",
    "QQQ": "us_large_cap_equity",
    "IWM": "us_small_cap_equity",
    "XLK": "us_technology_sector",
    "XLF": "us_cyclicals_sector",
    "KRE": "us_cyclicals_sector",
    "XLE": "oil_and_energy",
    "USO": "oil_and_energy",
    "TLT": "us_rates_and_ig_credit",
    "GLD": "precious_metals",
    "HYG": "high_yield_credit",
    "EEM": "emerging_markets",
    "UVXY": "long_volatility_vix",
    "MSOS": "us_cannabis",
    "IBIT": "crypto",
    "SPX": "index_feature_source",
    "VIX": "index_feature_source",
    # breadth-extension names (2026-06 cross-sectional pivot experiments)
    "XLI": "us_industrial_sector",
    "XLU": "us_utilities_sector",
    "XLP": "us_staples_sector",
    "XLV": "us_healthcare_sector",
    "XLY": "us_discretionary_sector",
    "XLB": "us_materials_sector",
    "DIA": "us_large_cap_equity",
    "EFA": "developed_intl_equity",
    "FXI": "china_equity",
    "EWZ": "latam_equity",
    "GDX": "precious_metals",
    "SLV": "precious_metals",
    "XOP": "oil_and_energy",
    "SMH": "us_technology_sector",
    "XBI": "us_healthcare_sector",
    "IBB": "us_healthcare_sector",
    "XRT": "us_discretionary_sector",
    "IYR": "us_real_estate",
}

GROUP_LEADER: dict[str, str] = {
    "us_large_cap_equity": "SPY",
    "us_small_cap_equity": "IWM",
    "us_technology_sector": "XLK",
    "us_cyclicals_sector": "XLF",
    "oil_and_energy": "XLE",
    "us_rates_and_ig_credit": "TLT",
    "precious_metals": "GLD",
    "high_yield_credit": "HYG",
    "emerging_markets": "EEM",
}

# --------------------------------------------------------------------------- horizons
HORIZONS: tuple[int, ...] = (1, 5, 10, 22, 42)
PRIMARY_HORIZON = 22
HORIZON_DTE = {1: None, 5: 7, 10: 14, 22: 30, 42: 52}

IV_TENORS_DAYS: tuple[int, ...] = (30, 60, 90)
QUANTILES: tuple[float, ...] = (0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95)

TRADING_DAYS_PER_YEAR = 252

# --------------------------------------------------------------------------- sessions
ET_TZ = "America/New_York"
RTH_OPEN = (9, 30)
RTH_CLOSE = (16, 0)
BAR_MINUTES = 5
FULL_SESSION_5MIN_BARS = 78
MIN_BAR_FRACTION = 0.95

# --------------------------------------------------------------------------- OOS protocol
OOS_START = os.environ.get("SB_OOS_START", "2010-01-01")   # extended for this backtest (design v2 §2.2)
MIN_TRAIN_DAYS = 252 * 3      # >=3y before the first OOS fold — do NOT lower
REFIT_FREQ = "monthly"        # {"weekly","monthly"} refit cadence
TRAIN_WINDOW = os.environ.get("SB_TRAIN_WINDOW", "expanding")   # {"expanding","rolling"}
ROLLING_TRAIN_DAYS = int(os.environ.get("SB_ROLLING_TRAIN_DAYS", 252 * 8))  # 8y for the §3 rolling ablation
EMBARGO_EXTRA = 1

# --------------------------------------------------------------------------- regimes
IV_PCTILE_BUCKETS = 5
IV_PCTILE_LOOKBACK = 252
POST_SHOCK_LOOKBACK = 5
POST_SHOCK_RV_QUANTILE = 0.95


def tickers_for(tier: str) -> tuple[str, ...]:
    """Resolve a ``--universe`` selector to its scored tickers."""
    return {
        "clean_core": CLEAN_CORE,
        "hard_cases": HARD_CASES,
        "all": SCORED_TICKERS,
    }[tier]


def annualize_variance(horizon_variance, h: int):
    """Sum-of-h-daily-variances -> annualized variance (x252/h)."""
    return horizon_variance * (TRADING_DAYS_PER_YEAR / h)
