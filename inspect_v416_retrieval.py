import inspect
import mlai_market_structure_v416 as m

print("=" * 110)
print("MLAI v4.1.6 — RETRIEVAL IMPLEMENTATION INSPECTION")
print("=" * 110)

# ---------------------------------------------------------------------
# 1. COARSE FILTER IMPLEMENTATION
# ---------------------------------------------------------------------

print()
print("=" * 110)
print("COARSE FILTER FUNCTION")
print("=" * 110)

for name in dir(m):
    if "candidate" in name.lower() or "filter" in name.lower():
        obj = getattr(m, name)
        if callable(obj):
            try:
                print()
                print("FUNCTION:", name)
                print("-" * 110)
                print(inspect.getsource(obj))
            except Exception as exc:
                print("Could not inspect", name, ":", exc)


# ---------------------------------------------------------------------
# 2. SIMILARITY IMPLEMENTATION
# ---------------------------------------------------------------------

print()
print("=" * 110)
print("SIMILARITY FUNCTIONS")
print("=" * 110)

for name in (
    "similarity_score",
    "path_similarity",
    "numeric_similarity",
    "select_episode_representatives",
):
    if hasattr(m, name):
        print()
        print("FUNCTION:", name)
        print("-" * 110)
        try:
            print(inspect.getsource(getattr(m, name)))
        except Exception as exc:
            print("ERROR:", exc)


# ---------------------------------------------------------------------
# 3. RETRIEVAL FUNCTION
# ---------------------------------------------------------------------

print()
print("=" * 110)
print("RETRIEVAL-RELATED FUNCTIONS")
print("=" * 110)

for name in dir(m):
    if any(
        token in name.lower()
        for token in (
            "retriev",
            "experience",
            "match",
            "candidate",
        )
    ):
        obj = getattr(m, name)
        if callable(obj):
            print()
            print("FUNCTION:", name)
            print("-" * 110)
            try:
                print(inspect.getsource(obj))
            except Exception as exc:
                print("ERROR:", exc)


# ---------------------------------------------------------------------
# 4. PATH CONSTANTS
# ---------------------------------------------------------------------

print()
print("=" * 110)
print("PATH / SIMILARITY CONSTANTS")
print("=" * 110)

for name in sorted(dir(m)):
    if any(
        token in name.upper()
        for token in (
            "PATH",
            "WEIGHT",
            "SIMILARITY",
            "RETRIEVAL",
            "MATCH",
            "HISTORY",
        )
    ):
        value = getattr(m, name)

        if not callable(value):
            print(f"{name:<40} = {value!r}")


print()
print("=" * 110)
print("INSPECTION COMPLETE — NO SOURCE FILES MODIFIED")
print("=" * 110)
