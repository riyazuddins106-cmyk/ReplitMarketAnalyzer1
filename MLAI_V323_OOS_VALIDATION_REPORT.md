# MLAI v3.2.3 Out-of-Sample Validation Report

## Purpose

This experiment evaluates candidate outcome-classification thresholds on a later chronological historical period that was not used for candidate selection.

## Dataset

- Market file: `market_data.bin`
- Valid candles: **1239**
- Current window: **60**
- Horizons: **[4, 8, 16]**
- Validation ratio: **30%**
- Calibration/reference candles: **867**
- Validation candles: **372**

## Candidate Thresholds

- ±0.15%
- ±0.18%
- ±0.20%
- ±0.24%

## Ranking

| Rank | Threshold | Directional | Dir-F1 | BUY Precision | SELL Precision | Coverage | Stability | Score |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | ±0.20% | 62.26% | 26.40% | 21.21% | 15.25% | 99.72% | 84.74 | 56.55 |
| 2 | ±0.18% | 60.71% | 28.51% | 23.54% | 16.67% | 99.72% | 96.41 | 56.42 |
| 3 | ±0.15% | 58.70% | 32.02% | 27.51% | 19.81% | 99.72% | 94.58 | 56.42 |
| 4 | ±0.24% | 63.05% | 20.62% | 16.55% | 10.22% | 99.72% | 86.78 | 55.49 |

## Result

**Best out-of-sample candidate: ±0.20%**

- OOS score: **56.55**
- Directional accuracy: **62.26%**
- Directional F1: **26.40%**
- BUY precision: **21.21%**
- SELL precision: **15.25%**
- Coverage: **99.72%**
- Cross-horizon stability: **84.74**

## Important Interpretation

This result is historical evidence only. It is not a guarantee of future market performance.
No v3.1 logic was changed during this experiment.
The original market data was not modified.
Existing MLAI learning memory was not modified.

## Next Decision

The out-of-sample result should be compared with the v3.2, v3.2.1 and v3.2.2 calibration results before changing any production classification logic.