from pathlib import Path
import ast
import hashlib
import py_compile
import shutil
from datetime import datetime


SOURCE = Path("mlai_market_structure_v415.py")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def source_text() -> str:
    return SOURCE.read_text(encoding="utf-8")


def find_function(tree, name):
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == name:
                return node
    return None


def function_source(text, node):
    lines = text.splitlines()
    return "\n".join(lines[node.lineno - 1:node.end_lineno])


print("=" * 100)
print("MLAI v4.1.5 — DIRECT PREDICTIVE INTEGRATION FIX")
print("=" * 100)
print()
print("This patch:")
print("  1. Does NOT create a new MLAI version")
print("  2. Does NOT modify market_data.bin")
print("  3. Backs up the current source")
print("  4. Verifies the repaired prediction API")
print("  5. Verifies whether the real main() evaluation path calls it")
print("  6. If not, integrates the repaired prediction into the actual evaluation loop")
print("  7. Syntax-checks the result")
print()

if not SOURCE.exists():
    raise SystemExit(f"SOURCE NOT FOUND: {SOURCE.resolve()}")

before_hash = sha256(SOURCE)

print("SOURCE:")
print(SOURCE.resolve())
print()
print("SHA256 BEFORE:")
print(before_hash)
print()

text = source_text()
tree = ast.parse(text)

repaired_fn = find_function(tree, "mlai_v415_repaired_prediction")
evidence_fn = find_function(tree, "_mlai_fix_class_evidence")
decision_fn = find_function(tree, "_mlai_fix_predict_from_evidence")
main_fn = find_function(tree, "main")

if repaired_fn is None:
    raise RuntimeError(
        "mlai_v415_repaired_prediction() is missing. "
        "Do not patch blindly."
    )

if evidence_fn is None:
    raise RuntimeError(
        "_mlai_fix_class_evidence() is missing. "
        "The repaired predictive layer is incomplete."
    )

if decision_fn is None:
    raise RuntimeError(
        "_mlai_fix_predict_from_evidence() is missing. "
        "The repaired predictive layer is incomplete."
    )

if main_fn is None:
    raise RuntimeError("main() was not found.")

print("REPAIRED API:")
print("  mlai_v415_repaired_prediction : FOUND")
print("  _mlai_fix_class_evidence      : FOUND")
print("  _mlai_fix_predict_from_evidence: FOUND")
print("  main                           : FOUND")
print()

# ---------------------------------------------------------------------
# Check actual source references
# ---------------------------------------------------------------------

calls = []

for node in ast.walk(tree):
    if isinstance(node, ast.Call):
        fn = node.func

        if isinstance(fn, ast.Name):
            calls.append(fn.id)
        elif isinstance(fn, ast.Attribute):
            calls.append(fn.attr)

repaired_call_count = calls.count("mlai_v415_repaired_prediction")

print("CURRENT INTEGRATION:")
print(f"  Calls to mlai_v415_repaired_prediction(): {repaired_call_count}")
print()

if repaired_call_count > 0:
    print("REPAIRED PREDICTIVE PATH IS ALREADY REFERENCED.")
    print("No integration patch will be applied.")
else:
    print("REPAIRED PREDICTIVE PATH IS NOT REFERENCED.")
    print("THIS IS THE ACTUAL INTEGRATION BUG.")
    print()

# ---------------------------------------------------------------------
# Locate the actual evaluation loop.
#
# We deliberately patch only the section containing:
#
#   retrieval = retrieve_historical_experience(...)
#   outcome = make_outcome(...)
#
# because that is the actual chronological evaluation point.
# ---------------------------------------------------------------------

if repaired_call_count == 0:

    marker = """                retrieval = retrieve_historical_experience(
                    query_state,
                    records,
                    horizon,
                    query_index,
                )
"""

    if marker not in text:
        raise RuntimeError(
            "Could not find the exact chronological retrieval call. "
            "Source layout differs from the inspected implementation. "
            "NO PATCH WAS APPLIED."
        )

    integration = """                retrieval = retrieve_historical_experience(
                    query_state,
                    records,
                    horizon,
                    query_index,
                )

                # ---------------------------------------------------------
                # REPAIRED PREDICTIVE DECISION PATH
                #
                # The historical retrieval object remains available for
                # diagnostics, but the actual directional decision now
                # comes from the repaired evidence layer.
                #
                # This is deliberately evaluated using only:
                #   - query_state
                #   - training records
                #   - horizon
                #   - query_index
                #
                # No OOS outcome is supplied to the predictor.
                # ---------------------------------------------------------

                repaired_prediction = mlai_v415_repaired_prediction(
                    current=query_state,
                    records=records,
                    horizon=horizon,
                    query_index=query_index,
                )
"""

    text = text.replace(marker, integration, 1)

    # -----------------------------------------------------------------
    # Add repaired prediction evaluation immediately after outcome.
    # -----------------------------------------------------------------

    marker2 = """                outcome = make_outcome(
                    candles,
                    atr,
                    query_index,
                    horizon,
                )
                if outcome is None:
                    continue

"""

    if marker2 not in text:
        raise RuntimeError(
            "Could not find the exact outcome construction block. "
            "NO PATCH WAS APPLIED."
        )

    replacement2 = """                outcome = make_outcome(
                    candles,
                    atr,
                    query_index,
                    horizon,
                )
                if outcome is None:
                    continue

                # ---------------------------------------------------------
                # REPAIRED PREDICTION EVALUATION
                #
                # This is the first point where the repaired predictive
                # layer is connected to an actual out-of-sample evaluation.
                #
                # The outcome is used ONLY AFTER prediction has been
                # generated, so it cannot leak into the prediction.
                # ---------------------------------------------------------

                repaired_prediction_value = repaired_prediction["prediction"]
                repaired_probabilities = repaired_prediction["probabilities"]

                repaired_eval = evaluate_distribution(
                    repaired_probabilities,
                    outcome.direction,
                )

"""

    text = text.replace(marker2, replacement2, 1)

    # -----------------------------------------------------------------
    # Add repaired results into row.
    # -----------------------------------------------------------------

    marker3 = """                row = {
                    "query_index": query_index,
                    "actual": outcome.direction,
"""

    replacement3 = """                row = {
                    "query_index": query_index,
                    "actual": outcome.direction,

                    # -----------------------------------------------------
                    # REPAIRED PREDICTIVE RESULT
                    # -----------------------------------------------------
                    "repaired_prediction": repaired_prediction_value,
                    "repaired_probabilities": repaired_probabilities,
                    "repaired_margin": repaired_prediction["margin"],
                    "repaired_best_probability": repaired_prediction[
                        "best_probability"
                    ],
                    "repaired_evaluation": repaired_eval,
"""

    if marker3 not in text:
        raise RuntimeError(
            "Could not find evaluation row construction. "
            "NO PATCH WAS APPLIED."
        )

    text = text.replace(marker3, replacement3, 1)

    # -----------------------------------------------------------------
    # Add repaired metrics next to retrieval accuracy.
    # -----------------------------------------------------------------

    marker4 = """            retrieval_accuracy = (
                mean_or_zero(
"""

    if marker4 not in text:
        raise RuntimeError(
            "Could not locate retrieval accuracy calculation. "
            "NO PATCH WAS APPLIED."
        )

    repaired_metrics = """            repaired_accuracy = (
                mean_or_zero(
                    [
                        1.0
                        if row["repaired_evaluation"]["correct"]
                        else 0.0
                        for row in evaluations
                    ]
                )
                if evaluations
                else None
            )

            repaired_brier = (
                mean_or_zero(
                    [
                        row["repaired_evaluation"]["brier"]
                        for row in evaluations
                    ]
                )
                if evaluations
                else None
            )

            repaired_log_loss = (
                mean_or_zero(
                    [
                        row["repaired_evaluation"]["log_loss"]
                        for row in evaluations
                    ]
                )
                if evaluations
                else None
            )

"""

    text = text.replace(marker4, repaired_metrics + marker4, 1)

    # -----------------------------------------------------------------
    # Add metrics into result dictionary.
    # -----------------------------------------------------------------

    marker5 = """            result = {
                "training_records": len(records),
                "oos_queries": len(evaluations),
"""

    replacement5 = """            result = {
                "training_records": len(records),
                "oos_queries": len(evaluations),

                # Repaired predictive layer
                "repaired_accuracy": repaired_accuracy,
                "repaired_brier": repaired_brier,
                "repaired_log_loss": repaired_log_loss,
"""

    if marker5 not in text:
        raise RuntimeError(
            "Could not locate result dictionary. "
            "NO PATCH WAS APPLIED."
        )

    text = text.replace(marker5, replacement5, 1)

    # -----------------------------------------------------------------
    # Print actual repaired metrics.
    # -----------------------------------------------------------------

    marker6 = """            print(
                f"Retrieval Accuracy={fmt_pct(retrieval_accuracy)} | "
                f"Baseline={fmt_pct(baseline_accuracy)}"
            )
"""

    replacement6 = """            print(
                f"Retrieval Accuracy={fmt_pct(retrieval_accuracy)} | "
                f"Baseline={fmt_pct(baseline_accuracy)}"
            )

            print(
                f"REPAIRED Accuracy={fmt_pct(repaired_accuracy)} | "
                f"REPAIRED Brier={fmt_num(repaired_brier)} | "
                f"REPAIRED LogLoss={fmt_num(repaired_log_loss)}"
            )
"""

    if marker6 not in text:
        raise RuntimeError(
            "Could not locate retrieval metric print block. "
            "NO PATCH WAS APPLIED."
        )

    text = text.replace(marker6, replacement6, 1)

    # -----------------------------------------------------------------
    # Save backup
    # -----------------------------------------------------------------

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    backup = SOURCE.with_name(
        f"mlai_market_structure_v415_BACKUP_BEFORE_DIRECT_INTEGRATION_{timestamp}.py"
    )

    shutil.copy2(SOURCE, backup)

    print("BACKUP CREATED:")
    print(backup.resolve())
    print()

    SOURCE.write_text(text, encoding="utf-8")

    print("DIRECT INTEGRATION PATCH: APPLIED")
    print()

# ---------------------------------------------------------------------
# Syntax validation
# ---------------------------------------------------------------------

print("=" * 100)
print("POST-PATCH VALIDATION")
print("=" * 100)

try:
    py_compile.compile(
        str(SOURCE),
        doraise=True,
    )
    print("SYNTAX: PASS")
except Exception:
    print("SYNTAX: FAIL")
    raise

after_text = source_text()
after_tree = ast.parse(after_text)

after_calls = []

for node in ast.walk(after_tree):
    if isinstance(node, ast.Call):
        fn = node.func

        if isinstance(fn, ast.Name):
            after_calls.append(fn.id)
        elif isinstance(fn, ast.Attribute):
            after_calls.append(fn.attr)

after_repaired_calls = after_calls.count(
    "mlai_v415_repaired_prediction"
)

print(
    "Calls to mlai_v415_repaired_prediction():",
    after_repaired_calls,
)

if after_repaired_calls == 0:
    raise RuntimeError(
        "PATCH VALIDATION FAILED: repaired predictor is still not called."
    )

print("REPAIRED PREDICTIVE API INTEGRATION: PASS")

# ---------------------------------------------------------------------
# Import test
# ---------------------------------------------------------------------

print()
print("=" * 100)
print("IMPORT TEST")
print("=" * 100)

import importlib.util

spec = importlib.util.spec_from_file_location(
    "mlai_market_structure_v415_repaired",
    SOURCE,
)

module = importlib.util.module_from_spec(spec)

if spec.loader is None:
    raise RuntimeError("Unable to create module loader.")

spec.loader.exec_module(module)

print("IMPORT: PASS")

required = [
    "mlai_v415_repaired_prediction",
    "_mlai_fix_class_evidence",
    "_mlai_fix_predict_from_evidence",
]

for name in required:
    if not hasattr(module, name):
        raise RuntimeError(
            f"Required repaired function missing after import: {name}"
        )
    print(f"{name}: PASS")

# ---------------------------------------------------------------------
# Final hash
# ---------------------------------------------------------------------

after_hash = sha256(SOURCE)

print()
print("=" * 100)
print("FINAL RESULT")
print("=" * 100)

print()
print("SOURCE SHA256 BEFORE:")
print(before_hash)

print()
print("SOURCE SHA256 AFTER:")
print(after_hash)

print()
print("RESULT:")
print("  Repaired predictive layer : PRESENT")
print("  Actual evaluation path   : INTEGRATED")
print("  Syntax                    : PASS")
print("  Import                    : PASS")
print("  New MLAI version          : NO")
print("  market_data.bin           : NOT MODIFIED")
print()

print("=" * 100)
print("DIRECT PREDICTIVE INTEGRATION FIX COMPLETE")
print("=" * 100)

print()
print("IMPORTANT:")
print("The next step is NOT another investigation.")
print()
print("Run the actual v4.1.5 forensic/validation test.")
print("Its output must now contain REPAIRED Accuracy/Brier/LogLoss")
print("from the repaired predictive path.")
print()
print("If the repaired metrics still fail, THEN we fix the predictive")
print("logic itself. We will not create another version.")