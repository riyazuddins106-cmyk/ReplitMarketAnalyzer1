from pathlib import Path
import importlib
import inspect
import traceback

print("=" * 100)
print("MLAI v4.1.5 — DATA OBJECT FORENSIC INSPECTION")
print("=" * 100)

module = importlib.import_module("mlai_market_structure_v415")

# =====================================================================
# 1. MODULE DATA-RELATED NAMES
# =====================================================================

print()
print("-" * 100)
print("1. MODULE DATA-RELATED OBJECTS")
print("-" * 100)

for name in sorted(dir(module)):
    if any(x in name.lower() for x in (
        "candle",
        "market_data",
        "data",
        "load",
    )):
        try:
            obj = getattr(module, name)
            print()
            print(f"NAME: {name}")
            print(f"TYPE: {type(obj).__name__}")

            if isinstance(obj, (list, tuple, dict)):
                print(f"LEN: {len(obj)}")

                if isinstance(obj, (list, tuple)) and len(obj) > 0:
                    first = obj[0]
                    print(f"FIRST TYPE: {type(first).__name__}")
                    print(f"FIRST REPR: {repr(first)[:500]}")

        except Exception as exc:
            print(f"ERROR READING {name}: {exc}")

# =====================================================================
# 2. CANDLE CLASS
# =====================================================================

print()
print("-" * 100)
print("2. CANDLE CLASS")
print("-" * 100)

candle_cls = getattr(module, "Candle", None)

if candle_cls is None:
    print("Candle class: MISSING")
else:
    print("Candle class: FOUND")
    print("signature:", end=" ")

    try:
        print(inspect.signature(candle_cls))
    except Exception as exc:
        print(f"unavailable ({exc})")

    print()
    print("annotations:")
    print(getattr(candle_cls, "__annotations__", {}))

# =====================================================================
# 3. CANDLES GLOBAL — FULL TYPE STRUCTURE
# =====================================================================

print()
print("-" * 100)
print("3. MODULE.CANDLES STRUCTURE")
print("-" * 100)

candles = getattr(module, "CANDLES", None)

print("CANDLES exists:", candles is not None)
print("CANDLES type:", type(candles).__name__)

if candles is not None:

    try:
        print("CANDLES length:", len(candles))
    except Exception:
        pass

    try:
        for i, value in enumerate(candles):
            print()
            print(f"CANDLES[{i}]")
            print("  type:", type(value).__name__)
            print("  repr:", repr(value)[:1000])

            if isinstance(value, (list, tuple)):
                print("  nested length:", len(value))

                if len(value):
                    print(
                        "  nested first type:",
                        type(value[0]).__name__
                    )
                    print(
                        "  nested first repr:",
                        repr(value[0])[:1000]
                    )

    except Exception as exc:
        print("CANDLES inspection failed:", exc)

# =====================================================================
# 4. LOAD MARKET DATA FUNCTION
# =====================================================================

print()
print("-" * 100)
print("4. LOAD MARKET DATA FUNCTION")
print("-" * 100)

loader = getattr(module, "load_market_data", None)

if loader is None:
    print("load_market_data: MISSING")
else:
    print("load_market_data: FOUND")
    print("signature:", inspect.signature(loader))
    print("module:", getattr(loader, "__module__", None))
    print("source:")
    try:
        print(inspect.getsource(loader))
    except Exception as exc:
        print("SOURCE UNAVAILABLE:", exc)

# =====================================================================
# 5. MARKET DATA FILE
# =====================================================================

print()
print("-" * 100)
print("5. MARKET DATA CONFIGURATION")
print("-" * 100)

for name in (
    "MARKET_DATA_FILE",
    "DATA_FILE",
    "CANDLES",
):
    if hasattr(module, name):
        obj = getattr(module, name)
        print(f"{name}: type={type(obj).__name__}")
        print(f"{name}: repr={repr(obj)[:1000]}")

# =====================================================================
# 6. DIRECT LOAD — DO NOT USE CANDLES GLOBAL
# =====================================================================

print()
print("-" * 100)
print("6. DIRECT market_data.bin LOAD")
print("-" * 100)

data_file = getattr(module, "MARKET_DATA_FILE", "market_data.bin")
print("data_file:", data_file)

if loader is None:
    print("DIRECT LOAD: BLOCKED — loader missing")
else:
    try:
        loaded = loader(data_file)

        print("DIRECT LOAD: PASS")
        print("loaded type:", type(loaded).__name__)

        try:
            print("loaded length:", len(loaded))
        except Exception:
            pass

        if isinstance(loaded, (list, tuple)) and len(loaded):
            first = loaded[0]

            print("first element type:", type(first).__name__)
            print("first element repr:", repr(first)[:1000])

            if candle_cls is not None:
                print(
                    "first element is Candle:",
                    isinstance(first, candle_cls)
                )

            required = ("timestamp", "open", "high", "low", "close")

            print()
            print("required Candle attributes:")

            for attr in required:
                print(
                    f"  {attr}:",
                    hasattr(first, attr)
                )

    except Exception as exc:
        print("DIRECT LOAD: FAIL")
        print(f"{type(exc).__name__}: {exc}")
        traceback.print_exc()

# =====================================================================
# 7. SOURCE INITIALIZATION AROUND CANDLES
# =====================================================================

print()
print("-" * 100)
print("7. SOURCE LOCATIONS FOR CANDLES INITIALIZATION")
print("-" * 100)

source = Path("mlai_market_structure_v415.py").read_text(
    encoding="utf-8"
)

lines = source.splitlines()

for i, line in enumerate(lines):
    if "CANDLES" in line or "load_market_data" in line:
        print(f"{i + 1:5}: {line}")

# =====================================================================
# FINAL
# =====================================================================

print()
print("=" * 100)
print("DATA OBJECT FORENSIC INSPECTION COMPLETE")
print("=" * 100)
print("SOURCE WAS NOT MODIFIED.")
print("market_data.bin WAS NOT MODIFIED.")
print("=" * 100)
