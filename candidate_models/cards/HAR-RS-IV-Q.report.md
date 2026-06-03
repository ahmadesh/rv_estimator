# HAR-RS-IV-Q — Modeling Report

**Identity.** Model 7 · class `candidate_models.har_rs_iv_q:HARRSIVQ` (name `HAR-RS-IV-Q`) · Tier: Modern HAR (the research doc's recommended primary / strongest *linear* baseline).

## Overview

HAR-RS-IV-Q is the "everything cheap and informative" linear HAR: a single log-OLS that stacks the semivariance/jump decomposition, the option-implied-volatility / VIX-complex block, and the realized-quarticity attenuation term onto one HAR backbone. The single idea it adds over plain HAR is *kitchen-sink linear conditioning* — combine the three independently useful HAR extensions (directional/jump asymmetry, forward-looking IV, measurement-error correction) into the strongest forecast obtainable without leaving the linear-log-OLS family. The research doc nominates it as the primary modern-HAR model: the bar that the ML/DL/PDV candidates must clear to justify their extra complexity.

## Modeling approach & rationale

The model unions three well-motivated extensions, each citing its own literature, into one regression:

- **Semivariance + jump (Patton & Sheppard 2015):** signed realized-semivariance pieces and a jump term, so downside variation can predict future RV more strongly than upside, and transient jumps are discounted.
- **Implied-volatility / VIX complex:** option-implied volatility is the market's forward-looking risk-neutral forecast of variance and empirically leads realized variance; the IV level, term-structure slope, skew, and the VIX/VIX3M/VVIX block add information the variance path alone lacks, especially at the ~30-day (h=22) option-relevant horizon.
- **Realized quarticity (Bollerslev-Patton-Quaedvlieg 2016 HARQ):** `sqrt_rq` proxies the measurement noise of the daily RV term, attenuating it when RV is least reliable.

The bet is that these signals are complementary — semivariance/jump captures the realized-path structure, IV the forward-looking risk premium, quarticity the measurement quality — so a single OLS that conditions on all three jointly should be the best linear forecast, and a fair, hard-to-beat baseline for the nonlinear models. It remains plain log-OLS with the same estimator and lognormal back-transform as HAR; the only cost is the IV data dependence (rows with null IV features are unusable).

## Features & inputs

`needs = _dedup(HAR_RS_FEATURES + IV_FEATURES + ["sqrt_rq"])` — 14 regressors plus an intercept (no column repeats across the three groups, so the dedup helper dropped nothing; it exists only to guard against accidental duplication if the feature groups ever overlap):

- HAR + semivariance/jump block: `log_rv_d`, `log_rv_w`, `log_rv_m`, `rs_minus_5d`, `rs_plus_5d`, `jump_5d`.
- IV / VIX-complex block: `log_iv`, `iv_slope`, `skew_25d`, `vix`, `vix3m`, `vix_slope`, `vvix`.
- Quarticity attenuation: `sqrt_rq`.

All 14 are point-in-time columns built in `features.py`; the model adds nothing of its own.

## Design & implementation

HAR-RS-IV-Q subclasses `_LinearLogHAR`, setting `name` and the deduplicated `needs`. Per `(ticker, horizon)` it runs a direct-h OLS of `log(target_var)` on the 14 regressors + intercept via `numpy.linalg.lstsq`, storing `beta` and the residual log-sd `s` (`ddof = n_params`, `min_obs = 100`). At predict time `mu = design @ beta`, `m = exp(mu + ½ s²)` is the lognormal-mean forecast (`rv_hat`), `sigma = m·sqrt(expm1(s²))`, quantiles via `_lognormal_quantiles(m, s)`. **No free hyperparameters** — deterministic log-OLS, identical machinery to the benchmarks. The one model-specific detail is the `_dedup` of the concatenated feature lists (preserving first-seen order); functionally a no-op on the current feature groups but it keeps the design matrix well-conditioned if the groups are later edited to overlap. Rows where **any** of the 14 features is null propagate NaN through the design matrix and are **dropped, never imputed** — which, because of the IV block, materially narrows coverage for thin-option tickers (see below).

## Self-only results interpretation

**QLIKE across horizons.** On clean_core, pooled QLIKE is 0.2818 / 0.1813 / 0.2057 / 0.3458 / 0.4680 at h = 1 / 5 / 10 / 22 / 42 — the lowest short/medium-horizon QLIKE of the four reports here (h=1 = 0.2818, h=5 = 0.1813), where the freshly-observed IV block adds most. Headline **QLIKE@h22 = 0.3458** (hard_cases 0.2901); at the long horizons it is roughly level with the simpler HAR variants, so the IV edge concentrates at the short end. On hard_cases the curve is flatter and lower (0.3094 → 0.3391).

**Calibration / coverage.** Well calibrated on clean_core: at h=22 cov50 = 0.5607, cov90 = 0.9165. Hard_cases at h=22 is a touch under nominal (cov50 = 0.4743, cov90 = 0.8524), heavily dragged by the thin IV-starved tickers.

**Conditional bias.** The IV block clearly *reduces* the high-IV under-forecast. At h=22 (clean_core) log_bias by IV-percentile bucket is −0.1473 / −0.1619 / −0.1183 / −0.0807 / −0.0204 (buckets 0→4) — the smallest high-IV-bucket bias of the four reports, with the forecast pulled up in elevated-vol regimes by conditioning on IV. Hard_cases is milder still (−0.1029 → −0.0496).

**Post-shock behavior.** Best post-shock calibration of the four reports: at h=22 bias_all = −0.1031 vs bias_postshock = −0.0497 (n=3,914, clean_core) — the post-shock bias is *smaller in magnitude* than the unconditional bias, and the **trap flag does NOT fire**. Conditioning on the (elevated) post-shock IV keeps the forecast appropriately high. Hard_cases shows the same favorable pattern (−0.0748 → −0.0842, essentially flat, no trap flag).

**Across tickers (h=22, clean_core).** Strongest on GLD (0.1427), TLT (0.2057), EEM (0.2566), XLE (0.2839) — generally the lowest per-ticker QLIKEs of the four reports on the easy names. The weak spot is **HYG (0.8343)** — its highest per-ticker QLIKE *of all four reports*, an interesting reversal: adding IV actually *raises* HYG's QLIKE relative to the variance-only HAR variants even though its bias improves (−0.3617 vs HAR-RS's −0.6345), suggesting HYG's IV signal is noisy / mismatched to its realized path. SPY (0.4583) is next weakest. On hard_cases, KRE (0.3477) and UVXY (0.3252) are weakest; IBIT (0.1588) and USO (0.2329) are nominally low (IBIT on a tiny n=224 sample).

**IV-incremental skill (the headline for this model).** At h=22 `qlike_gain_vs_iv = −0.0061` (clean_core) — essentially level with IV-as-forecast at the primary horizon, which is the natural ceiling there since IV *is* one of its inputs. The real story is the short horizons: `qlike_gain_vs_iv = +0.0455` at h=1 and **+0.0265 at h=5**, the strongest short-horizon IV-incremental skill of the four reports — combining the realized path with IV decisively beats IV alone where the realized signal is freshest. The §5 regression slope on its signal is large and significant at the short end (0.48 at h=1, t=47; 0.50 at h=5, t=38) and fades by h=22 (slope 0.033, t=1.7, i.e. little left to add over IV at the primary horizon). On hard_cases the same shape holds: +0.0477 at h=1, ~0 at h=5, slightly negative thereafter. Sign-accuracy peaks at h=1 (0.70 clean_core / 0.74 hard_cases).

## Coverage & limitations

- **Near-full coverage on all 10 clean_core tickers** (~2,059 OOS rows per ticker × 5 horizons; 104,000 clean_core / 142,497 file total), losing only a handful of warmup rows plus any IV-null rows. No clean_core ticker is materially shortened.
- **IV-feature nulls drop rows (never imputed)** — the defining coverage limitation. Because the model `needs` the full IV block, any `(ticker, date)` with a null IV feature is excluded from both fit and predict. This sharply shortens the thin-option hard cases:
  - **IBIT** predicts only 2025-05-01 → 2026-05-21 (1,247 rows total; ~1y of options/IV history; only n=224 at h=22). Its interval coverage is consequently poor (cov90 = 0.50, cov50 = 0.27 at h=22) on that tiny sample — flagged for the comparison reader.
  - **MSOS** predicts only 2021-06-01 → 2026-05-21 (6,055 rows; thin/late IV coverage; n=1,181 at h=22), with a *positive* log_bias at h=22 (+0.1912) and weak coverage (cov90 = 0.70).
  - UVXY/USO/KRE have near-full coverage (~10,400 rows each).
- General limitation: HAR-RS-IV-Q cannot forecast where IV inputs are missing, so its support is **narrower than the variance-only HAR variants** (HAR/HARQ/HAR-RS/HAR-CJ). This is the key thing the comparison's common-support join must account for when ranking it against the variance-only models.

## Reproduction

```bash
.venv/bin/python -m rv_eval.walkforward --model candidate_models.har_rs_iv_q:HARRSIVQ --universe clean_core
.venv/bin/python -m rv_eval.walkforward --model candidate_models.har_rs_iv_q:HARRSIVQ --universe hard_cases
.venv/bin/python -m rv_eval.selfstats --pred execution/data/predictions/HAR-RS-IV-Q.parquet --out candidate_models/cards/HAR-RS-IV-Q.md --universe clean_core
.venv/bin/python -m rv_eval.selfstats --pred execution/data/predictions/HAR-RS-IV-Q.parquet --out candidate_models/cards/HAR-RS-IV-Q.hard_cases.md --universe hard_cases
```
