
====================================================================================================
1. SOURCE INTEGRITY AND SYNTAX
====================================================================================================

SYNTAX: PASS
AST nodes: 14558

====================================================================================================
2. FUNCTION ARCHITECTURE
====================================================================================================

| Function | Count | First line |
|---|---:|---:|
| `__init__` | 2 | 366 |
| `_get_value` | 1 | 457 |
| `_is_confirmed_high` | 1 | 811 |
| `_is_confirmed_low` | 1 | 833 |
| `_normalize_candle` | 1 | 497 |
| `_outcome_direction` | 1 | 3044 |
| `_to_float` | 1 | 485 |
| `assign_episode_ids` | 1 | 1643 |
| `audit_chronology` | 1 | 652 |
| `audit_structure_causality` | 1 | 1036 |
| `brier` | 1 | 2767 |
| `bucket_name` | 1 | 3024 |
| `build` | 1 | 855 |
| `build_experience_records` | 1 | 1691 |
| `build_market_states` | 1 | 1360 |
| `build_path_vector` | 1 | 1265 |
| `calculate_atr` | 1 | 737 |
| `calculate_incremental_value` | 1 | 3261 |
| `calculate_retrieval_discrimination` | 1 | 2111 |
| `clamp` | 1 | 402 |
| `class_evidence` | 1 | 3077 |
| `classify_momentum` | 1 | 1171 |
| `classify_regime` | 1 | 1141 |
| `coarse_filter` | 1 | 1758 |
| `conditional_baseline` | 1 | 2699 |
| `create_walk_forward_windows` | 1 | 689 |
| `deterministic_permutation` | 1 | 2845 |
| `distribution_distance` | 1 | 441 |
| `distribution_from_records` | 1 | 2079 |
| `entropy3` | 1 | 421 |
| `evaluate_distribution` | 1 | 2810 |
| `fmt_num` | 1 | 416 |
| `fmt_pct` | 1 | 411 |
| `horizon_discrimination_summary` | 1 | 3350 |
| `load_market_data` | 1 | 596 |
| `log_loss` | 1 | 2789 |
| `main` | 1 | 3564 |
| `make_outcome` | 1 | 1565 |
| `mean_or_zero` | 1 | 397 |
| `null_retrieval_sanity_test` | 1 | 2875 |
| `numeric_similarity` | 1 | 1806 |
| `path_row_similarity` | 1 | 1818 |
| `path_similarity` | 1 | 1880 |
| `predictive_decision` | 1 | 3200 |
| `retrieve_historical_experience` | 1 | 2260 |
| `rolling_return` | 1 | 1125 |
| `safe_div` | 1 | 392 |
| `select_episode_representatives` | 1 | 2035 |
| `sha256_file` | 1 | 377 |
| `similarity_representation` | 1 | 1901 |
| `similarity_score` | 1 | 2008 |
| `update_sequence` | 1 | 1206 |
| `verify_unchanged` | 1 | 373 |

DUPLICATE FUNCTION DEFINITIONS DETECTED:
- `__init__` appears 2 times

====================================================================================================
3. REQUIRED V4.1.6 COMPONENTS
====================================================================================================

| Component | Exists | Count | Line |
|---|---|---:|---:|
| `similarity_representation` | YES | 1 | 1901 |
| `similarity_score` | YES | 1 | 2008 |
| `calculate_retrieval_discrimination` | YES | 1 | 2111 |
| `retrieve_historical_experience` | YES | 1 | 2260 |
| `null_retrieval_sanity_test` | YES | 1 | 2875 |
| `predictive_decision` | YES | 1 | 3200 |
| `calculate_incremental_value` | YES | 1 | 3261 |
| `horizon_discrimination_summary` | YES | 1 | 3350 |
| `build_experience_records` | YES | 1 | 1691 |
| `make_outcome` | YES | 1 | 1565 |
| `conditional_baseline` | YES | 1 | 2699 |
| `evaluate_distribution` | YES | 1 | 2810 |
| `main` | YES | 1 | 3564 |

====================================================================================================
4. CALL GRAPH
====================================================================================================

`main`
- _get_value
- _is_confirmed_high
- _is_confirmed_low
- _normalize_candle
- _outcome_direction
- _to_float
- assign_episode_ids
- audit_chronology
- audit_structure_causality
- brier
- bucket_name
- build
- build_experience_records
- build_market_states
- build_path_vector
- calculate_atr
- calculate_incremental_value
- calculate_retrieval_discrimination
- clamp
- class_evidence
- classify_momentum
- classify_regime
- coarse_filter
- conditional_baseline
- create_walk_forward_windows
- deterministic_permutation
- distribution_from_records
- entropy3
- evaluate_distribution
- fmt_num
- fmt_pct
- horizon_discrimination_summary
- load_market_data
- log_loss
- make_outcome
- mean_or_zero
- null_retrieval_sanity_test
- numeric_similarity
- path_row_similarity
- path_similarity
- predictive_decision
- retrieve_historical_experience
- rolling_return
- safe_div
- select_episode_representatives
- sha256_file
- similarity_representation
- similarity_score
- update_sequence
`retrieve_historical_experience`
- calculate_retrieval_discrimination
- clamp
- coarse_filter
- distribution_from_records
- entropy3
- mean_or_zero
- numeric_similarity
- path_row_similarity
- path_similarity
- safe_div
- select_episode_representatives
- similarity_representation
- similarity_score
`predictive_decision`
- _outcome_direction
- clamp
- class_evidence
- mean_or_zero
- numeric_similarity
- path_row_similarity
- path_similarity
- similarity_representation
`calculate_incremental_value`
`horizon_discrimination_summary`
- mean_or_zero

====================================================================================================
5. OUT-OF-SAMPLE / WALK-FORWARD PIPELINE
====================================================================================================

OOS loop candidates: 3
- line 3765: append, asdict, bucket_name, build_experience_records, calculate_incremental_value, conditional_baseline, evaluate_distribution, fmt_num, fmt_pct, horizon_discrimination_summary, len, make_outcome, mean_or_zero, null_retrieval_sanity_test, predictive_decision, print, range, retrieve_historical_experience, safe_div
- line 3781: append, asdict, bucket_name, build_experience_records, calculate_incremental_value, conditional_baseline, evaluate_distribution, fmt_num, fmt_pct, horizon_discrimination_summary, len, make_outcome, mean_or_zero, null_retrieval_sanity_test, predictive_decision, print, range, retrieve_historical_experience, safe_div
- line 3795: append, asdict, bucket_name, calculate_incremental_value, conditional_baseline, evaluate_distribution, len, make_outcome, null_retrieval_sanity_test, predictive_decision, range, retrieve_historical_experience
WARNING: Multiple loops satisfy the basic OOS call signature. This requires manual semantic verification.

====================================================================================================
6. REQUIRED EVALUATION MARKERS
====================================================================================================

`selected_match_indices` -> 353, 2373, 2687
`similarity_bucket` -> 3907, 4530, 4749
`incremental_value` -> 3261, 3529, 3540, 3551, 3875, 3876, 3905
`null_test` -> 3921, 4752
`predictive_evaluation` -> 3264, 3274, 3284, 3308, 3396, 3889, 3954, 3998, 4037, 4549, 4579
`retrieval_evaluation` -> 3262, 3269, 3279, 3290, 3407, 3895, 3969, 4011, 4050, 4540, 4568
`baseline_evaluation` -> 3263, 3268, 3273, 3278, 3283, 3298, 3316, 3418, 3903, 3984, 4024, 4063, 4558
`discrimination` -> 9, 10, 11, 12, 26, 27, 28, 29, 314, 357, 2111, 2133, 2229, 2251, 2341, 2385, 2386, 2689, 2690, 3350
`predictive_margin` -> 3365, 3497, 4276, 5546
`similarity_separation` -> 308, 2129, 2161, 2237, 2247, 3360, 3442, 3447, 4266, 4612, 4620, 4832, 5155, 5364, 5536
`directional_discrimination` -> 314, 2133, 2229, 2251, 3362, 3464, 3469, 4271, 4626, 4634, 5165, 5369, 5541

====================================================================================================
7. METRIC IMPLEMENTATION AUDIT
====================================================================================================


### `calculate_retrieval_discrimination`
Line: 2111
Arguments: selected_matches, all_candidates, selected_records, candidate_records
Calls: RetrievalDiscrimination, clamp, distribution_from_records, entropy3, len, max, mean_or_zero, safe_div, sorted
- contains accuracy: NO
- contains brier: NO
- contains log_loss: NO
- contains similarity: YES
- contains direction: YES
- contains rate: NO
- contains margin: NO
- contains null: NO

### `horizon_discrimination_summary`
Line: 3350
Arguments: rows
Calls: bool, len, mean_or_zero, sum
- contains accuracy: YES
- contains brier: YES
- contains log_loss: YES
- contains similarity: YES
- contains direction: YES
- contains rate: YES
- contains margin: YES
- contains null: NO

### `calculate_incremental_value`
Line: 3261
Arguments: retrieval_evaluation, baseline_evaluation, predictive_evaluation
Calls: NONE
- contains accuracy: YES
- contains brier: YES
- contains log_loss: YES
- contains similarity: NO
- contains direction: NO
- contains rate: NO
- contains margin: NO
- contains null: NO

### `predictive_decision`
Line: 3200
Arguments: current, records, query_index
Calls: class_evidence, items, sorted
- contains accuracy: NO
- contains brier: NO
- contains log_loss: NO
- contains similarity: NO
- contains direction: NO
- contains rate: NO
- contains margin: YES
- contains null: NO

### `evaluate_distribution`
Line: 2810
Arguments: distribution, actual
Calls: brier, items, log_loss, sorted
- contains accuracy: NO
- contains brier: YES
- contains log_loss: YES
- contains similarity: NO
- contains direction: NO
- contains rate: NO
- contains margin: NO
- contains null: NO

### `null_retrieval_sanity_test`
Line: 2875
Arguments: current, records, query_index, horizon
Calls: ExperienceRecord, Outcome, append, deterministic_permutation, int, len, max, mean_or_zero, min, range, retrieve_historical_experience, sorted, zip
- contains accuracy: NO
- contains brier: NO
- contains log_loss: NO
- contains similarity: NO
- contains direction: YES
- contains rate: NO
- contains margin: NO
- contains null: YES

====================================================================================================
8. DISCRIMINATION SEMANTICS — CRITICAL AUDIT
====================================================================================================


### `calculate_retrieval_discrimination` source excerpt
```python
def calculate_retrieval_discrimination(
    selected_matches: Sequence[SimilarityMatch],
    all_candidates: Sequence[SimilarityMatch],
    selected_records: Sequence[ExperienceRecord],
    candidate_records: Sequence[ExperienceRecord],
) -> RetrievalDiscrimination:

    candidate_count = len(all_candidates)
    selected_count = len(selected_matches)

    if not all_candidates:

        return RetrievalDiscrimination(
            candidate_count=0,
            selected_count=0,
            top_similarity=0.0,
            mean_selected_similarity=0.0,
            mean_candidate_similarity=0.0,
            similarity_separation=0.0,
            ranking_concentration=0.0,
            class_entropy=1.0,
            baseline_entropy=1.0,
            directional_discrimination=0.0,
            discriminative=False,
        )

    candidate_similarities = [
        match.similarity
        for match in all_candidates
    ]

    selected_similarities = [
        match.similarity
        for match in selected_matches
    ]

    top_similarity = (
        max(selected_similarities)
        if selected_similarities
        else 0.0
    )

    mean_selected = mean_or_zero(
        selected_similarities
    )

    mean_candidate = mean_or_zero(
        candidate_similarities
    )

    similarity_separation = clamp(
        safe_div(
            mean_selected
            - mean_candidate,
            max(
                1.0 - mean_candidate,
                EPS,
            ),
        )
    )

    if candidate_similarities:

        median_candidate = sorted(
            candidate_similarities
        )[len(candidate_similarities) // 2]

    else:

        median_candidate = 0.0

    ranking_concentration = clamp(
        safe_div(
            mean_selected
            - median_candidate,
            max(
                1.0 - median_candidate,
                EPS,
            ),
        )
    )

    selected_distribution = (
        distribution_from_records(
            selected_records
        )
        if selected_records
        else {
            "UP": 1.0 / 3.0,
            "DOWN": 1.0 / 3.0,
            "NEUTRAL": 1.0 / 3.0,
        }
    )

    candidate_distribution = (
        distribution_from_records(
            candidate_records
        )
        if candidate_records
        else {
            "UP": 1.0 / 3.0,
            "DOWN": 1.0 / 3.0,
            "NEUTRAL": 1.0 / 3.0,
        }
    )

    class_entropy = entropy3(
        selected_distribution["UP"],
        selected_distribution["DOWN"],
        selected_distribution["NEUTRAL"],
    )

    baseline_entropy = entropy3(
        candidate_distribution["UP"],
        candidate_distribution["DOWN"],
        candidate_distribution["NEUTRAL"],
    )

    directional_discrimination = clamp(
        baseline_entropy
        - class_entropy
    )

    discriminative = (
        selected_count
        >= DISCRIMINATION_MIN_MATCHES
        and similarity_separation
        >= MIN_SIMILARITY_SEPARATION
    )

    return RetrievalDiscrimination(
        candidate_count=candidate_count,
        selected_count=selected_count,
        top_similarity=top_similarity,
        mean_selected_similarity=mean_selected,
        mean_candidate_similarity=mean_candidate,
        similarity_separation=similarity_separation,
        ranking_concentration=ranking_concentration,
        class_entropy=class_entropy,
        baseline_entropy=baseline_entropy,
        directional_discrimination=directional_discrimination,
        discriminative=discriminative,
    )
```

### `horizon_discrimination_summary` source excerpt
```python
def horizon_discrimination_summary(
    rows: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:

    if not rows:

        return {
            "queries": 0,
            "discriminative_queries": 0,
            "discrimination_rate": None,
            "mean_similarity_separation": None,
            "mean_ranking_concentration": None,
            "mean_directional_discrimination": None,
            "mean_class_entropy": None,
            "mean_baseline_entropy": None,
            "mean_predictive_margin": None,
            "mean_predictive_best_probability": None,
            "predictive_accuracy": None,
            "retrieval_accuracy": None,
            "baseline_accuracy": None,
            "incremental_brier_lift": None,
            "incremental_log_loss_lift": None,
            "incremental_accuracy_delta": None,
        }

    discrimination_rows = [
        row
        for row in rows
        if row["retrieval"][
            "discrimination"
        ]
    ]

    discrimination_flags = [
        bool(
            row["retrieval"][
                "discrimination"
            ]["discriminative"]
        )
        for row in rows
    ]

    predictive_accuracy = mean_or_zero(
        [
            1.0
            if row[
                "predictive_evaluation"
            ]["correct"]
            else 0.0
            for row in rows
        ]
    )

    retrieval_accuracy = mean_or_zero(
        [
            1.0
            if row[
                "retrieval_evaluation"
            ]["correct"]
            else 0.0
            for row in rows
        ]
    )

    baseline_accuracy = mean_or_zero(
        [
            1.0
            if row[
                "baseline_evaluation"
            ]["correct"]
            else 0.0
            for row in rows
        ]
    )

    return {
        "queries": len(rows),

        "discriminative_queries": sum(
            discrimination_flags
        ),

        "discrimination_rate": (
            mean_or_zero(
                [
                    1.0 if x else 0.0
                    for x
                    in discrimination_flags
                ]
            )
        ),

        "mean_similarity_separation": (
            mean_or_zero(
                [
                    row["retrieval"][
                        "discrimination"
                    ]["similarity_separation"]
                    for row in rows
                ]
            )
        ),

        "mean_ranking_concentration": (
            mean_or_zero(
                [
                    row["retrieval"][
                        "discrimination"
                    ]["ranking_concentration"]
                    for row in rows
                ]
            )
        ),

        "mean_directional_discrimination": (
            mean_or_zero(
                [
                    row["retrieval"][
                        "discrimination"
                    ]["directional_discrimination"]
                    for row in rows
                ]
            )
        ),

        "mean_class_entropy": (
            mean_or_zero(
                [
                    row["retrieval"][
                        "discrimination"
                    ]["class_entropy"]
                    for row in rows
                ]
            )
        ),

        "mean_baseline_entropy": (
            mean_or_zero(
                [
                    row["retrieval"][
                        "discrimination"
                    ]["baseline_entropy"]
                    for row in rows
                ]
            )
        ),

        "mean_predictive_margin": (
            mean_or_zero(
                [
                    row[
                        "predictive"
                    ]["margin"]
                    for row in rows
                ]
            )
        ),

        "mean_predictive_best_probability": (
            mean_or_zero(
                [
                    row[
                        "predictive"
                    ]["best_probability"]
                    for row in rows
                ]
            )
        ),

        "predictive_accuracy": predictive_accuracy,

        "retrieval_accuracy": retrieval_accuracy,

        "baseline_accuracy": baseline_accuracy,

        "incremental_brier_lift": (
            mean_or_zero(
                [
                    row[
                        "incremental_value"
                    ]["predictive_brier_lift"]
                    for row in rows
                ]
            )
        ),

        "incremental_log_loss_lift": (
            mean_or_zero(
                [
                    row[
                        "incremental_value"
                    ]["predictive_log_loss_lift"]
                    for row in rows
                ]
            )
        ),

        "incremental_accuracy_delta": (
            mean_or_zero(
                [
                    row[
                        "incremental_value"
                    ]["predictive_accuracy_delta"]
                    for row in rows
                ]
            )
        ),
    }
```

IMPORTANT DIAGNOSTIC QUESTION:
Does `discrimination_rate` measure genuine outcome discrimination, or merely the percentage of queries for which the discrimination calculation was available?
The runtime result of 100.00% for H4/H8/H16 must NOT automatically be interpreted as 100% predictive discrimination.

====================================================================================================
9. SIMILARITY REPRESENTATION AND RANKING
====================================================================================================

### `similarity_representation`
Lines: 1901-2005
Arguments: current, record
Internal calls: SimilarityRepresentation, clamp, mean_or_zero, numeric_similarity, path_similarity
- normalization: NOT EVIDENT
- distance: NOT EVIDENT
- weighting: FOUND
- rank/sort: NOT EVIDENT
- episode: NOT EVIDENT
- temporal exclusion: NOT EVIDENT
### `similarity_score`
Lines: 2008-2028
Arguments: current, record
Internal calls: similarity_representation
- normalization: NOT EVIDENT
- distance: NOT EVIDENT
- weighting: NOT EVIDENT
- rank/sort: NOT EVIDENT
- episode: NOT EVIDENT
- temporal exclusion: NOT EVIDENT
### `path_similarity`
Lines: 1880-1893
Arguments: current, record
Internal calls: mean_or_zero, path_row_similarity, zip
- normalization: NOT EVIDENT
- distance: NOT EVIDENT
- weighting: NOT EVIDENT
- rank/sort: NOT EVIDENT
- episode: NOT EVIDENT
- temporal exclusion: NOT EVIDENT
### `numeric_similarity`
Lines: 1806-1815
Arguments: a, b, scale
Internal calls: abs, exp, max
- normalization: NOT EVIDENT
- distance: NOT EVIDENT
- weighting: NOT EVIDENT
- rank/sort: NOT EVIDENT
- episode: NOT EVIDENT
- temporal exclusion: NOT EVIDENT
### `retrieve_historical_experience`
Lines: 2260-2692
Arguments: current, records, horizon, query_index
Internal calls: RetrievalResult, SimilarityMatch, append, asdict, calculate_retrieval_discrimination, coarse_filter, len, max, mean_or_zero, min, safe_div, select_episode_representatives, similarity_score, sort, sum, zip
- normalization: NOT EVIDENT
- distance: NOT EVIDENT
- weighting: FOUND
- rank/sort: FOUND
- episode: FOUND
- temporal exclusion: FOUND
### `select_episode_representatives`
Lines: 2035-2072
Arguments: matches
Internal calls: get, list, sort, values
- normalization: NOT EVIDENT
- distance: NOT EVIDENT
- weighting: NOT EVIDENT
- rank/sort: FOUND
- episode: FOUND
- temporal exclusion: FOUND

====================================================================================================
10. HISTORICAL RETRIEVAL AUDIT
====================================================================================================

- coarse filtering: FOUND
- similarity scoring: FOUND
- episode deduplication: FOUND
- top-k selection: NOT EVIDENT
- selected matches: FOUND
- sparse handling: FOUND
- query index: FOUND
- horizon: FOUND

====================================================================================================
11. PREDICTIVE DECISION INTEGRATION
====================================================================================================

Function lines: 3200-3253
- retrieval: NOT EVIDENT
- probabilities: FOUND
- confidence: NOT EVIDENT
- abstention: NOT EVIDENT
- logistic: NOT EVIDENT
- knn: NOT EVIDENT
- state evidence: FOUND
- weights: NOT EVIDENT
- similarity: NOT EVIDENT

Predictive source excerpt:
```python
def predictive_decision(
    current: MarketState,
    records: Sequence[ExperienceRecord],
    query_index: int,
) -> Dict[str, Any]:

    probabilities = class_evidence(
        current,
        records,
        query_index,
    )

    ranked = sorted(
        probabilities.items(),
        key=lambda x: x[1],
        reverse=True,
    )

    best_class = ranked[0][0]

    best_probability = ranked[0][1]

    second_probability = ranked[1][1]

    margin = (
        best_probability
        - second_probability
    )

    if (
        best_probability
        < PREDICTION_MIN_PROBABILITY
    ):

        prediction = "NEUTRAL"

    elif (
        margin
        < PREDICTION_MIN_MARGIN
    ):

        prediction = "NEUTRAL"

    else:

        prediction = best_class

    return {
        "prediction": prediction,
        "probabilities": probabilities,
        "margin": margin,
        "best_probability": best_probability,
        "best_class": best_class,
    }
```

====================================================================================================
12. INCREMENTAL PREDICTIVE VALUE
====================================================================================================

Function lines: 3261-3342
Source:
```python
def calculate_incremental_value(
    retrieval_evaluation: Dict[str, Any],
    baseline_evaluation: Dict[str, Any],
    predictive_evaluation: Dict[str, Any],
) -> Dict[str, Any]:

    retrieval_brier_lift = (
        baseline_evaluation["brier"]
        - retrieval_evaluation["brier"]
    )

    predictive_brier_lift = (
        baseline_evaluation["brier"]
        - predictive_evaluation["brier"]
    )

    retrieval_log_loss_lift = (
        baseline_evaluation["log_loss"]
        - retrieval_evaluation["log_loss"]
    )

    predictive_log_loss_lift = (
        baseline_evaluation["log_loss"]
        - predictive_evaluation["log_loss"]
    )

    retrieval_accuracy_delta = (
        (
            1.0
            if retrieval_evaluation[
                "correct"
            ]
            else 0.0
        )
        -
        (
            1.0
            if baseline_evaluation[
                "correct"
            ]
            else 0.0
        )
    )

    predictive_accuracy_delta = (
        (
            1.0
            if predictive_evaluation[
                "correct"
            ]
            else 0.0
        )
        -
        (
            1.0
            if baseline_evaluation[
                "correct"
            ]
            else 0.0
        )
    )

    return {
        "retrieval_brier_lift": retrieval_brier_lift,
        "predictive_brier_lift": predictive_brier_lift,
        "retrieval_log_loss_lift": retrieval_log_loss_lift,
        "predictive_log_loss_lift": predictive_log_loss_lift,
        "retrieval_accuracy_delta": retrieval_accuracy_delta,
        "predictive_accuracy_delta": predictive_accuracy_delta,
        "predictive_improves_brier": (
            predictive_brier_lift
            > INCREMENTAL_VALUE_EPS
        ),
        "predictive_improves_log_loss": (
            predictive_log_loss_lift
            > INCREMENTAL_VALUE_EPS
        ),
        "predictive_improves_accuracy": (
            predictive_accuracy_delta
            > INCREMENTAL_VALUE_EPS
        ),
    }
```
- `retrieval`: FOUND
- `baseline`: FOUND
- `predictive`: FOUND
- `brier`: FOUND
- `log_loss`: FOUND
- `accuracy`: FOUND

====================================================================================================
13. NULL RETRIEVAL SANITY TEST
====================================================================================================

Function lines: 2875-3017
- `random`: NOT EVIDENT
- `shuffle`: FOUND
- `permutation`: FOUND
- `null`: FOUND
- `similarity`: NOT EVIDENT
- `retrieval`: FOUND
- `outcome`: FOUND

Source excerpt:
```python
def null_retrieval_sanity_test(
    current: MarketState,
    records: Sequence[ExperienceRecord],
    query_index: int,
    horizon: int,
) -> Dict[str, Any]:

    eligible = [
        record
        for record in records
        if (
            record.index < query_index
            and
            query_index - record.index
            >= MIN_HISTORY_GAP
        )
    ]

    if (
        len(eligible)
        < MIN_RETRIEVAL_MATCHES
    ):

        return {
            "available": False,
            "permutations": 0,
            "real_max_share": None,
            "null_max_share_mean": None,
            "null_max_share_p95": None,
            "real_minus_null_mean": None,
        }

    real = retrieve_historical_experience(
        current,
        eligible,
        horizon,
        query_index,
    )

    real_max_share = max(
        real.up_share,
        real.down_share,
        real.neutral_share,
    )

    outcomes = [
        record.outcome.direction
        for record in eligible
    ]

    null_max = []

    for permutation in range(
        NULL_PERMUTATIONS
    ):

        shuffled = deterministic_permutation(
            outcomes,
            seed=1009
            * (permutation + 1)
            + query_index,
        )

        permuted_records = []

        for record, direction in zip(
            eligible,
            shuffled,
        ):

            permuted_records.append(
                ExperienceRecord(
                    index=record.index,
                    episode_id=record.episode_id,
                    state_key=record.state_key,
                    sequence_state=record.sequence_state,
                    regime=record.regime,
                    structure_event=record.structure_event,
                    location=record.location,
                    momentum_state=record.momentum_state,
                    volatility_ratio=record.volatility_ratio,
                    body_ratio=record.body_ratio,
                    range_ratio=record.range_ratio,
                    r1=record.r1,
                    r3=record.r3,
                    r8=record.r8,
                    r16=record.r16,
                    path_vector=record.path_vector,
                    horizon=record.horizon,
                    outcome=Outcome(
                        direction=direction,
                        raw_return=record.outcome.raw_return,
                        atr_return=record.outcome.atr_return,
                        mfe_atr=record.outcome.mfe_atr,
                        mae_atr=record.outcome.mae_atr,
                    ),
                )
            )

        null_result = retrieve_historical_experience(
            current,
            permuted_records,
            horizon,
            query_index,
        )

        null_max.append(
            max(
                null_result.up_share,
                null_result.down_share,
                null_result.neutral_share,
            )
        )

    ordered = sorted(null_max)

    p95 = ordered[
        min(
            len(ordered) - 1,
            int(
                0.95
                * (
                    len(ordered) - 1
                )
            ),
        )
    ]

    null_mean = mean_or_zero(
        null_max
    )

    return {
        "available": True,
        "permutations": len(null_max),
        "real_max_share": real_max_share,
        "null_max_share_mean": null_mean,
        "null_max_share_p95": p95,
        "real_minus_null_mean": (
            real_max_share
            - null_mean
        ),
    }
```

====================================================================================================
14. CAUSALITY / LEAKAGE STATIC AUDIT
====================================================================================================

Potential future-related references: 85
NOTE: These are diagnostic candidates, NOT automatic leakage failures.
- line 36: [outcome] - No OOS outcome is supplied to the predictor.
- line 46: [future] from __future__ import annotations
- line 168: [label] label: str = ""
- line 179: [label] high_label: str
- line 180: [label] low_label: str
- line 188: [forward] class WalkForwardWindow:
- line 208: [label] high_label: str
- line 209: [label] low_label: str
- line 225: [outcome] class Outcome:
- line 252: [outcome] outcome: Outcome
- line 686: [forward] # WALK FORWARD
- line 689: [forward] def create_walk_forward_windows(
- line 693: [forward] ) -> List[WalkForwardWindow]:
- line 697: [forward] "Insufficient candles for requested walk-forward setup."
- line 721: [forward] WalkForwardWindow(
- line 862: [label] high_label = "UNKNOWN"
- line 863: [label] low_label = "UNKNOWN"
- line 879: [label] label = (
- line 894: [label] label,
- line 899: [label] high_label = label
- line 903: [label] label = (
- line 918: [label] label,
- line 923: [label] low_label = label
- line 1024: [label] high_label=high_label,
- line 1025: [label] low_label=low_label,
- line 1079: [future] f"Future high visible at state {state.index}."
- line 1098: [future] f"Future low visible at state {state.index}."
- line 1112: [future] f"Future event visible at state {state.index}."
- line 1511: [label] state.high_label,
- line 1512: [label] state.low_label,
- line 1541: [label] high_label=state.high_label,
- line 1542: [label] low_label=state.low_label,
- line 1562: [outcome] # OUTCOME
- line 1565: [outcome] def make_outcome(
- line 1570: [outcome] ) -> Optional[Outcome]:
- line 1572: [target] target = index + horizon
- line 1574: [target] if target >= len(candles):
- line 1587: [future] future_close = candles[target].close
- line 1590: [future] future_close - base,
- line 1595: [future] future_close - base,
- line 1608: [future] future_high = max(
- line 1612: [target] target + 1
- line 1616: [future] future_low = min(
- line 1620: [target] target + 1
- line 1624: [outcome] return Outcome(
- line 1629: [future] future_high - base,
- line 1633: [future] future_low - base,
- line 1716: [outcome] outcome = make_outcome(
- line 1723: [outcome] if outcome is None:
- line 1747: [outcome] outcome=outcome,
- line 1919: [label] if current.high_label
- line 1924: [label] if current.low_label
- line 2084: [outcome] record.outcome.direction
- line 2405: [outcome] if record.outcome.direction
- line 2419: [outcome] if record.outcome.direction
- line 2433: [outcome] if record.outcome.direction
- line 2458: [outcome] if record.outcome.direction
- line 2515: [outcome] record.outcome.atr_return
- line 2531: [outcome] record.outcome.mfe_atr
- line 2547: [outcome] record.outcome.mae_atr
- line 2920: [outcome] outcomes = [
- line 2921: [outcome] record.outcome.direction
- line 2932: [outcome] outcomes,
- line 2964: [outcome] outcome=Outcome(
- line 2966: [outcome] raw_return=record.outcome.raw_return,
- line 2967: [outcome] atr_return=record.outcome.atr_return,
- line 2968: [outcome] mfe_atr=record.outcome.mfe_atr,
- line 2969: [outcome] mae_atr=record.outcome.mae_atr,
- line 3044: [outcome] def _outcome_direction(
- line 3048: [outcome] outcome = getattr(
- line 3050: [outcome] "outcome",
- line 3055: [outcome] outcome,
- line 3102: [outcome] direction = _outcome_direction(
- line 3640: [forward] windows = create_walk_forward_windows(
- line 3760: [forward] "STRICT WALK-FORWARD HISTORICAL "
- line 3829: [outcome] outcome = make_outcome(
- line 3836: [outcome] if outcome is None:
- line 3848: [outcome] outcome.direction,
- line 3857: [outcome] outcome.direction,
- line 3871: [outcome] outcome.direction,
- line 3885: [outcome] "actual": outcome.direction,
- line 4743: [forward] "walk_forward":
- line 5012: [outcome] "- ATR-normalized outcomes: ENABLED"
- line 5084: [outcome] "- OOS outcomes used for retrieval: NO"
- line 5211: [forward] "## Walk-forward aggregate"

====================================================================================================
15. MAIN OOS EVALUATION SOURCE
====================================================================================================

```python
        "STRICT WALK-FORWARD HISTORICAL "
        "RETRIEVAL + DISCRIMINATION"
    )
    print("=" * 100)

    for window in windows:

        window_result = {
            "window": asdict(window),
            "horizons": {},
        }

        print()
        print("-" * 100)

        print(
            f"WINDOW {window.number} | "
            f"TRAIN [{window.train_start}:{window.train_end}] | "
            f"OOS [{window.oos_start}:{window.oos_end}]"
        )

        for horizon in HORIZONS:

            records = build_experience_records(
                candles,
                atr,
                market_states,
                episode_ids,
                window.train_start,
                window.train_end,
                horizon,
            )

            evaluations = []

            for query_index in range(
                window.oos_start,
                window.oos_end,
            ):

                if (
                    query_index + horizon
                    >= len(candles)
                ):
                    continue

                query_state = (
                    market_states[
                        query_index
                    ]
                )

                retrieval = (
                    retrieve_historical_experience(
                        query_state,
                        records,
                        horizon,
                        query_index,
                    )
                )

                predictive = (
                    predictive_decision(
                        query_state,
                        records,
                        query_index,
                    )
                )

                outcome = make_outcome(
                    candles,
                    atr,
                    query_index,
                    horizon,
                )

                if outcome is None:
                    continue

                retrieval_distribution = {
                    "UP": retrieval.up_share,
                    "DOWN": retrieval.down_share,
                    "NEUTRAL": retrieval.neutral_share,
                }

                retrieval_eval = (
                    evaluate_distribution(
                        retrieval_distribution,
                        outcome.direction,
                    )
                )

                predictive_eval = (
                    evaluate_distribution(
                        predictive[
                            "probabilities"
                        ],
                        outcome.direction,
                    )
                )

                baseline_level, baseline_distribution, baseline_samples = (
                    conditional_baseline(
                        query_state,
                        records,
                    )
                )

                baseline_eval = (
                    evaluate_distribution(
                        baseline_distribution,
                        outcome.direction,
                    )
                )

                incremental_value = (
                    calculate_incremental_value(
                        retrieval_eval,
                        baseline_eval,
                        predictive_eval,
                    )
                )

                row = {
                    "query_index": query_index,
                    "actual": outcome.direction,

                    "predictive": predictive,

                    "predictive_evaluation": predictive_eval,

                    "retrieval": asdict(
                        retrieval
                    ),

                    "retrieval_evaluation": retrieval_eval,

                    "baseline": baseline_distribution,

                    "baseline_level": baseline_level,

                    "baseline_samples": baseline_samples,

                    "baseline_evaluation": baseline_eval,

                    "incremental_value": incremental_value,

                    "similarity_bucket": bucket_name(
                        retrieval.top_similarity
                    ),
                }

                null_result = (
                    null_retrieval_sanity_test(
                        query_state,
                        records,
                        query_index,
                        horizon,
                    )
                )

                row["null_test"] = (
                    null_result
                )

                evaluations.append(
                    row
                )

                all_horizon_rows[
                    horizon
                ].append(row)

                bucket_rows.append(
                    row
                )

                if null_result[
                    "available"
                ]:

                    null_rows.append(
                        null_result
                    )

            # ---------------------------------------------------------
            # WINDOW METRICS
            # ---------------------------------------------------------

            predictive_accuracy = (
                mean_or_zero(
                    [
                        1.0
                        if row[
                            "predictive_evaluation"
                        ]["correct"]
                        else 0.0
                        for row in evaluations
                    ]
                )
                if evaluations
                else None
            )

            retrieval_accuracy = (
                mean_or_zero(
                    [
                        1.0
                        if row[
                            "retrieval_evaluation"
                        ]["correct"]
                        else 0.0
                        for row in evaluations
                    ]
                )
                if evaluations
                else None
            )

            baseline_accuracy = (
                mean_or_zero(
                    [
                        1.0
                        if row[
                            "baseline_evaluation"
                        ]["correct"]
                        else 0.0
                        for row in evaluations
                    ]
                )
                if evaluations
                else None
            )

            predictive_brier = (
                mean_or_zero(
                    [
                        row[
                            "predictive_evaluation"
                        ]["brier"]
                        for row in evaluations
                    ]
                )
                if evaluations
                else None
            )

            retrieval_brier = (
                mean_or_zero(
                    [
                        row[
                            "retrieval_evaluation"
                        ]["brier"]
                        for row in evaluations
                    ]
                )
                if evaluations
                else None
            )

            baseline_brier = (
                mean_or_zero(
                    [
                        row[
                            "baseline_evaluation"
                        ]["brier"]
                        for row in evaluations
                    ]
                )
                if evaluations
                else None
            )

            predictive_log_loss = (
                mean_or_zero(
```

====================================================================================================
16. MODEL / VALIDATION CONSTANTS
====================================================================================================

- `VERSION` = `4.1.6`
- `MARKET_DATA_FILE` = `market_data.bin`
- `HORIZONS` = `(4, 8, 16)`
- `VALIDATION_BIN` = `MLAI_V416_ROBUST_HISTORICAL_EXPERIENCE_RETRIEVAL.bin`
- `VALIDATION_REPORT` = `MLAI_V416_ROBUST_HISTORICAL_EXPERIENCE_RETRIEVAL_REPORT.md`

====================================================================================================
17. RUNTIME FUNCTION AVAILABILITY
====================================================================================================

| Function | Status | Signature |
|---|---|---|
| `similarity_representation` | CALLABLE | `(current: 'MarketState', record: 'ExperienceRecord') -> 'SimilarityRepresentation'` |
| `similarity_score` | CALLABLE | `(current: 'MarketState', record: 'ExperienceRecord') -> 'Dict[str, float]'` |
| `calculate_retrieval_discrimination` | CALLABLE | `(selected_matches: 'Sequence[SimilarityMatch]', all_candidates: 'Sequence[SimilarityMatch]', selected_records: 'Sequence[ExperienceRecord]', candidate_records: 'Sequence[ExperienceRecord]') -> 'RetrievalDiscrimination'` |
| `retrieve_historical_experience` | CALLABLE | `(current: 'MarketState', records: 'Sequence[ExperienceRecord]', horizon: 'int', query_index: 'int') -> 'RetrievalResult'` |
| `null_retrieval_sanity_test` | CALLABLE | `(current: 'MarketState', records: 'Sequence[ExperienceRecord]', query_index: 'int', horizon: 'int') -> 'Dict[str, Any]'` |
| `predictive_decision` | CALLABLE | `(current: 'MarketState', records: 'Sequence[ExperienceRecord]', query_index: 'int') -> 'Dict[str, Any]'` |
| `calculate_incremental_value` | CALLABLE | `(retrieval_evaluation: 'Dict[str, Any]', baseline_evaluation: 'Dict[str, Any]', predictive_evaluation: 'Dict[str, Any]') -> 'Dict[str, Any]'` |
| `horizon_discrimination_summary` | CALLABLE | `(rows: 'Sequence[Dict[str, Any]]') -> 'Dict[str, Any]'` |
| `build_experience_records` | CALLABLE | `(candles: 'Sequence[Candle]', atr: 'Sequence[Optional[float]]', states: 'Sequence[MarketState]', episode_ids: 'Dict[int, int]', start: 'int', train_end: 'int', horizon: 'int') -> 'List[ExperienceRecord]'` |
| `make_outcome` | CALLABLE | `(candles: 'Sequence[Candle]', atr: 'Sequence[Optional[float]]', index: 'int', horizon: 'int') -> 'Optional[Outcome]'` |
| `conditional_baseline` | CALLABLE | `(current: 'MarketState', records: 'Sequence[ExperienceRecord]') -> 'Tuple[str, Dict[str, float], int]'` |
| `evaluate_distribution` | CALLABLE | `(distribution: 'Dict[str, float]', actual: 'str') -> 'Dict[str, Any]'` |
| `main` | CALLABLE | `() -> 'None'` |

====================================================================================================
18. DATA / FILE PROTECTION
====================================================================================================

market_data.bin exists: YES
market_data.bin SHA256 before audit: `dd57bccc3526ebaeb900181096adcbf48a84b5a3a334da1f1990a443cde091b5`
v4.1.6 SHA256 before audit: `3f5b43cf8b44713c988b97cfdcd581e00c258d2367a2df3a3d14ccfb59e90580`
The auditor itself performs no write operation against the source or market data.

====================================================================================================
19. SEVEN REQUIREMENTS — ENGINEERING VS SCIENTIFIC STATUS
====================================================================================================

| Requirement | Implemented | Causal | Measurable | Predictive | Incremental | Robust |
|---|---|---|---|---|---|---|
| Similarity representation | YES | AUDIT | YES | AUDIT | AUDIT | AUDIT |
| Retrieval ranking / discrimination | YES | AUDIT | YES | AUDIT | AUDIT | AUDIT |
| H4 discrimination | YES | AUDIT | YES | AUDIT | AUDIT | AUDIT |
| H8 discrimination | YES | AUDIT | YES | AUDIT | AUDIT | AUDIT |
| H16 discrimination | YES | AUDIT | YES | AUDIT | AUDIT | AUDIT |
| Incremental predictive value | YES | AUDIT | YES | NOT DEMONSTRATED | NOT DEMONSTRATED | AUDIT |
| Predictive decision integration | YES | AUDIT | YES | CURRENTLY WEAK | CURRENTLY NEGATIVE | AUDIT |

====================================================================================================
20. CURRENT V4.1.6 RUNTIME EVIDENCE
====================================================================================================

The following values are recorded from the supplied v4.1.6 run.
| Horizon | Retrieval Acc | Baseline Acc | Retrieval Brier Lift | Predictive Brier Lift | Predictive LogLoss Lift | Discrimination Rate | Similarity Separation | Directional Discrimination |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| H+4 | 43.94% | 44.72% | -0.001900 | -0.016000 | -0.079200 | 100.00% | 0.587500 | 0.035300 |
| H+8 | 47.64% | 50.27% | -0.002300 | -0.022100 | -0.065200 | 100.00% | 0.586300 | 0.040400 |
| H+16 | 46.45% | 48.80% | 0.001200 | -0.018900 | -0.063300 | 100.00% | 0.585200 | 0.050700 |

====================================================================================================
21. ROOT-CAUSE ANALYSIS
====================================================================================================

Based on the supplied execution results plus the static architecture, the following issues require correction rather than cosmetic tuning.

ROOT CAUSE CANDIDATE A — DISCRIMINATION METRIC SEMANTICS
- The reported 100% discrimination rate is not consistent with the modest directional-discrimination values.
- The implementation must be inspected to determine whether the rate measures availability/calculation success instead of true outcome discrimination.

ROOT CAUSE CANDIDATE B — SIMILARITY-TO-OUTCOME LINK
- Similarity separation exists, but the retrieval Brier lift is approximately zero overall.
- Therefore high similarity does not yet demonstrate a strong future-outcome relationship.

ROOT CAUSE CANDIDATE C — PREDICTIVE INTEGRATION
- Predictive Brier lift is negative at all three horizons.
- The predictive layer is therefore not currently adding useful information to the baseline.
- The integration must be conditional on demonstrated retrieval signal rather than assuming retrieval evidence is beneficial.

ROOT CAUSE CANDIDATE D — EVALUATION DEPTH
- Aggregate accuracy/Brier values alone are insufficient to establish robust historical-experience retrieval.
- Similarity-bucket performance, top-k stability, null comparison, and effect-size analysis need to be treated as first-class metrics.

====================================================================================================
22. ACCEPTANCE CRITERIA FOR THE NEXT FIX
====================================================================================================

- Discrimination rate must have an unambiguous scientific definition.
- Technical availability must be separated from predictive discrimination.
- Similarity must remain strictly causal.
- Historical candidates must remain strictly prior to each OOS query.
- Similarity ranking must be evaluated against future outcomes.
- H4, H8 and H16 must be evaluated independently.
- Top-ranked retrieval must be compared against lower-ranked retrieval.
- Retrieval must be compared against the appropriate conditional baseline.
- Observed retrieval performance must be compared against a valid null.
- Predictive integration must not degrade the baseline merely because retrieval exists.
- Incremental value must be measured on identical OOS observations.
- Negative incremental value must remain visible rather than being hidden.
- No tuning may use OOS outcomes.
- market_data.bin must remain read-only.
- v4.1.5 must remain unchanged.

====================================================================================================
23. FINAL AUDIT CLASSIFICATION
====================================================================================================

CURRENT ENGINEERING STATUS: IMPLEMENTED
CURRENT CAUSAL STATUS: REQUIRES VERIFICATION
CURRENT RETRIEVAL SIGNAL STATUS: WEAK / MIXED
CURRENT INCREMENTAL VALUE STATUS: NOT DEMONSTRATED
CURRENT PREDICTIVE INTEGRATION STATUS: NEGATIVE ON AGGREGATE BRIER
CURRENT SCIENTIFIC ROBUSTNESS STATUS: NOT YET ESTABLISHED

IMPORTANT:
This audit intentionally does NOT modify the implementation.
The purpose is to establish the root causes before the next implementation change.

====================================================================================================
24. POST-AUDIT INTEGRITY
====================================================================================================

v4.1.6 SHA256 after audit: `3f5b43cf8b44713c988b97cfdcd581e00c258d2367a2df3a3d14ccfb59e90580`
market_data.bin SHA256 after audit: `dd57bccc3526ebaeb900181096adcbf48a84b5a3a334da1f1990a443cde091b5`
v4.1.6 source integrity: PASS — unchanged
market_data.bin integrity: PASS — unchanged
