# Stage-2 Strategy Refinement & Real-P&L Plan — VRP Short-Vol on the Core ETFs

**Status:** design spec + a **built engine framework** (Part D is implemented as `stage2_trade_eval/`,
tests green; no model refits, no OOS scored yet). Operationalizes the promotion list out of
[`trade_eval/reports/STAGE1_RESULTS_REPORT.md`](../trade_eval/reports/STAGE1_RESULTS_REPORT.md) into
(a) a finetuning program for the primary forecaster, (b) a horizon-switched management design, and
(c) a tradable, real-option-marks strategy with a Stage-2 P&L engine (now built — see Part D / `README.md`).

**Locked decisions (from the kickoff Q&A, 2026-06-05):**
- **Structures:** **defined-risk** (iron fly / iron condor / put debit-spread) as the workhorse **and**
  **naked short strangle/straddle** as a higher-octane variant. *No wheel.*
- **Sizing:** **fractional Kelly on the VRP edge** (`f = c·μ/σ²`, `c≈0.25–0.35`, capped).
- **Tuning:** **plan + a validation-safe protocol only** this session — the frozen 2018→2026 OOS is
  **not** touched; no sweeps are executed here.
- **Universe:** the **10 clean-core ETFs** — `SPY QQQ IWM XLK XLF XLE TLT GLD HYG EEM`. The 5 hard-case
  names and the pooled sleeve (`HAR-Shrink2Group`, `PanelHAR-FE`) are out of scope here.
- **Data confirmed on disk:** full **ORATS EOD chains** at
  `execution/data/raw/orats/ticker=<T>/year=<Y>/data.parquet` — per `trade_date`, the whole strike×expiry
  surface with `cBidPx/cAskPx/pBidPx/pAskPx`, `cMidIv/pMidIv/smoothSmvVol`, full greeks
  (`delta/gamma/theta/vega/rho`), `stkPx/spot_px`, `iRate/divRate`, `yte`, `expirDate`. SPY spans
  2007→2026, ~253 trade-dates/yr, ~4.6k rows/day, expiries out to ~3y. **Real per-contract P&L is
  feasible now — no Black-Scholes proxy needed.**

---

## 0. The Stage-1 constraints this refinement must respect

Everything below is downstream of five findings that are **not up for re-litigation** — they are the
result of the frozen study and they bound the design:

1. **The edge lives at 30 DTE (h=22) only.** 7 and 14 DTE are No-Go for the forecast; IV-only is the
   better book at 7 DTE. → *We build the real strategy at ~30 DTE entry.*
2. **The edge is tail-control, not mean alpha.** At 30 DTE `rv_hat` carries ~no incremental skill over
   `iv2`; the forecast pays through the **regime gate** (avoids variance-spike names) and **σ-sizing**.
   CVaR95 −0.018 vs IV −0.064; maxDD 0.051 vs 0.203. → *We optimize and measure on tail/DSR, never on
   mean return; the gate and σ are the assets we are refining.*
3. **Daily forecast re-gating (A9) is a No-Go at 30 DTE.** It churns the book (125→254 rolls) and gives
   back the return (Sharpe 0.94→0.21). → *The "manage daily" idea must NOT be implemented as forecast
   re-gating (see Part B).*
4. **Management value at short DTE is generic, not forecast-specific** — it helped IV-only the most
   (IV-only managed @7 DTE is the only DSR≥0.95 cell in the grid). → *Terminal-week management should be
   mechanical / IV-driven, not forecast-driven.*
5. **The regime gate buys genuine stress-decorrelation** (cross-group corr 0.46→0.05 into the worst-20
   days for IV-only vs EnsembleTopK). → *One-position-per-group and the gate are kept; the diversification
   property is a primary thing to preserve when we add real structures.*

**Roles carried forward (core path):** `EnsembleTopK` = primary @ h=22; `HAR-X` = transparent
graceful-degrade fallback @ h=22. Both already "PASS (qualified)" — qualified because *no* cell cleared
the **absolute** DSR≥0.95 bar after 104-trial deflation (a power limit on ~125 monthly obs). **The
option engine adds realism, not observations — this power caveat persists into Stage-2 and every
readout must keep flagging it.**

---

## Part A — Finetuning & optimizing EnsembleTopK

### A.1 What is actually tunable — and what is *not*

`EnsembleTopK` (`candidate_models/ensemble_top.py`) is **hyperparameter-free by design**: an
equal-weight (1/N) mean of four HAR-family components (`HAR-RS-IV-Q, HARQ, HAR-RS, HAR-CJ`), with
`sigma = sqrt(mean(component σ²) + var(component rv_hat))` (within + between variance) and quantiles
regenerated lognormally. `fit` is a no-op. So "tuning the model" has **two genuinely distinct surfaces**,
and the Stage-1 results tell us which one matters:

| Surface | Knob | Why it might help | Why it probably *won't* move trading P&L |
|---|---|---|---|
| **Forecast — point (`rv_hat`)** | component set, top-K, weights (equal vs inverse-MSE vs regime-conditional) | better QLIKE | **At 30 DTE `rv_hat` has no edge over `iv2` (Finding #2).** Improving the *mean* forecast does **not** translate to economic value at the only horizon that trades. **De-prioritize.** |
| **Forecast — uncertainty (`sigma`)** | the within+between σ construction; **σ-calibration** | the gate and the size both key on `sigma/rv_hat` (dispersion). The report flags **h=22 interval under-coverage** (cov90 = 0.70 clean-core vs 0.90 nominal) and a **downward point bias**. A mis-calibrated σ mis-gates and mis-sizes. | This is the **right** lever — but it must be tuned against the **gate/size economic objective**, not against QLIKE. |
| **Trading wrapper (`trade_eval/config.py`)** | gate percentile, terciles, IV-cheap buckets, `REDUCE_MULT`, sizing `K`/`SIZE_CAP`, `RISK_SCALE`, structure haircuts, costs, mgmt `TAKE_FRAC/STOP_MULT` | **these are the dominant value drivers** (A2 gate, A3 σ-sizing are what move CVaR/maxDD) | overfitting risk — they were "set once, never fit on OOS" (§6). Tuning them **burns OOS** unless done on a carved validation split. |

**Conclusion that reframes the user's question:** for *trading*, EnsembleTopK is best "optimized" by
(i) **calibrating its `sigma`** (the documented weak spot) and (ii) **tuning the wrapper knobs that
consume `sigma`** — *not* by chasing a better `rv_hat`. The component/weight surface is a forecasting-
quality question and is **low-leverage for P&L** at 30 DTE; we test it once (E1) and expect little.

### A.2 The wrapper knobs (current value · plausible range · expected effect · risk)

All from `trade_eval/config.py`. These are the highest-leverage, lowest-cost things to tune.

| Knob | Current | Range to probe | Expected effect | Risk if mis-set |
|---|---|---|---|---|
| `DISP_PCTILE` (gate "avoid" threshold) | 0.80 | {0.70, 0.75, 0.80, 0.85, 0.90} | **the dominant driver** — looser → more carry, fatter tail; tighter → smaller tail, less return. | over-tight throttles the 30-DTE carry (the 7-DTE failure mode); over-loose loses the decorrelation. |
| `DISP_TERCILE_LO/HI` ("reduce" band) | 1/3, 2/3 | {0.25–0.40 lo, 0.60–0.75 hi} | shapes the half-size middle regime | minor; interacts with `REDUCE_MULT`. |
| `REDUCE_MULT` | 0.5 | {0.33, 0.5, 0.67} | how hard "reduce" cuts | low. |
| `IV_CHEAP_BUCKETS` | (0,1) | {(0), (0,1), (0,1,2)} | sits out / shrinks low-IV-percentile sells (thin premium) | dropping it re-admits low-premium trades. |
| `K` (risk-aversion in size ∝ vrp/Kσ²) | 1.0 | reparam as Kelly `c` (A.4 / Part C.4) | overall leverage | too high → cap-saturation, tail; too low → leaves edge. |
| `SIZE_CAP` | 3.0 | {2, 3, 4} units | truncates the most-confident sells | high cap concentrates risk. |
| `RISK_SCALE` | "sigma" | "sigma" vs "qspread" | A5 showed qspread is a wash | keep "sigma" unless E-series flips it. |
| `STRUCTURE_HAIRCUT` | per-name | re-derive from real structures (Part C.2) | maps proxy → real defined-risk vega | Stage-1 values are abstractions; recompute. |
| `TAKE_FRAC` / `STOP_MULT` (mgmt) | 0.6 / 2.0 | {0.5, 0.6, 0.75} / {1.5, 2, 3} | terminal-week mgmt (Part B) | only matters once management is on. |

### A.3 The validation-safe tuning protocol (mandatory — protects the OOS)

The frozen 2018→2026 OOS is the **final test set** and must stay untouched. Any tuning runs on a carved
window with the study's own leakage discipline:

1. **Split.** Reserve **2018-01 → 2021-12 as the tuning/validation window**; **2022-01 → 2026-05 as the
   held-out confirmation set** (kept frozen until the very end). Rationale: validation must include
   2018-Q4, 2020-Q1 (COVID) and 2018-vol-spike so the gate is tuned across at least one real
   stress — a tail strategy tuned only on calm years is worthless.
2. **Inner evaluation = walk-forward CV inside the validation window**, never a single in-sample fit.
   Embargo ≥ `horizon + target-window` (≥ 22 + the target accrual, ~44 trading days) between any tuning
   fold and its evaluation block — reuse `rv_eval`'s purge/embargo. No knob may see a P&L it is scored on.
3. **Objective = economic, tail-led**, *not* QLIKE: a CVaR-penalized utility, e.g.
   `U = AnnRet − λ·|CVaR95| − μ·maxDD` (λ, μ pre-registered, λ dominant), reported next to DSR. Tie-break
   on DSR. **Never** select on mean return alone (Finding #2).
4. **Pre-register a *coarse* grid and count the trials.** Every additional knob value is a DSR-deflation
   trial. With ~60 monthly obs in the validation window, power is tiny — keep grids to 3–5 points/knob,
   tune **one knob family at a time**, freeze, move on (coordinate-descent, not full cross-product).
5. **Guardrails (a tuned config is rejected unless all hold on validation):** (a) tail no-regress —
   CVaR95 **and** maxDD not worse than the frozen baseline config; (b) still **beats the A7 random/always
   controls**; (c) the gate/σ attribution (A2/A3 marginal) stays positive. A config that wins return by
   loosening the gate into a fatter tail is a fail, by construction.
6. **One-shot confirmation.** The single chosen config is run **once** on 2022→2026 and on the full
   frozen OOS for the report. If it doesn't hold there, it is reported as a negative — no re-tuning.

### A.4 Recommended experiments (ranked by expected P&L leverage)

Each is a `trade_eval` run + the existing `score_stage1` scoring on the **validation** window only.

- **E1 — `EnsembleTopK-v2` vs v1 (forecast-side, low expected leverage).** v2
  (`candidate_models/ensemble_top_v2.py`) already exists on disk: regime-conditional, leakage-safe
  inverse-discounted-MSE softmax weights with per-horizon top-K. *Hypothesis:* regime weighting tightens
  `sigma` in calm regimes and widens it in stress → better gating. *Test:* add `EnsembleTopK-v2` to the
  `trade_eval` shortlist, score on validation. *Guardrail:* must beat v1 on **DSR+CVaR**, not QLIKE.
  *Prior:* modest — both share the same four HAR cores; the win, if any, is in σ-calibration not the mean.
- **E2 — gate percentile sweep (highest leverage).** `DISP_PCTILE ∈ {0.70…0.90}`. The gate is *the*
  documented value driver (A2). Find the validation-optimal, confirm tail no-regress.
- **E3 — σ-recalibration overlay (targets the documented weakness).** The report flags h=22
  under-coverage. Fit a **point-in-time conformal / PIT recalibration** of `sigma` (a monotone scale
  `sigma' = a·sigma`, `a` estimated only on past residual coverage, per the embargo) **before** it feeds
  the gate/size. *Hypothesis:* a better-calibrated dispersion gates and sizes the tail more accurately.
  This is the most principled forecast-side lever and is leakage-safe (uses only past coverage).
- **E4 — Kelly fraction & cap (`c`, `SIZE_CAP`).** Re-parameterize sizing as fractional Kelly (A.5),
  validate `c∈{0.25,0.30,0.35}`, `cap∈{2,3,4}`.
- **E5 — reduce-regime shape (`REDUCE_MULT`, terciles, IV-cheap).** Lowest leverage; tune last or skip.

### A.5 Sizing is already (fractional) Kelly — the connector

Stage-1's inverse-risk size is `size ∝ (vrp/iv2) / (K·(σ/rv_hat)²)` — i.e. **edge / (K·variance)**. Kelly
is `f* = μ/σ²`. So **Stage-1 σ-sizing *is* fractional Kelly with fraction `c = 1/K`.** Adopting
"fractional Kelly on the VRP edge" is therefore **not a new, untested sizer** — it is a recalibration of
the `K` that the study already validated (A3: σ-sizing halves CVaR, significant for HAR-X/Shrink2Group).
The refinement is only: (i) estimate the edge `μ` and variance `σ²` in **real structure-P&L units** (Part
C.4) rather than abstract variance units, and (ii) pin `c≤0.35` and a hard cap, because Kelly is
notoriously sensitive to edge mis-estimation and a short-gamma book cannot afford an over-bet tail.

---

## Part B — The horizon-switched management idea ("enter @22 with EnsembleTopK, manage daily with IV-only below 10 DTE")

### B.1 The idea is right in spirit — but Stage-1 says *how* it must be built

The user's intuition: **enter** at 30 DTE with the forecast, then **manage daily** with a simpler
IV-only rule once the trade is inside ~10 DTE. The Stage-1 evidence (Findings #3, #4) says this is
**well-aimed** — but only if implemented precisely:

- ❌ **Not** as forecast daily re-gating (that *is* Stage-1 A9, a No-Go at 30 DTE — churns, gives back
  return). The forecast's job is the **entry**, where its gate avoids the spike names; re-running the
  forecast gate every day inside the trade destroys the carry.
- ✅ **Yes** as **forecast-gated entry + mechanical (IV/variance-accrual) terminal-week management.**
  Management at short DTE is a generic short-vol discipline (it made IV-only the only DSR≥0.95 cell), so
  the terminal-week manager should be **model-free**: profit-take / variance-stop / delta-band, driven by
  the *mark* and `iv2`, not by a fresh `rv_hat`.

This cleanly separates the two things each tool is good at: **EnsembleTopK picks *what* and *whether* to
sell (tail avoidance at entry); mechanics decide *when to leave* in the gamma-heavy final week.**

### B.2 The four management arms to A/B in the option engine

Run as ablations of the same forecast-gated entry book (core ETFs, ~30 DTE entry):

| Arm | Entry | 30→~12 DTE | ~12→0 DTE (terminal week) | Stage-1 prior |
|---|---|---|---|---|
| **H1 Hold-to-expiry** | EnsembleTopK gate+size | hold | hold to settlement | the promoted baseline; the reference. |
| **H2 Forecast re-gate (A9 redux)** | same | daily forecast gate | daily forecast gate | **expected loser** — replicate to confirm churn under real marks. |
| **H3 Entry-forecast + mechanical terminal mgmt** ★ | same | hold | **model-free:** take-profit @ `TAKE_FRAC`·max-credit, variance-stop (accrued RV > entry `iv2`), defined-risk auto-stop, delta-band | **the user's idea, the one to beat H1.** Short-DTE mgmt is where the generic win lives. |
| **H4 Entry-forecast + IV-only re-gate terminal week** | same | hold | re-gate on the **IV-only** signal (`iv2` vs trailing RV + post_shock) only | tests whether *any* terminal-week signal beats pure mechanics. |

**Hypothesis:** `H3 ≥ H1 > H4 > H2` on DSR/CVaR at 30 DTE. H3 is the design to ship if it clears H1's
tail without giving back the carry that A9 churned away. Crucially, under **real option marks** the
terminal week is where **gamma/theta** dominate — the variance-accrual proxy could not see this, so H3
may finally show the early-exit benefit the proxy suppressed. This is explicitly flagged in the Stage-1
report as the thing Stage-2 should revisit "on true greeks, not the variance-accrual proxy."

### B.3 Model *blend* (not horizon blend), for completeness

Within the core path the model combination is already specified by role: **EnsembleTopK primary**, with
**HAR-X as graceful-degrade fallback** when an EnsembleTopK key is missing (fewer than 2 components, or a
prediction gap). Keep this as a **coverage fallback**, not a daily blend — A6 showed EnsembleTopK ≥ HAR-X
everywhere, so blending them adds noise. (The Shrink2Group sleeve is hard-cases-only and out of core
scope.)

---

## Part C — The tradable strategy spec (core ETFs)

### C.1 Universe, cadence, portfolio construction

- **10 core ETFs**, grouped by the `rv_eval` correlation map (e.g. `SPY/QQQ` large-cap, `XLF/KRE`
  cyclicals, `XLE/USO` energy — within core: `SPY,QQQ`=large-cap; `IWM`=small-cap; `XLK`=tech;
  `XLF`=cyclicals; `XLE`=energy; `TLT`=rates; `GLD`=metals; `HYG`=HY credit; `EEM`=EM).
- **One position per correlation group** at any time — this is what preserved the stress-decorrelation in
  §5 of the report; do **not** let two highly-correlated names both carry full risk into a shock.
- **Entry cadence:** monthly, on the h=22 roll date, choosing the listed expiry nearest **~30 DTE**
  (`yte ≈ 0.082`, i.e. 22 trading days). Non-overlapping per name, matching the frozen fold cadence.

### C.2 Structure selection (the two chosen) and strike rules

Drive strikes off the ORATS `delta` and IV columns (point-in-time, EOD).

**Workhorse — defined-risk (default for most gated names):**
- **Iron condor / iron fly** when the gate is `trade` and skew is roughly symmetric: short legs at
  **~16–20Δ** (≈ 1σ), long wings a fixed width out (e.g. 1.5–2× the short-strike gap, or ~5–8Δ) to cap the
  exact left tail the gate is meant to avoid. Iron **fly** (short ATM straddle + wings) when `vrp_score`
  is large and the gate is cleanest (max premium, still capped); **condor** when more cushion is wanted.
- **Put debit/credit-spread** when the forecast/skew leans directionally or for the most fragile names
  (e.g. `HYG`, `EEM`) — sells the rich downside vol with a hard floor.
- **Margin = width − net credit** (defined). This is what makes naked-tail size irrelevant and is why
  defined-risk is the default workhorse.

**Higher-octane — naked short strangle/straddle (gated, small):**
- Only when **gate == `trade`** (not `reduce`), `post_shock == False`, dispersion in the low/mid tercile,
  and IV percentile mid-or-higher (enough premium). Short **~16–25Δ strangle** (or ATM straddle on the
  very cleanest signals).
- **Smaller Kelly fraction** than defined-risk (undefined tail → `c_naked ≈ 0.5·c_defined`), a **hard
  per-name contract cap**, a **hard portfolio margin cap**, and a mandatory delta-band stop (C.6).
- Recommendation: **defined-risk carries the book; naked strangles are a confidence-weighted overlay on
  the top-decile gate states only.** The Stage-1 tail story is the whole reason this strategy passes —
  don't re-introduce the uncapped tail except where the gate is most certain and the size is smallest.

### C.3 Entry & gating (the EnsembleTopK signal → option order)

1. **Candidacy:** `vrp_score = iv2 − rv_hat > 0` (forecast says implied is rich vs expected realized).
2. **Regime gate** `{trade, reduce, avoid}` from `dispersion = sigma/rv_hat` vs its PIT trailing-80th /
   terciles, `post_shock`, and IV-cheap bucket. **Enter only on `trade`/`reduce`; never on `avoid`.**
   `reduce` → half the Kelly size and prefer defined-risk over naked.
3. **Expiry/strike:** nearest ~30 DTE listed expiry; strikes by Δ as in C.2.
4. **Tradability filters (from ORATS):** min open-interest / volume on every leg, max relative bid-ask
   spread, min net credit, min credit/width ratio for defined-risk. Reject illiquid legs — these are the
   real frictions Stage-1's flat bps abstracted away.

### C.4 Sizing — fractional Kelly on the VRP edge (real units)

- **Edge `μ`:** expected structure P&L = (premium collected) − (expected payout under the forecast).
  Map `vrp_score` to the structure via its **variance-vega** (∂P&L/∂realized-variance from the ORATS
  greeks/strikes), so `μ_$ ≈ vrp_score × variance_sensitivity_of_structure`.
- **Variance `σ²`:** dispersion of structure P&L from the forecast `sigma` (and, for defined-risk, the
  capped payoff truncates the left tail → use the structure's own P&L variance, not the naked one).
- **Bet:** `f = c · μ_$/σ²_$`, `c ≈ 0.25–0.35` (defined-risk), `≈0.12–0.18` (naked), then **clamp** to
  `SIZE_CAP`, to a **per-group concentration cap**, and to **available buying power / margin**.
- This is continuous with the validated Stage-1 sizer (A.5). **Negative-edge names are zeroed by the gate
  *before* Kelly** — Kelly is only ever applied to positive-edge, gated candidates.

### C.5 Exit & management (ties to Part B, arm H3)

- **30→~12 DTE:** hold (no daily re-gate — Finding #3).
- **Terminal week (~12→0 DTE), model-free mechanics:**
  - **Profit-take** at `TAKE_FRAC` (≈0.5–0.6) of max capturable credit.
  - **Variance-stop** when accrued realized variance over the trade already exceeds entry `iv2` (the
    premium is spent).
  - **Defined-risk** rides to its capped max-loss naturally; **naked** stops at `STOP_MULT·credit` or a
    delta breach (C.6).
  - **Roll-vs-close** decision: close if the next expiry's gate is `avoid`; otherwise roll the winner.

### C.6 Delta hedging — make it an ablation, default *light*

The book's edge is **vol, not direction** — at entry a symmetric strangle/straddle and a balanced
condor/fly are ~delta-neutral by construction. The question is whether to **re-hedge as spot drifts**:

- **Defined-risk condor/fly/spread:** **no continuous hedge** by default — the tail is already capped and
  hedging cost would eat the thin credit. Optionally hedge only if `|position delta|` breaches a wide band
  in the terminal week.
- **Naked strangle/straddle:** **light delta-band hedge** — re-hedge with the underlying (or a futures
  proxy) when `|portfolio delta|` exceeds, say, a fixed % of NAV. This converts the P&L toward **pure
  vol/gamma-theta** and caps the directional accident the gate doesn't address.
- **Make it an explicit ablation** (`hedge ∈ {none, terminal-band, full-band}`): delta-hedging trades away
  the favorable drift for a cleaner VRP read and adds transaction cost — Stage-2 should *measure* that
  trade-off on real marks, not assume it. Hypothesis: defined-risk wants `none`; naked wants
  `terminal-band`.

### C.7 Real frictions (finally a true cost number)

Replace Stage-1's flat per-group bps with: **ORATS bid/ask fills** (sell at bid / buy at ask, or
mid − a half-spread haircut), **per-contract commission**, **assignment/pin risk** at expiry, and
**roll cost**. This is the genuine cost test the report defers to Stage-2 — it will put a real number on
the Stage-1 break-even that currently shows a (suspiciously comfortable) ~60–80× margin.

---

## Part D — The Stage-2 option-P&L engine (**BUILT** — `stage2_trade_eval/`)

> **Status (2026-06-05): the framework in this section is implemented, imports clean, and runs
> end-to-end on the real ORATS lake; framework + smoke tests pass (`pytest stage2_trade_eval/tests`).**
> It is a *framework, not a validated result* — the correctness gates below (leakage on every path
> mark, full strike-selection validation, Stage-2 DSR re-deflation) are the M1 work that gates any
> economic claim.

It reuses the existing `trade_eval` skeleton and swaps only the P&L kernel: the **entry gate and
inverse-risk size are reused verbatim** (`trade_eval.prepare_scored` + `select_entries`), and the
engine emits the **same `LEDGER_COLS` schema** (`trade_eval.backtest.LEDGER_COLS`), so
`trade_eval.portfolio` and the Go/No-Go scoring (`reports/score_stage1.py`: DSR/CVaR/DM/bootstrap)
carry over unchanged. P&L is in **dollars for the sized position** (toggle `ROUND_TO_CONTRACTS`/`NAV`
for integer-contract buying-power realism).

**Design = three pluggable registered contracts** (mirrors `rv_eval.model_contract.Model` — add an
idea from this plan by writing one small class + `@register_*`, or drop it in `contributing.py`):

| Contract | Decides | Built-in implementations |
|---|---|---|
| `Structure` (§C.2) | gated signal → option legs | `iron_condor`, `iron_fly`, `put_credit_spread` (defined-risk); `short_strangle`, `short_straddle` (naked) |
| `ManagementArm` (§B.2) | when to leave a live trade | `hold` (H1), `forecast_regate` (H2), `mechanical_terminal` (H3 ★), `iv_regate` (H4) |
| `HedgeMode` (§C.6) | delta-hedge along the path | `none`, `terminal_band`, `full_band` |

A `Structure` only ever picks strikes (by |Δ| off the entry chain) and returns `Leg`s for one unit;
fills, marking, greeks, settlement, frictions and sizing are the engine's job.

**Module layout (`stage2_trade_eval/`):**
- `contracts.py` — `Leg`/`EntryContext`/`ExpiryChain`/`MarkRow` + the three ABCs + registries.
- `chains.py` — load/cache ORATS per ticker-year; `locate_expiry` (~30 DTE); relocate a leg on each
  later EOD for path-marking; ORATS `delta` is the **call** delta (put = `delta−1`).
- `structures.py` / `management.py` / `hedge.py` — the registered built-ins above.
- `sizing.py` — fractional Kelly = `c · (trade_eval inverse-risk size)`, capped (§A.5/§C.4).
- `marks.py` — entry fill (cross bid/ask), daily **mid** mark, expiry settlement (intrinsic),
  liquidity + credit/width filters (`Rejected`).
- `engine.py` — `run_cell(model, h, structure, mgmt, hedge)` → per-trade ledger.
- `run.py` — CLI grid driver → `results/{ledger,portfolio,manifest}`; `--list` prints the registries.
- `contributing.py` — drop-in zone for E1–E5 / new structures without touching core.
- `tests/` — framework pins (registries, well-formed legs, **P&L identity**, fill direction) +
  an auto-skipping ORATS end-to-end smoke.

**P&L convention:** realized per unit `= Σ qtyᵢ·(close_fillᵢ − entry_fillᵢ)·multiplier`; entry/close
**cross the spread** (short sells @ bid / buys back @ ask), expiry settles at intrinsic, intermediate
marks use **mid** (so management/hedge aren't double-charged the spread). `gross_pnl` is net of
bid/ask; `cost` holds commissions + slippage + hedge rebalancing.

**Correctness gates before any result is believed (M1):**
- **Leakage:** entry uses only the entry-date EOD chain + the frozen prediction available that day;
  path marks use only that day's EOD chain. *(Add a `test_leakage` mirroring `trade_eval/tests`.)*
- **P&L identity:** a held-to-expiry short structure's terminal P&L equals credit − intrinsic —
  **pinned** in `tests/test_framework.py::test_credit_and_pnl_identity`.
- **Coverage honesty:** drop names/dates with no tradable chain; never impute (matches §6).

**Scoring:** identical to Stage-1 — DSR (re-deflate by the **new** Stage-2 trial count: structures ×
mgmt-arms × hedge-modes × any tuned configs), CVaR/maxDD/worst-20, DM + block-bootstrap vs the **IV-only
option book** (same structures, flat size, no gate) as the null — already wired (`model="IV-only"`
rebuilds the benchmark in option space). **Beating the variance proxy's IV-only is not the bar; beating
an *option* IV-only seller is.**

---

## E. Sequencing, deliverables, and open risks

**Milestones**
1. **M1 — Engine skeleton + identity/leakage tests** — **scaffold DONE** (`stage2_trade_eval/` built,
   runs end-to-end on SPY 2020 iron_condor/hold/none, framework + smoke tests green, P&L identity
   pinned). *Remaining:* a dedicated `test_leakage` on the path-mark surface + full strike-selection
   validation against the chain before any number is trusted.
2. **M2 — Defined-risk book on all 10 core ETFs, H1 hold-to-expiry**, scored vs option-space IV-only on
   the **frozen** OOS (this is the headline real-P&L number; tunes nothing).
3. **M3 — Management A/B (H1–H4)** + delta-hedge ablation; pick the shipping arm (expect H3).
4. **M4 — Naked-strangle overlay** on top-decile gate states with the hard caps; measure incremental
   DSR/CVaR.
5. **M5 — Validation-safe tuning (Part A.3/A.4)** on 2018→2021, **one** confirmation pass on
   2022→2026 + full OOS. Report tuned vs frozen honestly, including negatives.

**Open decisions to confirm before M2/M5**
- **Account NAV** for the %-NAV / margin / buying-power caps (Kelly needs a capital base; default $1M,
  parameterized).
- **Kelly fraction `c`** starting points (proposed 0.30 defined-risk / 0.15 naked) and the per-group +
  portfolio margin caps.
- **Validation split** confirmation (proposed 2018–2021 tune / 2022–2026 + full OOS confirm).

**Risks carried from Stage-1 (must stay flagged in every Stage-2 report)**
- **Power, not just effect size:** ~125 monthly h=22 obs; no cell cleared absolute DSR≥0.95. Real marks
  add realism, **not** observations — the promotions remain *relative-DSR + tail-driven*, conditional, and
  the option engine cannot manufacture significance the data doesn't contain.
- **Kelly fragility:** edge mis-estimation over-bets a short-gamma tail → keep `c` low, capped, and gated.
- **Naked tail:** undefined-risk strangles re-introduce the exact exposure the study's edge is about
  avoiding — they live only on the cleanest, smallest, hard-capped sleeve.

---

*Inputs: frozen predictions (`execution/data/predictions/`), targets (`execution/data/targets.parquet`),
ORATS EOD chains (`execution/data/raw/orats/`, local). No model refits or OOS scoring performed. The Part D
engine is built as `stage2_trade_eval/` (see its `README.md`); economic results await M1 validation +
scoring. Companion: [`STAGE1_RESULTS_REPORT.md`](../trade_eval/reports/STAGE1_RESULTS_REPORT.md),
[`STAGE1_TRADING_EVAL_PLAN.md`](../trade_eval/STAGE1_TRADING_EVAL_PLAN.md).*
