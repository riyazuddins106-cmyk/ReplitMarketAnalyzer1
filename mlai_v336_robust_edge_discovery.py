import os
import math
import pickle
from collections import Counter, defaultdict
from statistics import mean, pstdev


# ============================================================
# MLAI v3.3.6
# ROBUST EDGE DISCOVERY
# ============================================================
#
# PURPOSE
# -------
# Discover whether market structures contain repeatable
# directional information that survives chronological
# walk-forward validation.
#
# IMPORTANT
# ---------
# This program is diagnostic/research only.
#
# It MUST NOT:
#   - modify market_data.bin
#   - modify mlai_v31.py
#   - modify learning memory
#   - modify production thresholds
#   - generate production trading signals
#
# v3.3.6 adds:
#   1. Multi-dimensional structure features
#   2. Momentum state
#   3. Market location
#   4. Candle-body/wick structure
#   5. Trend consistency
#   6. Historical nearest-neighbor similarity
#   7. Walk-forward validation
#   8. Minimum sample requirements
#   9. Cross-fold stability testing
#  10. Baseline comparisons
#
# ============================================================


MARKET_FILE = "market_data.bin"

WINDOW = 60
HORIZONS = [4, 8, 16]

CLASSIFICATION_THRESHOLD = 0.0015

N_FOLDS = 4

MIN_CALIBRATION_SAMPLES = 40
MIN_VALIDATION_SAMPLES = 20

NEIGHBORS = [10, 20, 40]

# Minimum number of historical examples required before
# considering a discovered structure.
MIN_RULE_SAMPLES = 40

# Minimum directional confidence in calibration.
MIN_RULE_CONFIDENCE = 0.55

# Minimum validation accuracy to even report a possible edge.
MIN_VALIDATION_ACCURACY = 0.55

# Required number of folds in which a rule must remain
# directionally useful.
MIN_STABLE_FOLDS = 2


# ============================================================
# PROTECTION
# ============================================================

def protection_check():
    print("=" * 70)
    print("PROTECTION CHECK")
    print("=" * 70)

    print(f"{MARKET_FILE}: READ ONLY")
    print("mlai_v31.py: NOT MODIFIED")
    print("learning memory: NOT MODIFIED")
    print("production thresholds: NOT MODIFIED")

    print()


# ============================================================
# DATA LOADING
# ============================================================

def load_market_data():
    if not os.path.exists(MARKET_FILE):
        raise FileNotFoundError(
            f"{MARKET_FILE} was not found in the current directory."
        )

    with open(MARKET_FILE, "rb") as f:
        data = pickle.load(f)

    return data


def extract_candles(data):
    """
    Attempt to support common candle-storage formats.

    Expected logical candle fields:
        timestamp
        open
        high
        low
        close
    """

    candles = None

    if isinstance(data, dict):

        possible_keys = [
            "candles",
            "data",
            "records",
            "ohlc",
            "market_data",
            "prices",
        ]

        for key in possible_keys:
            if key in data and isinstance(data[key], list):
                candles = data[key]
                break

    elif isinstance(data, list):
        candles = data

    if candles is None:
        raise ValueError(
            "Could not locate candle list inside market_data.bin."
        )

    normalized = []

    for i, c in enumerate(candles):

        if isinstance(c, dict):

            def get_value(*names):
                for name in names:
                    if name in c:
                        return c[name]
                return None

            ts = get_value(
                "timestamp",
                "time",
                "datetime",
                "date",
            )

            o = get_value("open", "Open", "o")
            h = get_value("high", "High", "h")
            l = get_value("low", "Low", "l")
            cl = get_value("close", "Close", "c")

        elif isinstance(c, (list, tuple)) and len(c) >= 5:

            ts = c[0]
            o = c[1]
            h = c[2]
            l = c[3]
            cl = c[4]

        else:
            continue

        try:
            normalized.append(
                {
                    "timestamp": ts,
                    "open": float(o),
                    "high": float(h),
                    "low": float(l),
                    "close": float(cl),
                }
            )
        except Exception:
            continue

    if len(normalized) < WINDOW + max(HORIZONS) + 10:
        raise ValueError(
            f"Not enough valid candles. Found {len(normalized)}."
        )

    return normalized


# ============================================================
# BASIC HELPERS
# ============================================================

def safe_div(a, b):
    if b == 0:
        return 0.0
    return a / b


def clamp(x, low=-10.0, high=10.0):
    return max(low, min(high, x))


def pct_return(a, b):
    if a == 0:
        return 0.0
    return (b - a) / a


def avg(values):
    if not values:
        return 0.0
    return sum(values) / len(values)


def std(values):
    if len(values) < 2:
        return 0.0

    return pstdev(values)


# ============================================================
# CANDLE FEATURES
# ============================================================

def candle_features(c):
    o = c["open"]
    h = c["high"]
    l = c["low"]
    cl = c["close"]

    candle_range = max(h - l, 1e-12)

    body = abs(cl - o)

    upper_wick = h - max(o, cl)
    lower_wick = min(o, cl) - l

    direction = 1 if cl > o else -1 if cl < o else 0

    return {
        "range": candle_range,
        "body": body,
        "body_ratio": safe_div(body, candle_range),
        "upper_wick_ratio": safe_div(upper_wick, candle_range),
        "lower_wick_ratio": safe_div(lower_wick, candle_range),
        "direction": direction,
    }


# ============================================================
# STRUCTURE FEATURES
# ============================================================

def build_structure(candles, end_index):
    """
    Uses candles ending at end_index.

    No future candle is used.
    """

    start = end_index - WINDOW + 1

    if start < 0:
        return None

    window = candles[start:end_index + 1]

    closes = [c["close"] for c in window]
    opens = [c["open"] for c in window]
    highs = [c["high"] for c in window]
    lows = [c["low"] for c in window]

    if len(closes) < WINDOW:
        return None

    current = closes[-1]

    return_15 = pct_return(closes[-16], current)
    return_30 = pct_return(closes[-31], current)
    return_60 = pct_return(closes[0], current)

    directions = []

    body_ratios = []
    upper_wicks = []
    lower_wicks = []
    ranges = []

    for c in window:
        f = candle_features(c)

        directions.append(f["direction"])
        body_ratios.append(f["body_ratio"])
        upper_wicks.append(f["upper_wick_ratio"])
        lower_wicks.append(f["lower_wick_ratio"])
        ranges.append(f["range"])

    bullish_count = sum(1 for x in directions if x > 0)
    bearish_count = sum(1 for x in directions if x < 0)

    bullish_ratio = safe_div(bullish_count, WINDOW)
    bearish_ratio = safe_div(bearish_count, WINDOW)

    directional_imbalance = bullish_ratio - bearish_ratio

    volatility_values = []

    for i in range(1, len(closes)):
        previous = closes[i - 1]

        if previous != 0:
            volatility_values.append(
                abs((closes[i] - previous) / previous)
            )

    volatility = avg(volatility_values)

    recent_volatility = avg(volatility_values[-15:])

    older_volatility = avg(volatility_values[:30])

    volatility_ratio = safe_div(
        recent_volatility,
        older_volatility
    )

    highest = max(highs)
    lowest = min(lows)

    location_in_range = safe_div(
        current - lowest,
        highest - lowest
    )

    normalized_slope = return_60

    # --------------------------------------------------------
    # MOMENTUM
    # --------------------------------------------------------

    momentum_5 = pct_return(closes[-6], current)
    momentum_10 = pct_return(closes[-11], current)
    momentum_20 = pct_return(closes[-21], current)

    momentum_acceleration = momentum_5 - (
        momentum_20 / 4.0
    )

    # --------------------------------------------------------
    # TREND AGREEMENT
    # --------------------------------------------------------

    trend_signs = [
        1 if return_15 > 0 else -1 if return_15 < 0 else 0,
        1 if return_30 > 0 else -1 if return_30 < 0 else 0,
        1 if return_60 > 0 else -1 if return_60 < 0 else 0,
    ]

    positive_trends = sum(1 for x in trend_signs if x > 0)
    negative_trends = sum(1 for x in trend_signs if x < 0)

    if positive_trends == 3:
        trend_consistency = "bullish"
    elif negative_trends == 3:
        trend_consistency = "bearish"
    elif positive_trends > negative_trends:
        trend_consistency = "bullish_bias"
    elif negative_trends > positive_trends:
        trend_consistency = "bearish_bias"
    else:
        trend_consistency = "mixed"

    # --------------------------------------------------------
    # VOLATILITY REGIME
    # --------------------------------------------------------

    if volatility_ratio > 1.15:
        volatility_regime = "expanding"
    elif volatility_ratio < 0.85:
        volatility_regime = "contracting"
    else:
        volatility_regime = "stable"

    # --------------------------------------------------------
    # DIRECTIONAL REGIME
    # --------------------------------------------------------

    if return_60 > 0.005:
        directional_regime = "bullish"
    elif return_60 < -0.005:
        directional_regime = "bearish"
    elif return_30 > 0.002:
        directional_regime = "bullish_bias"
    elif return_30 < -0.002:
        directional_regime = "bearish_bias"
    else:
        directional_regime = "neutral"

    # --------------------------------------------------------
    # MARKET LOCATION
    # --------------------------------------------------------

    if location_in_range >= 0.80:
        location_state = "upper_range"
    elif location_in_range <= 0.20:
        location_state = "lower_range"
    else:
        location_state = "middle_range"

    # --------------------------------------------------------
    # MOMENTUM STATE
    # --------------------------------------------------------

    if momentum_5 > 0 and momentum_10 > 0:
        momentum_state = "positive"
    elif momentum_5 < 0 and momentum_10 < 0:
        momentum_state = "negative"
    else:
        momentum_state = "mixed"

    # --------------------------------------------------------
    # CANDLE STRUCTURE
    # --------------------------------------------------------

    recent_body_ratio = avg(body_ratios[-10:])
    recent_upper_wick = avg(upper_wicks[-10:])
    recent_lower_wick = avg(lower_wicks[-10:])

    recent_directions = directions[-10:]

    recent_bullish = sum(
        1 for x in recent_directions if x > 0
    )

    recent_bearish = sum(
        1 for x in recent_directions if x < 0
    )

    if recent_bullish >= 7:
        candle_pressure = "bullish_pressure"
    elif recent_bearish >= 7:
        candle_pressure = "bearish_pressure"
    else:
        candle_pressure = "balanced"

    # --------------------------------------------------------
    # BREAKOUT / REJECTION STATE
    # --------------------------------------------------------

    previous_high = max(highs[:-5])
    previous_low = min(lows[:-5])

    recent_high = max(highs[-5:])
    recent_low = min(lows[-5:])

    breakout_up = recent_high > previous_high
    breakout_down = recent_low < previous_low

    if breakout_up and not breakout_down:
        range_event = "up_breakout"
    elif breakout_down and not breakout_up:
        range_event = "down_breakout"
    elif breakout_up and breakout_down:
        range_event = "volatile_break"
    else:
        range_event = "inside_range"

    return {
        # numerical features
        "return_15": return_15,
        "return_30": return_30,
        "return_60": return_60,

        "bullish_ratio": bullish_ratio,
        "bearish_ratio": bearish_ratio,
        "directional_imbalance": directional_imbalance,

        "volatility": volatility,
        "volatility_ratio": volatility_ratio,

        "location_in_range": location_in_range,
        "normalized_slope": normalized_slope,

        "momentum_5": momentum_5,
        "momentum_10": momentum_10,
        "momentum_20": momentum_20,
        "momentum_acceleration": momentum_acceleration,

        "recent_body_ratio": recent_body_ratio,
        "recent_upper_wick": recent_upper_wick,
        "recent_lower_wick": recent_lower_wick,

        # categorical features
        "directional_regime": directional_regime,
        "volatility_regime": volatility_regime,
        "trend_consistency": trend_consistency,
        "location_state": location_state,
        "momentum_state": momentum_state,
        "candle_pressure": candle_pressure,
        "range_event": range_event,
    }


# ============================================================
# STRUCTURE SIGNATURE
# ============================================================

NUMERIC_FEATURES = [
    "return_15",
    "return_30",
    "return_60",
    "bullish_ratio",
    "bearish_ratio",
    "directional_imbalance",
    "volatility_ratio",
    "location_in_range",
    "normalized_slope",
    "momentum_5",
    "momentum_10",
    "momentum_20",
    "momentum_acceleration",
    "recent_body_ratio",
    "recent_upper_wick",
    "recent_lower_wick",
]


CATEGORICAL_FEATURES = [
    "directional_regime",
    "volatility_regime",
    "trend_consistency",
    "location_state",
    "momentum_state",
    "candle_pressure",
    "range_event",
]


def structure_signature(f):
    return tuple(
        f[x] for x in CATEGORICAL_FEATURES
    )


# ============================================================
# FEATURE DISTANCE
# ============================================================

def numeric_distance(a, b):
    """
    Robust normalized distance.

    Features are normalized so price scale itself does not
    dominate similarity.
    """

    scales = {
        "return_15": 0.005,
        "return_30": 0.008,
        "return_60": 0.015,

        "bullish_ratio": 0.20,
        "bearish_ratio": 0.20,
        "directional_imbalance": 0.20,

        "volatility_ratio": 0.30,
        "location_in_range": 0.30,
        "normalized_slope": 0.015,

        "momentum_5": 0.004,
        "momentum_10": 0.006,
        "momentum_20": 0.010,
        "momentum_acceleration": 0.005,

        "recent_body_ratio": 0.30,
        "recent_upper_wick": 0.30,
        "recent_lower_wick": 0.30,
    }

    total = 0.0

    for key in NUMERIC_FEATURES:
        scale = scales.get(key, 1.0)

        d = abs(a[key] - b[key])

        total += min(d / scale, 5.0) ** 2

    categorical_penalty = 0.0

    for key in CATEGORICAL_FEATURES:

        if a[key] != b[key]:
            categorical_penalty += 0.75

    return math.sqrt(total + categorical_penalty)


# ============================================================
# OUTCOME CLASSIFICATION
# ============================================================

def classify_outcome(candles, index, horizon):
    """
    Classification is based ONLY on future candles after index.

    BUY:
        future return >= +0.15%

    SELL:
        future return <= -0.15%

    NEUTRAL:
        otherwise
    """

    future_index = index + horizon

    if future_index >= len(candles):
        return None

    current_price = candles[index]["close"]
    future_price = candles[future_index]["close"]

    if current_price == 0:
        return None

    future_return = (
        future_price - current_price
    ) / current_price

    if future_return >= CLASSIFICATION_THRESHOLD:
        return "BUY"

    if future_return <= -CLASSIFICATION_THRESHOLD:
        return "SELL"

    return "NEUTRAL"


# ============================================================
# BUILD HISTORICAL RECORDS
# ============================================================

def build_records(candles, horizon):
    records = []

    last_index = len(candles) - horizon - 1

    for index in range(WINDOW - 1, last_index + 1):

        features = build_structure(
            candles,
            index
        )

        if features is None:
            continue

        outcome = classify_outcome(
            candles,
            index,
            horizon
        )

        if outcome is None:
            continue

        records.append(
            {
                "index": index,
                "timestamp": candles[index]["timestamp"],
                "features": features,
                "outcome": outcome,
            }
        )

    return records


# ============================================================
# BASELINE METRICS
# ============================================================

def accuracy(predictions):
    if not predictions:
        return 0.0

    correct = sum(
        1 for p, y in predictions
        if p == y
    )

    return correct / len(predictions)


def precision(predictions, direction):
    selected = [
        (p, y)
        for p, y in predictions
        if p == direction
    ]

    if not selected:
        return 0.0

    correct = sum(
        1 for p, y in selected
        if p == y
    )

    return correct / len(selected)


def print_baselines(validation):
    print()
    print("-" * 70)
    print("BASELINE COMPARISON")
    print("-" * 70)

    outcomes = [
        r["outcome"]
        for r in validation
    ]

    total = len(outcomes)

    if total == 0:
        return

    counts = Counter(outcomes)

    buy_rate = counts["BUY"] / total
    sell_rate = counts["SELL"] / total
    neutral_rate = counts["NEUTRAL"] / total

    print(f"Validation records: {total}")

    print(
        f"BUY frequency:     {buy_rate:.2%}"
    )

    print(
        f"SELL frequency:    {sell_rate:.2%}"
    )

    print(
        f"NEUTRAL frequency: {neutral_rate:.2%}"
    )

    majority = max(
        ["BUY", "SELL", "NEUTRAL"],
        key=lambda x: counts[x]
    )

    majority_accuracy = counts[majority] / total

    print(
        f"Majority baseline ({majority}): "
        f"{majority_accuracy:.2%}"
    )


# ============================================================
# RULE DISCOVERY
# ============================================================

def discover_rules(calibration):
    """
    Discover categorical combinations that have enough samples.

    IMPORTANT:
        Only calibration records are used.
    """

    groups = defaultdict(list)

    for record in calibration:

        f = record["features"]

        key = (
            f["directional_regime"],
            f["volatility_regime"],
            f["trend_consistency"],
            f["location_state"],
            f["momentum_state"],
            f["candle_pressure"],
            f["range_event"],
        )

        groups[key].append(record["outcome"])

    rules = {}

    for key, outcomes in groups.items():

        if len(outcomes) < MIN_RULE_SAMPLES:
            continue

        directional = [
            x for x in outcomes
            if x in ("BUY", "SELL")
        ]

        if not directional:
            continue

        counts = Counter(directional)

        buy_count = counts["BUY"]
        sell_count = counts["SELL"]

        if buy_count >= sell_count:
            direction = "BUY"
            directional_count = buy_count
        else:
            direction = "SELL"
            directional_count = sell_count

        confidence = safe_div(
            directional_count,
            len(directional)
        )

        if confidence < MIN_RULE_CONFIDENCE:
            continue

        rules[key] = {
            "direction": direction,
            "confidence": confidence,
            "samples": len(outcomes),
            "directional_samples": len(directional),
            "buy_count": buy_count,
            "sell_count": sell_count,
        }

    return rules


# ============================================================
# RULE MATCHING
# ============================================================

def rule_key(features):
    return (
        features["directional_regime"],
        features["volatility_regime"],
        features["trend_consistency"],
        features["location_state"],
        features["momentum_state"],
        features["candle_pressure"],
        features["range_event"],
    )


# ============================================================
# APPLY LOCKED RULES
# ============================================================

def apply_rules(validation, rules):
    predictions = []

    for record in validation:

        key = rule_key(record["features"])

        rule = rules.get(key)

        if rule is None:
            continue

        predictions.append(
            (
                rule["direction"],
                record["outcome"],
                rule["confidence"],
                key,
            )
        )

    return predictions


# ============================================================
# NEAREST NEIGHBOR PREDICTION
# ============================================================

def nearest_neighbor_prediction(
    target,
    calibration,
    k
):
    scored = []

    for record in calibration:

        distance = numeric_distance(
            target["features"],
            record["features"]
        )

        scored.append(
            (
                distance,
                record["outcome"],
                record,
            )
        )

    scored.sort(
        key=lambda x: x[0]
    )

    neighbors = scored[:k]

    if not neighbors:
        return None

    directional = [
        x[1]
        for x in neighbors
        if x[1] in ("BUY", "SELL")
    ]

    if not directional:
        return None

    counts = Counter(directional)

    if counts["BUY"] >= counts["SELL"]:
        direction = "BUY"
        winning = counts["BUY"]
    else:
        direction = "SELL"
        winning = counts["SELL"]

    confidence = safe_div(
        winning,
        len(directional)
    )

    return {
        "direction": direction,
        "confidence": confidence,
        "neighbors": len(neighbors),
    }


def evaluate_neighbors(calibration, validation, k):
    predictions = []

    for record in validation:

        result = nearest_neighbor_prediction(
            record,
            calibration,
            k
        )

        if result is None:
            continue

        predictions.append(
            (
                result["direction"],
                record["outcome"],
                result["confidence"],
            )
        )

    return predictions


# ============================================================
# WALK-FORWARD SPLITS
# ============================================================

def build_walk_forward_folds(records):
    """
    Chronological expanding calibration.

    Example with 4 folds:

        Fold 4:
            calibration = earliest block
            validation  = next block

        Fold 3:
            calibration = earliest 2 blocks
            validation  = next block

        Fold 2:
            calibration = earliest 3 blocks
            validation  = next block

        Fold 1:
            calibration = earliest 4 blocks
            validation  = final block

    No validation data is used for discovery.
    """

    n = len(records)

    validation_size = n // (N_FOLDS + 1)

    folds = []

    for fold in range(N_FOLDS, 0, -1):

        validation_start = (
            fold * validation_size
        )

        validation_end = (
            validation_start + validation_size
        )

        calibration = records[:validation_start]

        validation = records[
            validation_start:validation_end
        ]

        if (
            len(calibration) >= MIN_CALIBRATION_SAMPLES
            and len(validation) >= MIN_VALIDATION_SAMPLES
        ):
            folds.append(
                (
                    fold,
                    calibration,
                    validation,
                )
            )

    return folds


# ============================================================
# PRINT RULES
# ============================================================

def print_locked_rules(rules):

    print()
    print(
        f"Locked rules discovered: {len(rules)}"
    )

    if not rules:
        print("No rule met discovery criteria.")
        return

    ranked = sorted(
        rules.items(),
        key=lambda x: (
            x[1]["confidence"],
            x[1]["samples"]
        ),
        reverse=True
    )

    for key, rule in ranked[:20]:

        print(
            f"LOCKED {key} -> "
            f"{rule['direction']} "
            f"({rule['confidence']:.2%} confidence, "
            f"{rule['samples']} samples)"
        )


# ============================================================
# RULE VALIDATION METRICS
# ============================================================

def evaluate_rule_predictions(predictions):

    if not predictions:
        return {
            "n": 0,
            "accuracy": 0.0,
            "coverage": 0.0,
            "buy_precision": 0.0,
            "sell_precision": 0.0,
        }

    correct = sum(
        1 for p, y, *_ in predictions
        if p == y
    )

    buy = [
        x for x in predictions
        if x[0] == "BUY"
    ]

    sell = [
        x for x in predictions
        if x[0] == "SELL"
    ]

    buy_correct = sum(
        1 for x in buy
        if x[0] == x[1]
    )

    sell_correct = sum(
        1 for x in sell
        if x[0] == x[1]
    )

    return {
        "n": len(predictions),
        "accuracy": safe_div(
            correct,
            len(predictions)
        ),
        "coverage": 0.0,
        "buy_precision": safe_div(
            buy_correct,
            len(buy)
        ),
        "sell_precision": safe_div(
            sell_correct,
            len(sell)
        ),
    }


# ============================================================
# FOLD VALIDATION
# ============================================================

def run_rule_walk_forward(records):

    folds = build_walk_forward_folds(records)

    all_predictions = []

    fold_results = []

    for fold_number, calibration, validation in folds:

        print()
        print("-" * 70)
        print(f"FOLD {fold_number}")
        print("-" * 70)

        print(
            f"Calibration records: {len(calibration)}"
        )

        print(
            f"Validation records:  {len(validation)}"
        )

        print(
            "Rule discovery: CALIBRATION ONLY"
        )

        rules = discover_rules(
            calibration
        )

        print_locked_rules(rules)

        predictions = apply_rules(
            validation,
            rules
        )

        metrics = evaluate_rule_predictions(
            predictions
        )

        metrics["coverage"] = safe_div(
            len(predictions),
            len(validation)
        )

        print()
        print(
            f"Validation matched records: "
            f"{metrics['n']}"
        )

        print(
            f"Directional accuracy: "
            f"{metrics['accuracy']:.2%}"
        )

        print(
            f"Coverage: "
            f"{metrics['coverage']:.2%}"
        )

        print(
            f"BUY precision: "
            f"{metrics['buy_precision']:.2%}"
        )

        print(
            f"SELL precision: "
            f"{metrics['sell_precision']:.2%}"
        )

        fold_results.append(
            {
                "fold": fold_number,
                "rules": rules,
                "metrics": metrics,
            }
        )

        all_predictions.extend(
            predictions
        )

    return fold_results, all_predictions


# ============================================================
# AGGREGATED RESULTS
# ============================================================

def print_aggregated_rule_result(
    predictions,
    total_validation
):

    print()
    print("=" * 70)
    print("AGGREGATED LOCKED OUT-OF-SAMPLE RESULT")
    print("=" * 70)

    if not predictions:

        print("No locked rules generated predictions.")

        return

    correct = sum(
        1 for p, y, *_ in predictions
        if p == y
    )

    buys = [
        x for x in predictions
        if x[0] == "BUY"
    ]

    sells = [
        x for x in predictions
        if x[0] == "SELL"
    ]

    buy_correct = sum(
        1 for x in buys
        if x[0] == x[1]
    )

    sell_correct = sum(
        1 for x in sells
        if x[0] == x[1]
    )

    print(
        f"Validation predictions: "
        f"{len(predictions)}"
    )

    print(
        f"Directional accuracy: "
        f"{safe_div(correct, len(predictions)):.2%}"
    )

    print(
        f"Coverage: "
        f"{safe_div(len(predictions), total_validation):.2%}"
    )

    print(
        f"BUY predictions: {len(buys)}"
    )

    print(
        f"SELL predictions: {len(sells)}"
    )

    print(
        f"BUY precision: "
        f"{safe_div(buy_correct, len(buys)):.2%}"
    )

    print(
        f"SELL precision: "
        f"{safe_div(sell_correct, len(sells)):.2%}"
    )


# ============================================================
# CROSS-FOLD STABILITY
# ============================================================

def stability_analysis(fold_results):

    print()
    print("=" * 70)
    print("CROSS-FOLD STABILITY ANALYSIS")
    print("=" * 70)

    if not fold_results:
        print("No fold results.")
        return

    rule_stats = defaultdict(list)

    for fold in fold_results:

        rules = fold["rules"]

        for key, rule in rules.items():

            rule_stats[key].append(
                {
                    "fold": fold["fold"],
                    "direction": rule["direction"],
                    "confidence": rule["confidence"],
                    "samples": rule["samples"],
                }
            )

    stable = []

    for key, values in rule_stats.items():

        if len(values) < MIN_STABLE_FOLDS:
            continue

        directions = {
            x["direction"]
            for x in values
        }

        if len(directions) != 1:
            continue

        avg_confidence = avg(
            x["confidence"]
            for x in values
        )

        total_samples = sum(
            x["samples"]
            for x in values
        )

        stable.append(
            (
                key,
                values,
                avg_confidence,
                total_samples,
            )
        )

    stable.sort(
        key=lambda x: (
            x[2],
            x[3]
        ),
        reverse=True
    )

    print(
        f"Stable rules: {len(stable)}"
    )

    for key, values, confidence, samples in stable[:20]:

        direction = values[0]["direction"]

        print()
        print(
            f"STABLE RULE:"
        )

        print(
            f"  Structure: {key}"
        )

        print(
            f"  Direction: {direction}"
        )

        print(
            f"  Folds: {len(values)}"
        )

        print(
            f"  Average calibration confidence: "
            f"{confidence:.2%}"
        )

        print(
            f"  Combined samples: {samples}"
        )

    return stable


# ============================================================
# NEAREST NEIGHBOR TEST
# ============================================================

def run_neighbor_tests(
    calibration,
    validation
):

    print()
    print("-" * 70)
    print("HISTORICAL SIMILARITY TEST")
    print("-" * 70)

    for k in NEIGHBORS:

        predictions = evaluate_neighbors(
            calibration,
            validation,
            k
        )

        if not predictions:

            print(
                f"TOP {k}: no predictions"
            )

            continue

        correct = sum(
            1 for p, y, _ in predictions
            if p == y
        )

        buys = [
            x for x in predictions
            if x[0] == "BUY"
        ]

        sells = [
            x for x in predictions
            if x[0] == "SELL"
        ]

        buy_correct = sum(
            1 for x in buys
            if x[0] == x[1]
        )

        sell_correct = sum(
            1 for x in sells
            if x[0] == x[1]
        )

        print()
        print(
            f"TOP {k} NEIGHBORS"
        )

        print(
            f"Predictions: {len(predictions)}"
        )

        print(
            f"Accuracy: "
            f"{safe_div(correct, len(predictions)):.2%}"
        )

        print(
            f"Coverage: "
            f"{safe_div(len(predictions), len(validation)):.2%}"
        )

        print(
            f"BUY precision: "
            f"{safe_div(buy_correct, len(buys)):.2%}"
        )

        print(
            f"SELL precision: "
            f"{safe_div(sell_correct, len(sells)):.2%}"
        )


# ============================================================
# CURRENT STRUCTURE
# ============================================================

def print_current_structure(candles):

    print()
    print("=" * 70)
    print("CURRENT 60-CANDLE MARKET STRUCTURE")
    print("=" * 70)

    index = len(candles) - 1

    features = build_structure(
        candles,
        index
    )

    print(
        f"Latest index: {index}"
    )

    print(
        f"Latest candle: "
        f"{candles[index]['timestamp']}"
    )

    print(
        f"Latest price: "
        f"{candles[index]['close']}"
    )

    print()
    print(
        f"Directional regime: "
        f"{features['directional_regime']}"
    )

    print(
        f"Volatility regime: "
        f"{features['volatility_regime']}"
    )

    print(
        f"Trend consistency: "
        f"{features['trend_consistency']}"
    )

    print(
        f"Location state: "
        f"{features['location_state']}"
    )

    print(
        f"Momentum state: "
        f"{features['momentum_state']}"
    )

    print(
        f"Candle pressure: "
        f"{features['candle_pressure']}"
    )

    print(
        f"Range event: "
        f"{features['range_event']}"
    )

    print()
    print("NUMERIC STRUCTURE FEATURES")

    for key in NUMERIC_FEATURES:

        print(
            f"{key:25s}: "
            f"{features[key]:.6f}"
        )

    return features


# ============================================================
# CURRENT HISTORICAL NEIGHBORS
# ============================================================

def current_neighbor_evidence(
    candles,
    records,
    current_features
):

    target = {
        "features": current_features
    }

    print()
    print("=" * 70)
    print("CURRENT STRUCTURE HISTORICAL EVIDENCE")
    print("=" * 70)

    for k in NEIGHBORS:

        scored = []

        for record in records:

            distance = numeric_distance(
                current_features,
                record["features"]
            )

            scored.append(
                (
                    distance,
                    record["outcome"]
                )
            )

        scored.sort(
            key=lambda x: x[0]
        )

        neighbors = scored[:k]

        outcomes = [
            x[1]
            for x in neighbors
        ]

        counts = Counter(
            outcomes
        )

        directional = [
            x
            for x in outcomes
            if x in ("BUY", "SELL")
        ]

        print()
        print(
            f"TOP {k} HISTORICAL NEIGHBORS"
        )

        print(
            f"Bullish outcomes: "
            f"{counts['BUY']}"
        )

        print(
            f"Neutral outcomes: "
            f"{counts['NEUTRAL']}"
        )

        print(
            f"Bearish outcomes: "
            f"{counts['SELL']}"
        )

        if not directional:

            print(
                "Diagnostic prediction: NO TRADE"
            )

            print(
                "Confidence: 0.00%"
            )

            continue

        buy = counts["BUY"]
        sell = counts["SELL"]

        if buy > sell:

            prediction = "BUY"
            confidence = safe_div(
                buy,
                len(directional)
            )

        elif sell > buy:

            prediction = "SELL"
            confidence = safe_div(
                sell,
                len(directional)
            )

        else:

            prediction = "NO TRADE"
            confidence = 0.50

        print(
            f"Diagnostic prediction: "
            f"{prediction}"
        )

        print(
            f"Confidence: "
            f"{confidence:.2%}"
        )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("MLAI v3.3.6 ROBUST EDGE DISCOVERY")
    print("=" * 70)

    print()
    print("Purpose:")
    print(
        "Determine whether multi-dimensional market structures "
        "contain repeatable directional information that survives "
        "strict chronological walk-forward validation."
    )

    print()

    protection_check()

    # --------------------------------------------------------
    # LOAD DATA
    # --------------------------------------------------------

    data = load_market_data()

    candles = extract_candles(data)

    print(
        f"Data type: {type(data).__name__}"
    )

    print(
        f"Total candles: {len(candles)}"
    )

    print(
        "PASS: market_data.bin loaded."
    )

    print(
        "PASS: Close prices extracted."
    )

    print(
        "PASS: market_data.bin will NOT be modified."
    )

    print(
        "PASS: Production MLAI will NOT be modified."
    )

    # --------------------------------------------------------
    # RESULTS STORAGE
    # --------------------------------------------------------

    all_horizon_results = {}

    # --------------------------------------------------------
    # HORIZONS
    # --------------------------------------------------------

    for horizon in HORIZONS:

        print()
        print()
        print("=" * 70)
        print(
            f"HORIZON: {horizon} CANDLES"
        )
        print("=" * 70)

        records = build_records(
            candles,
            horizon
        )

        print(
            f"Historical records: {len(records)}"
        )

        if len(records) < 100:

            print(
                "WARNING: insufficient records."
            )

            continue

        folds = build_walk_forward_folds(
            records
        )

        print(
            f"Walk-forward folds: {len(folds)}"
        )

        # ----------------------------------------------------
        # BASELINE USING FINAL VALIDATION BLOCK
        # ----------------------------------------------------

        if folds:

            final_fold = folds[-1]

            print_baselines(
                final_fold[2]
            )

        # ----------------------------------------------------
        # LOCKED RULE WALK-FORWARD
        # ----------------------------------------------------

        fold_results, all_predictions = (
            run_rule_walk_forward(records)
        )

        total_validation = sum(
            len(x[2])
            for x in folds
        )

        print_aggregated_rule_result(
            all_predictions,
            total_validation
        )

        # ----------------------------------------------------
        # STABILITY
        # ----------------------------------------------------

        stable_rules = stability_analysis(
            fold_results
        )

        # ----------------------------------------------------
        # FINAL-FOLD NEIGHBOR TEST
        # ----------------------------------------------------

        if folds:

            _, calibration, validation = folds[-1]

            run_neighbor_tests(
                calibration,
                validation
            )

        all_horizon_results[horizon] = {
            "records": len(records),
            "folds": fold_results,
            "stable_rules": stable_rules,
        }

    # ========================================================
    # CURRENT STRUCTURE
    # ========================================================

    current_features = print_current_structure(
        candles
    )

    # --------------------------------------------------------
    # Current evidence using longest horizon
    # --------------------------------------------------------

    if 16 in HORIZONS:

        records_16 = build_records(
            candles,
            16
        )

        current_neighbor_evidence(
            candles,
            records_16,
            current_features
        )

    # ========================================================
    # FINAL VERDICT
    # ========================================================

    print()
    print()
    print("=" * 70)
    print("MLAI v3.3.6 FINAL VERDICT")
    print("=" * 70)

    print()
    print(
        "This experiment is diagnostic only."
    )

    print(
        "No production model was changed."
    )

    print(
        "No learning memory was changed."
    )

    print(
        "market_data.bin was READ ONLY."
    )

    print(
        "mlai_v31.py was NOT modified."
    )

    print()

    print(
        "A structure is considered a candidate edge ONLY when:"
    )

    print(
        "  1. It has sufficient calibration samples."
    )

    print(
        "  2. Calibration confidence exceeds the minimum."
    )

    print(
        "  3. The direction remains stable across folds."
    )

    print(
        "  4. The rule is tested on unseen chronological data."
    )

    print(
        "  5. The out-of-sample result is materially better "
        "than a trivial baseline."
    )

    print()

    print(
        "IMPORTANT:"
    )

    print(
        "High calibration accuracy alone is NOT sufficient."
    )

    print(
        "High historical similarity accuracy alone is NOT sufficient."
    )

    print(
        "No rule should be promoted to production from this script."
    )

    print()

    print(
        "MLAI v3.3.6 COMPLETE"
    )


if __name__ == "__main__":
    main()