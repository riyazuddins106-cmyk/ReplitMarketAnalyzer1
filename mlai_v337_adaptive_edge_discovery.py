
import os
import pickle
import math
from collections import Counter, defaultdict
from itertools import combinations


# ============================================================
# MLAI v3.3.7 ADAPTIVE EDGE DISCOVERY
# ============================================================
#
# PURPOSE
# -------
# Search for repeatable directional structures without requiring
# an exact predefined combination of market states.
#
# v3.3.7 improvements:
#
# 1. Categorical structure rules
# 2. Continuous feature quantile bins
# 3. One-feature rules
# 4. Two-feature rules
# 5. Calibration-only discovery
# 6. Strict chronological walk-forward validation
# 7. Cross-fold stability analysis
# 8. Majority-baseline comparison
# 9. Rule confidence / lift reporting
#
# PROTECTION
# ----------
# market_data.bin is READ ONLY
# mlai_v31.py is NOT MODIFIED
# learning memory is NOT MODIFIED
# production thresholds are NOT MODIFIED
#
# THIS SCRIPT DOES NOT CREATE TRADING SIGNALS.
# THIS SCRIPT DOES NOT MODIFY PRODUCTION MLAI.
#
# ============================================================


MARKET_FILE = "market_data.bin"

WINDOW = 60

HORIZONS = [4, 8, 16]

CLASSIFICATION_THRESHOLD = 0.0015

WALK_FORWARD_FOLDS = 4

MIN_CALIBRATION_SAMPLES = 20

MIN_VALIDATION_SAMPLES = 20

MIN_CONFIDENCE = 0.45

MIN_DIRECTIONAL_LIFT = 0.05

MIN_STABILITY_FOLDS = 2

TOP_RULES_TO_PRINT = 20

QUANTILE_BINS = 3


# ============================================================
# LOAD DATA
# ============================================================

print("=" * 70)
print("MLAI v3.3.7 ADAPTIVE EDGE DISCOVERY")
print("=" * 70)

print("""
Purpose:
Search for repeatable directional information using adaptive
market-structure features while preserving strict chronological
walk-forward validation.

Rules are discovered using calibration data only.
Validation data is never used to discover rules.
""")

print("=" * 70)
print("PROTECTION CHECK")
print("=" * 70)

print("market_data.bin: READ ONLY")
print("mlai_v31.py: NOT MODIFIED")
print("learning memory: NOT MODIFIED")
print("production thresholds: NOT MODIFIED")

if not os.path.exists(MARKET_FILE):
    raise FileNotFoundError(f"{MARKET_FILE} not found.")

with open(MARKET_FILE, "rb") as f:
    market_data = pickle.load(f)

print()
print("Data type:", type(market_data).__name__)


# ============================================================
# EXTRACT CANDLES
# ============================================================

def extract_candles(data):
    if isinstance(data, dict):

        for key in ["candles", "data", "market_data", "ohlcv"]:
            if key in data and isinstance(data[key], list):
                return data[key]

        if all(k in data for k in ["open", "high", "low", "close"]):
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

    raise ValueError("Unsupported market_data.bin structure.")


candles = extract_candles(market_data)

print("Total candles:", len(candles))
print("PASS: market_data.bin loaded.")
print("PASS: Close prices extracted.")
print("PASS: market_data.bin will NOT be modified.")
print("PASS: Production MLAI will NOT be modified.")


# ============================================================
# SAFE CANDLE ACCESS
# ============================================================

def get_value(candle, key, default=0.0):
    if isinstance(candle, dict):
        value = candle.get(key, default)

        try:
            return float(value)
        except Exception:
            return default

    return default


opens = [get_value(c, "open") for c in candles]
highs = [get_value(c, "high") for c in candles]
lows = [get_value(c, "low") for c in candles]
closes = [get_value(c, "close") for c in candles]


# ============================================================
# BASIC STATISTICS
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


def quantile_edges(values, bins=3):
    """
    Quantile edges calculated only from calibration data.
    """
    values = sorted(v for v in values if math.isfinite(v))

    if len(values) < bins:
        return []

    edges = []

    for i in range(1, bins):
        pos = (len(values) - 1) * i / bins

        low = int(math.floor(pos))
        high = int(math.ceil(pos))

        if low == high:
            q = values[low]
        else:
            fraction = pos - low
            q = (
                values[low]
                + (values[high] - values[low]) * fraction
            )

        edges.append(q)

    return edges


def quantile_label(value, edges):
    if not edges:
        return "unknown"

    if value <= edges[0]:
        return "q1"

    if len(edges) == 1:
        return "q2"

    if value <= edges[1]:
        return "q2"

    return "q3"


# ============================================================
# STRUCTURE CALCULATION
# ============================================================

def structure_features(index):
    start = index - WINDOW + 1

    if start < 0:
        return None

    c60 = closes[start:index + 1]

    if len(c60) < WINDOW:
        return None

    current = closes[index]

    if current <= 0:
        return None

    def ret(n):
        if len(c60) <= n:
            return 0.0

        previous = closes[index - n]

        if previous == 0:
            return 0.0

        return (current - previous) / previous

    returns = []

    for j in range(start + 1, index + 1):

        previous = closes[j - 1]

        if previous != 0:
            returns.append(
                (closes[j] - previous) / previous
            )

    volatility = std(returns)

    recent_returns = returns[-20:] if len(returns) >= 20 else returns

    recent_volatility = std(recent_returns)

    volatility_ratio = safe_div(
        volatility,
        recent_volatility
    ) if recent_volatility != 0 else 1.0

    bullish = 0
    bearish = 0

    body_sizes = []
    upper_wicks = []
    lower_wicks = []

    for j in range(start, index + 1):

        o = opens[j]
        h = highs[j]
        l = lows[j]
        c = closes[j]

        if c > o:
            bullish += 1
        elif c < o:
            bearish += 1

        candle_range = max(h - l, 1e-12)

        body_sizes.append(abs(c - o) / candle_range)

        upper_wicks.append(
            max(0.0, h - max(o, c)) / candle_range
        )

        lower_wicks.append(
            max(0.0, min(o, c) - l) / candle_range
        )

    total = max(len(c60), 1)

    bullish_ratio = bullish / total
    bearish_ratio = bearish / total

    directional_imbalance = (
        bullish_ratio - bearish_ratio
    )

    high60 = max(highs[start:index + 1])
    low60 = min(lows[start:index + 1])

    range60 = max(high60 - low60, 1e-12)

    location = (
        current - low60
    ) / range60

    momentum_5 = ret(5)
    momentum_10 = ret(10)
    momentum_20 = ret(20)

    momentum_acceleration = (
        momentum_5 - momentum_10
    )

    slope = ret(60)

    recent_body_ratio = mean(body_sizes[-10:])

    recent_upper_wick = mean(upper_wicks[-10:])

    recent_lower_wick = mean(lower_wicks[-10:])

    # --------------------------------------------------------
    # CATEGORICAL STATES
    # --------------------------------------------------------

    if slope > 0.002:
        directional_regime = "bullish"
    elif slope < -0.002:
        directional_regime = "bearish"
    else:
        directional_regime = "neutral"

    if abs(slope) > 0.005:
        trend_consistency = "strong"
    elif abs(slope) > 0.002:
        trend_consistency = "moderate"
    else:
        trend_consistency = "weak"

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

    if momentum_5 > 0 and momentum_10 > 0:
        momentum_state = "bullish"
    elif momentum_5 < 0 and momentum_10 < 0:
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

    return {
        "return_5": momentum_5,
        "return_10": momentum_10,
        "return_20": momentum_20,
        "return_30": ret(30),
        "return_60": ret(60),

        "bullish_ratio": bullish_ratio,
        "bearish_ratio": bearish_ratio,
        "directional_imbalance": directional_imbalance,

        "volatility": volatility,
        "volatility_ratio": volatility_ratio,

        "location_in_range": location,

        "normalized_slope": slope,

        "momentum_5": momentum_5,
        "momentum_10": momentum_10,
        "momentum_20": momentum_20,

        "momentum_acceleration": momentum_acceleration,

        "recent_body_ratio": recent_body_ratio,
        "recent_upper_wick": recent_upper_wick,
        "recent_lower_wick": recent_lower_wick,

        "directional_regime": directional_regime,
        "trend_consistency": trend_consistency,
        "volatility_regime": volatility_regime,
        "location_state": location_state,
        "momentum_state": momentum_state,
        "pressure": pressure,
        "range_event": range_event,
    }


# ============================================================
# BUILD HISTORICAL RECORDS
# ============================================================

def classify_outcome(index, horizon):

    future_index = index + horizon

    if future_index >= len(closes):
        return None

    current = closes[index]
    future = closes[future_index]

    if current == 0:
        return None

    change = (
        future - current
    ) / current

    if change >= CLASSIFICATION_THRESHOLD:
        return "BUY"

    if change <= -CLASSIFICATION_THRESHOLD:
        return "SELL"

    return "NEUTRAL"


def build_records(horizon):

    records = []

    first = WINDOW - 1

    last = len(closes) - horizon - 1

    for index in range(first, last + 1):

        features = structure_features(index)

        if features is None:
            continue

        outcome = classify_outcome(index, horizon)

        if outcome is None:
            continue

        records.append({
            "index": index,
            "features": features,
            "outcome": outcome,
        })

    return records


# ============================================================
# FEATURE TYPES
# ============================================================

CATEGORICAL_FEATURES = [
    "directional_regime",
    "trend_consistency",
    "volatility_regime",
    "location_state",
    "momentum_state",
    "pressure",
    "range_event",
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
]


# ============================================================
# ADAPTIVE FEATURE REPRESENTATION
# ============================================================

def prepare_feature_values(calibration_records):

    edges = {}

    for feature in NUMERIC_FEATURES:

        values = [
            r["features"][feature]
            for r in calibration_records
            if math.isfinite(r["features"][feature])
        ]

        edges[feature] = quantile_edges(
            values,
            QUANTILE_BINS
        )

    return edges


def get_rule_value(record, feature, edges):

    value = record["features"][feature]

    if feature in NUMERIC_FEATURES:

        return (
            feature,
            quantile_label(
                value,
                edges.get(feature, [])
            )
        )

    return (
        feature,
        str(value)
    )


# ============================================================
# RULE DISCOVERY
# ============================================================

def discover_rules(calibration_records):

    edges = prepare_feature_values(
        calibration_records
    )

    candidates = []

    feature_pool = (
        CATEGORICAL_FEATURES
        + NUMERIC_FEATURES
    )

    # --------------------------------------------------------
    # 1 FEATURE RULES
    # --------------------------------------------------------

    for feature in feature_pool:

        groups = defaultdict(list)

        for record in calibration_records:

            key = (
                get_rule_value(
                    record,
                    feature,
                    edges
                ),
            )

            groups[key].append(
                record["outcome"]
            )

        for key, outcomes in groups.items():

            if len(outcomes) < MIN_CALIBRATION_SAMPLES:
                continue

            counts = Counter(outcomes)

            directional_count = (
                counts["BUY"]
                + counts["SELL"]
            )

            if directional_count == 0:
                continue

            direction = (
                "BUY"
                if counts["BUY"] > counts["SELL"]
                else "SELL"
            )

            confidence = (
                counts[direction]
                / len(outcomes)
            )

            directional_rate = (
                directional_count
                / len(outcomes)
            )

            # Compare against overall calibration
            # directional frequency.
            calibration_counts = Counter(
                r["outcome"]
                for r in calibration_records
            )

            base_direction_rate = (
                calibration_counts[direction]
                / len(calibration_records)
            )

            lift = (
                confidence
                - base_direction_rate
            )

            if confidence < MIN_CONFIDENCE:
                continue

            if lift < MIN_DIRECTIONAL_LIFT:
                continue

            candidates.append({
                "features": key,
                "direction": direction,
                "samples": len(outcomes),
                "confidence": confidence,
                "directional_rate": directional_rate,
                "lift": lift,
            })

    # --------------------------------------------------------
    # 2 FEATURE RULES
    # --------------------------------------------------------

    for feature_a, feature_b in combinations(
        feature_pool,
        2
    ):

        groups = defaultdict(list)

        for record in calibration_records:

            value_a = get_rule_value(
                record,
                feature_a,
                edges
            )

            value_b = get_rule_value(
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

            if len(outcomes) < MIN_CALIBRATION_SAMPLES:
                continue

            counts = Counter(outcomes)

            directional_count = (
                counts["BUY"]
                + counts["SELL"]
            )

            if directional_count == 0:
                continue

            direction = (
                "BUY"
                if counts["BUY"] > counts["SELL"]
                else "SELL"
            )

            confidence = (
                counts[direction]
                / len(outcomes)
            )

            directional_rate = (
                directional_count
                / len(outcomes)
            )

            calibration_counts = Counter(
                r["outcome"]
                for r in calibration_records
            )

            base_direction_rate = (
                calibration_counts[direction]
                / len(calibration_records)
            )

            lift = (
                confidence
                - base_direction_rate
            )

            if confidence < MIN_CONFIDENCE:
                continue

            if lift < MIN_DIRECTIONAL_LIFT:
                continue

            candidates.append({
                "features": key,
                "direction": direction,
                "samples": len(outcomes),
                "confidence": confidence,
                "directional_rate": directional_rate,
                "lift": lift,
            })

    # --------------------------------------------------------
    # SORT
    # --------------------------------------------------------

    candidates.sort(
        key=lambda x: (
            x["lift"],
            x["confidence"],
            math.log1p(x["samples"])
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

    for feature_name, expected_value in rule["features"]:

        actual = get_rule_value(
            record,
            feature_name,
            edges
        )

        if actual != expected_value:
            return False

    return True


# ============================================================
# VALIDATION
# ============================================================

def evaluate_rules(
    validation_records,
    rules,
    calibration_records
):

    if not rules:
        return {
            "predictions": 0,
            "correct": 0,
            "accuracy": 0.0,
            "coverage": 0.0,
            "buy_predictions": 0,
            "sell_predictions": 0,
            "buy_correct": 0,
            "sell_correct": 0,
            "buy_precision": 0.0,
            "sell_precision": 0.0,
        }

    edges = prepare_feature_values(
        calibration_records
    )

    predictions = []

    for record in validation_records:

        matched_rules = []

        for rule in rules:

            if rule_matches(
                record,
                rule,
                edges
            ):
                matched_rules.append(rule)

        if not matched_rules:
            continue

        # Strongest matching rule.
        best_rule = max(
            matched_rules,
            key=lambda r: (
                len(r["features"]),
                r["confidence"],
                r["lift"],
                r["samples"]
            )
        )

        predictions.append(
            (
                best_rule["direction"],
                record["outcome"]
            )
        )

    if not predictions:
        return {
            "predictions": 0,
            "correct": 0,
            "accuracy": 0.0,
            "coverage": 0.0,
            "buy_predictions": 0,
            "sell_predictions": 0,
            "buy_correct": 0,
            "sell_correct": 0,
            "buy_precision": 0.0,
            "sell_precision": 0.0,
        }

    correct = sum(
        1
        for predicted, actual in predictions
        if predicted == actual
    )

    buy_predictions = sum(
        1
        for predicted, _ in predictions
        if predicted == "BUY"
    )

    sell_predictions = sum(
        1
        for predicted, _ in predictions
        if predicted == "SELL"
    )

    buy_correct = sum(
        1
        for predicted, actual in predictions
        if predicted == "BUY"
        and actual == "BUY"
    )

    sell_correct = sum(
        1
        for predicted, actual in predictions
        if predicted == "SELL"
        and actual == "SELL"
    )

    total_validation = len(validation_records)

    return {
        "predictions": len(predictions),

        "correct": correct,

        "accuracy": (
            correct / len(predictions)
        ) * 100,

        "coverage": (
            len(predictions)
            / total_validation
        ) * 100
        if total_validation else 0.0,

        "buy_predictions": buy_predictions,

        "sell_predictions": sell_predictions,

        "buy_correct": buy_correct,

        "sell_correct": sell_correct,

        "buy_precision": (
            buy_correct
            / buy_predictions
        ) * 100
        if buy_predictions else 0.0,

        "sell_precision": (
            sell_correct
            / sell_predictions
        ) * 100
        if sell_predictions else 0.0,
    }


# ============================================================
# BASELINE
# ============================================================

def print_baseline(records):

    counts = Counter(
        r["outcome"]
        for r in records
    )

    total = len(records)

    print("-" * 70)
    print("VALIDATION BASELINE")
    print("-" * 70)

    for label in ["BUY", "SELL", "NEUTRAL"]:

        frequency = (
            counts[label]
            / total
            * 100
        ) if total else 0.0

        print(
            f"{label:<10}: "
            f"{frequency:6.2f}%"
        )

    majority = (
        max(counts.values()) / total * 100
        if total
        else 0.0
    )

    majority_label = (
        counts.most_common(1)[0][0]
        if counts
        else "NONE"
    )

    print(
        f"Majority baseline: "
        f"{majority_label} "
        f"({majority:.2f}%)"
    )


# ============================================================
# RULE FORMAT
# ============================================================

def rule_text(rule):

    parts = []

    for feature, value in rule["features"]:

        parts.append(
            f"{feature}={value}"
        )

    return (
        " + ".join(parts)
        + " -> "
        + rule["direction"]
    )


# ============================================================
# WALK FORWARD
# ============================================================

def walk_forward(records):

    n = len(records)

    fold_size = n // (
        WALK_FORWARD_FOLDS + 1
    )

    all_results = []

    rule_fold_counts = defaultdict(int)

    stable_rule_candidates = defaultdict(list)

    for fold in range(
        WALK_FORWARD_FOLDS,
        0,
        -1
    ):

        validation_start = (
            fold_size * fold
        )

        validation_end = min(
            validation_start + fold_size,
            n
        )

        calibration_records = records[
            :validation_start
        ]

        validation_records = records[
            validation_start:validation_end
        ]

        if (
            len(calibration_records)
            < MIN_CALIBRATION_SAMPLES
        ):
            continue

        if (
            len(validation_records)
            < MIN_VALIDATION_SAMPLES
        ):
            continue

        print()
        print("-" * 70)
        print(f"FOLD {fold}")
        print("-" * 70)

        print(
            "Calibration records:",
            len(calibration_records)
        )

        print(
            "Validation records: ",
            len(validation_records)
        )

        print(
            "Rule discovery: CALIBRATION ONLY"
        )

        rules = discover_rules(
            calibration_records
        )

        print()
        print(
            "Adaptive rules discovered:",
            len(rules)
        )

        if rules:

            print()
            print("TOP CALIBRATION RULES")

            for rule in rules[
                :TOP_RULES_TO_PRINT
            ]:

                print(
                    f"{rule_text(rule)}"
                    f" | samples={rule['samples']}"
                    f" | confidence="
                    f"{rule['confidence'] * 100:.2f}%"
                    f" | lift="
                    f"{rule['lift'] * 100:.2f}%"
                )

                rule_key = (
                    tuple(rule["features"]),
                    rule["direction"]
                )

                rule_fold_counts[
                    rule_key
                ] += 1

                stable_rule_candidates[
                    rule_key
                ].append(rule)

        result = evaluate_rules(
            validation_records,
            rules,
            calibration_records
        )

        all_results.append(result)

        print()
        print(
            "Validation matched records:",
            result["predictions"]
        )

        print(
            f"Directional accuracy: "
            f"{result['accuracy']:.2f}%"
        )

        print(
            f"Coverage: "
            f"{result['coverage']:.2f}%"
        )

        print(
            f"BUY precision: "
            f"{result['buy_precision']:.2f}%"
        )

        print(
            f"SELL precision: "
            f"{result['sell_precision']:.2f}%"
        )

    return (
        all_results,
        rule_fold_counts,
        stable_rule_candidates
    )


# ============================================================
# AGGREGATE RESULTS
# ============================================================

def aggregate_results(results):

    if not results:
        return None

    predictions = sum(
        r["predictions"]
        for r in results
    )

    correct = sum(
        r["correct"]
        for r in results
    )

    buy_predictions = sum(
        r["buy_predictions"]
        for r in results
    )

    sell_predictions = sum(
        r["sell_predictions"]
        for r in results
    )

    buy_correct = sum(
        r["buy_correct"]
        for r in results
    )

    sell_correct = sum(
        r["sell_correct"]
        for r in results
    )

    return {
        "predictions": predictions,

        "correct": correct,

        "accuracy": (
            correct / predictions * 100
        ) if predictions else 0.0,

        "buy_predictions": buy_predictions,

        "sell_predictions": sell_predictions,

        "buy_precision": (
            buy_correct
            / buy_predictions
            * 100
        ) if buy_predictions else 0.0,

        "sell_precision": (
            sell_correct
            / sell_predictions
            * 100
        ) if sell_predictions else 0.0,
    }


# ============================================================
# HISTORICAL SIMILARITY
# ============================================================

def feature_distance(a, b):

    numeric = [
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

    distance = 0.0

    for key in numeric:

        av = a[key]
        bv = b[key]

        scale = max(
            abs(av),
            abs(bv),
            0.0001
        )

        distance += (
            (av - bv) / scale
        ) ** 2

    categorical = [
        "directional_regime",
        "trend_consistency",
        "volatility_regime",
        "location_state",
        "momentum_state",
        "pressure",
        "range_event",
    ]

    for key in categorical:

        if a[key] != b[key]:
            distance += 1.0

    return math.sqrt(distance)


def similarity_test(records):

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
                record["outcome"]
            )
        )

    distances.sort(
        key=lambda x: x[0]
    )

    print()
    print("-" * 70)
    print("HISTORICAL SIMILARITY TEST")
    print("-" * 70)

    for k in [10, 20, 40]:

        neighbors = distances[
            :min(k, len(distances))
        ]

        if not neighbors:
            continue

        counts = Counter(
            outcome
            for _, outcome in neighbors
        )

        directional = (
            counts["BUY"]
            + counts["SELL"]
        )

        if directional == 0:
            prediction = "NO TRADE"
            confidence = 0.0
        else:

            if counts["BUY"] > counts["SELL"]:
                prediction = "BUY"
                confidence = (
                    counts["BUY"]
                    / directional
                )
            else:
                prediction = "SELL"
                confidence = (
                    counts["SELL"]
                    / directional
                )

        print()
        print(f"TOP {k} NEIGHBORS")
        print(
            "Bullish:",
            counts["BUY"]
        )
        print(
            "Neutral:",
            counts["NEUTRAL"]
        )
        print(
            "Bearish:",
            counts["SELL"]
        )
        print(
            "Diagnostic prediction:",
            prediction
        )
        print(
            f"Directional confidence: "
            f"{confidence * 100:.2f}%"
        )


# ============================================================
# CURRENT MARKET STRUCTURE
# ============================================================

def print_current_structure():

    index = len(closes) - 1

    features = structure_features(index)

    if features is None:
        return

    print()
    print("=" * 70)
    print("CURRENT 60-CANDLE MARKET STRUCTURE")
    print("=" * 70)

    print(
        "Latest index:",
        index
    )

    print(
        "Latest price:",
        closes[index]
    )

    print()
    print(
        "Directional regime:",
        features["directional_regime"]
    )

    print(
        "Volatility regime:",
        features["volatility_regime"]
    )

    print(
        "Trend consistency:",
        features["trend_consistency"]
    )

    print(
        "Location state:",
        features["location_state"]
    )

    print(
        "Momentum state:",
        features["momentum_state"]
    )

    print(
        "Candle pressure:",
        features["pressure"]
    )

    print(
        "Range event:",
        features["range_event"]
    )

    print()
    print("NUMERIC STRUCTURE FEATURES")

    numeric_to_show = [
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
    ]

    for key in numeric_to_show:

        print(
            f"{key:<24}: "
            f"{features[key]:.6f}"
        )


# ============================================================
# MAIN
# ============================================================

all_horizon_results = {}

for horizon in HORIZONS:

    print()
    print("=" * 70)
    print(f"HORIZON: {horizon} CANDLES")
    print("=" * 70)

    records = build_records(
        horizon
    )

    print(
        "Historical records:",
        len(records)
    )

    if len(records) < 100:
        print(
            "Not enough historical records."
        )
        continue

    # --------------------------------------------------------
    # BASELINE
    # --------------------------------------------------------

    validation_size = len(records) // (
        WALK_FORWARD_FOLDS + 1
    )

    baseline_validation = records[
        -validation_size:
    ]

    print_baseline(
        baseline_validation
    )

    # --------------------------------------------------------
    # WALK FORWARD
    # --------------------------------------------------------

    (
        fold_results,
        rule_fold_counts,
        stable_rule_candidates
    ) = walk_forward(
        records
    )

    # --------------------------------------------------------
    # AGGREGATE
    # --------------------------------------------------------

    aggregate = aggregate_results(
        fold_results
    )

    print()
    print("=" * 70)
    print(
        "AGGREGATED LOCKED OUT-OF-SAMPLE RESULT"
    )
    print("=" * 70)

    if aggregate is None:

        print(
            "No validation results."
        )

    elif aggregate["predictions"] == 0:

        print(
            "No locked adaptive rules "
            "generated predictions."
        )

    else:

        print(
            "Validation predictions:",
            aggregate["predictions"]
        )

        print(
            f"Directional accuracy: "
            f"{aggregate['accuracy']:.2f}%"
        )

        print(
            "BUY predictions:",
            aggregate["buy_predictions"]
        )

        print(
            "SELL predictions:",
            aggregate["sell_predictions"]
        )

        print(
            f"BUY precision: "
            f"{aggregate['buy_precision']:.2f}%"
        )

        print(
            f"SELL precision: "
            f"{aggregate['sell_precision']:.2f}%"
        )

    # --------------------------------------------------------
    # STABILITY
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("CROSS-FOLD STABILITY ANALYSIS")
    print("=" * 70)

    stable_rules = []

    for key, fold_count in rule_fold_counts.items():

        if fold_count >= MIN_STABILITY_FOLDS:

            stable_rules.append(
                (
                    fold_count,
                    key
                )
            )

    stable_rules.sort(
        reverse=True
    )

    print(
        "Stable rules:",
        len(stable_rules)
    )

    if stable_rules:

        for fold_count, key in stable_rules[
            :TOP_RULES_TO_PRINT
        ]:

            features, direction = key

            print()
            print(
                "STABLE:",
                " + ".join(
                    f"{a}={b}"
                    for a, b in features
                ),
                "->",
                direction,
                f"| folds={fold_count}"
            )

    all_horizon_results[
        horizon
    ] = {
        "records": records,
        "aggregate": aggregate,
        "stable_rules": stable_rules,
    }

    # --------------------------------------------------------
    # HISTORICAL SIMILARITY
    # --------------------------------------------------------

    similarity_test(
        records
    )


# ============================================================
# CURRENT STRUCTURE
# ============================================================

print_current_structure()


# ============================================================
# FINAL VERDICT
# ============================================================

print()
print("=" * 70)
print("MLAI v3.3.7 FINAL VERDICT")
print("=" * 70)

print("""
This experiment is diagnostic only.

No production model was changed.
No learning memory was changed.
market_data.bin was READ ONLY.
mlai_v31.py was NOT modified.

v3.3.7 searches adaptive one-feature and two-feature
market structures instead of requiring one exact predefined
multidimensional structure.

A candidate rule is considered interesting only when:

  1. It has sufficient calibration samples.
  2. Calibration confidence exceeds the minimum.
  3. Calibration directional lift is positive.
  4. The rule is locked before validation.
  5. Validation is chronological and unseen.
  6. The rule survives across multiple folds.
  7. Validation performance is evaluated independently.
  8. No validation information is used to discover the rule.

IMPORTANT:

A high historical similarity percentage is NOT proof of an edge.

A high calibration percentage is NOT proof of an edge.

A rule must survive unseen chronological validation.

No rule from this experiment is promoted to production.

MLAI v3.3.7 COMPLETE
""")
