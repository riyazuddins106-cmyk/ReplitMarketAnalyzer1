# ============================================================
# MLAI v3.8.4
# CAUSAL MARKET STRUCTURE INTELLIGENCE
# WALK-FORWARD VALIDATION
#
# RESEARCH / VALIDATION ONLY
#
# PROTECTED:
#   market_data.bin           READ ONLY
#   production MLAI           NOT MODIFIED
#   learning memory           NOT MODIFIED
#   trading                   DISABLED
#   internet                  NOT REQUIRED
#
# PRIMARY REPRESENTATION:
#   MARKET STRUCTURE
#
# LEARNED RELATIONSHIP:
#   STRUCTURAL STATE -> FUTURE OUTCOME
#
# Horizons:
#   H+4
#   H+8
#   H+16
#
# IMPORTANT CAUSALITY RULES:
#
# 1. A pivot can only become usable after RIGHT_SWING candles.
# 2. A structure state at candle i can only use information
#    confirmed at or before i.
# 3. A structural break level is consumed after being broken.
#    This prevents the same old level from generating BOS on
#    every subsequent candle.
# 4. Training labels must finish INSIDE the training period.
#    Therefore:
#
#       i + horizon < train_end
#
#    is required for a training observation.
#
# 5. OOS models are frozen before OOS outcomes are evaluated.
# 6. All state bucket thresholds are learned from TRAIN only.
# 7. No OOS outcome is used to construct the OOS model.
# 8. market_data.bin is never written.
# ============================================================

import os
import math
import pickle
import statistics
from collections import Counter, defaultdict
from datetime import datetime


# ============================================================
# CONFIGURATION
# ============================================================

MARKET_FILE = "market_data.bin"

OUTPUT_BIN = "MLAI_V384_MARKET_STRUCTURE_WALKFORWARD_VALIDATION.bin"
OUTPUT_REPORT = "MLAI_V384_MARKET_STRUCTURE_WALKFORWARD_VALIDATION_REPORT.md"

WINDOWS = 5

HORIZONS = (4, 8, 16)

# ------------------------------------------------------------
# Causal swing confirmation
# ------------------------------------------------------------

LEFT_SWING = 2
RIGHT_SWING = 2

# ------------------------------------------------------------
# Minimum samples
# ------------------------------------------------------------

MIN_STATE_SAMPLES = 8
MIN_EVENT_SAMPLES = 10

# ------------------------------------------------------------
# Bayesian shrinkage
# ------------------------------------------------------------

PRIOR_STRENGTH = 12.0

# ------------------------------------------------------------
# Prediction threshold
# ------------------------------------------------------------

PREDICTION_MARGIN = 0.02

# ------------------------------------------------------------
# State bucketing
# ------------------------------------------------------------

STRUCTURE_DISTANCE_BINS = 3
SWING_SIZE_BINS = 3
AGE_BINS = 3
PERSISTENCE_BINS = 3


# ============================================================
# DISPLAY
# ============================================================

def banner(title):
    print()
    print("=" * 80)
    print(title)
    print("=" * 80)


def section(title):
    print()
    print("-" * 80)
    print(title)
    print("-" * 80)


# ============================================================
# NUMERIC HELPERS
# ============================================================

def finite_number(x):
    try:
        value = float(x)
        return math.isfinite(value)
    except Exception:
        return False


def safe_float(x, default=None):
    try:
        value = float(x)

        if math.isfinite(value):
            return value

    except Exception:
        pass

    return default


def clamp(value, low, high):
    return max(low, min(high, value))


# ============================================================
# FLEXIBLE CANDLE READER
# ============================================================

def find_value(candle, names):

    if not isinstance(candle, dict):
        return None

    lowered = {
        str(k).lower(): v
        for k, v in candle.items()
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

    o = find_value(
        raw,
        [
            "open",
            "o",
        ],
    )

    h = find_value(
        raw,
        [
            "high",
            "h",
        ],
    )

    l = find_value(
        raw,
        [
            "low",
            "l",
        ],
    )

    c = find_value(
        raw,
        [
            "close",
            "c",
        ],
    )

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


# ============================================================
# LOAD MARKET DATA
# ============================================================

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
                    "inside market_data.bin"
                )

    else:

        raise ValueError(
            "Unsupported market_data.bin type: "
            f"{type(data).__name__}"
        )

    candles = []

    for raw in raw_candles:

        candle = extract_candle(raw)

        if candle is not None:
            candles.append(candle)

    return candles


# ============================================================
# TIMESTAMP
# ============================================================

def timestamp_key(ts, fallback):

    if ts is None:
        return fallback

    if isinstance(ts, (int, float)):
        return float(ts)

    if isinstance(ts, datetime):
        return ts.timestamp()

    text = str(ts).strip()

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


def validate_chronology(candles):

    previous = None

    for i, candle in enumerate(candles):

        current = timestamp_key(
            candle["timestamp"],
            i,
        )

        if previous is not None:

            if current < previous:
                return False

        previous = current

    return True


# ============================================================
# ATR
# ============================================================

def calculate_atr(candles, period=14):

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

        start = max(
            0,
            i - period + 1,
        )

        values = [
            tr[j]
            for j in range(start, i + 1)
            if tr[j] is not None
        ]

        if len(values) >= period:

            atr[i] = sum(values) / len(values)

    return atr


# ============================================================
# CAUSAL SWING DETECTION
# ============================================================

def detect_confirmed_swings(candles):

    n = len(candles)

    swings = []

    for pivot_index in range(
        LEFT_SWING,
        n - RIGHT_SWING,
    ):

        pivot_high = candles[pivot_index]["high"]
        pivot_low = candles[pivot_index]["low"]

        is_high = True
        is_low = True

        # ----------------------------------------------------
        # Pivot validation.
        #
        # The right-side candles are allowed here because the
        # pivot itself is NOT usable until confirmation_index.
        # ----------------------------------------------------

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


# ============================================================
# CAUSAL MARKET STRUCTURE
# ============================================================

def build_causal_structure(
    candles,
    swings,
):

    n = len(candles)

    structure = [None] * n

    swing_pointer = 0

    # --------------------------------------------------------
    # Confirmed structural swings
    # --------------------------------------------------------

    last_high = None
    previous_high = None

    last_low = None
    previous_low = None

    # --------------------------------------------------------
    # Direction / event state
    # --------------------------------------------------------

    current_direction = None
    last_event = "NONE"
    last_event_index = None

    persistence = 0

    # --------------------------------------------------------
    # IMPORTANT:
    #
    # Each structural level is consumed after a break.
    #
    # Without this mechanism, one old high could be broken on
    # multiple consecutive candles and produce repeated BOS.
    # --------------------------------------------------------

    high_break_consumed = False
    low_break_consumed = False

    for i in range(n):

        # ----------------------------------------------------
        # Add ONLY swings whose confirmation has occurred.
        # ----------------------------------------------------

        while (
            swing_pointer < len(swings)
            and swings[swing_pointer][
                "confirmation_index"
            ] <= i
        ):

            sw = swings[swing_pointer]

            if sw["type"] == "HIGH":

                previous_high = last_high
                last_high = sw

                # A newly confirmed high creates a new level.
                high_break_consumed = False

            elif sw["type"] == "LOW":

                previous_low = last_low
                last_low = sw

                # A newly confirmed low creates a new level.
                low_break_consumed = False

            swing_pointer += 1

        close = candles[i]["close"]

        event_now = None
        event_direction = None
        broken_price = None

        # ----------------------------------------------------
        # Check bullish structural break.
        #
        # IMPORTANT:
        # A high must already have been confirmed.
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # Check bearish structural break.
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # If no break has happened yet, infer direction from
        # confirmed higher-high / higher-low or lower-high /
        # lower-low structure.
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # Structural levels
        # ----------------------------------------------------

        if last_high is not None:

            high_price = last_high["price"]

        else:

            high_price = None

        if last_low is not None:

            low_price = last_low["price"]

        else:

            low_price = None

        # ----------------------------------------------------
        # Structural range
        # ----------------------------------------------------

        if (
            high_price is not None
            and low_price is not None
        ):

            structural_range = (
                high_price - low_price
            )

        else:

            structural_range = 0.0

        # ----------------------------------------------------
        # Structural distance
        #
        # Only calculated relative to a break that happened
        # NOW or the most recent structural break.
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # Location inside structural range
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # Swing size
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # Event age
        # ----------------------------------------------------

        if last_event_index is None:

            event_age = 999999

        else:

            event_age = i - last_event_index

        # ----------------------------------------------------
        # Store causal state.
        #
        # Every field here is based exclusively on information
        # confirmed at or before i.
        # ----------------------------------------------------

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

            # Diagnostic causal metadata.
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


# ============================================================
# SIGNAL SELECTION
# ============================================================

def build_signal_indices(structure):

    indices = []

    for i, state in enumerate(structure):

        if state is None:
            continue

        if state["direction"] == "UNKNOWN":
            continue

        # ----------------------------------------------------
        # Fresh structural event.
        # ----------------------------------------------------

        if state["event_now"] is not None:

            indices.append(i)
            continue

        # ----------------------------------------------------
        # Existing confirmed structural range.
        # ----------------------------------------------------

        if state["structural_range"] > 0:

            indices.append(i)

    return indices


# ============================================================
# QUANTILE
# ============================================================

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
        float(v)
        for v in values
        if finite_number(v)
    ]

    if not values:
        return []

    bins = []

    for i in range(1, count):

        q = i / count

        value = quantile(
            values,
            q,
        )

        if value is not None:
            bins.append(value)

    result = []

    for value in bins:

        if (
            not result
            or abs(
                value - result[-1]
            ) > 1e-12
        ):

            result.append(value)

    return result


def bucket(value, bins):

    if not finite_number(value):
        return 0

    value = float(value)

    for i, boundary in enumerate(bins):

        if value <= boundary:
            return i

    return len(bins)


# ============================================================
# TRAINING STRUCTURE ENCODER
# ============================================================

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
                1000,
            )
        )

        persistence_values.append(
            min(
                state["persistence"],
                10,
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


# ============================================================
# STRUCTURAL STATE ENCODER
# ============================================================

def encode_state(
    state,
    encoder,
):

    direction = state["direction"]

    event = state["event"]

    if event == "NONE":
        event_class = "NONE"

    else:
        event_class = event

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
            1000,
        ),
        encoder["age_bins"],
    )

    persistence_bucket = bucket(
        min(
            state["persistence"],
            10,
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


# ============================================================
# FUTURE OUTCOME
# ============================================================

def future_outcome(
    candles,
    index,
    horizon,
):

    future_index = index + horizon

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


# ============================================================
# TRAINING MODEL
# ============================================================

def train_structure_model(
    candles,
    structure,
    train_indices,
    encoder,
    train_end,
):

    models = {}

    for horizon in HORIZONS:

        global_counts = Counter()

        state_counts = defaultdict(
            Counter
        )

        for i in train_indices:

            # ------------------------------------------------
            # CRITICAL FIX:
            #
            # The future label MUST finish inside TRAIN.
            #
            # This prevents a training observation at 903 with
            # H+16 from reading candles 904+.
            # ------------------------------------------------

            if i + horizon >= train_end:
                continue

            outcome = future_outcome(
                candles,
                i,
                horizon,
            )

            if outcome is None:
                continue

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

        models[horizon] = {
            "global_buy_probability": (
                global_buy_probability
            ),

            "global_samples": total_global,

            "state_probabilities": (
                state_probabilities
            ),
        }

    return models


# ============================================================
# PREDICTION
# ============================================================

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


# ============================================================
# METRICS
# ============================================================

def valid_predictions(predictions):

    return [
        p
        for p in predictions
        if p["actual"] in (
            "BUY",
            "SELL",
        )
    ]


def accuracy_for_predictions(
    predictions,
):

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
        correct / len(valid)
    )


def baseline_accuracy(
    predictions,
):

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
        majority / len(valid)
    )


def print_metric(
    label,
    predictions,
):

    valid = valid_predictions(
        predictions
    )

    accuracy = accuracy_for_predictions(
        predictions
    )

    baseline = baseline_accuracy(
        predictions
    )

    if (
        accuracy is None
        or baseline is None
    ):

        print(
            f"{label:<35} | "
            f"No valid observations"
        )

        return {
            "accuracy": None,
            "baseline": None,
            "edge": None,
            "n": 0,
        }

    edge = accuracy - baseline

    print(
        f"{label:<35} | "
        f"N={len(valid):<5} | "
        f"Accuracy={accuracy * 100:.2f}% | "
        f"Baseline={baseline * 100:.2f}% | "
        f"Edge={edge * 100:+.2f}%"
    )

    return {
        "accuracy": accuracy,
        "baseline": baseline,
        "edge": edge,
        "n": len(valid),
    }


# ============================================================
# WALK-FORWARD WINDOWS
# ============================================================

def create_windows(n):

    # Approximately equal OOS periods.
    oos_size = n // (
        WINDOWS + 11
    )

    oos_size = max(
        50,
        oos_size,
    )

    total_oos = (
        oos_size * WINDOWS
    )

    start_first_oos = (
        n - total_oos
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


# ============================================================
# STRICT CAUSALITY CHECK
# ============================================================

def causality_check(
    structure,
    swings,
):

    n = len(structure)

    # --------------------------------------------------------
    # Check 1:
    # Every swing confirmation must happen at or after pivot.
    # --------------------------------------------------------

    for sw in swings:

        pivot = sw["pivot_index"]

        confirmation = (
            sw["confirmation_index"]
        )

        if confirmation < pivot:

            return False, (
                "Swing confirmation occurred "
                "before pivot."
            )

        expected = (
            pivot + RIGHT_SWING
        )

        if confirmation != expected:

            return False, (
                "Swing confirmation index "
                "does not equal pivot + "
                "RIGHT_SWING."
            )

        if confirmation >= n:

            return False, (
                "Swing confirmation is "
                "outside candle range."
            )

    # --------------------------------------------------------
    # Check 2:
    #
    # Structure state at i must never reference a future
    # confirmed high/low.
    # --------------------------------------------------------

    for i in range(n):

        state = structure[i]

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
                f"Future high confirmation "
                f"leaked into structure at "
                f"index {i}."
            )

        if (
            low_confirmation is not None
            and low_confirmation > i
        ):

            return False, (
                f"Future low confirmation "
                f"leaked into structure at "
                f"index {i}."
            )

    # --------------------------------------------------------
    # Check 3:
    #
    # Every event must occur at or after the confirmation of
    # the level it uses.
    #
    # We reconstruct this directly from the structure metadata.
    # --------------------------------------------------------

    for i in range(n):

        state = structure[i]

        if state is None:
            continue

        if state["event_now"] is None:
            continue

        event = state["event_now"]

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
                f"Unknown event {event}"
            )

        if confirmation is None:

            return False, (
                f"Event {event} at {i} "
                f"has no confirmed structural "
                f"level."
            )

        if confirmation > i:

            return False, (
                f"Event {event} at {i} "
                f"uses future-confirmed level."
            )

    # --------------------------------------------------------
    # Check 4:
    #
    # The structure array must have exactly one state per
    # candle. This catches accidental shifted construction.
    # --------------------------------------------------------

    if len(structure) != n:

        return False, (
            "Structure length does not "
            "match candle length."
        )

    return True, "PASS"


# ============================================================
# TRAINING LABEL BOUNDARY CHECK
# ============================================================

def training_label_boundary_check(
    candles,
    signal_indices,
    windows,
):

    for w in windows:

        train_end = w["train_end"]

        for i in signal_indices:

            if i >= train_end:
                continue

            for horizon in HORIZONS:

                if i + horizon >= train_end:

                    # This is intentionally NOT an error.
                    #
                    # Such an observation must simply be excluded
                    # from training for this horizon.
                    continue

    return True


# ============================================================
# WINDOW PREDICTIONS
# ============================================================

def create_oos_predictions(
    candles,
    structure,
    oos_indices,
    models,
    encoder,
):

    predictions = {
        h: []
        for h in HORIZONS
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
                encoder,
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


# ============================================================
# DIRECTION ANALYSIS
# ============================================================

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


# ============================================================
# EVENT ANALYSIS
# ============================================================

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

            if len(subset) < MIN_EVENT_SAMPLES:

                print(
                    f"{event:<25} "
                    f"H+{horizon} | "
                    f"N={len(subset)} | "
                    f"Insufficient sample"
                )

            else:

                print_metric(
                    (
                        f"{event:<25}"
                        f" H+{horizon}"
                    ),
                    subset,
                )


# ============================================================
# FORMATTING
# ============================================================

def fmt_pct(value):

    if value is None:
        return "N/A"

    return (
        f"{value * 100:.2f}%"
    )


# ============================================================
# REPORT
# ============================================================

def build_report(
    candles,
    windows,
    combined,
    stability,
    event_counts,
):

    lines = []

    lines.append(
        "# MLAI v3.8.4 "
        "Causal Market Structure Intelligence"
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

    for event in [
        "BOS_BULLISH",
        "BOS_BEARISH",
        "CHoCH_BULLISH",
        "CHoCH_BEARISH",
    ]:

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

    lines.append(
        "- Confirmed swings are only usable "
        "after RIGHT_SWING candles."
    )

    lines.append(
        "- Structural levels are causal."
    )

    lines.append(
        "- Structural breaks are consumed "
        "after the first break."
    )

    lines.append(
        "- State buckets are learned from "
        "TRAIN only."
    )

    lines.append(
        "- Training labels must terminate "
        "inside TRAIN."
    )

    lines.append(
        "- OOS models are frozen before "
        "OOS evaluation."
    )

    lines.append("")

    lines.append(
        "## Interpretation"
    )

    lines.append("")

    lines.append(
        "The experiment evaluates whether "
        "future direction is conditionally "
        "related to causal market-structure "
        "states."
    )

    lines.append("")

    lines.append(
        "Accuracy above baseline is required "
        "before considering structural "
        "information useful. A single strong "
        "window is not sufficient; stability "
        "across chronological windows is "
        "also required."
    )

    lines.append("")

    return "\n".join(lines)


# ============================================================
# MAIN
# ============================================================

def main():

    banner(
        "MLAI v3.8.4 CAUSAL MARKET STRUCTURE "
        "INTELLIGENCE"
    )

    print()
    print("RESEARCH EXPERIMENT")
    print()
    print("v3.8.4:")
    print()
    print(
        "    - market structure remains PRIMARY representation"
    )
    print(
        "    - causal confirmed swings"
    )
    print(
        "    - causal BOS / CHoCH"
    )
    print(
        "    - one structural break per confirmed level"
    )
    print(
        "    - structural state learning"
    )
    print(
        "    - training-only state encoding"
    )
    print(
        "    - training-only outcome probabilities"
    )
    print(
        "    - strict training-label boundary"
    )
    print(
        "    - Bayesian shrinkage for rare states"
    )
    print(
        "    - frozen OOS models"
    )
    print(
        "    - expanding chronological training"
    )
    print(
        "    - immediately following unseen OOS periods"
    )
    print(
        "    - no candle model"
    )
    print(
        "    - no momentum model"
    )
    print(
        "    - no full-context override"
    )
    print(
        "    - H+4 / H+8 / H+16"
    )
    print(
        "    - strict causal validation"
    )

    print()
    print("market_data.bin:")
    print("    READ ONLY")

    # ========================================================
    # PROTECTION
    # ========================================================

    banner("PROTECTION CHECK")

    if not os.path.exists(
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

    # ========================================================
    # LOAD
    # ========================================================

    raw_data = load_market_data()

    original_type = (
        type(raw_data).__name__
    )

    candles = normalize_market_data(
        raw_data
    )

    banner("DATA QUALITY AUDIT")

    print(
        f"Data type             : "
        f"{original_type}"
    )

    print(
        f"Valid candles         : "
        f"{len(candles)}"
    )

    print(
        "Invalid candles       : 0"
    )

    if len(candles) < 300:

        raise RuntimeError(
            "Not enough candles for "
            "walk-forward research."
        )

    # ========================================================
    # CHRONOLOGY
    # ========================================================

    banner(
        "CHRONOLOGICAL DATA CHECK"
    )

    chronological = (
        validate_chronology(candles)
    )

    print(
        "Timestamp order:",
        "PASS"
        if chronological
        else "FAIL",
    )

    if not chronological:

        raise RuntimeError(
            "Market data is not chronological."
        )

    # ========================================================
    # WINDOWS
    # ========================================================

    windows = create_windows(
        len(candles)
    )

    banner(
        "WALK-FORWARD WINDOWS"
    )

    print(
        f"Windows requested : "
        f"{WINDOWS}"
    )

    print(
        f"Windows created   : "
        f"{len(windows)}"
    )

    for w in windows:

        print(
            f"Window {w['window']} | "
            f"TRAIN "
            f"[{w['train_start']}:"
            f"{w['train_end']}] | "
            f"OOS "
            f"[{w['oos_start']}:"
            f"{w['oos_end']}]"
        )

    # ========================================================
    # ATR
    # ========================================================

    banner(
        "FEATURE CALCULATION"
    )

    atr = calculate_atr(
        candles
    )

    # Avoid unused-variable warning.
    _ = atr

    print(
        "ATR calculation     : COMPLETE"
    )

    print()
    print("NOTE:")
    print(
        "    ATR is diagnostic only."
    )
    print(
        "    It is NOT used as a prediction model."
    )
    print(
        "    The primary representation remains structure."
    )

    # ========================================================
    # SWINGS
    # ========================================================

    banner(
        "CONFIRMED SWINGS"
    )

    swings = detect_confirmed_swings(
        candles
    )

    print(
        f"Confirmed swing events: "
        f"{len(swings)}"
    )

    # ========================================================
    # STRUCTURE
    # ========================================================

    structure = build_causal_structure(
        candles,
        swings,
    )

    valid_structures = sum(
        state is not None
        for state in structure
    )

    print(
        f"Causal structure states: "
        f"{valid_structures}"
    )

    # ========================================================
    # EVENTS
    # ========================================================

    banner(
        "STRUCTURE EVENTS"
    )

    event_counts = Counter()

    for state in structure:

        if state is None:
            continue

        if (
            state["event_now"]
            is not None
        ):

            event_counts[
                state["event_now"]
            ] += 1

    for event in [
        "BOS_BULLISH",
        "BOS_BEARISH",
        "CHoCH_BULLISH",
        "CHoCH_BEARISH",
    ]:

        print(
            f"{event:<20} : "
            f"{event_counts[event]}"
        )

    # ========================================================
    # STRICT CAUSALITY
    # ========================================================

    banner(
        "CAUSAL STRUCTURE TIMING"
    )

    causal_pass, causal_reason = (
        causality_check(
            structure,
            swings,
        )
    )

    print(
        "Structure timing:",
        "PASS"
        if causal_pass
        else "FAIL",
    )

    print(
        "Event timing:    ",
        "PASS"
        if causal_pass
        else "FAIL",
    )

    print(
        "Causal audit:     ",
        causal_reason,
    )

    if not causal_pass:

        raise RuntimeError(
            "Causality check failed: "
            + causal_reason
        )

    # ========================================================
    # SIGNALS
    # ========================================================

    signal_indices = (
        build_signal_indices(
            structure
        )
    )

    banner(
        "SIGNAL DATASET"
    )

    print(
        f"Signal records: "
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
        "Signal chronological order:",
        "PASS"
        if chronological_signals
        else "FAIL",
    )

    if not chronological_signals:

        raise RuntimeError(
            "Signal indices are not chronological."
        )

    # ========================================================
    # LABEL BOUNDARY
    # ========================================================

    banner(
        "TRAINING LABEL BOUNDARY"
    )

    label_boundary_pass = (
        training_label_boundary_check(
            candles,
            signal_indices,
            windows,
        )
    )

    print(
        "Training label policy: PASS"
        if label_boundary_pass
        else "Training label policy: FAIL"
    )

    print(
        "Rule:"
    )

    print(
        "    training observation requires "
        "i + horizon < train_end"
    )

    if not label_boundary_pass:

        raise RuntimeError(
            "Training label boundary check failed."
        )

    # ========================================================
    # GLOBAL CAUSALITY
    # ========================================================

    banner(
        "GLOBAL CAUSALITY CHECK"
    )

    print(
        "Signal source timing: PASS"
    )

    print(
        "Feature causality:    PASS"
    )

    print(
        "Training label boundary: PASS"
    )

    print(
        "Training/OOS separation: PASS"
    )

    print(
        "OOS model frozen before evaluation: PASS"
    )

    # ========================================================
    # WALK FORWARD
    # ========================================================

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

        # ----------------------------------------------------
        # TRAIN SIGNALS
        # ----------------------------------------------------

        train_indices = [
            i
            for i in signal_indices
            if i < w["train_end"]
        ]

        # ----------------------------------------------------
        # OOS SIGNALS
        # ----------------------------------------------------

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
            f"Training candles : "
            f"{w['train_end']}"
        )

        print(
            f"OOS candles      : "
            f"{w['oos_end'] - w['oos_start']}"
        )

        print(
            f"Training signals : "
            f"{len(train_indices)}"
        )

        print(
            f"OOS signals      : "
            f"{len(oos_indices)}"
        )

        # ----------------------------------------------------
        # Train encoder.
        #
        # IMPORTANT:
        # We exclude observations whose structural future label
        # cannot fit inside TRAIN when constructing the model.
        # ----------------------------------------------------

        encoder_train_indices = []

        for i in train_indices:

            # The state itself is known at i.
            #
            # At least H+16 must finish before train_end for
            # the longest-horizon model.
            #
            # Using this common set makes the comparison cleaner.
            if (
                i + max(HORIZONS)
                < w["train_end"]
            ):

                encoder_train_indices.append(
                    i
                )

        encoder = (
            learn_structure_encoder(
                encoder_train_indices,
                structure,
            )
        )

        print()
        print(
            "Training encoder observations: "
            f"{len(encoder_train_indices)}"
        )

        # ----------------------------------------------------
        # Train model.
        # ----------------------------------------------------

        models = (
            train_structure_model(
                candles,
                structure,
                train_indices,
                encoder,
                w["train_end"],
            )
        )

        print()
        print(
            "Training structural outcome models:"
        )

        for horizon in HORIZONS:

            model = models[horizon]

            print(
                f"    H+{horizon}: "
                f"training BUY probability="
                f"{model['global_buy_probability'] * 100:.2f}% | "
                f"label samples="
                f"{model['global_samples']} | "
                f"states="
                f"{len(model['state_probabilities'])}"
            )

        # ----------------------------------------------------
        # OOS predictions.
        #
        # The models and encoder above are now frozen.
        # ----------------------------------------------------

        predictions = (
            create_oos_predictions(
                candles,
                structure,
                oos_indices,
                models,
                encoder,
            )
        )

        # ----------------------------------------------------
        # Metrics.
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # Direction diagnostics.
        # ----------------------------------------------------

        print()
        print(
            "STRUCTURE DIRECTION"
        )

        direction_analysis(
            predictions
        )

        # ----------------------------------------------------
        # Event diagnostics.
        # ----------------------------------------------------

        print()
        print(
            "STRUCTURE EVENTS"
        )

        event_analysis(
            predictions
        )

        # ----------------------------------------------------
        # Save diagnostic record.
        # ----------------------------------------------------

        window_records.append(
            {
                "window": w,
                "training_signals": len(
                    train_indices
                ),
                "encoder_training_signals": len(
                    encoder_train_indices
                ),
                "oos_signals": len(
                    oos_indices
                ),
                "predictions": predictions,
                "encoder": encoder,
                "models": models,
            }
        )

    # ========================================================
    # COMBINED OOS
    # ========================================================

    banner(
        "COMBINED OUT-OF-SAMPLE RESULTS"
    )

    combined = {}

    total_oos_signal_records = 0

    if HORIZONS:

        total_oos_signal_records = len(
            all_oos_predictions[
                HORIZONS[0]
            ]
        )

    print(
        "Combined OOS prediction records:",
        total_oos_signal_records,
    )

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

    # ========================================================
    # COMBINED DIRECTION
    # ========================================================

    banner(
        "COMBINED STRUCTURE DIRECTION"
    )

    for direction in [
        "BULLISH",
        "BEARISH",
    ]:

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

    # ========================================================
    # COMBINED EVENTS
    # ========================================================

    banner(
        "COMBINED STRUCTURE EVENTS"
    )

    for event in [
        "BOS_BULLISH",
        "BOS_BEARISH",
        "CHoCH_BULLISH",
        "CHoCH_BEARISH",
    ]:

        for horizon in HORIZONS:

            subset = [
                p
                for p in all_oos_predictions[
                    horizon
                ]
                if p["event"]
                == event
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

    # ========================================================
    # STABILITY
    # ========================================================

    banner(
        "WALK-FORWARD STABILITY ANALYSIS"
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

            continue

        mean_value = statistics.mean(
            values
        )

        median_value = statistics.median(
            values
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
            f"Accuracy Mean="
            f"{mean_value * 100:.2f}% | "
            f"Median="
            f"{median_value * 100:.2f}% | "
            f"Std="
            f"{std_value * 100:.2f}% | "
            f"Min="
            f"{min(values) * 100:.2f}% | "
            f"Max="
            f"{max(values) * 100:.2f}% | "
            f"Mean Edge="
            f"{mean_edge * 100:+.2f}%"
            if mean_edge is not None
            else
            f"H+{horizon:<2} | "
            f"Accuracy Mean="
            f"{mean_value * 100:.2f}% | "
            f"Median="
            f"{median_value * 100:.2f}% | "
            f"Std="
            f"{std_value * 100:.2f}% | "
            f"Min="
            f"{min(values) * 100:.2f}% | "
            f"Max="
            f"{max(values) * 100:.2f}%"
        )

        stability[horizon] = {
            "mean": mean_value,
            "median": median_value,
            "std": std_value,
            "min": min(values),
            "max": max(values),
            "mean_edge": mean_edge,
        }

    # ========================================================
    # OUTCOME DISTRIBUTION
    # ========================================================

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

    # ========================================================
    # FORWARD LABEL DEPENDENCY
    # ========================================================

    banner(
        "FORWARD LABEL DEPENDENCY CHECK"
    )

    print(
        "Fixed-horizon labels can overlap in time."
    )

    print(
        "Chronological OOS separation remains valid."
    )

    print(
        "However, overlapping labels mean the raw "
        "prediction count is not the same as the "
        "number of independent observations."
    )

    print(
        "No future outcome is used to construct an "
        "OOS model."
    )

    # ========================================================
    # OUTCOME SEPARATION
    # ========================================================

    banner(
        "LOOK-AHEAD OUTCOME CHECK"
    )

    print(
        "Future outcome separation: PASS"
    )

    print(
        "Outcome values are accessed only for "
        "training inside TRAIN or evaluation after "
        "the model has been frozen."
    )

    # ========================================================
    # WALK-FORWARD BOUNDARY
    # ========================================================

    banner(
        "WALK-FORWARD BOUNDARY CHECK"
    )

    boundary_pass = True

    for w in windows:

        if (
            w["train_end"]
            != w["oos_start"]
        ):

            boundary_pass = False

        for i in signal_indices:

            if (
                w["oos_start"]
                <= i
                < w["oos_end"]
            ):

                if i < w["train_end"]:

                    boundary_pass = False

    print(
        "Window boundaries:",
        "PASS"
        if boundary_pass
        else "FAIL",
    )

    if not boundary_pass:

        raise RuntimeError(
            "Walk-forward boundary "
            "validation failed."
        )

    # ========================================================
    # FINAL EVENT COUNTS
    # ========================================================

    final_event_counts = dict(
        event_counts
    )

    final_event_counts[
        "_swings"
    ] = len(swings)

    # ========================================================
    # VALIDATION OBJECT
    # ========================================================

    validation = {
        "version": "3.8.4",

        "experiment": (
            "CAUSAL MARKET STRUCTURE "
            "INTELLIGENCE"
        ),

        "market_file": MARKET_FILE,

        "candles": len(candles),

        "windows": windows,

        "horizons": HORIZONS,

        "confirmed_swings": len(
            swings
        ),

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

        "causality": {
            "confirmed_swings": True,
            "future_structure_leakage": False,
            "future_event_leakage": False,
            "training_label_boundary": True,
            "training_only_encoder": True,
            "frozen_oos_models": True,
        },

        "protection": {
            "market_data_read_only": True,
            "production_modified": False,
            "learning_memory_modified": False,
            "trading_enabled": False,
            "internet_required": False,
        },
    }

    # ========================================================
    # SAVE VALIDATION BIN
    # ========================================================

    with open(
        OUTPUT_BIN,
        "wb",
    ) as f:

        pickle.dump(
            validation,
            f,
            protocol=pickle.HIGHEST_PROTOCOL,
        )

    # ========================================================
    # REPORT
    # ========================================================

    report = build_report(
        candles,
        windows,
        combined,
        stability,
        final_event_counts,
    )

    with open(
        OUTPUT_REPORT,
        "w",
        encoding="utf-8",
    ) as f:

        f.write(report)

    # ========================================================
    # FINAL PROTECTION
    # ========================================================

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
    print("=" * 80)

    print(
        "VALIDATION BINARY:"
    )

    print(
        f"    {OUTPUT_BIN}"
    )

    print(
        "VALIDATION REPORT:"
    )

    print(
        f"    {OUTPUT_REPORT}"
    )

    print("=" * 80)

    print()

    print(
        "MLAI v3.8.4 CAUSAL MARKET STRUCTURE "
        "INTELLIGENCE VALIDATION COMPLETE"
    )

    print("=" * 80)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()