import os
import pickle
from collections import Counter, defaultdict
from statistics import mean


# ============================================================
# MLAI v1.3
# PATTERN DISCOVERY ENGINE
#
# Purpose:
# Discover recurring market behaviour from stored market memory.
#
# v1.3 builds on:
#   v0.3.1 Candle Relationships
#   v0.4   Market Structure
#   v0.5   Market Context
#   v0.6   Pattern / Context Engine
#   v0.7   Historical Behaviour
#   v0.8   Relationship + Reasoning
#   v0.9   Market Story
#   v1.0   Integrated MLAI Brain
#   v1.1   Experience Memory
#   v1.2   Outcome Resolution
#
# v1.3 adds:
#   - Behavioural sequence discovery
#   - Directional sequence discovery
#   - Candle relationship patterns
#   - Momentum / volatility combinations
#   - Rejection combinations
#   - Structure-like local patterns
#   - Historical outcome analysis
#   - Pattern frequency
#   - Pattern confirmation rate
#   - Pattern failure rate
#   - Pattern confidence
#   - Current-market pattern matching
#
# IMPORTANT:
# This is NOT a trading signal engine.
# It discovers historical behavioural relationships.
# Historical behaviour does not guarantee future behaviour.
# ============================================================


DATA_FILE = "market_data.bin"
EXPERIENCE_FILE = "mlai_experience.bin"
PATTERN_FILE = "mlai_pattern_memory.bin"
STATUS_FILE = "MLAI_PROJECT_STATUS.md"

ANALYSIS_CANDLES = 60

# Sequence length used for behavioural pattern discovery.
PATTERN_LENGTH = 6

# Number of future candles used to study historical outcomes.
OUTCOME_WINDOWS = [4, 8, 16]

# Minimum number of occurrences required before a pattern
# receives a stronger statistical classification.
MIN_PATTERN_OCCURRENCES = 3

# Maximum patterns displayed.
TOP_PATTERNS_TO_SHOW = 15

# Pattern similarity threshold.
CURRENT_PATTERN_THRESHOLD = 0.65


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

    high = get_value(candle, "high")
    low = get_value(candle, "low")

    return max(0.0, high - low)


def candle_body(candle):

    return abs(
        get_value(candle, "close")
        - get_value(candle, "open")
    )


def upper_wick(candle):

    high = get_value(candle, "high")

    return max(
        0.0,
        high
        - max(
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
        - low
    )


def safe_mean(values):

    return mean(values) if values else 0.0


def percentage_change(first, last):

    if first == 0:
        return 0.0

    return (
        (last - first)
        / abs(first)
    ) * 100.0


def clamp(value, minimum, maximum):

    return max(
        minimum,
        min(maximum, value)
    )


# ============================================================
# NORMALIZED CANDLE FEATURES
# ============================================================

def candle_feature(candle):

    o = get_value(candle, "open")
    h = get_value(candle, "high")
    l = get_value(candle, "low")
    c = get_value(candle, "close")

    rng = max(
        h - l,
        0.000001
    )

    body = abs(c - o)

    body_ratio = body / rng

    upper_ratio = (
        upper_wick(candle)
        / rng
    )

    lower_ratio = (
        lower_wick(candle)
        / rng
    )

    close_position = (
        (c - l) / rng
    )

    if c > o:
        direction = "B"

    elif c < o:
        direction = "S"

    else:
        direction = "N"

    if body_ratio >= 0.65:
        body_class = "strong"

    elif body_ratio >= 0.30:
        body_class = "medium"

    else:
        body_class = "weak"

    if upper_ratio >= 0.35:
        upper_class = "high"

    elif upper_ratio >= 0.15:
        upper_class = "medium"

    else:
        upper_class = "low"

    if lower_ratio >= 0.35:
        lower_class = "high"

    elif lower_ratio >= 0.15:
        lower_class = "medium"

    else:
        lower_class = "low"

    if close_position >= 0.70:
        close_class = "high"

    elif close_position <= 0.30:
        close_class = "low"

    else:
        close_class = "middle"

    return {
        "direction": direction,
        "body_class": body_class,
        "upper_class": upper_class,
        "lower_class": lower_class,
        "close_class": close_class,
        "body_ratio": body_ratio,
        "upper_ratio": upper_ratio,
        "lower_ratio": lower_ratio,
        "close_position": close_position,
        "range": rng,
    }


# ============================================================
# COMPACT BEHAVIOURAL SYMBOL
# ============================================================

def behaviour_symbol(candle):

    feature = candle_feature(candle)

    return (
        f"{feature['direction']}:"
        f"{feature['body_class']}:"
        f"U{feature['upper_class']}:"
        f"L{feature['lower_class']}"
    )


def direction_symbol(candle):

    return candle_feature(candle)["direction"]


# ============================================================
# SEQUENCE HELPERS
# ============================================================

def direction_sequence(sequence):

    return tuple(
        direction_symbol(c)
        for c in sequence
    )


def behaviour_sequence(sequence):

    return tuple(
        behaviour_symbol(c)
        for c in sequence
    )


# ============================================================
# OUTCOME CLASSIFICATION
# ============================================================

def classify_outcome(
    start_price,
    end_price
):

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

    return outcome, change


# ============================================================
# PATTERN RECORD CREATION
# ============================================================

def create_pattern_record(
    pattern_id,
    pattern_type,
    sequence,
    start_index
):

    return {
        "pattern_id": pattern_id,
        "pattern_type": pattern_type,
        "sequence": list(sequence),
        "length": len(sequence),
        "first_seen": start_index,
        "occurrences": 0,
        "outcomes": {
            str(window): {
                "resolved": 0,
                "bullish": 0,
                "bearish": 0,
                "neutral": 0,
                "changes": []
            }
            for window in OUTCOME_WINDOWS
        }
    }


# ============================================================
# UPDATE PATTERN OUTCOME
# ============================================================

def update_pattern_outcome(
    record,
    candles,
    outcome_start,
    outcome_window
):

    outcome_end = (
        outcome_start
        + outcome_window
    )

    if outcome_end >= len(candles):
        return

    start_price = get_value(
        candles[outcome_start],
        "close"
    )

    end_price = get_value(
        candles[outcome_end],
        "close"
    )

    outcome, change = classify_outcome(
        start_price,
        end_price
    )

    bucket = record["outcomes"][
        str(outcome_window)
    ]

    bucket["resolved"] += 1
    bucket[outcome] += 1

    bucket["changes"].append(
        round(change, 6)
    )


# ============================================================
# PATTERN STATISTICS
# ============================================================

def pattern_statistics(record):

    total_occurrences = record["occurrences"]

    statistics = {}

    for window in OUTCOME_WINDOWS:

        bucket = record["outcomes"][
            str(window)
        ]

        resolved = bucket["resolved"]

        if resolved == 0:

            statistics[window] = {
                "resolved": 0,
                "bullish_pct": 0.0,
                "bearish_pct": 0.0,
                "neutral_pct": 0.0,
                "dominant": "unresolved",
                "accuracy": 0.0,
                "average_change": 0.0
            }

            continue

        bullish_pct = (
            bucket["bullish"]
            / resolved
        ) * 100.0

        bearish_pct = (
            bucket["bearish"]
            / resolved
        ) * 100.0

        neutral_pct = (
            bucket["neutral"]
            / resolved
        ) * 100.0

        if bullish_pct >= bearish_pct and bullish_pct >= neutral_pct:
            dominant = "bullish"

        elif bearish_pct >= bullish_pct and bearish_pct >= neutral_pct:
            dominant = "bearish"

        else:
            dominant = "neutral"

        if dominant == "bullish":
            accuracy = bullish_pct

        elif dominant == "bearish":
            accuracy = bearish_pct

        else:
            accuracy = neutral_pct

        average_change = safe_mean(
            bucket["changes"]
        )

        statistics[window] = {
            "resolved": resolved,
            "bullish_pct": bullish_pct,
            "bearish_pct": bearish_pct,
            "neutral_pct": neutral_pct,
            "dominant": dominant,
            "accuracy": accuracy,
            "average_change": average_change
        }

    return statistics


# ============================================================
# LOAD MARKET MEMORY
# ============================================================

print("=" * 70)
print("MLAI v1.3 - LOADING MARKET MEMORY")
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
# SUPPORT BOTH MEMORY FORMATS
# ============================================================

if isinstance(
    market_data,
    dict
):

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

    candles = market_data.get(
        "candles",
        []
    )

else:

    print(
        "PASS: Legacy candle-list market memory loaded."
    )

    candles = market_data


if not isinstance(
    candles,
    (list, tuple)
):

    print(
        "ERROR: No candle list found in market_data.bin."
    )

    raise SystemExit(1)


candles = list(candles)

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


recent = candles[
    -ANALYSIS_CANDLES:
]

print(
    f"PASS: Using latest {len(recent)} candles."
)

print()

print(
    "Analysing latest 60 candles..."
)

print()


# ============================================================
# CURRENT MARKET CHARACTER
# ============================================================

current_directions = [
    candle_direction(c)
    for c in recent
]

bullish_count = (
    current_directions.count(
        "bullish"
    )
)

bearish_count = (
    current_directions.count(
        "bearish"
    )
)

neutral_count = (
    current_directions.count(
        "neutral"
    )
)


if bullish_count > bearish_count:
    current_direction = "bullish"

elif bearish_count > bullish_count:
    current_direction = "bearish"

else:
    current_direction = "mixed"


# ============================================================
# CURRENT REJECTION
# ============================================================

current_ranges = [
    candle_range(c)
    for c in recent
]

average_range = safe_mean(
    current_ranges
)

upper_rejections = 0
lower_rejections = 0

for candle in recent:

    rng = candle_range(candle)

    if rng <= 0:
        continue

    upper = upper_wick(candle)
    lower = lower_wick(candle)

    if upper >= rng * 0.20:
        upper_rejections += 1

    if lower >= rng * 0.20:
        lower_rejections += 1


if lower_rejections > upper_rejections:
    rejection_context = (
        "lower_rejection_dominant"
    )

elif upper_rejections > lower_rejections:
    rejection_context = (
        "upper_rejection_dominant"
    )

else:
    rejection_context = (
        "balanced_rejection"
    )


# ============================================================
# CURRENT MOMENTUM
# ============================================================

body_values = [
    candle_body(c)
    for c in recent
]

early_body = safe_mean(
    body_values[:15]
)

recent_body = safe_mean(
    body_values[-15:]
)

if recent_body > early_body * 1.15:
    momentum_context = "increasing"

elif recent_body < early_body * 0.85:
    momentum_context = "decreasing"

else:
    momentum_context = "stable"


# ============================================================
# CURRENT VOLATILITY
# ============================================================

early_range = safe_mean(
    current_ranges[:15]
)

recent_range = safe_mean(
    current_ranges[-15:]
)

if recent_range > early_range * 1.15:
    volatility_context = "expanding"

elif recent_range < early_range * 0.85:
    volatility_context = "contracting"

else:
    volatility_context = "stable"


# ============================================================
# CURRENT PATTERNS
# ============================================================

current_direction_pattern = (
    direction_sequence(
        recent[-PATTERN_LENGTH:]
    )
)

current_behaviour_pattern = (
    behaviour_sequence(
        recent[-PATTERN_LENGTH:]
    )
)


# ============================================================
# DISCOVER PATTERNS
# ============================================================

print(
    "PASS: Discovering recurring market behaviour..."
)

print()


direction_patterns = {}
behaviour_patterns = {}

direction_counter = Counter()
behaviour_counter = Counter()


# ============================================================
# HISTORICAL SCAN
# ============================================================

search_limit = (
    len(candles)
    - PATTERN_LENGTH
)

for start in range(
    0,
    search_limit
):

    sequence = candles[
        start:
        start + PATTERN_LENGTH
    ]

    direction_key = (
        direction_sequence(
            sequence
        )
    )

    behaviour_key = (
        behaviour_sequence(
            sequence
        )
    )

    direction_counter[
        direction_key
    ] += 1

    behaviour_counter[
        behaviour_key
    ] += 1

    # --------------------------------------------------------
    # Direction pattern
    # --------------------------------------------------------

    if direction_key not in direction_patterns:

        pattern_id = (
            f"DIR_{len(direction_patterns) + 1:05d}"
        )

        direction_patterns[
            direction_key
        ] = create_pattern_record(
            pattern_id,
            "direction_sequence",
            direction_key,
            start
        )

    direction_record = (
        direction_patterns[
            direction_key
        ]
    )

    direction_record[
        "occurrences"
    ] += 1

    # Outcome begins at the final candle
    # of the observed sequence.

    outcome_start = (
        start
        + PATTERN_LENGTH
        - 1
    )

    for window in OUTCOME_WINDOWS:

        update_pattern_outcome(
            direction_record,
            candles,
            outcome_start,
            window
        )

    # --------------------------------------------------------
    # Behaviour pattern
    # --------------------------------------------------------

    if behaviour_key not in behaviour_patterns:

        pattern_id = (
            f"BEH_{len(behaviour_patterns) + 1:05d}"
        )

        behaviour_patterns[
            behaviour_key
        ] = create_pattern_record(
            pattern_id,
            "behaviour_sequence",
            behaviour_key,
            start
        )

    behaviour_record = (
        behaviour_patterns[
            behaviour_key
        ]
    )

    behaviour_record[
        "occurrences"
    ] += 1

    for window in OUTCOME_WINDOWS:

        update_pattern_outcome(
            behaviour_record,
            candles,
            outcome_start,
            window
        )


# ============================================================
# REMOVE LOW-FREQUENCY PATTERNS
# ============================================================

direction_patterns = {

    key: value

    for key, value
    in direction_patterns.items()

    if value["occurrences"]
    >= MIN_PATTERN_OCCURRENCES
}


behaviour_patterns = {

    key: value

    for key, value
    in behaviour_patterns.items()

    if value["occurrences"]
    >= MIN_PATTERN_OCCURRENCES
}


print(
    "PASS: Pattern discovery completed."
)

print()


# ============================================================
# PATTERN SCORING
# ============================================================

def pattern_score(record):

    stats = pattern_statistics(
        record
    )

    window_scores = []

    for window in OUTCOME_WINDOWS:

        item = stats[window]

        if item["resolved"] > 0:

            window_scores.append(
                item["accuracy"]
            )

    average_accuracy = safe_mean(
        window_scores
    )

    occurrence_factor = clamp(
        record["occurrences"]
        / 20.0,
        0.0,
        1.0
    )

    resolved_total = sum(
        stats[w]["resolved"]
        for w in OUTCOME_WINDOWS
    )

    resolution_factor = clamp(
        resolved_total
        / max(
            1,
            record["occurrences"]
            * len(OUTCOME_WINDOWS)
        ),
        0.0,
        1.0
    )

    score = (
        average_accuracy
        * 0.60
        + occurrence_factor
        * 20.0
        + resolution_factor
        * 20.0
    )

    return score


# ============================================================
# SORT PATTERNS
# ============================================================

top_direction_patterns = sorted(
    direction_patterns.values(),
    key=pattern_score,
    reverse=True
)

top_behaviour_patterns = sorted(
    behaviour_patterns.values(),
    key=pattern_score,
    reverse=True
)


# ============================================================
# CURRENT PATTERN MATCHING
# ============================================================

def exact_current_match(
    record,
    current_sequence
):

    return (
        tuple(record["sequence"])
        == tuple(current_sequence)
    )


current_direction_matches = []

for record in direction_patterns.values():

    if exact_current_match(
        record,
        current_direction_pattern
    ):

        current_direction_matches.append(
            record
        )


current_behaviour_matches = []

for record in behaviour_patterns.values():

    if exact_current_match(
        record,
        current_behaviour_pattern
    ):

        current_behaviour_matches.append(
            record
        )


# ============================================================
# CURRENT PATTERN EXPERIENCE
# ============================================================

def summarize_current_matches(
    matches
):

    result = {}

    for window in OUTCOME_WINDOWS:

        total = 0
        bullish = 0
        bearish = 0
        neutral = 0
        changes = []

        for record in matches:

            bucket = record[
                "outcomes"
            ][str(window)]

            total += bucket[
                "resolved"
            ]

            bullish += bucket[
                "bullish"
            ]

            bearish += bucket[
                "bearish"
            ]

            neutral += bucket[
                "neutral"
            ]

            changes.extend(
                bucket[
                    "changes"
                ]
            )

        if total == 0:

            result[window] = {
                "resolved": 0,
                "bullish_pct": 0.0,
                "bearish_pct": 0.0,
                "neutral_pct": 0.0,
                "dominant": "unresolved",
                "average_change": 0.0
            }

            continue

        bullish_pct = (
            bullish / total
        ) * 100.0

        bearish_pct = (
            bearish / total
        ) * 100.0

        neutral_pct = (
            neutral / total
        ) * 100.0

        if (
            bullish_pct >= bearish_pct
            and bullish_pct >= neutral_pct
        ):
            dominant = "bullish"

        elif (
            bearish_pct >= bullish_pct
            and bearish_pct >= neutral_pct
        ):
            dominant = "bearish"

        else:
            dominant = "neutral"

        result[window] = {
            "resolved": total,
            "bullish_pct": bullish_pct,
            "bearish_pct": bearish_pct,
            "neutral_pct": neutral_pct,
            "dominant": dominant,
            "average_change": safe_mean(
                changes
            )
        }

    return result


current_direction_experience = (
    summarize_current_matches(
        current_direction_matches
    )
)

current_behaviour_experience = (
    summarize_current_matches(
        current_behaviour_matches
    )
)


# ============================================================
# GENERAL PATTERN COUNTS
# ============================================================

direction_occurrences = sum(
    record["occurrences"]
    for record
    in direction_patterns.values()
)

behaviour_occurrences = sum(
    record["occurrences"]
    for record
    in behaviour_patterns.values()
)


# ============================================================
# LOAD EXPERIENCE MEMORY
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

        print(
            "PASS: Existing MLAI experience memory loaded."
        )

    except Exception as e:

        print(
            "WARNING: Could not load "
            f"{EXPERIENCE_FILE}: {e}"
        )

else:

    print(
        "INFO: No MLAI experience memory found."
    )

print()


# ============================================================
# EXPERIENCE SUMMARY
# ============================================================

experience_observations = []

if isinstance(
    experience_memory,
    dict
):

    possible_observations = (
        experience_memory.get(
            "observations"
        )
    )

    if isinstance(
        possible_observations,
        list
    ):

        experience_observations = (
            possible_observations
        )

    elif isinstance(
        possible_observations,
        dict
    ):

        experience_observations = list(
            possible_observations.values()
        )


resolved_experience = 0
pending_experience = 0

for observation in experience_observations:

    outcomes = observation.get(
        "outcomes",
        {}
    )

    resolved_any = False

    for window in OUTCOME_WINDOWS:

        outcome = outcomes.get(
            str(window),
            outcomes.get(window)
        )

        if isinstance(
            outcome,
            dict
        ):

            status = outcome.get(
                "status",
                "pending"
            )

            if status != "pending":
                resolved_any = True

    if resolved_any:
        resolved_experience += 1

    else:
        pending_experience += 1


# ============================================================
# SAVE PATTERN MEMORY
# ============================================================

pattern_memory = {

    "mlai_version": "1.3",

    "created_at": __import__(
        "datetime"
    ).datetime.now(
        __import__(
            "datetime"
        ).timezone.utc
    ).isoformat(),

    "source": (
        market_data.get(
            "source"
        )
        if isinstance(
            market_data,
            dict
        )
        else "unknown"
    ),

    "analysis": {

        "candles_available": len(candles),

        "analysis_candles": ANALYSIS_CANDLES,

        "pattern_length": PATTERN_LENGTH,

        "outcome_windows": OUTCOME_WINDOWS,

        "minimum_pattern_occurrences":
            MIN_PATTERN_OCCURRENCES
    },

    "current_market": {

        "direction": current_direction,

        "bullish_candles":
            bullish_count,

        "bearish_candles":
            bearish_count,

        "neutral_candles":
            neutral_count,

        "momentum":
            momentum_context,

        "volatility":
            volatility_context,

        "rejection":
            rejection_context,

        "current_direction_pattern":
            list(
                current_direction_pattern
            ),

        "current_behaviour_pattern":
            list(
                current_behaviour_pattern
            )
    },

    "pattern_statistics": {

        "direction_patterns":
            len(direction_patterns),

        "behaviour_patterns":
            len(behaviour_patterns),

        "direction_occurrences":
            direction_occurrences,

        "behaviour_occurrences":
            behaviour_occurrences
    },

    "direction_patterns":
        list(
            direction_patterns.values()
        ),

    "behaviour_patterns":
        list(
            behaviour_patterns.values()
        ),

    "current_pattern_matches": {

        "direction_matches":
            [
                r["pattern_id"]
                for r
                in current_direction_matches
            ],

        "behaviour_matches":
            [
                r["pattern_id"]
                for r
                in current_behaviour_matches
            ]
    },

    "experience_summary": {

        "observations":
            len(experience_observations),

        "resolved":
            resolved_experience,

        "pending":
            pending_experience
    }
}


try:

    with open(
        PATTERN_FILE,
        "wb"
    ) as f:

        pickle.dump(
            pattern_memory,
            f
        )

    print(
        f"PASS: {PATTERN_FILE} saved."
    )

except Exception as e:

    print(
        f"ERROR: Could not save "
        f"{PATTERN_FILE}: {e}"
    )

print()


# ============================================================
# OUTPUT
# ============================================================

print("=" * 70)
print(
    "MLAI v1.3 PATTERN DISCOVERY ENGINE"
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

print("CURRENT BEHAVIOURAL PATTERN")
print("-" * 70)

print(
    "Direction sequence    : "
    + " ".join(
        current_direction_pattern
    )
)

print()

for i, symbol in enumerate(
    current_behaviour_pattern,
    start=1
):

    print(
        f"{i:02d}. {symbol}"
    )

print()

print("PATTERN DISCOVERY")
print("-" * 70)

print(
    f"Direction patterns    : "
    f"{len(direction_patterns)}"
)

print(
    f"Behaviour patterns    : "
    f"{len(behaviour_patterns)}"
)

print(
    f"Direction occurrences : "
    f"{direction_occurrences}"
)

print(
    f"Behaviour occurrences : "
    f"{behaviour_occurrences}"
)

print()


# ============================================================
# BEST DIRECTION PATTERNS
# ============================================================

print("BEST DIRECTION PATTERNS")
print("-" * 70)

if top_direction_patterns:

    for i, record in enumerate(
        top_direction_patterns[
            :TOP_PATTERNS_TO_SHOW
        ],
        start=1
    ):

        stats = pattern_statistics(
            record
        )

        sequence = " ".join(
            record["sequence"]
        )

        print(
            f"{i:02d}. "
            f"{sequence}"
        )

        print(
            f"    occurrences="
            f"{record['occurrences']} | "
            f"4c="
            f"{stats[4]['dominant']} "
            f"{stats[4]['accuracy']:.1f}% | "
            f"8c="
            f"{stats[8]['dominant']} "
            f"{stats[8]['accuracy']:.1f}% | "
            f"16c="
            f"{stats[16]['dominant']} "
            f"{stats[16]['accuracy']:.1f}%"
        )

else:

    print(
        "No direction patterns found."
    )

print()


# ============================================================
# BEST BEHAVIOURAL PATTERNS
# ============================================================

print("BEST BEHAVIOURAL PATTERNS")
print("-" * 70)

if top_behaviour_patterns:

    for i, record in enumerate(
        top_behaviour_patterns[
            :TOP_PATTERNS_TO_SHOW
        ],
        start=1
    ):

        stats = pattern_statistics(
            record
        )

        sequence = " | ".join(
            record["sequence"]
        )

        print(
            f"{i:02d}. "
            f"{sequence}"
        )

        print(
            f"    occurrences="
            f"{record['occurrences']} | "
            f"4c="
            f"{stats[4]['dominant']} "
            f"{stats[4]['accuracy']:.1f}% | "
            f"8c="
            f"{stats[8]['dominant']} "
            f"{stats[8]['accuracy']:.1f}% | "
            f"16c="
            f"{stats[16]['dominant']} "
            f"{stats[16]['accuracy']:.1f}%"
        )

else:

    print(
        "No behavioural patterns found."
    )

print()


# ============================================================
# CURRENT DIRECTION PATTERN EXPERIENCE
# ============================================================

print(
    "CURRENT DIRECTION PATTERN EXPERIENCE"
)

print("-" * 70)

if current_direction_matches:

    print(
        f"Exact historical matches : "
        f"{len(current_direction_matches)}"
    )

    for window in OUTCOME_WINDOWS:

        result = (
            current_direction_experience[
                window
            ]
        )

        print(
            f"{window:2d} candles -> "
            f"resolved="
            f"{result['resolved']} | "
            f"bullish="
            f"{result['bullish_pct']:.1f}% | "
            f"bearish="
            f"{result['bearish_pct']:.1f}% | "
            f"neutral="
            f"{result['neutral_pct']:.1f}% | "
            f"dominant="
            f"{result['dominant']}"
        )

else:

    print(
        "No exact historical direction-pattern match."
    )

print()


# ============================================================
# CURRENT BEHAVIOUR PATTERN EXPERIENCE
# ============================================================

print(
    "CURRENT BEHAVIOUR PATTERN EXPERIENCE"
)

print("-" * 70)

if current_behaviour_matches:

    print(
        f"Exact historical matches : "
        f"{len(current_behaviour_matches)}"
    )

    for window in OUTCOME_WINDOWS:

        result = (
            current_behaviour_experience[
                window
            ]
        )

        print(
            f"{window:2d} candles -> "
            f"resolved="
            f"{result['resolved']} | "
            f"bullish="
            f"{result['bullish_pct']:.1f}% | "
            f"bearish="
            f"{result['bearish_pct']:.1f}% | "
            f"neutral="
            f"{result['neutral_pct']:.1f}% | "
            f"dominant="
            f"{result['dominant']}"
        )

else:

    print(
        "No exact historical behaviour-pattern match."
    )

print()


# ============================================================
# EXPERIENCE MEMORY
# ============================================================

print("EXPERIENCE MEMORY")
print("-" * 70)

print(
    f"Observations stored   : "
    f"{len(experience_observations)}"
)

print(
    f"Resolved observations  : "
    f"{resolved_experience}"
)

print(
    f"Pending observations   : "
    f"{pending_experience}"
)

print()


# ============================================================
# PATTERN INTERPRETATION
# ============================================================

pattern_interpretation = (
    "insufficient_pattern_experience"
)

best_current_result = None

for window in OUTCOME_WINDOWS:

    result = (
        current_behaviour_experience[
            window
        ]
    )

    if result["resolved"] > 0:

        if (
            best_current_result is None
            or result["resolved"]
            > best_current_result["resolved"]
        ):

            best_current_result = result


if best_current_result is not None:

    dominant = (
        best_current_result[
            "dominant"
        ]
    )

    accuracy = (
        best_current_result[
            "bullish_pct"
        ]
        if dominant == "bullish"
        else
        best_current_result[
            "bearish_pct"
        ]
        if dominant == "bearish"
        else
        best_current_result[
            "neutral_pct"
        ]
    )

    if accuracy >= 65:

        pattern_interpretation = (
            f"historically_strong_{dominant}_pattern"
        )

    elif accuracy >= 55:

        pattern_interpretation = (
            f"historically_moderate_{dominant}_pattern"
        )

    else:

        pattern_interpretation = (
            "historically_mixed_pattern"
        )


print("PATTERN INTERPRETATION")
print("-" * 70)

print(
    f"Classification: "
    f"{pattern_interpretation}"
)

print()


# ============================================================
# LEARNING PRINCIPLES
# ============================================================

print("LEARNING PRINCIPLES")
print("-" * 70)

print(
    "1. Patterns are discovered from observed market behaviour."
)

print(
    "2. Repeated patterns are separated from isolated events."
)

print(
    "3. Historical outcomes are measured separately at "
    "4, 8 and 16 candle horizons."
)

print(
    "4. Unresolved future outcomes are not treated as learning evidence."
)

print(
    "5. Pattern frequency and historical outcomes are preserved."
)

print(
    "6. A historical pattern does not guarantee a future outcome."
)

print(
    "7. Pattern discovery is evidence generation, not automatic prediction."
)

print()


# ============================================================
# MARKET STORY
# ============================================================

print("CURRENT MARKET STORY")
print("-" * 70)

story_parts = []

story_parts.append(
    f"The current {PATTERN_LENGTH}-candle "
    f"behavioural sequence has a "
    f"{current_direction} directional character."
)

story_parts.append(
    f"Momentum is {momentum_context} "
    f"and volatility is {volatility_context}."
)

story_parts.append(
    f"Rejection behaviour is "
    f"{rejection_context}."
)

story_parts.append(
    f"MLAI discovered "
    f"{len(direction_patterns)} recurring "
    f"direction patterns and "
    f"{len(behaviour_patterns)} recurring "
    f"behaviour patterns using the available "
    f"market memory."
)

if current_direction_matches:

    story_parts.append(
        f"The current directional sequence has "
        f"{len(current_direction_matches)} "
        f"exact historical matches."
    )

else:

    story_parts.append(
        "The current directional sequence has "
        "no exact historical match in the "
        "discovered pattern memory."
    )


if current_behaviour_matches:

    story_parts.append(
        f"The current detailed behavioural sequence "
        f"has {len(current_behaviour_matches)} "
        f"exact historical matches."
    )

else:

    story_parts.append(
        "The current detailed behavioural sequence "
        "has no exact historical match."
    )


if resolved_experience > 0:

    story_parts.append(
        f"MLAI also has "
        f"{resolved_experience} resolved "
        f"experience observations that can "
        f"eventually support deeper learning."
    )

else:

    story_parts.append(
        "MLAI does not yet have resolved "
        "experience observations, so the new "
        "pattern memory is primarily based on "
        "historical candle behaviour."
    )


story_parts.append(
    "The discovered patterns represent "
    "historical relationships rather than "
    "guaranteed future behaviour."
)

print(
    " ".join(story_parts)
)

print()


# ============================================================
# UPDATE PROJECT STATUS
# ============================================================

status_text = f"""

## MLAI v1.3 — Pattern Discovery Engine

Status: COMPLETED

Market candles available:
{len(candles)}

Analysis candles:
{ANALYSIS_CANDLES}

Pattern length:
{PATTERN_LENGTH}

Outcome windows:
{OUTCOME_WINDOWS}

Direction patterns discovered:
{len(direction_patterns)}

Behaviour patterns discovered:
{len(behaviour_patterns)}

Direction pattern occurrences:
{direction_occurrences}

Behaviour pattern occurrences:
{behaviour_occurrences}

Current direction:
{current_direction}

Current momentum:
{momentum_context}

Current volatility:
{volatility_context}

Current rejection:
{rejection_context}

Current pattern interpretation:
{pattern_interpretation}

Exact current direction matches:
{len(current_direction_matches)}

Exact current behaviour matches:
{len(current_behaviour_matches)}

Experience observations:
{len(experience_observations)}

Resolved experience observations:
{resolved_experience}

Pending experience observations:
{pending_experience}

### v1.3 Purpose

MLAI v1.3 introduces a Pattern Discovery Engine.

The engine searches historical market memory for recurring:

- Direction sequences
- Candle behaviour sequences
- Body-strength relationships
- Upper-wick relationships
- Lower-wick relationships
- Directional continuation/reversal sequences

Each discovered pattern is evaluated across:

- 4-candle outcomes
- 8-candle outcomes
- 16-candle outcomes

Pattern outcomes are classified as:

- Bullish
- Bearish
- Neutral
- Unresolved

Pattern frequency, historical outcome distribution and average
historical movement are preserved.

### Important Learning Rule

MLAI does not treat a discovered pattern as a guaranteed prediction.

A pattern becomes more useful only when repeated observations provide
sufficient historical evidence.

Unresolved experience observations remain separate from resolved
experience.

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
v1.3    Pattern Discovery Engine          COMPLETED
v1.4    Market Regime Memory              NEXT
v1.5    Adaptive Evidence Engine          PENDING
v1.6    Continuous Learning Cycle         PENDING
v1.7    Multi-Timeframe MLAI              PENDING
v1.8    Advanced Market Structure         PENDING
v1.9    Prediction Research Engine        PENDING
v2.0    Continuous MLAI Brain             PENDING
Final   Continuous Data + Memory +
        Analysis + Learning               PENDING
"""


try:

    with open(
        STATUS_FILE,
        "a",
        encoding="utf-8"
    ) as f:

        f.write(
            "\n"
            + status_text
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
    "PASS: MLAI v1.3 Pattern Discovery Engine completed."
)

print("=" * 70)