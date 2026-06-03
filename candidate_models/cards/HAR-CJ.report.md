# HAR-CJ — Modeling Report

**Identity.** Model 6 · class `candidate_models.har_cj:HARCJ` (name `HAR-CJ`) · Tier: Modern HAR (continuous + jump decomposition).

## Overview

HAR-CJ is plain log-OLS HAR augmented with a continuous-vs-jump decomposition of realized variance. The single idea it adds over HAR is **persistence separation**: total RV mixes a smooth continuous (diffusive) component with sporadic jumps, and these have very different dynamics — the continuous part is highly persistent and forecasts future variance well, while jumps are transient and largely unpredictable. By giving the regression a dedicated measure of the continuous part (bipower variation) at day/week/month scales plus a separate daily jump term, HAR-CJ lets it lean on the persistent component and discount the noisy jump component.

## Modeling approach & rationale

HAR-CJ implements the continuous-plus-jump idea of Andersen, Bollerslev & Diebold (HAR-CJ). Bipower variation (BV) is a jump-robust estimator of the continuous part of quadratic variation; the jump component is (roughly) RV minus BV. The economic argument is that the diffusive variance is what carries volatility's long memory, whereas jumps are one-off and mean-revert almost immediately, so a forecast that conditions on BV persistence and treats jumps separately should be both more persistent and more robust than one that regresses on total RV alone. Here the model keeps the standard HAR lags of *total* RV (`HAR_FEATURES`) and adds day/week/month log-BV roll-means (continuous persistence) plus a daily log-jump term, then runs the same linear log-OLS and lognormal back-transform as HAR — so any gain is attributable to the decomposition.

## Features & inputs

`needs = HAR_FEATURES + ["log_bv_d", "log_bv_w", "log_bv_m", "log_jump_d"]`.

- `log_rv_d`, `log_rv_w`, `log_rv_m` — the Corsi total-RV day/week/month log components, from `features.py`.
- `log_bv_d`, `log_bv_w`, `log_bv_m` — trailing (include-today) log-roll-means of bipower variation at windows w = 1 / 5 / 22 (w=1 is just `log(bv)`), the continuous-component persistence block.
- `log_jump_d` — the daily log-jump term, isolating the transient discontinuous variation.

`bv` and `jump` live in `inputs.parquet` (per `setup/measurement.py`) and pass through `features.build_features` untouched, so they are present on `X` at fit/predict. The four BV/jump-derived columns are **not** in `features.py` — they are built inside `har_cj.py`, deliberately leaving `features.py` untouched. BV and jump are floored at `1e-12` before the log (they can be exactly 0 — e.g. a session with no detected jump gives `jump == 0`), matching the log-floor convention in `features.py`.

## Design & implementation

HAR-CJ subclasses `_LinearLogHAR` (so the per-`(ticker, horizon)` OLS of `log(target_var)`, lognormal-mean `rv_hat = exp(mu + ½ s²)`, `sigma`, and `_lognormal_quantiles` are all inherited and identical to the benchmarks). **No free hyperparameters.**

The model-specific decision is *how the derived columns are injected*. HAR-CJ overrides `fit` and `predict` to call `_attach(X)` before delegating to `super()`. `_attach` builds the three log-BV roll-means and `log_jump_d` **once over each ticker's FULL point-in-time series** (read from `inputs.parquet`), then **left-joins** them onto the `X` slice by `(ticker, date)`. This full-series-then-join design is essential and leakage-safe: the walk-forward hands `fit`/`predict` only a train slice or a single one-month test slice, so computing `rolling_mean(22)` on that slice alone would null out its leading 21 rows and drop them at predict (NaN propagates through `_LinearLogHAR._design`). The first build attempt did exactly that and yielded only ~41 unique OOS dates; the join fix restores the full ~2,109-date coverage matching the sibling HAR models. Because the windows are trailing/include-today, every value uses only at-or-before-date rows — so building on the full series introduces no look-ahead. (If `X` carries `(ticker, date)` keys absent from `inputs.parquet` — the synthetic smoke test — `_attach` falls back to building the table straight from `X`, which there *is* the full series.) The full-history CJ table is cached on the instance after first build.

## Self-only results interpretation

**QLIKE across horizons.** On clean_core, pooled QLIKE is 0.3043 / 0.2057 / 0.2257 / 0.3451 / 0.4716 at h = 1 / 5 / 10 / 22 / 42. HAR-CJ is notably strong at the *short* horizons (h=1 QLIKE 0.3043, the lowest of its own curve relative to siblings) where separating the fresh jump out of the daily signal helps most, but its long-horizon QLIKE (h=42 = 0.4716) is the highest of the four reports here — the BV-persistence block over-extrapolates at long range. Headline **QLIKE@h22 = 0.3451** (hard_cases 0.3132). On hard_cases the curve is much flatter (0.3303 → 0.3546).

**Calibration / coverage.** Well calibrated on clean_core: at h=22 cov50 = 0.5738, cov90 = 0.9142. Hard_cases at h=22 is near nominal (cov50 = 0.4993, cov90 = 0.8672).

**Conditional bias.** The mildest IV-bucket bias of the four reports. At h=22 (clean_core) log_bias is −0.1694 / −0.1457 / −0.1139 / −0.0974 / −0.0768 (buckets 0→4) — a gentle under-forecast shrinking toward zero as IV rises. On hard_cases the highest-IV bucket even turns slightly *positive* (−0.2307 → +0.0195 across buckets 0→4).

**Post-shock behavior.** Best-behaved of the four here: at h=22 bias_all = −0.1222 vs bias_postshock = −0.1694 (n=3,986, clean_core) — only a modest deepening, **trap flag does NOT fire**. On hard_cases the post-shock bias (−0.1036) is essentially equal to the unconditional bias (−0.1080): the continuous-component conditioning keeps post-shock forecasts appropriately high.

**Across tickers (h=22, clean_core).** Strongest on GLD (0.1680), TLT (0.2251), EEM (0.2533), XLE (0.3237). The clear weak spot is **HYG (0.7196)** — the highest per-ticker QLIKE of the four reports on HYG, with a large negative bias (−0.5582). SPY (0.4506) is next weakest. On hard_cases, KRE (0.3776) and UVXY (0.3359) are weakest; IBIT (0.1959) is nominally low on a small n=517 sample. MSOS shows a slightly positive bias (+0.0619).

**IV-incremental skill.** At h=22 `qlike_gain_vs_iv = −0.0076` (clean_core) — about even with, slightly behind, IV-as-forecast at the primary horizon — but strongly positive at h=1 (+0.0232), where the jump-separated short-horizon forecast clearly beats IV. The §5 regression slope on HAR-CJ's signal is large and highly significant at every horizon (e.g. 1.32 at h=1, t=46; 0.79 at h=22 on hard_cases, t=38), indicating its forecast carries real incremental information about the IV residual even where pooled QLIKE is even. Sign-accuracy is high at h=1 (0.68 clean_core / 0.72 hard_cases).

## Coverage & limitations

- **Full coverage on all 10 clean_core tickers**, 105,450 OOS rows (≈2,087 per ticker × 5 horizons), span 2018-01-02 … 2026-05-22.
- `bv` and `jump` have **zero nulls** across the entire inputs panel, so no rows were dropped for missing BV/jump (none imputed). Coverage therefore equals the full variance-path support — identical to HAR-RS/HARQ and broader than the IV-using models.
- **Hard_cases data-starvation is a history effect, not a model drop.** All 5 tickers cover all 5 horizons (40,810 rows). IBIT (~2,713 rows total, 517 at h=22) and MSOS (~6,462 rows, 1,270 at h=22) have short histories; IBIT's interval coverage at h=22 is weak (cov90 = 0.7408) on its thin sample.
- The full-series-then-join injection (above) is the one non-obvious implementation point: it is what gives HAR-CJ full date coverage rather than the ~41-date degenerate slice the naive per-fold rolling-mean would produce.

## Reproduction

```bash
.venv/bin/python -m rv_eval.walkforward --model candidate_models.har_cj:HARCJ --universe clean_core
.venv/bin/python -m rv_eval.walkforward --model candidate_models.har_cj:HARCJ --universe hard_cases
.venv/bin/python -m rv_eval.selfstats --pred execution/data/predictions/HAR-CJ.parquet --out candidate_models/cards/HAR-CJ.md --universe clean_core
.venv/bin/python -m rv_eval.selfstats --pred execution/data/predictions/HAR-CJ.parquet --out candidate_models/cards/HAR-CJ.hard_cases.md --universe hard_cases
```
