
import os
import pickle
from collections import Counter
from statistics import mean


# ============================================================
# MLAI v3.2.2
# FINE-GRAINED DIRECTIONAL VALIDATION ENGINE
# ============================================================
#
# Purpose:
#   Validate whether the historically selected threshold is
#   genuinely useful for BUY/SELL directional classification.
#
# IMPORTANT:
#   - market_data.bin is READ ONLY
#   - MLAI v3.1 is NOT modified
#   - existing learning memory is NOT modified
#   - v3.2.1 calibration file is READ ONLY
#
# ============================================================


MARKET_FILE = "market_data.bin"
CALIBRATION_FILE = "mlai_v321_calibration.bin"

WINDOW = 60
HORIZONS = [4, 8, 16]

THRESHOLDS = [
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
]

EPSILON = 1e-12


# ============================================================
# HELPERS
# ============================================================

def pct_change(start_price, end_price):
    if start_price == 0:
        return 0.0

    return ((end_price - start_price) / start_price) * 100.0


def classify_actual(change_pct, threshold):
    if change_pct > threshold:
        return "B"

    if change_pct < -threshold:
        return "S"

    return "N"


def safe_div(a, b):
    if abs(b) < EPSILON:
        return 0.0

    return a / b


def f1_score(precision, recall):
    if precision + recall == 0:
        return 0.0

    return 2.0 * precision * recall / (precision + recall)


# ============================================================
# LOAD MARKET DATA
# ============================================================

print()
print("=" * 78)
print("MLAI v3.2.2 DIRECTIONAL VALIDATION ENGINE")
print("=" * 78)
print()
print("Purpose: validate BUY/SELL directional usefulness of")
print("fine-grained historical outcome thresholds.")
print()
print(f"Market file       : {MARKET_FILE}")
print(f"Current window    : {WINDOW}")
print(f"Horizons          : {HORIZONS}")
print(
    "Thresholds        : "
    + ", ".join(f"±{x:.2f}%" for x in THRESHOLDS)
)
print()

if not os.path.exists(MARKET_FILE):
    print(f"ERROR: {MARKET_FILE} not found.")
    raise SystemExit(1)

with open(MARKET_FILE, "rb") as f:
    market_data = pickle.load(f)

print("PASS: market_data.bin loaded.")

# ------------------------------------------------------------
# Normalize possible data structures
# ------------------------------------------------------------

if isinstance(market_data, dict):
    if "candles" in market_data:
        candles = market_data["candles"]
    elif "data" in market_data:
        candles = market_data["data"]
    else:
        candles = list(market_data.values())
else:
    candles = market_data


if not isinstance(candles, list):
    candles = list(candles)


print(f"Stored candles: {len(candles)}")

if len(candles) < WINDOW + max(HORIZONS):
    print("ERROR: Not enough candles for validation.")
    raise SystemExit(1)

print()
print("PASS: Original market data will NOT be modified.")
print("PASS: MLAI v3.1 will NOT be modified.")
print("PASS: Existing learning memory will NOT be modified.")
print()


# ============================================================
# EXTRACT CLOSE PRICES
# ============================================================

def extract_close(candle):
    if isinstance(candle, dict):

        possible_keys = [
            "close",
            "Close",
            "c",
            "C",
        ]

        for key in possible_keys:
            if key in candle:
                return float(candle[key])

    elif isinstance(candle, (list, tuple)):

        # Common OHLC format:
        # timestamp, open, high, low, close, volume
        if len(candle) >= 5:
            return float(candle[4])

    raise ValueError(
        f"Unable to determine close price from candle: {candle}"
    )


closes = []

for candle in candles:
    closes.append(extract_close(candle))


print("PASS: Close prices extracted.")
print()


# ============================================================
# BUILD WALK-FORWARD PREDICTIONS
# ============================================================
#
# We intentionally use a simple historical directional baseline:
#
#   current close compared with the close at the beginning
#   of the 60-candle window.
#
# This lets us evaluate threshold behavior without changing
# the MLAI v3.1 learning engine.
#
# Prediction:
#
#   window movement > threshold  -> BUY
#   window movement < -threshold -> SELL
#   otherwise                    -> NEUTRAL
#
# Actual outcome is measured over the future horizon.
# ============================================================


print("Building walk-forward directional predictions...")
print()

predictions = {
    horizon: []
    for horizon in HORIZONS
}


for i in range(WINDOW, len(closes) - max(HORIZONS)):

    current_price = closes[i]

    historical_price = closes[i - WINDOW]

    historical_move = pct_change(
        historical_price,
        current_price
    )

    for horizon in HORIZONS:

        future_price = closes[i + horizon]

        future_move = pct_change(
            current_price,
            future_price
        )

        predictions[horizon].append(
            {
                "historical_move": historical_move,
                "future_move": future_move,
            }
        )


print("PASS: Walk-forward directional dataset generated.")
print()


# ============================================================
# VALIDATION
# ============================================================

results = []


for threshold in THRESHOLDS:

    print("=" * 78)
    print(
        f"TESTING DIRECTIONAL THRESHOLD ±{threshold:.2f}%"
    )
    print("-" * 78)

    horizon_results = []

    for horizon in HORIZONS:

        rows = predictions[horizon]

        # ----------------------------------------------------
        # Confusion counts
        # ----------------------------------------------------

        confusion = {
            "B": {"B": 0, "S": 0, "N": 0},
            "S": {"B": 0, "S": 0, "N": 0},
            "N": {"B": 0, "S": 0, "N": 0},
        }

        predicted_counts = Counter()
        actual_counts = Counter()

        for row in rows:

            predicted = classify_actual(
                row["historical_move"],
                threshold
            )

            actual = classify_actual(
                row["future_move"],
                threshold
            )

            confusion[predicted][actual] += 1

            predicted_counts[predicted] += 1
            actual_counts[actual] += 1

        total = sum(predicted_counts.values())

        # ----------------------------------------------------
        # Directional-only validation
        #
        # Remove cases where either prediction or actual
        # outcome is Neutral.
        # ----------------------------------------------------

        directional_total = 0
        directional_correct = 0

        buy_pred = 0
        sell_pred = 0

        buy_correct = 0
        sell_correct = 0

        for predicted in ("B", "S"):

            for actual in ("B", "S"):

                count = confusion[predicted][actual]

                directional_total += count

                if predicted == actual:
                    directional_correct += count

        for actual in ("B", "S"):

            buy_pred += confusion["B"][actual]
            sell_pred += confusion["S"][actual]

        buy_correct = confusion["B"]["B"]
        sell_correct = confusion["S"]["S"]

        directional_accuracy = safe_div(
            directional_correct,
            directional_total
        ) * 100.0

        buy_precision = safe_div(
            buy_correct,
            buy_pred
        ) * 100.0

        sell_precision = safe_div(
            sell_correct,
            sell_pred
        ) * 100.0

        # Recall is measured against actual directional events.
        actual_buy = (
            confusion["B"]["B"]
            + confusion["S"]["B"]
            + confusion["N"]["B"]
        )

        actual_sell = (
            confusion["B"]["S"]
            + confusion["S"]["S"]
            + confusion["N"]["S"]
        )

        buy_recall = safe_div(
            buy_correct,
            actual_buy
        ) * 100.0

        sell_recall = safe_div(
            sell_correct,
            actual_sell
        ) * 100.0

        buy_f1 = f1_score(
            buy_precision,
            buy_recall
        )

        sell_f1 = f1_score(
            sell_precision,
            sell_recall
        )

        directional_f1 = mean(
            [buy_f1, sell_f1]
        )

        # ----------------------------------------------------
        # Coverage
        # ----------------------------------------------------

        directional_prediction_count = (
            predicted_counts["B"]
            + predicted_counts["S"]
        )

        directional_coverage = safe_div(
            directional_prediction_count,
            total
        ) * 100.0

        # ----------------------------------------------------
        # Overall accuracy
        # ----------------------------------------------------

        overall_correct = (
            confusion["B"]["B"]
            + confusion["S"]["S"]
            + confusion["N"]["N"]
        )

        overall_accuracy = safe_div(
            overall_correct,
            total
        ) * 100.0

        # ----------------------------------------------------
        # Neutral prediction rate
        # ----------------------------------------------------

        neutral_rate = safe_div(
            predicted_counts["N"],
            total
        ) * 100.0

        horizon_result = {
            "horizon": horizon,
            "records": total,
            "overall_accuracy": overall_accuracy,
            "directional_accuracy": directional_accuracy,
            "directional_f1": directional_f1,
            "buy_precision": buy_precision,
            "sell_precision": sell_precision,
            "buy_recall": buy_recall,
            "sell_recall": sell_recall,
            "directional_coverage": directional_coverage,
            "neutral_rate": neutral_rate,
            "buy_predictions": predicted_counts["B"],
            "sell_predictions": predicted_counts["S"],
            "neutral_predictions": predicted_counts["N"],
        }

        horizon_results.append(horizon_result)

        print(
            f"{horizon:2d} candles -> "
            f"records={total} | "
            f"overall={overall_accuracy:.2f}% | "
            f"directional={directional_accuracy:.2f}% | "
            f"directional-F1={directional_f1:.2f}% | "
            f"BUY precision={buy_precision:.2f}% | "
            f"SELL precision={sell_precision:.2f}% | "
            f"coverage={directional_coverage:.2f}% | "
            f"neutral={neutral_rate:.2f}%"
        )

    # ========================================================
    # AVERAGE METRICS
    # ========================================================

    avg_directional_accuracy = mean(
        x["directional_accuracy"]
        for x in horizon_results
    )

    avg_directional_f1 = mean(
        x["directional_f1"]
        for x in horizon_results
    )

    avg_buy_precision = mean(
        x["buy_precision"]
        for x in horizon_results
    )

    avg_sell_precision = mean(
        x["sell_precision"]
        for x in horizon_results
    )

    avg_coverage = mean(
        x["directional_coverage"]
        for x in horizon_results
    )

    avg_neutral_rate = mean(
        x["neutral_rate"]
        for x in horizon_results
    )

    avg_overall_accuracy = mean(
        x["overall_accuracy"]
        for x in horizon_results
    )

    # --------------------------------------------------------
    # Directional balance
    # --------------------------------------------------------

    directional_balance = (
        100.0
        - abs(
            avg_buy_precision
            - avg_sell_precision
        )
    )

    # --------------------------------------------------------
    # Practical directional score
    #
    # Priority:
    #   directional accuracy
    #   directional F1
    #   coverage
    #   BUY/SELL balance
    #
    # Coverage prevents thresholds with almost no signals
    # from automatically winning.
    # --------------------------------------------------------

    directional_score = (
        avg_directional_accuracy * 0.35
        + avg_directional_f1 * 0.30
        + avg_coverage * 0.20
        + directional_balance * 0.15
    )

    print()
    print(
        f"Average directional accuracy : "
        f"{avg_directional_accuracy:.2f}%"
    )

    print(
        f"Average directional F1       : "
        f"{avg_directional_f1:.2f}%"
    )

    print(
        f"Average BUY precision        : "
        f"{avg_buy_precision:.2f}%"
    )

    print(
        f"Average SELL precision       : "
        f"{avg_sell_precision:.2f}%"
    )

    print(
        f"Directional coverage         : "
        f"{avg_coverage:.2f}%"
    )

    print(
        f"Average neutral rate         : "
        f"{avg_neutral_rate:.2f}%"
    )

    print(
        f"Directional balance          : "
        f"{directional_balance:.2f}"
    )

    print(
        f"Directional validation score : "
        f"{directional_score:.2f}"
    )

    results.append(
        {
            "threshold": threshold,
            "avg_directional_accuracy":
                avg_directional_accuracy,
            "avg_directional_f1":
                avg_directional_f1,
            "avg_buy_precision":
                avg_buy_precision,
            "avg_sell_precision":
                avg_sell_precision,
            "avg_coverage":
                avg_coverage,
            "avg_neutral_rate":
                avg_neutral_rate,
            "directional_balance":
                directional_balance,
            "overall_accuracy":
                avg_overall_accuracy,
            "score":
                directional_score,
            "horizons":
                horizon_results,
        }
    )

    print()


# ============================================================
# RANKING
# ============================================================

results.sort(
    key=lambda x: x["score"],
    reverse=True
)


print("=" * 78)
print("DIRECTIONAL VALIDATION RANKING")
print("=" * 78)

print(
    "Rank | Threshold | Directional | Dir-F1 | "
    "BUY Prec | SELL Prec | Coverage | Score"
)

print("-" * 78)

for index, result in enumerate(results, start=1):

    print(
        f"{index:02d}.  | "
        f"±{result['threshold']:.2f}%    | "
        f"{result['avg_directional_accuracy']:10.2f}% | "
        f"{result['avg_directional_f1']:7.2f}% | "
        f"{result['avg_buy_precision']:8.2f}% | "
        f"{result['avg_sell_precision']:9.2f}% | "
        f"{result['avg_coverage']:8.2f}% | "
        f"{result['score']:6.2f}"
    )


# ============================================================
# FINAL RESULT
# ============================================================

best = results[0]

print()
print("=" * 78)
print("V3.2.2 DIRECTIONAL VALIDATION RESULT")
print("=" * 78)

print()
print("Previous v3.1 threshold : ±0.02%")
print(
    "Best directional candidate : "
    f"±{best['threshold']:.2f}%"
)

print(
    "Directional validation score : "
    f"{best['score']:.2f}"
)

print(
    "Directional accuracy : "
    f"{best['avg_directional_accuracy']:.2f}%"
)

print(
    "Directional F1 : "
    f"{best['avg_directional_f1']:.2f}%"
)

print(
    "BUY precision : "
    f"{best['avg_buy_precision']:.2f}%"
)

print(
    "SELL precision : "
    f"{best['avg_sell_precision']:.2f}%"
)

print(
    "Directional coverage : "
    f"{best['avg_coverage']:.2f}%"
)

print()

print(
    "IMPORTANT: This validation does NOT change MLAI v3.1."
)

print(
    "IMPORTANT: The result is historical evidence only."
)

print(
    "IMPORTANT: A higher directional score does NOT guarantee"
)

print(
    "future trading performance."
)

# ============================================================
# SAVE VALIDATION REPORT
# ============================================================

output = {
    "engine": "MLAI v3.2.2",
    "market_file": MARKET_FILE,
    "window": WINDOW,
    "horizons": HORIZONS,
    "thresholds": THRESHOLDS,
    "best_candidate": best,
    "all_results": results,
}

with open(
    "mlai_v322_directional_validation.bin",
    "wb"
) as f:
    pickle.dump(output, f)


with open(
    "MLAI_V322_DIRECTIONAL_VALIDATION_REPORT.md",
    "w",
    encoding="utf-8"
) as f:

    f.write("# MLAI v3.2.2 Directional Validation Report\n\n")

    f.write(
        "## Purpose\n\n"
        "Validate whether the fine-grained historical "
        "threshold is useful for BUY/SELL directional "
        "classification rather than winning primarily "
        "because of Neutral classification.\n\n"
    )

    f.write("## Best Candidate\n\n")

    f.write(
        f"- Threshold: ±{best['threshold']:.2f}%\n"
    )

    f.write(
        f"- Directional accuracy: "
        f"{best['avg_directional_accuracy']:.2f}%\n"
    )

    f.write(
        f"- Directional F1: "
        f"{best['avg_directional_f1']:.2f}%\n"
    )

    f.write(
        f"- BUY precision: "
        f"{best['avg_buy_precision']:.2f}%\n"
    )

    f.write(
        f"- SELL precision: "
        f"{best['avg_sell_precision']:.2f}%\n"
    )

    f.write(
        f"- Directional coverage: "
        f"{best['avg_coverage']:.2f}%\n"
    )

    f.write(
        f"- Validation score: "
        f"{best['score']:.2f}\n\n"
    )

    f.write("## Ranking\n\n")

    f.write(
        "| Rank | Threshold | Directional Accuracy | "
        "Directional F1 | BUY Precision | SELL Precision | "
        "Coverage | Score |\n"
    )

    f.write(
        "|---:|---:|---:|---:|---:|---:|---:|---:|\n"
    )

    for index, result in enumerate(results, start=1):

        f.write(
            f"| {index} | "
            f"±{result['threshold']:.2f}% | "
            f"{result['avg_directional_accuracy']:.2f}% | "
            f"{result['avg_directional_f1']:.2f}% | "
            f"{result['avg_buy_precision']:.2f}% | "
            f"{result['avg_sell_precision']:.2f}% | "
            f"{result['avg_coverage']:.2f}% | "
            f"{result['score']:.2f} |\n"
        )

    f.write(
        "\n## Safety\n\n"
        "- market_data.bin was read only.\n"
        "- MLAI v3.1 was not modified.\n"
        "- Existing learning memory was not modified.\n"
        "- No classification threshold was applied to v3.1.\n"
        "- This is historical validation, not a future performance guarantee.\n"
    )


print()
print("PASS: mlai_v322_directional_validation.bin saved.")
print("PASS: MLAI_V322_DIRECTIONAL_VALIDATION_REPORT.md saved.")
print()
print("=" * 78)
print("MLAI v3.2.2 DIRECTIONAL VALIDATION COMPLETED")
print("=" * 78)
print()
print(
    f"Recommended directional candidate: "
    f"±{best['threshold']:.2f}%"
)
print(
    f"Directional validation score: "
    f"{best['score']:.2f}"
)
print()
print("PASS: v3.1 remains unchanged.")
print("PASS: market_data.bin remains unchanged.")
print("PASS: Existing learning memory remains unchanged.")
print()
print("NEXT STEP:")
print(
    "Review the directional validation result before "
    "changing any v3.1 classification logic."
)
