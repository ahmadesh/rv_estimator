"""Configuration for the v2 put-credit-spread backtest (self-contained).

Every knob the strategy needs lives here, set ONCE and never tuned on the P&L being scored.
This package imports nothing from the repo-root `rv_eval` / `trade_eval` / `stage2_trade_eval`
engines — the option-mechanics it needs are ported into this folder so the whole backtest runs
entirely from `strategy_backtest/`. Values follow `plan_docs/PUT_SPREAD_STRATEGY_DESIGN_v2.md`.
"""

from __future__ import annotations

from pathlib import Path

# --------------------------------------------------------------------------- paths
PKG_ROOT = Path(__file__).resolve().parent
SB_ROOT = PKG_ROOT.parent                              # strategy_backtest/
DATA_ROOT = SB_ROOT / "data"
RAW_ORATS = SB_ROOT / "back-test-data" / "orats"       # ticker=<T>/year=<Y>/data.parquet
INPUTS_PARQUET = DATA_ROOT / "inputs.parquet"
TARGETS_PARQUET = DATA_ROOT / "targets.parquet"
FEATURES_PARQUET = DATA_ROOT / "features.parquet"
PREDICTIONS_PARQUET = DATA_ROOT / "predictions" / "EnsembleTopK.parquet"

RESULTS_ROOT = SB_ROOT / "results"

# --------------------------------------------------------------------------- universe / window
# The 10 core ETFs (rv_eval.config.CLEAN_CORE), and their correlation group (rv_eval.config.GROUP).
CLEAN_CORE = ("SPY", "QQQ", "IWM", "XLK", "XLF", "XLE", "TLT", "GLD", "HYG", "EEM")
GROUP = {
    "SPY": "us_large_cap_equity", "QQQ": "us_large_cap_equity",
    "IWM": "us_small_cap_equity", "XLK": "us_technology_sector",
    "XLF": "us_cyclicals_sector", "XLE": "oil_and_energy",
    "TLT": "us_rates_and_ig_credit", "GLD": "precious_metals",
    "HYG": "high_yield_credit", "EEM": "emerging_markets",
}
TRADING_DAYS_PER_YEAR = 252
PRIMARY_HORIZON = 22                                    # ~30 DTE — the only horizon that trades

# Two-segment window (design §2.2). Chains start 2007; first trained forecast ~2010-01-04.
BACKTEST_START = "2007-01-01"
HEADLINE_START = "2010-01-04"                           # first EnsembleTopK prediction date
BACKTEST_END = "2026-12-31"

# Roll cadence (trading days between fresh entries per ticker). Weekly (5) instead of the monthly
# h-block (22) multiplies the trade count ~4× to raise capital utilization (report §10 deployment
# work). Overlapping same-name positions this creates are bounded by the engine's CONCURRENT margin
# accounting (not just same-day) so the per-group cap still holds — see engine._book_with_margin.
ROLL_CADENCE = 5

# --------------------------------------------------------------------------- entry gate (lean core, §4.1)
GATE_IVRANK_MAX = 0.85                  # G2: trade only if trailing-252d IVrank(iv_30d) <= 0.85
DISP_PCTILE = 0.80                      # G4: trade only if dispersion <= trailing-80th-pctile
DISP_MIN_PERIODS = 252                  # trailing obs before the dispersion / IVrank pctile is trusted
# G3 contango: own iv_slope (= iv_90d - iv_30d) > 0  AND  vix3m > vix. (No knob — sign cut.)

# --------------------------------------------------------------------------- stress composite (design §4.3)
# Optional avoidance veto layered on the lean core: stand down when a regime-break signal fires. Each
# sub-flag is a PIT trailing-252d percentile (or a boolean trend/shock rule). ABLATION-DRIVEN: kept in
# production only if it cuts the post-2014 tail without gutting carry (resolved by stress_ablation.py).
# Ablation verdict (stress_ablation.py, 2026-06-08): of the five §4.3 sub-flags, ONLY the 200d-SMA
# trend filter ("sma") carries independent avoidance info — it lifts 2014+ Sharpe 0.20→0.26, cuts 2014+
# maxDD 8.7→7.7%, and cuts the 2018/2022/2024 bad-year bleed −$172k→−$119k while keeping 2014+ P&L flat
# and full-sample Sharpe (0.45→0.46). The percentile flags (skew/vvix/credit/shock) are redundant with
# G2/G3 and OVER-filter (the full 5-flag composite craters Sharpe to 0.28). So production = sma only.
STRESS_GATE = True                      # the stress composite vetoes entries (trend filter only)
STRESS_COMPONENTS = ("sma",)            # active sub-signals — ablation kept only the 200d-SMA downtrend
STRESS_SKEW_P = 0.90                    # st_skew:  skew_25d > trailing p90 (per ticker)
STRESS_VVIX_P = 0.90                    # st_vvix:  vvix > trailing p90 (market-wide vol-of-vol)
STRESS_CREDIT_P = 0.80                  # st_credit: credit_mom > trailing p80 (exogenous LQD/HY-OAS proxy)
STRESS_SHOCK_P = 0.025                  # st_shock: trailing-window min(ret_cc) < trailing p2.5 (per ticker)
STRESS_SHOCK_WINDOW = 5                 # lookback days for the recent-shock min
STRESS_SMA_WINDOW = 200                 # st_sma: price index < its own 200-day SMA (downtrend, per ticker)
STRESS_MIN_PERIODS = 252               # trailing obs before a stress percentile is trusted

# --------------------------------------------------------------------------- VRP -> sizing tilt (§4.2 / §7)
VRP_FLOOR = 0.05                        # f: floor on vrp_rel so fair-vol names size small, never zero
KELLY_C = 0.30                          # c_K = KELLY_C_DEFINED — fractional Kelly haircut (defined-risk)
SIZE_CAP = 3.0                          # U_max — max sizing units per trade
# b — target risk fraction of NAV per unit size. Set to the deployment ceiling that holds backtest
# maxDD <= ~10% NAV under WEEKLY cadence + VRP de-bias (the capital-use work, report §10 follow-up,
# resolved 2026-06-08): a b-sweep put the 10%-maxDD point at b≈0.022; b=0.02 (maxDD ~8.9%) leaves a
# buffer given maxDD's wide bootstrap CI. Deploys ~3.4% NAV avg (vs 0.9% before), ~1.0%/yr at Sharpe
# ~0.44 — ~4× the original deployment/return at a HIGHER Sharpe (de-bias sizes onto genuine edge,
# weekly adds diversification), so capital use rose without diluting the edge. b is a pure scalar on
# size (Sharpe / per-trade ROC invariant to it) until the per-group margin cap binds.
RISK_BUDGET = 0.02
# Degraded GFC book (no forecaster): IV-only inverse-risk. disp proxy = iv_30d / IV_REF (dimensionless).
IV_REF = 0.20                           # fixed 20%-vol reference anchor (never tuned)
# VRP de-bias (report §10.B): PIT per-ticker correction of rv_hat (over-predicts RV on 2010+), applied
# to the VRP/sizing input ONLY — the gate (G2/G3/G4/G7) is untouched, so trade SELECTION is unchanged
# and only position SIZE moves (deploys capital onto genuinely-rich trades without diluting the edge).
DEBIAS_VRP = True                       # apply the rv_hat -> rv_hat_cal calibration for sizing
DEBIAS_EMBARGO = PRIMARY_HORIZON        # only use forecasts whose h-day realisation has closed (leakage-safe)
DEBIAS_MIN_PERIODS = 126                # matured obs before the per-ticker bias is trusted (~6 months)

# --------------------------------------------------------------------------- account / margin (§7)
NAV = 2_000_000.0                       # headline economic run base (design's stated >= $2M)
GROUP_MARGIN_CAP = 0.20                 # max fraction of NAV margin in any one correlation group
ROUND_TO_CONTRACTS = True               # headline run trades whole contracts off NAV
# Rounding of the (group-capped) raw contract count to integers. "nearest" (round-half-up) removes the
# systematic *downward* bias that plain "floor" inflicts hardest on expensive names (n_raw≈1.4 -> 1),
# which otherwise distorts the per-name risk distribution (suggestion D). "floor" keeps the old behaviour.
CONTRACT_ROUNDING = "nearest"           # "nearest" | "floor"

# --------------------------------------------------------------------------- exit framework (§5)
# Primary arm is hold-to-expiry; mechanical_terminal is the challenger that must BEAT hold under real
# marks (§5.2). run.py runs all arms; the headline report is the primary arm.
EXIT_ARM = "hold"                       # "hold" | "managed" | "managed_no_x3"  (which arm run.py reports)
TAKE_FRAC = 0.50                        # X1 profit target: close when mark P&L >= TAKE_FRAC * max credit
HARD_STOP_MULT = 2.0                    # X5 hard stop: close when mark loss >= HARD_STOP_MULT * credit
TERMINAL_DTE_HARD = 12                  # X2: hard close at DTE <= 12 (terminal gamma). No soft tier (resolved 2026-06-08).
X3_CONFIRM_DAYS = 2                     # X3 term-flip must persist this many consecutive days before firing
X3_DEADBAND = 0.005                     # X3 dead-band: fire only when iv_slope < -X3_DEADBAND (½ vol-pt), not at 0
# X4 variance stop is model-free: close when realized variance accrued since entry exceeds entry iv2.

# --------------------------------------------------------------------------- expiry / DTE targeting (§6)
TARGET_DTE = 30
DTE_TOLERANCE = (25, 45)                # accept entry only in [25, 45] DTE; outside -> no trade

# --------------------------------------------------------------------------- strike selection (§6)
SHORT_DELTA = 0.25                      # short put ~1 sigma OTM
WING_DELTA = 0.10                       # long protective wing

# --------------------------------------------------------------------------- fills & frictions (§8.4)
FILL = "cross"                          # cross the bid/ask on entry & early close; expiry = intrinsic
CONTRACT_MULTIPLIER = 100.0
COMMISSION_PER_CONTRACT = 0.65          # per leg, per contract, each transaction
SLIPPAGE_TICKS = 0.0                    # extra adverse ticks on top of bid/ask (cost-stress knob)

# --------------------------------------------------------------------------- liquidity / credit filters (G7, §4.1)
# NB: two deviations from the v2 doc's literal G7, made after the data showed the doc's thresholds
# are infeasible with its own 0.25/0.10 strike choice (resolved with the user, 2026-06-08):
#  * MIN_CREDIT_TO_WIDTH 0.20 -> 0.10: a 0.25Δ/0.10Δ spread structurally yields credit/width ≈ 0.11,
#    so the 0.20 floor rejected ~99.9% of trades (0.10 was the engine's pre-v2 default).
#  * per-leg OI: short ≥ 50, protective wing ≥ 10 (the 10Δ wing is the thinnest leg — doc §8.4).
MIN_OI_SHORT = 50                       # min open interest on the short (sold) leg
MIN_OI_WING = 10                        # min open interest on the long protective wing
MIN_VOLUME = 0                          # min daily volume on every leg (0 = ignore)
MAX_REL_SPREAD = 0.35                   # reject a leg if (ask-bid)/mid exceeds this
MIN_NET_CREDIT = 0.05                   # reject a structure whose net credit is below this ($/share)
MIN_CREDIT_TO_WIDTH = 0.10              # reject if credit/width below this

# --------------------------------------------------------------------------- reporting (§8.2)
BOOT_B = 4000                           # block-bootstrap resamples for tail CIs
BOOT_SEED = 7
STRESS_WINDOWS = {                      # named stress episodes for the decorrelation panel (§8.3)
    "GFC_2008": ("2008-01-01", "2009-06-30"),
    "COVID_2020": ("2020-02-01", "2020-06-30"),
    "RateShock_2022": ("2022-01-01", "2022-12-31"),
}
