# MLAI v3.2.1 Fine-Grained Historical Threshold Calibration Report

Generated: 2026-08-15T06:56:35.482147+00:00

## Purpose

This calibration independently examines fine-grained historical outcome thresholds after MLAI v3.2 identified ±0.20% as a candidate threshold.

## Protection

- market_data.bin was read only.
- market_data.bin was not modified.
- mlai_v31.py was not modified.
- mlai_learning_memory.bin was not modified.
- Current 60-candle window was excluded from historical training.
- Future candles were used only for historical outcome resolution.

## Dataset

- Stored candles: 1239
- Current window: 60
- Horizons: [4, 8, 16]

## Threshold Ranking

| Rank | Threshold | Balanced | Macro-F1 | Neutral-F1 | Stability | Score |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | ±0.24% | 30.04% | 27.70% | 58.31% | 99.43 | 48.87 |
| 2 | ±0.18% | 31.65% | 30.25% | 54.09% | 96.94 | 48.78 |
| 3 | ±0.22% | 30.31% | 28.46% | 56.99% | 98.63 | 48.76 |
| 4 | ±0.19% | 31.30% | 29.80% | 54.70% | 97.19 | 48.71 |
| 5 | ±0.21% | 30.10% | 28.55% | 55.97% | 98.94 | 48.57 |
| 6 | ±0.20% | 31.17% | 29.38% | 55.42% | 95.73 | 48.39 |
| 7 | ±0.17% | 31.86% | 30.57% | 53.37% | 94.89 | 48.38 |
| 8 | ±0.23% | 30.07% | 27.87% | 57.53% | 97.36 | 48.36 |
| 9 | ±0.16% | 32.11% | 30.94% | 52.25% | 93.99 | 48.16 |
| 10 | ±0.25% | 29.40% | 27.21% | 58.83% | 96.58 | 48.07 |
| 11 | ±0.15% | 32.08% | 31.13% | 50.73% | 94.55 | 48.02 |
| 12 | ±0.14% | 31.93% | 31.21% | 48.92% | 93.72 | 47.47 |
| 13 | ±0.13% | 31.47% | 30.95% | 46.72% | 93.41 | 46.75 |
| 14 | ±0.12% | 31.09% | 30.67% | 44.55% | 91.92 | 45.82 |

## Recommended Candidate

**±0.24%**

This is a historical calibration candidate only. It is not a guaranteed future prediction threshold.

## Detailed Results

### Threshold ±0.24%

#### 4 candles

- Records: 1104
- Accuracy: 46.47%
- Balanced accuracy: 30.21%
- Macro-F1: 25.66%
- Neutral-F1: 64.02%
- Actual bullish: 4.17%
- Actual bearish: 5.25%
- Actual neutral: 90.58%

#### 8 candles

- Records: 1104
- Accuracy: 42.57%
- Balanced accuracy: 30.00%
- Macro-F1: 28.04%
- Neutral-F1: 59.84%
- Actual bullish: 9.60%
- Actual bearish: 11.32%
- Actual neutral: 79.08%

#### 16 candles

- Records: 1104
- Accuracy: 36.68%
- Balanced accuracy: 29.91%
- Macro-F1: 29.42%
- Neutral-F1: 51.06%
- Actual bullish: 19.47%
- Actual bearish: 17.48%
- Actual neutral: 63.04%

#### Confusion Matrix — 4 candles

| Predicted / Actual | Bullish | Bearish | Neutral |
|---|---:|---:|---:|
| bullish | 8 | 21 | 251 |
| bearish | 18 | 14 | 258 |
| neutral | 20 | 23 | 491 |

### Threshold ±0.18%

#### 4 candles

- Records: 1104
- Accuracy: 44.75%
- Balanced accuracy: 32.56%
- Macro-F1: 29.21%
- Neutral-F1: 61.97%
- Actual bullish: 8.51%
- Actual bearish: 10.05%
- Actual neutral: 81.43%

#### 8 candles

- Records: 1104
- Accuracy: 40.13%
- Balanced accuracy: 31.50%
- Macro-F1: 30.67%
- Neutral-F1: 56.34%
- Actual bullish: 16.30%
- Actual bearish: 16.30%
- Actual neutral: 67.39%

#### 16 candles

- Records: 1104
- Accuracy: 33.79%
- Balanced accuracy: 30.88%
- Macro-F1: 30.88%
- Neutral-F1: 43.96%
- Actual bullish: 27.99%
- Actual bearish: 24.37%
- Actual neutral: 47.64%

#### Confusion Matrix — 4 candles

| Predicted / Actual | Bullish | Bearish | Neutral |
|---|---:|---:|---:|
| bullish | 20 | 35 | 225 |
| bearish | 30 | 30 | 230 |
| neutral | 44 | 46 | 444 |

### Threshold ±0.22%

#### 4 candles

- Records: 1104
- Accuracy: 45.83%
- Balanced accuracy: 30.41%
- Macro-F1: 26.70%
- Neutral-F1: 63.42%
- Actual bullish: 5.07%
- Actual bearish: 7.34%
- Actual neutral: 87.59%

#### 8 candles

- Records: 1104
- Accuracy: 41.58%
- Balanced accuracy: 30.62%
- Macro-F1: 29.04%
- Neutral-F1: 58.44%
- Actual bullish: 11.78%
- Actual bearish: 13.22%
- Actual neutral: 75.00%

#### 16 candles

- Records: 1104
- Accuracy: 35.60%
- Balanced accuracy: 29.90%
- Macro-F1: 29.65%
- Neutral-F1: 49.11%
- Actual bullish: 21.92%
- Actual bearish: 19.11%
- Actual neutral: 58.97%

#### Confusion Matrix — 4 candles

| Predicted / Actual | Bullish | Bearish | Neutral |
|---|---:|---:|---:|
| bullish | 9 | 28 | 243 |
| bearish | 21 | 21 | 248 |
| neutral | 26 | 32 | 476 |

### Threshold ±0.19%

#### 4 candles

- Records: 1104
- Accuracy: 44.84%
- Balanced accuracy: 31.72%
- Macro-F1: 28.28%
- Neutral-F1: 62.22%
- Actual bullish: 7.52%
- Actual bearish: 9.24%
- Actual neutral: 83.24%

#### 8 candles

- Records: 1104
- Accuracy: 40.67%
- Balanced accuracy: 31.73%
- Macro-F1: 30.66%
- Neutral-F1: 56.90%
- Actual bullish: 15.04%
- Actual bearish: 15.85%
- Actual neutral: 69.11%

#### 16 candles

- Records: 1104
- Accuracy: 33.97%
- Balanced accuracy: 30.46%
- Macro-F1: 30.45%
- Neutral-F1: 45.00%
- Actual bullish: 26.72%
- Actual bearish: 23.01%
- Actual neutral: 50.27%

#### Confusion Matrix — 4 candles

| Predicted / Actual | Bullish | Bearish | Neutral |
|---|---:|---:|---:|
| bullish | 17 | 33 | 230 |
| bearish | 27 | 26 | 237 |
| neutral | 39 | 43 | 452 |

### Threshold ±0.21%

#### 4 candles

- Records: 1104
- Accuracy: 45.29%
- Balanced accuracy: 30.15%
- Macro-F1: 26.96%
- Neutral-F1: 62.94%
- Actual bullish: 5.98%
- Actual bearish: 7.97%
- Actual neutral: 86.05%

#### 8 candles

- Records: 1104
- Accuracy: 41.12%
- Balanced accuracy: 30.36%
- Macro-F1: 29.05%
- Neutral-F1: 58.01%
- Actual bullish: 12.50%
- Actual bearish: 13.77%
- Actual neutral: 73.73%

#### 16 candles

- Records: 1104
- Accuracy: 34.51%
- Balanced accuracy: 29.78%
- Macro-F1: 29.63%
- Neutral-F1: 46.96%
- Actual bullish: 23.55%
- Actual bearish: 20.65%
- Actual neutral: 55.80%

#### Confusion Matrix — 4 candles

| Predicted / Actual | Bullish | Bearish | Neutral |
|---|---:|---:|---:|
| bullish | 10 | 29 | 241 |
| bearish | 25 | 23 | 242 |
| neutral | 31 | 36 | 467 |

### Threshold ±0.20%

#### 4 candles

- Records: 1104
- Accuracy: 45.56%
- Balanced accuracy: 32.45%
- Macro-F1: 28.31%
- Neutral-F1: 62.90%
- Actual bullish: 6.88%
- Actual bearish: 8.42%
- Actual neutral: 84.69%

#### 8 candles

- Records: 1104
- Accuracy: 40.94%
- Balanced accuracy: 31.16%
- Macro-F1: 29.96%
- Neutral-F1: 57.53%
- Actual bullish: 13.77%
- Actual bearish: 14.95%
- Actual neutral: 71.29%

#### 16 candles

- Records: 1104
- Accuracy: 33.97%
- Balanced accuracy: 29.89%
- Macro-F1: 29.86%
- Neutral-F1: 45.82%
- Actual bullish: 25.63%
- Actual bearish: 21.92%
- Actual neutral: 52.45%

#### Confusion Matrix — 4 candles

| Predicted / Actual | Bullish | Bearish | Neutral |
|---|---:|---:|---:|
| bullish | 16 | 30 | 234 |
| bearish | 26 | 25 | 239 |
| neutral | 34 | 38 | 462 |

### Threshold ±0.17%

#### 4 candles

- Records: 1104
- Accuracy: 44.84%
- Balanced accuracy: 33.39%
- Macro-F1: 30.04%
- Neutral-F1: 61.92%
- Actual bullish: 9.15%
- Actual bearish: 10.78%
- Actual neutral: 80.07%

#### 8 candles

- Records: 1104
- Accuracy: 39.40%
- Balanced accuracy: 31.26%
- Macro-F1: 30.75%
- Neutral-F1: 55.56%
- Actual bullish: 17.66%
- Actual bearish: 17.57%
- Actual neutral: 64.76%

#### 16 candles

- Records: 1104
- Accuracy: 33.33%
- Balanced accuracy: 30.92%
- Macro-F1: 30.91%
- Neutral-F1: 42.62%
- Actual bullish: 29.26%
- Actual bearish: 25.18%
- Actual neutral: 45.56%

#### Confusion Matrix — 4 candles

| Predicted / Actual | Bullish | Bearish | Neutral |
|---|---:|---:|---:|
| bullish | 23 | 37 | 220 |
| bearish | 32 | 33 | 225 |
| neutral | 46 | 49 | 439 |

### Threshold ±0.23%

#### 4 candles

- Records: 1104
- Accuracy: 46.47%
- Balanced accuracy: 30.83%
- Macro-F1: 26.31%
- Neutral-F1: 63.99%
- Actual bullish: 4.44%
- Actual bearish: 6.07%
- Actual neutral: 89.49%

#### 8 candles

- Records: 1104
- Accuracy: 41.94%
- Balanced accuracy: 30.10%
- Macro-F1: 28.35%
- Neutral-F1: 58.98%
- Actual bullish: 10.60%
- Actual bearish: 12.14%
- Actual neutral: 77.26%

#### 16 candles

- Records: 1104
- Accuracy: 35.60%
- Balanced accuracy: 29.28%
- Macro-F1: 28.95%
- Neutral-F1: 49.63%
- Actual bullish: 20.65%
- Actual bearish: 18.21%
- Actual neutral: 61.14%

#### Confusion Matrix — 4 candles

| Predicted / Actual | Bullish | Bearish | Neutral |
|---|---:|---:|---:|
| bullish | 8 | 24 | 248 |
| bearish | 19 | 18 | 253 |
| neutral | 22 | 25 | 487 |

### Threshold ±0.16%

#### 4 candles

- Records: 1104
- Accuracy: 44.57%
- Balanced accuracy: 33.91%
- Macro-F1: 30.79%
- Neutral-F1: 61.42%
- Actual bullish: 10.24%
- Actual bearish: 11.59%
- Actual neutral: 78.17%

#### 8 candles

- Records: 1104
- Accuracy: 38.86%
- Balanced accuracy: 31.80%
- Macro-F1: 31.47%
- Neutral-F1: 54.38%
- Actual bullish: 19.38%
- Actual bearish: 19.38%
- Actual neutral: 61.23%

#### 16 candles

- Records: 1104
- Accuracy: 32.52%
- Balanced accuracy: 30.61%
- Macro-F1: 30.55%
- Neutral-F1: 40.95%
- Actual bullish: 30.62%
- Actual bearish: 26.18%
- Actual neutral: 43.21%

#### Confusion Matrix — 4 candles

| Predicted / Actual | Bullish | Bearish | Neutral |
|---|---:|---:|---:|
| bullish | 27 | 39 | 214 |
| bearish | 34 | 36 | 220 |
| neutral | 52 | 53 | 429 |

### Threshold ±0.25%

#### 4 candles

- Records: 1104
- Accuracy: 46.29%
- Balanced accuracy: 28.39%
- Macro-F1: 24.72%
- Neutral-F1: 63.95%
- Actual bullish: 3.71%
- Actual bearish: 4.71%
- Actual neutral: 91.58%

#### 8 candles

- Records: 1104
- Accuracy: 43.21%
- Balanced accuracy: 30.43%
- Macro-F1: 28.07%
- Neutral-F1: 60.48%
- Actual bullish: 9.06%
- Actual bearish: 10.51%
- Actual neutral: 80.43%

#### 16 candles

- Records: 1104
- Accuracy: 37.05%
- Balanced accuracy: 29.39%
- Macro-F1: 28.84%
- Neutral-F1: 52.07%
- Actual bullish: 18.12%
- Actual bearish: 16.49%
- Actual neutral: 65.40%

#### Confusion Matrix — 4 candles

| Predicted / Actual | Bullish | Bearish | Neutral |
|---|---:|---:|---:|
| bullish | 7 | 20 | 253 |
| bearish | 16 | 10 | 264 |
| neutral | 18 | 22 | 494 |

### Threshold ±0.15%

#### 4 candles

- Records: 1104
- Accuracy: 43.84%
- Balanced accuracy: 33.71%
- Macro-F1: 31.15%
- Neutral-F1: 60.54%
- Actual bullish: 11.41%
- Actual bearish: 12.77%
- Actual neutral: 75.82%

#### 8 candles

- Records: 1104
- Accuracy: 37.95%
- Balanced accuracy: 31.91%
- Macro-F1: 31.73%
- Neutral-F1: 52.64%
- Actual bullish: 21.38%
- Actual bearish: 20.65%
- Actual neutral: 57.97%

#### 16 candles

- Records: 1104
- Accuracy: 31.97%
- Balanced accuracy: 30.61%
- Macro-F1: 30.50%
- Neutral-F1: 39.02%
- Actual bullish: 32.25%
- Actual bearish: 26.99%
- Actual neutral: 40.76%

#### Confusion Matrix — 4 candles

| Predicted / Actual | Bullish | Bearish | Neutral |
|---|---:|---:|---:|
| bullish | 31 | 42 | 207 |
| bearish | 37 | 38 | 215 |
| neutral | 58 | 61 | 415 |

### Threshold ±0.14%

#### 4 candles

- Records: 1104
- Accuracy: 43.21%
- Balanced accuracy: 33.75%
- Macro-F1: 31.79%
- Neutral-F1: 59.69%
- Actual bullish: 12.95%
- Actual bearish: 14.31%
- Actual neutral: 72.74%

#### 8 candles

- Records: 1104
- Accuracy: 37.23%
- Balanced accuracy: 31.99%
- Macro-F1: 31.93%
- Neutral-F1: 51.32%
- Actual bullish: 23.19%
- Actual bearish: 22.10%
- Actual neutral: 54.71%

#### 16 candles

- Records: 1104
- Accuracy: 30.80%
- Balanced accuracy: 30.04%
- Macro-F1: 29.89%
- Neutral-F1: 35.75%
- Actual bullish: 33.88%
- Actual bearish: 28.35%
- Actual neutral: 37.77%

#### Confusion Matrix — 4 candles

| Predicted / Actual | Bullish | Bearish | Neutral |
|---|---:|---:|---:|
| bullish | 33 | 45 | 202 |
| bearish | 43 | 45 | 202 |
| neutral | 67 | 68 | 399 |

### Threshold ±0.13%

#### 4 candles

- Records: 1104
- Accuracy: 42.21%
- Balanced accuracy: 33.45%
- Macro-F1: 32.09%
- Neutral-F1: 58.46%
- Actual bullish: 14.95%
- Actual bearish: 15.67%
- Actual neutral: 69.38%

#### 8 candles

- Records: 1104
- Accuracy: 35.69%
- Balanced accuracy: 31.21%
- Macro-F1: 31.22%
- Neutral-F1: 49.09%
- Actual bullish: 24.64%
- Actual bearish: 23.73%
- Actual neutral: 51.63%

#### 16 candles

- Records: 1104
- Accuracy: 29.98%
- Balanced accuracy: 29.76%
- Macro-F1: 29.55%
- Neutral-F1: 32.60%
- Actual bullish: 35.51%
- Actual bearish: 30.07%
- Actual neutral: 34.42%

#### Confusion Matrix — 4 candles

| Predicted / Actual | Bullish | Bearish | Neutral |
|---|---:|---:|---:|
| bullish | 37 | 51 | 192 |
| bearish | 47 | 49 | 194 |
| neutral | 81 | 73 | 380 |

### Threshold ±0.12%

#### 4 candles

- Records: 1104
- Accuracy: 41.67%
- Balanced accuracy: 33.51%
- Macro-F1: 32.54%
- Neutral-F1: 57.73%
- Actual bullish: 16.39%
- Actual bearish: 17.12%
- Actual neutral: 66.49%

#### 8 candles

- Records: 1104
- Accuracy: 34.60%
- Balanced accuracy: 30.94%
- Macro-F1: 30.93%
- Neutral-F1: 47.06%
- Actual bullish: 26.18%
- Actual bearish: 25.18%
- Actual neutral: 48.64%

#### 16 candles

- Records: 1104
- Accuracy: 28.62%
- Balanced accuracy: 28.81%
- Macro-F1: 28.53%
- Neutral-F1: 28.86%
- Actual bullish: 37.50%
- Actual bearish: 31.16%
- Actual neutral: 31.34%

#### Confusion Matrix — 4 candles

| Predicted / Actual | Bullish | Bearish | Neutral |
|---|---:|---:|---:|
| bullish | 40 | 56 | 184 |
| bearish | 52 | 54 | 184 |
| neutral | 89 | 79 | 366 |

## Interpretation Rules

The recommended threshold must not be interpreted as future prediction probability.

Ordinary accuracy is not sufficient for threshold selection because class imbalance can make accuracy misleading.

Balanced accuracy and Macro-F1 are used to evaluate all three classes.

Neutral-F1 is explicitly monitored because v3.1 showed very weak neutral historical accuracy at ±0.02%.

Cross-horizon stability is used to avoid selecting a threshold that works only for one horizon.

## Decision

The current v3.2.1 calibration ranking places ±0.24% first.

This result must be reviewed before any outcome-classification logic is changed in a future MLAI engine version.
