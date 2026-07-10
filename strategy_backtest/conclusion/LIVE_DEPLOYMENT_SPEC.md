# Cross-Sectional VRP Put-Spread Strategy — LIVE DEPLOYMENT SPEC v1.2

_Assembled 2026-07-10 from `FROZEN_STRATEGY_SPEC.md` (v1.0), `STRATEGY_SPEC_v1.1_DRAFT.md`
(v1.1a absorbed, v1.1b dropped) and `CADENCE_EXPERIMENTS.md` (Monday cadence adopted).
Repo `rv_estimator` · python 3.12.13 / polars 1.41.1 / numpy 2.4.6._

**Status: FROZEN FOR LIVE EVALUATION.** This is the single reference for what gets deployed.
It contains only rules that carry a demonstrated edge or are pure feasibility corrections —
no rejected variants, no open hypotheses. Any change to §2 is v1.3 and restarts the §7 clock.
The full research record (everything tested, everything rejected, all caveats at length) stays
in `FROZEN_STRATEGY_SPEC.md` §5–§6 and `results/HOLE_DIGGING_REPORT.md`; do not re-litigate
anything there without new evidence.

**What v1.2 is, in one line:** v1.0 frozen spec + OI-cap sizing (v1.1a, a liquidity-feasibility
rule) + fixed-Monday entry (best measured cadence). Nothing else. DTE stays 30. No hedging arm,
no gates, no management — the core book only.

---

## 0. One-paragraph summary

Every **Monday**, rank ~29 liquid ETFs by how rich their options are relative to a bias-corrected
HAR-ensemble forecast of realized variance (`score = log(IV²) − log(rv_hat_cal)`), and sell
defined-risk put-credit spreads (0.25Δ short / 0.10Δ wing, ~30 DTE, hold to expiry) on the **two
richest names that actually fill that day**, sized at $40k max-loss per trade **capped at 25% of
the thinner leg's open interest**. The exact combined configuration, backtested on real ORATS
chains 2010→2026 (§4.1 confirmation run, 2026-07-10): **Sharpe 1.05 cross-fill / 1.22 mid-fill**,
maxDD $268k on $2M NAV, 86% win rate, every era ≥ 0.74 at worst-case fills. The edge is the forecaster's
**cross-sectional ranking** (rank-IC +0.25, ≈34σ vs permutation null, no decay through 2025) —
per-name directional forecasting is a coin-flip and is not what this book relies on. It is an
overlay: ~$330k mean margin on a $2M NAV; the v1.0 form lifted a $2M SPY portfolio's Sharpe from
1.06 to 1.18.

## 1. Provenance of every rule (what's in, and why it earned its place)

| Rule | Source | Evidence it carries an edge |
| --- | --- | --- |
| 29-ETF universe, HYG excluded | v1.0 §2.1 | Breadth 9→29: +35% P&L, higher mid Sharpe, halved QQQ dependence; HYG excluded ex-ante on liquidity |
| EnsembleTopK forecast + trailing de-bias | v1.0 §2.2 | Load-bearing: swapping in trailing-22d RV kills the book (0.02 cross vs 0.66; ~1/27th the P&L) despite keeping 86% of rank-IC — the model's value is trap-avoidance in the tails |
| `score = log(iv²) − log(rv_hat_cal)`, gate `score > 0`, rank, top-2 | v1.0 §2.2–2.3 | Rank-IC +0.246 (t≈25, positive 80% of weeks); top-2 selection edge +0.116 (t≈13); permutation null p<0.0005; random-pick null Sharpe 0.16±0.09 vs 0.66 realized |
| Tradeable-rank walk | v1.0 §2.3 | Load-bearing: without it untradeable names hog slots and Sharpe collapses 0.66→0.43 |
| **Monday entry, both spreads** | cadence study A | Best of all cadences tested: 0.78/1.04 vs 0.66/0.93 floating, same maxDD; economically motivated (weekend-gap premium). In-sample pick — the shadow run adjudicates it (§7) |
| 0.25Δ/0.10Δ put spread, ~30 DTE, hold to expiry | v1.0 §2.4 | The one expression that survived friction; managed exits lose (−$129k vs +$309k hold) |
| G7 liquidity/credit filters | v1.0 §2.5 | Ex-ante fill-feasibility screen |
| **OI-cap sizing (≤0.25× min leg OI)** | v1.1a | Feasibility correction, not an optimization: 31% of v1.0 booked size exceeded resting OI and netted −3% of P&L. With the cap: 0.89 cross / 1.06 mid, maxDD halved ($218k vs $434k), every era improves |
| Group margin cap 20% NAV | v1.0 §2.6 | Concentration control, unchanged |

Dropped from the v1.1 draft: **v1.1b (45 DTE)** — born from a 9-cell sweep (multiplicity debt),
gain over v1.1a marginal (0.89→0.91 cross), weakest arm in the most recent era (2022–26: 0.54 vs
v1.1a's 0.95), higher maxDD. Also excluded: the conditional VIX-term-structure tail hedge —
Sharpe-neutral portfolio option, not part of this book.

## 2. THE SPEC (complete; this section is the contract)

### 2.1 Universe (29 names)

```
Core 9 :  SPY QQQ IWM XLK XLF XLE TLT GLD EEM
Breadth:  XLI XLU XLP XLV XLY XLB DIA EFA FXI EWZ GDX SLV USO XOP SMH XBI IBB KRE XRT IYR
Excluded: HYG — ex-ante liquidity rule (median ATM half-spread 6.1% of premium)
Feature sources (never traded): SPX, VIX chains
```

### 2.2 Signal

- **Forecast `rv_hat`** — EnsembleTopK: equal-weight level-space mean of 4 HAR-family components
  (HARQ, HAR-RS, HAR-CJ, HAR-RS-IV-Q), each an independent per-(ticker, horizon=22) log-OLS,
  walk-forward (expanding window, **monthly refits**, purged + 1-day-embargoed,
  `MIN_TRAIN_DAYS=756`). Inputs: 5-min realized measures (RV, semivariances, jumps, quarticity)
  from Polygon minute bars + per-ticker ORATS IV features.

  All components share the Corsi-HAR backbone `log_rv_{d,w,m}` (log of today's / trailing-5d /
  trailing-22d daily total RV); each adds:

  | Component | Extra features | What it adds |
  | --- | --- | --- |
  | HARQ | `sqrt_rq` (√realized quarticity) | down-weights noisy RV days (measurement-error fix) |
  | HAR-RS | `rs_minus_5d, rs_plus_5d, jump_5d` | downside RV predicts future RV; upside/jumps don't |
  | HAR-CJ | `log_bv_{d,w,m}, log_jump_d` | separates persistent smooth vol from transitory jumps |
  | HAR-RS-IV-Q | HAR-RS + `sqrt_rq` + IV block (`log_iv, iv_slope, skew_25d, vix, vix3m, vix_slope, vvix`) | the only forward-looking member — injects the market's IV/term-structure view |

  **Combiner** (parameter-free, `fit()` is a no-op): `rv_hat = mean(component rv_hat)` in variance
  space; `sigma = √(mean(component σ²) + var(component rv_hat))`. A key needs ≥2 finite-positive
  components or it is dropped, never imputed. `rv_hat` forecasts
  `E[Σ_{s=t+1..t+22} RV_s]`. Verified bit-exact vs the production guide
  (`results/ensemble_verification.md`). Full authoritative model spec:
  `plan_docs/ENSEMBLETOPK_PRODUCTION_GUIDE.md`; source in
  `candidate_models/{ensemble_top,harq,har_rs,har_cj,har_rs_iv_q}.py`.

- **De-bias** (`pit.trailing_debias`): `rv_hat_cal = rv_hat × exp(median of matured log errors)` —
  expanding per-ticker median over forecasts whose 22-day realization has closed (shift 22 rows,
  `min_periods=126`). Zero lookahead; corrects the structural +0.27 median log over-prediction.

- **Implied variance**: `iv2 = iv_30d² × (22/252)` (ORATS 30-day ATM IV, de-annualized).

- **Score**: `log(iv2) − log(rv_hat_cal)` — log-richness of options vs forecast RV.

### 2.3 Entry selection (weekly, Monday)

1. **Cadence: every Monday** (both spreads on the same day). Holiday fallback: the nearest later
   trading day that week, else the nearest earlier. A date needs ≥7 names with valid data
   (`MIN_NAMES_XS=7`) or the week is skipped.
2. **Absolute-richness gate:** drop names with `score ≤ 0`.
3. **Rank** remaining names by score, descending.
4. **Tradeable-rank walk:** walk down the ranked list; for each name attempt to actually open the
   spread on that day's chain (§2.4 + §2.5 + §2.6 including the OI cap); keep the **first 2 that
   fill**. Point-in-time: entry-day chain only. If the OI cap rounds a name's size below 1
   contract, that name does not fill — continue the walk.

### 2.4 Structure & exit

| Parameter | Value |
| --- | --- |
| Structure | Put credit spread: sell ~0.25Δ put, buy ~0.10Δ put (strikes by nearest abs delta; ORATS delta col is the call delta ⇒ put Δ = callΔ − 1) |
| Expiry | nearest to **30 calendar DTE** within [25, 45]; skip the name if none |
| Exit | **hold to expiry**; settle at intrinsic on expiry-day spot (walk back ≤5 sessions if missing). No management arm |

### 2.5 Liquidity / credit filters (applied at fill time, per name)

| Filter | Value |
| --- | --- |
| Open interest | short leg ≥ 50, wing ≥ 10 |
| Relative spread | (ask − bid)/mid ≤ 0.35 per leg |
| Net credit | ≥ $0.05/share AND credit/width ≥ 0.10 |

### 2.6 Sizing & risk

| Parameter | Value |
| --- | --- |
| Base risk per trade | `size_units=1.0 × b=0.02 × NAV` = **$40k max-loss** at $2M NAV; contracts = 40k / ((width − credit) × 100), nearest-rounded |
| **OI cap (binding)** | `contracts ≤ 0.25 × min(short-leg OI, wing OI)` at entry; if the cap rounds below 1 contract, skip the name (the walk continues) |
| Group margin cap | 20% of NAV per correlation group, concurrent accounting (overlapping positions), pro-rata scaling within a (date, group) batch. Group map: `pipeline/config.py` |
| Resulting book | ~8 concurrent positions; OI-cap mean margin ≈ $25k/trade (vs $40k uncapped) |
| Scaling | Start at b = 0.02. Raise toward 2× only after §7 passes; never past the liquidity ceiling — the OI cap enforces this per-trade automatically. Compounding b × current equity is fine |

### 2.7 Fills & costs (accounting conventions)

- Entry bounds: crossing the bid/ask = worst case; mid = best case; live lands in between.
  Record realized **fill-λ** per trade (fill = mid + λ·half-spread).
- Expiry settlement: intrinsic, no spread, no commission.
- Commissions: $0.65 per contract per leg at entry.

## 3. The pipeline, end to end

### 3.1 Data layer (what must be current before the signal can run)

| Input | Source | Used for | Freshness needed at signal time |
| --- | --- | --- | --- |
| 1-min bars, 30 tickers (29 + SPY dup) | Polygon flat files (`us_stocks_sip/minute_aggs_v1`) | daily realized measures: total RV, up/down semivariance, bipower, jumps, quarticity | complete through the prior trading day (the HAR backbone's `log_rv_d` is the latest **complete** session) |
| EOD option chains + 30d ATM IV, slope, 25Δ skew, per ticker | ORATS | `iv2`, IV features, and the entry-day chain for strike selection / fills / OI | entry-day (see §3.4 timing note) |
| VIX, VIX3M, VVIX | ORATS/CBOE | HAR-RS-IV-Q feature block | prior EOD |
| Corp actions + holiday calendar | Polygon reference | split-adjustment, calendar | as published |

Backtest mirror layout (for any re-run): `strategy_backtest/back-test-data/` —
`orats/ticker=<T>/year=<Y>/data.parquet`, `minute/ticker=<T>/data.parquet`, `corp_actions/`,
`market_holidays.parquet`. Master lakes on `/Volumes/Ex-Disk/`.

### 3.2 Forecast stack (weekly-refreshed cache; monthly model refits)

```
pipeline.setup.prepare_panel  → inputs.parquet, targets.parquet     (leakage-safe two-file split)
pipeline.features             → features.parquet                    (HAR backbone + extras + IV block)
pipeline.walkforward × {HARQ, HARRS, HARCJ, HARRSIVQ, EnsembleTopK} --universe all
                              → predictions/EnsembleTopK.parquet    (per-ticker rv_hat, σ, dated)
```

Full historical rebuild: `zsh strategy_backtest/experiments/build_wide_cache.sh` (≈4 min M-series,
`SB_DATA_ROOT=strategy_backtest/data_wide`, `SB_EXTRA_TICKERS=<20 breadth names>`). Walk-forward
protocol: expanding window, refit on the monthly boundary, purge + 1-day embargo between train and
predict — the live cadence must preserve exactly this (refit models once a month; score daily rows
with the standing fit in between).

### 3.3 Signal & selection layer

```
rv_hat ──trailing_debias (expanding matured-error median, per ticker)──► rv_hat_cal
iv_30d ──² × 22/252──────────────────────────────────────────────────► iv2
score = log(iv2) − log(rv_hat_cal)   →  gate score>0  →  rank desc  →  tradeable walk → top-2 fills
```

The de-bias state (per-ticker matured-error history) is part of the system state: persist it, and
append each forecast's log error only when its 22-day window closes.

### 3.4 Execution layer (live Monday runbook)

1. **Pre-open:** confirm minute-bar ingest complete through Friday; refresh features + predictions
   for the latest date; update de-bias medians with newly-matured errors.
2. **Signal:** compute `score` per name, apply the gate, rank. The backtest convention is
   same-day-EOD signal and same-day fill; live, replicate it by computing the score near the
   Monday close (realized-vol features are complete as of Friday and don't move intraday; use
   near-close IV quotes for `iv2`) and working the orders into the close.
   **Fallback:** if orders can't be worked at the signal close, execute Tuesday on Monday's EOD
   signal — measured cost of a 1-day lag on the floating-cadence book was ≈0.12 Sharpe (v1.0
   §6.4); log which mode each entry used.
3. **Walk the ranked list.** Per name: pick expiry (§2.4), strikes by nearest |Δ| (0.25/0.10),
   check filters (§2.5), size = min($40k max-loss formula, 0.25× thinner-leg OI); if < 1 contract
   or any filter fails, next name. Stop at 2 fills.
4. **Apply the group margin cap** (§2.6) across everything concurrently open, pro-rata within
   today's batch.
5. **Record per trade (shadow-run ledger, §7):** timestamps, quotes at decision and at fill,
   realized fill-λ per leg, contracts vs each leg's OI, margin, the full ranked list with scores.
6. **Lifecycle:** no management. At expiry, settle at intrinsic; handle assignment mechanically if
   short leg is ITM (the backtest models European-style intrinsic settlement — see §6).

### 3.5 Reference backtest repro

```bash
# THE v1.2 reference (Monday + OI-cap 0.25 together — the §4.1 confirmation run):
.venv/bin/python -m strategy_backtest.experiments.xsec_putspread_v12ref
# -> results/xsec_putspread_v12ref.md + xsec_putspread_v12ref_trades_{cross,mid}.csv

# Component runs (for attribution):
XS_DATA_ROOT=strategy_backtest/data_wide XS_TOPK=2 XS_TRADEABLE=1 XS_MIN_SCORE=0.0 \
.venv/bin/python -m strategy_backtest.experiments.xsec_putspread_oicap   # OI-cap, floating cadence
.venv/bin/python -m strategy_backtest.experiments.xsec_putspread_dow     # Monday, v1.0 sizing
```

Engine code: `experiments/xsec_putspread_topk.py` (strategy), `backtest/` (chains, marks,
structures, sizing, pit), `pipeline/` (forecast stack).

## 4. Reference results

The v1.2 reference backtest (the §4.1 confirmation run, 2026-07-10) and the component runs it was
pre-registered against (same frozen engine, real ORATS chains 2010→2026, both fill bounds):

| book | trades | Sharpe cross | Sharpe mid | maxDD (cross) | P&L cross | era Sharpes cross (10–13/14–17/18–21/22–26) |
| --- | --- | --- | --- | --- | --- | --- |
| **v1.2 (Monday + OI-cap) — THIS SPEC** | 1580 | **1.05** | **1.22** | **$268k** | $2.02M | **1.19 / 0.74 / 1.37 / 0.89** |
| v1.0 frozen (baseline) | 1525 | 0.66 | 0.93 | $434k | $1.92M | 0.90 / 0.30 / 0.67 / 0.78 |
| + OI-cap only (v1.1a) | 1525 | 0.89 | 1.06 | $218k | $1.77M | 1.08 / 0.52 / 0.92 / 0.95 |
| + Monday only (v1.0 sizing) | — | 0.78 | 1.04 | $433k | $2.41M | strong all eras except flat-vol 2014–17 |

v1.2 detail (from `results/xsec_putspread_v12ref.md`): 805 Monday cohorts, 86% win rate, mean
margin ≈ $24.5k/trade (the OI cap binds size well below the $40k budget), worst realization-dated
month **−$188k** (May-2010; Mar-2020 second at −$170k) — these are the §7 comparison anchors.
Context (v1.0 numbers, expected to carry over): monthly corr to SPY +0.42; as an overlay the v1.0
form lifted a $2M SPY portfolio 1.06 → 1.18 Sharpe.

### 4.1 The combined confirmation run — COMPLETED 2026-07-10

The exact v1.2 configuration (Monday **and** OI-cap together) had never been backtested when this
spec was assembled; a single pre-registered confirmation run was required before the shadow clock
starts. It has now been run — `experiments/xsec_putspread_v12ref.py`, composing
`xsec_putspread_dow.py`'s Monday rule with `xsec_putspread_oicap.py`'s 0.25 cap verbatim, nothing
else changed:

- **Result: cross 1.05 / mid 1.22, maxDD $268k** — comfortably above the pre-registered abort
  threshold (cross < 0.66) and better than both component runs. The two changes compound rather
  than interfere: Monday's extra P&L arrives on the OI-cap's halved risk base, and every era
  improves vs v1.0 (weakest era 2014–17 at 0.74 vs v1.0's 0.30).
- **No parameter was changed in response to this run** (it confirmed; nothing was tuned). Per
  §7.1 it is the last permitted backtest before the shadow run.
- Read it honestly: these are still in-sample numbers on the same 2010→2026 sample every choice
  was made on, inherit the realization-dated basis (v1.0's true-MTM haircut was ≈ −0.11 Sharpe;
  assume similar), and sit on top of the §6.1 multiplicity stack. The §7 pass bar stays 0.4.

## 5. Why this has an edge (the mechanism, briefly)

The edge is **cross-sectional**: ranking the universe by `score` sorts names by their *realized*
IV-richness that week (rank-IC +0.246, t≈25, positive 80% of weeks, ≈34σ vs a within-date
permutation null; no decay — trailing-2y IC +0.205, 2025 = +0.299). Selling the top-2 harvests
genuine dispersion in the vol-risk premium: a random-pick null on the identical gated cohorts
Sharpes 0.16 ± 0.09 vs the realized 0.66, and a crash-factor regression (SPY, min(SPY,0), ΔVIX)
leaves residual α ≈ $199k/yr (t = 2.75) — the book is short the crash factor but is not only that.

The **forecaster is load-bearing**, not a garnish: substituting trailing-22d RV for `rv_hat_cal`
keeps 86% of the rank-IC yet destroys ~96% of worst-case P&L, because the model's value
concentrates where equal-weight IC can't see it — deflating scores on high-forward-vol trap names
(EWZ/USO/FXI) and picking QQQ 4× more often. Per-name directional forecasting skill is ≈ a
coin-flip at h=22; the book does not use it and does not need it.

**The model's alpha is execution-conditional.** Over a trivial "sell SPY+QQQ every week" pair, the
model's incremental alpha is ~$37k/yr at mid fills decaying to ~$9k/yr at full spread-crossing
(breakeven ≈ λ = 1). Execution quality is what pays for running the model — hence fill-λ is a
first-class §7 metric, not a nice-to-have.

## 6. Caveats that survive into v1.2 (read before believing the numbers)

1. **Multiplicity.** All parameters were chosen on 2010–2026. v1.0's deflated Sharpe was 0.59
   against 18 documented forks (bootstrap 90% CI on 0.66: [0.22, 1.15]); Monday adds one more
   in-sample layer (+0.12 is an upper bound). True expectation sits below the point estimates —
   this is exactly why §7 exists and why the pass bar is 0.4, not 0.9.
2. **MTM basis.** Backtest P&L is realization-dated; re-marked daily, v1.0's true MTM path
   Sharped ~0.11 lower with worst MTM month −$264k (2019-05, a vol chop). Read §7's pass criteria
   against the MTM basis.
3. **Fill bounds.** Cross = worst case, mid = best; live in between. Mid assumes current clip
   sizes (median ~112 contracts pre-cap; smaller with the cap, which helps).
4. **Signal→fill timing.** Same-day-EOD convention; a 1-day execution lag costs ≈0.12 Sharpe
   (measured on the floating-cadence book). Budget for it if Monday-close execution isn't
   achievable (§3.4).
5. **Crash beta.** +0.42 monthly SPY correlation; long equity-crash exposure (convexity β 0.45).
   The binding drawdown in backtest is the 2014–16 low-vol grind, not a crash.
6. **Settlement model.** ~8% of trades settle within ±1% of the short strike (pin/assignment
   zone); early assignment on distribution-paying ETFs is unmodeled. Live, handle assignment
   mechanically and log any deviation from intrinsic settlement.

## 7. Pre-registered evaluation protocol (MANDATORY before real capital)

1. **No further tuning.** Any §2 change ⇒ v1.3, clock restarts. The §4.1 combined confirmation
   run (completed 2026-07-10, no parameters changed) was the last permitted backtest.
2. **Shadow-run ≥ 2 quarters (~26 Monday cohorts)** at b = 0.02, recording per trade: actual
   fills vs cross/mid bounds, realized **fill-λ** per leg, **contracts / leg OI**, daily MTM P&L,
   margin usage, execution mode (Monday-close vs T+1 fallback).
3. **Pass criteria (set now):**
   - realized monthly Sharpe > **0.4** (MTM basis);
   - realized fill-λ ≤ **0.4** (at λ = 0.4 the model beats the trivial pair by ~$25k/yr; at
     λ = 1 its alpha is ~$9k/yr and not worth running);
   - no maxDD > 15% of deployed margin beyond what the same weeks' §4.1 reference shows.
4. **Kill rule (live, set now):** stop if trailing 3-year Sharpe < 0, or a single month loses
   > 2× the §4.1 reference's worst month at the deployed scale (reference worst month −$188k at
   b = 0.02 / $2M NAV, realization-dated ⇒ kill at a month worse than −$376k at 1×, scaled with b).
5. **Sizing path:** start b = 0.02 ($40k/trade pre-cap at $2M NAV) with the OI cap binding.
   Raise toward 2× only after the evaluation passes. The user's stated hurdle for real capital
   is realized Sharpe ≥ 1; passing §7.3 authorizes scaling the shadow book, not skipping that
   hurdle.

## 8. Document map

| Doc | Role |
| --- | --- |
| `LIVE_DEPLOYMENT_SPEC.md` (this) | what gets deployed — the v1.2 contract |
| `FROZEN_STRATEGY_SPEC.md` | v1.0 reference: full results, all rejected variants (§5), full caveat detail (§6), research provenance |
| `STRATEGY_SPEC_v1.1_DRAFT.md` | superseded — v1.1a absorbed here; v1.1b (45 DTE) dropped |
| `CADENCE_EXPERIMENTS.md` | cadence evidence behind the Monday rule |
| `plan_docs/ENSEMBLETOPK_PRODUCTION_GUIDE.md` | authoritative forecaster spec |
| `results/HOLE_DIGGING_REPORT.md` + `results/frozen_*.md` | robustness program: stats, MTM, forensics, λ-curve |
