
import os
import pickle
import math
from collections import Counter


# ============================================================
# MLAI v3.6.0
# COMPLETE MARKET ANALYSIS DIAGNOSTIC
#
# FILE:
#     mlai_v3.6_market_analysis_test.py
#
# PURPOSE
# ------------------------------------------------------------
# This is a diagnostic market-analysis experiment.
#
# It reads:
#
#     market_data.bin
#
# It analyzes:
#
#     1. OHLC
#     2. Candle direction
#     3. Candle body
#     4. Upper wick
#     5. Lower wick
#     6. Candle range
#     7. Body/range ratio
#     8. ATR
#     9. Volatility
#    10. Moving averages
#    11. Momentum
#    12. RSI
#    13. MACD
#    14. Volume
#    15. Volume trend
#    16. Swing highs
#    17. Swing lows
#    18. HH
#    19. HL
#    20. LH
#    21. LL
#    22. Equal highs
#    23. Equal lows
#    24. BOS
#    25. CHoCH
#    26. Support
#    27. Resistance
#    28. Support/resistance clustering
#    29. Distance to support
#    30. Distance to resistance
#    31. Price location
#    32. Breakout status
#    33. Rejection status
#    34. Trend
#    35. Market structure
#    36. Structure score
#    37. Structural quality
#    38. Volatility regime
#    39. Momentum state
#    40. Market regime
#    41. Data integrity
#
# IMPORTANT
# ------------------------------------------------------------
# This program is DESCRIPTIVE.
#
# It does NOT:
#
#     - modify market_data.bin
#     - modify mlai_v31.py
#     - modify production models
#     - modify learning memory
#     - train a production model
#     - place trades
#
# It does NOT claim that any indicator predicts the future.
#
# Swing detection is retrospective because a swing requires
# candles after the candidate candle.
#
# ============================================================


# ============================================================
# CONFIGURATION
# ============================================================

MARKET_FILE = "market_data.bin"

SWING_LOOKBACK = 3

MIN_CANDLES = 100

RECENT_CANDLES = 100

MAX_SWINGS_TO_PRINT = 40

MAX_EVENTS_TO_PRINT = 40

MAX_LEVELS_TO_PRINT = 10

ATR_PERIOD = 14

RSI_PERIOD = 14

FAST_EMA_PERIOD = 12

SLOW_EMA_PERIOD = 26

MACD_SIGNAL_PERIOD = 9

SHORT_MA_PERIOD = 20

MEDIUM_MA_PERIOD = 50

LONG_MA_PERIOD = 200

MIN_STRUCTURE_MOVE = 0.0002

SUPPORT_RESISTANCE_TOLERANCE = 0.0015

MIN_LEVEL_TOUCHES = 2

RECENT_RANGE_PERIOD = 50

VOLUME_PERIOD = 20


# ============================================================
# HEADER
# ============================================================

print("=" * 80)
print("MLAI v3.6.0 COMPLETE MARKET ANALYSIS TEST")
print("=" * 80)

print(
    """
PURPOSE
-------

This experiment performs a comprehensive diagnostic analysis
of raw OHLC market data.

It analyzes:

    OHLC
    Candle behaviour
    Volatility
    ATR
    Moving averages
    Momentum
    RSI
    MACD
    Volume
    Swing structure
    HH / HL / LH / LL
    BOS
    CHoCH
    Support
    Resistance
    Price location
    Breakout / rejection behaviour
    Trend
    Market regime
    Data integrity

This is a diagnostic experiment only.

market_data.bin        = READ ONLY
Production MLAI        = NOT MODIFIED
Learning memory        = NOT MODIFIED
Trading                = NOT PERFORMED

No output in this program should be interpreted as a
guaranteed prediction of future price movement.
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
print(
    "Data type:",
    type(market_data).__name__
)


if not isinstance(market_data, dict):

    raise ValueError(
        "Unexpected market_data.bin structure. "
        "Expected a dictionary."
    )


candles = market_data.get(
    "candles",
    []
)


print(
    "Total candles:",
    len(candles)
)


if len(candles) < MIN_CANDLES:

    raise ValueError(
        f"Not enough candles. "
        f"Required at least {MIN_CANDLES}, "
        f"found {len(candles)}."
    )


# ============================================================
# CANDLE NORMALIZATION
# ============================================================

def normalize_candle(candle, index):

    timestamp = None
    open_price = None
    high = None
    low = None
    close = None
    volume = None

    if isinstance(candle, dict):

        timestamp = (
            candle.get("timestamp")
            or candle.get("time")
            or candle.get("datetime")
            or candle.get("date")
        )

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

        if volume is not None:

            volume = float(volume)

    except (TypeError, ValueError):

        return None

    if (
        not math.isfinite(open_price)
        or not math.isfinite(high)
        or not math.isfinite(low)
        or not math.isfinite(close)
    ):

        return None

    if volume is not None and not math.isfinite(volume):

        volume = None

    if (
        high < low
        or high < open_price
        or high < close
        or low > open_price
        or low > close
    ):

        return None

    return {

        "index": index,

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

invalid_candles = 0

for index, candle in enumerate(candles):

    normalized = normalize_candle(
        candle,
        index
    )

    if normalized is not None:

        normalized_candles.append(
            normalized
        )

    else:

        invalid_candles += 1


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
    invalid_candles
)

print(
    "PASS: market_data.bin loaded."
)

print(
    "PASS: OHLC data normalized."
)

print(
    "PASS: market_data.bin remains READ ONLY."
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

volumes = [
    candle["volume"]
    for candle in normalized_candles
]


# ============================================================
# BASIC HELPERS
# ============================================================

def mean(values):

    if not values:

        return 0.0

    return sum(values) / len(values)


def percentage_change(start, end):

    if start == 0:

        return 0.0

    return (end / start) - 1.0


def safe_percentage(value):

    return value * 100.0


# ============================================================
# CANDLE ANALYSIS
# ============================================================

def candle_direction(index):

    if closes[index] > opens[index]:

        return "BULLISH"

    if closes[index] < opens[index]:

        return "BEARISH"

    return "NEUTRAL"


def candle_range(index):

    return highs[index] - lows[index]


def candle_body(index):

    return abs(
        closes[index] - opens[index]
    )


def upper_wick(index):

    return (
        highs[index]
        - max(
            opens[index],
            closes[index]
        )
    )


def lower_wick(index):

    return (
        min(
            opens[index],
            closes[index]
        )
        - lows[index]
    )


def body_ratio(index):

    rng = candle_range(index)

    if rng == 0:

        return 0.0

    return candle_body(index) / rng


def candle_strength(index):

    ratio = body_ratio(index)

    if ratio >= 0.70:

        return "STRONG_BODY"

    if ratio >= 0.40:

        return "MODERATE_BODY"

    if ratio >= 0.20:

        return "SMALL_BODY"

    return "DOJI_LIKE"


# ============================================================
# TRUE RANGE / ATR
# ============================================================

def true_range(index):

    if index <= 0:

        return highs[index] - lows[index]

    previous_close = closes[index - 1]

    return max(

        highs[index] - lows[index],

        abs(
            highs[index]
            - previous_close
        ),

        abs(
            lows[index]
            - previous_close
        ),
    )


def calculate_atr(
    index,
    period=ATR_PERIOD
):

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
# EMA
# ============================================================

def calculate_ema_series(
    values,
    period
):

    if not values:

        return []

    multiplier = 2.0 / (period + 1.0)

    ema = [values[0]]

    for value in values[1:]:

        next_value = (
            (value - ema[-1])
            * multiplier
            + ema[-1]
        )

        ema.append(next_value)

    return ema


# ============================================================
# MOVING AVERAGES
# ============================================================

ema_fast = calculate_ema_series(
    closes,
    FAST_EMA_PERIOD
)

ema_slow = calculate_ema_series(
    closes,
    SLOW_EMA_PERIOD
)

ema_signal_source = [

    ema_fast[i] - ema_slow[i]

    for i in range(
        len(closes)
    )
]

macd_signal = calculate_ema_series(
    ema_signal_source,
    MACD_SIGNAL_PERIOD
)


def simple_moving_average(
    values,
    period
):

    if len(values) < period:

        return mean(values)

    return mean(
        values[-period:]
    )


# ============================================================
# RSI
# ============================================================

def calculate_rsi(
    index,
    period=RSI_PERIOD
):

    if index <= 0:

        return 50.0

    start = max(
        1,
        index - period + 1
    )

    gains = []
    losses = []

    for i in range(
        start,
        index + 1
    ):

        change = (
            closes[i]
            - closes[i - 1]
        )

        if change > 0:

            gains.append(change)
            losses.append(0.0)

        else:

            gains.append(0.0)
            losses.append(abs(change))

    average_gain = mean(gains)
    average_loss = mean(losses)

    if average_loss == 0:

        if average_gain == 0:

            return 50.0

        return 100.0

    rs = (
        average_gain
        / average_loss
    )

    return 100.0 - (
        100.0
        / (1.0 + rs)
    )


# ============================================================
# MOMENTUM
# ============================================================

def calculate_momentum(
    index,
    period=14
):

    if index < period:

        return 0.0

    return percentage_change(
        closes[index - period],
        closes[index]
    )


# ============================================================
# SWING HIGH DETECTION
# ============================================================

def detect_swing_highs(
    lookback=SWING_LOOKBACK
):

    swings = []

    start = lookback

    end = (
        len(normalized_candles)
        - lookback
    )

    for index in range(
        start,
        end
    ):

        current_high = highs[index]

        left_highs = highs[
            index - lookback:
            index
        ]

        right_highs = highs[
            index + 1:
            index + lookback + 1
        ]

        if (
            current_high >= max(left_highs)
            and
            current_high >= max(right_highs)
        ):

            swings.append({

                "type":
                    "SWING_HIGH",

                "index":
                    index,

                "price":
                    current_high,

                "timestamp":
                    normalized_candles[
                        index
                    ]["timestamp"],

                "original_index":
                    normalized_candles[
                        index
                    ]["index"],
            })

    return swings


# ============================================================
# SWING LOW DETECTION
# ============================================================

def detect_swing_lows(
    lookback=SWING_LOOKBACK
):

    swings = []

    start = lookback

    end = (
        len(normalized_candles)
        - lookback
    )

    for index in range(
        start,
        end
    ):

        current_low = lows[index]

        left_lows = lows[
            index - lookback:
            index
        ]

        right_lows = lows[
            index + 1:
            index + lookback + 1
        ]

        if (
            current_low <= min(left_lows)
            and
            current_low <= min(right_lows)
        ):

            swings.append({

                "type":
                    "SWING_LOW",

                "index":
                    index,

                "price":
                    current_low,

                "timestamp":
                    normalized_candles[
                        index
                    ]["timestamp"],

                "original_index":
                    normalized_candles[
                        index
                    ]["index"],
            })

    return swings


# ============================================================
# DETECT SWINGS
# ============================================================

swing_highs = detect_swing_highs()

swing_lows = detect_swing_lows()


print()
print("=" * 80)
print("RAW SWING DETECTION")
print("=" * 80)

print(
    "Raw swing highs:",
    len(swing_highs)
)

print(
    "Raw swing lows:",
    len(swing_lows)
)


# ============================================================
# COMBINE SWINGS
# ============================================================

all_swings = (
    swing_highs
    + swing_lows
)

all_swings.sort(
    key=lambda x: x["index"]
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

        if (
            previous["type"]
            != swing["type"]
        ):

            cleaned.append(swing)

            continue

        if swing["type"] == "SWING_HIGH":

            if (
                swing["price"]
                >= previous["price"]
            ):

                cleaned[-1] = swing

        else:

            if (
                swing["price"]
                <= previous["price"]
            ):

                cleaned[-1] = swing

    return cleaned


all_swings = clean_swings(
    all_swings
)


print()
print("=" * 80)
print("SWING DETECTION")
print("=" * 80)

print(
    "Swing highs:",
    len([
        s for s in all_swings
        if s["type"] == "SWING_HIGH"
    ])
)

print(
    "Swing lows:",
    len([
        s for s in all_swings
        if s["type"] == "SWING_LOW"
    ])
)

print(
    "Total cleaned swings:",
    len(all_swings)
)


# ============================================================
# CLASSIFY HH HL LH LL
# ============================================================

def classify_swings(swings):

    classified = []

    previous_high = None

    previous_low = None

    for swing in swings:

        item = dict(swing)

        if (
            swing["type"]
            == "SWING_HIGH"
        ):

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

            previous_high = swing

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

            previous_low = swing

        classified.append(item)

    return classified


classified_swings = classify_swings(
    all_swings
)


# ============================================================
# PRINT MARKET STRUCTURE
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
        structure_counts.get(
            name,
            0
        )
    )


# ============================================================
# STRUCTURE SCORE
# ============================================================

def calculate_structure_score(
    swings
):

    bullish_points = 0

    bearish_points = 0

    for swing in swings:

        structure = swing[
            "structure"
        ]

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

    if score >= 0.25:

        direction = "BULLISH"

    elif score <= -0.25:

        direction = "BEARISH"

    else:

        direction = "RANGE / MIXED"

    return {

        "bullish":
            bullish_points,

        "bearish":
            bearish_points,

        "score":
            score,

        "direction":
            direction,
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
# BOS / CHoCH
# ============================================================

def detect_structure_events(
    candles,
    swings
):

    events = []

    last_swing_high = None

    last_swing_low = None

    current_bias = "UNKNOWN"

    for index, candle in enumerate(candles):

        for swing in swings:

            if swing["index"] != index:

                continue

            if (
                swing["type"]
                == "SWING_HIGH"
            ):

                last_swing_high = swing

            elif (
                swing["type"]
                == "SWING_LOW"
            ):

                last_swing_low = swing

        close = candle["close"]

        if (
            last_swing_high is not None
            and index
            > last_swing_high["index"]
            and close
            > last_swing_high["price"]
        ):

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

                "swing_index":
                    last_swing_high["index"],
            })

            current_bias = "BULLISH"

            last_swing_high = None

        elif (
            last_swing_low is not None
            and index
            > last_swing_low["index"]
            and close
            < last_swing_low["price"]
        ):

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

                "swing_index":
                    last_swing_low["index"],
            })

            current_bias = "BEARISH"

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
            f"SwingIndex={event['swing_index']:>6} | "
            f"Time={event['timestamp']}"

        )


# ============================================================
# SUPPORT / RESISTANCE LEVEL DETECTION
# ============================================================

def cluster_levels(
    prices,
    tolerance=SUPPORT_RESISTANCE_TOLERANCE
):

    if not prices:

        return []

    clusters = []

    for price in sorted(prices):

        matched = None

        for cluster in clusters:

            reference = cluster[
                "price"
            ]

            if reference == 0:

                continue

            difference = abs(
                price - reference
            ) / reference

            if difference <= tolerance:

                matched = cluster

                break

        if matched is None:

            clusters.append({

                "price":
                    price,

                "touches":
                    1,

                "prices":
                    [price],
            })

        else:

            matched["prices"].append(
                price
            )

            matched["touches"] += 1

            matched["price"] = mean(
                matched["prices"]
            )

    return clusters


swing_high_prices = [

    swing["price"]

    for swing in classified_swings

    if swing["type"]
    == "SWING_HIGH"
]


swing_low_prices = [

    swing["price"]

    for swing in classified_swings

    if swing["type"]
    == "SWING_LOW"
]


resistance_clusters = cluster_levels(
    swing_high_prices
)

support_clusters = cluster_levels(
    swing_low_prices
)


support_levels = [

    level

    for level in support_clusters

    if level["touches"]
    >= MIN_LEVEL_TOUCHES
]


resistance_levels = [

    level

    for level in resistance_clusters

    if level["touches"]
    >= MIN_LEVEL_TOUCHES
]


# ============================================================
# SUPPORT / RESISTANCE REPORT
# ============================================================

latest_close = closes[-1]


support_levels_below = [

    level

    for level in support_levels

    if level["price"] <= latest_close
]


resistance_levels_above = [

    level

    for level in resistance_levels

    if level["price"] >= latest_close
]


support_levels_below.sort(
    key=lambda x: latest_close - x["price"]
)


resistance_levels_above.sort(
    key=lambda x: x["price"] - latest_close
)


print()
print("=" * 80)
print("SUPPORT LEVELS")
print("=" * 80)

if not support_levels_below:

    print(
        "No confirmed support cluster below current price."
    )

else:

    for level in support_levels_below[
        :MAX_LEVELS_TO_PRINT
    ]:

        distance = percentage_change(
            latest_close,
            level["price"]
        )

        print(

            f"Support={level['price']:.5f} | "
            f"Touches={level['touches']} | "
            f"Distance={distance:+.3%}"

        )


print()
print("=" * 80)
print("RESISTANCE LEVELS")
print("=" * 80)

if not resistance_levels_above:

    print(
        "No confirmed resistance cluster above current price."
    )

else:

    for level in resistance_levels_above[
        :MAX_LEVELS_TO_PRINT
    ]:

        distance = percentage_change(
            latest_close,
            level["price"]
        )

        print(

            f"Resistance={level['price']:.5f} | "
            f"Touches={level['touches']} | "
            f"Distance={distance:+.3%}"

        )


# ============================================================
# NEAREST SUPPORT / RESISTANCE
# ============================================================

nearest_support = None

nearest_resistance = None


if support_levels_below:

    nearest_support = (
        support_levels_below[0]
    )


if resistance_levels_above:

    nearest_resistance = (
        resistance_levels_above[0]
    )


print()
print("=" * 80)
print("NEAREST SUPPORT / RESISTANCE")
print("=" * 80)

if nearest_support:

    print(
        f"Nearest support: "
        f"{nearest_support['price']:.5f} "
        f"({nearest_support['touches']} touches)"
    )

else:

    print(
        "Nearest support: NONE"
    )


if nearest_resistance:

    print(
        f"Nearest resistance: "
        f"{nearest_resistance['price']:.5f} "
        f"({nearest_resistance['touches']} touches)"
    )

else:

    print(
        "Nearest resistance: NONE"
    )


# ============================================================
# PRICE LOCATION
# ============================================================

recent_range_start = max(
    0,
    len(closes) - RECENT_RANGE_PERIOD
)

recent_high = max(
    highs[recent_range_start:]
)

recent_low = min(
    lows[recent_range_start:]
)

recent_range = (
    recent_high
    - recent_low
)


if recent_range > 0:

    price_location = (
        latest_close
        - recent_low
    ) / recent_range

else:

    price_location = 0.5


if price_location >= 0.80:

    price_location_state = "NEAR_RANGE_HIGH"

elif price_location <= 0.20:

    price_location_state = "NEAR_RANGE_LOW"

else:

    price_location_state = "MID_RANGE"


print()
print("=" * 80)
print("PRICE LOCATION")
print("=" * 80)

print(
    f"Recent range high: {recent_high:.5f}"
)

print(
    f"Recent range low : {recent_low:.5f}"
)

print(
    f"Price location: {price_location:.2%}"
)

print(
    "Location state:",
    price_location_state
)


# ============================================================
# CURRENT CANDLE ANALYSIS
# ============================================================

latest_index = len(closes) - 1

latest_open = opens[latest_index]

latest_high = highs[latest_index]

latest_low = lows[latest_index]

latest_atr = calculate_atr(
    latest_index
)

latest_body = candle_body(
    latest_index
)

latest_upper_wick = upper_wick(
    latest_index
)

latest_lower_wick = lower_wick(
    latest_index
)

latest_range = candle_range(
    latest_index
)

latest_body_ratio = body_ratio(
    latest_index
)

latest_direction = candle_direction(
    latest_index
)

latest_strength = candle_strength(
    latest_index
)


print()
print("=" * 80)
print("LATEST OHLC / CANDLE")
print("=" * 80)

print(
    f"Open : {latest_open:.5f}"
)

print(
    f"High : {latest_high:.5f}"
)

print(
    f"Low  : {latest_low:.5f}"
)

print(
    f"Close: {latest_close:.5f}"
)

print(
    f"Direction: {latest_direction}"
)

print(
    f"Range: {latest_range:.5f}"
)

print(
    f"Body: {latest_body:.5f}"
)

print(
    f"Upper wick: {latest_upper_wick:.5f}"
)

print(
    f"Lower wick: {latest_lower_wick:.5f}"
)

print(
    f"Body/range ratio: "
    f"{latest_body_ratio:.2%}"
)

print(
    "Candle strength:",
    latest_strength
)


# ============================================================
# VOLATILITY
# ============================================================

atr_previous = calculate_atr(
    max(0, latest_index - 1)
)

if atr_previous > 0:

    volatility_change = (
        latest_atr
        / atr_previous
    ) - 1.0

else:

    volatility_change = 0.0


if latest_atr > mean([
    calculate_atr(i)
    for i in range(
        max(0, latest_index - 49),
        latest_index + 1
    )
]) * 1.25:

    volatility_regime = "HIGH_VOLATILITY"

elif latest_atr < mean([
    calculate_atr(i)
    for i in range(
        max(0, latest_index - 49),
        latest_index + 1
    )
]) * 0.75:

    volatility_regime = "LOW_VOLATILITY"

else:

    volatility_regime = "NORMAL_VOLATILITY"


print()
print("=" * 80)
print("VOLATILITY")
print("=" * 80)

print(
    f"ATR({ATR_PERIOD}): "
    f"{latest_atr:.5f}"
)

print(
    f"ATR change: "
    f"{volatility_change:+.2%}"
)

print(
    "Volatility regime:",
    volatility_regime
)


# ============================================================
# MOVING AVERAGES
# ============================================================

ma20 = simple_moving_average(
    closes,
    SHORT_MA_PERIOD
)

ma50 = simple_moving_average(
    closes,
    MEDIUM_MA_PERIOD
)

ma200 = simple_moving_average(
    closes,
    LONG_MA_PERIOD
)


print()
print("=" * 80)
print("MOVING AVERAGES")
print("=" * 80)

print(
    f"MA{SHORT_MA_PERIOD}: "
    f"{ma20:.5f}"
)

print(
    f"MA{MEDIUM_MA_PERIOD}: "
    f"{ma50:.5f}"
)

print(
    f"MA{LONG_MA_PERIOD}: "
    f"{ma200:.5f}"
)

if (
    latest_close > ma20
    and ma20 > ma50
):

    moving_average_bias = "BULLISH"

elif (
    latest_close < ma20
    and ma20 < ma50
):

    moving_average_bias = "BEARISH"

else:

    moving_average_bias = "MIXED"


print(
    "Moving-average bias:",
    moving_average_bias
)


# ============================================================
# RSI
# ============================================================

latest_rsi = calculate_rsi(
    latest_index
)


if latest_rsi >= 70:

    rsi_state = "OVERBOUGHT"

elif latest_rsi <= 30:

    rsi_state = "OVERSOLD"

elif latest_rsi >= 55:

    rsi_state = "BULLISH_MOMENTUM"

elif latest_rsi <= 45:

    rsi_state = "BEARISH_MOMENTUM"

else:

    rsi_state = "NEUTRAL"


print()
print("=" * 80)
print("RSI")
print("=" * 80)

print(
    f"RSI({RSI_PERIOD}): "
    f"{latest_rsi:.2f}"
)

print(
    "RSI state:",
    rsi_state
)


# ============================================================
# MACD
# ============================================================

latest_macd = ema_signal_source[-1]

latest_macd_signal = macd_signal[-1]

latest_macd_histogram = (
    latest_macd
    - latest_macd_signal
)


if latest_macd_histogram > 0:

    macd_state = "BULLISH"

elif latest_macd_histogram < 0:

    macd_state = "BEARISH"

else:

    macd_state = "NEUTRAL"


print()
print("=" * 80)
print("MACD")
print("=" * 80)

print(
    f"MACD: {latest_macd:.5f}"
)

print(
    f"Signal: {latest_macd_signal:.5f}"
)

print(
    f"Histogram: "
    f"{latest_macd_histogram:.5f}"
)

print(
    "MACD state:",
    macd_state
)


# ============================================================
# MOMENTUM
# ============================================================

latest_momentum = calculate_momentum(
    latest_index
)


if latest_momentum > 0.01:

    momentum_state = "STRONG_BULLISH"

elif latest_momentum > 0:

    momentum_state = "BULLISH"

elif latest_momentum < -0.01:

    momentum_state = "STRONG_BEARISH"

elif latest_momentum < 0:

    momentum_state = "BEARISH"

else:

    momentum_state = "NEUTRAL"


print()
print("=" * 80)
print("MOMENTUM")
print("=" * 80)

print(
    f"Momentum({RSI_PERIOD}): "
    f"{latest_momentum:+.3%}"
)

print(
    "Momentum state:",
    momentum_state
)


# ============================================================
# VOLUME ANALYSIS
# ============================================================

valid_volumes = [

    volume

    for volume in volumes

    if volume is not None
]


print()
print("=" * 80)
print("VOLUME")
print("=" * 80)

if not valid_volumes:

    volume_state = "UNAVAILABLE"

    print(
        "Volume data: NOT AVAILABLE"
    )

else:

    latest_volume = volumes[-1]

    recent_volume_values = [

        volume

        for volume in volumes[
            -VOLUME_PERIOD:
        ]

        if volume is not None
    ]

    average_volume = mean(
        recent_volume_values
    )

    if average_volume > 0:

        volume_ratio = (
            latest_volume
            / average_volume
        )

    else:

        volume_ratio = 1.0

    if volume_ratio >= 1.5:

        volume_state = "HIGH_VOLUME"

    elif volume_ratio <= 0.5:

        volume_state = "LOW_VOLUME"

    else:

        volume_state = "NORMAL_VOLUME"

    print(
        f"Latest volume: "
        f"{latest_volume:.2f}"
    )

    print(
        f"Average volume: "
        f"{average_volume:.2f}"
    )

    print(
        f"Volume ratio: "
        f"{volume_ratio:.2f}x"
    )

    print(
        "Volume state:",
        volume_state
    )


# ============================================================
# BREAKOUT / REJECTION STATUS
# ============================================================

breakout_status = "NO_CONFIRMED_BREAKOUT"

if nearest_resistance:

    resistance_price = (
        nearest_resistance["price"]
    )

    if latest_close > resistance_price:

        breakout_status = (
            "ABOVE_RESISTANCE"
        )

    elif (
        latest_high > resistance_price
        and latest_close < resistance_price
    ):

        breakout_status = (
            "RESISTANCE_REJECTION"
        )


if nearest_support:

    support_price = (
        nearest_support["price"]
    )

    if latest_close < support_price:

        breakout_status = (
            "BELOW_SUPPORT"
        )

    elif (
        latest_low < support_price
        and latest_close > support_price
    ):

        breakout_status = (
            "SUPPORT_REJECTION"
        )


print()
print("=" * 80)
print("SUPPORT / RESISTANCE BEHAVIOUR")
print("=" * 80)

print(
    "Current S/R status:",
    breakout_status
)


# ============================================================
# CURRENT STRUCTURAL HIGH / LOW
# ============================================================

previous_structural_high = None

previous_structural_low = None

for swing in reversed(
    classified_swings
):

    if (
        previous_structural_high is None
        and swing["type"]
        == "SWING_HIGH"
    ):

        previous_structural_high = swing

    if (
        previous_structural_low is None
        and swing["type"]
        == "SWING_LOW"
    ):

        previous_structural_low = swing

    if (
        previous_structural_high is not None
        and previous_structural_low is not None
    ):

        break


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

    if swing["index"]
    >= recent_start
]


recent_events = [

    event

    for event in structure_events

    if event["index"]
    >= recent_start
]


recent_structure_score = (
    calculate_structure_score(
        recent_swings
    )
)


# ============================================================
# STRUCTURE QUALITY
# ============================================================

def calculate_structure_quality(
    swings,
    events
):

    if not swings:

        return 0.0

    directional_swings = [

        swing

        for swing in swings

        if swing["structure"]
        in (
            "HH",
            "HL",
            "LH",
            "LL"
        )
    ]

    if not directional_swings:

        return 0.0

    structure_consistency = (
        len(directional_swings)
        / len(swings)
    )

    event_factor = min(
        len(events),
        5
    ) / 5.0

    quality = (
        structure_consistency
        * 0.75
        +
        event_factor
        * 0.25
    )

    return min(
        1.0,
        max(
            0.0,
            quality
        )
    )


structure_quality = (
    calculate_structure_quality(
        recent_swings,
        recent_events
    )
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

    if (
        bullish >= 2
        and bullish > bearish
    ):

        return "UPTREND"

    if (
        bearish >= 2
        and bearish > bullish
    ):

        return "DOWNTREND"

    return "RANGE / TRANSITION"


trend_classification = classify_trend(
    recent_swings
)


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

    if latest_event:

        event_type = latest_event[
            "type"
        ]

        if event_type == "CHoCH_BULLISH":

            return "CURRENT_CANDLE_CHOCH_BULLISH"

        if event_type == "CHoCH_BEARISH":

            return "CURRENT_CANDLE_CHOCH_BEARISH"

        if event_type == "BOS_BULLISH":

            return "CURRENT_CANDLE_BOS_BULLISH"

        if event_type == "BOS_BEARISH":

            return "CURRENT_CANDLE_BOS_BEARISH"

    if (
        structural_high
        and latest_close
        > structural_high["price"]
    ):

        return "ABOVE_LAST_STRUCTURAL_HIGH"

    if (
        structural_low
        and latest_close
        < structural_low["price"]
    ):

        return "BELOW_LAST_STRUCTURAL_LOW"

    direction = (
        structure_score["direction"]
    )

    if direction == "BULLISH":

        return "BULLISH_STRUCTURE"

    if direction == "BEARISH":

        return "BEARISH_STRUCTURE"

    if direction == "RANGE / MIXED":

        return "RANGE / MIXED"

    return "UNKNOWN"


latest_event = (
    structure_events[-1]
    if structure_events
    else None
)


current_state = determine_current_state(

    recent_structure_score,

    latest_close,

    previous_structural_high,

    previous_structural_low,

    latest_event
)


# ============================================================
# MARKET REGIME
# ============================================================

if (
    trend_classification == "UPTREND"
    and volatility_regime
    == "HIGH_VOLATILITY"
):

    market_regime = "BULLISH_HIGH_VOLATILITY"

elif (
    trend_classification == "DOWNTREND"
    and volatility_regime
    == "HIGH_VOLATILITY"
):

    market_regime = "BEARISH_HIGH_VOLATILITY"

elif trend_classification == "UPTREND":

    market_regime = "BULLISH_TREND"

elif trend_classification == "DOWNTREND":

    market_regime = "BEARISH_TREND"

elif volatility_regime == "LOW_VOLATILITY":

    market_regime = "LOW_VOLATILITY_RANGE"

else:

    market_regime = "RANGE_TRANSITION"


# ============================================================
# FINAL MARKET SNAPSHOT
# ============================================================

print()
print("=" * 80)
print("COMPLETE MARKET SNAPSHOT")
print("=" * 80)

print(
    f"Latest timestamp: "
    f"{normalized_candles[-1]['timestamp']}"
)

print(
    f"Latest close: "
    f"{latest_close:.5f}"
)

print(
    f"Trend: "
    f"{trend_classification}"
)

print(
    f"Structure: "
    f"{recent_structure_score['direction']}"
)

print(
    f"Current state: "
    f"{current_state}"
)

print(
    f"Market regime: "
    f"{market_regime}"
)

print(
    f"Structure score: "
    f"{recent_structure_score['score']:+.3f}"
)

print(
    f"Structural quality: "
    f"{structure_quality:.2%}"
)

print(
    f"ATR: "
    f"{latest_atr:.5f}"
)

print(
    f"RSI: "
    f"{latest_rsi:.2f}"
)

print(
    f"MACD: "
    f"{latest_macd:.5f}"
)

print(
    f"Momentum: "
    f"{latest_momentum:+.3%}"
)

print(
    f"MA bias: "
    f"{moving_average_bias}"
)

print(
    f"Volatility: "
    f"{volatility_regime}"
)

print(
    f"Price location: "
    f"{price_location_state}"
)

print(
    f"S/R status: "
    f"{breakout_status}"
)

if nearest_support:

    print(
        f"Nearest support: "
        f"{nearest_support['price']:.5f}"
    )

else:

    print(
        "Nearest support: NONE"
    )

if nearest_resistance:

    print(
        f"Nearest resistance: "
        f"{nearest_resistance['price']:.5f}"
    )

else:

    print(
        "Nearest resistance: NONE"
    )


# ============================================================
# LATEST STRUCTURE EVENT
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
        latest_event["swing_index"]
    )

    print(
        "Event timestamp:",
        latest_event["timestamp"]
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
    "Recent BOS / CHoCH:",
    len(recent_events)
)

print(
    "Recent bullish points:",
    recent_structure_score[
        "bullish"
    ]
)

print(
    "Recent bearish points:",
    recent_structure_score[
        "bearish"
    ]
)

print(
    f"Recent structure score: "
    f"{recent_structure_score['score']:+.3f}"
)

print(
    "Recent direction:",
    recent_structure_score[
        "direction"
    ]
)


# ============================================================
# DATA INTEGRITY
# ============================================================

print()
print("=" * 80)
print("DATA INTEGRITY CHECK")
print("=" * 80)

timestamp_order_pass = True

previous_timestamp = None

for candle in normalized_candles:

    timestamp = candle[
        "timestamp"
    ]

    if (
        timestamp is not None
        and previous_timestamp is not None
    ):

        try:

            if timestamp < previous_timestamp:

                timestamp_order_pass = False

                break

        except TypeError:

            pass

    previous_timestamp = timestamp


print(
    "Timestamp order:",
    "PASS"
    if timestamp_order_pass
    else "FAIL"
)


ohlc_integrity_pass = True

for candle in normalized_candles:

    if not (
        candle["high"]
        >= candle["open"]
        >= candle["low"]
    ):

        ohlc_integrity_pass = False

        break

    if not (
        candle["high"]
        >= candle["close"]
        >= candle["low"]
    ):

        ohlc_integrity_pass = False

        break


print(
    "OHLC integrity:",
    "PASS"
    if ohlc_integrity_pass
    else "FAIL"
)


finite_price_pass = all(

    math.isfinite(value)

    for value in (
        opens
        + highs
        + lows
        + closes
    )
)


print(
    "Finite prices:",
    "PASS"
    if finite_price_pass
    else "FAIL"
)


print(
    "Invalid candles:",
    invalid_candles
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

It reads historical OHLC data and calculates market
characteristics from that data.

It does NOT prove that any indicator predicts the future.

Included analysis:

    OHLC
    Candle anatomy
    Candle direction
    Body
    Upper wick
    Lower wick
    Candle range
    Body/range ratio

    ATR
    Volatility regime

    MA20
    MA50
    MA200

    RSI
    MACD
    Momentum

    Volume
    Volume ratio

    Swing highs
    Swing lows

    HH
    HL
    LH
    LL
    Equal highs
    Equal lows

    BOS
    CHoCH

    Support
    Resistance
    Support clusters
    Resistance clusters
    Distance to S/R

    Recent range
    Price location
    Breakout status
    Rejection status

    Trend
    Structure direction
    Structure score
    Structural quality
    Current structure state
    Market regime

IMPORTANT:

Swing detection is retrospective.

A swing requires candles AFTER the candidate candle.
Therefore a swing cannot be considered confirmed in
real time until SWING_LOOKBACK future candles exist.

Therefore this diagnostic must NOT be treated as a
live trading signal.

Also:

Structural quality is NOT prediction confidence.

RSI is NOT prediction confidence.

MACD is NOT prediction confidence.

Trend classification is NOT prediction confidence.

Support/resistance detection is NOT a guarantee that
price will react from that level.

The next MLAI experiment should test whether these
features actually contain measurable predictive
information.

Future testing should include:

    1. Future return measurement
    2. BUY outcome definition
    3. SELL outcome definition
    4. Neutral outcome definition
    5. HH/HL predictive testing
    6. LH/LL predictive testing
    7. BOS predictive testing
    8. CHoCH predictive testing
    9. Support/resistance testing
   10. RSI testing
   11. MACD testing
   12. Momentum testing
   13. Volatility testing
   14. Volume testing
   15. Feature combinations
   16. Accuracy
   17. Precision
   18. Recall
   19. Coverage
   20. Baseline comparison
   21. Out-of-sample testing
   22. Walk-forward validation
   23. Look-ahead-bias testing

A visually convincing market pattern must NOT be
considered predictive until it survives statistical
and out-of-sample testing.
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
print("MLAI v3.6.0 COMPLETE MARKET ANALYSIS TEST COMPLETE")
print("=" * 80)
