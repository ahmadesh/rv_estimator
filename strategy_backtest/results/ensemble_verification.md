# EnsembleTopK — implementation verification

_Independent re-derivation vs `ENSEMBLETOPK_PRODUCTION_GUIDE.md` · cache window 2010-01-04→2026-05-22, clean_core, 204,565 keys · 36/36 checks passed_

> Tier-1 checks re-derive each quantity from raw inputs with plain numpy and assert the cached prediction parquets match — they verify the implementation and regressors are correct, independent of the OOS window. Tier-2 reproduces the guide's qualitative conclusions on our cache (OOS 2010+ / clean_core only, so exact numbers differ from the guide's 2018 / clean+hard figures — we check the *shape* of the claims).

**Tier-1 (implementation correctness): ✅ ALL PASS**

| # | Check | Result | Detail |
| --- | --- | --- | --- |
| 1 | regressor rv_d == recompute | ✅ | max|Δ|=0.00e+00, n=54385 |
| 2 | regressor rv_w == recompute | ✅ | max|Δ|=0.00e+00, n=54345 |
| 3 | regressor rv_m == recompute | ✅ | max|Δ|=0.00e+00, n=54175 |
| 4 | regressor sqrt_rq == recompute | ✅ | max|Δ|=0.00e+00, n=54385 |
| 5 | regressor rs_minus_5d == recompute | ✅ | max|Δ|=0.00e+00, n=54345 |
| 6 | regressor rs_plus_5d == recompute | ✅ | max|Δ|=0.00e+00, n=54345 |
| 7 | regressor jump_5d == recompute | ✅ | max|Δ|=0.00e+00, n=54345 |
| 8 | regressor log_iv == recompute | ✅ | max|Δ|=0.00e+00, n=47013 |
| 9 | regressor iv_slope == recompute | ✅ | max|Δ|=0.00e+00, n=47013 |
| 10 | log_rv_d == log(clip(rv,1e-12)) | ✅ | max|Δ|=0.00e+00 |
| 11 | log_rv_w == log(clip(rv,1e-12)) | ✅ | max|Δ|=0.00e+00 |
| 12 | log_rv_m == log(clip(rv,1e-12)) | ✅ | max|Δ|=0.00e+00 |
| 13 | HARQ feature list | ✅ | 4 feats |
| 14 | HAR-RS feature list | ✅ | 6 feats |
| 15 | HAR-CJ feature list | ✅ | 7 feats |
| 16 | HAR-RS-IV-Q feature list | ✅ | 14 feats |
| 17 | COMPONENTS == 4 HAR family | ✅ | ['HAR-RS-IV-Q', 'HARQ', 'HAR-RS', 'HAR-CJ'] |
| 18 | MIN_COMPONENTS == 2 | ✅ | 2 |
| 19 | HARQ OLS reproduces cache (last fold, h=22) | ✅ | max rel err=0.00e+00 over 160 preds |
| 20 | HAR-RS OLS reproduces cache (last fold, h=22) | ✅ | max rel err=0.00e+00 over 160 preds |
| 21 | HAR-RS-IV-Q OLS reproduces cache (last fold, h=22) | ✅ | max rel err=0.00e+00 over 150 preds |
| 22 | HAR-CJ OLS reproduces cache (last fold, h=22) | ✅ | max rel err=0.00e+00 over 160 preds |
| 23 | ensemble rv_hat == mean(component rv_hat) | ✅ | max|Δ|=0.00e+00 |
| 24 | ensemble sigma == sqrt(mean(σ²)+var(rv_hat)) | ✅ | max|Δ|=0.00e+00 |
| 25 | all ensemble keys have n_comp >= 2 | ✅ | min n_comp=3 |
| 26 | ensemble keys ⊆ recomputed keys (no imputation) | ✅ | ens 204565 vs matched 204565 |
| 27 | quantiles monotone q05≤…≤q95 | ✅ |  |
| 28 | q50 == lognormal median(rv_hat, s) | ✅ | max rel err=1.96e-15 |
| 29 | rv_hat ≥ q50 (lognormal mean ≥ median) | ✅ |  |
| 30 | h=22 ensemble level blow-ups rare (<0.1% of keys) | ✅ | 1/40913 keys rv_hat>0.5; worst QQQ 2015-08-24 rv_hat=76.1 — a HARQ quarticity spike averaged in; NOT a roll/trade date |
| 31 | HAR-CJ degrades at long h (h42), not the traded h=22 | ✅ | HAR-CJ h42 QLIKE=1124.8 (bv→0 log-floor outliers); h22 book unaffected |
| 32 | per-horizon QLIKE U-shape (h5 min, rising to h42) | ✅ | h1=0.292 h5=0.199 h10=0.210 h22=0.280 h42=0.491 |
| 33 | cov90 @ h=22 in [0.85, 0.97] | ✅ | cov90=0.930 (guide 0.927) |
| 34 | sign_acc @ h=22 ≈ coin-flip [0.45, 0.60] | ✅ | sign_acc=0.504 (guide ~0.518) |
| 35 | bias @ h=22 modest (|median log-ratio| < 0.5) | ✅ | median log(rv/tv)=+0.268 (2018+ +0.214), level ratio=+0.558 — POSITIVE/over-predicts here; guide −0.10..−0.17 is the crisis-weighted 2018 window |
| 36 | EnsembleTopK @ h=22 inside the component tie-set (≤1.05× best) | ✅ | ens=0.2798 best_comp=0.2736 HAR-RS-IV-Q=0.2736 HARQ=0.2909 HAR-RS=0.2915 HAR-CJ=0.6985 |

## Tier-2 measured values (our window)

| Metric | Our cache | Guide (ref) | Note |
| --- | --- | --- | --- |
| QLIKE per-h | h1 0.292 · h5 0.199 · h10 0.210 · h22 0.280 · h42 0.491 | h1 .296 · h5 .194 · h10 .213 · h22 .324 · h42 .431 | U-shape, min ~h5 |
| cov90 @ h22 | 0.930 | 0.927 | interval calibration |
| sign_acc @ h22 | 0.504 | ~0.518 | coin-flip over IV² (no dir. alpha) |
| bias @ h22 (median log) | +0.268 (level +0.558) | −0.10..−0.17 | **over**-predicts here — see Finding |
| QLIKE @ h22 ens vs comps | ens 0.2798 · HAR-RS-IV-Q 0.2736 · HARQ 0.2909 · HAR-RS 0.2915 · HAR-CJ 0.6985 | tie-set | averaging, not raw accuracy |

## Robustness — single-component level blow-ups (guide §3.5/§7/§9.4)

The combiner is an **arithmetic mean in level space**, so it is sensitive to a single component producing an extreme `rv_hat`. On the traded horizon h=22 this bites on exactly **1 of 40,913 keys** (0.002%): **QQQ 2015-08-24** (the Aug-2015 vol spike), where HARQ's quarticity term extrapolated to ~303 and dragged the mean to `rv_hat=76.1`. That date is **not a monthly roll date**, so it never becomes a trade — the 395-trade book is unaffected (its max in-book dispersion is a sane 2.35). Separately, **HAR-CJ destabilises at the long horizon** (h42 QLIKE 1125, from `bv→0` values hitting the `log(1e-12)` floor) but is well-behaved at h=22; the equal-weight mean absorbs it there. **Recommended hardening** (does not affect the current result): winsorize each component's `rv_hat` before combining, or switch the combiner to a **median / log-space mean** (guide §9.4 corollary) — this removes the single-key contamination and the long-horizon fragility.

## Finding — bias sign differs from the guide (window/regime, not a bug)

The guide reports a **mild negative** bias at h=22 (−0.10..−0.17, rv_hat under-predicts RV). On our cache the bias is **positive** — median `log(rv_hat/target_var) = +0.268` (and `+0.214` even restricted to the guide's own 2018+ window), i.e. the forecaster *over*-predicts realized variance on this universe. This is **not an implementation error** — Tier-1 proves the components and combiner are bit-exact. Two compounding causes: (i) `rv_hat` is the lognormal **mean** forecast `exp(μ̂+½ŝ²)`, structurally above the median by ≈½ŝ² (~+0.2 in log at h=22), so a log-ratio bias of that size is expected by construction; (ii) the 2010→ window is predominantly the **calm post-GFC regime**, where HAR-family models (carrying recent higher-vol memory) over-forecast — the over-prediction is largest in calm years (2013 +0.37, 2017 +0.41) and collapses toward zero in stress (2020 +0.09, 2022 −0.01). The guide's negative figure reflects a more crisis-weighted measurement.

**Consequence for the backtest:** because `rv_hat > iv²` on ~64% of candidates here, the conditional VRP `iv² − rv_hat` is mostly negative, so the put-spread sizer floors at `vrp_rel = 0.05` and under-deploys — directly the granularity-tax story in the backtest report §2. The fix the backtest already flags (de-bias `rv_hat`, doc §11 / report §10-B) follows straight from this.

## Conclusion

The cached EnsembleTopK forecasts the put-spread backtest consumes are a **faithful, bit-exact implementation** of the guide: the four components carry the documented regressors (all recomputed at 0.00 error), each is an independent per-(ticker,horizon) log-OLS reproduced here to 1e-6, and the ensemble is the exact equal-weight level-space mean with the documented sigma/lognormal contract. The guide's qualitative conclusions — QLIKE U-shape, cov90≈0.93, coin-flip directional skill at h=22, and h=22 point accuracy inside the component tie-set — reproduce on our 2010+ window. The one divergence (bias **sign**) is a regime/window effect with a clear mechanism, and it is the upstream cause of the backtest's negative-VRP / under-deployment behavior.
