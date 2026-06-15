"""HAR-RS-IV-Q — Modern HAR (MODEL_PLAN.md §4 model 7).

The research doc's recommended primary / strongest *linear* baseline: a plain
log-OLS HAR that stacks together every cheap, informative regressor the harness
already bakes — the semivariance/jump HAR block (Patton & Sheppard 2015), the
implied-vol block (IV level/slope/skew + VIX term structure + VVIX), and the
realized-quarticity attenuation term (`sqrt_rq`, Bollerslev-Patton-Quaedvlieg
2016 HARQ). No free hyperparameters: the inherited `_LinearLogHAR` machinery
fits per-(ticker, horizon) OLS of log(target_var) on `needs` and emits lognormal
quantiles consistently with the benchmarks.
"""

from __future__ import annotations

from strategy_backtest.pipeline.features import HAR_RS_FEATURES, IV_FEATURES
from strategy_backtest.pipeline.model_contract import _LinearLogHAR


def _dedup(seq: list[str]) -> list[str]:
    """Drop repeats while preserving first-seen order."""
    seen: set[str] = set()
    return [c for c in seq if not (c in seen or seen.add(c))]


class HARRSIVQ(_LinearLogHAR):
    name = "HAR-RS-IV-Q"
    needs = _dedup(HAR_RS_FEATURES + IV_FEATURES + ["sqrt_rq"])
