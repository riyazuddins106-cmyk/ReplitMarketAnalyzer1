import os
import pickle
import math
import random
from collections import Counter, defaultdict
from itertools import combinations


# ============================================================
# MLAI v3.4.0 MARKET LANGUAGE RESEARCH AUDIT
# ============================================================
#
# PURPOSE
# -------
# This is a READ-ONLY research experiment.
#
# It does NOT modify:
#
#   market_data.bin
#   mlai_v31.py
#   production learning memory
#   production thresholds
#
# The purpose is to test whether market structure contains
# repeatable, generalizable information under strict
# chronological validation.
#
# IMPORTANT:
#
# This is NOT a trading-signal generator.
#
# The objective is to investigate:
#
#   1. Market representation
#   2. Context
#   3. Candle behaviour
#   4. Sequences
#   5. Regimes
#   6. Historical similarity
#   7. Probability
#   8. Calibration
#   9. Generalization
#   10. Overfitting risk
#
# ============================================================


MARKET_FILE = "market_data.bin"

WINDOW = 60

HORIZONS = [4, 8, 16]

CLASSIFICATION_THRESHOLD = 0.0015

WALK_FORWARD_FOLDS = 4

MIN_CALIBRATION_SAMPLES = 40
MIN_VALIDATION_SAMPLES = 20

MIN_RULE_SAMPLES = 30

MIN_RULE_CONFIDENCE = 0.50

MIN_LIFT = 0.03

MAX_RULES_FOR_VALIDATION = 100

TOP_RULES_TO_PRINT = 20

QUANTILE_BINS = 3

NEIGHBOR_K = [10, 20, 40]

RANDOM_SEED = 42

PERMUTATION_TESTS = 100

SEQUENCE_LENGTHS = [2, 3, 5]


# ============================================================
# BASIC UTILITIES
# ============================================================

def safe_div(a, b):
    if b == 0:
        return 0.0
    return a / b


def mean(values):
    if not values:
        return 0.0
    return sum(values) / len(values)


def std(values):
    if len(values) < 2:
        return 0.0

    m = mean(values)

    return math.sqrt(
        sum((x - m) ** 2 for x in values)
        / (len(values) - 1)
    )


def clamp(value, low, high):
    return max(low, min(high, value))


# ============================================================
# PROTECTION
# ============================================================

def protection_check():

    print("=" * 80)
    print("PROTECTION CHECK")
    print("=" * 80)

    print("market_data.bin : READ ONLY")
    print("mlai_v31.py     : NOT MODIFIED")
    print("production      : NOT MODIFIED")
    print("learning memory : NOT MODIFIED")
    print()

    if not os.path.exists(MARKET_FILE):
        raise FileNotFoundError(
            f"{MARKET_FILE} not found."
        )


# ============================================================
# LOAD MARKET DATA
# ============================================================

def load_market_data():

    with open(MARKET_FILE, "rb") as f:
        return pickle.load(f)


def extract_candles(data):

    if isinstance(data, dict):

        for key in [
            "candles",
            "data",
            "market_data",
            "ohlcv",
        ]:

            if (
                key in data
                and isinstance(data[key], list)
            ):
                return data[key]

        if all(
            k in data
            for k in [
                "open",
                "high",
                "low",
                "close",
            ]
        ):

            opens = data["open"]
            highs = data["high"]
            lows = data["low"]
            closes = data["close"]

            n = min(
                len(opens),
                len(highs),
                len(lows),
                len(closes),
            )

            return [
                {
                    "open": opens[i],
                    "high": highs[i],
                    "low": lows[i],
                    "close": closes[i],
                }
                for i in range(n)
            ]

    if isinstance(data, list):
        return data

    raise ValueError(
        "Unsupported market_data.bin structure."
    )


def get_value(candle, key, default=0.0):

    if not isinstance(candle, dict):
        return default

    try:
        value = float(
            candle.get(
                key,
                default
            )
        )

        if not math.isfinite(value):
            return default

        return value

    except Exception:
        return default


# ============================================================
# LOAD
# ============================================================

protection_check()

market_data = load_market_data()

candles = extract_candles(
    market_data
)

opens = [
    get_value(c, "open")
    for c in candles
]

highs = [
    get_value(c, "high")
    for c in candles
]

lows = [
    get_value(c, "low")
    for c in candles
]

closes = [
    get_value(c, "close")
    for c in candles
]

print(
    "Data type:",
    type(market_data).__name__
)

print(
    "Total candles:",
    len(candles)
)

print(
    "PASS: market_data.bin loaded."
)

print(
    "PASS: OHLC extracted."
)


# ============================================================
# DATA QUALITY
# ============================================================

def data_quality_report():

    print()
    print("=" * 80)
    print("DATA QUALITY AUDIT")
    print("=" * 80)

    invalid = 0
    zero_close = 0
    negative_prices = 0
    malformed_ranges = 0

    for i in range(len(candles)):

        o = opens[i]
        h = highs[i]
        l = lows[i]
        c = closes[i]

        if not all(
            math.isfinite(x)
            for x in [o, h, l, c]
        ):
            invalid += 1
            continue

        if c <= 0:
            zero_close += 1

        if any(
            x < 0
            for x in [o, h, l, c]
        ):
            negative_prices += 1

        if h < max(o, c):
            malformed_ranges += 1

        if l > min(o, c):
            malformed_ranges += 1

    print(
        "Invalid candles:",
        invalid
    )

    print(
        "Non-positive closes:",
        zero_close
    )

    print(
        "Negative prices:",
        negative_prices
    )

    print(
        "Malformed OHLC ranges:",
        malformed_ranges
    )

    if invalid == 0 and malformed_ranges == 0:
        print(
            "PASS: basic OHLC integrity appears valid."
        )
    else:
        print(
            "WARNING: data quality problems detected."
        )


data_quality_report()


# ============================================================
# CANDLE FEATURES
# ============================================================

def candle_features(index):

    o = opens[index]
    h = highs[index]
    l = lows[index]
    c = closes[index]

    candle_range = max(
        h - l,
        1e-12
    )

    body = abs(c - o)

    upper_wick = max(
        0.0,
        h - max(o, c)
    )

    lower_wick = max(
        0.0,
        min(o, c) - l
    )

    return {
        "body_ratio":
            body / candle_range,

        "upper_wick_ratio":
            upper_wick / candle_range,

        "lower_wick_ratio":
            lower_wick / candle_range,

        "close_location":
            (c - l) / candle_range,

        "range":
            candle_range,

        "body":
            body,

        "bullish":
            c > o,

        "bearish":
            c < o,
    }


# ============================================================
# CANDLE CLASSIFICATION
# ============================================================

def candle_type(index):

    f = candle_features(index)

    body = f["body_ratio"]

    upper = f["upper_wick_ratio"]

    lower = f["lower_wick_ratio"]

    location = f["close_location"]

    if body < 0.10:
        return "doji"

    if lower > 0.55 and body < 0.35:
        return "hammer_like"

    if upper > 0.55 and body < 0.35:
        return "shooting_star_like"

    if body > 0.75:

        if f["bullish"]:
            return "strong_bullish"

        if f["bearish"]:
            return "strong_bearish"

    if f["bullish"] and location > 0.75:
        return "bullish_close_strong"

    if f["bearish"] and location < 0.25:
        return "bearish_close_strong"

    return "normal"


# ============================================================
# RETURN
# ============================================================

def return_from(index, periods):

    target = index - periods

    if target < 0:
        return 0.0

    previous = closes[target]

    current = closes[index]

    if previous == 0:
        return 0.0

    return (
        current - previous
    ) / previous


# ============================================================
# STRUCTURE FEATURES
# ============================================================

def structure_features(index):

    start = (
        index
        - WINDOW
        + 1
    )

    if start < 0:
        return None

    if closes[index] <= 0:
        return None

    window_closes = closes[
        start:index + 1
    ]

    returns = []

    for j in range(
        start + 1,
        index + 1
    ):

        previous = closes[j - 1]

        if previous != 0:

            returns.append(
                (
                    closes[j]
                    - previous
                )
                / previous
            )

    volatility = std(
        returns
    )

    recent_returns = (
        returns[-20:]
        if len(returns) >= 20
        else returns
    )

    recent_volatility = std(
        recent_returns
    )

    volatility_ratio = (
        safe_div(
            volatility,
            recent_volatility
        )
        if recent_volatility
        else 1.0
    )

    bullish = 0
    bearish = 0

    body_ratios = []
    upper_wicks = []
    lower_wicks = []
    ranges = []

    for j in range(
        start,
        index + 1
    ):

        f = candle_features(j)

        if f["bullish"]:
            bullish += 1

        elif f["bearish"]:
            bearish += 1

        body_ratios.append(
            f["body_ratio"]
        )

        upper_wicks.append(
            f["upper_wick_ratio"]
        )

        lower_wicks.append(
            f["lower_wick_ratio"]
        )

        ranges.append(
            f["range"]
        )

    total = max(
        len(window_closes),
        1
    )

    bullish_ratio = (
        bullish / total
    )

    bearish_ratio = (
        bearish / total
    )

    imbalance = (
        bullish_ratio
        - bearish_ratio
    )

    high60 = max(
        highs[start:index + 1]
    )

    low60 = min(
        lows[start:index + 1]
    )

    range60 = max(
        high60 - low60,
        1e-12
    )

    location = (
        closes[index]
        - low60
    ) / range60

    momentum_5 = return_from(
        index,
        5
    )

    momentum_10 = return_from(
        index,
        10
    )

    momentum_20 = return_from(
        index,
        20
    )

    momentum_30 = return_from(
        index,
        30
    )

    momentum_60 = return_from(
        index,
        59
    )

    acceleration = (
        momentum_5
        - momentum_10
    )

    slope = momentum_60

    if slope > 0.002:
        regime = "bullish"

    elif slope < -0.002:
        regime = "bearish"

    else:
        regime = "neutral"

    if abs(slope) > 0.005:
        consistency = "strong"

    elif abs(slope) > 0.002:
        consistency = "moderate"

    else:
        consistency = "weak"

    if volatility_ratio > 1.15:
        volatility_regime = "expanding"

    elif volatility_ratio < 0.85:
        volatility_regime = "contracting"

    else:
        volatility_regime = "stable"

    if location >= 0.75:
        location_state = "upper_range"

    elif location <= 0.25:
        location_state = "lower_range"

    else:
        location_state = "middle_range"

    if (
        momentum_5 > 0
        and momentum_10 > 0
    ):
        momentum_state = "bullish"

    elif (
        momentum_5 < 0
        and momentum_10 < 0
    ):
        momentum_state = "bearish"

    else:
        momentum_state = "mixed"

    if bullish_ratio > 0.55:
        pressure = "bullish"

    elif bearish_ratio > 0.55:
        pressure = "bearish"

    else:
        pressure = "balanced"

    if location >= 0.90:
        range_event = "near_high"

    elif location <= 0.10:
        range_event = "near_low"

    else:
        range_event = "inside_range"

    sequence = tuple(
        candle_type(j)
        for j in range(
            max(start, index - 4),
            index + 1
        )
    )

    return {

        "return_5":
            momentum_5,

        "return_10":
            momentum_10,

        "return_20":
            momentum_20,

        "return_30":
            momentum_30,

        "return_60":
            momentum_60,

        "bullish_ratio":
            bullish_ratio,

        "bearish_ratio":
            bearish_ratio,

        "directional_imbalance":
            imbalance,

        "volatility":
            volatility,

        "volatility_ratio":
            volatility_ratio,

        "location_in_range":
            location,

        "normalized_slope":
            slope,

        "momentum_acceleration":
            acceleration,

        "recent_body_ratio":
            mean(
                body_ratios[-10:]
            ),

        "recent_upper_wick":
            mean(
                upper_wicks[-10:]
            ),

        "recent_lower_wick":
            mean(
                lower_wicks[-10:]
            ),

        "recent_range":
            mean(
                ranges[-10:]
            ),

        "directional_regime":
            regime,

        "trend_consistency":
            consistency,

        "volatility_regime":
            volatility_regime,

        "location_state":
            location_state,

        "momentum_state":
            momentum_state,

        "pressure":
            pressure,

        "range_event":
            range_event,

        "latest_candle":
            candle_type(index),

        "candle_sequence":
            sequence,
    }


# ============================================================
# MARKET STRUCTURE SWINGS
# ============================================================

def detect_swing(index, radius=2):

    if (
        index - radius < 0
        or index + radius >= len(candles)
    ):
        return None

    high = highs[index]
    low = lows[index]

    left_highs = highs[
        index - radius:index
    ]

    right_highs = highs[
        index + 1:index + radius + 1
    ]

    left_lows = lows[
        index - radius:index
    ]

    right_lows = lows[
        index + 1:index + radius + 1
    ]

    if all(
        high > x
        for x in left_highs
        + right_highs
    ):
        return "swing_high"

    if all(
        low < x
        for x in left_lows
        + right_lows
    ):
        return "swing_low"

    return None


def market_structure_state(index):

    start = max(
        0,
        index - 60
    )

    swing_highs = []
    swing_lows = []

    for i in range(
        start,
        index
    ):

        swing = detect_swing(i)

        if swing == "swing_high":
            swing_highs.append(
                (i, highs[i])
            )

        elif swing == "swing_low":
            swing_lows.append(
                (i, lows[i])
            )

    if len(swing_highs) < 2:
        high_state = "unknown"
    else:

        previous = swing_highs[-2][1]
        latest = swing_highs[-1][1]

        if latest > previous:
            high_state = "higher_high"

        elif latest < previous:
            high_state = "lower_high"

        else:
            high_state = "equal_high"

    if len(swing_lows) < 2:
        low_state = "unknown"
    else:

        previous = swing_lows[-2][1]
        latest = swing_lows[-1][1]

        if latest > previous:
            low_state = "higher_low"

        elif latest < previous:
            low_state = "lower_low"

        else:
            low_state = "equal_low"

    if (
        high_state == "higher_high"
        and low_state == "higher_low"
    ):
        regime = "up_structure"

    elif (
        high_state == "lower_high"
        and low_state == "lower_low"
    ):
        regime = "down_structure"

    else:
        regime = "mixed_structure"

    return {
        "swing_high_state":
            high_state,

        "swing_low_state":
            low_state,

        "structure_regime":
            regime,
    }


# ============================================================
# SEQUENCE FEATURES
# ============================================================

def candle_sequence(index, length):

    start = index - length + 1

    if start < 0:
        return None

    return tuple(
        candle_type(i)
        for i in range(
            start,
            index + 1
        )
    )


# ============================================================
# OUTCOME
# ============================================================

def classify_outcome(
    index,
    horizon
):

    future_index = (
        index
        + horizon
    )

    if future_index >= len(closes):
        return None

    current = closes[index]

    future = closes[
        future_index
    ]

    if current <= 0:
        return None

    change = (
        future
        - current
    ) / current

    if change >= CLASSIFICATION_THRESHOLD:
        return "BUY"

    if change <= -CLASSIFICATION_THRESHOLD:
        return "SELL"

    return "NEUTRAL"


# ============================================================
# RECORDS
# ============================================================

def build_records(horizon):

    records = []

    first = WINDOW - 1

    last = (
        len(closes)
        - horizon
        - 1
    )

    for index in range(
        first,
        last + 1
    ):

        features = structure_features(
            index
        )

        if features is None:
            continue

        outcome = classify_outcome(
            index,
            horizon
        )

        if outcome is None:
            continue

        structure = market_structure_state(
            index
        )

        records.append({

            "index":
                index,

            "features":
                features,

            "structure":
                structure,

            "outcome":
                outcome,
        })

    return records


# ============================================================
# FEATURE DEFINITIONS
# ============================================================

CATEGORICAL_FEATURES = [

    "directional_regime",

    "trend_consistency",

    "volatility_regime",

    "location_state",

    "momentum_state",

    "pressure",

    "range_event",

    "latest_candle",

]

NUMERIC_FEATURES = [

    "return_5",

    "return_10",

    "return_20",

    "return_30",

    "return_60",

    "bullish_ratio",

    "bearish_ratio",

    "directional_imbalance",

    "volatility",

    "volatility_ratio",

    "location_in_range",

    "normalized_slope",

    "momentum_acceleration",

    "recent_body_ratio",

    "recent_upper_wick",

    "recent_lower_wick",

    "recent_range",
]

STRUCTURE_FEATURES = [

    "swing_high_state",

    "swing_low_state",

    "structure_regime",
]


# ============================================================
# QUANTILE EDGES
# ============================================================

def quantile_edges(
    values,
    bins=3
):

    clean = sorted(
        v
        for v in values
        if math.isfinite(v)
    )

    if len(clean) < bins:
        return []

    edges = []

    for i in range(
        1,
        bins
    ):

        position = (
            (len(clean) - 1)
            * i
            / bins
        )

        low = int(
            math.floor(position)
        )

        high = int(
            math.ceil(position)
        )

        if low == high:
            q = clean[low]

        else:

            fraction = (
                position - low
            )

            q = (
                clean[low]
                + (
                    clean[high]
                    - clean[low]
                )
                * fraction
            )

        edges.append(q)

    return edges


def prepare_edges(records):

    edges = {}

    for feature in NUMERIC_FEATURES:

        values = [
            r["features"][feature]
            for r in records
        ]

        edges[feature] = quantile_edges(
            values,
            QUANTILE_BINS
        )

    return edges


def numeric_bin(
    value,
    edges
):

    if not edges:
        return "unknown"

    if value <= edges[0]:
        return "q1"

    if len(edges) == 1:
        return "q2"

    if value <= edges[1]:
        return "q2"

    return "q3"


def get_feature_value(
    record,
    feature,
    edges
):

    if feature in NUMERIC_FEATURES:

        return (
            feature,
            numeric_bin(
                record["features"][feature],
                edges.get(
                    feature,
                    []
                )
            )
        )

    if feature in CATEGORICAL_FEATURES:

        return (
            feature,
            str(
                record["features"][feature]
            )
        )

    if feature in STRUCTURE_FEATURES:

        return (
            feature,
            str(
                record["structure"][feature]
            )
        )

    return (
        feature,
        "unknown"
    )


# ============================================================
# BASELINE
# ============================================================

def baseline_statistics(records):

    counts = Counter(
        r["outcome"]
        for r in records
    )

    total = len(records)

    if total == 0:
        return {}

    majority_label, majority_count = (
        counts.most_common(1)[0]
    )

    return {

        "BUY":
            safe_div(
                counts["BUY"],
                total
            ),

        "SELL":
            safe_div(
                counts["SELL"],
                total
            ),

        "NEUTRAL":
            safe_div(
                counts["NEUTRAL"],
                total
            ),

        "majority":
            majority_label,

        "majority_accuracy":
            safe_div(
                majority_count,
                total
            ),
    }


def print_baseline(records):

    stats = baseline_statistics(
        records
    )

    print()
    print("-" * 80)
    print("BASELINE")
    print("-" * 80)

    print(
        f"BUY      : "
        f"{stats.get('BUY', 0) * 100:.2f}%"
    )

    print(
        f"SELL     : "
        f"{stats.get('SELL', 0) * 100:.2f}%"
    )

    print(
        f"NEUTRAL  : "
        f"{stats.get('NEUTRAL', 0) * 100:.2f}%"
    )

    print(
        "Majority :",
        stats.get(
            "majority",
            "NONE"
        ),
        f"({stats.get('majority_accuracy', 0) * 100:.2f}%)"
    )


# ============================================================
# RULE DISCOVERY
# ============================================================

def discover_rules(
    calibration_records
):

    if not calibration_records:
        return []

    edges = prepare_edges(
        calibration_records
    )

    all_features = (
        CATEGORICAL_FEATURES
        + NUMERIC_FEATURES
        + STRUCTURE_FEATURES
    )

    base_counts = Counter(
        r["outcome"]
        for r in calibration_records
    )

    total = len(
        calibration_records
    )

    candidates = []

    # --------------------------------------------------------
    # ONE FEATURE
    # --------------------------------------------------------

    for feature in all_features:

        groups = defaultdict(list)

        for record in calibration_records:

            key = (
                get_feature_value(
                    record,
                    feature,
                    edges
                ),
            )

            groups[key].append(
                record["outcome"]
            )

        for key, outcomes in groups.items():

            if len(outcomes) < MIN_RULE_SAMPLES:
                continue

            counts = Counter(
                outcomes
            )

            buy = counts["BUY"]
            sell = counts["SELL"]

            if buy == sell:
                continue

            direction = (
                "BUY"
                if buy > sell
                else "SELL"
            )

            confidence = (
                max(buy, sell)
                / len(outcomes)
            )

            base_rate = (
                base_counts[direction]
                / total
            )

            lift = (
                confidence
                - base_rate
            )

            if (
                confidence
                < MIN_RULE_CONFIDENCE
            ):
                continue

            if lift < MIN_LIFT:
                continue

            candidates.append({

                "features":
                    key,

                "direction":
                    direction,

                "samples":
                    len(outcomes),

                "confidence":
                    confidence,

                "lift":
                    lift,

                "complexity":
                    1,
            })

    # --------------------------------------------------------
    # TWO FEATURE
    # --------------------------------------------------------

    for feature_a, feature_b in combinations(
        all_features,
        2
    ):

        groups = defaultdict(list)

        for record in calibration_records:

            value_a = get_feature_value(
                record,
                feature_a,
                edges
            )

            value_b = get_feature_value(
                record,
                feature_b,
                edges
            )

            key = (
                value_a,
                value_b,
            )

            groups[key].append(
                record["outcome"]
            )

        for key, outcomes in groups.items():

            if len(outcomes) < MIN_RULE_SAMPLES:
                continue

            counts = Counter(
                outcomes
            )

            buy = counts["BUY"]
            sell = counts["SELL"]

            if buy == sell:
                continue

            direction = (
                "BUY"
                if buy > sell
                else "SELL"
            )

            confidence = (
                max(buy, sell)
                / len(outcomes)
            )

            base_rate = (
                base_counts[direction]
                / total
            )

            lift = (
                confidence
                - base_rate
            )

            if (
                confidence
                < MIN_RULE_CONFIDENCE
            ):
                continue

            if lift < MIN_LIFT:
                continue

            candidates.append({

                "features":
                    key,

                "direction":
                    direction,

                "samples":
                    len(outcomes),

                "confidence":
                    confidence,

                "lift":
                    lift,

                "complexity":
                    2,
            })

    # --------------------------------------------------------
    # SORT
    # --------------------------------------------------------

    candidates.sort(
        key=lambda r: (
            r["lift"],
            r["confidence"],
            math.log1p(
                r["samples"]
            ),
            -r["complexity"],
        ),
        reverse=True
    )

    return candidates


# ============================================================
# RULE MATCHING
# ============================================================

def rule_matches(
    record,
    rule,
    edges
):

    for feature, expected in (
        rule["features"]
    ):

        actual = get_feature_value(
            record,
            feature,
            edges
        )

        if actual != expected:
            return False

    return True


# ============================================================
# RULE VALIDATION
# ============================================================

def evaluate_rules(
    calibration_records,
    validation_records,
    rules
):

    if not rules:
        return {
            "predictions": 0,
            "correct": 0,
            "accuracy": 0.0,
            "coverage": 0.0,
            "brier": None,
        }

    edges = prepare_edges(
        calibration_records
    )

    predictions = []

    for record in validation_records:

        matched = []

        for rule in rules[
            :MAX_RULES_FOR_VALIDATION
        ]:

            if rule_matches(
                record,
                rule,
                edges
            ):

                matched.append(
                    rule
                )

        if not matched:
            continue

        best = max(
            matched,
            key=lambda r: (
                r["complexity"],
                r["samples"],
                r["confidence"],
                r["lift"],
            )
        )

        predictions.append({

            "prediction":
                best["direction"],

            "actual":
                record["outcome"],

            "confidence":
                best["confidence"],

            "index":
                record["index"],
        })

    if not predictions:

        return {
            "predictions": 0,
            "correct": 0,
            "accuracy": 0.0,
            "coverage": 0.0,
            "brier": None,
        }

    correct = sum(
        1
        for p in predictions
        if p["prediction"]
        == p["actual"]
    )

    total = len(
        validation_records
    )

    accuracy = (
        correct
        / len(predictions)
        * 100
    )

    coverage = (
        len(predictions)
        / total
        * 100
        if total
        else 0.0
    )

    brier_values = []

    for p in predictions:

        confidence = clamp(
            p["confidence"],
            0.0,
            1.0
        )

        predicted = p["prediction"]
        actual = p["actual"]

        if predicted == "BUY":

            probs = {
                "BUY":
                    confidence,

                "SELL":
                    (1 - confidence) / 2,

                "NEUTRAL":
                    (1 - confidence) / 2,
            }

        else:

            probs = {
                "SELL":
                    confidence,

                "BUY":
                    (1 - confidence) / 2,

                "NEUTRAL":
                    (1 - confidence) / 2,
            }

        score = sum(
            (
                probs[label]
                - (
                    1.0
                    if label == actual
                    else 0.0
                )
            ) ** 2
            for label in [
                "BUY",
                "SELL",
                "NEUTRAL",
            ]
        )

        brier_values.append(
            score
        )

    return {

        "predictions":
            len(predictions),

        "correct":
            correct,

        "accuracy":
            accuracy,

        "coverage":
            coverage,

        "brier":
            mean(
                brier_values
            ),

        "details":
            predictions,
    }


# ============================================================
# WALK FORWARD
# ============================================================

def build_walk_forward_folds(
    records
):

    n = len(records)

    if n < (
        WALK_FORWARD_FOLDS
        + 1
    ) * MIN_VALIDATION_SAMPLES:

        return []

    fold_size = (
        n
        // (
            WALK_FORWARD_FOLDS
            + 1
        )
    )

    folds = []

    for fold in range(
        1,
        WALK_FORWARD_FOLDS + 1
    ):

        validation_start = (
            fold_size
            * fold
        )

        validation_end = (
            fold_size
            * (fold + 1)
        )

        validation_end = min(
            validation_end,
            n
        )

        calibration = records[
            :validation_start
        ]

        validation = records[
            validation_start:
            validation_end
        ]

        if len(calibration) < (
            MIN_CALIBRATION_SAMPLES
        ):
            continue

        if len(validation) < (
            MIN_VALIDATION_SAMPLES
        ):
            continue

        folds.append(
            (
                fold,
                calibration,
                validation,
            )
        )

    return folds


# ============================================================
# PRINT RULE
# ============================================================

def rule_text(rule):

    return (
        " + ".join(
            f"{feature}={value}"
            for feature, value
            in rule["features"]
        )
        + " -> "
        + rule["direction"]
    )


# ============================================================
# SIMILARITY
# ============================================================

SIMILARITY_NUMERIC = [

    "return_5",
    "return_10",
    "return_20",
    "return_30",
    "return_60",
    "bullish_ratio",
    "bearish_ratio",
    "directional_imbalance",
    "volatility_ratio",
    "location_in_range",
    "normalized_slope",
    "momentum_acceleration",
    "recent_body_ratio",
    "recent_upper_wick",
    "recent_lower_wick",
]


SIMILARITY_CATEGORICAL = [

    "directional_regime",
    "trend_consistency",
    "volatility_regime",
    "location_state",
    "momentum_state",
    "pressure",
    "range_event",
    "latest_candle",
]


def feature_distance(
    a,
    b
):

    distance = 0.0

    for key in SIMILARITY_NUMERIC:

        av = a[key]
        bv = b[key]

        scale = max(
            abs(av),
            abs(bv),
            0.0001
        )

        distance += (
            (av - bv)
            / scale
        ) ** 2

    for key in SIMILARITY_CATEGORICAL:

        if a[key] != b[key]:
            distance += 1.0

    return math.sqrt(
        distance
    )


def similarity_test(
    records
):

    if len(records) < 2:
        return

    current = records[-1]

    historical = records[:-1]

    distances = []

    for record in historical:

        distance = feature_distance(
            current["features"],
            record["features"]
        )

        distances.append(
            (
                distance,
                record["outcome"],
                record["index"],
            )
        )

    distances.sort(
        key=lambda x: x[0]
    )

    print()
    print("-" * 80)
    print("HISTORICAL SIMILARITY")
    print("-" * 80)

    for k in NEIGHBOR_K:

        neighbors = distances[
            :min(
                k,
                len(distances)
            )
        ]

        if not neighbors:
            continue

        counts = Counter(
            item[1]
            for item in neighbors
        )

        directional = (
            counts["BUY"]
            + counts["SELL"]
        )

        if directional:

            if counts["BUY"] > counts["SELL"]:

                prediction = "BUY"

                confidence = (
                    counts["BUY"]
                    / directional
                )

            elif counts["SELL"] > counts["BUY"]:

                prediction = "SELL"

                confidence = (
                    counts["SELL"]
                    / directional
                )

            else:

                prediction = "NO TRADE"
                confidence = 0.50

        else:

            prediction = "NO TRADE"
            confidence = 0.0

        print()
        print(
            f"TOP {k} HISTORICAL STATES"
        )

        print(
            "BUY:",
            counts["BUY"]
        )

        print(
            "SELL:",
            counts["SELL"]
        )

        print(
            "NEUTRAL:",
            counts["NEUTRAL"]
        )

        print(
            "Diagnostic interpretation:",
            prediction
        )

        print(
            f"Directional evidence: "
            f"{confidence * 100:.2f}%"
        )


# ============================================================
# SEQUENCE ANALYSIS
# ============================================================

def sequence_analysis(
    records,
    length
):

    groups = defaultdict(list)

    for record in records:

        sequence = candle_sequence(
            record["index"],
            length
        )

        if sequence is None:
            continue

        groups[sequence].append(
            record["outcome"]
        )

    results = []

    for sequence, outcomes in groups.items():

        if len(outcomes) < MIN_RULE_SAMPLES:
            continue

        counts = Counter(
            outcomes
        )

        directional = (
            counts["BUY"]
            + counts["SELL"]
        )

        if directional == 0:
            continue

        if counts["BUY"] > counts["SELL"]:
            direction = "BUY"

        elif counts["SELL"] > counts["BUY"]:
            direction = "SELL"

        else:
            continue

        confidence = (
            counts[direction]
            / len(outcomes)
        )

        results.append({

            "sequence":
                sequence,

            "direction":
                direction,

            "samples":
                len(outcomes),

            "confidence":
                confidence,

            "buy":
                counts["BUY"],

            "sell":
                counts["SELL"],

            "neutral":
                counts["NEUTRAL"],
        })

    results.sort(
        key=lambda x: (
            x["confidence"],
            x["samples"],
        ),
        reverse=True
    )

    return results


def print_sequence_analysis(
    records
):

    print()
    print("=" * 80)
    print("CANDLE SEQUENCE ANALYSIS")
    print("=" * 80)

    for length in SEQUENCE_LENGTHS:

        results = sequence_analysis(
            records,
            length
        )

        print()
        print(
            f"SEQUENCE LENGTH {length}"
        )

        print(
            "Candidate sequences:",
            len(results)
        )

        for result in results[
            :10
        ]:

            print(
                " ",
                " -> ".join(
                    result["sequence"]
                ),
                "=>",
                result["direction"],
                f"| n={result['samples']}",
                f"| confidence="
                f"{result['confidence'] * 100:.2f}%"
            )


# ============================================================
# REGIME ANALYSIS
# ============================================================

def regime_analysis(records):

    print()
    print("=" * 80)
    print("CONDITIONAL REGIME ANALYSIS")
    print("=" * 80)

    regimes = defaultdict(list)

    for record in records:

        key = (
            record["features"][
                "directional_regime"
            ],

            record["features"][
                "volatility_regime"
            ],

            record["features"][
                "location_state"
            ],

            record["structure"][
                "structure_regime"
            ],
        )

        regimes[key].append(
            record["outcome"]
        )

    ranked = []

    for key, outcomes in regimes.items():

        if len(outcomes) < MIN_RULE_SAMPLES:
            continue

        counts = Counter(
            outcomes
        )

        directional = (
            counts["BUY"]
            + counts["SELL"]
        )

        if directional == 0:
            continue

        if counts["BUY"] > counts["SELL"]:
            direction = "BUY"
        else:
            direction = "SELL"

        confidence = (
            counts[direction]
            / directional
        )

        ranked.append(
            (
                confidence,
                len(outcomes),
                key,
                counts,
            )
        )

    ranked.sort(
        reverse=True
    )

    for confidence, samples, key, counts in ranked[
        :20
    ]:

        print()
        print(
            "REGIME:",
            key
        )

        print(
            "Samples:",
            samples
        )

        print(
            "BUY:",
            counts["BUY"],
            "| SELL:",
            counts["SELL"],
            "| NEUTRAL:",
            counts["NEUTRAL"]
        )

        print(
            f"Directional confidence: "
            f"{confidence * 100:.2f}%"
        )


# ============================================================
# PROBABILITY CALIBRATION
# ============================================================

def calibration_report(
    predictions
):

    if not predictions:
        return

    buckets = defaultdict(list)

    for prediction in predictions:

        confidence = prediction[
            "confidence"
        ]

        bucket = min(
            int(
                confidence * 10
            ),
            9
        )

        buckets[bucket].append(
            prediction
        )

    print()
    print("=" * 80)
    print("PROBABILITY CALIBRATION")
    print("=" * 80)

    print(
        "Bucket       Samples       Confidence       Accuracy"
    )

    for bucket in range(10):

        items = buckets.get(
            bucket,
            []
        )

        if not items:
            continue

        confidence = mean(
            x["confidence"]
            for x in items
        )

        accuracy = (
            sum(
                x["prediction"]
                == x["actual"]
                for x in items
            )
            / len(items)
        )

        print(
            f"{bucket / 10:.1f}-{(bucket + 1) / 10:.1f}"
            f"       "
            f"{len(items):>5}"
            f"          "
            f"{confidence * 100:>7.2f}%"
            f"          "
            f"{accuracy * 100:>7.2f}%"
        )


# ============================================================
# PERMUTATION NULL TEST
# ============================================================

def permutation_test(
    records,
    actual_best_accuracy
):

    if len(records) < 100:
        return

    print()
    print("=" * 80)
    print("PERMUTATION NULL TEST")
    print("=" * 80)

    print(
        "Purpose:"
    )

    print(
        "Estimate how strong a result can appear "
        "when outcome labels contain no real predictive structure."
    )

    print(
        "Permutation count:",
        PERMUTATION_TESTS
    )

    outcomes = [
        r["outcome"]
        for r in records
    ]

    null_results = []

    rng = random.Random(
        RANDOM_SEED
    )

    for iteration in range(
        PERMUTATION_TESTS
    ):

        shuffled = outcomes[:]

        rng.shuffle(
            shuffled
        )

        permuted_records = []

        for i, record in enumerate(
            records
        ):

            permuted_records.append({

                "index":
                    record["index"],

                "features":
                    record["features"],

                "structure":
                    record["structure"],

                "outcome":
                    shuffled[i],
            })

        folds = build_walk_forward_folds(
            permuted_records
        )

        best_accuracy = 0.0

        for _, calibration, validation in folds:

            rules = discover_rules(
                calibration
            )

            result = evaluate_rules(
                calibration,
                validation,
                rules
            )

            if result["predictions"]:

                best_accuracy = max(
                    best_accuracy,
                    result["accuracy"]
                )

        null_results.append(
            best_accuracy
        )

    null_mean = mean(
        null_results
    )

    null_max = max(
        null_results
    )

    print(
        f"Observed best fold accuracy: "
        f"{actual_best_accuracy:.2f}%"
    )

    print(
        f"Mean null best accuracy: "
        f"{null_mean:.2f}%"
    )

    print(
        f"Maximum null best accuracy: "
        f"{null_max:.2f}%"
    )

    if actual_best_accuracy <= null_mean:

        print()
        print(
            "WARNING:"
        )

        print(
            "Observed result does not clearly "
            "beat the null-search distribution."
        )

    else:

        print()
        print(
            "Observed result exceeds the mean null result."
        )

        print(
            "This is NOT proof of an edge."
        )

        print(
            "Further independent testing is required."
        )


# ============================================================
# CURRENT MARKET STRUCTURE
# ============================================================

def print_current_structure():

    index = (
        len(closes)
        - 1
    )

    features = structure_features(
        index
    )

    structure = market_structure_state(
        index
    )

    print()
    print("=" * 80)
    print("CURRENT MARKET STRUCTURE")
    print("=" * 80)

    print(
        "Latest candle index:",
        index
    )

    print(
        "Latest close:",
        closes[index]
    )

    print()

    print(
        "Directional regime:",
        features[
            "directional_regime"
        ]
    )

    print(
        "Trend consistency:",
        features[
            "trend_consistency"
        ]
    )

    print(
        "Volatility regime:",
        features[
            "volatility_regime"
        ]
    )

    print(
        "Location:",
        features[
            "location_state"
        ]
    )

    print(
        "Momentum:",
        features[
            "momentum_state"
        ]
    )

    print(
        "Pressure:",
        features[
            "pressure"
        ]
    )

    print(
        "Range event:",
        features[
            "range_event"
        ]
    )

    print(
        "Latest candle:",
        features[
            "latest_candle"
        ]
    )

    print()

    print(
        "Swing-high state:",
        structure[
            "swing_high_state"
        ]
    )

    print(
        "Swing-low state:",
        structure[
            "swing_low_state"
        ]
    )

    print(
        "Structure regime:",
        structure[
            "structure_regime"
        ]
    )

    print()

    print(
        "Recent candle sequence:"
    )

    print(
        " -> ".join(
            features[
                "candle_sequence"
            ]
        )
    )

    print()

    for key in [
        "return_5",
        "return_10",
        "return_20",
        "return_30",
        "return_60",
        "bullish_ratio",
        "bearish_ratio",
        "directional_imbalance",
        "volatility",
        "volatility_ratio",
        "location_in_range",
        "normalized_slope",
        "momentum_acceleration",
        "recent_body_ratio",
        "recent_upper_wick",
        "recent_lower_wick",
    ]:

        print(
            f"{key:<28}: "
            f"{features[key]:.8f}"
        )


# ============================================================
# WALK-FORWARD REPORT
# ============================================================

def run_horizon(
    horizon
):

    print()
    print()
    print("=" * 80)
    print(
        f"HORIZON {horizon} CANDLES"
    )
    print("=" * 80)

    records = build_records(
        horizon
    )

    print(
        "Historical records:",
        len(records)
    )

    if len(records) < 100:

        print(
            "WARNING: insufficient records."
        )

        return None

    # --------------------------------------------------------
    # FIXED SYNTAX
    # --------------------------------------------------------
    # The original code contained an extra closing bracket
    # after the records slice.
    # --------------------------------------------------------

    baseline_size = (
        len(records)
        // (
            WALK_FORWARD_FOLDS + 1
        )
    )

    baseline_records = records[
        -baseline_size:
    ]

    print_baseline(
        baseline_records
    )

    folds = build_walk_forward_folds(
        records
    )

    print()
    print(
        "Walk-forward folds:",
        len(folds)
    )

    fold_results = []

    all_predictions = []

    best_observed_accuracy = 0.0

    for fold_number, calibration, validation in folds:

        print()
        print("-" * 80)
        print(
            f"FOLD {fold_number}"
        )
        print("-" * 80)

        print(
            "Calibration:",
            len(calibration)
        )

        print(
            "Validation:",
            len(validation)
        )

        # ----------------------------------------------------
        # DISCOVER ONLY ON CALIBRATION
        # ----------------------------------------------------

        rules = discover_rules(
            calibration
        )

        print(
            "Rules discovered:",
            len(rules)
        )

        print()

        for rule in rules[
            :TOP_RULES_TO_PRINT
        ]:

            print(
                rule_text(rule),
                f"| n={rule['samples']}",
                f"| confidence="
                f"{rule['confidence'] * 100:.2f}%",
                f"| lift="
                f"{rule['lift'] * 100:.2f}%"
            )

        # ----------------------------------------------------
        # VALIDATE
        # ----------------------------------------------------

        result = evaluate_rules(
            calibration,
            validation,
            rules
        )

        fold_results.append(
            result
        )

        if result["predictions"]:

            best_observed_accuracy = max(
                best_observed_accuracy,
                result["accuracy"]
            )

        print()
        print(
            "Validation predictions:",
            result["predictions"]
        )

        print(
            f"Accuracy: "
            f"{result['accuracy']:.2f}%"
        )

        print(
            f"Coverage: "
            f"{result['coverage']:.2f}%"
        )

        if result["brier"] is not None:

            print(
                f"Brier-like score: "
                f"{result['brier']:.6f}"
            )

        if result.get(
            "details"
        ):

            all_predictions.extend(
                result["details"]
            )

    # --------------------------------------------------------
    # AGGREGATION
    # --------------------------------------------------------

    predictions = sum(
        r["predictions"]
        for r in fold_results
    )

    correct = sum(
        r["correct"]
        for r in fold_results
    )

    accuracy = (
        correct
        / predictions
        * 100
        if predictions
        else 0.0
    )

    validation_total = sum(
        len(validation)
        for _, _, validation
        in folds
    )

    coverage = (
        predictions
        / validation_total
        * 100
        if validation_total
        else 0.0
    )

    print()
    print("=" * 80)
    print(
        "LOCKED OUT-OF-SAMPLE RESULT"
    )
    print("=" * 80)

    print(
        "Validation observations:",
        validation_total
    )

    print(
        "Predictions:",
        predictions
    )

    print(
        f"Accuracy: "
        f"{accuracy:.2f}%"
    )

    print(
        f"Coverage: "
        f"{coverage:.2f}%"
    )

    calibration_report(
        all_predictions
    )

    return {

        "records":
            records,

        "folds":
            fold_results,

        "predictions":
            all_predictions,

        "accuracy":
            accuracy,

        "coverage":
            coverage,

        "best_fold_accuracy":
            best_observed_accuracy,
    }


# ============================================================
# FINAL DIAGNOSTIC
# ============================================================

def final_diagnostic(
    results
):

    print()
    print()
    print("=" * 80)
    print("MLAI v3.4.0 FINAL DIAGNOSTIC")
    print("=" * 80)

    print()
    print(
        "The purpose of this experiment is NOT "
        "to maximize historical accuracy."
    )

    print()
    print(
        "The important question is whether "
        "market observations contain repeatable "
        "information that survives unseen chronological data."
    )

    print()

    for horizon, result in results.items():

        if result is None:
            continue

        print(
            f"Horizon {horizon}: "
            f"{result['accuracy']:.2f}% "
            f"accuracy | "
            f"{result['coverage']:.2f}% coverage"
        )

    print()
    print("-" * 80)
    print("INTERPRETATION")
    print("-" * 80)

    print(
        """
1. A high calibration result is NOT enough.

2. A high historical-neighbor result is NOT enough.

3. A rule discovered after looking at the entire dataset
   is not valid evidence.

4. Rules must be discovered using past data only.

5. Validation must remain chronologically unseen.

6. The number of rules searched matters.

7. The more combinations searched, the greater the
   probability of discovering accidental patterns.

8. A result that does not beat a simple baseline is
   not useful evidence of directional predictive power.

9. A result that does not beat an appropriate null-search
   distribution is especially suspicious.

10. Similarity is evidence retrieval, not understanding.

11. Candle labels are observations, not explanations.

12. The eventual MLAI architecture needs to combine:

       candle anatomy
       +
       candle sequences
       +
       price movement
       +
       market structure
       +
       context
       +
       regime
       +
       historical experience
       +
       probability
       +
       uncertainty

13. The final objective is generalization to unseen market
    periods, not memorization of historical combinations.
"""
    )

    print()
    print("-" * 80)
    print("CURRENT SYSTEM STATUS")
    print("-" * 80)

    print(
        "Current v3.x architecture:"
    )

    print(
        "STATISTICAL FEATURE/RULE DISCOVERY"
    )

    print()
    print(
        "It is NOT yet a complete Market Language Brain."
    )

    print(
        "It does not yet possess genuine sequence "
        "representation learning."
    )

    print(
        "It does not yet possess a validated probabilistic "
        "market-memory system."
    )

    print(
        "It does not yet demonstrate general market understanding."
    )

    print()
    print(
        "However, the current research infrastructure "
        "can be preserved as an experimental layer."
    )

    print()
    print("-" * 80)
    print("RECOMMENDED EVOLUTION")
    print("-" * 80)

    print(
        """
P0
--
Protect chronological testing.
Protect against leakage.
Separate research discovery from production.
Establish strong baselines.
Establish null/permutation testing.

P1
--
Build a richer market-state representation.

Market state should contain:

OHLC
candle anatomy
relative returns
sequences
swing structure
location
volatility
momentum
regime
support/reaction context
timeframe

P1
--
Build a historical experience index.

CURRENT STATE
      |
      v
SIMILAR HISTORICAL STATES
      |
      v
OUTCOME DISTRIBUTION
      |
      v
CONTEXT-CONDITIONAL PROBABILITY

P1
--
Add proper probability calibration.

Evaluate:

Brier score
log loss
reliability
sample size
confidence calibration

P2
--
Add sequence modelling.

Do not reduce every sequence to:

HAMMER
ENGULFING
DOJI

Instead preserve relationships between consecutive
market states.

P2
--
Add multi-timeframe context.

Higher timeframe context should constrain
lower timeframe interpretation.

P2
--
Add live market-data ingestion separately from learning.

DATA COLLECTION
       !=
LEARNING
       !=
VALIDATION
       !=
INFERENCE

P3
--
Add natural-language explanation.

Only after the underlying evidence engine is reliable.

The explanation layer should describe evidence,
not invent trader intentions.
"""
    )

    print()
    print("=" * 80)
    print(
        "MLAI v3.4.0 RESEARCH AUDIT COMPLETE"
    )
    print("=" * 80)

    print()
    print(
        "No production files were modified."
    )

    print(
        "market_data.bin was READ ONLY."
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 80)
    print(
        "MLAI v3.4.0 MARKET LANGUAGE RESEARCH AUDIT"
    )
    print("=" * 80)

    results = {}

    for horizon in HORIZONS:

        result = run_horizon(
            horizon
        )

        results[horizon] = result

        if result is not None:

            print_sequence_analysis(
                result["records"]
            )

            regime_analysis(
                result["records"]
            )

            similarity_test(
                result["records"]
            )

            permutation_test(
                result["records"],
                result[
                    "best_fold_accuracy"
                ]
            )

    print_current_structure()

    final_diagnostic(
        results
    )


if __name__ == "__main__":
    main()