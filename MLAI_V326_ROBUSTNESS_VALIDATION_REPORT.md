# MLAI v3.2.6 Multi-Window Robustness Validation Report

This report evaluates historical threshold robustness across multiple chronological out-of-sample windows.

## Configuration

- Market file: `market_data.bin`
- Valid close prices: 1239
- Current window: 60
- Horizons: [4, 8, 16]
- Validation ratio: 30%
- Validation windows: 4

## Validation Windows

- Window 1: index 867 to 959
- Window 2: index 960 to 1052
- Window 3: index 1053 to 1145
- Window 4: index 1146 to 1238

## Ranking

| Rank | Threshold | Directional | Dir-F1 | BUY Precision | SELL Precision | Target Coverage | Prediction Coverage | Stability | Score |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | ±0.15% | 50.26% | 16.21% | 9.98% | 11.19% | 36.83% | 92.52% | 3.05 | 22.01 |
| 2 | ±0.16% | 51.81% | 16.01% | 9.88% | 10.88% | 34.37% | 91.54% | 0.79 | 21.82 |
| 3 | ±0.18% | 52.74% | 14.39% | 8.68% | 9.48% | 29.82% | 91.24% | 0.00 | 21.23 |
| 4 | ±0.17% | 51.74% | 14.69% | 9.08% | 9.59% | 31.01% | 91.24% | 0.18 | 21.10 |
| 5 | ±0.19% | 53.10% | 13.66% | 7.83% | 9.18% | 27.95% | 90.75% | 0.00 | 21.05 |
| 6 | ±0.20% | 52.47% | 13.03% | 7.70% | 8.42% | 26.56% | 90.06% | 0.00 | 20.61 |
| 7 | ±0.21% | 52.18% | 11.91% | 7.34% | 7.27% | 24.39% | 89.07% | 0.00 | 20.09 |
| 8 | ±0.23% | 53.44% | 10.59% | 6.82% | 5.95% | 20.54% | 87.70% | 0.00 | 19.96 |
| 9 | ±0.22% | 52.33% | 11.27% | 7.04% | 6.65% | 22.22% | 88.78% | 0.00 | 19.89 |
| 10 | ±0.24% | 53.64% | 9.34% | 6.04% | 5.08% | 18.27% | 86.22% | 0.00 | 19.54 |

## Best Candidate

**±0.15%**

Robustness score: **22.01**

This is a historical robustness candidate only. It is not a guarantee of future trading performance.

## Safety

- MLAI v3.1 was not modified.
- market_data.bin was not modified.
- Existing learning memory was not modified.
- No production classification threshold was changed.
