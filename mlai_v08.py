from pathlib import Path

path = Path("mlai_v341.py")

text = path.read_text(encoding="utf-8")

start_marker = "# MAIN EXPERIMENT"
end_marker = "# FINAL VERDICT"

start = text.index(start_marker)
end = text.index(end_marker)

new_main = r'''
# ============================================================
# MAIN EXPERIMENT
# MLAI v3.4.1
#
# NESTED WALK-FORWARD ANTI-OVERFITTING EXPERIMENT
#
# IMPORTANT:
# ------------------------------------------------------------
# The OUTER validation data is never used to select rules.
#
# INNER DEVELOPMENT:
#     discover rules
#     rank rules
#     select rules
#
# OUTER VALIDATION:
#     locked rules are tested once on unseen data
#
# This prevents the outer validation set from becoming
# another training/selection set.
# ============================================================

all_results = {}

for horizon in HORIZONS:

    print()
    print("=" * 78)
    print(
        f"HORIZON: {horizon} CANDLES"
    )
    print("=" * 78)

    records = build_records(horizon)

    print(
        "Historical records:",
        len(records)
    )

    if len(records) < FOLDS * MIN_VALIDATION_MATCHES:
        print("Not enough records.")
        continue

    # --------------------------------------------------------
    # OUTER WALK-FORWARD
    #
    # The final chronological portion of each outer fold is
    # completely unseen while rules are selected.
    # --------------------------------------------------------

    fold_size = len(records) // (FOLDS + 1)

    fold_results = []

    aggregated_predictions = []

    for fold in range(FOLDS, 0, -1):

        outer_validation_start = (
            len(records)
            - fold_size * fold
        )

        outer_validation_end = (
            outer_validation_start
            + fold_size
        )

        outer_validation = records[
            outer_validation_start:
            outer_validation_end
        ]

        if not outer_validation:
            continue

        outer_start_index = (
            outer_validation[0]["index"]
        )

        print()
        print("-" * 78)
        print(
            f"OUTER FOLD {fold}"
        )
        print("-" * 78)

        print(
            "Outer validation start index:",
            outer_start_index
        )

        print(
            "Outer validation records:",
            len(outer_validation)
        )

        # ----------------------------------------------------
        # OUTER CALIBRATION
        #
        # Anything whose future label can overlap the outer
        # validation period is removed.
        # ----------------------------------------------------

        outer_calibration, outer_purged = (
            build_purged_calibration(
                records,
                outer_start_index,
                horizon
            )
        )

        print(
            "Outer calibration records:",
            len(outer_calibration)
        )

        print(
            "Outer purged records:",
            len(outer_purged)
        )

        if not outer_calibration:
            print(
                "Skipping fold: no outer calibration data."
            )
            continue

        # ----------------------------------------------------
        # INNER WALK-FORWARD SELECTION
        #
        # Rules are discovered and selected only inside the
        # outer calibration period.
        #
        # The outer validation period is NEVER inspected here.
        # ----------------------------------------------------

        inner_size = (
            len(outer_calibration)
            // 3
        )

        if inner_size < MIN_VALIDATION_MATCHES:
            print(
                "Skipping fold: insufficient inner data."
            )
            continue

        inner_train_end = (
            len(outer_calibration)
            - inner_size
        )

        inner_validation = outer_calibration[
            inner_train_end:
        ]

        inner_train_source = outer_calibration[
            :inner_train_end
        ]

        inner_validation_start_index = (
            inner_validation[0]["index"]
        )

        inner_calibration, inner_purged = (
            build_purged_calibration(
                inner_train_source,
                inner_validation_start_index,
                horizon
            )
        )

        print()
        print(
            "INNER SELECTION"
        )

        print(
            "Inner calibration records:",
            len(inner_calibration)
        )

        print(
            "Inner purged records:",
            len(inner_purged)
        )

        print(
            "Inner validation records:",
            len(inner_validation)
        )

        if len(inner_calibration) < MIN_CALIBRATION_SAMPLES:
            print(
                "Skipping fold: insufficient inner calibration."
            )
            continue

        # ----------------------------------------------------
        # LEAKAGE CHECK
        # ----------------------------------------------------

        leakage_found = False

        for record in inner_calibration:

            if (
                record["index"] + horizon
                >= inner_validation_start_index
            ):
                leakage_found = True
                break

        if leakage_found:

            raise RuntimeError(
                "CRITICAL: inner calibration contains "
                "future-label overlap."
            )

        print(
            "PASS: Inner calibration future-label overlap = NONE"
        )

        # ----------------------------------------------------
        # INNER QUANTILE MODEL
        # ----------------------------------------------------

        inner_quantile_model = (
            fit_quantile_model(
                inner_calibration
            )
        )

        inner_calibration_transformed = (
            transform_records(
                inner_calibration,
                inner_quantile_model
            )
        )

        inner_validation_transformed = (
            transform_records(
                inner_validation,
                inner_quantile_model
            )
        )

        # ----------------------------------------------------
        # INNER RULE DISCOVERY
        # ----------------------------------------------------

        inner_rules = discover_rules(
            inner_calibration_transformed
        )

        print(
            "Inner rules discovered:",
            len(inner_rules)
        )

        # ----------------------------------------------------
        # INNER RULE AUDIT
        #
        # Rules are evaluated against INNER validation only.
        # This validation is still inside the development
        # region and therefore does not contaminate the
        # OUTER validation result.
        # ----------------------------------------------------

        inner_rule_validation = (
            audit_rule_validation(
                inner_rules[
                    :MAX_RULES_FOR_VALIDATION
                ],
                inner_validation_transformed
            )
        )

        # ----------------------------------------------------
        # INNER RULE SELECTION
        #
        # A rule must satisfy:
        #
        #   1. minimum validation matches
        #   2. inner validation accuracy above inner baseline
        #
        # Then it is ranked by validation accuracy, matches,
        # and calibration confidence.
        #
        # This selection happens BEFORE outer validation.
        # ----------------------------------------------------

        inner_baseline = baseline_metrics(
            inner_validation
        )

        inner_baseline_accuracy = (
            inner_baseline["accuracy"]
        )

        selected_candidates = []

        for item in inner_rule_validation:

            if (
                item["validation_accuracy"]
                <= inner_baseline_accuracy
            ):
                continue

            selected_candidates.append(
                item
            )

        selected_candidates.sort(
            key=lambda x: (
                x["validation_accuracy"],
                x["validation_matches"],
                x["rule"]["confidence"],
                x["rule"]["score"],
            ),
            reverse=True
        )

        # ----------------------------------------------------
        # LOCKED OUTER RULE SET
        #
        # The selected rules are now frozen.
        # No outer validation information is used.
        # ----------------------------------------------------

        locked_rules = [
            item["rule"]
            for item in selected_candidates[
                :MAX_RULES_FOR_VALIDATION
            ]
        ]

        print(
            "Inner rules passing selection:",
            len(selected_candidates)
        )

        print(
            "LOCKED rules for outer validation:",
            len(locked_rules)
        )

        # ----------------------------------------------------
        # OUTER QUANTILE MODEL
        #
        # This model is fitted only from data available before
        # the outer validation period.
        # ----------------------------------------------------

        outer_quantile_model = (
            fit_quantile_model(
                outer_calibration
            )
        )

        outer_validation_transformed = (
            transform_records(
                outer_validation,
                outer_quantile_model
            )
        )

        # ----------------------------------------------------
        # OUTER VALIDATION
        #
        # LOCKED RULES ONLY.
        #
        # No selection occurs here.
        # ----------------------------------------------------

        predictions = validate_rules(
            locked_rules,
            outer_validation_transformed
        )

        metrics = calculate_metrics(
            predictions,
            outer_validation_transformed
        )

        outer_baseline = baseline_metrics(
            outer_validation
        )

        baseline_accuracy = (
            outer_baseline["accuracy"]
        )

        accuracy_difference = (
            metrics["accuracy"]
            - baseline_accuracy
        )

        print()
        print(
            "LOCKED OUTER VALIDATION RESULT"
        )

        print(
            "Outer validation records:",
            len(outer_validation)
        )

        print(
            "Locked rules:",
            len(locked_rules)
        )

        print(
            "Outer validation predictions:",
            metrics["predictions"]
        )

        print(
            f"Outer directional accuracy: "
            f"{metrics['accuracy']:.2%}"
        )

        print(
            f"Outer majority baseline: "
            f"{baseline_accuracy:.2%}"
        )

        print(
            f"Outer accuracy vs baseline: "
            f"{accuracy_difference:+.2%}"
        )

        print(
            f"Outer coverage: "
            f"{metrics['coverage']:.2%}"
        )

        print(
            f"Outer BUY precision: "
            f"{metrics['buy_precision']:.2%}"
        )

        print(
            f"Outer SELL precision: "
            f"{metrics['sell_precision']:.2%}"
        )

        fold_results.append({

            "fold":
                fold,

            "outer_calibration":
                len(outer_calibration),

            "outer_purged":
                len(outer_purged),

            "inner_calibration":
                len(inner_calibration),

            "inner_purged":
                len(inner_purged),

            "inner_validation":
                len(inner_validation),

            "outer_validation":
                len(outer_validation),

            "rules_discovered_inner":
                len(inner_rules),

            "rules_selected_inner":
                len(selected_candidates),

            "locked_rules":
                len(locked_rules),

            "predictions":
                predictions,

            "metrics":
                metrics,

            "inner_rule_validation":
                inner_rule_validation,
        })

        aggregated_predictions.extend(
            predictions
        )

    # ========================================================
    # AGGREGATED OUTER RESULT
    # ========================================================

    print()
    print("=" * 78)
    print(
        "AGGREGATED LOCKED "
        "OUTER OUT-OF-SAMPLE RESULT"
    )
    print("=" * 78)

    if aggregated_predictions:

        total_predictions = len(
            aggregated_predictions
        )

        correct = sum(
            x["prediction"] == x["actual"]
            for x in aggregated_predictions
        )

        accuracy = (
            correct / total_predictions
        )

        buys = [
            x
            for x in aggregated_predictions
            if x["prediction"] == "BUY"
        ]

        sells = [
            x
            for x in aggregated_predictions
            if x["prediction"] == "SELL"
        ]

        buy_precision = (
            sum(
                x["actual"] == "BUY"
                for x in buys
            )
            / len(buys)
            if buys
            else 0.0
        )

        sell_precision = (
            sum(
                x["actual"] == "SELL"
                for x in sells
            )
            / len(sells)
            if sells
            else 0.0
        )

        print(
            "Outer validation predictions:",
            total_predictions
        )

        print(
            "Correct predictions:",
            correct
        )

        print(
            f"Outer directional accuracy: "
            f"{accuracy:.2%}"
        )

        print(
            "BUY predictions:",
            len(buys)
        )

        print(
            "SELL predictions:",
            len(sells)
        )

        print(
            f"BUY precision: "
            f"{buy_precision:.2%}"
        )

        print(
            f"SELL precision: "
            f"{sell_precision:.2%}"
        )

    else:

        print(
            "No locked outer validation predictions."
        )

    # ========================================================
    # FINAL FOLD INFORMATION
    # ========================================================

    all_results[horizon] = {

        "fold_results":
            fold_results,

        "aggregated_predictions":
            aggregated_predictions,
    }


'''

new_text = (
    text[:start]
    + new_main
    + text[end:]
)

path.write_text(
    new_text,
    encoding="utf-8"
)

print("SUCCESS: v3.4.1 main experiment replaced.")