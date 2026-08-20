"""
===============================================================================
MLAI CANDLE LANGUAGE ENGINE V2.1
===============================================================================

Purpose:
    Translate completed candles into machine language + human language and
    attach the relevant evidence from MLAI_CANDLE_LANGUAGE_KB_V1.json.

IMPORTANT:
    READ ONLY.
    No modification of market_data.bin.
    No modification of the KB.
    No future candles.
    No BUY/SELL generation.
    No hidden-order inference.
===============================================================================
"""

from __future__ import annotations

import hashlib
import json
import math
import pickle
from pathlib import Path
from statistics import median
from typing import Any, Dict, List


# =============================================================================
# CONFIG
# =============================================================================

BASE_DIR = Path(__file__).resolve().parent

MARKET_DATA_FILE = BASE_DIR / "market_data.bin"
KB_FILE = BASE_DIR / "MLAI_CANDLE_LANGUAGE_KB_V1.json"
INDEX_FILE = BASE_DIR / "MLAI_CANDLE_LANGUAGE_INDEX_V1.json"

ENGINE_VERSION = "2.1.0"


# =============================================================================
# HELPERS
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


def pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def load_pickle(path: Path) -> Any:
    with path.open("rb") as f:
        return pickle.load(f)


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


# =============================================================================
# CANDLE VALIDATION
# =============================================================================

def validate_candle(candle: Dict[str, Any]) -> Dict[str, Any]:

    required = [
        "timestamp",
        "open",
        "high",
        "low",
        "close",
    ]

    missing = [x for x in required if x not in candle]

    if missing:
        raise ValueError(f"Missing candle fields: {missing}")

    o = safe_float(candle["open"])
    h = safe_float(candle["high"])
    l = safe_float(candle["low"])
    c = safe_float(candle["close"])

    if h < max(o, c):
        raise ValueError("Invalid candle: high below open/close.")

    if l > min(o, c):
        raise ValueError("Invalid candle: low above open/close.")

    if h < l:
        raise ValueError("Invalid candle: high below low.")

    return {
        **candle,
        "open": o,
        "high": h,
        "low": l,
        "close": c,
    }


# =============================================================================
# GEOMETRY
# =============================================================================

def candle_geometry(candle: Dict[str, Any]) -> Dict[str, float]:

    o = candle["open"]
    h = candle["high"]
    l = candle["low"]
    c = candle["close"]

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
        "direction": direction,
    }


# =============================================================================
# MACHINE LANGUAGE CLASSIFICATION
# =============================================================================

def classify_body(body_ratio: float) -> str:

    if body_ratio < 0.05:
        return "doji_like"

    if body_ratio < 0.20:
        return "very_small_body"

    if body_ratio < 0.45:
        return "small_to_medium_body"

    if body_ratio < 0.75:
        return "medium_to_large_body"

    if body_ratio < 0.95:
        return "large_body"

    return "very_large_body"


def classify_wicks(
    upper_ratio: float,
    lower_ratio: float,
) -> str:

    if upper_ratio < 0.03 and lower_ratio < 0.03:
        return "full_body_low_wick"

    if upper_ratio >= 0.45 and lower_ratio >= 0.45:
        return "balanced_wick_structure"

    if upper_ratio >= 0.45:
        return "long_upper_wick"

    if lower_ratio >= 0.45:
        return "long_lower_wick"

    if upper_ratio >= 0.25:
        return "meaningful_upper_wick"

    if lower_ratio >= 0.25:
        return "meaningful_lower_wick"

    return "balanced_wick_structure"


def classify_behaviour(
    direction: str,
    body_ratio: float,
    upper_ratio: float,
    lower_ratio: float,
) -> str:

    if body_ratio < 0.08:
        if upper_ratio > 0.30 and lower_ratio > 0.30:
            return "indecision_or_balance"

        return "indecision_or_balance"

    if direction == "bullish" and body_ratio >= 0.70:

        if upper_ratio < 0.12 and lower_ratio < 0.12:
            return "strong_bullish_displacement"

        return "directional_candle_with_context_dependent_wicks"

    if direction == "bearish" and body_ratio >= 0.70:

        if upper_ratio < 0.12 and lower_ratio < 0.12:
            return "strong_bearish_displacement"

        return "directional_candle_with_context_dependent_wicks"

    if direction == "bullish" and lower_ratio >= 0.35:
        return "bullish_close_with_lower_price_rejection"

    if direction == "bearish" and upper_ratio >= 0.35:
        return "bearish_close_with_upper_price_rejection"

    return "directional_candle_with_context_dependent_wicks"


def classify_relative_size(
    candle_range: float,
    previous_candles: List[Dict[str, Any]],
) -> str:

    ranges = []

    for candle in previous_candles:

        try:
            h = safe_float(candle["high"])
            l = safe_float(candle["low"])
            r = h - l

            if r > 0:
                ranges.append(r)

        except Exception:
            continue

    if not ranges:
        return "unknown"

    reference = median(ranges)

    if reference <= 0:
        return "unknown"

    ratio = candle_range / reference

    if ratio < 0.50:
        return "very_small"

    if ratio < 0.80:
        return "small"

    if ratio < 1.25:
        return "normal"

    if ratio < 1.75:
        return "large"

    return "very_large"


# =============================================================================
# HUMAN LANGUAGE
# =============================================================================

def human_body(
    body_ratio: float,
    direction: str,
) -> str:

    if body_ratio < 0.05:
        return (
            "The candle has almost no net directional body. "
            "Open and close were very close, indicating limited net displacement."
        )

    if body_ratio < 0.20:
        return (
            f"The candle has a small {direction} body occupying approximately "
            f"{pct(body_ratio)} of the range. Net directional movement was limited."
        )

    if body_ratio < 0.45:
        return (
            f"The candle has a moderate body occupying approximately "
            f"{pct(body_ratio)} of the range. "
            "The candle recorded meaningful but not dominant directional movement."
        )

    if body_ratio < 0.75:
        return (
            f"The candle has a large body occupying approximately "
            f"{pct(body_ratio)} of the range. "
            "Directional movement dominated much of the interval."
        )

    return (
        f"The candle has a very large body occupying approximately "
        f"{pct(body_ratio)} of the range. "
        "Most of the observed movement occurred in the direction of the close."
    )


def human_wicks(
    direction: str,
    upper_ratio: float,
    lower_ratio: float,
) -> List[str]:

    result = []

    if lower_ratio >= 0.45:

        result.append(
            "The lower wick is large relative to the range, showing that "
            "price traded substantially lower before moving back toward the close."
        )

        if direction == "bullish":
            result.append(
                "Because the candle closed bullish after the lower excursion, "
                "this provides observable evidence of lower-price rejection."
            )

    elif lower_ratio >= 0.25:

        result.append(
            "The candle contains a meaningful lower wick, indicating "
            "some recovery from lower prices before the close."
        )

    if upper_ratio >= 0.45:

        result.append(
            "The upper wick is large relative to the range, showing that "
            "price traded substantially higher before moving back toward the close."
        )

        if direction == "bearish":
            result.append(
                "Because the candle closed bearish after the upper excursion, "
                "this provides observable evidence of upper-price rejection."
            )

    elif upper_ratio >= 0.25:

        result.append(
            "The candle contains a meaningful upper wick, indicating "
            "some retreat from higher prices before the close."
        )

    if upper_ratio < 0.03 and lower_ratio < 0.03:

        result.append(
            "Both wicks are minimal, so the candle is close to a full-body "
            "movement from one end of the range to the other."
        )

    return result


def human_behaviour(machine_behaviour: str) -> str:

    mapping = {

        "strong_bullish_displacement":
            "The candle shows strong bullish displacement with little visible "
            "rejection on either side.",

        "strong_bearish_displacement":
            "The candle shows strong bearish displacement with little visible "
            "rejection on either side.",

        "bullish_close_with_lower_price_rejection":
            "The candle combines a bullish close with observable lower-price "
            "rejection. This describes what happened inside the candle; it does "
            "not establish a future reversal.",

        "bearish_close_with_upper_price_rejection":
            "The candle combines a bearish close with observable upper-price "
            "rejection. This describes what happened inside the candle; it does "
            "not establish a future reversal.",

        "indecision_or_balance":
            "The candle produced limited net displacement and should be "
            "interpreted as balance or indecision rather than automatic direction.",

        "directional_candle_with_context_dependent_wicks":
            "The candle records directional displacement, but its wick structure "
            "shows that price also explored the opposite side during the interval.",
    }

    return mapping.get(
        machine_behaviour,
        "The candle records observable price movement whose meaning depends on context."
    )


# =============================================================================
# VOLUME
# =============================================================================

def human_volume(
    candle: Dict[str, Any],
    previous: List[Dict[str, Any]],
) -> str:

    volume = safe_float(candle.get("volume", 0.0))

    if volume <= 0:
        return (
            "Volume is unavailable or zero for this candle. "
            "No volume interpretation is made."
        )

    volumes = [
        safe_float(x.get("volume", 0.0))
        for x in previous
        if safe_float(x.get("volume", 0.0)) > 0
    ]

    if not volumes:
        return (
            f"Recorded volume is {volume:g}. "
            "There is insufficient historical volume for comparison."
        )

    reference = median(volumes)

    if reference <= 0:
        return "No reliable historical volume reference is available."

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
        f"Recorded volume is {volume:g}, approximately {ratio:.2f} times "
        f"the recent reference level, classified as {classification} relative "
        "volume. Volume does not reveal exact buyer/seller counts or hidden orders."
    )


# =============================================================================
# SEQUENCE
# =============================================================================

def sequence_context(candles: List[Dict[str, Any]]) -> List[str]:

    if len(candles) < 3:
        return ["Insufficient completed candles for sequence context."]

    recent = candles[-8:]

    closes = [
        safe_float(x.get("close"))
        for x in recent
    ]

    up = 0
    down = 0

    for i in range(1, len(closes)):

        if closes[i] > closes[i - 1]:
            up += 1

        elif closes[i] < closes[i - 1]:
            down += 1

    result = []

    if up >= len(closes) - 2:

        result.append(
            "The recent completed sequence is predominantly moving upward."
        )

    elif down >= len(closes) - 2:

        result.append(
            "The recent completed sequence is predominantly moving downward."
        )

    else:

        result.append(
            "The recent completed sequence is mixed, with movement in both directions."
        )

    movements = [
        abs(closes[i] - closes[i - 1])
        for i in range(1, len(closes))
    ]

    if len(movements) >= 4:

        half = len(movements) // 2

        first = movements[:half]
        second = movements[half:]

        first_avg = sum(first) / len(first)
        second_avg = sum(second) / len(second)

        if first_avg > 0:

            ratio = second_avg / first_avg

            if ratio >= 1.40:

                result.append(
                    "Recent movement has expanded relative to the earlier "
                    "part of the sequence."
                )

            elif ratio <= 0.65:

                result.append(
                    "Recent movement has contracted relative to the earlier "
                    "part of the sequence."
                )

    return result


# =============================================================================
# KB EVIDENCE MATCHING
# =============================================================================

def find_kb_evidence(
    kb: Dict[str, Any],
    machine_state: Dict[str, str],
) -> List[Dict[str, Any]]:

    rules = kb.get("rules", [])

    if not isinstance(rules, list):
        return []

    matches = []

    behaviour = machine_state["behaviour"]
    body = machine_state["body"]
    wicks = machine_state["wicks"]

    # Explicit mappings from machine states to KB concepts.
    concepts = set()

    if body in {
        "large_body",
        "very_large_body",
    }:
        concepts.add("large_body")

    if body in {
        "small_to_medium_body",
        "very_small_body",
        "doji_like",
    }:
        concepts.add("small_body")

    if wicks == "long_upper_wick":
        concepts.add("long_upper_wick")

    if wicks == "long_lower_wick":
        concepts.add("long_lower_wick")

    if wicks == "balanced_wick_structure" and body in {
        "doji_like",
        "very_small_body",
    }:
        concepts.add("two_sided_rejection")

    if behaviour == "bullish_close_with_lower_price_rejection":
        concepts.add("long_lower_wick")

    if behaviour == "bearish_close_with_upper_price_rejection":
        concepts.add("long_upper_wick")

    for rule in rules:

        if not isinstance(rule, dict):
            continue

        machine = str(rule.get("machine", ""))

        if machine in concepts:

            matches.append({
                "rule_id": rule.get("id"),
                "topic": rule.get("topic"),
                "machine_concept": machine,
                "human_evidence": rule.get("human"),
                "sources": rule.get("sources", []),
            })

    return matches


# =============================================================================
# TRANSLATION
# =============================================================================

def translate(
    candle: Dict[str, Any],
    previous: List[Dict[str, Any]],
    kb: Dict[str, Any],
) -> Dict[str, Any]:

    candle = validate_candle(candle)

    geometry = candle_geometry(candle)

    direction = geometry["direction"]

    body = classify_body(
        geometry["body_to_range"]
    )

    wicks = classify_wicks(
        geometry["upper_wick_to_range"],
        geometry["lower_wick_to_range"],
    )

    behaviour = classify_behaviour(
        direction,
        geometry["body_to_range"],
        geometry["upper_wick_to_range"],
        geometry["lower_wick_to_range"],
    )

    relative = classify_relative_size(
        geometry["range"],
        previous,
    )

    machine_state = {
        "direction": direction,
        "body": body,
        "wicks": wicks,
        "behaviour": behaviour,
        "relative_size": relative,
    }

    evidence = find_kb_evidence(
        kb,
        machine_state,
    )

    return {
        "engine_version": ENGINE_VERSION,
        "timestamp": candle.get("timestamp"),
        "datetime": candle.get("datetime"),

        "raw_ohlc": {
            "open": candle["open"],
            "high": candle["high"],
            "low": candle["low"],
            "close": candle["close"],
        },

        "machine_language": machine_state,

        "geometry": geometry,

        "human_language": {
            "body": human_body(
                geometry["body_to_range"],
                direction,
            ),
            "wicks": human_wicks(
                direction,
                geometry["upper_wick_to_range"],
                geometry["lower_wick_to_range"],
            ),
            "behaviour": human_behaviour(
                behaviour
            ),
            "volume": human_volume(
                candle,
                previous,
            ),
        },

        "sequence_context": sequence_context(
            previous + [candle]
        ),

        "knowledge_base_evidence": evidence,

        "scientific_limits": [
            "This is an observation of completed price data.",
            "The candle does not automatically represent BUY or SELL.",
            "Historical similarity does not guarantee the next move.",
            "Wick rejection is descriptive evidence, not proof of reversal.",
            "OHLCV does not reveal hidden orders or exact trader intent.",
            "Volume is not interpreted as an exact buyer-versus-seller count.",
            "Future candles are not used to interpret this candle.",
        ],
    }


# =============================================================================
# REPORT
# =============================================================================

def print_report(result: Dict[str, Any]) -> None:

    g = result["geometry"]
    m = result["machine_language"]
    h = result["human_language"]

    print()
    print("=" * 78)
    print("MLAI CANDLE LANGUAGE TRANSLATION V2.1")
    print("=" * 78)

    print()
    print("IDENTITY")
    print("-" * 78)

    print(f"Timestamp : {result['datetime']}")
    print(f"Direction : {m['direction']}")
    print(f"Body class: {m['body']}")
    print(f"Relative  : {m['relative_size']}")

    print()
    print("RAW OHLC")
    print("-" * 78)

    for key, value in result["raw_ohlc"].items():
        print(f"{key.capitalize():10}: {value:.6f}")

    print()
    print("CANDLE GEOMETRY")
    print("-" * 78)

    print(f"Range         : {g['range']:.6f}")
    print(f"Body          : {g['body']:.6f}")
    print(f"Upper wick    : {g['upper_wick']:.6f}")
    print(f"Lower wick    : {g['lower_wick']:.6f}")
    print(f"Body / range  : {pct(g['body_to_range'])}")
    print(f"Upper / range : {pct(g['upper_wick_to_range'])}")
    print(f"Lower / range : {pct(g['lower_wick_to_range'])}")

    print()
    print("MACHINE MARKET LANGUAGE")
    print("-" * 78)

    print(f"Direction : {m['direction']}")
    print(f"Body      : {m['body']}")
    print(f"Behaviour : {m['behaviour']}")
    print(f"Wicks     : {m['wicks']}")
    print(f"Relative  : {m['relative_size']}")

    print()
    print("HUMAN MARKET LANGUAGE")
    print("-" * 78)

    print()
    print("BODY")
    print(h["body"])

    print()
    print("WICKS")

    if h["wicks"]:
        for text in h["wicks"]:
            print(f"• {text}")
    else:
        print("• No dominant wick behaviour detected.")

    print()
    print("BEHAVIOUR")
    print(h["behaviour"])

    print()
    print("VOLUME")
    print(h["volume"])

    print()
    print("SEQUENCE CONTEXT")

    for text in result["sequence_context"]:
        print(f"• {text}")

    print()
    print("KNOWLEDGE BASE EVIDENCE")
    print("-" * 78)

    evidence = result["knowledge_base_evidence"]

    if not evidence:

        print("No direct KB rule matched this machine state.")

    else:

        for item in evidence:

            print(
                f"[{item['rule_id']}] "
                f"{item['machine_concept']}"
            )

            print(
                f"Topic : {item['topic']}"
            )

            print(
                f"Meaning: {item['human_evidence']}"
            )

            print(
                f"Sources: {', '.join(item['sources'])}"
            )

            print()

    print("SCIENTIFIC LIMITS")
    print("-" * 78)

    for text in result["scientific_limits"]:
        print(f"• {text}")

    print()
    print("=" * 78)
    print("ENGINE STATUS")
    print("-" * 78)

    print("Completed candle analyzed : YES")
    print("Future candles used       : NO")
    print("Market data modified      : NO")
    print("KB modified               : NO")
    print("BUY/SELL signal generated : NO")
    print("Hidden-order inference    : NO")
    print("Machine language          : YES")
    print("Human language            : YES")
    print(
        "KB evidence attached      : "
        + ("YES" if evidence else "NO")
    )

    print()
    print("=" * 78)
    print("MLAI CANDLE LANGUAGE ENGINE V2.1 COMPLETE")
    print("=" * 78)


# =============================================================================
# MAIN
# =============================================================================

def main() -> None:

    print("=" * 78)
    print("MLAI CANDLE LANGUAGE ENGINE V2.1")
    print("=" * 78)

    print()
    print("Checking required files...")

    for path in [
        MARKET_DATA_FILE,
        KB_FILE,
        INDEX_FILE,
    ]:

        if not path.exists():
            raise FileNotFoundError(
                f"Required file missing:\n{path}"
            )

    print()
    print("Loading market data...")
    market_data = load_pickle(MARKET_DATA_FILE)

    print("Loading candle-language KB...")
    kb = load_json(KB_FILE)

    print("Loading KB index...")
    index = load_json(INDEX_FILE)

    candles = market_data.get("candles")

    if not isinstance(candles, list):
        raise TypeError(
            "market_data.bin does not contain a candle list."
        )

    if not candles:
        raise ValueError(
            "No candles found."
        )

    print()
    print(f"Market candles : {len(candles):,}")
    print(f"KB schema      : {kb.get('schema_version')}")
    print(f"KB rules       : {len(kb.get('rules', []))}")
    print(f"KB sources     : {len(kb.get('sources', []))}")

    print()
    print("READ-ONLY INTEGRITY")
    print("-" * 78)

    market_hash = sha256_file(MARKET_DATA_FILE)
    kb_hash = sha256_file(KB_FILE)

    print(
        "market_data.bin SHA256:",
        market_hash
    )

    print(
        "KB JSON SHA256        :",
        kb_hash
    )

    print()
    print("KB INDEX")
    print("-" * 78)

    print(
        "Index records:",
        index.get("record_count")
    )

    print(
        "Index SHA256  :",
        index.get("sha256")
    )

    print(
        "Topics        :",
        ", ".join(index.get("topics", []))
    )

    target_index = len(candles) - 1

    target = candles[target_index]

    previous = candles[
        max(0, target_index - 50):
        target_index
    ]

    print()
    print(
        f"Analyzing completed candle "
        f"{target_index + 1:,} of {len(candles):,}"
    )

    result = translate(
        target,
        previous,
        kb,
    )

    print_report(result)


if __name__ == "__main__":
    main()