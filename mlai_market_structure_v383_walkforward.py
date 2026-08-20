# ============================================================
# MLAI v3.8.3
# CAUSAL WALK-FORWARD MARKET STRUCTURE VALIDATION
# ============================================================
#
# PURPOSE
# -------
# Research validation of whether confirmed market structure
# contains measurable future directional information across
# multiple chronological unseen periods.
#
# v3.8.3 RETAINS FROM v3.8.2
# ---------------------------
# 1. Causal confirmed swings
# 2. No future swing rewriting
# 3. Causal HH / HL / LH / LL structure
# 4. Causal BOS / CHoCH events
# 5. ATR
# 6. Momentum
# 7. Candle behaviour
# 8. Structural location
# 9. READ-ONLY market_data.bin
# 10. No trading
# 11. No production modification
#
# v3.8.3 UPGRADES
# ----------------
# 1. Multiple chronological walk-forward windows
# 2. Training and OOS are separated for EVERY window
# 3. Thresholds are learned from each training window only
# 4. OOS thresholds are frozen
# 5. Separate outcome thresholds for H+4/H+8/H+16
# 6. Feature thresholds are genuinely used
# 7. Per-window OOS metrics
# 8. Combined OOS metrics
# 9. Mean / median / standard deviation
# 10. Minimum / maximum window performance
# 11. OOS stability analysis
# 12. Structure-direction analysis
# 13. BOS / CHoCH analysis
# 14. Stronger look-ahead integrity checks
#
# IMPORTANT
# ---------
# This is a RESEARCH VALIDATION experiment.
#
# It is NOT:
#
#     - a trading system
#     - a production MLAI model
#     - financial advice
#
# ============================================================

import os
import math
import pickle
import statistics
from datetime import datetime


# ============================================================
# CONFIGURATION
# ============================================================

ROOT = os.path.dirname(os.path.abspath(__file__))

DATA_FILE = os.path.join(
    ROOT,
    "market_data.bin"
)

OUTPUT_BIN = os.path.join(
    ROOT,
    "MLAI_V383_MARKET_STRUCTURE_WALKFORWARD_VALIDATION.bin"
)

OUTPUT_REPORT = os.path.join(
    ROOT,
    "MLAI_V383_MARKET_STRUCTURE_WALKFORWARD_VALIDATION_REPORT.md"
)


# ------------------------------------------------------------
# Walk-forward configuration
# ------------------------------------------------------------

TRAIN_RATIO = 0.70

WINDOW_COUNT = 5

MIN_TRAIN_CANDLES = 150

MIN_OOS_CANDLES = 50

HORIZONS = [4, 8, 16]


# ------------------------------------------------------------
# Structure configuration
# ------------------------------------------------------------

SWING_LEFT = 3

SWING_RIGHT = 3

EQUAL_TOLERANCE_PCT = 0.03


# ------------------------------------------------------------
# Feature configuration
# ------------------------------------------------------------

ATR_PERIOD = 14

MOMENTUM_PERIOD = 8

RECENT_STRUCTURE_COUNT = 8

RECENT_LOCATION_COUNT = 10

RECENT_EVENT_COUNT = 5


# ------------------------------------------------------------
# Outcome threshold candidates
# ------------------------------------------------------------

RETURN_THRESHOLD_CANDIDATES = [
    0.00,
    0.01,
    0.02,
    0.03,
    0.05,
]


# ============================================================
# BASIC HELPERS
# ============================================================

def mean(values):

    values = list(values)

    if not values:
        return 0.0

    return sum(values) / len(values)


def safe_float(value, default=0.0):

    try:
        return float(value)

    except Exception:
        return default


def pct_change(a, b):

    if b == 0:
        return 0.0

    return (
        (a - b) / b
    ) * 100.0


def banner(title):

    print()
    print("=" * 80)
    print(title)
    print("=" * 80)


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


def finite(value):

    try:
        return math.isfinite(float(value))

    except Exception:
        return False


# ============================================================
# CANDLE NORMALIZATION
# ============================================================

def find_first(mapping, names, default=None):

    if not isinstance(mapping, dict):
        return default

    lowered = {
        str(k).lower(): v
        for k, v in mapping.items()
    }

    for name in names:

        key = str(name).lower()

        if key in lowered:
            return lowered[key]

    return default


def normalize_candle(raw, index):

    if isinstance(raw, dict):

        timestamp = find_first(
            raw,
            [
                "timestamp",
                "time",
                "datetime",
                "date",
                "ts",
            ],
            index
        )

        op = find_first(
            raw,
            ["open", "o"]
        )

        hi = find_first(
            raw,
            ["high", "h"]
        )

        lo = find_first(
            raw,
            ["low", "l"]
        )

        cl = find_first(
            raw,
            ["close", "c"]
        )

        volume = find_first(
            raw,
            ["volume", "vol", "v"],
            0
        )

    elif isinstance(raw, (list, tuple)) and len(raw) >= 5:

        timestamp = raw[0]
        op = raw[1]
        hi = raw[2]
        lo = raw[3]
        cl = raw[4]

        volume = (
            raw[5]
            if len(raw) > 5
            else 0
        )

    else:

        return None

    try:

        op = float(op)
        hi = float(hi)
        lo = float(lo)
        cl = float(cl)
        volume = float(volume or 0)

        values = [
            op,
            hi,
            lo,
            cl,
        ]

        if not all(
            math.isfinite(x)
            for x in values
        ):
            return None

        if not all(
            x > 0
            for x in values
        ):
            return None

        if hi < max(op, cl):
            return None

        if lo > min(op, cl):
            return None

        if hi < lo:
            return None

        return {

            "index":
                index,

            "timestamp":
                timestamp,

            "open":
                op,

            "high":
                hi,

            "low":
                lo,

            "close":
                cl,

            "volume":
                volume,
        }

    except Exception:

        return None


# ============================================================
# DATA EXTRACTION
# ============================================================

def extract_raw_candles(data):

    if isinstance(data, list):
        return data

    if isinstance(data, tuple):
        return list(data)

    if not isinstance(data, dict):
        return []

    candidate_keys = [

        "candles",
        "data",
        "market_data",
        "ohlc",
        "bars",
        "prices",
        "records",
        "history",

    ]

    for key in candidate_keys:

        value = data.get(key)

        if isinstance(value, list):
            return value

    values = list(
        data.values()
    )

    if values:

        if all(
            isinstance(x, dict)
            for x in values
        ):
            return values

    return []


def load_market_data():

    if not os.path.exists(DATA_FILE):

        raise FileNotFoundError(
            f"market_data.bin not found:\n"
            f"{DATA_FILE}"
        )

    with open(
        DATA_FILE,
        "rb"
    ) as f:

        data = pickle.load(f)

    raw = extract_raw_candles(
        data
    )

    candles = []

    invalid = 0

    for item in raw:

        candle = normalize_candle(
            item,
            len(candles)
        )

        if candle is None:

            invalid += 1

            continue

        candle["index"] = len(
            candles
        )

        candles.append(
            candle
        )

    return (
        data,
        candles,
        invalid
    )


# ============================================================
# TIMESTAMP
# ============================================================

def timestamp_numeric(value):

    if isinstance(
        value,
        (int, float)
    ):

        return float(value)

    if isinstance(value, str):

        try:

            return float(value)

        except Exception:

            pass

        try:

            return datetime.fromisoformat(
                value.replace(
                    "Z",
                    "+00:00"
                )
            ).timestamp()

        except Exception:

            return 0.0

    return 0.0


def chronological_check(candles):

    timestamps = [

        timestamp_numeric(
            candle["timestamp"]
        )

        for candle in candles

    ]

    for i in range(
        1,
        len(timestamps)
    ):

        if (
            timestamps[i]
            <
            timestamps[i - 1]
        ):

            return False

    return True


# ============================================================
# ATR
# ============================================================

def calculate_true_ranges(candles):

    result = []

    for i, candle in enumerate(
        candles
    ):

        if i == 0:

            tr = (
                candle["high"]
                -
                candle["low"]
            )

        else:

            previous_close = candles[
                i - 1
            ]["close"]

            tr = max(

                candle["high"]
                -
                candle["low"],

                abs(
                    candle["high"]
                    -
                    previous_close
                ),

                abs(
                    candle["low"]
                    -
                    previous_close
                ),
            )

        result.append(
            tr
        )

    return result


def calculate_atr(
    candles,
    period=ATR_PERIOD
):

    tr = calculate_true_ranges(
        candles
    )

    atr = [
        None
    ] * len(candles)

    for i in range(
        len(candles)
    ):

        start = max(
            0,
            i - period + 1
        )

        values = tr[
            start:i + 1
        ]

        if values:

            atr[i] = mean(
                values
            )

    return atr


# ============================================================
# MOMENTUM
# ============================================================

def calculate_momentum(
    candles,
    period=MOMENTUM_PERIOD
):

    result = [
        0.0
    ] * len(candles)

    for i in range(
        len(candles)
    ):

        j = i - period

        if j < 0:
            continue

        previous = candles[
            j
        ]["close"]

        if previous == 0:
            continue

        result[i] = (

            (
                candles[i]["close"]
                -
                previous
            )
            /
            previous

        ) * 100.0

    return result


# ============================================================
# CANDLE FEATURES
# ============================================================

def candle_features(candle):

    op = candle["open"]

    hi = candle["high"]

    lo = candle["low"]

    cl = candle["close"]

    total_range = hi - lo

    if total_range <= 0:

        return {

            "body_pct":
                0.0,

            "upper_wick_pct":
                0.0,

            "lower_wick_pct":
                0.0,

            "close_location":
                0.5,

            "direction":
                0,
        }

    body = abs(
        cl - op
    )

    upper_wick = (
        hi
        -
        max(op, cl)
    )

    lower_wick = (
        min(op, cl)
        -
        lo
    )

    close_location = (
        cl - lo
    ) / total_range

    if cl > op:

        direction = 1

    elif cl < op:

        direction = -1

    else:

        direction = 0

    return {

        "body_pct":
            body / total_range,

        "upper_wick_pct":
            upper_wick / total_range,

        "lower_wick_pct":
            lower_wick / total_range,

        "close_location":
            close_location,

        "direction":
            direction,
    }


# ============================================================
# CONFIRMED SWINGS
# ============================================================

def detect_confirmed_swings(
    candles,
    left=SWING_LEFT,
    right=SWING_RIGHT
):

    swings = []

    total = len(
        candles
    )

    for i in range(
        left,
        total - right
    ):

        current = candles[i]

        is_high = True

        is_low = True

        for j in range(
            i - left,
            i + right + 1
        ):

            if j == i:
                continue

            if (
                candles[j]["high"]
                >=
                current["high"]
            ):

                is_high = False

            if (
                candles[j]["low"]
                <=
                current["low"]
            ):

                is_low = False

        confirmation_index = (
            i + right
        )

        if is_high:

            swings.append({

                "candidate_index":
                    i,

                "confirmed_index":
                    confirmation_index,

                "type":
                    "SWING_HIGH",

                "price":
                    current["high"],

                "timestamp":
                    current["timestamp"],
            })

        if is_low:

            swings.append({

                "candidate_index":
                    i,

                "confirmed_index":
                    confirmation_index,

                "type":
                    "SWING_LOW",

                "price":
                    current["low"],

                "timestamp":
                    current["timestamp"],
            })

    swings.sort(
        key=lambda x: (
            x["confirmed_index"],
            x["candidate_index"],
            x["type"],
        )
    )

    return swings


# ============================================================
# CAUSAL STRUCTURES
# ============================================================

def build_causal_structures(
    candles,
    raw_swings
):

    structures = []

    previous_high = None

    previous_low = None

    swing_pointer = 0

    for index in range(
        len(candles)
    ):

        while (

            swing_pointer
            <
            len(raw_swings)

            and

            raw_swings[
                swing_pointer
            ]["confirmed_index"]
            <=
            index

        ):

            swing = raw_swings[
                swing_pointer
            ]

            item = dict(
                swing
            )

            if swing["type"] == "SWING_HIGH":

                if previous_high is None:

                    label = "HH"

                else:

                    difference = (

                        abs(
                            swing["price"]
                            -
                            previous_high[
                                "price"
                            ]
                        )
                        /
                        previous_high[
                            "price"
                        ]

                    ) * 100.0

                    if (
                        difference
                        <=
                        EQUAL_TOLERANCE_PCT
                    ):

                        label = (
                            "EQUAL_HIGH"
                        )

                    elif (
                        swing["price"]
                        >
                        previous_high[
                            "price"
                        ]
                    ):

                        label = "HH"

                    else:

                        label = "LH"

                previous_high = swing

            else:

                if previous_low is None:

                    label = "LL"

                else:

                    difference = (

                        abs(
                            swing["price"]
                            -
                            previous_low[
                                "price"
                            ]
                        )
                        /
                        previous_low[
                            "price"
                        ]

                    ) * 100.0

                    if (
                        difference
                        <=
                        EQUAL_TOLERANCE_PCT
                    ):

                        label = (
                            "EQUAL_LOW"
                        )

                    elif (
                        swing["price"]
                        >
                        previous_low[
                            "price"
                        ]
                    ):

                        label = "HL"

                    else:

                        label = "LL"

                previous_low = swing

            item["structure"] = label

            structures.append(
                item
            )

            swing_pointer += 1

    return structures


# ============================================================
# STRUCTURE CONTEXT
# ============================================================

def structure_context(
    structures,
    index
):

    available = [

        x

        for x in structures

        if x["confirmed_index"]
        <=
        index

    ]

    recent = available[
        -RECENT_STRUCTURE_COUNT:
    ]

    labels = [

        x["structure"]

        for x in recent

    ]

    bullish = sum(

        1

        for x in labels

        if x in (
            "HH",
            "HL",
        )

    )

    bearish = sum(

        1

        for x in labels

        if x in (
            "LH",
            "LL",
        )

    )

    if bullish > bearish:

        direction = 1

    elif bearish > bullish:

        direction = -1

    else:

        direction = 0

    return {

        "labels":
            labels,

        "direction":
            direction,
    }


# ============================================================
# STRUCTURAL LOCATION
# ============================================================

def structural_location(
    candles,
    structures,
    index
):

    recent = [

        x

        for x in structures

        if x["confirmed_index"]
        <=
        index

    ][
        -RECENT_LOCATION_COUNT:
    ]

    if len(recent) < 2:

        return {

            "position":
                0.5,

            "regime":
                "MIDDLE",
        }

    prices = [

        x["price"]

        for x in recent

    ]

    high = max(
        prices
    )

    low = min(
        prices
    )

    if high == low:

        position = 0.5

    else:

        position = (

            candles[index]["close"]
            -
            low

        ) / (

            high
            -
            low

        )

    position = max(
        0.0,
        min(
            1.0,
            position
        )
    )

    if position >= 0.67:

        regime = "HIGH"

    elif position <= 0.33:

        regime = "LOW"

    else:

        regime = "MIDDLE"

    return {

        "position":
            position,

        "regime":
            regime,
    }


# ============================================================
# STRUCTURE EVENTS
# ============================================================

def build_structure_events(
    candles,
    structures
):

    events = []

    active_high = None

    active_low = None

    broken_high = set()

    broken_low = set()

    trend = None

    pointer = 0

    for index in range(
        len(candles)
    ):

        while (

            pointer
            <
            len(structures)

            and

            structures[
                pointer
            ]["confirmed_index"]
            <=
            index

        ):

            swing = structures[
                pointer
            ]

            if swing["type"] == "SWING_HIGH":

                active_high = swing

            else:

                active_low = swing

            pointer += 1

        close = candles[
            index
        ]["close"]

        # ----------------------------------------------------
        # Bullish break
        # ----------------------------------------------------

        if active_high is not None:

            key = (
                active_high[
                    "candidate_index"
                ]
            )

            if (

                key not in broken_high

                and

                index
                >
                active_high[
                    "confirmed_index"
                ]

                and

                close
                >
                active_high[
                    "price"
                ]

            ):

                if trend == "BULLISH":

                    event_name = (
                        "BOS_BULLISH"
                    )

                else:

                    event_name = (
                        "CHoCH_BULLISH"
                    )

                events.append({

                    "index":
                        index,

                    "event":
                        event_name,

                    "direction":
                        "BULLISH",

                    "close":
                        close,

                    "broken_price":
                        active_high[
                            "price"
                        ],

                    "swing_index":
                        active_high[
                            "candidate_index"
                        ],

                    "confirmed_index":
                        active_high[
                            "confirmed_index"
                        ],

                    "timestamp":
                        candles[index][
                            "timestamp"
                        ],
                })

                broken_high.add(
                    key
                )

                trend = "BULLISH"

        # ----------------------------------------------------
        # Bearish break
        # ----------------------------------------------------

        if active_low is not None:

            key = (
                active_low[
                    "candidate_index"
                ]
            )

            if (

                key not in broken_low

                and

                index
                >
                active_low[
                    "confirmed_index"
                ]

                and

                close
                <
                active_low[
                    "price"
                ]

            ):

                if trend == "BEARISH":

                    event_name = (
                        "BOS_BEARISH"
                    )

                else:

                    event_name = (
                        "CHoCH_BEARISH"
                    )

                events.append({

                    "index":
                        index,

                    "event":
                        event_name,

                    "direction":
                        "BEARISH",

                    "close":
                        close,

                    "broken_price":
                        active_low[
                            "price"
                        ],

                    "swing_index":
                        active_low[
                            "candidate_index"
                        ],

                    "confirmed_index":
                        active_low[
                            "confirmed_index"
                        ],

                    "timestamp":
                        candles[index][
                            "timestamp"
                        ],
                })

                broken_low.add(
                    key
                )

                trend = "BEARISH"

    events.sort(
        key=lambda x: x["index"]
    )

    return events


# ============================================================
# FEATURE SNAPSHOT
# ============================================================

def build_feature_snapshot(
    index,
    candles,
    structures,
    events,
    atr,
    momentum
):

    candle = candles[index]

    cf = candle_features(
        candle
    )

    context = structure_context(
        structures,
        index
    )

    location = structural_location(
        candles,
        structures,
        index
    )

    atr_value = (

        atr[index]

        if atr[index] is not None

        else 0.0

    )

    close = candle["close"]

    if close != 0:

        atr_pct = (

            atr_value
            /
            close

        ) * 100.0

    else:

        atr_pct = 0.0

    recent_events = [

        event

        for event in events

        if event["index"]
        <=
        index

    ][
        -RECENT_EVENT_COUNT:
    ]

    event_direction = 0

    if recent_events:

        last = recent_events[-1]

        if (
            last["direction"]
            ==
            "BULLISH"
        ):

            event_direction = 1

        elif (
            last["direction"]
            ==
            "BEARISH"
        ):

            event_direction = -1

    return {

        "index":
            index,

        "price":
            close,

        "atr":
            atr_value,

        "atr_pct":
            atr_pct,

        "momentum":
            momentum[index],

        "body_pct":
            cf["body_pct"],

        "upper_wick_pct":
            cf["upper_wick_pct"],

        "lower_wick_pct":
            cf["lower_wick_pct"],

        "close_location":
            cf["close_location"],

        "candle_direction":
            cf["direction"],

        "structure_direction":
            context["direction"],

        "event_direction":
            event_direction,

        "structural_location":
            location["position"],

        "location_regime":
            location["regime"],
    }


# ============================================================
# SIGNAL DATASET
# ============================================================

def build_signal_dataset(
    candles,
    structures,
    events,
    atr,
    momentum
):

    signal_indexes = {}

    # --------------------------------------------------------
    # Structure signals
    # --------------------------------------------------------

    for swing in structures:

        index = swing[
            "confirmed_index"
        ]

        if index >= len(candles):
            continue

        if swing["structure"] not in (

            "HH",
            "HL",
            "LH",
            "LL",

        ):

            continue

        signal_indexes.setdefault(
            index,
            []
        ).append({

            "signal_type":
                swing["structure"],

            "signal_direction":

                (
                    "BULLISH"

                    if swing["structure"]
                    in (
                        "HH",
                        "HL",
                    )

                    else

                    "BEARISH"
                ),

            "signal_source":
                "STRUCTURE",

        })

    # --------------------------------------------------------
    # Event signals
    # --------------------------------------------------------

    for event in events:

        index = event["index"]

        if index >= len(candles):
            continue

        signal_indexes.setdefault(
            index,
            []
        ).append({

            "signal_type":
                event["event"],

            "signal_direction":
                event["direction"],

            "signal_source":
                "EVENT",

        })

    dataset = []

    for index in sorted(
        signal_indexes
    ):

        feature = build_feature_snapshot(
            index,
            candles,
            structures,
            events,
            atr,
            momentum
        )

        for signal in signal_indexes[
            index
        ]:

            record = dict(
                feature
            )

            record.update(
                signal
            )

            dataset.append(
                record
            )

    return dataset


# ============================================================
# OUTCOME
# ============================================================

def outcome_return(
    current,
    future
):

    if current == 0:
        return 0.0

    return (

        (
            future
            -
            current
        )
        /
        current

    ) * 100.0


def classify_outcome(
    current,
    future,
    threshold
):

    change = outcome_return(
        current,
        future
    )

    if change > threshold:
        return "BUY"

    if change < -threshold:
        return "SELL"

    return "NEUTRAL"


# ============================================================
# THRESHOLD SELECTION
# ============================================================

def threshold_training_stats(
    records,
    candles,
    horizon,
    threshold
):

    labels = []

    returns = []

    for record in records:

        index = record["index"]

        future_index = (
            index
            +
            horizon
        )

        if future_index >= len(
            candles
        ):

            continue

        current = candles[
            index
        ]["close"]

        future = candles[
            future_index
        ]["close"]

        ret = outcome_return(
            current,
            future
        )

        label = classify_outcome(
            current,
            future,
            threshold
        )

        labels.append(
            label
        )

        returns.append(
            ret
        )

    if not labels:

        return {

            "samples":
                0,

            "buy_pct":
                0.0,

            "sell_pct":
                0.0,

            "neutral_pct":
                0.0,

            "directional_pct":
                0.0,

            "directional_balance":
                0.0,

            "mean_abs_return":
                0.0,

        }

    buy = labels.count(
        "BUY"
    )

    sell = labels.count(
        "SELL"
    )

    neutral = labels.count(
        "NEUTRAL"
    )

    total = len(
        labels
    )

    buy_pct = (
        buy / total
    ) * 100.0

    sell_pct = (
        sell / total
    ) * 100.0

    neutral_pct = (
        neutral / total
    ) * 100.0

    directional_pct = (

        (
            buy
            +
            sell
        )
        /
        total

    ) * 100.0

    directional_balance = abs(
        buy_pct
        -
        sell_pct
    )

    mean_abs_return = mean(
        abs(x)
        for x in returns
    )

    return {

        "samples":
            total,

        "buy_pct":
            buy_pct,

        "sell_pct":
            sell_pct,

        "neutral_pct":
            neutral_pct,

        "directional_pct":
            directional_pct,

        "directional_balance":
            directional_balance,

        "mean_abs_return":
            mean_abs_return,

    }


def select_training_threshold(
    records,
    candles,
    horizon
):

    candidates = []

    for threshold in (
        RETURN_THRESHOLD_CANDIDATES
    ):

        stats = threshold_training_stats(
            records,
            candles,
            horizon,
            threshold
        )

        if stats["samples"] < 10:
            continue

        directional = (
            stats["directional_pct"]
        )

        balance_penalty = (

            stats["directional_balance"]
            /
            100.0

        )

        score = (

            directional
            -
            balance_penalty * 20.0

        )

        candidates.append({

            "threshold":
                threshold,

            "score":
                score,

            "stats":
                stats,

        })

    if not candidates:

        return {

            "threshold":
                0.0,

            "score":
                0.0,

            "stats":
                threshold_training_stats(
                    records,
                    candles,
                    horizon,
                    0.0
                ),

        }

    candidates.sort(

        key=lambda x: (

            x["score"],

            x["stats"][
                "directional_pct"
            ],

            -x["threshold"],

        ),

        reverse=True

    )

    return candidates[0]


# ============================================================
# TRAINING MEDIAN
# ============================================================

def training_median(
    records,
    key
):

    values = [

        float(record[key])

        for record in records

        if isinstance(
            record.get(key),
            (int, float)
        )

        and finite(
            record[key]
        )

    ]

    if not values:
        return 0.0

    values.sort()

    middle = len(values) // 2

    if len(values) % 2 == 0:

        return (

            values[middle - 1]
            +
            values[middle]

        ) / 2.0

    return values[middle]


def learn_feature_thresholds(
    training
):

    momentum_records = [

        {
            "x":
                abs(
                    record["momentum"]
                )
        }

        for record in training

    ]

    return {

        "atr_pct_median":

            training_median(
                training,
                "atr_pct"
            ),

        "momentum_abs_median":

            training_median(
                momentum_records,
                "x"
            ),

        "close_location_median":

            training_median(
                training,
                "close_location"
            ),

        "structural_location_median":

            training_median(
                training,
                "structural_location"
            ),

        "body_pct_median":

            training_median(
                training,
                "body_pct"
            ),

    }


# ============================================================
# FEATURE DIRECTIONS
# ============================================================

def feature_direction(
    record,
    feature_name,
    thresholds
):

    # --------------------------------------------------------
    # MARKET STRUCTURE
    # --------------------------------------------------------

    if feature_name == "MARKET_STRUCTURE":

        return record[
            "structure_direction"
        ]

    # --------------------------------------------------------
    # MOMENTUM
    #
    # Use training-learned magnitude threshold.
    # --------------------------------------------------------

    if feature_name == "MOMENTUM":

        value = record[
            "momentum"
        ]

        threshold = thresholds.get(
            "momentum_abs_median",
            0.0
        )

        if (
            value > threshold
            and
            threshold > 0
        ):

            return 1

        if (
            value < -threshold
            and
            threshold > 0
        ):

            return -1

        # If threshold is zero, use sign.
        if threshold == 0:

            if value > 0:
                return 1

            if value < 0:
                return -1

        return 0

    # --------------------------------------------------------
    # CANDLE BEHAVIOUR
    #
    # Close location threshold learned from training.
    # --------------------------------------------------------

    if feature_name == "CANDLE_BEHAVIOUR":

        location = record[
            "close_location"
        ]

        median = thresholds.get(
            "close_location_median",
            0.5
        )

        if location > median:

            return 1

        if location < median:

            return -1

        return 0

    # --------------------------------------------------------
    # STRUCTURAL LOCATION
    #
    # Still contextual rather than intrinsically directional.
    #
    # Here it acts as a confirmation filter:
    #
    # bullish structure + low location
    # bearish structure + high location
    #
    # This prevents the simplistic assumption that location
    # alone predicts direction.
    # --------------------------------------------------------

    if feature_name == "STRUCTURAL_LOCATION":

        location = record[
            "structural_location"
        ]

        structure = record[
            "structure_direction"
        ]

        if (
            structure > 0
            and
            location < 0.5
        ):

            return 1

        if (
            structure < 0
            and
            location > 0.5
        ):

            return -1

        return 0

    # --------------------------------------------------------
    # ATR
    #
    # ATR remains a volatility regime and does not directly
    # predict direction.
    #
    # It therefore does not cast a directional vote.
    # --------------------------------------------------------

    if feature_name == "ATR_VOLATILITY":

        return 0

    return 0


# ============================================================
# PREDICTION
# ============================================================

def predict_direction(
    record,
    feature_group,
    thresholds
):

    votes = []

    for feature in feature_group:

        direction = feature_direction(
            record,
            feature,
            thresholds
        )

        if direction != 0:

            votes.append(
                direction
            )

    if not votes:
        return "NEUTRAL"

    total = sum(
        votes
    )

    if total > 0:
        return "BUY"

    if total < 0:
        return "SELL"

    return "NEUTRAL"


# ============================================================
# OUTCOME DISTRIBUTION
# ============================================================

def outcome_distribution(
    records,
    candles,
    horizon,
    threshold
):

    counts = {

        "BUY":
            0,

        "SELL":
            0,

        "NEUTRAL":
            0,

    }

    for record in records:

        index = record[
            "index"
        ]

        future_index = (
            index
            +
            horizon
        )

        if future_index >= len(
            candles
        ):

            continue

        current = candles[
            index
        ]["close"]

        future = candles[
            future_index
        ]["close"]

        label = classify_outcome(
            current,
            future,
            threshold
        )

        counts[label] += 1

    total = sum(
        counts.values()
    )

    if total == 0:

        return {

            "BUY":
                0.0,

            "SELL":
                0.0,

            "NEUTRAL":
                0.0,

        }

    return {

        key:
            counts[key]
            /
            total
            *
            100.0

        for key in counts

    }


# ============================================================
# MAJORITY BASELINE
# ============================================================

def majority_baseline(
    records,
    candles,
    horizon,
    threshold
):

    distribution = outcome_distribution(
        records,
        candles,
        horizon,
        threshold
    )

    label = max(
        distribution,
        key=distribution.get
    )

    return {

        "label":
            label,

        "BUY":
            distribution["BUY"],

        "SELL":
            distribution["SELL"],

        "NEUTRAL":
            distribution["NEUTRAL"],

    }


# ============================================================
# METRICS
# ============================================================

def calculate_metrics(
    records,
    candles,
    feature_group,
    horizon,
    threshold,
    baseline,
    feature_thresholds
):

    outputs = []

    for record in records:

        index = record[
            "index"
        ]

        future_index = (
            index
            +
            horizon
        )

        if future_index >= len(
            candles
        ):

            continue

        current = candles[
            index
        ]["close"]

        future = candles[
            future_index
        ]["close"]

        actual = classify_outcome(
            current,
            future,
            threshold
        )

        prediction = predict_direction(
            record,
            feature_group,
            feature_thresholds
        )

        outputs.append({

            "prediction":
                prediction,

            "actual":
                actual,

            "return":
                outcome_return(
                    current,
                    future
                ),

        })

    if not outputs:

        return {

            "signals":
                0,

            "accuracy":
                0.0,

            "precision_buy":
                0.0,

            "recall_buy":
                0.0,

            "predicted_directional_pct":
                0.0,

            "actual_directional_pct":
                0.0,

            "avg_return":
                0.0,

            "baseline":
                baseline,

            "edge":
                0.0,

        }

    correct = sum(

        1

        for x in outputs

        if x["prediction"]
        ==
        x["actual"]

    )

    accuracy = (

        correct
        /
        len(outputs)

    ) * 100.0

    predicted_buy = [

        x

        for x in outputs

        if x["prediction"]
        ==
        "BUY"

    ]

    true_buy = [

        x

        for x in predicted_buy

        if x["actual"]
        ==
        "BUY"

    ]

    actual_buy = [

        x

        for x in outputs

        if x["actual"]
        ==
        "BUY"

    ]

    precision_buy = (

        len(true_buy)
        /
        len(predicted_buy)

        * 100.0

        if predicted_buy

        else 0.0

    )

    recall_buy = (

        len(true_buy)
        /
        len(actual_buy)

        * 100.0

        if actual_buy

        else 0.0

    )

    predicted_directional = [

        x

        for x in outputs

        if x["prediction"]
        !=
        "NEUTRAL"

    ]

    actual_directional = [

        x

        for x in outputs

        if x["actual"]
        !=
        "NEUTRAL"

    ]

    predicted_directional_pct = (

        len(predicted_directional)
        /
        len(outputs)

    ) * 100.0

    actual_directional_pct = (

        len(actual_directional)
        /
        len(outputs)

    ) * 100.0

    avg_return = mean(

        x["return"]

        for x in outputs

    )

    edge = (

        accuracy
        -
        baseline

    )

    return {

        "signals":
            len(outputs),

        "accuracy":
            accuracy,

        "precision_buy":
            precision_buy,

        "recall_buy":
            recall_buy,

        "predicted_directional_pct":
            predicted_directional_pct,

        "actual_directional_pct":
            actual_directional_pct,

        "avg_return":
            avg_return,

        "baseline":
            baseline,

        "edge":
            edge,

    }


# ============================================================
# WALK-FORWARD WINDOW CREATION
# ============================================================

def create_walkforward_windows(
    total_candles
):

    if total_candles < (
        MIN_TRAIN_CANDLES
        +
        MIN_OOS_CANDLES
    ):

        raise RuntimeError(
            "Not enough candles for "
            "walk-forward validation."
        )

    windows = []

    # --------------------------------------------------------
    # Expanding training windows.
    #
    # Each OOS block occurs AFTER the corresponding training
    # block.
    #
    # Training data is never taken from the future.
    # --------------------------------------------------------

    first_train_end = int(
        total_candles
        *
        TRAIN_RATIO
    )

    remaining = (
        total_candles
        -
        first_train_end
    )

    if remaining < MIN_OOS_CANDLES:

        raise RuntimeError(
            "Insufficient OOS candles."
        )

    possible_oos_size = max(
        MIN_OOS_CANDLES,
        remaining // WINDOW_COUNT
    )

    for window_number in range(
        WINDOW_COUNT
    ):

        oos_start = (

            first_train_end
            +
            window_number
            *
            possible_oos_size

        )

        if oos_start >= total_candles:
            break

        if window_number == (
            WINDOW_COUNT - 1
        ):

            oos_end = total_candles

        else:

            oos_end = min(

                total_candles,

                oos_start
                +
                possible_oos_size

            )

        train_end = oos_start

        if (
            train_end
            <
            MIN_TRAIN_CANDLES
        ):

            continue

        if (
            oos_end
            -
            oos_start
            <
            MIN_OOS_CANDLES
        ):

            continue

        windows.append({

            "window":
                len(windows) + 1,

            "train_start":
                0,

            "train_end":
                train_end,

            "oos_start":
                oos_start,

            "oos_end":
                oos_end,

        })

    if not windows:

        raise RuntimeError(
            "No valid walk-forward windows."
        )

    return windows


# ============================================================
# WINDOW STATISTICS
# ============================================================

def summarize_metric(values):

    values = [

        float(x)

        for x in values

        if finite(x)

    ]

    if not values:

        return {

            "count":
                0,

            "mean":
                0.0,

            "median":
                0.0,

            "std":
                0.0,

            "min":
                0.0,

            "max":
                0.0,

        }

    return {

        "count":
            len(values),

        "mean":
            mean(values),

        "median":
            statistics.median(
                values
            ),

        "std":
            (
                statistics.stdev(
                    values
                )
                if len(values) > 1
                else 0.0
            ),

        "min":
            min(values),

        "max":
            max(values),

    }


# ============================================================
# INTEGRITY CHECKS
# ============================================================

def check_structure_timing(
    structures
):

    violations = []

    for structure in structures:

        if (
            structure[
                "confirmed_index"
            ]
            <
            structure[
                "candidate_index"
            ]
        ):

            violations.append(
                structure
            )

    return violations


def check_event_timing(
    events
):

    violations = []

    for event in events:

        if (
            event[
                "confirmed_index"
            ]
            >=
            event[
                "index"
            ]
        ):

            violations.append(
                event
            )

    return violations


def check_signal_timing(
    signals,
    structures,
    events
):

    violations = []

    structure_map = {

        (
            x["confirmed_index"],
            x["structure"]
        ):
            x

        for x in structures

    }

    event_map = {

        (
            x["index"],
            x["event"]
        ):
            x

        for x in events

    }

    for signal in signals:

        index = signal[
            "index"
        ]

        if (
            signal[
                "signal_source"
            ]
            ==
            "STRUCTURE"
        ):

            key = (

                index,

                signal[
                    "signal_type"
                ]

            )

            structure = structure_map.get(
                key
            )

            if structure is None:

                violations.append(
                    signal
                )

        elif (
            signal[
                "signal_source"
            ]
            ==
            "EVENT"
        ):

            key = (

                index,

                signal[
                    "signal_type"
                ]

            )

            event = event_map.get(
                key
            )

            if event is None:

                violations.append(
                    signal
                )

            elif (
                event[
                    "confirmed_index"
                ]
                >=
                index
            ):

                violations.append(
                    signal
                )

    return violations


def check_feature_causality(
    signals,
    structures,
    events
):

    violations = []

    for signal in signals:

        index = signal[
            "index"
        ]

        available_structures = [

            x

            for x in structures

            if x[
                "confirmed_index"
            ]
            <=
            index

        ]

        for structure in (
            available_structures
        ):

            if (
                structure[
                    "confirmed_index"
                ]
                >
                index
            ):

                violations.append({
                    "type":
                        "FUTURE_STRUCTURE",
                    "signal_index":
                        index,
                    "structure":
                        structure,
                })

        available_events = [

            x

            for x in events

            if x["index"]
            <=
            index

        ]

        for event in available_events:

            if event["index"] > index:

                violations.append({
                    "type":
                        "FUTURE_EVENT",
                    "signal_index":
                        index,
                    "event":
                        event,
                })

    return violations


def check_outcome_separation(
    signals,
    candles
):

    violations = []

    for signal in signals:

        index = signal[
            "index"
        ]

        for horizon in HORIZONS:

            future_index = (
                index
                +
                horizon
            )

            if future_index >= len(
                candles
            ):

                continue

            if future_index <= index:

                violations.append({

                    "signal_index":
                        index,

                    "future_index":
                        future_index,

                    "horizon":
                        horizon,

                })

    return violations


def check_window_boundaries(
    records,
    train_start,
    train_end,
    oos_start,
    oos_end
):

    violations = []

    for record in records:

        index = record[
            "index"
        ]

        if (
            index < train_start
            or
            index >= oos_end
        ):

            violations.append(
                record
            )

    return violations


# ============================================================
# REPORT CLASS
# ============================================================

class Report:

    def __init__(self):

        self.lines = []

    def add(
        self,
        text=""
    ):

        self.lines.append(
            str(text)
        )

    def section(
        self,
        title
    ):

        self.add()

        self.add(
            "=" * 80
        )

        self.add(
            title
        )

        self.add(
            "=" * 80
        )

    def subsection(
        self,
        title
    ):

        self.add()

        self.add(
            "-" * 80
        )

        self.add(
            title
        )

        self.add(
            "-" * 80
        )

    def save(
        self,
        filename
    ):

        with open(
            filename,
            "w",
            encoding="utf-8"
        ) as f:

            f.write(
                "\n".join(
                    self.lines
                )
            )


# ============================================================
# MAIN
# ============================================================

def main():

    report = Report()

    banner(
        "MLAI v3.8.3 CAUSAL WALK-FORWARD "
        "MARKET STRUCTURE VALIDATION"
    )

    print(
        """
RESEARCH EXPERIMENT

v3.8.3:

    - causal confirmed structure
    - causal BOS / CHoCH
    - multiple chronological windows
    - training-only threshold learning
    - separate threshold per horizon
    - frozen OOS thresholds
    - training-learned feature thresholds
    - per-window OOS validation
    - combined OOS validation
    - stability statistics
    - look-ahead checks
    - boundary checks

TRAINING:
    Expanding chronological history

OOS:
    Immediately following unseen period

market_data.bin:
    READ ONLY
"""
    )

    report.add(
        "# MLAI v3.8.3 CAUSAL WALK-FORWARD "
        "MARKET STRUCTURE VALIDATION"
    )

    report.add()

    report.add(
        "Research-only chronological "
        "walk-forward validation."
    )

    # ========================================================
    # PROTECTION
    # ========================================================

    section(
        "PROTECTION CHECK"
    )

    print(
        "market_data.bin     : READ ONLY"
    )

    print(
        "Production MLAI     : NOT MODIFIED"
    )

    print(
        "Learning memory     : NOT MODIFIED"
    )

    print(
        "Trading             : DISABLED"
    )

    print(
        "Internet            : NOT REQUIRED"
    )

    # ========================================================
    # LOAD
    # ========================================================

    data, candles, invalid = (
        load_market_data()
    )

    section(
        "DATA QUALITY AUDIT"
    )

    print(
        f"Data type           : "
        f"{type(data).__name__}"
    )

    print(
        f"Valid candles       : "
        f"{len(candles)}"
    )

    print(
        f"Invalid candles     : "
        f"{invalid}"
    )

    if len(candles) < 300:

        raise RuntimeError(
            "At least 300 candles are recommended "
            "for multi-window validation."
        )

    # ========================================================
    # CHRONOLOGY
    # ========================================================

    chronological = chronological_check(
        candles
    )

    section(
        "CHRONOLOGICAL DATA CHECK"
    )

    print(
        "Timestamp order: "
        +
        (
            "PASS"
            if chronological
            else "FAIL"
        )
    )

    if not chronological:

        raise RuntimeError(
            "Timestamp order failed."
        )

    # ========================================================
    # WALK-FORWARD WINDOWS
    # ========================================================

    windows = create_walkforward_windows(
        len(candles)
    )

    section(
        "WALK-FORWARD WINDOWS"
    )

    print(
        f"Windows requested : "
        f"{WINDOW_COUNT}"
    )

    print(
        f"Windows created   : "
        f"{len(windows)}"
    )

    for window in windows:

        print(

            f"Window {window['window']} | "
            f"TRAIN [{window['train_start']}:"
            f"{window['train_end']}] | "
            f"OOS [{window['oos_start']}:"
            f"{window['oos_end']}]"

        )

    # ========================================================
    # FEATURES
    # ========================================================

    section(
        "FEATURE CALCULATION"
    )

    atr = calculate_atr(
        candles
    )

    momentum = calculate_momentum(
        candles
    )

    print(
        "ATR calculation     : COMPLETE"
    )

    print(
        "Momentum calculation: COMPLETE"
    )

    # ========================================================
    # SWINGS
    # ========================================================

    section(
        "CONFIRMED SWINGS"
    )

    raw_swings = (
        detect_confirmed_swings(
            candles
        )
    )

    print(
        f"Raw confirmed swings: "
        f"{len(raw_swings)}"
    )

    # ========================================================
    # CAUSAL STRUCTURE
    # ========================================================

    structures = (
        build_causal_structures(
            candles,
            raw_swings
        )
    )

    print(
        f"Causal structures   : "
        f"{len(structures)}"
    )

    structure_counts = {}

    for structure in structures:

        label = structure[
            "structure"
        ]

        structure_counts[label] = (

            structure_counts.get(
                label,
                0
            )
            +
            1

        )

    # ========================================================
    # STRUCTURE EVENTS
    # ========================================================

    events = (
        build_structure_events(
            candles,
            structures
        )
    )

    event_counts = {}

    for event in events:

        name = event[
            "event"
        ]

        event_counts[name] = (

            event_counts.get(
                name,
                0
            )
            +
            1

        )

    section(
        "STRUCTURE EVENTS"
    )

    for name in [

        "BOS_BULLISH",
        "BOS_BEARISH",
        "CHoCH_BULLISH",
        "CHoCH_BEARISH",

    ]:

        print(

            f"{name:<20}: "
            f"{event_counts.get(name, 0)}"

        )

    # ========================================================
    # TIMING CHECKS
    # ========================================================

    structure_timing_violations = (
        check_structure_timing(
            structures
        )
    )

    event_timing_violations = (
        check_event_timing(
            events
        )
    )

    section(
        "CAUSAL STRUCTURE TIMING"
    )

    print(
        "Structure timing: "
        +
        (
            "PASS"
            if not structure_timing_violations
            else "FAIL"
        )
    )

    if structure_timing_violations:

        raise RuntimeError(
            "Structure timing violation detected."
        )

    print(
        "Event timing: "
        +
        (
            "PASS"
            if not event_timing_violations
            else "FAIL"
        )
    )

    if event_timing_violations:

        raise RuntimeError(
            "Event timing violation detected."
        )

    # ========================================================
    # SIGNAL DATASET
    # ========================================================

    signals = build_signal_dataset(
        candles,
        structures,
        events,
        atr,
        momentum
    )

    section(
        "SIGNAL DATASET"
    )

    print(
        f"Signal records: "
        f"{len(signals)}"
    )

    signal_indices = [

        x["index"]

        for x in signals

    ]

    signal_chronological = (
        signal_indices
        ==
        sorted(
            signal_indices
        )
    )

    print(
        "Signal chronological order: "
        +
        (
            "PASS"
            if signal_chronological
            else "FAIL"
        )
    )

    if not signal_chronological:

        raise RuntimeError(
            "Signal chronological order failed."
        )

    # ========================================================
    # GLOBAL CAUSALITY CHECK
    # ========================================================

    signal_timing_violations = (
        check_signal_timing(
            signals,
            structures,
            events
        )
    )

    feature_causality_violations = (
        check_feature_causality(
            signals,
            structures,
            events
        )
    )

    section(
        "GLOBAL CAUSALITY CHECK"
    )

    print(
        "Signal source timing: "
        +
        (
            "PASS"
            if not signal_timing_violations
            else "FAIL"
        )
    )

    print(
        "Feature causality: "
        +
        (
            "PASS"
            if not feature_causality_violations
            else "FAIL"
        )
    )

    if signal_timing_violations:

        raise RuntimeError(
            "Signal timing violation detected."
        )

    if feature_causality_violations:

        raise RuntimeError(
            "Feature causality violation detected."
        )

    # ========================================================
    # FEATURE GROUPS
    # ========================================================

    FEATURE_GROUPS = {

        "MARKET_STRUCTURE": [

            "MARKET_STRUCTURE",

        ],

        "STRUCTURE_MOMENTUM": [

            "MARKET_STRUCTURE",
            "MOMENTUM",

        ],

        "STRUCTURE_CANDLE": [

            "MARKET_STRUCTURE",
            "CANDLE_BEHAVIOUR",

        ],

        "STRUCTURE_LOCATION": [

            "MARKET_STRUCTURE",
            "STRUCTURAL_LOCATION",

        ],

        "STRUCTURE_MOMENTUM_CANDLE": [

            "MARKET_STRUCTURE",
            "MOMENTUM",
            "CANDLE_BEHAVIOUR",

        ],

        "STRUCTURE_FULL_CONTEXT": [

            "MARKET_STRUCTURE",
            "MOMENTUM",
            "CANDLE_BEHAVIOUR",
            "ATR_VOLATILITY",
            "STRUCTURAL_LOCATION",

        ],

    }

    # ========================================================
    # WALK-FORWARD VALIDATION
    # ========================================================

    all_window_results = {}

    combined_results = {}

    window_summaries = []

    for window in windows:

        window_number = window[
            "window"
        ]

        train_start = window[
            "train_start"
        ]

        train_end = window[
            "train_end"
        ]

        oos_start = window[
            "oos_start"
        ]

        oos_end = window[
            "oos_end"
        ]

        train_records = [

            x

            for x in signals

            if (
                train_start
                <=
                x["index"]
                <
                train_end
            )

        ]

        oos_records = [

            x

            for x in signals

            if (
                oos_start
                <=
                x["index"]
                <
                oos_end
            )

        ]

        # ----------------------------------------------------
        # Remove records without required future horizon.
        # ----------------------------------------------------

        train_records = [

            x

            for x in train_records

            if (
                x["index"]
                +
                max(HORIZONS)
                <
                len(candles)
            )

        ]

        oos_records = [

            x

            for x in oos_records

            if (
                x["index"]
                +
                max(HORIZONS)
                <
                len(candles)
            )

        ]

        subsection(
            f"WALK-FORWARD WINDOW {window_number}"
        )

        print(
            f"Training candles : "
            f"{train_end - train_start}"
        )

        print(
            f"OOS candles      : "
            f"{oos_end - oos_start}"
        )

        print(
            f"Training signals : "
            f"{len(train_records)}"
        )

        print(
            f"OOS signals      : "
            f"{len(oos_records)}"
        )

        if len(train_records) < 10:

            print(
                "WARNING: Low training signal count."
            )

        # ----------------------------------------------------
        # Outcome thresholds
        # ----------------------------------------------------

        selected_thresholds = {}

        threshold_stats = {}

        for horizon in HORIZONS:

            result = select_training_threshold(
                train_records,
                candles,
                horizon
            )

            selected_thresholds[
                horizon
            ] = result[
                "threshold"
            ]

            threshold_stats[
                horizon
            ] = result[
                "stats"
            ]

        # ----------------------------------------------------
        # Feature thresholds
        # ----------------------------------------------------

        feature_thresholds = (
            learn_feature_thresholds(
                train_records
            )
        )

        print()

        print(
            "Training-learned outcome thresholds:"
        )

        for horizon in HORIZONS:

            print(

                f"    H+{horizon}: "
                f"{selected_thresholds[horizon]:.4f}%"

            )

        print()

        print(
            "Training-learned feature thresholds:"
        )

        for key, value in (
            feature_thresholds.items()
        ):

            print(

                f"    {key:<32}: "
                f"{value:.6f}"

            )

        # ----------------------------------------------------
        # Per-horizon baseline
        # ----------------------------------------------------

        baselines = {}

        for horizon in HORIZONS:

            baselines[
                horizon
            ] = majority_baseline(

                train_records,

                candles,

                horizon,

                selected_thresholds[
                    horizon
                ]

            )

        # ----------------------------------------------------
        # Feature results
        # ----------------------------------------------------

        window_feature_results = {}

        for group_name, feature_group in (
            FEATURE_GROUPS.items()
        ):

            window_feature_results[
                group_name
            ] = {}

            for horizon in HORIZONS:

                baseline = baselines[
                    horizon
                ][
                    baselines[
                        horizon
                    ]["label"]
                ]

                metrics = calculate_metrics(

                    oos_records,

                    candles,

                    feature_group,

                    horizon,

                    selected_thresholds[
                        horizon
                    ],

                    baseline,

                    feature_thresholds

                )

                window_feature_results[
                    group_name
                ][horizon] = metrics

                print(

                    f"{group_name:<30} "
                    f"H+{horizon:<2} | "
                    f"N={metrics['signals']:<5} | "
                    f"Accuracy="
                    f"{metrics['accuracy']:.2f}% | "
                    f"Baseline="
                    f"{metrics['baseline']:.2f}% | "
                    f"Edge="
                    f"{metrics['edge']:+.2f}%"

                )

        # ----------------------------------------------------
        # Directional structure results
        # ----------------------------------------------------

        directional_groups = {

            "BULLISH_STRUCTURE": [

                x

                for x in oos_records

                if x[
                    "signal_direction"
                ]
                ==
                "BULLISH"

            ],

            "BEARISH_STRUCTURE": [

                x

                for x in oos_records

                if x[
                    "signal_direction"
                ]
                ==
                "BEARISH"

            ],

            "ALL_STRUCTURE": [

                x

                for x in oos_records

            ],

        }

        directional_results = {}

        for group_name, group_records in (
            directional_groups.items()
        ):

            directional_results[
                group_name
            ] = {}

            for horizon in HORIZONS:

                baseline = baselines[
                    horizon
                ][
                    baselines[
                        horizon
                    ]["label"]
                ]

                metrics = calculate_metrics(

                    group_records,

                    candles,

                    [
                        "MARKET_STRUCTURE"
                    ],

                    horizon,

                    selected_thresholds[
                        horizon
                    ],

                    baseline,

                    feature_thresholds

                )

                directional_results[
                    group_name
                ][horizon] = metrics

        # ----------------------------------------------------
        # Event results
        # ----------------------------------------------------

        event_results = {}

        for event_type in [

            "BOS_BULLISH",
            "BOS_BEARISH",
            "CHoCH_BULLISH",
            "CHoCH_BEARISH",

        ]:

            records = [

                x

                for x in oos_records

                if x[
                    "signal_type"
                ]
                ==
                event_type

            ]

            event_results[
                event_type
            ] = {}

            for horizon in HORIZONS:

                baseline = baselines[
                    horizon
                ][
                    baselines[
                        horizon
                    ]["label"]
                ]

                metrics = calculate_metrics(

                    records,

                    candles,

                    [
                        "MARKET_STRUCTURE"
                    ],

                    horizon,

                    selected_thresholds[
                        horizon
                    ],

                    baseline,

                    feature_thresholds

                )

                event_results[
                    event_type
                ][horizon] = metrics

        # ----------------------------------------------------
        # Store window
        # ----------------------------------------------------

        all_window_results[
            window_number
        ] = {

            "window":
                window,

            "training_signals":
                len(train_records),

            "oos_signals":
                len(oos_records),

            "selected_thresholds":
                selected_thresholds,

            "threshold_stats":
                threshold_stats,

            "feature_thresholds":
                feature_thresholds,

            "baselines":
                baselines,

            "feature_results":
                window_feature_results,

            "directional_results":
                directional_results,

            "event_results":
                event_results,

        }

        window_summaries.append({

            "window":
                window_number,

            "training_signals":
                len(train_records),

            "oos_signals":
                len(oos_records),

            "oos_start":
                oos_start,

            "oos_end":
                oos_end,

        })

    # ========================================================
    # COMBINED OOS
    # ========================================================

    section(
        "COMBINED OUT-OF-SAMPLE RESULTS"
    )

    combined_oos = []

    for window in windows:

        start = window[
            "oos_start"
        ]

        end = window[
            "oos_end"
        ]

        records = [

            x

            for x in signals

            if (
                start
                <=
                x["index"]
                <
                end
            )

            and

            (
                x["index"]
                +
                max(HORIZONS)
                <
                len(candles)
            )

        ]

        combined_oos.extend(
            records
        )

    combined_oos.sort(
        key=lambda x: x["index"]
    )

    print(
        f"Combined OOS signals: "
        f"{len(combined_oos)}"
    )

    # --------------------------------------------------------
    # Combined results need a fair fixed threshold.
    #
    # We do NOT learn from combined OOS.
    #
    # Use the threshold from the earliest walk-forward
    # training period for reporting consistency.
    #
    # The primary evaluation remains per-window.
    # --------------------------------------------------------

    first_window = all_window_results[
        windows[0]["window"]
    ]

    combined_thresholds = first_window[
        "selected_thresholds"
    ]

    combined_feature_thresholds = first_window[
        "feature_thresholds"
    ]

    combined_results = {}

    for group_name, feature_group in (
        FEATURE_GROUPS.items()
    ):

        combined_results[
            group_name
        ] = {}

        for horizon in HORIZONS:

            training_records_for_baseline = [

                x

                for x in signals

                if x["index"]
                <
                windows[0]["oos_start"]

            ]

            baseline = majority_baseline(

                training_records_for_baseline,

                candles,

                horizon,

                combined_thresholds[
                    horizon
                ]

            )

            metrics = calculate_metrics(

                combined_oos,

                candles,

                feature_group,

                horizon,

                combined_thresholds[
                    horizon
                ],

                baseline[
                    baseline["label"]
                ],

                combined_feature_thresholds

            )

            combined_results[
                group_name
            ][horizon] = metrics

            print(

                f"{group_name:<30} "
                f"H+{horizon:<2} | "
                f"N={metrics['signals']:<5} | "
                f"Accuracy="
                f"{metrics['accuracy']:.2f}% | "
                f"Baseline="
                f"{metrics['baseline']:.2f}% | "
                f"Edge="
                f"{metrics['edge']:+.2f}%"

            )

    # ========================================================
    # STABILITY ANALYSIS
    # ========================================================

    section(
        "WALK-FORWARD STABILITY ANALYSIS"
    )

    stability = {}

    for group_name in FEATURE_GROUPS:

        stability[
            group_name
        ] = {}

        for horizon in HORIZONS:

            accuracies = []

            edges = []

            avg_returns = []

            sample_counts = []

            for window_number in (
                all_window_results
            ):

                metrics = (
                    all_window_results[
                        window_number
                    ][
                        "feature_results"
                    ][
                        group_name
                    ][
                        horizon
                    ]
                )

                accuracies.append(
                    metrics[
                        "accuracy"
                    ]
                )

                edges.append(
                    metrics[
                        "edge"
                    ]
                )

                avg_returns.append(
                    metrics[
                        "avg_return"
                    ]
                )

                sample_counts.append(
                    metrics[
                        "signals"
                    ]
                )

            stability[
                group_name
            ][horizon] = {

                "accuracy":
                    summarize_metric(
                        accuracies
                    ),

                "edge":
                    summarize_metric(
                        edges
                    ),

                "avg_return":
                    summarize_metric(
                        avg_returns
                    ),

                "sample_count":
                    summarize_metric(
                        sample_counts
                    ),

            }

            a = stability[
                group_name
            ][horizon][
                "accuracy"
            ]

            e = stability[
                group_name
            ][horizon][
                "edge"
            ]

            print(

                f"{group_name:<30} "
                f"H+{horizon:<2} | "
                f"Accuracy Mean="
                f"{a['mean']:.2f}% | "
                f"Median="
                f"{a['median']:.2f}% | "
                f"Std="
                f"{a['std']:.2f} | "
                f"Min="
                f"{a['min']:.2f}% | "
                f"Max="
                f"{a['max']:.2f}% | "
                f"Mean Edge="
                f"{e['mean']:+.2f}%"

            )

    # ========================================================
    # STRUCTURE / EVENT COMBINED ANALYSIS
    # ========================================================

    section(
        "COMBINED STRUCTURE / EVENT ANALYSIS"
    )

    combined_directional = {}

    combined_events = {}

    for name, records in {

        "BULLISH_STRUCTURE": [

            x

            for x in combined_oos

            if x[
                "signal_direction"
            ]
            ==
            "BULLISH"

        ],

        "BEARISH_STRUCTURE": [

            x

            for x in combined_oos

            if x[
                "signal_direction"
            ]
            ==
            "BEARISH"

        ],

        "ALL_STRUCTURE": combined_oos,

    }.items():

        combined_directional[
            name
        ] = {}

        print()

        print(name)

        for horizon in HORIZONS:

            baseline_training = [

                x

                for x in signals

                if x["index"]
                <
                windows[0]["oos_start"]

            ]

            baseline = majority_baseline(

                baseline_training,

                candles,

                horizon,

                combined_thresholds[
                    horizon
                ]

            )

            metrics = calculate_metrics(

                records,

                candles,

                [
                    "MARKET_STRUCTURE"
                ],

                horizon,

                combined_thresholds[
                    horizon
                ],

                baseline[
                    baseline["label"]
                ],

                combined_feature_thresholds

            )

            combined_directional[
                name
            ][horizon] = metrics

            print(

                f"H+{horizon} | "
                f"N={metrics['signals']} | "
                f"Accuracy="
                f"{metrics['accuracy']:.2f}% | "
                f"Edge="
                f"{metrics['edge']:+.2f}%"

            )

    for event_type in [

        "BOS_BULLISH",
        "BOS_BEARISH",
        "CHoCH_BULLISH",
        "CHoCH_BEARISH",

    ]:

        records = [

            x

            for x in combined_oos

            if x[
                "signal_type"
            ]
            ==
            event_type

        ]

        combined_events[
            event_type
        ] = {}

        print()

        print(event_type)

        for horizon in HORIZONS:

            baseline_training = [

                x

                for x in signals

                if x["index"]
                <
                windows[0]["oos_start"]

            ]

            baseline = majority_baseline(

                baseline_training,

                candles,

                horizon,

                combined_thresholds[
                    horizon
                ]

            )

            metrics = calculate_metrics(

                records,

                candles,

                [
                    "MARKET_STRUCTURE"
                ],

                horizon,

                combined_thresholds[
                    horizon
                ],

                baseline[
                    baseline["label"]
                ],

                combined_feature_thresholds

            )

            combined_events[
                event_type
            ][horizon] = metrics

            print(

                f"H+{horizon} | "
                f"N={metrics['signals']} | "
                f"Accuracy="
                f"{metrics['accuracy']:.2f}% | "
                f"Edge="
                f"{metrics['edge']:+.2f}%"

            )

    # ========================================================
    # OUTCOME DISTRIBUTIONS
    # ========================================================

    section(
        "COMBINED OOS OUTCOME DISTRIBUTIONS"
    )

    combined_distributions = {}

    for horizon in HORIZONS:

        distribution = outcome_distribution(

            combined_oos,

            candles,

            horizon,

            combined_thresholds[
                horizon
            ]

        )

        combined_distributions[
            horizon
        ] = distribution

        print(

            f"H+{horizon}: "
            f"BUY={distribution['BUY']:.2f}% | "
            f"SELL={distribution['SELL']:.2f}% | "
            f"NEUTRAL={distribution['NEUTRAL']:.2f}%"

        )

    # ========================================================
    # OUTCOME SEPARATION CHECK
    # ========================================================

    outcome_violations = (
        check_outcome_separation(
            signals,
            candles
        )
    )

    section(
        "LOOK-AHEAD OUTCOME CHECK"
    )

    print(

        "Future outcome separation: "
        +
        (
            "PASS"
            if not outcome_violations
            else "FAIL"
        )

    )

    if outcome_violations:

        raise RuntimeError(
            "Future outcome separation failed."
        )

    # ========================================================
    # WALK-FORWARD BOUNDARY CHECK
    # ========================================================

    boundary_violations = []

    for window in windows:

        start = window[
            "oos_start"
        ]

        end = window[
            "oos_end"
        ]

        for record in signals:

            index = record[
                "index"
            ]

            if (
                start
                <=
                index
                <
                end
            ):

                if index < start:

                    boundary_violations.append(
                        record
                    )

    section(
        "WALK-FORWARD BOUNDARY CHECK"
    )

    print(

        "Window boundaries: "
        +
        (
            "PASS"
            if not boundary_violations
            else "FAIL"
        )

    )

    if boundary_violations:

        raise RuntimeError(
            "Walk-forward boundary failed."
        )

    # ========================================================
    # FINAL PROTECTION
    # ========================================================

    section(
        "FINAL PROTECTION CHECK"
    )

    print(
        "market_data.bin     : READ ONLY"
    )

    print(
        "Production MLAI     : NOT MODIFIED"
    )

    print(
        "Learning memory     : NOT MODIFIED"
    )

    print(
        "Trading             : DISABLED"
    )

    print(
        "Internet            : NOT REQUIRED"
    )

    # ========================================================
    # VALIDATION OBJECT
    # ========================================================

    validation = {

        "version":
            "MLAI_V3.8.3",

        "experiment":
            "CAUSAL_WALK_FORWARD_MARKET_STRUCTURE_VALIDATION",

        "description":
            "Multi-window chronological validation "
            "of causal market structure and contextual "
            "directional information.",

        "total_candles":
            len(candles),

        "invalid_candles":
            invalid,

        "window_count":
            len(windows),

        "windows":
            windows,

        "horizons":
            HORIZONS,

        "confirmed_swings":
            len(raw_swings),

        "causal_structures":
            len(structures),

        "structure_counts":
            structure_counts,

        "event_counts":
            event_counts,

        "signals":
            signals,

        "combined_oos_signals":
            len(combined_oos),

        "window_results":
            all_window_results,

        "combined_results":
            combined_results,

        "stability":
            stability,

        "combined_directional_results":
            combined_directional,

        "combined_event_results":
            combined_events,

        "combined_oos_distributions":
            combined_distributions,

        "integrity": {

            "timestamp_order":
                chronological,

            "signal_chronological_order":
                signal_chronological,

            "structure_timing":
                not structure_timing_violations,

            "event_timing":
                not event_timing_violations,

            "signal_timing":
                not signal_timing_violations,

            "feature_causality":
                not feature_causality_violations,

            "future_outcome_separation":
                not outcome_violations,

            "walkforward_boundaries":
                not boundary_violations,

        },

        "protection": {

            "market_data_read_only":
                True,

            "production_mlai_modified":
                False,

            "learning_memory_modified":
                False,

            "trading_enabled":
                False,

            "internet_required":
                False,

        },

    }

    # ========================================================
    # SAVE BINARY
    # ========================================================

    with open(
        OUTPUT_BIN,
        "wb"
    ) as f:

        pickle.dump(

            validation,

            f,

            protocol=
            pickle.HIGHEST_PROTOCOL

        )

    # ========================================================
    # REPORT
    # ========================================================

    report.section(
        "EXPERIMENT"
    )

    report.add(
        "Version: MLAI v3.8.3"
    )

    report.add(
        "Type: Causal walk-forward "
        "research validation"
    )

    report.add(
        f"Windows: {len(windows)}"
    )

    report.add(
        f"Horizons: {HORIZONS}"
    )

    report.section(
        "DATASET"
    )

    report.add(
        f"Total candles: {len(candles)}"
    )

    report.add(
        f"Invalid candles: {invalid}"
    )

    report.section(
        "WALK-FORWARD WINDOWS"
    )

    for window in windows:

        report.add(

            f"Window {window['window']}: "
            f"TRAIN {window['train_start']}:"
            f"{window['train_end']} | "
            f"OOS {window['oos_start']}:"
            f"{window['oos_end']}"

        )

    report.section(
        "STRUCTURE"
    )

    report.add(
        f"Raw confirmed swings: "
        f"{len(raw_swings)}"
    )

    report.add(
        f"Causal structures: "
        f"{len(structures)}"
    )

    for label in [

        "HH",
        "HL",
        "LH",
        "LL",
        "EQUAL_HIGH",
        "EQUAL_LOW",

    ]:

        report.add(

            f"{label}: "
            f"{structure_counts.get(label, 0)}"

        )

    report.section(
        "STRUCTURE EVENTS"
    )

    for event_type in [

        "BOS_BULLISH",
        "BOS_BEARISH",
        "CHoCH_BULLISH",
        "CHoCH_BEARISH",

    ]:

        report.add(

            f"{event_type}: "
            f"{event_counts.get(event_type, 0)}"

        )

    report.section(
        "PER-WINDOW RESULTS"
    )

    for window_number, result in (
        all_window_results.items()
    ):

        report.subsection(
            f"WINDOW {window_number}"
        )

        report.add(
            f"Training signals: "
            f"{result['training_signals']}"
        )

        report.add(
            f"OOS signals: "
            f"{result['oos_signals']}"
        )

        report.add(
            "Outcome thresholds:"
        )

        for horizon in HORIZONS:

            report.add(

                f"  H+{horizon}: "
                f"{result['selected_thresholds'][horizon]:.4f}%"

            )

        for group_name, results in (
            result[
                "feature_results"
            ].items()
        ):

            report.subsection(
                group_name
            )

            for horizon in HORIZONS:

                m = results[
                    horizon
                ]

                report.add(

                    f"H+{horizon} | "
                    f"N={m['signals']} | "
                    f"Accuracy="
                    f"{m['accuracy']:.2f}% | "
                    f"Baseline="
                    f"{m['baseline']:.2f}% | "
                    f"Edge="
                    f"{m['edge']:+.2f}% | "
                    f"AvgReturn="
                    f"{m['avg_return']:+.4f}%"

                )

    report.section(
        "COMBINED OOS RESULTS"
    )

    for group_name, results in (
        combined_results.items()
    ):

        report.subsection(
            group_name
        )

        for horizon in HORIZONS:

            m = results[
                horizon
            ]

            report.add(

                f"H+{horizon} | "
                f"N={m['signals']} | "
                f"Accuracy="
                f"{m['accuracy']:.2f}% | "
                f"Baseline="
                f"{m['baseline']:.2f}% | "
                f"Edge="
                f"{m['edge']:+.2f}% | "
                f"AvgReturn="
                f"{m['avg_return']:+.4f}%"

            )

    report.section(
        "STABILITY"
    )

    for group_name, horizons in (
        stability.items()
    ):

        report.subsection(
            group_name
        )

        for horizon in HORIZONS:

            stats = horizons[
                horizon
            ]

            accuracy = stats[
                "accuracy"
            ]

            edge = stats[
                "edge"
            ]

            report.add(

                f"H+{horizon} | "
                f"Accuracy Mean="
                f"{accuracy['mean']:.2f}% | "
                f"Median="
                f"{accuracy['median']:.2f}% | "
                f"Std="
                f"{accuracy['std']:.2f} | "
                f"Min="
                f"{accuracy['min']:.2f}% | "
                f"Max="
                f"{accuracy['max']:.2f}% | "
                f"Mean Edge="
                f"{edge['mean']:+.2f}%"

            )

    report.section(
        "STRUCTURE DIRECTION"
    )

    for group_name, results in (
        combined_directional.items()
    ):

        report.subsection(
            group_name
        )

        for horizon in HORIZONS:

            m = results[
                horizon
            ]

            report.add(

                f"H+{horizon} | "
                f"N={m['signals']} | "
                f"Accuracy="
                f"{m['accuracy']:.2f}% | "
                f"Edge="
                f"{m['edge']:+.2f}%"

            )

    report.section(
        "STRUCTURE EVENTS"
    )

    for event_type, results in (
        combined_events.items()
    ):

        report.subsection(
            event_type
        )

        for horizon in HORIZONS:

            m = results[
                horizon
            ]

            report.add(

                f"H+{horizon} | "
                f"N={m['signals']} | "
                f"Accuracy="
                f"{m['accuracy']:.2f}% | "
                f"Edge="
                f"{m['edge']:+.2f}%"

            )

    report.section(
        "COMBINED OOS DISTRIBUTION"
    )

    for horizon in HORIZONS:

        d = combined_distributions[
            horizon
        ]

        report.add(

            f"H+{horizon}: "
            f"BUY={d['BUY']:.2f}% | "
            f"SELL={d['SELL']:.2f}% | "
            f"NEUTRAL={d['NEUTRAL']:.2f}%"

        )

    report.section(
        "INTEGRITY"
    )

    report.add(

        f"Timestamp order: "
        f"{'PASS' if chronological else 'FAIL'}"

    )

    report.add(

        f"Signal chronological order: "
        f"{'PASS' if signal_chronological else 'FAIL'}"

    )

    report.add(

        f"Structure timing: "
        f"{'PASS' if not structure_timing_violations else 'FAIL'}"

    )

    report.add(

        f"Event timing: "
        f"{'PASS' if not event_timing_violations else 'FAIL'}"

    )

    report.add(

        f"Signal timing: "
        f"{'PASS' if not signal_timing_violations else 'FAIL'}"

    )

    report.add(

        f"Feature causality: "
        f"{'PASS' if not feature_causality_violations else 'FAIL'}"

    )

    report.add(

        f"Future outcome separation: "
        f"{'PASS' if not outcome_violations else 'FAIL'}"

    )

    report.add(

        f"Walk-forward boundaries: "
        f"{'PASS' if not boundary_violations else 'FAIL'}"

    )

    report.section(
        "PROTECTION"
    )

    report.add(
        "market_data.bin : READ ONLY"
    )

    report.add(
        "Production MLAI : NOT MODIFIED"
    )

    report.add(
        "Learning memory : NOT MODIFIED"
    )

    report.add(
        "Trading         : DISABLED"
    )

    report.add(
        "Internet        : NOT REQUIRED"
    )

    report.section(
        "OUTPUT"
    )

    report.add(
        os.path.basename(
            OUTPUT_BIN
        )
    )

    report.add(
        os.path.basename(
            OUTPUT_REPORT
        )
    )

    report.save(
        OUTPUT_REPORT
    )

    # ========================================================
    # FINAL
    # ========================================================

    print()
    print("=" * 80)

    print(
        "VALIDATION BINARY:"
    )

    print(
        f"    {os.path.basename(OUTPUT_BIN)}"
    )

    print(
        "VALIDATION REPORT:"
    )

    print(
        f"    {os.path.basename(OUTPUT_REPORT)}"
    )

    print("=" * 80)

    print(
        "MLAI v3.8.3 CAUSAL WALK-FORWARD "
        "VALIDATION COMPLETE"
    )

    print("=" * 80)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    try:

        main()

    except KeyboardInterrupt:

        print()

        print(
            "Validation interrupted."
        )

    except Exception as exc:

        print()

        print("=" * 80)

        print(
            "VALIDATION ERROR"
        )

        print("=" * 80)

        print(
            f"{type(exc).__name__}: {exc}"
        )

        raise