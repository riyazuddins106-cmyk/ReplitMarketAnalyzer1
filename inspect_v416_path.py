import inspect
import mlai_market_structure_v416 as m

print("=" * 110)
print("MLAI v4.1.6 — PATH VECTOR / PATH SIMILARITY FORENSIC INSPECTION")
print("=" * 110)

# ================================================================
# 1. PATH ROW SIMILARITY
# ================================================================

print()
print("=" * 110)
print("PATH ROW SIMILARITY")
print("=" * 110)

if hasattr(m, "path_row_similarity"):
    print(inspect.getsource(m.path_row_similarity))
else:
    print("ERROR: path_row_similarity not found")


# ================================================================
# 2. PATH VECTOR CONSTRUCTION
# ================================================================

print()
print("=" * 110)
print("PATH VECTOR REFERENCES")
print("=" * 110)

for name in dir(m):
    if "path" in name.lower():
        obj = getattr(m, name)

        print()
        print("NAME:", name)
        print("TYPE:", type(obj))

        if callable(obj):
            try:
                print(inspect.getsource(obj))
            except Exception as exc:
                print("SOURCE ERROR:", exc)


# ================================================================
# 3. MARKET STATE DEFINITION
# ================================================================

print()
print("=" * 110)
print("MARKET STATE DEFINITION")
print("=" * 110)

if hasattr(m, "MarketState"):
    print(inspect.getsource(m.MarketState))


# ================================================================
# 4. BUILD MARKET STATE FUNCTIONS
# ================================================================

print()
print("=" * 110)
print("STATE-BUILDING FUNCTIONS")
print("=" * 110)

for name in dir(m):
    if any(
        token in name.lower()
        for token in (
            "build_market",
            "market_state",
            "build_state",
            "state_from",
            "path_vector",
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
                print("SOURCE ERROR:", exc)


# ================================================================
# 5. PATH LENGTH / VECTOR SHAPE
# ================================================================

print()
print("=" * 110)
print("PATH CONFIGURATION")
print("=" * 110)

for name in sorted(dir(m)):
    if "PATH" in name.upper():
        value = getattr(m, name)

        if not callable(value):
            print(f"{name:<40} = {value!r}")


# ================================================================
# 6. NUMERIC SIMILARITY
# ================================================================

print()
print("=" * 110)
print("NUMERIC SIMILARITY")
print("=" * 110)

print(inspect.getsource(m.numeric_similarity))


print()
print("=" * 110)
print("PATH FORENSIC INSPECTION COMPLETE — NO SOURCE FILES MODIFIED")
print("=" * 110)
