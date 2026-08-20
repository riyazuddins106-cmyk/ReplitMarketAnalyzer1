# MLAI Causality and Visibility Contract

Status: First replay-safety slice implemented.

## Visibility boundary

`analyzeMarket` accepts an optional `visibleThrough` ISO timestamp. When it is
present:

1. Only completed candles at or before the boundary are eligible.
2. Later candles are excluded before trend, sequence, volatility, structure,
   evidence, scenario, or explanation calculations run.
3. The returned analysis reports the last visible completed candle, the visible
   candle count, and the number of excluded candles.
4. An invalid boundary fails explicitly.
5. A boundary with no completed candles fails explicitly.

The CLI exposes this as:

```text
--visible-through <ISO timestamp>
```

The boundary is an analysis input and must be included in future replay cache
keys and persisted analysis-session records.

## Causality records

Every current analysis returns a causality record for:

- Candle anatomy
- ATR
- Recent range and location
- Future outcomes

Each record includes:

- Feature name
- Causality classification
- First availability point
- Candle lookback used
- Effective visible-through timestamp
- Whether future values were used

Future outcomes are explicitly classified as `future_target` and report
`futureValuesUsed: false`. This means they remain available for a later
evaluation phase without entering current-state analysis.

## Current guarantees

- A bounded analysis cannot use a later candle to calculate the current state.
- Causal features use only the visible candle and prior visible candles.
- Evidence timestamps cannot exceed the effective visibility boundary.
- The explanation states when later candles were excluded.
- Invalid or empty boundaries do not silently fall back to full-history analysis.

## Remaining causality work

This contract still needs to be extended with:

- Stable candle IDs instead of timestamp-only boundaries
- Feature-level availability timestamps for every derived feature
- Confirmed-swing timing audits
- Label-boundary audits
- Multi-timeframe synchronization checks
- Replay cache-key enforcement
- Persisted replay sessions and leakage regression fixtures