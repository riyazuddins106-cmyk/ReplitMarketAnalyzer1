"""
MLAI v4.1.6 — INDEPENDENT SEVEN-CAPABILITY AUDIT

Purpose
-------
Independently audit the seven V4.1.6 capabilities without trusting
the model's own "ENABLED" status claims.

The audit distinguishes:

    IMPLEMENTED
    RUNTIME VERIFIED
    EMPIRICALLY VERIFIED
    INCONCLUSIVE
    FAILED

Capabilities audited individually:

1. Similarity representation
2. Retrieval ranking / discrimination
3. H4 discrimination
4. H8 discrimination
5. H16 discrimination
6. Incremental predictive value
7. Predictive decision integration

This program is READ-ONLY with respect to:
    - market_data.bin
    - production MLAI
    - learning memory
    - trading

It does NOT modify mlai_market_structure_v416.py.

It reads:
    mlai_market_structure_v416.py
    MLAI_V416_ROBUST_HISTORICAL_EXPERIENCE_RETRIEVAL.bin
    MLAI_V416_ROBUST_HISTORICAL_EXPERIENCE_RETRIEVAL_REPORT.md

It creates:
    MLAI_V416_SEVEN_CAPABILITY_AUDIT.md
"""


from __future__ import annotations

import ast
import hashlib
import json
import math
import pickle
import re
import statistics
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


# ============================================================================
# CONFIGURATION
# ============================================================================

SOURCE_FILE = Path("mlai_market_structure_v416.py")

VALIDATION_BIN = Path(
    "MLAI_V416_ROBUST_HISTORICAL_EXPERIENCE_RETRIEVAL.bin"
)

VALIDATION_REPORT = Path(
    "MLAI_V416_ROBUST_HISTORICAL_EXPERIENCE_RETRIEVAL_REPORT.md"
)

OUTPUT_REPORT = Path(
    "MLAI_V416_SEVEN_CAPABILITY_AUDIT.md"
)

HORIZONS = (4, 8, 16)


# ============================================================================
# GENERAL HELPERS
# ============================================================================

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        while True:
            block = f.read(1024 * 1024)
            if not block:
                break
            h.update(block)

    return h.hexdigest()


def finite_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def pct(value: Any) -> str:
    if not finite_number(value):
        return "N/A"

    return f"{float(value) * 100.0:.2f}%"


def num(value: Any) -> str:
    if not finite_number(value):
        return "N/A"

    return f"{float(value):.6f}"


def safe_mean(values: Iterable[float]) -> Optional[float]:
    vals = [
        float(v)
        for v in values
        if finite_number(v)
    ]

    if not vals:
        return None

    return statistics.mean(vals)


def flatten_dict(
    obj: Any,
    prefix: str = "",
    max_depth: int = 8,
) -> Dict[str, Any]:
    """
    Flatten dictionaries enough for structural inspection.
    """

    result = {}

    if max_depth < 0:
        return result

    if isinstance(obj, dict):
        for key, value in obj.items():
            key_text = str(key)

            child_prefix = (
                f"{prefix}.{key_text}"
                if prefix
                else key_text
            )

            result[child_prefix] = value

            result.update(
                flatten_dict(
                    value,
                    child_prefix,
                    max_depth - 1,
                )
            )

    elif isinstance(obj, (list, tuple)):
        for index, value in enumerate(obj[:20]):
            child_prefix = (
                f"{prefix}[{index}]"
                if prefix
                else f"[{index}]"
            )

            result[child_prefix] = value

            result.update(
                flatten_dict(
                    value,
                    child_prefix,
                    max_depth - 1,
                )
            )

    return result


def recursive_find_dicts(
    obj: Any,
    predicate,
    path: str = "root",
    max_depth: int = 8,
) -> List[Tuple[str, dict]]:

    found = []

    if max_depth < 0:
        return found

    if isinstance(obj, dict):

        try:
            if predicate(obj):
                found.append((path, obj))
        except Exception:
            pass

        for key, value in obj.items():
            found.extend(
                recursive_find_dicts(
                    value,
                    predicate,
                    f"{path}.{key}",
                    max_depth - 1,
                )
            )

    elif isinstance(obj, (list, tuple)):

        for index, value in enumerate(obj[:5000]):
            found.extend(
                recursive_find_dicts(
                    value,
                    predicate,
                    f"{path}[{index}]",
                    max_depth - 1,
                )
            )

    return found


def key_contains(
    obj: Any,
    names: Iterable[str],
) -> bool:

    if not isinstance(obj, dict):
        return False

    lowered = {
        str(k).lower()
        for k in obj.keys()
    }

    for name in names:
        name = name.lower()

        if any(
            name in key
            for key in lowered
        ):
            return True

    return False


def collect_key_paths(
    obj: Any,
    names: Iterable[str],
) -> List[str]:

    names = [
        n.lower()
        for n in names
    ]

    flat = flatten_dict(obj)

    paths = []

    for path in flat:

        low = path.lower()

        if any(
            name in low
            for name in names
        ):
            paths.append(path)

    return paths


def source_contains(
    source: str,
    patterns: Iterable[str],
) -> List[str]:

    found = []

    for pattern in patterns:

        if pattern.lower() in source.lower():
            found.append(pattern)

    return found


# ============================================================================
# LOAD FILES
# ============================================================================

audit_lines: List[str] = []


def log(message: str = "") -> None:
    print(message)
    audit_lines.append(message)


log("=" * 100)
log("MLAI v4.1.6 — INDEPENDENT SEVEN-CAPABILITY AUDIT")
log("=" * 100)
log("")


# ============================================================================
# FILE AVAILABILITY
# ============================================================================

log("FILES")
log("-" * 100)

required_files = [
    SOURCE_FILE,
    VALIDATION_BIN,
    VALIDATION_REPORT,
]

all_files_present = True

for path in required_files:

    exists = path.exists()

    if not exists:
        all_files_present = False

    log(
        f"{path.name:<70} : "
        f"{'PRESENT' if exists else 'MISSING'}"
    )

log("")


if not SOURCE_FILE.exists():
    log("FATAL: V4.1.6 source file is missing.")
    OUTPUT_REPORT.write_text(
        "\n".join(audit_lines),
        encoding="utf-8",
    )
    raise SystemExit(1)


# ============================================================================
# SOURCE HASH
# ============================================================================

source_hash_before = sha256_file(SOURCE_FILE)

source_text = SOURCE_FILE.read_text(
    encoding="utf-8",
    errors="replace",
)

log("SOURCE INTEGRITY")
log("-" * 100)
log(f"Source SHA256: {source_hash_before}")
log("")


# ============================================================================
# AST ANALYSIS
# ============================================================================

try:

    tree = ast.parse(
        source_text,
        filename=str(SOURCE_FILE),
    )

    ast_ok = True

except SyntaxError as exc:

    tree = None
    ast_ok = False

    log("SOURCE AST PARSE: FAILED")
    log(str(exc))


if ast_ok:

    functions = []
    classes = []
    constants = []

    for node in ast.walk(tree):

        if isinstance(node, ast.FunctionDef):
            functions.append(node.name)

        elif isinstance(node, ast.AsyncFunctionDef):
            functions.append(node.name)

        elif isinstance(node, ast.ClassDef):
            classes.append(node.name)

        elif isinstance(node, ast.Assign):

            for target in node.targets:

                if isinstance(target, ast.Name):

                    name = target.id

                    if name.isupper():
                        constants.append(name)

    log("SOURCE AST PARSE: PASS")
    log(f"Functions discovered: {len(functions)}")
    log(f"Classes discovered  : {len(classes)}")
    log(f"Constants discovered: {len(constants)}")
    log("")


# ============================================================================
# SOURCE IMPLEMENTATION EVIDENCE
# ============================================================================

log("SOURCE IMPLEMENTATION EVIDENCE")
log("-" * 100)

implementation_patterns = {

    1: [
        "similarity",
        "similarity_score",
        "similarity_vector",
        "representation",
        "feature_vector",
    ],

    2: [
        "ranking",
        "rank",
        "discrimination",
        "separation",
        "retrieval",
        "similarity",
    ],

    3: [
        "horizon",
        "HORIZONS",
        "4",
        "H+4",
    ],

    4: [
        "horizon",
        "HORIZONS",
        "8",
        "H+8",
    ],

    5: [
        "horizon",
        "HORIZONS",
        "16",
        "H+16",
    ],

    6: [
        "incremental",
        "brier",
        "logloss",
        "baseline",
        "predictive",
    ],

    7: [
        "predictive",
        "decision",
        "retrieval",
        "prediction",
    ],
}

implementation_evidence = {}

for capability, patterns in implementation_patterns.items():

    found = source_contains(
        source_text,
        patterns,
    )

    implementation_evidence[capability] = found

    log(
        f"Capability {capability}: "
        f"{len(found)} source indicators found"
    )

    if found:
        log(
            "  "
            + ", ".join(found[:20])
        )

log("")


# ============================================================================
# LOAD VALIDATION ARTIFACT
# ============================================================================

artifact = None

if VALIDATION_BIN.exists():

    try:

        with VALIDATION_BIN.open("rb") as f:
            artifact = pickle.load(f)

        log("VALIDATION ARTIFACT")
        log("-" * 100)
        log("Pickle load: PASS")
        log(
            f"Artifact type: {type(artifact).__name__}"
        )

        if isinstance(artifact, dict):
            log(
                "Top-level keys:"
            )

            for key in artifact.keys():
                log(
                    f"  - {key}"
                )

        log("")

    except Exception as exc:

        log("Pickle load: FAILED")
        log(
            f"{type(exc).__name__}: {exc}"
        )
        log("")


# ============================================================================
# REPORT INSPECTION
# ============================================================================

validation_report_text = ""

if VALIDATION_REPORT.exists():

    validation_report_text = (
        VALIDATION_REPORT.read_text(
            encoding="utf-8",
            errors="replace",
        )
    )

    log("VALIDATION REPORT")
    log("-" * 100)
    log("Report file: PRESENT")
    log(
        f"Report size: "
        f"{len(validation_report_text):,} characters"
    )

    enabled_count = len(
        re.findall(
            r"ENABLED",
            validation_report_text,
            flags=re.IGNORECASE,
        )
    )

    log(
        f"'ENABLED' occurrences: {enabled_count}"
    )

    log(
        "Important: ENABLED labels are NOT treated as proof."
    )

    log("")


# ============================================================================
# FIND AGGREGATE HORIZON RESULTS
# ============================================================================

aggregate = None

if isinstance(artifact, dict):

    candidate = artifact.get("aggregate")

    if isinstance(candidate, dict):
        aggregate = candidate

if aggregate is None and isinstance(artifact, dict):

    # Search recursively for something that looks like:
    # {4: {...}, 8: {...}, 16: {...}}

    candidates = recursive_find_dicts(
        artifact,
        lambda d: all(
            any(
                str(k) == str(h)
                for k in d.keys()
            )
            for h in HORIZONS
        ),
    )

    if candidates:
        aggregate = candidates[0][1]


log("AGGREGATE RESULT DISCOVERY")
log("-" * 100)

if isinstance(aggregate, dict):

    log("Aggregate horizon structure: FOUND")

    for horizon in HORIZONS:

        result = None

        for key in (
            horizon,
            str(horizon),
            f"H+{horizon}",
            f"h{horizon}",
        ):

            if key in aggregate:
                result = aggregate[key]
                break

        if isinstance(result, dict):

            log(
                f"H+{horizon}: FOUND"
            )

            important = [
                "mean_retrieval_accuracy",
                "mean_baseline_accuracy",
                "mean_predictive_accuracy",
                "mean_brier_lift",
                "mean_retrieval_brier",
                "mean_baseline_brier",
                "mean_predictive_brier",
            ]

            for key in important:

                if key in result:

                    log(
                        f"  {key}: "
                        f"{result[key]}"
                    )

        else:

            log(
                f"H+{horizon}: NOT FOUND"
            )

else:

    log("Aggregate horizon structure: NOT FOUND")

log("")


# ============================================================================
# CAPABILITY 1
# ============================================================================

results = {}


def capability_result(
    number: int,
    name: str,
    status: str,
    reason: str,
) -> None:

    results[number] = {
        "name": name,
        "status": status,
        "reason": reason,
    }


log("=" * 100)
log("CAPABILITY 1 — SIMILARITY REPRESENTATION")
log("=" * 100)

similarity_paths = []

if artifact is not None:

    similarity_paths = collect_key_paths(
        artifact,
        [
            "similarity",
            "similarity_score",
            "similarity_vector",
            "representation",
        ],
    )

source_similarity = implementation_evidence[1]

if similarity_paths:

    log("Artifact evidence: FOUND")
    log(
        f"Similarity-related artifact paths: "
        f"{len(similarity_paths)}"
    )

    for path in similarity_paths[:20]:
        log(f"  {path}")

    capability_result(
        1,
        "Similarity representation",
        "RUNTIME VERIFIED",
        "Similarity-related values are present in the validation artifact.",
    )

elif source_similarity:

    capability_result(
        1,
        "Similarity representation",
        "IMPLEMENTED / NOT RUNTIME VERIFIED",
        "Source contains similarity implementation indicators, but the artifact does not expose enough similarity evidence.",
    )

else:

    capability_result(
        1,
        "Similarity representation",
        "FAILED",
        "No reliable similarity implementation evidence found.",
    )

log("")


# ============================================================================
# CAPABILITY 2
# ============================================================================

log("=" * 100)
log("CAPABILITY 2 — RETRIEVAL RANKING / DISCRIMINATION")
log("=" * 100)

discrimination_paths = []

if artifact is not None:

    discrimination_paths = collect_key_paths(
        artifact,
        [
            "discrimination",
            "ranking",
            "ranking_concentration",
            "similarity_separation",
            "directional_discrimination",
        ],
    )

if discrimination_paths:

    log("Discrimination evidence: FOUND")

    for path in discrimination_paths[:30]:
        log(f"  {path}")

    capability_result(
        2,
        "Retrieval ranking/discrimination",
        "RUNTIME VERIFIED",
        "Artifact exposes explicit ranking/discrimination diagnostics.",
    )

elif implementation_evidence[2]:

    capability_result(
        2,
        "Retrieval ranking/discrimination",
        "IMPLEMENTED / NOT RUNTIME VERIFIED",
        "Source contains ranking/discrimination logic, but runtime evidence is insufficient.",
    )

else:

    capability_result(
        2,
        "Retrieval ranking/discrimination",
        "FAILED",
        "No reliable ranking/discrimination evidence found.",
    )

log("")


# ============================================================================
# CAPABILITIES 3, 4, 5 — HORIZON DISCRIMINATION
# ============================================================================

for capability, horizon in (
    (3, 4),
    (4, 8),
    (5, 16),
):

    log("=" * 100)
    log(
        f"CAPABILITY {capability} — H+{horizon} DISCRIMINATION"
    )
    log("=" * 100)

    result = None

    if isinstance(aggregate, dict):

        for key in (
            horizon,
            str(horizon),
            f"H+{horizon}",
            f"h{horizon}",
        ):

            if key in aggregate:
                result = aggregate[key]
                break

    if not isinstance(result, dict):

        capability_result(
            capability,
            f"H+{horizon} discrimination",
            "NOT VERIFIED",
            "No horizon-specific aggregate result was found.",
        )

        log("Horizon result: NOT FOUND")
        log("")

        continue

    discrimination = result.get(
        "discrimination"
    )

    if not isinstance(discrimination, dict):

        capability_result(
            capability,
            f"H+{horizon} discrimination",
            "NOT VERIFIED",
            "Horizon result exists but explicit discrimination diagnostics were not found.",
        )

        log(
            "Discrimination substructure: NOT FOUND"
        )
        log("")

        continue

    log("Horizon discrimination diagnostics:")

    for key, value in discrimination.items():

        log(
            f"  {key}: {value}"
        )

    separation = discrimination.get(
        "mean_similarity_separation"
    )

    discrimination_rate = discrimination.get(
        "discrimination_rate"
    )

    if (
        finite_number(separation)
        and finite_number(discrimination_rate)
    ):

        capability_result(
            capability,
            f"H+{horizon} discrimination",
            "RUNTIME VERIFIED",
            (
                f"H+{horizon} has explicit "
                "similarity separation and "
                "discrimination-rate diagnostics."
            ),
        )

    else:

        capability_result(
            capability,
            f"H+{horizon} discrimination",
            "NOT VERIFIED",
            (
                f"H+{horizon} exists but does not expose "
                "sufficient quantitative discrimination evidence."
            ),
        )

    log("")


# ============================================================================
# CAPABILITY 6 — INCREMENTAL PREDICTIVE VALUE
# ============================================================================

log("=" * 100)
log("CAPABILITY 6 — INCREMENTAL PREDICTIVE VALUE")
log("=" * 100)

incremental_evidence = []

if artifact is not None:

    incremental_evidence = collect_key_paths(
        artifact,
        [
            "incremental_brier",
            "brier_lift",
            "incremental_log_loss",
            "logloss_lift",
            "incremental_accuracy",
            "accuracy_delta",
        ],
    )

for path in incremental_evidence[:40]:
    log(f"  {path}")

positive_brier = []
positive_logloss = []
accuracy_deltas = []

for horizon in HORIZONS:

    result = None

    if isinstance(aggregate, dict):

        for key in (
            horizon,
            str(horizon),
            f"H+{horizon}",
            f"h{horizon}",
        ):

            if key in aggregate:
                result = aggregate[key]
                break

    if not isinstance(result, dict):
        continue

    for key in (
        "mean_brier_lift",
        "incremental_brier_lift",
    ):

        if finite_number(result.get(key)):
            positive_brier.append(
                float(result[key])
            )
            break

    for key in (
        "mean_log_loss_lift",
        "incremental_log_loss_lift",
    ):

        if finite_number(result.get(key)):
            positive_logloss.append(
                float(result[key])
            )
            break

    for key in (
        "incremental_accuracy_delta",
        "mean_incremental_accuracy_delta",
    ):

        if finite_number(result.get(key)):
            accuracy_deltas.append(
                float(result[key])
            )
            break


log("")
log(
    f"Brier lift observations: {positive_brier}"
)
log(
    f"Log-loss lift observations: {positive_logloss}"
)
log(
    f"Accuracy deltas: {accuracy_deltas}"
)


if positive_brier:

    brier_positive_count = sum(
        x > 0
        for x in positive_brier
    )

    log(
        f"Positive Brier lifts: "
        f"{brier_positive_count}/{len(positive_brier)}"
    )

else:

    brier_positive_count = 0


if positive_logloss:

    logloss_positive_count = sum(
        x > 0
        for x in positive_logloss
    )

    log(
        f"Positive LogLoss lifts: "
        f"{logloss_positive_count}/{len(positive_logloss)}"
    )

else:

    logloss_positive_count = 0


if (
    positive_brier
    and positive_logloss
):

    if (
        brier_positive_count == len(positive_brier)
        and logloss_positive_count == len(positive_logloss)
    ):

        capability_result(
            6,
            "Incremental predictive value",
            "EMPIRICALLY VERIFIED",
            "All available horizon-level Brier and log-loss lifts are positive.",
        )

    elif (
        brier_positive_count == 0
        and logloss_positive_count == 0
    ):

        capability_result(
            6,
            "Incremental predictive value",
            "FAILED",
            "All available horizon-level Brier and log-loss lifts are non-positive.",
        )

    else:

        capability_result(
            6,
            "Incremental predictive value",
            "INCONCLUSIVE / MIXED",
            "Some predictive metrics improve while others do not.",
        )

else:

    capability_result(
        6,
        "Incremental predictive value",
        "NOT VERIFIED",
        "Insufficient incremental predictive metrics were exposed.",
    )

log("")


# ============================================================================
# CAPABILITY 7 — PREDICTIVE DECISION INTEGRATION
# ============================================================================

log("=" * 100)
log("CAPABILITY 7 — PREDICTIVE DECISION INTEGRATION")
log("=" * 100)

decision_paths = []

if artifact is not None:

    decision_paths = collect_key_paths(
        artifact,
        [
            "predictive",
            "prediction",
            "decision",
            "retrieval",
            "probability",
            "margin",
        ],
    )

log(
    f"Decision-related artifact paths: "
    f"{len(decision_paths)}"
)

for path in decision_paths[:50]:
    log(f"  {path}")


predictive_accuracy_paths = collect_key_paths(
    artifact,
    [
        "predictive_accuracy",
        "mean_predictive_accuracy",
    ],
) if artifact is not None else []


if (
    decision_paths
    and predictive_accuracy_paths
    and implementation_evidence[7]
):

    capability_result(
        7,
        "Predictive decision integration",
        "RUNTIME VERIFIED",
        (
            "Retrieval/prediction/decision evidence exists in the "
            "artifact and predictive decision metrics are exposed."
        ),
    )

elif implementation_evidence[7]:

    capability_result(
        7,
        "Predictive decision integration",
        "IMPLEMENTED / NOT FULLY RUNTIME VERIFIED",
        (
            "Source contains predictive integration logic, "
            "but artifact evidence is incomplete."
        ),
    )

else:

    capability_result(
        7,
        "Predictive decision integration",
        "FAILED",
        "No reliable predictive decision integration evidence found.",
    )

log("")


# ============================================================================
# SPECIAL CHECK — 100% DISCRIMINATION RATE
# ============================================================================

log("=" * 100)
log("SPECIAL AUDIT — 100% DISCRIMINATION RATE")
log("=" * 100)

discrimination_rates = []

for horizon in HORIZONS:

    result = None

    if isinstance(aggregate, dict):

        for key in (
            horizon,
            str(horizon),
            f"H+{horizon}",
            f"h{horizon}",
        ):

            if key in aggregate:
                result = aggregate[key]
                break

    if not isinstance(result, dict):
        continue

    discrimination = result.get(
        "discrimination"
    )

    if isinstance(discrimination, dict):

        rate = discrimination.get(
            "discrimination_rate"
        )

        if finite_number(rate):
            discrimination_rates.append(
                (horizon, float(rate))
            )


for horizon, rate in discrimination_rates:

    log(
        f"H+{horizon} discrimination rate: "
        f"{pct(rate)}"
    )


if (
    discrimination_rates
    and all(
        abs(rate - 1.0) < 1e-12
        for _, rate in discrimination_rates
    )
):

    log("")
    log(
        "WARNING:"
    )
    log(
        "All horizon discrimination rates are 100%."
    )
    log(
        "This audit does NOT interpret that as 100% predictive success."
    )
    log(
        "The rate is treated as an internal diagnostic until its "
        "definition is independently demonstrated against a null/"
        "permutation/control procedure."
    )

log("")


# ============================================================================
# FINAL SEVEN-CAPABILITY TABLE
# ============================================================================

log("=" * 100)
log("FINAL SEVEN-CAPABILITY AUDIT")
log("=" * 100)
log("")

log(
    f"{'#':<4}"
    f"{'CAPABILITY':<42}"
    f"{'STATUS':<38}"
)

log("-" * 100)

for number in range(1, 8):

    item = results.get(number)

    if item is None:
        continue

    log(
        f"{number:<4}"
        f"{item['name']:<42}"
        f"{item['status']:<38}"
    )

log("")


# ============================================================================
# DETAILED FINAL ASSESSMENT
# ============================================================================

log("=" * 100)
log("DETAILED ASSESSMENT")
log("=" * 100)
log("")

for number in range(1, 8):

    item = results.get(number)

    if item is None:
        continue

    log(
        f"{number}. {item['name']}"
    )

    log(
        f"   STATUS : {item['status']}"
    )

    log(
        f"   REASON : {item['reason']}"
    )

    log("")


# ============================================================================
# SUBMISSION READINESS
# ============================================================================

failed = [
    item
    for item in results.values()
    if item["status"] == "FAILED"
]

not_verified = [
    item
    for item in results.values()
    if "NOT VERIFIED" in item["status"]
]

empirical = [
    item
    for item in results.values()
    if item["status"] == "EMPIRICALLY VERIFIED"
]


log("=" * 100)
log("SUBMISSION INTERPRETATION")
log("=" * 100)
log("")

if failed:

    log(
        "OVERALL: NOT ALL SEVEN CAPABILITIES ARE EMPIRICALLY "
        "SUPPORTED BY THE CURRENT EVIDENCE."
    )

elif not_verified:

    log(
        "OVERALL: IMPLEMENTATION EXISTS, BUT SOME CAPABILITIES "
        "LACK SUFFICIENT INDEPENDENT RUNTIME EVIDENCE."
    )

else:

    log(
        "OVERALL: ALL SEVEN CAPABILITIES HAVE AT LEAST "
        "RUNTIME/EMPIRICAL EVIDENCE."
    )

log("")

log(
    "IMPORTANT:"
)

log(
    "This audit separates implementation from empirical effectiveness."
)

log(
    "A capability being present in source code is not equivalent "
    "to proving that it improves prediction."
)

log(
    "Negative out-of-sample predictive results are retained as "
    "valid research findings and are not silently converted to PASS."
)

log("")


# ============================================================================
# SOURCE INTEGRITY AFTER AUDIT
# ============================================================================

source_hash_after = sha256_file(SOURCE_FILE)

log("=" * 100)
log("READ-ONLY INTEGRITY CHECK")
log("=" * 100)
log("")

log(
    f"Source SHA256 before audit: "
    f"{source_hash_before}"
)

log(
    f"Source SHA256 after audit : "
    f"{source_hash_after}"
)

if source_hash_before == source_hash_after:

    log(
        "V4.1.6 source modification during audit: NONE"
    )

else:

    log(
        "WARNING: V4.1.6 source changed during audit."
    )


# ============================================================================
# OUTPUT REPORT
# ============================================================================

OUTPUT_REPORT.write_text(
    "\n".join(audit_lines),
    encoding="utf-8",
)

log("")
log("=" * 100)
log("AUDIT REPORT SAVED")
log("=" * 100)
log(
    f"    {OUTPUT_REPORT}"
)
log("")

print("")
print(
    "Independent seven-capability audit complete."
)
print(
    f"Report: {OUTPUT_REPORT}"
)