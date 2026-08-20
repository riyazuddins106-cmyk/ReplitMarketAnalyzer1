import inspect
import mlai_market_structure_v416 as m

print("=" * 110)
print("MLAI v4.1.6 — DATA LOADING / NORMALIZATION BOUNDARY INSPECTION")
print("=" * 110)

for name in (
    "load_market_data",
    "_normalize_candle",
    "calculate_atr",
    "build_structure_states",
):
    print()
    print("=" * 110)
    print("FUNCTION:", name)
    print("=" * 110)

    if hasattr(m, name):
        obj = getattr(m, name)

        try:
            print("SIGNATURE:", inspect.signature(obj))
        except Exception as exc:
            print("SIGNATURE ERROR:", exc)

        try:
            print(inspect.getsource(obj))
        except Exception as exc:
            print("SOURCE ERROR:", exc)
    else:
        print("NOT FOUND")

print()
print("=" * 110)
print("RUNTIME TYPE CHECK")
print("=" * 110)

raw = m.load_market_data(m.MARKET_DATA_FILE)

print("raw type:", type(raw))
print("raw length:", len(raw))

if raw:
    print("first item type:", type(raw[0]))
    print("first item:", raw[0])

    if isinstance(raw[0], (list, tuple)):
        print("first item length:", len(raw[0]))

print()
print("=" * 110)
print("DATA BOUNDARY INSPECTION COMPLETE — NO SOURCE FILES MODIFIED")
print("=" * 110)
