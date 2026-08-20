from pathlib import Path

p = Path("mlai_market_structure_v415.py")
s = p.read_text(encoding="utf-8")

targets = [
    "def build_market_states",
    "def assign_episode_ids",
    "def build_experience_records",
    "def similarity_score",
    "def build_path_vector",
    "class CausalStructureEngine",
    "class StructureState",
]

lines = s.splitlines()

print("=" * 100)
print("MLAI v4.1.5 — TARGET IMPLEMENTATION FORENSIC INSPECTION")
print("=" * 100)

for target in targets:

    matches = [
        i for i, line in enumerate(lines)
        if target in line
    ]

    print()
    print("-" * 100)
    print(target)

    if not matches:
        print("NOT FOUND")
        continue

    start = matches[0]

    # Print from the declaration until the next top-level
    # def/class declaration, or maximum 180 lines.
    end = min(len(lines), start + 180)

    for i in range(start + 1, end):
        stripped = lines[i].lstrip()

        if i > start + 1 and (
            stripped.startswith("def ")
            or stripped.startswith("class ")
        ) and not lines[i].startswith((" ", "\t")):
            end = i
            break

    print(f"Source lines {start + 1}-{end}")

    for i in range(start, end):
        print(f"{i + 1:5}: {lines[i]}")

print()
print("=" * 100)
print("INSPECTION COMPLETE")
print("=" * 100)
print("SOURCE WAS NOT MODIFIED.")
print("=" * 100)
