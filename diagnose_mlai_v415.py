import ast
import importlib
import inspect
from pathlib import Path

TARGET = Path("mlai_market_structure_v415.py")

print("=" * 100)
print("MLAI v4.1.5 — TARGETED FORENSIC DIAGNOSIS")
print("=" * 100)
print(f"Target: {TARGET.resolve()}")
print()

source = TARGET.read_text(encoding="utf-8")
tree = ast.parse(source)

# ================================================================
# 1. SHOW ACTUAL CLASSES
# ================================================================

print("=" * 100)
print("1. ACTUAL CLASS DEFINITIONS")
print("=" * 100)

classes = []

for node in ast.walk(tree):
    if isinstance(node, ast.ClassDef):
        classes.append(node)

if not classes:
    print("NO CLASSES FOUND")
else:
    for node in classes:
        methods = [
            n.name
            for n in node.body
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]

        print(f"\nCLASS: {node.name}")
        print(f"LINE : {node.lineno}")
        print("METHODS:")
        for method in methods:
            print(f"  - {method}")

# ================================================================
# 2. STRUCTURE-RELATED SYMBOLS
# ================================================================

print()
print("=" * 100)
print("2. STRUCTURE-RELATED SYMBOLS")
print("=" * 100)

for node in ast.walk(tree):
    if isinstance(node, ast.ClassDef):
        if any(x in node.name.lower() for x in ("structure", "swing", "state")):
            print(f"CLASS: {node.name} (line {node.lineno})")

    elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        if any(x in node.name.lower() for x in ("structure", "swing", "state", "build")):
            print(f"FUNCTION: {node.name} (line {node.lineno})")

# ================================================================
# 3. CHECK WHETHER StructureEngine ACTUALLY EXISTS
# ================================================================

print()
print("=" * 100)
print("3. StructureEngine EXISTENCE CHECK")
print("=" * 100)

structure_engine_defs = [
    node
    for node in ast.walk(tree)
    if isinstance(node, ast.ClassDef)
    and node.name == "StructureEngine"
]

if structure_engine_defs:
    print("StructureEngine EXISTS in source.")
    for node in structure_engine_defs:
        print(f"  line {node.lineno}")
else:
    print("StructureEngine DOES NOT EXIST in source.")
    print()
    print("Therefore an auditor requiring module.StructureEngine is")
    print("making an architectural assumption that is not supported by")
    print("the current source.")

# ================================================================
# 4. IMPORT MODULE AND SHOW REAL EXPORTED SYMBOLS
# ================================================================

print()
print("=" * 100)
print("4. RUNTIME EXPORTED SYMBOLS")
print("=" * 100)

try:
    module = importlib.import_module("mlai_market_structure_v415")

    names = sorted(
        name for name in dir(module)
        if not name.startswith("__")
    )

    for name in names:
        obj = getattr(module, name)

        if (
            inspect.isclass(obj)
            or inspect.isfunction(obj)
        ):
            print(f"{name:40} {type(obj).__name__}")

except Exception as exc:
    print("IMPORT FAILED")
    print(type(exc).__name__, str(exc))

# ================================================================
# 5. EXACT FUTURE-INDEX EXPRESSIONS
# ================================================================

print()
print("=" * 100)
print("5. EXACT FUTURE-INDEX EXPRESSIONS")
print("=" * 100)

lines = source.splitlines()

future_hits = []

for node in ast.walk(tree):

    # ----------------------------
    # Subscript: candles[index + X]
    # ----------------------------
    if isinstance(node, ast.Subscript):

        text = ast.get_source_segment(source, node)

        if text and (
            "index +" in text
            or "index+" in text
            or "target" in text
        ):
            future_hits.append(
                (
                    node.lineno,
                    "SUBSCRIPT",
                    text.strip()
                )
            )

    # ----------------------------
    # Range/slice expressions
    # ----------------------------
    elif isinstance(node, ast.Slice):

        text = ast.get_source_segment(source, node)

        if text and (
            "index +" in text
            or "index+" in text
            or "target" in text
        ):
            future_hits.append(
                (
                    node.lineno,
                    "SLICE",
                    text.strip()
                )
            )

    # ----------------------------
    # Binary index arithmetic
    # ----------------------------
    elif isinstance(node, ast.BinOp):

        text = ast.get_source_segment(source, node)

        if text and (
            "index +" in text
            or "index+" in text
            or "target" in text
        ):
            future_hits.append(
                (
                    node.lineno,
                    "ARITHMETIC",
                    text.strip()
                )
            )

# Deduplicate
seen = set()

for line_no, kind, text in sorted(future_hits):
    key = (line_no, kind, text)

    if key in seen:
        continue

    seen.add(key)

    print(f"\nLINE {line_no} [{kind}]")
    print(f"  {text}")

    start = max(1, line_no - 2)
    end = min(len(lines), line_no + 2)

    print("  CONTEXT:")

    for n in range(start, end + 1):
        marker = ">>" if n == line_no else "  "
        print(f"  {marker} {n:5}: {lines[n-1]}")

# ================================================================
# 6. IDENTIFY FUNCTIONS CONTAINING FUTURE REFERENCES
# ================================================================

print()
print("=" * 100)
print("6. FUNCTIONS CONTAINING FUTURE REFERENCES")
print("=" * 100)

function_nodes = [
    node
    for node in ast.walk(tree)
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
]

for fn in sorted(function_nodes, key=lambda x: x.lineno):

    fn_end = getattr(fn, "end_lineno", fn.lineno)

    hits = [
        (line_no, kind, text)
        for line_no, kind, text in future_hits
        if fn.lineno <= line_no <= fn_end
    ]

    if not hits:
        continue

    print()
    print(f"FUNCTION: {fn.name}")
    print(f"LINES   : {fn.lineno}-{fn_end}")

    for line_no, kind, text in hits:
        print(f"  line {line_no}: {text}")

# ================================================================
# 7. CLASSIFY KNOWN OUTCOME FUNCTIONS
# ================================================================

print()
print("=" * 100)
print("7. OUTCOME / LABEL FUNCTIONS")
print("=" * 100)

for fn in sorted(function_nodes, key=lambda x: x.lineno):

    name = fn.name.lower()

    if any(word in name for word in (
        "outcome",
        "evaluation",
        "evaluate",
        "validation",
        "null",
        "permutation",
    )):
        print(
            f"{fn.name:40} lines "
            f"{fn.lineno}-{getattr(fn, 'end_lineno', fn.lineno)}"
        )

# ================================================================
# 8. FINAL TARGETED INTERPRETATION
# ================================================================

print()
print("=" * 100)
print("TARGETED DIAGNOSIS")
print("=" * 100)

print()
print("StructureEngine:")
if structure_engine_defs:
    print("  FOUND")
    print("  Auditor expectation is structurally valid.")
else:
    print("  NOT FOUND")
    print("  The previous StructureEngine FAIL is an auditor/API mismatch")
    print("  unless another symbol is explicitly intended to be the engine.")

print()
print(f"Future-index expressions discovered: {len(seen)}")

print()
print("IMPORTANT:")
print("This script does NOT modify the MLAI source.")
print("This script does NOT modify market_data.bin.")
print("This is a targeted diagnosis only.")
print()
print("END")
