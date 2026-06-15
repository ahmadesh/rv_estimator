# Cross-sectional top-K put-credit-spread book (pivot candidate)

_top-4 of {universe minus HYG} by de-biased log-VRP score, weekly, 0.25d/0.10d ~30DTE hold-to-expiry, flat sizing (b=0.02, NAV $2M) · generated 2026-06-11_

> EXPLORATORY: structure/K/exclusions were chosen on this same sample (see
> `XSEC_PIVOT_FINDINGS.md` for the multiplicity discussion and the pre-registration protocol
> required before any deployment decision). The daily series is realization-dated (no MTM).

| fill | trades | pnl | Sharpe(mo) | maxDD | win | 2010–2013 | 2014–2017 | 2018–2021 | 2022–2026 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| cross | 1240 | $1,104,287 | **0.36** | $497,398 | 84% | 0.49 | 0.32 | 0.61 | -0.03 |
| mid | 1358 | $1,932,343 | **0.60** | $398,868 | 84% | 0.60 | 0.66 | 0.87 | 0.25 |

## By ticker (cross fills)

| ticker | n | pnl |
| --- | --- | --- |
| QQQ | 264 | $548,105 |
| SLV | 72 | $316,887 |
| GLD | 54 | $180,166 |
| GDX | 80 | $178,466 |
| SPY | 82 | $177,274 |
| EEM | 111 | $144,751 |
| IWM | 40 | $108,581 |
| XRT | 24 | $78,204 |
| KRE | 33 | $70,091 |
| XLE | 7 | $42,568 |
| EFA | 17 | $39,293 |
| XLU | 8 | $31,572 |
| XLF | 15 | $23,145 |
| SMH | 12 | $16,487 |
| XLI | 13 | $9,771 |
| DIA | 66 | $7,468 |
| XLB | 3 | $-2,425 |
| XBI | 6 | $-2,964 |
| IBB | 12 | $-16,201 |
| XLY | 12 | $-23,409 |
| XOP | 12 | $-42,373 |
| FXI | 19 | $-47,900 |
| XLK | 18 | $-56,590 |
| IYR | 45 | $-57,425 |
| XLV | 16 | $-68,260 |
| XLP | 17 | $-72,476 |
| TLT | 39 | $-90,227 |
| USO | 75 | $-183,129 |
| EWZ | 68 | $-205,166 |
