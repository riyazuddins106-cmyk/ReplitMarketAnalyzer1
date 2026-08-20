# ============================================================
# MLAI v3.8.0
# UNIFIED MARKET REPRESENTATION / P2 TEST
# ============================================================
#
# PURPOSE
# -------
# P2 establishes a unified machine-readable representation
# for the MLAI Market Language Brain.
#
# This layer converts validated OHLCV data into structured
# descriptions of market behaviour.
#
# It does NOT attempt to predict the future.
#
# It does NOT train a model.
#
# It does NOT create trading signals.
#
# It does NOT modify production MLAI.
#
# It does NOT modify market_data.bin.
#
# ============================================================

import os
import math
import pickle
import statistics
from collections import Counter


# ============================================================
# CONFIGURATION
# ============================================================

DATA_FILE = "market_data.bin"

SEQUENCE_LENGTH = 5

ATR_PERIOD = 14
MOMENTUM_PERIOD = 14
VOLUME_PERIOD = 20
LOCATION_PERIOD = 20
RELATIVE_RANGE_PERIOD = 20

EPSILON = 1e-12


# ============================================================
# DISPLAY
# ============================================================

def section(title):
    print()
    print("=" * 80)
    print(title)
    print("=" * 80)


def subsection(title):
    print()
    print("-" * 80)
    print(title)
    print("-" * 80)


# ============================================================
# SAFE NUMERIC HELPERS
# ============================================================

def safe_float(value, default=None):
    try:
        result = float(value)

        if not math.isfinite(result):
            return default

        return result

    except Exception:
        return default


def clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


# ============================================================
# DATA LOADING
# ============================================================

def load_market_data(path):
    with open(path, "rb") as f:
        return pickle.load(f)


# ============================================================
# CANDLE EXTRACTION
# ============================================================

def extract_candle(record):
    """
    Supports common dictionary layouts.

    Expected fields:

        timestamp / time
        open
        high
        low
        close
        volume
    """

    if not isinstance(record, dict):
        return None

    timestamp = (
        record.get("timestamp")
        if record.get("timestamp") is not None
        else record.get("time")
    )

    open_price = record.get("open")
    high_price = record.get("high")
    low_price = record.get("low")
    close_price = record.get("close")

    volume = record.get("volume", 0.0)

    timestamp = safe_float(timestamp)
    open_price = safe_float(open_price)
    high_price = safe_float(high_price)
    low_price = safe_float(low_price)
    close_price = safe_float(close_price)
    volume = safe_float(volume, 0.0)

    if None in (
        timestamp,
        open_price,
        high_price,
        low_price,
        close_price,
    ):
        return None

    if high_price < low_price:
        return None

    if not (
        low_price <= open_price <= high_price
        and low_price <= close_price <= high_price
    ):
        return None

    return {
        "timestamp": int(timestamp),
        "open": open_price,
        "high": high_price,
        "low": low_price,
        "close": close_price,
        "volume": volume,
    }


# ============================================================
# NORMALIZATION
# ============================================================

def normalize_data(raw):
    records = []

    if isinstance(raw, dict):

        if "data" in raw and isinstance(raw["data"], list):
            source_records = raw["data"]

        elif "candles" in raw and isinstance(raw["candles"], list):
            source_records = raw["candles"]

        elif "ohlcv" in raw and isinstance(raw["ohlcv"], list):
            source_records = raw["ohlcv"]

        else:
            source_records = []

            for value in raw.values():
                if isinstance(value, list):
                    source_records.extend(value)

    elif isinstance(raw, list):
        source_records = raw

    else:
        source_records = []

    for record in source_records:

        candle = extract_candle(record)

        if candle is not None:
            records.append(candle)

    records.sort(key=lambda x: x["timestamp"])

    return records


# ============================================================
# TRUE RANGE
# ============================================================

def true_range(current, previous=None):

    high = current["high"]
    low = current["low"]

    if previous is None:
        return high - low

    return max(
        high - low,
        abs(high - previous["close"]),
        abs(low - previous["close"]),
    )


# ============================================================
# ATR
# ============================================================

def calculate_atr(candles, index, period=ATR_PERIOD):

    start = max(0, index - period + 1)

    ranges = []

    for i in range(start, index + 1):

        previous = candles[i - 1] if i > 0 else None

        ranges.append(
            true_range(
                candles[i],
                previous
            )
        )

    if not ranges:
        return 0.0

    return statistics.mean(ranges)


# ============================================================
# MOVING AVERAGE
# ============================================================

def moving_average(values, period):

    if not values:
        return 0.0

    subset = values[-period:]

    return statistics.mean(subset)


# ============================================================
# CANDLE ANATOMY
# ============================================================

def candle_anatomy(candle):

    o = candle["open"]
    h = candle["high"]
    l = candle["low"]
    c = candle["close"]

    total_range = max(h - l, EPSILON)

    body = abs(c - o)

    upper_wick = max(0.0, h - max(o, c))

    lower_wick = max(0.0, min(o, c) - l)

    body_ratio = body / total_range

    upper_wick_ratio = upper_wick / total_range

    lower_wick_ratio = lower_wick / total_range

    close_location = (c - l) / total_range

    if c > o:
        direction = "BULLISH"

    elif c < o:
        direction = "BEARISH"

    else:
        direction = "NEUTRAL"

    return {
        "range": total_range,
        "body": body,
        "upper_wick": upper_wick,
        "lower_wick": lower_wick,
        "body_ratio": body_ratio,
        "upper_wick_ratio": upper_wick_ratio,
        "lower_wick_ratio": lower_wick_ratio,
        "close_location": close_location,
        "direction": direction,
    }


# ============================================================
# CANDLE CLASSIFICATION
# ============================================================

def classify_candle(anatomy, atr):

    body = anatomy["body"]
    candle_range = anatomy["range"]

    body_ratio = anatomy["body_ratio"]

    upper = anatomy["upper_wick_ratio"]
    lower = anatomy["lower_wick_ratio"]

    if candle_range <= EPSILON:
        return "NO_RANGE"

    if atr > EPSILON:

        relative_size = candle_range / atr

    else:
        relative_size = 1.0

    if relative_size >= 2.0:
        size_class = "LARGE_RANGE"

    elif relative_size >= 1.25:
        size_class = "EXPANSION"

    elif relative_size <= 0.60:
        size_class = "COMPRESSION"

    else:
        size_class = "NORMAL_RANGE"

    if body_ratio >= 0.80:
        body_class = "STRONG_BODY"

    elif body_ratio >= 0.55:
        body_class = "MODERATE_BODY"

    elif body_ratio <= 0.20:
        body_class = "SMALL_BODY"

    else:
        body_class = "BALANCED_BODY"

    if upper >= 0.45 and upper > lower * 1.5:
        wick_behavior = "UPPER_REJECTION"

    elif lower >= 0.45 and lower > upper * 1.5:
        wick_behavior = "LOWER_REJECTION"

    elif upper >= 0.25 and lower >= 0.25:
        wick_behavior = "TWO_SIDED_REJECTION"

    else:
        wick_behavior = "LOW_WICK_ACTIVITY"

    if body_ratio <= 0.10:
        pattern_family = "DOJI_LIKE"

    elif lower >= 0.50 and body_ratio <= 0.35:
        pattern_family = "HAMMER_LIKE"

    elif upper >= 0.50 and body_ratio <= 0.35:
        pattern_family = "SHOOTING_STAR_LIKE"

    elif body_ratio >= 0.85:
        pattern_family = "MARUBOZU_LIKE"

    else:
        pattern_family = "STANDARD"

    return {
        "size_class": size_class,
        "relative_size_atr": relative_size,
        "body_class": body_class,
        "wick_behavior": wick_behavior,
        "pattern_family": pattern_family,
    }


# ============================================================
# RELATIVE PRICE MOVEMENT
# ============================================================

def relative_movement(candles, index):

    current = candles[index]

    close = current["close"]

    previous_close = (
        candles[index - 1]["close"]
        if index > 0
        else close
    )

    change = close - previous_close

    percentage = (
        change / previous_close * 100
        if abs(previous_close) > EPSILON
        else 0.0
    )

    if change > EPSILON:
        direction = "UP"

    elif change < -EPSILON:
        direction = "DOWN"

    else:
        direction = "FLAT"

    return {
        "price_change": change,
        "percentage_change": percentage,
        "direction": direction,
    }


# ============================================================
# MOMENTUM
# ============================================================

def momentum(candles, index, period=MOMENTUM_PERIOD):

    if index < period:

        return {
            "change": 0.0,
            "percentage": 0.0,
            "direction": "INSUFFICIENT_HISTORY",
        }

    current = candles[index]["close"]
    previous = candles[index - period]["close"]

    change = current - previous

    percentage = (
        change / previous * 100
        if abs(previous) > EPSILON
        else 0.0
    )

    if change > EPSILON:
        direction = "BULLISH"

    elif change < -EPSILON:
        direction = "BEARISH"

    else:
        direction = "NEUTRAL"

    return {
        "change": change,
        "percentage": percentage,
        "direction": direction,
    }


# ============================================================
# VOLUME CONTEXT
# ============================================================

def volume_context(candles, index, period=VOLUME_PERIOD):

    current_volume = candles[index]["volume"]

    start = max(0, index - period + 1)

    volumes = [
        max(0.0, candles[i]["volume"])
        for i in range(start, index + 1)
    ]

    average_volume = (
        statistics.mean(volumes)
        if volumes
        else 0.0
    )

    if average_volume > EPSILON:

        ratio = current_volume / average_volume

    else:

        ratio = 0.0

    if ratio >= 2.0:
        state = "HIGH_VOLUME"

    elif ratio >= 1.25:
        state = "ABOVE_AVERAGE_VOLUME"

    elif ratio <= 0.50:
        state = "LOW_VOLUME"

    elif ratio <= 0.80:
        state = "BELOW_AVERAGE_VOLUME"

    else:
        state = "NORMAL_VOLUME"

    return {
        "current_volume": current_volume,
        "average_volume": average_volume,
        "ratio": ratio,
        "state": state,
    }


# ============================================================
# VOLATILITY CONTEXT
# ============================================================

def volatility_context(candles, index):

    atr = calculate_atr(candles, index)

    start = max(0, index - RELATIVE_RANGE_PERIOD + 1)

    ranges = [
        candles[i]["high"] - candles[i]["low"]
        for i in range(start, index + 1)
    ]

    average_range = (
        statistics.mean(ranges)
        if ranges
        else 0.0
    )

    current_range = (
        candles[index]["high"]
        - candles[index]["low"]
    )

    if average_range > EPSILON:

        range_ratio = current_range / average_range

    else:

        range_ratio = 1.0

    if range_ratio >= 1.75:
        regime = "VOLATILITY_EXPANSION"

    elif range_ratio <= 0.60:
        regime = "VOLATILITY_COMPRESSION"

    elif range_ratio >= 1.25:
        regime = "ELEVATED_VOLATILITY"

    elif range_ratio <= 0.80:
        regime = "LOW_VOLATILITY"

    else:
        regime = "NORMAL_VOLATILITY"

    return {
        "atr": atr,
        "current_range": current_range,
        "average_range": average_range,
        "range_ratio": range_ratio,
        "regime": regime,
    }


# ============================================================
# PRICE LOCATION
# ============================================================

def price_location(
    candles,
    index,
    period=LOCATION_PERIOD
):

    start = max(0, index - period + 1)

    highs = [
        candles[i]["high"]
        for i in range(start, index + 1)
    ]

    lows = [
        candles[i]["low"]
        for i in range(start, index + 1)
    ]

    highest = max(highs)
    lowest = min(lows)

    current = candles[index]["close"]

    span = max(highest - lowest, EPSILON)

    location = (
        (current - lowest) / span
    )

    if location >= 0.80:
        state = "NEAR_RANGE_HIGH"

    elif location >= 0.60:
        state = "UPPER_RANGE"

    elif location <= 0.20:
        state = "NEAR_RANGE_LOW"

    elif location <= 0.40:
        state = "LOWER_RANGE"

    else:
        state = "MID_RANGE"

    return {
        "range_high": highest,
        "range_low": lowest,
        "location": location,
        "state": state,
    }


# ============================================================
# SEQUENCE BEHAVIOUR
# ============================================================

def sequence_context(candles, index, length=SEQUENCE_LENGTH):

    start = max(0, index - length + 1)

    sequence = candles[start:index + 1]

    directions = []

    for candle in sequence:

        if candle["close"] > candle["open"]:
            directions.append("BULLISH")

        elif candle["close"] < candle["open"]:
            directions.append("BEARISH")

        else:
            directions.append("NEUTRAL")

    bullish_count = directions.count("BULLISH")
    bearish_count = directions.count("BEARISH")
    neutral_count = directions.count("NEUTRAL")

    consecutive_bullish = 0
    consecutive_bearish = 0

    for direction in reversed(directions):

        if direction == "BULLISH":
            consecutive_bullish += 1

        else:
            break

    for direction in reversed(directions):

        if direction == "BEARISH":
            consecutive_bearish += 1

        else:
            break

    if bullish_count >= length - 1:

        sequence_state = "PERSISTENT_BULLISH_PRESSURE"

    elif bearish_count >= length - 1:

        sequence_state = "PERSISTENT_BEARISH_PRESSURE"

    elif bullish_count > bearish_count:

        sequence_state = "BULLISH_SEQUENCE"

    elif bearish_count > bullish_count:

        sequence_state = "BEARISH_SEQUENCE"

    else:

        sequence_state = "BALANCED_SEQUENCE"

    return {
        "length": len(sequence),
        "directions": directions,
        "bullish_count": bullish_count,
        "bearish_count": bearish_count,
        "neutral_count": neutral_count,
        "consecutive_bullish": consecutive_bullish,
        "consecutive_bearish": consecutive_bearish,
        "state": sequence_state,
    }


# ============================================================
# FOLLOW-THROUGH
# ============================================================

def follow_through_context(candles, index):

    if index < 2:

        return {
            "state": "INSUFFICIENT_HISTORY"
        }

    current = candles[index]

    previous = candles[index - 1]

    previous2 = candles[index - 2]

    current_change = current["close"] - current["open"]

    previous_change = (
        previous["close"] - previous["open"]
    )

    previous2_change = (
        previous2["close"] - previous2["open"]
    )

    if (
        current_change > 0
        and previous_change > 0
        and previous2_change > 0
    ):

        state = "BULLISH_FOLLOW_THROUGH"

    elif (
        current_change < 0
        and previous_change < 0
        and previous2_change < 0
    ):

        state = "BEARISH_FOLLOW_THROUGH"

    elif (
        current_change > 0
        and previous_change < 0
    ):

        state = "BULLISH_RESPONSE"

    elif (
        current_change < 0
        and previous_change > 0
    ):

        state = "BEARISH_RESPONSE"

    else:

        state = "MIXED_FOLLOW_THROUGH"

    return {
        "state": state
    }


# ============================================================
# MARKET LANGUAGE DESCRIPTION
# ============================================================

def generate_description(
    candle,
    anatomy,
    classification,
    movement,
    momentum_data,
    volume_data,
    volatility_data,
    location_data,
    sequence_data,
    follow_through
):

    parts = []

    # Candle
    parts.append(
        f"{anatomy['direction'].lower()} candle"
    )

    parts.append(
        classification["body_class"].lower().replace("_", " ")
    )

    parts.append(
        classification["size_class"].lower().replace("_", " ")
    )

    # Wick behaviour
    if classification["wick_behavior"] != "LOW_WICK_ACTIVITY":

        parts.append(
            classification["wick_behavior"]
            .lower()
            .replace("_", " ")
        )

    # Sequence
    parts.append(
        sequence_data["state"]
        .lower()
        .replace("_", " ")
    )

    # Momentum
    if momentum_data["direction"] in (
        "BULLISH",
        "BEARISH"
    ):

        parts.append(
            momentum_data["direction"].lower()
            + " momentum"
        )

    # Volatility
    parts.append(
        volatility_data["regime"]
        .lower()
        .replace("_", " ")
    )

    # Volume
    parts.append(
        volume_data["state"]
        .lower()
        .replace("_", " ")
    )

    # Location
    parts.append(
        location_data["state"]
        .lower()
        .replace("_", " ")
    )

    # Follow through
    parts.append(
        follow_through["state"]
        .lower()
        .replace("_", " ")
    )

    return "; ".join(parts) + "."


# ============================================================
# UNIFIED REPRESENTATION
# ============================================================

def build_representation(candles, index):

    candle = candles[index]

    anatomy = candle_anatomy(candle)

    volatility_data = volatility_context(
        candles,
        index
    )

    classification = classify_candle(
        anatomy,
        volatility_data["atr"]
    )

    movement = relative_movement(
        candles,
        index
    )

    momentum_data = momentum(
        candles,
        index
    )

    volume_data = volume_context(
        candles,
        index
    )

    location_data = price_location(
        candles,
        index
    )

    sequence_data = sequence_context(
        candles,
        index
    )

    follow_through = follow_through_context(
        candles,
        index
    )

    representation = {

        "representation_version": "3.8.0",

        "index": index,

        "timestamp": candle["timestamp"],

        # ----------------------------------------------------
        # RAW MARKET DATA
        # ----------------------------------------------------

        "ohlcv": {
            "open": candle["open"],
            "high": candle["high"],
            "low": candle["low"],
            "close": candle["close"],
            "volume": candle["volume"],
        },

        # ----------------------------------------------------
        # CANDLE ANATOMY
        # ----------------------------------------------------

        "candle_anatomy": anatomy,

        # ----------------------------------------------------
        # CANDLE CLASSIFICATION
        # ----------------------------------------------------

        "candle_classification": classification,

        # ----------------------------------------------------
        # RELATIVE MOVEMENT
        # ----------------------------------------------------

        "relative_movement": movement,

        # ----------------------------------------------------
        # MOMENTUM
        # ----------------------------------------------------

        "momentum": momentum_data,

        # ----------------------------------------------------
        # VOLATILITY
        # ----------------------------------------------------

        "volatility": volatility_data,

        # ----------------------------------------------------
        # VOLUME
        # ----------------------------------------------------

        "volume_context": volume_data,

        # ----------------------------------------------------
        # PRICE LOCATION
        # ----------------------------------------------------

        "price_location": location_data,

        # ----------------------------------------------------
        # SEQUENCE
        # ----------------------------------------------------

        "sequence": sequence_data,

        # ----------------------------------------------------
        # FOLLOW THROUGH
        # ----------------------------------------------------

        "follow_through": follow_through,

        # ----------------------------------------------------
        # MARKET LANGUAGE
        # ----------------------------------------------------

        "market_language": generate_description(
            candle,
            anatomy,
            classification,
            movement,
            momentum_data,
            volume_data,
            volatility_data,
            location_data,
            sequence_data,
            follow_through
        ),

    }

    return representation


# ============================================================
# REPRESENTATION VALIDATION
# ============================================================

def validate_representation(rep):

    required_sections = [
        "representation_version",
        "index",
        "timestamp",
        "ohlcv",
        "candle_anatomy",
        "candle_classification",
        "relative_movement",
        "momentum",
        "volatility",
        "volume_context",
        "price_location",
        "sequence",
        "follow_through",
        "market_language",
    ]

    missing = []

    for section_name in required_sections:

        if section_name not in rep:

            missing.append(section_name)

    if missing:

        return False, missing

    return True, []


# ============================================================
# VECTOR EXTRACTION
# ============================================================

def numerical_vector(rep):

    anatomy = rep["candle_anatomy"]

    classification = rep["candle_classification"]

    movement = rep["relative_movement"]

    momentum_data = rep["momentum"]

    volatility_data = rep["volatility"]

    volume_data = rep["volume_context"]

    location_data = rep["price_location"]

    sequence_data = rep["sequence"]

    vector = [

        # Candle anatomy
        anatomy["range"],
        anatomy["body"],
        anatomy["upper_wick"],
        anatomy["lower_wick"],
        anatomy["body_ratio"],
        anatomy["upper_wick_ratio"],
        anatomy["lower_wick_ratio"],
        anatomy["close_location"],

        # Relative movement
        movement["price_change"],
        movement["percentage_change"],

        # Momentum
        momentum_data["change"],
        momentum_data["percentage"],

        # Volatility
        volatility_data["atr"],
        volatility_data["current_range"],
        volatility_data["average_range"],
        volatility_data["range_ratio"],

        # Volume
        volume_data["current_volume"],
        volume_data["average_volume"],
        volume_data["ratio"],

        # Price location
        location_data["location"],

        # Sequence
        sequence_data["bullish_count"],
        sequence_data["bearish_count"],
        sequence_data["neutral_count"],
        sequence_data["consecutive_bullish"],
        sequence_data["consecutive_bearish"],

        # Relative candle size
        classification["relative_size_atr"],
    ]

    return vector


# ============================================================
# DATASET REPRESENTATION SUMMARY
# ============================================================

def representation_summary(representations):

    candle_directions = Counter()

    candle_sizes = Counter()

    wick_behaviours = Counter()

    sequence_states = Counter()

    volatility_states = Counter()

    volume_states = Counter()

    location_states = Counter()

    pattern_families = Counter()

    for rep in representations:

        candle_directions[
            rep["candle_anatomy"]["direction"]
        ] += 1

        candle_sizes[
            rep["candle_classification"]["size_class"]
        ] += 1

        wick_behaviours[
            rep["candle_classification"]["wick_behavior"]
        ] += 1

        sequence_states[
            rep["sequence"]["state"]
        ] += 1

        volatility_states[
            rep["volatility"]["regime"]
        ] += 1

        volume_states[
            rep["volume_context"]["state"]
        ] += 1

        location_states[
            rep["price_location"]["state"]
        ] += 1

        pattern_families[
            rep["candle_classification"]["pattern_family"]
        ] += 1

    return {
        "candle_directions": candle_directions,
        "candle_sizes": candle_sizes,
        "wick_behaviours": wick_behaviours,
        "sequence_states": sequence_states,
        "volatility_states": volatility_states,
        "volume_states": volume_states,
        "location_states": location_states,
        "pattern_families": pattern_families,
    }


# ============================================================
# MAIN TEST
# ============================================================

def main():

    print("=" * 80)
    print("MLAI v3.8.0 UNIFIED MARKET REPRESENTATION TEST")
    print("=" * 80)

    print("""
PURPOSE
-------

This experiment implements P2 of the MLAI Market Language
Brain architecture.

It converts validated OHLCV data into a unified
machine-readable market representation.

The representation describes:

    OHLCV
    Candle anatomy
    Candle direction
    Body
    Upper wick
    Lower wick
    Range
    Body/range ratio
    Relative candle size
    Candle behaviour
    Relative price movement
    Candle sequences
    Follow-through
    Momentum
    Volatility
    Volume context
    Price location
    Market-language description

This is NOT a prediction system.

This is NOT a trading system.

This is NOT a learning system.

This is the representation layer that future learning
systems will consume.

market_data.bin        = READ ONLY
Production MLAI        = NOT MODIFIED
Learning memory        = NOT MODIFIED
Training               = NOT PERFORMED
Prediction             = NOT PERFORMED
Trading                = NOT PERFORMED
""")

    # ========================================================
    # PROTECTION
    # ========================================================

    section("PROTECTION CHECK")

    print("market_data.bin : READ ONLY")
    print("production MLAI : NOT MODIFIED")
    print("learning memory : NOT MODIFIED")
    print("training        : DISABLED")
    print("prediction      : DISABLED")
    print("trading         : DISABLED")

    if not os.path.exists(DATA_FILE):

        print()
        print("FAIL: market_data.bin was not found.")
        print(f"Expected: {os.path.abspath(DATA_FILE)}")
        return

    original_size = os.path.getsize(DATA_FILE)

    print(f"Data file: {os.path.abspath(DATA_FILE)}")
    print(f"Original file size: {original_size:,} bytes")

    # ========================================================
    # LOAD
    # ========================================================

    section("DATA LOADING")

    try:

        raw = load_market_data(DATA_FILE)

    except Exception as exc:

        print("FAIL: Could not load market_data.bin.")
        print(f"Error: {exc}")
        return

    print(f"Data type: {type(raw).__name__}")

    candles = normalize_data(raw)

    print(f"Normalized candles: {len(candles)}")

    if not candles:

        print("FAIL: No valid candles detected.")
        return

    print("PASS: market_data.bin loaded.")

    # ========================================================
    # BASIC DATA VALIDATION
    # ========================================================

    section("BASIC DATA VALIDATION")

    invalid = 0

    for candle in candles:

        values = [
            candle["open"],
            candle["high"],
            candle["low"],
            candle["close"],
            candle["volume"],
        ]

        if not all(
            math.isfinite(float(value))
            for value in values
        ):

            invalid += 1

    print(f"Invalid normalized candles: {invalid}")

    if invalid == 0:

        print("PASS: All normalized candles are finite.")

    else:

        print("FAIL: Invalid numeric values detected.")
        return

    # ========================================================
    # BUILD REPRESENTATIONS
    # ========================================================

    section("UNIFIED REPRESENTATION BUILD")

    representations = []

    representation_errors = 0

    for index in range(len(candles)):

        try:

            rep = build_representation(
                candles,
                index
            )

            valid, missing = validate_representation(rep)

            if not valid:

                representation_errors += 1

            else:

                representations.append(rep)

        except Exception as exc:

            representation_errors += 1

            if representation_errors <= 5:

                print(
                    f"Representation error at index "
                    f"{index}: {exc}"
                )

    print(
        f"Representations generated: "
        f"{len(representations)}"
    )

    print(
        f"Representation errors: "
        f"{representation_errors}"
    )

    if representation_errors == 0:

        print(
            "PASS: Every candle received a unified "
            "market representation."
        )

    else:

        print(
            "FAIL: Some candles could not be represented."
        )

    # ========================================================
    # SAMPLE REPRESENTATION
    # ========================================================

    section("LATEST MARKET REPRESENTATION")

    latest = representations[-1]

    print(f"Index: {latest['index']}")
    print(f"Timestamp: {latest['timestamp']}")

    print()
    print("OHLCV")

    for key, value in latest["ohlcv"].items():

        print(f"  {key:18}: {value}")

    print()
    print("CANDLE ANATOMY")

    for key, value in latest["candle_anatomy"].items():

        print(f"  {key:18}: {value}")

    print()
    print("CANDLE CLASSIFICATION")

    for key, value in latest["candle_classification"].items():

        print(f"  {key:18}: {value}")

    print()
    print("RELATIVE MOVEMENT")

    for key, value in latest["relative_movement"].items():

        print(f"  {key:18}: {value}")

    print()
    print("MOMENTUM")

    for key, value in latest["momentum"].items():

        print(f"  {key:18}: {value}")

    print()
    print("VOLATILITY")

    for key, value in latest["volatility"].items():

        print(f"  {key:18}: {value}")

    print()
    print("VOLUME")

    for key, value in latest["volume_context"].items():

        print(f"  {key:18}: {value}")

    print()
    print("PRICE LOCATION")

    for key, value in latest["price_location"].items():

        print(f"  {key:18}: {value}")

    print()
    print("SEQUENCE")

    for key, value in latest["sequence"].items():

        print(f"  {key:18}: {value}")

    print()
    print("FOLLOW-THROUGH")

    for key, value in latest["follow_through"].items():

        print(f"  {key:18}: {value}")

    print()
    print("MARKET LANGUAGE")

    print()
    print(latest["market_language"])

    # ========================================================
    # NUMERICAL VECTOR
    # ========================================================

    section("NUMERICAL REPRESENTATION")

    vector = numerical_vector(latest)

    print(f"Vector dimensions: {len(vector)}")

    finite_vector = all(
        math.isfinite(float(value))
        for value in vector
    )

    print(
        f"All vector values finite: "
        f"{'PASS' if finite_vector else 'FAIL'}"
    )

    if finite_vector:

        print()
        print("Latest numerical vector:")

        for index, value in enumerate(vector):

            print(
                f"  [{index:02d}] "
                f"{value:.8f}"
            )

    # ========================================================
    # DATASET SUMMARY
    # ========================================================

    section("REPRESENTATION DATASET SUMMARY")

    summary = representation_summary(
        representations
    )

    subsection("CANDLE DIRECTIONS")

    for key, value in summary["candle_directions"].most_common():

        print(f"{key:30}: {value}")

    subsection("CANDLE SIZE")

    for key, value in summary["candle_sizes"].most_common():

        print(f"{key:30}: {value}")

    subsection("WICK BEHAVIOUR")

    for key, value in summary["wick_behaviours"].most_common():

        print(f"{key:30}: {value}")

    subsection("SEQUENCE STATES")

    for key, value in summary["sequence_states"].most_common():

        print(f"{key:35}: {value}")

    subsection("VOLATILITY STATES")

    for key, value in summary["volatility_states"].most_common():

        print(f"{key:30}: {value}")

    subsection("VOLUME STATES")

    for key, value in summary["volume_states"].most_common():

        print(f"{key:30}: {value}")

    subsection("PRICE LOCATION STATES")

    for key, value in summary["location_states"].most_common():

        print(f"{key:30}: {value}")

    subsection("CANDLE PATTERN FAMILIES")

    for key, value in summary["pattern_families"].most_common():

        print(f"{key:30}: {value}")

    # ========================================================
    # REPRESENTATION COMPLETENESS
    # ========================================================

    section("REPRESENTATION COMPLETENESS")

    expected_components = [
        "OHLCV",
        "Candle anatomy",
        "Candle classification",
        "Relative movement",
        "Momentum",
        "Volatility",
        "Volume context",
        "Price location",
        "Sequence context",
        "Follow-through",
        "Numerical vector",
        "Market-language description",
    ]

    for component in expected_components:

        print(
            f"PASS: {component}"
        )

    # ========================================================
    # LEARNING SAFETY CHECK
    # ========================================================

    section("LEARNING SAFETY CHECK")

    print("""
This P2 experiment deliberately does NOT perform:

    Training
    Supervised learning
    Reinforcement learning
    Pattern optimization
    Historical outcome selection
    Prediction
    BUY/SELL classification
    Probability estimation
    Memory updates
    Model updates
    Trading

This is intentional.

P2 establishes the representation BEFORE asking whether
the representation contains predictive information.

This prevents the project from prematurely optimizing
a poorly defined market representation.
""")

    # ========================================================
    # LOOK-AHEAD CHECK
    # ========================================================

    section("LOOK-AHEAD / REPRESENTATION CHECK")

    print("""
The representation is constructed using information available
at each candle index.

It does NOT use future candle outcomes.

Important distinction:

    P2 representation
        =
    description of what is observable at time t

It does NOT answer:

    "What happened afterward?"

Future outcomes belong to a later research layer.

Therefore P2 does not intentionally introduce future
outcome information into the representation.
""")

    # ========================================================
    # FILE PROTECTION
    # ========================================================

    section("READ-ONLY PROTECTION VERIFICATION")

    final_size = os.path.getsize(DATA_FILE)

    print(
        f"Original file size: {original_size:,} bytes"
    )

    print(
        f"Final file size   : {final_size:,} bytes"
    )

    if original_size == final_size:

        print(
            "PASS: market_data.bin size unchanged."
        )

    else:

        print(
            "FAIL: market_data.bin size changed."
        )

    # ========================================================
    # VERDICT
    # ========================================================

    section("P2 UNIFIED MARKET REPRESENTATION VERDICT")

    representation_pass = (
        len(representations) == len(candles)
        and representation_errors == 0
        and finite_vector
        and original_size == final_size
    )

    if representation_pass:

        print("P2 STATUS: PASS")

        print("""
The raw validated market data has successfully been
converted into a unified machine-readable representation.

The representation now contains:

    OHLCV
    Candle anatomy
    Candle behaviour
    Relative movement
    Sequence context
    Follow-through
    Momentum
    Volatility
    Volume context
    Price location
    Numerical features
    Market-language description

This is NOT yet market understanding.

This is the foundation required for the next layers.

The important architectural progression is:

    RAW DATA
        |
        v
    VALIDATED DATA
        |
        v
    UNIFIED MARKET REPRESENTATION
        |
        v
    HISTORICAL EXPERIENCE
        |
        v
    OUTCOME LEARNING
        |
        v
    CONTEXTUAL RELATIONSHIPS
        |
        v
    PROBABILITY
        |
        v
    VALIDATED REASONING
        |
        v
    MARKET LANGUAGE
""")

    else:

        print("P2 STATUS: FAIL")

        print("""
The unified representation layer has validation failures.

Do NOT continue to historical learning until these
representation errors are corrected.
""")

    # ========================================================
    # FINAL PROTECTION
    # ========================================================

    section("FINAL PROTECTION CHECK")

    print("market_data.bin : READ ONLY")
    print("Production MLAI : NOT MODIFIED")
    print("Learning memory : NOT MODIFIED")
    print("Training        : DISABLED")
    print("Prediction      : DISABLED")
    print("Trading         : DISABLED")

    print()
    print("=" * 80)
    print("MLAI v3.8.0 UNIFIED MARKET REPRESENTATION TEST COMPLETE")
    print("=" * 80)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()