# MLAI v4.1.6 Robust Causal Historical Experience Retrieval

## V4.1.6 seven capability status

- Similarity representation: ENABLED
- Retrieval ranking/discrimination: ENABLED
- H4 discrimination: ENABLED
- H8 discrimination: ENABLED
- H16 discrimination: ENABLED
- Incremental predictive value: ENABLED
- Predictive decision integration: ENABLED

## Phase scope

- Historical retrieval: ENABLED
- Explicit similarity representation: ENABLED
- Retrieval discrimination: ENABLED
- Predictive decision integration: ENABLED
- Incremental predictive value: ENABLED
- Probability calibration: NOT CLAIMED
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
- Explicit similarity representation: ENABLED
- Causal path similarity: ENABLED
- Temporal episode de-duplication: ENABLED
- Retrieval ranking/discrimination: ENABLED
- Supporting/conflicting evidence: ENABLED
- Sparse-evidence warning: ENABLED
- Retrieval-vs-baseline diagnostics: ENABLED
- Incremental predictive value: ENABLED
- Predictive decision integration: ENABLED
- H4 discrimination: ENABLED
- H8 discrimination: ENABLED
- H16 discrimination: ENABLED
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

## H4 / H8 / H16 discrimination

### H+4
- OOS queries: 401
- Discriminative queries: 401
- Discrimination rate: 100.00%
- Mean similarity separation: 0.5875
- Mean ranking concentration: 0.6016
- Mean directional discrimination: 0.0353
- Mean class entropy: 0.8973
- Mean baseline entropy: 0.9212
- Predictive accuracy: 32.92%
- Retrieval accuracy: 43.89%
- Baseline accuracy: 44.64%
- Incremental Brier lift: -0.0159
- Incremental log-loss lift: -0.0787
- Incremental accuracy delta: -0.1172

### H+8
- OOS queries: 397
- Discriminative queries: 397
- Discrimination rate: 100.00%
- Mean similarity separation: 0.5863
- Mean ranking concentration: 0.6005
- Mean directional discrimination: 0.0404
- Mean class entropy: 0.8325
- Mean baseline entropy: 0.8552
- Predictive accuracy: 34.51%
- Retrieval accuracy: 47.61%
- Baseline accuracy: 50.13%
- Incremental Brier lift: -0.0220
- Incremental log-loss lift: -0.0667
- Incremental accuracy delta: -0.1562

### H+16
- OOS queries: 389
- Discriminative queries: 389
- Discrimination rate: 100.00%
- Mean similarity separation: 0.5852
- Mean ranking concentration: 0.5993
- Mean directional discrimination: 0.0507
- Mean class entropy: 0.7768
- Mean baseline entropy: 0.8077
- Predictive accuracy: 38.56%
- Retrieval accuracy: 46.27%
- Baseline accuracy: 49.10%
- Incremental Brier lift: -0.0195
- Incremental log-loss lift: -0.0631
- Incremental accuracy delta: -0.1054

## Walk-forward aggregate

### H+4
- Retrieval accuracy: 43.94%
- Baseline accuracy: 44.72%
- Predictive accuracy: 33.03%
- Retrieval Brier: 0.2091
- Baseline Brier: 0.2071
- Retrieval Brier lift: -0.0019
- Predictive Brier: 0.2231
- Predictive Brier lift: -0.0160
- Retrieval log loss: 1.0352
- Baseline log loss: 1.0231
- Retrieval log-loss lift: -0.0121
- Predictive log loss: 1.1023
- Predictive log-loss lift: -0.0792
- Coverage: 100.00%
- Sparse rate: 0.00%
- Mean top similarity: 90.63%
- Mean independent matches: 40.00

### H+8
- Retrieval accuracy: 47.64%
- Baseline accuracy: 50.27%
- Predictive accuracy: 34.58%
- Retrieval Brier: 0.2014
- Baseline Brier: 0.1991
- Retrieval Brier lift: -0.0023
- Predictive Brier: 0.2212
- Predictive Brier lift: -0.0221
- Retrieval log loss: 1.0201
- Baseline log loss: 1.0286
- Retrieval log-loss lift: 0.0086
- Predictive log loss: 1.0938
- Predictive log-loss lift: -0.0652
- Coverage: 100.00%
- Sparse rate: 0.00%
- Mean top similarity: 90.60%
- Mean independent matches: 40.00

### H+16
- Retrieval accuracy: 46.45%
- Baseline accuracy: 48.80%
- Predictive accuracy: 38.80%
- Retrieval Brier: 0.2019
- Baseline Brier: 0.2031
- Retrieval Brier lift: 0.0012
- Predictive Brier: 0.2220
- Predictive Brier lift: -0.0189
- Retrieval log loss: 0.9958
- Baseline log loss: 1.0327
- Retrieval log-loss lift: 0.0369
- Predictive log loss: 1.0960
- Predictive log-loss lift: -0.0633
- Coverage: 100.00%
- Sparse rate: 0.00%
- Mean top similarity: 90.59%
- Mean independent matches: 40.00

## Similarity bucket diagnostics

### MODERATE_STRONG
- Samples: 30
- Retrieval accuracy: 40.00%
- Predictive accuracy: 40.00%
- Retrieval Brier: 0.2204
- Predictive Brier: 0.2237
- Baseline Brier: 0.2363
- Retrieval Brier lift: 0.0159
- Predictive Brier lift: 0.0126
- Similarity separation: 0.4370
- Directional discrimination: 0.0620

### STRONG
- Samples: 1157
- Retrieval accuracy: 46.07%
- Predictive accuracy: 35.18%
- Retrieval Brier: 0.2037
- Predictive Brier: 0.2222
- Baseline Brier: 0.2022
- Retrieval Brier lift: -0.0015
- Predictive Brier lift: -0.0199
- Similarity separation: 0.5902
- Directional discrimination: 0.0416

## Null retrieval sanity test

- Queries: 1187
- Mean real maximum share: 52.45%
- Mean null maximum share: 51.13%
- Mean null 95th percentile: 58.48%
- Mean real-minus-null: 1.32%

## Interpretation

V4.1.6 explicitly tests whether historical experience retrieval produces a distinguishable neighbour set, whether that discrimination exists independently at H4, H8 and H16, and whether the integrated predictive decision provides incremental value over the conditional baseline.

Positive discrimination is not treated as proof of trading profitability. All results remain research / validation evidence.

## Protection

- market_data.bin unchanged: PASS
- Production MLAI modified: NO
- Learning memory modified: NO
- Trading enabled: NO

MLAI v4.1.6 COMPLETE