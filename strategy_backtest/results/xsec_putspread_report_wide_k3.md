# Cross-sectional top-K put-credit-spread book (pivot candidate)

_top-3 of {universe minus HYG} by de-biased log-VRP score, weekly, 0.25d/0.10d ~30DTE hold-to-expiry, flat sizing (b=0.02, NAV $2M) · generated 2026-06-11_

> EXPLORATORY: structure/K/exclusions were chosen on this same sample (see
> `XSEC_PIVOT_FINDINGS.md` for the multiplicity discussion and the pre-registration protocol
> required before any deployment decision). The daily series is realization-dated (no MTM).

| fill | trades | pnl | Sharpe(mo) | maxDD | win | 2010–2013 | 2014–2017 | 2018–2021 | 2022–2026 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| cross | 927 | $833,567 | **0.36** | $322,761 | 84% | 0.43 | 0.29 | 0.51 | 0.16 |
| mid | 1012 | $1,420,356 | **0.57** | $322,185 | 84% | 0.49 | 0.55 | 0.74 | 0.50 |

## By ticker (cross fills)

| ticker | n | pnl |
| --- | --- | --- |
| QQQ | 226 | $415,840 |
| SLV | 49 | $212,802 |
| GDX | 58 | $142,036 |
| EEM | 91 | $132,358 |
| SPY | 49 | $129,381 |
| IWM | 23 | $124,235 |
| GLD | 39 | $89,091 |
| KRE | 27 | $82,728 |
| XLF | 12 | $53,431 |
| XRT | 14 | $52,981 |
| EFA | 15 | $34,123 |
| XLK | 10 | $33,018 |
| XLE | 5 | $30,607 |
| XBI | 4 | $27,532 |
| XLU | 6 | $20,713 |
| XLI | 6 | $18,807 |
| SMH | 10 | $4,278 |
| XOP | 8 | $2,579 |
| XLB | 3 | $-2,425 |
| IBB | 10 | $-6,819 |
| XLY | 10 | $-34,261 |
| XLV | 6 | $-39,922 |
| XLP | 13 | $-47,158 |
| DIA | 44 | $-57,915 |
| FXI | 14 | $-76,773 |
| IYR | 38 | $-91,114 |
| TLT | 26 | $-103,143 |
| EWZ | 53 | $-145,347 |
| USO | 58 | $-168,098 |
