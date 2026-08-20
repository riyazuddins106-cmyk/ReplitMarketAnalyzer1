from pathlib import Path
import ast
import hashlib
import shutil
import py_compile
from datetime import datetime
import importlib

SOURCE = Path("mlai_market_structure_v415.py")


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def find_functions(source_text):
    tree = ast.parse(source_text)

    result = {}

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            result[node.name] = node

    return result


print("=" * 100)
print("MLAI v4.1.5 - COMPLETE REPAIRED HELPER DEFINITION-ORDER FIX")
print("=" * 100)

if not SOURCE.exists():
    raise FileNotFoundError(SOURCE)

before_hash = sha256(SOURCE)

print()
print("SOURCE:")
print(SOURCE.resolve())

print()
print("SHA256 BEFORE:")
print(before_hash)

source_text = SOURCE.read_text(encoding="utf-8")

functions = find_functions(source_text)

required = [
    "_mlai_fix_safe_float",
    "_mlai_fix_similarity_total",
    "_mlai_fix_outcome_direction",
    "_mlai_fix_class_evidence",
    "_mlai_fix_predict_from_evidence",
    "mlai_v415_repaired_prediction",
    "main",
]

print()
print("1. FUNCTION DISCOVERY")
print("-" * 100)

for name in required:
    if name not in functions:
        raise RuntimeError(f"Required function not found: {name}")

    node = functions[name]
    print(f"{name:<42}: line {node.lineno}-{node.end_lineno}")

main_node = functions["main"]
anchor_node = functions["_mlai_fix_outcome_direction"]

safe_node = functions["_mlai_fix_safe_float"]
similarity_node = functions["_mlai_fix_similarity_total"]

print()
print("2. CONFIRMED PROBLEM")
print("-" * 100)

print(
    f"_mlai_fix_safe_float      : line {safe_node.lineno} "
    f"(AFTER main line {main_node.lineno})"
)

print(
    f"_mlai_fix_similarity_total: line {similarity_node.lineno} "
    f"(AFTER main line {main_node.lineno})"
)

if safe_node.lineno < main_node.lineno:
    raise RuntimeError(
        "_mlai_fix_safe_float is already before main; refusing unnecessary move."
    )

if similarity_node.lineno < main_node.lineno:
    raise RuntimeError(
        "_mlai_fix_similarity_total is already before main; refusing unnecessary move."
    )

if anchor_node.lineno >= main_node.lineno:
    raise RuntimeError(
        "_mlai_fix_outcome_direction is not before main; "
        "expected repaired prediction block to remain before main."
    )

print()
print("Confirmed:")
print("  Both missing runtime dependencies are defined after main().")
print("  Both must be moved before the repaired prediction layer.")

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

backup = SOURCE.with_name(
    f"mlai_market_structure_v415_BACKUP_BEFORE_HELPER_ORDER_FIX_{timestamp}.py"
)

shutil.copy2(SOURCE, backup)

print()
print("3. BACKUP CREATED")
print("-" * 100)
print(backup.resolve())

lines = source_text.splitlines(keepends=True)


def extract_node(node):
    return "".join(lines[node.lineno - 1:node.end_lineno])


# Extract the exact existing function bodies.
safe_text = extract_node(safe_node)
similarity_text = extract_node(similarity_node)

# Remove the two original definitions.
ranges = sorted(
    [
        (safe_node.lineno - 1, safe_node.end_lineno),
        (similarity_node.lineno - 1, similarity_node.end_lineno),
    ],
    reverse=True,
)

new_lines = lines[:]

for start, end in ranges:
    del new_lines[start:end]

# Reparse after removal so we can locate the anchor accurately.
intermediate_text = "".join(new_lines)
intermediate_lines = intermediate_text.splitlines(keepends=True)

intermediate_functions = find_functions(intermediate_text)

anchor_after = intermediate_functions["_mlai_fix_outcome_direction"]

# Insert safe_float first, then similarity_total, immediately before
# _mlai_fix_outcome_direction.
insertion = (
    safe_text
    + "\n\n"
    + similarity_text
    + "\n\n"
)

insert_at = anchor_after.lineno - 1

intermediate_lines[insert_at:insert_at] = [insertion]

patched_text = "".join(intermediate_lines)

# Parse before writing.
ast.parse(patched_text)

SOURCE.write_text(patched_text, encoding="utf-8")

after_hash = sha256(SOURCE)

print()
print("4. PATCH APPLIED")
print("-" * 100)
print("Moved:")
print("  _mlai_fix_safe_float")
print("  _mlai_fix_similarity_total")
print()
print("Destination:")
print("  Immediately before _mlai_fix_outcome_direction")
print()
print("Implementations changed:")
print("  NO")
print("Prediction mathematics changed:")
print("  NO")
print("market_data.bin changed:")
print("  NO")
print("MLAI version changed:")
print("  NO")

print()
print("SHA256 AFTER:")
print(after_hash)

print()
print("5. SYNTAX CHECK")
print("-" * 100)

py_compile.compile(
    str(SOURCE),
    doraise=True,
)

print("SYNTAX: PASS")

# Reparse final source and verify exact ordering.
final_text = SOURCE.read_text(encoding="utf-8")
final_functions = find_functions(final_text)

print()
print("6. FINAL DEFINITION ORDER")
print("-" * 100)

order = [
    "_mlai_fix_safe_float",
    "_mlai_fix_similarity_total",
    "_mlai_fix_outcome_direction",
    "_mlai_fix_class_evidence",
    "_mlai_fix_predict_from_evidence",
    "mlai_v415_repaired_prediction",
    "main",
]

positions = {
    name: final_functions[name].lineno
    for name in order
}

for name in order:
    print(f"{name:<42}: line {positions[name]}")

main_line = positions["main"]

for name in order:
    if name == "main":
        continue

    if positions[name] >= main_line:
        raise RuntimeError(
            f"Definition-order verification failed: {name} "
            f"is not before main()."
        )

print()
print("DEFINITION ORDER: PASS")

print()
print("7. DEPENDENCY ORDER")
print("-" * 100)

if not (
    positions["_mlai_fix_safe_float"]
    < positions["_mlai_fix_similarity_total"]
    < positions["_mlai_fix_outcome_direction"]
    < positions["_mlai_fix_class_evidence"]
    < positions["_mlai_fix_predict_from_evidence"]
    < positions["mlai_v415_repaired_prediction"]
    < positions["main"]
):
    raise RuntimeError("Complete repaired dependency chain is not ordered correctly.")

print(
    "_mlai_fix_safe_float"
    " -> _mlai_fix_similarity_total"
    " -> _mlai_fix_outcome_direction"
    " -> _mlai_fix_class_evidence"
    " -> _mlai_fix_predict_from_evidence"
    " -> mlai_v415_repaired_prediction"
    " -> main"
)

print()
print("DEPENDENCY ORDER: PASS")

print()
print("8. NORMAL IMPORT TEST")
print("-" * 100)

module = importlib.import_module("mlai_market_structure_v415")

checks = [
    "_mlai_fix_safe_float",
    "_mlai_fix_similarity_total",
    "_mlai_fix_outcome_direction",
    "_mlai_fix_class_evidence",
    "_mlai_fix_predict_from_evidence",
    "mlai_v415_repaired_prediction",
]

for name in checks:
    if not hasattr(module, name):
        raise RuntimeError(f"Import test failed: {name} missing")
    print(f"{name:<42}: FOUND")

print()
print("IMPORT: PASS")

print()
print("9. PROTECTION")
print("-" * 100)
print("market_data.bin: NOT MODIFIED")
print("No new MLAI version created.")

print()
print("=" * 100)
print("COMPLETE HELPER DEFINITION-ORDER FIX: PASS")
print("=" * 100)
