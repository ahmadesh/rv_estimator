# Split cadence + THURSDAY-ONLY exclusion — Mon free, Thu skips that week's Monday name

_Monday picks the richest tradeable name with no constraint; Thursday picks the richest tradeable name EXCEPT the one Monday opened this week. Frozen book otherwise. NAV $2M, b=0.02 · generated 2026-07-08_

_Diagnostics: 1702 entry dates; the Thursday exclusion changed the pick on 344 of them; 84 dates opened nothing._

| fill | trades | pnl | Sharpe(mo) | maxDD | win | 2010–2013 | 2014–2017 | 2018–2021 | 2022–2026 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| cross | 1617 | $2,101,274 | **0.67** | $483,749 | 85% | 0.79 | 0.45 | 0.82 | 0.59 |
| mid | 1618 | $2,981,541 | **0.93** | $455,929 | 85% | 1.01 | 0.86 | 1.04 | 0.82 |

### Reference (prior experiments, same NAV/b)

| arm | Sharpe cross | Sharpe mid | maxDD cross |
| --- | --- | --- | --- |
| Mon top-2 (both on Monday) | 0.78 | 1.04 | $433k |
| split, no exclusion | 0.75 | 1.01 | $571k |
| split + symmetric exclusion | 0.67 | 0.94 | $449k |
| roll5 top-2 (frozen baseline) | 0.66 | 0.93 | $443k |

