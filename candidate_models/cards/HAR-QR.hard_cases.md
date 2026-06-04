# HAR-QR — Self Stats
_universe=`hard_cases` · primary horizon h=22 · predictions=`execution/data/predictions/HAR-QR.parquet` · generated 2026-06-04T02:00:57Z_

_Self-only metrics — no leaderboard rank, no DM test, no MCS, no §9 status._
_Cross-model comparison is produced by the final `rv_eval.evaluator` pass._

## Tier-1 pooled by horizon (§3)
| model | horizon | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-QR | 1 | 8196 | 15376677.1697 | 2.6412 | 0.9051 | 0.3283 | 0.8908 | 0.4930 | 0.0005 |
| HAR-QR | 5 | 8153 | 39593936.9915 | 1.9358 | 0.6567 | 0.1869 | 0.8762 | 0.4768 | 0.0021 |
| HAR-QR | 10 | 8108 | 30108205.2099 | 1.3861 | 0.5568 | 0.1181 | 0.8642 | 0.4780 | 0.0041 |
| HAR-QR | 22 | 8048 | 455400.7232 | 0.7159 | 0.4951 | 0.0609 | 0.8549 | 0.4674 | 0.0086 |
| HAR-QR | 42 | 7905 | 0.3885 | 0.6629 | 0.4812 | 0.0699 | 0.8309 | 0.4563 | 0.0151 |

## §5 IV-incremental skill (per horizon)
| model | horizon | n | slope | t_slope | sign_acc | qlike_model | qlike_iv | qlike_gain_vs_iv |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-QR | 1 | 7906 | -0.0639 | -1.6447 | 0.7312 | 15560193.0696 | 0.3595 | -15560192.7101 |
| HAR-QR | 5 | 7863 | 0.3418 | 12.7836 | 0.6821 | 38977713.0812 | 0.2624 | -38977712.8188 |
| HAR-QR | 10 | 7838 | 0.5256 | 23.5805 | 0.6633 | 27738321.2557 | 0.2542 | -27738321.0015 |
| HAR-QR | 22 | 7778 | 0.6909 | 39.0947 | 0.6305 | 471209.1701 | 0.2732 | -471208.8970 |
| HAR-QR | 42 | 7657 | 0.8474 | 62.8363 | 0.6339 | 0.3958 | 0.3134 | -0.0824 |

## §6 Conditional bias by IV-percentile bucket (h=22)
| model | horizon | iv_pctile_bucket | n | qlike | log_bias |
| --- | --- | --- | --- | --- | --- |
| HAR-QR | 22 | 0 | 2078 | 0.4387 | -0.0685 |
| HAR-QR | 22 | 1 | 1264 | 2899574.5573 | 0.0226 |
| HAR-QR | 22 | 2 | 1355 | 0.2741 | 0.0624 |
| HAR-QR | 22 | 3 | 1460 | 0.3074 | 0.0528 |
| HAR-QR | 22 | 4 | 1727 | 0.5863 | 0.2892 |

## §6 Post-shock calibration (h=22)
| model | horizon | bias_all | qlike_all | bias_postshock | qlike_postshock | n_postshock | trap_flag |
| --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-QR | 22 | 0.0609 | 455400.7232 | 0.1230 | 0.4884 | 1487 | ✓ |

## Per-ticker Tier-1 at h=22
| model | horizon | ticker | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-QR | 22 | IBIT | 517 | 0.1842 | 0.6616 | 0.5469 | -0.3221 | 0.7118 | 0.4642 | 0.0039 |
| HAR-QR | 22 | KRE | 2087 | 1756139.3173 | 0.8076 | 0.4602 | 0.0507 | 0.9420 | 0.5362 | 0.0018 |
| HAR-QR | 22 | MSOS | 1270 | 0.3304 | 0.6696 | 0.5103 | 0.2652 | 0.7480 | 0.3748 | 0.0069 |
| HAR-QR | 22 | USO | 2087 | 0.4144 | 0.6656 | 0.4722 | 0.1379 | 0.8601 | 0.4552 | 0.0034 |
| HAR-QR | 22 | UVXY | 2087 | 0.4244 | 0.7071 | 0.5308 | -0.0354 | 0.8630 | 0.4681 | 0.0228 |

## Pooled by group
| model | group | n | qlike | log_rmse | log_mae | log_bias | cov90 | cov50 | pinball |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR-QR | crypto | 2633 | 0.2994 | 0.6974 | 0.5473 | -0.1909 | 0.8268 | 0.5078 | 0.0027 |
| HAR-QR | long_volatility_vix | 10465 | 64000935.8707 | 2.6854 | 0.8795 | 0.3147 | 0.8620 | 0.4572 | 0.0158 |
| HAR-QR | oil_and_energy | 10465 | 980110.9227 | 1.0780 | 0.5476 | 0.1201 | 0.8585 | 0.4642 | 0.0025 |
| HAR-QR | us_cannabis | 6382 | 0.3712 | 0.6498 | 0.4788 | 0.2345 | 0.7921 | 0.4069 | 0.0049 |
| HAR-QR | us_cyclicals_sector | 10465 | 1585509.0738 | 1.3580 | 0.5393 | 0.0641 | 0.9234 | 0.5347 | 0.0013 |
