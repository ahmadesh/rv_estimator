# Hole-Digging & Improvement Program — Consolidated Report

_Frozen spec v1.0 (`conclusion/FROZEN_STRATEGY_SPEC.md`, cross 0.66 / mid 0.93) attacked on 9
fronts and extended on 5 · all experiments run 2026-07-09 · checkpoint ledger
`execution_plan/HOLE_DIGGING_2026_07.md`_

## TL;DR

The edge is real but the headline flatters it. The selection signal survives every falsification
attack thrown at it (timing lag, random-pick null, crash-factor regression, recency); the
**numbers** shrink under honest accounting (true MTM 0.55 vs 0.66; deflated Sharpe 0.59 after
multiplicity; 31% of booked size was never tradeable). The single best discovery is defensive:
**capping size at resting open interest raises Sharpe to 0.89 cross / 1.06 mid and halves maxDD**
— the infeasible size was negative-carry. The v1.1 additive pair-core+overlay design is rejected.

## 1. Holes dug — what survived, what didn't

| # | Attack | Verdict | Artifact |
| --- | --- | --- | --- |
| A1 | Same-day signal→fill coupling (spec §6.4) | **Mostly defused.** T+1-executable book: 0.54 cross / 0.80 mid (vs 0.66/0.93). Lagging either score component alone ≈ lagging both, and mid degrades no more than cross ⇒ timing sensitivity of the top-2 boundary, not quote-noise harvesting. ~0.12 Sharpe of the headline is same-day-timing dependent. | `xsec_putspread_report_lag1{,iv,rv}.md` |
| A2 | Size vs open interest | **Hole confirmed.** 31% of trades exceed the worse leg's resting OI (wing p95 9.7×, p99 23.6×); that bucket nets **−3%** of book P&L. 80% of P&L sits below 0.25× OI. The profitable core is deliverable; the booked size is not. → spawned I5. | `frozen_forensics.md` |
| A7 | Fill quality under stress | **Defused.** Entry friction ≈ 7% of mid credit, flat across VIX quintiles (Q5 6.7–7.2% vs Q1 9.2%); the top-VIX quintile carries $1.06M of $1.92M cross P&L. No hidden stress-fill tax. | `frozen_forensics.md` |
| A8 | Settlement realism | **Minor.** 8.3% of trades settle within ±1% of the short strike (pin zone); 272 breaches, 102 on distribution-paying ETFs (early assignment unmodeled); USO 1:8 reverse split mishandled on 1 trade (immaterial). Worth a line in the spec's caveats, not a re-run. | `frozen_forensics.md` |
| A3 | Realization-dated P&L (spec §6.2) | **Headline flattered.** True daily-MTM Sharpe **0.55** vs 0.66; daily-path maxDD $502k; worst MTM month 2019-05 −$264k (a vol chop, not a crash); era 2018–21 drops 0.67→0.51. Same total P&L by construction — only the path. | `frozen_mtm.md`, `frozen_mtm_daily.csv` |
| A4 | Config multiplicity (plateau map) | **Mixed.** Δ/gate axes are a plateau (0.59–0.66 cross); wingΔ 0.15 sags (0.43). The DTE axis is NOT flat: 21-DTE craters to **0.21**; **45-DTE beats frozen (0.83 cross / 1.03 mid, +$228k, lower maxDD)**. Frozen 30-DTE is not a selected peak (money was left toward 45), and expiry must sit ≥ the h=22 forecast horizon. Neighborhood mean cross 0.57 ≈ honest expectation. | `xsec_putspread_plateau.md` |
| A5 | Random-pick P&L null | **Selection is real in dollars.** Random 2-of-cohort through the identical gate/walk/engine: null Sharpe **0.16 ± 0.09** (10 reps, stopped early — conclusion settled) vs frozen 0.66, ≈5.5σ. Reconciles with §6.6: the SPY/QQQ pair ties at cross because of its *execution* edge, not because selection doesn't matter. | `xsec_putspread_nullpick.md` |
| A6 | Crash-factor compensation | **Alpha survives.** Monthly P&L ~ SPY + min(SPY,0) + ΔVIX (Newey-West): residual α **$199k/yr, t=2.75**; crash-convexity β 0.45 confirms the book is short the crash factor, but it is not *only* that (R²=0.26). | `frozen_stats.md` |
| A9 | Edge recency | **No decay.** Trailing-2y rank-IC +0.205 vs full-sample +0.248; 2025 = +0.299; 2026 partial-year thin (15 cohorts, +0.087). | `frozen_stats.md` |
| — | Honest Sharpe | Bootstrap 90% CI on the 0.66: **[0.22, 1.15]**. Deflated Sharpe vs the 18 documented tried variants: **0.59** (0.45 under an N=40 undocumented-forks scenario) — i.e. after multiplicity, roughly a coin-flip that the true SR > 0. The pre-registered §7 shadow run remains the only decisive test. | `frozen_stats.md` |

## 2. Improvements tested

| # | Lever | Verdict | Artifact |
| --- | --- | --- | --- |
| I5 | **OI-capped sizing** (born from A2) | **ADOPT-CANDIDATE.** contracts ≤ frac·min(leg OI): frac=0.25 ⇒ **0.89 cross / 1.06 mid**, maxDD $218k; frac=0.5 ⇒ 0.89/1.08, cross P&L $1.95M ≥ frozen with **maxDD halved** ($244k vs $434k) and 27% less margin/trade. PIT, liquidity-motivated, no performance peeking — removing size that couldn't fill deletes negative-carry exposure. The capacity-honest book clears the Sharpe ≥ 1 hurdle at mid fills. | `xsec_putspread_oicap.md` |
| I1 | Fill-capture curve (fill = mid + λ·half-spread) | Model beats the pair at every λ, but its alpha over the pair decays $37k/yr (IR 0.24) at λ=0 → $9k/yr (IR 0.06) at λ=1. **Breakeven ≈ full crossing**: any live capture below λ=1 is what pays for running the model. Shadow-run pass criterion: demonstrate λ < 1 at ~100-contract clips. | `xsec_putspread_lambda.md` |
| I2 | v1.1 pair-core + non-pair overlay (§8.6) | **REJECTED.** cross 0.44 / mid 0.67. Additive sleeves double gross short-vol (sleeve corr 0.47) and the pair-less overlay loses QQQ, its best name ($531k cross). §8.6's blend works only as two whole books at half size each (0.74 cross, §6.6) — a capital-allocation choice, not a new strategy. | `xsec_putspread_v11.md` |
| I4 | Crash-gate integration (§8.2) | **Already closed by prior work** (memory `crashhedge-rejected-2026-07`): keeper = conditional `vix≥vix3m · φ=0.20 · 0.10Δ/30` hold hedge — Sharpe-neutral, halves the COVID tail, not a maxDD fix. ⚠ Those experiment artifacts were never committed (verified against git); numbers survive only in the memory note — rebuild before re-litigating. | — |
| I3 | Vol-targeted sizing | **REJECTED.** EWMA book-vol targeting (1-day lag, mean-leverage-normalized) on the true MTM path: Sharpe 0.55 → **0.46 daily / 0.47 monthly**, maxDD +~50%. Mechanism: the book's realized vol is lowest right *before* vol events, so trailing-vol targeting levers up into the storm — anti-signal for a short-vol book (same physics as the rejected VIX/IV-rank entry gates). | `frozen_voltarget.md` |

## 3. What this changes about the deployment picture

1. **The honest v1.0 expectation band is lower than the spec's.** Stack the haircuts that apply
   simultaneously: realization-dating (−0.11), T+1 execution (−0.12 if you can't trade at the
   signal close), neighborhood-mean vs peak (−0.09). A live v1.0 at cross-ish fills is a
   ~0.4–0.55 Sharpe book, consistent with the spec's own §7 pass threshold (>0.4) — the shadow
   run's bar is set about right.
2. **The OI cap should be in any deployed version.** It is the rare change that is simultaneously
   more honest and better on every measured axis. At real capital it is not optional: the
   uncapped book *assumes* fills that exceed resting OI on a third of its trades.
3. **Execution is the whole margin over the trivial pair** (I1 confirms §6.6 quantitatively).
   If the desk can't beat full-spread crossing, trade the pair and keep the model as research.
4. **Don't add sleeves; blend books.** The additive core+overlay design is dead; the §6.6
   half-and-half blend (0.74 cross) remains the only blend worth carrying forward, and it's
   an allocation decision on two already-specified books.
5. **A v1.1 spec worth writing** (ex-ante, resets the §7 clock): frozen selection + OI-cap 0.25–0.5
   + (optionally) 45-DTE — but the 45-DTE observation carries fresh multiplicity debt from this
   very sweep and must be treated as a hypothesis, not a result.

## 4. Multiplicity self-accounting

This program itself explored ~20 new cells (8 plateau neighbors, 4 OI fractions, 5 λ points, 2 lag
decompositions, 1 v1.1). The *attacks* (A1–A9) spend no multiplicity — they could only have hurt
the headline. The *improvements* do: the OI-cap's 0.89/1.06 is a 4-cell selection (though monotone
and mechanism-backed), and 45-DTE is a 9-cell selection. Both belong in a v1.1 spec that clears
§7, not in the v1.0 record.

## 5. Recommendations — what to add / remove in `FROZEN_STRATEGY_SPEC.md`

The spec's own rule (§0): any §2 change is a new version and resets the §7 clock. So the
recommendations split into (A) documentation fixes to the v1.0 doc that change no trading rule,
(B) the §2 changes that should define v1.1, and (C) things to explicitly NOT change.

### A. Add to the v1.0 doc now (no version bump — these correct the record)

1. **§6.2 (realization-dated P&L)** — replace the qualitative warning with the measured number:
   true MTM Sharpe **0.55 cross** (vs 0.66), daily-path maxDD **$502k**, worst MTM month
   2019-05 −$264k (`frozen_mtm.md`). The §7 pass criteria should be read against 0.55, not 0.66.
2. **§6.1 (multiplicity)** — quantify it: deflated Sharpe **0.59** vs the 18 documented forks
   (0.45 at N=40); bootstrap 90% CI on the 0.66 = **[0.22, 1.15]** (`frozen_stats.md`).
3. **NEW caveat §6.7 — capacity**: 31% of trades exceed the worse leg's resting OI (wing p95
   9.7×); that slice nets −3% of P&L. Both fill bounds are fiction for that slice at booked size
   (`frozen_forensics.md`).
4. **§6.4 (same-day signal→fill)** — resolve it with the measurement: T+1 execution keeps
   0.54/0.80; the coupling is timing sensitivity, not quote-noise harvesting
   (`xsec_putspread_report_lag1*.md`).
5. **NEW caveat §6.8 — settlement model limits**: 8.3% pin-zone settles, early assignment
   unmodeled on 102 breached div-payer trades, corporate-action strikes taken as listed (USO
   1:8 split mishandled once, immaterial) (`frozen_forensics.md`).
6. **§4.3 (edge is not luck)** — add the two missing legs: random-pick P&L null (0.16 ± 0.09 vs
   0.66, ≈5.5σ — selection pays in dollars through the full engine), and the factor regression
   (residual α $199k/yr, t=2.75 after SPY / crash-convexity / ΔVIX betas).
7. **§5 rejected table** — append: additive pair-core+overlay (0.44/0.67), trailing-vol-targeted
   sizing (0.55→0.46, levers into storms), and — flagged as *findings whose artifacts were lost,
   rebuild before re-litigating* — the always-on crash hedge, spike monetization, VIX entry gate,
   IV-rank entry gate (memory `crashhedge-rejected-2026-07`).
8. **§8 levers** — update in place: §8.1 execution is now quantified (α over the pair $37k/yr at
   mid → $9k/yr at full cross; breakeven ≈ λ=1); §8.2 is closed (conditional hedge = qualified
   keeper, artifacts lost); §8.3's MTM prerequisite now exists (`frozen_mtm_daily.csv`); §8.6 in
   its additive form is dead — only the half/half whole-book blend (0.74 cross) survives.
9. **§7 shadow-run metrics** — add two recorded quantities: realized fill-λ per trade (must
   demonstrate λ < 1, else trade the pair) and contracts/OI per leg at entry (audits caveat 6.7).

### B. Define v1.1 with exactly these §2 changes (version bump, full §7 evaluation)

1. **ADD sizing rule (the one clear adopt): contracts ≤ 0.25 × min(short-leg OI, wing OI)** at
   entry; skip if the cap rounds to zero. Backtest: 0.89 cross / 1.06 mid, maxDD halved, less
   margin — dominates v1.0 on every axis *and* removes untradeable size (`xsec_putspread_oicap.md`).
   Prefer 0.25 over 0.50 as the honest primary (0.50's extra P&L rides thinner books).
2. **CONSIDER (hypothesis only): TARGET_DTE 30 → 45** (tolerance [35, 60]): 0.83/1.03 with lower
   maxDD, and mechanism-consistent (expiry ≥ h=22 horizon). Born from a 9-cell sweep on this
   sample — carries multiplicity debt; if included, the shadow run is its only test.
3. Nothing else. One version, at most these two changes — every additional knob re-inflates the
   fork count that A4/DSR just measured.

### C. Do NOT change (attacks it survived / negative results)

- The **forecaster, score, gate (score>0), K=2, weekly cadence, tradeable-walk** — selection is
  ≈5.5σ outside the random-pick null; leave the machine alone.
- The **hold-to-expiry exit** — managed exits already rejected (§5); vol-targeted sizing now
  joins them (levers into storms).
- **21-DTE or tighter expiries** — the one direction that kills the edge outright (0.21).
- **No additive sleeves** (pair-core+overlay rejected); blending with the SPY/QQQ book is a
  capital-allocation decision outside the spec.
- The **wing at 0.10Δ** — 0.15Δ sags to 0.43; 0.05Δ costs P&L; the frozen wing is fine.

## 6. Artifact inventory (all in `strategy_backtest/results/` unless noted)

- `xsec_putspread_report_lag1.md` / `_lag1iv.md` / `_lag1rv.md` (+ trades CSVs) — A1
- `frozen_forensics.md` + `frozen_forensics_trades.parquet` — A2/A7/A8
- `frozen_mtm.md` + `frozen_mtm_daily.csv` — A3 (input for I3/blending)
- `xsec_putspread_plateau.md` — A4 · `frozen_stats.md` — A6/A9/honest-Sharpe
- `xsec_putspread_nullpick.md` — A5 · `xsec_putspread_lambda.md` — I1
- `xsec_putspread_oicap.md` — I5 · `xsec_putspread_v11.md` (+ trades CSV) — I2
- Experiments: `experiments/{xsec_putspread_lag,frozen_forensics,frozen_stats,frozen_mtm,xsec_putspread_plateau,xsec_putspread_nullpick,xsec_putspread_lambda,xsec_putspread_oicap,xsec_putspread_v11}.py`
