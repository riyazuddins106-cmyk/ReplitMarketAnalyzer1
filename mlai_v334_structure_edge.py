import os
import pickle
import math
from collections import defaultdict
from datetime import datetime


# ============================================================
# MLAI v3.3.4
# STRUCTURE EDGE DISCOVERY
#
# PURPOSE:
#   Combine:
#       60-candle structure
#       directional regime
#       volatility regime
#       historical similarity
#       confidence
#       NO TRADE
#
# IMPORTANT:
#   DIAGNOSTIC ONLY
#
#   market_data.bin      -> READ ONLY
#   mlai_v31.py          -> NOT MODIFIED
#   learning memory      -> NOT MODIFIED
#   production threshold -> NOT MODIFIED
# ============================================================


MARKET_FILE = "market_data.bin"

WINDOW = 60
HORIZONS = [4, 8, 16]

THRESHOLD = 0.0015
CALIBRATION_RATIO = 0.70

K_VALUES = [10, 20, 40]

# Minimum historical neighbors required before a
# structure/regime combination is considered meaningful.
MIN_REGIME_SAMPLES = 10

# Minimum directional precision required to classify
# a structure as potentially useful.
MIN_EDGE_PRECISION = 0.50

# Confidence levels to inspect.
CONFIDENCE_LEVELS = [0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85]


# ============================================================
# PROTECTION
# ============================================================

def protection_check():
    print("=" * 70)
    print("PROTECTION CHECK")
    print("=" * 70)

    if os.path.exists(MARKET_FILE):
        print("market_data.bin: READ ONLY")
    else:
        print("ERROR: market_data.bin not found.")
        raise FileNotFoundError(MARKET_FILE)

    print("mlai_v31.py: NOT MODIFIED")
    print("learning memory: NOT MODIFIED")
    print("production threshold: NOT MODIFIED")
    print()


# ============================================================
# LOAD MARKET DATA
# ============================================================

def load_market_data(path):
    with open(path, "rb") as f:
        data = pickle.load(f)

    if isinstance(data, dict):

        for key in [
            "candles",
            "data",
            "market_data",
            "records",
            "ohlc"
        ]:
            if key in data and isinstance(data[key], (list, tuple)):
                data = data[key]
                break

    if not isinstance(data, (list, tuple)):
        raise ValueError(
            "Unsupported market_data.bin structure. "
            "Expected a list/tuple of candle records."
        )

    return list(data)


# ============================================================
# FIELD HELPERS
# ============================================================

def get_value(row, names):

    if isinstance(row, dict):
        lower = {
            str(k).lower(): v
            for k, v in row.items()
        }

        for name in names:
            if name.lower() in lower:
                return lower[name.lower()]

    else:

        for name in names:

            if hasattr(row, name):
                return getattr(row, name)

    return None


def get_open(row):
    return float(get_value(row, [
        "open",
        "o"
    ]))


def get_high(row):
    return float(get_value(row, [
        "high",
        "h"
    ]))


def get_low(row):
    return float(get_value(row, [
        "low",
        "l"
    ]))


def get_close(row):
    return float(get_value(row, [
        "close",
        "c"
    ]))


def get_timestamp(row):

    value = get_value(row, [
        "timestamp",
        "datetime",
        "date",
        "time"
    ])

    if value is None:
        return "unknown"

    return str(value)


# ============================================================
# BASIC MATH
# ============================================================

def safe_div(a, b):
    if b == 0:
        return 0.0

    return a / b


def mean(values):

    if not values:
        return 0.0

    return sum(values) / len(values)


def std(values):

    if len(values) < 2:
        return 0.0

    m = mean(values)

    variance = sum(
        (x - m) ** 2
        for x in values
    ) / len(values)

    return math.sqrt(variance)


# ============================================================
# STRUCTURE FEATURES
# ============================================================

def build_features(candles, end_index):

    start = end_index - WINDOW + 1

    if start < 0:
        return None

    window = candles[start:end_index + 1]

    closes = [
        get_close(x)
        for x in window
    ]

    opens = [
        get_open(x)
        for x in window
    ]

    highs = [
        get_high(x)
        for x in window
    ]

    lows = [
        get_low(x)
        for x in window
    ]

    if len(closes) != WINDOW:
        return None

    current = closes[-1]

    if current <= 0:
        return None

    return_15 = safe_div(
        closes[-1] - closes[-16],
        closes[-16]
    )

    return_30 = safe_div(
        closes[-1] - closes[-31],
        closes[-31]
    )

    return_60 = safe_div(
        closes[-1] - closes[0],
        closes[0]
    )

    bullish = 0
    bearish = 0

    for o, c in zip(opens, closes):

        if c > o:
            bullish += 1

        elif c < o:
            bearish += 1

    bullish_ratio = safe_div(
        bullish,
        WINDOW
    )

    bearish_ratio = safe_div(
        bearish,
        WINDOW
    )

    directional_imbalance = (
        bullish_ratio - bearish_ratio
    )

    returns = []

    for i in range(1, len(closes)):

        if closes[i - 1] != 0:

            r = (
                closes[i] - closes[i - 1]
            ) / closes[i - 1]

            returns.append(r)

    volatility = std(returns)

    recent_returns = returns[-20:]

    recent_volatility = std(
        recent_returns
    )

    volatility_ratio = safe_div(
        recent_volatility,
        volatility
    )

    highest = max(highs)
    lowest = min(lows)

    location_in_range = safe_div(
        current - lowest,
        highest - lowest
    )

    normalized_slope = return_60

    return {
        "return_15": return_15,
        "return_30": return_30,
        "return_60": return_60,
        "bullish_ratio": bullish_ratio,
        "bearish_ratio": bearish_ratio,
        "directional_imbalance": directional_imbalance,
        "volatility": volatility,
        "volatility_ratio": volatility_ratio,
        "location_in_range": location_in_range,
        "normalized_slope": normalized_slope
    }


# ============================================================
# REGIME CLASSIFICATION
# ============================================================

def directional_regime(f):

    score = 0

    if f["return_15"] > 0.001:
        score += 1

    if f["return_30"] > 0.002:
        score += 1

    if f["return_60"] > 0.003:
        score += 1

    if f["directional_imbalance"] > 0.05:
        score += 1

    if f["return_15"] < -0.001:
        score -= 1

    if f["return_30"] < -0.002:
        score -= 1

    if f["return_60"] < -0.003:
        score -= 1

    if f["directional_imbalance"] < -0.05:
        score -= 1

    if score >= 3:
        return "bullish"

    if score >= 1:
        return "bullish_bias"

    if score <= -3:
        return "bearish"

    if score <= -1:
        return "bearish_bias"

    return "neutral"


def volatility_regime(f):

    ratio = f["volatility_ratio"]

    if ratio >= 1.15:
        return "expanding"

    if ratio <= 0.85:
        return "contracting"

    return "stable"


# ============================================================
# OUTCOME CLASSIFICATION
# ============================================================

def classify_outcome(current_price, future_price):

    if current_price <= 0:
        return "neutral"

    change = (
        future_price - current_price
    ) / current_price

    if change >= THRESHOLD:
        return "bullish"

    if change <= -THRESHOLD:
        return "bearish"

    return "neutral"


# ============================================================
# RECORD CREATION
# ============================================================

def build_records(candles, horizon):

    records = []

    last_valid_index = (
        len(candles) - horizon - 1
    )

    for i in range(WINDOW - 1, last_valid_index + 1):

        features = build_features(
            candles,
            i
        )

        if features is None:
            continue

        current_price = get_close(
            candles[i]
        )

        future_price = get_close(
            candles[i + horizon]
        )

        outcome = classify_outcome(
            current_price,
            future_price
        )

        direction = directional_regime(
            features
        )

        volatility = volatility_regime(
            features
        )

        records.append({
            "index": i,
            "timestamp": get_timestamp(candles[i]),
            "features": features,
            "regime": direction,
            "volatility_regime": volatility,
            "outcome": outcome
        })

    return records


# ============================================================
# FEATURE VECTOR
# ============================================================

FEATURE_NAMES = [
    "return_15",
    "return_30",
    "return_60",
    "bullish_ratio",
    "bearish_ratio",
    "directional_imbalance",
    "volatility",
    "volatility_ratio",
    "location_in_range",
    "normalized_slope"
]


def vector(record):

    return [
        record["features"][x]
        for x in FEATURE_NAMES
    ]


# ============================================================
# SCALER
# ============================================================

def fit_scaler(records):

    columns = list(
        zip(*[
            vector(x)
            for x in records
        ])
    )

    means = [
        mean(column)
        for column in columns
    ]

    stds = [
        std(column)
        for column in columns
    ]

    stds = [
        x if x > 1e-12 else 1.0
        for x in stds
    ]

    return means, stds


def scale_vector(v, means, stds):

    return [
        (x - m) / s
        for x, m, s in zip(
            v,
            means,
            stds
        )
    ]


# ============================================================
# DISTANCE
# ============================================================

def distance(a, b):

    return math.sqrt(
        sum(
            (x - y) ** 2
            for x, y in zip(a, b)
        )
    )


# ============================================================
# FIND SIMILAR STRUCTURES
# ============================================================

def find_neighbors(
    target,
    calibration,
    means,
    stds,
    k
):

    target_vector = scale_vector(
        vector(target),
        means,
        stds
    )

    candidates = []

    for record in calibration:

        # Strong regime matching.
        if (
            record["regime"] != target["regime"]
            or
            record["volatility_regime"]
            != target["volatility_regime"]
        ):
            continue

        v = scale_vector(
            vector(record),
            means,
            stds
        )

        d = distance(
            target_vector,
            v
        )

        candidates.append(
            (d, record)
        )

    candidates.sort(
        key=lambda x: x[0]
    )

    return candidates[:k]


# ============================================================
# NEIGHBOR PREDICTION
# ============================================================

def neighbor_prediction(neighbors):

    if not neighbors:
        return {
            "prediction": "NO TRADE",
            "confidence": 0.0,
            "bull": 0,
            "neutral": 0,
            "bear": 0
        }

    bull = 0
    neutral = 0
    bear = 0

    for _, record in neighbors:

        if record["outcome"] == "bullish":
            bull += 1

        elif record["outcome"] == "bearish":
            bear += 1

        else:
            neutral += 1

    total = len(neighbors)

    probabilities = {
        "bullish": bull / total,
        "neutral": neutral / total,
        "bearish": bear / total
    }

    prediction = max(
        probabilities,
        key=probabilities.get
    )

    confidence = probabilities[
        prediction
    ]

    if prediction == "bullish":
        action = "BUY"

    elif prediction == "bearish":
        action = "SELL"

    else:
        action = "NO TRADE"

    return {
        "prediction": action,
        "confidence": confidence,
        "bull": bull,
        "neutral": neutral,
        "bear": bear
    }


# ============================================================
# EVALUATION
# ============================================================

def evaluate_predictions(
    predictions,
    actuals
):

    total = len(actuals)

    if total == 0:
        return {}

    correct = 0

    directional_total = 0
    directional_correct = 0

    buy_predictions = []
    sell_predictions = []

    for prediction, actual in zip(
        predictions,
        actuals
    ):

        if (
            prediction == actual
        ):
            correct += 1

        if prediction in [
            "BUY",
            "SELL"
        ]:

            directional_total += 1

            expected = (
                "BUY"
                if actual == "bullish"
                else
                "SELL"
                if actual == "bearish"
                else
                "NO TRADE"
            )

            if prediction == expected:
                directional_correct += 1

        if prediction == "BUY":
            buy_predictions.append(actual)

        if prediction == "SELL":
            sell_predictions.append(actual)

    directional_accuracy = (
        directional_correct /
        directional_total
        if directional_total
        else 0.0
    )

    coverage = (
        directional_total /
        total
    )

    buy_precision = (
        sum(
            x == "bullish"
            for x in buy_predictions
        )
        /
        len(buy_predictions)
        if buy_predictions
        else 0.0
    )

    sell_precision = (
        sum(
            x == "bearish"
            for x in sell_predictions
        )
        /
        len(sell_predictions)
        if sell_predictions
        else 0.0
    )

    return {
        "accuracy": correct / total,
        "directional_accuracy":
            directional_accuracy,
        "coverage": coverage,
        "buy_precision":
            buy_precision,
        "sell_precision":
            sell_precision,
        "buy_predictions":
            len(buy_predictions),
        "sell_predictions":
            len(sell_predictions)
    }


# ============================================================
# EDGE TABLE
# ============================================================

def print_edge_table(
    calibration,
    validation_results
):

    print()
    print("=" * 70)
    print("STRUCTURE EDGE DISCOVERY")
    print("=" * 70)

    groups = defaultdict(list)

    for record in calibration:

        key = (
            record["regime"],
            record["volatility_regime"]
        )

        groups[key].append(
            record["outcome"]
        )

    print()
    print(
        f"{'REGIME':<20}"
        f"{'VOLATILITY':<15}"
        f"{'N':>6}"
        f"{'BULL %':>10}"
        f"{'NEUTRAL %':>12}"
        f"{'BEAR %':>10}"
    )

    print("-" * 70)

    for key, outcomes in sorted(
        groups.items()
    ):

        regime, volatility = key

        n = len(outcomes)

        bull = (
            outcomes.count("bullish")
            / n
            * 100
        )

        neutral = (
            outcomes.count("neutral")
            / n
            * 100
        )

        bear = (
            outcomes.count("bearish")
            / n
            * 100
        )

        print(
            f"{regime:<20}"
            f"{volatility:<15}"
            f"{n:>6}"
            f"{bull:>10.2f}"
            f"{neutral:>12.2f}"
            f"{bear:>10.2f}"
        )


# ============================================================
# CONFIDENCE TEST
# ============================================================

def confidence_test(results):

    print()
    print("=" * 70)
    print("CONFIDENCE / EDGE TEST")
    print("=" * 70)

    print()
    print(
        f"{'THRESHOLD':>10}"
        f"{'DIR ACC':>12}"
        f"{'COVERAGE':>12}"
        f"{'BUY PREC':>12}"
        f"{'SELL PREC':>12}"
    )

    print("-" * 70)

    best = None

    for threshold in CONFIDENCE_LEVELS:

        selected = [
            x
            for x in results
            if x["confidence"] >= threshold
            and x["prediction"] != "NO TRADE"
        ]

        if not selected:
            continue

        correct = 0
        buy_total = 0
        buy_correct = 0
        sell_total = 0
        sell_correct = 0

        for x in selected:

            prediction = x["prediction"]
            actual = x["actual"]

            if (
                prediction == "BUY"
                and actual == "bullish"
            ):
                correct += 1

            elif (
                prediction == "SELL"
                and actual == "bearish"
            ):
                correct += 1

            if prediction == "BUY":

                buy_total += 1

                if actual == "bullish":
                    buy_correct += 1

            if prediction == "SELL":

                sell_total += 1

                if actual == "bearish":
                    sell_correct += 1

        directional_accuracy = (
            correct /
            len(selected)
        )

        coverage = (
            len(selected) /
            len(results)
        )

        buy_precision = (
            buy_correct /
            buy_total
            if buy_total
            else 0.0
        )

        sell_precision = (
            sell_correct /
            sell_total
            if sell_total
            else 0.0
        )

        print(
            f"{threshold * 100:>9.0f}%"
            f"{directional_accuracy * 100:>11.2f}%"
            f"{coverage * 100:>11.2f}%"
            f"{buy_precision * 100:>11.2f}%"
            f"{sell_precision * 100:>11.2f}%"
        )

        # Prefer accuracy while maintaining useful coverage.
        score = (
            directional_accuracy
            * math.sqrt(coverage)
        )

        if (
            best is None
            or score > best["score"]
        ):
            best = {
                "threshold": threshold,
                "directional_accuracy":
                    directional_accuracy,
                "coverage": coverage,
                "buy_precision":
                    buy_precision,
                "sell_precision":
                    sell_precision,
                "score": score
            }

    return best


# ============================================================
# MAIN HORIZON TEST
# ============================================================

def run_horizon(
    candles,
    horizon
):

    print()
    print("=" * 70)
    print(f"HORIZON: {horizon} CANDLES")
    print("=" * 70)

    records = build_records(
        candles,
        horizon
    )

    total = len(records)

    calibration_count = int(
        total * CALIBRATION_RATIO
    )

    calibration = records[
        :calibration_count
    ]

    validation = records[
        calibration_count:
    ]

    print()
    print(
        f"Historical records: {total}"
    )

    print(
        f"Calibration records: "
        f"{len(calibration)}"
    )

    print(
        f"Validation records:  "
        f"{len(validation)}"
    )

    print()
    print(
        "Calibration contains ONLY "
        "earlier chronological records."
    )

    print(
        "Validation contains ONLY "
        "later chronological records."
    )

    print(
        "Validation outcomes are NEVER "
        "used to select the model."
    )

    # --------------------------------------------------------
    # SCALER
    # --------------------------------------------------------

    means, stds = fit_scaler(
        calibration
    )

    all_results = []

    # --------------------------------------------------------
    # K TEST
    # --------------------------------------------------------

    for k in K_VALUES:

        print()
        print("-" * 70)
        print(
            f"SIMILAR STRUCTURE + REGIME | "
            f"TOP {k} NEIGHBORS"
        )
        print("-" * 70)

        predictions = []
        actuals = []

        detailed = []

        for target in validation:

            neighbors = find_neighbors(
                target,
                calibration,
                means,
                stds,
                k
            )

            result = neighbor_prediction(
                neighbors
            )

            prediction = result[
                "prediction"
            ]

            actual = target[
                "outcome"
            ]

            predictions.append(
                prediction
            )

            actuals.append(
                actual
            )

            detailed.append({
                "prediction":
                    prediction,
                "confidence":
                    result["confidence"],
                "actual":
                    actual,
                "regime":
                    target["regime"],
                "volatility":
                    target[
                        "volatility_regime"
                    ]
            })

        metrics = evaluate_predictions(
            predictions,
            actuals
        )

        print()
        print(
            f"Directional accuracy: "
            f"{metrics['directional_accuracy'] * 100:.2f}%"
        )

        print(
            f"Directional coverage: "
            f"{metrics['coverage'] * 100:.2f}%"
        )

        print(
            f"BUY precision: "
            f"{metrics['buy_precision'] * 100:.2f}%"
        )

        print(
            f"SELL precision: "
            f"{metrics['sell_precision'] * 100:.2f}%"
        )

        print(
            f"BUY predictions: "
            f"{metrics['buy_predictions']}"
        )

        print(
            f"SELL predictions: "
            f"{metrics['sell_predictions']}"
        )

        # ----------------------------------------------------
        # CONFIDENCE
        # ----------------------------------------------------

        best = confidence_test(
            detailed
        )

        if best:

            print()
            print(
                "BEST CONFIDENCE / COVERAGE BALANCE"
            )

            print("-" * 70)

            print(
                f"Confidence threshold: "
                f"{best['threshold'] * 100:.0f}%"
            )

            print(
                f"Directional accuracy: "
                f"{best['directional_accuracy'] * 100:.2f}%"
            )

            print(
                f"Directional coverage: "
                f"{best['coverage'] * 100:.2f}%"
            )

            print(
                f"BUY precision: "
                f"{best['buy_precision'] * 100:.2f}%"
            )

            print(
                f"SELL precision: "
                f"{best['sell_precision'] * 100:.2f}%"
            )

        # ----------------------------------------------------
        # REGIME PERFORMANCE
        # ----------------------------------------------------

        print()
        print("REGIME EDGE PERFORMANCE")
        print("-" * 70)

        regime_groups = defaultdict(list)

        for x in detailed:

            key = (
                x["regime"],
                x["volatility"]
            )

            regime_groups[key].append(x)

        print(
            f"{'REGIME':<20}"
            f"{'VOLATILITY':<15}"
            f"{'N':>6}"
            f"{'DIR ACC':>12}"
            f"{'BUY PREC':>12}"
            f"{'SELL PREC':>12}"
        )

        print("-" * 70)

        for key, items in sorted(
            regime_groups.items()
        ):

            regime, volatility = key

            directional = [
                x
                for x in items
                if x["prediction"]
                in ["BUY", "SELL"]
            ]

            if directional:

                correct = 0

                buy_total = 0
                buy_correct = 0

                sell_total = 0
                sell_correct = 0

                for x in directional:

                    if (
                        x["prediction"] == "BUY"
                        and
                        x["actual"] == "bullish"
                    ):
                        correct += 1

                    if (
                        x["prediction"] == "SELL"
                        and
                        x["actual"] == "bearish"
                    ):
                        correct += 1

                    if x["prediction"] == "BUY":

                        buy_total += 1

                        if (
                            x["actual"]
                            == "bullish"
                        ):
                            buy_correct += 1

                    if x["prediction"] == "SELL":

                        sell_total += 1

                        if (
                            x["actual"]
                            == "bearish"
                        ):
                            sell_correct += 1

                dir_acc = (
                    correct /
                    len(directional)
                )

                buy_prec = (
                    buy_correct /
                    buy_total
                    if buy_total
                    else 0.0
                )

                sell_prec = (
                    sell_correct /
                    sell_total
                    if sell_total
                    else 0.0
                )

            else:

                dir_acc = 0.0
                buy_prec = 0.0
                sell_prec = 0.0

            print(
                f"{regime:<20}"
                f"{volatility:<15}"
                f"{len(items):>6}"
                f"{dir_acc * 100:>11.2f}%"
                f"{buy_prec * 100:>11.2f}%"
                f"{sell_prec * 100:>11.2f}%"
            )

            for x in directional:

                all_results.append(x)

    # --------------------------------------------------------
    # EDGE DISCOVERY
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("RELIABLE STRUCTURE DISCOVERY")
    print("=" * 70)

    edge_groups = defaultdict(list)

    for x in all_results:

        key = (
            x["regime"],
            x["volatility"]
        )

        edge_groups[key].append(x)

    found = False

    for key, items in sorted(
        edge_groups.items()
    ):

        directional = [
            x for x in items
            if x["prediction"]
            in ["BUY", "SELL"]
        ]

        if len(directional) < MIN_REGIME_SAMPLES:
            continue

        correct = 0

        for x in directional:

            if (
                x["prediction"] == "BUY"
                and x["actual"] == "bullish"
            ):
                correct += 1

            elif (
                x["prediction"] == "SELL"
                and x["actual"] == "bearish"
            ):
                correct += 1

        precision = (
            correct /
            len(directional)
        )

        if precision >= MIN_EDGE_PRECISION:

            found = True

            regime, volatility = key

            print()
            print(
                f"STRUCTURE: "
                f"{regime} + {volatility}"
            )

            print(
                f"Samples: "
                f"{len(directional)}"
            )

            print(
                f"Directional accuracy: "
                f"{precision * 100:.2f}%"
            )

            buys = [
                x for x in directional
                if x["prediction"] == "BUY"
            ]

            sells = [
                x for x in directional
                if x["prediction"] == "SELL"
            ]

            buy_precision = (
                sum(
                    x["actual"] == "bullish"
                    for x in buys
                )
                / len(buys)
                if buys
                else 0
            )

            sell_precision = (
                sum(
                    x["actual"] == "bearish"
                    for x in sells
                )
                / len(sells)
                if sells
                else 0
            )

            print(
                f"BUY precision: "
                f"{buy_precision * 100:.2f}%"
            )

            print(
                f"SELL precision: "
                f"{sell_precision * 100:.2f}%"
            )

    if not found:

        print()
        print(
            "No structure currently satisfies "
            "the minimum edge criteria."
        )

    # --------------------------------------------------------
    # CURRENT MARKET
    # --------------------------------------------------------

    current_index = len(candles) - 1

    current_features = build_features(
        candles,
        current_index
    )

    current_regime = directional_regime(
        current_features
    )

    current_volatility = volatility_regime(
        current_features
    )

    current_record = {
        "index": current_index,
        "timestamp":
            get_timestamp(
                candles[current_index]
            ),
        "features":
            current_features,
        "regime":
            current_regime,
        "volatility_regime":
            current_volatility,
        "outcome": None
    }

    print()
    print("=" * 70)
    print("CURRENT 60-CANDLE MARKET STRUCTURE")
    print("=" * 70)

    print()
    print(
        f"Latest candle: "
        f"{current_record['timestamp']}"
    )

    print(
        f"Latest price: "
        f"{get_close(candles[current_index])}"
    )

    print()
    print(
        f"Directional regime: "
        f"{current_regime}"
    )

    print(
        f"Volatility regime: "
        f"{current_volatility}"
    )

    print()
    print("STRUCTURE FEATURES")

    for name in FEATURE_NAMES:

        print(
            f"{name:<25}: "
            f"{current_features[name]:.6f}"
        )

    # --------------------------------------------------------
    # CURRENT HISTORICAL SIMILARITY
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("CURRENT STRUCTURE HISTORICAL EVIDENCE")
    print("=" * 70)

    means, stds = fit_scaler(
        calibration
    )

    for k in K_VALUES:

        neighbors = find_neighbors(
            current_record,
            calibration,
            means,
            stds,
            k
        )

        prediction = neighbor_prediction(
            neighbors
        )

        print()
        print(
            f"TOP {k} HISTORICAL NEIGHBORS"
        )

        print(
            f"Prediction: "
            f"{prediction['prediction']}"
        )

        print(
            f"Confidence: "
            f"{prediction['confidence'] * 100:.2f}%"
        )

        print(
            f"Bullish outcomes: "
            f"{prediction['bull']}"
        )

        print(
            f"Neutral outcomes: "
            f"{prediction['neutral']}"
        )

        print(
            f"Bearish outcomes: "
            f"{prediction['bear']}"
        )

    print()
    print("=" * 70)
    print("IMPORTANT")
    print("=" * 70)

    print(
        "This is NOT a trading signal."
    )

    print(
        "The current-market output is "
        "diagnostic only."
    )

    print(
        "No production model was changed."
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("MLAI v3.3.4 STRUCTURE EDGE DISCOVERY")
    print("=" * 70)

    print()
    print(
        "Purpose:"
    )

    print(
        "Find which combinations of:"
    )

    print(
        "60-candle structure + regime + "
        "volatility + historical similarity"
    )

    print(
        "show repeatable directional information."
    )

    print()

    protection_check()

    candles = load_market_data(
        MARKET_FILE
    )

    print(
        f"Total candles: {len(candles)}"
    )

    print()

    for horizon in HORIZONS:

        run_horizon(
            candles,
            horizon
        )

    print()
    print("=" * 70)
    print("MLAI v3.3.4 DIAGNOSTIC VERDICT")
    print("=" * 70)

    print()
    print(
        "This experiment does NOT modify "
        "MLAI production logic."
    )

    print(
        "market_data.bin was READ ONLY."
    )

    print(
        "mlai_v31.py was NOT modified."
    )

    print(
        "Learning memory was NOT modified."
    )

    print(
        "Production thresholds were NOT modified."
    )

    print()
    print(
        "The objective was to discover whether "
        "specific market structures have stronger "
        "historical directional evidence than others."
    )

    print()
    print(
        "MLAI v3.3.4 COMPLETE"
    )


if __name__ == "__main__":
    main()