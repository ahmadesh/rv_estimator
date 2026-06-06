# Stage-1 Trading Evaluation — Economic Results Report

**Scope.** Economic scoring of the **frozen** Stage-1 short-vol variance-proxy backtests
(`trade_eval/results/`), per `STAGE1_TRADING_EVAL_PLAN.md` §4–§8. This is the *scoring layer only*:
no refits, no pipeline changes — every number is read off the frozen `ledger/` and `portfolio/`
parquets over the **2018-01 → 2026-05 OOS folds**. Six forecasters × three horizons × seven
ablations = **104 cells** (`manifest.parquet`); that 104 is the trial count used to deflate the
headline Sharpe.

**Reproduce:** `.venv/bin/python -m trade_eval.reports.score_stage1`
→ `scorecard.parquet` (per-cell), `attribution.parquet` (A1–A9 marginals), `verdicts.parquet`
(go/no-go matrix), `_scoring_dump.json` (significance tables).

**Reading protocol (the binding §5 caveat).** At 30 DTE (h=22) IV² already prices essentially
all predictable VRP, so we do **not** look for mean-return alpha there. Every readout leads with
**Deflated Sharpe (DSR)** and **CVaR/left-tail**; mean return is a supporting number. Significance
is HAC (Newey-West) Diebold-Mariano + a **moving-block bootstrap** (block ≥ 22 calendar days,
overlap-aware) on the P&L series, on **common support** vs the IV-only benchmark.

---

## 0. Headline verdict

> **The forecast pays at 30 DTE, and it pays exactly where the §5 caveat said it would — in the
> left tail, through the regime gate and σ-sizing, not in mean return. It does *not* pay at 7–14
> DTE, where the hypothesized short-horizon directional alpha failed to show and the IV-only
> seller is the better book.**

**Stage-2 survivors (promoted, all at h=22 / 30 DTE only):**

| Role | Model | h | Why it passes |
|---|---|---|---|
| **Primary** | **EnsembleTopK** | 22 | DSR 0.68 (vs IV 0.28); CVaR95 −0.018 vs IV −0.064; maxDD 0.051 vs IV 0.203; gate marginal sig (ΔCVaR95 +0.044, p=0.026); beats both A7 controls; break-even ≈ 312 bps. |
| **Fallback** | **HAR-X** | 22 | DSR 0.57; CVaR95 −0.016; maxDD 0.053; σ-sizing marginal sig (ΔSharpe p=0.003); break-even ≈ 336 bps. |
| **Sleeve (thin names)** | **HAR-Shrink2Group** | 22 *(and 10)* | DSR 0.58; **beats IV on mean too** (boot p=0.035 @22, p=0.004 @10); best hard-case book; σ-sizing sig (p=0.008). The only model that also clears the bar at 14 DTE. |
| **Sleeve bound (watch)** | **PanelHAR-FE** | 22 | Marginal pass (DSR 0.333 vs IV 0.277); worst tail of the four (CVaR95 −0.029, maxDD 0.152). Promote *only inside the sleeve*, where Shrink2Group dominates it. |

**No-Go:** every h=5 and h=10 cell except `HAR-Shrink2Group@h10`; **HAR-ENet at every horizon**
(the short-horizon directional candidate never beat IV-only); the **A9 managed overlay at h=22**
(churns the book, gives back return, no net tail gain).

**The one caveat on the passes:** *no* cell in the entire 104-grid clears the **absolute** DSR≥0.95
bar. After deflating for 104 trials the benchmark per-observation Sharpe is SR₀≈0.21 (≈1.4
annualized on the 125 monthly h=22 observations); the best strategy reaches 0.94 annualized. So the
four h=22 passes **beat IV-only on deflated Sharpe (relative)** and win the tail decisively, but
their Sharpe is not individually distinguishable from the best-of-104 null at 95% — an effect-size
*and* a power limitation (8 years ⇒ ~125 monthly obs). The promotion rests on criterion 2 (tail
no-regress — the dominant criterion for a short-gamma book) and criterion 3 (signal attribution),
which are met cleanly; the deflated-Sharpe criterion is met only in the relative sense. This is
flagged on every verdict below rather than buried.

---

## 1. Method notes (so the numbers are legible)

- **P&L series.** Each `portfolio/<cell>.parquet` is the one-position-per-group book P&L indexed by
  roll date. Cadence is the roll cadence, not calendar-daily: median gap ≈ 28 d at h=22, ≈ 5 d at
  h=5. So an "observation" already aggregates ~h days; the block bootstrap uses
  `block = ceil(22 / median_gap)` observations (≥2) to respect the ≥22-calendar-day overlap rule.
- **Deflated Sharpe (Bailey–López de Prado).** Per-observation SR, corrected for skew/kurtosis,
  deflated by `SR₀ = √Var(SR over the 104 trials)·[(1−γ)Z(1−1/N) + γZ(1−1/(Ne))]`, N=104,
  γ=0.5772. `Var(SR)` across the 104 cells = **0.00660**, giving SR₀ ≈ 0.206 (per-obs). DSR is the
  probability the true SR exceeds SR₀; "beats IV" = the model's DSR exceeds the IV-only cell's DSR
  at the same horizon.
- **CVaR(95/99)** = mean of the worst 5%/1% of book observations (a loss, negative). Tail panel also
  reports worst single observation, worst-20-observation sum, max drawdown (on the cumulative
  equity), Sortino/downside deviation.
- **Significance vs IV-only** runs on the **inner-join common support** (dates both books cover);
  per-group P&L over each model's own covered dates; never imputed.
- **A2/A9 attribution caveat.** Turning the gate off (A2) or adding management (A9) *changes the set
  of trade dates*, so the paired common-support test sees only the intersection and **structurally
  understates the gate** (its whole value is in the dates it removes). For A2 and A9 the report leads
  with the **full-book** scorecard; A3/A5 keep the same trade set, so their paired tests are exact.

---

## 1b. Metric glossary (what every column means)

Short-vol P&L is **short-gamma and negatively skewed** — it makes small gains most months and
occasionally loses a lot. Plain average return and plain Sharpe flatter it, so the metrics below
lead with risk-adjusted and left-tail measures. All P&L is in **summed-variance units** (the same
units `iv2` and `target_var` live in); a "book observation" is one roll-date P&L of the
one-position-per-group portfolio.

**Headline risk-adjusted**

| Term | Plain-English meaning | How to read it |
|---|---|---|
| **Sharpe (ann.)** | Average return ÷ volatility of return, annualized. Reward per unit of wiggle. | Higher = better. ~1.0 is decent; but for short-vol it *understates* risk because it ignores skew. |
| **DSR** (Deflated Sharpe Ratio) | The **probability that the strategy's true Sharpe is genuinely positive**, after two honesty adjustments: (1) it corrects for the fat-tailed, skewed return shape, and (2) it *deflates* for the fact that we tried **104 strategy variants** — with that many tries, some will look good by luck. | A probability in [0,1]. **0.95 = the 95%-confidence "statistically significant" bar.** 0.68 means "68% confident the edge is real after accounting for luck/multiple-testing" — suggestive, not conclusive. "Beats IV" = the model's DSR exceeds the IV-only benchmark's DSR at the same tenor. |
| **SR₀** | The Sharpe a *lucky* strategy would post by chance given 104 tries (the deflation benchmark). Here ≈0.21 per-observation ≈ **1.4 annualized**. | A strategy must beat SR₀ to be credible. None did in absolute terms; the best was 0.94 annualized. |

**Left-tail / downside (the dominant axis for a short-gamma book)**

| Term | Plain-English meaning | How to read it |
|---|---|---|
| **CVaR95** (95% Conditional Value-at-Risk, a.k.a. Expected Shortfall) | The **average loss on the worst 5% of months** — "when it goes bad, how bad on average?" | A negative number; **closer to zero = better (smaller tail)**. −0.018 vs −0.064 means the second book loses ~3.5× more in its bad tail. |
| **CVaR99** | Same idea on the **worst 1%** of months — the deeper, rarer tail. | Negative; closer to zero = better. |
| **worst-day** / **worst-20** | The single worst observation / the worst 20-observation cumulative loss. | Negative; closer to zero = better. The crash-day and crash-window exposure. |
| **maxDD** (max drawdown) | The largest peak-to-trough drop in the cumulative equity curve — the worst losing streak you'd have lived through. | Positive number; **smaller = better.** 0.05 vs 0.20 = a 4× shallower worst stretch. |
| **Sortino** | Like Sharpe but only penalizes *downside* volatility (upside swings don't count as "risk"). | Higher = better. Fairer than Sharpe for skewed P&L. |
| **downside deviation** | The volatility of *negative* returns only — the denominator of Sortino. | Lower = better. |

**Activity, cost, supporting**

| Term | Plain-English meaning | How to read it |
|---|---|---|
| **AnnRet** | Annualized average return (gross of nothing — net of the modeled cost). | Higher = more profit, but for short-vol must always be read *next to* CVaR/maxDD. |
| **break-even (BE) bps** | The per-trade cost (in basis points) at which the edge is fully eaten — profit goes to zero. | Higher = more cost-robust. The 5-bps default and 20-bps stress are the realistic points; BE ≈ 312 means the edge survives ~60× the default cost (in the Stage-1 abstraction). |
| **hit rate** | Fraction of observations that made money. | Short-vol typically has a *high* hit rate with rare big losses — high hit rate alone is not safety. |
| **n_obs / common support** | Number of book observations / the dates two books *both* trade (used for fair head-to-head tests). | More obs = more statistical power. h=22 has only ~125 monthly obs over 8 years — a real power limit. |

**Significance / attribution**

| Term | Plain-English meaning | How to read it |
|---|---|---|
| **DM p (Diebold-Mariano)** | p-value of a HAC (autocorrelation-robust) test that one book's mean P&L beats another's. | **Smaller = stronger evidence.** < 0.05 = significant. One-sided here (testing "model > IV"). |
| **Boot p** (block-bootstrap p) | Same question answered by resampling the P&L series in ≥22-day blocks (respects the overlapping windows). | Smaller = stronger. < 0.05 = significant. Reported alongside DM as a robustness check. |
| **ΔCVaR95 / ΔSharpe (p)** | An **ablation's marginal contribution**: how much turning a signal on (gate, sizing) changes the tail/Sharpe, with its significance. | Positive Δ = the signal *helps*; p < 0.10 = that help is statistically credible. |
| **A1…A9** | The ablation map (§5): A1 forecast-vs-IV, A2 gate on/off, A3 sizing on/off, A4 sleeve-vs-core, A5 σ-vs-quantile size, A6 ensemble-vs-fallback, A7 random/always controls, A8 horizon sweep, A9 managed-vs-hold. | Each isolates *one* signal so value can be attributed to it rather than to short-vol carry. |

---

## 1c. The two strategies being compared

Every test pits a **forecast-driven short-vol book** against the **IV-only benchmark**. Both *sell
volatility* — they collect a premium when the market's implied variance (`iv2`) sits above the
variance that actually gets realized — but they decide *when* and *how much* to sell differently.

**IV-only (the benchmark / null).** The fair-vol straw man. It sells vol whenever implied looks rich
versus a simple **trailing realized variance** — `vrp = iv2 − trailing_RV` — and sizes every trade
**flat** (same notional each time). **No forecast, no regime gate, no risk-based sizing.** It is the
"just harvest the volatility-risk premium" book that any options desk can run without a model. The
question this whole study asks is: *does the RV forecaster add anything on top of this?* Beating a
random-walk seller is not the bar — beating *this* disciplined-but-naive IV seller is.

> Why it's the right benchmark: at 30 DTE, IV² already prices essentially all the predictable
> variance-risk premium (the binding §5 caveat). So if a forecast can't beat a book that just sells
> when IV² is rich, the forecast adds no *economic* value at that tenor — regardless of how good its
> QLIKE looks.

**Forecast-gated book (what each model runs).** Same short-vol payoff, but the frozen RV forecast
steers three decisions: (1) a **conditional VRP score** `iv2 − rv_hat` decides candidacy; (2) a
**regime gate** `{trade / reduce / avoid}` — driven by the forecast's *uncertainty* (`sigma/rv_hat`)
and shock flags — **sits out** names it thinks are about to blow up; (3) **inverse-risk sizing**
`∝ vrp_score / σ²` trades smaller when the forecast is less sure. The hypothesis (§5) is that at
30 DTE the forecast can't out-*predict* IV² on average, but its **second moment** (σ, the gate) lets
the book **avoid the variance spikes** the flat IV-only seller walks straight into — i.e. it wins on
the **tail**, not on mean return. That is exactly what the results below show.

---

## 2. Per-(model, horizon) economic scorecard — baseline, led by DSR + CVaR

All over the frozen 2018→2026 OOS folds. CVaR/maxDD/worst-20 are losses; less-negative = better.
`BE bps` = break-even cost (default-name bps the edge survives to).

### h = 22 (30 DTE) — the primary book

| Model | DSR | Sharpe(ann) | CVaR95 | CVaR99 | worst-20 | maxDD | AnnRet | BE bps |
|---|---|---|---|---|---|---|---|---|
| **EnsembleTopK** | **0.682** | 0.943 | **−0.0181** | −0.0403 | **−0.0287** | **0.0513** | 0.0465 | 312 |
| **HAR-Shrink2Group** | 0.579 | 0.855 | −0.0170 | −0.0464 | −0.0620 | 0.0726 | 0.0547 | 413 |
| **HAR-X** | 0.565 | 0.772 | −0.0164 | −0.0383 | −0.0412 | 0.0529 | 0.0354 | 336 |
| PanelHAR-FE | 0.333 | 0.586 | −0.0286 | −0.0825 | −0.1201 | 0.1519 | 0.0402 | 287 |
| *IV-only (bench)* | *0.277* | *0.621* | *−0.0637* | *−0.1650* | *−0.1696* | *0.2026* | *0.0676* | *220* |

**Read:** the four forecast books carry roughly the same annual return as IV-only but with a **3–4×
smaller left tail and a 3–4× smaller drawdown**. IV-only earns the most (0.068) and ranks *last* on
DSR because it pays for that carry with a −0.064 CVaR95 and a 20% drawdown. This is the §5 result in
one table: at 30 DTE the forecast doesn't out-earn IV² — it out-survives it.

### h = 10 (14 DTE)

| Model | DSR | Sharpe | CVaR95 | maxDD | AnnRet |
|---|---|---|---|---|---|
| **HAR-Shrink2Group** | **0.161** | 0.712 | −0.0191 | 0.147 | 0.0454 |
| *IV-only* | *0.134* | *0.786* | *−0.0337* | *0.184* | *0.0689* |
| EnsembleTopK | 0.057 | 0.462 | −0.0234 | 0.151 | 0.0292 |
| HAR-X | 0.026 | 0.254 | −0.0155 | 0.134 | 0.0127 |
| HAR-ENet | 0.016 | 0.246 | −0.0250 | 0.164 | 0.0166 |
| PanelHAR-FE | 0.010 | 0.181 | −0.0367 | 0.294 | 0.0202 |

Only **Shrink2Group** clears IV-only here (and only just).

### h = 5 (7 DTE)

| Model | DSR | Sharpe | CVaR95 | maxDD | AnnRet |
|---|---|---|---|---|---|
| *IV-only* | *0.370* | *1.451* | *−0.0202* | *0.155* | *0.1071* |
| EnsembleTopK | 0.296 | 1.353 | −0.0086 | 0.118 | 0.0669 |
| HAR-Shrink2Group | 0.056 | 0.811 | −0.0084 | 0.117 | 0.0393 |
| HAR-ENet | 0.016 | 0.549 | −0.0107 | 0.122 | 0.0283 |
| HAR-X | 0.023 | 0.507 | −0.0065 | 0.103 | 0.0196 |
| PanelHAR-FE | 0.001 | 0.214 | −0.0140 | 0.224 | 0.0173 |

**IV-only wins outright at 7 DTE** on DSR, Sharpe and return. The forecast books only "win" the tail
because the gate throttles the position so hard that the carry that makes 7-DTE short-vol profitable
is left on the table. The expected short-horizon directional edge did **not** materialise.

*(Full per-cell numbers incl. Sortino, hit-rate, avg win/loss, cost sweep → `scorecard.parquet`.)*

---

## 3. A1–A9 attribution — where (if anywhere) the forecast adds value

### A1 — forecast-gated vs IV-only (common support, model − IV-only)

| h | Model | n_common | AnnΔ vs IV | Sharpe m / IV | CVaR95 m / IV | DM p (1-sided) | Boot p |
|---|---|---|---|---|---|---|---|
| 22 | EnsembleTopK | 89 | −0.025 | 0.36 / 0.15 | **−0.008 / −0.069** | 0.80 | 0.80 |
| 22 | HAR-Shrink2Group | 41 | **+0.014** | 0.35 / 0.38 | −0.011 / −0.010 | 0.069 | **0.035** |
| 22 | PanelHAR-FE | 44 | **+0.011** | 0.45 / 0.45 | −0.007 / −0.008 | 0.019 | **0.006** |
| 22 | HAR-X | 24 | +0.009 | 0.35 / 0.11 | −0.016 / −0.030 | 0.257 | 0.311 |
| 10 | HAR-Shrink2Group | 112 | **+0.018** | 0.10 / 0.02 | −0.038 / −0.041 | 0.011 | **0.004** |
| 10 | EnsembleTopK | 218 | −0.031 | 0.03 / 0.09 | −0.020 / −0.044 | 0.98 | 0.98 |
| 5 | EnsembleTopK | 467 | −0.072 | 0.09 / 0.18 | −0.008 / −0.023 | 1.00 | 1.00 |

**Read.** On **mean return**, A1 is flat-to-negative for the EnsembleTopK/HAR-X clean-core path at
every horizon (the §5 caveat, confirmed — and at h=5 IV-only is *significantly* ahead). The
exception is the **pooling sleeve**: `HAR-Shrink2Group` and `PanelHAR-FE` beat IV-only on mean at
h=22 (boot p=0.035 / 0.006) and Shrink2Group again at h=10 (p=0.004). Where A1 is flat (EnsembleTopK
@22), the value is entirely in the CVaR column: −0.008 vs IV's −0.069.

### A2 — regime gate on vs off (full book, h=22)

| Model | maxDD gated → no-gate | worst-20 gated → no-gate | Sharpe gated / no-gate | Paired ΔCVaR95 (p) |
|---|---|---|---|---|
| EnsembleTopK | **0.051 → 0.431** | −0.029 → −0.266 | 0.94 / 0.68 | +0.044 (**0.026**) |
| HAR-Shrink2Group | 0.073 → 0.433 | −0.062 → −0.287 | 0.86 / 0.93 | +0.038 (0.054) |
| HAR-X | 0.053 → 0.394 | −0.041 → −0.227 | 0.77 / 0.98 | +0.038 (0.080) |
| PanelHAR-FE | 0.152 → 0.559 | −0.120 → −0.317 | 0.59 / 0.77 | +0.047 (0.082) |

**The single clearest result in the study.** Removing the gate at 30 DTE blows the drawdown up
**~8×** (0.05 → 0.43 for EnsembleTopK) and the worst-20 ~9× — because the gate's value is precisely
the variance-spike dates it *refuses to sell into*, which the paired test can't see (hence the
paired ΔCVaR95 p≈0.03–0.08 understates it). EnsembleTopK keeps a higher Sharpe **with** the gate;
for the others the gate trades a little Sharpe for a massive drawdown cut — the right trade for a
short-gamma book. **At h=5/h=10 the sign flips:** removing the gate *raises* Sharpe sharply (HAR-X
0.51 → 2.56; EnsembleTopK 1.35 → 2.02 at h=5) for only modestly worse tails — the gate is too
conservative at short DTE and suppresses the carry. **Gate value is a 30-DTE phenomenon.**

### A3 — forecast σ-sizing on vs off (full book, h=22)

| Model | CVaR95 sized → flat | maxDD sized → flat | DSR sized → flat | Paired ΔSharpe (p) |
|---|---|---|---|---|
| EnsembleTopK | −0.018 → −0.039 | 0.051 → 0.147 | 0.68 → 0.33 | +0.092 (0.16) |
| HAR-Shrink2Group | −0.017 → −0.041 | 0.073 → 0.201 | 0.58 → 0.27 | +0.092 (**0.008**) |
| HAR-X | −0.016 → −0.045 | 0.053 → 0.194 | 0.57 → 0.20 | +0.121 (**0.003**) |
| PanelHAR-FE | −0.029 → −0.051 | 0.152 → 0.207 | 0.33 → 0.08 | +0.096 (**0.049**) |

Inverse-risk (σ-keyed) sizing **roughly halves CVaR95 and cuts maxDD 2–3×** at 30 DTE, lifting DSR
materially. The marginal Sharpe contribution is statistically significant for HAR-X (p=0.003),
Shrink2Group (p=0.008) and PanelHAR-FE (p=0.049); for EnsembleTopK the point estimate is positive
but not individually significant (p=0.16). The second moment earns its keep at 30 DTE.

### A5 — σ-sizing vs quantile-spread sizing (q95−q05)

Across the grid, quantile-spread sizing **lowers mean return** (ΔP&L negative, often boot-significant)
while **marginally improving CVaR** (ΔCVaR95 > 0, p ≈ 0.01–0.07 at h=5/10). Sharpe is essentially
unchanged. Verdict: the full quantile grid does **not** size better than a single σ — it buys a
little tail for a little return, a wash. The σ head is sufficient downstream; carrying q05…q95 for
sizing is not justified on these results. (Diagnostic only; not a go/no-go axis.)

### A6 — EnsembleTopK vs HAR-X (primary vs fallback)

EnsembleTopK ≥ HAR-X at **every** horizon: h=22 DSR 0.68 vs 0.57 (Sharpe 0.94 vs 0.77, equal tails);
h=10 0.057 vs 0.026; h=5 Sharpe 1.35 vs 0.51. The ensemble earns its (small) complexity over the
transparent fallback — but HAR-X is close enough at h=22, and more interpretable, to remain the
graceful-degrade fallback rather than be dropped.

### A7 — controls (random-entry / always-sell)

The signal is not luck or carry. At h=22, baseline Sharpe **crushes** both controls (EnsembleTopK
0.94 vs random 0.03 / always 0.21) and baseline CVaR95 is 5–8× better (−0.018 vs random −0.139 /
always −0.144). Same ordering at h=5/h=10. Every promoted cell beats both controls on Sharpe and
CVaR — criterion 3's "edge ≠ control" condition is satisfied throughout.

### A8 — horizon sweep (per-tenor ranking)

| Tenor | Winner | 2nd | Story |
|---|---|---|---|
| **7 DTE (h=5)** | **IV-only** (DSR 0.37) | EnsembleTopK 0.30 | Forecast loses; carry dominates; gate over-throttles. |
| **14 DTE (h=10)** | **HAR-Shrink2Group** 0.16 | IV-only 0.13 | Only the pooling sleeve edges the benchmark. |
| **30 DTE (h=22)** | **EnsembleTopK** 0.68 | Shrink2Group 0.58 | All four forecast books beat IV-only; tail control is the source. |

The promotion ranking is horizon-specific exactly as the plan anticipated — but in the *opposite*
direction to the directional-alpha prior: value concentrates at **30 DTE**, not 7–14 DTE.

### A9 — managed (daily re-gating) vs hold-to-expiry (full book)

| h | Model | Sharpe hold → managed | maxDD hold → managed | CVaR95 hold → managed |
|---|---|---|---|---|
| 5 | EnsembleTopK | 1.35 → **2.64** | 0.118 → **0.021** | −0.009 → −0.002 |
| 5 | HAR-X | 0.51 → **1.97** | 0.103 → 0.019 | −0.006 → −0.002 |
| 5 | *IV-only* | *1.45 → **3.19** (DSR 0.96)* | *0.155 → 0.037* | *−0.020 → −0.007* |
| 10 | HAR-Shrink2Group | 0.71 → 1.56 | 0.147 → 0.032 | −0.019 → −0.004 |
| 22 | EnsembleTopK | **0.94 → 0.21** | **0.051 → 0.068** | −0.018 → −0.014 |
| 22 | HAR-Shrink2Group | 0.86 → 0.69 | 0.073 → 0.034 | −0.017 → −0.009 |

**Counter-prior result.** The plan expected management to be the forecast's biggest 30-DTE tail win.
It is the opposite: at h=22 the daily re-gating **churns the book** (125 → 254 roll dates), gives back
most of the return (EnsembleTopK Sharpe 0.94 → 0.21, AnnRet 0.047 → 0.006) and *worsens* maxDD and
worst-20 — only CVaR95 nudges. Management's large, real benefit is at **7–14 DTE**, where there's
more path to exit early — but **it helps IV-only just as much** (IV-only @ h=5 managed is the **only
DSR≥0.95 cell in the entire grid**, 0.957). So management at short DTE is a *generic short-vol
discipline*, not a forecast-specific edge, and at 30 DTE this Stage-1 variance-accrual mark makes it
counterproductive. **A9 managed is a No-Go at h=22.** (Stage-2 ORATS, with true option marks, may
revisit short-DTE management — but on its own merits, not as the forecast's tail story.)

---

## 4. A4 — pooled sleeve vs clean-core on `hard_cases` (UVXY, MSOS, IBIT, USO, KRE)

Hard-case-only book (one-per-group over the thin names), baseline:

| h | Model | Role | Sharpe | CVaR95 | maxDD | PnL |
|---|---|---|---|---|---|---|
| 22 | **HAR-Shrink2Group** | sleeve | **0.914** | −0.016 | 0.058 | 0.456 |
| 22 | EnsembleTopK | core | 0.898 | −0.020 | 0.051 | 0.360 |
| 22 | HAR-X | core | 0.811 | −0.017 | 0.044 | 0.293 |
| 22 | PanelHAR-FE | sleeve | 0.601 | −0.036 | 0.143 | 0.327 |
| 10 | **HAR-Shrink2Group** | sleeve | **0.711** | −0.022 | 0.145 | 0.372 |
| 10 | EnsembleTopK | core | 0.425 | −0.026 | 0.150 | 0.221 |
| 5 | **EnsembleTopK** | core | **1.279** | −0.009 | 0.117 | 0.520 |
| 5 | HAR-Shrink2Group | sleeve | 0.738 | −0.011 | 0.116 | 0.297 |

**The iter-2 pooling promotion pays economically on the thin names at 14–30 DTE:** `HAR-Shrink2Group`
is the best hard-case book at h=10 (0.71 vs core 0.43) and edges the clean-core path at h=22 (0.914
vs 0.898) with a comparable tail. At 7 DTE the clean-core EnsembleTopK is better even on hard names.
`PanelHAR-FE` — the *aggressive* pooling bound — has the **worst tail** of the four everywhere
(CVaR95 −0.036, maxDD 0.143 at h=22), confirming the plan's caution: keep it as the sleeve's bound,
not a standalone line. **Use the sleeve (Shrink2Group) for hard_cases at h≥10; clean-core elsewhere.**

---

## 5. Portfolio stress (§6) — the worst-20 days and stress-vs-calm correlation (h=22 book)

| Model | worst-20-day book P&L | mean cross-group corr (stress) | … (calm) |
|---|---|---|---|
| **EnsembleTopK** | **−0.169** | **0.049** | 0.135 |
| HAR-X | −0.119 | 0.120 | 0.170 |
| HAR-Shrink2Group | −0.143 | 0.162 | 0.169 |
| PanelHAR-FE | −0.227 | 0.048 | 0.150 |
| *IV-only* | **−0.685** | **0.464** | 0.225 |

This is the diversification-collapse test, and it is the most damning panel for IV-only. In its worst
20 days the IV-only book loses **−0.685** (4× the forecast books) and its cross-group correlation
**doubles into the shock** (0.22 calm → 0.46 stress) — the classic short-vol failure where the
15-group book behaves like one position exactly when it must not. The gated forecast books do the
opposite: EnsembleTopK's stress correlation *falls* to 0.05 (the gate sits out the names lighting up
together), so the book stays diversified through the spike. The regime gate is buying genuine
tail-state decorrelation, not just lower average variance.

---

## 6. Cost sensitivity (§4.3)

Stage-1 cost is a flat per-group bps haircut (default 5 bps; wider for thin names). Net annualised
return is essentially flat across the full sweep (0 → 20 bps) for every promoted cell — e.g.
EnsembleTopK@22 0.0474 → 0.0443; Shrink2Group@22 0.0555 → 0.0528. **Break-even costs are 287–413 bps**
for the h=22 passes, i.e. ~60–80× the conservative 5-bps point and ~15–20× the 20-bps stress point.
Criterion 4 (survives conservative cost) is met with enormous margin — *in the Stage-1 abstraction.*
Caveat: the variance-proxy charges cost as a fraction of premium and omits real bid/ask, slippage and
short-gamma roll cost; the genuine cost test is Stage-2 ORATS. The Stage-1 read is only that cost is
not what kills the edge.

---

## 7. Per-model sections (signal use · universe/role · verdict)

### EnsembleTopK — clean-core **primary**
- **Signals.** `vrp_score = iv2 − rv_hat` sets sell-vol candidacy; `sigma` drives the dispersion gate
  (`sigma/rv_hat` > trailing-80th → avoid) and the inverse-risk size `∝ vrp_score/σ²`; quantiles feed
  only the A5 variant. At 30 DTE the mean (`rv_hat`) carries no edge over IV² — the **second moment is
  the value source**, and the results bear this out: A2 (gate) and A3 (σ-size) are what move CVaR/maxDD.
- **Universe/role.** Clean-core primary; results confirm it — best DSR and smallest tail at h=22, best
  hard-case book at h=5, ≥ HAR-X everywhere (A6).
- **Verdict.** **PASS @ h=22** (Stage-2 primary). Beats IV on relative DSR (0.68 vs 0.28), CVaR/maxDD
  far better, gate marginal significant (p=0.026), beats both controls, break-even ~312 bps.
  *Qualified:* absolute DSR 0.68 < 0.95. **No-Go @ h=5, h=10.** Do **not** run it managed (A9).

### HAR-X — clean-core **fallback**
- **Signals.** Same map; the transparent one-regressor-family baseline. σ-sizing is its strongest
  contributor (A3 ΔSharpe p=0.003 @22).
- **Role.** The graceful-degrade fallback; travels well to hard names (2nd-best hard-case book @22).
- **Verdict.** **PASS @ h=22** (Stage-2 fallback): DSR 0.57 > IV, CVaR −0.016, maxDD 0.053, σ-sizing
  significant, break-even ~336 bps. *Qualified* on absolute DSR. **No-Go @ h=5, h=10.**

### HAR-Shrink2Group — short-history **sleeve default**
- **Signals.** Same map; empirical-Bayes shrink-to-pool tightens hard-case σ, which directly improves
  the size/gate on thin names. **The only model whose A1 beats IV-only on mean** (boot p=0.035 @22,
  p=0.004 @10), not just on tail.
- **Role.** Sleeve for `hard_cases`; best hard-case book at h=10 and h=22 (A4).
- **Verdict.** **PASS @ h=22 and @ h=10** (Stage-2 sleeve). The only cell that clears IV-only at 14 DTE.
  σ-sizing significant (p=0.008). *Qualified* on absolute DSR (0.58 @22, 0.16 @10).

### PanelHAR-FE — short-history **sleeve bound**
- **Signals.** Full pooling + ticker FE; the aggressive pooling end. A3 sizing significant (p=0.049),
  A1 beats IV on mean (p=0.006 @22).
- **Role/verdict.** **Marginal PASS @ h=22 only** (DSR 0.333, barely > IV 0.277) but the **worst tail**
  of the four (CVaR95 −0.029, maxDD 0.152) and worst hard-case tail. Promote **only as the sleeve's
  bound**, dominated by Shrink2Group; do not run as a standalone line. **No-Go @ h=5, h=10.**

### HAR-ENet — short-horizon §5 candidate (h=5, 10 only)
- **Signals.** Shrinkage head added specifically to chase the short-DTE directional edge.
- **Verdict.** **No-Go everywhere.** DSR 0.016 at both h=5 and h=10; never beats IV-only on any axis;
  worst-or-near-worst tail. The hypothesised 7–14-DTE directional alpha did not appear in P&L. A clean
  negative — it stays a valid forecasting research-candidate, just not promoted for trading.

### IV-only — benchmark
- **Signals.** `vrp = iv2 − trailing_RV`, flat size, no gate. **The better book at 7 DTE** (highest DSR,
  Sharpe, return there) and, **managed, the only DSR≥0.95 cell in the grid** — underlining that
  short-DTE management value is structural, not forecast-driven. At 30 DTE it is the worst book: it
  out-earns the forecasts but with 3–4× the tail and the diversification-collapse signature in §5.

---

## 8. Go / No-Go matrix (§7.2)

Criteria, vs IV-only on the model's intended universe: **(1)** beats IV-only on deflated Sharpe;
**(2)** not-worse CVaR95 *and* maxDD; **(3)** A2(gate) and/or A3(size) marginal statistically positive
*and* edge beats A7 controls; **(4)** survives conservative cost. (`verdicts.parquet`.)

| Model | h | (1) DSR>IV | (2) tail | (3) attrib | (4) cost | **Verdict** |
|---|---|:--:|:--:|:--:|:--:|---|
| **EnsembleTopK** | 22 | ✅ 0.68>0.28 | ✅ | ✅ gate p=.026 | ✅ 312bps | **PASS** (qual.) |
| **HAR-Shrink2Group** | 22 | ✅ 0.58 | ✅ | ✅ size p=.008 | ✅ 413bps | **PASS** (qual.) |
| **HAR-X** | 22 | ✅ 0.57 | ✅ | ✅ size p=.003 | ✅ 336bps | **PASS** (qual.) |
| PanelHAR-FE | 22 | ✅ 0.33>0.28 | ✅ | ✅ size p=.049 | ✅ 287bps | **PASS** (marginal/bound) |
| **HAR-Shrink2Group** | 10 | ✅ 0.16>0.13 | ✅ | ✅ gate p=.012 | ✅ 289bps | **PASS** (qual.) |
| EnsembleTopK | 10 | ❌ 0.06<0.13 | ✅ | ❌ | ✅ | No-Go |
| HAR-X / HAR-ENet / PanelHAR-FE | 10 | ❌ | – | – | – | No-Go |
| *all forecasters* | 5 | ❌ < IV 0.37 | – | – | – | **No-Go** |
| HAR-ENet | 5,10 | ❌ | – | – | – | **No-Go** |

**Qualifier carried on every PASS:** criterion 1 is met *relative to IV-only*; no cell meets the
**absolute** DSR≥0.95 bar (best 0.68), a power limit on 125 monthly h=22 observations. Promotion is
driven by criterion 2 (the dominant criterion for a short-gamma book), which is met decisively, plus
significant gate/sizing attribution (criterion 3).

**Stage-2 ORATS run list:** `EnsembleTopK@22` (primary), `HAR-X@22` (fallback),
`HAR-Shrink2Group@22+@10` (sleeve), `PanelHAR-FE@22` (sleeve bound, watch).
Run **hold-to-expiry** (A9 managed is not promoted). Stage-2's exact EOD option marks will (a) put a
real number on the now-100×-margin Stage-1 break-even and (b) re-test short-DTE management on true
greeks rather than the variance-accrual proxy.

---

## 9. What this study establishes

1. **The §5 caveat holds and is now economically quantified.** No 30-DTE mean alpha over IV²; the
   forecast's entire economic contribution is **left-tail control** — CVaR95 −0.018 vs IV −0.064,
   maxDD 0.051 vs 0.203, worst-20 −0.029 vs −0.170 (EnsembleTopK).
2. **It traces to a signal, not carry/luck.** The regime gate (A2) cuts 30-DTE drawdown ~8× and
   *decorrelates the book in stress* (corr 0.46→0.05); σ-sizing (A3) halves CVaR with significant
   marginal Sharpe; both crush the A7 controls.
3. **Two priors were wrong, and that is the finding.** (a) No short-horizon directional alpha — at
   7 DTE IV-only is the better book and the gate over-throttles. (b) Management is *not* the 30-DTE
   tail win; it churns there and its short-DTE benefit is model-agnostic (helps IV-only most).
4. **The pooling promotion pays on the thin names** (Shrink2Group best hard-case book at 14–30 DTE),
   and PanelHAR-FE is correctly the aggressive bound (worst tail).
5. **Honest limit:** no strategy clears the absolute deflated-Sharpe bar after 104-trial deflation.
   The promotions are conditional, tail-driven, and demand Stage-2 confirmation under real option
   marks — a clean, decision-useful result, not a manufactured edge.

*All numbers: frozen 2018→2026 OOS folds, common support, no retraining. Trial count for DSR
deflation N=104 (Var(SR)=0.00660, SR₀≈0.206 per-obs). Artifacts: `scorecard.parquet`,
`attribution.parquet`, `verdicts.parquet`, `_scoring_dump.json`.*
