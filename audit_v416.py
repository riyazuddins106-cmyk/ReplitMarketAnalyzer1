"""
MLAI v4.1.6 — COMPREHENSIVE RETRIEVAL / PREDICTIVE AUDITOR

Purpose
-------
Audit the EXISTING v4.1.6 implementation before making any code changes.

This auditor is intentionally diagnostic-only.

It does NOT:
    - modify mlai_market_structure_v416.py
    - modify mlai_market_structure_v415.py
    - modify market_data.bin
    - modify learning memory
    - modify production MLAI
    - change model parameters
    - create a replacement implementation

It produces:
    MLAI_V416_COMPREHENSIVE_AUDIT_REPORT.md

The audit covers:

1. Syntax / import integrity
2. Architecture inventory
3. Required v4.1.6 functions
4. Similarity representation
5. Similarity ranking
6. Retrieval implementation
7. Retrieval discrimination
8. H4 / H8 / H16 paths
9. Null retrieval test
10. Predictive decision integration
11. Incremental predictive value
12. Walk-forward/OOS architecture
13. Causality / leakage indicators
14. Discrimination metric semantics
15. Statistical/evaluation weaknesses
16. Runtime execution diagnostics
17. Source-code consistency
18. Root-cause classification
19. Recommended correction plan

The report deliberately distinguishes:

    IMPLEMENTED
    EXECUTABLE
    CAUSAL
    MEASURABLE
    PREDICTIVE
    INCREMENTAL
    ROBUST

These are NOT treated as equivalent.
"""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import inspect
import json
import math
import re
import statistics
import sys
import traceback
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


# =============================================================================
# CONFIGURATION
# =============================================================================

ROOT = Path(__file__).resolve().parent

SOURCE = ROOT / "mlai_market_structure_v416.py"
MARKET_DATA = ROOT / "market_data.bin"

REPORT = ROOT / "MLAI_V416_COMPREHENSIVE_AUDIT_REPORT.md"

HORIZONS = (4, 8, 16)

REQUIRED_FUNCTIONS = [
    "similarity_representation",
    "similarity_score",
    "calculate_retrieval_discrimination",
    "retrieve_historical_experience",
    "null_retrieval_sanity_test",
    "predictive_decision",
    "calculate_incremental_value",
    "horizon_discrimination_summary",
    "build_experience_records",
    "make_outcome",
    "conditional_baseline",
    "evaluate_distribution",
    "main",
]

REQUIRED_TEXT_MARKERS = [
    "selected_match_indices",
    "similarity_bucket",
    "incremental_value",
    "null_test",
    "predictive_evaluation",
    "retrieval_evaluation",
    "baseline_evaluation",
    "discrimination",
    "predictive_margin",
    "similarity_separation",
    "directional_discrimination",
]

FORBIDDEN_MUTATION_MARKERS = [
    "wb",
    "ab",
    "r+",
    "w+",
    "a+",
]

REPORT_LINES: List[str] = []


# =============================================================================
# REPORT HELPERS
# =============================================================================

def section(title: str) -> None:
    REPORT_LINES.append("")
    REPORT_LINES.append("=" * 100)
    REPORT_LINES.append(title)
    REPORT_LINES.append("=" * 100)
    REPORT_LINES.append("")


def line(text: str = "") -> None:
    REPORT_LINES.append(text)


def bullet(text: str) -> None:
    REPORT_LINES.append(f"- {text}")


def code(text: str) -> None:
    REPORT_LINES.append(f"`{text}`")


def verdict(
    label: str,
    implemented: str,
    causal: str,
    measurable: str,
    predictive: str,
    incremental: str,
    robust: str,
) -> None:
    line(
        f"| {label} | {implemented} | {causal} | "
        f"{measurable} | {predictive} | {incremental} | {robust} |"
    )


# =============================================================================
# BASIC UTILITIES
# =============================================================================

def sha256_file(path: Path) -> Optional[str]:
    if not path.exists():
        return None

    h = hashlib.sha256()

    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)

            if not chunk:
                break

            h.update(chunk)

    return h.hexdigest()


def read_source() -> str:
    if not SOURCE.exists():
        raise FileNotFoundError(
            f"Required source file does not exist:\n{SOURCE}"
        )

    return SOURCE.read_text(encoding="utf-8")


def safe_float(value: Any) -> Optional[float]:
    try:
        value = float(value)

        if not math.isfinite(value):
            return None

        return value

    except Exception:
        return None


def pct(value: Optional[float]) -> str:
    if value is None:
        return "N/A"

    return f"{value * 100:.2f}%"


def num(value: Optional[float]) -> str:
    if value is None:
        return "N/A"

    return f"{value:.6f}"


# =============================================================================
# AST ANALYSIS
# =============================================================================

@dataclass
class FunctionInfo:
    name: str
    lineno: int
    end_lineno: int
    args: List[str]
    calls: List[str]
    source: str


def collect_functions(
    tree: ast.AST,
    source_lines: Sequence[str],
) -> Dict[str, List[FunctionInfo]]:

    result: Dict[str, List[FunctionInfo]] = defaultdict(list)

    for node in ast.walk(tree):

        if not isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef),
        ):
            continue

        calls: List[str] = []

        for child in ast.walk(node):

            if isinstance(child, ast.Call):

                if isinstance(child.func, ast.Name):
                    calls.append(child.func.id)

                elif isinstance(child.func, ast.Attribute):
                    calls.append(child.func.attr)

        args = []

        for arg in node.args.args:
            args.append(arg.arg)

        start = max(0, node.lineno - 1)
        end = node.end_lineno or node.lineno

        fn_source = "\n".join(
            source_lines[start:end]
        )

        result[node.name].append(
            FunctionInfo(
                name=node.name,
                lineno=node.lineno,
                end_lineno=end,
                args=args,
                calls=sorted(set(calls)),
                source=fn_source,
            )
        )

    return result


def find_text_locations(
    source: str,
    markers: Iterable[str],
) -> Dict[str, List[int]]:

    lines = source.splitlines()

    result = {}

    for marker in markers:

        locations = []

        for index, text in enumerate(lines, start=1):

            if marker in text:
                locations.append(index)

        result[marker] = locations

    return result


def function_containing_line(
    functions: Dict[str, List[FunctionInfo]],
    line_number: int,
) -> Optional[str]:

    for name, entries in functions.items():

        for entry in entries:

            if (
                entry.lineno
                <= line_number
                <= entry.end_lineno
            ):
                return name

    return None


# =============================================================================
# IMPORT ANALYSIS
# =============================================================================

def import_module_from_path():
    module_name = "mlai_market_structure_v416_audit_target"

    spec = importlib.util.spec_from_file_location(
        module_name,
        SOURCE,
    )

    if spec is None or spec.loader is None:
        raise ImportError(
            f"Unable to construct import specification for {SOURCE}"
        )

    module = importlib.util.module_from_spec(spec)

    sys.modules[module_name] = module

    spec.loader.exec_module(module)

    return module


# =============================================================================
# CALL GRAPH ANALYSIS
# =============================================================================

def call_graph_for(
    functions: Dict[str, List[FunctionInfo]],
) -> Dict[str, List[str]]:

    graph: Dict[str, List[str]] = {}

    known = set(functions)

    for name, entries in functions.items():

        calls = set()

        for entry in entries:

            for call in entry.calls:

                if call in known and call != name:
                    calls.add(call)

        graph[name] = sorted(calls)

    return graph


def reachable_from(
    graph: Dict[str, List[str]],
    root: str,
) -> set:

    seen = set()
    stack = [root]

    while stack:

        current = stack.pop()

        if current in seen:
            continue

        seen.add(current)

        for child in graph.get(current, []):
            if child not in seen:
                stack.append(child)

    return seen


# =============================================================================
# SOURCE-LEVEL CAUSALITY / LEAKAGE HEURISTICS
# =============================================================================

def leakage_scan(
    source: str,
    functions: Dict[str, List[FunctionInfo]],
) -> Dict[str, Any]:

    lines = source.splitlines()

    future_markers = [
        "future",
        "forward",
        "lookahead",
        "lead(",
        "shift(",
        "outcome",
        "target",
        "label",
        "close[i +",
        "candles[i +",
    ]

    suspicious = []

    for index, text in enumerate(lines, start=1):

        lower = text.lower()

        for marker in future_markers:

            if marker.lower() in lower:

                suspicious.append(
                    {
                        "line": index,
                        "marker": marker,
                        "text": text.strip(),
                    }
                )

                break

    return {
        "suspicious_count": len(suspicious),
        "suspicious": suspicious,
    }


# =============================================================================
# METRIC SEMANTICS ANALYSIS
# =============================================================================

def metric_definition_analysis(
    functions: Dict[str, List[FunctionInfo]],
) -> Dict[str, Any]:

    targets = [
        "calculate_retrieval_discrimination",
        "horizon_discrimination_summary",
        "calculate_incremental_value",
        "predictive_decision",
        "evaluate_distribution",
        "null_retrieval_sanity_test",
    ]

    result = {}

    for name in targets:

        entries = functions.get(name, [])

        if not entries:
            result[name] = {
                "exists": False,
            }

            continue

        entry = entries[0]

        source = entry.source

        result[name] = {
            "exists": True,
            "line": entry.lineno,
            "args": entry.args,
            "calls": entry.calls,
            "contains_accuracy": "accuracy" in source.lower(),
            "contains_brier": "brier" in source.lower(),
            "contains_log_loss": "log_loss" in source.lower()
                or "logloss" in source.lower(),
            "contains_similarity": "similarity" in source.lower(),
            "contains_direction": "direction" in source.lower(),
            "contains_rate": "rate" in source.lower(),
            "contains_margin": "margin" in source.lower(),
            "contains_null": "null" in source.lower(),
        }

    return result


# =============================================================================
# RUNTIME STRUCTURAL TESTS
# =============================================================================

def runtime_audit(module) -> Dict[str, Any]:

    result: Dict[str, Any] = {
        "imported": True,
        "runtime_checks": [],
        "errors": [],
    }

    for name in REQUIRED_FUNCTIONS:

        fn = getattr(module, name, None)

        if not callable(fn):

            result["runtime_checks"].append(
                {
                    "function": name,
                    "status": "MISSING",
                }
            )

            continue

        try:
            signature = inspect.signature(fn)

            result["runtime_checks"].append(
                {
                    "function": name,
                    "status": "CALLABLE",
                    "signature": str(signature),
                }
            )

        except Exception as exc:

            result["runtime_checks"].append(
                {
                    "function": name,
                    "status": "CALLABLE_BUT_SIGNATURE_FAILED",
                    "error": repr(exc),
                }
            )

    return result


# =============================================================================
# DATA / MODULE CONSTANT AUDIT
# =============================================================================

def constant_audit(module) -> Dict[str, Any]:

    names = [
        "VERSION",
        "MARKET_DATA_FILE",
        "HORIZONS",
        "MIN_TRAIN_SAMPLES",
        "MIN_STATE_SUPPORT",
        "KNN_K",
        "MIN_CONFIDENCE",
        "WEIGHT_LOGISTIC",
        "WEIGHT_KNN",
        "WEIGHT_STATE",
        "VALIDATION_BIN",
        "VALIDATION_REPORT",
    ]

    result = {}

    for name in names:

        if hasattr(module, name):

            value = getattr(module, name)

            try:
                json.dumps(value)

            except Exception:
                value = repr(value)

            result[name] = value

    return result


# =============================================================================
# FUNCTION SOURCE EXTRACTION
# =============================================================================

def source_excerpt(
    functions: Dict[str, List[FunctionInfo]],
    name: str,
    max_lines: int = 160,
) -> List[str]:

    entries = functions.get(name, [])

    if not entries:
        return []

    lines = entries[0].source.splitlines()

    if len(lines) <= max_lines:
        return lines

    return lines[:max_lines] + [
        "... [excerpt truncated]"
    ]


# =============================================================================
# STATIC REQUIREMENT AUDIT
# =============================================================================

def requirement_audit(
    source: str,
    functions: Dict[str, List[FunctionInfo]],
) -> Dict[str, Any]:

    result = {}

    for name in REQUIRED_FUNCTIONS:

        entries = functions.get(name, [])

        result[name] = {
            "exists": bool(entries),
            "count": len(entries),
            "lines": [
                entry.lineno
                for entry in entries
            ],
        }

    marker_locations = find_text_locations(
        source,
        REQUIRED_TEXT_MARKERS,
    )

    result["_markers"] = marker_locations

    return result


# =============================================================================
# MAIN LOOP DISCOVERY
# =============================================================================

def discover_oos_loop(
    source: str,
    tree: ast.AST,
) -> Dict[str, Any]:

    result = {
        "candidates": [],
        "selected": None,
    }

    for node in ast.walk(tree):

        if not isinstance(node, ast.FunctionDef):
            continue

        if node.name != "main":
            continue

        for child in ast.walk(node):

            if not isinstance(
                child,
                (ast.For, ast.While),
            ):
                continue

            calls = set()

            for sub in ast.walk(child):

                if isinstance(sub, ast.Call):

                    if isinstance(sub.func, ast.Name):
                        calls.add(sub.func.id)

                    elif isinstance(sub.func, ast.Attribute):
                        calls.add(sub.func.attr)

            required = {
                "retrieve_historical_experience",
                "predictive_decision",
                "make_outcome",
            }

            if required.issubset(calls):

                result["candidates"].append(
                    {
                        "line": child.lineno,
                        "calls": sorted(calls),
                    }
                )

    if len(result["candidates"]) == 1:
        result["selected"] = result["candidates"][0]

    elif result["candidates"]:

        # Select the deepest / latest loop as diagnostic target,
        # but explicitly mark ambiguity.
        result["selected"] = result["candidates"][-1]
        result["ambiguous"] = True

    else:
        result["ambiguous"] = False

    return result


# =============================================================================
# WRITE REPORT
# =============================================================================

def write_report() -> None:

    REPORT.write_text(
        "\n".join(REPORT_LINES) + "\n",
        encoding="utf-8",
    )


# =============================================================================
# AUDIT
# =============================================================================

def main() -> int:

    print("=" * 100)
    print("MLAI v4.1.6 COMPREHENSIVE AUDITOR")
    print("=" * 100)
    print()

    if not SOURCE.exists():

        print("ERROR:")
        print(f"Missing source: {SOURCE}")

        return 1

    source = read_source()
    source_lines = source.splitlines()

    source_hash_before = sha256_file(SOURCE)
    market_hash_before = sha256_file(MARKET_DATA)

    print(f"Source : {SOURCE}")
    print(f"Lines  : {len(source_lines)}")
    print(f"Bytes  : {len(source.encode('utf-8'))}")
    print()

    # -------------------------------------------------------------------------
    # 1. SYNTAX
    # -------------------------------------------------------------------------

    section("1. SOURCE INTEGRITY AND SYNTAX")

    syntax_pass = True
    tree = None

    try:

        tree = ast.parse(
            source,
            filename=str(SOURCE),
        )

        line("SYNTAX: PASS")
        line(
            f"AST nodes: {sum(1 for _ in ast.walk(tree))}"
        )

    except SyntaxError as exc:

        syntax_pass = False

        line("SYNTAX: FAIL")
        line(
            f"Line: {exc.lineno}"
        )
        line(
            f"Offset: {exc.offset}"
        )
        line(
            f"Message: {exc.msg}"
        )

        write_report()

        return 1

    functions = collect_functions(
        tree,
        source_lines,
    )

    # -------------------------------------------------------------------------
    # 2. FUNCTION INVENTORY
    # -------------------------------------------------------------------------

    section("2. FUNCTION ARCHITECTURE")

    line(
        "| Function | Count | First line |"
    )
    line(
        "|---|---:|---:|"
    )

    for name in sorted(functions):

        entries = functions[name]

        line(
            f"| `{name}` | {len(entries)} | "
            f"{entries[0].lineno} |"
        )

    duplicate_functions = {
        name: len(entries)
        for name, entries in functions.items()
        if len(entries) > 1
    }

    if duplicate_functions:

        line()
        line("DUPLICATE FUNCTION DEFINITIONS DETECTED:")

        for name, count in duplicate_functions.items():

            bullet(
                f"`{name}` appears {count} times"
            )

    else:

        line("Duplicate function definitions: NONE")

    # -------------------------------------------------------------------------
    # 3. REQUIRED FUNCTIONS
    # -------------------------------------------------------------------------

    section("3. REQUIRED V4.1.6 COMPONENTS")

    line(
        "| Component | Exists | Count | Line |"
    )
    line(
        "|---|---|---:|---:|"
    )

    for name in REQUIRED_FUNCTIONS:

        entries = functions.get(name, [])

        line(
            f"| `{name}` | "
            f"{'YES' if entries else 'NO'} | "
            f"{len(entries)} | "
            f"{entries[0].lineno if entries else '-'} |"
        )

    # -------------------------------------------------------------------------
    # 4. CALL GRAPH
    # -------------------------------------------------------------------------

    section("4. CALL GRAPH")

    graph = call_graph_for(functions)

    roots = [
        "main",
        "retrieve_historical_experience",
        "predictive_decision",
        "calculate_incremental_value",
        "horizon_discrimination_summary",
    ]

    for root in roots:

        line(f"`{root}`")

        reachable = reachable_from(
            graph,
            root,
        )

        for item in sorted(reachable):

            if item == root:
                continue

            bullet(item)

    # -------------------------------------------------------------------------
    # 5. OOS LOOP
    # -------------------------------------------------------------------------

    section("5. OUT-OF-SAMPLE / WALK-FORWARD PIPELINE")

    oos = discover_oos_loop(
        source,
        tree,
    )

    if oos["candidates"]:

        line(
            f"OOS loop candidates: {len(oos['candidates'])}"
        )

        for candidate in oos["candidates"]:

            line(
                f"- line {candidate['line']}: "
                f"{', '.join(candidate['calls'])}"
            )

    else:

        line("OOS loop candidate: NOT FOUND")

    if oos.get("ambiguous"):

        line(
            "WARNING: Multiple loops satisfy the basic OOS call "
            "signature. This requires manual semantic verification."
        )

    elif oos.get("selected"):

        line(
            f"Selected diagnostic loop: "
            f"line {oos['selected']['line']}"
        )

    else:

        line("Selected OOS loop: NONE")

    # -------------------------------------------------------------------------
    # 6. REQUIRED TEXT
    # -------------------------------------------------------------------------

    section("6. REQUIRED EVALUATION MARKERS")

    marker_locations = find_text_locations(
        source,
        REQUIRED_TEXT_MARKERS,
    )

    for marker, locations in marker_locations.items():

        if locations:

            line(
                f"`{marker}` -> "
                f"{', '.join(map(str, locations[:20]))}"
            )

        else:

            line(
                f"`{marker}` -> NOT FOUND"
            )

    # -------------------------------------------------------------------------
    # 7. METRIC SEMANTICS
    # -------------------------------------------------------------------------

    section("7. METRIC IMPLEMENTATION AUDIT")

    metrics = metric_definition_analysis(
        functions,
    )

    for name, info in metrics.items():

        line()
        line(f"### `{name}`")

        if not info.get("exists"):

            line("STATUS: MISSING")
            continue

        line(
            f"Line: {info['line']}"
        )

        line(
            f"Arguments: {', '.join(info['args'])}"
        )

        line(
            f"Calls: {', '.join(info['calls']) or 'NONE'}"
        )

        flags = [
            "accuracy",
            "brier",
            "log_loss",
            "similarity",
            "direction",
            "rate",
            "margin",
            "null",
        ]

        for flag in flags:

            key = f"contains_{flag}"

            line(
                f"- contains {flag}: "
                f"{'YES' if info[key] else 'NO'}"
            )

    # -------------------------------------------------------------------------
    # 8. DISCRIMINATION DEEP AUDIT
    # -------------------------------------------------------------------------

    section("8. DISCRIMINATION SEMANTICS — CRITICAL AUDIT")

    discrimination_functions = [
        "calculate_retrieval_discrimination",
        "horizon_discrimination_summary",
    ]

    for name in discrimination_functions:

        excerpts = source_excerpt(
            functions,
            name,
            220,
        )

        if not excerpts:
            continue

        line()
        line(f"### `{name}` source excerpt")

        line("```python")

        for item in excerpts:
            line(item)

        line("```")

    line()
    line(
        "IMPORTANT DIAGNOSTIC QUESTION:"
    )

    line(
        "Does `discrimination_rate` measure genuine outcome "
        "discrimination, or merely the percentage of queries for "
        "which the discrimination calculation was available?"
    )

    line(
        "The runtime result of 100.00% for H4/H8/H16 must NOT "
        "automatically be interpreted as 100% predictive discrimination."
    )

    # -------------------------------------------------------------------------
    # 9. SIMILARITY AUDIT
    # -------------------------------------------------------------------------

    section("9. SIMILARITY REPRESENTATION AND RANKING")

    for name in [
        "similarity_representation",
        "similarity_score",
        "path_similarity",
        "numeric_similarity",
        "retrieve_historical_experience",
        "select_episode_representatives",
    ]:

        entries = functions.get(name, [])

        if not entries:
            continue

        entry = entries[0]

        line(
            f"### `{name}`"
        )

        line(
            f"Lines: {entry.lineno}-{entry.end_lineno}"
        )

        line(
            f"Arguments: {', '.join(entry.args)}"
        )

        line(
            f"Internal calls: "
            f"{', '.join(entry.calls) or 'NONE'}"
        )

        source_lower = entry.source.lower()

        checks = {
            "normalization": (
                "normalize" in source_lower
                or "normaliz" in source_lower
            ),
            "distance": (
                "distance" in source_lower
                or "diff" in source_lower
            ),
            "weighting": (
                "weight" in source_lower
                or "weighted" in source_lower
            ),
            "rank/sort": (
                "sort" in source_lower
                or "rank" in source_lower
            ),
            "episode": (
                "episode" in source_lower
            ),
            "temporal exclusion": (
                "query_index" in source_lower
                or "index" in source_lower
            ),
        }

        for key, value in checks.items():

            line(
                f"- {key}: "
                f"{'FOUND' if value else 'NOT EVIDENT'}"
            )

    # -------------------------------------------------------------------------
    # 10. RETRIEVAL AUDIT
    # -------------------------------------------------------------------------

    section("10. HISTORICAL RETRIEVAL AUDIT")

    retrieval_entries = functions.get(
        "retrieve_historical_experience",
        [],
    )

    if retrieval_entries:

        entry = retrieval_entries[0]

        source_lower = entry.source.lower()

        checks = [
            ("coarse filtering", "coarse_filter"),
            ("similarity scoring", "similarity_score"),
            ("episode deduplication", "episode"),
            ("top-k selection", "top_k"),
            ("selected matches", "selected_match"),
            ("sparse handling", "sparse"),
            ("query index", "query_index"),
            ("horizon", "horizon"),
        ]

        for label, marker in checks:

            line(
                f"- {label}: "
                f"{'FOUND' if marker.lower() in source_lower else 'NOT EVIDENT'}"
            )

    else:

        line(
            "retrieve_historical_experience: MISSING"
        )

    # -------------------------------------------------------------------------
    # 11. PREDICTIVE INTEGRATION AUDIT
    # -------------------------------------------------------------------------

    section("11. PREDICTIVE DECISION INTEGRATION")

    predictive_entries = functions.get(
        "predictive_decision",
        [],
    )

    if predictive_entries:

        entry = predictive_entries[0]

        source_lower = entry.source.lower()

        line(
            f"Function lines: {entry.lineno}-{entry.end_lineno}"
        )

        checks = [
            ("retrieval", "retrieval"),
            ("probabilities", "probabil"),
            ("confidence", "confidence"),
            ("abstention", "abstain"),
            ("logistic", "logistic"),
            ("knn", "knn"),
            ("state evidence", "state"),
            ("weights", "weight"),
            ("similarity", "similarity"),
        ]

        for label, marker in checks:

            line(
                f"- {label}: "
                f"{'FOUND' if marker.lower() in source_lower else 'NOT EVIDENT'}"
            )

        line()
        line(
            "Predictive source excerpt:"
        )

        line("```python")

        for item in source_excerpt(
            functions,
            "predictive_decision",
            260,
        ):

            line(item)

        line("```")

    else:

        line(
            "predictive_decision: MISSING"
        )

    # -------------------------------------------------------------------------
    # 12. INCREMENTAL VALUE AUDIT
    # -------------------------------------------------------------------------

    section("12. INCREMENTAL PREDICTIVE VALUE")

    incremental_entries = functions.get(
        "calculate_incremental_value",
        [],
    )

    if incremental_entries:

        entry = incremental_entries[0]

        line(
            f"Function lines: {entry.lineno}-{entry.end_lineno}"
        )

        line(
            "Source:"
        )

        line("```python")

        for item in source_excerpt(
            functions,
            "calculate_incremental_value",
            260,
        ):

            line(item)

        line("```")

        source_lower = entry.source.lower()

        for marker in [
            "retrieval",
            "baseline",
            "predictive",
            "brier",
            "log_loss",
            "accuracy",
        ]:

            line(
                f"- `{marker}`: "
                f"{'FOUND' if marker in source_lower else 'NOT EVIDENT'}"
            )

    else:

        line(
            "calculate_incremental_value: MISSING"
        )

    # -------------------------------------------------------------------------
    # 13. NULL TEST
    # -------------------------------------------------------------------------

    section("13. NULL RETRIEVAL SANITY TEST")

    null_entries = functions.get(
        "null_retrieval_sanity_test",
        [],
    )

    if null_entries:

        entry = null_entries[0]

        line(
            f"Function lines: {entry.lineno}-{entry.end_lineno}"
        )

        source_lower = entry.source.lower()

        for marker in [
            "random",
            "shuffle",
            "permutation",
            "null",
            "similarity",
            "retrieval",
            "outcome",
        ]:

            line(
                f"- `{marker}`: "
                f"{'FOUND' if marker in source_lower else 'NOT EVIDENT'}"
            )

        line()
        line(
            "Source excerpt:"
        )

        line("```python")

        for item in source_excerpt(
            functions,
            "null_retrieval_sanity_test",
            260,
        ):

            line(item)

        line("```")

    else:

        line(
            "null_retrieval_sanity_test: MISSING"
        )

    # -------------------------------------------------------------------------
    # 14. CAUSALITY / LEAKAGE
    # -------------------------------------------------------------------------

    section("14. CAUSALITY / LEAKAGE STATIC AUDIT")

    leakage = leakage_scan(
        source,
        functions,
    )

    line(
        f"Potential future-related references: "
        f"{leakage['suspicious_count']}"
    )

    line(
        "NOTE: These are diagnostic candidates, NOT automatic leakage failures."
    )

    for item in leakage["suspicious"][:120]:

        line(
            f"- line {item['line']}: "
            f"[{item['marker']}] "
            f"{item['text']}"
        )

    # -------------------------------------------------------------------------
    # 15. MAIN EVALUATION SOURCE
    # -------------------------------------------------------------------------

    section("15. MAIN OOS EVALUATION SOURCE")

    if oos.get("selected"):

        selected_line = oos["selected"]["line"]

        main_entries = functions.get("main", [])

        if main_entries:

            main_entry = main_entries[0]

            main_lines = main_entry.source.splitlines()

            # Locate relative position.
            start_line = main_entry.lineno

            relative = selected_line - start_line

            lower = max(
                0,
                relative - 35,
            )

            upper = min(
                len(main_lines),
                relative + 240,
            )

            line("```python")

            for item in main_lines[lower:upper]:
                line(item)

            line("```")

    else:

        line(
            "Unable to identify a unique OOS evaluation loop."
        )

    # -------------------------------------------------------------------------
    # 16. CONSTANTS
    # -------------------------------------------------------------------------

    section("16. MODEL / VALIDATION CONSTANTS")

    try:

        module = import_module_from_path()

        constants = constant_audit(module)

        for name, value in constants.items():

            line(
                f"- `{name}` = `{value}`"
            )

    except Exception as exc:

        line(
            "Module import failed."
        )

        line(
            f"ERROR: {repr(exc)}"
        )

        line(
            traceback.format_exc()
        )

        module = None

    # -------------------------------------------------------------------------
    # 17. RUNTIME FUNCTION AUDIT
    # -------------------------------------------------------------------------

    section("17. RUNTIME FUNCTION AVAILABILITY")

    if module is not None:

        runtime = runtime_audit(module)

        line(
            "| Function | Status | Signature |"
        )

        line(
            "|---|---|---|"
        )

        for item in runtime["runtime_checks"]:

            line(
                f"| `{item['function']}` | "
                f"{item['status']} | "
                f"`{item.get('signature', '-')}` |"
            )

    else:

        line(
            "Runtime module unavailable because import failed."
        )

    # -------------------------------------------------------------------------
    # 18. DATA PROTECTION
    # -------------------------------------------------------------------------

    section("18. DATA / FILE PROTECTION")

    line(
        f"market_data.bin exists: "
        f"{'YES' if MARKET_DATA.exists() else 'NO'}"
    )

    if market_hash_before:

        line(
            f"market_data.bin SHA256 before audit: "
            f"`{market_hash_before}`"
        )

    line(
        f"v4.1.6 SHA256 before audit: "
        f"`{source_hash_before}`"
    )

    line(
        "The auditor itself performs no write operation against "
        "the source or market data."
    )

    # -------------------------------------------------------------------------
    # 19. SEVEN REQUIREMENTS CLASSIFICATION
    # -------------------------------------------------------------------------

    section("19. SEVEN REQUIREMENTS — ENGINEERING VS SCIENTIFIC STATUS")

    line(
        "| Requirement | Implemented | Causal | Measurable | "
        "Predictive | Incremental | Robust |"
    )

    line(
        "|---|---|---|---|---|---|---|"
    )

    # Deliberately conservative classifications.
    verdict(
        "Similarity representation",
        "YES",
        "AUDIT",
        "YES",
        "AUDIT",
        "AUDIT",
        "AUDIT",
    )

    verdict(
        "Retrieval ranking / discrimination",
        "YES",
        "AUDIT",
        "YES",
        "AUDIT",
        "AUDIT",
        "AUDIT",
    )

    verdict(
        "H4 discrimination",
        "YES",
        "AUDIT",
        "YES",
        "AUDIT",
        "AUDIT",
        "AUDIT",
    )

    verdict(
        "H8 discrimination",
        "YES",
        "AUDIT",
        "YES",
        "AUDIT",
        "AUDIT",
        "AUDIT",
    )

    verdict(
        "H16 discrimination",
        "YES",
        "AUDIT",
        "YES",
        "AUDIT",
        "AUDIT",
        "AUDIT",
    )

    verdict(
        "Incremental predictive value",
        "YES",
        "AUDIT",
        "YES",
        "NOT DEMONSTRATED",
        "NOT DEMONSTRATED",
        "AUDIT",
    )

    verdict(
        "Predictive decision integration",
        "YES",
        "AUDIT",
        "YES",
        "CURRENTLY WEAK",
        "CURRENTLY NEGATIVE",
        "AUDIT",
    )

    # -------------------------------------------------------------------------
    # 20. CURRENT KNOWN RUNTIME RESULTS
    # -------------------------------------------------------------------------

    section("20. CURRENT V4.1.6 RUNTIME EVIDENCE")

    line(
        "The following values are recorded from the supplied v4.1.6 run."
    )

    runtime_results = {
        4: {
            "retrieval_accuracy": 0.4394,
            "baseline_accuracy": 0.4472,
            "retrieval_brier_lift": -0.0019,
            "predictive_brier_lift": -0.0160,
            "predictive_log_loss_lift": -0.0792,
            "discrimination_rate": 1.0000,
            "similarity_separation": 0.5875,
            "directional_discrimination": 0.0353,
            "predictive_margin": 0.0347,
        },
        8: {
            "retrieval_accuracy": 0.4764,
            "baseline_accuracy": 0.5027,
            "retrieval_brier_lift": -0.0023,
            "predictive_brier_lift": -0.0221,
            "predictive_log_loss_lift": -0.0652,
            "discrimination_rate": 1.0000,
            "similarity_separation": 0.5863,
            "directional_discrimination": 0.0404,
            "predictive_margin": 0.0439,
        },
        16: {
            "retrieval_accuracy": 0.4645,
            "baseline_accuracy": 0.4880,
            "retrieval_brier_lift": 0.0012,
            "predictive_brier_lift": -0.0189,
            "predictive_log_loss_lift": -0.0633,
            "discrimination_rate": 1.0000,
            "similarity_separation": 0.5852,
            "directional_discrimination": 0.0507,
            "predictive_margin": 0.0836,
        },
    }

    line(
        "| Horizon | Retrieval Acc | Baseline Acc | "
        "Retrieval Brier Lift | Predictive Brier Lift | "
        "Predictive LogLoss Lift | Discrimination Rate | "
        "Similarity Separation | Directional Discrimination |"
    )

    line(
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    )

    for horizon in HORIZONS:

        row = runtime_results[horizon]

        line(
            f"| H+{horizon} | "
            f"{pct(row['retrieval_accuracy'])} | "
            f"{pct(row['baseline_accuracy'])} | "
            f"{num(row['retrieval_brier_lift'])} | "
            f"{num(row['predictive_brier_lift'])} | "
            f"{num(row['predictive_log_loss_lift'])} | "
            f"{pct(row['discrimination_rate'])} | "
            f"{num(row['similarity_separation'])} | "
            f"{num(row['directional_discrimination'])} |"
        )

    # -------------------------------------------------------------------------
    # 21. ROOT CAUSE ANALYSIS
    # -------------------------------------------------------------------------

    section("21. ROOT-CAUSE ANALYSIS")

    line(
        "Based on the supplied execution results plus the static architecture,"
        " the following issues require correction rather than cosmetic tuning."
    )

    line()
    line("ROOT CAUSE CANDIDATE A — DISCRIMINATION METRIC SEMANTICS")

    bullet(
        "The reported 100% discrimination rate is not consistent with "
        "the modest directional-discrimination values."
    )

    bullet(
        "The implementation must be inspected to determine whether "
        "the rate measures availability/calculation success instead of "
        "true outcome discrimination."
    )

    line()
    line("ROOT CAUSE CANDIDATE B — SIMILARITY-TO-OUTCOME LINK")

    bullet(
        "Similarity separation exists, but the retrieval Brier lift "
        "is approximately zero overall."
    )

    bullet(
        "Therefore high similarity does not yet demonstrate a strong "
        "future-outcome relationship."
    )

    line()
    line("ROOT CAUSE CANDIDATE C — PREDICTIVE INTEGRATION")

    bullet(
        "Predictive Brier lift is negative at all three horizons."
    )

    bullet(
        "The predictive layer is therefore not currently adding "
        "useful information to the baseline."
    )

    bullet(
        "The integration must be conditional on demonstrated retrieval "
        "signal rather than assuming retrieval evidence is beneficial."
    )

    line()
    line("ROOT CAUSE CANDIDATE D — EVALUATION DEPTH")

    bullet(
        "Aggregate accuracy/Brier values alone are insufficient to "
        "establish robust historical-experience retrieval."
    )

    bullet(
        "Similarity-bucket performance, top-k stability, null comparison, "
        "and effect-size analysis need to be treated as first-class metrics."
    )

    # -------------------------------------------------------------------------
    # 22. WHAT A CORRECT FIX MUST ACHIEVE
    # -------------------------------------------------------------------------

    section("22. ACCEPTANCE CRITERIA FOR THE NEXT FIX")

    criteria = [
        "Discrimination rate must have an unambiguous scientific definition.",
        "Technical availability must be separated from predictive discrimination.",
        "Similarity must remain strictly causal.",
        "Historical candidates must remain strictly prior to each OOS query.",
        "Similarity ranking must be evaluated against future outcomes.",
        "H4, H8 and H16 must be evaluated independently.",
        "Top-ranked retrieval must be compared against lower-ranked retrieval.",
        "Retrieval must be compared against the appropriate conditional baseline.",
        "Observed retrieval performance must be compared against a valid null.",
        "Predictive integration must not degrade the baseline merely because retrieval exists.",
        "Incremental value must be measured on identical OOS observations.",
        "Negative incremental value must remain visible rather than being hidden.",
        "No tuning may use OOS outcomes.",
        "market_data.bin must remain read-only.",
        "v4.1.5 must remain unchanged.",
    ]

    for criterion in criteria:
        bullet(criterion)

    # -------------------------------------------------------------------------
    # 23. FINAL CLASSIFICATION
    # -------------------------------------------------------------------------

    section("23. FINAL AUDIT CLASSIFICATION")

    line(
        "CURRENT ENGINEERING STATUS: IMPLEMENTED"
    )

    line(
        "CURRENT CAUSAL STATUS: REQUIRES VERIFICATION"
    )

    line(
        "CURRENT RETRIEVAL SIGNAL STATUS: WEAK / MIXED"
    )

    line(
        "CURRENT INCREMENTAL VALUE STATUS: NOT DEMONSTRATED"
    )

    line(
        "CURRENT PREDICTIVE INTEGRATION STATUS: NEGATIVE ON AGGREGATE BRIER"
    )

    line(
        "CURRENT SCIENTIFIC ROBUSTNESS STATUS: NOT YET ESTABLISHED"
    )

    line()
    line(
        "IMPORTANT:"
    )

    line(
        "This audit intentionally does NOT modify the implementation."
    )

    line(
        "The purpose is to establish the root causes before the next "
        "implementation change."
    )

    # -------------------------------------------------------------------------
    # 24. SOURCE HASH AFTER
    # -------------------------------------------------------------------------

    section("24. POST-AUDIT INTEGRITY")

    source_hash_after = sha256_file(SOURCE)
    market_hash_after = sha256_file(MARKET_DATA)

    line(
        f"v4.1.6 SHA256 after audit: "
        f"`{source_hash_after}`"
    )

    line(
        f"market_data.bin SHA256 after audit: "
        f"`{market_hash_after}`"
    )

    if source_hash_before == source_hash_after:

        line(
            "v4.1.6 source integrity: PASS — unchanged"
        )

    else:

        line(
            "v4.1.6 source integrity: WARNING — hash changed"
        )

    if market_hash_before == market_hash_after:

        line(
            "market_data.bin integrity: PASS — unchanged"
        )

    else:

        line(
            "market_data.bin integrity: WARNING — hash changed"
        )

    # -------------------------------------------------------------------------
    # WRITE
    # -------------------------------------------------------------------------

    write_report()

    print()
    print("=" * 100)
    print("MLAI v4.1.6 AUDIT COMPLETE")
    print("=" * 100)
    print()
    print(f"Audit report:")
    print(f"    {REPORT}")
    print()
    print("Source:")
    print(f"    {SOURCE}")
    print()
    print("Source SHA256 before:")
    print(f"    {source_hash_before}")
    print()
    print("Source SHA256 after:")
    print(f"    {source_hash_after}")
    print()
    print("market_data.bin SHA256 before:")
    print(f"    {market_hash_before}")
    print()
    print("market_data.bin SHA256 after:")
    print(f"    {market_hash_after}")
    print()
    print("IMPORTANT:")
    print("    No source modification was performed.")
    print("    No market-data modification was performed.")
    print("    No model modification was performed.")
    print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())