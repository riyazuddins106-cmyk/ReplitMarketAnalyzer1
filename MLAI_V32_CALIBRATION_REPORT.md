# MLAI v3.2 Historical Prediction Calibration Report

Generated: 2026-08-15T06:47:05.064884+00:00

## Purpose

Determine whether the v3.1 outcome classification threshold is appropriate for the historical XAU/USD dataset.

## Data Protection

- `market_data.bin` was read-only.
- `mlai_v31.py` was not modified.
- `mlai_learning_memory.bin` was not overwritten.
- Calibration results were saved separately.

## Dataset

- Stored candles: 1239
- Current window: 60
- Horizons: 4, 8, 16

## Thresholds Tested

- ±0.02%
- ±0.05%
- ±0.10%
- ±0.15%
- ±0.20%
- ±0.30%

## Threshold Ranking

| Rank | Threshold | Balanced Accuracy | Macro F1 | Neutral F1 | Stability | Score |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | ±0.20% | 31.12% | 29.31% | 55.33% | 97.55 | 45.47 |
| 2 | ±0.15% | 32.07% | 31.09% | 50.68% | 97.01 | 45.29 |
| 3 | ±0.30% | 28.63% | 25.98% | 61.26% | 96.21 | 44.63 |
| 4 | ±0.10% | 31.09% | 30.75% | 40.72% | 96.11 | 42.68 |
| 5 | ±0.05% | 31.71% | 29.71% | 28.01% | 94.40 | 39.87 |
| 6 | ±0.02% | 32.15% | 26.27% | 13.14% | 94.74 | 36.27 |

## Recommended Candidate

**±0.20%**

This is a historical calibration candidate, not a future probability or guaranteed prediction threshold.

## Detailed Horizon Results

### Threshold ±0.02%

#### 4-candle horizon

- Records: 1116
- Accuracy: 28.49%
- Balanced accuracy: 34.31%
- Macro precision: 33.06%
- Macro recall: 34.31%
- Macro F1: 28.09%
- Directional accuracy: 43.35%

Confusion matrix (rows=prediction, columns=actual):

| Prediction | Bullish | Neutral | Bearish |
|---|---:|---:|---:|
| bullish | 128 | 37 | 124 |
| neutral | 254 | 67 | 216 |
| bearish | 142 | 25 | 123 |

- bullish: precision=44.29%, recall=24.43%, F1=31.49%
- neutral: precision=12.48%, recall=51.94%, F1=20.12%
- bearish: precision=42.41%, recall=26.57%, F1=32.67%

#### 8-candle horizon

- Records: 1112
- Accuracy: 26.53%
- Balanced accuracy: 33.08%
- Macro precision: 31.90%
- Macro recall: 33.08%
- Macro F1: 25.59%
- Directional accuracy: 43.83%

Confusion matrix (rows=prediction, columns=actual):

| Prediction | Bullish | Neutral | Bearish |
|---|---:|---:|---:|
| bullish | 132 | 24 | 129 |
| neutral | 269 | 43 | 225 |
| bearish | 151 | 19 | 120 |

- bullish: precision=46.32%, recall=23.91%, F1=31.54%
- neutral: precision=8.01%, recall=50.00%, F1=13.80%
- bearish: precision=41.38%, recall=25.32%, F1=31.41%

#### 16-candle horizon

- Records: 1104
- Accuracy: 27.17%
- Balanced accuracy: 29.05%
- Macro precision: 34.24%
- Macro recall: 29.05%
- Macro F1: 25.12%
- Directional accuracy: 49.82%

Confusion matrix (rows=prediction, columns=actual):

| Prediction | Bullish | Neutral | Bearish |
|---|---:|---:|---:|
| bullish | 146 | 15 | 119 |
| neutral | 271 | 16 | 247 |
| bearish | 135 | 17 | 138 |

- bullish: precision=52.14%, recall=26.45%, F1=35.10%
- neutral: precision=3.00%, recall=33.33%, F1=5.50%
- bearish: precision=47.59%, recall=27.38%, F1=34.76%

### Threshold ±0.05%

#### 4-candle horizon

- Records: 1116
- Accuracy: 33.69%
- Balanced accuracy: 34.38%
- Macro precision: 33.79%
- Macro recall: 34.38%
- Macro F1: 32.99%
- Directional accuracy: 34.02%

Confusion matrix (rows=prediction, columns=actual):

| Prediction | Bullish | Neutral | Bearish |
|---|---:|---:|---:|
| bullish | 99 | 84 | 106 |
| neutral | 191 | 179 | 167 |
| bearish | 111 | 81 | 98 |

- bullish: precision=34.26%, recall=24.69%, F1=28.70%
- neutral: precision=33.33%, recall=52.03%, F1=40.64%
- bearish: precision=33.79%, recall=26.42%, F1=29.65%

#### 8-candle horizon

- Records: 1112
- Accuracy: 28.96%
- Balanced accuracy: 31.97%
- Macro precision: 31.30%
- Macro recall: 31.97%
- Macro F1: 28.99%
- Directional accuracy: 36.52%

Confusion matrix (rows=prediction, columns=actual):

| Prediction | Bullish | Neutral | Bearish |
|---|---:|---:|---:|
| bullish | 103 | 70 | 112 |
| neutral | 231 | 112 | 194 |
| bearish | 131 | 52 | 107 |

- bullish: precision=36.14%, recall=22.15%, F1=27.47%
- neutral: precision=20.86%, recall=47.86%, F1=29.05%
- bearish: precision=36.90%, recall=25.91%, F1=30.44%

#### 16-candle horizon

- Records: 1104
- Accuracy: 27.63%
- Balanced accuracy: 28.78%
- Macro precision: 33.04%
- Macro recall: 28.78%
- Macro F1: 27.15%
- Directional accuracy: 44.91%

Confusion matrix (rows=prediction, columns=actual):

| Prediction | Bullish | Neutral | Bearish |
|---|---:|---:|---:|
| bullish | 136 | 47 | 97 |
| neutral | 254 | 49 | 231 |
| bearish | 116 | 54 | 120 |

- bullish: precision=48.57%, recall=26.88%, F1=34.61%
- neutral: precision=9.18%, recall=32.67%, F1=14.33%
- bearish: precision=41.38%, recall=26.79%, F1=32.52%

### Threshold ±0.10%

#### 4-candle horizon

- Records: 1116
- Accuracy: 39.43%
- Balanced accuracy: 33.42%
- Macro precision: 33.57%
- Macro recall: 33.42%
- Macro F1: 33.13%
- Directional accuracy: 20.38%

Confusion matrix (rows=prediction, columns=actual):

| Prediction | Bullish | Neutral | Bearish |
|---|---:|---:|---:|
| bullish | 53 | 170 | 66 |
| neutral | 113 | 322 | 102 |
| bearish | 64 | 161 | 65 |

- bullish: precision=18.34%, recall=23.04%, F1=20.42%
- neutral: precision=59.96%, recall=49.31%, F1=54.12%
- bearish: precision=22.41%, recall=27.90%, F1=24.86%

#### 8-candle horizon

- Records: 1112
- Accuracy: 32.10%
- Balanced accuracy: 30.33%
- Macro precision: 30.13%
- Macro recall: 30.33%
- Macro F1: 30.07%
- Directional accuracy: 25.74%

Confusion matrix (rows=prediction, columns=actual):

| Prediction | Bullish | Neutral | Bearish |
|---|---:|---:|---:|
| bullish | 74 | 124 | 87 |
| neutral | 178 | 209 | 150 |
| bearish | 91 | 125 | 74 |

- bullish: precision=25.96%, recall=21.57%, F1=23.57%
- neutral: precision=38.92%, recall=45.63%, F1=42.01%
- bearish: precision=25.52%, recall=23.79%, F1=24.63%

#### 16-candle horizon

- Records: 1104
- Accuracy: 28.89%
- Balanced accuracy: 29.53%
- Macro precision: 31.47%
- Macro recall: 29.53%
- Macro F1: 29.03%
- Directional accuracy: 37.02%

Confusion matrix (rows=prediction, columns=actual):

| Prediction | Bullish | Neutral | Bearish |
|---|---:|---:|---:|
| bullish | 117 | 87 | 76 |
| neutral | 224 | 108 | 202 |
| bearish | 95 | 101 | 94 |

- bullish: precision=41.79%, recall=26.83%, F1=32.68%
- neutral: precision=20.22%, recall=36.49%, F1=26.02%
- bearish: precision=32.41%, recall=25.27%, F1=28.40%

### Threshold ±0.15%

#### 4-candle horizon

- Records: 1116
- Accuracy: 43.64%
- Balanced accuracy: 33.60%
- Macro precision: 33.89%
- Macro recall: 33.60%
- Macro F1: 30.96%
- Directional accuracy: 11.92%

Confusion matrix (rows=prediction, columns=actual):

| Prediction | Bullish | Neutral | Bearish |
|---|---:|---:|---:|
| bullish | 31 | 216 | 42 |
| neutral | 58 | 418 | 61 |
| bearish | 37 | 215 | 38 |

- bullish: precision=10.73%, recall=24.60%, F1=14.94%
- neutral: precision=77.84%, recall=49.23%, F1=60.32%
- bearish: precision=13.10%, recall=26.95%, F1=17.63%

#### 8-candle horizon

- Records: 1112
- Accuracy: 38.04%
- Balanced accuracy: 32.00%
- Macro precision: 32.23%
- Macro recall: 32.00%
- Macro F1: 31.80%
- Directional accuracy: 19.30%

Confusion matrix (rows=prediction, columns=actual):

| Prediction | Bullish | Neutral | Bearish |
|---|---:|---:|---:|
| bullish | 54 | 166 | 65 |
| neutral | 119 | 312 | 106 |
| bearish | 64 | 169 | 57 |

- bullish: precision=18.95%, recall=22.78%, F1=20.69%
- neutral: precision=58.10%, recall=48.22%, F1=52.70%
- bearish: precision=19.66%, recall=25.00%, F1=22.01%

#### 16-candle horizon

- Records: 1104
- Accuracy: 31.97%
- Balanced accuracy: 30.61%
- Macro precision: 30.86%
- Macro recall: 30.61%
- Macro F1: 30.50%
- Directional accuracy: 28.25%

Confusion matrix (rows=prediction, columns=actual):

| Prediction | Bullish | Neutral | Bearish |
|---|---:|---:|---:|
| bullish | 89 | 123 | 68 |
| neutral | 184 | 192 | 158 |
| bearish | 83 | 135 | 72 |

- bullish: precision=31.79%, recall=25.00%, F1=27.99%
- neutral: precision=35.96%, recall=42.67%, F1=39.02%
- bearish: precision=24.83%, recall=24.16%, F1=24.49%

### Threshold ±0.20%

#### 4-candle horizon

- Records: 1116
- Accuracy: 45.34%
- Balanced accuracy: 32.35%
- Macro precision: 33.58%
- Macro recall: 32.35%
- Macro F1: 28.16%
- Directional accuracy: 7.08%

Confusion matrix (rows=prediction, columns=actual):

| Prediction | Bullish | Neutral | Bearish |
|---|---:|---:|---:|
| bullish | 16 | 243 | 30 |
| neutral | 34 | 465 | 38 |
| bearish | 26 | 239 | 25 |

- bullish: precision=5.54%, recall=21.05%, F1=8.77%
- neutral: precision=86.59%, recall=49.10%, F1=62.67%
- bearish: precision=8.62%, recall=26.88%, F1=13.05%

#### 8-candle horizon

- Records: 1112
- Accuracy: 40.92%
- Balanced accuracy: 31.12%
- Macro precision: 32.11%
- Macro recall: 31.12%
- Macro F1: 29.90%
- Directional accuracy: 12.52%

Confusion matrix (rows=prediction, columns=actual):

| Prediction | Bullish | Neutral | Bearish |
|---|---:|---:|---:|
| bullish | 30 | 206 | 49 |
| neutral | 80 | 383 | 74 |
| bearish | 42 | 206 | 42 |

- bullish: precision=10.53%, recall=19.74%, F1=13.73%
- neutral: precision=71.32%, recall=48.18%, F1=57.51%
- bearish: precision=14.48%, recall=25.45%, F1=18.46%

#### 16-candle horizon

- Records: 1104
- Accuracy: 33.97%
- Balanced accuracy: 29.89%
- Macro precision: 29.98%
- Macro recall: 29.89%
- Macro F1: 29.86%
- Directional accuracy: 21.05%

Confusion matrix (rows=prediction, columns=actual):

| Prediction | Bullish | Neutral | Bearish |
|---|---:|---:|---:|
| bullish | 66 | 156 | 58 |
| neutral | 149 | 255 | 130 |
| bearish | 68 | 168 | 54 |

- bullish: precision=23.57%, recall=23.32%, F1=23.45%
- neutral: precision=47.75%, recall=44.04%, F1=45.82%
- bearish: precision=18.62%, recall=22.31%, F1=20.30%

### Threshold ±0.30%

#### 4-candle horizon

- Records: 1116
- Accuracy: 47.22%
- Balanced accuracy: 28.27%
- Macro precision: 33.30%
- Macro recall: 28.27%
- Macro F1: 23.85%
- Directional accuracy: 1.90%

Confusion matrix (rows=prediction, columns=actual):

| Prediction | Bullish | Neutral | Bearish |
|---|---:|---:|---:|
| bullish | 3 | 272 | 14 |
| neutral | 9 | 516 | 12 |
| bearish | 12 | 270 | 8 |

- bullish: precision=1.04%, recall=12.50%, F1=1.92%
- neutral: precision=96.09%, recall=48.77%, F1=64.70%
- bearish: precision=2.76%, recall=23.53%, F1=4.94%

#### 8-candle horizon

- Records: 1112
- Accuracy: 44.33%
- Balanced accuracy: 26.92%
- Macro precision: 31.89%
- Macro recall: 26.92%
- Macro F1: 25.15%
- Directional accuracy: 4.17%

Confusion matrix (rows=prediction, columns=actual):

| Prediction | Bullish | Neutral | Bearish |
|---|---:|---:|---:|
| bullish | 7 | 250 | 28 |
| neutral | 31 | 469 | 37 |
| bearish | 22 | 251 | 17 |

- bullish: precision=2.46%, recall=11.67%, F1=4.06%
- neutral: precision=87.34%, recall=48.35%, F1=62.24%
- bearish: precision=5.86%, recall=20.73%, F1=9.14%

#### 16-candle horizon

- Records: 1104
- Accuracy: 40.67%
- Balanced accuracy: 30.71%
- Macro precision: 31.52%
- Macro recall: 30.71%
- Macro F1: 28.95%
- Directional accuracy: 11.23%

Confusion matrix (rows=prediction, columns=actual):

| Prediction | Bullish | Neutral | Bearish |
|---|---:|---:|---:|
| bullish | 33 | 210 | 37 |
| neutral | 76 | 385 | 73 |
| bearish | 33 | 226 | 31 |

- bullish: precision=11.79%, recall=23.24%, F1=15.64%
- neutral: precision=72.10%, recall=46.89%, F1=56.83%
- bearish: precision=10.69%, recall=21.99%, F1=14.39%

## Calibration Rules

The calibration process does not select a threshold using raw accuracy alone.

The calibration score considers:
- Balanced accuracy
- Macro F1
- Neutral-class F1
- Cross-horizon stability

The purpose is to find a threshold that produces meaningful and stable classes rather than simply maximizing one metric.

## Important

Historical classification performance is not future prediction probability.

The recommended threshold must be validated before being adopted by a future MLAI version.