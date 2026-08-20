import inspect
import mlai_market_structure_v416 as m

print("=" * 110)
print("MLAI v4.1.6 — PATH SIMILARITY LOGIC INSPECTION")
print("=" * 110)

for name in (
    "path_row_similarity",
    "path_similarity",
    "similarity_score",
):
    print()
    print("=" * 110)
    print("FUNCTION:", name)
    print("=" * 110)

    obj = getattr(m, name)

    print("SIGNATURE:", inspect.signature(obj))
    print(inspect.getsource(obj))

print()
print("=" * 110)
print("PATH LOGIC INSPECTION COMPLETE — NO SOURCE FILES MODIFIED")
print("=" * 110)
