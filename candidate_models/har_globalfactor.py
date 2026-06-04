"""HAR-GVF — HAR augmented with a GLOBAL volatility factor (ITER2 catalog model 24).

A plain log-OLS HAR (`_LinearLogHAR`) whose feature set is extended by ONE systematic
regressor: a market-wide "global volatility factor" (GVF). Because SPX/VIX realized
variance is NOT in `inputs.parquet` (only the 15 scored tickers are; see catalog §4.5),
the GVF is built as the CROSS-SECTIONAL MEAN of `total_rv` across the clean-core ticker
set, per date:

    gvf_t   = mean_{i in CLEAN_CORE} total_rv_{i,t}
    log_gvf = log(max(gvf_t, floor))

This is leak-free in exactly the sense a ticker's own `total_rv` is: it is a
contemporaneous-date aggregate of a quantity known at the end of day t, used to predict
horizon-ahead RV. It carries NO fitted cross-sectional loadings (it is a simple per-date
mean), so there is nothing to leak.

Crucial design choices (catalog §3 model 24, swarm rules):
  * The factor is joined by DATE ALONE — every ticker on a given date sees the same
    `log_gvf`. We achieve this by computing the per-date mean once and cross-joining it
    onto the full key set, so the `_AttachMixin` join-by-(ticker,date) is value-identical
    across tickers.
  * The basket is ALWAYS the clean-core cross-section, even when scoring `hard_cases`.
    Hard names are never added to the basket (they would contaminate / leak into the
    factor). We read `CLEAN_CORE` from `rv_eval.config`, never hardcode it.
  * Built ONCE on the full series via `_AttachMixin._derive(inputs)` and joined, never
    recomputed on the one-month predict slice. The mixin's synthetic-X fallback rebuilds
    the table straight from X (the smoke test, where X already IS the full series and may
    not contain clean-core tickers — see `_gvf_panel` basket fallback).

`needs = HAR_FEATURES + ["log_gvf"]`. No free hyperparameters — inherited `_LinearLogHAR`
does per-(ticker, horizon) log-OLS and lognormal quantiles consistently with the benchmarks.
"""

from __future__ import annotations

import polars as pl

from rv_eval import config as C
from rv_eval.features import HAR_FEATURES
from rv_eval.model_contract import _LinearLogHAR
from candidate_models._base_v2 import _AttachMixin

_GVF_FEATURES = ["log_gvf"]
_FLOOR = 1e-12  # matches features.py log-floor; total_rv is positive but guard anyway.
_KEYS = ["ticker", "date"]


def _gvf_panel(src: pl.DataFrame) -> pl.DataFrame:
    """Build the per-date global volatility factor and broadcast it across tickers.

    The factor is the cross-sectional mean of `total_rv` over the CLEAN_CORE basket on
    each date (a point-in-time, leak-free aggregate). It is computed ONCE and then joined
    back onto the full `(ticker, date)` key set so that on any given date the value is
    identical for every ticker — the `_AttachMixin` then joins by (ticker, date), which is
    value-equivalent to joining by date alone.

    Basket fallback: if NONE of the clean-core tickers are present in `src` (the synthetic
    smoke test uses made-up ticker names), fall back to averaging over whatever tickers ARE
    present, so the factor is still well-defined. In production `src` is `inputs.parquet`,
    which always contains the clean-core names.
    """
    present = set(src["ticker"].unique().to_list())
    basket = [t for t in C.CLEAN_CORE if t in present]
    if not basket:                       # synthetic smoke test: no clean-core names in X
        basket = sorted(present)

    factor = (
        src.filter(pl.col("ticker").is_in(basket))
        .group_by("date")
        .agg(pl.col("total_rv").mean().alias("gvf"))
        .with_columns(
            log_gvf=pl.col("gvf").clip(lower_bound=_FLOOR).log(),
        )
        .select("date", *_GVF_FEATURES)
    )
    # Broadcast onto the full key set so log_gvf is identical across tickers per date.
    keys = src.select(_KEYS).unique()
    return keys.join(factor, on="date", how="left").select(_KEYS + _GVF_FEATURES)


class HARGlobalFactor(_AttachMixin, _LinearLogHAR):
    name = "HAR-GVF"
    needs = HAR_FEATURES + _GVF_FEATURES

    def _derive(self, src: pl.DataFrame) -> pl.DataFrame:
        return _gvf_panel(src)
