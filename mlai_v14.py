
import os
import pickle
from collections import Counter, defaultdict
from statistics import mean


# ============================================================
# MLAI v1.4
# PATTERN + EXPERIENCE LEARNING ENGINE
#
# Purpose:
#
# Connect:
#   Market memory
#   Experience memory
#   Pattern memory
#   Resolved outcomes
#   Historical pattern behaviour
#
# v1.4 does NOT predict automatically.
#
# It learns from ACTUAL resolved future outcomes.
#
# Pending observations are NOT counted as success/failure.
#
# Files:
#
#   market_data.bin
#   mlai_experience.bin
#   mlai_pattern_memory.bin
#   mlai_learning_memory.bin
#   MLAI_PROJECT_STATUS.md
#
# ============================================================


DATA_FILE = "market_data.bin"
EXPERIENCE_FILE = "mlai_experience.bin"
PATTERN_FILE = "mlai_pattern_memory.bin"
LEARNING_FILE = "mlai_learning_memory.bin"
STATUS_FILE = "MLAI_PROJECT_STATUS.md"

ANALYSIS_CANDLES = 60

PATTERN_LENGTH = 6

OUTCOME_WINDOWS = {
    "4": 4,
    "8": 8,
    "16": 16
}

MIN_PATTERN_OCCURRENCES = 3

MAX_DISPLAY_PATTERNS = 20


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

    open_price = get_value(candle, "open")
    close_price = get_value(candle, "close")

    if close_price > open_price:
        return "bullish"

    if close_price < open_price:
        return "bearish"

    return "neutral"


def direction_symbol(candle):

    direction = candle_direction(candle)

    if direction == "bullish":
        return "B"

    if direction == "bearish":
        return "S"

    return "N"


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

    if not values:
        return 0.0

    return mean(values)


def normalize_direction(value):

    if value is None:
        return "mixed"

    value = str(value).lower().strip()

    if value in ("bullish", "b"):
        return "bullish"

    if value in ("bearish", "s"):
        return "bearish"

    if value in ("neutral", "n"):
        return "neutral"

    return "mixed"


# ============================================================
# LOAD MARKET MEMORY
# ============================================================

print("=" * 70)
print("MLAI v1.4 - LOADING MARKET MEMORY")
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

    print(
        f"ERROR: Could not load market_data.bin: {e}"
    )

    raise SystemExit(1)


# ============================================================
# SUPPORT BOTH OLD AND NEW MARKET MEMORY FORMATS
# ============================================================

market_metadata = {}

if isinstance(market_memory, dict):

    market_metadata = {
        "mlai_version":
            market_memory.get("mlai_version"),

        "created_at":
            market_memory.get("created_at"),

        "source":
            market_memory.get("source")
    }

    if isinstance(
        market_memory.get("candles"),
        (list, tuple)
    ):

        candles = list(
            market_memory["candles"]
        )

    else:

        print(
            "ERROR: Market memory dictionary does not "
            "contain a valid candles list."
        )

        raise SystemExit(1)

elif isinstance(
    market_memory,
    (list, tuple)
):

    candles = list(market_memory)

else:

    print(
        "ERROR: Unsupported market_data.bin format."
    )

    raise SystemExit(1)


print(
    "PASS: market_data.bin loaded as MLAI memory object."
)

print()

print("MEMORY METADATA")
print("-" * 70)

print(
    f"MLAI version : "
    f"{market_metadata.get('mlai_version', 'unknown')}"
)

print(
    f"Created at   : "
    f"{market_metadata.get('created_at', 'unknown')}"
)

print(
    f"Source       : "
    f"{market_metadata.get('source', 'unknown')}"
)

print()

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


recent = candles[-ANALYSIS_CANDLES:]


print(
    f"PASS: Using latest {len(recent)} candles."
)

print()

print("Analysing latest 60 candles...")
print()


# ============================================================
# CURRENT MARKET CONTEXT
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


early_range_avg = safe_mean(
    ranges[:15]
)

recent_range_avg = safe_mean(
    ranges[-15:]
)

early_body_avg = safe_mean(
    bodies[:15]
)

recent_body_avg = safe_mean(
    bodies[-15:]
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


upper_wicks = [
    upper_wick(c)
    for c in recent
]

lower_wicks = [
    lower_wick(c)
    for c in recent
]

average_range = safe_mean(
    ranges
)

upper_rejection_count = sum(
    1
    for value in upper_wicks
    if value > 0 and
    value >= average_range * 0.20
)

lower_rejection_count = sum(
    1
    for value in lower_wicks
    if value > 0 and
    value >= average_range * 0.20
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
# CURRENT PATTERN
# ============================================================

current_pattern_candles = candles[
    -PATTERN_LENGTH:
]

current_direction_pattern = " ".join(
    direction_symbol(c)
    for c in current_pattern_candles
)


# ============================================================
# EXPERIENCE MEMORY
# ============================================================

print(
    "PASS: Loading MLAI experience memory..."
)


experience_memory = None


if os.path.exists(EXPERIENCE_FILE):

    try:

        with open(
            EXPERIENCE_FILE,
            "rb"
        ) as f:

            experience_memory = pickle.load(f)

    except Exception as e:

        print(
            "WARNING: Could not load "
            f"{EXPERIENCE_FILE}: {e}"
        )


if experience_memory is None:

    experience_memory = {
        "version": "1.4",
        "observations": []
    }


# ============================================================
# NORMALIZE EXPERIENCE MEMORY
# ============================================================

if isinstance(
    experience_memory,
    list
):

    experience_memory = {
        "version": "1.4",
        "observations": experience_memory
    }


if not isinstance(
    experience_memory,
    dict
):

    experience_memory = {
        "version": "1.4",
        "observations": []
    }


observations = experience_memory.get(
    "observations",
    []
)


if not isinstance(
    observations,
    list
):

    observations = []


# ============================================================
# RESOLVE PENDING EXPERIENCE
# ============================================================

newly_resolved = []

resolved_confirmed = 0
resolved_not_confirmed = 0
resolved_neutral = 0


for observation in observations:

    if not isinstance(
        observation,
        dict
    ):
        continue

    candle_index = observation.get(
        "candle_index"
    )

    if candle_index is None:
        continue

    try:

        candle_index = int(
            candle_index
        )

    except:

        continue


    predicted_direction = normalize_direction(
        observation.get(
            "direction"
        )
    )


    outcomes = observation.get(
        "outcomes"
    )


    if not isinstance(
        outcomes,
        dict
    ):

        outcomes = {}

        observation["outcomes"] = outcomes


    for window_name, window_size in OUTCOME_WINDOWS.items():

        existing = outcomes.get(
            window_name
        )


        if isinstance(
            existing,
            dict
        ):

            status = existing.get(
                "status",
                "pending"
            )

            if status != "pending":
                continue

        elif existing in (
            "confirmed",
            "not_confirmed",
            "neutral"
        ):

            continue

        else:

            existing = {
                "status": "pending"
            }

            outcomes[window_name] = existing


        target_index = (
            candle_index +
            window_size
        )


        if target_index >= len(candles):

            continue


        start_price = get_value(
            candles[candle_index],
            "close"
        )

        end_price = get_value(
            candles[target_index],
            "close"
        )


        change = percentage_change(
            start_price,
            end_price
        )


        if change > 0.05:

            actual_direction = "bullish"

        elif change < -0.05:

            actual_direction = "bearish"

        else:

            actual_direction = "neutral"


        if predicted_direction in (
            "bullish",
            "bearish"
        ):

            if actual_direction == predicted_direction:

                result = "confirmed"

                resolved_confirmed += 1

            elif actual_direction in (
                "bullish",
                "bearish"
            ):

                result = "not_confirmed"

                resolved_not_confirmed += 1

            else:

                result = "neutral"

                resolved_neutral += 1

        else:

            result = "neutral"

            resolved_neutral += 1


        existing.update({

            "status": result,

            "actual_direction":
                actual_direction,

            "change_pct":
                change,

            "resolved_candle_index":
                target_index
        })


        newly_resolved.append({

            "observation_id":
                observation.get(
                    "observation_id",
                    "unknown"
                ),

            "window":
                window_name,

            "predicted":
                predicted_direction,

            "actual":
                actual_direction,

            "result":
                result,

            "change_pct":
                change
        })


# ============================================================
# SAVE EXPERIENCE MEMORY
# ============================================================

experience_memory["version"] = "1.4"

experience_memory["observations"] = observations

experience_memory[
    "last_processed_candle"
] = len(candles) - 1


try:

    with open(
        EXPERIENCE_FILE,
        "wb"
    ) as f:

        pickle.dump(
            experience_memory,
            f
        )

    print(
        "PASS: Updated experience memory saved."
    )

except Exception as e:

    print(
        "WARNING: Could not save experience memory:"
        f" {e}"
    )


# ============================================================
# PATTERN MEMORY
# ============================================================

print(
    "PASS: Loading MLAI pattern memory..."
)


pattern_memory = None


if os.path.exists(PATTERN_FILE):

    try:

        with open(
            PATTERN_FILE,
            "rb"
        ) as f:

            pattern_memory = pickle.load(f)

    except Exception as e:

        print(
            "WARNING: Could not load "
            f"{PATTERN_FILE}: {e}"
        )


if pattern_memory is None:

    pattern_memory = {}


# ============================================================
# SUPPORT MULTIPLE PATTERN MEMORY FORMATS
# ============================================================

direction_patterns = {}
behaviour_patterns = {}


if isinstance(
    pattern_memory,
    dict
):

    direction_patterns = (
        pattern_memory.get(
            "direction_patterns",
            pattern_memory.get(
                "patterns",
                {}
            )
        )
    )

    behaviour_patterns = (
        pattern_memory.get(
            "behaviour_patterns",
            {}
        )
    )


if not isinstance(
    direction_patterns,
    dict
):

    direction_patterns = {}


if not isinstance(
    behaviour_patterns,
    dict
):

    behaviour_patterns = {}


# ============================================================
# BUILD HISTORICAL PATTERN EXPERIENCE DIRECTLY
#
# This is intentionally recalculated from market_data.bin.
#
# It prevents old pattern-memory formats from corrupting
# v1.4 learning.
# ============================================================

print(
    "PASS: Calculating historical pattern experience..."
)


historical_pattern_stats = defaultdict(
    lambda: {
        "occurrences": 0,
        "bullish": {
            "4": 0,
            "8": 0,
            "16": 0
        },
        "bearish": {
            "4": 0,
            "8": 0,
            "16": 0
        },
        "neutral": {
            "4": 0,
            "8": 0,
            "16": 0
        }
    }
)


max_start = (
    len(candles) -
    PATTERN_LENGTH -
    max(
        OUTCOME_WINDOWS.values()
    )
)


for start in range(
    0,
    max_start + 1
):

    pattern_candles = candles[
        start:
        start + PATTERN_LENGTH
    ]


    pattern = " ".join(
        direction_symbol(c)
        for c in pattern_candles
    )


    historical_pattern_stats[
        pattern
    ]["occurrences"] += 1


    outcome_start = (
        start +
        PATTERN_LENGTH -
        1
    )


    for window_name, window_size in OUTCOME_WINDOWS.items():

        target_index = (
            outcome_start +
            window_size
        )


        if target_index >= len(candles):

            continue


        start_price = get_value(
            candles[outcome_start],
            "close"
        )

        end_price = get_value(
            candles[target_index],
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


        historical_pattern_stats[
            pattern
        ][outcome][window_name] += 1


# ============================================================
# CREATE LEARNING MEMORY
# ============================================================

learning_memory = {

    "version": "1.4",

    "created_from": {
        "market_file": DATA_FILE,
        "experience_file": EXPERIENCE_FILE,
        "pattern_file": PATTERN_FILE
    },

    "last_candle_index":
        len(candles) - 1,

    "current_pattern":
        current_direction_pattern,

    "patterns": {}
}


# ============================================================
# PATTERN LEARNING ANALYSIS
# ============================================================

for pattern, stats in historical_pattern_stats.items():

    occurrences = stats[
        "occurrences"
    ]

    if occurrences < MIN_PATTERN_OCCURRENCES:
        continue


    record = {

        "occurrences":
            occurrences,

        "horizons": {}
    }


    for window_name in OUTCOME_WINDOWS:

        bullish = stats[
            "bullish"
        ][window_name]

        bearish = stats[
            "bearish"
        ][window_name]

        neutral = stats[
            "neutral"
        ][window_name]


        total = (
            bullish +
            bearish +
            neutral
        )


        if total == 0:

            continue


        bullish_pct = (
            bullish /
            total
        ) * 100.0


        bearish_pct = (
            bearish /
            total
        ) * 100.0


        neutral_pct = (
            neutral /
            total
        ) * 100.0


        if (
            bullish_pct >= bearish_pct
            and
            bullish_pct >= neutral_pct
        ):

            dominant = "bullish"

            dominant_pct = bullish_pct

        elif (
            bearish_pct >= bullish_pct
            and
            bearish_pct >= neutral_pct
        ):

            dominant = "bearish"

            dominant_pct = bearish_pct

        else:

            dominant = "neutral"

            dominant_pct = neutral_pct


        record[
            "horizons"
        ][window_name] = {

            "bullish":
                bullish,

            "bearish":
                bearish,

            "neutral":
                neutral,

            "bullish_pct":
                bullish_pct,

            "bearish_pct":
                bearish_pct,

            "neutral_pct":
                neutral_pct,

            "dominant":
                dominant,

            "dominant_pct":
                dominant_pct
        }


    learning_memory[
        "patterns"
    ][pattern] = record


# ============================================================
# CURRENT PATTERN ANALYSIS
# ============================================================

current_stats = learning_memory[
    "patterns"
].get(
    current_direction_pattern
)


current_pattern_status = (
    "no_historical_match"
)


if current_stats:

    current_pattern_status = (
        "historical_match"
    )


# ============================================================
# RESOLVED EXPERIENCE STATISTICS
# ============================================================

experience_statistics = {

    "4": {
        "resolved": 0,
        "confirmed": 0,
        "not_confirmed": 0,
        "neutral": 0
    },

    "8": {
        "resolved": 0,
        "confirmed": 0,
        "not_confirmed": 0,
        "neutral": 0
    },

    "16": {
        "resolved": 0,
        "confirmed": 0,
        "not_confirmed": 0,
        "neutral": 0
    }
}


for observation in observations:

    if not isinstance(
        observation,
        dict
    ):
        continue


    outcomes = observation.get(
        "outcomes",
        {}
    )


    if not isinstance(
        outcomes,
        dict
    ):
        continue


    for window_name in OUTCOME_WINDOWS:

        result = outcomes.get(
            window_name
        )


        if not isinstance(
            result,
            dict
        ):
            continue


        status = result.get(
            "status"
        )


        if status not in (
            "confirmed",
            "not_confirmed",
            "neutral"
        ):
            continue


        experience_statistics[
            window_name
        ]["resolved"] += 1


        experience_statistics[
            window_name
        ][status] += 1


# ============================================================
# EXPERIENCE ACCURACY
# ============================================================

for window_name, stats in experience_statistics.items():

    resolved = stats["resolved"]

    if resolved:

        stats["accuracy"] = (
            stats["confirmed"] /
            resolved
        ) * 100.0

    else:

        stats["accuracy"] = 0.0


# ============================================================
# CURRENT PATTERN LEARNING INTERPRETATION
# ============================================================

pattern_learning_classification = (
    "insufficient_pattern_experience"
)


if current_stats:

    horizon_8 = current_stats[
        "horizons"
    ].get("8")


    if horizon_8:

        dominant = horizon_8[
            "dominant"
        ]

        dominant_pct = horizon_8[
            "dominant_pct"
        ]


        if dominant_pct >= 65:

            pattern_learning_classification = (
                f"strong_historical_{dominant}_pattern_bias"
            )

        elif dominant_pct >= 55:

            pattern_learning_classification = (
                f"moderate_historical_{dominant}_pattern_bias"
            )

        else:

            pattern_learning_classification = (
                "mixed_historical_pattern_behaviour"
            )


# ============================================================
# RESOLVED EXPERIENCE COUNTS
# ============================================================

total_resolved = sum(
    stats["resolved"]
    for stats in experience_statistics.values()
)


total_confirmed = sum(
    stats["confirmed"]
    for stats in experience_statistics.values()
)


total_not_confirmed = sum(
    stats["not_confirmed"]
    for stats in experience_statistics.values()
)


total_neutral = sum(
    stats["neutral"]
    for stats in experience_statistics.values()
)


# ============================================================
# PENDING COUNT
# ============================================================

pending_windows = 0


for observation in observations:

    if not isinstance(
        observation,
        dict
    ):
        continue


    outcomes = observation.get(
        "outcomes",
        {}
    )


    if not isinstance(
        outcomes,
        dict
    ):
        continue


    for window_name in OUTCOME_WINDOWS:

        result = outcomes.get(
            window_name
        )


        if isinstance(
            result,
            dict
        ):

            if result.get(
                "status"
            ) == "pending":

                pending_windows += 1


# ============================================================
# SAVE LEARNING MEMORY
# ============================================================

learning_memory[
    "experience_statistics"
] = experience_statistics

learning_memory[
    "resolved_outcomes"
] = total_resolved

learning_memory[
    "confirmed_outcomes"
] = total_confirmed

learning_memory[
    "not_confirmed_outcomes"
] = total_not_confirmed

learning_memory[
    "neutral_outcomes"
] = total_neutral

learning_memory[
    "pending_windows"
] = pending_windows

learning_memory[
    "current_pattern_classification"
] = (
    pattern_learning_classification
)


try:

    with open(
        LEARNING_FILE,
        "wb"
    ) as f:

        pickle.dump(
            learning_memory,
            f
        )

    print(
        "PASS: mlai_learning_memory.bin saved."
    )

except Exception as e:

    print(
        "WARNING: Could not save learning memory:"
        f" {e}"
    )


# ============================================================
# PRINT RESULTS
# ============================================================

print()

print("=" * 70)
print(
    "MLAI v1.4 PATTERN + EXPERIENCE LEARNING ENGINE"
)
print("=" * 70)

print()

print("CURRENT MARKET CONTEXT")
print("-" * 70)

print(
    f"Directional character : "
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

print("CURRENT DIRECTION PATTERN")
print("-" * 70)

print(
    f"{current_direction_pattern}"
)

print()

print("EXPERIENCE RESOLUTION")
print("-" * 70)

print(
    f"Newly resolved windows : "
    f"{len(newly_resolved)}"
)

print(
    f"Confirmed             : "
    f"{resolved_confirmed}"
)

print(
    f"Not confirmed         : "
    f"{resolved_not_confirmed}"
)

print(
    f"Neutral               : "
    f"{resolved_neutral}"
)

print()

print("EXPERIENCE MEMORY")
print("-" * 70)

print(
    f"Observations stored   : "
    f"{len(observations)}"
)

print(
    f"Resolved windows      : "
    f"{total_resolved}"
)

print(
    f"Pending windows       : "
    f"{pending_windows}"
)

print()

print("EXPERIENCE PERFORMANCE")
print("-" * 70)

for window_name in (
    "4",
    "8",
    "16"
):

    stats = experience_statistics[
        window_name
    ]

    print(
        f"{window_name:>2} candles -> "
        f"resolved={stats['resolved']} | "
        f"confirmed={stats['confirmed']} | "
        f"not_confirmed={stats['not_confirmed']} | "
        f"neutral={stats['neutral']} | "
        f"accuracy={stats['accuracy']:.1f}%"
    )

print()

print("HISTORICAL PATTERN MEMORY")
print("-" * 70)

print(
    f"Unique direction patterns : "
    f"{len(learning_memory['patterns'])}"
)

print(
    f"Minimum occurrences        : "
    f"{MIN_PATTERN_OCCURRENCES}"
)

print()

print("CURRENT PATTERN EXPERIENCE")
print("-" * 70)

print(
    f"Pattern                  : "
    f"{current_direction_pattern}"
)

print(
    f"Historical status        : "
    f"{current_pattern_status}"
)

print(
    f"Classification            : "
    f"{pattern_learning_classification}"
)

if current_stats:

    print()

    print(
        "Historical outcomes for current pattern:"
    )

    for window_name in (
        "4",
        "8",
        "16"
    ):

        horizon = current_stats[
            "horizons"
        ].get(
            window_name
        )


        if not horizon:
            continue


        print(
            f" {window_name} candles -> "
            f"bullish={horizon['bullish_pct']:.1f}% | "
            f"bearish={horizon['bearish_pct']:.1f}% | "
            f"neutral={horizon['neutral_pct']:.1f}% | "
            f"dominant={horizon['dominant']}"
        )

else:

    print(
        "No sufficiently repeated historical "
        "match for the current pattern."
    )


# ============================================================
# BEST LEARNED PATTERNS
# ============================================================

ranked_patterns = []


for pattern, record in learning_memory[
    "patterns"
].items():

    horizon = record[
        "horizons"
    ].get(
        "8"
    )


    if not horizon:
        continue


    ranked_patterns.append(
        (
            horizon["dominant_pct"],
            record["occurrences"],
            pattern,
            horizon
        )
    )


ranked_patterns.sort(
    key=lambda x: (
        x[0],
        x[1]
    ),
    reverse=True
)


print()

print("BEST HISTORICALLY CONSISTENT PATTERNS")
print("-" * 70)


if ranked_patterns:

    for index, item in enumerate(
        ranked_patterns[
            :MAX_DISPLAY_PATTERNS
        ],
        start=1
    ):

        dominant_pct = item[0]

        occurrences = item[1]

        pattern = item[2]

        horizon = item[3]


        print(
            f"{index:02d}. {pattern}"
        )

        print(
            f"    occurrences={occurrences} | "
            f"8c dominant={horizon['dominant']} "
            f"{dominant_pct:.1f}% | "
            f"4c={horizon['bullish_pct']:.1f}%/"
            f"{horizon['bearish_pct']:.1f}%/"
            f"{horizon['neutral_pct']:.1f}% | "
            f"16c="
        )


        horizon_16 = learning_memory[
            "patterns"
        ][pattern][
            "horizons"
        ].get(
            "16"
        )


        if horizon_16:

            print(
                f"    "
                f"{horizon_16['bullish_pct']:.1f}%/"
                f"{horizon_16['bearish_pct']:.1f}%/"
                f"{horizon_16['neutral_pct']:.1f}%"
            )

else:

    print(
        "No sufficiently repeated patterns found."
    )


# ============================================================
# NEWLY RESOLVED EXPERIENCE
# ============================================================

print()

print("NEWLY RESOLVED EXPERIENCE")
print("-" * 70)


if newly_resolved:

    for item in newly_resolved[
        :20
    ]:

        print(
            f"{item['observation_id']} | "
            f"{item['window']} candles | "
            f"predicted={item['predicted']} | "
            f"actual={item['actual']} | "
            f"result={item['result']} | "
            f"change={item['change_pct']:+.3f}%"
        )

else:

    print(
        "No previously pending outcome became "
        "resolvable during this run."
    )


# ============================================================
# LEARNING INTERPRETATION
# ============================================================

print()

print("LEARNING INTERPRETATION")
print("-" * 70)


if total_resolved == 0:

    print(
        "MLAI does not yet have resolved experience "
        "windows."
    )

    print(
        "Historical pattern statistics are available, "
        "but they are not treated as learned personal "
        "experience."
    )

elif total_confirmed > total_not_confirmed:

    print(
        "Resolved experience currently contains more "
        "confirmed observations than not-confirmed "
        "observations."
    )

elif total_not_confirmed > total_confirmed:

    print(
        "Resolved experience currently contains more "
        "not-confirmed observations than confirmed "
        "observations."
    )

else:

    print(
        "Resolved experience is currently balanced."
    )


print()

print("LEARNING PRINCIPLES")
print("-" * 70)

print(
    "1. Historical patterns and actual experience "
    "are stored separately."
)

print(
    "2. Pending observations are never treated as "
    "successes or failures."
)

print(
    "3. Resolved outcomes are based on actual future "
    "market candles."
)

print(
    "4. Pattern frequency does not equal prediction "
    "certainty."
)

print(
    "5. Mixed outcomes remain visible."
)

print(
    "6. More observations are required before "
    "experience reliability becomes meaningful."
)

print(
    "7. MLAI does not create an automatic trading "
    "signal."
)


# ============================================================
# CURRENT MARKET STORY
# ============================================================

print()

print("CURRENT MARKET STORY")
print("-" * 70)


story = []

story.append(
    f"The current {PATTERN_LENGTH}-candle direction "
    f"pattern is {current_direction_pattern}."
)

story.append(
    f"The broader {len(recent)}-candle context has "
    f"a {current_direction} directional character."
)

story.append(
    f"Momentum is {momentum_context} and volatility "
    f"is {volatility_context}."
)

story.append(
    f"Rejection behaviour is {rejection_context}."
)

story.append(
    f"MLAI currently has {len(observations)} "
    f"experience observations."
)

story.append(
    f"{total_resolved} outcome windows have been "
    f"resolved and {pending_windows} remain pending."
)


if current_stats:

    horizon_8 = current_stats[
        "horizons"
    ].get(
        "8"
    )


    if horizon_8:

        story.append(
            f"The current pattern has historically "
            f"shown {horizon_8['bullish_pct']:.1f}% "
            f"bullish, "
            f"{horizon_8['bearish_pct']:.1f}% bearish "
            f"and "
            f"{horizon_8['neutral_pct']:.1f}% neutral "
            f"outcomes at the 8-candle horizon."
        )

else:

    story.append(
        "The current pattern does not yet have a "
        "sufficiently repeated historical match."
    )


if total_resolved > 0:

    story.append(
        "Actual resolved experience is now being "
        "separated from historical pattern frequency."
    )

else:

    story.append(
        "Actual resolved experience is not yet "
        "available in sufficient quantity."
    )


story.append(
    "MLAI v1.4 uses historical relationships and "
    "resolved experience as evidence while preserving "
    "uncertainty."
)


print(
    " ".join(story)
)


# ============================================================
# UPDATE PROJECT STATUS
# ============================================================

status_text = f"""

## MLAI v1.4 — Pattern + Experience Learning Engine

Status: COMPLETED

Market candles available:
{len(candles)}

Current pattern:
{current_direction_pattern}

Current directional character:
{current_direction}

Momentum:
{momentum_context}

Volatility:
{volatility_context}

Rejection:
{rejection_context}

Experience observations:
{len(observations)}

Resolved outcome windows:
{total_resolved}

Pending outcome windows:
{pending_windows}

Confirmed outcomes:
{total_confirmed}

Not-confirmed outcomes:
{total_not_confirmed}

Neutral outcomes:
{total_neutral}

Historical direction patterns:
{len(learning_memory["patterns"])}

Current pattern classification:
{pattern_learning_classification}

### v1.4 Purpose

MLAI v1.4 connects:

- Market memory
- Pattern discovery
- Experience memory
- Actual future outcomes
- Historical pattern behaviour
- Resolved experience

The engine keeps historical pattern frequency separate from
actual MLAI experience.

Pending observations are not treated as successful or failed.

Actual future candles are required before an observation can
become resolved experience.

### Learning Architecture

v1.1  Learning + Experience Memory              COMPLETED
v1.2  Outcome Resolution + Learning              COMPLETED
v1.3  Pattern Discovery Engine                  COMPLETED
v1.4  Pattern + Experience Learning Engine     COMPLETED
v1.5  Pattern Reliability + Experience Scoring  NEXT
v1.6  Market Regime Learning                    PENDING
v1.7  Multi-Timeframe Learning                  PENDING
v1.8  Adaptive Evidence Weighting               PENDING
v1.9  Continuous Learning Memory                PENDING
v2.0  MLAI Adaptive Market Brain                PENDING

### Important Principle

Historical frequency is not treated as guaranteed future
behaviour.

Resolved experience is based only on actual subsequent candles.

The system preserves uncertainty and does not generate an
automatic trading signal.
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
        "WARNING: Could not update "
        f"{STATUS_FILE}: {e}"
    )


# ============================================================
# FINAL
# ============================================================

print()

print(
    "PASS: MLAI v1.4 Pattern + Experience "
    "Learning Engine completed."
)

print("=" * 70)

