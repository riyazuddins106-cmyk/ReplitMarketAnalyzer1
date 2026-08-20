import os
import pickle
from datetime import datetime, timezone


# ============================================================
# MLAI v1.7 - MARKET REGIME DETECTION ENGINE
#
# Purpose:
#   Detect the current market environment/regime using:
#   - Candle behaviour
#   - Price movement
#   - Structure
#   - Momentum
#   - Volatility
#   - Multi-timeframe context
#   - Existing MLAI adaptive memory
#
# Important:
#   This version identifies market environment.
#   It does NOT create an automatic trading signal.
# ============================================================


MARKET_FILE = "market_data.bin"
MTF_FILE = "mlai_multitimeframe_memory.bin"
ADAPTIVE_FILE = "mlai_adaptive_memory.bin"
STATUS_FILE = "MLAI_PROJECT_STATUS.md"

LOOKBACK = 60
SHORT_LOOKBACK = 20
MEDIUM_LOOKBACK = 60
HIGHER_LOOKBACK = 120


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


def get_value(obj, key, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)

    return getattr(obj, key, default)


def normalize_candle(candle):
    if isinstance(candle, dict):
        return {
            "open": safe_float(
                candle.get("open", candle.get("Open", 0))
            ),
            "high": safe_float(
                candle.get("high", candle.get("High", 0))
            ),
            "low": safe_float(
                candle.get("low", candle.get("Low", 0))
            ),
            "close": safe_float(
                candle.get("close", candle.get("Close", 0))
            ),
        }

    return {
        "open": safe_float(getattr(candle, "open", 0)),
        "high": safe_float(getattr(candle, "high", 0)),
        "low": safe_float(getattr(candle, "low", 0)),
        "close": safe_float(getattr(candle, "close", 0)),
    }


# ============================================================
# LOAD MARKET MEMORY
# ============================================================

print("=" * 70)
print("MLAI v1.7 - LOADING MARKET MEMORY")
print("=" * 70)
print(f"File: {MARKET_FILE}")
print()


if not os.path.exists(MARKET_FILE):
    print("ERROR: market_data.bin not found.")
    raise SystemExit(1)


try:
    with open(MARKET_FILE, "rb") as f:
        market_memory = pickle.load(f)

    print("PASS: market_data.bin loaded as MLAI memory object.")
except Exception as exc:
    print(f"ERROR: Could not load market_data.bin: {exc}")
    raise SystemExit(1)


# ============================================================
# EXTRACT CANDLES
# ============================================================

raw_candles = None

if isinstance(market_memory, dict):

    possible_keys = [
        "candles",
        "data",
        "records",
        "market_data",
        "ohlcv",
    ]

    for key in possible_keys:
        value = market_memory.get(key)

        if isinstance(value, list):
            raw_candles = value
            break

elif isinstance(market_memory, list):
    raw_candles = market_memory


if raw_candles is None:

    for attr in [
        "candles",
        "data",
        "records",
        "market_data",
        "ohlcv",
    ]:
        value = getattr(market_memory, attr, None)

        if isinstance(value, list):
            raw_candles = value
            break


if not raw_candles:
    print("ERROR: No candle data found in market_data.bin.")
    raise SystemExit(1)


candles = [
    normalize_candle(c)
    for c in raw_candles
]


print()
print("MEMORY METADATA")
print("-" * 70)

metadata = market_memory if isinstance(market_memory, dict) else {}

print(
    "MLAI version :",
    metadata.get("mlai_version", metadata.get("version", "unknown"))
)

print(
    "Created at   :",
    metadata.get("created_at", "unknown")
)

print(
    "Source       :",
    metadata.get("source", "unknown")
)

print()
print(f"Found {len(candles)} stored candles.")


if len(candles) < HIGHER_LOOKBACK:
    print(
        f"ERROR: At least {HIGHER_LOOKBACK} candles are required "
        "for v1.7."
    )
    raise SystemExit(1)


latest = candles[-LOOKBACK:]

print()
print(f"PASS: Using latest {LOOKBACK} candles.")
print()
print("Analysing latest 60 candles...")


# ============================================================
# CANDLE ANALYSIS
# ============================================================

def analyse_context(data):

    bullish = 0
    bearish = 0
    neutral = 0

    ranges = []
    bodies = []

    for c in data:

        o = c["open"]
        h = c["high"]
        l = c["low"]
        close = c["close"]

        candle_range = max(h - l, 0)
        body = abs(close - o)

        ranges.append(candle_range)
        bodies.append(body)

        if close > o:
            bullish += 1
        elif close < o:
            bearish += 1
        else:
            neutral += 1

    first_close = data[0]["close"]
    latest_close = data[-1]["close"]

    if first_close != 0:
        net_change_pct = (
            (latest_close - first_close)
            / first_close
        ) * 100
    else:
        net_change_pct = 0.0

    # --------------------------------------------------------
    # Momentum
    # --------------------------------------------------------

    half = max(len(data) // 2, 1)

    first_half = data[:half]
    second_half = data[half:]

    first_move = (
        first_half[-1]["close"]
        - first_half[0]["close"]
    )

    second_move = (
        second_half[-1]["close"]
        - second_half[0]["close"]
    )

    first_body_avg = (
        sum(abs(c["close"] - c["open"]) for c in first_half)
        / len(first_half)
    )

    second_body_avg = (
        sum(abs(c["close"] - c["open"]) for c in second_half)
        / len(second_half)
    )

    if abs(second_move) > abs(first_move) * 1.10:
        momentum = "increasing"
    elif abs(second_move) < abs(first_move) * 0.90:
        momentum = "decreasing"
    else:
        momentum = "stable"

    # --------------------------------------------------------
    # Volatility
    # --------------------------------------------------------

    range_half = max(len(ranges) // 2, 1)

    early_range = (
        sum(ranges[:range_half])
        / len(ranges[:range_half])
    )

    recent_range = (
        sum(ranges[range_half:])
        / len(ranges[range_half:])
    )

    if recent_range > early_range * 1.10:
        volatility = "expanding"
    elif recent_range < early_range * 0.90:
        volatility = "contracting"
    else:
        volatility = "stable"

    # --------------------------------------------------------
    # Direction
    # --------------------------------------------------------

    if bullish > bearish + max(2, len(data) * 0.05):
        direction = "bullish"
    elif bearish > bullish + max(2, len(data) * 0.05):
        direction = "bearish"
    else:
        direction = "mixed"

    return {
        "candles": len(data),
        "bullish": bullish,
        "bearish": bearish,
        "neutral": neutral,
        "first_close": first_close,
        "latest_close": latest_close,
        "net_change_pct": net_change_pct,
        "momentum": momentum,
        "volatility": volatility,
        "direction": direction,
        "avg_range": (
            sum(ranges) / len(ranges)
            if ranges else 0
        ),
        "avg_body": (
            sum(bodies) / len(bodies)
            if bodies else 0
        ),
    }


short_context = analyse_context(
    candles[-SHORT_LOOKBACK:]
)

medium_context = analyse_context(
    candles[-MEDIUM_LOOKBACK:]
)

higher_context = analyse_context(
    candles[-HIGHER_LOOKBACK:]
)


# ============================================================
# STRUCTURE ANALYSIS
# ============================================================

def detect_structure(data):

    highs = []
    lows = []

    if len(data) < 5:
        return "unknown"

    for i in range(2, len(data) - 2):

        h = data[i]["high"]
        l = data[i]["low"]

        if (
            h >= data[i - 1]["high"]
            and h >= data[i - 2]["high"]
            and h >= data[i + 1]["high"]
            and h >= data[i + 2]["high"]
        ):
            highs.append(h)

        if (
            l <= data[i - 1]["low"]
            and l <= data[i - 2]["low"]
            and l <= data[i + 1]["low"]
            and l <= data[i + 2]["low"]
        ):
            lows.append(l)

    higher_highs = 0
    lower_highs = 0
    higher_lows = 0
    lower_lows = 0

    for i in range(1, len(highs)):
        if highs[i] > highs[i - 1]:
            higher_highs += 1
        elif highs[i] < highs[i - 1]:
            lower_highs += 1

    for i in range(1, len(lows)):
        if lows[i] > lows[i - 1]:
            higher_lows += 1
        elif lows[i] < lows[i - 1]:
            lower_lows += 1

    bullish_score = higher_highs + higher_lows
    bearish_score = lower_highs + lower_lows

    if bullish_score > bearish_score + 1:
        structure = "bullish_structure"

    elif bearish_score > bullish_score + 1:
        structure = "bearish_structure"

    else:
        structure = "range_structure"

    return {
        "structure": structure,
        "swing_highs": len(highs),
        "swing_lows": len(lows),
        "higher_highs": higher_highs,
        "lower_highs": lower_highs,
        "higher_lows": higher_lows,
        "lower_lows": lower_lows,
    }


short_structure = detect_structure(
    candles[-SHORT_LOOKBACK:]
)

medium_structure = detect_structure(
    candles[-MEDIUM_LOOKBACK:]
)

higher_structure = detect_structure(
    candles[-HIGHER_LOOKBACK:]
)


# ============================================================
# LOAD v1.6 MULTI-TIMEFRAME MEMORY
# ============================================================

mtf_memory = None

if os.path.exists(MTF_FILE):

    try:

        with open(MTF_FILE, "rb") as f:
            mtf_memory = pickle.load(f)

        print()
        print("PASS: Multi-timeframe memory loaded.")

    except Exception:

        print()
        print(
            "WARNING: Multi-timeframe memory could not be loaded."
        )


# ============================================================
# LOAD ADAPTIVE MEMORY
# ============================================================

adaptive_memory = None

if os.path.exists(ADAPTIVE_FILE):

    try:

        with open(ADAPTIVE_FILE, "rb") as f:
            adaptive_memory = pickle.load(f)

        print("PASS: Adaptive learning memory loaded.")

    except Exception:

        print(
            "WARNING: Adaptive learning memory could not be loaded."
        )


print()
print("PASS: Detecting current market regime...")


# ============================================================
# REGIME SCORING
# ============================================================

scores = {
    "bullish_trend": 0.0,
    "bearish_trend": 0.0,
    "range": 0.0,
    "breakout": 0.0,
    "high_volatility": 0.0,
    "low_volatility": 0.0,
    "transition": 0.0,
}


contexts = [
    short_context,
    medium_context,
    higher_context,
]

structures = [
    short_structure,
    medium_structure,
    higher_structure,
]


# ------------------------------------------------------------
# Directional trend evidence
# ------------------------------------------------------------

for context, structure in zip(contexts, structures):

    if context["direction"] == "bullish":
        scores["bullish_trend"] += 2.0

    elif context["direction"] == "bearish":
        scores["bearish_trend"] += 2.0

    if structure["structure"] == "bullish_structure":
        scores["bullish_trend"] += 2.0

    elif structure["structure"] == "bearish_structure":
        scores["bearish_trend"] += 2.0

    elif structure["structure"] == "range_structure":
        scores["range"] += 2.0


# ------------------------------------------------------------
# Momentum
# ------------------------------------------------------------

if medium_context["momentum"] == "increasing":

    if medium_context["direction"] == "bullish":
        scores["bullish_trend"] += 2.0

    elif medium_context["direction"] == "bearish":
        scores["bearish_trend"] += 2.0


# ------------------------------------------------------------
# Volatility
# ------------------------------------------------------------

volatility_values = [
    short_context["volatility"],
    medium_context["volatility"],
    higher_context["volatility"],
]

expanding_count = volatility_values.count("expanding")
contracting_count = volatility_values.count("contracting")

if expanding_count >= 2:
    scores["high_volatility"] += 3.0

elif contracting_count >= 2:
    scores["low_volatility"] += 3.0


# ------------------------------------------------------------
# Breakout / transition evidence
# ------------------------------------------------------------

short_direction = short_context["direction"]
medium_direction = medium_context["direction"]
higher_direction = higher_context["direction"]

if (
    short_direction != medium_direction
    and medium_direction == higher_direction
):
    scores["transition"] += 4.0

if (
    short_context["volatility"] == "expanding"
    and medium_context["volatility"] == "expanding"
):
    scores["breakout"] += 3.0


# ------------------------------------------------------------
# Range evidence
# ------------------------------------------------------------

if (
    short_structure["structure"] == "range_structure"
    and medium_structure["structure"] == "range_structure"
):
    scores["range"] += 4.0


# ============================================================
# DETERMINE PRIMARY REGIME
# ============================================================

primary_regime = max(
    scores,
    key=scores.get
)

primary_score = scores[primary_regime]

total_score = sum(scores.values())

if total_score > 0:

    regime_confidence = (
        primary_score / total_score
    ) * 100

else:

    regime_confidence = 0.0


# ------------------------------------------------------------
# Improve classification where strong directional agreement
# exists.
# ------------------------------------------------------------

if (
    short_direction == "bullish"
    and medium_direction == "bullish"
    and higher_direction == "bullish"
    and medium_structure["structure"] == "bullish_structure"
):

    primary_regime = "bullish_trend"

elif (
    short_direction == "bearish"
    and medium_direction == "bearish"
    and higher_direction == "bearish"
    and medium_structure["structure"] == "bearish_structure"
):

    primary_regime = "bearish_trend"


# ============================================================
# REGIME LABELS
# ============================================================

regime_labels = {
    "bullish_trend":
        "bullish_trending_environment",

    "bearish_trend":
        "bearish_trending_environment",

    "range":
        "range_bound_environment",

    "breakout":
        "breakout_environment",

    "high_volatility":
        "high_volatility_environment",

    "low_volatility":
        "low_volatility_environment",

    "transition":
        "market_transition_environment",
}


regime_label = regime_labels.get(
    primary_regime,
    "mixed_market_environment"
)


# ============================================================
# REGIME STATE
# ============================================================

if regime_confidence >= 70:
    regime_strength = "strong"

elif regime_confidence >= 50:
    regime_strength = "moderate"

else:
    regime_strength = "weak"


# ============================================================
# SUPPORTING EVIDENCE
# ============================================================

supporting = []
conflicting = []


if primary_regime == "bullish_trend":

    if medium_context["direction"] == "bullish":
        supporting.append(
            "Medium-term directional behaviour is bullish."
        )

    if medium_structure["structure"] == "bullish_structure":
        supporting.append(
            "Medium-term market structure is bullish."
        )

    if higher_context["direction"] == "bullish":
        supporting.append(
            "Higher context remains bullish."
        )

    if short_context["direction"] == "bearish":
        conflicting.append(
            "Short-term context is temporarily bearish."
        )


elif primary_regime == "bearish_trend":

    if medium_context["direction"] == "bearish":
        supporting.append(
            "Medium-term directional behaviour is bearish."
        )

    if medium_structure["structure"] == "bearish_structure":
        supporting.append(
            "Medium-term market structure is bearish."
        )

    if higher_context["direction"] == "bearish":
        supporting.append(
            "Higher context remains bearish."
        )

    if short_context["direction"] == "bullish":
        conflicting.append(
            "Short-term context is temporarily bullish."
        )


elif primary_regime == "range":

    supporting.append(
        "Multiple contexts show balanced directional behaviour."
    )

    supporting.append(
        "Swing structure shows range-like behaviour."
    )


elif primary_regime == "breakout":

    supporting.append(
        "Volatility expansion is increasing movement intensity."
    )

    supporting.append(
        "Directional context is changing across timeframes."
    )


elif primary_regime == "high_volatility":

    supporting.append(
        "Recent candle ranges are expanding."
    )


elif primary_regime == "low_volatility":

    supporting.append(
        "Recent candle ranges are contracting."
    )


elif primary_regime == "transition":

    supporting.append(
        "Short-term direction differs from broader direction."
    )

    supporting.append(
        "The market may be transitioning between regimes."
    )


if not supporting:
    supporting.append(
        "No single regime has dominant evidence."
    )


if not conflicting:
    conflicting.append(
        "No major conflicting regime evidence detected."
    )


# ============================================================
# EXPERIENCE INFORMATION
# ============================================================

experience_observations = 0
resolved_windows = 0
pending_windows = 0

if isinstance(adaptive_memory, dict):

    experience_observations = safe_int(
        adaptive_memory.get(
            "observations_count",
            adaptive_memory.get("total_observations", 0)
        )
    )

    resolved_windows = safe_int(
        adaptive_memory.get(
            "resolved_windows",
            0
        )
    )

    pending_windows = safe_int(
        adaptive_memory.get(
            "pending_windows",
            0
        )
    )


# ============================================================
# SAVE REGIME MEMORY
# ============================================================

regime_memory = {
    "mlai_version": "1.7",
    "engine": "Market Regime Detection Engine",

    "created_at": datetime.now(
        timezone.utc
    ).isoformat(),

    "market_source": metadata.get(
        "source",
        "unknown"
    ),

    "lookback": LOOKBACK,

    "current_regime": primary_regime,
    "regime_label": regime_label,
    "regime_strength": regime_strength,
    "regime_confidence": round(
        regime_confidence,
        2
    ),

    "scores": {
        key: round(value, 4)
        for key, value in scores.items()
    },

    "contexts": {
        "short": short_context,
        "medium": medium_context,
        "higher": higher_context,
    },

    "structures": {
        "short": short_structure,
        "medium": medium_structure,
        "higher": higher_structure,
    },

    "experience": {
        "observations": experience_observations,
        "resolved_windows": resolved_windows,
        "pending_windows": pending_windows,
    },

    "supporting_evidence": supporting,
    "conflicting_evidence": conflicting,

    "principles": [
        "Market regimes describe environments rather than guaranteed outcomes.",
        "Multiple timeframes are considered together.",
        "Structure and direction are evaluated separately.",
        "Momentum and volatility provide contextual evidence.",
        "Conflicting timeframe evidence is preserved.",
        "Historical memory does not guarantee future behaviour.",
        "Confidence represents evidence agreement rather than certainty.",
        "The engine does not create an automatic trading signal.",
    ],
}


REGIME_FILE = "mlai_regime_memory.bin"


with open(REGIME_FILE, "wb") as f:
    pickle.dump(
        regime_memory,
        f,
        protocol=pickle.HIGHEST_PROTOCOL
    )


print()
print(f"PASS: {REGIME_FILE} saved.")


# ============================================================
# OUTPUT
# ============================================================

print()
print("=" * 70)
print("MLAI v1.7 MARKET REGIME DETECTION ENGINE")
print("=" * 70)

print()
print("CURRENT MARKET REGIME")
print("-" * 70)

print(
    f"Regime                  : {regime_label}"
)

print(
    f"Regime strength         : {regime_strength}"
)

print(
    f"Regime confidence       : {regime_confidence:.1f}%"
)


print()
print("REGIME SCORES")
print("-" * 70)

print(
    f"Bullish trend           : "
    f"{scores['bullish_trend']:.3f}"
)

print(
    f"Bearish trend           : "
    f"{scores['bearish_trend']:.3f}"
)

print(
    f"Range                   : "
    f"{scores['range']:.3f}"
)

print(
    f"Breakout                : "
    f"{scores['breakout']:.3f}"
)

print(
    f"High volatility         : "
    f"{scores['high_volatility']:.3f}"
)

print(
    f"Low volatility          : "
    f"{scores['low_volatility']:.3f}"
)

print(
    f"Transition              : "
    f"{scores['transition']:.3f}"
)


print()
print("TIMEFRAME REGIME CONTEXT")
print("-" * 70)

print(
    f"Short                   : "
    f"{short_context['direction']} | "
    f"{short_structure['structure']}"
)

print(
    f"Medium                  : "
    f"{medium_context['direction']} | "
    f"{medium_structure['structure']}"
)

print(
    f"Higher                  : "
    f"{higher_context['direction']} | "
    f"{higher_structure['structure']}"
)


print()
print("SHORT CONTEXT")
print("-" * 70)

print(
    f"Direction               : "
    f"{short_context['direction']}"
)

print(
    f"Structure               : "
    f"{short_structure['structure']}"
)

print(
    f"Momentum                : "
    f"{short_context['momentum']}"
)

print(
    f"Volatility              : "
    f"{short_context['volatility']}"
)

print(
    f"Net change %            : "
    f"{short_context['net_change_pct']:.3f}%"
)


print()
print("MEDIUM CONTEXT")
print("-" * 70)

print(
    f"Direction               : "
    f"{medium_context['direction']}"
)

print(
    f"Structure               : "
    f"{medium_structure['structure']}"
)

print(
    f"Momentum                : "
    f"{medium_context['momentum']}"
)

print(
    f"Volatility              : "
    f"{medium_context['volatility']}"
)

print(
    f"Net change %            : "
    f"{medium_context['net_change_pct']:.3f}%"
)


print()
print("HIGHER CONTEXT")
print("-" * 70)

print(
    f"Direction               : "
    f"{higher_context['direction']}"
)

print(
    f"Structure               : "
    f"{higher_structure['structure']}"
)

print(
    f"Momentum                : "
    f"{higher_context['momentum']}"
)

print(
    f"Volatility              : "
    f"{higher_context['volatility']}"
)

print(
    f"Net change %            : "
    f"{higher_context['net_change_pct']:.3f}%"
)


print()
print("SUPPORTING REGIME EVIDENCE")
print("-" * 70)

for item in supporting:
    print(f"- {item}")


print()
print("CONFLICTING REGIME EVIDENCE")
print("-" * 70)

for item in conflicting:
    print(f"- {item}")


print()
print("EXPERIENCE MEMORY")
print("-" * 70)

print(
    f"Observations stored     : "
    f"{experience_observations}"
)

print(
    f"Resolved windows        : "
    f"{resolved_windows}"
)

print(
    f"Pending windows         : "
    f"{pending_windows}"
)


# ============================================================
# MARKET STORY
# ============================================================

story = (
    f"The MLAI v1.7 engine classifies the current market "
    f"environment as {regime_label}. "
    f"The short context is {short_context['direction']}, "
    f"the medium context is {medium_context['direction']}, "
    f"and the higher context is {higher_context['direction']}. "
    f"Medium-term structure is "
    f"{medium_structure['structure']}. "
    f"Momentum is "
    f"{medium_context['momentum']} and volatility is "
    f"{medium_context['volatility']}. "
    f"The detected regime has a calculated evidence "
    f"confidence of {regime_confidence:.1f}%. "
    f"Conflicting evidence is preserved rather than removed. "
    f"The regime describes the current market environment "
    f"and does not guarantee future price behaviour."
)


print()
print("CURRENT MARKET STORY")
print("-" * 70)
print(story)


# ============================================================
# PRINCIPLES
# ============================================================

print()
print("REGIME LEARNING PRINCIPLES")
print("-" * 70)

principles = [
    "Market regimes describe environments rather than guaranteed outcomes.",
    "Multiple timeframes are considered together.",
    "Structure and direction are evaluated separately.",
    "Momentum and volatility provide contextual evidence.",
    "Conflicting timeframe evidence is preserved.",
    "Historical memory does not guarantee future behaviour.",
    "Confidence represents evidence agreement rather than certainty.",
    "The engine does not create an automatic trading signal.",
]

for i, principle in enumerate(principles, 1):
    print(f"{i}. {principle}")


# ============================================================
# UPDATE PROJECT STATUS
# ============================================================

status_entry = f"""

## MLAI v1.7 - Market Regime Detection Engine

**Completed:** {datetime.now(timezone.utc).isoformat()}

### Current Regime

- Regime: `{regime_label}`
- Strength: `{regime_strength}`
- Evidence confidence: `{regime_confidence:.1f}%`

### Timeframe Context

- Short: `{short_context['direction']}`
- Medium: `{medium_context['direction']}`
- Higher: `{higher_context['direction']}`

### Structure

- Short: `{short_structure['structure']}`
- Medium: `{medium_structure['structure']}`
- Higher: `{higher_structure['structure']}`

### Market Context

- Momentum: `{medium_context['momentum']}`
- Volatility: `{medium_context['volatility']}`

### Learning Memory

- Observations: `{experience_observations}`
- Resolved windows: `{resolved_windows}`
- Pending windows: `{pending_windows}`

### Principle

MLAI v1.7 detects the current market environment/regime using multiple
timeframes, structure, momentum and volatility. Regime classification is
contextual evidence and is not treated as a guaranteed prediction or
automatic trading signal.
"""


try:

    with open(
        STATUS_FILE,
        "a",
        encoding="utf-8"
    ) as f:

        f.write(status_entry)

    print()
    print(
        "PASS: MLAI_PROJECT_STATUS.md updated."
    )

except Exception as exc:

    print()
    print(
        f"WARNING: Could not update "
        f"{STATUS_FILE}: {exc}"
    )


# ============================================================
# COMPLETE
# ============================================================

print()
print("=" * 70)
print(
    "PASS: MLAI v1.7 Market Regime Detection Engine completed."
)
print("=" * 70)