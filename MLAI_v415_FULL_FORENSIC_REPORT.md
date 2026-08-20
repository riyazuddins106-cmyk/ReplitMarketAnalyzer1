# MLAI v4.1.5 — FULL FORENSIC PREDICTIVE AUDIT

Source SHA256: `95a733a639e432863b5ae8583fa263e6a80dbf757cf1274aaaf70afadb41d242`
Data SHA256: `dd57bccc3526ebaeb900181096adcbf48a84b5a3a334da1f1990a443cde091b5`

## Executive Summary

This report is an evidence-based forensic assessment. It does not automatically modify MLAI or create v4.1.6.


## H4

Samples: **880**

### Actual class distribution

{'UP': 0.43863636363636366, 'DOWN': 0.41704545454545455, 'NEUTRAL': 0.14431818181818182}

### Fixed decision rules

| Rule | Accuracy | Balanced Accuracy | Macro F1 | Prediction Entropy |
|---|---:|---:|---:|---:|
| power_1 | 0.4386 | 0.3333 | 0.2033 | -0.0000 |
| power_2 | 0.4273 | 0.3263 | 0.2442 | 0.4617 |
| power_4 | 0.4091 | 0.3144 | 0.2688 | 0.8040 |
| top_5 | 0.3693 | 0.3028 | 0.2941 | 1.2320 |
| top_10 | 0.4011 | 0.3188 | 0.3021 | 1.0537 |
| top_20 | 0.4000 | 0.3116 | 0.2876 | 0.9884 |
| vote_5 | 0.3693 | 0.3028 | 0.2941 | 1.2320 |
| vote_10 | 0.4011 | 0.3188 | 0.3021 | 1.0537 |
| vote_20 | 0.4000 | 0.3116 | 0.2876 | 0.9884 |

Majority baseline: **UP** accuracy=0.4386, balanced=0.3333, macro-F1=0.2033.

### Confusion matrix

| Actual \ Predicted | UP | DOWN | NEUTRAL |
|---|---:|---:|---:|
| UP | 386 | 0 | 0 |
| DOWN | 367 | 0 | 0 |
| NEUTRAL | 127 | 0 | 0 |

Prediction distribution: `{'UP': 1.0, 'DOWN': 0.0, 'NEUTRAL': 0.0}`

Actual/prediction Jensen-Shannon divergence: **0.361824**.

### Similarity

Mean top similarity: **0.874462**
Median: **0.885908**
P10: **0.789411**
P90: **0.937189**

### Top-K historical outcome agreement

| K | Mean agreement with actual outcome |
|---:|---:|
| 1 | 0.3693 |
| 3 | 0.3871 |
| 5 | 0.3730 |
| 10 | 0.3806 |
| 20 | 0.3799 |
| 50 | 0.3824 |

### Similarity deciles

| Decile | Mean similarity | Accuracy | Balanced accuracy | Macro F1 |
|---:|---:|---:|---:|---:|
| 1 | 0.7563 | 0.3977 | 0.3333 | 0.1897 |
| 2 | 0.8100 | 0.3636 | 0.3333 | 0.1778 |
| 3 | 0.8376 | 0.4205 | 0.3333 | 0.1973 |
| 4 | 0.8575 | 0.4773 | 0.3333 | 0.2154 |
| 5 | 0.8780 | 0.4886 | 0.3333 | 0.2188 |
| 6 | 0.8931 | 0.4432 | 0.3333 | 0.2047 |
| 7 | 0.9096 | 0.4773 | 0.3333 | 0.2154 |
| 8 | 0.9235 | 0.4773 | 0.3333 | 0.2154 |
| 9 | 0.9327 | 0.5227 | 0.3333 | 0.2289 |
| 10 | 0.9464 | 0.3182 | 0.3333 | 0.1609 |

### Similarity component statistics

| Component | Mean | Median | Min | Max |
|---|---:|---:|---:|---:|
| candle | 0.680251 | 0.717726 | 0.009541 | 0.999982 |
| location | 0.366200 | 0.000000 | 0.000000 | 1.000000 |
| momentum | 0.206794 | 0.000000 | 0.000000 | 1.000000 |
| path | 0.604334 | 0.606868 | 0.196558 | 0.884602 |
| regime | 0.201451 | 0.000000 | 0.000000 | 1.000000 |
| sequence | 0.187835 | 0.000000 | 0.000000 | 1.000000 |
| structure | 0.599988 | 0.500000 | 0.000000 | 1.000000 |
| total | 0.412304 | 0.390616 | 0.054550 | 0.960172 |
| volatility | 0.519513 | 0.521682 | 0.000033 | 0.999995 |

### Label permutation test

Observed accuracy: **0.438636**
Permutation null mean: **0.438636**
Permutation p-value: **1.000000**

### Fold stability

Mean=0.438636, median=0.412500, stdev=0.101158, min=0.312500, max=0.625000.


## H8

Samples: **880**

### Actual class distribution

{'UP': 0.4625, 'DOWN': 0.43863636363636366, 'NEUTRAL': 0.09886363636363636}

### Fixed decision rules

| Rule | Accuracy | Balanced Accuracy | Macro F1 | Prediction Entropy |
|---|---:|---:|---:|---:|
| power_1 | 0.4625 | 0.3333 | 0.2108 | -0.0000 |
| power_2 | 0.4330 | 0.3134 | 0.2389 | 0.5006 |
| power_4 | 0.4250 | 0.3110 | 0.2830 | 0.8841 |
| top_5 | 0.4216 | 0.3283 | 0.3252 | 1.2396 |
| top_10 | 0.4534 | 0.3367 | 0.3216 | 1.0234 |
| top_20 | 0.4352 | 0.3203 | 0.3013 | 0.9696 |
| vote_5 | 0.4216 | 0.3283 | 0.3252 | 1.2396 |
| vote_10 | 0.4534 | 0.3367 | 0.3216 | 1.0234 |
| vote_20 | 0.4352 | 0.3203 | 0.3013 | 0.9696 |

Majority baseline: **UP** accuracy=0.4625, balanced=0.3333, macro-F1=0.2108.

### Confusion matrix

| Actual \ Predicted | UP | DOWN | NEUTRAL |
|---|---:|---:|---:|
| UP | 242 | 165 | 0 |
| DOWN | 226 | 156 | 4 |
| NEUTRAL | 45 | 41 | 1 |

Prediction distribution: `{'UP': 0.5829545454545455, 'DOWN': 0.4113636363636364, 'NEUTRAL': 0.005681818181818182}`

Actual/prediction Jensen-Shannon divergence: **0.041684**.

### Similarity

Mean top similarity: **0.874350**
Median: **0.885719**
P10: **0.789411**
P90: **0.937189**

### Top-K historical outcome agreement

| K | Mean agreement with actual outcome |
|---:|---:|
| 1 | 0.4080 |
| 3 | 0.4133 |
| 5 | 0.4098 |
| 10 | 0.4119 |
| 20 | 0.4085 |
| 50 | 0.4060 |

### Similarity deciles

| Decile | Mean similarity | Accuracy | Balanced accuracy | Macro F1 |
|---:|---:|---:|---:|---:|
| 1 | 0.7560 | 0.4205 | 0.3305 | 0.2715 |
| 2 | 0.8097 | 0.4773 | 0.3596 | 0.3377 |
| 3 | 0.8375 | 0.4091 | 0.3039 | 0.2876 |
| 4 | 0.8573 | 0.4205 | 0.2901 | 0.2752 |
| 5 | 0.8778 | 0.5114 | 0.3659 | 0.3519 |
| 6 | 0.8930 | 0.5000 | 0.4045 | 0.4030 |
| 7 | 0.9096 | 0.5227 | 0.3920 | 0.3702 |
| 8 | 0.9235 | 0.4886 | 0.3591 | 0.3378 |
| 9 | 0.9327 | 0.4091 | 0.2750 | 0.2543 |
| 10 | 0.9464 | 0.3750 | 0.2874 | 0.2532 |

### Similarity component statistics

| Component | Mean | Median | Min | Max |
|---|---:|---:|---:|---:|
| candle | 0.680808 | 0.718279 | 0.009541 | 0.999982 |
| location | 0.367654 | 0.000000 | 0.000000 | 1.000000 |
| momentum | 0.207226 | 0.000000 | 0.000000 | 1.000000 |
| path | 0.604687 | 0.607272 | 0.196558 | 0.884602 |
| regime | 0.201922 | 0.000000 | 0.000000 | 1.000000 |
| sequence | 0.188091 | 0.000000 | 0.000000 | 1.000000 |
| structure | 0.600246 | 0.500000 | 0.000000 | 1.000000 |
| total | 0.412921 | 0.391284 | 0.054550 | 0.960172 |
| volatility | 0.521384 | 0.524774 | 0.000033 | 0.999995 |

### Label permutation test

Observed accuracy: **0.453409**
Permutation null mean: **0.450574**
Permutation p-value: **0.454545**

### Fold stability

Mean=0.453409, median=0.425000, stdev=0.132416, min=0.287500, max=0.712500.


## H16

Samples: **880**

### Actual class distribution

{'UP': 0.44772727272727275, 'DOWN': 0.47613636363636364, 'NEUTRAL': 0.07613636363636364}

### Fixed decision rules

| Rule | Accuracy | Balanced Accuracy | Macro F1 | Prediction Entropy |
|---|---:|---:|---:|---:|
| power_1 | 0.4477 | 0.3333 | 0.2062 | -0.0000 |
| power_2 | 0.4284 | 0.3169 | 0.2442 | 0.5499 |
| power_4 | 0.4500 | 0.3293 | 0.2972 | 0.8625 |
| top_5 | 0.4545 | 0.3295 | 0.3153 | 1.0428 |
| top_10 | 0.4386 | 0.3193 | 0.2990 | 0.9501 |
| top_20 | 0.4568 | 0.3327 | 0.3108 | 0.9381 |
| vote_5 | 0.4545 | 0.3295 | 0.3153 | 1.0428 |
| vote_10 | 0.4386 | 0.3193 | 0.2990 | 0.9501 |
| vote_20 | 0.4568 | 0.3327 | 0.3108 | 0.9381 |

Majority baseline: **DOWN** accuracy=0.4761, balanced=0.3333, macro-F1=0.2150.

### Confusion matrix

| Actual \ Predicted | UP | DOWN | NEUTRAL |
|---|---:|---:|---:|
| UP | 394 | 0 | 0 |
| DOWN | 419 | 0 | 0 |
| NEUTRAL | 67 | 0 | 0 |

Prediction distribution: `{'UP': 1.0, 'DOWN': 0.0, 'NEUTRAL': 0.0}`

Actual/prediction Jensen-Shannon divergence: **0.354082**.

### Similarity

Mean top similarity: **0.874121**
Median: **0.885719**
P10: **0.789411**
P90: **0.936913**

### Top-K historical outcome agreement

| K | Mean agreement with actual outcome |
|---:|---:|
| 1 | 0.4068 |
| 3 | 0.4352 |
| 5 | 0.4405 |
| 10 | 0.4407 |
| 20 | 0.4385 |
| 50 | 0.4377 |

### Similarity deciles

| Decile | Mean similarity | Accuracy | Balanced accuracy | Macro F1 |
|---:|---:|---:|---:|---:|
| 1 | 0.7560 | 0.4091 | 0.3333 | 0.1935 |
| 2 | 0.8092 | 0.4659 | 0.3333 | 0.2119 |
| 3 | 0.8371 | 0.5114 | 0.3333 | 0.2256 |
| 4 | 0.8570 | 0.4318 | 0.3333 | 0.2011 |
| 5 | 0.8778 | 0.3977 | 0.3333 | 0.1897 |
| 6 | 0.8930 | 0.4205 | 0.3333 | 0.1973 |
| 7 | 0.9092 | 0.3864 | 0.3333 | 0.1858 |
| 8 | 0.9229 | 0.4318 | 0.3333 | 0.2011 |
| 9 | 0.9326 | 0.5000 | 0.3333 | 0.2222 |
| 10 | 0.9464 | 0.5227 | 0.3333 | 0.2289 |

### Similarity component statistics

| Component | Mean | Median | Min | Max |
|---|---:|---:|---:|---:|
| candle | 0.681508 | 0.719431 | 0.009541 | 0.999982 |
| location | 0.370608 | 0.000000 | 0.000000 | 1.000000 |
| momentum | 0.207238 | 0.000000 | 0.000000 | 1.000000 |
| path | 0.604868 | 0.607473 | 0.196558 | 0.884602 |
| regime | 0.202254 | 0.000000 | 0.000000 | 1.000000 |
| sequence | 0.187540 | 0.000000 | 0.000000 | 1.000000 |
| structure | 0.599645 | 0.500000 | 0.000000 | 1.000000 |
| total | 0.413178 | 0.391787 | 0.054550 | 0.960172 |
| volatility | 0.521899 | 0.526569 | 0.000033 | 0.999995 |

### Label permutation test

Observed accuracy: **0.447727**
Permutation null mean: **0.447727**
Permutation p-value: **1.000000**

### Fold stability

Mean=0.447727, median=0.412500, stdev=0.157502, min=0.200000, max=0.812500.


## Cross-horizon fixed-rule summary

| Horizon | Samples | Accuracy | Balanced Accuracy | Macro F1 | Entropy |
|---:|---:|---:|---:|---:|---:|
| H4 | 880 | 0.4273 | 0.3263 | 0.2442 | 0.4617 |
| H8 | 880 | 0.4330 | 0.3134 | 0.2389 | 0.5006 |
| H16 | 880 | 0.4284 | 0.3169 | 0.2442 | 0.5499 |

## Automatic forensic diagnosis

**Final classification: NO ROBUST THREE-CLASS PREDICTIVE SIGNAL ESTABLISHED**

### Pros

- Baseline source remained byte-for-byte unchanged.
- Market data remained byte-for-byte unchanged.
- Historical retrieval records obey strict chronological isolation.
- Causal prefix stability passed all tested checkpoints.
- H16: high-similarity queries outperform low-similarity queries by 0.0682.

### Cons / warnings

- H4: balanced accuracy is near random-class performance.
- H4: macro-F1 is weak, indicating poor three-class behavior.
- H4: prediction distribution is materially different from actual distribution.
- H4: prediction concentration exceeds 70%, indicating possible class bias.
- H8: balanced accuracy is near random-class performance.
- H8: macro-F1 is weak, indicating poor three-class behavior.
- H8: prediction concentration exceeds 70%, indicating possible class bias.
- H16: balanced accuracy is near random-class performance.
- H16: macro-F1 is weak, indicating poor three-class behavior.
- H16: prediction concentration exceeds 70%, indicating possible class bias.
- H4: higher similarity does not correspond to better predictive performance.
- H8: similarity-strength gradient is weak.

### Recommended investigation/fixes

- H16: investigate class decision calibration and neutral handling.
- H4: investigate class decision calibration and neutral handling.
- H4: investigate whether similarity features encode the correct future behavior.
- H8: investigate class decision calibration and neutral handling.

## Interpretation

This report deliberately distinguishes statistical performance from evidence of predictive intelligence. A result above 50% accuracy is not automatically considered predictive, and a result below 50% is not automatically considered useless. Class balance, balanced accuracy, macro-F1, prediction distribution, temporal isolation, causal-prefix stability, similarity behavior, fold stability, and null testing must be considered together.

## Baseline integrity

- Source unchanged: `True`
- Data unchanged: `True`
- Prefix causal stability: `1.000000`
- Temporal violations: `{4: 0, 8: 0, 16: 0}`