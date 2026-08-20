from pathlib import Path

print("=" * 100)
print("MLAI CURRENT ARCHITECTURE AUDIT")
print("=" * 100)

root = Path.cwd()

print()
print("PROJECT ROOT:")
print(root)

print()
print("PYTHON FILES:")
print("-" * 100)

python_files = sorted(root.glob("*.py"))

for path in python_files:
    print(path.name)

print()
print("KEY MLAI FILES:")
print("-" * 100)

patterns = [
    "mlai_market_structure_v415.py",
    "mlai_market_structure_v*.py",
    "mlai_*.py",
]

found = set()

for pattern in patterns:
    for path in sorted(root.glob(pattern)):
        found.add(path.name)

for name in sorted(found):
    print(name)

print()
print("DATA / MEMORY / REPORT FILES:")
print("-" * 100)

patterns = [
    "*.bin",
    "*.md",
    "*.json",
    "*.pkl",
    "*.pickle",
]

for pattern in patterns:
    for path in sorted(root.glob(pattern)):
        print(path.name)

print()
print("PROTECTION CHECK:")
print("-" * 100)

protected = root / "market_data.bin"

if protected.exists():
    print("market_data.bin : FOUND")
    print("market_data.bin : NOT MODIFIED BY THIS AUDIT")
else:
    print("market_data.bin : NOT FOUND")

print()
print("V4.1.5:")
print("-" * 100)

v415 = root / "mlai_market_structure_v415.py"

if v415.exists():
    print("mlai_market_structure_v415.py : FOUND")
else:
    print("mlai_market_structure_v415.py : NOT FOUND")

print()
print("AUDIT RESULT:")
print("-" * 100)
print("Architecture inventory completed.")
print("No MLAI source files were modified.")
print("No market data was modified.")
print("No learning memory was modified.")

print()
print("=" * 100)
print("AUDIT COMPLETE")
print("=" * 100)
