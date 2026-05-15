# Forward Realized Volatility Forecasting — Methods Survey

**Context:** Short-put / VRP system. Decision rule: sell puts when IV > predicted RV
over the option's horizon (~30 days). The forecast we need is *forward realized
volatility over a fixed horizon* (1d, 5d, 22d), with 22d (monthly) the primary
target. Universe is liquid ETFs (see `data/universe.yml`).

The "edge" we are trying to capture is the variance risk premium (VRP): on broad
US equity, IV is ~9% higher than RV on average and is positive 85–90% of the
time. So the model only needs to be **better than IV's own implicit RV forecast**
to drive position sizing — it does not need to be the world's best
volatility model in isolation.

This shapes what "strong" means here:
- Calibration matters more than raw R². A model that systematically over-
  predicts RV will leave VRP edge on the table; one that under-predicts will
  short premium into stress.
- Asymmetry matters: downside vol is what kills short puts, so models that
  exploit realized semivariance / leverage effects are preferred.
- Horizon: monthly. Short-horizon SOTA (1-day) does not transfer cleanly.

---

## 1. The two-step decomposition

Any practical RV forecasting pipeline has two layers:

1. **Measurement** — turn raw price data into a clean RV estimate per day. This
   is its own modeling problem because of jumps and microstructure noise.
2. **Forecasting** — model the dynamics of the daily RV series and project
   forward to horizon h.

Skipping #1 and using close-to-close squared returns is the single biggest
quality drop you can make in this pipeline. Intraday RV is roughly an order of
magnitude less noisy than daily squared returns and is what every modern paper
benchmarks against.

---

## 2. Measurement: how to build the daily RV target

| Estimator | What it does | When to use | Data needed |
|---|---|---|---|
| **Realized Variance (RV)** — sum of squared 5-min intraday log returns | Standard target. Good bias/variance tradeoff at 5 min. | Default measurement. | 5-min trade or mid prices, full RTH |
| **Bipower Variation (BV)** — Barndorff-Nielsen & Shephard 2004 | Estimates the **continuous** component only — robust to jumps. RV − BV ≈ jump variation. | Splitting jump vs continuous so the forecaster can treat them separately. | Same 5-min data |
| **Realized Semivariance (RS+ / RS−)** — Barndorff-Nielsen et al. 2010 | Splits RV into upside-only and downside-only contributions. | **Critical for short-put.** Downside semivariance has much stronger predictive power for future RV than upside. | Same 5-min data |
| **Realized Quarticity (RQ)** — sum of 4th-power returns × scaling | Measures the variance of the RV estimator itself (vol of vol on the estimate). | Plugs into HARQ to downweight noisy past observations. | Same 5-min data |
| **Realized Kernel (RK)** — Barndorff-Nielsen, Hansen, Lunde, Shephard 2008 | Asymptotically efficient under microstructure noise. Lets you sample at higher frequency than 5 min. | If using sub-5-min data (1-min or tick). At 5 min the gain over RV is small. | 1-min or tick data |
| **Two-Scale RV (TSRV)** — Zhang, Mykland, Aït-Sahalia 2005 | Noise-robust alternative to RK using two sampling scales. | Alternative to RK at high frequency. | Tick data |
| **Range-based (Garman-Klass, Parkinson, Yang-Zhang)** | Estimates daily variance from OHLC. Uses ~4× less data than RV but is unbiased and efficient compared to squared close-to-close return. | Fallback when intraday data is unavailable, or sanity check. | Daily OHLC only |

**Practical default:** RV(5-min) on RTH data, plus BV, RS±, RQ computed from the
same series. Compute overnight (close-to-open) squared return separately and
add it to the day's RV with a scaling factor (Hansen-Lunde 2005). This whole
block is one Python module.

---

## 3. Forecasting models — ranked by strength/complexity tradeoff

### 3.1 HAR family (Corsi 2009) — the workhorse

HAR-RV regresses today's RV on averages over the past day, week (5d), and month
(22d):

    RV_t = β₀ + β_d RV_{t-1} + β_w RV̄_{t-5,t-1} + β_m RV̄_{t-22,t-1} + ε_t

It approximates long memory in volatility with three components representing
short-, medium-, and long-horizon traders. For h-step forecasts you either:
- **Direct method:** regress `RV_{t+1,t+h}` (sum of next h daily RVs) on
  features at t. Recommended for our 22-day target.
- **Iterated method:** forecast 1-step and chain. Has bias issues at long h.

HAR is the standard benchmark and is *very hard to beat* on broad equity. Most
"new" RV papers report a 5–15% MSE improvement over HAR — often inside
noise. So the bar is: start with HAR and add only what survives a Diebold-
Mariano test on held-out data.

**Variants worth implementing:**

| Variant | What it adds | Why useful for us |
|---|---|---|
| **HAR-CJ** | Splits past RV into continuous (BV) and jump (RV-BV) components. Continuous component has higher persistence. | Jumps don't predict future vol the way smooth vol does. |
| **HAR-RS** | Splits past RV into RS+ and RS− (semivariance). Coefficient on RS− is much larger. | **Most useful for puts.** Bad-news vol predicts future vol; good-news vol largely doesn't. |
| **HARQ** (Bollerslev, Patton, Quaedvlieg 2016) | Interaction term β_d · √RQ_t lets the model downweight RV_{t-1} when it was a noisy estimate. | Standard fix for measurement-error attenuation bias. |
| **HARX / HAR-IV** | Adds exogenous regressors: implied vol, VIX, VIX term-structure slope, credit spread, etc. | **The biggest single win** at the 22-day horizon. See §3.3. |

A compact "modern HAR" specification combining the above:

    RV_{t+1,t+22} = β₀ + (β_d + β_dq √RQ_t) RV_{t-1}
                  + β_w⁻ RS̄−_{w} + β_w⁺ RS̄+_{w}
                  + β_m RV̄_{m} + β_j JV̄_{w}
                  + γ_iv IV_t^{30d}
                  + γ_vix ΔVIX_t + γ_ts (VIX_3m − VIX_t) + ε

This is the recommended baseline. Linear, transparent, fast to fit, easy to
diagnose, and routinely competitive with ML in published horse races
especially at the monthly horizon.

**Data needed:** intraday 5-min returns (for RV/BV/RS/RQ), daily OHLC
(overnight return), per-ticker 30-day ATM IV or model-free IV, VIX index plus
3-month VIX (VIX3M) for term-structure slope.

### 3.2 GARCH family — useful as a sanity-check baseline

Pure GARCH(1,1) on daily returns is the textbook benchmark. It is dominated by
HAR-RV when you have intraday data, because GARCH wastes information by
estimating volatility from a single number per day. Still worth running because
some tickers in our universe (cannabis MSOS, junior miners SILJ) have weak
option chains and possibly thin intraday data — there GARCH may be the most
defensible model.

- **GARCH(1,1)** — baseline.
- **EGARCH / GJR-GARCH** — adds leverage effect (downside shocks raise vol more
  than upside). Material for equity ETFs.
- **Realized GARCH** (Hansen, Huang, Shek 2012) — joint model of returns and
  a realized measure; bridges GARCH and HAR. Beats plain GARCH; usually
  comparable to a well-specified HAR. Good if you want a single likelihood-
  based model that gives distributional forecasts directly.

**Data needed:** daily close-to-close returns. Realized GARCH adds the daily RV
series.

### 3.3 Implied volatility as a forecaster — usually the single most useful regressor

There is a large literature establishing that implied vol contains
information about future RV that is *not* in past RV. Two ways to use it:

1. **HAR-IV / HARX with IV regressor.** Just add ATM 30-day IV (or
   model-free IV like VIX-methodology applied to each ETF chain) as an
   exogenous variable in the HAR regression. Empirically the lowest-loss HAR
   variant across most indices at the monthly horizon.
2. **IV-only model with bias correction.** Regress realized vol on
   ex-ante IV and use the fitted relationship — equivalent to treating IV as
   a biased forecast. Clean, interpretable, and surprisingly hard to beat.

For the VRP / short-put use case, there is a subtlety: we are *using* the
predicted RV to compare against IV. If the IV is on the right-hand side of the
forecast, the forecast is in part a transformation of IV. That's fine — what we
ultimately want is the residual `IV − Ê[RV | features]`, which is the conditional
VRP, and IV-as-regressor lets the model estimate exactly that. But the
regression should not be interpreted as "IV predicts RV"; it's "IV plus past RV
predicts future RV better than past RV alone."

**IV features worth trying:**
- Per-ticker 30-day ATM IV (level)
- Per-ticker IV term-structure slope (e.g., 30d vs 90d ATM IV)
- VIX level + VIX3M slope (systematic vol regime)
- 25-delta risk reversal / IV skew (downside-tail pricing)

**Data needed:** historical option chains. Either (a) OPRA-derived greeks +
IV per ticker (OptionMetrics IvyDB, ORATS, LiveVol), or (b) compute model-free
IV per ETF from option chain snapshots yourself (this is a non-trivial
implementation cost — Cboe's VIX whitepaper is the reference algorithm).

### 3.4 Machine learning — gains are real but smaller than people claim at monthly horizons

The empirical picture from recent horse races (Christensen et al. 2024,
Teller-Pigorsch-Pigorsch 2022, the deep-learning surveys):

- **Short horizon (1-day):** XGBoost / LightGBM with HAR-style features
  usually wins, sometimes by 5–10% MSE. LSTM/Transformer occasionally
  competitive but data-hungry.
- **Longer horizons (5d, 22d):** Linear models (HAR, HARX) come back to within
  noise of the best ML. Nonlinearities matter much less when you're averaging
  over 22 days. DL surveys (TiDE, DeepAR) report gains *only when augmented
  with macro features*, which is what HARX does anyway.
- **Crypto / single names:** Sentiment-augmented ML helps more (different
  noise profile).

**My recommendation:** start with the linear HAR-RS-IV baseline; add an
XGBoost head on the same feature matrix and ensemble. Skip LSTM/Transformer
unless the linear baseline is clearly missing something specific you can name.
A monthly RV forecast for ETFs is a low-data regime by ML standards (one
data point per day per ticker; ~250/yr per ticker over say 10 years = 2,500 per
ticker, or ~150k panel observations across the universe), and the marginal
return on a deep network here is small relative to the engineering cost.

**Data needed (ML on HAR features):** same as HARX above. No new data
required if you do this on top of the HAR feature matrix.

### 3.5 Path-dependent / rough volatility — research frontier, not for production

Recent work (HAR-PD, rough Bergomi-style models, options-driven RV forecasting
with rough vol) reports modest improvements over HAR. Worth knowing the
literature exists but the implementation lift is high and the gains aren't
large enough to justify it as a first iteration.

---

## 4. Combining forecasts

The most reliable improvement once you have 2–3 reasonable models is to
combine them. The simplest combiner — equal weight of HAR-RS-IV + Realized
GARCH + XGBoost(HAR features) — typically beats any single component out of
sample. More sophisticated combiners (constrained least squares, Bates-Granger,
discounted MSE weights) help a little but the gains over equal-weighting are
small.

---

## 5. Evaluation — what "strong" should mean

For this trading application, accuracy metrics should be picked deliberately:

- **QLIKE loss** ≡ RV/RV̂ − log(RV/RV̂) − 1. Preferred over MSE for variance
  forecasts because it is robust to the heavy right tail of RV and treats
  proportional errors symmetrically. This is the standard published metric.
- **Diebold-Mariano test** between model pairs for significance.
- **Calibration diagnostics:** is forecast bias zero on average? Is bias zero
  conditional on regime (high-IV vs low-IV days, post-shock vs quiet)? A model
  that is unbiased unconditionally but biased after vol spikes will lose money
  precisely when it matters.
- **Economic loss:** simulate the actual VRP strategy decisions with the
  forecast and measure dollar P&L vs an IV-only benchmark. This is what we
  ultimately care about — a model that wins on QLIKE but doesn't change
  position-sizing decisions vs an IV-only model is not adding economic value.

Recommended OOS protocol: rolling-origin re-estimation, refit weekly or
monthly, evaluate on the next-period horizon. At least 3–5 years of OOS data,
spanning at least one stress regime (2020 covid, 2022 rates shock, ideally
2025 tariff vol).

---

## 6. Recommended pipeline for this project

**Build order:**

1. **Measurement layer.** Daily RV(5-min), BV, RS+, RS−, RQ, jump component
   per ticker. Validate on SPY against published values. This is the
   foundation; everything depends on it.
2. **HAR-RS-IV baseline.** Direct 22-day forecasts. One model per ticker (or
   panel with ticker fixed effects — see Q5 below). This will already be a
   credible monthly RV forecast.
3. **Add HARQ correction and HAR-CJ jump decomposition** as ablations.
   Keep them if they survive DM tests, drop if not.
4. **Add Realized GARCH** as a second model. Same target, different
   functional form, gives a distributional output.
5. **Ensemble** HAR-RS-IV and Realized GARCH (equal weight is fine).
6. **Optional: XGBoost head** on the same feature matrix. Add to the
   ensemble only if it improves OOS QLIKE on at least 3 unrelated tickers.
7. **Economic backtest** vs IV-only benchmark on the VRP rule.

All of this is a few hundred lines of Python (statsmodels / arch / xgboost),
not a research project.

**Build later only if motivated by a specific gap:**
- IV-surface CNN features
- LSTM/Transformer
- Rough-vol models
- Cross-ticker dynamic factor model

---

## 7. Data requirements — consolidated

**Required for the recommended pipeline:**

| Data | Resolution | History | Used by |
|---|---|---|---|
| Trade prices (or NBBO mids) | 5-minute, RTH | ≥7y | RV, BV, RS±, RQ |
| Daily OHLC + close-to-close return | Daily | ≥10y | Overnight return, GARCH, range-based fallback |
| Risk-free rate | Daily | ≥10y | Excess returns, option pricing for IV |
| Dividends / distributions | As declared | ≥10y | Clean total-return series |
| Per-ticker option chains | Snapshot per day (EOD min) | ≥7y | 30-day ATM IV, IV term slope, model-free IV |
| VIX, VIX3M | Daily | ≥10y | Regime regressor |

**Nice to have:**
- Tick data → enables realized kernel (small precision gain)
- Full IV surface per ticker → enables IV-surface features (PCA or CNN)
- 25-delta risk reversal per ticker → tail-pricing feature
- Earnings calendar, FOMC calendar, ETF rebalance dates → event flags
- Cross-asset state (USD index, 2s10s, HYG-LQD spread, credit spreads) → regime
- ETF flow data (creations/redemptions) → for smaller-AUM names

**Probable sources:**
- Intraday equity bars: Polygon, Databento, AlgoSeek, Tiqs
- Options + IV: ORATS, LiveVol, OptionMetrics IvyDB (academic-licensed)
- Free fallback: yfinance for daily; Cboe site for VIX/VIX3M; SEC for
  ETF holdings; FRED for rates and macro

For tickers in the universe with thin option chains (VTWO, ARKB, SIVR, AAAU,
BTCO, etc. — explicitly flagged in `universe.yml`), the IV regressor will be
noisy or missing on some dates. Either fall back to a same-group proxy IV
(e.g. use IBIT IV for the BTC cluster) or skip IV features for those tickers
and rely on HAR-RS alone.

---

## 8. Open questions

(Listed inline above where they arise; consolidated in the chat for response.)
