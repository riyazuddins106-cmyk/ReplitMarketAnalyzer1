# MLAI v4.1.5 Predictive Failure Forensic Audit v2

## Baseline Integrity

- Source SHA256: `e42eacc11885cd408f7301d6f35c3c047f8d8212d02469b60a6ba3e944ad7b89`
- Data SHA256: `dd57bccc3526ebaeb900181096adcbf48a84b5a3a334da1f1990a443cde091b5`
- v4.1.5 source modified: NO
- market_data.bin modified: NO

## Audit Method Correction

The previous audit incorrectly attempted to construct the query target through `build_experience_records()` with `train_end=query_index+1`. That function intentionally excludes future outcomes that do not complete before `train_end`, causing zero query samples.

The corrected audit obtains the query target directly from the actual v4.1.5 `make_outcome()` function while retaining strict historical isolation.

For query index `q` and horizon `h`, historical records must satisfy:

```text
record.index + horizon < query_index
```

The query outcome is never inserted into the historical retrieval set.

## Corrected Predictive Results

### H4

- Evaluation samples: 250
- Retrieval accuracy: 0.456000
- Majority baseline: 0.436000
- Improvement: 0.020000
- Temporal violations: 0
- Retrieval failures: 0
- Mean top similarity: 0.898077
- Best tested rule: `power_4`
- Best tested accuracy: 0.448000
- Best improvement: 0.012000

### H8

- Evaluation samples: 250
- Retrieval accuracy: 0.468000
- Majority baseline: 0.424000
- Improvement: 0.044000
- Temporal violations: 0
- Retrieval failures: 0
- Mean top similarity: 0.899860
- Best tested rule: `vote_10`
- Best tested accuracy: 0.468000
- Best improvement: 0.044000

### H16

- Evaluation samples: 250
- Retrieval accuracy: 0.472000
- Majority baseline: 0.360000
- Improvement: 0.112000
- Temporal violations: 0
- Retrieval failures: 0
- Mean top similarity: 0.897742
- Best tested rule: `vote_5`
- Best tested accuracy: 0.484000
- Best improvement: 0.124000

## Interpretation

This audit does not modify v4.1.5 and does not create v4.1.6.

The corrected results must be used to determine whether the predictive weakness originates from historical experience construction, similarity representation, retrieval selection, decision aggregation, outcome definition, or lack of predictive signal in the supplied data.

## Final Integrity

- Source unchanged: `True`
- Data unchanged: `True`