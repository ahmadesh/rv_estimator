# Sequential Model Swarm — Progress Ledger

Orchestrator-owned durable state. On every resume, re-read this file AND the filesystem
before acting. A model is `done` only if its validation gate passes (parquet valid +
both cards non-empty + smoke test reported). Build order: 0,1,2,3 → 4..11 → 12 (last).

status ∈ {pending, building, done, failed}

| model | name | class spec | status | parquet rows | cards | last_update | notes |
|------|------|-----------|--------|-------------|-------|-------------|-------|
| 0 | RW | rv_eval.model_contract:RandomWalk | done | 147210 | RW.md, RW.hard_cases.md | 2026-05-31 | GATE PASS: 15 tickers, all h, rv_hat>0, quantiles monotone. cpu, ~10s. IBIT/MSOS thin (legit). |
| 1 | EWMA | rv_eval.model_contract:EWMA | done | 147210 | EWMA.md, EWMA.hard_cases.md | 2026-05-31 | GATE PASS: 15 tickers, all h, rv_hat>0, monotone. cpu, ~10s. Full coverage. |
| 2 | HAR | rv_eval.model_contract:HAR | done | 146260 | HAR.md, HAR.hard_cases.md | 2026-05-31 | GATE PASS: §9 baseline present. 15 tickers, all h, rv_hat>0, monotone. cpu ~12s. |
| 3 | HAR-X | rv_eval.model_contract:HARX | done | 142497 | HAR-X.md, HAR-X.hard_cases.md | 2026-05-31 | GATE PASS: 15 tickers, all h, rv_hat>0, monotone. cpu ~14s. IBIT/MSOS IV-null rows dropped (legit). |
| 4 | HARQ | candidate_models.harq:HARQ | done | 146260 | HARQ.md, HARQ.hard_cases.md | 2026-05-31 | GATE PASS: 15 tickers, all h, monotone, smoke OK. cpu ~12s. harq.py+test in sandbox. |
| 5 | HAR-RS | candidate_models.har_rs:HARRS | done | 146260 | HAR-RS.md, HAR-RS.hard_cases.md | 2026-05-31 | GATE PASS: 15 tickers, all h, monotone, smoke OK. cpu ~12s. Full coverage. |
| 6 | HAR-CJ | candidate_models.har_cj:HARCJ | done | 146260 | HAR-CJ.md, HAR-CJ.hard_cases.md | 2026-05-31 | GATE PASS: 15 tickers, all h, monotone, smoke OK, min date 2018-01-02. Derived log-BV/jump computed on full series then date-joined (trailing→leakage-safe). cpu ~14s. |
| 7 | HAR-RS-IV-Q | candidate_models.har_rs_iv_q:HARRSIVQ | done | 142497 | HAR-RS-IV-Q.md, HAR-RS-IV-Q.hard_cases.md | 2026-05-31 | GATE PASS: 15 tickers, all h, monotone, smoke OK, min 2018-01-02. 14 dedup feats. IBIT/MSOS IV-null rows dropped (legit). cpu ~15s. |
| 8 | RealizedGARCH | candidate_models.realized_garch:RealizedGARCH | done | 146448 | RealizedGARCH.md, RealizedGARCH.hard_cases.md | 2026-05-31 | GATE PASS after orchestrator-run walkforward (subagents kept backgrounding the 37-min MLE run & dying). 15 tickers, all h, rv_hat>0, monotone. arch 8.0.0, omega floor 1e-8, 1000 MC paths, seed 0. clean_core 2236s/hard_cases 77s. cpu. LESSON: heavy models 9/10/11 → build-only worker + orchestrator-run walkforward + card worker. |
| 9 | XGBHARRSIV | candidate_models.xgb_har:XGBHARRSIV | done | 144527 | XGBHARRSIV.md, XGBHARRSIV.hard_cases.md | 2026-06-01 | GATE PASS (split build). 15 tickers, all h, rv_hat>0, monotone, smoke 2 passed. xgboost 3.2.0, frozen max_depth=3/lr=0.03/mcw=20 (val QLIKE@h22 0.1470 vs init 0.1590), tree_method=hist, seed 0. clean_core 698s/hard 264s cpu. |
| 10 | LSTMRV | candidate_models.lstm_rv:LSTMRV | done | 142495 | .md+.hard_cases.md+.report.md | 2026-06-01 | GATE PASS after 3 walkforward attempts. torch 2.12.0 MPS. Frozen hidden=64/layers=1/dropout=0.1/lr=5e-4 (tuned: QLIKE@h22 0.2100 vs init 0.4128, 1-layer wins). A1 emitted 0 preds (predict got ~21d slice < WINDOW=60 → all-NaN; walkforward.py:95). FIX: cache last 59 rows/ticker in fit, prepend at predict (leakage-safe, regression-tested, real-data verified). A2 crashed at _merge (stale 0-row parquet); deleted it. A3 OK: clean_core 10999s/hard 2999s. 15 tickers all h, rv_hat>0, monotone. IBIT/MSOS thin (IV hist). QLIKE@h22 0.372. qlike_gain_vs_iv negative (self-note). Report inline. |
| 11 | GuyonLekeufackPDV | candidate_models.pdv_glek:GuyonLekeufackPDV | done | 146471 | .md+.hard_cases.md+.report.md | 2026-06-01 | GATE PASS (split build). 15 tickers, all h, rv_hat>0, monotone, smoke 2 passed. scipy 1.17.1, L-BFGS-B, 500 paths, seed 0. walkforward clean_core 11129s/hard 2604s cpu. QLIKE@h22 1.70 (clean, inflated by HYG anomaly QLIKE 9.54); hard improves w/ horizon. Report inline. |
| 12 | EnsembleTopK | candidate_models.ensemble_top:EnsembleTopK | done | 146448 | .md+.hard_cases.md+.report.md | 2026-06-01 | GATE PASS. 15 tickers, all h, rv_hat>0, monotone, smoke 1 passed. Equal-weight mean of 8 components; sigma=sqrt(within²+between var); min-2-component rule (23 MSOS keys dropped for <2 comps, never imputed). clean_core 6.8s/hard 6.5s cpu. Report inline. |

## Modeling reports (NEW deliverable, user request 2026-06-01)
Each model 0–12 also gets a narrative `candidate_models/cards/<name>.report.md` (separate from
the selfstats cards). Content: overview; modeling approach & rationale (cite method/paper);
features & why; key design/implementation decisions (incl. non-obvious ones); hyperparameters &
selection (or "none" for 0–7); self-only results interpretation (QLIKE by h, IV-incremental
skill, conditional bias, calibration/coverage — strengths/weaknesses, NO cross-model ranking);
coverage & limitations (dropped tickers/horizons, anomalies); reproduction. Report-only workers
for done models do NOT re-run walk-forwards/selfstats. Future card/build workers (10,11,12)
produce the report inline.

Report status: 0–9 DONE (10 .report.md written by 3 report-only batch workers; verified non-empty,
no contamination). Remaining: 10,11 via their card workers; 12 via ensemble worker (report inline).

## FINAL SUMMARY (swarm complete 2026-06-01 ~12:00 PDT) — STOP, comparison NOT run
All 13 models (0–12) are `done`. Validation gate passed for every model: correct `model` column,
all 5 horizons {1,5,10,22,42}, 10 clean_core tickers fully covered, rv_hat finite & >0, monotone
q05..q95, both self-stats cards + a narrative report present. Zero harness contamination across
the whole run (every git-status check showed only candidate_models/ + execution_plan/ changes;
rv_eval/, pyproject.toml, uv.lock never touched by a worker).

Deliverables: 13 predictions parquets in execution/data/predictions/; 26 self-stats cards
(<name>.md + <name>.hard_cases.md); 13 modeling reports (<name>.report.md). No twice-failed
models — all 13 succeeded.

Per-model OOS rows (clean_core+hard_cases): RW 147210, EWMA 147210, HAR 146260, HAR-X 142497,
HARQ 146260, HAR-RS 146260, HAR-CJ 146260, HAR-RS-IV-Q 142497, RealizedGARCH 146448,
XGBHARRSIV 144527, LSTMRV 142495, GuyonLekeufackPDV 146471, EnsembleTopK 146448. (HAR-X &
HAR-RS-IV-Q have fewer rows because IV-null rows are dropped, not imputed; LSTMRV slightly fewer
from window warm-up + IBIT/MSOS thin IV history.)

Coverage gaps (expected, documented, never imputed): IBIT (~1–2y options history) and MSOS
(thin/late IV) are data-starved across IV-dependent models; EnsembleTopK dropped 23 MSOS keys
with <2 available components.

Orchestration notes / lessons:
- Heavy models (R-GARCH, XGB, LSTM, PDV) were run by the orchestrator as harness-tracked background
  jobs because subagents reliably YIELD their turn on long foreground commands, killing the child
  process before any parquet is written. Pattern used for 9/10/11: build-only worker (code + smoke
  + frozen HPs) → orchestrator-run walk-forward in bg → card+report worker.
- One session usage-limit hit (23:40 PDT) mid-build of model 9; recovered cleanly from the ledger +
  filesystem with no lost work (credit reset immediately).
- LSTM (model 10) was the hard case: real predict-context bug (test slice < 60-day window → 0 preds)
  fixed with fit-time context caching + regression test + real-data verification; then a stale
  0-row parquet poisoned _merge_predictions (deleted); 3rd run succeeded.
- Self-only red flags for the comparison pass to weigh (NOT acted on here): RealizedGARCH QLIKE@h22
  ~5.1 (severe long-horizon bias); GuyonLekeufackPDV inflated by HYG anomaly (QLIKE 9.54 at h=22);
  LSTMRV qlike_gain_vs_iv negative at all horizons.

NEXT (separate, human-triggered — OUT OF SCOPE for this swarm): the cross-model comparison pass
(planning_docs/execution/COMPARISON_PLAN.md, evaluator.py) — leaderboard, §9 status vs HAR baseline,
DM matrix, MCS, Progression. NOT run here by design.

## Run notes
- Pre-flight done 2026-05-31: candidate_models/ scaffold present; `uv sync --extra dev` clean
  (no changes); inputs.parquet + targets.parquet present; benchmark names confirmed
  RW/EWMA/HAR/HAR-X; clean_core=10, hard_cases=5, horizons={1,5,10,22,42}.
- Predictions dir at start: RW.parquet, EWMA.parquet (valid). HAR, HAR-X, 4-12 absent.
