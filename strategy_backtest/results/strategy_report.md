# Put-Credit-Spread Strategy — Backtest Report

_v2 lean-core book · 2007-01-01 → 2026-05-22 · NAV $2.0M, whole contracts (b=0.02, nearest-round) · primary exit: hold · generated 2026-06-08_

> Headline economic run of `PUT_SPREAD_STRATEGY_DESIGN_v2.md`: a defined-risk short-variance put-credit spread (0.25Δ short / 0.10Δ wing, ~30 DTE) on the 10 core ETFs, gated by the 4-signal lean core (G2 IVrank≤85 · G3 contango · G4 dispersion · G7 liquidity) + a **200d-SMA trend stand-down** (§4.3 ablation winner: of the 5 stress flags only the downtrend filter cut the post-2014 tail), sized by inverse-risk fractional Kelly with VRP as a tilt, held to expiry. 2007–2010 is the degraded GFC stress segment (no forecaster; IV-only inverse-risk sizing; G4 dropped).

## 1. Headline metrics

- **Trades placed:** 1,630 (win rate 82.76%, short-strike breach rate 19.88%)
- **Realized P&L (total):** $308,925 = 15.45% of NAV over 18.14 yrs
- **Annualized return:** $17,029 (0.85% of NAV)
- **Sharpe (ann):** 0.46  ·  **Sortino (ann):** 0.55
- **Max drawdown:** $154,889 (7.74% of NAV)
- **CVaR95 (per realization day):** $-18,817 (-0.94% of NAV)  ·  **worst day:** $-78,529
- **Cost drag:** $45,945 (12.95% of gross); break-even cost ×7.72

## 2. Capital deployment / sizing reality (the granularity tax, design §7.3)

> **Capital-use overhaul applied** (report §10.A/B/D follow-up). Three edge-preserving levers — none change which trades fire: (1) **WEEKLY roll cadence** (`ROLL_CADENCE=5`) ~4× the trade count for more concurrent deployment + diversification; (2) **VRP de-bias** (`DEBIAS_VRP` — PIT per-ticker calibration of rv_hat, which over-predicts RV on 2010+) so size lands on genuinely-rich trades instead of flooring at vrp_rel=0.05; (3) **`RISK_BUDGET` b=0.02** + **nearest-rounding**, b set to the deployment ceiling that holds maxDD ≤ ~10% NAV. The overlapping weekly positions are bounded by the engine's **concurrent** per-group margin accounting (not just same-day), so the 20%/group cap still holds. Net vs the original monthly book: ~4× capital deployed and ~4× return at a HIGHER Sharpe — capital use rose without diluting the edge.

- **Mean margin at risk / trade:** 0.34% of NAV (max 2.55%)
- **Contracts / trade:** mean 21.68, median 14.00; 3.74% of trades are a single contract
- **Avg return on capital-at-risk / trade:** 1.14% (mean of pnl_i / max-loss_i) — the per-trade edge net of the NAV-deployment choice
- **Implication:** with the capital-use overhaul the book now deploys ~3.4% of NAV on average at an 82.76% win rate; the headline %-NAV return scales with `RISK_BUDGET` b, which is pinned to the ≤10%-NAV-maxDD ceiling. Going higher is a pure risk-appetite choice (b is Sharpe-invariant until the per-group cap binds), not an edge question.

## 3. Statistical power (block-bootstrap 95% CIs, design §8.2)

- Realization-day observations: **533**, effective-N (lag-1 adj): **509.8**, bootstrap block length: **4** obs

| Metric | Point | 95% CI low | 95% CI high |
| --- | --- | --- | --- |
| CVaR95 ($) | $-18,817 | $-26,455 | $-12,702 |
| Max drawdown ($) | $154,889 | $54,504 | $233,807 |
| Sharpe (per obs) | 0.08 | -0.01 | 0.21 |

## 4. By segment (GFC degraded vs forecaster headline, design §2.2)

| segment | n_trades | pnl_total | win_rate | breach_rate |
| --- | --- | --- | --- | --- |
| degraded | 122 | 22,035.50 | 0.9098 | 0.0902 |
| forecaster | 1508 | 286,889.52 | 0.8210 | 0.2076 |


## 5. P&L by ticker

| ticker | n_trades | pnl_total | win_rate | breach_rate | avg_contracts |
| --- | --- | --- | --- | --- | --- |
| GLD | 152 | 149,001.80 | 0.8421 | 0.2105 | 28.04 |
| IWM | 293 | 89,296.18 | 0.8362 | 0.1911 | 18.69 |
| QQQ | 330 | 62,697.75 | 0.8455 | 0.1697 | 9.32 |
| SPY | 230 | 50,975.70 | 0.8652 | 0.1478 | 11.66 |
| XLK | 45 | 16,093.26 | 0.8667 | 0.1556 | 45.89 |
| XLF | 79 | 11,893.80 | 0.8101 | 0.2152 | 46.29 |
| HYG | 30 | 9,025.20 | 0.8333 | 0.1667 | 38.87 |
| XLE | 165 | -6,284.55 | 0.8000 | 0.2424 | 22.98 |
| EEM | 185 | -13,909.22 | 0.8000 | 0.2216 | 21.57 |
| TLT | 121 | -59,864.90 | 0.7438 | 0.2975 | 42.79 |


## 6. P&L by correlation group

| group | n_trades | pnl_total | win_rate | breach_rate | avg_contracts |
| --- | --- | --- | --- | --- | --- |
| precious_metals | 152 | 149,001.80 | 0.8421 | 0.2105 | 28.04 |
| us_large_cap_equity | 560 | 113,673.45 | 0.8536 | 0.1607 | 10.28 |
| us_small_cap_equity | 293 | 89,296.18 | 0.8362 | 0.1911 | 18.69 |
| us_technology_sector | 45 | 16,093.26 | 0.8667 | 0.1556 | 45.89 |
| us_cyclicals_sector | 79 | 11,893.80 | 0.8101 | 0.2152 | 46.29 |
| high_yield_credit | 30 | 9,025.20 | 0.8333 | 0.1667 | 38.87 |
| oil_and_energy | 165 | -6,284.55 | 0.8000 | 0.2424 | 22.98 |
| emerging_markets | 185 | -13,909.22 | 0.8000 | 0.2216 | 21.57 |
| us_rates_and_ig_credit | 121 | -59,864.90 | 0.7438 | 0.2975 | 42.79 |


## 7. Annual returns

| year | pnl | ret_pct_nav | n_days |
| --- | --- | --- | --- |
| 2008 | -3,585.80 | -0.0018 | 7 |
| 2009 | 24,462.00 | 0.0122 | 10 |
| 2010 | 87,395.80 | 0.0437 | 15 |
| 2011 | 47,473.80 | 0.0237 | 11 |
| 2012 | -1,552.87 | -0.0008 | 17 |
| 2013 | 75,909.25 | 0.0380 | 37 |
| 2014 | 81,502.86 | 0.0408 | 42 |
| 2015 | -4,610.50 | -0.0023 | 45 |
| 2016 | 10,032.20 | 0.0050 | 41 |
| 2017 | 80,307.40 | 0.0402 | 47 |
| 2018 | -47,495.62 | -0.0237 | 35 |
| 2019 | -17,694.30 | -0.0088 | 33 |
| 2020 | 5,110.50 | 0.0026 | 22 |
| 2021 | 22,125.10 | 0.0111 | 29 |
| 2022 | -29,101.30 | -0.0146 | 10 |
| 2023 | -17,932.90 | -0.0090 | 45 |
| 2024 | -42,368.80 | -0.0212 | 37 |
| 2025 | 24,907.80 | 0.0125 | 35 |
| 2026 | 14,040.40 | 0.0070 | 15 |


## 8. Stress-window decorrelation (design §8.3)

Cross-group P&L correlation should collapse in stress (the book's decorrelation thesis).

| window | n_trades | pnl_total | mean_cross_group_corr |
| --- | --- | --- | --- |
| GFC_2008 | 33 | -1,491.40 | 0.0300 |
| COVID_2020 | 8 | 3,872.40 | nan |
| RateShock_2022 | 14 | -21,762.30 | 0.00 |


## 9. Known optimistic biases (disclosed, design §8.4)

- **EOD-only marks / settlement.** Hold-to-expiry settles at ORATS expiry-day intrinsic; no intraday gap is modeled — understates short-gamma terminal-week tail.
- **No early assignment / dividend timing.** American ETF puts driven deep ITM near ex-div could be assigned early; intrinsic settlement ignores that timing.
- **Wing-fill optimism.** Crossing the spread on the 10Δ long wing in 2007–2013 for thinner names (XLE/EEM/HYG) may be optimistic where strikes are sparse.
- **Fixed-NAV sizing.** Sizing is off a constant $2M reference, not compounding; per-group margin cap is applied across same-day entries, not intramonth overlap.
- **Cached leakage-safe forecasts.** EnsembleTopK predictions are the purged/embargoed walk-forward cache (first fold ~2010); the 2007–2010 segment carries no forecaster.


## 10. Suggestions to improve results

_Ranked by expected impact; each maps to a knob in `config.py` or a documented ablation._

**A. Capital deployment — APPLIED (§2).** Weekly cadence + VRP de-bias + `RISK_BUDGET` b=0.02 (set to the ≤10%-NAV-maxDD ceiling) lift avg deployment ~0.9%→~3.4% of NAV. Mean margin-at-risk is now 0.34% (max 2.55%); avg return on capital-at-risk per trade 1.14%. b is a pure size scalar (Sharpe-invariant until the per-group cap binds) — raise it for more deployment only if you accept a higher drawdown. Next lever (deferred): concurrent-margin headroom to sub-group the equity cap.

**B. VRP de-bias — APPLIED (§2).** EnsembleTopK `rv_hat` over-predicts forward RV (+0.27 log on 2010+), biasing raw VRP negative so most trades floored at `vrp_rel=0.05`. A PIT per-ticker log-bias correction (`pit.trailing_debias`, matured obs only, leakage-safe) now feeds VRP/sizing while the gate keeps raw rv_hat — so selection is unchanged and size lands on genuinely-rich names. In the sweep this ~doubled deployment & return at equal Sharpe vs no-debias. Follow-up: a slope term (β·rv_hat), not just a level shift.

**C. Push the short strike further OTM to cut breaches.** Short-strike breach rate is 19.88% (a defined-risk loss whenever it bites). Sweep the short delta {0.20, 0.16} (doc §6 sweep) — fewer breaches and a higher win rate, traded against thinner credit. `SHORT_DELTA` in `config.py`; watch the credit/width floor.

**D. Per-name risk normalization — APPLIED.** Contracts now round to NEAREST (was floor), removing the systematic down-bias that hit expensive names hardest (n_raw≈1.4→1); combined with the b-scale, XLF averages 46.29 contracts and the priciest names clear the floor, so the σ-edge u — not strike price/rounding — sets the per-name weights. Watch TLT ($-59,865): if a name stays the lone net loser after the rescale, it's an edge problem, not a granularity one.

**E. Managed exit challenger — IMPLEMENTED (see §11).** The `mechanical_terminal` arm (X1 50% profit-take · X2 DTE≤12 hard close · X3 term-flip w/ 2-day confirm + dead-band · X4 variance stop · X5 2× hard stop) now runs alongside hold in the §11 ablation. Keep it only if it beats hold on the tail (CVaR95/maxDD) under real marks; `managed_no_x3` isolates whether the term-flip earns its churn.

**F. Run the A-vs-B promotion test for decision-grade power.** Effective-N is only 509.8 and the per-obs Sharpe CI straddles 0, so the headline isn't yet decision-grade. Run regime-only (forecaster off, flat size, no G4) vs regime+model and judge on the bootstrap CI of the tail (doc §8.1) — that attributes whether the forecaster earns its place at all.

**G. Prune redundant gates / widen entries for sample.** The lean core still trades a thin, correlated sample. Check whether G2 (IVrank) and G3 (contango) carry independent avoidance info or fire together (doc §4.3 stress-composite ablation); a single combined stress axis could free entries and raise N without hurting the tail. Also consider weekly (not just monthly) roll cadence to multiply the sample.

**H. Stress the wing fill before trusting the tail.** Break-even cost is ×7.72, comfortable on paper — but the 10Δ wing is the thinnest, most fill-optimistic leg early in the sample. Sweep `SLIPPAGE_TICKS` and specifically widen the wing's adverse fill to confirm the defined-risk floor survives realistic 2008–2013 wing liquidity.


## 11. Exit-arm ablation — hold vs managed (design §5.2)

_Hold-to-expiry is the primary/benchmark arm; `mechanical_terminal` (managed) is the challenger that must beat hold on the tail to ship. `managed_no_x3` drops the term-flip trigger to isolate its churn (design §5.2)._

| arm | n_trades | pnl_total | ann_ret_%nav | sharpe_ann | maxDD_%nav | cvar95_$ | win_rate | breach_rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| hold * | 1630 | 308,925.00 | 0.8510 | 0.4600 | 7.74 | -18,817.00 | 0.8276 | 0.1988 |
| managed | 1629 | -129,371.00 | -0.3560 | -0.4100 | 9.93 | -7,252.00 | 0.7244 | 0.1393 |
| managed_no_x3 | 1629 | -127,505.00 | -0.3510 | -0.3800 | 10.89 | -7,912.00 | 0.7483 | 0.1516 |


_`*` = the headline arm reported in sections 1–10._


**Managed arm — exit-trigger mix:**

| exit_reason | n | pnl_total |
| --- | --- | --- |
| X1_take | 1055 | 509,777.80 |
| X2_terminal | 229 | -63,779.60 |
| X5_hardstop | 183 | -499,136.60 |
| X3_termflip | 122 | -103,567.90 |
| expiry | 32 | 37,657.90 |
| X4_varstop | 8 | -10,322.40 |
