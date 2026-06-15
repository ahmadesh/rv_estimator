# Cross-sectional top-K put-credit-spread book (pivot candidate)

_top-2 of {universe minus HYG} by de-biased log-VRP score, weekly, 0.25d/0.10d ~30DTE hold-to-expiry, flat sizing (b=0.02, NAV $2M) · generated 2026-06-11_

> EXPLORATORY: structure/K/exclusions were chosen on this same sample (see
> `XSEC_PIVOT_FINDINGS.md` for the multiplicity discussion and the pre-registration protocol
> required before any deployment decision). The daily series is realization-dated (no MTM).

| fill | trades | pnl | Sharpe(mo) | maxDD | win | 2010–2013 | 2014–2017 | 2018–2021 | 2022–2026 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| cross | 623 | $731,815 | **0.43** | $287,061 | 84% | 0.50 | 0.43 | 0.60 | 0.16 |
| mid | 683 | $1,150,369 | **0.64** | $286,760 | 84% | 0.61 | 0.66 | 0.79 | 0.47 |

## By ticker (cross fills)

| ticker | n | pnl |
| --- | --- | --- |
| QQQ | 174 | $260,904 |
| SLV | 34 | $198,969 |
| EEM | 61 | $181,762 |
| GLD | 28 | $94,897 |
| GDX | 39 | $61,638 |
| SPY | 23 | $56,961 |
| KRE | 21 | $47,557 |
| XLF | 9 | $39,831 |
| SMH | 6 | $35,501 |
| XRT | 11 | $34,313 |
| IWM | 6 | $32,845 |
| XBI | 4 | $27,532 |
| EFA | 13 | $24,508 |
| XLU | 3 | $18,296 |
| IBB | 3 | $17,693 |
| XLE | 2 | $13,511 |
| XOP | 2 | $12,642 |
| XLI | 2 | $9,834 |
| XLV | 2 | $9,660 |
| XLB | 2 | $9,153 |
| XLK | 4 | $3,076 |
| XLY | 7 | $-13,636 |
| EWZ | 42 | $-26,816 |
| FXI | 4 | $-29,311 |
| TLT | 13 | $-58,996 |
| XLP | 7 | $-73,298 |
| DIA | 31 | $-77,186 |
| USO | 42 | $-80,543 |
| IYR | 28 | $-99,483 |
