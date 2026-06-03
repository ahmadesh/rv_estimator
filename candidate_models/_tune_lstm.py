"""Tune-once-then-freeze HP search for LSTMRV (MODEL_PLAN.md §4, model 10).

Leakage-safe, pre-OOS only:
  search-train = date <  HPTUNE_VAL_START (2016-01-01)
  validation   = [HPTUNE_VAL_START, OOS_START) = 2016-2017
Subset (bound compute): HPTUNE_DL_SUBSET = (SPY, QQQ, TLT, XLE).

For each grid point: fit one LSTMRV per subset-ticker on search-train only
(windows ending strictly before 2016-01-01), predict h=22 over the validation
block, pool QLIKE@h22 across the subset, keep the lowest.

Run: .venv/bin/python -m candidate_models._tune_lstm
NOTE: standalone tuning artifact; not part of the harness or predictions.
"""

from __future__ import annotations

import itertools
import time

import numpy as np
import polars as pl

from rv_eval import config as C
from rv_eval.features import build_features
from candidate_models.lstm_rv import LSTMRV, WINDOW_FEATURES

H = C.HPTUNE_METRIC_HORIZON          # 22
SUBSET = list(C.HPTUNE_DL_SUBSET)    # SPY, QQQ, TLT, XLE

GRID = list(itertools.product(
    [32, 64, 128],   # hidden
    [1, 2],          # num_layers
    [0.1, 0.2],      # dropout
    [5e-4, 1e-3],    # lr
))
INITIAL = (64, 2, 0.1, 1e-3)


def qlike(rv: np.ndarray, rv_hat: np.ndarray) -> float:
    rv_hat = np.maximum(rv_hat, 1e-18)
    r = rv / rv_hat
    return float(np.mean(r - np.log(r) - 1.0))


def load_split():
    inputs = pl.read_parquet(C.INPUTS_PARQUET).filter(pl.col("ticker").is_in(SUBSET))
    feats = build_features(inputs)
    tgt = (pl.read_parquet(C.TARGETS_PARQUET)
           .filter(pl.col("ticker").is_in(SUBSET))
           .select("ticker", "date", "horizon", "target_var"))

    val_start = pl.lit(C.HPTUNE_VAL_START).str.strptime(pl.Date, "%Y-%m-%d")
    oos_start = pl.lit(C.OOS_START).str.strptime(pl.Date, "%Y-%m-%d")

    # search-train features (X) = strictly before val_start; train targets (y) likewise.
    feats_train = feats.filter(pl.col("date") < val_start)
    y_train = tgt.filter(pl.col("date") < val_start)

    # validation features: include the WINDOW-1 lead-in so a window terminal day in
    # [val_start, oos_start) has its full 60-day history; NEVER read date >= oos_start.
    feats_val_ctx = feats.filter(pl.col("date") < oos_start)
    y_val = (tgt.filter((pl.col("horizon") == H)
                        & (pl.col("date") >= val_start)
                        & (pl.col("date") < oos_start))
             .select("ticker", "date", "target_var"))

    # guards
    import datetime as _dt
    assert feats_train["date"].max() < _dt.date(2016, 1, 1)
    assert y_val["date"].min() >= _dt.date(2016, 1, 1)
    assert y_val["date"].max() < _dt.date(2018, 1, 1)
    assert feats_val_ctx["date"].max() < _dt.date(2018, 1, 1)
    return feats_train, y_train, feats_val_ctx, y_val


def fit_score(feats_train, y_train, feats_val_ctx, y_val, hp) -> float:
    hidden, num_layers, dropout, lr = hp

    class _Tuned(LSTMRV):
        HIDDEN = hidden
        NUM_LAYERS = num_layers
        DROPOUT = dropout
        LR = lr

    model = _Tuned()
    model.fit(feats_train, y_train)
    # predict h=22 over validation context; keep only validation-block terminal days
    pred = model.predict(feats_val_ctx)
    if pred.is_empty():
        return float("inf")
    pred = pred.filter(pl.col("horizon") == H).select("ticker", "date", "rv_hat")

    joined = y_val.join(pred, on=["ticker", "date"], how="inner")
    joined = joined.filter((pl.col("target_var") > 0) & pl.col("rv_hat").is_finite())
    if joined.height < 10:
        return float("inf")
    rv = joined["target_var"].to_numpy().astype(np.float64)
    rv_hat = joined["rv_hat"].to_numpy().astype(np.float64)
    return qlike(rv, rv_hat)


def main(full: bool = True):
    feats_train, y_train, feats_val_ctx, y_val = load_split()
    print(f"search-train rows={feats_train.height}  val targets={y_val.height}  "
          f"val dates {y_val['date'].min()}..{y_val['date'].max()}  subset={SUBSET}")
    grid = GRID if full else [INITIAL]
    results = []
    for hp in grid:
        t0 = time.time()
        q = fit_score(feats_train, y_train, feats_val_ctx, y_val, hp)
        dt_ = time.time() - t0
        tag = "  <- initial" if hp == INITIAL else ""
        results.append((q, hp))
        print(f"  hidden={hp[0]:>3} layers={hp[1]} dropout={hp[2]} lr={hp[3]:.0e}  "
              f"QLIKE@h22={q:.6f}  ({dt_:.1f}s){tag}")
    results.sort(key=lambda r: r[0])
    best_q, best_hp = results[0]
    init_q = next((q for q, hp in results if hp == INITIAL), None)
    print("\n=== RESULT ===")
    print(f"WINNER: hidden={best_hp[0]} num_layers={best_hp[1]} dropout={best_hp[2]} "
          f"lr={best_hp[3]}  QLIKE@h22={best_q:.6f}")
    if init_q is not None:
        print(f"INITIAL (64,2,0.1,1e-3): QLIKE@h22={init_q:.6f}")


if __name__ == "__main__":
    import sys
    main(full="--initial" not in sys.argv)
