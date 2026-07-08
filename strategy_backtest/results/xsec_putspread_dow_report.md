# Day-of-week cadence experiment — frozen cross-sectional put-spread book

_Frozen spec varied on cadence ONLY (universe/score/gate/tradeable-walk/structure/sizing/fills identical). TOPK=2, TRADEABLE=1, MIN_SCORE=0.0, NAV $2M, b=0.02 · generated 2026-07-08_

`roll5` = the frozen every-5th-trading-day baseline (weekday floats). `Mon..Fri` = fixed ISO weekday with holiday fallback to the nearest later/earlier trading day that week.

## Cross fills (worst case)

| cadence | cohorts | trades | pnl | Sharpe(mo) | maxDD | win | 2010–2013 | 2014–2017 | 2018–2021 | 2022–2026 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Mon | 805 | 1582 | $2,397,284 | **0.78** | $432,638 | 86% | 1.28 | 0.36 | 0.58 | 1.02 |
| Tue | 809 | 1597 | $1,738,728 | **0.55** | $549,174 | 84% | 0.67 | 0.18 | 0.65 | 0.69 |
| Wed | 814 | 1615 | $1,540,351 | **0.48** | $530,803 | 85% | 1.12 | 0.18 | 0.28 | 0.47 |
| Thu | 816 | 1614 | $2,213,186 | **0.71** | $414,246 | 85% | 0.94 | 0.66 | 0.66 | 0.60 |
| Fri | 815 | 1617 | $1,477,475 | **0.52** | $522,924 | 84% | 0.79 | 0.17 | 0.58 | 0.52 |
| roll5 | 776 | 1525 | $1,910,752 | **0.66** | $442,801 | 85% | 0.90 | 0.30 | 0.67 | 0.78 |

## Mid fills (best case)

| cadence | cohorts | trades | pnl | Sharpe(mo) | maxDD | win | 2010–2013 | 2014–2017 | 2018–2021 | 2022–2026 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Mon | 805 | 1582 | $3,214,718 | **1.04** | $430,698 | 86% | 1.52 | 0.71 | 0.78 | 1.29 |
| Tue | 809 | 1597 | $2,529,602 | **0.78** | $466,862 | 84% | 0.86 | 0.50 | 0.86 | 0.91 |
| Wed | 814 | 1615 | $2,385,672 | **0.74** | $477,688 | 85% | 1.35 | 0.53 | 0.50 | 0.71 |
| Thu | 816 | 1615 | $3,108,081 | **0.98** | $388,720 | 85% | 1.15 | 1.05 | 0.91 | 0.84 |
| Fri | 815 | 1617 | $2,380,015 | **0.82** | $476,656 | 84% | 1.05 | 0.58 | 0.84 | 0.80 |
| roll5 | 776 | 1525 | $2,704,937 | **0.93** | $357,078 | 85% | 1.12 | 0.63 | 0.92 | 1.02 |
