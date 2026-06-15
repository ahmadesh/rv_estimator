# Backtest Data Specification — raw-only mirror for the put-spread backtest

_Data reference for the put-spread backtest · companion to `PUT_SPREAD_STRATEGY_DESIGN.md`_

> **Purpose.** Define the data layer for the put-spread backtest: a **raw-only** mirror under
> `strategy_backtest/back-test-data/` from which the model pipeline rebuilds features and trains
> walk-forward. This doc owns everything about *where the data lives, what is staged, and why*; the
> strategy doc owns *what the book does with it*. Provenance/copy commands also live in
> `back-test-data/README.md`.

---

## 1. Principle — raw only, features built walk-forward

**This backtest consumes no pre-built feature/target/forecast file.** The previously-used processed
artifacts (`execution/data/inputs.parquet`, `features.parquet`, `targets.parquet`, `predictions/*.parquet`)
are **deliberately not used** — they were computed once over a fixed window and are not a valid input to a
walk-forward backtest (they bake in a single train/OOS split and would leak). Instead the pipeline
**recomputes realized measures + IV features and trains the HAR forecasters per fold** (measurement →
IV-feature → HAR-fit, re-run on each expanding/rolling window; strategy doc §3). Nothing downstream of the
raw chains and raw bars is precomputed or cached ahead.

## 2. Layout

A per-ticker subset copied directly from the Ex-Disk master lakes, mirroring the `rv_eval.config.RAW_*`
contract so the existing measurement/feature code reads it unchanged once `RAW_ROOT` is pointed here:

```
back-test-data/
  orats/ticker=<T>/year=<Y>/data.parquet   # ORATS SMV strike snapshots (option chains), 2007→
  minute/ticker=<T>/data.parquet           # Polygon 1-min OHLCV bars, 2003→
  daily/ticker=<T>/data.parquet            # Polygon daily OHLCV (cross-asset macro proxies only)
  corp_actions/{splits,dividends,ticker_events}.parquet
  market_holidays.parquet
```

| Layer | Path | Source on Ex-Disk | Content | Coverage | Tickers staged |
|---|---|---|---|---|---|
| **Option chains** | `orats/ticker=<T>/year=<Y>/` | `orats_parquet/ticker=<T>/year=<Y>/` | per-strike bid/ask, IV, **delta/gamma/theta/vega**, OI, volume, `stkPx` | **2007 →** | 10 core + **SPX**, **VIX** |
| **Minute bars** | `minute/ticker=<T>/` | `polygon_parquet/us_stocks_sip/minute_aggs_v1/ticker=<T>/` | 1-min OHLCV (`window_start` UTC ns, OHLC, volume, transactions) | **2003 →** | 10 core |
| **Daily bars** | `daily/ticker=<T>/` | `polygon_parquet/us_stocks_sip/day_aggs_v1/ticker=<T>/` | daily OHLCV — cross-asset macro proxies only | 2003 → | HYG, LQD, UUP, TLT, SHY |
| **Corp actions** | `corp_actions/*.parquet` | `polygon_parquet/corporate_actions/` | split ratios + cash dividends (overnight adjustment) | full | all (ticker column) |
| **Holidays** | `market_holidays.parquet` | `polygon_parquet/reference/` | market-holiday / half-day calendar (session cross-check) | full | — |

Total staged ≈ **11.7 GB** (ORATS ≈ 11 GB, minute ≈ 0.6 GB). Verified: all tickers present, parquet
readable, ORATS row-counts match Ex-Disk exactly, no AppleDouble/`.DS_Store` leakage.

## 3. Why each ticker is staged

| Group | Tickers | Layers | Purpose |
|---|---|---|---|
| **Core ETF universe** | SPY, QQQ, IWM, XLK, XLF, XLE, TLT, GLD, HYG, EEM | orats + minute | the names the strategy trades; minute → realized vol, orats → IV features + option marks |
| **Index feature sources** | SPX, VIX | orats | build the market VIX block (`vix`/`vix3m`/`vix9d`/`vvix` + slopes) — IV-aware HAR component + term-structure gate (`rv_eval/setup/iv_features.py`) |
| **Cross-asset proxies** | HYG, LQD, UUP, TLT, SHY | daily | `credit_spread`, `credit_mom`, `usd_mom`, `rates_mom` (`rv_eval/setup/cross_asset.py`) |

The ORATS chain columns (`delta`, `cBidPx/cAskPx/pBidPx/pAskPx`, `cMidIv/pMidIv`, `cOi/pOi`, `cVolu/pVolu`,
`stkPx`) are exactly what strike-selection, fills, and the liquidity filters need; greeks are
vendor-supplied, so no re-pricing is required. The realized-vol inputs (5-min RV, bipower, semivariance,
quarticity, overnight) are recomputed from the staged minute bars per fold by `measurement.py`.

> **Note (SPX/VIX minute):** only ORATS is staged for SPX/VIX — they are *feature sources*, not traded, and
> `measurement.py` computes RV only for scored tickers. If SPX is ever *traded* (or its RV needed), add its
> minute bars with the same `rsync` from `minute_aggs_v1/ticker=SPX/`.

## 4. Pointing the pipeline at the mirror

`rv_eval.config` derives `RAW_ROOT` from `DATA_ROOT/raw` and resolves `RAW_MINUTE`, `RAW_DAILY`,
`RAW_ORATS`, `RAW_CORP`, `RAW_HOLIDAYS` underneath. For this backtest, set
`RAW_ROOT → strategy_backtest/back-test-data/` (leave `RV_EXDISK` as the master fallback). No
`inputs.parquet`/`targets.parquet` is written ahead of time — the walk-forward driver materializes only the
per-fold slice it needs.

## 5. Provenance / re-pull

Copied with `rsync -a --exclude='._*'` (AppleDouble sidecars from the exFAT drive skipped). Compacted
per-ticker lakes already exist on Ex-Disk under `polygon_parquet/us_stocks_sip/{minute,day}_aggs_v1/` (the
`polygon_parquet` tree, **not** the raw flat-file CSVs under `polygon/`), so staging is direct file copies —
no multi-hour re-extraction. Re-pull any ticker by re-running the same `rsync` from the source in §2.
Column-level schema docs: the source lakes' own READMEs (`orats_parquet_readme.md`,
`polygon_parquet_readme.md`); per-folder summary in `back-test-data/README.md`.
