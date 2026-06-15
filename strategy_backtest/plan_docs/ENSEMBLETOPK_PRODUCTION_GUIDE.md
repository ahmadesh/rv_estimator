# EnsembleTopK — Production Guide for the 22-Day RV Forecaster

_Synthesis & production reference · compiled 2026-06-06 · repo git `d438fd8`_

> **Purpose.** A single, complete guide to the **EnsembleTopK** realized-variance forecaster — the
> model promoted as the **primary 22-day (≈30 DTE) RV predictor** across every stage of this study.
> It covers (1) what the model is, (2) exactly which sub-models it combines and what each regresses
> on, (3) how it is trained, refit, and whether it needs per-feature training or calibration,
> (4) what signal each sub-model emits and how they are combined, and (5) how to run, validate, and
> deploy it. It is meant to be self-contained for someone putting this model into production.
>
> **Scope note.** "EnsembleTopK" in this document means the **iteration-1 equal-weight ensemble**
> (`candidate_models/ensemble_top.py:EnsembleTopK`). It is *not* `EnsembleTopK-v2` — see §10 for why
> v2 was built and rejected.

---

## 0. TL;DR

- **EnsembleTopK = the equal-weight mean (in variance/level space) of four linear HAR-family
  forecasts:** `HAR-RS-IV-Q`, `HARQ`, `HAR-RS`, `HAR-CJ`. It is a *post-hoc combiner* — it has **no
  parameters of its own, no training, and no calibration step**. `fit()` is a no-op; `predict()`
  reads the four components' prediction files and averages them.
- **It is the winner at h=22 — but on the right axes.** It is *not* the single lowest h=22 point-QLIKE
  model on clean_core (HARQ 0.3226 and HAR 0.3232 edge it at 0.3241, all inside one MCS tie-set). It
  wins on **pooled QLIKE across horizons (0.2914, best in field), best-behaved interval calibration,
  robustness across clean+hard universes, no post-shock trap, and — decisively — the Stage-1 economic
  backtest** (best deflated Sharpe 0.68 and the smallest left tail at 30 DTE).
- **The conclusion is consistent across all three study stages** (iter-1 forecasting eval, iter-2
  forecasting eval, Stage-1 trading eval). See the consistency audit in §1.
- **Each of the four sub-models is trained separately per (ticker, horizon)** as a plain log-OLS HAR
  regression. The ensemble itself trains nothing. So "training" lives entirely in the components.
- **At 30 DTE the economic value is NOT a mean-return alpha over IV²** — it is **left-tail control**
  delivered downstream via the regime gate and σ-sizing, which consume the ensemble's `sigma`/`rv_hat`.
  Plan production expectations accordingly.

---

## 1. Consistency audit — is "EnsembleTopK wins at h=22" supported at every stage?

**Yes.** Three independent evaluation stages reach the same conclusion. The table reconciles them.

| Stage | Document | What it concluded about EnsembleTopK @ h=22 |
|---|---|---|
| **Iter-1 forecasting eval** | `execution/reports/FINAL_MODEL_COMPARISON_REPORT.md` | **Primary.** Best pooled QLIKE (0.2914), best-calibrated (cov90 0.927), robust across both universes, no §6 trap, ~4 s. HAR-X = simplest single-model fallback. |
| **Iter-2 forecasting eval** | `execution/reports/ITER2_FINAL_MODEL_COMPARISON_REPORT.md` + `iter2_verdicts.md` | **Incumbent unbeaten.** Of 20 new models, *none* beat the iter-1 incumbents on clean_core or on the decisive §5 axis. `EnsembleTopK-v2` (regime-weighted) was **rejected** — "does NOT beat iter-1 equal-weight EnsembleTopK." Iter-2 only added a *hard-case pooling sleeve* (`PanelHAR-FE`, `HAR-Shrink2Group`) for short-history names. |
| **Stage-1 trading eval** | `trade_eval/reports/STAGE1_RESULTS_REPORT.md` | **Stage-2 primary @ h=22.** DSR 0.68 vs IV-only 0.28; CVaR95 −0.018 vs −0.064; maxDD 0.051 vs 0.203; ≥ HAR-X at every horizon (A6); gate marginal-significant (p=0.026). HAR-X = fallback. |

**The one nuance to carry into production (stated honestly, and identically, in all three reports):**
EnsembleTopK's claim is **not** lowest raw h=22 QLIKE. At exactly h=22 on clean_core the entire HAR
family sits in one statistically inseparable MCS tie-set (p≈0.124–0.128); HARQ and HAR are a hair
lower on point QLIKE. EnsembleTopK wins because it is **simultaneously** best-pooled, best-calibrated,
most robust, trap-free, and — the deciding vote — the best **economic** book at 30 DTE. There is no
contradiction between the stages; they consistently rank it #1 on the axes that matter for the VRP
book and explicitly note it is co-equal on raw h=22 QLIKE.

**Caveats that travel with the verdict (consistent across stages):**
1. **§5 incremental skill over IV² collapses to ~coin-flip at h=22** (sign_acc ≈ 0.518). The forecast
   adds little *directional* information beyond IV² at 30 DTE. Two iter-2 head-on attacks on this
   (VRP-Spread, HARX-HS) both failed — the limit is real, not a modeling gap.
2. **No strategy clears the absolute deflated-Sharpe ≥ 0.95 bar** after 104-trial deflation (best
   0.68). Promotion rests on tail no-regress + signal attribution, not absolute Sharpe.
3. **For data-starved hard-case names (IBIT/MSOS-type), layer the pooling sleeve** (`HAR-Shrink2Group`
   primary, `PanelHAR-FE` bound) on top — that is the only thing iter-2 added that beats the
   incumbent, and only on the thin-name sleeve.

---

## 2. What EnsembleTopK is

A **post-hoc, equal-weight combiner** over four already-trained HAR-family forecasters. Formally, for
every `(ticker, date, horizon)` key, over the components available for that key:

```
rv_hat   = mean( component rv_hat )                         # arithmetic mean in LEVEL (variance) space
sigma    = sqrt( mean(component_sigma²) + var(component_rv_hat) )
                                                            # within-model variance + between-model dispersion
q05..q95 = lognormal_quantiles(m = rv_hat,
                               s = sqrt(log(1 + (sigma/rv_hat)²)))
```

- **Components (top-K = 4):** `HAR-RS-IV-Q`, `HARQ`, `HAR-RS`, `HAR-CJ` (hard-coded in
  `COMPONENTS` at the top of `candidate_models/ensemble_top.py`).
- **Availability rule:** a key is kept only if **≥ 2** components have a finite, positive `rv_hat`
  for it; otherwise the key is **dropped, never imputed**. In practice all four components have
  near-identical coverage, so the floor effectively never binds (142,497 of 146,260 keys used all 4;
  3,763 used exactly 3; 0 dropped).
- **No parameters, no seed, deterministic.** `fit()` is a no-op. There is nothing to tune, no random
  state, no learned weights.

### Output contract (identical to every model in the study)

Each row, keyed by `(ticker, date, horizon)`:

```
ticker · date · horizon · rv_hat · sigma · q05 · q10 · q25 · q50 · q75 · q90 · q95
```

| Output | Meaning | Units |
|---|---|---|
| `rv_hat` | Point forecast of **forward realized variance** = `E[ Σ_{s=t+1..t+h} RV_s ]`, the sum of the next `h` daily 5-min RVs. | Variance (annualize to vol via `√(rv_hat · 252/h)`). |
| `sigma` | Predictive **standard deviation of `rv_hat`** in level space — the model's uncertainty about its own point forecast (NOT the vol being forecast). | Same as `rv_hat`. |
| `q05…q95` | Full lognormal predictive distribution of forward RV. `q05…q95` = 90% interval; `q25…q75` = 50%; `q50` = median. Monotone by construction. | Same as `rv_hat`. |

The quantile *shape* is a shared lognormal wrapper; the only things the model controls are **where the
distribution sits (`rv_hat`)** and **how wide it is (`sigma`)**.

---

## 3. The four component models — what each regresses on

All four are **plain log-OLS HAR regressions** built on the shared base class
`rv_eval/model_contract.py:_LinearLogHAR`. Each fits, **independently per (ticker, horizon)**, an OLS
of `log(target_var)` on an intercept + its feature list, and emits the lognormal-mean-corrected point
forecast `rv_hat = exp(μ̂ + ½ŝ²)` plus `sigma` from the OLS log-residual std. **None has any free
hyperparameter; none is tuned; none uses a random seed.**

Feature names are produced by `rv_eval/features.py:build_features()` from `inputs.parquet`. The shared
feature constants are:

```
HAR_FEATURES    = [log_rv_d, log_rv_w, log_rv_m]
HARQ_FEATURES   = HAR_FEATURES + [sqrt_rq]
HAR_RS_FEATURES = [log_rv_d, log_rv_w, log_rv_m, rs_minus_5d, rs_plus_5d, jump_5d]
IV_FEATURES     = [log_iv, iv_slope, skew_25d, vix, vix3m, vix_slope, vvix]
```

### What each regressor means

The regressors fall into four blocks. All are **point-in-time** (trailing windows, known at the row's
date) and are built by `rv_eval/features.py` from the realized measures in `inputs.parquet`
(`setup/measurement.py`) and the implied-vol features (`setup/iv_features.py`).

**(a) HAR realized-vol lags — the Corsi (2009) heterogeneous-autoregressive backbone.** Volatility is
persistent at multiple time scales, so HAR regresses forward RV on its own averages over a day, week,
and month:

| Regressor | Definition | Why it's in the model |
|---|---|---|
| `log_rv_d` | log of `rv_d` = today's daily total realized variance (sum of 5-min intraday squared returns + overnight, Hansen-Lunde scaled). | The **short-memory** term — yesterday's vol is the strongest single predictor of tomorrow's. |
| `log_rv_w` | log of `rv_w` = trailing **5-day** mean of daily RV. | The **weekly** vol level — smooths daily noise. |
| `log_rv_m` | log of `rv_m` = trailing **22-day** mean of daily RV. | The **monthly** vol level — captures the slow-moving vol regime. |

**(b) Quarticity correction (HARQ, Bollerslev-Patton-Quaedvlieg 2016).**

| Regressor | Definition | Why it's in the model |
|---|---|---|
| `sqrt_rq` | √ of realized quarticity `rq = (n/3)·Σ r⁴` (clipped ≥ 0). RQ is the variance *of* the daily RV estimate. | When `RV_{t-1}` was itself a **noisy** estimate (high RQ), the HAR coefficient on it should shrink. `sqrt_rq` lets the regression **downweight noisy RV days**, fixing measurement-error attenuation bias. |

**(c) Semivariance / jump decomposition (Patton-Sheppard 2015; continuous-jump).** Splits raw RV into
economically distinct pieces because they predict future vol differently:

| Regressor | Definition | Why it's in the model |
|---|---|---|
| `rs_minus_5d` | 5-day mean of **downside semivariance** `rs_minus = Σ r²·1(r<0)` (sum of squared *negative* 5-min returns). | **Downside realized vol strongly predicts future vol** — the leverage/fear channel. The most put-relevant regressor. |
| `rs_plus_5d` | 5-day mean of **upside semivariance** `rs_plus = Σ r²·1(r>0)`. | Upside vol predicts future vol **much less**; separating it from downside sharpens the forecast. |
| `jump_5d` | 5-day mean of the **jump component** `jump = max(rv_intraday − bv, 0)`. | Discontinuous jumps are largely **transitory** — they don't persist the way smooth vol does, so they get their own (small) coefficient. |
| `log_bv_d/w/m` | log of trailing 1/5/22-day means of **bipower variation** `bv` — a jump-*robust* estimate of the **continuous** part of variance. | (HAR-CJ only.) The smooth, persistent part of vol — what actually carries forward. |
| `log_jump_d` | log of today's jump component. | (HAR-CJ only.) The daily transitory jump, modeled separately from `log_bv_*`. |

**(d) Implied-vol / VIX block (forward-looking, HAR-RS-IV-Q only).** The market's own vol expectations
— the only forward-looking information in the set, and what gives the ensemble its short-horizon edge:

| Regressor | Definition | Why it's in the model |
|---|---|---|
| `log_iv` | log of `iv_30d` = the ticker's own **30-day ATM implied vol** (interpolated from its option chain). | The market's 30-day vol forecast — directly relevant to the 30-DTE book. |
| `iv_slope` | `iv_90d − iv_30d` — the ticker's **IV term-structure slope**. | Slope encodes whether the market prices vol as mean-reverting (downward) or rising — a regime signal. |
| `skew_25d` | `put25 − call25` — the **25-delta risk reversal** (put IV minus call IV). | Steeper put skew = more priced crash risk = higher future-vol probability. |
| `vix` | SPX 30-day ATM IV (the VIX analog, constructed the same way). | Market-wide vol level — the systematic vol factor common to all names. |
| `vix3m` | SPX 90-day ATM IV (VIX3M analog). | The market-wide vol level at the longer tenor. |
| `vix_slope` | SPX `iv_90d − iv_30d` — the **VIX term-structure slope**. | Inverted (backwardated) VIX curve flags acute market stress. |
| `vvix` | The **VIX index's own 30-day ATM IV** — vol-of-vol. | How uncertain the market's vol forecast itself is; rises before vol regime shifts. |

> **Not used by the ensemble's components** (listed for completeness, present in `features.py`):
> `rv_q`/`log_rv_q` (66-day quarterly HAR lag) and `ewma_rv` (RiskMetrics λ=0.94 EWMA of RV) feed the
> RandomWalk/EWMA benchmarks, not the four EnsembleTopK members.

| # | Component | Regressors (exact) | What its signal captures |
|---|---|---|---|
| 4 | **HARQ** (Bollerslev-Patton-Quaedvlieg 2016) | `log_rv_d, log_rv_w, log_rv_m, sqrt_rq` (4 feats) | Standard HAR + a **quarticity attenuation** term that downweights `RV_{t-1}` when that day's RV was a noisy estimate. Fixes measurement-error bias. |
| 5 | **HAR-RS** (Patton-Sheppard 2015) | `log_rv_d, log_rv_w, log_rv_m, rs_minus_5d, rs_plus_5d, jump_5d` (6 feats) | HAR with RV split into **down vs up semivariance + jump**. Encodes "downside vol predicts future vol; upside largely doesn't" — the most put-relevant decomposition. |
| 6 | **HAR-CJ** (continuous/jump) | `log_rv_d, log_rv_w, log_rv_m` + `log_bv_d, log_bv_w, log_bv_m, log_jump_d` (7 feats) | Splits past RV into a **continuous (bipower, BV) component and a jump component**. Jumps don't predict future vol the way smooth vol does. *(The log-BV roll-means and `log_jump_d` are built inside `har_cj.py` from the `bv`/`jump` columns of `inputs.parquet` via a left-join — see "build note" below.)* |
| 7 | **HAR-RS-IV-Q** | `log_rv_d, log_rv_w, log_rv_m, rs_minus_5d, rs_plus_5d, jump_5d, log_iv, iv_slope, skew_25d, vix, vix3m, vix_slope, vvix, sqrt_rq` (14 feats) | The "everything linear" model: semivariance/jump + **implied-vol block** (IV level/slope/skew, VIX/VIX3M/VIX term-structure, VVIX) + quarticity. The only IV-aware component — it is what gives the ensemble its short-horizon IV skill. |

**HAR-CJ build note (relevant if you re-run it):** the walk-forward hands `fit`/`predict` only a
train slice or a single month, so a `rolling_mean(22)` computed *on that slice* would null its leading
21 rows and silently drop them. `HARCJ._attach()` therefore builds the log-BV roll-means + `log_jump_d`
**once over each ticker's full series** from `inputs.parquet` and left-joins them onto the slice by
`(ticker, date)`. Do not recompute rolling windows on per-fold slices.

### Is the ensemble trained per ticker? Does it need calibration?

- **Per-ticker (and per-horizon) training: yes, but inside the components — the ensemble itself
  trains nothing.** Each of the four components fits an **independent OLS per (ticker, horizon)**:
  for clean_core (10 tickers × 5 horizons) that is 50 independent regressions per component. There is
  no single global/pooled fit and no shared-across-tickers model — every ticker gets its own
  coefficients at every horizon. The ensemble is a parameter-free combiner on top: `fit()` is a no-op.
- **Calibration: none required.** There is no post-hoc calibration layer (no isotonic/Platt/variance
  inflation). The lognormal quantiles fall directly out of `(rv_hat, sigma)`. Empirically the
  ensemble is the **best-calibrated model in the study** as-is: cov90 = 0.927 on clean_core (target
  0.90; the slight over-coverage comes from the `var(means)` between-model term widening the
  intervals) and 0.882 on hard_cases. No calibration step is needed before deployment. If anything
  the intervals are marginally *wide* on clean_core, which is the safe direction for a short-vol book.

---

## 4. Signals each sub-model emits and how they are combined

### 4.1 What each component emits

All four components emit the **identical forecast contract** — `rv_hat, sigma, q05…q95` per
`(ticker, date, horizon)`. They do **not** emit different "signal types"; they differ only in *how
`rv_hat` and `sigma` are produced* (different regressor sets → different point forecasts and residual
spreads). Concretely, the signal each contributes to the mean:

- **HARQ** → an RV-only forecast that is robust to noisy single-day RV estimates.
- **HAR-RS** → an RV forecast that leans on **downside** semivariance and discounts jumps/upside.
- **HAR-CJ** → an RV forecast that separates persistent continuous vol from transient jumps.
- **HAR-RS-IV-Q** → the **IV-aware** forecast that injects the implied-vol/VIX term-structure view.

The diversity is deliberate: three RV-microstructure views (quarticity, semivariance, continuous/jump)
plus one forward-looking IV view. Averaging them reduces idiosyncratic estimation error and — via the
`var(component rv_hat)` term — **widens the predictive interval exactly when the four views disagree**,
which is the calibration property that makes the ensemble's `sigma` trustworthy downstream.

### 4.2 How they are combined (the combiner, step by step)

For each `(ticker, date, horizon)` key, `EnsembleTopK.predict()`:

1. Reads `execution/data/predictions/<component>.parquet` for each of the four components and keeps
   only `ticker, date, horizon, rv_hat, sigma`.
2. Restricts to the keys in this fold's feature matrix `X` (inner-join on `ticker, date`; horizons
   fan out) and filters to finite `rv_hat > 0` and finite `sigma ≥ 0`.
3. Groups by `(ticker, date, horizon)` and computes:
   - `rv_hat = mean(component rv_hat)` — **equal weight, arithmetic mean in level (variance) space.**
   - `mean_var = mean(component_sigma²)` — average within-model variance.
   - `between_var = var(component rv_hat, ddof=0)` — between-model dispersion.
   - `n_comp` = number of components present for the key.
4. Keeps keys with `n_comp ≥ 2` (`MIN_COMPONENTS`), drops the rest (never imputes).
5. Sets `sigma = sqrt(max(mean_var + between_var, 0))`.
6. Backs out the log-space sd consistent with the `_PerKeyModel` level-sigma convention
   `sigma = m·sqrt(expm1(s²))`, i.e. `s = sqrt(log(1 + (sigma/rv_hat)²))`, then regenerates
   `q05…q95` via `_lognormal_quantiles(rv_hat, s)`.

**Weights are fixed and equal (0.25 each when all four are present).** There is no learned weighting,
no regime conditioning, no time decay. That simplicity is a feature: iter-2's regime-weighted
`EnsembleTopK-v2` added all of that machinery and **did not beat** this equal-weight combiner at h=22
(§10).

### 4.3 From forecast outputs to trading decisions (downstream layer)

The ensemble emits only the forecast contract. The **trading layer** (`trade_eval/`, per
`planning_docs/execution/rv_trading_eval_plan.md`) derives the actual strategy signals from it:

| Forecast output | Derived trading signal | How it is used |
|---|---|---|
| `rv_hat` | `vrp_score = iv2 − rv_hat` | Conditional VRP / "sell vol when IV is rich" candidacy. |
| `sigma` | regime gate `{trade / reduce / avoid}` (driven by `sigma/rv_hat` vs a trailing-80th-pctile threshold + shock flags) **and** inverse-risk size `∝ vrp_score / σ²` | The gate sits out names about to blow up; sizing trades smaller when the forecast is less sure. **This is where the 30-DTE economic value comes from** (Stage-1 A2/A3). |
| `q05…q95` | tail/CVaR (the A5 sizing variant only) | Stage-1 found quantile-spread sizing is **not** better than the single-σ head — so production uses `sigma`, and the quantiles are carried but not load-bearing for sizing. |

**Key production expectation:** at 30 DTE `rv_hat` carries essentially no mean-edge over IV²
(§5 sign_acc ≈ 0.52). The book's edge is the **second moment** — the gate + σ-sizing cutting the left
tail (CVaR95 −0.018 vs IV −0.064, maxDD 0.051 vs 0.203, and the book *decorrelates* in stress:
cross-group corr 0.46→0.05). Do not deploy expecting directional alpha; deploy for tail control.

---

## 5. Performance reference (h=22 unless noted)

**Pooled / headline (clean_core):**

| Metric | EnsembleTopK | HAR (baseline) | Note |
|---|---|---|---|
| Mean QLIKE (all h) | **0.2914** | 0.3003 | Best in field — driven by short horizons (h=5 QLIKE 0.194). |
| QLIKE @ h=22 | 0.3241 | 0.3232 | Inside the MCS tie-set; HARQ 0.3226 nominally lowest. |
| cov90 @ h=22 | 0.927 | ~0.916 | Best-behaved; slightly wide (safe direction). |
| §6 post-shock trap | **none** | none | Entire HAR family is trap-free. |
| §5 sign_acc @ h=22 | 0.518 | 0.506 | Coin-flip — the caveat (true for all models). |
| Train wall-time | **~4 s** | seconds | Combiner only; components are seconds each. |

**Per-horizon QLIKE (clean_core):** h=1 0.2956 · h=5 **0.1939** · h=10 0.2130 · h=22 0.3241 · h=42 0.4305.
Same U-then-rise shape as HAR; best around h=5, worst at h=42.

**Hard_cases @ h=22:** QLIKE 0.2907, cov90 0.882. For thin names (IBIT cov90 0.758, MSOS 0.832)
prefer the pooling sleeve.

**Stage-1 economics @ h=22 (vs IV-only benchmark):** DSR **0.68** (IV 0.28) · CVaR95 **−0.018** (IV
−0.064) · maxDD **0.051** (IV 0.203) · AnnRet 0.047 (IV 0.068) · break-even ≈ 312 bps. The forecast
book earns slightly less than IV-only but with a 3–4× smaller tail and drawdown.

---

## 6. How to run it in production

### 6.1 Prerequisites (dependency order)

EnsembleTopK is a combiner — it **requires the four component prediction parquets to exist on disk
first**. The production refit order each period is:

```
inputs.parquet + targets.parquet            # data layer (setup/prepare_panel.py)
        │
        ▼  features.build_features()
  ┌─────┴─────────────────────────────┐
  ▼     ▼            ▼            ▼
HARQ  HAR-RS    HAR-CJ    HAR-RS-IV-Q     # 4 components, each: per-(ticker,horizon) log-OLS
  └─────┬─────────────────────────────┘
        ▼  predictions/<component>.parquet
   EnsembleTopK.predict()                  # equal-weight mean → predictions/EnsembleTopK.parquet
```

Use `.venv/bin/python` (system `python3` lacks polars).

### 6.2 Commands

```bash
# 1. Build/refresh component predictions (each writes execution/data/predictions/<name>.parquet)
.venv/bin/python -m rv_eval.walkforward --model candidate_models.harq:HARQ           --universe all
.venv/bin/python -m rv_eval.walkforward --model candidate_models.har_rs:HARRS        --universe all
.venv/bin/python -m rv_eval.walkforward --model candidate_models.har_cj:HARCJ        --universe all
.venv/bin/python -m rv_eval.walkforward --model candidate_models.har_rs_iv_q:HARRSIVQ --universe all

# 2. Build the ensemble (reads the four parquets above, writes predictions/EnsembleTopK.parquet)
.venv/bin/python -m rv_eval.walkforward --model candidate_models.ensemble_top:EnsembleTopK --universe all

# 3. (optional) self-stats card
.venv/bin/python -m rv_eval.selfstats --pred execution/data/predictions/EnsembleTopK.parquet \
    --out candidate_models/cards/EnsembleTopK.md --universe clean_core
```

### 6.3 Walk-forward / refit protocol (from `rv_eval/config.py`)

| Setting | Value | Meaning |
|---|---|---|
| `HORIZONS` | `(1, 5, 10, 22, 42)` | **22 is primary** (≈30 DTE). |
| `OOS_START` | `2018-01-01` | No model ever trains on `date ≥` this in OOS folds. |
| `REFIT_FREQ` | `monthly` (~101 folds) | Components re-fit OLS monthly; the ensemble re-combines monthly. |
| `TRAIN_WINDOW` | `expanding` (`lo=0`) | Each refit uses all panel history before the test block (RV back to ~2003, IV ~2007). |
| `MIN_TRAIN_DAYS` | `252×3` | ≥3y required before the first OOS fold. |
| Embargo / purge | `max(EMBARGO_EXTRA=1, h)` | **Essential at h=22** — the 22-day forward target overlaps across days; purge+embargo prevents leakage. |
| `min_obs` (components) | 100 | Per (ticker,horizon) OLS requires ≥100 rows or that key is skipped. |

**Live cadence.** On each monthly refit: rebuild the feature matrix, re-fit the four components'
per-(ticker,horizon) OLS on the expanding window (with purge+embargo before the prediction block),
write their parquets, then run the ensemble combiner. End-to-end this is **seconds** of compute — the
entire production path is linear and CPU-only.

### 6.4 Universe routing

- **Clean-core / liquid names** (SPY, QQQ, IWM, XLK, XLF, XLE, TLT, GLD, HYG, EEM): use EnsembleTopK
  directly. HAR-X is the graceful-degrade fallback if a component is unavailable.
- **Hard / short-history names** (IBIT, MSOS-type thin tickers): layer the **pooling sleeve**
  (`HAR-Shrink2Group` primary, `PanelHAR-FE` as the aggressive bound) — these are the only iter-2
  models that DM-significantly beat the incumbent on hard_cases (p=0.0009 / 0.008) and improve thin-name
  calibration. Do **not** use the pooling models on clean_core (they regress there).

---

## 7. Validation checklist before each deployment

1. **Component parquets fresh and present** — all four of `HARQ/HAR-RS/HAR-CJ/HAR-RS-IV-Q.parquet`
   updated for the new fold; ensemble must read current files (it silently skips a missing component,
   so a stale/absent file degrades the mean without erroring).
2. **`n_comp ≥ 2` everywhere it matters** — confirm no unexpected key drops (historically 0 dropped).
3. **Sanity on outputs:** `rv_hat > 0` and finite; quantiles monotone `q05 ≤ … ≤ q95` (guaranteed by
   construction but verify after any code change); `sigma ≥ 0`.
4. **Calibration drift:** spot-check rolling cov90 stays near 0.90 (it ran 0.927 clean / 0.882 hard).
   A drift well below 0.90 means the intervals went over-confident — investigate the component σ's.
5. **No new §6 post-shock trap** in the latest fold.
6. **Never combine a blow-up model in.** The component list is fixed to the four HAR models precisely
   because `RealizedGARCH` (rv_hat up to ~1e21) and `GuyonLekeufackPDV` dragged the arithmetic mean to
   ~1e18 in the first swarm pass. If you ever edit `COMPONENTS`, keep level-space blow-ups out.

---

## 8. Why these four — and why equal weight

- **Why drop the others.** The first swarm pass equal-weighted all 8 non-baseline candidates. Because
  the combiner is an **arithmetic mean in level space**, the two numerically divergent models
  (`RealizedGARCH`, `GuyonLekeufackPDV`) dominated the mean and scored the ensemble worse than a random
  walk. They were **excluded, not clipped**. `XGBoost` and `LSTM` were also dropped: no blow-up, but
  they trail the HAR-family four by a clear margin (pooled QLIKE ~0.32–0.36 vs ~0.29–0.32) and only
  dilute the combiner. What remains is the genuine top-K.
- **Why equal weight.** It is parameter-free (nothing to overfit, nothing to refit, no leakage
  surface), and at h=22 it empirically matches or beats the learned-weight alternative. The four
  components are tightly clustered in skill and diverse in mechanism, so equal weighting is close to
  optimal and far more robust than estimating 4 weights on noisy h=22 errors.

---

## 9. Does it make sense that combining these four wins? (and why not one big regression?)

**Short answer: yes — but for a specific reason that is worth being precise about.** The four models
do **not** each forecast a *disjoint piece* of RV that you then sum. All four predict the **same
target** (forward realized variance `RV_{t,t+h}`). What differs is the **view of the past** each one
uses, so their forecast *errors* are imperfectly correlated — and averaging imperfectly-correlated
forecasts of the same quantity is the classic variance-reduction win (Bates-Granger 1969; the
"forecast combination" literature).

### 9.1 Do they predict "different parts of RV"?

Not additively — but they are **specified differently**, and each captures a different way RV can be
mispredicted:

| Component | The "view" it takes of the same RV | When it is the *right* view |
|---|---|---|
| **HARQ** | RV lags, **discounted when the RV estimate itself was noisy** (measurement-error view). | Days after a noisy/illiquid session, where raw `RV_{t-1}` over-drives a plain HAR. |
| **HAR-RS** | RV split by **return sign** (down vs up semivariance) + jump. | Leverage/fear regimes where downside drives persistence and upside is spurious. |
| **HAR-CJ** | RV split into **smooth (continuous/bipower) vs transitory (jump)** parts. | After isolated jumps that a plain HAR would wrongly extrapolate. |
| **HAR-RS-IV-Q** | All of the above **plus the market's forward IV/VIX view**. | When option markets already price a vol move the realized history hasn't shown yet. |

So the mean is "more reasonable" not because each predicts a separate component, but because **no
single decomposition is correct all the time** — averaging them diversifies *specification error*. On
a quiet day the four nearly agree (the mean ≈ any one of them); when they disagree — exactly the
uncertain days — the mean hedges across views and the **between-model dispersion term widens the
predictive interval honestly** (§2, §4.2). That second effect is the ensemble's most distinctive edge.

### 9.2 Be honest about the size of the win

The four are **highly correlated** — they are all per-(ticker, horizon) log-OLS HAR variants sharing
the same `log_rv_d/w/m` backbone. So the diversification benefit is **real but bounded**, and the
evidence shows exactly that:

- On **raw h=22 QLIKE** the ensemble does *not* meaningfully beat its best member or plain HAR — all
  sit in one MCS tie-set (§1, §5). The combination does **not** manufacture accuracy out of nothing.
- Where it *does* win is on the axes combination theory predicts: **best pooled QLIKE across horizons**
  (variance reduction helps most at the short end where there is signal to average), **best-behaved
  calibration** (the `var(means)` term → honest intervals, which a single regression cannot produce —
  its `sigma` is just its own residual std and understates model uncertainty), and **robustness across
  clean + hard universes** with **no post-shock trap**. Downstream, those translate into the best
  Stage-1 tail control.

In other words: the ensemble buys **robustness and calibration more than raw point accuracy** — which
is precisely what a short-vol book consuming `sigma` for gating and sizing needs.

### 9.3 Why not just fit one regression on all regressors?

This was **tested directly, and the kitchen-sink answer lost** — three independent results:

1. **HAR-RS-IV-Q already *is* "the big linear model."** It stacks all 14 cheap informative regressors
   (RS + jump + IV/VIX block + quarticity) into one OLS. It is one of the four — and on clean_core it
   is **slightly worse than plain HAR at h=22** (0.3458 vs 0.3232). More regressors did not help at the
   primary horizon; it earns its keep at the *short* end and inside the ensemble, not as a standalone
   h=22 forecaster.
2. **HAR-MAX is the literal "all regressors" model and it was the worst non-broken model.** Iter-2
   built a deliberate kitchen-sink OLS on the **union of ~31 regressors**. It was the **worst** model
   on hard_cases (QLIKE 0.405 vs HAR 0.299) and overfit exactly as designed. With limited per-ticker
   history, 31 collinear regressors blow up coefficient (estimation) variance — the forecast gets
   *worse*, not better.
3. **Explicit shrinkage repairs the overfit but only ties the incumbents.** `HAR-ENet`/`HAR-Ridge`
   (penalized OLS on the HAR-MAX matrix) fix HAR-MAX (hard 0.289/0.303 vs 0.405) — confirming the
   overfit diagnosis — but at h=22 they only **tie** the simple incumbents while costing ~100× more
   compute. They were kept as ensemble *components*, never shipped standalone.

**The mechanism:** with only hundreds-to-thousands of rows per (ticker, horizon) and highly collinear
vol regressors, a single all-in OLS is a **high-variance** estimator. Averaging four smaller,
differently-specified fits is a form of **implicit regularization / bagging** — it cuts that variance
without the tuning, leakage surface, or cost of one big penalized regression. It is cheaper *and* more
robust than the alternatives that were actually built and measured.

> **Corollary (why equal weight, not learned weights):** estimating combination weights is itself a
> high-variance regression on noisy h=22 errors. Iter-2's `EnsembleTopK-v2` did exactly that
> (regime-conditional softmax weights) and **did not beat** the equal-weight mean (§10) — the
> "forecast combination puzzle" in miniature. Equal weights are the right default when the members are
> similar in skill and the weights would have to be learned from little data.

### 9.4 Would adding more models (K = 5, 6, …) help?

**For the clean-core global ensemble: almost certainly not — and the project already ran the
experiment.** The component count went the *other* way: the first swarm pass used **K = 8** (all
non-baseline candidates) and it scored **worse than a random walk**, because the level-space mean is
dragged by any divergent member. Pruning to **K = 4** is what produced the winner. So more members has
already been shown to hurt here, for two distinct reasons:

1. **Diminishing returns are near-saturated, because the four are highly correlated.** For an
   equal-weight mean of `n` forecasts with average pairwise error-correlation `ρ` and similar error
   variance `σ²`, the variance of the combined error is `σ²·[ρ + (1−ρ)/n]`. The four HAR variants
   share the `log_rv_d/w/m` backbone, so `ρ` is high (~0.9+). At `ρ = 0.9`: going `n = 4 → 6` moves the
   bracket only `0.925 → 0.917` — a **<1% variance gain in the best case**, and that case assumes the
   new member is *equally skilled*. The correlation floor `ρ`, not `n`, dominates — you cannot average
   your way past it by adding more of the same family.
2. **Any added member that is weaker just dilutes (and equal weight has no defense).** This is exactly
   why `XGBoost` and `LSTM` were dropped from the pool: no blow-up, but they trail the four by a clear
   margin (pooled QLIKE ~0.32–0.36 vs ~0.29–0.32), so equal-weighting them in **raised** the mean
   error. With equal weights, a 5th model helps only if it is **both** comparably skilled **and**
   meaningfully decorrelated from the existing four. No model in the current candidate set is both.

**What a productive 5th member would have to look like.** A genuinely *decorrelated*, comparably-skilled,
level-stable forecaster — e.g. a different data modality (order-flow, a calibrated nonlinear model that
*actually* beats HAR, an IV-surface model) whose errors are low-correlation with the HAR family. The
candidates that exist are the wrong shape:

| Candidate to add | Why it does *not* earn a global K=5 slot |
|---|---|
| `HAR-ENet` / `HAR-Ridge` / `HAR-CSR` | Built on the same (overlapping) HAR feature matrix → high error-correlation with the four; only *tie* the incumbents at h=22. Near-redundant; minimal diversification. |
| `XGBoost` / `LSTM` | Decorrelated-ish (nonlinear/recurrent) but **trail** on skill and **under-cover** their intervals → dilution + worse calibration. |
| `EnsembleTopK-v2` | An ensemble of (mostly) the same pool — averaging it in is double-counting, and it already failed to beat v1 (§10). |
| `RealizedGARCH` / `PDV` | Level-space **blow-ups** — the original reason K shrank from 8 to 4. Never re-add to a mean-in-level combiner. |

**The one place "more models" *does* pay is not a bigger K — it's segmentation.** The pooling models
(`HAR-Shrink2Group`, `PanelHAR-FE`) genuinely beat the incumbents, but **only on data-starved hard-case
names**, and they **regress on clean_core**. Equal-weighting them into the global ensemble would help
hard names and hurt clean ones. The correct design — and what the study adopted — is to **route** them
as a separate **hard-case sleeve** (§6.4), not to raise K on the clean-core combiner. Segment by
regime/universe where a model has a real edge; don't dilute one global average.

**Practical guidance if you still want to grow the ensemble:**
- Screen any candidate on **error-correlation vs the existing four** first; reject if `ρ` is high
  (it adds cost, not diversification).
- Require it to be **at least as skilled** as the current weakest member on pooled QLIKE *and* not
  under-cover its intervals — otherwise equal weight will dilute.
- Confirm it is **level-stable** (no `rv_hat` blow-ups) before it touches a mean-in-level combiner; or
  switch the combiner to **median / log-space mean**, which is robust to a single divergent member and
  would let you relax that constraint.
- If members differ materially in skill, prefer **skill-screened selection or shrinkage-to-equal
  weights** over naive equal weight — but note v2 tried learned weights and lost, so the bar is high.

**Bottom line:** raising K from 4 to 5–6 with the available models is expected to be flat-to-negative —
the diversification is saturated and the spare candidates are either redundant or weaker. The higher-EV
moves are (a) a *segmented* pooling sleeve for thin names (already done), and (b) sourcing a genuinely
decorrelated new forecaster before expanding the global average.

---

## 10. EnsembleTopK vs EnsembleTopK-v2 — why v1 is the production model

Iteration-2 built `EnsembleTopK-v2` (`candidate_models/ensemble_top_v2.py:EnsembleTopKV2`) to try to
improve the combiner: a 15-model eligible pool, **per-horizon top-5 selection by trailing
discounted-MSE**, and **regime-conditional inverse-MSE softmax weights** per (horizon, IV-percentile
bucket) with a 252-day half-life. It is fully leakage-safe (weights estimated only on purged
`y_train`).

**It was rejected.** Verdict (`iter2_verdicts.md` #21): *"does NOT beat iter-1 equal-weight
EnsembleTopK."* Specifically at h=22: v2 QLIKE clean **0.3458** vs v1 **0.3241** (v2 is worse), and v2
sits inside the same MCS tie-set with no §5 gain. The added complexity bought nothing at the primary
horizon. **Use the simple equal-weight v1.** The regime weights remain a useful diagnostic (which
family dominates per regime) but are not worth shipping.

---

## 11. Limitations & production cautions

- **No mean-alpha over IV² at 30 DTE.** Budget the edge as tail control via the gate/σ-sizing, not
  directional VRP. The §5 collapse is robust and was confirmed by two failed iter-2 attacks.
- **Absolute Sharpe bar not cleared.** Best deflated Sharpe is 0.68 (< 0.95) on ~125 monthly h=22
  observations — a real power limit. Treat promotions as conditional and confirm under true option
  marks (Stage-2 ORATS, `stage2_trade_eval/`).
- **Mild negative bias (−0.10 to −0.17 at h=22)** — the ensemble slightly under-predicts RV, the
  dangerous direction for short puts. The gate is what compensates; do not run the book ungated at
  30 DTE (A2: removing the gate blows drawdown up ~8×).
- **Do not run it "managed" (daily re-gating) at h=22** — Stage-1 A9 found it churns the book and
  gives back return there. Run hold-to-expiry at 30 DTE.
- **Coverage is per-model.** All QLIKE/coverage numbers are over each model's own covered cells;
  IV-dependent components shorten coverage on short-IV-history names (IBIT/MSOS) — route those to the
  pooling sleeve.
- **Stage-1 costs are a variance-proxy abstraction** (break-even ~312 bps is optimistic); real
  bid/ask, slippage, and short-gamma roll cost are only tested in Stage-2 ORATS.

---

## 12. File / source map

| Thing | Path |
|---|---|
| Ensemble implementation | `candidate_models/ensemble_top.py` (`EnsembleTopK`, `COMPONENTS`, `MIN_COMPONENTS=2`) |
| Component models | `candidate_models/{harq.py, har_rs.py, har_cj.py, har_rs_iv_q.py}` |
| Base classes (OLS, quantiles) | `rv_eval/model_contract.py` (`_LinearLogHAR`, `_PerKeyModel`, `_lognormal_quantiles`) |
| Features | `rv_eval/features.py` (`HAR_FEATURES`, `HARQ_FEATURES`, `HAR_RS_FEATURES`, `IV_FEATURES`) |
| Universe / horizons / OOS protocol | `rv_eval/config.py` |
| Walk-forward harness | `rv_eval/walkforward.py` |
| Self-stats cards | `candidate_models/cards/EnsembleTopK.md` (+ `.hard_cases.md`) and each component |
| Iter-1 forecasting comparison | `execution/reports/FINAL_MODEL_COMPARISON_REPORT.md` |
| Iter-2 forecasting comparison | `execution/reports/ITER2_FINAL_MODEL_COMPARISON_REPORT.md`, `iter2_verdicts.md` |
| Stage-1 trading eval | `trade_eval/reports/STAGE1_RESULTS_REPORT.md` |
| Downstream trading plan | `planning_docs/execution/rv_trading_eval_plan.md`; Stage-2: `stage2_trade_eval/` |
| Predictions (output) | `execution/data/predictions/EnsembleTopK.parquet` |

---

_Conclusion: the "EnsembleTopK wins at h=22" finding is consistent across the iter-1 forecasting eval,
the iter-2 forecasting eval (which explicitly could not beat it), and the Stage-1 trading eval (which
promoted it as the Stage-2 primary). It is a parameter-free equal-weight mean of four per-(ticker,
horizon) log-OLS HAR forecasts; it needs no calibration and no per-feature training; its production
value at 30 DTE is left-tail control through the downstream gate and σ-sizing, not directional alpha
over IV²._
