import os
import pickle
from statistics import mean


# ============================================================
# MLAI v0.5 - MARKET CONTEXT ENGINE
# ============================================================
#
# Purpose:
#   Understand the context surrounding recent price behaviour.
#
# Pipeline:
#
#   Candle Data
#       ↓
#   Candle Relationships
#       ↓
#   Market Structure
#       ↓
#   MARKET CONTEXT  ← THIS VERSION
#       ↓
#   Pattern / Context Engine
#       ↓
#   Historical Behaviour
#       ↓
#   Reasoning
#       ↓
#   Market Story
#
# This version does NOT predict the market.
# It describes observable context and conflicting evidence.
# ============================================================


DATA_FILE = "market_data.bin"
STATUS_FILE = "MLAI_PROJECT_STATUS.md"

LOOKBACK = 30


# ============================================================
# HELPERS
# ============================================================

def get_value(candle, *names, default=None):
    """
    Safely retrieve a value from a candle.

    Supports dictionaries and objects.
    """
    if isinstance(candle, dict):
        for name in names:
            if name in candle:
                return candle[name]

    for name in names:
        if hasattr(candle, name):
            return getattr(candle, name)

    return default


def number(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def candle_values(candle):
    open_price = number(
        get_value(candle, "open", "Open", "o")
    )
    high = number(
        get_value(candle, "high", "High", "h")
    )
    low = number(
        get_value(candle, "low", "Low", "l")
    )
    close = number(
        get_value(candle, "close", "Close", "c")
    )

    return open_price, high, low, close


def candle_direction(candle):
    o, h, l, c = candle_values(candle)

    if c > o:
        return "bullish"
    elif c < o:
        return "bearish"

    return "neutral"


def candle_range(candle):
    o, h, l, c = candle_values(candle)
    return max(0.0, h - l)


def candle_body(candle):
    o, h, l, c = candle_values(candle)
    return abs(c - o)


def upper_wick(candle):
    o, h, l, c = candle_values(candle)
    return max(0.0, h - max(o, c))


def lower_wick(candle):
    o, h, l, c = candle_values(candle)
    return max(0.0, min(o, c) - l)


def percentage_change(first, last):
    if first == 0:
        return 0.0

    return ((last - first) / first) * 100.0


def classify_volatility(avg_range, reference_range):
    if reference_range <= 0:
        return "unknown"

    ratio = avg_range / reference_range

    if ratio >= 1.35:
        return "high_volatility"

    if ratio <= 0.70:
        return "low_volatility"

    return "normal_volatility"


# ============================================================
# LOAD MARKET MEMORY
# ============================================================

print("=" * 70)
print("MLAI v0.5 - LOADING MARKET MEMORY")
print("=" * 70)
print(f"File: {DATA_FILE}")


if not os.path.exists(DATA_FILE):
    print()
    print("ERROR: market_data.bin was not found.")
    print()
    print("Make sure you are running this from:")
    print("C:\\Users\\HomePC\\mlai-test")
    raise SystemExit(1)


try:
    with open(DATA_FILE, "rb") as f:
        market_data = pickle.load(f)
except Exception as e:
    print()
    print("ERROR: Could not load market_data.bin")
    print(f"Reason: {e}")
    raise SystemExit(1)


if isinstance(market_data, dict):
    for key in ("candles", "data", "market_data", "records"):
        if key in market_data and isinstance(market_data[key], list):
            market_data = market_data[key]
            break


if not isinstance(market_data, list):
    print()
    print("ERROR: market_data.bin does not contain a candle list.")
    raise SystemExit(1)


print("PASS: market_data.bin loaded")
print(f"Found {len(market_data)} stored candles.")
print()


if len(market_data) < LOOKBACK:
    print(
        f"ERROR: At least {LOOKBACK} candles are required "
        f"for v0.5 analysis."
    )
    raise SystemExit(1)


candles = market_data[-LOOKBACK:]


# ============================================================
# BASIC DATA
# ============================================================

directions = [candle_direction(c) for c in candles]
ranges = [candle_range(c) for c in candles]
bodies = [candle_body(c) for c in candles]
upper_wicks = [upper_wick(c) for c in candles]
lower_wicks = [lower_wick(c) for c in candles]


opens = [candle_values(c)[0] for c in candles]
highs = [candle_values(c)[1] for c in candles]
lows = [candle_values(c)[2] for c in candles]
closes = [candle_values(c)[3] for c in candles]


first_close = closes[0]
latest_close = closes[-1]

total_change = latest_close - first_close
total_change_percent = percentage_change(first_close, latest_close)


# ============================================================
# DIRECTION
# ============================================================

bullish_count = directions.count("bullish")
bearish_count = directions.count("bearish")
neutral_count = directions.count("neutral")


if bullish_count > bearish_count:
    directional_bias = "bullish"
elif bearish_count > bullish_count:
    directional_bias = "bearish"
else:
    directional_bias = "balanced"


# ============================================================
# EARLY / RECENT CONTEXT
# ============================================================

split = LOOKBACK // 2

early_ranges = ranges[:split]
recent_ranges = ranges[split:]

early_bodies = bodies[:split]
recent_bodies = bodies[split:]


early_avg_range = mean(early_ranges)
recent_avg_range = mean(recent_ranges)

early_avg_body = mean(early_bodies)
recent_avg_body = mean(recent_bodies)


range_change_percent = percentage_change(
    early_avg_range,
    recent_avg_range
)

body_change_percent = percentage_change(
    early_avg_body,
    recent_avg_body
)


# ============================================================
# VOLATILITY CONTEXT
# ============================================================

overall_avg_range = mean(ranges)

volatility_state = classify_volatility(
    recent_avg_range,
    overall_avg_range
)


if recent_avg_range > early_avg_range * 1.20:
    volatility_transition = "volatility_expansion"

elif recent_avg_range < early_avg_range * 0.80:
    volatility_transition = "volatility_contraction"

else:
    volatility_transition = "stable_volatility"


# ============================================================
# PRICE LOCATION
# ============================================================

range_high = max(highs)
range_low = min(lows)

range_size = range_high - range_low


if range_size > 0:
    location_percent = (
        (latest_close - range_low) / range_size
    ) * 100.0
else:
    location_percent = 50.0


if location_percent >= 80:
    price_location = "near_range_high"

elif location_percent <= 20:
    price_location = "near_range_low"

else:
    price_location = "middle_of_range"


# ============================================================
# RECENT HIGH / LOW PRESSURE
# ============================================================

recent_window = min(10, LOOKBACK)

recent_highs = highs[-recent_window:]
recent_lows = lows[-recent_window:]

recent_high = max(recent_highs)
recent_low = min(recent_lows)


near_recent_high = latest_close >= recent_high * 0.998
near_recent_low = latest_close <= recent_low * 1.002


# ============================================================
# WICK / REJECTION CONTEXT
# ============================================================

upper_rejection_count = 0
lower_rejection_count = 0


for candle in candles:
    r = candle_range(candle)

    if r <= 0:
        continue

    uw = upper_wick(candle)
    lw = lower_wick(candle)

    if uw >= r * 0.35:
        upper_rejection_count += 1

    if lw >= r * 0.35:
        lower_rejection_count += 1


if upper_rejection_count > lower_rejection_count:
    rejection_context = "upper_rejection_dominant"

elif lower_rejection_count > upper_rejection_count:
    rejection_context = "lower_rejection_dominant"

else:
    rejection_context = "balanced_rejection"


# ============================================================
# BODY STRENGTH CONTEXT
# ============================================================

large_body_count = 0
small_body_count = 0


body_reference = mean(bodies)


for body in bodies:
    if body >= body_reference * 1.40:
        large_body_count += 1

    elif body <= body_reference * 0.60:
        small_body_count += 1


if recent_avg_body > early_avg_body * 1.20:
    body_context = "directional_strength_increasing"

elif recent_avg_body < early_avg_body * 0.80:
    body_context = "directional_strength_decreasing"

else:
    body_context = "directional_strength_stable"


# ============================================================
# FOLLOW-THROUGH CONTEXT
# ============================================================

bullish_follow_through = 0
bearish_follow_through = 0
failed_directional_moves = 0


for i in range(1, len(candles)):
    previous = directions[i - 1]
    current = directions[i]

    if previous == "bullish" and current == "bullish":
        bullish_follow_through += 1

    elif previous == "bearish" and current == "bearish":
        bearish_follow_through += 1

    elif previous in ("bullish", "bearish") and current in (
        "bullish",
        "bearish"
    ):
        if previous != current:
            failed_directional_moves += 1


# ============================================================
# SEQUENCE STABILITY
# ============================================================

direction_changes = 0

for i in range(1, len(directions)):
    if (
        directions[i] != directions[i - 1]
        and directions[i] != "neutral"
        and directions[i - 1] != "neutral"
    ):
        direction_changes += 1


if direction_changes >= 10:
    sequence_state = "highly_alternating"

elif direction_changes >= 6:
    sequence_state = "frequently_alternating"

elif direction_changes <= 3:
    sequence_state = "relatively_stable"

else:
    sequence_state = "mixed"


# ============================================================
# TREND / RANGE CONTEXT
# ============================================================

first_high = highs[0]
last_high = highs[-1]

first_low = lows[0]
last_low = lows[-1]


higher_price_bias = last_high > first_high
lower_price_bias = last_low < first_low


if higher_price_bias and lower_price_bias:
    structural_context = "expanding_or_mixed"

elif higher_price_bias:
    structural_context = "upward_price_context"

elif lower_price_bias:
    structural_context = "downward_price_context"

else:
    structural_context = "stable_price_context"


# ============================================================
# CONTEXT INTERACTION
# ============================================================

context_flags = []


if directional_bias == "bearish":
    context_flags.append(
        "More bearish candles than bullish candles are present."
    )

elif directional_bias == "bullish":
    context_flags.append(
        "More bullish candles than bearish candles are present."
    )

else:
    context_flags.append(
        "Bullish and bearish candle counts are balanced."
    )


if volatility_transition == "volatility_contraction":
    context_flags.append(
        "Recent ranges are contracting relative to the earlier sequence."
    )

elif volatility_transition == "volatility_expansion":
    context_flags.append(
        "Recent ranges are expanding relative to the earlier sequence."
    )


if rejection_context == "upper_rejection_dominant":
    context_flags.append(
        "Upper rejection is more frequent than lower rejection."
    )

elif rejection_context == "lower_rejection_dominant":
    context_flags.append(
        "Lower rejection is more frequent than upper rejection."
    )


if sequence_state in (
    "highly_alternating",
    "frequently_alternating"
):
    context_flags.append(
        "Frequent directional changes indicate unstable short-term control."
    )


if failed_directional_moves >= 4:
    context_flags.append(
        "Multiple directional movements were followed by opposite candles."
    )


if price_location == "near_range_high":
    context_flags.append(
        "Latest price is positioned near the upper part of the observed range."
    )

elif price_location == "near_range_low":
    context_flags.append(
        "Latest price is positioned near the lower part of the observed range."
    )


# ============================================================
# CONTEXT CLASSIFICATION
# ============================================================

context_conditions = []


if directional_bias == "bearish":
    context_conditions.append("bearish_directional_context")

if directional_bias == "bullish":
    context_conditions.append("bullish_directional_context")

if volatility_transition == "volatility_contraction":
    context_conditions.append("contracting_volatility")

if volatility_transition == "volatility_expansion":
    context_conditions.append("expanding_volatility")

if rejection_context == "upper_rejection_dominant":
    context_conditions.append("upper_rejection_context")

if rejection_context == "lower_rejection_dominant":
    context_conditions.append("lower_rejection_context")

if price_location == "near_range_high":
    context_conditions.append("upper_range_location")

if price_location == "near_range_low":
    context_conditions.append("lower_range_location")

if sequence_state in (
    "highly_alternating",
    "frequently_alternating"
):
    context_conditions.append("unstable_short_term_sequence")


# ============================================================
# CONFLICT DETECTION
# ============================================================

conflicts = []


if directional_bias == "bearish" and total_change > 0:
    conflicts.append(
        "Candle-count direction is bearish while net price movement is positive."
    )

if directional_bias == "bullish" and total_change < 0:
    conflicts.append(
        "Candle-count direction is bullish while net price movement is negative."
    )

if directional_bias == "bearish" and lower_rejection_count > upper_rejection_count:
    conflicts.append(
        "Bearish candle dominance conflicts with stronger lower-price rejection."
    )

if directional_bias == "bullish" and upper_rejection_count > lower_rejection_count:
    conflicts.append(
        "Bullish candle dominance conflicts with stronger upper-price rejection."
    )

if volatility_transition == "volatility_contraction" and abs(total_change_percent) > 0.30:
    conflicts.append(
        "Price has moved directionally while movement intensity is contracting."
    )

if failed_directional_moves >= 5:
    conflicts.append(
        "Frequent directional failures make short-term control less certain."
    )


if conflicts:
    context_classification = "conflicting_market_context"

else:
    if directional_bias == "bearish":
        context_classification = "bearish_market_context"

    elif directional_bias == "bullish":
        context_classification = "bullish_market_context"

    else:
        context_classification = "balanced_market_context"


# ============================================================
# MARKET CONTEXT STORY
# ============================================================

story_parts = []


story_parts.append(
    f"The analysed {LOOKBACK}-candle context contains "
    f"{bullish_count} bullish candles, "
    f"{bearish_count} bearish candles, and "
    f"{neutral_count} neutral candles."
)


if total_change > 0:
    story_parts.append(
        f"Net price movement across the sequence is upward "
        f"by approximately {total_change:.4f} "
        f"({total_change_percent:.3f}%)."
    )

elif total_change < 0:
    story_parts.append(
        f"Net price movement across the sequence is downward "
        f"by approximately {abs(total_change):.4f} "
        f"({abs(total_change_percent):.3f}%)."
    )

else:
    story_parts.append(
        "Net price movement across the sequence is approximately flat."
    )


if volatility_transition == "volatility_contraction":
    story_parts.append(
        "Recent candle ranges are contracting, indicating reduced "
        "movement intensity compared with the earlier portion."
    )

elif volatility_transition == "volatility_expansion":
    story_parts.append(
        "Recent candle ranges are expanding, indicating increased "
        "movement intensity compared with the earlier portion."
    )

else:
    story_parts.append(
        "Recent candle ranges remain relatively stable."
    )


if body_context == "directional_strength_decreasing":
    story_parts.append(
        "Average candle bodies are decreasing, suggesting weaker "
        "directional efficiency in the recent sequence."
    )

elif body_context == "directional_strength_increasing":
    story_parts.append(
        "Average candle bodies are increasing, suggesting stronger "
        "directional movement in the recent sequence."
    )


if rejection_context == "upper_rejection_dominant":
    story_parts.append(
        "Upper rejection is dominant, showing repeated rejection "
        "of higher price excursions."
    )

elif rejection_context == "lower_rejection_dominant":
    story_parts.append(
        "Lower rejection is dominant, showing repeated rejection "
        "of lower price excursions."
    )


if sequence_state in (
    "highly_alternating",
    "frequently_alternating"
):
    story_parts.append(
        "Directional changes occur frequently, indicating that "
        "short-term control is unstable."
    )


if price_location == "near_range_high":
    story_parts.append(
        "Latest price is positioned near the upper portion of "
        "the observed range."
    )

elif price_location == "near_range_low":
    story_parts.append(
        "Latest price is positioned near the lower portion of "
        "the observed range."
    )


if failed_directional_moves >= 4:
    story_parts.append(
        f"{failed_directional_moves} directional movement transitions "
        "were followed by opposite-direction candles, indicating "
        "incomplete short-term follow-through."
    )


if conflicts:
    story_parts.append(
        "Conflicting evidence is present, so the context should "
        "not be reduced to a single directional conclusion."
    )


story_parts.append(
    "This interpretation describes observable price behaviour "
    "and does not prove hidden participant intentions."
)


market_story = " ".join(story_parts)


# ============================================================
# OUTPUT
# ============================================================

print()
print("Analysing latest 30 candles...")
print()

print("=" * 70)
print("MLAI v0.5 MARKET CONTEXT ANALYSIS")
print("=" * 70)

print(f"Candles analysed: {LOOKBACK}")
print()

print("DIRECTIONAL CONTEXT")
print("-" * 70)
print(f"Bullish candles : {bullish_count}")
print(f"Bearish candles : {bearish_count}")
print(f"Neutral candles : {neutral_count}")
print(f"Directional bias: {directional_bias}")
print()

print("PRICE MOVEMENT")
print("-" * 70)
print(f"First close: {first_close:.4f}")
print(f"Latest close: {latest_close:.4f}")
print(f"Net movement: {total_change:.4f}")
print(f"Net change %: {total_change_percent:.3f}%")
print()

print("VOLATILITY CONTEXT")
print("-" * 70)
print(f"Early average range : {early_avg_range:.4f}")
print(f"Recent average range: {recent_avg_range:.4f}")
print(f"Range change        : {range_change_percent:.2f}%")
print(f"Volatility state    : {volatility_state}")
print(f"Transition          : {volatility_transition}")
print()

print("BODY STRENGTH")
print("-" * 70)
print(f"Early average body : {early_avg_body:.4f}")
print(f"Recent average body: {recent_avg_body:.4f}")
print(f"Body change        : {body_change_percent:.2f}%")
print(f"Context            : {body_context}")
print(f"Large body candles : {large_body_count}")
print(f"Small body candles : {small_body_count}")
print()

print("PRICE LOCATION")
print("-" * 70)
print(f"Range high      : {range_high:.4f}")
print(f"Range low       : {range_low:.4f}")
print(f"Range size      : {range_size:.4f}")
print(f"Latest position : {location_percent:.2f}% of range")
print(f"Location        : {price_location}")
print()

print("REJECTION CONTEXT")
print("-" * 70)
print(f"Upper rejection count: {upper_rejection_count}")
print(f"Lower rejection count: {lower_rejection_count}")
print(f"Dominant context     : {rejection_context}")
print()

print("FOLLOW-THROUGH")
print("-" * 70)
print(f"Bullish follow-through : {bullish_follow_through}")
print(f"Bearish follow-through : {bearish_follow_through}")
print(f"Failed movement events : {failed_directional_moves}")
print()

print("SEQUENCE STABILITY")
print("-" * 70)
print(f"Direction changes: {direction_changes}")
print(f"Sequence state  : {sequence_state}")
print()

print("STRUCTURAL CONTEXT")
print("-" * 70)
print(f"First high → latest high: {first_high:.4f} → {last_high:.4f}")
print(f"First low  → latest low : {first_low:.4f} → {last_low:.4f}")
print(f"Context                 : {structural_context}")
print()

print("MARKET CONTEXT CLASSIFICATION")
print("-" * 70)
print(f"Classification: {context_classification}")
print()

print("CONTEXT CONDITIONS")
print("-" * 70)

if context_conditions:
    for condition in context_conditions:
        print(f"- {condition}")
else:
    print("- No dominant context condition detected.")

print()

print("CONTEXT EVIDENCE")
print("-" * 70)

for flag in context_flags:
    print(f"- {flag}")

print()

print("CONFLICTING EVIDENCE")
print("-" * 70)

if conflicts:
    for conflict in conflicts:
        print(f"- {conflict}")
else:
    print("- No major contextual conflict detected.")

print()

print("MARKET CONTEXT STORY")
print("-" * 70)
print(market_story)

print()
print("=" * 70)


# ============================================================
# UPDATE PROJECT STATUS
# ============================================================

status_entry = f"""
## MLAI v0.5 — Market Context

Status: COMPLETED

Input:
- market_data.bin
- Latest {LOOKBACK} candles

Context analysis implemented:
- Directional context
- Net price movement
- Volatility context
- Volatility expansion/contraction
- Candle body strength
- Price location within observed range
- Upper/lower rejection context
- Follow-through behaviour
- Failed directional movement detection
- Sequence stability
- Structural context
- Context condition classification
- Conflicting evidence detection
- Market Context Story generation

Important:
The engine describes observable price behaviour.
It does not claim hidden participant intentions.
It does not provide automatic trading signals.

Next stage:
MLAI v0.6 — Pattern / Context Engine
"""


try:
    with open(STATUS_FILE, "a", encoding="utf-8") as f:
        f.write("\n" + status_entry)

    print()
    print(f"PASS: {STATUS_FILE} updated.")
except Exception as e:
    print()
    print(f"WARNING: Could not update {STATUS_FILE}: {e}")


print()
print("PASS: MLAI v0.5 market context analysis completed.")