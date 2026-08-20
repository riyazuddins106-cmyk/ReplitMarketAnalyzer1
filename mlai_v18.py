import os
import pickle
import math
from datetime import datetime, timezone


# ============================================================
# MLAI v1.8
# MARKET REGIME TRANSITION + STATE MEMORY ENGINE
#
# Input:
#   market_data.bin
#   mlai_multitimeframe_memory.bin
#   mlai_adaptive_memory.bin
#   mlai_regime_memory.bin
#
# Output:
#   mlai_regime_transition_memory.bin
#   MLAI_PROJECT_STATUS.md
#
# Principle:
#   Detect and remember changes in market environment.
#   This is NOT a trading signal.
# ============================================================


MARKET_FILE = "market_data.bin"
MTF_FILE = "mlai_multitimeframe_memory.bin"
ADAPTIVE_FILE = "mlai_adaptive_memory.bin"
REGIME_FILE = "mlai_regime_memory.bin"
TRANSITION_FILE = "mlai_regime_transition_memory.bin"
STATUS_FILE = "MLAI_PROJECT_STATUS.md"

ANALYSIS_CANDLES = 60

REGIME_HISTORY_LIMIT = 500


# ============================================================
# GENERAL HELPERS
# ============================================================

def safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def safe_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default


def pct_change(first, last):
    first = safe_float(first)
    last = safe_float(last)

    if first == 0:
        return 0.0

    return ((last - first) / abs(first)) * 100.0


def normalize_direction(value):
    value = str(value).lower().strip()

    if value in ("bullish", "up", "positive"):
        return "bullish"

    if value in ("bearish", "down", "negative"):
        return "bearish"

    if value in ("neutral", "mixed", "range"):
        return "mixed"

    return "mixed"


def normalize_structure(value):
    value = str(value).lower().strip()

    if "bullish" in value:
        return "bullish_structure"

    if "bearish" in value:
        return "bearish_structure"

    if "range" in value:
        return "range_structure"

    return "unknown_structure"


def normalize_momentum(value):
    value = str(value).lower().strip()

    if value in ("increasing", "rising", "strong"):
        return "increasing"

    if value in ("decreasing", "falling", "weak"):
        return "decreasing"

    return "stable"


def normalize_volatility(value):
    value = str(value).lower().strip()

    if value in ("expanding", "high", "increasing"):
        return "expanding"

    if value in ("contracting", "low", "decreasing"):
        return "contracting"

    return "stable"


def print_line():
    print("-" * 70)


def load_pickle(filename):
    if not os.path.exists(filename):
        return None

    try:
        with open(filename, "rb") as f:
            return pickle.load(f)
    except Exception:
        return None


def save_pickle(filename, data):
    with open(filename, "wb") as f:
        pickle.dump(data, f)


def get_value(obj, *keys, default=None):
    if not isinstance(obj, dict):
        return default

    for key in keys:
        if key in obj:
            return obj[key]

    return default


# ============================================================
# MARKET DATA EXTRACTION
# ============================================================

def extract_candles(memory):
    if isinstance(memory, dict):

        for key in (
            "candles",
            "data",
            "market_data",
            "ohlcv",
            "records",
        ):
            value = memory.get(key)

            if isinstance(value, list):
                return value

        # Some versions may store candles directly under history
        history = memory.get("history")

        if isinstance(history, list):
            return history

    if isinstance(memory, list):
        return memory

    return []


def candle_value(candle, names, default=None):

    if not isinstance(candle, dict):
        return default

    for name in names:
        if name in candle:
            return candle[name]

    return default


def get_close(candle):
    return safe_float(
        candle_value(
            candle,
            ["close", "Close", "c"],
            0.0
        ),
        0.0
    )


def get_open(candle):
    return safe_float(
        candle_value(
            candle,
            ["open", "Open", "o"],
            0.0
        ),
        0.0
    )


def get_high(candle):
    return safe_float(
        candle_value(
            candle,
            ["high", "High", "h"],
            0.0
        ),
        0.0
    )


def get_low(candle):
    return safe_float(
        candle_value(
            candle,
            ["low", "Low", "l"],
            0.0
        ),
        0.0
    )


# ============================================================
# FALLBACK TIMEFRAME ANALYSIS
# ============================================================

def analyse_context(candles):

    if not candles:
        return {
            "direction": "mixed",
            "structure": "unknown_structure",
            "momentum": "stable",
            "volatility": "stable",
            "net_change_pct": 0.0,
            "bullish": 0,
            "bearish": 0,
            "neutral": 0,
        }

    closes = [get_close(c) for c in candles]

    opens = [get_open(c) for c in candles]

    highs = [get_high(c) for c in candles]

    lows = [get_low(c) for c in candles]

    bullish = 0
    bearish = 0
    neutral = 0

    ranges = []
    bodies = []

    for i, candle in enumerate(candles):

        o = opens[i]
        c = closes[i]
        h = highs[i]
        l = lows[i]

        if c > o:
            bullish += 1
        elif c < o:
            bearish += 1
        else:
            neutral += 1

        ranges.append(max(0.0, h - l))
        bodies.append(abs(c - o))

    first_close = closes[0]
    last_close = closes[-1]

    change = pct_change(first_close, last_close)

    if bullish > bearish:
        direction = "bullish"
    elif bearish > bullish:
        direction = "bearish"
    else:
        direction = "mixed"

    # Simple structure approximation
    half = max(2, len(closes) // 2)

    first_half = closes[:half]
    second_half = closes[half:]

    if second_half and first_half:
        first_avg = sum(first_half) / len(first_half)
        second_avg = sum(second_half) / len(second_half)

        if second_avg > first_avg and direction == "bullish":
            structure = "bullish_structure"
        elif second_avg < first_avg and direction == "bearish":
            structure = "bearish_structure"
        else:
            structure = "range_structure"
    else:
        structure = "range_structure"

    recent_body = (
        sum(bodies[-min(10, len(bodies)):]) /
        max(1, min(10, len(bodies)))
    )

    earlier_count = min(10, max(1, len(bodies) // 2))

    earlier_body = (
        sum(bodies[-min(20, len(bodies)):-min(10, len(bodies))])
        / max(1, earlier_count)
    )

    if recent_body > earlier_body * 1.10:
        momentum = "increasing"
    elif recent_body < earlier_body * 0.90:
        momentum = "decreasing"
    else:
        momentum = "stable"

    recent_range = (
        sum(ranges[-min(10, len(ranges)):]) /
        max(1, min(10, len(ranges)))
    )

    earlier_ranges = ranges[-min(20, len(ranges)):-min(10, len(ranges))]

    if earlier_ranges:
        earlier_range = sum(earlier_ranges) / len(earlier_ranges)

        if recent_range > earlier_range * 1.10:
            volatility = "expanding"
        elif recent_range < earlier_range * 0.90:
            volatility = "contracting"
        else:
            volatility = "stable"
    else:
        volatility = "stable"

    return {
        "direction": direction,
        "structure": structure,
        "momentum": momentum,
        "volatility": volatility,
        "net_change_pct": change,
        "bullish": bullish,
        "bearish": bearish,
        "neutral": neutral,
    }


# ============================================================
# REGIME EXTRACTION
# ============================================================

def extract_regime(regime_memory):

    if not isinstance(regime_memory, dict):
        return {
            "regime": "unknown",
            "strength": "unknown",
            "confidence": 0.0,
            "scores": {},
        }

    regime = get_value(
        regime_memory,
        "regime",
        "current_regime",
        "market_regime",
        default="unknown"
    )

    strength = get_value(
        regime_memory,
        "regime_strength",
        "strength",
        default="unknown"
    )

    confidence = safe_float(
        get_value(
            regime_memory,
            "regime_confidence",
            "confidence",
            default=0.0
        )
    )

    scores = get_value(
        regime_memory,
        "regime_scores",
        "scores",
        default={}
    )

    if not isinstance(scores, dict):
        scores = {}

    return {
        "regime": str(regime),
        "strength": str(strength),
        "confidence": confidence,
        "scores": scores,
    }


# ============================================================
# REGIME CLASSIFICATION
# ============================================================

def classify_regime(contexts):

    short = contexts["short"]
    medium = contexts["medium"]
    higher = contexts["higher"]

    bullish_score = 0.0
    bearish_score = 0.0
    range_score = 0.0
    transition_score = 0.0
    volatility_score = 0.0

    for context, weight in (
        (short, 1.0),
        (medium, 2.0),
        (higher, 3.0),
    ):

        direction = normalize_direction(
            context.get("direction")
        )

        structure = normalize_structure(
            context.get("structure")
        )

        momentum = normalize_momentum(
            context.get("momentum")
        )

        volatility = normalize_volatility(
            context.get("volatility")
        )

        if direction == "bullish":
            bullish_score += weight

        elif direction == "bearish":
            bearish_score += weight

        else:
            range_score += weight

        if structure == "bullish_structure":
            bullish_score += weight

        elif structure == "bearish_structure":
            bearish_score += weight

        elif structure == "range_structure":
            range_score += weight

        if volatility == "expanding":
            volatility_score += weight

    directions = [
        normalize_direction(short.get("direction")),
        normalize_direction(medium.get("direction")),
        normalize_direction(higher.get("direction")),
    ]

    if len(set(directions)) > 1:
        transition_score += 2.0

    if bullish_score > bearish_score and bullish_score >= range_score:
        regime = "bullish_trending_environment"

    elif bearish_score > bullish_score and bearish_score >= range_score:
        regime = "bearish_trending_environment"

    elif range_score >= bullish_score and range_score >= bearish_score:
        regime = "range_environment"

    else:
        regime = "transition_environment"

    total = (
        bullish_score +
        bearish_score +
        range_score +
        volatility_score
    )

    if regime.startswith("bullish"):
        dominant = bullish_score
    elif regime.startswith("bearish"):
        dominant = bearish_score
    elif regime.startswith("range"):
        dominant = range_score
    else:
        dominant = max(
            bullish_score,
            bearish_score,
            range_score
        )

    if total > 0:
        confidence = (dominant / total) * 100.0
    else:
        confidence = 0.0

    if confidence >= 75:
        strength = "strong"
    elif confidence >= 55:
        strength = "moderate"
    else:
        strength = "weak"

    return {
        "regime": regime,
        "strength": strength,
        "confidence": round(confidence, 2),
        "bullish_score": round(bullish_score, 3),
        "bearish_score": round(bearish_score, 3),
        "range_score": round(range_score, 3),
        "transition_score": round(transition_score, 3),
        "volatility_score": round(volatility_score, 3),
    }


# ============================================================
# REGIME STABILITY
# ============================================================

def calculate_stability(history, current_regime):

    if not history:
        return {
            "state": "new_regime",
            "persistence": 1,
            "stability": 0.0,
        }

    persistence = 0

    for item in reversed(history):

        if not isinstance(item, dict):
            break

        if item.get("regime") == current_regime:
            persistence += 1
        else:
            break

    total = min(len(history), 20)

    same_count = 0

    for item in history[-total:]:
        if isinstance(item, dict):
            if item.get("regime") == current_regime:
                same_count += 1

    stability = (
        same_count / total * 100.0
        if total > 0
        else 0.0
    )

    if persistence <= 1:
        state = "new_regime"

    elif persistence <= 3:
        state = "early_regime"

    elif persistence <= 8:
        state = "established_regime"

    else:
        state = "persistent_regime"

    return {
        "state": state,
        "persistence": persistence,
        "stability": round(stability, 2),
    }


# ============================================================
# TRANSITION DETECTION
# ============================================================

def detect_transition(history, current_regime):

    if not history:
        return {
            "transition": False,
            "from_regime": None,
            "to_regime": current_regime,
            "type": "initial_observation",
        }

    previous = history[-1]

    if not isinstance(previous, dict):
        return {
            "transition": False,
            "from_regime": None,
            "to_regime": current_regime,
            "type": "unknown",
        }

    previous_regime = previous.get(
        "regime",
        "unknown"
    )

    if previous_regime == current_regime:
        return {
            "transition": False,
            "from_regime": previous_regime,
            "to_regime": current_regime,
            "type": "stable",
        }

    if (
        "bullish" in previous_regime
        and "bearish" in current_regime
    ):
        transition_type = "bullish_to_bearish"

    elif (
        "bearish" in previous_regime
        and "bullish" in current_regime
    ):
        transition_type = "bearish_to_bullish"

    elif "range" in current_regime:
        transition_type = "transition_to_range"

    elif "transition" in current_regime:
        transition_type = "transition_environment"

    else:
        transition_type = "regime_change"

    return {
        "transition": True,
        "from_regime": previous_regime,
        "to_regime": current_regime,
        "type": transition_type,
    }


# ============================================================
# REGIME HISTORY STATISTICS
# ============================================================

def calculate_regime_statistics(history):

    counts = {}

    for item in history:

        if not isinstance(item, dict):
            continue

        regime = item.get(
            "regime",
            "unknown"
        )

        counts[regime] = counts.get(regime, 0) + 1

    total = sum(counts.values())

    frequencies = {}

    if total > 0:
        for regime, count in counts.items():
            frequencies[regime] = round(
                count / total * 100.0,
                2
            )

    return {
        "counts": counts,
        "frequencies": frequencies,
        "total": total,
    }


# ============================================================
# MEMORY CREATION / MIGRATION
# ============================================================

def normalize_transition_memory(memory):

    if not isinstance(memory, dict):

        return {
            "memory_version": "1.8",
            "created_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "updated_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "observations": [],
        }

    if "observations" not in memory:
        memory["observations"] = []

    if not isinstance(
        memory["observations"],
        list
    ):
        memory["observations"] = []

    memory.setdefault(
        "memory_version",
        "1.8"
    )

    memory.setdefault(
        "created_at",
        datetime.now(
            timezone.utc
        ).isoformat()
    )

    memory["updated_at"] = datetime.now(
        timezone.utc
    ).isoformat()

    return memory


# ============================================================
# STATUS DOCUMENT
# ============================================================

def update_status(
    market_memory,
    current_regime,
    stability,
    transition,
    statistics,
    candle_count
):

    source = {}

    if isinstance(market_memory, dict):
        source = market_memory.get(
            "metadata",
            market_memory.get(
                "meta",
                {}
            )
        )

    if not isinstance(source, dict):
        source = {}

    lines = []

    lines.append("# MLAI PROJECT STATUS")
    lines.append("")
    lines.append("## Current Version")
    lines.append("")
    lines.append("MLAI v1.8")
    lines.append("")
    lines.append(
        "Market Regime Transition + State Memory Engine"
    )
    lines.append("")

    lines.append("## Runtime")
    lines.append("")
    lines.append(
        f"- Updated: {datetime.now(timezone.utc).isoformat()}"
    )
    lines.append(
        f"- Candles analysed: {candle_count}"
    )
    lines.append("")

    lines.append("## Current Regime")
    lines.append("")
    lines.append(
        f"- Regime: {current_regime['regime']}"
    )
    lines.append(
        f"- Strength: {current_regime['strength']}"
    )
    lines.append(
        f"- Confidence: {current_regime['confidence']:.1f}%"
    )
    lines.append("")

    lines.append("## Regime Stability")
    lines.append("")
    lines.append(
        f"- State: {stability['state']}"
    )
    lines.append(
        f"- Consecutive observations: "
        f"{stability['persistence']}"
    )
    lines.append(
        f"- Recent stability: "
        f"{stability['stability']:.1f}%"
    )
    lines.append("")

    lines.append("## Regime Transition")
    lines.append("")
    lines.append(
        f"- Transition detected: "
        f"{transition['transition']}"
    )
    lines.append(
        f"- From: "
        f"{transition.get('from_regime')}"
    )
    lines.append(
        f"- To: "
        f"{transition.get('to_regime')}"
    )
    lines.append(
        f"- Type: "
        f"{transition.get('type')}"
    )
    lines.append("")

    lines.append("## Historical Regime Memory")
    lines.append("")
    lines.append(
        f"- Stored regime observations: "
        f"{statistics['total']}"
    )

    for regime, count in sorted(
        statistics["counts"].items(),
        key=lambda x: x[1],
        reverse=True
    ):
        frequency = statistics["frequencies"].get(
            regime,
            0.0
        )

        lines.append(
            f"- {regime}: "
            f"{count} ({frequency:.1f}%)"
        )

    lines.append("")

    lines.append("## v1.8 Principles")
    lines.append("")
    lines.append(
        "1. Regime observations are stored separately "
        "from raw market data."
    )
    lines.append(
        "2. A regime change is detected only when "
        "the current regime differs from the previous "
        "stored regime."
    )
    lines.append(
        "3. Regime persistence is measured over time."
    )
    lines.append(
        "4. A new regime is not automatically treated "
        "as a reversal."
    )
    lines.append(
        "5. Multi-timeframe disagreement remains visible."
    )
    lines.append(
        "6. Historical regime frequency is contextual "
        "evidence, not prediction."
    )
    lines.append(
        "7. The engine does not create an automatic "
        "trading signal."
    )
    lines.append("")

    lines.append("## Memory Files")
    lines.append("")
    lines.append(
        f"- {MARKET_FILE}"
    )
    lines.append(
        f"- {MTF_FILE}"
    )
    lines.append(
        f"- {ADAPTIVE_FILE}"
    )
    lines.append(
        f"- {REGIME_FILE}"
    )
    lines.append(
        f"- {TRANSITION_FILE}"
    )
    lines.append("")

    lines.append(
        "MLAI v1.8 completed successfully."
    )

    with open(
        STATUS_FILE,
        "w",
        encoding="utf-8"
    ) as f:
        f.write("\n".join(lines))


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("MLAI v1.8 - LOADING MARKET MEMORY")
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
        return

    print(
        "PASS: market_data.bin loaded as MLAI memory object."
    )

    metadata = {}

    if isinstance(market_memory, dict):
        metadata = market_memory.get(
            "metadata",
            market_memory.get(
                "meta",
                {}
            )
        )

    if not isinstance(metadata, dict):
        metadata = {}

    print()
    print("MEMORY METADATA")
    print("-" * 70)

    print(
        "MLAI version :",
        metadata.get(
            "mlai_version",
            metadata.get(
                "version",
                "unknown"
            )
        )
    )

    print(
        "Created at   :",
        metadata.get(
            "created_at",
            "unknown"
        )
    )

    print(
        "Source       :",
        metadata.get(
            "source",
            "unknown"
        )
    )

    candles = extract_candles(
        market_memory
    )

    if not candles:
        print()
        print(
            "ERROR: No candles found in market_data.bin."
        )
        return

    print()
    print(
        f"Found {len(candles)} stored candles."
    )

    analysis_candles = candles[
        -ANALYSIS_CANDLES:
    ]

    print()
    print(
        f"PASS: Using latest "
        f"{len(analysis_candles)} candles."
    )

    print()
    print(
        "Analysing latest "
        f"{len(analysis_candles)} candles..."
    )

    # --------------------------------------------------------
    # Load v1.6 memory
    # --------------------------------------------------------

    mtf_memory = load_pickle(
        MTF_FILE
    )

    if mtf_memory is not None:
        print()
        print(
            "PASS: Multi-timeframe memory loaded."
        )
    else:
        print()
        print(
            "INFO: Multi-timeframe memory unavailable; "
            "calculating contexts directly."
        )

    # --------------------------------------------------------
    # Load v1.5 memory
    # --------------------------------------------------------

    adaptive_memory = load_pickle(
        ADAPTIVE_FILE
    )

    if adaptive_memory is not None:
        print(
            "PASS: Adaptive learning memory loaded."
        )
    else:
        print(
            "INFO: Adaptive learning memory unavailable."
        )

    # --------------------------------------------------------
    # Load v1.7 regime memory
    # --------------------------------------------------------

    regime_memory = load_pickle(
        REGIME_FILE
    )

    if regime_memory is not None:
        print(
            "PASS: Regime memory loaded."
        )
    else:
        print(
            "INFO: v1.7 regime memory unavailable; "
            "regime will be calculated."
        )

    # --------------------------------------------------------
    # Calculate contexts
    # --------------------------------------------------------

    short_candles = candles[-20:]

    medium_candles = candles[-60:]

    higher_candles = candles[-120:]

    contexts = {
        "short": analyse_context(
            short_candles
        ),
        "medium": analyse_context(
            medium_candles
        ),
        "higher": analyse_context(
            higher_candles
        ),
    }

    # --------------------------------------------------------
    # Current regime
    # --------------------------------------------------------

    if regime_memory is not None:

        previous_regime_data = extract_regime(
            regime_memory
        )

        # Use v1.7 regime when valid.
        if (
            previous_regime_data["regime"]
            != "unknown"
        ):
            current_regime = previous_regime_data
        else:
            current_regime = classify_regime(
                contexts
            )

    else:

        current_regime = classify_regime(
            contexts
        )

    print()
    print(
        "PASS: Current market regime loaded/calculated."
    )

    # --------------------------------------------------------
    # Load transition memory
    # --------------------------------------------------------

    transition_memory = load_pickle(
        TRANSITION_FILE
    )

    if transition_memory is None:

        transition_memory = (
            normalize_transition_memory(None)
        )

        print(
            "PASS: Created new regime transition memory."
        )

    else:

        transition_memory = (
            normalize_transition_memory(
                transition_memory
            )
        )

        print(
            "PASS: Existing regime transition memory loaded."
        )

    history = transition_memory[
        "observations"
    ]

    # --------------------------------------------------------
    # Detect transition
    # --------------------------------------------------------

    transition = detect_transition(
        history,
        current_regime["regime"]
    )

    # --------------------------------------------------------
    # Stability
    # --------------------------------------------------------

    stability = calculate_stability(
        history,
        current_regime["regime"]
    )

    # --------------------------------------------------------
    # Create observation
    # --------------------------------------------------------

    observation_number = len(history) + 1

    observation = {
        "observation_id": (
            f"regime_obs_{observation_number:06d}"
        ),
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),

        "candle_index": len(candles) - 1,

        "price": get_close(
            candles[-1]
        ),

        "regime": current_regime[
            "regime"
        ],

        "regime_strength": current_regime[
            "strength"
        ],

        "regime_confidence": current_regime[
            "confidence"
        ],

        "bullish_score": current_regime.get(
            "bullish_score",
            0.0
        ),

        "bearish_score": current_regime.get(
            "bearish_score",
            0.0
        ),

        "range_score": current_regime.get(
            "range_score",
            0.0
        ),

        "transition_score": current_regime.get(
            "transition_score",
            0.0
        ),

        "contexts": {
            name: {
                "direction": value.get(
                    "direction"
                ),
                "structure": value.get(
                    "structure"
                ),
                "momentum": value.get(
                    "momentum"
                ),
                "volatility": value.get(
                    "volatility"
                ),
                "net_change_pct": value.get(
                    "net_change_pct",
                    0.0
                ),
            }
            for name, value in contexts.items()
        },

        "transition": transition,

        "stability": stability,
    }

    history.append(
        observation
    )

    if len(history) > REGIME_HISTORY_LIMIT:
        transition_memory[
            "observations"
        ] = history[
            -REGIME_HISTORY_LIMIT:
        ]

    else:
        transition_memory[
            "observations"
        ] = history

    transition_memory[
        "current_regime"
    ] = current_regime

    transition_memory[
        "current_transition"
    ] = transition

    transition_memory[
        "current_stability"
    ] = stability

    transition_memory[
        "updated_at"
    ] = datetime.now(
        timezone.utc
    ).isoformat()

    save_pickle(
        TRANSITION_FILE,
        transition_memory
    )

    print()
    print(
        f"PASS: {TRANSITION_FILE} saved."
    )

    # --------------------------------------------------------
    # Statistics
    # --------------------------------------------------------

    statistics = calculate_regime_statistics(
        transition_memory[
            "observations"
        ]
    )

    # ========================================================
    # DISPLAY
    # ========================================================

    print()
    print("=" * 70)
    print(
        "MLAI v1.8 REGIME TRANSITION + STATE MEMORY ENGINE"
    )
    print("=" * 70)

    print()
    print("CURRENT REGIME")
    print("-" * 70)

    print(
        f"Regime                  : "
        f"{current_regime['regime']}"
    )

    print(
        f"Regime strength         : "
        f"{current_regime['strength']}"
    )

    print(
        f"Regime confidence       : "
        f"{current_regime['confidence']:.1f}%"
    )

    print()
    print("REGIME SCORES")
    print("-" * 70)

    print(
        f"Bullish trend           : "
        f"{current_regime.get('bullish_score', 0.0):.3f}"
    )

    print(
        f"Bearish trend           : "
        f"{current_regime.get('bearish_score', 0.0):.3f}"
    )

    print(
        f"Range                   : "
        f"{current_regime.get('range_score', 0.0):.3f}"
    )

    print(
        f"Transition              : "
        f"{current_regime.get('transition_score', 0.0):.3f}"
    )

    print()
    print("TIMEFRAME CONTEXT")
    print("-" * 70)

    for name, context in contexts.items():

        print(
            f"{name.capitalize():<23} | "
            f"direction={context['direction']:<8} | "
            f"structure={context['structure']}"
        )

    print()
    print("REGIME STABILITY")
    print("-" * 70)

    print(
        f"State                   : "
        f"{stability['state']}"
    )

    print(
        f"Consecutive observations: "
        f"{stability['persistence']}"
    )

    print(
        f"Recent stability       : "
        f"{stability['stability']:.1f}%"
    )

    print()
    print("REGIME TRANSITION")
    print("-" * 70)

    print(
        f"Transition detected     : "
        f"{transition['transition']}"
    )

    print(
        f"Previous regime         : "
        f"{transition.get('from_regime')}"
    )

    print(
        f"Current regime          : "
        f"{transition.get('to_regime')}"
    )

    print(
        f"Transition type         : "
        f"{transition.get('type')}"
    )

    print()
    print("REGIME MEMORY")
    print("-" * 70)

    print(
        f"Stored regime states    : "
        f"{statistics['total']}"
    )

    for regime, count in sorted(
        statistics["counts"].items(),
        key=lambda x: x[1],
        reverse=True
    ):

        frequency = statistics[
            "frequencies"
        ].get(
            regime,
            0.0
        )

        print(
            f"{regime:<35} "
            f"{count:>5} observations | "
            f"{frequency:>5.1f}%"
        )

    print()
    print("REGIME MEMORY INTERPRETATION")
    print("-" * 70)

    if transition["transition"]:

        print(
            f"A regime transition has been detected "
            f"from {transition.get('from_regime')} "
            f"to {transition.get('to_regime')}."
        )

    else:

        if stability["state"] == "new_regime":

            print(
                "The current regime is newly observed "
                "in the v1.8 transition memory."
            )

        elif stability["state"] == "early_regime":

            print(
                "The current regime is beginning to "
                "persist, but there is not yet enough "
                "history to classify it as established."
            )

        elif stability["state"] == "established_regime":

            print(
                "The current regime has persisted across "
                "multiple observations and is becoming "
                "historically established."
            )

        else:

            print(
                "The current regime has shown persistent "
                "behaviour across the stored observations."
            )

    print()
    print("LEARNING PRINCIPLES")
    print("-" * 70)

    principles = [
        "Regime observations are stored separately from raw market data.",
        "A regime change is detected when the current environment differs from the previous stored environment.",
        "Regime persistence is measured over repeated observations.",
        "A new regime is not automatically treated as a reversal.",
        "Multi-timeframe disagreement remains visible.",
        "Historical regime frequency is contextual evidence rather than prediction.",
        "Regime confidence measures evidence agreement rather than certainty.",
        "The engine does not create an automatic trading signal.",
    ]

    for i, principle in enumerate(
        principles,
        1
    ):
        print(
            f"{i}. {principle}"
        )

    print()
    print("CURRENT MARKET STORY")
    print("-" * 70)

    direction = contexts[
        "medium"
    ]["direction"]

    print(
        f"The MLAI v1.8 engine currently identifies "
        f"the environment as "
        f"{current_regime['regime']}. "
        f"The medium-term directional context is "
        f"{direction}. "
        f"The current regime has a calculated evidence "
        f"confidence of "
        f"{current_regime['confidence']:.1f}%. "
        f"The regime transition memory contains "
        f"{statistics['total']} stored regime observations. "
        f"The current regime is classified as "
        f"{stability['state']} with "
        f"{stability['persistence']} consecutive "
        f"observations. "
        f"Transition status is "
        f"{'active' if transition['transition'] else 'stable'}."
    )

    print()
    print(
        "The v1.8 engine is designed to remember how market "
        "environments change over time. A regime transition "
        "is treated as an observation requiring additional "
        "confirmation rather than an automatic directional "
        "signal."
    )

    print()
    print(
        f"PASS: {STATUS_FILE} updated."
    )

    print()
    print("=" * 70)
    print(
        "PASS: MLAI v1.8 Regime Transition + State Memory Engine completed."
    )
    print("=" * 70)


if __name__ == "__main__":
    main()