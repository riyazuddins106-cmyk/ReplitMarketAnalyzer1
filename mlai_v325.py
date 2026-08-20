import os
import pickle
import math
from collections import Counter


# ============================================================
# MLAI v3.2.5
# CORRECTED CHRONOLOGICAL OUT-OF-SAMPLE VALIDATION ENGINE
# ============================================================

MARKET_FILE = "market_data.bin"

CURRENT_WINDOW = 60
HORIZONS = [4, 8, 16]

THRESHOLDS = [0.0015, 0.0018, 0.0020, 0.0024]

VALIDATION_RATIO = 0.30


# ============================================================
# DISPLAY
# ============================================================

def header(title):
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def section(title):
    print()
    print("=" * 78)
    print(title)
    print("-" * 78)


# ============================================================
# LOAD MARKET DATA
# ============================================================

header("MLAI v3.2.5 CORRECTED OUT-OF-SAMPLE VALIDATION")
print("Purpose: independently validate threshold classification and")
print("correctly separate target coverage from prediction coverage.")
print()
print(f"Market file       : {MARKET_FILE}")
print(f"Current window    : {CURRENT_WINDOW}")
print(f"Horizons          : {HORIZONS}")
print(
    "Thresholds        : "
    + ", ".join(f"±{x * 100:.2f}%" for x in THRESHOLDS)
)
print(f"Validation ratio  : {VALIDATION_RATIO * 100:.0f}%")

if not os.path.exists(MARKET_FILE):
    raise FileNotFoundError(f"{MARKET_FILE} not found.")

with open(MARKET_FILE, "rb") as f:
    market_data = pickle.load(f)

print()
print("PASS: market_data.bin loaded.")
print(f"Data type: {type(market_data).__name__}")

print()
print("PASS: Original market data will NOT be modified.")
print("PASS: MLAI v3.1 will NOT be modified.")
print("PASS: Existing learning memory will NOT be modified.")


# ============================================================
# EXTRACT CLOSE PRICES
# ============================================================

def extract_close_prices(data):
    candidates = []

    if isinstance(data, dict):
        for key in ["candles", "data", "prices", "market_data"]:
            value = data.get(key)

            if isinstance(value, list):
                candidates.append(value)

    elif isinstance(data, list):
        candidates.append(data)

    for records in candidates:
        closes = []

        for row in records:
            value = None

            if isinstance(row, dict):
                for key in ["close", "Close", "c", "closing_price"]:
                    if key in row:
                        value = row[key]
                        break

            elif isinstance(row, (list, tuple)):
                # Common OHLC structure:
                # timestamp, open, high, low, close
                if len(row) >= 5:
                    value = row[4]

            if value is not None:
                try:
                    value = float(value)

                    if math.isfinite(value) and value > 0:
                        closes.append(value)
                except Exception:
                    pass

        if len(closes) >= 100:
            return closes

    raise ValueError(
        "Could not extract at least 100 valid close prices "
        "from market_data.bin."
    )


closes = extract_close_prices(market_data)

print()
print("PASS: Close prices extracted.")
print(f"Valid close prices: {len(closes)}")


# ============================================================
# CHRONOLOGICAL SPLIT
# ============================================================

split_index = int(len(closes) * (1 - VALIDATION_RATIO))

calibration_candles = closes[:split_index]
validation_candles = closes[split_index:]

section("CHRONOLOGICAL DATA SPLIT")

print(f"Calibration/reference candles : {len(calibration_candles)}")
print(f"Validation candles            : {len(validation_candles)}")
print(f"Validation begins at index    : {split_index}")

if split_index <= CURRENT_WINDOW:
    raise ValueError("Validation split is too early for the current window.")

print()
print("PASS: validation period occurs after calibration/reference period.")
print("PASS: validation period will be treated as unseen historical data.")


# ============================================================
# CLASSIFICATION
# ============================================================

def classify_return(start_price, future_price, threshold):
    if start_price <= 0:
        return "N"

    change = (future_price - start_price) / start_price

    if change >= threshold:
        return "B"

    if change <= -threshold:
        return "S"

    return "N"


# ============================================================
# BUILD OOS DATASET
# ============================================================

section("BUILDING CHRONOLOGICAL OOS DATASET")

records = []

# IMPORTANT:
# Prediction point must be inside the validation period.
#
# Historical window:
# closes[i-CURRENT_WINDOW:i]
#
# Target:
# closes[i+horizon]
#
# Therefore the target is always strictly after i.

for i in range(split_index, len(closes)):

    if i < CURRENT_WINDOW:
        continue

    for horizon in HORIZONS:

        target_index = i + horizon

        if target_index >= len(closes):
            continue

        start_price = closes[i]
        future_price = closes[target_index]

        if start_price <= 0 or future_price <= 0:
            continue

        # ====================================================
        # SIMPLE WALK-FORWARD DIRECTIONAL MODEL
        # ====================================================
        #
        # This deliberately uses ONLY candles before i.
        #
        # It estimates direction from the historical window.
        #
        # This is not a trading strategy.
        # It is a validation baseline.
        # ====================================================

        window = closes[i - CURRENT_WINDOW:i]

        first_price = window[0]
        last_price = window[-1]

        historical_return = (
            (last_price - first_price) / first_price
            if first_price > 0
            else 0.0
        )

        # Direction prediction:
        #
        # positive historical movement -> BUY
        # negative historical movement -> SELL
        #
        # The threshold is intentionally applied later,
        # separately to the prediction and the target.

        records.append(
            {
                "index": i,
                "horizon": horizon,
                "start_price": start_price,
                "future_price": future_price,
                "historical_return": historical_return,
            }
        )

print("PASS: chronological OOS dataset generated.")
print(f"Total OOS records: {len(records)}")


# ============================================================
# METRICS
# ============================================================

def safe_div(a, b):
    return a / b if b else 0.0


def f1_score(precision, recall):
    return safe_div(
        2 * precision * recall,
        precision + recall
    )


def calculate_metrics(rows, threshold):

    target_labels = []
    prediction_labels = []

    for row in rows:

        target = classify_return(
            row["start_price"],
            row["future_price"],
            threshold,
        )

        prediction_change = row["historical_return"]

        if prediction_change >= threshold:
            prediction = "B"
        elif prediction_change <= -threshold:
            prediction = "S"
        else:
            prediction = "N"

        target_labels.append(target)
        prediction_labels.append(prediction)

    total = len(target_labels)

    # --------------------------------------------------------
    # TARGET COVERAGE
    # --------------------------------------------------------

    target_directional = sum(
        x in ("B", "S") for x in target_labels
    )

    target_neutral = sum(
        x == "N" for x in target_labels
    )

    target_coverage = safe_div(
        target_directional,
        total
    )

    target_neutral_rate = safe_div(
        target_neutral,
        total
    )

    # --------------------------------------------------------
    # PREDICTION COVERAGE
    # --------------------------------------------------------

    prediction_directional = sum(
        x in ("B", "S") for x in prediction_labels
    )

    prediction_neutral = sum(
        x == "N" for x in prediction_labels
    )

    prediction_coverage = safe_div(
        prediction_directional,
        total
    )

    prediction_neutral_rate = safe_div(
        prediction_neutral,
        total
    )

    # --------------------------------------------------------
    # OVERALL ACCURACY
    # --------------------------------------------------------

    correct = sum(
        a == b
        for a, b in zip(target_labels, prediction_labels)
    )

    overall_accuracy = safe_div(correct, total)

    # --------------------------------------------------------
    # DIRECTIONAL ACCURACY
    #
    # Only targets that actually became BUY or SELL.
    # --------------------------------------------------------

    directional_indices = [
        i
        for i, target in enumerate(target_labels)
        if target in ("B", "S")
    ]

    directional_correct = sum(
        target_labels[i] == prediction_labels[i]
        for i in directional_indices
    )

    directional_accuracy = safe_div(
        directional_correct,
        len(directional_indices)
    )

    # --------------------------------------------------------
    # BUY METRICS
    # --------------------------------------------------------

    actual_buy = sum(
        x == "B"
        for x in target_labels
    )

    predicted_buy = sum(
        x == "B"
        for x in prediction_labels
    )

    true_buy = sum(
        target_labels[i] == "B"
        and prediction_labels[i] == "B"
        for i in range(total)
    )

    buy_precision = safe_div(
        true_buy,
        predicted_buy
    )

    buy_recall = safe_div(
        true_buy,
        actual_buy
    )

    buy_f1 = f1_score(
        buy_precision,
        buy_recall
    )

    # --------------------------------------------------------
    # SELL METRICS
    # --------------------------------------------------------

    actual_sell = sum(
        x == "S"
        for x in target_labels
    )

    predicted_sell = sum(
        x == "S"
        for x in prediction_labels
    )

    true_sell = sum(
        target_labels[i] == "S"
        and prediction_labels[i] == "S"
        for i in range(total)
    )

    sell_precision = safe_div(
        true_sell,
        predicted_sell
    )

    sell_recall = safe_div(
        true_sell,
        actual_sell
    )

    sell_f1 = f1_score(
        sell_precision,
        sell_recall
    )

    directional_f1 = (
        buy_f1 + sell_f1
    ) / 2

    # --------------------------------------------------------
    # NEUTRAL METRICS
    # --------------------------------------------------------

    actual_neutral = sum(
        x == "N"
        for x in target_labels
    )

    predicted_neutral = sum(
        x == "N"
        for x in prediction_labels
    )

    true_neutral = sum(
        target_labels[i] == "N"
        and prediction_labels[i] == "N"
        for i in range(total)
    )

    neutral_precision = safe_div(
        true_neutral,
        predicted_neutral
    )

    neutral_recall = safe_div(
        true_neutral,
        actual_neutral
    )

    neutral_f1 = f1_score(
        neutral_precision,
        neutral_recall
    )

    # --------------------------------------------------------
    # MACRO F1
    # --------------------------------------------------------

    macro_f1 = (
        buy_f1
        + sell_f1
        + neutral_f1
    ) / 3

    # --------------------------------------------------------
    # TARGET CLASS BALANCE
    # --------------------------------------------------------

    target_counts = Counter(target_labels)

    buy_rate = safe_div(target_counts["B"], total)
    sell_rate = safe_div(target_counts["S"], total)
    neutral_rate = safe_div(target_counts["N"], total)

    return {
        "records": total,

        "overall_accuracy": overall_accuracy,

        "directional_accuracy": directional_accuracy,
        "directional_f1": directional_f1,

        "buy_precision": buy_precision,
        "sell_precision": sell_precision,

        "buy_f1": buy_f1,
        "sell_f1": sell_f1,
        "neutral_f1": neutral_f1,

        "macro_f1": macro_f1,

        "target_coverage": target_coverage,
        "target_neutral_rate": target_neutral_rate,

        "prediction_coverage": prediction_coverage,
        "prediction_neutral_rate": prediction_neutral_rate,

        "target_buy_rate": buy_rate,
        "target_sell_rate": sell_rate,
        "target_neutral_rate": neutral_rate,

        "predicted_buy_rate": safe_div(
            predicted_buy,
            total
        ),

        "predicted_sell_rate": safe_div(
            predicted_sell,
            total
        ),

        "predicted_neutral_rate": safe_div(
            prediction_neutral,
            total
        ),
    }


# ============================================================
# TEST THRESHOLDS
# ============================================================

all_results = []

for threshold in THRESHOLDS:

    section(
        f"TESTING CORRECTED OOS THRESHOLD ±{threshold * 100:.2f}%"
    )

    horizon_results = []

    for horizon in HORIZONS:

        horizon_rows = [
            row
            for row in records
            if row["horizon"] == horizon
        ]

        metrics = calculate_metrics(
            horizon_rows,
            threshold
        )

        horizon_results.append(metrics)

        print(
            f"{horizon:2d} candles -> "
            f"records={metrics['records']} | "
            f"overall={metrics['overall_accuracy'] * 100:.2f}% | "
            f"balanced-target={metrics['target_coverage'] * 100:.2f}% | "
            f"macro-F1={metrics['macro_f1'] * 100:.2f}% | "
            f"directional={metrics['directional_accuracy'] * 100:.2f}% | "
            f"dir-F1={metrics['directional_f1'] * 100:.2f}% | "
            f"BUY precision={metrics['buy_precision'] * 100:.2f}% | "
            f"SELL precision={metrics['sell_precision'] * 100:.2f}% | "
            f"target-coverage={metrics['target_coverage'] * 100:.2f}% | "
            f"prediction-coverage={metrics['prediction_coverage'] * 100:.2f}%"
        )

    avg_directional = sum(
        x["directional_accuracy"]
        for x in horizon_results
    ) / len(horizon_results)

    avg_directional_f1 = sum(
        x["directional_f1"]
        for x in horizon_results
    ) / len(horizon_results)

    avg_macro_f1 = sum(
        x["macro_f1"]
        for x in horizon_results
    ) / len(horizon_results)

    avg_buy_precision = sum(
        x["buy_precision"]
        for x in horizon_results
    ) / len(horizon_results)

    avg_sell_precision = sum(
        x["sell_precision"]
        for x in horizon_results
    ) / len(horizon_results)

    avg_target_coverage = sum(
        x["target_coverage"]
        for x in horizon_results
    ) / len(horizon_results)

    avg_prediction_coverage = sum(
        x["prediction_coverage"]
        for x in horizon_results
    ) / len(horizon_results)

    # --------------------------------------------------------
    # CROSS-HORIZON STABILITY
    # --------------------------------------------------------

    directional_values = [
        x["directional_accuracy"]
        for x in horizon_results
    ]

    mean_directional = sum(
        directional_values
    ) / len(directional_values)

    variance = sum(
        (x - mean_directional) ** 2
        for x in directional_values
    ) / len(directional_values)

    std = math.sqrt(variance)

    stability = max(
        0.0,
        100.0 - (std * 100.0)
    )

    # --------------------------------------------------------
    # CORRECTED VALIDATION SCORE
    #
    # Directional usefulness + F1 + precision.
    #
    # Coverage is reported separately and NOT allowed to
    # masquerade as prediction accuracy.
    # --------------------------------------------------------

    score = (
        avg_directional * 45
        + avg_directional_f1 * 25
        + avg_macro_f1 * 15
        + ((avg_buy_precision + avg_sell_precision) / 2) * 15
    )

    result = {
        "threshold": threshold,

        "avg_directional": avg_directional,
        "avg_directional_f1": avg_directional_f1,
        "avg_macro_f1": avg_macro_f1,

        "avg_buy_precision": avg_buy_precision,
        "avg_sell_precision": avg_sell_precision,

        "avg_target_coverage": avg_target_coverage,
        "avg_prediction_coverage": avg_prediction_coverage,

        "stability": stability,
        "score": score,

        "horizon_results": horizon_results,
    }

    all_results.append(result)

    print()
    print(
        f"Average directional accuracy : "
        f"{avg_directional * 100:.2f}%"
    )

    print(
        f"Average directional F1       : "
        f"{avg_directional_f1 * 100:.2f}%"
    )

    print(
        f"Average macro-F1             : "
        f"{avg_macro_f1 * 100:.2f}%"
    )

    print(
        f"Average BUY precision        : "
        f"{avg_buy_precision * 100:.2f}%"
    )

    print(
        f"Average SELL precision       : "
        f"{avg_sell_precision * 100:.2f}%"
    )

    print(
        f"Target directional coverage  : "
        f"{avg_target_coverage * 100:.2f}%"
    )

    print(
        f"Prediction directional coverage : "
        f"{avg_prediction_coverage * 100:.2f}%"
    )

    print(
        f"Cross-horizon stability      : "
        f"{stability:.2f}"
    )

    print(
        f"Corrected OOS validation score : "
        f"{score:.2f}"
    )


# ============================================================
# RANKING
# ============================================================

section("CORRECTED OOS VALIDATION RANKING")

ranked = sorted(
    all_results,
    key=lambda x: x["score"],
    reverse=True
)

print(
    "Rank | Threshold | Directional | Dir-F1 | "
    "BUY Prec | SELL Prec | Target Cov | Pred Cov | Score"
)

print("-" * 110)

for index, result in enumerate(ranked, 1):

    print(
        f"{index:02d}.  | "
        f"±{result['threshold'] * 100:.2f}%   | "
        f"{result['avg_directional'] * 100:10.2f}% | "
        f"{result['avg_directional_f1'] * 100:6.2f}% | "
        f"{result['avg_buy_precision'] * 100:8.2f}% | "
        f"{result['avg_sell_precision'] * 100:9.2f}% | "
        f"{result['avg_target_coverage'] * 100:10.2f}% | "
        f"{result['avg_prediction_coverage'] * 100:8.2f}% | "
        f"{result['score']:6.2f}"
    )


# ============================================================
# FINAL RESULT
# ============================================================

best = ranked[0]

section("V3.2.5 CORRECTED OOS VALIDATION RESULT")

print()
print(
    f"Best corrected OOS candidate : "
    f"±{best['threshold'] * 100:.2f}%"
)

print(
    f"Corrected OOS validation score : "
    f"{best['score']:.2f}"
)

print(
    f"Directional accuracy : "
    f"{best['avg_directional'] * 100:.2f}%"
)

print(
    f"Directional F1 : "
    f"{best['avg_directional_f1'] * 100:.2f}%"
)

print(
    f"BUY precision : "
    f"{best['avg_buy_precision'] * 100:.2f}%"
)

print(
    f"SELL precision : "
    f"{best['avg_sell_precision'] * 100:.2f}%"
)

print(
    f"Target directional coverage : "
    f"{best['avg_target_coverage'] * 100:.2f}%"
)

print(
    f"Prediction directional coverage : "
    f"{best['avg_prediction_coverage'] * 100:.2f}%"
)

print(
    f"Cross-horizon stability : "
    f"{best['stability']:.2f}"
)

print()
print("IMPORTANT:")
print("This is historical out-of-sample evidence only.")
print("It does NOT guarantee future trading performance.")
print()
print("IMPORTANT:")
print("MLAI v3.1 classification logic has NOT been changed.")
print("market_data.bin has NOT been changed.")
print("Existing learning memory has NOT been changed.")


# ============================================================
# SAVE VALIDATION RESULT
# ============================================================

output = {
    "engine": "MLAI v3.2.5",
    "purpose": "Corrected chronological OOS validation",
    "market_file": MARKET_FILE,
    "market_candles": len(closes),
    "current_window": CURRENT_WINDOW,
    "horizons": HORIZONS,
    "thresholds": THRESHOLDS,
    "validation_ratio": VALIDATION_RATIO,
    "split_index": split_index,
    "best_candidate": best,
    "ranking": ranked,
}

with open(
    "mlai_v325_corrected_oos_validation.bin",
    "wb"
) as f:
    pickle.dump(output, f)

print()
print(
    "PASS: "
    "mlai_v325_corrected_oos_validation.bin saved."
)

print()
print("=" * 78)
print("MLAI v3.2.5 CORRECTED OOS VALIDATION COMPLETED")
print("=" * 78)

print()
print(
    f"Recommended corrected OOS candidate: "
    f"±{best['threshold'] * 100:.2f}%"
)

print(
    f"Corrected OOS validation score: "
    f"{best['score']:.2f}"
)

print()
print("NEXT STEP:")
print("Review the target/prediction coverage separation.")
print("Do NOT modify MLAI v3.1 until the result is reviewed.")
