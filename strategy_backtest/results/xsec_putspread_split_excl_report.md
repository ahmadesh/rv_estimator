# Split cadence + prior-pick exclusion — Mon top-1 + Thu top-1, no immediate repeat

_Each entry day skips the name the previous entry day opened (Thu excludes Mon; Mon excludes last Thu). Frozen book otherwise. NAV $2M, b=0.02 · generated 2026-07-08_

_Diagnostics: 1702 entry dates; the exclusion changed the pick on 612 of them; 89 dates opened nothing._

| fill | trades | pnl | Sharpe(mo) | maxDD | win | 2010–2013 | 2014–2017 | 2018–2021 | 2022–2026 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| cross | 1613 | $2,069,966 | **0.67** | $448,846 | 85% | 0.83 | 0.52 | 0.66 | 0.63 |
| mid | 1613 | $2,970,130 | **0.94** | $429,122 | 85% | 1.05 | 0.92 | 0.91 | 0.88 |

### Reference (from prior experiments, same NAV/b)

| arm | Sharpe cross | Sharpe mid | maxDD cross |
| --- | --- | --- | --- |
| split, no exclusion (Mon#1+Thu#1) | 0.75 | 1.01 | $571k |
| Mon top-2 (both on Monday) | 0.78 | 1.04 | $433k |
| roll5 top-2 (frozen baseline) | 0.66 | 0.93 | $443k |

