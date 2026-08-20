from pathlib import Path


path = Path("mlai_v342.py")

text = path.read_text(encoding="utf-8")


marker = "# ============================================================\n# RULE DISCOVERY\n# ============================================================"


diagnostics = r'''
# ============================================================
# MLAI v3.4.2 DIAGNOSTIC FUNCTIONS
# ============================================================

def outcome_distribution(records):
    """
    Count BUY / SELL / NEUTRAL outcomes.
    """

    counts = Counter(
        record["outcome"]
        for record in records
    )

    total = len(records)

    return {
        "BUY": counts.get("BUY", 0),
        "SELL": counts.get("SELL", 0),
        "NEUTRAL": counts.get("NEUTRAL", 0),
        "total": total,
    }


def print_outcome_distribution(
    title,
    records
):

    distribution = outcome_distribution(
        records
    )

    total = distribution["total"]

    print()
    print("-" * 78)
    print(title)
    print("-" * 78)

    print(
        "Total:",
        total
    )

    if total == 0:
        print("BUY     : 0")
        print("SELL    : 0")
        print("NEUTRAL : 0")
        return distribution

    print(
        f"BUY     : "
        f"{distribution['BUY']} "
        f"({distribution['BUY'] / total:.2%})"
    )

    print(
        f"SELL    : "
        f"{distribution['SELL']} "
        f"({distribution['SELL'] / total:.2%})"
    )

    print(
        f"NEUTRAL : "
        f"{distribution['NEUTRAL']} "
        f"({distribution['NEUTRAL'] / total:.2%})"
    )

    return distribution


def rule_length_distribution(
    rules
):

    counts = Counter(
        rule.get(
            "rule_length",
            0
        )
        for rule in rules
    )

    return counts


def print_rule_search_diagnostics(
    title,
    discovered_rules,
    selected_candidates,
    locked_rules
):

    discovered_lengths = (
        rule_length_distribution(
            discovered_rules
        )
    )

    selected_lengths = (
        rule_length_distribution(
            selected_candidates
        )
    )

    locked_lengths = (
        rule_length_distribution(
            locked_rules
        )
    )

    print()
    print("-" * 78)
    print(title)
    print("-" * 78)

    print(
        "Rules discovered:",
        len(discovered_rules)
    )

    print(
        "Rules passing inner validation:",
        len(selected_candidates)
    )

    print(
        "Rules locked for outer validation:",
        len(locked_rules)
    )

    print(
        "Discovered 1-feature rules:",
        discovered_lengths.get(1, 0)
    )

    print(
        "Discovered 2-feature rules:",
        discovered_lengths.get(2, 0)
    )

    print(
        "Selected 1-feature rules:",
        selected_lengths.get(1, 0)
    )

    print(
        "Selected 2-feature rules:",
        selected_lengths.get(2, 0)
    )

    print(
        "Locked 1-feature rules:",
        locked_lengths.get(1, 0)
    )

    print(
        "Locked 2-feature rules:",
        locked_lengths.get(2, 0)
    )


def calculate_rule_validation_summary(
    validation_results
):

    if not validation_results:
        return {
            "rules": 0,
            "average_accuracy": 0.0,
            "best_accuracy": 0.0,
            "average_matches": 0.0,
        }

    accuracies = [
        item["validation_accuracy"]
        for item in validation_results
    ]

    matches = [
        item["validation_matches"]
        for item in validation_results
    ]

    return {
        "rules":
            len(validation_results),

        "average_accuracy":
            sum(accuracies)
            / len(accuracies),

        "best_accuracy":
            max(accuracies),

        "average_matches":
            sum(matches)
            / len(matches),
    }


def print_validation_selection_diagnostics(
    title,
    validation_results,
    baseline_accuracy
):

    summary = (
        calculate_rule_validation_summary(
            validation_results
        )
    )

    print()
    print("-" * 78)
    print(title)
    print("-" * 78)

    print(
        "Rules individually validated:",
        summary["rules"]
    )

    print(
        f"Average rule validation accuracy: "
        f"{summary['average_accuracy']:.2%}"
    )

    print(
        f"Best rule validation accuracy: "
        f"{summary['best_accuracy']:.2%}"
    )

    print(
        f"Average validation matches: "
        f"{summary['average_matches']:.2f}"
    )

    print(
        f"Validation baseline: "
        f"{baseline_accuracy:.2%}"
    )

    above_baseline = sum(
        item["validation_accuracy"]
        > baseline_accuracy
        for item in validation_results
    )

    print(
        "Rules above validation baseline:",
        above_baseline
    )

    if validation_results:

        print(
            f"Selection rate above baseline: "
            f"{above_baseline / len(validation_results):.2%}"
        )


def shuffled_calibration_records(
    records,
    rng
):
    """
    Preserve feature/index structure while randomly
    permuting only the calibration outcome labels.

    This is a null-model diagnostic.

    Features remain unchanged.
    Time/index structure remains unchanged.
    Only labels are shuffled.
    """

    shuffled = [
        dict(record)
        for record in records
    ]

    outcomes = [
        record["outcome"]
        for record in shuffled
    ]

    rng.shuffle(
        outcomes
    )

    for record, outcome in zip(
        shuffled,
        outcomes
    ):

        record["outcome"] = outcome

    return shuffled


def run_permutation_null_test(
    calibration_records,
    validation_records,
    quantile_model,
    permutations=25,
    seed=341
):
    """
    Diagnostic null test.

    Randomizes calibration labels while preserving
    all feature values.

    Rules are discovered from randomized labels.

    Those rules are then evaluated against the untouched
    validation labels.

    This is NOT a production model test.

    It measures whether the rule-search process can
    generate apparently strong validation candidates
    even when the calibration labels contain no
    genuine feature/outcome relationship.
    """

    rng = random.Random(
        seed
    )

    validation_transformed = (
        transform_records(
            validation_records,
            quantile_model
        )
    )

    baseline = baseline_metrics(
        validation_records
    )

    baseline_accuracy = (
        baseline["accuracy"]
    )

    best_accuracies = []
    candidate_counts = []
    above_baseline_counts = []

    for iteration in range(
        permutations
    ):

        shuffled = (
            shuffled_calibration_records(
                calibration_records,
                rng
            )
        )

        shuffled_quantile_model = (
            fit_quantile_model(
                shuffled
            )
        )

        shuffled_transformed = (
            transform_records(
                shuffled,
                shuffled_quantile_model
            )
        )

        rules = discover_rules(
            shuffled_transformed
        )

        validation_results = (
            audit_rule_validation(
                rules[
                    :MAX_RULES_FOR_VALIDATION
                ],
                validation_transformed
            )
        )

        if validation_results:

            best_accuracy = max(
                item["validation_accuracy"]
                for item in validation_results
            )

            above_baseline = sum(
                item["validation_accuracy"]
                > baseline_accuracy
                for item in validation_results
            )

        else:

            best_accuracy = 0.0
            above_baseline = 0

        best_accuracies.append(
            best_accuracy
        )

        candidate_counts.append(
            len(rules)
        )

        above_baseline_counts.append(
            above_baseline
        )

    if not best_accuracies:

        return {
            "permutations": 0,
            "baseline_accuracy":
                baseline_accuracy,
            "mean_best_accuracy":
                0.0,
            "max_best_accuracy":
                0.0,
            "mean_rule_count":
                0.0,
            "mean_above_baseline":
                0.0,
        }

    return {
        "permutations":
            permutations,

        "baseline_accuracy":
            baseline_accuracy,

        "mean_best_accuracy":
            sum(best_accuracies)
            / len(best_accuracies),

        "max_best_accuracy":
            max(best_accuracies),

        "mean_rule_count":
            sum(candidate_counts)
            / len(candidate_counts),

        "mean_above_baseline":
            sum(above_baseline_counts)
            / len(above_baseline_counts),
    }


def print_permutation_null_result(
    result
):

    print()
    print("=" * 78)
    print(
        "PERMUTATION / NULL TEST"
    )
    print("=" * 78)

    print(
        "Permutations:",
        result["permutations"]
    )

    print(
        f"Real validation baseline: "
        f"{result['baseline_accuracy']:.2%}"
    )

    print(
        f"Mean best null-rule accuracy: "
        f"{result['mean_best_accuracy']:.2%}"
    )

    print(
        f"Maximum best null-rule accuracy: "
        f"{result['max_best_accuracy']:.2%}"
    )

    print(
        f"Mean rules discovered under null: "
        f"{result['mean_rule_count']:.2f}"
    )

    print(
        f"Mean null rules above baseline: "
        f"{result['mean_above_baseline']:.2f}"
    )

    print()
    print(
        "INTERPRETATION:"
    )

    print(
        "If randomized labels regularly produce "
        "apparently strong validation rules, the "
        "rule-search process has substantial "
        "selection-overfitting risk."
    )


'''


if marker not in text:
    raise RuntimeError(
        "ERROR: RULE DISCOVERY marker not found."
    )


if "MLAI v3.4.2 DIAGNOSTIC FUNCTIONS" in text:
    raise RuntimeError(
        "ERROR: v3.4.2 diagnostics already exist."
    )


text = (
    text.replace(
        marker,
        diagnostics + "\n" + marker,
        1
    )
)


text = text.replace(
    "MLAI v3.4.1 FINAL VERDICT",
    "MLAI v3.4.2 FINAL VERDICT"
)


text = text.replace(
    "MLAI v3.4.0 COMPLETE",
    "MLAI v3.4.2 COMPLETE"
)


path.write_text(
    text,
    encoding="utf-8"
)


print(
    "SUCCESS: v3.4.2 diagnostic functions added."
)