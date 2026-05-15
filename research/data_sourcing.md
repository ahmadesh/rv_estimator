# Data Sourcing — Recommendations

This is the practical "what to actually buy/subscribe to" companion to
`rv_forecasting_methods.md`. Scoped to a single-developer research/trading
setup, not an institutional data stack.

## 1. Intraday equity bars (for RV measurement)

**Recommendation: Polygon.io Stocks Advanced.**

- 5-minute aggregate bars on every US-listed equity/ETF in our universe, full
  history (≥10y on the major names; ≥5y on newer like IBIT/MSTU/UVIX).
- REST + flat-file delivery. Good Python SDK.
- ~$199/mo retail tier (verify current pricing). Materially cheaper than
  Databento or AlgoSeek for the same data quality at this resolution.
- 5-minute is sufficient: at this frequency, microstructure-noise bias on
  realized variance is small, and the gain from going to 1-min + realized
  kernel is single-digit-% on point estimates of daily RV — not worth the cost
  step-up unless we discover a specific problem.

**Alternatives in order:**
- **Databento** — best engineering / latency story, more expensive. Pick this
  if we later want sub-5-min or order-book data.
- **AlgoSeek** — high quality, batch-heavy. Better if we want adjusted minute
  bars including corporate actions baked in.
- **Free fallback** — yfinance gives 5-min only for last ~60 days. Not viable
  for building history. Useable only for live monitoring after the model is
  trained.

**What to download for each ticker in `universe.yml`:**
- 5-min bars, RTH (09:30–16:00 ET), close-to-close adjusted for splits and
  dividends.
- Daily OHLCV separately for overnight-return calculation and as a sanity
  cross-check.
- 7+ years where available. For newer ETFs (IBIT, ETHA, MSTU, BITX, UVIX,
  ASHR newer wrappers): use what exists.

## 2. Options / implied vol data

This is the harder vendor decision. Three workable paths in increasing cost
and quality:

### Path A — minimal, IV-from-chain ourselves: **Polygon.io Options Starter/Advanced**

- Historical EOD option chains per ticker.
- Compute per-ticker 30-day ATM IV and term-structure slope ourselves using
  Black-Scholes inversion or the VIX whitepaper algorithm.
- ~$199–$499/mo on top of stocks.
- More implementation work but flexible.

### Path B — IV pre-computed, retail-friendly: **ORATS Data API (Historical)**

- Per-ticker IV (30d ATM, 60d, 90d), term slope, skew, greeks, all
  pre-computed. ~$240/mo for the historical tier.
- Saves us from implementing the VIX-style integration ourselves.
- Recommended path for fastest time-to-model.

### Path C — gold standard: **OptionMetrics IvyDB US**

- Academic / institutional database. Daily implied vol surface per ticker by
  delta and tenor.
- Requires academic affiliation or institutional pricing (well into $XX,XXX/yr).
- Skip unless we have access via an institution.

**Recommendation: start with Path B (ORATS).** If budget is the constraint,
fall back to Path A (Polygon Options + our own IV calculation) — the
algorithms are well-documented and the engineering is finite.

For the systematic regressors (VIX, VIX3M, skew indices) we can pull free
from Cboe historical files: https://www.cboe.com/tradable_products/vix/

## 3. Macro & supporting data

All free:
- **FRED** (St. Louis Fed): risk-free rate (DGS3MO), 2s10s, USD index (DTWEXBGS),
  credit spreads (BAMLH0A0HYM2 for HY, BAMLC0A0CMEY for IG).
- **Cboe**: VIX, VIX3M, VIX9D, VVIX, SKEW.
- **CME Group**: term structure of VIX futures (for downstream regime signal).
- **SEC EDGAR / ETF.com**: ETF holdings (used only if we extend to single
  names later).

## 4. Special-case tickers in our universe

Several universe tickers will have data gaps or quality issues:

| Ticker | Issue | Mitigation |
|---|---|---|
| IBIT, FBTC, ARKB, BITB, HODL, BTCO | Spot BTC ETFs, launched Jan 2024 | Only ~2y of history. Use BITO (Oct 2021) or GBTC pre-conversion as a longer-history proxy in the BTC cluster. |
| MSTU | Launched Sept 2024, ~8 months of data | Too short for HAR. Use MSTR as the underlying proxy with leverage adjustment, or skip MSTU until enough history accumulates. |
| ETHA | Spot ETH ETF, launched July 2024 | Similar problem. Use ETHE pre-conversion or skip until history grows. |
| UVIX | Volatility Shares launch March 2022, ~4y data | Workable. |
| MSOS | Very high IV, thin options | Compute IV but expect noisy regressor. Consider widening windows. |
| AAAU, SIVR, SGOL, GLDM | Thin options, low AUM | Skip per-ticker IV; use GLD/SLV as group proxy in the precious-metals cluster (universe.yml already implies this). |
| DRAM, SILJ, BITO | Marginal option liquidity | Same as above — borrow IV from group-leader ticker. |

**General rule:** when a ticker's own option chain is too thin to compute
stable model-free IV, substitute the group's most-liquid ticker's IV as the
regressor. This is consistent with the user's universe rule that within a
group, tickers share the same underlying vol driver.

## 5. Total monthly cost estimate (retail tier)

| Item | Cost |
|---|---|
| Polygon.io Stocks Advanced | ~$199/mo |
| ORATS Data API | ~$240/mo |
| FRED, Cboe, CME free data | $0 |
| Compute (single machine, no cloud) | $0–$50/mo if local |
| **Total** | **~$440/mo** |

If budget is tight: Polygon Stocks + Polygon Options + DIY IV calculation
drops this to ~$398/mo at the cost of a few weeks of implementation work.

## 6. Storage & ingestion

- ~5 years of 5-min bars × ~70 tickers × ~6.5 trading hours × 12 bars/hr ≈
  6M rows. Trivial. Parquet on disk; DuckDB or Postgres for queries.
- Option chains are bigger (every strike, every expiry, every day) — easily
  100M+ rows over 5y. DuckDB on parquet handles this without issue on a laptop.

## 7. Validation against published values

Before trusting our measurement layer, validate daily RV(5-min) for SPY over
2010–2020 against published values in the Oxford-Man Realized Library
(now hosted by the Quant Strats lab at Stevens Institute, formerly at Oxford).
This is a free academic dataset with reference RV series for major indices.
Discrepancy >5% on any well-behaved day signals a bug in our intraday
pipeline.

URL: https://realized.oxford-man.ox.ac.uk/data — verify currently hosted.
