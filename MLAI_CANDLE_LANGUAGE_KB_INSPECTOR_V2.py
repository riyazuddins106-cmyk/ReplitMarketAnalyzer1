"""
MLAI CANDLE LANGUAGE KB INSPECTOR V2
====================================

Purpose:
    Independent, READ-ONLY verification of candle_language_v2.bin.

This inspector:
    - Does NOT modify the knowledge base.
    - Does NOT modify market_data.bin.
    - Does NOT modify MLAI v4.x.
    - Does NOT create historical experience.
    - Does NOT create predictions.
    - Does NOT alter retrieval.
    - Verifies binary integrity and expected foundational vocabulary.
    - Produces an audit report.

The inspector intentionally detects the binary serialization format
instead of assuming one silently.
"""

from __future__ import annotations

import hashlib
import json
import pickle
import struct
import sys
from pathlib import Path
from collections import Counter


# ================================================================
# CONFIGURATION
# ================================================================

KB_FILE = Path("candle_language_v2.bin")
INDEX_FILE = Path("candle_language_v2.index.json")


# ================================================================
# DISPLAY HELPERS
# ================================================================

WIDTH = 100


def line(char="=", width=WIDTH):
    print(char * width)


def section(title):
    print()
    line("=")
    print(title)
    line("=")


def subsection(title):
    print()
    line("-")
    print(title)
    line("-")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)

            if not chunk:
                break

            h.update(chunk)

    return h.hexdigest()


def safe_str(value):
    try:
        return str(value)
    except Exception:
        return "<unprintable>"


# ================================================================
# FORMAT DETECTION
# ================================================================

def detect_format(raw: bytes) -> str:
    """
    Detect obvious serialization formats from file signatures.

    This does not assume the format.
    """

    if raw.startswith(b"\x80"):
        return "pickle"

    stripped = raw.lstrip()

    if stripped.startswith(b"{") or stripped.startswith(b"["):
        return "json"

    if raw.startswith(b"PK\x03\x04"):
        return "zip/container"

    if raw.startswith(b"\x93NUMPY"):
        return "numpy"

    if raw.startswith(b"ARROW1"):
        return "arrow"

    return "unknown"


# ================================================================
# SAFE LOADERS
# ================================================================

def load_pickle(raw: bytes):
    """
    Load pickle using Python's standard pickle loader.

    IMPORTANT:
    This is only appropriate because this is a local project file
    produced by the user's own project.

    The inspector does not execute arbitrary external files.
    """

    return pickle.loads(raw)


def load_json(raw: bytes):
    return json.loads(raw.decode("utf-8"))


def load_binary_object(path: Path):
    raw = path.read_bytes()

    fmt = detect_format(raw)

    if fmt == "pickle":
        try:
            return fmt, load_pickle(raw), None
        except Exception as exc:
            return fmt, None, exc

    if fmt == "json":
        try:
            return fmt, load_json(raw), None
        except Exception as exc:
            return fmt, None, exc

    return fmt, None, None


# ================================================================
# GENERIC OBJECT NORMALIZATION
# ================================================================

def object_to_records(obj):
    """
    Convert common container structures into a list of records
    without changing the original object.
    """

    if isinstance(obj, list):
        return obj

    if isinstance(obj, tuple):
        return list(obj)

    if isinstance(obj, dict):

        # Common record containers.
        for key in (
            "records",
            "knowledge",
            "rules",
            "items",
            "entries",
            "definitions",
            "data",
            "vocabulary",
        ):
            value = obj.get(key)

            if isinstance(value, (list, tuple)):
                return list(value)

        # A dictionary itself may represent one knowledge record.
        return [obj]

    return [obj]


def object_to_mapping(obj):
    if isinstance(obj, dict):
        return obj

    if hasattr(obj, "__dict__"):
        try:
            return vars(obj)
        except Exception:
            pass

    return {}


# ================================================================
# RECURSIVE TEXT EXTRACTION
# ================================================================

def recursive_strings(obj, depth=0, max_depth=8):
    """
    Extract textual values for audit purposes.

    This is an inspection function only.
    """

    if depth > max_depth:
        return []

    result = []

    if isinstance(obj, str):
        result.append(obj)
        return result

    if isinstance(obj, dict):

        for key, value in obj.items():
            result.extend(recursive_strings(key, depth + 1, max_depth))
            result.extend(recursive_strings(value, depth + 1, max_depth))

        return result

    if isinstance(obj, (list, tuple, set)):

        for value in obj:
            result.extend(recursive_strings(value, depth + 1, max_depth))

        return result

    if hasattr(obj, "__dict__"):

        try:
            result.extend(
                recursive_strings(vars(obj), depth + 1, max_depth)
            )
        except Exception:
            pass

    return result


# ================================================================
# REQUIRED FOUNDATION VOCABULARY
# ================================================================

REQUIRED_TERMS = {

    "candle_anatomy": [
        "body",
        "range",
        "upper_wick",
        "lower_wick",
        "close_position",
    ],

    "candle_direction": [
        "bullish",
        "bearish",
        "neutral",
        "doji",
    ],

    "candle_patterns": [
        "hammer",
        "inverted hammer",
        "shooting star",
        "engulfing",
        "inside bar",
        "outside bar",
    ],

    "sequence": [
        "rejection",
        "compression",
        "expansion",
        "momentum",
        "hesitation",
        "continuation",
        "reversal",
        "pullback",
        "retracement",
    ],

    "structure": [
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
    ],

    "support_resistance": [
        "support",
        "resistance",
        "reaction area",
        "retest",
        "role reversal",
    ],

    "volatility": [
        "atr",
        "volatility",
        "high volatility",
        "low volatility",
        "volatility expansion",
        "volatility contraction",
    ],

    "momentum": [
        "momentum",
        "acceleration",
        "deceleration",
        "exhaustion",
        "follow-through",
    ],

    "context": [
        "context",
        "location",
        "regime",
        "timeframe",
        "session",
    ],

    "liquidity": [
        "equal highs",
        "equal lows",
        "sweep",
        "false break",
    ],

    "causality": [
        "causal",
        "future",
        "look-ahead",
        "completed candle",
    ],

    "scientific_safety": [
        "uncertainty",
        "historical evidence",
        "not certainty",
    ],
}


# ================================================================
# TEXT MATCHING
# ================================================================

def normalized_text(text):
    return " ".join(
        text.lower()
        .replace("_", " ")
        .replace("-", " ")
        .split()
    )


def find_term(term, all_text):
    normalized = normalized_text(all_text)

    return normalized_text(term) in normalized


# ================================================================
# INDEX VALIDATION
# ================================================================

def validate_index(kb_hash):
    results = {}

    if not INDEX_FILE.exists():
        results["index_exists"] = False
        return results

    results["index_exists"] = True

    try:
        index = json.loads(
            INDEX_FILE.read_text(encoding="utf-8")
        )
    except Exception as exc:
        results["index_parse"] = False
        results["index_error"] = safe_str(exc)
        return results

    results["index_parse"] = True
    results["index"] = index

    indexed_hash = None

    if isinstance(index, dict):

        for key in (
            "sha256",
            "kb_sha256",
            "indexed_sha256",
            "hash",
        ):

            if key in index:
                indexed_hash = index[key]
                break

    results["indexed_hash"] = indexed_hash
    results["hash_matches"] = indexed_hash == kb_hash

    return results


# ================================================================
# CATEGORY EXTRACTION
# ================================================================

def inspect_records(records):

    category_counts = Counter()

    names = []

    for record in records:

        mapping = object_to_mapping(record)

        category = None
        name = None

        if mapping:

            for key in (
                "category",
                "type",
                "record_type",
                "kind",
                "topic",
            ):

                if key in mapping:
                    category = safe_str(mapping[key])
                    break

            for key in (
                "name",
                "id",
                "key",
                "pattern",
                "state",
                "title",
            ):

                if key in mapping:
                    name = safe_str(mapping[key])
                    break

        if category:
            category_counts[category] += 1

        if name:
            names.append(name)

    return category_counts, names


# ================================================================
# MAIN INSPECTION
# ================================================================

def main():

    section(
        "MLAI CANDLE LANGUAGE KB INSPECTOR V2"
    )

    print()
    print("PURPOSE")
    print("-" * WIDTH)
    print("Independent READ-ONLY verification of candle_language_v2.bin.")
    print("No market data modification.")
    print("No experience creation.")
    print("No prediction.")
    print("No retrieval modification.")
    print("No MLAI v4.x modification.")

    # ------------------------------------------------------------
    # FILE VALIDATION
    # ------------------------------------------------------------

    section("FILE VALIDATION")

    print(
        f"KB file    : "
        f"{'PASS' if KB_FILE.exists() else 'FAIL'}"
    )

    print(
        f"Index file : "
        f"{'PASS' if INDEX_FILE.exists() else 'FAIL'}"
    )

    if not KB_FILE.exists():

        print()
        print("FATAL: candle_language_v2.bin was not found.")
        print()
        print("Expected:")
        print(f"    {KB_FILE.resolve()}")
        sys.exit(1)

    # ------------------------------------------------------------
    # FILE HASH
    # ------------------------------------------------------------

    section("FILE INTEGRITY")

    kb_hash = sha256_file(KB_FILE)

    print(f"KB SHA256    : {kb_hash}")

    raw = KB_FILE.read_bytes()

    print(f"KB size      : {len(raw):,} bytes")

    # ------------------------------------------------------------
    # FORMAT
    # ------------------------------------------------------------

    section("BINARY FORMAT")

    fmt = detect_format(raw)

    print(f"Detected format : {fmt}")

    if fmt == "unknown":

        print()
        print(
            "STATUS : REVIEW"
        )
        print()
        print(
            "The binary format could not be identified from its "
            "file signature."
        )
        print(
            "No unsupported deserialization was attempted."
        )

        print()
        print(
            "NEXT ACTION:"
        )
        print(
            "Inspect the builder's serialization code before adding "
            "another loader."
        )

        sys.exit(2)

    # ------------------------------------------------------------
    # LOAD
    # ------------------------------------------------------------

    section("READ-ONLY LOAD")

    loaded_format, obj, load_error = load_binary_object(KB_FILE)

    if load_error is not None:

        print("Load status : FAIL")
        print(f"Error       : {load_error}")

        sys.exit(1)

    print("Load status : PASS")
    print(f"Loader      : {loaded_format}")

    # ------------------------------------------------------------
    # OBJECT SUMMARY
    # ------------------------------------------------------------

    section("OBJECT SUMMARY")

    print(f"Python type : {type(obj).__name__}")

    if isinstance(obj, dict):

        print(f"Top-level keys : {len(obj)}")

        for key in obj.keys():

            print(
                f"  - {safe_str(key)}"
            )

    elif isinstance(obj, (list, tuple)):

        print(f"Top-level records : {len(obj)}")

    else:

        print(
            "Top-level object is not a standard list/dictionary."
        )

    # ------------------------------------------------------------
    # RECORDS
    # ------------------------------------------------------------

    records = object_to_records(obj)

    section("KNOWLEDGE RECORD AUDIT")

    print(
        f"Records discovered : {len(records)}"
    )

    category_counts, names = inspect_records(records)

    if category_counts:

        print()
        print("Detected categories:")

        for category, count in sorted(
            category_counts.items(),
            key=lambda x: (-x[1], x[0])
        ):

            print(
                f"  {category:<35} {count}"
            )

    # ------------------------------------------------------------
    # FULL TEXT REPRESENTATION
    # ------------------------------------------------------------

    all_strings = recursive_strings(obj)

    all_text = "\n".join(all_strings)

    print()
    print(
        f"Inspectable text fragments : "
        f"{len(all_strings)}"
    )

    # ------------------------------------------------------------
    # REQUIRED VOCABULARY
    # ------------------------------------------------------------

    section("FOUNDATIONAL VOCABULARY AUDIT")

    total_required = 0
    total_found = 0

    category_results = {}

    for category, terms in REQUIRED_TERMS.items():

        found = []
        missing = []

        for term in terms:

            total_required += 1

            if find_term(term, all_text):

                found.append(term)
                total_found += 1

            else:

                missing.append(term)

        category_results[category] = {
            "found": found,
            "missing": missing,
        }

        if missing:

            status = "REVIEW"

        else:

            status = "PASS"

        print()
        print(
            f"[{status}] {category}"
        )

        if found:

            print(
                "  Found:"
            )

            for term in found:
                print(
                    f"    + {term}"
                )

        if missing:

            print(
                "  Missing:"
            )

            for term in missing:
                print(
                    f"    - {term}"
                )

    # ------------------------------------------------------------
    # SUPPORT / RESISTANCE
    # ------------------------------------------------------------

    section("SUPPORT / RESISTANCE AUDIT")

    sr_terms = [
        "support",
        "resistance",
        "reaction area",
        "prior swing",
        "previous high",
        "previous low",
        "breakout area",
        "retest",
        "failed support",
        "failed resistance",
        "role reversal",
    ]

    sr_found = []
    sr_missing = []

    for term in sr_terms:

        if find_term(term, all_text):
            sr_found.append(term)
        else:
            sr_missing.append(term)

    print(
        f"Found : {len(sr_found)} / {len(sr_terms)}"
    )

    if sr_found:

        print()
        print("Present:")

        for term in sr_found:
            print(
                f"  + {term}"
            )

    if sr_missing:

        print()
        print("Missing:")

        for term in sr_missing:
            print(
                f"  - {term}"
            )

    # ------------------------------------------------------------
    # CAUSALITY
    # ------------------------------------------------------------

    section("CAUSALITY SAFETY AUDIT")

    causality_terms = [
        "causal",
        "future",
        "look-ahead",
        "completed candle",
        "confirmation",
    ]

    causal_found = [
        term
        for term in causality_terms
        if find_term(term, all_text)
    ]

    causal_missing = [
        term
        for term in causality_terms
        if not find_term(term, all_text)
    ]

    print(
        f"Found : {len(causal_found)} / "
        f"{len(causality_terms)}"
    )

    for term in causal_found:
        print(
            f"  + {term}"
        )

    for term in causal_missing:
        print(
            f"  - {term}"
        )

    # ------------------------------------------------------------
    # SEPARATION AUDIT
    # ------------------------------------------------------------

    section("KNOWLEDGE / EXPERIENCE SEPARATION")

    forbidden_experience_terms = [
        "historical occurrence count",
        "outcome distribution",
        "prediction history",
        "actual result",
        "prediction error",
        "experience memory",
        "market_experience",
    ]

    experience_hits = [
        term
        for term in forbidden_experience_terms
        if find_term(term, all_text)
    ]

    if experience_hits:

        print("STATUS : REVIEW")

        print()
        print(
            "Experience-related fields were found inside "
            "the foundational knowledge object:"
        )

        for term in experience_hits:
            print(
                f"  - {term}"
            )

        print()
        print(
            "This does not automatically mean contamination, "
            "but it requires review."
        )

    else:

        print(
            "STATUS : PASS"
        )

        print(
            "No obvious historical-experience records detected."
        )

    # ------------------------------------------------------------
    # INDEX
    # ------------------------------------------------------------

    section("INDEX VALIDATION")

    index_result = validate_index(kb_hash)

    print(
        f"Index exists : "
        f"{'PASS' if index_result.get('index_exists') else 'FAIL'}"
    )

    if index_result.get("index_parse") is False:

        print(
            "Index parse : FAIL"
        )

        print(
            f"Error : {index_result.get('index_error')}"
        )

    elif index_result.get("index_parse"):

        print(
            "Index parse  : PASS"
        )

        indexed_hash = index_result.get(
            "indexed_hash"
        )

        if indexed_hash:

            print(
                f"Indexed hash : {indexed_hash}"
            )

            print(
                "Hash match   : "
                f"{'PASS' if index_result.get('hash_matches') else 'FAIL'}"
            )

        else:

            print(
                "Indexed hash : NOT FOUND"
            )

    # ------------------------------------------------------------
    # FINAL SUMMARY
    # ------------------------------------------------------------

    section("FINAL INSPECTION SUMMARY")

    vocabulary_pass = (
        total_found == total_required
    )

    sr_pass = (
        len(sr_missing) == 0
    )

    causality_pass = (
        len(causal_missing) == 0
    )

    index_pass = (
        index_result.get("index_exists")
        and index_result.get("index_parse")
        and index_result.get("hash_matches")
    )

    experience_separation_pass = (
        len(experience_hits) == 0
    )

    print(
        "KB file                 : PASS"
    )

    print(
        "Binary load             : PASS"
    )

    print(
        "Foundational vocabulary : "
        f"{'PASS' if vocabulary_pass else 'REVIEW'}"
    )

    print(
        "Support/resistance      : "
        f"{'PASS' if sr_pass else 'REVIEW'}"
    )

    print(
        "Causality vocabulary    : "
        f"{'PASS' if causality_pass else 'REVIEW'}"
    )

    print(
        "Knowledge separation    : "
        f"{'PASS' if experience_separation_pass else 'REVIEW'}"
    )

    print(
        "Index integrity         : "
        f"{'PASS' if index_pass else 'REVIEW'}"
    )

    print()
    print(
        f"Vocabulary coverage     : "
        f"{total_found}/{total_required}"
    )

    # ------------------------------------------------------------
    # OVERALL STATUS
    # ------------------------------------------------------------

    overall_pass = (
        vocabulary_pass
        and sr_pass
        and causality_pass
        and index_pass
        and experience_separation_pass
    )

    section("FINAL STATUS")

    if overall_pass:

        print(
            "FOUNDATION INSPECTOR V2 : PASS"
        )

        print()
        print(
            "The foundational knowledge base passed "
            "the independent read-only inspection."
        )

        print()
        print(
            "NEXT GATE:"
        )

        print(
            "1. Audit market_data.bin"
        )

        print(
            "2. Verify canonical candle schema"
        )

        print(
            "3. Verify candle completeness"
        )

        print(
            "4. Build the causal candle-language parser"
        )

        print(
            "5. Only then build chronological experience memory"
        )

        sys.exit(0)

    else:

        print(
            "FOUNDATION INSPECTOR V2 : REVIEW"
        )

        print()
        print(
            "The foundation should NOT be promoted to the "
            "next stage until the REVIEW items are investigated."
        )

        sys.exit(2)


if __name__ == "__main__":
    main()