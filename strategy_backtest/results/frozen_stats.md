# Frozen-book statistics layer (A6 crash-beta · A9 recency · honest Sharpe)

_cross-fill ledger, 196 months · generated 2026-07-09_

## A6 — crash-factor attribution (monthly, Newey-West lags=3)

`pnl%NAV ~ α + β1·SPY + β2·min(SPY,0) + β3·ΔVIX`

| term | coef | t |
| --- | --- | --- |
| α (monthly) | 0.830% NAV ($16,595/mo, $199,138/yr) | **2.75** |
| β SPY | 0.154 | 1.85 |
| β min(SPY,0) (crash convexity) | 0.450 | 2.66 |
| β ΔVIX (per vol pt/100) | 0.1173 | 2.68 |

R² = 0.26. α is the P&L left after paying for equity/crash/vol-of-vol beta.

## A9 — is the cross-sectional edge decaying? (per-year cohort rank-IC)

| year | cohorts | mean rank-IC | IC>0 share | top-2 selection edge |
| --- | --- | --- | --- | --- |
| 2010 | 42 | +0.389 | 90% | +0.078 |
| 2011 | 50 | +0.359 | 88% | +0.193 |
| 2012 | 50 | +0.459 | 98% | +0.221 |
| 2013 | 49 | +0.299 | 84% | +0.125 |
| 2014 | 50 | +0.193 | 78% | +0.083 |
| 2015 | 50 | +0.234 | 84% | +0.163 |
| 2016 | 51 | +0.108 | 67% | -0.043 |
| 2017 | 50 | +0.371 | 94% | +0.175 |
| 2018 | 48 | +0.087 | 52% | +0.085 |
| 2019 | 51 | +0.247 | 75% | +0.094 |
| 2020 | 50 | +0.195 | 74% | +0.096 |
| 2021 | 51 | +0.363 | 94% | +0.216 |
| 2022 | 50 | +0.117 | 64% | +0.052 |
| 2023 | 50 | +0.191 | 76% | +0.112 |
| 2024 | 45 | +0.106 | 69% | +0.044 |
| 2025 | 48 | +0.299 | 90% | +0.190 |
| 2026 | 15 | +0.087 | 80% | -0.047 |

Full-sample mean IC +0.248; trailing-2y mean IC +0.205 (95 cohorts, IC>0 82% of weeks).

## Honest Sharpe — bootstrap CI + deflated Sharpe

- observed Sharpe (ann.) **0.66**; stationary-bootstrap 90% CI [0.22, 1.15] (mean block 6 months, B=4000)
- monthly skew -1.72, kurtosis 6.0
- deflated Sharpe (prob. the true SR > 0 after selection among trials):
    - N=18 documented variants (trial-SR sd 0.32 ann.): **DSR = 0.59**
    - N=40 (undocumented forks scenario): **DSR = 0.45**

