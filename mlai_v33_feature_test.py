import pickle
import math
from collections import defaultdict


# ============================================================
# MLAI v3.3 FEATURE DIAGNOSTIC
# ============================================================

MARKET_FILE = "market_data.bin"

CURRENT_WINDOW = 60

HORIZONS = [4, 8, 16]

THRESHOLD = 0.15


# ============================================================
# HELPERS
# ============================================================

def percentage_change(start, end):

    if start == 0:
        return 0.0

    return (
        (end - start)
        / abs(start)
        * 100.0
    )


def average(values):

    if not values:
        return 0.0

    return sum(values) / len(values)


def safe_float(value):

    try:
        return float(value)
    except Exception:
        return 0.0


def classify_return(value):

    if value > THRESHOLD:
        return "bullish"

    if value < -THRESHOLD:
        return "bearish"

    return "neutral"


# ============================================================
# LOAD DATA
# ============================================================

print("=" * 70)
print("MLAI v3.3 FEATURE DIAGNOSTIC")
print("=" * 70)

with open(MARKET_FILE, "rb") as f:

    data = pickle.load(f)


candles = data["candles"]

print()
print("Market file:", MARKET_FILE)
print("Total candles:", len(candles))
print("Current window:", CURRENT_WINDOW)
print("Horizons:", HORIZONS)
print("Classification threshold:", f"±{THRESHOLD:.2f}%")
print()


# ============================================================
# FEATURE EXTRACTION
# ============================================================

def extract_features(window):

    closes = [
        safe_float(c["close"])
        for c in window
    ]

    opens = [
        safe_float(c["open"])
        for c in window
    ]

    highs = [
        safe_float(c["high"])
        for c in window
    ]

    lows = [
        safe_float(c["low"])
        for c in window
    ]

    bodies = [
        safe_float(c.get("body", 0.0))
        for c in window
    ]

    ranges = [
        safe_float(c.get("range", 0.0))
        for c in window
    ]

    upper_wicks = [
        safe_float(c.get("upper_wick", 0.0))
        for c in window
    ]

    lower_wicks = [
        safe_float(c.get("lower_wick", 0.0))
        for c in window
    ]

    directions = [
        c.get("direction", "neutral")
        for c in window
    ]

    candle_types = [
        c.get("candle_type", "normal")
        for c in window
    ]


    # --------------------------------------------------------
    # RETURNS
    # --------------------------------------------------------

    return_60 = percentage_change(
        closes[0],
        closes[-1]
    )

    return_30 = percentage_change(
        closes[-30],
        closes[-1]
    )

    return_15 = percentage_change(
        closes[-15],
        closes[-1]
    )

    return_10 = percentage_change(
        closes[-10],
        closes[-1]
    )

    return_5 = percentage_change(
        closes[-5],
        closes[-1]
    )


    # --------------------------------------------------------
    # CANDLE COUNTS
    # --------------------------------------------------------

    bullish_count = sum(
        1
        for d in directions
        if d == "bullish"
    )

    bearish_count = sum(
        1
        for d in directions
        if d == "bearish"
    )

    neutral_count = sum(
        1
        for d in directions
        if d == "neutral"
    )


    bullish_ratio = (
        bullish_count
        / len(window)
        * 100.0
    )

    bearish_ratio = (
        bearish_count
        / len(window)
        * 100.0
    )


    directional_imbalance = (
        bullish_count
        - bearish_count
    )


    # --------------------------------------------------------
    # CANDLE TYPE COUNTS
    # --------------------------------------------------------

    strong_body_count = sum(
        1
        for t in candle_types
        if t == "strong_body"
    )

    upper_rejection_count = sum(
        1
        for t in candle_types
        if t == "upper_rejection"
    )

    lower_rejection_count = sum(
        1
        for t in candle_types
        if t == "lower_rejection"
    )

    doji_count = sum(
        1
        for t in candle_types
        if t == "doji_like"
    )


    strong_body_ratio = (
        strong_body_count
        / len(window)
        * 100.0
    )


    rejection_imbalance = (
        lower_rejection_count
        - upper_rejection_count
    )


    # --------------------------------------------------------
    # BODY / RANGE
    # --------------------------------------------------------

    body_ratios = []

    for body, candle_range in zip(
        bodies,
        ranges
    ):

        if candle_range > 0:

            body_ratios.append(
                abs(body)
                / candle_range
            )


    average_body_ratio = average(
        body_ratios
    )


    # --------------------------------------------------------
    # VOLATILITY
    # --------------------------------------------------------

    percentage_ranges = []

    for high, low, close in zip(
        highs,
        lows,
        closes
    ):

        if close == 0:
            continue

        percentage_ranges.append(
            (high - low)
            / abs(close)
            * 100.0
        )


    volatility = average(
        percentage_ranges
    )


    # --------------------------------------------------------
    # RECENT VS OLDER VOLATILITY
    # --------------------------------------------------------

    older_volatility = average(
        percentage_ranges[:-10]
    )

    recent_volatility = average(
        percentage_ranges[-10:]
    )

    if older_volatility > 0:

        volatility_ratio = (
            recent_volatility
            / older_volatility
        )

    else:

        volatility_ratio = 1.0


    # --------------------------------------------------------
    # HIGH / LOW LOCATION
    # --------------------------------------------------------

    highest = max(highs)

    lowest = min(lows)

    price_range = highest - lowest

    if price_range > 0:

        location_in_range = (
            closes[-1] - lowest
        ) / price_range

    else:

        location_in_range = 0.5


    distance_from_high = percentage_change(
        highest,
        closes[-1]
    )

    distance_from_low = percentage_change(
        lowest,
        closes[-1]
    )


    # --------------------------------------------------------
    # TREND SLOPE
    # --------------------------------------------------------

    n = len(closes)

    x_values = list(
        range(n)
    )

    x_mean = average(
        x_values
    )

    y_mean = average(
        closes
    )

    numerator = sum(
        (
            x - x_mean
        )
        *
        (
            y - y_mean
        )
        for x, y in zip(
            x_values,
            closes
        )
    )

    denominator = sum(
        (
            x - x_mean
        ) ** 2
        for x in x_values
    )

    if denominator != 0:

        slope = (
            numerator
            / denominator
        )

    else:

        slope = 0.0


    normalized_slope = (
        slope
        / closes[-1]
        * 100.0
    )


    # --------------------------------------------------------
    # MOMENTUM ACCELERATION
    # --------------------------------------------------------

    first_half_return = percentage_change(
        closes[0],
        closes[30]
    )

    second_half_return = percentage_change(
        closes[30],
        closes[-1]
    )

    momentum_acceleration = (
        second_half_return
        - first_half_return
    )


    # --------------------------------------------------------
    # RETURN FEATURES
    # --------------------------------------------------------

    return {

        "return_60":
            return_60,

        "return_30":
            return_30,

        "return_15":
            return_15,

        "return_10":
            return_10,

        "return_5":
            return_5,

        "bullish_ratio":
            bullish_ratio,

        "bearish_ratio":
            bearish_ratio,

        "directional_imbalance":
            directional_imbalance,

        "strong_body_ratio":
            strong_body_ratio,

        "rejection_imbalance":
            rejection_imbalance,

        "average_body_ratio":
            average_body_ratio,

        "volatility":
            volatility,

        "volatility_ratio":
            volatility_ratio,

        "location_in_range":
            location_in_range,

        "distance_from_high":
            distance_from_high,

        "distance_from_low":
            distance_from_low,

        "normalized_slope":
            normalized_slope,

        "momentum_acceleration":
            momentum_acceleration,
    }


# ============================================================
# CORRELATION
# ============================================================

def correlation(x_values, y_values):

    if len(x_values) < 2:
        return 0.0

    x_mean = average(x_values)
    y_mean = average(y_values)

    numerator = sum(
        (x - x_mean)
        *
        (y - y_mean)
        for x, y in zip(
            x_values,
            y_values
        )
    )

    x_variance = sum(
        (x - x_mean) ** 2
        for x in x_values
    )

    y_variance = sum(
        (y - y_mean) ** 2
        for y in y_values
    )

    denominator = math.sqrt(
        x_variance
        *
        y_variance
    )

    if denominator == 0:

        return 0.0

    return (
        numerator
        / denominator
    )


# ============================================================
# FEATURE TEST
# ============================================================

def test_feature(
    feature_name,
    feature_values,
    outcomes
):

    result = {}

    result["feature"] = feature_name

    result["samples"] = len(
        feature_values
    )

    result["correlation"] = correlation(
        feature_values,
        outcomes
    )

    if not feature_values:

        result["high_mean"] = 0.0
        result["low_mean"] = 0.0
        result["directional_lift"] = 0.0

        return result


    ordered = sorted(
        zip(
            feature_values,
            outcomes
        ),
        key=lambda x: x[0]
    )


    split = max(
        1,
        len(ordered) // 4
    )


    low_group = [
        outcome
        for _, outcome
        in ordered[:split]
    ]

    high_group = [
        outcome
        for _, outcome
        in ordered[-split:]
    ]


    low_mean = average(
        low_group
    )

    high_mean = average(
        high_group
    )


    result["low_mean"] = low_mean

    result["high_mean"] = high_mean

    result["directional_lift"] = (
        abs(high_mean)
        - abs(low_mean)
    )

    return result


# ============================================================
# HISTORICAL WALK-FORWARD DATASET
# ============================================================

print("=" * 70)
print("BUILDING WALK-FORWARD FEATURE DATASET")
print("=" * 70)

records_by_horizon = {
    horizon: []
    for horizon in HORIZONS
}


last_decision_index = (
    len(candles)
    - max(HORIZONS)
)


for decision_index in range(
    CURRENT_WINDOW,
    last_decision_index
):

    window = candles[
        decision_index - CURRENT_WINDOW:
        decision_index
    ]

    features = extract_features(
        window
    )

    current_close = safe_float(
        candles[
            decision_index - 1
        ]["close"]
    )


    for horizon in HORIZONS:

        outcome_index = (
            decision_index
            + horizon
            - 1
        )

        if outcome_index >= len(candles):

            continue

        future_close = safe_float(
            candles[
                outcome_index
            ]["close"]
        )

        future_return = percentage_change(
            current_close,
            future_close
        )

        records_by_horizon[
            horizon
        ].append({

            "features":
                features,

            "future_return":
                future_return,

            "future_direction":
                classify_return(
                    future_return
                ),
        })


# ============================================================
# ANALYZE FEATURES
# ============================================================

FEATURE_NAMES = [

    "return_60",

    "return_30",

    "return_15",

    "return_10",

    "return_5",

    "bullish_ratio",

    "bearish_ratio",

    "directional_imbalance",

    "strong_body_ratio",

    "rejection_imbalance",

    "average_body_ratio",

    "volatility",

    "volatility_ratio",

    "location_in_range",

    "distance_from_high",

    "distance_from_low",

    "normalized_slope",

    "momentum_acceleration",
]


for horizon in HORIZONS:

    print()
    print("=" * 70)
    print(f"HORIZON: {horizon} CANDLES")
    print("=" * 70)

    records = records_by_horizon[
        horizon
    ]

    print(
        "Records:",
        len(records)
    )

    results = []

    for feature_name in FEATURE_NAMES:

        feature_values = [
            record[
                "features"
            ][feature_name]

            for record in records
        ]

        outcomes = [
            record[
                "future_return"
            ]

            for record in records
        ]

        result = test_feature(
            feature_name,
            feature_values,
            outcomes
        )

        results.append(
            result
        )


    results.sort(
        key=lambda item:
            abs(
                item["correlation"]
            ),
        reverse=True
    )


    print()
    print(
        "Feature ranking by absolute correlation"
    )

    print()

    print(
        f"{'Feature':<28}"
        f"{'Correlation':>14}"
        f"{'Low Mean':>14}"
        f"{'High Mean':>14}"
    )

    print("-" * 70)


    for result in results:

        print(
            f"{result['feature']:<28}"
            f"{result['correlation']:>14.4f}"
            f"{result['low_mean']:>14.4f}"
            f"{result['high_mean']:>14.4f}"
        )


# ============================================================
# COMPLETE
# ============================================================

print()
print("=" * 70)
print("MLAI v3.3 FEATURE DIAGNOSTIC COMPLETE")
print("=" * 70)

print()
print(
    "IMPORTANT:"
)

print(
    "This program does not modify market_data.bin."
)

print(
    "This program does not modify mlai_v31.py."
)

print(
    "This program does not modify learning memory."
)

print(
    "Results are diagnostic only."
)

print("=" * 70)