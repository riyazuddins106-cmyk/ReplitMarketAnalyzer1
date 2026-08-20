import os
import pickle
from datetime import datetime, timezone
from statistics import mean


# ============================================================
# MLAI v1.1
# LEARNING + EXPERIENCE MEMORY ENGINE
#
# Purpose:
#   Build persistent MLAI experience memory.
#
# v1.1 connects:
#   Market Memory
#   Current Evidence
#   Integrated Reasoning
#   Market Story
#   Historical Evidence
#   Observation Memory
#   Future Outcome Tracking
#
# IMPORTANT:
#   This version does NOT automatically claim prediction accuracy.
#   It records observations and later outcomes as separate evidence.
#
# Files:
#   market_data.bin
#       Existing market candle memory.
#
#   mlai_experience.bin
#       Persistent MLAI experience / observation memory.
#
#   MLAI_PROJECT_STATUS.md
#       Project progress documentation.
# ============================================================


DATA_FILE = "market_data.bin"
EXPERIENCE_FILE = "mlai_experience.bin"
STATUS_FILE = "MLAI_PROJECT_STATUS.md"

ANALYSIS_CANDLES = 60

# Future observation windows.
# These are measured in candles, not minutes.
OUTCOME_WINDOWS = [4, 8, 16]

# Maximum number of experience records to display.
DISPLAY_EXPERIENCES = 10


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


def utc_now():

    return datetime.now(
        timezone.utc
    ).isoformat()


# ============================================================
# LOAD MARKET MEMORY
# ============================================================

print("=" * 70)
print("MLAI v1.1 - LOADING MARKET MEMORY")
print("=" * 70)

print(f"File: {DATA_FILE}")
print()

if not os.path.exists(DATA_FILE):

    print(
        "ERROR: market_data.bin not found."
    )

    raise SystemExit(1)


try:

    with open(
        DATA_FILE,
        "rb"
    ) as f:

        market_data = pickle.load(f)

except Exception as e:

    print(
        f"ERROR: Could not load market_data.bin: {e}"
    )

    raise SystemExit(1)


# ============================================================
# SUPPORT BOTH CURRENT MLAI MEMORY FORMATS
# ============================================================

memory_metadata = {}

if isinstance(market_data, dict):

    print(
        "PASS: market_data.bin loaded as MLAI memory object."
    )

    memory_metadata = market_data

    if "candles" not in market_data:

        print(
            "ERROR: MLAI memory object does not contain 'candles'."
        )

        raise SystemExit(1)

    candles = list(
        market_data["candles"]
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

else:

    print(
        "PASS: Legacy candle-list memory detected."
    )

    if not isinstance(
        market_data,
        (list, tuple)
    ):

        print(
            "ERROR: market_data.bin does not contain candles."
        )

        raise SystemExit(1)

    candles = list(
        market_data
    )


print()
print(
    f"Found {len(candles)} stored candles."
)

print()


# ============================================================
# VALIDATE CANDLE COUNT
# ============================================================

if len(candles) < ANALYSIS_CANDLES:

    print(
        f"ERROR: Need at least "
        f"{ANALYSIS_CANDLES} candles."
    )

    raise SystemExit(1)


recent = candles[
    -ANALYSIS_CANDLES:
]


print(
    f"PASS: Using latest {ANALYSIS_CANDLES} candles."
)

print()
print(
    "Analysing latest 60 candles..."
)

print()


# ============================================================
# CURRENT MARKET EVIDENCE
# ============================================================

directions = [
    candle_direction(c)
    for c in recent
]

bullish_count = directions.count(
    "bullish"
)

bearish_count = directions.count(
    "bearish"
)

neutral_count = directions.count(
    "neutral"
)


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
# DIRECTIONAL CHARACTER
# ============================================================

if bullish_count > bearish_count:

    current_direction = "bullish"

elif bearish_count > bullish_count:

    current_direction = "bearish"

else:

    current_direction = "mixed_or_neutral"


# ============================================================
# STRUCTURE
# ============================================================

swing_highs = []
swing_lows = []


for i in range(
    1,
    len(recent) - 1
):

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
        and
        current_high > next_high
    ):

        swing_highs.append(
            (
                i,
                current_high
            )
        )


    if (
        current_low < previous_low
        and
        current_low < next_low
    ):

        swing_lows.append(
            (
                i,
                current_low
            )
        )


higher_highs = 0
lower_highs = 0

higher_lows = 0
lower_lows = 0


for i in range(
    1,
    len(swing_highs)
):

    previous = swing_highs[
        i - 1
    ][1]

    current = swing_highs[
        i
    ][1]


    if current > previous:

        higher_highs += 1

    elif current < previous:

        lower_highs += 1


for i in range(
    1,
    len(swing_lows)
):

    previous = swing_lows[
        i - 1
    ][1]

    current = swing_lows[
        i
    ][1]


    if current > previous:

        higher_lows += 1

    elif current < previous:

        lower_lows += 1


if (
    higher_highs > lower_highs
    and
    higher_lows >= lower_lows
):

    structure_context = (
        "bullish_structure"
    )

elif (
    lower_highs > higher_highs
    and
    lower_lows >= higher_lows
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

    latest_swing_high = (
        swing_highs[-1][1]
    )

    if latest_close > latest_swing_high:

        bullish_break = True


if swing_lows:

    latest_swing_low = (
        swing_lows[-1][1]
    )

    if latest_close < latest_swing_low:

        bearish_break = True


# ============================================================
# REJECTION
# ============================================================

average_range = safe_mean(
    ranges
)

upper_rejection_count = sum(
    1
    for value in upper_wicks
    if (
        value > 0
        and
        value >= average_range * 0.20
    )
)

lower_rejection_count = sum(
    1
    for value in lower_wicks
    if (
        value > 0
        and
        value >= average_range * 0.20
    )
)


if (
    upper_rejection_count >
    lower_rejection_count
):

    rejection_context = (
        "upper_rejection_dominant"
    )

elif (
    lower_rejection_count >
    upper_rejection_count
):

    rejection_context = (
        "lower_rejection_dominant"
    )

else:

    rejection_context = (
        "balanced_rejection"
    )


# ============================================================
# FOLLOW-THROUGH
# ============================================================

bullish_follow_through = 0
bearish_follow_through = 0
failed_movements = 0
direction_changes = 0


for i in range(
    1,
    len(directions)
):

    previous = directions[
        i - 1
    ]

    current = directions[
        i
    ]


    if (
        previous != current
        and
        previous != "neutral"
        and
        current != "neutral"
    ):

        direction_changes += 1


    if (
        previous == "bullish"
        and
        current == "bullish"
    ):

        bullish_follow_through += 1


    if (
        previous == "bearish"
        and
        current == "bearish"
    ):

        bearish_follow_through += 1


    if (
        previous in (
            "bullish",
            "bearish"
        )
        and
        current in (
            "bullish",
            "bearish"
        )
        and
        previous != current
    ):

        failed_movements += 1


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


if recent_body_avg > (
    early_body_avg * 1.15
):

    momentum_context = (
        "increasing"
    )

elif recent_body_avg < (
    early_body_avg * 0.85
):

    momentum_context = (
        "decreasing"
    )

else:

    momentum_context = (
        "stable"
    )


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


if recent_range_avg > (
    early_range_avg * 1.15
):

    volatility_context = (
        "expanding"
    )

elif recent_range_avg < (
    early_range_avg * 0.85
):

    volatility_context = (
        "contracting"
    )

else:

    volatility_context = (
        "stable"
    )


# ============================================================
# MARKET STATE
# ============================================================

if (
    structure_context ==
    "bullish_structure"
    and
    current_direction ==
    "bullish"
):

    market_state = (
        "bullish_structural_environment"
    )

elif (
    structure_context ==
    "bearish_structure"
    and
    current_direction ==
    "bearish"
):

    market_state = (
        "bearish_structural_environment"
    )

elif (
    current_direction ==
    "bullish"
):

    market_state = (
        "bullish_directional_environment"
    )

elif (
    current_direction ==
    "bearish"
):

    market_state = (
        "bearish_directional_environment"
    )

else:

    market_state = (
        "mixed_or_uncertain_environment"
    )


# ============================================================
# EVIDENCE FUSION
# ============================================================

bullish_score = 0
bearish_score = 0

supporting_evidence = []
conflicting_evidence = []
neutral_evidence = []


# Direction
if current_direction == "bullish":

    bullish_score += 2

    supporting_evidence.append(
        "Bullish candle count is greater than bearish candle count."
    )

elif current_direction == "bearish":

    bearish_score += 2

    supporting_evidence.append(
        "Bearish candle count is greater than bullish candle count."
    )


# Net movement
if net_change > 0:

    bullish_score += 2

    supporting_evidence.append(
        f"Net price movement is upward by "
        f"{net_change_pct:.3f}%."
    )

elif net_change < 0:

    bearish_score += 2

    supporting_evidence.append(
        f"Net price movement is downward by "
        f"{abs(net_change_pct):.3f}%."
    )


# Structure
if structure_context == "bullish_structure":

    bullish_score += 3

    supporting_evidence.append(
        "Market structure contains stronger "
        "higher-high and higher-low behaviour."
    )

elif structure_context == "bearish_structure":

    bearish_score += 3

    supporting_evidence.append(
        "Market structure contains stronger "
        "lower-high and lower-low behaviour."
    )

else:

    neutral_evidence.append(
        "Market structure is mixed."
    )


# Rejection
if (
    rejection_context ==
    "lower_rejection_dominant"
):

    if current_direction == "bullish":

        bullish_score += 1

        supporting_evidence.append(
            "Lower-price rejection is dominant "
            "within the bullish context."
        )

    else:

        neutral_evidence.append(
            "Lower-price rejection is dominant."
        )


elif (
    rejection_context ==
    "upper_rejection_dominant"
):

    if current_direction == "bearish":

        bearish_score += 1

        supporting_evidence.append(
            "Upper-price rejection is dominant "
            "within the bearish context."
        )

    else:

        neutral_evidence.append(
            "Upper-price rejection is dominant."
        )


# Follow-through
if (
    bullish_follow_through >
    bearish_follow_through
):

    bullish_score += 1

    supporting_evidence.append(
        "Bullish follow-through is stronger "
        "than bearish follow-through."
    )

elif (
    bearish_follow_through >
    bullish_follow_through
):

    bearish_score += 1

    supporting_evidence.append(
        "Bearish follow-through is stronger "
        "than bullish follow-through."
    )


# Momentum
if momentum_context == "increasing":

    if current_direction == "bullish":

        bullish_score += 1

    elif current_direction == "bearish":

        bearish_score += 1

    neutral_evidence.append(
        "Momentum is increasing."
    )

elif momentum_context == "decreasing":

    neutral_evidence.append(
        "Momentum is decreasing."
    )


# Volatility
neutral_evidence.append(
    f"Volatility is {volatility_context}."
)


# Failed movements
if failed_movements >= 10:

    conflicting_evidence.append(
        f"{failed_movements} directional transitions "
        "were followed by opposite-direction candles."
    )


# Structural break
if bullish_break:

    bullish_score += 2

    supporting_evidence.append(
        "Latest close is above the latest detected swing high."
    )

elif bearish_break:

    bearish_score += 2

    supporting_evidence.append(
        "Latest close is below the latest detected swing low."
    )

else:

    neutral_evidence.append(
        "No current structural break is detected."
    )


# ============================================================
# INTEGRATED DIRECTION
# ============================================================

if bullish_score > bearish_score:

    integrated_direction = "bullish"

elif bearish_score > bullish_score:

    integrated_direction = "bearish"

else:

    integrated_direction = "mixed"


total_direction_score = (
    bullish_score +
    bearish_score
)


if total_direction_score > 0:

    directional_strength = (
        abs(
            bullish_score -
            bearish_score
        )
        /
        total_direction_score
    ) * 100

else:

    directional_strength = 0.0


# ============================================================
# EXPERIENCE MEMORY
# ============================================================

print("=" * 70)
print("MLAI v1.1 LEARNING + EXPERIENCE MEMORY ENGINE")
print("=" * 70)

print()


# ============================================================
# LOAD EXISTING EXPERIENCE MEMORY
# ============================================================

experience_memory = None


if os.path.exists(
    EXPERIENCE_FILE
):

    try:

        with open(
            EXPERIENCE_FILE,
            "rb"
        ) as f:

            experience_memory = (
                pickle.load(f)
            )

        if not isinstance(
            experience_memory,
            dict
        ):

            experience_memory = None

    except Exception:

        experience_memory = None


if experience_memory is None:

    experience_memory = {

        "mlai_version": "1.1",

        "created_at": utc_now(),

        "updated_at": utc_now(),

        "records": [],

        "statistics": {

            "total_observations": 0,

            "resolved_4": 0,

            "resolved_8": 0,

            "resolved_16": 0,

            "bullish_observations": 0,

            "bearish_observations": 0,

            "mixed_observations": 0,

            "bullish_confirmations_4": 0,

            "bullish_confirmations_8": 0,

            "bullish_confirmations_16": 0,

            "bearish_confirmations_4": 0,

            "bearish_confirmations_8": 0,

            "bearish_confirmations_16": 0,

        }

    }

    print(
        "PASS: Created new MLAI experience memory."
    )

else:

    print(
        "PASS: Existing MLAI experience memory loaded."
    )


records = experience_memory.setdefault(
    "records",
    []
)


statistics = experience_memory.setdefault(
    "statistics",
    {}
)


# ============================================================
# IDENTIFY CURRENT OBSERVATION
# ============================================================

observation_id = (
    f"obs_{len(records) + 1:06d}"
)


current_observation = {

    "observation_id":
        observation_id,

    "timestamp":
        utc_now(),

    "market_source":
        memory_metadata.get(
            "source",
            "unknown"
        ),

    "candle_count":
        len(recent),

    "market_candle_index":
        len(candles) - 1,

    "first_close":
        first_close,

    "latest_close":
        latest_close,

    "net_change":
        net_change,

    "net_change_pct":
        net_change_pct,

    "bullish_candles":
        bullish_count,

    "bearish_candles":
        bearish_count,

    "neutral_candles":
        neutral_count,

    "directional_character":
        current_direction,

    "market_state":
        market_state,

    "integrated_direction":
        integrated_direction,

    "bullish_score":
        bullish_score,

    "bearish_score":
        bearish_score,

    "directional_strength":
        directional_strength,

    "structure":
        structure_context,

    "swing_highs":
        len(swing_highs),

    "swing_lows":
        len(swing_lows),

    "higher_highs":
        higher_highs,

    "lower_highs":
        lower_highs,

    "higher_lows":
        higher_lows,

    "lower_lows":
        lower_lows,

    "bullish_break":
        bullish_break,

    "bearish_break":
        bearish_break,

    "latest_swing_high":
        latest_swing_high,

    "latest_swing_low":
        latest_swing_low,

    "rejection_context":
        rejection_context,

    "upper_rejection":
        upper_rejection_count,

    "lower_rejection":
        lower_rejection_count,

    "bullish_follow_through":
        bullish_follow_through,

    "bearish_follow_through":
        bearish_follow_through,

    "failed_movements":
        failed_movements,

    "direction_changes":
        direction_changes,

    "momentum":
        momentum_context,

    "volatility":
        volatility_context,

    "supporting_evidence":
        list(supporting_evidence),

    "conflicting_evidence":
        list(conflicting_evidence),

    "neutral_evidence":
        list(neutral_evidence),

    "outcomes":
        {}

}


# ============================================================
# PREVENT DUPLICATE CURRENT OBSERVATION
# ============================================================

already_exists = False


for record in records:

    if (
        record.get(
            "market_candle_index"
        )
        ==
        current_observation[
            "market_candle_index"
        ]
        and
        record.get(
            "candle_count"
        )
        ==
        ANALYSIS_CANDLES
    ):

        already_exists = True

        break


if not already_exists:

    records.append(
        current_observation
    )

    print(
        "PASS: New market observation "
        f"stored as {observation_id}."
    )

else:

    print(
        "INFO: Current candle position "
        "already exists in experience memory."
    )


# ============================================================
# RESOLVE PREVIOUS OBSERVATIONS
#
# Once enough new candles exist after an observation,
# compare the observed direction with what actually happened.
# ============================================================

for record in records:

    start_index = record.get(
        "market_candle_index"
    )

    if not isinstance(
        start_index,
        int
    ):

        continue


    start_price = record.get(
        "latest_close"
    )

    if start_price is None:

        continue


    for window in OUTCOME_WINDOWS:

        outcome_key = str(
            window
        )

        existing_outcome = (
            record
            .setdefault(
                "outcomes",
                {}
            )
            .get(
                outcome_key
            )
        )


        outcome_index = (
            start_index +
            window
        )


        if outcome_index >= len(candles):

            continue


        # Do not repeatedly overwrite
        # already resolved outcomes.

        if (
            existing_outcome
            and
            existing_outcome.get(
                "resolved"
            )
        ):

            continue


        future_close = get_value(
            candles[
                outcome_index
            ],
            "close"
        )


        change = percentage_change(
            start_price,
            future_close
        )


        if change > 0.05:

            actual_direction = "bullish"

        elif change < -0.05:

            actual_direction = "bearish"

        else:

            actual_direction = "neutral"


        observed_direction = record.get(
            "integrated_direction",
            "mixed"
        )


        if (
            observed_direction ==
            actual_direction
            and
            observed_direction
            in (
                "bullish",
                "bearish"
            )
        ):

            result = "direction_confirmed"

        elif actual_direction == "neutral":

            result = "neutral_outcome"

        else:

            result = "direction_not_confirmed"


        record[
            "outcomes"
        ][
            outcome_key
        ] = {

            "resolved":
                True,

            "window_candles":
                window,

            "future_candle_index":
                outcome_index,

            "future_close":
                future_close,

            "change_pct":
                change,

            "actual_direction":
                actual_direction,

            "observed_direction":
                observed_direction,

            "result":
                result,

            "resolved_at":
                utc_now()

        }


# ============================================================
# RECALCULATE EXPERIENCE STATISTICS
# ============================================================

statistics.clear()


statistics.update({

    "total_observations":
        len(records),

    "resolved_4":
        0,

    "resolved_8":
        0,

    "resolved_16":
        0,

    "bullish_observations":
        0,

    "bearish_observations":
        0,

    "mixed_observations":
        0,

    "bullish_confirmations_4":
        0,

    "bullish_confirmations_8":
        0,

    "bullish_confirmations_16":
        0,

    "bearish_confirmations_4":
        0,

    "bearish_confirmations_8":
        0,

    "bearish_confirmations_16":
        0,

    "direction_confirmed_4":
        0,

    "direction_confirmed_8":
        0,

    "direction_confirmed_16":
        0,

    "direction_not_confirmed_4":
        0,

    "direction_not_confirmed_8":
        0,

    "direction_not_confirmed_16":
        0,

    "neutral_outcome_4":
        0,

    "neutral_outcome_8":
        0,

    "neutral_outcome_16":
        0

})


for record in records:

    direction = record.get(
        "integrated_direction"
    )


    if direction == "bullish":

        statistics[
            "bullish_observations"
        ] += 1

    elif direction == "bearish":

        statistics[
            "bearish_observations"
        ] += 1

    else:

        statistics[
            "mixed_observations"
        ] += 1


    outcomes = record.get(
        "outcomes",
        {}
    )


    for window in OUTCOME_WINDOWS:

        key = str(window)

        outcome = outcomes.get(
            key
        )


        if not outcome:

            continue


        if not outcome.get(
            "resolved"
        ):

            continue


        statistics[
            f"resolved_{window}"
        ] += 1


        result = outcome.get(
            "result"
        )


        if result == "direction_confirmed":

            statistics[
                f"direction_confirmed_{window}"
            ] += 1


        elif result == "direction_not_confirmed":

            statistics[
                f"direction_not_confirmed_{window}"
            ] += 1


        elif result == "neutral_outcome":

            statistics[
                f"neutral_outcome_{window}"
            ] += 1


        actual_direction = outcome.get(
            "actual_direction"
        )


        if (
            actual_direction ==
            "bullish"
            and
            direction ==
            "bullish"
        ):

            statistics[
                f"bullish_confirmations_{window}"
            ] += 1


        if (
            actual_direction ==
            "bearish"
            and
            direction ==
            "bearish"
        ):

            statistics[
                f"bearish_confirmations_{window}"
            ] += 1


# ============================================================
# STORE UPDATE METADATA
# ============================================================

experience_memory[
    "updated_at"
] = utc_now()


experience_memory[
    "last_market_candle_index"
] = len(candles) - 1


experience_memory[
    "last_observation"
] = current_observation


# ============================================================
# SAVE EXPERIENCE MEMORY
# ============================================================

try:

    with open(
        EXPERIENCE_FILE,
        "wb"
    ) as f:

        pickle.dump(
            experience_memory,
            f,
            protocol=pickle.HIGHEST_PROTOCOL
        )

    print()
    print(
        f"PASS: {EXPERIENCE_FILE} saved."
    )

except Exception as e:

    print()
    print(
        f"ERROR: Could not save "
        f"{EXPERIENCE_FILE}: {e}"
    )

    raise SystemExit(1)


# ============================================================
# DISPLAY RESULTS
# ============================================================

print()
print("=" * 70)
print(
    "MLAI v1.1 LEARNING + EXPERIENCE MEMORY"
)
print("=" * 70)

print()

print("CURRENT OBSERVATION")
print("-" * 70)

print(
    f"Observation ID       : "
    f"{observation_id}"
)

print(
    f"Market state         : "
    f"{market_state}"
)

print(
    f"Integrated direction  : "
    f"{integrated_direction}"
)

print(
    f"Bullish evidence     : "
    f"{bullish_score}"
)

print(
    f"Bearish evidence     : "
    f"{bearish_score}"
)

print(
    f"Directional strength : "
    f"{directional_strength:.1f}%"
)

print(
    f"Current price        : "
    f"{latest_close:.4f}"
)

print()


print("CURRENT EVIDENCE")
print("-" * 70)

print(
    f"Bullish candles      : "
    f"{bullish_count}"
)

print(
    f"Bearish candles      : "
    f"{bearish_count}"
)

print(
    f"Neutral candles      : "
    f"{neutral_count}"
)

print(
    f"Structure            : "
    f"{structure_context}"
)

print(
    f"Momentum             : "
    f"{momentum_context}"
)

print(
    f"Volatility           : "
    f"{volatility_context}"
)

print(
    f"Rejection            : "
    f"{rejection_context}"
)

print()


print("EXPERIENCE MEMORY")
print("-" * 70)

print(
    f"Total observations   : "
    f"{statistics['total_observations']}"
)

print(
    f"Bullish observations : "
    f"{statistics['bullish_observations']}"
)

print(
    f"Bearish observations : "
    f"{statistics['bearish_observations']}"
)

print(
    f"Mixed observations   : "
    f"{statistics['mixed_observations']}"
)

print()


print("RESOLVED OUTCOMES")
print("-" * 70)

for window in OUTCOME_WINDOWS:

    resolved = statistics[
        f"resolved_{window}"
    ]

    confirmed = statistics[
        f"direction_confirmed_{window}"
    ]

    not_confirmed = statistics[
        f"direction_not_confirmed_{window}"
    ]

    neutral = statistics[
        f"neutral_outcome_{window}"
    ]


    print(
        f"{window:>2} candles -> "
        f"resolved={resolved} | "
        f"confirmed={confirmed} | "
        f"not_confirmed={not_confirmed} | "
        f"neutral={neutral}"
    )


print()


print("RECENT EXPERIENCE MEMORY")
print("-" * 70)


recent_records = records[
    -DISPLAY_EXPERIENCES:
]


if recent_records:

    for record in recent_records:

        print(
            f"{record.get('observation_id')} | "
            f"candle={record.get('market_candle_index')} | "
            f"direction="
            f"{record.get('integrated_direction')} | "
            f"state="
            f"{record.get('market_state')}"
        )

        outcomes = record.get(
            "outcomes",
            {}
        )


        resolved_text = []


        for window in OUTCOME_WINDOWS:

            outcome = outcomes.get(
                str(window)
            )


            if outcome and outcome.get(
                "resolved"
            ):

                resolved_text.append(
                    f"{window}c="
                    f"{outcome.get('result')}"
                )


        if resolved_text:

            print(
                "   " +
                " | ".join(
                    resolved_text
                )
            )

        else:

            print(
                "   Outcomes: pending"
            )

else:

    print(
        "No experience records available."
    )


print()


print("LEARNING PRINCIPLE")
print("-" * 70)

print(
    "MLAI v1.1 does not immediately label an observation "
    "as correct or incorrect."
)

print(
    "The system stores the observation first and waits for "
    "future candles to provide an actual outcome."
)

print(
    "This separates what MLAI observed from what the market "
    "actually did afterward."
)

print(
    "Resolved outcomes become experience data that future "
    "MLAI versions can analyse."
)

print()


print("CURRENT MARKET STORY")
print("-" * 70)

story = (

    f"The current market observation is classified as "
    f"{market_state}. "

    f"The integrated directional interpretation is "
    f"{integrated_direction}. "

    f"The latest price is {latest_close:.4f}, "
    f"with a net movement of "
    f"{net_change_pct:.3f}% across the analysed "
    f"{ANALYSIS_CANDLES}-candle context. "

    f"Market structure is {structure_context}. "

    f"Momentum is {momentum_context} and volatility is "
    f"{volatility_context}. "

    f"The current observation has been stored in MLAI "
    f"experience memory. "

    f"Future candles will be used to resolve the "
    f"4-, 8- and 16-candle outcome windows. "

    f"Those outcomes will become historical experience "
    f"for later MLAI learning stages."
)


print(story)

print()


# ============================================================
# UPDATE PROJECT STATUS
# ============================================================

status_text = f"""
## MLAI v1.1 — Learning + Experience Memory Engine

Status: COMPLETED

Completed at:
{utc_now()}

Market candles available:
{len(candles)}

Analysis candles:
{ANALYSIS_CANDLES}

Current observation:
{observation_id}

Market state:
{market_state}

Integrated direction:
{integrated_direction}

Bullish evidence score:
{bullish_score}

Bearish evidence score:
{bearish_score}

Directional strength:
{directional_strength:.1f}%

Structure:
{structure_context}

Momentum:
{momentum_context}

Volatility:
{volatility_context}

Experience observations:
{statistics['total_observations']}

Resolved 4-candle outcomes:
{statistics['resolved_4']}

Resolved 8-candle outcomes:
{statistics['resolved_8']}

Resolved 16-candle outcomes:
{statistics['resolved_16']}

### v1.1 Purpose

MLAI v1.1 introduces persistent Learning + Experience Memory.

The system now separates:

- Current observation
- Integrated market interpretation
- Stored experience
- Future market outcome
- Confirmed interpretation
- Non-confirmed interpretation
- Neutral outcome

The system records the market state before waiting for future candles.

After enough future candles exist, the observation is resolved against actual market behaviour.

Outcome windows:

- 4 candles
- 8 candles
- 16 candles

The system does not treat an observation as correct simply because
the current interpretation appears strong.

The future market must provide the actual outcome.

### Persistent Memory

Experience memory file:

{EXPERIENCE_FILE}

The experience memory contains:

- Observation records
- Market state
- Integrated direction
- Evidence scores
- Structural context
- Momentum
- Volatility
- Rejection context
- Future outcomes
- Resolution status
- Experience statistics

### Architecture Progress

v0.3.1  Candle Relationships              COMPLETED
v0.4    Market Structure                  COMPLETED
v0.5    Market Context                    COMPLETED
v0.6    Pattern / Context Engine          COMPLETED
v0.7    Historical Behaviour              COMPLETED
v0.8    Relationship + Reasoning Engine   COMPLETED
v0.9    Market Story Engine               COMPLETED
v1.0    Integrated MLAI Brain             COMPLETED
v1.1    Learning + Experience Memory      COMPLETED
v1.2    Continuous Learning Engine        NEXT
v1.3    Pattern Discovery Engine          PENDING
v1.4    Market Regime Memory              PENDING
v1.5    Adaptive Evidence Engine          PENDING
v2.0    Autonomous MLAI Market Brain      PENDING

### Important Principle

MLAI is not allowed to rewrite history.

Observed market behaviour is stored first.

Actual future behaviour is stored separately.

The system can later compare the two.

This creates a foundation for genuine experience-based learning.
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
    "PASS: MLAI v1.1 Learning + Experience "
    "Memory Engine completed."
)

print("=" * 70)