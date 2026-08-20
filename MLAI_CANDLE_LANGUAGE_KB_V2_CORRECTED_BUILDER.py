import hashlib
import json
import pickle
from datetime import datetime, timezone
from pathlib import Path

KB_FILE = Path("candle_language_v2.bin")
INDEX_FILE = Path("candle_language_v2.index.json")


def sha256_file(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def make_record(category, name, meaning, topic=None):
    return {
        "category": category,
        "name": name,
        "meaning": meaning,
        "topic": topic or category,
    }


print("=" * 100)
print("MLAI CANDLE LANGUAGE KB V2 — FOUNDATION CORRECTION BUILDER")
print("=" * 100)

print()
print("PURPOSE")
print("-" * 100)
print("Add the three explicit foundational vocabulary items identified by")
print("FOUNDATION INSPECTOR V2.")
print()
print("No market data is modified.")
print("No historical experience is created.")
print("No prediction model is changed.")
print("No retrieval system is changed.")
print("Existing MLAI v4.x is not modified.")

# ---------------------------------------------------------------------
# LOAD EXISTING KB
# ---------------------------------------------------------------------

if not KB_FILE.exists():
    raise FileNotFoundError(
        f"Required KB not found: {KB_FILE}"
    )

print()
print("=" * 100)
print("LOADING EXISTING KNOWLEDGE BASE")
print("=" * 100)

with KB_FILE.open("rb") as f:
    kb = pickle.load(f)

if not isinstance(kb, dict):
    raise TypeError("Knowledge base is not a dictionary.")

records = kb.get("records")

if not isinstance(records, list):
    raise TypeError("Knowledge base records are not a list.")

original_count = len(records)

print(f"Existing records : {original_count}")

# ---------------------------------------------------------------------
# PREVENT DUPLICATE INSERTION
# ---------------------------------------------------------------------

existing_keys = set()

for r in records:
    if isinstance(r, dict):
        existing_keys.add(
            (
                str(r.get("category", "")).strip().lower(),
                str(r.get("name", "")).strip().lower(),
            )
        )

# ---------------------------------------------------------------------
# THREE REQUIRED FOUNDATION ADDITIONS
# ---------------------------------------------------------------------

required_additions = [
    make_record(
        "support_resistance",
        "previous high",
        (
            "A previously observed high price or high area that may act as "
            "a reference point for later reactions, resistance, breakout, "
            "retest or role reversal. It is an observable price reference, "
            "not proof of hidden orders."
        ),
        "support_resistance",
    ),
    make_record(
        "support_resistance",
        "previous low",
        (
            "A previously observed low price or low area that may act as "
            "a reference point for later reactions, support, breakdown, "
            "retest or role reversal. It is an observable price reference, "
            "not proof of hidden orders."
        ),
        "support_resistance",
    ),
    make_record(
        "causality",
        "look-ahead",
        (
            "Look-ahead bias occurs when information that was not available "
            "at the prediction timestamp is used as an input. MLAI must "
            "exclude future candles, future outcomes and future-confirmed "
            "information from the state being evaluated."
        ),
        "causality",
    ),
]

print()
print("=" * 100)
print("FOUNDATION CORRECTION")
print("=" * 100)

added = 0

for record in required_additions:
    key = (
        record["category"].lower(),
        record["name"].lower(),
    )

    if key in existing_keys:
        print(f"[EXISTS] {record['name']}")
    else:
        records.append(record)
        existing_keys.add(key)
        added += 1
        print(f"[ADDED ] {record['name']}")

print()
print(f"Records before : {original_count}")
print(f"Records added  : {added}")
print(f"Records after  : {len(records)}")

# ---------------------------------------------------------------------
# UPDATE METADATA
# ---------------------------------------------------------------------

kb["records"] = records
kb["version"] = "2.0"
kb["schema_version"] = "2.0"
kb["format"] = kb.get(
    "format",
    "MLAI Candle Language Knowledge Base"
)
kb["created_utc"] = utc_now()

# ---------------------------------------------------------------------
# VALIDATE REQUIRED ITEMS BEFORE WRITING
# ---------------------------------------------------------------------

required_names = {
    "body",
    "range",
    "upper_wick",
    "lower_wick",
    "bullish",
    "bearish",
    "neutral",
    "doji",
    "hammer",
    "inverted hammer",
    "shooting star",
    "engulfing",
    "inside bar",
    "outside bar",
    "rejection",
    "compression",
    "expansion",
    "momentum",
    "pullback",
    "retracement",
    "higher high",
    "higher low",
    "lower high",
    "lower low",
    "bos",
    "choch",
    "trend",
    "range",
    "breakout",
    "breakdown",
    "support",
    "resistance",
    "reaction area",
    "retest",
    "role reversal",
    "previous high",
    "previous low",
    "atr",
    "volatility",
    "acceleration",
    "deceleration",
    "exhaustion",
    "follow-through",
    "context",
    "location",
    "regime",
    "timeframe",
    "session",
    "equal highs",
    "equal lows",
    "sweep",
    "false break",
    "causal",
    "future",
    "completed candle",
    "confirmation",
    "look-ahead",
    "uncertainty",
    "historical evidence",
    "not certainty",
}

all_text = " ".join(
    str(record)
    for record in records
).lower()

missing = [
    item for item in sorted(required_names)
    if item.lower() not in all_text
]

print()
print("=" * 100)
print("VALIDATION")
print("=" * 100)

if missing:
    print("STATUS : FAIL")
    print()
    print("Missing required vocabulary:")
    for item in missing:
        print(f"  - {item}")
    raise RuntimeError("Foundation validation failed.")

print("STATUS : PASS")
print("Required foundational vocabulary is present.")
print("Previous high is present.")
print("Previous low is present.")
print("Look-ahead causality terminology is present.")

# ---------------------------------------------------------------------
# WRITE NEW KB
# ---------------------------------------------------------------------

print()
print("=" * 100)
print("WRITING CORRECTED KNOWLEDGE BASE")
print("=" * 100)

with KB_FILE.open("wb") as f:
    pickle.dump(
        kb,
        f,
        protocol=pickle.HIGHEST_PROTOCOL
    )

print(f"KB file : {KB_FILE}")
print("Status  : UPDATED")

# ---------------------------------------------------------------------
# HASH
# ---------------------------------------------------------------------

kb_hash = sha256_file(KB_FILE)

print()
print("=" * 100)
print("HASHING")
print("=" * 100)
print(f"KB SHA256:")
print(kb_hash)

# ---------------------------------------------------------------------
# REBUILD INDEX
# ---------------------------------------------------------------------

print()
print("=" * 100)
print("CREATING AUDIT INDEX")
print("=" * 100)

categories = {}

for record in records:
    category = str(
        record.get("category", "unknown")
    )

    categories[category] = categories.get(category, 0) + 1

index = {
    "knowledge_base": "MLAI Candle Language KB V2",
    "created_utc": kb["created_utc"],
    "version": kb["version"],
    "schema_version": kb["schema_version"],
    "record_count": len(records),
    "source_count": len(kb.get("sources", [])),
    "indexed_sha256": kb_hash,
    "categories": dict(sorted(categories.items())),
}

with INDEX_FILE.open(
    "w",
    encoding="utf-8"
) as f:
    json.dump(
        index,
        f,
        indent=2,
        ensure_ascii=False,
    )

print(f"Index file : {INDEX_FILE}")
print("Status     : CREATED")

# ---------------------------------------------------------------------
# SUMMARY
# ---------------------------------------------------------------------

print()
print("=" * 100)
print("FOUNDATION SUMMARY")
print("=" * 100)

print(f"Version              : {kb['version']}")
print(f"Schema               : {kb['schema_version']}")
print(f"Records              : {len(records)}")
print(f"Categories           : {len(categories)}")

print()
print("EXPLICIT CORRECTIONS")
print("-" * 100)
print("  + previous high")
print("  + previous low")
print("  + look-ahead")

print()
print("=" * 100)
print("IMPORTANT SEPARATION")
print("=" * 100)

print("Knowledge base      : FOUNDATIONAL DEFINITIONS")
print("Historical memory   : NOT CREATED")
print("Prediction          : NOT CREATED")
print("Retrieval           : NOT MODIFIED")
print("MLAI v4.x           : NOT MODIFIED")
print("market_data.bin     : NOT MODIFIED")

print()
print("=" * 100)
print("FINAL STATUS")
print("=" * 100)

print("FOUNDATION CORRECTION BUILD : PASS")

print()
print("NEXT STEP:")
print("Run:")
print("    python MLAI_CANDLE_LANGUAGE_KB_INSPECTOR_V2.py")
print()
print("Expected:")
print("    Vocabulary coverage : 66/66")
print("    FOUNDATION INSPECTOR V2 : PASS")
print()
print("=" * 100)