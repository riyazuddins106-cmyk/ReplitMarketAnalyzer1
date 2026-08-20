import os
import pickle
import math
from collections import Counter


# ============================================================
# MLAI v3.5.1
# MARKET STRUCTURE DIAGNOSTIC TEST
#
# FILE:
#     mlai_v35_market_structure_test.py
#
# PURPOSE
# ------------------------------------------------------------
# Diagnostic experiment for raw market structure.
#
# Reads:
#
#     market_data.bin
#
# Detects:
#
#     Swing Highs
#     Swing Lows
#
#     Higher High  (HH)
#     Higher Low   (HL)
#
#     Lower High   (LH)
#     Lower Low    (LL)
#
#     Break of Structure (BOS)
#     Change of Character (CHoCH)
#
#     Recent structural direction
#     Current structural position
#
# IMPORTANT
# ------------------------------------------------------------
# This program is READ ONLY.
#
# It does NOT:
#
#     - modify market_data.bin
#     - modify production MLAI
#     - modify learning memory
#     - train a production model
#     - place trades
#
# This is a diagnostic experiment only.
#
# IMPORTANT INTERPRETATION
# ------------------------------------------------------------
# HH/HL/LH/LL are descriptive structural labels.
#
# BOS/CHoCH are algorithmic classifications based on
# confirmed swing levels and candle CLOSE prices.
#
# "Confidence" in this program is NOT prediction accuracy.
# It is a structural quality metric only.
#
# No future price prediction is performed.
# ============================================================


# ============================================================
# CONFIGURATION
# ============================================================

MARKET_FILE = "market_data.bin"

# Number of candles on each side required to confirm a swing.
#
# Example:
#
#     3
#
# means a candle must be >= the highs of the previous
# 3 candles and the next 3 candles.
SWING_LOOKBACK = 3

# Minimum candles required.
MIN_CANDLES = 100

# Number of recent candles used for recent structure analysis.
RECENT_CANDLES = 100

# Number of swing records printed.
MAX_SWINGS_TO_PRINT = 30

# Number of events printed.
MAX_EVENTS_TO_PRINT = 30

# Minimum percentage movement required before classifying
# a structural point as HH/LH or HL/LL.
#
# 0.0002 = 0.02%
MIN_STRUCTURE_MOVE = 0.0002

# ATR period.
ATR_PERIOD = 14

# Minimum number of directional structural points required
# before classifying a recent trend.
MIN_DIRECTIONAL_POINTS = 2

# Score threshold for directional classification.
STRUCTURE_DIRECTION_THRESHOLD = 0.25


# ============================================================
# HEADER
# ============================================================

print("=" * 80)
print("MLAI v3.5.1 MARKET STRUCTURE TEST")
print("=" * 80)

print(
    """
PURPOSE
-------

This experiment investigates raw market structure.

The program reads market_data.bin and attempts to identify:

    Swing Highs
    Swing Lows

    Higher High  (HH)
    Higher Low   (HL)

    Lower High   (LH)
    Lower Low    (LL)

    Break of Structure (BOS)
    Change of Character (CHoCH)

    Bullish structure
    Bearish structure
    Range / transition

This is a diagnostic experiment only.

market_data.bin        = READ ONLY
Production MLAI        = NOT MODIFIED
Learning memory        = NOT MODIFIED
Trading                = NOT PERFORMED

IMPORTANT:

Structural confidence is NOT prediction confidence.
No future outcome is being predicted in this experiment.
"""
)

print("=" * 80)


# ============================================================
# PROTECTION CHECK
# ============================================================

print("PROTECTION CHECK")
print("=" * 80)

print("market_data.bin : READ ONLY")
print("production MLAI : NOT MODIFIED")
print("learning memory : NOT MODIFIED")
print("trading         : DISABLED")


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


print("Total candles:", len(candles))


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
    """
    Convert supported candle formats into one standard format.

    IMPORTANT:
    original_index is preserved so the program can distinguish
    the original market-data position from the normalized array
    position.
    """

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

    if (
        not math.isfinite(open_price)
        or not math.isfinite(high)
        or not math.isfinite(low)
        or not math.isfinite(close)
    ):
        return None

    # Validate OHLC relationship.
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
# BUILD NORMALIZED CANDLES
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
        "Not enough valid OHLC candles "
        "after normalization."
    )


print()
print(
    "Valid OHLC candles:",
    len(normalized_candles)
)

print(
    "Invalid candles skipped:",
    invalid_candle_count
)

print("PASS: market_data.bin loaded.")
print("PASS: OHLC data normalized.")
print("PASS: market_data.bin remains READ ONLY.")


# ============================================================
# BASIC PRICE ARRAYS
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
# NUMERIC HELPERS
# ============================================================

def mean(values):

    if not values:
        return 0.0

    return sum(values) / len(values)


def percentage_change(start, end):

    if start == 0:
        return 0.0

    return (end / start) - 1.0


def true_range(index):

    if index <= 0:

        return highs[index] - lows[index]

    previous_close = closes[index - 1]

    return max(
        highs[index] - lows[index],
        abs(highs[index] - previous_close),
        abs(lows[index] - previous_close),
    )


def calculate_atr(index, period=ATR_PERIOD):

    start = max(
        0,
        index - period + 1
    )

    values = [
        true_range(i)
        for i in range(
            start,
            index + 1
        )
    ]

    return mean(values)


# ============================================================
# SWING HIGH DETECTION
# ============================================================

def detect_swing_highs(lookback=SWING_LOOKBACK):

    swings = []

    start = lookback
    end = len(normalized_candles) - lookback

    for index in range(start, end):

        current_high = highs[index]

        left_highs = highs[
            index - lookback:index
        ]

        right_highs = highs[
            index + 1:index + lookback + 1
        ]

        left_max = max(left_highs)
        right_max = max(right_highs)

        # Strictly require the current candle to be at
        # least as high as both sides.
        #
        # Equal highs are allowed, but they are handled
        # later by swing cleaning.
        if (
            current_high >= left_max
            and current_high >= right_max
        ):

            swings.append({

                "type":
                    "SWING_HIGH",

                "index":
                    index,

                "original_index":
                    normalized_candles[index]["index"],

                "price":
                    current_high,

                "timestamp":
                    normalized_candles[index]["timestamp"],
            })

    return swings


# ============================================================
# SWING LOW DETECTION
# ============================================================

def detect_swing_lows(lookback=SWING_LOOKBACK):

    swings = []

    start = lookback
    end = len(normalized_candles) - lookback

    for index in range(start, end):

        current_low = lows[index]

        left_lows = lows[
            index - lookback:index
        ]

        right_lows = lows[
            index + 1:index + lookback + 1
        ]

        left_min = min(left_lows)
        right_min = min(right_lows)

        if (
            current_low <= left_min
            and current_low <= right_min
        ):

            swings.append({

                "type":
                    "SWING_LOW",

                "index":
                    index,

                "original_index":
                    normalized_candles[index]["index"],

                "price":
                    current_low,

                "timestamp":
                    normalized_candles[index]["timestamp"],
            })

    return swings


# ============================================================
# DETECT RAW SWINGS
# ============================================================

raw_swing_highs = detect_swing_highs()

raw_swing_lows = detect_swing_lows()


print()
print("=" * 80)
print("RAW SWING DETECTION")
print("=" * 80)

print(
    "Raw swing highs:",
    len(raw_swing_highs)
)

print(
    "Raw swing lows:",
    len(raw_swing_lows)
)


# ============================================================
# COMBINE SWINGS
# ============================================================

all_swings = (
    raw_swing_highs
    + raw_swing_lows
)

all_swings.sort(
    key=lambda x: (
        x["index"],
        x["type"]
    )
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

            cleaned.append(swing)
            continue

        previous = cleaned[-1]

        # Different swing types can coexist.
        if previous["type"] != swing["type"]:

            cleaned.append(swing)
            continue

        # Same type consecutively.
        #
        # For highs:
        # keep the higher high.
        #
        # For lows:
        # keep the lower low.

        if swing["type"] == "SWING_HIGH":

            if swing["price"] > previous["price"]:

                cleaned[-1] = swing

            elif swing["price"] == previous["price"]:

                # If exactly equal, keep the later confirmed
                # point because it has more confirmation bars.
                cleaned[-1] = swing

        else:

            if swing["price"] < previous["price"]:

                cleaned[-1] = swing

            elif swing["price"] == previous["price"]:

                cleaned[-1] = swing

    return cleaned


cleaned_swings = clean_swings(
    all_swings
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

                item["structure"] = "INITIAL_HIGH"

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

                    item["structure"] = "EQUAL_HIGH"

            previous_high = item

        else:

            if previous_low is None:

                item["structure"] = "INITIAL_LOW"

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

                    item["structure"] = "EQUAL_LOW"

            previous_low = item

        classified.append(item)

    return classified


classified_swings = classify_swings(
    cleaned_swings
)


# ============================================================
# SWING DETECTION REPORT
# ============================================================

print()
print("=" * 80)
print("SWING DETECTION")
print("=" * 80)

print(
    "Swing highs:",
    sum(
        1
        for x in classified_swings
        if x["type"] == "SWING_HIGH"
    )
)

print(
    "Swing lows:",
    sum(
        1
        for x in classified_swings
        if x["type"] == "SWING_LOW"
    )
)

print(
    "Total cleaned swings:",
    len(classified_swings)
)


# ============================================================
# PRINT MARKET STRUCTURE SWINGS
# ============================================================

print()
print("=" * 80)
print("MARKET STRUCTURE SWINGS")
print("=" * 80)

for swing in classified_swings[
    -MAX_SWINGS_TO_PRINT:
]:

    print(
        f"Index={swing['index']:>6} | "
        f"Original={swing['original_index']:>6} | "
        f"{swing['type']:<11} | "
        f"{swing['structure']:<12} | "
        f"Price={swing['price']:.5f} | "
        f"Time={swing['timestamp']}"
    )


# ============================================================
# STRUCTURE COUNTS
# ============================================================

structure_counts = Counter(
    swing["structure"]
    for swing in classified_swings
)


print()
print("=" * 80)
print("STRUCTURE COUNTS")
print("=" * 80)

for name in [
    "HH",
    "HL",
    "LH",
    "LL",
    "EQUAL_HIGH",
    "EQUAL_LOW",
]:

    print(
        f"{name:<12}:",
        structure_counts.get(name, 0)
    )


# ============================================================
# STRUCTURE SCORE
# ============================================================

def calculate_structure_score(swings):

    bullish_points = 0
    bearish_points = 0

    for swing in swings:

        structure = swing["structure"]

        if structure in (
            "HH",
            "HL"
        ):

            bullish_points += 1

        elif structure in (
            "LH",
            "LL"
        ):

            bearish_points += 1

    total = (
        bullish_points
        + bearish_points
    )

    if total == 0:

        return {
            "bullish": 0,
            "bearish": 0,
            "score": 0.0,
            "direction": "UNKNOWN",
        }

    score = (
        bullish_points
        - bearish_points
    ) / total

    if score >= STRUCTURE_DIRECTION_THRESHOLD:

        direction = "BULLISH"

    elif score <= -STRUCTURE_DIRECTION_THRESHOLD:

        direction = "BEARISH"

    else:

        direction = "RANGE / MIXED"

    return {
        "bullish": bullish_points,
        "bearish": bearish_points,
        "score": score,
        "direction": direction,
    }


structure_score = calculate_structure_score(
    classified_swings
)


print()
print("=" * 80)
print("MARKET STRUCTURE SCORE")
print("=" * 80)

print(
    "Bullish structural points:",
    structure_score["bullish"]
)

print(
    "Bearish structural points:",
    structure_score["bearish"]
)

print(
    f"Structure score: "
    f"{structure_score['score']:+.3f}"
)

print(
    "Structure direction:",
    structure_score["direction"]
)


# ============================================================
# CREATE SWING LOOKUP
# ============================================================

swings_by_index = {}

for swing in classified_swings:

    swings_by_index.setdefault(
        swing["index"],
        []
    ).append(swing)


# ============================================================
# BOS / CHoCH DETECTION
# ============================================================

def detect_structure_events(
    candles,
    swings
):

    events = []

    swings_by_index_local = {}

    for swing in swings:

        swings_by_index_local.setdefault(
            swing["index"],
            []
        ).append(swing)

    last_swing_high = None
    last_swing_low = None

    current_bias = "UNKNOWN"

    broken_high_indices = set()
    broken_low_indices = set()

    for index, candle in enumerate(candles):

        # ----------------------------------------------------
        # Register newly confirmed swings
        # ----------------------------------------------------

        for swing in swings_by_index_local.get(
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
            and index > last_swing_high["index"]
            and close > last_swing_high["price"]
            and last_swing_high["index"]
            not in broken_high_indices
        )

        # ----------------------------------------------------
        # Bearish structural break
        # ----------------------------------------------------

        bearish_break = (
            last_swing_low is not None
            and index > last_swing_low["index"]
            and close < last_swing_low["price"]
            and last_swing_low["index"]
            not in broken_low_indices
        )

        # ----------------------------------------------------
        # If both occur on the same candle
        # ----------------------------------------------------

        if bullish_break and bearish_break:

            # Large-range candle can break both sides.
            # Record the side corresponding to the larger
            # close displacement from each level.

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

                event_type = "CHoCH_BULLISH"

            else:

                event_type = "BOS_BULLISH"

            events.append({

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

                "direction":
                    "BULLISH",
            })

            current_bias = "BULLISH"

            broken_high_indices.add(
                last_swing_high["index"]
            )

            # The level has now been consumed.
            last_swing_high = None

        # ----------------------------------------------------
        # Bearish event
        # ----------------------------------------------------

        elif bearish_break:

            if current_bias == "BULLISH":

                event_type = "CHoCH_BEARISH"

            else:

                event_type = "BOS_BEARISH"

            events.append({

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

                "direction":
                    "BEARISH",
            })

            current_bias = "BEARISH"

            broken_low_indices.add(
                last_swing_low["index"]
            )

            last_swing_low = None

    return events


structure_events = detect_structure_events(
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

print(
    "Bullish BOS:",
    event_counts.get(
        "BOS_BULLISH",
        0
    )
)

print(
    "Bearish BOS:",
    event_counts.get(
        "BOS_BEARISH",
        0
    )
)

print(
    "Bullish CHoCH:",
    event_counts.get(
        "CHoCH_BULLISH",
        0
    )
)

print(
    "Bearish CHoCH:",
    event_counts.get(
        "CHoCH_BEARISH",
        0
    )
)


# ============================================================
# PRINT STRUCTURE EVENTS
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
            f"SwingIndex={event['broken_swing_index']:>6} | "
            f"Time={event['timestamp']}"
        )


# ============================================================
# RECENT STRUCTURE
# ============================================================

recent_start = max(
    0,
    len(normalized_candles)
    - RECENT_CANDLES
)


recent_swings = [

    swing

    for swing in classified_swings

    if swing["index"] >= recent_start
]


recent_events = [

    event

    for event in structure_events

    if event["index"] >= recent_start
]


recent_structure_score = calculate_structure_score(
    recent_swings
)


# ============================================================
# RECENT STRUCTURE REPORT
# ============================================================

print()
print("=" * 80)
print("RECENT MARKET STRUCTURE")
print("=" * 80)

print(
    "Recent candles:",
    len(normalized_candles)
    - recent_start
)

print(
    "Recent swings:",
    len(recent_swings)
)

print(
    "Recent structure events:",
    len(recent_events)
)

print(
    "Recent bullish points:",
    recent_structure_score["bullish"]
)

print(
    "Recent bearish points:",
    recent_structure_score["bearish"]
)

print(
    f"Recent structure score: "
    f"{recent_structure_score['score']:+.3f}"
)

print(
    "Recent structure direction:",
    recent_structure_score["direction"]
)


# ============================================================
# LAST STRUCTURAL LEVELS
# ============================================================

def get_last_structural_levels(swings):

    latest_high = None
    latest_low = None

    for swing in reversed(swings):

        if (
            latest_high is None
            and swing["type"] == "SWING_HIGH"
        ):

            latest_high = swing

        if (
            latest_low is None
            and swing["type"] == "SWING_LOW"
        ):

            latest_low = swing

        if (
            latest_high is not None
            and latest_low is not None
        ):

            break

    return latest_high, latest_low


# ============================================================
# CURRENT MARKET POSITION
# ============================================================

latest_index = len(normalized_candles) - 1

latest_candle = normalized_candles[
    latest_index
]

latest_close = latest_candle["close"]
latest_high = latest_candle["high"]
latest_low = latest_candle["low"]

latest_atr = calculate_atr(
    latest_index
)


last_structural_high, last_structural_low = (
    get_last_structural_levels(
        classified_swings
    )
)


# ============================================================
# DISTANCE TO STRUCTURAL LEVELS
# ============================================================

distance_to_high = None
distance_to_low = None

if last_structural_high is not None:

    distance_to_high = percentage_change(
        last_structural_high["price"],
        latest_close
    )


if last_structural_low is not None:

    distance_to_low = percentage_change(
        last_structural_low["price"],
        latest_close
    )


# ============================================================
# CURRENT MARKET POSITION REPORT
# ============================================================

print()
print("=" * 80)
print("CURRENT MARKET POSITION")
print("=" * 80)

print(
    f"Latest close: {latest_close:.5f}"
)

print(
    f"Latest high : {latest_high:.5f}"
)

print(
    f"Latest low  : {latest_low:.5f}"
)

print(
    f"Estimated ATR: {latest_atr:.5f}"
)

if last_structural_high:

    print(
        "Last structural high:",
        f"{last_structural_high['price']:.5f}",
        "| index:",
        last_structural_high["index"],
        "| structure:",
        last_structural_high["structure"]
    )

if last_structural_low:

    print(
        "Last structural low:",
        f"{last_structural_low['price']:.5f}",
        "| index:",
        last_structural_low["index"],
        "| structure:",
        last_structural_low["structure"]
    )

if distance_to_high is not None:

    print(
        f"Distance from structural high: "
        f"{distance_to_high:+.4%}"
    )

if distance_to_low is not None:

    print(
        f"Distance from structural low: "
        f"{distance_to_low:+.4%}"
    )


# ============================================================
# FIND MOST RECENT STRUCTURE EVENT
# ============================================================

latest_event = None

if structure_events:

    latest_event = structure_events[-1]


# ============================================================
# CURRENT STRUCTURE STATE
# ============================================================

def determine_current_state(
    structure_score,
    latest_close,
    structural_high,
    structural_low,
    latest_event
):

    # Most recent confirmed structural event has priority.
    if latest_event is not None:

        if (
            latest_event["type"]
            == "CHoCH_BULLISH"
            and latest_event["index"]
            == latest_index
        ):

            return "CURRENT_CANDLE_CHOCH_BULLISH"

        if (
            latest_event["type"]
            == "CHoCH_BEARISH"
            and latest_event["index"]
            == latest_index
        ):

            return "CURRENT_CANDLE_CHOCH_BEARISH"

        if (
            latest_event["type"]
            == "BOS_BULLISH"
            and latest_event["index"]
            == latest_index
        ):

            return "CURRENT_CANDLE_BOS_BULLISH"

        if (
            latest_event["type"]
            == "BOS_BEARISH"
            and latest_event["index"]
            == latest_index
        ):

            return "CURRENT_CANDLE_BOS_BEARISH"

    # Current close relative to the latest confirmed levels.
    if (
        structural_high is not None
        and latest_close > structural_high["price"]
    ):

        return "ABOVE_LAST_STRUCTURAL_HIGH"

    if (
        structural_low is not None
        and latest_close < structural_low["price"]
    ):

        return "BELOW_LAST_STRUCTURAL_LOW"

    if structure_score["direction"] == "BULLISH":

        return "BULLISH_STRUCTURE"

    if structure_score["direction"] == "BEARISH":

        return "BEARISH_STRUCTURE"

    if structure_score["direction"] == "RANGE / MIXED":

        return "RANGE / MIXED"

    return "UNKNOWN"


current_state = determine_current_state(
    recent_structure_score,
    latest_close,
    last_structural_high,
    last_structural_low,
    latest_event
)


print()
print("=" * 80)
print("CURRENT STRUCTURE STATE")
print("=" * 80)

print(
    "State:",
    current_state
)


# ============================================================
# STRUCTURAL QUALITY
# ============================================================

def calculate_structure_quality(
    swings,
    events
):

    if not swings:

        return {
            "quality": 0.0,
            "directional_ratio": 0.0,
            "event_factor": 0.0,
        }

    directional_swings = [

        swing

        for swing in swings

        if swing["structure"] in (
            "HH",
            "HL",
            "LH",
            "LL"
        )
    ]

    if not directional_swings:

        return {
            "quality": 0.0,
            "directional_ratio": 0.0,
            "event_factor": 0.0,
        }

    directional_ratio = (
        len(directional_swings)
        / len(swings)
    )

    recent_events_count = min(
        len(events),
        5
    )

    event_factor = (
        recent_events_count
        / 5.0
    )

    quality = (
        directional_ratio * 0.75
        + event_factor * 0.25
    )

    quality = min(
        1.0,
        max(
            0.0,
            quality
        )
    )

    return {
        "quality": quality,
        "directional_ratio": directional_ratio,
        "event_factor": event_factor,
    }


structure_quality = calculate_structure_quality(
    recent_swings,
    recent_events
)


print()
print("=" * 80)
print("STRUCTURE QUALITY")
print("=" * 80)

print(
    f"Structural quality: "
    f"{structure_quality['quality']:.2%}"
)

print(
    f"Directional swing ratio: "
    f"{structure_quality['directional_ratio']:.2%}"
)

print(
    f"Recent event factor: "
    f"{structure_quality['event_factor']:.2%}"
)

print(
    "IMPORTANT: This is NOT prediction confidence."
)


# ============================================================
# TREND CLASSIFICATION
# ============================================================

def classify_trend(swings):

    if not swings:

        return "UNKNOWN"

    bullish = 0
    bearish = 0

    for swing in swings:

        if swing["structure"] in (
            "HH",
            "HL"
        ):

            bullish += 1

        elif swing["structure"] in (
            "LH",
            "LL"
        ):

            bearish += 1

    total = bullish + bearish

    if total == 0:

        return "UNKNOWN"

    score = (
        bullish - bearish
    ) / total

    # Require both:
    #
    # 1. enough directional observations
    # 2. sufficient score
    #
    # before calling a trend.

    if (
        bullish >= MIN_DIRECTIONAL_POINTS
        and score >= STRUCTURE_DIRECTION_THRESHOLD
    ):

        return "UPTREND"

    if (
        bearish >= MIN_DIRECTIONAL_POINTS
        and score <= -STRUCTURE_DIRECTION_THRESHOLD
    ):

        return "DOWNTREND"

    return "RANGE / TRANSITION"


trend_classification = classify_trend(
    recent_swings
)


print(
    "Trend classification:",
    trend_classification
)


# ============================================================
# LAST EVENT DETAILS
# ============================================================

print()
print("=" * 80)
print("LATEST STRUCTURE EVENT")
print("=" * 80)

if latest_event is None:

    print(
        "No structure event detected."
    )

else:

    print(
        "Event:",
        latest_event["type"]
    )

    print(
        "Event index:",
        latest_event["index"]
    )

    print(
        f"Event close: "
        f"{latest_event['price']:.5f}"
    )

    print(
        f"Broken level: "
        f"{latest_event['broken_level']:.5f}"
    )

    print(
        "Broken swing index:",
        latest_event["broken_swing_index"]
    )

    print(
        "Event timestamp:",
        latest_event["timestamp"]
    )


# ============================================================
# STRUCTURE SUMMARY
# ============================================================

print()
print("=" * 80)
print("MARKET STRUCTURE SUMMARY")
print("=" * 80)

print(
    f"""
Trend:
    {trend_classification}

Structure:
    {recent_structure_score['direction']}

Current state:
    {current_state}

Structure score:
    {recent_structure_score['score']:+.3f}

Structural quality:
    {structure_quality['quality']:.2%}

Recent swing count:
    {len(recent_swings)}

Recent BOS / CHoCH count:
    {len(recent_events)}

Bullish structure points:
    {recent_structure_score['bullish']}

Bearish structure points:
    {recent_structure_score['bearish']}
"""
)


# ============================================================
# DATA INTEGRITY CHECK
# ============================================================

print()
print("=" * 80)
print("DATA INTEGRITY CHECK")
print("=" * 80)

timestamps = [
    candle["timestamp"]
    for candle in normalized_candles
    if candle["timestamp"] is not None
]

if len(timestamps) >= 2:

    timestamp_ordered = all(
        timestamps[i] <= timestamps[i + 1]
        for i in range(
            len(timestamps) - 1
        )
    )

    if timestamp_ordered:

        print(
            "Timestamp order: PASS"
        )

    else:

        print(
            "Timestamp order: WARNING"
        )

else:

    print(
        "Timestamp order: NOT AVAILABLE"
    )


# ============================================================
# IMPORTANT INTERPRETATION
# ============================================================

print()
print("=" * 80)
print("IMPORTANT INTERPRETATION")
print("=" * 80)

print(
    """
This experiment is DESCRIPTIVE.

It does NOT prove that any structure state predicts
future price movement.

Definitions used by this experiment:

    HH
        Higher High relative to the previous confirmed
        swing high.

    HL
        Higher Low relative to the previous confirmed
        swing low.

    LH
        Lower High relative to the previous confirmed
        swing high.

    LL
        Lower Low relative to the previous confirmed
        swing low.

    BOS
        A candle CLOSE beyond a previously confirmed
        structural swing level.

    CHoCH
        A structural break occurring after the detected
        directional bias was opposite.

Important:

    Swing detection is retrospective.

A swing requires candles AFTER the candidate candle.
Therefore a swing cannot be considered confirmed in
real-time until SWING_LOOKBACK future candles exist.

This is acceptable for this diagnostic experiment.

It must NOT be treated as a live trading signal without
removing the confirmation look-ahead.

Structural quality is NOT prediction confidence.

To determine whether market structure has predictive value,
the next experiment must test future outcomes.

Required future tests include:

    1. HH/HL -> future BUY outcome
    2. LH/LL -> future SELL outcome
    3. BOS -> future directional outcome
    4. CHoCH -> future directional outcome
    5. Structure + volatility
    6. Structure + momentum
    7. Structure + location
    8. Structure + candle behavior
    9. Coverage
   10. Accuracy
   11. Precision
   12. Recall
   13. Baseline comparison
   14. Out-of-sample testing
   15. Walk-forward validation
   16. Look-ahead-bias testing

A visually convincing structure pattern must NOT be
considered predictive until it survives out-of-sample testing.
"""
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
    "Learning memory : NOT MODIFIED"
)

print(
    "Trading         : DISABLED"
)

print()
print("=" * 80)
print("MLAI v3.5.1 MARKET STRUCTURE TEST COMPLETE")
print("=" * 80)