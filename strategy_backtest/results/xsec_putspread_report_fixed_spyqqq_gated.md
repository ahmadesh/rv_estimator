# Fixed-universe baseline put-credit-spread book (SPY/QQQ, no selection)

_always trade {SPY,QQQ} every weekly date when score>0, 0.25d/0.10d ~30DTE hold-to-expiry, flat sizing (b=0.02, NAV $2M) · generated 2026-07-09_

> BASELINE: everything (cadence, structure, sizing, fills, G7 filters) matches the frozen
> spec; ONLY the name-selection is replaced by a fixed pair. Compare against the frozen
> tradeable-walk top-2 (cross 0.66 / mid 0.93) to read the value of cross-sectional selection.

| fill | trades | pnl | Sharpe(mo) | maxDD | win | 2010–2013 | 2014–2017 | 2018–2021 | 2022–2026 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| cross | 958 | $1,656,595 | **0.69** | $330,185 | 87% | 0.40 | 0.76 | 1.06 | 0.61 |
| mid | 1022 | $2,005,678 | **0.81** | $323,082 | 87% | 0.57 | 1.03 | 0.98 | 0.67 |

## By ticker (cross fills)

| ticker | n | pnl |
| --- | --- | --- |
| QQQ | 528 | $1,038,011 |
| SPY | 430 | $618,584 |
