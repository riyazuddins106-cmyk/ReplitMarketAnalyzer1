import os
import pickle
import json
from statistics import mean


# ============================================================
# MLAI v3.2.3
# CHRONOLOGICAL OUT-OF-SAMPLE THRESHOLD VALIDATION ENGINE
# ============================================================
#
# Purpose:
#   Determine whether candidate outcome thresholds remain useful
#   on a completely later/unseen historical validation period.
#
# IMPORTANT:
#   - Does NOT modify market_data.bin
#   - Does NOT modify mlai_v31.py
#   - Does NOT modify existing learning memory
#   - Does NOT train on the validation period
#
# Candidates:
#   ±0.15%, ±0.18%, ±0.20%, ±0.24%
#
# Horizons:
#   4, 8, 16 candles
#
# ============================================================


MARKET_FILE = "market_data.bin"

OUTPUT_BIN = "mlai_v323_oos_validation.bin"
OUTPUT_REPORT = "MLAI_V323_OOS_VALIDATION_REPORT.md"
STATUS_FILE = "MLAI_PROJECT_STATUS.md"

CURRENT_WINDOW = 60
HORIZONS = [4, 8, 16]

THRESHOLDS = [0.0015, 0.0018, 0.0020, 0.0024]

# Chronological split.
#
# The earlier portion is the calibration/reference period.
# The later portion is the completely unseen validation period.
#
# IMPORTANT:
# We do not use the validation period to choose the threshold.
#
VALIDATION_RATIO = 0.30

MIN_CLASS_COUNT = 5


# ============================================================
# UTILITY
# ============================================================

def pct(value):
    return f"{value * 100:.2f}%"


def safe_mean(values):
    if not values:
        return 0.0
    return mean(values)


def clamp(value, low=0.0, high=1.0):
    return max(low, min(high, value))


# ============================================================
# LOAD MARKET DATA
# ============================================================

def load_market_data():
    if not os.path.exists(MARKET_FILE):
        raise FileNotFoundError(
            f"{MARKET_FILE} was not found in the current directory."
        )

    with open(MARKET_FILE, "rb") as f:
        data = pickle.load(f)

    return data


# ============================================================
# EXTRACT CLOSE PRICES
# ============================================================

def extract_close_prices(data):
    candles = []

    if isinstance(data, list):
        candles = data

    elif isinstance(data, dict):
        possible_keys = [
            "candles",
            "data",
            "market_data",
            "records",
            "prices",
        ]

        for key in possible_keys:
            if key in data and isinstance(data[key], list):
                candles = data[key]
                break

    if not candles:
        raise ValueError(
            "Could not find candle list inside market_data.bin"
        )

    closes = []

    for candle in candles:

        if not isinstance(candle, dict):
            continue

        close = None

        for key in ["close", "Close", "c"]:
            if key in candle:
                close = candle[key]
                break

        if close is None:
            continue

        try:
            closes.append(float(close))
        except (ValueError, TypeError):
            continue

    if len(closes) < CURRENT_WINDOW + max(HORIZONS) + 50:
        raise ValueError(
            f"Not enough valid close prices. Found {len(closes)}."
        )

    return closes


# ============================================================
# OUTCOME CLASSIFICATION
# ============================================================

def classify_outcome(start_price, future_price, threshold):
    if start_price <= 0:
        return "N"

    change = (future_price - start_price) / start_price

    if change >= threshold:
        return "B"

    if change <= -threshold:
        return "S"

    return "N"


# ============================================================
# PREDICTION MODEL
# ============================================================
#
# This validation engine intentionally uses a simple,
# deterministic historical directional baseline.
#
# The purpose is NOT to replace v3.1.
#
# The purpose is to test whether threshold candidates
# remain meaningful on unseen historical data.
#
# Prediction:
#
#   recent movement over the current window
#
# Positive -> BUY
# Negative -> SELL
#
# Very weak movement -> NEUTRAL
#
# The threshold itself is NOT used to create the prediction.
# It is only used to classify the future outcome.
#
# This separation is important because otherwise the threshold
# could artificially influence both prediction and evaluation.
# ============================================================

def predict_direction(closes, index):

    start = index - CURRENT_WINDOW + 1

    if start < 0:
        return None

    current = closes[index]
    previous = closes[start]

    if previous <= 0:
        return None

    movement = (current - previous) / previous

    if movement > 0:
        return "B"

    if movement < 0:
        return "S"

    return "N"


# ============================================================
# BUILD WALK-FORWARD DATASET
# ============================================================

def build_dataset(closes, validation_start):
    dataset = []

    max_horizon = max(HORIZONS)

    first_index = CURRENT_WINDOW - 1
    last_index = len(closes) - max_horizon - 1

    for index in range(first_index, last_index + 1):

        prediction = predict_direction(closes, index)

        if prediction is None:
            continue

        # Determine whether this observation belongs to
        # the completely unseen validation period.
        #
        # The validation split is based on the prediction time,
        # not on the future outcome time.
        is_validation = index >= validation_start

        for horizon in HORIZONS:

            future_index = index + horizon

            if future_index >= len(closes):
                continue

            start_price = closes[index]
            future_price = closes[future_index]

            dataset.append(
                {
                    "index": index,
                    "horizon": horizon,
                    "prediction": prediction,
                    "start_price": start_price,
                    "future_price": future_price,
                    "validation": is_validation,
                }
            )

    return dataset


# ============================================================
# CONFUSION MATRIX
# ============================================================

def confusion_matrix(records):

    labels = ["B", "S", "N"]

    matrix = {
        actual: {
            predicted: 0
            for predicted in labels
        }
        for actual in labels
    }

    for r in records:
        actual = r["actual"]
        predicted = r["prediction"]

        matrix[actual][predicted] += 1

    return matrix


# ============================================================
# METRICS
# ============================================================

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
            "neutral_rate": 0.0,
            "buy_actual_rate": 0.0,
            "sell_actual_rate": 0.0,
            "neutral_actual_rate": 0.0,
        }

    labels = ["B", "S", "N"]

    matrix = confusion_matrix(records)

    total = len(records)

    correct = sum(
        matrix[label][label]
        for label in labels
    )

    accuracy = correct / total

    recalls = []
    f1s = []

    for label in labels:

        actual_count = sum(
            matrix[label][pred]
            for pred in labels
        )

        predicted_count = sum(
            matrix[actual][label]
            for actual in labels
        )

        tp = matrix[label][label]

        recall = (
            tp / actual_count
            if actual_count > 0
            else 0.0
        )

        precision = (
            tp / predicted_count
            if predicted_count > 0
            else 0.0
        )

        if precision + recall > 0:
            f1 = (
                2 * precision * recall
                / (precision + recall)
            )
        else:
            f1 = 0.0

        recalls.append(recall)
        f1s.append(f1)

    balanced_accuracy = safe_mean(recalls)
    macro_f1 = safe_mean(f1s)

    # Directional-only metrics.
    directional_records = [
        r for r in records
        if r["actual"] in ("B", "S")
    ]

    directional_correct = [
        r for r in directional_records
        if r["prediction"] == r["actual"]
    ]

    directional_accuracy = (
        len(directional_correct)
        / len(directional_records)
        if directional_records
        else 0.0
    )

    # BUY precision
    buy_tp = matrix["B"]["B"]

    buy_predicted = (
        matrix["B"]["B"]
        + matrix["S"]["B"]
        + matrix["N"]["B"]
    )

    buy_precision = (
        buy_tp / buy_predicted
        if buy_predicted > 0
        else 0.0
    )

    # SELL precision
    sell_tp = matrix["S"]["S"]

    sell_predicted = (
        matrix["B"]["S"]
        + matrix["S"]["S"]
        + matrix["N"]["S"]
    )

    sell_precision = (
        sell_tp / sell_predicted
        if sell_predicted > 0
        else 0.0
    )

    # Directional F1
    directional_f1_values = []

    for label in ["B", "S"]:

        tp = matrix[label][label]

        predicted_count = sum(
            matrix[actual][label]
            for actual in labels
        )

        actual_count = sum(
            matrix[label][pred]
            for pred in labels
        )

        precision = (
            tp / predicted_count
            if predicted_count > 0
            else 0.0
        )

        recall = (
            tp / actual_count
            if actual_count > 0
            else 0.0
        )

        if precision + recall > 0:
            f1 = (
                2 * precision * recall
                / (precision + recall)
            )
        else:
            f1 = 0.0

        directional_f1_values.append(f1)

    directional_f1 = safe_mean(
        directional_f1_values
    )

    predicted_directional = [
        r for r in records
        if r["prediction"] in ("B", "S")
    ]

    coverage = (
        len(predicted_directional) / total
    )

    neutral_rate = (
        sum(
            1 for r in records
            if r["actual"] == "N"
        )
        / total
    )

    buy_actual_rate = (
        sum(
            1 for r in records
            if r["actual"] == "B"
        )
        / total
    )

    sell_actual_rate = (
        sum(
            1 for r in records
            if r["actual"] == "S"
        )
        / total
    )

    neutral_actual_rate = neutral_rate

    return {
        "accuracy": accuracy,
        "balanced_accuracy": balanced_accuracy,
        "macro_f1": macro_f1,
        "directional_accuracy": directional_accuracy,
        "directional_f1": directional_f1,
        "buy_precision": buy_precision,
        "sell_precision": sell_precision,
        "coverage": coverage,
        "neutral_rate": neutral_rate,
        "buy_actual_rate": buy_actual_rate,
        "sell_actual_rate": sell_actual_rate,
        "neutral_actual_rate": neutral_actual_rate,
    }


# ============================================================
# OOS SCORE
# ============================================================

def calculate_oos_score(metrics_by_horizon):

    directional_accuracy = safe_mean(
        [
            x["directional_accuracy"]
            for x in metrics_by_horizon
        ]
    )

    directional_f1 = safe_mean(
        [
            x["directional_f1"]
            for x in metrics_by_horizon
        ]
    )

    balanced_accuracy = safe_mean(
        [
            x["balanced_accuracy"]
            for x in metrics_by_horizon
        ]
    )

    coverage = safe_mean(
        [
            x["coverage"]
            for x in metrics_by_horizon
        ]
    )

    # Balance between directional usefulness,
    # classification quality and useful coverage.
    #
    # This is deliberately independent from v3.2/v3.2.1.
    #
    score = (
        directional_accuracy * 35
        + directional_f1 * 25
        + balanced_accuracy * 20
        + coverage * 20
    )

    return score


# ============================================================
# HORIZON STABILITY
# ============================================================

def calculate_stability(metrics_by_horizon):

    values = [
        x["directional_accuracy"]
        for x in metrics_by_horizon
    ]

    if not values:
        return 0.0

    average = safe_mean(values)

    if average == 0:
        return 0.0

    spread = max(values) - min(values)

    stability = 100 * (
        1 - clamp(
            spread / average
        )
    )

    return stability


# ============================================================
# MAIN VALIDATION
# ============================================================

def main():

    print()
    print("=" * 78)
    print("MLAI v3.2.3 CHRONOLOGICAL OUT-OF-SAMPLE VALIDATION")
    print("=" * 78)
    print()
    print("Purpose: test threshold candidates on unseen historical data.")
    print()

    print(f"Market file       : {MARKET_FILE}")
    print(f"Current window    : {CURRENT_WINDOW}")
    print(f"Horizons          : {HORIZONS}")

    threshold_text = ", ".join(
        f"±{t * 100:.2f}%"
        for t in THRESHOLDS
    )

    print(f"Thresholds        : {threshold_text}")
    print(f"Validation ratio  : {VALIDATION_RATIO * 100:.0f}%")
    print()

    # --------------------------------------------------------
    # LOAD
    # --------------------------------------------------------

    data = load_market_data()

    print("PASS: market_data.bin loaded.")

    if isinstance(data, list):
        print(f"Stored candles: {len(data)}")
    elif isinstance(data, dict):
        print("Stored candles: data structure detected.")

    print()
    print("PASS: Original market data will NOT be modified.")
    print("PASS: MLAI v3.1 will NOT be modified.")
    print("PASS: Existing learning memory will NOT be modified.")
    print()

    closes = extract_close_prices(data)

    print("PASS: Close prices extracted.")
    print(f"Valid close prices: {len(closes)}")
    print()

    # --------------------------------------------------------
    # CHRONOLOGICAL SPLIT
    # --------------------------------------------------------

    validation_start = int(
        len(closes) * (1 - VALIDATION_RATIO)
    )

    calibration_count = validation_start
    validation_count = len(closes) - validation_start

    print("=" * 78)
    print("CHRONOLOGICAL DATA SPLIT")
    print("-" * 78)

    print(
        f"Calibration/reference candles : "
        f"{calibration_count}"
    )

    print(
        f"Validation candles            : "
        f"{validation_count}"
    )

    print(
        f"Validation begins at index    : "
        f"{validation_start}"
    )

    print()
    print(
        "IMPORTANT: The later validation period is treated as unseen."
    )
    print()

    # --------------------------------------------------------
    # DATASET
    # --------------------------------------------------------

    print("Building walk-forward dataset...")

    dataset = build_dataset(
        closes,
        validation_start
    )

    print("PASS: Walk-forward dataset generated.")
    print()

    validation_dataset = [
        r for r in dataset
        if r["validation"]
    ]

    if not validation_dataset:
        raise RuntimeError(
            "Validation dataset is empty."
        )

    # --------------------------------------------------------
    # TEST CANDIDATES
    # --------------------------------------------------------

    all_results = []

    for threshold in THRESHOLDS:

        print("=" * 78)
        print(
            f"TESTING OOS THRESHOLD "
            f"±{threshold * 100:.2f}%"
        )
        print("-" * 78)

        horizon_results = []

        for horizon in HORIZONS:

            records = []

            horizon_data = [
                r for r in validation_dataset
                if r["horizon"] == horizon
            ]

            for item in horizon_data:

                actual = classify_outcome(
                    item["start_price"],
                    item["future_price"],
                    threshold
                )

                records.append(
                    {
                        "prediction": item["prediction"],
                        "actual": actual,
                    }
                )

            metrics = calculate_metrics(records)

            result = {
                "horizon": horizon,
                "records": len(records),
                **metrics,
            }

            horizon_results.append(result)

            print(
                f"{horizon:2d} candles -> "
                f"records={len(records)} | "
                f"overall={pct(metrics['accuracy'])} | "
                f"balanced={pct(metrics['balanced_accuracy'])} | "
                f"macro-F1={pct(metrics['macro_f1'])} | "
                f"directional={pct(metrics['directional_accuracy'])} | "
                f"dir-F1={pct(metrics['directional_f1'])} | "
                f"BUY precision={pct(metrics['buy_precision'])} | "
                f"SELL precision={pct(metrics['sell_precision'])} | "
                f"coverage={pct(metrics['coverage'])}"
            )

        avg_directional = safe_mean(
            [
                x["directional_accuracy"]
                for x in horizon_results
            ]
        )

        avg_directional_f1 = safe_mean(
            [
                x["directional_f1"]
                for x in horizon_results
            ]
        )

        avg_balanced = safe_mean(
            [
                x["balanced_accuracy"]
                for x in horizon_results
            ]
        )

        avg_buy_precision = safe_mean(
            [
                x["buy_precision"]
                for x in horizon_results
            ]
        )

        avg_sell_precision = safe_mean(
            [
                x["sell_precision"]
                for x in horizon_results
            ]
        )

        avg_coverage = safe_mean(
            [
                x["coverage"]
                for x in horizon_results
            ]
        )

        stability = calculate_stability(
            horizon_results
        )

        score = calculate_oos_score(
            horizon_results
        )

        result = {
            "threshold": threshold,
            "threshold_percent": threshold * 100,
            "horizons": horizon_results,
            "average_directional_accuracy":
                avg_directional,
            "average_directional_f1":
                avg_directional_f1,
            "average_balanced_accuracy":
                avg_balanced,
            "average_buy_precision":
                avg_buy_precision,
            "average_sell_precision":
                avg_sell_precision,
            "coverage":
                avg_coverage,
            "stability":
                stability,
            "score":
                score,
        }

        all_results.append(result)

        print()
        print(
            f"Average directional accuracy : "
            f"{pct(avg_directional)}"
        )

        print(
            f"Average directional F1       : "
            f"{pct(avg_directional_f1)}"
        )

        print(
            f"Average balanced accuracy    : "
            f"{pct(avg_balanced)}"
        )

        print(
            f"Average BUY precision        : "
            f"{pct(avg_buy_precision)}"
        )

        print(
            f"Average SELL precision       : "
            f"{pct(avg_sell_precision)}"
        )

        print(
            f"Directional coverage         : "
            f"{pct(avg_coverage)}"
        )

        print(
            f"Cross-horizon stability      : "
            f"{stability:.2f}"
        )

        print(
            f"OOS validation score        : "
            f"{score:.2f}"
        )

        print()

    # --------------------------------------------------------
    # RANKING
    # --------------------------------------------------------

    ranked = sorted(
        all_results,
        key=lambda x: x["score"],
        reverse=True
    )

    print("=" * 78)
    print("OUT-OF-SAMPLE VALIDATION RANKING")
    print("=" * 78)

    print(
        "Rank | Threshold | Directional | Dir-F1 | "
        "BUY Prec | SELL Prec | Coverage | Stability | Score"
    )

    print("-" * 78)

    for i, result in enumerate(ranked, start=1):

        print(
            f"{i:02d}.  | "
            f"±{result['threshold_percent']:.2f}%   | "
            f"{pct(result['average_directional_accuracy']):>10} | "
            f"{pct(result['average_directional_f1']):>7} | "
            f"{pct(result['average_buy_precision']):>8} | "
            f"{pct(result['average_sell_precision']):>9} | "
            f"{pct(result['coverage']):>8} | "
            f"{result['stability']:>9.2f} | "
            f"{result['score']:>5.2f}"
        )

    # --------------------------------------------------------
    # BEST RESULT
    # --------------------------------------------------------

    best = ranked[0]

    print()
    print("=" * 78)
    print("V3.2.3 OUT-OF-SAMPLE VALIDATION RESULT")
    print("=" * 78)
    print()

    print(
        "Best unseen-data candidate : "
        f"±{best['threshold_percent']:.2f}%"
    )

    print(
        "OOS validation score       : "
        f"{best['score']:.2f}"
    )

    print(
        "Directional accuracy       : "
        f"{pct(best['average_directional_accuracy'])}"
    )

    print(
        "Directional F1             : "
        f"{pct(best['average_directional_f1'])}"
    )

    print(
        "BUY precision              : "
        f"{pct(best['average_buy_precision'])}"
    )

    print(
        "SELL precision             : "
        f"{pct(best['average_sell_precision'])}"
    )

    print(
        "Directional coverage       : "
        f"{pct(best['coverage'])}"
    )

    print(
        "Cross-horizon stability    : "
        f"{best['stability']:.2f}"
    )

    print()

    print(
        "IMPORTANT: This result is historical "
        "out-of-sample evidence only."
    )

    print(
        "IMPORTANT: It does NOT guarantee future "
        "trading performance."
    )

    print(
        "IMPORTANT: v3.1 classification logic "
        "has NOT been changed."
    )

    # --------------------------------------------------------
    # SAVE BIN
    # --------------------------------------------------------

    output = {
        "engine": "MLAI v3.2.3",
        "purpose": "chronological out-of-sample validation",
        "market_file": MARKET_FILE,
        "stored_candles": len(closes),
        "current_window": CURRENT_WINDOW,
        "horizons": HORIZONS,
        "thresholds_tested": THRESHOLDS,
        "validation_ratio": VALIDATION_RATIO,
        "validation_start": validation_start,
        "calibration_candles": calibration_count,
        "validation_candles": validation_count,
        "results": all_results,
        "ranking": [
            {
                "rank": i,
                "threshold": r["threshold"],
                "threshold_percent":
                    r["threshold_percent"],
                "score": r["score"],
                "directional_accuracy":
                    r["average_directional_accuracy"],
                "directional_f1":
                    r["average_directional_f1"],
                "buy_precision":
                    r["average_buy_precision"],
                "sell_precision":
                    r["average_sell_precision"],
                "coverage":
                    r["coverage"],
                "stability":
                    r["stability"],
            }
            for i, r in enumerate(ranked, start=1)
        ],
        "best_candidate":
            best["threshold"],
        "best_candidate_percent":
            best["threshold_percent"],
        "v31_modified": False,
        "market_data_modified": False,
        "learning_memory_modified": False,
    }

    with open(OUTPUT_BIN, "wb") as f:
        pickle.dump(output, f)

    print()
    print(f"PASS: {OUTPUT_BIN} saved.")

    # --------------------------------------------------------
    # REPORT
    # --------------------------------------------------------

    report = []

    report.append("# MLAI v3.2.3 Out-of-Sample Validation Report")
    report.append("")

    report.append("## Purpose")
    report.append("")
    report.append(
        "This experiment evaluates candidate outcome-classification "
        "thresholds on a later chronological historical period "
        "that was not used for candidate selection."
    )
    report.append("")

    report.append("## Dataset")
    report.append("")
    report.append(
        f"- Market file: `{MARKET_FILE}`"
    )
    report.append(
        f"- Valid candles: **{len(closes)}**"
    )
    report.append(
        f"- Current window: **{CURRENT_WINDOW}**"
    )
    report.append(
        f"- Horizons: **{HORIZONS}**"
    )
    report.append(
        f"- Validation ratio: **{VALIDATION_RATIO * 100:.0f}%**"
    )
    report.append(
        f"- Calibration/reference candles: **{calibration_count}**"
    )
    report.append(
        f"- Validation candles: **{validation_count}**"
    )
    report.append("")

    report.append("## Candidate Thresholds")
    report.append("")

    for threshold in THRESHOLDS:
        report.append(
            f"- ±{threshold * 100:.2f}%"
        )

    report.append("")

    report.append("## Ranking")
    report.append("")

    report.append(
        "| Rank | Threshold | Directional | Dir-F1 | "
        "BUY Precision | SELL Precision | Coverage | Stability | Score |"
    )

    report.append(
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    )

    for i, result in enumerate(ranked, start=1):

        report.append(
            f"| {i} | "
            f"±{result['threshold_percent']:.2f}% | "
            f"{pct(result['average_directional_accuracy'])} | "
            f"{pct(result['average_directional_f1'])} | "
            f"{pct(result['average_buy_precision'])} | "
            f"{pct(result['average_sell_precision'])} | "
            f"{pct(result['coverage'])} | "
            f"{result['stability']:.2f} | "
            f"{result['score']:.2f} |"
        )

    report.append("")

    report.append("## Result")
    report.append("")

    report.append(
        f"**Best out-of-sample candidate: "
        f"±{best['threshold_percent']:.2f}%**"
    )

    report.append("")

    report.append(
        f"- OOS score: **{best['score']:.2f}**"
    )

    report.append(
        f"- Directional accuracy: "
        f"**{pct(best['average_directional_accuracy'])}**"
    )

    report.append(
        f"- Directional F1: "
        f"**{pct(best['average_directional_f1'])}**"
    )

    report.append(
        f"- BUY precision: "
        f"**{pct(best['average_buy_precision'])}**"
    )

    report.append(
        f"- SELL precision: "
        f"**{pct(best['average_sell_precision'])}**"
    )

    report.append(
        f"- Coverage: "
        f"**{pct(best['coverage'])}**"
    )

    report.append(
        f"- Cross-horizon stability: "
        f"**{best['stability']:.2f}**"
    )

    report.append("")

    report.append("## Important Interpretation")
    report.append("")

    report.append(
        "This result is historical evidence only. "
        "It is not a guarantee of future market performance."
    )

    report.append(
        "No v3.1 logic was changed during this experiment."
    )

    report.append(
        "The original market data was not modified."
    )

    report.append(
        "Existing MLAI learning memory was not modified."
    )

    report.append("")

    report.append("## Next Decision")
    report.append("")

    report.append(
        "The out-of-sample result should be compared with "
        "the v3.2, v3.2.1 and v3.2.2 calibration results "
        "before changing any production classification logic."
    )

    with open(
        OUTPUT_REPORT,
        "w",
        encoding="utf-8"
    ) as f:
        f.write("\n".join(report))

    print(f"PASS: {OUTPUT_REPORT} saved.")

    # --------------------------------------------------------
    # PROJECT STATUS
    # --------------------------------------------------------

    status_text = f"""
MLAI PROJECT STATUS
===================

Latest validation:
MLAI v3.2.3 chronological out-of-sample validation

Market candles:
{len(closes)}

Validation period:
{validation_count} candles

Best OOS candidate:
±{best['threshold_percent']:.2f}%

OOS validation score:
{best['score']:.2f}

Directional accuracy:
{pct(best['average_directional_accuracy'])}

Directional F1:
{pct(best['average_directional_f1'])}

BUY precision:
{pct(best['average_buy_precision'])}

SELL precision:
{pct(best['average_sell_precision'])}

Coverage:
{pct(best['coverage'])}

Cross-horizon stability:
{best['stability']:.2f}

IMPORTANT:
This is historical out-of-sample evidence only.

v3.1 modified:
NO

market_data.bin modified:
NO

Existing learning memory modified:
NO

Next stage:
Review v3.2.3 against previous calibration results
before changing outcome-classification logic.
"""

    with open(
        STATUS_FILE,
        "w",
        encoding="utf-8"
    ) as f:
        f.write(status_text.strip() + "\n")

    print(f"PASS: {STATUS_FILE} updated.")

    print()
    print("=" * 78)
    print("MLAI v3.2.3 OUT-OF-SAMPLE VALIDATION COMPLETED")
    print("=" * 78)
    print()
    print(
        f"Recommended OOS candidate : "
        f"±{best['threshold_percent']:.2f}%"
    )
    print(
        f"OOS validation score      : "
        f"{best['score']:.2f}"
    )
    print()
    print("PASS: v3.1 remains unchanged.")
    print("PASS: market_data.bin remains unchanged.")
    print("PASS: Existing learning memory remains unchanged.")
    print()
    print("NEXT STEP:")
    print(
        "Review the complete v3.2.3 output before "
        "changing any v3.1 classification logic."
    )
    print()


if __name__ == "__main__":
    main()