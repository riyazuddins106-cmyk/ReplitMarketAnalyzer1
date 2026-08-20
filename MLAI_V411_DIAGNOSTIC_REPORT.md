# MLAI v4.1.1 Diagnostic / State Generalization Audit

## Protection

- Market data SHA256 before: `dd57bccc3526ebaeb900181096adcbf48a84b5a3a334da1f1990a443cde091b5`
- Market data SHA256 after: `dd57bccc3526ebaeb900181096adcbf48a84b5a3a334da1f1990a443cde091b5`
- Market data unchanged: PASS
- Production MLAI modified: NO
- Learning memory modified: NO
- Trading: DISABLED

## Dataset

- Valid candles: 1309
- Invalid candles: 0
- Chronological order: True
- Duplicate timestamps: False

## Causal Structure

- Confirmed swings: 225
- Structure states: 1309
- Structural events: 1309
- Signals: 1309

## Structural Events

- BOS_BULLISH: 23
- BOS_BEARISH: 18
- CHoCH_BULLISH: 18
- CHoCH_BEARISH: 18

## State Fragmentation

- Observations: 1309
- Structural unique states: 1309
- Structural singleton states: 1309
- 2-occurrence states: 0
- 3-5 occurrence states: 0
- 6-10 occurrence states: 0
- >10 occurrence states: 0
- Maximum frequency: 1
- Median frequency: 1.00

### Raw vs Structural Identity

- Raw unique states: 1309
- Structural unique states: 1309
- Raw singleton ratio: 100.00%
- Structural singleton ratio: 100.00%
- Maximum structural frequency: 1
- Median structural frequency: 1.00

## Signal Distribution

- Total signals: 1309
- BOS_BEARISH: 18
- BOS_BULLISH: 23
- CHoCH_BEARISH: 18
- CHoCH_BULLISH: 18
- NONE: 1232

## OOS Coverage

### H+4
- OOS: 400
- Predictions: 0
- Abstentions: 400
- Coverage: 0.00%
- Abstention rate: 100.00%

### H+8
- OOS: 395
- Predictions: 0
- Abstentions: 395
- Coverage: 0.00%
- Abstention rate: 100.00%

### H+16
- OOS: 388
- Predictions: 6
- Abstentions: 382
- Coverage: 1.55%
- Abstention rate: 98.45%

## Independent Event Audit

### BOS_BULLISH
- Total unique events: 23
- Outside OOS: 17
- OOS: 6
- Window 1: 1
- Window 2: 1
- Window 4: 4

### BOS_BEARISH
- Total unique events: 18
- Outside OOS: 15
- OOS: 3
- Window 2: 1
- Window 3: 1
- Window 5: 1

### CHoCH_BULLISH
- Total unique events: 18
- Outside OOS: 12
- OOS: 6
- Window 1: 1
- Window 2: 1
- Window 3: 2
- Window 5: 2

### CHoCH_BEARISH
- Total unique events: 18
- Outside OOS: 12
- OOS: 6
- Window 1: 2
- Window 2: 1
- Window 3: 1
- Window 5: 2

## Model Result Structure

### Window 1
- Top-level keys: ['window', 'horizons']
- H+4: train=894 | oos=81 | states=164
  result keys: ['samples', 'used', 'abstained', 'accuracy', 'balanced_accuracy', 'baseline_accuracy', 'edge', 'coverage', 'brier_score', 'log_loss', 'calibration_error', 'probabilities', 'abstain_mask', 'actual']
- H+8: train=894 | oos=81 | states=163
  result keys: ['samples', 'used', 'abstained', 'accuracy', 'balanced_accuracy', 'baseline_accuracy', 'edge', 'coverage', 'brier_score', 'log_loss', 'calibration_error', 'probabilities', 'abstain_mask', 'actual']
- H+16: train=886 | oos=81 | states=164
  result keys: ['samples', 'used', 'abstained', 'accuracy', 'balanced_accuracy', 'baseline_accuracy', 'edge', 'coverage', 'brier_score', 'log_loss', 'calibration_error', 'probabilities', 'abstain_mask', 'actual']

### Window 2
- Top-level keys: ['window', 'horizons']
- H+4: train=975 | oos=80 | states=168
  result keys: ['samples', 'used', 'abstained', 'accuracy', 'balanced_accuracy', 'baseline_accuracy', 'edge', 'coverage', 'brier_score', 'log_loss', 'calibration_error', 'probabilities', 'abstain_mask', 'actual']
- H+8: train=975 | oos=80 | states=167
  result keys: ['samples', 'used', 'abstained', 'accuracy', 'balanced_accuracy', 'baseline_accuracy', 'edge', 'coverage', 'brier_score', 'log_loss', 'calibration_error', 'probabilities', 'abstain_mask', 'actual']
- H+16: train=967 | oos=80 | states=168
  result keys: ['samples', 'used', 'abstained', 'accuracy', 'balanced_accuracy', 'baseline_accuracy', 'edge', 'coverage', 'brier_score', 'log_loss', 'calibration_error', 'probabilities', 'abstain_mask', 'actual']

### Window 3
- Top-level keys: ['window', 'horizons']
- H+4: train=1055 | oos=81 | states=169
  result keys: ['samples', 'used', 'abstained', 'accuracy', 'balanced_accuracy', 'baseline_accuracy', 'edge', 'coverage', 'brier_score', 'log_loss', 'calibration_error', 'probabilities', 'abstain_mask', 'actual']
- H+8: train=1055 | oos=80 | states=168
  result keys: ['samples', 'used', 'abstained', 'accuracy', 'balanced_accuracy', 'baseline_accuracy', 'edge', 'coverage', 'brier_score', 'log_loss', 'calibration_error', 'probabilities', 'abstain_mask', 'actual']
- H+16: train=1047 | oos=81 | states=169
  result keys: ['samples', 'used', 'abstained', 'accuracy', 'balanced_accuracy', 'baseline_accuracy', 'edge', 'coverage', 'brier_score', 'log_loss', 'calibration_error', 'probabilities', 'abstain_mask', 'actual']

### Window 4
- Top-level keys: ['window', 'horizons']
- H+4: train=1136 | oos=81 | states=169
  result keys: ['samples', 'used', 'abstained', 'accuracy', 'balanced_accuracy', 'baseline_accuracy', 'edge', 'coverage', 'brier_score', 'log_loss', 'calibration_error', 'probabilities', 'abstain_mask', 'actual']
- H+8: train=1135 | oos=81 | states=168
  result keys: ['samples', 'used', 'abstained', 'accuracy', 'balanced_accuracy', 'baseline_accuracy', 'edge', 'coverage', 'brier_score', 'log_loss', 'calibration_error', 'probabilities', 'abstain_mask', 'actual']
- H+16: train=1128 | oos=81 | states=169
  result keys: ['samples', 'used', 'abstained', 'accuracy', 'balanced_accuracy', 'baseline_accuracy', 'edge', 'coverage', 'brier_score', 'log_loss', 'calibration_error', 'probabilities', 'abstain_mask', 'actual']

### Window 5
- Top-level keys: ['window', 'horizons']
- H+4: train=1217 | oos=77 | states=172
  result keys: ['samples', 'used', 'abstained', 'accuracy', 'balanced_accuracy', 'baseline_accuracy', 'edge', 'coverage', 'brier_score', 'log_loss', 'calibration_error', 'probabilities', 'abstain_mask', 'actual']
- H+8: train=1216 | oos=73 | states=171
  result keys: ['samples', 'used', 'abstained', 'accuracy', 'balanced_accuracy', 'baseline_accuracy', 'edge', 'coverage', 'brier_score', 'log_loss', 'calibration_error', 'probabilities', 'abstain_mask', 'actual']
- H+16: train=1209 | oos=65 | states=172
  result keys: ['samples', 'used', 'abstained', 'accuracy', 'balanced_accuracy', 'baseline_accuracy', 'edge', 'coverage', 'brier_score', 'log_loss', 'calibration_error', 'probabilities', 'abstain_mask', 'actual']

## Automatic Diagnosis

### HIGH PRIORITY DIAGNOSTIC ISSUE

- HIGH structural state fragmentation: 1309 structural states across 1309 observations.
- HIGH singleton concentration: 1309 of 1309 structural states occur only once (100.00%).
- H+4: ZERO prediction coverage.
- H+8: ZERO prediction coverage.
- H+16: extremely low coverage (1.55%).
- BOS_BULLISH: 23 total unique events, 17 outside OOS, 6 inside OOS.
- BOS_BEARISH: 18 total unique events, 15 outside OOS, 3 inside OOS.
- CHoCH_BULLISH: 18 total unique events, 12 outside OOS, 6 inside OOS.
- CHoCH_BEARISH: 18 total unique events, 12 outside OOS, 6 inside OOS.

## Scientific Interpretation

The v4.1.0 H+4/H+8 zero-accuracy result must not be interpreted as ordinary 0% predictive accuracy because the model abstained on all tested observations.

The first investigation is therefore prediction coverage and state support rather than threshold optimization.

Raw state identity and canonical structural state identity are reported separately so that observation-specific fields cannot automatically be mistaken for distinct market regimes.

Walk-forward training-event counts are treated as unique event observations rather than summed across overlapping training windows.

No predictive rule has been promoted from this audit.

MLAI v4.1.1 DIAGNOSTIC AUDIT COMPLETE