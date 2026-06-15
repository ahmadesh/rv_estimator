# back-test-data — raw-only data mirror for the put-spread backtest

Self-contained **raw** data for the put-spread strategy backtest (see
`../PUT_SPREAD_STRATEGY_DESIGN.md` §2.2). Copied directly from the Ex-Disk master lakes; **no derived
features, no `inputs.parquet`/`targets.parquet`/`features.parquet`/predictions**. The model pipeline
recomputes realized measures + IV features and trains the HAR forecasters **walk-forward** from these raw
files — nothing here is precomputed downstream of the raw chains/bars.

## Layout

```
back-test-data/
  orats/ticker=<T>/year=<Y>/data.parquet   # ORATS SMV strike snapshots (option chains), 2007→
  minute/ticker=<T>/data.parquet           # Polygon 1-min OHLCV bars, 2003→
  daily/ticker=<T>/data.parquet            # Polygon daily OHLCV (cross-asset macro proxies only)
  corp_actions/{splits,dividends,ticker_events}.parquet
  market_holidays.parquet
```

This mirrors the `rv_eval.config.RAW_*` contract. Point `RAW_ROOT` at this directory to run the pipeline
against it (`RAW_MINUTE/RAW_DAILY/RAW_ORATS/RAW_CORP/RAW_HOLIDAYS` resolve underneath).

## Tickers staged and why

| Group | Tickers | Layers | Purpose |
|---|---|---|---|
| **Core ETF universe** | SPY, QQQ, IWM, XLK, XLF, XLE, TLT, GLD, HYG, EEM | orats + minute | the 10 names the strategy trades; minute → realized vol, orats → IV features + option marks |
| **Index feature sources** | SPX, VIX | orats | build the market VIX block (`vix`/`vix3m`/`vix9d`/`vvix` + slopes) and term-structure gate |
| **Cross-asset proxies** | HYG, LQD, UUP, TLT, SHY | daily | `credit_spread`, `credit_mom`, `usd_mom`, `rates_mom` (`rv_eval/setup/cross_asset.py`) |

## Source (Ex-Disk master lakes)

| Local | Ex-Disk source |
|---|---|
| `orats/` | `/Volumes/Ex-Disk/orats_parquet/ticker=<T>/year=<Y>/` |
| `minute/` | `/Volumes/Ex-Disk/polygon_parquet/us_stocks_sip/minute_aggs_v1/ticker=<T>/` |
| `daily/` | `/Volumes/Ex-Disk/polygon_parquet/us_stocks_sip/day_aggs_v1/ticker=<T>/` |
| `corp_actions/` | `/Volumes/Ex-Disk/polygon_parquet/corporate_actions/` |
| `market_holidays.parquet` | `/Volumes/Ex-Disk/polygon_parquet/reference/market_holidays.parquet` |

Copied with `rsync -a --exclude='._*'` (AppleDouble sidecar files from the exFAT drive are skipped).
Column-level schema docs live in the source lakes' own READMEs (`orats_parquet_readme.md`,
`polygon_parquet_readme.md`). Re-pull any ticker by re-running the same `rsync` from the source above.
