# HAR-X — Modeling Report

**Identity.** Model 3 · class `rv_eval.model_contract:HARX` (name `HAR-X`) · Tier: Baseline (modern-HAR extension with IV/VIX exogenous regressors).

## Overview

HAR-X is HAR augmented with **exogenous option-implied information**: the same daily/weekly/monthly variance components, plus implied-volatility and VIX-complex regressors. The idea it encodes: the options market is forward-looking, so its implied volatility and surface shape carry information about future realized variance that the variance path alone does not. HAR-X tests whether bolting IV onto the HAR backbone improves the forecast.

## Modeling approach & rationale

HAR-X keeps Corsi's (2009) HAR skeleton — the heterogeneous daily/weekly/monthly log-RV components that reproduce volatility's long memory — and adds option-implied covariates as extra linear regressors. The rationale is that implied volatility is the market's risk-neutral forecast of future variance and empirically leads realized variance, so a model that conditions on `log_iv`, the IV term-structure slope, skew, and the VIX/VIX3M/VVIX complex should sharpen the HAR forecast, particularly at the option-relevant ~30-day (h=22) horizon. It remains a plain linear log-OLS — the same estimator and back-transform as HAR — so any improvement is attributable to the information in the regressors, not to a more flexible functional form. The cost is data dependence: rows where IV features are missing cannot be used.

## Features & inputs

`HAR_FEATURES + IV_FEATURES` = `log_rv_d`, `log_rv_w`, `log_rv_m`, `log_iv`, `iv_slope`, `skew_25d`, `vix`, `vix3m`, `vix_slope`, `vvix` — 10 regressors plus an intercept. The first three are the Corsi HAR components; the remaining seven are the option-implied / VIX-complex covariates. All are point-in-time from `features.py`.

## Design & implementation

HAR-X subclasses `_LinearLogHAR` (`needs = HAR_FEATURES + IV_FEATURES`, `min_obs = 100`). Per `(ticker, horizon)` it runs a direct-h OLS of `log(target_var)` on the 10 regressors + intercept (`numpy.linalg.lstsq`), storing `beta` and the residual log-sd `s`. At predict time `mu = design @ beta`, `m = exp(mu + ½ s²)` (lognormal mean), `sigma = m · sqrt(expm1(s²))`, quantiles via `_lognormal_quantiles(m, s)`. **No free hyperparameters** — deterministic log-OLS. Crucially, the design matrix carries NaN wherever any IV feature is null, so those predictions are non-finite and **dropped, never imputed** — this is why HAR-X's coverage differs from HAR's.

## Self-only results interpretation

**QLIKE across horizons.** On clean_core, pooled QLIKE is 0.2818 / 0.1795 / 0.2020 / 0.3386 / 0.4587 at h = 1 / 5 / 10 / 22 / 42 — lower than HAR at the short/medium horizons (h=1/5/10), with the IV regressors helping most where the option signal is freshest. Headline **QLIKE@h22 = 0.3386** (hard_cases 0.2839). On hard_cases the curve is flat and low (0.3038 → 0.3233).

**Calibration / coverage.** Well calibrated on clean_core: at h=22 cov50 = 0.5648, cov90 = 0.9175 (near nominal). On hard_cases the *aggregate* coverage is fine (cov50 = 0.4757, cov90 = 0.8524) but it is dragged down by the thin tickers (see below).

**Conditional bias.** HAR-X has the mildest IV-bucket bias of the four benchmarks: at h=22, log_bias is −0.1391 / −0.1559 / −0.1146 / −0.0851 / −0.0320 (buckets 0→4) — a gentle under-forecast that shrinks toward zero in high-IV regimes, the same favorable slope as HAR but smaller in magnitude. The IV regressors pull the high-vol forecasts up. Hard_cases biases are smaller still (−0.10 → −0.04).

**Post-shock behavior.** Best of the benchmarks here: at h=22 bias_all = −0.1029 and bias_postshock = −0.0588 (n=3,914) — the post-shock bias is actually *smaller* than the unconditional bias, and the **trap flag does NOT fire**. Conditioning on the (elevated) IV after a shock keeps the forecast appropriately high. Hard_cases: bias_postshock −0.0665, no trap flag.

**Across tickers (h=22, clean_core).** Strong on GLD (0.1417), TLT (0.2061), EEM (0.2467), XLE (0.2744). As with HAR the weak spot is **HYG (0.8198)** — its highest per-ticker QLIKE — though the bias (−0.3668) is less extreme than HAR's on HYG. SPY (0.4459) is the next weakest. On hard_cases, UVXY (0.3212) and KRE (0.3452) are weakest; IBIT (0.1511) is nominally best but on a tiny n=224 sample.

**IV-incremental skill.** At h=22 `qlike_gain_vs_iv = +0.0012` (clean_core) — about even with IV-as-forecast at the primary horizon — but clearly positive at the short horizons (+0.0455 at h=1, +0.0283 at h=5), where combining IV with the variance path beats either alone. Sign-accuracy at h=1 is 0.70 (clean_core) / 0.74 (hard_cases), the highest of the benchmarks.

## Coverage & limitations

- **Full coverage on all 10 clean_core tickers** (~2,059–2,080 OOS rows × 5 horizons), losing only ~27–30 warmup rows per ticker to the HAR rolling-window + IV-NaN OOS boundary. Combined parquet 142,497 rows — fewer than HAR because of dropped IV-null rows.
- **IBIT is severely data-starved** (BTC ETF, ~2y options coverage): only ~266 OOS rows at h=1 shrinking to ~224 at h=22; `log_iv`/`iv_slope`/`skew_25d` are null on 313 of 686 OOS feature rows, all dropped. On the resulting thin sample interval coverage at h=22 is poor (cov90 = 0.50, cov50 = 0.25) — flagged for the comparison reader.
- **MSOS is thin** (cannabis ETF): ~1,181–1,202 OOS rows at h=22, with `log_iv` null on 100 of 1,437 feature rows (dropped). It shows a *positive* log_bias (+0.196 at h=22, the only meaningfully positive bias among these tickers) and weak coverage (cov90 = 0.70).
- General limitation: HAR-X cannot forecast where IV inputs are missing — entire rows are excluded from fit and predict, no imputation anywhere. This makes its support narrower than the variance-only benchmarks (RW/EWMA/HAR) and is the key thing the comparison's common-support join must account for.

## Reproduction

```bash
.venv/bin/python -m rv_eval.walkforward --model rv_eval.model_contract:HARX --universe clean_core
.venv/bin/python -m rv_eval.walkforward --model rv_eval.model_contract:HARX --universe hard_cases
.venv/bin/python -m rv_eval.selfstats --pred execution/data/predictions/HAR-X.parquet --out candidate_models/cards/HAR-X.md --universe clean_core
.venv/bin/python -m rv_eval.selfstats --pred execution/data/predictions/HAR-X.parquet --out candidate_models/cards/HAR-X.hard_cases.md --universe hard_cases
```
