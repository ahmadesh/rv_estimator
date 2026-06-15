# Put-Credit-Spread Backtest (v2 lean-core, self-contained)

Tier-3 trade engine for `plan_docs/PUT_SPREAD_STRATEGY_DESIGN_v2.md`. Runs the **headline economic
book**: a defined-risk short-variance put-credit spread (0.25Δ short / 0.10Δ wing, ~30 DTE) on the
10 core ETFs, gated by the 4-signal lean core, sized by inverse-risk fractional Kelly with VRP as a
tilt, **held to expiry**, 2007 → 2026.

This package imports **nothing** from the repo-root `rv_eval` / `trade_eval` / `stage2_trade_eval`
engines — every piece of option mechanics it needs is ported here, so the whole backtest runs
entirely from `strategy_backtest/`.

## Run

```bash
.venv/bin/python -m strategy_backtest.backtest.run
```

Writes to `strategy_backtest/results/`:

| Artifact | Contents |
|---|---|
| `trades.csv` | every placed trade — strikes, credit, width, max-loss, sizing units, contracts, entry/settlement spot, breach flag, gross/cost/net P&L |
| `daily_pnl.csv` | daily realized P&L, cumulative P&L, equity (= NAV + cum P&L) |
| `equity_curve.png` | equity + drawdown (%-NAV) timeseries — the P&L visualization |
| `pnl_breakdown.png` | P&L by ticker, by correlation group, and annual returns |
| `strategy_report.md` | headline metrics, capital deployment, power CIs, segment/ticker/group/annual/stress panels, disclosed biases |

## Inputs (all already cached under `strategy_backtest/`)

- `data/inputs.parquet`, `data/targets.parquet` — PIT regime columns + implied variance (2003→).
- `data/predictions/EnsembleTopK.parquet` — leakage-safe walk-forward forecasts (`rv_hat`, `sigma`), first fold ~2010.
- `back-test-data/orats/ticker=<T>/year=<Y>/data.parquet` — raw ORATS EOD chains (2007→) for fills + settlement.

## Two segments (design §2.2)

- **degraded (2007 → 2010-01-04)** — no forecaster: `rv_hat` = trailing-22d realized variance,
  IV-only inverse-risk sizing (`disp = iv_30d / IV_REF`), gate G4 (dispersion) dropped. The GFC
  co-equal stress test.
- **forecaster (≥ 2010-01-04)** — full EnsembleTopK, full lean-core gate (G2 IVrank ≤ 0.85 · G3
  contango · G4 dispersion ≤ trailing-80th-pct · G7 liquidity/credit).

## Module map

`config` knobs · `pit` PIT trailing stats (IVrank, dispersion pct, trailing RV) · `panel` builds the
roll-date candidate frame for both segments · `signals` the lean-core gate + Kelly sizing units ·
`chains` ORATS access · `structures` the put-credit spread · `marks` fills + intrinsic settlement +
G7 liquidity/credit filters · `sizing` units → dollar risk → contracts + group-margin cap ·
`engine` per-trade open/size/settle → ledger · `portfolio` daily P&L + equity · `scoring` metrics +
block-bootstrap CIs · `report` CSV + charts + markdown · `run` orchestrator.

## Deviations from the v2 doc (resolved with the user, 2026-06-08)

The doc's G7 thresholds are infeasible with its own 0.25Δ/0.10Δ strike choice, so two were relaxed
(see `config.py`): **credit/width floor 0.20 → 0.10** (a 0.25/0.10 spread structurally yields ≈ 0.11,
so 0.20 rejected ~99.9% of trades), and **per-leg OI: short ≥ 50, wing ≥ 10** (the 10Δ wing is the
thinnest leg, doc §8.4). Everything else follows the v2 defaults verbatim.

## Forecaster verification

Before trusting the book, verify the EnsembleTopK forecasts it consumes against
`plan_docs/ENSEMBLETOPK_PRODUCTION_GUIDE.md`:

```bash
.venv/bin/python -m strategy_backtest.experiments.verify_ensemble_topk   # -> results/ensemble_verification.md
```

It independently re-derives (plain numpy) every regressor, each component's per-(ticker,horizon)
log-OLS, and the combiner, and asserts the cached parquets match to ~1e-6 — **Tier-1 (implementation
correctness) is all-pass / bit-exact**. Tier-2 reproduces the guide's qualitative conclusions on our
window (QLIKE U-shape, cov90≈0.93, coin-flip sign_acc, tie-set point accuracy). Two findings it
surfaces: (a) on the 2010+ universe the forecaster *over*-predicts RV (median log bias +0.27, vs the
guide's crisis-weighted −0.10/−0.17) — the upstream cause of the book's mostly-negative VRP and
floored sizing; (b) the level-space mean is contaminated on exactly 1/40,913 h=22 keys (QQQ
2015-08-24, a HARQ quarticity spike) which is not a trade date, so the book is unaffected.

## Note on the headline numbers

The cached EnsembleTopK has median dispersion ≈ 0.62 (vs the doc's assumed 0.30) and frequently
negative raw VRP, so the actual median sizing unit `u ≈ 0.06` — ~7× below the doc's assumed 0.33. At
$2M NAV the book therefore **deploys < 0.1 % of NAV on average** and rounds most equity-name trades
to 0–1 contracts (the "granularity tax", §7.3). Returns as %-NAV are correspondingly small despite an
83 % win rate; see report §2. A deployment-calibrated variant would raise `RISK_BUDGET` or normalize
`u_med→1`, or run `ROUND_TO_CONTRACTS=False` for the NAV-independent attribution book.
