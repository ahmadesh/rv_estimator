# RW — Modeling Report

**Identity.** Model 0 · class `rv_eval.model_contract:RandomWalk` (name `RW`) · Tier: Baseline (reference benchmark, the comparison floor).

## Overview

RW is the simplest scored forecaster in the sweep. It encodes a single idea: **tomorrow's variance looks like today's**. The horizon-`h` variance forecast is just today's daily realized variance scaled up by the number of days in the horizon, `rv_hat = h · rv_d`. There is no learning of dynamics, no mean reversion, and no awareness of the options market — it is pure persistence, and it exists to set the floor every other model must clear.

## Modeling approach & rationale

The random walk is the canonical naive persistence baseline for volatility. Because realized variance is strongly autocorrelated at short horizons, "use the last observation" is a genuinely hard benchmark to beat one day out, which is exactly why it belongs in the sweep: a model that cannot beat RW at `h=1` has learned nothing. The forecast aggregates today's daily variance over the horizon by summing `h` identically-distributed daily variances, i.e. multiplying the daily proxy by `h`. As the horizon lengthens, this assumption becomes progressively less defensible — variance mean-reverts, so a single recent day is a poor anchor for a month-ahead sum — and RW is expected to degrade accordingly. It carries no exogenous information (no IV, no VIX), so it is also expected to lose to IV-as-forecast at every horizon. That expected weakness is the point: RW measures how much signal lives in persistence alone.

## Features & inputs

A single feature: `rv_d` (daily total realized variance, the `total_rv` column surfaced by `build_features`). Nothing else enters the forecast.

## Design & implementation

RW subclasses `_NaiveScaled` (`min_obs = 30`). For each `(ticker, horizon)` the fit step computes the standard deviation `s` of the log-residual `log(target_var) − log(h · rv_d)` over the training window — this is the only thing "fit". At predict time the level forecast is `m = h · rv_d · exp(½ s²)`: the `exp(½ s²)` factor is a lognormal-mean correction so that `rv_hat` is the QLIKE-optimal mean forecast rather than the median (without it the naive `h · rv_d` is the median and biases QLIKE low). `sigma` is derived from the same log-sd as `m · sqrt(expm1(s²))`, and the predictive quantiles `q05…q95` come from `_lognormal_quantiles(m, s)`, treating the horizon variance as lognormal with mean `m` and log-sd `s`. **There are no free hyperparameters** — `s` is estimated from the data, not chosen, and there is no optimizer.

## Self-only results interpretation

**QLIKE across horizons.** On clean_core, pooled QLIKE is 0.4219 / 0.3540 / 0.4014 / 0.5895 / 0.7709 at h = 1 / 5 / 10 / 22 / 42. The shape is telling: RW is at its relative best around the week horizon and then degrades steadily, roughly doubling between h=5 and h=42 — exactly the persistence-decay story. The headline primary-horizon number is **QLIKE@h22 = 0.5895** (hard_cases 0.6054). The hard_cases set is broadly similar (0.4544 → 0.7006).

**Calibration / coverage.** At h=22 the intervals modestly under-cover: cov50 = 0.4869 and cov90 = 0.8779 on clean_core (cov50 = 0.4864, cov90 = 0.8643 on hard_cases) against nominal 0.50 / 0.90. The single-`s` lognormal band is a touch too tight.

**Conditional bias by IV bucket.** RW shows the classic naive mean-reversion miss: at h=22 log_bias runs +0.0814 / +0.0107 / −0.0356 / −0.1124 / −0.3243 across IV buckets 0→4. It **over-forecasts in calm regimes and under-forecasts strongly in high-IV regimes** — it cannot anticipate that elevated vol will partly revert, nor that it should be higher when the market is already stressed. The hard_cases pattern is the same (+0.1017 → −0.3246).

**Post-shock behavior.** This is RW's worst regime. At h=22 the overall bias is a mild −0.0786 but the post-shock bias is −0.4831 (n=3,986) and the post-shock trap flag fires (✓). After a vol spike RW lags the subsequent decay and under-forecasts heavily — it keeps projecting the elevated level forward. Hard_cases is even more extreme: post-shock bias −0.5533, trap flag ✓.

**Across tickers (h=22, clean_core).** Best on XLE (0.4246), TLT (0.4425), IWM (0.4863); worst on HYG (0.9493, with the strongest negative bias −0.357 and over-coverage) and SPY (0.8031). On hard_cases, UVXY is the worst (0.8235, large pinball 0.036, as expected for a leveraged VIX product) and MSOS the best (0.4287); USO is the only ticker with a positive bias (+0.072).

**IV-incremental skill.** RW carries no IV, and at h=22 `qlike_gain_vs_iv = −0.2504` (clean_core) / −0.3019 (hard_cases) — IV-as-forecast beats RW, as expected for a naive benchmark with no options awareness. The slope is small and shrinks toward zero with horizon.

## Coverage & limitations

- RW covers all 15 scored tickers at every horizon (closed-form, no convergence step). The prediction parquet holds 147,210 rows.
- **IBIT** has only ~2y of history → 620 OOS rows at h=22 (3,212 total); **MSOS** is thin → 1,353 rows at h=22. These are genuinely short series, not dropped cells — no rows imputed. Their reduced support matters for the comparison pass's common-support joins.
- Structural limitations (all expected for a persistence floor): no IV awareness (loses to IV-as-forecast at all horizons), degrades with horizon, and falls into the post-shock under-forecast trap.

## Reproduction

```bash
.venv/bin/python -m rv_eval.walkforward --model rv_eval.model_contract:RandomWalk --universe clean_core
.venv/bin/python -m rv_eval.walkforward --model rv_eval.model_contract:RandomWalk --universe hard_cases
.venv/bin/python -m rv_eval.selfstats --pred execution/data/predictions/RW.parquet --out candidate_models/cards/RW.md --universe clean_core
.venv/bin/python -m rv_eval.selfstats --pred execution/data/predictions/RW.parquet --out candidate_models/cards/RW.hard_cases.md --universe hard_cases
```
