# MLAI v3.2.7 Signal Integrity + Baseline Validation

## Purpose

This validation determines whether the current 60-candle momentum representation contains meaningful directional information beyond simple baseline strategies.

## Important Finding About v3.2.6

The v3.2.6 prediction was based on the return of the current 60-candle window. Therefore it is treated here as a MOMENTUM BASELINE rather than as the MLAI learned candle-language engine.

## Configuration

- Market file: `market_data.bin`
- Valid closes: 1239
- Current window: 60
- Horizons: [4, 8, 16]
- Validation ratio: 30%
- Validation windows: 4

## Threshold Ranking

| Rank | Threshold | Momentum Directional | Momentum Dir-F1 | Last Candle Directional | F1 Lift | BUY Precision | SELL Precision |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | ±0.15% | 49.95% | 15.99% | 2.55% | 11.87% | 10.26% | 11.32% |
| 2 | ±0.16% | 51.56% | 15.76% | 1.83% | 12.60% | 10.16% | 11.02% |
| 3 | ±0.17% | 51.83% | 14.46% | 2.11% | 10.97% | 9.36% | 9.71% |
| 4 | ±0.18% | 53.32% | 14.20% | 2.16% | 10.71% | 8.95% | 9.59% |
| 5 | ±0.19% | 53.45% | 13.42% | 1.65% | 11.05% | 8.11% | 9.26% |
| 6 | ±0.20% | 53.42% | 12.83% | 1.73% | 10.36% | 7.96% | 8.48% |
| 7 | ±0.21% | 52.78% | 11.75% | 1.82% | 9.20% | 7.58% | 7.31% |
| 8 | ±0.22% | 53.41% | 11.13% | 1.91% | 8.58% | 7.27% | 6.69% |
| 9 | ±0.23% | 55.86% | 10.47% | 1.01% | 9.11% | 7.04% | 5.98% |
| 10 | ±0.24% | 55.54% | 9.14% | 1.10% | 7.63% | 6.27% | 5.10% |

## Final Diagnostic Result

- Best diagnostic threshold: **±0.15%**
- Momentum directional accuracy: **49.95%**
- Momentum directional F1: **15.99%**
- Last-candle directional accuracy: **2.55%**
- Random directional accuracy: **31.12%**
- Directional lift: **47.40%**
- F1 lift: **11.87%**

### Verdict: WEAK SIGNAL

The current representation shows limited evidence of directional information, but not enough to justify treating it as a reliable predictive engine.

## Safety

- `market_data.bin` was not modified.
- MLAI v3.1 was not modified.
- Existing learning memory was not modified.
- No production classification threshold was changed.
- No trading decision system was changed.
