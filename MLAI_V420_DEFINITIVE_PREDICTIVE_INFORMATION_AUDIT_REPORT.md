# MLAI V4.2.0 — Definitive Predictive Information Audit

Audit version: `V420-DEFINITIVE-PREDICTIVE-INFORMATION-AUDIT-2.0`

## Final verdict

**NO EVIDENCE**

The verdict is generated from predefined evidence rules. No OOS result is used to modify the production model.

## Predictive results

| Horizon | N | Baseline Acc | Predictive Acc | Δ Accuracy | Δ Brier | Δ LogLoss |
|---:|---:|---:|---:|---:|---:|---:|
| H+4 | 401 | 44.888% | 41.895% | -2.993% | -0.03142614 | -1.26312103 |
| H+8 | 397 | 50.126% | 49.370% | -0.756% | -0.02237110 | -1.31973679 |
| H+16 | 389 | 49.357% | 48.586% | -0.771% | -0.00257596 | -1.48881810 |

## Similarity discrimination

### H+4
- Spearman similarity vs predictive Brier lift: `0.02081922`
- D1: N=40, similarity=78.605%, predictive accuracy=32.500%, predictive Brier=0.63492399
- D2: N=40, similarity=83.126%, predictive accuracy=47.500%, predictive Brier=0.63875113
- D3: N=40, similarity=85.152%, predictive accuracy=40.000%, predictive Brier=0.65702987
- D4: N=40, similarity=86.838%, predictive accuracy=42.500%, predictive Brier=0.64109227
- D5: N=40, similarity=88.175%, predictive accuracy=30.000%, predictive Brier=0.69267640
- D6: N=40, similarity=89.217%, predictive accuracy=50.000%, predictive Brier=0.68035393
- D7: N=40, similarity=89.933%, predictive accuracy=35.000%, predictive Brier=0.68496668
- D8: N=40, similarity=90.595%, predictive accuracy=37.500%, predictive Brier=0.62909989
- D9: N=40, similarity=91.250%, predictive accuracy=55.000%, predictive Brier=0.65284568
- D10: N=41, similarity=92.209%, predictive accuracy=48.780%, predictive Brier=0.61178760

### H+8
- Spearman similarity vs predictive Brier lift: `-0.09164171`
- D1: N=39, similarity=78.754%, predictive accuracy=43.590%, predictive Brier=0.65572384
- D2: N=40, similarity=83.109%, predictive accuracy=45.000%, predictive Brier=0.64679359
- D3: N=40, similarity=85.189%, predictive accuracy=60.000%, predictive Brier=0.50811429
- D4: N=39, similarity=86.953%, predictive accuracy=58.974%, predictive Brier=0.51498013
- D5: N=40, similarity=88.423%, predictive accuracy=40.000%, predictive Brier=0.68294359
- D6: N=40, similarity=89.532%, predictive accuracy=57.500%, predictive Brier=0.63273560
- D7: N=39, similarity=90.242%, predictive accuracy=41.026%, predictive Brier=0.63307833
- D8: N=40, similarity=90.910%, predictive accuracy=45.000%, predictive Brier=0.63047358
- D9: N=40, similarity=91.524%, predictive accuracy=60.000%, predictive Brier=0.64458406
- D10: N=40, similarity=92.496%, predictive accuracy=42.500%, predictive Brier=0.64371756

### H+16
- Spearman similarity vs predictive Brier lift: `-0.08621060`
- D1: N=38, similarity=77.611%, predictive accuracy=34.211%, predictive Brier=0.69285629
- D2: N=39, similarity=81.953%, predictive accuracy=61.538%, predictive Brier=0.55353913
- D3: N=39, similarity=84.008%, predictive accuracy=43.590%, predictive Brier=0.56699772
- D4: N=39, similarity=85.969%, predictive accuracy=46.154%, predictive Brier=0.62496368
- D5: N=39, similarity=87.647%, predictive accuracy=53.846%, predictive Brier=0.58725562
- D6: N=39, similarity=88.835%, predictive accuracy=51.282%, predictive Brier=0.61178223
- D7: N=39, similarity=89.595%, predictive accuracy=41.026%, predictive Brier=0.61998457
- D8: N=39, similarity=90.343%, predictive accuracy=61.538%, predictive Brier=0.59878808
- D9: N=39, similarity=91.001%, predictive accuracy=48.718%, predictive Brier=0.61288540
- D10: N=39, similarity=92.031%, predictive accuracy=43.590%, predictive Brier=0.61372830

## Calibration

### H+4
- baseline: ECE=0.07945614
- retrieval: ECE=0.12406891
- predictive: ECE=0.09720483

### H+8
- baseline: ECE=0.11827193
- retrieval: ECE=0.09180347
- predictive: ECE=0.08729960

### H+16
- baseline: ECE=0.13008942
- retrieval: ECE=0.13200934
- predictive: ECE=0.09645669

## Cross-window robustness

- H+4: 0/5 windows positive on Brier; 0/5 positive on LogLoss; mean Brier lift=-0.03126360; 95% CI=[-0.04940946, -0.01616054]
- H+8: 1/5 windows positive on Brier; 0/5 positive on LogLoss; mean Brier lift=-0.02273754; 95% CI=[-0.03599271, -0.00660797]
- H+16: 2/5 windows positive on Brier; 1/5 positive on LogLoss; mean Brier lift=-0.00157989; 95% CI=[-0.01796596, 0.01272497]

## Regime robustness

### H+4
- `TRANSITION`: N=78, ΔAccuracy=2.564%, ΔBrier=-0.04994378, ΔLogLoss=-2.60692861
- `TRENDING_DOWN`: N=78, ΔAccuracy=-7.692%, ΔBrier=0.00060602, ΔLogLoss=-0.58113537
- `TRENDING_UP`: N=96, ΔAccuracy=-5.208%, ΔBrier=-0.03772664, ΔLogLoss=-0.56835262
- `VOL_CONTRACTION`: N=84, ΔAccuracy=1.190%, ΔBrier=-0.03266000, ΔLogLoss=-0.89854688
- `VOL_EXPANSION`: N=65, ΔAccuracy=-6.154%, ΔBrier=-0.03674368, ΔLogLoss=-1.96619620

### H+8
- `TRANSITION`: N=78, ΔAccuracy=11.538%, ΔBrier=-0.01387928, ΔLogLoss=-1.60961119
- `TRENDING_DOWN`: N=76, ΔAccuracy=3.947%, ΔBrier=-0.01949482, ΔLogLoss=-1.99954423
- `TRENDING_UP`: N=96, ΔAccuracy=-7.292%, ΔBrier=-0.01840377, ΔLogLoss=-0.76042314
- `VOL_CONTRACTION`: N=82, ΔAccuracy=-13.415%, ΔBrier=-0.04843191, ΔLogLoss=-1.21863486
- `VOL_EXPANSION`: N=65, ΔAccuracy=4.615%, ΔBrier=-0.00890704, ΔLogLoss=-1.13064295

### H+16
- `TRANSITION`: N=77, ΔAccuracy=3.896%, ΔBrier=0.03212147, ΔLogLoss=-1.82219435
- `TRENDING_DOWN`: N=72, ΔAccuracy=6.944%, ΔBrier=-0.00413873, ΔLogLoss=-0.70677717
- `TRENDING_UP`: N=96, ΔAccuracy=-5.208%, ΔBrier=0.01540371, ΔLogLoss=-2.24235340
- `VOL_CONTRACTION`: N=79, ΔAccuracy=-6.329%, ΔBrier=-0.08135771, ΔLogLoss=-1.62909730
- `VOL_EXPANSION`: N=65, ΔAccuracy=-1.538%, ΔBrier=0.02724753, ΔLogLoss=-0.67674932

## Null investigation

- H+4: observed ΔAccuracy=-2.993%; null P95=2.743%; null P99=3.990%; empirical p=0.65834166; beats P95=False.
- H+8: observed ΔAccuracy=-0.756%; null P95=5.542%; null P99=7.305%; empirical p=0.55344655; beats P95=False.
- H+16: observed ΔAccuracy=-0.771%; null P95=6.941%; null P99=7.969%; empirical p=0.57342657; beats P95=False.

## Evidence by horizon

### H+4
- similarity_discrimination: `True`
- incremental_predictive_value: `False`
- calibration: `True`
- cross_window_stability: `False`
- null_support: `False`
- strong_evidence: `False`

### H+8
- similarity_discrimination: `True`
- incremental_predictive_value: `False`
- calibration: `True`
- cross_window_stability: `False`
- null_support: `False`
- strong_evidence: `False`

### H+16
- similarity_discrimination: `True`
- incremental_predictive_value: `False`
- calibration: `True`
- cross_window_stability: `False`
- null_support: `False`
- strong_evidence: `False`

## Protection

- SHA256 before: `dd57bccc3526ebaeb900181096adcbf48a84b5a3a334da1f1990a443cde091b5`
- SHA256 after: `dd57bccc3526ebaeb900181096adcbf48a84b5a3a334da1f1990a443cde091b5`
- Dataset unchanged: `True`
- Production MLAI modified: `NO`
- Learning memory modified: `NO`
- Trading: `DISABLED`

Elapsed seconds: `331.935`