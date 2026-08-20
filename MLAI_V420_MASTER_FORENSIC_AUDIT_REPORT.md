# MLAI V4.2.0 MASTER FORENSIC PREDICTIVE INFORMATION AUDIT

Audit version: `V420-MASTER-FORENSIC-AUDIT-1.0`

## 1. Executive conclusion

**FINAL VERDICT: NO EVIDENCE**

This audit is diagnostic. It does not modify V4.2.0.

The purpose is to identify the exact failure location before any production change.

## 2. Foundation integrity

- Candles: 1309
- Invalid candles: 0
- Walk-forward windows: 5
- Swings: 225
- Chronology: PASS
- Causal structure: PASS

## 3. Horizon performance

| Horizon | N | Baseline Acc | Production Acc | ΔAcc | ΔBrier | ΔLogLoss |
|---|---:|---:|---:|---:|---:|---:|
| H+4 | 401 | 44.8878% | 41.8953% | -2.9925% | -0.03142614 | -1.26312103 |
| H+8 | 397 | 50.1259% | 49.3703% | -0.7557% | -0.02237110 | -1.31973679 |
| H+16 | 389 | 49.3573% | 48.5861% | -0.7712% | -0.00257596 | -1.48881810 |

## 4. Similarity validity

### H+4

- Similarity → Brier Spearman: `-0.01782931`
- Mean top similarity: `87.5217%`
- Mean candidate count: `15.96009975`

- Decile 1: N=40, similarity=78.6054%, same-outcome=32.5000%
- Decile 2: N=40, similarity=83.1262%, same-outcome=47.5000%
- Decile 3: N=40, similarity=85.1521%, same-outcome=40.0000%
- Decile 4: N=40, similarity=86.8376%, same-outcome=42.5000%
- Decile 5: N=40, similarity=88.1747%, same-outcome=30.0000%
- Decile 6: N=40, similarity=89.2166%, same-outcome=50.0000%
- Decile 7: N=40, similarity=89.9330%, same-outcome=35.0000%
- Decile 8: N=40, similarity=90.5947%, same-outcome=37.5000%
- Decile 9: N=40, similarity=91.2504%, same-outcome=55.0000%
- Decile 10: N=41, similarity=92.2090%, same-outcome=48.7805%

### H+8

- Similarity → Brier Spearman: `0.05948106`
- Mean top similarity: `87.7313%`
- Mean candidate count: `15.95214106`

- Decile 1: N=39, similarity=78.7542%, same-outcome=43.5897%
- Decile 2: N=40, similarity=83.1088%, same-outcome=45.0000%
- Decile 3: N=40, similarity=85.1892%, same-outcome=60.0000%
- Decile 4: N=39, similarity=86.9528%, same-outcome=58.9744%
- Decile 5: N=40, similarity=88.4231%, same-outcome=40.0000%
- Decile 6: N=40, similarity=89.5321%, same-outcome=57.5000%
- Decile 7: N=39, similarity=90.2425%, same-outcome=41.0256%
- Decile 8: N=40, similarity=90.9096%, same-outcome=45.0000%
- Decile 9: N=40, similarity=91.5239%, same-outcome=60.0000%
- Decile 10: N=40, similarity=92.4961%, same-outcome=42.5000%

### H+16

- Similarity → Brier Spearman: `-0.02798204`
- Mean top similarity: `86.9231%`
- Mean candidate count: `15.92544987`

- Decile 1: N=38, similarity=77.6115%, same-outcome=34.2105%
- Decile 2: N=39, similarity=81.9531%, same-outcome=61.5385%
- Decile 3: N=39, similarity=84.0077%, same-outcome=43.5897%
- Decile 4: N=39, similarity=85.9687%, same-outcome=46.1538%
- Decile 5: N=39, similarity=87.6474%, same-outcome=53.8462%
- Decile 6: N=39, similarity=88.8348%, same-outcome=51.2821%
- Decile 7: N=39, similarity=89.5946%, same-outcome=41.0256%
- Decile 8: N=39, similarity=90.3430%, same-outcome=61.5385%
- Decile 9: N=39, similarity=91.0008%, same-outcome=48.7179%
- Decile 10: N=39, similarity=92.0309%, same-outcome=43.5897%

## 5. Candidate quality / historical outcome separation

### H+4

- Mean candidate entropy H+10: 0.87937581
- Mean unique-episode ratio: 91.9142%
- Mean top-10 temporal gap: 590.60847880

### H+8

- Mean candidate entropy H+10: 0.82746410
- Mean unique-episode ratio: 91.9299%
- Mean top-10 temporal gap: 594.82392947

### H+16

- Mean candidate entropy H+10: 0.76955811
- Mean unique-episode ratio: 91.8597%
- Mean top-10 temporal gap: 596.87686375

## 6. Walk-forward stability

- H+4: Brier-positive 0/5; LogLoss-positive 0/5; mean Brier lift -0.03126360; mean LogLoss lift -1.25383711
- H+8: Brier-positive 1/5; LogLoss-positive 0/5; mean Brier lift -0.02273754; mean LogLoss lift -1.31457472
- H+16: Brier-positive 2/5; LogLoss-positive 1/5; mean Brier lift -0.00157989; mean LogLoss lift -1.45703732

## 7. Regime stability

### H+4
- `TRENDING_UP`: N=96, ΔBrier=-0.03772664, ΔLogLoss=-0.56835262, ΔAcc=-5.2083%
- `TRANSITION`: N=78, ΔBrier=-0.04994378, ΔLogLoss=-2.60692861, ΔAcc=2.5641%
- `VOL_EXPANSION`: N=65, ΔBrier=-0.03674368, ΔLogLoss=-1.96619620, ΔAcc=-6.1538%
- `TRENDING_DOWN`: N=78, ΔBrier=0.00060602, ΔLogLoss=-0.58113537, ΔAcc=-7.6923%
- `VOL_CONTRACTION`: N=84, ΔBrier=-0.03266000, ΔLogLoss=-0.89854688, ΔAcc=1.1905%

### H+8
- `TRENDING_UP`: N=96, ΔBrier=-0.01840377, ΔLogLoss=-0.76042314, ΔAcc=-7.2917%
- `TRANSITION`: N=78, ΔBrier=-0.01387928, ΔLogLoss=-1.60961119, ΔAcc=11.5385%
- `VOL_EXPANSION`: N=65, ΔBrier=-0.00890704, ΔLogLoss=-1.13064295, ΔAcc=4.6154%
- `TRENDING_DOWN`: N=76, ΔBrier=-0.01949482, ΔLogLoss=-1.99954423, ΔAcc=3.9474%
- `VOL_CONTRACTION`: N=82, ΔBrier=-0.04843191, ΔLogLoss=-1.21863486, ΔAcc=-13.4146%

### H+16
- `TRENDING_UP`: N=96, ΔBrier=0.01540371, ΔLogLoss=-2.24235340, ΔAcc=-5.2083%
- `TRANSITION`: N=77, ΔBrier=0.03212147, ΔLogLoss=-1.82219435, ΔAcc=3.8961%
- `VOL_EXPANSION`: N=65, ΔBrier=0.02724753, ΔLogLoss=-0.67674932, ΔAcc=-1.5385%
- `TRENDING_DOWN`: N=72, ΔBrier=-0.00413873, ΔLogLoss=-0.70677717, ΔAcc=6.9444%
- `VOL_CONTRACTION`: N=79, ΔBrier=-0.08135771, ΔLogLoss=-1.62909730, ΔAcc=-6.3291%

## 8. ROOT-CAUSE FINDINGS

### 1. [P0] CROSS_WINDOW_INSTABILITY

**Finding:** Only 2/5 walk-forward windows improve Brier score.

**Likely area:** non-stationary retrieval relationship / regime dependence

**Recommended fix:** Investigate regime-conditioned retrieval and temporal relevance before changing global weights.

### 2. [P0] RETRIEVAL_NEGATIVE_INCREMENTAL_VALUE

**Finding:** Historical retrieval worsens probabilistic prediction relative to the conditional baseline.

**Likely area:** retrieval integration / candidate relevance / weighting

**Recommended fix:** Do not increase retrieval weight. First isolate candidate selection, outcome homogeneity, and aggregation failure.

### 3. [P0] SIMILARITY_NOT_PREDICTIVELY_ALIGNED

**Finding:** Similarity/Brier relationship is weak (Spearman=-0.027982).

**Likely area:** market-state representation or similarity metric

**Recommended fix:** Redesign similarity only after determining which state dimensions fail to discriminate future outcomes.

### 4. [P1] CONFIDENCE_OVERSTATEMENT

**Finding:** Mean predictive confidence exceeds observed accuracy.

**Likely area:** probability construction / aggregation

**Recommended fix:** Do not use raw similarity as confidence. Calibrate probabilities using training-only calibration.

### 5. [P1] TEMPORAL_DISTANCE

**Finding:** Top historical matches are temporally remote (mean top-10 gap=596.9 candles).

**Likely area:** temporal relevance

**Recommended fix:** Evaluate recency weighting or regime-era matching.

## 9. MASTER FIX PLAN

The following order is mandatory. Do not change global retrieval weights before completing the earlier diagnostic fixes.

### P0-1 — Verify similarity/outcome relationship
Do not treat similarity as confidence until high-similarity historical states demonstrate materially different future outcome distributions.

### P0-2 — Fix candidate equivalence
Investigate which market-state dimensions are producing false historical matches.

### P0-3 — Fix outcome heterogeneity
A retrieval candidate set containing strongly conflicting future outcomes is not a predictive historical analogue.

### P0-4 — Fix retrieval aggregation
Do not assume top similarity should directly determine probability. Evaluate rank weighting, episode weighting, outcome consistency and effective sample size.

### P1-1 — Add temporal relevance only if evidence supports it
Historical similarity from a distant regime should not automatically receive the same predictive authority as a recent equivalent state.

### P1-2 — Regime-conditioned retrieval
If retrieval works in some regimes and fails in others, global retrieval should not be applied uniformly.

### P1-3 — Calibration
Similarity must never be presented as probability. Probability calibration must be learned only from training data.

### P2 — Optimize computational implementation
Only after correctness is established should candidate scanning and component calculations be optimized.

## 10. Protection verification

- Dataset unchanged: True
- Production MLAI modified: NO
- Learning memory modified: NO
- Trading enabled: NO

Audit runtime: 345.70s