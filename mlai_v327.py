import os
import pickle
import math
import random
from collections import Counter


# ============================================================
# MLAI v3.2.7
# SIGNAL INTEGRITY + BASELINE VALIDATION
#
# PURPOSE:
#   Determine whether the current historical prediction rule
#   contains genuine directional information beyond simple
#   baseline strategies.
#
# IMPORTANT:
#   - Does NOT modify market_data.bin
#   - Does NOT modify MLAI v3.1
#   - Does NOT modify existing learning memory
#   - Does NOT change production classification logic
#   - Does NOT select a production threshold
#
# THIS VERSION IS AN AUDIT.
#
# The previous v3.2.6 used:
#
#     60-candle window return -> BUY/SELL/NEUTRAL
#
# as the prediction.
#
# v3.2.7 explicitly identifies that predictor as a
# MOMENTUM BASELINE and compares it against simpler baselines.
# ============================================================


MARKET_FILE = "market_data.bin"

CURRENT_WINDOW = 60
HORIZONS = [4, 8, 16]

THRESHOLDS = [
    0.0015,
    0.0016,
    0.0017,
    0.0018,
    0.0019,
    0.0020,
    0.0021,
    0.0022,
    0.0023,
    0.0024,
]

VALIDATION_RATIO = 0.30
WINDOW_COUNT = 4

RANDOM_SEED = 327

OUTPUT_BIN = "mlai_v327_signal_integrity.bin"
OUTPUT_REPORT = "MLAI_V327_SIGNAL_INTEGRITY_REPORT.md"


# ============================================================
# UTILITIES
# ============================================================

def pct(value):
    return f"{value * 100:.2f}%"


def safe_div(a, b):
    return a / b if b else 0.0


def harmonic_mean(a, b):
    if a + b == 0:
        return 0.0
    return 2.0 * a * b / (a + b)


def classify_return(return_value, threshold):

    if return_value >= threshold:
        return "BUY"

    if return_value <= -threshold:
        return "SELL"

    return "NEUTRAL"


# ============================================================
# LOAD DATA
# ============================================================

print()
print("=" * 78)
print("MLAI v3.2.7 SIGNAL INTEGRITY + BASELINE VALIDATION")
print("=" * 78)
print()

print("Purpose:")
print("Determine whether the current prediction rule contains")
print("genuine directional information beyond trivial baselines.")
print()

print(f"Market file    : {MARKET_FILE}")
print(f"Current window : {CURRENT_WINDOW}")
print(f"Horizons       : {HORIZONS}")
print(
    "Thresholds     : "
    + ", ".join(f"±{t * 100:.2f}%" for t in THRESHOLDS)
)
print(f"Validation     : {VALIDATION_RATIO:.0%}")
print(f"Windows        : {WINDOW_COUNT}")
print()

if not os.path.exists(MARKET_FILE):
    raise FileNotFoundError(
        f"{MARKET_FILE} was not found."
    )

with open(MARKET_FILE, "rb") as f:
    market_data = pickle.load(f)

print("PASS: market_data.bin loaded.")
print(f"Data type: {type(market_data).__name__}")


# ============================================================
# EXTRACT CLOSES
# ============================================================

def extract_close_prices(data):

    candidates = []

    if isinstance(data, dict):

        for key in [
            "candles",
            "data",
            "prices",
            "market_data",
            "historical_data",
        ]:

            if key in data and isinstance(data[key], list):
                candidates = data[key]
                break

        if not candidates:

            if all(isinstance(v, dict) for v in data.values()):
                candidates = list(data.values())

    elif isinstance(data, list):

        candidates = data

    closes = []

    for candle in candidates:

        if not isinstance(candle, dict):
            continue

        value = None

        for key in [
            "close",
            "Close",
            "c",
        ]:

            if key in candle:
                value = candle[key]
                break

        if value is None:
            continue

        try:

            value = float(value)

            if math.isfinite(value) and value > 0:
                closes.append(value)

        except Exception:
            pass

    return closes


closes = extract_close_prices(market_data)

if not closes:
    raise RuntimeError(
        "Could not extract valid close prices."
    )

print()
print("PASS: Close prices extracted.")
print(f"Valid close prices: {len(closes)}")

print()
print("PASS: market_data.bin will NOT be modified.")
print("PASS: MLAI v3.1 will NOT be modified.")
print("PASS: Existing learning memory will NOT be modified.")


# ============================================================
# CHRONOLOGICAL SPLIT
# ============================================================

n = len(closes)

validation_start = int(
    n * (1.0 - VALIDATION_RATIO)
)

validation_length = n - validation_start

window_size = validation_length // WINDOW_COUNT

if validation_start <= CURRENT_WINDOW:
    raise RuntimeError(
        "Insufficient calibration history."
    )

if window_size <= max(HORIZONS):
    raise RuntimeError(
        "Validation windows are too small."
    )


print()
print("=" * 78)
print("CHRONOLOGICAL VALIDATION WINDOWS")
print("-" * 78)

print(
    f"Calibration/reference candles : "
    f"{validation_start}"
)

print(
    f"Validation candles            : "
    f"{validation_length}"
)

windows = []

for w in range(WINDOW_COUNT):

    start = validation_start + w * window_size

    if w == WINDOW_COUNT - 1:
        end = n
    else:
        end = validation_start + (w + 1) * window_size

    windows.append(
        {
            "window": w + 1,
            "start": start,
            "end": end,
        }
    )

    print(
        f"Window {w + 1}: "
        f"{start} -> {end - 1} "
        f"({end - start} candles)"
    )

print()
print("PASS: validation windows are chronological.")


# ============================================================
# RECORD GENERATION
# ============================================================

def build_records(start, end, threshold, horizon):

    records = []

    first_i = max(
        CURRENT_WINDOW,
        start,
    )

    last_i = min(
        end - horizon - 1,
        n - horizon - 1,
    )

    for i in range(first_i, last_i + 1):

        current_close = closes[i]

        if current_close <= 0:
            continue

        future_close = closes[i + horizon]

        future_return = (
            future_close - current_close
        ) / current_close

        actual = classify_return(
            future_return,
            threshold,
        )

        # ----------------------------------------------------
        # BASELINE 1:
        # Always NEUTRAL
        # ----------------------------------------------------

        always_neutral = "NEUTRAL"

        # ----------------------------------------------------
        # BASELINE 2:
        # Last candle direction
        #
        # Uses only:
        # close[i] vs close[i-1]
        # ----------------------------------------------------

        previous_close = closes[i - 1]

        if previous_close > 0:

            last_return = (
                current_close - previous_close
            ) / previous_close

            last_candle_prediction = classify_return(
                last_return,
                threshold,
            )

        else:

            last_candle_prediction = "NEUTRAL"

        # ----------------------------------------------------
        # BASELINE 3:
        # Current 60-candle momentum
        #
        # This is the exact prediction approach previously
        # used by v3.2.6.
        #
        # It is therefore explicitly called MOMENTUM_BASELINE.
        # ----------------------------------------------------

        window_start = (
            i - CURRENT_WINDOW + 1
        )

        first_window_close = closes[
            window_start
        ]

        if first_window_close <= 0:
            continue

        window_return = (
            current_close -
            first_window_close
        ) / first_window_close

        momentum_prediction = classify_return(
            window_return,
            threshold,
        )

        records.append(
            {
                "index": i,
                "horizon": horizon,
                "actual": actual,
                "always_neutral": always_neutral,
                "last_candle": last_candle_prediction,
                "momentum": momentum_prediction,
            }
        )

    return records


# ============================================================
# METRICS
# ============================================================

def confusion_matrix(records, prediction_key):

    classes = [
        "BUY",
        "SELL",
        "NEUTRAL",
    ]

    matrix = {
        actual: {
            predicted: 0
            for predicted in classes
        }
        for actual in classes
    }

    for r in records:

        actual = r["actual"]
        predicted = r[prediction_key]

        matrix[actual][predicted] += 1

    return matrix


def calculate_metrics(records, prediction_key):

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
            "target_coverage": 0.0,
            "prediction_coverage": 0.0,
        }

    classes = [
        "BUY",
        "SELL",
        "NEUTRAL",
    ]

    matrix = confusion_matrix(
        records,
        prediction_key,
    )

    total = len(records)

    correct = sum(
        matrix[c][c]
        for c in classes
    )

    accuracy = safe_div(
        correct,
        total,
    )

    recalls = []

    f1s = []

    precisions = {}

    recalls_by_class = {}

    for cls in classes:

        tp = matrix[cls][cls]

        fp = sum(
            matrix[actual][cls]
            for actual in classes
            if actual != cls
        )

        fn = sum(
            matrix[cls][predicted]
            for predicted in classes
            if predicted != cls
        )

        precision = safe_div(
            tp,
            tp + fp,
        )

        recall = safe_div(
            tp,
            tp + fn,
        )

        f1 = harmonic_mean(
            precision,
            recall,
        )

        precisions[cls] = precision
        recalls_by_class[cls] = recall

        recalls.append(recall)
        f1s.append(f1)

    balanced_accuracy = (
        sum(recalls) / len(recalls)
    )

    macro_f1 = (
        sum(f1s) / len(f1s)
    )

    directional_records = [
        r
        for r in records
        if r["actual"] != "NEUTRAL"
    ]

    directional_correct = sum(
        1
        for r in directional_records
        if r[prediction_key] == r["actual"]
    )

    directional_accuracy = safe_div(
        directional_correct,
        len(directional_records),
    )

    directional_f1 = (
        precisions["BUY"]
        * 0.0
    )

    directional_f1_values = []

    for cls in ["BUY", "SELL"]:

        directional_f1_values.append(
            harmonic_mean(
                precisions[cls],
                recalls_by_class[cls],
            )
        )

    directional_f1 = (
        sum(directional_f1_values)
        / len(directional_f1_values)
    )

    target_directional = sum(
        1
        for r in records
        if r["actual"] != "NEUTRAL"
    )

    predicted_directional = sum(
        1
        for r in records
        if r[prediction_key] != "NEUTRAL"
    )

    return {
        "accuracy": accuracy,
        "balanced_accuracy": balanced_accuracy,
        "macro_f1": macro_f1,
        "directional_accuracy": directional_accuracy,
        "directional_f1": directional_f1,
        "buy_precision": precisions["BUY"],
        "sell_precision": precisions["SELL"],
        "buy_recall": recalls_by_class["BUY"],
        "sell_recall": recalls_by_class["SELL"],
        "target_coverage": safe_div(
            target_directional,
            total,
        ),
        "prediction_coverage": safe_div(
            predicted_directional,
            total,
        ),
    }


# ============================================================
# RANDOM BASELINE
# ============================================================

random_generator = random.Random(
    RANDOM_SEED
)


def add_random_predictions(records):

    for r in records:

        r["random"] = random_generator.choice(
            [
                "BUY",
                "SELL",
                "NEUTRAL",
            ]
        )

    return records


# ============================================================
# MAJORITY CLASS BASELINE
# ============================================================

def majority_prediction(records):

    counts = Counter(
        r["actual"]
        for r in records
    )

    if not counts:
        return "NEUTRAL"

    return counts.most_common(1)[0][0]


def add_majority_prediction(
    records,
    majority_class,
):

    for r in records:
        r["majority"] = majority_class

    return records


# ============================================================
# TEST
# ============================================================

results = []

print()
print("=" * 78)
print("SIGNAL INTEGRITY TEST")
print("=" * 78)

print()
print(
    "IMPORTANT:"
)
print(
    "The v3.2.6 predictor is now explicitly treated as"
)
print(
    "a MOMENTUM BASELINE."
)
print()
print(
    "We will determine whether it beats simpler baselines."
)


for threshold in THRESHOLDS:

    print()
    print("=" * 78)
    print(
        f"THRESHOLD ±{threshold * 100:.2f}%"
    )
    print("-" * 78)

    threshold_result = {
        "threshold": threshold,
        "threshold_label":
            f"±{threshold * 100:.2f}%",
        "horizons": {},
    }

    for horizon in HORIZONS:

        horizon_results = []

        print()
        print(
            f"HORIZON {horizon} CANDLES"
        )
        print("-" * 78)

        for window in windows:

            records = build_records(
                window["start"],
                window["end"],
                threshold,
                horizon,
            )

            add_random_predictions(
                records
            )

            majority_class = majority_prediction(
                records
            )

            add_majority_prediction(
                records,
                majority_class,
            )

            neutral_metrics = calculate_metrics(
                records,
                "always_neutral",
            )

            majority_metrics = calculate_metrics(
                records,
                "majority",
            )

            last_metrics = calculate_metrics(
                records,
                "last_candle",
            )

            momentum_metrics = calculate_metrics(
                records,
                "momentum",
            )

            random_metrics = calculate_metrics(
                records,
                "random",
            )

            horizon_results.append(
                {
                    "window": window["window"],
                    "records": len(records),
                    "neutral": neutral_metrics,
                    "majority": majority_metrics,
                    "last_candle": last_metrics,
                    "momentum": momentum_metrics,
                    "random": random_metrics,
                }
            )

            print(
                f"Window {window['window']} | "
                f"records={len(records)} | "
                f"Momentum dir="
                f"{pct(momentum_metrics['directional_accuracy'])} | "
                f"Momentum F1="
                f"{pct(momentum_metrics['directional_f1'])} | "
                f"BUY="
                f"{pct(momentum_metrics['buy_precision'])} | "
                f"SELL="
                f"{pct(momentum_metrics['sell_precision'])} | "
                f"Last="
                f"{pct(last_metrics['directional_accuracy'])} | "
                f"Random="
                f"{pct(random_metrics['directional_accuracy'])}"
            )

        threshold_result[
            "horizons"
        ][horizon] = horizon_results


    # ========================================================
    # AGGREGATE MOMENTUM VS BASELINES
    # ========================================================

    all_momentum = []
    all_last = []
    all_random = []
    all_majority = []

    for horizon in HORIZONS:

        for row in threshold_result[
            "horizons"
        ][horizon]:

            all_momentum.append(
                row["momentum"]
            )

            all_last.append(
                row["last_candle"]
            )

            all_random.append(
                row["random"]
            )

            all_majority.append(
                row["majority"]
            )

    def average_metric(
        rows,
        key,
    ):

        return (
            sum(
                r[key]
                for r in rows
            )
            / len(rows)
        )

    momentum_average = {
        key: average_metric(
            all_momentum,
            key,
        )
        for key in [
            "accuracy",
            "balanced_accuracy",
            "macro_f1",
            "directional_accuracy",
            "directional_f1",
            "buy_precision",
            "sell_precision",
            "buy_recall",
            "sell_recall",
            "target_coverage",
            "prediction_coverage",
        ]
    }

    last_average = {
        key: average_metric(
            all_last,
            key,
        )
        for key in [
            "accuracy",
            "balanced_accuracy",
            "macro_f1",
            "directional_accuracy",
            "directional_f1",
            "buy_precision",
            "sell_precision",
        ]
    }

    random_average = {
        key: average_metric(
            all_random,
            key,
        )
        for key in [
            "accuracy",
            "balanced_accuracy",
            "macro_f1",
            "directional_accuracy",
            "directional_f1",
        ]
    }

    majority_average = {
        key: average_metric(
            all_majority,
            key,
        )
        for key in [
            "accuracy",
            "balanced_accuracy",
            "macro_f1",
            "directional_accuracy",
            "directional_f1",
        ]
    }

    # --------------------------------------------------------
    # Improvement over last-candle baseline.
    # --------------------------------------------------------

    directional_lift = (
        momentum_average[
            "directional_accuracy"
        ]
        -
        last_average[
            "directional_accuracy"
        ]
    )

    f1_lift = (
        momentum_average[
            "directional_f1"
        ]
        -
        last_average[
            "directional_f1"
        ]
    )

    threshold_result[
        "momentum"
    ] = momentum_average

    threshold_result[
        "last_candle"
    ] = last_average

    threshold_result[
        "random"
    ] = random_average

    threshold_result[
        "majority"
    ] = majority_average

    threshold_result[
        "directional_lift_vs_last"
    ] = directional_lift

    threshold_result[
        "f1_lift_vs_last"
    ] = f1_lift

    results.append(
        threshold_result
    )

    print()
    print(
        "AGGREGATE"
    )
    print("-" * 78)

    print(
        "Momentum directional accuracy : "
        f"{pct(momentum_average['directional_accuracy'])}"
    )

    print(
        "Last-candle directional accuracy: "
        f"{pct(last_average['directional_accuracy'])}"
    )

    print(
        "Random directional accuracy    : "
        f"{pct(random_average['directional_accuracy'])}"
    )

    print(
        "Majority directional accuracy  : "
        f"{pct(majority_average['directional_accuracy'])}"
    )

    print(
        "Momentum directional F1        : "
        f"{pct(momentum_average['directional_f1'])}"
    )

    print(
        "Momentum F1 lift vs last candle: "
        f"{pct(f1_lift)}"
    )

    print(
        "Momentum directional lift      : "
        f"{pct(directional_lift)}"
    )


# ============================================================
# RANKING BY ACTUAL EVIDENCE
# ============================================================

ranking = sorted(
    results,
    key=lambda x: (
        x["momentum"]["directional_f1"],
        x["directional_lift_vs_last"],
    ),
    reverse=True,
)


print()
print("=" * 78)
print("SIGNAL INTEGRITY RANKING")
print("=" * 78)

print()
print(
    "Rank | Threshold | Momentum Dir | "
    "Momentum F1 | Last Dir | F1 Lift | "
    "BUY Prec | SELL Prec"
)

print("-" * 95)

for rank, result in enumerate(
    ranking,
    start=1,
):

    m = result["momentum"]
    l = result["last_candle"]

    print(
        f"{rank:02d}.  | "
        f"{result['threshold_label']:<9} | "
        f"{pct(m['directional_accuracy']):>12} | "
        f"{pct(m['directional_f1']):>11} | "
        f"{pct(l['directional_accuracy']):>8} | "
        f"{pct(result['f1_lift_vs_last']):>7} | "
        f"{pct(m['buy_precision']):>8} | "
        f"{pct(m['sell_precision']):>9}"
    )


# ============================================================
# FINAL SIGNAL VERDICT
# ============================================================

best = ranking[0]

best_momentum = best["momentum"]
best_last = best["last_candle"]
best_random = best["random"]

directional_lift = (
    best_momentum[
        "directional_accuracy"
    ]
    -
    best_last[
        "directional_accuracy"
    ]
)

f1_lift = (
    best_momentum[
        "directional_f1"
    ]
    -
    best_last[
        "directional_f1"
    ]
)

# ------------------------------------------------------------
# Conservative evidence classification.
#
# We do NOT call something predictive merely because it is
# above 50%.
# ------------------------------------------------------------

if (
    directional_lift >= 0.05
    and f1_lift >= 0.05
    and best_momentum[
        "buy_precision"
    ] >= 0.50
    and best_momentum[
        "sell_precision"
    ] >= 0.50
):

    verdict = "SIGNAL DETECTED"

elif (
    directional_lift >= 0.02
    or f1_lift >= 0.02
):

    verdict = "WEAK SIGNAL"

else:

    verdict = "NO MEANINGFUL SIGNAL"


print()
print("=" * 78)
print("V3.2.7 FINAL SIGNAL INTEGRITY RESULT")
print("=" * 78)
print()

print(
    f"Best threshold for diagnostic testing : "
    f"{best['threshold_label']}"
)

print(
    f"Momentum directional accuracy         : "
    f"{pct(best_momentum['directional_accuracy'])}"
)

print(
    f"Momentum directional F1               : "
    f"{pct(best_momentum['directional_f1'])}"
)

print(
    f"Momentum BUY precision                : "
    f"{pct(best_momentum['buy_precision'])}"
)

print(
    f"Momentum SELL precision               : "
    f"{pct(best_momentum['sell_precision'])}"
)

print(
    f"Last-candle directional accuracy      : "
    f"{pct(best_last['directional_accuracy'])}"
)

print(
    f"Random directional accuracy           : "
    f"{pct(best_random['directional_accuracy'])}"
)

print(
    f"Directional lift vs last candle       : "
    f"{pct(directional_lift)}"
)

print(
    f"F1 lift vs last candle                : "
    f"{pct(f1_lift)}"
)

print()
print(
    f"FINAL DIAGNOSTIC VERDICT: "
    f"{verdict}"
)

print()
print("=" * 78)
print("WHAT THIS RESULT MEANS")
print("=" * 78)
print()

if verdict == "SIGNAL DETECTED":

    print(
        "The current momentum representation shows evidence"
    )
    print(
        "above the selected baseline comparisons."
    )
    print(
        "This does NOT yet prove a profitable trading system."
    )
    print(
        "The next step can investigate the actual candle"
    )
    print(
        "language representation."
    )

elif verdict == "WEAK SIGNAL":

    print(
        "The current representation contains some directional"
    )
    print(
        "information, but the evidence is not strong enough"
    )
    print(
        "to call it a reliable predictive engine."
    )
    print(
        "The candle-language representation needs improvement"
    )
    print(
        "before production classification is changed."
    )

else:

    print(
        "The current 60-candle momentum representation does"
    )
    print(
        "not demonstrate sufficient predictive advantage"
    )
    print(
        "over simple baselines."
    )
    print()
    print(
        "Therefore we MUST NOT pretend that threshold tuning"
    )
    print(
        "has solved the prediction problem."
    )
    print()
    print(
        "The next engineering task would be to build the"
    )
    print(
        "actual candle-language feature representation."
    )


print()
print("=" * 78)
print("SAFETY CHECK")
print("=" * 78)
print()

print("PASS: market_data.bin unchanged.")
print("PASS: MLAI v3.1 unchanged.")
print("PASS: Existing learning memory unchanged.")
print("PASS: No production threshold changed.")
print("PASS: No trading decision system changed.")


# ============================================================
# SAVE RESULT
# ============================================================

output_data = {
    "engine": "MLAI v3.2.7",
    "purpose": "signal integrity and baseline validation",
    "market_file": MARKET_FILE,
    "current_window": CURRENT_WINDOW,
    "horizons": HORIZONS,
    "thresholds": THRESHOLDS,
    "validation_ratio": VALIDATION_RATIO,
    "window_count": WINDOW_COUNT,
    "validation_start": validation_start,
    "windows": windows,
    "results": results,
    "ranking": ranking,
    "best_candidate": best,
    "verdict": verdict,
}

with open(
    OUTPUT_BIN,
    "wb",
) as f:

    pickle.dump(
        output_data,
        f,
        protocol=pickle.HIGHEST_PROTOCOL,
    )

print()
print(
    f"PASS: {OUTPUT_BIN} saved."
)


# ============================================================
# MARKDOWN REPORT
# ============================================================

report = []

report.append(
    "# MLAI v3.2.7 Signal Integrity + Baseline Validation"
)

report.append("")

report.append(
    "## Purpose"
)

report.append("")

report.append(
    "This validation determines whether the current 60-candle "
    "momentum representation contains meaningful directional "
    "information beyond simple baseline strategies."
)

report.append("")

report.append(
    "## Important Finding About v3.2.6"
)

report.append("")

report.append(
    "The v3.2.6 prediction was based on the return of the "
    "current 60-candle window. Therefore it is treated here "
    "as a MOMENTUM BASELINE rather than as the MLAI learned "
    "candle-language engine."
)

report.append("")

report.append(
    "## Configuration"
)

report.append("")

report.append(
    f"- Market file: `{MARKET_FILE}`"
)

report.append(
    f"- Valid closes: {len(closes)}"
)

report.append(
    f"- Current window: {CURRENT_WINDOW}"
)

report.append(
    f"- Horizons: {HORIZONS}"
)

report.append(
    f"- Validation ratio: {VALIDATION_RATIO:.0%}"
)

report.append(
    f"- Validation windows: {WINDOW_COUNT}"
)

report.append("")

report.append(
    "## Threshold Ranking"
)

report.append("")

report.append(
    "| Rank | Threshold | Momentum Directional | "
    "Momentum Dir-F1 | Last Candle Directional | "
    "F1 Lift | BUY Precision | SELL Precision |"
)

report.append(
    "|---:|---:|---:|---:|---:|---:|---:|---:|"
)

for rank, result in enumerate(
    ranking,
    start=1,
):

    m = result["momentum"]
    l = result["last_candle"]

    report.append(
        f"| {rank} "
        f"| {result['threshold_label']} "
        f"| {pct(m['directional_accuracy'])} "
        f"| {pct(m['directional_f1'])} "
        f"| {pct(l['directional_accuracy'])} "
        f"| {pct(result['f1_lift_vs_last'])} "
        f"| {pct(m['buy_precision'])} "
        f"| {pct(m['sell_precision'])} |"
    )

report.append("")

report.append(
    "## Final Diagnostic Result"
)

report.append("")

report.append(
    f"- Best diagnostic threshold: "
    f"**{best['threshold_label']}**"
)

report.append(
    f"- Momentum directional accuracy: "
    f"**{pct(best_momentum['directional_accuracy'])}**"
)

report.append(
    f"- Momentum directional F1: "
    f"**{pct(best_momentum['directional_f1'])}**"
)

report.append(
    f"- Last-candle directional accuracy: "
    f"**{pct(best_last['directional_accuracy'])}**"
)

report.append(
    f"- Random directional accuracy: "
    f"**{pct(best_random['directional_accuracy'])}**"
)

report.append(
    f"- Directional lift: "
    f"**{pct(directional_lift)}**"
)

report.append(
    f"- F1 lift: "
    f"**{pct(f1_lift)}**"
)

report.append("")

report.append(
    f"### Verdict: {verdict}"
)

report.append("")

if verdict == "SIGNAL DETECTED":

    report.append(
        "The current representation shows evidence above "
        "the selected baseline comparisons. This does not "
        "guarantee future profitability."
    )

elif verdict == "WEAK SIGNAL":

    report.append(
        "The current representation shows limited evidence "
        "of directional information, but not enough to "
        "justify treating it as a reliable predictive engine."
    )

else:

    report.append(
        "The current representation does not demonstrate "
        "sufficient predictive advantage over simple baselines."
    )

report.append("")

report.append(
    "## Safety"
)

report.append("")

report.append(
    "- `market_data.bin` was not modified."
)

report.append(
    "- MLAI v3.1 was not modified."
)

report.append(
    "- Existing learning memory was not modified."
)

report.append(
    "- No production classification threshold was changed."
)

report.append(
    "- No trading decision system was changed."
)

report.append("")

with open(
    OUTPUT_REPORT,
    "w",
    encoding="utf-8",
) as f:

    f.write(
        "\n".join(report)
    )

print(
    f"PASS: {OUTPUT_REPORT} saved."
)

print()
print("=" * 78)
print("MLAI v3.2.7 SIGNAL INTEGRITY VALIDATION COMPLETED")
print("=" * 78)
print()
print(
    f"Diagnostic verdict: {verdict}"
)
print()
print(
    "IMPORTANT:"
)
print(
    "Do NOT modify MLAI v3.1 based solely on this test."
)
print()
print(
    "The purpose of this version is to establish whether"
)
print(
    "the current representation contains genuine signal."
)
print()