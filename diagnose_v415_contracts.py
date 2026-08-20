from pathlib import Path
import ast
import inspect
import importlib
import traceback

TARGET = Path("mlai_market_structure_v415.py")

print("=" * 100)
print("MLAI v4.1.5 — SECOND FORENSIC DIAGNOSTIC")
print("=" * 100)

# =====================================================================
# 1. SYNTAX
# =====================================================================

print()
print("-" * 100)
print("1. PYTHON SYNTAX CHECK")
print("-" * 100)

source = TARGET.read_text(encoding="utf-8")

try:
    ast.parse(source, filename=str(TARGET))
    print("SYNTAX: PASS")
except SyntaxError as exc:
    print("SYNTAX: FAIL")
    print(f"{type(exc).__name__}: {exc}")
    print(f"line={exc.lineno}, offset={exc.offset}")
    print(repr(exc.text))

# =====================================================================
# 2. IMPORT
# =====================================================================

print()
print("-" * 100)
print("2. MODULE IMPORT")
print("-" * 100)

try:
    module = importlib.import_module("mlai_market_structure_v415")
    print("IMPORT: PASS")
except Exception as exc:
    print("IMPORT: FAIL")
    print(f"{type(exc).__name__}: {exc}")
    traceback.print_exc()
    raise SystemExit(1)

# =====================================================================
# 3. SIGNATURES
# =====================================================================

print()
print("-" * 100)
print("3. TARGET FUNCTION SIGNATURES")
print("-" * 100)

targets = [
    "build_market_states",
    "assign_episode_ids",
    "build_experience_records",
    "similarity_score",
    "retrieve_historical_experience",
    "build_path_vector",
    "calculate_atr",
    "compute_atr",
]

for name in targets:
    obj = getattr(module, name, None)

    if obj is None:
        print(f"{name}: MISSING")
        continue

    try:
        print(f"{name}: {inspect.signature(obj)}")
    except Exception as exc:
        print(f"{name}: signature unavailable: {exc}")

# =====================================================================
# 4. LOAD DATA
# =====================================================================

print()
print("-" * 100)
print("4. DATA / CORE OBJECTS")
print("-" * 100)

try:
    candles = getattr(module, "CANDLES", None)

    if candles is None:
        candles = getattr(module, "candles", None)

    if candles is None:
        data_file = getattr(module, "MARKET_DATA_FILE", "market_data.bin")
        loader = getattr(module, "load_market_data", None)

        if loader is None:
            raise RuntimeError(
                "Could not find CANDLES/candles/load_market_data."
            )

        candles = loader(data_file)

    print(f"candles type: {type(candles).__name__}")
    print(f"candles count: {len(candles)}")

except Exception as exc:
    print("DATA LOAD: FAIL")
    print(f"{type(exc).__name__}: {exc}")
    traceback.print_exc()
    raise SystemExit(1)

# =====================================================================
# 5. ATR
# =====================================================================

print()
print("-" * 100)
print("5. ATR EXECUTION")
print("-" * 100)

atr_fn = (
    getattr(module, "calculate_atr", None)
    or getattr(module, "compute_atr", None)
)

if atr_fn is None:
    print("ATR: MISSING")
    raise SystemExit(1)

try:
    atr = atr_fn(candles)

    print("ATR: PASS")
    print(f"type={type(atr).__name__}")
    print(f"length={len(atr)}")

except Exception as exc:
    print("ATR: FAIL")
    print(f"{type(exc).__name__}: {exc}")
    traceback.print_exc()
    raise SystemExit(1)

# =====================================================================
# 6. STRUCTURE ENGINE
# =====================================================================

print()
print("-" * 100)
print("6. STRUCTURE ENGINE EXECUTION")
print("-" * 100)

engine_cls = getattr(module, "CausalStructureEngine", None)

if engine_cls is None:
    engine_cls = getattr(module, "MarketStructureEngine", None)

if engine_cls is None:
    print("STRUCTURE ENGINE: MISSING")
    raise SystemExit(1)

try:
    engine = engine_cls(candles)
    structure = engine.build()

    print("STRUCTURE ENGINE: PASS")
    print(f"engine={engine_cls.__name__}")
    print(f"structure type={type(structure).__name__}")
    print(f"structure length={len(structure)}")

except Exception as exc:
    print("STRUCTURE ENGINE: FAIL")
    print(f"{type(exc).__name__}: {exc}")
    traceback.print_exc()
    raise SystemExit(1)

# =====================================================================
# 7. EXTRACT STRUCTURE STATES
# =====================================================================

print()
print("-" * 100)
print("7. STRUCTURE STATE EXTRACTION")
print("-" * 100)

state_cls = getattr(module, "StructureState", None)

if state_cls is None:
    print("StructureState: MISSING")
    raise SystemExit(1)

structure_states = []

def collect(value):
    if isinstance(value, (list, tuple)):
        for x in value:
            collect(x)

    elif isinstance(value, dict):
        for x in value.values():
            collect(x)

    elif isinstance(value, state_cls):
        structure_states.append(value)

collect(structure)

print(f"StructureState objects found: {len(structure_states)}")

if len(structure_states) != len(candles):
    print("STATE COUNT: WARNING")
else:
    print("STATE COUNT: PASS")

# =====================================================================
# 8. CORRECT build_market_states ARGUMENT ORDER
# =====================================================================

print()
print("-" * 100)
print("8. BUILD MARKET STATES — ACTUAL SIGNATURE ORDER")
print("-" * 100)

market_state_fn = getattr(module, "build_market_states", None)

if market_state_fn is None:
    print("build_market_states: MISSING")
    raise SystemExit(1)

try:
    market_states = market_state_fn(
        candles,
        structure_states,
        atr,
    )

    print("BUILD MARKET STATES: PASS")
    print(f"type={type(market_states).__name__}")
    print(f"length={len(market_states)}")

except Exception as exc:
    print("BUILD MARKET STATES: FAIL")
    print(f"{type(exc).__name__}: {exc}")
    traceback.print_exc()
    raise SystemExit(1)

# =====================================================================
# 9. EPISODE IDS
# =====================================================================

print()
print("-" * 100)
print("9. EPISODE IDS")
print("-" * 100)

episode_fn = getattr(module, "assign_episode_ids", None)

if episode_fn is None:
    print("assign_episode_ids: MISSING")
else:
    try:
        episode_ids = episode_fn(market_states)

        print("EPISODES: PASS")
        print(f"type={type(episode_ids).__name__}")
        print(f"count={len(episode_ids)}")

    except Exception as exc:
        print("EPISODES: FAIL")
        print(f"{type(exc).__name__}: {exc}")
        traceback.print_exc()
        episode_ids = None

# =====================================================================
# 10. EXPERIENCE RECORDS
# =====================================================================

print()
print("-" * 100)
print("10. EXPERIENCE RECORD GENERATION")
print("-" * 100)

experience_fn = getattr(module, "build_experience_records", None)

if experience_fn is None:
    print("EXPERIENCE: MISSING")
    records = []
elif episode_ids is None:
    print("EXPERIENCE: BLOCKED — episode IDs unavailable")
    records = []
else:
    try:
        train_end = len(candles) // 2
        horizon = 8

        records = experience_fn(
            candles,
            atr,
            market_states,
            episode_ids,
            0,
            train_end,
            horizon,
        )

        print("EXPERIENCE: PASS")
        print(f"records={len(records)}")
        print(f"train_end={train_end}")
        print(f"horizon={horizon}")

        violations = []

        for r in records:
            idx = int(r.index)

            if idx >= train_end:
                violations.append(
                    f"index {idx} >= train_end {train_end}"
                )

            if idx + horizon > train_end:
                violations.append(
                    f"index {idx} + {horizon} > train_end {train_end}"
                )

        if violations:
            print("BOUNDARY: FAIL")
            for x in violations[:20]:
                print(" ", x)
        else:
            print("BOUNDARY: PASS")

    except Exception as exc:
        print("EXPERIENCE: FAIL")
        print(f"{type(exc).__name__}: {exc}")
        traceback.print_exc()
        records = []

# =====================================================================
# 11. SIMILARITY — ACTUAL CONTRACT
# =====================================================================

print()
print("-" * 100)
print("11. SIMILARITY CONTRACT TEST")
print("-" * 100)

similarity_fn = getattr(module, "similarity_score", None)

if similarity_fn is None:
    print("SIMILARITY: MISSING")

elif not records:
    print("SIMILARITY: BLOCKED — no records")

else:
    try:
        record = records[0]
        current = market_states[int(record.index)]

        score = similarity_fn(
            current,
            record,
        )

        print("SIMILARITY: PASS")
        print(f"return type={type(score).__name__}")

        if isinstance(score, dict):
            print("keys=", sorted(score.keys()))

            if "total" in score:
                print(f"total={score['total']}")

        else:
            print("WARNING: expected dictionary-like component score")

    except Exception as exc:
        print("SIMILARITY: FAIL")
        print(f"{type(exc).__name__}: {exc}")
        traceback.print_exc()

# =====================================================================
# 12. STRUCTURE PREFIX INVARIANCE
# =====================================================================

print()
print("-" * 100)
print("12. STRUCTURE PREFIX CAUSALITY")
print("-" * 100)

try:
    boundary = len(candles) // 2

    original_prefix = candles[:boundary]

    mutated = list(candles)

    for i in range(boundary, len(mutated)):
        c = mutated[i]

        # Preserve timestamp but alter only suffix prices.
        mutated[i] = type(c)(
            timestamp=c.timestamp,
            open=c.open + 1000.0,
            high=c.high + 1000.0,
            low=c.low + 1000.0,
            close=c.close + 1000.0,
            volume=getattr(c, "volume", None),
        )

    mutated_engine = engine_cls(mutated)
    mutated_structure = mutated_engine.build()

    original_prefix_states = structure[:boundary]
    mutated_prefix_states = mutated_structure[:boundary]

    if len(original_prefix_states) != len(mutated_prefix_states):
        print("PREFIX CAUSALITY: FAIL — length mismatch")

    else:
        mismatches = []

        for i, (a, b) in enumerate(
            zip(original_prefix_states, mutated_prefix_states)
        ):
            if a != b:
                mismatches.append(i)

        if mismatches:
            print("PREFIX CAUSALITY: FAIL")
            print(
                f"mismatches={len(mismatches)}"
            )
            print(
                "first mismatches=",
                mismatches[:20]
            )
        else:
            print("PREFIX CAUSALITY: PASS")
            print(
                f"{boundary} historical structure states unchanged "
                "after suffix mutation."
            )

except Exception as exc:
    print("PREFIX CAUSALITY: ERROR")
    print(f"{type(exc).__name__}: {exc}")
    traceback.print_exc()

# =====================================================================
# FINAL
# =====================================================================

print()
print("=" * 100)
print("SECOND FORENSIC DIAGNOSTIC COMPLETE")
print("=" * 100)
print("SOURCE WAS NOT MODIFIED.")
print("market_data.bin WAS NOT MODIFIED.")
print("NO v4.1.6 WAS CREATED.")
print("=" * 100)
