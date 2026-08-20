import inspect
import mlai_market_structure_v416 as m

print("=" * 100)
print("MLAI v4.1.6 — DATA BOUNDARY — TARGETED INSPECTION")
print("=" * 100)

# ---------------------------------------------------------------
# 1. Loader
# ---------------------------------------------------------------

print()
print("=" * 100)
print("LOAD_MARKET_DATA")
print("=" * 100)

print(inspect.signature(m.load_market_data))
print(inspect.getsource(m.load_market_data))

# ---------------------------------------------------------------
# 2. Normalizer
# ---------------------------------------------------------------

print()
print("=" * 100)
print("_NORMALIZE_CANDLE")
print("=" * 100)

print(inspect.signature(m._normalize_candle))
print(inspect.getsource(m._normalize_candle))

# ---------------------------------------------------------------
# 3. ATR
# ---------------------------------------------------------------

print()
print("=" * 100)
print("CALCULATE_ATR")
print("=" * 100)

print(inspect.signature(m.calculate_atr))
print(inspect.getsource(m.calculate_atr))

# ---------------------------------------------------------------
# 4. Runtime boundary — NO candle contents
# ---------------------------------------------------------------

print()
print("=" * 100)
print("RUNTIME TYPE / SHAPE")
print("=" * 100)

raw = m.load_market_data(m.MARKET_DATA_FILE)

print("raw type:", type(raw).__name__)
print("raw length:", len(raw))

if raw:
    first = raw[0]

    print("first item type:", type(first).__name__)

    if isinstance(first, (list, tuple)):
        print("first item length:", len(first))
        print("first item element types:",
              [type(x).__name__ for x in first])
    elif hasattr(first, "__dict__"):
        print("first item fields:", list(first.__dict__.keys()))
    else:
        print("first item has no list/tuple/dict structure")

print()
print("=" * 100)
print("TARGETED INSPECTION COMPLETE — NO SOURCE FILES MODIFIED")
print("=" * 100)
