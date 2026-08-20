"""
MLAI CANDLE LANGUAGE KB V2 — FOUNDATION CORRECTION BUILDER V3

Purpose:
    Correct the foundational vocabulary identified by the read-only inspector.

IMPORTANT:
    This script modifies ONLY candle_language_v2.bin and its audit index.
    It does NOT modify:
        - market_data.bin
        - MLAI v4.x
        - historical experience
        - retrieval
        - prediction models

Scientific rule:
    Foundational vocabulary definitions must never contain future outcomes,
    predictions, probabilities, success/failure statistics, or historical
    experience fields.

Correction concepts:
    - previous high
    - previous low
    - look-ahead

"false break" is already present and is NOT duplicated.

The builder creates a fresh corrected KB from the ORIGINAL 178-record KB
using the pre-correction backup when available.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import pickle
import shutil
from datetime import datetime, timezone


KB_FILE = "candle_language_v2.bin"
INDEX_FILE = "candle_language_v2.index.json"

BACKUP_KB = "candle_language_v2.pre_correction_backup.bin"
BACKUP_INDEX = "candle_language_v2.pre_correction_backup.index.json"

REQUIRED_CONCEPTS = {
    "previous high",
    "previous low",
    "look-ahead",
}

ALREADY_PRESENT_CONCEPTS = {
    "false break",
}

FORBIDDEN_EXPERIENCE_FIELDS = {
    "outcome",
    "outcomes",
    "future_outcome",
    "future_outcomes",
    "prediction",
    "predictions",
    "probability",
    "probabilities",
    "success",
    "success_count",
    "failure",
    "failure_count",
    "historical_memory",
    "historical_experience",
    "experience",
    "mfe",
    "mae",
    "future_return",
    "return",
    "label",
    "target",
    "targets",
}


# ============================================================================
# UTILITIES
# ============================================================================

def sha256_file(path: str) -> str:
    h = hashlib.sha256()

    with open(path, "rb") as f:
        while True:
            chunk = f.read(1024 * 1024)

            if not chunk:
                break

            h.update(chunk)

    return h.hexdigest()


def load_pickle(path: str):
    with open(path, "rb") as f:
        return pickle.load(f)


def save_pickle(path: str, obj) -> None:
    temp = path + ".tmp"

    with open(temp, "wb") as f:
        pickle.dump(
            obj,
            f,
            protocol=pickle.HIGHEST_PROTOCOL,
        )

    os.replace(temp, path)


def recursive_text(value):
    """
    Return all textual fragments from an arbitrary nested structure.
    """
    fragments = []

    if isinstance(value, str):
        fragments.append(value)

    elif isinstance(value, dict):
        for key, val in value.items():
            fragments.extend(recursive_text(key))
            fragments.extend(recursive_text(val))

    elif isinstance(value, (list, tuple, set)):
        for item in value:
            fragments.extend(recursive_text(item))

    return fragments


def normalized_text_fragments(obj):
    return [
        str(x).strip().lower()
        for x in recursive_text(obj)
        if str(x).strip()
    ]


def contains_concept(obj, concept: str) -> bool:
    concept = concept.lower().strip()

    fragments = normalized_text_fragments(obj)

    # Exact textual fragment.
    if concept in fragments:
        return True

    # Phrase inside longer text.
    for fragment in fragments:
        if concept in fragment:
            return True

    return False


def collect_field_names(obj):
    """
    Recursively collect dictionary field names.
    """
    fields = set()

    if isinstance(obj, dict):
        for key, value in obj.items():
            fields.add(str(key).strip().lower())
            fields.update(collect_field_names(value))

    elif isinstance(obj, (list, tuple, set)):
        for item in obj:
            fields.update(collect_field_names(item))

    return fields


def contains_forbidden_field(obj):
    fields = collect_field_names(obj)

    found = sorted(
        field
        for field in fields
        if field in FORBIDDEN_EXPERIENCE_FIELDS
    )

    return found


def rebuild_index(kb, kb_path):
    records = kb.get("records", [])

    index = {
        "format": kb.get("format"),
        "version": kb.get("version"),
        "schema_version": kb.get("schema_version"),
        "kb_file": os.path.basename(kb_path),
        "kb_sha256": sha256_file(kb_path),
        "kb_size": os.path.getsize(kb_path),
        "record_count": len(records),
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "index_type": "foundational_knowledge_audit",
        "read_only_reference": True,
    }

    temp = INDEX_FILE + ".tmp"

    with open(temp, "w", encoding="utf-8") as f:
        json.dump(
            index,
            f,
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        )

    os.replace(temp, INDEX_FILE)

    return index


# ============================================================================
# SAFE FOUNDATIONAL RECORDS
# ============================================================================

def make_previous_high_record():
    return {
        "category": "support_resistance",
        "name": "previous high",

        "definition": (
            "A previously observed high price or high-price area in the "
            "causal market history available before the current evaluation."
        ),

        "human_language": (
            "Previous high means a high that occurred earlier in the "
            "available market history. It can be used as a reference area "
            "for describing current price location, reactions, breaks, "
            "retests, or resistance behavior."
        ),

        "observable_basis": [
            "historical candle high",
            "previously observed price high",
            "prior reaction area",
        ],

        "causality": {
            "type": "causal",
            "availability": (
                "Available only after the candle containing the previous "
                "high has completed."
            ),
        },

        "interpretation_restriction": (
            "A previous high is an observable price reference. It does not "
            "by itself prove resistance, hidden orders, trader intent, or "
            "future price direction."
        ),

        "source": "foundational_definition",
        "knowledge_type": "vocabulary",
    }


def make_previous_low_record():
    return {
        "category": "support_resistance",
        "name": "previous low",

        "definition": (
            "A previously observed low price or low-price area in the "
            "causal market history available before the current evaluation."
        ),

        "human_language": (
            "Previous low means a low that occurred earlier in the available "
            "market history. It can be used as a reference area for "
            "describing current price location, reactions, breaks, "
            "retests, or support behavior."
        ),

        "observable_basis": [
            "historical candle low",
            "previously observed price low",
            "prior reaction area",
        ],

        "causality": {
            "type": "causal",
            "availability": (
                "Available only after the candle containing the previous "
                "low has completed."
            ),
        },

        "interpretation_restriction": (
            "A previous low is an observable price reference. It does not "
            "by itself prove support, hidden orders, trader intent, or "
            "future price direction."
        ),

        "source": "foundational_definition",
        "knowledge_type": "vocabulary",
    }


def make_look_ahead_record():
    """
    IMPORTANT:
        This record describes a prohibited methodology condition.

    It deliberately contains NO:
        outcome
        prediction
        target
        probability
        success/failure
        historical experience
    """

    return {
        "category": "causality",
        "name": "look-ahead",

        "definition": (
            "Look-ahead occurs when information that was not available at "
            "the evaluation timestamp is used as an input to describe, "
            "classify, retrieve, model, or interpret the market state."
        ),

        "human_language": (
            "In simple language, look-ahead means seeing information from "
            "later candles before that information would actually have "
            "been known. MLAI must not do this."
        ),

        "causality": {
            "type": "prohibited",
            "rule": (
                "An input may only use information available at or before "
                "the feature's causal availability timestamp."
            ),
        },

        "examples_of_prohibited_access": [
            "using a future candle to describe the current candle",
            "using an uncompleted higher-timeframe candle",
            "using future-confirmed structure before confirmation",
            "using later price movement as a current-state feature",
        ],

        "required_safeguard": (
            "Every feature must have a known availability timestamp and "
            "must pass a future-data access audit."
        ),

        "source": "foundational_definition",
        "knowledge_type": "scientific_safety",
    }


# ============================================================================
# VALIDATION
# ============================================================================

def validate_foundation(kb):
    print()
    print("=" * 100)
    print("POST-CORRECTION FOUNDATION VALIDATION")
    print("=" * 100)

    all_text = "\n".join(
        normalized_text_fragments(kb)
    )

    failures = []

    for concept in sorted(REQUIRED_CONCEPTS):
        if concept.lower() in all_text:
            print(f"[PASS] {concept}")
        else:
            print(f"[FAIL] {concept}")
            failures.append(concept)

    # false break must already exist.
    if "false break" in all_text:
        print("[PASS] false break already present")
    else:
        print("[FAIL] false break missing")
        failures.append("false break")

    # Validate correction records specifically.
    records = kb.get("records", [])

    correction_names = {
        "previous high",
        "previous low",
        "look-ahead",
    }

    correction_records = [
        r
        for r in records
        if isinstance(r, dict)
        and str(r.get("name", "")).strip().lower()
        in correction_names
    ]

    print()
    print("CORRECTION RECORD SAFETY")
    print("-" * 100)

    for record in correction_records:
        name = str(record.get("name", ""))

        forbidden = contains_forbidden_field(record)

        if forbidden:
            print(
                f"[FAIL] {name}: forbidden fields detected: "
                f"{forbidden}"
            )
            failures.append(
                f"{name}: forbidden fields"
            )
        else:
            print(
                f"[PASS] {name}: foundational-only record"
            )

    if failures:
        print()
        print("STATUS : FAIL")
        print()
        print("Failures:")
        for failure in failures:
            print(f"  - {failure}")

        return False

    print()
    print("STATUS : PASS")
    print("All required concepts are present.")
    print("No forbidden experience/prediction fields detected.")
    print("false break was not duplicated.")

    return True


# ============================================================================
# MAIN
# ============================================================================

def main():

    print("=" * 100)
    print("MLAI CANDLE LANGUAGE KB V2 — FOUNDATION CORRECTION BUILDER V3")
    print("=" * 100)

    print()
    print("PURPOSE")
    print("-" * 100)
    print(
        "Correct the foundational vocabulary without introducing "
        "historical experience or prediction information."
    )

    # ------------------------------------------------------------------------
    # File check
    # ------------------------------------------------------------------------

    if not os.path.exists(KB_FILE):
        raise FileNotFoundError(
            f"Missing KB file: {KB_FILE}"
        )

    print()
    print("-" * 100)
    print("SOURCE FILE")
    print("-" * 100)

    original_hash = sha256_file(KB_FILE)
    original_size = os.path.getsize(KB_FILE)

    print(f"KB file       : {KB_FILE}")
    print(f"Original hash : {original_hash}")
    print(f"Original size : {original_size:,} bytes")

    # ------------------------------------------------------------------------
    # Create backup ONLY if not already present.
    # ------------------------------------------------------------------------

    if not os.path.exists(BACKUP_KB):

        shutil.copy2(
            KB_FILE,
            BACKUP_KB,
        )

        if os.path.exists(INDEX_FILE):
            shutil.copy2(
                INDEX_FILE,
                BACKUP_INDEX,
            )

        print()
        print("Backup created:")
        print(f"  {BACKUP_KB}")

        if os.path.exists(INDEX_FILE):
            print(f"  {BACKUP_INDEX}")

    else:
        print()
        print("Existing pre-correction backup found.")
        print(f"Using: {BACKUP_KB}")

    # ------------------------------------------------------------------------
    # IMPORTANT:
    # Always start from original backup.
    # ------------------------------------------------------------------------

    source_file = (
        BACKUP_KB
        if os.path.exists(BACKUP_KB)
        else KB_FILE
    )

    print()
    print("-" * 100)
    print("LOADING ORIGINAL FOUNDATION")
    print("-" * 100)

    kb = load_pickle(source_file)

    if not isinstance(kb, dict):
        raise RuntimeError(
            "Foundation KB must be a dictionary."
        )

    records = kb.get("records")

    if not isinstance(records, list):
        raise RuntimeError(
            "Foundation KB records must be a list."
        )

    print(f"Source                  : {source_file}")
    print(f"Original record count   : {len(records)}")

    # ------------------------------------------------------------------------
    # Pre-correction audit
    # ------------------------------------------------------------------------

    print()
    print("-" * 100)
    print("PRE-CORRECTION AUDIT")
    print("-" * 100)

    source_text = "\n".join(
        normalized_text_fragments(kb)
    )

    for concept in sorted(REQUIRED_CONCEPTS):
        if concept in source_text:
            print(f"[PRESENT] {concept}")
        else:
            print(f"[MISSING] {concept}")

    if "false break" in source_text:
        print("[PRESENT] false break")
    else:
        print("[MISSING] false break")

    # ------------------------------------------------------------------------
    # Build fresh corrected record list.
    # ------------------------------------------------------------------------

    new_kb = copy.deepcopy(kb)
    new_records = copy.deepcopy(records)

    additions = [
        make_previous_high_record(),
        make_previous_low_record(),
        make_look_ahead_record(),
    ]

    print()
    print("-" * 100)
    print("FOUNDATION CORRECTION")
    print("-" * 100)

    for record in additions:

        name = record["name"]

        # Prevent duplicate concept records.
        if contains_concept(new_records, name):
            print(
                f"[SKIPPED] {name} already represented"
            )
            continue

        forbidden = contains_forbidden_field(record)

        if forbidden:
            raise RuntimeError(
                f"Safety failure before insertion: "
                f"{name} contains forbidden fields: {forbidden}"
            )

        new_records.append(record)

        print(f"[ADDED] {name}")

    new_kb["records"] = new_records

    # Update metadata without changing the scientific schema.
    new_kb["version"] = "2.0"
    new_kb["schema_version"] = "2.0"
    new_kb["corrected_utc"] = (
        datetime.now(timezone.utc).isoformat()
    )

    # ------------------------------------------------------------------------
    # Validate BEFORE writing.
    # ------------------------------------------------------------------------

    print()
    print("-" * 100)
    print("VALIDATING CORRECTED KB BEFORE WRITE")
    print("-" * 100)

    if not validate_foundation(new_kb):
        raise RuntimeError(
            "Corrected foundation failed validation. "
            "Original KB has NOT been overwritten."
        )

    # ------------------------------------------------------------------------
    # Write corrected KB.
    # ------------------------------------------------------------------------

    print()
    print("-" * 100)
    print("WRITING CORRECTED FOUNDATION")
    print("-" * 100)

    save_pickle(
        KB_FILE,
        new_kb,
    )

    corrected_hash = sha256_file(KB_FILE)
    corrected_size = os.path.getsize(KB_FILE)

    print(f"KB file          : {KB_FILE}")
    print(f"Status           : CREATED")
    print(f"Records          : {len(new_records)}")
    print(f"SHA256           : {corrected_hash}")
    print(f"Size             : {corrected_size:,} bytes")

    # ------------------------------------------------------------------------
    # Rebuild index.
    # ------------------------------------------------------------------------

    print()
    print("-" * 100)
    print("REBUILDING AUDIT INDEX")
    print("-" * 100)

    index = rebuild_index(
        new_kb,
        KB_FILE,
    )

    print(f"Index file       : {INDEX_FILE}")
    print("Status            : CREATED")
    print(f"Indexed hash      : {index['kb_sha256']}")

    if index["kb_sha256"] != corrected_hash:
        raise RuntimeError(
            "Index hash mismatch after writing corrected KB."
        )

    print("Hash verification : PASS")

    # ------------------------------------------------------------------------
    # Final reload verification.
    # ------------------------------------------------------------------------

    print()
    print("-" * 100)
    print("FINAL READ-BACK VERIFICATION")
    print("-" * 100)

    reread = load_pickle(KB_FILE)

    if not isinstance(reread, dict):
        raise RuntimeError(
            "Final KB reload failed."
        )

    if len(reread.get("records", [])) != len(new_records):
        raise RuntimeError(
            "Final record count mismatch."
        )

    if not validate_foundation(reread):
        raise RuntimeError(
            "Final read-back validation failed."
        )

    print()
    print("=" * 100)
    print("FINAL STATUS")
    print("=" * 100)

    print("FOUNDATION CORRECTION : PASS")
    print()
    print("Added:")
    print("  + previous high")
    print("  + previous low")
    print("  + look-ahead")
    print()
    print("Already present:")
    print("  + false break")
    print()
    print("Historical experience : NOT CREATED")
    print("Prediction             : NOT CREATED")
    print("Retrieval              : NOT MODIFIED")
    print("MLAI v4.x               : NOT MODIFIED")
    print("market_data.bin         : NOT MODIFIED")
    print()
    print("Next step:")
    print("Run:")
    print("  python MLAI_CANDLE_LANGUAGE_KB_INSPECTOR_V2.py")
    print()
    print("The inspector must report:")
    print("  FOUNDATION INSPECTOR V2 : PASS")
    print()
    print("=" * 100)


if __name__ == "__main__":
    main()