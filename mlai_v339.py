
import os
import pickle
import math
from collections import Counter, defaultdict


# ============================================================
# MLAI v3.3.9
# PURGED CALIBRATION-LOCKED QUANTILE VALIDATION
#
# PURPOSE
# ------------------------------------------------------------
# v3.3.8 correctly locked quantile boundaries to calibration.
#
# v3.3.9 adds the next critical methodological protection:
#
# PURGED WALK-FORWARD VALIDATION
#
# A calibration record is allowed ONLY when its complete
# future outcome window finishes BEFORE validation begins.
#
# Therefore:
#
# calibration
#     ↓
# PURGE / EMBARGO
#     ↓
# validation
#
# Validation NEVER participates in:
#   - feature binning
#   - quantile fitting
#   - rule discovery
#   - threshold discovery
#   - rule modification
#
# PRODUCTION SAFETY
# ------------------------------------------------------------
# market_data.bin : READ ONLY
# mlai_v31.py      : NOT MODIFIED
# learning memory  : NOT MODIFIED
# ============================================================


MARKET_FILE = "market_data.bin"

WINDOW = 60
HORIZONS = [4, 8, 16]

FOLDS = 4

MIN_CALIBRATION_SAMPLES = 20
MIN_VALIDATION_SAMPLES = 20

MIN_CONFIDENCE = 0.45
MIN_LIFT = 0.10

STABILITY_MIN_FOLDS = 2

TOP_RULES_TO_PRINT = 20


# ============================================================
# LOAD MARKET DATA
# ============================================================

print("=" * 70)
print("MLAI v3.3.9 PURGED CALIBRATION-LOCKED QUANTILE VALIDATION")
print("=" * 70)

print("""
Purpose:
1. Fit quantile boundaries from calibration ONLY.
2. Apply identical locked boundaries to validation.
3. Discover rules from calibration ONLY.
4. Lock rules before validation.
5. Purge calibration records whose future outcome window
   overlaps the validation period.
6. Measure chronological out-of-sample performance.

NO validation data is used for learning.
""")

print("=" * 70)
print("PROTECTION CHECK")
print("=" * 70)

print("market_data.bin: READ ONLY")
print("mlai_v31.py: NOT MODIFIED")
print("learning memory: NOT MODIFIED")
print("production thresholds: NOT MODIFIED")
print("validation quantiles: NOT FIT")
print("validation rules: NOT DISCOVERED")
print("future-label overlap: PURGED")

if not os.path.exists(MARKET_FILE):
    raise FileNotFoundError(MARKET_FILE)

with open(MARKET_FILE, "rb") as f:
    market_data = pickle.load(f)

print()
print("Data type:", type(market_data).__name__)

if isinstance(market_data, dict):
    print("Total candles:", len(market_data.get("candles", [])))
else:
    raise ValueError("Unexpected market_data.bin structure")


# ============================================================
# EXTRACT CLOSES
# ============================================================

candles = market_data.get("candles", [])

if len(candles) < WINDOW + max(HORIZONS) + 100:
    raise ValueError("Not enough candles")

closes = []

for candle in candles:

    if isinstance(candle, dict):

        close = candle.get("close")

        if close is None:
            close = candle.get("c")

        if close is not None:
            value = float(close)

            if math.isfinite(value):
                closes.append(value)

    elif isinstance(candle, (list, tuple)):

        # Common OHLC ordering:
        # timestamp, open, high, low, close

        if len(candle) >= 5:

            value = float(candle[4])

            if math.isfinite(value):
                closes.append(value)

print()
print("PASS: market_data.bin loaded.")
print("PASS: Close prices extracted.")
print("PASS: market_data.bin will NOT be modified.")
print("PASS: Production MLAI will NOT be modified.")


# ============================================================
# SAFE NUMERIC HELPERS
# ============================================================

def safe_return(values, n):

    if len(values) <= n:
        return 0.0

    base = values[-n - 1]

    if base == 0:
        return 0.0

    return (values[-1] / base) - 1.0


def mean(values):

    if not values:
        return 0.0

    return sum(values) / len(values)


def stdev(values):

    if len(values) < 2:
        return 0.0

    m = mean(values)

    return math.sqrt(
        sum((x - m) ** 2 for x in values)
        / (len(values) - 1)
    )


def percentile(sorted_values, p):

    if not sorted_values:
        return 0.0

    if len(sorted_values) == 1:
        return sorted_values[0]

    position = (
        (len(sorted_values) - 1)
        * p
    )

    lower = int(math.floor(position))
    upper = int(math.ceil(position))

    if lower == upper:
        return sorted_values[lower]

    weight = position - lower

    return (
        sorted_values[lower] * (1.0 - weight)
        + sorted_values[upper] * weight
    )


# ============================================================
# RAW FEATURE EXTRACTION
# ============================================================

def raw_features(index):

    if index < WINDOW:
        return None

    segment = closes[
        index - WINDOW + 1:index + 1
    ]

    if len(segment) < WINDOW:
        return None

    current = segment[-1]

    r5 = safe_return(segment, 5)
    r10 = safe_return(segment, 10)
    r15 = safe_return(segment, 15)
    r20 = safe_return(segment, 20)
    r30 = safe_return(segment, 30)

    # IMPORTANT:
    # Preserve v3.3.8 behavior.
    #
    # The 60-candle window contains 60 prices, therefore
    # safe_return(segment, 60) cannot calculate a true
    # 60-period return.
    #
    # Do NOT silently change this feature in the purging fix.
    r60 = safe_return(segment, 59)

    # --------------------------------------------------------
    # Returns
    # --------------------------------------------------------

    returns = []

    for i in range(1, len(segment)):

        prev = segment[i - 1]

        if prev != 0:

            value = (
                segment[i] / prev
            ) - 1.0

            if math.isfinite(value):
                returns.append(value)

    volatility = stdev(returns)

    recent_returns = returns[-20:]

    if recent_returns:
        recent_volatility = stdev(
            recent_returns
        )
    else:
        recent_volatility = volatility

    if volatility > 0:
        volatility_ratio = (
            recent_volatility
            / volatility
        )
    else:
        volatility_ratio = 1.0

    # --------------------------------------------------------
    # Directional structure
    # --------------------------------------------------------

    bullish = 0
    bearish = 0

    for i in range(1, len(segment)):

        if segment[i] > segment[i - 1]:
            bullish += 1

        elif segment[i] < segment[i - 1]:
            bearish += 1

    total_directional = (
        bullish + bearish
    )

    if total_directional:

        bullish_ratio = (
            bullish
            / total_directional
        )

        bearish_ratio = (
            bearish
            / total_directional
        )

        directional_imbalance = (
            bullish_ratio
            - bearish_ratio
        )

    else:

        bullish_ratio = 0.5
        bearish_ratio = 0.5
        directional_imbalance = 0.0

    # --------------------------------------------------------
    # Range location
    # --------------------------------------------------------

    lo = min(segment)
    hi = max(segment)

    if hi > lo:

        location_in_range = (
            (current - lo)
            / (hi - lo)
        )

    else:

        location_in_range = 0.5

    # --------------------------------------------------------
    # Normalized slope
    # --------------------------------------------------------

    if segment[0] != 0:

        normalized_slope = (
            segment[-1]
            / segment[0]
        ) - 1.0

    else:

        normalized_slope = 0.0

    # --------------------------------------------------------
    # Momentum
    # --------------------------------------------------------

    momentum_5 = r5
    momentum_10 = r10
    momentum_20 = r20

    momentum_acceleration = (
        momentum_5
        - momentum_10
    )

    # --------------------------------------------------------
    # Recent candle-body proxies
    # --------------------------------------------------------

    recent_window = segment[-10:]

    recent_changes = []

    for i in range(
        1,
        len(recent_window)
    ):

        previous = (
            recent_window[i - 1]
        )

        current_value = (
            recent_window[i]
        )

        if previous != 0:

            value = (
                abs(
                    current_value
                    - previous
                )
                / previous
            )

            if math.isfinite(value):
                recent_changes.append(value)

    recent_body_ratio = mean(
        recent_changes
    )

    positive_moves = [
        x
        for x in recent_changes
        if x > 0
    ]

    recent_upper_wick = (
        mean(positive_moves)
        if positive_moves
        else 0.0
    )

    recent_lower_wick = (
        mean(recent_changes)
        if recent_changes
        else 0.0
    )

    return {

        "return_5": r5,
        "return_10": r10,
        "return_15": r15,
        "return_20": r20,
        "return_30": r30,
        "return_60": r60,

        "bullish_ratio":
            bullish_ratio,

        "bearish_ratio":
            bearish_ratio,

        "directional_imbalance":
            directional_imbalance,

        "volatility":
            volatility,

        "volatility_ratio":
            volatility_ratio,

        "location_in_range":
            location_in_range,

        "normalized_slope":
            normalized_slope,

        "momentum_5":
            momentum_5,

        "momentum_10":
            momentum_10,

        "momentum_20":
            momentum_20,

        "momentum_acceleration":
            momentum_acceleration,

        "recent_body_ratio":
            recent_body_ratio,

        "recent_upper_wick":
            recent_upper_wick,

        "recent_lower_wick":
            recent_lower_wick,
    }


# ============================================================
# OUTCOME
# ============================================================

def classify_outcome(index, horizon):

    if index + horizon >= len(closes):
        return None

    start = closes[index]

    if start == 0:
        return None

    future = closes[
        index + horizon
    ]

    change = (
        future / start
    ) - 1.0

    if change >= 0.0015:
        return "BUY"

    if change <= -0.0015:
        return "SELL"

    return "NEUTRAL"


# ============================================================
# BUILD RAW RECORDS
# ============================================================

def build_records(horizon):

    records = []

    last_index = (
        len(closes)
        - horizon
        - 1
    )

    for index in range(
        WINDOW,
        last_index + 1
    ):

        features = raw_features(index)

        if features is None:
            continue

        outcome = classify_outcome(
            index,
            horizon
        )

        if outcome is None:
            continue

        records.append({

            "index": index,

            "features": features,

            "outcome": outcome

        })

    return records


# ============================================================
# QUANTILE FEATURES
# ============================================================

QUANTILE_FEATURES = [

    "return_5",
    "return_10",
    "return_15",
    "return_20",
    "return_30",
    "return_60",

    "bullish_ratio",
    "bearish_ratio",
    "directional_imbalance",

    "volatility",
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


# ============================================================
# FIT QUANTILE MODEL
# ============================================================

def fit_quantile_model(
    calibration_records
):

    """
    CRITICAL:

    Quantile boundaries are learned ONLY
    from calibration records.

    Validation records are NEVER passed here.
    """

    model = {}

    for feature in QUANTILE_FEATURES:

        values = []

        for record in calibration_records:

            value = (
                record["features"]
                .get(feature)
            )

            if (
                value is not None
                and math.isfinite(value)
            ):

                values.append(
                    float(value)
                )

        values.sort()

        if len(values) < 5:
            continue

        q1 = percentile(
            values,
            1.0 / 3.0
        )

        q2 = percentile(
            values,
            2.0 / 3.0
        )

        model[feature] = {

            "q1": q1,

            "q2": q2,

            "min": values[0],

            "max": values[-1],
        }

    return model


# ============================================================
# APPLY LOCKED QUANTILE MODEL
# ============================================================

def apply_quantile_model(
    features,
    model
):

    """
    Apply calibration-locked boundaries.

    NO boundary calculation occurs here.
    """

    result = {}

    for feature, boundaries in (
        model.items()
    ):

        value = features.get(feature)

        if (
            value is None
            or not math.isfinite(value)
        ):
            continue

        if value <= boundaries["q1"]:

            bucket = "q1"

        elif value <= boundaries["q2"]:

            bucket = "q2"

        else:

            bucket = "q3"

        result[feature] = bucket

    return result


# ============================================================
# DISCRETE REGIME FEATURES
# ============================================================

def derive_regime_features(
    features,
    quantized
):

    result = dict(quantized)

    volatility_ratio = (
        features["volatility_ratio"]
    )

    location = (
        features["location_in_range"]
    )

    imbalance = (
        features["directional_imbalance"]
    )

    momentum = (
        features["momentum_20"]
    )

    if volatility_ratio > 1.10:

        result["volatility_regime"] = (
            "expanding"
        )

    elif volatility_ratio < 0.90:

        result["volatility_regime"] = (
            "contracting"
        )

    else:

        result["volatility_regime"] = (
            "stable"
        )

    if location >= 0.80:

        result["location_state"] = (
            "upper_range"
        )

    elif location <= 0.20:

        result["location_state"] = (
            "lower_range"
        )

    else:

        result["location_state"] = (
            "middle_range"
        )

    if imbalance >= 0.10:

        result["directional_regime"] = (
            "bullish"
        )

    elif imbalance <= -0.10:

        result["directional_regime"] = (
            "bearish"
        )

    else:

        result["directional_regime"] = (
            "neutral"
        )

    if momentum >= 0.002:

        result["momentum_state"] = (
            "bullish"
        )

    elif momentum <= -0.002:

        result["momentum_state"] = (
            "bearish"
        )

    else:

        result["momentum_state"] = (
            "mixed"
        )

    if imbalance > 0.05:

        result["pressure"] = (
            "bullish"
        )

    elif imbalance < -0.05:

        result["pressure"] = (
            "bearish"
        )

    else:

        result["pressure"] = (
            "balanced"
        )

    if location >= 0.90:

        result["range_event"] = (
            "near_high"
        )

    elif location <= 0.10:

        result["range_event"] = (
            "near_low"
        )

    else:

        result["range_event"] = (
            "inside_range"
        )

    return result


# ============================================================
# TRANSFORM RECORDS
# ============================================================

def transform_records(
    records,
    quantile_model
):

    transformed = []

    for record in records:

        quantized = (
            apply_quantile_model(
                record["features"],
                quantile_model
            )
        )

        transformed_features = (
            derive_regime_features(
                record["features"],
                quantized
            )
        )

        transformed.append({

            "index":
                record["index"],

            "features":
                transformed_features,

            "outcome":
                record["outcome"]
        })

    return transformed


# ============================================================
# CANDIDATE FEATURES
# ============================================================

CANDIDATE_FEATURES = [

    "return_5",
    "return_10",
    "return_15",
    "return_20",
    "return_30",
    "return_60",

    "bullish_ratio",
    "bearish_ratio",
    "directional_imbalance",

    "volatility",
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

    "volatility_regime",
    "location_state",
    "directional_regime",
    "momentum_state",
    "pressure",
    "range_event",
]


# ============================================================
# RULE DISCOVERY
# ============================================================

def discover_rules(records):

    rules = []

    # --------------------------------------------------------
    # Single-feature rules
    # --------------------------------------------------------

    for feature in CANDIDATE_FEATURES:

        groups = defaultdict(list)

        for record in records:

            value = (
                record["features"]
                .get(feature)
            )

            if value is not None:

                groups[
                    (feature, value)
                ].append(
                    record["outcome"]
                )

        for key, outcomes in (
            groups.items()
        ):

            if (
                len(outcomes)
                < MIN_CALIBRATION_SAMPLES
            ):
                continue

            directional = [
                x
                for x in outcomes
                if x in ("BUY", "SELL")
            ]

            if not directional:
                continue

            counts = Counter(
                directional
            )

            direction, count = (
                counts.most_common(1)[0]
            )

            confidence = (
                count / len(outcomes)
            )

            if (
                confidence
                < MIN_CONFIDENCE
            ):
                continue

            directional_rate = (
                len(directional)
                / len(outcomes)
            )

            lift = (
                confidence
                * directional_rate
            )

            if lift < MIN_LIFT:
                continue

            rules.append({

                "conditions": (
                    (feature, key[1]),
                ),

                "direction":
                    direction,

                "samples":
                    len(outcomes),

                "confidence":
                    confidence,

                "lift":
                    lift,
            })

    # --------------------------------------------------------
    # Two-feature rules
    # --------------------------------------------------------

    for i in range(
        len(CANDIDATE_FEATURES)
    ):

        feature_a = (
            CANDIDATE_FEATURES[i]
        )

        for j in range(
            i + 1,
            len(CANDIDATE_FEATURES)
        ):

            feature_b = (
                CANDIDATE_FEATURES[j]
            )

            groups = defaultdict(list)

            for record in records:

                a = (
                    record["features"]
                    .get(feature_a)
                )

                b = (
                    record["features"]
                    .get(feature_b)
                )

                if (
                    a is None
                    or b is None
                ):
                    continue

                groups[

                    (
                        (feature_a, a),
                        (feature_b, b)
                    )

                ].append(
                    record["outcome"]
                )

            for key, outcomes in (
                groups.items()
            ):

                if (
                    len(outcomes)
                    < MIN_CALIBRATION_SAMPLES
                ):
                    continue

                directional = [
                    x
                    for x in outcomes
                    if x in ("BUY", "SELL")
                ]

                if not directional:
                    continue

                counts = Counter(
                    directional
                )

                direction, count = (
                    counts.most_common(1)[0]
                )

                confidence = (
                    count
                    / len(outcomes)
                )

                if (
                    confidence
                    < MIN_CONFIDENCE
                ):
                    continue

                directional_rate = (
                    len(directional)
                    / len(outcomes)
                )

                lift = (
                    confidence
                    * directional_rate
                )

                if lift < MIN_LIFT:
                    continue

                rules.append({

                    "conditions":
                        key,

                    "direction":
                        direction,

                    "samples":
                        len(outcomes),

                    "confidence":
                        confidence,

                    "lift":
                        lift,
                })

    rules.sort(

        key=lambda x: (

            x["lift"],

            x["confidence"],

            x["samples"]

        ),

        reverse=True
    )

    return rules


# ============================================================
# RULE MATCHING
# ============================================================

def rule_matches(
    rule,
    features
):

    for feature, expected in (
        rule["conditions"]
    ):

        if (
            features.get(feature)
            != expected
        ):

            return False

    return True


# ============================================================
# VALIDATE LOCKED RULES
# ============================================================

def validate_rules(
    rules,
    validation_records
):

    predictions = []

    for record in validation_records:

        matched = []

        for rule in rules:

            if rule_matches(
                rule,
                record["features"]
            ):

                matched.append(rule)

        if not matched:
            continue

        matched.sort(

            key=lambda x: (

                x["confidence"],

                x["lift"],

                x["samples"]

            ),

            reverse=True
        )

        rule = matched[0]

        predictions.append({

            "index":
                record["index"],

            "prediction":
                rule["direction"],

            "actual":
                record["outcome"],

            "rule":
                rule,
        })

    return predictions


# ============================================================
# METRICS
# ============================================================

def calculate_metrics(
    predictions,
    validation_records
):

    if not validation_records:

        return {

            "accuracy": 0.0,

            "coverage": 0.0,

            "buy_precision": 0.0,

            "sell_precision": 0.0,
        }

    total = len(
        validation_records
    )

    if not predictions:

        return {

            "accuracy": 0.0,

            "coverage": 0.0,

            "buy_precision": 0.0,

            "sell_precision": 0.0,
        }

    correct = sum(

        1

        for x in predictions

        if (
            x["prediction"]
            == x["actual"]
        )
    )

    coverage = (
        len(predictions)
        / total
    )

    accuracy = (
        correct
        / len(predictions)
    )

    buy_predictions = [

        x

        for x in predictions

        if x["prediction"] == "BUY"
    ]

    sell_predictions = [

        x

        for x in predictions

        if x["prediction"] == "SELL"
    ]

    buy_precision = (

        sum(
            x["actual"] == "BUY"
            for x in buy_predictions
        )

        / len(buy_predictions)

        if buy_predictions

        else 0.0
    )

    sell_precision = (

        sum(
            x["actual"] == "SELL"
            for x in sell_predictions
        )

        / len(sell_predictions)

        if sell_predictions

        else 0.0
    )

    return {

        "accuracy":
            accuracy,

        "coverage":
            coverage,

        "buy_precision":
            buy_precision,

        "sell_precision":
            sell_precision,
    }


def baseline_metrics(
    validation_records
):

    counts = Counter(

        x["outcome"]

        for x in validation_records
    )

    total = len(
        validation_records
    )

    if not total:

        return {

            "majority":
                "NONE",

            "accuracy":
                0.0,

            "counts":
                counts,
        }

    majority_direction, majority_count = (
        counts.most_common(1)[0]
    )

    return {

        "majority":
            majority_direction,

        "accuracy":
            majority_count
            / total,

        "counts":
            counts,
    }


# ============================================================
# RULE SIGNATURE
# ============================================================

def rule_signature(rule):

    conditions = tuple(
        sorted(
            rule["conditions"]
        )
    )

    return (

        conditions,

        rule["direction"]
    )


# ============================================================
# PURGED CALIBRATION
# ============================================================

def build_purged_calibration(
    records,
    validation_start_index,
    horizon
):

    """
    CRITICAL TEMPORAL PROTECTION.

    A calibration record at index t has a label using:

        t + horizon

    Therefore it is safe for calibration only when:

        t + horizon < validation_start_index

    This prevents calibration labels from using future
    information that belongs to the validation period.
    """

    calibration = []

    purged = []

    for record in records:

        record_index = (
            record["index"]
        )

        if (
            record_index + horizon
            < validation_start_index
        ):

            calibration.append(
                record
            )

        else:

            purged.append(
                record
            )

    return calibration, purged


# ============================================================
# MAIN EXPERIMENT
# ============================================================

all_results = {}

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

    print(
        "Historical records:",
        len(records)
    )

    if (
        len(records)
        < FOLDS
        * MIN_VALIDATION_SAMPLES
    ):

        print(
            "Not enough records "
            "for requested folds."
        )

        continue

    fold_size = (
        len(records)
        // (FOLDS + 1)
    )

    fold_results = []

    stable_registry = defaultdict(
        list
    )

    aggregated_predictions = []

    # --------------------------------------------------------
    # BASELINE
    # --------------------------------------------------------

    final_validation_start = (
        len(records)
        - fold_size
    )

    baseline_validation = records[
        final_validation_start:
    ]

    baseline = baseline_metrics(
        baseline_validation
    )

    print()
    print("-" * 70)
    print("VALIDATION BASELINE")
    print("-" * 70)

    baseline_total = len(
        baseline_validation
    )

    if baseline_total:

        print(
            f"BUY       : "
            f"{baseline['counts'].get('BUY', 0) / baseline_total:.2%}"
        )

        print(
            f"SELL      : "
            f"{baseline['counts'].get('SELL', 0) / baseline_total:.2%}"
        )

        print(
            f"NEUTRAL   : "
            f"{baseline['counts'].get('NEUTRAL', 0) / baseline_total:.2%}"
        )

        print(
            f"Majority baseline: "
            f"{baseline['majority']} "
            f"({baseline['accuracy']:.2%})"
        )

    # --------------------------------------------------------
    # PURGED WALK-FORWARD
    # --------------------------------------------------------

    for fold in range(
        FOLDS,
        0,
        -1
    ):

        validation_start = (
            len(records)
            - fold_size * fold
        )

        validation_end = (
            validation_start
            + fold_size
        )

        validation_records = records[
            validation_start:
            validation_end
        ]

        # ----------------------------------------------------
        # IMPORTANT:
        #
        # Do NOT simply use:
        #
        # records[:validation_start]
        #
        # because some of those records have outcomes extending
        # into validation.
        #
        # Purge them.
        # ----------------------------------------------------

        validation_start_record_index = (
            validation_records[0]["index"]
        )

        calibration_records, purged_records = (
            build_purged_calibration(

                records,

                validation_start_record_index,

                horizon
            )
        )

        print()
        print("-" * 70)
        print(
            f"FOLD {fold}"
        )
        print("-" * 70)

        print(
            "Validation start index:",
            validation_start_record_index
        )

        print(
            "Calibration records:",
            len(calibration_records)
        )

        print(
            "Purged records:",
            len(purged_records)
        )

        print(
            "Validation records:",
            len(validation_records)
        )

        print(
            "Quantile fitting: "
            "CALIBRATION ONLY"
        )

        print(
            "Rule discovery: "
            "CALIBRATION ONLY"
        )

        print(
            "Future-label overlap: "
            "PURGED"
        )

        # ----------------------------------------------------
        # SAFETY CHECK
        # ----------------------------------------------------

        leakage_found = False

        for record in calibration_records:

            if (
                record["index"]
                + horizon
                >= validation_start_record_index
            ):

                leakage_found = True

                print(
                    "CRITICAL ERROR: "
                    "calibration label overlaps "
                    "validation period."
                )

                break

        if leakage_found:

            raise RuntimeError(
                "PURGED VALIDATION FAILED: "
                "future-label overlap detected."
            )

        print(
            "PASS: No calibration label "
            "overlaps validation."
        )

        # ----------------------------------------------------
        # FIT QUANTILES ONLY ON PURGED CALIBRATION
        # ----------------------------------------------------

        quantile_model = (
            fit_quantile_model(
                calibration_records
            )
        )

        print(
            "Locked quantile features:",
            len(quantile_model)
        )

        # ----------------------------------------------------
        # APPLY SAME MODEL
        # ----------------------------------------------------

        calibration_transformed = (
            transform_records(

                calibration_records,

                quantile_model
            )
        )

        validation_transformed = (
            transform_records(

                validation_records,

                quantile_model
            )
        )

        # ----------------------------------------------------
        # DISCOVER RULES FROM CALIBRATION ONLY
        # ----------------------------------------------------

        rules = discover_rules(
            calibration_transformed
        )

        print()
        print(
            "Locked rules discovered:",
            len(rules)
        )

        if rules:

            print()
            print(
                "TOP CALIBRATION RULES"
            )

            for rule in rules[
                :TOP_RULES_TO_PRINT
            ]:

                condition_text = (
                    " + ".join(

                        f"{a}={b}"

                        for a, b
                        in rule["conditions"]
                    )
                )

                print(

                    f"{condition_text} -> "
                    f"{rule['direction']} | "
                    f"samples={rule['samples']} | "
                    f"confidence={rule['confidence']:.2%} | "
                    f"lift={rule['lift']:.2%}"
                )

        # ----------------------------------------------------
        # LOCKED VALIDATION
        # ----------------------------------------------------

        predictions = validate_rules(

            rules,

            validation_transformed
        )

        metrics = calculate_metrics(

            predictions,

            validation_transformed
        )

        print()
        print(
            "Validation matched records:",
            len(predictions)
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

        # ----------------------------------------------------
        # REGISTRY
        # ----------------------------------------------------

        for rule in rules:

            signature = rule_signature(
                rule
            )

            stable_registry[
                signature
            ].append({

                "fold":
                    fold,

                "rule":
                    rule
            })

        aggregated_predictions.extend(
            predictions
        )

        fold_results.append({

            "fold":
                fold,

            "calibration":
                len(calibration_records),

            "purged":
                len(purged_records),

            "validation":
                len(validation_records),

            "rules":
                rules,

            "predictions":
                predictions,

            "metrics":
                metrics,
        })

    # ========================================================
    # AGGREGATED RESULT
    # ========================================================

    print()
    print("=" * 70)
    print(
        "AGGREGATED PURGED "
        "OUT-OF-SAMPLE RESULT"
    )
    print("=" * 70)

    if aggregated_predictions:

        total_predictions = len(
            aggregated_predictions
        )

        correct = sum(

            x["prediction"]
            == x["actual"]

            for x in
            aggregated_predictions
        )

        accuracy = (
            correct
            / total_predictions
        )

        buys = [

            x

            for x in
            aggregated_predictions

            if x["prediction"] == "BUY"
        ]

        sells = [

            x

            for x in
            aggregated_predictions

            if x["prediction"] == "SELL"
        ]

        buy_precision = (

            sum(
                x["actual"] == "BUY"
                for x in buys
            )

            / len(buys)

            if buys

            else 0.0
        )

        sell_precision = (

            sum(
                x["actual"] == "SELL"
                for x in sells
            )

            / len(sells)

            if sells

            else 0.0
        )

        print(
            "Validation predictions:",
            total_predictions
        )

        print(
            f"Directional accuracy: "
            f"{accuracy:.2%}"
        )

        print(
            "BUY predictions:",
            len(buys)
        )

        print(
            "SELL predictions:",
            len(sells)
        )

        print(
            f"BUY precision: "
            f"{buy_precision:.2%}"
        )

        print(
            f"SELL precision: "
            f"{sell_precision:.2%}"
        )

    else:

        print(
            "No locked rules generated "
            "validation predictions."
        )

    # ========================================================
    # CROSS-FOLD RULE DISCOVERY STABILITY
    # ========================================================

    print()
    print("=" * 70)
    print(
        "CROSS-FOLD "
        "CALIBRATION RULE STABILITY"
    )
    print("=" * 70)

    stable_rules = []

    for signature, occurrences in (
        stable_registry.items()
    ):

        if (
            len(occurrences)
            >= STABILITY_MIN_FOLDS
        ):

            stable_rules.append(
                (
                    signature,
                    occurrences
                )
            )

    print(
        "Stable calibration rules:",
        len(stable_rules)
    )

    for signature, occurrences in sorted(

        stable_rules,

        key=lambda x:
            len(x[1]),

        reverse=True
    ):

        conditions, direction = (
            signature
        )

        condition_text = (
            " + ".join(

                f"{a}={b}"

                for a, b
                in conditions
            )
        )

        print()
        print(

            f"STABLE CALIBRATION RULE: "
            f"{condition_text} -> "
            f"{direction} | "
            f"folds={len(occurrences)}"
        )

    # ========================================================
    # CURRENT MARKET DIAGNOSTIC
    # ========================================================

    print()
    print("-" * 70)
    print(
        "CURRENT 60-CANDLE "
        "MARKET STRUCTURE"
    )
    print("-" * 70)

    latest_index = (
        len(closes) - 1
    )

    latest_raw = raw_features(
        latest_index
    )

    # Diagnostic only.
    #
    # This model does NOT participate in validation.
    #
    # It is intentionally fitted using historical records
    # only for current-market description.

    diagnostic_model = (
        fit_quantile_model(
            records
        )
    )

    latest_quantized = (
        apply_quantile_model(

            latest_raw,

            diagnostic_model
        )
    )

    latest_structure = (
        derive_regime_features(

            latest_raw,

            latest_quantized
        )
    )

    print(
        "Latest index:",
        latest_index
    )

    print(
        "Latest price:",
        closes[-1]
    )

    print()

    print(
        "Directional regime:",
        latest_structure.get(
            "directional_regime"
        )
    )

    print(
        "Volatility regime:",
        latest_structure.get(
            "volatility_regime"
        )
    )

    print(
        "Location state:",
        latest_structure.get(
            "location_state"
        )
    )

    print(
        "Momentum state:",
        latest_structure.get(
            "momentum_state"
        )
    )

    print(
        "Candle pressure:",
        latest_structure.get(
            "pressure"
        )
    )

    print(
        "Range event:",
        latest_structure.get(
            "range_event"
        )
    )

    print()
    print(
        "NUMERIC STRUCTURE FEATURES"
    )

    for key, value in (
        latest_raw.items()
    ):

        print(

            f"{key:24s}: "
            f"{value:.6f}"
        )

    all_results[horizon] = {

        "fold_results":
            fold_results,

        "stable_rules":
            stable_rules,
    }


# ============================================================
# FINAL VERDICT
# ============================================================

print()
print("=" * 70)
print(
    "MLAI v3.3.9 FINAL VERDICT"
)
print("=" * 70)

print("""
This experiment is diagnostic only.

No production model was changed.
No learning memory was changed.
market_data.bin was READ ONLY.
mlai_v31.py was NOT modified.

METHODOLOGY PROTECTIONS:

1. Quantile boundaries are fitted ONLY on calibration data.

2. The calibration quantile boundaries are LOCKED.

3. The exact same boundaries are applied to validation.

4. Validation data NEVER participates in quantile fitting.

5. Rules are discovered ONLY from calibration.

6. Rules are LOCKED before validation.

7. Validation cannot modify rules.

8. Calibration records whose future outcome window reaches
   into the validation period are PURGED.

9. Every fold performs chronological walk-forward validation.

10. Validation performance is measured only after the model
    and rules are locked.

IMPORTANT:

A calibration edge is NOT enough.

A stable calibration rule is NOT enough.

A historical similarity result is NOT enough.

A rule must generate meaningful predictions on unseen,
chronological, PURGED validation data.

No rule from this experiment is promoted to production.
""")

print()
print(
    "MLAI v3.3.9 COMPLETE"
)
