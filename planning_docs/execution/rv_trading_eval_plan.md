# VRP Trading — Evaluation Plan

**Status:** design spec (no code yet). The **downstream, economic** half of the
evaluation. It consumes a *frozen* forecasting model that has already cleared
[`rv_forecasting_eval_plan.md`](rv_forecasting_eval_plan.md) as a **Research candidate**,
and decides whether it earns **Production candidate** status.

> **Principle — this doc does NOT gate forecasting iteration.** Models are iterated and
> compared on forecast merit alone (the forecasting doc). A model is **never rejected**
> here for poor monetization under the first strategy abstraction. Trading evaluation
> confirms that a forecasting improvement survives a real strategy after costs and
> tails; it does not redefine what "a better forecast" means.

---

## 0. What this layer answers

Given a frozen forecaster emitting the §1 outputs of the forecasting doc (point RV,
quantiles, uncertainty, gap/intraday split, IV-spread), does **using it** change trading
decisions vs an **IV-only** benchmark in a way that is **+EV after costs and tail risk**
on the VRP / short-put book over the 15-group universe in
[`universe.yml`](../data_ingestion/data_download_universe/universe.yml)?

---

## 1. Strategy-layer signals (derived from forecasting outputs)

These are **strategy decisions**, not RV forecasts — defined and evaluated here only:

| Signal | Derived from | Evaluated by |
|---|---|---|
| **Regime state** `{trade, reduce, avoid}` | forecast + uncertainty + macro state | does gating cut tail loss (§5)? does `avoid` precede RV spikes / high forecast error? |
| **Position size** | `σ̂_forecast` (uncertainty) | risk-adjusted P&L vs flat sizing; calibration (do high-uncertainty trades show wider realized P&L dispersion?) |
| **Structure selection** | IV-spread + group type | per-group structure map (§2) |

## 2. Trade abstraction (parameterized, swappable)

`universe.yml` cites a `vrp/strategy_summary.md` not in the repo, so the evaluator
defines its own swappable model:

```
forecast → conditional-VRP score → regime gate → size → structure → P&L
```

**Structure map** (from universe.yml hints): index/equity/sector → short put / put
spread / iron fly; trending (GLD/TLT/USO/EWZ) → one-sided or delta-hedged;
structural-decay long-vol (VXX/UVXY/UVIX/UNG) → **call-wing only**; defensives
(XLU/XLP) → small size. **One open position per group** across the 15 groups.

All thresholds, DTE, and structures are **config**, so a real strategy doc can replace
the defaults without touching the evaluator.

## 3. Two-stage backtest

- **Stage 1 — variance proxy:** P&L ≈ `notional × (IV² − RV_realized²)`, signal-sized,
  net of a cost haircut. Fast; ranks frozen models; exercises regime gate + sizing.
- **Stage 2 — full ORATS:** real structures from ORATS strikes/greeks/IV, EOD marks,
  bid-ask + slippage + commissions, managed exits. Stage-1 survivors only.

## 4. Benchmarks & attribution

Benchmarks: **IV-only** (sell when IV > trailing RV), always-sell, HAR-only, and a
**random-entry control**. **Ablation attribution:** drop regime gate / drop sizing /
swap forecast for IV-only — measure each signal's marginal contribution.

## 5. Economic metrics

Annualized return, Sharpe, Sortino, **deflated Sharpe** (multiple-testing aware), max
drawdown, **CVaR / worst-day**, tail-loss distribution, hit rate, avg win/loss,
turnover, capacity. Significance on the P&L series via DM / Hansen **SPA** + block
bootstrap.

> Short-vol P&L is short-gamma, negatively skewed — plain Sharpe flatters it. Deflated
> Sharpe + CVaR + tail-loss distribution are **mandatory**.

## 6. Portfolio-level stress / correlation

One-per-group × 15 groups *looks* diversified, but cross-group correlation collapses to
~1 in stress. Evaluate the whole book on its worst ~20 days; report realized cross-group
correlation in stress vs calm.

## 7. Promotion to Production candidate

A frozen Research-candidate forecaster becomes a **Production candidate** when it:
1. beats **IV-only** on Stage-1 **deflated Sharpe** with **not-worse CVaR**, and
2. survives **Stage-2** full ORATS on the clean-core subset (edge persists after costs).

Failing this does **not** demote the model below Research candidate — it remains a valid
forecasting improvement; it just isn't promoted for trading yet.

---

## Critical assessment & expansions

- The residual edge is small and costs can eat it → IV-only (not random walk) is the
  benchmark, and the ablation in §4 must show the forecast — not luck — drives P&L.
- Negative-skew Sharpe inflation → deflated Sharpe + CVaR + tail-loss are mandatory.
- Diversification illusion → §6.

**Staged expansions (with the eval hook each needs):** cross-sectional within-group
ranking (pick the best VRP name per group — rank-IC partly tracked in the forecasting
doc §3); forward correlation / dispersion (component-vol + `ρ̂` + a dispersion P&L
module); single-name extension behind a separate selector; jump/event-risk probability
as a gate.

## Relationship to the forecasting doc

Consumes a frozen model from
[`rv_forecasting_eval_plan.md`](rv_forecasting_eval_plan.md) (Research candidate) and the
universe/data flags from
[`universe.yml`](../data_ingestion/data_download_universe/universe.yml) and
[`data_sourcing.md`](../research/data_sourcing.md). Shared OOS protocol, universe tiers,
and regime buckets are defined in the forecasting doc — this doc references them rather
than redefining them.
