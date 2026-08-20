
import os
import re
import ast
from pathlib import Path
from datetime import datetime


# ============================================================
# MLAI VERSION AUDIT TOOL
# ============================================================
#
# Purpose:
#   Inspect ALL mlai*.py files in the current folder.
#
#   This does NOT modify any MLAI files.
#   This does NOT modify market_data.bin.
#   This does NOT modify mlai_learning_memory.bin.
#
#   It identifies:
#       - MLAI version files
#       - file sizes
#       - functions
#       - imports
#       - market_data.bin usage
#       - mlai_learning_memory.bin usage
#       - status file usage
#       - accuracy logic
#       - directional accuracy logic
#       - failure learning logic
#       - historical record logic
#       - context matching logic
#       - prediction logic
#
# ============================================================


BASE_DIR = Path.cwd()

OUTPUT_FILE = BASE_DIR / "MLAI_VERSION_AUDIT.txt"


# ============================================================
# HELPERS
# ============================================================

def print_line(char="=", length=80):
    print(char * length)


def safe_read_text(path):
    try:
        return path.read_text(
            encoding="utf-8",
            errors="replace"
        )
    except Exception as error:
        return f"<< READ ERROR: {error} >>"


def find_all(pattern, text, flags=re.IGNORECASE):
    try:
        return re.findall(
            pattern,
            text,
            flags
        )
    except Exception:
        return []


def get_functions(text):
    names = []

    try:
        tree = ast.parse(text)

        for node in ast.walk(tree):

            if isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef
                )
            ):

                names.append(
                    node.name
                )

    except Exception:
        pass

    return names


def get_imports(text):
    imports = []

    try:
        tree = ast.parse(text)

        for node in ast.walk(tree):

            if isinstance(
                node,
                ast.Import
            ):

                for item in node.names:

                    imports.append(
                        f"import {item.name}"
                    )

            elif isinstance(
                node,
                ast.ImportFrom
            ):

                module = node.module or ""

                for item in node.names:

                    imports.append(
                        f"from {module} import "
                        f"{item.name}"
                    )

    except Exception:
        pass

    return imports


def contains_any(text, patterns):

    found = []

    lower_text = text.lower()

    for pattern in patterns:

        if pattern.lower() in lower_text:

            found.append(pattern)

    return found


# ============================================================
# SEARCH CATEGORIES
# ============================================================

MARKET_PATTERNS = [
    "market_data.bin",
    "market_data",
    "pickle.load",
    "pickle.dump",
]


LEARNING_PATTERNS = [
    "mlai_learning_memory.bin",
    "learning_memory",
    "historical_records",
    "historical_records =",
    "build_historical_records",
]


ACCURACY_PATTERNS = [
    "accuracy",
    "calculate_statistics",
    "correct",
    "incorrect",
    "historical_accuracy",
    "directional_accuracy",
]


FAILURE_PATTERNS = [
    "failure_rate",
    "failure_penalty",
    "failure learning",
    "failure_patterns",
    "calculate_failure_learning",
    "build_failure_patterns",
]


PREDICTION_PATTERNS = [
    "prediction",
    "predict_from_context",
    "integrated_direction",
    "bullish",
    "bearish",
    "neutral",
]


CONTEXT_PATTERNS = [
    "analyze_context",
    "context_match_score",
    "current_context",
    "structure",
    "momentum",
    "volatility",
    "rejection",
]


HORIZON_PATTERNS = [
    "HORIZONS",
    "horizon",
    "4, 8, 16",
    "4:",
    "8:",
    "16:",
]


LEAKAGE_PATTERNS = [
    "walk-forward",
    "walk forward",
    "data leakage",
    "current_window",
    "future_only",
    "decision_index",
    "outcome_index",
]


STATUS_PATTERNS = [
    "MLAI_PROJECT_STATUS.md",
    "STATUS_FILE",
]


# ============================================================
# DISCOVER FILES
# ============================================================

all_python_files = sorted(
    BASE_DIR.glob("*.py")
)

mlai_files = []

for path in all_python_files:

    name = path.name.lower()

    if (
        name.startswith("mlai")
        or "mlai" in name
    ):

        mlai_files.append(path)


# ============================================================
# HEADER
# ============================================================

print_line()

print(
    "MLAI VERSION AUDIT"
)

print_line()

print(
    f"Folder: {BASE_DIR}"
)

print(
    f"Audit time: {datetime.now().isoformat()}"
)

print()

print(
    f"Python files found: {len(all_python_files)}"
)

print(
    f"MLAI files found: {len(mlai_files)}"
)

print()


# ============================================================
# FILE LIST
# ============================================================

print_line()

print(
    "ALL PYTHON FILES"
)

print_line()

for path in all_python_files:

    try:
        size = path.stat().st_size
    except Exception:
        size = 0

    print(
        f"{path.name:<40} "
        f"{size:>10} bytes"
    )


print()


# ============================================================
# MLAI FILE DETAILS
# ============================================================

audit_results = []


for path in mlai_files:

    text = safe_read_text(path)

    functions = get_functions(text)

    imports = get_imports(text)

    result = {

        "file":
            path.name,

        "size":
            len(text.encode(
                "utf-8",
                errors="replace"
            )),

        "functions":
            functions,

        "imports":
            imports,

        "market":
            contains_any(
                text,
                MARKET_PATTERNS
            ),

        "learning":
            contains_any(
                text,
                LEARNING_PATTERNS
            ),

        "accuracy":
            contains_any(
                text,
                ACCURACY_PATTERNS
            ),

        "failure":
            contains_any(
                text,
                FAILURE_PATTERNS
            ),

        "prediction":
            contains_any(
                text,
                PREDICTION_PATTERNS
            ),

        "context":
            contains_any(
                text,
                CONTEXT_PATTERNS
            ),

        "horizon":
            contains_any(
                text,
                HORIZON_PATTERNS
            ),

        "leakage":
            contains_any(
                text,
                LEAKAGE_PATTERNS
            ),

        "status":
            contains_any(
                text,
                STATUS_PATTERNS
            ),

        "has_main":
            "__name__" in text
            and "__main__" in text,

        "has_try":
            "try:" in text,

        "has_pickle":
            "pickle" in text,

        "text":
            text,
    }

    audit_results.append(
        result
    )


# ============================================================
# MLAI SUMMARY
# ============================================================

print_line()

print(
    "MLAI FILE SUMMARY"
)

print_line()


if not audit_results:

    print(
        "NO MLAI PYTHON FILES FOUND."
    )

else:

    for result in audit_results:

        print()

        print(
            f"FILE: {result['file']}"
        )

        print(
            f"Size: {result['size']} bytes"
        )

        print(
            "Market data logic      : "
            + (
                "YES"
                if result["market"]
                else "NO"
            )
        )

        print(
            "Learning memory logic  : "
            + (
                "YES"
                if result["learning"]
                else "NO"
            )
        )

        print(
            "Accuracy logic         : "
            + (
                "YES"
                if result["accuracy"]
                else "NO"
            )
        )

        print(
            "Failure logic          : "
            + (
                "YES"
                if result["failure"]
                else "NO"
            )
        )

        print(
            "Prediction logic       : "
            + (
                "YES"
                if result["prediction"]
                else "NO"
            )
        )

        print(
            "Context logic          : "
            + (
                "YES"
                if result["context"]
                else "NO"
            )
        )

        print(
            "Horizon logic          : "
            + (
                "YES"
                if result["horizon"]
                else "NO"
            )
        )

        print(
            "Leakage protection     : "
            + (
                "YES"
                if result["leakage"]
                else "NO"
            )
        )

        print(
            "Status file logic      : "
            + (
                "YES"
                if result["status"]
                else "NO"
            )
        )

        print(
            f"Functions              : "
            f"{len(result['functions'])}"
        )


# ============================================================
# IMPORTANT FILE OWNERS
# ============================================================

print()

print_line()

print(
    "IMPORTANT FILE OWNERS"
)

print_line()


categories = {

    "MARKET DATA": "market",

    "LEARNING MEMORY": "learning",

    "ACCURACY": "accuracy",

    "FAILURE LEARNING": "failure",

    "PREDICTION": "prediction",

    "CONTEXT": "context",

    "HORIZONS": "horizon",

    "DATA LEAKAGE": "leakage",

    "STATUS": "status",
}


for category, key in categories.items():

    owners = [
        result["file"]
        for result in audit_results
        if result[key]
    ]

    print()

    print(
        f"{category}:"
    )

    if owners:

        for owner in owners:

            print(
                f"  -> {owner}"
            )

    else:

        print(
            "  -> NONE"
        )


# ============================================================
# SEARCH FOR SPECIFIC LOGIC
# ============================================================

print()

print_line()

print(
    "ACCURACY / FAILURE / DIRECTION LOGIC LOCATIONS"
)

print_line()


important_terms = [

    "calculate_statistics",

    "directional_accuracy",

    "historical_accuracy",

    "failure_rate",

    "failure_penalty",

    "calculate_failure_learning",

    "build_failure_patterns",

    "predict_from_context",

    "context_match_score",

    "integrated_direction",

    "directional_separation",

    "neutral",

    "historical_records",

]


for result in audit_results:

    text = result["text"]

    lines = text.splitlines()

    matches = []

    for line_number, line in enumerate(
        lines,
        start=1
    ):

        lower_line = line.lower()

        for term in important_terms:

            if term.lower() in lower_line:

                matches.append(
                    (
                        line_number,
                        line.strip()
                    )
                )

    if not matches:
        continue

    print()

    print(
        f"FILE: {result['file']}"
    )

    print("-" * 80)

    printed = set()

    for line_number, line in matches:

        key = (
            line_number,
            line
        )

        if key in printed:
            continue

        printed.add(key)

        print(
            f"{line_number:>5}: {line}"
        )


# ============================================================
# CHECK FOR DUPLICATE DEFINITIONS
# ============================================================

print()

print_line()

print(
    "DUPLICATE FUNCTION DEFINITIONS ACROSS FILES"
)

print_line()


function_locations = {}


for result in audit_results:

    for function in result["functions"]:

        function_locations.setdefault(
            function,
            []
        ).append(
            result["file"]
        )


duplicates_found = False


for function, files in sorted(
    function_locations.items()
):

    if len(files) > 1:

        duplicates_found = True

        print()

        print(
            f"{function}:"
        )

        for file in files:

            print(
                f"  -> {file}"
            )


if not duplicates_found:

    print(
        "No duplicate function names "
        "found across MLAI files."
    )


# ============================================================
# CHECK FOR FILES THAT WRITE THE SAME MEMORY
# ============================================================

print()

print_line()

print(
    "MEMORY FILE WRITERS"
)

print_line()


memory_writers = []

for result in audit_results:

    text = result["text"]

    if (
        "mlai_learning_memory.bin"
        in text
        and (
            "pickle.dump"
            in text
            or "open(" in text
        )
    ):

        memory_writers.append(
            result["file"]
        )


if memory_writers:

    for file in memory_writers:

        print(
            f"  -> {file}"
        )

else:

    print(
        "No obvious learning-memory writer found."
    )


# ============================================================
# CHECK MARKET DATA WRITERS
# ============================================================

print()

print_line()

print(
    "MARKET DATA WRITERS"
)

print_line()


market_writers = []

for result in audit_results:

    text = result["text"]

    if (
        "market_data.bin"
        in text
        and "pickle.dump"
        in text
    ):

        market_writers.append(
            result["file"]
        )


if market_writers:

    for file in market_writers:

        print(
            f"  -> {file}"
        )

else:

    print(
        "No obvious market-data writer found."
    )


# ============================================================
# CHECK CURRENT EXECUTABLE VERSION
# ============================================================

print()

print_line()

print(
    "VERSION IDENTIFICATION"
)

print_line()


for result in audit_results:

    text = result["text"]

    version_matches = find_all(
        r'(?:VERSION|MLAI_VERSION)\s*=\s*["\']([^"\']+)["\']',
        text
    )

    if version_matches:

        print()

        print(
            f"{result['file']}:"
        )

        for version in version_matches:

            print(
                f"  VERSION = {version}"
            )


# ============================================================
# CHECK FOR COMMON LOGICAL PROBLEMS
# ============================================================

print()

print_line()

print(
    "AUTOMATIC LOGIC WARNINGS"
)

print_line()


warnings = []


for result in audit_results:

    text = result["text"]
    filename = result["file"]

    # --------------------------------------------------------
    # Warning 1
    # --------------------------------------------------------

    if (
        "correct"
        in text
        and "neutral"
        in text
        and "accuracy"
        in text
    ):

        if (
            "prediction == actual"
            in text
            or "prediction\n                ==" in text
        ):

            warnings.append(
                f"{filename}: "
                "accuracy appears to compare prediction "
                "against actual including neutral outcomes."
            )

    # --------------------------------------------------------
    # Warning 2
    # --------------------------------------------------------

    if (
        "failure_rate"
        in text
        and "correct"
        in text
    ):

        warnings.append(
            f"{filename}: "
            "contains both failure-rate and correctness logic. "
            "This file requires detailed inspection."
        )

    # --------------------------------------------------------
    # Warning 3
    # --------------------------------------------------------

    if (
        "historical_accuracy"
        in text
        and "historical_influence"
        in text
    ):

        warnings.append(
            f"{filename}: "
            "historical accuracy directly influences "
            "historical influence."
        )

    # --------------------------------------------------------
    # Warning 4
    # --------------------------------------------------------

    if (
        "neutral"
        in text
        and "directional_accuracy"
        in text
    ):

        warnings.append(
            f"{filename}: "
            "contains both neutral and directional accuracy logic. "
            "Verify neutral handling."
        )

    # --------------------------------------------------------
    # Warning 5
    # --------------------------------------------------------

    if (
        "historical_records"
        in text
        and "HORIZONS"
        in text
    ):

        warnings.append(
            f"{filename}: "
            "contains historical records and multiple horizons. "
            "Verify that each horizon is resolved independently."
        )


if warnings:

    for warning in warnings:

        print()

        print(
            "WARNING: "
            + warning
        )

else:

    print(
        "No automatic logic warnings detected."
    )


# ============================================================
# WRITE FULL AUDIT REPORT
# ============================================================

report_lines = []


report_lines.append(
    "MLAI VERSION AUDIT REPORT"
)

report_lines.append(
    "=" * 80
)

report_lines.append(
    f"Folder: {BASE_DIR}"
)

report_lines.append(
    f"Audit time: {datetime.now().isoformat()}"
)

report_lines.append("")


report_lines.append(
    "MLAI FILES"
)

report_lines.append(
    "-" * 80
)


for result in audit_results:

    report_lines.append(
        f"\nFILE: {result['file']}"
    )

    report_lines.append(
        f"Size: {result['size']} bytes"
    )

    report_lines.append(
        f"Market data: "
        f"{bool(result['market'])}"
    )

    report_lines.append(
        f"Learning memory: "
        f"{bool(result['learning'])}"
    )

    report_lines.append(
        f"Accuracy: "
        f"{bool(result['accuracy'])}"
    )

    report_lines.append(
        f"Failure learning: "
        f"{bool(result['failure'])}"
    )

    report_lines.append(
        f"Prediction: "
        f"{bool(result['prediction'])}"
    )

    report_lines.append(
        f"Context: "
        f"{bool(result['context'])}"
    )

    report_lines.append(
        f"Horizons: "
        f"{bool(result['horizon'])}"
    )

    report_lines.append(
        f"Leakage protection: "
        f"{bool(result['leakage'])}"
    )

    report_lines.append(
        "Functions:"
    )

    for function in result["functions"]:

        report_lines.append(
            f"  - {function}"
        )


report_lines.append("")

report_lines.append(
    "IMPORTANT OWNERS"
)

report_lines.append(
    "-" * 80
)


for category, key in categories.items():

    report_lines.append(
        f"\n{category}:"
    )

    owners = [
        result["file"]
        for result in audit_results
        if result[key]
    ]

    if owners:

        for owner in owners:

            report_lines.append(
                f"  - {owner}"
            )

    else:

        report_lines.append(
            "  - NONE"
        )


report_lines.append("")

report_lines.append(
    "WARNINGS"
)

report_lines.append(
    "-" * 80
)


if warnings:

    for warning in warnings:

        report_lines.append(
            f"- {warning}"
        )

else:

    report_lines.append(
        "No automatic warnings."
    )


report_lines.append("")

report_lines.append(
    "IMPORTANT LOGIC LOCATIONS"
)

report_lines.append(
    "-" * 80
)


for result in audit_results:

    text = result["text"]

    lines = text.splitlines()

    matches = []

    for line_number, line in enumerate(
        lines,
        start=1
    ):

        lower_line = line.lower()

        for term in important_terms:

            if term.lower() in lower_line:

                matches.append(
                    (
                        line_number,
                        line.strip()
                    )
                )

    if not matches:
        continue

    report_lines.append(
        f"\nFILE: {result['file']}"
    )

    printed = set()

    for line_number, line in matches:

        key = (
            line_number,
            line
        )

        if key in printed:
            continue

        printed.add(key)

        report_lines.append(
            f"{line_number}: {line}"
        )


try:

    OUTPUT_FILE.write_text(
        "\n".join(report_lines),
        encoding="utf-8"
    )

    print()

    print_line()

    print(
        f"PASS: Audit report saved to:"
    )

    print(
        f"{OUTPUT_FILE}"
    )

    print_line()

except Exception as error:

    print()

    print(
        "WARNING: Could not save audit report."
    )

    print(
        f"DETAIL: {type(error).__name__}: {error}"
    )


# ============================================================
# FINAL
# ============================================================

print()

print_line()

print(
    "MLAI AUDIT COMPLETED"
)

print_line()

print(
    "IMPORTANT:"
)

print(
    "This script only inspects the Python files."
)

print(
    "It does NOT modify MLAI source files."
)

print(
    "It does NOT modify market_data.bin."
)

print(
    "It does NOT modify mlai_learning_memory.bin."
)

print()

print(
    "Next step:"
)

print(
    "Send me the complete output of this audit."
)

print(
    "Then we can identify exactly which version "
    "contains the conflicting logic before changing anything."
)

print_line()
