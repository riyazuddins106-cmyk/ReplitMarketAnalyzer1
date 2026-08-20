from __future__ import annotations

import ast
import hashlib
import shutil
import subprocess
import sys
from pathlib import Path
from datetime import datetime


ROOT = Path(__file__).resolve().parent

SOURCE = ROOT / "mlai_market_structure_v415.py"
AUDIT = ROOT / "audit_mlai_v415_full_forensic.py"

BACKUP = ROOT / (
    "mlai_market_structure_v415_BACKUP_BEFORE_PREDICTIVE_FIX_"
    + datetime.now().strftime("%Y%m%d_%H%M%S")
    + ".py"
)

MARKER = "# MLAI_V415_PREDICTIVE_FIX_V1"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def fail(msg: str):
    print()
    print("=" * 100)
    print("FIX ABORTED")
    print("=" * 100)
    print(msg)
    print()
    sys.exit(1)


def find_function(tree, name: str):
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == name:
                return node
    return None


def find_class(tree, name: str):
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            if node.name == name:
                return node
    return None


print("=" * 100)
print("MLAI v4.1.5 — ONE-SHOT PREDICTIVE-LAYER FIX + TEST")
print("=" * 100)
print()
print("This operation:")
print("  * preserves market_data.bin")
print("  * creates a source backup")
print("  * patches only the predictive retrieval/decision layer")
print("  * syntax-checks the patched source")
print("  * imports the patched module")
print("  * runs the existing full forensic audit")
print()

if not SOURCE.exists():
    fail(f"Missing source file:\n{SOURCE}")

if not AUDIT.exists():
    fail(f"Missing audit file:\n{AUDIT}")

original_hash = sha256(SOURCE)

print("SOURCE:")
print(SOURCE)
print()
print("SOURCE SHA256 BEFORE:")
print(original_hash)
print()

# ---------------------------------------------------------------------
# SAFETY CHECKS
# ---------------------------------------------------------------------

source_text = SOURCE.read_text(encoding="utf-8")

if MARKER in source_text:
    fail(
        "This predictive fix is already present in the source.\n"
        "I will not apply it twice."
    )

try:
    tree = ast.parse(source_text, filename=str(SOURCE))
except SyntaxError as e:
    fail(f"Existing source is already syntactically invalid:\n{e}")

required_functions = [
    "load_market_data",
    "calculate_atr",
    "build_path_vector",
    "build_market_states",
    "assign_episode_ids",
    "build_experience_records",
    "make_outcome",
    "similarity_score",
    "retrieve_historical_experience",
]

missing = [x for x in required_functions if find_function(tree, x) is None]

if missing:
    fail(
        "Expected v4.1.5 functions were not found:\n"
        + "\n".join("  - " + x for x in missing)
    )

if find_class(tree, "CausalStructureEngine") is None:
    fail("CausalStructureEngine was not found.")

print("SOURCE CONTRACT: PASS")
print("Existing v4.1.5 structure detected.")
print()

# ---------------------------------------------------------------------
# BACKUP
# ---------------------------------------------------------------------

shutil.copy2(SOURCE, BACKUP)

print("BACKUP CREATED:")
print(BACKUP)
print()

# ---------------------------------------------------------------------
# PATCH
# ---------------------------------------------------------------------
#
# Strategy:
#
# The existing v4.1.5 retrieval system is retained.
#
# We add a causal evidence layer that:
#
# 1. does NOT inspect future candles;
# 2. uses only historical ExperienceRecord outcomes;
# 3. normalizes evidence by class;
# 4. prevents UP/DOWN/NEUTRAL collapse caused by raw vote counts;
# 5. uses similarity-weighted evidence;
# 6. penalizes tiny effective sample support;
# 7. produces probability-like class evidence;
# 8. allows neutral to compete instead of being structurally ignored.
#
# This is intentionally implemented as a separate helper layer so that
# the underlying causal structure/retrieval machinery remains intact.
# ---------------------------------------------------------------------

PATCH = r'''
# MLAI_V415_PREDICTIVE_FIX_V1
#
# Purpose:
#   Repair the predictive decision layer without changing the causal
#   structure engine or market data.
#
# Design constraints:
#   - historical outcomes only
#   - no future feature access
#   - chronological walk-forward compatible
#   - class-balanced evidence
#   - similarity-weighted evidence
#   - neutral class preserved
#   - deterministic
#
# IMPORTANT:
#   This helper layer does not alter market_data.bin.

from collections import defaultdict
import math


def _mlai_fix_safe_float(value, default=0.0):
    try:
        x = float(value)
        if math.isfinite(x):
            return x
    except Exception:
        pass
    return float(default)


def _mlai_fix_outcome_direction(record):
    """
    Extract the direction from an ExperienceRecord/Outcome object
    without assuming one exact internal representation.
    """
    outcome = getattr(record, "outcome", record)

    value = getattr(outcome, "direction", None)

    if value is None:
        value = getattr(outcome, "label", None)

    if value is None:
        value = getattr(outcome, "class_name", None)

    if value is None:
        value = getattr(outcome, "target", None)

    if value is None:
        value = getattr(outcome, "prediction", None)

    if value is None:
        return None

    value = str(value).upper().strip()

    if value in ("UP", "DOWN", "NEUTRAL"):
        return value

    return None


def _mlai_fix_similarity_total(similarity):
    """
    Existing similarity_score() returns component scores.

    We deliberately avoid trusting an existing 'total' blindly.
    The repaired layer uses the component evidence when available.
    """
    if not isinstance(similarity, dict):
        return 0.0

    components = (
        "candle",
        "location",
        "momentum",
        "path",
        "regime",
        "sequence",
        "structure",
        "volatility",
    )

    values = []

    for key in components:
        if key in similarity:
            value = _mlai_fix_safe_float(similarity[key], 0.0)
            value = max(0.0, min(1.0, value))
            values.append(value)

    if values:
        return sum(values) / len(values)

    return max(
        0.0,
        min(1.0, _mlai_fix_safe_float(similarity.get("total"), 0.0))
    )


def _mlai_fix_class_evidence(
    current,
    records,
    horizon,
    query_index,
    *,
    temperature=0.12,
    min_similarity=0.0,
):
    """
    Causal class-evidence estimator.

    Every record must already belong to the historical training/calibration
    set supplied by the caller.

    No record with an index >= query_index is allowed.

    Evidence is similarity-weighted but class-balanced so that a large
    historical class does not automatically dominate the result.

    The class prior is therefore not allowed to become the prediction.
    """

    buckets = {
        "UP": [],
        "DOWN": [],
        "NEUTRAL": [],
    }

    for record in records:
        record_index = getattr(record, "index", None)

        if record_index is None:
            record_index = getattr(record, "query_index", None)

        if record_index is not None:
            try:
                if int(record_index) >= int(query_index):
                    continue
            except Exception:
                continue

        direction = _mlai_fix_outcome_direction(record)

        if direction not in buckets:
            continue

        try:
            similarity = similarity_score(current, record)
        except Exception:
            continue

        score = _mlai_fix_similarity_total(similarity)

        if score < min_similarity:
            continue

        # Soft kernel.
        #
        # High similarity receives more weight, but we do not allow one
        # single historical record to dominate the entire prediction.
        distance = max(0.0, 1.0 - score)

        weight = math.exp(-distance / max(temperature, 1e-6))

        buckets[direction].append(weight)

    # No evidence.
    if not any(buckets.values()):
        return {
            "UP": 1.0 / 3.0,
            "DOWN": 1.0 / 3.0,
            "NEUTRAL": 1.0 / 3.0,
        }

    # -----------------------------------------------------------------
    # Class-balanced evidence
    # -----------------------------------------------------------------
    #
    # Raw vote totals are dangerous:
    #
    #   if UP has 200 records and DOWN has 100,
    #   raw similarity sums naturally favor UP.
    #
    # We normalize each class by its own historical support.
    #
    # This makes the model ask:
    #
    #   "How strongly does the retrieved evidence support this class?"
    #
    # rather than:
    #
    #   "Which class has the most records?"
    # -----------------------------------------------------------------

    evidence = {}

    for cls, values in buckets.items():
        if not values:
            evidence[cls] = 0.0
            continue

        support = len(values)

        # Mean evidence is intentionally used instead of raw sum.
        mean_weight = sum(values) / support

        # Mild support confidence.
        #
        # This prevents one matching record from receiving the same
        # credibility as a well-supported historical pattern.
        support_factor = 1.0 - math.exp(-support / 8.0)

        evidence[cls] = mean_weight * support_factor

    total = sum(evidence.values())

    if total <= 1e-12:
        return {
            "UP": 1.0 / 3.0,
            "DOWN": 1.0 / 3.0,
            "NEUTRAL": 1.0 / 3.0,
        }

    probabilities = {
        cls: evidence[cls] / total
        for cls in ("UP", "DOWN", "NEUTRAL")
    }

    return probabilities


def _mlai_fix_predict_from_evidence(
    current,
    records,
    horizon,
    query_index,
    *,
    min_probability=0.40,
    min_margin=0.05,
):
    """
    Final repaired decision rule.

    The decision layer no longer blindly follows:
      - raw top-k majority
      - power aggregation
      - the historical class prior

    It requires positive evidence and a minimum separation between the
    best and second-best classes.

    Otherwise it returns NEUTRAL.

    This is deliberately conservative.
    """

    probabilities = _mlai_fix_class_evidence(
        current,
        records,
        horizon,
        query_index,
    )

    ranked = sorted(
        probabilities.items(),
        key=lambda x: x[1],
        reverse=True,
    )

    best_class, best_probability = ranked[0]
    second_probability = ranked[1][1]

    margin = best_probability - second_probability

    # If evidence is ambiguous, do not manufacture a directional signal.
    if best_probability < min_probability:
        prediction = "NEUTRAL"
    elif margin < min_margin:
        prediction = "NEUTRAL"
    else:
        prediction = best_class

    return {
        "prediction": prediction,
        "probabilities": probabilities,
        "margin": margin,
        "best_probability": best_probability,
    }


def mlai_v415_repaired_prediction(
    current,
    records,
    horizon,
    query_index,
):
    """
    Public repaired predictive layer.

    Existing v4.1.5 retrieval remains available.

    Use this function for the repaired decision path.
    """

    return _mlai_fix_predict_from_evidence(
        current=current,
        records=records,
        horizon=horizon,
        query_index=query_index,
    )


# MLAI_V415_PREDICTIVE_FIX_V1_END
'''

# Append only after successful source-contract checks.
patched_text = source_text.rstrip() + "\n\n" + PATCH + "\n"

try:
    ast.parse(patched_text, filename=str(SOURCE))
except SyntaxError as e:
    shutil.copy2(BACKUP, SOURCE)
    fail(
        "Generated patch failed syntax validation.\n"
        "Original source has been restored.\n"
        f"\n{e}"
    )

SOURCE.write_text(patched_text, encoding="utf-8")

print("PATCH APPLIED.")
print("Predictive repair layer added.")
print()

# ---------------------------------------------------------------------
# VERIFY SOURCE
# ---------------------------------------------------------------------

try:
    ast.parse(
        SOURCE.read_text(encoding="utf-8"),
        filename=str(SOURCE),
    )
except SyntaxError as e:
    shutil.copy2(BACKUP, SOURCE)
    fail(
        "Patched source failed final syntax validation.\n"
        "Original source restored.\n"
        f"\n{e}"
    )

patched_hash = sha256(SOURCE)

print("SOURCE SHA256 AFTER:")
print(patched_hash)
print()

if patched_hash == original_hash:
    fail("Patch did not change the source.")

# ---------------------------------------------------------------------
# IMPORT TEST
# ---------------------------------------------------------------------

print("=" * 100)
print("IMPORT TEST")
print("=" * 100)

module_name = SOURCE.stem

try:
    import importlib

    # Remove a previously cached module if one exists.
    sys.modules.pop(module_name, None)

    module = importlib.import_module(module_name)

    required_new_functions = [
        "_mlai_fix_class_evidence",
        "_mlai_fix_predict_from_evidence",
        "mlai_v415_repaired_prediction",
    ]

    for name in required_new_functions:
        if not hasattr(module, name):
            raise RuntimeError(
                f"Patched function missing after import: {name}"
            )

    print("IMPORT: PASS")
    print("REPAIRED PREDICTIVE API: PASS")

except Exception as e:
    shutil.copy2(BACKUP, SOURCE)
    fail(
        "Patched module could not be imported.\n"
        "Original source restored.\n"
        f"\n{type(e).__name__}: {e}"
    )

print()

# ---------------------------------------------------------------------
# RUN EXISTING FULL FORENSIC AUDIT
# ---------------------------------------------------------------------

print("=" * 100)
print("RUNNING FULL FORENSIC AUDIT")
print("=" * 100)
print()

result = subprocess.run(
    [sys.executable, str(AUDIT)],
    cwd=str(ROOT),
)

print()
print("=" * 100)
print("PATCH + TEST COMPLETE")
print("=" * 100)

print()
print("SOURCE BACKUP:")
print(BACKUP)

print()
print("SOURCE SHA256 BEFORE:")
print(original_hash)

print()
print("SOURCE SHA256 AFTER:")
print(patched_hash)

print()
print("AUDIT EXIT CODE:")
print(result.returncode)

print()

if result.returncode != 0:
    print("AUDIT PROCESS FAILED.")
    print()
    print("The source was NOT automatically reverted because the audit")
    print("may have produced useful diagnostic information.")
    print()
    print("Backup available at:")
    print(BACKUP)
else:
    print("AUDIT PROCESS: PASS")
    print()
    print("IMPORTANT:")
    print("The audit result itself determines whether the predictive")
    print("repair is actually successful.")
    print()
    print("Do NOT assume success merely because the script exited 0.")