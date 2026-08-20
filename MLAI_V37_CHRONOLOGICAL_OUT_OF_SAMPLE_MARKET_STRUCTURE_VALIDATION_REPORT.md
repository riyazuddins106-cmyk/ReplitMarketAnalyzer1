# MLAI v3.7 Chronological Out-of-Sample Market Structure Validation

## Experiment Status

- market_data.bin: READ ONLY
- Production MLAI: NOT MODIFIED
- Learning memory: NOT MODIFIED
- Trading: DISABLED
- Production model training: DISABLED

## Dataset

- Raw candles: 1309
- Valid candles: 1309
- Invalid candles: 0
- Training candles: 916
- OOS candles: 393
- Training ratio: 70.00%
- OOS ratio: 30.00%

## Configuration

- Swing lookback: 3
- Minimum structure move: 0.0200%
- Outcome threshold: 0.0500%
- Horizons: [4, 8, 16]

## Look-Ahead-Bias Checks

- Structure confirmation timing: PASS
- Future outcome separation: PASS
- Chronological OOS signal order: PASS

## Structure Event Counts

- BOS_BULLISH: 17
- BOS_BEARISH: 17
- CHoCH_BULLISH: 15
- CHoCH_BEARISH: 15

## Grouped OOS Results

| Group | Horizon | Signals | Accuracy | Precision | Recall | Avg Return | Baseline | Edge |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| BULLISH_STRUCTURE | H+4 | 31 | 45.16% | 45.16% | 70.00% | +0.0321% | 45.16% | +0.00% |
| BULLISH_STRUCTURE | H+8 | 31 | 48.39% | 48.39% | 68.18% | +0.0259% | 48.39% | +0.00% |
| BULLISH_STRUCTURE | H+16 | 31 | 54.84% | 54.84% | 60.71% | +0.0129% | 54.84% | +0.00% |
| BEARISH_STRUCTURE | H+4 | 30 | 30.00% | 30.00% | 40.91% | -0.0072% | 30.00% | +0.00% |
| BEARISH_STRUCTURE | H+8 | 30 | 36.67% | 36.67% | 45.83% | -0.0053% | 36.67% | +0.00% |
| BEARISH_STRUCTURE | H+16 | 29 | 44.83% | 44.83% | 52.00% | -0.0289% | 44.83% | +0.00% |
| BOS | H+4 | 8 | 37.50% | 37.50% | 50.00% | +0.0410% | 50.00% | -12.50% |
| BOS | H+8 | 8 | 50.00% | 50.00% | 80.00% | +0.0958% | 50.00% | +0.00% |
| BOS | H+16 | 8 | 62.50% | 62.50% | 71.43% | +0.0532% | 37.50% | +25.00% |
| CHoCH | H+4 | 7 | 57.14% | 57.14% | 80.00% | -0.0108% | 42.86% | +14.29% |
| CHoCH | H+8 | 7 | 42.86% | 42.86% | 60.00% | -0.0064% | 42.86% | +0.00% |
| CHoCH | H+16 | 7 | 28.57% | 28.57% | 40.00% | +0.0177% | 14.29% | +14.29% |
| SWING_STRUCTURE | H+4 | 46 | 34.78% | 34.78% | 51.61% | +0.0115% | 23.91% | +10.87% |
| SWING_STRUCTURE | H+8 | 46 | 41.30% | 41.30% | 52.78% | -0.0017% | 45.65% | -4.35% |
| SWING_STRUCTURE | H+16 | 45 | 51.11% | 51.11% | 56.10% | -0.0219% | 48.89% | +2.22% |
| ALL_STRUCTURE_EVENTS | H+4 | 61 | 37.70% | 37.70% | 54.76% | +0.0128% | 44.26% | -6.56% |
| ALL_STRUCTURE_EVENTS | H+8 | 61 | 42.62% | 42.62% | 56.52% | +0.0106% | 45.90% | -3.28% |
| ALL_STRUCTURE_EVENTS | H+16 | 60 | 50.00% | 50.00% | 56.60% | -0.0073% | 48.33% | +1.67% |

## Interpretation

This experiment measures historical association between confirmed market structure and subsequent price outcomes.

A result above the baseline does NOT automatically mean the structure is profitable or suitable for live trading.

The experiment does not include transaction costs, spread, slippage, execution latency, position sizing, stop-loss logic, take-profit logic, or portfolio effects.

Swing candidates are retrospective. A swing becomes available only after SWING_LOOKBACK confirmation candles.

The final 30% of the chronological dataset is treated as out-of-sample validation data.

OOS results should be considered evidence for further research, not proof of predictive power.

## Required Next Validation Steps

- Repeat validation on multiple chronological windows.
- Perform walk-forward validation.
- Test different instruments and market regimes.
- Test different volatility environments.
- Compare against stronger baselines.
- Evaluate statistical significance.
- Test transaction costs and spread.
- Test signal clustering and dependency.
- Test whether apparent edge survives parameter changes.
- Perform strict live/paper forward testing before any production integration.

## Final Protection

- market_data.bin: READ ONLY
- Production MLAI: NOT MODIFIED
- Learning memory: NOT MODIFIED
- Trading: DISABLED