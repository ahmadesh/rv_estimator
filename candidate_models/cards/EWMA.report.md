# EWMA — Modeling Report

**Identity.** Model 1 · class `rv_eval.model_contract:EWMA` (name `EWMA`) · Tier: Baseline (reference benchmark).

## Overview

EWMA replaces the random walk's single-day anchor with an **exponentially-weighted moving average of past daily variance**, then scales it to the horizon. The one idea it encodes: recent variance still dominates, but a smoothed, decaying blend of the recent path is a better anchor than the last observation alone. The forecast is `rv_hat = h · ewma_rv`, where `ewma_rv` is the RiskMetrics EWMA of `total_rv`.

## Modeling approach & rationale

EWMA is the RiskMetrics convention for variance: a recursive estimator `v_t = (1−α) v_{t−1} + α · rv_t` with decay parameter `λ = 0.94` (so `α = 1 − λ = 0.06`). The geometric down-weighting of older observations smooths out the day-to-day noise that a pure random walk inherits, while still tracking the level quickly enough to follow regime changes. It is a sensible RV forecaster because realized variance is persistent and clustered: weighting the recent past more heavily than the distant past captures that clustering with a single, well-understood parameter. Per MODEL_PLAN §4.1 and the §9 reference list, **λ=0.94 is the fixed RiskMetrics convention and is explicitly NOT tuned** — it is a convention, not a fitted knob. Like RW, EWMA carries no exogenous (IV/VIX) information, so it is expected to lose to IV-as-forecast; its value is showing how much smoothing alone buys over raw persistence.

## Features & inputs

A single feature: `ewma_rv` — the EWMA of `total_rv` built in `features.py` via `ewm_mean(alpha = 1 − 0.94, adjust=False)` per ticker. No other inputs.

## Design & implementation

EWMA subclasses `_NaiveScaled` (`source = "ewma_rv"`, `min_obs = 30`) — the same machinery as RW but reading the smoothed proxy. Per `(ticker, horizon)` the fit estimates the log-residual sd `s` of `log(target_var) − log(h · ewma_rv)`. The level forecast applies the lognormal-mean correction `m = h · ewma_rv · exp(½ s²)` (so `rv_hat` is the QLIKE-optimal mean, not the median), `sigma = m · sqrt(expm1(s²))`, and the quantiles come from `_lognormal_quantiles(m, s)`. **No free hyperparameters** — λ is the fixed RiskMetrics convention and `s` is estimated, not chosen; the fit is closed-form with no optimizer.

## Self-only results interpretation

**QLIKE across horizons.** On clean_core, pooled QLIKE is 0.4410 / 0.2900 / 0.2938 / 0.3841 / 0.5323 at h = 1 / 5 / 10 / 22 / 42. The smoothing helps most in the middle of the horizon range (best at h=5/10) and the curve is markedly flatter and lower than RW's at the medium horizons. Headline **QLIKE@h22 = 0.3841** (hard_cases 0.3662). Hard_cases QLIKE is 0.4748 → 0.4016 and notably *less* degrading at the long end.

**Calibration / coverage.** At h=22, cov50 = 0.5743 and cov90 = 0.8967 on clean_core — close to nominal at 90% and slightly over-covering at 50%. Hard_cases is cov50 = 0.4983, cov90 = 0.8759, near nominal.

**Conditional bias.** EWMA runs a persistent **negative** log_bias — it systematically under-forecasts. At h=22 the IV-bucket biases are roughly −0.33 across all five buckets on clean_core (−0.3291 / −0.3522 / −0.3270 / −0.3419 / −0.2937), i.e. the under-forecast is broadly level-independent rather than regime-dependent. This is the smoothing tax: the EWMA lags rising variance and the lognormal correction does not fully offset the level shortfall. Hard_cases biases are milder (~−0.21 to −0.25).

**Post-shock behavior.** At h=22 bias_all = −0.3264 and bias_postshock = −0.3523 (n=3,986) — only modestly worse post-shock, and the **trap flag does NOT fire**. Because the EWMA still carries weight on the recent spike, it does not collapse the way the random walk does after a shock. Hard_cases similarly: bias_postshock −0.3377, no trap flag.

**Across tickers (h=22, clean_core).** Best on GLD (0.1945), TLT (0.2217), EEM (0.2860); much worse on HYG (0.7952), which also shows an extreme negative bias (−1.0023) and heavy over-coverage (cov50 0.7892) — EWMA badly under-forecasts the low-but-spiky HYG variance. SPY (0.5193) is the next weakest. On hard_cases, UVXY is worst (0.5170) and IBIT best (0.2209, but only n=620).

**IV-incremental skill.** At h=22 the IV-regression slope is *negative* (−0.1109, t=−12.6) on clean_core and `qlike_gain_vs_iv = −0.0465` — IV still adds value over EWMA, though the gap is smaller than for RW. Sign-accuracy is below 0.5 at the longer horizons (~0.43), consistent with EWMA's systematic under-forecast.

## Coverage & limitations

- EWMA covers all 15 tickers × 5 horizons; `rv_hat` is 100% finite (closed-form, no optimizer). Combined parquet 147,210 rows.
- Because it needs only `ewma_rv` (no IV features), the data-starved hard cases ran without issue: **IBIT** (short options history) and **MSOS** (thin) are limited only by their own price history, not by IV availability — unlike HAR-X.
- Structural limitations: persistent negative (under-forecast) bias from the smoothing lag, especially severe on HYG; no IV awareness; sign-accuracy below 0.5 at long horizons.

## Reproduction

```bash
.venv/bin/python -m rv_eval.walkforward --model rv_eval.model_contract:EWMA --universe clean_core
.venv/bin/python -m rv_eval.walkforward --model rv_eval.model_contract:EWMA --universe hard_cases
.venv/bin/python -m rv_eval.selfstats --pred execution/data/predictions/EWMA.parquet --out candidate_models/cards/EWMA.md --universe clean_core
.venv/bin/python -m rv_eval.selfstats --pred execution/data/predictions/EWMA.parquet --out candidate_models/cards/EWMA.hard_cases.md --universe hard_cases
```
