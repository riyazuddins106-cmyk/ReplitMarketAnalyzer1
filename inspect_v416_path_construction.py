import inspect
import mlai_market_structure_v416 as m

print("=" * 110)
print("MLAI v4.1.6 — PATH CONSTRUCTION FORENSIC INSPECTION")
print("=" * 110)

# Find functions/methods that appear related to path construction.
names = [
    name
    for name in dir(m)
    if "path" in name.lower()
]

print()
print("PATH-RELATED OBJECTS")
print("-" * 110)

for name in names:
    obj = getattr(m, name)

    print()
    print("NAME:", name)
    print("TYPE:", type(obj).__name__)

    try:
        print("SIGNATURE:", inspect.signature(obj))
    except Exception as exc:
        print("SIGNATURE ERROR:", exc)

    try:
        source = inspect.getsource(obj)
        print(source)
    except Exception as exc:
        print("SOURCE ERROR:", exc)

print()
print("=" * 110)
print("PATH CONSTRUCTION INSPECTION COMPLETE — NO SOURCE FILES MODIFIED")
print("=" * 110)
