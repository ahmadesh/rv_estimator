# Vol-targeted sizing on the frozen book's MTM path (improvement I3)

_EWMA(λ=0.94) book-vol, 1-day lag, m∈[0.3,3.0], σ_target = base full-sample vol (mean-leverage≈1) · generated 2026-07-09_

| arm | mean m | Sharpe(mo) | P&L | maxDD (daily) | 2010–2013 | 2014–2017 | 2018–2021 | 2022–2026 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| base (MTM, m=1) | 1.00 | **0.55** | $1,915,757 | $501,545 | 0.81 | 0.27 | 0.51 | 0.65 |
| vol-target daily | 1.30 | **0.46** | $1,935,904 | $710,848 | 0.70 | 0.46 | 0.29 | 0.44 |
| vol-target monthly | 1.32 | **0.47** | $2,372,942 | $768,532 | 0.73 | 0.55 | 0.20 | 0.55 |

Caveats: portfolio-level approximation (live version scales NEW entries only;
existing spreads can't be resized costlessly); ignores contract rounding and the
group-margin cap. The monthly arm is the implementable read.

