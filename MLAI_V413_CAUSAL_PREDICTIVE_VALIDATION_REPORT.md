# MLAI v4.1.3 Robust Causal Predictive Validation

## Protection

- Market data SHA256 before: `dd57bccc3526ebaeb900181096adcbf48a84b5a3a334da1f1990a443cde091b5`
- Market data SHA256 after: `dd57bccc3526ebaeb900181096adcbf48a84b5a3a334da1f1990a443cde091b5`
- Market data modification: NO
- Production MLAI modification: NO
- Learning memory modification: NO
- Trading: DISABLED
- Internet required: NO

## Predictive Architecture

- Causal market structure: YES
- Causal price / volatility features: YES
- Hierarchical structural-state model: YES
- Regularized logistic model: YES
- Distance-weighted kNN model: YES
- Fixed ensemble: YES
- Training-only scaling: ENFORCED
- Training-only state statistics: ENFORCED
- Frozen OOS model: ENFORCED
- OOS tuning: NO
- v4.1.3 reduced abstention policy: YES

## Dataset

- Valid candles: 1309
- Invalid candles: 0
- Timestamp order: True
- Duplicate timestamps: False

## Causal Structure

- Confirmed swings: 225
- Structure states: 1309
- Structural events: 1309
- ATR observations: 1296

## Event Counts

- BOS_BULLISH: 23
- BOS_BEARISH: 18
- CHoCH_BULLISH: 18
- CHoCH_BEARISH: 18

## Causality Audits

- Causal structure audit: PASS
- Training label boundary: PASS
- Walk-forward boundaries: PASS
- Training-only feature scaling: ENFORCED
- Training-only state learning: ENFORCED
- Frozen OOS models: ENFORCED

## V4.1.3 Decision Policy

- Minimum confidence: 0.45
- Minimum probability margin: 0.020
- State support for full confidence: 20
- Thresholds fixed before OOS evaluation: YES
- OOS threshold optimization: NO

## Combined Walk-Forward Results

### H+4

- Mean accuracy: 42.87%
- Median accuracy: 50.00%
- Std accuracy: 22.88%
- Min accuracy: 0.00%
- Max accuracy: 68.18%
- Mean balanced accuracy: 39.00%
- Mean edge: -23.65%
- Positive-edge windows: 1
- Negative-edge windows: 4
- Mean coverage: 30.77%
- Mean Brier: 0.2662
- Mean log loss: 0.7259
- Mean calibration error: 19.38%
- Mean confidence: 42.25%
- Mean state support: 10.67

### H+8

- Mean accuracy: 53.14%
- Median accuracy: 50.00%
- Std accuracy: 13.45%
- Min accuracy: 36.36%
- Max accuracy: 73.33%
- Mean balanced accuracy: 48.00%
- Mean edge: -10.81%
- Positive-edge windows: 0
- Negative-edge windows: 3
- Mean coverage: 28.74%
- Mean Brier: 0.2554
- Mean log loss: 0.7043
- Mean calibration error: 15.14%
- Mean confidence: 42.46%
- Mean state support: 10.60

### H+16

- Mean accuracy: 53.32%
- Median accuracy: 50.00%
- Std accuracy: 14.53%
- Min accuracy: 31.43%
- Max accuracy: 72.92%
- Mean balanced accuracy: 48.50%
- Mean edge: -16.12%
- Positive-edge windows: 0
- Negative-edge windows: 3
- Mean coverage: 37.75%
- Mean Brier: 0.2572
- Mean log loss: 0.7083
- Mean calibration error: 19.06%
- Mean confidence: 43.83%
- Mean state support: 10.47

## Per-Window Results

### Window 1
- TRAIN [0:904]
- OOS [904:985]

- H+4: Train=894 | OOS=81 | States=164 | Accuracy=52.17% | Balanced=42.86% | Baseline=60.87% | Edge=-8.70% | Coverage=28.40% | Brier=0.2603 | LogLoss=0.7141 | Confidence=42.05%
- H+8: Train=894 | OOS=81 | States=163 | Accuracy=63.16% | Balanced=50.00% | Baseline=63.16% | Edge=0.00% | Coverage=23.46% | Brier=0.2460 | LogLoss=0.6856 | Confidence=41.97%
- H+16: Train=886 | OOS=81 | States=164 | Accuracy=47.06% | Balanced=53.75% | Baseline=67.65% | Edge=-20.59% | Coverage=41.98% | Brier=0.2806 | LogLoss=0.7570 | Confidence=43.71%

### Window 2
- TRAIN [0:985]
- OOS [985:1066]

- H+4: Train=975 | OOS=80 | States=168 | Accuracy=50.00% | Balanced=52.98% | Baseline=53.85% | Edge=-3.85% | Coverage=32.50% | Brier=0.2621 | LogLoss=0.7177 | Confidence=42.21%
- H+8: Train=975 | OOS=80 | States=167 | Accuracy=36.36% | Balanced=50.00% | Baseline=63.64% | Edge=-27.27% | Coverage=27.50% | Brier=0.2755 | LogLoss=0.7445 | Confidence=42.82%
- H+16: Train=967 | OOS=80 | States=168 | Accuracy=31.43% | Balanced=34.00% | Baseline=71.43% | Edge=-40.00% | Coverage=43.75% | Brier=0.2930 | LogLoss=0.7805 | Confidence=44.10%

### Window 3
- TRAIN [0:1066]
- OOS [1066:1147]

- H+4: Train=1055 | OOS=81 | States=169 | Accuracy=44.00% | Balanced=45.83% | Baseline=52.00% | Edge=-8.00% | Coverage=30.86% | Brier=0.2638 | LogLoss=0.7211 | Confidence=42.06%
- H+8: Train=1055 | OOS=80 | States=168 | Accuracy=42.86% | Balanced=50.00% | Baseline=57.14% | Edge=-14.29% | Coverage=26.25% | Brier=0.2730 | LogLoss=0.7400 | Confidence=42.19%
- H+16: Train=1047 | OOS=81 | States=169 | Accuracy=65.22% | Balanced=50.00% | Baseline=65.22% | Edge=0.00% | Coverage=28.40% | Brier=0.2331 | LogLoss=0.6594 | Confidence=43.61%

### Window 4
- TRAIN [0:1147]
- OOS [1147:1228]

- H+4: Train=1136 | OOS=81 | States=169 | Accuracy=68.18% | Balanced=53.33% | Baseline=65.91% | Edge=2.27% | Coverage=54.32% | Brier=0.2348 | LogLoss=0.6627 | Confidence=44.70%
- H+8: Train=1135 | OOS=81 | States=168 | Accuracy=73.33% | Balanced=50.00% | Baseline=73.33% | Edge=0.00% | Coverage=55.56% | Brier=0.2237 | LogLoss=0.6401 | Confidence=44.69%
- H+16: Train=1128 | OOS=81 | States=169 | Accuracy=72.92% | Balanced=50.00% | Baseline=72.92% | Edge=0.00% | Coverage=59.26% | Brier=0.2296 | LogLoss=0.6525 | Confidence=46.11%

### Window 5
- TRAIN [0:1228]
- OOS [1228:1309]

- H+4: Train=1217 | OOS=77 | States=172 | Accuracy=0.00% | Balanced=0.00% | Baseline=100.00% | Edge=-100.00% | Coverage=7.79% | Brier=0.3100 | LogLoss=0.8139 | Confidence=40.25%
- H+8: Train=1216 | OOS=73 | States=171 | Accuracy=50.00% | Balanced=40.00% | Baseline=62.50% | Edge=-12.50% | Coverage=10.96% | Brier=0.2589 | LogLoss=0.7112 | Confidence=40.63%
- H+16: Train=1209 | OOS=65 | States=172 | Accuracy=50.00% | Balanced=54.76% | Baseline=70.00% | Edge=-20.00% | Coverage=15.38% | Brier=0.2497 | LogLoss=0.6923 | Confidence=41.61%

## Event Diagnostics

### BOS_BULLISH
- H+4: N=3 | Accuracy=33.33% | Edge=-66.67%
- H+8: N=4 | Accuracy=75.00% | Edge=-25.00%
- H+16: N=4 | Accuracy=50.00% | Edge=-50.00%

### BOS_BEARISH
- H+4: insufficient sample
- H+8: insufficient sample
- H+16: insufficient sample

### CHoCH_BULLISH
- H+4: insufficient sample
- H+8: N=1 | Accuracy=0.00% | Edge=-100.00%
- H+16: insufficient sample

### CHoCH_BEARISH
- H+4: insufficient sample
- H+8: insufficient sample
- H+16: insufficient sample

## Interpretation

v4.1.3 changes the predictive decision layer rather than changing the chronological validation protocol.

The less restrictive fixed abstention policy increases the number of evaluated predictions, but does not constitute evidence of predictive success.

Predictive strength still requires positive untouched OOS edge, balanced performance, useful coverage, calibration, and stability across chronological windows.

No threshold is optimized from OOS observations.

## Final Protection

Market data unchanged: PASS
- Production MLAI modified: NO
- Learning memory modified: NO
- Trading enabled: NO

MLAI v4.1.3 ROBUST CAUSAL PREDICTIVE VALIDATION COMPLETE