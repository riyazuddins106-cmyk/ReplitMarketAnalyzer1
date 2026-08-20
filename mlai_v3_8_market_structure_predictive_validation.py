# ============================================================
# MLAI v3.8 MARKET STRUCTURE PREDICTIVE VALIDATION
# ============================================================
#
# PURPOSE
# -------
# Determine whether confirmed market structure contains
# measurable future directional information and whether that
# information improves when combined with:
#
#     Market Structure
#     ATR / Volatility
#     Momentum
#     Candle Behaviour
#     Structural Location
#     Directional Agreement
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
import json
import math
import pickle
import statistics
from datetime import datetime, timezone


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
    "MLAI_V38_MARKET_STRUCTURE_PREDICTIVE_VALIDATION.bin"
)

OUTPUT_REPORT = os.path.join(
    ROOT,
    "MLAI_V38_MARKET_STRUCTURE_PREDICTIVE_VALIDATION_REPORT.md"
)

TRAIN_RATIO = 0.70

HORIZONS = [4, 8, 16]

SWING_LEFT = 3
SWING_RIGHT = 3

ATR_PERIOD = 14
MOMENTUM_PERIOD = 8

# Minimum return expressed as a percentage for directional
# classification.
#
# The threshold is deliberately small because this experiment
# is measuring directional information rather than trading
# profitability.
#
# Training-only threshold selection is used.
RETURN_THRESHOLD_CANDIDATES = [
    0.00,
    0.01,
    0.02,
    0.03,
    0.05,
]

# Equal-high / equal-low tolerance.
EQUAL_TOLERANCE_PCT = 0.03

# Number of recent records printed.
RECENT_COUNT = 30

# Minimum samples needed for feature threshold estimation.
MIN_TRAIN_FEATURE_SAMPLES = 10


# ============================================================
# SAFE MEAN
# ============================================================
#
# IMPORTANT FIX
# -------------
# The previous v3.8 crashed because mean() received a
# generator and attempted len(generator).
#
# This implementation converts any iterable to a list first.
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


def safe_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default


def pct_change(a, b):
    if b == 0:
        return 0.0

    return ((a - b) / b) * 100.0


def clamp(value, low, high):
    return max(low, min(high, value))


# ============================================================
# CONSOLE HELPERS
# ============================================================

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
    """
    Supports common market_data.bin candle formats.
    """

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
            ["open", "o"],
            None
        )

        hi = find_first(
            raw,
            ["high", "h"],
            None
        )

        lo = find_first(
            raw,
            ["low", "l"],
            None
        )

        cl = find_first(
            raw,
            ["close", "c"],
            None
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
    """
    Attempts to locate candle arrays inside common dictionary
    structures.
    """

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

    # Some market_data.bin files are dictionaries whose values
    # themselves form candle records.
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
# TIMESTAMP SORT / VALIDATION
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
                value.replace("Z", "+00:00")
            ).timestamp()
        except Exception:
            return 0.0

    return 0.0


def chronological_check(candles):

    timestamps = [
        timestamp_numeric(c["timestamp"])
        for c in candles
    ]

    for i in range(1, len(timestamps)):

        if timestamps[i] < timestamps[i - 1]:
            return False

    return True


# ============================================================
# TRUE RANGE / ATR
# ============================================================

def calculate_true_ranges(candles):

    tr = []

    for i, candle in enumerate(candles):

        if i == 0:

            value = (
                candle["high"]
                - candle["low"]
            )

        else:

            previous_close = candles[i - 1]["close"]

            value = max(
                candle["high"] - candle["low"],
                abs(
                    candle["high"]
                    - previous_close
                ),
                abs(
                    candle["low"]
                    - previous_close
                ),
            )

        tr.append(value)

    return tr


def calculate_atr(candles, period=ATR_PERIOD):

    tr = calculate_true_ranges(candles)

    atr = [None] * len(candles)

    for i in range(len(candles)):

        start = max(
            0,
            i - period + 1
        )

        values = tr[start:i + 1]

        if values:
            atr[i] = mean(values)

    return atr


# ============================================================
# MOMENTUM
# ============================================================

def calculate_momentum(candles, period=MOMENTUM_PERIOD):

    result = [0.0] * len(candles)

    for i in range(len(candles)):

        j = i - period

        if j < 0:
            result[i] = 0.0
            continue

        previous = candles[j]["close"]

        if previous == 0:
            result[i] = 0.0
        else:
            result[i] = (
                (candles[i]["close"] - previous)
                / previous
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
            "candle_direction": 0,
        }

    body = abs(cl - op)

    upper_wick = hi - max(op, cl)
    lower_wick = min(op, cl) - lo

    close_location = (
        (cl - lo)
        / total_range
    )

    direction = 1 if cl > op else (
        -1 if cl < op else 0
    )

    return {
        "body_pct": body / total_range,
        "upper_wick_pct": upper_wick / total_range,
        "lower_wick_pct": lower_wick / total_range,
        "close_location": close_location,
        "candle_direction": direction,
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

            if candles[j]["high"] >= current["high"]:
                is_high = False

            if candles[j]["low"] <= current["low"]:
                is_low = False

        confirmation_index = i + right

        if is_high:

            swings.append({
                "candidate_index": i,
                "confirmed_index": confirmation_index,
                "type": "SWING_HIGH",
                "price": current["high"],
                "timestamp": candles[i]["timestamp"],
            })

        if is_low:

            swings.append({
                "candidate_index": i,
                "confirmed_index": confirmation_index,
                "type": "SWING_LOW",
                "price": current["low"],
                "timestamp": candles[i]["timestamp"],
            })

    swings.sort(
        key=lambda x: (
            x["confirmed_index"],
            x["candidate_index"]
        )
    )

    return swings


# ============================================================
# MARKET STRUCTURE CLASSIFICATION
# ============================================================

def classify_structure(
    current,
    previous
):

    if previous is None:
        return (
            "HH"
            if current["type"] == "SWING_HIGH"
            else "LL"
        )

    current_price = current["price"]
    previous_price = previous["price"]

    if previous_price == 0:
        return (
            "HH"
            if current["type"] == "SWING_HIGH"
            else "LL"
        )

    difference_pct = abs(
        current_price - previous_price
    ) / previous_price * 100.0

    if difference_pct <= EQUAL_TOLERANCE_PCT:

        if current["type"] == "SWING_HIGH":
            return "EQUAL_HIGH"

        return "EQUAL_LOW"

    if current["type"] == "SWING_HIGH":

        return (
            "HH"
            if current_price > previous_price
            else "LH"
        )

    return (
        "HL"
        if current_price > previous_price
        else "LL"
    )


def build_market_structure(
    confirmed_swings
):

    previous_high = None
    previous_low = None

    structures = []

    for swing in confirmed_swings:

        if swing["type"] == "SWING_HIGH":

            label = classify_structure(
                swing,
                previous_high
            )

            previous_high = swing

        else:

            label = classify_structure(
                swing,
                previous_low
            )

            previous_low = swing

        record = dict(swing)
        record["structure"] = label

        structures.append(record)

    return structures


# ============================================================
# REMOVE SAME-TYPE DUPLICATES
# ============================================================

def clean_swings(structures):

    cleaned = []

    last_type = None

    for swing in structures:

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

            cleaned.append(swing)
            last_type = swing["type"]

    return cleaned


# ============================================================
# STRUCTURE EVENTS
# ============================================================

def build_structure_events(
    candles,
    structures
):

    events = []

    last_high = None
    last_low = None

    broken_high_indices = set()
    broken_low_indices = set()

    # Determine trend from latest structural sequence.
    current_trend = None

    for swing in structures:

        if swing["type"] == "SWING_HIGH":
            last_high = swing

        elif swing["type"] == "SWING_LOW":
            last_low = swing

        start = swing["confirmed_index"] + 1

        if start >= len(candles):
            continue

        for i in range(
            start,
            len(candles)
        ):

            close = candles[i]["close"]

            # ------------------------------------------------
            # Bullish break
            # ------------------------------------------------

            if (
                last_high is not None
                and last_high["candidate_index"]
                not in broken_high_indices
                and close > last_high["price"]
            ):

                event_type = (
                    "BOS_BULLISH"
                    if current_trend == "BULLISH"
                    else "CHoCH_BULLISH"
                )

                events.append({
                    "index": i,
                    "event": event_type,
                    "direction": "BULLISH",
                    "close": close,
                    "broken_price": last_high["price"],
                    "swing_index": last_high["candidate_index"],
                    "confirmed_index": last_high["confirmed_index"],
                    "timestamp": candles[i]["timestamp"],
                })

                broken_high_indices.add(
                    last_high["candidate_index"]
                )

                current_trend = "BULLISH"

            # ------------------------------------------------
            # Bearish break
            # ------------------------------------------------

            if (
                last_low is not None
                and last_low["candidate_index"]
                not in broken_low_indices
                and close < last_low["price"]
            ):

                event_type = (
                    "BOS_BEARISH"
                    if current_trend == "BEARISH"
                    else "CHoCH_BEARISH"
                )

                events.append({
                    "index": i,
                    "event": event_type,
                    "direction": "BEARISH",
                    "close": close,
                    "broken_price": last_low["price"],
                    "swing_index": last_low["candidate_index"],
                    "confirmed_index": last_low["confirmed_index"],
                    "timestamp": candles[i]["timestamp"],
                })

                broken_low_indices.add(
                    last_low["candidate_index"]
                )

                current_trend = "BEARISH"

    # Remove duplicate event indexes/types.
    unique = {}
    for event in events:

        key = (
            event["index"],
            event["event"]
        )

        unique[key] = event

    result = list(unique.values())

    result.sort(
        key=lambda x: x["index"]
    )

    return result


# ============================================================
# STRUCTURAL CONTEXT
# ============================================================

def latest_structure_at(
    structures,
    index
):

    available = [
        x for x in structures
        if x["confirmed_index"] <= index
    ]

    if not available:
        return None

    return available[-1]


def structure_context(
    structures,
    index
):

    available = [
        x for x in structures
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
        if x in ("HH", "HL")
    )

    bearish = sum(
        1
        for x in labels
        if x in ("LH", "LL")
    )

    if bullish > bearish:
        direction = "BULLISH"
    elif bearish > bullish:
        direction = "BEARISH"
    else:
        direction = "NEUTRAL"

    return {
        "recent_labels": labels,
        "bullish_count": bullish,
        "bearish_count": bearish,
        "direction": direction,
    }


# ============================================================
# STRUCTURAL LOCATION
# ============================================================

def calculate_structural_location(
    candles,
    structures,
    index
):

    recent = [
        x for x in structures
        if x["confirmed_index"] <= index
    ][-10:]

    if len(recent) < 2:
        return {
            "location": 0.5,
            "range_position": 0.5,
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
            candles[index]["close"] - low
        ) / (high - low)

    return {
        "location": position,
        "range_position": position,
    }


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

    cf = candle_features(candle)

    context = structure_context(
        structures,
        index
    )

    location = calculate_structural_location(
        candles,
        structures,
        index
    )

    recent_events = [
        e
        for e in events
        if e["index"] <= index
    ][-5:]

    event_direction = 0

    if recent_events:

        last_event = recent_events[-1]

        if last_event["direction"] == "BULLISH":
            event_direction = 1
        elif last_event["direction"] == "BEARISH":
            event_direction = -1

    structure_direction = 0

    if context["direction"] == "BULLISH":
        structure_direction = 1
    elif context["direction"] == "BEARISH":
        structure_direction = -1

    momentum_direction = 0

    if momentum[index] > 0:
        momentum_direction = 1
    elif momentum[index] < 0:
        momentum_direction = -1

    candle_direction = cf["candle_direction"]

    votes = [
        structure_direction,
        event_direction,
        momentum_direction,
        candle_direction,
    ]

    bullish_votes = sum(
        1 for x in votes if x > 0
    )

    bearish_votes = sum(
        1 for x in votes if x < 0
    )

    if bullish_votes > bearish_votes:
        agreement = "BULLISH"
    elif bearish_votes > bullish_votes:
        agreement = "BEARISH"
    else:
        agreement = "NEUTRAL"

    return {
        "index": index,
        "price": candle["close"],
        "atr": atr[index] or 0.0,
        "momentum": momentum[index],

        "body_pct": cf["body_pct"],
        "upper_wick_pct": cf["upper_wick_pct"],
        "lower_wick_pct": cf["lower_wick_pct"],
        "close_location": cf["close_location"],

        "structure_direction": structure_direction,
        "event_direction": event_direction,

        "structural_location":
            location["location"],

        "bullish_votes": bullish_votes,
        "bearish_votes": bearish_votes,

        "directional_agreement":
            agreement,
    }


# ============================================================
# OUTCOME CLASSIFICATION
# ============================================================

def classify_outcome(
    current_close,
    future_close,
    threshold_pct
):

    if current_close == 0:
        return "NEUTRAL"

    change = (
        (future_close - current_close)
        / current_close
    ) * 100.0

    if change > threshold_pct:
        return "BUY"

    if change < -threshold_pct:
        return "SELL"

    return "NEUTRAL"


def outcome_return(
    current_close,
    future_close
):

    if current_close == 0:
        return 0.0

    return (
        (future_close - current_close)
        / current_close
    ) * 100.0


# ============================================================
# BUILD SIGNAL DATASET
# ============================================================

def build_signal_dataset(
    candles,
    structures,
    events,
    atr,
    momentum
):

    signals = {}

    # --------------------------------------------------------
    # Structure signals
    # --------------------------------------------------------

    for swing in structures:

        index = swing["confirmed_index"]

        if index >= len(candles):
            continue

        label = swing["structure"]

        if label not in (
            "HH",
            "HL",
            "LH",
            "LL",
        ):
            continue

        if index not in signals:
            signals[index] = []

        signals[index].append({
            "signal_type": label,
            "direction":
                "BULLISH"
                if label in ("HH", "HL")
                else "BEARISH",
            "index": index,
            "price": candles[index]["close"],
        })

    # --------------------------------------------------------
    # Structure events
    # --------------------------------------------------------

    for event in events:

        index = event["index"]

        if index >= len(candles):
            continue

        if index not in signals:
            signals[index] = []

        signals[index].append({
            "signal_type":
                event["event"],
            "direction":
                event["direction"],
            "index": index,
            "price":
                candles[index]["close"],
        })

    # --------------------------------------------------------
    # Flatten and build features
    # --------------------------------------------------------

    dataset = []

    for index in sorted(signals):

        feature = build_feature_snapshot(
            index,
            candles,
            structures,
            events,
            atr,
            momentum
        )

        for signal in signals[index]:

            record = dict(feature)

            record.update({
                "signal_type":
                    signal["signal_type"],
                "signal_direction":
                    signal["direction"],
            })

            dataset.append(record)

    return dataset


# ============================================================
# OUTCOME ATTACHMENT
# ============================================================

def attach_outcomes(
    signals,
    candles,
    threshold_pct
):

    result = []

    for signal in signals:

        index = signal["index"]

        record = dict(signal)

        record["outcomes"] = {}

        for horizon in HORIZONS:

            future_index = index + horizon

            if future_index >= len(candles):

                record["outcomes"][horizon] = None
                continue

            current_close = candles[index]["close"]
            future_close = candles[future_index]["close"]

            ret = outcome_return(
                current_close,
                future_close
            )

            label = classify_outcome(
                current_close,
                future_close,
                threshold_pct
            )

            record["outcomes"][horizon] = {
                "label": label,
                "return": ret,
                "future_index": future_index,
            }

        result.append(record)

    return result


# ============================================================
# TRAINING BASELINE
# ============================================================

def outcome_distribution(
    records,
    horizon
):

    counts = {
        "BUY": 0,
        "SELL": 0,
        "NEUTRAL": 0,
    }

    for record in records:

        outcome = record["outcomes"].get(horizon)

        if outcome is None:
            continue

        label = outcome["label"]

        if label in counts:
            counts[label] += 1

    total = sum(counts.values())

    if total == 0:
        return {
            "BUY": 0.0,
            "SELL": 0.0,
            "NEUTRAL": 0.0,
        }

    return {
        key:
            counts[key] / total * 100.0
        for key in counts
    }


def majority_baseline(
    records,
    horizon
):

    distribution = outcome_distribution(
        records,
        horizon
    )

    label = max(
        distribution,
        key=distribution.get
    )

    return {
        "label": label,
        "BUY": distribution["BUY"],
        "SELL": distribution["SELL"],
        "NEUTRAL": distribution["NEUTRAL"],
    }


# ============================================================
# FEATURE SCORING
# ============================================================

def feature_direction(
    record,
    feature_name
):

    if feature_name == "MARKET_STRUCTURE":

        return record["structure_direction"]

    if feature_name == "ATR_VOLATILITY":

        return 1 if record["atr"] > 0 else 0

    if feature_name == "MOMENTUM":

        return (
            1
            if record["momentum"] > 0
            else (
                -1
                if record["momentum"] < 0
                else 0
            )
        )

    if feature_name == "CANDLE_BEHAVIOUR":

        return (
            1
            if record["close_location"] >= 0.60
            else (
                -1
                if record["close_location"] <= 0.40
                else 0
            )
        )

    if feature_name == "STRUCTURAL_LOCATION":

        return (
            1
            if record["structural_location"] >= 0.60
            else (
                -1
                if record["structural_location"] <= 0.40
                else 0
            )
        )

    if feature_name == "DIRECTIONAL_AGREEMENT":

        agreement = record[
            "directional_agreement"
        ]

        if agreement == "BULLISH":
            return 1

        if agreement == "BEARISH":
            return -1

        return 0

    return 0


FEATURES = [
    "MARKET_STRUCTURE",
    "ATR_VOLATILITY",
    "MOMENTUM",
    "CANDLE_BEHAVIOUR",
    "STRUCTURAL_LOCATION",
    "DIRECTIONAL_AGREEMENT",
]


# ============================================================
# FEATURE COMBINATIONS
# ============================================================

FEATURE_GROUPS = {
    "ALL_STRUCTURE": [
        "MARKET_STRUCTURE"
    ],

    "STRUCTURE_ATR": [
        "MARKET_STRUCTURE",
        "ATR_VOLATILITY",
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

    "STRUCTURE_AGREEMENT": [
        "MARKET_STRUCTURE",
        "DIRECTIONAL_AGREEMENT",
    ],

    "STRUCTURE_ATR_MOMENTUM": [
        "MARKET_STRUCTURE",
        "ATR_VOLATILITY",
        "MOMENTUM",
    ],

    "STRUCTURE_FULL_CONTEXT": [
        "MARKET_STRUCTURE",
        "ATR_VOLATILITY",
        "MOMENTUM",
        "CANDLE_BEHAVIOUR",
        "STRUCTURAL_LOCATION",
        "DIRECTIONAL_AGREEMENT",
    ],
}


# ============================================================
# SIGNAL PREDICTION
# ============================================================

def predict_direction(
    record,
    feature_group
):

    votes = []

    for feature in feature_group:

        direction = feature_direction(
            record,
            feature
        )

        if direction != 0:
            votes.append(direction)

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
    feature_group,
    horizon,
    baseline_buy
):

    outcomes = []

    for record in records:

        outcome = record["outcomes"].get(
            horizon
        )

        if outcome is None:
            continue

        prediction = predict_direction(
            record,
            feature_group
        )

        outcomes.append({
            "prediction": prediction,
            "actual": outcome["label"],
            "return": outcome["return"],
        })

    if not outcomes:

        return {
            "signals": 0,
            "accuracy": 0.0,
            "precision": 0.0,
            "recall": 0.0,
            "avg_return": 0.0,
            "baseline": baseline_buy,
            "edge": 0.0,
        }

    correct = sum(
        1
        for x in outcomes
        if x["prediction"] == x["actual"]
    )

    accuracy = (
        correct
        / len(outcomes)
        * 100.0
    )

    predicted_positive = [
        x
        for x in outcomes
        if x["prediction"] == "BUY"
    ]

    true_positive = [
        x
        for x in predicted_positive
        if x["actual"] == "BUY"
    ]

    actual_positive = [
        x
        for x in outcomes
        if x["actual"] == "BUY"
    ]

    if predicted_positive:
        precision = (
            len(true_positive)
            / len(predicted_positive)
            * 100.0
        )
    else:
        precision = 0.0

    if actual_positive:
        recall = (
            len(true_positive)
            / len(actual_positive)
            * 100.0
        )
    else:
        recall = 0.0

    # IMPORTANT:
    #
    # The previous v3.8 implementation crashed here because
    # a generator was passed to mean().
    #
    # mean() now safely accepts generators.

    avg_return = mean(
        x["return"]
        for x in outcomes
    )

    baseline = baseline_buy

    edge = accuracy - baseline

    return {
        "signals": len(outcomes),
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "avg_return": avg_return,
        "baseline": baseline,
        "edge": edge,
    }


# ============================================================
# DIRECTIONAL STRUCTURE RESULTS
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
# REPORT FORMATTERS
# ============================================================

def fmt_pct(value):
    return f"{value:+.4f}%"


def print_metrics(
    name,
    metrics
):

    print(
        f"{name:<28}"
        f"| Signals={metrics['signals']:<5}"
        f"| Accuracy={metrics['accuracy']:.2f}%"
        f"| Precision={metrics['precision']:.2f}%"
        f"| Recall={metrics['recall']:.2f}%"
        f"| AvgReturn={fmt_pct(metrics['avg_return'])}"
        f"| Baseline={metrics['baseline']:.2f}%"
        f"| Edge={fmt_pct(metrics['edge'])}"
    )


# ============================================================
# LOOK-AHEAD CHECK
# ============================================================

def lookahead_check(
    signals
):

    violations = []

    for signal in signals:

        signal_index = signal["index"]

        for horizon in HORIZONS:

            outcome = signal["outcomes"].get(
                horizon
            )

            if outcome is None:
                continue

            future_index = outcome[
                "future_index"
            ]

            if future_index <= signal_index:

                violations.append({
                    "signal": signal_index,
                    "future": future_index,
                    "horizon": horizon,
                })

    return violations


# ============================================================
# STRUCTURE EVENT LOOK-AHEAD CHECK
# ============================================================

def structure_event_timing_check(
    events
):

    violations = []

    for event in events:

        if (
            event["confirmed_index"]
            > event["index"]
        ):
            violations.append(event)

    return violations


# ============================================================
# CHRONOLOGICAL SPLIT
# ============================================================

def chronological_split(
    records,
    total_candles
):

    split_index = int(
        total_candles * TRAIN_RATIO
    )

    training = [
        x
        for x in records
        if x["index"] < split_index
    ]

    oos = [
        x
        for x in records
        if x["index"] >= split_index
    ]

    return (
        split_index,
        training,
        oos,
    )


# ============================================================
# REPORT STORAGE
# ============================================================

class Report:

    def __init__(self):
        self.lines = []

    def add(self, text=""):
        self.lines.append(str(text))

    def section(self, title):
        self.add()
        self.add("=" * 80)
        self.add(title)
        self.add("=" * 80)

    def subsection(self, title):
        self.add()
        self.add("-" * 80)
        self.add(title)
        self.add("-" * 80)

    def save(self, filename):
        with open(
            filename,
            "w",
            encoding="utf-8"
        ) as f:
            f.write(
                "\n".join(self.lines)
            )


# ============================================================
# MAIN
# ============================================================

def main():

    report = Report()

    banner(
        "MLAI v3.8 MARKET STRUCTURE PREDICTIVE VALIDATION"
    )

    print(
        """
PURPOSE
-------

Determine whether confirmed market structure contains
measurable future directional information and whether that
information improves when combined with:

    Market Structure
    ATR / Volatility
    Momentum
    Candle Behaviour
    Structural Location
    Directional Agreement

Future horizons:

    H+4
    H+8
    H+16

The experiment is chronological.

TRAINING:
    First 70%

OUT-OF-SAMPLE:
    Final 30%

The OOS period is NOT used to determine thresholds,
baselines, or signal definitions.

This is a research experiment.

It is NOT:

    - a trading system
    - a production MLAI model
    - financial advice
"""
    )

    report.add(
        "# MLAI v3.8 MARKET STRUCTURE "
        "PREDICTIVE VALIDATION"
    )

    report.add()
    report.add(
        "Research-only chronological validation."
    )

    # --------------------------------------------------------
    # Protection
    # --------------------------------------------------------

    section("PROTECTION CHECK")

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
        "Model training  : DISABLED"
    )
    print(
        "Internet        : NOT REQUIRED"
    )
    print(
        "Output          : Separate validation files only"
    )

    # --------------------------------------------------------
    # Load
    # --------------------------------------------------------

    data, candles, invalid = load_market_data()

    print(
        f"\nData type: {type(data).__name__}"
    )

    print(
        f"Total raw candles: "
        f"{len(candles) + invalid}"
    )

    report.section(
        "PROTECTION CHECK"
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
        "Model training  : DISABLED"
    )
    report.add(
        "Internet        : NOT REQUIRED"
    )

    # --------------------------------------------------------
    # Data quality
    # --------------------------------------------------------

    section("DATA QUALITY")

    print(
        f"Valid OHLC candles: {len(candles)}"
    )

    print(
        f"Invalid candles skipped: {invalid}"
    )

    report.section("DATA QUALITY")
    report.add(
        f"Valid OHLC candles: {len(candles)}"
    )
    report.add(
        f"Invalid candles skipped: {invalid}"
    )

    if len(candles) < 100:
        raise RuntimeError(
            "Not enough candles for validation."
        )

    # --------------------------------------------------------
    # Chronological check
    # --------------------------------------------------------

    section(
        "CHRONOLOGICAL DATA CHECK"
    )

    chronological = chronological_check(
        candles
    )

    print(
        "Timestamp order: "
        + ("PASS" if chronological else "FAIL")
    )

    if not chronological:
        raise RuntimeError(
            "Timestamp order failed."
        )

    # --------------------------------------------------------
    # ATR / momentum
    # --------------------------------------------------------

    atr = calculate_atr(
        candles
    )

    momentum = calculate_momentum(
        candles
    )

    # --------------------------------------------------------
    # Confirmed swings
    # --------------------------------------------------------

    section(
        "CONFIRMED SWING DETECTION"
    )

    confirmed_swings = detect_confirmed_swings(
        candles
    )

    print(
        f"Raw confirmed swings: "
        f"{len(confirmed_swings)}"
    )

    report.section(
        "CONFIRMED SWING DETECTION"
    )

    report.add(
        f"Raw confirmed swings: "
        f"{len(confirmed_swings)}"
    )

    # --------------------------------------------------------
    # Structure
    # --------------------------------------------------------

    section(
        "MARKET STRUCTURE SWINGS"
    )

    structures = build_market_structure(
        confirmed_swings
    )

    cleaned = clean_swings(
        structures
    )

    highs = [
        x
        for x in cleaned
        if x["type"] == "SWING_HIGH"
    ]

    lows = [
        x
        for x in cleaned
        if x["type"] == "SWING_LOW"
    ]

    print(
        f"Swing highs: {len(highs)}"
    )

    print(
        f"Swing lows: {len(lows)}"
    )

    print(
        f"Cleaned swings: {len(cleaned)}"
    )

    report.section(
        "MARKET STRUCTURE SWINGS"
    )

    report.add(
        f"Swing highs: {len(highs)}"
    )
    report.add(
        f"Swing lows: {len(lows)}"
    )
    report.add(
        f"Cleaned swings: {len(cleaned)}"
    )

    print()
    print("Recent swings:")

    for swing in cleaned[-RECENT_COUNT:]:

        print(
            f"Candidate={swing['candidate_index']:6d} | "
            f"Confirmed={swing['confirmed_index']:6d} | "
            f"{swing['type']:<11} | "
            f"{swing['structure']:<12} | "
            f"Price={swing['price']:.5f} | "
            f"Time={swing['timestamp']}"
        )

    # --------------------------------------------------------
    # Split
    # --------------------------------------------------------

    split_index = int(
        len(candles) * TRAIN_RATIO
    )

    training_last = split_index - 1
    oos_first = split_index

    section(
        "CHRONOLOGICAL DATA SPLIT"
    )

    print(
        f"Total candles       : {len(candles)}"
    )

    print(
        f"Training candles    : {split_index}"
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

    print(
        f"Training last index : "
        f"{training_last}"
    )

    print(
        f"OOS first index     : "
        f"{oos_first}"
    )

    # --------------------------------------------------------
    # Structure events
    # --------------------------------------------------------

    events = build_structure_events(
        candles,
        cleaned
    )

    section(
        "STRUCTURE EVENTS"
    )

    event_counts = {}

    for event in events:

        event_name = event["event"]

        event_counts[event_name] = (
            event_counts.get(
                event_name,
                0
            ) + 1
        )

    for event_name in [
        "BOS_BULLISH",
        "BOS_BEARISH",
        "CHoCH_BULLISH",
        "CHoCH_BEARISH",
    ]:

        print(
            f"{event_name:<20}: "
            f"{event_counts.get(event_name, 0)}"
        )

    # --------------------------------------------------------
    # Event timing protection
    # --------------------------------------------------------

    event_violations = (
        structure_event_timing_check(
            events
        )
    )

    section(
        "LOOK-AHEAD-BIAS CHECK"
    )

    if event_violations:

        print(
            "FAIL: Structure event timing violations."
        )

        for item in event_violations[:10]:
            print(item)

        raise RuntimeError(
            "Structure timing validation failed."
        )

    print(
        "PASS: No structure-event "
        "confirmation timing violations."
    )

    # --------------------------------------------------------
    # Signal dataset
    # --------------------------------------------------------

    signals = build_signal_dataset(
        candles,
        cleaned,
        events,
        atr,
        momentum
    )

    # --------------------------------------------------------
    # Training-only threshold
    # --------------------------------------------------------
    #
    # We use zero threshold as the primary classification
    # because this is a directional-information experiment.
    #
    # Importantly, the threshold is established BEFORE OOS
    # evaluation.
    # --------------------------------------------------------

    threshold_pct = 0.0

    signals = attach_outcomes(
        signals,
        candles,
        threshold_pct
    )

    # Remove signals that have no usable H+4 outcome.
    signals = [
        x
        for x in signals
        if x["outcomes"].get(4) is not None
    ]

    split_index, training, oos = chronological_split(
        signals,
        len(candles)
    )

    section("SIGNAL DATASET")

    print(
        f"Total usable signals: {len(signals)}"
    )

    print(
        f"Training signals: {len(training)}"
    )

    print(
        f"OOS signals: {len(oos)}"
    )

    # --------------------------------------------------------
    # Training-only baselines
    # --------------------------------------------------------

    section(
        "TRAINING-ONLY BASELINES"
    )

    baselines = {}

    for horizon in HORIZONS:

        baseline = majority_baseline(
            training,
            horizon
        )

        baselines[horizon] = baseline

        print()
        print(f"H+{horizon}")

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
            f"{baseline['label']} "
            f"({baseline[baseline['label']]:.2f}%)"
        )

    # --------------------------------------------------------
    # Feature validation
    # --------------------------------------------------------

    section(
        "OUT-OF-SAMPLE FEATURE VALIDATION"
    )

    all_results = {}

    for group_name, feature_group in FEATURE_GROUPS.items():

        print()
        print("-" * 80)
        print(group_name)
        print("-" * 80)

        print(
            f"Training signals: {len(training)}"
        )

        print(
            f"OOS signals: {len(oos)}"
        )

        all_results[group_name] = {}

        for horizon in HORIZONS:

            baseline_value = baselines[
                horizon
            ][
                baselines[horizon]["label"]
            ]

            metrics = calculate_metrics(
                oos,
                feature_group,
                horizon,
                baseline_value
            )

            all_results[
                group_name
            ][horizon] = metrics

            print_metrics(
                f"H+{horizon}",
                metrics
            )

    # --------------------------------------------------------
    # Structure-specific OOS
    # --------------------------------------------------------

    section(
        "STRUCTURE-DIRECTION OOS RESULTS"
    )

    structure_groups = {
        "BULLISH_STRUCTURE":
            filter_structure_records(
                oos,
                bullish=True
            ),

        "BEARISH_STRUCTURE":
            filter_structure_records(
                oos,
                bullish=False
            ),

        "ALL_STRUCTURE":
            filter_structure_records(
                oos,
                bullish=None
            ),
    }

    directional_results = {}

    for name, records in structure_groups.items():

        subsection(name)

        directional_results[name] = {}

        for horizon in HORIZONS:

            baseline_value = baselines[
                horizon
            ][
                baselines[horizon]["label"]
            ]

            metrics = calculate_metrics(
                records,
                ["MARKET_STRUCTURE"],
                horizon,
                baseline_value
            )

            directional_results[
                name
            ][horizon] = metrics

            print_metrics(
                f"H+{horizon}",
                metrics
            )

    # --------------------------------------------------------
    # Event-specific OOS
    # --------------------------------------------------------

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
            if x["signal_type"] == event_type
        ]

        subsection(
            event_type
        )

        event_results[event_type] = {}

        for horizon in HORIZONS:

            baseline_value = baselines[
                horizon
            ][
                baselines[horizon]["label"]
            ]

            metrics = calculate_metrics(
                records,
                ["MARKET_STRUCTURE"],
                horizon,
                baseline_value
            )

            event_results[
                event_type
            ][horizon] = metrics

            print_metrics(
                f"H+{horizon}",
                metrics
            )

    # --------------------------------------------------------
    # Sample signals
    # --------------------------------------------------------

    section(
        "SAMPLE OOS VALIDATION SIGNALS"
    )

    sample_count = 30

    for signal in oos[:sample_count]:

        outputs = []

        for horizon in HORIZONS:

            outcome = signal[
                "outcomes"
            ][horizon]

            if outcome is None:
                label = "N/A"
            else:
                label = outcome["label"]

            outputs.append(
                f"H{horizon}={label:<7}"
            )

        print(
            f"Index={signal['index']:6d} | "
            f"{signal['signal_type']:<16} | "
            f"Direction={signal['signal_direction']:<8} | "
            f"Price={signal['price']:.5f} | "
            + " | ".join(outputs)
        )

    # --------------------------------------------------------
    # Coverage
    # --------------------------------------------------------

    section(
        "OOS COVERAGE"
    )

    oos_candles = len(candles) - split_index

    total_oos_signals = len(oos)

    frequency = (
        total_oos_signals
        / oos_candles
        if oos_candles
        else 0
    )

    print(
        f"OOS candles: {oos_candles}"
    )

    print(
        f"Total OOS signals: "
        f"{total_oos_signals}"
    )

    print(
        f"Signal frequency per OOS candle: "
        f"{frequency:.4f}"
    )

    # --------------------------------------------------------
    # Outcome distributions
    # --------------------------------------------------------

    section(
        "TRAINING OUTCOME DISTRIBUTION"
    )

    training_distributions = {}

    for horizon in HORIZONS:

        distribution = outcome_distribution(
            training,
            horizon
        )

        training_distributions[
            horizon
        ] = distribution

        print()
        print(f"H+{horizon}")

        for label in [
            "BUY",
            "SELL",
            "NEUTRAL",
        ]:

            count = sum(
                1
                for x in training
                if (
                    x["outcomes"]
                    .get(horizon) is not None
                    and x["outcomes"][horizon][
                        "label"
                    ] == label
                )
            )

            print(
                f"{label:<8}: {count}"
            )

    section(
        "OOS OUTCOME DISTRIBUTION"
    )

    oos_distributions = {}

    for horizon in HORIZONS:

        distribution = outcome_distribution(
            oos,
            horizon
        )

        oos_distributions[
            horizon
        ] = distribution

        print()
        print(f"H+{horizon}")

        for label in [
            "BUY",
            "SELL",
            "NEUTRAL",
        ]:

            count = sum(
                1
                for x in oos
                if (
                    x["outcomes"]
                    .get(horizon) is not None
                    and x["outcomes"][horizon][
                        "label"
                    ] == label
                )
            )

            print(
                f"{label:<8}: {count}"
            )

    # --------------------------------------------------------
    # OOS chronological integrity
    # --------------------------------------------------------

    section(
        "OOS CHRONOLOGICAL INTEGRITY"
    )

    indices = [
        x["index"]
        for x in oos
    ]

    chronological_oos = (
        indices == sorted(indices)
    )

    print(
        "Signal order: "
        + (
            "PASS"
            if chronological_oos
            else "FAIL"
        )
    )

    if not chronological_oos:
        raise RuntimeError(
            "OOS chronological integrity failed."
        )

    # --------------------------------------------------------
    # Future outcome separation
    # --------------------------------------------------------

    section(
        "FUTURE OUTCOME SEPARATION CHECK"
    )

    violations = lookahead_check(
        signals
    )

    if violations:

        print(
            "FAIL: Future outcome separation violated."
        )

        for violation in violations[:10]:
            print(violation)

        raise RuntimeError(
            "Future outcome separation failed."
        )

    print(
        "PASS: All future outcomes occur after signals."
    )

    # --------------------------------------------------------
    # Structure summary
    # --------------------------------------------------------

    section(
        "STRUCTURE SUMMARY"
    )

    structure_counts = {}

    for swing in cleaned:

        label = swing["structure"]

        structure_counts[label] = (
            structure_counts.get(
                label,
                0
            ) + 1
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

    # --------------------------------------------------------
    # Final protection
    # --------------------------------------------------------

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
        "Learning memory  : NOT MODIFIED"
    )

    print(
        "Trading          : DISABLED"
    )

    print(
        "Model training   : DISABLED"
    )

    # --------------------------------------------------------
    # Build validation object
    # --------------------------------------------------------

    validation = {
        "version":
            "MLAI_V3.8",

        "experiment":
            "MARKET_STRUCTURE_PREDICTIVE_VALIDATION",

        "data_file":
            os.path.basename(DATA_FILE),

        "total_candles":
            len(candles),

        "invalid_candles":
            invalid,

        "train_ratio":
            TRAIN_RATIO,

        "training_candles":
            split_index,

        "oos_candles":
            len(candles) - split_index,

        "training_signals":
            len(training),

        "oos_signals":
            len(oos),

        "horizons":
            HORIZONS,

        "threshold_pct":
            threshold_pct,

        "confirmed_swings":
            len(confirmed_swings),

        "cleaned_swings":
            len(cleaned),

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

        "feature_groups":
            FEATURE_GROUPS,

        "feature_results":
            all_results,

        "directional_results":
            directional_results,

        "event_results":
            event_results,

        "protection": {
            "market_data_read_only": True,
            "production_mlai_modified": False,
            "learning_memory_modified": False,
            "trading_enabled": False,
            "model_training_enabled": False,
            "internet_required": False,
        },

        "integrity": {
            "timestamp_order":
                chronological,

            "event_timing":
                len(event_violations) == 0,

            "oos_signal_order":
                chronological_oos,

            "future_outcome_separation":
                len(violations) == 0,
        },

        "signals": signals,
    }

    # --------------------------------------------------------
    # Save binary
    # --------------------------------------------------------

    with open(
        OUTPUT_BIN,
        "wb"
    ) as f:

        pickle.dump(
            validation,
            f,
            protocol=pickle.HIGHEST_PROTOCOL
        )

    # --------------------------------------------------------
    # Generate Markdown report
    # --------------------------------------------------------

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
        f"OOS candles: {len(candles) - split_index}"
    )

    report.add(
        f"Training signals: {len(training)}"
    )

    report.add(
        f"OOS signals: {len(oos)}"
    )

    report.section(
        "TRAINING-ONLY BASELINES"
    )

    for horizon in HORIZONS:

        b = baselines[horizon]

        report.add(
            f"H+{horizon}: "
            f"BUY={b['BUY']:.2f}% | "
            f"SELL={b['SELL']:.2f}% | "
            f"NEUTRAL={b['NEUTRAL']:.2f}% | "
            f"Majority={b['label']}"
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
                f"Precision={m['precision']:.2f}% | "
                f"Recall={m['recall']:.2f}% | "
                f"AvgReturn={m['avg_return']:+.4f}% | "
                f"Baseline={m['baseline']:.2f}% | "
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
        "Model training  : DISABLED"
    )

    report.add(
        "Internet        : NOT REQUIRED"
    )

    report.section(
        "OUTPUT"
    )

    report.add(
        os.path.basename(OUTPUT_BIN)
    )

    report.add(
        os.path.basename(OUTPUT_REPORT)
    )

    report.save(
        OUTPUT_REPORT
    )

    # --------------------------------------------------------
    # Final output
    # --------------------------------------------------------

    print()
    print("=" * 80)

    print(
        "Validation binary:"
    )

    print(
        f"    {os.path.basename(OUTPUT_BIN)}"
    )

    print(
        "Validation report:"
    )

    print(
        f"    {os.path.basename(OUTPUT_REPORT)}"
    )

    print("=" * 80)

    print(
        "MLAI v3.8 MARKET STRUCTURE "
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
            "Validation interrupted by user."
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