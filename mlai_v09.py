import os
import pickle
from statistics import mean


# ============================================================
# MLAI v0.9
# MARKET STORY ENGINE
#
# Purpose:
# Convert the evidence produced by previous MLAI layers into
# one structured, explainable market story.
#
# v0.9 connects:
#   Candle behaviour
#   Candle relationships
#   Market structure
#   Market context
#   Momentum
#   Volatility
#   Historical behaviour
#   Evidence balance
#   Confirmation conditions
#   Invalidation conditions
#
# IMPORTANT:
# This is NOT a trading signal engine.
# This is NOT a guaranteed prediction engine.
#
# v0.9 describes observable market behaviour and explains
# why the current interpretation was reached.
# ============================================================


DATA_FILE = "market_data.bin"
STATUS_FILE = "MLAI_PROJECT_STATUS.md"

ANALYSIS_CANDLES = 60

HISTORICAL_SEQUENCE = 8
OUTCOME_WINDOW = 8
HISTORICAL_MIN_SIMILARITY = 0.60

TOP_HISTORICAL_MATCHES = 10


# ============================================================
# BASIC HELPERS
# ============================================================

def get_value(candle, key, default=0.0):

    if isinstance(candle, dict):
        value = candle.get(key, default)
    else:
        value = getattr(candle, key, default)

    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def candle_direction(candle):

    o = get_value(candle, "open")
    c = get_value(candle, "close")

    if c > o:
        return "bullish"

    if c < o:
        return "bearish"

    return "neutral"


def candle_range(candle):

    return max(
        0.0,
        get_value(candle, "high") -
        get_value(candle, "low")
    )


def candle_body(candle):

    return abs(
        get_value(candle, "close") -
        get_value(candle, "open")
    )


def upper_wick(candle):

    high = get_value(candle, "high")

    return max(
        0.0,
        high -
        max(
            get_value(candle, "open"),
            get_value(candle, "close")
        )
    )


def lower_wick(candle):

    low = get_value(candle, "low")

    return max(
        0.0,
        min(
            get_value(candle, "open"),
            get_value(candle, "close")
        ) -
        low
    )


def percentage_change(first, last):

    if first == 0:
        return 0.0

    return (
        (last - first) /
        abs(first)
    ) * 100.0


def safe_mean(values):

    return mean(values) if values else 0.0


# ============================================================
# LOAD MARKET MEMORY
# ============================================================

print("=" * 70)
print("MLAI v0.9 - LOADING MARKET MEMORY")
print("=" * 70)

print(f"File: {DATA_FILE}")
print()


if not os.path.exists(DATA_FILE):

    print("ERROR: market_data.bin not found.")
    raise SystemExit(1)


try:

    with open(DATA_FILE, "rb") as f:
        market_data = pickle.load(f)

except Exception as e:

    print(
        f"ERROR: Could not load market_data.bin: {e}"
    )

    raise SystemExit(1)


# ============================================================
# SUPPORT CURRENT MLAI MEMORY FORMAT
# ============================================================

if isinstance(market_data, dict):

    candles = market_data.get("candles")

    if not isinstance(candles, (list, tuple)):

        print(
            "ERROR: market_data.bin dictionary does not "
            "contain a valid 'candles' list."
        )

        raise SystemExit(1)

    candles = list(candles)

    print(
        "PASS: market_data.bin loaded as MLAI memory object."
    )

    print()

    print("MEMORY METADATA")
    print("-" * 70)

    print(
        f"MLAI version : "
        f"{market_data.get('mlai_version', 'unknown')}"
    )

    print(
        f"Created at   : "
        f"{market_data.get('created_at', 'unknown')}"
    )

    print(
        f"Source       : "
        f"{market_data.get('source', 'unknown')}"
    )

    print()


elif isinstance(market_data, (list, tuple)):

    # Compatibility with older versions.

    candles = list(market_data)

    print(
        "PASS: market_data.bin loaded as legacy candle list."
    )

    print()


else:

    print(
        "ERROR: Unsupported market_data.bin format."
    )

    raise SystemExit(1)


print(
    f"Found {len(candles)} stored candles."
)

print()


if len(candles) < ANALYSIS_CANDLES:

    print(
        f"ERROR: Need at least {ANALYSIS_CANDLES} candles "
        "for v0.9 analysis."
    )

    raise SystemExit(1)


recent = candles[-ANALYSIS_CANDLES:]


print(
    f"PASS: Using latest {ANALYSIS_CANDLES} candles."
)

print()

print(
    f"Analysing latest {ANALYSIS_CANDLES} candles..."
)

print()


# ============================================================
# CURRENT CANDLE EVIDENCE
# ============================================================

directions = [
    candle_direction(c)
    for c in recent
]

bullish_count = directions.count("bullish")
bearish_count = directions.count("bearish")
neutral_count = directions.count("neutral")


ranges = [
    candle_range(c)
    for c in recent
]

bodies = [
    candle_body(c)
    for c in recent
]

upper_wicks = [
    upper_wick(c)
    for c in recent
]

lower_wicks = [
    lower_wick(c)
    for c in recent
]


first_close = get_value(
    recent[0],
    "close"
)

latest_close = get_value(
    recent[-1],
    "close"
)


net_change = (
    latest_close -
    first_close
)

net_change_pct = percentage_change(
    first_close,
    latest_close
)


# ============================================================
# CURRENT DIRECTION
# ============================================================

if bullish_count > bearish_count:

    current_direction = "bullish"

elif bearish_count > bullish_count:

    current_direction = "bearish"

else:

    current_direction = "mixed_or_neutral"


# ============================================================
# REJECTION CONTEXT
# ============================================================

average_range = safe_mean(ranges)

upper_rejection_count = sum(
    1
    for x in upper_wicks
    if x > 0 and
    x >= average_range * 0.20
)


lower_rejection_count = sum(
    1
    for x in lower_wicks
    if x > 0 and
    x >= average_range * 0.20
)


if upper_rejection_count > lower_rejection_count:

    rejection_context = (
        "upper_rejection_dominant"
    )

elif lower_rejection_count > upper_rejection_count:

    rejection_context = (
        "lower_rejection_dominant"
    )

else:

    rejection_context = (
        "balanced_rejection"
    )


# ============================================================
# FOLLOW THROUGH
# ============================================================

bullish_follow_through = 0
bearish_follow_through = 0
direction_changes = 0

for i in range(1, len(directions)):

    previous = directions[i - 1]
    current = directions[i]

    if (
        previous != current
        and previous != "neutral"
        and current != "neutral"
    ):

        direction_changes += 1

    if (
        previous == "bullish"
        and current == "bullish"
    ):

        bullish_follow_through += 1

    if (
        previous == "bearish"
        and current == "bearish"
    ):

        bearish_follow_through += 1


failed_movements = direction_changes


# ============================================================
# SWING STRUCTURE
# ============================================================

swing_highs = []
swing_lows = []


for i in range(1, len(recent) - 1):

    previous_high = get_value(
        recent[i - 1],
        "high"
    )

    current_high = get_value(
        recent[i],
        "high"
    )

    next_high = get_value(
        recent[i + 1],
        "high"
    )


    previous_low = get_value(
        recent[i - 1],
        "low"
    )

    current_low = get_value(
        recent[i],
        "low"
    )

    next_low = get_value(
        recent[i + 1],
        "low"
    )


    if (
        current_high > previous_high
        and current_high > next_high
    ):

        swing_highs.append(
            (i, current_high)
        )


    if (
        current_low < previous_low
        and current_low < next_low
    ):

        swing_lows.append(
            (i, current_low)
        )


higher_highs = 0
lower_highs = 0

higher_lows = 0
lower_lows = 0


for i in range(1, len(swing_highs)):

    previous = swing_highs[i - 1][1]
    current = swing_highs[i][1]

    if current > previous:

        higher_highs += 1

    elif current < previous:

        lower_highs += 1


for i in range(1, len(swing_lows)):

    previous = swing_lows[i - 1][1]
    current = swing_lows[i][1]

    if current > previous:

        higher_lows += 1

    elif current < previous:

        lower_lows += 1


if (
    higher_highs > lower_highs
    and higher_lows >= lower_lows
):

    structure_context = (
        "bullish_structure"
    )

elif (
    lower_highs > higher_highs
    and lower_lows >= higher_lows
):

    structure_context = (
        "bearish_structure"
    )

else:

    structure_context = (
        "mixed_structure"
    )


# ============================================================
# STRUCTURAL BREAK
# ============================================================

bullish_break = False
bearish_break = False

latest_swing_high = None
latest_swing_low = None


if swing_highs:

    latest_swing_high = swing_highs[-1][1]

    if latest_close > latest_swing_high:

        bullish_break = True


if swing_lows:

    latest_swing_low = swing_lows[-1][1]

    if latest_close < latest_swing_low:

        bearish_break = True


# ============================================================
# VOLATILITY
# ============================================================

early_ranges = ranges[:15]
recent_ranges = ranges[-15:]


early_range_avg = safe_mean(
    early_ranges
)

recent_range_avg = safe_mean(
    recent_ranges
)


if (
    recent_range_avg >
    early_range_avg * 1.15
):

    volatility_context = "expanding"

elif (
    recent_range_avg <
    early_range_avg * 0.85
):

    volatility_context = "contracting"

else:

    volatility_context = "stable"


# ============================================================
# MOMENTUM
# ============================================================

early_bodies = bodies[:15]
recent_bodies = bodies[-15:]


early_body_avg = safe_mean(
    early_bodies
)

recent_body_avg = safe_mean(
    recent_bodies
)


if (
    recent_body_avg >
    early_body_avg * 1.15
):

    momentum_context = "increasing"

elif (
    recent_body_avg <
    early_body_avg * 0.85
):

    momentum_context = "decreasing"

else:

    momentum_context = "stable"


# ============================================================
# HISTORICAL FEATURE VECTOR
# ============================================================

def feature_vector(sequence):

    values = []

    for c in sequence:

        o = get_value(c, "open")
        h = get_value(c, "high")
        l = get_value(c, "low")
        close = get_value(c, "close")

        rng = max(
            h - l,
            0.000001
        )

        values.extend(
            [
                (close - o) / rng,
                (
                    h -
                    max(o, close)
                ) / rng,
                (
                    min(o, close) -
                    l
                ) / rng,
                rng
            ]
        )

    return values


def similarity(a, b):

    if len(a) != len(b):

        return 0.0

    distances = []

    for x, y in zip(a, b):

        denominator = max(
            abs(x),
            abs(y),
            0.000001
        )

        distances.append(
            abs(x - y) /
            denominator
        )

    average_distance = safe_mean(
        distances
    )

    return max(
        0.0,
        min(
            1.0,
            1.0 /
            (
                1.0 +
                average_distance
            )
        )
    )


# ============================================================
# HISTORICAL ANALYSIS
# ============================================================

historical_matches = []


if (
    len(candles)
    >=
    ANALYSIS_CANDLES
    +
    HISTORICAL_SEQUENCE
    +
    OUTCOME_WINDOW
):

    current_sequence = recent[
        -HISTORICAL_SEQUENCE:
    ]

    current_features = feature_vector(
        current_sequence
    )


    search_limit = (
        len(candles)
        -
        HISTORICAL_SEQUENCE
        -
        OUTCOME_WINDOW
    )


    for start in range(
        0,
        search_limit
    ):

        historical_sequence = candles[
            start:
            start +
            HISTORICAL_SEQUENCE
        ]


        historical_features = feature_vector(
            historical_sequence
        )


        sim = similarity(
            current_features,
            historical_features
        )


        if sim < HISTORICAL_MIN_SIMILARITY:

            continue


        outcome_start = (
            start +
            HISTORICAL_SEQUENCE -
            1
        )

        outcome_end = (
            outcome_start +
            OUTCOME_WINDOW
        )


        if outcome_end >= len(candles):

            continue


        start_price = get_value(
            candles[outcome_start],
            "close"
        )

        end_price = get_value(
            candles[outcome_end],
            "close"
        )


        change = percentage_change(
            start_price,
            end_price
        )


        if change > 0.05:

            outcome = "bullish"

        elif change < -0.05:

            outcome = "bearish"

        else:

            outcome = "neutral"


        historical_matches.append(
            {
                "start": start,
                "end": (
                    start +
                    HISTORICAL_SEQUENCE -
                    1
                ),
                "similarity": sim,
                "outcome": outcome,
                "change": change
            }
        )


historical_matches.sort(
    key=lambda x: x["similarity"],
    reverse=True
)


historical_bullish = sum(
    1
    for x in historical_matches
    if x["outcome"] == "bullish"
)

historical_bearish = sum(
    1
    for x in historical_matches
    if x["outcome"] == "bearish"
)

historical_neutral = sum(
    1
    for x in historical_matches
    if x["outcome"] == "neutral"
)


historical_total = len(
    historical_matches
)


if historical_total > 0:

    historical_bullish_pct = (
        historical_bullish /
        historical_total
    ) * 100

    historical_bearish_pct = (
        historical_bearish /
        historical_total
    ) * 100

    historical_neutral_pct = (
        historical_neutral /
        historical_total
    ) * 100

else:

    historical_bullish_pct = 0.0
    historical_bearish_pct = 0.0
    historical_neutral_pct = 0.0


# ============================================================
# EVIDENCE COLLECTION
# ============================================================

supporting_evidence = []
conflicting_evidence = []
neutral_evidence = []


# Direction

if current_direction == "bullish":

    supporting_evidence.append(
        "More bullish candles than bearish candles "
        "are present."
    )

elif current_direction == "bearish":

    supporting_evidence.append(
        "More bearish candles than bullish candles "
        "are present."
    )

else:

    neutral_evidence.append(
        "Bullish and bearish candle counts are "
        "relatively balanced."
    )


# Net movement

if net_change > 0:

    supporting_evidence.append(
        f"Net price movement is upward by "
        f"approximately {net_change_pct:.3f}%."
    )

elif net_change < 0:

    supporting_evidence.append(
        f"Net price movement is downward by "
        f"approximately {abs(net_change_pct):.3f}%."
    )

else:

    neutral_evidence.append(
        "Net price movement is approximately flat."
    )


# Structure

if structure_context == "bullish_structure":

    supporting_evidence.append(
        "Recent swing structure contains stronger "
        "higher-high/higher-low behaviour."
    )

elif structure_context == "bearish_structure":

    supporting_evidence.append(
        "Recent swing structure contains stronger "
        "lower-high/lower-low behaviour."
    )

else:

    conflicting_evidence.append(
        "Swing structure contains mixed higher and "
        "lower structural movement."
    )


# Rejection

if rejection_context == "upper_rejection_dominant":

    if current_direction == "bearish":

        supporting_evidence.append(
            "Upper rejection is dominant while candle "
            "direction is bearish."
        )

    else:

        conflicting_evidence.append(
            "Upper rejection is dominant while overall "
            "direction is not bearish."
        )


elif rejection_context == "lower_rejection_dominant":

    if current_direction == "bullish":

        supporting_evidence.append(
            "Lower rejection is dominant while candle "
            "direction is bullish."
        )

    else:

        conflicting_evidence.append(
            "Lower rejection is dominant while overall "
            "direction is not bullish."
        )

else:

    neutral_evidence.append(
        "Upper and lower rejection are relatively balanced."
    )


# Follow-through

if (
    bullish_follow_through >
    bearish_follow_through
):

    supporting_evidence.append(
        "Bullish candle follow-through is stronger "
        "than bearish follow-through."
    )

elif (
    bearish_follow_through >
    bullish_follow_through
):

    supporting_evidence.append(
        "Bearish candle follow-through is stronger "
        "than bullish follow-through."
    )

else:

    neutral_evidence.append(
        "Bullish and bearish follow-through are "
        "relatively balanced."
    )


# Failed movements

if failed_movements >= max(
    3,
    len(recent) // 8
):

    conflicting_evidence.append(
        f"{failed_movements} directional movement "
        "transitions were followed by opposite-direction "
        "candles."
    )


# Momentum

if momentum_context == "increasing":

    neutral_evidence.append(
        "Recent candle bodies indicate increasing "
        "directional intensity."
    )

elif momentum_context == "decreasing":

    conflicting_evidence.append(
        "Recent candle bodies are becoming smaller, "
        "indicating decreasing directional intensity."
    )

else:

    neutral_evidence.append(
        "Recent candle body strength remains relatively stable."
    )


# Volatility

if volatility_context == "expanding":

    neutral_evidence.append(
        "Recent candle ranges are expanding."
    )

elif volatility_context == "contracting":

    neutral_evidence.append(
        "Recent candle ranges are contracting."
    )

else:

    neutral_evidence.append(
        "Recent candle ranges remain relatively stable."
    )


# Structural break

if bullish_break:

    supporting_evidence.append(
        "The latest close is above the most recent "
        "detected swing high."
    )


if bearish_break:

    supporting_evidence.append(
        "The latest close is below the most recent "
        "detected swing low."
    )


if not bullish_break and not bearish_break:

    neutral_evidence.append(
        "No clear current structural break is detected."
    )


# Historical evidence

if historical_total > 0:

    if historical_bullish_pct >= 55:

        supporting_evidence.append(
            f"Historical matches show bullish outcomes "
            f"at {historical_bullish_pct:.1f}%."
        )

    elif historical_bearish_pct >= 55:

        supporting_evidence.append(
            f"Historical matches show bearish outcomes "
            f"at {historical_bearish_pct:.1f}%."
        )

    else:

        conflicting_evidence.append(
            "Historical matches produce mixed bullish, "
            "bearish and neutral outcomes."
        )

else:

    neutral_evidence.append(
        "No sufficiently similar historical sequences "
        "were found."
    )


# ============================================================
# EVIDENCE BALANCE
# ============================================================

support_score = len(
    supporting_evidence
)

conflict_score = len(
    conflicting_evidence
)


if support_score >= conflict_score + 3:

    reasoning_state = (
        "supportive_evidence_dominant"
    )

elif conflict_score >= support_score + 3:

    reasoning_state = (
        "conflicting_evidence_dominant"
    )

else:

    reasoning_state = (
        "balanced_or_conflicting_evidence"
    )


# ============================================================
# CURRENT INTERPRETATION
# ============================================================

if reasoning_state == (
    "supportive_evidence_dominant"
):

    if current_direction == "bullish":

        interpretation = (
            "bullish_evidence_dominant"
        )

    elif current_direction == "bearish":

        interpretation = (
            "bearish_evidence_dominant"
        )

    else:

        interpretation = (
            "directional_evidence_present_but_unclear"
        )


elif reasoning_state == (
    "conflicting_evidence_dominant"
):

    interpretation = (
        "conflicting_market_evidence"
    )

else:

    interpretation = (
        "mixed_market_evidence"
    )


# ============================================================
# MARKET STATE
# ============================================================

if (
    current_direction == "bullish"
    and structure_context == "bullish_structure"
):

    market_state = "bullish_structural_environment"

elif (
    current_direction == "bearish"
    and structure_context == "bearish_structure"
):

    market_state = "bearish_structural_environment"

elif (
    current_direction == "bullish"
    and structure_context == "mixed_structure"
):

    market_state = "bullish_direction_mixed_structure"

elif (
    current_direction == "bearish"
    and structure_context == "mixed_structure"
):

    market_state = "bearish_direction_mixed_structure"

else:

    market_state = "mixed_market_environment"


# ============================================================
# CONFIRMATION CONDITIONS
# ============================================================

confirmation_conditions = []

invalidation_conditions = []


if current_direction == "bullish":

    confirmation_conditions.append(
        "Continued higher highs and higher lows would "
        "strengthen the bullish interpretation."
    )

    confirmation_conditions.append(
        "Bullish candles with stronger follow-through "
        "would strengthen the evidence."
    )

    if bullish_break:

        confirmation_conditions.append(
            "Acceptance above the structural break level "
            "would strengthen the bullish structural reading."
        )

    invalidation_conditions.append(
        "A sustained break below an important recent "
        "swing low would weaken the bullish interpretation."
    )

    invalidation_conditions.append(
        "Repeated bullish failures followed by stronger "
        "bearish continuation would weaken the interpretation."
    )


elif current_direction == "bearish":

    confirmation_conditions.append(
        "Continued lower highs and lower lows would "
        "strengthen the bearish interpretation."
    )

    confirmation_conditions.append(
        "Bearish candles with stronger follow-through "
        "would strengthen the evidence."
    )

    if bearish_break:

        confirmation_conditions.append(
            "Acceptance below the structural break level "
            "would strengthen the bearish structural reading."
        )

    invalidation_conditions.append(
        "A sustained break above an important recent "
        "swing high would weaken the bearish interpretation."
    )

    invalidation_conditions.append(
        "Repeated bearish failures followed by stronger "
        "bullish continuation would weaken the interpretation."
    )


else:

    confirmation_conditions.append(
        "A clean structural break followed by "
        "follow-through would help resolve the current uncertainty."
    )

    confirmation_conditions.append(
        "A sustained directional sequence would provide "
        "stronger evidence than alternating candles."
    )

    invalidation_conditions.append(
        "Additional alternating behaviour without "
        "structural progress would maintain uncertainty."
    )


# ============================================================
# MARKET STORY GENERATION
# ============================================================

story_parts = []


# Opening

if current_direction == "bullish":

    story_parts.append(
        "The current market sequence shows a bullish "
        "directional character."
    )

elif current_direction == "bearish":

    story_parts.append(
        "The current market sequence shows a bearish "
        "directional character."
    )

else:

    story_parts.append(
        "The current market sequence does not show "
        "a strong single directional character."
    )


# Price movement

if net_change > 0:

    story_parts.append(
        f"Price has moved upward by approximately "
        f"{net_change_pct:.3f}% across the analysed context."
    )

elif net_change < 0:

    story_parts.append(
        f"Price has moved downward by approximately "
        f"{abs(net_change_pct):.3f}% across the analysed context."
    )

else:

    story_parts.append(
        "Net price movement across the analysed context "
        "is approximately flat."
    )


# Structure

if structure_context == "bullish_structure":

    story_parts.append(
        "The detected swing structure supports the "
        "bullish interpretation through stronger higher-high "
        "and higher-low behaviour."
    )

elif structure_context == "bearish_structure":

    story_parts.append(
        "The detected swing structure supports the "
        "bearish interpretation through stronger lower-high "
        "and lower-low behaviour."
    )

else:

    story_parts.append(
        "The detected swing structure is mixed and therefore "
        "does not provide clean directional confirmation."
    )


# Rejection

if rejection_context == "lower_rejection_dominant":

    story_parts.append(
        "Lower-price rejection is dominant, indicating that "
        "lower prices have repeatedly encountered buying "
        "response within this sample."
    )

elif rejection_context == "upper_rejection_dominant":

    story_parts.append(
        "Upper-price rejection is dominant, indicating that "
        "higher prices have repeatedly encountered selling "
        "response within this sample."
    )

else:

    story_parts.append(
        "Upper and lower rejection are relatively balanced."
    )


# Momentum

if momentum_context == "increasing":

    story_parts.append(
        "Candle body strength is increasing, indicating "
        "greater recent directional intensity."
    )

elif momentum_context == "decreasing":

    story_parts.append(
        "Candle body strength is decreasing, indicating "
        "reduced recent directional intensity."
    )

else:

    story_parts.append(
        "Candle body strength remains relatively stable."
    )


# Volatility

if volatility_context == "expanding":

    story_parts.append(
        "Candle ranges are expanding, so recent movement "
        "intensity is increasing."
    )

elif volatility_context == "contracting":

    story_parts.append(
        "Candle ranges are contracting, so recent movement "
        "intensity is decreasing."
    )

else:

    story_parts.append(
        "Candle ranges remain relatively stable."
    )


# Follow-through

if (
    bullish_follow_through >
    bearish_follow_through
):

    story_parts.append(
        "Bullish follow-through is stronger than bearish "
        "follow-through in the analysed sequence."
    )

elif (
    bearish_follow_through >
    bullish_follow_through
):

    story_parts.append(
        "Bearish follow-through is stronger than bullish "
        "follow-through in the analysed sequence."
    )

else:

    story_parts.append(
        "Bullish and bearish follow-through are relatively balanced."
    )


# Failures

if failed_movements > 0:

    story_parts.append(
        f"There are {failed_movements} directional transitions "
        "where the following candle moved in the opposite "
        "direction, showing that short-term movement is not "
        "completely continuous."
    )


# Historical

if historical_total > 0:

    story_parts.append(
        f"The historical memory contains {historical_total} "
        "similar sequences."
    )

    story_parts.append(
        f"Those historical sequences produced "
        f"{historical_bullish_pct:.1f}% bullish, "
        f"{historical_bearish_pct:.1f}% bearish and "
        f"{historical_neutral_pct:.1f}% neutral outcomes."
    )

    story_parts.append(
        "Historical outcomes are treated as contextual evidence "
        "rather than guaranteed future behaviour."
    )

else:

    story_parts.append(
        "No sufficiently similar historical sequences were found."
    )


# Evidence conflict

if conflict_score > 0:

    story_parts.append(
        "Conflicting evidence is present, so the market story "
        "must retain uncertainty instead of forcing a single "
        "certain conclusion."
    )


# Final interpretation

if interpretation == "bullish_evidence_dominant":

    story_parts.append(
        "Overall, the observable evidence currently favours "
        "a bullish interpretation."
    )

elif interpretation == "bearish_evidence_dominant":

    story_parts.append(
        "Overall, the observable evidence currently favours "
        "a bearish interpretation."
    )

elif interpretation == "conflicting_market_evidence":

    story_parts.append(
        "Overall, the evidence is conflicting and does not "
        "support a clean directional interpretation."
    )

else:

    story_parts.append(
        "Overall, the evidence is mixed and should be treated "
        "as an unresolved market condition."
    )


# ============================================================
# PRINT RESULTS
# ============================================================

print("=" * 70)
print("MLAI v0.9 MARKET STORY ENGINE")
print("=" * 70)

print(
    f"Candles analysed       : {len(recent)}"
)

print()


print("MARKET STATE")
print("-" * 70)

print(
    f"Market state            : {market_state}"
)

print(
    f"Directional character   : {current_direction}"
)

print(
    f"Structural context      : {structure_context}"
)

print(
    f"Interpretation          : {interpretation}"
)

print()


print("PRICE CONTEXT")
print("-" * 70)

print(
    f"First close             : {first_close:.4f}"
)

print(
    f"Latest close            : {latest_close:.4f}"
)

print(
    f"Net movement            : {net_change:.4f}"
)

print(
    f"Net change %            : {net_change_pct:.3f}%"
)

print()


print("CANDLE BEHAVIOUR")
print("-" * 70)

print(
    f"Bullish candles         : {bullish_count}"
)

print(
    f"Bearish candles         : {bearish_count}"
)

print(
    f"Neutral candles         : {neutral_count}"
)

print()


print("STRUCTURE")
print("-" * 70)

print(
    f"Swing highs             : {len(swing_highs)}"
)

print(
    f"Swing lows              : {len(swing_lows)}"
)

print(
    f"Higher highs            : {higher_highs}"
)

print(
    f"Lower highs             : {lower_highs}"
)

print(
    f"Higher lows             : {higher_lows}"
)

print(
    f"Lower lows              : {lower_lows}"
)

print(
    f"Structure               : {structure_context}"
)

print()


print("STRUCTURAL BREAK")
print("-" * 70)

print(
    f"Bullish break           : {bullish_break}"
)

print(
    f"Bearish break           : {bearish_break}"
)

if latest_swing_high is not None:

    print(
        f"Latest swing high      : "
        f"{latest_swing_high:.4f}"
    )

else:

    print(
        "Latest swing high      : unavailable"
    )


if latest_swing_low is not None:

    print(
        f"Latest swing low       : "
        f"{latest_swing_low:.4f}"
    )

else:

    print(
        "Latest swing low       : unavailable"
    )

print()


print("BEHAVIOUR RELATIONSHIPS")
print("-" * 70)

print(
    f"Upper rejection         : "
    f"{upper_rejection_count}"
)

print(
    f"Lower rejection         : "
    f"{lower_rejection_count}"
)

print(
    f"Rejection context       : "
    f"{rejection_context}"
)

print(
    f"Bullish follow-through  : "
    f"{bullish_follow_through}"
)

print(
    f"Bearish follow-through  : "
    f"{bearish_follow_through}"
)

print(
    f"Failed movements        : "
    f"{failed_movements}"
)

print(
    f"Direction changes       : "
    f"{direction_changes}"
)

print()


print("MARKET CONTEXT")
print("-" * 70)

print(
    f"Momentum                : "
    f"{momentum_context}"
)

print(
    f"Volatility              : "
    f"{volatility_context}"
)

print()


print("HISTORICAL MEMORY")
print("-" * 70)

print(
    f"Historical matches      : "
    f"{historical_total}"
)

print(
    f"Bullish outcomes        : "
    f"{historical_bullish}"
)

print(
    f"Bearish outcomes        : "
    f"{historical_bearish}"
)

print(
    f"Neutral outcomes        : "
    f"{historical_neutral}"
)

print(
    f"Bullish frequency       : "
    f"{historical_bullish_pct:.1f}%"
)

print(
    f"Bearish frequency       : "
    f"{historical_bearish_pct:.1f}%"
)

print(
    f"Neutral frequency       : "
    f"{historical_neutral_pct:.1f}%"
)

print()


print("BEST HISTORICAL MATCHES")
print("-" * 70)

if historical_matches:

    for number, match in enumerate(
        historical_matches[
            :TOP_HISTORICAL_MATCHES
        ],
        start=1
    ):

        print(
            f"{number:02d}. "
            f"Candles "
            f"{match['start']}→{match['end']} | "
            f"similarity="
            f"{match['similarity']:.3f} | "
            f"outcome="
            f"{match['outcome']} | "
            f"change="
            f"{match['change']:+.3f}%"
        )

else:

    print(
        "No historical matches available."
    )

print()


print("SUPPORTING EVIDENCE")
print("-" * 70)

if supporting_evidence:

    for item in supporting_evidence:

        print(
            f"- {item}"
        )

else:

    print(
        "- No strong supporting evidence detected."
    )

print()


print("CONFLICTING EVIDENCE")
print("-" * 70)

if conflicting_evidence:

    for item in conflicting_evidence:

        print(
            f"- {item}"
        )

else:

    print(
        "- No major conflicting evidence detected."
    )

print()


print("NEUTRAL / ADDITIONAL EVIDENCE")
print("-" * 70)

if neutral_evidence:

    for item in neutral_evidence:

        print(
            f"- {item}"
        )

else:

    print(
        "- None."
    )

print()


print("EVIDENCE BALANCE")
print("-" * 70)

print(
    f"Supporting evidence    : "
    f"{support_score}"
)

print(
    f"Conflicting evidence   : "
    f"{conflict_score}"
)

print(
    f"Reasoning state        : "
    f"{reasoning_state}"
)

print()


print("CURRENT INTERPRETATION")
print("-" * 70)

print(
    f"Classification: "
    f"{interpretation}"
)

print()


print("CONFIRMATION CONDITIONS")
print("-" * 70)

for item in confirmation_conditions:

    print(
        f"- {item}"
    )

print()


print("INVALIDATION CONDITIONS")
print("-" * 70)

for item in invalidation_conditions:

    print(
        f"- {item}"
    )

print()


# ============================================================
# MARKET STORY
# ============================================================

print("MARKET STORY")
print("-" * 70)

print(
    " ".join(story_parts)
)

print()


# ============================================================
# REASONING PRINCIPLES
# ============================================================

print("REASONING PRINCIPLES")
print("-" * 70)

print(
    "1. Observable price behaviour is separated from interpretation."
)

print(
    "2. Multiple evidence layers are considered together."
)

print(
    "3. Conflicting evidence is preserved rather than hidden."
)

print(
    "4. Historical behaviour describes previous observations "
    "and does not guarantee future behaviour."
)

print(
    "5. The market story is explanatory, not a guaranteed prediction."
)

print(
    "6. No single candle or pattern is treated as an automatic signal."
)

print()


print("=" * 70)


# ============================================================
# UPDATE PROJECT STATUS
# ============================================================

status_text = f"""
## MLAI v0.9 — Market Story Engine

Status: COMPLETED

Analysis candles:
{len(recent)}

Market state:
{market_state}

Current directional character:
{current_direction}

Structural context:
{structure_context}

Rejection context:
{rejection_context}

Momentum:
{momentum_context}

Volatility:
{volatility_context}

Bullish candles:
{bullish_count}

Bearish candles:
{bearish_count}

Neutral candles:
{neutral_count}

Net change:
{net_change:.4f}

Net change percentage:
{net_change_pct:.3f}%

Supporting evidence:
{support_score}

Conflicting evidence:
{conflict_score}

Historical matches:
{historical_total}

Historical bullish frequency:
{historical_bullish_pct:.1f}%

Historical bearish frequency:
{historical_bearish_pct:.1f}%

Historical neutral frequency:
{historical_neutral_pct:.1f}%

Reasoning state:
{reasoning_state}

Current interpretation:
{interpretation}

### v0.9 Purpose

MLAI v0.9 converts the previously developed evidence
layers into a structured market story.

The engine connects:

- Candle behaviour
- Candle relationships
- Market structure
- Market context
- Momentum
- Volatility
- Structural breaks
- Historical behaviour
- Evidence balance
- Confirmation conditions
- Invalidation conditions

The output is designed to answer:

- What is currently happening?
- What observable evidence supports that interpretation?
- What evidence conflicts with it?
- What has happened in similar historical situations?
- What would strengthen the current interpretation?
- What would weaken or invalidate the interpretation?

The market story is explanatory rather than a guaranteed prediction.

### Architecture Progress

v0.3.1  Candle Relationships              COMPLETED
v0.4    Market Structure                  COMPLETED
v0.5    Market Context                    COMPLETED
v0.6    Pattern / Context Engine          COMPLETED
v0.7    Historical Behaviour              COMPLETED
v0.8    Relationship + Reasoning Engine   COMPLETED
v0.9    Market Story Engine               COMPLETED
v1.0    Integrated MLAI Brain              NEXT
Final   Continuous Data + Memory +
        Analysis + Learning                PENDING
"""


try:

    with open(
        STATUS_FILE,
        "a",
        encoding="utf-8"
    ) as f:

        f.write(
            "\n" +
            status_text
        )

    print(
        f"PASS: {STATUS_FILE} updated."
    )

except Exception as e:

    print(
        f"WARNING: Could not update "
        f"{STATUS_FILE}: {e}"
    )


print()

print(
    "PASS: MLAI v0.9 Market Story Engine completed."
)

print("=" * 70)