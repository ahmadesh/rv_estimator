# Modern-HAR Extensions — Iteration 2 Research Plan

**Status:** design spec (no code yet). Created 2026-06-03. A targeted second wave of
candidate models for the forward-RV forecasting harness
([`rv_forecasting_eval_plan.md`](../execution/rv_forecasting_eval_plan.md)),
motivated by the iteration-1 results in
[`execution/reports/FINAL_MODEL_COMPARISON_REPORT.md`](../../execution/reports/FINAL_MODEL_COMPARISON_REPORT.md).

**Reuses, does not replace, the existing harness.** Every model below plugs into the
same `Model` contract (`rv_eval/model_contract.py`), the same walk-forward protocol
(purged+embargoed, monthly refit, OOS ≥ 2018), and the same Tier-1/§5/§6/Tier-2
evaluator. New features are added to `rv_eval/features.py`; new models are thin
subclasses in `candidate_models/`. No change to the measurement layer or the output
contract (`rv_hat · sigma · q05…q95`).

---

## 0. What iteration-1 actually told us (the design brief)

Read straight off the comparison report:

1. **Point accuracy at the primary horizon is saturated.** At h=22 the MCS cannot
   separate ten of thirteen models; DM vs HAR is insignificant for the whole HAR
   family. Plain HAR is in the tie-set. **Chasing raw h=22 QLIKE is low-EV.**
2. **The economically decisive axis is weak for everyone.** The §5 IV-incremental
   skill (does `sign(IV²−R̂V)` predict `IV²−RV_realized`?) decays to sign-accuracy
   ≈0.51–0.52 and QLIKE-gain-vs-IV² ≈0 at h=22, with R²≈0.01. The information that
   IV-augmented models add over IV² is concentrated at **h=1** (R²≈0.10, sign-acc 0.70)
   and **largely gone by 30 DTE** — exactly the horizon the book trades.
3. **Calibration is the lever that still has room.** The HAR family sits within ±0.03
   of the 0.90 coverage target on clean_core but is mildly tight on hard_cases; all
   models carry a mild **negative** unconditional bias at h=22 (−0.10 to −0.17) — the
   dangerous direction for short puts. The downstream value, per the report's own
   synthesis, "is most likely to show up through the regime gate and sizing
   (calibration), not a large directional RV-vs-IV alpha."
4. **Complexity lost, decisively.** R-GARCH/PDV are numerically broken; LSTM/XGBoost
   cost 10²–10³× more and the MCS can't tell them from free HAR. The production path is
   linear and runs in seconds.
5. **Verdict labels are fragile.** HARQ vs HAR-RS-IV-Q flip research-candidate/rejected
   across universes on ~0.01 QLIKE wobble inside the MCS tie-set. Any new "win" must
   clear that noise floor on a **different axis** to be real.

### Design decisions for this wave (from the scoping round, 2026-06-03)

- **Primary objective:** maximize **§5 incremental skill and calibration**, not raw
  h=22 QLIKE. A candidate that flattens the §5 decay or tightens conditional coverage
  is a win *even if h=22 QLIKE is unchanged*. QLIKE is a guardrail (must not regress),
  not the target.
- **Complexity ceiling:** **linear + light state-space.** New linear HAR feature
  blocks, shrinkage/combination, and panel pooling are first-class. A small number of
  light state-space / regime models (HAR-GARCH error variance, threshold/Markov-switch
  HAR) are allowed — minutes to fit, not the multi-hour PDV/LSTM regime. No iterative
  deep optimizers.
- **Data:** already-ingested columns first; **cheap free public additions allowed**
  where motivated (cross-asset, macro EPU, event flags). The 2024 shrinkage-HAR wins
  come precisely from a *large* exogenous predictor set, so this is on-thesis.
- **Pooling:** **add a cross-ticker pooling/shrinkage track.** Per-(ticker,h) OLS with
  14+ regressors is noisy on limited history; pooling is the textbook fix and directly
  helps the short-history hard cases (IBIT/MSOS).
- **History depth:** option-chain IV and minute bars exist back to **2007-01-03**
  (verified: `iv_30/60/90d`, `ext_vol` non-null from 2007; RV/range/returns from 2003),
  but OOS only starts 2018 and several models train on a short window. Extending the
  training/validation depth to 2007 (keeping OOS unchanged) is a near-free way to
  stabilise the shrinkage, pooling, and regime models. Treated as a cross-cutting
  enabler (§6), not a model.

---

## 1. Untapped signal already in `inputs.parquet`

Columns the measurement/IV layer already produces but **no current model uses**, with
the hypothesis each one tests. (Verified present and populated; IV-block from 2007,
the rest from 2003.)

| Column(s) | Currently used? | What it adds | Primary axis it targets |
|---|---|---|---|
| `ret_cc`, `overnight_ret` | no (signed) | **Leverage effect** — signed past returns; negative returns raise future vol more than positive. HAR-RS uses *semivariance* but never the raw signed return. | §5 / §6 (downside) |
| `rs_plus`, `rs_minus` | only as 5d means | **Signed jump** `SJ = RS⁺−RS⁻` and `|SJ|`; Patton-Sheppard find SJ more informative than the two halves separately. | §5 / §6 |
| `iv_60d`, `iv_90d` | **no** | Full IV **term-structure level + curvature** (`iv_30 − 2·iv_60 + iv_90`), not just the 30/90 slope already used. The convexity of the IV curve prices the path of expected vol — directly relevant to a 22-day forecast. | §5 |
| `iv2` (in targets) − `rv` | no | **Lagged realized VRP** and its momentum/mean-reversion — *the §5 quantity itself* as a predictor. | §5 (head-on) |
| `vvix` | only as a level in IV block | **Vol-of-vol** dynamics → time-varying forecast *uncertainty*, the calibration lever. | calibration / coverage |
| `ext_vol` | no | ORATS extrapolated/forward vol estimate — a second IV view. | §5 |
| `parkinson`, `gk`, `rs` (range) | no | Range-based daily variance (Parkinson/Garman-Klass/Rogers-Satchell) — robust, includes the open→close path; a cheap noise-reduced RV proxy and a cross-check that downweights microstructure. | accuracy / robustness |
| `rv_overnight`, `rv_intraday` | no (as features) | Overnight vs intraday RV **share** — overnight gap risk is a distinct driver and its share shifts with regime. (The *forecast* split is a deferred v2 output; using the *past* split as a feature is in-scope now.) | §6 (regime) |
| `volume`, `transactions` | no | Activity/liquidity surprise — volume shocks lead vol. | accuracy |
| `rq` | only `sqrt_rq` (HARQ) | **Vol-of-vol of the estimator** → drives a heteroskedastic predictive `sigma`. | calibration |

Most of the new value is unlocked by **using these as either (a) new linear regressors
or (b) drivers of a time-varying predictive variance** — both cheap.

---

## 2. The model series — five tracks

Organised by mechanism, each tagged with the axis it attacks, its cost, and the exact
code touch-point. Models are named so they slot into `candidate_models/` alongside the
existing cards.

### Track A — New linear feature blocks (per-ticker OLS, seconds)

Extends the `_LinearLogHAR` family with the §1 signals. Each is one new `needs` list +
a few columns in `features.py`. Ablate **each block in isolation** against HAR and the
incumbent HAR-X / HAR-RS-IV-Q so we learn *which signal* carries, not just "more is
better."

| Model | Adds over HAR-RS-IV-Q | Hypothesis (axis) | Refs |
|---|---|---|---|
| **A1 · LHAR** (leverage) | `lev_d/w/m = rolling_mean(min(ret_cc,0))` over 1/5/22d | Signed downside returns predict vol beyond semivariance; the classic asymmetry HAR-RS only half-captures. (§5/§6) | Corsi-Renò 2012 |
| **A2 · HAR-SJ** (signed jump) | `sj_5d = rs⁺−rs⁻`, `abs_sj_5d` replacing/augmenting `jump_5d` | SJ is the more informative jump decomposition; bad jumps persist, good ones don't. (§5) | Patton-Sheppard 2015 |
| **A3 · HAR-IVTS** (IV term structure + VRP state) | `iv_curv = iv30−2·iv60+iv90`, `iv_ts_30_90`, **`vrp_lag = iv2_{t}−rv_d`**, `vrp_mom` (Δ over 5d), `vix3m_vix_sign` | Models the **VRP directly**: when the curve is steep/backwardated and realized VRP is mean-reverting, the (IV²−RV) spread is predictable — *this is the §5 signal by construction*. (§5 head-on) | Bali et al.; VIX-term-structure→RV (Sci.Dir. S1057521922001600) |
| **A4 · HAR-Range** | `log` of Parkinson/GK/RS range vars as extra HAR lags | Range vol is a lower-noise variance proxy; helps where 5-min RV is thin. (accuracy/robustness) | Yang-Zhang; Patton range RV |
| **A5 · HAR-Act** | `log_vol_surprise`, `log_txn_surprise` (vs 22d mean), `overnight_share` | Activity/overnight-share regime conditioning. (§6) | Bollerslev "risk everywhere" |
| **A6 · HAR-MAX** | union of A1–A5 + existing RS/IV/Q blocks (~25 regressors) | The kitchen sink — **deliberately over-parameterised**; its job is to be the input to Track B shrinkage, not to be fit by OLS. | — |

> A6 by OLS will overfit at h=22 (the report's exact failure mode). That is the point:
> it sets up the shrinkage comparison in Track B. Report A6-OLS as the "what not to do"
> baseline.

### Track B — Shrinkage & combination (the overfit fix; this is the cited 2024 win)

The strongest evidence-backed lever: shrinkage-HAR with a large predictor set beats
plain HAR out of sample (Sci.Dir. S105905602400306X, 2024). Per-(ticker,h), **penalty
chosen by leakage-safe inner CV on the training slice only** (reuse the existing
tune-once-then-freeze discipline, §1.4 of the report).

| Model | What it is | Why (axis) |
|---|---|---|
| **B1 · HAR-Ridge / HAR-ENet** | Ridge / Elastic-Net OLS on the A6 feature matrix, per (ticker,h). Standardise features; CV `λ` (and `l1_ratio`) on inner train tail. | Controls estimation-error variance — the single most likely *real* QLIKE+calibration gain at h=22 with 25 regressors on limited history. (accuracy + §5) |
| **B2 · HAR-CSR** (complete-subset regression) | Average forecasts over all k-feature OLS subsets (Elliott-Gargano-Timmermann). Cheap closed-form, no penalty tuning. | Robust forecast combination; empirically strong for RV (HAR-CSR/CSQR literature, Sci.Dir. S0957417421008356). (accuracy + calibration) |
| **B3 · EnsembleTopK-v2** | Replace equal-weight with **discounted-MSE / Bates-Granger** and a **regime-conditional** weighting (weights vary by IV-percentile bucket); include the new A/B/D winners in the pool. | Current ensemble is equal-weight; regime-conditional weights target §6. Gains over equal-weight are usually small — keep only if it clears the noise floor. | 

### Track C — Cross-ticker pooling / panel (explicitly requested)

Attacks overfit *and* the short-history hard cases by sharing strength across tickers.

| Model | What it is | Why (axis) |
|---|---|---|
| **C1 · PanelHAR-FE** | Single pooled OLS per horizon across all clean-core tickers with **group + ticker fixed effects** (intercept dummies), shared slopes. | ~10× the data per coefficient → far less estimation noise; a natural prior for IBIT/MSOS where per-ticker fits are starved. (accuracy/calibration) |
| **C2 · HAR-Shrink2Group** | Per-ticker coefficients **shrunk toward the group/pooled mean** (ridge-to-pooled / empirical-Bayes James-Stein). `β_ticker = (1−w)·β_OLS + w·β_pooled`, `w` by CV. | Best of both: ticker-specific where data supports it, pooled where it doesn't. The principled middle between per-ticker OLS and full pooling. | 
| **C3 · GlobalVolFactor-HAR** | Add a pooled cross-sectional **market-RV factor** (1st PC of clean-core RV, or scaled SPX RV) as a regressor on top of HAR. | Common vol component is a known driver; cheap systematic-regime feature distinct from VIX. (§6) |

### Track D — Calibration & distribution (the primary objective)

The harness wraps every point forecast in a **lognormal with a single constant
log-residual `sigma`**. That is the calibration bottleneck the report flags (§3.4) — a
great `rv_hat` is useless downstream if `sigma` is mis-scaled. These make the
*distribution* the modelled object.

| Model | What it is | Why (axis) |
|---|---|---|
| **D1 · Hetero-sigma wrapper** | Drop-in replacement for the constant log-sd: `sigma_t = g(sqrt_rq, vix, vvix, regime)` fit on training residuals (log-residual variance regressed on these). Applies to **any** existing HAR model. | Time-varying forecast uncertainty → coverage that holds *conditional on regime*, fixing the hard-case tightness and the §6 trap. Cheapest, highest-leverage calibration fix. (calibration — primary) |
| **D2 · HAR-GARCH** | GARCH(1,1) (or GJR for leverage) on the HAR log-residuals so the predictive error variance is conditionally heteroskedastic. Light state-space. | Same goal as D1, generative form; gives honest fan-out after shocks. (calibration) |
| **D3 · HAR-QR** (quantile regression) | Fit `q05…q95` **directly** by quantile regression on the A-track features (optionally complete-subset quantile, HAR-CSQR), instead of inverting a lognormal. | Optimises pinball/coverage — the actual downstream metric — and frees the tails from the lognormal shape assumption. (calibration + tails) |
| **D4 · VRP-Spread head** | Model the spread `s_t = IV²−RV` directly (HAR-style mean-reversion on `s` + curve/regime features), emit `R̂V = IV² − ŝ` **and a calibrated sign-confidence** for `sign(IV²−R̂V)`. | Optimises the §5 diagnostic *as the loss*, rather than hoping it falls out of an RV-level fit. The most direct attack on the study's key weakness. (§5 — head-on) |

### Track E — Regime-switching / threshold (light state-space)

The §6 conditional-bias and the §5 short-vs-long decay both say "the relationship is
regime-dependent." Let coefficients change with regime.

| Model | What it is | Why (axis) |
|---|---|---|
| **E1 · Threshold-HAR (TVHAR)** | Two/three coefficient regimes keyed on an **observable** threshold: VIX percentile, or VIX-term-structure **sign** (contango vs backwardation), or the existing `post_shock` flag. Hard split, per-regime OLS. | Cheap, transparent regime conditioning; directly targets post-shock bias (§6) and the contango/backwardation asymmetry. | 
| **E2 · STAR-HAR (smooth transition / interaction)** | Continuous interaction: HAR features × VIX-percentile (and × term-structure sign). One OLS, no MLE. | A cheaper, smoother E1 — captures regime-varying slopes without discrete-split noise. (§6/§5) |
| **E3 · MS-HAR** (Markov-switching, 2-state) | Latent 2-state HAR via EM; regime-conditional mean **and** variance → a genuinely bimodal predictive distribution. **Highest cost in this wave**; gate it hard against E1/E2 (must beat the cheap regime models, not just HAR). | Calm/stress regimes with their own dynamics; richest §6 story. (§6/calibration) | 

---

## 3. New data — **INGESTED 2026-06-03** (cheap, on-disk, no network)

The inventory found that the proposed regime series were all derivable from data already
on Ex-Disk — no external download needed. Six systematic (date-keyed, broadcast-to-all-
tickers, point-in-time) columns were added to `inputs.parquet`. Source code:
`rv_eval/setup/cross_asset.py` (cross-asset proxies) and the extended
`iv_features.systematic_features()` (VIX9D); back-filled onto the existing panel by
`rv_eval/setup/_add_systematic_cols.py`; `prepare_panel.INPUT_COLS` updated so future
rebuilds include them natively.

| Column | Definition | On-disk source | Feeds | Rationale |
|---|---|---|---|---|
| `vix9d` | SPX 9-day ATM IV (interpolated, like vix/vix3m) | SPX ORATS chain | A3, E1/E2 | Short end of the VIX term structure → sharper contango/backwardation regime signal. |
| `vix9d_slope` | `vix9d − vix` (9d−30d) | derived | A3, E | Front-end term slope; **>0 = backwardation/stress** (0.14 mean in 2020-03). |
| `credit_spread` | `log(LQD/HYG)` level | Polygon daily | A5, C3, E | IG-vs-HY price level; **rises in credit stress** (0.47 in COVID vs ~0.30 calm). |
| `credit_mom` | `r20(HYG) − r20(LQD)` | Polygon daily | A5, C3, E | HY-minus-IG 20d return; **<0 in stress** (−0.08 in COVID). |
| `usd_mom` | `r20(UUP)` | Polygon daily | C3, E | Broad-USD 20d return; risk-off proxy (esp. EEM/GLD/USO). |
| `rates_mom` | `r20(TLT) − r20(SHY)` | Polygon daily | C3, E | Long-minus-short duration 20d return; curve/rates regime. |

Coverage: `vix9d` matches the existing `vix` exactly (0.849, both from the SPX chain
back to 2007); `credit_spread` from HYG's real inception 2007-04-11 (spurious pre-2007
HYG lake rows are guarded out). Verified across 2018/2020/2024 regimes — signs behave as
expected. Backup at `inputs.parquet.bak`.

> **Not ingested (deferred):** the **EPU index** and **FOMC/event flags** are the only
> genuinely-external items (no on-disk proxy) — left out per the "on-disk only" scope.
> Cheap to add later from a FRED CSV (`USEPUINDXD`) and the Fed calendar if a model wants
> them.

> **Discipline:** these enter the **shrinkage/pooling** models (B/C) where the penalty
> can discard them, or as **regime thresholds** (E) — *not* as free OLS regressors in a
> per-ticker fit, to avoid re-creating the A6 overfit. Each must survive the §7 ablation
> (lower QLIKE *or* improve §5/coverage) or it is dropped.

Plus the cross-cutting **history extension to 2007** (§6): no new ingestion, just widen
the train/validation window the existing models see.

---

## 4. Evaluation — how each candidate is judged (unchanged harness, re-weighted gate)

Same evaluator, same protocol. The **gate is re-prioritised** to match the objective:

1. **Guardrail (must not regress):** h=22 QLIKE within the incumbent MCS tie-set on
   clean_core. A candidate that *worsens* h=22 QLIKE materially is rejected regardless
   of other gains.
2. **Primary acceptance (must improve ≥1):**
   - **§5 incremental skill** — higher `sign_acc` and/or `qlike_gain_vs_iv²` at **h=22**
     (the decay is the target). Also report the h=1→h=22 decay curve; flattening it is
     the headline win.
   - **Calibration** — `cov90`/`cov50` closer to target *conditional on regime*
     (IV-percentile bucket, post-shock), and lower pinball loss. Especially on
     hard_cases where the incumbents run tight.
3. **Conditional bias (§6):** no new `trap_flag`; shrink the −0.10/−0.17 unconditional
   negative bias toward zero (the short-put-dangerous direction).
4. **Finalists only (Tier-2):** DM (vs HAR *and* vs HAR-X/EnsembleTopK) and MCS — but,
   per the report's caveat, as *confirmation* of a Tier-1/§5 signal, never the driver.

**Ablation table (extends report §7) — every block earns its place OOS:**

| Added complexity | Must out-forecast | Kept only if it |
|---|---|---|
| A1–A5 individual blocks | HAR-RS-IV-Q | lowers QLIKE **or** improves §5/coverage |
| A6 kitchen sink (OLS) | — | (reference; expected to overfit — illustrative) |
| B1/B2 shrinkage | A6-OLS **and** HAR-RS-IV-Q | beats both at h=22 without breaking coverage |
| C1/C2 pooling | per-ticker OLS counterpart | cuts hard-case bias/variance without hurting clean core |
| D1/D2 hetero-sigma | constant-sigma version of the *same* mean model | improves conditional coverage + pinball |
| D3 quantile head | D1 lognormal wrapper | improves pinball/coverage at the tails |
| D4 VRP head | HAR-X §5 numbers | raises h=22 sign_acc / gain-vs-IV² |
| E1–E3 regime | unconditional counterpart | reduces §6 conditional bias |
| New exogenous series | model without it | survives in the shrinkage/penalised fit |

Crucially: because §3.7 of the report showed labels flip on ~0.01 QLIKE noise, **a
candidate is only "research candidate" if its win is on the §5/calibration axis or is
DM/MCS-robust — not on a sub-noise QLIKE wobble.**

---

## 5. Prioritised build order (highest expected value first)

Three waves, front-loaded with the cheapest, highest-EV work. Each wave is gated before
the next starts.

**Wave 1 — cheap linear, biggest expected payoff (days):**
1. **D1 Hetero-sigma wrapper** — applies to existing HAR-X/EnsembleTopK immediately;
   pure calibration win, the primary objective, near-zero cost. *Do this first.*
2. **A1 LHAR · A2 HAR-SJ · A3 HAR-IVTS** — the three feature blocks most likely to move
   §5 (leverage, signed jump, VRP/term-structure state).
3. **B1 HAR-Ridge/ENet** on A6 — the evidence-backed shrinkage win; resolves the
   per-ticker overfit.
4. **D4 VRP-Spread head** — direct attack on the §5 decay.

**Wave 2 — pooling, combination, quantiles (1–2 weeks):**
5. **C1 PanelHAR-FE · C2 HAR-Shrink2Group** — the requested pooling track; biggest help
   on hard cases.
6. **D3 HAR-QR** — direct quantile calibration.
7. **B2 HAR-CSR · B3 EnsembleTopK-v2** — combination upgrades over equal-weight.
8. **A4/A5 + new exogenous series (§3)** folded into B1/C2.

**Wave 3 — light state-space, optional depth (as warranted):**
9. **E1 Threshold-HAR · E2 STAR-HAR** — cheap regime conditioning for §6.
10. **D2 HAR-GARCH · E3 MS-HAR** — only if the cheap regime/hetero-sigma models show
    regime structure is being left on the table. Gate hard against Wave-1/2 winners.
11. **History extension to 2007** (§6) — rerun the shrinkage/pooling/regime models with
    the deeper train window; cheap robustness check.

**If only five models get built:** D1, A3, B1, D4, C2 — they cover all three target
axes (calibration, §5, overfit/pooling) at near-zero compute.

---

## 6. Cross-cutting enabler — extend training depth to 2007

OOS still starts 2018 (unchanged, so all reported numbers stay comparable), but the
**train/validation window currently wastes 2007–2017** for several models. IV is
populated from 2007-01-03; RV/range/returns from 2003. Widening the expanding-window
start gives:
- the **shrinkage** models (B) more observations to estimate 25 coefficients;
- the **pooling** models (C) a longer cross-section;
- the **regime** models (E) more than one stress episode (2008 GFC, 2011 EU, 2015,
  2018) *inside the training set* — essential for MS-HAR/threshold estimation;
- the **hetero-sigma / quantile** heads (D) more tail observations to calibrate against.

**Correction (verified 2026-06-03):** this is **largely already in effect**, not a pending
change. `config.TRAIN_WINDOW="expanding"` with fold `lo=0` means every model already trains
on *all* panel history from the earliest date (RV from 2003, IV from 2007); `MIN_TRAIN_DAYS`
only gates the first OOS fold (still 2018). So the IV-dependent models already see 2007→ —
**no code change is needed** to "extend depth." The genuine knobs are: (a) switch to
`rolling` to *shorten* history for a sensitivity test, or (b) confirm the IV/range columns
are clean pre-2018 (the HYG pre-inception guard in `cross_asset.py` is one such fix). Treat
§6 as a *robustness check already satisfied* rather than a build step. See
`execution_plan/ITER2_MODEL_CATALOG.md` §4.6.

---

## 7. Critical assessment (honest priors)

- **Most of these will land inside the noise floor at h=22, as in iteration 1.** That is
  expected and *not* the bar this time — the bar is §5/calibration. Be ruthless: if a
  model only wobbles QLIKE by ≤0.01 and adds nothing to §5/coverage, it is rejected.
- **The highest-confidence wins are the least glamorous:** D1 (hetero-sigma) and B1
  (shrinkage). Calibration and regularisation are where the report says room remains.
- **D4/A3 (direct VRP modelling) is the highest-variance bet** — it attacks the study's
  core weakness head-on, but the §5 decay may be *irreducible* (IV² already prices most
  of the predictable VRP at 30 DTE). If D4 can't beat HAR-X's §5 numbers, that is itself
  a valuable, publishable-internally negative result: it bounds the achievable edge.
- **Pooling has a known failure mode:** clean-core tickers are heterogeneous (TLT vs
  XLE vs GLD), so full pooling (C1) may bias slopes. C2 (shrink-to-group) is the safer
  bet; C1 is mainly there as the pooling bound.
- **MS-HAR (E3) is the one cost risk** — gate it hard; it must beat the cheap threshold
  models, or it is a PDV-style cautionary tale.
- **Watch leakage on the new heads:** D4 uses `iv2` (a target-adjacent quantity) as a
  feature — it is point-in-time (known at t) so legitimate, but the evaluator's §5
  diagnostic must compare against *next-period* realized spread; double-check the
  embargo on the VRP-lag feature.

---

## 8. Relationship to existing docs

- **Operational run plan:** the per-model build spec + swarm to actually run these is
  `execution_plan/ITER2_MODEL_CATALOG.md` (catalog of models 13–32, reuse patterns, and the
  §4 reuse-discrepancy report), driven by `ITER2_ORCHESTRATOR_PROMPT.md` +
  `ITER2_SWARM_KICKOFF.md`, ledger `iter2_swarm_progress.md`. **No edits to `rv_eval/`** —
  one shared `candidate_models/_base_v2.py` plus one file per model.
- Operationalises the "build later" list in
  [`rv_forecasting_methods.md`](rv_forecasting_methods.md) §3.5/§6 (rough/path-dependent,
  cross-ticker factor) and the §7 ablation discipline of
  [`rv_forecasting_eval_plan.md`](../execution/rv_forecasting_eval_plan.md).
- Consumes the same universe/protocol from `rv_eval/config.py` and the same evaluator.
- Feeds the same downstream gate: a Wave winner that clears §5/calibration becomes a
  *Research candidate* and is handed to
  [`rv_trading_eval_plan.md`](../execution/rv_trading_eval_plan.md) for Production
  candidacy.

### Key references (2012–2025)

- Corsi & Renò (2012) — HAR with leverage (LHAR).
- Patton & Sheppard (2015) — semivariance / signed-jump HAR (SHAR).
- Bollerslev, Patton, Quaedvlieg (2016) — HARQ; HARQ-F full quarticity.
- Elliott, Gargano & Timmermann — complete-subset regression; HAR-CSR/CSQR
  (Expert Sys. Appl. S0957417421008356).
- Shrinkage HAR with large cross-market predictor set (J. Bank. Finance / Sci.Dir.
  S105905602400306X, 2024).
- VIX term structure → realized (semi)variance (Sci.Dir. S1057521922001600).
- Regime-switching HAR for S&P 500 vol (arXiv 2510.03236, 2025).
- HAR-GARCH; deep-learning quantile-function RV (Sci.Dir. S1568494625003278) — cited as
  the calibration target, not as a model to build.
