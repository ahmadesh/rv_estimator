# Put-Spread Strategy — Backtest Design Specification

_Design reference for a clean put-credit-spread backtest on the core ETF universe · compiled 2026-06-06 · repo git `d438fd8`_

> **Purpose.** A single, self-contained design document for backtesting a **defined-risk put-credit-spread**
> short-volatility strategy, gated by the **EnsembleTopK** 22-day RV forecaster plus a stack of regime
> filters (IV-percentile, term structure, dispersion, …) and a layered exit framework. This is a **design
> spec only — no code.** It defines the universe, data, training protocol, entry gates, exits, strike
> selection, and position sizing, and reasons through every open question the brief raised. It is meant to
> be the contract a subsequent implementation (built on the existing `stage2_trade_eval/` engine) is
> measured against.
>
> **Scope note.** The strategy is a **put-credit spread** (sell a ~25Δ put, buy a ~10Δ protective wing),
> *not* a naked put or a strangle. The downside wing is load-bearing: the forecaster's documented economic
> value is **left-tail control**, not directional alpha (see `ENSEMBLETOPK_PRODUCTION_GUIDE.md` §0, §4.3),
> so the structure must itself cap the tail the gate is trying to avoid.

---

## 0. TL;DR

- **What:** Sell a 30-DTE put-credit spread on each of 10 core ETFs whenever a stack of gates says the
  variance-risk premium (VRP) is being paid *and* the regime is benign. Hold to a managed exit.
- **Universe:** SPY, QQQ, IWM, XLK, XLF, XLE, TLT, GLD, HYG, EEM — exactly `rv_eval.config.CLEAN_CORE`.
- **Data:** raw-only mirror under `strategy_backtest/back-test-data/` (ORATS chains back to **2007**, minute
  bars back to 2003), copied from the Ex-Disk lakes. **No pre-built features/targets** — the pipeline
  rebuilds features and trains walk-forward (see `BACKTEST_DATA_SPEC.md`). Realistic **first OOS trade ≈ 2010** (need ≥3y train
  *and* IV-feature history, which begins ~2007). See §2.
- **Forecaster:** EnsembleTopK at **h=22 (≈30 DTE)**, refit **monthly on an expanding window** (min 3y).
  Expanding beats a short rolling window here — reasoned in §3.
- **Entry gate (all must pass):** VRP **not materially negative** (soft band, not a hard `>0` veto — §4.5) ·
  IV-percentile in a **mid-high band (avoid >85, reduce <25)** · **term structure in contango** ·
  forecast-dispersion not hot · not post-shock · liquidity OK. §4.
- **Tail forecast (the model's strength):** use `q90`/`q95` of forward RV — the up-RV tail the book is
  exposed to — for tail-conditioned strike placement / a tail gate / downside-dispersion sizing. Note q95 is
  a deterministic lognormal transform of `(rv_hat, σ)`, so it re-expresses σ in the right units, not a new
  signal; verify **upper-tail calibration per ticker** before trusting it. §4.6.
- **Exit (first trigger wins):** 50% profit · ≤21 DTE terminal management · term structure flips to
  **backwardation** · variance stop (accrued RV > entry IV²) · hard stop at 2× credit · else expiry. §5.
- **Strikes:** short **0.25Δ** put, long **0.10Δ** wing; require credit/width ≥ 0.20. §6.
- **Sizing:** fractional Kelly on the VRP edge, inverse-risk (∝ vrp/σ²), gate-scaled, ~1% NAV risk/trade,
  per-correlation-group margin cap 20% NAV. §7.
- **What success looks like:** smaller left tail (CVaR95, maxDD) than an ungated IV-only put-spread book at
  comparable or better risk-adjusted return — the same axis the forecaster won on in Stage-1.

---

## 1. Strategy thesis (why this trade, why this book)

The trade is a **conditional short-variance** position. Across equity-index and sector ETFs, implied
variance (IV²) is on average richer than subsequently realized variance — the **variance risk premium**.
Selling a put spread monetizes that premium on the downside, where the premium is largest (put skew) and
where the protective long wing converts an unbounded tail into a known, capped loss.

Two facts from the upstream research shape every design choice:

1. **There is no reliable *directional* edge over IV² at 30 DTE.** The forecaster's sign accuracy vs IV²
   at h=22 is ≈0.52 — a coin flip (`ENSEMBLETOPK_PRODUCTION_GUIDE.md` §5). So the book is **not** built to
   predict which way vol goes; it is built to **decide when to be in the trade at all and how big**.
2. **The economic value is second-moment / left-tail control.** Stage-1 showed the forecaster's gate +
   σ-sizing cut CVaR95 from −0.064 → −0.018 and maxDD from 0.203 → 0.051 vs an ungated IV-only book, at
   slightly lower mean return. The book *decorrelates in stress*. (Guide §0, §4.3, §5.)

Design corollary: **the gate and the wing carry the strategy.** We are paid the VRP in calm contango
regimes and we step aside (or are capped) in the regimes where realized variance overshoots implied — the
crashes that wreck naked short-vol books. Every gate below is a filter for "is this a regime where the VRP
is actually being paid, or one where I'm about to be run over?"

---

## 2. Universe and backtest window

> **Data layer is specified separately.** Everything about *where the data lives, what is staged, and how
> the pipeline reads it* — the raw-only `back-test-data/` mirror, ticker staging, and the
> "features rebuilt walk-forward, no cached `inputs/targets/predictions`" principle — lives in
> **`BACKTEST_DATA_SPEC.md`**. This doc assumes that mirror exists and focuses on the strategy.

### 2.1 Universe (10 core ETFs)

| Ticker | Sleeve | Correlation group (`rv_eval.config.GROUP`) |
|---|---|---|
| SPY, QQQ, IWM | Broad equity | equity-beta |
| XLK, XLF, XLE | Sectors | sector |
| TLT | Rates | rates |
| GLD | Metals | commodity |
| HYG | Credit | credit |
| EEM | Intl equity | intl |

These are exactly `CLEAN_CORE` — the liquid names the EnsembleTopK guide routes **directly** to the
ensemble (no pooling sleeve needed; §6.4 of the guide). All ten have deep, continuous ORATS option chains
and clean RV/IV history. The correlation-group tag drives the portfolio-level margin cap in §7.

### 2.2 Backtest window — "back to 2007", honestly

The brief asks for "back to any data we have (back to 2007)." Two constraints bound the *tradeable* start:

- **Option chains start 2007.** Before that there is no put spread to sell. Hard floor.
- **The forecaster needs training history *and* IV features.** EnsembleTopK's IV-aware component
  (`HAR-RS-IV-Q`) regresses on the IV/VIX block, which only begins ~2007. With the `MIN_TRAIN_DAYS = 252×3`
  rule, the **first fold with a fully-populated, IV-aware, ≥3y-trained forecaster lands ≈2010–2011.**

**Recommendation — two-segment backtest, reported separately:**

| Segment | Window | Forecaster state | Use |
|---|---|---|---|
| **Warm-up / IV-only** | 2007 → ~2010 | forecaster thin or RV-only (IV block immature) | Run a **degraded book**: gate on IV-percentile + term-structure + post-shock only (no forecast-dispersion gate, flat or IV-sized). Reported as a robustness segment, **not** the headline. Captures the GFC stress test — the most valuable tail data we have. |
| **Primary OOS** | ~2010 → present | full EnsembleTopK, expanding window | The **headline** book. All gates active. |

This is the only honest way to "use all data back to 2007": the GFC period is the single most important
left-tail stress for a short-vol book, so we *do* trade it — but with the IV-only/degraded gate, clearly
labelled, rather than pretending the forecaster existed. Do **not** lower `MIN_TRAIN_DAYS` to manufacture a
2007 forecast; that trains on 1–2y and leaks regime-overfit garbage into the very crisis we most need to
measure honestly.

> The existing `rv_eval.config.OOS_START = 2018-01-01` was chosen for the *forecasting* study's clean OOS.
> For this backtest we deliberately extend earlier (to ~2010 for the primary segment, 2007 for warm-up).
> This is a config change for the backtest, **not** a change to the frozen forecasting evaluation.

---

## 3. Forecaster training protocol — rolling vs expanding window

**The brief's question: train on "past N years continuously" (rolling) or "whole past years, min N"
(expanding)? Which is better?**

**Recommendation: expanding window, monthly refit, min 3y — the production default.** Reasoning, then the
robustness ablation.

### 3.1 Why expanding wins for this model class

1. **HAR coefficients are structurally stable; the *features* carry the regime, not the betas.** HAR
   regresses forward RV on current daily/weekly/monthly RV levels. When vol regime shifts, the **inputs**
   (rv_d, rv_w, rv_m) move — the mapping from "current vol structure → forward vol" is close to
   time-invariant. So unlike a price-momentum or factor model, you do **not** need to drop old data to stay
   adaptive: today's high-vol regime is represented by today's high feature values fed through stable betas.
   This is the core reason HAR works with long histories.
2. **OLS estimation variance falls with more data.** Each component fits a per-(ticker,horizon) OLS on
   hundreds-to-thousands of rows. At h=22 the 22-day-overlapping target already costs effective sample
   size; a short rolling window (say 2–3y ≈ 500–750 rows, far fewer *independent* 22-day blocks) makes the
   betas noisy. The guide is explicit that this model family is fragile to estimation-variance, not bias
   (§9.3 — kitchen-sink overfit is the failure mode). Expanding maximizes effective sample → lowest beta
   variance → best calibration (the property the gate consumes).
3. **The ensemble's calibration depends on stable component σ's.** The downstream gate keys on
   `sigma/rv_hat` vs a trailing percentile. A short rolling window injects refit-to-refit jitter into σ,
   which would make the dispersion gate chatter. Expanding gives a smooth, slowly-evolving σ.
4. **It is the validated production protocol.** `TRAIN_WINDOW = expanding (lo=0)`, `REFIT_FREQ = monthly`,
   `MIN_TRAIN_DAYS = 252×3` is exactly what won across all three study stages. Changing it for the backtest
   would mean the book runs on an unvalidated forecaster.

### 3.2 The case *against* pure expanding (and how we bound it)

The one real risk of expanding: **permanent influence of ancient regimes** — the 2008 GFC and the
2003–2006 pre-IV microstructure era never age out, so 2024 betas still carry a 2008 fingerprint. For a
short-vol book this is arguably *protective* (it keeps a healthy fear of tails baked into σ), but it is
worth measuring.

**Robustness ablation (secondary, not the headline):** also run a **long rolling window — 8 years (≈2000
days)** — refit monthly. Eight years is long enough to keep effective sample healthy yet drops truly
ancient regime. Compare headline metrics (DSR, CVaR95, maxDD, calibration) between expanding and 8y-rolling.

- If they match → ship expanding (simpler, validated, more data).
- If 8y-rolling materially improves the post-2020 tail → adopt a **hybrid: expanding with a soft cap at
  ~10y** (drop only the oldest, never go below a long floor). Do **not** ship a short (≤3y) rolling window:
  it maximizes the exact estimation-variance failure mode the guide warns about.

**Refit cadence is monthly either way** — this matches the 22-day roll, so each new trade is sized off a
forecaster refit within the last ~22 trading days. Purge+embargo of `max(1, h)=22` days before each
prediction block is **mandatory** (the 22-day forward target overlaps across days; guide §6.3).

> **Verdict:** Expanding, monthly, min 3y is the primary. 8y-rolling is a one-line robustness ablation.
> Reason: HAR's edge is low-variance, well-calibrated betas, and that comes from *more* data, not *recent*
> data, because the regime lives in the features.

---

## 4. Entry gate — when to put the trade on

A candidate entry exists for `(ticker, date)` on the **monthly roll dates** (non-overlapping 22-day cadence,
`trade_eval.config.ROLL_CADENCE`). It becomes a **trade** only if **every** gate below passes. Each gate is
computed **point-in-time** (trailing windows only — no lookahead; reuse `trade_eval.pit`).

The gate is intentionally a **conjunction of regime filters** — the research says the edge is *avoidance*,
so we are generous with reasons to stand down.

### 4.1 The gate stack (all must pass to trade at full size)

| # | Gate | Condition to **trade** | Source column | Rationale |
|---|---|---|---|---|
| G1 | **VRP not meaningfully negative** (soft band) | `vrp_rel = (iv2 − rv_hat)/iv2 ≥ −τ`, **τ=0.05** (sweep ≤0.10) | forecast + `iv2` | **Not a hard `>0` veto** — see §4.5. A put spread also earns drift + skew premium, so "IV ≈ expected RV" is fine; only stand down when the model says RV is *materially* above IV. |
| G2 | **IV-percentile band** | `25 ≤ IVrank ≤ 85` (trade); `IVrank > 85` → **avoid**; `IVrank < 25` → **reduce** | trailing 252d pct of `iv_30d` | See §4.2 — the brief's >85 avoid rule, plus a cheap-floor. |
| G3 | **Term structure in contango** | `iv_slope = iv_90d − iv_30d > 0` **and** VIX contango `vix3m > vix` | `iv_slope`, `vix`, `vix3m` | See §4.3 — the single strongest short-vol regime filter. Backwardation → avoid. |
| G4 | **Forecast dispersion not hot** | `sigma/rv_hat ≤` trailing-80th-pctile | forecast `sigma` | The validated Stage-1 gate: stand down when the forecaster is unusually unsure (regime about to break). |
| G5 | **Not post-shock** | `post_shock == False` | `post_shock` | Don't re-enter into the immediate aftermath of a vol shock (mean-reversion trap). |
| G6 | **Skew not extreme** | `skew_25d ≤` trailing-90th-pctile | `skew_25d` | Blow-off put skew = crash being priced = the market is paying you *because* tail risk is real. Avoid the top decile. |
| G7 | **Liquidity OK** | every leg: OI ≥ 50, rel-spread ≤ 0.35; net credit ≥ $0.05; credit/width ≥ 0.20 | ORATS chain | Reject untradeable / no-edge-after-cost structures. (`stage2_trade_eval.config` MIN_OI etc.) |

If **G1–G6 pass but the row is in a "reduce" sub-state** (IVrank<25, or mid-tercile dispersion, per
`trade_eval.signals._gate_expr`), trade at **half size** (`REDUCE_MULT = 0.5`) rather than skipping.

### 4.2 The IV-percentile gate (the brief's ">85 → avoid")

**Define `IVrank` = point-in-time percentile of today's `iv_30d` within its own trailing 252-day window**
(per ticker). This is the standard "IV rank/percentile" practitioners use, computed leakage-free.

The brief's instinct — **avoid when IVrank > 85** — is correct and worth stating *why*, because it is the
opposite of the naïve "sell vol when IV is high":

- A short-vol book *wants* elevated IV (more premium), **but the top decile of IV is not "rich vol," it is
  "regime stress."** When IVrank pushes >85–90, you are usually inside or entering a crisis where **realized
  variance overshoots implied** — the VRP goes *negative* exactly when IV looks most tempting. Selling into
  the top decile is how naked short-vol books die.
- This is fully consistent with the forecaster's documented behavior: its value is **left-tail control**,
  and the >85 cutoff is a coarse but robust left-tail filter that needs no model at all.

**But also gate the cheap floor:** `IVrank < 25` → **reduce** (not avoid). Very low IV means thin premium;
the spread's credit/width may fail G7 anyway, but where it doesn't, trade small. The **sweet spot is a
mid-to-elevated band (≈25–85)** where premium is meaningful and the regime is not yet stressed.

> Note: a coarse `iv_pctile_bucket` is produced by the panel builder (and the Stage-1 gate used its low
> buckets for "reduce"). Here it is recomputed PIT per fold like every other feature. For this book we
> promote IV-percentile to a **first-class continuous gate** with the
> explicit 85/25 thresholds, computed PIT from `iv_30d`. Treat the 85/25 cuts as **fixed** (set once, never
> tuned on OOS P&L); expose them as a robustness sweep only (e.g. avoid∈{80,85,90}).

### 4.3 The term-structure gate (contango required)

**Require contango at entry; avoid in backwardation.** Two complementary slopes, both already in the panel:

- **Own-ticker IV term structure:** `iv_slope = iv_90d − iv_30d > 0` (the curve slopes up — near-dated vol
  cheaper than far-dated, the normal calm-market shape).
- **Market VIX term structure:** `vix3m > vix` (equivalently `vix_slope > 0`).

**Why this is the highest-value single filter for short vol:**

- Contango is the normal, calm-market state and is *mechanically* associated with positive VRP carry: the
  curve rolls down toward you as the option ages.
- **Backwardation (front > back, `iv_slope < 0` / `vix > vix3m`) is the canonical stress signal** — it flags
  acute, present-tense fear (guide §3, `vix_slope` "inverted curve flags acute market stress"). Selling
  premium in backwardation is selling into the storm. This is the regime where put spreads gap to max loss.

**Strictness:** require **both** the own-ticker slope **and** the market VIX slope to be in contango. The
own-curve catches single-name stress (e.g. XLE during an oil shock) the index curve misses; the VIX curve
catches market-wide stress. Conjunction = avoid trading any name when *either* its own curve *or* the broad
market has inverted. (Optionally relax to "own-curve OR a short floor `vix9d < vix`" as a sweep, but default
= strict AND.)

### 4.4 Other entry signals worth adding (proposed, ranked by expected value)

Beyond G1–G7, candidates — implement the top two; the rest are sweeps:

1. **Trend / drawdown-state filter (high value).** Sell put spreads only when price is **not** in a fresh
   downtrend — e.g. spot ≥ its 200-day SMA, or 20-day return > −X%. Put spreads are short downside; entering
   into an active selloff is fighting the trend. Cheap to compute from `inputs` close/returns. *Recommend
   adding as G8.*
2. **Credit / macro stress (medium-high).** `credit_spread` and `credit_mom` are in the panel. Widening HY
   credit spreads lead equity-vol regime shifts; gate to **avoid when `credit_mom` > trailing-80th-pctile**.
   Especially relevant for HYG itself. *Recommend adding as G9.*
3. **VVIX / vol-of-vol (medium).** `vvix` rising flags vol-regime instability before VIX moves (guide §3).
   Avoid when `vvix` > trailing-90th-pctile. Overlaps with G4 (dispersion) but is market-wide.
4. **Realized-vol acceleration (medium).** Avoid when short-window RV is rising fast relative to its monthly
   level (`rv_w/rv_m > τ`) — a momentum-in-vol stand-down, complements the post-shock flag.
5. **Cross-sectional concentration (portfolio-level).** Cap the number of concurrent positions inside one
   correlation group (§7) — not a per-name gate but an entry admission control.
6. **Event/earnings (low for ETFs).** ETFs have no single-name earnings; FOMC/CPI macro-event blackouts are
   optional and low-value at 30 DTE. Skip for v1.

### 4.5 Why G1 is a *soft band*, not a hard `iv2 − rv_hat > 0` veto

A strict `vrp_score > 0` gate is the right rule for a **symmetric variance sale** (straddle / variance
swap), whose P&L literally *is* `iv2 − realized_var`. **It is too strict for an OTM put credit spread**,
which earns two premia that do **not** require IV to exceed expected RV:

1. **Drift / put-selling premium** — the short put is OTM and indices drift up, so it decays even at *fair*
   ATM vol (the equity risk premium harvested by put-writing, independent of VRP).
2. **Skew premium** — the 25Δ put is priced on a richer vol than ATM, so the *specific strikes* sold carry
   premium even when ATM `iv2 ≈ rv_hat`.

Two more reasons not to hard-veto at zero:

- **No mean-VRP alpha at h=22** (sign_acc ≈ 0.52, guide §5) — gating on the model's marginal VRP call is
  gating on noise.
- **`rv_hat` is biased low** (−0.10 to −0.17 at h=22), so `vrp_score = iv2 − rv_hat` is biased *high*; a
  `>0` cut is already optimistic in truth terms and discards a band of tradeable fair-vol setups.

**Design (v1 defaults, §10):** (a) gate `vrp_rel ≥ −τ` with **τ = 0.05** so "IV ≈ expected RV" passes and
only *materially* negative VRP stands down; (b) keep `vrp` as a **sizing tilt with a floor** —
`vrp_rel → max(vrp_rel, f)` with **f = 0.05** so near-zero-VRP trades still take a baseline size (they
carry drift+skew, not VRP) rather than collapsing to zero (the current sizer zeroes at `vrp≤0`).
**Ablation:** strict `>0` vs soft-band vs vrp-off (regime gates only) — given §5, expect soft/off to match
or beat strict.

### 4.6 Using the model's tail forecast (q90/q95) — the documented strength

The forecaster's edge is the **second moment / left-tail control**, and for a short put spread the
risk-relevant object is the **upper tail of forecast forward RV** (vol blows out → spot down → short put
goes ITM). So `q90`/`q95` of forward RV — not the symmetric dispersion `sigma/rv_hat` the Stage-1 gate
used — are the natural inputs. Three uses, in priority order:

1. **Tail-aware strike selection (highest value).** Convert `q95` (upper-tail forward variance) into an
   implied worst-case move over the holding period; place the short strike **beyond** it. When the upper
   tail is fat → lower-delta / further-OTM short; when benign → the standard 25Δ (§6). This turns the
   forecast directly into structure. *(Replaces a fixed-delta short with a tail-conditioned delta.)*
2. **Tail gate.** Reduce/skip when the `q95`-implied move would breach the short strike's breakeven — a
   one-sided version of G4 keyed on the tail the book is actually exposed to.
3. **Tail-aware sizing (re-test).** Size on a *downside* dispersion `(q95 − q50)` instead of symmetric σ.
   Stage-1 A5 found `(q95 − q05)` sizing **not** better than σ — but that was the *symmetric* spread on the
   *variance-proxy* P&L; the OTM put-spread payoff is convex/asymmetric, so the one-sided upper tail may
   matter here where the symmetric one didn't. Worth re-checking in option space.

**Critical caveat — what q95 actually is.** In this model the quantiles are a **shared lognormal wrapper**
around `(rv_hat, sigma)` (guide §2): `q95` is a *deterministic transform* of those two numbers, **not an
independently estimated tail**. So q95 adds **no new information beyond σ** — what it adds is the **right
units and the right asymmetry**: it re-expresses model uncertainty as an upper-tail vol/move you can
compare directly to a strike, and the lognormal right-skew weights the up-RV tail (the one that hurts) more
than a symmetric σ band. Useful re-expression, not a second signal.

**So the mandatory check (add to §8): upper-tail calibration specifically** — the empirical rate at which
realized RV exceeds `q90`/`q95`, *per ticker*. The guide's `cov90 ≈ 0.927` is *symmetric* coverage; before
trusting `q95` to place strikes, confirm the **right-tail hit rate** is at/below nominal (the safe
direction), since that one tail is the book's entire exposure.

---

## 5. Exit framework — when to take the trade off

Hold-to-expiry was the Stage-1 winner at h=22, but that was a *variance-proxy* abstraction. Under real
option marks the brief's managed exits (50% profit, terminal-week, regime flip) deserve a head-to-head. The
exit logic is a **first-trigger-wins** stack, evaluated daily on the mark path (reuse
`stage2_trade_eval.management`).

### 5.1 The exit stack (first trigger fires)

| # | Trigger | Condition | Maps to |
|---|---|---|---|
| X1 | **Profit target** | mark P&L ≥ **50%** of max capturable credit | `TAKE_FRAC` (set 0.50; Stage-1 used 0.60) |
| X2 | **Terminal-week management** | `DTE ≤ 21`: tighten — take profit at lower bar, honor stops; **hard close at DTE ≤ 12** (gamma) | `TERMINAL_DTE`, the brief's "n DTE" |
| X3 | **Term structure flips** | `iv_slope < 0` **or** `vix > vix3m` (contango → backwardation) | regime exit (new; the brief's request) |
| X4 | **Variance stop** | accrued realized var over `[t,now]` > entry `iv2` | `MechanicalTerminal` var_stop |
| X5 | **Hard stop** | mark loss ≥ **2× credit** (capped anyway by the wing) | `STOP_MULT = 2.0` |
| X6 | **Forecast re-gate (optional)** | re-evaluated gate flips to `avoid` | `forecast_regate` (H2; churn risk) |
| X7 | **Expiry** | else settle at intrinsic at expiration | default |

### 5.2 Rationale and the management arms to test

- **X1 — 50% profit.** The well-established practitioner default: capturing half the max credit in well
  under half the holding time maximizes return-per-day-of-risk and sidesteps the late-cycle gamma where a
  small spread can swing to max loss overnight. Stage-1 used 0.60; **the brief asks for 50% — adopt 0.50**
  as the primary and sweep {0.50, 0.60} as a robustness check.
- **X2 — "n DTE to expiration."** The brief's n-DTE exit. Two thresholds: **soft at 21 DTE** (begin
  terminal management — lower the profit bar, enforce stops) and **hard at 12 DTE** (close regardless). The
  21-DTE soft threshold is the standard "manage at 21" convention; the 12-DTE hard close avoids the worst
  pin/gamma risk in the final two weeks. (`TERMINAL_DTE = 12` already; add a 21-DTE soft tier.)
- **X3 — term-structure flip (the brief's "contango no longer").** Symmetric with the entry gate G3: if the
  curve that justified entry inverts, the regime assumption is void — exit. This is a **regime stop**, not a
  P&L stop, and is the most defensible "thesis-broken" exit for a short-vol trade.
- **X4 — variance stop.** If realized variance already accrued since entry exceeds the IV² we sold,
  the trade's premise (IV>RV) has failed in-flight; cut it. Model-free, uses the RV path directly.
- **X5 — hard stop at 2× credit.** For a *defined-risk* spread the wing already caps loss, so the stop is a
  secondary discipline (and avoids paying through the spread to close a near-max-loss position late). Keep
  it but expect it to bind rarely once the wing is in place.
- **X6 — forecast re-gate.** Stage-1 A9 found daily forecast re-gating **churns and gives back return** at
  h=22 ("do not run it managed at 30 DTE", guide §11). Keep it as a *toggle* to confirm under real marks,
  but the **default management arm is mechanical (X1–X5), not forecast-driven.**

### 5.3 Recommended default vs ablations

- **Primary management arm:** `mechanical_terminal` extended with X1=0.50, the 21-DTE soft tier, and the
  X3 term-structure flip. This is the brief's exact request and "the one to beat hold."
- **Benchmark arms:** `hold` (Stage-1 winner — must be beaten under real marks to justify managing) and
  `iv_regate`/`forecast_regate` (to confirm the churn finding).
- **Other exit signals worth considering (sweeps):** delta-breach stop (short put delta > 0.45 → roll/close,
  catches a fast move into the short strike before the variance stop fires); profit-and-time combo (take 25%
  if achieved in <10 days); skew-blowout exit (entry-day skew percentile re-checked). Rank delta-breach
  highest of these.

---

## 6. Strike selection — proposed deltas for the put spread

**Recommended: short leg ≈ 0.25Δ put, long protective wing ≈ 0.10Δ put.** Strikes are chosen off the
**entry-day ORATS chain's option delta** (`pValue`/`delta` column; puts use the put delta), then fills come
from that chain's bid/ask. This reuses `stage2_trade_eval.structures.PutCreditSpread` with tuned deltas.

> **Tail-conditioned variant (§4.6, recommended ablation):** instead of a fixed 0.25Δ short, place the
> short strike **beyond the model's `q95`-implied move** over the holding period — lower-delta when the
> upper RV tail is fat, ~0.25Δ when benign. This is the most direct way to convert the forecaster's
> documented tail strength into the structure; gate it on the §4.6 upper-tail calibration check first.

### 6.1 Why 0.25Δ short / 0.10Δ long

| Choice | Value | Reasoning |
|---|---|---|
| **Short ≈ 0.25Δ** | `SHORT_DELTA = 0.25` | ~1σ OTM. Balances premium (meaningful credit) against probability of touch (~75% finish OTM). 0.30Δ collects more but sits too close to spot — the short strike gets tested often, raising the realized tail. 0.16Δ (1σ) is safer but the credit/width often fails G7's 0.20 floor at 30 DTE. **0.25 is the premium-vs-safety knee.** Sweep {0.16, 0.20, 0.25, 0.30}. |
| **Long ≈ 0.10Δ** | `WING_DELTA = 0.10` | The wing exists to **cap the exact left tail the gate avoids** (the strategy's whole thesis). 0.10Δ keeps the spread wide enough that the net credit is most of the premium (you're not over-paying for protection) while still hard-capping max loss at ~3–5σ. A 0.07Δ wing (the Stage-2 default) caps a fatter tail but costs less protection per dollar of width; 0.10 is the recommended balance. Sweep {0.07, 0.10}. |

The current `stage2_trade_eval.config` ships `SHORT_DELTA = 0.20`, `WING_DELTA = 0.07`. **This design
nudges to 0.25 / 0.10** as the put-spread primary (more credit on the short, slightly tighter wing), with
the existing values inside the sweep.

### 6.2 Width and credit-quality constraints

- **Define the spread by delta, not fixed dollar width** — delta-anchoring auto-adapts the width to each
  ticker's price and vol level (a $5 wing means very different things on TLT vs SPY).
- **Credit/width floor:** require net credit ≥ **0.20 × width** (`MIN_CREDIT_TO_WIDTH`). Below that the
  reward/risk is too poor to clear costs — reject (part of G7). Reject also if net credit < $0.05/share.
- **DTE targeting:** nearest listed expiry to **30 calendar days**, accept window **[21, 45]** DTE
  (`TARGET_DTE = 30`, `DTE_TOLERANCE`). Outside the window → no trade that day.

### 6.3 Why a *spread*, not a naked put or a put-ratio

- Naked put = undefined tail = exactly the risk the forecaster cannot give directional protection against;
  the half-Kelly naked fraction the engine uses for strangles is a patch, not a cure.
- The defined-risk spread caps max loss → enables a **higher Kelly fraction** (`KELLY_C_DEFINED = 0.30` vs
  naked `0.15`) and a clean per-group margin budget (§7). The wing is cheap insurance bought *with* the
  premium, in the regime (put skew) where it's relatively well-priced for the seller.

---

## 7. Position sizing

**Recommended: fractional Kelly on the VRP edge, inverse-risk, gate-scaled, with a hard per-trade risk cap
and a per-correlation-group margin cap.** This reuses the validated `trade_eval` size and the
`stage2_trade_eval.sizing` Kelly recalibration verbatim — sizing is *not* re-invented here.

### 7.1 The sizing chain (each step already exists)

1. **Edge/variance base size (Stage-1, validated):**
   `size ∝ vrp_rel / (K · dispersion²)` where `vrp_rel = max(vrp/iv2, f)` and `dispersion = sigma/rv_hat`.
   This is algebraically **Kelly with fraction 1/K** — bet proportional to edge, inversely to forecast
   variance. Smaller when the forecaster is less sure. **Use a small positive floor `f>0` (not 0)** so
   fair-vol trades still take a baseline size for their drift+skew premium (§4.5); the soft G1 band, not the
   sizer, is what removes materially-negative-VRP names. *(Optionally use the §4.6 downside dispersion
   `(q95−q50)/rv_hat` in place of `dispersion` here — re-test vs σ.)* (`trade_eval.signals.build_signals`.)
2. **Gate multiplier:** × 1.0 (trade) / 0.5 (reduce) / 0.0 (avoid). (§4.)
3. **Fractional Kelly by structure:** × `KELLY_C_DEFINED = 0.30` for the defined-risk put spread, clamped
   at `SIZE_CAP = 3.0` units. (`stage2_trade_eval.sizing.kelly_units`.) Kelly is fragile to edge
   mis-estimation, so the fraction is well below 1 and the gate has already zeroed negative-edge names.
4. **Units → contracts off NAV/margin:** with `ROUND_TO_CONTRACTS`, contracts = floor of
   `min(units, group_margin_budget / margin_per_contract)`; for a defined-risk spread
   `margin_per_unit = width − credit` (the true max loss). (`sizing.units_to_contracts`.)

### 7.2 Risk caps (the part that makes it a *book*, not a pile of trades)

| Cap | Value | Why |
|---|---|---|
| **Per-trade risk** | ≈ **1% of NAV** at one size unit (`RISK_BUDGET = 0.01`) | Bounds single-trade damage; defined-risk so max loss is known at entry. |
| **Per-group margin cap** | **20% of NAV** in any one correlation group (`GROUP_MARGIN_CAP = 0.20`) | The 10 ETFs cluster (SPY/QQQ/IWM/XLK all equity-beta). Without a group cap, "10 names" is really ~2–3 independent bets and a crash hits them together. This is the portfolio-level tail control that complements the per-trade wing. |
| **Size cap** | 3 units/trade (`SIZE_CAP`) | Prevents Kelly from concentrating into one apparently-rich name. |
| **Portfolio vol target (optional)** | scale all sizes so book σ ≈ target | Secondary overlay; sweep, not v1 default. |

### 7.3 Why this sizing, not fixed-fractional or fixed-contracts

- **Inverse-risk is the documented source of the book's edge.** Stage-1 A2/A3: the gate + σ-sizing is
  what delivered the 3–4× tail reduction. Flat sizing throws that away.
- **Fractional (not full) Kelly** because the VRP edge is noisily estimated on ~125 monthly h=22
  observations (guide §11 power caveat). Full Kelly on a mis-estimated edge is ruin-seeking; 0.30× is the
  validated compromise.
- **Group-margin capping over naive equal-weight** because the universe's true dimensionality is low —
  correlation, not name count, sets the tail.

---

## 8. What to measure (success criteria)

Reuse the Stage-1/Stage-2 scoring (`reports.score_stage1`: DSR, CVaR95, maxDD, AnnRet, break-even bps) so
results are comparable to the upstream studies. The bar is **relative**, framed by the forecaster's thesis:

| Axis | Target | Why it's the right axis |
|---|---|---|
| **Left tail** | CVaR95 and maxDD materially **below** an ungated IV-only put-spread book | The forecaster's whole documented value is tail control (§1). This is the headline. |
| **Risk-adjusted return** | Deflated Sharpe ≥ the IV-only put-spread benchmark; ideally beat hold-to-expiry | Promotion rests on tail-no-regress + signal attribution, not absolute Sharpe (guide §11). |
| **Stress decorrelation** | cross-group P&L correlation collapses in stress windows (2008, 2020, 2022) | The book should *decorrelate* when it matters, as Stage-1 showed (0.46→0.05). |
| **Calibration of the gate** | gate-on vs gate-off ablation shows the tail improvement is the gate's doing | Attribution: prove the gates, not luck, cut the tail. |
| **Upper-tail forecast calibration** (§4.6) | empirical rate of `realized RV > q90`/`> q95`, **per ticker**, at/below nominal | The book's entire exposure is the up-RV tail; symmetric cov90 doesn't certify it. Required before tail-conditioned strikes/sizing are trusted. |

**Mandatory benchmarks/ablations:**
- **IV-only put spread** (no forecast gate; size flat) — the null the forecaster must beat on the tail.
- **Gate-off** (G1–G6 disabled) — isolates the gate's contribution (Stage-1 A2: removing the gate blew up
  drawdown ~8×).
- **Hold vs managed** (§5.3) — does managing beat hold under real marks?
- **VRP gate: strict `>0` vs soft-band vs off** (§4.5) — does the model's marginal VRP call add anything, or
  do the regime gates + drift/skew carry it?
- **Tail usage: fixed-25Δ vs `q95`-conditioned strike; σ vs `(q95−q50)` sizing** (§4.6).
- **Expanding vs 8y-rolling** forecaster (§3.2).
- **Cost stress:** the engine crosses the bid/ask on entry and close; additionally sweep `SLIPPAGE_TICKS`
  and report break-even cost (Stage-1's ~312 bps abstraction is optimistic; real spread cost is the point
  of doing this in option space).

---

## 9. How this maps onto the existing engine (build note, not code)

This design is deliberately a **parameterization of `stage2_trade_eval/`**, not a new system. The
implementation is mostly config + two small additions:

| Design element | Existing hook | Change needed |
|---|---|---|
| Put spread structure | `structures.PutCreditSpread` | tune `SHORT_DELTA→0.25`, `WING_DELTA→0.10` |
| Entry gate G1 (VRP) | `trade_eval.signals._gate_expr` / `build_signals` | relax `vrp_score>0` → soft band `vrp_rel≥−τ`; add sizing floor `f>0` (§4.5) |
| Entry gate G4, G5 | `trade_eval.signals._gate_expr` | reuse as-is |
| Tail forecast use (q90/q95) | forecast `q05..q95` already emitted | tail-conditioned short strike + optional tail gate / `(q95−q50)` sizing; check upper-tail calibration (§4.6) |
| IV-percentile gate G2 (85/25) | new | add PIT `IVrank` from `iv_30d`; promote to first-class gate |
| Term-structure gate G3 | `iv_slope`, `vix_slope` in panel | add as entry filter (new condition) |
| Skew/credit/trend gates G6/G8/G9 | columns in `inputs` | add as entry filters (new conditions) |
| Exit X1/X2/X4/X5 | `management.MechanicalTerminal` | set `TAKE_FRAC=0.50`; add 21-DTE soft tier |
| Exit X3 term-structure flip | new | add a `term_structure_flip` trigger to the terminal arm |
| Sizing | `sizing.kelly_units` + caps | reuse as-is |
| Data layer (raw mirror + per-fold feature/forecast build) | `rv_eval.config.RAW_ROOT`, `rv_eval/setup/{measurement,iv_features,cross_asset}.py` + `walkforward` | point `RAW_ROOT` at `back-test-data/`; rebuild features + train HARs per fold, never cached — full spec in **`BACKTEST_DATA_SPEC.md`** |
| Backtest window 2007/2010 | `OOS_START` | extend for this backtest only; two-segment reporting |
| Forecaster expanding/rolling | `rv_eval.config.TRAIN_WINDOW` | primary expanding; add 8y-rolling ablation |

Everything else — fills, marking, greeks, settlement, ledger schema, DSR/CVaR scoring — carries over
unchanged, so results are directly comparable to the Stage-1/Stage-2 studies.

---

## 10. Resolved decisions (v1 defaults)

These were the previously-open questions; each is now resolved to a **v1 default** (set once, never tuned
on OOS P&L). The "ablation" column says what is *also* run to test the choice — but the book ships with the
default regardless of the sweep, and sweeps are read-outs, not selection on OOS.

| # | Decision | **v1 default** | Why | Also run as ablation |
|---|---|---|---|---|
| 1 | Term-structure strictness (G3) | **strict AND** — own-curve `iv_slope>0` *and* `vix3m>vix` | conjunction catches single-name *and* market stress; backwardation is the regime that gaps put spreads to max loss (§4.3) | OR variant |
| 2 | Profit target (X1) | **0.50** of max credit | best return-per-day-of-risk; the brief's number; avoids late-cycle gamma (§5.2) | 0.60 |
| 3 | Short / wing delta (§6) | **0.25Δ short, 0.10Δ wing**, credit/width ≥ 0.20 | premium-vs-safety knee; wing caps the tail the gate avoids (§6.1) | short {0.16,0.20,0.30}, wing 0.07; + tail-conditioned strike (#8) |
| 4 | OOS window (§2.2) | **primary ~2010 →**, with **2007–2010 labelled IV-only warm-up** | first fold with a full ≥3y IV-aware forecaster ≈2010; warm-up still trades the GFC honestly under the degraded gate | — (do **not** lower `MIN_TRAIN_DAYS`) |
| 5 | Forecaster train window (§3) | **expanding, monthly refit, min 3y** | HAR betas stable; edge is low-variance calibrated σ from *more* data, not recent data (§3.1) | 8y rolling |
| 6 | Trend filter (G8, §4.4) | **include in v1** — spot ≥ 200-day SMA (else avoid) | put spreads are short downside; don't enter a fresh downtrend; cheap, high-value | off (isolate its contribution) |
| 7 | VRP gate (G1, §4.5) | **soft band**: avoid only if `vrp_rel < −τ`, **τ = 0.05**; sizing floor **f = 0.05** | a put spread also earns drift+skew, so fair vol is fine; model has no mean-VRP alpha at h=22; `rv_hat` biased low | strict `>0`; vrp-off (regime gates only) |
| 8 | Tail-forecast use (§4.6) | **v1 ships fixed 0.25Δ short + σ-sizing**; turn on `q95`-conditioned strike / `(q95−q50)` sizing **only if** the per-ticker upper-tail calibration check passes | q95 is a deterministic transform of σ — adopt the tail re-expression only once its right-tail hit rate is certified | q95-conditioned strike; `(q95−q50)` sizing |

**Remaining genuinely-empirical items** (decided by the ablation read-out, not pre-set): whether managing
beats hold-to-expiry under real marks (§5.3), and whether the tail-conditioned strike (#8) clears its
calibration gate. Everything else above ships at the stated default.

---

_Conclusion: this is a defined-risk, conditionally-short-variance put-spread book whose edge is **regime
avoidance and capped tails**, not directional vol prediction. It sells a 0.25Δ/0.10Δ 30-DTE put spread on
10 core ETFs whenever the VRP is **not materially negative** (fair vol is fine — the spread also earns drift
and skew premium), IV-percentile sits in a mid-high band (≤85), the term structure is in contango, and the
forecaster is confident; it exits on 50% profit, a 21-DTE terminal tighten, a contango→backwardation flip,
a variance stop, or a 2× hard stop; and it sizes by fractional Kelly on the VRP edge with a
per-correlation-group margin cap. The forecaster's documented strength — the **upper tail of forward RV
(`q90`/`q95`)** — is used where it bites: tail-conditioned strike placement and downside-aware sizing. It is
a parameterization of the existing `stage2_trade_eval/` engine, trained on the production EnsembleTopK
forecaster with an expanding monthly refit, and it is judged on the axis the forecaster actually wins on:
the left tail._
