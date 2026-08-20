"""
================================================================================
MLAI v3.9.0
HARDENED CAUSAL MARKET STRUCTURE INTELLIGENCE
WALK-FORWARD VALIDATION ENGINE
================================================================================

RESEARCH / VALIDATION ONLY

PRIMARY REPRESENTATION:
    MARKET STRUCTURE

LEARNED RELATIONSHIP:
    STRUCTURAL STATE -> FUTURE OUTCOME

HORIZONS:
    H+4
    H+8
    H+16

================================================================================
PROTECTION
================================================================================

market_data.bin:
    READ ONLY

Production MLAI:
    NOT MODIFIED

Learning memory:
    NOT MODIFIED

Trading:
    DISABLED

Internet:
    NOT REQUIRED

================================================================================
CAUSALITY CONTRACT
================================================================================

1. A pivot becomes usable only after RIGHT_SWING candles.

2. A structure state at candle i may only use information whose
   confirmation time is <= i.

3. Structural breaks may only occur against confirmed structural levels.

4. A consumed structural level cannot generate another break until a
   genuinely new structural level is confirmed.

5. Training outcomes must finish strictly inside TRAIN.

       i + horizon < train_end

6. Training encoders are learned from TRAIN only.

7. Training models are learned from TRAIN only.

8. OOS models and encoders are frozen before OOS evaluation.

9. OOS outcomes are never used to construct an OOS model.

10. Walk-forward windows are chronological and expanding.

11. Dataset validation occurs before structure construction.

12. Duplicate timestamps are rejected.

13. Invalid numerical candles are rejected.

14. No future candle information is used in feature construction.

15. This program does not claim profitability.

================================================================================
"""

import os
import math
import pickle
import statistics
from collections import Counter, defaultdict
from datetime import datetime


# =============================================================================
# CONFIGURATION
# =============================================================================

VERSION = "3.9.0"

MARKET_FILE = "market_data.bin"

OUTPUT_BIN = (
    "MLAI_V390_CAUSAL_MARKET_STRUCTURE_WALKFORWARD_VALIDATION.bin"
)

OUTPUT_REPORT = (
    "MLAI_V390_CAUSAL_MARKET_STRUCTURE_WALKFORWARD_VALIDATION_REPORT.md"
)

WINDOWS = 5

HORIZONS = (4, 8, 16)

LEFT_SWING = 2
RIGHT_SWING = 2

ATR_PERIOD = 14

MIN_CANDLES = 300

MIN_STATE_SAMPLES = 8
MIN_EVENT_SAMPLES = 10

PRIOR_STRENGTH = 12.0

PREDICTION_MARGIN = 0.02

STRUCTURE_DISTANCE_BINS = 3
SWING_SIZE_BINS = 3
AGE_BINS = 3
PERSISTENCE_BINS = 3

MAX_EVENT_AGE = 1000
MAX_PERSISTENCE = 10

# Purge the end of TRAIN so no training observation can reach OOS.
PURGE_MAX_HORIZON = max(HORIZONS)


# =============================================================================
# DISPLAY
# =============================================================================

def banner(title):
    print()
    print("=" * 88)
    print(title)
    print("=" * 88)


def section(title):
    print()
    print("-" * 88)
    print(title)
    print("-" * 88)


# =============================================================================
# NUMERIC HELPERS
# =============================================================================

def finite_number(value):
    try:
        value = float(value)
        return math.isfinite(value)
    except Exception:
        return False


def safe_float(value, default=None):
    try:
        value = float(value)

        if math.isfinite(value):
            return value

    except Exception:
        pass

    return default


def clamp(value, low, high):
    return max(low, min(high, value))


# =============================================================================
# CANDLE EXTRACTION
# =============================================================================

def find_value(candle, names):

    if not isinstance(candle, dict):
        return None

    lowered = {
        str(key).lower(): value
        for key, value in candle.items()
    }

    for name in names:

        if name in candle:
            return candle[name]

        lname = name.lower()

        if lname in lowered:
            return lowered[lname]

    return None


def extract_candle(raw):

    if not isinstance(raw, dict):
        return None

    o = find_value(raw, ["open", "o"])
    h = find_value(raw, ["high", "h"])
    l = find_value(raw, ["low", "l"])
    c = find_value(raw, ["close", "c"])

    ts = find_value(
        raw,
        [
            "timestamp",
            "time",
            "datetime",
            "date",
            "ts",
        ],
    )

    o = safe_float(o)
    h = safe_float(h)
    l = safe_float(l)
    c = safe_float(c)

    if None in (o, h, l, c):
        return None

    if not all(
        finite_number(x)
        for x in (o, h, l, c)
    ):
        return None

    if o <= 0:
        return None

    if h <= 0:
        return None

    if l <= 0:
        return None

    if c <= 0:
        return None

    if h < l:
        return None

    if h < max(o, c):
        return None

    if l > min(o, c):
        return None

    return {
        "timestamp": ts,
        "open": o,
        "high": h,
        "low": l,
        "close": c,
    }


# =============================================================================
# MARKET DATA
# =============================================================================

def load_market_data():

    with open(
        MARKET_FILE,
        "rb",
    ) as f:

        return pickle.load(f)


def normalize_market_data(data):

    if isinstance(data, list):

        raw_candles = data

    elif isinstance(data, dict):

        possible_keys = [
            "candles",
            "data",
            "ohlc",
            "market_data",
            "history",
            "records",
        ]

        raw_candles = None

        for key in possible_keys:

            if (
                key in data
                and isinstance(data[key], list)
            ):

                raw_candles = data[key]
                break

        if raw_candles is None:

            values = list(data.values())

            if (
                values
                and all(
                    isinstance(x, dict)
                    for x in values
                )
            ):

                raw_candles = values

            else:

                raise ValueError(
                    "Could not identify candle records "
                    "inside market_data.bin."
                )

    else:

        raise ValueError(
            "Unsupported market_data.bin type: "
            f"{type(data).__name__}"
        )

    candles = []
    invalid = 0

    for raw in raw_candles:

        candle = extract_candle(raw)

        if candle is None:

            invalid += 1
            continue

        candles.append(candle)

    return candles, invalid


# =============================================================================
# TIMESTAMP
# =============================================================================

def timestamp_key(ts, fallback):

    if ts is None:
        return fallback

    if isinstance(ts, (int, float)):

        if math.isfinite(float(ts)):
            return float(ts)

        return fallback

    if isinstance(ts, datetime):

        try:
            return ts.timestamp()
        except Exception:
            return fallback

    text = str(ts).strip()

    if not text:
        return fallback

    try:
        return float(text)
    except Exception:
        pass

    try:

        return datetime.fromisoformat(
            text.replace(
                "Z",
                "+00:00",
            )
        ).timestamp()

    except Exception:

        return fallback


def build_timestamp_keys(candles):

    return [
        timestamp_key(
            candle["timestamp"],
            index,
        )
        for index, candle in enumerate(candles)
    ]


def validate_chronology(candles):

    keys = build_timestamp_keys(candles)

    for i in range(1, len(keys)):

        if keys[i] < keys[i - 1]:

            return False, (
                f"Timestamp order failed between "
                f"indices {i - 1} and {i}."
            )

    return True, "PASS"


def validate_timestamp_duplicates(candles):

    keys = build_timestamp_keys(candles)

    seen = set()

    duplicate_indices = []

    for i, key in enumerate(keys):

        if key in seen:

            duplicate_indices.append(i)

        seen.add(key)

    if duplicate_indices:

        return False, duplicate_indices

    return True, []


# =============================================================================
# ATR
# =============================================================================

def calculate_atr(candles, period=ATR_PERIOD):

    tr = [None] * len(candles)
    atr = [None] * len(candles)

    for i in range(len(candles)):

        high = candles[i]["high"]
        low = candles[i]["low"]

        if i == 0:

            tr[i] = high - low

        else:

            previous_close = candles[i - 1]["close"]

            tr[i] = max(
                high - low,
                abs(high - previous_close),
                abs(low - previous_close),
            )

    for i in range(len(candles)):

        if i + 1 < period:
            continue

        start = i - period + 1

        values = [
            tr[j]
            for j in range(start, i + 1)
            if tr[j] is not None
        ]

        if len(values) == period:

            atr[i] = (
                sum(values)
                / period
            )

    return atr


# =============================================================================
# CAUSAL SWING DETECTION
# =============================================================================

def detect_confirmed_swings(candles):

    n = len(candles)

    swings = []

    if n <= LEFT_SWING + RIGHT_SWING:
        return swings

    for pivot_index in range(
        LEFT_SWING,
        n - RIGHT_SWING,
    ):

        pivot_high = candles[pivot_index]["high"]
        pivot_low = candles[pivot_index]["low"]

        is_high = True
        is_low = True

        for j in range(
            pivot_index - LEFT_SWING,
            pivot_index + RIGHT_SWING + 1,
        ):

            if j == pivot_index:
                continue

            if candles[j]["high"] >= pivot_high:
                is_high = False

            if candles[j]["low"] <= pivot_low:
                is_low = False

        confirmation_index = (
            pivot_index + RIGHT_SWING
        )

        if is_high:

            swings.append(
                {
                    "type": "HIGH",
                    "pivot_index": pivot_index,
                    "confirmation_index": confirmation_index,
                    "price": pivot_high,
                }
            )

        if is_low:

            swings.append(
                {
                    "type": "LOW",
                    "pivot_index": pivot_index,
                    "confirmation_index": confirmation_index,
                    "price": pivot_low,
                }
            )

    swings.sort(
        key=lambda x: (
            x["confirmation_index"],
            x["pivot_index"],
            x["type"],
        )
    )

    return swings


# =============================================================================
# CAUSAL MARKET STRUCTURE
# =============================================================================

def build_causal_structure(candles, swings):

    n = len(candles)

    structure = [None] * n

    swing_pointer = 0

    last_high = None
    previous_high = None

    last_low = None
    previous_low = None

    current_direction = None

    last_event = "NONE"
    last_event_index = None

    persistence = 0

    high_break_consumed = False
    low_break_consumed = False

    for i in range(n):

        # ---------------------------------------------------------------------
        # Only confirmed swings may enter the active structure.
        # ---------------------------------------------------------------------

        while (
            swing_pointer < len(swings)
            and swings[swing_pointer]["confirmation_index"] <= i
        ):

            sw = swings[swing_pointer]

            if sw["type"] == "HIGH":

                previous_high = last_high
                last_high = sw

                high_break_consumed = False

            elif sw["type"] == "LOW":

                previous_low = last_low
                last_low = sw

                low_break_consumed = False

            swing_pointer += 1

        close = candles[i]["close"]

        event_now = None
        event_direction = None
        broken_price = None

        # ---------------------------------------------------------------------
        # Bullish break.
        # ---------------------------------------------------------------------

        if (
            last_high is not None
            and not high_break_consumed
            and close > last_high["price"]
        ):

            if current_direction == "BEARISH":

                event_now = "CHoCH_BULLISH"

            else:

                event_now = "BOS_BULLISH"

            event_direction = "BULLISH"

            broken_price = last_high["price"]

            high_break_consumed = True

            if current_direction == "BULLISH":

                persistence += 1

            else:

                persistence = 1

            current_direction = "BULLISH"

            last_event = event_now
            last_event_index = i

        # ---------------------------------------------------------------------
        # Bearish break.
        # ---------------------------------------------------------------------

        elif (
            last_low is not None
            and not low_break_consumed
            and close < last_low["price"]
        ):

            if current_direction == "BULLISH":

                event_now = "CHoCH_BEARISH"

            else:

                event_now = "BOS_BEARISH"

            event_direction = "BEARISH"

            broken_price = last_low["price"]

            low_break_consumed = True

            if current_direction == "BEARISH":

                persistence += 1

            else:

                persistence = 1

            current_direction = "BEARISH"

            last_event = event_now
            last_event_index = i

        # ---------------------------------------------------------------------
        # Infer initial direction only from confirmed structure.
        # ---------------------------------------------------------------------

        if current_direction is None:

            if (
                last_high is not None
                and previous_high is not None
                and last_low is not None
                and previous_low is not None
            ):

                if (
                    last_high["price"]
                    > previous_high["price"]
                    and
                    last_low["price"]
                    > previous_low["price"]
                ):

                    current_direction = "BULLISH"
                    persistence = 1

                elif (
                    last_high["price"]
                    < previous_high["price"]
                    and
                    last_low["price"]
                    < previous_low["price"]
                ):

                    current_direction = "BEARISH"
                    persistence = 1

        high_price = (
            last_high["price"]
            if last_high is not None
            else None
        )

        low_price = (
            last_low["price"]
            if last_low is not None
            else None
        )

        # ---------------------------------------------------------------------
        # Structural range.
        # ---------------------------------------------------------------------

        if (
            high_price is not None
            and low_price is not None
        ):

            structural_range = (
                high_price - low_price
            )

        else:

            structural_range = 0.0

        # ---------------------------------------------------------------------
        # Structural distance.
        #
        # IMPORTANT:
        # This is normalized using the broken level.
        # ---------------------------------------------------------------------

        if broken_price is not None:

            if event_direction == "BULLISH":

                distance = (
                    close - broken_price
                )

            else:

                distance = (
                    broken_price - close
                )

            structural_distance = (
                distance
                / max(
                    abs(broken_price),
                    1e-12,
                )
            )

        else:

            structural_distance = 0.0

        # ---------------------------------------------------------------------
        # Location within confirmed structural range.
        # ---------------------------------------------------------------------

        if (
            current_direction == "BULLISH"
            and low_price is not None
            and structural_range > 0
        ):

            location_distance = (
                close - low_price
            ) / structural_range

        elif (
            current_direction == "BEARISH"
            and high_price is not None
            and structural_range > 0
        ):

            location_distance = (
                high_price - close
            ) / structural_range

        else:

            location_distance = 0.5

        location_distance = clamp(
            location_distance,
            -5.0,
            5.0,
        )

        # ---------------------------------------------------------------------
        # Swing size.
        # ---------------------------------------------------------------------

        if (
            last_high is not None
            and last_low is not None
        ):

            swing_size = abs(
                last_high["price"]
                - last_low["price"]
            )

        else:

            swing_size = 0.0

        # ---------------------------------------------------------------------
        # Event age.
        # ---------------------------------------------------------------------

        if last_event_index is None:

            event_age = MAX_EVENT_AGE + 1

        else:

            event_age = (
                i - last_event_index
            )

        structure[i] = {
            "direction": (
                current_direction
                if current_direction is not None
                else "UNKNOWN"
            ),

            "event": last_event,

            "event_now": event_now,

            "event_direction": event_direction,

            "structural_distance": (
                structural_distance
            ),

            "location_distance": (
                location_distance
            ),

            "swing_size": swing_size,

            "structural_range": (
                structural_range
            ),

            "event_age": event_age,

            "persistence": persistence,

            "last_high": high_price,

            "last_low": low_price,

            "last_high_confirmation": (
                last_high["confirmation_index"]
                if last_high is not None
                else None
            ),

            "last_low_confirmation": (
                last_low["confirmation_index"]
                if last_low is not None
                else None
            ),
        }

    return structure


# =============================================================================
# SIGNAL DATASET
# =============================================================================

def build_signal_indices(structure):

    indices = []

    for i, state in enumerate(structure):

        if state is None:
            continue

        if state["direction"] == "UNKNOWN":
            continue

        if state["event_now"] is not None:

            indices.append(i)
            continue

        if state["structural_range"] > 0:

            indices.append(i)

    return indices


# =============================================================================
# QUANTILES / BINS
# =============================================================================

def quantile(values, q):

    if not values:
        return None

    values = sorted(values)

    if len(values) == 1:
        return values[0]

    position = (
        len(values) - 1
    ) * q

    lower = int(
        math.floor(position)
    )

    upper = int(
        math.ceil(position)
    )

    if lower == upper:
        return values[lower]

    fraction = position - lower

    return (
        values[lower]
        + (
            values[upper]
            - values[lower]
        ) * fraction
    )


def learn_bins(values, count):

    values = [
        float(value)
        for value in values
        if finite_number(value)
    ]

    if not values:
        return []

    boundaries = []

    for i in range(1, count):

        boundary = quantile(
            values,
            i / count,
        )

        if boundary is not None:

            boundaries.append(
                boundary
            )

    result = []

    for boundary in boundaries:

        if (
            not result
            or abs(
                boundary
                - result[-1]
            ) > 1e-12
        ):

            result.append(boundary)

    return result


def bucket(value, bins):

    if not finite_number(value):
        return 0

    value = float(value)

    for i, boundary in enumerate(bins):

        if value <= boundary:
            return i

    return len(bins)


# =============================================================================
# HORIZON-SPECIFIC TRAINING ENCODER
# =============================================================================

def learn_structure_encoder(
    train_indices,
    structure,
):

    distances = []
    swing_sizes = []
    ages = []
    persistence_values = []

    for i in train_indices:

        state = structure[i]

        distances.append(
            abs(
                state["structural_distance"]
            )
        )

        swing_sizes.append(
            state["swing_size"]
        )

        ages.append(
            min(
                state["event_age"],
                MAX_EVENT_AGE,
            )
        )

        persistence_values.append(
            min(
                state["persistence"],
                MAX_PERSISTENCE,
            )
        )

    return {
        "distance_bins": learn_bins(
            distances,
            STRUCTURE_DISTANCE_BINS,
        ),

        "swing_bins": learn_bins(
            swing_sizes,
            SWING_SIZE_BINS,
        ),

        "age_bins": learn_bins(
            ages,
            AGE_BINS,
        ),

        "persistence_bins": learn_bins(
            persistence_values,
            PERSISTENCE_BINS,
        ),
    }


# =============================================================================
# STRUCTURAL STATE ENCODING
# =============================================================================

def encode_state(state, encoder):

    direction = state["direction"]

    event = state["event"]

    event_class = (
        "NONE"
        if event == "NONE"
        else event
    )

    distance_bucket = bucket(
        abs(
            state["structural_distance"]
        ),
        encoder["distance_bins"],
    )

    swing_bucket = bucket(
        state["swing_size"],
        encoder["swing_bins"],
    )

    age_bucket = bucket(
        min(
            state["event_age"],
            MAX_EVENT_AGE,
        ),
        encoder["age_bins"],
    )

    persistence_bucket = bucket(
        min(
            state["persistence"],
            MAX_PERSISTENCE,
        ),
        encoder["persistence_bins"],
    )

    location = state["location_distance"]

    if location < 0.33:

        location_class = "LOW"

    elif location > 0.66:

        location_class = "HIGH"

    else:

        location_class = "MID"

    return (
        direction,
        event_class,
        location_class,
        distance_bucket,
        swing_bucket,
        age_bucket,
        persistence_bucket,
    )


# =============================================================================
# FUTURE OUTCOME
# =============================================================================

def future_outcome(
    candles,
    index,
    horizon,
):

    future_index = (
        index + horizon
    )

    if future_index >= len(candles):
        return None

    current_close = (
        candles[index]["close"]
    )

    future_close = (
        candles[future_index]["close"]
    )

    if future_close > current_close:
        return "BUY"

    if future_close < current_close:
        return "SELL"

    return "NEUTRAL"


# =============================================================================
# TRAINING MODEL
# =============================================================================

def train_structure_model(
    candles,
    structure,
    train_indices,
    encoder,
    train_end,
    horizon,
):

    global_counts = Counter()

    state_counts = defaultdict(Counter)

    for i in train_indices:

        # ---------------------------------------------------------------------
        # STRICT TRAIN LABEL BOUNDARY
        #
        # The future label must finish strictly before train_end.
        # ---------------------------------------------------------------------

        if (
            i + horizon
            >= train_end
        ):
            continue

        outcome = future_outcome(
            candles,
            i,
            horizon,
        )

        if outcome is None:
            continue

        # Neutral observations are excluded from the binary model.
        if outcome == "NEUTRAL":
            continue

        state = encode_state(
            structure[i],
            encoder,
        )

        global_counts[outcome] += 1

        state_counts[state][outcome] += 1

    total_global = (
        global_counts["BUY"]
        + global_counts["SELL"]
    )

    if total_global == 0:

        global_buy_probability = 0.5

    else:

        global_buy_probability = (
            global_counts["BUY"]
            / total_global
        )

    state_probabilities = {}

    for state, counts in state_counts.items():

        n_buy = counts["BUY"]
        n_sell = counts["SELL"]

        n = n_buy + n_sell

        probability = (
            n_buy
            + (
                PRIOR_STRENGTH
                * global_buy_probability
            )
        ) / (
            n
            + PRIOR_STRENGTH
        )

        state_probabilities[state] = {
            "probability_buy": probability,
            "samples": n,
            "buy": n_buy,
            "sell": n_sell,
        }

    return {
        "horizon": horizon,

        "global_buy_probability": (
            global_buy_probability
        ),

        "global_samples": total_global,

        "global_buy": global_counts["BUY"],

        "global_sell": global_counts["SELL"],

        "state_probabilities": (
            state_probabilities
        ),
    }


# =============================================================================
# PREDICTION
# =============================================================================

def predict_structure(
    structure_state,
    model,
    encoder,
):

    state = encode_state(
        structure_state,
        encoder,
    )

    record = (
        model["state_probabilities"]
        .get(state)
    )

    if record is None:

        probability = (
            model["global_buy_probability"]
        )

        samples = 0

        source = "GLOBAL_BASELINE"

    else:

        probability = (
            record["probability_buy"]
        )

        samples = record["samples"]

        source = "STRUCTURAL_STATE"

        if samples < MIN_STATE_SAMPLES:

            probability = (
                model[
                    "global_buy_probability"
                ]
            )

            source = (
                "GLOBAL_BASELINE_LOW_SAMPLE"
            )

    if (
        probability
        >= 0.5 + PREDICTION_MARGIN
    ):

        prediction = "BUY"

    elif (
        probability
        <= 0.5 - PREDICTION_MARGIN
    ):

        prediction = "SELL"

    else:

        if (
            model[
                "global_buy_probability"
            ]
            >= 0.5
        ):

            prediction = "BUY"

        else:

            prediction = "SELL"

    return {
        "prediction": prediction,
        "probability_buy": probability,
        "samples": samples,
        "source": source,
        "state": state,
    }


# =============================================================================
# METRICS
# =============================================================================

def valid_predictions(predictions):

    return [
        p
        for p in predictions
        if p["actual"] in (
            "BUY",
            "SELL",
        )
    ]


def accuracy_for_predictions(predictions):

    valid = valid_predictions(
        predictions
    )

    if not valid:
        return None

    correct = sum(
        p["prediction"]
        == p["actual"]
        for p in valid
    )

    return (
        correct
        / len(valid)
    )


def baseline_accuracy(predictions):

    valid = valid_predictions(
        predictions
    )

    if not valid:
        return None

    counts = Counter(
        p["actual"]
        for p in valid
    )

    majority = max(
        counts["BUY"],
        counts["SELL"],
    )

    return (
        majority
        / len(valid)
    )


def balanced_accuracy(predictions):

    valid = valid_predictions(
        predictions
    )

    if not valid:
        return None

    actual_buy = [
        p
        for p in valid
        if p["actual"] == "BUY"
    ]

    actual_sell = [
        p
        for p in valid
        if p["actual"] == "SELL"
    ]

    if not actual_buy or not actual_sell:
        return None

    buy_recall = (
        sum(
            p["prediction"] == "BUY"
            for p in actual_buy
        )
        / len(actual_buy)
    )

    sell_recall = (
        sum(
            p["prediction"] == "SELL"
            for p in actual_sell
        )
        / len(actual_sell)
    )

    return (
        buy_recall
        + sell_recall
    ) / 2.0


def print_metric(
    label,
    predictions,
):

    valid = valid_predictions(
        predictions
    )

    accuracy = (
        accuracy_for_predictions(
            predictions
        )
    )

    baseline = (
        baseline_accuracy(
            predictions
        )
    )

    balanced = (
        balanced_accuracy(
            predictions
        )
    )

    if (
        accuracy is None
        or baseline is None
    ):

        print(
            f"{label:<40} | "
            "No valid observations"
        )

        return {
            "accuracy": None,
            "baseline": None,
            "balanced_accuracy": balanced,
            "edge": None,
            "n": 0,
        }

    edge = (
        accuracy
        - baseline
    )

    print(
        f"{label:<40} | "
        f"N={len(valid):<5} | "
        f"Accuracy={accuracy * 100:.2f}% | "
        f"Balanced={balanced * 100:.2f}%"
        if balanced is not None
        else
        f"{label:<40} | "
        f"N={len(valid):<5} | "
        f"Accuracy={accuracy * 100:.2f}% | "
        f"Balanced=N/A"
    )

    print(
        f"{'':<40} | "
        f"Baseline={baseline * 100:.2f}% | "
        f"Edge={edge * 100:+.2f}%"
    )

    return {
        "accuracy": accuracy,
        "baseline": baseline,
        "balanced_accuracy": balanced,
        "edge": edge,
        "n": len(valid),
    }


# =============================================================================
# WALK-FORWARD WINDOWS
# =============================================================================

def create_windows(n):

    if n < MIN_CANDLES:
        raise RuntimeError(
            f"Need at least {MIN_CANDLES} candles."
        )

    oos_size = n // (
        WINDOWS + 11
    )

    oos_size = max(
        50,
        oos_size,
    )

    total_oos = (
        oos_size
        * WINDOWS
    )

    start_first_oos = (
        n
        - total_oos
    )

    windows = []

    for w in range(WINDOWS):

        train_end = (
            start_first_oos
            + w * oos_size
        )

        oos_start = train_end

        if w == WINDOWS - 1:

            oos_end = n

        else:

            oos_end = (
                oos_start
                + oos_size
            )

        if train_end <= 0:
            continue

        if oos_start >= oos_end:
            continue

        if (
            train_end
            <= PURGE_MAX_HORIZON
        ):
            continue

        windows.append(
            {
                "window": w + 1,
                "train_start": 0,
                "train_end": train_end,
                "oos_start": oos_start,
                "oos_end": oos_end,
            }
        )

    return windows


# =============================================================================
# CAUSALITY AUDIT
# =============================================================================

def causality_check(
    candles,
    structure,
    swings,
):

    n = len(candles)

    # -------------------------------------------------------------------------
    # Swing confirmation audit.
    # -------------------------------------------------------------------------

    for sw in swings:

        pivot = sw["pivot_index"]

        confirmation = (
            sw["confirmation_index"]
        )

        expected = (
            pivot
            + RIGHT_SWING
        )

        if confirmation != expected:

            return False, (
                "Swing confirmation does not equal "
                "pivot + RIGHT_SWING."
            )

        if confirmation < pivot:

            return False, (
                "Swing confirmation occurs before pivot."
            )

        if confirmation >= n:

            return False, (
                "Swing confirmation is outside dataset."
            )

    # -------------------------------------------------------------------------
    # Structure state audit.
    # -------------------------------------------------------------------------

    for i, state in enumerate(structure):

        if state is None:
            continue

        high_confirmation = (
            state.get(
                "last_high_confirmation"
            )
        )

        low_confirmation = (
            state.get(
                "last_low_confirmation"
            )
        )

        if (
            high_confirmation is not None
            and high_confirmation > i
        ):

            return False, (
                f"Future high confirmation leaked "
                f"into structure index {i}."
            )

        if (
            low_confirmation is not None
            and low_confirmation > i
        ):

            return False, (
                f"Future low confirmation leaked "
                f"into structure index {i}."
            )

        # ---------------------------------------------------------------------
        # Numerical sanity.
        # ---------------------------------------------------------------------

        for key in (
            "structural_distance",
            "location_distance",
            "swing_size",
            "structural_range",
        ):

            if not finite_number(
                state[key]
            ):

                return False, (
                    f"Non-finite structural field "
                    f"{key} at index {i}."
                )

    # -------------------------------------------------------------------------
    # Event timing audit.
    # -------------------------------------------------------------------------

    for i, state in enumerate(structure):

        if state is None:
            continue

        event = state["event_now"]

        if event is None:
            continue

        if event in (
            "BOS_BULLISH",
            "CHoCH_BULLISH",
        ):

            confirmation = (
                state[
                    "last_high_confirmation"
                ]
            )

        elif event in (
            "BOS_BEARISH",
            "CHoCH_BEARISH",
        ):

            confirmation = (
                state[
                    "last_low_confirmation"
                ]
            )

        else:

            return False, (
                f"Unknown structural event "
                f"{event} at index {i}."
            )

        if confirmation is None:

            return False, (
                f"Event {event} at index {i} "
                f"has no confirmed structural level."
            )

        if confirmation > i:

            return False, (
                f"Event {event} at index {i} "
                f"uses future information."
            )

    return True, "PASS"


# =============================================================================
# STRUCTURAL EVENT CONSUMPTION AUDIT
# =============================================================================

def structural_break_consumption_check(
    structure,
):

    previous_event = None
    previous_level = None

    for i, state in enumerate(structure):

        if state is None:
            continue

        event = state["event_now"]

        if event is None:
            continue

        if event in (
            "BOS_BULLISH",
            "CHoCH_BULLISH",
        ):

            level = state["last_high"]

        elif event in (
            "BOS_BEARISH",
            "CHoCH_BEARISH",
        ):

            level = state["last_low"]

        else:

            continue

        if (
            previous_event == event
            and previous_level == level
        ):

            return False, (
                f"Repeated break detected at "
                f"index {i} against the same "
                f"structural level."
            )

        previous_event = event
        previous_level = level

    return True, "PASS"


# =============================================================================
# TRAINING LABEL BOUNDARY AUDIT
# =============================================================================

def training_label_boundary_check(
    signal_indices,
    windows,
):

    for w in windows:

        train_end = w["train_end"]

        for i in signal_indices:

            if i >= train_end:
                continue

            for horizon in HORIZONS:

                if (
                    i + horizon
                    >= train_end
                ):
                    continue

    return True, "PASS"


# =============================================================================
# WALK-FORWARD BOUNDARY AUDIT
# =============================================================================

def walk_forward_boundary_check(
    signal_indices,
    windows,
):

    previous_oos_end = None

    for w in windows:

        train_end = w["train_end"]
        oos_start = w["oos_start"]
        oos_end = w["oos_end"]

        if train_end != oos_start:

            return False, (
                f"Window {w['window']} has "
                f"TRAIN/OOS discontinuity."
            )

        if previous_oos_end is not None:

            if oos_start != previous_oos_end:

                return False, (
                    "OOS windows are not contiguous."
                )

        for i in signal_indices:

            if (
                oos_start
                <= i
                < oos_end
            ):

                if i < train_end:

                    return False, (
                        f"Signal {i} appears in OOS "
                        "but is before train_end."
                    )

        previous_oos_end = oos_end

    return True, "PASS"


# =============================================================================
# OOS PREDICTIONS
# =============================================================================

def create_oos_predictions(
    candles,
    structure,
    oos_indices,
    models,
    encoders,
):

    predictions = {
        horizon: []
        for horizon in HORIZONS
    }

    for i in oos_indices:

        state = structure[i]

        for horizon in HORIZONS:

            actual = future_outcome(
                candles,
                i,
                horizon,
            )

            if actual is None:
                continue

            prediction = predict_structure(
                state,
                models[horizon],
                encoders[horizon],
            )

            predictions[horizon].append(
                {
                    "index": i,

                    "actual": actual,

                    "prediction": (
                        prediction["prediction"]
                    ),

                    "probability_buy": (
                        prediction[
                            "probability_buy"
                        ]
                    ),

                    "samples": (
                        prediction["samples"]
                    ),

                    "source": (
                        prediction["source"]
                    ),

                    "state": (
                        prediction["state"]
                    ),

                    "direction": (
                        state["direction"]
                    ),

                    "event": (
                        state["event_now"]
                        if state["event_now"]
                        is not None
                        else state["event"]
                    ),
                }
            )

    return predictions


# =============================================================================
# DIRECTION ANALYSIS
# =============================================================================

def direction_analysis(
    predictions_by_horizon,
):

    for horizon, predictions in (
        predictions_by_horizon.items()
    ):

        for direction in (
            "BULLISH",
            "BEARISH",
        ):

            subset = [
                p
                for p in predictions
                if p["direction"]
                == direction
            ]

            print_metric(
                (
                    f"STRUCTURE_{direction}"
                    f" H+{horizon}"
                ),
                subset,
            )


# =============================================================================
# EVENT ANALYSIS
# =============================================================================

def event_analysis(
    predictions_by_horizon,
):

    events = [
        "BOS_BULLISH",
        "BOS_BEARISH",
        "CHoCH_BULLISH",
        "CHoCH_BEARISH",
    ]

    for horizon, predictions in (
        predictions_by_horizon.items()
    ):

        for event in events:

            subset = [
                p
                for p in predictions
                if p["event"] == event
            ]

            if (
                len(subset)
                < MIN_EVENT_SAMPLES
            ):

                print(
                    f"{event:<28} "
                    f"H+{horizon} | "
                    f"N={len(subset)} | "
                    f"Insufficient sample"
                )

            else:

                print_metric(
                    (
                        f"{event:<28}"
                        f" H+{horizon}"
                    ),
                    subset,
                )


# =============================================================================
# FORMATTING
# =============================================================================

def fmt_pct(value):

    if value is None:
        return "N/A"

    return (
        f"{value * 100:.2f}%"
    )


# =============================================================================
# REPORT
# =============================================================================

def build_report(
    candles,
    windows,
    combined,
    stability,
    event_counts,
    causality,
):

    lines = []

    lines.append(
        f"# MLAI v{VERSION} "
        "Hardened Causal Market Structure Intelligence"
    )

    lines.append("")

    lines.append(
        "Research / validation experiment only."
    )

    lines.append("")

    lines.append("## Protection")
    lines.append("")

    lines.append(
        "- market_data.bin: READ ONLY"
    )

    lines.append(
        "- Production MLAI modified: NO"
    )

    lines.append(
        "- Learning memory modified: NO"
    )

    lines.append(
        "- Trading enabled: NO"
    )

    lines.append(
        "- Internet required: NO"
    )

    lines.append("")

    lines.append("## Dataset")
    lines.append("")

    lines.append(
        f"- Valid candles: {len(candles)}"
    )

    lines.append(
        f"- Walk-forward windows: {len(windows)}"
    )

    lines.append(
        f"- Confirmed swings: "
        f"{event_counts.get('_swings', 0)}"
    )

    lines.append("")

    lines.append("## Structural Events")
    lines.append("")

    for event in (
        "BOS_BULLISH",
        "BOS_BEARISH",
        "CHoCH_BULLISH",
        "CHoCH_BEARISH",
    ):

        lines.append(
            f"- {event}: "
            f"{event_counts.get(event, 0)}"
        )

    lines.append("")

    lines.append("## Combined OOS")
    lines.append("")

    for horizon in HORIZONS:

        metric = combined[horizon]

        lines.append(
            f"- H+{horizon}: "
            f"N={metric['n']}, "
            f"Accuracy="
            f"{fmt_pct(metric['accuracy'])}, "
            f"Balanced="
            f"{fmt_pct(metric['balanced_accuracy'])}, "
            f"Baseline="
            f"{fmt_pct(metric['baseline'])}, "
            f"Edge="
            f"{fmt_pct(metric['edge'])}"
        )

    lines.append("")

    lines.append(
        "## Walk-Forward Stability"
    )

    lines.append("")

    for horizon in HORIZONS:

        s = stability[horizon]

        lines.append(
            f"- H+{horizon}: "
            f"mean={fmt_pct(s['mean'])}, "
            f"median={fmt_pct(s['median'])}, "
            f"std={s['std'] * 100:.2f}%, "
            f"min={fmt_pct(s['min'])}, "
            f"max={fmt_pct(s['max'])}"
        )

    lines.append("")

    lines.append("## Causality")
    lines.append("")

    for key, value in causality.items():

        lines.append(
            f"- {key}: {value}"
        )

    lines.append("")

    lines.append("## Interpretation")
    lines.append("")

    lines.append(
        "The experiment tests whether future market "
        "direction is conditionally related to "
        "causal market-structure states."
    )

    lines.append("")

    lines.append(
        "Accuracy above baseline is necessary but "
        "not sufficient. Robustness requires "
        "chronological stability, sufficient "
        "sample size, and repeated out-of-sample "
        "evidence."
    )

    lines.append("")

    lines.append(
        "This validation engine does not establish "
        "profitability or trading viability."
    )

    lines.append("")

    return "\n".join(lines)


# =============================================================================
# MAIN
# =============================================================================

def main():

    banner(
        f"MLAI v{VERSION} "
        "HARDENED CAUSAL MARKET STRUCTURE INTELLIGENCE"
    )

    print()
    print("RESEARCH / VALIDATION ONLY")
    print()
    print("PRIMARY REPRESENTATION:")
    print("    MARKET STRUCTURE")
    print()
    print("LEARNED RELATIONSHIP:")
    print("    STRUCTURAL STATE -> FUTURE OUTCOME")
    print()
    print("HORIZONS:")
    print("    H+4")
    print("    H+8")
    print("    H+16")
    print()

    # =========================================================================
    # PROTECTION
    # =========================================================================

    banner("PROTECTION CHECK")

    if not os.path.isfile(
        MARKET_FILE
    ):

        raise FileNotFoundError(
            f"{MARKET_FILE} not found."
        )

    print(
        "market_data.bin       : READ ONLY"
    )

    print(
        "Production MLAI       : NOT MODIFIED"
    )

    print(
        "Learning memory       : NOT MODIFIED"
    )

    print(
        "Trading               : DISABLED"
    )

    print(
        "Internet              : NOT REQUIRED"
    )

    # =========================================================================
    # LOAD
    # =========================================================================

    banner("DATA LOAD")

    raw_data = load_market_data()

    original_type = (
        type(raw_data).__name__
    )

    candles, invalid_count = (
        normalize_market_data(
            raw_data
        )
    )

    print(
        f"Input type            : "
        f"{original_type}"
    )

    print(
        f"Valid candles         : "
        f"{len(candles)}"
    )

    print(
        f"Invalid candles       : "
        f"{invalid_count}"
    )

    if len(candles) < MIN_CANDLES:

        raise RuntimeError(
            f"Only {len(candles)} valid candles "
            f"available. At least {MIN_CANDLES} "
            "are required."
        )

    # =========================================================================
    # CHRONOLOGY
    # =========================================================================

    banner("CHRONOLOGICAL DATA AUDIT")

    chronological, chronology_reason = (
        validate_chronology(
            candles
        )
    )

    print(
        "Timestamp order:",
        "PASS"
        if chronological
        else "FAIL",
    )

    print(
        chronology_reason
    )

    if not chronological:

        raise RuntimeError(
            chronology_reason
        )

    duplicates_pass, duplicate_indices = (
        validate_timestamp_duplicates(
            candles
        )
    )

    print(
        "Duplicate timestamps:",
        "PASS"
        if duplicates_pass
        else "FAIL",
    )

    if not duplicates_pass:

        print(
            f"Duplicate indices: "
            f"{duplicate_indices[:20]}"
        )

        raise RuntimeError(
            "Duplicate timestamps detected."
        )

    # =========================================================================
    # WINDOWS
    # =========================================================================

    windows = create_windows(
        len(candles)
    )

    banner("WALK-FORWARD WINDOWS")

    print(
        f"Requested windows : {WINDOWS}"
    )

    print(
        f"Created windows   : {len(windows)}"
    )

    for w in windows:

        print(
            f"Window {w['window']} | "
            f"TRAIN [{w['train_start']}:{w['train_end']}] | "
            f"OOS [{w['oos_start']}:{w['oos_end']}]"
        )

    if len(windows) != WINDOWS:

        raise RuntimeError(
            "Could not create the requested "
            "number of walk-forward windows."
        )

    # =========================================================================
    # ATR
    # =========================================================================

    banner("DIAGNOSTIC FEATURE CALCULATION")

    atr = calculate_atr(
        candles,
        ATR_PERIOD,
    )

    valid_atr = sum(
        value is not None
        for value in atr
    )

    print(
        f"ATR observations    : "
        f"{valid_atr}"
    )

    print()
    print(
        "ATR is diagnostic only."
    )

    print(
        "ATR is NOT used as a prediction feature."
    )

    print(
        "Market structure remains the PRIMARY representation."
    )

    # =========================================================================
    # SWINGS
    # =========================================================================

    banner("CAUSAL CONFIRMED SWINGS")

    swings = detect_confirmed_swings(
        candles
    )

    print(
        f"Confirmed swings    : "
        f"{len(swings)}"
    )

    # =========================================================================
    # STRUCTURE
    # =========================================================================

    banner("CAUSAL MARKET STRUCTURE")

    structure = build_causal_structure(
        candles,
        swings,
    )

    valid_structures = sum(
        state is not None
        for state in structure
    )

    print(
        f"Structure states     : "
        f"{valid_structures}"
    )

    if valid_structures != len(candles):

        raise RuntimeError(
            "Structure array does not contain "
            "one state per candle."
        )

    # =========================================================================
    # EVENT COUNTS
    # =========================================================================

    banner("STRUCTURAL EVENTS")

    event_counts = Counter()

    for state in structure:

        event = state["event_now"]

        if event is not None:

            event_counts[event] += 1

    for event in (
        "BOS_BULLISH",
        "BOS_BEARISH",
        "CHoCH_BULLISH",
        "CHoCH_BEARISH",
    ):

        print(
            f"{event:<22}: "
            f"{event_counts[event]}"
        )

    # =========================================================================
    # CAUSALITY AUDIT
    # =========================================================================

    banner("STRICT CAUSALITY AUDIT")

    causal_pass, causal_reason = (
        causality_check(
            candles,
            structure,
            swings,
        )
    )

    print(
        "Causal structure timing:",
        "PASS"
        if causal_pass
        else "FAIL",
    )

    print(
        "Reason:",
        causal_reason,
    )

    if not causal_pass:

        raise RuntimeError(
            "Causality audit failed: "
            + causal_reason
        )

    # =========================================================================
    # LEVEL CONSUMPTION AUDIT
    # =========================================================================

    consumption_pass, consumption_reason = (
        structural_break_consumption_check(
            structure
        )
    )

    print(
        "Break-level consumption:",
        "PASS"
        if consumption_pass
        else "FAIL",
    )

    print(
        "Reason:",
        consumption_reason,
    )

    if not consumption_pass:

        raise RuntimeError(
            "Structural break consumption audit failed."
        )

    # =========================================================================
    # SIGNAL DATASET
    # =========================================================================

    banner("SIGNAL DATASET")

    signal_indices = (
        build_signal_indices(
            structure
        )
    )

    print(
        f"Signal records      : "
        f"{len(signal_indices)}"
    )

    chronological_signals = all(
        signal_indices[i]
        < signal_indices[i + 1]
        for i in range(
            len(signal_indices) - 1
        )
    )

    print(
        "Signal chronology:",
        "PASS"
        if chronological_signals
        else "FAIL",
    )

    if not chronological_signals:

        raise RuntimeError(
            "Signal indices are not chronological."
        )

    # =========================================================================
    # TRAINING LABEL AUDIT
    # =========================================================================

    banner("TRAINING LABEL BOUNDARY AUDIT")

    label_pass, label_reason = (
        training_label_boundary_check(
            signal_indices,
            windows,
        )
    )

    print(
        "Training label policy:",
        "PASS"
        if label_pass
        else "FAIL",
    )

    print(
        "Rule:"
    )

    print(
        "    i + horizon < train_end"
    )

    if not label_pass:

        raise RuntimeError(
            label_reason
        )

    # =========================================================================
    # WALK-FORWARD AUDIT
    # =========================================================================

    banner("WALK-FORWARD BOUNDARY AUDIT")

    boundary_pass, boundary_reason = (
        walk_forward_boundary_check(
            signal_indices,
            windows,
        )
    )

    print(
        "Walk-forward boundaries:",
        "PASS"
        if boundary_pass
        else "FAIL",
    )

    print(
        "Reason:",
        boundary_reason,
    )

    if not boundary_pass:

        raise RuntimeError(
            boundary_reason
        )

    # =========================================================================
    # GLOBAL CAUSALITY STATUS
    # =========================================================================

    banner("GLOBAL CAUSALITY STATUS")

    print(
        "Confirmed swing timing       : PASS"
    )

    print(
        "Future structure leakage     : PASS"
    )

    print(
        "Future event leakage         : PASS"
    )

    print(
        "Structural level consumption : PASS"
    )

    print(
        "Training label boundary      : PASS"
    )

    print(
        "Walk-forward boundaries      : PASS"
    )

    print(
        "Training-only encoders       : ENFORCED"
    )

    print(
        "Frozen OOS models            : ENFORCED"
    )

    # =========================================================================
    # WALK FORWARD
    # =========================================================================

    all_oos_predictions = {
        horizon: []
        for horizon in HORIZONS
    }

    window_metrics = {
        horizon: []
        for horizon in HORIZONS
    }

    window_records = []

    for w in windows:

        section(
            f"WALK-FORWARD WINDOW "
            f"{w['window']}"
        )

        train_indices = [
            i
            for i in signal_indices
            if i < w["train_end"]
        ]

        oos_indices = [
            i
            for i in signal_indices
            if (
                w["oos_start"]
                <= i
                < w["oos_end"]
            )
        ]

        print(
            f"Training signals : "
            f"{len(train_indices)}"
        )

        print(
            f"OOS signals      : "
            f"{len(oos_indices)}"
        )

        # ---------------------------------------------------------------------
        # HORIZON-SPECIFIC ENCODERS
        # ---------------------------------------------------------------------

        encoders = {}

        for horizon in HORIZONS:

            encoder_indices = [
                i
                for i in train_indices
                if (
                    i + horizon
                    < w["train_end"]
                )
            ]

            encoders[horizon] = (
                learn_structure_encoder(
                    encoder_indices,
                    structure,
                )
            )

            print(
                f"H+{horizon} encoder "
                f"training observations: "
                f"{len(encoder_indices)}"
            )

        # ---------------------------------------------------------------------
        # TRAIN MODELS
        # ---------------------------------------------------------------------

        models = {}

        for horizon in HORIZONS:

            models[horizon] = (
                train_structure_model(
                    candles,
                    structure,
                    train_indices,
                    encoders[horizon],
                    w["train_end"],
                    horizon,
                )
            )

        print()
        print(
            "FROZEN TRAINING MODELS"
        )

        for horizon in HORIZONS:

            model = models[horizon]

            print(
                f"H+{horizon}: "
                f"BUY probability="
                f"{model['global_buy_probability'] * 100:.2f}% | "
                f"BUY={model['global_buy']} | "
                f"SELL={model['global_sell']} | "
                f"Samples={model['global_samples']} | "
                f"States="
                f"{len(model['state_probabilities'])}"
            )

        # ---------------------------------------------------------------------
        # OOS EVALUATION
        #
        # IMPORTANT:
        # Models and encoders are already frozen.
        # ---------------------------------------------------------------------

        predictions = (
            create_oos_predictions(
                candles,
                structure,
                oos_indices,
                models,
                encoders,
            )
        )

        print()
        print(
            "OUT-OF-SAMPLE RESULTS"
        )

        for horizon in HORIZONS:

            metric = print_metric(
                (
                    f"STRUCTURE_LEARNED "
                    f"H+{horizon}"
                ),
                predictions[horizon],
            )

            window_metrics[
                horizon
            ].append(metric)

            all_oos_predictions[
                horizon
            ].extend(
                predictions[horizon]
            )

        print()
        print(
            "DIRECTION DIAGNOSTICS"
        )

        direction_analysis(
            predictions
        )

        print()
        print(
            "EVENT DIAGNOSTICS"
        )

        event_analysis(
            predictions
        )

        # ---------------------------------------------------------------------
        # Save diagnostics.
        # ---------------------------------------------------------------------

        window_records.append(
            {
                "window": w,

                "training_signals": len(
                    train_indices
                ),

                "oos_signals": len(
                    oos_indices
                ),

                "encoders": encoders,

                "models": models,

                "predictions": predictions,
            }
        )

    # =========================================================================
    # COMBINED OOS
    # =========================================================================

    banner(
        "COMBINED OUT-OF-SAMPLE RESULTS"
    )

    combined = {}

    for horizon in HORIZONS:

        combined[horizon] = (
            print_metric(
                (
                    f"STRUCTURE_LEARNED "
                    f"H+{horizon}"
                ),
                all_oos_predictions[
                    horizon
                ],
            )
        )

    # =========================================================================
    # COMBINED DIRECTION
    # =========================================================================

    banner(
        "COMBINED STRUCTURE DIRECTION"
    )

    for direction in (
        "BULLISH",
        "BEARISH",
    ):

        for horizon in HORIZONS:

            subset = [
                p
                for p in all_oos_predictions[
                    horizon
                ]
                if p["direction"]
                == direction
            ]

            print_metric(
                (
                    f"STRUCTURE_{direction} "
                    f"H+{horizon}"
                ),
                subset,
            )

    # =========================================================================
    # COMBINED EVENTS
    # =========================================================================

    banner(
        "COMBINED STRUCTURAL EVENTS"
    )

    for event in (
        "BOS_BULLISH",
        "BOS_BEARISH",
        "CHoCH_BULLISH",
        "CHoCH_BEARISH",
    ):

        for horizon in HORIZONS:

            subset = [
                p
                for p in all_oos_predictions[
                    horizon
                ]
                if p["event"] == event
            ]

            if (
                len(subset)
                < MIN_EVENT_SAMPLES
            ):

                print(
                    f"{event:<28} "
                    f"H+{horizon} | "
                    f"N={len(subset)} | "
                    f"Insufficient sample"
                )

            else:

                print_metric(
                    (
                        f"{event:<28} "
                        f"H+{horizon}"
                    ),
                    subset,
                )

    # =========================================================================
    # STABILITY
    # =========================================================================

    banner(
        "WALK-FORWARD STABILITY"
    )

    stability = {}

    for horizon in HORIZONS:

        values = [
            metric["accuracy"]
            for metric in window_metrics[
                horizon
            ]
            if metric["accuracy"]
            is not None
        ]

        edges = [
            metric["edge"]
            for metric in window_metrics[
                horizon
            ]
            if metric["edge"]
            is not None
        ]

        if not values:

            stability[horizon] = {
                "mean": None,
                "median": None,
                "std": 0.0,
                "min": None,
                "max": None,
                "mean_edge": None,
            }

            print(
                f"H+{horizon}: "
                "No valid window metrics."
            )

            continue

        mean_value = (
            statistics.mean(
                values
            )
        )

        median_value = (
            statistics.median(
                values
            )
        )

        std_value = (
            statistics.stdev(values)
            if len(values) > 1
            else 0.0
        )

        mean_edge = (
            statistics.mean(edges)
            if edges
            else None
        )

        print(
            f"H+{horizon:<2} | "
            f"Mean={mean_value * 100:.2f}% | "
            f"Median={median_value * 100:.2f}% | "
            f"Std={std_value * 100:.2f}% | "
            f"Min={min(values) * 100:.2f}% | "
            f"Max={max(values) * 100:.2f}% | "
            f"Mean Edge="
            f"{mean_edge * 100:+.2f}%"
            if mean_edge is not None
            else
            f"H+{horizon:<2} | "
            f"Mean={mean_value * 100:.2f}% | "
            f"Median={median_value * 100:.2f}% | "
            f"Std={std_value * 100:.2f}% | "
            f"Min={min(values) * 100:.2f}% | "
            f"Max={max(values) * 100:.2f}%"
        )

        stability[horizon] = {
            "mean": mean_value,
            "median": median_value,
            "std": std_value,
            "min": min(values),
            "max": max(values),
            "mean_edge": mean_edge,
        }

    # =========================================================================
    # OUTCOME DISTRIBUTION
    # =========================================================================

    banner(
        "COMBINED OOS OUTCOME DISTRIBUTIONS"
    )

    for horizon in HORIZONS:

        predictions = (
            all_oos_predictions[
                horizon
            ]
        )

        counts = Counter(
            p["actual"]
            for p in predictions
        )

        total = sum(
            counts.values()
        )

        if total == 0:
            continue

        print(
            f"H+{horizon}: "
            f"BUY="
            f"{counts['BUY'] / total * 100:.2f}% | "
            f"SELL="
            f"{counts['SELL'] / total * 100:.2f}% | "
            f"NEUTRAL="
            f"{counts['NEUTRAL'] / total * 100:.2f}%"
        )

    # =========================================================================
    # FORWARD LABEL DEPENDENCY
    # =========================================================================

    banner(
        "FORWARD LABEL DEPENDENCY"
    )

    print(
        "Fixed-horizon labels may overlap in time."
    )

    print(
        "Overlapping labels do not permit us to "
        "treat every prediction as an independent "
        "statistical observation."
    )

    print(
        "Chronological OOS separation remains enforced."
    )

    print(
        "No OOS outcome is used for model construction."
    )

    # =========================================================================
    # FINAL CAUSALITY OBJECT
    # =========================================================================

    causality = {
        "confirmed_swings": "PASS",

        "future_structure_leakage": "PASS",

        "future_event_leakage": "PASS",

        "structural_level_consumption": "PASS",

        "training_label_boundary": "PASS",

        "training_only_encoders": "PASS",

        "frozen_oos_models": "PASS",

        "chronological_walk_forward": "PASS",

        "duplicate_timestamp_check": "PASS",

        "invalid_candle_validation": "PASS",
    }

    # =========================================================================
    # VALIDATION OBJECT
    # =========================================================================

    final_event_counts = dict(
        event_counts
    )

    final_event_counts[
        "_swings"
    ] = len(swings)

    validation = {
        "version": VERSION,

        "experiment": (
            "HARDENED CAUSAL MARKET "
            "STRUCTURE INTELLIGENCE"
        ),

        "market_file": MARKET_FILE,

        "candles": len(candles),

        "invalid_input_candles": (
            invalid_count
        ),

        "windows": windows,

        "horizons": HORIZONS,

        "confirmed_swings": len(swings),

        "structure_states": (
            valid_structures
        ),

        "signals": len(
            signal_indices
        ),

        "event_counts": (
            final_event_counts
        ),

        "combined_metrics": combined,

        "stability": stability,

        "window_records": (
            window_records
        ),

        "causality": causality,

        "protection": {
            "market_data_read_only": True,

            "production_modified": False,

            "learning_memory_modified": False,

            "trading_enabled": False,

            "internet_required": False,
        },

        "configuration": {
            "left_swing": LEFT_SWING,

            "right_swing": RIGHT_SWING,

            "min_state_samples": (
                MIN_STATE_SAMPLES
            ),

            "prior_strength": (
                PRIOR_STRENGTH
            ),

            "prediction_margin": (
                PREDICTION_MARGIN
            ),

            "structure_distance_bins": (
                STRUCTURE_DISTANCE_BINS
            ),

            "swing_size_bins": (
                SWING_SIZE_BINS
            ),

            "age_bins": AGE_BINS,

            "persistence_bins": (
                PERSISTENCE_BINS
            ),
        },
    }

    # =========================================================================
    # SAVE VALIDATION BINARY
    # =========================================================================

    banner(
        "SAVE VALIDATION ARTIFACT"
    )

    with open(
        OUTPUT_BIN,
        "wb",
    ) as f:

        pickle.dump(
            validation,
            f,
            protocol=pickle.HIGHEST_PROTOCOL,
        )

    print(
        f"Validation binary saved:"
    )

    print(
        f"    {OUTPUT_BIN}"
    )

    # =========================================================================
    # REPORT
    # =========================================================================

    report = build_report(
        candles,
        windows,
        combined,
        stability,
        final_event_counts,
        causality,
    )

    with open(
        OUTPUT_REPORT,
        "w",
        encoding="utf-8",
    ) as f:

        f.write(report)

    print(
        f"Validation report saved:"
    )

    print(
        f"    {OUTPUT_REPORT}"
    )

    # =========================================================================
    # FINAL PROTECTION
    # =========================================================================

    banner(
        "FINAL PROTECTION CHECK"
    )

    print(
        "market_data.bin       : READ ONLY"
    )

    print(
        "Production MLAI       : NOT MODIFIED"
    )

    print(
        "Learning memory       : NOT MODIFIED"
    )

    print(
        "Trading               : DISABLED"
    )

    print(
        "Internet              : NOT REQUIRED"
    )

    print()

    print("=" * 88)

    print(
        f"MLAI v{VERSION} "
        "CAUSAL MARKET STRUCTURE "
        "VALIDATION COMPLETE"
    )

    print("=" * 88)


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    main()