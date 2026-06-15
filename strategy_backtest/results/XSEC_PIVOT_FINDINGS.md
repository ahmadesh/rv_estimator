# Cross-Sectional VRP Ranking — Can It Carry a Sharpe ≥ 1 Strategy?

_Follow-up to `BACKTEST_REVIEW_AND_VERDICT.md` · built & tested 2026-06-12 · question: the ranking
signal looks like real edge — can a strategy on it (any structure, incl. straddles) reach Sharpe > 1
or close?_

---

## TL;DR — honest answer

**Demonstrated today: Sharpe ~0.68–0.85, positive in every era and strongest in the recent ones.
Sharpe ≥ 1 is plausible but not yet demonstrated; the binding constraint is breadth (10 names), not
the signal.**

- The signal's ceiling is enormous: a paper variance-swap long/short on the ranking runs **Sharpe ~4
  in log space** (era Sharpes 3.9 / 6.1 / 4.5 / 3.1), rank IC = 0.349 (t = 29), positive **every
  single year** 2010–2026.
- The naive market-neutral expression (long/short delta-hedged ATM straddles) **fails on friction**:
  +$1.40M mid-to-mid but −$1.22M after crossing real spreads — and its long-vol side loses even
  frictionless (the universal VRP level taxes any long-vol leg ~$1M over the sample).
- The best tradable expression found: **top-2-ranked put-credit spreads** (selection replaces the
  G2/G3/G4 gates, which were collapsing the cross-section to ~1 name per date). With real crossed
  fills: **Sharpe 0.68**, $1.41M, 87% win, era Sharpes **0.95 / 0.18 / 0.77 / 0.83** — alive
  post-2018, unlike the original book (−0.27 / −0.42). Mid fills bound it at **0.85** (spread cost
  is 23% of gross; realistic execution lands ~0.75–0.80).
- A second sleeve exists: top-3 **short-only delta-hedged straddles** earn **Sharpe 0.70 on a true
  daily-MTM basis even paying full spreads** — but with naked-short tails (worst day −$105k per
  $3k vega/week book).

## 1. Signal-space ceiling (Stage A)

Score = log(iv2) − log(rv_hat_cal) (PIT de-biased, 22-day embargo). Outcome = next-22d realized
richness. Weekly cross-section of 10 names, 2010–2026, 815 weeks:

| Construction (paper, no costs) | Sharpe | 2010–13 | 2014–17 | 2018–21 | 2022–26 |
| --- | --- | --- | --- | --- | --- |
| L/S top/bottom-3, variance units | 0.71 | 1.77 | 3.14 | 0.14 | 1.81 |
| L/S top/bottom-3, **log units** | **4.12** | 3.89 | 6.13 | 4.48 | 3.06 |
| same, model-free control (IV vs trailing-RV) | 3.40 | 4.27 | 3.62 | 3.32 | 2.95 |
| same, static per-name carry control | 2.53 | 2.47 | 4.24 | 2.13 | 1.79 |
| **model residual** (orthogonal to static carry) | **2.78** | 3.14 | 3.02 | 3.39 | 2.06 |

Reads: (a) the variance-unit L/S is wrecked by one month (Mar-2020 = −24σ-equivalents) because
trailing betas can't see crash convexity; log units cancel the common multiplicative vol shock
exactly in a zero-net basket — that's the construction that shows the true ceiling. (b) Much of the
premium is harvestable model-free, **but the model adds a genuine, era-stable ~2.8-Sharpe residual**
on top of static name carry. (c) Basket turnover is ~39%/week; HYG sits in the short basket 92% of
weeks.

## 2. What failed, and why it's informative (Stage B)

**L/S delta-hedged ATM straddles (the "correct" market-neutral expression).** Weekly top/bottom-3,
$1k vega/name, daily EOD hedge, hold to expiry, real ORATS marks, true daily MTM:

| Variant | P&L | Sharpe (daily MTM) |
| --- | --- | --- |
| full spread crossing | −$1,219,384 | −0.50 |
| 25% of half-spread | +$144,896 | 0.06 |
| frictionless (mid fills) | +$1,397,679 | 0.57 (positive all four eras) |
| 60-DTE variant, 25% half-spread | +$712,186 | 0.21 |
| **short-side only, full crossing** | **+$1,324,379** | **0.70** (1.23 / 0.68 / 0.68 / 0.17) |

Three lessons. (1) **Friction, not signal**: the book makes $1.4M mid-to-mid; ATM straddle entries
on 6 names/week eat $2.6M. Cadence can't fix it (cost and gross both scale per position). (2) **The
long-vol leg never pays in dollars** (−$1.0M even frictionless, 38% win): the cheap-ranked names are
still absolutely rich (the universal VRP level), so "long the cheapest" is a hedge you pay ~$60k/yr
for — and it didn't even improve the Sharpe (0.57 L/S vs 0.70 short-only). (3) Straddle path noise
(gamma drifting off-strike, discrete hedging) dilutes the paper Sharpe ~6× before any costs.

**Entry cost map** (median half-spread as % of straddle premium): SPY/QQQ/IWM 0.5–0.6%, GLD 1.0%,
TLT 1.5%, XLE/EEM/XLF/XLK 2.1–2.7%, **HYG 6.1%**. Costs halved in the 2022–26 era (0.99% median) —
live trading today is cheaper than the backtest average.

## 3. What works: rank-selected put-credit spreads (the pivot candidate)

The review showed the original book's fatal flaw was trading *every* gated candidate with VRP only
as a size tilt. Flipping that — **the ranking is the gate** — and using the structure whose cost
profile the original book already validated (spread cost ≈ 13–23% of gross, vs ~190% for ATM
straddles):

Top-K by score each week → 0.25Δ/0.10Δ put spread, ~30 DTE, hold to expiry, flat size, engine
group-margin cap, G7 liquidity intact, **no G2/G3/G4** (they leave only one candidate on 63% of
dates — there is no cross-section after them). HYG excluded ex-ante on liquidity (6.1% half-spread;
it hogged 45% of top-2 slots and mostly rejected at fill time — and contributed −$12k when it did
fill, so nothing real is lost):

| Book (real ORATS fills) | trades | P&L | Sharpe (monthly) | 2010–13 | 2014–17 | 2018–21 | 2022–26 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ORIGINAL book (review baseline) | 1,508 | $287k | 0.39 | 0.78 | 1.14 | **−0.27** | **−0.42** |
| top-2, cross fills | 903 | $1,407k | **0.68** | 0.95 | 0.18 | **0.77** | **0.83** |
| top-2, mid fills (execution bound) | 978 | $1,823k | **0.85** | 1.27 | 0.48 | 0.87 | 0.79 |
| top-3, cross fills | 1,315 | $1,605k | 0.54 | 0.60 | 0.28 | 0.69 | 0.60 |

The era pattern inverts vs the original book: this design is **strongest after 2018** — consistent
with the signal decomposition (the cross-sectional residual held up while the aggregate VRP level
died). Equity curves (mid vs cross) + annual P&L: `xsec_putspread_pnl.png` — 14 of 17 years
positive on mid fills (losers: 2015 −$37k, 2016 −$54k, 2022 −$145k).
Reproducible: `.venv/bin/python -m strategy_backtest.experiments.xsec_putspread_topk`
(artifacts: `xsec_putspread_report.md`, `xsec_putspread_trades.csv`; straddle prototype:
`xsec_straddle.py`).

## 4. Honest caveats before believing 0.68–0.85

1. **Multiplicity.** Structure, K, log-space scoring, and the HYG exclusion were all chosen looking
   at this sample (the HYG rule and "selection not tilt" have ex-ante rationales, but I saw the
   numbers). The true expectation is below the reported point estimates.
2. **Basis.** The put-spread books are realization-dated (no MTM), the same flattering basis the
   review criticized — expect the MTM Sharpe somewhat lower (the straddle sleeve numbers ARE MTM).
3. **Fills.** "Cross" is worst-case, "mid" best-case; truth in between, era-dependent.
4. **Concentration.** QQQ is the most-selected name (246/903 trades, $401k); TLT remains a loser
   even when ranked rich (−$91k) — worth a pre-registered look, not an ex-post exclusion.

## 5. The road to Sharpe ≥ 1 — ranked

1. **Breadth (the structural lever).** 10 names → 30–50 liquid optionable names. IC 0.349 with
   breadth ~9 yields paper Sharpe ~4; the tradable book captures ~0.2 of the ceiling. Fundamental-law
   scaling says 3–5× the names ≈ √3–√5 × the Sharpe: even capturing it imperfectly puts ≥1 well in
   range. Cost: extend the minute-RV ingestion + ORATS download + EnsembleTopK walk-forward to the
   wider universe (the pipelines exist; it's compute + disk, not new research). Local chains already
   hold KRE/USO/SPX/IBIT as a first increment.
2. **Sleeve combination.** Put-spread top-2 (realization-lumpy, defined-risk) + short-straddle top-3
   (daily MTM, vega-clean) monetize the same ranking through different P&L paths; a vol-weighted
   blend should land between 0.75 and 0.95 before breadth. Needs the put-spread sleeve re-marked MTM
   for an apples-to-apples covariance estimate.
3. **Execution.** The 0.68→0.85 gap is pure fill quality on ≤ ~$40k-risk clips in liquid ETF
   options — patient limit orders near mid are realistic for this size; assume ~half the gap.
4. **Then stop tuning.** Freeze the spec (universe, K, score, structure, sizing), pre-register the
   evaluation (monthly MTM Sharpe, bootstrap CI, per-era table), and run 2022+ as the headline
   out-of-sample window — or better, paper-trade it live for two quarters; the signal trades weekly,
   so ~26 fresh cohorts arrive in 6 months.

## Bottom line

The ranking is the real edge the original project accidentally built, and it survives contact with
real option markets when expressed as **selection in a cost-efficient defined-risk structure**:
0.68–0.85 era-stable Sharpe today against your ≥1 hurdle. The gap is closable — by breadth most of
all — and the failure mode that killed the original book (aggregate short-vol beta decay) is
demonstrably not what this design depends on.

---

# Addendum (2026-06-12): the breadth experiment — 9 → 29 names

The §5.1 hypothesis was run for real: 20 new ETFs staged from Ex-Disk (sector SPDRs XLI/XLU/XLP/
XLV/XLY/XLB, DIA, EFA/FXI/EWZ, GDX/SLV/USO/XOP, SMH/XBI/IBB/KRE/XRT/IYR), the full pipeline
(minute-RV inputs → features → 4 HAR walk-forwards → EnsembleTopK) rebuilt into
`data_wide/` (30 names, 616,765 OOS predictions, 2010→2026; core-name predictions reproduce the
original cache **bit-exact**, confirming per-ticker fit independence).

## What breadth did — and didn't — do

| Book (top-K of universe, weekly, real ORATS fills) | trades | P&L cross | Sharpe cross | Sharpe mid |
| --- | --- | --- | --- | --- |
| 9-name top-2 (baseline, §3) | 903 | $1.41M | 0.68 | 0.85 |
| 29-name top-2, naive rank | 623 | $0.73M | 0.43 | 0.64 |
| 29-name top-2, **tradeable-rank** | 1,549 | $1.88M | 0.63 | 0.89 |
| 29-name top-2, tradeable + score>0 (**final**) | 1,524 | $1.92M | **0.66** | **0.93** |
| 29-name top-4 / top-6 (tradeable) | 3,010 / 4,248 | $1.7M / $1.6M | 0.29 / 0.20 | 0.56 / 0.47 |

Final book era Sharpes (mid): **1.12 / 0.64 / 0.92 / 1.02** — at or near 1 in three of four eras;
15 of 17 years positive (2015 −$150k, 2022 −$217k). Charts: `xsec_putspread_pnl_wide.png`.
Reproduce: `XS_DATA_ROOT=strategy_backtest/data_wide XS_TOPK=2 XS_TRADEABLE=1 XS_MIN_SCORE=0.0
.venv/bin/python -m strategy_backtest.experiments.xsec_putspread_topk`.

Three structural lessons:

1. **Naive breadth backfired** (0.68 → 0.43): the wider ranking constantly selected names whose
   0.25Δ/0.10Δ spread can't pass G7 (XLP: 113 top-2 selections, 7 fills) — untradeable names hog
   basket slots and the few fills are adverse residue. The paper signal was *right* on those names
   (IYR paper outcome +0.25 when selected; its 28 actual trades lost $99k) — the failure was
   translation, not forecast. Fix: **rank within the tradeable set** (walk the ranked list, take
   the first K that actually open — PIT, exactly what a live trader does). This alone recovered
   0.43 → 0.63 and doubled capacity.
2. **The fundamental-law √N scaling did not materialize** (0.68 → 0.66 cross at 3× names). Two
   reasons measured directly: short-put outcomes share one dominant crash factor, so extra names
   add exposure faster than independent bets (K=4/6 books: Sharpe *halves* while maxDD triples);
   and the edge concentrates in ranks 1–2 — deeper picks dilute. Group-distinct selection (≤1 per
   correlation group) also hurt (0.63 → 0.54): the doubled-up top picks were genuinely the best.
3. **What breadth actually bought:** ~35% more P&L at equal-or-better Sharpe (capacity), a
   higher mid-fill bound (0.85 → 0.93), ~25% smaller maxDD-to-P&L, and much less single-name
   dependence (QQQ's share of P&L fell from 28% to 14%).

## Tested and rejected: periodic worst-ticker exclusion

A natural-looking refinement — every 6 months, ban names whose trailing-2y realized trade P&L is
negative (≥5 trades; shadow book keeps scoring banned names so they can re-enter) — was run and
**does not help**: cross 0.66 → 0.66, mid 0.93 → 0.90, with a redistribution (2022–26 up to 1.29,
2018–21 down to 0.71). Root cause measured directly: per-name performance is **not persistent** —
the rank-correlation of per-name mean ROC across consecutive 2-year windows averages +0.15 and
flips sign (−0.36 in 2016→2018). With ~10 trades/name/window the ban list chases noise: it banned
QQQ in 2013 and SPY in 2020, both of which kept earning. If a per-name screen is wanted in the
frozen spec, screen on **model skill** (trailing forecast-error quality, ~250 obs/name/yr) rather
than trade P&L (~10 obs) — that estimator is an order of magnitude less noisy and is computable
ex-ante.

## vs S&P 500 (chart: `xsec_putspread_vs_spy.png`)

Same window (2010-01 → 2026-05), monthly basis, SPY total return (price + ~1.8% dividends):

| | ann return | Sharpe (monthly) | capital basis |
| --- | --- | --- | --- |
| SPY buy & hold | 15.2% | **1.06** (0.91 price-only; ~0.8 excess of T-bills) | $2M → $5.0M cum P&L (non-compounding) |
| strategy (mid fills) | $166k/yr | **0.93** | mean concurrent margin **$330k** → 50%/yr on capital-at-risk |
| SPY on equal $330k capital | 15.2% | 1.06 | $0.82M cum P&L |
| **$2M SPY + strategy overlay** | — | **1.18** | the deployment that makes sense |

Read: (a) the strategy does NOT beat holding $2M of SPY in dollars — but it only consumes ~$330k
of margin, so that's the wrong comparison; (b) per dollar of capital-at-risk it returns ~3× SPY;
(c) monthly correlation to SPY is **+0.42** (short puts are long equity beta — this is why the
crash-factor hedge is the named next lever), yet the overlay still lifts a $2M SPY portfolio's
Sharpe 1.06 → 1.18. Context: 2010–2026 SPY Sharpe ~1.0 is historically exceptional (long-run ~0.4–
0.5); the strategy's 0.93 vs that benchmark is a strong showing for a defined-risk overlay, with
the usual caveats (realized-dated basis, in-sample multiplicity).

## Revised answer on Sharpe ≥ 1

Realistic fills (halfway between cross and mid) put the wide book at **~0.80**, with the best-case
execution bound at **0.93**. Breadth alone will not push past 1 — the binding constraint has moved
from breadth to the **common crash factor** in the outcomes. The remaining levers, in order:
(1) execution quality (the cross→mid gap is worth 0.27 Sharpe — patient limit orders at this clip
size capture most of it); (2) a crash-factor hedge financed out of the spread richness (e.g. a
small SPY put tail overlay — the one variant deliberately NOT explored here to avoid another
in-sample fork; design it ex-ante); (3) the short-straddle sleeve blend (§5.2). The multiplicity
debt is now substantial — freeze this spec and evaluate per §5.4 before any further tuning.
