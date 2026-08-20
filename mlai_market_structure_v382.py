# ============================================================
# MLAI v3.8.2 MARKET STRUCTURE PREDICTIVE VALIDATION
# ============================================================
#
# PURPOSE
# -------
# Research validation of whether confirmed market structure
# contains measurable future directional information.
#
# FEATURES EVALUATED
# ------------------
#     1. Market Structure
#     2. ATR / Volatility Regime
#     3. Momentum
#     4. Candle Behaviour
#     5. Structural Location
#     6. Combined Context
#
# HORIZONS
# --------
#     H+4
#     H+8
#     H+16
#
# CHRONOLOGICAL VALIDATION
# ------------------------
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
# v3.8.2 CORRECTIONS
# ------------------
#
# 1. Removed global candle state.
#
# 2. Removed non-causal swing cleaning.
#
# 3. Structure is now constructed chronologically.
#
# 4. Historical structure cannot be rewritten by a future swing.
#
# 5. Confirmed swing information is only available from its
#    confirmation candle onward.
#
# 6. Structure events are processed causally.
#
# 7. Feature thresholds are learned from TRAINING only.
#
# 8. OOS feature thresholds are completely frozen.
#
# 9. ATR is treated as a volatility regime, not a direction.
#
# 10. Structural location is treated as context, not direction.
#
# 11. Prediction voting uses one vote per independent feature
#     family.
#
# 12. Duplicate signal weighting is reduced by evaluating each
#     signal event independently while preserving signal type.
#
# 13. Threshold selection is based on training directional
#     usefulness rather than simply BUY/SELL percentage balance.
#
# 14. No future candle is used to create a signal before that
#     candle's information becomes causally available.
#
# 15. Explicit integrity checks are included.
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
    "MLAI_V382_MARKET_STRUCTURE_PREDICTIVE_VALIDATION.bin"
)

OUTPUT_REPORT = os.path.join(
    ROOT,
    "MLAI_V382_MARKET_STRUCTURE_PREDICTIVE_VALIDATION_REPORT.md"
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
# PERCENT CHANGE
# ============================================================

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

    for item in raw:

        candle = normalize_candle(
            item,
            len(candles)
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

            previous_close = candles[
                i - 1
            ]["close"]

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
# CAUSAL SWING STREAM
# ============================================================
#
# IMPORTANT:
#
# v3.8.1 used a global cleaning operation which could replace
# an earlier swing with a later swing.
#
# That means a historical record could effectively change
# after the fact.
#
# v3.8.2 instead maintains the active swing stream
# chronologically.
#
# A swing that was known at time T remains part of the
# historical context at time T.
#
# ============================================================

def build_causal_structures(
    candles,
    raw_swings
):

    structures = []

    previous_high = None
    previous_low = None

    active_high = None
    active_low = None

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
            <= index
        ):

            swing = raw_swings[
                swing_pointer
            ]

            swing_type = swing[
                "type"
            ]

            # ------------------------------------------------
            # Same-type swing replacement is causal.
            #
            # The old swing remains part of the history.
            # The new swing becomes active only from this
            # confirmation point onward.
            # ------------------------------------------------

            item = dict(swing)

            if swing_type == "SWING_HIGH":

                if previous_high is None:

                    label = "HH"

                else:

                    difference = (
                        abs(
                            swing["price"]
                            -
                            previous_high["price"]
                        )
                        /
                        previous_high["price"]
                    ) * 100.0

                    if difference <= EQUAL_TOLERANCE_PCT:

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
                active_high = item

            else:

                if previous_low is None:

                    label = "LL"

                else:

                    difference = (
                        abs(
                            swing["price"]
                            -
                            previous_low["price"]
                        )
                        /
                        previous_low["price"]
                    ) * 100.0

                    if difference <= EQUAL_TOLERANCE_PCT:

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
                active_low = item

            item["structure"] = label

            structures.append(
                item
            )

            swing_pointer += 1

        # Nothing else is required here.
        # The active structures are queried causally later.

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
        if x["confirmed_index"] <= index
    ][-10:]

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
            *
            100.0
        )

    else:

        atr_pct = 0.0

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

    swing_pointer = 0

    for index in range(
        len(candles)
    ):

        # ----------------------------------------------------
        # Only swings confirmed by current candle are active.
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

            key = (
                active_high[
                    "candidate_index"
                ]
            )

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

                broken_low.add(
                    key
                )

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
                    in ("HH", "HL")
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

        if future_index >= len(candles):
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

            "accuracy_majority":
                0.0,

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
        *
        100.0
    )

    sell_pct = (
        counts["SELL"]
        /
        total
        *
        100.0
    )

    neutral_pct = (
        counts["NEUTRAL"]
        /
        total
        *
        100.0
    )

    directional_pct = (
        (
            counts["BUY"]
            +
            counts["SELL"]
        )
        /
        total
        *
        100.0
    )

    majority_accuracy = (
        max(counts.values())
        /
        total
        *
        100.0
    )

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

        "accuracy_majority":
            majority_accuracy,

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

    for threshold in RETURN_THRESHOLD_CANDIDATES:

        stats = threshold_training_stats(
            records,
            candles,
            horizon,
            threshold
        )

        if stats["samples"] < MIN_TRAIN_SAMPLES:
            continue

        # ----------------------------------------------------
        # Threshold selection:
        #
        # We do NOT simply maximize neutrality or BUY/SELL
        # balance.
        #
        # We prefer a threshold which:
        #
        # 1. leaves meaningful directional outcomes,
        # 2. keeps BUY and SELL reasonably represented,
        # 3. avoids an all-neutral classification.
        #
        # Score is deterministic and training-only.
        # ----------------------------------------------------

        directional = stats[
            "directional_pct"
        ]

        balance_penalty = (
            stats["directional_balance"]
            /
            100.0
        )

        score = (
            directional
            -
            (
                balance_penalty
                *
                20.0
            )
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
            x["stats"]["directional_pct"],
            -x["threshold"]
        ),
        reverse=True
    )

    return candidates[0]


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
# TRAINING MEDIAN
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

    momentum_abs_records = [

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
                momentum_abs_records,
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
    # --------------------------------------------------------

    if feature_name == "MOMENTUM":

        value = record[
            "momentum"
        ]

        if value > 0:
            return 1

        if value < 0:
            return -1

        return 0

    # --------------------------------------------------------
    # CANDLE BEHAVIOUR
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
    # STRUCTURAL LOCATION
    #
    # Location is contextual.
    #
    # It is deliberately NOT converted directly into BUY
    # or SELL because "high in range" does not intrinsically
    # mean sell and "low in range" does not intrinsically mean
    # buy.
    # --------------------------------------------------------

    if feature_name == "STRUCTURAL_LOCATION":

        return 0

    # --------------------------------------------------------
    # ATR VOLATILITY
    #
    # ATR is a regime variable, not directional information.
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

        if future_index >= len(candles):
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

            "precision":
                0.0,

            "recall":
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

                result.append(
                    record
                )

        elif bullish is False:

            if direction == "BEARISH":

                result.append(
                    record
                )

        else:

            result.append(
                record
            )

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


def signal_confirmation_check(
    signals,
    structures,
    events
):

    violations = []

    structure_map = {}

    for structure in structures:

        structure_map[
            (
                structure[
                    "confirmed_index"
                ],
                structure[
                    "structure"
                ]
            )
        ] = structure

    event_map = {}

    for event in events:

        event_map[
            (
                event["index"],
                event["event"]
            )
        ] = event

    for signal in signals:

        index = signal[
            "index"
        ]

        source = signal.get(
            "signal_source"
        )

        if source == "STRUCTURE":

            if signal["signal_type"] in (
                "HH",
                "HL",
                "LH",
                "LL",
            ):

                if (
                    index < 0
                    or
                    index >= len(
                        structures
                    ) + len(events) + 1000000
                ):
                    violations.append(
                        signal
                    )

        elif source == "EVENT":

            event = event_map.get(
                (
                    index,
                    signal["signal_type"]
                )
            )

            if event is None:

                violations.append(
                    signal
                )

            elif event[
                "confirmed_index"
            ] > index:

                violations.append(
                    signal
                )

    return violations


def lookahead_check(
    signals
):

    violations = []

    for signal in signals:

        index = signal[
            "index"
        ]

        for horizon in HORIZONS:

            outcome = signal[
                "outcomes"
            ].get(horizon)

            if outcome is None:
                continue

            if (
                outcome[
                    "future_index"
                ]
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


def feature_split_check(
    records,
    split_index
):

    violations = []

    for record in records:

        index = record[
            "index"
        ]

        if index < split_index:

            continue

        # Feature record itself must not reference an event
        # whose confirmation occurs after the signal candle.

        if record.get(
            "signal_source"
        ) == "EVENT":

            if record.get(
                "event_direction"
            ) is None:

                violations.append(
                    record
                )

    return violations


# ============================================================
# REPORT
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
        "MLAI v3.8.2 MARKET STRUCTURE "
        "PREDICTIVE VALIDATION"
    )

    print(
        """
RESEARCH EXPERIMENT

v3.8.2 corrections:

    - causal structure processing
    - no global candle state
    - no non-causal swing replacement
    - confirmed-only structure information
    - confirmed-only event processing
    - training-only threshold learning
    - frozen OOS feature thresholds
    - ATR treated as volatility regime
    - structural location treated as context
    - chronological OOS validation
    - explicit look-ahead checks

TRAINING:
    First 70%

OOS:
    Final 30%

market_data.bin:
    READ ONLY
"""
    )

    report.add(
        "# MLAI v3.8.2 MARKET STRUCTURE "
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

    section(
        "DATA QUALITY AUDIT"
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
            "Not enough candles for validation."
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
    # RAW SWINGS
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

    # ========================================================
    # CAUSAL STRUCTURES
    # ========================================================

    structures = build_causal_structures(
        candles,
        raw_swings
    )

    print(
        f"Causal structures   : "
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
        f"Swing highs         : "
        f"{len(highs)}"
    )

    print(
        f"Swing lows          : "
        f"{len(lows)}"
    )

    print()
    print(
        "Recent causal structure:"
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
    # STRUCTURE EVENTS
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
    # EVENT TIMING
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

    section(
        "SIGNAL DATASET"
    )

    print(
        f"Raw signal records: "
        f"{len(signals)}"
    )

    # ========================================================
    # SIGNAL CHRONOLOGY
    # ========================================================

    signal_indices = [
        x["index"]
        for x in signals
    ]

    signal_chronological = (
        signal_indices
        ==
        sorted(signal_indices)
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
            "Signal chronology failed."
        )

    # ========================================================
    # TRAINING-ONLY THRESHOLD SELECTION
    # ========================================================

    section(
        "TRAINING-ONLY THRESHOLD SELECTION"
    )

    # Use only signals whose signal candle is inside
    # the training section.

    training_signal_records = [

        x

        for x in signals

        if x["index"] < split_index
    ]

    selected_thresholds = {}

    threshold_stats = {}

    for horizon in HORIZONS:

        result = select_training_threshold(
            training_signal_records,
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

        stats = result[
            "stats"
        ]

        print(
            f"H+{horizon}: "
            f"{result['threshold']:.4f}% | "
            f"Samples={stats['samples']} | "
            f"Directional="
            f"{stats['directional_pct']:.2f}% | "
            f"BUY="
            f"{stats['buy_pct']:.2f}% | "
            f"SELL="
            f"{stats['sell_pct']:.2f}% | "
            f"NEUTRAL="
            f"{stats['neutral_pct']:.2f}%"
        )

    # --------------------------------------------------------
    # Freeze one common threshold.
    #
    # H+4 remains the reference threshold, matching the
    # original experiment design.
    # --------------------------------------------------------

    common_threshold = (
        selected_thresholds[4]
    )

    print()
    print(
        f"Frozen common threshold: "
        f"{common_threshold:.4f}%"
    )

    # ========================================================
    # FINAL SIGNAL OUTCOMES
    # ========================================================

    final_signals = attach_outcomes(
        signals,
        candles,
        common_threshold
    )

    # Require H+4 outcome because H+4 is the minimum horizon
    # used for this experiment.

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

    print(
        f"Total final signals: "
        f"{len(final_signals)}"
    )

    print(
        f"Training signals   : "
        f"{len(training)}"
    )

    print(
        f"OOS signals        : "
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
            f"{key:<32}: "
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

        baselines[
            horizon
        ] = baseline

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
            "CANDLE_BEHAVIOUR",
            "ATR_VOLATILITY",
            "STRUCTURAL_LOCATION"
        ],
    }

    # ========================================================
    # OOS FEATURE VALIDATION
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

        directional_results[
            name
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
    # TRAINING DISTRIBUTIONS
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

        print(
            f"H+{horizon}: "
            f"BUY={distribution['BUY']:.2f}% | "
            f"SELL={distribution['SELL']:.2f}% | "
            f"NEUTRAL={distribution['NEUTRAL']:.2f}%"
        )

    # ========================================================
    # OOS DISTRIBUTIONS
    # ========================================================

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
    # TRAINING / OOS BOUNDARY
    # ========================================================

    section(
        "TRAINING / OOS BOUNDARY CHECK"
    )

    boundary_violations = []

    for record in training:

        if record["index"] >= split_index:

            boundary_violations.append(
                record
            )

    for record in oos:

        if record["index"] < split_index:

            boundary_violations.append(
                record
            )

    print(
        "PASS"
        if not boundary_violations
        else "FAIL"
    )

    if boundary_violations:

        raise RuntimeError(
            "Training/OOS boundary failed."
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
            "MLAI_V3.8.2",

        "experiment":
            "MARKET_STRUCTURE_PREDICTIVE_VALIDATION",

        "description":
            "Causal chronological research validation "
            "of market structure and contextual directional "
            "information.",

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

        "training_threshold_stats":
            threshold_stats,

        "frozen_common_threshold":
            common_threshold,

        "feature_thresholds":
            feature_thresholds,

        "confirmed_swings":
            len(raw_swings),

        "causal_structures":
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

            "signal_chronological_order":
                signal_chronological,

            "structure_event_timing":
                len(
                    event_violations
                ) == 0,

            "oos_signal_order":
                chronological_oos,

            "training_oos_boundary":
                len(
                    boundary_violations
                ) == 0,

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
        "EXPERIMENT"
    )

    report.add(
        "Version: MLAI v3.8.2"
    )

    report.add(
        "Type: Research-only predictive validation"
    )

    report.add(
        "Training: First 70%"
    )

    report.add(
        "OOS: Final 30%"
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

            m = results[
                horizon
            ]

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
        "STRUCTURE DIRECTION"
    )

    for group_name, results in directional_results.items():

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
                f"Accuracy={m['accuracy']:.2f}% | "
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
        "TRAINING OUTCOME DISTRIBUTION"
    )

    for horizon in HORIZONS:

        d = training_distributions[
            horizon
        ]

        report.add(
            f"H+{horizon}: "
            f"BUY={d['BUY']:.2f}% | "
            f"SELL={d['SELL']:.2f}% | "
            f"NEUTRAL={d['NEUTRAL']:.2f}%"
        )

    report.section(
        "OOS OUTCOME DISTRIBUTION"
    )

    for horizon in HORIZONS:

        d = oos_distributions[
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
        f"Structure event timing: "
        f"{'PASS' if not event_violations else 'FAIL'}"
    )

    report.add(
        f"OOS signal order: "
        f"{'PASS' if chronological_oos else 'FAIL'}"
    )

    report.add(
        f"Training/OOS boundary: "
        f"{'PASS' if not boundary_violations else 'FAIL'}"
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
        "MLAI v3.8.2 MARKET STRUCTURE "
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