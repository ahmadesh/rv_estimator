# Cross-sectional top-K put-credit-spread book (pivot candidate)

_top-2 of {universe minus HYG} by de-biased log-VRP score, weekly, 0.25d/0.10d ~30DTE hold-to-expiry, flat sizing (b=0.02, NAV $2M) · generated 2026-06-11_

> EXPLORATORY: structure/K/exclusions were chosen on this same sample (see
> `XSEC_PIVOT_FINDINGS.md` for the multiplicity discussion and the pre-registration protocol
> required before any deployment decision). The daily series is realization-dated (no MTM).

| fill | trades | pnl | Sharpe(mo) | maxDD | win | 2010–2013 | 2014–2017 | 2018–2021 | 2022–2026 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| cross | 1524 | $1,915,757 | **0.66** | $437,795 | 85% | 0.90 | 0.30 | 0.67 | 0.78 |
| mid | 1524 | $2,709,077 | **0.93** | $352,939 | 85% | 1.12 | 0.63 | 0.92 | 1.02 |

## By ticker (cross fills)

| ticker | n | pnl |
| --- | --- | --- |
| QQQ | 319 | $670,837 |
| IWM | 105 | $362,298 |
| SPY | 132 | $246,132 |
| GDX | 89 | $136,028 |
| GLD | 84 | $135,837 |
| SLV | 92 | $114,513 |
| KRE | 33 | $110,952 |
| XLF | 25 | $104,358 |
| EEM | 115 | $77,333 |
| DIA | 80 | $74,680 |
| SMH | 20 | $59,396 |
| XLE | 16 | $54,260 |
| XRT | 18 | $50,836 |
| TLT | 67 | $24,529 |
| EFA | 13 | $24,508 |
| XLV | 10 | $17,027 |
| XLU | 8 | $12,005 |
| XLB | 2 | $9,153 |
| IBB | 16 | $4,903 |
| USO | 86 | $-6,199 |
| FXI | 23 | $-6,491 |
| XBI | 9 | $-9,385 |
| XOP | 16 | $-9,391 |
| XLY | 12 | $-11,514 |
| XLI | 8 | $-25,882 |
| IYR | 39 | $-45,164 |
| XLK | 11 | $-47,068 |
| XLP | 11 | $-96,852 |
| EWZ | 65 | $-115,882 |
