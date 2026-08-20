
"""
MLAI CANDLE LANGUAGE KB V2 — FOUNDATION CORRECTION BUILDER V5

Purpose:
    Correct the foundational vocabulary identified by the read-only
    FOUNDATION INSPECTOR V2.

V5 FIX:
    The V4 builder correctly inserted the "look-ahead" record, but its
    validator normalized "look-ahead" to "look ahead" and then incorrectly
    reported the record as missing.

    This version fixes ONLY that validation mismatch.

IMPORTANT:
    This script modifies ONLY:
        - candle_language_v2.bin
        - candle_language_v2.index.json

It does NOT modify:
        - market_data.bin
        - MLAI v4.x
        - historical experience
        - retrieval
        - prediction models

FOUNDATIONAL CORRECTIONS:
        + previous high
        + previous low
        + look-ahead

IMPORTANT:
    "false break" already exists in the original KB as:
        false_break_behavior

    It is NOT duplicated.

SAFETY:
    Correction records must not contain historical experience,
    prediction, probability, outcome, target, label, return, or
    success/failure fields.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import pickle
import re
import shutil
from datetime import datetime, timezone


# ============================================================================
# FILES
# ============================================================================

KB_FILE = "candle_language_v2.bin"
INDEX_FILE = "candle_language_v2.index.json"

BACKUP_KB = "candle_language_v2.pre_correction_backup.bin"
BACKUP_INDEX = "candle_language_v2.pre_correction_backup.index.json"


# ============================================================================
# REQUIRED CONCEPTS
# ============================================================================

REQUIRED_CONCEPTS = {
    "previous high",
    "previous low",
    "look-ahead",
}


# ============================================================================
# FORBIDDEN EXPERIENCE / PREDICTION FIELDS
# ============================================================================

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
    "labels",
    "target",
    "targets",
}


# ============================================================================
# BASIC FILE UTILITIES
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

    os.replace(
        temp,
        path,
    )


# ============================================================================
# RECURSIVE TEXT EXTRACTION
# ============================================================================

def recursive_text(value):

    fragments = []

    if isinstance(value, str):

        fragments.append(value)

    elif isinstance(value, dict):

        for key, val in value.items():

            fragments.extend(
                recursive_text(key)
            )

            fragments.extend(
                recursive_text(val)
            )

    elif isinstance(value, (list, tuple, set)):

        for item in value:

            fragments.extend(
                recursive_text(item)
            )

    return fragments


# ============================================================================
# NORMALIZATION
# ============================================================================

def normalize_concept_text(text: str) -> str:

    text = str(text).strip().lower()

    # Treat underscore and hyphen as word separators.
    text = re.sub(
        r"[_\-]+",
        " ",
        text,
    )

    # Remove remaining punctuation.
    text = re.sub(
        r"[^a-z0-9\s]+",
        " ",
        text,
    )

    # Normalize whitespace.
    text = re.sub(
        r"\s+",
        " ",
        text,
    ).strip()

    return text


def normalized_text_fragments(obj):

    fragments = []

    for fragment in recursive_text(obj):

        normalized = normalize_concept_text(
            fragment
        )

        if normalized:
            fragments.append(normalized)

    return fragments


def concept_variants(concept: str):

    return {
        normalize_concept_text(concept),
        normalize_concept_text(
            concept.replace(" ", "_")
        ),
        normalize_concept_text(
            concept.replace(" ", "-")
        ),
    }


def contains_concept(obj, concept: str) -> bool:

    variants = concept_variants(
        concept
    )

    fragments = normalized_text_fragments(
        obj
    )

    for fragment in fragments:

        for variant in variants:

            if variant == fragment:
                return True

            if variant in fragment:
                return True

    return False


# ============================================================================
# CONCEPT EVIDENCE
# ============================================================================

def show_concept_evidence(
    obj,
    concept: str,
    maximum: int = 10,
):

    variants = concept_variants(
        concept
    )

    matches = []

    for original in recursive_text(obj):

        if not isinstance(
            original,
            str,
        ):
            continue

        normalized = normalize_concept_text(
            original
        )

        for variant in variants:

            if (
                variant == normalized
                or variant in normalized
            ):

                matches.append(
                    original
                )

                break

        if len(matches) >= maximum:
            break

    return matches


# ============================================================================
# FIELD COLLECTION
# ============================================================================

def collect_field_names(obj):

    fields = set()

    if isinstance(obj, dict):

        for key, value in obj.items():

            fields.add(
                normalize_concept_text(
                    str(key)
                )
            )

            fields.update(
                collect_field_names(value)
            )

    elif isinstance(
        obj,
        (list, tuple, set),
    ):

        for item in obj:

            fields.update(
                collect_field_names(item)
            )

    return fields


def contains_forbidden_field(obj):

    fields = collect_field_names(
        obj
    )

    found = sorted(
        field
        for field in fields
        if field in FORBIDDEN_EXPERIENCE_FIELDS
    )

    return found


# ============================================================================
# CORRECTION RECORDS
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
# FIND CORRECTION RECORD BY NORMALIZED NAME
# ============================================================================

def find_record_by_name(
    records,
    expected_name: str,
):

    expected_normalized = normalize_concept_text(
        expected_name
    )

    for record in records:

        if not isinstance(
            record,
            dict,
        ):
            continue

        record_name = normalize_concept_text(
            record.get(
                "name",
                "",
            )
        )

        if record_name == expected_normalized:

            return record

    return None


# ============================================================================
# VALIDATION
# ============================================================================

def validate_foundation(kb):

    print()
    print("=" * 100)
    print("POST-CORRECTION FOUNDATION VALIDATION")
    print("=" * 100)

    failures = []

    # ------------------------------------------------------------------------
    # Required concepts
    # ------------------------------------------------------------------------

    print()
    print("REQUIRED FOUNDATION VOCABULARY")
    print("-" * 100)

    for concept in sorted(
        REQUIRED_CONCEPTS
    ):

        if contains_concept(
            kb,
            concept,
        ):

            print(
                f"[PASS] {concept}"
            )

        else:

            print(
                f"[FAIL] {concept}"
            )

            failures.append(
                concept
            )

    # ------------------------------------------------------------------------
    # Existing false break
    # ------------------------------------------------------------------------

    print()
    print("EXISTING FOUNDATION VOCABULARY")
    print("-" * 100)

    if contains_concept(
        kb,
        "false break",
    ):

        print(
            "[PASS] false break already present"
        )

        evidence = show_concept_evidence(
            kb,
            "false break",
            maximum=5,
        )

        print(
            "Evidence:"
        )

        for fragment in evidence:

            print(
                f"  + {fragment}"
            )

    else:

        print(
            "[FAIL] false break missing"
        )

        failures.append(
            "false break"
        )

    # ------------------------------------------------------------------------
    # Actual correction records
    # ------------------------------------------------------------------------

    records = kb.get(
        "records",
        [],
    )

    print()
    print("CORRECTION RECORD SAFETY")
    print("-" * 100)

    for expected_name in [
        "previous high",
        "previous low",
        "look-ahead",
    ]:

        record = find_record_by_name(
            records,
            expected_name,
        )

        if record is None:

            print(
                f"[FAIL] {expected_name}: correction record missing"
            )

            failures.append(
                f"{expected_name}: correction record missing"
            )

            continue

        forbidden = contains_forbidden_field(
            record
        )

        if forbidden:

            print(
                f"[FAIL] {expected_name}: "
                f"forbidden fields detected: {forbidden}"
            )

            failures.append(
                f"{expected_name}: forbidden fields"
            )

        else:

            print(
                f"[PASS] {expected_name}: foundational-only record"
            )

    # ------------------------------------------------------------------------
    # False-break duplication
    # ------------------------------------------------------------------------

    print()
    print("FALSE BREAK DUPLICATION CHECK")
    print("-" * 100)

    false_break_named_records = []

    for record in records:

        if not isinstance(
            record,
            dict,
        ):
            continue

        name = normalize_concept_text(
            record.get(
                "name",
                "",
            )
        )

        if name == "false break":

            false_break_named_records.append(
                record
            )

    print(
        "Named 'false break' records : "
        f"{len(false_break_named_records)}"
    )

    if len(
        false_break_named_records
    ) <= 1:

        print(
            "[PASS] No duplicate false-break record created."
        )

    else:

        print(
            "[FAIL] Duplicate false-break records detected."
        )

        failures.append(
            "duplicate false break records"
        )

    # ------------------------------------------------------------------------
    # Final result
    # ------------------------------------------------------------------------

    if failures:

        print()
        print(
            "STATUS : FAIL"
        )

        print()
        print(
            "Failures:"
        )

        seen = set()

        for failure in failures:

            if failure not in seen:

                print(
                    f"  - {failure}"
                )

                seen.add(
                    failure
                )

        return False

    print()
    print(
        "STATUS : PASS"
    )

    print(
        "All required concepts are present."
    )

    print(
        "false break is present and was not duplicated."
    )

    print(
        "All three correction records are foundational-only."
    )

    print(
        "No forbidden experience/prediction fields detected."
    )

    return True


# ============================================================================
# INDEX
# ============================================================================

def rebuild_index(
    kb,
    kb_path,
):

    records = kb.get(
        "records",
        [],
    )

    index = {
        "format": kb.get(
            "format"
        ),

        "version": kb.get(
            "version"
        ),

        "schema_version": kb.get(
            "schema_version"
        ),

        "kb_file": os.path.basename(
            kb_path
        ),

        "kb_sha256": sha256_file(
            kb_path
        ),

        "kb_size": os.path.getsize(
            kb_path
        ),

        "record_count": len(
            records
        ),

        "created_utc": datetime.now(
            timezone.utc
        ).isoformat(),

        "index_type":
            "foundational_knowledge_audit",

        "read_only_reference":
            True,
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
        "Correct the foundational vocabulary while preserving strict "
        "separation between foundational knowledge, historical experience, "
        "and prediction."
    )

    # ========================================================================
    # FILE CHECK
    # ========================================================================

    if not os.path.exists(
        KB_FILE
    ):

        raise FileNotFoundError(
            f"Missing KB file: {KB_FILE}"
        )

    print()
    print("-" * 100)
    print("SOURCE FILE")
    print("-" * 100)

    current_hash = sha256_file(
        KB_FILE
    )

    current_size = os.path.getsize(
        KB_FILE
    )

    print(
        f"KB file       : {KB_FILE}"
    )

    print(
        f"Current hash  : {current_hash}"
    )

    print(
        f"Current size  : {current_size:,} bytes"
    )

    # ========================================================================
    # ORIGINAL BACKUP
    # ========================================================================

    if not os.path.exists(
        BACKUP_KB
    ):

        shutil.copy2(
            KB_FILE,
            BACKUP_KB,
        )

        print()
        print(
            "Original foundation backup created."
        )

        if os.path.exists(
            INDEX_FILE
        ):

            shutil.copy2(
                INDEX_FILE,
                BACKUP_INDEX,
            )

    else:

        print()
        print(
            "Existing original foundation backup found."
        )

        print(
            f"Using: {BACKUP_KB}"
        )

    # ========================================================================
    # LOAD ORIGINAL FOUNDATION
    # ========================================================================

    print()
    print("-" * 100)
    print("LOADING ORIGINAL FOUNDATION")
    print("-" * 100)

    kb = load_pickle(
        BACKUP_KB
    )

    if not isinstance(
        kb,
        dict,
    ):

        raise RuntimeError(
            "Foundation KB must be a dictionary."
        )

    records = kb.get(
        "records"
    )

    if not isinstance(
        records,
        list,
    ):

        raise RuntimeError(
            "Foundation KB records must be a list."
        )

    print(
        f"Source                : {BACKUP_KB}"
    )

    print(
        f"Original record count : {len(records)}"
    )

    # ========================================================================
    # ORIGINAL INTEGRITY
    # ========================================================================

    print()
    print("-" * 100)
    print("ORIGINAL FOUNDATION INTEGRITY")
    print("-" * 100)

    print(
        "Original backup SHA256 : "
        f"{sha256_file(BACKUP_KB)}"
    )

    print(
        "Original backup size   : "
        f"{os.path.getsize(BACKUP_KB):,} bytes"
    )

    # ========================================================================
    # PRE-CORRECTION AUDIT
    # ========================================================================

    print()
    print("-" * 100)
    print("PRE-CORRECTION AUDIT")
    print("-" * 100)

    for concept in sorted(
        REQUIRED_CONCEPTS
    ):

        if contains_concept(
            kb,
            concept,
        ):

            print(
                f"[PRESENT] {concept}"
            )

        else:

            print(
                f"[MISSING] {concept}"
            )

    if contains_concept(
        kb,
        "false break",
    ):

        print(
            "[PRESENT] false break"
        )

        evidence = show_concept_evidence(
            kb,
            "false break",
            maximum=5,
        )

        print(
            "Evidence found:"
        )

        for item in evidence:

            print(
                f"  + {item}"
            )

    else:

        print(
            "[MISSING] false break"
        )

        raise RuntimeError(
            "SAFETY STOP: original foundation does not contain "
            "'false break'. The builder will not manufacture it."
        )

    # ========================================================================
    # BUILD FRESH CORRECTED KB
    # ========================================================================

    new_kb = copy.deepcopy(
        kb
    )

    new_records = copy.deepcopy(
        records
    )

    additions = [
        make_previous_high_record(),
        make_previous_low_record(),
        make_look_ahead_record(),
    ]

    print()
    print("-" * 100)
    print("FOUNDATION CORRECTION")
    print("-" * 100)

    added_count = 0

    for record in additions:

        name = record[
            "name"
        ]

        if contains_concept(
            new_records,
            name,
        ):

            print(
                f"[SKIPPED] {name} already represented"
            )

            continue

        forbidden = contains_forbidden_field(
            record
        )

        if forbidden:

            raise RuntimeError(
                f"Safety failure before insertion: "
                f"{name} contains forbidden fields: "
                f"{forbidden}"
            )

        new_records.append(
            record
        )

        added_count += 1

        print(
            f"[ADDED] {name}"
        )

    new_kb[
        "records"
    ] = new_records

    new_kb[
        "version"
    ] = "2.0"

    new_kb[
        "schema_version"
    ] = "2.0"

    new_kb[
        "corrected_utc"
    ] = datetime.now(
        timezone.utc
    ).isoformat()

    # ========================================================================
    # PRE-WRITE VALIDATION
    # ========================================================================

    print()
    print("-" * 100)
    print("VALIDATING CORRECTED KB BEFORE WRITE")
    print("-" * 100)

    print(
        f"Records before : {len(records)}"
    )

    print(
        f"Records added  : {added_count}"
    )

    print(
        f"Records after  : {len(new_records)}"
    )

    if not validate_foundation(
        new_kb
    ):

        raise RuntimeError(
            "Corrected foundation failed validation. "
            "Original KB has NOT been overwritten."
        )

    # ========================================================================
    # WRITE
    # ========================================================================

    print()
    print("-" * 100)
    print("WRITING CORRECTED FOUNDATION")
    print("-" * 100)

    save_pickle(
        KB_FILE,
        new_kb,
    )

    corrected_hash = sha256_file(
        KB_FILE
    )

    corrected_size = os.path.getsize(
        KB_FILE
    )

    print(
        f"KB file   : {KB_FILE}"
    )

    print(
        "Status    : CREATED"
    )

    print(
        f"Records   : {len(new_records)}"
    )

    print(
        f"SHA256    : {corrected_hash}"
    )

    print(
        f"Size      : {corrected_size:,} bytes"
    )

    # ========================================================================
    # REBUILD INDEX
    # ========================================================================

    print()
    print("-" * 100)
    print("REBUILDING AUDIT INDEX")
    print("-" * 100)

    index = rebuild_index(
        new_kb,
        KB_FILE,
    )

    print(
        f"Index file       : {INDEX_FILE}"
    )

    print(
        "Status            : CREATED"
    )

    print(
        f"Indexed hash      : "
        f"{index['kb_sha256']}"
    )

    if (
        index["kb_sha256"]
        != corrected_hash
    ):

        raise RuntimeError(
            "Index hash mismatch after writing corrected KB."
        )

    print(
        "Hash verification : PASS"
    )

    # ========================================================================
    # FINAL READ-BACK
    # ========================================================================

    print()
    print("-" * 100)
    print("FINAL READ-BACK VERIFICATION")
    print("-" * 100)

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

    final_records = reread.get(
        "records",
        [],
    )

    if len(final_records) != len(
        new_records
    ):

        raise RuntimeError(
            "Final record count mismatch."
        )

    if not validate_foundation(
        reread
    ):

        raise RuntimeError(
            "Final read-back validation failed."
        )

    # ========================================================================
    # FINAL STATUS
    # ========================================================================

    print()
    print("=" * 100)
    print("FINAL STATUS")
    print("=" * 100)

    print(
        "FOUNDATION CORRECTION : PASS"
    )

    print()
    print(
        "Original records:"
    )

    print(
        f"  {len(records)}"
    )

    print()
    print(
        "Added:"
    )

    print(
        "  + previous high"
    )

    print(
        "  + previous low"
    )

    print(
        "  + look-ahead"
    )

    print()
    print(
        "Already present:"
    )

    print(
        "  + false break"
    )

    print()
    print(
        "Final records:"
    )

    print(
        f"  {len(final_records)}"
    )

    print()
    print(
        "Historical experience : NOT CREATED"
    )

    print(
        "Prediction            : NOT CREATED"
    )

    print(
        "Retrieval             : NOT MODIFIED"
    )

    print(
        "MLAI v4.x             : NOT MODIFIED"
    )

    print(
        "market_data.bin       : NOT MODIFIED"
    )

    print()
    print(
        "NEXT GATE"
    )

    print(
        "Run:"
    )

    print(
        "  python MLAI_CANDLE_LANGUAGE_KB_INSPECTOR_V2.py"
    )

    print()
    print(
        "Expected:"
    )

    print(
        "  FOUNDATION INSPECTOR V2 : PASS"
    )

    print()
    print("=" * 100)


if __name__ == "__main__":
    main()
