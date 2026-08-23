# MLAI V4.20 — Definitive Unseen 8-Day / 2-Day Validation

This is the completed chronological research holdout. The latest ten available
UTC dates were split into eight historical dates and two untouched holdout
dates. Every available 5-minute holdout candle was processed sequentially.

## Reproducibility

- Dataset: `data/market_data_50d.bin`
- Dataset SHA-256: `c329b7469e69ff913861b8ad569a351e9c49f0cf47bf3fb2fdb195c91a11093a`
- Dataset size: 3,682,999 bytes
- Candle count: 35,403
- Instrument / symbol / timeframe: XAU/USD / XAUUSD / 5m
- First timestamp: `2026-02-02T03:20:00+00:00`
- Last timestamp: `2026-07-31T20:40:00+00:00`
- Training dates: `2026-07-21` through `2026-07-29` (Days 1–8)
- Locked holdout dates: `2026-07-30` and `2026-07-31` (Days 9–10)
- Training candles: 1,929
- Available and processed holdout candles: 525
- Sampling: every available 5-minute candle; no hourly subsampling
- Configuration: `k=24`, no temporal decay, no regime filter, balanced similarity
- Calibration: frozen predeclared shrink `0.35`, temperature `1.0`
- Configuration SHA-256: `e402cd5e939c0c77353f971c5f2235f6d3f544a356985cb655ff0c81ebe29517`
- Random seed: none

## Locked holdout results

| Horizon | Holdout | Scored | Excluded | Baseline accuracy | Retrieval accuracy | Accuracy lift | Baseline Brier | Retrieval Brier | Brier lift | Baseline LogLoss | Retrieval LogLoss | LogLoss lift | Coverage |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| H+4 | 525 | 521 | 4 | 46.641% | 38.964% | -7.678% | 0.618991 | 0.658080 | -0.039090 | 1.017792 | 1.085365 | -0.067573 | 100% |
| H+8 | 525 | 517 | 8 | 43.133% | 44.681% | +1.547% | 0.606157 | 0.648093 | -0.041937 | 0.992960 | 1.069838 | -0.076878 | 100% |
| H+16 | 525 | 509 | 16 | 42.043% | 43.615% | +1.572% | 0.575827 | 0.637471 | -0.061645 | 0.923858 | 1.051278 | -0.127420 | 100% |

The only exclusions were candles whose future horizon extended beyond the
dataset: H+4 = 4, H+8 = 8, H+16 = 16. No prediction was excluded for sparse
retrieval evidence.

## Probability and stability diagnostics

| Horizon | Actual UP / DOWN / NEUTRAL | Mean predicted UP / DOWN / NEUTRAL | Calibration slope | Intercept | ECE | Sharpness |
|---:|---|---|---:|---:|---:|---:|
| H+4 | 206 / 236 / 79 | 0.3431 / 0.3486 / 0.3082 | -0.1197 | 0.4328 | 0.0292 | 0.3605 |
| H+8 | 197 / 252 / 68 | 0.3503 / 0.3564 / 0.2933 | -1.1991 | 0.8905 | 0.0787 | 0.3701 |
| H+16 | 213 / 254 / 42 | 0.3580 / 0.3614 / 0.2806 | -1.2695 | 0.9188 | 0.0593 | 0.3802 |

Performance was reported independently for both holdout dates by the validator.
The retrieval path improved accuracy slightly at H+8 and H+16, but worsened
Brier score and LogLoss at every horizon. This is not evidence of a calibrated
predictive advantage over the causal baseline.

## Causal protections

- Prediction was created before the corresponding future outcome was read.
- Every retrieval record had a completed outcome before the query boundary.
- Holdout outcomes were not used for retrieval, calibration, tuning, or memory.
- All available 5-minute holdout candles were processed.
- Synthetic candles created: NO.
- Raw market data modified: NO.

Run the validator with:

```bash
python MLAI_V420_UNSEEN_8_2_VALIDATION.py --report MLAI_V420_UNSEEN_8_2_VALIDATION_REPORT.md
```

When memory is constrained, run each fixed horizon separately with
`--horizon 4`, `--horizon 8`, or `--horizon 16`.