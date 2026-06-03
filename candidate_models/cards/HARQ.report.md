# HARQ — Modeling Report

**Identity.** Model 4 · class `candidate_models.harq:HARQ` (name `HARQ`) · Tier: Modern HAR (quarticity-corrected).

## Overview

HARQ is plain log-OLS HAR with one extra regressor: the square-root of realized quarticity (`sqrt_rq`). The single idea it adds over HAR is *measurement-error correction*. The daily RV component of a HAR is a noisy estimate of true integrated variance, and the magnitude of that noise is itself time-varying — large on turbulent days, small on calm ones. Realized quarticity is the canonical proxy for that noise magnitude, so feeding `sqrt_rq` into the regression lets the model down-weight (attenuate) the daily lag exactly when it is least reliable.

## Modeling approach & rationale

HARQ keeps Corsi's (2009) heterogeneous daily/weekly/monthly log-RV skeleton and augments it with the realized-quarticity term of Bollerslev, Patton & Quaedvlieg (2016). Their insight is an errors-in-variables argument: RV measures integrated variance with sampling error whose variance scales with integrated quarticity. A standard HAR ignores this and over-trusts the daily lag on days when RV is most error-laden — typically high-volatility days, where the noise is worst. By interacting/adjoining a quarticity term, HARQ effectively shrinks the daily coefficient toward zero when measurement error is large and lets it run when RV is precise, producing a forecast that is more responsive in calm periods and more robust to one-off measurement spikes. In this harness the term enters additively as `sqrt_rq` (square root keeps it in the same units as the variance components and stabilizes the heavy-tailed quarticity). It is still a single linear log-OLS — the same estimator and lognormal back-transform as HAR — so any improvement is attributable to the quarticity information, not a more flexible functional form.

## Features & inputs

`HARQ_FEATURES` = `HAR_FEATURES + ["sqrt_rq"]` = `log_rv_d`, `log_rv_w`, `log_rv_m`, `sqrt_rq` — four regressors plus an intercept. The first three are the Corsi HAR components (trailing day/week/month log-RV roll-means). `sqrt_rq = sqrt(clip(rq, 0))` is the measurement-noise proxy described above. All four are point-in-time columns built in `features.py`; the model adds nothing of its own.

## Design & implementation

HARQ subclasses `_LinearLogHAR` and sets only `name = "HARQ"` and `needs = HARQ_FEATURES`. Per `(ticker, horizon)` it runs a direct-h OLS of `log(target_var)` on the four regressors + intercept via `numpy.linalg.lstsq`, storing `beta` and the residual log-sd `s` (`ddof = n_params`, `min_obs = 100`). At predict time `mu = design @ beta`, `m = exp(mu + ½ s²)` is the lognormal-mean forecast (`rv_hat`), `sigma = m·sqrt(expm1(s²))`, and quantiles come from `_lognormal_quantiles(m, s)`. **No free hyperparameters** — deterministic log-OLS, identical machinery to the benchmarks so it is comparable on equal footing. Rows where any feature is null propagate NaN through the design matrix and are dropped, never imputed.

## Self-only results interpretation

**QLIKE across horizons.** On clean_core, pooled QLIKE is 0.3177 / 0.2102 / 0.2256 / 0.3226 / 0.4200 at h = 1 / 5 / 10 / 22 / 42. The curve has the familiar HAR-family shape: lowest at h=5, rising into the long horizons. Headline **QLIKE@h22 = 0.3226** (hard_cases 0.2996). On hard_cases the curve is flatter (0.3495 → 0.3224) and actually improves with horizon.

**Calibration / coverage.** Well calibrated on clean_core: at h=22 cov50 = 0.5644 and cov90 = 0.9160, both close to nominal (the 90% band is slightly conservative). Hard_cases coverage at h=22 is a touch under nominal (cov50 = 0.4867, cov90 = 0.8662), dragged by the thin tickers.

**Conditional bias.** A consistent mild *under*-forecast that shrinks toward zero as IV rises. At h=22 (clean_core) log_bias by IV-percentile bucket is −0.2210 / −0.2078 / −0.1647 / −0.1296 / −0.0948 (buckets 0→4) — the model is most under-confident in the lowest-IV regime and best-calibrated in the highest. Hard_cases mirrors this (−0.2487 → −0.0265).

**Post-shock behavior.** At h=22 bias_all = −0.1641 vs bias_postshock = −0.2509 (n=3,986, clean_core): the under-forecast worsens in the 5 days after a vol spike, though the **trap flag does NOT fire**. Hard_cases shows the same direction but milder (−0.1395 → −0.1914).

**Across tickers (h=22, clean_core).** Strongest on GLD (0.1801), TLT (0.2094), EEM (0.2329), XLE (0.2784). The clear weak spot is **HYG (0.6585)** — the highest per-ticker QLIKE, with a large negative bias (−0.6435) reflecting HYG's spike-prone credit-stress dynamics. SPY (0.4328) is the next weakest. On hard_cases, UVXY (0.3317) and KRE (0.3426) are weakest; IBIT (0.2125) is nominally low but on a small n=517 sample.

**IV-incremental skill.** At h=22 `qlike_gain_vs_iv = +0.0155` (clean_core) — HARQ beats IV-as-forecast at the primary horizon — and the gain grows at h=42 (+0.0462). At the short horizons it is roughly even with or slightly behind IV (−0.0025 at h=5, −0.0076 at h=10), where fresh option information is hardest to beat with variance-path features alone. Sign-accuracy is 0.63 at h=1, fading toward 0.5 at the long horizons.

## Coverage & limitations

- **Full coverage on all 10 clean_core tickers**, 105,450 OOS rows (≈2,087 per ticker × 5 horizons), span 2018-01-02 … 2026-05-22. No cells dropped; `min_obs=100` never tripped.
- **Hard_cases data-starvation is a history effect, not a model drop.** All 5 tickers cover all 5 horizons (40,810 rows total), but IBIT (~2,713 rows total, 517 at h=22) and MSOS (~6,462 rows, 1,270 at h=22) have short histories. IBIT's interval coverage at h=22 is poor (cov90 = 0.7176) on its thin sample.
- Because HARQ uses no IV features, it does **not** lose rows to IV nulls — its support is the full variance-path support, identical to HAR/HAR-RS and broader than the IV-using models. This is the key thing the comparison's common-support join must account for.

## Reproduction

```bash
.venv/bin/python -m rv_eval.walkforward --model candidate_models.harq:HARQ --universe clean_core
.venv/bin/python -m rv_eval.walkforward --model candidate_models.harq:HARQ --universe hard_cases
.venv/bin/python -m rv_eval.selfstats --pred execution/data/predictions/HARQ.parquet --out candidate_models/cards/HARQ.md --universe clean_core
.venv/bin/python -m rv_eval.selfstats --pred execution/data/predictions/HARQ.parquet --out candidate_models/cards/HARQ.hard_cases.md --universe hard_cases
```
