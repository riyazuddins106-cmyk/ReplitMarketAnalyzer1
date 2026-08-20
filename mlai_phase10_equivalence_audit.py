"""
MLAI PHASE 10B
V4.15 / CANONICAL TARGET-OUTCOME EQUIVALENCE AUDIT

READ ONLY.

This audit:
    - does not modify production source files
    - does not modify market_data.bin
    - does not perform Git operations
    - loads the canonical candle dictionaries from market_data.bin
    - converts them IN MEMORY into v4.15 Candle objects
    - computes a causal ATR sequence
    - calls the actual v4.15 make_outcome API
    - compares returned outcomes with the canonical target/outcome calculation
    - distinguishes API/data execution errors from actual mismatches
"""

from __future__ import annotations

import hashlib
import importlib
import math
import pickle
import traceback
from pathlib import Path
from typing import Any, Optional, Sequence


# =============================================================================
# CONFIGURATION
# =============================================================================

MARKET_DATA_FILE = Path("market_data.bin")

V415_MODULE = "mlai_market_structure_v415"
CONTRACT_MODULE = "mlai_target_outcome_contract"

HORIZONS = (4, 8, 16)

TEST_INDICES = (
    0,
    1,
    2,
    10,
    25,
    50,
    100,
)

ATR_PERIOD = 14

RETURN_TOLERANCE = 1e-12


# =============================================================================
# DISPLAY
# =============================================================================

def banner(title: str) -> None:
    print("=" * 90)
    print(title)
    print("=" * 90)


# =============================================================================
# SAFE HELPERS
# =============================================================================

def safe_repr(value: Any, limit: int = 1000) -> str:
    try:
        text = repr(value)
    except Exception as exc:
        text = f"<repr failed: {type(exc).__name__}: {exc}>"

    if len(text) > limit:
        return text[:limit] + "...<truncated>"

    return text


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        while True:
            block = handle.read(1024 * 1024)

            if not block:
                break

            digest.update(block)

    return digest.hexdigest()


# =============================================================================
# GENERIC CANDLE FIELD ACCESS
# =============================================================================

def field(candle: Any, name: str) -> Any:
    """
    Read a candle field from either:
        - dictionary candles
        - object/dataclass candles
    """

    if isinstance(candle, dict):

        if name in candle:
            return candle[name]

        aliases = {
            "timestamp": ("time", "datetime"),
            "open": ("Open",),
            "high": ("High",),
            "low": ("Low",),
            "close": ("Close",),
            "volume": ("Volume",),
        }

        for alias in aliases.get(name, ()):
            if alias in candle:
                return candle[alias]

        raise KeyError(
            f"Candle dictionary has no field '{name}'. "
            f"Available keys: {list(candle.keys())}"
        )

    if hasattr(candle, name):
        return getattr(candle, name)

    aliases = {
        "timestamp": ("time", "datetime"),
        "open": ("Open",),
        "high": ("High",),
        "low": ("Low",),
        "close": ("Close",),
        "volume": ("Volume",),
    }

    for alias in aliases.get(name, ()):

        if hasattr(candle, alias):
            return getattr(candle, alias)

    raise AttributeError(
        f"Candle object has no field '{name}'"
    )


def numeric(candle: Any, name: str) -> float:
    value = field(candle, name)

    result = float(value)

    if not math.isfinite(result):
        raise ValueError(
            f"Non-finite candle field {name}: {value!r}"
        )

    return result


# =============================================================================
# MARKET DATA LOAD
# =============================================================================

def load_candles() -> list[Any]:
    banner("MARKET DATA LOAD")

    if not MARKET_DATA_FILE.exists():
        raise FileNotFoundError(
            f"Missing {MARKET_DATA_FILE.resolve()}"
        )

    digest = sha256_file(MARKET_DATA_FILE)

    print(f"File SHA256 : {digest}")

    with MARKET_DATA_FILE.open("rb") as handle:
        payload = pickle.load(handle)

    print(f"Outer type  : {type(payload).__name__}")

    if not isinstance(payload, dict):
        raise TypeError(
            "market_data.bin outer object must be a dictionary."
        )

    print(f"Keys        : {list(payload.keys())}")

    if "candles" not in payload:
        raise KeyError(
            "market_data.bin does not contain 'candles'."
        )

    candles = payload["candles"]

    if not isinstance(candles, list):
        candles = list(candles)

    print(f"Candle type : {type(candles).__name__}")
    print(f"Candle count: {len(candles)}")

    if not candles:
        raise ValueError(
            "Canonical candle list is empty."
        )

    first = candles[0]

    print(
        f"First candle type: "
        f"{type(first).__name__}"
    )

    print(
        f"First candle     : "
        f"{safe_repr(first)}"
    )

    return candles


# =============================================================================
# V4.15 CANDLE ADAPTER
# =============================================================================

def adapt_canonical_candles_for_v415(
    canonical_candles: Sequence[Any],
    v415: Any,
) -> list[Any]:
    """
    Convert serialized canonical candle dictionaries into
    actual mlai_market_structure_v415.Candle objects.

    IMPORTANT:

    This creates a NEW in-memory list.

    The original market_data.bin data is never modified.
    """

    banner("V4.15 CANDLE ADAPTER")

    Candle = getattr(v415, "Candle", None)

    if Candle is None:
        raise AttributeError(
            "mlai_market_structure_v415.Candle is unavailable."
        )

    print(
        f"Source candles        : "
        f"{len(canonical_candles)}"
    )

    print(
        f"Target Candle class   : "
        f"{Candle}"
    )

    adapted: list[Any] = []

    for index, candle in enumerate(canonical_candles):

        if isinstance(candle, Candle):

            adapted.append(candle)
            continue

        if not isinstance(candle, dict):
            raise TypeError(
                f"Canonical candle {index} must be dict "
                f"or {Candle.__name__}, "
                f"got {type(candle).__name__}"
            )

        required = (
            "timestamp",
            "open",
            "high",
            "low",
            "close",
        )

        missing = [
            name
            for name in required
            if name not in candle
        ]

        if missing:
            raise ValueError(
                f"Canonical candle {index} "
                f"missing fields: {missing}"
            )

        adapted.append(
            Candle(
                index=index,
                timestamp=candle["timestamp"],
                open=float(candle["open"]),
                high=float(candle["high"]),
                low=float(candle["low"]),
                close=float(candle["close"]),
                volume=float(
                    candle.get("volume", 0.0)
                ),
            )
        )

    print(
        f"Adapted candles      : "
        f"{len(adapted)}"
    )

    if adapted:

        print(
            f"Adapted candle type  : "
            f"{type(adapted[0]).__name__}"
        )

        print(
            f"Adapted first candle : "
            f"{safe_repr(adapted[0])}"
        )

    if len(adapted) != len(canonical_candles):
        raise RuntimeError(
            "Candle adapter changed candle count."
        )

    return adapted


# =============================================================================
# CAUSAL ATR
# =============================================================================

def build_causal_atr(
    candles: Sequence[Any],
    period: int = ATR_PERIOD,
) -> list[Optional[float]]:
    """
    Build ATR using information available through the current candle only.

    True Range:

        max(
            high_i - low_i,
            abs(high_i - close_(i-1)),
            abs(low_i - close_(i-1))
        )

    ATR is a rolling arithmetic mean over the previous
    `period` true ranges including the current candle.

    No future candle is accessed.
    """

    if period <= 0:
        raise ValueError(
            "ATR period must be positive."
        )

    true_ranges: list[float] = []

    atr: list[Optional[float]] = []

    previous_close: Optional[float] = None

    for index, candle in enumerate(candles):

        high = numeric(candle, "high")
        low = numeric(candle, "low")
        close = numeric(candle, "close")

        if high < low:
            raise ValueError(
                f"Invalid candle at index {index}: "
                f"high < low."
            )

        if previous_close is None:

            tr = high - low

        else:

            tr = max(
                high - low,
                abs(high - previous_close),
                abs(low - previous_close),
            )

        true_ranges.append(tr)

        if len(true_ranges) < period:

            atr.append(None)

        else:

            window = true_ranges[-period:]

            value = sum(window) / period

            if not math.isfinite(value):
                raise ValueError(
                    f"Non-finite ATR at index {index}."
                )

            atr.append(value)

        previous_close = close

    return atr


# =============================================================================
# ATR DIAGNOSTICS
# =============================================================================

def inspect_atr(
    candles: Sequence[Any],
    atr: Sequence[Optional[float]],
) -> None:

    banner("CAUSAL ATR DIAGNOSTIC")

    print(
        f"ATR period       : "
        f"{ATR_PERIOD}"
    )

    print(
        f"ATR length       : "
        f"{len(atr)}"
    )

    print(
        f"ATR[0]           : "
        f"{safe_repr(atr[0] if atr else None)}"
    )

    print(
        f"ATR[{ATR_PERIOD - 1}]       : "
        f"{safe_repr(atr[ATR_PERIOD - 1] if len(atr) >= ATR_PERIOD else None)}"
    )

    valid = [
        value
        for value in atr
        if value is not None
        and math.isfinite(value)
        and value > 0
    ]

    print(
        f"Valid ATR values : "
        f"{len(valid)}"
    )

    if valid:

        print(
            f"Minimum ATR      : "
            f"{min(valid)}"
        )

        print(
            f"Maximum ATR      : "
            f"{max(valid)}"
        )


# =============================================================================
# V4.15 IMPORT / API
# =============================================================================

def load_v415() -> Any:

    banner("V4.15 API")

    module = importlib.import_module(
        V415_MODULE
    )

    print(
        f"Module  : "
        f"{module.__name__}"
    )

    print(
        f"VERSION : "
        f"{getattr(module, 'VERSION', 'UNKNOWN')}"
    )

    required = (
        "Candle",
        "make_outcome",
        "rolling_return",
        "CausalStructureEngine",
        "ExperienceRecord",
        "Outcome",
    )

    for name in required:

        print(
            f"{name:<24}: "
            f"{'PRESENT' if hasattr(module, name) else 'MISSING'}"
        )

    missing = [
        name
        for name in required
        if not hasattr(module, name)
    ]

    if missing:
        raise AttributeError(
            "v4.15 is missing required API symbols: "
            f"{missing}"
        )

    return module


# =============================================================================
# OUTCOME EXTRACTION
# =============================================================================

def get_attr(
    obj: Any,
    names: Sequence[str],
    default: Any = None,
) -> Any:

    for name in names:

        if hasattr(obj, name):
            return getattr(obj, name)

        if isinstance(obj, dict) and name in obj:
            return obj[name]

    return default


def normalize_direction(
    value: Any,
) -> Optional[str]:

    if value is None:
        return None

    text = str(value).strip().lower()

    mapping = {
        "bullish": "higher",
        "bull": "higher",
        "up": "higher",
        "long": "higher",
        "higher": "higher",

        "bearish": "lower",
        "bear": "lower",
        "down": "lower",
        "short": "lower",
        "lower": "lower",

        "neutral": "neutral",
        "flat": "neutral",
    }

    return mapping.get(text, text)


def extract_v415_outcome(
    result: Any,
) -> dict[str, Any]:

    if result is None:

        return {
            "direction": None,
            "raw_return": None,
            "atr_return": None,
            "mfe_atr": None,
            "mae_atr": None,
        }

    return {
        "direction": normalize_direction(
            get_attr(
                result,
                ("direction",),
            )
        ),

        "raw_return": get_attr(
            result,
            (
                "raw_return",
                "return_pct",
                "future_return",
            ),
        ),

        "atr_return": get_attr(
            result,
            (
                "atr_return",
                "atr_normalized_return",
            ),
        ),

        "mfe_atr": get_attr(
            result,
            ("mfe_atr",),
        ),

        "mae_atr": get_attr(
            result,
            ("mae_atr",),
        ),
    }


# =============================================================================
# CANONICAL CONTRACT
# =============================================================================

def inspect_contract(
    contract: Any,
) -> None:

    banner("CANONICAL CONTRACT")

    print(
        f"Module: "
        f"{contract.__name__}"
    )

    for name in (
        "HORIZONS",
        "TARGET",
        "CONTRACT_VERSION",
        "VERSION",
        "CONTRACT_SHA256",
    ):

        if hasattr(contract, name):

            print(
                f"{name:<20}: "
                f"{safe_repr(getattr(contract, name))}"
            )

    print(
        "\nRelevant public symbols:"
    )

    for name in dir(contract):

        lower = name.lower()

        if (
            "target" in lower
            or "outcome" in lower
            or "horizon" in lower
            or "label" in lower
            or "contract" in lower
        ):

            if not name.startswith("_"):
                print(
                    f"  {name}"
                )


# =============================================================================
# CANONICAL TARGET CALCULATION
# =============================================================================

def canonical_outcome(
    candles: Sequence[Any],
    index: int,
    horizon: int,
) -> dict[str, Any]:
    """
    Canonical audit target:

        base   = close[index]
        target = close[index + horizon]

        raw_return = (target - base) / base

        direction:
            higher
            lower
            neutral

    This is an audit calculation only.
    """

    if index < 0:
        raise IndexError(
            "Negative index."
        )

    target = index + horizon

    if target >= len(candles):
        raise IndexError(
            f"Insufficient future candles: "
            f"index={index}, "
            f"horizon={horizon}, "
            f"target={target}, "
            f"count={len(candles)}"
        )

    base = numeric(
        candles[index],
        "close",
    )

    future = numeric(
        candles[target],
        "close",
    )

    raw_return = (
        (future - base) / base
    )

    if future > base:

        direction = "higher"

    elif future < base:

        direction = "lower"

    else:

        direction = "neutral"

    return {
        "direction": direction,
        "raw_return": raw_return,
        "future_close": future,
        "base_close": base,
    }


# =============================================================================
# NUMERICAL COMPARISON
# =============================================================================

def numeric_equal(
    left: Any,
    right: Any,
    tolerance: float = RETURN_TOLERANCE,
) -> bool:

    if left is None or right is None:

        return (
            left is None
            and right is None
        )

    try:

        a = float(left)
        b = float(right)

    except Exception:

        return left == right

    if (
        not math.isfinite(a)
        or not math.isfinite(b)
    ):

        return a == b

    return abs(a - b) <= tolerance


def compare_outcomes(
    canonical: dict[str, Any],
    v415: dict[str, Any],
) -> list[str]:

    mismatches: list[str] = []

    if (
        canonical["direction"]
        != v415["direction"]
    ):

        mismatches.append(
            "direction: "
            f"canonical={canonical['direction']!r}, "
            f"v415={v415['direction']!r}"
        )

    if not numeric_equal(
        canonical["raw_return"],
        v415["raw_return"],
    ):

        mismatches.append(
            "raw_return: "
            f"canonical={canonical['raw_return']!r}, "
            f"v415={v415['raw_return']!r}"
        )

    return mismatches


# =============================================================================
# EQUIVALENCE AUDIT
# =============================================================================

def run_audit(
    canonical_candles: Sequence[Any],
    v415_candles: Sequence[Any],
    atr: Sequence[Optional[float]],
    v415: Any,
) -> tuple[int, int, int]:

    banner(
        "PHASE 10B — EQUIVALENCE CHECKS"
    )

    make_outcome = v415.make_outcome

    checks = 0
    mismatches = 0
    errors = 0

    if len(canonical_candles) != len(v415_candles):

        raise RuntimeError(
            "Canonical and v4.15 candle counts differ."
        )

    usable_indices: list[int] = []

    for index in TEST_INDICES:

        if index < 0:
            continue

        if index >= len(canonical_candles):
            continue

        if atr[index] is None:

            print(
                f"INDEX={index:<4} "
                f"SKIP — ATR unavailable"
            )

            continue

        usable_indices.append(index)

    print(
        f"Usable test indices: "
        f"{usable_indices}"
    )

    for horizon in HORIZONS:

        for index in usable_indices:

            target = index + horizon

            if target >= len(canonical_candles):

                print(
                    f"INDEX={index:<4} "
                    f"H={horizon:<3} "
                    f"SKIP — future boundary"
                )

                continue

            checks += 1

            print(
                f"\nINDEX={index:<4} "
                f"H={horizon:<3}"
            )

            # =============================================================
            # CANONICAL
            # =============================================================

            try:

                expected = canonical_outcome(
                    canonical_candles,
                    index,
                    horizon,
                )

            except Exception as exc:

                errors += 1

                print(
                    "  STATUS: CANONICAL_ERROR"
                )

                print(
                    f"  {type(exc).__name__}: "
                    f"{exc}"
                )

                traceback.print_exc()

                continue

            # =============================================================
            # V4.15
            # =============================================================

            try:

                # CRITICAL FIX:
                #
                # Pass v4.15 Candle objects, NOT the
                # serialized dictionaries from market_data.bin.
                #
                # The original failure:
                #
                #   AttributeError:
                #   'dict' object has no attribute 'close'
                #
                # happened because make_outcome() expects
                # candles[index].close.

                actual_obj = make_outcome(
                    v415_candles,
                    atr,
                    index,
                    horizon,
                )

                actual = extract_v415_outcome(
                    actual_obj
                )

            except Exception as exc:

                errors += 1

                print(
                    "  STATUS: V415_ERROR"
                )

                print(
                    f"  {type(exc).__name__}: "
                    f"{exc}"
                )

                traceback.print_exc()

                continue

            # =============================================================
            # COMPARE
            # =============================================================

            differences = compare_outcomes(
                expected,
                actual,
            )

            if differences:

                mismatches += 1

                print(
                    "  STATUS: MISMATCH"
                )

                print(
                    "  CANONICAL: "
                    f"{safe_repr(expected)}"
                )

                print(
                    "  V4.15    : "
                    f"{safe_repr(actual)}"
                )

                for difference in differences:

                    print(
                        f"  DIFF     : "
                        f"{difference}"
                    )

            else:

                print(
                    "  STATUS: PASS"
                )

                print(
                    "  direction : "
                    f"{expected['direction']}"
                )

                print(
                    "  raw_return: "
                    f"{expected['raw_return']:.12g}"
                )

                print(
                    "  v4.15 MFE : "
                    f"{actual['mfe_atr']!r}"
                )

                print(
                    "  v4.15 MAE : "
                    f"{actual['mae_atr']!r}"
                )

    return (
        checks,
        mismatches,
        errors,
    )


# =============================================================================
# MAIN
# =============================================================================

def main() -> int:

    banner(
        "MLAI PHASE 10B — "
        "V4.15 / CANONICAL OUTCOME "
        "EQUIVALENCE AUDIT"
    )

    print(
        """
READ-ONLY AUDIT

No source files will be modified.
No market data will be modified.
No Git operations will be performed.
"""
    )

    # ---------------------------------------------------------------------
    # Load v4.15
    # ---------------------------------------------------------------------

    try:

        v415 = load_v415()

    except Exception:

        print(
            "\nV4.15 LOAD FAILED"
        )

        traceback.print_exc()

        return 2

    # ---------------------------------------------------------------------
    # Load canonical contract
    # ---------------------------------------------------------------------

    try:

        contract = importlib.import_module(
            CONTRACT_MODULE
        )

    except Exception:

        print(
            "\nCANONICAL CONTRACT LOAD FAILED"
        )

        traceback.print_exc()

        return 3

    inspect_contract(
        contract
    )

    # ---------------------------------------------------------------------
    # Load serialized market data
    # ---------------------------------------------------------------------

    try:

        canonical_candles = load_candles()

    except Exception:

        print(
            "\nMARKET DATA LOAD FAILED"
        )

        traceback.print_exc()

        return 4

    # ---------------------------------------------------------------------
    # IMPORTANT:
    #
    # The canonical data remains untouched.
    #
    # Create a separate in-memory v4.15 Candle representation.
    # ---------------------------------------------------------------------

    try:

        v415_candles = (
            adapt_canonical_candles_for_v415(
                canonical_candles,
                v415,
            )
        )

    except Exception:

        print(
            "\nV4.15 CANDLE ADAPTER FAILED"
        )

        traceback.print_exc()

        return 5

    # ---------------------------------------------------------------------
    # Build ATR from the v4.15-compatible candle sequence.
    #
    # The values are identical to the canonical OHLC values,
    # but this keeps the audit's v4.15 input representation consistent.
    # ---------------------------------------------------------------------

    try:

        atr = build_causal_atr(
            v415_candles,
            ATR_PERIOD,
        )

    except Exception:

        print(
            "\nATR CONSTRUCTION FAILED"
        )

        traceback.print_exc()

        return 6

    inspect_atr(
        v415_candles,
        atr,
    )

    # ---------------------------------------------------------------------
    # Equivalence
    # ---------------------------------------------------------------------

    try:

        checks, mismatches, errors = run_audit(
            canonical_candles,
            v415_candles,
            atr,
            v415,
        )

    except Exception:

        print(
            "\nEQUIVALENCE AUDIT FAILED"
        )

        traceback.print_exc()

        return 7

    # ---------------------------------------------------------------------
    # Final result
    # ---------------------------------------------------------------------

    banner(
        "PHASE 10B FINAL RESULT"
    )

    print(
        f"Checks       : {checks}"
    )

    print(
        f"Mismatches   : {mismatches}"
    )

    print(
        f"Errors       : {errors}"
    )

    if errors > 0:

        print(
            """
OVERALL RESULT:
INCONCLUSIVE — EXECUTION ERRORS

An API/data execution error occurred.

This does NOT establish a target/outcome mismatch.

Production code remains unchanged.
Market data remains unchanged.
"""
        )

        return 10

    if mismatches > 0:

        print(
            """
OVERALL RESULT:
FAIL — CANONICAL / V4.15 MISMATCH

This is an actual semantic mismatch between
the canonical target calculation and v4.15.

DO NOT modify v4.15 automatically.
"""
        )

        return 11

    print(
        """
OVERALL RESULT:
PASS — V4.15 / CANONICAL TARGET-OUTCOME EQUIVALENCE

The tested horizons and indices agree on:

    - direction
    - raw return

The audit used the actual v4.15 Candle API.

No production files were modified.
No market data was modified.
No Git history was modified.
"""
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )