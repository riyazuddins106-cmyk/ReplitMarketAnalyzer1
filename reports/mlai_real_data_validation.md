# MLAI Real-Data Validation

Date: 2026-08-20
Engine: mlai_unified.py
Dataset: market_data.bin (GC=F, Yahoo Finance, 5-minute candles)

## Dataset audit

- Candle count: 1,309
- Invalid OHLC candles: 0
- Duplicate candles: 0
- Chronological ordering: PASS
- Expected interval: 300 seconds
- Timestamp gaps: 4
- Gap length: 3,900 seconds each
- Overall market audit: REVIEW because of gaps

## Causal walk-forward results

| Horizon | MLAI accuracy | Majority baseline | Incremental value | Predictions |
|---|---:|---:|---:|---:|
| H4 | 56.55% | 58.88% | -2.33 pp | 1,245 |
| H8 | 40.61% | 41.98% | -1.37 pp | 1,241 |
| H16 | 42.90% | 39.17% | +3.73 pp | 1,233 |

## Calibration metrics

| Horizon | Brier score | Log loss |
|---|---:|---:|
| H4 | 0.6127 | 1.0216 |
| H8 | 0.6586 | 1.0865 |
| H16 | 0.6544 | 1.0799 |

## Retrieval wiring check

After fixing the 12-field state-key mismatch, historical retrieval returned nonzero matches for 99.92% of predictions. Mean retrieved matches were approximately 24.5, with a maximum of 25.

This confirms that retrieval is mechanically connected. It does not yet prove path-aware historical intelligence: the current retrieval still needs to incorporate state returns and normalized path vectors.

## Interpretation

H16 is above the majority baseline in this sample, while H4 and H8 are below it. This is a preliminary result from one short dataset with four timestamp gaps and must not be treated as proof of generalization. The next scientific step is causal return/path similarity followed by repeated chronological and unseen-period validation.
