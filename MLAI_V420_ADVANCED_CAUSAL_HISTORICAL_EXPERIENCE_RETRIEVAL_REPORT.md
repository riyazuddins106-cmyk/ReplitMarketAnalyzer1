# MLAI v4.1.6 Robust Causal Historical Experience Retrieval

## Phase scope

- Historical retrieval only
- Probability calibration: NOT ADDED
- Scenario reasoning: NOT ADDED
- Human-language generation: NOT ADDED
- Multi-timeframe reasoning: NOT ADDED
- Continuous learning: NOT ADDED
- Live data: NOT ADDED

## Architecture

- Canonical causal MarketState: ENABLED
- Causal structure / sequence / regime: ENABLED
- ATR-normalized outcomes: ENABLED
- Causal eligibility filter: ENABLED
- Coarse-to-fine retrieval: ENABLED
- Multi-layer similarity: ENABLED
- Causal path similarity: ENABLED
- Temporal episode de-duplication: ENABLED
- Supporting/conflicting evidence: ENABLED
- Sparse-evidence warning: ENABLED
- Retrieval-vs-baseline diagnostics: ENABLED
- Similarity bucket analysis: ENABLED
- Training-only null retrieval sanity test: ENABLED
- OOS outcomes used for retrieval: NO

## Dataset / causality

- Valid candles: 1309
- Invalid candles: 0
- Confirmed swings: 225
- Chronology: PASS
- Duplicate timestamps: PASS
- Causal structure: PASS

## Walk-forward results

### H+4
- Retrieval accuracy: 46.19%
- Baseline accuracy: 44.97%
- Retrieval Brier: 0.2138
- Baseline Brier: 0.2068
- Brier lift: -0.0070
- Retrieval log loss: 1.2663
- Baseline log loss: 1.0214
- Log-loss lift: -0.2449
- Coverage: 100.00%
- Sparse rate: 0.00%
- Mean top similarity: 87.52%
- Mean independent matches: 15.96

### H+8
- Retrieval accuracy: 47.97%
- Baseline accuracy: 50.27%
- Retrieval Brier: 0.2035
- Baseline Brier: 0.1989
- Brier lift: -0.0047
- Retrieval log loss: 1.1835
- Baseline log loss: 1.0582
- Log-loss lift: -0.1253
- Coverage: 100.00%
- Sparse rate: 0.00%
- Mean top similarity: 87.73%
- Mean independent matches: 15.95

### H+16
- Retrieval accuracy: 47.13%
- Baseline accuracy: 49.05%
- Retrieval Brier: 0.2063
- Baseline Brier: 0.2022
- Brier lift: -0.0041
- Retrieval log loss: 1.1930
- Baseline log loss: 1.0295
- Log-loss lift: -0.1635
- Coverage: 100.00%
- Sparse rate: 0.00%
- Mean top similarity: 86.93%
- Mean independent matches: 15.93

## Similarity bucket diagnostics

### MODERATE
- Samples: 2
- Accuracy: 50.00%
- Retrieval Brier: 0.2129
- Baseline Brier: 0.1927
- Brier lift: -0.0202

### MODERATE_STRONG
- Samples: 75
- Accuracy: 37.33%
- Retrieval Brier: 0.2274
- Baseline Brier: 0.2231
- Brier lift: -0.0042

### STRONG
- Samples: 1110
- Accuracy: 47.66%
- Retrieval Brier: 0.2066
- Baseline Brier: 0.2013
- Brier lift: -0.0054

## Null retrieval sanity test

- Queries: 1187
- Mean real maximum share: 55.25%
- Mean null maximum share: 54.45%
- Mean null 95th percentile: 65.61%
- Mean real-minus-null: 0.80%

## Interpretation

v4.1.6 tests retrieval quality, not trading performance. Historical outcome shares are evidence distributions and are not presented as calibrated probabilities.

Promotion to v4.1.7 should require retrieval to demonstrate stable out-of-sample usefulness against appropriate baselines and sensible behaviour across similarity buckets.

## Protection

- market_data.bin unchanged: PASS
- Production MLAI modified: NO
- Learning memory modified: NO
- Trading enabled: NO

MLAI v4.1.6 COMPLETE