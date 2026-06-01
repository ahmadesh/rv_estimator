"""Central configuration for the RV forecasting evaluator.

Everything path-, universe-, horizon-, and protocol-related lives here so the rest
of the package never hard-codes a ticker list or a drive path. The eval universe and
its group map are hard-coded (small, stable) rather than read from the shifting
`universe.yml`; the source of those groupings is
`raw_data_ingestion_download/data_download_universe/universe.yml`.
"""

from __future__ import annotations

import os
from pathlib import Path

# --------------------------------------------------------------------------- paths
REPO_ROOT = Path(__file__).resolve().parents[1]

# Source lakes on the external drive (override with RV_EXDISK for testing/relocation).
EXDISK = Path(os.environ.get("RV_EXDISK", "/Volumes/Ex-Disk"))
ORATS_LAKE = EXDISK / "orats_parquet"                              # ticker=<T>/year=<Y>/data.parquet
POLYGON_LAKE = EXDISK / "polygon_parquet"
MINUTE_LAKE = POLYGON_LAKE / "us_stocks_sip" / "minute_aggs_v1"    # ticker=<T>/data.parquet
DAILY_LAKE = POLYGON_LAKE / "us_stocks_sip" / "day_aggs_v1"        # ticker=<T>/data.parquet
CORP_ACTIONS_LAKE = POLYGON_LAKE / "corporate_actions"            # splits/dividends/ticker_events.parquet
MARKET_HOLIDAYS = POLYGON_LAKE / "reference" / "market_holidays.parquet"

# Local working area (gitignored). The user named this `execution/data`.
EXEC_ROOT = Path(os.environ.get("RV_EXEC_ROOT", REPO_ROOT / "execution"))
DATA_ROOT = EXEC_ROOT / "data"
RAW_ROOT = DATA_ROOT / "raw"                                      # staged subset mirror
RAW_MINUTE = RAW_ROOT / "minute"                                 # ticker=<T>/data.parquet
RAW_DAILY = RAW_ROOT / "daily"                                   # ticker=<T>/data.parquet
RAW_ORATS = RAW_ROOT / "orats"                                   # ticker=<T>/year=<Y>/data.parquet
RAW_CORP = RAW_ROOT / "corp_actions"                             # splits/dividends/ticker_events.parquet
RAW_HOLIDAYS = RAW_ROOT / "market_holidays.parquet"
STAGE_MANIFEST = RAW_ROOT / "_manifest.csv"

INPUTS_PARQUET = DATA_ROOT / "inputs.parquet"                     # comprehensive point-in-time base store
TARGETS_PARQUET = DATA_ROOT / "targets.parquet"                  # truth + IV^2 + regime (long by horizon)
FEATURES_PARQUET = DATA_ROOT / "features.parquet"               # optional cached wide feature matrix
PREDICTIONS_ROOT = DATA_ROOT / "predictions"

REPORTS_ROOT = EXEC_ROOT / "reports"
RUN_REGISTRY = REPORTS_ROOT / "registry.parquet"                # append-only run history for progression

# --------------------------------------------------------------------------- universe
# Clean core (build & iterate) — eval plan §8.
CLEAN_CORE: tuple[str, ...] = (
    "SPY", "QQQ", "IWM", "XLK", "XLF", "XLE", "TLT", "GLD", "HYG", "EEM",
)
# Hard cases (stress after the base works) — eval plan §8.
HARD_CASES: tuple[str, ...] = ("UVXY", "MSOS", "IBIT", "USO", "KRE")
# Index chains used only as feature sources (never scored as forecast targets).
FEATURE_SOURCES: tuple[str, ...] = ("SPX", "VIX")

# Tickers whose RV/targets are produced and scored.
SCORED_TICKERS: tuple[str, ...] = CLEAN_CORE + HARD_CASES
# Everything that must be staged off the drive.
ALL_TICKERS: tuple[str, ...] = SCORED_TICKERS + FEATURE_SOURCES

# Correlation-group map (subset of universe.yml relevant to the eval universe).
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
}

# Most-liquid ticker per group — used as the proxy-IV donor when a ticker's own
# option chain is too thin to extract stable IV (data_sourcing.md §4).
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
    "long_volatility_vix": "UVXY",
    "us_cannabis": "MSOS",
    "crypto": "IBIT",
}

# --------------------------------------------------------------------------- horizons
# Forecast horizons in trading days; 22d (~30 DTE) is primary. eval plan §1.
HORIZONS: tuple[int, ...] = (1, 5, 10, 22, 42)
PRIMARY_HORIZON = 22
HORIZON_DTE = {1: None, 5: 7, 10: 14, 22: 30, 42: 52}  # informational mapping to option DTE

# IV tenors (calendar days) extracted from option chains.
IV_TENORS_DAYS: tuple[int, ...] = (30, 60, 90)
# Forecast quantile grid — eval plan §1 output #2.
QUANTILES: tuple[float, ...] = (0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95)

TRADING_DAYS_PER_YEAR = 252

# --------------------------------------------------------------------------- sessions
ET_TZ = "America/New_York"
RTH_OPEN = (9, 30)   # 09:30 ET
RTH_CLOSE = (16, 0)  # 16:00 ET
BAR_MINUTES = 5      # realized-measure sampling frequency
# A regular session is 6.5h => 78 five-minute bars (close-to-close gives 78 returns).
FULL_SESSION_5MIN_BARS = 78
MIN_BAR_FRACTION = 0.95  # < 95% of expected bars => low-confidence day (eval plan §2)

# --------------------------------------------------------------------------- OOS protocol (§10)
OOS_START = "2018-01-01"      # ≥3–5y OOS spanning 2020 COVID / 2022 rates / 2025 tariff
MIN_TRAIN_DAYS = 252 * 3      # require ≥3y before the first OOS fold
REFIT_FREQ = "monthly"        # {"weekly","monthly"} refit cadence
TRAIN_WINDOW = "expanding"    # {"expanding","rolling"}
ROLLING_TRAIN_DAYS = 252 * 5  # used only when TRAIN_WINDOW == "rolling"
# Embargo between train_end and test_start = max(EMBARGO_EXTRA, h) trading days.
EMBARGO_EXTRA = 1

# --------------------------------------------------------------------------- hyperparameter tuning
# Tune-once-then-freeze (MODEL_PLAN §4 "Hyperparameter selection"): models with structural
# hyperparameters (XGBoost, LSTM, PDV) select them ONCE on a pre-OOS validation block, freeze
# them, then run the walk-forward. The validation block is [HPTUNE_VAL_START, OOS_START) so no
# OOS (>= OOS_START) data ever informs a hyperparameter; the search-train slice is everything
# before HPTUNE_VAL_START. After selection these dates are reused only as TRAIN rows (never test).
HPTUNE_VAL_START = "2016-01-01"      # validation block = 2016-2017 (last 2y before OOS)
HPTUNE_METRIC_HORIZON = PRIMARY_HORIZON   # select on pooled QLIKE at the primary horizon
HPTUNE_DL_SUBSET = ("SPY", "QQQ", "TLT", "XLE")   # representative tickers for tuning the LSTM

# Stress regimes for shaded report panels (label -> (start, end)).
STRESS_REGIMES = {
    "COVID 2020": ("2020-02-19", "2020-04-30"),
    "Rates 2022": ("2022-01-01", "2022-10-31"),
    "Tariff 2025": ("2025-03-01", "2025-06-30"),
}

# --------------------------------------------------------------------------- regimes (§6)
IV_PCTILE_BUCKETS = 5            # quintiles of trailing IV percentile
IV_PCTILE_LOOKBACK = 252         # rolling window for the IV percentile rank
POST_SHOCK_LOOKBACK = 5          # days after a vol spike counted as "post-shock"
POST_SHOCK_RV_QUANTILE = 0.95    # a "shock" = daily RV above this trailing quantile


def tickers_for(tier: str) -> tuple[str, ...]:
    """Resolve a ``--universe`` selector to its scored tickers."""
    return {
        "clean_core": CLEAN_CORE,
        "hard_cases": HARD_CASES,
        "all": SCORED_TICKERS,
    }[tier]


def annualize_variance(horizon_variance: float | "pl.Expr", h: int):  # noqa: F821
    """Sum-of-h-daily-variances -> annualized variance (×252/h)."""
    return horizon_variance * (TRADING_DAYS_PER_YEAR / h)
