
import os
import pickle
from datetime import datetime, timezone


# ============================================================
# MLAI v2.8
# FAILURE-AWARE DECISION ENGINE
#
# v2.7:
#   Rebuilt historical decisions and identified failure patterns.
#
# v2.8:
#   Uses those historical failure patterns to evaluate the
#   CURRENT market context.
#
# IMPORTANT:
#   - No future candles are used for the current decision.
#   - Failure frequency does NOT automatically reverse direction.
#   - Failure evidence reduces trust/confidence.
#   - Historical failures are contextual evidence.
# ============================================================

VERSION = "2.8"

MARKET_FILE = "market_data.bin"
ERROR_MEMORY_FILE = "mlai_error_memory.bin"
FAILURE_MEMORY_FILE = "mlai_failure_aware_memory.bin"
STATUS_FILE = "MLAI_PROJECT_STATUS.md"

WINDOW = 60
HORIZONS = [4, 8, 16]

NEUTRAL_THRESHOLD = 0.0005

SEPARATOR = "=" * 70
LINE = "-" * 70


# ============================================================
# HELPERS
# ============================================================

def safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def get_value(obj, *names):
    if isinstance(obj, dict):
        for name in names:
            if name in obj:
                return obj[name]

    for name in names:
        if hasattr(obj, name):
            return getattr(obj, name)

    return None


def normalize_candle(raw):

    if isinstance(raw, dict):

        timestamp = get_value(
            raw,
            "timestamp",
            "datetime",
            "date",
            "time",
            "t"
        )

        open_price = get_value(
            raw,
            "open",
            "Open",
            "o"
        )

        high_price = get_value(
            raw,
            "high",
            "High",
            "h"
        )

        low_price = get_value(
            raw,
            "low",
            "Low",
            "l"
        )

        close_price = get_value(
            raw,
            "close",
            "Close",
            "c"
        )

        volume = get_value(
            raw,
            "volume",
            "Volume",
            "v"
        )

    elif isinstance(raw, (list, tuple)):

        if len(raw) < 5:
            return None

        timestamp = raw[0]
        open_price = raw[1]
        high_price = raw[2]
        low_price = raw[3]
        close_price = raw[4]
        volume = raw[5] if len(raw) > 5 else 0

    else:

        timestamp = get_value(
            raw,
            "timestamp",
            "datetime",
            "date",
            "time"
        )

        open_price = get_value(
            raw,
            "open",
            "Open"
        )

        high_price = get_value(
            raw,
            "high",
            "High"
        )

        low_price = get_value(
            raw,
            "low",
            "Low"
        )

        close_price = get_value(
            raw,
            "close",
            "Close"
        )

        volume = get_value(
            raw,
            "volume",
            "Volume"
        )

    open_price = safe_float(open_price, None)
    high_price = safe_float(high_price, None)
    low_price = safe_float(low_price, None)
    close_price = safe_float(close_price, None)

    if (
        open_price is None
        or high_price is None
        or low_price is None
        or close_price is None
    ):
        return None

    return {
        "timestamp": timestamp,
        "open": open_price,
        "high": high_price,
        "low": low_price,
        "close": close_price,
        "volume": safe_float(volume),
    }


def extract_candles(memory):

    candidates = []

    if isinstance(memory, (list, tuple)):
        candidates = list(memory)

    elif isinstance(memory, dict):

        for key in [
            "candles",
            "data",
            "market_data",
            "ohlcv",
            "records",
            "prices"
        ]:

            value = memory.get(key)

            if isinstance(value, (list, tuple)):
                candidates = list(value)
                break

    else:

        for attr in [
            "candles",
            "data",
            "market_data",
            "records",
            "prices"
        ]:

            value = getattr(memory, attr, None)

            if isinstance(value, (list, tuple)):
                candidates = list(value)
                break

    normalized = []

    for item in candidates:

        candle = normalize_candle(item)

        if candle is not None:
            normalized.append(candle)

    return normalized


# ============================================================
# LOAD MARKET MEMORY
# ============================================================

print()

print(SEPARATOR)
print("MLAI v2.8 - LOADING MARKET MEMORY")
print(SEPARATOR)

print()
print(f"File: {MARKET_FILE}")
print()

if not os.path.exists(MARKET_FILE):

    print("ERROR: market_data.bin not found.")
    raise SystemExit(1)

try:

    with open(
        MARKET_FILE,
        "rb"
    ) as f:

        market_memory = pickle.load(f)

    print(
        "PASS: market_data.bin loaded as MLAI memory object."
    )

except Exception as exc:

    print(
        f"ERROR: Unable to load market_data.bin: {exc}"
    )

    raise SystemExit(1)


candles = extract_candles(market_memory)

if len(candles) < WINDOW:

    print()
    print(
        f"ERROR: Need at least {WINDOW} candles. "
        f"Found {len(candles)}."
    )

    raise SystemExit(1)


print()
print(
    f"Found {len(candles)} stored candles."
)

print()
print(
    f"PASS: Using latest {WINDOW} candles."
)


# ============================================================
# CURRENT MARKET CONTEXT
# ============================================================

latest = candles[-WINDOW:]


def candle_direction(candle):

    if candle["close"] > candle["open"]:
        return "bullish"

    if candle["close"] < candle["open"]:
        return "bearish"

    return "neutral"


def calculate_context(window):

    closes = [
        c["close"]
        for c in window
    ]

    first_close = closes[0]
    latest_close = closes[-1]

    net_change = latest_close - first_close

    if first_close != 0:

        net_change_pct = (
            net_change
            / first_close
        )

    else:

        net_change_pct = 0.0


    bullish = 0
    bearish = 0
    neutral = 0

    for candle in window:

        direction = candle_direction(
            candle
        )

        if direction == "bullish":
            bullish += 1

        elif direction == "bearish":
            bearish += 1

        else:
            neutral += 1


    # --------------------------------------------------------
    # Direction
    # --------------------------------------------------------

    if net_change_pct > NEUTRAL_THRESHOLD:

        direction = "bullish"

    elif net_change_pct < -NEUTRAL_THRESHOLD:

        direction = "bearish"

    elif bullish > bearish:

        direction = "bullish"

    elif bearish > bullish:

        direction = "bearish"

    else:

        direction = "neutral"


    # --------------------------------------------------------
    # Structure
    # --------------------------------------------------------

    quarter = max(
        5,
        len(closes) // 4
    )

    q1 = closes[:quarter]
    q2 = closes[quarter:2 * quarter]
    q3 = closes[2 * quarter:3 * quarter]
    q4 = closes[-quarter:]


    q1_high = max(q1)
    q2_high = max(q2)
    q3_high = max(q3)
    q4_high = max(q4)

    q1_low = min(q1)
    q2_low = min(q2)
    q3_low = min(q3)
    q4_low = min(q4)


    higher_highs = (
        q2_high >= q1_high
        and q3_high >= q2_high
        and q4_high >= q3_high
    )

    higher_lows = (
        q2_low >= q1_low
        and q3_low >= q2_low
        and q4_low >= q3_low
    )


    lower_highs = (
        q2_high <= q1_high
        and q3_high <= q2_high
        and q4_high <= q3_high
    )

    lower_lows = (
        q2_low <= q1_low
        and q3_low <= q2_low
        and q4_low <= q3_low
    )


    if higher_highs and higher_lows:

        structure = "bullish_structure"

    elif lower_highs and lower_lows:

        structure = "bearish_structure"

    else:

        structure = "range_structure"


    # --------------------------------------------------------
    # Momentum
    # --------------------------------------------------------

    half = max(
        2,
        len(closes) // 2
    )

    first_half = closes[:half]
    second_half = closes[-half:]

    first_move = (
        first_half[-1]
        - first_half[0]
    )

    second_move = (
        second_half[-1]
        - second_half[0]
    )


    if (
        abs(first_move) > 0
        and abs(second_move)
        > abs(first_move) * 1.25
    ):

        momentum = "increasing"

    elif (
        abs(first_move) > 0
        and abs(second_move)
        < abs(first_move) * 0.75
    ):

        momentum = "decreasing"

    else:

        momentum = "stable"


    # --------------------------------------------------------
    # Volatility
    # --------------------------------------------------------

    ranges = []

    for candle in window:

        low = candle["low"]

        if low != 0:

            ranges.append(
                (
                    candle["high"]
                    - candle["low"]
                )
                / low
            )


    if len(ranges) >= 4:

        half_range = (
            len(ranges) // 2
        )

        old_vol = (
            sum(ranges[:half_range])
            / half_range
        )

        new_vol = (
            sum(ranges[-half_range:])
            / half_range
        )


        if new_vol > old_vol * 1.15:

            volatility = "expanding"

        elif new_vol < old_vol * 0.85:

            volatility = "contracting"

        else:

            volatility = "stable"

    else:

        volatility = "stable"


    # --------------------------------------------------------
    # Rejection
    # --------------------------------------------------------

    upper = 0
    lower = 0

    for candle in window:

        body_high = max(
            candle["open"],
            candle["close"]
        )

        body_low = min(
            candle["open"],
            candle["close"]
        )

        upper_wick = (
            candle["high"]
            - body_high
        )

        lower_wick = (
            body_low
            - candle["low"]
        )

        if upper_wick > lower_wick:
            upper += 1

        elif lower_wick > upper_wick:
            lower += 1


    if lower > upper:

        rejection = (
            "lower_rejection_dominant"
        )

    elif upper > lower:

        rejection = (
            "upper_rejection_dominant"
        )

    else:

        rejection = (
            "balanced_rejection"
        )


    return {
        "direction": direction,
        "structure": structure,
        "momentum": momentum,
        "volatility": volatility,
        "rejection": rejection,
        "first_close": first_close,
        "latest_close": latest_close,
        "net_change": net_change,
        "net_change_pct": net_change_pct,
        "bullish_candles": bullish,
        "bearish_candles": bearish,
        "neutral_candles": neutral,
    }


context = calculate_context(
    latest
)


# ============================================================
# LOAD v2.7 FAILURE MEMORY
# ============================================================

print()
print(
    "PASS: Loading v2.7 failure memory..."
)

if not os.path.exists(
    ERROR_MEMORY_FILE
):

    print(
        "ERROR: mlai_error_memory.bin not found."
    )

    print(
        "Run mlai_v27.py first."
    )

    raise SystemExit(1)


try:

    with open(
        ERROR_MEMORY_FILE,
        "rb"
    ) as f:

        error_memory = pickle.load(f)

    print(
        "PASS: Failure memory loaded."
    )

except Exception as exc:

    print(
        f"ERROR: Unable to load failure memory: {exc}"
    )

    raise SystemExit(1)


failure_patterns = error_memory.get(
    "failure_patterns",
    []
)

records = error_memory.get(
    "records",
    [])


print()
print(
    f"Failure patterns available: "
    f"{len(failure_patterns)}"
)

print(
    f"Detailed historical records: "
    f"{len(records)}"
)


# ============================================================
# CURRENT DECISION BASELINE
# ============================================================

bullish_score = 0.0
bearish_score = 0.0
neutral_score = 0.0


if context["direction"] == "bullish":

    bullish_score += 3.0

elif context["direction"] == "bearish":

    bearish_score += 3.0

else:

    neutral_score += 3.0


if context["structure"] == "bullish_structure":

    bullish_score += 2.0

elif context["structure"] == "bearish_structure":

    bearish_score += 2.0

else:

    neutral_score += 1.0


if context["momentum"] == "increasing":

    if context["direction"] == "bullish":

        bullish_score += 1.0

    elif context["direction"] == "bearish":

        bearish_score += 1.0

    else:

        neutral_score += 0.5


elif context["momentum"] == "decreasing":

    neutral_score += 0.5


if context["rejection"] == "lower_rejection_dominant":

    if context["direction"] == "bullish":

        bullish_score += 1.0


elif context["rejection"] == "upper_rejection_dominant":

    if context["direction"] == "bearish":

        bearish_score += 1.0


# ============================================================
# FAILURE MATCHING
# ============================================================

def pattern_matches(
    pattern,
    direction,
    structure,
    momentum,
    volatility,
    horizon
):

    return (
        pattern.get("predicted")
        == direction
        and
        pattern.get("structure")
        == structure
        and
        pattern.get("momentum")
        == momentum
        and
        pattern.get("volatility")
        == volatility
        and
        int(pattern.get("horizon", -1))
        == horizon
    )


matched_patterns = []

for horizon in HORIZONS:

    for pattern in failure_patterns:

        if pattern_matches(
            pattern,
            context["direction"],
            context["structure"],
            context["momentum"],
            context["volatility"],
            horizon
        ):

            matched_patterns.append(
                pattern
            )


# ============================================================
# FAILURE SEVERITY
# ============================================================

total_failure_count = sum(
    int(
        p.get(
            "failures",
            0
        )
    )
    for p in matched_patterns
)


# Calculate a bounded failure penalty.
#
# This is intentionally conservative.
#
# A failure pattern does NOT reverse the market direction.
# It only reduces confidence.
# ============================================================

if total_failure_count <= 0:

    failure_penalty = 0.0

elif total_failure_count < 50:

    failure_penalty = 0.05

elif total_failure_count < 100:

    failure_penalty = 0.10

elif total_failure_count < 200:

    failure_penalty = 0.15

else:

    failure_penalty = 0.20


# ============================================================
# FAILURE-AWARE ADJUSTMENT
# ============================================================

baseline_total = (
    bullish_score
    + bearish_score
    + neutral_score
)

if baseline_total <= 0:

    baseline_distribution = {
        "bullish": 1 / 3,
        "bearish": 1 / 3,
        "neutral": 1 / 3,
    }

else:

    baseline_distribution = {

        "bullish":
            bullish_score
            / baseline_total,

        "bearish":
            bearish_score
            / baseline_total,

        "neutral":
            neutral_score
            / baseline_total,
    }


# Reduce confidence of the current dominant direction.
#
# Do not manufacture a reversal.
# Move the removed weight into neutral.
# ============================================================

adjusted = dict(
    baseline_distribution
)

dominant_direction = max(
    adjusted,
    key=adjusted.get
)

removed = (
    adjusted[dominant_direction]
    * failure_penalty
)

adjusted[
    dominant_direction
] -= removed

adjusted[
    "neutral"
] += removed


# ============================================================
# NORMALIZE
# ============================================================

total = sum(
    adjusted.values()
)

if total <= 0:

    adjusted = {
        "bullish": 1 / 3,
        "bearish": 1 / 3,
        "neutral": 1 / 3,
    }

else:

    for key in adjusted:

        adjusted[key] /= total


primary_direction = max(
    adjusted,
    key=adjusted.get
)


# ============================================================
# CONFIDENCE
# ============================================================

sorted_distribution = sorted(
    adjusted.values(),
    reverse=True
)

if len(sorted_distribution) >= 2:

    evidence_confidence = (
        sorted_distribution[0]
        - sorted_distribution[1]
    )

else:

    evidence_confidence = 0.0


# Failure penalty directly reduces confidence.
final_confidence = max(
    0.0,
    evidence_confidence
)


if final_confidence >= 0.60:

    confidence_level = "high"

elif final_confidence >= 0.35:

    confidence_level = "moderate"

elif final_confidence >= 0.15:

    confidence_level = "low"

else:

    confidence_level = "very_low"


# ============================================================
# FAILURE INTERPRETATION
# ============================================================

if matched_patterns:

    failure_state = (
        "historical_failure_pattern_detected"
    )

else:

    failure_state = (
        "no_matching_failure_pattern"
    )


# ============================================================
# SAVE v2.8 MEMORY
# ============================================================

failure_aware_memory = {

    "version": VERSION,

    "created_at":
        datetime.now(
            timezone.utc
        ).isoformat(),

    "current_context": context,

    "baseline_distribution":
        baseline_distribution,

    "failure_aware_distribution":
        adjusted,

    "primary_direction":
        primary_direction,

    "evidence_confidence":
        evidence_confidence,

    "confidence_level":
        confidence_level,

    "failure_analysis": {

        "matched_patterns":
            matched_patterns,

        "matched_pattern_count":
            len(matched_patterns),

        "total_failure_count":
            total_failure_count,

        "failure_penalty":
            failure_penalty,

        "state":
            failure_state,
    },

    "principles": [
        "Failure patterns reduce trust rather than automatically reversing direction.",
        "Historical failures are contextual evidence.",
        "Future candles are not used for the current decision.",
        "Failure frequency is not future probability.",
        "No single failure pattern controls the decision.",
        "The engine does not create an automatic trading signal.",
    ],
}


with open(
    FAILURE_MEMORY_FILE,
    "wb"
) as f:

    pickle.dump(
        failure_aware_memory,
        f
    )


print()
print(
    "PASS: mlai_failure_aware_memory.bin saved."
)


# ============================================================
# DISPLAY
# ============================================================

print()
print(SEPARATOR)
print(
    "MLAI v2.8 FAILURE-AWARE DECISION ENGINE"
)
print(SEPARATOR)


print()
print("CURRENT MARKET CONTEXT")
print(LINE)

print(
    f"Direction              : "
    f"{context['direction']}"
)

print(
    f"Structure              : "
    f"{context['structure']}"
)

print(
    f"Momentum               : "
    f"{context['momentum']}"
)

print(
    f"Volatility             : "
    f"{context['volatility']}"
)

print(
    f"Rejection              : "
    f"{context['rejection']}"
)

print(
    f"Latest price           : "
    f"{context['latest_close']:.4f}"
)

print(
    f"Net change %           : "
    f"{context['net_change_pct'] * 100:.3f}%"
)


print()
print("BASELINE EVIDENCE")
print(LINE)

print(
    f"Bullish                : "
    f"{baseline_distribution['bullish'] * 100:.1f}%"
)

print(
    f"Bearish                : "
    f"{baseline_distribution['bearish'] * 100:.1f}%"
)

print(
    f"Neutral                : "
    f"{baseline_distribution['neutral'] * 100:.1f}%"
)


print()
print("FAILURE PATTERN ANALYSIS")
print(LINE)

print(
    f"Available patterns     : "
    f"{len(failure_patterns)}"
)

print(
    f"Matched patterns       : "
    f"{len(matched_patterns)}"
)

print(
    f"Historical failures    : "
    f"{total_failure_count}"
)

print(
    f"Failure penalty        : "
    f"{failure_penalty * 100:.1f}%"
)

print(
    f"Failure state          : "
    f"{failure_state}"
)


print()
print("FAILURE-AWARE DISTRIBUTION")
print(LINE)

print(
    f"Bullish                : "
    f"{adjusted['bullish'] * 100:.1f}%"
)

print(
    f"Bearish                : "
    f"{adjusted['bearish'] * 100:.1f}%"
)

print(
    f"Neutral                : "
    f"{adjusted['neutral'] * 100:.1f}%"
)


print()
print("FAILURE-AWARE DECISION")
print(LINE)

print(
    f"Primary direction      : "
    f"{primary_direction}"
)

print(
    f"Evidence confidence    : "
    f"{evidence_confidence * 100:.1f}%"
)

print(
    f"Confidence level       : "
    f"{confidence_level}"
)


print()
print("MATCHED FAILURE PATTERNS")
print(LINE)

if not matched_patterns:

    print(
        "No matching historical failure pattern."
    )

else:

    for index, pattern in enumerate(
        matched_patterns[:10],
        start=1
    ):

        print(
            f"{index:02d}. "
            f"prediction={pattern.get('predicted')} | "
            f"structure={pattern.get('structure')} | "
            f"momentum={pattern.get('momentum')} | "
            f"volatility={pattern.get('volatility')} | "
            f"horizon={pattern.get('horizon')} | "
            f"failures={pattern.get('failures')}"
        )


print()
print("INTERPRETATION")
print(LINE)

if failure_penalty == 0:

    print(
        "No matching historical failure pattern "
        "was found for the current context."
    )

    print(
        "The baseline evidence distribution is "
        "retained."
    )

else:

    print(
        "Historical failure patterns matching the "
        "current context were detected."
    )

    print(
        "MLAI reduced confidence in the dominant "
        "direction rather than automatically reversing it."
    )

    print(
        "The failure evidence is contextual and does "
        "not represent a future probability."
    )


print()
print("IMPORTANT CALIBRATION")
print(LINE)

print(
    "Failure frequency is NOT a prediction probability."
)

print(
    "Historical failure patterns do NOT guarantee "
    "future failure."
)

print(
    "A matching failure pattern reduces trust; it "
    "does not automatically create the opposite direction."
)

print(
    "The engine does NOT create a BUY/SELL signal."
)


print()
print("LEARNING PRINCIPLES")
print(LINE)

principles = [
    "v2.7 historical failure patterns are used as contextual evidence.",
    "Failure patterns reduce confidence rather than automatically reversing direction.",
    "Current decisions use only currently available market candles.",
    "Future candles are never used for the current decision.",
    "Historical failure frequency is not future probability.",
    "Failure patterns are evaluated by direction, structure, momentum, volatility and horizon.",
    "Multiple matching failures increase caution.",
    "No single historical failure pattern controls the interpretation.",
    "Failure evidence is separate from direct market evidence.",
    "Confidence is evidence agreement, not certainty.",
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


# ============================================================
# UPDATE STATUS
# ============================================================

status = f"""
# MLAI Project Status

## v2.8 Failure-Aware Decision Engine

Updated:
{datetime.now(timezone.utc).isoformat()}

### Current Context

Direction: {context["direction"]}
Structure: {context["structure"]}
Momentum: {context["momentum"]}
Volatility: {context["volatility"]}

### Failure Learning

Available failure patterns:
{len(failure_patterns)}

Matched failure patterns:
{len(matched_patterns)}

Historical failures matched:
{total_failure_count}

Failure penalty:
{failure_penalty * 100:.1f}%

### Failure-Aware Decision

Primary direction:
{primary_direction}

Bullish:
{adjusted["bullish"] * 100:.1f}%

Bearish:
{adjusted["bearish"] * 100:.1f}%

Neutral:
{adjusted["neutral"] * 100:.1f}%

Evidence confidence:
{evidence_confidence * 100:.1f}%

Confidence level:
{confidence_level}

### Architecture

v2.8 consumes the detailed failure patterns generated
by v2.7.

Failure patterns reduce confidence in matching contexts.
They do not automatically reverse the current direction.

No future candle is used for the current decision.

### Safety

MLAI v2.8 is an analysis and historical-learning engine.
It does not generate automatic BUY/SELL trading signals.
"""

try:

    with open(
        STATUS_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(status)

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


print()
print(SEPARATOR)
print(
    "PASS: MLAI v2.8 Failure-Aware Decision Engine completed."
)
print(SEPARATOR)
