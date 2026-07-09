# Fixed-universe baseline put-credit-spread book (SPY/QQQ, no selection)

_always trade {SPY,QQQ} every weekly date unconditionally, 0.25d/0.10d ~30DTE hold-to-expiry, flat sizing (b=0.02, NAV $2M) · generated 2026-07-09_

> BASELINE: everything (cadence, structure, sizing, fills, G7 filters) matches the frozen
> spec; ONLY the name-selection is replaced by a fixed pair. Compare against the frozen
> tradeable-walk top-2 (cross 0.66 / mid 0.93) to read the value of cross-sectional selection.

| fill | trades | pnl | Sharpe(mo) | maxDD | win | 2010–2013 | 2014–2017 | 2018–2021 | 2022–2026 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| cross | 1045 | $1,767,465 | **0.67** | $315,247 | 87% | 0.21 | 0.88 | 1.12 | 0.67 |
| mid | 1117 | $2,096,947 | **0.77** | $308,064 | 88% | 0.34 | 1.17 | 0.95 | 0.74 |

## By ticker (cross fills)

| ticker | n | pnl |
| --- | --- | --- |
| QQQ | 565 | $1,023,970 |
| SPY | 480 | $743,495 |
