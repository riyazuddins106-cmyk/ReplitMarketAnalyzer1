# MLAI V4.2.0 — Definitive Retrieval Forensic Repair

**Version:** `V420-DEFINITIVE-RETRIEVAL-FORENSIC-REPAIR-FAST-3.0`

## Final verdict: **NO CREDIBLE INCREMENTAL EVIDENCE**

This experiment is research-only. It does not modify production MLAI or historical data.

## Root-level repairs

1. Every query now receives only records whose complete outcome was known before that query.
2. The inner validation baseline is causally fenced; it cannot see labels from later in the validation period.
3. Configuration selection is chronological and OOS-blind.
4. Calibration uses a disjoint late-training slice.
5. Retrieval feature computation, all three similarity policies, and the causal baseline are cached per query, avoiding repeated nested scans.
6. The runtime defect in the original forensic script is eliminated by a complete retrieval-info contract: diagnostic fields exist even when retrieval is sparse.
7. The missing `Counter` dependency is explicitly imported.

## Global OOS results

| Horizon | Verdict | Baseline Acc | Retrieval Acc | Acc Lift | Brier Lift | LogLoss Lift | Coverage |
|---:|---|---:|---:|---:|---:|---:|---:|
| H+4 | NO_EVIDENCE | 44.8878% | 43.1421% | -1.7456% | -0.01924629 | -0.03377537 | 100.00% |
| H+8 | NO_EVIDENCE | 50.1259% | 50.1259% | 0.0000% | -0.01707457 | 0.14240394 | 100.00% |
| H+16 | NO_EVIDENCE | 49.3573% | 48.8432% | -0.5141% | -0.00323769 | 0.10213015 | 100.00% |

## Stability

- H+4: positive Brier 1/5; positive LogLoss 1/5; mean Brier lift -0.019412745271143176; mean LogLoss lift -0.0340772453795247
- H+8: positive Brier 0/5; positive LogLoss 2/5; mean Brier lift -0.01738242699902661; mean LogLoss lift 0.15175304944456708
- H+16: positive Brier 2/5; positive LogLoss 2/5; mean Brier lift -0.002956637621983065; mean LogLoss lift 0.09727427456028065

## Similarity discrimination

- H+4: Spearman(similarity, Brier) = -0.021589682510142556
  - Q1: n=100, similarity=0.82190030356238, accuracy=0.42, Brier=0.6423329413359465, Brier lift=-0.02863564265118704
  - Q2: n=100, similarity=0.8769521284292046, accuracy=0.45, Brier=0.6361679227444303, Brier lift=-0.01497003275721609
  - Q3: n=100, similarity=0.904618886098069, accuracy=0.4, Brier=0.6463283578535988, Brier lift=-0.022731140806914046
  - Q4: n=101, similarity=0.92096296531421, accuracy=0.45544554455445546, Brier=0.6357030090457876, Brier lift=-0.010733457241612518
- H+8: Spearman(similarity, Brier) = 0.01750604790995662
  - Q1: n=99, similarity=0.8244747952343972, accuracy=0.47474747474747475, Brier=0.613551329665613, Brier lift=0.013797024250757786
  - Q2: n=99, similarity=0.8800142674653162, accuracy=0.5353535353535354, Brier=0.5966676476154921, Brier lift=-0.020745189294977647
  - Q3: n=99, similarity=0.9045061453322503, accuracy=0.47474747474747475, Brier=0.636315548260519, Brier lift=-0.034260397066881734
  - Q4: n=100, similarity=0.9229853412959428, accuracy=0.52, Brier=0.6106948098698215, Brier lift=-0.02698957582972761
- H+16: Spearman(similarity, Brier) = -0.03322025812948878
  - Q1: n=97, similarity=0.8141857703590204, accuracy=0.422680412371134, Brier=0.6352001146496458, Brier lift=0.025770556171762507
  - Q2: n=97, similarity=0.8744685492224924, accuracy=0.5257731958762887, Brier=0.5924334868531705, Brier lift=-0.0023786287983450123
  - Q3: n=97, similarity=0.9011127986453976, accuracy=0.5463917525773195, Brier=0.6041396446174432, Brier lift=-0.024496723638903563
  - Q4: n=98, similarity=0.9197873581640806, accuracy=0.45918367346938777, Brier=0.6031735566967563, Brier lift=-0.011758105018441389

## Rank discrimination

- H+4: top-similarity tertile beats bottom tertile on Brier = True
  - TOP: n=133, similarity=0.9183098527848593, Brier=0.6418589847769468, Brier lift=-0.0038826887242193525
  - MIDDLE: n=134, similarity=0.8935102654325142, Brier=0.6339523426580456, Brier lift=-0.02830331027303575
  - BOTTOM: n=134, similarity=0.8320806366966966, Brier=0.6445676657873886, Brier lift=-0.025438206164377745
- H+8: top-similarity tertile beats bottom tertile on Brier = False
  - TOP: n=132, similarity=0.9198056741455372, Brier=0.6186349480046983, Brier lift=-0.028215472264345832
  - MIDDLE: n=132, similarity=0.8941957981222407, Brier=0.6203006047705443, Brier lift=-0.017009159672742715
  - BOTTOM: n=133, similarity=0.835645604401594, Brier=0.6040368875885032, Brier lift=-0.0060823595208731665
- H+16: top-similarity tertile beats bottom tertile on Brier = True
  - TOP: n=129, similarity=0.916887163967168, Brier=0.609997780548896, Brier lift=-0.017861397141560195
  - MIDDLE: n=130, similarity=0.8902005442823839, Brier=0.599048085313715, Brier lift=-0.0064399862873009
  - BOTTOM: n=130, similarity=0.8257081281508896, Brier=0.6171311434488982, Brier lift=0.014475837838853672

## Permutation tests

- H+4: observed accuracy difference=-0.017456359102244388, p=0.5338645418326693
- H+8: observed accuracy difference=0.0, p=0.5139442231075697
- H+16: observed accuracy difference=-0.005141388174807198, p=0.6055776892430279

## Protection

- market_data.bin unchanged: PASS
- Production MLAI modified: NO
- Learning memory modified: NO
- Trading: DISABLED

## Interpretation

No positive OOS result is assumed. Retrieval is considered genuinely useful only when the frozen OOS evidence demonstrates incremental probabilistic value against the causally fenced baseline, with cross-window stability and independent diagnostic support.