# Cross-sectional top-K put-credit-spread book (pivot candidate)

_top-6 of {universe minus HYG} by de-biased log-VRP score, weekly, 0.25d/0.10d ~30DTE hold-to-expiry, flat sizing (b=0.02, NAV $2M) · generated 2026-06-11_

> EXPLORATORY: structure/K/exclusions were chosen on this same sample (see
> `XSEC_PIVOT_FINDINGS.md` for the multiplicity discussion and the pre-registration protocol
> required before any deployment decision). The daily series is realization-dated (no MTM).

| fill | trades | pnl | Sharpe(mo) | maxDD | win | 2010–2013 | 2014–2017 | 2018–2021 | 2022–2026 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| cross | 1838 | $1,808,328 | **0.44** | $591,183 | 84% | 0.71 | 0.24 | 0.60 | 0.13 |
| mid | 2025 | $3,013,225 | **0.69** | $539,026 | 85% | 0.91 | 0.65 | 0.76 | 0.38 |

## By ticker (cross fills)

| ticker | n | pnl |
| --- | --- | --- |
| QQQ | 323 | $776,168 |
| SLV | 99 | $305,033 |
| GLD | 82 | $272,934 |
| IWM | 71 | $255,283 |
| SPY | 138 | $253,316 |
| GDX | 115 | $175,369 |
| DIA | 105 | $121,683 |
| EEM | 149 | $116,134 |
| KRE | 45 | $82,114 |
| TLT | 72 | $75,653 |
| XLU | 18 | $73,061 |
| EFA | 25 | $61,143 |
| XLF | 22 | $58,023 |
| IBB | 22 | $34,139 |
| XRT | 40 | $23,830 |
| IYR | 58 | $15,863 |
| FXI | 38 | $-5,336 |
| XLI | 29 | $-7,232 |
| XLV | 25 | $-19,654 |
| XLP | 26 | $-26,715 |
| SMH | 19 | $-33,536 |
| XLE | 13 | $-33,573 |
| XLB | 4 | $-41,878 |
| XLK | 30 | $-51,235 |
| XLY | 23 | $-56,637 |
| XBI | 12 | $-75,064 |
| XOP | 25 | $-79,973 |
| EWZ | 96 | $-173,807 |
| USO | 114 | $-286,774 |
