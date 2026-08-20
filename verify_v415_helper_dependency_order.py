import inspect
import mlai_market_structure_v415 as m

print("=" * 100)
print("MLAI v4.1.5 - REPAIRED HELPER DEPENDENCY ORDER FORENSIC CHECK")
print("=" * 100)

source = inspect.getsource(m)
lines = source.splitlines()

def find_definition(name):
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("def " + name + "("):
            return i
    return None

names = [
    "_mlai_fix_safe_float",
    "_mlai_fix_similarity_total",
    "_mlai_fix_outcome_direction",
    "_mlai_fix_class_evidence",
    "_mlai_fix_predict_from_evidence",
    "mlai_v415_repaired_prediction",
    "main",
]

print()
print("1. DEFINITION POSITIONS")
print("-" * 100)

positions = {}

for name in names:
    line = find_definition(name)
    positions[name] = line
    print(f"{name:<42}: {line}")

print()
print("2. HELPER EXISTENCE")
print("-" * 100)

for name in names:
    print(f"{name:<42}: {hasattr(m, name)}")

print()
print("3. _mlai_fix_similarity_total SOURCE")
print("-" * 100)
print(inspect.getsource(m._mlai_fix_similarity_total))

print()
print("4. _mlai_fix_safe_float SOURCE")
print("-" * 100)

if hasattr(m, "_mlai_fix_safe_float"):
    print(inspect.getsource(m._mlai_fix_safe_float))
else:
    print("MISSING")

print()
print("5. ORDER CHECK")
print("-" * 100)

main_line = positions["main"]

for name in names:
    if name == "main":
        continue

    line = positions[name]

    if line is None:
        print(f"{name:<42}: MISSING")
    elif line < main_line:
        print(f"{name:<42}: BEFORE main - PASS")
    else:
        print(f"{name:<42}: AFTER main  - PROBLEM")

print()
print("6. ALL REFERENCES TO _mlai_fix_SAFE_FLOAT")
print("-" * 100)

for line_no, line in enumerate(lines, 1):
    if "_mlai_fix_safe_float" in line:
        print(f"{line_no}: {line}")

print()
print("=" * 100)
print("FORENSIC CHECK COMPLETE")
print("=" * 100)
