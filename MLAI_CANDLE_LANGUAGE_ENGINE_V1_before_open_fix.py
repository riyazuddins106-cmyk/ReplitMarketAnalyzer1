"""
===============================================================================
MLAI CANDLE LANGUAGE ENGINE V1
===============================================================================

Purpose:
    Read the indexed MLAI Candle Language Knowledge Base and translate
    COMPLETED candles into human-readable Market Language.

Inputs:
    1. market_data.bin
    2. MLAI_CANDLE_LANGUAGE_KB_V1.bin

Important scientific rules:
    - READ ONLY
    - Does not modify market_data.bin
    - Does not modify the KB
    - Does not use future candles
    - Does not create BUY/SELL labels
    - Does not claim hidden orders
    - Does not claim exact buyer/seller counts from OHLCV volume
    - Only analyzes completed candles
    - Every interpretation is evidence-based
    - A candle observation is not automatically a prediction

===============================================================================
"""

from __future__ import annotations

import hashlib
import math
import pickle
from pathlib import Path
from statistics import median
from typing import Any, Dict, List, Optional


# =============================================================================
# CONFIGURATION
# =============================================================================

BASE_DIR = Path(__file__).resolve().parent

MARKET_DATA_FILE = BASE_DIR / "market_data.bin"
KB_FILE = BASE_DIR / "MLAI_CANDLE_LANGUAGE_KB_V1.bin"

ENGINE_VERSION = "1.0.0"


# =============================================================================
# GENERAL HELPERS
# =============================================================================

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        while True:
            block = f.read(1024 * 1024)

            if not block:
                break

            h.update(block)

    return h.hexdigest()


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        x = float(value)

        if math.isfinite(x):
            return x

    except Exception:
        pass

    return default


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def load_pickle_read_only(path: Path) -> Any:
    """
    Load an existing pickle/binary artifact.

    This function ONLY reads the file.
    """

    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path}")

    with path.open("rb") as f:
        return pickle.load(f)


# =============================================================================
# MARKET DATA VALIDATION
# =============================================================================

def validate_candle(candle: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and normalize one completed candle.

    The function does not infer anything from future candles.
    """

    required = [
        "timestamp",
        "open",
        "high",
        "low",
        "close",
    ]

    missing = [x for x in required if x not in candle]

    if missing:
        raise ValueError(
            f"Candle is missing required fields: {missing}"
        )

    o = safe_float(candle["open"])
    h = safe_float(candle["high"])
    l = safe_float(candle["low"])
    c = safe_float(candle["close"])

    if h < max(o, c):
        raise ValueError("Invalid candle: high is below open/close.")

    if l > min(o, c):
        raise ValueError("Invalid candle: low is above open/close.")

    if h < l:
        raise ValueError("Invalid candle: high is below low.")

    return {
        **candle,
        "open": o,
        "high": h,
        "low": l,
        "close": c,
    }


# =============================================================================
# CANDLE ANATOMY
# =============================================================================

def calculate_candle_anatomy(candle: Dict[str, Any]) -> Dict[str, float]:
    """
    Calculate the physical geometry of a candlestick.

    This is purely descriptive.
    """

    o = safe_float(candle["open"])
    h = safe_float(candle["high"])
    l = safe_float(candle["low"])
    c = safe_float(candle["close"])

    candle_range = max(0.0, h - l)
    body = abs(c - o)

    upper_wick = max(0.0, h - max(o, c))
    lower_wick = max(0.0, min(o, c) - l)

    if candle_range > 0:
        body_ratio = body / candle_range
        upper_ratio = upper_wick / candle_range
        lower_ratio = lower_wick / candle_range
    else:
        body_ratio = 0.0
        upper_ratio = 0.0
        lower_ratio = 0.0

    if candle_range > 0:
        close_position = (c - l) / candle_range
    else:
        close_position = 0.5

    if c > o:
        direction = "bullish"

    elif c < o:
        direction = "bearish"

    else:
        direction = "neutral"

    return {
        "range": candle_range,
        "body": body,
        "upper_wick": upper_wick,
        "lower_wick": lower_wick,
        "body_to_range": body_ratio,
        "upper_wick_to_range": upper_ratio,
        "lower_wick_to_range": lower_ratio,
        "close_position": clamp(close_position, 0.0, 1.0),
        "direction_numeric": (
            1.0 if direction == "bullish"
            else -1.0 if direction == "bearish"
            else 0.0
        ),
    }


# =============================================================================
# RELATIVE CANDLE SIZE
# =============================================================================

def classify_relative_size(
    candle_range: float,
    historical_ranges: List[float],
) -> str:

    if not historical_ranges:
        return "unknown_relative_size"

    valid = [
        x for x in historical_ranges
        if x > 0 and math.isfinite(x)
    ]

    if not valid:
        return "unknown_relative_size"

    reference = median(valid)

    if reference <= 0:
        return "unknown_relative_size"

    ratio = candle_range / reference

    if ratio < 0.50:
        return "very_small_relative_range"

    if ratio < 0.80:
        return "small_relative_range"

    if ratio < 1.25:
        return "normal_relative_range"

    if ratio < 1.75:
        return "large_relative_range"

    return "very_large_relative_range"


# =============================================================================
# KB LOOKUP
# =============================================================================

def build_kb_indexes(kb: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract indexes from the generated knowledge base.

    The engine deliberately tolerates different dictionary layouts so that
    the KB can evolve without rewriting the entire reader.
    """

    indexes = kb.get("indexes")

    if isinstance(indexes, dict):
        return indexes

    indexes = kb.get("knowledge_indexes")

    if isinstance(indexes, dict):
        return indexes

    return {}


def find_reference_concept(
    kb: Dict[str, Any],
    concept: str,
) -> Optional[Dict[str, Any]]:

    references = kb.get("references", [])

    if isinstance(references, dict):
        references = list(references.values())

    if not isinstance(references, list):
        return None

    concept_lower = concept.lower()

    for item in references:

        if not isinstance(item, dict):
            continue

        text = str(
            item.get("concept")
            or item.get("name")
            or item.get("title")
            or ""
        )

        if concept_lower in text.lower():
            return item

    return None


# =============================================================================
# BODY LANGUAGE
# =============================================================================

def body_language(
    direction: str,
    body_ratio: float,
) -> str:

    if body_ratio < 0.05:
        return (
            "The candle has almost no directional body. "
            "Open and close are very close, so the interval shows "
            "little net directional displacement."
        )

    if body_ratio < 0.20:
        if direction == "bullish":
            return (
                "The candle has a small bullish body. "
                "Price finished above the open, but the net directional "
                "movement was relatively limited."
            )

        if direction == "bearish":
            return (
                "The candle has a small bearish body. "
                "Price finished below the open, but the net directional "
                "movement was relatively limited."
            )

        return (
            "The candle has a very small body, indicating limited "
            "net directional movement."
        )

    if body_ratio < 0.45:
        return (
            f"The candle has a moderate body occupying approximately "
            f"{pct(body_ratio)} of its total range. "
            f"This represents meaningful but not dominant directional movement."
        )

    if body_ratio < 0.75:
        return (
            f"The candle has a large directional body occupying approximately "
            f"{pct(body_ratio)} of its total range. "
            f"Directional movement dominated much of the candle."
        )

    return (
        f"The candle has a very large body occupying approximately "
        f"{pct(body_ratio)} of its range. "
        f"Most of the candle's movement occurred in the direction of the close."
    )


# =============================================================================
# WICK LANGUAGE
# =============================================================================

def wick_language(
    direction: str,
    upper_wick: float,
    lower_wick: float,
    candle_range: float,
) -> List[str]:

    observations = []

    if candle_range <= 0:
        return observations

    upper_ratio = upper_wick / candle_range
    lower_ratio = lower_wick / candle_range

    # -------------------------------------------------------------------------
    # Lower wick
    # -------------------------------------------------------------------------

    if lower_ratio >= 0.45:

        observations.append(
            "The lower wick is large relative to the candle range, "
            "showing that price traded substantially below the final "
            "closing area before recovering."
        )

        if direction == "bullish":
            observations.append(
                "Because the candle closed bullish after this lower excursion, "
                "the candle provides observable evidence of lower-price rejection."
            )

        elif direction == "bearish":
            observations.append(
                "Despite the bearish close, the large lower wick shows that "
                "lower prices were not fully maintained into the close."
            )

    elif lower_ratio >= 0.25:

        observations.append(
            "The candle contains a meaningful lower wick, indicating "
            "some recovery from lower prices before the close."
        )

    # -------------------------------------------------------------------------
    # Upper wick
    # -------------------------------------------------------------------------

    if upper_ratio >= 0.45:

        observations.append(
            "The upper wick is large relative to the candle range, "
            "showing that price traded substantially above the final "
            "closing area before moving back down."
        )

        if direction == "bearish":
            observations.append(
                "Because the candle closed bearish after this upper excursion, "
                "the candle provides observable evidence of upper-price rejection."
            )

        elif direction == "bullish":
            observations.append(
                "Despite the bullish close, the large upper wick shows that "
                "higher prices were not fully maintained into the close."
            )

    elif upper_ratio >= 0.25:

        observations.append(
            "The candle contains a meaningful upper wick, indicating "
            "some retreat from higher prices before the close."
        )

    # -------------------------------------------------------------------------
    # Balanced structure
    # -------------------------------------------------------------------------

    if (
        upper_ratio >= 0.15
        and lower_ratio >= 0.15
        and abs(upper_ratio - lower_ratio) < 0.12
    ):
        observations.append(
            "The upper and lower wicks are relatively balanced, "
            "showing movement in both directions during the interval."
        )

    # -------------------------------------------------------------------------
    # Full-body candle
    # -------------------------------------------------------------------------

    if upper_wick <= candle_range * 0.03 and lower_wick <= candle_range * 0.03:
        observations.append(
            "Both wicks are minimal, so the candle is close to a full-body "
            "movement from one end of the range to the other."
        )

    return observations


# =============================================================================
# CANDLE BEHAVIOUR
# =============================================================================

def behaviour_language(
    direction: str,
    body_ratio: float,
    upper_ratio: float,
    lower_ratio: float,
) -> str:

    # Very small / indecision
    if body_ratio < 0.08:

        if upper_ratio > 0.30 and lower_ratio > 0.30:
            return (
                "The candle shows strong two-sided exploration with little "
                "net displacement. This is better described as balance or "
                "indecision than as directional control."
            )

        return (
            "The candle produced very little net displacement. "
            "Its meaning depends strongly on the surrounding sequence and location."
        )

    # Strong bullish displacement
    if direction == "bullish" and body_ratio >= 0.70:

        if upper_ratio < 0.12 and lower_ratio < 0.12:
            return (
                "The candle shows strong bullish displacement with little "
                "visible rejection on either side."
            )

        return (
            "The candle shows substantial bullish displacement, although "
            "the wick structure indicates some two-sided price exploration."
        )

    # Strong bearish displacement
    if direction == "bearish" and body_ratio >= 0.70:

        if upper_ratio < 0.12 and lower_ratio < 0.12:
            return (
                "The candle shows strong bearish displacement with little "
                "visible rejection on either side."
            )

        return (
            "The candle shows substantial bearish displacement, although "
            "the wick structure indicates some two-sided price exploration."
        )

    # Bullish lower rejection
    if direction == "bullish" and lower_ratio >= 0.35:
        return (
            "The candle combines a bullish close with meaningful lower-price "
            "rejection. This describes recovery from lower prices, but does "
            "not by itself establish a trend reversal."
        )

    # Bearish upper rejection
    if direction == "bearish" and upper_ratio >= 0.35:
        return (
            "The candle combines a bearish close with meaningful upper-price "
            "rejection. This describes retreat from higher prices, but does "
            "not by itself establish a trend reversal."
        )

    # General directional
    if direction == "bullish":
        return (
            "The candle finished above its open and therefore records "
            "net upward displacement during this interval."
        )

    if direction == "bearish":
        return (
            "The candle finished below its open and therefore records "
            "net downward displacement during this interval."
        )

    return (
        "The candle does not show meaningful net directional displacement."
    )


# =============================================================================
# VOLUME LANGUAGE
# =============================================================================

def volume_language(
    candle: Dict[str, Any],
    previous_candles: List[Dict[str, Any]],
) -> str:

    volume = safe_float(candle.get("volume", 0.0))

    if volume <= 0:
        return (
            "Volume is unavailable or zero for this candle, so no "
            "volume-based interpretation is made."
        )

    previous_volumes = [
        safe_float(x.get("volume", 0.0))
        for x in previous_candles
        if safe_float(x.get("volume", 0.0)) > 0
    ]

    if not previous_volumes:
        return (
            f"Reported volume is {volume:g}. There is not enough prior "
            "volume history here to classify it as relatively high or low."
        )

    reference = median(previous_volumes)

    if reference <= 0:
        return (
            "Volume is present, but no reliable historical volume reference "
            "is available for comparison."
        )

    ratio = volume / reference

    if ratio >= 2.0:
        classification = "very high"

    elif ratio >= 1.30:
        classification = "high"

    elif ratio <= 0.60:
        classification = "low"

    else:
        classification = "normal"

    return (
        f"Reported volume is {volume:g}, approximately {ratio:.2f} times "
        f"the recent reference level, so it is classified as {classification} "
        "relative volume. Volume alone does not reveal the exact number of "
        "buyers, sellers, institutions, or hidden orders."
    )


# =============================================================================
# SEQUENCE LANGUAGE
# =============================================================================

def sequence_language(
    candles: List[Dict[str, Any]],
) -> List[str]:

    if len(candles) < 3:
        return [
            "There are not enough completed candles to make a reliable "
            "sequence interpretation."
        ]

    recent = candles[-min(8, len(candles)):]

    closes = [
        safe_float(x["close"])
        for x in recent
    ]

    if len(closes) < 3:
        return []

    up_moves = 0
    down_moves = 0

    for i in range(1, len(closes)):
        if closes[i] > closes[i - 1]:
            up_moves += 1

        elif closes[i] < closes[i - 1]:
            down_moves += 1

    result = []

    if up_moves >= len(closes) - 2:
        result.append(
            "The recent completed sequence is predominantly moving upward."
        )

    elif down_moves >= len(closes) - 2:
        result.append(
            "The recent completed sequence is predominantly moving downward."
        )

    else:
        result.append(
            "The recent completed sequence is mixed, with movement in both directions."
        )

    # Detect recent acceleration/deceleration using absolute changes.
    movements = [
        abs(closes[i] - closes[i - 1])
        for i in range(1, len(closes))
    ]

    if len(movements) >= 4:

        first_half = movements[:len(movements) // 2]
        second_half = movements[len(movements) // 2:]

        first_avg = sum(first_half) / len(first_half)
        second_avg = sum(second_half) / len(second_half)

        if first_avg > 0:

            ratio = second_avg / first_avg

            if ratio >= 1.40:
                result.append(
                    "Recent price movement has expanded relative to the earlier "
                    "part of the sequence, indicating increasing movement intensity."
                )

            elif ratio <= 0.65:
                result.append(
                    "Recent price movement has contracted relative to the earlier "
                    "part of the sequence, indicating decreasing movement intensity."
                )

    return result


# =============================================================================
# CANDLE TRANSLATION
# =============================================================================

def translate_candle(
    candle: Dict[str, Any],
    previous_candles: List[Dict[str, Any]],
    kb: Dict[str, Any],
) -> Dict[str, Any]:

    candle = validate_candle(candle)

    anatomy = calculate_candle_anatomy(candle)

    direction_numeric = anatomy["direction_numeric"]

    if direction_numeric > 0:
        direction = "bullish"

    elif direction_numeric < 0:
        direction = "bearish"

    else:
        direction = "neutral"

    historical_ranges = [
        calculate_candle_anatomy(x)["range"]
        for x in previous_candles
        if isinstance(x, dict)
    ]

    relative_size = classify_relative_size(
        anatomy["range"],
        historical_ranges,
    )

    body_text = body_language(
        direction,
        anatomy["body_to_range"],
    )

    wick_text = wick_language(
        direction,
        anatomy["upper_wick"],
        anatomy["lower_wick"],
        anatomy["range"],
    )

    behaviour_text = behaviour_language(
        direction,
        anatomy["body_to_range"],
        anatomy["upper_wick_to_range"],
        anatomy["lower_wick_to_range"],
    )

    volume_text = volume_language(
        candle,
        previous_candles,
    )

    result = {
        "engine_version": ENGINE_VERSION,

        "timestamp": candle.get("timestamp"),
        "datetime": candle.get("datetime"),

        "direction": direction,

        "anatomy": anatomy,

        "relative_size": relative_size,

        "machine_language": {
            "direction": direction,
            "relative_size": relative_size,
            "body_ratio": round(
                anatomy["body_to_range"], 6
            ),
            "upper_wick_ratio": round(
                anatomy["upper_wick_to_range"], 6
            ),
            "lower_wick_ratio": round(
                anatomy["lower_wick_to_range"], 6
            ),
        },

        "human_language": {
            "body": body_text,
            "wicks": wick_text,
            "behaviour": behaviour_text,
            "volume": volume_text,
        },

        "sequence_context": sequence_language(
            previous_candles + [candle]
        ),

        "scientific_limits": [
            "This is an observation of completed price data.",
            "The candle does not automatically represent BUY or SELL.",
            "Wick rejection is descriptive evidence, not proof of future reversal.",
            "OHLCV data cannot reveal hidden orders or exact trader intent.",
            "Volume is not interpreted as an exact buyer-versus-seller count.",
            "Future candles are not used to interpret this candle.",
        ],
    }

    return result


# =============================================================================
# HUMAN REPORT
# =============================================================================

def print_translation(result: Dict[str, Any]) -> None:

    anatomy = result["anatomy"]
    human = result["human_language"]

    print()
    print("=" * 78)
    print("MLAI CANDLE LANGUAGE TRANSLATION")
    print("=" * 78)

    print(f"Timestamp : {result.get('datetime')}")
    print(f"Direction : {result['direction']}")
    print(f"Size      : {result['relative_size']}")

    print()
    print("CANDLE ANATOMY")
    print("-" * 78)

    print(f"Open          : {anatomy['body'] * 0 + 0:.6f}")
    print(
        f"Range         : {anatomy['range']:.6f}"
    )
    print(
        f"Body          : {anatomy['body']:.6f}"
    )
    print(
        f"Upper wick    : {anatomy['upper_wick']:.6f}"
    )
    print(
        f"Lower wick    : {anatomy['lower_wick']:.6f}"
    )
    print(
        f"Body / range  : {pct(anatomy['body_to_range'])}"
    )
    print(
        f"Upper / range : {pct(anatomy['upper_wick_to_range'])}"
    )
    print(
        f"Lower / range : {pct(anatomy['lower_wick_to_range'])}"
    )

    print()
    print("HUMAN MARKET LANGUAGE")
    print("-" * 78)

    print()
    print("BODY")
    print(human["body"])

    print()
    print("WICKS")

    if human["wicks"]:
        for text in human["wicks"]:
            print(f"• {text}")
    else:
        print("• No dominant wick behaviour detected.")

    print()
    print("BEHAVIOUR")
    print(human["behaviour"])

    print()
    print("VOLUME")
    print(human["volume"])

    print()
    print("SEQUENCE CONTEXT")

    for text in result["sequence_context"]:
        print(f"• {text}")

    print()
    print("SCIENTIFIC LIMITS")

    for text in result["scientific_limits"]:
        print(f"• {text}")

    print()
    print("=" * 78)


# =============================================================================
# MAIN
# =============================================================================

def main() -> None:

    print("=" * 78)
    print("MLAI CANDLE LANGUAGE ENGINE V1")
    print("=" * 78)

    # -------------------------------------------------------------------------
    # File checks
    # -------------------------------------------------------------------------

    print()
    print("Checking required files...")

    if not MARKET_DATA_FILE.exists():
        raise FileNotFoundError(
            f"Missing market data file:\n{MARKET_DATA_FILE}"
        )

    if not KB_FILE.exists():
        raise FileNotFoundError(
            f"Missing knowledge base:\n{KB_FILE}\n\n"
            "Run MLAI_CANDLE_LANGUAGE_KB_BUILDER_V1.py first."
        )

    # -------------------------------------------------------------------------
    # Load files
    # -------------------------------------------------------------------------

    print()
    print("Loading market data...")

    market_data = load_pickle_read_only(
        MARKET_DATA_FILE
    )

    print("Loading candle-language knowledge base...")

    kb = load_pickle_read_only(
        KB_FILE
    )

    if not isinstance(market_data, dict):
        raise TypeError(
            "market_data.bin does not contain the expected dictionary."
        )

    candles = market_data.get("candles")

    if not isinstance(candles, list):
        raise TypeError(
            "market_data.bin does not contain a candle list."
        )

    if not candles:
        raise ValueError(
            "No candles found in market_data.bin."
        )

    print()
    print(f"Market candles : {len(candles):,}")

    if isinstance(kb, dict):

        print(
            "KB version     :",
            kb.get("kb_version", "unknown")
        )

        print(
            "KB source hash :",
            kb.get("source_sha256", "not recorded")
        )

    # -------------------------------------------------------------------------
    # Integrity information
    # -------------------------------------------------------------------------

    print()
    print("READ-ONLY INTEGRITY")

    print(
        "market_data.bin SHA256:",
        sha256_file(MARKET_DATA_FILE)
    )

    print(
        "KB SHA256             :",
        sha256_file(KB_FILE)
    )

    # -------------------------------------------------------------------------
    # Analyze ONLY completed candles
    #
    # Current market_data.bin contains completed historical candles.
    # We intentionally select the last stored candle only.
    #
    # No future candle is used to interpret it.
    # -------------------------------------------------------------------------

    target_index = len(candles) - 1

    target_candle = candles[target_index]

    previous_candles = candles[
        max(0, target_index - 50):target_index
    ]

    print()
    print(
        f"Analyzing completed candle "
        f"{target_index + 1:,} of {len(candles):,}"
    )

    result = translate_candle(
        target_candle,
        previous_candles,
        kb,
    )

    # -------------------------------------------------------------------------
    # Display
    # -------------------------------------------------------------------------

    print_translation(result)

    # -------------------------------------------------------------------------
    # Completion
    # -------------------------------------------------------------------------

    print()
    print("ENGINE STATUS")
    print("-" * 78)
    print("Completed candle analyzed : YES")
    print("Future candles used       : NO")
    print("Market data modified      : NO")
    print("Knowledge base modified   : NO")
    print("BUY/SELL signal generated : NO")
    print("Hidden-order inference    : NO")
    print("Human-language translation: YES")

    print()
    print("=" * 78)
    print("MLAI CANDLE LANGUAGE ENGINE V1 COMPLETE")
    print("=" * 78)


if __name__ == "__main__":
    main()