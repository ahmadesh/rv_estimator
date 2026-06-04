# Iteration-2 Model Catalog — Modern-HAR Extensions

**Authoritative per-model build spec for the second wave**, operationalising
[`planning_docs/research/rv_har_extensions_plan.md`](../planning_docs/research/rv_har_extensions_plan.md).
This is the iter-2 analogue of [`rv_eval/MODEL_PLAN.md`](../rv_eval/MODEL_PLAN.md) §4 — same
harness, same output contract, same walk-forward, same `selfstats` cards. It **reuses**
`rv_eval/` unchanged; new models are files in `candidate_models/`.

Run them with the iter-2 swarm: [`ITER2_ORCHESTRATOR_PROMPT.md`](ITER2_ORCHESTRATOR_PROMPT.md)
+ [`ITER2_SWARM_KICKOFF.md`](ITER2_SWARM_KICKOFF.md), ledger
[`iter2_swarm_progress.md`](iter2_swarm_progress.md).

> **Numbering** continues the iter-1 catalog (0–12). New models are **13–32**, grouped by
> the plan's Tracks A–E. Model `name` (filesystem-safe) becomes the prediction filename and
> the card path — keep it exactly as listed.

---

## 1. How these reuse the existing harness (read once)

The walk-forward builds features centrally and hands the model only feature slices:

```
walkforward.main(): X = build_features(read inputs.parquet); per fold → model.fit(X_train,y_train); model.predict(X_test)
```

So a model can use **(a)** any column already in `inputs.parquet` (they pass through
`build_features` into X — including the six new systematic regime columns `vix9d`,
`vix9d_slope`, `credit_spread`, `credit_mom`, `usd_mom`, `rates_mom`), **(b)** the pre-baked
feature groups in `features.py`, and **(c)** any *derived* column it builds itself — but
derived **rolling** features must follow the join pattern below, never be recomputed on the
predict slice.

### The three reuse patterns (every iter-2 model is one of these)

| Pattern | Base | When | Reference impl |
|---|---|---|---|
| **P1 · Linear-log HAR + derived join** | `_LinearLogHAR` + `_AttachMixin` | Track A, C3, E2 — add trailing-window regressors, fit log-OLS | `candidate_models/har_cj.py` (the `_attach`/`_cj_panel` join) |
| **P2 · Per-key custom fit** | `_PerKeyModel` | Track B (shrinkage), D1/D2 (hetero-σ), E1 (threshold) — per-(ticker,h) but non-OLS fit / time-varying σ | `candidate_models/realized_garch.py` |
| **P3 · Direct `Model` impl** | `Model` (ABC) | Track C1/C2 (pooling across tickers), D3 (direct quantiles), D4 (spread), E3 (Markov-switch) — break the per-ticker-independence assumption | `candidate_models/ensemble_top.py` (post-hoc) |

**Critical rolling-feature rule (P1).** The walk-forward hands `predict` only the
one-month test slice, so `rolling_mean(22).over("ticker")` computed *inside* predict would
be null for its leading rows. Instead, build the trailing windows **once on the full series
from `inputs.parquet`** and **join by `(ticker, date)`** — exactly as `har_cj.py::_attach`
does, including its fallback to building from X when X carries keys absent from
`inputs.parquet` (the synthetic smoke test). The `_AttachMixin` (§2) packages this so each
Track-A model only writes a `_derive(inputs) -> DataFrame[ticker,date,<cols>]` hook.

### Output contract (unchanged — must match exactly)

`predict(X)` returns `ticker, date, horizon, rv_hat, sigma, q05, q10, q25, q50, q75, q90, q95`.
`rv_hat` in `target_var` units. Quantiles via `_lognormal_quantiles(m, s)` **except** D3/D4
which emit quantiles directly (and must keep them non-decreasing). `sigma` may be **per-row**
(D1/D2): the base `predict` already applies `sigma`/quantiles elementwise, so returning a
length-`n` `s` array from `_predict_one` works with **no harness change**.

---

## 2. Pre-flight infra — Wave 0 (one worker, before any model)

A single shared module keeps the Track-A/C/E models DRY. **This is the only new file outside
a per-model sandbox; one designated infra worker writes it, then it is frozen.**

`candidate_models/_base_v2.py` — provides:

- **`_AttachMixin`** — generalises `har_cj.py::_attach`. Subclass supplies
  `_derive(self, inputs: pl.DataFrame) -> pl.DataFrame` returning `[ticker, date, *new_cols]`
  built with trailing windows on the full series; the mixin caches it, joins into X at
  fit/predict, and falls back to `_derive(X)` when X has uncovered keys (smoke test). Wraps
  `fit`/`predict` to attach before delegating to `super()`.
- **`_PooledLinearHAR(Model)`** — pooled OLS of `log(target_var)` per horizon across all
  tickers in the fit set, with **group + ticker fixed-effect intercepts** and shared slopes;
  optional ridge-to-pooled shrinkage weight `w` (for C2). Reuses `_lognormal_quantiles`,
  `Q_COLS`, `C.HORIZONS`. Emits the standard schema.
- **`_QuantileModel(_PerKeyModel)`** — overrides `predict` to emit `q05…q95` from per-(ticker,h)
  quantile fits (set by a `_fit_one`/`_predict_quantiles` hook) instead of the lognormal
  wrapper; still fills `rv_hat=q50`-consistent mean and a `sigma` proxy for downstream sizing.

It imports only from `rv_eval` (`Model`, `_PerKeyModel`, `_lognormal_quantiles`, `Q_COLS`,
`config`) — **no edits to `rv_eval/`.** Smoke-test it with a synthetic 3-ticker panel.

---

## 3. Catalog

Each entry: **file:Class · base/pattern · `name` · needs/derived · note · ref · wave**. LOC
budgets are guidance. All set seeds where stochastic. Priority shortlist (plan's "if only
five"): **15, 19, 24, 26, 29**.

### Track A — new linear feature blocks (Pattern P1; Wave 1)

**13 · LHAR (leverage)** — `candidate_models/lhar.py:LHAR` · `name="LHAR"`
- Derived (`_derive`): `lev_d/w/m = rolling_mean(min(ret_cc,0), {1,5,22}).over("ticker")` (signed
  downside-return aggregates). `ret_cc` is in inputs.
- `needs = HAR_FEATURES + ["lev_d","lev_w","lev_m"]`. Ref: Corsi-Renò 2012.

**14 · HAR-SJ (signed jump)** — `candidate_models/har_sj.py:HARSJ` · `name="HAR-SJ"`
- Derived: `sj_5d = rolling_mean(rs_plus-rs_minus,5)`, `abs_sj_5d = |sj_5d|`. (`rs_plus/rs_minus`
  in inputs.)
- `needs = HAR_RS_FEATURES (minus jump_5d) + ["sj_5d","abs_sj_5d"]`. Ref: Patton-Sheppard 2015.

**15 · HAR-IVTS (IV term structure + VRP state)** — `candidate_models/har_ivts.py:HARIVTS` · `name="HAR-IVTS"` *(priority)*
- Derived: `iv_curv = iv_30d - 2*iv_60d + iv_90d`; `iv_ts_30_90 = iv_90d - iv_30d`;
  **`vrp_lag = iv_30d**2 - total_rv`** (point-in-time VRP proxy — use `iv_30d²`, **not**
  `targets.iv2`, which is not in X; see §4 discrepancy); `vrp_mom = vrp_lag - vrp_lag.shift(5).over("ticker")`.
  Also pass through `vix9d_slope` (already in X).
- `needs = HAR_FEATURES + IV_FEATURES + ["iv_curv","iv_ts_30_90","vrp_lag","vrp_mom"]`.
- The §5-by-construction model: directly encodes VRP mean-reversion. Ref: VIX-TS→RV (S1057521922001600).

**16 · HAR-Range** — `candidate_models/har_range.py:HARRange` · `name="HAR-Range"`
- Derived: `log_park_d/w = log(rolling_mean(parkinson,{1,5}))`, same for `gk`. (`parkinson`,`gk`,`rs` in inputs.)
- `needs = HAR_FEATURES + ["log_park_d","log_park_w","log_gk_d","log_gk_w"]`. Ref: Yang-Zhang.

**17 · HAR-Act (activity/overnight)** — `candidate_models/har_act.py:HARAct` · `name="HAR-Act"`
- Derived: `log_vol_surprise = log(volume) - log(rolling_mean(volume,22))`; same for `transactions`;
  `overnight_share = rv_overnight / total_rv`. (All in inputs.)
- `needs = HAR_FEATURES + ["log_vol_surprise","log_txn_surprise","overnight_share"]`. Ref: Bollerslev "risk everywhere".

**18 · HAR-MAX (kitchen sink, OLS)** — `candidate_models/har_max.py:HARMAX` · `name="HAR-MAX"`
- `needs =` union of 13–17 derived + `HAR_RS_FEATURES + IV_FEATURES + ["sqrt_rq"]` (~25 cols, deduped).
- **Deliberately over-parameterised** — its job is the OLS-overfit baseline that B1/B2 must beat.
  `_AttachMixin._derive` concatenates the other tracks' derivations.

### Track B — shrinkage & combination (Wave 1–2)

**19 · HAR-ENet / HAR-Ridge** — `candidate_models/har_shrink.py:{HARENet,HARRidge}` · `name="HAR-ENet"`,`"HAR-Ridge"` · Pattern P2 over `_AttachMixin` *(priority: ENet)*
- Same feature matrix as **18**. Override `_fit_one`: standardise X (store μ/σ), fit
  `sklearn.linear_model.ElasticNetCV` (HAR-ENet) or `RidgeCV` (HAR-Ridge) with a
  **time-ordered inner CV on the train slice only** (no OOS leakage); `_predict_one` applies the
  stored scaler+coefs, `sigma` from in-sample log-resid std. Ref: shrinkage-HAR (S105905602400306X, 2024).

**20 · HAR-CSR (complete-subset regression)** — `candidate_models/har_csr.py:HARCSR` · `name="HAR-CSR"` · P2
- Average `rv_hat` over all `k`-feature OLS subsets of a curated ~8-feature set (k≈4; cap #subsets,
  e.g. ≤70, sample if larger). `_fit_one` stores the subset betas; `_predict_one` averages. Ref: Elliott-Gargano-Timmermann; HAR-CSR (S0957417421008356).

**21 · EnsembleTopK-v2** — `candidate_models/ensemble_top_v2.py:EnsembleTopKV2` · `name="EnsembleTopK-v2"` · P3 (post-hoc, reads parquets) · **Wave 2, after its components exist**
- Like `ensemble_top.py` but **regime-conditional / discounted-MSE weights** (weights vary by
  IV-percentile bucket from `targets`), pooling the iter-1 winners + the best new A/B/D models.
  `fit()` is a no-op; reads `predictions/<component>.parquet`.

### Track C — cross-ticker pooling (Pattern P3 / `_PooledLinearHAR`; Wave 2)

**22 · PanelHAR-FE** — `candidate_models/panel_har.py:PanelHARFE` · `name="PanelHAR-FE"`
- `_PooledLinearHAR`: one pooled OLS per horizon across the fit set, ticker+group FE intercepts,
  shared HAR-RS-IV slopes. ~10× obs/coef. **Cannot subclass `_PerKeyModel`** (it loops per
  ticker) — that's why `_PooledLinearHAR` exists.

**23 · HAR-Shrink2Group** — `candidate_models/har_shrink2group.py:HARShrink2Group` · `name="HAR-Shrink2Group"` *(priority)*
- Per-ticker OLS β shrunk toward the pooled/group β: `β = (1-w)·β_ticker + w·β_pooled`, `w` by
  inner-CV. Uses `_PooledLinearHAR` for the pooled fit + `_LinearLogHAR` per-ticker. Safer than 22.

**24 · GlobalVolFactor-HAR** — `candidate_models/har_globalfactor.py:HARGlobalFactor` · `name="HAR-GVF"` · P1
- Derived **systematic** factor: cross-sectional **mean of clean-core `total_rv` per date**
  (no fitted loadings → no leakage; SPX RV is **not** in inputs, see §4). `_derive` computes
  `gvf = mean(total_rv) over tickers per date`, `log_gvf`. `needs = HAR_FEATURES + ["log_gvf"]`.

### Track D — calibration & distribution (Wave 1–2; the primary objective)

**25 · HARX-HeteroSigma** — `candidate_models/harx_hs.py:HARXHeteroSigma` · `name="HARX-HS"` · P2 *(priority — do first)*
- Mean model = HAR-X (`HAR_FEATURES+IV_FEATURES`). Override `_fit_one` to **also** regress squared
  log-residuals on `[log_sqrt_rq, vix, vvix, vix9d_slope]` (a log-variance model); `_predict_one`
  returns a **per-row** `s_t` from that fit. No harness change (base applies σ elementwise).
  Cheapest, highest-leverage calibration fix.

**26 · HAR-GARCH** — `candidate_models/har_garch.py:HARGARCH` · `name="HAR-GARCH"` · P2
- Per-(ticker,h): HAR mean, then `arch` GARCH(1,1)/GJR on the log-residuals → time-varying `s_t`.
  Light state-space. Library: `arch` (present).

**27 · HAR-QR (direct quantiles)** — `candidate_models/har_qr.py:HARQR` · `name="HAR-QR"` · P3 / `_QuantileModel`
- Per-(ticker,h) **quantile regression** (`sklearn.linear_model.QuantileRegressor` or statsmodels)
  for each of `C.QUANTILES` on the A-feature set; emit `q05…q95` directly, enforce monotonicity
  (sort). `rv_hat` = mean proxy. Optimises pinball/coverage directly.

**28 · VRP-Spread head** — `candidate_models/vrp_spread.py:VRPSpread` · `name="VRP-Spread"` · P3 *(priority)*
- Model the spread `s_t = iv_30d² - total_rv` (HAR-style mean-reversion on `s` + curve/regime
  features), emit `rv_hat = max(iv_30d² - ŝ, floor)` and a calibrated sign-confidence. Spread can
  be negative → fit in **level** space (OLS), not log. **§5-as-loss.** ⚠ leakage: use `iv_30d²`
  (point-in-time, in X), and the evaluator compares to *next-period* realized — fine.

### Track E — regime / threshold (Wave 3; light state-space)

**29 · Threshold-HAR** — `candidate_models/threshold_har.py:ThresholdHAR` · `name="Threshold-HAR"` · P2
- Regime split on an **observable in X**: `vix` expanding-percentile (computed in `_derive`,
  point-in-time) or `sign(vix9d_slope)` (contango/backwardation). Per-regime OLS in `_fit_one`;
  `_predict_one` routes each row by its regime. **Note:** `post_shock` is **not** in X (§4) — use
  the vix-percentile / term-slope regime instead, or a self-derived RV-spike proxy.

**30 · STAR-HAR (interaction)** — `candidate_models/star_har.py:STARHAR` · `name="STAR-HAR"` · P1
- `_derive` adds `HAR_FEATURES × vix_pctile` interaction columns (expanding percentile, leak-safe).
  One OLS. Cheaper/smoother than 29.

**31 · MS-HAR (Markov-switching, 2-state)** — `candidate_models/ms_har.py:MSHAR` · `name="MS-HAR"` · P3 · **highest cost — gate hard vs 29/30**
- 2-state HAR via EM (statsmodels `MarkovRegression` or hand-rolled); regime-conditional mean+var →
  mixture predictive distribution (map to `rv_hat`,`sigma` + quantiles). Build last; reject if it
  doesn't beat the cheap regime models.

---

## 4. Reuse discrepancies & resolutions (the requested report)

Everything below is reusable **without editing `rv_eval/`**; the items are the sharp edges.

1. **Derived rolling features can't be computed in `predict`** (slice has no history). **Resolved**
   by the HAR-CJ `_attach` join pattern, packaged as `_AttachMixin`. No `features.py` edit — the
   swarm's "never touch rv_eval/" rule holds. *(This was the only thing that looked like it forced
   a harness change; it doesn't.)*
2. **`post_shock` and `iv2` live in `targets.parquet`, NOT in X.** `predict` only receives features.
   → **E1/Threshold-HAR** must define its regime from in-X signals (`vix` percentile, `vix9d_slope`
   sign) not `post_shock`. → **D4/VRP-Spread** and **A3/HAR-IVTS** must use **`iv_30d²`** (in X) as
   the IV-variance, not `targets.iv2`. Both are legitimate point-in-time substitutes.
3. **`_PerKeyModel` assumes per-ticker independence** → **pooling (22/23)**, **direct-quantile (27)**,
   **VRP (28)**, **MS-HAR (31)** implement the `Model` ABC directly (via `_PooledLinearHAR` /
   `_QuantileModel` / bespoke). They still reuse `_lognormal_quantiles`, `Q_COLS`, `config`, and the
   exact output schema — only the fit loop differs.
4. **Per-row `sigma` is already supported** by the base `predict` (σ and quantiles are applied
   elementwise; `_predict_one` may return a length-`n` `s` array). → **D1 (25) needs no harness
   change.** Confirmed by reading `model_contract.py::_PerKeyModel.predict`.
5. **SPX/VIX RV is not in `inputs.parquet`** (only the 15 scored tickers are). → **C3/HAR-GVF** builds
   its market factor from the **clean-core RV cross-section** (a per-date mean — leak-free), not SPX RV.
6. **History-to-2007 (plan §6) is largely already in effect.** `config.TRAIN_WINDOW="expanding"` with
   fold `lo=0` means every model already trains on **all** panel history from the earliest date
   (RV from 2003, IV from 2007); `MIN_TRAIN_DAYS=252*3` only gates the first OOS fold (still 2018).
   → **No code change needed** to "extend depth"; the IV-dependent models already see 2007→. Treat
   plan §6 as a *robustness check already satisfied*, or, to actually shorten history for a
   sensitivity test, switch to `rolling`. (One genuine correction to the research plan's framing.)
7. **New systematic columns flow automatically** (`vix9d`, `credit_*`, `usd_mom`, `rates_mom`):
   they're in `inputs.parquet`, so `build_features` passes them into X. They are **not** in any
   `*_FEATURES` constant — reference them by raw name in `needs`/`_derive`. No `features.py` edit.
8. **`selfstats` + the comparison pass are fully reusable as-is.** `selfstats` already emits the §5
   IV-skill and §6 conditional-bias panels per model. The plan's *re-weighted gate* (§4 of the
   research plan: §5/calibration promoted above raw QLIKE) is an **interpretation applied in the
   comparison pass**, not new code — record it in the comparison doc, not the harness.

**Net:** zero edits to `rv_eval/`. One new shared file (`candidate_models/_base_v2.py`, Wave 0) and
one file per model. The output contract, walk-forward, lognormal machinery, `selfstats` cards, and
the evaluator all carry over unchanged.

---

## 5. Evaluation (unchanged harness, re-weighted gate)

Per model: run the walk-forward on both universes, then `selfstats` → two cards (exactly as
iter-1, MODEL_PLAN §2 steps 5–9). The cross-model comparison + the **re-weighted gate**
(guardrail: h=22 QLIKE in the MCS tie-set; acceptance: §5 sign-acc / IV-gain and conditional
coverage; see research plan §4) run **once, separately**, after predictions exist — out of scope
for workers. Do **not** call `evaluator.py` in a worker.
