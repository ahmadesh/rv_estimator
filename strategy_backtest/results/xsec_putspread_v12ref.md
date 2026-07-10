# v1.2 combined confirmation run — Monday cadence + OI-cap 0.25

_Pre-registered in `conclusion/LIVE_DEPLOYMENT_SPEC.md` §4.1 · frozen machinery, cadence and sizing-cap changed together, nothing else · TOPK=2, TRADEABLE=1, MIN_SCORE=0.0, NAV $2M, b=0.02, OI_FRAC=0.25 · generated 2026-07-10_

| fill | cohorts | trades | pnl | Sharpe(mo) | maxDD | win | mean margin/trade | 2010–2013 | 2014–2017 | 2018–2021 | 2022–2026 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| cross | 805 | 1580 | $2,019,955 | **1.05** | $267,999 | 86% | $24,488 | 1.19 | 0.74 | 1.37 | 0.89 |
| mid | 805 | 1581 | $2,368,970 | **1.22** | $261,922 | 86% | $24,415 | 1.38 | 1.01 | 1.48 | 1.04 |

Reference points: v1.0 frozen 0.66 cross / 0.93 mid; OI-cap-only 0.89 / 1.06; Monday-only 0.78 / 1.04. Abort threshold (pre-registered): cross < 0.66.

Ledgers: `xsec_putspread_v12ref_trades_{cross,mid}.csv`.
