# MLAI v3.8.4 Causal Market Structure Intelligence

Research / validation experiment only.

## Protection

- market_data.bin: READ ONLY
- Production MLAI modified: NO
- Learning memory modified: NO
- Trading enabled: NO

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

- H+4: N=400, Accuracy=52.00%, Baseline=51.00%, Edge=1.00%
- H+8: N=395, Accuracy=48.86%, Baseline=50.13%, Edge=-1.27%
- H+16: N=388, Accuracy=51.80%, Baseline=52.58%, Edge=-0.77%

## Walk-Forward Stability

- H+4: mean=51.90%, median=47.50%, std=10.98%, min=42.86%, max=70.37%
- H+8: mean=48.77%, median=45.21%, std=16.15%, min=33.33%, max=74.07%
- H+16: mean=51.31%, median=40.00%, std=17.55%, min=37.04%, max=76.54%

## Causality

- Confirmed swings are only usable after RIGHT_SWING candles.
- Structural levels are causal.
- Structural breaks are consumed after the first break.
- State buckets are learned from TRAIN only.
- Training labels must terminate inside TRAIN.
- OOS models are frozen before OOS evaluation.

## Interpretation

The experiment evaluates whether future direction is conditionally related to causal market-structure states.

Accuracy above baseline is required before considering structural information useful. A single strong window is not sufficient; stability across chronological windows is also required.
