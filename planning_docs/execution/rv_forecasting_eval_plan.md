# RV Forecasting — Evaluation Plan

**Status:** design spec (no code yet). The fixed yardstick for iterating the modeling
approaches in [`research/rv_forecasting_methods.md`](../research/rv_forecasting_methods.md).
Build the evaluator first; every candidate model is judged against it.

**Scope:** this document is **strategy-agnostic** — it evaluates forecast quality only.
The downstream VRP trading evaluation lives in a companion doc,
[`rv_trading_eval_plan.md`](rv_trading_eval_plan.md), and **does not gate iteration
here**. A model is iterated and accepted as a *Research candidate* on this document
alone; the trading doc only governs promotion to *Production candidate* (§9).

> **Revision history:** v1 combined forecasting + trading. v2 split them and decoupled
> the gates. v3 (this) made forecasting a standalone, reusable spec, and moved
> downside semivariance to a **measure-in-v1 / forecast-in-v2** scope (§1, §7).

---

## 0. Purpose & framing

We forecast **forward realized volatility**. The first consumer is a VRP / short-put
book, but nothing here is specific to it — the same forecast quality matters for
dispersion, hedging, or any other vol strategy.

### The IV framing — stated correctly
A common shortcut is "the model only has to beat IV's implicit RV forecast." That is
**misleading**: implied variance `IV²` is derived from option prices and embeds the
variance risk premium plus hedging/tail demand and supply pressure — it is *not* a
clean statistical RV forecast. So evaluate a **three-way comparison**, not "IV = the
benchmark forecast":

```
Error_model = RV_realized − R̂V_model
Error_IV    = RV_realized − IV²              (IV treated as a biased forecast)
```

and — the bridge to economics, computed with **no P&L** — the model's **incremental
skill conditional on the IV–forecast spread**:

```
does sign/magnitude of (IV² − R̂V_model)  predict  (IV² − RV_realized) ?
```

i.e. when the model says "IV is rich," is realized RV actually below IV more often / by
more than IV-alone implies? This conditional diagnostic (§5) tells us the model adds
information *beyond* IV — the single most important forecasting question for any
vol-premium strategy.

---

## 1. Model output contract

Forecast-native quantities only — per ticker, per day `t`, per horizon `h`. (Regime
state, position size, and structure selection are **strategy** decisions and live in
the trading doc.)

| # | Output | Symbol | Scope | Purpose |
|---|---|---|---|---|
| 1 | Point forward RV | `R̂V_{t,t+h}` | **v1** | core fair-vol estimate |
| 2 | Forecast quantiles | `{0.05,0.10,0.25,0.50,0.75,0.90,0.95}` | **v1** | distribution → tails |
| 3 | Forecast uncertainty | `σ̂_forecast` (predictive s.d.) | **v1** | basis for downstream sizing |
| 4 | Gap vs intraday decomposition | `R̂V_overnight`, `R̂V_intraday` | **v1** | overnight risk is a distinct driver |
| 5 | IV-vs-forecast spread | `IV² − R̂V` | **v1** | incremental-info / bridge signal |
| 6 | Downside semivariance | `R̂S−_{t,t+h}` | **v2** | downside vol (see scope note) |

**Semivariance scope (v1 vs v2):** the **measurement layer computes RS± targets in
v1** (cheap to do alongside RV/BV/RQ, and it avoids reprocessing all intraday history
later — §2). But the **RS− *forecast* and its evaluation are deferred to v2**, added as
an isolated ablation (§7) once the total-RV baseline is solid. Rationale: keep v1 lean
and prove the harness on total RV first; RS− is the most short-put-relevant feature but
also noisier to forecast, so it earns its place against a frozen baseline.

Horizon → option-DTE mapping (DTE is informational; this doc is strategy-agnostic):

| `h` | DTE | role |
|---|---|---|
| 1d | — | regime input / short-horizon sanity |
| 5d | ~7 | weekly |
| 10d | ~14 | bi-weekly |
| **22d** | **~30** | **primary** |
| 42d | ~45–60 | longer-dated |

Report all outputs in **both** annualized vol and variance; QLIKE is on variance.

## 2. Measurement layer & target validation

Targets built from intraday + daily bars (see
[`rv_forecasting_methods.md`](../research/rv_forecasting_methods.md) §2): close-to-close
RV, **5-min intraday RV**, **overnight gap RV**, **total RV** (Hansen-Lunde scaled), plus
BV / **RS±** / RQ. **RS± is measured and validated in v1** even though its forecast is a
v2 output (§1). The forward-`h` target is the **sum of the next h daily total-RVs**.

**Oxford-Man SPY validation — specified, not just "within 5%":**
- **Well-behaved day** = full regular session, no halt, ≥ 95% of expected 5-min bars
  present, not a known half-day or index-roll anomaly.
- **Half-days** handled explicitly: scale expected-bar count to the shortened session;
  don't flag as missing-data failures.
- **Missing-bar policy:** < 95% bars → mark low-confidence and exclude from the
  tolerance check (don't impute then compare).
- **Overnight consistency:** Oxford-Man RV is RTH-only — compare our **RTH RV** to it,
  not the overnight-augmented total RV. Validate the pieces separately.
- **Session/timestamp alignment:** ET, 09:30–16:00, same bar-stamp convention before
  differencing.
- **Tolerance:** ≤ 5% on well-behaved days; allow wider divergence on event/halt days
  and treat as expected.
- Document any **signed** microstructure bias (bid-ask bounce/discreteness) vs
  Oxford-Man, not only the magnitude.

## 3. Tier-1 metrics — every iteration (cheap, fast)

On the **clean core** (§8), per ticker / group / pooled, in variance and vol units:
- **QLIKE** `RV/R̂V − log(RV/R̂V) − 1` (heavy-tail-robust, primary).
- **log RMSE**, **log MAE** (a non-QLIKE second opinion).
- **Forecast bias** — unconditional and by regime.
- **Quantile coverage + pinball loss** (are 90% intervals 90% OOS?).
- **Error by regime** (IV-percentile bucket, post-shock vs quiet).
- **Error by ticker/group** (no single ticker carrying the average).
- **Cross-sectional rank correlation** within group (groundwork for picking one name
  per group; cheap to track now).

This bundle — not the heavy tests — gates day-to-day iteration.

## 4. Tier-2 battery — finalists only

- **Diebold-Mariano** (pairwise) and **Giacomini-White** conditional predictive ability.
- **Model Confidence Set** (Hansen-Lunde-Nason).
- **Newey-West / Hansen-Hodrick** SEs + **block bootstrap**.

**Caveat:** overlapping `h`-horizons make the loss differential strongly dependent,
reducing DM power and risking misleading results. Use as **confirmation** of a Tier-1
signal, never as the iteration driver.

## 5. Benchmarks & the IV comparison

Benchmarks, increasing strength: **random walk (`RV_{t-1}`)**, **EWMA**, **HAR**,
**HAR-X (IV/VIX features)**. Always report **model vs IV** (§0): `Error_model`,
`Error_IV`, and the **conditional diagnostic** — does `sign(IV² − R̂V_model)` predict
`(IV² − RV_realized)`? A model that improves QLIKE but adds nothing here is a weak
candidate for any premium strategy.

## 6. Conditional calibration — the trap to catch

A model can be unbiased on average but biased exactly when it matters. Report bias and
QLIKE conditional on: IV-percentile bucket, post-shock vs quiet, and group. Flag any
model unbiased unconditionally but biased after vol spikes.

## 7. Ablations — does each layer of complexity earn its place?

**Every added component must beat the simpler model OOS** (Tier-1, clean core) to stay.

| Added complexity | Must out-forecast | Scope | Kept only if it |
|---|---|---|---|
| IV/VIX features | HAR without IV | v1 | lowers QLIKE / improves conditional diagnostic |
| **Downside semivariance** | total-RV-only model | **v2** | improves OOS QLIKE or post-shock calibration |
| Regime conditioning | unconditional model | v1 | reduces conditional bias (§6) |
| Quantile/distribution head | point + Gaussian s.d. | v1 | improves coverage + pinball |
| ML (XGBoost, etc.) | HAR-X and ElasticNet | v2 | beats both on ≥3 unrelated tickers |
| Per-ticker calibration | pooled/panel | v2 | cuts ticker bias without overfitting |

## 8. Universe tiers

- **Clean core (build & iterate):** SPY, QQQ, IWM, XLK, XLF, XLE, TLT, GLD, HYG, EEM.
  Liquid, long history, no decay/proxy pathologies — design decisions are made here.
- **Hard cases (stress *after* the base works):** UVXY (decay), MSOS (extreme IV/thin),
  IBIT (short/proxy history), USO (futures roll), KRE (tail-prone banks).
- **SPY first** for the §2 measurement validation.

## 9. Model statuses

| Status | Meaning |
|---|---|
| **Rejected** | worse forecast accuracy or unstable calibration |
| **Research candidate** | improves ≥1 forecast target/regime without breaking others — decided on **this doc alone** |
| **Production candidate** | a Research candidate that also survives [`rv_trading_eval_plan.md`](rv_trading_eval_plan.md) |

ORATS-backtest survival is **not** required to call a forecasting improvement real.

## 10. Out-of-sample protocol

**Purged + embargoed rolling-origin** walk-forward (22d target overlaps → embargo ≥ `h`,
purge boundary overlaps). Refit weekly/monthly; evaluate next non-overlapping period.
**≥3–5y OOS spanning 2020 COVID / 2022 rates / 2025 tariff.** Point-in-time IV only;
short-history ETFs use proxy rules ([`data_sourcing.md`](../research/data_sourcing.md) §4).

---

## Critical assessment (forecasting)

- The residual edge (`IV − R̂V` beyond IV's own info) is small — hence IV-only, not
  random walk, is the bar, and §5's conditional diagnostic matters more than raw QLIKE.
- QLIKE wins needn't translate to anything economic — that's why §5 exists and why the
  trading doc is the final arbiter for Production status.
- Signed semivariance is noisier to forecast than total RV → deferring it to v2 (while
  measuring it in v1) protects iteration speed without losing the target data.

## Relationship to existing docs & build order

Operationalizes [`rv_forecasting_methods.md`](../research/rv_forecasting_methods.md) §5–6;
consumes universe/data flags from
[`universe.yml`](../data_ingestion/data_download_universe/universe.yml) and
[`data_sourcing.md`](../research/data_sourcing.md). Downstream economics:
[`rv_trading_eval_plan.md`](rv_trading_eval_plan.md).

**Build order:** measurement layer + SPY validation (§2, RS± measured) → realized targets
→ baselines (RW / EWMA / HAR / HAR-X) → Tier-1 metrics on clean core (§3) → ablations (§7)
→ finalist Tier-2 (§4) → **freeze forecasting model** (Research candidate) → hand to the
trading doc for Production candidacy. (RS− forecast added as a v2 ablation.)
