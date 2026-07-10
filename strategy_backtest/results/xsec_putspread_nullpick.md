# Random-pick P&L null (hole-dig A5) — stopped early, conclusion settled

_10 completed replications (of a planned 40); per weekly cohort the score-rank was replaced by a
random permutation before the identical tradeable-walk; score>0 gate, engine, sizing, cross fills
all frozen · generated 2026-07-09_

**Run cut short deliberately**: each replication re-runs the full 16-year backtest (~2.7 min,
I/O-bound), and the answer was already unambiguous:

| quantity | value |
| --- | --- |
| null Sharpe (cross), mean ± sd over 10 reps | **0.16 ± 0.09** |
| frozen book (cross) | **0.66** |
| separation | ≈ 5.5 null-sd above the null mean; no rep came near it |

**Read:** picking the 2 *richest* gated names beats picking 2 *random* gated names decisively in
realized dollars, not just in rank-IC. Combined with §6.6 (the fixed SPY/QQQ pair *ties* the frozen
book at cross fills), the picture is: random selection within the gated cohort is much worse than
both — the pair baseline works because SPY/QQQ are the two most liquid, cheapest-to-trade names,
not because selection doesn't matter. The model's selection edge is real; the pair's execution
edge is real too; they are different edges.

_Repro: `experiments/xsec_putspread_nullpick.py` (XS_NULL_REPS to extend; per-rep CSV written only
at completion, so this early-stop record is from the run log)._
