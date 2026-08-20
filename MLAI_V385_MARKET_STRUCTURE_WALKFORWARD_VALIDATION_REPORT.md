# MLAI v3.8.5 Causal Market Structure Intelligence

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
- Structural state records: 1298
- Structural event records: 105
- Confirmed swings: 322

## Structural Events

- BOS_BULLISH: 29
- BOS_BEARISH: 24
- CHoCH_BULLISH: 26
- CHoCH_BEARISH: 26

## Combined OOS Prediction

- H+4: N=400, Accuracy=49.50%, Baseline=51.00%, Edge=-1.50%
- H+8: N=395, Accuracy=48.86%, Baseline=50.13%, Edge=-1.27%
- H+16: N=388, Accuracy=49.48%, Baseline=52.58%, Edge=-3.09%

## Future Movement

- H+4: MFE=1.0802 ATR, MAE=1.0524 ATR, Time-to-MFE=2.5187, Time-to-MAE=2.4464
- H+8: MFE=1.5711 ATR, MAE=1.5289 ATR, Time-to-MFE=4.4635, Time-to-MAE=4.4030
- H+16: MFE=2.2999 ATR, MAE=2.2159 ATR, Time-to-MFE=8.2211, Time-to-MAE=8.3702

## Walk-Forward Stability

- H+4: mean=49.35%, median=49.38%, std=13.71%, min=36.36%, max=71.60%
- H+8: mean=48.48%, median=44.44%, std=16.92%, min=30.14%, max=74.07%
- H+16: mean=48.34%, median=35.00%, std=27.04%, min=21.54%, max=82.72%

## Causality

- Confirmed swings become usable only after RIGHT_SWING candles.
- Structural states use only confirmed information.
- Structural levels are consumed after breaks.
- State bucket thresholds are learned from TRAIN only.
- Training labels must terminate inside TRAIN.
- OOS models are frozen before OOS outcomes are evaluated.
- MFE/MAE are evaluation outcomes and are never model inputs.

## v3.8.5 Interpretation

The experiment evaluates whether causally observable market-structure states are conditionally related to future price direction and future price excursion.

Accuracy above baseline is required before considering the structural representation useful.

MFE and MAE provide additional information about the magnitude and path of future movement.

A single strong walk-forward window is not sufficient evidence. Chronological stability is required.
