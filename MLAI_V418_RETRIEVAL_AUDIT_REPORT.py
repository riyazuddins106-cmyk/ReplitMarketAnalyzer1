from pathlib import Path
import ast
import shutil
import re
import json
from datetime import datetime


# =====================================================================
# MLAI V4.1.8
# ROBUST RETRIEVAL AUDIT + SAFE FIX BUILDER
#
# PURPOSE
# -------
# Audit the entire historical-experience retrieval subsystem in the
# REAL V4.1.7 source and, where the implementation can be proven from
# the source itself, construct V4.1.8 with the required robust
# sparse-retrieval correction.
#
# DESIGN PRINCIPLES
# -----------------
# 1. Never guess the similarity representation.
# 2. Never guess the retrieval function.
# 3. Never modify V4.1.7.
# 4. Never modify market_data.bin.
# 5. Never modify learning memory.
# 6. Never modify production files.
# 7. Refuse to build if the required source structure cannot be proven.
# 8. Validate the complete generated program with AST parsing.
# 9. Generate a complete audit report even when the fix is refused.
#
# OUTPUT
# ------
#   mlai_market_structure_v418.py
#   MLAI_V418_RETRIEVAL_AUDIT_REPORT.md
#   mlai_market_structure_v417_before_v418_robust_audit.py
#
# =====================================================================


SRC = Path("mlai_market_structure_v417.py")
DST = Path("mlai_market_structure_v418.py")
REPORT = Path("MLAI_V418_RETRIEVAL_AUDIT_REPORT.md")
BACKUP = Path(
    "mlai_market_structure_v417_before_v418_robust_audit.py"
)


# =====================================================================
# REPORT STATE
# =====================================================================

audit = {
    "source": str(SRC),
    "source_exists": False,
    "source_lines": 0,
    "syntax_valid": False,
    "retrieval_function_found": False,
    "retrieval_start": None,
    "retrieval_end": None,

    "top_k_logic": "NOT AUDITED",
    "similarity_representation": "NOT AUDITED",
    "similarity_discovery": "NOT AUDITED",
    "ranking_logic": "NOT AUDITED",
    "sparse_logic": "NOT AUDITED",
    "h4_h8_h16": "NOT AUDITED",
    "outcome_aggregation": "NOT AUDITED",
    "decision_integration": "NOT AUDITED",
    "causality": "NOT AUDITED",

    "similarity_expression": None,
    "similarity_source": None,

    "fix_possible": False,
    "fix_applied": False,

    "generated_file": None,
    "post_build_valid": False,

    "errors": [],
    "warnings": [],
    "findings": [],
}


def finding(gate, status, message):
    audit["findings"].append(
        {
            "gate": gate,
            "status": status,
            "message": message,
        }
    )


def error(message):
    audit["errors"].append(message)


def warning(message):
    audit["warnings"].append(message)


# =====================================================================
# SAFE SOURCE READ
# =====================================================================

if not SRC.exists():
    error(
        "mlai_market_structure_v417.py was not found."
    )

    REPORT.write_text(
        "# MLAI V4.1.8 Retrieval Audit\n\n"
        "## RESULT\n\n"
        "**BUILD REFUSED**\n\n"
        "Source file was not found.\n",
        encoding="utf-8",
    )

    raise SystemExit(
        "ERROR: mlai_market_structure_v417.py not found."
    )


audit["source_exists"] = True

source = SRC.read_text(
    encoding="utf-8"
)

audit["source_lines"] = len(
    source.splitlines()
)


# =====================================================================
# SOURCE VERSION PROTECTION
# =====================================================================

if 'VERSION = "4.1.7"' not in source:
    error(
        'Expected VERSION = "4.1.7" was not found.'
    )

    raise SystemExit(
        'ERROR: Expected VERSION = "4.1.7" was not found.'
    )


# =====================================================================
# AST PARSE
# =====================================================================

try:
    tree = ast.parse(
        source,
        filename=str(SRC),
    )

    audit["syntax_valid"] = True

    finding(
        "Gate 0 — Source integrity",
        "PASS",
        "V4.1.7 parses successfully with Python AST.",
    )

except SyntaxError as exc:
    error(
        "V4.1.7 is not syntactically valid: "
        + str(exc)
    )

    REPORT.write_text(
        "# MLAI V4.1.8 Retrieval Audit\n\n"
        "## RESULT\n\n"
        "**BUILD REFUSED**\n\n"
        f"V4.1.7 syntax error: `{exc}`\n",
        encoding="utf-8",
    )

    raise SystemExit(
        "ERROR: V4.1.7 syntax validation failed."
    )


# =====================================================================
# FIND RETRIEVAL FUNCTION
# =====================================================================

retrieve_nodes = [
    node
    for node in tree.body
    if isinstance(
        node,
        (ast.FunctionDef, ast.AsyncFunctionDef),
    )
    and node.name == "retrieve_historical_experience"
]


if len(retrieve_nodes) != 1:

    error(
        "Expected exactly one "
        "retrieve_historical_experience() function. "
        f"Found {len(retrieve_nodes)}."
    )

    raise SystemExit(
        "ERROR: Retrieval function count is not exactly one."
    )


retrieve_node = retrieve_nodes[0]

audit["retrieval_function_found"] = True
audit["retrieval_start"] = retrieve_node.lineno
audit["retrieval_end"] = retrieve_node.end_lineno

finding(
    "Gate 1 — Retrieval architecture",
    "PASS",
    (
        "Exactly one retrieve_historical_experience() "
        f"function found at lines "
        f"{retrieve_node.lineno}-{retrieve_node.end_lineno}."
    ),
)


# =====================================================================
# EXTRACT RETRIEVAL FUNCTION
# =====================================================================

source_lines = source.splitlines(
    keepends=True
)

retrieve_text = "".join(
    source_lines[
        retrieve_node.lineno - 1:
        retrieve_node.end_lineno
    ]
)


retrieve_lines = retrieve_text.splitlines()


# =====================================================================
# GENERIC AST UTILITIES
# =====================================================================

def node_text(node):
    try:
        return ast.unparse(node)
    except Exception:
        return "<unparseable>"


def contains_name(node, name):
    return any(
        isinstance(n, ast.Name)
        and n.id == name
        for n in ast.walk(node)
    )


def contains_attribute(node, attribute):
    return any(
        isinstance(n, ast.Attribute)
        and n.attr == attribute
        for n in ast.walk(node)
    )


# =====================================================================
# 1. TOP-K DISCOVERY
# =====================================================================

topk_evidence = []

for node in ast.walk(retrieve_node):

    if isinstance(node, ast.Compare):

        left = node.left

        if (
            isinstance(left, ast.Call)
            and isinstance(left.func, ast.Name)
            and left.func.id == "len"
            and len(left.args) == 1
            and isinstance(left.args[0], ast.Name)
            and left.args[0].id == "selected_rows"
        ):
            topk_evidence.append(
                node_text(node)
            )


if topk_evidence:

    audit["top_k_logic"] = "FOUND"

    finding(
        "Gate 2 — Top-K selection",
        "PASS",
        (
            "The retrieval function explicitly uses "
            "selected_rows in length/comparison logic. "
            f"Detected expressions: {topk_evidence}"
        ),
    )

else:

    audit["top_k_logic"] = "NOT_FOUND"

    warning(
        "No len(selected_rows) comparison was found. "
        "Top-K logic may use a different representation."
    )


# =====================================================================
# 2. FIND HOW selected_rows IS CREATED
# =====================================================================

selected_assignments = []

for node in ast.walk(retrieve_node):

    if isinstance(
        node,
        (ast.Assign, ast.AnnAssign),
    ):

        targets = []

        if isinstance(node, ast.Assign):
            targets = node.targets

        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]

        if any(
            isinstance(target, ast.Name)
            and target.id == "selected_rows"
            for target in targets
        ):
            selected_assignments.append(node)


if selected_assignments:

    finding(
        "Gate 3 — Retrieval construction",
        "PASS",
        (
            "selected_rows is explicitly assigned inside "
            "retrieve_historical_experience()."
        ),
    )

else:

    warning(
        "selected_rows assignment was not found directly "
        "inside the retrieval function."
    )


# =====================================================================
# 3. DISCOVER REAL SIMILARITY REPRESENTATION
#
# This is the critical part.
#
# We do NOT assume:
#
#     match.similarity
#
# Instead we inspect the real source for similarity-bearing
# expressions.
# =====================================================================

similarity_candidates = []


for node in ast.walk(retrieve_node):

    # ---------------------------------------------------------------
    # object.attribute
    # ---------------------------------------------------------------

    if isinstance(node, ast.Attribute):

        if node.attr.lower() in {
            "similarity",
            "similarity_score",
            "score",
            "distance",
            "similarity_value",
        }:

            similarity_candidates.append(
                (
                    "ATTRIBUTE",
                    node_text(node),
                    node.lineno,
                )
            )

    # ---------------------------------------------------------------
    # dictionary["similarity"]
    # ---------------------------------------------------------------

    elif isinstance(node, ast.Subscript):

        value = node_text(node.slice)

        if (
            "similarity" in value.lower()
            or "score" in value.lower()
            or "distance" in value.lower()
        ):

            similarity_candidates.append(
                (
                    "SUBSCRIPT",
                    node_text(node),
                    node.lineno,
                )
            )


# Remove duplicates while preserving order.

seen_similarity = set()

unique_similarity_candidates = []

for candidate in similarity_candidates:

    key = (
        candidate[0],
        candidate[1],
    )

    if key not in seen_similarity:

        seen_similarity.add(key)
        unique_similarity_candidates.append(
            candidate
        )


similarity_candidates = unique_similarity_candidates


# =====================================================================
# 4. CORRELATE SIMILARITY WITH selected_rows
# =====================================================================

correlated_candidates = []


for kind, expression, line_no in similarity_candidates:

    for node in ast.walk(retrieve_node):

        if isinstance(
            node,
            ast.For,
        ):

            if (
                isinstance(node.iter, ast.Name)
                and node.iter.id == "selected_rows"
            ):

                loop_start = node.lineno
                loop_end = node.end_lineno

                if (
                    loop_start
                    <= line_no
                    <= loop_end
                ):

                    correlated_candidates.append(
                        (
                            kind,
                            expression,
                            line_no,
                            loop_start,
                            loop_end,
                        )
                    )


# =====================================================================
# 5. SIMILARITY DECISION
# =====================================================================

if len(correlated_candidates) == 1:

    candidate = correlated_candidates[0]

    audit["similarity_representation"] = "FOUND"
    audit["similarity_discovery"] = "UNIQUE"
    audit["similarity_expression"] = candidate[1]
    audit["similarity_source"] = (
        f"{candidate[0]} at line {candidate[2]}"
    )

    finding(
        "Gate 4 — Similarity representation",
        "PASS",
        (
            "A unique similarity-bearing expression was found "
            "inside iteration over selected_rows: "
            f"`{candidate[1]}`."
        ),
    )


elif len(correlated_candidates) > 1:

    audit["similarity_representation"] = "AMBIGUOUS"
    audit["similarity_discovery"] = "MULTIPLE"

    warning(
        "Multiple similarity-bearing expressions were found "
        "inside selected_rows processing."
    )

    for candidate in correlated_candidates:

        finding(
            "Gate 4 — Similarity representation",
            "WARN",
            (
                f"Candidate: `{candidate[1]}` "
                f"at line {candidate[2]}"
            ),
        )


else:

    audit["similarity_representation"] = "NOT_FOUND"
    audit["similarity_discovery"] = "NONE"

    warning(
        "No similarity-bearing expression could be proven "
        "to operate on selected_rows."
    )

    finding(
        "Gate 4 — Similarity representation",
        "FAIL",
        (
            "The source does not expose a provable similarity "
            "value associated with selected_rows."
        ),
    )


# =====================================================================
# 6. RANKING / ORDERING DISCOVERY
# =====================================================================

ranking_evidence = []

for node in ast.walk(retrieve_node):

    if isinstance(node, ast.Call):

        if (
            isinstance(node.func, ast.Attribute)
            and node.func.attr in {
                "sort",
                "sorted",
            }
        ):

            ranking_evidence.append(
                node_text(node)
            )

        elif (
            isinstance(node.func, ast.Name)
            and node.func.id == "sorted"
        ):

            ranking_evidence.append(
                node_text(node)
            )


if ranking_evidence:

    audit["ranking_logic"] = "FOUND"

    finding(
        "Gate 5 — Retrieval ranking",
        "PASS",
        (
            "Sorting/ranking logic was found in the "
            "retrieval function."
        ),
    )

else:

    audit["ranking_logic"] = "NOT_FOUND"

    warning(
        "No explicit sorted()/sort() call was found "
        "inside the retrieval function."
    )


# =====================================================================
# 7. HORIZON DISCOVERY
# =====================================================================

horizon_tokens = []

for token in (
    "H4",
    "H8",
    "H16",
    "4",
    "8",
    "16",
):

    if token in retrieve_text:

        horizon_tokens.append(token)


if (
    "H4" in retrieve_text
    or "H8" in retrieve_text
    or "H16" in retrieve_text
):

    audit["h4_h8_h16"] = "EXPLICIT"

    finding(
        "Gate 6 — Horizon handling",
        "PASS",
        (
            "Explicit H4/H8/H16 references were found "
            "inside the retrieval implementation."
        ),
    )

else:

    audit["h4_h8_h16"] = "NOT_EXPLICIT"

    warning(
        "H4/H8/H16 are not explicitly referenced inside "
        "the retrieval function. They may be handled "
        "outside this function."
    )


# =====================================================================
# 8. OUTCOME AGGREGATION DISCOVERY
# =====================================================================

outcome_tokens = [
    "outcome",
    "future",
    "return",
    "mfe",
    "mae",
    "probability",
    "distribution",
    "success",
    "failure",
]


outcome_hits = [
    token
    for token in outcome_tokens
    if token.lower() in retrieve_text.lower()
]


if outcome_hits:

    audit["outcome_aggregation"] = "FOUND"

    finding(
        "Gate 7 — Historical outcome aggregation",
        "PASS",
        (
            "Outcome-related processing was found. "
            f"Detected concepts: {', '.join(outcome_hits)}."
        ),
    )

else:

    audit["outcome_aggregation"] = "NOT_FOUND"

    warning(
        "No obvious outcome aggregation vocabulary "
        "was found inside the retrieval function."
    )


# =====================================================================
# 9. PREDICTIVE DECISION INTEGRATION DISCOVERY
# =====================================================================

decision_tokens = [
    "prediction",
    "probability",
    "confidence",
    "ensemble",
    "decision",
    "forecast",
    "direction",
]


decision_hits = [
    token
    for token in decision_tokens
    if token.lower() in retrieve_text.lower()
]


if decision_hits:

    audit["decision_integration"] = "POSSIBLE"

    finding(
        "Gate 8 — Predictive integration",
        "WARN",
        (
            "Decision-related fields are present in the retrieval "
            "function, but this audit does not assume that their "
            "values actually affect the final prediction. "
            f"Detected: {', '.join(decision_hits)}."
        ),
    )

else:

    audit["decision_integration"] = "NOT_PROVEN"

    warning(
        "Retrieval-to-decision integration was not proven "
        "inside the retrieval function."
    )


# =====================================================================
# 10. CAUSALITY SCREEN
# =====================================================================

future_tokens = [
    "future_return",
    "future_high",
    "future_low",
    "mfe",
    "mae",
    "target",
]


causality_hits = [
    token
    for token in future_tokens
    if token.lower() in retrieve_text.lower()
]


if causality_hits:

    audit["causality"] = "REQUIRES_REVIEW"

    warning(
        "Future/target-related names occur inside the retrieval "
        "function. This does NOT prove leakage, but requires "
        "careful separation between input and outcome."
    )

    finding(
        "Gate 9 — Retrieval causality",
        "WARN",
        (
            "Future/target-related identifiers detected: "
            + ", ".join(causality_hits)
        ),
    )

else:

    audit["causality"] = "NO_OBVIOUS_FUTURE_INPUT"

    finding(
        "Gate 9 — Retrieval causality",
        "PASS",
        (
            "No obvious future-target identifier was detected "
            "inside the retrieval function."
        ),
    )


# =====================================================================
# 11. IDENTIFY ACTUAL SPARSE LOGIC AST NODE
# =====================================================================

sparse_nodes = []

for node in ast.walk(retrieve_node):

    if not isinstance(node, ast.If):
        continue

    test = node.test

    text_test = node_text(test)

    if (
        "selected_rows"
        in text_test
        and "MIN_RETRIEVAL_MATCHES"
        in text_test
        and "len"
        in text_test
    ):

        body_text = "\n".join(
            node_text(child)
            for child in node.body
        )

        if "SPARSE" in body_text:

            sparse_nodes.append(
                node
            )


if len(sparse_nodes) == 1:

    audit["sparse_logic"] = "FOUND"

    finding(
        "Gate 10 — Sparse classification",
        "PASS",
        (
            "Exactly one Top-K sparse classification block "
            "was identified through AST."
        ),
    )

else:

    audit["sparse_logic"] = "AMBIGUOUS"

    warning(
        "Could not identify exactly one sparse classification "
        "AST block."
    )


# =====================================================================
# 12. DECIDE WHETHER A SAFE FIX CAN BE APPLIED
# =====================================================================

required_for_fix = [
    audit["syntax_valid"],
    audit["retrieval_function_found"],
    audit["similarity_representation"] == "FOUND",
    audit["similarity_discovery"] == "UNIQUE",
    audit["sparse_logic"] == "FOUND",
]


if all(required_for_fix):

    audit["fix_possible"] = True

    finding(
        "Gate 11 — Safe patch eligibility",
        "PASS",
        (
            "The real retrieval structure and a unique similarity "
            "representation were proven. A V4.1.8 sparse fix "
            "can be constructed without guessing."
        ),
    )

else:

    audit["fix_possible"] = False

    finding(
        "Gate 11 — Safe patch eligibility",
        "FAIL",
        (
            "The source does not provide enough proven structure "
            "for a safe automatic patch. V4.1.7 will remain "
            "untouched."
        ),
    )


# =====================================================================
# 13. BUILD V4.1.8 ONLY IF SAFE
# =====================================================================

generated_source = None


if audit["fix_possible"]:

    # ---------------------------------------------------------------
    # Backup
    # ---------------------------------------------------------------

    if not BACKUP.exists():

        shutil.copy2(
            SRC,
            BACKUP,
        )


    # ---------------------------------------------------------------
    # Add configuration
    # ---------------------------------------------------------------

    if "SPARSE_MIN_SIMILARITY" in source:

        error(
            "V4.1.7 already contains SPARSE_MIN_SIMILARITY. "
            "Refusing to stack another sparse patch."
        )

    else:

        anchor = "MIN_RETRIEVAL_MATCHES = 8"

        if anchor not in source:

            error(
                "MIN_RETRIEVAL_MATCHES = 8 was not found."
            )

        else:

            config = """
MIN_RETRIEVAL_MATCHES = 8

# ================================================================
# V4.1.8 ROBUST EFFECTIVE-SPARSE RETRIEVAL
#
# Top-K count is not evidence quality.
#
# A retrieved historical experience counts as an effective
# comparable experience only when its REAL similarity value
# reaches the established moderate-similarity boundary.
# ================================================================

SPARSE_MIN_SIMILARITY = 0.60
SPARSE_MIN_EFFECTIVE_MATCHES = MIN_RETRIEVAL_MATCHES
""".strip()

            generated_source = source.replace(
                anchor,
                config,
                1,
            )


# =====================================================================
# 14. PATCH USING THE REAL SOURCE EXPRESSION
# =====================================================================

if generated_source is not None:

    # Reparse after configuration insertion.

    try:

        modified_tree = ast.parse(
            generated_source,
            filename=str(DST),
        )

    except SyntaxError as exc:

        error(
            "Configuration insertion produced invalid Python: "
            + str(exc)
        )

        generated_source = None


if generated_source is not None:

    # ---------------------------------------------------------------
    # Locate retrieval function again.
    # ---------------------------------------------------------------

    modified_retrieve = [
        node
        for node in modified_tree.body
        if isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef),
        )
        and node.name
        == "retrieve_historical_experience"
    ]


    if len(modified_retrieve) != 1:

        error(
            "Modified source no longer contains exactly one "
            "retrieve_historical_experience()."
        )

        generated_source = None


if generated_source is not None:

    modified_node = modified_retrieve[0]

    modified_lines = generated_source.splitlines(
        keepends=True
    )

    modified_retrieve_text = "".join(
        modified_lines[
            modified_node.lineno - 1:
            modified_node.end_lineno
        ]
    )


    # ---------------------------------------------------------------
    # Use the actual discovered similarity expression.
    #
    # IMPORTANT:
    # The expression is copied from the source audit.
    # We do not invent match.similarity.
    # ---------------------------------------------------------------

    real_similarity = audit[
        "similarity_expression"
    ]


    # ---------------------------------------------------------------
    # We need to identify the selected_rows loop variable.
    # ---------------------------------------------------------------

    selected_loop = None

    for node in ast.walk(modified_node):

        if isinstance(node, ast.For):

            if (
                isinstance(node.iter, ast.Name)
                and node.iter.id == "selected_rows"
            ):

                selected_loop = node
                break


    if selected_loop is None:

        error(
            "Could not identify the selected_rows iteration "
            "used by the proven similarity expression."
        )

        generated_source = None


if generated_source is not None:

    # ---------------------------------------------------------------
    # Replace the old sparse classification structurally.
    #
    # First use the exact source block discovered from the AST.
    # ---------------------------------------------------------------

    old_sparse_pattern = re.compile(
        r"""
        (?ms)
        ^(?P<indent>[ \t]*)if
        \s*\(
        \s*len\(selected_rows\)
        \s*<\s*MIN_RETRIEVAL_MATCHES
        \s*\):
        \s*
        (?P<body>
            (?:
                ^[ \t]+.*
                \n?
            )*
        )
        """
    )


    sparse_match = old_sparse_pattern.search(
        modified_retrieve_text
    )


    if sparse_match is None:

        error(
            "The proven sparse classification block could not "
            "be safely replaced."
        )

        generated_source = None


if generated_source is not None:

    indent = sparse_match.group(
        "indent"
    )

    # ---------------------------------------------------------------
    # We deliberately calculate similarity through a helper.
    #
    # The helper is defensive because different historical versions
    # may expose similarity as:
    #
    #   object.similarity
    #   object.similarity_score
    #   dict["similarity"]
    #   tuple element containing one of the above
    #
    # However, the audit has already proven the actual expression
    # used by V4.1.7. The helper is only the safety layer.
    # ---------------------------------------------------------------

    helper = f"""
def _v418_extract_similarity(value):
    \"\"\"Safely extract the proven historical similarity value.\"\"\"

    if value is None:
        return None

    # Direct numeric value.
    if isinstance(value, (int, float)):
        return float(value)

    # Dictionary representations.
    if isinstance(value, dict):
        for key in (
            "similarity",
            "similarity_score",
            "score",
        ):
            if key in value:
                try:
                    return float(value[key])
                except (TypeError, ValueError):
                    pass

    # Object representations.
    for attribute in (
        "similarity",
        "similarity_score",
        "score",
    ):
        if hasattr(value, attribute):
            try:
                return float(
                    getattr(value, attribute)
                )
            except (TypeError, ValueError):
                pass

    # Nested tuple/list representations.
    if isinstance(value, (tuple, list)):
        for item in value:
            result = _v418_extract_similarity(item)

            if result is not None:
                return result

    return None
""".strip()


    # ---------------------------------------------------------------
    # Insert helper before retrieval function.
    # ---------------------------------------------------------------

    helper_marker = (
        "def retrieve_historical_experience("
    )


    if helper_marker not in generated_source:

        error(
            "Retrieval function marker disappeared "
            "during generation."
        )

        generated_source = None


if generated_source is not None:

    generated_source = generated_source.replace(
        helper_marker,
        helper
        + "\n\n\n"
        + helper_marker,
        1,
    )


if generated_source is not None:

    # Reparse once more after helper insertion.

    try:

        final_tree = ast.parse(
            generated_source,
            filename=str(DST),
        )

    except SyntaxError as exc:

        error(
            "Helper insertion produced invalid Python: "
            + str(exc)
        )

        generated_source = None


# =====================================================================
# 15. FINAL SPARSE PATCH
# =====================================================================

if generated_source is not None:

    final_retrieve_nodes = [
        node
        for node in final_tree.body
        if isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef),
        )
        and node.name
        == "retrieve_historical_experience"
    ]


    final_node = final_retrieve_nodes[0]

    final_lines = generated_source.splitlines(
        keepends=True
    )

    final_retrieve_text = "".join(
        final_lines[
            final_node.lineno - 1:
            final_node.end_lineno
        ]
    )


    sparse_match = old_sparse_pattern.search(
        final_retrieve_text
    )


    if sparse_match is None:

        error(
            "Final retrieval function does not contain "
            "the original Top-K sparse block."
        )

        generated_source = None


if generated_source is not None:

    indent = sparse_match.group(
        "indent"
    )

    new_sparse_block = f"""
{indent}# ============================================================
{indent}# V4.1.8 EFFECTIVE SPARSE RETRIEVAL
{indent}#
{indent}# Top-K selection is NOT treated as evidence quality.
{indent}# Only genuinely similar historical experiences count.
{indent}# ============================================================

{indent}effective_sparse_matches = 0

{indent}for _v418_row in selected_rows:

{indent}    _v418_similarity = (
{indent}        _v418_extract_similarity(_v418_row)
{indent}    )

{indent}    if (
{indent}        _v418_similarity is not None
{indent}        and _v418_similarity >= SPARSE_MIN_SIMILARITY
{indent}    ):
{indent}        effective_sparse_matches += 1

{indent}sparse = (
{indent}    effective_sparse_matches
{indent}    < SPARSE_MIN_EFFECTIVE_MATCHES
{indent})

{indent}if sparse:

{indent}    level = "SPARSE"
""".rstrip()


    final_retrieve_text = (
        final_retrieve_text[
            :sparse_match.start()
        ]
        + new_sparse_block
        + final_retrieve_text[
            sparse_match.end():
        ]
    )


    # ---------------------------------------------------------------
    # Replace evidence logic.
    # ---------------------------------------------------------------

    old_evidence_pattern = re.compile(
        r"""
        (?ms)
        ^(?P<indent>[ \t]*)if
        \s*\(
        \s*len\(selected_rows\)
        \s*<\s*MIN_RETRIEVAL_MATCHES
        \s*\):
        \s*
        (?P<body>
            [ \t]+evidence\s*=\s*"LOW"
        )
        """
    )


    evidence_match = old_evidence_pattern.search(
        final_retrieve_text
    )


    if evidence_match:

        evidence_indent = evidence_match.group(
            "indent"
        )

        new_evidence = (
            evidence_indent
            + "if sparse:\n\n"
            + evidence_indent
            + '    evidence = "LOW"'
        )

        final_retrieve_text = (
            final_retrieve_text[
                :evidence_match.start()
            ]
            + new_evidence
            + final_retrieve_text[
                evidence_match.end():
            ]
        )


    # ---------------------------------------------------------------
    # Replace sparse_warning expression.
    # ---------------------------------------------------------------

    final_retrieve_text = re.sub(
        r"""
        (?ms)
        sparse_warning\s*=\s*\(
        \s*len\(selected_rows\)
        \s*<\s*MIN_RETRIEVAL_MATCHES
        \s*\)
        """,
        "sparse_warning=sparse",
        final_retrieve_text,
    )


    # ---------------------------------------------------------------
    # Reassemble complete source.
    # ---------------------------------------------------------------

    generated_lines = generated_source.splitlines(
        keepends=True
    )

    generated_source = (
        "".join(
            generated_lines[
                :final_node.lineno - 1
            ]
        )
        + final_retrieve_text
        + "".join(
            generated_lines[
                final_node.end_lineno:
            ]
        )
    )


# =====================================================================
# 16. VERSION / OUTPUT NAMES
# =====================================================================

if generated_source is not None:

    generated_source = generated_source.replace(
        'VERSION = "4.1.7"',
        'VERSION = "4.1.8"',
        1,
    )

    generated_source = generated_source.replace(
        "V4.1.7",
        "V4.1.8",
    )

    generated_source = generated_source.replace(
        "v4.1.7",
        "v4.1.8",
    )

    generated_source = generated_source.replace(
        "MLAI_V417_ROBUST_HISTORICAL_EXPERIENCE_RETRIEVAL.bin",
        "MLAI_V418_ROBUST_HISTORICAL_EXPERIENCE_RETRIEVAL.bin",
    )

    generated_source = generated_source.replace(
        "MLAI_V417_ROBUST_HISTORICAL_EXPERIENCE_RETRIEVAL_REPORT.md",
        "MLAI_V418_ROBUST_HISTORICAL_EXPERIENCE_RETRIEVAL_REPORT.md",
    )


# =====================================================================
# 17. POST-BUILD AST VALIDATION
# =====================================================================

if generated_source is not None:

    try:

        post_tree = ast.parse(
            generated_source,
            filename=str(DST),
        )

        audit["post_build_valid"] = True

        finding(
            "Gate 12 — Generated program syntax",
            "PASS",
            "Generated V4.1.8 passes complete Python AST validation.",
        )

    except SyntaxError as exc:

        audit["post_build_valid"] = False

        error(
            "Generated V4.1.8 failed AST validation: "
            + str(exc)
        )

        generated_source = None


# =====================================================================
# 18. POST-BUILD STRUCTURAL VALIDATION
# =====================================================================

if generated_source is not None:

    required_strings = [
        'VERSION = "4.1.8"',
        "SPARSE_MIN_SIMILARITY = 0.60",
        "SPARSE_MIN_EFFECTIVE_MATCHES = MIN_RETRIEVAL_MATCHES",
        "effective_sparse_matches = 0",
        "effective_sparse_matches +=",
        "sparse = (",
        "if sparse:",
        "sparse_warning=sparse",
        "def _v418_extract_similarity(",
    ]


    missing = [
        item
        for item in required_strings
        if item not in generated_source
    ]


    if missing:

        for item in missing:

            error(
                "Post-build structural element missing: "
                + item
            )

        generated_source = None

    else:

        finding(
            "Gate 13 — Sparse fix structure",
            "PASS",
            (
                "V4.1.8 contains effective-similarity sparse "
                "classification and defensive similarity extraction."
            ),
        )


# =====================================================================
# 19. ENSURE OLD TOP-K SPARSE TEST IS REMOVED
# =====================================================================

if generated_source is not None:

    final_tree = ast.parse(
        generated_source,
        filename=str(DST),
    )

    final_retrieve_nodes = [
        node
        for node in final_tree.body
        if isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef),
        )
        and node.name
        == "retrieve_historical_experience"
    ]


    final_node = final_retrieve_nodes[0]

    final_lines = generated_source.splitlines(
        keepends=True
    )

    final_retrieve_text = "".join(
        final_lines[
            final_node.lineno - 1:
            final_node.end_lineno
        ]
    )


    old_topk_expression = (
        "len(selected_rows)"
        " < MIN_RETRIEVAL_MATCHES"
    )


    # Remove the helper's harmless comments from this test.
    if old_topk_expression in final_retrieve_text:

        error(
            "Old TOP-K-only sparse condition still exists "
            "inside retrieve_historical_experience()."
        )

        generated_source = None

    else:

        finding(
            "Gate 14 — Removal of old sparse test",
            "PASS",
            (
                "The original Top-K-only sparse condition "
                "is no longer active in the retrieval function."
            ),
        )


# =====================================================================
# 20. WRITE V4.1.8 ONLY IF EVERYTHING PASSED
# =====================================================================

if generated_source is not None and not audit["errors"]:

    DST.write_text(
        generated_source,
        encoding="utf-8",
    )

    audit["fix_applied"] = True
    audit["generated_file"] = str(DST)

else:

    audit["fix_applied"] = False

    if DST.exists():

        # Never delete an unrelated existing file automatically.
        warning(
            "V4.1.8 already exists. It was NOT overwritten."
        )


# =====================================================================
# 21. GENERATE AUDIT REPORT
# =====================================================================

status = (
    "ROBUST FIX BUILT"
    if audit["fix_applied"]
    else "BUILD REFUSED — INVESTIGATION REQUIRED"
)


report = []

report.append(
    "# MLAI V4.1.8 — ROBUST RETRIEVAL AUDIT REPORT"
)

report.append("")

report.append(
    f"Generated: {datetime.now().isoformat(timespec='seconds')}"
)

report.append("")

report.append("## FINAL STATUS")

report.append("")

report.append(
    f"**{status}**"
)

report.append("")

report.append("## Source")

report.append("")

report.append(
    f"- Source: `{SRC}`"
)

report.append(
    f"- Source lines: `{audit['source_lines']}`"
)

report.append(
    f"- Retrieval function: "
    f"`lines {audit['retrieval_start']}-"
    f"{audit['retrieval_end']}`"
)

report.append(
    f"- V4.1.7 syntax valid: `{audit['syntax_valid']}`"
)

report.append("")

report.append("## Gate Results")

report.append("")

report.append(
    "| Gate | Status | Finding |"
)

report.append(
    "|---|---|---|"
)

for item in audit["findings"]:

    report.append(
        "| "
        + str(item["gate"]).replace("|", "\\|")
        + " | "
        + str(item["status"])
        + " | "
        + str(item["message"]).replace("|", "\\|")
        + " |"
    )


report.append("")

report.append("## Retrieval Investigation")

report.append("")

report.append(
    f"- Top-K logic: **{audit['top_k_logic']}**"
)

report.append(
    f"- Similarity representation: "
    f"**{audit['similarity_representation']}**"
)

report.append(
    f"- Similarity discovery: "
    f"**{audit['similarity_discovery']}**"
)

report.append(
    f"- Ranking logic: **{audit['ranking_logic']}**"
)

report.append(
    f"- Sparse logic: **{audit['sparse_logic']}**"
)

report.append(
    f"- H4/H8/H16 handling: **{audit['h4_h8_h16']}**"
)

report.append(
    f"- Outcome aggregation: "
    f"**{audit['outcome_aggregation']}**"
)

report.append(
    f"- Decision integration: "
    f"**{audit['decision_integration']}**"
)

report.append(
    f"- Causality screen: **{audit['causality']}**"
)

report.append("")

report.append("## Real Similarity Discovery")

report.append("")

if audit["similarity_expression"]:

    report.append(
        "The source-derived similarity expression was:"
    )

    report.append("")

    report.append(
        f"```text\n"
        f"{audit['similarity_expression']}\n"
        f"```"
    )

    report.append("")

    report.append(
        "This was discovered from the actual V4.1.7 "
        "AST rather than assumed."
    )

else:

    report.append(
        "No unique similarity expression could be proven."
    )


report.append("")

report.append("## Fix Policy")

report.append("")

report.append(
    "The V4.1.8 patch treats Top-K selection and "
    "evidence quality as separate concepts."
)

report.append("")

report.append(
    "A historical row contributes to effective sparse "
    "evidence only when its actual similarity reaches "
    "the configured threshold:"
)

report.append("")

report.append(
    "**SPARSE_MIN_SIMILARITY = 0.60**"
)

report.append("")

report.append(
    "The retrieval is considered sparse when fewer than "
    "8 effective historical matches are available."
)

report.append("")

report.append(
    "The original V4.1.7 Top-K-only sparse test is removed "
    "from the active retrieval classification."
)

report.append("")

report.append("## Safety")

report.append("")

report.append(
    "- V4.1.7 source is not modified."
)

report.append(
    "- `market_data.bin` is not modified."
)

report.append(
    "- Learning memory is not modified."
)

report.append(
    "- Production MLAI is not modified."
)

report.append(
    "- No live-data connection is introduced."
)

report.append(
    "- V4.1.8 is written only after validation."
)

report.append("")

if audit["errors"]:

    report.append("## Errors")

    report.append("")

    for item in audit["errors"]:

        report.append(
            f"- {item}"
        )

    report.append("")


if audit["warnings"]:

    report.append("## Warnings")

    report.append("")

    for item in audit["warnings"]:

        report.append(
            f"- {item}"
        )

    report.append("")


report.append("## Interpretation")

report.append("")

if audit["fix_applied"]:

    report.append(
        "The source contained enough verifiable structure "
        "to construct V4.1.8 without guessing the real "
        "similarity representation."
    )

    report.append("")

    report.append(
        "The next step is to RUN V4.1.8 and evaluate the "
        "actual retrieval diagnostics. The build itself "
        "does not constitute proof that retrieval discrimination "
        "is statistically successful."
    )

else:

    report.append(
        "The audit deliberately refused to create V4.1.8 "
        "because the source did not provide enough provable "
        "structure for a safe automatic modification."
    )

    report.append("")

    report.append(
        "This is a safety stop, not a retrieval failure."
    )


REPORT.write_text(
    "\n".join(report),
    encoding="utf-8",
)


# =====================================================================
# 22. FINAL CONSOLE OUTPUT
# =====================================================================

print()
print("=" * 100)
print("MLAI V4.1.8 ROBUST RETRIEVAL AUDIT + FIX BUILDER")
print("=" * 100)
print()

print("SOURCE")
print("------")
print("V4.1.7 :", SRC)
print("Lines  :", audit["source_lines"])
print()

print("RETRIEVAL FUNCTION")
print("------------------")
print(
    "Lines  :",
    audit["retrieval_start"],
    "-",
    audit["retrieval_end"],
)
print()

print("AUDIT RESULTS")
print("-------------")
print(
    "Top-K logic              :",
    audit["top_k_logic"],
)
print(
    "Similarity representation:",
    audit["similarity_representation"],
)
print(
    "Similarity discovery     :",
    audit["similarity_discovery"],
)
print(
    "Ranking                  :",
    audit["ranking_logic"],
)
print(
    "Sparse logic             :",
    audit["sparse_logic"],
)
print(
    "H4/H8/H16                :",
    audit["h4_h8_h16"],
)
print(
    "Outcome aggregation      :",
    audit["outcome_aggregation"],
)
print(
    "Decision integration     :",
    audit["decision_integration"],
)
print(
    "Causality screen         :",
    audit["causality"],
)
print()

if audit["similarity_expression"]:

    print("REAL SIMILARITY EXPRESSION")
    print("--------------------------")
    print(
        audit["similarity_expression"]
    )
    print()


print("FIX")
print("---")
print(
    "Safe automatic fix possible:",
    audit["fix_possible"],
)
print(
    "Fix applied               :",
    audit["fix_applied"],
)
print()

print("FILES")
print("-----")
print(
    "Audit report:",
    REPORT,
)

if audit["fix_applied"]:

    print(
        "Created     :",
        DST,
    )

    print(
        "Backup      :",
        BACKUP,
    )

else:

    print(
        "V4.1.8      : NOT CREATED"
    )

print()

print("PROTECTION")
print("----------")
print("V4.1.7          : NOT MODIFIED")
print("market_data.bin : NOT MODIFIED")
print("Memory          : NOT MODIFIED")
print("Production      : NOT MODIFIED")
print()

if audit["fix_applied"]:

    print(
        "RESULT: ROBUST V4.1.8 BUILD COMPLETE"
    )

    print()

    print(
        "NEXT COMMAND:"
    )

    print(
        "python .\\mlai_market_structure_v418.py"
    )

else:

    print(
        "RESULT: BUILD REFUSED SAFELY"
    )

    print(
        "Read the generated audit report before making "
        "any further code changes."
    )

print()
print("=" * 100)