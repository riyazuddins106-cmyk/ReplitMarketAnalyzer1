import os
import pickle
import math
from collections import Counter
from datetime import datetime, timezone


# ============================================================
# MLAI v3.2.1
# FINE-GRAINED HISTORICAL THRESHOLD CALIBRATION ENGINE
# ============================================================

VERSION = "MLAI v3.2.1 FINE-GRAINED HISTORICAL THRESHOLD CALIBRATION"

MARKET_FILE = "market_data.bin"

CALIBRATION_FILE = "mlai_v321_calibration.bin"

REPORT_FILE = "MLAI_V321_CALIBRATION_REPORT.md"

STATUS_FILE = "MLAI_PROJECT_STATUS.md"

CURRENT_WINDOW = 60

HORIZONS = [4, 8, 16]

# ------------------------------------------------------------
# Fine-grained threshold range.
#
# v3.2 identified ±0.15% and ±0.20% as strong candidates.
# v3.2.1 examines the area between and around them.
# ------------------------------------------------------------

THRESHOLDS = [
    0.12,
    0.13,
    0.14,
    0.15,
    0.16,
    0.17,
    0.18,
    0.19,
    0.20,
    0.21,
    0.22,
    0.23,
    0.24,
    0.25,
]

MIN_CLASS_PERCENT = 5.0


# ============================================================
# OUTPUT
# ============================================================

def print_header(text):

    print()
    print("=" * 78)
    print(text)
    print("=" * 78)


def print_section(text):

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

    with open(
        MARKET_FILE,
        "rb"
    ) as f:

        data = pickle.load(f)

    if isinstance(data, list):

        source = data

    elif isinstance(data, dict):

        source = None

        possible_keys = [
            "candles",
            "data",
            "records",
            "market_data",
            "ohlcv",
        ]

        for key in possible_keys:

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
            "a supported candle list."
        )

    candles = []

    for raw in source:

        candle = normalize_candle(raw)

        if candle is not None:

            candles.append(candle)

    if not candles:

        raise ValueError(
            "No valid OHLC candles were found "
            "in market_data.bin."
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


# ============================================================
# OUTCOME CLASSIFICATION
# ============================================================

def classify_outcome(
    movement,
    threshold
):

    if movement > threshold:

        return "bullish"

    if movement < -threshold:

        return "bearish"

    return "neutral"


# ============================================================
# CONFUSION MATRIX
# ============================================================

def build_confusion_matrix(
    predictions,
    actuals
):

    labels = [
        "bullish",
        "bearish",
        "neutral",
    ]

    matrix = {
        predicted: {
            actual: 0
            for actual in labels
        }
        for predicted in labels
    }

    for prediction, actual in zip(
        predictions,
        actuals
    ):

        if prediction in labels and actual in labels:

            matrix[prediction][actual] += 1

    return matrix


# ============================================================
# METRICS
# ============================================================

def calculate_metrics(
    predictions,
    actuals
):

    labels = [
        "bullish",
        "bearish",
        "neutral",
    ]

    total = len(actuals)

    if total == 0:

        return {

            "accuracy": 0.0,

            "balanced_accuracy": 0.0,

            "macro_f1": 0.0,

            "neutral_f1": 0.0,

            "precision": {
                label: 0.0
                for label in labels
            },

            "recall": {
                label: 0.0
                for label in labels
            },

            "f1": {
                label: 0.0
                for label in labels
            },

            "distribution": {
                label: 0.0
                for label in labels
            },

            "confusion_matrix":
                build_confusion_matrix(
                    predictions,
                    actuals
                ),
        }

    matrix = build_confusion_matrix(
        predictions,
        actuals
    )

    correct = sum(
        1
        for prediction, actual
        in zip(predictions, actuals)
        if prediction == actual
    )

    accuracy = (
        correct
        / total
        * 100.0
    )

    precision = {}
    recall = {}
    f1 = {}

    for label in labels:

        true_positive = matrix[label][label]

        predicted_positive = sum(
            matrix[label][actual]
            for actual in labels
        )

        actual_positive = sum(
            matrix[predicted][label]
            for predicted in labels
        )

        if predicted_positive > 0:

            p = (
                true_positive
                / predicted_positive
                * 100.0
            )

        else:

            p = 0.0

        if actual_positive > 0:

            r = (
                true_positive
                / actual_positive
                * 100.0
            )

        else:

            r = 0.0

        if (
            p + r
        ) > 0:

            f = (
                2.0
                * p
                * r
                / (p + r)
            )

        else:

            f = 0.0

        precision[label] = p
        recall[label] = r
        f1[label] = f

    balanced_accuracy = average([
        recall[label]
        for label in labels
    ])

    macro_f1 = average([
        f1[label]
        for label in labels
    ])

    distribution_counts = Counter(
        actuals
    )

    distribution = {}

    for label in labels:

        distribution[label] = (
            distribution_counts[label]
            / total
            * 100.0
        )

    return {

        "accuracy":
            accuracy,

        "balanced_accuracy":
            balanced_accuracy,

        "macro_f1":
            macro_f1,

        "neutral_f1":
            f1["neutral"],

        "precision":
            precision,

        "recall":
            recall,

        "f1":
            f1,

        "distribution":
            distribution,

        "confusion_matrix":
            matrix,
    }


# ============================================================
# AVERAGE
# ============================================================

def average(values):

    if not values:
        return 0.0

    return sum(values) / len(values)


# ============================================================
# HISTORICAL PREDICTION
#
# IMPORTANT:
# v3.2.1 is calibrating the OUTCOME threshold.
#
# It intentionally does not modify or depend on v3.1
# historical-learning memory.
#
# We use the same direct context logic as v3.1 so the
# comparison remains consistent.
# ============================================================

def analyze_context(candles):

    closes = [
        candle["close"]
        for candle in candles
    ]

    latest = closes[-1]

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

        elif (
            recent_volatility
            > older_volatility * 1.15
        ):

            volatility = "expanding"

        elif (
            recent_volatility
            < older_volatility * 0.85
        ):

            volatility = "contracting"

        else:

            volatility = "stable"

    else:

        volatility = "stable"

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

    if (
        upper_rejections
        > lower_rejections + 2
    ):

        rejection = "upper_rejection_dominant"

    elif (
        lower_rejections
        > upper_rejections + 2
    ):

        rejection = "lower_rejection_dominant"

    else:

        rejection = "balanced_rejection"

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

    total_score = (
        bullish_score
        + bearish_score
        + neutral_score
    )

    if total_score <= 0:

        bullish = 33.3333
        bearish = 33.3333
        neutral = 33.3334

    else:

        bullish = (
            bullish_score
            / total_score
            * 100.0
        )

        bearish = (
            bearish_score
            / total_score
            * 100.0
        )

        neutral = (
            neutral_score
            / total_score
            * 100.0
        )

    # Same v3.1 directional protection.

    directional_separation = abs(
        bullish - bearish
    )

    strongest_direction = max(
        bullish,
        bearish
    )

    neutral_gap = (
        strongest_direction
        - neutral
    )

    if directional_separation < 5.0:

        prediction = "neutral"

    elif neutral_gap < 5.0:

        prediction = "neutral"

    elif bullish > bearish:

        prediction = "bullish"

    else:

        prediction = "bearish"

    return prediction


# ============================================================
# BUILD HISTORICAL PREDICTIONS
# ============================================================

def build_predictions(candles):

    results = {}

    total_candles = len(candles)

    training_end = (
        total_candles
        - CURRENT_WINDOW
    )

    max_horizon = max(HORIZONS)

    last_decision_index = (
        training_end
        - max_horizon
        + 1
    )

    for threshold in THRESHOLDS:

        threshold_results = {}

        for horizon in HORIZONS:

            predictions = []

            actuals = []

            for decision_index in range(
                CURRENT_WINDOW,
                last_decision_index
            ):

                context_candles = candles[
                    decision_index - CURRENT_WINDOW:
                    decision_index
                ]

                prediction = analyze_context(
                    context_candles
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

                predictions.append(
                    prediction
                )

                actuals.append(
                    actual
                )

            metrics = calculate_metrics(
                predictions,
                actuals
            )

            threshold_results[horizon] = {

                "predictions":
                    predictions,

                "actuals":
                    actuals,

                "metrics":
                    metrics,
            }

        results[threshold] = threshold_results

    return results


# ============================================================
# CROSS-HORIZON STABILITY
# ============================================================

def calculate_stability(
    horizon_metrics
):

    balanced_values = [
        horizon_metrics[horizon][
            "balanced_accuracy"
        ]
        for horizon in HORIZONS
    ]

    if not balanced_values:

        return 0.0

    mean_value = average(
        balanced_values
    )

    deviations = [
        abs(
            value - mean_value
        )
        for value in balanced_values
    ]

    average_deviation = average(
        deviations
    )

    stability = max(
        0.0,
        100.0 - (
            average_deviation * 5.0
        )
    )

    return stability


# ============================================================
# CALIBRATION SCORE
#
# The score balances:
#
# - Balanced accuracy
# - Macro-F1
# - Neutral-F1
# - Cross-horizon stability
#
# It does NOT use ordinary accuracy as the primary metric
# because ordinary accuracy can reward class imbalance.
# ============================================================

def calculate_calibration_score(
    average_balanced,
    average_macro_f1,
    average_neutral_f1,
    stability,
    class_distribution
):

    # Penalize extremely dominant classes.

    class_values = list(
        class_distribution.values()
    )

    class_balance_penalty = 0.0

    if class_values:

        for value in class_values:

            if value < MIN_CLASS_PERCENT:

                class_balance_penalty += (
                    MIN_CLASS_PERCENT - value
                )

    score = (

        average_balanced * 0.30

        + average_macro_f1 * 0.30

        + average_neutral_f1 * 0.20

        + stability * 0.20

        - class_balance_penalty * 0.50
    )

    return score


# ============================================================
# REPORT
# ============================================================

def create_report(
    candles,
    results,
    ranking,
    best_threshold
):

    generated_at = (
        datetime.now(timezone.utc)
        .isoformat()
    )

    best = ranking[0]

    lines = []

    lines.append(
        "# MLAI v3.2.1 Fine-Grained "
        "Historical Threshold Calibration Report"
    )

    lines.append("")

    lines.append(
        f"Generated: {generated_at}"
    )

    lines.append("")

    lines.append(
        "## Purpose"
    )

    lines.append("")

    lines.append(
        "This calibration independently examines "
        "fine-grained historical outcome thresholds "
        "after MLAI v3.2 identified ±0.20% as a "
        "candidate threshold."
    )

    lines.append("")

    lines.append(
        "## Protection"
    )

    lines.append("")

    lines.append(
        "- market_data.bin was read only."
    )

    lines.append(
        "- market_data.bin was not modified."
    )

    lines.append(
        "- mlai_v31.py was not modified."
    )

    lines.append(
        "- mlai_learning_memory.bin was not modified."
    )

    lines.append(
        "- Current 60-candle window was excluded "
        "from historical training."
    )

    lines.append(
        "- Future candles were used only for "
        "historical outcome resolution."
    )

    lines.append("")

    lines.append(
        "## Dataset"
    )

    lines.append("")

    lines.append(
        f"- Stored candles: {len(candles)}"
    )

    lines.append(
        f"- Current window: {CURRENT_WINDOW}"
    )

    lines.append(
        f"- Horizons: {HORIZONS}"
    )

    lines.append("")

    lines.append(
        "## Threshold Ranking"
    )

    lines.append("")

    lines.append(
        "| Rank | Threshold | Balanced | Macro-F1 | "
        "Neutral-F1 | Stability | Score |"
    )

    lines.append(
        "|---:|---:|---:|---:|---:|---:|---:|"
    )

    for index, item in enumerate(
        ranking,
        start=1
    ):

        lines.append(
            f"| {index} | ±{item['threshold']:.2f}% | "
            f"{item['average_balanced']:.2f}% | "
            f"{item['average_macro_f1']:.2f}% | "
            f"{item['average_neutral_f1']:.2f}% | "
            f"{item['stability']:.2f} | "
            f"{item['score']:.2f} |"
        )

    lines.append("")

    lines.append(
        "## Recommended Candidate"
    )

    lines.append("")

    lines.append(
        f"**±{best_threshold:.2f}%**"
    )

    lines.append("")

    lines.append(
        "This is a historical calibration candidate "
        "only. It is not a guaranteed future "
        "prediction threshold."
    )

    lines.append("")

    lines.append(
        "## Detailed Results"
    )

    lines.append("")

    for item in ranking:

        threshold = item["threshold"]

        lines.append(
            f"### Threshold ±{threshold:.2f}%"
        )

        lines.append("")

        for horizon in HORIZONS:

            metrics = results[
                threshold
            ][horizon]["metrics"]

            distribution = (
                metrics["distribution"]
            )

            lines.append(
                f"#### {horizon} candles"
            )

            lines.append("")

            lines.append(
                f"- Records: "
                f"{len(results[threshold][horizon]['actuals'])}"
            )

            lines.append(
                f"- Accuracy: "
                f"{metrics['accuracy']:.2f}%"
            )

            lines.append(
                f"- Balanced accuracy: "
                f"{metrics['balanced_accuracy']:.2f}%"
            )

            lines.append(
                f"- Macro-F1: "
                f"{metrics['macro_f1']:.2f}%"
            )

            lines.append(
                f"- Neutral-F1: "
                f"{metrics['neutral_f1']:.2f}%"
            )

            lines.append(
                f"- Actual bullish: "
                f"{distribution['bullish']:.2f}%"
            )

            lines.append(
                f"- Actual bearish: "
                f"{distribution['bearish']:.2f}%"
            )

            lines.append(
                f"- Actual neutral: "
                f"{distribution['neutral']:.2f}%"
            )

            lines.append("")

        lines.append(
            "#### Confusion Matrix — 4 candles"
        )

        lines.append("")

        matrix = results[
            threshold
        ][4]["metrics"]["confusion_matrix"]

        lines.append(
            "| Predicted / Actual | Bullish | "
            "Bearish | Neutral |"
        )

        lines.append(
            "|---|---:|---:|---:|"
        )

        for predicted in [
            "bullish",
            "bearish",
            "neutral",
        ]:

            lines.append(
                f"| {predicted} | "
                f"{matrix[predicted]['bullish']} | "
                f"{matrix[predicted]['bearish']} | "
                f"{matrix[predicted]['neutral']} |"
            )

        lines.append("")

    lines.append(
        "## Interpretation Rules"
    )

    lines.append("")

    lines.append(
        "The recommended threshold must not be "
        "interpreted as future prediction probability."
    )

    lines.append("")

    lines.append(
        "Ordinary accuracy is not sufficient for "
        "threshold selection because class imbalance "
        "can make accuracy misleading."
    )

    lines.append("")

    lines.append(
        "Balanced accuracy and Macro-F1 are used "
        "to evaluate all three classes."
    )

    lines.append("")

    lines.append(
        "Neutral-F1 is explicitly monitored because "
        "v3.1 showed very weak neutral historical "
        "accuracy at ±0.02%."
    )

    lines.append("")

    lines.append(
        "Cross-horizon stability is used to avoid "
        "selecting a threshold that works only "
        "for one horizon."
    )

    lines.append("")

    lines.append(
        "## Decision"
    )

    lines.append("")

    lines.append(
        f"The current v3.2.1 calibration ranking "
        f"places ±{best_threshold:.2f}% first."
    )

    lines.append("")

    lines.append(
        "This result must be reviewed before any "
        "outcome-classification logic is changed "
        "in a future MLAI engine version."
    )

    lines.append("")

    return "\n".join(lines)


# ============================================================
# MAIN
# ============================================================

try:

    print_header(
        "MLAI v3.2.1 "
        "FINE-GRAINED HISTORICAL THRESHOLD CALIBRATION"
    )

    print()

    print(
        "Purpose: refine the historical outcome "
        "classification threshold."
    )

    print()

    print(
        f"Market file       : {MARKET_FILE}"
    )

    print(
        f"Current window    : {CURRENT_WINDOW}"
    )

    print(
        f"Horizons          : {HORIZONS}"
    )

    print(
        "Thresholds        : "
        + ", ".join(
            f"±{x:.2f}%"
            for x in THRESHOLDS
        )
    )

    print()

    candles = load_market_data()

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
            "Not enough candles for calibration."
        )

    print()

    print(
        "PASS: Original market data "
        "will NOT be modified."
    )

    print(
        "PASS: MLAI v3.1 will NOT be modified."
    )

    print(
        "PASS: Existing MLAI learning memory "
        "will NOT be modified."
    )

    print()

    print(
        "Building walk-forward predictions..."
    )

    results = build_predictions(
        candles
    )

    print(
        "PASS: Walk-forward predictions generated."
    )

    ranking = []

    for threshold in THRESHOLDS:

        print_section(
            f"TESTING FINE THRESHOLD ±{threshold:.2f}%"
        )

        horizon_metrics = {}

        all_actuals = []

        for horizon in HORIZONS:

            metrics = results[
                threshold
            ][horizon]["metrics"]

            horizon_metrics[horizon] = metrics

            all_actuals.extend(
                results[
                    threshold
                ][horizon]["actuals"]
            )

            print(
                f"{horizon:2d} candles -> "
                f"records="
                f"{len(results[threshold][horizon]['actuals'])} | "
                f"accuracy="
                f"{metrics['accuracy']:.2f}% | "
                f"balanced="
                f"{metrics['balanced_accuracy']:.2f}% | "
                f"macro-F1="
                f"{metrics['macro_f1']:.2f}% | "
                f"neutral-F1="
                f"{metrics['neutral_f1']:.2f}%"
            )

        average_balanced = average([
            horizon_metrics[horizon][
                "balanced_accuracy"
            ]
            for horizon in HORIZONS
        ])

        average_macro_f1 = average([
            horizon_metrics[horizon][
                "macro_f1"
            ]
            for horizon in HORIZONS
        ])

        average_neutral_f1 = average([
            horizon_metrics[horizon][
                "neutral_f1"
            ]
            for horizon in HORIZONS
        ])

        stability = calculate_stability(
            horizon_metrics
        )

        distribution_counts = Counter(
            all_actuals
        )

        total_actuals = len(
            all_actuals
        )

        if total_actuals > 0:

            class_distribution = {

                "bullish":
                    distribution_counts["bullish"]
                    / total_actuals
                    * 100.0,

                "bearish":
                    distribution_counts["bearish"]
                    / total_actuals
                    * 100.0,

                "neutral":
                    distribution_counts["neutral"]
                    / total_actuals
                    * 100.0,
            }

        else:

            class_distribution = {

                "bullish": 0.0,

                "bearish": 0.0,

                "neutral": 0.0,
            }

        score = calculate_calibration_score(
            average_balanced,
            average_macro_f1,
            average_neutral_f1,
            stability,
            class_distribution
        )

        print()

        print(
            f"Average balanced accuracy : "
            f"{average_balanced:.2f}%"
        )

        print(
            f"Average Macro-F1          : "
            f"{average_macro_f1:.2f}%"
        )

        print(
            f"Average Neutral-F1        : "
            f"{average_neutral_f1:.2f}%"
        )

        print(
            f"Cross-horizon stability   : "
            f"{stability:.2f}"
        )

        print(
            f"Class distribution        : "
            f"B={class_distribution['bullish']:.1f}% | "
            f"S={class_distribution['bearish']:.1f}% | "
            f"N={class_distribution['neutral']:.1f}%"
        )

        print(
            f"Calibration score         : "
            f"{score:.2f}"
        )

        ranking.append({

            "threshold":
                threshold,

            "average_balanced":
                average_balanced,

            "average_macro_f1":
                average_macro_f1,

            "average_neutral_f1":
                average_neutral_f1,

            "stability":
                stability,

            "score":
                score,

            "class_distribution":
                class_distribution,
        })

    ranking.sort(
        key=lambda item: (
            item["score"],
            item["average_balanced"],
            item["average_macro_f1"],
            item["average_neutral_f1"],
            item["stability"],
        ),
        reverse=True,
    )

    best_threshold = ranking[0][
        "threshold"
    ]

    # ========================================================
    # RANKING
    # ========================================================

    print_header(
        "FINE-GRAINED THRESHOLD CALIBRATION RANKING"
    )

    print(
        f"{'Rank':>4} | "
        f"{'Threshold':>10} | "
        f"{'Balanced':>9} | "
        f"{'Macro-F1':>9} | "
        f"{'Neutral-F1':>11} | "
        f"{'Stability':>9} | "
        f"{'Score':>8}"
    )

    print("-" * 78)

    for index, item in enumerate(
        ranking,
        start=1
    ):

        print(
            f"{index:02d}. | "
            f"±{item['threshold']:.2f}%"
            f"{'':>5} | "
            f"{item['average_balanced']:>8.2f}% | "
            f"{item['average_macro_f1']:>8.2f}% | "
            f"{item['average_neutral_f1']:>10.2f}% | "
            f"{item['stability']:>8.2f} | "
            f"{item['score']:>7.2f}"
        )

    # ========================================================
    # RESULT
    # ========================================================

    print_section(
        "V3.2.1 CALIBRATION RESULT"
    )

    print(
        "Previous v3.1 threshold : ±0.02%"
    )

    print(
        f"Best fine-grained candidate : "
        f"±{best_threshold:.2f}%"
    )

    print(
        f"Calibration score            : "
        f"{ranking[0]['score']:.2f}"
    )

    print()

    print(
        "RESULT: The best candidate is based on "
        "combined historical calibration metrics."
    )

    print(
        "IMPORTANT: This is NOT a guaranteed "
        "future prediction threshold."
    )

    # ========================================================
    # SAVE CALIBRATION MEMORY
    # ========================================================

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

        "thresholds_tested":
            THRESHOLDS,

        "previous_v31_threshold":
            0.02,

        "best_threshold":
            best_threshold,

        "ranking":
            ranking,

        "detailed_results":
            results,

        "protection": {

            "market_data_modified":
                False,

            "v31_modified":
                False,

            "learning_memory_modified":
                False,

            "current_window_excluded":
                True,

            "future_only_for_outcome_resolution":
                True,
        },

        "methodology": {

            "balanced_accuracy":
                True,

            "macro_f1":
                True,

            "neutral_f1":
                True,

            "cross_horizon_stability":
                True,

            "class_distribution_check":
                True,

            "fine_grained_threshold_search":
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

    # ========================================================
    # SAVE REPORT
    # ========================================================

    report = create_report(
        candles,
        results,
        ranking,
        best_threshold
    )

    with open(
        REPORT_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(report)

    print(
        f"PASS: {REPORT_FILE} saved."
    )

    # ========================================================
    # UPDATE PROJECT STATUS
    # ========================================================

    status_text = f"""# MLAI Project Status

## Current Version

MLAI v3.2.1 FINE-GRAINED HISTORICAL THRESHOLD CALIBRATION

## Current Checkpoint

v3.1 historical-learning architecture remains unchanged.

v3.2 broad historical threshold calibration identified ±0.20% as the best broad candidate.

v3.2.1 performed a fine-grained search from ±0.12% through ±0.25%.

## Dataset

- Market file: market_data.bin
- Stored candles: {len(candles)}
- Current window: {CURRENT_WINDOW}
- Horizons: {HORIZONS}

## v3.2.1 Result

- Previous v3.1 threshold: ±0.02%
- Best fine-grained candidate: ±{best_threshold:.2f}%
- Calibration score: {ranking[0]["score"]:.2f}
- Average balanced accuracy: {ranking[0]["average_balanced"]:.2f}%
- Average Macro-F1: {ranking[0]["average_macro_f1"]:.2f}%
- Average Neutral-F1: {ranking[0]["average_neutral_f1"]:.2f}%
- Cross-horizon stability: {ranking[0]["stability"]:.2f}

## Top Candidates

"""

    for index, item in enumerate(
        ranking[:5],
        start=1
    ):

        status_text += (
            f"{index}. ±{item['threshold']:.2f}% "
            f"| score={item['score']:.2f} "
            f"| balanced={item['average_balanced']:.2f}% "
            f"| macro-F1={item['average_macro_f1']:.2f}% "
            f"| neutral-F1={item['average_neutral_f1']:.2f}% "
            f"| stability={item['stability']:.2f}\\n"
        )

    status_text += f"""

## Protection

- market_data.bin was not modified.
- mlai_v31.py was not modified.
- mlai_learning_memory.bin was not modified.
- Current 60-candle window remains excluded.
- Future candles are used only for historical outcome resolution.
- Previous MLAI versions remain preserved.

## Important Interpretation

The v3.2.1 result is a historical calibration candidate.

It is NOT a future prediction probability.

It is NOT a guaranteed trading threshold.

It does NOT justify an automatic BUY/SELL signal.

The selected threshold must be reviewed before changing outcome classification in a future MLAI engine version.

## Files Created

- mlai_v321.py
- mlai_v321_calibration.bin
- MLAI_V321_CALIBRATION_REPORT.md

## Next Step

Review the v3.2.1 calibration results.

Do NOT modify MLAI v3.1 until the threshold is explicitly approved based on the calibration evidence.

## Last Updated

{datetime.now(timezone.utc).isoformat()}
"""

    with open(
        STATUS_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(status_text)

    print(
        f"PASS: {STATUS_FILE} updated."
    )

    print_header(
        "MLAI v3.2.1 CALIBRATION COMPLETED"
    )

    print(
        f"Recommended fine-grained candidate : "
        f"±{best_threshold:.2f}%"
    )

    print(
        f"Calibration score                  : "
        f"{ranking[0]['score']:.2f}"
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

    print(
        f"  - {STATUS_FILE}"
    )

    print()

    print(
        "PASS: v3.1 remains unchanged."
    )

    print(
        "PASS: market_data.bin remains unchanged."
    )

    print(
        "PASS: Existing learning memory remains unchanged."
    )

    print()

    print(
        "NEXT STEP:"
    )

    print(
        "Review the complete v3.2.1 output and "
        "calibration report before changing any "
        "outcome-classification logic."
    )


except FileNotFoundError as error:

    print()

    print(
        "ERROR: Required file was not found."
    )

    print(
        f"DETAIL: {error}"
    )


except (
    pickle.UnpicklingError,
    EOFError
) as error:

    print()

    print(
        "ERROR: market_data.bin could not be "
        "read as a valid pickle object."
    )

    print(
        f"DETAIL: {error}"
    )


except Exception as error:

    print()

    print("=" * 78)

    print(
        "ERROR: MLAI v3.2.1 execution failed."
    )

    print("=" * 78)

    print(
        f"{type(error).__name__}: {error}"
    )

    print()

    print(
        "The original market_data.bin has NOT "
        "been modified."
    )