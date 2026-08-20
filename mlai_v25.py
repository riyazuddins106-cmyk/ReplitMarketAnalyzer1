import os
import pickle
import math
from datetime import datetime, timezone


# ============================================================
# MLAI v2.5
# DECISION VALIDATION + EVIDENCE STABILITY ENGINE
#
# Purpose:
#   Validate the unified v2.4 market interpretation before any
#   future prediction/signal layer is introduced.
#
# Important:
#   This engine does NOT create a BUY/SELL trading signal.
# ============================================================


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MARKET_FILE = os.path.join(BASE_DIR, "market_data.bin")
DECISION_FILE = os.path.join(BASE_DIR, "mlai_decision_memory.bin")
SCENARIO_FILE = os.path.join(BASE_DIR, "mlai_scenario_memory.bin")
CALIBRATION_FILE = os.path.join(BASE_DIR, "mlai_calibration_memory.bin")
RELIABILITY_FILE = os.path.join(BASE_DIR, "mlai_reliability_memory.bin")
MTF_FILE = os.path.join(BASE_DIR, "mlai_multitimeframe_memory.bin")
REGIME_FILE = os.path.join(BASE_DIR, "mlai_regime_memory.bin")
ADAPTIVE_FILE = os.path.join(BASE_DIR, "mlai_adaptive_memory.bin")

OUTPUT_FILE = os.path.join(BASE_DIR, "mlai_validation_memory.bin")
STATUS_FILE = os.path.join(BASE_DIR, "MLAI_PROJECT_STATUS.md")


# ============================================================
# BASIC HELPERS
# ============================================================

def load_pickle(path, default=None):
    if not os.path.exists(path):
        return default

    try:
        with open(path, "rb") as f:
            return pickle.load(f)
    except Exception:
        return default


def save_pickle(path, data):
    with open(path, "wb") as f:
        pickle.dump(data, f)


def safe_float(value, default=0.0):
    try:
        value = float(value)

        if not math.isfinite(value):
            return default

        return value
    except Exception:
        return default


def clamp(value, low=0.0, high=100.0):
    return max(low, min(high, value))


def normalize_distribution(bullish, bearish, neutral):
    bullish = max(0.0, safe_float(bullish))
    bearish = max(0.0, safe_float(bearish))
    neutral = max(0.0, safe_float(neutral))

    total = bullish + bearish + neutral

    if total <= 0:
        return 33.333, 33.333, 33.334

    return (
        bullish / total * 100.0,
        bearish / total * 100.0,
        neutral / total * 100.0,
    )


def direction_to_distribution(direction):
    direction = str(direction or "").lower()

    if direction in ("bullish", "bull", "up"):
        return 100.0, 0.0, 0.0

    if direction in ("bearish", "bear", "down"):
        return 0.0, 100.0, 0.0

    return 0.0, 0.0, 100.0


def get_value(data, *keys, default=None):
    if not isinstance(data, dict):
        return default

    for key in keys:
        if key in data:
            return data[key]

    return default


# ============================================================
# LOAD MARKET MEMORY
# ============================================================

print("=" * 70)
print("MLAI v2.5 - LOADING MARKET MEMORY")
print("=" * 70)
print(f"File: {os.path.basename(MARKET_FILE)}")
print()

market_memory = load_pickle(MARKET_FILE)

if market_memory is None:
    print("ERROR: market_data.bin could not be loaded.")
    raise SystemExit(1)

print("PASS: market_data.bin loaded as MLAI memory object.")
print()

# ------------------------------------------------------------
# Extract candles
# ------------------------------------------------------------

candles = []

if isinstance(market_memory, list):
    candles = market_memory

elif isinstance(market_memory, dict):

    for key in (
        "candles",
        "data",
        "market_data",
        "records",
        "ohlcv",
    ):
        value = market_memory.get(key)

        if isinstance(value, list):
            candles = value
            break

if not candles:
    print("ERROR: No candle data found inside market_data.bin.")
    raise SystemExit(1)


print("MEMORY METADATA")
print("-" * 70)

if isinstance(market_memory, dict):

    metadata = market_memory.get("metadata", {})

    if not isinstance(metadata, dict):
        metadata = {}

    print(
        "MLAI version : "
        + str(metadata.get("mlai_version", market_memory.get("mlai_version", "unknown")))
    )

    print(
        "Created at   : "
        + str(metadata.get("created_at", market_memory.get("created_at", "unknown")))
    )

    print(
        "Source       : "
        + str(metadata.get("source", market_memory.get("source", "unknown")))
    )

else:

    print("MLAI version : unknown")
    print("Created at   : unknown")
    print("Source       : unknown")


print()
print(f"Found {len(candles)} stored candles.")
print()

if len(candles) < 20:
    print("ERROR: At least 20 candles are required.")
    raise SystemExit(1)


# ============================================================
# CANDLE READER
# ============================================================

def candle_value(candle, key, index=None):

    if isinstance(candle, dict):

        aliases = {
            "open": ["open", "Open", "o"],
            "high": ["high", "High", "h"],
            "low": ["low", "Low", "l"],
            "close": ["close", "Close", "c"],
            "volume": ["volume", "Volume", "v"],
        }

        for name in aliases.get(key, [key]):

            if name in candle:
                return safe_float(candle[name])

        return 0.0

    if isinstance(candle, (list, tuple)) and index is not None:

        if len(candle) > index:
            return safe_float(candle[index])

    return 0.0


# ============================================================
# USE LATEST 60 CANDLES
# ============================================================

window = candles[-60:]

print("PASS: Using latest 60 candles.")
print()
print("Analysing latest candles...")
print()

closes = []

for candle in window:

    close = candle_value(candle, "close", 4)

    if close > 0:
        closes.append(close)

if len(closes) < 20:
    print("ERROR: Not enough valid closing prices.")
    raise SystemExit(1)


first_close = closes[0]
latest_close = closes[-1]

net_change = latest_close - first_close

if first_close != 0:
    net_change_pct = (net_change / first_close) * 100.0
else:
    net_change_pct = 0.0


# ============================================================
# DIRECT MARKET ANALYSIS
# ============================================================

bullish_candles = 0
bearish_candles = 0
neutral_candles = 0

for candle in window:

    open_price = candle_value(candle, "open", 1)
    close_price = candle_value(candle, "close", 4)

    if close_price > open_price:
        bullish_candles += 1

    elif close_price < open_price:
        bearish_candles += 1

    else:
        neutral_candles += 1


total_candles = bullish_candles + bearish_candles + neutral_candles

if total_candles > 0:

    direct_bullish = bullish_candles / total_candles * 100
    direct_bearish = bearish_candles / total_candles * 100
    direct_neutral = neutral_candles / total_candles * 100

else:

    direct_bullish, direct_bearish, direct_neutral = 33.333, 33.333, 33.334


if net_change_pct > 0.10:
    direct_direction = "bullish"

elif net_change_pct < -0.10:
    direct_direction = "bearish"

else:
    direct_direction = "neutral"


# ============================================================
# MOMENTUM
# ============================================================

half = max(10, len(closes) // 2)

first_half = closes[:half]
second_half = closes[-half:]

first_move = first_half[-1] - first_half[0]
second_move = second_half[-1] - second_half[0]

if abs(second_move) > abs(first_move) * 1.10:
    momentum = "increasing"

elif abs(second_move) < abs(first_move) * 0.90:
    momentum = "decreasing"

else:
    momentum = "stable"


# ============================================================
# VOLATILITY
# ============================================================

returns = []

for i in range(1, len(closes)):

    previous = closes[i - 1]

    if previous != 0:

        change = abs((closes[i] - previous) / previous) * 100.0
        returns.append(change)


if len(returns) >= 20:

    old_vol = sum(returns[: len(returns) // 2]) / (len(returns) // 2)

    new_vol = sum(returns[len(returns) // 2:]) / (
        len(returns) - len(returns) // 2
    )

    if new_vol > old_vol * 1.10:
        volatility = "expanding"

    elif new_vol < old_vol * 0.90:
        volatility = "contracting"

    else:
        volatility = "stable"

else:

    volatility = "stable"


# ============================================================
# STRUCTURE
# ============================================================

structure_window = min(20, len(closes))

recent = closes[-structure_window:]

mid = structure_window // 2

if mid > 2:

    first_segment = recent[:mid]
    second_segment = recent[mid:]

    first_high = max(first_segment)
    second_high = max(second_segment)

    first_low = min(first_segment)
    second_low = min(second_segment)

    if second_high > first_high and second_low > first_low:
        structure = "bullish_structure"

    elif second_high < first_high and second_low < first_low:
        structure = "bearish_structure"

    else:
        structure = "mixed_structure"

else:

    structure = "unknown"


# ============================================================
# REJECTION
# ============================================================

upper_rejections = 0
lower_rejections = 0

for candle in window:

    open_price = candle_value(candle, "open", 1)
    high_price = candle_value(candle, "high", 2)
    low_price = candle_value(candle, "low", 3)
    close_price = candle_value(candle, "close", 4)

    body_high = max(open_price, close_price)
    body_low = min(open_price, close_price)

    upper_wick = max(0.0, high_price - body_high)
    lower_wick = max(0.0, body_low - low_price)

    if upper_wick > lower_wick * 1.25:
        upper_rejections += 1

    elif lower_wick > upper_wick * 1.25:
        lower_rejections += 1


if lower_rejections > upper_rejections:
    rejection = "lower_rejection_dominant"

elif upper_rejections > lower_rejections:
    rejection = "upper_rejection_dominant"

else:
    rejection = "balanced_rejection"


# ============================================================
# LOAD ALL AVAILABLE MEMORY
# ============================================================

print("PASS: Loading MLAI evidence memories...")

decision_memory = load_pickle(DECISION_FILE, {})
scenario_memory = load_pickle(SCENARIO_FILE, {})
calibration_memory = load_pickle(CALIBRATION_FILE, {})
reliability_memory = load_pickle(RELIABILITY_FILE, {})
mtf_memory = load_pickle(MTF_FILE, {})
regime_memory = load_pickle(REGIME_FILE, {})
adaptive_memory = load_pickle(ADAPTIVE_FILE, {})

print("PASS: Evidence memories loaded.")
print()


# ============================================================
# MULTI-TIMEFRAME CONTEXT
# ============================================================

short_direction = "unknown"
medium_direction = "unknown"
higher_direction = "unknown"
mtf_integrated = "unknown"
mtf_alignment = 0.0

if isinstance(mtf_memory, dict):

    contexts = mtf_memory.get("contexts", {})

    if isinstance(contexts, dict):

        short = contexts.get("short", contexts.get("Short", {}))
        medium = contexts.get("medium", contexts.get("Medium", {}))
        higher = contexts.get("higher", contexts.get("Higher", {}))

        if isinstance(short, dict):
            short_direction = str(
                get_value(short, "direction", default="unknown")
            ).lower()

        if isinstance(medium, dict):
            medium_direction = str(
                get_value(medium, "direction", default="unknown")
            ).lower()

        if isinstance(higher, dict):
            higher_direction = str(
                get_value(higher, "direction", default="unknown")
            ).lower()

    mtf_integrated = str(
        get_value(
            mtf_memory,
            "integrated_direction",
            "direction",
            default="unknown",
        )
    ).lower()

    mtf_alignment = safe_float(
        get_value(
            mtf_memory,
            "alignment_score",
            "alignment",
            default=0.0,
        )
    )


# Fallback from direct memory if nested format is different

if mtf_integrated == "unknown":

    directions = [
        short_direction,
        medium_direction,
        higher_direction,
    ]

    valid = [
        d for d in directions
        if d in ("bullish", "bearish", "neutral")
    ]

    if valid:

        bullish_count = valid.count("bullish")
        bearish_count = valid.count("bearish")
        neutral_count = valid.count("neutral")

        if bullish_count >= bearish_count and bullish_count >= neutral_count:
            mtf_integrated = "bullish"

        elif bearish_count >= bullish_count and bearish_count >= neutral_count:
            mtf_integrated = "bearish"

        else:
            mtf_integrated = "neutral"

        mtf_alignment = max(
            bullish_count,
            bearish_count,
            neutral_count
        ) / len(valid) * 100.0


# ============================================================
# REGIME
# ============================================================

regime = "unknown"
regime_direction = "unknown"
regime_strength = "unknown"
regime_confidence = 0.0

if isinstance(regime_memory, dict):

    regime = str(
        get_value(
            regime_memory,
            "regime",
            "current_regime",
            default="unknown",
        )
    )

    regime_direction = str(
        get_value(
            regime_memory,
            "direction",
            "regime_direction",
            default="unknown",
        )
    ).lower()

    regime_strength = str(
        get_value(
            regime_memory,
            "strength",
            "regime_strength",
            default="unknown",
        )
    )

    regime_confidence = safe_float(
        get_value(
            regime_memory,
            "confidence",
            "regime_confidence",
            default=0.0,
        )
    )


# ============================================================
# SCENARIO MEMORY
# ============================================================

scenario_bullish = 0.0
scenario_bearish = 0.0
scenario_neutral = 100.0
primary_scenario = "unknown"

if isinstance(scenario_memory, dict):

    primary_scenario = str(
        get_value(
            scenario_memory,
            "primary_scenario",
            "scenario",
            default="unknown",
        )
    )

    scenario_bullish = safe_float(
        get_value(
            scenario_memory,
            "bullish",
            "bullish_continuation",
            default=0.0,
        )
    )

    scenario_bearish = safe_float(
        get_value(
            scenario_memory,
            "bearish",
            "bearish_reversal",
            default=0.0,
        )
    )

    scenario_neutral = safe_float(
        get_value(
            scenario_memory,
            "neutral",
            "neutral_range",
            default=0.0,
        )
    )

    scenario_bullish, scenario_bearish, scenario_neutral = (
        normalize_distribution(
            scenario_bullish,
            scenario_bearish,
            scenario_neutral,
        )
    )


# ============================================================
# ADAPTIVE MEMORY
# ============================================================

adaptive_bullish = 33.333
adaptive_bearish = 33.333
adaptive_neutral = 33.334

if isinstance(adaptive_memory, dict):

    adaptive_bullish = safe_float(
        get_value(
            adaptive_memory,
            "bullish_weight",
            "bullish",
            default=0.0,
        )
    )

    adaptive_bearish = safe_float(
        get_value(
            adaptive_memory,
            "bearish_weight",
            "bearish",
            default=0.0,
        )
    )

    adaptive_neutral = safe_float(
        get_value(
            adaptive_memory,
            "neutral_weight",
            "neutral",
            default=0.0,
        )
    )

    if (
        adaptive_bullish == 0
        and adaptive_bearish == 0
        and adaptive_neutral == 0
    ):
        adaptive_bullish = 33.333
        adaptive_bearish = 33.333
        adaptive_neutral = 33.334
    else:

        adaptive_bullish, adaptive_bearish, adaptive_neutral = (
            normalize_distribution(
                adaptive_bullish,
                adaptive_bearish,
                adaptive_neutral,
            )
        )


# ============================================================
# EXPERIENCE / RELIABILITY
# ============================================================

experience_resolved = 0
experience_pending = 0
experience_reliability = 0.0

if isinstance(reliability_memory, dict):

    experience_resolved = int(
        safe_float(
            get_value(
                reliability_memory,
                "resolved_experience",
                "resolved_windows",
                default=0,
            )
        )
    )

    experience_pending = int(
        safe_float(
            get_value(
                reliability_memory,
                "pending_experience",
                "pending_windows",
                default=0,
            )
        )
    )

    experience_reliability = safe_float(
        get_value(
            reliability_memory,
            "experience_reliability",
            default=0.0,
        )
    )


# ============================================================
# BUILD EVIDENCE DISTRIBUTIONS
# ============================================================

# Direct market
direct_bullish, direct_bearish, direct_neutral = normalize_distribution(
    direct_bullish,
    direct_bearish,
    direct_neutral,
)


# MTF
mtf_bullish, mtf_bearish, mtf_neutral = direction_to_distribution(
    mtf_integrated
)


# Regime
regime_bullish, regime_bearish, regime_neutral = direction_to_distribution(
    regime_direction
)


# ============================================================
# WEIGHTED FUSION
# ============================================================

# Direct market gets highest weight.
# MTF and regime get medium weight.
# Scenario and adaptive are contextual.
#
# If scenario/adaptive data is unavailable, their neutral
# distribution prevents false confidence.

weights = {
    "direct": 0.35,
    "scenario": 0.15,
    "mtf": 0.20,
    "regime": 0.15,
    "adaptive": 0.15,
}


bullish_score = (
    direct_bullish * weights["direct"]
    + scenario_bullish * weights["scenario"]
    + mtf_bullish * weights["mtf"]
    + regime_bullish * weights["regime"]
    + adaptive_bullish * weights["adaptive"]
)

bearish_score = (
    direct_bearish * weights["direct"]
    + scenario_bearish * weights["scenario"]
    + mtf_bearish * weights["mtf"]
    + regime_bearish * weights["regime"]
    + adaptive_bearish * weights["adaptive"]
)

neutral_score = (
    direct_neutral * weights["direct"]
    + scenario_neutral * weights["scenario"]
    + mtf_neutral * weights["mtf"]
    + regime_neutral * weights["regime"]
    + adaptive_neutral * weights["adaptive"]
)

bullish_score, bearish_score, neutral_score = normalize_distribution(
    bullish_score,
    bearish_score,
    neutral_score,
)


# ============================================================
# INTEGRATED DIRECTION
# ============================================================

scores = {
    "bullish": bullish_score,
    "bearish": bearish_score,
    "neutral": neutral_score,
}

integrated_direction = max(
    scores,
    key=scores.get,
)


# ============================================================
# EVIDENCE AGREEMENT
# ============================================================

largest_score = max(
    bullish_score,
    bearish_score,
    neutral_score,
)

second_score = sorted(scores.values(), reverse=True)[1]

spread = largest_score - second_score

# 0 = no agreement
# 100 = strong agreement
evidence_confidence = clamp(
    spread * 2.0
)


if evidence_confidence >= 70:
    confidence_level = "high"

elif evidence_confidence >= 45:
    confidence_level = "moderate"

elif evidence_confidence >= 25:
    confidence_level = "low"

else:
    confidence_level = "very_low"


# ============================================================
# DECISION STABILITY
# ============================================================

previous_direction = "unknown"

if isinstance(decision_memory, dict):

    previous_direction = str(
        get_value(
            decision_memory,
            "integrated_direction",
            "direction",
            default="unknown",
        )
    ).lower()


if previous_direction == "unknown":

    stability_state = "new_decision"

elif previous_direction == integrated_direction:

    stability_state = "stable_decision"

else:

    stability_state = "decision_changed"


# ============================================================
# CONFLICT DETECTION
# ============================================================

conflicts = []
supporting = []
limitations = []


if direct_direction == integrated_direction:

    supporting.append(
        "Direct market direction agrees with the integrated direction."
    )

else:

    conflicts.append(
        "Direct market direction conflicts with the integrated direction."
    )


if mtf_integrated == integrated_direction:

    supporting.append(
        "Multi-timeframe context supports the integrated direction."
    )

elif mtf_integrated != "unknown":

    conflicts.append(
        "Multi-timeframe context conflicts with the integrated direction."
    )

else:

    limitations.append(
        "Multi-timeframe direction is unavailable."
    )


if regime_direction == integrated_direction:

    supporting.append(
        "Current regime direction supports the integrated direction."
    )

elif regime_direction != "unknown":

    conflicts.append(
        "Current regime direction conflicts with the integrated direction."
    )

else:

    limitations.append(
        "Current regime direction is unavailable."
    )


if structure == "bullish_structure" and integrated_direction == "bullish":

    supporting.append(
        "Bullish market structure supports the integrated direction."
    )

elif structure == "bearish_structure" and integrated_direction == "bearish":

    supporting.append(
        "Bearish market structure supports the integrated direction."
    )

elif structure in ("bullish_structure", "bearish_structure"):

    conflicts.append(
        "Market structure conflicts with the integrated direction."
    )


if momentum == "decreasing":

    limitations.append(
        "Momentum is decreasing, reducing continuation stability."
    )

elif momentum == "increasing":

    supporting.append(
        "Momentum is increasing in the current market context."
    )


if volatility == "contracting":

    limitations.append(
        "Volatility is contracting, which can reduce directional expansion."
    )

elif volatility == "expanding":

    supporting.append(
        "Volatility is expanding in the current market context."
    )


if mtf_alignment < 100 and mtf_integrated != "unknown":

    limitations.append(
        f"Multi-timeframe alignment is incomplete at {mtf_alignment:.1f}%."
    )


if experience_resolved == 0:

    limitations.append(
        "No resolved personal experience is available."
    )


# ============================================================
# DECISION READINESS
# ============================================================

readiness_score = evidence_confidence


if mtf_alignment >= 66.7:
    readiness_score += 5

if regime_confidence >= 50:
    readiness_score += 5

if experience_resolved > 0:
    readiness_score += min(10, experience_reliability / 10)

if len(conflicts) >= 2:
    readiness_score -= 15

elif len(conflicts) == 1:
    readiness_score -= 5


readiness_score = clamp(readiness_score)


if readiness_score >= 75:

    readiness = "decision_ready"

elif readiness_score >= 50:

    readiness = "conditionally_ready"

elif readiness_score >= 30:

    readiness = "insufficient_evidence"

else:

    readiness = "not_ready"


# ============================================================
# MARKET STATE
# ============================================================

if integrated_direction == "bullish":

    market_state = "bullish_validated_environment"

elif integrated_direction == "bearish":

    market_state = "bearish_validated_environment"

else:

    market_state = "neutral_validated_environment"


# ============================================================
# SAVE VALIDATION MEMORY
# ============================================================

validation_record = {
    "version": "2.5",
    "created_at": datetime.now(timezone.utc).isoformat(),

    "market": {
        "candles_analysed": len(window),
        "first_close": first_close,
        "latest_close": latest_close,
        "net_change": net_change,
        "net_change_pct": net_change_pct,
        "bullish_candles": bullish_candles,
        "bearish_candles": bearish_candles,
        "neutral_candles": neutral_candles,
        "direction": direct_direction,
        "structure": structure,
        "momentum": momentum,
        "volatility": volatility,
        "rejection": rejection,
    },

    "decision": {
        "market_state": market_state,
        "integrated_direction": integrated_direction,
        "bullish": bullish_score,
        "bearish": bearish_score,
        "neutral": neutral_score,
        "confidence": evidence_confidence,
        "confidence_level": confidence_level,
    },

    "timeframe": {
        "short": short_direction,
        "medium": medium_direction,
        "higher": higher_direction,
        "integrated": mtf_integrated,
        "alignment": mtf_alignment,
    },

    "regime": {
        "regime": regime,
        "direction": regime_direction,
        "strength": regime_strength,
        "confidence": regime_confidence,
    },

    "scenario": {
        "primary": primary_scenario,
        "bullish": scenario_bullish,
        "bearish": scenario_bearish,
        "neutral": scenario_neutral,
    },

    "experience": {
        "resolved": experience_resolved,
        "pending": experience_pending,
        "reliability": experience_reliability,
    },

    "validation": {
        "previous_direction": previous_direction,
        "stability": stability_state,
        "readiness_score": readiness_score,
        "readiness": readiness,
        "supporting": supporting,
        "conflicts": conflicts,
        "limitations": limitations,
    },
}


save_pickle(
    OUTPUT_FILE,
    validation_record
)

print("PASS: mlai_validation_memory.bin saved.")
print()


# ============================================================
# OUTPUT
# ============================================================

print("=" * 70)
print("MLAI v2.5 DECISION VALIDATION + EVIDENCE STABILITY ENGINE")
print("=" * 70)
print()

print("CURRENT MARKET CONTEXT")
print("-" * 70)
print(f"Direction              : {direct_direction}")
print(f"Structure              : {structure}")
print(f"Momentum               : {momentum}")
print(f"Volatility             : {volatility}")
print(f"Rejection              : {rejection}")
print(f"Latest price           : {latest_close:.4f}")
print(f"Net change %           : {net_change_pct:.3f}%")
print()

print("UNIFIED DECISION")
print("-" * 70)
print(f"Market state           : {market_state}")
print(f"Integrated direction   : {integrated_direction}")
print(
    f"Evidence distribution  : "
    f"B={bullish_score:.1f}% | "
    f"S={bearish_score:.1f}% | "
    f"N={neutral_score:.1f}%"
)
print(f"Evidence confidence    : {evidence_confidence:.1f}%")
print(f"Confidence level       : {confidence_level}")
print()

print("DECISION STABILITY")
print("-" * 70)
print(f"Previous direction     : {previous_direction}")
print(f"Current direction      : {integrated_direction}")
print(f"Stability state        : {stability_state}")
print()

print("MULTI-TIMEFRAME")
print("-" * 70)
print(f"Short direction        : {short_direction}")
print(f"Medium direction       : {medium_direction}")
print(f"Higher direction       : {higher_direction}")
print(f"Integrated direction   : {mtf_integrated}")
print(f"Alignment              : {mtf_alignment:.1f}%")
print()

print("REGIME")
print("-" * 70)
print(f"Regime                 : {regime}")
print(f"Direction              : {regime_direction}")
print(f"Strength               : {regime_strength}")
print(f"Confidence             : {regime_confidence:.1f}%")
print()

print("EXPERIENCE")
print("-" * 70)
print(f"Resolved observations : {experience_resolved}")
print(f"Pending observations  : {experience_pending}")
print(f"Reliability           : {experience_reliability:.1f}%")
print()

print("DECISION READINESS")
print("-" * 70)
print(f"Readiness score        : {readiness_score:.1f}%")
print(f"Readiness              : {readiness}")
print()

print("SUPPORTING EVIDENCE")
print("-" * 70)

if supporting:

    for item in supporting:
        print(f"- {item}")

else:

    print("- None identified.")

print()

print("CONFLICTING EVIDENCE")
print("-" * 70)

if conflicts:

    for item in conflicts:
        print(f"- {item}")

else:

    print("- No major conflicts identified.")

print()

print("LIMITING / UNCERTAIN EVIDENCE")
print("-" * 70)

if limitations:

    for item in limitations:
        print(f"- {item}")

else:

    print("- No major limitations identified.")

print()

print("VALIDATION INTERPRETATION")
print("-" * 70)

if readiness == "decision_ready":

    interpretation = (
        "The evidence layers currently show sufficient agreement for "
        "a validated market-context decision."
    )

elif readiness == "conditionally_ready":

    interpretation = (
        "The evidence currently supports the integrated direction, "
        "but additional confirmation is required before treating the "
        "decision as strongly validated."
    )

elif readiness == "insufficient_evidence":

    interpretation = (
        "The current evidence is not sufficiently mature for a strongly "
        "validated decision. The direction remains contextual."
    )

else:

    interpretation = (
        "The current evidence is not sufficiently reliable or consistent "
        "for a validated decision."
    )


print(interpretation)
print()

print("IMPORTANT")
print("-" * 70)
print(
    "Decision readiness is NOT a prediction probability."
)
print(
    "Evidence confidence is NOT a probability of future price movement."
)
print(
    "Historical evidence does not guarantee future behaviour."
)
print(
    "This engine does NOT create a BUY/SELL trading signal."
)
print()

print("LEARNING PRINCIPLES")
print("-" * 70)
print("1. Validation is separate from prediction.")
print("2. Direct market evidence receives priority.")
print("3. Multiple evidence layers are evaluated together.")
print("4. Conflicting evidence is preserved.")
print("5. Multi-timeframe disagreement reduces decision stability.")
print("6. Regime information provides environmental context.")
print("7. Resolved experience can increase future trust.")
print("8. Pending experience receives no learned reliability.")
print("9. Decision stability is measured across repeated observations.")
print("10. Decision readiness is not a probability.")
print("11. Evidence confidence is not future-price certainty.")
print("12. The engine does not create an automatic trading signal.")
print()


# ============================================================
# PROJECT STATUS
# ============================================================

status_text = f"""# MLAI PROJECT STATUS

## v2.5 Completed

MLAI v2.5 Decision Validation + Evidence Stability Engine completed.

### Current Decision

- Market state: {market_state}
- Integrated direction: {integrated_direction}
- Evidence confidence: {evidence_confidence:.1f}%
- Confidence level: {confidence_level}
- Decision stability: {stability_state}
- Readiness score: {readiness_score:.1f}%
- Readiness: {readiness}

### Market Context

- Direction: {direct_direction}
- Structure: {structure}
- Momentum: {momentum}
- Volatility: {volatility}
- Rejection: {rejection}
- Latest price: {latest_close:.4f}
- Net change: {net_change_pct:.3f}%

### Multi-Timeframe

- Short: {short_direction}
- Medium: {medium_direction}
- Higher: {higher_direction}
- Integrated: {mtf_integrated}
- Alignment: {mtf_alignment:.1f}%

### Regime

- Regime: {regime}
- Direction: {regime_direction}
- Strength: {regime_strength}
- Confidence: {regime_confidence:.1f}%

### Experience

- Resolved: {experience_resolved}
- Pending: {experience_pending}
- Reliability: {experience_reliability:.1f}%

### Safety

v2.5 does not create an automatic BUY/SELL trading signal.

Evidence confidence and decision readiness are contextual measurements,
not probabilities of future market movement.
"""


with open(STATUS_FILE, "w", encoding="utf-8") as f:
    f.write(status_text)


print("PASS: MLAI_PROJECT_STATUS.md updated.")
print()
print("=" * 70)
print("PASS: MLAI v2.5 Decision Validation + Evidence Stability Engine completed.")
print("=" * 70)