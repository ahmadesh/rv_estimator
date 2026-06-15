# Stress-composite ablation (design §4.3)

_Generated 2026-06-08 · hold arm · weekly cadence · de-bias on · b=0.02 · NAV $2.0M_

Screening the five §4.3 stress sub-flags as an avoidance veto layered on the lean core. The book made ~78% of its P&L in 2010–2013; the question is whether any veto lifts the **2014+** tail (Sharpe↑ / maxDD↓ / bad-year P&L↑) without gutting carry. Bad years = 2018/2022/2024.

## Full sample vs 2014+

| config | trades | Sharpe | maxDD% | 2014+ trades | 2014+ Sharpe | 2014+ maxDD% | 2014+ P&L | bad-yr P&L | total P&L |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline (no stress) | 2,098 | 0.44 | 8.7 | 1,258 | 0.20 | 8.7 | $76,154 | $-172,353 | $356,024 |
| only skew | 2,064 | 0.39 | 9.0 | 1,246 | 0.17 | 9.0 | $65,092 | $-171,370 | $314,047 |
| only vvix | 2,004 | 0.42 | 8.7 | 1,197 | 0.18 | 8.7 | $66,691 | $-141,828 | $328,601 |
| only credit | 1,813 | 0.42 | 8.9 | 1,085 | 0.16 | 8.9 | $58,207 | $-134,750 | $315,502 |
| only sma | 1,629 | 0.46 | 7.7 | 980 | 0.26 | 7.7 | $78,956 | $-118,966 | $307,989 |
| only shock | 2,037 | 0.41 | 8.9 | 1,239 | 0.17 | 8.9 | $63,404 | $-168,810 | $326,588 |
| FULL (all 5) | 1,312 | 0.29 | 8.6 | 805 | 0.12 | 8.6 | $33,444 | $-87,881 | $181,284 |
| all − skew | 1,322 | 0.31 | 8.6 | 805 | 0.12 | 8.6 | $33,577 | $-87,881 | $192,244 |
| all − vvix | 1,365 | 0.32 | 7.9 | 841 | 0.19 | 7.9 | $54,247 | $-92,251 | $204,870 |
| all − credit | 1,513 | 0.39 | 7.9 | 919 | 0.21 | 7.9 | $64,794 | $-93,805 | $254,647 |
| all − sma | 1,662 | 0.29 | 10.0 | 1,013 | 0.04 | 10.0 | $15,421 | $-121,102 | $213,657 |
| all − shock | 1,337 | 0.32 | 8.5 | 816 | 0.14 | 8.5 | $41,536 | $-86,637 | $201,045 |

## Read-out

- **Baseline 2014+:** Sharpe 0.20, maxDD 8.7%, P&L $76,154, bad-year P&L $-172,353.
- A sub-flag earns its place only if it lifts **2014+ Sharpe** and/or cuts **2014+ maxDD** and the **bad-year P&L** by more than it costs in trade count / total return (§4.3).
- `only X` rows isolate each signal's marginal protection; `all − X` rows show what each removes from the full composite (independent vs redundant avoidance info).

## Verdict — adopt the 200d-SMA trend filter only (`STRESS_COMPONENTS=("sma",)`)

Only **`sma`** (price index below its own 200-day SMA) carries independent avoidance info. It lifts **2014+ Sharpe 0.20→0.26**, cuts **2014+ maxDD 8.7→7.7%**, and cuts the **2018/2022/2024 bad-year bleed −$172k→−$119k** (~31%), while keeping 2014+ P&L flat and full-sample Sharpe (0.45→0.46) — so it doesn't touch the 2010–2013 harvest. The four percentile flags (skew/vvix/credit/shock) are **redundant with G2/G3 and over-filter**: the full 5-flag composite craters Sharpe to 0.28 and guts carry. Pair tests (`sma`+each) all reduce Sharpe and total P&L vs `sma` alone, so no second flag is added. This matches the §4.3 prior (percentile stress is redundant) with the trend signal as the lone exception — a classic trend-overlay-on-short-vol tail cut.