"""
MLAI CANDLE LANGUAGE KB V2 — STRUCTURE INVESTIGATOR V1

PURPOSE
-------
READ-ONLY investigation of the actual internal structure of
candle_language_v2.bin.

This script DOES NOT:
    - modify candle_language_v2.bin
    - modify the index
    - modify market_data.bin
    - create experience
    - modify retrieval
    - modify prediction
    - modify MLAI v4.x

It determines exactly why the aggregate vocabulary audit can report
"look-ahead" as present while the correction-record audit reports
"look-ahead correction record missing".

It also determines exactly how "false break" is represented.
"""

from __future__ import annotations

import hashlib
import json
import os
import pickle
from pprint import pprint


KB_FILE = "candle_language_v2.bin"


SEARCH_TERMS = [
    "look-ahead",
    "look ahead",
    "lookahead",
    "false break",
    "false_break",
    "previous high",
    "previous_high",
    "previous low",
    "previous_low",
]


def sha256_file(path):
    h = hashlib.sha256()

    with open(path, "rb") as f:
        while True:
            chunk = f.read(1024 * 1024)

            if not chunk:
                break

            h.update(chunk)

    return h.hexdigest()


def contains_term(value, terms):
    """
    Recursively determine whether any search term occurs in the
    textual representation of an object.
    """

    if isinstance(value, str):

        text = value.lower()

        return [
            term
            for term in terms
            if term.lower() in text
        ]

    if isinstance(value, dict):

        found = []

        for key, val in value.items():

            found.extend(
                contains_term(key, terms)
            )

            found.extend(
                contains_term(val, terms)
            )

        return sorted(set(found))

    if isinstance(value, (list, tuple, set)):

        found = []

        for item in value:

            found.extend(
                contains_term(item, terms)
            )

        return sorted(set(found))

    return []


def path_walk(value, path="root"):
    """
    Yield every nested object together with its structural path.
    """

    yield path, value

    if isinstance(value, dict):

        for key, val in value.items():

            yield from path_walk(
                val,
                f"{path}[{key!r}]",
            )

    elif isinstance(value, (list, tuple)):

        for index, item in enumerate(value):

            yield from path_walk(
                item,
                f"{path}[{index}]",
            )


def compact(value, max_length=500):
    """
    Produce readable representation without flooding the console.
    """

    try:

        text = repr(value)

    except Exception:

        text = f"<{type(value).__name__}>"

    if len(text) > max_length:

        return text[:max_length] + " ..."

    return text


def main():

    print("=" * 100)
    print("MLAI CANDLE LANGUAGE KB V2 — STRUCTURE INVESTIGATOR V1")
    print("=" * 100)

    print()
    print("PURPOSE")
    print("-" * 100)
    print(
        "Determine the ACTUAL structural representation of "
        "look-ahead and false break."
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
            f"Missing file: {KB_FILE}"
        )

    print()
    print("-" * 100)
    print("FILE")
    print("-" * 100)

    print(f"Path   : {os.path.abspath(KB_FILE)}")
    print(f"Size   : {os.path.getsize(KB_FILE):,} bytes")
    print(f"SHA256 : {sha256_file(KB_FILE)}")

    # ------------------------------------------------------------------
    # LOAD
    # ------------------------------------------------------------------

    with open(KB_FILE, "rb") as f:

        kb = pickle.load(f)

    print()
    print("-" * 100)
    print("TOP-LEVEL STRUCTURE")
    print("-" * 100)

    print(f"Python type : {type(kb).__name__}")

    if isinstance(kb, dict):

        print(f"Top keys    : {len(kb)}")

        for key in kb.keys():

            print(f"  - {key}")

    else:

        raise RuntimeError(
            "Unexpected KB type."
        )

    records = kb.get("records")

    if not isinstance(records, list):

        raise RuntimeError(
            "KB 'records' is not a list."
        )

    print()
    print(f"Record count : {len(records)}")

    # ------------------------------------------------------------------
    # SEARCH EVERY RECORD
    # ------------------------------------------------------------------

    print()
    print("=" * 100)
    print("TARGET TERM STRUCTURAL SEARCH")
    print("=" * 100)

    matches = []

    for index, record in enumerate(records):

        found_terms = contains_term(
            record,
            SEARCH_TERMS,
        )

        if found_terms:

            matches.append(
                (
                    index,
                    found_terms,
                    record,
                )
            )

    print()
    print(f"Matching records : {len(matches)}")

    # ------------------------------------------------------------------
    # SHOW MATCHES
    # ------------------------------------------------------------------

    for index, found_terms, record in matches:

        print()
        print("=" * 100)
        print(f"RECORD INDEX : {index}")
        print("=" * 100)

        print()
        print("MATCHED TERMS")
        print("-" * 100)

        for term in found_terms:

            print(f"  + {term}")

        print()
        print("RECORD TYPE")
        print("-" * 100)

        print(type(record).__name__)

        print()
        print("TOP-LEVEL FIELDS")
        print("-" * 100)

        if isinstance(record, dict):

            for key, value in record.items():

                print(
                    f"  {key!r} : "
                    f"{type(value).__name__}"
                )

        print()
        print("FULL RECORD")
        print("-" * 100)

        pprint(
            record,
            width=120,
            sort_dicts=False,
        )

    # ------------------------------------------------------------------
    # SPECIFIC NAME FIELD AUDIT
    # ------------------------------------------------------------------

    print()
    print("=" * 100)
    print("EXACT NAME FIELD AUDIT")
    print("=" * 100)

    target_names = {
        "look-ahead",
        "previous high",
        "previous low",
        "false break",
    }

    exact_name_matches = []

    for index, record in enumerate(records):

        if not isinstance(record, dict):

            continue

        name = record.get("name")

        if isinstance(name, str):

            normalized = name.strip().lower()

            if normalized in target_names:

                exact_name_matches.append(
                    (
                        index,
                        normalized,
                        record,
                    )
                )

    print()
    print(
        f"Exact record-name matches : "
        f"{len(exact_name_matches)}"
    )

    if exact_name_matches:

        for index, name, record in exact_name_matches:

            print()
            print(
                f"[FOUND] record index={index} "
                f"name={name!r}"
            )

            pprint(
                record,
                width=120,
                sort_dicts=False,
            )

    else:

        print("No exact target names found.")

    # ------------------------------------------------------------------
    # FIELD-NAME INVENTORY FOR MATCHING RECORDS
    # ------------------------------------------------------------------

    print()
    print("=" * 100)
    print("FIELD STRUCTURE OF MATCHING RECORDS")
    print("=" * 100)

    for index, found_terms, record in matches:

        print()
        print(
            f"Record {index} "
            f"| terms={found_terms}"
        )

        fields = set()

        for path, value in path_walk(record):

            if isinstance(value, dict):

                for key in value.keys():

                    fields.add(
                        str(key)
                    )

        for field in sorted(fields):

            print(
                f"  - {field}"
            )

    # ------------------------------------------------------------------
    # SEARCH PATHS
    # ------------------------------------------------------------------

    print()
    print("=" * 100)
    print("EXACT TERM LOCATIONS")
    print("=" * 100)

    for term in SEARCH_TERMS:

        print()
        print(f"TERM: {term}")
        print("-" * 100)

        found = False

        for index, record in enumerate(records):

            for path, value in path_walk(
                record,
                f"records[{index}]",
            ):

                if isinstance(value, str):

                    if term.lower() in value.lower():

                        print(
                            f"  {path} "
                            f"= {value!r}"
                        )

                        found = True

        if not found:

            print("  NOT FOUND")

    # ------------------------------------------------------------------
    # RECORD CATEGORY DISTRIBUTION
    # ------------------------------------------------------------------

    print()
    print("=" * 100)
    print("CATEGORY DISTRIBUTION")
    print("=" * 100)

    categories = {}

    for record in records:

        if isinstance(record, dict):

            category = record.get(
                "category",
                "<missing>",
            )

            categories[str(category)] = (
                categories.get(
                    str(category),
                    0,
                )
                + 1
            )

    for category, count in sorted(
        categories.items(),
        key=lambda x: (-x[1], x[0]),
    ):

        print(
            f"{category:<40} {count}"
        )

    # ------------------------------------------------------------------
    # FINAL DIAGNOSIS
    # ------------------------------------------------------------------

    print()
    print("=" * 100)
    print("INVESTIGATION STATUS")
    print("=" * 100)

    print()
    print(
        "NO FILES WERE MODIFIED."
    )

    print()
    print(
        "The output above is required before creating another "
        "correction builder."
    )

    print()
    print(
        "Specifically we need to determine:"
    )

    print(
        "  1. Where 'look-ahead' actually exists."
    )

    print(
        "  2. Why the validator does not recognize that "
        "location as a correction record."
    )

    print(
        "  3. Where 'false break' actually exists."
    )

    print(
        "  4. What schema the original KB uses for vocabulary "
        "records."
    )

    print(
        "  5. Whether the correction records should use the "
        "existing KB schema instead of a newly invented schema."
    )

    print()
    print("=" * 100)
    print("END OF READ-ONLY INVESTIGATION")
    print("=" * 100)


if __name__ == "__main__":
    main()