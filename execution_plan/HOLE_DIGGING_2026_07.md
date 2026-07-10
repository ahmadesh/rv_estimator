# Hole-digging + improvement program on the frozen put-spread book (2026-07-09)

Checkpoint ledger for the 4-track program approved 2026-07-09. Resume from the first unchecked item.
Target spec: `strategy_backtest/conclusion/FROZEN_STRATEGY_SPEC.md` (v1.0, cross 0.66 / mid 0.93).
All new artifacts tagged and written to `strategy_backtest/results/`; summary doc at the end.

## Phase 1 — cheap forensics (attacks on load-bearing assumptions)

- [x] **A1 lag test** — DONE. cross 0.66→0.54, mid 0.93→0.80. Decomposition: lagging either
      component alone (iv 0.56/0.83, rv 0.55/0.81) ≈ lagging both ⇒ top-2 selection is timing-
      sensitive but NOT quote-coupled (artifact would hit mid harder than cross; it doesn't).
      §6.4 partially defused; T+1-executable book keeps ~82% of the edge.
- [x] **A2 OI capacity** — DONE (`results/frozen_forensics.md`). HOLE CONFIRMED: 31% of trades
      exceed the worse leg's OI (wing p95 9.7×) and that bucket nets −3% of P&L; 80% of P&L sits
      under 0.25× OI. → spawned I5 OI-cap experiment.
- [x] **A7 stress fills** — DONE, DEFUSED: friction ≈ 7% of mid credit, flat across VIX quintiles;
      top-VIX quintile carries $1.06M of the $1.92M P&L with the cheapest relative friction.
- [x] **A8 pin/assignment** — DONE: 8.3% of trades settle within ±1% of short strike; 64 trades
      settle below the wing (−$2.58M gross); 272 breached (102 on div payers — assignment risk
      unmodeled). USO Apr-2020: 1 trade spans the 1:8 reverse split, settle spot unadjusted in the
      chain (booked +$10k; roughly right by coincidence, mechanically wrong) — negligible.

## Phase 2 — statistics layer

- [x] **A4 plateau sweep** — DONE (`results/xsec_putspread_plateau.md`). Δ/gate axes = plateau
      (0.59–0.66 cross); wingΔ 0.15 soft spot (0.43). DTE axis NOT a plateau: 21-DTE craters to
      0.21 cross; **45-DTE beats frozen (0.83/1.03, +$228k, lower maxDD)**. Frozen 30-DTE not a
      selected peak (money left toward 45); short-dated is where the edge dies (forecast h=22
      needs expiry ≥ horizon). Neighborhood mean cross 0.57. 45-DTE = observation w/ multiplicity
      debt, NOT a tuning move.
- [x] **A5 random-pick null** — DONE, stopped early at 10 reps (each rep = full 16-yr backtest,
      ~2.7 min; conclusion settled): null Sharpe 0.16 ± 0.09 vs frozen 0.66 (≈5.5σ). Selection
      pays in realized dollars, not just rank-IC (`results/xsec_putspread_nullpick.md`).
- [x] **A6 crash-beta regression** — DONE (`results/frozen_stats.md`): residual α $199k/yr,
      t=2.75 after SPY β 0.15, crash convexity β 0.45, ΔVIX β 0.12; R²=0.26.
- [x] **A9 recency** — DONE: no decay trend (trailing-2y IC +0.205 vs full +0.248; 2025 +0.30;
      2026 partial +0.09 on 15 cohorts). Honest-Sharpe: bootstrap 90% CI [0.22, 1.15];
      **deflated Sharpe 0.59 (N=18) / 0.45 (N=40)** — the multiplicity number the spec lacked.

## Phase 3 — MTM

- [x] **A3 MTM re-mark** — DONE (`results/frozen_mtm.md`, daily series
      `results/frozen_mtm_daily.csv`): true MTM Sharpe **0.55** vs 0.66 realization-dated (cross);
      daily-path maxDD $502k; worst MTM month 2019-05 −$264k; era 2018–21 drops 0.67→0.51.

## Phase 4 — improvement track

- [x] **I1 fill-capture curve** — DONE (`results/xsec_putspread_lambda.md`): model > pair at every
      λ but alpha decays $37k/yr (IR 0.24, λ=0) → $9k/yr (IR 0.06, λ=1); breakeven ≈ λ=1. Any
      capture below full-crossing is model alpha; shadow-run criterion = demonstrate λ < 1.
- [x] **I2 v1.1 pair-core+overlay** — DONE, **REJECTED** (`results/xsec_putspread_v11.md`):
      cross 0.44 / mid 0.67 (vs frozen 0.66/0.93). Additive sleeves double gross short-vol
      (sleeve corr 0.47) and the pair-less overlay loses QQQ, its top earner ($531k cross on
      ~1250 trades). §8.6's blend works only as two WHOLE books at half size (0.74 cross, §6.6),
      not as trade-level sleeves.
- [ ] **I4 crash-gate note** — RESOLVED BY PRIOR WORK (memory `crashhedge-rejected-2026-07`):
      lever closed; keeper = conditional `vix≥vix3m · φ=0.20 · 0.10Δ/30` hold hedge, Sharpe-neutral
      crash-beta reducer. CAVEAT: the experiment artifacts were never committed (verified against
      git 2026-07-09) — numbers survive only in memory notes; rebuild before re-litigating.
- [x] **I5 OI-cap sizing** (new, from A2) — DONE (`results/xsec_putspread_oicap.md`): frac=0.25 ⇒
      cross **0.89** / mid **1.06**; frac=0.5 ⇒ 0.89/1.08 ($1.95M cross). Removing capacity-
      infeasible size RAISES Sharpe above frozen (0.67/0.93) — the strongest single improvement
      found; PIT-liquidity-based, no performance peeking. Candidate spec change for v1.1.
- [x] **Summary** — DONE: `strategy_backtest/results/HOLE_DIGGING_REPORT.md` (consolidated
      verdicts, deployment implications, multiplicity self-accounting, artifact inventory).
      PROGRAM COMPLETE 2026-07-09. I3 vol-target run last: **REJECTED** (0.55→0.46/0.47, maxDD
      +50% — trailing book-vol is lowest right before vol events; targeting levers into storms;
      `results/frozen_voltarget.md`). No open threads.

## Ops note (user instruction 2026-07-09)

Run heavy jobs ONE AT A TIME (16GB RAM) — chain with `&&`, never parallel background engines.
Queue when plateau finishes: nullpick → lambda → oicap → v11.
GOTCHA: a "stopped/killed" background chain can leave its python child DETACHED and running —
always `ps aux | grep xsec_putspread` and kill leftovers before relaunching, or runs stack up
and OOM the machine (this happened twice on 2026-07-09).

## Conventions

- Interpreter: `.venv/bin/python`, run as `-m strategy_backtest.experiments.<name>` with
  `XS_DATA_ROOT=strategy_backtest/data_wide`.
- Frozen reference numbers: cross 0.66 / $1.92M / maxDD $438k; mid 0.93 / $2.71M; 1524 trades.
- On usage-limit interruption: this file is the resume point; artifacts already on disk are done.
