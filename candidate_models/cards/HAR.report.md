# HAR — Modeling Report

**Identity.** Model 2 · class `rv_eval.model_contract:HAR` (name `HAR`) · Tier: Baseline. **This is the §9 comparison baseline** — the anchor every other model is judged against in the downstream comparison pass.

## Overview

HAR (Heterogeneous AutoRegressive) regresses log realized variance on three trailing averages of past variance — daily, weekly, and monthly — capturing the empirical fact that volatility is driven by market participants acting on different time scales. The single idea: **a few lagged averages over heterogeneous horizons reproduce the long-memory persistence of variance with a simple linear model**. It is the workhorse RV forecaster and, in this sweep, the reference baseline.

## Modeling approach & rationale

HAR is Corsi (2009). The motivation is the Heterogeneous Market Hypothesis: short-term traders, weekly position managers, and monthly/institutional participants each respond to volatility at their own frequency, and their superimposed activity produces the slowly-decaying autocorrelation ("long memory") seen in realized variance. Corsi's insight is that you can approximate that long memory cheaply by regressing variance on just three components — a one-day lag, a one-week (5d) average, and a one-month (22d) average — instead of a high-order ARFIMA. The result is a sparse, robust, interpretable model that is famously hard to beat, which is exactly why MODEL_PLAN designates **HAR as the §9 baseline**: `status.assign()` computes its comparison baseline from the HAR row, so HAR must be in the predictions set for the comparison pass to anchor. Fitting in log space is deliberate — variance is right-skewed and multiplicative, so logs stabilize the OLS and the lognormal back-transform yields a proper mean forecast.

## Features & inputs

`HAR_FEATURES = [log_rv_d, log_rv_w, log_rv_m]` — the log of daily variance, the log of the trailing 5-day mean variance, and the log of the trailing 22-day mean variance. These are the canonical Corsi daily/weekly/monthly components, all built point-in-time (trailing windows) in `features.py`. No exogenous (IV/VIX) inputs — that is HAR-X's job.

## Design & implementation

HAR subclasses `_LinearLogHAR` (`needs = HAR_FEATURES`, `min_obs = 100`). For each `(ticker, horizon)` it runs a **direct-h** OLS of `log(target_var)` on the three HAR features plus an intercept (`numpy.linalg.lstsq`). The horizon enters only through the target (the `h`-day-ahead variance sum), so there is one fitted coefficient vector per horizon — no iterated multi-step forecasting. From the fit it stores `beta` and the residual log-sd `s`. At predict time `mu = design @ beta`, the level forecast is the lognormal mean `m = exp(mu + ½ s²)`, `sigma = m · sqrt(expm1(s²))`, and quantiles come from `_lognormal_quantiles(m, s)`. **No free hyperparameters** — plain log-OLS, deterministic, no optimizer or tuning. A null feature propagates as NaN and that prediction is dropped (never imputed).

## Self-only results interpretation

**QLIKE across horizons.** On clean_core, pooled QLIKE is 0.3198 / 0.2114 / 0.2267 / 0.3232 / 0.4204 at h = 1 / 5 / 10 / 22 / 42 — uniformly lower and flatter than the naive baselines, and best in the week-to-fortnight range. Headline **QLIKE@h22 = 0.3232** (hard_cases 0.2985). Hard_cases is remarkably stable across horizon (0.3419 → 0.3201), the flattest curve of the four benchmarks.

**Calibration / coverage.** Well calibrated on clean_core: at h=22, cov50 = 0.5644 and cov90 = 0.9156 (close to nominal, very slightly over-covering at 90%, which holds across all horizons). Hard_cases is a touch under-covered (cov50 = 0.4876, cov90 = 0.8668).

**Conditional bias.** HAR under-forecasts but more mildly than EWMA, and the bias *shrinks* as IV rises: at h=22 the IV-bucket log_bias goes −0.2187 / −0.2091 / −0.1683 / −0.1372 / −0.0977 (buckets 0→4). So HAR's worst (most negative) bias is in calm regimes and it is nearly unbiased in high-IV regimes — the opposite slope to RW. Hard_cases shows the same monotone pattern (−0.2501 → −0.0188).

**Post-shock behavior.** At h=22 bias_all = −0.1663, bias_postshock = −0.2534 (n=3,986), and the **trap flag does NOT fire**. The weekly/monthly components keep the forecast elevated after a shock, so HAR avoids the random walk's post-shock collapse, with only a modest worsening. Hard_cases: post-shock bias −0.1839, no trap flag.

**Across tickers (h=22, clean_core).** Strong on TLT (0.2094), GLD (0.1807), EEM (0.2377), most equity/sector ETFs in the 0.28–0.37 range. The clear weak spot is **HYG (0.6580)**, with a large negative bias (−0.6434) and over-coverage — HAR struggles with HYG's spiky, low-base variance, the same ticker that troubles the naive models. SPY (0.4344) is the next weakest. On hard_cases, UVXY (0.3303) and KRE (0.3425) are the weakest; IBIT (0.2168) and USO (0.2665) the strongest, though IBIT is thin (n=517).

**IV-incremental skill.** At h=22 `qlike_gain_vs_iv = +0.0149` (clean_core): HAR already roughly matches or slightly edges IV-as-forecast on its own at the primary horizon, and the gain is positive at h=1 and grows at h=42 (+0.0459). The IV-regression slope is large and highly significant at short horizons (1.18 at h=1) and decays toward 0.28 at h=22 — much of HAR's medium-horizon forecast moves with IV even without IV as an input. Hard_cases gains are mostly slightly negative (−0.03 at h=22), so IV still adds a little there.

## Coverage & limitations

- HAR covers all 15 tickers × all 5 horizons; closed-form OLS, no convergence failures, no NaN warnings. Combined parquet 146,260 rows.
- **IBIT** is data-starved (~2y options history → OOS effectively begins 2024-03; 2,713 total rows, ~517 at h=22) but all five horizons fit — data availability, not a coverage gap. **MSOS** is thin (1,270 rows at h=22).
- Limitations: persistent (if mild) under-forecast in calm regimes; pronounced weakness on HYG (low-base, spiky variance); no exogenous IV/VIX information.

## Reproduction

```bash
.venv/bin/python -m rv_eval.walkforward --model rv_eval.model_contract:HAR --universe clean_core
.venv/bin/python -m rv_eval.walkforward --model rv_eval.model_contract:HAR --universe hard_cases
.venv/bin/python -m rv_eval.selfstats --pred execution/data/predictions/HAR.parquet --out candidate_models/cards/HAR.md --universe clean_core
.venv/bin/python -m rv_eval.selfstats --pred execution/data/predictions/HAR.parquet --out candidate_models/cards/HAR.hard_cases.md --universe hard_cases
```
