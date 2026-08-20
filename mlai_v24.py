
import os
import json
import pickle
from datetime import datetime, timezone

# ============================================================
# MLAI v2.4 FIXED
# DECISION FUSION + CONFIDENCE CALIBRATION ENGINE
#
# Inputs:
#   market_data.bin
#   mlai_experience.bin
#   mlai_pattern_memory.bin
#   mlai_adaptive_memory.bin
#   mlai_multitimeframe_memory.bin
#   mlai_regime_memory.bin
#   mlai_regime_transition_memory.bin
#   mlai_regime_learning_memory.bin
#   mlai_unified_memory.bin
#   mlai_scenario_memory.bin
#   mlai_calibration_memory.bin
#   mlai_reliability_memory.bin
#
# Output:
#   mlai_decision_memory.bin
#   MLAI_PROJECT_STATUS.md
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MARKET_FILE = os.path.join(BASE_DIR, "market_data.bin")
DECISION_FILE = os.path.join(BASE_DIR, "mlai_decision_memory.bin")
STATUS_FILE = os.path.join(BASE_DIR, "MLAI_PROJECT_STATUS.md")


def path(name):
    return os.path.join(BASE_DIR, name)


def load_pickle(filename, default=None):
    file_path = path(filename)

    if not os.path.exists(file_path):
        return default

    try:
        with open(file_path, "rb") as f:
            return pickle.load(f)
    except Exception:
        return default


def save_pickle(filename, data):
    with open(path(filename), "wb") as f:
        pickle.dump(data, f)


def number(value, default=0.0):
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def text(value, default="unknown"):
    if value is None:
        return default

    value = str(value).strip()

    if not value:
        return default

    return value


def first_value(data, keys, default=None):
    if not isinstance(data, dict):
        return default

    for key in keys:
        if key in data and data[key] is not None:
            return data[key]

    return default


def find_nested(data, keys, default=None):
    """
    Searches common nested dictionaries without requiring
    one exact memory schema.
    """
    if not isinstance(data, dict):
        return default

    value = first_value(data, keys, None)

    if value is not None:
        return value

    for value in data.values():
        if isinstance(value, dict):
            found = find_nested(value, keys, None)
            if found is not None:
                return found

    return default


def normalize_direction(value):
    value = text(value).lower()

    if value in {
        "bullish",
        "bull",
        "up",
        "long",
        "positive",
        "bullish_trend",
        "bullish_trending_environment",
        "bullish_structural_environment",
        "bullish_continuation_scenario",
    }:
        return "bullish"

    if value in {
        "bearish",
        "bear",
        "down",
        "short",
        "negative",
        "bearish_trend",
        "bearish_trending_environment",
        "bearish_structural_environment",
        "bearish_reversal_scenario",
    }:
        return "bearish"

    if value in {
        "neutral",
        "range",
        "mixed",
        "sideways",
        "unknown",
        "none",
        "",
    }:
        return "neutral"

    return "neutral"


def distribution_from_direction(direction):
    direction = normalize_direction(direction)

    if direction == "bullish":
        return {"bullish": 1.0, "bearish": 0.0, "neutral": 0.0}

    if direction == "bearish":
        return {"bullish": 0.0, "bearish": 1.0, "neutral": 0.0}

    return {"bullish": 0.0, "bearish": 0.0, "neutral": 1.0}


def normalize_distribution(b, s, n):
    b = max(0.0, number(b))
    s = max(0.0, number(s))
    n = max(0.0, number(n))

    total = b + s + n

    if total <= 0:
        return {
            "bullish": 1 / 3,
            "bearish": 1 / 3,
            "neutral": 1 / 3,
        }

    return {
        "bullish": b / total,
        "bearish": s / total,
        "neutral": n / total,
    }


def distribution_from_object(data):
    if not isinstance(data, dict):
        return distribution_from_direction("neutral")

    # Direct percentages / weights.
    bullish = first_value(
        data,
        [
            "bullish",
            "bullish_probability",
            "bullish_weight",
            "bullish_score",
            "bullish_percentage",
        ],
        None,
    )

    bearish = first_value(
        data,
        [
            "bearish",
            "bearish_probability",
            "bearish_weight",
            "bearish_score",
            "bearish_percentage",
        ],
        None,
    )

    neutral = first_value(
        data,
        [
            "neutral",
            "neutral_probability",
            "neutral_weight",
            "neutral_score",
            "neutral_percentage",
        ],
        None,
    )

    if bullish is not None or bearish is not None or neutral is not None:
        b = number(bullish)
        s = number(bearish)
        n = number(neutral)

        # Convert percentages when appropriate.
        if max(abs(b), abs(s), abs(n)) > 1.0:
            b /= 100.0
            s /= 100.0
            n /= 100.0

        return normalize_distribution(b, s, n)

    direction = find_nested(
        data,
        [
            "integrated_direction",
            "direction",
            "directional_character",
            "regime_direction",
        ],
        None,
    )

    if direction is not None:
        return distribution_from_direction(direction)

    return distribution_from_direction("neutral")


def extract_market_data(memory):
    candles = []

    if isinstance(memory, list):
        candles = memory

    elif isinstance(memory, dict):
        for key in [
            "candles",
            "data",
            "market_data",
            "ohlcv",
            "records",
        ]:
            value = memory.get(key)

            if isinstance(value, list):
                candles = value
                break

    return candles


def candle_close(candle):
    if not isinstance(candle, dict):
        return None

    value = first_value(
        candle,
        [
            "close",
            "Close",
            "c",
            "price",
        ],
        None,
    )

    return number(value, None)


def calculate_market_context(candles):
    closes = []

    for candle in candles:
        close = candle_close(candle)

        if close is not None:
            closes.append(close)

    if len(closes) < 2:
        raise RuntimeError("Not enough valid candle close prices.")

    latest = closes[-1]

    first = closes[0]

    movement = latest - first

    change_pct = 0.0

    if first != 0:
        change_pct = (movement / first) * 100.0

    bullish = 0
    bearish = 0
    neutral = 0

    for i in range(1, len(closes)):
        if closes[i] > closes[i - 1]:
            bullish += 1
        elif closes[i] < closes[i - 1]:
            bearish += 1
        else:
            neutral += 1

    if bullish > bearish:
        direction = "bullish"
    elif bearish > bullish:
        direction = "bearish"
    else:
        direction = "neutral"

    # Momentum from first half vs second half.
    midpoint = len(closes) // 2

    first_half = closes[:midpoint]
    second_half = closes[midpoint:]

    first_half_move = (
        first_half[-1] - first_half[0]
        if len(first_half) >= 2
        else 0.0
    )

    second_half_move = (
        second_half[-1] - second_half[0]
        if len(second_half) >= 2
        else 0.0
    )

    if abs(second_half_move) > abs(first_half_move) * 1.10:
        momentum = "increasing"
    elif abs(second_half_move) < abs(first_half_move) * 0.90:
        momentum = "decreasing"
    else:
        momentum = "stable"

    # Volatility from absolute candle changes.
    changes = []

    for i in range(1, len(closes)):
        changes.append(abs(closes[i] - closes[i - 1]))

    if len(changes) >= 10:
        half = len(changes) // 2

        old_vol = sum(changes[:half]) / max(1, len(changes[:half]))
        new_vol = sum(changes[half:]) / max(1, len(changes[half:]))

        if new_vol > old_vol * 1.10:
            volatility = "expanding"
        elif new_vol < old_vol * 0.90:
            volatility = "contracting"
        else:
            volatility = "stable"
    else:
        volatility = "stable"

    return {
        "first_close": first,
        "latest_close": latest,
        "net_movement": movement,
        "net_change_pct": change_pct,
        "bullish_candles": bullish,
        "bearish_candles": bearish,
        "neutral_candles": neutral,
        "direction": direction,
        "momentum": momentum,
        "volatility": volatility,
    }


def extract_mtf(memory):
    if not isinstance(memory, dict):
        return {
            "short": "neutral",
            "medium": "neutral",
            "higher": "neutral",
            "integrated": "neutral",
            "alignment": 0.0,
        }

    contexts = memory.get("timeframe_contexts")

    if not isinstance(contexts, dict):
        contexts = memory.get("contexts")

    if not isinstance(contexts, dict):
        contexts = {}

    def get_context(name):
        item = contexts.get(name)

        if not isinstance(item, dict):
            # Search recursively.
            item = find_nested(
                memory,
                [name],
                None,
            )

        if not isinstance(item, dict):
            return "neutral"

        return normalize_direction(
            first_value(
                item,
                [
                    "direction",
                    "directional_character",
                    "integrated_direction",
                ],
                "neutral",
            )
        )

    short = get_context("short")
    medium = get_context("medium")
    higher = get_context("higher")

    integrated = normalize_direction(
        first_value(
            memory,
            [
                "integrated_direction",
                "direction",
            ],
            None,
        )
        or (
            "bullish"
            if [short, medium, higher].count("bullish")
            > [short, medium, higher].count("bearish")
            else "bearish"
            if [short, medium, higher].count("bearish")
            > [short, medium, higher].count("bullish")
            else "neutral"
        )
    )

    alignment = number(
        first_value(
            memory,
            [
                "alignment_score",
                "alignment",
                "directional_alignment",
            ],
            None,
        ),
        0.0,
    )

    if alignment > 1:
        alignment = alignment / 100.0

    if alignment <= 0:
        directions = [short, medium, higher]

        if directions:
            dominant = max(
                directions.count("bullish"),
                directions.count("bearish"),
            )
            alignment = dominant / len(directions)

    return {
        "short": short,
        "medium": medium,
        "higher": higher,
        "integrated": integrated,
        "alignment": alignment,
    }


def extract_regime(memory):
    if not isinstance(memory, dict):
        return {
            "regime": "unknown",
            "direction": "neutral",
            "strength": "unknown",
            "confidence": 0.0,
        }

    regime = first_value(
        memory,
        [
            "regime",
            "current_regime",
            "market_regime",
        ],
        None,
    )

    if isinstance(regime, dict):
        regime_dict = regime

        regime = first_value(
            regime_dict,
            ["regime", "name", "state"],
            "unknown",
        )

        direction = first_value(
            regime_dict,
            ["direction", "regime_direction"],
            None,
        )

        strength = first_value(
            regime_dict,
            ["strength", "regime_strength"],
            "unknown",
        )

        confidence = first_value(
            regime_dict,
            ["confidence", "regime_confidence"],
            0.0,
        )

    else:
        direction = first_value(
            memory,
            [
                "regime_direction",
                "direction",
            ],
            None,
        )

        strength = first_value(
            memory,
            [
                "regime_strength",
                "strength",
            ],
            "unknown",
        )

        confidence = first_value(
            memory,
            [
                "regime_confidence",
                "confidence",
            ],
            0.0,
        )

    regime = text(regime)

    if direction is None or normalize_direction(direction) == "neutral":
        lower = regime.lower()

        if "bullish" in lower:
            direction = "bullish"
        elif "bearish" in lower:
            direction = "bearish"
        elif "range" in lower:
            direction = "neutral"
        else:
            direction = "neutral"

    confidence = number(confidence)

    if confidence > 1:
        confidence /= 100.0

    return {
        "regime": regime,
        "direction": normalize_direction(direction),
        "strength": text(strength),
        "confidence": max(0.0, min(1.0, confidence)),
    }


def extract_experience(memory):
    if not isinstance(memory, dict):
        return {
            "observations": 0,
            "resolved": 0,
            "pending": 0,
            "accuracy": 0.0,
        }

    observations = first_value(
        memory,
        [
            "total_observations",
            "observations_stored",
            "observations",
            "total",
        ],
        0,
    )

    resolved = first_value(
        memory,
        [
            "resolved_windows",
            "resolved_outcomes",
            "resolved",
            "total_resolved",
        ],
        0,
    )

    pending = first_value(
        memory,
        [
            "pending_windows",
            "pending_outcomes",
            "pending",
            "total_pending",
        ],
        0,
    )

    accuracy = first_value(
        memory,
        [
            "experience_accuracy",
            "accuracy",
            "reliability",
        ],
        0.0,
    )

    return {
        "observations": int(number(observations)),
        "resolved": int(number(resolved)),
        "pending": int(number(pending)),
        "accuracy": max(0.0, min(1.0, number(accuracy) / 100.0))
        if number(accuracy) > 1
        else max(0.0, min(1.0, number(accuracy))),
    }


def extract_reliability(memory):
    if not isinstance(memory, dict):
        return 0.0

    value = first_value(
        memory,
        [
            "overall_reliability",
            "reliability",
            "trust_score",
        ],
        0.0,
    )

    value = number(value)

    if value > 1:
        value /= 100.0

    return max(0.0, min(1.0, value))


def direct_distribution(context):
    bullish = context["bullish_candles"]
    bearish = context["bearish_candles"]
    neutral = context["neutral_candles"]

    return normalize_distribution(
        bullish,
        bearish,
        neutral,
    )


def regime_distribution(regime):
    direction = regime["direction"]

    confidence = regime["confidence"]

    if direction == "bullish":
        return normalize_distribution(
            0.5 + confidence,
            0.5 - confidence,
            0.0,
        )

    if direction == "bearish":
        return normalize_distribution(
            0.5 - confidence,
            0.5 + confidence,
            0.0,
        )

    return {
        "bullish": 1 / 3,
        "bearish": 1 / 3,
        "neutral": 1 / 3,
    }


def mtf_distribution(mtf):
    return distribution_from_direction(
        mtf["integrated"]
    )


def scenario_distribution(memory):
    if not isinstance(memory, dict):
        return distribution_from_direction("neutral")

    primary = first_value(
        memory,
        [
            "primary_scenario",
            "scenario",
            "primary_direction",
        ],
        None,
    )

    if primary is not None:
        return distribution_from_direction(primary)

    # Search nested scenario memory.
    primary = find_nested(
        memory,
        [
            "primary_scenario",
            "scenario",
        ],
        None,
    )

    if primary is not None:
        return distribution_from_direction(primary)

    return distribution_from_direction("neutral")


def adaptive_distribution(memory):
    if not isinstance(memory, dict):
        return distribution_from_direction("neutral")

    b = first_value(
        memory,
        [
            "bullish_weight",
            "bullish_score",
            "bullish_pattern_weight",
        ],
        None,
    )

    s = first_value(
        memory,
        [
            "bearish_weight",
            "bearish_score",
            "bearish_pattern_weight",
        ],
        None,
    )

    n = first_value(
        memory,
        [
            "neutral_weight",
            "neutral_score",
            "neutral_pattern_weight",
        ],
        None,
    )

    if b is not None or s is not None or n is not None:
        return normalize_distribution(
            number(b),
            number(s),
            number(n),
        )

    return distribution_from_direction(
        find_nested(
            memory,
            [
                "integrated_direction",
                "direction",
            ],
            "neutral",
        )
    )


def fuse_distributions(layers):
    """
    Reliability-aware fusion.

    Direct market evidence receives the highest base weight.
    Other layers contribute only when meaningful evidence exists.
    """
    weights = {
        "direct": 0.35,
        "scenario": 0.15,
        "mtf": 0.20,
        "regime": 0.15,
        "adaptive": 0.15,
    }

    totals = {
        "bullish": 0.0,
        "bearish": 0.0,
        "neutral": 0.0,
    }

    for name, distribution in layers.items():
        weight = weights.get(name, 0.0)

        for direction in totals:
            totals[direction] += (
                distribution[direction] * weight
            )

    total = sum(totals.values())

    if total <= 0:
        return {
            "bullish": 1 / 3,
            "bearish": 1 / 3,
            "neutral": 1 / 3,
        }

    return {
        key: value / total
        for key, value in totals.items()
    }


def calculate_confidence(distribution):
    values = sorted(
        distribution.values(),
        reverse=True,
    )

    if not values:
        return 0.0

    # Difference between strongest and weakest evidence.
    spread = values[0] - values[-1]

    # Also reward dominance over the second-best direction.
    dominance = values[0] - values[1]

    confidence = (
        spread * 0.60
        + dominance * 0.40
    )

    return max(
        0.0,
        min(1.0, confidence),
    )


def confidence_level(confidence):
    if confidence >= 0.70:
        return "high_evidence_agreement"

    if confidence >= 0.45:
        return "moderate_evidence_agreement"

    return "low_evidence_agreement"


def dominant_direction(distribution):
    return max(
        distribution,
        key=distribution.get,
    )


def write_status(result):
    now = datetime.now(timezone.utc).isoformat()

    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        f.write(
            "# MLAI PROJECT STATUS\n\n"
            f"Updated: {now}\n\n"
            "## Current Version\n\n"
            "MLAI v2.4 FIXED\n\n"
            "## Engine\n\n"
            "Decision Fusion + Confidence Calibration Engine\n\n"
            "## Current Direction\n\n"
            f"{result['integrated_direction']}\n\n"
            "## Evidence Confidence\n\n"
            f"{result['confidence'] * 100:.1f}%\n\n"
            "## Evidence Distribution\n\n"
            f"- Bullish: {result['distribution']['bullish'] * 100:.1f}%\n"
            f"- Bearish: {result['distribution']['bearish'] * 100:.1f}%\n"
            f"- Neutral: {result['distribution']['neutral'] * 100:.1f}%\n\n"
            "## Principle\n\n"
            "MLAI v2.4 combines direct market evidence, "
            "scenario context, multi-timeframe context, "
            "regime context and adaptive historical evidence. "
            "Confidence represents evidence agreement and is "
            "not a probability of future price movement.\n"
        )


# ============================================================
# MAIN
# ============================================================

print("=" * 70)
print("MLAI v2.4 FIXED - LOADING MARKET MEMORY")
print("=" * 70)
print(f"File: {os.path.basename(MARKET_FILE)}")
print()

market_memory = load_pickle("market_data.bin")

if market_memory is None:
    raise FileNotFoundError(
        "market_data.bin was not found or could not be loaded."
    )

print("PASS: market_data.bin loaded as MLAI memory object.")
print()

metadata = (
    market_memory.get("metadata", {})
    if isinstance(market_memory, dict)
    else {}
)

print("MEMORY METADATA")
print("-" * 70)
print(
    f"MLAI version : "
    f"{metadata.get('mlai_version', metadata.get('version', 'unknown'))}"
)
print(
    f"Created at   : "
    f"{metadata.get('created_at', 'unknown')}"
)
print(
    f"Source       : "
    f"{metadata.get('source', 'unknown')}"
)
print()

candles = extract_market_data(market_memory)

if not candles:
    raise RuntimeError(
        "No candle data found inside market_data.bin."
    )

print(f"Found {len(candles)} stored candles.")
print()

if len(candles) >= 60:
    candles = candles[-60:]
    print("PASS: Using latest 60 candles.")
else:
    print(
        f"WARNING: Only {len(candles)} candles available."
    )

print()
print("Analysing latest candles...")
print()

context = calculate_market_context(candles)

# ------------------------------------------------------------
# LOAD ALL MEMORY LAYERS
# ------------------------------------------------------------

print("PASS: Loading MLAI evidence memories...")
print()

experience_memory = load_pickle(
    "mlai_experience.bin",
    {},
)

pattern_memory = load_pickle(
    "mlai_pattern_memory.bin",
    {},
)

adaptive_memory = load_pickle(
    "mlai_adaptive_memory.bin",
    {},
)

mtf_memory = load_pickle(
    "mlai_multitimeframe_memory.bin",
    {},
)

regime_memory = load_pickle(
    "mlai_regime_memory.bin",
    {},
)

regime_transition_memory = load_pickle(
    "mlai_regime_transition_memory.bin",
    {},
)

regime_learning_memory = load_pickle(
    "mlai_regime_learning_memory.bin",
    {},
)

unified_memory = load_pickle(
    "mlai_unified_memory.bin",
    {},
)

scenario_memory = load_pickle(
    "mlai_scenario_memory.bin",
    {},
)

calibration_memory = load_pickle(
    "mlai_calibration_memory.bin",
    {},
)

reliability_memory = load_pickle(
    "mlai_reliability_memory.bin",
    {},
)

print("PASS: Evidence memories loaded.")
print()

# ------------------------------------------------------------
# EXTRACT CORRECT CURRENT STATE
# ------------------------------------------------------------

mtf = extract_mtf(mtf_memory)

regime = extract_regime(regime_memory)

experience = extract_experience(
    experience_memory
)

reliability = extract_reliability(
    reliability_memory
)

# If the main regime memory is incomplete, use regime learning.
if regime["regime"] == "unknown":
    alternative_regime = extract_regime(
        regime_learning_memory
    )

    if alternative_regime["regime"] != "unknown":
        regime = alternative_regime

# If MTF memory is incomplete, try unified memory.
if mtf["integrated"] == "neutral":
    alternative_mtf = extract_mtf(
        unified_memory
    )

    if alternative_mtf["integrated"] != "neutral":
        mtf = alternative_mtf

# ------------------------------------------------------------
# BUILD EVIDENCE LAYERS
# ------------------------------------------------------------

direct = direct_distribution(context)

scenario = scenario_distribution(
    scenario_memory
)

mtf_dist = mtf_distribution(
    mtf
)

regime_dist = regime_distribution(
    regime
)

adaptive = adaptive_distribution(
    adaptive_memory
)

layers = {
    "direct": direct,
    "scenario": scenario,
    "mtf": mtf_dist,
    "regime": regime_dist,
    "adaptive": adaptive,
}

distribution = fuse_distributions(
    layers
)

integrated_direction = dominant_direction(
    distribution
)

confidence = calculate_confidence(
    distribution
)

level = confidence_level(
    confidence
)

# ------------------------------------------------------------
# SAVE DECISION MEMORY
# ------------------------------------------------------------

decision_memory = {
    "mlai_version": "2.4",
    "engine": (
        "Decision Fusion + Confidence "
        "Calibration Engine"
    ),
    "created_at": datetime.now(
        timezone.utc
    ).isoformat(),

    "market_context": context,

    "evidence_layers": {
        "direct_market": direct,
        "scenario": scenario,
        "multi_timeframe": mtf_dist,
        "regime": regime_dist,
        "adaptive": adaptive,
    },

    "multi_timeframe": mtf,

    "regime": regime,

    "experience": experience,

    "reliability": reliability,

    "unified_decision": {
        "integrated_direction": integrated_direction,
        "distribution": distribution,
        "confidence": confidence,
        "confidence_level": level,
    },

    "principles": [
        "Direct market evidence receives priority.",
        "Multiple evidence layers are fused.",
        "Historical patterns remain contextual evidence.",
        "Pending experience receives zero learning influence.",
        "Resolved experience receives increasing influence.",
        "Multi-timeframe disagreement remains visible.",
        "Regime information provides environmental context.",
        "Reliability modifies trust but is not prediction probability.",
        "Scenario percentages are evidence-weighted.",
        "Conflicting evidence is never silently removed.",
        "Confidence represents evidence agreement.",
        "No single module determines the interpretation.",
        "The system does not guarantee future behaviour.",
        "The engine does not create an automatic trading signal.",
    ],
}

save_pickle(
    "mlai_decision_memory.bin",
    decision_memory,
)

print(
    "PASS: mlai_decision_memory.bin saved."
)
print()

# ============================================================
# OUTPUT
# ============================================================

print("=" * 70)
print(
    "MLAI v2.4 FIXED DECISION FUSION + "
    "CONFIDENCE CALIBRATION ENGINE"
)
print("=" * 70)
print()

print("CURRENT MARKET CONTEXT")
print("-" * 70)
print(
    f"Direction              : {context['direction']}"
)
print(
    f"First close            : {context['first_close']:.4f}"
)
print(
    f"Latest close           : {context['latest_close']:.4f}"
)
print(
    f"Net movement           : {context['net_movement']:.4f}"
)
print(
    f"Net change %           : {context['net_change_pct']:.3f}%"
)
print(
    f"Bullish candles        : {context['bullish_candles']}"
)
print(
    f"Bearish candles        : {context['bearish_candles']}"
)
print(
    f"Neutral candles        : {context['neutral_candles']}"
)
print()

print("EVIDENCE LAYER DISTRIBUTIONS")
print("-" * 70)

for label, data in [
    ("Direct market", direct),
    ("Scenario", scenario),
    ("Multi-timeframe", mtf_dist),
    ("Regime", regime_dist),
    ("Adaptive", adaptive),
]:
    print(
        f"{label:<22} : "
        f"B={data['bullish'] * 100:.1f}% | "
        f"S={data['bearish'] * 100:.1f}% | "
        f"N={data['neutral'] * 100:.1f}%"
    )

print()

print("UNIFIED DECISION")
print("-" * 70)
print(
    f"Market state           : "
    f"{integrated_direction}_evidence_environment"
)
print(
    f"Integrated direction   : "
    f"{integrated_direction}"
)
print(
    f"Evidence distribution  : "
    f"B={distribution['bullish'] * 100:.1f}% | "
    f"S={distribution['bearish'] * 100:.1f}% | "
    f"N={distribution['neutral'] * 100:.1f}%"
)
print(
    f"Evidence confidence    : "
    f"{confidence * 100:.1f}%"
)
print(
    f"Confidence level       : {level}"
)
print()

print("RELIABILITY / TRUST")
print("-" * 70)
print(
    f"Overall reliability    : "
    f"{reliability * 100:.1f}%"
)
print(
    f"Experience reliability : "
    f"{experience['accuracy'] * 100:.1f}%"
)
print(
    f"Resolved experience   : "
    f"{experience['resolved']}"
)
print(
    f"Pending experience    : "
    f"{experience['pending']}"
)
print()

print("REGIME CONTEXT")
print("-" * 70)
print(
    f"Regime                 : "
    f"{regime['regime']}"
)
print(
    f"Regime direction       : "
    f"{regime['direction']}"
)
print(
    f"Regime strength        : "
    f"{regime['strength']}"
)
print(
    f"Regime confidence      : "
    f"{regime['confidence'] * 100:.1f}%"
)
print()

print("MULTI-TIMEFRAME CONTEXT")
print("-" * 70)
print(
    f"Short direction        : {mtf['short']}"
)
print(
    f"Medium direction       : {mtf['medium']}"
)
print(
    f"Higher direction       : {mtf['higher']}"
)
print(
    f"Integrated direction   : {mtf['integrated']}"
)
print(
    f"Alignment              : "
    f"{mtf['alignment'] * 100:.1f}%"
)
print()

print("SUPPORTING EVIDENCE")
print("-" * 70)

if direct["bullish"] > direct["bearish"]:
    print(
        "- Direct candle participation currently "
        "favours bullish direction."
    )
elif direct["bearish"] > direct["bullish"]:
    print(
        "- Direct candle participation currently "
        "favours bearish direction."
    )
else:
    print(
        "- Direct candle participation is balanced."
    )

if context["net_change_pct"] > 0:
    print(
        f"- Price moved upward by "
        f"{context['net_change_pct']:.3f}% across "
        f"the analysed context."
    )
elif context["net_change_pct"] < 0:
    print(
        f"- Price moved downward by "
        f"{abs(context['net_change_pct']):.3f}% across "
        f"the analysed context."
    )

if mtf["integrated"] == integrated_direction:
    print(
        "- Multi-timeframe context supports the "
        "integrated direction."
    )

if regime["direction"] == integrated_direction:
    print(
        "- Current regime direction supports the "
        "integrated direction."
    )

print()

print("CONFLICTING EVIDENCE")
print("-" * 70)

conflict_found = False

if mtf["short"] != "neutral":
    if (
        mtf["short"] != mtf["medium"]
        and mtf["medium"] != "neutral"
    ):
        print(
            "- Short-term and medium-term directions "
            "are not aligned."
        )
        conflict_found = True

if regime["direction"] not in {
    "neutral",
    integrated_direction,
}:
    print(
        "- Regime direction conflicts with the "
        "integrated direction."
    )
    conflict_found = True

if (
    direct["bullish"] > direct["bearish"]
    and regime["direction"] == "bearish"
):
    print(
        "- Direct market evidence conflicts with "
        "the regime direction."
    )
    conflict_found = True

if not conflict_found:
    print(
        "- No major conflicting evidence identified."
    )

print()

print("LIMITING / UNCERTAIN EVIDENCE")
print("-" * 70)

if experience["resolved"] == 0:
    print(
        "- No resolved personal experience is "
        "available yet."
    )

if reliability <= 0:
    print(
        "- Overall evidence reliability is not yet "
        "supported by resolved historical samples."
    )

if mtf["alignment"] < 1.0:
    print(
        "- Multi-timeframe alignment is incomplete."
    )

print(
    "- Confidence represents evidence agreement, "
    "not a probability of future price movement."
)

print()

print("CURRENT MARKET STORY")
print("-" * 70)

print(
    f"The MLAI v2.4 Fixed Decision Fusion Engine "
    f"evaluates the current market context as "
    f"{integrated_direction}_evidence_environment."
)

print(
    f"The integrated direction is {integrated_direction}, "
    f"with an evidence distribution of "
    f"{distribution['bullish'] * 100:.1f}% bullish, "
    f"{distribution['bearish'] * 100:.1f}% bearish and "
    f"{distribution['neutral'] * 100:.1f}% neutral."
)

print(
    f"The calculated evidence confidence is "
    f"{confidence * 100:.1f}%, classified as "
    f"{level}."
)

print(
    f"The multi-timeframe context is "
    f"{mtf['integrated']} with "
    f"{mtf['alignment'] * 100:.1f}% directional alignment."
)

print(
    f"The current regime is {regime['regime']} "
    f"with {regime['confidence'] * 100:.1f}% regime confidence."
)

print(
    f"MLAI has {experience['observations']} stored "
    f"experience observations, with "
    f"{experience['resolved']} resolved windows and "
    f"{experience['pending']} pending windows."
)

print(
    "Historical information remains contextual evidence. "
    "The final interpretation describes the current "
    "evidence environment and does not guarantee future "
    "market behaviour."
)

print()

print("DECISION FUSION PRINCIPLES")
print("-" * 70)

principles = decision_memory["principles"]

for index, principle in enumerate(
    principles,
    start=1,
):
    print(f"{index}. {principle}")

print()

write_status(
    {
        "integrated_direction": integrated_direction,
        "distribution": distribution,
        "confidence": confidence,
    }
)

print(
    "PASS: MLAI_PROJECT_STATUS.md updated."
)

print()
print("=" * 70)
print(
    "PASS: MLAI v2.4 FIXED Decision Fusion + "
    "Confidence Calibration Engine completed."
)
print("=" * 70)
