---
name: Market data import validation
description: A data-import mismatch can make the unified console fail before its causal logic is exercised.
---

The unified console expects the market corpus to be a pickle-compatible object containing a `candles` list. An imported `data/market_data.bin` may exist but still be a different raw binary representation, so presence and file size are not sufficient validation.

**Why:** Runtime checks failed before the MLAI pipeline ran because the tracked market binary did not satisfy the loader contract, while a separate project snapshot contained a valid 1,309-candle pickle.

**How to apply:** Before interpreting audit or walk-forward results, load the corpus with the actual console loader and confirm the candle count and payload shape. Do not silently overwrite the tracked market corpus to make a test pass.