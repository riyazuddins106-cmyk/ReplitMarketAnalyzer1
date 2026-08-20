"""
===============================================================================
MLAI CANDLE LANGUAGE ARCHIVE BUILDER V1.2
===============================================================================

Purpose
-------
Build a complete historical Candle Language Archive from the existing:

    1. market_data.bin
    2. MLAI_CANDLE_LANGUAGE_KB_V1.json
    3. MLAI_CANDLE_LANGUAGE_INDEX_V1.json
    4. MLAI_CANDLE_LANGUAGE_ENGINE_V2.py

Scientific / causal rules
-------------------------
1. READ market_data.bin only.
2. READ the KB only.
3. READ the engine only.
4. DO NOT modify any source/input file.
5. Candle N may use candles 1..N-1 as historical context.
6. Candle N may NEVER use candles N+1 onward.
7. Every completed candle is archived.
8. Raw OHLC is preserved.
9. Machine language is preserved.
10. Human-readable language is preserved.
11. KB evidence is preserved.
12. Sequence context is preserved.
13. Archive provenance and SHA256 hashes are recorded.
14. No BUY/SELL labels are created.
15. No future information is allowed into a candle's interpretation.
16. Archive metadata is stored consistently.
17. Archive JSON/BIN/INDEX outputs are generated only after validation passes.

Important engine compatibility
------------------------------
MLAI_CANDLE_LANGUAGE_ENGINE_V2 exposes:

    translate(candle, previous, kb)

It does NOT expose:

    translate_candle(...)

This builder therefore calls the actual V2 API.

Outputs
-------
    MLAI_CANDLE_LANGUAGE_ARCHIVE_V1.json
    MLAI_CANDLE_LANGUAGE_ARCHIVE_V1.bin
    MLAI_CANDLE_LANGUAGE_ARCHIVE_INDEX_V1.json

The archive contains one record for every completed candle.

===============================================================================
"""

from __future__ import annotations

import hashlib
import importlib
import inspect
import json
import pickle
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


# =============================================================================
# CONFIGURATION
# =============================================================================

BASE_DIR = Path(__file__).resolve().parent

MARKET_DATA_FILE = BASE_DIR / "market_data.bin"
KB_FILE = BASE_DIR / "MLAI_CANDLE_LANGUAGE_KB_V1.json"
INDEX_FILE = BASE_DIR / "MLAI_CANDLE_LANGUAGE_INDEX_V1.json"
ENGINE_FILE = BASE_DIR / "MLAI_CANDLE_LANGUAGE_ENGINE_V2.py"

ARCHIVE_JSON_FILE = BASE_DIR / "MLAI_CANDLE_LANGUAGE_ARCHIVE_V1.json"
ARCHIVE_BIN_FILE = BASE_DIR / "MLAI_CANDLE_LANGUAGE_ARCHIVE_V1.bin"
ARCHIVE_INDEX_FILE = BASE_DIR / "MLAI_CANDLE_LANGUAGE_ARCHIVE_INDEX_V1.json"

BUILDER_VERSION = "1.2.0"
ARCHIVE_SCHEMA_VERSION = "1.2"


# =============================================================================
# HASHING
# =============================================================================

def sha256_file(path: Path) -> str:
    """Return SHA256 without modifying the file."""

    digest = hashlib.sha256()

    with path.open("rb") as f:
        while True:
            block = f.read(1024 * 1024)

            if not block:
                break

            digest.update(block)

    return digest.hexdigest()


# =============================================================================
# FILE LOADING
# =============================================================================

def load_pickle_read_only(path: Path) -> Any:
    with path.open("rb") as f:
        return pickle.load(f)


def load_json_read_only(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


# =============================================================================
# BASIC VALIDATION
# =============================================================================

def require_file(path: Path, label: str) -> None:

    if not path.exists():
        raise FileNotFoundError(
            f"Required {label} not found:\n{path}"
        )

    if not path.is_file():
        raise RuntimeError(
            f"Required {label} is not a normal file:\n{path}"
        )


def validate_market_data(
    market_data: Any,
) -> List[Dict[str, Any]]:

    if not isinstance(market_data, dict):
        raise TypeError(
            "market_data.bin does not contain a dictionary."
        )

    candles = market_data.get("candles")

    if not isinstance(candles, list):
        raise TypeError(
            "market_data.bin does not contain a 'candles' list."
        )

    if not candles:
        raise ValueError(
            "market_data.bin contains zero candles."
        )

    required_fields = [
        "timestamp",
        "open",
        "high",
        "low",
        "close",
    ]

    for index, candle in enumerate(candles):

        if not isinstance(candle, dict):
            raise TypeError(
                f"Candle {index + 1} is not a dictionary."
            )

        missing = [
            key
            for key in required_fields
            if key not in candle
        ]

        if missing:
            raise ValueError(
                f"Candle {index + 1} missing fields: {missing}"
            )

    return candles


# =============================================================================
# ENGINE LOADING
# =============================================================================

def load_engine_module():
    """
    Import the existing V2 engine.

    The builder verifies that the real V2 public translation API exists.
    """

    if str(BASE_DIR) not in sys.path:
        sys.path.insert(0, str(BASE_DIR))

    module_name = ENGINE_FILE.stem

    # Remove previously loaded module so the current file is used.
    if module_name in sys.modules:
        del sys.modules[module_name]

    engine = importlib.import_module(module_name)

    if not hasattr(engine, "translate"):
        raise AttributeError(
            "MLAI_CANDLE_LANGUAGE_ENGINE_V2.py does not expose "
            "the required translate(candle, previous, kb) function."
        )

    if not callable(engine.translate):
        raise TypeError(
            "engine.translate exists but is not callable."
        )

    return engine


# =============================================================================
# ENGINE API VERIFICATION
# =============================================================================

def verify_engine_api(engine) -> Dict[str, Any]:
    """
    Verify the exact API being used.

    Expected:

        translate(candle, previous, kb)
    """

    translate = getattr(engine, "translate", None)

    if translate is None:
        raise AttributeError(
            "Required engine function 'translate' is missing."
        )

    if not callable(translate):
        raise TypeError(
            "Required engine function 'translate' is not callable."
        )

    signature = inspect.signature(translate)

    parameter_names = list(signature.parameters.keys())

    expected = [
        "candle",
        "previous",
        "kb",
    ]

    if parameter_names[:3] != expected:
        raise RuntimeError(
            "Unexpected engine.translate API.\n"
            f"Expected first parameters: {expected}\n"
            f"Found: {parameter_names}"
        )

    return {
        "function": "translate",
        "parameters": parameter_names,
        "signature": str(signature),
    }


# =============================================================================
# TIMESTAMP ORDER CHECK
# =============================================================================

def validate_timestamp_order(
    candles: List[Dict[str, Any]]
) -> Dict[str, Any]:

    timestamps = []

    for index, candle in enumerate(candles):

        try:
            timestamp = int(candle["timestamp"])
        except Exception as exc:
            raise ValueError(
                f"Invalid timestamp at candle {index + 1}: "
                f"{candle.get('timestamp')!r}"
            ) from exc

        timestamps.append(timestamp)

    duplicate_count = (
        len(timestamps)
        - len(set(timestamps))
    )

    ordering_violations = []

    for i in range(1, len(timestamps)):

        if timestamps[i] <= timestamps[i - 1]:

            ordering_violations.append({
                "index": i,
                "previous_timestamp": timestamps[i - 1],
                "current_timestamp": timestamps[i],
            })

    return {
        "timestamp_count": len(timestamps),
        "duplicate_count": duplicate_count,
        "ordering_violations": ordering_violations,
        "strictly_increasing": (
            duplicate_count == 0
            and not ordering_violations
        ),
    }


# =============================================================================
# CANDLE HASH
# =============================================================================

def candle_fingerprint(
    candle: Dict[str, Any]
) -> str:
    """
    Deterministic fingerprint of the stored candle.

    This proves which raw candle produced the archive record.
    """

    payload = {
        "timestamp": candle.get("timestamp"),
        "datetime": candle.get("datetime"),
        "open": candle.get("open"),
        "high": candle.get("high"),
        "low": candle.get("low"),
        "close": candle.get("close"),
        "volume": candle.get("volume"),
    }

    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")

    return hashlib.sha256(encoded).hexdigest()


# =============================================================================
# UTC TIMESTAMP
# =============================================================================

def utc_now() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


# =============================================================================
# ARCHIVE RECORD BUILDER
# =============================================================================

def build_archive(
    candles: List[Dict[str, Any]],
    kb: Dict[str, Any],
    engine,
) -> List[Dict[str, Any]]:

    records: List[Dict[str, Any]] = []

    total = len(candles)

    print()
    print("=" * 78)
    print("BUILDING HISTORICAL CANDLE LANGUAGE ARCHIVE")
    print("=" * 78)

    print()
    print(
        f"Total completed candles: {total:,}"
    )

    print()
    print("Causal context rule:")
    print(
        "  Candle N sees only candles 1 through N-1 as history."
    )
    print(
        "  Future candles are never supplied to the translator."
    )

    print()
    print("Using engine API:")
    print(
        "  engine.translate(candle, previous, kb)"
    )

    print()

    for index, candle in enumerate(candles):

        # =====================================================================
        # CRITICAL CAUSAL BOUNDARY
        # =====================================================================
        #
        # Current candle:
        #
        #     candles[index]
        #
        # Historical context:
        #
        #     candles[:index]
        #
        # Therefore:
        #
        #     Candle N NEVER sees Candle N+1 onward.
        #
        # =====================================================================

        previous = candles[:index]

        translation = engine.translate(
            candle,
            previous,
            kb,
        )

        if not isinstance(translation, dict):
            raise TypeError(
                f"Engine returned non-dictionary result for "
                f"candle {index + 1}."
            )

        record = {
            "archive_record_version": ARCHIVE_SCHEMA_VERSION,

            "archive_index": index,

            "candle_number": index + 1,

            "total_candles": total,

            "causal_context": {
                "current_candle_index": index,
                "current_candle_number": index + 1,
                "historical_candle_count": len(previous),

                "future_candles_supplied": 0,

                "future_candles_used": False,

                "context_rule": (
                    "Current candle sees only candles "
                    "before the current candle."
                ),
            },

            "source_candle": {
                "fingerprint_sha256": candle_fingerprint(candle),

                "timestamp": candle.get("timestamp"),

                "datetime": candle.get("datetime"),

                "open": candle.get("open"),

                "high": candle.get("high"),

                "low": candle.get("low"),

                "close": candle.get("close"),

                "volume": candle.get("volume"),
            },

            "translation": translation,
        }

        records.append(record)

        if (
            (index + 1) % 100 == 0
            or index == 0
            or index == total - 1
        ):

            print(
                f"  Archived {index + 1:>5,} / {total:,}"
            )

    return records


# =============================================================================
# ARCHIVE INTEGRITY
# =============================================================================

def validate_archive(
    records: List[Dict[str, Any]],
    candles: List[Dict[str, Any]],
) -> Dict[str, Any]:

    errors: List[str] = []

    if len(records) != len(candles):

        errors.append(
            "Archive record count does not equal candle count."
        )

    for index, record in enumerate(records):

        if index >= len(candles):
            errors.append(
                f"Archive contains unexpected record {index + 1}."
            )
            continue

        expected_number = index + 1

        if record.get("candle_number") != expected_number:

            errors.append(
                f"Incorrect candle number at archive index {index}."
            )

        source = record.get(
            "source_candle",
            {},
        )

        original = candles[index]

        # ---------------------------------------------------------------------
        # Raw field verification
        # ---------------------------------------------------------------------

        for field in [
            "timestamp",
            "datetime",
            "open",
            "high",
            "low",
            "close",
            "volume",
        ]:

            if source.get(field) != original.get(field):

                errors.append(
                    f"{field} mismatch at candle "
                    f"{expected_number}."
                )

        # ---------------------------------------------------------------------
        # Fingerprint verification
        # ---------------------------------------------------------------------

        expected_fingerprint = candle_fingerprint(
            original
        )

        if source.get(
            "fingerprint_sha256"
        ) != expected_fingerprint:

            errors.append(
                f"Fingerprint mismatch at candle "
                f"{expected_number}."
            )

        # ---------------------------------------------------------------------
        # Causal verification
        # ---------------------------------------------------------------------

        causal = record.get(
            "causal_context",
            {},
        )

        expected_history = index

        if causal.get(
            "historical_candle_count"
        ) != expected_history:

            errors.append(
                f"Causal history mismatch at candle "
                f"{expected_number}: "
                f"expected {expected_history}, "
                f"got "
                f"{causal.get('historical_candle_count')}."
            )

        if causal.get(
            "current_candle_index"
        ) != index:

            errors.append(
                f"Current candle index mismatch at candle "
                f"{expected_number}."
            )

        if causal.get(
            "current_candle_number"
        ) != expected_number:

            errors.append(
                f"Current candle number mismatch at candle "
                f"{expected_number}."
            )

        if causal.get(
            "future_candles_supplied"
        ) != 0:

            errors.append(
                f"Future candles supplied at candle "
                f"{expected_number}."
            )

        if causal.get(
            "future_candles_used"
        ) is not False:

            errors.append(
                f"Future-candle flag invalid at candle "
                f"{expected_number}."
            )

        # ---------------------------------------------------------------------
        # Translation presence verification
        # ---------------------------------------------------------------------

        translation = record.get(
            "translation"
        )

        if not isinstance(
            translation,
            dict,
        ):

            errors.append(
                f"Translation missing at candle "
                f"{expected_number}."
            )

        else:

            required_translation_sections = [
                "raw_ohlc",
                "machine_language",
                "geometry",
                "human_language",
                "sequence_context",
                "knowledge_base_evidence",
                "scientific_limits",
            ]

            for section in required_translation_sections:

                if section not in translation:

                    errors.append(
                        f"Translation section '{section}' "
                        f"missing at candle "
                        f"{expected_number}."
                    )

    return {
        "passed": not errors,

        "record_count": len(records),

        "expected_count": len(candles),

        "errors": errors,
    }


# =============================================================================
# ARCHIVE METADATA VALIDATION
# =============================================================================

def validate_archive_metadata(
    archive: Dict[str, Any]
) -> Dict[str, Any]:

    required_top_level_fields = [
        "archive_name",
        "archive_schema_version",
        "builder_version",
        "created_utc",
        "purpose",
        "scientific_guarantees",
        "source_provenance",
        "input_summary",
        "engine_api",
        "validation",
        "records",
    ]

    missing = [
        field
        for field in required_top_level_fields
        if field not in archive
    ]

    return {
        "passed": not missing,
        "missing_fields": missing,
    }


# =============================================================================
# WRITE JSON ARCHIVE
# =============================================================================

def write_json_archive(
    archive: Dict[str, Any]
) -> None:

    with ARCHIVE_JSON_FILE.open(
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            archive,
            f,
            indent=2,
            ensure_ascii=False,
        )


# =============================================================================
# WRITE BINARY ARCHIVE
# =============================================================================

def write_binary_archive(
    archive: Dict[str, Any]
) -> None:

    with ARCHIVE_BIN_FILE.open(
        "wb"
    ) as f:

        pickle.dump(
            archive,
            f,
            protocol=pickle.HIGHEST_PROTOCOL,
        )


# =============================================================================
# WRITE ARCHIVE INDEX
# =============================================================================

def write_archive_index(
    archive: Dict[str, Any],
    source_hashes: Dict[str, str],
    validation: Dict[str, Any],
) -> None:

    records = archive["records"]

    engine_versions = sorted({
        str(
            record["translation"].get(
                "engine_version",
                "unknown",
            )
        )
        for record in records
    })

    # =====================================================================
    # IMPORTANT FIX
    # =====================================================================
    #
    # archive["created_utc"] is the actual location of the timestamp.
    #
    # Previous V1.1 code incorrectly attempted:
    #
    #     archive["metadata"]["created_utc"]
    #
    # which caused:
    #
    #     KeyError: 'metadata'
    #
    # =====================================================================

    created_utc = archive["created_utc"]

    index = {

        "archive_name": (
            "MLAI Candle Language Historical Archive V1"
        ),

        "archive_schema_version": ARCHIVE_SCHEMA_VERSION,

        "builder_version": BUILDER_VERSION,

        "created_utc": created_utc,

        "record_count": len(records),

        "engine_versions": engine_versions,

        "source_hashes": source_hashes,

        "validation": validation,

        "causal_guarantees": {

            "completed_candles_only": True,

            "future_candles_used": False,

            "future_candles_supplied": False,

            "historical_context_only": True,

            "candle_n_uses_only_1_to_n_minus_1": True,
        },

        "input_summary": archive[
            "input_summary"
        ],

        "output_files": {

            "json": ARCHIVE_JSON_FILE.name,

            "binary": ARCHIVE_BIN_FILE.name,

            "index": ARCHIVE_INDEX_FILE.name,
        },
    }

    with ARCHIVE_INDEX_FILE.open(
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            index,
            f,
            indent=2,
            ensure_ascii=False,
        )


# =============================================================================
# FINAL OUTPUT VERIFICATION
# =============================================================================

def verify_written_outputs() -> Dict[str, Any]:

    required_outputs = [
        ARCHIVE_JSON_FILE,
        ARCHIVE_BIN_FILE,
        ARCHIVE_INDEX_FILE,
    ]

    missing = [
        str(path)
        for path in required_outputs
        if not path.exists()
    ]

    if missing:
        return {
            "passed": False,
            "missing": missing,
        }

    # -------------------------------------------------------------------------
    # Reload JSON archive
    # -------------------------------------------------------------------------

    try:

        json_archive = load_json_read_only(
            ARCHIVE_JSON_FILE
        )

    except Exception as exc:

        return {
            "passed": False,
            "error": (
                "Could not reload archive JSON: "
                f"{exc}"
            ),
        }

    # -------------------------------------------------------------------------
    # Reload binary archive
    # -------------------------------------------------------------------------

    try:

        binary_archive = load_pickle_read_only(
            ARCHIVE_BIN_FILE
        )

    except Exception as exc:

        return {
            "passed": False,
            "error": (
                "Could not reload archive BIN: "
                f"{exc}"
            ),
        }

    # -------------------------------------------------------------------------
    # Reload index
    # -------------------------------------------------------------------------

    try:

        archive_index = load_json_read_only(
            ARCHIVE_INDEX_FILE
        )

    except Exception as exc:

        return {
            "passed": False,
            "error": (
                "Could not reload archive INDEX: "
                f"{exc}"
            ),
        }

    # -------------------------------------------------------------------------
    # Compare record counts
    # -------------------------------------------------------------------------

    json_records = json_archive.get(
        "records",
        []
    )

    binary_records = binary_archive.get(
        "records",
        []
    )

    json_count = len(json_records)

    binary_count = len(binary_records)

    index_count = archive_index.get(
        "record_count"
    )

    if json_count != binary_count:

        return {
            "passed": False,
            "error": (
                "JSON/BIN record count mismatch."
            ),
            "json_count": json_count,
            "binary_count": binary_count,
        }

    if index_count != json_count:

        return {
            "passed": False,
            "error": (
                "Archive INDEX record count mismatch."
            ),
            "index_count": index_count,
            "json_count": json_count,
        }

    # -------------------------------------------------------------------------
    # Metadata presence
    # -------------------------------------------------------------------------

    metadata_validation = validate_archive_metadata(
        json_archive
    )

    if not metadata_validation["passed"]:

        return {
            "passed": False,
            "error": (
                "Archive metadata validation failed."
            ),
            "missing_fields": (
                metadata_validation[
                    "missing_fields"
                ]
            ),
        }

    # -------------------------------------------------------------------------
    # Created timestamp consistency
    # -------------------------------------------------------------------------

    if (
        archive_index.get("created_utc")
        != json_archive.get("created_utc")
    ):

        return {
            "passed": False,
            "error": (
                "Archive INDEX created_utc does not "
                "match archive JSON."
            ),
        }

    return {
        "passed": True,

        "json_record_count": json_count,

        "binary_record_count": binary_count,

        "index_record_count": index_count,

        "metadata_valid": True,

        "created_utc_consistent": True,
    }


# =============================================================================
# MAIN
# =============================================================================

def main() -> None:

    print("=" * 78)
    print("MLAI CANDLE LANGUAGE ARCHIVE BUILDER V1.2")
    print("=" * 78)

    # =========================================================================
    # FILE CHECKS
    # =========================================================================

    print()
    print("Checking required files...")

    require_file(
        MARKET_DATA_FILE,
        "market data",
    )

    print(
        "  PASS :",
        MARKET_DATA_FILE.name,
    )

    require_file(
        KB_FILE,
        "candle-language KB",
    )

    print(
        "  PASS :",
        KB_FILE.name,
    )

    require_file(
        INDEX_FILE,
        "KB index",
    )

    print(
        "  PASS :",
        INDEX_FILE.name,
    )

    require_file(
        ENGINE_FILE,
        "V2 engine",
    )

    print(
        "  PASS :",
        ENGINE_FILE.name,
    )

    # =========================================================================
    # HASHES
    # =========================================================================

    print()
    print("Calculating source hashes...")

    source_hashes = {

        "market_data_sha256":
            sha256_file(
                MARKET_DATA_FILE
            ),

        "kb_json_sha256":
            sha256_file(
                KB_FILE
            ),

        "kb_index_sha256":
            sha256_file(
                INDEX_FILE
            ),

        "engine_sha256":
            sha256_file(
                ENGINE_FILE
            ),
    }

    print(
        "market_data.bin SHA256 :",
        source_hashes[
            "market_data_sha256"
        ],
    )

    print(
        "KB JSON SHA256         :",
        source_hashes[
            "kb_json_sha256"
        ],
    )

    print(
        "KB index SHA256        :",
        source_hashes[
            "kb_index_sha256"
        ],
    )

    print(
        "Engine SHA256          :",
        source_hashes[
            "engine_sha256"
        ],
    )

    # =========================================================================
    # LOAD INPUTS
    # =========================================================================

    print()
    print("Loading market data...")

    market_data = load_pickle_read_only(
        MARKET_DATA_FILE
    )

    print(
        "Loading candle-language KB..."
    )

    kb = load_json_read_only(
        KB_FILE
    )

    print(
        "Loading KB index..."
    )

    kb_index = load_json_read_only(
        INDEX_FILE
    )

    print(
        "Loading existing V2 engine..."
    )

    engine = load_engine_module()

    # =========================================================================
    # ENGINE API
    # =========================================================================

    print()
    print("ENGINE API VALIDATION")
    print("-" * 78)

    engine_api = verify_engine_api(
        engine
    )

    print(
        "Function  :",
        engine_api["function"],
    )

    print(
        "Signature :",
        engine_api["signature"],
    )

    print(
        "API status: PASS"
    )

    # =========================================================================
    # INPUT VALIDATION
    # =========================================================================

    candles = validate_market_data(
        market_data
    )

    if not isinstance(
        kb,
        dict,
    ):

        raise TypeError(
            "KB JSON must contain a dictionary."
        )

    if not isinstance(
        kb_index,
        dict,
    ):

        raise TypeError(
            "KB index JSON must contain a dictionary."
        )

    print()
    print("INPUT VALIDATION")
    print("-" * 78)

    print(
        "Market candles :",
        f"{len(candles):,}",
    )

    print(
        "KB schema      :",
        kb.get(
            "schema_version",
            "unknown",
        ),
    )

    print(
        "KB rules       :",
        len(
            kb.get(
                "rules",
                []
            )
        ),
    )

    print(
        "KB sources     :",
        len(
            kb.get(
                "sources",
                []
            )
        ),
    )

    print(
        "KB index records:",
        kb_index.get(
            "record_count",
            "unknown",
        ),
    )

    # =========================================================================
    # TIMESTAMP VALIDATION
    # =========================================================================

    timestamp_validation = (
        validate_timestamp_order(
            candles
        )
    )

    print()
    print("TIMESTAMP VALIDATION")
    print("-" * 78)

    print(
        "Strictly increasing:",
        "PASS"
        if timestamp_validation[
            "strictly_increasing"
        ]
        else "FAIL",
    )

    print(
        "Duplicate timestamps:",
        timestamp_validation[
            "duplicate_count"
        ],
    )

    print(
        "Ordering violations:",
        len(
            timestamp_validation[
                "ordering_violations"
            ]
        ),
    )

    if not timestamp_validation[
        "strictly_increasing"
    ]:

        raise RuntimeError(
            "Timestamp validation failed. "
            "Archive construction stopped."
        )

    # =========================================================================
    # BUILD
    # =========================================================================

    records = build_archive(
        candles=candles,
        kb=kb,
        engine=engine,
    )

    # =========================================================================
    # VALIDATE
    # =========================================================================

    print()
    print("=" * 78)
    print("ARCHIVE VALIDATION")
    print("=" * 78)

    validation = validate_archive(
        records,
        candles,
    )

    print(
        "Record count:",
        validation[
            "record_count"
        ],
    )

    print(
        "Expected    :",
        validation[
            "expected_count"
        ],
    )

    print(
        "Causal validation:",
        "PASS"
        if validation["passed"]
        else "FAIL",
    )

    if not validation["passed"]:

        print()
        print("ERRORS:")

        for error in validation[
            "errors"
        ][:50]:

            print(
                "  -",
                error,
            )

        raise RuntimeError(
            "Archive validation failed. "
            "No archive should be considered valid."
        )

    # =========================================================================
    # ARCHIVE METADATA
    # =========================================================================

    first_candle = candles[0]
    last_candle = candles[-1]

    archive_created_utc = utc_now()

    archive = {

        "archive_name":
            "MLAI Candle Language Historical Archive V1",

        "archive_schema_version":
            ARCHIVE_SCHEMA_VERSION,

        "builder_version":
            BUILDER_VERSION,

        "created_utc":
            archive_created_utc,

        "purpose": (
            "Historical completed-candle language archive "
            "with causal candle-by-candle context."
        ),

        "scientific_guarantees": {

            "read_only_inputs": True,

            "completed_candles_only": True,

            "future_candles_used": False,

            "future_candles_supplied": False,

            "historical_context_only": True,

            "buy_sell_labels_created": False,

            "hidden_order_inference": False,

            "exact_buyer_seller_counts": False,
        },

        "source_provenance": {

            "market_data_file":
                MARKET_DATA_FILE.name,

            "kb_file":
                KB_FILE.name,

            "kb_index_file":
                INDEX_FILE.name,

            "engine_file":
                ENGINE_FILE.name,

            "hashes":
                source_hashes,
        },

        "input_summary": {

            "candle_count":
                len(candles),

            "first_timestamp":
                first_candle.get(
                    "timestamp"
                ),

            "first_datetime":
                first_candle.get(
                    "datetime"
                ),

            "last_timestamp":
                last_candle.get(
                    "timestamp"
                ),

            "last_datetime":
                last_candle.get(
                    "datetime"
                ),

            "timestamp_validation":
                timestamp_validation,
        },

        "engine_api":
            engine_api,

        "validation":
            validation,

        "records":
            records,
    }

    # =========================================================================
    # METADATA VALIDATION BEFORE WRITING
    # =========================================================================

    metadata_validation = (
        validate_archive_metadata(
            archive
        )
    )

    if not metadata_validation["passed"]:

        raise RuntimeError(
            "Archive metadata validation failed before writing: "
            + str(
                metadata_validation[
                    "missing_fields"
                ]
            )
        )

    # =========================================================================
    # WRITE OUTPUTS
    # =========================================================================

    print()
    print("=" * 78)
    print("WRITING ARCHIVE")
    print("=" * 78)

    print()
    print(
        "Writing:",
        ARCHIVE_JSON_FILE.name,
    )

    write_json_archive(
        archive
    )

    print(
        "PASS :",
        ARCHIVE_JSON_FILE.name,
    )

    print()
    print(
        "Writing:",
        ARCHIVE_BIN_FILE.name,
    )

    write_binary_archive(
        archive
    )

    print(
        "PASS :",
        ARCHIVE_BIN_FILE.name,
    )

    print()
    print(
        "Writing:",
        ARCHIVE_INDEX_FILE.name,
    )

    write_archive_index(
        archive,
        source_hashes,
        validation,
    )

    print(
        "PASS :",
        ARCHIVE_INDEX_FILE.name,
    )

    # =========================================================================
    # RELOAD AND VERIFY WRITTEN OUTPUTS
    # =========================================================================

    print()
    print("=" * 78)
    print("WRITTEN OUTPUT VERIFICATION")
    print("=" * 78)

    output_validation = (
        verify_written_outputs()
    )

    print(
        "JSON reload:",
        "PASS"
        if output_validation["passed"]
        else "FAIL",
    )

    if output_validation["passed"]:

        print(
            "JSON records :",
            output_validation[
                "json_record_count"
            ],
        )

        print(
            "BIN records  :",
            output_validation[
                "binary_record_count"
            ],
        )

        print(
            "INDEX records:",
            output_validation[
                "index_record_count"
            ],
        )

        print(
            "Metadata      : PASS"
        )

        print(
            "Timestamp consistency: PASS"
        )

    else:

        print(
            "OUTPUT VERIFICATION ERROR:"
        )

        print(
            output_validation
        )

        raise RuntimeError(
            "Written archive verification failed."
        )

    # =========================================================================
    # OUTPUT HASHES
    # =========================================================================

    print()
    print("OUTPUT HASHES")
    print("-" * 78)

    archive_json_hash = sha256_file(
        ARCHIVE_JSON_FILE
    )

    archive_bin_hash = sha256_file(
        ARCHIVE_BIN_FILE
    )

    archive_index_hash = sha256_file(
        ARCHIVE_INDEX_FILE
    )

    print(
        "Archive JSON SHA256  :",
        archive_json_hash,
    )

    print(
        "Archive BIN SHA256   :",
        archive_bin_hash,
    )

    print(
        "Archive INDEX SHA256 :",
        archive_index_hash,
    )

    # =========================================================================
    # FINAL STATUS
    # =========================================================================

    print()
    print("=" * 78)
    print("FINAL ARCHIVE STATUS")
    print("=" * 78)

    print()

    print(
        "Total candles archived:",
        f"{len(records):,}",
    )

    print(
        "Causal records valid  : YES"
    )

    print(
        "Future leakage        : NO"
    )

    print(
        "Future candles supplied: NO"
    )

    print(
        "Source files modified : NO"
    )

    print(
        "Raw OHLC preserved     : YES"
    )

    print(
        "Machine language       : YES"
    )

    print(
        "Human language         : YES"
    )

    print(
        "KB evidence            : YES"
    )

    print(
        "Per-candle fingerprint : YES"
    )

    print(
        "JSON/BIN consistency   : YES"
    )

    print(
        "Archive INDEX verified : YES"
    )

    print()
    print("OUTPUT FILES")
    print("-" * 78)

    print(
        ARCHIVE_JSON_FILE
    )

    print(
        ARCHIVE_BIN_FILE
    )

    print(
        ARCHIVE_INDEX_FILE
    )

    print()
    print("=" * 78)
    print(
        "MLAI CANDLE LANGUAGE ARCHIVE BUILDER V1.2 COMPLETE"
    )
    print("=" * 78)


if __name__ == "__main__":
    main()