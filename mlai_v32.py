import os
import pickle
import math
from collections import Counter
from datetime import datetime, timezone


# ============================================================
# MLAI v3.2
# HISTORICAL PREDICTION CALIBRATION ENGINE
#
# PURPOSE:
# Determine whether the v3.1 outcome classification threshold
# is appropriate for the historical XAU/USD dataset.
#
# IMPORTANT:
# - Does NOT modify market_data.bin
# - Does NOT modify mlai_v31.py
# - Does NOT overwrite mlai_learning_memory.bin
# - Calibration results are saved separately
# ============================================================

VERSION = "MLAI v3.2 HISTORICAL PREDICTION CALIBRATION ENGINE"

MARKET_FILE = "market_data.bin"
CALIBRATION_FILE = "mlai_v32_calibration.bin"
REPORT_FILE = "MLAI_V32_CALIBRATION_REPORT.md"
STATUS_FILE = "MLAI_PROJECT_STATUS.md"

CURRENT_WINDOW = 60

HORIZONS = [4, 8, 16]

THRESHOLDS = [
    0.02,
    0.05,
    0.10,
    0.15,
    0.20,
    0.30,
]

# v3.1 decision thresholds.
MIN_DIRECTIONAL_SEPARATION = 5.0
MIN_DIRECTIONAL_OVER_NEUTRAL = 5.0


# ============================================================
# OUTPUT
# ============================================================

def header(text):
    print()
    print("=" * 78)
    print(text)
    print("=" * 78)


def section(text):
    print()
    print(text)
    print("-" * 78)


# ============================================================
# SAFE NUMBER
# ============================================================

def safe_float(value, default=None):

    try:

        if value is None:
            return default

        if isinstance(value, bool):
            return default

        result = float(value)

        if not math.isfinite(result):
            return default

        return result

    except (TypeError, ValueError):

        return default


# ============================================================
# CANDLE NORMALIZATION
# ============================================================

def normalize_candle(raw):

    if not isinstance(raw, dict):
        return None

    def find_value(names):

        for name in names:

            if name in raw:
                return raw[name]

        return None

    timestamp = find_value([
        "timestamp",
        "datetime",
        "date",
        "time",
        "ts",
    ])

    open_price = safe_float(
        find_value(["open", "o"])
    )

    high_price = safe_float(
        find_value(["high", "h"])
    )

    low_price = safe_float(
        find_value(["low", "l"])
    )

    close_price = safe_float(
        find_value(["close", "c"])
    )

    volume = safe_float(
        find_value(["volume", "v"]),
        0.0
    )

    if (
        open_price is None
        or high_price is None
        or low_price is None
        or close_price is None
    ):
        return None

    if high_price < low_price:
        return None

    if high_price < max(open_price, close_price):
        return None

    if low_price > min(open_price, close_price):
        return None

    return {
        "timestamp": timestamp,
        "open": open_price,
        "high": high_price,
        "low": low_price,
        "close": close_price,
        "volume": volume,
    }


# ============================================================
# LOAD MARKET DATA
# ============================================================

def load_market_data():

    if not os.path.exists(MARKET_FILE):

        raise FileNotFoundError(
            f"{MARKET_FILE} was not found."
        )

    with open(MARKET_FILE, "rb") as f:
        data = pickle.load(f)

    if isinstance(data, list):

        source = data

    elif isinstance(data, dict):

        source = None

        for key in [
            "candles",
            "data",
            "records",
            "market_data",
            "ohlcv",
        ]:

            if (
                key in data
                and isinstance(data[key], list)
            ):

                source = data[key]
                break

        if source is None:

            values = list(data.values())

            if (
                values
                and all(
                    isinstance(x, dict)
                    for x in values
                )
            ):

                source = values

    else:

        source = None

    if source is None:

        raise ValueError(
            "market_data.bin does not contain "
            "a supported candle collection."
        )

    candles = []

    for raw in source:

        candle = normalize_candle(raw)

        if candle is not None:
            candles.append(candle)

    if not candles:

        raise ValueError(
            "No valid OHLC candles were found."
        )

    return candles


# ============================================================
# BASIC CALCULATIONS
# ============================================================

def percentage_change(old, new):

    if old is None or new is None:
        return 0.0

    if old == 0:
        return 0.0

    return (
        (new - old)
        / abs(old)
        * 100.0
    )


def average(values):

    if not values:
        return 0.0

    return sum(values) / len(values)


# ============================================================
# V3.1 CONTEXT ANALYSIS
#
# This is intentionally kept independent from mlai_v31.py.
# ============================================================

def analyze_context(candles):

    if len(candles) < 10:

        raise ValueError(
            "At least 10 candles are required."
        )

    closes = [
        c["close"]
        for c in candles
    ]

    latest = closes[-1]

    # --------------------------------------------------------
    # Direction
    # --------------------------------------------------------

    short_start = closes[-10]

    net_change = percentage_change(
        short_start,
        latest
    )

    if net_change > 0.10:

        direction = "bullish"

    elif net_change < -0.10:

        direction = "bearish"

    else:

        direction = "neutral"

    # --------------------------------------------------------
    # Structure
    # --------------------------------------------------------

    split_index = max(
        5,
        len(candles) // 2
    )

    first_half = closes[:split_index]
    second_half = closes[split_index:]

    first_avg = average(first_half)
    second_avg = average(second_half)

    structure_change = percentage_change(
        first_avg,
        second_avg
    )

    if structure_change > 0.20:

        structure = "bullish_structure"

    elif structure_change < -0.20:

        structure = "bearish_structure"

    else:

        structure = "range_structure"

    # --------------------------------------------------------
    # Momentum
    # --------------------------------------------------------

    if len(closes) >= 12:

        previous_change = percentage_change(
            closes[-12],
            closes[-6]
        )

        recent_change = percentage_change(
            closes[-6],
            closes[-1]
        )

        momentum_difference = (
            recent_change
            - previous_change
        )

        if momentum_difference > 0.05:

            momentum = "increasing"

        elif momentum_difference < -0.05:

            momentum = "decreasing"

        else:

            momentum = "stable"

    else:

        momentum = "stable"

    # --------------------------------------------------------
    # Volatility
    # --------------------------------------------------------

    ranges = []

    for candle in candles:

        close = candle["close"]

        if close == 0:
            continue

        candle_range = (
            candle["high"]
            - candle["low"]
        ) / abs(close) * 100.0

        ranges.append(candle_range)

    if len(ranges) >= 10:

        older_volatility = average(
            ranges[:-5]
        )

        recent_volatility = average(
            ranges[-5:]
        )

        if older_volatility == 0:

            volatility = "stable"

        elif recent_volatility > older_volatility * 1.15:

            volatility = "expanding"

        elif recent_volatility < older_volatility * 0.85:

            volatility = "contracting"

        else:

            volatility = "stable"

    else:

        volatility = "stable"

    # --------------------------------------------------------
    # Rejection
    # --------------------------------------------------------

    upper_rejections = 0
    lower_rejections = 0

    for candle in candles[-20:]:

        body_high = max(
            candle["open"],
            candle["close"]
        )

        body_low = min(
            candle["open"],
            candle["close"]
        )

        upper_wick = (
            candle["high"]
            - body_high
        )

        lower_wick = (
            body_low
            - candle["low"]
        )

        if upper_wick > lower_wick * 1.25:

            upper_rejections += 1

        elif lower_wick > upper_wick * 1.25:

            lower_rejections += 1

    if upper_rejections > lower_rejections + 2:

        rejection = "upper_rejection_dominant"

    elif lower_rejections > upper_rejections + 2:

        rejection = "lower_rejection_dominant"

    else:

        rejection = "balanced_rejection"

    # --------------------------------------------------------
    # Direct evidence
    # --------------------------------------------------------

    bullish_score = 0.0
    bearish_score = 0.0
    neutral_score = 0.0

    if direction == "bullish":

        bullish_score += 30.0

    elif direction == "bearish":

        bearish_score += 30.0

    else:

        neutral_score += 30.0

    if structure == "bullish_structure":

        bullish_score += 25.0

    elif structure == "bearish_structure":

        bearish_score += 25.0

    else:

        neutral_score += 25.0

    if momentum == "increasing":

        if direction == "bullish":

            bullish_score += 15.0

        elif direction == "bearish":

            bearish_score += 15.0

        else:

            neutral_score += 15.0

    elif momentum == "decreasing":

        if direction == "bullish":

            bearish_score += 8.0
            bullish_score += 4.0

        elif direction == "bearish":

            bullish_score += 8.0
            bearish_score += 4.0

        else:

            neutral_score += 12.0

    else:

        neutral_score += 8.0

    if volatility == "expanding":

        if direction == "bullish":

            bullish_score += 8.0

        elif direction == "bearish":

            bearish_score += 8.0

        else:

            neutral_score += 8.0

    elif volatility == "contracting":

        neutral_score += 8.0

    else:

        neutral_score += 4.0

    if rejection == "upper_rejection_dominant":

        bearish_score += 8.0

    elif rejection == "lower_rejection_dominant":

        bullish_score += 8.0

    else:

        neutral_score += 4.0

    total = (
        bullish_score
        + bearish_score
        + neutral_score
    )

    if total <= 0:

        distribution = {
            "bullish": 33.3333,
            "bearish": 33.3333,
            "neutral": 33.3334,
        }

    else:

        distribution = {
            "bullish":
                bullish_score / total * 100.0,

            "bearish":
                bearish_score / total * 100.0,

            "neutral":
                neutral_score / total * 100.0,
        }

    return {
        "direction": direction,
        "structure": structure,
        "momentum": momentum,
        "volatility": volatility,
        "rejection": rejection,
        "latest_price": latest,
        "net_change_percent": net_change,
        "direct_distribution": distribution,
    }


# ============================================================
# V3.1 PREDICTION LOGIC
# ============================================================

def predict_from_context(context):

    direct = context["direct_distribution"]

    bullish = direct["bullish"]
    bearish = direct["bearish"]
    neutral = direct["neutral"]

    strongest_direction = max(
        bullish,
        bearish
    )

    directional_separation = abs(
        bullish - bearish
    )

    neutral_gap = (
        strongest_direction
        - neutral
    )

    if directional_separation < (
        MIN_DIRECTIONAL_SEPARATION
    ):

        return "neutral"

    if neutral_gap < (
        MIN_DIRECTIONAL_OVER_NEUTRAL
    ):

        return "neutral"

    if bullish > bearish:

        return "bullish"

    return "bearish"


# ============================================================
# OUTCOME CLASSIFICATION
# ============================================================

def classify_outcome(movement, threshold):

    if movement > threshold:

        return "bullish"

    if movement < -threshold:

        return "bearish"

    return "neutral"


# ============================================================
# WALK-FORWARD CALIBRATION RECORDS
# ============================================================

def build_calibration_records(
    candles,
    threshold,
    horizon
):

    records = []

    total_candles = len(candles)

    training_end = (
        total_candles
        - CURRENT_WINDOW
    )

    if training_end <= CURRENT_WINDOW:
        return records

    last_decision_index = (
        training_end
        - horizon
        + 1
    )

    if last_decision_index <= CURRENT_WINDOW:
        return records

    for decision_index in range(
        CURRENT_WINDOW,
        last_decision_index
    ):

        context_candles = candles[
            decision_index - CURRENT_WINDOW:
            decision_index
        ]

        context = analyze_context(
            context_candles
        )

        prediction = predict_from_context(
            context
        )

        current_close = candles[
            decision_index - 1
        ]["close"]

        outcome_index = (
            decision_index
            + horizon
            - 1
        )

        if outcome_index >= training_end:
            continue

        future_close = candles[
            outcome_index
        ]["close"]

        movement = percentage_change(
            current_close,
            future_close
        )

        actual = classify_outcome(
            movement,
            threshold
        )

        records.append({
            "decision_index":
                decision_index,

            "prediction":
                prediction,

            "actual":
                actual,

            "movement_percent":
                movement,
        })

    return records


# ============================================================
# CONFUSION MATRIX
#
# Rows    = predicted
# Columns = actual
# ============================================================

def confusion_matrix(records):

    labels = [
        "bullish",
        "neutral",
        "bearish",
    ]

    matrix = {
        predicted: {
            actual: 0
            for actual in labels
        }
        for predicted in labels
    }

    for record in records:

        predicted = record["prediction"]
        actual = record["actual"]

        if (
            predicted in matrix
            and actual in matrix[predicted]
        ):

            matrix[predicted][actual] += 1

    return matrix


# ============================================================
# CLASSIFICATION METRICS
# ============================================================

def calculate_metrics(records):

    labels = [
        "bullish",
        "neutral",
        "bearish",
    ]

    matrix = confusion_matrix(records)

    total = len(records)

    correct = sum(
        matrix[label][label]
        for label in labels
    )

    accuracy = (
        correct / total * 100.0
        if total
        else 0.0
    )

    class_metrics = {}

    recalls = []
    specificities = []
    precisions = []
    f1_values = []

    for label in labels:

        tp = matrix[label][label]

        predicted_total = sum(
            matrix[label][actual]
            for actual in labels
        )

        actual_total = sum(
            matrix[predicted][label]
            for predicted in labels
        )

        fp = (
            predicted_total - tp
        )

        fn = (
            actual_total - tp
        )

        tn = (
            total
            - tp
            - fp
            - fn
        )

        precision = (
            tp / (tp + fp) * 100.0
            if tp + fp > 0
            else 0.0
        )

        recall = (
            tp / (tp + fn) * 100.0
            if tp + fn > 0
            else 0.0
        )

        specificity = (
            tn / (tn + fp) * 100.0
            if tn + fp > 0
            else 0.0
        )

        if precision + recall > 0:

            f1 = (
                2
                * precision
                * recall
                / (precision + recall)
            )

        else:

            f1 = 0.0

        precisions.append(precision)
        recalls.append(recall)
        specificities.append(specificity)
        f1_values.append(f1)

        class_metrics[label] = {
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "tn": tn,
            "precision": precision,
            "recall": recall,
            "specificity": specificity,
            "f1": f1,
            "actual_count": actual_total,
            "predicted_count": predicted_total,
        }

    balanced_accuracy = (
        sum(recalls) / len(recalls)
        if recalls
        else 0.0
    )

    macro_precision = (
        sum(precisions) / len(precisions)
        if precisions
        else 0.0
    )

    macro_recall = (
        sum(recalls) / len(recalls)
        if recalls
        else 0.0
    )

    macro_f1 = (
        sum(f1_values) / len(f1_values)
        if f1_values
        else 0.0
    )

    directional_records = [
        record
        for record in records
        if record["prediction"] in (
            "bullish",
            "bearish",
        )
    ]

    directional_correct = sum(
        1
        for record in directional_records
        if record["prediction"]
        == record["actual"]
    )

    directional_accuracy = (
        directional_correct
        / len(directional_records)
        * 100.0
        if directional_records
        else 0.0
    )

    prediction_distribution = Counter(
        record["prediction"]
        for record in records
    )

    actual_distribution = Counter(
        record["actual"]
        for record in records
    )

    return {
        "total": total,
        "correct": correct,
        "accuracy": accuracy,
        "balanced_accuracy":
            balanced_accuracy,
        "macro_precision":
            macro_precision,
        "macro_recall":
            macro_recall,
        "macro_f1":
            macro_f1,
        "directional_accuracy":
            directional_accuracy,
        "class_metrics":
            class_metrics,
        "confusion_matrix":
            matrix,
        "prediction_distribution":
            dict(prediction_distribution),
        "actual_distribution":
            dict(actual_distribution),
    }


# ============================================================
# THRESHOLD STABILITY
# ============================================================

def calculate_threshold_summary(
    threshold,
    horizon_results
):

    balanced_values = [
        result["metrics"]["balanced_accuracy"]
        for result in horizon_results
    ]

    macro_f1_values = [
        result["metrics"]["macro_f1"]
        for result in horizon_results
    ]

    neutral_f1_values = [
        result["metrics"]["class_metrics"]
        ["neutral"]["f1"]
        for result in horizon_results
    ]

    directional_values = [
        result["metrics"]["directional_accuracy"]
        for result in horizon_results
    ]

    avg_balanced = average(
        balanced_values
    )

    avg_macro_f1 = average(
        macro_f1_values
    )

    avg_neutral_f1 = average(
        neutral_f1_values
    )

    avg_directional = average(
        directional_values
    )

    # Stability = consistency across horizons.
    if balanced_values:

        spread = (
            max(balanced_values)
            - min(balanced_values)
        )

        stability = max(
            0.0,
            100.0 - spread
        )

    else:

        stability = 0.0

    # We deliberately do NOT optimize raw accuracy alone.
    #
    # Balanced accuracy receives the highest weight.
    # Macro F1 rewards all three classes.
    # Neutral F1 specifically protects the neutral class.
    # Stability rewards consistency across horizons.
    #
    score = (
        avg_balanced * 0.40
        + avg_macro_f1 * 0.25
        + avg_neutral_f1 * 0.20
        + stability * 0.15
    )

    return {
        "threshold": threshold,
        "average_balanced_accuracy":
            avg_balanced,
        "average_macro_f1":
            avg_macro_f1,
        "average_neutral_f1":
            avg_neutral_f1,
        "average_directional_accuracy":
            avg_directional,
        "cross_horizon_stability":
            stability,
        "calibration_score":
            score,
    }


# ============================================================
# MAIN CALIBRATION
# ============================================================

try:

    header(
        "MLAI v3.2 HISTORICAL PREDICTION "
        "CALIBRATION ENGINE"
    )

    print()
    print(
        "Purpose: determine whether the v3.1 "
        "outcome threshold is properly calibrated."
    )

    print()
    print(
        f"Market file : {MARKET_FILE}"
    )

    print(
        f"Current window : {CURRENT_WINDOW}"
    )

    print(
        f"Horizons : {HORIZONS}"
    )

    print(
        "Thresholds : "
        + ", ".join(
            f"±{x:.2f}%"
            for x in THRESHOLDS
        )
    )

    # --------------------------------------------------------
    # LOAD
    # --------------------------------------------------------

    candles = load_market_data()

    print()
    print(
        "PASS: market_data.bin loaded."
    )

    print(
        f"Stored candles: {len(candles)}"
    )

    minimum_required = (
        CURRENT_WINDOW
        + max(HORIZONS)
        + 1
    )

    if len(candles) < minimum_required:

        raise ValueError(
            f"Need at least {minimum_required} candles."
        )

    print()
    print(
        "PASS: Original market data will "
        "NOT be modified."
    )

    print(
        "PASS: MLAI v3.1 will NOT be modified."
    )

    # --------------------------------------------------------
    # CALIBRATION
    # --------------------------------------------------------

    all_results = []

    for threshold in THRESHOLDS:

        section(
            f"TESTING THRESHOLD ±{threshold:.2f}%"
        )

        horizon_results = []

        for horizon in HORIZONS:

            records = build_calibration_records(
                candles,
                threshold,
                horizon
            )

            metrics = calculate_metrics(
                records
            )

            result = {
                "threshold":
                    threshold,

                "horizon":
                    horizon,

                "metrics":
                    metrics,
            }

            horizon_results.append(result)

            print(
                f"{horizon:2d} candles -> "
                f"records={metrics['total']} | "
                f"accuracy={metrics['accuracy']:.2f}% | "
                f"balanced={metrics['balanced_accuracy']:.2f}% | "
                f"macro-F1={metrics['macro_f1']:.2f}% | "
                f"neutral-F1="
                f"{metrics['class_metrics']['neutral']['f1']:.2f}%"
            )

        summary = calculate_threshold_summary(
            threshold,
            horizon_results
        )

        print()
        print(
            f"Calibration score : "
            f"{summary['calibration_score']:.2f}"
        )

        print(
            f"Average balanced accuracy : "
            f"{summary['average_balanced_accuracy']:.2f}%"
        )

        print(
            f"Average macro F1 : "
            f"{summary['average_macro_f1']:.2f}%"
        )

        print(
            f"Average neutral F1 : "
            f"{summary['average_neutral_f1']:.2f}%"
        )

        print(
            f"Cross-horizon stability : "
            f"{summary['cross_horizon_stability']:.2f}"
        )

        all_results.append({
            "threshold":
                threshold,

            "horizons":
                horizon_results,

            "summary":
                summary,
        })

    # --------------------------------------------------------
    # RANKING
    # --------------------------------------------------------

    ranked_results = sorted(
        all_results,
        key=lambda item:
            item["summary"]["calibration_score"],
        reverse=True,
    )

    best_result = ranked_results[0]

    recommended_threshold = (
        best_result["threshold"]
    )

    # --------------------------------------------------------
    # DISPLAY RANKING
    # --------------------------------------------------------

    section(
        "THRESHOLD CALIBRATION RANKING"
    )

    print(
        f"{'Threshold':>12} | "
        f"{'Balanced':>10} | "
        f"{'Macro-F1':>10} | "
        f"{'Neutral-F1':>11} | "
        f"{'Stability':>10} | "
        f"{'Score':>10}"
    )

    print("-" * 78)

    for rank, item in enumerate(
        ranked_results,
        start=1
    ):

        summary = item["summary"]

        print(
            f"{rank:02d}. ±"
            f"{item['threshold']:<7.2f} | "
            f"{summary['average_balanced_accuracy']:>9.2f}% | "
            f"{summary['average_macro_f1']:>9.2f}% | "
            f"{summary['average_neutral_f1']:>10.2f}% | "
            f"{summary['cross_horizon_stability']:>9.2f} | "
            f"{summary['calibration_score']:>9.2f}"
        )

    # --------------------------------------------------------
    # BEST THRESHOLD
    # --------------------------------------------------------

    section(
        "CALIBRATION RESULT"
    )

    print(
        f"Current v3.1 threshold : ±0.02%"
    )

    print(
        f"Best historical candidate : "
        f"±{recommended_threshold:.2f}%"
    )

    print(
        f"Calibration score : "
        f"{best_result['summary']['calibration_score']:.2f}"
    )

    if recommended_threshold == 0.02:

        print()
        print(
            "RESULT: ±0.02% remains the strongest "
            "candidate under the calibration criteria."
        )

    else:

        print()
        print(
            "RESULT: Historical evidence suggests "
            f"±{recommended_threshold:.2f}% should be "
            "investigated as a better candidate."
        )

    print()
    print(
        "IMPORTANT: This is a calibration candidate, "
        "NOT a guaranteed future prediction threshold."
    )

    # --------------------------------------------------------
    # SAVE CALIBRATION MEMORY
    # --------------------------------------------------------

    calibration_memory = {

        "mlai_version":
            VERSION,

        "created_at":
            datetime.now(timezone.utc).isoformat(),

        "market_file":
            MARKET_FILE,

        "stored_candles":
            len(candles),

        "current_window":
            CURRENT_WINDOW,

        "horizons":
            HORIZONS,

        "tested_thresholds":
            THRESHOLDS,

        "results":
            all_results,

        "ranking":
            ranked_results,

        "recommended_threshold":
            recommended_threshold,

        "methodology": {

            "walk_forward":
                True,

            "market_data_modified":
                False,

            "v31_modified":
                False,

            "balanced_accuracy_used":
                True,

            "macro_f1_used":
                True,

            "neutral_f1_used":
                True,

            "cross_horizon_stability_used":
                True,

            "raw_accuracy_not_used_as_only_metric":
                True,
        },
    }

    with open(
        CALIBRATION_FILE,
        "wb"
    ) as f:

        pickle.dump(
            calibration_memory,
            f,
            protocol=pickle.HIGHEST_PROTOCOL
        )

    print()
    print(
        f"PASS: {CALIBRATION_FILE} saved."
    )

    # --------------------------------------------------------
    # REPORT
    # --------------------------------------------------------

    report = []

    report.append(
        "# MLAI v3.2 Historical Prediction Calibration Report"
    )

    report.append("")
    report.append(
        f"Generated: "
        f"{calibration_memory['created_at']}"
    )

    report.append("")

    report.append("## Purpose")
    report.append("")
    report.append(
        "Determine whether the v3.1 outcome "
        "classification threshold is appropriate "
        "for the historical XAU/USD dataset."
    )

    report.append("")
    report.append("## Data Protection")
    report.append("")
    report.append(
        "- `market_data.bin` was read-only."
    )
    report.append(
        "- `mlai_v31.py` was not modified."
    )
    report.append(
        "- `mlai_learning_memory.bin` was not overwritten."
    )
    report.append(
        "- Calibration results were saved separately."
    )

    report.append("")
    report.append("## Dataset")
    report.append("")
    report.append(
        f"- Stored candles: {len(candles)}"
    )
    report.append(
        f"- Current window: {CURRENT_WINDOW}"
    )
    report.append(
        f"- Horizons: {', '.join(map(str, HORIZONS))}"
    )

    report.append("")
    report.append("## Thresholds Tested")
    report.append("")

    for threshold in THRESHOLDS:

        report.append(
            f"- ±{threshold:.2f}%"
        )

    report.append("")
    report.append(
        "## Threshold Ranking"
    )
    report.append("")

    report.append(
        "| Rank | Threshold | Balanced Accuracy | "
        "Macro F1 | Neutral F1 | Stability | Score |"
    )

    report.append(
        "|---:|---:|---:|---:|---:|---:|---:|"
    )

    for rank, item in enumerate(
        ranked_results,
        start=1
    ):

        summary = item["summary"]

        report.append(
            f"| {rank} | "
            f"±{item['threshold']:.2f}% | "
            f"{summary['average_balanced_accuracy']:.2f}% | "
            f"{summary['average_macro_f1']:.2f}% | "
            f"{summary['average_neutral_f1']:.2f}% | "
            f"{summary['cross_horizon_stability']:.2f} | "
            f"{summary['calibration_score']:.2f} |"
        )

    report.append("")
    report.append("## Recommended Candidate")
    report.append("")
    report.append(
        f"**±{recommended_threshold:.2f}%**"
    )

    report.append("")
    report.append(
        "This is a historical calibration candidate, "
        "not a future probability or guaranteed "
        "prediction threshold."
    )

    report.append("")
    report.append("## Detailed Horizon Results")
    report.append("")

    for item in all_results:

        threshold = item["threshold"]

        report.append(
            f"### Threshold ±{threshold:.2f}%"
        )

        report.append("")

        for result in item["horizons"]:

            horizon = result["horizon"]
            metrics = result["metrics"]

            report.append(
                f"#### {horizon}-candle horizon"
            )

            report.append("")

            report.append(
                f"- Records: {metrics['total']}"
            )

            report.append(
                f"- Accuracy: "
                f"{metrics['accuracy']:.2f}%"
            )

            report.append(
                f"- Balanced accuracy: "
                f"{metrics['balanced_accuracy']:.2f}%"
            )

            report.append(
                f"- Macro precision: "
                f"{metrics['macro_precision']:.2f}%"
            )

            report.append(
                f"- Macro recall: "
                f"{metrics['macro_recall']:.2f}%"
            )

            report.append(
                f"- Macro F1: "
                f"{metrics['macro_f1']:.2f}%"
            )

            report.append(
                f"- Directional accuracy: "
                f"{metrics['directional_accuracy']:.2f}%"
            )

            report.append("")

            report.append(
                "Confusion matrix "
                "(rows=prediction, columns=actual):"
            )

            report.append("")

            report.append(
                "| Prediction | Bullish | Neutral | Bearish |"
            )

            report.append(
                "|---|---:|---:|---:|"
            )

            matrix = metrics["confusion_matrix"]

            for label in [
                "bullish",
                "neutral",
                "bearish",
            ]:

                report.append(
                    f"| {label} | "
                    f"{matrix[label]['bullish']} | "
                    f"{matrix[label]['neutral']} | "
                    f"{matrix[label]['bearish']} |"
                )

            report.append("")

            for label in [
                "bullish",
                "neutral",
                "bearish",
            ]:

                cm = metrics[
                    "class_metrics"
                ][label]

                report.append(
                    f"- {label}: "
                    f"precision={cm['precision']:.2f}%, "
                    f"recall={cm['recall']:.2f}%, "
                    f"F1={cm['f1']:.2f}%"
                )

            report.append("")

    report.append("## Calibration Rules")
    report.append("")
    report.append(
        "The calibration process does not select a "
        "threshold using raw accuracy alone."
    )

    report.append("")
    report.append(
        "The calibration score considers:"
    )

    report.append(
        "- Balanced accuracy"
    )

    report.append(
        "- Macro F1"
    )

    report.append(
        "- Neutral-class F1"
    )

    report.append(
        "- Cross-horizon stability"
    )

    report.append("")
    report.append(
        "The purpose is to find a threshold that "
        "produces meaningful and stable classes rather "
        "than simply maximizing one metric."
    )

    report.append("")
    report.append("## Important")
    report.append("")
    report.append(
        "Historical classification performance is not "
        "future prediction probability."
    )

    report.append("")
    report.append(
        "The recommended threshold must be validated "
        "before being adopted by a future MLAI version."
    )

    with open(
        REPORT_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(
            "\n".join(report)
        )

    print()
    print(
        f"PASS: {REPORT_FILE} saved."
    )

    # --------------------------------------------------------
    # UPDATE PROJECT STATUS
    # --------------------------------------------------------

    existing_status = ""

    if os.path.exists(STATUS_FILE):

        with open(
            STATUS_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            existing_status = f.read()

    status_marker = (
        "# MLAI v3.2 CALIBRATION CHECKPOINT"
    )

    calibration_section = f"""

---

{status_marker}

## Calibration Engine

MLAI v3.2 independently tested the historical outcome-classification thresholds using the existing `market_data.bin`.

### Data Protection

- `market_data.bin` was not modified.
- `mlai_v31.py` was not modified.
- `mlai_learning_memory.bin` was not overwritten.
- Calibration memory was saved separately.
- Calibration report was saved separately.
- Walk-forward methodology was preserved.

### Thresholds Tested

{", ".join(f"±{x:.2f}%" for x in THRESHOLDS)}

### Current v3.1 Threshold

- ±0.02%

### Best Historical Calibration Candidate

- ±{recommended_threshold:.2f}%

### Best Candidate Score

- {best_result["summary"]["calibration_score"]:.2f}

### Best Candidate Metrics

- Average balanced accuracy: {best_result["summary"]["average_balanced_accuracy"]:.2f}%
- Average macro F1: {best_result["summary"]["average_macro_f1"]:.2f}%
- Average neutral F1: {best_result["summary"]["average_neutral_f1"]:.2f}%
- Cross-horizon stability: {best_result["summary"]["cross_horizon_stability"]:.2f}
- Average directional accuracy: {best_result["summary"]["average_directional_accuracy"]:.2f}%

### Calibration Interpretation

The threshold shown above is a historical calibration candidate only.

It is NOT a future prediction probability.

It is NOT a guaranteed optimal threshold.

It must be validated on unseen historical segments before adoption by a future MLAI version.

### v3.2 Files

- `mlai_v32.py`
- `mlai_v32_calibration.bin`
- `MLAI_V32_CALIBRATION_REPORT.md`

### Next Decision

Do NOT modify MLAI v3.1 based only on this result.

First inspect the calibration report and determine whether the candidate threshold is stable across 4-, 8- and 16-candle horizons.

Updated: {datetime.now(timezone.utc).isoformat()}
"""

    if status_marker in existing_status:

        existing_status = (
            existing_status
            .split(
                "---\n\n"
                + status_marker
            )[0]
            .rstrip()
        )

    new_status = (
        existing_status.rstrip()
        + calibration_section
        + "\n"
    )

    with open(
        STATUS_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(new_status)

    print()
    print(
        f"PASS: {STATUS_FILE} updated."
    )

    # --------------------------------------------------------
    # FINAL
    # --------------------------------------------------------

    header(
        "MLAI v3.2 CALIBRATION COMPLETED"
    )

    print(
        f"Recommended historical candidate : "
        f"±{recommended_threshold:.2f}%"
    )

    print(
        f"Calibration score                : "
        f"{best_result['summary']['calibration_score']:.2f}"
    )

    print()
    print(
        "Files created:"
    )

    print(
        f"  - {CALIBRATION_FILE}"
    )

    print(
        f"  - {REPORT_FILE}"
    )

    print()
    print(
        "PASS: v3.1 remains unchanged."
    )

    print(
        "PASS: market_data.bin remains unchanged."
    )

    print()
    print(
        "NEXT STEP:"
    )

    print(
        "Inspect the calibration report before "
        "changing any v3.1 classification logic."
    )


except FileNotFoundError as error:

    print()
    print("=" * 78)
    print("ERROR: Required file was not found.")
    print("=" * 78)
    print(f"DETAIL: {error}")


except (
    pickle.UnpicklingError,
    EOFError
) as error:

    print()
    print("=" * 78)
    print(
        "ERROR: market_data.bin could not be "
        "read as a valid pickle object."
    )
    print("=" * 78)
    print(f"DETAIL: {error}")


except Exception as error:

    print()
    print("=" * 78)
    print("ERROR: MLAI v3.2 calibration failed.")
    print("=" * 78)
    print(
        f"{type(error).__name__}: {error}"
    )
    print()
    print(
        "The original market_data.bin has NOT "
        "been modified."
    )