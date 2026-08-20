# MLAI v4.1.5 — Robust Walk-Forward Predictive Forensic Audit

## Baseline Integrity

- Source SHA256: `e42eacc11885cd408f7301d6f35c3c047f8d8212d02469b60a6ba3e944ad7b89`
- Data SHA256: `dd57bccc3526ebaeb900181096adcbf48a84b5a3a334da1f1990a443cde091b5`
- Source unchanged: `True`
- Data unchanged: `True`
- v4.1.5 modified: NO
- v4.1.6 created: NO

## Audit Design

- Minimum history: 400
- Calibration size: 120
- Test size: 80
- Walk-forward folds: 11
- Decision rule selected only from calibration data
- Final test data never used for rule selection
- Query targets obtained using make_outcome()
- Historical records obtained using build_experience_records()
- Temporal leakage explicitly checked

## Results

### H4

- Samples: 880
- Walk-forward selected accuracy: 0.419318
- Majority baseline: 0.438636
- Improvement over majority: -0.019318
- Selected balanced accuracy: 0.324142
- Majority balanced accuracy: 0.333333
- Paired mean improvement: -0.019318
- Bootstrap 95% CI: [-0.043182, +0.004545]
- Paired permutation p-value: 0.133573
- Mean top similarity: 0.894950
- Mean historical records: 822.50
- Temporal violations: 0
- Rule selections: `{'vote_20': 1, 'top_5': 1, 'power_2': 5, 'top_10': 1, 'power_1': 2, 'power_4': 1}`

### H8

- Samples: 880
- Walk-forward selected accuracy: 0.446591
- Majority baseline: 0.462500
- Improvement over majority: -0.015909
- Selected balanced accuracy: 0.325343
- Majority balanced accuracy: 0.333333
- Paired mean improvement: -0.015909
- Bootstrap 95% CI: [-0.045455, +0.012500]
- Paired permutation p-value: 0.319736
- Mean top similarity: 0.894563
- Mean historical records: 818.50
- Temporal violations: 0
- Rule selections: `{'top_5': 3, 'power_1': 1, 'power_2': 4, 'vote_10': 1, 'power_4': 1, 'top_10': 1}`

### H16

- Samples: 880
- Walk-forward selected accuracy: 0.464773
- Majority baseline: 0.405682
- Improvement over majority: +0.059091
- Selected balanced accuracy: 0.338805
- Majority balanced accuracy: 0.301475
- Paired mean improvement: +0.059091
- Bootstrap 95% CI: [+0.022727, +0.096591]
- Paired permutation p-value: 0.000800
- Mean top similarity: 0.894383
- Mean historical records: 810.50
- Temporal violations: 0
- Rule selections: `{'power_4': 2, 'top_5': 2, 'power_1': 3, 'vote_5': 1, 'vote_10': 2, 'top_10': 1}`

## Fold Details

### H4

- Fold 1: selected=`vote_20`, test_samples=80, selected_accuracy=0.337500, power_2=0.362500, majority=0.375000, violations=0
- Fold 2: selected=`top_5`, test_samples=80, selected_accuracy=0.450000, power_2=0.562500, majority=0.562500, violations=0
- Fold 3: selected=`power_2`, test_samples=80, selected_accuracy=0.425000, power_2=0.425000, majority=0.425000, violations=0
- Fold 4: selected=`power_2`, test_samples=80, selected_accuracy=0.412500, power_2=0.412500, majority=0.412500, violations=0
- Fold 5: selected=`power_2`, test_samples=80, selected_accuracy=0.500000, power_2=0.500000, majority=0.500000, violations=0
- Fold 6: selected=`power_2`, test_samples=80, selected_accuracy=0.325000, power_2=0.325000, majority=0.312500, violations=0
- Fold 7: selected=`power_2`, test_samples=80, selected_accuracy=0.512500, power_2=0.512500, majority=0.525000, violations=0
- Fold 8: selected=`top_10`, test_samples=80, selected_accuracy=0.287500, power_2=0.350000, majority=0.362500, violations=0
- Fold 9: selected=`power_1`, test_samples=80, selected_accuracy=0.325000, power_2=0.312500, majority=0.325000, violations=0
- Fold 10: selected=`power_4`, test_samples=80, selected_accuracy=0.637500, power_2=0.625000, majority=0.625000, violations=0
- Fold 11: selected=`power_1`, test_samples=80, selected_accuracy=0.400000, power_2=0.400000, majority=0.400000, violations=0

### H8

- Fold 1: selected=`top_5`, test_samples=80, selected_accuracy=0.412500, power_2=0.325000, majority=0.412500, violations=0
- Fold 2: selected=`top_5`, test_samples=80, selected_accuracy=0.500000, power_2=0.612500, majority=0.612500, violations=0
- Fold 3: selected=`power_1`, test_samples=80, selected_accuracy=0.537500, power_2=0.537500, majority=0.537500, violations=0
- Fold 4: selected=`power_2`, test_samples=80, selected_accuracy=0.387500, power_2=0.387500, majority=0.387500, violations=0
- Fold 5: selected=`power_2`, test_samples=80, selected_accuracy=0.412500, power_2=0.412500, majority=0.425000, violations=0
- Fold 6: selected=`vote_10`, test_samples=80, selected_accuracy=0.400000, power_2=0.325000, majority=0.312500, violations=0
- Fold 7: selected=`power_2`, test_samples=80, selected_accuracy=0.612500, power_2=0.612500, majority=0.612500, violations=0
- Fold 8: selected=`power_4`, test_samples=80, selected_accuracy=0.312500, power_2=0.337500, majority=0.362500, violations=0
- Fold 9: selected=`top_10`, test_samples=80, selected_accuracy=0.375000, power_2=0.300000, majority=0.300000, violations=0
- Fold 10: selected=`top_5`, test_samples=80, selected_accuracy=0.600000, power_2=0.775000, majority=0.762500, violations=0
- Fold 11: selected=`power_2`, test_samples=80, selected_accuracy=0.362500, power_2=0.362500, majority=0.362500, violations=0

### H16

- Fold 1: selected=`power_4`, test_samples=80, selected_accuracy=0.325000, power_2=0.300000, majority=0.337500, violations=0
- Fold 2: selected=`top_5`, test_samples=80, selected_accuracy=0.625000, power_2=0.575000, majority=0.562500, violations=0
- Fold 3: selected=`power_4`, test_samples=80, selected_accuracy=0.450000, power_2=0.537500, majority=0.562500, violations=0
- Fold 4: selected=`power_1`, test_samples=80, selected_accuracy=0.462500, power_2=0.300000, majority=0.462500, violations=0
- Fold 5: selected=`power_1`, test_samples=80, selected_accuracy=0.412500, power_2=0.375000, majority=0.412500, violations=0
- Fold 6: selected=`vote_5`, test_samples=80, selected_accuracy=0.437500, power_2=0.250000, majority=0.200000, violations=0
- Fold 7: selected=`top_5`, test_samples=80, selected_accuracy=0.475000, power_2=0.475000, majority=0.425000, violations=0
- Fold 8: selected=`vote_10`, test_samples=80, selected_accuracy=0.550000, power_2=0.537500, majority=0.200000, violations=0
- Fold 9: selected=`vote_10`, test_samples=80, selected_accuracy=0.400000, power_2=0.325000, majority=0.262500, violations=0
- Fold 10: selected=`top_10`, test_samples=80, selected_accuracy=0.612500, power_2=0.700000, majority=0.675000, violations=0
- Fold 11: selected=`power_1`, test_samples=80, selected_accuracy=0.362500, power_2=0.437500, majority=0.362500, violations=0

## Final Interpretation
- H4: **NO ROBUST OUT-OF-SAMPLE ADVANTAGE ESTABLISHED**
- H8: **NO ROBUST OUT-OF-SAMPLE ADVANTAGE ESTABLISHED**
- H16: **STRONGER EVIDENCE OF OUT-OF-SAMPLE ADVANTAGE**

## Safety

- Baseline v4.1.5 source was not modified.
- market_data.bin was not modified.
- No v4.1.6 source was generated.