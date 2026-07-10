# Cross-Sectional VRP Put-Spread Strategy — v1.1 DRAFT (pre-registration candidate)

_Drafted 2026-07-09 from the hole-digging program (`results/HOLE_DIGGING_REPORT.md`).
Status: **DRAFT — NOT FROZEN.** Freezing this document starts a fresh §7 evaluation clock;
v1.0 (`FROZEN_STRATEGY_SPEC.md`) remains the standing reference until then._

## 1. What changes vs v1.0 — and nothing else

v1.1 is v1.0 **by reference** (universe, signal, entry selection, structure, exits, fills,
margin caps, filters — all §2 of the frozen spec unchanged) plus exactly one rule, with one
severable optional arm:

| arm | change | rationale |
| --- | --- | --- |
| **v1.1a (primary)** | **OI-cap sizing**: at entry, `contracts ≤ 0.25 × min(short-leg OI, wing OI)`; if the cap rounds below 1 contract, skip the trade. | Closes v1.0 caveat §6.7 (31% of booked size exceeded resting OI and netted −3% of P&L). Liquidity-feasibility rule, PIT, no performance peeking. Backtest: dominates v1.0 on every axis. |
| **v1.1b (optional, severable)** | v1.1a **+ TARGET_DTE 30 → 45, tolerance [25,45] → [35,60]**. | Mechanism-consistent (expiry ≥ h=22 forecast horizon; 21-DTE craters to 0.21) — but born from a 9-cell sweep on the same sample: **hypothesis with multiplicity debt**, promotable only by the shadow run. |

Why only these: the deflated-Sharpe analysis (`results/frozen_stats.md`) priced v1.0's ~18
explored forks at DSR 0.59. Every additional knob spends more of that budget. The OI cap is
included because it is a feasibility correction, not an optimization; the DTE arm is carried
*separately* so it can be dropped without touching v1.1a's evaluation.

Explicitly NOT in v1.1 (all tested and rejected 2026-07 — see v1.0 §5): additive pair-core +
overlay, vol-targeted sizing, entry gates (VIX, IV-rank), managed exits, iron-condor call side,
always-on tail hedge. The conditional `vix≥vix3m` tail-put hold hedge remains a deployment-time
*portfolio* option (crash-beta reducer, Sharpe-neutral), not part of this spec.

## 2. Reference backtest (in-sample; the LAST such numbers before the shadow run)

From `results/xsec_putspread_oicap.md` and `results/xsec_putspread_v11ref.md` (same frozen
machinery, both fills):

| book | trades | cross Sharpe | cross P&L | cross maxDD | mid Sharpe | mid P&L | era Sharpes (cross, 10–13/14–17/18–21/22–26) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| v1.0 frozen | 1525 | 0.66 | $1.92M | $434k | 0.93 | $2.71M | 0.90 / 0.30 / 0.67 / 0.78 |
| **v1.1a** (OI-cap 0.25) | 1525 | **0.89** | $1.77M | $218k | **1.06** | $2.14M | 1.08 / 0.52 / 0.92 / 0.95 |
| **v1.1b** (+ DTE 45) | 1245 | **0.91** | $1.89M | $343k | **1.11** | $2.30M | 1.05 / 0.88 / 1.42 / 0.54 |

Notes: (i) these inherit every v1.0 caveat — realization-dated basis (v1.0's true-MTM haircut was
−0.11 Sharpe; assume similar here until re-marked), multiplicity, cross/mid bounds; (ii) the
OI-cap mechanically shrinks the mean margin per trade (~$25k vs $40k at 1×), so dollar P&L is
lower while risk-adjusted results improve — scale b within §2.6's rules if dollar targets matter;
(iii) v1.1b's headline gain over v1.1a is small (0.89→0.91 cross) and its era profile is uneven —
it fixes the weak 2014–17 era (0.52→0.88) and is superb 2018–21 (1.42) but is the WEAKEST arm in
the most recent era (2022–26: 0.54 vs v1.1a's 0.95) with a higher maxDD ($343k vs $218k). That
recent-era softness is exactly what the shadow run will adjudicate; it is a reason to keep v1.1b
severable, not to promote it.

## 3. Evaluation protocol (unchanged from v1.0 §7, restarted, plus the two new metrics)

1. No further tuning; any change to §1 above is v1.2.
2. Shadow-run ≥ 2 quarters (~26 weekly cohorts), recording: actual fills vs cross/mid bounds,
   MTM daily P&L, margin usage, **realized fill-λ per trade** (must show λ < 1 — at λ = 1 the
   model's alpha over the trivial SPY/QQQ pair is ~$9k/yr and not worth running), and
   **contracts/OI per leg** (audits the cap's real-world bite).
3. Pass criteria: realized monthly Sharpe > 0.4 (read against the MTM basis); fill quality
   ≤ 40% of half-spread (λ ≤ 0.4 beats the pair by ~$25k/yr on the λ-curve); no maxDD > 15% of
   deployed margin beyond what the same weeks' backtest shows.
4. Kill rule: trailing 3-year Sharpe < 0, or a single month losing > 2× the backtest's worst
   month at the deployed scale.
5. Size at start: b = 0.02 with the OI cap binding; raise only after the evaluation passes.

## 4. Repro

```bash
XS_DATA_ROOT=strategy_backtest/data_wide XS_TOPK=2 XS_TRADEABLE=1 XS_MIN_SCORE=0.0 \
.venv/bin/python -m strategy_backtest.experiments.xsec_putspread_v11ref
# -> results/xsec_putspread_v11ref.md (+ xsec_putspread_trades_v11b.csv)
# v1.1a alone: experiments/xsec_putspread_oicap.py (FRACS row 0.25)
```
