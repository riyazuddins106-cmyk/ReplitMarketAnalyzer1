# MLAI v4.0.0 Causal Market Structure Validation

## Protection

- Market data SHA256 before: `dd57bccc3526ebaeb900181096adcbf48a84b5a3a334da1f1990a443cde091b5`
- Market data SHA256 after: `dd57bccc3526ebaeb900181096adcbf48a84b5a3a334da1f1990a443cde091b5`
- Market data modification: NO
- Production MLAI modification: NO
- Learning memory modification: NO
- Trading: DISABLED
- Internet required: NO

## Dataset

- Valid candles: 1309
- Invalid candles: 0
- Timestamp order: True
- Duplicate timestamps: False

## Causal Structure

- Confirmed swings: 248
- Structure states: 1309
- Structural events: 81
- ATR observations: 1296

## Event Counts

- BOS_BULLISH: 24
- BOS_BEARISH: 0
- CHoCH_BULLISH: 18
- CHoCH_BEARISH: 39

## Causality Audits

- Confirmed swing timing: PASS
- Future structure leakage: PASS
- Future event leakage: PASS
- Structural level consumption: PASS
- Training label boundary: PASS
- Walk-forward boundaries: PASS

## Walk-Forward Results

### H+4

- Mean accuracy: 53.44%
- Median accuracy: 51.79%
- Std: 16.98%
- Min: 35.19%
- Max: 75.47%
- Mean balanced accuracy: 54.13%
- Mean edge: -5.64%
- Positive-edge windows: 2
- Negative-edge windows: 2

### H+8

- Mean accuracy: 49.45%
- Median accuracy: 54.29%
- Std: 15.90%
- Min: 25.49%
- Max: 63.83%
- Mean balanced accuracy: 48.46%
- Mean edge: -9.09%
- Positive-edge windows: 3
- Negative-edge windows: 2

### H+16

- Mean accuracy: 41.12%
- Median accuracy: 42.86%
- Std: 7.12%
- Min: 30.43%
- Max: 48.84%
- Mean balanced accuracy: 46.11%
- Mean edge: -28.37%
- Positive-edge windows: 0
- Negative-edge windows: 5

## Per-Window Results

### Window 1
TRAIN [0:904]
OOS [904:985]

H+4: N=81 | Accuracy=75.47% | Balanced=69.87% | Baseline=39.62% | Edge=35.85% | Coverage=65.43%
H+8: N=81 | Accuracy=63.83% | Balanced=66.00% | Baseline=53.19% | Edge=10.64% | Coverage=58.02%
H+16: N=81 | Accuracy=38.18% | Balanced=51.25% | Baseline=72.73% | Edge=-34.55% | Coverage=67.90%

### Window 2
TRAIN [0:985]
OOS [985:1066]

H+4: N=80 | Accuracy=35.19% | Balanced=38.21% | Baseline=59.26% | Edge=-24.07% | Coverage=67.50%
H+8: N=80 | Accuracy=25.49% | Balanced=29.93% | Baseline=62.75% | Edge=-37.25% | Coverage=63.75%
H+16: N=80 | Accuracy=30.43% | Balanced=42.19% | Baseline=71.74% | Edge=-41.30% | Coverage=57.50%

### Window 3
TRAIN [0:1066]
OOS [1066:1147]

H+4: N=81 | Accuracy=51.79% | Balanced=50.64% | Baseline=51.79% | Edge=0.00% | Coverage=69.14%
H+8: N=80 | Accuracy=61.70% | Balanced=58.97% | Baseline=44.68% | Edge=17.02% | Coverage=58.75%
H+16: N=81 | Accuracy=45.28% | Balanced=44.51% | Baseline=73.58% | Edge=-28.30% | Coverage=65.43%

### Window 4
TRAIN [0:1147]
OOS [1147:1228]

H+4: N=81 | Accuracy=39.53% | Balanced=43.92% | Baseline=86.05% | Edge=-46.51% | Coverage=53.09%
H+8: N=81 | Accuracy=41.94% | Balanced=32.33% | Baseline=80.65% | Edge=-38.71% | Coverage=38.27%
H+16: N=81 | Accuracy=48.84% | Balanced=43.69% | Baseline=65.12% | Edge=-16.28% | Coverage=53.09%

### Window 5
TRAIN [0:1228]
OOS [1228:1309]

H+4: N=77 | Accuracy=65.22% | Balanced=68.03% | Baseline=58.70% | Edge=6.52% | Coverage=59.74%
H+8: N=73 | Accuracy=54.29% | Balanced=55.07% | Baseline=51.43% | Edge=2.86% | Coverage=47.95%
H+16: N=65 | Accuracy=42.86% | Balanced=48.89% | Baseline=64.29% | Edge=-21.43% | Coverage=43.08%

## Important Interpretation

Accuracy alone is NOT treated as evidence of predictive power.

The system requires positive out-of-sample edge, reasonable balanced accuracy, sufficient coverage, and stability across walk-forward windows.

Unknown or weakly supported structural states are allowed to abstain instead of forcing BUY/SELL.

Calibration is fitted only on training observations.

OOS observations are never used to construct the model, encoder, or calibration temperature.

## Event Diagnostics

### BOS_BULLISH
- H+4, Window 1: N=38 | Accuracy=47.37% | Baseline=0.00% | Edge=-52.63%
- H+4, Window 2: N=22 | Accuracy=36.36% | Baseline=0.00% | Edge=-63.64%
- H+4, Window 4: N=53 | Accuracy=66.04% | Baseline=66.04% | Edge=0.00%
- H+8, Window 1: N=38 | Accuracy=50.00% | Baseline=50.00% | Edge=0.00%
- H+8, Window 2: N=22 | Accuracy=36.36% | Baseline=0.00% | Edge=-63.64%
- H+8, Window 4: N=53 | Accuracy=66.04% | Baseline=66.04% | Edge=0.00%
- H+16, Window 1: N=38 | Accuracy=26.32% | Baseline=0.00% | Edge=-73.68%
- H+16, Window 2: N=22 | Accuracy=13.64% | Baseline=0.00% | Edge=-86.36%
- H+16, Window 4: N=53 | Accuracy=67.92% | Baseline=67.92% | Edge=0.00%

### BOS_BEARISH
- H+4: insufficient sample
- H+8: insufficient sample
- H+16: insufficient sample

### CHoCH_BULLISH
- H+4, Window 1: N=18 | Accuracy=22.22% | Baseline=0.00% | Edge=-77.78%
- H+4, Window 3: N=42 | Accuracy=47.62% | Baseline=0.00% | Edge=-52.38%
- H+4, Window 4: N=28 | Accuracy=82.14% | Baseline=82.14% | Edge=0.00%
- H+8, Window 1: N=18 | Accuracy=16.67% | Baseline=0.00% | Edge=-83.33%
- H+8, Window 3: N=41 | Accuracy=46.34% | Baseline=0.00% | Edge=-53.66%
- H+8, Window 4: N=28 | Accuracy=89.29% | Baseline=89.29% | Edge=0.00%
- H+16, Window 1: N=18 | Accuracy=38.89% | Baseline=0.00% | Edge=-61.11%
- H+16, Window 3: N=42 | Accuracy=66.67% | Baseline=66.67% | Edge=0.00%
- H+16, Window 4: N=28 | Accuracy=92.86% | Baseline=92.86% | Edge=0.00%

### CHoCH_BEARISH
- H+4, Window 1: N=25 | Accuracy=28.00% | Baseline=72.00% | Edge=-44.00%
- H+4, Window 2: N=53 | Accuracy=62.26% | Baseline=0.00% | Edge=-37.74%
- H+4, Window 3: N=39 | Accuracy=48.72% | Baseline=51.28% | Edge=-2.56%
- H+4, Window 5: N=71 | Accuracy=54.93% | Baseline=0.00% | Edge=-45.07%
- H+8, Window 1: N=25 | Accuracy=44.00% | Baseline=56.00% | Edge=-12.00%
- H+8, Window 2: N=53 | Accuracy=64.15% | Baseline=0.00% | Edge=-35.85%
- H+8, Window 3: N=39 | Accuracy=35.90% | Baseline=64.10% | Edge=-28.21%
- H+8, Window 5: N=67 | Accuracy=62.69% | Baseline=0.00% | Edge=-37.31%
- H+16, Window 1: N=25 | Accuracy=80.00% | Baseline=0.00% | Edge=-20.00%
- H+16, Window 2: N=53 | Accuracy=64.15% | Baseline=0.00% | Edge=-35.85%
- H+16, Window 3: N=39 | Accuracy=23.08% | Baseline=76.92% | Edge=-53.85%
- H+16, Window 5: N=59 | Accuracy=81.36% | Baseline=0.00% | Edge=-18.64%

## Final Protection

Market data unchanged: PASS
Production MLAI modified: NO
Learning memory modified: NO
Trading enabled: NO

MLAI v4.0.0 CAUSAL MARKET STRUCTURE VALIDATION COMPLETE