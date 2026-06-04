# Iteration-2 Model Swarm — Progress Ledger

Orchestrator-owned durable state for the Modern-HAR Extensions wave (models 13–32 +
Wave-0 infra), per `ITER2_ORCHESTRATOR_PROMPT.md` / `ITER2_MODEL_CATALOG.md`. On every
resume, re-read this file AND the filesystem before acting. A model is `done` only if its
validation gate passes (parquet valid: all horizons, clean_core covered, rv_hat>0, monotone
quantiles; both cards non-empty; smoke test reported). Build order: Wave-0 → Wave-1 →
Wave-2 (21 last) → Wave-3.

status ∈ {pending, building, done, failed}

| model | name | file:Class | track | status | parquet rows | cards | last_update | notes |
|------|------|-----------|-------|--------|-------------|-------|-------------|-------|
| W0 | _base_v2 | candidate_models/_base_v2.py | infra | done | — | — | 2026-06-03 | FROZEN. _AttachMixin + _PooledLinearHAR + _QuantileModel + helpers (_emit_lognormal, fit_pooled, pooled_mu). Smoke test test_base_v2.py: 4 passed. Real-data integration verified via walkforward (LHAR-style attach 104k preds, pooled 105k preds, both 10/10 clean_core, rv_hat>0, monotone). Zero rv_eval/ edits. Later workers import READ-ONLY. |
| 13 | LHAR | candidate_models.lhar:LHAR | A | done | 146260 (105.4k cc + 40.8k hc) | both | 2026-06-03 | P1 attach: lev_d/w/m = roll_mean(min(ret_cc,0),{1,5,22}). 15/15, no drops. Smoke 2/2. Neg log-bias (HYG/EEM, IBIT/UVXY, post-shock). 9.6s cc/4.9s hc. |
| 14 | HAR-SJ | candidate_models.har_sj:HARSJ | A | done | 146260 (105.4k cc + 40.8k hc) | both | 2026-06-03 | P1 attach: sj_5d=roll_mean(rs_plus-rs_minus,5), abs_sj_5d. 15/15, no drops. Smoke 2/2. 9.6s cc/4.9s hc. |
| 15 | HAR-IVTS | candidate_models.har_ivts:HARIVTS | A | done | 140839 (102.8k cc + 38k hc) | both | 2026-06-03 | P1 attach: iv_curv, iv_ts_30_90, vrp_lag(=iv_30d²−rv), vrp_mom(shift5), vix9d_slope. 15/15 tickers, no drops. Smoke 2/2. HYG h=22 neg bias; hc cov90~0.83-0.85. 11s cc/5.4s hc. |
| 16 | HAR-Range | candidate_models.har_range:HARRange | A | done | 146260 (105.4k cc + 40.8k hc) | both | 2026-06-03 | P1 attach. log_park_d/w + log_gk_d/w = log roll_mean(parkinson/gk,{1,5}) from inputs precomputed cols. 10/10 cc. Smoke 2/2. hc cov90 0.34-0.46 UVXY/MSOS short hz (fat tail). 9.8s cc/4.7s hc. |
| 17 | HAR-Act | candidate_models.har_act:HARAct | A | done | 146260 (105.4k cc + 40.8k hc) | both | 2026-06-03 | P1 attach. log_vol_surprise, log_txn_surprise (vs 22d roll mean), overnight_share=rv_overnight/total_rv. 10/10 cc. Smoke 2/2. 9s cc/4.4s hc. |
| 18 | HAR-MAX | candidate_models.har_max:HARMAX | A | done | 140839 (102.85k cc + 38k hc) | both | 2026-06-03 | P1 kitchen-sink plain OLS, 31 feats (union of 13-17 derived + IV/RS/rq). 10/10 cc. Smoke pass. 17.3s cc/8.8s hc. Matrix reused by 19. |
| 19 | HAR-ENet+Ridge | candidate_models.har_shrink:{HARENet,HARRidge} | B | done | ENet 140839 + Ridge 140839 (102.85k cc + 38k hc each) | both x2 | 2026-06-03 | P2 per-key penalized log-OLS on MAX matrix (~25 cols). TimeSeriesSplit(5) inner CV on train only, standardized. 10/10 cc both. Smoke 3/3. ENet 567s+183s; Ridge 298s+104s. Two parquets: HAR-ENet, HAR-Ridge. |
| 20 | HAR-CSR | candidate_models.har_csr:HARCSR | B | done | 142562 (104k cc + 38.5k hc) | both | 2026-06-03 | P2. Complete-subset: avg of C(8,4)=70 OLS fits (full enum, no sampling). 8 pass-through feats. 10/10 cc. Smoke 2/2. USO h>=10 level-pinball (2020 oil outlier, QLIKE fine). 54s cc/17s hc. |
| 21 | EnsembleTopK-v2 | candidate_models.ensemble_top_v2:EnsembleTopKV2 | B | done | 140566 (101.9k cc + 38.7k hc) | both | 2026-06-03 | P3 post-hoc. Pool=15 (iter-1 winners + A/B/D). Top-K=5 per-horizon by trailing discounted-MSE; regime-cond inverse-MSE softmax per (horizon, iv_pctile bucket), HL=252d, expanding, thin→pooled fallback. Leak-safe (weights from purged y_train only). 10/10 cc. Smoke 5/5. 10s cc/6.7s hc. |
| 22 | PanelHAR-FE | candidate_models.panel_har:PanelHARFE | C | done | 143745 (104k cc + 39.7k hc) | both | 2026-06-03 | P3 _PooledLinearHAR. Pooled per-horizon log-OLS, ticker FE intercepts, unseen→group→global fallback. needs=RS+IV (13 slopes). 10/10 cc. Smoke 2/2. 9.1s cc/3.3s hc. |
| 23 | HAR-Shrink2Group | candidate_models.har_shrink2group:HARShrink2Group | C | done | 143745 (104k cc + 39.7k hc) | both | 2026-06-03 | P3. β=(1-w)β_ticker+wβ_pooled, w per-horizon by 4-fold expanding inner CV on TRAIN (selected {.5,.6,.6,.8,.9}). Thin→pooled fallback (0 occurred). 10/10 cc. Smoke 3/3. 39s cc/13s hc. |
| 24 | HAR-GVF | candidate_models.har_globalfactor:HARGlobalFactor | C | done | 146260 (105.4k cc + 40.8k hc) | both | 2026-06-03 | P1 attach. log_gvf=log(mean total_rv over CLEAN_CORE basket per DATE), joined by date, identical across tickers; hard names never in basket (leak-free). 10/10 cc. Smoke 3/3. 8.3s cc/4.1s hc. |
| 25 | HARX-HS | candidate_models.harx_hs:HARXHeteroSigma | D | done | 142497 (104k cc + 38.5k hc) | both | 2026-06-03 | HAR-X mean + per-row σ head (log resid² on rq/vix/vvix/vix9d_slope). Full coverage 15/15 tickers, 0 σ-head fallbacks. Smoke 3/3. Note: pooled cov90≈0.54-0.62 (still narrow). 10.2s cc / 5.0s hc CPU. |
| 26 | HAR-GARCH | candidate_models.har_garch:HARGARCH | D | done | 146260 (105.4k cc + 40.8k hc) | both | 2026-06-03 | P2. HAR log-OLS mean + arch GARCH(1,1)/GJR on log-resid, o∈{0,1} by TRAIN BIC. 0 fallbacks (50/50 cc, 25/25 hc). Smoke 4/4. cov90~0.87-0.89. arch 8.0.0. 145s cc/46s hc. |
| 27 | HAR-QR | candidate_models.har_qr:HARQR | D | done | 146260 (105.4k cc + 40.8k hc) | both (orch-gen) | 2026-06-03 | DIRECT QUANTILES, level-space sklearn QuantileRegressor(highs). 10/10 cc, monotone+finite. Worker backgrounded+died; ORCHESTRATOR ran walkforward (cc 10889s≈3.0h + hc 2244s≈37m — SLOW: highs LP scales w/ n; use statsmodels QuantReg to fix) + gen+augmented cards. ⚠QUALITY: pooled QLIKE explodes 1e6-1e7 on HYG/GLD/SPY (level-space miscalib) — flag for comparison. Smoke 2/2. |
| 28 | VRP-Spread | candidate_models.vrp_spread:VRPSpread | D | done | 127754 (93.7k cc + 34k hc) | both | 2026-06-03 | P3 direct-quantile. Level-space OLS of spread s=iv2_h−rv_h (iv2_h=iv_30d²·h/252, from X not targets). 10/10 cc all 5 hz, monotone+finite verified. Fewer rows (IV start). cov90~0.88cc/0.81-0.86hc, cov50~0.45 narrow. 10s cc/4.9s hc. |
| 29 | Threshold-HAR | candidate_models.threshold_har:ThresholdHAR | E | done | 142497 (104k cc + 38.5k hc) | both | 2026-06-03 | P2 attach. HARD regime by expanding pctile of vix (thr 0.5), per-regime log-OLS on RS+IV; sparse<40→pooled fallback (0). Both regimes exercised. 10/10 cc. Smoke 4/4. 26s cc/11s hc. |
| 30 | STAR-HAR | candidate_models.star_har:STARHAR | E | done | 144178 (104k cc + 40.1k hc) | both | 2026-06-03 | P1 attach. Logistic transition g=σ(10·(vix_pctile−0.5)), expanding pctile (leak-safe join). HAR + vix_pctile + 3 interactions. 10/10 cc. Smoke 4/4. 10.3s cc/5.6s hc. |
| 31 | MS-HAR | candidate_models.ms_har:MSHAR | E | done (CANDIDATE-FOR-REJECTION) | 146048 (105.4k cc + 40.6k hc) | both | 2026-06-03 | P3 2-state MS-HAR, hand EM (Hamilton/Kim), cap80 iter, refit_every6 amortized, 1 single-regime fallback cc. 10/10 cc. Smoke 3/3. HARD-GATE: WORSE than STAR/single-HAR at every horizon (h22 QLIKE .370 vs STAR .315) — flagged reject, comparison decides. 556s cc/132s hc. |

## FINAL SUMMARY — swarm complete 2026-06-03

**Status: ALL DONE.** Wave-0 infra + all of 13–32 built, validated, carded. 0 failed, 0 twice-failed.
1 flagged candidate-for-rejection (31 MS-HAR, per its own hard gate). Model 19 produced TWO parquets
(HAR-ENet + HAR-Ridge). Total iter-2 prediction parquets written: **21** (20 catalog models, 19→2).

| metric | value |
|---|---|
| models done | 20/20 (13–32), + W0 infra |
| failed | 0 |
| candidate-for-rejection | 1 (31 MS-HAR — loses to STAR/single-HAR at every horizon) |
| quality-flagged | 1 (27 HAR-QR — pooled QLIKE 1e6–1e7 on heavy-tail names, level-space miscalib) |
| clean_core coverage | 10/10 tickers × 5 horizons on every model |
| hard_cases coverage | full on every model (no data-starved drops needed) |
| rv_hat>0 / monotone q | passed on all 21 parquets |
| sandbox violations | 0 (no worker touched rv_eval/, _base_v2.py, pyproject, uv.lock, or another's file) |

**Wall-time outlier:** 27 HAR-QR = 3.0h cc + 37m hc (sklearn QuantileRegressor highs-LP scales with n;
worker backgrounded+died → orchestrator ran the walk-forward + generated/augmented cards). Fix for any
rerun: statsmodels QuantReg (IRLS) → minutes. All other models 8–560s/universe.

**Heavy-model handling that worked:** 26 HAR-GARCH (timed a fit first, capped iters) and 31 MS-HAR
(timed a fit first, capped EM iters + refit_every=6 amortization) both finished foreground in <10min —
the lesson from QR's 3h was applied successfully downstream.

**Next step (separate, human-triggered — NOT run here):** the cross-model comparison pass
(planning_docs/execution/COMPARISON_PLAN.md, evaluator.py) under the re-weighted gate
(planning_docs/research/rv_har_extensions_plan.md §4).

## Notes / lessons (append as the run proceeds)

- Pre-flight: confirm inputs.parquet has vix9d/vix9d_slope/credit_spread/credit_mom/usd_mom/rates_mom
  (added 2026-06-03 via `rv_eval.setup._add_systematic_cols`). If missing, run it once.
- Wave-0 `_base_v2.py` MUST be done + frozen before any of 13–32. Later workers import it read-only.
- Inherit the iter-1 heavy-model lesson (ledger row 8): for any model whose walk-forward runs long
  (26 HAR-GARCH, 31 MS-HAR), use build-only worker → orchestrator-run walkforward → card worker, so a
  subagent dying mid-run doesn't lose the parquet.
