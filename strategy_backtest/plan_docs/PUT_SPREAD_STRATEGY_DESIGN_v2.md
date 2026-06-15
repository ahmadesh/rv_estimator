# Put-Spread Strategy — Backtest Design Specification (v2)

_Refinement of `PUT_SPREAD_STRATEGY_DESIGN.md` · compiled 2026-06-06 · repo git `d438fd8`_

> **What changed from v1.** v2 is a deliberate **simplification**. The 9-gate entry stack collapses to a
> **4-gate lean core** (the rest become a single optional stress composite); VRP stops being a gate and
> becomes a sizing tilt; **hold-to-expiry is the primary exit** (managed is a challenger that must beat it);
> the tail/q95 machinery is deferred to a one-paragraph note; and three things become **mandatory**: the
> forecaster-attribution ablation, statistical-power reporting (trade count + bootstrap CIs), and disclosure
> of the backtest's known optimistic biases. The motivation throughout: the edge is small and
> power-limited (best Stage-1 DSR 0.68 on ~125 obs), so every standing knob must earn its degree of freedom.

> **Purpose.** A single, self-contained design for backtesting a **defined-risk put-credit-spread**
> short-volatility book, gated by the **EnsembleTopK** 22-day RV forecaster plus a small regime stack and a
> layered exit framework. **Design spec only — no code.** It is a parameterization of the existing
> `stage2_trade_eval/` engine; the data layer lives in `BACKTEST_DATA_SPEC.md`.

> **Scope note.** A **put-credit spread** (sell ~25Δ put, buy ~10Δ wing), *not* a naked put or strangle.
> The wing is load-bearing: the forecaster's documented value is **left-tail control**, not directional
> alpha (`ENSEMBLETOPK_PRODUCTION_GUIDE.md` §0, §4.3), so the structure must itself cap the tail.

---

## 0. TL;DR

- **What:** Sell a 30-DTE put-credit spread on each of 10 core ETFs whenever a **lean** regime stack says
  the variance-risk premium (VRP) is being paid and the regime is benign. **Hold to expiry** (primary).
- **Universe:** SPY, QQQ, IWM, XLK, XLF, XLE, TLT, GLD, HYG, EEM — exactly `rv_eval.config.CLEAN_CORE`.
- **Data:** raw-only mirror under `strategy_backtest/back-test-data/`, features rebuilt + HARs trained
  walk-forward, no cached artifacts (`BACKTEST_DATA_SPEC.md`).
- **Forecaster:** EnsembleTopK at **h=22 (≈30 DTE)**, expanding window, monthly refit, min 3y (§3).
- **Entry gate — lean core, 4 primary (all must pass):** term structure in **contango** · forecast
  **dispersion not hot** · **liquidity/credit-width OK** · **IVrank ≤ 85** (single avoid cut). VRP is a
  **sizing tilt, not a gate**. A 5-signal **stress composite** is ablation-only. §4.
- **Exit:** **hold-to-expiry is primary.** A mechanical managed arm (50% PT · 21-DTE tighten / 12-DTE close
  · variance stop · 2× hard stop · term-flip with 2-day confirm) is a **challenger that must beat hold under
  real marks.** §5.
- **Strikes:** short **0.25Δ** put, long **0.10Δ** wing; credit/width ≥ 0.20. §6.
- **Sizing:** fractional Kelly on the VRP edge, inverse-risk (∝ vrp/σ²) — gradation is continuous, so there
  is no separate "reduce" tier — ~1% NAV risk/trade, per-correlation-group margin cap 20% NAV. §7.
- **Promotion test (the headline ablation):** the forecaster ships **only if** adding it (σ-sizing +
  dispersion gate) beats the **same regime stack with the model off** on the tail — by a **bootstrap CI**,
  not a point estimate. §8.

---

## 1. Strategy thesis

A **conditional short-variance** position. Implied variance (IV²) is on average richer than subsequently
realized variance — the variance risk premium. A put spread monetizes it on the downside, where the premium
is largest (put skew) and where the long wing converts an unbounded tail into a known, capped loss.

Two facts from the upstream research shape every choice:

1. **No reliable directional edge over IV² at 30 DTE** (sign_acc ≈ 0.52; guide §5). The book does **not**
   predict which way vol goes; it decides **when to be in the trade and how big**.
2. **The economic value is second-moment / left-tail control.** Stage-1: the gate + σ-sizing cut CVaR95
   −0.064 → −0.018 and maxDD 0.203 → 0.051 vs an ungated IV-only book, at slightly lower mean return. The
   book decorrelates in stress (guide §0, §4.3, §5).

Corollary: **the gate and the wing carry the strategy.** Every gate is a filter for "is the VRP actually
being paid, or am I about to be run over?" — and because the edge is *avoidance*, v2 keeps only the gates
that carry **independent, non-redundant** avoidance information (§4).

---

## 2. Universe and backtest window

### 2.1 Universe (10 core ETFs)

| Ticker | Sleeve | Correlation group (`rv_eval.config.GROUP`) |
|---|---|---|
| SPY, QQQ, IWM | Broad equity | equity-beta |
| XLK, XLF, XLE | Sectors | sector |
| TLT | Rates | rates |
| GLD | Metals | commodity |
| HYG | Credit | credit |
| EEM | Intl equity | intl |

Exactly `CLEAN_CORE` — the names the guide routes directly to the ensemble (§6.4). The group tag drives the
margin cap in §7.

### 2.2 Window — two segments, the GFC as a **co-equal stress test**

- **Option chains start 2007** (hard floor — no spread before that).
- **The IV-aware component + `MIN_TRAIN_DAYS=252×3` push the first fully-trained fold to ≈2010–2011.**

| Segment | Window | Forecaster state | Role |
|---|---|---|---|
| **GFC stress test** | 2007 → ~2010 | RV-only / IV-block immature | **Degraded book** (gate on contango + IVrank + liquidity; flat or IV-sized). **Co-equal stress test, not a sidebar** — the GFC is the single richest left-tail episode we have. |
| **Headline OOS** | ~2010 → present | full EnsembleTopK, expanding | Primary book, full lean-core gate. |

**Pre-commitment (new in v2):** the headline window (2010→) contains only ~2–3 independent crash episodes,
so much of the genuine tail information lives in the GFC segment. **If the GFC degraded-gate run contradicts
the post-2010 headline on the tail, the headline tail metric is down-weighted, not the GFC.** Do **not**
lower `MIN_TRAIN_DAYS` to manufacture a 2007 forecast (it would train on 1–2y and leak regime-overfit
garbage into the crisis we most need to measure honestly).

> `OOS_START` is extended earlier for this backtest only; the frozen forecasting evaluation is unchanged.

---

## 3. The forecaster — EnsembleTopK (complete spec)

Everything needed to build and run the forecaster is here; no need to consult the production guide.

### 3.1 What it is

A **parameter-free, equal-weight combiner** over **four** already-trained HAR-family log-OLS forecasters.
`fit()` is a no-op; `predict()` reads the four components' prediction files and averages them in
level/variance space. No weights, no seed, no calibration layer — deterministic. **Components (fixed):**
`HARQ`, `HAR-RS`, `HAR-CJ`, `HAR-RS-IV-Q`.

Each **component** is an independent OLS of `log(forward realized variance)` on an intercept + its feature
list, fit **per (ticker, horizon)** (10 tickers × 5 horizons = 50 fits/component), emitting the
lognormal-mean-corrected point forecast `rv_hat = exp(μ̂ + ½ŝ²)` and `sigma` from the OLS log-residual std.
No component has a tunable hyperparameter; `min_obs = 100` rows per (ticker,horizon) or that key is skipped.

**Feature constants** (from `rv_eval/features.py`, built PIT from `inputs.parquet`):

```
HAR_FEATURES    = [log_rv_d, log_rv_w, log_rv_m]
HARQ_FEATURES   = HAR_FEATURES + [sqrt_rq]
HAR_RS_FEATURES = [log_rv_d, log_rv_w, log_rv_m, rs_minus_5d, rs_plus_5d, jump_5d]
IV_FEATURES     = [log_iv, iv_slope, skew_25d, vix, vix3m, vix_slope, vvix]
```

| Component | Features (exact) | View |
|---|---|---|
| **HARQ** | `log_rv_d, log_rv_w, log_rv_m, sqrt_rq` (4) | HAR + quarticity: downweights `RV_{t-1}` when that day's RV was a noisy estimate |
| **HAR-RS** | `+ rs_minus_5d, rs_plus_5d, jump_5d` (6) | RV split into down/up semivariance + jump (downside predicts; upside/jumps less) |
| **HAR-CJ** | `log_rv_d/w/m + log_bv_d, log_bv_w, log_bv_m, log_jump_d` (7) | continuous (bipower) vs transitory (jump) split |
| **HAR-RS-IV-Q** | RS/jump + full IV block + `sqrt_rq` (14) | the only **IV-aware** component — gives the short-horizon edge |

**Regressor definitions.** All are point-in-time (trailing windows known at the row's date), built by
`rv_eval/features.py` from realized measures in `inputs.parquet` (`setup/measurement.py`) and IV features
(`setup/iv_features.py`). `RV` = daily total realized variance = sum of 5-min intraday squared returns +
overnight, Hansen-Lunde scaled.

| Regressor | Definition | What it captures |
|---|---|---|
| `log_rv_d` | log of `rv_d` = today's daily RV | short-memory term — yesterday's vol, strongest single predictor |
| `log_rv_w` | log of `rv_w` = trailing **5-day** mean of daily RV | weekly vol level — smooths daily noise |
| `log_rv_m` | log of `rv_m` = trailing **22-day** mean of daily RV | monthly vol level — slow-moving regime |
| `sqrt_rq` | √ of realized quarticity `rq = (n/3)·Σ r⁴` (clipped ≥ 0); RQ = variance *of* the daily RV estimate | downweights `RV_{t-1}` on noisy/illiquid days → fixes measurement-error attenuation |
| `rs_minus_5d` | 5-day mean of **downside** semivariance `rs_minus = Σ r²·1(r<0)` | downside vol strongly predicts future vol (leverage/fear) — most put-relevant |
| `rs_plus_5d` | 5-day mean of **upside** semivariance `rs_plus = Σ r²·1(r>0)` | upside vol predicts much less; separating it sharpens the forecast |
| `jump_5d` | 5-day mean of jump component `jump = max(rv_intraday − bv, 0)` | discontinuous jumps are largely transitory → small own coefficient |
| `log_bv_d/w/m` | log of trailing 1/5/22-day means of **bipower variation** `bv` (jump-robust continuous variance). *HAR-CJ only* | the smooth, persistent part of vol that carries forward |
| `log_jump_d` | log of today's jump component. *HAR-CJ only* | the daily transitory jump, modeled separately from `log_bv_*` |
| `log_iv` | log of `iv_30d` = ticker's own **30-day ATM implied vol** (interpolated from its chain) | the market's 30-day vol forecast — directly relevant to the 30-DTE book |
| `iv_slope` | `iv_90d − iv_30d` — ticker's **IV term-structure slope** | up/down slope = mean-reverting vs rising regime signal |
| `skew_25d` | `put25 − call25` — the **25-delta risk reversal** (put IV − call IV) | steeper put skew = more priced crash risk = higher future-vol probability |
| `vix` | SPX 30-day ATM IV (VIX analog, same construction) | market-wide vol level — systematic vol factor common to all names |
| `vix3m` | SPX 90-day ATM IV (VIX3M analog) | market-wide vol level at the longer tenor |
| `vix_slope` | SPX `iv_90d − iv_30d` — **VIX term-structure slope** | inverted (backwardated) VIX curve flags acute market stress |
| `vvix` | the VIX index's own 30-day ATM IV — **vol-of-vol** | how uncertain the market's vol forecast is; rises before regime shifts |

> Also produced by `features.py` but **not used by these four components** (they feed the RandomWalk/EWMA
> benchmarks): `rv_q`/`log_rv_q` (66-day quarterly HAR lag) and `ewma_rv` (RiskMetrics λ=0.94 EWMA of RV).

> **HAR-CJ build gotcha.** Its `log_bv_*` roll-means and `log_jump_d` must be built **once over each
> ticker's full series** (from `inputs.parquet`) and left-joined onto each fold slice by `(ticker, date)`.
> Do **not** recompute `rolling_mean(22)` on a per-fold slice — it nulls the leading 21 rows and silently
> drops them.

### 3.2 Combiner math & output contract

For each `(ticker, date, horizon)` key, over components with finite `rv_hat > 0`, `sigma ≥ 0`:

```
rv_hat = mean(component rv_hat)                       # equal weight, LEVEL (variance) space
sigma  = sqrt( mean(component_sigma²) + var(component rv_hat, ddof=0) )
                                                      # within-model + between-model dispersion
s      = sqrt(log(1 + (sigma/rv_hat)²))              # back out log-space sd
q05, q10, q90, q95 = lognormal_quantiles(m = rv_hat, s = s)   # tails only; monotone by construction
```

- Keep a key only if **≥ 2 components** present (`MIN_COMPONENTS = 2`); else **drop, never impute**
  (historically 0 dropped — all 4 nearly always present).
- The `var(component rv_hat)` term **widens the interval when the four views disagree** — this is the
  calibration property the gate/sizer consume.
- **Emit only the four tail quantiles** `q05, q10, q90, q95`. The strategy consumes `rv_hat` and `sigma`
  directly (gate + sizing); the central quantiles `q25/q50/q75` are unused — drop them. `q90/q95` are carried
  only for the deferred upper-tail work / calibration check (§6, §3.5), not load-bearing in v1.

**Output contract** (one row per key):

| Field | Meaning | Units |
|---|---|---|
| `rv_hat` | point forecast of forward RV = `E[Σ_{s=t+1..t+h} RV_s]` | variance (vol = `√(rv_hat·252/h)`) |
| `sigma` | predictive **sd of `rv_hat`** (model's uncertainty about its own forecast — *not* the vol being forecast) | same as `rv_hat` |
| `q05, q10, q90, q95` | lognormal tail quantiles of forward RV (`q05`/`q95` = 90% interval edges; lower tails informational, upper tails for §6) | same as `rv_hat` |

> **Production expectations (budget the edge correctly).** At h=22 `rv_hat` carries **no mean-alpha over
> IV²** (sign_acc ≈ 0.52) — do not deploy for directional VRP. The value is **left-tail control via the G4
> gate + σ-sizing** (Stage-1: CVaR95 −0.064→−0.018, maxDD 0.203→0.051). `rv_hat` is **biased low** (−0.10
> to −0.17) — the dangerous direction for short puts — which is *why* the book is never run ungated (A2:
> removing the gate blows drawdown ~8×) and why VRP is a tilt not a veto (§4.2).

### 3.3 Training & refit protocol

| Setting | Value | Meaning |
|---|---|---|
| `HORIZONS` | `(1, 5, 10, 22, 42)` | **22 is primary** (≈30 DTE) |
| `REFIT_FREQ` | monthly | components re-fit OLS monthly; ensemble re-combines monthly (matches the 22-day roll) |
| `TRAIN_WINDOW` | **expanding** (`lo=0`) | each refit uses all panel history before the test block |
| `MIN_TRAIN_DAYS` | `252×3` | ≥3y before the first OOS fold |
| Purge / embargo | `max(EMBARGO_EXTRA=1, h) = 22` | **mandatory at h=22** — the 22-day forward target overlaps across days; purge+embargo before each prediction block prevents leakage |
| `min_obs` | 100 | per-(ticker,horizon) OLS minimum rows |

**Why expanding, not rolling:** HAR betas are structurally stable (the regime lives in the *features*
rv_d/w/m, not the betas), so more data lowers OLS variance — the documented failure mode is estimation
variance, not staleness; and expanding gives a smooth σ so the dispersion gate doesn't chatter. **Robustness
ablation:** 8-year rolling, monthly. Match → ship expanding; if 8y-rolling materially improves the post-2020
tail → adopt expanding with a ~10y soft cap. Do **not** ship a ≤3y rolling window.

### 3.4 Build order & commands (per fold; CPU-only, seconds)

Components must exist on disk **before** the ensemble (it silently skips a missing component → degraded
mean, no error). Use `.venv/bin/python` (system python lacks polars).

```
inputs.parquet + targets.parquet  →  features.build_features()
  →  HARQ, HAR-RS, HAR-CJ, HAR-RS-IV-Q   (4 components, each per-(ticker,horizon) log-OLS)
  →  EnsembleTopK.predict()              (equal-weight mean → predictions/EnsembleTopK.parquet)
```

```bash
.venv/bin/python -m rv_eval.walkforward --model candidate_models.harq:HARQ            --universe all
.venv/bin/python -m rv_eval.walkforward --model candidate_models.har_rs:HARRS         --universe all
.venv/bin/python -m rv_eval.walkforward --model candidate_models.har_cj:HARCJ         --universe all
.venv/bin/python -m rv_eval.walkforward --model candidate_models.har_rs_iv_q:HARRSIVQ --universe all
.venv/bin/python -m rv_eval.walkforward --model candidate_models.ensemble_top:EnsembleTopK --universe all
```

> For this backtest, features and all four components are **rebuilt per fold from the raw mirror** (no cached
> `inputs/features/targets/predictions`) — see `BACKTEST_DATA_SPEC.md`. Universe is `CLEAN_CORE` (all 10
> names route directly to EnsembleTopK; HAR-X is the graceful-degrade fallback if a component is missing — no
> hard-case pooling sleeve is needed for this universe).

### 3.5 Per-fold validation checklist

1. All four component parquets fresh & present (a stale/absent one silently degrades the mean).
2. `n_comp ≥ 2` for every key (no unexpected drops).
3. Outputs sane: `rv_hat > 0` finite, `sigma ≥ 0`, tail quantiles monotone `q05 ≤ q10 ≤ q90 ≤ q95`.
4. Calibration drift: rolling `cov90` near 0.90 (ran 0.927 clean; well below 0.90 = intervals went
   over-confident → check component σ's). Upper-tail (right-side) hit rate per ticker is **not** certified by
   cov90 — see the deferred tail note in §6.
5. **Never add a level-space blow-up component.** The list is fixed to the four HAR models because
   `RealizedGARCH`/`GuyonLekeufackPDV` produced `rv_hat ~1e18–1e21` and destroyed the arithmetic mean. If
   `COMPONENTS` is ever edited, keep level-space blow-ups out (or switch the combiner to median/log-space).

---

## 4. Entry gate — lean core

A candidate entry exists for `(ticker, date)` on the **monthly roll dates** (`trade_eval.config.ROLL_CADENCE`).
It becomes a trade only if **all four primary gates pass**. Every gate is **point-in-time** (trailing windows
only; reuse `trade_eval.pit`).

> **v2 design principle.** v1 stacked 9 gates, but 7 of them are model-free and fire **together** in a crash
> — they are one stress axis measured many ways (the gate-side version of the guide's §9.4 "high-ρ members
> saturate" argument). Each redundant gate spends a degree of freedom against a tiny effective sample without
> adding independent protection. v2 keeps the **smallest set that spans the independent axes**: term
> structure (G3), forecast uncertainty (G4), tradeability (G7), and a coarse IV-stress ceiling (G2). The
> rest become **one optional composite**, screened empirically, never a standing knob.

### 4.1 The lean-core gate stack (all four must pass)

| # | Gate | Condition to **trade** | Source | Rationale |
|---|---|---|---|---|
| G2 | **IV not in stress** | `IVrank ≤ 85` (avoid above) | trailing-252d pct of `iv_30d`, PIT, per ticker | The top decile of IV is **regime stress**, not "rich vol" — VRP goes negative exactly there. A single coarse left-tail cut that needs no model. (No 25-floor "reduce" tier — sizing handles thin premium continuously, and G7 rejects un-tradeable cheap spreads anyway.) |
| G3 | **Term structure in contango** | own `iv_slope = iv_90d − iv_30d > 0` **and** `vix3m > vix` | `iv_slope`, `vix`, `vix3m` | The highest-value single short-vol filter. Backwardation = acute present-tense stress = where spreads gap to max loss. Conjunction catches single-name (own curve) *and* market (VIX) stress. (Sweep: OR variant.) |
| G4 | **Forecast dispersion not hot** | `sigma/rv_hat ≤` trailing-80th-pctile | forecast `sigma` | The validated Stage-1 gate: stand down when the forecaster is unusually unsure (regime about to break). **One of only two gates that uses the model.** |
| G7 | **Liquidity / credit quality** | every leg OI ≥ 50, rel-spread ≤ 0.35; net credit ≥ $0.05; **credit/width ≥ 0.20** | ORATS chain | Reject untradeable / no-edge-after-cost structures. (`stage2_trade_eval.config`.) |

The gate is **binary (trade / avoid)**. There is no half-size "reduce" sub-state in v2: inverse-risk sizing
(§7) already scales continuously with forecast uncertainty and VRP, so a discrete reduce multiplier is
redundant machinery.

### 4.2 VRP is a sizing tilt, not a gate (changed from v1)

v1's G1 gated on `vrp_rel ≥ −τ`. v2 **removes VRP from the gate entirely** and uses it only as the **sizing
edge** (§7), with a positive floor. Why:

- **No mean-VRP alpha at h=22** (sign_acc ≈ 0.52) — gating on the model's marginal VRP call is gating on
  noise.
- **`rv_hat` is biased low** (−0.10 to −0.17), so `vrp = iv2 − rv_hat` is biased *high* — a veto built on it
  is already optimistic in truth terms.
- A put spread also earns **drift + skew premium** that don't require IV > expected RV, so "fair vol" is a
  tradeable setup, not a stand-down.

So VRP enters as `vrp_rel = max((iv2 − rv_hat)/iv2, f)` with floor **f = 0.05**: materially-negative-VRP
names size *small*, never zero, and never get a hard veto. (Ablation: VRP-as-soft-gate `≥ −0.05` vs
tilt-only vs off — expect tilt/off to match or beat a gate, per guide §5.)

### 4.3 Optional stress composite (ablation-only — not a standing gate)

The five v1 gates that proved collinear with G2/G3 are folded into **one** composite, run **only** as an
ablation to measure whether the regime stack needs *anything* beyond the lean core:

```
stress = post_shock  OR  skew_25d > p90  OR  spot < 200d-SMA
         OR  credit_mom > p80  OR  vvix > p90       →  avoid
```

- **What `p90`/`p80` mean.** Each is the value's own **point-in-time trailing 252-day (≈1y) percentile**,
  recomputed PIT every fold (no lookahead), exactly like G2 (`IVrank`) and G4 (dispersion). So `skew_25d >
  p90` reads "today's 25Δ skew is in the top decile of *its own* trailing-year range." It is a **per-series**
  rank, not a cross-sectional or fixed-level cut: `skew_25d` is ranked **per ticker** (each name vs its own
  history); the market-wide series (`credit_mom`, `vvix`) are each ranked as a **single series** shared
  across names. Self-relative ranking auto-adapts to each name's vol/skew scale and needs no hand-set level.
  (`post_shock` and `spot < 200d-SMA` are boolean, no percentile.)
- Run the headline book **with and without** `stress`. Keep it in v1-production **only if** it cuts the tail
  *after* the lean core already fired — i.e. only if it carries independent avoidance information (§9.4
  logic applied to gates). Expectation: it is largely redundant with G2/G3 and does **not** survive.
- **`credit_mom` uses an exogenous proxy** (LQD / HY-OAS), **not HYG** — HYG is a traded name, so an
  HYG-built credit gate would be endogenous to its own trade. (`rv_eval/setup/cross_asset.py`.)

> Dropped as standing gates vs v1: the separate skew (G6), trend (G8), credit (G9), VVIX, and RV-accel
> filters, and the post-shock gate (G5) — all now live only inside `stress`.

---

## 5. Exit framework

**Hold-to-expiry is the primary arm** (the Stage-1 winner at h=22; the guide is explicit not to run the book
managed / daily-re-gated at 30 DTE — A9 found it churns and gives back return, §11). The managed arm is a
**challenger that must beat hold under real option marks** to justify its complexity — Stage-1 was a
variance-proxy abstraction, so the real-marks path (path-dependent 50% PT, terminal gamma) genuinely *might*
flip the verdict, but **that is the hypothesis under test, not an assumption.**

### 5.1 Arms

- **Primary / benchmark: `hold`** — settle at intrinsic at expiration.
- **Challenger: `mechanical_terminal`**, first-trigger-wins, evaluated daily on the mark path
  (`stage2_trade_eval.management`):

| # | Trigger | Condition | Note |
|---|---|---|---|
| X1 | Profit target | mark P&L ≥ **50%** of max credit | `TAKE_FRAC=0.50` (sweep 0.60) |
| X2 | Terminal management | soft tighten at **DTE ≤ 21**; **hard close at DTE ≤ 12** (gamma) | `TERMINAL_DTE` |
| X3 | Term-structure flip | contango → backwardation, **confirmed 2 consecutive days**, with a dead-band around 0 | **whipsaw-protected** (see below) |
| X4 | Variance stop | accrued realized var over `[t,now]` > entry `iv2` | model-free |
| X5 | Hard stop | mark loss ≥ **2× credit** (capped by the wing anyway) | rarely binds |
| X7 | Expiry | else settle at intrinsic | default |

**X3 whipsaw protection (new in v2).** v1's term-flip exit was a daily regime exit with no confirmation —
structurally the same daily-re-gating churn A9 warned about, just on a model-free signal. v2 requires the
flip to **persist 2 consecutive days** and clear a **dead-band** around the contango/backwardation boundary
before firing, and **each X3 round-trip is charged the full close+reopen spread cost** in the ledger. If X3
still churns after this, drop it (it is the most expendable trigger).

> X6 forecast-re-gate from v1 is **removed** — A9 showed daily forecast re-gating churns at h=22; it has no
> place even as a default toggle.

### 5.2 Ablation

`hold` (primary) vs `mechanical_terminal` (challenger) vs `mechanical_terminal − X3` (does the regime exit
add anything net of churn?). Managing ships **only if** it beats hold under real marks on the §8 axes.

---

## 6. Strike selection

**Short ≈ 0.25Δ put, long ≈ 0.10Δ wing**, off the entry-day ORATS chain delta; fills from that chain's
bid/ask. Reuses `stage2_trade_eval.structures.PutCreditSpread` with tuned deltas.

- **0.25Δ short** ≈ 1σ OTM — the premium-vs-safety knee (0.30Δ sits too close; 0.16Δ often fails the
  credit/width floor). Sweep {0.16, 0.20, 0.25, 0.30}.
- **0.10Δ wing** caps the exact left tail the gate avoids while keeping most of the premium. Sweep {0.07, 0.10}.
- **Delta-anchored, not fixed-dollar width** — auto-adapts to each ticker's price/vol.
- **Credit/width ≥ 0.20**, net credit ≥ $0.05 (part of G7).
- **DTE:** nearest listed expiry to **30 days**; **accept entry only in [25, 45] DTE** (raised from v1's 21
  floor so a fresh trade is never born into the 21-DTE terminal tier, §5). Outside → no trade.

The current engine ships 0.20Δ / 0.07Δ; v2 nudges to **0.25 / 0.10** with the old values inside the sweep.

**Why a spread, not a naked put:** defined risk caps the tail (the forecaster can't give directional
protection), enables a higher Kelly fraction (`KELLY_C_DEFINED=0.30` vs naked 0.15), and a clean per-group
margin budget (§7).

> **Tail/q95 strikes — deferred (was v1 §4.6).** v1 proposed placing the short strike beyond a `q95`-implied
> move. v2 **ships fixed 0.25Δ + σ-sizing** and defers this to future work, for a specific reason: `q95` is a
> deterministic lognormal transform of `(rv_hat, σ)` (guide §2) — **no new signal beyond σ** — and that σ is
> largely *between-model disagreement*, which is **tightest in the calm pre-jump days where HAR most
> under-predicts**. So a q95-conditioned strike would place maximum exposure exactly when model agreement is
> high but jump risk is not. Revisit only after (a) per-ticker **upper-tail calibration** (empirical
> `P(RV > q95)` at/below nominal) **and** (b) a **`rv_hat` de-bias** (it is biased low — the wrong way for
> short puts) both pass.

---

## 7. Position sizing

**Fractional Kelly on the VRP edge, inverse-risk, with a per-trade risk cap and a per-correlation-group
margin cap.** Reuses `trade_eval` sizing + `stage2_trade_eval.sizing` verbatim — not re-invented.

### 7.1 Sizing chain (exact)

Per candidate trade *i*, with multiplier `m = 100`, `W` = strike width and `C` = net credit (per share):

1. **Inputs:** `vrp_rel = max((iv2 − rv_hat)/iv2, f)`, `f = 0.05`; `disp = sigma/rv_hat`;
   `maxloss_c = (W − C)·m` (max loss per contract, $).
2. **Sizing multiple (inverse-risk Kelly):**
   `u = clip( c_K · vrp_rel / disp² , 0 , U_max )`, with `c_K = KELLY_C_DEFINED = 0.30`,
   `U_max = SIZE_CAP = 3.0`. The `vrp_rel/disp²` shape *is* Kelly (edge ÷ variance); `c_K` is the
   fractional haircut. The floor `f` keeps fair-vol trades at a baseline size for their drift+skew premium
   (§4.2). *This continuous `u` is why v2 has no discrete "reduce" tier.*
3. **Target dollar risk:** `R = u · b · NAV`, with `b = RISK_BUDGET = 0.01`.
4. **Raw contracts:** `n_raw = R / maxloss_c = u·b·NAV / [(W−C)·m]`.
5. **Group cap, then round:** scale a group pro-rata if `Σ_{i∈g} n_i·maxloss_c,i > 0.20·NAV`; then
   `contracts = floor(n_raw)`, skip if `floor → 0`.

At the documented calibration the **typical** `u ≈ 0.33` (median `vrp_rel ≈ 0.10`, `disp ≈ 0.30`), so the
median trade risks ~0.33% NAV, rising toward 1–3% only in target-rich (high vrp, low disp) regimes.

### 7.2 Risk caps

| Cap | Value | Why |
|---|---|---|
| Per-trade risk | ≈ **1% NAV** at one unit (`RISK_BUDGET=0.01`) | bounds single-trade damage (max loss known at entry) |
| Per-group margin | **20% NAV** per correlation group (`GROUP_MARGIN_CAP=0.20`) | the 10 ETFs cluster; correlation, not name count, sets the tail |
| Size cap | 3 units/trade | stops Kelly concentrating into one rich-looking name |

**Concentration note (new in v2).** The 20% equity-beta cap with **4 names** (SPY/QQQ/IWM/XLK) means each
equity name is effectively ≤~5%, so the book's P&L will be **driven by the singleton-group diversifiers
(GLD/TLT/HYG/EEM)**, not the core equity VRP. This is intended correlation control, but state it explicitly
and treat as a sweep whether to **sub-group equities** (broad vs sector) or modestly raise the equity cap.

### 7.3 Capital & contract granularity (the binding practical constraint)

You trade `floor(n_raw)` whole contracts, so the continuous sizer only expresses gradation if `n_raw` sits
well above 1. The driver is **max loss per contract** ≈ `13.4·IV·S`, which ranges ~14× across the universe
(and grows over the sample as prices rise):

| Names (2026 px) | maxloss/contract | Notes |
|---|---|---|
| QQQ ~$1,200 · SPY ~$1,100 | **highest** | **binding** — also squeezed by the 20% equity-beta cap |
| IWM/XLK ~$620 · GLD ~$435 · XLE ~$300 | mid | |
| TLT ~$180 · XLF/EEM ~$120 · HYG ~$85 | lowest | fine granularity at any size |

**Required NAV** for the typical trade on the binding name (QQQ, ~$1,200, `u_med ≈ 0.33`) to round to `N*`
contracts: `NAV_min = N* · maxloss / (u_med · b) ≈ N* · $364k`.

| Resolution | N* (QQQ) | NAV |
|---|---|---|
| Coarse floor | 3 | ~$1.1M |
| Workable | 5 | ~$1.8M |
| Comfortable | 8–10 | ~$2.9–3.6M |

So: **NAV ≈ $2–3M** for honest 1-contract resolution across all 10 names at current prices; **~$1M is the
floor** below which SPY/QQQ/IWM/XLK round to 0–2 contracts and σ-sizing collapses to binary on/off on the
equity-beta core. That is fatal *for this strategy specifically*, because the σ-sizing gradation **is** the
documented edge (Stage-1 A2/A3) — a sub-$1M book would not reproduce the backtest. The floor is tunable ~3×
(normalize `u_med→1` or raise `b`) but cannot be tuned past the ~$1,200/contract maxloss on QQQ; width
(wing delta) is the only structural lever. The floor was lower early in the sample (prices ~3–5× smaller),
so a fixed-NAV book gets *coarser* sizing late.

**Backtest policy (state both):**
- **Attribution run (§8.1 A-vs-B):** **fractional contracts** (NAV-independent) — isolates the sizing signal
  cleanly so rounding doesn't contaminate the forecaster-vs-regime comparison.
- **Headline economic run:** **round to contracts at a stated NAV ≥ $2M**; report the gap to the fractional
  run as the **"granularity tax."** If the rounded book loses the tail edge the fractional book showed, the
  strategy is not deployable at that size.

---

## 8. What to measure

Reuse Stage-1/Stage-2 scoring (`reports.score_stage1`: DSR, CVaR95, maxDD, AnnRet, break-even bps) so
results compare to the upstream studies. The bar is **relative** — the forecaster's thesis is tail control.

### 8.1 The headline promotion test (the decisive ablation)

Because the lean core is mostly model-free (only G4 + σ-sizing use the forecaster), "gate vs IV-only" does
**not** attribute the tail win to the model. The decisive comparison is:

| Arm | Description |
|---|---|
| **A — regime only** | full lean-core regime gates ON, **forecaster OFF**: flat size, **no G4 dispersion gate** |
| **B — regime + model** | same regime gates **+ σ-sizing + G4** |

**The forecaster ships only if B beats A** on the tail. This isolates EnsembleTopK's marginal value over the
model-free regime stack — the entire promotion thesis.

### 8.2 Statistical-power discipline (mandatory)

The headline window has ~2–3 independent crash episodes and the heavy-gate book trades a thin, serially- and
cross-sectionally-correlated sample. Point estimates on CVaR95/maxDD are **not** decision-grade. Therefore:

- **Report** post-gate **trade count** and an **effective-N** (account for block/serial dependence).
- **Report block-bootstrap CIs** on **CVaR95 and maxDD** (block to respect the 22-day overlap + regime
  persistence).
- **Promotion requires the CI** — the lower bound of B's tail improvement must beat the benchmark, not the
  point estimate.

### 8.3 Other axes & ablations

| Axis | Target |
|---|---|
| Left tail | CVaR95 / maxDD **CI** below the IV-only put-spread book |
| Risk-adjusted return | DSR ≥ IV-only benchmark; ideally beat hold |
| Stress decorrelation | cross-group P&L corr collapses in 2008 / 2020 / 2022 |

**Mandatory ablations:**
- **A vs B** (§8.1) — the promotion test.
- **Stress composite on/off** (§4.3) — does anything beyond the lean core survive?
- **Hold vs managed vs managed−X3** (§5.2).
- **VRP: soft-gate vs tilt-only vs off** (§4.2).
- **Expanding vs 8y-rolling** forecaster (§3).
- **Cost stress:** sweep `SLIPPAGE_TICKS`; report break-even cost; **wing-fill sensitivity** specifically
  (the 10Δ long is the thesis and the thinnest leg early in the sample).

### 8.4 Known optimistic biases (disclose; do not hide)

The backtest is honest about where it flatters the book:

- **EOD-only marks (ORATS SMV).** Entries, the 50% PT, and all stops are evaluated **once per day at EOD**.
  A gap-down day blows past the 2× / variance stop and the book can only act at the *next* EOD — this
  **understates the short-gamma tail**, especially in the terminal week. The DTE≤12 hard close mitigates but
  does not remove it.
- **No early-assignment / dividend timing.** ETF options are American; a short put driven deep ITM in a
  selloff (around ex-div) can be assigned early. EOD intrinsic settlement ignores assignment timing.
- **Wing-fill optimism.** "Cross the spread" on a 10Δ put in 2010–2013 for thinner names (XLE/EEM/HYG) may
  be optimistic where strikes are sparse → hence the §8.3 wing-fill sensitivity.

---

## 9. How this maps onto the existing engine (build note)

A parameterization of `stage2_trade_eval/`, not a new system.

| Design element | Existing hook | Change |
|---|---|---|
| Put spread structure | `structures.PutCreditSpread` | `SHORT_DELTA→0.25`, `WING_DELTA→0.10` |
| Lean-core gates G3/G4/G7 | `trade_eval.signals._gate_expr` / `build_signals` | reuse; drop the v1 reduce sub-states |
| Gate G2 (IVrank ≤ 85) | new | PIT `IVrank` from `iv_30d`; single avoid cut |
| VRP → sizing tilt | `trade_eval.signals` | **remove VRP from the gate**; keep as `vrp_rel` with floor `f=0.05` |
| Stress composite (ablation) | columns in `inputs` | one OR-composite, exogenous credit proxy (LQD/HY-OAS) |
| Exit: hold primary | `management.hold` | make primary/benchmark |
| Exit: managed challenger | `management.MechanicalTerminal` | `TAKE_FRAC=0.50`; 21-DTE soft tier; **X3 with 2-day confirm + dead-band + round-trip cost**; remove X6 |
| Sizing | `sizing.kelly_units` + caps | reuse; no reduce tier |
| Entry DTE floor 25 | `TARGET_DTE`/`DTE_TOLERANCE` | accept [25, 45] |
| Window 2007/2010 | `OOS_START` | extend for this backtest; GFC = co-equal stress test |
| Forecaster window | `TRAIN_WINDOW` | expanding primary; 8y-rolling ablation |
| Power reporting | `reports.score_stage1` | add trade count, effective-N, block-bootstrap CIs |

Fills, marking, greeks, settlement, ledger schema, DSR/CVaR scoring carry over unchanged.

**Forecaster source files** (§3): ensemble `candidate_models/ensemble_top.py` (`EnsembleTopK`, `COMPONENTS`,
`MIN_COMPONENTS=2`); components `candidate_models/{harq,har_rs,har_cj,har_rs_iv_q}.py`; base OLS/quantiles
`rv_eval/model_contract.py` (`_LinearLogHAR`, `_PerKeyModel`, `_lognormal_quantiles`); features
`rv_eval/features.py`; measures/IV/cross-asset setup `rv_eval/setup/{measurement,iv_features,cross_asset}.py`;
config `rv_eval/config.py`; walk-forward harness `rv_eval/walkforward.py`.

---

## 10. Resolved decisions (v2 defaults)

Set once, never tuned on OOS P&L. "Ablation" = what is *also* run; the book ships the default regardless.

| # | Decision | **v2 default** | Changed from v1? | Also run |
|---|---|---|---|---|
| 1 | Entry gate | **4-gate lean core** (G2 IVrank≤85, G3 contango, G4 dispersion, G7 liquidity) | **Yes** — was 9 gates | stress composite on/off |
| 2 | VRP | **sizing tilt only** (floor f=0.05), **not a gate** | **Yes** — was soft gate | soft-gate vs off |
| 3 | Reduce tier | **removed** — sizing is continuous | **Yes** | — |
| 4 | Exit | **hold-to-expiry primary**; managed is a challenger | **Yes** — was managed primary | managed, managed−X3 |
| 5 | X3 term-flip | **2-day confirm + dead-band + round-trip cost** | **Yes** — was bare daily | drop X3 |
| 6 | Tail/q95 strike | **deferred** (ship fixed 0.25Δ + σ) | **Yes** — was a v1 ablation | revisit post calib + de-bias |
| 7 | Term-structure (G3) | strict AND (own `iv_slope>0` *and* `vix3m>vix`) | no | OR variant |
| 8 | Profit target (X1) | 0.50 of max credit | no | 0.60 |
| 9 | Short / wing delta | 0.25Δ / 0.10Δ, credit/width ≥ 0.20 | no | short {0.16,0.20,0.30}, wing 0.07 |
| 10 | Entry DTE | **[25, 45]** | **Yes** — was [21,45] | — |
| 11 | Window | primary ~2010→; **GFC = co-equal stress test** | **Yes** — was sidebar | — |
| 12 | Forecaster window | expanding, monthly, min 3y | no | 8y rolling |
| 13 | Credit proxy (stress) | **exogenous LQD / HY-OAS** | **Yes** — was HYG | — |
| 14 | Reporting | **trade count + effective-N + bootstrap CIs**; promote on CI | **Yes** — was point estimates | — |

**Genuinely-empirical items** (decided by the ablation read-out): whether the forecaster beats the
regime-only book (§8.1, the promotion gate), whether managing beats hold under real marks (§5.2), and whether
the stress composite survives (§4.3).

---

_Conclusion: v2 is a **smaller** book than v1 by design. A defined-risk, conditionally-short-variance
put-spread on 10 core ETFs, gated by a **4-signal lean core**, sized by inverse-risk Kelly with VRP as a
tilt, **held to expiry** unless a whipsaw-protected managed arm proves it can beat hold under real marks. The
forecaster's documented strength — left-tail control via σ — is the only place the model is load-bearing, and
v2 makes the book **prove that** with an explicit regime-only-vs-model ablation judged on bootstrap CIs, not
point estimates, while honestly disclosing the EOD/assignment biases that flatter any option backtest._
