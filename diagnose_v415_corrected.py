from pathlib import Path
import ast
import inspect
import importlib
import traceback

TARGET = Path("mlai_market_structure_v415.py")

print("=" * 100)
print("MLAI v4.1.5 — CORRECTED FULL CONTRACT FORENSIC DIAGNOSTIC")
print("=" * 100)

# =====================================================================
# 1. SYNTAX
# =====================================================================

print()
print("-" * 100)
print("1. PYTHON SYNTAX")
print("-" * 100)

source = TARGET.read_text(encoding="utf-8")

try:
    ast.parse(source, filename=str(TARGET))
    print("SYNTAX: PASS")
except Exception as exc:
    print("SYNTAX: FAIL")
    print(type(exc).__name__, exc)
    raise SystemExit(1)

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
    print(type(exc).__name__, exc)
    traceback.print_exc()
    raise SystemExit(1)

# =====================================================================
# 3. LOAD DATA — CORRECTLY UNPACK LOADER RETURN VALUE
# =====================================================================

print()
print("-" * 100)
print("3. MARKET DATA LOAD")
print("-" * 100)

loader = getattr(module, "load_market_data", None)

if loader is None:
    print("LOAD: FAIL — load_market_data missing")
    raise SystemExit(1)

try:
    loaded = loader(
        getattr(module, "MARKET_DATA_FILE", "market_data.bin")
    )

    print("loader return type:", type(loaded).__name__)
    print("loader return length:", len(loaded))

    candles, invalid = loaded

    print("candles type:", type(candles).__name__)
    print("candles count:", len(candles))
    print("invalid count:", invalid)

    if len(candles) == 0:
        raise RuntimeError("No valid candles loaded.")

    candle_cls = getattr(module, "Candle", None)

    print(
        "first candle type:",
        type(candles[0]).__name__
    )

    if candle_cls is not None:
        print(
            "first candle is Candle:",
            isinstance(candles[0], candle_cls)
        )

    print("LOAD DATA: PASS")

except Exception as exc:
    print("LOAD DATA: FAIL")
    print(type(exc).__name__, exc)
    traceback.print_exc()
    raise SystemExit(1)

# =====================================================================
# 4. ATR
# =====================================================================

print()
print("-" * 100)
print("4. ATR EXECUTION")
print("-" * 100)

atr_fn = getattr(module, "calculate_atr", None)

if atr_fn is None:
    atr_fn = getattr(module, "compute_atr", None)

if atr_fn is None:
    print("ATR: MISSING")
    raise SystemExit(1)

try:
    atr = atr_fn(candles)

    print("ATR: PASS")
    print("type:", type(atr).__name__)
    print("length:", len(atr))

    if len(atr) != len(candles):
        print("ATR LENGTH: FAIL")
    else:
        print("ATR LENGTH: PASS")

except Exception as exc:
    print("ATR: FAIL")
    print(type(exc).__name__, exc)
    traceback.print_exc()
    raise SystemExit(1)

# =====================================================================
# 5. STRUCTURE ENGINE
# =====================================================================

print()
print("-" * 100)
print("5. STRUCTURE ENGINE")
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

    print("engine:", engine_cls.__name__)
    print("structure type:", type(structure).__name__)
    print("structure length:", len(structure))

    if len(structure) != len(candles):
        print("STRUCTURE LENGTH: FAIL")
    else:
        print("STRUCTURE LENGTH: PASS")

    print("STRUCTURE ENGINE: PASS")

except Exception as exc:
    print("STRUCTURE ENGINE: FAIL")
    print(type(exc).__name__, exc)
    traceback.print_exc()
    raise SystemExit(1)

# =====================================================================
# 6. STRUCTURE STATE TYPES
# =====================================================================

print()
print("-" * 100)
print("6. STRUCTURE STATE VALIDATION")
print("-" * 100)

state_cls = getattr(module, "StructureState", None)

if state_cls is None:
    print("StructureState: MISSING")
    raise SystemExit(1)

bad_states = []

for i, state in enumerate(structure):
    if not isinstance(state, state_cls):
        bad_states.append(
            (i, type(state).__name__)
        )

if bad_states:
    print("STATE TYPES: FAIL")
    print("first bad states:", bad_states[:20])
else:
    print("STATE TYPES: PASS")

# =====================================================================
# 7. MARKET STATES
# =====================================================================

print()
print("-" * 100)
print("7. MARKET STATE CONSTRUCTION")
print("-" * 100)

market_state_fn = getattr(module, "build_market_states", None)

if market_state_fn is None:
    print("build_market_states: MISSING")
    raise SystemExit(1)

try:
    market_states = market_state_fn(
        candles,
        structure,
        atr,
    )

    print("MARKET STATES: PASS")
    print("type:", type(market_states).__name__)
    print("length:", len(market_states))

    if len(market_states) != len(candles):
        print("MARKET STATE LENGTH: FAIL")
    else:
        print("MARKET STATE LENGTH: PASS")

except Exception as exc:
    print("MARKET STATES: FAIL")
    print(type(exc).__name__, exc)
    traceback.print_exc()
    raise SystemExit(1)

# =====================================================================
# 8. MARKET STATE SAMPLE
# =====================================================================

print()
print("-" * 100)
print("8. MARKET STATE SAMPLE")
print("-" * 100)

if market_states:

    sample = market_states[-1]

    print("type:", type(sample).__name__)
    print("index:", getattr(sample, "index", None))
    print("timestamp:", getattr(sample, "timestamp", None))
    print("trend:", getattr(sample, "trend", None))
    print("structure_event:", getattr(sample, "structure_event", None))
    print("high_label:", getattr(sample, "high_label", None))
    print("low_label:", getattr(sample, "low_label", None))
    print("location:", getattr(sample, "location", None))
    print("regime:", getattr(sample, "regime", None))
    print("momentum_state:", getattr(sample, "momentum_state", None))
    print("sequence_state:", getattr(sample, "sequence_state", None))
    print("volatility_ratio:", getattr(sample, "volatility_ratio", None))
    print("path_vector length:", len(getattr(sample, "path_vector", ())))

# =====================================================================
# 9. EPISODE IDS
# =====================================================================

print()
print("-" * 100)
print("9. EPISODE SEGMENTATION")
print("-" * 100)

episode_fn = getattr(module, "assign_episode_ids", None)

if episode_fn is None:
    print("EPISODES: MISSING")
    episode_ids = None
else:
    try:
        episode_ids = episode_fn(market_states)

        print("EPISODES: PASS")
        print("type:", type(episode_ids).__name__)
        print("count:", len(episode_ids))

        if len(episode_ids) != len(market_states):
            print("EPISODE COVERAGE: FAIL")
        else:
            print("EPISODE COVERAGE: PASS")

        unique_episodes = sorted(set(episode_ids.values()))

        print("unique episode count:", len(unique_episodes))

        if unique_episodes:
            print(
                "episode range:",
                unique_episodes[0],
                "to",
                unique_episodes[-1],
            )

    except Exception as exc:
        print("EPISODES: FAIL")
        print(type(exc).__name__, exc)
        traceback.print_exc()
        episode_ids = None

# =====================================================================
# 10. EXPERIENCE RECORDS
# =====================================================================

print()
print("-" * 100)
print("10. HISTORICAL EXPERIENCE RECORDS")
print("-" * 100)

experience_fn = getattr(
    module,
    "build_experience_records",
    None
)

records = []

if experience_fn is None:
    print("EXPERIENCE: MISSING")

elif episode_ids is None:
    print("EXPERIENCE: BLOCKED — no episode IDs")

else:

    train_end = len(candles) // 2
    horizon = 8

    try:
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
        print("record count:", len(records))
        print("train_end:", train_end)
        print("horizon:", horizon)

        violations = []

        for r in records:

            idx = int(r.index)

            if idx < 0:
                violations.append(
                    f"negative index: {idx}"
                )

            if idx >= train_end:
                violations.append(
                    f"index {idx} >= train_end {train_end}"
                )

            if idx + horizon > train_end:
                violations.append(
                    f"index {idx} + horizon {horizon} > train_end {train_end}"
                )

            if r.horizon != horizon:
                violations.append(
                    f"record {idx} has horizon {r.horizon}"
                )

        if violations:
            print("BOUNDARY: FAIL")
            for x in violations[:20]:
                print(" ", x)
        else:
            print("BOUNDARY: PASS")

    except Exception as exc:
        print("EXPERIENCE: FAIL")
        print(type(exc).__name__, exc)
        traceback.print_exc()
        records = []

# =====================================================================
# 11. EXPERIENCE RECORD SAMPLE
# =====================================================================

print()
print("-" * 100)
print("11. EXPERIENCE RECORD SAMPLE")
print("-" * 100)

if records:

    r = records[0]

    print("type:", type(r).__name__)
    print("index:", r.index)
    print("episode_id:", r.episode_id)
    print("horizon:", r.horizon)
    print("outcome:", r.outcome)
    print("state_key:", r.state_key)
    print("path_vector length:", len(r.path_vector))

else:
    print("No experience records available.")

# =====================================================================
# 12. SIMILARITY
# =====================================================================

print()
print("-" * 100)
print("12. SIMILARITY CONTRACT")
print("-" * 100)

similarity_fn = getattr(
    module,
    "similarity_score",
    None
)

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
        print("return type:", type(score).__name__)

        if isinstance(score, dict):

            print("keys:", sorted(score.keys()))

            for key in sorted(score.keys()):
                print(
                    f"  {key}: {score[key]}"
                )

            if "total" in score:

                if 0.0 <= score["total"] <= 1.0:
                    print("TOTAL RANGE: PASS")
                else:
                    print("TOTAL RANGE: FAIL")

        else:
            print("SIMILARITY RETURN TYPE: WARNING")

    except Exception as exc:
        print("SIMILARITY: FAIL")
        print(type(exc).__name__, exc)
        traceback.print_exc()

# =====================================================================
# 13. HISTORICAL RETRIEVAL
# =====================================================================

print()
print("-" * 100)
print("13. HISTORICAL RETRIEVAL")
print("-" * 100)

retrieve_fn = getattr(
    module,
    "retrieve_historical_experience",
    None
)

if retrieve_fn is None:
    print("RETRIEVAL: MISSING")

elif not records:
    print("RETRIEVAL: BLOCKED — no records")

else:

    try:

        query_index = min(
            len(candles) - 1,
            train_end + 10
        )

        current = market_states[query_index]

        result = retrieve_fn(
            current,
            records,
            8,
            query_index,
        )

        print("RETRIEVAL: PASS")
        print("type:", type(result).__name__)
        print("repr:", repr(result)[:3000])

    except Exception as exc:
        print("RETRIEVAL: FAIL")
        print(type(exc).__name__, exc)
        traceback.print_exc()

# =====================================================================
# 14. STRUCTURE PREFIX CAUSALITY
# =====================================================================

print()
print("-" * 100)
print("14. STRUCTURE PREFIX CAUSALITY")
print("-" * 100)

try:

    boundary = len(candles) // 2

    mutated = list(candles)

    for i in range(boundary, len(mutated)):

        c = mutated[i]

        mutated[i] = type(c)(
            index=c.index,
            timestamp=c.timestamp,
            open=c.open + 1000.0,
            high=c.high + 1000.0,
            low=c.low + 1000.0,
            close=c.close + 1000.0,
            volume=c.volume,
        )

    mutated_engine = engine_cls(mutated)
    mutated_structure = mutated_engine.build()

    mismatches = []

    for i in range(boundary):

        if structure[i] != mutated_structure[i]:
            mismatches.append(i)

    if mismatches:

        print("PREFIX CAUSALITY: FAIL")
        print("mismatch count:", len(mismatches))
        print("first mismatches:", mismatches[:20])

    else:

        print("PREFIX CAUSALITY: PASS")
        print(
            f"All {boundary} prefix structure states "
            "remained identical after suffix mutation."
        )

except Exception as exc:

    print("PREFIX CAUSALITY: ERROR")
    print(type(exc).__name__, exc)
    traceback.print_exc()

# =====================================================================
# 15. SOURCE MODIFICATION CHECK
# =====================================================================

print()
print("-" * 100)
print("15. SAFETY CHECK")
print("-" * 100)

print("This diagnostic does not write to:")
print("  mlai_market_structure_v415.py")
print("  market_data.bin")
print("  any v4.1.6 file")

print()
print("=" * 100)
print("CORRECTED FULL CONTRACT FORENSIC DIAGNOSTIC COMPLETE")
print("=" * 100)
