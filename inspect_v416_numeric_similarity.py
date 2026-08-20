import inspect
import mlai_market_structure_v416 as m

print("=" * 110)
print("MLAI v4.1.6 — NUMERIC SIMILARITY FORENSIC INSPECTION")
print("=" * 110)

name = "numeric_similarity"

print()
print("=" * 110)
print("FUNCTION:", name)
print("=" * 110)

obj = getattr(m, name)

print("SIGNATURE:", inspect.signature(obj))
print(inspect.getsource(obj))

print()
print("=" * 110)
print("RUNTIME PROBE")
print("=" * 110)

tests = [
    (0.0, 0.0, 1.0),
    (0.1, 0.0, 1.0),
    (0.5, 0.0, 1.0),
    (1.0, 0.0, 1.0),
    (-1.0, 1.0, 1.0),
    (-0.5, 0.5, 1.0),
    (0.5, -0.5, 1.0),
    (1.0, -1.0, 1.0),
    (2.0, 0.0, 1.0),
]

for a, b, scale in tests:
    try:
        result = obj(a, b, scale)
        print(
            f"a={a:7.3f} "
            f"b={b:7.3f} "
            f"scale={scale:5.2f} "
            f"similarity={result:.9f}"
        )
    except Exception as exc:
        print(
            f"a={a:7.3f} "
            f"b={b:7.3f} "
            f"ERROR={type(exc).__name__}: {exc}"
        )

print()
print("=" * 110)
print("NUMERIC SIMILARITY INSPECTION COMPLETE — NO SOURCE FILES MODIFIED")
print("=" * 110)
