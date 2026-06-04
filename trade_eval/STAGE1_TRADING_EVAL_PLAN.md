# Stage-1 Trading Evaluation Plan — VRP Short-Put Economic Value

**Status:** design spec (no code, no training). Operationalizes the downstream economic
half of [`planning_docs/execution/rv_trading_eval_plan.md`](../planning_docs/execution/rv_trading_eval_plan.md)
for the **frozen** forecasters promoted out of the two-iteration forecasting study.

**Inputs (all on disk):**
- Forecasts: `execution/data/predictions/<model>.parquet` — `ticker · date · horizon · rv_hat · sigma · q05…q95 · fold_id · model`.
- Truth + benchmark: `execution/data/targets.parquet` — `ticker · date · group · horizon · target_var · target_vol · iv2 · iv_pctile_bucket · post_shock`.
- Protocol/universe: `rv_eval/config.py` (OOS ≥ 2018-01-01, monthly refit, expanding, purged+embargoed; `PRIMARY_HORIZON = 22`).

**The binding caveat (ITER2 §5, FINAL §0).** At 30 DTE the §5 IV-incremental skill is a
coin flip (h=22 `sign_acc` ≈ 0.51–0.54 across the whole field; `qlike_gain_vs_iv²` ≈ 0).
**IV² already prices essentially all of the predictable VRP at this horizon.** Therefore
this layer does **not** test for an RV-vs-IV directional alpha — it tests whether the
forecast's *second moment* (σ, quantiles) and the *regime gate* it powers convert into
**better risk-adjusted and tail-controlled** short-vol P&L than selling vol on IV² alone.
Lead every readout with deflated Sharpe + CVaR, not with mean return.

---

## 1. Model selection & how each output maps to a trading signal

### 1.1 The shortlist (justified from the gate verdicts)

Keep it to **four forecasters + one benchmark**, split into a clean-core path and a
short-history sleeve, exactly as the iteration reports hand off.

| Role | Model | Why promoted (verdict source) |
|---|---|---|
| **Primary (clean_core)** | **EnsembleTopK** | Iter-1 research-candidate; equal-weight Top-K of the HAR family. Best-bunched at h=22 (QLIKE 0.324 clean / 0.291 hard), one of three models with `qlike_gain_vs_iv² > 0` at h=22 (+0.014), runs in seconds. Iter-2 could not beat it: EnsembleTopK-v2's regime weights **did not** improve on equal weight (verdict #21 *reject*). It is the frozen production primary. |
| **Simple fallback (clean_core)** | **HAR-X** | Iter-1 incumbent, HAR + IV/VIX regressors. Lowest pooled clean QLIKE among simple models, **travels best to hard_cases** (h=22 0.284), well-calibrated (cov90 0.909–0.917). The transparent one-regressor-family baseline the ensemble must justify itself against, and the degrade-gracefully path if the ensemble misbehaves on a name. |
| **Short-history sleeve default** | **HAR-Shrink2Group** | Iter-2 **PROMOTE** (verdict #23). Empirical-Bayes shrink-to-pool. Best hard-case QLIKE in the field (0.275, Δ −0.024 vs HAR), **DM-significant vs HAR @ h=22 (+2.65, p=0.008)**, cov90 hard 0.879 toward target, negative bias halved. Regresses clean_core far less than full pooling — the safer pooling bet. |
| **Short-history sleeve bound** | **PanelHAR-FE** | Iter-2 **PROMOTE** (verdict #22). Full pooling + ticker FE. Ties Shrink2Group on hard QLIKE (0.275) with the **strongest DM (+3.33, p=0.0009)** and best hard-case calibration (cov90 0.891). Kept as the *pooling bound* — it regresses clean_core more (+0.020), so it is the aggressive end of the sleeve, not a clean-core replacement. |
| **Benchmark to beat** | **IV-only** | Sell vol when `IV² > trailing RV`; size flat (or by IV-percentile only). `iv2` is already in `targets.parquet`; no model needed. This is the fair-vol null — beating *random walk* is not the bar. |

**Explicitly excluded and why** (so the shortlist stays honest):
- *EnsembleTopK-v2, STAR-HAR, all Track-A blocks (HAR-IVTS/SJ/Range/Act/GVF)* — sub-noise
  or wrong-axis QLIKE wobbles; no §5 or calibration gain that survives the noise floor.
- *VRP-Spread (D4)* — its native "sell-when-IV-rich" head is **anti-informative** at h=22
  (sign_acc 0.469 < coin flip) and springs post-shock traps. We compute the VRP score from
  `rv_hat` instead; we do not trade its head.
- *HARX-HS (D1), HAR-GARCH (D2)* — their per-row σ heads **under-disperse** (cov90 0.62 / 0.87).
  Because Stage-1 *sizing* keys on σ/quantiles, a mis-calibrated σ would silently corrupt the
  size signal. They are barred from the sleeve until recalibrated.
- *HAR-QR (D3), MS-HAR (E3), HAR-MAX* — broken point forecast / DM-significantly worse / overfit yardstick.

### 1.2 Output → signal map

The frozen forecaster emits, per `(ticker, date, horizon=22)`: a point `rv_hat`, a
predictive `sigma`, and the lognormal quantile grid `q05…q95`. These map to three
**strategy** decisions (defined and evaluated only here, never fed back to forecasting):

| Trading signal | Built from | Formula / rule (config-driven) |
|---|---|---|
| **Conditional-VRP score** | `rv_hat`, `iv2` | `vrp_score = iv2 − rv_hat` (both in h=22 summed-variance units, the same units the evaluator's §5 already compares). Positive ⇒ IV rich ⇒ sell-vol candidate. The benchmark uses `iv2 − trailing_RV` in its place. |
| **Regime gate `{trade, reduce, avoid}`** | `vrp_score`, `sigma`, `q05…q95`, `iv_pctile_bucket`, `post_shock` | `avoid` if `post_shock` OR forecast dispersion `sigma/rv_hat` above its trailing 80th pctile OR `vrp_score ≤ 0`; `reduce` if mid-tercile dispersion or low IV percentile bucket; else `trade`. Thresholds are config. |
| **Position size** | `sigma`, quantiles | Inverse-risk / fractional-Kelly proxy: `size ∝ clip( vrp_score / σ²_predictive , 0, cap )`, where σ²_predictive comes from `sigma` (or the `q05…q95` spread for a quantile-native size). Higher forecast uncertainty ⇒ smaller clip. |
| **Structure** | `iv_pctile_bucket`, group, quantile skew | Structure map from `rv_trading_eval_plan.md` §2 (see §2 below); selection is by group + IV regime, **not** by RV alpha. |

The whole point of the σ/quantile dependence: the §5 caveat says the *mean* (`rv_hat`)
carries no edge over IV² at 30 DTE, so any economic value must come from the *gate and the
size*, both of which are driven by the second moment. That is precisely what the ablations
in §5 isolate.

---

## 2. Strategy specification

### 2.1 Pipeline (per `rv_trading_eval_plan.md` §2)

```
forecast(rv_hat, σ, q05..q95) → conditional-VRP score → regime gate → size → structure → P&L
```

- **Universe:** the full scored set — `clean_core` (10) traded by the EnsembleTopK/HAR-X
  path, `hard_cases` (5) traded by the HAR-Shrink2Group/PanelHAR-FE sleeve. **One open
  position per correlation group** (`config.GROUP`) to avoid stacking correlated short-vol.
- **Tenor sweep:** 30-DTE (h=22) is primary, but the strategy is run **across the full
  horizon grid** `h ∈ {5, 10, 22}` ≈ `{7, 14, 30}` DTE (see §2.5). The 30-DTE book is where
  the §5 alpha is gone and value must come from gate/sizing; the 7–14-DTE books are where the
  forecast still carries directional edge over IV² and a *different* model ranking applies.
- **Instrument (Stage-1 abstraction):** short put / put-spread proxied by the variance
  payoff (§3). Long-vol structural-decay names (UVXY) are **call-wing only / no naked short
  put** per the structure map — they are in the sleeve to stress the *gate*, not to harvest VRP.

### 2.2 Regime gate `{trade, reduce, avoid}`

| State | Trigger (config defaults) | Action |
|---|---|---|
| **avoid** | `post_shock == True` OR `vrp_score ≤ 0` OR `sigma/rv_hat` > trailing-80th-pctile | No new position; flatten existing if held. |
| **reduce** | `iv_pctile_bucket ∈ {0,1}` (IV cheap) OR mid dispersion tercile | Half size. |
| **trade** | else (IV rich, dispersion contained, not post-shock) | Full size. |

The gate is the primary hypothesized value source: it should **cut the left tail** (avoid
selling vol into a forecastable variance spike) even if it never improves mean return.

### 2.3 Sizing

`size = base_notional × clip( vrp_score / (k · σ²_pred), 0, size_cap ) × gate_multiplier`.
σ²_pred from the forecast `sigma`. A **quantile-native variant** uses `(q95 − q05)` as the
risk scale instead of `sigma`, to test whether the full predictive shape sizes better than a
single σ. `k`, `size_cap`, `base_notional` are config.

### 2.4 Structure map (config; from `universe.yml` hints via `rv_trading_eval_plan.md` §2)

index/large-cap (SPY, QQQ, EEM, IWM) → short put / put-spread; sector (XLK, XLF, XLE, KRE)
→ put-spread / iron-fly; trending (GLD, TLT, USO) → one-sided or delta-hedged; HYG → short
put small; structural-decay long-vol (UVXY) → **call-wing only**; thin/extreme (MSOS, IBIT)
→ defined-risk put-spread, small size. Stage-1 collapses all of these to the variance proxy
with a per-group cost/notional haircut; Stage-2 (out of scope here) instantiates real strikes.

### 2.5 Horizon sweep — shorter-DTE books and the horizon-dependent verdict

**The §5 "no alpha over IV²" caveat is specific to h=22.** The forecasting reports show the
IV-incremental edge is strong at short horizons and *decays into* the coin flip by 30 DTE:

| Axis (clean_core) | h=1 | h=5 (≈7 DTE) | h=10 (≈14 DTE) | h=22 (≈30 DTE) |
|---|---|---|---|---|
| Best §5 `sign_acc` | 0.73 | ~0.62 | ~0.57 | 0.54 |
| HAR-X QLIKE | 0.282 | **0.180** | 0.202 | 0.339 |
| HAR baseline QLIKE | 0.320 | 0.211 | 0.227 | 0.323 |

So the trading test is **run at h=5, h=10, and h=22**, and the hypothesis differs by tenor:
- **7–14 DTE (h=5, h=10):** the forecast plausibly carries a **directional VRP edge** over
  IV² (the A1 ablation can be positive here, unlike at 30 DTE). This is where to look for
  mean-return alpha, not just tail control.
- **30 DTE (h=22):** value, if any, comes from the **gate and sizing** (tail control), per the
  binding caveat.

**Which models are better at shorter horizons (and why the shortlist must flex):**

| Tenor | Best point forecaster (QLIKE) | Best §5 / directional model (`sign_acc`) |
|---|---|---|
| h=5, h=10 | **HAR-X** (lowest clean QLIKE at h=1/5/10), pooling sleeve close behind on hard names | **HAR-ENet (0.720 @ h=1)**, EnsembleTopK-v2 (0.731), HAR-Ridge — the shrinkage family leads §5 at short horizons |
| h=22 | field converges; HAR baseline ties at h=22 | EnsembleTopK / HAR-X (the frozen path) |

The promotion ranking is **horizon-specific**: the h=22 production primary (EnsembleTopK,
`sign_acc` 0.670 @ h=1) is *not* the short-horizon §5 leader — **HAR-ENet / HAR-Ridge** (kept
as components in iter-2, verdict #19) and **EnsembleTopK-v2** (rejected only because it added
nothing *at h=22*) lead the directional axis at 7–14 DTE. Therefore the sweep **adds HAR-ENet
as a short-horizon §5 candidate** alongside the frozen four, evaluated only at h=5/h=10. The
trade-off to measure: the stronger short-DTE signal is paid for with **higher roll frequency,
turnover, cost, and short-gamma** — so the §4 cost sweep and tail metrics decide whether the
short-DTE edge survives, not the raw `sign_acc`.

---

## 3. Stage-1 backtest mechanics (variance proxy)

Per `rv_trading_eval_plan.md` §3, Stage 1 is the fast, model-ranking layer:

```
pnl_t = size_t × sign_short × (iv2_t − target_var_t) − cost_t
```

- `iv2_t` and `target_var_t` from `targets.parquet` at `(ticker, date, horizon=22)` —
  variance units, already aligned with `rv_hat`. `sign_short = +1` for a short-vol position
  (we collect when realized var lands below implied).
- **Cost haircut** `cost_t = c_bps × turnover_t × notional`, per-group `c_bps` (wider for
  MSOS/IBIT/UVXY). Turnover from position changes at the monthly roll. Stage-1 uses a
  conservative flat haircut; real bid/ask + slippage is deferred to Stage-2.
- **Roll cadence:** monthly (matches 30-DTE and the `REFIT_FREQ="monthly"` walk-forward),
  so position dates align with refit folds and no intra-fold look-ahead is introduced.
- **Entry timing:** signal computed from forecasts dated `t`; P&L realized over `[t, t+22]`
  using the forward `target_var` that the evaluator already defines. No same-day truth use.

### 3.5 Intra-trade management & early exit (daily re-gating)

**Gap in the v1 spec, now closed.** The pipeline as first written entered at the monthly
roll and **held to expiry** — there was *no* mid-trade adjustment or closure if conditions
turned risky. That is exactly the wrong default for a short-gamma book, and it under-uses the
forecaster: predictions are produced **daily** for every `(ticker, date, horizon)`, so for a
30-DTE trade opened at `t` there is a fresh forecast and a fresh gate on each of `t+1 … t+22`.

The strategy therefore carries a **management overlay** evaluated **daily over each open
position** (all rules config-driven, swappable):

| Rule | Trigger (from the daily-refreshed forecast) | Action |
|---|---|---|
| **Risk-off exit** | gate flips to `avoid` mid-trade — `post_shock` fires, `sigma/rv_hat` jumps above its trailing-80th pctile, or `vrp_score` turns ≤ 0 | Close (or de-risk: roll the short strike down / buy the protective wing). The forecast's tail-warning is consumed *continuously*, not only at entry. |
| **Profit-take** | accrued variance P&L ≥ `take_frac` of max capturable premium (e.g. 50–70%) | Close early — standard short-vol discipline; banks the convexity-favorable middle of the trade. |
| **Stop-loss** | mark-to-market loss > `stop_mult` × credit, **or** realized variance accrued over `[t, t+k]` already exceeds the entry `iv2` | Close — caps the left tail the terminal payoff would otherwise eat in full. |
| **Roll** | near expiry and gate still `trade` | Roll to the next monthly instead of flat-then-reopen (lowers turnover vs naive re-entry). |

**Stage-1 fidelity — the variance-accrual mark.** The simple terminal payoff
`(iv2_t − target_var_t)` cannot represent an early exit, so to model management in Stage-1 the
position is **marked daily** along its path: realized variance accrued over `[t, t+k]` (from
the daily RV path already in `inputs`/`targets`) **plus** the remaining implied carry valued at
the prevailing `iv2_{t+k}`. That gives a per-day mark series so the exit rules above can fire
at the correct date. It is an approximation (no greeks, no smile, no early-assignment), but it
is enough to **rank a managed overlay against hold-to-expiry**. Full path-dependent management
— theta/vega/gamma marks, real bid/ask on the unwind, assignment — is **Stage-2 ORATS**, where
EOD option marks make the early-close P&L exact.

This overlay is tested head-to-head against the held-to-expiry book in ablation **A9** (§5):
the §5 caveat predicts continuous re-gating is precisely where the forecast's tail value should
concentrate, so a managed book that cuts CVaR/max-DD without giving back too much mean return
is the single most likely place the forecast pays its way at 30 DTE.

---

## 4. Economic metrics (lead with risk-adjusted + tail)

Per `rv_trading_eval_plan.md` §5 and the §5 thin-alpha caveat — short-vol P&L is
short-gamma and negatively skewed, so plain Sharpe flatters it. **Mandatory, in this order:**

1. **Deflated Sharpe Ratio (DSR)** — Bailey/López de Prado, adjusted for the number of
   model/ablation configurations tried here (we are explicitly multiple-testing across 4
   forecasters × ablations). This is the headline statistic.
2. **Tail / CVaR:** CVaR(95), CVaR(99), worst-day and worst-20-day P&L, max drawdown,
   downside (Sortino) deviation. Report the full left-tail distribution, not just a point.
3. **Turnover & cost sensitivity:** P&L net vs gross across a `c_bps` sweep; the break-even
   cost at which the edge vanishes.
4. **Supporting:** annualized return, Sharpe, Sortino, hit rate, avg win/loss, capacity.

**Significance:** P&L-series DM and Hansen **SPA** vs the IV-only benchmark, with a
**stationary block bootstrap** (block length ≥ 22 to respect the overlapping 30-DTE windows).
Overlap-aware: the 22-day horizon means daily P&L is autocorrelated — never use iid bootstrap
or naive Sharpe SEs.

**Portfolio stress (§6):** evaluate the whole one-per-group book on its worst ~20 days and
report realized cross-group correlation in stress vs calm — the diversification across 15
groups collapses toward 1 in a vol shock, which is exactly when a short-vol book is exposed.

---

## 5. Ablations — isolating where (if anywhere) the forecast adds economic value

Each ablation toggles **one** signal and is measured by the §4 metric stack (DSR + CVaR
first). The design mirrors `rv_trading_eval_plan.md` §4 attribution.

| # | Contrast | Question it answers |
|---|---|---|
| **A1** | **Forecast-gated vs IV-only** | Does using `rv_hat`/σ at all beat selling vol on IV² with flat/IV-percentile sizing? The top-line go/no-go contrast. |
| **A2** | **With vs without the regime gate** | Holding the forecaster fixed, does `{trade/reduce/avoid}` cut CVaR/max-DD? The hypothesized primary value source (tail control), per §5 caveat. |
| **A3** | **With vs without forecast-driven sizing** | σ/quantile-keyed size vs flat size. Does the second moment improve *risk-adjusted* return even if mean is flat? |
| **A4** | **With vs without the pooled hard-case sleeve** | On `hard_cases`, HAR-Shrink2Group/PanelHAR-FE sleeve vs forcing the clean-core path (or per-ticker HAR-X) onto the thin names. Tests whether the iter-2 pooling promotion pays *economically*, not just in QLIKE. |
| **A5** | **σ-sizing vs quantile-spread sizing** | Does the full predictive shape (`q95−q05`) size better than a single `sigma`? Diagnostic for whether the quantile grid is worth carrying downstream. |
| **A6** | **EnsembleTopK vs HAR-X (primary vs fallback)** | Does the ensemble earn its complexity economically over the transparent fallback? |
| **A7 (control)** | **Random-entry / always-sell controls** | Confirms any edge is the signal, not the short-vol carry itself or luck. |
| **A8** | **Horizon sweep: h=5 / h=10 / h=22** (§2.5) | Where does the forecast pay? Expect directional (A1-positive) edge at 7–14 DTE that decays to gate/sizing-only value at 30 DTE. Also re-ranks models per tenor (HAR-ENet/v2 at short DTE vs EnsembleTopK at 30 DTE). |
| **A9** | **Managed (daily re-gating) vs hold-to-expiry** (§3.5) | Does the intra-trade overlay — early `avoid`-exit, profit-take, variance-accrual stop — cut CVaR/max-DD beyond entry-only gating? The most likely place forecast tail-value shows up at 30 DTE. |

Attribution is read as the marginal CVaR/DSR contribution of each toggled signal —
**not** as a single combined P&L. A flat A1 with a strongly positive A2 is the *expected*
outcome under the §5 caveat (no mean alpha, but real tail value from gating) and is reported
as such, not buried.

---

## 6. Leakage-safe backtest protocol

Reuse the existing forecasting discipline verbatim — **no new estimation, no refits** in this
layer; we only consume frozen prediction parquets.

- **OOS window:** `OOS_START = 2018-01-01` → 2026-05-21, the same rolling-origin,
  purged + embargoed, monthly-refit, expanding-window folds (`fold_id` is carried in the
  prediction files). Spans COVID-2020, Rates-2022, Tariff-2025 stress regimes.
- **Strict point-in-time:** the signal at `t` uses only forecasts dated `≤ t`; P&L uses the
  forward `target_var` over `[t, t+22]`. The 22-day embargo (`EMBARGO_EXTRA`, h) already
  baked into the predictions prevents the training tail from leaking into the test fold.
- **Frozen forecaster:** models are *not* re-tuned for P&L. Strategy thresholds (gate
  cutoffs, `k`, `c_bps`, `size_cap`) are **config set once** and, where they need any
  calibration (e.g. the dispersion percentile), calibrated **only on a pre-OOS block
  (< 2018)** or on a trailing-expanding basis — never on the OOS P&L being scored.
- **Coverage honesty:** predictions are inner-joined to truth (as the evaluator does);
  missing cells are dropped, never imputed. IV-dependent / short-history names cover fewer
  rows — DM/SPA vs IV-only run on **common support** only, and per-group P&L is reported over
  each model's own covered dates.
- **Multiple-testing bookkeeping:** count every forecaster × ablation × threshold variant
  evaluated and feed that count into the DSR deflation, so the headline statistic is honest
  about the search.

---

## 7. Honest priors & go/no-go bar

### 7.1 Priors (what the forecasting study already tells us to expect)

- **A1 (forecast vs IV-only) is likely ≈ flat on mean return at h=22 but plausibly positive
  at h=5/h=10.** IV² prices the predictable VRP at 30 DTE; both head-on attacks on that axis
  (VRP-Spread, HARX-HS) failed. But the §5 edge is real at short horizons (`sign_acc` ≈0.70 @
  h=1), so the **directional alpha is a short-DTE phenomenon (A8)** — and there it is bought
  with higher turnover/cost and worse short-gamma, which the §4 cost sweep must clear.
- **A2 (regime gate) and A9 (intra-trade management) are the most likely sources of real
  value at 30 DTE** — and they show up in **CVaR and max-drawdown**, not in mean return.
  `post_shock` + dispersion gating, applied both at entry (A2) and **continuously over the
  trade's life (A9)**, should let the book *sit out / exit* the forecastable variance spikes a
  naive hold-to-expiry IV-only seller walks straight into.
- **The best model is horizon-dependent (A8).** Expect EnsembleTopK/HAR-X to carry the 30-DTE
  book on gate/sizing, but HAR-ENet / EnsembleTopK-v2 to lead the directional 7–14-DTE book —
  the iter-2 "components" may earn standalone use at a tenor the forecasting study didn't gate on.
- **A4 (pooled sleeve) should help on `hard_cases` specifically** — the iter-2 pooling win
  was DM-significant on the thin names and improved their calibration, which is exactly what
  better sizing/gating needs. Expect little-to-negative benefit if forced onto clean_core.
- **The edge, if any, is small and cost-sensitive.** Expect Stage-1 break-even cost to be low.

### 7.2 Go / No-Go bar (promotion to Production candidate, per `rv_trading_eval_plan.md` §7)

A frozen Research-candidate forecaster **passes Stage-1** and earns a Stage-2 (full ORATS) run
iff, vs the IV-only benchmark, on its intended universe:

1. **Risk-adjusted:** beats IV-only on **deflated Sharpe** (DSR statistically positive after
   the multiple-testing deflation), **and**
2. **Tail not worse:** **not-worse CVaR(95) and max-drawdown** than IV-only (a strict
   no-regress on the left tail — this is the dominant criterion for a short-gamma book), **and**
3. **Attribution:** the A2 (gate) **and/or** A3 (sizing) ablation shows a **statistically
   positive marginal** contribution — i.e. the edge traces to a forecast signal, not to the
   short-vol carry or to luck (A7 controls must not match it), **and**
4. **Survives cost:** the edge persists at the conservative `c_bps` haircut (positive net of
   the realistic, not just the optimistic, cost point).

**No-Go does not demote the forecaster.** Per the downstream spec's principle, failing here
keeps the model a valid forecasting Research-candidate; it simply is not promoted for trading
yet. A *clean negative* (e.g. "the gate adds no tail value beyond IV-only's own IV-percentile
gating") is a publishable, decision-useful result — and, given the §5 caveat, a genuinely
plausible outcome this plan is designed to detect rather than to overcome.

---

## 8. Deliverables of the Stage-1 run (when built)

- A per-`(forecaster, horizon, ablation)` economic scorecard led by DSR + CVaR, with the §4 stress panel.
- The A1–A9 attribution table isolating gate vs sizing vs sleeve vs ensemble vs horizon vs management.
- A **per-tenor model ranking** (which model wins at 7 / 14 / 30 DTE, §2.5/A8).
- A **managed-vs-hold** tail comparison (A9) showing whether intra-trade re-gating cuts CVaR/max-DD.
- A go/no-go verdict per forecaster **per horizon** against §7.2, naming Stage-2 survivors (if any).
- All numbers over the frozen 2018→2026 OOS folds on common support; no retraining.

_Sources: `execution/reports/ITER2_FINAL_MODEL_COMPARISON_REPORT.md` (§5 caveat, promotions),
`execution/reports/iter2_verdicts.md` (per-model gate), `execution/reports/FINAL_MODEL_COMPARISON_REPORT.md`
(iter-1 incumbents), `planning_docs/execution/rv_trading_eval_plan.md` (downstream spec),
`rv_eval/config.py` + `rv_eval/model_contract.py` (universe / horizons / output contract)._
