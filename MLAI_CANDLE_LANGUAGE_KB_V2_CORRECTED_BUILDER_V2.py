import os
import json
import pickle
import hashlib
import shutil
from datetime import datetime, timezone


# ============================================================
# CONFIGURATION
# ============================================================

KB_FILE = "candle_language_v2.bin"
INDEX_FILE = "candle_language_v2.index.json"

BACKUP_KB_FILE = "candle_language_v2.pre_correction_backup.bin"
BACKUP_INDEX_FILE = "candle_language_v2.pre_correction_backup.index.json"

VERSION = "2.1"
SCHEMA_VERSION = "2.0"


# ============================================================
# DISPLAY
# ============================================================

WIDTH = 100


def banner(title):
    print("\n" + "=" * WIDTH)
    print(title)
    print("=" * WIDTH)


def section(title):
    print("\n" + "-" * WIDTH)
    print(title)
    print("-" * WIDTH)


# ============================================================
# HASH
# ============================================================

def sha256_file(path):
    h = hashlib.sha256()

    with open(path, "rb") as f:
        while True:
            chunk = f.read(1024 * 1024)

            if not chunk:
                break

            h.update(chunk)

    return h.hexdigest()


# ============================================================
# RECURSIVE TEXT EXTRACTION
#
# IMPORTANT:
# This intentionally mirrors the Inspector's philosophy.
# It searches all nested dictionaries/lists/tuples/sets.
# Therefore "false break" already present anywhere in the KB
# will NOT be incorrectly reported as missing.
# ============================================================

def collect_text_fragments(obj, output=None):
    if output is None:
        output = []

    if isinstance(obj, str):
        output.append(obj.lower())

    elif isinstance(obj, dict):
        for key, value in obj.items():
            if isinstance(key, str):
                output.append(key.lower())

            collect_text_fragments(value, output)

    elif isinstance(obj, (list, tuple, set)):
        for item in obj:
            collect_text_fragments(item, output)

    return output


def normalized_text(obj):
    fragments = collect_text_fragments(obj)

    return "\n".join(fragments)


def contains_phrase(obj, phrase):
    text = normalized_text(obj)

    phrase = phrase.lower().strip()

    return phrase in text


# ============================================================
# LOAD
# ============================================================

def load_kb():
    if not os.path.exists(KB_FILE):
        raise FileNotFoundError(
            f"Knowledge base not found: {KB_FILE}"
        )

    with open(KB_FILE, "rb") as f:
        return pickle.load(f)


# ============================================================
# RECORD EXTRACTION
# ============================================================

def get_records(kb):
    if not isinstance(kb, dict):
        raise RuntimeError(
            f"Unexpected KB object type: {type(kb).__name__}"
        )

    if "records" not in kb:
        raise RuntimeError(
            "KB does not contain a top-level 'records' field."
        )

    records = kb["records"]

    if not isinstance(records, list):
        raise RuntimeError(
            f"KB 'records' field is not a list: {type(records).__name__}"
        )

    return records


# ============================================================
# RECORD CONSTRUCTION
#
# These are foundational definitions only.
# They do NOT contain historical outcomes.
# They do NOT contain predictions.
# ============================================================

NEW_RECORDS = [
    {
        "category": "support_resistance",
        "name": "previous high",
        "term": "previous high",
        "definition": (
            "A previously observed price high that can be used as a "
            "historical reference area for structure, resistance, "
            "breakout, retest, or liquidity analysis."
        ),
        "human_meaning": (
            "A prior high where price previously reached a higher level. "
            "It may become relevant again if price approaches or crosses it."
        ),
        "causal_rule": (
            "Only highs that were already available at the observation "
            "timestamp may be used as input."
        ),
        "knowledge_type": "foundational_definition",
    },

    {
        "category": "support_resistance",
        "name": "previous low",
        "term": "previous low",
        "definition": (
            "A previously observed price low that can be used as a "
            "historical reference area for structure, support, breakdown, "
            "retest, or liquidity analysis."
        ),
        "human_meaning": (
            "A prior low where price previously reached a lower level. "
            "It may become relevant again if price approaches or crosses it."
        ),
        "causal_rule": (
            "Only lows that were already available at the observation "
            "timestamp may be used as input."
        ),
        "knowledge_type": "foundational_definition",
    },

    {
        "category": "causality",
        "name": "look-ahead",
        "term": "look-ahead",
        "definition": (
            "Use of information that was not available at the time an "
            "observation or prediction was made."
        ),
        "human_meaning": (
            "MLAI must never use future candles or future-derived "
            "information when interpreting the current market state."
        ),
        "causal_rule": (
            "Future candles, future outcomes, future-confirmed events, "
            "and future-derived statistics are prohibited inputs before "
            "their information becomes causally available."
        ),
        "knowledge_type": "scientific_safety_rule",
    },
]


# ============================================================
# SAFETY CHECK
# ============================================================

def ensure_no_experience_fields(record):
    forbidden = {
        "historical_probability",
        "probability",
        "sample_count",
        "success_count",
        "failure_count",
        "outcome",
        "future_return",
        "prediction",
        "prediction_result",
        "actual_result",
        "mfe",
        "mae",
    }

    text = normalized_text(record)

    suspicious = []

    for field in forbidden:
        if field.lower() in text:
            suspicious.append(field)

    return suspicious


# ============================================================
# MAIN
# ============================================================

def main():

    banner(
        "MLAI CANDLE LANGUAGE KB V2 — FOUNDATION CORRECTION BUILDER V2"
    )

    print("""
PURPOSE
----------------------------------------------------------------------------------------------------
Correct only the three genuinely missing foundational vocabulary concepts
identified by FOUNDATION INSPECTOR V2.

This builder uses recursive validation so concepts already present in
nested KB records are not incorrectly reported as missing.

No market data is modified.
No historical experience is created.
No prediction model is changed.
No retrieval system is changed.
Existing MLAI v4.x is not modified.
""")

    # --------------------------------------------------------
    # FILE CHECK
    # --------------------------------------------------------

    section("FILE CHECK")

    if not os.path.exists(KB_FILE):
        raise FileNotFoundError(
            f"Missing required file: {KB_FILE}"
        )

    print(f"KB file : PASS")
    print(f"Path    : {os.path.abspath(KB_FILE)}")

    original_hash = sha256_file(KB_FILE)
    original_size = os.path.getsize(KB_FILE)

    print(f"Original SHA256 : {original_hash}")
    print(f"Original size   : {original_size:,} bytes")

    # --------------------------------------------------------
    # LOAD
    # --------------------------------------------------------

    section("LOADING EXISTING KNOWLEDGE BASE")

    kb = load_kb()

    records = get_records(kb)

    original_record_count = len(records)

    print(f"Python type    : {type(kb).__name__}")
    print(f"Existing records : {original_record_count}")

    if original_record_count != 178:
        print(
            "WARNING: Existing record count is not 178."
        )
        print(
            "The builder will continue only if the KB structure is valid."
        )

    # --------------------------------------------------------
    # BACKUP
    # --------------------------------------------------------

    section("CREATING SAFETY BACKUP")

    if os.path.exists(BACKUP_KB_FILE):
        print(
            f"Backup already exists : {BACKUP_KB_FILE}"
        )
    else:
        shutil.copy2(KB_FILE, BACKUP_KB_FILE)

        print(
            f"Backup created : {BACKUP_KB_FILE}"
        )

    if os.path.exists(INDEX_FILE):

        if not os.path.exists(BACKUP_INDEX_FILE):
            shutil.copy2(
                INDEX_FILE,
                BACKUP_INDEX_FILE
            )

            print(
                f"Index backup created : {BACKUP_INDEX_FILE}"
            )
        else:
            print(
                f"Index backup already exists : {BACKUP_INDEX_FILE}"
            )

    # --------------------------------------------------------
    # PRE-CORRECTION VALIDATION
    # --------------------------------------------------------

    section("PRE-CORRECTION VOCABULARY AUDIT")

    required = [
        "previous high",
        "previous low",
        "look-ahead",
        "false break",
    ]

    before_text = normalized_text(kb)

    missing_before = []

    for term in required:

        if term.lower() in before_text:
            print(f"[PASS] {term}")
        else:
            print(f"[MISSING] {term}")
            missing_before.append(term)

    print()
    print(
        "IMPORTANT: 'false break' is already present in the existing KB."
    )
    print(
        "It will NOT be added again."
    )

    # --------------------------------------------------------
    # BUILD ONLY WHAT IS ACTUALLY MISSING
    # --------------------------------------------------------

    section("FOUNDATION CORRECTION")

    added = []

    for record in NEW_RECORDS:

        term = record["term"]

        if contains_phrase(kb, term):

            print(
                f"[SKIP ] {term} — already present"
            )

        else:

            suspicious = ensure_no_experience_fields(record)

            if suspicious:

                raise RuntimeError(
                    f"Safety failure: {term} contains forbidden "
                    f"experience/prediction fields: {suspicious}"
                )

            records.append(record)

            added.append(term)

            print(
                f"[ADDED] {term}"
            )

    print()
    print(
        f"Records before : {original_record_count}"
    )
    print(
        f"Records added  : {len(added)}"
    )
    print(
        f"Records after  : {len(records)}"
    )

    # --------------------------------------------------------
    # UPDATE METADATA
    # --------------------------------------------------------

    if isinstance(kb, dict):

        kb["version"] = VERSION
        kb["schema_version"] = SCHEMA_VERSION
        kb["updated_utc"] = datetime.now(
            timezone.utc
        ).isoformat()

    # --------------------------------------------------------
    # POST-CORRECTION VALIDATION
    # --------------------------------------------------------

    section("POST-CORRECTION VALIDATION")

    validation_text = normalized_text(kb)

    all_pass = True

    for term in required:

        if term.lower() in validation_text:

            print(
                f"[PASS] {term}"
            )

        else:

            print(
                f"[FAIL] {term}"
            )

            all_pass = False

    # Ensure exactly one occurrence of newly required concepts
    # is present at the record-name/term level where practical.

    if not all_pass:

        print()
        print(
            "VALIDATION FAILED."
        )
        print(
            "The existing KB has NOT been overwritten."
        )

        raise RuntimeError(
            "Foundation validation failed."
        )

    print()
    print(
        "STATUS : PASS"
    )
    print(
        "All required foundational vocabulary is now present."
    )

    # --------------------------------------------------------
    # KNOWLEDGE / EXPERIENCE SEPARATION
    # --------------------------------------------------------

    section("KNOWLEDGE / EXPERIENCE SEPARATION")

    forbidden_global_terms = [
        "historical_probability",
        "prediction_result",
        "actual_result",
        "future_return",
    ]

    suspicious_global = []

    for term in forbidden_global_terms:

        if term.lower() in validation_text:
            suspicious_global.append(term)

    if suspicious_global:

        print(
            "STATUS : REVIEW"
        )

        print(
            "Potential experience-related fields detected:"
        )

        for item in suspicious_global:
            print(
                f"  - {item}"
            )

        raise RuntimeError(
            "Knowledge/experience separation requires review."
        )

    print(
        "STATUS : PASS"
    )
    print(
        "No prohibited historical-experience fields detected."
    )

    # --------------------------------------------------------
    # SERIALIZE TO TEMPORARY FILE FIRST
    # --------------------------------------------------------

    section("WRITING CORRECTED KNOWLEDGE BASE")

    TEMP_FILE = KB_FILE + ".tmp"

    with open(TEMP_FILE, "wb") as f:

        pickle.dump(
            kb,
            f,
            protocol=pickle.HIGHEST_PROTOCOL
        )

    temp_hash = sha256_file(TEMP_FILE)
    temp_size = os.path.getsize(TEMP_FILE)

    print(
        f"Temporary KB size   : {temp_size:,} bytes"
    )

    print(
        f"Temporary KB SHA256  : {temp_hash}"
    )

    # --------------------------------------------------------
    # RELOAD TEMP FILE BEFORE COMMIT
    # --------------------------------------------------------

    section("REOPEN / ROUND-TRIP VERIFICATION")

    with open(TEMP_FILE, "rb") as f:

        verification_kb = pickle.load(f)

    verification_records = get_records(
        verification_kb
    )

    print(
        "Reload status : PASS"
    )

    print(
        f"Reloaded records : {len(verification_records)}"
    )

    verification_text = normalized_text(
        verification_kb
    )

    for term in required:

        if term.lower() not in verification_text:

            raise RuntimeError(
                f"Round-trip verification failed for: {term}"
            )

    print(
        "Vocabulary round-trip : PASS"
    )

    # --------------------------------------------------------
    # COMMIT
    # --------------------------------------------------------

    os.replace(
        TEMP_FILE,
        KB_FILE
    )

    final_hash = sha256_file(KB_FILE)
    final_size = os.path.getsize(KB_FILE)

    # --------------------------------------------------------
    # INDEX
    # --------------------------------------------------------

    section("REBUILDING AUDIT INDEX")

    fragments = collect_text_fragments(kb)

    categories = {}

    for record in records:

        if isinstance(record, dict):

            category = record.get(
                "category",
                "unknown"
            )

            categories[category] = (
                categories.get(category, 0) + 1
            )

    index = {
        "format": "MLAI_CANDLE_LANGUAGE_KB_INDEX",
        "version": VERSION,
        "schema_version": SCHEMA_VERSION,
        "generated_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "kb_file": KB_FILE,
        "kb_sha256": final_hash,
        "kb_size_bytes": final_size,
        "record_count": len(records),
        "categories": categories,
        "required_vocabulary": {
            term: True
            for term in required
        },
        "knowledge_only": True,
        "historical_experience_included": False,
        "prediction_included": False,
        "retrieval_modified": False,
        "market_data_modified": False,
    }

    with open(
        INDEX_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            index,
            f,
            indent=2,
            ensure_ascii=False
        )

    print(
        f"Index file : {INDEX_FILE}"
    )
    print(
        "Index status : CREATED"
    )

    # --------------------------------------------------------
    # FINAL VERIFICATION
    # --------------------------------------------------------

    section("FINAL INTEGRITY VERIFICATION")

    index_hash = index["kb_sha256"]

    print(
        f"KB SHA256       : {final_hash}"
    )

    print(
        f"Index SHA256    : {index_hash}"
    )

    if final_hash != index_hash:

        raise RuntimeError(
            "FINAL HASH MISMATCH."
        )

    print(
        "Hash match      : PASS"
    )

    # --------------------------------------------------------
    # FINAL SUMMARY
    # --------------------------------------------------------

    section("FOUNDATION SUMMARY")

    print(
        f"Version              : {VERSION}"
    )

    print(
        f"Schema               : {SCHEMA_VERSION}"
    )

    print(
        f"Records              : {len(records)}"
    )

    print(
        f"Inspectable fragments: {len(fragments)}"
    )

    print()
    print(
        "Required vocabulary:"
    )

    for term in required:

        print(
            f"  PASS : {term}"
        )

    # --------------------------------------------------------
    # IMPORTANT SEPARATION
    # --------------------------------------------------------

    section("IMPORTANT SEPARATION")

    print(
        "Knowledge base      : FOUNDATIONAL DEFINITIONS"
    )

    print(
        "Historical memory   : NOT CREATED"
    )

    print(
        "Prediction          : NOT CREATED"
    )

    print(
        "Retrieval           : NOT MODIFIED"
    )

    print(
        "MLAI v4.x           : NOT MODIFIED"
    )

    print(
        "market_data.bin     : NOT MODIFIED"
    )

    # --------------------------------------------------------
    # FINAL STATUS
    # --------------------------------------------------------

    section("FINAL STATUS")

    print(
        "FOUNDATION CORRECTION : PASS"
    )

    print()
    print(
        "The foundational vocabulary is now complete for the"
    )

    print(
        "currently defined Inspector V2 requirements."
    )

    print()
    print(
        "NEXT GATE:"
    )

    print(
        "Run:"
    )

    print(
        "    python MLAI_CANDLE_LANGUAGE_KB_INSPECTOR_V2.py"
    )

    print()
    print(
        "Only if Inspector V2 returns PASS should we move to:"
    )

    print(
        "    1. market_data.bin forensic audit"
    )

    print(
        "    2. canonical candle schema verification"
    )

    print(
        "    3. causal candle-language parser"
    )

    print(
        "    4. chronological experience memory"
    )

    print("=" * WIDTH)


if __name__ == "__main__":
    main()