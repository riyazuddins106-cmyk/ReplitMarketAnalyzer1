# MLAI v4.1.5 Robust Causal Historical Experience Retrieval

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
- Retrieval accuracy: 43.94%
- Baseline accuracy: 44.72%
- Retrieval Brier: 0.2091
- Baseline Brier: 0.2071
- Brier lift: -0.0019
- Retrieval log loss: 1.0352
- Baseline log loss: 1.0231
- Log-loss lift: -0.0121
- Coverage: 100.00%
- Sparse rate: 0.00%
- Mean top similarity: 90.63%
- Mean independent matches: 40.00

### H+8
- Retrieval accuracy: 47.64%
- Baseline accuracy: 50.27%
- Retrieval Brier: 0.2014
- Baseline Brier: 0.1991
- Brier lift: -0.0023
- Retrieval log loss: 1.0201
- Baseline log loss: 1.0286
- Log-loss lift: 0.0086
- Coverage: 100.00%
- Sparse rate: 0.00%
- Mean top similarity: 90.60%
- Mean independent matches: 40.00

### H+16
- Retrieval accuracy: 46.45%
- Baseline accuracy: 48.80%
- Retrieval Brier: 0.2019
- Baseline Brier: 0.2031
- Brier lift: 0.0012
- Retrieval log loss: 0.9958
- Baseline log loss: 1.0327
- Log-loss lift: 0.0369
- Coverage: 100.00%
- Sparse rate: 0.00%
- Mean top similarity: 90.59%
- Mean independent matches: 40.00

## Similarity bucket diagnostics

### MODERATE_STRONG
- Samples: 30
- Accuracy: 40.00%
- Retrieval Brier: 0.2204
- Baseline Brier: 0.2363
- Brier lift: 0.0159

### STRONG
- Samples: 1157
- Accuracy: 46.07%
- Retrieval Brier: 0.2037
- Baseline Brier: 0.2022
- Brier lift: -0.0015

## Null retrieval sanity test

- Queries: 1187
- Mean real maximum share: 52.45%
- Mean null maximum share: 51.13%
- Mean null 95th percentile: 58.48%
- Mean real-minus-null: 1.32%

## Interpretation

v4.1.5 tests retrieval quality, not trading performance. Historical outcome shares are evidence distributions and are not presented as calibrated probabilities.

Promotion to v4.1.6 should require retrieval to demonstrate stable out-of-sample usefulness against appropriate baselines and sensible behaviour across similarity buckets.

## Protection

- market_data.bin unchanged: PASS
- Production MLAI modified: NO
- Learning memory modified: NO
- Trading enabled: NO

MLAI v4.1.5 COMPLETE