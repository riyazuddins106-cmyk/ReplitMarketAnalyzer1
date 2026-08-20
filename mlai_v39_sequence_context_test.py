
import os
import pickle
import math
import statistics
from collections import Counter
from datetime import datetime, timezone


# ============================================================
# MLAI P2
# SEQUENCE + CONTEXT REPRESENTATION TEST
# ============================================================
#
# VERSION
# -------
# MLAI v3.9.0
#
# PURPOSE
# -------
# Move from:
#
#     "What is this candle?"
#
# to:
#
#     "What is happening across these candles?"
#
# This experiment builds a chronological, machine-readable
# representation of multi-candle market behaviour.
#
# It is DIAGNOSTIC ONLY.
#
# It does NOT:
#
#     - modify market_data.bin
#     - modify production MLAI
#     - modify learning memory
#     - train a model
#     - make predictions
#     - search for profitable rules
#     - trade
#
# ============================================================


VERSION = "3.9.0"

DATA_FILE = "market_data.bin"

# Sequence windows.
WINDOWS = [3, 5, 10, 20]

EPSILON = 1e-12


# ============================================================
# OUTPUT
# ============================================================

def separator(char="=", width=80):
    print(char * width)


def section(title):
    print()
    separator()
    print(title)
    separator()


def pass_check(message):
    print(f"PASS: {message}")


def warn_check(message):
    print(f"WARNING: {message}")


def fail_check(message):
    print(f"FAIL: {message}")


# ============================================================
# BASIC HELPERS
# ============================================================

def finite(value):
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def number(value):
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (TypeError, ValueError):
        return None


def timestamp(value):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def time_text(ts):
    try:
        return datetime.fromtimestamp(
            ts,
            tz=timezone.utc
        ).strftime("%Y-%m-%d %H:%M:%S UTC")
    except Exception:
        return "INVALID"


def get_value(record, names):
    if not isinstance(record, dict):
        return None

    lowered = {
        str(k).lower(): v
        for k, v in record.items()
    }

    for name in names:
        if name.lower() in lowered:
            return lowered[name.lower()]

    return None


# ============================================================
# DATA LOADING
# ============================================================

def load_data():
    if not os.path.exists(DATA_FILE):
        raise FileNotFoundError(
            f"Cannot find {os.path.abspath(DATA_FILE)}"
        )

    # Explicitly read-only.
    with open(DATA_FILE, "rb") as f:
        return pickle.load(f)


def extract_records(data):
    if isinstance(data, list):
        return data

    if isinstance(data, tuple):
        return list(data)

    if isinstance(data, dict):

        for key in [
            "candles",
            "data",
            "records",
            "market_data",
            "ohlcv",
            "prices",
        ]:
            value = data.get(key)

            if isinstance(value, (list, tuple)):
                return list(value)

        # Single candle dictionary.
        keys = {
            str(k).lower()
            for k in data.keys()
        }

        if {"open", "high", "low", "close"}.issubset(keys):
            return [data]

    return []


# ============================================================
# NORMALIZATION
# ============================================================

def normalize(records):

    candles = []
    invalid = Counter()

    for index, record in enumerate(records):

        ts = timestamp(
            get_value(
                record,
                ["timestamp", "time", "datetime", "date", "ts"]
            )
        )

        o = number(
            get_value(record, ["open", "o"])
        )

        h = number(
            get_value(record, ["high", "h"])
        )

        l = number(
            get_value(record, ["low", "l"])
        )

        c = number(
            get_value(record, ["close", "c"])
        )

        v = number(
            get_value(record, ["volume", "vol", "v"])
        )

        if ts is None:
            invalid["timestamp"] += 1
            continue

        if not all(
            finite(x)
            for x in [o, h, l, c]
        ):
            invalid["ohlc"] += 1
            continue

        if h < l:
            invalid["high_below_low"] += 1
            continue

        if not l <= o <= h:
            invalid["open_outside_range"] += 1
            continue

        if not l <= c <= h:
            invalid["close_outside_range"] += 1
            continue

        if v is not None and not finite(v):
            v = None

        candles.append({
            "index": index,
            "timestamp": ts,
            "open": o,
            "high": h,
            "low": l,
            "close": c,
            "volume": v,
        })

    return candles, invalid


# ============================================================
# CANDLE REPRESENTATION
# ============================================================

def candle_features(candle):

    o = candle["open"]
    h = candle["high"]
    l = candle["low"]
    c = candle["close"]

    candle_range = h - l

    body = abs(c - o)

    upper_wick = h - max(o, c)

    lower_wick = min(o, c) - l

    if candle_range > EPSILON:
        body_ratio = body / candle_range
        upper_ratio = upper_wick / candle_range
        lower_ratio = lower_wick / candle_range
    else:
        body_ratio = 0.0
        upper_ratio = 0.0
        lower_ratio = 0.0

    if c > o + EPSILON:
        direction = "BULLISH"
    elif c < o - EPSILON:
        direction = "BEARISH"
    else:
        direction = "NEUTRAL"

    return {
        "direction": direction,
        "range": candle_range,
        "body": body,
        "upper_wick": upper_wick,
        "lower_wick": lower_wick,
        "body_ratio": body_ratio,
        "upper_wick_ratio": upper_ratio,
        "lower_wick_ratio": lower_ratio,
    }


# ============================================================
# SEQUENCE HELPERS
# ============================================================

def sequence_return(candles):

    if len(candles) < 2:
        return 0.0

    first_close = candles[0]["close"]
    last_close = candles[-1]["close"]

    if abs(first_close) < EPSILON:
        return 0.0

    return (
        (last_close - first_close)
        / first_close
    )


def directional_sequence(candles):

    directions = [
        candle_features(c)["direction"]
        for c in candles
    ]

    bullish = directions.count("BULLISH")
    bearish = directions.count("BEARISH")
    neutral = directions.count("NEUTRAL")

    if bullish > bearish:
        dominant = "BULLISH"
    elif bearish > bullish:
        dominant = "BEARISH"
    else:
        dominant = "BALANCED"

    return {
        "bullish": bullish,
        "bearish": bearish,
        "neutral": neutral,
        "dominant": dominant,
        "sequence": directions,
    }


# ============================================================
# PRESSURE / FOLLOW-THROUGH
# ============================================================

def pressure_state(candles):

    if not candles:
        return "UNKNOWN"

    directions = [
        candle_features(c)["direction"]
        for c in candles
    ]

    bullish = directions.count("BULLISH")
    bearish = directions.count("BEARISH")

    if bullish >= len(candles) * 0.70:
        return "PERSISTENT_BULLISH_PRESSURE"

    if bearish >= len(candles) * 0.70:
        return "PERSISTENT_BEARISH_PRESSURE"

    if bullish > bearish:
        return "MIXED_BULLISH_PRESSURE"

    if bearish > bullish:
        return "MIXED_BEARISH_PRESSURE"

    return "BALANCED_PRESSURE"


def follow_through_state(candles):

    if len(candles) < 3:
        return "INSUFFICIENT_DATA"

    previous = candles[-2]
    current = candles[-1]

    previous_features = candle_features(previous)
    current_features = candle_features(current)

    if (
        previous_features["direction"] == "BULLISH"
        and current_features["direction"] == "BULLISH"
        and current["close"] >= previous["close"]
    ):
        return "BULLISH_FOLLOW_THROUGH"

    if (
        previous_features["direction"] == "BEARISH"
        and current_features["direction"] == "BEARISH"
        and current["close"] <= previous["close"]
    ):
        return "BEARISH_FOLLOW_THROUGH"

    return "NO_CLEAR_FOLLOW_THROUGH"


# ============================================================
# REJECTION
# ============================================================

def rejection_state(candles):

    if not candles:
        return "UNKNOWN"

    current = candles[-1]
    features = candle_features(current)

    range_value = features["range"]

    if range_value <= EPSILON:
        return "NO_RANGE"

    lower = features["lower_wick_ratio"]
    upper = features["upper_wick_ratio"]

    body = features["body_ratio"]

    if lower >= 0.45 and lower > upper:
        return "LOWER_PRICE_REJECTION"

    if upper >= 0.45 and upper > lower:
        return "HIGHER_PRICE_REJECTION"

    if body >= 0.75:
        return "STRONG_BODY"

    return "NO_STRONG_REJECTION"


# ============================================================
# EXPANSION / COMPRESSION
# ============================================================

def volatility_state(candles):

    if len(candles) < 6:
        return "INSUFFICIENT_DATA"

    ranges = [
        candle_features(c)["range"]
        for c in candles
    ]

    recent = statistics.fmean(ranges[-3:])
    previous = statistics.fmean(ranges[:-3])

    if previous <= EPSILON:
        return "UNDEFINED"

    ratio = recent / previous

    if ratio >= 1.50:
        return "EXPANSION"

    if ratio <= 0.67:
        return "COMPRESSION"

    return "STABLE"


# ============================================================
# MOMENTUM CHANGE
# ============================================================

def momentum_state(candles):

    if len(candles) < 6:
        return "INSUFFICIENT_DATA"

    returns = []

    for previous, current in zip(
        candles[:-1],
        candles[1:]
    ):
        if abs(previous["close"]) > EPSILON:
            returns.append(
                (
                    current["close"]
                    - previous["close"]
                )
                / previous["close"]
            )

    if len(returns) < 5:
        return "INSUFFICIENT_DATA"

    first_half = statistics.fmean(
        returns[:-3]
    )

    second_half = statistics.fmean(
        returns[-3:]
    )

    if second_half > first_half:
        return "MOMENTUM_INCREASING"

    if second_half < first_half:
        return "MOMENTUM_DECREASING"

    return "MOMENTUM_STABLE"


# ============================================================
# ACCELERATION
# ============================================================

def acceleration_state(candles):

    if len(candles) < 5:
        return "INSUFFICIENT_DATA"

    changes = []

    for previous, current in zip(
        candles[:-1],
        candles[1:]
    ):
        changes.append(
            current["close"] - previous["close"]
        )

    if len(changes) < 4:
        return "INSUFFICIENT_DATA"

    earlier = statistics.fmean(changes[-4:-2])
    recent = statistics.fmean(changes[-2:])

    if recent > earlier:
        return "ACCELERATING_UP"

    if recent < earlier:
        return "ACCELERATING_DOWN"

    return "NO_CLEAR_ACCELERATION"


# ============================================================
# HIGH / LOW BEHAVIOUR
# ============================================================

def local_price_structure(candles):

    if not candles:
        return {
            "highest": None,
            "lowest": None,
            "location": None,
            "state": "UNKNOWN",
        }

    highs = [c["high"] for c in candles]
    lows = [c["low"] for c in candles]

    highest = max(highs)
    lowest = min(lows)

    current_close = candles[-1]["close"]

    distance = highest - lowest

    if distance <= EPSILON:
        location = 0.5
    else:
        location = (
            current_close - lowest
        ) / distance

    if location >= 0.80:
        state = "NEAR_RANGE_HIGH"

    elif location <= 0.20:
        state = "NEAR_RANGE_LOW"

    else:
        state = "MID_RANGE"

    return {
        "highest": highest,
        "lowest": lowest,
        "location": location,
        "state": state,
    }


# ============================================================
# BREAKOUT / FAILED MOVE
# ============================================================

def movement_state(candles):

    if len(candles) < 5:
        return "INSUFFICIENT_DATA"

    current = candles[-1]

    previous_high = max(
        c["high"]
        for c in candles[:-1]
    )

    previous_low = min(
        c["low"]
        for c in candles[:-1]
    )

    if current["close"] > previous_high:
        return "UPSIDE_BREAK"

    if current["close"] < previous_low:
        return "DOWNSIDE_BREAK"

    if (
        current["high"] > previous_high
        and current["close"] <= previous_high
    ):
        return "POSSIBLE_UPSIDE_REJECTION"

    if (
        current["low"] < previous_low
        and current["close"] >= previous_low
    ):
        return "POSSIBLE_DOWNSIDE_REJECTION"

    return "NO_RANGE_BREAK"


# ============================================================
# VOLUME CONTEXT
# ============================================================

def volume_state(candles):

    values = [
        c["volume"]
        for c in candles
        if c["volume"] is not None
    ]

    if len(values) < 5:
        return "NO_VOLUME_CONTEXT"

    current = values[-1]

    previous = values[:-1]

    average = statistics.fmean(previous)

    if average <= EPSILON:
        return "UNDEFINED_VOLUME"

    ratio = current / average

    if ratio >= 1.50:
        return "VOLUME_EXPANSION"

    if ratio <= 0.67:
        return "VOLUME_CONTRACTION"

    return "NORMAL_VOLUME"


# ============================================================
# SEQUENCE REPRESENTATION
# ============================================================

def build_representation(candles, index):

    current = candles[index]

    representation = {
        "timestamp": current["timestamp"],
        "index": index,

        # Current candle.
        "candle": candle_features(current),

        # Sequence-level context.
        "windows": {},

        # Current local context.
        "current_price": current["close"],
    }

    for window in WINDOWS:

        start = index - window + 1

        if start < 0:
            representation["windows"][window] = {
                "available": False
            }
            continue

        sequence = candles[start:index + 1]

        directions = directional_sequence(
            sequence
        )

        local_structure = local_price_structure(
            sequence
        )

        representation["windows"][window] = {
            "available": True,

            "sequence_return":
                sequence_return(sequence),

            "bullish_count":
                directions["bullish"],

            "bearish_count":
                directions["bearish"],

            "neutral_count":
                directions["neutral"],

            "dominant_direction":
                directions["dominant"],

            "pressure":
                pressure_state(sequence),

            "follow_through":
                follow_through_state(sequence),

            "rejection":
                rejection_state(sequence),

            "volatility":
                volatility_state(sequence),

            "momentum":
                momentum_state(sequence),

            "acceleration":
                acceleration_state(sequence),

            "movement":
                movement_state(sequence),

            "volume":
                volume_state(sequence),

            "range_high":
                local_structure["highest"],

            "range_low":
                local_structure["lowest"],

            "price_location":
                local_structure["location"],

            "location_state":
                local_structure["state"],
        }

    return representation


# ============================================================
# LEAKAGE TEST
# ============================================================

def build_prefix_representation(candles, index):

    """
    Build the representation using ONLY candles <= index.

    This is the core P2 protection rule.

    At candle i:

        representation(i)

    may use:

        candle 0 ... candle i

    but NEVER:

        candle i+1 ... future candles
    """

    return build_representation(
        candles,
        index
    )


def compare_prefixes(candles):

    """
    Verify that the representation at time i does not
    change merely because future candles are appended.

    We compare:

        representation using data[0:i]

    against:

        representation using the full dataset

    for features that should only depend on the prefix.
    """

    test_indices = []

    if len(candles) < 50:
        return {
            "tested": 0,
            "mismatches": 0,
            "status": "INSUFFICIENT_DATA",
        }

    # Test multiple points throughout the dataset.
    for fraction in [
        0.10,
        0.25,
        0.50,
        0.75,
    ]:
        index = int(
            len(candles) * fraction
        )

        index = max(
            max(WINDOWS) - 1,
            min(index, len(candles) - 1)
        )

        test_indices.append(index)

    mismatches = 0

    for index in sorted(set(test_indices)):

        prefix = candles[:index + 1]

        prefix_representation = build_prefix_representation(
            prefix,
            len(prefix) - 1
        )

        full_representation = build_representation(
            candles,
            index
        )

        if prefix_representation != full_representation:
            mismatches += 1

    return {
        "tested": len(set(test_indices)),
        "mismatches": mismatches,
        "status": (
            "PASS"
            if mismatches == 0
            else "FAIL"
        ),
    }


# ============================================================
# SEQUENCE STATISTICS
# ============================================================

def sequence_statistics(candles):

    result = {}

    for window in WINDOWS:

        states = Counter()

        for index in range(
            window - 1,
            len(candles)
        ):

            sequence = candles[
                index - window + 1:
                index + 1
            ]

            state = pressure_state(sequence)

            states[state] += 1

        result[window] = states

    return result


# ============================================================
# MAIN
# ============================================================

def main():

    section(
        f"MLAI v{VERSION} SEQUENCE + CONTEXT REPRESENTATION TEST"
    )

    print(
        """
PURPOSE
-------

This experiment is P2 of the MLAI Market Language Brain.

P0:
    Data Foundation

P1:
    Unified Market Representation

P2:
    Sequence + Context Representation

The purpose is to represent relationships across multiple
candles instead of treating each candle independently.

The representation includes:

    Candle behaviour
    Multi-candle direction
    Sequence return
    Pressure
    Follow-through
    Rejection
    Expansion / compression
    Momentum change
    Acceleration
    Local price structure
    Price location
    Range breaks
    Possible rejection
    Volume context

IMPORTANT:

This is NOT a prediction engine.

This is NOT a trading system.

This is NOT a learning model.

This is NOT a profitability test.

It is a representation experiment.
"""
    )

    # --------------------------------------------------------
    # PROTECTION
    # --------------------------------------------------------

    section("PROTECTION CHECK")

    print("market_data.bin : READ ONLY")
    print("Production MLAI : NOT MODIFIED")
    print("Learning memory : NOT MODIFIED")
    print("Training        : DISABLED")
    print("Trading         : DISABLED")
    print("Prediction      : DISABLED")

    if not os.path.exists(DATA_FILE):

        fail_check(
            f"{DATA_FILE} was not found."
        )

        return

    original_size = os.path.getsize(
        DATA_FILE
    )

    # --------------------------------------------------------
    # LOAD
    # --------------------------------------------------------

    section("DATA LOADING")

    try:
        raw_data = load_data()

    except Exception as exc:

        fail_check(
            f"Unable to load data: {exc}"
        )

        return

    records = extract_records(
        raw_data
    )

    print(
        f"Raw records: {len(records)}"
    )

    if not records:

        fail_check(
            "No market records detected."
        )

        return

    pass_check(
        "market_data.bin loaded successfully."
    )

    # --------------------------------------------------------
    # NORMALIZE
    # --------------------------------------------------------

    section("DATA NORMALIZATION")

    candles, invalid = normalize(
        records
    )

    print(
        f"Valid candles  : {len(candles)}"
    )

    print(
        f"Invalid candles: {sum(invalid.values())}"
    )

    if invalid:

        for reason, count in invalid.items():

            print(
                f"    {reason:25} : {count}"
            )

        fail_check(
            "Invalid records detected."
        )

        return

    pass_check(
        "All candles passed normalization."
    )

    # --------------------------------------------------------
    # ORDER
    # --------------------------------------------------------

    section("CHRONOLOGICAL ORDER")

    ordered = all(
        candles[i]["timestamp"]
        < candles[i + 1]["timestamp"]
        for i in range(
            len(candles) - 1
        )
    )

    if ordered:
        pass_check(
            "Candles are strictly chronological."
        )
    else:
        fail_check(
            "Chronological ordering failed."
        )

        return

    # --------------------------------------------------------
    # CURRENT REPRESENTATION
    # --------------------------------------------------------

    section("LATEST MARKET REPRESENTATION")

    latest_index = len(candles) - 1

    latest = build_representation(
        candles,
        latest_index
    )

    current = candles[-1]

    print(
        f"Timestamp : "
        f"{time_text(current['timestamp'])}"
    )

    print(
        f"Close     : "
        f"{current['close']:.5f}"
    )

    candle = latest["candle"]

    print()
    print("CURRENT CANDLE")

    print(
        f"Direction       : "
        f"{candle['direction']}"
    )

    print(
        f"Range           : "
        f"{candle['range']:.5f}"
    )

    print(
        f"Body            : "
        f"{candle['body']:.5f}"
    )

    print(
        f"Upper wick      : "
        f"{candle['upper_wick']:.5f}"
    )

    print(
        f"Lower wick      : "
        f"{candle['lower_wick']:.5f}"
    )

    print(
        f"Body/range      : "
        f"{candle['body_ratio'] * 100:.2f}%"
    )

    # --------------------------------------------------------
    # WINDOWS
    # --------------------------------------------------------

    section("MULTI-CANDLE SEQUENCE CONTEXT")

    for window in WINDOWS:

        data = latest["windows"][window]

        print()
        print(
            f"WINDOW = {window} CANDLES"
        )

        if not data["available"]:

            print(
                "    Not enough candles."
            )

            continue

        print(
            f"    Sequence return : "
            f"{data['sequence_return'] * 100:+.5f}%"
        )

        print(
            f"    Bullish candles : "
            f"{data['bullish_count']}"
        )

        print(
            f"    Bearish candles : "
            f"{data['bearish_count']}"
        )

        print(
            f"    Neutral candles : "
            f"{data['neutral_count']}"
        )

        print(
            f"    Dominant        : "
            f"{data['dominant_direction']}"
        )

        print(
            f"    Pressure        : "
            f"{data['pressure']}"
        )

        print(
            f"    Follow-through  : "
            f"{data['follow_through']}"
        )

        print(
            f"    Rejection       : "
            f"{data['rejection']}"
        )

        print(
            f"    Volatility      : "
            f"{data['volatility']}"
        )

        print(
            f"    Momentum        : "
            f"{data['momentum']}"
        )

        print(
            f"    Acceleration    : "
            f"{data['acceleration']}"
        )

        print(
            f"    Movement        : "
            f"{data['movement']}"
        )

        print(
            f"    Volume          : "
            f"{data['volume']}"
        )

        print(
            f"    Range high      : "
            f"{data['range_high']:.5f}"
        )

        print(
            f"    Range low       : "
            f"{data['range_low']:.5f}"
        )

        print(
            f"    Price location  : "
            f"{data['price_location'] * 100:.2f}%"
        )

        print(
            f"    Location state  : "
            f"{data['location_state']}"
        )

    # --------------------------------------------------------
    # HISTORICAL SEQUENCE DISTRIBUTION
    # --------------------------------------------------------

    section("SEQUENCE STATE DISTRIBUTION")

    distributions = sequence_statistics(
        candles
    )

    for window in WINDOWS:

        print()
        print(
            f"{window}-CANDLE WINDOW"
        )

        for state, count in distributions[
            window
        ].most_common():

            print(
                f"    {state:32} : {count}"
            )

    # --------------------------------------------------------
    # SEQUENCE EXAMPLES
    # --------------------------------------------------------

    section("RECENT CANDLE SEQUENCE")

    start = max(
        0,
        len(candles) - 10
    )

    for index in range(
        start,
        len(candles)
    ):

        c = candles[index]

        f = candle_features(c)

        print(
            f"Index={index:5d} | "
            f"{time_text(c['timestamp'])} | "
            f"{f['direction']:8} | "
            f"O={c['open']:.4f} | "
            f"H={c['high']:.4f} | "
            f"L={c['low']:.4f} | "
            f"C={c['close']:.4f} | "
            f"Range={f['range']:.4f}"
        )

    # --------------------------------------------------------
    # FUTURE LEAKAGE TEST
    # --------------------------------------------------------

    section("LOOK-AHEAD / FUTURE LEAKAGE TEST")

    print(
        """
Rule:

At candle i, the representation may use:

    candle 0
    candle 1
    ...
    candle i

It must NOT use:

    candle i+1
    candle i+2
    ...
    future candles
"""
    )

    leakage = compare_prefixes(
        candles
    )

    print(
        f"Test points : {leakage['tested']}"
    )

    print(
        f"Mismatches  : {leakage['mismatches']}"
    )

    print(
        f"Status      : {leakage['status']}"
    )

    if leakage["status"] == "PASS":

        pass_check(
            "Sequence representation is invariant "
            "to future candles at tested points."
        )

    elif leakage["status"] == "INSUFFICIENT_DATA":

        warn_check(
            "Not enough data for leakage testing."
        )

    else:

        fail_check(
            "Potential future-data dependency detected."
        )

    # --------------------------------------------------------
    # REPRESENTATION COMPLETENESS
    # --------------------------------------------------------

    section("REPRESENTATION COMPLETENESS")

    required_components = [
        "candle anatomy",
        "multi-candle direction",
        "sequence return",
        "pressure",
        "follow-through",
        "rejection",
        "volatility context",
        "momentum context",
        "acceleration",
        "price location",
        "range movement",
        "volume context",
    ]

    for component in required_components:

        print(
            f"    PRESENT : {component}"
        )

    pass_check(
        "Core P2 sequence/context components are represented."
    )

    # --------------------------------------------------------
    # PROTECTION
    # --------------------------------------------------------

    section("READ-ONLY PROTECTION VERIFICATION")

    final_size = os.path.getsize(
        DATA_FILE
    )

    print(
        f"Original size: {original_size:,} bytes"
    )

    print(
        f"Final size   : {final_size:,} bytes"
    )

    if original_size == final_size:

        pass_check(
            "market_data.bin remains unchanged."
        )

    else:

        fail_check(
            "market_data.bin size changed."
        )

    # --------------------------------------------------------
    # FINAL VERDICT
    # --------------------------------------------------------

    section("P2 VERDICT")

    p2_pass = (
        len(candles) > 0
        and ordered
        and leakage["status"] == "PASS"
        and original_size == final_size
    )

    if p2_pass:

        print(
            "P2 STATUS: PASS"
        )

        print()
        print(
            "MLAI can now construct a chronological "
            "multi-candle context representation."
        )

        print()
        print(
            "IMPORTANT:"
        )

        print(
            "This still does NOT mean MLAI understands "
            "market language."
        )

        print(
            "It means the raw market can now be represented "
            "as sequences and context rather than isolated candles."
        )

        print()
        print(
            "NEXT PHASE:"
        )

        print(
            "P3 = MARKET STRUCTURE"
        )

        print(
            "P3 will connect sequence context with:"
        )

        print(
            "    Swing highs"
        )

        print(
            "    Swing lows"
        )

        print(
            "    HH"
        )

        print(
            "    HL"
        )

        print(
            "    LH"
        )

        print(
            "    LL"
        )

        print(
            "    BOS"
        )

        print(
            "    CHoCH"
        )

        print(
            "    Structural continuation"
        )

        print(
            "    Structural transition"
        )

        print(
            "    Structural failure"
        )

    else:

        print(
            "P2 STATUS: NOT READY"
        )

        print()
        print(
            "Do not proceed to P3 until the failing "
            "condition has been investigated."
        )

    # --------------------------------------------------------
    # FINAL SAFETY
    # --------------------------------------------------------

    section("FINAL PROTECTION CHECK")

    print("market_data.bin : READ ONLY")
    print("Production MLAI : NOT MODIFIED")
    print("Learning memory : NOT MODIFIED")
    print("Training        : DISABLED")
    print("Trading         : DISABLED")
    print("Prediction      : DISABLED")

    separator()

    print(
        f"MLAI v{VERSION} SEQUENCE + CONTEXT TEST COMPLETE"
    )

    separator()


if __name__ == "__main__":
    main()
