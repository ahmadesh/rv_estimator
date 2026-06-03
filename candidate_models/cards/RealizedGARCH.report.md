# RealizedGARCH — Modeling Report

**Model number:** 8 · **Class:** `candidate_models.realized_garch:RealizedGARCH` · **Tier:** GARCH

## Overview

RealizedGARCH is the log/log Realized GARCH(1,1) model of Hansen, Huang & Shek
(2012), fit per `(ticker, horizon)` by joint maximum likelihood. Its core idea is
to let the daily conditional variance react to a *realized measure* of variance
(the intraday realized variance `rv_d`) rather than only to squared daily returns,
as a plain GARCH would. A measurement equation ties that realized measure back to
the latent conditional variance and carries an asymmetric leverage term, so the
model couples the daily return process and the realized-variance process into one
estimable system. Multi-step horizon forecasts are produced by Monte-Carlo
bootstrapping the joint recursion forward and summing the simulated daily
variances. When the joint MLE fails to converge it falls back to a plain Gaussian
GARCH(1,1).

## Modeling approach & rationale

The model implements the "RealGARCH(1,1)" log/log specification of
**Hansen, Huang & Shek (2012)** (MODEL_PLAN §9 reference; §4 model 8):

- return equation:      `r_t = sqrt(h_t) * z_t`,  `z_t ~ N(0,1)`
- GARCH equation:       `log h_t = omega + beta*log h_{t-1} + gamma*log x_{t-1}`
- measurement equation: `log x_t = xi + phi*log h_t + tau(z_t) + u_t`,  `u_t ~ N(0, su2)`
- leverage function:    `tau(z) = tau1*z + tau2*(z^2 - 1)`

where `r_t` is the daily close-to-close return (`ret_cc`, the plan's `ret_close`)
and `x_t` is the realized measure of daily variance (`rv_d` = `total_rv`, in the
same units as `r_t^2`). The eight parameters
`theta = (omega, beta, gamma, xi, phi, tau1, tau2, su2)` are estimated jointly by
maximizing the HHS joint log-likelihood (eq. 2.7):

    L = -1/2 * sum_t [ log h_t + r_t^2/h_t + log su2 + u_t^2/su2 ]

Why this should help RV forecasting: a standard GARCH learns the conditional
variance only from past *squared returns*, a noisy one-observation-per-day proxy.
By putting the realized measure `log x_{t-1}` on the right-hand side of the GARCH
recursion (the `gamma` term) and closing the loop with a measurement equation,
R-GARCH lets the much more informative intraday realized variance drive the
variance dynamics, while the leverage function `tau(z)` captures the asymmetric
volatility response to negative return shocks. This is the whole point of HHS
(2012) and is the reason the model belongs in the GARCH tier as the realized-measure
generalization of GARCH.

There is no clean closed form for the multi-step variance of a log/log Realized
GARCH, so for horizon `h` the model **Monte-Carlo bootstraps ~1000 paths** of the
joint `(log h, log x)` recursion `h` steps forward, drawing `z ~ N(0,1)` and
`u ~ N(0, su2)` at each step, and sums the simulated daily conditional variances:

    rv_hat = E[ sum_{s=t+1..t+h} h_s ]      (target_var units: sum of next-h daily RVs)
    sigma  = std( log( sum_s h_s ) )         (log-std of the simulated horizon sums)

**Robustness / fallback.** `omega` is floored at a small positive value for
numerical stability. If the joint MLE fails to converge or is degenerate for a
`(ticker, horizon)`, the model falls back to a plain Gaussian **GARCH(1,1)** on
returns (via the `arch` library) and records the fallback. If even the fallback
fails, that key is dropped (never imputed) — `predict` simply yields no row for it.

## Features & inputs

Two columns from the inputs panel:

- `ret_cc` — daily close-to-close return (the plan's `ret_close`); used as `r_t`.
- `rv_d` — daily realized measure of variance (= `total_rv`); used as `x_t`.

Returns are coerced to finite (NaN→0); the realized measure is floored above zero
(`_H_FLOOR = 1e-12`) before any log. No HAR/IV features are used — R-GARCH is a
pure return + realized-measure model.

## Design & implementation

- **Estimation:** per-`(ticker, horizon)` joint MLE of the eight R-GARCH parameters
  via `scipy.optimize.minimize`, method `L-BFGS-B`, `maxiter=500`, with bounded
  parameters (`beta ∈ [0, 0.9999]`, `gamma ∈ [0, 2]`, `phi ∈ [0.01, 3]`,
  `su2 ∈ [1e-6, 10]`, etc.). Initialization: persistent variance, measurement ≈
  identity, mild leverage.
- **omega floor:** `_OMEGA_FLOOR = 1e-8`, applied as
  `theta[0] = max(theta[0], log(1e-8))` in log-variance space; the GARCH(1,1)
  fallback omega is floored at `1e-8` directly. Conditional-variance / realized-
  measure floor before log: `_H_FLOOR = 1e-12`.
- **Horizon forecast:** 1000 Monte-Carlo paths (`_N_PATHS = 1000`) of the joint
  recursion; `rv_hat` is the mean of the simulated horizon sums and
  `sigma = std(log(horizon sums))`, clipped to `[1e-3, 5.0]`.
- **Seeding:** numpy seed fixed to 0 (`np.random.default_rng(0)`, re-seeded per
  predict call) so forecasts are reproducible.
- **Fallback policy:** R-GARCH MLE → plain Gaussian GARCH(1,1) (`arch.univariate.
  arch_model`, `mean="Zero"`, `vol="GARCH"`, `p=1`, `q=1`, `dist="normal"`,
  returns scaled by 100 for conditioning) → drop. The GARCH(1,1) fallback uses the
  same MC bootstrap on its standard variance recursion to keep one code path and a
  consistent `sigma`. `min_obs = 100`.
- **Library versions:** arch 8.0.0; scipy.optimize (L-BFGS-B); numpy; polars.
- **Device:** cpu.

## Hyperparameters & selection

R-GARCH has **no tunable hyperparameters** — all eight parameters are obtained per
`(ticker, horizon)` by maximum likelihood, not by a validation-block grid search.
There is therefore no tune-once-then-freeze step (MODEL_PLAN §4 table confirms
"none (params via MLE)" for model 8). The only fixed, non-estimated quantities are
numerical safeguards and reproducibility settings: the `omega` floor (`1e-8`), the
variance/measure floor (`_H_FLOOR = 1e-12`), the 1000-path MC count, the
`sigma` clip `[1e-3, 5.0]`, the numpy seed 0, and `min_obs = 100`. These were not
selected against any OOS or validation block.

## Self-only results interpretation

All numbers below are this model's own OOS self-stats, read from
`RealizedGARCH.md` (clean_core) and `RealizedGARCH.hard_cases.md`. They describe
the model in isolation — no ranking against other models.

**QLIKE across horizons (pooled).** QLIKE degrades sharply with horizon:

| horizon | QLIKE clean_core | QLIKE hard_cases |
|---|---|---|
| 1  | 0.757 | 0.594 |
| 5  | 1.385 | 1.055 |
| 10 | 2.557 | 2.020 |
| 22 | **5.102** | **3.900** |
| 42 | 8.200 | 5.675 |

The **headline QLIKE@h22 is 5.102 (clean_core) / 3.900 (hard_cases)**. The strong
horizon dependence, together with a large and increasingly negative `log_bias`
(−1.19 at h=1 rising to −5.72 at h=22 and −8.44 at h=42 on clean_core), is the
defining feature of this model's behavior: forecasts are severely biased *low* at
the longer horizons. The pinball loss at h=22/h=42 explodes (8.96e6 and ~9.8e15 on
clean_core), consistent with the back-transformed level forecasts being far too
small and the lognormal intervals collapsing. This is a multi-step Monte-Carlo
artifact of the log/log recursion: simulated horizon sums sit well below the
realized horizon variance, so the level forecast `rv_hat` is systematically
undersized.

**§5 IV-incremental skill (h=22).** The model adds **no** incremental skill over
the IV-as-forecast benchmark: `qlike_gain_vs_iv = −4.77` (clean_core) / −3.62
(hard_cases) at h=22 — strongly negative at every horizon. The regression slope of
truth on the model forecast is essentially zero at long horizons
(slope ≈ 0.000, t ≈ 0 at h=22/42 on clean_core), and directional sign-accuracy is
below 0.40 throughout. In short, R-GARCH's long-horizon forecasts carry little
usable signal relative to implied volatility here.

**§6 conditional bias by IV bucket (h=22).** The low bias is present in every IV
percentile bucket. On clean_core `log_bias` runs from −5.69 (lowest IV bucket) to
−5.47 (highest), QLIKE 4.88→5.12; on hard_cases the bias is somewhat milder and
*improves* with IV level (−5.21 in bucket 0 to −4.35 in bucket 4, QLIKE
4.22→3.37). The model is uniformly under-forecasting regardless of the implied-vol
regime.

**§6 post-shock calibration (h=22).** Post-shock the negative bias narrows slightly
(clean_core −5.72→−5.53; hard_cases −4.89→−4.51) while QLIKE rises modestly
(clean_core 5.10→5.31; hard_cases 3.90→3.53). No post-shock "trap" flag fired on
clean_core; the hard_cases card does not flag a trap for R-GARCH either.

**Interval coverage (h=22).** Coverage is badly miscalibrated, the natural
consequence of the level bias. On clean_core, 90% coverage is 0.053 and 50%
coverage 0.022 (target 0.90 / 0.50); several tickers (GLD, IWM, QQQ, TLT) show
~0.00 coverage. The one exception is **HYG**, where cov90 = 0.458 / cov50 = 0.193
and `log_bias` is only −1.99 — by far the best-behaved key, suggesting HYG's
fit (or its fallback) produced far more reasonable horizon paths. On hard_cases,
h=22 cov90 is 0.011 and falls to 0.000 at h=42.

**Strong vs weak tickers/horizons.** The model is least bad at **h=1** (QLIKE 0.76
/ 0.59) where the level bias is smallest and coverage least relevant, and on
**HYG** at h=22. It is weakest at the long horizons (h=22, h=42) across nearly all
tickers, where the negative bias and interval collapse dominate. Among hard cases,
**UVXY** has the lowest h=22 QLIKE (2.99) and **KRE** the highest (4.69).

## Coverage & limitations

- **Full key coverage, no drops.** Per the cards, the predictions parquet has
  146,448 OOS rows covering all 15 scored tickers × 5 horizons {1,5,10,22,42}, with
  every `rv_hat` finite and > 0. No `(ticker, horizon)` was dropped — every key
  converged under either the full R-GARCH MLE or the GARCH(1,1) fallback.
- **Fallback split not recoverable.** The model records the chosen variant
  (`"rgarch"`, `"fallback: GARCH(1,1)"`, or `"dropped"`) per key on
  `self.warnings`, but that per-key split is *not* recoverable from the predictions
  parquet alone, and the card workers did not reconstruct it (doing so would require
  re-running the walk-forward, which is out of scope). So while no key was dropped,
  the exact count of R-GARCH vs GARCH(1,1) fallbacks is unknown from the artifacts.
- **Thin hard cases.** IBIT and MSOS have shorter histories and thus reduced h=22
  support (IBIT n=537, MSOS n=1270 at h=22 on hard_cases) versus the ~2087-row
  full-history tickers.
- **Long-horizon level bias is the dominant limitation.** The systematic
  under-forecasting at h≥10 (large negative `log_bias`, near-zero coverage, and
  exploding pinball loss at h=22/h=42) means the long-horizon point and interval
  forecasts are not trustworthy in isolation; the MC horizon sums sit well below
  realized horizon variance. This is the key anomaly a downstream reader should
  know about.

## Reproduction

```bash
.venv/bin/python -m rv_eval.walkforward --model candidate_models.realized_garch:RealizedGARCH --universe clean_core
.venv/bin/python -m rv_eval.walkforward --model candidate_models.realized_garch:RealizedGARCH --universe hard_cases
.venv/bin/python -m rv_eval.selfstats --pred execution/data/predictions/RealizedGARCH.parquet \
    --out candidate_models/cards/RealizedGARCH.md --universe clean_core
.venv/bin/python -m rv_eval.selfstats --pred execution/data/predictions/RealizedGARCH.parquet \
    --out candidate_models/cards/RealizedGARCH.hard_cases.md --universe hard_cases
```
