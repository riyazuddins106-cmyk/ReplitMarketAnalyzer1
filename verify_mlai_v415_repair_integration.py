# inspect_mlai_v415_structure_and_prediction_path.py
#
# READ ONLY.
# Does not modify MLAI source or market data.
#
# PURPOSE:
#   1. Determine exactly what CausalStructureEngine.states contains.
#   2. Determine how build_market_states() is supposed to receive structure.
#   3. Locate the actual walk-forward / forensic prediction path.
#   4. Locate every caller of retrieve_historical_experience().
#   5. Locate the actual prediction functions.
#
# We will use this output to make ONE targeted fix.

from pathlib import Path
import ast
import hashlib
import inspect
import importlib
import sys

SOURCE = Path("mlai_market_structure_v415.py")

print("=" * 110)
print("MLAI v4.1.5 — STRUCTURE PIPELINE + PREDICTION PATH INSPECTION")
print("=" * 110)

if not SOURCE.exists():
    raise SystemExit(f"Missing source: {SOURCE}")

text = SOURCE.read_text(encoding="utf-8")
tree = ast.parse(text)

print()
print("SOURCE SHA256:")
print(hashlib.sha256(text.encode("utf-8")).hexdigest())

# ---------------------------------------------------------------------
# AST helpers
# ---------------------------------------------------------------------

functions = {}
classes = {}

for node in ast.walk(tree):
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        functions[node.name] = node
    elif isinstance(node, ast.ClassDef):
        classes[node.name] = node


def source_of(node):
    try:
        return ast.get_source_segment(text, node) or ""
    except Exception:
        return ""


def calls_in(node, target):
    hits = []

    for child in ast.walk(node):
        if isinstance(child, ast.Call):

            fn = child.func

            if isinstance(fn, ast.Name) and fn.id == target:
                hits.append(child)

            elif isinstance(fn, ast.Attribute) and fn.attr == target:
                hits.append(child)

    return hits


# ---------------------------------------------------------------------
# 1. Import
# ---------------------------------------------------------------------

print()
print("=" * 110)
print("1. IMPORT")
print("=" * 110)

sys.path.insert(0, str(SOURCE.parent.resolve()))

if SOURCE.stem in sys.modules:
    del sys.modules[SOURCE.stem]

m = importlib.import_module(SOURCE.stem)

print("IMPORT: PASS")


# ---------------------------------------------------------------------
# 2. CausalStructureEngine inspection
# ---------------------------------------------------------------------

print()
print("=" * 110)
print("2. CAUSAL STRUCTURE ENGINE")
print("=" * 110)

if "CausalStructureEngine" not in classes:
    raise SystemExit("CausalStructureEngine class not found.")

engine_cls = m.CausalStructureEngine

print()
print("CLASS SOURCE:")
print("-" * 110)
print(source_of(classes["CausalStructureEngine"]))

candles, meta = m.load_market_data("market_data.bin")

print()
print("CANDLES:", len(candles))

engine = engine_cls(candles)

print()
print("ENGINE INSTANCE ATTRIBUTES:")

for name in sorted(vars(engine)):
    try:
        value = getattr(engine, name)
        if isinstance(value, (list, tuple, dict, set)):
            print(
                f"{name:35} type={type(value).__name__:15} "
                f"len={len(value)}"
            )
        else:
            print(
                f"{name:35} type={type(value).__name__:15} "
                f"value={repr(value)[:100]}"
            )
    except Exception as exc:
        print(f"{name:35} ERROR={exc}")


# ---------------------------------------------------------------------
# 3. build_market_states source
# ---------------------------------------------------------------------

print()
print("=" * 110)
print("3. build_market_states() EXACT SOURCE")
print("=" * 110)

if "build_market_states" not in functions:
    raise SystemExit("build_market_states not found.")

print(source_of(functions["build_market_states"]))


# ---------------------------------------------------------------------
# 4. Find ALL calls to build_market_states
# ---------------------------------------------------------------------

print()
print("=" * 110)
print("4. CALLERS OF build_market_states()")
print("=" * 110)

found = False

for name, node in functions.items():
    calls = calls_in(node, "build_market_states")

    if calls:
        found = True

        print()
        print("FUNCTION:", name)

        for call in calls:
            print("CALL:")
            print(source_of(call))

if not found:
    print("No function caller found.")


# ---------------------------------------------------------------------
# 5. Find structure engine usage
# ---------------------------------------------------------------------

print()
print("=" * 110)
print("5. ALL CausalStructureEngine USAGE")
print("=" * 110)

for name, node in functions.items():

    body = source_of(node)

    if "CausalStructureEngine" in body:

        print()
        print("FUNCTION:", name)
        print("-" * 110)

        for line in body.splitlines():
            if (
                "CausalStructureEngine" in line
                or ".states" in line
                or "structure" in line.lower()
            ):
                print(line)


# ---------------------------------------------------------------------
# 6. retrieve_historical_experience callers
# ---------------------------------------------------------------------

print()
print("=" * 110)
print("6. ALL CALLERS OF retrieve_historical_experience()")
print("=" * 110)

retrieval_callers = []

for name, node in functions.items():

    calls = calls_in(node, "retrieve_historical_experience")

    if calls:

        retrieval_callers.append(name)

        print()
        print("FUNCTION:", name)
        print("-" * 110)

        for call in calls:
            print(source_of(call))

if not retrieval_callers:
    print()
    print("!!! NO CALLERS FOUND !!!")
    print()
    print(
        "This would strongly indicate that the repaired retrieval function "
        "is not connected to the evaluated prediction pipeline."
    )


# ---------------------------------------------------------------------
# 7. Find every function containing prediction decisions
# ---------------------------------------------------------------------

print()
print("=" * 110)
print("7. PREDICTION / DECISION PIPELINE FUNCTIONS")
print("=" * 110)

prediction_terms = [
    "prediction",
    "predict",
    "decision",
    "majority",
    "top_5",
    "top_10",
    "top_20",
    "vote_5",
    "vote_10",
    "vote_20",
    "power_1",
    "power_2",
    "power_4",
    "accuracy",
    "balanced_accuracy",
    "macro_f1",
    "walk_forward",
    "forensic",
    "evaluate",
    "test",
]

prediction_functions = []

for name, node in functions.items():

    body = source_of(node).lower()

    hits = [term for term in prediction_terms if term in body]

    if hits:
        prediction_functions.append((name, hits))

for name, hits in prediction_functions:

    print()
    print(f"{name}")
    print("  matches:", ", ".join(hits))


# ---------------------------------------------------------------------
# 8. Show candidate prediction function sources
# ---------------------------------------------------------------------

print()
print("=" * 110)
print("8. CANDIDATE PREDICTION FUNCTION SOURCE")
print("=" * 110)

for name, hits in prediction_functions:

    if any(
        x in hits
        for x in [
            "prediction",
            "predict",
            "decision",
            "majority",
            "top_5",
            "top_10",
            "top_20",
            "vote_5",
            "vote_10",
            "vote_20",
            "power_1",
            "power_2",
            "power_4",
            "walk_forward",
            "forensic",
        ]
    ):

        print()
        print("=" * 110)
        print("FUNCTION:", name)
        print("=" * 110)
        print(source_of(functions[name]))


# ---------------------------------------------------------------------
# 9. Search source text for retrieval call
# ---------------------------------------------------------------------

print()
print("=" * 110)
print("9. RAW SOURCE REFERENCES TO retrieve_historical_experience")
print("=" * 110)

lines = text.splitlines()

for number, line in enumerate(lines, start=1):

    if "retrieve_historical_experience" in line:

        print(f"{number:5}: {line}")


# ---------------------------------------------------------------------
# 10. Search for direct fixed-rule prediction implementation
# ---------------------------------------------------------------------

print()
print("=" * 110)
print("10. RAW FIXED-RULE REFERENCES")
print("=" * 110)

for number, line in enumerate(lines, start=1):

    if any(
        term in line
        for term in [
            "power_1",
            "power_2",
            "power_4",
            "top_5",
            "top_10",
            "top_20",
            "vote_5",
            "vote_10",
            "vote_20",
        ]
    ):

        print(f"{number:5}: {line}")


# ---------------------------------------------------------------------
# 11. Final interpretation
# ---------------------------------------------------------------------

print()
print("=" * 110)
print("11. INTERPRETATION")
print("=" * 110)

print()
print("This inspection is READ ONLY.")
print()
print("We specifically need to establish:")
print()
print("A. What structure sequence build_market_states() actually expects.")
print("B. How the production/forensic pipeline constructs that structure.")
print("C. Whether retrieve_historical_experience() is actually called.")
print("D. Which function produces the H4/H8/H16 predictions.")
print("E. Whether the fixed-rule results are produced by a separate legacy")
print("   evaluation path that bypasses the repaired retrieval layer.")
print()
print("Do NOT modify mlai_market_structure_v415.py after this test.")
print("Do NOT create another version.")
print()
print("=" * 110)
print("INSPECTION COMPLETE")
print("=" * 110)