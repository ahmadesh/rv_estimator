# Stage-2 Trading Evaluation — Real-Option-Marks Economic Results Report

**Scope.** Economic interpretation of the **Stage-2 option-marks** backtests on the **10 clean-core
ETFs** (`SPY QQQ IWM XLK XLF XLE TLT GLD HYG EEM`), at **30 DTE / h=22 only**, per
[`STAGE2_STRATEGY_REFINEMENT_PLAN.md`](../STAGE2_STRATEGY_REFINEMENT_PLAN.md) milestones M2–M5. This is
the *scoring/analysis layer only*: no refits, no new windows. Every number is read off the frozen
`results/` parquets produced by the W0–W5 orchestration (`RESULTS_INDEX.md`,
`_orchestrator_checkpoint.json`). The Stage-1 findings
([`STAGE1_RESULTS_REPORT.md`](../../trade_eval/reports/STAGE1_RESULTS_REPORT.md)) **bound every claim
here** and are not re-litigated.

**Reproduce:** the four artifact families under `stage2_trade_eval/results/` —
`full_oos_consolidated/` (headline, W2+W3+W4 pooled, 2018-01→2026-04, **N_TRIALS=44** global
deflation), the per-worker slices `w2/` (M2, 9 cells), `w3/` (M3, 24 cells), `w4/` (M4, 16 cells), and
`w5/` (M5 validation-window tuning, **2018-01→2021-12 only**, scored per-sweep, **never pooled**).
Each carries `scorecard / attribution / verdicts / ledger / portfolio` parquets.

**Reading protocol (the binding Stage-1 §5 caveat, carried verbatim).** At 30 DTE, IV² already prices
essentially all predictable VRP. We do **not** look for mean-return alpha. Every readout leads with
**DSR** and **left-tail** (CVaR95/99, maxDD); mean/Sharpe are supporting context. Significance vs the
**option-space IV-only** null (same structures, flat size, no gate) is HAC Diebold–Mariano +
moving-block bootstrap on common support. **A cell that wins return by fattening the tail is a FAIL.**

**Two new units of honesty Stage-2 buys that Stage-1 could not:**
1. **Real cost.** Stage-1's flat-bps haircut is replaced by true ORATS bid/ask + commission;
   `cost_frac_of_gross` is now a *measured* number, not an abstraction.
2. **Real gamma/theta.** Terminal-week management and hedging are marked on actual option greeks, so
   the M3 hypothesis ("management finally shows the early-exit benefit the variance proxy suppressed")
   gets a fair test.

**Units note.** P&L is in dollars for the fractional-Kelly-sized position (NAV=$1M); absolute dollar
magnitudes differ *across structures* because the sizer scales positions differently, so cross-structure
`ann_return` levels are **not** apples-to-apples. We therefore lead with DSR and **within-structure**
model-vs-IV tail ratios, which are the scale-robust comparisons.

---

## 0. Headline verdict

> **The Stage-1 result survives contact with real option marks — but it is now sharply
> structure-specific. The forecast's tail-control edge reproduces only on the `put_credit_spread`
> (sell the rich downside skew, defined floor); the symmetric `iron_condor` / `iron_fly` get run over
> by short-call gamma in an eight-year bull-with-spikes tape and post catastrophic tails. Management
> and delta-hedging both *destroy* value under real marks (cost + churn), and the naked sleeve does
> not earn its undefined tail. The shippable book is a single, simple structure held to expiry, no
> hedge, no management.**

**What carries forward (defined-risk, hold-to-expiry, no hedge, h=22):**

| Role | Cell (`model \| ablation`) | DSR | CVaR95 | maxDD | Why |
|---|---|---|---|---|---|
| **Primary** | `EnsembleTopK \| put_credit_spread__hold__none` | 0.865 | **−15.9** | **2.3** | Best forecast book. Gate cuts CVaR95 ~3× and maxDD ~17× vs same-structure IV-only; skew ≈ 0, sortino 2.82. |
| **Benchmark to beat (it is hard)** | `IV-only \| put_credit_spread__hold__none` | **0.919** | −53.2 | 39.1 | The option-space null *out-DSRs the forecast here* (more carry, +0.86 skew) — but with a 3× CVaR and 17× maxDD. The §5 trade-off in one row. |
| **Fallback — FAILS on real marks** | `HAR-X \| put_credit_spread__hold__none` | 0.067 | −54.2 | 55.1 | HAR-X does **not** travel to real option P&L; do not run as the fallback structure. |

**Clean No-Go's (Stage-2 specific, all h=22):**
- **`iron_condor` / `iron_fly` for every model** — symmetric short-gamma; EnsembleTopK iron_condor DSR
  0.015 (CVaR95 −119, maxDD 224), iron_fly DSR 0.001 (negative return). IV-only iron_fly is a disaster
  (CVaR95 −591, maxDD 2130).
- **All management arms** (`forecast_regate`, `mechanical_terminal`, `iv_regate`) — every one *lowers*
  DSR vs `hold` and balloons cost (M3).
- **All hedge modes** (`terminal_band`, `full_band`) — cut the tail but cost 80–2700% of gross; net DSR
  falls. Defined-risk wants `none` (plan hypothesis **confirmed**).
- **The entire naked sleeve** (`short_strangle` / `short_straddle`) — every EnsembleTopK naked cell
  loses money with a large tail (M4). It reintroduces exactly the exposure the edge is about avoiding.

**The Stage-1 power caveat persists, undiminished.** Global full-OOS deflation is **N_TRIALS=44**. **No
cell clears the absolute DSR ≥ 0.95 bar** — the best two are the *put-spread* pair at 0.92 (IV-only) and
0.87 (EnsembleTopK). Option marks added realism, **not observations** (~24–58 monthly h=22 obs per
defined-risk cell; many ablation cells have NaN DM stats from <15-date common overlap and `block_obs=2`).
Promotion remains *relative-DSR + tail-driven*, conditional, and **unconfirmed on the deliberately
unscored 2022-01→2026-05 held-out window.**

---

## 1. Method notes (so the numbers are legible)

- **Benchmark.** The null is the **option-space IV-only book**: same structure, flat size, no
  forecast/gate. Beating the *variance-proxy* IV-only is not the bar; beating an **option** IV-only
  seller is (plan §D). Attribution/verdicts are matched by structure family.
- **Deflation scope.** `full_oos_consolidated` deflates by the **global N_TRIALS=44** (all unique
  W2+W3+W4 cells). The per-worker slices (`w2`/`w3`/`w4`) deflate **locally** (N=9/24/16) for
  drill-down, so their DSRs run a touch higher than the consolidated value for the same cell (e.g.
  `EnsembleTopK | put_credit_spread` 0.851 local-W2 → 0.865 consolidated). **W5 deflates per-sweep by
  N=2** — its DSRs (0.93–0.98) are *not* comparable to the 44-trial full-OOS scale and must never be
  read as out-of-sample significance.
- **Small-n / NaN-stat honesty.** Defined-risk cells run 24–58 book observations; several ablation
  contrasts have `n_common ≤ 15` → **NaN DM stat** and a 2-observation bootstrap block. These are
  **inconclusive**, flagged inline, and never silently counted as a "win."
- **Tail metrics.** `cvar95/99` and `max_dd` are the lead. (`worst_20` = sum of the 20 worst
  observations; for high-hit-rate, small-n cells like the put-spread it can be *positive* — most months
  win — so we do not lean on its sign there; maxDD is the clean cross-cell tail metric.)

---

## 2. M2 — Defined-risk book, full OOS (the headline real-P&L number)

`{EnsembleTopK, HAR-X, IV-only} × {iron_condor, iron_fly, put_credit_spread} × hold × none`, h=22,
2018→2026, scored vs option-space IV-only. (`results/w2/`, consolidated in `full_oos_consolidated/`.)

| `model \| ablation` | n_trd | DSR | Sharpe | CVaR95 | CVaR99 | maxDD | skew | cost/gross |
|---|---|---|---|---|---|---|---|---|
| `IV-only \| put_credit_spread` | 52 | **0.919** | 1.345 | −53.2 | −67.3 | 39.1 | +0.86 | 1.6% |
| **`EnsembleTopK \| put_credit_spread`** | 37 | **0.865** | 1.209 | **−15.9** | **−29.4** | **2.3** | −0.10 | **1.2%** |
| `HAR-X \| put_credit_spread` | 47 | 0.067 | 0.25 | −54.2 | −55.1 | 55.1 | −1.56 | 4.3% |
| `IV-only \| iron_condor` | 150 | 0.028 | 0.371 | −376.4 | −589.0 | 855.7 | −1.43 | 8.5% |
| `EnsembleTopK \| iron_condor` | 102 | 0.015 | 0.209 | −119.3 | −183.0 | 224.2 | −2.39 | 10.5% |
| `HAR-X \| iron_fly` | 88 | 0.011 | 0.268 | −89.7 | −102.1 | 236.9 | — | 4.4% |
| `EnsembleTopK \| iron_fly` | 93 | 0.001 | −0.049 | −190.1 | −329.2 | 505.2 | — | 8.2% |
| `IV-only \| iron_fly` | 143 | 0.000 | −0.182 | −591.3 | −1028.5 | 2130.4 | — | 4.2% |

**Read — three findings.**

**(a) Structure is now the dominant axis, and only the put-spread works.** Every `iron_condor` /
`iron_fly` cell — forecast or IV-only — posts a DSR ≤ 0.028 and a brutal tail (maxDD 210–2130). These
sell *both* wings; in the 2018–2026 trend-with-spikes tape the short-call/short-ATM gamma gets run over
on the upside and the body gets torn in the spikes (EnsembleTopK iron_condor skew −2.39, kurt 11.6). The
`put_credit_spread` — sell the rich downside-skew vol with a hard floor, leave the upside alone — is the
*only* defined-risk structure that clears, for both the forecast and the null. **This is the cleanest
new Stage-2 result: at 30 DTE on these ETFs the harvestable, survivable VRP lives on the put side, not
in a symmetric straddle/condor.**

**(b) Inside the put-spread, the §5 tail-control story reproduces exactly.** `EnsembleTopK` vs `IV-only`
on the *same* structure: CVaR95 **−15.9 vs −53.2** (3.4× smaller), CVaR99 **−29.4 vs −67.3**, maxDD
**2.3 vs 39.1** (17× shallower), and skew pulled to ≈0. The gate is doing precisely what Stage-1 said —
sitting out the spike names, compressing the left tail — now confirmed on real marks.

**(c) …but the forecast does *not* beat IV-only on DSR here — it out-*survives*, it does not out-earn.**
`IV-only | put_credit_spread` posts the higher DSR (0.919 > 0.865), higher Sharpe (1.345 > 1.209) and
*positive* skew, because the flat seller collects more carry in a market that mostly went up. The
attribution confirms the forecast is **not** ahead on mean (`EnsembleTopK | put_credit_spread` vs IV-only:
`ann_delta −43.7`, `beat_iv_boot_p = 1.0`, DM NaN at `n_common=18`). The forecast's entire contribution
is the 3–17× tail compression. **For a short-gamma book that is the right trade — but it must be stated
plainly: on this structure the gate buys tail insurance at a cost of carry, and the absolute-DSR winner
is the naive seller.**

**(d) HAR-X does not travel to real option P&L.** `HAR-X | put_credit_spread` collapses to DSR 0.067
(CVaR95 −54.2, maxDD 55.1) — worse tail than even IV-only. The Stage-1 graceful-degrade fallback is a
fallback in *variance-proxy* space only; on real marks it should not be run as the put-spread book.
EnsembleTopK is the unambiguous primary.

**Real cost (M2's promised number).** `cost_frac_of_gross` for the clean cells: put-spread **1.2%**
(EnsembleTopK) / 1.6% (IV-only) — a 2-leg structure with tight ORATS markets; iron_condor **8.5–10.5%**
(4 legs); iron_fly 4–8%. So Stage-1's "60–80× break-even margin" was optimistic but **not fantasy for
the put-spread**: real frictions eat ~1% of gross, the edge survives them comfortably. The 4-leg
condors lose ~10% of gross to cost on top of their tail problem. (Pathological case: `HAR-X |
iron_condor` cost/gross = **538%** — when the gross edge is ≈0, cost dominates absolutely; a useful
reminder that cost robustness is conditional on there being an edge to begin with.)

---

## 3. M3 — Management × hedge ablations (`results/w3/`, EnsembleTopK only, N=24 local)

### 3a. Management arms — testing `H3 ≥ H1 > H4 > H2`

`EnsembleTopK | iron_condor`, hedge = `none`, by management arm:

| Arm | `ablation` | DSR | AnnRet | CVaR95 | maxDD | cost/gross |
|---|---|---|---|---|---|---|
| **H1 hold** | `iron_condor__hold__none` | **0.218** | 22.4 | −119.3 | 224.2 | 0.11 |
| H2 forecast_regate | `iron_condor__forecast_regate__none` | 0.075 | 2.0 | −11.6 | 48.8 | 0.51 |
| H3 mechanical_terminal | `iron_condor__mechanical_terminal__none` | 0.047 | 1.1 | −95.5 | 236.9 | **2.69** |
| H4 iv_regate | `iron_condor__iv_regate__none` | 0.012 | −8.3 | −60.6 | 151.5 | 0.42 |

**The hypothesis is rejected. Observed ranking: `H1 > H2 > H3 > H4`.** Hold-to-expiry dominates on DSR
and return. The headline expectation — that real gamma/theta marks would finally let **H3 mechanical
terminal-week management** show the early-exit benefit the variance proxy suppressed — **does not
materialize**: H3 gives back essentially all the return (22.4 → 1.1), does **not** improve the tail
(CVaR95 −95.5 vs hold −119.3 is marginal; maxDD 236.9 *worse* than hold's 224.2), and **triples-plus the
cost** (`cost/gross` 0.11 → 2.69 — the terminal-week roundtrips churn fees). This is the Stage-1 A9
"management churns at 30 DTE" finding **confirmed under true greeks**, not overturned. The only arm that
produces a small tail (H2, maxDD 48.8) does so by trading almost nothing — the A9 churn failure in a
different costume, and its DSR (0.075) is a third of hold's.

### 3b. Hedge modes — does defined-risk want `none`?

`EnsembleTopK | iron_condor`, arm = `hold`, by hedge:

| Hedge | DSR | AnnRet | CVaR95 | maxDD | cost/gross |
|---|---|---|---|---|---|
| **none** | **0.218** | 22.4 | −119.3 | 224.2 | 0.11 |
| full_band | 0.178 | 9.1 | −57.2 | 131.6 | 0.87 |
| terminal_band | 0.159 | 11.1 | −96.9 | 153.9 | 0.83 |

Delta-hedging **does** compress the tail (full_band CVaR95 −57 vs −119, maxDD 132 vs 224) — but it
costs **83–87% of gross** to do it, and the net is a *lower* DSR and most of the return gone.
**Verdict: defined-risk wants `hedge = none`** — the plan's hypothesis (§C.6) is confirmed; the capped
structure already bounds the tail, and paying ~85% of gross to hedge what is already defined is a bad
trade. (The companion hypothesis "naked wants `terminal_band`" is **not** supported — see M4: hedging
makes the naked book *worse*, `short_strangle | hold` Sharpe −0.17 → `terminal_band` −0.41.)

---

## 4. M4 — Naked overlay (`results/w4/`, N=16 local): does it earn its tail?

`{EnsembleTopK, IV-only} × {short_strangle, short_straddle} × {hold, mechanical_terminal} × {none,
terminal_band}`:

| `model \| ablation` | DSR | AnnRet | CVaR95 | maxDD |
|---|---|---|---|---|
| `IV-only \| short_strangle__hold__terminal_band` | 0.207 | 35.5 | −260.2 | 477.2 |
| `IV-only \| short_strangle__hold__none` | 0.175 | 35.4 | −481.7 | 847.2 |
| **`EnsembleTopK \| short_strangle__hold__none`** (best forecast naked) | **0.032** | **−23.0** | −147.6 | 470.0 |
| `EnsembleTopK \| short_straddle__hold__none` | 0.014 | −42.7 | −169.1 | 737.0 |
| *(all other EnsembleTopK naked cells)* | 0.00 | −28 … −69 | −34 … −105 | 239 … 722 |

**The naked sleeve does not pay and should not be shipped.** *Every* EnsembleTopK naked cell posts a
**negative annual return** and a large drawdown (maxDD 239–737); the best is DSR 0.032. The
attribution's apparent "wins" are an artifact of a catastrophic null: e.g.
`EnsembleTopK | short_strangle__mechanical_terminal__full_band` shows `ann_delta +169`,
`dm_p 0.028` vs IV-only — but only because `IV-only | short_strangle` is itself a disaster (Sharpe
−0.24, CVaR95 −622, maxDD 1558). **Beating a money-losing null while also losing money, at `block_obs=2`,
is not earning the undefined tail.** This is the Stage-1 thesis confirmed: undefined-risk strangles
reintroduce exactly the left tail the strategy's edge is built to avoid. **Keep the book defined-risk
only.**

---

## 5. M5 — Validation-window tuning (`results/w5/`, 2018-01→2021-12 ONLY, per-sweep N=2)

> **Discipline.** All W5 runs are windowed to 2018–2021 (max entry 2021-12-03; the `--end>2021-12-31`
> guard fires). The **held-out 2022-01→2026-05 window was never scored by any worker.** W5 DSRs are
> deflated by **N=2 per sweep** — they are validation-fit quality signals, **not** out-of-sample
> significance, and are not comparable to the 44-trial full-OOS scale. Base cell for all sweeps:
> `iron_condor__hold__none`. Per §A.3 we may *select* a candidate on validation under the guardrails
> (tail no-regress vs baseline; still beats IV-only on tail; gate/σ attribution positive); we may
> **not** call it confirmed.

| Sweep | Best/selected | DSR | CVaR95 | maxDD | vs frozen baseline (`p080`: CVaR95 −45.3 / maxDD 47.3) | Call |
|---|---|---|---|---|---|---|
| **E1** v2 vs v1 | `EnsembleTopK-v2` | 0.979 | −56.7 | 105.8 | **tail REGRESSES** (maxDD 47→106) | **REJECT** |
| **E2** gate pctile | `p090` (val-opt) | 0.983 | −45.3 | 47.3 | tail flat, +return | keep, but see caveat |
| **E3** σ-recal | overlay on | 0.963 | **−15.1** | **15.1** | **tail 3× better** | **SELECT (lead lever)** |
| **E4** Kelly c×cap | `c=0.25` | 0.932 | **−37.8** | **39.4** | tail-minimal; cap inactive | SELECT `c=0.25` |

**E1 — `EnsembleTopK-v2` (forecast-side).** v2 raises DSR (0.979) and Sharpe (1.288) over v1
(`e2_p080`: 0.932 / 1.014) — but **worsens the tail**: CVaR95 −56.7 vs −45.3, maxDD 105.8 vs 47.3 (2.2×).
The guardrail is explicit — *win on DSR **and** CVaR, not QLIKE.* v2 fails CVaR. **Rejected.** This is
the §A.1 prior confirmed: chasing a better `rv_hat` buys mean/Sharpe and fattens the tail — the wrong
trade for this book.

**E2 — gate percentile (`DISP_PCTILE`).** Validation-optimal is the *loosest* gate, `p090` (DSR 0.983,
AnnRet 141.8). Crucially the tail is **identical** across `p080/p085/p090` (CVaR95 −45.3) — on the
2018–2021 window, loosening 0.80→0.90 adds return at zero tail cost; the two tightest gates
(`p070` DSR 0.262, `p075` 0.570) over-throttle. **But I will not pre-register the loosening.** Setting
the gate to 0.90 *nearly disables it* (avoids only the top dispersion decile), and the gate **is** the
edge — it is the entire source of the tail control in M2. The held-out window is 2022 (rate shock, bear)
— precisely the stress regime where a disabled gate lets in the names that blow up. Loosening a tail
gate on a window that under-weights the next stress is the textbook overfit. **Pre-register the frozen
`p080`**; treat `p090`'s validation edge as a calm-period artifact pending held-out tail confirmation.

**E3 — PIT σ-recalibration (leakage-safe, lag h+1=23d).** The standout. It targets the *documented*
weakness (h=22 σ under-coverage) and **compresses the tail 3×**: CVaR95 **−15.1** and maxDD **15.1** vs
the −45.3/47.3 baseline, while holding DSR 0.963 and hit-rate 0.68. It is the most principled lever
(uses only past coverage; no `rv_hat`-chasing), and it improves exactly the axis the rules privilege.
**This is the recommended lead lever for the held-out confirmation.**

**E4 — Kelly `c` × `SIZE_CAP`.** Two clean findings: (1) **`SIZE_CAP` is inactive** — cap ∈ {2,3,4}
gives byte-identical results; the gate, not the cap, throttles concentration. (2) **`c` scales the tail
linearly** at fixed DSR (scale-invariant 0.932): `c=0.25` → CVaR95 −37.8/maxDD 39.4; `c=0.30` →
−45.3/47.3; `c=0.35` → −52.9/55.2. The tail-led pick is the **smallest fraction, `c=0.25`**, which buys
~17% tail reduction vs the 0.30 default for proportional give-up in size. **Select `c=0.25`, cap left at
3 (inactive).**

### Pre-registered config for the one-shot held-out confirmation (NOT yet run, NOT confirmed)

Per plan §A.3 step 6 — to be run **once** on 2022-01→2026-05 and on the full frozen OOS, reported
honestly including negatives, with **no re-tuning**:

> **`EnsembleTopK` · `put_credit_spread` · `hold` · `hedge=none` · frozen gate `DISP_PCTILE=0.80` ·
> σ-recalibration overlay (E3) · Kelly `c=0.25` (cap=3, inactive).**

Rationale: structure from M2 (put-spread is the only working defined-risk structure); `hold`/`none`
from M3 (management and hedging both destroy value); **σ-recal (E3) as the one tuning lever that improved
the tail without overfit**; `c=0.25` as the tail-minimal sizing; **reject v2** (tail regress) and
**reject the gate-loosening** (overfit into the stress window). **Caveat, stated up front:** the σ-recal
sweep (E3) and the Kelly/gate sweeps were run on the `iron_condor` *base cell*, not on the put-spread, so
the **combination `put_credit_spread × σ-recal × c=0.25` is itself untested** — the held-out one-shot is
its first evaluation, not a confirmation of a previously-validated joint config.

---

## 6. The real cost picture (Stage-1's deferred number, now measured)

`cost_frac_of_gross`, clean defined-risk `hold__none` cells (M2):

| Structure | EnsembleTopK | IV-only | Note |
|---|---|---|---|
| `put_credit_spread` | **1.2%** | 1.6% | 2 legs, tight markets — cheap |
| `iron_condor` | 10.5% | 8.5% | 4 legs — meaningful drag |
| `iron_fly` | 8.2% | 4.2% | (moot — negative gross) |

Hedged / managed variants are where cost turns lethal: `hold__terminal_band` / `__full_band` run
**83–87%** of gross; `iv_regate__terminal_band` hits **1415%**; `forecast_regate__full_band` **2720%**.
**Cost does not kill the put-spread book (≈1% of gross); cost is what kills every hedge and management
overlay.** Stage-1's flat-bps abstraction was directionally right for the *base* book and badly
understated the *overlays* — the opposite of where one might have feared. This is the clean Stage-2
correction to the cost story.

---

## 7. Risks & caveats (carried forward and newly sharpened)

1. **Power, not just effect size — unchanged and binding.** N_TRIALS=44 global; **no cell clears
   absolute DSR ≥ 0.95** (best: IV-only put-spread 0.919, EnsembleTopK put-spread 0.865). Defined-risk
   cells have 24–58 obs; many ablation contrasts are **NaN-DM / `block_obs=2`** and are reported as
   inconclusive, not wins. The W5 DSRs of 0.93–0.98 are **N=2 validation deflation** and do **not**
   indicate significance. Option marks added realism, not observations.
2. **The absolute-DSR winner is the naive seller.** On the put-spread, IV-only out-DSRs the forecast
   (0.919 vs 0.865). The forecast's case rests **entirely** on tail control (3× CVaR, 17× maxDD) — the
   correct axis for a short-gamma book, but an honest reader should know the forecast is buying tail
   insurance with carry, not generating alpha.
3. **Structure fragility / regime dependence.** The put-spread's dominance is partly a read on an
   eight-year up-trend: selling downside skew with the wind at your back. A prolonged grinding bear
   (the very 2022 stress in the held-out window) is where a put-spread book is most exposed — another
   reason the held-out one-shot is the real test, and another reason not to loosen the gate (E2).
4. **Kelly fragility.** Confirmed live: `c` scales the tail linearly (E4). The sizer is honest but
   unforgiving — over-estimating the edge over-bets a short-gamma tail. Hence the recommendation of the
   *lower* `c=0.25`, capped, and gated.
5. **Naked tail — empirically a No-Go.** M4 shows the naked sleeve loses money and re-imports the tail.
   Do not ship it; if ever revisited, only on the very cleanest, smallest, hard-capped gate states, and
   only with a held-out mandate.
6. **Held-out window never scored.** 2022-01→2026-05 was deliberately untouched. **No claim in this
   report is out-of-sample confirmed.** The §A.3 step-6 one-shot is a separate, not-yet-run step.

---

## 8. What to ship, and what to confirm next

**Ship (subject to the held-out confirmation below):** a **single, simple book** — `EnsembleTopK`
gated, **`put_credit_spread`** at ~30 DTE, **held to expiry, no delta hedge, no terminal-week
management**, one position per correlation group, fractional-Kelly `c=0.25` capped, with the **PIT
σ-recalibration** overlay (E3) feeding the gate/size. Everything fancier that was tested — symmetric
condors/flies, daily re-gating, mechanical terminal management, delta-band hedging, the naked overlay,
the v2 forecaster, the loosened gate — **measurably hurts** on real marks (tail, cost, or both). The
Stage-2 result is a *subtractive* one: the discipline is in what you don't do.

**Confirm next (one shot, no re-tuning):** run the §5 pre-registered config —
`EnsembleTopK · put_credit_spread · hold · none · gate p080 · σ-recal · c=0.25` — **once** on the frozen
**2022-01→2026-05 held-out window** and on the full OOS, and report it against `IV-only |
put_credit_spread` on DSR and (decisively) CVaR95/maxDD. The bar is **tail no-regress vs the IV-only
put-spread under the 2022 stress**; if the gate's tail compression survives the rate-shock bear that the
validation window under-weights, the book is real. If it does not, that is the finding — and per §A.3 it
is reported as a negative, not re-tuned away. The one genuinely untested joint is `put_credit_spread ×
σ-recal`; the held-out run is its first and only evaluation.

---

*All numbers: Stage-2 ORATS option marks, 10 clean-core ETFs, h=22, 2018→2026 frozen OOS, common
support, no refits. Headline deflation N_TRIALS=44 (`full_oos_consolidated/`); per-worker slices
N=9/24/16 (`w2`,`w3`,`w4`); W5 validation N=2/sweep (2018–2021 only). Held-out 2022→2026 never scored.
Companion: [`STAGE2_STRATEGY_REFINEMENT_PLAN.md`](../STAGE2_STRATEGY_REFINEMENT_PLAN.md),
[`STAGE1_RESULTS_REPORT.md`](../../trade_eval/reports/STAGE1_RESULTS_REPORT.md).*
