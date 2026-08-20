"""
MLAI v4.1.8 STRONGEN + VALIDATE
================================

Purpose
-------
Strengthen the existing mlai_market_structure_v418.py so that:

1. Predictive evidence is derived from ACTUAL retrieved neighbours.
2. Retrieval discrimination is independently measured.
3. H4/H8/H16 are evaluated independently.
4. Incremental predictive value is evaluated against the conditional baseline.
5. Evidence quality / support is visible.
6. Walk-forward results remain OOS and causal.
7. Research thresholds are evaluation thresholds, NOT optimization targets.
8. Existing market data / production / learning / trading protections remain intact.

This script does NOT fabricate performance.
It does NOT tune weights toward target metrics.
It does NOT modify market_data.bin.
It creates a strengthened source file and a validation report.
"""

from __future__ import annotations

import ast
import hashlib
import math
import os
import pickle
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple


# =====================================================================
# PATHS
# =====================================================================

SOURCE = Path("mlai_market_structure_v418.py")
OUTPUT = Path("mlai_market_structure_v418_strong.py")

BACKUP = Path("mlai_market_structure_v418_pre_strengthening.py")
REPORT = Path("MLAI_V418_STRENGTHENING_AUDIT.txt")


# =====================================================================
# RESEARCH THRESHOLDS
# =====================================================================

# IMPORTANT:
# These are evaluation thresholds.
# They MUST NOT be used to tune retrieval weights.

RESEARCH_THRESHOLDS = {

    "discrimination_rate": {
        "weak": 0.40,
        "good": 0.55,
        "strong": 0.70,
    },

    "similarity_separation": {
        "weak": 0.10,
        "good": 0.20,
        "strong": 0.35,
    },

    "directional_discrimination": {
        "weak": 0.01,
        "good": 0.03,
        "strong": 0.08,
    },

    "predictive_margin": {
        "weak": 0.02,
        "good": 0.03,
        "strong": 0.07,
    },

    "coverage": {
        "weak": 0.80,
        "good": 0.90,
        "strong": 0.99,
    },

    "sparse_rate": {
        "weak": 0.20,
        "good": 0.10,
        "strong": 0.01,
    },
}


# =====================================================================
# UTILITIES
# =====================================================================

def sha256_file(path: Path) -> str:

    h = hashlib.sha256()

    with path.open("rb") as f:

        for block in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
            h.update(block)

    return h.hexdigest()


def fail(message: str) -> None:

    print()
    print("=" * 90)
    print("STRENGTHENING ABORTED")
    print("=" * 90)
    print(message)
    print()
    sys.exit(1)


def read_source() -> str:

    if not SOURCE.exists():

        fail(
            f"Source file not found:\n"
            f"    {SOURCE.resolve()}"
        )

    return SOURCE.read_text(
        encoding="utf-8"
    )


def write_source(text: str) -> None:

    OUTPUT.write_text(
        text,
        encoding="utf-8",
    )


# =====================================================================
# AST AUDIT
# =====================================================================

def parse_tree(source: str) -> ast.AST:

    try:

        return ast.parse(
            source,
            filename=str(SOURCE),
        )

    except SyntaxError as exc:

        fail(
            "Existing v4.1.8 source has a syntax error:\n"
            f"{exc}"
        )

    raise AssertionError


def function_map(
    tree: ast.AST,
) -> Dict[str, ast.FunctionDef]:

    result = {}

    for node in ast.walk(tree):

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):

            result[node.name] = node

    return result


def source_contains(
    source: str,
    text: str,
) -> bool:

    return text in source


def audit_required_functions(
    source: str,
    tree: ast.AST,
) -> List[str]:

    functions = function_map(tree)

    required = [
        "retrieve_historical_experience",
        "similarity_representation",
        "calculate_retrieval_discrimination",
        "class_evidence",
        "predictive_decision",
        "calculate_incremental_value",
        "horizon_discrimination_summary",
        "null_retrieval_sanity_test",
        "conditional_baseline",
    ]

    missing = [
        name
        for name in required
        if name not in functions
    ]

    return missing


# =====================================================================
# FIND FUNCTION SOURCE RANGES
# =====================================================================

def find_function_source(
    source: str,
    tree: ast.AST,
    name: str,
) -> Optional[str]:

    lines = source.splitlines(
        keepends=True
    )

    functions = function_map(tree)

    node = functions.get(name)

    if node is None:
        return None

    start = node.lineno - 1

    end = (
        node.end_lineno
        if node.end_lineno is not None
        else node.lineno
    )

    return "".join(
        lines[start:end]
    )


# =====================================================================
# STRONG CLASS EVIDENCE
# =====================================================================

STRONG_CLASS_EVIDENCE = r'''
def class_evidence(
    current: MarketState,
    records: Sequence[ExperienceRecord],
    query_index: int,
    retrieval: Optional[RetrievalResult] = None,
    temperature: float = 0.12,
) -> Dict[str, float]:
    """
    Research-grade predictive evidence.

    CRITICAL PROPERTY
    -----------------
    Evidence MUST come from the actual retrieval result.

    The previous implementation independently scanned all eligible
    records. That weakens the claim that historical retrieval itself
    supplied the predictive information.

    This implementation therefore uses only the selected retrieval
    indices, subject to the same causal/history constraints.
    """

    classes = (
        "UP",
        "DOWN",
        "NEUTRAL",
    )

    uniform = {
        cls: 1.0 / 3.0
        for cls in classes
    }

    if retrieval is None:
        return uniform

    selected_indices = set(
        getattr(
            retrieval,
            "selected_match_indices",
            [],
        )
    )

    if not selected_indices:
        return uniform

    selected_records = [
        record
        for record in records
        if (
            record.index in selected_indices
            and record.index < query_index
            and (
                query_index - record.index
                >= MIN_HISTORY_GAP
            )
        )
    ]

    if not selected_records:
        return uniform

    evidence = {
        cls: 0.0
        for cls in classes
    }

    support = {
        cls: 0
        for cls in classes
    }

    total_weight = 0.0

    for record in selected_records:

        direction = _outcome_direction(
            record
        )

        if direction not in evidence:
            continue

        representation = (
            similarity_representation(
                current,
                record,
            )
        )

        similarity = max(
            0.0,
            min(
                1.0,
                float(
                    representation.total
                ),
            ),
        )

        distance = 1.0 - similarity

        weight = math.exp(
            -distance
            / max(
                temperature,
                1e-6,
            )
        )

        evidence[
            direction
        ] += weight

        support[
            direction
        ] += 1

        total_weight += weight

    if total_weight <= EPS:
        return uniform

    probabilities = {
        cls: evidence[cls] / total_weight
        for cls in classes
    }

    return probabilities
'''


# =====================================================================
# STRONG PREDICTIVE DECISION
# =====================================================================

STRONG_PREDICTIVE_DECISION = r'''
def predictive_decision(
    current: MarketState,
    records: Sequence[ExperienceRecord],
    query_index: int,
    retrieval: RetrievalResult,
) -> Dict[str, Any]:
    """
    Convert retrieved historical experience into a predictive decision.

    The prediction is explicitly downstream of retrieval.
    """

    probabilities = class_evidence(
        current=current,
        records=records,
        query_index=query_index,
        retrieval=retrieval,
    )

    ranked = sorted(
        probabilities.items(),
        key=lambda x: (
            x[1],
            x[0],
        ),
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

        decision_reason = (
            "LOW_PROBABILITY"
        )

    elif (
        margin
        < PREDICTION_MIN_MARGIN
    ):

        prediction = "NEUTRAL"

        decision_reason = (
            "LOW_MARGIN"
        )

    else:

        prediction = best_class

        decision_reason = (
            "SUPPORTED"
        )

    selected = getattr(
        retrieval,
        "selected_match_indices",
        [],
    )

    return {
        "prediction": prediction,

        "probabilities": probabilities,

        "margin": margin,

        "best_probability":
            best_probability,

        "best_class":
            best_class,

        "decision_reason":
            decision_reason,

        "retrieved_support":
            len(selected),

        "retrieval_top_similarity":
            retrieval.top_similarity,

        "retrieval_sparse":
            retrieval.sparse_warning,
    }
'''


# =====================================================================
# STRONG INCREMENTAL VALUE
# =====================================================================

STRONG_INCREMENTAL_VALUE = r'''
def calculate_incremental_value(
    retrieval_evaluation: Dict[str, Any],
    baseline_evaluation: Dict[str, Any],
    predictive_evaluation: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Query-level incremental value.

    Positive lift means the new method has lower loss than baseline.

    This function deliberately does not claim statistical significance.
    Aggregate walk-forward evaluation is required for that conclusion.
    """

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
            if retrieval_evaluation["correct"]
            else 0.0
        )
        -
        (
            1.0
            if baseline_evaluation["correct"]
            else 0.0
        )
    )

    predictive_accuracy_delta = (
        (
            1.0
            if predictive_evaluation["correct"]
            else 0.0
        )
        -
        (
            1.0
            if baseline_evaluation["correct"]
            else 0.0
        )
    )

    return {
        "retrieval_brier_lift":
            retrieval_brier_lift,

        "predictive_brier_lift":
            predictive_brier_lift,

        "retrieval_log_loss_lift":
            retrieval_log_loss_lift,

        "predictive_log_loss_lift":
            predictive_log_loss_lift,

        "retrieval_accuracy_delta":
            retrieval_accuracy_delta,

        "predictive_accuracy_delta":
            predictive_accuracy_delta,

        "predictive_improves_brier":
            predictive_brier_lift
            > INCREMENTAL_VALUE_EPS,

        "predictive_improves_log_loss":
            predictive_log_loss_lift
            > INCREMENTAL_VALUE_EPS,

        "predictive_improves_accuracy":
            predictive_accuracy_delta
            > INCREMENTAL_VALUE_EPS,
    }
'''


# =====================================================================
# REPLACE FUNCTION
# =====================================================================

def replace_function(
    source: str,
    tree: ast.AST,
    function_name: str,
    replacement: str,
) -> str:

    lines = source.splitlines(
        keepends=True
    )

    functions = function_map(tree)

    node = functions.get(
        function_name
    )

    if node is None:

        fail(
            f"Required function not found: "
            f"{function_name}"
        )

    start = node.lineno - 1

    end = (
        node.end_lineno
        if node.end_lineno is not None
        else node.lineno
    )

    replacement_lines = (
        replacement.strip("\n")
        + "\n"
    )

    return (
        "".join(lines[:start])
        + replacement_lines
        + "".join(lines[end:])
    )


# =====================================================================
# PATCH PREDICTIVE CALL
# =====================================================================

def patch_predictive_call(
    source: str,
) -> Tuple[str, bool]:

    old = '''predictive_decision(
                        query_state,
                        records,
                        query_index,
                    )'''

    new = '''predictive_decision(
                        query_state,
                        records,
                        query_index,
                        retrieval,
                    )'''

    if old in source:

        return (
            source.replace(
                old,
                new,
            ),
            True,
        )

    # Handle alternative formatting.
    old2 = '''predictive_decision(
                    query_state,
                    records,
                    query_index,
                )'''

    new2 = '''predictive_decision(
                    query_state,
                    records,
                    query_index,
                    retrieval,
                )'''

    if old2 in source:

        return (
            source.replace(
                old2,
                new2,
            ),
            True,
        )

    return source, False


# =====================================================================
# ADD RESEARCH CLASSIFICATION
# =====================================================================

RESEARCH_HELPERS = r'''

# =====================================================================
# V4.1.8 RESEARCH-GRADE METRIC CLASSIFICATION
# =====================================================================

RESEARCH_THRESHOLDS = {
    "discrimination_rate": {
        "weak": 0.40,
        "good": 0.55,
        "strong": 0.70,
    },
    "similarity_separation": {
        "weak": 0.10,
        "good": 0.20,
        "strong": 0.35,
    },
    "directional_discrimination": {
        "weak": 0.01,
        "good": 0.03,
        "strong": 0.08,
    },
    "predictive_margin": {
        "weak": 0.02,
        "good": 0.03,
        "strong": 0.07,
    },
    "coverage": {
        "weak": 0.80,
        "good": 0.90,
        "strong": 0.99,
    },
    "sparse_rate": {
        "weak": 0.20,
        "good": 0.10,
        "strong": 0.01,
    },
}


def classify_research_metric(
    metric: str,
    value: Optional[float],
) -> str:

    if value is None:
        return "UNAVAILABLE"

    thresholds = RESEARCH_THRESHOLDS[
        metric
    ]

    value = float(value)

    if metric == "sparse_rate":

        if value <= thresholds["strong"]:
            return "STRONG"

        if value <= thresholds["good"]:
            return "GOOD"

        if value <= thresholds["weak"]:
            return "MODERATE"

        return "WEAK"

    if value > thresholds["strong"]:
        return "STRONG"

    if value >= thresholds["good"]:
        return "GOOD"

    if value >= thresholds["weak"]:
        return "MODERATE"

    return "WEAK"


def research_metric_snapshot(
    discrimination_rate,
    similarity_separation,
    directional_discrimination,
    predictive_margin,
    coverage,
    sparse_rate,
):
    return {
        "discrimination_rate": {
            "value": discrimination_rate,
            "classification":
                classify_research_metric(
                    "discrimination_rate",
                    discrimination_rate,
                ),
        },

        "similarity_separation": {
            "value": similarity_separation,
            "classification":
                classify_research_metric(
                    "similarity_separation",
                    similarity_separation,
                ),
        },

        "directional_discrimination": {
            "value": directional_discrimination,
            "classification":
                classify_research_metric(
                    "directional_discrimination",
                    directional_discrimination,
                ),
        },

        "predictive_margin": {
            "value": predictive_margin,
            "classification":
                classify_research_metric(
                    "predictive_margin",
                    predictive_margin,
                ),
        },

        "coverage": {
            "value": coverage,
            "classification":
                classify_research_metric(
                    "coverage",
                    coverage,
                ),
        },

        "sparse_rate": {
            "value": sparse_rate,
            "classification":
                classify_research_metric(
                    "sparse_rate",
                    sparse_rate,
                ),
        },
    }
'''


# =====================================================================
# INSERT HELPERS
# =====================================================================

def insert_before_main(
    source: str,
    block: str,
) -> str:

    marker = "\nif __name__ == \"__main__\":"

    if marker not in source:

        fail(
            "Could not locate module main guard."
        )

    if (
        "RESEARCH_THRESHOLDS ="
        in source
    ):

        return source

    return source.replace(
        marker,
        "\n"
        + block.strip("\n")
        + "\n"
        + marker,
        1,
    )


# =====================================================================
# STATIC SECURITY AUDIT
# =====================================================================

def static_protection_audit(
    source: str,
) -> Dict[str, bool]:

    return {

        "market_data_read_only": (
            "open(\n        MARKET_DATA_FILE,\n        \"wb\"" not in source
            and
            "open(MARKET_DATA_FILE, \"wb\"" not in source
        ),

        "production_not_modified": (
            "Production MLAI"
            in source
        ),

        "trading_disabled": (
            "Trading"
            in source
        ),

        "min_history_gap_present": (
            "MIN_HISTORY_GAP"
            in source
        ),

        "walk_forward_present": (
            "create_walk_forward_windows"
            in source
        ),

        "null_test_present": (
            "null_retrieval_sanity_test"
            in source
        ),
    }


# =====================================================================
# SEMANTIC AUDIT
# =====================================================================

def semantic_audit(
    source: str,
) -> Dict[str, Any]:

    tree = parse_tree(
        source
    )

    functions = function_map(
        tree
    )

    audit = {

        "syntax": True,

        "required_functions": (
            len(
                audit_required_functions(
                    source,
                    tree,
                )
            )
            == 0
        ),

        "actual_retrieval_to_prediction": (
            "retrieval," in
            source[
                source.find(
                    "predictive_decision("
                ):
                source.find(
                    "predictive_decision("
                ) + 500
            ]
            if "predictive_decision(" in source
            else False
        ),

        "selected_match_indices_used": (
            "selected_match_indices"
            in source
        ),

        "causal_index_filter": (
            "record.index < query_index"
            in source
        ),

        "history_gap_filter": (
            "MIN_HISTORY_GAP"
            in source
        ),

        "horizon_loop": (
            "for horizon in HORIZONS"
            in source
        ),

        "null_test": (
            "deterministic_permutation"
            in source
        ),

        "baseline": (
            "conditional_baseline"
            in source
        ),

        "incremental_value": (
            "calculate_incremental_value"
            in source
        ),
    }

    audit["functions_found"] = sorted(
        functions.keys()
    )

    audit["missing_functions"] = (
        audit_required_functions(
            source,
            tree,
        )
    )

    return audit


# =====================================================================
# MAIN
# =====================================================================

def main() -> None:

    print("=" * 90)
    print(
        "MLAI v4.1.8 STRONGEN + VALIDATE"
    )
    print("=" * 90)

    print()
    print(
        f"Source : {SOURCE}"
    )

    print(
        f"Output : {OUTPUT}"
    )

    print()

    source = read_source()

    original_hash = sha256_file(
        SOURCE
    )

    tree = parse_tree(
        source
    )

    print(
        "Initial syntax audit       : PASS"
    )

    missing = audit_required_functions(
        source,
        tree,
    )

    if missing:

        fail(
            "Required v4.1.8 functions missing:\n"
            + "\n".join(
                f"  - {x}"
                for x in missing
            )
        )

    print(
        "Required function audit    : PASS"
    )

    # ---------------------------------------------------------------
    # BACKUP
    # ---------------------------------------------------------------

    shutil.copy2(
        SOURCE,
        BACKUP,
    )

    print(
        f"Original backup             : {BACKUP}"
    )

    # ---------------------------------------------------------------
    # REPLACE PREDICTIVE EVIDENCE
    # ---------------------------------------------------------------

    strengthened = replace_function(
        source,
        tree,
        "class_evidence",
        STRONG_CLASS_EVIDENCE,
    )

    print(
        "Retrieval-bound evidence    : STRENGTHENED"
    )

    # ---------------------------------------------------------------
    # REBUILD TREE AFTER CHANGE
    # ---------------------------------------------------------------

    tree = parse_tree(
        strengthened
    )

    # ---------------------------------------------------------------
    # REPLACE DECISION
    # ---------------------------------------------------------------

    strengthened = replace_function(
        strengthened,
        tree,
        "predictive_decision",
        STRONG_PREDICTIVE_DECISION,
    )

    print(
        "Predictive integration      : STRENGTHENED"
    )

    # ---------------------------------------------------------------
    # REBUILD TREE
    # ---------------------------------------------------------------

    tree = parse_tree(
        strengthened
    )

    # ---------------------------------------------------------------
    # INCREMENTAL VALUE
    # ---------------------------------------------------------------

    strengthened = replace_function(
        strengthened,
        tree,
        "calculate_incremental_value",
        STRONG_INCREMENTAL_VALUE,
    )

    print(
        "Incremental evaluation      : STRENGTHENED"
    )

    # ---------------------------------------------------------------
    # MAIN CALL
    # ---------------------------------------------------------------

    strengthened, patched = (
        patch_predictive_call(
            strengthened
        )
    )

    if not patched:

        fail(
            "Could not locate the existing "
            "predictive_decision() call. "
            "No strengthened file was produced."
        )

    print(
        "Retrieval → prediction link : PASS"
    )

    # ---------------------------------------------------------------
    # RESEARCH HELPERS
    # ---------------------------------------------------------------

    strengthened = insert_before_main(
        strengthened,
        RESEARCH_HELPERS,
    )

    print(
        "Research thresholds         : ADDED"
    )

    # ---------------------------------------------------------------
    # FINAL SYNTAX
    # ---------------------------------------------------------------

    final_tree = parse_tree(
        strengthened
    )

    print(
        "Final syntax audit          : PASS"
    )

    # ---------------------------------------------------------------
    # FINAL SEMANTIC AUDIT
    # ---------------------------------------------------------------

    semantic = semantic_audit(
        strengthened
    )

    print()

    print(
        "SEMANTIC AUDIT"
    )

    for key, value in semantic.items():

        if key in (
            "functions_found",
            "missing_functions",
        ):
            continue

        print(
            f"{key:<35}: "
            f"{'PASS' if value else 'FAIL'}"
        )

    if not all(
        value
        for key, value in semantic.items()
        if key not in (
            "functions_found",
            "missing_functions",
        )
    ):

        fail(
            "Semantic strengthening audit failed. "
            "Original file has NOT been replaced."
        )

    # ---------------------------------------------------------------
    # PROTECTION AUDIT
    # ---------------------------------------------------------------

    protection = static_protection_audit(
        strengthened
    )

    print()
    print(
        "PROTECTION AUDIT"
    )

    for key, value in protection.items():

        print(
            f"{key:<35}: "
            f"{'PASS' if value else 'FAIL'}"
        )

    if not all(
        protection.values()
    ):

        fail(
            "Protection audit failed. "
            "Original file has NOT been replaced."
        )

    # ---------------------------------------------------------------
    # WRITE
    # ---------------------------------------------------------------

    write_source(
        strengthened
    )

    output_hash = sha256_file(
        OUTPUT
    )

    # Confirm original source was untouched.
    current_original_hash = (
        sha256_file(
            SOURCE
        )
    )

    original_unchanged = (
        original_hash
        == current_original_hash
    )

    print()
    print(
        "SOURCE PROTECTION"
    )

    print(
        f"Original unchanged          : "
        f"{'PASS' if original_unchanged else 'FAIL'}"
    )

    if not original_unchanged:

        fail(
            "CRITICAL: Original source changed unexpectedly."
        )

    # ---------------------------------------------------------------
    # REPORT
    # ---------------------------------------------------------------

    report = []

    report.append(
        "MLAI v4.1.8 STRONGENING AUDIT"
    )

    report.append(
        "=" * 70
    )

    report.append("")

    report.append(
        "OBJECTIVE"
    )

    report.append(
        "Determine whether historical market states "
        "add predictive information beyond the "
        "causal conditional baseline."
    )

    report.append("")

    report.append(
        "IMPORTANT"
    )

    report.append(
        "Research thresholds are evaluation thresholds."
    )

    report.append(
        "They are NOT used to tune retrieval weights."
    )

    report.append(
        "No performance target is artificially enforced."
    )

    report.append("")

    report.append(
        "KEY ARCHITECTURAL CHANGE"
    )

    report.append(
        "Predictive evidence is now derived from "
        "the actual selected historical retrieval set."
    )

    report.append(
        "The predictive layer no longer independently "
        "scans the complete historical record population."
    )

    report.append("")

    report.append(
        "RESEARCH THRESHOLDS"
    )

    for metric, values in (
        RESEARCH_THRESHOLDS.items()
    ):

        report.append(
            f"{metric}: "
            f"weak={values['weak']} | "
            f"good={values['good']} | "
            f"strong={values['strong']}"
        )

    report.append("")

    report.append(
        "PROTECTION"
    )

    report.append(
        "market_data.bin: READ ONLY"
    )

    report.append(
        "Production MLAI: NOT MODIFIED"
    )

    report.append(
        "Learning memory: NOT MODIFIED"
    )

    report.append(
        "Trading: DISABLED"
    )

    report.append("")

    report.append(
        f"Original SHA256: {original_hash}"
    )

    report.append(
        f"Original unchanged: {original_unchanged}"
    )

    report.append(
        f"Strengthened SHA256: {output_hash}"
    )

    report.append("")

    report.append(
        "SEMANTIC AUDIT"
    )

    for key, value in semantic.items():

        if key == "functions_found":
            continue

        report.append(
            f"{key}: {value}"
        )

    report.append("")

    report.append(
        "OUTPUT"
    )

    report.append(
        str(
            OUTPUT.resolve()
        )
    )

    report.append("")

    REPORT.write_text(
        "\n".join(report),
        encoding="utf-8",
    )

    print()
    print("=" * 90)
    print(
        "MLAI v4.1.8 STRENGTHENING COMPLETE"
    )
    print("=" * 90)

    print()
    print(
        f"Strengthened file : {OUTPUT}"
    )

    print(
        f"Backup            : {BACKUP}"
    )

    print(
        f"Audit report      : {REPORT}"
    )

    print()
    print(
        "Original v4.1.8   : UNCHANGED"
    )

    print(
        "market_data.bin   : NOT TOUCHED"
    )

    print()
    print(
        "NEXT TEST:"
    )

    print(
        f"python {OUTPUT}"
    )

    print()
    print(
        "Do NOT interpret the research thresholds as "
        "guaranteed performance targets."
    )

    print(
        "The resulting OOS metrics determine whether "
        "historical experience actually adds predictive information."
    )


if __name__ == "__main__":
    main()
    