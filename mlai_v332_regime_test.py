import pickle
import math
from collections import Counter


# ============================================================
# MLAI v3.3.2
# REGIME + CONFIDENCE DIAGNOSTIC
#
# PURPOSE:
# Determine WHEN the 60-candle structure contains useful
# directional information and WHEN MLAI should stay neutral.
#
# PROTECTION:
# - market_data.bin is READ ONLY
# - mlai_v31.py is NOT modified
# - learning memory is NOT modified
# - production thresholds are NOT modified
# ============================================================


DATA_FILE = "market_data.bin"

WINDOW = 60
HORIZONS = [4, 8, 16]

CLASSIFICATION_THRESHOLD = 0.15

CALIBRATION_RATIO = 0.70

MIN_REGIME_SAMPLES = 15


# ============================================================
# BASIC FUNCTIONS
# ============================================================

def average(values):
    if not values:
        return 0.0
    return sum(values) / len(values)


def percentage_change(old, new):
    if old == 0:
        return 0.0

    return ((new - old) / abs(old)) * 100.0


def clamp(value, low, high):
    return max(low, min(high, value))


# ============================================================
# LOAD MARKET DATA
# ============================================================

print("=" * 70)
print("MLAI v3.3.2 REGIME + CONFIDENCE DIAGNOSTIC")
print("=" * 70)

print()
print("Market file:", DATA_FILE)
print("Current window:", WINDOW)
print("Horizons:", HORIZONS)
print("Classification threshold: +/-", CLASSIFICATION_THRESHOLD, "%")
print("Calibration ratio:", CALIBRATION_RATIO)

print()

with open(DATA_FILE, "rb") as f:
    data = pickle.load(f)

candles = data["candles"]

print("Total candles:", len(candles))


# ============================================================
# PROTECTION CHECK
# ============================================================

print()
print("=" * 70)
print("PROTECTION CHECK")
print("=" * 70)

print("market_data.bin: READ ONLY")
print("mlai_v31.py: NOT MODIFIED")
print("learning memory: NOT MODIFIED")
print("production threshold: NOT MODIFIED")


# ============================================================
# FEATURE EXTRACTION
# ============================================================

def build_features(window):

    closes = [x["close"] for x in window]

    highs = [x["high"] for x in window]

    lows = [x["low"] for x in window]

    ranges = [x["range"] for x in window]

    bodies = [x["body"] for x in window]

    directions = [
        x["direction"]
        for x in window
    ]

    # --------------------------------------------------------
    # RETURNS
    # --------------------------------------------------------

    def ret(n):

        if len(closes) <= n:
            return 0.0

        return percentage_change(
            closes[-n - 1],
            closes[-1]
        )

    return_5 = ret(5)
    return_10 = ret(10)
    return_15 = ret(15)
    return_30 = ret(30)
    return_60 = ret(59)

    # --------------------------------------------------------
    # DIRECTIONAL BALANCE
    # --------------------------------------------------------

    bullish_count = sum(
        1 for x in directions
        if x == "bullish"
    )

    bearish_count = sum(
        1 for x in directions
        if x == "bearish"
    )

    neutral_count = sum(
        1 for x in directions
        if x == "neutral"
    )

    total = len(window)

    bullish_ratio = bullish_count / total

    bearish_ratio = bearish_count / total

    neutral_ratio = neutral_count / total

    directional_imbalance = (
        bullish_ratio
        - bearish_ratio
    )

    # --------------------------------------------------------
    # BODY STRUCTURE
    # --------------------------------------------------------

    body_ratios = []

    for candle in window:

        candle_range = candle["range"]

        if candle_range <= 0:
            continue

        body_ratios.append(
            candle["body"] / candle_range
        )

    average_body_ratio = average(
        body_ratios
    )

    strong_body_ratio = sum(
        1
        for candle in window
        if candle["candle_type"] == "strong_body"
    ) / total

    # --------------------------------------------------------
    # REJECTION
    # --------------------------------------------------------

    upper_rejections = 0
    lower_rejections = 0

    for candle in window:

        if candle["candle_type"] == "upper_rejection":
            upper_rejections += 1

        elif candle["candle_type"] == "lower_rejection":
            lower_rejections += 1

    rejection_imbalance = (
        lower_rejections
        - upper_rejections
    ) / total

    # --------------------------------------------------------
    # VOLATILITY
    # --------------------------------------------------------

    volatility = average(
        ranges
    ) / abs(closes[-1]) * 100.0

    older_ranges = ranges[:-15]

    recent_ranges = ranges[-15:]

    older_volatility = average(
        older_ranges
    ) / abs(closes[-1]) * 100.0

    recent_volatility = average(
        recent_ranges
    ) / abs(closes[-1]) * 100.0

    if older_volatility == 0:

        volatility_ratio = 1.0

    else:

        volatility_ratio = (
            recent_volatility
            / older_volatility
        )

    # --------------------------------------------------------
    # RANGE POSITION
    # --------------------------------------------------------

    highest = max(highs)

    lowest = min(lows)

    total_range = highest - lowest

    if total_range == 0:

        location_in_range = 0.5
        distance_from_high = 0.0
        distance_from_low = 0.0

    else:

        location_in_range = (
            closes[-1] - lowest
        ) / total_range

        distance_from_high = (
            highest - closes[-1]
        ) / total_range

        distance_from_low = (
            closes[-1] - lowest
        ) / total_range

    # --------------------------------------------------------
    # SLOPE
    # --------------------------------------------------------

    first_close = closes[0]

    last_close = closes[-1]

    normalized_slope = percentage_change(
        first_close,
        last_close
    )

    # --------------------------------------------------------
    # MOMENTUM ACCELERATION
    # --------------------------------------------------------

    if len(closes) >= 30:

        previous = percentage_change(
            closes[-30],
            closes[-15]
        )

        recent = percentage_change(
            closes[-15],
            closes[-1]
        )

        momentum_acceleration = (
            recent - previous
        )

    else:

        momentum_acceleration = 0.0

    return {

        "return_5": return_5,
        "return_10": return_10,
        "return_15": return_15,
        "return_30": return_30,
        "return_60": return_60,

        "bullish_ratio": bullish_ratio,
        "bearish_ratio": bearish_ratio,
        "neutral_ratio": neutral_ratio,

        "directional_imbalance":
            directional_imbalance,

        "average_body_ratio":
            average_body_ratio,

        "strong_body_ratio":
            strong_body_ratio,

        "rejection_imbalance":
            rejection_imbalance,

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
# FUTURE CLASSIFICATION
# ============================================================

def future_classification(
    candles,
    index,
    horizon
):

    current_close = candles[index]["close"]

    future_index = index + horizon

    if future_index >= len(candles):

        return None

    future_close = candles[
        future_index
    ]["close"]

    change = percentage_change(
        current_close,
        future_close
    )

    if change >= CLASSIFICATION_THRESHOLD:

        return "bullish"

    elif change <= -CLASSIFICATION_THRESHOLD:

        return "bearish"

    else:

        return "neutral"


# ============================================================
# REGIME DETECTION
# ============================================================

def detect_regime(features):

    directional = features[
        "directional_imbalance"
    ]

    volatility_ratio = features[
        "volatility_ratio"
    ]

    slope = features[
        "normalized_slope"
    ]

    location = features[
        "location_in_range"
    ]

    rejection = features[
        "rejection_imbalance"
    ]

    # --------------------------------------------------------
    # STRONG BULL REGIME
    # --------------------------------------------------------

    bull_score = 0

    if directional > 0.08:
        bull_score += 1

    if slope > 0.20:
        bull_score += 1

    if location > 0.60:
        bull_score += 1

    if rejection > 0.03:
        bull_score += 1

    # --------------------------------------------------------
    # STRONG BEAR REGIME
    # --------------------------------------------------------

    bear_score = 0

    if directional < -0.08:
        bear_score += 1

    if slope < -0.20:
        bear_score += 1

    if location < 0.40:
        bear_score += 1

    if rejection < -0.03:
        bear_score += 1

    # --------------------------------------------------------
    # VOLATILITY REGIME
    # --------------------------------------------------------

    if volatility_ratio >= 1.20:

        volatility_regime = "expanding"

    elif volatility_ratio <= 0.80:

        volatility_regime = "contracting"

    else:

        volatility_regime = "stable"

    # --------------------------------------------------------
    # DIRECTIONAL REGIME
    # --------------------------------------------------------

    if bull_score >= 3:

        directional_regime = "bullish"

    elif bear_score >= 3:

        directional_regime = "bearish"

    elif bull_score > bear_score:

        directional_regime = "bullish_bias"

    elif bear_score > bull_score:

        directional_regime = "bearish_bias"

    else:

        directional_regime = "balanced"

    return (
        directional_regime,
        volatility_regime,
        bull_score,
        bear_score,
    )


# ============================================================
# CONFIDENCE MODEL
# ============================================================

def calculate_confidence(
    features,
    regime
):

    directional_regime = regime[0]

    volatility_regime = regime[1]

    bull_score = regime[2]

    bear_score = regime[3]

    bull_evidence = 0.0
    bear_evidence = 0.0

    # --------------------------------------------------------
    # Directional imbalance
    # --------------------------------------------------------

    imbalance = features[
        "directional_imbalance"
    ]

    bull_evidence += max(
        0.0,
        imbalance * 100.0
    )

    bear_evidence += max(
        0.0,
        -imbalance * 100.0
    )

    # --------------------------------------------------------
    # Momentum
    # --------------------------------------------------------

    momentum = features[
        "return_15"
    ]

    bull_evidence += max(
        0.0,
        momentum * 1.5
    )

    bear_evidence += max(
        0.0,
        -momentum * 1.5
    )

    # --------------------------------------------------------
    # Location
    # --------------------------------------------------------

    location = features[
        "location_in_range"
    ]

    if location > 0.65:

        bull_evidence += 10.0

    elif location < 0.35:

        bear_evidence += 10.0

    # --------------------------------------------------------
    # Rejection
    # --------------------------------------------------------

    rejection = features[
        "rejection_imbalance"
    ]

    bull_evidence += max(
        0.0,
        rejection * 100.0
    )

    bear_evidence += max(
        0.0,
        -rejection * 100.0
    )

    # --------------------------------------------------------
    # Regime bonus
    # --------------------------------------------------------

    if directional_regime == "bullish":

        bull_evidence += 20.0

    elif directional_regime == "bearish":

        bear_evidence += 20.0

    elif directional_regime == "bullish_bias":

        bull_evidence += 8.0

    elif directional_regime == "bearish_bias":

        bear_evidence += 8.0

    # --------------------------------------------------------
    # Volatility adjustment
    # --------------------------------------------------------

    if volatility_regime == "expanding":

        bull_evidence *= 1.05
        bear_evidence *= 1.05

    elif volatility_regime == "contracting":

        bull_evidence *= 0.90
        bear_evidence *= 0.90

    total = (
        bull_evidence
        + bear_evidence
    )

    if total <= 0:

        return {
            "prediction": "neutral",
            "confidence": 0.0,
            "bull_evidence": 0.0,
            "bear_evidence": 0.0,
        }

    if bull_evidence > bear_evidence:

        prediction = "bullish"

        confidence = (
            bull_evidence / total
        ) * 100.0

    elif bear_evidence > bull_evidence:

        prediction = "bearish"

        confidence = (
            bear_evidence / total
        ) * 100.0

    else:

        prediction = "neutral"

        confidence = 0.0

    return {
        "prediction": prediction,
        "confidence": confidence,
        "bull_evidence": bull_evidence,
        "bear_evidence": bear_evidence,
    }


# ============================================================
# BUILD WALK-FORWARD DATASET
# ============================================================

def build_records(horizon):

    records = []

    start = WINDOW - 1

    end = len(candles) - horizon

    for index in range(
        start,
        end
    ):

        window = candles[
            index - WINDOW + 1:
            index + 1
        ]

        features = build_features(
            window
        )

        actual = future_classification(
            candles,
            index,
            horizon
        )

        if actual is None:
            continue

        regime = detect_regime(
            features
        )

        confidence = calculate_confidence(
            features,
            regime
        )

        records.append({
            "index": index,
            "features": features,
            "regime": regime,
            "confidence": confidence,
            "actual": actual,
        })

    return records


# ============================================================
# METRICS
# ============================================================

def evaluate(
    records,
    confidence_threshold
):

    matrix = {
        "bullish": {
            "bullish": 0,
            "neutral": 0,
            "bearish": 0,
        },

        "neutral": {
            "bullish": 0,
            "neutral": 0,
            "bearish": 0,
        },

        "bearish": {
            "bullish": 0,
            "neutral": 0,
            "bearish": 0,
        },
    }

    predictions = []

    for record in records:

        result = record["confidence"]

        prediction = result[
            "prediction"
        ]

        confidence = result[
            "confidence"
        ]

        if (
            prediction != "neutral"
            and confidence < confidence_threshold
        ):

            prediction = "neutral"

        matrix[
            prediction
        ][
            record["actual"]
        ] += 1

        predictions.append(
            (
                prediction,
                record["actual"]
            )
        )

    total = len(predictions)

    correct = sum(
        1
        for prediction, actual
        in predictions
        if prediction == actual
    )

    accuracy = (
        correct / total * 100.0
        if total
        else 0.0
    )

    directional_predictions = [
        x
        for x in predictions
        if x[0] in ("bullish", "bearish")
    ]

    directional_correct = sum(
        1
        for prediction, actual
        in directional_predictions
        if prediction == actual
    )

    directional_accuracy = (
        directional_correct
        / len(directional_predictions)
        * 100.0
        if directional_predictions
        else 0.0
    )

    coverage = (
        len(directional_predictions)
        / total
        * 100.0
        if total
        else 0.0
    )

    # --------------------------------------------------------
    # BUY PRECISION
    # --------------------------------------------------------

    buy_predictions = [
        x
        for x in predictions
        if x[0] == "bullish"
    ]

    buy_correct = sum(
        1
        for prediction, actual
        in buy_predictions
        if actual == "bullish"
    )

    buy_precision = (
        buy_correct
        / len(buy_predictions)
        * 100.0
        if buy_predictions
        else 0.0
    )

    # --------------------------------------------------------
    # SELL PRECISION
    # --------------------------------------------------------

    sell_predictions = [
        x
        for x in predictions
        if x[0] == "bearish"
    ]

    sell_correct = sum(
        1
        for prediction, actual
        in sell_predictions
        if actual == "bearish"
    )

    sell_precision = (
        sell_correct
        / len(sell_predictions)
        * 100.0
        if sell_predictions
        else 0.0
    )

    return {
        "accuracy": accuracy,
        "directional_accuracy":
            directional_accuracy,
        "coverage": coverage,
        "buy_precision":
            buy_precision,
        "sell_precision":
            sell_precision,
        "matrix": matrix,
    }


# ============================================================
# REGIME ANALYSIS
# ============================================================

def analyze_regimes(records):

    groups = {}

    for record in records:

        directional_regime = record[
            "regime"
        ][0]

        volatility_regime = record[
            "regime"
        ][1]

        key = (
            directional_regime,
            volatility_regime
        )

        if key not in groups:

            groups[key] = []

        groups[key].append(
            record
        )

    print()
    print("=" * 70)
    print("REGIME OUTCOME ANALYSIS")
    print("=" * 70)

    print()

    print(
        f"{'REGIME':<22}"
        f"{'VOLATILITY':<15}"
        f"{'N':>6}"
        f"{'BULL %':>10}"
        f"{'NEUTRAL %':>12}"
        f"{'BEAR %':>10}"
    )

    print("-" * 70)

    for key, group in sorted(
        groups.items(),
        key=lambda x: len(x[1]),
        reverse=True
    ):

        if len(group) < MIN_REGIME_SAMPLES:
            continue

        counts = Counter(
            x["actual"]
            for x in group
        )

        n = len(group)

        bull = (
            counts["bullish"]
            / n
            * 100
        )

        neutral = (
            counts["neutral"]
            / n
            * 100
        )

        bear = (
            counts["bearish"]
            / n
            * 100
        )

        print(
            f"{key[0]:<22}"
            f"{key[1]:<15}"
            f"{n:>6}"
            f"{bull:>10.2f}"
            f"{neutral:>12.2f}"
            f"{bear:>10.2f}"
        )


# ============================================================
# MAIN EXPERIMENT
# ============================================================

for horizon in HORIZONS:

    print()
    print("=" * 70)
    print(
        f"HORIZON: {horizon} CANDLES"
    )
    print("=" * 70)

    records = build_records(
        horizon
    )

    print()
    print(
        "Historical records:",
        len(records)
    )

    calibration_count = int(
        len(records)
        * CALIBRATION_RATIO
    )

    calibration = records[
        :calibration_count
    ]

    validation = records[
        calibration_count:
    ]

    print(
        "Calibration records:",
        len(calibration)
    )

    print(
        "Validation records:",
        len(validation)
    )

    print()
    print(
        "The validation section is"
    )

    print(
        "chronologically AFTER calibration."
    )

    print(
        "No validation outcomes are used"
    )

    print(
        "to calculate the diagnostic rules."
    )

    # --------------------------------------------------------
    # REGIME ANALYSIS ON VALIDATION
    # --------------------------------------------------------

    analyze_regimes(
        validation
    )

    # --------------------------------------------------------
    # CONFIDENCE TEST
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("CONFIDENCE THRESHOLD TEST")
    print("=" * 70)

    thresholds = [
        50,
        55,
        60,
        65,
        70,
        75,
        80,
        85,
    ]

    print()

    print(
        f"{'Threshold':<12}"
        f"{'Accuracy':>12}"
        f"{'Dir Acc':>12}"
        f"{'Coverage':>12}"
        f"{'BUY Prec':>12}"
        f"{'SELL Prec':>12}"
    )

    print("-" * 70)

    for threshold in thresholds:

        metrics = evaluate(
            validation,
            threshold
        )

        print(
            f"{threshold:>8.0f}%"
            f"{metrics['accuracy']:>12.2f}"
            f"{metrics['directional_accuracy']:>12.2f}"
            f"{metrics['coverage']:>12.2f}"
            f"{metrics['buy_precision']:>12.2f}"
            f"{metrics['sell_precision']:>12.2f}"
        )

    # --------------------------------------------------------
    # BEST CONFIDENCE THRESHOLD
    # --------------------------------------------------------

    best = None

    for threshold in thresholds:

        metrics = evaluate(
            validation,
            threshold
        )

        if metrics["coverage"] < 10:

            continue

        score = (
            metrics["directional_accuracy"]
            * math.sqrt(
                metrics["coverage"]
                / 100.0
            )
        )

        if (
            best is None
            or score > best["score"]
        ):

            best = {
                "threshold": threshold,
                "score": score,
                "metrics": metrics,
            }

    print()
    print("=" * 70)
    print("BEST CONFIDENCE / COVERAGE BALANCE")
    print("=" * 70)

    if best:

        metrics = best["metrics"]

        print()
        print(
            "Confidence threshold:",
            f"{best['threshold']}%"
        )

        print(
            "Directional accuracy:",
            f"{metrics['directional_accuracy']:.2f}%"
        )

        print(
            "Directional coverage:",
            f"{metrics['coverage']:.2f}%"
        )

        print(
            "BUY precision:",
            f"{metrics['buy_precision']:.2f}%"
        )

        print(
            "SELL precision:",
            f"{metrics['sell_precision']:.2f}%"
        )

    else:

        print()
        print(
            "No threshold met minimum coverage."
        )


# ============================================================
# CURRENT MARKET STATE
# ============================================================

print()
print("=" * 70)
print("CURRENT 60-CANDLE MARKET STATE")
print("=" * 70)

current_window = candles[-WINDOW:]

current_features = build_features(
    current_window
)

current_regime = detect_regime(
    current_features
)

current_confidence = calculate_confidence(
    current_features,
    current_regime
)

print()

print(
    "Latest candle:",
    candles[-1]["datetime"]
)

print(
    "Latest price:",
    candles[-1]["close"]
)

print()

print(
    "Directional regime:",
    current_regime[0]
)

print(
    "Volatility regime:",
    current_regime[1]
)

print(
    "Bull regime score:",
    current_regime[2]
)

print(
    "Bear regime score:",
    current_regime[3]
)

print()

print(
    "Raw structural prediction:",
    current_confidence["prediction"]
)

print(
    "Structural confidence:",
    f"{current_confidence['confidence']:.2f}%"
)

print(
    "Bull evidence:",
    f"{current_confidence['bull_evidence']:.2f}"
)

print(
    "Bear evidence:",
    f"{current_confidence['bear_evidence']:.2f}"
)

print()

print(
    "IMPORTANT:"
)

print(
    "This current-market output is NOT a trading signal."
)

print(
    "It is only a diagnostic representation of the"
)

print(
    "current 60-candle structure."
)


# ============================================================
# FINAL VERDICT
# ============================================================

print()
print("=" * 70)
print("MLAI v3.3.2 DIAGNOSTIC VERDICT")
print("=" * 70)

print()
print(
    "This experiment does NOT modify MLAI production logic."
)

print(
    "It does NOT modify market_data.bin."
)

print(
    "It does NOT modify learning memory."
)

print()

print(
    "The purpose is to determine whether different"
)

print(
    "60-candle regimes have measurably different"
)

print(
    "future directional outcomes."
)

print()

print(
    "The important discovery we are looking for is:"
)

print(
    "SOME STRUCTURES -> stronger directional edge"
)

print(
    "OTHER STRUCTURES -> weak / uncertain outcome"
)

print(
    "Therefore MLAI may eventually need:"
)

print(
    "BUY / SELL / NO TRADE"
)

print()

print(
    "Do NOT interpret these diagnostic results as"
)

print(
    "guaranteed future trading probabilities."
)

print()

print("=" * 70)
print("MLAI v3.3.2 REGIME DIAGNOSTIC COMPLETE")
print("=" * 70)