# Put-Credit-Spread Backtest — Independent Review & Verdict

_Review of `strategy_backtest/` (engine, pipeline, results) · 2026-06-11 · reviewed against the stated goal: **deploy real capital at ~$2M NAV, hurdle = standalone Sharpe ≥ ~1**_

---

## TL;DR

**The backtest is implemented correctly. The results, read honestly, say: do not deploy this strategy.**

- Mechanics verified: fills, deltas, settlement and P&L reconcile **bit-exact** against raw ORATS chains; totals, margin caps and PIT/leakage discipline all check out.
- But the headline Sharpe 0.46 is (a) computed on a flattering basis, (b) partly the product of in-sample knob selection, and (c) **entirely pre-2018**: the book made +$397k at Sharpe 0.82 before 2018 and **lost $88k at Sharpe −0.34 over the 8.4 years since**. Against a Sharpe ≥ 1 hurdle this fails by a wide margin, in level *and* in trend.
- The salvageable asset is not the strategy — it is the **forecaster's cross-sectional ranking signal**, which my checks show is genuinely predictive in every era (including post-2018) but is wasted as a mere size tilt in the current design. The honest options are: stop, or pivot the RV stack to a market-neutral cross-sectional expression where that ranking is the whole trade.

---

## 1. Correctness audit — what I verified

| Check | Result |
| --- | --- |
| Per-trade economics (3 random trades vs raw ORATS parquet) | ✅ credit, put deltas (−0.25/−0.10), settlement spot, gross P&L all match exactly |
| Ledger ↔ daily P&L ↔ report totals ($308,925; 1,630 trades; 82.76% win; 19.88% breach) | ✅ reconcile |
| `pnl == gross − cost` per trade | ✅ max error 0.0 |
| Concurrent per-group margin cap (20% NAV) | ✅ peak group margin 9.7% (GLD); peak whole-book margin 19.9% NAV |
| PIT discipline (expanding IVrank/dispersion percentiles, 22-day-embargoed VRP de-bias, walk-forward forecast cache) | ✅ leakage-safe by construction; `trailing_debias` shift logic correct |
| Forecaster cache vs production guide | ✅ already independently verified bit-exact (36/36, `ensemble_verification.md`) |
| Stress/SMA flags, gate logic (G2/G3/G4/G7), strike selection, fill conventions | ✅ match the v2 design (with the two disclosed G7 relaxations) |

Minor issues found (none change the conclusion):

1. **`marks._liquid` OI null-pass** — `if q["oi"] is not None and q["oi"] < min_oi`: a leg with *missing* OI passes the OI filter. Mild fill-optimism on sparse early-sample chains.
2. **Round-half-up after the group cap** can nudge a group slightly past the 20% budget (in practice it never did — peak 19.9%).
3. **Same-day EOD signal → same-day EOD fill**: the entry is filled at the same close that produced the signal. Standard EOD-sim optimism, undisclosed in §9 biases.
4. Saturday expiries (pre-2015 conventions; 67 realization days) settle on the Friday walk-back spot — fine, but worth knowing it's there.

## 2. Why the headline flatters — three methodological problems

**(a) Realized-only risk basis.** P&L is booked only on exit dates. The Sharpe (0.46), maxDD (7.74%) and CVaR are computed on a 533-observation realization-day series — intra-trade mark-to-market swings are invisible. The managed-arm ablation itself proves these swings are large: **183 of 1,629 trades (11%) touched a mark loss ≥ 2× credit** at some point (the X5 trigger), most of which then "recovered" by expiry in the hold arm. A real margin account lives on the MTM path; the true drawdown and vol are materially worse than reported. Re-basing the same P&L: monthly aggregation → **Sharpe 0.40**; with-zeros daily → 0.38.

**(b) In-sample knob selection.** `config.py` says "set ONCE and never tuned on the P&L being scored," but the file's own comments document the opposite: `RISK_BUDGET b=0.02` was set from a b-sweep targeting the backtest's maxDD; weekly cadence, VRP de-bias, and nearest-rounding were adopted because they improved this same backtest; the 200d-SMA stress filter was picked as the best of 5 candidates *on this P&L* (ablation table: it lifts 2014+ Sharpe 0.20→0.26 — that is selection, not validation); credit/width was relaxed 0.20→0.10 after seeing rejection rates. Individually defensible, collectively the reported Sharpe is roughly a **max over ~5 axes of variants**, so the unconditional expectation is lower than 0.46 even before regime concerns.

**(c) The design's own promotion bar was never met.** §8.1 of the design doc makes promotion conditional on the A-vs-B ablation (regime-only vs regime+forecaster, judged on a bootstrap tail CI). It was never run (report §10.F admits this). Meanwhile the per-obs Sharpe 95% CI is **(−0.01, 0.21) — it straddles zero**. By the strategy's own pre-registered standard, it is unpromoted.

## 3. The result that decides it: the edge died in 2018

| Era | Trades | P&L | Sharpe (monthly basis) |
| --- | --- | --- | --- |
| 2008–2017 | — | **+$397,334** | **+0.82** |
| 2018–2026 (8.4 yrs) | — | **−$88,409** | **−0.34** |

Annual P&L is negative in 2018, 2019, 2022, 2023, 2024. The equity curve peaks in Jan-2018 and never recovers. This is not noise around a positive mean — it is one good decade followed by one bad one, and the bad one is the recent one. Plausible structural reading: the 30-DTE ~0.25Δ ETF put-spread VRP got crowded/arbitraged post-2018 (systematic put-selling ETFs, retail option flow, 0DTE migration), exactly the segment of the surface this strategy harvests.

Additional fragility:

- **Concentration:** GLD is $149k of the $309k total (48%). TLT is a persistent loser (−$60k, worst breach rate 29.8%). Remove GLD and the full-sample story is roughly break-even.
- **Per-trade edge is thin where the forecaster runs:** mean return-on-risk is **+0.40%** per trade in the forecaster segment (vs +10.2% in the no-forecaster GFC segment — the easy money was the 2009–2010 vol normalization, which needed no model).
- **Opportunity cost at the stated goal:** ~0.85%/yr on NAV (and ~0 since 2018) vs ~4–5%/yr on T-bills 2022–2026. As a standalone deployment of $2M this is strictly dominated; even as an overlay it adds ~nothing net of operational and tail risk in the recent regime.
- The managed-exit challenger **loses outright** (−$129k), so there is no exit-engineering rescue on the table; hold-to-expiry is already the best arm tested.

## 4. The genuinely interesting finding: the ranking signal is real, the strategy wastes it

The forecaster has **no timing alpha** (sign accuracy vs IV² = 0.504 — a coin flip, per the verification report) and a large level bias (+0.27 log, needing a PIT de-bias just to size). But its **cross-sectional ranking** of trades is real. Within-year quintiles of de-biased `vrp_rel` vs per-trade return-on-risk (forecaster segment, n=1,508):

| Quintile | Mean ROC | Post-2018 mean ROC |
| --- | --- | --- |
| Q1 (cheapest VRP) | **−3.0%** | −5.9% |
| Q2 | −3.5% | −11.6% |
| Q3 | +0.8% | −5.0% |
| Q4 | +2.1% | −0.2% |
| Q5 (richest VRP) | **+5.5%** | **+2.3%** |

The control kills the obvious alternative: the same quintile table built on **model-free trailing-RV VRP is flat** (Spearman ≈ 0.01 vs the forecaster's clean monotone gradient). The ranking power comes from the model, not from "IV high vs recent RV."

The current design trades **every** gated candidate and uses VRP only as a size tilt floored at 0.05 — so Q1–Q3 (which bleed, especially post-2018) still trade. An in-sample illustration of what selection would do: `vrp_rel ≥ 0.25` keeps 580 of 1,508 trades and is **positive in every era**: 2010–13 +$178k, 2014–17 +$94k, 2018–21 +$26k, 2022–26 +$34k (87% win rate). *Caveat: this threshold was chosen looking at the ledger — it is an upper bound, not a forecast.* But the within-year quintile monotonicity is not threshold-snooping, and it is the one robust, era-stable piece of alpha in the whole project.

## 5. Verdict (against your stated hurdle)

**Do not deploy. Stop the strategy in its current form.**

1. Best-case honest Sharpe is ~0.4 full-sample, **negative for 8.4 years running** — the hurdle is ≥ 1 standalone.
2. The risk numbers that look acceptable (7.7% maxDD, CVaR) are computed on a realized-only basis that demonstrably hides MTM pain (11% of trades touched 2× credit).
3. The design's own promotion test was never passed, and the Sharpe CI includes zero.
4. The economics don't clear T-bills in the recent regime, at any b, because b is a pure scalar — there is no sizing knob that fixes a dead edge.

**But "stop RV forecasting for VRP" is the wrong generalization.** The evidence is more specific: *the long-only short-vol expression is dead; the cross-sectional ranking the RV model produces is alive.* Killing the whole stack would discard the one validated asset.

## 6. If you continue — redirect, don't iterate

Ranked by how directly they exploit the validated signal while shedding the dead short-vol beta:

1. **Market-neutral cross-sectional vol RV (the natural pivot).** Each roll date, rank the 10 names by de-biased VRP; sell premium (put spreads or strangles) on the top 2–3, **buy** the same structure on the bottom 2–3. This monetizes the Q5−Q1 spread (~8–9% ROC gross, era-stable) while being roughly flat the aggregate VRP/short-vol factor that died post-2018. It also recycles everything already built (panel, chains, engine, sizing). Main risks to test: the long legs' carry bleed, and whether 10 names give enough cross-sectional breadth (consider widening the universe — the ORATS mirror has more tickers).
2. **VRP as a selection gate, properly tested.** Pre-register a threshold rule (e.g., "trade only Q4–Q5 within trailing cross-section," no fixed numeric threshold to avoid level-drift), then run it once. Combine with the never-run **§8.1 A-vs-B promotion test** — one experiment, two questions answered: does the forecaster earn its place, and does selection beat tilt.
3. **Re-express the short side where VRP still exists.** If you keep any outright short-vol, test where post-2018 P&L actually concentrated (GLD, IWM) and whether richer segments of the surface (further-OTM tails, longer DTE, single-name overlap) still carry VRP — rather than 30-DTE 0.25Δ index-beta puts, the most crowded trade in retail finance.
4. **Mandatory hygiene for whatever runs next:** (a) build the MTM equity curve (the chains support daily re-marking — the managed arm already does it) and quote Sharpe/maxDD off that; (b) freeze all knobs before the run and treat 2022+ as a hold-out; (c) set a kill rule in advance (e.g., "trailing 3-yr Sharpe < 0 → stop"), which the current strategy would have triggered around 2021.

### Decision summary

| Question | Answer |
| --- | --- |
| Is the backtest implementation trustworthy? | Yes — verified to the raw data |
| Do the results support deployment at Sharpe ≥ 1? | No — not close, and the trend is negative |
| Is the RV-forecasting stack worthless for VRP? | No — its cross-sectional ranking is the one era-stable edge found |
| Recommended action | Stop this book; if continuing, pivot to the market-neutral cross-sectional expression (option 1) and run the A-vs-B test before writing any new strategy code |

> **Follow-up (2026-06-12):** the pivot was prototyped — see `XSEC_PIVOT_FINDINGS.md`. Rank-selected
> put-credit spreads reach Sharpe 0.68–0.85 era-stable (strongest post-2018); the pure L/S straddle
> expression fails on friction. Path to ≥1 runs through universe breadth.
