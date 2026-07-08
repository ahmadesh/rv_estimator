# Entry-Cadence Experiments — Frozen Put-Spread Book

_Run 2026-07-08 · companion to `FROZEN_STRATEGY_SPEC.md` · all in-sample 2010→2026, NAV $2M, b=0.02_

**Question.** The frozen book (`FROZEN_STRATEGY_SPEC.md` §2.3) rolls "every 5th trading day of the
prediction calendar" (`ROLL_EVERY=5`), opening the **two** richest tradeable names on a single entry
day whose weekday floats. Does re-timing entries — a fixed weekday, or splitting the two spreads
across two days — improve risk-adjusted return?

**Answer: no.** Cadence is not a free Sharpe lever. Concentrating both spreads on **Monday** is the
best in-sample cadence; every split/exclusion variant is dominated by it. The durable results are the
structural/negative ones; the Monday edge itself is a multiplicity-inflated point estimate that still
needs the §7 shadow run before it can be banked.

Only the **entry timing / count-per-day** changed — universe, de-biased score, `score>0` gate,
tradeable-walk, structure, sizing, fills and settlement are the frozen book, imported verbatim so
the comparison is apples-to-apples.

## Master table (Sharpe monthly; maxDD = cross)

| # | cadence | spreads/wk | entry days/wk | **Sharpe cross** | **Sharpe mid** | **maxDD** | P&L cross |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | **Monday, top-2** | 2 | 1 (Mon) | **0.78** | **1.04** | **$433k** | $2.41M |
| 2 | Thursday, top-2 | 2 | 1 (Thu) | 0.71 | 0.98 | $414k | $2.21M |
| 3 | roll5, top-2 (**frozen baseline**) | 2 | ~1 (floats) | 0.66 | 0.93 | $443k | $1.91M |
| 4 | Tue / Wed / Fri, top-2 | 2 | 1 | 0.55 / 0.48 / 0.52 | 0.78 / 0.74 / 0.82 | — | — |
| 5 | split: Mon#1 + Thu#1, no exclusion | 2 | 2 | 0.75 | 1.01 | $571k | $2.41M |
| 6 | split + symmetric exclusion | 2 | 2 | 0.67 | 0.94 | $449k | $2.07M |
| 7 | split + Thursday-only exclusion | 2 | 2 | 0.67 | 0.93 | $484k | $2.10M |

Ranked by cross Sharpe: **Mon top-2 (0.78) > split-no-excl (0.75) > Thu top-2 (0.71) > both-excl
variants ≈ roll5 (0.66–0.67) > Tue/Fri/Wed.**

## The four experiments

### A. Weekday sweep — which fixed day is best (`xsec_putspread_dow.py`)
Replace the every-5th-day rule with a **fixed ISO weekday** (holiday fallback to the nearest
later-then-earlier trading day that week), both spreads on that day.

- **Monday wins decisively** (0.78/1.04), beating the floating baseline by +0.12 cross / +0.11 mid
  and +$0.49M P&L at similar maxDD. Thursday second (0.71). Tue/Wed/Fri all *worse* than baseline.
- Economically plausible: entering Monday sells the fresh weekend-gap risk premium; the 30-DTE exit
  lands mid-week. Monday is strong in every era except the flat-vol 2014–17 stretch (weak for all).
- Cohort counts barely differ (776 roll5 vs ~805 weekday), so the gap isn't a trade-count artifact.

### B. Split, no exclusion — Mon top-1 + Thu top-1 (`xsec_putspread_split.py`)
Same two-spread weekly budget, but one spread Monday and one Thursday, each the single richest
tradeable name that day.

- **Same P&L as Monday-only ($2.41M), but maxDD jumps ~30% → $571k** and Sharpe is a touch lower.
  Staggering entry timing **hurt** risk-adjusted return.
- Why: the book's dominant risk is a **common short-vol crash factor** (spec §4.2, no √N scaling) —
  a vol spike marks down the Monday and Thursday spreads together, so splitting buys ~no
  independence. It merely reshuffled *which* crashes it stood in front of (strong 2018–21, weak
  2022–26 — the mirror of Monday-top-2).

### C. Split + symmetric exclusion (`xsec_putspread_split_excl.py`)
Each entry day skips the name the previous entry opened (Thu excludes Mon; Mon excludes last Thu),
to test whether name-overlap (not the crash factor) caused B's extra drawdown.

- **Confirms the diagnosis: maxDD $571k → $449k**, back in line with the single-day books —
  name-overlap *was* the source of B's extra drawdown.
- **But the exclusion fired on 36% of entry dates (612 / 1702)** — the top cross-sectional pick is
  *sticky*, often still the richest 3 days later — so it repeatedly forces the trade onto the
  2nd-best (less rich) name. That costs edge: Sharpe 0.75 → 0.67, P&L −$0.34M.
- Upside: **most era-stable variant** (mid Sharpe 0.88–1.05 across all four eras).

### D. Split + Thursday-only exclusion (`xsec_putspread_split_thuexcl.py`)
Asymmetric: Monday picks freely; only Thursday skips that week's Monday name.

- **Isolates where the cost lives: the entire Sharpe hit comes from the *Thursday* constraint, not
  Monday.** Thu-only and symmetric both land at 0.67 cross — freeing Monday recovered nothing,
  because Monday rarely wanted to repeat the older Thursday name.
- **Thu-only is the worst exclusion option**: it pays the full Sharpe cost of constraining Thursday
  yet keeps more name-overlap than symmetric → *higher* maxDD ($484k vs $449k). Symmetric dominates.

## Takeaways

1. **Both spreads on Monday is the best in-sample cadence** — nothing beat it on Sharpe or maxDD.
2. **Splitting entry days never improves risk-adjusted return** — the risk is a common crash factor,
   not name concentration, and staggered entries can't diversify it.
3. **Exclusion rules only reshuffle drawdown, capped at ~0.67 Sharpe** once Thursday is forced off
   the sticky top name. Symmetric exclusion is the cleanest (fixes overlap DD, most era-stable) but
   still gives up ~0.1 Sharpe vs plain Monday.
4. **New structural facts learned** (model-independent, robust): the top cross-sectional pick is
   ~36% sticky across a 3-day gap; there is a real Monday weekend-vol effect; entry timing cannot
   touch crash-factor risk.
5. **Caveat.** All of the above is an in-sample cadence search on the same 2010→2026 data the book
   was tuned on — picking "Monday" adds a multiplicity layer on top of §6.1. Treat the Monday edge
   (~+0.12 Sharpe) as an upper bound. Per §7, a cadence change is a spec change ⇒ version bump ⇒
   re-run the pre-registered shadow evaluation before deploying.

## Reproduce

```bash
.venv/bin/python -m strategy_backtest.experiments.xsec_putspread_dow          # A: weekday sweep
.venv/bin/python -m strategy_backtest.experiments.xsec_putspread_split        # B: split, no exclusion
.venv/bin/python -m strategy_backtest.experiments.xsec_putspread_split_excl   # C: symmetric exclusion
.venv/bin/python -m strategy_backtest.experiments.xsec_putspread_split_thuexcl # D: Thu-only exclusion
```

Reports land in `strategy_backtest/results/xsec_putspread_{dow,split,split_excl,split_thuexcl}_report.md`;
per-cadence cross-fill ledgers alongside them.
