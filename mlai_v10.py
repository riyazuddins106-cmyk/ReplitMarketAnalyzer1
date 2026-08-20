import os
import pickle
from statistics import mean


# ============================================================
# MLAI v1.0
# INTEGRATED MLAI BRAIN
#
# Purpose:
# Integrate the evidence layers developed in v0.x:
#
#   Candle Behaviour
#   Candle Relationships
#   Market Structure
#   Market Context
#   Pattern / Context Evidence
#   Historical Behaviour
#   Relationship + Reasoning
#   Market Story
#
# v1.0 produces:
#
#   Integrated market state
#   Directional bias
#   Evidence score
#   Confidence level
#   Supporting evidence
#   Conflicting evidence
#   Historical evidence
#   Structural evidence
#   Behaviour evidence
#   Momentum / volatility context
#   Confirmation conditions
#   Invalidation conditions
#   Integrated market story
#
# IMPORTANT:
# This is NOT a guaranteed prediction engine.
# This is NOT a financial advice engine.
# This is an evidence-integration engine.
# ============================================================


DATA_FILE = "market_data.bin"
STATUS_FILE = "MLAI_PROJECT_STATUS.md"

ANALYSIS_CANDLES = 60
HISTORICAL_SEQUENCE = 8
OUTCOME_WINDOW = 8

HISTORICAL_SIMILARITY_THRESHOLD = 0.60


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


def safe_mean(values):

    return mean(values) if values else 0.0


def percentage_change(first, last):

    if first == 0:
        return 0.0

    return ((last - first) / abs(first)) * 100.0


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
        ) - low
    )


# ============================================================
# LOAD MARKET MEMORY
# ============================================================

print("=" * 70)
print("MLAI v1.0 - LOADING MARKET MEMORY")
print("=" * 70)

print(f"File: {DATA_FILE}")
print()

if not os.path.exists(DATA_FILE):

    print("ERROR: market_data.bin not found.")
    raise SystemExit(1)


try:

    with open(DATA_FILE, "rb") as f:
        market_memory = pickle.load(f)

except Exception as e:

    print(f"ERROR: Could not load market_data.bin: {e}")
    raise SystemExit(1)


# ============================================================
# VALIDATE MLAI MEMORY OBJECT
# ============================================================

if not isinstance(market_memory, dict):

    print(
        "ERROR: market_data.bin does not contain "
        "an MLAI memory object."
    )

    raise SystemExit(1)


if "candles" not in market_memory:

    print(
        "ERROR: MLAI memory object does not contain "
        "a candles field."
    )

    raise SystemExit(1)


candles = market_memory["candles"]


if not isinstance(candles, (list, tuple)):

    print(
        "ERROR: MLAI memory candles field is not a list."
    )

    raise SystemExit(1)


candles = list(candles)


print("PASS: market_data.bin loaded as MLAI memory object.")
print()

print("MEMORY METADATA")
print("-" * 70)

print(
    f"MLAI version : "
    f"{market_memory.get('mlai_version', 'unknown')}"
)

print(
    f"Created at   : "
    f"{market_memory.get('created_at', 'unknown')}"
)

print(
    f"Source       : "
    f"{market_memory.get('source', 'unknown')}"
)

print()

print(f"Found {len(candles)} stored candles.")
print()


# ============================================================
# VALIDATE CANDLE COUNT
# ============================================================

if len(candles) < ANALYSIS_CANDLES:

    print(
        f"ERROR: Need at least {ANALYSIS_CANDLES} candles."
    )

    raise SystemExit(1)


recent = candles[-ANALYSIS_CANDLES:]


print(
    f"PASS: Using latest {len(recent)} candles."
)

print()

print("Analysing latest 60 candles...")
print()


# ============================================================
# ============================================================
# LAYER 1 — CANDLE BEHAVIOUR
# ============================================================
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


net_change = latest_close - first_close


net_change_pct = percentage_change(
    first_close,
    latest_close
)


if bullish_count > bearish_count:

    directional_character = "bullish"

elif bearish_count > bullish_count:

    directional_character = "bearish"

else:

    directional_character = "mixed_or_neutral"


# ============================================================
# FOLLOW THROUGH
# ============================================================

bullish_follow_through = 0
bearish_follow_through = 0
direction_changes = 0
failed_movements = 0


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

    if (
        previous in ("bullish", "bearish")
        and current in ("bullish", "bearish")
        and previous != current
    ):

        failed_movements += 1


# ============================================================
# REJECTION
# ============================================================

average_range = safe_mean(ranges)


upper_rejection_count = sum(
    1
    for x in upper_wicks
    if x > 0
    and x >= average_range * 0.20
)


lower_rejection_count = sum(
    1
    for x in lower_wicks
    if x > 0
    and x >= average_range * 0.20
)


if upper_rejection_count > lower_rejection_count:

    rejection_context = "upper_rejection_dominant"

elif lower_rejection_count > upper_rejection_count:

    rejection_context = "lower_rejection_dominant"

else:

    rejection_context = "balanced_rejection"


# ============================================================
# ============================================================
# LAYER 2 — MARKET STRUCTURE
# ============================================================
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

    structure_context = "bullish_structure"


elif (
    lower_highs > higher_highs
    and lower_lows >= higher_lows
):

    structure_context = "bearish_structure"


else:

    structure_context = "mixed_structure"


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
# ============================================================
# LAYER 3 — MARKET CONTEXT
# ============================================================
# ============================================================

early_ranges = ranges[:15]
recent_ranges = ranges[-15:]


early_bodies = bodies[:15]
recent_bodies = bodies[-15:]


early_range_avg = safe_mean(
    early_ranges
)


recent_range_avg = safe_mean(
    recent_ranges
)


early_body_avg = safe_mean(
    early_bodies
)


recent_body_avg = safe_mean(
    recent_bodies
)


if recent_range_avg > early_range_avg * 1.15:

    volatility_context = "expanding"

elif recent_range_avg < early_range_avg * 0.85:

    volatility_context = "contracting"

else:

    volatility_context = "stable"


if recent_body_avg > early_body_avg * 1.15:

    momentum_context = "increasing"

elif recent_body_avg < early_body_avg * 0.85:

    momentum_context = "decreasing"

else:

    momentum_context = "stable"


# ============================================================
# ============================================================
# LAYER 4 — HISTORICAL MEMORY
# ============================================================
# ============================================================

historical_matches = []


def historical_feature_vector(sequence):

    values = []

    for candle in sequence:

        o = get_value(
            candle,
            "open"
        )

        h = get_value(
            candle,
            "high"
        )

        l = get_value(
            candle,
            "low"
        )

        c = get_value(
            candle,
            "close"
        )

        rng = max(
            h - l,
            0.000001
        )


        values.extend(
            [
                (c - o) / rng,

                (
                    h -
                    max(o, c)
                ) / rng,

                (
                    min(o, c) -
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
            (1.0 + average_distance)
        )
    )


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


    current_features = (
        historical_feature_vector(
            current_sequence
        )
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
            start + HISTORICAL_SEQUENCE
        ]


        historical_features = (
            historical_feature_vector(
                historical_sequence
            )
        )


        sim = similarity(
            current_features,
            historical_features
        )


        if sim < HISTORICAL_SIMILARITY_THRESHOLD:

            continue


        outcome_start = (
            start
            +
            HISTORICAL_SEQUENCE
            -
            1
        )


        outcome_end = (
            outcome_start
            +
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
                    start
                    +
                    HISTORICAL_SEQUENCE
                    -
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
# ============================================================
# LAYER 5 — EVIDENCE FUSION
# ============================================================
# ============================================================

bullish_evidence = 0
bearish_evidence = 0


supporting_evidence = []
conflicting_evidence = []
neutral_evidence = []


# ------------------------------------------------------------
# CANDLE DIRECTION
# ------------------------------------------------------------

if directional_character == "bullish":

    bullish_evidence += 2

    supporting_evidence.append(
        "Bullish candle count is greater than bearish candle count."
    )


elif directional_character == "bearish":

    bearish_evidence += 2

    supporting_evidence.append(
        "Bearish candle count is greater than bullish candle count."
    )


else:

    neutral_evidence.append(
        "Bullish and bearish candle counts are relatively balanced."
    )


# ------------------------------------------------------------
# NET MOVEMENT
# ------------------------------------------------------------

if net_change > 0:

    bullish_evidence += 2

    supporting_evidence.append(
        f"Net price movement is upward by "
        f"{net_change_pct:.3f}%."
    )


elif net_change < 0:

    bearish_evidence += 2

    supporting_evidence.append(
        f"Net price movement is downward by "
        f"{abs(net_change_pct):.3f}%."
    )


else:

    neutral_evidence.append(
        "Net price movement is approximately flat."
    )


# ------------------------------------------------------------
# STRUCTURE
# ------------------------------------------------------------

if structure_context == "bullish_structure":

    bullish_evidence += 3

    supporting_evidence.append(
        "Market structure contains stronger higher-high "
        "and higher-low behaviour."
    )


elif structure_context == "bearish_structure":

    bearish_evidence += 3

    supporting_evidence.append(
        "Market structure contains stronger lower-high "
        "and lower-low behaviour."
    )


else:

    neutral_evidence.append(
        "Market structure is mixed."
    )


# ------------------------------------------------------------
# STRUCTURAL BREAK
# ------------------------------------------------------------

if bullish_break:

    bullish_evidence += 3

    supporting_evidence.append(
        "Latest close is above the latest detected swing high."
    )


if bearish_break:

    bearish_evidence += 3

    supporting_evidence.append(
        "Latest close is below the latest detected swing low."
    )


if not bullish_break and not bearish_break:

    neutral_evidence.append(
        "No current structural break is detected."
    )


# ------------------------------------------------------------
# REJECTION
# ------------------------------------------------------------

if rejection_context == "lower_rejection_dominant":

    if directional_character == "bullish":

        bullish_evidence += 1

        supporting_evidence.append(
            "Lower-price rejection is dominant while "
            "directional character is bullish."
        )

    else:

        conflicting_evidence.append(
            "Lower-price rejection is dominant but "
            "directional character is not bullish."
        )


elif rejection_context == "upper_rejection_dominant":

    if directional_character == "bearish":

        bearish_evidence += 1

        supporting_evidence.append(
            "Upper-price rejection is dominant while "
            "directional character is bearish."
        )

    else:

        conflicting_evidence.append(
            "Upper-price rejection is dominant but "
            "directional character is not bearish."
        )


# ------------------------------------------------------------
# FOLLOW THROUGH
# ------------------------------------------------------------

if bullish_follow_through > bearish_follow_through:

    bullish_evidence += 1

    supporting_evidence.append(
        "Bullish follow-through is stronger than bearish "
        "follow-through."
    )


elif bearish_follow_through > bullish_follow_through:

    bearish_evidence += 1

    supporting_evidence.append(
        "Bearish follow-through is stronger than bullish "
        "follow-through."
    )


else:

    neutral_evidence.append(
        "Bullish and bearish follow-through are balanced."
    )


# ------------------------------------------------------------
# FAILURE
# ------------------------------------------------------------

if failed_movements >= max(
    3,
    len(recent) // 8
):

    conflicting_evidence.append(
        f"{failed_movements} directional transitions "
        "were followed by opposite-direction candles."
    )


# ------------------------------------------------------------
# MOMENTUM
# ------------------------------------------------------------

if momentum_context == "increasing":

    if directional_character == "bullish":

        bullish_evidence += 1

        supporting_evidence.append(
            "Momentum is increasing within the bullish context."
        )

    elif directional_character == "bearish":

        bearish_evidence += 1

        supporting_evidence.append(
            "Momentum is increasing within the bearish context."
        )


elif momentum_context == "decreasing":

    conflicting_evidence.append(
        "Recent candle body strength is decreasing."
    )


# ------------------------------------------------------------
# HISTORICAL MEMORY
# ------------------------------------------------------------

if historical_total > 0:

    if (
        historical_bullish_pct
        >
        historical_bearish_pct
        and
        historical_bullish_pct
        >
        historical_neutral_pct
    ):

        bullish_evidence += 1

        supporting_evidence.append(
            f"Historical memory has a bullish-dominant outcome "
            f"frequency of {historical_bullish_pct:.1f}%."
        )


    elif (
        historical_bearish_pct
        >
        historical_bullish_pct
        and
        historical_bearish_pct
        >
        historical_neutral_pct
    ):

        bearish_evidence += 1

        supporting_evidence.append(
            f"Historical memory has a bearish-dominant outcome "
            f"frequency of {historical_bearish_pct:.1f}%."
        )


    else:

        conflicting_evidence.append(
            "Historical memory produces mixed outcome behaviour."
        )


else:

    neutral_evidence.append(
        "No sufficiently similar historical sequences were found."
    )


# ============================================================
# ============================================================
# INTEGRATED DIRECTION
# ============================================================
# ============================================================

if bullish_evidence > bearish_evidence:

    integrated_direction = "bullish"


elif bearish_evidence > bullish_evidence:

    integrated_direction = "bearish"


else:

    integrated_direction = "uncertain"


total_directional_evidence = (
    bullish_evidence
    +
    bearish_evidence
)


if total_directional_evidence > 0:

    if integrated_direction == "bullish":

        directional_strength = (
            bullish_evidence /
            total_directional_evidence
        ) * 100


    elif integrated_direction == "bearish":

        directional_strength = (
            bearish_evidence /
            total_directional_evidence
        ) * 100


    else:

        directional_strength = 50.0

else:

    directional_strength = 50.0


# ============================================================
# CONFIDENCE
# ============================================================

conflict_count = len(
    conflicting_evidence
)


support_count = len(
    supporting_evidence
)


base_confidence = directional_strength


conflict_penalty = min(
    conflict_count * 5,
    25
)


confidence = max(
    0.0,
    min(
        100.0,
        base_confidence -
        conflict_penalty
    )
)


if confidence >= 75:

    confidence_level = "high"


elif confidence >= 55:

    confidence_level = "moderate"


elif confidence >= 40:

    confidence_level = "low"


else:

    confidence_level = "very_low"


# ============================================================
# MARKET STATE
# ============================================================

if (
    integrated_direction == "bullish"
    and structure_context == "bullish_structure"
):

    market_state = (
        "bullish_structural_environment"
    )


elif (
    integrated_direction == "bearish"
    and structure_context == "bearish_structure"
):

    market_state = (
        "bearish_structural_environment"
    )


elif integrated_direction == "bullish":

    market_state = (
        "bullish_evidence_environment"
    )


elif integrated_direction == "bearish":

    market_state = (
        "bearish_evidence_environment"
    )


else:

    market_state = (
        "uncertain_or_conflicting_environment"
    )


# ============================================================
# CONFIRMATION CONDITIONS
# ============================================================

confirmation_conditions = []
invalidation_conditions = []


if integrated_direction == "bullish":

    confirmation_conditions.append(
        "Continued higher highs and higher lows would strengthen "
        "the integrated bullish interpretation."
    )

    confirmation_conditions.append(
        "Stronger bullish follow-through would increase "
        "directional evidence."
    )

    if not bullish_break:

        confirmation_conditions.append(
            "A confirmed break above the latest important swing high "
            "would provide additional structural confirmation."
        )


    invalidation_conditions.append(
        "A sustained break below an important recent swing low "
        "would weaken the bullish interpretation."
    )

    invalidation_conditions.append(
        "Repeated bullish failures followed by stronger bearish "
        "continuation would weaken the evidence."
    )


elif integrated_direction == "bearish":

    confirmation_conditions.append(
        "Continued lower highs and lower lows would strengthen "
        "the integrated bearish interpretation."
    )

    confirmation_conditions.append(
        "Stronger bearish follow-through would increase "
        "directional evidence."
    )

    if not bearish_break:

        confirmation_conditions.append(
            "A confirmed break below the latest important swing low "
            "would provide additional structural confirmation."
        )


    invalidation_conditions.append(
        "A sustained break above an important recent swing high "
        "would weaken the bearish interpretation."
    )

    invalidation_conditions.append(
        "Repeated bearish failures followed by stronger bullish "
        "continuation would weaken the evidence."
    )


else:

    confirmation_conditions.append(
        "A clean structural break followed by directional "
        "follow-through would help resolve uncertainty."
    )

    invalidation_conditions.append(
        "Continued alternating behaviour without structural "
        "progress would maintain uncertainty."
    )


# ============================================================
# INTEGRATED MARKET STORY
# ============================================================

story = []


story.append(
    f"The integrated MLAI analysis identifies the current "
    f"environment as {market_state}."
)


story.append(
    f"The dominant directional character is "
    f"{integrated_direction}."
)


story.append(
    f"Price has moved {net_change_pct:.3f}% across the "
    f"analysed {len(recent)}-candle context."
)


story.append(
    f"Market structure is classified as "
    f"{structure_context}."
)


story.append(
    f"Momentum is {momentum_context} and volatility is "
    f"{volatility_context}."
)


story.append(
    f"Rejection behaviour is "
    f"{rejection_context}."
)


if bullish_follow_through != bearish_follow_through:

    story.append(
        f"Follow-through currently favours "
        f"{'bullish' if bullish_follow_through > bearish_follow_through else 'bearish'} "
        f"behaviour."
    )


if historical_total > 0:

    story.append(
        f"The historical memory contains "
        f"{historical_total} similar sequences."
    )

    story.append(
        f"Those sequences produced "
        f"{historical_bullish_pct:.1f}% bullish, "
        f"{historical_bearish_pct:.1f}% bearish and "
        f"{historical_neutral_pct:.1f}% neutral outcomes."
    )


if failed_movements > 0:

    story.append(
        f"There are {failed_movements} directional transitions "
        f"where the following candle moved in the opposite direction, "
        f"showing incomplete short-term continuity."
    )


story.append(
    f"The integrated directional evidence score is "
    f"{bullish_evidence} bullish versus "
    f"{bearish_evidence} bearish."
)


story.append(
    f"Estimated evidence confidence is "
    f"{confidence:.1f}% ({confidence_level})."
)


if conflicting_evidence:

    story.append(
        "Conflicting evidence remains present, so the integrated "
        "interpretation must retain uncertainty."
    )


story.append(
    "The MLAI Brain combines observable evidence layers rather "
    "than treating any single candle, pattern or historical match "
    "as an automatic prediction."
)


integrated_story = " ".join(story)


# ============================================================
# PRINT RESULTS
# ============================================================

print("=" * 70)
print("MLAI v1.0 INTEGRATED MLAI BRAIN")
print("=" * 70)

print()

print("INTEGRATED MARKET STATE")
print("-" * 70)

print(
    f"Market state            : "
    f"{market_state}"
)

print(
    f"Integrated direction     : "
    f"{integrated_direction}"
)

print(
    f"Directional strength     : "
    f"{directional_strength:.1f}%"
)

print(
    f"Confidence               : "
    f"{confidence:.1f}%"
)

print(
    f"Confidence level         : "
    f"{confidence_level}"
)

print()

print("CURRENT MARKET EVIDENCE")
print("-" * 70)

print(
    f"Bullish candles          : "
    f"{bullish_count}"
)

print(
    f"Bearish candles          : "
    f"{bearish_count}"
)

print(
    f"Neutral candles          : "
    f"{neutral_count}"
)

print(
    f"Directional character    : "
    f"{directional_character}"
)

print()

print("PRICE CONTEXT")
print("-" * 70)

print(
    f"First close              : "
    f"{first_close:.4f}"
)

print(
    f"Latest close             : "
    f"{latest_close:.4f}"
)

print(
    f"Net movement             : "
    f"{net_change:.4f}"
)

print(
    f"Net change %             : "
    f"{net_change_pct:.3f}%"
)

print()

print("STRUCTURAL EVIDENCE")
print("-" * 70)

print(
    f"Swing highs              : "
    f"{len(swing_highs)}"
)

print(
    f"Swing lows               : "
    f"{len(swing_lows)}"
)

print(
    f"Higher highs             : "
    f"{higher_highs}"
)

print(
    f"Lower highs              : "
    f"{lower_highs}"
)

print(
    f"Higher lows              : "
    f"{higher_lows}"
)

print(
    f"Lower lows               : "
    f"{lower_lows}"
)

print(
    f"Structure                : "
    f"{structure_context}"
)

print()

print("STRUCTURAL BREAK")
print("-" * 70)

print(
    f"Bullish break            : "
    f"{bullish_break}"
)

print(
    f"Bearish break            : "
    f"{bearish_break}"
)

print(
    f"Latest swing high        : "
    f"{latest_swing_high if latest_swing_high is not None else 'None'}"
)

print(
    f"Latest swing low         : "
    f"{latest_swing_low if latest_swing_low is not None else 'None'}"
)

print()

print("BEHAVIOUR RELATIONSHIPS")
print("-" * 70)

print(
    f"Upper rejection          : "
    f"{upper_rejection_count}"
)

print(
    f"Lower rejection          : "
    f"{lower_rejection_count}"
)

print(
    f"Rejection context        : "
    f"{rejection_context}"
)

print(
    f"Bullish follow-through   : "
    f"{bullish_follow_through}"
)

print(
    f"Bearish follow-through   : "
    f"{bearish_follow_through}"
)

print(
    f"Failed movements         : "
    f"{failed_movements}"
)

print(
    f"Direction changes        : "
    f"{direction_changes}"
)

print()

print("MARKET CONTEXT")
print("-" * 70)

print(
    f"Momentum                 : "
    f"{momentum_context}"
)

print(
    f"Volatility               : "
    f"{volatility_context}"
)

print()

print("HISTORICAL MEMORY")
print("-" * 70)

print(
    f"Historical matches       : "
    f"{historical_total}"
)

print(
    f"Bullish outcomes         : "
    f"{historical_bullish}"
)

print(
    f"Bearish outcomes         : "
    f"{historical_bearish}"
)

print(
    f"Neutral outcomes         : "
    f"{historical_neutral}"
)

print(
    f"Bullish frequency        : "
    f"{historical_bullish_pct:.1f}%"
)

print(
    f"Bearish frequency        : "
    f"{historical_bearish_pct:.1f}%"
)

print(
    f"Neutral frequency        : "
    f"{historical_neutral_pct:.1f}%"
)

print()

print("BEST HISTORICAL MATCHES")
print("-" * 70)

for i, match in enumerate(
    historical_matches[:10],
    start=1
):

    print(
        f"{i:02d}. "
        f"Candles "
        f"{match['start']}→{match['end']} | "
        f"similarity="
        f"{match['similarity']:.3f} | "
        f"outcome="
        f"{match['outcome']} | "
        f"change="
        f"{match['change']:+.3f}%"
    )


if not historical_matches:

    print("No historical matches found.")


print()

print("EVIDENCE FUSION")
print("-" * 70)

print(
    f"Bullish evidence score  : "
    f"{bullish_evidence}"
)

print(
    f"Bearish evidence score  : "
    f"{bearish_evidence}"
)

print(
    f"Supporting evidence     : "
    f"{support_count}"
)

print(
    f"Conflicting evidence    : "
    f"{conflict_count}"
)

print()

print("SUPPORTING EVIDENCE")
print("-" * 70)

if supporting_evidence:

    for item in supporting_evidence:

        print(f"- {item}")

else:

    print("- None.")


print()

print("CONFLICTING EVIDENCE")
print("-" * 70)

if conflicting_evidence:

    for item in conflicting_evidence:

        print(f"- {item}")

else:

    print("- No major conflicting evidence detected.")


print()

print("NEUTRAL / ADDITIONAL EVIDENCE")
print("-" * 70)

if neutral_evidence:

    for item in neutral_evidence:

        print(f"- {item}")

else:

    print("- None.")


print()

print("CONFIRMATION CONDITIONS")
print("-" * 70)

for item in confirmation_conditions:

    print(f"- {item}")


print()

print("INVALIDATION CONDITIONS")
print("-" * 70)

for item in invalidation_conditions:

    print(f"- {item}")


print()

print("INTEGRATED MARKET STORY")
print("-" * 70)

print(integrated_story)


print()

print("MLAI BRAIN PRINCIPLES")
print("-" * 70)

print(
    "1. Multiple evidence layers are integrated."
)

print(
    "2. Observable market behaviour is separated from interpretation."
)

print(
    "3. Historical behaviour is treated as contextual evidence."
)

print(
    "4. Conflicting evidence is preserved."
)

print(
    "5. Confidence represents evidence agreement, not certainty."
)

print(
    "6. No single candle or pattern automatically determines the result."
)

print(
    "7. The system does not guarantee future market behaviour."
)

print()

print("=" * 70)


# ============================================================
# UPDATE PROJECT STATUS
# ============================================================

status_text = f"""
## MLAI v1.0 — Integrated MLAI Brain

Status: COMPLETED

Analysis candles: {len(recent)}

Integrated market state:
{market_state}

Integrated direction:
{integrated_direction}

Directional strength:
{directional_strength:.1f}%

Confidence:
{confidence:.1f}%

Confidence level:
{confidence_level}

Directional character:
{directional_character}

Structural context:
{structure_context}

Momentum:
{momentum_context}

Volatility:
{volatility_context}

Rejection context:
{rejection_context}

Bullish evidence score:
{bullish_evidence}

Bearish evidence score:
{bearish_evidence}

Supporting evidence:
{support_count}

Conflicting evidence:
{conflict_count}

Historical matches:
{historical_total}

Historical bullish frequency:
{historical_bullish_pct:.1f}%

Historical bearish frequency:
{historical_bearish_pct:.1f}%

Historical neutral frequency:
{historical_neutral_pct:.1f}%

### v1.0 Purpose

MLAI v1.0 is the first integrated reasoning layer.

It combines the evidence developed through the v0.x architecture:

- Candle behaviour
- Candle relationships
- Market structure
- Market context
- Pattern/context evidence
- Historical behaviour
- Relationship + reasoning
- Market story

The integrated brain produces:

- Market state
- Directional bias
- Directional evidence strength
- Evidence confidence
- Supporting evidence
- Conflicting evidence
- Historical context
- Confirmation conditions
- Invalidation conditions
- Integrated market story

Confidence is treated as an evidence-agreement measurement,
not as a guarantee of future market behaviour.

### Architecture Progress

v0.3.1  Candle Relationships              COMPLETED
v0.4    Market Structure                  COMPLETED
v0.5    Market Context                    COMPLETED
v0.6    Pattern / Context Engine          COMPLETED
v0.7    Historical Behaviour              COMPLETED
v0.8    Relationship + Reasoning Engine   COMPLETED
v0.9    Market Story Engine               COMPLETED
v1.0    Integrated MLAI Brain              COMPLETED

### Next Architecture

v1.1    Continuous Market Reader           NEXT
v1.2    Memory Update Engine               PENDING
v1.3    Learning / Outcome Tracking        PENDING
v1.4    Multi-timeframe Evidence            PENDING
v1.5    Advanced Market Structure           PENDING
v2.0    Full Continuous MLAI System        PENDING

### Important

MLAI v1.0 does not claim certainty or guaranteed prediction.

It integrates observable evidence into a structured market
interpretation while preserving uncertainty and conflicting evidence.
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

    print()
    print(
        f"PASS: {STATUS_FILE} updated."
    )

except Exception as e:

    print()
    print(
        f"WARNING: Could not update "
        f"{STATUS_FILE}: {e}"
    )


print()

print(
    "PASS: MLAI v1.0 Integrated MLAI Brain completed."
)

print("=" * 70)