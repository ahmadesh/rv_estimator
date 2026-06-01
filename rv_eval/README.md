# rv_eval — Forward-RV Forecasting Evaluator

A **strategy-agnostic forecast-quality harness** for forward realized-volatility models.
This is the fixed yardstick referenced by
[`planning_docs/execution/rv_forecasting_eval_plan.md`](../planning_docs/execution/rv_forecasting_eval_plan.md)
(operationalizing [`planning_docs/research/rv_forecasting_methods.md`](../planning_docs/research/rv_forecasting_methods.md)).
Every candidate model is judged against it on identical data, identical splits, identical metrics.

## Purpose

We forecast forward realized volatility (the sum of the next `h` daily RVs). The first consumer
is a VRP / short-put book, but **nothing here is specific to it** — the same forecast quality
matters for dispersion, hedging, or any other vol strategy. This package answers, for any model:

- Is it better than HAR, EWMA, random walk, and *IV as a forecast*? (§3, §5)
- Is it unbiased *conditionally* — including after vol spikes and in high-IV regimes? (§6)
- Does it add information **beyond** IV²? (§5 conditional incremental-skill diagnostic)
- Did it improve or regress vs your prior runs and the benchmarks? (Progression panel)

Everything else — feature engineering, regime conditioning, position sizing, the trading
strategy itself — is **outside the evaluator's scope**. The user's `model.py` is iterated
independently; the harness only scores its predictions.

## Architecture at a glance

The whole package is built around **one principle**: do the expensive thing once, keep the
iterated thing cheap, and make leakage **structurally impossible** rather than a convention.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  raw bars + ORATS chains on /Volumes/Ex-Disk                               │
│                                                                             │
│        1. setup/data_stage.py  ─────────────────────────────►  execution/data/raw/  (once, ~13 GB)
│                                                                             │
│        2. setup/prepare_panel.py  ──────────────────────────►  inputs.parquet  +  targets.parquet  (once)
│                                                  ▲                          │
│            (measurement + range_vol + iv_features + targets)                │
│                                                                             │
│        3. walkforward.py  ←─ reads BOTH ─►  model.py  ──►  predictions.parquet  (per experiment)
│                          purged + embargoed                                 │
│                          rolling-origin folds                               │
│                                                                             │
│        4. evaluator.py  ←─ reads targets.parquet + predictions.parquet ──►  reports/<run>/    │
│                                                                                                │
│                                       report.html + report.md + metrics.json + registry.parquet
└─────────────────────────────────────────────────────────────────────────────┘
```

### The leakage split (why two files, not one)

The only future-looking columns are the forward `target_*` columns (they sum RV over `t+1..t+h`).
Daily inputs, IV, IV², and regime tags are all known at time `t` and safe to expose.

| File | Read by | Contains |
|---|---|---|
| `inputs.parquet`  | **only** `model.py` (and the harness) | point-in-time daily measures + IV + regime |
| `targets.parquet` | only the harness + `evaluator.py`     | forward `target_*` + IV² + regime tags    |

Three guards work in concert:

1. **File split** — `model.py` literally never opens `targets.parquet`.
2. **Contract** — `Model.fit(X, y)` (X and y are separate frames; a target can't be slipped in as a feature) and `Model.predict(X)` (no target object exists at predict time).
3. **Walk-forward purge + embargo** — train rows with `t + h > train_end − embargo` are dropped per horizon.

## Directory structure (every file, one line each)

```
rv_eval/
├── README.md                     this file
├── __init__.py                   empty package marker
│
├── config.py                     ★ universe (clean core + hard cases + SPX/VIX), group map,
│                                   horizons (1/5/10/22/42; primary 22), IV tenors (30/60/90d),
│                                   OOS start, refit cadence, embargo, paths to data/reports
├── features.py                   optional model-side feature builder: HAR lags, EWMA, log-RV,
│                                   semivariance windows, sqrt-RQ, IV passthrough. Every column
│                                   is point-in-time (.over("ticker") rolling), so building it on
│                                   the full series introduces no leakage.
├── model_contract.py             ★ the public Model ABC (fit(X,y) / predict(X)) + lognormal
│                                   quantile helper + per-(ticker,horizon) base class +
│                                   reference benchmarks: RandomWalk, EWMA, HAR, HAR-X.
│                                   `HARReference` is the default the walk-forward exercises.
├── walkforward.py                ★ purged + embargoed rolling-origin loop. Generates monthly
│                                   refit dates, slices the panel per fold, drives any Model,
│                                   accumulates OOS predictions → predictions.parquet.
├── evaluator.py                  ★ CLI — joins predictions to targets, runs Tier-1 (§3),
│                                   IV diagnostic (§5), calibration (§6), Tier-2 (§4) on demand,
│                                   §9 status, then assembles the report. Decoupled: any
│                                   predictions.parquet with the right schema can be scored.
├── report.py                     HTML (matplotlib + base64-embedded PNGs) + Markdown
│                                   (LLM-readable tables) + metrics.json + registry append +
│                                   Progression panel diffing vs prior runs.
│
├── setup/                        ──── one-time scripts (build the panel; never touched
│   │                                  again during model iteration) ────
│   ├── __init__.py
│   ├── data_stage.py             copies the 17-ticker raw subset off Ex-Disk into
│   │                               execution/data/raw/ (idempotent; writes _manifest.csv).
│   ├── measurement.py            5-min RV/BV/RS±/RQ/jump from minute bars; overnight
│   │                               close→open (split + dividend adjusted via
│   │                               corp_actions); Hansen-Lunde total RV = intraday + overnight.
│   │                               Sessions detected empirically (regular ≈ 78 buckets,
│   │                               early-close ≈ 42; well_behaved if ≥95% of expected).
│   ├── range_vol.py              daily Parkinson / Garman-Klass / Rogers-Satchell from OHLC
│   │                               (alt vol proxies + sanity cross-check); also carries
│   │                               daily volume + transactions.
│   ├── iv_features.py            ORATS chain → per-ticker ATM IV at 30/60/90d (interpolated
│   │                               across expiries at delta≈0.5), term slope, 25-delta skew,
│   │                               vendor extVol. Systematic regime from SPX (VIX/VIX3M term
│   │                               structure) and VIX (VVIX-like vol-of-vol) chains.
│   ├── targets.py                forward-h realized targets (sum of next h total-RVs) in
│   │                               variance & annualized-vol units, IV² horizon-de-annualized,
│   │                               regime tags (IV-percentile quintile, post-shock flag).
│   ├── prepare_panel.py          ★ orchestrates the above. Loops scored tickers, joins
│   │                               measurement + range + IV + systematic by date, adds group,
│   │                               writes inputs.parquet; then build_targets → targets.parquet.
│   └── validate_oxfordman.py     §2 SPY validation: our RTH RV vs the Oxford-Man / Stevens
│                                   realized library on well-behaved days (≤5% tolerance, signed
│                                   microstructure bias). Needs one external file (--ref).
│
├── metrics/                      ──── pure scoring functions; no I/O ────
│   ├── tier1.py                  §3 — add_pointwise (qlike, log err, in50/in90, pinball),
│   │                               summarize(by=[...]), within-group rank correlation.
│   ├── iv_diagnostic.py          §0/§5 — Error_model vs Error_IV; the incremental-skill
│   │                               regression realized_spread ~ a + b·model_spread + sign accuracy.
│   ├── calibration.py            §6 — conditional bias/QLIKE by regime bucket; flags the
│   │                               "unbiased overall but biased post-shock" trap.
│   ├── tier2.py                  §4 — Diebold-Mariano with Newey-West HAC, Hansen-Lunde-Nason
│   │                               Model Confidence Set via moving-block bootstrap.
│   └── status.py                 §9 — assigns Rejected / Research-candidate / benchmark
│                                   per model from Tier-1 + IV gain + post-shock flag.
│
└── tests/
    ├── test_measurement.py       writes a synthetic RTH session to a tmp dir; asserts RV
    │                               matches an independent numpy reference and RS+ + RS- = RV;
    │                               a monotone path has rs_minus == 0.
    └── test_walkforward.py       a Recorder Model captures every fold's (y_train, X_test); the
                                    test asserts for every horizon `h`, max(train idx) + h ≤
                                    (test_start idx) − embargo. No leakage by construction.
```

### Data & outputs live outside the package (gitignored)

```
execution/
├── data/
│   ├── raw/                      mirror of the 17-ticker subset off Ex-Disk + _manifest.csv
│   ├── inputs.parquet            point-in-time base store (the ONLY file model.py reads)
│   ├── targets.parquet           truth + IV² + regime (long by horizon)
│   ├── features.parquet          optional cache of features.build_features output
│   └── predictions/<model>.parquet  one walk-forward run per model
└── reports/
    ├── registry.parquet          append-only headline metrics per run × model × horizon
    └── run-<utc-timestamp>/      report.html, report.md, metrics.json per evaluation
```

## End-to-end flow

```bash
# 0. environment (once) — uv manages pyproject.toml + .python-version (3.12)
uv sync --extra dev

# 1. stage 17 tickers off /Volumes/Ex-Disk  (once, ~13 GB; idempotent)
.venv/bin/python -m rv_eval.setup.data_stage

# 2. build the panel  (once, ~5 s on this machine)
.venv/bin/python -m rv_eval.setup.prepare_panel
# -> execution/data/inputs.parquet  + execution/data/targets.parquet

# 3a. iterate: a reference benchmark
.venv/bin/python -m rv_eval.walkforward --benchmarks --universe clean_core
# -> execution/data/predictions/{RW,EWMA,HAR,HAR-X}.parquet

# 3b. iterate: your own model (by import path; same contract)
.venv/bin/python -m rv_eval.walkforward --model your_pkg.model:YourModel --universe clean_core
# -> execution/data/predictions/your-model.parquet

# 4. score everything currently in execution/data/predictions/ and write a report
.venv/bin/python -m rv_eval.evaluator --universe clean_core --tier 2 \
    --out execution/reports/run_$(date +%Y%m%dT%H%M%SZ)

# optional one-time check: validate measurement vs Oxford-Man (bring the reference file)
.venv/bin/python -m rv_eval.setup.validate_oxfordman --ref oxfordman.csv

# unit tests (synthetic measurement + walk-forward no-leakage)
.venv/bin/python -m pytest rv_eval/tests
```

Steps 1 and 2 are run **once**. Steps 3 and 4 are the iteration loop while you tune `model.py`.

## Writing a model

Subclass `Model` (`rv_eval.model_contract`). The walk-forward calls `fit` / `predict` per fold;
you never write a refit loop yourself.

```python
import polars as pl
from rv_eval.model_contract import Model
from rv_eval.features import build_features  # optional: HAR lags / EWMA / log-RV / IV passthrough

class MyModel(Model):
    name = "my-model"

    def fit(self, X: pl.DataFrame, y: pl.DataFrame) -> None:
        # X: one row per (ticker, date); columns = point-in-time inputs from inputs.parquet.
        #    Use build_features(X) to get HAR/EWMA/log-RV/IV-tenor columns, or build your own.
        # y: targets long by horizon — ticker, date, horizon, target_var (+ vol/overnight/intraday).
        ...

    def predict(self, X: pl.DataFrame) -> pl.DataFrame:
        # return: ticker, date, horizon, rv_hat [, q05, q10, q25, q50, q75, q90, q95, sigma]
        # rv_hat is in `target_var` units: the horizon variance = sum of next-h daily total-RVs.
        ...
```

Then run `walkforward.py --model your_pkg.model:MyModel` and the rest of the pipeline picks it up
automatically. The reference benchmarks in `model_contract.py` are working examples of the contract
(plain log-OLS HAR; lognormal quantiles; per-(ticker, horizon) state).

## What the report contains

The `report.html` panels (and the same numbers in `report.md` as flat tables):

| Panel | Plan section | What it answers |
|---|---|---|
| Verdict — §9 status                                | §9       | Rejected / Research-candidate, with the evidence |
| Progression vs previous run                        | (new)    | Signed Δ QLIKE vs the prior `registry.parquet` entry — progressed / regressed / flat per metric |
| QLIKE leaderboard (model vs benchmarks vs IV²)     | §3, §5   | The primary loss, pooled, per horizon |
| Forecast vs realized time series (h=22, stress shaded) | §3   | Eyeball check; COVID 2020 / Rates 2022 / Tariff 2025 highlighted |
| Interval coverage (50% / 90%)                      | §3       | Distribution head sanity (probabilistic models only) |
| Conditional bias by IV-percentile bucket           | §6       | The §6 trap: unbiased overall, biased at the regime that matters |
| §5 incremental-skill slope                         | §0, §5   | Does the model add information beyond IV²? (slope > 0, sign accuracy > 0.5) |
| Error-by-ticker / by-group tables                  | §3       | Is one ticker carrying the average? Is one group biased? |
| Within-group cross-sectional rank correlation      | §3       | Groundwork for "pick one name per group" |
| DM matrix + Model Confidence Set (Tier 2)          | §4       | Statistical confirmation of a Tier-1 signal |

`report.md` is deliberately compact and image-free so an LLM can ingest the numbers and tell you
whether the model progressed or regressed. `metrics.json` is the same headline metrics as a flat
dict for programmatic comparison. `registry.parquet` is append-only across runs and powers the
Progression panel.

## Configuration knobs (config.py)

- **Universe** — `CLEAN_CORE` (10), `HARD_CASES` (5), `FEATURE_SOURCES` (SPX, VIX). Hard-coded
  so the package is robust to repo reorganisations of `universe.yml`. Group map + group-leader
  fallback for thin-chain IV are in the same file.
- **Horizons** — `(1, 5, 10, 22, 42)` trading days; primary 22 (~30 DTE).
- **OOS protocol (§10)** — `OOS_START="2018-01-01"` (covers 2020 COVID / 2022 rates / 2025 tariff),
  `MIN_TRAIN_DAYS=756` (≥3y), `REFIT_FREQ="monthly"`, `TRAIN_WINDOW="expanding"`, `EMBARGO_EXTRA=1`.
- **Regime tags (§6)** — `IV_PCTILE_BUCKETS=5` quintiles over a 252-day rolling rank;
  post-shock = a daily RV above its trailing-252 95th percentile in the last 5 days.
- **Paths** — `EXDISK` (default `/Volumes/Ex-Disk`, overridable via `RV_EXDISK`) and
  `EXEC_ROOT` (default `<repo>/execution`, overridable via `RV_EXEC_ROOT`).

## Known caveats

- **Oxford-Man validation needs one external file** (free, one-time). Everything else is
  fully local / no network. `setup/validate_oxfordman.py` prints download instructions if `--ref`
  is omitted.
- **Forward-looking holiday calendar** — the staged `market_holidays.parquet` is a snapshot of
  *future* holidays only, so half-days are detected **empirically** from the data (a day whose
  last RTH bar is around 13:00 ET is treated as a half session with expected ≈ 42 buckets).
- **QQQ history under the old `QQQQ` ticker** — `polygon_parquet` keys QQQ from ~2011 onward;
  pre-2011 lives at `ticker=QQQQ`. The `4124`-day measurement count for QQQ reflects this; for
  the eval purposes 16y is ample. Add a QQQQ alias to `setup/data_stage.py` if you need it.
- **IBIT IV coverage ≈ 54%** — expected hard case (BTC-spot ETF launched 2024-01; options
  history is shorter than its minute bars).
- **Embargo + purge are per-horizon** — the embargo gap between train_end and test_start is
  `h + EMBARGO_EXTRA` trading days, so longer horizons necessarily consume more training data
  near each refit boundary. The `test_walkforward.py` assertion locks this.
