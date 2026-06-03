"""HARQ — Quarticity-Corrected HAR (MODEL_PLAN.md §4 model 4).

Plain log-OLS HAR augmented with the realized-quarticity term `sqrt_rq`, which
proxies the measurement-error magnitude of the daily RV component (Bollerslev,
Patton, Quaedvlieg 2016). No free hyperparameters — inherited log-OLS machinery.
"""

from __future__ import annotations

from rv_eval.features import HARQ_FEATURES
from rv_eval.model_contract import _LinearLogHAR


class HARQ(_LinearLogHAR):
    name = "HARQ"
    needs = HARQ_FEATURES
