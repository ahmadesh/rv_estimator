"""PanelHAR-FE — pooled HAR with ticker/group fixed-effect intercepts (catalog model 22).

Track C, Pattern P3. Instead of fitting an independent HAR per (ticker, horizon) like the
`_PerKeyModel` benchmarks, this model **pools** all tickers in the train slice into one OLS of
`log(target_var)` per horizon: a single shared slope vector on the HAR-RS-IV feature block,
plus a per-ticker **fixed-effect intercept** (one dummy per ticker, no global intercept). That
trades the per-ticker degrees of freedom (~each ticker its own slopes) for ~10x as many
observations per slope coefficient, which stabilises the slopes on thin/noisy tickers at the
cost of assuming the *shape* of the HAR response is common across the panel (only the level
differs, captured by the FE intercept).

All the pooling machinery — the FE design matrix, the lstsq fit, the lognormal predictive
quantiles, and the unseen-ticker fallback (test ticker absent from train -> its group-mean
intercept, then the global-mean intercept) — lives in `_base_v2._PooledLinearHAR` /
`fit_pooled` / `pooled_mu` (frozen Wave-0 infra). This file therefore only:

  * names the class / model `name`,
  * declares the pooled feature set `needs`.

No `_derive`/`_AttachMixin` is needed: every column in `needs` is produced centrally by
`features.build_features` from `inputs.parquet` (the HAR roll-means, the realized-semivariance
/ jump aggregates, and the IV transforms) and so arrives on X point-in-time with no rolling
recomputation on the predict slice. Per-horizon pooling; FE intercepts learned on TRAIN only.
No free hyperparameters (plain pooled OLS), hence nothing to tune.
"""

from __future__ import annotations

from candidate_models._base_v2 import _PooledLinearHAR
from rv_eval.features import HAR_RS_FEATURES, IV_FEATURES

# Shared pooled slopes act on the HAR realized-semivariance/jump block + the IV term-structure
# block; the level differences across tickers are absorbed by the fixed-effect intercepts.
_NEEDS = HAR_RS_FEATURES + IV_FEATURES


class PanelHARFE(_PooledLinearHAR):
    name = "PanelHAR-FE"
    needs = _NEEDS
