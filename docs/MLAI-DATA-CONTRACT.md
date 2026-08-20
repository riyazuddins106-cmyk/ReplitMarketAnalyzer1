# MLAI Canonical Data Contract

Status: Implemented foundation for the first version of the data layer.

## Dataset metadata

Every normalization result carries explicit metadata:

| Field | Meaning |
|---|---|
| `datasetId` | Stable logical identity of the imported dataset |
| `datasetVersion` | Caller-defined immutable revision identifier |
| `instrument` | Instrument represented by the rows |
| `timeframe` | Candle interval, such as `5m`, `1h`, or `1d` |
| `source` | Provider, file, or caller source label |
| `sourceFormat` | `csv`, `json`, or in-memory `rows` |
| `normalizationVersion` | Version of the normalization rules |
| `rawRecordCount` | Number of input records before validation |

The CLI supports:

```text
--dataset-id <id>
--dataset-version <version>
```

If these are omitted, the output deliberately uses `adhoc-input` and
`unversioned` so that non-persisted exploratory runs are visible as such rather
than appearing to be validated dataset versions.

## Raw and normalized layers

The normalizer returns two separate representations:

1. `rawRecords` preserves the original row payload, source-row number,
   normalization status, and row-level issues.
2. `candles` contains only accepted, canonical `NormalizedCandle` records sorted
   by timestamp.

Each normalized candle retains `sourceRow`, allowing a canonical candle to be
traced back to its original input record.

The current implementation keeps both layers in memory. Persistent storage and
immutable dataset snapshots are a later step.

## Quality states

Quality results are separated into:

- `errors`: issues that reject a record.
- `warnings`: issues that preserve the record but reduce data quality or require
  interpretation.
- `issues`: a compatibility-ordered combined list.

Examples of errors:

- Missing required OHLC field
- Invalid number
- Invalid timestamp
- Invalid OHLC relationship
- Duplicate timestamp

Examples of warnings:

- Out-of-order source records, which are reported before chronological sorting
- Invalid optional volume, which becomes unavailable rather than zero
- Time gaps relative to the declared timeframe

The distinction is important: chronological sorting creates a stable analysis
view, but does not erase source-order problems.

## Invariants

- Raw payloads are never rewritten into normalized values.
- Future outcomes are not part of the normalization input.
- Invalid records cannot enter the normalized candle list.
- Duplicate timestamps cannot enter the normalized candle list.
- Accepted candles are chronologically ordered.
- Every accepted candle retains source-row provenance.
- Dataset metadata is carried into the structured market analysis.
- Missing or invalid volume is never silently converted to zero.

## Current boundary

This contract does not yet provide:

- Database persistence
- Content hashes for raw payloads
- Provider retrieval timestamps
- Timezone/source-calendar metadata
- Replay visibility boundaries
- Historical outcome labels
- Multi-timeframe synchronization

Those belong to later milestones and must extend this contract without merging
future targets into current-state inputs.