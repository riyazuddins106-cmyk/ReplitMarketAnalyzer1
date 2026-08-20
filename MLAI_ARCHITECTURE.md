# MLAI Unified Architecture

## Purpose

`mlai_unified.py` is the single console entry point for the imported MLAI
project. It connects the corrected candle-language knowledge book with the
historical market corpus and a chronological experience memory.

The older `mlai_market_structure_v*.py`, `MLAI_V418_*`, and `MLAI_V420_*` files
remain in the project as preserved audit/reference implementations. They are
not silently replaced by the new integration path.

## Data flow

```text
market_data.bin
    |
    v
validated Candle records
    |
    v
candle anatomy + candle language
    |
    v
market state (trend, volatility, location, sequence)
    |
    v
market_experience.bin (historical evidence only)
    |
    v
probabilistic forecast
    |
    v
future outcome reveal
    |
    v
experience update
```

The prediction function is called before the future outcome is read. The
outcome is then revealed and recorded, so the walk-forward loop cannot use a
future candle as an input feature.

## Binary contracts

- `data/candle_language_v2.bin` is foundational knowledge.
- `data/candle_language_v2.index.json` records its count, size, and SHA-256.
- `data/market_data.bin` is raw historical OHLCV data.
- `data/market_experience.bin` is generated historical experience and is
  separate from foundational knowledge.
- `data/market_experience.index.json` records the experience manifest.

The imported corrected knowledge book currently contains 179 records and its
verified SHA-256 is
`d76039b86cec6940a345bd5977d345c58ad6a377ab67d0147c6e71975d4105c6`.

## Console commands

```bash
python mlai_unified.py audit
python mlai_unified.py translate --index 1308
python mlai_unified.py walk-forward --horizon 4 --start 60 --limit 200
python mlai_unified.py walk-forward --horizon 4 --start 60 --limit 200 --persist
```

`audit` is the first gate. It checks the knowledge hash/index, vocabulary
coverage, candle chronology, duplicates, OHLC validity, and detected gaps.
The currently imported corpus is valid but reports four timestamp gaps for
review rather than hiding them.

## Integration boundary

The single-file engine is deliberately an independent validation path first.
Retrieval, kNN, logistic, ensemble, and causal components from the existing
v4.x system remain available for later comparison. They should only be wired
into the forecast stage after the representation, data, and leakage audits
show measurable evidence.