"""Tune-once-then-freeze HP search for XGBHARRSIV (MODEL_PLAN.md §4, model 9).

Leakage-safe, pre-OOS only:
  search-train = date <  HPTUNE_VAL_START (2016-01-01)
  validation   = [HPTUNE_VAL_START, OOS_START) = 2016-2017
Fit ONE global booster (pooled across SCORED_TICKERS) at h=22 per grid point,
score pooled QLIKE @ h=22 on the validation block, keep the lowest.

Run: .venv/bin/python -m candidate_models._tune_xgb
NOTE: standalone tuning artifact; not part of the harness or predictions.
"""

from __future__ import annotations

import itertools

import numpy as np
import polars as pl
import xgboost as xgb

from rv_eval import config as C
from rv_eval.features import build_features, HAR_RS_FEATURES, IV_FEATURES

NEEDS = list(dict.fromkeys(HAR_RS_FEATURES + IV_FEATURES + ["sqrt_rq"]))
H = C.HPTUNE_METRIC_HORIZON          # 22
VAL_TAIL_FRAC = 0.10
CAP = 2000
ESR = 50

GRID = list(itertools.product(
    [3, 4, 6],            # max_depth
    [0.03, 0.05, 0.1],    # learning_rate
    [5, 10, 20],          # min_child_weight
))
INITIAL = (4, 0.05, 10)


def qlike(rv: np.ndarray, rv_hat: np.ndarray) -> float:
    rv_hat = np.maximum(rv_hat, 1e-18)
    r = rv / rv_hat
    return float(np.mean(r - np.log(r) - 1.0))


def load_split():
    inputs = pl.read_parquet(C.INPUTS_PARQUET).filter(
        pl.col("ticker").is_in(list(C.SCORED_TICKERS))
    )
    feats = build_features(inputs)
    tgt = (pl.read_parquet(C.TARGETS_PARQUET)
           .filter((pl.col("horizon") == H) & pl.col("ticker").is_in(list(C.SCORED_TICKERS)))
           .select("ticker", "date", "target_var"))
    df = feats.join(tgt, on=["ticker", "date"], how="inner")
    df = df.drop_nulls(NEEDS + ["target_var"]).filter(pl.col("target_var") > 0)

    val_start = pl.lit(C.HPTUNE_VAL_START).str.strptime(pl.Date, "%Y-%m-%d")
    oos_start = pl.lit(C.OOS_START).str.strptime(pl.Date, "%Y-%m-%d")
    train = df.filter(pl.col("date") < val_start).sort("ticker", "date")
    val = df.filter((pl.col("date") >= val_start) & (pl.col("date") < oos_start))
    # guard: never read OOS during tuning
    assert val["date"].max() < df.filter(pl.col("date") >= oos_start)["date"].min() \
        if df.filter(pl.col("date") >= oos_start).height else True
    assert val["date"].min() >= __import__("datetime").date(2016, 1, 1)
    assert val["date"].max() < __import__("datetime").date(2018, 1, 1)
    return train, val


def fit_score(train: pl.DataFrame, val: pl.DataFrame, hp) -> float:
    md, lr, mcw = hp
    # time-ordered within-search-train tail for early stopping (pooled, by date)
    tr = train.sort("date")
    n = tr.height
    n_tail = max(1, int(round(n * VAL_TAIL_FRAC)))
    cut_date = tr["date"][n - n_tail]
    core = tr.filter(pl.col("date") < cut_date)
    tail = tr.filter(pl.col("date") >= cut_date)
    if core.height < 100 or tail.height < 10:
        core, tail = tr[:-n_tail], tr[-n_tail:]

    Xc = core.select(NEEDS).to_numpy().astype(np.float64)
    yc = np.log(core["target_var"].to_numpy().astype(np.float64))
    Xt = tail.select(NEEDS).to_numpy().astype(np.float64)
    yt = np.log(tail["target_var"].to_numpy().astype(np.float64))

    model = xgb.XGBRegressor(
        n_estimators=CAP, early_stopping_rounds=ESR,
        objective="reg:squarederror", max_depth=md, learning_rate=lr,
        min_child_weight=mcw, subsample=0.8, colsample_bytree=0.8,
        reg_lambda=1.0, tree_method="hist", seed=0,
    )
    model.fit(Xc, yc, eval_set=[(Xt, yt)], verbose=False)
    s = float(np.std(yt - model.predict(Xt)))
    s = max(s, 1e-3)

    Xv = val.select(NEEDS).to_numpy().astype(np.float64)
    rv = val["target_var"].to_numpy().astype(np.float64)
    rv_hat = np.exp(model.predict(Xv).astype(np.float64) + 0.5 * s * s)
    return qlike(rv, rv_hat)


def main():
    train, val = load_split()
    print(f"search-train rows={train.height}  validation rows={val.height}  "
          f"val dates {val['date'].min()}..{val['date'].max()}")
    results = []
    for hp in GRID:
        q = fit_score(train, val, hp)
        results.append((q, hp))
        tag = "  <- initial" if hp == INITIAL else ""
        print(f"  max_depth={hp[0]} lr={hp[1]} mcw={hp[2]:>2}  QLIKE@h22={q:.6f}{tag}")
    results.sort()
    best_q, best_hp = results[0]
    init_q = next(q for q, hp in results if hp == INITIAL)
    print("\n=== RESULT ===")
    print(f"WINNER: max_depth={best_hp[0]} learning_rate={best_hp[1]} "
          f"min_child_weight={best_hp[2]}  QLIKE@h22={best_q:.6f}")
    print(f"INITIAL (4,0.05,10): QLIKE@h22={init_q:.6f}")


if __name__ == "__main__":
    main()
