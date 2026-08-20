import pickle
import math
import statistics
from collections import Counter, defaultdict


# ============================================================
# MLAI v3.3.3
# SIMILAR STRUCTURE + REGIME CONDITIONAL MODEL
#
# DIAGNOSTIC ONLY
#
# market_data.bin       -> READ ONLY
# mlai_v31.py           -> NOT MODIFIED
# learning memory       -> NOT MODIFIED
# production logic      -> NOT MODIFIED
#
# Goal:
# Find historically similar 60-candle structures and determine
# whether those structures historically led to:
#
#     BUY
#     SELL
#     NO TRADE
#
# using strictly chronological walk-forward validation.
# ============================================================


DATA_FILE = "market_data.bin"

WINDOW = 60

HORIZONS = [4, 8, 16]

THRESHOLD = 0.15

CALIBRATION_RATIO = 0.70

# Number of historical structures used for prediction.
NEIGHBOR_COUNTS = [10, 20, 40]

# Minimum similarity required.
MAX_DISTANCE = 8.0

# If directional probability is too weak, return NO TRADE.
DIRECTION_MARGIN = 0.10

# Minimum confidence for directional prediction.
MIN_CONFIDENCE = 0.45


# ============================================================
# BASIC HELPERS
# ============================================================

def average(values):
    if not values:
        return 0.0

    return sum(values) / len(values)


def percentage_change(old, new):
    if old == 0:
        return 0.0

    return (new - old) / abs(old) * 100.0


def safe_ratio(a, b):
    if b == 0:
        return 0.0

    return a / b


def clamp(value, low, high):
    return max(low, min(high, value))


# ============================================================
# CANDLE FEATURES
# ============================================================

def extract_features(candles):

    if len(candles) < WINDOW:
        raise ValueError(
            f"At least {WINDOW} candles are required."
        )

    window = candles[-WINDOW:]

    closes = [float(c["close"]) for c in window]

    opens = [float(c["open"]) for c in window]

    highs = [float(c["high"]) for c in window]

    lows = [float(c["low"]) for c in window]

    ranges = []

    bodies = []

    bullish = 0

    bearish = 0

    neutral = 0

    strong_body = 0

    upper_rejection = 0

    lower_rejection = 0

    for candle in window:

        o = float(candle["open"])
        h = float(candle["high"])
        l = float(candle["low"])
        c = float(candle["close"])

        candle_range = h - l

        body = abs(c - o)

        ranges.append(candle_range)

        bodies.append(body)

        if c > o:
            bullish += 1

        elif c < o:
            bearish += 1

        else:
            neutral += 1

        candle_type = candle.get("candle_type", "")

        if candle_type == "strong_body":
            strong_body += 1

        elif candle_type == "upper_rejection":
            upper_rejection += 1

        elif candle_type == "lower_rejection":
            lower_rejection += 1

    # --------------------------------------------------------
    # Returns
    # --------------------------------------------------------

    latest = closes[-1]

    return_5 = percentage_change(
        closes[-6],
        closes[-1]
    )

    return_10 = percentage_change(
        closes[-11],
        closes[-1]
    )

    return_15 = percentage_change(
        closes[-16],
        closes[-1]
    )

    return_30 = percentage_change(
        closes[-31],
        closes[-1]
    )

    return_60 = percentage_change(
        closes[0],
        closes[-1]
    )

    # --------------------------------------------------------
    # Directional balance
    # --------------------------------------------------------

    bullish_ratio = bullish / WINDOW

    bearish_ratio = bearish / WINDOW

    neutral_ratio = neutral / WINDOW

    directional_imbalance = (
        bullish_ratio
        - bearish_ratio
    )

    # --------------------------------------------------------
    # Strong body
    # --------------------------------------------------------

    strong_body_ratio = (
        strong_body / WINDOW
    )

    average_body = average(bodies)

    average_range = average(ranges)

    average_body_ratio = safe_ratio(
        average_body,
        average_range
    )

    # --------------------------------------------------------
    # Rejection
    # --------------------------------------------------------

    rejection_imbalance = (
        lower_rejection
        - upper_rejection
    ) / WINDOW

    # --------------------------------------------------------
    # Volatility
    # --------------------------------------------------------

    normalized_ranges = []

    for i in range(len(window)):

        close = closes[i]

        if close == 0:
            continue

        normalized_ranges.append(
            ranges[i] / abs(close) * 100.0
        )

    volatility = average(
        normalized_ranges
    )

    older = normalized_ranges[:-10]

    recent = normalized_ranges[-10:]

    older_volatility = average(older)

    recent_volatility = average(recent)

    if older_volatility == 0:
        volatility_ratio = 1.0
    else:
        volatility_ratio = (
            recent_volatility
            / older_volatility
        )

    # --------------------------------------------------------
    # Range position
    # --------------------------------------------------------

    highest = max(highs)

    lowest = min(lows)

    total_range = highest - lowest

    if total_range == 0:

        location_in_range = 0.5

    else:

        location_in_range = (
            latest - lowest
        ) / total_range

    distance_from_high = safe_ratio(
        highest - latest,
        latest
    ) * 100.0

    distance_from_low = safe_ratio(
        latest - lowest,
        latest
    ) * 100.0

    # --------------------------------------------------------
    # Normalized slope
    # --------------------------------------------------------

    first_close = closes[0]

    last_close = closes[-1]

    normalized_slope = safe_ratio(
        last_close - first_close,
        first_close
    ) * 100.0

    # --------------------------------------------------------
    # Momentum acceleration
    # --------------------------------------------------------

    if len(closes) >= 30:

        old_momentum = percentage_change(
            closes[-30],
            closes[-15]
        )

        recent_momentum = percentage_change(
            closes[-15],
            closes[-1]
        )

        momentum_acceleration = (
            recent_momentum
            - old_momentum
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

        "strong_body_ratio":
            strong_body_ratio,

        "average_body_ratio":
            average_body_ratio,

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
# REGIME CLASSIFICATION
# ============================================================

def determine_regime(features):

    slope = features["normalized_slope"]

    imbalance = features[
        "directional_imbalance"
    ]

    volatility_ratio = features[
        "volatility_ratio"
    ]

    # --------------------------------------------------------
    # Directional regime
    # --------------------------------------------------------

    if slope > 0.25 and imbalance > 0.05:

        direction = "bullish"

    elif slope < -0.25 and imbalance < -0.05:

        direction = "bearish"

    elif slope > 0.10 or imbalance > 0.03:

        direction = "bullish_bias"

    elif slope < -0.10 or imbalance < -0.03:

        direction = "bearish_bias"

    else:

        direction = "neutral"

    # --------------------------------------------------------
    # Volatility regime
    # --------------------------------------------------------

    if volatility_ratio > 1.15:

        volatility = "expanding"

    elif volatility_ratio < 0.85:

        volatility = "contracting"

    else:

        volatility = "stable"

    return direction, volatility


# ============================================================
# FEATURE VECTOR
# ============================================================

FEATURE_NAMES = [
    "return_5",
    "return_10",
    "return_15",
    "return_30",
    "return_60",

    "bullish_ratio",
    "bearish_ratio",
    "neutral_ratio",

    "directional_imbalance",

    "strong_body_ratio",
    "average_body_ratio",

    "rejection_imbalance",

    "volatility",
    "volatility_ratio",

    "location_in_range",

    "distance_from_high",
    "distance_from_low",

    "normalized_slope",

    "momentum_acceleration",
]


def vector_from_features(features):

    return [
        float(features[name])
        for name in FEATURE_NAMES
    ]


# ============================================================
# HISTORICAL OUTCOME
# ============================================================

def classify_outcome(current_close, future_close):

    move = percentage_change(
        current_close,
        future_close
    )

    if move >= THRESHOLD:

        return "bullish"

    if move <= -THRESHOLD:

        return "bearish"

    return "neutral"


# ============================================================
# BUILD HISTORICAL RECORDS
# ============================================================

def build_records(candles, horizon):

    records = []

    start_index = WINDOW - 1

    end_index = (
        len(candles)
        - horizon
    )

    for index in range(
        start_index,
        end_index
    ):

        context = candles[
            index - WINDOW + 1:
            index + 1
        ]

        features = extract_features(
            context
        )

        regime_direction, regime_volatility = (
            determine_regime(features)
        )

        current_close = float(
            candles[index]["close"]
        )

        future_close = float(
            candles[index + horizon]["close"]
        )

        outcome = classify_outcome(
            current_close,
            future_close
        )

        future_return = percentage_change(
            current_close,
            future_close
        )

        records.append({

            "index": index,

            "features": features,

            "vector":
                vector_from_features(features),

            "regime_direction":
                regime_direction,

            "regime_volatility":
                regime_volatility,

            "outcome":
                outcome,

            "future_return":
                future_return,
        })

    return records


# ============================================================
# STANDARDIZATION
# ============================================================

def calculate_scaler(records):

    scaler = {}

    for i, name in enumerate(
        FEATURE_NAMES
    ):

        values = [
            r["vector"][i]
            for r in records
        ]

        mean_value = average(values)

        if len(values) >= 2:

            std_value = statistics.pstdev(
                values
            )

        else:

            std_value = 1.0

        if std_value == 0:

            std_value = 1.0

        scaler[name] = (
            mean_value,
            std_value
        )

    return scaler


def standardize_vector(vector, scaler):

    result = []

    for i, name in enumerate(
        FEATURE_NAMES
    ):

        mean_value, std_value = (
            scaler[name]
        )

        result.append(
            (
                vector[i]
                - mean_value
            )
            / std_value
        )

    return result


# ============================================================
# REGIME COMPATIBILITY
# ============================================================

def regime_distance(
    current,
    historical
):

    distance = 0.0

    if (
        current["direction"]
        != historical["direction"]
    ):

        distance += 1.5

    if (
        current["volatility"]
        != historical["volatility"]
    ):

        distance += 1.0

    return distance


# ============================================================
# SIMILARITY DISTANCE
# ============================================================

def euclidean_distance(a, b):

    total = 0.0

    for x, y in zip(a, b):

        difference = x - y

        total += (
            difference
            * difference
        )

    return math.sqrt(total)


def calculate_similarity_distance(
    current_vector,
    historical_vector,
    current_regime,
    historical_regime
):

    base_distance = euclidean_distance(
        current_vector,
        historical_vector
    )

    regime_penalty = regime_distance(
        current_regime,
        historical_regime
    )

    return (
        base_distance
        + regime_penalty
    )


# ============================================================
# FIND SIMILAR STRUCTURES
# ============================================================

def find_neighbors(
    target,
    calibration_records,
    scaler,
    neighbor_count
):

    target_vector = standardize_vector(
        target["vector"],
        scaler
    )

    current_regime = {
        "direction":
            target["regime_direction"],

        "volatility":
            target["regime_volatility"],
    }

    scored = []

    for record in calibration_records:

        historical_vector = (
            standardize_vector(
                record["vector"],
                scaler
            )
        )

        distance = (
            calculate_similarity_distance(
                target_vector,
                historical_vector,
                current_regime,
                {
                    "direction":
                        record[
                            "regime_direction"
                        ],

                    "volatility":
                        record[
                            "regime_volatility"
                        ],
                }
            )
        )

        scored.append(
            (
                distance,
                record
            )
        )

    scored.sort(
        key=lambda x: x[0]
    )

    neighbors = []

    for distance, record in scored:

        if distance <= MAX_DISTANCE:

            neighbors.append(
                (
                    distance,
                    record
                )
            )

        if len(neighbors) >= neighbor_count:

            break

    return neighbors


# ============================================================
# PREDICT BUY / SELL / NO TRADE
# ============================================================

def predict_from_neighbors(
    neighbors
):

    if not neighbors:

        return {

            "prediction": "NO TRADE",

            "confidence": 0.0,

            "bull_probability": 0.0,

            "bear_probability": 0.0,

            "neutral_probability": 0.0,

            "neighbor_count": 0,

            "average_distance": None,
        }

    # --------------------------------------------------------
    # Distance-weighted voting
    # --------------------------------------------------------

    bull_score = 0.0

    bear_score = 0.0

    neutral_score = 0.0

    total_weight = 0.0

    for distance, record in neighbors:

        weight = 1.0 / (
            1.0 + distance
        )

        total_weight += weight

        if record["outcome"] == "bullish":

            bull_score += weight

        elif record["outcome"] == "bearish":

            bear_score += weight

        else:

            neutral_score += weight

    if total_weight == 0:

        return {

            "prediction": "NO TRADE",

            "confidence": 0.0,

            "bull_probability": 0.0,

            "bear_probability": 0.0,

            "neutral_probability": 0.0,

            "neighbor_count":
                len(neighbors),

            "average_distance":
                average(
                    [x[0] for x in neighbors]
                ),
        }

    bull_probability = (
        bull_score
        / total_weight
    )

    bear_probability = (
        bear_score
        / total_weight
    )

    neutral_probability = (
        neutral_score
        / total_weight
    )

    probabilities = {

        "BUY":
            bull_probability,

        "SELL":
            bear_probability,

        "NO TRADE":
            neutral_probability,
    }

    prediction = max(
        probabilities,
        key=probabilities.get
    )

    confidence = probabilities[
        prediction
    ]

    # --------------------------------------------------------
    # Directional margin protection
    # --------------------------------------------------------

    if prediction == "BUY":

        directional_margin = (
            bull_probability
            - max(
                bear_probability,
                neutral_probability
            )
        )

    elif prediction == "SELL":

        directional_margin = (
            bear_probability
            - max(
                bull_probability,
                neutral_probability
            )
        )

    else:

        directional_margin = 0.0

    if prediction in ("BUY", "SELL"):

        if (
            confidence < MIN_CONFIDENCE
            or directional_margin
            < DIRECTION_MARGIN
        ):

            prediction = "NO TRADE"

            confidence = neutral_probability

    average_distance = average(
        [x[0] for x in neighbors]
    )

    return {

        "prediction": prediction,

        "confidence": confidence,

        "bull_probability":
            bull_probability,

        "bear_probability":
            bear_probability,

        "neutral_probability":
            neutral_probability,

        "neighbor_count":
            len(neighbors),

        "average_distance":
            average_distance,
    }


# ============================================================
# METRICS
# ============================================================

def calculate_metrics(
    predictions,
    actuals
):

    total = len(actuals)

    if total == 0:

        return {}

    exact_correct = sum(
        1
        for p, a in zip(
            predictions,
            actuals
        )
        if p == a
    )

    directional_indices = [

        i

        for i, p in enumerate(
            predictions
        )

        if p in ("BUY", "SELL")
    ]

    directional_correct = 0

    for i in directional_indices:

        prediction = predictions[i]

        actual = actuals[i]

        if (
            prediction == "BUY"
            and actual == "bullish"
        ):

            directional_correct += 1

        elif (
            prediction == "SELL"
            and actual == "bearish"
        ):

            directional_correct += 1

    coverage = (
        len(directional_indices)
        / total
        * 100.0
    )

    if directional_indices:

        directional_accuracy = (
            directional_correct
            / len(directional_indices)
            * 100.0
        )

    else:

        directional_accuracy = 0.0

    buy_indices = [
        i
        for i, p in enumerate(predictions)
        if p == "BUY"
    ]

    sell_indices = [
        i
        for i, p in enumerate(predictions)
        if p == "SELL"
    ]

    actual_bullish = sum(
        1
        for a in actuals
        if a == "bullish"
    )

    actual_bearish = sum(
        1
        for a in actuals
        if a == "bearish"
    )

    buy_correct = sum(
        1
        for i in buy_indices
        if actuals[i] == "bullish"
    )

    sell_correct = sum(
        1
        for i in sell_indices
        if actuals[i] == "bearish"
    )

    buy_precision = (
        buy_correct
        / len(buy_indices)
        * 100.0
        if buy_indices
        else 0.0
    )

    sell_precision = (
        sell_correct
        / len(sell_indices)
        * 100.0
        if sell_indices
        else 0.0
    )

    buy_recall = (
        buy_correct
        / actual_bullish
        * 100.0
        if actual_bullish
        else 0.0
    )

    sell_recall = (
        sell_correct
        / actual_bearish
        * 100.0
        if actual_bearish
        else 0.0
    )

    return {

        "accuracy":
            exact_correct / total * 100.0,

        "directional_accuracy":
            directional_accuracy,

        "coverage":
            coverage,

        "buy_precision":
            buy_precision,

        "sell_precision":
            sell_precision,

        "buy_recall":
            buy_recall,

        "sell_recall":
            sell_recall,

        "buy_count":
            len(buy_indices),

        "sell_count":
            len(sell_indices),

        "no_trade_count":
            predictions.count("NO TRADE"),
    }


# ============================================================
# PRINT METRICS
# ============================================================

def print_metrics(metrics):

    print(
        f"Accuracy:             "
        f"{metrics['accuracy']:.2f}%"
    )

    print(
        f"Directional accuracy: "
        f"{metrics['directional_accuracy']:.2f}%"
    )

    print(
        f"Directional coverage: "
        f"{metrics['coverage']:.2f}%"
    )

    print(
        f"BUY precision:        "
        f"{metrics['buy_precision']:.2f}%"
    )

    print(
        f"SELL precision:       "
        f"{metrics['sell_precision']:.2f}%"
    )

    print(
        f"BUY recall:           "
        f"{metrics['buy_recall']:.2f}%"
    )

    print(
        f"SELL recall:          "
        f"{metrics['sell_recall']:.2f}%"
    )

    print(
        f"BUY predictions:      "
        f"{metrics['buy_count']}"
    )

    print(
        f"SELL predictions:     "
        f"{metrics['sell_count']}"
    )

    print(
        f"NO TRADE predictions: "
        f"{metrics['no_trade_count']}"
    )


# ============================================================
# CONFUSION / ACTION TABLE
# ============================================================

def print_action_distribution(
    predictions,
    actuals
):

    table = defaultdict(
        lambda: Counter()
    )

    for prediction, actual in zip(
        predictions,
        actuals
    ):

        table[prediction][actual] += 1

    print()

    print(
        "Prediction        Bullish   Neutral   Bearish"
    )

    print(
        "-------------------------------------------------------"
    )

    for prediction in [
        "BUY",
        "NO TRADE",
        "SELL"
    ]:

        print(
            f"{prediction:<17}"
            f"{table[prediction]['bullish']:>8}"
            f"{table[prediction]['neutral']:>10}"
            f"{table[prediction]['bearish']:>10}"
        )


# ============================================================
# REGIME PERFORMANCE
# ============================================================

def analyze_regime_performance(
    predictions,
    records
):

    groups = defaultdict(list)

    for prediction, record in zip(
        predictions,
        records
    ):

        key = (
            record["regime_direction"],
            record["regime_volatility"]
        )

        groups[key].append(
            (
                prediction,
                record["outcome"]
            )
        )

    print()

    print(
        "REGIME PERFORMANCE"
    )

    print(
        "-----------------------------------------------------------------------"
    )

    print(
        f"{'REGIME':<18}"
        f"{'VOLATILITY':<15}"
        f"{'N':>6}"
        f"{'DIR ACC':>12}"
        f"{'BUY PREC':>12}"
        f"{'SELL PREC':>12}"
    )

    print(
        "-----------------------------------------------------------------------"
    )

    for key, values in sorted(
        groups.items()
    ):

        direction, volatility = key

        preds = [
            x[0]
            for x in values
        ]

        actuals = [
            x[1]
            for x in values
        ]

        metrics = calculate_metrics(
            preds,
            actuals
        )

        print(
            f"{direction:<18}"
            f"{volatility:<15}"
            f"{len(values):>6}"
            f"{metrics['directional_accuracy']:>11.2f}%"
            f"{metrics['buy_precision']:>11.2f}%"
            f"{metrics['sell_precision']:>11.2f}%"
        )


# ============================================================
# RUN ONE HORIZON
# ============================================================

def run_horizon(
    all_records,
    horizon
):

    total = len(all_records)

    split = int(
        total * CALIBRATION_RATIO
    )

    calibration_records = (
        all_records[:split]
    )

    validation_records = (
        all_records[split:]
    )

    print()

    print("=" * 70)

    print(
        f"HORIZON: {horizon} CANDLES"
    )

    print("=" * 70)

    print()

    print(
        f"Historical records: "
        f"{total}"
    )

    print(
        f"Calibration records: "
        f"{len(calibration_records)}"
    )

    print(
        f"Validation records:  "
        f"{len(validation_records)}"
    )

    print()

    print(
        "Calibration contains ONLY earlier "
        "chronological records."
    )

    print(
        "Validation contains ONLY later "
        "chronological records."
    )

    # --------------------------------------------------------
    # Scaler is calculated ONLY from calibration data.
    # --------------------------------------------------------

    scaler = calculate_scaler(
        calibration_records
    )

    print()

    print(
        "Feature scaler calculated "
        "from calibration data only."
    )

    print()

    # --------------------------------------------------------
    # Test different neighbor counts.
    # --------------------------------------------------------

    for neighbor_count in NEIGHBOR_COUNTS:

        print()

        print("-" * 70)

        print(
            f"SIMILAR STRUCTURE MODEL "
            f"| TOP {neighbor_count} NEIGHBORS"
        )

        print("-" * 70)

        predictions = []

        actuals = []

        validation_for_regime = []

        distances = []

        for target in validation_records:

            neighbors = find_neighbors(
                target,
                calibration_records,
                scaler,
                neighbor_count
            )

            prediction = predict_from_neighbors(
                neighbors
            )

            predictions.append(
                prediction["prediction"]
            )

            actuals.append(
                target["outcome"]
            )

            validation_for_regime.append(
                target
            )

            if prediction[
                "average_distance"
            ] is not None:

                distances.append(
                    prediction[
                        "average_distance"
                    ]
                )

        metrics = calculate_metrics(
            predictions,
            actuals
        )

        print()

        print(
            "SIMILAR-STRUCTURE PERFORMANCE"
        )

        print(
            "----------------------------------------------------------------------"
        )

        print_metrics(
            metrics
        )

        print()

        print(
            f"Average neighbor distance: "
            f"{average(distances):.4f}"
            if distances
            else
            "Average neighbor distance: N/A"
        )

        print_action_distribution(
            predictions,
            actuals
        )

        analyze_regime_performance(
            predictions,
            validation_for_regime
        )


# ============================================================
# CURRENT MARKET ANALYSIS
# ============================================================

def current_market_analysis(
    candles
):

    print()

    print("=" * 70)

    print(
        "CURRENT 60-CANDLE STRUCTURE"
    )

    print("=" * 70)

    context = candles[-WINDOW:]

    features = extract_features(
        context
    )

    direction, volatility = (
        determine_regime(features)
    )

    latest = context[-1]

    print()

    print(
        f"Latest candle: "
        f"{latest.get('datetime')}"
    )

    print(
        f"Latest price:  "
        f"{latest.get('close')}"
    )

    print()

    print(
        f"Directional regime: "
        f"{direction}"
    )

    print(
        f"Volatility regime:  "
        f"{volatility}"
    )

    print()

    print(
        "Key structure features:"
    )

    print(
        f"  return_15:             "
        f"{features['return_15']:.4f}%"
    )

    print(
        f"  return_30:             "
        f"{features['return_30']:.4f}%"
    )

    print(
        f"  return_60:             "
        f"{features['return_60']:.4f}%"
    )

    print(
        f"  bullish_ratio:         "
        f"{features['bullish_ratio']:.4f}"
    )

    print(
        f"  bearish_ratio:         "
        f"{features['bearish_ratio']:.4f}"
    )

    print(
        f"  directional_imbalance: "
        f"{features['directional_imbalance']:.4f}"
    )

    print(
        f"  volatility:            "
        f"{features['volatility']:.4f}"
    )

    print(
        f"  volatility_ratio:      "
        f"{features['volatility_ratio']:.4f}"
    )

    print(
        f"  location_in_range:     "
        f"{features['location_in_range']:.4f}"
    )

    print(
        f"  normalized_slope:      "
        f"{features['normalized_slope']:.4f}"
    )

    print()

    print(
        "IMPORTANT:"
    )

    print(
        "This section describes the current "
        "60-candle structure only."
    )

    print(
        "It is NOT a trading signal."
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)

    print(
        "MLAI v3.3.3 "
        "SIMILAR STRUCTURE + REGIME MODEL"
    )

    print("=" * 70)

    print()

    print(
        f"Market file: {DATA_FILE}"
    )

    print(
        f"Current window: {WINDOW}"
    )

    print(
        f"Horizons: {HORIZONS}"
    )

    print(
        f"Threshold: +/-{THRESHOLD}%"
    )

    print(
        f"Calibration ratio: "
        f"{CALIBRATION_RATIO}"
    )

    # --------------------------------------------------------
    # Load market data READ ONLY.
    # --------------------------------------------------------

    with open(
        DATA_FILE,
        "rb"
    ) as f:

        data = pickle.load(f)

    candles = data["candles"]

    print()

    print(
        f"Total candles: {len(candles)}"
    )

    # --------------------------------------------------------
    # Protection
    # --------------------------------------------------------

    print()

    print("=" * 70)

    print(
        "PROTECTION CHECK"
    )

    print("=" * 70)

    print(
        "market_data.bin: READ ONLY"
    )

    print(
        "mlai_v31.py: NOT MODIFIED"
    )

    print(
        "learning memory: NOT MODIFIED"
    )

    print(
        "production logic: NOT MODIFIED"
    )

    # --------------------------------------------------------
    # Historical tests
    # --------------------------------------------------------

    for horizon in HORIZONS:

        records = build_records(
            candles,
            horizon
        )

        run_horizon(
            records,
            horizon
        )

    # --------------------------------------------------------
    # Current state
    # --------------------------------------------------------

    current_market_analysis(
        candles
    )

    # --------------------------------------------------------
    # Final verdict
    # --------------------------------------------------------

    print()

    print("=" * 70)

    print(
        "MLAI v3.3.3 DIAGNOSTIC VERDICT"
    )

    print("=" * 70)

    print()

    print(
        "This experiment tests whether the current "
        "60-candle structure resembles earlier "
        "historical structures."
    )

    print()

    print(
        "Historical neighbors are selected only "
        "from data occurring before the validation "
        "period."
    )

    print()

    print(
        "The model evaluates:"
    )

    print(
        "  BUY"
    )

    print(
        "  SELL"
    )

    print(
        "  NO TRADE"
    )

    print()

    print(
        "The regime is also included:"
    )

    print(
        "  Directional regime"
    )

    print(
        "  Volatility regime"
    )

    print()

    print(
        "IMPORTANT:"
    )

    print(
        "This is a diagnostic experiment only."
    )

    print(
        "It does NOT create a trading signal."
    )

    print(
        "It does NOT modify market_data.bin."
    )

    print(
        "It does NOT modify mlai_v31.py."
    )

    print(
        "It does NOT modify learning memory."
    )

    print(
        "It does NOT change production thresholds."
    )

    print()

    print(
        "The main question is:"
    )

    print(
        "Does a similar historical 60-candle "
        "structure produce a repeatable outcome "
        "on completely unseen chronological data?"
    )

    print()

    print("=" * 70)

    print(
        "MLAI v3.3.3 TEST COMPLETE"
    )

    print("=" * 70)


if __name__ == "__main__":

    main()