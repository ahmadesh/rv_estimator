# Split-cadence experiment — 1 spread Monday + 1 spread Thursday

_Frozen book, 2 spreads/week, varying only entry timing. `split` = top-1 richest tradeable name each of Mon & Thu; `Mon/Thu top-2` = both spreads on one day. NAV $2M, b=0.02 · generated 2026-07-08_

## Cross fills (worst case)

| arm | entry-days | trades | pnl | Sharpe(mo) | maxDD | win | 2010–2013 | 2014–2017 | 2018–2021 | 2022–2026 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| split (Mon#1 + Thu#1) | 1621 | 1621 | $2,409,463 | **0.75** | $570,556 | 85% | 1.06 | 0.30 | 1.34 | 0.40 |
| Mon top-2 | 805 | 1582 | $2,406,441 | **0.78** | $432,639 | 86% | 1.28 | 0.38 | 0.58 | 1.02 |
| Thu top-2 | 816 | 1615 | $2,183,097 | **0.69** | $414,246 | 85% | 0.94 | 0.66 | 0.66 | 0.56 |

_roll5 top-2 baseline (frozen): cross 0.66 / mid 0.93 — see `xsec_putspread_dow_report.md`._

## Mid fills (best case)

| arm | entry-days | trades | pnl | Sharpe(mo) | maxDD | win | 2010–2013 | 2014–2017 | 2018–2021 | 2022–2026 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| split (Mon#1 + Thu#1) | 1621 | 1621 | $3,273,472 | **1.01** | $481,194 | 85% | 1.29 | 0.68 | 1.54 | 0.61 |
| Mon top-2 | 805 | 1581 | $3,209,558 | **1.04** | $430,698 | 86% | 1.52 | 0.72 | 0.77 | 1.29 |
| Thu top-2 | 816 | 1615 | $3,064,204 | **0.96** | $388,720 | 85% | 1.15 | 1.05 | 0.91 | 0.77 |

_roll5 top-2 baseline (frozen): cross 0.66 / mid 0.93 — see `xsec_putspread_dow_report.md`._

