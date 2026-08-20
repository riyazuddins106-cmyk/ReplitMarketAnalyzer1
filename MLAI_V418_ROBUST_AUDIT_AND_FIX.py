from pathlib import Path
import ast
import re
import shutil
import json
import hashlib
import textwrap
from datetime import datetime


# =============================================================================
# MLAI V4.1.8 — ROBUST AUDIT + FIX BUILDER
#
# PURPOSE
# -------
# Audit the REAL v4.1.7 implementation before attempting any modification.
#
# This program deliberately avoids assumptions such as:
#
#     match.similarity
#     "total": mean_similarity
#     a specific similarity dictionary
#     a specific candidate variable name
#
# The source itself must prove the implementation.
#
# SAFETY CONTRACT
# ---------------
# 1. V4.1.7 is never modified.
# 2. market_data.bin is never modified.
# 3. Existing memory artifacts are never modified.
# 4. A V4.1.8 file is written only after:
#       - source parses
#       - retrieval function is uniquely identified
#       - similarity representation is discovered
#       - candidate/ranking path is identified
#       - sparse logic is identified
#       - a structurally safe patch point is proven
# 5. If anything is ambiguous, BUILD IS REFUSED.
#
# IMPORTANT
# ---------
# This is an audit/fix BUILDER, not a blind text-replacement script.
# =============================================================================


SRC = Path("mlai_market_structure_v417.py")
DST = Path("mlai_market_structure_v418.py")
BACKUP = Path("mlai_market_structure_v417_before_v418_auditfix.py")

REPORT = Path("MLAI_V418_ROBUST_AUDIT_REPORT.md")
JSON_REPORT = Path("MLAI_V418_ROBUST_AUDIT_REPORT.json")


# =============================================================================
# RESULT STATE
# =============================================================================

audit = {
    "timestamp": datetime.now().isoformat(),
    "source": str(SRC),
    "destination": str(DST),
    "safe_to_modify": False,
    "fix_applied": False,
    "checks": {},
    "discoveries": {},
    "warnings": [],
    "blockers": [],
}


def pass_check(name, detail=""):
    audit["checks"][name] = {
        "status": "PASS",
        "detail": detail,
    }


def warn_check(name, detail=""):
    audit["checks"][name] = {
        "status": "WARN",
        "detail": detail,
    }
    audit["warnings"].append(f"{name}: {detail}")


def fail_check(name, detail=""):
    audit["checks"][name] = {
        "status": "FAIL",
        "detail": detail,
    }
    audit["blockers"].append(f"{name}: {detail}")


def discover(name, value):
    audit["discoveries"][name] = value


def source_hash(path):
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


# =============================================================================
# AST HELPERS
# =============================================================================

def get_source_segment(source, node):
    segment = ast.get_source_segment(source, node)
    return segment if segment is not None else ""


def node_name(node):
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        parts = []
        current = node

        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value

        if isinstance(current, ast.Name):
            parts.append(current.id)

        return ".".join(reversed(parts))

    return ""


def iter_functions(tree):
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield node


def iter_calls(node):
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            yield child


def iter_assignments(node):
    for child in ast.walk(node):
        if isinstance(child, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            yield child


def assignment_targets(node):
    if isinstance(node, ast.Assign):
        targets = node.targets

    elif isinstance(node, ast.AnnAssign):
        targets = [node.target]

    elif isinstance(node, ast.AugAssign):
        targets = [node.target]

    else:
        return []

    result = []

    for target in targets:
        if isinstance(target, ast.Name):
            result.append(target.id)

        elif isinstance(target, (ast.Tuple, ast.List)):
            for element in target.elts:
                if isinstance(element, ast.Name):
                    result.append(element.id)

    return result


# =============================================================================
# DISCOVER SIMILARITY EXPRESSIONS
# =============================================================================

SIMILARITY_KEYWORDS = (
    "similarity",
    "similar",
    "distance",
    "score",
    "match_score",
    "sim_score",
    "retrieval_score",
    "similarity_score",
)


def similarity_related_text(text):
    lower = text.lower()
    return any(word in lower for word in SIMILARITY_KEYWORDS)


def discover_similarity(tree, retrieve_node, source):
    discoveries = []

    # -------------------------------------------------------------------------
    # A. Variables whose names explicitly indicate similarity
    # -------------------------------------------------------------------------
    for node in ast.walk(retrieve_node):

        if isinstance(node, ast.Name):
            if similarity_related_text(node.id):
                discoveries.append({
                    "kind": "name",
                    "name": node.id,
                    "line": getattr(node, "lineno", None),
                })

        elif isinstance(node, ast.Attribute):
            if similarity_related_text(node.attr):
                discoveries.append({
                    "kind": "attribute",
                    "name": node_name(node),
                    "line": getattr(node, "lineno", None),
                })

    # -------------------------------------------------------------------------
    # B. Calls containing similarity-like functions
    # -------------------------------------------------------------------------
    for call in iter_calls(retrieve_node):
        name = node_name(call.func)

        if similarity_related_text(name):
            discoveries.append({
                "kind": "call",
                "name": name,
                "line": getattr(call, "lineno", None),
                "source": get_source_segment(source, call)[:500],
            })

    # -------------------------------------------------------------------------
    # C. Comparisons involving similarity-like names
    # -------------------------------------------------------------------------
    for node in ast.walk(retrieve_node):

        if isinstance(node, ast.Compare):

            segment = get_source_segment(source, node)

            if similarity_related_text(segment):
                discoveries.append({
                    "kind": "comparison",
                    "line": getattr(node, "lineno", None),
                    "source": segment[:500],
                })

    # Deduplicate
    unique = []
    seen = set()

    for item in discoveries:
        key = json.dumps(item, sort_keys=True)

        if key not in seen:
            seen.add(key)
            unique.append(item)

    return unique


# =============================================================================
# DISCOVER CANDIDATE GENERATION
# =============================================================================

def discover_candidate_generation(retrieve_node, source):

    candidates = []

    for node in ast.walk(retrieve_node):

        if isinstance(node, ast.Assign):

            targets = assignment_targets(node)

            if not targets:
                continue

            segment = get_source_segment(source, node)

            lower = segment.lower()

            candidate_words = (
                "candidate",
                "historical",
                "experience",
                "match",
                "retriev",
                "nearest",
                "neighbor",
                "similar",
            )

            if any(word in lower for word in candidate_words):
                candidates.append({
                    "targets": targets,
                    "line": getattr(node, "lineno", None),
                    "source": segment[:1000],
                })

    return candidates


# =============================================================================
# DISCOVER SORTING / RANKING
# =============================================================================

def discover_ranking(retrieve_node, source):

    ranking = []

    for call in iter_calls(retrieve_node):

        name = node_name(call.func)

        if name.endswith(".sort") or name == "sorted":

            segment = get_source_segment(source, call)

            ranking.append({
                "kind": "sort",
                "name": name,
                "line": getattr(call, "lineno", None),
                "source": segment[:1500],
            })

    for node in ast.walk(retrieve_node):

        if isinstance(node, ast.Subscript):

            segment = get_source_segment(source, node)

            if any(
                token in segment
                for token in (
                    "[:",
                    "[0:",
                    "TOP",
                    "top",
                    "k",
                    "K",
                )
            ):

                ranking.append({
                    "kind": "selection",
                    "line": getattr(node, "lineno", None),
                    "source": segment[:1000],
                })

    return ranking


# =============================================================================
# DISCOVER HORIZON REFERENCES
# =============================================================================

def discover_horizons(source, retrieve_node):

    function_text = get_source_segment(source, retrieve_node)

    result = {
        "H4": [],
        "H8": [],
        "H16": [],
    }

    patterns = {
        "H4": [
            r"\bH4\b",
            r"\bh4\b",
            r"4[\s_-]*(?:bar|candle|step|period|horizon)",
            r"4[\s_-]*ahead",
        ],
        "H8": [
            r"\bH8\b",
            r"\bh8\b",
            r"8[\s_-]*(?:bar|candle|step|period|horizon)",
            r"8[\s_-]*ahead",
        ],
        "H16": [
            r"\bH16\b",
            r"\bh16\b",
            r"16[\s_-]*(?:bar|candle|step|period|horizon)",
            r"16[\s_-]*ahead",
        ],
    }

    for horizon, pats in patterns.items():

        for pattern in pats:

            matches = list(
                re.finditer(
                    pattern,
                    function_text,
                    flags=re.IGNORECASE,
                )
            )

            for match in matches:

                line_offset = function_text[:match.start()].count("\n") + 1

                result[horizon].append(
                    line_offset + retrieve_node.lineno - 1
                )

    return result


# =============================================================================
# DISCOVER OUTCOME AGGREGATION
# =============================================================================

def discover_outcome_aggregation(retrieve_node, source):

    results = []

    keywords = (
        "outcome",
        "probability",
        "count",
        "mean",
        "median",
        "distribution",
        "success",
        "failure",
        "mfe",
        "mae",
        "return",
        "future",
        "horizon",
    )

    for node in ast.walk(retrieve_node):

        if isinstance(
            node,
            (
                ast.Assign,
                ast.AnnAssign,
                ast.AugAssign,
                ast.Call,
                ast.Return,
            ),
        ):

            segment = get_source_segment(source, node)

            if any(
                word in segment.lower()
                for word in keywords
            ):

                results.append({
                    "line": getattr(node, "lineno", None),
                    "kind": type(node).__name__,
                    "source": segment[:1200],
                })

    return results


# =============================================================================
# DISCOVER CAUSALITY SIGNALS
# =============================================================================

def discover_causality(retrieve_node, source):

    results = []

    causal_words = (
        "timestamp",
        "index",
        "position",
        "future",
        "lookahead",
        "look_ahead",
        "causal",
        "confirmation",
        "end_idx",
        "target",
        "outcome",
    )

    for node in ast.walk(retrieve_node):

        segment = get_source_segment(source, node)

        if not segment:
            continue

        lower = segment.lower()

        if any(word in lower for word in causal_words):

            results.append({
                "line": getattr(node, "lineno", None),
                "kind": type(node).__name__,
                "source": segment[:900],
            })

    return results


# =============================================================================
# DISCOVER DECISION INTEGRATION
# =============================================================================

def discover_decision_integration(tree, retrieve_node, source):

    retrieve_names = set()

    for node in ast.walk(retrieve_node):

        if isinstance(node, ast.Return):
            segment = get_source_segment(source, node)

            if segment:
                retrieve_names.update(
                    re.findall(
                        r"\b[A-Za-z_][A-Za-z0-9_]*\b",
                        segment,
                    )
                )

    integrations = []

    for function in iter_functions(tree):

        if function is retrieve_node:
            continue

        function_text = get_source_segment(source, function)

        if "retrieve_historical_experience" in function_text:

            integrations.append({
                "function": function.name,
                "line": function.lineno,
                "source": function_text[:1800],
            })

    # Main-module calls as well
    for node in ast.walk(tree):

        if isinstance(node, ast.Call):

            name = node_name(node.func)

            if name.endswith("retrieve_historical_experience"):

                integrations.append({
                    "function": "<module>",
                    "line": getattr(node, "lineno", None),
                    "source": get_source_segment(source, node)[:1200],
                })

    return integrations


# =============================================================================
# DISCOVER DATA STRUCTURE DEFINITIONS
# =============================================================================

def discover_match_classes(tree, source):

    results = []

    for node in tree.body:

        if isinstance(node, ast.ClassDef):

            text = get_source_segment(source, node)

            lower = text.lower()

            if any(
                word in lower
                for word in (
                    "similar",
                    "match",
                    "retriev",
                    "experience",
                    "memory",
                )
            ):

                results.append({
                    "class": node.name,
                    "line": node.lineno,
                    "source": text[:3000],
                })

    return results


# =============================================================================
# DISCOVER RETRIEVAL RETURN CONTRACT
# =============================================================================

def discover_returns(retrieve_node, source):

    results = []

    for node in ast.walk(retrieve_node):

        if isinstance(node, ast.Return):

            segment = get_source_segment(source, node)

            results.append({
                "line": node.lineno,
                "source": segment[:3000],
            })

    return results


# =============================================================================
# TEXT-LEVEL STRUCTURAL PATCH DISCOVERY
#
# IMPORTANT:
# We DO NOT patch similarity representation.
#
# We only patch sparse logic when:
#
#   1. exact old sparse block exists;
#   2. the source itself contains a usable similarity expression;
#   3. the similarity expression can be evaluated from the selected row;
#   4. no ambiguity exists.
# =============================================================================

OLD_SPARSE = """    if (
        len(selected_rows)
        < MIN_RETRIEVAL_MATCHES
    ):

        level = "SPARSE"
"""

OLD_EVIDENCE = """    if (
        len(selected_rows)
        < MIN_RETRIEVAL_MATCHES
    ):

        evidence = "LOW"
"""

OLD_WARNING = """        sparse_warning=(
            len(selected_rows)
            < MIN_RETRIEVAL_MATCHES
        ),
"""


def find_exact_similarity_access(retrieve_text):

    # Strong patterns only.
    patterns = [

        # match.similarity
        r'(?P<obj>[A-Za-z_][A-Za-z0-9_]*)\.similarity\b',

        # match["similarity"]
        r'(?P<obj>[A-Za-z_][A-Za-z0-9_]*)\[\s*["\']similarity["\']\s*\]',

        # getattr(match, "similarity", ...)
        r'getattr\(\s*(?P<obj>[A-Za-z_][A-Za-z0-9_]*)\s*,\s*["\']similarity["\']',

        # dictionary .get("similarity")
        r'(?P<obj>[A-Za-z_][A-Za-z0-9_]*)\.get\(\s*["\']similarity["\']',
    ]

    found = []

    for pattern in patterns:

        for match in re.finditer(
            pattern,
            retrieve_text,
            flags=re.IGNORECASE,
        ):

            found.append({
                "object": match.group("obj"),
                "pattern": pattern,
                "text": match.group(0),
                "offset": match.start(),
            })

    # Deduplicate
    unique = []
    seen = set()

    for item in found:

        key = (
            item["object"],
            item["text"],
        )

        if key not in seen:
            seen.add(key)
            unique.append(item)

    return unique


def verify_similarity_belongs_to_selected_row(
    retrieve_text,
    selected_row_names,
    similarity_access,
):

    if not similarity_access:
        return False, "No explicit similarity field access discovered."

    # We require selected_rows context.
    if "selected_rows" not in retrieve_text:
        return False, "selected_rows is not referenced in retrieval function."

    # If similarity object is "match", this is acceptable only if
    # the selected_rows iteration proves that match comes from selected_rows.
    for access in similarity_access:

        obj = access["object"]

        patterns = [
            rf"for\s+{re.escape(obj)}\s*,",
            rf"for\s+{re.escape(obj)}\s+in\s+selected_rows",
            rf"for\s+{re.escape(obj)}\s*,\s*_[^:]*\s+in\s+selected_rows",
        ]

        for pattern in patterns:

            if re.search(
                pattern,
                retrieve_text,
                flags=re.MULTILINE,
            ):

                return True, (
                    f"Similarity field {access['text']} is evaluated "
                    f"from selected_rows iterator object '{obj}'."
                )

    # More conservative fallback:
    # inspect whether a comprehension explicitly uses selected_rows and
    # the same object appears inside.
    for access in similarity_access:

        obj = access["object"]

        if re.search(
            rf"for\s+{re.escape(obj)}\b.*selected_rows",
            retrieve_text,
            flags=re.DOTALL,
        ):

            return True, (
                f"Similarity object '{obj}' appears bound to selected_rows."
            )

    return False, (
        "Similarity field exists, but the source does not prove that "
        "the accessed object is a selected historical match."
    )


# =============================================================================
# AUTOMATIC PATCH BUILDER
# =============================================================================

def build_safe_sparse_patch(
    source,
    retrieve_text,
    similarity_access,
):

    if OLD_SPARSE not in retrieve_text:
        return None, "Exact original sparse classification block not found."

    if OLD_EVIDENCE not in retrieve_text:
        return None, "Exact original sparse evidence block not found."

    if OLD_WARNING not in retrieve_text:
        return None, "Exact original sparse_warning block not found."

    if len(similarity_access) != 1:
        return None, (
            "Similarity access is ambiguous. "
            f"Discovered {len(similarity_access)} usable similarity accesses."
        )

    access = similarity_access[0]

    obj = access["object"]

    # -------------------------------------------------------------------------
    # We only support a proven selected-row similarity object.
    # -------------------------------------------------------------------------
    similarity_expr = f'{obj}.similarity'

    if ".similarity" not in access["text"].lower():

        return None, (
            "The only safe automatic patch currently supports explicit "
            f"attribute similarity access. Discovered: {access['text']}"
        )

    # -------------------------------------------------------------------------
    # Verify selected_rows iteration before constructing patch.
    # -------------------------------------------------------------------------
    if not re.search(
        rf"for\s+{re.escape(obj)}\s*,",
        retrieve_text,
    ):

        return None, (
            f"Could not prove '{obj}' is the selected historical match "
            "inside the retrieval function."
        )

    new_sparse = f"""    # ============================================================
    # V4.1.8 EFFECTIVE SPARSE RETRIEVAL
    #
    # TOP-K selection does NOT prove that useful historical
    # experiences were found.
    #
    # Count only selected matches whose actual similarity reaches
    # the configured minimum similarity boundary.
    # ============================================================

    effective_sparse_matches = sum(
        1
        for {obj}, _
        in selected_rows
        if float(
            getattr({obj}, "similarity", 0.0)
        ) >= SPARSE_MIN_SIMILARITY
    )

    sparse = (
        effective_sparse_matches
        < SPARSE_MIN_EFFECTIVE_MATCHES
    )

    if sparse:

        level = "SPARSE"
"""

    new_evidence = """    if sparse:

        evidence = "LOW"
"""

    new_warning = """        sparse_warning=sparse,
"""

    modified = retrieve_text.replace(
        OLD_SPARSE,
        new_sparse,
        1,
    )

    modified = modified.replace(
        OLD_EVIDENCE,
        new_evidence,
        1,
    )

    modified = modified.replace(
        OLD_WARNING,
        new_warning,
        1,
    )

    # Ensure old logic is really gone.
    if OLD_SPARSE in modified:
        return None, "Old sparse classification remains after patch."

    if OLD_EVIDENCE in modified:
        return None, "Old sparse evidence logic remains after patch."

    if OLD_WARNING in modified:
        return None, "Old sparse_warning logic remains after patch."

    return modified, (
        "Safe sparse patch constructed using the source-proven "
        f"selected-match similarity object '{obj}'."
    )


# =============================================================================
# REPORT GENERATION
# =============================================================================

def status_symbol(status):

    return {
        "PASS": "PASS",
        "WARN": "WARN",
        "FAIL": "FAIL",
    }.get(status, status)


def create_markdown_report():

    lines = []

    lines.append("# MLAI V4.1.8 Robust Retrieval Audit Report")
    lines.append("")
    lines.append(
        f"Generated: `{audit['timestamp']}`"
    )
    lines.append("")

    lines.append("## Build decision")
    lines.append("")

    if audit["fix_applied"]:
        lines.append("**V4.1.8 BUILD: CREATED AND VALIDATED**")
    else:
        lines.append("**V4.1.8 BUILD: REFUSED / NOT CREATED**")

    lines.append("")

    lines.append("## Protection")
    lines.append("")
    lines.append(
        "- V4.1.7 source is never modified."
    )
    lines.append(
        "- market_data.bin is never modified."
    )
    lines.append(
        "- Existing memory files are never modified."
    )
    lines.append(
        "- Production files are never modified."
    )
    lines.append("")

    lines.append("## Source")
    lines.append("")
    lines.append(f"- Source: `{SRC}`")
    lines.append(f"- Source SHA256: `{audit.get('source_sha256', 'unknown')}`")
    lines.append(
        f"- Source lines: `{audit.get('source_lines', 'unknown')}`"
    )
    lines.append("")

    lines.append("## Audit checks")
    lines.append("")

    for name, result in audit["checks"].items():

        lines.append(
            f"- **{status_symbol(result['status'])}** "
            f"{name}: {result['detail']}"
        )

    lines.append("")

    lines.append("## Discovered architecture")
    lines.append("")

    for name, value in audit["discoveries"].items():

        lines.append(f"### {name}")
        lines.append("")
        lines.append("```text")

        if isinstance(value, str):
            lines.append(value)

        else:
            lines.append(
                json.dumps(
                    value,
                    indent=2,
                    default=str,
                )
            )

        lines.append("```")
        lines.append("")

    lines.append("## Blockers")
    lines.append("")

    if audit["blockers"]:

        for blocker in audit["blockers"]:
            lines.append(f"- {blocker}")

    else:
        lines.append("- None.")

    lines.append("")

    lines.append("## Warnings")
    lines.append("")

    if audit["warnings"]:

        for warning in audit["warnings"]:
            lines.append(f"- {warning}")

    else:
        lines.append("- None.")

    lines.append("")

    lines.append("## Scientific interpretation")
    lines.append("")
    lines.append(
        "This audit distinguishes structural existence from scientific "
        "validity. Finding a similarity calculation or retrieval ranking "
        "does not prove that the representation discriminates useful "
        "historical states. Predictive discrimination, calibration, "
        "generalization and incremental value require empirical evaluation "
        "on chronologically separated data."
    )
    lines.append("")

    lines.append(
        "Therefore this builder will not manufacture claims of H4/H8/H16 "
        "predictive validity merely because corresponding variables or "
        "labels exist in the source."
    )
    lines.append("")

    return "\n".join(lines)


# =============================================================================
# MAIN AUDIT
# =============================================================================

print("=" * 100)
print("MLAI V4.1.8 ROBUST AUDIT + FIX BUILDER")
print("=" * 100)
print()

# -----------------------------------------------------------------------------
# 1. Source existence
# -----------------------------------------------------------------------------

if not SRC.exists():

    fail_check(
        "Source exists",
        f"{SRC} was not found."
    )

    REPORT.write_text(
        create_markdown_report(),
        encoding="utf-8",
    )

    raise SystemExit(
        f"ERROR: {SRC} not found."
    )

pass_check(
    "Source exists",
    f"Found {SRC}."
)

audit["source_sha256"] = source_hash(SRC)

source = SRC.read_text(
    encoding="utf-8"
)

audit["source_lines"] = len(
    source.splitlines()
)

# -----------------------------------------------------------------------------
# 2. Version verification
# -----------------------------------------------------------------------------

if 'VERSION = "4.1.7"' not in source:

    fail_check(
        "V4.1.7 version",
        'VERSION = "4.1.7" was not found.'
    )

else:

    pass_check(
        "V4.1.7 version",
        'VERSION = "4.1.7" confirmed.'
    )

# -----------------------------------------------------------------------------
# 3. AST parse
# -----------------------------------------------------------------------------

try:

    tree = ast.parse(
        source,
        filename=str(SRC),
    )

    pass_check(
        "Python AST validation",
        "V4.1.7 parses successfully."
    )

except SyntaxError as exc:

    fail_check(
        "Python AST validation",
        str(exc)
    )

    REPORT.write_text(
        create_markdown_report(),
        encoding="utf-8",
    )

    raise SystemExit(
        "ERROR: V4.1.7 is not syntactically valid."
    )

# -----------------------------------------------------------------------------
# 4. Locate retrieval function
# -----------------------------------------------------------------------------

retrieve_nodes = [
    node
    for node in tree.body
    if isinstance(
        node,
        (
            ast.FunctionDef,
            ast.AsyncFunctionDef,
        ),
    )
    and node.name == "retrieve_historical_experience"
]

if len(retrieve_nodes) != 1:

    fail_check(
        "Retrieval function uniqueness",
        (
            "Expected exactly one retrieve_historical_experience(); "
            f"found {len(retrieve_nodes)}."
        ),
    )

    REPORT.write_text(
        create_markdown_report(),
        encoding="utf-8",
    )

    raise SystemExit(
        "ERROR: Retrieval function is not uniquely identifiable."
    )

retrieve_node = retrieve_nodes[0]

pass_check(
    "Retrieval function uniqueness",
    (
        "Exactly one retrieve_historical_experience() found at "
        f"lines {retrieve_node.lineno}-{retrieve_node.end_lineno}."
    )
)

retrieve_text = get_source_segment(
    source,
    retrieve_node,
)

discover(
    "retrieval_function_lines",
    f"{retrieve_node.lineno}-{retrieve_node.end_lineno}"
)

discover(
    "retrieval_function_size",
    len(retrieve_text.splitlines())
)

print(
    f"Retrieval function : lines "
    f"{retrieve_node.lineno}-{retrieve_node.end_lineno}"
)

print()

# -----------------------------------------------------------------------------
# 5. Discover similarity
# -----------------------------------------------------------------------------

similarity_discovery = discover_similarity(
    tree,
    retrieve_node,
    source,
)

discover(
    "similarity_discovery",
    similarity_discovery[:100]
)

if similarity_discovery:

    pass_check(
        "Similarity-related representation",
        (
            f"Found {len(similarity_discovery)} similarity-related "
            "AST/source references."
        ),
    )

else:

    fail_check(
        "Similarity-related representation",
        "No similarity-related representation was discovered."
    )

# -----------------------------------------------------------------------------
# 6. Find exact usable similarity access
# -----------------------------------------------------------------------------

similarity_access = find_exact_similarity_access(
    retrieve_text
)

discover(
    "exact_similarity_access",
    similarity_access
)

if similarity_access:

    if len(similarity_access) == 1:

        pass_check(
            "Exact similarity field access",
            (
                "Exactly one explicit similarity access was found: "
                f"{similarity_access[0]['text']}"
            ),
        )

    else:

        warn_check(
            "Exact similarity field access",
            (
                "Multiple similarity accesses were found. "
                "Automatic repair will not guess which one is authoritative."
            ),
        )

else:

    fail_check(
        "Exact similarity field access",
        (
            "No explicit selected-match similarity field such as "
            "match.similarity, match['similarity'], or equivalent "
            "was discovered."
        ),
    )

# -----------------------------------------------------------------------------
# 7. Verify similarity belongs to selected historical match
# -----------------------------------------------------------------------------

similarity_bound, similarity_reason = (
    verify_similarity_belongs_to_selected_row(
        retrieve_text,
        set(),
        similarity_access,
    )
)

discover(
    "similarity_binding",
    similarity_reason
)

if similarity_bound:

    pass_check(
        "Similarity-to-selected-row binding",
        similarity_reason
    )

else:

    fail_check(
        "Similarity-to-selected-row binding",
        similarity_reason
    )

# -----------------------------------------------------------------------------
# 8. Candidate generation
# -----------------------------------------------------------------------------

candidate_generation = discover_candidate_generation(
    retrieve_node,
    source,
)

discover(
    "candidate_generation",
    candidate_generation[:100]
)

if candidate_generation:

    pass_check(
        "Historical candidate generation",
        f"Found {len(candidate_generation)} candidate-related assignments."
    )

else:

    warn_check(
        "Historical candidate generation",
        "No clearly identifiable candidate-generation assignment was found."
    )

# -----------------------------------------------------------------------------
# 9. Ranking
# -----------------------------------------------------------------------------

ranking = discover_ranking(
    retrieve_node,
    source,
)

discover(
    "ranking",
    ranking[:100]
)

if ranking:

    pass_check(
        "Retrieval ranking/selection",
        f"Found {len(ranking)} sorting/selection structures."
    )

else:

    fail_check(
        "Retrieval ranking/selection",
        "No explicit sorting/selection structure was discovered."
    )

# -----------------------------------------------------------------------------
# 10. Sparse logic
# -----------------------------------------------------------------------------

if OLD_SPARSE in retrieve_text:

    pass_check(
        "Existing sparse classification",
        "Original TOP-K sparse classification block found."
    )

else:

    warn_check(
        "Existing sparse classification",
        "Original TOP-K sparse classification block not found."
    )

if OLD_EVIDENCE in retrieve_text:

    pass_check(
        "Existing sparse evidence",
        "Original TOP-K sparse evidence block found."
    )

else:

    warn_check(
        "Existing sparse evidence",
        "Original TOP-K sparse evidence block not found."
    )

if OLD_WARNING in retrieve_text:

    pass_check(
        "Existing sparse_warning",
        "Original TOP-K sparse_warning block found."
    )

else:

    warn_check(
        "Existing sparse_warning",
        "Original TOP-K sparse_warning block not found."
    )

# -----------------------------------------------------------------------------
# 11. H4/H8/H16
# -----------------------------------------------------------------------------

horizons = discover_horizons(
    source,
    retrieve_node,
)

discover(
    "horizons",
    horizons
)

for horizon in ("H4", "H8", "H16"):

    if horizons[horizon]:

        pass_check(
            f"{horizon} structural reference",
            (
                f"Found {len(horizons[horizon])} reference(s) "
                f"to {horizon}."
            ),
        )

    else:

        warn_check(
            f"{horizon} structural reference",
            f"No explicit {horizon} reference inside retrieval function."
        )

# -----------------------------------------------------------------------------
# 12. Outcome aggregation
# -----------------------------------------------------------------------------

outcomes = discover_outcome_aggregation(
    retrieve_node,
    source,
)

discover(
    "outcome_aggregation",
    outcomes[:100]
)

if outcomes:

    pass_check(
        "Outcome aggregation",
        f"Found {len(outcomes)} outcome-related structures."
    )

else:

    warn_check(
        "Outcome aggregation",
        "No obvious outcome aggregation was found inside retrieval."
    )

# -----------------------------------------------------------------------------
# 13. Causality
# -----------------------------------------------------------------------------

causality = discover_causality(
    retrieve_node,
    source,
)

discover(
    "causality_signals",
    causality[:100]
)

if causality:

    warn_check(
        "Causality screen",
        (
            "Causality-related constructs were found, but AST discovery "
            "alone cannot prove that no future information enters retrieval."
        ),
    )

else:

    fail_check(
        "Causality screen",
        "No obvious causal-boundary constructs were found."
    )

# -----------------------------------------------------------------------------
# 14. Decision integration
# -----------------------------------------------------------------------------

decision_integration = discover_decision_integration(
    tree,
    retrieve_node,
    source,
)

discover(
    "decision_integration",
    decision_integration[:100]
)

if decision_integration:

    pass_check(
        "Predictive decision integration",
        (
            f"Found {len(decision_integration)} integration "
            "reference(s)."
        ),
    )

else:

    warn_check(
        "Predictive decision integration",
        (
            "No clear downstream decision/inference integration was "
            "identified."
        ),
    )

# -----------------------------------------------------------------------------
# 15. Match / memory classes
# -----------------------------------------------------------------------------

match_classes = discover_match_classes(
    tree,
    source,
)

discover(
    "match_memory_classes",
    match_classes
)

# -----------------------------------------------------------------------------
# 16. Retrieval return contract
# -----------------------------------------------------------------------------

returns = discover_returns(
    retrieve_node,
    source,
)

discover(
    "retrieval_returns",
    returns
)

if returns:

    pass_check(
        "Retrieval return contract",
        f"Found {len(returns)} return statement(s)."
    )

else:

    fail_check(
        "Retrieval return contract",
        "No return statement found."
    )

# -----------------------------------------------------------------------------
# 17. Determine whether safe automatic repair is possible
# -----------------------------------------------------------------------------

safe_patch_reason = None
patched_retrieve_text = None

# Strong safety requirement:
# We must have:
#
#   - exact sparse block
#   - exact similarity field
#   - exact binding of similarity to selected match
#
if (
    OLD_SPARSE in retrieve_text
    and OLD_EVIDENCE in retrieve_text
    and OLD_WARNING in retrieve_text
    and len(similarity_access) == 1
    and similarity_bound
):

    patched_retrieve_text, safe_patch_reason = (
        build_safe_sparse_patch(
            source,
            retrieve_text,
            similarity_access,
        )
    )

    if patched_retrieve_text is not None:

        audit["safe_to_modify"] = True

        pass_check(
            "Automatic sparse repair safety",
            safe_patch_reason
        )

    else:

        fail_check(
            "Automatic sparse repair safety",
            safe_patch_reason
        )

else:

    fail_check(
        "Automatic sparse repair safety",
        (
            "Automatic repair is refused because the source does not "
            "simultaneously prove the exact sparse blocks and an "
            "unambiguous similarity field bound to selected historical "
            "matches."
        )
    )

# -----------------------------------------------------------------------------
# 18. Construct complete candidate V4.1.8 only if safe
# -----------------------------------------------------------------------------

if audit["safe_to_modify"]:

    lines = source.splitlines(
        keepends=True
    )

    prefix = "".join(
        lines[:retrieve_node.lineno - 1]
    )

    suffix = "".join(
        lines[retrieve_node.end_lineno:]
    )

    candidate_source = (
        prefix
        + patched_retrieve_text
        + suffix
    )

    # -------------------------------------------------------------------------
    # Add configuration only after exact anchor is proven.
    # -------------------------------------------------------------------------

    CONFIG_ANCHOR = "MIN_RETRIEVAL_MATCHES = 8"

    if CONFIG_ANCHOR not in candidate_source:

        audit["safe_to_modify"] = False

        fail_check(
            "Sparse configuration anchor",
            "MIN_RETRIEVAL_MATCHES = 8 was not found."
        )

    elif "SPARSE_MIN_SIMILARITY" in candidate_source:

        audit["safe_to_modify"] = False

        fail_check(
            "Sparse configuration uniqueness",
            (
                "SPARSE_MIN_SIMILARITY already exists. "
                "Refusing to stack another patch."
            )
        )

    else:

        config = """MIN_RETRIEVAL_MATCHES = 8

# ================================================================
# V4.1.8 ROBUST EFFECTIVE-SPARSE RETRIEVAL
#
# TOP-K count is not treated as sufficient historical evidence.
#
# A selected historical experience is considered effective only
# when its actual similarity reaches this threshold.
# ================================================================

SPARSE_MIN_SIMILARITY = 0.60

SPARSE_MIN_EFFECTIVE_MATCHES = MIN_RETRIEVAL_MATCHES
"""

        candidate_source = candidate_source.replace(
            CONFIG_ANCHOR,
            config,
            1,
        )

    # -------------------------------------------------------------------------
    # Version
    # -------------------------------------------------------------------------

    candidate_source = candidate_source.replace(
        'VERSION = "4.1.7"',
        'VERSION = "4.1.8"',
        1,
    )

    candidate_source = candidate_source.replace(
        "V4.1.7",
        "V4.1.8",
    )

    candidate_source = candidate_source.replace(
        "v4.1.7",
        "v4.1.8",
    )

    # -------------------------------------------------------------------------
    # Output artifact names
    # -------------------------------------------------------------------------

    candidate_source = candidate_source.replace(
        "MLAI_V417_ROBUST_HISTORICAL_EXPERIENCE_RETRIEVAL.bin",
        "MLAI_V418_ROBUST_HISTORICAL_EXPERIENCE_RETRIEVAL.bin",
    )

    candidate_source = candidate_source.replace(
        "MLAI_V417_ROBUST_HISTORICAL_EXPERIENCE_RETRIEVAL_REPORT.md",
        "MLAI_V418_ROBUST_HISTORICAL_EXPERIENCE_RETRIEVAL_REPORT.md",
    )

    # -------------------------------------------------------------------------
    # Full AST validation
    # -------------------------------------------------------------------------

    try:

        candidate_tree = ast.parse(
            candidate_source,
            filename=str(DST),
        )

        pass_check(
            "Generated V4.1.8 AST validation",
            "Generated source parses successfully."
        )

    except SyntaxError as exc:

        audit["safe_to_modify"] = False

        fail_check(
            "Generated V4.1.8 AST validation",
            str(exc)
        )

        candidate_source = None

    # -------------------------------------------------------------------------
    # Structural verification
    # -------------------------------------------------------------------------

    if candidate_source is not None:

        required = [
            'VERSION = "4.1.8"',
            "SPARSE_MIN_SIMILARITY = 0.60",
            "SPARSE_MIN_EFFECTIVE_MATCHES = MIN_RETRIEVAL_MATCHES",
            "effective_sparse_matches = sum(",
            "sparse = (",
            "sparse_warning=sparse",
        ]

        missing = [
            item
            for item in required
            if item not in candidate_source
        ]

        if missing:

            audit["safe_to_modify"] = False

            fail_check(
                "Generated V4.1.8 structural validation",
                "Missing: " + ", ".join(missing)
            )

        else:

            pass_check(
                "Generated V4.1.8 structural validation",
                "All required V4.1.8 structures are present."
            )

    # -------------------------------------------------------------------------
    # Reparse retrieval function and verify old blocks are gone.
    # -------------------------------------------------------------------------

    if candidate_source is not None:

        new_tree = ast.parse(
            candidate_source,
            filename=str(DST),
        )

        new_retrieval_nodes = [
            node
            for node in new_tree.body
            if isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                ),
            )
            and node.name == "retrieve_historical_experience"
        ]

        if len(new_retrieval_nodes) != 1:

            audit["safe_to_modify"] = False

            fail_check(
                "Generated retrieval function uniqueness",
                (
                    "Expected exactly one retrieval function after patch; "
                    f"found {len(new_retrieval_nodes)}."
                ),
            )

        else:

            new_retrieval = new_retrieval_nodes[0]

            new_retrieval_text = get_source_segment(
                candidate_source,
                new_retrieval,
            )

            old_remaining = []

            if OLD_SPARSE in new_retrieval_text:
                old_remaining.append(
                    "old sparse classification"
                )

            if OLD_EVIDENCE in new_retrieval_text:
                old_remaining.append(
                    "old sparse evidence"
                )

            if OLD_WARNING in new_retrieval_text:
                old_remaining.append(
                    "old sparse_warning"
                )

            if old_remaining:

                audit["safe_to_modify"] = False

                fail_check(
                    "Old sparse logic removal",
                    (
                        "Old logic remains: "
                        + ", ".join(old_remaining)
                    ),
                )

            else:

                pass_check(
                    "Old sparse logic removal",
                    "All three old TOP-K-only sparse blocks are removed."
                )

# =============================================================================
# FINAL WRITE
# =============================================================================

if audit["safe_to_modify"]:

    # -------------------------------------------------------------------------
    # Protect original V4.1.7 with a byte-for-byte backup.
    # -------------------------------------------------------------------------

    if not BACKUP.exists():

        shutil.copy2(
            SRC,
            BACKUP,
        )

    # -------------------------------------------------------------------------
    # Verify backup hash matches source.
    # -------------------------------------------------------------------------

    if source_hash(BACKUP) != audit["source_sha256"]:

        audit["safe_to_modify"] = False

        fail_check(
            "V4.1.7 backup integrity",
            "Backup hash does not match original V4.1.7."
        )

    else:

        pass_check(
            "V4.1.7 backup integrity",
            "Backup is byte-for-byte identical to V4.1.7."
        )

# -----------------------------------------------------------------------------
# Write only after every safety check.
# -----------------------------------------------------------------------------

if audit["safe_to_modify"] and candidate_source is not None:

    DST.write_text(
        candidate_source,
        encoding="utf-8",
    )

    audit["fix_applied"] = True

    pass_check(
        "V4.1.8 file creation",
        f"Created {DST}."
    )

else:

    audit["fix_applied"] = False

    if "V4.1.8 file creation" not in audit["checks"]:

        warn_check(
            "V4.1.8 file creation",
            "BUILD REFUSED. No V4.1.8 file was created."
        )


# =============================================================================
# SAVE JSON REPORT
# =============================================================================

JSON_REPORT.write_text(
    json.dumps(
        audit,
        indent=2,
        default=str,
    ),
    encoding="utf-8",
)

# =============================================================================
# SAVE MARKDOWN REPORT
# =============================================================================

REPORT.write_text(
    create_markdown_report(),
    encoding="utf-8",
)


# =============================================================================
# FINAL CONSOLE OUTPUT
# =============================================================================

print()
print("=" * 100)
print("FINAL AUDIT RESULT")
print("=" * 100)
print()

print(
    "Safe automatic fix possible :",
    "YES" if audit["safe_to_modify"] else "NO",
)

print(
    "Fix applied                 :",
    "YES" if audit["fix_applied"] else "NO",
)

print()

print("FILES")
print("-----")
print("Audit report :", REPORT)

if JSON_REPORT.exists():
    print("JSON report  :", JSON_REPORT)

if audit["fix_applied"]:
    print("V4.1.8       :", DST)
    print("V4.1.7 backup:", BACKUP)
else:
    print("V4.1.8       : NOT CREATED")

print()

print("PROTECTION")
print("----------")
print("V4.1.7          : NOT MODIFIED")
print("market_data.bin  : NOT MODIFIED")
print("Memory           : NOT MODIFIED")
print("Production       : NOT MODIFIED")

print()

if audit["fix_applied"]:

    print("=" * 100)
    print("RESULT: V4.1.8 BUILD CREATED AND STRUCTURALLY VALIDATED")
    print("=" * 100)
    print()
    print("IMPORTANT:")
    print(
        "Structural validation does NOT yet prove predictive "
        "discrimination, calibration, or generalization."
    )
    print()
    print("NEXT COMMAND ONLY:")
    print("python .\\mlai_market_structure_v418.py")

else:

    print("=" * 100)
    print("RESULT: BUILD REFUSED SAFELY")
    print("=" * 100)
    print()
    print(
        "The source did not provide enough structural evidence for "
        "a safe automatic repair."
    )
    print()
    print(
        "Read the generated audit report before any further modification."
    )

print()
print("=" * 100)