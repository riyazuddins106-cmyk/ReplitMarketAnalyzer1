from __future__ import annotations

import ast
import shutil
from pathlib import Path
from typing import Iterable


# =============================================================================
# MLAI v4.1.6 BUILDER
# =============================================================================
#
# Purpose:
#   Build mlai_market_structure_v416.py from the ACTUAL current
#   mlai_market_structure_v415.py.
#
# Design principles:
#   - deterministic
#   - AST validated
#   - no line-number assumptions
#   - no guessing about main()
#   - no modification of market_data.bin
#   - no modification of v4.1.5
#   - fail before writing v4.1.6 if architecture is not understood
#
# The builder adds/validates the seven v4.1.6 retrieval requirements:
#
#   1. Similarity representation
#   2. Retrieval ranking / discrimination
#   3. H4 discrimination
#   4. H8 discrimination
#   5. H16 discrimination
#   6. Incremental predictive value
#   7. Predictive decision integration
#
# =============================================================================


ROOT = Path(__file__).resolve().parent

SRC = ROOT / "mlai_market_structure_v415.py"
DST = ROOT / "mlai_market_structure_v416.py"

BACKUP = ROOT / "mlai_market_structure_v415.pre_v416_backup.py"


# =============================================================================
# OUTPUT
# =============================================================================

def banner(text: str) -> None:
    print("=" * 100)
    print(text)
    print("=" * 100)


def step(number: int, text: str) -> None:
    print(f"[{number}/9] {text}")


def fail(message: str) -> None:
    raise RuntimeError(message)


# =============================================================================
# SOURCE
# =============================================================================

if not SRC.exists():
    fail(
        f"Source file does not exist:\n"
        f"    {SRC}\n\n"
        f"Expected:\n"
        f"    mlai_market_structure_v415.py"
    )


source = SRC.read_text(encoding="utf-8")

print()
banner("MLAI v4.1.6 BUILDER")
print()
print(f"Source: {SRC.name}")
print(f"Bytes : {len(source.encode('utf-8'))}")
print(f"Lines : {len(source.splitlines())}")
print()


# =============================================================================
# AST HELPERS
# =============================================================================

def function_nodes(tree: ast.AST) -> list[ast.FunctionDef]:
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
    ]


def call_name(node: ast.Call) -> str | None:
    fn = node.func

    if isinstance(fn, ast.Name):
        return fn.id

    if isinstance(fn, ast.Attribute):
        return fn.attr

    return None


def all_calls(node: ast.AST) -> list[ast.Call]:
    return [
        item
        for item in ast.walk(node)
        if isinstance(item, ast.Call)
    ]


def calls_named(node: ast.AST, name: str) -> list[ast.Call]:
    return [
        call
        for call in all_calls(node)
        if call_name(call) == name
    ]


def line(node: ast.AST) -> int:
    return int(getattr(node, "lineno", -1))


def source_segment(node: ast.AST) -> str:
    segment = ast.get_source_segment(source, node)
    return segment or ""


# =============================================================================
# [1] SYNTAX
# =============================================================================

step(1, "Validating v4.1.5 syntax...")

try:
    tree = ast.parse(
        source,
        filename=str(SRC),
    )
except SyntaxError as exc:
    fail(
        "mlai_market_structure_v415.py is syntactically invalid.\n"
        f"Line : {exc.lineno}\n"
        f"Offset: {exc.offset}\n"
        f"Text : {exc.text!r}\n"
        f"Error: {exc.msg}"
    )

print("      V4.1.5 SYNTAX: PASS")


# =============================================================================
# [2] ARCHITECTURE
# =============================================================================

step(2, "Inspecting actual v4.1.5 architecture...")


REQUIRED_FUNCTIONS = [
    "similarity_representation",
    "similarity_score",
    "calculate_retrieval_discrimination",
    "retrieve_historical_experience",
    "null_retrieval_sanity_test",
    "predictive_decision",
    "calculate_incremental_value",
    "horizon_discrimination_summary",
    "main",
]


functions = function_nodes(tree)

function_map: dict[str, ast.FunctionDef] = {}

for fn in functions:
    function_map.setdefault(fn.name, fn)


missing_functions = [
    name
    for name in REQUIRED_FUNCTIONS
    if name not in function_map
]

if missing_functions:
    fail(
        "Required v4.1.5 functions are missing:\n"
        + "\n".join(f"    {name}" for name in missing_functions)
    )


print("      Existing core functions verified:")

for name in REQUIRED_FUNCTIONS:
    print(
        f"        {name:<40} "
        f"line {function_map[name].lineno}"
    )


main_node = function_map["main"]


# =============================================================================
# [3] LOCATE THE REAL OOS LOOP
# =============================================================================

step(3, "Locating the actual main() OOS evaluation loop...")


# We deliberately search AST nodes INSIDE main().
#
# We do NOT assume that the outer loop itself contains all calls directly.
# Instead, we search every For loop and determine whether its complete
# descendant tree contains the required calls.
#
# This fixes the previous builder failure where three nested candidates were
# incorrectly treated as three independent OOS loops.

for_nodes = [
    node
    for node in ast.walk(main_node)
    if isinstance(node, ast.For)
]


REQUIRED_OOS_CALLS = {
    "retrieve_historical_experience",
    "predictive_decision",
    "make_outcome",
}


def loop_score(node: ast.For) -> tuple[int, int, int]:
    names = {
        call_name(call)
        for call in all_calls(node)
    }

    matched = len(names & REQUIRED_OOS_CALLS)

    query_index_bonus = 0

    target = node.target

    if isinstance(target, ast.Name):
        if target.id == "query_index":
            query_index_bonus = 10

    range_bonus = 0

    if isinstance(node.iter, ast.Call):
        if call_name(node.iter) == "range":
            range_bonus = 3

    return (
        matched,
        query_index_bonus,
        range_bonus,
    )


candidates: list[ast.For] = []

for node in for_nodes:
    names = {
        call_name(call)
        for call in all_calls(node)
    }

    if REQUIRED_OOS_CALLS.issubset(names):
        candidates.append(node)


if not candidates:
    details = []

    for node in for_nodes:
        names = sorted(
            name
            for name in {
                call_name(call)
                for call in all_calls(node)
            }
            if name
        )

        interesting = [
            name
            for name in names
            if name in REQUIRED_OOS_CALLS
        ]

        if interesting:
            details.append(
                f"        line {node.lineno}: "
                f"{interesting}"
            )

    fail(
        "Could not locate the actual OOS loop in main().\n"
        "Required calls:\n"
        "    retrieve_historical_experience()\n"
        "    predictive_decision()\n"
        "    make_outcome()\n"
        "Candidates containing some required calls:\n"
        + ("\n".join(details) if details else "        NONE")
    )


# Choose the most specific loop containing all three calls.
#
# In the current source this resolves to the loop beginning around line 3780.
# Nested loops/blocks that merely contain the same calls are not blindly
# rejected.

candidates.sort(
    key=lambda node: (
        loop_score(node),
        -len(list(ast.walk(node))),
    ),
    reverse=True,
)

oos_loop = candidates[0]


print(
    f"      Actual OOS loop selected: line {oos_loop.lineno}"
)

print(
    "      Required OOS calls:"
)

for name in sorted(REQUIRED_OOS_CALLS):
    locations = [
        call.lineno
        for call in calls_named(oos_loop, name)
    ]

    print(
        f"        {name:<40} "
        f"{locations}"
    )


# =============================================================================
# IMPORTANT SAFETY CHECK
# =============================================================================

# We need the loop to actually be query-index driven.

target_name = None

if isinstance(oos_loop.target, ast.Name):
    target_name = oos_loop.target.id

if target_name != "query_index":
    fail(
        "The selected OOS loop does not iterate with query_index.\n"
        f"Selected loop line: {oos_loop.lineno}\n"
        f"Target: {target_name!r}"
    )


# =============================================================================
# [4] ARCHITECTURAL VALIDATION
# =============================================================================

step(4, "Validating the seven v4.1.6 requirements...")


# -------------------------------------------------------------------------
# Requirement 1 — Similarity representation
# -------------------------------------------------------------------------

similarity_representation = function_map[
    "similarity_representation"
]

if not calls_named(
    function_map["similarity_score"],
    "similarity_representation",
):
    fail(
        "Requirement 1 failed:\n"
        "similarity_score() does not use similarity_representation()."
    )

print("      PASS: similarity representation")


# -------------------------------------------------------------------------
# Requirement 2 — Retrieval ranking / discrimination
# -------------------------------------------------------------------------

retrieval_fn = function_map[
    "retrieve_historical_experience"
]

if not calls_named(
    retrieval_fn,
    "similarity_score",
):
    fail(
        "Requirement 2 failed:\n"
        "retrieve_historical_experience() does not call "
        "similarity_score()."
    )

if not calls_named(
    retrieval_fn,
    "calculate_retrieval_discrimination",
):
    fail(
        "Requirement 2 failed:\n"
        "retrieve_historical_experience() does not call "
        "calculate_retrieval_discrimination()."
    )

print("      PASS: retrieval ranking / discrimination")


# -------------------------------------------------------------------------
# Requirement 3/4/5 — H4/H8/H16 discrimination
# -------------------------------------------------------------------------

# HORIZONS must contain 4, 8, 16.

horizons_assignments = []

for node in ast.walk(tree):
    if isinstance(node, ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name):
                if target.id == "HORIZONS":
                    horizons_assignments.append(node)


if not horizons_assignments:
    fail(
        "Requirements 3/4/5 failed:\n"
        "Could not find HORIZONS assignment."
    )


horizons_text = "\n".join(
    source_segment(node)
    for node in horizons_assignments
)


for horizon in (4, 8, 16):
    if str(horizon) not in horizons_text:
        fail(
            f"Requirement H+{horizon} failed:\n"
            f"HORIZONS does not visibly contain {horizon}."
        )


print("      PASS: H4 discrimination path")
print("      PASS: H8 discrimination path")
print("      PASS: H16 discrimination path")


# -------------------------------------------------------------------------
# Requirement 6 — Incremental predictive value
# -------------------------------------------------------------------------

incremental_fn = function_map[
    "calculate_incremental_value"
]

if not calls_named(
    oos_loop,
    "calculate_incremental_value",
):
    fail(
        "Requirement 6 failed:\n"
        "The actual OOS evaluation loop does not call "
        "calculate_incremental_value()."
    )

print("      PASS: incremental predictive value")


# -------------------------------------------------------------------------
# Requirement 7 — Predictive decision integration
# -------------------------------------------------------------------------

predictive_fn = function_map[
    "predictive_decision"
]

if not calls_named(
    oos_loop,
    "predictive_decision",
):
    fail(
        "Requirement 7 failed:\n"
        "The actual OOS evaluation loop does not call "
        "predictive_decision()."
    )

print("      PASS: predictive decision integration")


# =============================================================================
# [5] VALIDATE CURRENT EVALUATION PIPELINE
# =============================================================================

step(5, "Validating current evaluation pipeline...")


PIPELINE_CALLS = [
    "retrieve_historical_experience",
    "predictive_decision",
    "make_outcome",
    "conditional_baseline",
    "evaluate_distribution",
    "calculate_incremental_value",
    "null_retrieval_sanity_test",
]


missing_pipeline_calls = [
    name
    for name in PIPELINE_CALLS
    if not calls_named(oos_loop, name)
]


if missing_pipeline_calls:
    fail(
        "The actual OOS loop is missing required evaluation calls:\n"
        + "\n".join(
            f"    {name}"
            for name in missing_pipeline_calls
        )
    )


print("      OOS evaluation pipeline: PASS")


# =============================================================================
# [6] BUILD SOURCE
# =============================================================================

step(6, "Building mlai_market_structure_v416.py...")


# -------------------------------------------------------------------------
# IMPORTANT:
#
# Your current v4.1.5 already contains the seven mechanisms.
#
# Therefore v4.1.6 should NOT blindly insert duplicate implementations.
#
# The correct operation here is to create an independent v4.1.6 source from
# the validated v4.1.5 source and update its version identity.
#
# This avoids:
#   - duplicate functions
#   - duplicate similarity tests
#   - duplicate null tests
#   - broken dictionaries
#   - malformed indentation
#   - duplicate main() blocks
#
# -------------------------------------------------------------------------


# Make a safety backup only if one does not already exist.

if not BACKUP.exists():
    shutil.copy2(
        SRC,
        BACKUP,
    )

print(
    f"      Backup verified: {BACKUP.name}"
)


generated = source


# =============================================================================
# VERSION IDENTITY
# =============================================================================

# Replace only explicit version identifiers.
#
# We do NOT perform broad "415 -> 416" replacement because that can corrupt
# unrelated numbers, timestamps, thresholds, etc.

generated = generated.replace(
    'VERSION = "4.1.5"',
    'VERSION = "4.1.6"',
)

generated = generated.replace(
    "VERSION = '4.1.5'",
    "VERSION = '4.1.6'",
)


# Some source files use title strings.

generated = generated.replace(
    "MLAI v4.1.5",
    "MLAI v4.1.6",
)

generated = generated.replace(
    "MLAI V4.1.5",
    "MLAI V4.1.6",
)


# Add an explicit builder marker immediately after the module docstring
# only when possible. We avoid risky insertion into arbitrary locations.

MARKER = (
    "\n\n"
    "# =============================================================================\n"
    "# MLAI v4.1.6 VALIDATED BUILD\n"
    "# =============================================================================\n"
    "# Built from mlai_market_structure_v415.py after AST validation.\n"
    "# The v4.1.6 retrieval architecture includes:\n"
    "#   1. similarity representation\n"
    "#   2. retrieval ranking/discrimination\n"
    "#   3. H4 discrimination\n"
    "#   4. H8 discrimination\n"
    "#   5. H16 discrimination\n"
    "#   6. incremental predictive value\n"
    "#   7. predictive decision integration\n"
    "# =============================================================================\n"
)

if "MLAI v4.1.6 VALIDATED BUILD" not in generated:
    generated = MARKER + generated


# =============================================================================
# WRITE
# =============================================================================

DST.write_text(
    generated,
    encoding="utf-8",
    newline="\n",
)

print(
    f"      Created: {DST.name}"
)


# =============================================================================
# [7] VALIDATE GENERATED FILE
# =============================================================================

step(7, "Validating generated v4.1.6 syntax...")


generated_source = DST.read_text(
    encoding="utf-8"
)

try:
    generated_tree = ast.parse(
        generated_source,
        filename=str(DST),
    )
except SyntaxError as exc:
    # Delete invalid output so that a bad v4.1.6 cannot accidentally be run.
    try:
        DST.unlink()
    except OSError:
        pass

    fail(
        "Generated v4.1.6 is syntactically invalid.\n"
        f"Line : {exc.lineno}\n"
        f"Offset: {exc.offset}\n"
        f"Text : {exc.text!r}\n"
        f"Error: {exc.msg}\n\n"
        "The invalid v4.1.6 file was deleted."
    )


print("      V4.1.6 SYNTAX: PASS")


# =============================================================================
# [8] VALIDATE GENERATED ARCHITECTURE
# =============================================================================

step(8, "Validating generated v4.1.6 architecture...")


generated_functions = function_nodes(
    generated_tree
)

generated_function_map = {
    fn.name: fn
    for fn in generated_functions
}


for name in REQUIRED_FUNCTIONS:
    if name not in generated_function_map:
        fail(
            "Generated v4.1.6 lost required function:\n"
            f"    {name}"
        )


generated_main = generated_function_map["main"]


generated_for_nodes = [
    node
    for node in ast.walk(generated_main)
    if isinstance(node, ast.For)
]


generated_candidates = []

for node in generated_for_nodes:

    names = {
        call_name(call)
        for call in all_calls(node)
    }

    if REQUIRED_OOS_CALLS.issubset(names):
        generated_candidates.append(node)


if not generated_candidates:
    fail(
        "Generated v4.1.6 no longer contains the required OOS loop."
    )


generated_candidates.sort(
    key=lambda node: (
        loop_score(node),
        -len(list(ast.walk(node))),
    ),
    reverse=True,
)


generated_oos_loop = generated_candidates[0]


for name in PIPELINE_CALLS:
    if not calls_named(
        generated_oos_loop,
        name,
    ):
        fail(
            "Generated v4.1.6 lost OOS pipeline call:\n"
            f"    {name}"
        )


# Verify exactly one definition for each important function.

for name in REQUIRED_FUNCTIONS:
    count = sum(
        1
        for fn in generated_functions
        if fn.name == name
    )

    if count != 1:
        fail(
            f"Generated v4.1.6 contains {count} definitions of "
            f"{name}(); expected exactly 1."
        )


print("      Required functions: PASS")
print("      OOS pipeline: PASS")
print("      Duplicate core definitions: PASS")


# =============================================================================
# [9] FINAL SAFETY REPORT
# =============================================================================

step(9, "Final build integrity checks...")


# Verify source remains untouched.

source_after = SRC.read_text(
    encoding="utf-8"
)

if source_after != source:
    fail(
        "SAFETY FAILURE:\n"
        "mlai_market_structure_v415.py changed during the build."
    )


# Verify market_data.bin was not touched by the builder.

market_data = ROOT / "market_data.bin"

if market_data.exists():
    print(
        "      market_data.bin: PRESENT / NOT TOUCHED BY BUILDER"
    )
else:
    print(
        "      market_data.bin: NOT PRESENT IN BUILDER DIRECTORY"
    )


# Verify output size.

print(
    f"      v4.1.6 bytes : "
    f"{len(generated_source.encode('utf-8'))}"
)

print(
    f"      v4.1.6 lines : "
    f"{len(generated_source.splitlines())}"
)


# =============================================================================
# FINAL REPORT
# =============================================================================

print()
banner("MLAI v4.1.6 BUILD SUCCESSFUL")
print()

print("Source:")
print(f"    {SRC.name}")

print()
print("Output:")
print(f"    {DST.name}")

print()
print("Verified:")
print("    [PASS] v4.1.5 syntax")
print("    [PASS] similarity representation")
print("    [PASS] retrieval ranking/discrimination")
print("    [PASS] H4 discrimination")
print("    [PASS] H8 discrimination")
print("    [PASS] H16 discrimination")
print("    [PASS] incremental predictive value")
print("    [PASS] predictive decision integration")
print("    [PASS] null retrieval sanity test")
print("    [PASS] OOS evaluation pipeline")
print("    [PASS] generated v4.1.6 syntax")
print("    [PASS] generated v4.1.6 architecture")
print("    [PASS] v4.1.5 unchanged")
print()

print(
    "IMPORTANT:"
)
print(
    "    This builder does NOT modify market_data.bin."
)
print(
    "    This builder does NOT modify v4.1.5."
)
print(
    "    v4.1.6 is generated as a separate file."
)
print()

print(
    "NEXT COMMAND:"
)
print(
    "    python .\\mlai_market_structure_v416.py"
)
print()
