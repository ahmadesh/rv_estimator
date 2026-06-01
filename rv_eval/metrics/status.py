"""Model status assignment (eval plan §9), decided on the forecasting doc alone.

  Rejected           — worse forecast accuracy or unstable calibration.
  Research candidate — improves ≥1 forecast target/regime without breaking the others.
  (Production candidate requires the trading doc and is out of scope here.)

A candidate is judged against a baseline (default HAR); RW/EWMA/HAR are reference benchmarks.
"""

from __future__ import annotations

import polars as pl

from rv_eval import config as C

REFERENCE = {"RW", "EWMA", "HAR"}
BASELINE = "HAR"
_WORSE_MARGIN = 0.05   # >5% higher QLIKE on a horizon counts as "broken"

_SCHEMA = ["model", "n_improved", "n_broke", "improved_primary", "broke_primary",
           "beats_iv", "trap", "mean_qlike", "status"]


def assign(tier1_by_h: pl.DataFrame, iv_diag: pl.DataFrame,
           flags: pl.DataFrame, baseline: str = BASELINE) -> pl.DataFrame:
    """Return per-model status + the evidence behind it.

    tier1_by_h: columns model, horizon, qlike (pooled across tickers).
    iv_diag:    columns model, horizon, qlike_gain_vs_iv.
    flags:      columns model, horizon, trap_flag.

    Verdict policy (§9), anchored on the **primary horizon** (`config.PRIMARY_HORIZON`) because
    that is the horizon the book trades — a model that wins at h=22 but is >5% worse at h=1 should
    not be rejected for the off-horizon, and vice-versa:

      benchmark           — RW / EWMA / HAR (reference yardsticks).
      research_candidate  — does NOT break the primary horizon, is not the post-shock §6 trap,
                            improves QLIKE somewhere (primary or any horizon), AND adds information
                            beyond IV² (`beats_iv`, the §5 bar). `n_broke` on off-horizons is
                            reported but does not by itself reject.
      rejected            — breaks the primary horizon, springs the §6 trap, or fails the bars above.

    If the baseline model isn't in tier1_by_h, every model is marked ``no_baseline`` rather than
    silently mass-rejecting (which is what a naïve null-join would do).
    """
    primary = C.PRIMARY_HORIZON
    models_present = tier1_by_h["model"].unique().to_list() if tier1_by_h.height else []
    if baseline not in models_present:
        return (
            tier1_by_h.group_by("model")
            .agg(mean_qlike=pl.col("qlike").mean())
            .with_columns(
                n_improved=pl.lit(None, dtype=pl.UInt32),
                n_broke=pl.lit(None, dtype=pl.UInt32),
                improved_primary=pl.lit(None, dtype=pl.Boolean),
                broke_primary=pl.lit(None, dtype=pl.Boolean),
                beats_iv=pl.lit(None, dtype=pl.Boolean),
                trap=pl.lit(None, dtype=pl.Boolean),
                status=pl.lit("no_baseline"),
            )
            .select(_SCHEMA)
            .sort("mean_qlike")
        )
    base = (
        tier1_by_h.filter(pl.col("model") == baseline)
        .select("horizon", pl.col("qlike").alias("qlike_base"))
    )
    j = tier1_by_h.join(base, on="horizon", how="left").join(
        iv_diag.select("model", "horizon", "qlike_gain_vs_iv"),
        on=["model", "horizon"], how="left",
    ).join(flags.select("model", "horizon", "trap_flag"), on=["model", "horizon"], how="left")

    improved = pl.col("qlike") < pl.col("qlike_base")
    broke = pl.col("qlike") > pl.col("qlike_base") * (1 + _WORSE_MARGIN)
    at_primary = pl.col("horizon") == primary
    per_model = j.group_by("model").agg(
        n_improved=improved.sum(),
        n_broke=broke.sum(),
        improved_primary=(improved & at_primary).any(),
        broke_primary=(broke & at_primary).any(),
        beats_iv=(pl.col("qlike_gain_vs_iv") > 0).any(),
        trap=pl.col("trap_flag").fill_null(False).any(),
        mean_qlike=pl.col("qlike").mean(),
    )

    def _status(row: dict) -> str:
        if row["model"] in REFERENCE:
            return "benchmark"
        if row["broke_primary"] or row["trap"]:
            return "rejected"
        if (row["improved_primary"] or row["n_improved"] >= 1) and row["beats_iv"]:
            return "research_candidate"
        return "rejected"

    per_model = per_model.with_columns(
        status=pl.struct(["model", "improved_primary", "broke_primary", "n_improved",
                          "beats_iv", "trap"]).map_elements(_status, return_dtype=pl.Utf8)
    )
    return per_model.select(_SCHEMA).sort("mean_qlike")
