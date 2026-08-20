import os
import pickle
from datetime import datetime, timezone


# ============================================================
# MLAI v1.2
# OUTCOME RESOLUTION + LEARNING ENGINE
#
# Purpose:
#
# v1.1:
#   Stores market observations in mlai_experience.bin
#
# v1.2:
#   Loads those observations correctly
#   Resolves them using future candles
#   Stores confirmed / not-confirmed / neutral outcomes
#   Preserves pending observations
#
# IMPORTANT:
# This is NOT a trading signal engine.
# ============================================================


DATA_FILE = "market_data.bin"
EXPERIENCE_FILE = "mlai_experience.bin"
STATUS_FILE = "MLAI_PROJECT_STATUS.md"

ANALYSIS_CANDLES = 60

OUTCOME_WINDOWS = [4, 8, 16]

NEUTRAL_THRESHOLD_PERCENT = 0.05


# ============================================================
# HELPERS
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

    open_price = get_value(candle, "open")
    close_price = get_value(candle, "close")

    if close_price > open_price:
        return "bullish"

    if close_price < open_price:
        return "bearish"

    return "neutral"


def candle_range(candle):

    return max(
        0.0,
        get_value(candle, "high")
        -
        get_value(candle, "low")
    )


def candle_body(candle):

    return abs(
        get_value(candle, "close")
        -
        get_value(candle, "open")
    )


def upper_wick(candle):

    high = get_value(candle, "high")

    return max(
        0.0,
        high
        -
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
        )
        -
        low
    )


def percentage_change(first, last):

    if first == 0:
        return 0.0

    return (
        (last - first)
        /
        abs(first)
    ) * 100.0


# ============================================================
# LOAD MARKET DATA
# ============================================================

print("=" * 70)
print("MLAI v1.2 - LOADING MARKET MEMORY")
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
# SUPPORT MLAI MEMORY OBJECT
# ============================================================

if isinstance(market_data, dict):

    print(
        "PASS: market_data.bin loaded as MLAI memory object."
    )

    memory_metadata = market_data

    candles = market_data.get(
        "candles",
        []
    )

else:

    print(
        "PASS: market_data.bin loaded as candle list."
    )

    memory_metadata = {}

    candles = market_data


print()


if memory_metadata:

    print("MEMORY METADATA")
    print("-" * 70)

    print(
        f"MLAI version : "
        f"{memory_metadata.get('mlai_version', 'unknown')}"
    )

    print(
        f"Created at   : "
        f"{memory_metadata.get('created_at', 'unknown')}"
    )

    print(
        f"Source       : "
        f"{memory_metadata.get('source', 'unknown')}"
    )

    print()


if not isinstance(
    candles,
    (list, tuple)
):

    print(
        "ERROR: market_data.bin does not contain a candle list."
    )

    raise SystemExit(1)


candles = list(candles)


print(
    f"Found {len(candles)} stored candles."
)

print()


if len(candles) < ANALYSIS_CANDLES:

    print(
        f"ERROR: Need at least "
        f"{ANALYSIS_CANDLES} candles."
    )

    raise SystemExit(1)


recent = candles[
    -ANALYSIS_CANDLES:
]


current_candle_index = (
    len(candles) - 1
)


print(
    f"PASS: Using latest "
    f"{len(recent)} candles."
)

print()

print(
    "Analysing latest 60 candles..."
)

print()


# ============================================================
# CURRENT MARKET ANALYSIS
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


if bullish_count > bearish_count:

    current_direction = "bullish"

elif bearish_count > bullish_count:

    current_direction = "bearish"

else:

    current_direction = "mixed"


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
            (i, current_high)
        )


    if (
        current_low < previous_low
        and
        current_low < next_low
    ):

        swing_lows.append(
            (i, current_low)
        )


higher_highs = 0
lower_highs = 0

higher_lows = 0
lower_lows = 0


for i in range(
    1,
    len(swing_highs)
):

    previous = swing_highs[i - 1][1]
    current = swing_highs[i][1]

    if current > previous:

        higher_highs += 1

    elif current < previous:

        lower_highs += 1


for i in range(
    1,
    len(swing_lows)
):

    previous = swing_lows[i - 1][1]
    current = swing_lows[i][1]

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
# REJECTION
# ============================================================

average_range = (
    sum(ranges) /
    len(ranges)
    if ranges
    else 0.0
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
# FOLLOW THROUGH
# ============================================================

bullish_follow_through = 0
bearish_follow_through = 0
failed_movements = 0


for i in range(
    1,
    len(directions)
):

    previous = directions[i - 1]
    current = directions[i]


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
# MOMENTUM / VOLATILITY
# ============================================================

early_ranges = ranges[:15]
recent_ranges = ranges[-15:]

early_bodies = bodies[:15]
recent_bodies = bodies[-15:]


early_range_avg = (
    sum(early_ranges) /
    len(early_ranges)
    if early_ranges
    else 0.0
)


recent_range_avg = (
    sum(recent_ranges) /
    len(recent_ranges)
    if recent_ranges
    else 0.0
)


early_body_avg = (
    sum(early_bodies) /
    len(early_bodies)
    if early_bodies
    else 0.0
)


recent_body_avg = (
    sum(recent_bodies) /
    len(recent_bodies)
    if recent_bodies
    else 0.0
)


if recent_range_avg > (
    early_range_avg * 1.15
):

    volatility_context = "expanding"

elif recent_range_avg < (
    early_range_avg * 0.85
):

    volatility_context = "contracting"

else:

    volatility_context = "stable"


if recent_body_avg > (
    early_body_avg * 1.15
):

    momentum_context = "increasing"

elif recent_body_avg < (
    early_body_avg * 0.85
):

    momentum_context = "decreasing"

else:

    momentum_context = "stable"


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
# MARKET STATE
# ============================================================

if (
    current_direction == "bullish"
    and
    structure_context ==
    "bullish_structure"
):

    market_state = (
        "bullish_structural_environment"
    )

elif (
    current_direction == "bearish"
    and
    structure_context ==
    "bearish_structure"
):

    market_state = (
        "bearish_structural_environment"
    )

else:

    market_state = (
        "mixed_market_environment"
    )


# ============================================================
# LOAD EXPERIENCE MEMORY
# ============================================================

print(
    "PASS: Analysing experience memory..."
)

print()


if not os.path.exists(
    EXPERIENCE_FILE
):

    print(
        "ERROR: mlai_experience.bin not found."
    )

    print(
        "Run mlai_v11.py first to create the experience memory."
    )

    raise SystemExit(1)


try:

    with open(
        EXPERIENCE_FILE,
        "rb"
    ) as f:

        experience_memory = pickle.load(f)

except Exception as e:

    print(
        f"ERROR: Could not load "
        f"mlai_experience.bin: {e}"
    )

    raise SystemExit(1)


# ============================================================
# CRITICAL MEMORY COMPATIBILITY FIX
#
# v1.1 may have saved observations in different structures.
#
# We explicitly detect:
#
# 1. Direct list
# 2. {"observations": [...]}
# 3. {"experience": [...]}
# 4. {"memory": [...]}
# 5. {"data": [...]}
#
# This prevents the v1.2 zero-observation problem.
# ============================================================

observations = []


if isinstance(
    experience_memory,
    list
):

    observations = experience_memory


elif isinstance(
    experience_memory,
    dict
):

    possible_keys = [
        "observations",
        "experience",
        "memory",
        "data"
    ]


    for key in possible_keys:

        value = experience_memory.get(
            key
        )


        if isinstance(
            value,
            list
        ):

            observations = value

            break


# ============================================================
# HANDLE v1.1 SINGLE OBSERVATION STRUCTURE
# ============================================================

if not observations:

    if isinstance(
        experience_memory,
        dict
    ):

        if (
            "observation_id"
            in experience_memory
        ):

            observations = [
                experience_memory
            ]


# ============================================================
# NORMALIZE OBSERVATIONS
# ============================================================

normalized_observations = []


for index, observation in enumerate(
    observations
):

    if not isinstance(
        observation,
        dict
    ):

        continue


    obs = dict(observation)


    # --------------------------------------------------------
    # Observation ID
    # --------------------------------------------------------

    if not obs.get(
        "observation_id"
    ):

        obs["observation_id"] = (
            f"obs_{index + 1:06d}"
        )


    # --------------------------------------------------------
    # Candle index
    # --------------------------------------------------------

    if (
        "candle_index"
        not in obs
    ):

        if "candle" in obs:

            obs["candle_index"] = (
                obs["candle"]
            )

        elif "index" in obs:

            obs["candle_index"] = (
                obs["index"]
            )

        else:

            obs["candle_index"] = None


    # --------------------------------------------------------
    # Direction
    # --------------------------------------------------------

    if (
        "direction"
        not in obs
    ):

        if (
            "integrated_direction"
            in obs
        ):

            obs["direction"] = (
                obs[
                    "integrated_direction"
                ]
            )

        else:

            obs["direction"] = "mixed"


    # --------------------------------------------------------
    # Market state
    # --------------------------------------------------------

    if (
        "market_state"
        not in obs
    ):

        if "state" in obs:

            obs["market_state"] = (
                obs["state"]
            )

        else:

            obs["market_state"] = (
                "unknown"
            )


    # --------------------------------------------------------
    # Outcomes
    # --------------------------------------------------------

    if (
        "outcomes"
        not in obs
    ):

        obs["outcomes"] = {}


    if not isinstance(
        obs["outcomes"],
        dict
    ):

        obs["outcomes"] = {}


    normalized_observations.append(
        obs
    )


observations = normalized_observations


# ============================================================
# CURRENT OBSERVATION
# ============================================================

current_observation = None


for observation in observations:

    candle_index = (
        observation.get(
            "candle_index"
        )
    )


    if candle_index == (
        current_candle_index
    ):

        current_observation = (
            observation
        )

        break


# ============================================================
# DO NOT DUPLICATE CURRENT OBSERVATION
# ============================================================

if current_observation:

    print(
        "PASS: Current observation already exists."
    )

else:

    next_number = (
        len(observations) + 1
    )


    current_observation = {

        "observation_id":
            f"obs_{next_number:06d}",

        "candle_index":
            current_candle_index,

        "direction":
            current_direction,

        "market_state":
            market_state,

        "integrated_direction":
            current_direction,

        "current_price":
            latest_close,

        "bullish_candles":
            bullish_count,

        "bearish_candles":
            bearish_count,

        "neutral_candles":
            neutral_count,

        "structure":
            structure_context,

        "momentum":
            momentum_context,

        "volatility":
            volatility_context,

        "rejection":
            rejection_context,

        "created_at":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "outcomes":
            {}
    }


    observations.append(
        current_observation
    )


    print(
        f"PASS: New observation stored as "
        f"{current_observation['observation_id']}."
    )


# ============================================================
# RESOLVE OUTCOMES
# ============================================================

newly_resolved = 0
newly_confirmed = 0
newly_not_confirmed = 0
newly_neutral = 0


for observation in observations:

    candle_index = (
        observation.get(
            "candle_index"
        )
    )


    if candle_index is None:

        continue


    direction = observation.get(
        "direction",
        "mixed"
    )


    if (
        "outcomes"
        not in observation
    ):

        observation["outcomes"] = {}


    for window in OUTCOME_WINDOWS:

        key = str(window)


        # ----------------------------------------------------
        # Already resolved
        # ----------------------------------------------------

        if key in observation[
            "outcomes"
        ]:

            continue


        future_index = (
            candle_index +
            window
        )


        # ----------------------------------------------------
        # Not enough future candles
        # ----------------------------------------------------

        if future_index >= len(
            candles
        ):

            continue


        start_price = get_value(
            candles[
                candle_index
            ],
            "close"
        )


        future_price = get_value(
            candles[
                future_index
            ],
            "close"
        )


        change_pct = percentage_change(
            start_price,
            future_price
        )


        # ----------------------------------------------------
        # Actual market outcome
        # ----------------------------------------------------

        if (
            abs(change_pct)
            <=
            NEUTRAL_THRESHOLD_PERCENT
        ):

            market_outcome = "neutral"

        elif change_pct > 0:

            market_outcome = "bullish"

        else:

            market_outcome = "bearish"


        # ----------------------------------------------------
        # Compare actual outcome with observation
        # ----------------------------------------------------

        if direction == "bullish":

            if (
                market_outcome
                ==
                "bullish"
            ):

                result = "confirmed"

            elif (
                market_outcome
                ==
                "bearish"
            ):

                result = "not_confirmed"

            else:

                result = "neutral"


        elif direction == "bearish":

            if (
                market_outcome
                ==
                "bearish"
            ):

                result = "confirmed"

            elif (
                market_outcome
                ==
                "bullish"
            ):

                result = "not_confirmed"

            else:

                result = "neutral"


        else:

            result = "neutral"


        observation[
            "outcomes"
        ][key] = {

            "window":
                window,

            "start_candle":
                candle_index,

            "end_candle":
                future_index,

            "start_price":
                start_price,

            "end_price":
                future_price,

            "change_pct":
                change_pct,

            "market_outcome":
                market_outcome,

            "result":
                result,

            "resolved_at":
                datetime.now(
                    timezone.utc
                ).isoformat()
        }


        newly_resolved += 1


        if result == "confirmed":

            newly_confirmed += 1

        elif result == "not_confirmed":

            newly_not_confirmed += 1

        else:

            newly_neutral += 1


# ============================================================
# STATISTICS
# ============================================================

total_observations = len(
    observations
)


bullish_observations = sum(
    1
    for x in observations
    if x.get(
        "direction"
    ) == "bullish"
)


bearish_observations = sum(
    1
    for x in observations
    if x.get(
        "direction"
    ) == "bearish"
)


mixed_observations = (
    total_observations
    -
    bullish_observations
    -
    bearish_observations
)


statistics = {}


for window in OUTCOME_WINDOWS:

    resolved = 0
    confirmed = 0
    not_confirmed = 0
    neutral = 0


    for observation in observations:

        result_data = (
            observation
            .get(
                "outcomes",
                {}
            )
            .get(
                str(window)
            )
        )


        if not result_data:

            continue


        resolved += 1


        result = result_data.get(
            "result"
        )


        if result == "confirmed":

            confirmed += 1

        elif result == "not_confirmed":

            not_confirmed += 1

        elif result == "neutral":

            neutral += 1


    if resolved > 0:

        accuracy = (
            confirmed /
            resolved
        ) * 100.0

    else:

        accuracy = 0.0


    statistics[
        window
    ] = {

        "resolved":
            resolved,

        "confirmed":
            confirmed,

        "not_confirmed":
            not_confirmed,

        "neutral":
            neutral,

        "accuracy":
            accuracy
    }


# ============================================================
# PENDING / RESOLVED WINDOWS
# ============================================================

pending_windows = 0
resolved_windows = 0


for observation in observations:

    for window in OUTCOME_WINDOWS:

        key = str(window)


        if key in observation.get(
            "outcomes",
            {}
        ):

            resolved_windows += 1

        else:

            pending_windows += 1


# ============================================================
# REBUILD MEMORY OBJECT
#
# This is the important repair.
#
# Whatever v1.1 format existed is rewritten into a
# clean v1.2-compatible structure.
# ============================================================

new_memory = {

    "memory_version":
        "1.2",

    "created_at":
        experience_memory.get(
            "created_at",
            datetime.now(
                timezone.utc
            ).isoformat()
        )
        if isinstance(
            experience_memory,
            dict
        )
        else datetime.now(
            timezone.utc
        ).isoformat(),

    "updated_at":
        datetime.now(
            timezone.utc
        ).isoformat(),

    "observations":
        observations,

    "learning_summary": {

        "total_observations":
            total_observations,

        "bullish_observations":
            bullish_observations,

        "bearish_observations":
            bearish_observations,

        "mixed_observations":
            mixed_observations,

        "pending_windows":
            pending_windows,

        "resolved_windows":
            resolved_windows,

        "statistics":
            statistics
    }
}


# ============================================================
# SAVE CORRECTED EXPERIENCE MEMORY
# ============================================================

try:

    with open(
        EXPERIENCE_FILE,
        "wb"
    ) as f:

        pickle.dump(
            new_memory,
            f
        )


    print()
    print(
        "PASS: mlai_experience.bin saved."
    )

except Exception as e:

    print(
        f"ERROR: Could not save "
        f"mlai_experience.bin: {e}"
    )

    raise SystemExit(1)


# ============================================================
# OUTPUT
# ============================================================

print()

print("=" * 70)
print("MLAI v1.2 OUTCOME RESOLUTION + LEARNING ENGINE")
print("=" * 70)

print()

print("CURRENT MARKET OBSERVATION")
print("-" * 70)

print(
    f"Candle index          : "
    f"{current_candle_index}"
)

print(
    f"Current price         : "
    f"{latest_close:.4f}"
)

print(
    f"Market state          : "
    f"{market_state}"
)

print(
    f"Integrated direction  : "
    f"{current_direction}"
)

print(
    f"Bullish candles       : "
    f"{bullish_count}"
)

print(
    f"Bearish candles       : "
    f"{bearish_count}"
)

print(
    f"Neutral candles       : "
    f"{neutral_count}"
)

print(
    f"Structure             : "
    f"{structure_context}"
)

print(
    f"Momentum              : "
    f"{momentum_context}"
)

print(
    f"Volatility            : "
    f"{volatility_context}"
)

print(
    f"Rejection             : "
    f"{rejection_context}"
)

print()

print("EXPERIENCE MEMORY")
print("-" * 70)

print(
    f"Total observations   : "
    f"{total_observations}"
)

print(
    f"Bullish observations : "
    f"{bullish_observations}"
)

print(
    f"Bearish observations : "
    f"{bearish_observations}"
)

print(
    f"Mixed observations   : "
    f"{mixed_observations}"
)

print()

print("NEWLY RESOLVED OUTCOMES")
print("-" * 70)

print(
    f"Resolved             : "
    f"{newly_resolved}"
)

print(
    f"Confirmed            : "
    f"{newly_confirmed}"
)

print(
    f"Not confirmed        : "
    f"{newly_not_confirmed}"
)

print(
    f"Neutral              : "
    f"{newly_neutral}"
)

print()

print("RESOLVED EXPERIENCE")
print("-" * 70)


for window in OUTCOME_WINDOWS:

    stats = statistics[
        window
    ]


    print(
        f"{window:2d} candles -> "
        f"resolved={stats['resolved']} | "
        f"confirmed={stats['confirmed']} | "
        f"not_confirmed={stats['not_confirmed']} | "
        f"neutral={stats['neutral']} | "
        f"accuracy={stats['accuracy']:.1f}%"
    )


print()

print("RECENT EXPERIENCE MEMORY")
print("-" * 70)


if observations:

    for observation in observations[-10:]:

        print(
            f"{observation.get('observation_id')} | "
            f"candle={observation.get('candle_index')} | "
            f"direction={observation.get('direction')} | "
            f"state={observation.get('market_state')}"
        )


        outcome_text = []


        for window in OUTCOME_WINDOWS:

            result_data = (
                observation
                .get(
                    "outcomes",
                    {}
                )
                .get(
                    str(window)
                )
            )


            if result_data:

                outcome_text.append(
                    f"{window}={result_data.get('result')}"
                )

            else:

                outcome_text.append(
                    f"{window}=pending"
                )


        print(
            "   Outcomes: "
            +
            " | ".join(
                outcome_text
            )
        )


else:

    print(
        "No observations stored."
    )


print()

print("LEARNING SUMMARY")
print("-" * 70)

print(
    f"Resolved outcomes     : "
    f"{resolved_windows}"
)

print(
    f"Confirmed outcomes    : "
    f"{sum(x['confirmed'] for x in statistics.values())}"
)

print(
    f"Not confirmed         : "
    f"{sum(x['not_confirmed'] for x in statistics.values())}"
)

print(
    f"Neutral outcomes      : "
    f"{sum(x['neutral'] for x in statistics.values())}"
)


overall_resolved = sum(
    x["resolved"]
    for x in statistics.values()
)


overall_confirmed = sum(
    x["confirmed"]
    for x in statistics.values()
)


if overall_resolved > 0:

    overall_accuracy = (
        overall_confirmed /
        overall_resolved
    ) * 100.0

else:

    overall_accuracy = 0.0


print(
    f"Experience accuracy   : "
    f"{overall_accuracy:.1f}%"
)


print()

print("LEARNING PRINCIPLE")
print("-" * 70)

print(
    "MLAI does not assume that an observation was correct "
    "when it was created."
)

print(
    "The system waits for actual future candles before "
    "resolving the observation."
)

print(
    "Confirmed observations become positive experience."
)

print(
    "Not-confirmed observations become negative experience."
)

print(
    "Neutral outcomes are preserved separately."
)

print(
    "Pending observations remain unresolved until enough "
    "future market data exists."
)

print(
    "The corrected v1.2 memory format preserves the original "
    "v1.1 observations instead of discarding them."
)


# ============================================================
# CURRENT MARKET STORY
# ============================================================

print()

print("CURRENT MARKET STORY")
print("-" * 70)

print(
    f"The current market observation is classified as "
    f"{market_state}. "
    f"The integrated directional character is "
    f"{current_direction}. "
    f"The latest stored price is "
    f"{latest_close:.4f}. "
    f"Market structure is classified as "
    f"{structure_context}. "
    f"Momentum is {momentum_context} and "
    f"volatility is {volatility_context}. "
    f"MLAI currently has "
    f"{total_observations} experience observations "
    f"stored in persistent memory. "
    f"{resolved_windows} outcome windows have been "
    f"resolved and {pending_windows} remain pending. "
    f"MLAI v1.2 uses actual subsequent market behaviour "
    f"to convert observations into experience data. "
    f"This learning process does not guarantee future "
    f"market behaviour and does not create an automatic "
    f"trading signal."
)


# ============================================================
# UPDATE PROJECT STATUS
# ============================================================

status_text = f"""

## MLAI v1.2 — Outcome Resolution + Learning Engine

Status: COMPLETED

Market candles:
{len(candles)}

Current candle index:
{current_candle_index}

Current market state:
{market_state}

Current direction:
{current_direction}

Total observations:
{total_observations}

Bullish observations:
{bullish_observations}

Bearish observations:
{bearish_observations}

Mixed observations:
{mixed_observations}

Resolved outcome windows:
{resolved_windows}

Pending outcome windows:
{pending_windows}

Newly resolved:
{newly_resolved}

Newly confirmed:
{newly_confirmed}

Newly not confirmed:
{newly_not_confirmed}

Newly neutral:
{newly_neutral}

Overall experience accuracy:
{overall_accuracy:.1f}%

### v1.2 Purpose

MLAI v1.2 converts previously stored observations into actual experience by comparing each observation against future market candles.

The engine:

- Loads v1.1 experience memory
- Detects the existing observation structure
- Preserves v1.1 observations
- Rebuilds the memory in a clean v1.2 format
- Resolves 4-candle outcomes
- Resolves 8-candle outcomes
- Resolves 16-candle outcomes
- Records confirmed outcomes
- Records not-confirmed outcomes
- Records neutral outcomes
- Preserves unresolved future windows
- Calculates experience accuracy

### Important Architecture Principle

Observation is not the same as outcome.

MLAI first records:

Observation

Then waits for:

Actual future market behaviour

Then records:

Outcome

Then converts the result into:

Experience

This prevents MLAI from assuming that its own interpretation was correct.

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
v1.2    Outcome Resolution + Learning     COMPLETED
v1.3    Experience Pattern Learning       NEXT
v1.4    Multi-Timeframe Experience        NEXT
v2.0    Continuous Learning Brain         FUTURE

### Memory Compatibility Fix

v1.2 explicitly supports legacy v1.1 memory structures.

The engine can recover observations from:

- Direct observation lists
- observations
- experience
- memory
- data
- Single observation dictionaries

The memory is then rewritten into a consistent v1.2 format.

No existing v1.1 observation should be silently discarded.

### Learning Principle

Experience accuracy represents historical agreement between MLAI observations and subsequent candle behaviour.

It is not a guarantee of future prediction accuracy.
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
    "PASS: MLAI v1.2 Outcome Resolution + "
    "Learning Engine completed."
)

print("=" * 70)