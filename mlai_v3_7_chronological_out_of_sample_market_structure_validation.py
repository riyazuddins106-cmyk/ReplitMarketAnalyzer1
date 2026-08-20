import os
import pickle
import math
import json
from collections import Counter


# ============================================================
# MLAI v3.7
# CHRONOLOGICAL OUT-OF-SAMPLE MARKET STRUCTURE VALIDATION
#
# FILE:
#     mlai_v3_7_chronological_out_of_sample_market_structure_validation.py
#
# PURPOSE
# ------------------------------------------------------------
# This experiment tests whether market-structure information
# has measurable future directional value.
#
# It is a VALIDATION experiment.
#
# It does NOT:
#
#     - modify market_data.bin
#     - modify mlai_v31.py
#     - modify production MLAI
#     - modify learning memory
#     - train a production model
#     - place trades
#
# The experiment performs:
#
#     1. Chronological candle normalization
#     2. Chronological data integrity validation
#     3. Confirmed swing detection
#     4. HH / HL / LH / LL classification
#     5. BOS / CHoCH detection
#     6. Proper swing confirmation timing
#     7. Training-period analysis
#     8. Out-of-sample validation
#     9. Future outcome testing
#    10. H+4 / H+8 / H+16 horizons
#    11. Accuracy
#    12. Precision
#    13. Recall
#    14. Coverage
#    15. Baseline comparison
#    16. Look-ahead-bias checks
#    17. Chronological integrity checks
#
# IMPORTANT
# ------------------------------------------------------------
# This program does NOT claim that market structure predicts
# the market.
#
# It measures whether historical structure labels are associated
# with subsequent price movement in the supplied dataset.
#
# Statistical association is NOT proof of tradable profitability.
#
# ============================================================


# ============================================================
# CONFIGURATION
# ============================================================

MARKET_FILE = "market_data.bin"

OUTPUT_REPORT = (
    "MLAI_V37_CHRONOLOGICAL_OUT_OF_SAMPLE_MARKET_STRUCTURE_VALIDATION_REPORT.md"
)

OUTPUT_BIN = (
    "MLAI_V37_CHRONOLOGICAL_OUT_OF_SAMPLE_MARKET_STRUCTURE_VALIDATION.bin"
)

# ------------------------------------------------------------
# Swing configuration
# ------------------------------------------------------------

SWING_LOOKBACK = 3

# Minimum OHLC candles required.

MIN_CANDLES = 100

# ------------------------------------------------------------
# Chronological split
#
# 70% = historical/training period
# 30% = untouched out-of-sample validation period
# ------------------------------------------------------------

TRAIN_RATIO = 0.70

# ------------------------------------------------------------
# Structural movement threshold
#
# 0.0002 = 0.02%
# ------------------------------------------------------------

MIN_STRUCTURE_MOVE = 0.0002

# ------------------------------------------------------------
# Future outcome horizons
# ------------------------------------------------------------

HORIZONS = [4, 8, 16]

# ------------------------------------------------------------
# Minimum directional movement required to classify a future
# outcome.
#
# Example:
#
# 0.0005 = 0.05%
#
# If price rises more than this threshold:
#
#     BUY
#
# If price falls more than this threshold:
#
#     SELL
#
# Otherwise:
#
#     NEUTRAL
# ------------------------------------------------------------

OUTCOME_THRESHOLD = 0.0005

# ------------------------------------------------------------
# Number of records to print
# ------------------------------------------------------------

MAX_SWINGS_TO_PRINT = 30
MAX_EVENTS_TO_PRINT = 30
MAX_VALIDATION_SIGNALS_TO_PRINT = 30

# ------------------------------------------------------------
# Baseline
#
# The baseline predicts the majority class in the TRAINING
# period and applies that fixed class to the OOS period.
# ------------------------------------------------------------

USE_TRAINING_MAJORITY_BASELINE = True


# ============================================================
# HEADER
# ============================================================

print("=" * 80)
print("MLAI v3.7 CHRONOLOGICAL OUT-OF-SAMPLE MARKET STRUCTURE VALIDATION")
print("=" * 80)

print(
    """
PURPOSE
-------

Test whether confirmed market structure has measurable
future directional value.

The experiment tests:

    HH
    HL
    LH
    LL

    BOS_BULLISH
    BOS_BEARISH

    CHoCH_BULLISH
    CHoCH_BEARISH

against future price outcomes at:

    H+4
    H+8
    H+16

The experiment is chronological.

TRAINING DATA:
    Historical first 70%

OUT-OF-SAMPLE DATA:
    Final 30%

IMPORTANT:

    The OOS period is never used to determine the baseline.

    Confirmed swing information becomes available only after
    the required future confirmation candles exist.

    No future outcome is allowed to influence the signal.

    This is a research validation experiment, NOT a trading
    system and NOT a production MLAI model.
"""
)

print("=" * 80)


# ============================================================
# PROTECTION CHECK
# ============================================================

print()
print("=" * 80)
print("PROTECTION CHECK")
print("=" * 80)

print("market_data.bin : READ ONLY")
print("Production MLAI : NOT MODIFIED")
print("Learning memory : NOT MODIFIED")
print("Trading         : DISABLED")
print("Model training  : DISABLED")
print("Internet        : NOT REQUIRED")
print("Output          : Separate validation files only")


# ============================================================
# LOAD MARKET DATA
# ============================================================

if not os.path.exists(MARKET_FILE):

    raise FileNotFoundError(
        f"Required file not found: {MARKET_FILE}"
    )


with open(MARKET_FILE, "rb") as f:

    market_data = pickle.load(f)


print()
print("Data type:", type(market_data).__name__)


if not isinstance(market_data, dict):

    raise ValueError(
        "Unexpected market_data.bin structure. "
        "Expected a dictionary."
    )


candles = market_data.get("candles", [])


print("Total raw candles:", len(candles))


if len(candles) < MIN_CANDLES:

    raise ValueError(
        f"Not enough candles. "
        f"Required at least {MIN_CANDLES}, "
        f"found {len(candles)}."
    )


# ============================================================
# CANDLE NORMALIZATION
# ============================================================

def normalize_candle(candle, original_index):

    timestamp = None

    open_price = None
    high = None
    low = None
    close = None
    volume = None

    if isinstance(candle, dict):

        timestamp = (
            candle.get("timestamp")
            if candle.get("timestamp") is not None
            else candle.get("time")
        )

        if timestamp is None:
            timestamp = candle.get("datetime")

        if timestamp is None:
            timestamp = candle.get("date")

        open_price = (
            candle.get("open")
            if candle.get("open") is not None
            else candle.get("o")
        )

        high = (
            candle.get("high")
            if candle.get("high") is not None
            else candle.get("h")
        )

        low = (
            candle.get("low")
            if candle.get("low") is not None
            else candle.get("l")
        )

        close = (
            candle.get("close")
            if candle.get("close") is not None
            else candle.get("c")
        )

        volume = (
            candle.get("volume")
            if candle.get("volume") is not None
            else candle.get("v")
        )

    elif isinstance(candle, (list, tuple)):

        if len(candle) >= 5:

            timestamp = candle[0]

            open_price = candle[1]
            high = candle[2]
            low = candle[3]
            close = candle[4]

            if len(candle) >= 6:

                volume = candle[5]

    if (
        open_price is None
        or high is None
        or low is None
        or close is None
    ):

        return None

    try:

        open_price = float(open_price)
        high = float(high)
        low = float(low)
        close = float(close)

    except (TypeError, ValueError):

        return None

    if not all(
        math.isfinite(value)
        for value in (
            open_price,
            high,
            low,
            close,
        )
    ):

        return None

    # --------------------------------------------------------
    # OHLC integrity
    # --------------------------------------------------------

    if high < low:
        return None

    if high < open_price:
        return None

    if high < close:
        return None

    if low > open_price:
        return None

    if low > close:
        return None

    return {

        "index": original_index,

        "timestamp": timestamp,

        "open": open_price,

        "high": high,

        "low": low,

        "close": close,

        "volume": volume,
    }


# ============================================================
# BUILD NORMALIZED DATASET
# ============================================================

normalized_candles = []

invalid_candle_count = 0


for original_index, candle in enumerate(candles):

    normalized = normalize_candle(
        candle,
        original_index
    )

    if normalized is not None:

        normalized_candles.append(
            normalized
        )

    else:

        invalid_candle_count += 1


if len(normalized_candles) < MIN_CANDLES:

    raise ValueError(
        "Not enough valid candles after normalization."
    )


print()
print("=" * 80)
print("DATA QUALITY")
print("=" * 80)

print(
    "Valid OHLC candles:",
    len(normalized_candles)
)

print(
    "Invalid candles skipped:",
    invalid_candle_count
)


# ============================================================
# BASIC ARRAYS
# ============================================================

opens = [
    candle["open"]
    for candle in normalized_candles
]

highs = [
    candle["high"]
    for candle in normalized_candles
]

lows = [
    candle["low"]
    for candle in normalized_candles
]

closes = [
    candle["close"]
    for candle in normalized_candles
]


# ============================================================
# DATA ORDER CHECK
# ============================================================

def check_timestamp_order(candles):

    timestamps = [

        candle["timestamp"]

        for candle in candles

        if candle["timestamp"] is not None
    ]

    if len(timestamps) < 2:

        return {
            "available": False,
            "ordered": None,
        }

    ordered = all(

        timestamps[i] <= timestamps[i + 1]

        for i in range(
            len(timestamps) - 1
        )
    )

    return {
        "available": True,
        "ordered": ordered,
    }


timestamp_check = check_timestamp_order(
    normalized_candles
)


print()
print("=" * 80)
print("CHRONOLOGICAL DATA CHECK")
print("=" * 80)

if not timestamp_check["available"]:

    print(
        "Timestamp order: NOT AVAILABLE"
    )

elif timestamp_check["ordered"]:

    print(
        "Timestamp order: PASS"
    )

else:

    print(
        "Timestamp order: FAIL"
    )

    raise ValueError(
        "Market candles are not chronologically ordered."
    )


# ============================================================
# NUMERIC HELPERS
# ============================================================

def percentage_change(start, end):

    if start == 0:

        return 0.0

    return (
        end / start
    ) - 1.0


def mean(values):

    if not values:

        return 0.0

    return (
        sum(values)
        / len(values)
    )


# ============================================================
# FUTURE OUTCOME CLASSIFICATION
# ============================================================

def classify_future_outcome(
    entry_price,
    future_price,
    threshold=OUTCOME_THRESHOLD
):

    change = percentage_change(
        entry_price,
        future_price
    )

    if change >= threshold:

        return "BUY"

    if change <= -threshold:

        return "SELL"

    return "NEUTRAL"


# ============================================================
# SWING DETECTION
# ============================================================

def detect_confirmed_swings(
    candles,
    lookback=SWING_LOOKBACK
):

    """
    Detects swings while explicitly recording their
    confirmation index.

    Candidate:

        index

    Confirmation:

        index + lookback

    This is critical.

    Example with lookback=3:

        candidate swing = 100
        confirmed at    = 103

    The swing MUST NOT be available to the algorithm
    before candle 103.
    """

    swings = []

    total = len(candles)

    if total < (
        lookback * 2 + 1
    ):

        return swings

    for index in range(
        lookback,
        total - lookback
    ):

        current_high = highs[index]

        left_highs = highs[
            index - lookback:index
        ]

        right_highs = highs[
            index + 1:index + lookback + 1
        ]

        if (
            current_high >= max(left_highs)
            and current_high >= max(right_highs)
        ):

            confirmation_index = (
                index + lookback
            )

            swings.append({

                "type":
                    "SWING_HIGH",

                "index":
                    index,

                "confirmation_index":
                    confirmation_index,

                "original_index":
                    candles[index]["index"],

                "price":
                    current_high,

                "timestamp":
                    candles[index]["timestamp"],
            })

        current_low = lows[index]

        left_lows = lows[
            index - lookback:index
        ]

        right_lows = lows[
            index + 1:index + lookback + 1
        ]

        if (
            current_low <= min(left_lows)
            and current_low <= min(right_lows)
        ):

            confirmation_index = (
                index + lookback
            )

            swings.append({

                "type":
                    "SWING_LOW",

                "index":
                    index,

                "confirmation_index":
                    confirmation_index,

                "original_index":
                    candles[index]["index"],

                "price":
                    current_low,

                "timestamp":
                    candles[index]["timestamp"],
            })

    swings.sort(
        key=lambda item: (
            item["confirmation_index"],
            item["index"],
            item["type"],
        )
    )

    return swings


raw_swings = detect_confirmed_swings(
    normalized_candles
)


print()
print("=" * 80)
print("CONFIRMED SWING DETECTION")
print("=" * 80)

print(
    "Raw confirmed swings:",
    len(raw_swings)
)


# ============================================================
# CLEAN SAME-TYPE SWINGS
# ============================================================

def clean_swings(swings):

    if not swings:

        return []

    cleaned = []

    for swing in swings:

        if not cleaned:

            cleaned.append(
                swing
            )

            continue

        previous = cleaned[-1]

        if previous["type"] != swing["type"]:

            cleaned.append(
                swing
            )

            continue

        if swing["type"] == "SWING_HIGH":

            if swing["price"] > previous["price"]:

                cleaned[-1] = swing

            elif swing["price"] == previous["price"]:

                if (
                    swing["confirmation_index"]
                    >= previous["confirmation_index"]
                ):

                    cleaned[-1] = swing

        else:

            if swing["price"] < previous["price"]:

                cleaned[-1] = swing

            elif swing["price"] == previous["price"]:

                if (
                    swing["confirmation_index"]
                    >= previous["confirmation_index"]
                ):

                    cleaned[-1] = swing

    return cleaned


cleaned_swings = clean_swings(
    raw_swings
)


# ============================================================
# CLASSIFY SWINGS
# ============================================================

def classify_swings(swings):

    classified = []

    previous_high = None
    previous_low = None

    for swing in swings:

        item = dict(swing)

        if swing["type"] == "SWING_HIGH":

            if previous_high is None:

                item["structure"] = (
                    "INITIAL_HIGH"
                )

            else:

                change = percentage_change(
                    previous_high["price"],
                    swing["price"]
                )

                if change > MIN_STRUCTURE_MOVE:

                    item["structure"] = "HH"

                elif change < -MIN_STRUCTURE_MOVE:

                    item["structure"] = "LH"

                else:

                    item["structure"] = (
                        "EQUAL_HIGH"
                    )

            previous_high = item

        else:

            if previous_low is None:

                item["structure"] = (
                    "INITIAL_LOW"
                )

            else:

                change = percentage_change(
                    previous_low["price"],
                    swing["price"]
                )

                if change > MIN_STRUCTURE_MOVE:

                    item["structure"] = "HL"

                elif change < -MIN_STRUCTURE_MOVE:

                    item["structure"] = "LL"

                else:

                    item["structure"] = (
                        "EQUAL_LOW"
                    )

            previous_low = item

        classified.append(item)

    return classified


classified_swings = classify_swings(
    cleaned_swings
)


# ============================================================
# SWING REPORT
# ============================================================

print()
print("=" * 80)
print("MARKET STRUCTURE SWINGS")
print("=" * 80)

print(
    "Swing highs:",
    sum(
        1
        for swing in classified_swings
        if swing["type"] == "SWING_HIGH"
    )
)

print(
    "Swing lows:",
    sum(
        1
        for swing in classified_swings
        if swing["type"] == "SWING_LOW"
    )
)

print(
    "Cleaned swings:",
    len(classified_swings)
)

print()
print("Recent swings:")

for swing in classified_swings[
    -MAX_SWINGS_TO_PRINT:
]:

    print(

        f"Candidate={swing['index']:>6} | "
        f"Confirmed={swing['confirmation_index']:>6} | "
        f"{swing['type']:<11} | "
        f"{swing['structure']:<12} | "
        f"Price={swing['price']:.5f} | "
        f"Time={swing['timestamp']}"
    )


# ============================================================
# CHRONOLOGICAL SPLIT
# ============================================================

total_candles = len(
    normalized_candles
)

train_end = int(
    total_candles
    * TRAIN_RATIO
)

if train_end <= 0:

    raise ValueError(
        "Training period is empty."
    )

if train_end >= total_candles:

    raise ValueError(
        "Out-of-sample period is empty."
    )


oos_start = train_end


print()
print("=" * 80)
print("CHRONOLOGICAL DATA SPLIT")
print("=" * 80)

print(
    f"Total candles       : {total_candles}"
)

print(
    f"Training candles    : {train_end}"
)

print(
    f"OOS candles         : "
    f"{total_candles - oos_start}"
)

print(
    f"Training ratio      : "
    f"{TRAIN_RATIO:.2%}"
)

print(
    f"OOS ratio           : "
    f"{1.0 - TRAIN_RATIO:.2%}"
)

print(
    f"Training last index : "
    f"{train_end - 1}"
)

print(
    f"OOS first index     : "
    f"{oos_start}"
)


# ============================================================
# BUILD CHRONOLOGICAL STRUCTURE EVENTS
# ============================================================

def detect_structure_events_chronological(
    candles,
    swings
):

    """
    Structure-event detector that respects confirmation timing.

    A swing candidate at index X becomes known at:

        X + SWING_LOOKBACK

    Only after that confirmation index can the swing be used
    for BOS / CHoCH detection.
    """

    events = []

    confirmed_swings_by_index = {}

    for swing in swings:

        confirmed_swings_by_index.setdefault(
            swing["confirmation_index"],
            []
        ).append(swing)

    last_swing_high = None
    last_swing_low = None

    current_bias = "UNKNOWN"

    broken_high_indices = set()
    broken_low_indices = set()

    for index, candle in enumerate(candles):

        # ----------------------------------------------------
        # Register only swings that are confirmed NOW.
        # ----------------------------------------------------

        for swing in confirmed_swings_by_index.get(
            index,
            []
        ):

            if swing["type"] == "SWING_HIGH":

                last_swing_high = swing

            elif swing["type"] == "SWING_LOW":

                last_swing_low = swing

        close = candle["close"]

        # ----------------------------------------------------
        # Bullish structural break
        # ----------------------------------------------------

        bullish_break = (

            last_swing_high is not None

            and index > last_swing_high[
                "confirmation_index"
            ]

            and close > last_swing_high["price"]

            and last_swing_high["index"]
            not in broken_high_indices
        )

        # ----------------------------------------------------
        # Bearish structural break
        # ----------------------------------------------------

        bearish_break = (

            last_swing_low is not None

            and index > last_swing_low[
                "confirmation_index"
            ]

            and close < last_swing_low["price"]

            and last_swing_low["index"]
            not in broken_low_indices
        )

        # ----------------------------------------------------
        # If both occur on same candle.
        # ----------------------------------------------------

        if bullish_break and bearish_break:

            bullish_distance = (
                close
                - last_swing_high["price"]
            )

            bearish_distance = (
                last_swing_low["price"]
                - close
            )

            if bullish_distance >= bearish_distance:

                bearish_break = False

            else:

                bullish_break = False

        # ----------------------------------------------------
        # Bullish event
        # ----------------------------------------------------

        if bullish_break:

            if current_bias == "BEARISH":

                event_type = (
                    "CHoCH_BULLISH"
                )

            else:

                event_type = (
                    "BOS_BULLISH"
                )

            event = {

                "index":
                    index,

                "timestamp":
                    candle["timestamp"],

                "type":
                    event_type,

                "price":
                    close,

                "broken_level":
                    last_swing_high["price"],

                "broken_swing_index":
                    last_swing_high["index"],

                "broken_swing_confirmation_index":
                    last_swing_high[
                        "confirmation_index"
                    ],

                "direction":
                    "BULLISH",
            }

            events.append(
                event
            )

            current_bias = "BULLISH"

            broken_high_indices.add(
                last_swing_high["index"]
            )

            last_swing_high = None

        # ----------------------------------------------------
        # Bearish event
        # ----------------------------------------------------

        elif bearish_break:

            if current_bias == "BULLISH":

                event_type = (
                    "CHoCH_BEARISH"
                )

            else:

                event_type = (
                    "BOS_BEARISH"
                )

            event = {

                "index":
                    index,

                "timestamp":
                    candle["timestamp"],

                "type":
                    event_type,

                "price":
                    close,

                "broken_level":
                    last_swing_low["price"],

                "broken_swing_index":
                    last_swing_low["index"],

                "broken_swing_confirmation_index":
                    last_swing_low[
                        "confirmation_index"
                    ],

                "direction":
                    "BEARISH",
            }

            events.append(
                event
            )

            current_bias = "BEARISH"

            broken_low_indices.add(
                last_swing_low["index"]
            )

            last_swing_low = None

    return events


structure_events = detect_structure_events_chronological(
    normalized_candles,
    classified_swings
)


# ============================================================
# EVENT COUNTS
# ============================================================

event_counts = Counter(
    event["type"]
    for event in structure_events
)


print()
print("=" * 80)
print("STRUCTURE EVENTS")
print("=" * 80)

for event_name in [

    "BOS_BULLISH",
    "BOS_BEARISH",
    "CHoCH_BULLISH",
    "CHoCH_BEARISH",

]:

    print(
        f"{event_name:<20}:",
        event_counts.get(
            event_name,
            0
        )
    )


# ============================================================
# RECENT EVENTS
# ============================================================

print()
print("=" * 80)
print("RECENT STRUCTURE EVENTS")
print("=" * 80)

if not structure_events:

    print(
        "No BOS / CHoCH events detected."
    )

else:

    for event in structure_events[
        -MAX_EVENTS_TO_PRINT:
    ]:

        print(

            f"Index={event['index']:>6} | "
            f"{event['type']:<16} | "
            f"Close={event['price']:.5f} | "
            f"Broken={event['broken_level']:.5f} | "
            f"Swing={event['broken_swing_index']:>6} | "
            f"Confirmed={event['broken_swing_confirmation_index']:>6} | "
            f"Time={event['timestamp']}"
        )


# ============================================================
# LOOK-AHEAD SAFETY CHECK
# ============================================================

def validate_event_information_timing(
    events,
    swings
):

    errors = []

    swing_by_index = {
        swing["index"]: swing
        for swing in swings
    }

    for event in events:

        swing_index = event[
            "broken_swing_index"
        ]

        swing = swing_by_index.get(
            swing_index
        )

        if swing is None:

            errors.append(
                (
                    "Missing swing for event "
                    f"{event['index']}"
                )
            )

            continue

        if event["index"] <= swing[
            "confirmation_index"
        ]:

            errors.append(

                (
                    "LOOK-AHEAD ERROR: event "
                    f"{event['index']} used swing "
                    f"{swing_index} before confirmation "
                    f"{swing['confirmation_index']}"
                )
            )

    return errors


lookahead_errors = validate_event_information_timing(
    structure_events,
    classified_swings
)


print()
print("=" * 80)
print("LOOK-AHEAD-BIAS CHECK")
print("=" * 80)

if not lookahead_errors:

    print(
        "PASS: No structure-event confirmation timing violations."
    )

else:

    print(
        "FAIL: Look-ahead timing violations detected."
    )

    for error in lookahead_errors[:20]:

        print(
            error
        )

    raise RuntimeError(
        "Look-ahead-bias check failed."
    )


# ============================================================
# FUTURE OUTCOME RECORD GENERATION
# ============================================================

def generate_outcome_record(
    signal_index,
    signal_type,
    signal_direction,
    signal_price,
    source
):

    record = {

        "signal_index":
            signal_index,

        "signal_type":
            signal_type,

        "signal_direction":
            signal_direction,

        "signal_price":
            signal_price,

        "source":
            source,

        "outcomes":
            {},
    }

    for horizon in HORIZONS:

        future_index = (
            signal_index
            + horizon
        )

        if future_index >= len(
            normalized_candles
        ):

            record["outcomes"][
                str(horizon)
            ] = {

                "available":
                    False,

                "future_index":
                    future_index,

                "future_price":
                    None,

                "return":
                    None,

                "label":
                    None,
            }

            continue

        future_price = normalized_candles[
            future_index
        ]["close"]

        future_return = percentage_change(
            signal_price,
            future_price
        )

        label = classify_future_outcome(
            signal_price,
            future_price
        )

        record["outcomes"][
            str(horizon)
        ] = {

            "available":
                True,

            "future_index":
                future_index,

            "future_price":
                future_price,

            "return":
                future_return,

            "label":
                label,
        }

    return record


# ============================================================
# STRUCTURE SIGNAL DEFINITIONS
# ============================================================

SIGNAL_DEFINITIONS = [

    {
        "name":
            "HH",

        "structures":
            {"HH"},

        "direction":
            "BULLISH",
    },

    {
        "name":
            "HL",

        "structures":
            {"HL"},

        "direction":
            "BULLISH",
    },

    {
        "name":
            "LH",

        "structures":
            {"LH"},

        "direction":
            "BEARISH",
    },

    {
        "name":
            "LL",

        "structures":
            {"LL"},

        "direction":
            "BEARISH",
    },
]


# ============================================================
# BUILD SWING SIGNALS
# ============================================================

swing_signal_records = []


for swing in classified_swings:

    structure = swing[
        "structure"
    ]

    if structure not in {
        "HH",
        "HL",
        "LH",
        "LL",
    }:

        continue

    # --------------------------------------------------------
    # IMPORTANT:
    #
    # The signal becomes available at the confirmation index,
    # not the candidate index.
    # --------------------------------------------------------

    signal_index = swing[
        "confirmation_index"
    ]

    if signal_index >= len(
        normalized_candles
    ):

        continue

    signal_price = normalized_candles[
        signal_index
    ]["close"]

    direction = (
        "BULLISH"
        if structure in {
            "HH",
            "HL",
        }
        else
        "BEARISH"
    )

    record = generate_outcome_record(

        signal_index,

        structure,

        direction,

        signal_price,

        "SWING_STRUCTURE"
    )

    record[
        "candidate_index"
    ] = swing["index"]

    record[
        "confirmation_index"
    ] = swing[
        "confirmation_index"
    ]

    record[
        "structure"
    ] = structure

    swing_signal_records.append(
        record
    )


# ============================================================
# BUILD BOS / CHoCH SIGNALS
# ============================================================

event_signal_records = []


for event in structure_events:

    signal_index = event[
        "index"
    ]

    signal_price = event[
        "price"
    ]

    record = generate_outcome_record(

        signal_index,

        event["type"],

        event["direction"],

        signal_price,

        "STRUCTURE_EVENT"
    )

    record[
        "broken_swing_index"
    ] = event[
        "broken_swing_index"
    ]

    record[
        "broken_swing_confirmation_index"
    ] = event[
        "broken_swing_confirmation_index"
    ]

    event_signal_records.append(
        record
    )


# ============================================================
# FILTER SIGNALS FOR TRAINING / OOS
# ============================================================

def split_signal_records(
    records,
    split_index
):

    training = []
    oos = []

    for record in records:

        if record[
            "signal_index"
        ] < split_index:

            training.append(
                record
            )

        elif record[
            "signal_index"
        ] >= split_index:

            oos.append(
                record
            )

    return training, oos


swing_train, swing_oos = split_signal_records(
    swing_signal_records,
    oos_start
)

event_train, event_oos = split_signal_records(
    event_signal_records,
    oos_start
)


# ============================================================
# OUTCOME METRICS
# ============================================================

def calculate_metrics(
    records,
    horizon,
    expected_direction=None
):

    available = []

    for record in records:

        outcome = record[
            "outcomes"
        ].get(
            str(horizon)
        )

        if outcome is None:

            continue

        if not outcome[
            "available"
        ]:

            continue

        if expected_direction is not None:

            if (
                record[
                    "signal_direction"
                ]
                != expected_direction
            ):

                continue

        available.append(
            (
                record,
                outcome
            )
        )

    total = len(
        available
    )

    if total == 0:

        return {

            "signals":
                0,

            "bullish_signals":
                0,

            "bearish_signals":
                0,

            "buy_outcomes":
                0,

            "sell_outcomes":
                0,

            "neutral_outcomes":
                0,

            "coverage":
                0.0,

            "accuracy":
                0.0,

            "precision":
                0.0,

            "recall":
                0.0,

            "directional_accuracy":
                0.0,

            "average_return":
                0.0,
        }

    bullish_signals = 0
    bearish_signals = 0

    buy_outcomes = 0
    sell_outcomes = 0
    neutral_outcomes = 0

    correct = 0

    true_positive = 0
    false_positive = 0
    false_negative = 0

    returns = []

    for record, outcome in available:

        signal_direction = record[
            "signal_direction"
        ]

        label = outcome[
            "label"
        ]

        future_return = outcome[
            "return"
        ]

        returns.append(
            future_return
        )

        if signal_direction == "BULLISH":

            bullish_signals += 1

            if label == "BUY":

                buy_outcomes += 1
                correct += 1
                true_positive += 1

            elif label == "SELL":

                sell_outcomes += 1
                false_positive += 1

            else:

                neutral_outcomes += 1

                false_positive += 1

        elif signal_direction == "BEARISH":

            bearish_signals += 1

            if label == "SELL":

                sell_outcomes += 1
                correct += 1
                true_positive += 1

            elif label == "BUY":

                buy_outcomes += 1
                false_positive += 1

            else:

                neutral_outcomes += 1

                false_positive += 1

        # ----------------------------------------------------
        # Recall definition:
        #
        # Correct directional outcomes divided by all
        # directional outcomes matching the predicted class
        # opportunity.
        #
        # For this binary directional test, we treat the
        # opposite direction as a false negative as well.
        # ----------------------------------------------------

    accuracy = (
        correct / total
        if total
        else 0.0
    )

    precision_denominator = (
        true_positive
        + false_positive
    )

    precision = (

        true_positive
        / precision_denominator

        if precision_denominator
        else 0.0
    )

    # Since this is a directional signal evaluation,
    # recall is computed against the total number of
    # directional future outcomes.

    directional_outcomes = (
        buy_outcomes
        + sell_outcomes
    )

    recall = (

        true_positive
        / directional_outcomes

        if directional_outcomes
        else 0.0
    )

    directional_accuracy = (

        (
            buy_outcomes
            + sell_outcomes
        )
        / total

        if total
        else 0.0
    )

    return {

        "signals":
            total,

        "bullish_signals":
            bullish_signals,

        "bearish_signals":
            bearish_signals,

        "buy_outcomes":
            buy_outcomes,

        "sell_outcomes":
            sell_outcomes,

        "neutral_outcomes":
            neutral_outcomes,

        "coverage":
            total,

        "accuracy":
            accuracy,

        "precision":
            precision,

        "recall":
            recall,

        "directional_accuracy":
            directional_accuracy,

        "average_return":
            mean(returns),
    }


# ============================================================
# MAJORITY BASELINE
# ============================================================

def get_training_majority_class(
    records,
    horizon
):

    counts = Counter()

    for record in records:

        outcome = record[
            "outcomes"
        ].get(
            str(horizon)
        )

        if outcome is None:
            continue

        if not outcome[
            "available"
        ]:
            continue

        label = outcome[
            "label"
        ]

        counts[label] += 1

    if not counts:

        return "NEUTRAL"

    return counts.most_common(1)[0][0]


def calculate_baseline_metrics(
    training_records,
    oos_records,
    horizon
):

    majority_class = get_training_majority_class(
        training_records,
        horizon
    )

    available = []

    for record in oos_records:

        outcome = record[
            "outcomes"
        ].get(
            str(horizon)
        )

        if outcome is None:
            continue

        if not outcome[
            "available"
        ]:
            continue

        available.append(
            outcome["label"]
        )

    total = len(
        available
    )

    if total == 0:

        return {

            "majority_class":
                majority_class,

            "signals":
                0,

            "accuracy":
                0.0,
        }

    correct = sum(

        1

        for actual in available

        if actual == majority_class
    )

    return {

        "majority_class":
            majority_class,

        "signals":
            total,

        "accuracy":
            correct / total,
    }


# ============================================================
# VALIDATION REPORT
# ============================================================

print()
print("=" * 80)
print("OUT-OF-SAMPLE VALIDATION")
print("=" * 80)

print(
    "Swing training signals:",
    len(swing_train)
)

print(
    "Swing OOS signals:",
    len(swing_oos)
)

print(
    "Event training signals:",
    len(event_train)
)

print(
    "Event OOS signals:",
    len(event_oos)
)


# ============================================================
# STRUCTURE TYPE METRICS
# ============================================================

structure_types = [
    "HH",
    "HL",
    "LH",
    "LL",
    "BOS_BULLISH",
    "BOS_BEARISH",
    "CHoCH_BULLISH",
    "CHoCH_BEARISH",
]


def filter_by_signal_type(
    records,
    signal_type
):

    return [

        record

        for record in records

        if record[
            "signal_type"
        ] == signal_type
    ]


validation_results = {}


for signal_type in structure_types:

    train_records = (

        filter_by_signal_type(
            swing_train,
            signal_type
        )

        +

        filter_by_signal_type(
            event_train,
            signal_type
        )
    )

    oos_records = (

        filter_by_signal_type(
            swing_oos,
            signal_type
        )

        +

        filter_by_signal_type(
            event_oos,
            signal_type
        )
    )

    validation_results[
        signal_type
    ] = {}

    for horizon in HORIZONS:

        metrics = calculate_metrics(
            oos_records,
            horizon
        )

        baseline = calculate_baseline_metrics(
            train_records,
            oos_records,
            horizon
        )

        validation_results[
            signal_type
        ][
            str(horizon)
        ] = {

            "metrics":
                metrics,

            "baseline":
                baseline,
        }


# ============================================================
# PRINT STRUCTURE RESULTS
# ============================================================

print()
print("=" * 80)
print("STRUCTURE TYPE OOS RESULTS")
print("=" * 80)

for signal_type in structure_types:

    print()
    print(
        "-" * 80
    )

    print(
        signal_type
    )

    for horizon in HORIZONS:

        result = validation_results[
            signal_type
        ][
            str(horizon)
        ]

        metrics = result[
            "metrics"
        ]

        baseline = result[
            "baseline"
        ]

        print(

            f"H+{horizon:<2} | "
            f"Signals={metrics['signals']:<5} | "
            f"Accuracy={metrics['accuracy']:.2%} | "
            f"Precision={metrics['precision']:.2%} | "
            f"Recall={metrics['recall']:.2%} | "
            f"AvgReturn={metrics['average_return']:+.4%} | "
            f"Baseline={baseline['accuracy']:.2%}"
        )


# ============================================================
# DIRECTIONAL GROUP RESULTS
# ============================================================

def combine_records(
    records,
    allowed_types
):

    return [

        record

        for record in records

        if record[
            "signal_type"
        ] in allowed_types
    ]


directional_groups = {

    "BULLISH_STRUCTURE":
        [
            "HH",
            "HL",
            "BOS_BULLISH",
            "CHoCH_BULLISH",
        ],

    "BEARISH_STRUCTURE":
        [
            "LH",
            "LL",
            "BOS_BEARISH",
            "CHoCH_BEARISH",
        ],

    "BOS":
        [
            "BOS_BULLISH",
            "BOS_BEARISH",
        ],

    "CHoCH":
        [
            "CHoCH_BULLISH",
            "CHoCH_BEARISH",
        ],

    "SWING_STRUCTURE":
        [
            "HH",
            "HL",
            "LH",
            "LL",
        ],

    "ALL_STRUCTURE_EVENTS":
        [
            "HH",
            "HL",
            "LH",
            "LL",
            "BOS_BULLISH",
            "BOS_BEARISH",
            "CHoCH_BULLISH",
            "CHoCH_BEARISH",
        ],
}


group_results = {}


for group_name, allowed_types in directional_groups.items():

    train_records = combine_records(
        swing_train + event_train,
        allowed_types
    )

    oos_records = combine_records(
        swing_oos + event_oos,
        allowed_types
    )

    group_results[
        group_name
    ] = {}

    for horizon in HORIZONS:

        metrics = calculate_metrics(
            oos_records,
            horizon
        )

        baseline = calculate_baseline_metrics(
            train_records,
            oos_records,
            horizon
        )

        group_results[
            group_name
        ][
            str(horizon)
        ] = {

            "metrics":
                metrics,

            "baseline":
                baseline,
        }


# ============================================================
# PRINT GROUP RESULTS
# ============================================================

print()
print("=" * 80)
print("GROUPED OUT-OF-SAMPLE RESULTS")
print("=" * 80)

for group_name in directional_groups:

    print()
    print(
        group_name
    )

    for horizon in HORIZONS:

        result = group_results[
            group_name
        ][
            str(horizon)
        ]

        metrics = result[
            "metrics"
        ]

        baseline = result[
            "baseline"
        ]

        edge = (
            metrics["accuracy"]
            - baseline["accuracy"]
        )

        print(

            f"H+{horizon:<2} | "
            f"N={metrics['signals']:<5} | "
            f"Accuracy={metrics['accuracy']:.2%} | "
            f"Precision={metrics['precision']:.2%} | "
            f"Recall={metrics['recall']:.2%} | "
            f"Coverage={metrics['coverage']:<5} | "
            f"AvgReturn={metrics['average_return']:+.4%} | "
            f"Baseline={baseline['accuracy']:.2%} | "
            f"Edge={edge:+.2%}"
        )


# ============================================================
# SIGNAL SAMPLE
# ============================================================

print()
print("=" * 80)
print("SAMPLE OOS VALIDATION SIGNALS")
print("=" * 80)

all_oos_records = (
    swing_oos
    + event_oos
)

all_oos_records.sort(
    key=lambda record:
        record["signal_index"]
)


if not all_oos_records:

    print(
        "No OOS signals available."
    )

else:

    for record in all_oos_records[
        :MAX_VALIDATION_SIGNALS_TO_PRINT
    ]:

        h4 = record[
            "outcomes"
        ].get("4")

        h8 = record[
            "outcomes"
        ].get("8")

        h16 = record[
            "outcomes"
        ].get("16")

        print(

            f"Index={record['signal_index']:>6} | "
            f"{record['signal_type']:<16} | "
            f"Direction={record['signal_direction']:<8} | "
            f"Price={record['signal_price']:.5f} | "
            f"H4={h4['label'] if h4 and h4['available'] else 'N/A':<7} | "
            f"H8={h8['label'] if h8 and h8['available'] else 'N/A':<7} | "
            f"H16={h16['label'] if h16 and h16['available'] else 'N/A':<7}"
        )


# ============================================================
# COVERAGE ANALYSIS
# ============================================================

print()
print("=" * 80)
print("OOS COVERAGE")
print("=" * 80)

oos_candles = (
    total_candles
    - oos_start
)


print(
    "OOS candles:",
    oos_candles
)

print(
    "Total OOS signals:",
    len(all_oos_records)
)

if oos_candles > 0:

    signal_coverage = (
        len(all_oos_records)
        / oos_candles
    )

else:

    signal_coverage = 0.0


print(
    f"Signal frequency per OOS candle: "
    f"{signal_coverage:.4f}"
)


# ============================================================
# TRAINING CLASS DISTRIBUTION
# ============================================================

print()
print("=" * 80)
print("TRAINING OUTCOME DISTRIBUTION")
print("=" * 80)

for horizon in HORIZONS:

    labels = []

    for record in (
        swing_train
        + event_train
    ):

        outcome = record[
            "outcomes"
        ].get(
            str(horizon)
        )

        if outcome is None:
            continue

        if not outcome[
            "available"
        ]:
            continue

        labels.append(
            outcome["label"]
        )

    counts = Counter(
        labels
    )

    print()
    print(
        f"H+{horizon}"
    )

    print(
        "BUY     :",
        counts.get(
            "BUY",
            0
        )
    )

    print(
        "SELL    :",
        counts.get(
            "SELL",
            0
        )
    )

    print(
        "NEUTRAL :",
        counts.get(
            "NEUTRAL",
            0
        )
    )


# ============================================================
# OOS OUTCOME DISTRIBUTION
# ============================================================

print()
print("=" * 80)
print("OOS OUTCOME DISTRIBUTION")
print("=" * 80)

for horizon in HORIZONS:

    labels = []

    for record in all_oos_records:

        outcome = record[
            "outcomes"
        ].get(
            str(horizon)
        )

        if outcome is None:
            continue

        if not outcome[
            "available"
        ]:
            continue

        labels.append(
            outcome["label"]
        )

    counts = Counter(
        labels
    )

    print()
    print(
        f"H+{horizon}"
    )

    print(
        "BUY     :",
        counts.get(
            "BUY",
            0
        )
    )

    print(
        "SELL    :",
        counts.get(
            "SELL",
            0
        )
    )

    print(
        "NEUTRAL :",
        counts.get(
            "NEUTRAL",
            0
        )
    )


# ============================================================
# OOS CHRONOLOGICAL INTEGRITY
# ============================================================

print()
print("=" * 80)
print("OOS CHRONOLOGICAL INTEGRITY")
print("=" * 80)

chronological_signal_order = all(

    all_oos_records[i][
        "signal_index"
    ]

    <=

    all_oos_records[i + 1][
        "signal_index"
    ]

    for i in range(
        len(all_oos_records) - 1
    )
)


if chronological_signal_order:

    print(
        "Signal order: PASS"
    )

else:

    print(
        "Signal order: FAIL"
    )

    raise RuntimeError(
        "OOS signals are not chronologically ordered."
    )


# ============================================================
# FUTURE OUTCOME LEAKAGE CHECK
# ============================================================

def check_future_outcome_separation(
    records
):

    errors = []

    for record in records:

        signal_index = record[
            "signal_index"
        ]

        for horizon in HORIZONS:

            outcome = record[
                "outcomes"
            ].get(
                str(horizon)
            )

            if outcome is None:
                continue

            if not outcome[
                "available"
            ]:
                continue

            future_index = outcome[
                "future_index"
            ]

            if future_index <= signal_index:

                errors.append(

                    (
                        "Future outcome index "
                        f"{future_index} is not after "
                        f"signal index {signal_index}"
                    )
                )

    return errors


future_leakage_errors = check_future_outcome_separation(
    all_oos_records
)


print()
print("=" * 80)
print("FUTURE OUTCOME SEPARATION CHECK")
print("=" * 80)

if not future_leakage_errors:

    print(
        "PASS: All future outcomes occur after signals."
    )

else:

    print(
        "FAIL: Future outcome leakage detected."
    )

    for error in future_leakage_errors[:20]:

        print(
            error
        )

    raise RuntimeError(
        "Future outcome leakage detected."
    )


# ============================================================
# STRUCTURE SUMMARY
# ============================================================

structure_counter = Counter(
    swing["structure"]
    for swing in classified_swings
)


print()
print("=" * 80)
print("STRUCTURE SUMMARY")
print("=" * 80)

for structure in [

    "HH",
    "HL",
    "LH",
    "LL",
    "EQUAL_HIGH",
    "EQUAL_LOW",

]:

    print(

        f"{structure:<12}:",
        structure_counter.get(
            structure,
            0
        )
    )


# ============================================================
# SAVE RESULT OBJECT
# ============================================================

result_object = {

    "experiment":
        "MLAI v3.7 Chronological Out-of-Sample Market Structure Validation",

    "version":
        "3.7",

    "market_file":
        MARKET_FILE,

    "market_file_modified":
        False,

    "production_modified":
        False,

    "learning_memory_modified":
        False,

    "trading_enabled":
        False,

    "configuration": {

        "swing_lookback":
            SWING_LOOKBACK,

        "train_ratio":
            TRAIN_RATIO,

        "outcome_threshold":
            OUTCOME_THRESHOLD,

        "horizons":
            HORIZONS,

        "min_structure_move":
            MIN_STRUCTURE_MOVE,
    },

    "dataset": {

        "raw_candles":
            len(candles),

        "valid_candles":
            len(normalized_candles),

        "invalid_candles":
            invalid_candle_count,

        "training_candles":
            train_end,

        "oos_candles":
            total_candles - oos_start,
    },

    "lookahead_check": {

        "errors":
            len(lookahead_errors),

        "passed":
            not lookahead_errors,
    },

    "future_separation_check": {

        "errors":
            len(future_leakage_errors),

        "passed":
            not future_leakage_errors,
    },

    "structure_event_counts":
        dict(event_counts),

    "structure_counts":
        dict(structure_counter),

    "group_results":
        group_results,

    "validation_results":
        validation_results,

    "oos_signal_count":
        len(all_oos_records),

    "timestamp_check":
        timestamp_check,

    "protection": {

        "market_data_read_only":
            True,

        "production_not_modified":
            True,

        "learning_memory_not_modified":
            True,

        "trading_disabled":
            True,
    },
}


# ============================================================
# WRITE SEPARATE BINARY VALIDATION RESULT
# ============================================================

with open(
    OUTPUT_BIN,
    "wb"
) as f:

    pickle.dump(
        result_object,
        f
    )


# ============================================================
# REPORT GENERATION
# ============================================================

def format_percent(value):

    return f"{value:.2%}"


def format_return(value):

    return f"{value:+.4%}"


report_lines = []


report_lines.append(
    "# MLAI v3.7 Chronological Out-of-Sample Market Structure Validation"
)

report_lines.append("")

report_lines.append(
    "## Experiment Status"
)

report_lines.append("")

report_lines.append(
    "- market_data.bin: READ ONLY"
)

report_lines.append(
    "- Production MLAI: NOT MODIFIED"
)

report_lines.append(
    "- Learning memory: NOT MODIFIED"
)

report_lines.append(
    "- Trading: DISABLED"
)

report_lines.append(
    "- Production model training: DISABLED"
)

report_lines.append("")

report_lines.append(
    "## Dataset"
)

report_lines.append("")

report_lines.append(
    f"- Raw candles: {len(candles)}"
)

report_lines.append(
    f"- Valid candles: {len(normalized_candles)}"
)

report_lines.append(
    f"- Invalid candles: {invalid_candle_count}"
)

report_lines.append(
    f"- Training candles: {train_end}"
)

report_lines.append(
    f"- OOS candles: {total_candles - oos_start}"
)

report_lines.append(
    f"- Training ratio: {TRAIN_RATIO:.2%}"
)

report_lines.append(
    f"- OOS ratio: {1.0 - TRAIN_RATIO:.2%}"
)

report_lines.append("")

report_lines.append(
    "## Configuration"
)

report_lines.append("")

report_lines.append(
    f"- Swing lookback: {SWING_LOOKBACK}"
)

report_lines.append(
    f"- Minimum structure move: {MIN_STRUCTURE_MOVE:.4%}"
)

report_lines.append(
    f"- Outcome threshold: {OUTCOME_THRESHOLD:.4%}"
)

report_lines.append(
    f"- Horizons: {HORIZONS}"
)

report_lines.append("")

report_lines.append(
    "## Look-Ahead-Bias Checks"
)

report_lines.append("")

report_lines.append(
    f"- Structure confirmation timing: "
    f"{'PASS' if not lookahead_errors else 'FAIL'}"
)

report_lines.append(
    f"- Future outcome separation: "
    f"{'PASS' if not future_leakage_errors else 'FAIL'}"
)

report_lines.append(
    f"- Chronological OOS signal order: "
    f"{'PASS' if chronological_signal_order else 'FAIL'}"
)

report_lines.append("")

report_lines.append(
    "## Structure Event Counts"
)

report_lines.append("")

for name in [

    "BOS_BULLISH",
    "BOS_BEARISH",
    "CHoCH_BULLISH",
    "CHoCH_BEARISH",

]:

    report_lines.append(

        f"- {name}: "
        f"{event_counts.get(name, 0)}"
    )

report_lines.append("")

report_lines.append(
    "## Grouped OOS Results"
)

report_lines.append("")

report_lines.append(

    "| Group | Horizon | Signals | Accuracy | Precision | Recall | Avg Return | Baseline | Edge |"
)

report_lines.append(

    "|---|---:|---:|---:|---:|---:|---:|---:|---:|"
)


for group_name in directional_groups:

    for horizon in HORIZONS:

        result = group_results[
            group_name
        ][
            str(horizon)
        ]

        metrics = result[
            "metrics"
        ]

        baseline = result[
            "baseline"
        ]

        edge = (
            metrics["accuracy"]
            - baseline["accuracy"]
        )

        report_lines.append(

            "| "
            f"{group_name} | "
            f"H+{horizon} | "
            f"{metrics['signals']} | "
            f"{format_percent(metrics['accuracy'])} | "
            f"{format_percent(metrics['precision'])} | "
            f"{format_percent(metrics['recall'])} | "
            f"{format_return(metrics['average_return'])} | "
            f"{format_percent(baseline['accuracy'])} | "
            f"{edge:+.2%} |"
        )


report_lines.append("")

report_lines.append(
    "## Interpretation"
)

report_lines.append("")

report_lines.append(
    "This experiment measures historical association between "
    "confirmed market structure and subsequent price outcomes."
)

report_lines.append("")

report_lines.append(
    "A result above the baseline does NOT automatically mean "
    "the structure is profitable or suitable for live trading."
)

report_lines.append("")

report_lines.append(
    "The experiment does not include transaction costs, spread, "
    "slippage, execution latency, position sizing, stop-loss "
    "logic, take-profit logic, or portfolio effects."
)

report_lines.append("")

report_lines.append(
    "Swing candidates are retrospective. A swing becomes "
    "available only after SWING_LOOKBACK confirmation candles."
)

report_lines.append("")

report_lines.append(
    "The final 30% of the chronological dataset is treated as "
    "out-of-sample validation data."
)

report_lines.append("")

report_lines.append(
    "OOS results should be considered evidence for further "
    "research, not proof of predictive power."
)

report_lines.append("")

report_lines.append(
    "## Required Next Validation Steps"
)

report_lines.append("")

for item in [

    "Repeat validation on multiple chronological windows.",

    "Perform walk-forward validation.",

    "Test different instruments and market regimes.",

    "Test different volatility environments.",

    "Compare against stronger baselines.",

    "Evaluate statistical significance.",

    "Test transaction costs and spread.",

    "Test signal clustering and dependency.",

    "Test whether apparent edge survives parameter changes.",

    "Perform strict live/paper forward testing before any "
    "production integration.",

]:

    report_lines.append(
        f"- {item}"
    )


report_lines.append("")

report_lines.append(
    "## Final Protection"
)

report_lines.append("")

report_lines.append(
    "- market_data.bin: READ ONLY"
)

report_lines.append(
    "- Production MLAI: NOT MODIFIED"
)

report_lines.append(
    "- Learning memory: NOT MODIFIED"
)

report_lines.append(
    "- Trading: DISABLED"
)


with open(
    OUTPUT_REPORT,
    "w",
    encoding="utf-8"
) as f:

    f.write(
        "\n".join(
            report_lines
        )
    )


# ============================================================
# FINAL PROTECTION CHECK
# ============================================================

print()
print("=" * 80)
print("FINAL PROTECTION CHECK")
print("=" * 80)

print(
    "market_data.bin : READ ONLY"
)

print(
    "Production MLAI : NOT MODIFIED"
)

print(
    "Learning memory  : NOT MODIFIED"
)

print(
    "Trading          : DISABLED"
)

print(
    "Model training   : DISABLED"
)

print()
print(
    "Validation binary:"
)

print(
    f"    {OUTPUT_BIN}"
)

print(
    "Validation report:"
)

print(
    f"    {OUTPUT_REPORT}"
)

print()
print("=" * 80)
print(
    "MLAI v3.7 CHRONOLOGICAL OUT-OF-SAMPLE "
    "MARKET STRUCTURE VALIDATION COMPLETE"
)
print("=" * 80)