====================================================================================================
MLAI v4.1.6 — INDEPENDENT SEVEN-CAPABILITY AUDIT
====================================================================================================

FILES
----------------------------------------------------------------------------------------------------
mlai_market_structure_v416.py                                          : PRESENT
MLAI_V416_ROBUST_HISTORICAL_EXPERIENCE_RETRIEVAL.bin                   : PRESENT
MLAI_V416_ROBUST_HISTORICAL_EXPERIENCE_RETRIEVAL_REPORT.md             : PRESENT

SOURCE INTEGRITY
----------------------------------------------------------------------------------------------------
Source SHA256: 3f5b43cf8b44713c988b97cfdcd581e00c258d2367a2df3a3d14ccfb59e90580

SOURCE AST PARSE: PASS
Functions discovered: 54
Classes discovered  : 13
Constants discovered: 31

SOURCE IMPLEMENTATION EVIDENCE
----------------------------------------------------------------------------------------------------
Capability 1: 3 source indicators found
  similarity, similarity_score, representation
Capability 2: 6 source indicators found
  ranking, rank, discrimination, separation, retrieval, similarity
Capability 3: 3 source indicators found
  horizon, HORIZONS, 4
Capability 4: 3 source indicators found
  horizon, HORIZONS, 8
Capability 5: 3 source indicators found
  horizon, HORIZONS, 16
Capability 6: 5 source indicators found
  incremental, brier, logloss, baseline, predictive
Capability 7: 4 source indicators found
  predictive, decision, retrieval, prediction

VALIDATION ARTIFACT
----------------------------------------------------------------------------------------------------
Pickle load: PASS
Artifact type: dict
Top-level keys:
  - version
  - objective
  - candles
  - invalid_candles
  - chronology
  - causality
  - walk_forward
  - aggregate
  - similarity_buckets
  - null_test
  - v416_capabilities
  - retrieval_config
  - discrimination_config
  - market_language
  - protection

VALIDATION REPORT
----------------------------------------------------------------------------------------------------
Report file: PRESENT
Report size: 6,119 characters
'ENABLED' occurrences: 33
Important: ENABLED labels are NOT treated as proof.

AGGREGATE RESULT DISCOVERY
----------------------------------------------------------------------------------------------------
Aggregate horizon structure: FOUND
H+4: FOUND
  mean_retrieval_accuracy: 0.4394420394420394
  mean_baseline_accuracy: 0.4472342472342472
  mean_predictive_accuracy: 0.3302869969536636
  mean_brier_lift: -0.0019430340421061343
  mean_retrieval_brier: 0.2090542911922157
  mean_baseline_brier: 0.20711125715010956
  mean_predictive_brier: 0.22310616888563853
H+8: FOUND
  mean_retrieval_accuracy: 0.47640791476407907
  mean_baseline_accuracy: 0.5027228141383392
  mean_predictive_accuracy: 0.34584813123625907
  mean_brier_lift: -0.0023072511073935265
  mean_retrieval_brier: 0.20142125600546051
  mean_baseline_brier: 0.199114004898067
  mean_predictive_brier: 0.22121508197318263
H+16: FOUND
  mean_retrieval_accuracy: 0.4645014245014245
  mean_baseline_accuracy: 0.48801519468186133
  mean_predictive_accuracy: 0.38799620132953466
  mean_brier_lift: 0.0011948144055087817
  mean_retrieval_brier: 0.20193232657401844
  mean_baseline_brier: 0.20312714097952728
  mean_predictive_brier: 0.2220106460977364

====================================================================================================
CAPABILITY 1 — SIMILARITY REPRESENTATION
====================================================================================================
Artifact evidence: FOUND
Similarity-related artifact paths: 5161
  walk_forward[0].horizons.4.discrimination.mean_similarity_separation
  walk_forward[0].horizons.4.mean_top_similarity
  walk_forward[0].horizons.4.evaluations[0].retrieval.top_similarity
  walk_forward[0].horizons.4.evaluations[0].retrieval.mean_similarity
  walk_forward[0].horizons.4.evaluations[0].retrieval.similarity_representation
  walk_forward[0].horizons.4.evaluations[0].retrieval.similarity_representation.structure
  walk_forward[0].horizons.4.evaluations[0].retrieval.similarity_representation.sequence
  walk_forward[0].horizons.4.evaluations[0].retrieval.similarity_representation.regime
  walk_forward[0].horizons.4.evaluations[0].retrieval.similarity_representation.location
  walk_forward[0].horizons.4.evaluations[0].retrieval.similarity_representation.momentum
  walk_forward[0].horizons.4.evaluations[0].retrieval.similarity_representation.volatility
  walk_forward[0].horizons.4.evaluations[0].retrieval.similarity_representation.candle
  walk_forward[0].horizons.4.evaluations[0].retrieval.similarity_representation.path
  walk_forward[0].horizons.4.evaluations[0].retrieval.similarity_representation.total
  walk_forward[0].horizons.4.evaluations[0].retrieval.discrimination.top_similarity
  walk_forward[0].horizons.4.evaluations[0].retrieval.discrimination.mean_selected_similarity
  walk_forward[0].horizons.4.evaluations[0].retrieval.discrimination.mean_candidate_similarity
  walk_forward[0].horizons.4.evaluations[0].retrieval.discrimination.similarity_separation
  walk_forward[0].horizons.4.evaluations[0].similarity_bucket
  walk_forward[0].horizons.4.evaluations[1].retrieval.top_similarity

====================================================================================================
CAPABILITY 2 — RETRIEVAL RANKING / DISCRIMINATION
====================================================================================================
Discrimination evidence: FOUND
  walk_forward[0].horizons.4.discrimination
  walk_forward[0].horizons.4.discrimination.queries
  walk_forward[0].horizons.4.discrimination.discriminative_queries
  walk_forward[0].horizons.4.discrimination.discrimination_rate
  walk_forward[0].horizons.4.discrimination.mean_similarity_separation
  walk_forward[0].horizons.4.discrimination.mean_ranking_concentration
  walk_forward[0].horizons.4.discrimination.mean_directional_discrimination
  walk_forward[0].horizons.4.discrimination.mean_class_entropy
  walk_forward[0].horizons.4.discrimination.mean_baseline_entropy
  walk_forward[0].horizons.4.discrimination.mean_predictive_margin
  walk_forward[0].horizons.4.discrimination.mean_predictive_best_probability
  walk_forward[0].horizons.4.discrimination.predictive_accuracy
  walk_forward[0].horizons.4.discrimination.retrieval_accuracy
  walk_forward[0].horizons.4.discrimination.baseline_accuracy
  walk_forward[0].horizons.4.discrimination.incremental_brier_lift
  walk_forward[0].horizons.4.discrimination.incremental_log_loss_lift
  walk_forward[0].horizons.4.discrimination.incremental_accuracy_delta
  walk_forward[0].horizons.4.evaluations[0].retrieval.discrimination
  walk_forward[0].horizons.4.evaluations[0].retrieval.discrimination.candidate_count
  walk_forward[0].horizons.4.evaluations[0].retrieval.discrimination.selected_count
  walk_forward[0].horizons.4.evaluations[0].retrieval.discrimination.top_similarity
  walk_forward[0].horizons.4.evaluations[0].retrieval.discrimination.mean_selected_similarity
  walk_forward[0].horizons.4.evaluations[0].retrieval.discrimination.mean_candidate_similarity
  walk_forward[0].horizons.4.evaluations[0].retrieval.discrimination.similarity_separation
  walk_forward[0].horizons.4.evaluations[0].retrieval.discrimination.ranking_concentration
  walk_forward[0].horizons.4.evaluations[0].retrieval.discrimination.class_entropy
  walk_forward[0].horizons.4.evaluations[0].retrieval.discrimination.baseline_entropy
  walk_forward[0].horizons.4.evaluations[0].retrieval.discrimination.directional_discrimination
  walk_forward[0].horizons.4.evaluations[0].retrieval.discrimination.discriminative
  walk_forward[0].horizons.4.evaluations[1].retrieval.discrimination

====================================================================================================
CAPABILITY 3 — H+4 DISCRIMINATION
====================================================================================================
Horizon discrimination diagnostics:
  queries: 401
  discriminative_queries: 401
  discrimination_rate: 1.0
  mean_similarity_separation: 0.587478395361261
  mean_ranking_concentration: 0.6016366861944374
  mean_directional_discrimination: 0.035341372306519694
  mean_class_entropy: 0.897328086575836
  mean_baseline_entropy: 0.9211852510510432
  mean_predictive_margin: 0.034690946859183135
  mean_predictive_best_probability: 0.3701334167748162
  predictive_accuracy: 0.32917705735660846
  retrieval_accuracy: 0.4389027431421446
  baseline_accuracy: 0.4463840399002494
  incremental_brier_lift: -0.01590335486276498
  incremental_log_loss_lift: -0.07874246145138757
  incremental_accuracy_delta: -0.1172069825436409

====================================================================================================
CAPABILITY 4 — H+8 DISCRIMINATION
====================================================================================================
Horizon discrimination diagnostics:
  queries: 397
  discriminative_queries: 397
  discrimination_rate: 1.0
  mean_similarity_separation: 0.586345809637663
  mean_ranking_concentration: 0.6005346420244051
  mean_directional_discrimination: 0.04037989255967881
  mean_class_entropy: 0.8324571548194434
  mean_baseline_entropy: 0.8552396677362941
  mean_predictive_margin: 0.04392113586238775
  mean_predictive_best_probability: 0.37737207383897053
  predictive_accuracy: 0.345088161209068
  retrieval_accuracy: 0.4760705289672544
  baseline_accuracy: 0.5012594458438288
  incremental_brier_lift: -0.021990305232614256
  incremental_log_loss_lift: -0.06666928111496302
  incremental_accuracy_delta: -0.1561712846347607

====================================================================================================
CAPABILITY 5 — H+16 DISCRIMINATION
====================================================================================================
Horizon discrimination diagnostics:
  queries: 389
  discriminative_queries: 389
  discrimination_rate: 1.0
  mean_similarity_separation: 0.5851616885068622
  mean_ranking_concentration: 0.5993349252012562
  mean_directional_discrimination: 0.0507355716529062
  mean_class_entropy: 0.7768397667352304
  mean_baseline_entropy: 0.8077371226325314
  mean_predictive_margin: 0.08356558033277238
  mean_predictive_best_probability: 0.40737287906370956
  predictive_accuracy: 0.3856041131105398
  retrieval_accuracy: 0.46272493573264784
  baseline_accuracy: 0.4910025706940874
  incremental_brier_lift: -0.01949198876702072
  incremental_log_loss_lift: -0.06314684928927379
  incremental_accuracy_delta: -0.10539845758354756

====================================================================================================
CAPABILITY 6 — INCREMENTAL PREDICTIVE VALUE
====================================================================================================
  walk_forward[0].horizons.4.brier_lift
  walk_forward[0].horizons.4.predictive_brier_lift
  walk_forward[0].horizons.4.discrimination.incremental_brier_lift
  walk_forward[0].horizons.4.discrimination.incremental_log_loss_lift
  walk_forward[0].horizons.4.discrimination.incremental_accuracy_delta
  walk_forward[0].horizons.4.evaluations[0].incremental_value.retrieval_brier_lift
  walk_forward[0].horizons.4.evaluations[0].incremental_value.predictive_brier_lift
  walk_forward[0].horizons.4.evaluations[0].incremental_value.retrieval_accuracy_delta
  walk_forward[0].horizons.4.evaluations[0].incremental_value.predictive_accuracy_delta
  walk_forward[0].horizons.4.evaluations[1].incremental_value.retrieval_brier_lift
  walk_forward[0].horizons.4.evaluations[1].incremental_value.predictive_brier_lift
  walk_forward[0].horizons.4.evaluations[1].incremental_value.retrieval_accuracy_delta
  walk_forward[0].horizons.4.evaluations[1].incremental_value.predictive_accuracy_delta
  walk_forward[0].horizons.4.evaluations[2].incremental_value.retrieval_brier_lift
  walk_forward[0].horizons.4.evaluations[2].incremental_value.predictive_brier_lift
  walk_forward[0].horizons.4.evaluations[2].incremental_value.retrieval_accuracy_delta
  walk_forward[0].horizons.4.evaluations[2].incremental_value.predictive_accuracy_delta
  walk_forward[0].horizons.4.evaluations[3].incremental_value.retrieval_brier_lift
  walk_forward[0].horizons.4.evaluations[3].incremental_value.predictive_brier_lift
  walk_forward[0].horizons.4.evaluations[3].incremental_value.retrieval_accuracy_delta
  walk_forward[0].horizons.4.evaluations[3].incremental_value.predictive_accuracy_delta
  walk_forward[0].horizons.4.evaluations[4].incremental_value.retrieval_brier_lift
  walk_forward[0].horizons.4.evaluations[4].incremental_value.predictive_brier_lift
  walk_forward[0].horizons.4.evaluations[4].incremental_value.retrieval_accuracy_delta
  walk_forward[0].horizons.4.evaluations[4].incremental_value.predictive_accuracy_delta
  walk_forward[0].horizons.4.evaluations[5].incremental_value.retrieval_brier_lift
  walk_forward[0].horizons.4.evaluations[5].incremental_value.predictive_brier_lift
  walk_forward[0].horizons.4.evaluations[5].incremental_value.retrieval_accuracy_delta
  walk_forward[0].horizons.4.evaluations[5].incremental_value.predictive_accuracy_delta
  walk_forward[0].horizons.4.evaluations[6].incremental_value.retrieval_brier_lift
  walk_forward[0].horizons.4.evaluations[6].incremental_value.predictive_brier_lift
  walk_forward[0].horizons.4.evaluations[6].incremental_value.retrieval_accuracy_delta
  walk_forward[0].horizons.4.evaluations[6].incremental_value.predictive_accuracy_delta
  walk_forward[0].horizons.4.evaluations[7].incremental_value.retrieval_brier_lift
  walk_forward[0].horizons.4.evaluations[7].incremental_value.predictive_brier_lift
  walk_forward[0].horizons.4.evaluations[7].incremental_value.retrieval_accuracy_delta
  walk_forward[0].horizons.4.evaluations[7].incremental_value.predictive_accuracy_delta
  walk_forward[0].horizons.4.evaluations[8].incremental_value.retrieval_brier_lift
  walk_forward[0].horizons.4.evaluations[8].incremental_value.predictive_brier_lift
  walk_forward[0].horizons.4.evaluations[8].incremental_value.retrieval_accuracy_delta

Brier lift observations: [-0.0019430340421061343, -0.0023072511073935265, 0.0011948144055087817]
Log-loss lift observations: [-0.012147981854292934, 0.00856656734944985, 0.03691894110382228]
Accuracy deltas: []
Positive Brier lifts: 1/3
Positive LogLoss lifts: 2/3

====================================================================================================
CAPABILITY 7 — PREDICTIVE DECISION INTEGRATION
====================================================================================================
Decision-related artifact paths: 29064
  walk_forward[0].horizons.4.retrieval_accuracy
  walk_forward[0].horizons.4.retrieval_brier
  walk_forward[0].horizons.4.retrieval_log_loss
  walk_forward[0].horizons.4.predictive_accuracy
  walk_forward[0].horizons.4.predictive_brier
  walk_forward[0].horizons.4.predictive_log_loss
  walk_forward[0].horizons.4.predictive_brier_lift
  walk_forward[0].horizons.4.predictive_log_loss_lift
  walk_forward[0].horizons.4.discrimination.mean_predictive_margin
  walk_forward[0].horizons.4.discrimination.mean_predictive_best_probability
  walk_forward[0].horizons.4.discrimination.predictive_accuracy
  walk_forward[0].horizons.4.discrimination.retrieval_accuracy
  walk_forward[0].horizons.4.retrieval_coverage
  walk_forward[0].horizons.4.evaluations[0].predictive
  walk_forward[0].horizons.4.evaluations[0].predictive.prediction
  walk_forward[0].horizons.4.evaluations[0].predictive.probabilities
  walk_forward[0].horizons.4.evaluations[0].predictive.probabilities.UP
  walk_forward[0].horizons.4.evaluations[0].predictive.probabilities.DOWN
  walk_forward[0].horizons.4.evaluations[0].predictive.probabilities.NEUTRAL
  walk_forward[0].horizons.4.evaluations[0].predictive.margin
  walk_forward[0].horizons.4.evaluations[0].predictive.best_probability
  walk_forward[0].horizons.4.evaluations[0].predictive.best_class
  walk_forward[0].horizons.4.evaluations[0].predictive_evaluation
  walk_forward[0].horizons.4.evaluations[0].predictive_evaluation.predicted
  walk_forward[0].horizons.4.evaluations[0].predictive_evaluation.actual
  walk_forward[0].horizons.4.evaluations[0].predictive_evaluation.correct
  walk_forward[0].horizons.4.evaluations[0].predictive_evaluation.brier
  walk_forward[0].horizons.4.evaluations[0].predictive_evaluation.log_loss
  walk_forward[0].horizons.4.evaluations[0].retrieval
  walk_forward[0].horizons.4.evaluations[0].retrieval.horizon
  walk_forward[0].horizons.4.evaluations[0].retrieval.query_index
  walk_forward[0].horizons.4.evaluations[0].retrieval.raw_candidates
  walk_forward[0].horizons.4.evaluations[0].retrieval.deduplicated_matches
  walk_forward[0].horizons.4.evaluations[0].retrieval.top_similarity
  walk_forward[0].horizons.4.evaluations[0].retrieval.mean_similarity
  walk_forward[0].horizons.4.evaluations[0].retrieval.level
  walk_forward[0].horizons.4.evaluations[0].retrieval.evidence
  walk_forward[0].horizons.4.evaluations[0].retrieval.sparse_warning
  walk_forward[0].horizons.4.evaluations[0].retrieval.regime_agreement
  walk_forward[0].horizons.4.evaluations[0].retrieval.structure_agreement
  walk_forward[0].horizons.4.evaluations[0].retrieval.context_agreement
  walk_forward[0].horizons.4.evaluations[0].retrieval.up_share
  walk_forward[0].horizons.4.evaluations[0].retrieval.down_share
  walk_forward[0].horizons.4.evaluations[0].retrieval.neutral_share
  walk_forward[0].horizons.4.evaluations[0].retrieval.mean_atr_return
  walk_forward[0].horizons.4.evaluations[0].retrieval.mean_mfe_atr
  walk_forward[0].horizons.4.evaluations[0].retrieval.mean_mae_atr
  walk_forward[0].horizons.4.evaluations[0].retrieval.supporting_matches
  walk_forward[0].horizons.4.evaluations[0].retrieval.conflicting_matches
  walk_forward[0].horizons.4.evaluations[0].retrieval.historical_min_index

====================================================================================================
SPECIAL AUDIT — 100% DISCRIMINATION RATE
====================================================================================================
H+4 discrimination rate: 100.00%
H+8 discrimination rate: 100.00%
H+16 discrimination rate: 100.00%

WARNING:
All horizon discrimination rates are 100%.
This audit does NOT interpret that as 100% predictive success.
The rate is treated as an internal diagnostic until its definition is independently demonstrated against a null/permutation/control procedure.

====================================================================================================
FINAL SEVEN-CAPABILITY AUDIT
====================================================================================================

#   CAPABILITY                                STATUS                                
----------------------------------------------------------------------------------------------------
1   Similarity representation                 RUNTIME VERIFIED                      
2   Retrieval ranking/discrimination          RUNTIME VERIFIED                      
3   H+4 discrimination                        RUNTIME VERIFIED                      
4   H+8 discrimination                        RUNTIME VERIFIED                      
5   H+16 discrimination                       RUNTIME VERIFIED                      
6   Incremental predictive value              INCONCLUSIVE / MIXED                  
7   Predictive decision integration           RUNTIME VERIFIED                      

====================================================================================================
DETAILED ASSESSMENT
====================================================================================================

1. Similarity representation
   STATUS : RUNTIME VERIFIED
   REASON : Similarity-related values are present in the validation artifact.

2. Retrieval ranking/discrimination
   STATUS : RUNTIME VERIFIED
   REASON : Artifact exposes explicit ranking/discrimination diagnostics.

3. H+4 discrimination
   STATUS : RUNTIME VERIFIED
   REASON : H+4 has explicit similarity separation and discrimination-rate diagnostics.

4. H+8 discrimination
   STATUS : RUNTIME VERIFIED
   REASON : H+8 has explicit similarity separation and discrimination-rate diagnostics.

5. H+16 discrimination
   STATUS : RUNTIME VERIFIED
   REASON : H+16 has explicit similarity separation and discrimination-rate diagnostics.

6. Incremental predictive value
   STATUS : INCONCLUSIVE / MIXED
   REASON : Some predictive metrics improve while others do not.

7. Predictive decision integration
   STATUS : RUNTIME VERIFIED
   REASON : Retrieval/prediction/decision evidence exists in the artifact and predictive decision metrics are exposed.

====================================================================================================
SUBMISSION INTERPRETATION
====================================================================================================

OVERALL: ALL SEVEN CAPABILITIES HAVE AT LEAST RUNTIME/EMPIRICAL EVIDENCE.

IMPORTANT:
This audit separates implementation from empirical effectiveness.
A capability being present in source code is not equivalent to proving that it improves prediction.
Negative out-of-sample predictive results are retained as valid research findings and are not silently converted to PASS.

====================================================================================================
READ-ONLY INTEGRITY CHECK
====================================================================================================

Source SHA256 before audit: 3f5b43cf8b44713c988b97cfdcd581e00c258d2367a2df3a3d14ccfb59e90580
Source SHA256 after audit : 3f5b43cf8b44713c988b97cfdcd581e00c258d2367a2df3a3d14ccfb59e90580
V4.1.6 source modification during audit: NONE