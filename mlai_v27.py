import os
import json
import pickle
import math
from datetime import datetime, timezone


# ============================================================
# MLAI v2.7 FIXED
# HISTORICAL ERROR ANALYSIS + FAILURE PATTERN LEARNING ENGINE
#
# IMPORTANT:
# v2.7 rebuilds detailed historical samples directly from
# market_data.bin.
#
# It does NOT attempt to reconstruct individual records from
# v2.6 aggregate statistics.
# ============================================================

VERSION = "2.7"
MARKET_FILE = "market_data.bin"
ERROR_MEMORY_FILE = "mlai_error_memory.bin"
STATUS_FILE = "MLAI_PROJECT_STATUS.md"

WINDOW = 60
HORIZONS = [4, 8, 16]
NEUTRAL_THRESHOLD = 0.0005

SEPARATOR = "=" * 70
LINE = "-" * 70


# ============================================================
# OUTPUT HELPERS
# ============================================================

def pct(value):
    return f"{value * 100:.1f}%"


def safe_float(value, default=None):
    try:
        return float(value)
    except Exception:
        return default


def print_header(title):
    print(SEPARATOR)
    print(title)
    print(SEPARATOR)


def print_section(title):
    print()
    print(title)
    print(LINE)


# ============================================================
# GENERIC DATA EXTRACTION
# ============================================================

def get_value(obj, *names):
    """
    Read a value from either:
      - dictionary
      - object attributes
    """

    if isinstance(obj, dict):
        for name in names:
            if name in obj:
                return obj[name]

    for name in names:
        if hasattr(obj, name):
            return getattr(obj, name)

    return None


def normalize_candle(raw):
    """
    Convert different possible candle formats into:

    {
        timestamp,
        open,
        high,
        low,
        close,
        volume
    }
    """

    if isinstance(raw, dict):
        timestamp = get_value(
            raw,
            "timestamp",
            "datetime",
            "date",
            "time",
            "t"
        )

        open_price = get_value(
            raw,
            "open",
            "Open",
            "o"
        )

        high_price = get_value(
            raw,
            "high",
            "High",
            "h"
        )

        low_price = get_value(
            raw,
            "low",
            "Low",
            "l"
        )

        close_price = get_value(
            raw,
            "close",
            "Close",
            "c"
        )

        volume = get_value(
            raw,
            "volume",
            "Volume",
            "v"
        )

    elif isinstance(raw, (list, tuple)):
        if len(raw) >= 5:
            timestamp = raw[0]
            open_price = raw[1]
            high_price = raw[2]
            low_price = raw[3]
            close_price = raw[4]
            volume = raw[5] if len(raw) > 5 else None
        else:
            return None

    else:
        timestamp = get_value(
            raw,
            "timestamp",
            "datetime",
            "date",
            "time"
        )

        open_price = get_value(raw, "open", "Open")
        high_price = get_value(raw, "high", "High")
        low_price = get_value(raw, "low", "Low")
        close_price = get_value(raw, "close", "Close")
        volume = get_value(raw, "volume", "Volume")

    open_price = safe_float(open_price)
    high_price = safe_float(high_price)
    low_price = safe_float(low_price)
    close_price = safe_float(close_price)
    volume = safe_float(volume, 0.0)

    if (
        open_price is None
        or high_price is None
        or low_price is None
        or close_price is None
    ):
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
# MARKET DATA EXTRACTION
# ============================================================

def extract_candles(memory):
    """
    Supports several possible market_data.bin layouts.
    """

    candidates = []

    if isinstance(memory, list):
        candidates = memory

    elif isinstance(memory, tuple):
        candidates = list(memory)

    elif isinstance(memory, dict):

        possible_keys = [
            "candles",
            "data",
            "market_data",
            "ohlcv",
            "records",
            "prices"
        ]

        for key in possible_keys:
            value = memory.get(key)

            if isinstance(value, (list, tuple)):
                candidates = list(value)
                break

        if not candidates:

            # Sometimes the dictionary itself contains numeric
            # candle records.
            for value in memory.values():
                if isinstance(value, (list, tuple)):
                    if len(value) >= 5:
                        candidates.append(value)

    else:
        for attr in [
            "candles",
            "data",
            "market_data",
            "records",
            "prices"
        ]:
            value = getattr(memory, attr, None)

            if isinstance(value, (list, tuple)):
                candidates = list(value)
                break

    normalized = []

    for item in candidates:
        candle = normalize_candle(item)

        if candle is not None:
            normalized.append(candle)

    return normalized


# ============================================================
# LOAD MARKET MEMORY
# ============================================================

print()
print_header(
    "MLAI v2.7 FIXED - LOADING MARKET MEMORY"
)

print()
print(f"File: {MARKET_FILE}")
print()

if not os.path.exists(MARKET_FILE):
    print("ERROR: market_data.bin not found.")
    raise SystemExit(1)

try:
    with open(MARKET_FILE, "rb") as f:
        market_memory = pickle.load(f)

    print("PASS: market_data.bin loaded as MLAI memory object.")

except Exception as exc:
    print(f"ERROR: Unable to load market_data.bin: {exc}")
    raise SystemExit(1)


candles = extract_candles(market_memory)

if len(candles) < WINDOW + max(HORIZONS):
    print()
    print(
        f"ERROR: Not enough candles. "
        f"Need at least {WINDOW + max(HORIZONS)}, "
        f"found {len(candles)}."
    )
    raise SystemExit(1)


print()
print(f"Found {len(candles)} stored candles.")


# ============================================================
# DECISION ENGINE
# ============================================================

def candle_direction(candle):
    body = candle["close"] - candle["open"]

    if body > 0:
        return "bullish"

    if body < 0:
        return "bearish"

    return "neutral"


def calculate_context(window_candles):
    closes = [c["close"] for c in window_candles]

    first_close = closes[0]
    latest_close = closes[-1]

    net_change = latest_close - first_close

    if first_close != 0:
        net_change_pct = net_change / first_close
    else:
        net_change_pct = 0.0

    bullish = 0
    bearish = 0
    neutral = 0

    for candle in window_candles:
        direction = candle_direction(candle)

        if direction == "bullish":
            bullish += 1
        elif direction == "bearish":
            bearish += 1
        else:
            neutral += 1

    # --------------------------------------------------------
    # Momentum
    # --------------------------------------------------------

    half = max(2, len(closes) // 2)

    first_half = closes[:half]
    second_half = closes[-half:]

    first_move = (
        first_half[-1] - first_half[0]
        if len(first_half) >= 2
        else 0.0
    )

    second_move = (
        second_half[-1] - second_half[0]
        if len(second_half) >= 2
        else 0.0
    )

    if abs(second_move) < abs(first_move) * 0.75:
        momentum = "decreasing"
    elif abs(second_move) > abs(first_move) * 1.25:
        momentum = "increasing"
    else:
        momentum = "stable"

    # --------------------------------------------------------
    # Volatility
    # --------------------------------------------------------

    ranges = []

    for candle in window_candles:
        high = candle["high"]
        low = candle["low"]

        if low != 0:
            ranges.append((high - low) / low)

    if ranges:
        half_range = max(1, len(ranges) // 2)

        old_vol = (
            sum(ranges[:half_range]) /
            len(ranges[:half_range])
        )

        new_vol = (
            sum(ranges[-half_range:]) /
            len(ranges[-half_range:])
        )

        if new_vol > old_vol * 1.15:
            volatility = "expanding"
        elif new_vol < old_vol * 0.85:
            volatility = "contracting"
        else:
            volatility = "stable"
    else:
        volatility = "stable"

    # --------------------------------------------------------
    # Structure
    # --------------------------------------------------------

    quarter = max(5, len(closes) // 4)

    q1 = closes[:quarter]
    q2 = closes[quarter:2 * quarter]
    q3 = closes[2 * quarter:3 * quarter]
    q4 = closes[-quarter:]

    q1_high = max(q1)
    q2_high = max(q2)
    q3_high = max(q3)
    q4_high = max(q4)

    q1_low = min(q1)
    q2_low = min(q2)
    q3_low = min(q3)
    q4_low = min(q4)

    higher_highs = (
        q2_high >= q1_high
        and q3_high >= q2_high
        and q4_high >= q3_high
    )

    higher_lows = (
        q2_low >= q1_low
        and q3_low >= q2_low
        and q4_low >= q3_low
    )

    lower_highs = (
        q2_high <= q1_high
        and q3_high <= q2_high
        and q4_high <= q3_high
    )

    lower_lows = (
        q2_low <= q1_low
        and q3_low <= q2_low
        and q4_low <= q3_low
    )

    if higher_highs and higher_lows:
        structure = "bullish_structure"

    elif lower_highs and lower_lows:
        structure = "bearish_structure"

    else:
        structure = "range_structure"

    # --------------------------------------------------------
    # Rejection
    # --------------------------------------------------------

    upper_rejection = 0
    lower_rejection = 0

    for candle in window_candles:
        body_high = max(
            candle["open"],
            candle["close"]
        )

        body_low = min(
            candle["open"],
            candle["close"]
        )

        upper_wick = candle["high"] - body_high
        lower_wick = body_low - candle["low"]

        if upper_wick > lower_wick:
            upper_rejection += 1

        elif lower_wick > upper_wick:
            lower_rejection += 1

    if lower_rejection > upper_rejection:
        rejection = "lower_rejection_dominant"

    elif upper_rejection > lower_rejection:
        rejection = "upper_rejection_dominant"

    else:
        rejection = "balanced_rejection"

    # --------------------------------------------------------
    # Direction
    # --------------------------------------------------------

    if net_change_pct > NEUTRAL_THRESHOLD:
        direction = "bullish"

    elif net_change_pct < -NEUTRAL_THRESHOLD:
        direction = "bearish"

    else:
        if bullish > bearish:
            direction = "bullish"
        elif bearish > bullish:
            direction = "bearish"
        else:
            direction = "neutral"

    return {
        "direction": direction,
        "structure": structure,
        "momentum": momentum,
        "volatility": volatility,
        "rejection": rejection,
        "first_close": first_close,
        "latest_close": latest_close,
        "net_change": net_change,
        "net_change_pct": net_change_pct,
        "bullish_candles": bullish,
        "bearish_candles": bearish,
        "neutral_candles": neutral,
    }


# ============================================================
# HISTORICAL DECISION
# ============================================================

def build_decision(window_candles):
    context = calculate_context(window_candles)

    direction = context["direction"]

    # --------------------------------------------------------
    # Evidence scoring
    # --------------------------------------------------------

    bullish_score = 0.0
    bearish_score = 0.0
    neutral_score = 0.0

    if direction == "bullish":
        bullish_score += 3.0

    elif direction == "bearish":
        bearish_score += 3.0

    else:
        neutral_score += 3.0

    if context["structure"] == "bullish_structure":
        bullish_score += 2.0

    elif context["structure"] == "bearish_structure":
        bearish_score += 2.0

    else:
        neutral_score += 1.0

    if context["momentum"] == "increasing":

        if direction == "bullish":
            bullish_score += 1.0

        elif direction == "bearish":
            bearish_score += 1.0

    elif context["momentum"] == "decreasing":

        # Decreasing momentum reduces directional confidence.
        neutral_score += 0.5

    if context["rejection"] == "lower_rejection_dominant":

        if direction == "bullish":
            bullish_score += 1.0

    elif context["rejection"] == "upper_rejection_dominant":

        if direction == "bearish":
            bearish_score += 1.0

    total = (
        bullish_score
        + bearish_score
        + neutral_score
    )

    if total <= 0:
        distribution = {
            "bullish": 0.3333,
            "bearish": 0.3333,
            "neutral": 0.3334,
        }
    else:
        distribution = {
            "bullish": bullish_score / total,
            "bearish": bearish_score / total,
            "neutral": neutral_score / total,
        }

    primary = max(
        distribution,
        key=distribution.get
    )

    # Confidence = separation of strongest evidence
    sorted_values = sorted(
        distribution.values(),
        reverse=True
    )

    confidence = (
        sorted_values[0] - sorted_values[1]
    )

    return {
        "direction": primary,
        "distribution": distribution,
        "confidence": max(
            0.0,
            min(1.0, confidence)
        ),
        "context": context,
    }


# ============================================================
# ACTUAL FUTURE OUTCOME
# ============================================================

def resolve_outcome(
    candles,
    decision_index,
    horizon
):
    """
    Resolve ONLY using candles AFTER decision_index.

    This prevents future-data leakage.
    """

    decision_close = candles[
        decision_index - 1
    ]["close"]

    future_index = (
        decision_index + horizon - 1
    )

    if future_index >= len(candles):
        return None

    future_close = candles[
        future_index
    ]["close"]

    if decision_close == 0:
        return None

    change = (
        future_close - decision_close
    ) / decision_close

    if change > NEUTRAL_THRESHOLD:
        outcome = "bullish"

    elif change < -NEUTRAL_THRESHOLD:
        outcome = "bearish"

    else:
        outcome = "neutral"

    return {
        "outcome": outcome,
        "future_change": change,
        "future_close": future_close,
    }


# ============================================================
# BUILD DETAILED WALK-FORWARD RECORDS
# ============================================================

print()
print("PASS: Building detailed walk-forward error records...")

records = []

start_index = WINDOW
last_index = (
    len(candles)
    - max(HORIZONS)
)

for decision_end in range(
    start_index,
    last_index + 1
):

    window = candles[
        decision_end - WINDOW:
        decision_end
    ]

    decision = build_decision(window)

    timestamp = candles[
        decision_end - 1
    ]["timestamp"]

    for horizon in HORIZONS:

        outcome = resolve_outcome(
            candles,
            decision_end,
            horizon
        )

        if outcome is None:
            continue

        predicted = decision["direction"]
        actual = outcome["outcome"]

        correct = (
            predicted == actual
        )

        records.append({
            "decision_index": decision_end - 1,
            "timestamp": timestamp,
            "horizon": horizon,
            "predicted": predicted,
            "actual": actual,
            "correct": correct,
            "confidence": decision["confidence"],
            "distribution": decision["distribution"],
            "future_change": outcome[
                "future_change"
            ],
            "context": decision["context"],
        })


print(
    f"PASS: Generated {len(records)} "
    f"detailed historical outcome records."
)


# ============================================================
# VALIDATION STATISTICS
# ============================================================

def empty_stats():
    return {
        "resolved": 0,
        "correct": 0,
        "incorrect": 0,
        "accuracy": 0.0,
    }


def finalize_stats(stats):
    resolved = stats["resolved"]

    if resolved > 0:
        stats["accuracy"] = (
            stats["correct"]
            / resolved
            * 100.0
        )
    else:
        stats["accuracy"] = 0.0

    return stats


overall = empty_stats()

horizon_stats = {
    horizon: empty_stats()
    for horizon in HORIZONS
}

direction_stats = {
    direction: empty_stats()
    for direction in [
        "bullish",
        "bearish",
        "neutral"
    ]
}

confidence_buckets = {
    "0-20%": empty_stats(),
    "20-40%": empty_stats(),
    "40-60%": empty_stats(),
    "60-80%": empty_stats(),
    "80-100%": empty_stats(),
}


def get_confidence_bucket(confidence):
    value = confidence * 100.0

    if value < 20:
        return "0-20%"

    if value < 40:
        return "20-40%"

    if value < 60:
        return "40-60%"

    if value < 80:
        return "60-80%"

    return "80-100%"


for record in records:

    overall["resolved"] += 1

    if record["correct"]:
        overall["correct"] += 1
    else:
        overall["incorrect"] += 1

    horizon = record["horizon"]

    horizon_stats[
        horizon
    ]["resolved"] += 1

    if record["correct"]:
        horizon_stats[
            horizon
        ]["correct"] += 1
    else:
        horizon_stats[
            horizon
        ]["incorrect"] += 1

    direction = record["predicted"]

    direction_stats[
        direction
    ]["resolved"] += 1

    if record["correct"]:
        direction_stats[
            direction
        ]["correct"] += 1
    else:
        direction_stats[
            direction
        ]["incorrect"] += 1

    bucket = get_confidence_bucket(
        record["confidence"]
    )

    confidence_buckets[
        bucket
    ]["resolved"] += 1

    if record["correct"]:
        confidence_buckets[
            bucket
        ]["correct"] += 1
    else:
        confidence_buckets[
            bucket
        ]["incorrect"] += 1


finalize_stats(overall)

for stats in horizon_stats.values():
    finalize_stats(stats)

for stats in direction_stats.values():
    finalize_stats(stats)

for stats in confidence_buckets.values():
    finalize_stats(stats)


# ============================================================
# FAILURE PATTERN ANALYSIS
# ============================================================

failure_patterns = {}

for record in records:

    if record["correct"]:
        continue

    context = record["context"]

    key = (
        record["predicted"],
        context["structure"],
        context["momentum"],
        context["volatility"],
        record["horizon"],
    )

    if key not in failure_patterns:
        failure_patterns[key] = {
            "predicted": record["predicted"],
            "structure": context["structure"],
            "momentum": context["momentum"],
            "volatility": context["volatility"],
            "horizon": record["horizon"],
            "failures": 0,
        }

    failure_patterns[key]["failures"] += 1


failure_patterns = sorted(
    failure_patterns.values(),
    key=lambda x: x["failures"],
    reverse=True
)


# ============================================================
# LEARNING MATURITY
# ============================================================

if overall["resolved"] == 0:
    maturity = "insufficient_sample"

elif overall["resolved"] < 100:
    maturity = "early_historical_sample"

elif overall["resolved"] < 500:
    maturity = "developing_historical_sample"

elif overall["resolved"] < 1000:
    maturity = "established_historical_sample"

else:
    maturity = "large_historical_sample"


# ============================================================
# SAVE ERROR MEMORY
# ============================================================

error_memory = {
    "version": VERSION,
    "created_at": datetime.now(
        timezone.utc
    ).isoformat(),

    "source": {
        "file": MARKET_FILE,
        "candles": len(candles),
    },

    "configuration": {
        "window": WINDOW,
        "horizons": HORIZONS,
        "neutral_threshold": NEUTRAL_THRESHOLD,
    },

    "validation": {
        "overall": overall,
        "horizon": horizon_stats,
        "direction": direction_stats,
        "confidence": confidence_buckets,
        "learning_maturity": maturity,
    },

    "failure_patterns": failure_patterns,

    "records": records,
}


with open(
    ERROR_MEMORY_FILE,
    "wb"
) as f:
    pickle.dump(
        error_memory,
        f
    )


# ============================================================
# DISPLAY RESULTS
# ============================================================

print()
print("PASS: mlai_error_memory.bin saved.")

print()
print_header(
    "MLAI v2.7 FIXED HISTORICAL ERROR ANALYSIS + FAILURE PATTERN LEARNING ENGINE"
)

print_section("VALIDATION SUMMARY")

print(
    f"Historical samples    : "
    f"{len(records) // len(HORIZONS)}"
)

print(
    f"Resolved outcomes     : "
    f"{overall['resolved']}"
)

print(
    f"Correct               : "
    f"{overall['correct']}"
)

print(
    f"Incorrect             : "
    f"{overall['incorrect']}"
)

print(
    f"Overall accuracy      : "
    f"{overall['accuracy']:.1f}%"
)

print(
    f"Learning maturity     : "
    f"{maturity}"
)


print_section("DATA SOURCE")

print(
    "PASS: Detailed historical records were rebuilt "
    "directly from market_data.bin."
)

print(
    "PASS: No v2.6 aggregate statistics were used "
    "to reconstruct individual outcomes."
)

print(
    "PASS: Each historical decision uses only candles "
    "available before that decision."
)


print_section("HORIZON ERROR ANALYSIS")

for horizon in HORIZONS:

    stats = horizon_stats[horizon]

    print(
        f"{horizon:2d} candles -> "
        f"resolved={stats['resolved']} | "
        f"correct={stats['correct']} | "
        f"incorrect={stats['incorrect']} | "
        f"accuracy={stats['accuracy']:.1f}%"
    )


print_section("DIRECTION FAILURE ANALYSIS")

for direction in [
    "bullish",
    "bearish",
    "neutral"
]:

    stats = direction_stats[direction]

    print(
        f"{direction:<8} -> "
        f"resolved={stats['resolved']} | "
        f"correct={stats['correct']} | "
        f"incorrect={stats['incorrect']} | "
        f"accuracy={stats['accuracy']:.1f}%"
    )


print_section("CONFIDENCE FAILURE ANALYSIS")

for bucket, stats in confidence_buckets.items():

    print(
        f"{bucket:<8} -> "
        f"samples={stats['resolved']} | "
        f"correct={stats['correct']} | "
        f"incorrect={stats['incorrect']} | "
        f"accuracy={stats['accuracy']:.1f}%"
    )


print_section("FAILURE PATTERN LEARNING")

if not failure_patterns:

    print(
        "No individual failure patterns were detected."
    )

else:

    display_limit = 10

    for index, pattern in enumerate(
        failure_patterns[:display_limit],
        start=1
    ):

        print(
            f"{index:02d}. "
            f"prediction={pattern['predicted']} | "
            f"structure={pattern['structure']} | "
            f"momentum={pattern['momentum']} | "
            f"volatility={pattern['volatility']} | "
            f"horizon={pattern['horizon']} | "
            f"failures={pattern['failures']}"
        )

    if len(failure_patterns) > display_limit:
        print(
            f"... "
            f"{len(failure_patterns) - display_limit} "
            f"additional failure patterns stored."
        )


print_section("ERROR LEARNING INTERPRETATION")

if overall["resolved"] == 0:

    print(
        "No resolved historical outcomes were available."
    )

else:

    print(
        "MLAI independently reconstructed detailed "
        "historical decisions and resolved them using "
        "future candles only after each decision point."
    )

    print(
        f"The rebuilt validation set contains "
        f"{overall['resolved']} resolved outcomes."
    )

    print(
        f"Historical directional accuracy is "
        f"{overall['accuracy']:.1f}%."
    )

    print(
        "Incorrect decisions are retained as learning "
        "evidence rather than discarded."
    )

    print(
        f"{len(failure_patterns)} distinct failure "
        f"patterns were identified."
    )


print_section("DATA-LEAKAGE PROTECTION")

print(
    "PASS: Historical decisions use only candles "
    "available at each historical decision point."
)

print(
    "PASS: Future candles are used only to resolve "
    "the outcome after the decision."
)

print(
    "PASS: No future candle is used to construct "
    "the original historical decision."
)


print_section("LEARNING PRINCIPLES")

principles = [
    "Historical errors are analysed separately from successful decisions.",
    "Future candles are never used to construct the original historical decision.",
    "Incorrect outcomes are preserved rather than hidden.",
    "Failure frequency does not automatically imply future failure.",
    "Direction-specific errors are measured separately.",
    "Horizon-specific errors are measured separately.",
    "Confidence-level errors are measured separately.",
    "Detailed records are required for individual failure-pattern learning.",
    "Aggregate statistics are never treated as individual records.",
    "Small samples are explicitly marked as immature.",
    "Historical error patterns are evidence, not guarantees.",
    "The engine does not create an automatic trading signal.",
]

for index, principle in enumerate(
    principles,
    start=1
):
    print(f"{index}. {principle}")


# ============================================================
# UPDATE PROJECT STATUS
# ============================================================

status_text = f"""# MLAI Project Status

## v2.7 Fixed - Historical Error Analysis

Updated: {datetime.now(timezone.utc).isoformat()}

### Status

MLAI v2.7 independently rebuilds detailed historical
walk-forward decisions directly from market_data.bin.

### Configuration

- Decision window: {WINDOW} candles
- Outcome horizons: {HORIZONS}
- Neutral threshold: {NEUTRAL_THRESHOLD * 100:.3f}%
- Stored candles: {len(candles)}
- Historical decision samples: {len(records) // len(HORIZONS)}
- Resolved outcomes: {overall["resolved"]}

### Historical Performance

- Correct: {overall["correct"]}
- Incorrect: {overall["incorrect"]}
- Accuracy: {overall["accuracy"]:.1f}%
- Learning maturity: {maturity}

### Important Fix

v2.7 no longer attempts to reconstruct detailed
failure records from v2.6 aggregate statistics.

Detailed historical decisions are regenerated directly
from raw market_data.bin and future candles are used only
to resolve each historical decision.

### Leakage Protection

Historical decisions use only information available
at the historical decision point.

Future candles are used exclusively for outcome resolution.

### Safety

MLAI v2.7 is an analysis and historical learning engine.
It does not generate automatic BUY/SELL trading signals.
"""

try:

    with open(
        STATUS_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(status_text)

    print()
    print(
        "PASS: MLAI_PROJECT_STATUS.md updated."
    )

except Exception as exc:

    print()
    print(
        f"WARNING: Could not update "
        f"{STATUS_FILE}: {exc}"
    )


print()
print(SEPARATOR)
print(
    "PASS: MLAI v2.7 FIXED Historical Error Analysis "
    "+ Failure Pattern Learning Engine completed."
)
print(SEPARATOR)