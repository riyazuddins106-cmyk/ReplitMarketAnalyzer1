import pickle
import math
import random
from collections import Counter

# ============================================================
# MLAI v3.3 FEATURE COMBINATION MODEL TEST
#
# PURPOSE:
# Test whether combinations of candle-derived features contain
# useful directional information beyond simple baselines.
#
# PROTECTION:
# - market_data.bin is READ ONLY
# - mlai_v31.py is NOT modified
# - learning memory is NOT modified
# - No production threshold is changed
#
# METHOD:
# - Walk-forward chronological validation
# - No random train/test mixing
# - Horizons: 4, 8, 16 candles
# - Threshold: +/- 0.15%
# ============================================================


DATA_FILE = "market_data.bin"

CURRENT_WINDOW = 60
HORIZONS = [4, 8, 16]

THRESHOLD = 0.15

# Number of historical records reserved for each test block.
TEST_BLOCK_SIZE = 120

# Number of training records used immediately before each test block.
TRAIN_SIZE = 600


# ============================================================
# BASIC HELPERS
# ============================================================

def pct_change(old, new):
    if old == 0:
        return 0.0

    return (new - old) / abs(old) * 100.0


def safe_mean(values):
    if not values:
        return 0.0

    return sum(values) / len(values)


def clamp(value, low=-10.0, high=10.0):
    return max(low, min(high, value))


# ============================================================
# OUTCOME CLASSIFICATION
# ============================================================

def classify_return(return_value):
    if return_value >= THRESHOLD:
        return "bullish"

    if return_value <= -THRESHOLD:
        return "bearish"

    return "neutral"


# ============================================================
# FEATURE EXTRACTION
# ============================================================

def extract_features(candles, end_index):
    """
    Uses only candles BEFORE end_index.

    This is critical.

    No future candle is allowed to enter the feature vector.
    """

    start = end_index - CURRENT_WINDOW

    if start < 0:
        return None

    window = candles[start:end_index]

    if len(window) != CURRENT_WINDOW:
        return None

    closes = [float(c["close"]) for c in window]
    highs = [float(c["high"]) for c in window]
    lows = [float(c["low"]) for c in window]
    opens = [float(c["open"]) for c in window]

    latest_close = closes[-1]

    if latest_close == 0:
        return None

    # --------------------------------------------------------
    # RETURNS
    # --------------------------------------------------------

    def ret(n):
        if len(closes) <= n:
            return 0.0

        return pct_change(closes[-1 - n], closes[-1])

    return_5 = ret(5)
    return_10 = ret(10)
    return_15 = ret(15)
    return_30 = ret(30)
    return_60 = ret(59)

    # --------------------------------------------------------
    # BULLISH / BEARISH RATIOS
    # --------------------------------------------------------

    bullish = sum(
        1 for c in window
        if c.get("direction") == "bullish"
    )

    bearish = sum(
        1 for c in window
        if c.get("direction") == "bearish"
    )

    neutral = sum(
        1 for c in window
        if c.get("direction") == "neutral"
    )

    bullish_ratio = bullish / len(window)
    bearish_ratio = bearish / len(window)

    directional_imbalance = (
        (bullish - bearish) / len(window)
    )

    # --------------------------------------------------------
    # STRONG BODY
    # --------------------------------------------------------

    strong_body = sum(
        1 for c in window
        if c.get("candle_type") == "strong_body"
    )

    strong_body_ratio = strong_body / len(window)

    # --------------------------------------------------------
    # BODY RATIO
    # --------------------------------------------------------

    body_ratios = [
        float(c.get("body_to_range", 0.0))
        for c in window
        if float(c.get("range", 0.0)) > 0
    ]

    average_body_ratio = safe_mean(body_ratios)

    # --------------------------------------------------------
    # REJECTION
    # --------------------------------------------------------

    upper = sum(
        1 for c in window
        if c.get("candle_type") == "upper_rejection"
    )

    lower = sum(
        1 for c in window
        if c.get("candle_type") == "lower_rejection"
    )

    rejection_imbalance = (
        (lower - upper) / len(window)
    )

    # --------------------------------------------------------
    # VOLATILITY
    # --------------------------------------------------------

    ranges = []

    for c in window:

        close = float(c["close"])

        if close == 0:
            continue

        candle_range = (
            float(c["high"])
            - float(c["low"])
        ) / abs(close) * 100.0

        ranges.append(candle_range)

    volatility = safe_mean(ranges)

    # --------------------------------------------------------
    # VOLATILITY RATIO
    # --------------------------------------------------------

    older = ranges[:-10]
    recent = ranges[-10:]

    older_vol = safe_mean(older)
    recent_vol = safe_mean(recent)

    if older_vol == 0:
        volatility_ratio = 0.0
    else:
        volatility_ratio = (
            recent_vol / older_vol
        ) - 1.0

    # --------------------------------------------------------
    # RANGE POSITION
    # --------------------------------------------------------

    highest = max(highs)
    lowest = min(lows)

    total_range = highest - lowest

    if total_range == 0:
        location_in_range = 0.5
    else:
        location_in_range = (
            latest_close - lowest
        ) / total_range

    distance_from_high = (
        latest_close - highest
    ) / latest_close * 100.0

    distance_from_low = (
        latest_close - lowest
    ) / latest_close * 100.0

    # --------------------------------------------------------
    # NORMALIZED SLOPE
    # --------------------------------------------------------

    first_close = closes[0]

    if first_close == 0:
        normalized_slope = 0.0
    else:
        normalized_slope = (
            (latest_close - first_close)
            / first_close
            * 100.0
        )

    # --------------------------------------------------------
    # MOMENTUM ACCELERATION
    # --------------------------------------------------------

    if len(closes) >= 12:

        previous = pct_change(
            closes[-12],
            closes[-6]
        )

        recent = pct_change(
            closes[-6],
            closes[-1]
        )

        momentum_acceleration = (
            recent - previous
        )

    else:
        momentum_acceleration = 0.0

    # --------------------------------------------------------
    # RETURN FEATURE VECTOR
    # --------------------------------------------------------

    return {
        "return_5": return_5,
        "return_10": return_10,
        "return_15": return_15,
        "return_30": return_30,
        "return_60": return_60,

        "bullish_ratio": bullish_ratio,
        "bearish_ratio": bearish_ratio,
        "directional_imbalance": directional_imbalance,

        "strong_body_ratio": strong_body_ratio,
        "average_body_ratio": average_body_ratio,

        "rejection_imbalance": rejection_imbalance,

        "volatility": volatility,
        "volatility_ratio": volatility_ratio,

        "location_in_range": location_in_range,
        "distance_from_high": distance_from_high,
        "distance_from_low": distance_from_low,

        "normalized_slope": normalized_slope,
        "momentum_acceleration": momentum_acceleration,

        "neutral_ratio": neutral / len(window),
    }


# ============================================================
# RECORD BUILDING
# ============================================================

def build_records(candles, horizon):

    records = []

    # end_index is the candle immediately AFTER the context.
    #
    # Future outcome begins at end_index and ends at
    # end_index + horizon - 1.

    first_index = CURRENT_WINDOW
    last_index = len(candles) - horizon

    for end_index in range(
        first_index,
        last_index + 1
    ):

        features = extract_features(
            candles,
            end_index
        )

        if features is None:
            continue

        current_close = float(
            candles[end_index - 1]["close"]
        )

        future_close = float(
            candles[end_index + horizon - 1]["close"]
        )

        future_return = pct_change(
            current_close,
            future_close
        )

        outcome = classify_return(
            future_return
        )

        records.append({
            "index": end_index,
            "features": features,
            "future_return": future_return,
            "outcome": outcome,
        })

    return records


# ============================================================
# FEATURE STANDARDIZATION
# ============================================================

def calculate_stats(records, feature_names):

    stats = {}

    for name in feature_names:

        values = [
            r["features"][name]
            for r in records
        ]

        mean = safe_mean(values)

        variance = safe_mean([
            (x - mean) ** 2
            for x in values
        ])

        std = math.sqrt(variance)

        if std == 0:
            std = 1.0

        stats[name] = (
            mean,
            std
        )

    return stats


def standardize(features, stats):

    result = {}

    for name, value in features.items():

        if name not in stats:
            continue

        mean, std = stats[name]

        result[name] = (
            value - mean
        ) / std

    return result


# ============================================================
# SIMPLE LEARNED MODEL
# ============================================================

FEATURE_NAMES = [
    "return_5",
    "return_10",
    "return_15",
    "return_30",
    "return_60",

    "bullish_ratio",
    "bearish_ratio",
    "directional_imbalance",

    "strong_body_ratio",
    "average_body_ratio",

    "rejection_imbalance",

    "volatility",
    "volatility_ratio",

    "location_in_range",
    "distance_from_high",
    "distance_from_low",

    "normalized_slope",
    "momentum_acceleration",

    "neutral_ratio",
]


# These combinations are deliberately interpretable.
#
# We are NOT using a black-box neural network yet.
#
# The purpose is to determine whether combinations of features
# actually improve directional information.

COMBINATIONS = {

    "momentum_structure": [
        "return_15",
        "return_30",
        "directional_imbalance",
        "normalized_slope",
    ],

    "volatility_direction": [
        "volatility",
        "volatility_ratio",
        "directional_imbalance",
    ],

    "candle_balance": [
        "bullish_ratio",
        "bearish_ratio",
        "directional_imbalance",
        "strong_body_ratio",
    ],

    "range_position": [
        "location_in_range",
        "distance_from_high",
        "distance_from_low",
        "directional_imbalance",
    ],

    "rejection_momentum": [
        "rejection_imbalance",
        "momentum_acceleration",
        "directional_imbalance",
        "return_15",
    ],

    "full_feature_model": FEATURE_NAMES,
}


# ============================================================
# TRAIN LINEAR CLASSIFIER
# ============================================================

def train_model(records, feature_names):

    stats = calculate_stats(
        records,
        feature_names
    )

    standardized = []

    for r in records:

        x = standardize(
            r["features"],
            stats
        )

        y = r["outcome"]

        standardized.append(
            (x, y)
        )

    # --------------------------------------------------------
    # Calculate class centroids.
    #
    # This is intentionally simple and interpretable.
    # We are testing whether feature combinations contain
    # directional information, not optimizing a giant model.
    # --------------------------------------------------------

    classes = [
        "bullish",
        "neutral",
        "bearish",
    ]

    centroids = {}

    for cls in classes:

        class_items = [
            x for x, y in standardized
            if y == cls
        ]

        centroid = {}

        for name in feature_names:

            centroid[name] = safe_mean([
                x.get(name, 0.0)
                for x in class_items
            ])

        centroids[cls] = centroid

    return {
        "stats": stats,
        "centroids": centroids,
        "feature_names": feature_names,
    }


# ============================================================
# PREDICTION
# ============================================================

def predict_model(model, features):

    stats = model["stats"]
    centroids = model["centroids"]
    feature_names = model["feature_names"]

    x = standardize(
        features,
        stats
    )

    distances = {}

    for cls, centroid in centroids.items():

        distance = 0.0

        for name in feature_names:

            value = x.get(name, 0.0)

            center = centroid.get(
                name,
                0.0
            )

            difference = (
                value - center
            )

            distance += difference * difference

        distances[cls] = distance

    return min(
        distances,
        key=distances.get
    )


# ============================================================
# METRICS
# ============================================================

def confusion_matrix(records):

    classes = [
        "bullish",
        "neutral",
        "bearish",
    ]

    matrix = {
        prediction: {
            actual: 0
            for actual in classes
        }
        for prediction in classes
    }

    for r in records:

        matrix[
            r["prediction"]
        ][
            r["outcome"]
        ] += 1

    return matrix


def calculate_metrics(records):

    if not records:
        return {
            "accuracy": 0.0,
            "balanced_accuracy": 0.0,
            "macro_f1": 0.0,
            "directional_accuracy": 0.0,
            "directional_f1": 0.0,
            "buy_precision": 0.0,
            "sell_precision": 0.0,
            "coverage": 0.0,
        }

    classes = [
        "bullish",
        "neutral",
        "bearish",
    ]

    correct = sum(
        1
        for r in records
        if r["prediction"] == r["outcome"]
    )

    accuracy = (
        correct / len(records)
    )

    matrix = confusion_matrix(
        records
    )

    recalls = []
    f1s = []

    for cls in classes:

        tp = matrix[cls][cls]

        actual_count = sum(
            matrix[p][cls]
            for p in classes
        )

        predicted_count = sum(
            matrix[cls][a]
            for a in classes
        )

        recall = (
            tp / actual_count
            if actual_count
            else 0.0
        )

        precision = (
            tp / predicted_count
            if predicted_count
            else 0.0
        )

        if precision + recall == 0:
            f1 = 0.0
        else:
            f1 = (
                2
                * precision
                * recall
                / (precision + recall)
            )

        recalls.append(recall)
        f1s.append(f1)

    balanced_accuracy = safe_mean(
        recalls
    )

    macro_f1 = safe_mean(
        f1s
    )

    # --------------------------------------------------------
    # Directional metrics
    # --------------------------------------------------------

    directional = [
        r for r in records
        if r["outcome"] != "neutral"
    ]

    directional_correct = sum(
        1
        for r in directional
        if (
            r["prediction"] == r["outcome"]
            and r["prediction"] != "neutral"
        )
    )

    directional_accuracy = (
        directional_correct / len(directional)
        if directional
        else 0.0
    )

    buy_tp = sum(
        1
        for r in records
        if r["prediction"] == "bullish"
        and r["outcome"] == "bullish"
    )

    buy_predicted = sum(
        1
        for r in records
        if r["prediction"] == "bullish"
    )

    sell_tp = sum(
        1
        for r in records
        if r["prediction"] == "bearish"
        and r["outcome"] == "bearish"
    )

    sell_predicted = sum(
        1
        for r in records
        if r["prediction"] == "bearish"
    )

    buy_precision = (
        buy_tp / buy_predicted
        if buy_predicted
        else 0.0
    )

    sell_precision = (
        sell_tp / sell_predicted
        if sell_predicted
        else 0.0
    )

    directional_f1_precision = safe_mean([
        buy_precision,
        sell_precision
    ])

    directional_f1_recall = directional_accuracy

    if (
        directional_f1_precision
        + directional_f1_recall
        == 0
    ):
        directional_f1 = 0.0
    else:
        directional_f1 = (
            2
            * directional_f1_precision
            * directional_f1_recall
            /
            (
                directional_f1_precision
                + directional_f1_recall
            )
        )

    coverage = (
        len(directional)
        / len(records)
    )

    return {
        "accuracy": accuracy,
        "balanced_accuracy": balanced_accuracy,
        "macro_f1": macro_f1,
        "directional_accuracy": directional_accuracy,
        "directional_f1": directional_f1,
        "buy_precision": buy_precision,
        "sell_precision": sell_precision,
        "coverage": coverage,
    }


# ============================================================
# BASELINES
# ============================================================

def baseline_majority(train_records, test_records):

    counts = Counter(
        r["outcome"]
        for r in train_records
    )

    majority = counts.most_common(1)[0][0]

    result = []

    for r in test_records:

        copy = dict(r)
        copy["prediction"] = majority

        result.append(copy)

    return result


def baseline_momentum(test_records):

    result = []

    for r in test_records:

        features = r["features"]

        momentum = (
            features["return_15"]
            + features["return_30"]
            + features["directional_imbalance"] * 2.0
        )

        if momentum > 0:
            prediction = "bullish"
        elif momentum < 0:
            prediction = "bearish"
        else:
            prediction = "neutral"

        copy = dict(r)
        copy["prediction"] = prediction

        result.append(copy)

    return result


# ============================================================
# WALK-FORWARD TEST
# ============================================================

def run_walk_forward(records, feature_names):

    results = []

    start = TRAIN_SIZE

    while start < len(records):

        train_start = max(
            0,
            start - TRAIN_SIZE
        )

        train_records = records[
            train_start:start
        ]

        test_end = min(
            len(records),
            start + TEST_BLOCK_SIZE
        )

        test_records = records[
            start:test_end
        ]

        if len(train_records) < 100:
            break

        if not test_records:
            break

        model = train_model(
            train_records,
            feature_names
        )

        predicted = []

        for r in test_records:

            copy = dict(r)

            copy["prediction"] = predict_model(
                model,
                r["features"]
            )

            predicted.append(copy)

        results.extend(predicted)

        start = test_end

    return results


# ============================================================
# PRINT RESULTS
# ============================================================

def print_metrics(name, metrics):

    print()
    print(name)
    print("-" * 70)

    print(
        f"Accuracy:             "
        f"{metrics['accuracy'] * 100:.2f}%"
    )

    print(
        f"Balanced accuracy:    "
        f"{metrics['balanced_accuracy'] * 100:.2f}%"
    )

    print(
        f"Macro F1:             "
        f"{metrics['macro_f1'] * 100:.2f}%"
    )

    print(
        f"Directional accuracy: "
        f"{metrics['directional_accuracy'] * 100:.2f}%"
    )

    print(
        f"Directional F1:       "
        f"{metrics['directional_f1'] * 100:.2f}%"
    )

    print(
        f"BUY precision:        "
        f"{metrics['buy_precision'] * 100:.2f}%"
    )

    print(
        f"SELL precision:       "
        f"{metrics['sell_precision'] * 100:.2f}%"
    )

    print(
        f"Directional coverage: "
        f"{metrics['coverage'] * 100:.2f}%"
    )


def print_confusion(records):

    matrix = confusion_matrix(
        records
    )

    print()
    print("Confusion Matrix")
    print(
        "Prediction       Bullish   Neutral   Bearish"
    )
    print("-" * 55)

    for prediction in [
        "bullish",
        "neutral",
        "bearish",
    ]:

        print(
            f"{prediction:<16}"
            f"{matrix[prediction]['bullish']:>8}"
            f"{matrix[prediction]['neutral']:>10}"
            f"{matrix[prediction]['bearish']:>10}"
        )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("MLAI v3.3 FEATURE COMBINATION MODEL TEST")
    print("=" * 70)

    print()
    print(f"Market file: {DATA_FILE}")
    print(f"Current window: {CURRENT_WINDOW}")
    print(f"Horizons: {HORIZONS}")
    print(f"Threshold: +/-{THRESHOLD:.2f}%")
    print()

    # --------------------------------------------------------
    # LOAD MARKET DATA READ-ONLY
    # --------------------------------------------------------

    with open(
        DATA_FILE,
        "rb"
    ) as f:

        data = pickle.load(f)

    candles = data["candles"]

    print(
        f"Total candles: {len(candles)}"
    )

    print()
    print("=" * 70)
    print("PROTECTION CHECK")
    print("=" * 70)

    print("market_data.bin: READ ONLY")
    print("mlai_v31.py: NOT MODIFIED")
    print("learning memory: NOT MODIFIED")
    print("production threshold: NOT MODIFIED")

    # --------------------------------------------------------
    # TEST EACH HORIZON
    # --------------------------------------------------------

    for horizon in HORIZONS:

        print()
        print("=" * 70)
        print(
            f"HORIZON: {horizon} CANDLES"
        )
        print("=" * 70)

        records = build_records(
            candles,
            horizon
        )

        print(
            f"Historical records: "
            f"{len(records)}"
        )

        if len(records) < TRAIN_SIZE + TEST_BLOCK_SIZE:
            print(
                "Not enough records for "
                "walk-forward validation."
            )
            continue

        # ----------------------------------------------------
        # BASELINES
        # ----------------------------------------------------

        train_records = records[
            :TRAIN_SIZE
        ]

        test_records = records[
            TRAIN_SIZE:
        ]

        majority = baseline_majority(
            train_records,
            test_records
        )

        momentum = baseline_momentum(
            test_records
        )

        print()
        print("=" * 70)
        print("BASELINES")
        print("=" * 70)

        print_metrics(
            "Majority baseline",
            calculate_metrics(
                majority
            )
        )

        print_metrics(
            "Momentum baseline",
            calculate_metrics(
                momentum
            )
        )

        # ----------------------------------------------------
        # FEATURE COMBINATIONS
        # ----------------------------------------------------

        for name, feature_names in COMBINATIONS.items():

            print()
            print("=" * 70)
            print(
                f"FEATURE MODEL: {name}"
            )
            print("=" * 70)

            print(
                "Features:"
            )

            print(
                ", ".join(feature_names)
            )

            predicted = run_walk_forward(
                records,
                feature_names
            )

            metrics = calculate_metrics(
                predicted
            )

            print_metrics(
                name,
                metrics
            )

            print_confusion(
                predicted
            )

    print()
    print("=" * 70)
    print("MLAI v3.3 FEATURE COMBINATION TEST COMPLETE")
    print("=" * 70)

    print()
    print("IMPORTANT:")
    print(
        "This is a diagnostic experiment only."
    )

    print(
        "No production MLAI logic was changed."
    )

    print(
        "No market data was modified."
    )

    print(
        "No learning memory was modified."
    )

    print(
        "Results are historical validation only."
    )

    print(
        "Higher historical accuracy does NOT "
        "guarantee future trading performance."
    )

    print("=" * 70)


if __name__ == "__main__":
    main()