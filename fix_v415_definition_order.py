from pathlib import Path
import ast
import shutil
import hashlib
from datetime import datetime

SOURCE = Path("mlai_market_structure_v415.py")

TARGET_FUNCTIONS = [
    "_mlai_fix_outcome_direction",
    "_mlai_fix_class_evidence",
    "_mlai_fix_predict_from_evidence",
    "mlai_v415_repaired_prediction",
]

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


print("=" * 100)
print("MLAI v4.1.5 — REPAIRED PREDICTIVE DEFINITION-ORDER FIX")
print("=" * 100)

if not SOURCE.exists():
    raise FileNotFoundError(f"Source not found: {SOURCE.resolve()}")

before_hash = sha256_file(SOURCE)

print()
print("SOURCE:")
print(SOURCE.resolve())
print()
print("SHA256 BEFORE:")
print(before_hash)

source = SOURCE.read_text(encoding="utf-8")

# ---------------------------------------------------------------------
# Parse source
# ---------------------------------------------------------------------

tree = ast.parse(source)

top_level_functions = {}

for node in tree.body:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        top_level_functions[node.name] = node

if "main" not in top_level_functions:
    raise RuntimeError("main() was not found.")

missing = [
    name for name in TARGET_FUNCTIONS
    if name not in top_level_functions
]

if missing:
    raise RuntimeError(
        "Required repaired function(s) not found:\n"
        + "\n".join(f"  - {name}" for name in missing)
    )

main_node = top_level_functions["main"]

print()
print("FOUND:")
for name in TARGET_FUNCTIONS:
    node = top_level_functions[name]
    print(
        f"  {name:<38} "
        f"lines {node.lineno}-{node.end_lineno}"
    )

print(
    f"  {'main':<38} "
    f"lines {main_node.lineno}-{main_node.end_lineno}"
)

# ---------------------------------------------------------------------
# Verify the problem actually exists
# ---------------------------------------------------------------------

for name in TARGET_FUNCTIONS:
    if top_level_functions[name].lineno < main_node.lineno:
        raise RuntimeError(
            f"{name} is already before main(). "
            "The expected definition-order bug is not present."
        )

print()
print("CONFIRMED:")
print("All repaired predictive functions are defined AFTER main().")
print("This is the cause of the direct-execution NameError.")

# ---------------------------------------------------------------------
# Backup
# ---------------------------------------------------------------------

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

backup = SOURCE.with_name(
    f"mlai_market_structure_v415_BACKUP_BEFORE_DEFINITION_ORDER_FIX_{timestamp}.py"
)

shutil.copy2(SOURCE, backup)

print()
print("BACKUP CREATED:")
print(backup.resolve())

# ---------------------------------------------------------------------
# Extract exact top-level function source blocks.
#
# We use AST line boundaries rather than fragile string matching.
# ---------------------------------------------------------------------

lines = source.splitlines(keepends=True)

def node_text(node):
    start = node.lineno - 1
    end = node.end_lineno
    return "".join(lines[start:end])

blocks = {
    name: node_text(top_level_functions[name])
    for name in TARGET_FUNCTIONS
}

# ---------------------------------------------------------------------
# Remove the four functions from their current locations.
#
# Process from bottom to top so line positions remain valid.
# ---------------------------------------------------------------------

ranges = []

for name in TARGET_FUNCTIONS:
    node = top_level_functions[name]

    start = node.lineno - 1
    end = node.end_lineno

    ranges.append((start, end, name))

ranges.sort(reverse=True)

new_lines = list(lines)

for start, end, name in ranges:
    del new_lines[start:end]

source_without_repaired_functions = "".join(new_lines)

# ---------------------------------------------------------------------
# Re-parse after removal and locate main().
# ---------------------------------------------------------------------

tree2 = ast.parse(source_without_repaired_functions)

main2 = None

for node in tree2.body:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        if node.name == "main":
            main2 = node
            break

if main2 is None:
    raise RuntimeError("main() disappeared after removing repaired functions.")

lines2 = source_without_repaired_functions.splitlines(keepends=True)

# Insert immediately before main().
main_start = main2.lineno - 1

# Keep a clean separation between the repaired predictive layer
# and the existing main() function.
repair_block = (
    "\n"
    "# =====================================================================\n"
    "# REPAIRED PREDICTIVE LAYER\n"
    "# Must be defined before main() because main() executes this path.\n"
    "# =====================================================================\n\n"
)

for name in TARGET_FUNCTIONS:
    repair_block += blocks[name].rstrip() + "\n\n"

repair_block += "# =====================================================================\n"

lines2.insert(main_start, repair_block)

patched_source = "".join(lines2)

# ---------------------------------------------------------------------
# Syntax check before writing.
# ---------------------------------------------------------------------

compile(
    patched_source,
    str(SOURCE),
    "exec",
)

print()
print("SYNTAX CHECK: PASS")

# ---------------------------------------------------------------------
# Write patched source.
# ---------------------------------------------------------------------

SOURCE.write_text(patched_source, encoding="utf-8")

after_hash = sha256_file(SOURCE)

print()
print("PATCH APPLIED.")
print()
print("SHA256 AFTER:")
print(after_hash)

# ---------------------------------------------------------------------
# Verify ordering using AST.
# ---------------------------------------------------------------------

verify_tree = ast.parse(patched_source)

verify_positions = {}

for node in verify_tree.body:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        verify_positions[node.name] = node.lineno

print()
print("=" * 100)
print("POST-PATCH DEFINITION ORDER")
print("=" * 100)

for name in TARGET_FUNCTIONS:
    print(
        f"{name:<38}: line {verify_positions[name]}"
    )

print(
    f"{'main':<38}: line {verify_positions['main']}"
)

if not all(
    verify_positions[name] < verify_positions["main"]
    for name in TARGET_FUNCTIONS
):
    raise RuntimeError(
        "Definition-order verification failed."
    )

print()
print("DEFINITION ORDER: PASS")
print("All repaired predictive functions are now defined before main().")

# ---------------------------------------------------------------------
# Normal import test.
# ---------------------------------------------------------------------

print()
print("=" * 100)
print("NORMAL IMPORT TEST")
print("=" * 100)

import importlib
import sys

module_name = SOURCE.stem

if module_name in sys.modules:
    del sys.modules[module_name]

module = importlib.import_module(module_name)

print("IMPORT: PASS")
print(
    "mlai_v415_repaired_prediction:",
    hasattr(module, "mlai_v415_repaired_prediction")
)
print(
    "_mlai_fix_class_evidence:",
    hasattr(module, "_mlai_fix_class_evidence")
)
print(
    "_mlai_fix_predict_from_evidence:",
    hasattr(module, "_mlai_fix_predict_from_evidence")
)

if not hasattr(module, "mlai_v415_repaired_prediction"):
    raise RuntimeError(
        "Repaired prediction API missing after import."
    )

# ---------------------------------------------------------------------
# Final source inspection.
# ---------------------------------------------------------------------

final_source = SOURCE.read_text(encoding="utf-8")
final_tree = ast.parse(final_source)

final_positions = {}

for node in final_tree.body:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        final_positions[node.name] = node.lineno

print()
print("=" * 100)
print("FINAL VERIFICATION")
print("=" * 100)

for name in TARGET_FUNCTIONS:
    print(
        f"{name:<38}: {final_positions[name]} "
        f"< main({final_positions['main']})"
    )

print()
print("RESULT:")
print("PASS — repaired predictive layer is defined before main().")
print("PASS — source syntax is valid.")
print("PASS — normal module import succeeds.")
print("PASS — repaired prediction API is available.")
print()
print("market_data.bin: NOT MODIFIED")
print("No new MLAI version created.")
print()
print("=" * 100)
print("DEFINITION-ORDER FIX COMPLETE")
print("=" * 100)