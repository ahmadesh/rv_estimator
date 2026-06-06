# Stage-2 Results Index (index only — no commentary)

| Worker | Cells | Artifact | Rows |
|---|---|---|---|
| W1 | scoring adapter (dry-run smoke; 2 cells: EnsembleTopK + IV-only × iron_condor/hold/none, h22, full-OOS smoke) | `reports/score_stage2.py` | module |
| W1 | " | `results/scorecard.parquet` | 2 |
| W1 | " | `results/attribution.parquet` | 1 |
| W1 | " | `results/verdicts.parquet` | 1 |

_Note: W1 scorecard/attribution/verdicts are dry-run smoke outputs (default `results/` root); superseded by the per-worker subdir scoring below._

| W0 | leakage gate (10 leakage tests + framework, all green) | `tests/test_leakage.py`, `results/_w0_validation.json` | 15 pass |
| W2 | M2 defined-risk, full OOS, h22 — `{EnsembleTopK,HAR-X,IV-only}×{iron_condor,iron_fly,put_credit_spread}×hold×none` (9 cells) | `results/w2/ledger/*` + `portfolio/*` | 9+9 |
| W2 | " | `results/w2/{manifest,scorecard,attribution,verdicts}.parquet` | 9/9/6/6 |
| W4 | M4 naked overlay, full OOS, h22 — `{EnsembleTopK,IV-only}×{short_strangle,short_straddle}×{hold,mechanical_terminal}×{none,terminal_band}` (16 cells) | `results/w4/ledger/*` + `portfolio/*` | 16+16 |
| W4 | " | `results/w4/{manifest,scorecard,attribution,verdicts}.parquet` | 16/16/8/8 |
| W3 | M3 mgmt+hedge, full OOS, h22 — `EnsembleTopK×{iron_condor,short_strangle}×{hold,forecast_regate,mechanical_terminal,iv_regate}×{none,terminal_band,full_band}` (24 cells) | `results/w3/ledger/*` + `portfolio/*` | 24+24 |
| W3 | " | `results/w3/{manifest,scorecard,verdicts}.parquet` (no IV-only in slice → attribution 0) | 24/24/24 |
| W5 | M5 tuning, **VALIDATION WINDOW 2018-01..2021-12 ONLY** (max entry 2021-12-03; `--end>2021-12-31` guard fires). Each sweep-value = own subdir (model cell + IV-only null + scorecard/attribution/verdicts). E1 EnsembleTopK-v2; E2 gate pctile {0.70,0.75,0.80,0.85,0.90}; E3 PIT σ-recal (lag h+1=23d); E4 Kelly c{.25,.30,.35}×cap{2,3,4} | `results/w5/{e1,e2_p070..p090,e3,e4_c0**_cap*}/` (16 subdirs) + `results/w5/_w5_artifacts.json` | 32 ledgers |

## Headline — consolidated full-OOS book (W2+W3+W4 pooled, global deflation)

| Scope | Cells | N_TRIALS | Artifact | Rows |
|---|---|---|---|---|
| Full-OOS (W2+W3+W4 pooled, 5 identical overlaps collapsed) | 44 unique (EnsembleTopK 30 / HAR-X 3 / IV-only 11) | **44** (global) | `results/full_oos_consolidated/scorecard.parquet` | 44 |
| " | " | " | `results/full_oos_consolidated/{attribution,verdicts}.parquet` (33 non-benchmark cells vs option-space IV-only) | 33/33 |
| " | " | " | `results/full_oos_consolidated/{ledger,portfolio}/*.parquet` + `manifest.parquet` | 44+44/44 |

_W5 (validation-window tuning) is scored separately per-sweep and is NOT pooled into the full-OOS deflation. The 2022-01..2026-05 held-out window was never scored by any worker. DSR power caveat (plan §0: ~125 monthly h=22 obs; no cell cleared absolute DSR≥0.95) persists — option marks add realism, not observations._

---
**Handoff:** economic analysis is a separate LLM's job. Start from this index; per-cell numbers live in the `scorecard`/`attribution`/`verdicts` parquets above. No verdicts are recorded here by design.
