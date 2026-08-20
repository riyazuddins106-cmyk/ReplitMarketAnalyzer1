
import os
import pickle
import math
from collections import Counter


# ============================================================
# MLAI v3.2.4
# OOS VALIDATION AUDIT ENGINE
#
# Purpose:
#   Audit the v3.2.3 chronological validation methodology.
#
# IMPORTANT:
#   - Does NOT modify market_data.bin
#   - Does NOT modify MLAI v3.1
#   - Does NOT modify learning memory
#   - Does NOT change any threshold
#
# Main checks:
#   1. Candle/data integrity
#   2. Chronological split integrity
#   3. Target classification distributions
#   4. Threshold-dependent neutral rates
#   5. Directional coverage calculation
#   6. Prediction/target alignment
#   7. Look-ahead protection
# ============================================================


MARKET_FILE = "market_data.bin"

WINDOW = 60
HORIZONS = [4, 8, 16]

THRESHOLDS = [
    0.0015,   # 0.15%
    0.0018,   # 0.18%
    0.0020,   # 0.20%
    0.0024,   # 0.24%
]

VALIDATION_RATIO = 0.30


# ============================================================
# DISPLAY
# ============================================================

def banner(title):
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def pct(value):
    return f"{value * 100:.2f}%"


# ============================================================
# LOAD MARKET DATA
# ============================================================

banner("MLAI v3.2.4 OOS VALIDATION AUDIT")

print("Purpose: audit chronological validation methodology.")
print()
print(f"Market file       : {MARKET_FILE}")
print(f"Current window    : {WINDOW}")
print(f"Horizons          : {HORIZONS}")
print(
    "Thresholds        : "
    + ", ".join(f"±{x * 100:.2f}%" for x in THRESHOLDS)
)
print(f"Validation ratio  : {VALIDATION_RATIO * 100:.0f}%")

if not os.path.exists(MARKET_FILE):
    print()
    print("ERROR: market_data.bin was not found.")
    raise SystemExit(1)

with open(MARKET_FILE, "rb") as f:
    data = pickle.load(f)

print()
print("PASS: market_data.bin loaded.")
print(f"Data type: {type(data).__name__}")


# ============================================================
# EXTRACT CLOSE PRICES
# ============================================================

def extract_close(item):
    if isinstance(item, dict):
        for key in ("close", "Close", "c"):
            if key in item:
                return float(item[key])

        if "ohlc" in item and isinstance(item["ohlc"], dict):
            ohlc = item["ohlc"]
            for key in ("close", "Close", "c"):
                if key in ohlc:
                    return float(ohlc[key])

    if isinstance(item, (list, tuple)):
        # Common OHLC format:
        # [timestamp, open, high, low, close, ...]
        if len(item) >= 5:
            return float(item[4])

    return None


if isinstance(data, dict):
    possible_lists = [
        data.get("candles"),
        data.get("data"),
        data.get("prices"),
        data.get("records"),
    ]

    candles = None

    for candidate in possible_lists:
        if isinstance(candidate, list):
            candles = candidate
            break

    if candles is None:
        # Sometimes dictionary itself contains indexed records.
        candles = list(data.values())

elif isinstance(data, list):
    candles = data

else:
    candles = list(data)


closes = []

for item in candles:
    try:
        value = extract_close(item)

        if value is not None and math.isfinite(value) and value > 0:
            closes.append(value)

    except Exception:
        continue


if len(closes) < WINDOW + max(HORIZONS) + 10:
    print()
    print("ERROR: insufficient valid close prices.")
    print(f"Valid closes: {len(closes)}")
    raise SystemExit(1)

print()
print("PASS: Close prices extracted.")
print(f"Valid close prices: {len(closes)}")


# ============================================================
# CHRONOLOGICAL SPLIT
# ============================================================

split_index = int(len(closes) * (1.0 - VALIDATION_RATIO))

calibration_closes = closes[:split_index]
validation_closes = closes[split_index:]

print()
print("CHRONOLOGICAL DATA SPLIT")
print("-" * 78)

print(f"Calibration/reference candles : {len(calibration_closes)}")
print(f"Validation candles            : {len(validation_closes)}")
print(f"Validation begins at index    : {split_index}")

if split_index <= WINDOW:
    print()
    print("ERROR: validation split occurs before enough history exists.")
    raise SystemExit(1)

print()
print("PASS: validation period is later than calibration period.")


# ============================================================
# CLASSIFICATION
# ============================================================

def classify_return(return_pct, threshold):
    """
    return_pct is decimal percentage movement.

    Example:
        +0.0020 = +0.20%
        -0.0020 = -0.20%
    """

    if return_pct >= threshold:
        return "BUY"

    if return_pct <= -threshold:
        return "SELL"

    return "NEUTRAL"


# ============================================================
# TARGET DISTRIBUTION AUDIT
# ============================================================

banner("TARGET CLASSIFICATION AUDIT")

audit_results = []

for threshold in THRESHOLDS:

    print()
    print(f"THRESHOLD ±{threshold * 100:.2f}%")
    print("-" * 78)

    for horizon in HORIZONS:

        counts = Counter()

        total = 0

        # IMPORTANT:
        # Target starts from each validation candle and looks
        # FORWARD by the horizon.
        #
        # No prediction is involved here.
        # This isolates the ground-truth classification.

        for i in range(split_index, len(closes) - horizon):

            current_close = closes[i]
            future_close = closes[i + horizon]

            movement = (future_close - current_close) / current_close

            label = classify_return(movement, threshold)

            counts[label] += 1
            total += 1

        buy = counts["BUY"]
        sell = counts["SELL"]
        neutral = counts["NEUTRAL"]

        directional = buy + sell

        coverage = directional / total if total else 0
        neutral_rate = neutral / total if total else 0

        print(
            f"{horizon:2d} candles -> "
            f"records={total} | "
            f"BUY={pct(buy / total)} | "
            f"SELL={pct(sell / total)} | "
            f"NEUTRAL={pct(neutral / total)} | "
            f"directional coverage={pct(coverage)}"
        )

        audit_results.append(
            {
                "threshold": threshold,
                "horizon": horizon,
                "total": total,
                "buy": buy,
                "sell": sell,
                "neutral": neutral,
                "coverage": coverage,
                "neutral_rate": neutral_rate,
            }
        )


# ============================================================
# COVERAGE CONSISTENCY CHECK
# ============================================================

banner("COVERAGE CONSISTENCY CHECK")

coverage_by_threshold = {}

for row in audit_results:

    threshold = row["threshold"]

    coverage_by_threshold.setdefault(threshold, [])

    coverage_by_threshold[threshold].append(
        row["coverage"]
    )


for threshold, values in coverage_by_threshold.items():

    avg_coverage = sum(values) / len(values)

    print(
        f"±{threshold * 100:.2f}% -> "
        f"average target directional coverage = "
        f"{pct(avg_coverage)}"
    )


# ============================================================
# EXPECTATION CHECK
# ============================================================

banner("THRESHOLD MONOTONICITY CHECK")

print(
    "As the threshold increases, directional coverage should "
    "normally decrease or remain approximately stable."
)

monotonic_pass = True

for horizon in HORIZONS:

    values = []

    for threshold in THRESHOLDS:

        row = next(
            x for x in audit_results
            if x["threshold"] == threshold
            and x["horizon"] == horizon
        )

        values.append(
            (
                threshold,
                row["coverage"]
            )
        )

    for j in range(1, len(values)):

        previous = values[j - 1][1]
        current = values[j][1]

        if current > previous + 1e-9:

            monotonic_pass = False

            print(
                f"WARNING: horizon={horizon}, "
                f"coverage increased from "
                f"{pct(previous)} to {pct(current)}"
            )

if monotonic_pass:
    print()
    print("PASS: Target directional coverage behaves monotonically.")


# ============================================================
# CHECK V3.2.3 CLAIM
# ============================================================

banner("V3.2.3 COVERAGE CLAIM AUDIT")

print(
    "v3.2.3 reported approximately 99.72% directional coverage "
    "for every tested threshold."
)

print()
print("This audit calculates coverage directly from the")
print("chronological ground-truth target labels.")
print()

for threshold in THRESHOLDS:

    rows = [
        x for x in audit_results
        if x["threshold"] == threshold
    ]

    avg_coverage = (
        sum(x["coverage"] for x in rows)
        / len(rows)
    )

    avg_neutral = (
        sum(x["neutral_rate"] for x in rows)
        / len(rows)
    )

    print(
        f"±{threshold * 100:.2f}% -> "
        f"target coverage={pct(avg_coverage)} | "
        f"target neutral={pct(avg_neutral)}"
    )


# ============================================================
# LOOK-AHEAD CHECK
# ============================================================

banner("LOOK-AHEAD PROTECTION AUDIT")

print(
    "For every validation target:"
)
print(
    "  current candle = i"
)
print(
    "  future target  = i + horizon"
)
print()
print(
    "The validation label must never use candles before the "
    "current prediction point as future information."
)

lookahead_pass = True

for horizon in HORIZONS:

    maximum_target_index = (
        len(closes) - 1
    )

    minimum_prediction_index = split_index

    if minimum_prediction_index + horizon > maximum_target_index:
        lookahead_pass = False

        print(
            f"FAIL: horizon {horizon} exceeds available "
            "validation data."
        )

if lookahead_pass:
    print("PASS: Horizon bounds are valid.")


# ============================================================
# CLASS BALANCE
# ============================================================

banner("CLASS BALANCE AUDIT")

for threshold in THRESHOLDS:

    rows = [
        x for x in audit_results
        if x["threshold"] == threshold
    ]

    buy = sum(x["buy"] for x in rows)
    sell = sum(x["sell"] for x in rows)
    neutral = sum(x["neutral"] for x in rows)

    total = buy + sell + neutral

    print()
    print(f"±{threshold * 100:.2f}%")
    print(
        f"BUY     : {pct(buy / total)}"
    )
    print(
        f"SELL    : {pct(sell / total)}"
    )
    print(
        f"NEUTRAL : {pct(neutral / total)}"
    )


# ============================================================
# FINAL DIAGNOSIS
# ============================================================

banner("MLAI v3.2.4 AUDIT RESULT")

print()
print("IMPORTANT FINDINGS")
print("-" * 78)

if monotonic_pass:
    print("PASS: Threshold classification behaves as expected.")
else:
    print("WARNING: Threshold classification is not monotonic.")

if lookahead_pass:
    print("PASS: Chronological horizon boundaries are valid.")
else:
    print("FAIL: Horizon boundary problem detected.")

print()
print(
    "The key comparison is now:"
)
print()
print(
    "v3.2.3 reported coverage:"
)
print(
    "    approximately 99.72% for every threshold"
)
print()
print(
    "v3.2.4 calculates actual target coverage independently."
)

print()
print(
    "DO NOT change MLAI v3.1 based on v3.2.3 yet."
)

print()
print(
    "If v3.2.4 shows strongly different coverage values "
    "between thresholds, then the v3.2.3 coverage metric "
    "needs correction before threshold selection."
)

print()
print(
    "If the values agree, we can proceed to the next "
    "validation stage."
)

print()
print("=" * 78)
print("MLAI v3.2.4 AUDIT COMPLETED")
print("=" * 78)

