# MLAI v4.1.4 Market Language Foundation

## Scientific Status

- Research / validation only
- Trading: DISABLED
- Valid candles: 1309
- Confirmed swings: 225
- Causal structure: PASS
- Training boundary: PASS
- OOS boundary: PASS

## Market Language Representation

- Canonical MarketState: ENABLED
- Causal sequence state: ENABLED
- Causal regime state: ENABLED
- Historical experience records: ENABLED
- ATR-normalized outcomes: ENABLED
- UP/DOWN/NEUTRAL outcomes: ENABLED
- v4.1.3 binary benchmark retained: YES

## Benchmark

### H+4
- Mean accuracy: 43.61%
- Mean edge: -19.89%
- Mean coverage: 29.56%
- Positive-edge windows: 1
- Negative-edge windows: 3

### H+8
- Mean accuracy: 55.13%
- Mean edge: -7.57%
- Mean coverage: 31.55%
- Positive-edge windows: 0
- Negative-edge windows: 2

### H+16
- Mean accuracy: 53.49%
- Mean edge: -14.91%
- Mean coverage: 37.94%
- Positive-edge windows: 0
- Negative-edge windows: 3

## Historical Conditional Baselines

### H+4
- UP: 44.99%
- DOWN: 40.79%
- NEUTRAL: 14.22%

### H+8
- UP: 48.21%
- DOWN: 42.91%
- NEUTRAL: 8.88%

### H+16
- UP: 48.25%
- DOWN: 44.96%
- NEUTRAL: 6.78%

## Protection

- market_data.bin unchanged: PASS
- Production MLAI modified: NO
- Learning memory modified: NO
- Trading enabled: NO

MLAI v4.1.4 COMPLETE