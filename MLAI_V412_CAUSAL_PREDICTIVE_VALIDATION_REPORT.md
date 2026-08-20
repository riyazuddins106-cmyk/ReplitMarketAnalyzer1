# MLAI v4.1.2 Robust Causal Predictive Validation

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

## Combined Walk-Forward Results

### H+4

- Mean accuracy: N/A
- Median accuracy: N/A
- Std accuracy: N/A
- Min accuracy: N/A
- Max accuracy: N/A
- Mean balanced accuracy: N/A
- Mean edge: N/A
- Positive-edge windows: 0
- Negative-edge windows: 0
- Mean coverage: 0.00%
- Mean Brier: N/A
- Mean log loss: N/A
- Mean calibration error: N/A

### H+8

- Mean accuracy: N/A
- Median accuracy: N/A
- Std accuracy: N/A
- Min accuracy: N/A
- Max accuracy: N/A
- Mean balanced accuracy: N/A
- Mean edge: N/A
- Positive-edge windows: 0
- Negative-edge windows: 0
- Mean coverage: 0.00%
- Mean Brier: N/A
- Mean log loss: N/A
- Mean calibration error: N/A

### H+16

- Mean accuracy: 61.11%
- Median accuracy: 50.00%
- Std accuracy: 28.33%
- Min accuracy: 33.33%
- Max accuracy: 100.00%
- Mean balanced accuracy: 50.00%
- Mean edge: -11.11%
- Positive-edge windows: 0
- Negative-edge windows: 1
- Mean coverage: 1.49%
- Mean Brier: 0.2455
- Mean log loss: 0.6858
- Mean calibration error: 28.57%

## Per-Window Results

### Window 1
- TRAIN [0:904]
- OOS [904:985]

- H+4: Train=894 | OOS=81 | States=164 | Accuracy=N/A | Balanced=N/A | Baseline=50.62% | Edge=N/A | Coverage=0.00% | Brier=N/A | LogLoss=N/A
- H+8: Train=894 | OOS=81 | States=163 | Accuracy=N/A | Balanced=N/A | Baseline=55.56% | Edge=N/A | Coverage=0.00% | Brier=N/A | LogLoss=N/A
- H+16: Train=886 | OOS=81 | States=164 | Accuracy=33.33% | Balanced=50.00% | Baseline=66.67% | Edge=-33.33% | Coverage=3.70% | Brier=0.3510 | LogLoss=0.9076

### Window 2
- TRAIN [0:985]
- OOS [985:1066]

- H+4: Train=975 | OOS=80 | States=168 | Accuracy=N/A | Balanced=N/A | Baseline=58.75% | Edge=N/A | Coverage=0.00% | Brier=N/A | LogLoss=N/A
- H+8: Train=975 | OOS=80 | States=167 | Accuracy=N/A | Balanced=N/A | Baseline=62.50% | Edge=N/A | Coverage=0.00% | Brier=N/A | LogLoss=N/A
- H+16: Train=967 | OOS=80 | States=168 | Accuracy=50.00% | Balanced=50.00% | Baseline=50.00% | Edge=0.00% | Coverage=2.50% | Brier=0.2498 | LogLoss=0.6905

### Window 3
- TRAIN [0:1066]
- OOS [1066:1147]

- H+4: Train=1055 | OOS=81 | States=169 | Accuracy=N/A | Balanced=N/A | Baseline=50.62% | Edge=N/A | Coverage=0.00% | Brier=N/A | LogLoss=N/A
- H+8: Train=1055 | OOS=80 | States=168 | Accuracy=N/A | Balanced=N/A | Baseline=55.00% | Edge=N/A | Coverage=0.00% | Brier=N/A | LogLoss=N/A
- H+16: Train=1047 | OOS=81 | States=169 | Accuracy=N/A | Balanced=N/A | Baseline=71.60% | Edge=N/A | Coverage=0.00% | Brier=N/A | LogLoss=N/A

### Window 4
- TRAIN [0:1147]
- OOS [1147:1228]

- H+4: Train=1136 | OOS=81 | States=169 | Accuracy=N/A | Balanced=N/A | Baseline=71.60% | Edge=N/A | Coverage=0.00% | Brier=N/A | LogLoss=N/A
- H+8: Train=1135 | OOS=81 | States=168 | Accuracy=N/A | Balanced=N/A | Baseline=74.07% | Edge=N/A | Coverage=0.00% | Brier=N/A | LogLoss=N/A
- H+16: Train=1128 | OOS=81 | States=169 | Accuracy=100.00% | Balanced=50.00% | Baseline=100.00% | Edge=0.00% | Coverage=1.23% | Brier=0.1355 | LogLoss=0.4591

### Window 5
- TRAIN [0:1228]
- OOS [1228:1309]

- H+4: Train=1217 | OOS=77 | States=172 | Accuracy=N/A | Balanced=N/A | Baseline=57.14% | Edge=N/A | Coverage=0.00% | Brier=N/A | LogLoss=N/A
- H+8: Train=1216 | OOS=73 | States=171 | Accuracy=N/A | Balanced=N/A | Baseline=63.01% | Edge=N/A | Coverage=0.00% | Brier=N/A | LogLoss=N/A
- H+16: Train=1209 | OOS=65 | States=172 | Accuracy=N/A | Balanced=N/A | Baseline=76.92% | Edge=N/A | Coverage=0.00% | Brier=N/A | LogLoss=N/A

## Event Diagnostics

### BOS_BULLISH
- H+4: insufficient sample
- H+8: insufficient sample
- H+16: N=1 | Accuracy=100.00% | Edge=0.00%

### BOS_BEARISH
- H+4: insufficient sample
- H+8: insufficient sample
- H+16: insufficient sample

### CHoCH_BULLISH
- H+4: insufficient sample
- H+8: insufficient sample
- H+16: insufficient sample

### CHoCH_BEARISH
- H+4: insufficient sample
- H+8: insufficient sample
- H+16: insufficient sample

## Interpretation

This validation does not declare predictive success from accuracy alone.

Predictive strength requires positive untouched OOS edge, balanced performance, useful coverage, acceptable Brier/log-loss, calibration, and stability across chronological windows.

The predictive ensemble is deliberately fixed before OOS evaluation. Weights are not optimized against OOS observations.

Weak or uncertain predictions abstain instead of forcing a direction.

A strong result must survive additional unseen chronological data. This file therefore remains a research/validation engine and does not trade.

## Forward Label Dependency

Fixed-horizon labels may overlap in time. Overlapping labels are not treated as independent statistical observations.
Chronological OOS separation remains enforced.
No OOS outcome is used for model construction.

## Final Protection

Market data unchanged: PASS
- Production MLAI modified: NO
- Learning memory modified: NO
- Trading enabled: NO

MLAI v4.1.2 ROBUST CAUSAL PREDICTIVE VALIDATION COMPLETE