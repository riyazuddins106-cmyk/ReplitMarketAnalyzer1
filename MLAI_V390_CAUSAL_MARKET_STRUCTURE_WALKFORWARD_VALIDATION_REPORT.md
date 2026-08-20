# MLAI v3.9.0 Hardened Causal Market Structure Intelligence

Research / validation experiment only.

## Protection

- market_data.bin: READ ONLY
- Production MLAI modified: NO
- Learning memory modified: NO
- Trading enabled: NO
- Internet required: NO

## Dataset

- Valid candles: 1309
- Walk-forward windows: 5
- Confirmed swings: 322

## Structural Events

- BOS_BULLISH: 29
- BOS_BEARISH: 24
- CHoCH_BULLISH: 26
- CHoCH_BEARISH: 26

## Combined OOS

- H+4: N=400, Accuracy=53.50%, Balanced=52.80%, Baseline=51.00%, Edge=2.50%
- H+8: N=395, Accuracy=50.13%, Balanced=50.22%, Baseline=50.13%, Edge=0.00%
- H+16: N=388, Accuracy=51.80%, Balanced=53.63%, Baseline=52.58%, Edge=-0.77%

## Walk-Forward Stability

- H+4: mean=53.38%, median=51.85%, std=10.29%, min=42.86%, max=70.37%
- H+8: mean=50.01%, median=45.21%, std=14.86%, min=37.50%, max=74.07%
- H+16: mean=51.31%, median=40.00%, std=17.55%, min=37.04%, max=76.54%

## Causality

- confirmed_swings: PASS
- future_structure_leakage: PASS
- future_event_leakage: PASS
- structural_level_consumption: PASS
- training_label_boundary: PASS
- training_only_encoders: PASS
- frozen_oos_models: PASS
- chronological_walk_forward: PASS
- duplicate_timestamp_check: PASS
- invalid_candle_validation: PASS

## Interpretation

The experiment tests whether future market direction is conditionally related to causal market-structure states.

Accuracy above baseline is necessary but not sufficient. Robustness requires chronological stability, sufficient sample size, and repeated out-of-sample evidence.

This validation engine does not establish profitability or trading viability.
