import inspect
import mlai_market_structure_v416 as m

print("=" * 110)
print("MLAI v4.1.6 — ACTUAL ATR / STATE BUILDER INSPECTION")
print("=" * 110)

for name in dir(m):
    obj = getattr(m, name)

    if callable(obj) and any(
        token in name.lower()
        for token in (
            "atr",
            "candle",
            "structure",
            "market_state",
            "build_market",
            "build_state",
        )
    ):
        print()
        print("FUNCTION:", name)
        print("-" * 110)

        try:
            print(inspect.signature(obj))
        except Exception:
            pass

        try:
            print(inspect.getsource(obj))
        except Exception as exc:
            print("SOURCE ERROR:", exc)

print()
print("=" * 110)
print("ATR / STATE INSPECTION COMPLETE — NO SOURCE FILES MODIFIED")
print("=" * 110)
