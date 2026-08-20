import inspect
import mlai_market_structure_v416 as m

print("=" * 100)
print("MLAI v4.1.6 — RETRIEVAL SIMILARITY INTERNAL AUDIT")
print("=" * 100)

print()
print("RETRIEVAL FUNCTION")
print("-" * 100)

source = inspect.getsource(m.retrieve_historical_experience)
print(source)

print()
print("=" * 100)
print("NUMERIC SIMILARITY FUNCTION")
print("=" * 100)

print(inspect.getsource(m.numeric_similarity))

print()
print("=" * 100)
print("PATH SIMILARITY FUNCTION")
print("=" * 100)

print(inspect.getsource(m.path_row_similarity))

print()
print("=" * 100)
print("ALL RETRIEVAL-RELATED DEFINITIONS")
print("=" * 100)

for name in dir(m):
    if any(
        key in name.lower()
        for key in (
            "similar",
            "retriev",
            "score",
            "dedup",
            "experience",
        )
    ):
        obj = getattr(m, name)

        if callable(obj):
            print()
            print(f"### {name}")
            try:
                print(inspect.signature(obj))
            except Exception:
                pass

            try:
                print(inspect.getsource(obj))
            except Exception:
                print("<source unavailable>")

print()
print("=" * 100)
print("DONE")
print("=" * 100)
