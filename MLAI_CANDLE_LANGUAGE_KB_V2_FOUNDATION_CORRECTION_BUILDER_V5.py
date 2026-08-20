"""
MLAI CANDLE LANGUAGE KB V2
FOUNDATION CORRECTION BUILDER V5

Purpose
-------
Correct the foundational vocabulary using the ACTUAL schema discovered by
MLAI_CANDLE_LANGUAGE_KB_STRUCTURE_INVESTIGATOR_V1 and the schema investigation.

IMPORTANT
---------
This builder does NOT invent a new record schema.

The original KB contains:
    178 records
    178 records with a 'key' field
    0 records with a 'name' field

Therefore all vocabulary validation is performed using canonical 'key'
records.

Known canonical representations already present:

    prior_high
        -> semantically represents previous high

    prior_low
        -> semantically represents previous low

    false_break_behavior
        -> semantically represents false break

Missing canonical concept:

    look_ahead

This builder therefore adds ONLY the genuinely missing causality concept.

Safety
------
No:
    market_data.bin modification
    historical experience
    prediction
    retrieval modification
    MLAI v4.x modification

The original 178-record backup is always used as the source.

The live KB is written ONLY after complete pre-write validation succeeds.
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


# ============================================================================
# CANONICAL CONCEPT MAPPING
# ============================================================================

CONCEPT_ALIASES = {
    "previous high": {
        "prior_high",
    },

    "previous low": {
        "prior_low",
    },

    "false break": {
        "false_break_behavior",
    },

    "look-ahead": {
        "look_ahead",
        "lookahead",
        "look_ahead_detection",
    },
}


# Only this concept is genuinely missing according to the investigation.
MISSING_CANONICAL_KEY = "look_ahead"


FORBIDDEN_FIELDS = {
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
# FILE UTILITIES
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


# ============================================================================
# STRUCTURE UTILITIES
# ============================================================================

def get_records(kb):
    records = kb.get("records")

    if not isinstance(records, list):
        raise RuntimeError(
            "KB 'records' must be a list."
        )

    return records


def canonical_keys(records):
    return {
        str(record.get("key", "")).strip().lower()
        for record in records
        if isinstance(record, dict)
        and str(record.get("key", "")).strip()
    }


def records_with_key(records, key):
    key = key.lower().strip()

    return [
        record
        for record in records
        if isinstance(record, dict)
        and str(record.get("key", "")).strip().lower() == key
    ]


def find_semantic_concept(records, concept):
    """
    Determine whether a conceptual vocabulary item already exists
    using the canonical aliases established by investigation.
    """

    aliases = CONCEPT_ALIASES.get(
        concept.lower().strip(),
        set(),
    )

    keys = canonical_keys(records)

    matches = sorted(
        alias
        for alias in aliases
        if alias.lower() in keys
    )

    return matches


def collect_field_names(obj):
    fields = set()

    if isinstance(obj, dict):

        for key, value in obj.items():

            fields.add(
                str(key).strip().lower()
            )

            fields.update(
                collect_field_names(value)
            )

    elif isinstance(obj, (list, tuple, set)):

        for item in obj:

            fields.update(
                collect_field_names(item)
            )

    return fields


def forbidden_fields(obj):

    fields = collect_field_names(obj)

    return sorted(
        field
        for field in fields
        if field in FORBIDDEN_FIELDS
    )


# ============================================================================
# ACTUAL KB SCHEMA VALIDATION
# ============================================================================

def validate_original_schema(kb):

    records = get_records(kb)

    print()
    print("=" * 100)
    print("ORIGINAL KB SCHEMA VALIDATION")
    print("=" * 100)

    records_with_key_count = 0
    records_with_name_count = 0

    for record in records:

        if not isinstance(record, dict):
            raise RuntimeError(
                "A KB record is not a dictionary."
            )

        if "key" in record:
            records_with_key_count += 1

        if "name" in record:
            records_with_name_count += 1

    print(
        f"Records                  : {len(records)}"
    )

    print(
        f"Records containing key   : "
        f"{records_with_key_count}"
    )

    print(
        f"Records containing name  : "
        f"{records_with_name_count}"
    )

    if records_with_key_count != len(records):

        raise RuntimeError(
            "Unexpected schema: not every record contains 'key'."
        )

    if records_with_name_count != 0:

        raise RuntimeError(
            "Unexpected schema: 'name' field exists in original KB."
        )

    print()
    print("[PASS] Canonical vocabulary field = key")
    print("[PASS] No name-based vocabulary schema detected")

    return True


# ============================================================================
# LOOK-AHEAD RECORD
# ============================================================================

def make_look_ahead_record():

    record = {
        "type": "rule",
        "category": "causality",
        "key": "look_ahead",

        "meaning": (
            "Look-ahead occurs when information unavailable at the "
            "evaluation timestamp is used to describe, classify, retrieve, "
            "model, or interpret the market state."
        ),

        "technical_definition": (
            "A market-state feature violates causal availability when it "
            "depends on information whose availability timestamp is later "
            "than the evaluation timestamp."
        ),

        "human_meaning": (
            "In simple language, look-ahead means using information from "
            "later candles before that information would actually have "
            "been known. MLAI must not do this."
        ),

        "dependencies": [
            "completed_candles_only",
            "multi_timeframe_separation",
        ],

        "source": "MLAI foundational specification",

        "status": "candidate",
    }

    return record


# ============================================================================
# RECORD SAFETY
# ============================================================================

def validate_foundational_record(record):

    required_fields = {
        "type",
        "category",
        "key",
        "meaning",
        "technical_definition",
        "human_meaning",
        "dependencies",
        "source",
        "status",
    }

    missing = sorted(
        required_fields
        - set(record.keys())
    )

    if missing:

        raise RuntimeError(
            "look_ahead record is missing required canonical "
            f"schema fields: {missing}"
        )

    if "name" in record:

        raise RuntimeError(
            "look_ahead record incorrectly uses invented 'name' field."
        )

    forbidden = forbidden_fields(record)

    if forbidden:

        raise RuntimeError(
            "look_ahead record contains forbidden fields: "
            f"{forbidden}"
        )

    if record.get("type") != "rule":

        raise RuntimeError(
            "look_ahead must use type='rule'."
        )

    if record.get("category") != "causality":

        raise RuntimeError(
            "look_ahead must use category='causality'."
        )

    if record.get("key") != "look_ahead":

        raise RuntimeError(
            "look_ahead canonical key mismatch."
        )

    return True


# ============================================================================
# FOUNDATION VALIDATION
# ============================================================================

def validate_corrected_foundation(kb):

    records = get_records(kb)

    keys = canonical_keys(records)

    failures = []

    print()
    print("=" * 100)
    print("CORRECTED FOUNDATION VALIDATION")
    print("=" * 100)

    # ------------------------------------------------------------------------
    # Previous high
    # ------------------------------------------------------------------------

    print()
    print("PREVIOUS HIGH")
    print("-" * 100)

    matches = find_semantic_concept(
        records,
        "previous high",
    )

    if matches:

        print(
            "[PASS] previous high is represented by canonical key:"
        )

        for key in matches:
            print(f"  + {key}")

    else:

        print("[FAIL] previous high has no canonical representation")
        failures.append("previous high")

    # ------------------------------------------------------------------------
    # Previous low
    # ------------------------------------------------------------------------

    print()
    print("PREVIOUS LOW")
    print("-" * 100)

    matches = find_semantic_concept(
        records,
        "previous low",
    )

    if matches:

        print(
            "[PASS] previous low is represented by canonical key:"
        )

        for key in matches:
            print(f"  + {key}")

    else:

        print("[FAIL] previous low has no canonical representation")
        failures.append("previous low")

    # ------------------------------------------------------------------------
    # False break
    # ------------------------------------------------------------------------

    print()
    print("FALSE BREAK")
    print("-" * 100)

    matches = find_semantic_concept(
        records,
        "false break",
    )

    if matches:

        print(
            "[PASS] false break is represented by canonical key:"
        )

        for key in matches:
            print(f"  + {key}")

    else:

        print("[FAIL] false break has no canonical representation")
        failures.append("false break")

    # ------------------------------------------------------------------------
    # Look-ahead
    # ------------------------------------------------------------------------

    print()
    print("LOOK-AHEAD")
    print("-" * 100)

    lookahead_records = records_with_key(
        records,
        "look_ahead",
    )

    if not lookahead_records:

        print(
            "[FAIL] canonical key 'look_ahead' missing"
        )

        failures.append(
            "look_ahead"
        )

    else:

        print(
            f"[PASS] canonical key 'look_ahead' present "
            f"({len(lookahead_records)} record)"
        )

        if len(lookahead_records) != 1:

            print(
                "[FAIL] look_ahead must occur exactly once"
            )

            failures.append(
                "look_ahead duplicate"
            )

        for record in lookahead_records:

            try:

                validate_foundational_record(
                    record
                )

                print(
                    "[PASS] look_ahead follows actual KB rule schema"
                )

            except Exception as exc:

                print(
                    f"[FAIL] look_ahead schema/safety: {exc}"
                )

                failures.append(
                    "look_ahead schema/safety"
                )

    # ------------------------------------------------------------------------
    # Forbidden fields in newly created record
    # ------------------------------------------------------------------------

    print()
    print("FOUNDATIONAL SAFETY")
    print("-" * 100)

    for record in lookahead_records:

        forbidden = forbidden_fields(record)

        if forbidden:

            print(
                "[FAIL] look_ahead forbidden fields:"
                f" {forbidden}"
            )

            failures.append(
                "look_ahead forbidden fields"
            )

        else:

            print(
                "[PASS] look_ahead contains no experience/prediction fields"
            )

    # ------------------------------------------------------------------------
    # Duplicate prevention
    # ------------------------------------------------------------------------

    print()
    print("DUPLICATION CHECK")
    print("-" * 100)

    for key in (
        "prior_high",
        "prior_low",
        "false_break_behavior",
        "look_ahead",
    ):

        count = len(
            records_with_key(
                records,
                key,
            )
        )

        print(
            f"{key:<30} : {count}"
        )

        if count != 1:

            failures.append(
                f"{key} duplicate/missing"
            )

    # ------------------------------------------------------------------------
    # Result
    # ------------------------------------------------------------------------

    print()

    if failures:

        print("STATUS : FAIL")

        print()
        print("Failures:")

        for failure in failures:
            print(f"  - {failure}")

        return False

    print("STATUS : PASS")

    print()
    print(
        "All required foundational concepts are represented "
        "using the actual KB schema."
    )

    return True


# ============================================================================
# INDEX
# ============================================================================

def rebuild_index(kb):

    records = get_records(kb)

    index = {
        "format": kb.get("format"),
        "version": kb.get("version"),
        "schema_version": kb.get("schema_version"),
        "kb_file": os.path.basename(KB_FILE),
        "kb_sha256": sha256_file(KB_FILE),
        "kb_size": os.path.getsize(KB_FILE),
        "record_count": len(records),
        "created_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "index_type": "foundational_knowledge_audit",
        "read_only_reference": True,
    }

    temp = INDEX_FILE + ".tmp"

    with open(
        temp,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            index,
            f,
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        )

    os.replace(
        temp,
        INDEX_FILE,
    )

    return index


# ============================================================================
# MAIN
# ============================================================================

def main():

    print("=" * 100)
    print(
        "MLAI CANDLE LANGUAGE KB V2 — "
        "FOUNDATION CORRECTION BUILDER V5"
    )
    print("=" * 100)

    print()
    print("PURPOSE")
    print("-" * 100)
    print(
        "Correct only genuinely missing foundational vocabulary "
        "using the actual discovered KB schema."
    )

    # ------------------------------------------------------------------------
    # FILE CHECK
    # ------------------------------------------------------------------------

    if not os.path.exists(KB_FILE):

        raise FileNotFoundError(
            f"Missing KB file: {KB_FILE}"
        )

    current_hash = sha256_file(
        KB_FILE
    )

    current_size = os.path.getsize(
        KB_FILE
    )

    print()
    print("SOURCE FILE")
    print("-" * 100)

    print(
        f"KB file       : {KB_FILE}"
    )

    print(
        f"Current hash  : {current_hash}"
    )

    print(
        f"Current size  : {current_size:,} bytes"
    )

    # ------------------------------------------------------------------------
    # BACKUP
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
        print(
            "Original foundation backup created."
        )

    else:

        print()
        print(
            "Existing original foundation backup found."
        )

    # ------------------------------------------------------------------------
    # LOAD BACKUP
    # ------------------------------------------------------------------------

    print()
    print("LOADING ORIGINAL FOUNDATION")
    print("-" * 100)

    source_hash = sha256_file(
        BACKUP_KB
    )

    source_size = os.path.getsize(
        BACKUP_KB
    )

    print(
        f"Backup SHA256 : {source_hash}"
    )

    print(
        f"Backup size   : {source_size:,} bytes"
    )

    kb = load_pickle(
        BACKUP_KB
    )

    if not isinstance(kb, dict):

        raise RuntimeError(
            "Original foundation must be a dictionary."
        )

    records = get_records(
        kb
    )

    print(
        f"Original records : {len(records)}"
    )

    if len(records) != 178:

        raise RuntimeError(
            "Expected original foundation to contain exactly 178 "
            f"records; found {len(records)}."
        )

    # ------------------------------------------------------------------------
    # ACTUAL SCHEMA
    # ------------------------------------------------------------------------

    validate_original_schema(
        kb
    )

    # ------------------------------------------------------------------------
    # CONCEPT AUDIT
    # ------------------------------------------------------------------------

    print()
    print("=" * 100)
    print("SEMANTIC FOUNDATION AUDIT")
    print("=" * 100)

    for concept in (
        "previous high",
        "previous low",
        "false break",
        "look-ahead",
    ):

        matches = find_semantic_concept(
            records,
            concept,
        )

        if matches:

            print(
                f"[PRESENT] {concept:<20} -> "
                f"{', '.join(matches)}"
            )

        else:

            print(
                f"[MISSING] {concept:<20}"
            )

    # ------------------------------------------------------------------------
    # Determine whether correction is actually needed.
    # ------------------------------------------------------------------------

    existing_lookahead = records_with_key(
        records,
        MISSING_CANONICAL_KEY,
    )

    if existing_lookahead:

        print()
        print(
            "[INFO] look_ahead already exists in the original backup."
        )

        print(
            "[INFO] No new correction record will be created."
        )

        corrected = copy.deepcopy(
            kb
        )

    else:

        # ------------------------------------------------------------
        # Add only the genuinely missing canonical concept.
        # ------------------------------------------------------------

        print()
        print("=" * 100)
        print("FOUNDATION CORRECTION")
        print("=" * 100)

        new_record = make_look_ahead_record()

        validate_foundational_record(
            new_record
        )

        print(
            "[PASS] New look_ahead record matches actual KB schema."
        )

        print(
            "[PASS] New look_ahead record contains no forbidden fields."
        )

        corrected = copy.deepcopy(
            kb
        )

        corrected_records = corrected[
            "records"
        ]

        corrected_records.append(
            new_record
        )

        corrected[
            "records"
        ] = corrected_records

        print(
            "[ADDED] look_ahead"
        )

    # ------------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------------

    corrected[
        "corrected_utc"
    ] = datetime.now(
        timezone.utc
    ).isoformat()

    # ------------------------------------------------------------------------
    # PRE-WRITE VALIDATION
    # ------------------------------------------------------------------------

    print()
    print("=" * 100)
    print("PRE-WRITE VALIDATION")
    print("=" * 100)

    print(
        f"Records before : {len(records)}"
    )

    print(
        f"Records after  : "
        f"{len(corrected.get('records', []))}"
    )

    if not validate_corrected_foundation(
        corrected
    ):

        raise RuntimeError(
            "Corrected foundation failed validation. "
            "Original KB has NOT been overwritten."
        )

    # ------------------------------------------------------------------------
    # SAVE
    # ------------------------------------------------------------------------

    print()
    print("=" * 100)
    print("WRITING CORRECTED FOUNDATION")
    print("=" * 100)

    save_pickle(
        KB_FILE,
        corrected,
    )

    corrected_hash = sha256_file(
        KB_FILE
    )

    corrected_size = os.path.getsize(
        KB_FILE
    )

    print(
        f"KB hash : {corrected_hash}"
    )

    print(
        f"KB size : {corrected_size:,} bytes"
    )

    # ------------------------------------------------------------------------
    # INDEX
    # ------------------------------------------------------------------------

    print()
    print("=" * 100)
    print("REBUILDING INDEX")
    print("=" * 100)

    index = rebuild_index(
        corrected
    )

    print(
        f"Indexed hash : {index['kb_sha256']}"
    )

    if index["kb_sha256"] != corrected_hash:

        raise RuntimeError(
            "Index hash mismatch."
        )

    print(
        "Hash verification : PASS"
    )

    # ------------------------------------------------------------------------
    # FINAL READ-BACK
    # ------------------------------------------------------------------------

    print()
    print("=" * 100)
    print("FINAL READ-BACK VERIFICATION")
    print("=" * 100)

    reread = load_pickle(
        KB_FILE
    )

    if not isinstance(
        reread,
        dict,
    ):

        raise RuntimeError(
            "Final KB reload failed."
        )

    if not validate_corrected_foundation(
        reread
    ):

        raise RuntimeError(
            "Final read-back validation failed."
        )

    final_records = get_records(
        reread
    )

    print()
    print("=" * 100)
    print("FINAL STATUS")
    print("=" * 100)

    print(
        "FOUNDATION CORRECTION : PASS"
    )

    print()
    print(
        "Canonical representations:"
    )

    print(
        "  previous high  -> prior_high"
    )

    print(
        "  previous low   -> prior_low"
    )

    print(
        "  false break    -> false_break_behavior"
    )

    print(
        "  look-ahead     -> look_ahead"
    )

    print()
    print(
        f"Final records    : {len(final_records)}"
    )

    print(
        "Historical experience : NOT CREATED"
    )

    print(
        "Prediction             : NOT CREATED"
    )

    print(
        "Retrieval              : NOT MODIFIED"
    )

    print(
        "MLAI v4.x              : NOT MODIFIED"
    )

    print(
        "market_data.bin        : NOT MODIFIED"
    )

    print()
    print(
        "NEXT STEP"
    )

    print("-" * 100)

    print(
        "Run:"
    )

    print(
        "python MLAI_CANDLE_LANGUAGE_KB_INSPECTOR_V2.py"
    )

    print()
    print(
        "Then give me the complete inspector output."
    )

    print("=" * 100)


if __name__ == "__main__":
    main()