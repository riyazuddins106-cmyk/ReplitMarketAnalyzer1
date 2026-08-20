# MLAI v4.1.6 — Capability 6 Incremental Predictive Value Audit

## Purpose

This is an independent read-only audit of Capability 6: incremental predictive value. It distinguishes implementation, metric correctness, retrieval/predictive integration, and actual out-of-sample predictive improvement.

## Source Integrity

- Source: `mlai_market_structure_v416.py`
- Source SHA256 before audit: `3f5b43cf8b44713c988b97cfdcd581e00c258d2367a2df3a3d14ccfb59e90580`
- Source modified by this audit: NO

## Source Evidence

- `incremental_value`: 11 source occurrence(s)
- `retrieval_brier_lift`: 4 source occurrence(s)
- `predictive_brier_lift`: 13 source occurrence(s)
- `incremental_brier_lift`: 3 source occurrence(s)
- `incremental_log_loss_lift`: 3 source occurrence(s)
- `incremental_accuracy_delta`: 3 source occurrence(s)
- `baseline_brier`: 18 source occurrence(s)
- `retrieval_brier`: 19 source occurrence(s)
- `predictive_brier`: 28 source occurrence(s)
- `baseline_log_loss`: 11 source occurrence(s)
- `retrieval_log_loss`: 11 source occurrence(s)
- `predictive_log_loss`: 20 source occurrence(s)
- `baseline_accuracy`: 13 source occurrence(s)
- `retrieval_accuracy`: 19 source occurrence(s)
- `predictive_accuracy`: 21 source occurrence(s)

Functions containing incremental-value logic:
- `calculate_incremental_value` — lines 3261-3342
- `horizon_discrimination_summary` — lines 3350-3557
- `main` — lines 3564-5599

## Direct Out-of-Sample Recalculation

### H+4

- OOS evaluations: 401
- Retrieval accuracy: 0.43890274
- Baseline accuracy: 0.44638404
- Predictive accuracy: 0.32917706
- Retrieval Brier: 0.20916488
- Baseline Brier: 0.20723375
- Predictive Brier: 0.22313710
- Retrieval LogLoss: 1.03585646
- Baseline LogLoss: 1.02368439
- Predictive LogLoss: 1.10242685
- Direct retrieval-vs-baseline Brier lift: -0.00193114
- Direct predictive-vs-baseline Brier lift: -0.01590335
- Direct predictive-vs-baseline LogLoss lift: -0.07874246
- Direct predictive-vs-baseline accuracy delta: -0.11720698

### H+8

- OOS evaluations: 397
- Retrieval accuracy: 0.47607053
- Baseline accuracy: 0.50125945
- Predictive accuracy: 0.34508816
- Retrieval Brier: 0.20150454
- Baseline Brier: 0.19930825
- Predictive Brier: 0.22129855
- Retrieval LogLoss: 1.02070550
- Baseline LogLoss: 1.02754630
- Predictive LogLoss: 1.09421558
- Direct retrieval-vs-baseline Brier lift: -0.00219629
- Direct predictive-vs-baseline Brier lift: -0.02199031
- Direct predictive-vs-baseline LogLoss lift: -0.06666928
- Direct predictive-vs-baseline accuracy delta: -0.15617128

### H+16

- OOS evaluations: 389
- Retrieval accuracy: 0.46272494
- Baseline accuracy: 0.49100257
- Predictive accuracy: 0.38560411
- Retrieval Brier: 0.20169664
- Baseline Brier: 0.20270736
- Predictive Brier: 0.22219935
- Retrieval LogLoss: 0.99695566
- Baseline LogLoss: 1.03369624
- Predictive LogLoss: 1.09684308
- Direct retrieval-vs-baseline Brier lift: 0.00101071
- Direct predictive-vs-baseline Brier lift: -0.01949199
- Direct predictive-vs-baseline LogLoss lift: -0.06314685
- Direct predictive-vs-baseline accuracy delta: -0.10539846

## Formula Consistency

Expected Brier lift is independently recomputed as `baseline Brier - model Brier`.

- W1 H+4: expected=-0.00064997, reported=-0.00064997, difference=0.00000000, **PASS**
- W1 H+8: expected=-0.00337298, reported=-0.00337298, difference=0.00000000, **PASS**
- W1 H+16: expected=-0.00256225, reported=-0.00256225, difference=0.00000000, **PASS**
- W2 H+4: expected=0.00101066, reported=0.00101066, difference=0.00000000, **PASS**
- W2 H+8: expected=0.00258167, reported=0.00258167, difference=0.00000000, **PASS**
- W2 H+16: expected=-0.00699831, reported=-0.00699831, difference=0.00000000, **PASS**
- W3 H+4: expected=-0.00023084, reported=-0.00023084, difference=0.00000000, **PASS**
- W3 H+8: expected=-0.00294163, reported=-0.00294163, difference=0.00000000, **PASS**
- W3 H+16: expected=0.00165494, reported=0.00165494, difference=0.00000000, **PASS**
- W4 H+4: expected=-0.00670915, reported=-0.00670915, difference=0.00000000, **PASS**
- W4 H+8: expected=0.00001052, reported=0.00001052, difference=0.00000000, **PASS**
- W4 H+16: expected=0.00820893, reported=0.00820893, difference=0.00000000, **PASS**
- W5 H+4: expected=-0.00313588, reported=-0.00313588, difference=0.00000000, **PASS**
- W5 H+8: expected=-0.00781383, reported=-0.00781383, difference=0.00000000, **PASS**
- W5 H+16: expected=0.00567076, reported=0.00567076, difference=0.00000000, **PASS**

Predictive Brier-lift formula:

- W1 H+4: expected=-0.01126631, reported=-0.01126631, difference=0.00000000, **PASS**
- W1 H+8: expected=-0.02428619, reported=-0.02428619, difference=0.00000000, **PASS**
- W1 H+16: expected=-0.00552973, reported=-0.00552973, difference=0.00000000, **PASS**
- W2 H+4: expected=-0.00386407, reported=-0.00386407, difference=0.00000000, **PASS**
- W2 H+8: expected=-0.01221900, reported=-0.01221900, difference=0.00000000, **PASS**
- W2 H+16: expected=-0.04078368, reported=-0.04078368, difference=0.00000000, **PASS**
- W3 H+4: expected=-0.01307674, reported=-0.01307674, difference=0.00000000, **PASS**
- W3 H+8: expected=-0.01862247, reported=-0.01862247, difference=0.00000000, **PASS**
- W3 H+16: expected=-0.02120583, reported=-0.02120583, difference=0.00000000, **PASS**
- W4 H+4: expected=-0.02659394, reported=-0.02659394, difference=0.00000000, **PASS**
- W4 H+8: expected=-0.02777960, reported=-0.02777960, difference=0.00000000, **PASS**
- W4 H+16: expected=-0.02280854, reported=-0.02280854, difference=0.00000000, **PASS**
- W5 H+4: expected=-0.02517349, reported=-0.02517349, difference=0.00000000, **PASS**
- W5 H+8: expected=-0.02759813, reported=-0.02759813, difference=0.00000000, **PASS**
- W5 H+16: expected=-0.00408975, reported=-0.00408975, difference=0.00000000, **PASS**

## Window-Level Predictive Evidence

### H+4

- Positive Brier lifts: 0/5
- Positive LogLoss lifts: 0/5
- Positive accuracy deltas: 0/5

### H+8

- Positive Brier lifts: 0/5
- Positive LogLoss lifts: 2/5
- Positive accuracy deltas: 0/5

### H+16

- Positive Brier lifts: 0/5
- Positive LogLoss lifts: 1/5
- Positive accuracy deltas: 1/5

## Null / Permutation Control

Null-test artifact: FOUND
- `queries`: 1187
- `mean_real_max_share`: 0.524523313386721
- `mean_null_max_share`: 0.5113125284590772
- `mean_null_p95`: 0.5847550513791168
- `mean_real_minus_null`: 0.013210784927643816

## Retrieval → Predictive Integration

- H+4: 401/401 evaluations contain both retrieval and predictive evidence.
- H+8: 397/397 evaluations contain both retrieval and predictive evidence.
- H+16: 389/389 evaluations contain both retrieval and predictive evidence.

## Final Assessment

**EMPIRICALLY MIXED — METRIC CALCULATION CONSISTENT**

The available Brier-lift calculations are internally consistent. This does not establish positive predictive value; it establishes that the metric calculation agrees with its stated formula.

Negative out-of-sample predictive results are retained as research findings and are not converted into PASS merely because the capability is implemented.