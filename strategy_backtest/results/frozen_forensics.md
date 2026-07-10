# Frozen-book ledger forensics (A2 capacity · A7 stress fills · A8 settlement)

_1524 trades re-quoted on their entry chains · generated 2026-07-09_

## A2 — contracts vs resting open interest

**short leg** contracts/OI: median 0.10 · p75 0.51 · p90 1.72 · p95 2.60 · p99 5.26

**wing leg** contracts/OI: median 0.17 · p75 1.19 · p90 4.86 · p95 9.68 · p99 23.56

| contracts/OI (worse leg) | trades | share of trades | P&L | share of P&L |
| --- | --- | --- | --- | --- |
| 0–0.1 | 560 | 37% | $1,022,494 | 53% |
| 0.1–0.25 | 190 | 12% | $519,804 | 27% |
| 0.25–0.5 | 156 | 10% | $142,607 | 7% |
| 0.5–1 | 142 | 9% | $279,632 | 15% |
| 1–inf | 476 | 31% | $-48,779 | -3% |

## A7 — entry friction by VIX quintile at entry

friction = the two half-spreads paid crossing at entry (mid credit − cross credit).

| VIX quintile | VIX range | trades | mean friction/trade | friction Σ | friction as % of mid credit | cross P&L Σ |
| --- | --- | --- | --- | --- | --- | --- |
| Q1 | 6.6–10.8 | 305 | $581 | $177,224 | 9.2% | $157,015 |
| Q2 | 10.8–12.5 | 306 | $477 | $146,102 | 7.4% | $-174,128 |
| Q3 | 12.5–14.8 | 303 | $512 | $155,088 | 7.6% | $266,697 |
| Q4 | 14.8–18.7 | 305 | $437 | $133,274 | 6.7% | $607,249 |
| Q5 | 18.7–57.6 | 305 | $492 | $150,202 | 7.2% | $1,058,924 |

## A8 — settlement realism

- settles within ±1% of the short strike (pin/assignment zone): **126** trades (8.3%), P&L $458,371
- settles below the wing (max-loss zone): **64** trades, P&L $-2,580,956
- short strike breached at expiry: **272** trades (17.8%), of which **102** on distribution-paying ETFs (early-assignment exposure the intrinsic-settle model ignores)

### USO around the Apr-2020 1:8 reverse split

| entry | expiry | short K | wing K | entry spot | settle spot | pnl |
| --- | --- | --- | --- | --- | --- | --- |
| 2020-02-13 | 2020-03-13 | 10.0 | 9.5 | 10.85 | 6.68 | $-41,178 |
| 2020-04-20 | 2020-05-22 | 3.0 | 2.0 | 3.72 | 25.54 | $9,968 |

