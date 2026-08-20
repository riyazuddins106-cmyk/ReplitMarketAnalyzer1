from pathlib import Path
import ast
import json
import re
import shutil
import hashlib
import py_compile
from datetime import datetime, timezone


# =====================================================================
# MLAI V4.1.8
# DEFINITIVE AUDIT + ROBUST FIX BUILDER
#
# PURPOSE
# -------
# Audit the REAL V4.1.7 retrieval architecture and create V4.1.8 only
# when the required structural evidence is present.
#
# THIS PROGRAM:
#   - NEVER modifies V4.1.7
#   - NEVER modifies market_data.bin
#   - NEVER modifies memory
#   - NEVER modifies production
#   - NEVER guesses a similarity-report dictionary
#   - NEVER invents H4/H8/H16 behavior
#   - NEVER changes the retrieval scoring model
#   - ONLY changes the verified sparse-evidence definition
#
# V4.1.8 change:
#
#   OLD:
#       TOP-K count >= 8 => enough evidence
#
#   NEW:
#       at least 8 selected matches with similarity >= 0.60
#       => non-sparse evidence
#
# Everything else remains structurally unchanged.
# =====================================================================


VERSION_FROM = "4.1.7"
VERSION_TO = "4.1.8"

SRC = Path("mlai_market_structure_v417.py")
DST = Path("mlai_market_structure_v418.py")
BACKUP = Path("mlai_market_structure_v417_before_v418_definitive.py")

REPORT_MD = Path("MLAI_V418_DEFINITIVE_AUDIT_REPORT.md")
REPORT_JSON = Path("MLAI_V418_DEFINITIVE_AUDIT_REPORT.json")


# =====================================================================
# UTILITY
# =====================================================================

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def source_hash(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def fail(message: str):
    raise RuntimeError(message)


def node_text(source: str, node: ast.AST) -> str:
    lines = source.splitlines(keepends=True)
    return "".join(lines[node.lineno - 1:node.end_lineno])


def find_top_level_function(tree, name):
    nodes = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == name
    ]

    if len(nodes) != 1:
        fail(
            f"Expected exactly one top-level {name}() function; "
            f"found {len(nodes)}."
        )

    return nodes[0]


def contains_any(text, patterns):
    return any(pattern in text for pattern in patterns)


# =====================================================================
# SOURCE LOAD
# =====================================================================

print("=" * 100)
print("MLAI V4.1.8 DEFINITIVE AUDIT + ROBUST FIX BUILDER")
print("=" * 100)
print()

if not SRC.exists():
    fail(f"ERROR: {SRC} was not found.")

original_bytes = SRC.read_bytes()
original_source = original_bytes.decode("utf-8")

print("Source:", SRC)
print("Lines :", len(original_source.splitlines()))
print("SHA256:", source_hash(SRC))
print()


# =====================================================================
# ORIGINAL VERSION PROTECTION
# =====================================================================

if f'VERSION = "{VERSION_FROM}"' not in original_source:
    fail(
        f'ERROR: expected VERSION = "{VERSION_FROM}" was not found.\n'
        "Refusing to modify anything."
    )

if f'VERSION = "{VERSION_TO}"' in original_source:
    fail(
        f'ERROR: source already contains VERSION = "{VERSION_TO}".\n'
        "This program expects an untouched V4.1.7 source."
    )


# =====================================================================
# AST VALIDATION OF ORIGINAL
# =====================================================================

try:
    original_tree = ast.parse(
        original_source,
        filename=str(SRC),
    )
except SyntaxError as exc:
    fail(
        "ERROR: V4.1.7 source is not syntactically valid.\n"
        f"{exc}"
    )


retrieve_node = find_top_level_function(
    original_tree,
    "retrieve_historical_experience",
)

similarity_node = find_top_level_function(
    original_tree,
    "similarity_score",
)

episode_node = find_top_level_function(
    original_tree,
    "select_episode_representatives",
)

retrieve_text = node_text(
    original_source,
    retrieve_node,
)

similarity_text = node_text(
    original_source,
    similarity_node,
)

episode_text = node_text(
    original_source,
    episode_node,
)


print("RETRIEVAL FUNCTION")
print("------------------")
print(
    f"Lines: {retrieve_node.lineno} - "
    f"{retrieve_node.end_lineno}"
)
print()

print("SIMILARITY FUNCTION")
print("-------------------")
print(
    f"Lines: {similarity_node.lineno} - "
    f"{similarity_node.end_lineno}"
)
print()

print("EPISODE REPRESENTATIVE FUNCTION")
print("--------------------------------")
print(
    f"Lines: {episode_node.lineno} - "
    f"{episode_node.end_lineno}"
)
print()


# =====================================================================
# AUDIT RESULT STORAGE
# =====================================================================

checks = {}
evidence = {}
warnings = []


def check(name, passed, detail):
    checks[name] = bool(passed)
    evidence[name] = detail


# =====================================================================
# 1. VERIFY SIMILARITY ENGINE
# =====================================================================

similarity_total_present = (
    '"total": clamp(total)' in similarity_text
    or '"total": total' in similarity_text
)

similarity_components_present = all(
    token in similarity_text
    for token in [
        "structure",
        "context",
        "numeric",
        "path",
        "candle",
        "total",
    ]
)

check(
    "similarity function exists",
    True,
    "Top-level similarity_score() found.",
)

check(
    "similarity composite total exists",
    similarity_total_present,
    (
        "similarity_score() returns a composite total."
        if similarity_total_present
        else
        "Could not verify composite similarity total."
    ),
)

check(
    "similarity uses multiple evidence families",
    similarity_components_present,
    (
        "Structure/context/numeric/path/candle components "
        "are present."
        if similarity_components_present
        else
        "Required similarity components were not all found."
    ),
)


# =====================================================================
# 2. VERIFY OUTCOME-BLIND SIMILARITY
# =====================================================================

outcome_terms = [
    "outcome.direction",
    "outcome.raw_return",
    "outcome.atr_return",
    "mfe_atr",
    "mae_atr",
]

outcome_used_inside_similarity = any(
    term in similarity_text
    for term in outcome_terms
)

check(
    "similarity is outcome-blind",
    not outcome_used_inside_similarity,
    (
        "No outcome field was detected inside similarity_score()."
        if not outcome_used_inside_similarity
        else
        "Outcome-related field detected inside similarity_score()."
    ),
)


# =====================================================================
# 3. VERIFY SIMILARITY -> SimilarityMatch.similarity
# =====================================================================

similarity_match_assignment = (
    'similarity=components["total"]' in retrieve_text
)

check(
    "SimilarityMatch receives composite similarity",
    similarity_match_assignment,
    (
        'SimilarityMatch(similarity=components["total"]) '
        "verified."
        if similarity_match_assignment
        else
        "Could not verify SimilarityMatch receives components['total']."
    ),
)


# =====================================================================
# 4. VERIFY RANKING
# =====================================================================

ranking_present = (
    "candidates.sort(" in retrieve_text
    and "key=lambda item: (item.similarity, item.index)" in retrieve_text
)

check(
    "retrieval ranking exists",
    ranking_present,
    (
        "Candidates are sorted using similarity and index."
        if ranking_present
        else
        "Candidate ranking could not be verified."
    ),
)


# =====================================================================
# 5. VERIFY EPISODE DEDUPLICATION
# =====================================================================

episode_dedup_present = (
    "by_episode" in episode_text
    and "match.episode_id" in episode_text
    and "match.similarity" in episode_text
)

check(
    "episode deduplication exists",
    episode_dedup_present,
    (
        "At most one representative is selected per historical episode."
        if episode_dedup_present
        else
        "Episode-level deduplication could not be verified."
    ),
)


# =====================================================================
# 6. VERIFY TOP-K SELECTION
# =====================================================================

top_k_present = (
    "selected = select_episode_representatives(candidates)"
    in retrieve_text
    and "selected_rows" in retrieve_text
)

check(
    "Top-K retrieval exists",
    top_k_present,
    (
        "Candidates are converted into selected historical rows."
        if top_k_present
        else
        "Top-K retrieval chain could not be verified."
    ),
)


# =====================================================================
# 7. VERIFY selected_rows CONTAINS MATCH OBJECTS
# =====================================================================

selected_rows_pattern = re.compile(
    r"selected_rows\s*=\s*\[.*?"
    r"match.*?"
    r"record.*?"
    r"for\s+match\s*,\s*record\s+in\s+selected",
    re.S,
)

selected_rows_has_match_record = bool(
    selected_rows_pattern.search(retrieve_text)
)

if not selected_rows_has_match_record:
    # More permissive structural fallback.
    selected_rows_has_match_record = (
        "selected_rows = [" in retrieve_text
        and "for match in selected" in retrieve_text
        and "record_by_index" in retrieve_text
    )

check(
    "selected_rows contains similarity-bearing matches",
    selected_rows_has_match_record,
    (
        "selected_rows is built from selected SimilarityMatch objects "
        "and corresponding records."
        if selected_rows_has_match_record
        else
        "Could not prove selected_rows contains SimilarityMatch objects."
    ),
)


# =====================================================================
# 8. VERIFY ACTUAL match.similarity ACCESS
# =====================================================================

match_similarity_access = (
    "match.similarity" in retrieve_text
)

check(
    "match.similarity is available in retrieval function",
    match_similarity_access,
    (
        "retrieve_historical_experience() accesses match.similarity."
        if match_similarity_access
        else
        "No match.similarity access was found."
    ),
)


# =====================================================================
# 9. VERIFY SIMILARITY-WEIGHTED OUTCOME AGGREGATION
# =====================================================================

weighted_retrieval_present = (
    "similarity ** 2" in retrieve_text
    or "match.similarity ** 2" in retrieve_text
)

check(
    "similarity-weighted outcome aggregation",
    weighted_retrieval_present,
    (
        "Historical outcomes are weighted using similarity."
        if weighted_retrieval_present
        else
        "Similarity-weighted outcome aggregation could not be verified."
    ),
)


# =====================================================================
# 10. VERIFY EXISTING TOP-K SPARSE LOGIC
# =====================================================================

old_sparse_exact = """    if (
        len(selected_rows)
        < MIN_RETRIEVAL_MATCHES
    ):

        level = "SPARSE"
"""

old_evidence_exact = """    if (
        len(selected_rows)
        < MIN_RETRIEVAL_MATCHES
    ):

        evidence = "LOW"
"""

old_warning_exact = """        sparse_warning=(
            len(selected_rows)
            < MIN_RETRIEVAL_MATCHES
        ),
"""

old_sparse_present = old_sparse_exact in retrieve_text
old_evidence_present = old_evidence_exact in retrieve_text
old_warning_present = old_warning_exact in retrieve_text

check(
    "existing TOP-K sparse classification identified",
    old_sparse_present,
    (
        "Exact existing sparse classification block found."
        if old_sparse_present
        else
        "Existing sparse classification block was not found exactly."
    ),
)

check(
    "existing TOP-K sparse evidence identified",
    old_evidence_present,
    (
        "Exact existing sparse evidence block found."
        if old_evidence_present
        else
        "Existing sparse evidence block was not found exactly."
    ),
)

check(
    "existing TOP-K sparse warning identified",
    old_warning_present,
    (
        "Exact existing sparse_warning block found."
        if old_warning_present
        else
        "Existing sparse_warning block was not found exactly."
    ),
)


# =====================================================================
# 11. VERIFY H4/H8/H16 SUPPORT WITHOUT GUESSING
# =====================================================================

horizon_config_patterns = [
    "HORIZONS = (4, 8, 16)",
    "HORIZONS=(4, 8, 16)",
    "HORIZONS = (4,8,16)",
    "HORIZONS=(4,8,16)",
]

horizon_constant_present = any(
    pattern in original_source
    for pattern in horizon_config_patterns
)

horizon_literal_usage = all(
    re.search(rf"\b{h}\b", original_source) is not None
    for h in ["4", "8", "16"]
)

explicit_horizon_support = (
    horizon_constant_present
    or (
        "horizon" in retrieve_text
        and horizon_literal_usage
    )
)

check(
    "H4/H8/H16 horizon architecture",
    explicit_horizon_support,
    (
        "The source exposes horizon-aware retrieval and/or "
        "an explicit (4,8,16) horizon configuration."
        if explicit_horizon_support
        else
        "Could not safely prove explicit H4/H8/H16 configuration."
    ),
)

if not explicit_horizon_support:
    warnings.append(
        "H4/H8/H16 discrimination cannot be claimed from static "
        "source inspection alone."
    )


# =====================================================================
# 12. VERIFY CAUSAL HISTORICAL FILTER
# =====================================================================

causal_history_patterns = [
    "record.index < query_index",
    "r.index < query_index",
    "query_index - record.index",
    "MIN_HISTORY_GAP",
]

causal_terms_found = [
    pattern
    for pattern in causal_history_patterns
    if pattern in retrieve_text
]

causal_history_present = len(causal_terms_found) >= 2

check(
    "causal historical candidate filtering",
    causal_history_present,
    (
        "Retrieval source contains explicit past-only/index-gap "
        "constraints."
        if causal_history_present
        else
        "Could not verify sufficient causal candidate filtering."
    ),
)


# =====================================================================
# 13. VERIFY RETRIEVAL DOES NOT USE FUTURE OUTCOME FOR RANKING
# =====================================================================

ranking_section_start = retrieve_text.find("candidates.sort(")

if ranking_section_start >= 0:
    ranking_section = retrieve_text[
        :retrieve_text.find("selected_rows", ranking_section_start)
        if retrieve_text.find("selected_rows", ranking_section_start) >= 0
        else len(retrieve_text)
    ]
else:
    ranking_section = ""

ranking_outcome_contamination = any(
    token in ranking_section
    for token in [
        "outcome.direction",
        "outcome.raw_return",
        "outcome.atr_return",
        "mfe_atr",
        "mae_atr",
    ]
)

check(
    "ranking is outcome-blind",
    not ranking_outcome_contamination,
    (
        "No outcome fields were detected in the ranking section."
        if not ranking_outcome_contamination
        else
        "Outcome fields were detected in the ranking section."
    ),
)


# =====================================================================
# 14. VERIFY RETRIEVAL RESULT ALREADY HAS USEFUL FIELDS
# =====================================================================

existing_result_fields = [
    "raw_candidates",
    "deduplicated_matches",
    "top_similarity",
    "mean_similarity",
    "level",
    "evidence",
    "sparse_warning",
    "regime_agreement",
    "structure_agreement",
    "context_agreement",
    "up_share",
    "down_share",
    "neutral_share",
]

result_fields_found = [
    field
    for field in existing_result_fields
    if field in retrieve_text
]

check(
    "existing retrieval reporting contract",
    len(result_fields_found) >= 8,
    (
        f"Found {len(result_fields_found)} existing retrieval-result "
        "fields; reporting contract will remain untouched."
        if len(result_fields_found) >= 8
        else
        "Too few existing retrieval-result fields were identified."
    ),
)


# =====================================================================
# 15. FINAL PRE-FIX SAFETY DECISION
# =====================================================================

critical_checks = [
    "similarity function exists",
    "similarity composite total exists",
    "similarity uses multiple evidence families",
    "similarity is outcome-blind",
    "SimilarityMatch receives composite similarity",
    "retrieval ranking exists",
    "episode deduplication exists",
    "Top-K retrieval exists",
    "selected_rows contains similarity-bearing matches",
    "match.similarity is available in retrieval function",
    "similarity-weighted outcome aggregation",
    "existing TOP-K sparse classification identified",
    "existing TOP-K sparse evidence identified",
    "existing TOP-K sparse warning identified",
    "causal historical candidate filtering",
    "ranking is outcome-blind",
    "existing retrieval reporting contract",
]

critical_failures = [
    name
    for name in critical_checks
    if not checks.get(name, False)
]


# =====================================================================
# PRINT AUDIT
# =====================================================================

print("=" * 100)
print("DEFINITIVE RETRIEVAL AUDIT")
print("=" * 100)
print()

for name in critical_checks:
    status = "PASS" if checks[name] else "FAIL"
    print(f"{status:<6} : {name}")

print()

print("NON-BLOCKING HORIZON CHECK")
print("---------------------------")
print(
    f"{'PASS' if checks['H4/H8/H16 horizon architecture'] else 'REVIEW'}"
    " : H4/H8/H16 architecture"
)

print()

if warnings:
    print("WARNINGS")
    print("--------")
    for warning in warnings:
        print("WARNING:", warning)
    print()


# =====================================================================
# IF CRITICAL AUDIT FAILS -> REFUSE
# =====================================================================

if critical_failures:
    report = {
        "program": "MLAI V4.1.8 DEFINITIVE AUDIT + ROBUST FIX BUILDER",
        "source": str(SRC),
        "source_version": VERSION_FROM,
        "target_version": VERSION_TO,
        "source_sha256": source_hash(SRC),
        "safe_automatic_fix_possible": False,
        "fix_applied": False,
        "critical_failures": critical_failures,
        "checks": checks,
        "evidence": evidence,
        "warnings": warnings,
        "created_v418": False,
    }

    REPORT_JSON.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    md = []
    md.append("# MLAI V4.1.8 Definitive Retrieval Audit")
    md.append("")
    md.append("## Result")
    md.append("")
    md.append("**BUILD REFUSED SAFELY**")
    md.append("")
    md.append(
        "The real V4.1.7 source did not provide sufficient structural "
        "evidence for the requested automatic repair."
    )
    md.append("")
    md.append("## Critical failures")
    md.append("")
    for failure in critical_failures:
        md.append(f"- {failure}")
    md.append("")
    md.append("## Protection")
    md.append("")
    md.append("- V4.1.7: NOT MODIFIED")
    md.append("- market_data.bin: NOT MODIFIED")
    md.append("- Memory: NOT MODIFIED")
    md.append("- Production: NOT MODIFIED")
    md.append("")

    REPORT_MD.write_text(
        "\n".join(md),
        encoding="utf-8",
    )

    print("=" * 100)
    print("BUILD REFUSED SAFELY")
    print("=" * 100)
    print()
    print("Audit report :", REPORT_MD)
    print("JSON report  :", REPORT_JSON)
    print()
    print("V4.1.7          : NOT MODIFIED")
    print("market_data.bin  : NOT MODIFIED")
    print("Memory           : NOT MODIFIED")
    print("Production       : NOT MODIFIED")
    print()
    print("Critical failures:")
    for failure in critical_failures:
        print("  -", failure)
    print()

    raise SystemExit(1)


# =====================================================================
# FIX PREPARATION
# =====================================================================

print("=" * 100)
print("ALL CRITICAL STRUCTURAL CHECKS PASSED")
print("=" * 100)
print()
print("The existing retrieval architecture is sufficiently proven.")
print("Applying ONLY the verified effective-sparse repair.")
print()


# =====================================================================
# 16. VERIFY CONFIGURATION ANCHOR
# =====================================================================

CONFIG_ANCHOR = "MIN_RETRIEVAL_MATCHES = 8"

if CONFIG_ANCHOR not in original_source:
    fail(
        "ERROR: MIN_RETRIEVAL_MATCHES = 8 was not found."
    )

if "SPARSE_MIN_SIMILARITY" in original_source:
    fail(
        "ERROR: SPARSE_MIN_SIMILARITY already exists in V4.1.7.\n"
        "Refusing to stack another V4.1.8 patch."
    )


# =====================================================================
# 17. ADD EFFECTIVE-SPARSE CONFIGURATION
# =====================================================================

CONFIG_BLOCK = """MIN_RETRIEVAL_MATCHES = 8

# ================================================================
# V4.1.8 ROBUST EFFECTIVE-SPARSE RETRIEVAL
#
# TOP-K count alone is not sufficient evidence.
#
# A selected historical experience counts as an effective match
# only when its actual similarity reaches the minimum similarity
# boundary below.
# ================================================================

SPARSE_MIN_SIMILARITY = 0.60

# Number of genuinely similar selected historical experiences
# required before retrieval is considered non-sparse.
SPARSE_MIN_EFFECTIVE_MATCHES = MIN_RETRIEVAL_MATCHES
"""


modified = original_source.replace(
    CONFIG_ANCHOR,
    CONFIG_BLOCK,
    1,
)


# =====================================================================
# 18. RE-LOCATE RETRIEVAL FUNCTION AFTER CONFIG INSERTION
# =====================================================================

try:
    modified_tree = ast.parse(
        modified,
        filename=str(DST),
    )
except SyntaxError as exc:
    fail(
        "ERROR: source became syntactically invalid after "
        "configuration insertion.\n"
        f"{exc}"
    )

modified_retrieve_node = find_top_level_function(
    modified_tree,
    "retrieve_historical_experience",
)

modified_retrieve_text = node_text(
    modified,
    modified_retrieve_node,
)


# =====================================================================
# 19. EXACT SPARSE CLASSIFICATION REPAIR
# =====================================================================

NEW_SPARSE_BLOCK = """    # ============================================================
    # V4.1.8 EFFECTIVE SPARSE RETRIEVAL
    #
    # TOP-K selection does not prove that useful historical
    # experiences were found.
    #
    # Count only selected historical matches whose actual
    # similarity reaches SPARSE_MIN_SIMILARITY.
    # ============================================================

    effective_sparse_matches = sum(
        1
        for match, _ in selected_rows
        if float(
            getattr(match, "similarity", 0.0)
        ) >= SPARSE_MIN_SIMILARITY
    )

    sparse = (
        effective_sparse_matches
        < SPARSE_MIN_EFFECTIVE_MATCHES
    )

    if sparse:

        level = "SPARSE"
"""


if old_sparse_exact not in modified_retrieve_text:
    fail(
        "ERROR: exact V4.1.7 sparse classification block "
        "was not found after re-parsing.\n"
        "Refusing to modify retrieval logic."
    )


modified_retrieve_text = modified_retrieve_text.replace(
    old_sparse_exact,
    NEW_SPARSE_BLOCK,
    1,
)


# =====================================================================
# 20. EXACT SPARSE EVIDENCE REPAIR
# =====================================================================

NEW_EVIDENCE_BLOCK = """    if sparse:

        evidence = "LOW"
"""


if old_evidence_exact not in modified_retrieve_text:
    fail(
        "ERROR: exact V4.1.7 sparse evidence block was not found "
        "after classification replacement."
    )


modified_retrieve_text = modified_retrieve_text.replace(
    old_evidence_exact,
    NEW_EVIDENCE_BLOCK,
    1,
)


# =====================================================================
# 21. EXACT sparse_warning REPAIR
# =====================================================================

NEW_WARNING_BLOCK = """        sparse_warning=sparse,
"""


if old_warning_exact not in modified_retrieve_text:
    fail(
        "ERROR: exact V4.1.7 sparse_warning block was not found."
    )


modified_retrieve_text = modified_retrieve_text.replace(
    old_warning_exact,
    NEW_WARNING_BLOCK,
    1,
)


# =====================================================================
# 22. REASSEMBLE FUNCTION
# =====================================================================

modified_lines = modified.splitlines(keepends=True)

modified = (
    "".join(
        modified_lines[
            :modified_retrieve_node.lineno - 1
        ]
    )
    + modified_retrieve_text
    + "".join(
        modified_lines[
            modified_retrieve_node.end_lineno:
        ]
    )
)


# =====================================================================
# 23. VERSION UPDATE
# =====================================================================

version_before = modified.count(
    f'VERSION = "{VERSION_FROM}"'
)

if version_before != 1:
    fail(
        "ERROR: expected exactly one V4.1.7 VERSION assignment "
        f"after patch preparation; found {version_before}."
    )

modified = modified.replace(
    f'VERSION = "{VERSION_FROM}"',
    f'VERSION = "{VERSION_TO}"',
    1,
)


# =====================================================================
# 24. VERSION LABELS
# =====================================================================

modified = modified.replace(
    "V4.1.7",
    "V4.1.8",
)

modified = modified.replace(
    "v4.1.7",
    "v4.1.8",
)


# =====================================================================
# 25. OUTPUT ARTIFACT NAMES
# =====================================================================

modified = modified.replace(
    "MLAI_V417_ROBUST_HISTORICAL_EXPERIENCE_RETRIEVAL.bin",
    "MLAI_V418_ROBUST_HISTORICAL_EXPERIENCE_RETRIEVAL.bin",
)

modified = modified.replace(
    "MLAI_V417_ROBUST_HISTORICAL_EXPERIENCE_RETRIEVAL_REPORT.md",
    "MLAI_V418_ROBUST_HISTORICAL_EXPERIENCE_RETRIEVAL_REPORT.md",
)


# =====================================================================
# 26. FULL AST VALIDATION
# =====================================================================

try:
    final_tree = ast.parse(
        modified,
        filename=str(DST),
    )
except SyntaxError as exc:
    fail(
        "ERROR: generated V4.1.8 failed AST validation.\n"
        f"{exc}"
    )


# =====================================================================
# 27. FINAL RETRIEVAL FUNCTION
# =====================================================================

final_retrieve_node = find_top_level_function(
    final_tree,
    "retrieve_historical_experience",
)

final_retrieve_text = node_text(
    modified,
    final_retrieve_node,
)


# =====================================================================
# 28. STRUCTURAL POST-FIX CHECKS
# =====================================================================

post_checks = {
    "V4.1.8 version": (
        f'VERSION = "{VERSION_TO}"' in modified
    ),

    "effective sparse threshold": (
        "SPARSE_MIN_SIMILARITY = 0.60" in modified
    ),

    "effective sparse minimum": (
        "SPARSE_MIN_EFFECTIVE_MATCHES = "
        "MIN_RETRIEVAL_MATCHES"
        in modified
    ),

    "effective sparse calculation": (
        "effective_sparse_matches = sum("
        in final_retrieve_text
    ),

    "effective sparse boolean": (
        "sparse = ("
        in final_retrieve_text
    ),

    "sparse classification uses boolean": (
        "if sparse:" in final_retrieve_text
    ),

    "sparse warning uses boolean": (
        "sparse_warning=sparse" in final_retrieve_text
    ),

    "old sparse classification removed": (
        old_sparse_exact not in final_retrieve_text
    ),

    "old sparse evidence removed": (
        old_evidence_exact not in final_retrieve_text
    ),

    "old sparse warning removed": (
        old_warning_exact not in final_retrieve_text
    ),

    "similarity engine preserved": (
        "def similarity_score(" in modified
    ),

    "retrieval ranking preserved": (
        "candidates.sort(" in final_retrieve_text
    ),

    "SimilarityMatch similarity preserved": (
        'similarity=components["total"]'
        in final_retrieve_text
    ),

    "episode selection preserved": (
        "select_episode_representatives(candidates)"
        in final_retrieve_text
    ),

    "outcome aggregation preserved": (
        "selected_rows" in final_retrieve_text
        and "shares" in final_retrieve_text
    ),

    "causal query index preserved": (
        "query_index" in final_retrieve_text
    ),
}


failed_post_checks = [
    name
    for name, passed in post_checks.items()
    if not passed
]

if failed_post_checks:
    fail(
        "ERROR: post-fix structural validation failed:\n\n"
        + "\n".join(
            "  FAILED: " + item
            for item in failed_post_checks
        )
        + "\n\n"
        "No V4.1.8 file will be written."
    )


# =====================================================================
# 29. COMPILE VALIDATION
# =====================================================================

TEMP_VALIDATE = Path(
    "__mlai_v418_validation_temp__.py"
)

try:
    TEMP_VALIDATE.write_text(
        modified,
        encoding="utf-8",
    )

    py_compile.compile(
        str(TEMP_VALIDATE),
        doraise=True,
    )

finally:
    if TEMP_VALIDATE.exists():
        TEMP_VALIDATE.unlink()


# =====================================================================
# 30. ENSURE SOURCE WAS NOT MODIFIED
# =====================================================================

if SRC.read_bytes() != original_bytes:
    fail(
        "CRITICAL ERROR: V4.1.7 changed during the build.\n"
        "The build is being aborted."
    )


# =====================================================================
# 31. CREATE BACKUP
# =====================================================================

if not BACKUP.exists():
    shutil.copy2(
        SRC,
        BACKUP,
    )


# =====================================================================
# 32. WRITE V4.1.8
# =====================================================================

DST.write_text(
    modified,
    encoding="utf-8",
)


# =====================================================================
# 33. FINAL FILE VALIDATION
# =====================================================================

if not DST.exists():
    fail(
        "CRITICAL ERROR: V4.1.8 file was not created."
    )

try:
    generated_tree = ast.parse(
        DST.read_text(encoding="utf-8"),
        filename=str(DST),
    )
except SyntaxError as exc:
    fail(
        "CRITICAL ERROR: written V4.1.8 failed final AST validation.\n"
        f"{exc}"
    )


generated_hash = source_hash(DST)


# =====================================================================
# 34. AUDIT REPORT
# =====================================================================

report = {
    "program": "MLAI V4.1.8 DEFINITIVE AUDIT + ROBUST FIX BUILDER",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "source": str(SRC),
    "destination": str(DST),
    "backup": str(BACKUP),
    "source_version": VERSION_FROM,
    "target_version": VERSION_TO,
    "source_sha256": source_hash(SRC),
    "generated_sha256": generated_hash,
    "safe_automatic_fix_possible": True,
    "fix_applied": True,
    "created_v418": True,
    "checks": checks,
    "post_fix_checks": post_checks,
    "warnings": warnings,
    "critical_failures": [],
    "protected_files": {
        "v417": True,
        "market_data": True,
        "memory": True,
        "production": True,
    },
    "repair_scope": {
        "changed_sparse_definition": True,
        "changed_similarity_score": False,
        "changed_similarity_weights": False,
        "changed_ranking": False,
        "changed_episode_deduplication": False,
        "changed_outcome_aggregation": False,
        "changed_causality": False,
        "changed_reporting_contract": False,
        "changed_market_data": False,
    },
    "effective_sparse_rule": {
        "threshold": 0.60,
        "required_effective_matches": 8,
        "definition": (
            "A selected historical experience counts as effective "
            "evidence only when match.similarity >= 0.60."
        ),
    },
}


REPORT_JSON.write_text(
    json.dumps(
        report,
        indent=2,
    ),
    encoding="utf-8",
)


md = []

md.append("# MLAI V4.1.8 Definitive Retrieval Audit")
md.append("")
md.append("## Final result")
md.append("")
md.append("**BUILD PASSED — V4.1.8 CREATED**")
md.append("")
md.append(
    "The real V4.1.7 retrieval architecture was structurally verified "
    "before the repair was applied."
)
md.append("")
md.append("## Verified retrieval chain")
md.append("")
md.append("```text")
md.append("Market state")
md.append("    ↓")
md.append("similarity_score()")
md.append("    ↓")
md.append('components["total"]')
md.append("    ↓")
md.append("SimilarityMatch.similarity")
md.append("    ↓")
md.append("candidate ranking")
md.append("    ↓")
md.append("episode deduplication")
md.append("    ↓")
md.append("Top-K selection")
md.append("    ↓")
md.append("selected_rows")
md.append("    ↓")
md.append("similarity-weighted outcomes")
md.append("```")
md.append("")
md.append("## V4.1.8 repair")
md.append("")
md.append(
    "The only behavioral repair made by this builder is the definition "
    "of sparse historical evidence."
)
md.append("")
md.append("### Previous rule")
md.append("")
md.append(
    "Fewer than 8 selected Top-K rows meant sparse evidence."
)
md.append("")
md.append("### New rule")
md.append("")
md.append(
    "Only selected historical rows with similarity >= 0.60 count "
    "toward effective evidence."
)
md.append("")
md.append(
    "Sparse evidence = fewer than 8 effective historical matches."
)
md.append("")
md.append("## Deliberately unchanged")
md.append("")
md.append("- Similarity calculation")
md.append("- Similarity weights")
md.append("- Ranking")
md.append("- Episode deduplication")
md.append("- Top-K selection")
md.append("- Similarity-weighted outcome aggregation")
md.append("- Causal candidate filtering")
md.append("- Existing RetrievalResult reporting contract")
md.append("- Market data")
md.append("- Learning memory")
md.append("- Production")
md.append("")
md.append("## Validation")
md.append("")
md.append("- Original V4.1.7 AST: PASS")
md.append("- Generated V4.1.8 AST: PASS")
md.append("- Generated V4.1.8 Python compilation: PASS")
md.append("- Old Top-K-only sparse classification: REMOVED")
md.append("- Old Top-K-only sparse evidence: REMOVED")
md.append("- Old Top-K-only sparse_warning: REMOVED")
md.append("")
md.append("## Horizon note")
md.append("")
md.append(
    "H4/H8/H16 architecture was checked structurally. "
    "This does NOT constitute behavioral proof that retrieval "
    "discriminates equally well at H4, H8 and H16. That requires "
    "execution-time out-of-sample evaluation."
)
md.append("")
md.append("## Protection")
md.append("")
md.append("- V4.1.7: NOT MODIFIED")
md.append("- market_data.bin: NOT MODIFIED")
md.append("- Memory: NOT MODIFIED")
md.append("- Production: NOT MODIFIED")
md.append("")
md.append("## Files")
md.append("")
md.append(f"- Source: `{SRC}`")
md.append(f"- Generated: `{DST}`")
md.append(f"- Backup: `{BACKUP}`")
md.append(f"- JSON audit: `{REPORT_JSON}`")
md.append(f"- Markdown audit: `{REPORT_MD}`")
md.append("")

REPORT_MD.write_text(
    "\n".join(md),
    encoding="utf-8",
)


# =====================================================================
# 35. FINAL OUTPUT
# =====================================================================

print()
print("=" * 100)
print("MLAI V4.1.8 DEFINITIVE AUDIT + ROBUST FIX COMPLETE")
print("=" * 100)
print()

print("SOURCE")
print("------")
print("V4.1.7 :", SRC)
print("SHA256  :", source_hash(SRC))
print()

print("CREATED")
print("-------")
print("V4.1.8 :", DST)
print("SHA256  :", generated_hash)
print()

print("BACKUP")
print("------")
print("Backup  :", BACKUP)
print()

print("REPAIR")
print("------")
print("Similarity engine       : NOT MODIFIED")
print("Similarity weights      : NOT MODIFIED")
print("Ranking                 : NOT MODIFIED")
print("Episode deduplication   : NOT MODIFIED")
print("Outcome aggregation     : NOT MODIFIED")
print("Causality               : NOT MODIFIED")
print("Reporting contract      : NOT MODIFIED")
print()
print("Sparse rule             : REPAIRED")
print("Similarity threshold    : 0.60")
print("Required effective      : 8")
print()

print("VALIDATION")
print("----------")

for name, passed in post_checks.items():
    print(
        f"{'PASS' if passed else 'FAIL':<6} : {name}"
    )

print()
print("AST validation           : PASS")
print("Python compilation      : PASS")
print()

print("PROTECTION")
print("----------")
print("V4.1.7          : NOT MODIFIED")
print("market_data.bin : NOT MODIFIED")
print("Memory          : NOT MODIFIED")
print("Production      : NOT MODIFIED")
print()

print("REPORTS")
print("-------")
print("Markdown :", REPORT_MD)
print("JSON     :", REPORT_JSON)
print()

print("NEXT COMMAND ONLY:")
print("python .\\mlai_market_structure_v418.py")
print()

print("=" * 100)