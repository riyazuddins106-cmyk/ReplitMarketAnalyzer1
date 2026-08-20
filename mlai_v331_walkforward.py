import pickle
import math
from statistics import mean
from collections import Counter


# ============================================================
# MLAI v3.3.1
# UNSEEN WALK-FORWARD VALIDATION
#
# Purpose:
# Test whether the strongest v3.3 feature group:
#
#   volatility
#   volatility_ratio
#   directional_imbalance
#
# contains repeatable directional information on unseen
# chronological market data.
#
# IMPORTANT:
# - market_data.bin is READ ONLY
# - mlai_v31.py is NOT modified
# - learning memory is NOT modified
# - no production threshold is changed
# ============================================================


MARKET_FILE = "market_data.bin"

CURRENT_WINDOW = 60
HORIZONS = [4, 8, 16]

THRESHOLD = 0.15

# Number of chronological validation windows.
NUM_WINDOWS = 4

# Percentage of usable historical records reserved for
# chronological validation.
VALIDATION_RATIO = 0.30


# ============================================================
# BASIC HELPERS
# ============================================================

def percentage_change(old, new):
    if old == 0:
        return 0.0

    return ((new - old) / abs(old)) * 100.0


def safe_div(a, b):
    if b == 0:
        return 0.0

    return a / b


def classify_return(return_value):
    if return_value > THRESHOLD:
        return "bullish"

    if return_value < -THRESHOLD:
        return "bearish"

    return "neutral"


def harmonic_mean(a, b):
    if a <= 0 or b <= 0:
        return 0.0

    return 2.0 * a * b / (a + b)


# ============================================================
# FEATURE EXTRACTION
# ============================================================

def calculate_features(candles):
    """
    Calculate features using ONLY candles available
    at the prediction point.
    """

    closes = [
        float(c["close"])
        for c in candles
    ]

    highs = [
        float(c["high"])
        for c in candles
    ]

    lows = [
        float(c["low"])
        for c in candles
    ]

    opens = [
        float(c["open"])
        for c in candles
    ]

    if len(closes) < CURRENT_WINDOW:
        raise ValueError("Not enough candles.")

    # --------------------------------------------------------
    # Returns
    # --------------------------------------------------------

    def calc_return(n):

        if len(closes) <= n:
            return 0.0

        return percentage_change(
            closes[-n - 1],
            closes[-1]
        )

    return_5 = calc_return(5)
    return_10 = calc_return(10)
    return_15 = calc_return(15)
    return_30 = calc_return(30)
    return_60 = calc_return(60)

    # --------------------------------------------------------
    # Candle direction
    # --------------------------------------------------------

    bullish = 0
    bearish = 0
    neutral = 0

    for c in candles[-CURRENT_WINDOW:]:

        o = float(c["open"])
        cl = float(c["close"])

        if cl > o:
            bullish += 1

        elif cl < o:
            bearish += 1

        else:
            neutral += 1

    total = float(CURRENT_WINDOW)

    bullish_ratio = bullish / total
    bearish_ratio = bearish / total
    neutral_ratio = neutral / total

    directional_imbalance = (
        bullish_ratio - bearish_ratio
    )

    # --------------------------------------------------------
    # Candle ranges
    # --------------------------------------------------------

    ranges = []

    bodies = []

    body_ratios = []

    for o, h, l, c in zip(
        opens[-CURRENT_WINDOW:],
        highs[-CURRENT_WINDOW:],
        lows[-CURRENT_WINDOW:],
        closes[-CURRENT_WINDOW:]
    ):

        candle_range = max(
            h - l,
            0.0
        )

        body = abs(c - o)

        ranges.append(candle_range)

        bodies.append(body)

        if candle_range > 0:

            body_ratios.append(
                body / candle_range
            )

        else:

            body_ratios.append(0.0)

    average_range = mean(ranges)

    # --------------------------------------------------------
    # Volatility
    # --------------------------------------------------------

    recent_ranges = ranges[-10:]
    older_ranges = ranges[:-10]

    recent_volatility = (
        mean(recent_ranges)
        if recent_ranges
        else 0.0
    )

    older_volatility = (
        mean(older_ranges)
        if older_ranges
        else recent_volatility
    )

    volatility = safe_div(
        recent_volatility,
        abs(closes[-1])
    ) * 100.0

    volatility_ratio = safe_div(
        recent_volatility,
        older_volatility
    )

    # --------------------------------------------------------
    # Extra diagnostic features
    # --------------------------------------------------------

    average_body_ratio = mean(
        body_ratios
    )

    # --------------------------------------------------------
    # Momentum acceleration
    # --------------------------------------------------------

    if len(closes) >= 30:

        previous_return = percentage_change(
            closes[-30],
            closes[-15]
        )

        recent_return = percentage_change(
            closes[-15],
            closes[-1]
        )

        momentum_acceleration = (
            recent_return
            - previous_return
        )

    else:

        momentum_acceleration = 0.0

    # --------------------------------------------------------
    # Return all features
    # --------------------------------------------------------

    return {

        "return_5": return_5,
        "return_10": return_10,
        "return_15": return_15,
        "return_30": return_30,
        "return_60": return_60,

        "bullish_ratio": bullish_ratio,
        "bearish_ratio": bearish_ratio,
        "neutral_ratio": neutral_ratio,

        "directional_imbalance":
            directional_imbalance,

        "volatility":
            volatility,

        "volatility_ratio":
            volatility_ratio,

        "average_body_ratio":
            average_body_ratio,

        "momentum_acceleration":
            momentum_acceleration,
    }


# ============================================================
# NORMALIZATION
# ============================================================

def normalize_value(value, low, high):

    if high == low:
        return 0.5

    return (
        (value - low)
        /
        (high - low)
    )


def build_feature_vector(feature):

    return [
        feature["volatility"],
        feature["volatility_ratio"],
        feature["directional_imbalance"],
    ]


# ============================================================
# SIMPLE FEATURE MODEL
# ============================================================

def train_feature_model(records):

    """
    Train a very simple class-centroid model.

    This deliberately avoids a complicated ML library so that
    the experiment remains transparent.

    Each class gets an average feature vector.
    A new observation is classified according to the closest
    historical class centroid.
    """

    classes = [
        "bullish",
        "neutral",
        "bearish"
    ]

    vectors = {
        c: []
        for c in classes
    }

    for record in records:

        label = record["actual"]

        vector = record["features"]

        vectors[label].append(vector)

    centroids = {}

    for label in classes:

        samples = vectors[label]

        if not samples:

            centroids[label] = None

            continue

        dimension = len(samples[0])

        centroid = []

        for i in range(dimension):

            centroid.append(
                mean(
                    sample[i]
                    for sample in samples
                )
            )

        centroids[label] = centroid

    return centroids


def distance(a, b):

    if b is None:
        return float("inf")

    total = 0.0

    for x, y in zip(a, b):

        total += (
            (x - y) ** 2
        )

    return math.sqrt(total)


def predict_feature_model(
    vector,
    centroids
):

    distances = {}

    for label, centroid in centroids.items():

        distances[label] = distance(
            vector,
            centroid
        )

    return min(
        distances,
        key=distances.get
    )


# ============================================================
# MOMENTUM BASELINE
# ============================================================

def momentum_prediction(feature):

    """
    Simple baseline.

    Positive 60-candle momentum -> bullish
    Negative 60-candle momentum -> bearish
    Near zero -> neutral
    """

    value = feature["return_60"]

    if value > 0:
        return "bullish"

    if value < 0:
        return "bearish"

    return "neutral"


# ============================================================
# RECORD BUILDING
# ============================================================

def build_records(
    candles,
    start_index,
    end_index,
    horizon
):

    records = []

    maximum_index = min(
        end_index,
        len(candles) - horizon
    )

    for i in range(
        start_index,
        maximum_index
    ):

        if i < CURRENT_WINDOW:
            continue

        context = candles[
            i - CURRENT_WINDOW:i
        ]

        current_close = float(
            candles[i - 1]["close"]
        )

        future_close = float(
            candles[
                i + horizon - 1
            ]["close"]
        )

        future_return = percentage_change(
            current_close,
            future_close
        )

        actual = classify_return(
            future_return
        )

        features = calculate_features(
            context
        )

        records.append({

            "index": i,

            "features":
                build_feature_vector(
                    features
                ),

            "full_features":
                features,

            "actual":
                actual,

            "future_return":
                future_return,
        })

    return records


# ============================================================
# METRICS
# ============================================================

def confusion_matrix(
    records,
    prediction_key
):

    labels = [
        "bullish",
        "neutral",
        "bearish"
    ]

    matrix = {
        predicted: {
            actual: 0
            for actual in labels
        }
        for predicted in labels
    }

    for r in records:

        prediction = r[prediction_key]
        actual = r["actual"]

        matrix[prediction][actual] += 1

    return matrix


def classification_metrics(
    records,
    prediction_key
):

    labels = [
        "bullish",
        "neutral",
        "bearish"
    ]

    if not records:

        return {
            "accuracy": 0.0,
            "balanced_accuracy": 0.0,
            "macro_f1": 0.0,
            "directional_accuracy": 0.0,
            "directional_f1": 0.0,
            "buy_precision": 0.0,
            "sell_precision": 0.0,
            "buy_recall": 0.0,
            "sell_recall": 0.0,
            "coverage": 0.0,
        }

    matrix = confusion_matrix(
        records,
        prediction_key
    )

    total = len(records)

    correct = sum(
        matrix[label][label]
        for label in labels
    )

    accuracy = (
        correct / total * 100.0
    )

    recalls = []
    f1_values = []

    for label in labels:

        tp = matrix[label][label]

        actual_total = sum(
            matrix[p][label]
            for p in labels
        )

        predicted_total = sum(
            matrix[label][a]
            for a in labels
        )

        recall = safe_div(
            tp,
            actual_total
        )

        precision = safe_div(
            tp,
            predicted_total
        )

        f1 = harmonic_mean(
            precision,
            recall
        )

        recalls.append(recall)

        f1_values.append(f1)

    balanced_accuracy = (
        mean(recalls) * 100.0
    )

    macro_f1 = (
        mean(f1_values) * 100.0
    )

    # --------------------------------------------------------
    # Directional metrics
    # --------------------------------------------------------

    directional_records = [
        r
        for r in records
        if r["actual"] != "neutral"
    ]

    directional_predictions = [
        r
        for r in records
        if r[prediction_key] != "neutral"
    ]

    if directional_records:

        directional_correct = sum(
            1
            for r in directional_records
            if r[prediction_key]
            == r["actual"]
        )

        directional_accuracy = (
            directional_correct
            /
            len(directional_records)
            * 100.0
        )

    else:

        directional_accuracy = 0.0

    # Precision / recall for BUY

    buy_tp = matrix["bullish"]["bullish"]

    buy_predicted = sum(
        matrix["bullish"][a]
        for a in labels
    )

    buy_actual = sum(
        matrix[p]["bullish"]
        for p in labels
    )

    buy_precision = safe_div(
        buy_tp,
        buy_predicted
    )

    buy_recall = safe_div(
        buy_tp,
        buy_actual
    )

    # SELL

    sell_tp = matrix["bearish"]["bearish"]

    sell_predicted = sum(
        matrix["bearish"][a]
        for a in labels
    )

    sell_actual = sum(
        matrix[p]["bearish"]
        for p in labels
    )

    sell_precision = safe_div(
        sell_tp,
        sell_predicted
    )

    sell_recall = safe_div(
        sell_tp,
        sell_actual
    )

    directional_f1 = harmonic_mean(
        buy_precision,
        buy_recall
    )

    sell_f1 = harmonic_mean(
        sell_precision,
        sell_recall
    )

    directional_f1 = (
        (directional_f1 + sell_f1)
        / 2.0
        * 100.0
    )

    coverage = (
        len(directional_predictions)
        /
        total
        * 100.0
    )

    return {

        "accuracy": accuracy,

        "balanced_accuracy":
            balanced_accuracy,

        "macro_f1":
            macro_f1,

        "directional_accuracy":
            directional_accuracy,

        "directional_f1":
            directional_f1,

        "buy_precision":
            buy_precision * 100.0,

        "sell_precision":
            sell_precision * 100.0,

        "buy_recall":
            buy_recall * 100.0,

        "sell_recall":
            sell_recall * 100.0,

        "coverage":
            coverage,
    }


# ============================================================
# APPLY MODEL
# ============================================================

def apply_model(
    records,
    centroids
):

    for r in records:

        vector = r["features"]

        r["model_prediction"] = (
            predict_feature_model(
                vector,
                centroids
            )
        )

        r["momentum_prediction"] = (
            momentum_prediction(
                r["full_features"]
            )
        )


# ============================================================
# PRINT METRICS
# ============================================================

def print_metrics(
    name,
    metrics
):

    print()
    print(name)
    print("-" * 70)

    print(
        f"Accuracy:             "
        f"{metrics['accuracy']:.2f}%"
    )

    print(
        f"Balanced accuracy:    "
        f"{metrics['balanced_accuracy']:.2f}%"
    )

    print(
        f"Macro F1:             "
        f"{metrics['macro_f1']:.2f}%"
    )

    print(
        f"Directional accuracy: "
        f"{metrics['directional_accuracy']:.2f}%"
    )

    print(
        f"Directional F1:       "
        f"{metrics['directional_f1']:.2f}%"
    )

    print(
        f"BUY precision:        "
        f"{metrics['buy_precision']:.2f}%"
    )

    print(
        f"SELL precision:       "
        f"{metrics['sell_precision']:.2f}%"
    )

    print(
        f"BUY recall:           "
        f"{metrics['buy_recall']:.2f}%"
    )

    print(
        f"SELL recall:          "
        f"{metrics['sell_recall']:.2f}%"
    )

    print(
        f"Directional coverage: "
        f"{metrics['coverage']:.2f}%"
    )


# ============================================================
# CONFUSION MATRIX PRINT
# ============================================================

def print_confusion(
    records,
    prediction_key
):

    matrix = confusion_matrix(
        records,
        prediction_key
    )

    print()
    print("Confusion Matrix")
    print(
        "Prediction       "
        "Bullish   Neutral   Bearish"
    )
    print("-" * 55)

    for predicted in [
        "bullish",
        "neutral",
        "bearish"
    ]:

        print(
            f"{predicted:<17}"
            f"{matrix[predicted]['bullish']:>7}"
            f"{matrix[predicted]['neutral']:>10}"
            f"{matrix[predicted]['bearish']:>10}"
        )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print(
        "MLAI v3.3.1 "
        "UNSEEN WALK-FORWARD VALIDATION"
    )
    print("=" * 70)

    print()
    print(f"Market file: {MARKET_FILE}")
    print(
        f"Current window: "
        f"{CURRENT_WINDOW}"
    )
    print(
        f"Horizons: "
        f"{HORIZONS}"
    )
    print(
        f"Threshold: "
        f"+/-{THRESHOLD:.2f}%"
    )
    print(
        f"Validation windows: "
        f"{NUM_WINDOWS}"
    )

    # --------------------------------------------------------
    # Load market data
    # --------------------------------------------------------

    with open(
        MARKET_FILE,
        "rb"
    ) as f:

        data = pickle.load(f)

    candles = data["candles"]

    print()
    print(
        f"Total candles: "
        f"{len(candles)}"
    )

    # --------------------------------------------------------
    # Protection
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("PROTECTION CHECK")
    print("=" * 70)

    print(
        "market_data.bin: READ ONLY"
    )

    print(
        "mlai_v31.py: NOT MODIFIED"
    )

    print(
        "learning memory: NOT MODIFIED"
    )

    print(
        "production threshold: NOT MODIFIED"
    )

    # --------------------------------------------------------
    # Determine usable chronological records
    # --------------------------------------------------------

    minimum_index = CURRENT_WINDOW

    maximum_index = (
        len(candles)
        - max(HORIZONS)
    )

    usable_count = (
        maximum_index
        - minimum_index
    )

    validation_count = int(
        usable_count
        * VALIDATION_RATIO
    )

    calibration_count = (
        usable_count
        - validation_count
    )

    calibration_end = (
        minimum_index
        + calibration_count
    )

    validation_start = calibration_end

    print()
    print("=" * 70)
    print("CHRONOLOGICAL SPLIT")
    print("=" * 70)

    print(
        f"Calibration records: "
        f"{calibration_count}"
    )

    print(
        f"Validation records:  "
        f"{validation_count}"
    )

    print(
        f"Validation starts at "
        f"candle index: "
        f"{validation_start}"
    )

    # --------------------------------------------------------
    # Divide validation into windows
    # --------------------------------------------------------

    window_size = max(
        1,
        validation_count
        // NUM_WINDOWS
    )

    # --------------------------------------------------------
    # Results storage
    # --------------------------------------------------------

    all_results = {}

    for horizon in HORIZONS:

        print()
        print("=" * 70)
        print(
            f"HORIZON: "
            f"{horizon} CANDLES"
        )
        print("=" * 70)

        # ----------------------------------------------------
        # Calibration data
        # ----------------------------------------------------

        calibration_records = build_records(
            candles,
            minimum_index,
            calibration_end,
            horizon
        )

        print(
            f"Calibration records: "
            f"{len(calibration_records)}"
        )

        # ----------------------------------------------------
        # Train ONLY on earlier chronological data
        # ----------------------------------------------------

        centroids = train_feature_model(
            calibration_records
        )

        print()
        print("Feature model trained ONLY on")
        print("earlier chronological data.")

        print()
        print("Feature set:")
        print(
            "volatility, "
            "volatility_ratio, "
            "directional_imbalance"
        )

        # ----------------------------------------------------
        # Validation windows
        # ----------------------------------------------------

        horizon_results = []

        for window_number in range(
            NUM_WINDOWS
        ):

            start = (
                validation_start
                + window_number
                * window_size
            )

            if window_number == (
                NUM_WINDOWS - 1
            ):

                end = maximum_index

            else:

                end = min(
                    start + window_size,
                    maximum_index
                )

            if start >= end:
                continue

            validation_records = build_records(
                candles,
                start,
                end,
                horizon
            )

            if not validation_records:
                continue

            apply_model(
                validation_records,
                centroids
            )

            model_metrics = (
                classification_metrics(
                    validation_records,
                    "model_prediction"
                )
            )

            momentum_metrics = (
                classification_metrics(
                    validation_records,
                    "momentum_prediction"
                )
            )

            print()
            print(
                "=" * 70
            )

            print(
                f"VALIDATION WINDOW "
                f"{window_number + 1}"
            )

            print(
                "=" * 70
            )

            print(
                f"Index range: "
                f"{start} -> {end - 1}"
            )

            print(
                f"Records: "
                f"{len(validation_records)}"
            )

            print()
            print(
                "FEATURE MODEL"
            )

            print_metrics(
                "Volatility + Directional "
                "Structure",
                model_metrics
            )

            print()
            print(
                "MOMENTUM BASELINE"
            )

            print_metrics(
                "60-Candle Momentum",
                momentum_metrics
            )

            improvement = (
                model_metrics[
                    "directional_accuracy"
                ]
                -
                momentum_metrics[
                    "directional_accuracy"
                ]
            )

            f1_improvement = (
                model_metrics[
                    "directional_f1"
                ]
                -
                momentum_metrics[
                    "directional_f1"
                ]
            )

            print()
            print(
                "MODEL IMPROVEMENT"
            )

            print(
                f"Directional accuracy lift: "
                f"{improvement:+.2f} percentage points"
            )

            print(
                f"Directional F1 lift: "
                f"{f1_improvement:+.2f} percentage points"
            )

            print_confusion(
                validation_records,
                "model_prediction"
            )

            horizon_results.append({

                "window":
                    window_number + 1,

                "start":
                    start,

                "end":
                    end - 1,

                "model":
                    model_metrics,

                "momentum":
                    momentum_metrics,

                "accuracy_lift":
                    improvement,

                "f1_lift":
                    f1_improvement,
            })

        all_results[horizon] = (
            horizon_results
        )

    # ========================================================
    # FINAL SUMMARY
    # ========================================================

    print()
    print("=" * 70)
    print(
        "FINAL WALK-FORWARD SUMMARY"
    )
    print("=" * 70)

    for horizon in HORIZONS:

        results = all_results[horizon]

        if not results:
            continue

        model_directional = [
            r["model"][
                "directional_accuracy"
            ]
            for r in results
        ]

        momentum_directional = [
            r["momentum"][
                "directional_accuracy"
            ]
            for r in results
        ]

        model_f1 = [
            r["model"][
                "directional_f1"
            ]
            for r in results
        ]

        momentum_f1 = [
            r["momentum"][
                "directional_f1"
            ]
            for r in results
        ]

        lifts = [
            r["accuracy_lift"]
            for r in results
        ]

        f1_lifts = [
            r["f1_lift"]
            for r in results
        ]

        print()
        print(
            f"HORIZON: "
            f"{horizon} CANDLES"
        )

        print("-" * 70)

        print(
            f"Model average directional "
            f"accuracy: "
            f"{mean(model_directional):.2f}%"
        )

        print(
            f"Momentum average directional "
            f"accuracy: "
            f"{mean(momentum_directional):.2f}%"
        )

        print(
            f"Average accuracy lift: "
            f"{mean(lifts):+.2f} pp"
        )

        print(
            f"Model average directional F1: "
            f"{mean(model_f1):.2f}%"
        )

        print(
            f"Momentum average directional F1: "
            f"{mean(momentum_f1):.2f}%"
        )

        print(
            f"Average F1 lift: "
            f"{mean(f1_lifts):+.2f} pp"
        )

        print(
            f"Worst model directional accuracy: "
            f"{min(model_directional):.2f}%"
        )

        print(
            f"Best model directional accuracy: "
            f"{max(model_directional):.2f}%"
        )

    # ========================================================
    # FINAL INTERPRETATION
    # ========================================================

    print()
    print("=" * 70)
    print(
        "MLAI v3.3.1 DIAGNOSTIC VERDICT"
    )
    print("=" * 70)

    print()
    print(
        "This experiment does NOT change "
        "MLAI production logic."
    )

    print()
    print(
        "The important question is whether "
        "the feature model consistently "
        "beats the momentum baseline across "
        "unseen chronological windows."
    )

    print()
    print(
        "Do NOT interpret any individual "
        "window as future trading probability."
    )

    print()
    print(
        "If the feature model improves "
        "consistently across multiple windows, "
        "we have stronger evidence that the "
        "60-candle structure contains "
        "repeatable directional information."
    )

    print()
    print(
        "If performance collapses across "
        "unseen windows, the previous result "
        "was likely regime-specific or "
        "overfit."
    )

    print()
    print(
        "market_data.bin was READ ONLY."
    )

    print(
        "mlai_v31.py was NOT modified."
    )

    print(
        "Learning memory was NOT modified."
    )

    print(
        "No production threshold was changed."
    )

    print()
    print("=" * 70)
    print(
        "MLAI v3.3.1 VALIDATION COMPLETE"
    )
    print("=" * 70)


if __name__ == "__main__":
    main()