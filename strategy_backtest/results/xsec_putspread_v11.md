# v1.1 candidate — pair-core + non-pair overlay (I2, ex-ante design)

_core: SPY+QQQ every weekly date unconditionally; overlay: frozen top-2 walk on universe minus pair; ONE engine pass (shared concurrent margin cap) · generated 2026-07-09_

> Carries fresh multiplicity debt (§8.6): a candidate for the §7 protocol, not a v1.0 result.

Reference: frozen v1.0 cross **0.66** / mid **0.93**; fixed pair cross 0.67 / mid 0.77.

| fill | trades | pnl | Sharpe(mo) | maxDD | win | core P&L | overlay P&L | sleeve corr | 2010–2013 | 2014–2017 | 2018–2021 | 2022–2026 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| cross | 2526 | $2,182,134 | **0.44** | $786,409 | 84% | $1,651,230 | $530,905 | 0.47 | 0.50 | 0.31 | 0.50 | 0.43 |
| mid | 2591 | $3,460,222 | **0.67** | $660,996 | 84% | $1,958,323 | $1,501,900 | 0.48 | 0.71 | 0.67 | 0.65 | 0.65 |

## By ticker (cross fills)

| ticker | n | pnl |
| --- | --- | --- |
| QQQ | 565 | $969,193 |
| SPY | 477 | $682,037 |
| IWM | 172 | $325,696 |
| GDX | 121 | $153,162 |
| TLT | 92 | $134,467 |
| XLF | 40 | $86,686 |
| KRE | 44 | $85,315 |
| SLV | 127 | $72,867 |
| XRT | 22 | $71,888 |
| SMH | 30 | $54,509 |
| EFA | 16 | $38,697 |
| GLD | 114 | $29,377 |
| XLV | 15 | $22,975 |
| XOP | 27 | $20,146 |
| XLB | 4 | $18,835 |
| XLU | 15 | $18,383 |
| IBB | 17 | $10,701 |
| XLI | 14 | $5,476 |
| EEM | 134 | $-6,960 |
| XBI | 12 | $-8,737 |
| XLY | 17 | $-24,109 |
| IYR | 41 | $-33,986 |
| XLK | 20 | $-37,521 |
| XLE | 33 | $-39,945 |
| DIA | 107 | $-58,193 |
| FXI | 34 | $-76,832 |
| XLP | 16 | $-78,420 |
| USO | 105 | $-101,313 |
| EWZ | 95 | $-152,261 |
