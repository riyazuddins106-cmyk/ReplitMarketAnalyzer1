# MLAI v4.1.5 Robust Retrieval Scientific Gate

Version: `V415_ROBUST_RETRIEVAL_GATE_2.0`

## Protection

- Source modified: NO
- Market data modified: NO
- Retrieval memory modified: NO
- Retrieval parameters modified: NO
- Model retrained: NO

## 1. Self / Future Leakage

- Total OOS queries inspected: 1215
- Historical candidates inspected: 1159069
- Self matches: `0`
- Future candidates: `0`
- Boundary violations: `0`
- Outcome boundary violations: `0`
- Horizon violations: `0`

**RESULT: PASS — temporal separation is proven by the gate.**

## 2. Similarity Discrimination

### H+4
- Evaluation rows: `401`
- Top-group similarity: 59.19%
- Random-group similarity: 43.26%
- Top-group outcome agreement: 42.30%
- Middle-group outcome agreement: 42.26%
- Bottom-group outcome agreement: 42.17%
- Random-group outcome agreement: 42.36%
- Top vs random discrimination lift: -0.06%
- Monotonic similarity/outcome relationship: YES
- RESULT: FAIL

### H+8
- Evaluation rows: `397`
- Top-group similarity: 59.17%
- Random-group similarity: 43.20%
- Top-group outcome agreement: 44.89%
- Middle-group outcome agreement: 44.61%
- Bottom-group outcome agreement: 44.91%
- Random-group outcome agreement: 44.49%
- Top vs random discrimination lift: 0.41%
- Monotonic similarity/outcome relationship: NO
- RESULT: FAIL

### H+16
- Evaluation rows: `389`
- Top-group similarity: 59.14%
- Random-group similarity: 43.22%
- Top-group outcome agreement: 46.37%
- Middle-group outcome agreement: 46.27%
- Bottom-group outcome agreement: 45.54%
- Random-group outcome agreement: 46.00%
- Top vs random discrimination lift: 0.37%
- Monotonic similarity/outcome relationship: YES
- RESULT: FAIL

## 3. Retrieval Predictive Value

### H+4
- Walk-forward windows: 5
- Mean accuracy lift: 0.46%
- Mean Brier lift: -0.000412
- Mean LogLoss lift: 0.001583
- Accuracy-positive windows: 3/5
- Brier-positive windows: 2/5
- LogLoss-positive windows: 2/5
- Probability value demonstrated: YES
- Probability consistency demonstrated: NO
- Accuracy not catastrophically worse: YES
- RESULT: FAIL

| Window | Queries | Accuracy Lift | Brier Lift | LogLoss Lift |
|---:|---:|---:|---:|---:|
| 1 | 81 | 6.17% | 0.003170 | 0.013452 |
| 2 | 81 | 6.17% | 0.005738 | 0.030505 |
| 3 | 81 | 3.70% | -0.001533 | -0.008724 |
| 4 | 81 | -9.88% | -0.003991 | -0.012454 |
| 5 | 77 | -3.90% | -0.005445 | -0.014864 |

### H+8
- Walk-forward windows: 5
- Mean accuracy lift: -2.38%
- Mean Brier lift: -0.001171
- Mean LogLoss lift: -0.003600
- Accuracy-positive windows: 2/5
- Brier-positive windows: 2/5
- LogLoss-positive windows: 2/5
- Probability value demonstrated: NO
- Probability consistency demonstrated: NO
- Accuracy not catastrophically worse: YES
- RESULT: FAIL

| Window | Queries | Accuracy Lift | Brier Lift | LogLoss Lift |
|---:|---:|---:|---:|---:|
| 1 | 81 | -3.70% | -0.003649 | -0.006331 |
| 2 | 81 | 7.41% | 0.003685 | 0.004903 |
| 3 | 81 | -8.64% | -0.004555 | -0.017843 |
| 4 | 81 | 1.23% | 0.002535 | 0.004867 |
| 5 | 73 | -8.22% | -0.003872 | -0.003594 |

### H+16
- Walk-forward windows: 5
- Mean accuracy lift: -2.85%
- Mean Brier lift: -0.001049
- Mean LogLoss lift: -0.002445
- Accuracy-positive windows: 1/5
- Brier-positive windows: 2/5
- LogLoss-positive windows: 2/5
- Probability value demonstrated: NO
- Probability consistency demonstrated: NO
- Accuracy not catastrophically worse: YES
- RESULT: FAIL

| Window | Queries | Accuracy Lift | Brier Lift | LogLoss Lift |
|---:|---:|---:|---:|---:|
| 1 | 81 | -3.70% | -0.004436 | -0.010389 |
| 2 | 81 | -8.64% | -0.008527 | -0.023713 |
| 3 | 81 | -9.88% | -0.001123 | -0.012368 |
| 4 | 81 | -1.23% | 0.004919 | 0.018275 |
| 5 | 65 | 9.23% | 0.003924 | 0.015969 |

## 4. Final Classification

- **temporal**: PASS — no self/future/boundary leakage detected
- **discrimination_h4**: FAIL — similarity ranking does not demonstrate sufficient outcome discrimination
- **discrimination_h8**: FAIL — similarity ranking does not demonstrate sufficient outcome discrimination
- **discrimination_h16**: FAIL — similarity ranking does not demonstrate sufficient outcome discrimination
- **predictive_h4**: FAIL — retrieval does not demonstrate sufficient incremental predictive value
- **predictive_h8**: FAIL — retrieval does not demonstrate sufficient incremental predictive value
- **predictive_h16**: FAIL — retrieval does not demonstrate sufficient incremental predictive value

## 5. Scientific Decision

**RETRIEVAL VALIDATION NOT PASSED. Similarity does not consistently identify outcome-similar historical states.**

## 6. Protection Hashes

- Source before: `2893feb4a33cc7fc642e40fe1af9497016eb4d2ad31cf4fd27432e20760c8870`
- Source after: `2893feb4a33cc7fc642e40fe1af9497016eb4d2ad31cf4fd27432e20760c8870`
- Source unchanged: `True`

- Memory before: `de03d3ed39f530d21910f27f26011c54c86c0e3cb0ca2a15845c3ae843b73b0f`
- Memory after: `de03d3ed39f530d21910f27f26011c54c86c0e3cb0ca2a15845c3ae843b73b0f`
- Memory unchanged: `True`

- Market data before: `dd57bccc3526ebaeb900181096adcbf48a84b5a3a334da1f1990a443cde091b5`
- Market data after: `dd57bccc3526ebaeb900181096adcbf48a84b5a3a334da1f1990a443cde091b5`
- Market data unchanged: `True`
