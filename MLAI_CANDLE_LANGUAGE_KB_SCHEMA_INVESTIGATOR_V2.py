"""
MLAI CANDLE LANGUAGE KB V2 — SCHEMA INVESTIGATOR V2

READ-ONLY STRUCTURAL INVESTIGATION.

Purpose:
    Determine the canonical record schemas already used by
    candle_language_v2.bin before making ANY correction.

This script does NOT modify:
    - candle_language_v2.bin
    - candle_language_v2.index.json
    - market_data.bin
    - MLAI v4.x
    - historical experience
    - retrieval
    - prediction

It specifically investigates:
    1. causality records
    2. support/resistance records
    3. liquidity_proxy records
    4. market_structure records
    5. sequence records
    6. representative records from other categories
    7. duplicate/canonical field structures
    8. vocabulary suitable for previous high / previous low
    9. vocabulary suitable for look-ahead
"""

from __future__ import annotations

import hashlib
import os
import pickle
from collections import Counter, defaultdict
from pprint import pprint


KB_FILE = "candle_language_v2.bin"


TARGET_CATEGORIES = [
    "causality",
    "support_resistance",
    "liquidity_proxy",
    "market_structure",
    "sequence",
    "candle_type",
    "context",
    "structure",
    "interpretation",
    "reasoning",
]


TARGET_TERMS = [
    "previous",
    "prior",
    "high",
    "low",
    "swing",
    "future",
    "causal",
    "confirmation",
    "available",
    "timestamp",
    "completed",
    "look",
    "break",
    "retest",
    "reaction",
]


def sha256_file(path: str) -> str:

    h = hashlib.sha256()

    with open(path, "rb") as f:

        while True:

            chunk = f.read(1024 * 1024)

            if not chunk:
                break

            h.update(chunk)

    return h.hexdigest()


def load_kb():

    with open(KB_FILE, "rb") as f:

        return pickle.load(f)


def normalize(value):

    if isinstance(value, str):

        return value.strip().lower()

    return str(value).strip().lower()


def recursive_strings(value):

    result = []

    if isinstance(value, str):

        result.append(value)

    elif isinstance(value, dict):

        for key, val in value.items():

            result.extend(
                recursive_strings(key)
            )

            result.extend(
                recursive_strings(val)
            )

    elif isinstance(value, (list, tuple, set)):

        for item in value:

            result.extend(
                recursive_strings(item)
            )

    return result


def matching_terms(record):

    text = "\n".join(
        recursive_strings(record)
    ).lower()

    return [
        term
        for term in TARGET_TERMS
        if term.lower() in text
    ]


def field_signature(record):

    if not isinstance(record, dict):

        return ("<non-dict>",)

    return tuple(
        sorted(
            str(k)
            for k in record.keys()
        )
    )


def print_record(index, record):

    print()
    print("=" * 100)
    print(f"RECORD INDEX : {index}")
    print("=" * 100)

    if not isinstance(record, dict):

        print(
            f"Type : {type(record).__name__}"
        )

        pprint(
            record,
            width=120,
        )

        return

    print()
    print("FIELDS")
    print("-" * 100)

    for key, value in record.items():

        print(
            f"{key!r:<30} "
            f"type={type(value).__name__:<12} "
            f"value={repr(value)[:300]}"
        )

    print()
    print("FULL RECORD")
    print("-" * 100)

    pprint(
        record,
        width=120,
        sort_dicts=False,
    )


def main():

    print("=" * 100)
    print("MLAI CANDLE LANGUAGE KB V2 — SCHEMA INVESTIGATOR V2")
    print("=" * 100)

    print()
    print("PURPOSE")
    print("-" * 100)
    print(
        "Determine the existing canonical record schemas before "
        "creating any foundation correction."
    )

    print()
    print("SAFETY")
    print("-" * 100)
    print("Mode                 : READ-ONLY")
    print("KB modification      : NO")
    print("Index modification   : NO")
    print("Market data          : NOT TOUCHED")
    print("Historical experience: NOT CREATED")
    print("Prediction           : NOT CREATED")
    print("Retrieval            : NOT MODIFIED")
    print("MLAI v4.x            : NOT MODIFIED")

    # ------------------------------------------------------------------
    # FILE
    # ------------------------------------------------------------------

    if not os.path.exists(KB_FILE):

        raise FileNotFoundError(
            f"Missing KB file: {KB_FILE}"
        )

    print()
    print("-" * 100)
    print("FILE")
    print("-" * 100)

    print(
        f"Path   : {os.path.abspath(KB_FILE)}"
    )

    print(
        f"Size   : {os.path.getsize(KB_FILE):,} bytes"
    )

    print(
        f"SHA256 : {sha256_file(KB_FILE)}"
    )

    # ------------------------------------------------------------------
    # LOAD
    # ------------------------------------------------------------------

    kb = load_kb()

    if not isinstance(kb, dict):

        raise RuntimeError(
            "Unexpected KB type."
        )

    records = kb.get("records")

    if not isinstance(records, list):

        raise RuntimeError(
            "KB records are not a list."
        )

    print()
    print("-" * 100)
    print("KB SUMMARY")
    print("-" * 100)

    print(
        f"Python type : {type(kb).__name__}"
    )

    print(
        f"Records     : {len(records)}"
    )

    print(
        f"Version     : {kb.get('version')}"
    )

    print(
        f"Schema      : {kb.get('schema_version')}"
    )

    # ------------------------------------------------------------------
    # CATEGORY DISTRIBUTION
    # ------------------------------------------------------------------

    print()
    print("=" * 100)
    print("CATEGORY RECORD COUNTS")
    print("=" * 100)

    category_records = defaultdict(list)

    for index, record in enumerate(records):

        if isinstance(record, dict):

            category = normalize(
                record.get(
                    "category",
                    "<missing>",
                )
            )

            category_records[
                category
            ].append(
                (index, record)
            )

    for category, items in sorted(
        category_records.items()
    ):

        print(
            f"{category:<40} {len(items):>4}"
        )

    # ------------------------------------------------------------------
    # TARGET CATEGORY SCHEMA ANALYSIS
    # ------------------------------------------------------------------

    print()
    print("=" * 100)
    print("CANONICAL SCHEMA ANALYSIS")
    print("=" * 100)

    for category in TARGET_CATEGORIES:

        items = category_records.get(
            category,
            [],
        )

        print()
        print("-" * 100)
        print(
            f"CATEGORY : {category}"
        )
        print("-" * 100)

        if not items:

            print("No records found.")

            continue

        signatures = Counter(
            field_signature(record)
            for _, record in items
        )

        print(
            f"Records : {len(items)}"
        )

        print(
            f"Distinct field schemas : "
            f"{len(signatures)}"
        )

        for signature, count in signatures.most_common():

            print()
            print(
                f"Count {count}:"
            )

            for field in signature:

                print(
                    f"  - {field}"
                )

    # ------------------------------------------------------------------
    # REPRESENTATIVE RECORDS
    # ------------------------------------------------------------------

    print()
    print("=" * 100)
    print("REPRESENTATIVE RECORDS")
    print("=" * 100)

    for category in TARGET_CATEGORIES:

        items = category_records.get(
            category,
            [],
        )

        if not items:

            continue

        print()
        print(
            "#" * 100
        )

        print(
            f"CATEGORY : {category}"
        )

        print(
            "#" * 100
        )

        # Show up to first 5 records.
        for index, record in items[:5]:

            print_record(
                index,
                record,
            )

    # ------------------------------------------------------------------
    # TERM SEARCH
    # ------------------------------------------------------------------

    print()
    print("=" * 100)
    print("SEMANTICALLY RELEVANT RECORD SEARCH")
    print("=" * 100)

    relevant = []

    for index, record in enumerate(records):

        terms = matching_terms(record)

        if terms:

            relevant.append(
                (
                    index,
                    terms,
                    record,
                )
            )

    print()
    print(
        f"Relevant records found : "
        f"{len(relevant)}"
    )

    for index, terms, record in relevant:

        print()
        print(
            f"Record {index} | terms={terms}"
        )

        if isinstance(record, dict):

            print(
                f"  category : "
                f"{record.get('category')}"
            )

            print(
                f"  type     : "
                f"{record.get('type')}"
            )

            print(
                f"  key      : "
                f"{record.get('key')}"
            )

            print(
                f"  name     : "
                f"{record.get('name')}"
            )

    # ------------------------------------------------------------------
    # HIGH / LOW RECORDS
    # ------------------------------------------------------------------

    print()
    print("=" * 100)
    print("HIGH / LOW STRUCTURAL INVESTIGATION")
    print("=" * 100)

    high_low_candidates = []

    for index, record in enumerate(records):

        if not isinstance(record, dict):

            continue

        text = "\n".join(
            recursive_strings(record)
        ).lower()

        has_high = "high" in text
        has_low = "low" in text

        if has_high or has_low:

            high_low_candidates.append(
                (
                    index,
                    record,
                    has_high,
                    has_low,
                )
            )

    print()
    print(
        f"High/low related records : "
        f"{len(high_low_candidates)}"
    )

    for index, record, has_high, has_low in (
        high_low_candidates
    ):

        print()
        print(
            f"Record {index} "
            f"| high={has_high} "
            f"| low={has_low}"
        )

        if isinstance(record, dict):

            print(
                f"  category : "
                f"{record.get('category')}"
            )

            print(
                f"  type     : "
                f"{record.get('type')}"
            )

            print(
                f"  key      : "
                f"{record.get('key')}"
            )

            print(
                f"  human    : "
                f"{record.get('human_meaning')}"
            )

    # ------------------------------------------------------------------
    # CAUSALITY RECORDS IN FULL
    # ------------------------------------------------------------------

    print()
    print("=" * 100)
    print("ALL CAUSALITY RECORDS")
    print("=" * 100)

    causality_records = category_records.get(
        "causality",
        [],
    )

    print(
        f"Count : {len(causality_records)}"
    )

    for index, record in causality_records:

        print_record(
            index,
            record,
        )

    # ------------------------------------------------------------------
    # SUPPORT/RESISTANCE RECORDS IN FULL
    # ------------------------------------------------------------------

    print()
    print("=" * 100)
    print("ALL SUPPORT / RESISTANCE RECORDS")
    print("=" * 100)

    sr_records = category_records.get(
        "support_resistance",
        [],
    )

    print(
        f"Count : {len(sr_records)}"
    )

    for index, record in sr_records:

        print_record(
            index,
            record,
        )

    # ------------------------------------------------------------------
    # LIQUIDITY PROXY RECORDS IN FULL
    # ------------------------------------------------------------------

    print()
    print("=" * 100)
    print("ALL LIQUIDITY PROXY RECORDS")
    print("=" * 100)

    liquidity_records = category_records.get(
        "liquidity_proxy",
        [],
    )

    print(
        f"Count : {len(liquidity_records)}"
    )

    for index, record in liquidity_records:

        print_record(
            index,
            record,
        )

    # ------------------------------------------------------------------
    # KEY INVENTORY
    # ------------------------------------------------------------------

    print()
    print("=" * 100)
    print("KEY INVENTORY")
    print("=" * 100)

    keys = []

    for index, record in enumerate(records):

        if isinstance(record, dict):

            if "key" in record:

                keys.append(
                    (
                        index,
                        record["key"],
                        record.get(
                            "category"
                        ),
                    )
                )

    print(
        f"Records containing 'key' : "
        f"{len(keys)}"
    )

    for index, key, category in keys:

        print(
            f"{index:>4} | "
            f"{str(category):<30} | "
            f"{key}"
        )

    # ------------------------------------------------------------------
    # NAME INVENTORY
    # ------------------------------------------------------------------

    print()
    print("=" * 100)
    print("NAME FIELD INVENTORY")
    print("=" * 100)

    names = []

    for index, record in enumerate(records):

        if isinstance(record, dict):

            if "name" in record:

                names.append(
                    (
                        index,
                        record["name"],
                        record.get(
                            "category"
                        ),
                    )
                )

    print(
        f"Records containing 'name' : "
        f"{len(names)}"
    )

    for index, name, category in names:

        print(
            f"{index:>4} | "
            f"{str(category):<30} | "
            f"{name}"
        )

    # ------------------------------------------------------------------
    # FINAL
    # ------------------------------------------------------------------

    print()
    print("=" * 100)
    print("INVESTIGATION RESULT")
    print("=" * 100)

    print()
    print(
        "READ-ONLY INVESTIGATION COMPLETE."
    )

    print(
        "NO FILES WERE MODIFIED."
    )

    print()
    print(
        "The output identifies the canonical schema that the "
        "correction builder must follow."
    )

    print()
    print(
        "DO NOT run a correction builder until this output "
        "has been reviewed."
    )

    print()
    print("=" * 100)
    print("END")
    print("=" * 100)


if __name__ == "__main__":
    main()