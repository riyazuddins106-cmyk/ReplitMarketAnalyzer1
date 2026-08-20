from pathlib import Path

p = Path("mlai_market_structure_v415.py")
s = p.read_text(encoding="utf-8")

print("=" * 100)
print("MLAI v4.1.5 — VERIFIED DEFECT SOURCE INVESTIGATION")
print("=" * 100)

# ------------------------------------------------------------
# 1. Find market-state implementation
# ------------------------------------------------------------

print("\n" + "=" * 100)
print("1. MARKET STATE FUNCTIONS")
print("=" * 100)

lines = s.splitlines()

for i, line in enumerate(lines, 1):
    low = line.lower()

    if (
        "def build_market_states" in low
        or "def build_market_state" in low
        or "def market_state" in low
        or "def compute_market_state" in low
    ):
        start = max(1, i - 5)
        end = min(len(lines), i + 180)

        print(f"\n--- SOURCE LINES {start}-{end} ---")
        for n in range(start, end + 1):
            print(f"{n:5}: {lines[n - 1]}")

# ------------------------------------------------------------
# 2. Experience-memory implementation
# ------------------------------------------------------------

print("\n" + "=" * 100)
print("2. EXPERIENCE MEMORY FUNCTIONS")
print("=" * 100)

for i, line in enumerate(lines, 1):
    low = line.lower()

    if (
        "def build_experience_records" in low
        or "def assign_episode_ids" in low
        or "def similarity_score" in low
        or "last_low" in low
    ):
        start = max(1, i - 8)
        end = min(len(lines), i + 180)

        print(f"\n--- SOURCE LINES {start}-{end} ---")
        for n in range(start, end + 1):
            print(f"{n:5}: {lines[n - 1]}")

# ------------------------------------------------------------
# 3. Prefix / mutation-sensitive state code
# ------------------------------------------------------------

print("\n" + "=" * 100)
print("3. PREFIX CAUSALITY / FUTURE-DEPENDENCY AREAS")
print("=" * 100)

keywords = (
    "build_market_states",
    "mutate_suffix",
    "swing",
    "last_high",
    "last_low",
    "future",
    "state",
    "confirmed",
    "right",
    "SWING_RIGHT",
)

seen = set()

for i, line in enumerate(lines, 1):
    low = line.lower()

    if any(k.lower() in low for k in keywords):
        start = max(1, i - 3)
        end = min(len(lines), i + 5)

        block_key = (start, end)

        if block_key in seen:
            continue

        seen.add(block_key)

        print(f"\n--- SOURCE LINES {start}-{end} ---")
        for n in range(start, end + 1):
            print(f"{n:5}: {lines[n - 1]}")

# ------------------------------------------------------------
# 4. Exact dataclass/class definitions relevant to failures
# ------------------------------------------------------------

print("\n" + "=" * 100)
print("4. RELEVANT CLASSES / DATACLASSES")
print("=" * 100)

for i, line in enumerate(lines, 1):
    low = line.lower()

    if (
        line.startswith("class ")
        and any(
            x in low
            for x in (
                "state",
                "experience",
                "episode",
                "structure",
                "candle",
            )
        )
    ):
        start = max(1, i - 3)
        end = min(len(lines), i + 100)

        print(f"\n--- SOURCE LINES {start}-{end} ---")
        for n in range(start, end + 1):
            print(f"{n:5}: {lines[n - 1]}")

# ------------------------------------------------------------
# 5. Exact audit test logic for the three failures
# ------------------------------------------------------------

audit = Path("audit_mlai_v415_full_capability.py")

if audit.exists():
    a = audit.read_text(encoding="utf-8").splitlines()

    print("\n" + "=" * 100)
    print("5. AUDITOR TEST IMPLEMENTATIONS")
    print("=" * 100)

    for i, line in enumerate(a, 1):
        low = line.lower()

        if any(
            x in low
            for x in (
                "market_state_causality",
                "experience_memory",
                "global_prefix_causality",
                "mutate_suffix",
            )
        ):
            start = max(1, i - 8)
            end = min(len(a), i + 100)

            print(f"\n--- AUDITOR LINES {start}-{end} ---")
            for n in range(start, end + 1):
                print(f"{n:5}: {a[n - 1]}")

print("\n" + "=" * 100)
print("INVESTIGATION COMPLETE")
print("=" * 100)
print("No engine source was modified.")
print("market_data.bin was not modified.")
print("No v4.1.6 was created.")
print("=" * 100)
