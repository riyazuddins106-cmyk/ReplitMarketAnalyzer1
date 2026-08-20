# MLAI v3.8 MARKET STRUCTURE PREDICTIVE VALIDATION

Research-only chronological validation.

================================================================================
PROTECTION CHECK
================================================================================
market_data.bin : READ ONLY
Production MLAI : NOT MODIFIED
Learning memory : NOT MODIFIED
Trading         : DISABLED
Model training  : DISABLED
Internet        : NOT REQUIRED

================================================================================
DATA QUALITY
================================================================================
Valid OHLC candles: 1309
Invalid candles skipped: 0

================================================================================
CONFIRMED SWING DETECTION
================================================================================
Raw confirmed swings: 225

================================================================================
MARKET STRUCTURE SWINGS
================================================================================
Swing highs: 90
Swing lows: 89
Cleaned swings: 179

================================================================================
DATASET
================================================================================
Total candles: 1309
Training candles: 916
OOS candles: 393
Training signals: 191
OOS signals: 75

================================================================================
TRAINING-ONLY BASELINES
================================================================================
H+4: BUY=52.88% | SELL=47.12% | NEUTRAL=0.00% | Majority=BUY
H+8: BUY=53.40% | SELL=45.03% | NEUTRAL=1.57% | Majority=BUY
H+16: BUY=49.74% | SELL=50.26% | NEUTRAL=0.00% | Majority=SELL

================================================================================
OOS FEATURE VALIDATION
================================================================================

--------------------------------------------------------------------------------
ALL_STRUCTURE
--------------------------------------------------------------------------------
H+4 | N=75 | Accuracy=48.00% | Precision=54.76% | Recall=57.50% | AvgReturn=+0.0149% | Baseline=52.88% | Edge=-4.88%
H+8 | N=74 | Accuracy=56.76% | Precision=61.90% | Recall=65.00% | AvgReturn=+0.0230% | Baseline=53.40% | Edge=+3.35%
H+16 | N=73 | Accuracy=53.42% | Precision=64.29% | Recall=62.79% | AvgReturn=+0.0070% | Baseline=50.26% | Edge=+3.16%

--------------------------------------------------------------------------------
STRUCTURE_ATR
--------------------------------------------------------------------------------
H+4 | N=75 | Accuracy=33.33% | Precision=53.33% | Recall=60.00% | AvgReturn=+0.0149% | Baseline=52.88% | Edge=-19.55%
H+8 | N=74 | Accuracy=36.49% | Precision=60.00% | Recall=67.50% | AvgReturn=+0.0230% | Baseline=53.40% | Edge=-16.92%
H+16 | N=73 | Accuracy=39.73% | Precision=62.22% | Recall=65.12% | AvgReturn=+0.0070% | Baseline=50.26% | Edge=-10.54%

--------------------------------------------------------------------------------
STRUCTURE_MOMENTUM
--------------------------------------------------------------------------------
H+4 | N=75 | Accuracy=33.33% | Precision=51.72% | Recall=37.50% | AvgReturn=+0.0149% | Baseline=52.88% | Edge=-19.55%
H+8 | N=74 | Accuracy=29.73% | Precision=51.72% | Recall=37.50% | AvgReturn=+0.0230% | Baseline=53.40% | Edge=-23.67%
H+16 | N=73 | Accuracy=30.14% | Precision=51.72% | Recall=34.88% | AvgReturn=+0.0070% | Baseline=50.26% | Edge=-20.12%

--------------------------------------------------------------------------------
STRUCTURE_CANDLE
--------------------------------------------------------------------------------
H+4 | N=75 | Accuracy=29.33% | Precision=50.00% | Recall=32.50% | AvgReturn=+0.0149% | Baseline=52.88% | Edge=-23.55%
H+8 | N=74 | Accuracy=29.73% | Precision=53.85% | Recall=35.00% | AvgReturn=+0.0230% | Baseline=53.40% | Edge=-23.67%
H+16 | N=73 | Accuracy=32.88% | Precision=61.54% | Recall=37.21% | AvgReturn=+0.0070% | Baseline=50.26% | Edge=-17.39%

--------------------------------------------------------------------------------
STRUCTURE_LOCATION
--------------------------------------------------------------------------------
H+4 | N=75 | Accuracy=41.33% | Precision=56.67% | Recall=42.50% | AvgReturn=+0.0149% | Baseline=52.88% | Edge=-11.55%
H+8 | N=74 | Accuracy=47.30% | Precision=60.00% | Recall=45.00% | AvgReturn=+0.0230% | Baseline=53.40% | Edge=-6.11%
H+16 | N=73 | Accuracy=45.21% | Precision=66.67% | Recall=46.51% | AvgReturn=+0.0070% | Baseline=50.26% | Edge=-5.06%

--------------------------------------------------------------------------------
STRUCTURE_AGREEMENT
--------------------------------------------------------------------------------
H+4 | N=75 | Accuracy=37.33% | Precision=51.52% | Recall=42.50% | AvgReturn=+0.0149% | Baseline=52.88% | Edge=-15.55%
H+8 | N=74 | Accuracy=37.84% | Precision=54.55% | Recall=45.00% | AvgReturn=+0.0230% | Baseline=53.40% | Edge=-15.57%
H+16 | N=73 | Accuracy=38.36% | Precision=57.58% | Recall=44.19% | AvgReturn=+0.0070% | Baseline=50.26% | Edge=-11.91%

--------------------------------------------------------------------------------
STRUCTURE_ATR_MOMENTUM
--------------------------------------------------------------------------------
H+4 | N=75 | Accuracy=54.67% | Precision=55.93% | Recall=82.50% | AvgReturn=+0.0149% | Baseline=52.88% | Edge=+1.79%
H+8 | N=74 | Accuracy=52.70% | Precision=54.24% | Recall=80.00% | AvgReturn=+0.0230% | Baseline=53.40% | Edge=-0.70%
H+16 | N=73 | Accuracy=56.16% | Precision=59.32% | Recall=81.40% | AvgReturn=+0.0070% | Baseline=50.26% | Edge=+5.90%

--------------------------------------------------------------------------------
STRUCTURE_FULL_CONTEXT
--------------------------------------------------------------------------------
H+4 | N=75 | Accuracy=46.67% | Precision=51.11% | Recall=57.50% | AvgReturn=+0.0149% | Baseline=52.88% | Edge=-6.21%
H+8 | N=74 | Accuracy=41.89% | Precision=46.67% | Recall=52.50% | AvgReturn=+0.0230% | Baseline=53.40% | Edge=-11.51%
H+16 | N=73 | Accuracy=49.32% | Precision=57.78% | Recall=60.47% | AvgReturn=+0.0070% | Baseline=50.26% | Edge=-0.95%

================================================================================
STRUCTURE EVENTS
================================================================================

--------------------------------------------------------------------------------
BOS_BULLISH
--------------------------------------------------------------------------------
H+4 | N=7 | Accuracy=57.14% | Precision=80.00% | Recall=66.67% | AvgReturn=+0.0472% | Baseline=52.88% | Edge=+4.26%
H+8 | N=7 | Accuracy=85.71% | Precision=80.00% | Recall=100.00% | AvgReturn=+0.0952% | Baseline=53.40% | Edge=+32.31%
H+16 | N=7 | Accuracy=42.86% | Precision=60.00% | Recall=60.00% | AvgReturn=+0.1214% | Baseline=50.26% | Edge=-7.40%

--------------------------------------------------------------------------------
BOS_BEARISH
--------------------------------------------------------------------------------
H+4 | N=4 | Accuracy=50.00% | Precision=50.00% | Recall=100.00% | AvgReturn=+0.0574% | Baseline=52.88% | Edge=-2.88%
H+8 | N=4 | Accuracy=75.00% | Precision=75.00% | Recall=100.00% | AvgReturn=+0.0586% | Baseline=53.40% | Edge=+21.60%
H+16 | N=4 | Accuracy=50.00% | Precision=50.00% | Recall=100.00% | AvgReturn=+0.0218% | Baseline=50.26% | Edge=-0.26%

--------------------------------------------------------------------------------
CHoCH_BULLISH
--------------------------------------------------------------------------------
H+4 | N=10 | Accuracy=40.00% | Precision=40.00% | Recall=40.00% | AvgReturn=-0.0237% | Baseline=52.88% | Edge=-12.88%
H+8 | N=10 | Accuracy=60.00% | Precision=40.00% | Recall=66.67% | AvgReturn=+0.0059% | Baseline=53.40% | Edge=+6.60%
H+16 | N=10 | Accuracy=50.00% | Precision=60.00% | Recall=50.00% | AvgReturn=-0.0376% | Baseline=50.26% | Edge=-0.26%

--------------------------------------------------------------------------------
CHoCH_BEARISH
--------------------------------------------------------------------------------
H+4 | N=14 | Accuracy=64.29% | Precision=71.43% | Recall=71.43% | AvgReturn=+0.0172% | Baseline=52.88% | Edge=+11.41%
H+8 | N=14 | Accuracy=71.43% | Precision=71.43% | Recall=71.43% | AvgReturn=+0.0093% | Baseline=53.40% | Edge=+18.03%
H+16 | N=14 | Accuracy=71.43% | Precision=85.71% | Recall=66.67% | AvgReturn=-0.0528% | Baseline=50.26% | Edge=+21.17%

================================================================================
INTEGRITY
================================================================================
Timestamp order: PASS
Structure event timing: PASS
OOS signal order: PASS
Future outcome separation: PASS

================================================================================
PROTECTION
================================================================================
market_data.bin : READ ONLY
Production MLAI : NOT MODIFIED
Learning memory : NOT MODIFIED
Trading         : DISABLED
Model training  : DISABLED
Internet        : NOT REQUIRED

================================================================================
OUTPUT
================================================================================
MLAI_V38_MARKET_STRUCTURE_PREDICTIVE_VALIDATION.bin
MLAI_V38_MARKET_STRUCTURE_PREDICTIVE_VALIDATION_REPORT.md