# Cross-sectional top-K put-credit-spread book (pivot candidate)

_top-2 of {universe minus HYG} by de-biased log-VRP score, weekly, 0.25d/0.10d ~30DTE hold-to-expiry, flat sizing (b=0.02, NAV $2M) · generated 2026-06-11_

> EXPLORATORY: structure/K/exclusions were chosen on this same sample (see
> `XSEC_PIVOT_FINDINGS.md` for the multiplicity discussion and the pre-registration protocol
> required before any deployment decision). The daily series is realization-dated (no MTM).

| fill | trades | pnl | Sharpe(mo) | maxDD | win | 2010–2013 | 2014–2017 | 2018–2021 | 2022–2026 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| cross | 903 | $1,407,090 | **0.68** | $294,176 | 86% | 0.95 | 0.18 | 0.77 | 0.83 |
| mid | 978 | $1,823,102 | **0.85** | $267,397 | 86% | 1.27 | 0.47 | 0.87 | 0.79 |

## By ticker (cross fills)

| ticker | n | pnl |
| --- | --- | --- |
| QQQ | 344 | $622,905 |
| GLD | 82 | $259,927 |
| EEM | 148 | $193,892 |
| IWM | 70 | $187,852 |
| SPY | 120 | $129,500 |
| XLF | 29 | $89,992 |
| XLK | 23 | $11,742 |
| XLE | 18 | $-16,156 |
| TLT | 69 | $-72,565 |
