"""HAR-RS — Semivariance HAR + jump (MODEL_PLAN.md §4 model 5).

Plain log-OLS HAR augmented with realized-semivariance components and a jump
term (Patton & Sheppard 2015). The daily HAR lag is split into its signed
realized-semivariance pieces (`rs_minus_5d`, `rs_plus_5d`) and a separate jump
component (`jump_5d`), which lets downside variation predict future RV more
strongly than upside variation. No free hyperparameters — the inherited
`_LinearLogHAR` machinery does per-(ticker, horizon) OLS of log(target_var) on
`needs` and generates lognormal quantiles consistently with the benchmarks.
"""

from __future__ import annotations

from rv_eval.features import HAR_RS_FEATURES
from rv_eval.model_contract import _LinearLogHAR


class HARRS(_LinearLogHAR):
    name = "HAR-RS"
    needs = HAR_RS_FEATURES
