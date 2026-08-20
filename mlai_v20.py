
import os
import pickle
import math
from datetime import datetime, timezone


# ============================================================
# MLAI v2.0
# UNIFIED MLAI DECISION CONTEXT ENGINE
#
# Reads:
#   market_data.bin
#   mlai_experience.bin
#   mlai_pattern_memory.bin
#   mlai_adaptive_memory.bin
#   mlai_multitimeframe_memory.bin
#   mlai_regime_memory.bin
#   mlai_regime_transition_memory.bin
#   mlai_regime_learning_memory.bin
#
# Creates:
#   mlai_unified_memory.bin
#
# Important:
#   Existing memories are NEVER deleted or reset.
# ============================================================


VERSION = "2.0"

MARKET_FILE = "market_data.bin"
EXPERIENCE_FILE = "mlai_experience.bin"
PATTERN_FILE = "mlai_pattern_memory.bin"
ADAPTIVE_FILE = "mlai_adaptive_memory.bin"
MTF_FILE = "mlai_multitimeframe_memory.bin"
REGIME_FILE = "mlai_regime_memory.bin"
TRANSITION_FILE = "mlai_regime_transition_memory.bin"
REGIME_LEARNING_FILE = "mlai_regime_learning_memory.bin"

OUTPUT_FILE = "mlai_unified_memory.bin"
STATUS_FILE = "MLAI_PROJECT_STATUS.md"

ANALYSIS_CANDLES = 60


# ============================================================
# GENERAL HELPERS
# ============================================================

def load_pickle(path):
    if not os.path.exists(path):
        return None

    try:
        with open(path, "rb") as f:
            return pickle.load(f)
    except Exception:
        return None


def save_pickle(path, obj):
    with open(path, "wb") as f:
        pickle.dump(obj, f)


def first_value(obj, keys, default=None):
    if isinstance(obj, dict):
        for key in keys:
            if key in obj and obj[key] is not None:
                return obj[key]

    for key in keys:
        if hasattr(obj, key):
            value = getattr(obj, key)
            if value is not None:
                return value

    return default


def safe_float(value, default=0.0):
    try:
        if value is None:
            return default

        if isinstance(value, bool):
            return float(value)

        return float(value)
    except Exception:
        return default


def safe_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default


def clamp(value, low, high):
    return max(low, min(high, value))


def percentage(value, digits=1):
    return f"{safe_float(value):.{digits}f}%"


def normalize_direction(value):
    if value is None:
        return "unknown"

    text = str(value).lower().strip()

    if "bull" in text:
        return "bullish"

    if "bear" in text:
        return "bearish"

    if "neutral" in text:
        return "neutral"

    if "mixed" in text:
        return "mixed"

    return text


def normalize_structure(value):
    if value is None:
        return "unknown"

    text = str(value).lower().strip()

    if "bull" in text:
        return "bullish_structure"

    if "bear" in text:
        return "bearish_structure"

    if "range" in text:
        return "range_structure"

    if "mixed" in text:
        return "mixed_structure"

    return text


# ============================================================
# CANDLE EXTRACTION
# ============================================================

def extract_candles(memory):
    """
    Supports common structures:
        {
            "candles": [...]
        }

    or:
        {
            "data": [...]
        }

    or:
        [...]
    """

    if isinstance(memory, list):
        candles = memory

    elif isinstance(memory, dict):
        candles = None

        for key in (
            "candles",
            "data",
            "rows",
            "records",
            "market_data",
            "ohlc",
        ):
            if key in memory and isinstance(memory[key], list):
                candles = memory[key]
                break

        if candles is None:
            candles = []

    else:
        candles = first_value(
            memory,
            ["candles", "data", "rows", "records"],
            []
        )

    if not isinstance(candles, list):
        return []

    return candles


def candle_value(candle, names, default=0.0):
    if isinstance(candle, dict):
        for name in names:
            if name in candle:
                return safe_float(candle[name], default)

    for name in names:
        if hasattr(candle, name):
            return safe_float(getattr(candle, name), default)

    return default


def normalize_candle(candle):
    open_price = candle_value(
        candle,
        ["open", "Open", "o"],
        0.0
    )

    high_price = candle_value(
        candle,
        ["high", "High", "h"],
        open_price
    )

    low_price = candle_value(
        candle,
        ["low", "Low", "l"],
        open_price
    )

    close_price = candle_value(
        candle,
        ["close", "Close", "c"],
        open_price
    )

    volume = candle_value(
        candle,
        ["volume", "Volume", "v"],
        0.0
    )

    return {
        "open": open_price,
        "high": high_price,
        "low": low_price,
        "close": close_price,
        "volume": volume,
    }


# ============================================================
# BASIC MARKET ANALYSIS
# ============================================================

def candle_direction(candle):
    o = candle["open"]
    c = candle["close"]

    if c > o:
        return "bullish"

    if c < o:
        return "bearish"

    return "neutral"


def analyze_candles(candles):
    if not candles:
        raise ValueError("No usable candles found in market_data.bin")

    normalized = [
        normalize_candle(c)
        for c in candles
    ]

    latest = normalized[-ANALYSIS_CANDLES:]

    bullish = 0
    bearish = 0
    neutral = 0

    for candle in latest:
        direction = candle_direction(candle)

        if direction == "bullish":
            bullish += 1
        elif direction == "bearish":
            bearish += 1
        else:
            neutral += 1

    first_close = latest[0]["close"]
    latest_close = latest[-1]["close"]

    net_movement = latest_close - first_close

    if first_close != 0:
        net_change = (
            net_movement / first_close
        ) * 100
    else:
        net_change = 0.0

    if bullish > bearish:
        direction = "bullish"
    elif bearish > bullish:
        direction = "bearish"
    else:
        direction = "mixed"

    # --------------------------------------------------------
    # Simple swing structure
    # --------------------------------------------------------

    swing_highs = []
    swing_lows = []

    for i in range(1, len(latest) - 1):

        previous = latest[i - 1]
        current = latest[i]
        following = latest[i + 1]

        if (
            current["high"] >= previous["high"]
            and current["high"] >= following["high"]
        ):
            swing_highs.append(current["high"])

        if (
            current["low"] <= previous["low"]
            and current["low"] <= following["low"]
        ):
            swing_lows.append(current["low"])

    higher_highs = 0
    lower_highs = 0

    for i in range(1, len(swing_highs)):
        if swing_highs[i] > swing_highs[i - 1]:
            higher_highs += 1
        elif swing_highs[i] < swing_highs[i - 1]:
            lower_highs += 1

    higher_lows = 0
    lower_lows = 0

    for i in range(1, len(swing_lows)):
        if swing_lows[i] > swing_lows[i - 1]:
            higher_lows += 1
        elif swing_lows[i] < swing_lows[i - 1]:
            lower_lows += 1

    bullish_structure_score = (
        higher_highs + higher_lows
    )

    bearish_structure_score = (
        lower_highs + lower_lows
    )

    if bullish_structure_score > bearish_structure_score:
        structure = "bullish_structure"
    elif bearish_structure_score > bullish_structure_score:
        structure = "bearish_structure"
    else:
        structure = "mixed_structure"

    # --------------------------------------------------------
    # Momentum
    # --------------------------------------------------------

    half = max(5, len(latest) // 2)

    first_half = latest[:half]
    second_half = latest[half:]

    def average_body(data):
        if not data:
            return 0.0

        return sum(
            abs(c["close"] - c["open"])
            for c in data
        ) / len(data)

    def average_range(data):
        if not data:
            return 0.0

        return sum(
            c["high"] - c["low"]
            for c in data
        ) / len(data)

    body_first = average_body(first_half)
    body_second = average_body(second_half)

    range_first = average_range(first_half)
    range_second = average_range(second_half)

    if body_second > body_first * 1.10:
        momentum = "increasing"
    elif body_second < body_first * 0.90:
        momentum = "decreasing"
    else:
        momentum = "stable"

    if range_second > range_first * 1.10:
        volatility = "expanding"
    elif range_second < range_first * 0.90:
        volatility = "contracting"
    else:
        volatility = "stable"

    # --------------------------------------------------------
    # Rejection
    # --------------------------------------------------------

    upper_rejection = 0
    lower_rejection = 0

    for candle in latest:

        body_high = max(
            candle["open"],
            candle["close"]
        )

        body_low = min(
            candle["open"],
            candle["close"]
        )

        upper_wick = candle["high"] - body_high
        lower_wick = body_low - candle["low"]

        if upper_wick > abs(
            candle["close"] - candle["open"]
        ):
            upper_rejection += 1

        if lower_wick > abs(
            candle["close"] - candle["open"]
        ):
            lower_rejection += 1

    if lower_rejection > upper_rejection:
        rejection = "lower_rejection_dominant"
    elif upper_rejection > lower_rejection:
        rejection = "upper_rejection_dominant"
    else:
        rejection = "balanced_rejection"

    return {
        "candles": len(latest),
        "bullish_candles": bullish,
        "bearish_candles": bearish,
        "neutral_candles": neutral,
        "direction": direction,
        "first_close": first_close,
        "latest_close": latest_close,
        "net_movement": net_movement,
        "net_change_percent": net_change,
        "swing_highs": len(swing_highs),
        "swing_lows": len(swing_lows),
        "higher_highs": higher_highs,
        "lower_highs": lower_highs,
        "higher_lows": higher_lows,
        "lower_lows": lower_lows,
        "structure": structure,
        "momentum": momentum,
        "volatility": volatility,
        "upper_rejection": upper_rejection,
        "lower_rejection": lower_rejection,
        "rejection": rejection,
        "latest_swing_high": (
            swing_highs[-1]
            if swing_highs
            else latest[-1]["high"]
        ),
        "latest_swing_low": (
            swing_lows[-1]
            if swing_lows
            else latest[-1]["low"]
        ),
    }


# ============================================================
# MEMORY EXTRACTION
# ============================================================

def memory_dict(memory):
    if isinstance(memory, dict):
        return memory

    if hasattr(memory, "__dict__"):
        return vars(memory)

    return {}


def extract_experience_info(memory):
    if not memory:
        return {
            "observations": 0,
            "resolved": 0,
            "pending": 0,
            "confirmed": 0,
            "not_confirmed": 0,
            "neutral": 0,
            "accuracy": 0.0,
        }

    data = memory_dict(memory)

    observations = first_value(
        data,
        [
            "observations",
            "total_observations",
            "observation_count",
        ],
        0
    )

    if isinstance(observations, list):
        observation_list = observations
        observation_count = len(observation_list)
    else:
        observation_list = data.get(
            "memory",
            data.get("experiences", [])
        )

        if not isinstance(observation_list, list):
            observation_list = []

        observation_count = safe_int(
            observations,
            len(observation_list)
        )

    resolved = 0
    pending = 0
    confirmed = 0
    not_confirmed = 0
    neutral = 0

    # Search recursively through common outcome structures.
    def inspect(value):
        nonlocal resolved
        nonlocal pending
        nonlocal confirmed
        nonlocal not_confirmed
        nonlocal neutral

        if isinstance(value, dict):

            for key, item in value.items():

                key_lower = str(key).lower()

                if key_lower in (
                    "status",
                    "outcome",
                    "result",
                    "classification",
                ):
                    text = str(item).lower()

                    if "pending" in text:
                        pending += 1
                    elif "confirm" in text:
                        resolved += 1
                        confirmed += 1
                    elif (
                        "not_confirmed" in text
                        or "not confirmed" in text
                        or "failed" in text
                    ):
                        resolved += 1
                        not_confirmed += 1
                    elif "neutral" in text:
                        resolved += 1
                        neutral += 1

                elif isinstance(item, (dict, list)):
                    inspect(item)

        elif isinstance(value, list):
            for item in value:
                inspect(item)

    inspect(memory)

    explicit_resolved = first_value(
        data,
        [
            "resolved_windows",
            "resolved_outcomes",
            "resolved",
        ],
        None
    )

    if explicit_resolved is not None:
        resolved = max(
            resolved,
            safe_int(explicit_resolved)
        )

    explicit_pending = first_value(
        data,
        [
            "pending_windows",
            "pending_outcomes",
            "pending",
        ],
        None
    )

    if explicit_pending is not None:
        pending = max(
            pending,
            safe_int(explicit_pending)
        )

    confirmed = max(
        confirmed,
        safe_int(
            first_value(
                data,
                ["confirmed", "confirmed_outcomes"],
                0
            )
        )
    )

    not_confirmed = max(
        not_confirmed,
        safe_int(
            first_value(
                data,
                [
                    "not_confirmed",
                    "not_confirmed_outcomes",
                ],
                0
            )
        )
    )

    neutral = max(
        neutral,
        safe_int(
            first_value(
                data,
                ["neutral", "neutral_outcomes"],
                0
            )
        )
    )

    resolved = max(
        resolved,
        confirmed + not_confirmed + neutral
    )

    total_resolved_results = (
        confirmed
        + not_confirmed
    )

    if total_resolved_results > 0:
        accuracy = (
            confirmed
            / total_resolved_results
        ) * 100
    else:
        accuracy = 0.0

    return {
        "observations": observation_count,
        "resolved": resolved,
        "pending": pending,
        "confirmed": confirmed,
        "not_confirmed": not_confirmed,
        "neutral": neutral,
        "accuracy": accuracy,
    }


def extract_pattern_info(memory):
    if not memory:
        return {
            "patterns": 0,
            "best_patterns": [],
        }

    data = memory_dict(memory)

    patterns = first_value(
        data,
        [
            "patterns",
            "direction_patterns",
            "pattern_memory",
        ],
        {}
    )

    if isinstance(patterns, dict):
        count = len(patterns)
    elif isinstance(patterns, list):
        count = len(patterns)
    else:
        count = safe_int(patterns, 0)

    return {
        "patterns": count,
        "best_patterns": [],
    }


def extract_adaptive_info(memory):
    if not memory:
        return {
            "bullish_weight": 0.0,
            "bearish_weight": 0.0,
            "neutral_weight": 0.0,
            "confidence": 0.0,
        }

    data = memory_dict(memory)

    bullish = safe_float(
        first_value(
            data,
            [
                "bullish_pattern_weight",
                "bullish_weight",
                "bullish_score",
            ],
            0
        )
    )

    bearish = safe_float(
        first_value(
            data,
            [
                "bearish_pattern_weight",
                "bearish_weight",
                "bearish_score",
            ],
            0
        )
    )

    neutral = safe_float(
        first_value(
            data,
            [
                "neutral_pattern_weight",
                "neutral_weight",
                "neutral_score",
            ],
            0
        )
    )

    confidence = safe_float(
        first_value(
            data,
            [
                "confidence",
                "evidence_confidence",
            ],
            0
        )
    )

    return {
        "bullish_weight": bullish,
        "bearish_weight": bearish,
        "neutral_weight": neutral,
        "confidence": confidence,
    }


def extract_mtf_info(memory):
    if not memory:
        return {
            "direction": "unknown",
            "alignment": 0.0,
            "confidence": 0.0,
        }

    data = memory_dict(memory)

    direction = normalize_direction(
        first_value(
            data,
            [
                "integrated_direction",
                "direction",
            ],
            "unknown"
        )
    )

    alignment = safe_float(
        first_value(
            data,
            [
                "alignment_score",
                "alignment",
            ],
            0
        )
    )

    confidence = safe_float(
        first_value(
            data,
            [
                "evidence_confidence",
                "confidence",
            ],
            0
        )
    )

    return {
        "direction": direction,
        "alignment": alignment,
        "confidence": confidence,
    }


def extract_regime_info(memory):
    if not memory:
        return {
            "regime": "unknown",
            "strength": "unknown",
            "confidence": 0.0,
            "direction": "unknown",
        }

    data = memory_dict(memory)

    regime = first_value(
        data,
        [
            "regime",
            "current_regime",
            "market_regime",
        ],
        "unknown"
    )

    strength = first_value(
        data,
        [
            "regime_strength",
            "strength",
        ],
        "unknown"
    )

    confidence = safe_float(
        first_value(
            data,
            [
                "regime_confidence",
                "confidence",
            ],
            0
        )
    )

    direction = normalize_direction(
        first_value(
            data,
            [
                "direction",
                "integrated_direction",
            ],
            "unknown"
        )
    )

    return {
        "regime": str(regime),
        "strength": str(strength),
        "confidence": confidence,
        "direction": direction,
    }


def extract_transition_info(memory):
    if not memory:
        return {
            "transition": False,
            "previous": None,
            "current": None,
            "stability": 0.0,
            "observations": 0,
        }

    data = memory_dict(memory)

    transition = first_value(
        data,
        [
            "transition_detected",
            "transition",
        ],
        False
    )

    previous = first_value(
        data,
        [
            "previous_regime",
            "previous",
        ],
        None
    )

    current = first_value(
        data,
        [
            "current_regime",
            "current",
        ],
        None
    )

    stability = safe_float(
        first_value(
            data,
            [
                "recent_stability",
                "stability",
                "stability_percent",
            ],
            0
        )
    )

    observations = safe_int(
        first_value(
            data,
            [
                "stored_regime_states",
                "observations",
                "total_observations",
            ],
            0
        )
    )

    return {
        "transition": bool(transition),
        "previous": previous,
        "current": current,
        "stability": stability,
        "observations": observations,
    }


# ============================================================
# UNIFIED EVIDENCE ENGINE
# ============================================================

def evidence_engine(
    market,
    experience,
    adaptive,
    mtf,
    regime,
    transition,
):
    bullish = 0.0
    bearish = 0.0
    neutral = 0.0

    supporting = []
    conflicting = []
    limiting = []

    # --------------------------------------------------------
    # 1. Direct candle evidence
    # --------------------------------------------------------

    candle_total = (
        market["bullish_candles"]
        + market["bearish_candles"]
    )

    if candle_total > 0:

        candle_bull_ratio = (
            market["bullish_candles"]
            / candle_total
        )

        candle_bear_ratio = (
            market["bearish_candles"]
            / candle_total
        )

        if candle_bull_ratio > 0.5:
            bullish += 2.0
            supporting.append(
                "Bullish candle participation exceeds bearish participation."
            )

        elif candle_bear_ratio > 0.5:
            bearish += 2.0
            supporting.append(
                "Bearish candle participation exceeds bullish participation."
            )

        else:
            neutral += 1.0
            limiting.append(
                "Candle participation is relatively balanced."
            )

    # --------------------------------------------------------
    # 2. Price movement
    # --------------------------------------------------------

    if market["net_change_percent"] > 0:
        bullish += 2.0
        supporting.append(
            f"Price moved upward by {market['net_change_percent']:.3f}%."
        )

    elif market["net_change_percent"] < 0:
        bearish += 2.0
        supporting.append(
            f"Price moved downward by {abs(market['net_change_percent']):.3f}%."
        )

    else:
        neutral += 1.0

    # --------------------------------------------------------
    # 3. Structure
    # --------------------------------------------------------

    if market["structure"] == "bullish_structure":
        bullish += 2.5
        supporting.append(
            "Recent swing structure favours higher-high and higher-low behaviour."
        )

    elif market["structure"] == "bearish_structure":
        bearish += 2.5
        supporting.append(
            "Recent swing structure favours lower-high and lower-low behaviour."
        )

    else:
        neutral += 1.5
        limiting.append(
            "Current swing structure is mixed."
        )

    # --------------------------------------------------------
    # 4. Rejection
    # --------------------------------------------------------

    if market["rejection"] == "lower_rejection_dominant":

        if market["direction"] == "bullish":
            bullish += 1.5
            supporting.append(
                "Lower-price rejection is dominant inside a bullish context."
            )
        else:
            conflicting.append(
                "Lower-price rejection is present without bullish candle dominance."
            )

    elif market["rejection"] == "upper_rejection_dominant":

        if market["direction"] == "bearish":
            bearish += 1.5
            supporting.append(
                "Upper-price rejection is dominant inside a bearish context."
            )
        else:
            conflicting.append(
                "Upper-price rejection is present without bearish candle dominance."
            )

    # --------------------------------------------------------
    # 5. Momentum
    # --------------------------------------------------------

    if market["momentum"] == "increasing":

        if market["direction"] == "bullish":
            bullish += 1.0
        elif market["direction"] == "bearish":
            bearish += 1.0
        else:
            neutral += 0.5

    elif market["momentum"] == "decreasing":

        limiting.append(
            "Directional momentum is decreasing."
        )

    # --------------------------------------------------------
    # 6. Multi-timeframe
    # --------------------------------------------------------

    mtf_direction = mtf["direction"]

    if mtf_direction == "bullish":
        bullish += 2.5
        supporting.append(
            "Multi-timeframe context currently favours bullish direction."
        )

    elif mtf_direction == "bearish":
        bearish += 2.5
        supporting.append(
            "Multi-timeframe context currently favours bearish direction."
        )

    elif mtf_direction == "mixed":
        neutral += 1.5
        limiting.append(
            "Multi-timeframe direction is mixed."
        )

    # --------------------------------------------------------
    # 7. Regime
    # --------------------------------------------------------

    regime_direction = regime["direction"]

    if regime_direction == "bullish":
        bullish += 2.0
        supporting.append(
            "Current regime has a bullish directional character."
        )

    elif regime_direction == "bearish":
        bearish += 2.0
        supporting.append(
            "Current regime has a bearish directional character."
        )

    else:
        regime_text = regime["regime"].lower()

        if "bullish" in regime_text:
            bullish += 1.5
            supporting.append(
                "Current market regime is classified as bullish."
            )

        elif "bearish" in regime_text:
            bearish += 1.5
            supporting.append(
                "Current market regime is classified as bearish."
            )

    # --------------------------------------------------------
    # 8. Adaptive historical pattern evidence
    # --------------------------------------------------------

    adaptive_total = (
        adaptive["bullish_weight"]
        + adaptive["bearish_weight"]
        + adaptive["neutral_weight"]
    )

    if adaptive_total > 0:

        # Normalize weights regardless of whether the stored
        # memory uses percentages or arbitrary scores.
        bullish_ratio = (
            adaptive["bullish_weight"]
            / adaptive_total
        )

        bearish_ratio = (
            adaptive["bearish_weight"]
            / adaptive_total
        )

        neutral_ratio = (
            adaptive["neutral_weight"]
            / adaptive_total
        )

        # Historical pattern evidence receives lower weight
        # than direct/current evidence.
        bullish += bullish_ratio * 1.5
        bearish += bearish_ratio * 1.5
        neutral += neutral_ratio * 1.0

        if bullish_ratio > bearish_ratio:
            supporting.append(
                "Adaptive historical pattern memory has a bullish-weighted distribution."
            )

        elif bearish_ratio > bullish_ratio:
            conflicting.append(
                "Adaptive historical pattern memory has a bearish-weighted distribution."
            )

    else:
        limiting.append(
            "No usable adaptive historical pattern weighting is available."
        )

    # --------------------------------------------------------
    # 9. Resolved experience
    # --------------------------------------------------------

    resolved = experience["resolved"]

    if resolved > 0:

        experience_accuracy = experience["accuracy"]

        # Experience influence grows gradually.
        reliability = clamp(
            resolved / 20.0,
            0.0,
            1.0
        )

        if experience_accuracy >= 55.0:
            bullish += reliability * 2.0

        elif experience_accuracy <= 45.0:
            bearish += reliability * 2.0

        else:
            neutral += reliability * 1.5

    else:
        limiting.append(
            "No resolved personal experience is available yet; pending observations receive zero learning weight."
        )

    # --------------------------------------------------------
    # 10. Regime transition
    # --------------------------------------------------------

    if transition["transition"]:

        neutral += 2.0

        conflicting.append(
            "A regime transition has been detected, increasing environmental uncertainty."
        )

    # --------------------------------------------------------
    # Final direction
    # --------------------------------------------------------

    scores = {
        "bullish": bullish,
        "bearish": bearish,
        "neutral": neutral,
    }

    sorted_scores = sorted(
        scores.items(),
        key=lambda item: item[1],
        reverse=True
    )

    first_direction, first_score = sorted_scores[0]
    second_direction, second_score = sorted_scores[1]

    total_score = sum(scores.values())

    if total_score <= 0:
        direction = "neutral"
        confidence = 0.0

    else:

        direction = first_direction

        # Confidence is based on:
        # 1. dominance
        # 2. agreement
        # 3. unresolved/conflicting evidence
        dominance = (
            first_score / total_score
        )

        separation = (
            first_score - second_score
        ) / max(first_score, 1.0)

        confidence = (
            dominance * 70.0
            + separation * 30.0
        )

        if conflicting:
            confidence -= min(
                len(conflicting) * 2.0,
                15.0
            )

        if limiting:
            confidence -= min(
                len(limiting) * 1.0,
                8.0
            )

        confidence = clamp(
            confidence,
            0.0,
            100.0
        )

    if confidence >= 75:
        confidence_level = "high"
    elif confidence >= 55:
        confidence_level = "moderate"
    elif confidence >= 35:
        confidence_level = "low"
    else:
        confidence_level = "very_low"

    return {
        "bullish_score": bullish,
        "bearish_score": bearish,
        "neutral_score": neutral,
        "direction": direction,
        "confidence": confidence,
        "confidence_level": confidence_level,
        "supporting": supporting,
        "conflicting": conflicting,
        "limiting": limiting,
    }


# ============================================================
# MARKET STATE
# ============================================================

def determine_market_state(
    market,
    regime,
    mtf,
    transition,
    evidence,
):
    direction = evidence["direction"]
    regime_name = str(
        regime["regime"]
    ).lower()

    if transition["transition"]:
        return "transitioning_market_environment"

    if "range" in regime_name:
        return "range_environment"

    if direction == "bullish":
        if market["structure"] == "bullish_structure":
            return "bullish_structural_environment"

        return "bullish_market_environment"

    if direction == "bearish":
        if market["structure"] == "bearish_structure":
            return "bearish_structural_environment"

        return "bearish_market_environment"

    return "mixed_market_environment"


# ============================================================
# PROJECT STATUS
# ============================================================

def update_status(
    market,
    experience,
    adaptive,
    mtf,
    regime,
    transition,
    evidence,
    loaded_files,
):
    timestamp = datetime.now(
        timezone.utc
    ).isoformat()

    status = f"""# MLAI Project Status

## Current Version

**MLAI v2.0 — Unified Decision Context Engine**

Updated: `{timestamp}`

---

## v2.0 Purpose

MLAI v2.0 combines the evidence layers developed through v1.0-v1.9 into one unified market context engine.

The engine does not treat one candle, pattern, timeframe, regime, or historical match as an automatic prediction.

---

## Current Market

- Candles analysed: {market["candles"]}
- First close: {market["first_close"]:.4f}
- Latest close: {market["latest_close"]:.4f}
- Net movement: {market["net_movement"]:.4f}
- Net change: {market["net_change_percent"]:.3f}%
- Direction: {market["direction"]}
- Structure: {market["structure"]}
- Momentum: {market["momentum"]}
- Volatility: {market["volatility"]}
- Rejection: {market["rejection"]}

---

## Unified Interpretation

- Integrated direction: **{evidence["direction"]}**
- Evidence confidence: **{evidence["confidence"]:.1f}%**
- Confidence level: **{evidence["confidence_level"]}**
- Market state: **{determine_market_state(market, regime, mtf, transition, evidence)}**

### Evidence Scores

- Bullish: {evidence["bullish_score"]:.3f}
- Bearish: {evidence["bearish_score"]:.3f}
- Neutral: {evidence["neutral_score"]:.3f}

---

## Experience Memory

- Observations: {experience["observations"]}
- Resolved windows: {experience["resolved"]}
- Pending windows: {experience["pending"]}
- Confirmed: {experience["confirmed"]}
- Not confirmed: {experience["not_confirmed"]}
- Neutral: {experience["neutral"]}
- Experience accuracy: {experience["accuracy"]:.1f}%

Pending observations are excluded from learned experience scoring.

---

## Adaptive Historical Memory

- Bullish weight: {adaptive["bullish_weight"]:.3f}
- Bearish weight: {adaptive["bearish_weight"]:.3f}
- Neutral weight: {adaptive["neutral_weight"]:.3f}
- Historical confidence: {adaptive["confidence"]:.1f}%

---

## Multi-Timeframe Context

- Integrated direction: {mtf["direction"]}
- Alignment: {mtf["alignment"]:.1f}%
- Evidence confidence: {mtf["confidence"]:.1f}%

---

## Regime

- Current regime: {regime["regime"]}
- Strength: {regime["strength"]}
- Direction: {regime["direction"]}
- Confidence: {regime["confidence"]:.1f}%

---

## Regime Transition

- Transition detected: {transition["transition"]}
- Previous regime: {transition["previous"]}
- Current regime: {transition["current"]}
- Stability: {transition["stability"]:.1f}%
- Stored observations: {transition["observations"]}

---

## Memory Files

"""

    for name, loaded in loaded_files.items():
        status += (
            f"- `{name}`: "
            f"{'loaded' if loaded else 'not available'}\n"
        )

    status += """

---

## v2.0 Principles

1. Direct market observation has priority over historical pattern memory.
2. Multi-timeframe evidence provides context rather than certainty.
3. Regime information describes the environment.
4. Historical patterns provide contextual evidence.
5. Resolved experience is separate from unresolved observations.
6. Pending observations receive zero learning influence.
7. Conflicting evidence is preserved.
8. Confidence measures evidence agreement, not future certainty.
9. No single module determines the final interpretation.
10. v2.0 does not create an automatic trading signal.

---

## Next Development Direction

The next MLAI stage can use the unified state to develop stronger:

- outcome attribution
- evidence weighting
- historical validation
- pattern-to-regime relationships
- experience-based adaptation
- walk-forward evaluation
- calibration of confidence

"""


    with open(
        STATUS_FILE,
        "w",
        encoding="utf-8"
    ) as f:
        f.write(status)


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("MLAI v2.0 - LOADING MARKET MEMORY")
    print("=" * 70)

    print(f"File: {MARKET_FILE}")
    print()

    market_memory = load_pickle(
        MARKET_FILE
    )

    if market_memory is None:
        print(
            "ERROR: market_data.bin could not be loaded."
        )
        print(
            "Make sure market_data.bin exists in the current folder."
        )
        return

    print(
        "PASS: market_data.bin loaded as MLAI memory object."
    )

    # --------------------------------------------------------
    # Metadata
    # --------------------------------------------------------

    metadata = memory_dict(
        market_memory
    )

    metadata_container = first_value(
        metadata,
        [
            "metadata",
            "memory_metadata",
            "info",
        ],
        {}
    )

    if not isinstance(
        metadata_container,
        dict
    ):
        metadata_container = {}

    version = first_value(
        metadata_container,
        [
            "mlai_version",
            "version",
        ],
        first_value(
            metadata,
            [
                "mlai_version",
                "version",
            ],
            "unknown"
        )
    )

    created_at = first_value(
        metadata_container,
        [
            "created_at",
            "created",
            "timestamp",
        ],
        first_value(
            metadata,
            [
                "created_at",
                "created",
                "timestamp",
            ],
            "unknown"
        )
    )

    source = first_value(
        metadata_container,
        [
            "source",
            "provider",
        ],
        first_value(
            metadata,
            [
                "source",
                "provider",
            ],
            "unknown"
        )
    )

    print()
    print("MEMORY METADATA")
    print("-" * 70)
    print(f"MLAI version : {version}")
    print(f"Created at   : {created_at}")
    print(f"Source       : {source}")

    # --------------------------------------------------------
    # Candles
    # --------------------------------------------------------

    candles = extract_candles(
        market_memory
    )

    print()
    print(
        f"Found {len(candles)} stored candles."
    )

    if len(candles) < ANALYSIS_CANDLES:
        print(
            f"ERROR: At least {ANALYSIS_CANDLES} "
            "candles are required."
        )
        return

    print()
    print(
        f"PASS: Using latest {ANALYSIS_CANDLES} candles."
    )

    print()
    print(
        f"Analysing latest {ANALYSIS_CANDLES} candles..."
    )

    market = analyze_candles(
        candles
    )

    # --------------------------------------------------------
    # Load all previous memories
    # --------------------------------------------------------

    print()
    print(
        "PASS: Loading MLAI experience memory..."
    )

    experience_memory = load_pickle(
        EXPERIENCE_FILE
    )

    print(
        "PASS: Loading MLAI pattern memory..."
    )

    pattern_memory = load_pickle(
        PATTERN_FILE
    )

    print(
        "PASS: Loading adaptive learning memory..."
    )

    adaptive_memory = load_pickle(
        ADAPTIVE_FILE
    )

    print(
        "PASS: Loading multi-timeframe memory..."
    )

    mtf_memory = load_pickle(
        MTF_FILE
    )

    print(
        "PASS: Loading regime memory..."
    )

    regime_memory = load_pickle(
        REGIME_FILE
    )

    print(
        "PASS: Loading regime transition memory..."
    )

    transition_memory = load_pickle(
        TRANSITION_FILE
    )

    print(
        "PASS: Loading regime learning memory..."
    )

    regime_learning_memory = load_pickle(
        REGIME_LEARNING_FILE
    )

    # --------------------------------------------------------
    # Extract information
    # --------------------------------------------------------

    experience = extract_experience_info(
        experience_memory
    )

    pattern = extract_pattern_info(
        pattern_memory
    )

    adaptive = extract_adaptive_info(
        adaptive_memory
    )

    mtf = extract_mtf_info(
        mtf_memory
    )

    regime = extract_regime_info(
        regime_memory
    )

    # If regime memory doesn't expose useful data,
    # attempt regime-learning memory as fallback.
    if (
        regime["regime"] == "unknown"
        and regime_learning_memory is not None
    ):
        regime = extract_regime_info(
            regime_learning_memory
        )

    transition = extract_transition_info(
        transition_memory
    )

    # --------------------------------------------------------
    # If MTF memory is missing, use direct market context.
    # --------------------------------------------------------

    if mtf["direction"] == "unknown":

        mtf = {
            "direction": market["direction"],
            "alignment": 33.3,
            "confidence": 0.0,
        }

    # --------------------------------------------------------
    # Unified evidence
    # --------------------------------------------------------

    print()
    print(
        "PASS: Fusing all available MLAI evidence layers..."
    )

    evidence = evidence_engine(
        market,
        experience,
        adaptive,
        mtf,
        regime,
        transition,
    )

    market_state = determine_market_state(
        market,
        regime,
        mtf,
        transition,
        evidence,
    )

    # --------------------------------------------------------
    # Create unified memory
    # --------------------------------------------------------

    unified_memory = {
        "mlai_version": VERSION,
        "engine": "Unified Decision Context Engine",
        "created_at": datetime.now(
            timezone.utc
        ).isoformat(),

        "market": market,

        "experience": experience,

        "pattern": pattern,

        "adaptive": adaptive,

        "multi_timeframe": mtf,

        "regime": regime,

        "transition": transition,

        "evidence": evidence,

        "market_state": market_state,

        "principles": [
            "Direct observation has priority over historical context.",
            "Multiple evidence layers are combined.",
            "Pending experience is excluded from learned scoring.",
            "Historical patterns are contextual evidence.",
            "Regime information describes the current environment.",
            "Conflicting evidence is preserved.",
            "Confidence represents evidence agreement rather than certainty.",
            "No single candle or pattern determines the result.",
            "The engine does not guarantee future market behaviour.",
            "The engine does not create an automatic trading signal.",
        ],
    }

    save_pickle(
        OUTPUT_FILE,
        unified_memory
    )

    print()
    print(
        f"PASS: {OUTPUT_FILE} saved."
    )

    # ========================================================
    # DISPLAY
    # ========================================================

    print()
    print("=" * 70)
    print(
        "MLAI v2.0 UNIFIED DECISION CONTEXT ENGINE"
    )
    print("=" * 70)

    print()
    print("UNIFIED MARKET STATE")
    print("-" * 70)

    print(
        f"Market state          : {market_state}"
    )

    print(
        f"Integrated direction   : {evidence['direction']}"
    )

    print(
        f"Evidence confidence    : {evidence['confidence']:.1f}%"
    )

    print(
        f"Confidence level       : {evidence['confidence_level']}"
    )

    print()
    print("CURRENT MARKET")
    print("-" * 70)

    print(
        f"Candles analysed      : {market['candles']}"
    )

    print(
        f"First close            : {market['first_close']:.4f}"
    )

    print(
        f"Latest close           : {market['latest_close']:.4f}"
    )

    print(
        f"Net movement           : {market['net_movement']:.4f}"
    )

    print(
        f"Net change %           : {market['net_change_percent']:.3f}%"
    )

    print(
        f"Direction              : {market['direction']}"
    )

    print(
        f"Structure              : {market['structure']}"
    )

    print(
        f"Momentum               : {market['momentum']}"
    )

    print(
        f"Volatility             : {market['volatility']}"
    )

    print(
        f"Rejection              : {market['rejection']}"
    )

    print()
    print("UNIFIED EVIDENCE SCORES")
    print("-" * 70)

    print(
        f"Bullish evidence      : {evidence['bullish_score']:.3f}"
    )

    print(
        f"Bearish evidence      : {evidence['bearish_score']:.3f}"
    )

    print(
        f"Neutral evidence      : {evidence['neutral_score']:.3f}"
    )

    print()
    print("MULTI-TIMEFRAME")
    print("-" * 70)

    print(
        f"Direction              : {mtf['direction']}"
    )

    print(
        f"Alignment              : {mtf['alignment']:.1f}%"
    )

    print(
        f"MTF confidence         : {mtf['confidence']:.1f}%"
    )

    print()
    print("REGIME")
    print("-" * 70)

    print(
        f"Regime                 : {regime['regime']}"
    )

    print(
        f"Strength               : {regime['strength']}"
    )

    print(
        f"Direction              : {regime['direction']}"
    )

    print(
        f"Regime confidence      : {regime['confidence']:.1f}%"
    )

    print()
    print("REGIME TRANSITION")
    print("-" * 70)

    print(
        f"Transition detected    : {transition['transition']}"
    )

    print(
        f"Previous regime        : {transition['previous']}"
    )

    print(
        f"Current regime         : {transition['current']}"
    )

    print(
        f"Stability              : {transition['stability']:.1f}%"
    )

    print(
        f"Stored observations    : {transition['observations']}"
    )

    print()
    print("EXPERIENCE MEMORY")
    print("-" * 70)

    print(
        f"Observations stored    : {experience['observations']}"
    )

    print(
        f"Resolved windows       : {experience['resolved']}"
    )

    print(
        f"Pending windows        : {experience['pending']}"
    )

    print(
        f"Confirmed outcomes     : {experience['confirmed']}"
    )

    print(
        f"Not confirmed          : {experience['not_confirmed']}"
    )

    print(
        f"Neutral outcomes       : {experience['neutral']}"
    )

    print(
        f"Experience accuracy    : {experience['accuracy']:.1f}%"
    )

    print()
    print("ADAPTIVE HISTORICAL MEMORY")
    print("-" * 70)

    print(
        f"Bullish weight         : {adaptive['bullish_weight']:.3f}"
    )

    print(
        f"Bearish weight         : {adaptive['bearish_weight']:.3f}"
    )

    print(
        f"Neutral weight         : {adaptive['neutral_weight']:.3f}"
    )

    print(
        f"Historical confidence  : {adaptive['confidence']:.1f}%"
    )

    print()
    print("SUPPORTING EVIDENCE")
    print("-" * 70)

    if evidence["supporting"]:

        for item in evidence["supporting"]:
            print(
                f"- {item}"
            )

    else:
        print(
            "- No strong supporting evidence identified."
        )

    print()
    print("CONFLICTING EVIDENCE")
    print("-" * 70)

    if evidence["conflicting"]:

        for item in evidence["conflicting"]:
            print(
                f"- {item}"
            )

    else:
        print(
            "- No major conflicting evidence identified."
        )

    print()
    print("LIMITING / UNCERTAIN EVIDENCE")
    print("-" * 70)

    if evidence["limiting"]:

        for item in evidence["limiting"]:
            print(
                f"- {item}"
            )

    else:
        print(
            "- No major limiting evidence identified."
        )

    print()
    print("UNIFIED MARKET STORY")
    print("-" * 70)

    story = (
        f"The MLAI v2.0 Unified Decision Context Engine "
        f"classifies the current market as "
        f"{market_state}. "
        f"The integrated direction is "
        f"{evidence['direction']}, "
        f"with an evidence confidence of "
        f"{evidence['confidence']:.1f}%. "
        f"The analysed {market['candles']}-candle context "
        f"has a {market['direction']} directional character "
        f"and {market['structure']} structure. "
        f"Momentum is {market['momentum']} and volatility is "
        f"{market['volatility']}. "
        f"The multi-timeframe context is "
        f"{mtf['direction']} with "
        f"{mtf['alignment']:.1f}% alignment. "
        f"The current regime is "
        f"{regime['regime']}. "
        f"MLAI has {experience['observations']} stored "
        f"experience observations, with "
        f"{experience['resolved']} resolved windows and "
        f"{experience['pending']} pending windows. "
        f"Pending experience is excluded from learned "
        f"evidence weighting. "
        f"Historical pattern information is treated as "
        f"contextual evidence rather than certainty. "
        f"Conflicting and limiting evidence remains visible. "
        f"The unified interpretation describes the current "
        f"evidence environment and does not guarantee future "
        f"market behaviour."
    )

    print(story)

    print()
    print("UNIFIED MLAI PRINCIPLES")
    print("-" * 70)

    principles = [
        "Direct market evidence has priority.",
        "Multiple evidence layers are fused.",
        "Historical patterns are contextual evidence.",
        "Resolved experience is separate from pending experience.",
        "Pending outcomes receive zero learning influence.",
        "Multi-timeframe disagreement is preserved.",
        "Regime transitions increase uncertainty.",
        "Conflicting evidence is never silently removed.",
        "Confidence represents evidence agreement, not certainty.",
        "No single module determines the final interpretation.",
        "The system does not guarantee future market behaviour.",
        "The engine does not create an automatic trading signal.",
    ]

    for index, principle in enumerate(
        principles,
        start=1
    ):
        print(
            f"{index}. {principle}"
        )

    # --------------------------------------------------------
    # Status
    # --------------------------------------------------------

    loaded_files = {
        MARKET_FILE: market_memory is not None,
        EXPERIENCE_FILE: experience_memory is not None,
        PATTERN_FILE: pattern_memory is not None,
        ADAPTIVE_FILE: adaptive_memory is not None,
        MTF_FILE: mtf_memory is not None,
        REGIME_FILE: regime_memory is not None,
        TRANSITION_FILE: transition_memory is not None,
        REGIME_LEARNING_FILE: regime_learning_memory is not None,
    }

    update_status(
        market,
        experience,
        adaptive,
        mtf,
        regime,
        transition,
        evidence,
        loaded_files,
    )

    print()
    print(
        "PASS: MLAI_PROJECT_STATUS.md updated."
    )

    print()
    print("=" * 70)
    print(
        "PASS: MLAI v2.0 Unified Decision Context Engine completed."
    )
    print("=" * 70)


if __name__ == "__main__":
    main()
