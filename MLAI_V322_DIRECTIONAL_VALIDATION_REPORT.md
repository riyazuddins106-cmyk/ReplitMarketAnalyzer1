# MLAI v3.2.2 Directional Validation Report

## Purpose

Validate whether the fine-grained historical threshold is useful for BUY/SELL directional classification rather than winning primarily because of Neutral classification.

## Best Candidate

- Threshold: ±0.15%
- Directional accuracy: 54.86%
- Directional F1: 49.30%
- BUY precision: 56.83%
- SELL precision: 52.34%
- Directional coverage: 83.92%
- Validation score: 65.10

## Ranking

| Rank | Threshold | Directional Accuracy | Directional F1 | BUY Precision | SELL Precision | Coverage | Score |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | ±0.15% | 54.86% | 49.30% | 56.83% | 52.34% | 83.92% | 65.10 |
| 2 | ±0.16% | 54.44% | 48.50% | 56.31% | 51.97% | 82.37% | 64.43 |
| 3 | ±0.17% | 54.00% | 47.78% | 55.12% | 52.46% | 81.77% | 64.19 |
| 4 | ±0.19% | 54.54% | 47.46% | 55.09% | 53.67% | 79.79% | 64.07 |
| 5 | ±0.18% | 54.38% | 47.67% | 55.63% | 52.68% | 80.83% | 64.06 |
| 6 | ±0.20% | 55.01% | 47.54% | 56.12% | 53.42% | 78.85% | 63.88 |
| 7 | ±0.21% | 54.01% | 45.99% | 53.98% | 53.91% | 77.47% | 63.19 |
| 8 | ±0.22% | 54.09% | 45.55% | 53.50% | 54.53% | 76.44% | 62.73 |
| 9 | ±0.23% | 54.41% | 45.51% | 53.59% | 55.37% | 75.49% | 62.53 |
| 10 | ±0.24% | 53.69% | 44.71% | 52.77% | 54.89% | 74.12% | 61.71 |

## Safety

- market_data.bin was read only.
- MLAI v3.1 was not modified.
- Existing learning memory was not modified.
- No classification threshold was applied to v3.1.
- This is historical validation, not a future performance guarantee.
