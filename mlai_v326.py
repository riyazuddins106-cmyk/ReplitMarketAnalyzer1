
import os
import pickle
import math
from collections import defaultdict


# ============================================================
# MLAI v3.2.6
# MULTI-WINDOW CHRONOLOGICAL ROBUSTNESS VALIDATION
#
# Purpose:
#   Test threshold robustness across multiple chronological
#   out-of-sample historical windows.
#
# IMPORTANT:
#   - Does NOT modify market_data.bin
#   - Does NOT modify MLAI v3.1
#   - Does NOT modify existing learning memory
#   - Does NOT change classification logic
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

# Split the unseen historical section into multiple windows.
WINDOW_COUNT = 4

OUTPUT_BIN = "mlai_v326_robustness_validation.bin"
OUTPUT_REPORT = "MLAI_V326_ROBUSTNESS_VALIDATION_REPORT.md"


# ============================================================
# UTILITIES
# ============================================================

def pct(value):
    return f"{value * 100:.2f}%"


def threshold_label(threshold):
    return f"±{threshold * 100:.2f}%"


def safe_div(a, b):
    return a / b if b else 0.0


def harmonic_mean(a, b):
    if a + b == 0:
        return 0.0
    return 2.0 * a * b / (a + b)


# ============================================================
# LOAD MARKET DATA
# ============================================================

print()
print("=" * 78)
print("MLAI v3.2.6 MULTI-WINDOW CHRONOLOGICAL ROBUSTNESS VALIDATION")
print("=" * 78)
print()
print("Purpose: determine whether threshold performance is robust")
print("across multiple chronological unseen historical periods.")
print()

print(f"Market file       : {MARKET_FILE}")
print(f"Current window    : {CURRENT_WINDOW}")
print(f"Horizons          : {HORIZONS}")
print(
    "Thresholds        : "
    + ", ".join(threshold_label(t) for t in THRESHOLDS)
)
print(f"Validation ratio  : {VALIDATION_RATIO:.0%}")
print(f"Validation windows: {WINDOW_COUNT}")
print()

if not os.path.exists(MARKET_FILE):
    raise FileNotFoundError(
        f"{MARKET_FILE} was not found in the current directory."
    )

with open(MARKET_FILE, "rb") as f:
    market_data = pickle.load(f)

print("PASS: market_data.bin loaded.")
print(f"Data type: {type(market_data).__name__}")


# ============================================================
# EXTRACT CLOSE PRICES
# ============================================================

def extract_close_prices(data):
    candidates = []

    if isinstance(data, dict):

        # Common possible candle containers.
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
            # Sometimes the dictionary itself is indexed by timestamp.
            if all(isinstance(v, dict) for v in data.values()):
                candidates = list(data.values())

    elif isinstance(data, list):
        candidates = data

    closes = []

    for candle in candidates:

        if isinstance(candle, dict):

            value = None

            for key in [
                "close",
                "Close",
                "c",
            ]:
                if key in candle:
                    value = candle[key]
                    break

            if value is not None:
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
        "Could not extract valid close prices from market_data.bin."
    )

print()
print("PASS: Close prices extracted.")
print(f"Valid close prices: {len(closes)}")

print()
print("PASS: Original market data will NOT be modified.")
print("PASS: MLAI v3.1 will NOT be modified.")
print("PASS: Existing learning memory will NOT be modified.")


# ============================================================
# CHRONOLOGICAL SPLIT
# ============================================================

n = len(closes)

validation_start = int(n * (1.0 - VALIDATION_RATIO))

if validation_start <= CURRENT_WINDOW:
    raise RuntimeError("Not enough historical data for validation.")

validation_length = n - validation_start

window_size = validation_length // WINDOW_COUNT

if window_size < max(HORIZONS) + 5:
    raise RuntimeError(
        "Validation windows are too small for the selected horizons."
    )


print()
print("=" * 78)
print("CHRONOLOGICAL VALIDATION WINDOWS")
print("-" * 78)

print(f"Calibration/reference candles : {validation_start}")
print(f"Total validation candles     : {validation_length}")

windows = []

for w in range(WINDOW_COUNT):

    start = validation_start + (w * window_size)

    if w == WINDOW_COUNT - 1:
        end = n
    else:
        end = validation_start + ((w + 1) * window_size)

    windows.append(
        {
            "window": w + 1,
            "start": start,
            "end": end,
        }
    )

    print(
        f"Window {w + 1}: "
        f"index {start} -> {end - 1} "
        f"({end - start} candles)"
    )

print()
print("PASS: Validation windows are strictly chronological.")
print("PASS: Later validation data is kept separate from earlier data.")


# ============================================================
# CLASSIFICATION
# ============================================================

def classify_return(return_pct, threshold):

    if return_pct >= threshold:
        return "BUY"

    if return_pct <= -threshold:
        return "SELL"

    return "NEUTRAL"


# ============================================================
# METRICS
# ============================================================

def calculate_metrics(records):

    if not records:
        return {
            "overall": 0.0,
            "directional": 0.0,
            "directional_f1": 0.0,
            "buy_precision": 0.0,
            "sell_precision": 0.0,
            "target_coverage": 0.0,
            "prediction_coverage": 0.0,
            "macro_f1": 0.0,
        }

    labels = ["BUY", "SELL", "NEUTRAL"]

    correct = sum(
        1 for r in records if r["predicted"] == r["actual"]
    )

    overall = safe_div(correct, len(records))

    target_directional = sum(
        1 for r in records if r["actual"] != "NEUTRAL"
    )

    target_coverage = safe_div(
        target_directional,
        len(records),
    )

    predicted_directional = sum(
        1 for r in records if r["predicted"] != "NEUTRAL"
    )

    prediction_coverage = safe_div(
        predicted_directional,
        len(records),
    )

    directional_records = [
        r for r in records if r["actual"] != "NEUTRAL"
    ]

    directional_correct = sum(
        1
        for r in directional_records
        if r["predicted"] == r["actual"]
    )

    directional = safe_div(
        directional_correct,
        len(directional_records),
    )

    # Precision / recall / F1 for directional classes.
    f1_values = []

    precision_by_class = {}

    for cls in labels:

        tp = sum(
            1
            for r in records
            if r["actual"] == cls and r["predicted"] == cls
        )

        fp = sum(
            1
            for r in records
            if r["actual"] != cls and r["predicted"] == cls
        )

        fn = sum(
            1
            for r in records
            if r["actual"] == cls and r["predicted"] != cls
        )

        precision = safe_div(tp, tp + fp)
        recall = safe_div(tp, tp + fn)

        f1 = harmonic_mean(precision, recall)

        precision_by_class[cls] = precision
        f1_values.append(f1)

    macro_f1 = sum(f1_values) / len(f1_values)

    buy_precision = precision_by_class["BUY"]
    sell_precision = precision_by_class["SELL"]

    directional_f1_values = []

    for cls in ["BUY", "SELL"]:

        tp = sum(
            1
            for r in records
            if r["actual"] == cls and r["predicted"] == cls
        )

        fp = sum(
            1
            for r in records
            if r["actual"] != cls and r["predicted"] == cls
        )

        fn = sum(
            1
            for r in records
            if r["actual"] == cls and r["predicted"] != cls
        )

        precision = safe_div(tp, tp + fp)
        recall = safe_div(tp, tp + fn)

        directional_f1_values.append(
            harmonic_mean(precision, recall)
        )

    directional_f1 = (
        sum(directional_f1_values)
        / len(directional_f1_values)
    )

    return {
        "overall": overall,
        "directional": directional,
        "directional_f1": directional_f1,
        "buy_precision": buy_precision,
        "sell_precision": sell_precision,
        "target_coverage": target_coverage,
        "prediction_coverage": prediction_coverage,
        "macro_f1": macro_f1,
    }


# ============================================================
# BUILD WINDOW DATA
# ============================================================

def build_window_records(start, end, threshold):

    all_records = []

    for horizon in HORIZONS:

        horizon_records = []

        # Need enough candles before the validation point
        # to construct the 60-candle current window.
        first_i = max(
            CURRENT_WINDOW,
            start,
        )

        last_i = min(
            end - horizon,
            n - horizon - 1,
        )

        for i in range(first_i, last_i + 1):

            current_close = closes[i]
            future_close = closes[i + horizon]

            if current_close <= 0:
                continue

            future_return = (
                future_close - current_close
            ) / current_close

            actual = classify_return(
                future_return,
                threshold,
            )

            # The prediction model used here is intentionally
            # conservative and deterministic. It predicts the
            # direction of the current-window price displacement.
            #
            # This is NOT modifying MLAI v3.1.
            #
            # The purpose of v3.2.6 is threshold robustness
            # validation, not production-model replacement.

            window_start = i - CURRENT_WINDOW + 1

            window_closes = closes[
                window_start:i + 1
            ]

            first_close = window_closes[0]
            last_close = window_closes[-1]

            if first_close <= 0:
                continue

            window_return = (
                last_close - first_close
            ) / first_close

            predicted = classify_return(
                window_return,
                threshold,
            )

            horizon_records.append(
                {
                    "index": i,
                    "horizon": horizon,
                    "actual": actual,
                    "predicted": predicted,
                }
            )

        all_records.extend(horizon_records)

    return all_records


# ============================================================
# TEST EACH WINDOW
# ============================================================

all_results = []

print()
print("=" * 78)
print("MULTI-WINDOW THRESHOLD TESTING")
print("=" * 78)

for threshold in THRESHOLDS:

    print()
    print(
        "=" * 78
    )
    print(
        f"TESTING THRESHOLD {threshold_label(threshold)}"
    )
    print(
        "-" * 78
    )

    threshold_window_results = []

    for window in windows:

        records = build_window_records(
            window["start"],
            window["end"],
            threshold,
        )

        metrics = calculate_metrics(records)

        threshold_window_results.append(
            metrics
        )

        print(
            f"Window {window['window']} | "
            f"records={len(records)} | "
            f"directional={pct(metrics['directional'])} | "
            f"dir-F1={pct(metrics['directional_f1'])} | "
            f"BUY precision={pct(metrics['buy_precision'])} | "
            f"SELL precision={pct(metrics['sell_precision'])} | "
            f"target coverage={pct(metrics['target_coverage'])} | "
            f"prediction coverage={pct(metrics['prediction_coverage'])}"
        )

    # Average across windows.
    avg_directional = sum(
        r["directional"]
        for r in threshold_window_results
    ) / len(threshold_window_results)

    avg_dir_f1 = sum(
        r["directional_f1"]
        for r in threshold_window_results
    ) / len(threshold_window_results)

    avg_buy = sum(
        r["buy_precision"]
        for r in threshold_window_results
    ) / len(threshold_window_results)

    avg_sell = sum(
        r["sell_precision"]
        for r in threshold_window_results
    ) / len(threshold_window_results)

    avg_target_cov = sum(
        r["target_coverage"]
        for r in threshold_window_results
    ) / len(threshold_window_results)

    avg_prediction_cov = sum(
        r["prediction_coverage"]
        for r in threshold_window_results
    ) / len(threshold_window_results)

    # Stability:
    # 100 means identical directional accuracy across windows.
    values = [
        r["directional"]
        for r in threshold_window_results
    ]

    mean_value = (
        sum(values) / len(values)
        if values
        else 0.0
    )

    mean_abs_deviation = (
        sum(abs(v - mean_value) for v in values)
        / len(values)
        if values
        else 0.0
    )

    stability = max(
        0.0,
        100.0 - (mean_abs_deviation * 400.0),
    )

    # Combined robustness score.
    #
    # Favors:
    #   directional usefulness
    #   directional F1
    #   BUY/SELL precision
    #   stability
    #
    # Coverage is reported separately and does not dominate
    # the score.
    score = (
        avg_directional * 30.0
        + avg_dir_f1 * 25.0
        + ((avg_buy + avg_sell) / 2.0) * 20.0
        + (stability / 100.0) * 25.0
    )

    result = {
        "threshold": threshold,
        "threshold_label": threshold_label(threshold),
        "windows": threshold_window_results,
        "average_directional": avg_directional,
        "average_directional_f1": avg_dir_f1,
        "average_buy_precision": avg_buy,
        "average_sell_precision": avg_sell,
        "average_target_coverage": avg_target_cov,
        "average_prediction_coverage": avg_prediction_cov,
        "stability": stability,
        "score": score,
    }

    all_results.append(result)

    print()
    print(
        f"Average directional accuracy : "
        f"{pct(avg_directional)}"
    )
    print(
        f"Average directional F1       : "
        f"{pct(avg_dir_f1)}"
    )
    print(
        f"Average BUY precision        : "
        f"{pct(avg_buy)}"
    )
    print(
        f"Average SELL precision       : "
        f"{pct(avg_sell)}"
    )
    print(
        f"Average target coverage      : "
        f"{pct(avg_target_cov)}"
    )
    print(
        f"Average prediction coverage : "
        f"{pct(avg_prediction_cov)}"
    )
    print(
        f"Cross-window stability       : "
        f"{stability:.2f}"
    )
    print(
        f"Robustness score             : "
        f"{score:.2f}"
    )


# ============================================================
# RANKING
# ============================================================

ranking = sorted(
    all_results,
    key=lambda x: x["score"],
    reverse=True,
)

print()
print("=" * 78)
print("MULTI-WINDOW ROBUSTNESS RANKING")
print("=" * 78)

print(
    "Rank | Threshold | Directional | Dir-F1 | "
    "BUY Prec | SELL Prec | Target Cov | Pred Cov | Stability | Score"
)
print("-" * 100)

for idx, result in enumerate(ranking, start=1):

    print(
        f"{idx:02d}.  | "
        f"{result['threshold_label']:<9} | "
        f"{pct(result['average_directional']):>10} | "
        f"{pct(result['average_directional_f1']):>7} | "
        f"{pct(result['average_buy_precision']):>8} | "
        f"{pct(result['average_sell_precision']):>9} | "
        f"{pct(result['average_target_coverage']):>10} | "
        f"{pct(result['average_prediction_coverage']):>8} | "
        f"{result['stability']:>9.2f} | "
        f"{result['score']:>6.2f}"
    )


# ============================================================
# FINAL RESULT
# ============================================================

best = ranking[0]

print()
print("=" * 78)
print("V3.2.6 ROBUSTNESS VALIDATION RESULT")
print("=" * 78)
print()

print(
    f"Best multi-window candidate : "
    f"{best['threshold_label']}"
)

print(
    f"Robustness score            : "
    f"{best['score']:.2f}"
)

print(
    f"Average directional accuracy: "
    f"{pct(best['average_directional'])}"
)

print(
    f"Average directional F1      : "
    f"{pct(best['average_directional_f1'])}"
)

print(
    f"Average BUY precision       : "
    f"{pct(best['average_buy_precision'])}"
)

print(
    f"Average SELL precision      : "
    f"{pct(best['average_sell_precision'])}"
)

print(
    f"Average target coverage     : "
    f"{pct(best['average_target_coverage'])}"
)

print(
    f"Average prediction coverage: "
    f"{pct(best['average_prediction_coverage'])}"
)

print(
    f"Cross-window stability      : "
    f"{best['stability']:.2f}"
)

print()
print("IMPORTANT:")
print("This is historical evidence only.")
print("It does NOT guarantee future trading performance.")
print()
print("IMPORTANT:")
print("MLAI v3.1 classification logic has NOT been changed.")
print("market_data.bin has NOT been changed.")
print("Existing learning memory has NOT been changed.")


# ============================================================
# SAVE BINARY RESULT
# ============================================================

output_data = {
    "engine": "MLAI v3.2.6",
    "purpose": "multi-window chronological robustness validation",
    "market_file": MARKET_FILE,
    "current_window": CURRENT_WINDOW,
    "horizons": HORIZONS,
    "thresholds": THRESHOLDS,
    "validation_ratio": VALIDATION_RATIO,
    "window_count": WINDOW_COUNT,
    "validation_start": validation_start,
    "windows": windows,
    "ranking": ranking,
    "best_candidate": best,
}

with open(OUTPUT_BIN, "wb") as f:
    pickle.dump(
        output_data,
        f,
        protocol=pickle.HIGHEST_PROTOCOL,
    )

print()
print(f"PASS: {OUTPUT_BIN} saved.")


# ============================================================
# MARKDOWN REPORT
# ============================================================

report = []

report.append("# MLAI v3.2.6 Multi-Window Robustness Validation Report")
report.append("")
report.append(
    "This report evaluates historical threshold robustness across "
    "multiple chronological out-of-sample windows."
)
report.append("")

report.append("## Configuration")
report.append("")
report.append(f"- Market file: `{MARKET_FILE}`")
report.append(f"- Valid close prices: {len(closes)}")
report.append(f"- Current window: {CURRENT_WINDOW}")
report.append(f"- Horizons: {HORIZONS}")
report.append(f"- Validation ratio: {VALIDATION_RATIO:.0%}")
report.append(f"- Validation windows: {WINDOW_COUNT}")
report.append("")

report.append("## Validation Windows")
report.append("")

for window in windows:
    report.append(
        f"- Window {window['window']}: "
        f"index {window['start']} to {window['end'] - 1}"
    )

report.append("")

report.append("## Ranking")
report.append("")

report.append(
    "| Rank | Threshold | Directional | Dir-F1 | "
    "BUY Precision | SELL Precision | Target Coverage | "
    "Prediction Coverage | Stability | Score |"
)
report.append(
    "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
)

for idx, result in enumerate(ranking, start=1):

    report.append(
        f"| {idx} "
        f"| {result['threshold_label']} "
        f"| {pct(result['average_directional'])} "
        f"| {pct(result['average_directional_f1'])} "
        f"| {pct(result['average_buy_precision'])} "
        f"| {pct(result['average_sell_precision'])} "
        f"| {pct(result['average_target_coverage'])} "
        f"| {pct(result['average_prediction_coverage'])} "
        f"| {result['stability']:.2f} "
        f"| {result['score']:.2f} |"
    )

report.append("")
report.append("## Best Candidate")
report.append("")
report.append(
    f"**{best['threshold_label']}**"
)
report.append("")
report.append(
    f"Robustness score: **{best['score']:.2f}**"
)
report.append("")
report.append(
    "This is a historical robustness candidate only. "
    "It is not a guarantee of future trading performance."
)
report.append("")

report.append("## Safety")
report.append("")
report.append(
    "- MLAI v3.1 was not modified."
)
report.append(
    "- market_data.bin was not modified."
)
report.append(
    "- Existing learning memory was not modified."
)
report.append(
    "- No production classification threshold was changed."
)
report.append("")

with open(
    OUTPUT_REPORT,
    "w",
    encoding="utf-8",
) as f:
    f.write("\n".join(report))

print(f"PASS: {OUTPUT_REPORT} saved.")

print()
print("=" * 78)
print("MLAI v3.2.6 ROBUSTNESS VALIDATION COMPLETED")
print("=" * 78)
print()
print(
    f"Best multi-window candidate: "
    f"{best['threshold_label']}"
)
print(
    f"Robustness score           : "
    f"{best['score']:.2f}"
)
print()
print("NEXT STEP:")
print(
    "Compare the multi-window winner with the previous "
    "v3.2.5 corrected OOS result."
)
print(
    "Do NOT modify MLAI v3.1 until threshold robustness "
    "has been reviewed."
)
print()
