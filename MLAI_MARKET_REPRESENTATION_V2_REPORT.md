# MLAI v3.4.1 Market Representation Research

Research-only chronological validation.

## Protection

- `market_data.bin`: READ ONLY
- `mlai_v31.py`: NOT MODIFIED
- Production files: NOT MODIFIED
- Learning memory: NOT MODIFIED

## Horizon Results

| Horizon | Records | Predictions | Baseline | Accuracy | Coverage | Null Mean | Null Max | Permutation p |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 4 | 1245 | 954 | 35.66% | 35.53% | 95.78% | 33.87% | 37.58% | 0.1980 |
| 8 | 1241 | 992 | 41.50% | 39.21% | 100.00% | 39.91% | 43.76% | 0.6634 |
| 16 | 1233 | 984 | 45.09% | 46.65% | 100.00% | 43.60% | 46.54% | 0.0099 |

## Permutation Method

Outcome labels were shuffled while market features remained unchanged.

The exact chronological walk-forward fold boundaries used by the observed locked out-of-sample result were reused for every permutation.

Null accuracy was aggregated across all validation folds rather than selecting the best individual fold.

Numeric feature quartile boundaries were calculated once per calibration fold and reused during discretization.

## Current Market

- Index: `1308`
- Close: `4437.2998046875`
- Directional regime: `bearish`
- Volatility regime: `contracting`
- Location: `upper_range`
- Structure: `mixed_structure`

## Validation Engine

The validation engine explicitly applies calibration rules to chronologically unseen validation states.

The permutation engine uses the same validation windows and aggregates predictions across all walk-forward folds.
