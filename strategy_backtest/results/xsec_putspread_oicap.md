# OI-capped sizing (improvement I5 — closes capacity hole A2)

_frozen book + one rule: contracts ≤ OI_FRAC × min(leg OI) at entry; zero-contract trades skipped · generated 2026-07-09_

| OI_FRAC | trades | cross Sharpe | cross P&L | cross maxDD | mean margin/trade | mid Sharpe | mid P&L |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0.10 | 1524 | **0.83** | $1,464,336 | $188,137 | $20,204 | **0.97** | $1,741,095 |
| 0.25 | 1525 | **0.89** | $1,774,668 | $218,472 | $25,261 | **1.06** | $2,140,257 |
| 0.50 | 1524 | **0.89** | $1,951,066 | $243,611 | $29,027 | **1.08** | $2,395,329 |
| ∞ (frozen) | 1525 | **0.67** | $1,919,908 | $433,644 | $39,995 | **0.93** | $2,709,077 |
