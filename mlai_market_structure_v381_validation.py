# ============================================================
# MLAI v3.8.1 MARKET STRUCTURE PREDICTIVE VALIDATION
# ============================================================
#
# PURPOSE
# -------
# Research validation of whether confirmed market structure
# contains measurable future directional information.
#
# Features evaluated:
#
#     1. Market Structure
#     2. ATR / Volatility Regime
#     3. Momentum
#     4. Candle Behaviour
#     5. Structural Location
#     6. Combined Context
#
# Horizons:
#
#     H+4
#     H+8
#     H+16
#
# Chronological:
#
#     TRAINING = first 70%
#     OOS      = final 30%
#
# IMPORTANT
# ---------
# This is a research validation experiment.
#
# It is NOT:
#
#     - a trading system
#     - a production MLAI model
#     - financial advice
#
# market_data.bin is READ ONLY.
#
# ============================================================

import os
import math
import pickle
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
    "MLAI_V381_MARKET_STRUCTURE_PREDICTIVE_VALIDATION.bin"
)

OUTPUT_REPORT = os.path.join(
    ROOT,
    "MLAI_V381_MARKET_STRUCTURE_PREDICTIVE_VALIDATION_REPORT.md"
)

TRAIN_RATIO = 0.70

HORIZONS = [4, 8, 16]

SWING_LEFT = 3
SWING_RIGHT = 3

ATR_PERIOD = 14
MOMENTUM_PERIOD = 8

EQUAL_TOLERANCE_PCT = 0.03

RECENT_COUNT = 30

MIN_TRAIN_SAMPLES = 10

# Candidate directional thresholds.
# Selection is performed ONLY using training data.
RETURN_THRESHOLD_CANDIDATES = [
    0.00,
    0.01,
    0.02,
    0.03,
    0.05,
]


# ============================================================
# HELPERS
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


def pct_change(a, b):

    if b == 0:
        return 0.0

    return ((a - b) / b) * 100.0


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

        volume = raw[5] if len(raw) > 5 else 0

    else:

        return None

    try:

        op = float(op)
        hi = float(hi)
        lo = float(lo)
        cl = float(cl)
        volume = float(volume or 0)

        if not all(
            math.isfinite(x)
            for x in [op, hi, lo, cl]
        ):
            return None

        if op <= 0 or hi <= 0 or lo <= 0 or cl <= 0:
            return None

        if hi < max(op, cl):
            return None

        if lo > min(op, cl):
            return None

        if hi < lo:
            return None

        return {
            "index": index,
            "timestamp": timestamp,
            "open": op,
            "high": hi,
            "low": lo,
            "close": cl,
            "volume": volume,
        }

    except Exception:

        return None


# ============================================================
# DATA LOADING
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

    values = list(data.values())

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
            f"market_data.bin not found:\n{DATA_FILE}"
        )

    with open(
        DATA_FILE,
        "rb"
    ) as f:

        data = pickle.load(f)

    raw = extract_raw_candles(data)

    candles = []
    invalid = 0

    for i, item in enumerate(raw):

        candle = normalize_candle(
            item,
            i
        )

        if candle is None:

            invalid += 1
            continue

        candle["index"] = len(candles)

        candles.append(candle)

    return data, candles, invalid


# ============================================================
# TIMESTAMP
# ============================================================

def timestamp_numeric(value):

    if isinstance(value, (int, float)):
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
            c["timestamp"]
        )
        for c in candles
    ]

    for i in range(
        1,
        len(timestamps)
    ):

        if timestamps[i] < timestamps[i - 1]:
            return False

    return True


# ============================================================
# ATR
# ============================================================

def calculate_true_ranges(candles):

    result = []

    for i, candle in enumerate(candles):

        if i == 0:

            tr = (
                candle["high"]
                -
                candle["low"]
            )

        else:

            previous_close = candles[i - 1]["close"]

            tr = max(
                candle["high"] - candle["low"],
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

        result.append(tr)

    return result


def calculate_atr(
    candles,
    period=ATR_PERIOD
):

    tr = calculate_true_ranges(
        candles
    )

    atr = [None] * len(candles)

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
            atr[i] = mean(values)

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

        previous = candles[j]["close"]

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
# CANDLE BEHAVIOUR
# ============================================================

def candle_features(candle):

    op = candle["open"]
    hi = candle["high"]
    lo = candle["low"]
    cl = candle["close"]

    total_range = hi - lo

    if total_range <= 0:

        return {
            "body_pct": 0.0,
            "upper_wick_pct": 0.0,
            "lower_wick_pct": 0.0,
            "close_location": 0.5,
            "direction": 0,
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

    direction = (
        1
        if cl > op
        else (
            -1
            if cl < op
            else 0
        )
    )

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

    total = len(candles)

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
            x["candidate_index"]
        )
    )

    return swings


# ============================================================
# SWING CLEANING
# ============================================================

def clean_swings(swings):

    cleaned = []

    last_type = None

    for swing in swings:

        if (
            last_type is not None
            and swing["type"] == last_type
        ):

            previous = cleaned[-1]

            if swing["type"] == "SWING_HIGH":

                if swing["price"] > previous["price"]:

                    cleaned[-1] = swing

            else:

                if swing["price"] < previous["price"]:

                    cleaned[-1] = swing

        else:

            cleaned.append(
                dict(swing)
            )

            last_type = swing["type"]

    return cleaned


# ============================================================
# STRUCTURE CLASSIFICATION
# ============================================================

def classify_structures(
    swings
):

    previous_high = None
    previous_low = None

    result = []

    for swing in swings:

        item = dict(swing)

        if swing["type"] == "SWING_HIGH":

            if previous_high is None:

                label = "HH"

            else:

                diff = (
                    abs(
                        swing["price"]
                        -
                        previous_high["price"]
                    )
                    /
                    previous_high["price"]
                ) * 100.0

                if diff <= EQUAL_TOLERANCE_PCT:

                    label = "EQUAL_HIGH"

                elif (
                    swing["price"]
                    >
                    previous_high["price"]
                ):

                    label = "HH"

                else:

                    label = "LH"

            previous_high = swing

        else:

            if previous_low is None:

                label = "LL"

            else:

                diff = (
                    abs(
                        swing["price"]
                        -
                        previous_low["price"]
                    )
                    /
                    previous_low["price"]
                ) * 100.0

                if diff <= EQUAL_TOLERANCE_PCT:

                    label = "EQUAL_LOW"

                elif (
                    swing["price"]
                    >
                    previous_low["price"]
                ):

                    label = "HL"

                else:

                    label = "LL"

            previous_low = swing

        item["structure"] = label

        result.append(item)

    return result


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
        if x["confirmed_index"] <= index
    ]

    recent = available[-8:]

    labels = [
        x["structure"]
        for x in recent
    ]

    bullish = sum(
        1
        for x in labels
        if x in (
            "HH",
            "HL"
        )
    )

    bearish = sum(
        1
        for x in labels
        if x in (
            "LH",
            "LL"
        )
    )

    if bullish > bearish:

        direction = 1

    elif bearish > bullish:

        direction = -1

    else:

        direction = 0

    return {
        "labels": labels,
        "direction": direction,
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
        if x["confirmed_index"] <= index
    ][-10:]

    if len(recent) < 2:

        return {
            "position": 0.5,
            "regime": "MIDDLE",
        }

    prices = [
        x["price"]
        for x in recent
    ]

    high = max(prices)
    low = min(prices)

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

    if position >= 0.67:

        regime = "HIGH"

    elif position <= 0.33:

        regime = "LOW"

    else:

        regime = "MIDDLE"

    return {
        "position":
            max(
                0.0,
                min(
                    1.0,
                    position
                )
            ),

        "regime":
            regime,
    }


# ============================================================
# RAW FEATURE SNAPSHOT
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

    atr_pct = (
        atr_value / close * 100.0
        if close != 0
        else 0.0
    )

    recent_events = [
        e
        for e in events
        if e["index"] <= index
    ][-5:]

    event_direction = 0

    if recent_events:

        last = recent_events[-1]

        if last["direction"] == "BULLISH":
            event_direction = 1

        elif last["direction"] == "BEARISH":
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
# CHRONOLOGICAL STRUCTURE EVENT ENGINE
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

    swing_pointer = 0

    for index in range(
        len(candles)
    ):

        # ----------------------------------------------------
        # Add only swings confirmed by this candle.
        # ----------------------------------------------------

        while (
            swing_pointer
            <
            len(structures)
            and
            structures[
                swing_pointer
            ]["confirmed_index"]
            <= index
        ):

            swing = structures[
                swing_pointer
            ]

            if swing["type"] == "SWING_HIGH":

                active_high = swing

            else:

                active_low = swing

            swing_pointer += 1

        close = candles[index]["close"]

        # ----------------------------------------------------
        # Bullish break
        # ----------------------------------------------------

        if active_high is not None:

            key = active_high[
                "candidate_index"
            ]

            if (
                key not in broken_high
                and
                index >
                active_high[
                    "confirmed_index"
                ]
                and
                close >
                active_high["price"]
            ):

                if trend == "BULLISH":

                    event_name = "BOS_BULLISH"

                else:

                    event_name = "CHoCH_BULLISH"

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
                        active_high["price"],

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

                broken_high.add(key)

                trend = "BULLISH"

        # ----------------------------------------------------
        # Bearish break
        # ----------------------------------------------------

        if active_low is not None:

            key = active_low[
                "candidate_index"
            ]

            if (
                key not in broken_low
                and
                index >
                active_low[
                    "confirmed_index"
                ]
                and
                close <
                active_low["price"]
            ):

                if trend == "BEARISH":

                    event_name = "BOS_BEARISH"

                else:

                    event_name = "CHoCH_BEARISH"

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
                        active_low["price"],

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

                broken_low.add(key)

                trend = "BEARISH"

    events.sort(
        key=lambda x: x["index"]
    )

    return events


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
                    in ("HH", "HL")
                    else
                    "BEARISH"
                ),
        })

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

        for signal in signal_indexes[index]:

            record = dict(feature)

            record.update(
                signal
            )

            dataset.append(
                record
            )

    return dataset


# ============================================================
# OUTCOMES
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


def attach_outcomes(
    signals,
    candles,
    threshold
):

    result = []

    for signal in signals:

        index = signal["index"]

        record = dict(signal)

        record["outcomes"] = {}

        for horizon in HORIZONS:

            future_index = (
                index
                +
                horizon
            )

            if future_index >= len(candles):

                record["outcomes"][
                    horizon
                ] = None

                continue

            current = candles[index]["close"]

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

            record["outcomes"][
                horizon
            ] = {

                "label":
                    label,

                "return":
                    ret,

                "future_index":
                    future_index,
            }

        result.append(
            record
        )

    return result


# ============================================================
# TRAINING THRESHOLD SELECTION
# ============================================================

def majority_accuracy(
    records,
    horizon,
    threshold
):

    labels = []

    for record in records:

        index = record["index"]

        if index + horizon >= GLOBAL_CANDLE_COUNT:
            continue

        current = GLOBAL_CANDLES[
            index
        ]["close"]

        future = GLOBAL_CANDLES[
            index + horizon
        ]["close"]

        label = classify_outcome(
            current,
            future,
            threshold
        )

        labels.append(label)

    if not labels:
        return 0.0

    counts = {
        "BUY": labels.count("BUY"),
        "SELL": labels.count("SELL"),
        "NEUTRAL": labels.count("NEUTRAL"),
    }

    return (
        max(counts.values())
        /
        len(labels)
    ) * 100.0


def select_training_threshold(
    records,
    horizon
):

    best_threshold = 0.0
    best_balance = float("inf")
    best_samples = 0

    for threshold in RETURN_THRESHOLD_CANDIDATES:

        labels = []

        for record in records:

            index = record["index"]

            if (
                index + horizon
                >= GLOBAL_CANDLE_COUNT
            ):
                continue

            current = GLOBAL_CANDLES[
                index
            ]["close"]

            future = GLOBAL_CANDLES[
                index + horizon
            ]["close"]

            label = classify_outcome(
                current,
                future,
                threshold
            )

            labels.append(
                label
            )

        if len(labels) < MIN_TRAIN_SAMPLES:
            continue

        counts = {
            "BUY":
                labels.count("BUY"),

            "SELL":
                labels.count("SELL"),

            "NEUTRAL":
                labels.count("NEUTRAL"),
        }

        total = len(labels)

        buy_pct = (
            counts["BUY"]
            /
            total
        ) * 100.0

        sell_pct = (
            counts["SELL"]
            /
            total
        ) * 100.0

        # Prefer thresholds where BUY and SELL remain
        # reasonably represented rather than allowing
        # everything to become NEUTRAL.
        balance = abs(
            buy_pct - sell_pct
        )

        if balance < best_balance:

            best_balance = balance
            best_threshold = threshold
            best_samples = total

    return {
        "threshold":
            best_threshold,

        "samples":
            best_samples,

        "balance":
            best_balance
            if best_samples
            else None,
    }


# ============================================================
# BASELINE
# ============================================================

def outcome_distribution(
    records,
    candles,
    horizon,
    threshold
):

    counts = {
        "BUY": 0,
        "SELL": 0,
        "NEUTRAL": 0,
    }

    for record in records:

        index = record["index"]

        future_index = (
            index
            +
            horizon
        )

        if future_index >= len(candles):
            continue

        current = candles[index]["close"]

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
            "BUY": 0.0,
            "SELL": 0.0,
            "NEUTRAL": 0.0,
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
# TRAINING FEATURE THRESHOLDS
# ============================================================

def training_median(
    records,
    key
):

    values = [
        record[key]
        for record in records
        if isinstance(
            record.get(key),
            (int, float)
        )
        and math.isfinite(
            float(record[key])
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

    return {

        "atr_pct_median":
            training_median(
                training,
                "atr_pct"
            ),

        "momentum_median_abs":
            training_median(
                [
                    {
                        "x":
                            abs(
                                r["momentum"]
                            )
                    }
                    for r in training
                ],
                "x"
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
    # Market structure
    # --------------------------------------------------------

    if feature_name == "MARKET_STRUCTURE":

        return record[
            "structure_direction"
        ]

    # --------------------------------------------------------
    # ATR is NOT directional.
    #
    # It becomes a regime:
    #
    # LOW / NORMAL / HIGH
    #
    # and therefore contributes no BUY/SELL vote.
    # --------------------------------------------------------

    if feature_name == "ATR_VOLATILITY":

        atr = record["atr_pct"]

        median = thresholds[
            "atr_pct_median"
        ]

        if atr <= 0 or median <= 0:
            return 0

        # Volatility itself does not imply direction.
        return 0

    # --------------------------------------------------------
    # Momentum
    # --------------------------------------------------------

    if feature_name == "MOMENTUM":

        value = record["momentum"]

        if value > 0:
            return 1

        if value < 0:
            return -1

        return 0

    # --------------------------------------------------------
    # Candle behaviour
    # --------------------------------------------------------

    if feature_name == "CANDLE_BEHAVIOUR":

        location = record[
            "close_location"
        ]

        if location >= 0.60:
            return 1

        if location <= 0.40:
            return -1

        return 0

    # --------------------------------------------------------
    # Structural location
    #
    # Location itself is NOT direction.
    # --------------------------------------------------------

    if feature_name == "STRUCTURAL_LOCATION":

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

    total = sum(votes)

    if total > 0:
        return "BUY"

    if total < 0:
        return "SELL"

    return "NEUTRAL"


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

        index = record["index"]

        future_index = (
            index
            +
            horizon
        )

        if future_index >= len(candles):
            continue

        current = candles[index]["close"]

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
            "signals": 0,
            "accuracy": 0.0,
            "precision": 0.0,
            "recall": 0.0,
            "avg_return": 0.0,
            "baseline": baseline,
            "edge": 0.0,
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
        if x["prediction"] == "BUY"
    ]

    true_buy = [
        x
        for x in predicted_buy
        if x["actual"] == "BUY"
    ]

    actual_buy = [
        x
        for x in outputs
        if x["actual"] == "BUY"
    ]

    precision = (
        len(true_buy)
        /
        len(predicted_buy)
        *
        100.0
        if predicted_buy
        else 0.0
    )

    recall = (
        len(true_buy)
        /
        len(actual_buy)
        *
        100.0
        if actual_buy
        else 0.0
    )

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

        "precision":
            precision,

        "recall":
            recall,

        "avg_return":
            avg_return,

        "baseline":
            baseline,

        "edge":
            edge,
    }


# ============================================================
# SIGNAL FILTERS
# ============================================================

def filter_structure_records(
    records,
    bullish=None
):

    result = []

    for record in records:

        direction = record[
            "signal_direction"
        ]

        if bullish is True:

            if direction == "BULLISH":
                result.append(record)

        elif bullish is False:

            if direction == "BEARISH":
                result.append(record)

        else:

            result.append(record)

    return result


# ============================================================
# INTEGRITY CHECKS
# ============================================================

def structure_event_timing_check(
    events
):

    violations = []

    for event in events:

        if (
            event["confirmed_index"]
            >
            event["index"]
        ):

            violations.append(
                event
            )

    return violations


def lookahead_check(
    signals
):

    violations = []

    for signal in signals:

        index = signal["index"]

        for horizon in HORIZONS:

            outcome = signal[
                "outcomes"
            ].get(horizon)

            if outcome is None:
                continue

            if (
                outcome["future_index"]
                <=
                index
            ):

                violations.append({

                    "signal":
                        index,

                    "future":
                        outcome[
                            "future_index"
                        ],

                    "horizon":
                        horizon,
                })

    return violations


# ============================================================
# REPORT
# ============================================================

class Report:

    def __init__(self):

        self.lines = []

    def add(self, text=""):

        self.lines.append(
            str(text)
        )

    def section(self, title):

        self.add()
        self.add(
            "=" * 80
        )
        self.add(title)
        self.add(
            "=" * 80
        )

    def subsection(self, title):

        self.add()
        self.add(
            "-" * 80
        )
        self.add(title)
        self.add(
            "-" * 80
        )

    def save(self, filename):

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
# GLOBALS USED ONLY FOR TRAINING THRESHOLD CALCULATION
# ============================================================

GLOBAL_CANDLES = []
GLOBAL_CANDLE_COUNT = 0


# ============================================================
# MAIN
# ============================================================

def main():

    global GLOBAL_CANDLES
    global GLOBAL_CANDLE_COUNT

    report = Report()

    banner(
        "MLAI v3.8.1 MARKET STRUCTURE "
        "PREDICTIVE VALIDATION"
    )

    print(
        """
RESEARCH EXPERIMENT

This version specifically corrects:

    - ATR directional misuse
    - fake training threshold selection
    - directional-agreement double counting
    - structural-location directional misuse
    - swing cleaning/classification order
    - chronological structure-event processing

TRAINING:
    First 70%

OOS:
    Final 30%

The OOS period is not used to learn feature thresholds.
"""
    )

    report.add(
        "# MLAI v3.8.1 MARKET STRUCTURE "
        "PREDICTIVE VALIDATION"
    )

    report.add()
    report.add(
        "Research-only chronological validation."
    )

    # ========================================================
    # PROTECTION
    # ========================================================

    section(
        "PROTECTION CHECK"
    )

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
    print(
        "Internet        : NOT REQUIRED"
    )

    # ========================================================
    # LOAD DATA
    # ========================================================

    data, candles, invalid = load_market_data()

    GLOBAL_CANDLES = candles
    GLOBAL_CANDLE_COUNT = len(candles)

    section(
        "DATA QUALITY"
    )

    print(
        f"Data type              : "
        f"{type(data).__name__}"
    )

    print(
        f"Valid candles          : "
        f"{len(candles)}"
    )

    print(
        f"Invalid candles        : "
        f"{invalid}"
    )

    if len(candles) < 100:

        raise RuntimeError(
            "Not enough candles."
        )

    # ========================================================
    # CHRONOLOGY
    # ========================================================

    section(
        "CHRONOLOGICAL DATA CHECK"
    )

    chronological = chronological_check(
        candles
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
    # SPLIT
    # ========================================================

    split_index = int(
        len(candles)
        *
        TRAIN_RATIO
    )

    section(
        "CHRONOLOGICAL SPLIT"
    )

    print(
        f"Total candles       : "
        f"{len(candles)}"
    )

    print(
        f"Training candles    : "
        f"{split_index}"
    )

    print(
        f"OOS candles         : "
        f"{len(candles) - split_index}"
    )

    print(
        f"Training ratio      : "
        f"{TRAIN_RATIO * 100:.2f}%"
    )

    print(
        f"OOS ratio           : "
        f"{(1 - TRAIN_RATIO) * 100:.2f}%"
    )

    # ========================================================
    # FEATURES
    # ========================================================

    atr = calculate_atr(
        candles
    )

    momentum = calculate_momentum(
        candles
    )

    # ========================================================
    # SWINGS
    # ========================================================

    section(
        "CONFIRMED SWINGS"
    )

    raw_swings = detect_confirmed_swings(
        candles
    )

    print(
        f"Raw confirmed swings: "
        f"{len(raw_swings)}"
    )

    cleaned = clean_swings(
        raw_swings
    )

    structures = classify_structures(
        cleaned
    )

    print(
        f"Cleaned swings: "
        f"{len(structures)}"
    )

    highs = [
        x
        for x in structures
        if x["type"] == "SWING_HIGH"
    ]

    lows = [
        x
        for x in structures
        if x["type"] == "SWING_LOW"
    ]

    print(
        f"Swing highs: "
        f"{len(highs)}"
    )

    print(
        f"Swing lows : "
        f"{len(lows)}"
    )

    print()
    print(
        "Recent structure:"
    )

    for swing in structures[
        -RECENT_COUNT:
    ]:

        print(

            f"Candidate={swing['candidate_index']:6d} | "
            f"Confirmed={swing['confirmed_index']:6d} | "
            f"{swing['type']:<11} | "
            f"{swing['structure']:<11} | "
            f"Price={swing['price']:.5f}"
        )

    # ========================================================
    # EVENTS
    # ========================================================

    events = build_structure_events(
        candles,
        structures
    )

    section(
        "STRUCTURE EVENTS"
    )

    event_counts = {}

    for event in events:

        name = event["event"]

        event_counts[name] = (
            event_counts.get(
                name,
                0
            )
            +
            1
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
    # EVENT TIMING CHECK
    # ========================================================

    event_violations = (
        structure_event_timing_check(
            events
        )
    )

    section(
        "STRUCTURE EVENT TIMING CHECK"
    )

    if event_violations:

        print(
            "FAIL"
        )

        raise RuntimeError(
            "Structure event timing failed."
        )

    print(
        "PASS"
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

    print()
    print(
        f"Raw signal records: "
        f"{len(signals)}"
    )

    # ========================================================
    # PRELIMINARY ZERO-THRESHOLD DATASET
    # ========================================================

    preliminary = attach_outcomes(
        signals,
        candles,
        0.0
    )

    preliminary = [
        x
        for x in preliminary
        if x["index"] < split_index
    ]

    # ========================================================
    # TRAINING-ONLY THRESHOLD SELECTION
    # ========================================================

    section(
        "TRAINING-ONLY THRESHOLD SELECTION"
    )

    selected_thresholds = {}

    for horizon in HORIZONS:

        result = select_training_threshold(
            preliminary,
            horizon
        )

        selected_thresholds[
            horizon
        ] = result["threshold"]

        print(
            f"H+{horizon}: "
            f"{result['threshold']:.4f}% "
            f"(training samples="
            f"{result['samples']})"
        )

    # ========================================================
    # FINAL DATASET
    # ========================================================

    # Use one fixed threshold for all horizons only if
    # the experiment chooses a common classification.
    #
    # For this validation we use H+4's selected threshold
    # as the common signal classification threshold.
    #
    # This is frozen before OOS.

    common_threshold = (
        selected_thresholds[4]
    )

    print()
    print(
        f"Frozen common threshold: "
        f"{common_threshold:.4f}%"
    )

    final_signals = attach_outcomes(
        signals,
        candles,
        common_threshold
    )

    final_signals = [
        x
        for x in final_signals
        if x["index"] + 4 < len(candles)
    ]

    training = [
        x
        for x in final_signals
        if x["index"] < split_index
    ]

    oos = [
        x
        for x in final_signals
        if x["index"] >= split_index
    ]

    section(
        "SIGNAL DATASET"
    )

    print(
        f"Total signals    : "
        f"{len(final_signals)}"
    )

    print(
        f"Training signals  : "
        f"{len(training)}"
    )

    print(
        f"OOS signals       : "
        f"{len(oos)}"
    )

    # ========================================================
    # FEATURE THRESHOLDS
    # ========================================================

    feature_thresholds = (
        learn_feature_thresholds(
            training
        )
    )

    section(
        "TRAINING-LEARNED FEATURE THRESHOLDS"
    )

    for key, value in feature_thresholds.items():

        print(
            f"{key:<25}: "
            f"{value:.6f}"
        )

    # ========================================================
    # BASELINES
    # ========================================================

    section(
        "TRAINING-ONLY BASELINES"
    )

    baselines = {}

    for horizon in HORIZONS:

        baseline = majority_baseline(
            training,
            candles,
            horizon,
            common_threshold
        )

        baselines[horizon] = baseline

        print()
        print(
            f"H+{horizon}"
        )

        print(
            f"BUY     : "
            f"{baseline['BUY']:.2f}%"
        )

        print(
            f"SELL    : "
            f"{baseline['SELL']:.2f}%"
        )

        print(
            f"NEUTRAL : "
            f"{baseline['NEUTRAL']:.2f}%"
        )

        print(
            f"Majority: "
            f"{baseline['label']}"
        )

    # ========================================================
    # FEATURE GROUPS
    # ========================================================

    FEATURE_GROUPS = {

        "MARKET_STRUCTURE": [
            "MARKET_STRUCTURE"
        ],

        "STRUCTURE_MOMENTUM": [
            "MARKET_STRUCTURE",
            "MOMENTUM"
        ],

        "STRUCTURE_CANDLE": [
            "MARKET_STRUCTURE",
            "CANDLE_BEHAVIOUR"
        ],

        "STRUCTURE_LOCATION": [
            "MARKET_STRUCTURE",
            "STRUCTURAL_LOCATION"
        ],

        "STRUCTURE_MOMENTUM_CANDLE": [
            "MARKET_STRUCTURE",
            "MOMENTUM",
            "CANDLE_BEHAVIOUR"
        ],

        "STRUCTURE_FULL_CONTEXT": [
            "MARKET_STRUCTURE",
            "MOMENTUM",
            "CANDLE_BEHAVIOUR"
        ],
    }

    # ========================================================
    # OOS VALIDATION
    # ========================================================

    section(
        "OUT-OF-SAMPLE FEATURE VALIDATION"
    )

    all_results = {}

    for group_name, feature_group in FEATURE_GROUPS.items():

        subsection(
            group_name
        )

        all_results[
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
                oos,
                candles,
                feature_group,
                horizon,
                common_threshold,
                baseline,
                feature_thresholds
            )

            all_results[
                group_name
            ][horizon] = metrics

            print(
                f"H+{horizon} | "
                f"N={metrics['signals']} | "
                f"Accuracy="
                f"{metrics['accuracy']:.2f}% | "
                f"Precision="
                f"{metrics['precision']:.2f}% | "
                f"Recall="
                f"{metrics['recall']:.2f}% | "
                f"AvgReturn="
                f"{metrics['avg_return']:+.4f}% | "
                f"Baseline="
                f"{metrics['baseline']:.2f}% | "
                f"Edge="
                f"{metrics['edge']:+.2f}%"
            )

    # ========================================================
    # STRUCTURE DIRECTION
    # ========================================================

    section(
        "STRUCTURE-DIRECTION OOS RESULTS"
    )

    directional_results = {}

    groups = {

        "BULLISH_STRUCTURE":
            filter_structure_records(
                oos,
                True
            ),

        "BEARISH_STRUCTURE":
            filter_structure_records(
                oos,
                False
            ),

        "ALL_STRUCTURE":
            filter_structure_records(
                oos,
                None
            ),
    }

    for name, records in groups.items():

        subsection(
            name
        )

        directional_results[name] = {}

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
                common_threshold,
                baseline,
                feature_thresholds
            )

            directional_results[
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

    # ========================================================
    # EVENT RESULTS
    # ========================================================

    section(
        "STRUCTURE EVENT OOS RESULTS"
    )

    event_results = {}

    event_types = [
        "BOS_BULLISH",
        "BOS_BEARISH",
        "CHoCH_BULLISH",
        "CHoCH_BEARISH",
    ]

    for event_type in event_types:

        records = [
            x
            for x in oos
            if x["signal_type"]
            ==
            event_type
        ]

        subsection(
            event_type
        )

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
                common_threshold,
                baseline,
                feature_thresholds
            )

            event_results[
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
        "TRAINING OUTCOME DISTRIBUTION"
    )

    training_distributions = {}

    for horizon in HORIZONS:

        distribution = outcome_distribution(
            training,
            candles,
            horizon,
            common_threshold
        )

        training_distributions[
            horizon
        ] = distribution

        print()
        print(
            f"H+{horizon}: "
            f"BUY={distribution['BUY']:.2f}% | "
            f"SELL={distribution['SELL']:.2f}% | "
            f"NEUTRAL={distribution['NEUTRAL']:.2f}%"
        )

    section(
        "OOS OUTCOME DISTRIBUTION"
    )

    oos_distributions = {}

    for horizon in HORIZONS:

        distribution = outcome_distribution(
            oos,
            candles,
            horizon,
            common_threshold
        )

        oos_distributions[
            horizon
        ] = distribution

        print()
        print(
            f"H+{horizon}: "
            f"BUY={distribution['BUY']:.2f}% | "
            f"SELL={distribution['SELL']:.2f}% | "
            f"NEUTRAL={distribution['NEUTRAL']:.2f}%"
        )

    # ========================================================
    # LOOK-AHEAD CHECK
    # ========================================================

    section(
        "LOOK-AHEAD-BIAS CHECK"
    )

    violations = lookahead_check(
        final_signals
    )

    if violations:

        print(
            "FAIL"
        )

        raise RuntimeError(
            "Future outcome separation failed."
        )

    print(
        "PASS"
    )

    # ========================================================
    # OOS ORDER
    # ========================================================

    indices = [
        x["index"]
        for x in oos
    ]

    chronological_oos = (
        indices
        ==
        sorted(indices)
    )

    section(
        "OOS CHRONOLOGICAL INTEGRITY"
    )

    print(
        "PASS"
        if chronological_oos
        else "FAIL"
    )

    if not chronological_oos:

        raise RuntimeError(
            "OOS chronological order failed."
        )

    # ========================================================
    # STRUCTURE SUMMARY
    # ========================================================

    section(
        "STRUCTURE SUMMARY"
    )

    structure_counts = {}

    for swing in structures:

        label = swing[
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

    for label in [
        "HH",
        "HL",
        "LH",
        "LL",
        "EQUAL_HIGH",
        "EQUAL_LOW",
    ]:

        print(
            f"{label:<12}: "
            f"{structure_counts.get(label, 0)}"
        )

    # ========================================================
    # FINAL PROTECTION
    # ========================================================

    section(
        "FINAL PROTECTION CHECK"
    )

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

    print(
        "Model training  : RESEARCH THRESHOLD LEARNING ONLY"
    )

    # ========================================================
    # VALIDATION OBJECT
    # ========================================================

    validation = {

        "version":
            "MLAI_V3.8.1",

        "experiment":
            "MARKET_STRUCTURE_PREDICTIVE_VALIDATION",

        "total_candles":
            len(candles),

        "invalid_candles":
            invalid,

        "train_ratio":
            TRAIN_RATIO,

        "training_candles":
            split_index,

        "oos_candles":
            len(candles)
            -
            split_index,

        "training_signals":
            len(training),

        "oos_signals":
            len(oos),

        "horizons":
            HORIZONS,

        "training_selected_thresholds":
            selected_thresholds,

        "frozen_common_threshold":
            common_threshold,

        "feature_thresholds":
            feature_thresholds,

        "confirmed_swings":
            len(raw_swings),

        "cleaned_swings":
            len(structures),

        "structure_counts":
            structure_counts,

        "event_counts":
            event_counts,

        "training_baselines":
            baselines,

        "training_distributions":
            training_distributions,

        "oos_distributions":
            oos_distributions,

        "feature_results":
            all_results,

        "directional_results":
            directional_results,

        "event_results":
            event_results,

        "integrity": {

            "timestamp_order":
                chronological,

            "structure_event_timing":
                len(
                    event_violations
                ) == 0,

            "oos_signal_order":
                chronological_oos,

            "future_outcome_separation":
                len(
                    violations
                ) == 0,
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

        "signals":
            final_signals,
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
            protocol=pickle.HIGHEST_PROTOCOL
        )

    # ========================================================
    # REPORT
    # ========================================================

    report.section(
        "DATASET"
    )

    report.add(
        f"Total candles: {len(candles)}"
    )

    report.add(
        f"Training candles: {split_index}"
    )

    report.add(
        f"OOS candles: "
        f"{len(candles) - split_index}"
    )

    report.add(
        f"Training signals: "
        f"{len(training)}"
    )

    report.add(
        f"OOS signals: "
        f"{len(oos)}"
    )

    report.section(
        "TRAINING-LEARNED THRESHOLDS"
    )

    for horizon in HORIZONS:

        report.add(
            f"H+{horizon}: "
            f"{selected_thresholds[horizon]:.4f}%"
        )

    report.add(
        f"Frozen common threshold: "
        f"{common_threshold:.4f}%"
    )

    report.section(
        "FEATURE THRESHOLDS"
    )

    for key, value in feature_thresholds.items():

        report.add(
            f"{key}: {value:.6f}"
        )

    report.section(
        "OOS FEATURE VALIDATION"
    )

    for group_name, results in all_results.items():

        report.subsection(
            group_name
        )

        for horizon in HORIZONS:

            m = results[horizon]

            report.add(
                f"H+{horizon} | "
                f"N={m['signals']} | "
                f"Accuracy={m['accuracy']:.2f}% | "
                f"Precision={m['precision']:.2f}% | "
                f"Recall={m['recall']:.2f}% | "
                f"AvgReturn={m['avg_return']:+.4f}% | "
                f"Baseline={m['baseline']:.2f}% | "
                f"Edge={m['edge']:+.2f}%"
            )

    report.section(
        "STRUCTURE EVENTS"
    )

    for event_type in event_types:

        report.subsection(
            event_type
        )

        for horizon in HORIZONS:

            m = event_results[
                event_type
            ][horizon]

            report.add(
                f"H+{horizon} | "
                f"N={m['signals']} | "
                f"Accuracy={m['accuracy']:.2f}% | "
                f"Edge={m['edge']:+.2f}%"
            )

    report.section(
        "INTEGRITY"
    )

    report.add(
        f"Timestamp order: "
        f"{'PASS' if chronological else 'FAIL'}"
    )

    report.add(
        f"Structure event timing: "
        f"{'PASS' if not event_violations else 'FAIL'}"
    )

    report.add(
        f"OOS signal order: "
        f"{'PASS' if chronological_oos else 'FAIL'}"
    )

    report.add(
        f"Future outcome separation: "
        f"{'PASS' if not violations else 'FAIL'}"
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
        "MLAI v3.8.1 MARKET STRUCTURE "
        "PREDICTIVE VALIDATION COMPLETE"
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
        print("VALIDATION ERROR")
        print("=" * 80)

        print(
            f"{type(exc).__name__}: {exc}"
        )

        raise