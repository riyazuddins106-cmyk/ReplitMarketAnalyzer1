
import os
import pickle
import math
from collections import Counter, defaultdict

# ============================================================
# MLAI v3.4.0
# VALIDATION INVESTIGATION + RULE QUALITY AUDIT
#
# PURPOSE
# ------------------------------------------------------------
# v3.3.9 correctly introduced:
#   - calibration-only quantile fitting
#   - locked quantile boundaries
#   - purged calibration
#   - chronological validation
#
# v3.4.0 investigates the next problem:
#
#   "STABLE CALIBRATION RULE"
#   does NOT mean
#   "VALIDATED PREDICTIVE RULE".
#
# This version therefore:
#
#   1. Keeps market_data.bin READ ONLY.
#   2. Does not modify mlai_v31.py.
#   3. Fits quantiles only on calibration.
#   4. Purges future-label overlap.
#   5. Discovers rules only from calibration.
#   6. Locks rules before validation.
#   7. Ensures ONE prediction per validation record.
#   8. Separates calibration stability from validation success.
#   9. Measures validation performance against baseline.
#  10. Audits rule redundancy.
#  11. Reports validation rule performance.
#  12. Does NOT promote anything to production.
#
# IMPORTANT:
# This is a diagnostic experiment only.
# ============================================================


MARKET_FILE = "market_data.bin"

WINDOW = 60

HORIZONS = [4, 8, 16]

FOLDS = 4

MIN_CALIBRATION_SAMPLES = 20

MIN_VALIDATION_MATCHES = 5

MIN_CONFIDENCE = 0.45

MIN_DIRECTIONAL_RATE = 0.20

STABILITY_MIN_FOLDS = 2

TOP_RULES_TO_PRINT = 20

TOP_VALIDATED_RULES_TO_PRINT = 20

# Maximum number of rules considered during validation.
# This prevents an enormous calibration rule set from
# creating an uncontrolled validation search.
MAX_RULES_FOR_VALIDATION = 500


# ============================================================
# HEADER
# ============================================================

print("=" * 78)
print("MLAI v3.4.0 VALIDATION INVESTIGATION + RULE QUALITY AUDIT")
print("=" * 78)

print("""
This version investigates rule quality.

IMPORTANT DISTINCTION:

STABLE CALIBRATION RULE
    =
Rule discovered repeatedly during calibration.

VALIDATED RULE
    =
Rule actually matched unseen validation data and
demonstrated measurable out-of-sample performance.

These are NOT the same thing.

No production model will be modified.
No learning memory will be modified.
market_data.bin will be READ ONLY.
mlai_v31.py will NOT be modified.
""")

print("=" * 78)
print("PROTECTION CHECK")
print("=" * 78)

print("market_data.bin : READ ONLY")
print("mlai_v31.py     : NOT MODIFIED")
print("learning memory  : NOT MODIFIED")
print("production model : NOT MODIFIED")


# ============================================================
# LOAD MARKET DATA
# ============================================================

if not os.path.exists(MARKET_FILE):
    raise FileNotFoundError(
        f"Required file not found: {MARKET_FILE}"
    )

with open(MARKET_FILE, "rb") as f:
    market_data = pickle.load(f)

print()
print("Data type:", type(market_data).__name__)

if not isinstance(market_data, dict):
    raise ValueError(
        "Unexpected market_data.bin structure."
    )

candles = market_data.get("candles", [])

print("Total candles:", len(candles))

if len(candles) < WINDOW + max(HORIZONS) + 100:
    raise ValueError(
        "Not enough candles for requested experiment."
    )


# ============================================================
# EXTRACT CLOSES
# ============================================================

closes = []

for candle in candles:

    if isinstance(candle, dict):

        close = candle.get("close")

        if close is None:
            close = candle.get("c")

        if close is not None:
            closes.append(float(close))

    elif isinstance(candle, (list, tuple)):

        # Expected:
        # timestamp, open, high, low, close

        if len(candle) >= 5:
            closes.append(float(candle[4]))


if len(closes) < WINDOW + max(HORIZONS) + 100:
    raise ValueError(
        "Not enough valid close prices."
    )

print("Valid close prices:", len(closes))

print("PASS: market_data.bin loaded.")
print("PASS: Close prices extracted.")
print("PASS: market_data.bin remains READ ONLY.")
print("PASS: Production MLAI remains untouched.")


# ============================================================
# NUMERIC HELPERS
# ============================================================

def safe_return(values, n):

    if len(values) <= n:
        return 0.0

    base = values[-n - 1]

    if base == 0:
        return 0.0

    return (
        values[-1] / base
    ) - 1.0


def mean(values):

    if not values:
        return 0.0

    return sum(values) / len(values)


def stdev(values):

    if len(values) < 2:
        return 0.0

    m = mean(values)

    return math.sqrt(
        sum(
            (x - m) ** 2
            for x in values
        )
        / (len(values) - 1)
    )


def percentile(sorted_values, p):

    if not sorted_values:
        return 0.0

    if len(sorted_values) == 1:
        return sorted_values[0]

    position = (
        len(sorted_values) - 1
    ) * p

    lower = int(
        math.floor(position)
    )

    upper = int(
        math.ceil(position)
    )

    if lower == upper:
        return sorted_values[lower]

    weight = position - lower

    return (
        sorted_values[lower]
        * (1.0 - weight)
        +
        sorted_values[upper]
        * weight
    )


# ============================================================
# RAW FEATURES
# ============================================================

def raw_features(index):

    if index < WINDOW:
        return None

    segment = closes[
        index - WINDOW + 1:
        index + 1
    ]

    if len(segment) < WINDOW:
        return None

    current = segment[-1]

    r5 = safe_return(segment, 5)
    r10 = safe_return(segment, 10)
    r15 = safe_return(segment, 15)
    r20 = safe_return(segment, 20)
    r30 = safe_return(segment, 30)
    r60 = safe_return(segment, 59)

    returns = []

    for i in range(1, len(segment)):

        previous = segment[i - 1]

        if previous != 0:

            returns.append(
                (segment[i] / previous)
                - 1.0
            )

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

    lo = min(segment)
    hi = max(segment)

    if hi > lo:

        location_in_range = (
            current - lo
        ) / (hi - lo)

    else:

        location_in_range = 0.5

    if segment[0] != 0:

        normalized_slope = (
            segment[-1]
            / segment[0]
        ) - 1.0

    else:

        normalized_slope = 0.0

    momentum_5 = r5
    momentum_10 = r10
    momentum_20 = r20

    momentum_acceleration = (
        momentum_5
        - momentum_10
    )

    recent_window = segment[-10:]

    recent_changes = []

    for i in range(
        1,
        len(recent_window)
    ):

        previous = recent_window[i - 1]

        current_value = (
            recent_window[i]
        )

        if previous != 0:

            recent_changes.append(
                abs(
                    current_value
                    - previous
                )
                / previous
            )

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
# BUILD RECORDS
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

        features = raw_features(
            index
        )

        if features is None:
            continue

        outcome = classify_outcome(
            index,
            horizon
        )

        if outcome is None:
            continue

        records.append({

            "index":
                index,

            "features":
                features,

            "outcome":
                outcome,
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
# QUANTILE MODEL
# ============================================================

def fit_quantile_model(
    calibration_records
):

    model = {}

    for feature in QUANTILE_FEATURES:

        values = []

        for record in calibration_records:

            value = record[
                "features"
            ].get(feature)

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

            "min":
                values[0],

            "max":
                values[-1],
        }

    return model


# ============================================================
# APPLY QUANTILE MODEL
# ============================================================

def apply_quantile_model(
    features,
    model
):

    result = {}

    for feature, boundaries in (
        model.items()
    ):

        value = features.get(
            feature
        )

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
# REGIME FEATURES
# ============================================================

def derive_regime_features(
    features,
    quantized
):

    result = dict(
        quantized
    )

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

        result[
            "volatility_regime"
        ] = "expanding"

    elif volatility_ratio < 0.90:

        result[
            "volatility_regime"
        ] = "contracting"

    else:

        result[
            "volatility_regime"
        ] = "stable"

    if location >= 0.80:

        result[
            "location_state"
        ] = "upper_range"

    elif location <= 0.20:

        result[
            "location_state"
        ] = "lower_range"

    else:

        result[
            "location_state"
        ] = "middle_range"

    if imbalance >= 0.10:

        result[
            "directional_regime"
        ] = "bullish"

    elif imbalance <= -0.10:

        result[
            "directional_regime"
        ] = "bearish"

    else:

        result[
            "directional_regime"
        ] = "neutral"

    if momentum >= 0.002:

        result[
            "momentum_state"
        ] = "bullish"

    elif momentum <= -0.002:

        result[
            "momentum_state"
        ] = "bearish"

    else:

        result[
            "momentum_state"
        ] = "mixed"

    if imbalance > 0.05:

        result[
            "pressure"
        ] = "bullish"

    elif imbalance < -0.05:

        result[
            "pressure"
        ] = "bearish"

    else:

        result[
            "pressure"
        ] = "balanced"

    if location >= 0.90:

        result[
            "range_event"
        ] = "near_high"

    elif location <= 0.10:

        result[
            "range_event"
        ] = "near_low"

    else:

        result[
            "range_event"
        ] = "inside_range"

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
                record["outcome"],
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
# RULE SCORE
# ============================================================

def rule_score(
    confidence,
    directional_rate
):

    # This is deliberately called SCORE,
    # not "lift".
    #
    # It is:
    #
    # confidence * directional_rate
    #
    # This is the scoring formula used by v3.3.9,
    # but it is NOT conventional statistical lift.

    return (
        confidence
        * directional_rate
    )


# ============================================================
# RULE DISCOVERY
# ============================================================

def discover_rules(
    records
):

    rules = []

    # --------------------------------------------------------
    # SINGLE FEATURE
    # --------------------------------------------------------

    for feature in (
        CANDIDATE_FEATURES
    ):

        groups = defaultdict(list)

        for record in records:

            value = record[
                "features"
            ].get(feature)

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
                if x in (
                    "BUY",
                    "SELL"
                )
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

            directional_rate = (
                len(directional)
                / len(outcomes)
            )

            if confidence < MIN_CONFIDENCE:
                continue

            if (
                directional_rate
                < MIN_DIRECTIONAL_RATE
            ):
                continue

            score = rule_score(
                confidence,
                directional_rate
            )

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

                "directional_rate":
                    directional_rate,

                "score":
                    score,

                "rule_length":
                    1,
            })

    # --------------------------------------------------------
    # TWO FEATURE
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

                a = record[
                    "features"
                ].get(feature_a)

                b = record[
                    "features"
                ].get(feature_b)

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
                    if x in (
                        "BUY",
                        "SELL"
                    )
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

                directional_rate = (
                    len(directional)
                    / len(outcomes)
                )

                if confidence < MIN_CONFIDENCE:
                    continue

                if (
                    directional_rate
                    < MIN_DIRECTIONAL_RATE
                ):
                    continue

                score = rule_score(
                    confidence,
                    directional_rate
                )

                rules.append({

                    "conditions":
                        key,

                    "direction":
                        direction,

                    "samples":
                        len(outcomes),

                    "confidence":
                        confidence,

                    "directional_rate":
                        directional_rate,

                    "score":
                        score,

                    "rule_length":
                        2,
                })

    # --------------------------------------------------------
    # SORT
    # --------------------------------------------------------

    rules.sort(

        key=lambda x: (

            x["score"],

            x["confidence"],

            x["samples"],

            -x["rule_length"],
        ),

        reverse=True
    )

    return rules


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
# RULE MATCH
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
# PURGED CALIBRATION
# ============================================================

def build_purged_calibration(
    records,
    validation_start_index,
    horizon
):

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

    return (
        calibration,
        purged
    )


# ============================================================
# VALIDATION
# ============================================================

def validate_rules(
    rules,
    validation_records
):

    predictions = []

    # --------------------------------------------------------
    # IMPORTANT:
    #
    # ONE validation record gets at most ONE prediction.
    #
    # Multiple matching rules are not counted as multiple
    # predictions.
    #
    # The strongest LOCKED calibration rule wins.
    # --------------------------------------------------------

    for record in validation_records:

        matched = []

        for rule in rules:

            if rule_matches(
                rule,
                record["features"]
            ):

                matched.append(
                    rule
                )

        if not matched:
            continue

        matched.sort(

            key=lambda x: (

                x["confidence"],

                x["score"],

                x["samples"],

                -x["rule_length"],
            ),

            reverse=True
        )

        selected_rule = matched[0]

        predictions.append({

            "index":
                record["index"],

            "prediction":
                selected_rule[
                    "direction"
                ],

            "actual":
                record["outcome"],

            "rule":
                selected_rule,

            "matching_rule_count":
                len(matched),
        })

    return predictions


# ============================================================
# METRICS
# ============================================================

def calculate_metrics(
    predictions,
    validation_records
):

    total = len(
        validation_records
    )

    if total == 0:

        return {

            "accuracy": 0.0,
            "coverage": 0.0,
            "buy_precision": 0.0,
            "sell_precision": 0.0,

            "predictions": 0,

            "correct": 0,
        }

    if not predictions:

        return {

            "accuracy": 0.0,
            "coverage": 0.0,
            "buy_precision": 0.0,
            "sell_precision": 0.0,

            "predictions": 0,

            "correct": 0,
        }

    correct = sum(

        1

        for x in predictions

        if (
            x["prediction"]
            == x["actual"]
        )
    )

    prediction_count = len(
        predictions
    )

    coverage = (
        prediction_count
        / total
    )

    accuracy = (
        correct
        / prediction_count
    )

    buys = [

        x

        for x in predictions

        if x["prediction"]
        == "BUY"
    ]

    sells = [

        x

        for x in predictions

        if x["prediction"]
        == "SELL"
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

    return {

        "accuracy":
            accuracy,

        "coverage":
            coverage,

        "buy_precision":
            buy_precision,

        "sell_precision":
            sell_precision,

        "predictions":
            prediction_count,

        "correct":
            correct,
    }


# ============================================================
# BASELINE
# ============================================================

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
# RULE VALIDATION AUDIT
# ============================================================

def audit_rule_validation(
    rules,
    validation_records
):

    results = []

    for rule in rules:

        matches = []

        for record in validation_records:

            if rule_matches(
                rule,
                record["features"]
            ):

                matches.append(
                    record
                )

        if (
            len(matches)
            < MIN_VALIDATION_MATCHES
        ):

            continue

        correct = sum(

            record["outcome"]
            == rule["direction"]

            for record in matches
        )

        validation_accuracy = (
            correct
            / len(matches)
        )

        directional_matches = [

            record

            for record in matches

            if record["outcome"]
            in ("BUY", "SELL")
        ]

        directional_rate = (

            len(directional_matches)
            / len(matches)
        )

        results.append({

            "rule":
                rule,

            "validation_matches":
                len(matches),

            "validation_correct":
                correct,

            "validation_accuracy":
                validation_accuracy,

            "validation_directional_rate":
                directional_rate,
        })

    results.sort(

        key=lambda x: (

            x[
                "validation_accuracy"
            ],

            x[
                "validation_matches"
            ],

            x[
                "rule"
            ]["confidence"],
        ),

        reverse=True
    )

    return results


# ============================================================
# RULE REDUNDANCY AUDIT
# ============================================================

def condition_feature_set(
    rule
):

    return frozenset(

        feature

        for feature, value
        in rule["conditions"]
    )


def audit_rule_redundancy(
    rules
):

    feature_counts = Counter()

    exact_signatures = Counter()

    for rule in rules:

        signature = (
            rule_signature(rule)
        )

        exact_signatures[
            signature
        ] += 1

        for feature, value in (
            rule["conditions"]
        ):

            feature_counts[
                feature
            ] += 1

    return (
        feature_counts,
        exact_signatures
    )


# ============================================================
# MAIN EXPERIMENT
# ============================================================

all_results = {}

for horizon in HORIZONS:

    print()
    print("=" * 78)
    print(
        f"HORIZON: {horizon} CANDLES"
    )
    print("=" * 78)

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
        * MIN_VALIDATION_MATCHES
    ):

        print(
            "Not enough records."
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
    # FINAL FOLD BASELINE
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
    print("-" * 78)
    print("VALIDATION BASELINE")
    print("-" * 78)

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
    # WALK FORWARD
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

        if not validation_records:
            continue

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
        print("-" * 78)
        print(
            f"FOLD {fold}"
        )
        print("-" * 78)

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

        # ----------------------------------------------------
        # LEAKAGE CHECK
        # ----------------------------------------------------

        leakage_found = False

        for record in calibration_records:

            if (
                record["index"]
                + horizon
                >= validation_start_record_index
            ):

                leakage_found = True
                break

        if leakage_found:

            raise RuntimeError(
                "CRITICAL: Purged calibration "
                "contains future-label overlap."
            )

        print(
            "PASS: Calibration future-label overlap = NONE"
        )

        # ----------------------------------------------------
        # FIT QUANTILES
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
        # TRANSFORM
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
        # DISCOVER
        # ----------------------------------------------------

        rules = discover_rules(
            calibration_transformed
        )

        print()
        print(
            "Calibration rules discovered:",
            len(rules)
        )

        # ----------------------------------------------------
        # RULE REDUNDANCY
        # ----------------------------------------------------

        feature_counts, exact_signatures = (
            audit_rule_redundancy(
                rules
            )
        )

        print(
            "Unique rule signatures:",
            len(exact_signatures)
        )

        print(
            "Distinct candidate features used:",
            len(feature_counts)
        )

        # ----------------------------------------------------
        # TOP CALIBRATION RULES
        # ----------------------------------------------------

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
                    f"directional={rule['directional_rate']:.2%} | "
                    f"score={rule['score']:.2%}"
                )

        # ----------------------------------------------------
        # CROSS-FOLD CALIBRATION REGISTRY
        # ----------------------------------------------------

        for rule in rules:

            signature = (
                rule_signature(rule)
            )

            stable_registry[
                signature
            ].append({

                "fold":
                    fold,

                "rule":
                    rule,
            })

        # ----------------------------------------------------
        # LIMIT VALIDATION RULE SET
        #
        # We do NOT use every rule when investigating
        # validation. This lets us determine whether the
        # strongest calibration rules actually generalize.
        # ----------------------------------------------------

        validation_rules = rules[
            :MAX_RULES_FOR_VALIDATION
        ]

        print()
        print(
            "Rules used for locked validation:",
            len(validation_rules)
        )

        # ----------------------------------------------------
        # ONE PREDICTION PER VALIDATION RECORD
        # ----------------------------------------------------

        predictions = validate_rules(

            validation_rules,

            validation_transformed
        )

        metrics = calculate_metrics(

            predictions,

            validation_transformed
        )

        validation_baseline = (
            baseline_metrics(
                validation_records
            )
        )

        baseline_accuracy = (
            validation_baseline[
                "accuracy"
            ]
        )

        accuracy_difference = (
            metrics["accuracy"]
            - baseline_accuracy
        )

        print()
        print(
            "LOCKED VALIDATION RESULT"
        )

        print(
            "Validation records:",
            len(validation_records)
        )

        print(
            "Validation predictions:",
            metrics["predictions"]
        )

        print(
            f"Directional accuracy: "
            f"{metrics['accuracy']:.2%}"
        )

        print(
            f"Majority baseline: "
            f"{baseline_accuracy:.2%}"
        )

        print(
            f"Accuracy vs baseline: "
            f"{accuracy_difference:+.2%}"
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
        # INDIVIDUAL RULE VALIDATION AUDIT
        # ----------------------------------------------------

        individual_validation = (
            audit_rule_validation(

                validation_rules,

                validation_transformed
            )
        )

        validated_candidates = []

        for item in individual_validation:

            if (
                item[
                    "validation_accuracy"
                ]
                >
                baseline_accuracy
            ):

                validated_candidates.append(
                    item
                )

        print()
        print(
            "Individual rules with "
            "validation matches >= "
            f"{MIN_VALIDATION_MATCHES}:",
            len(individual_validation)
        )

        print(
            "Rules beating local majority baseline:",
            len(validated_candidates)
        )

        if validated_candidates:

            print()
            print(
                "TOP OUT-OF-SAMPLE RULE CANDIDATES"
            )

            for item in (
                validated_candidates[
                    :TOP_VALIDATED_RULES_TO_PRINT
                ]
            ):

                rule = item["rule"]

                condition_text = (
                    " + ".join(

                        f"{a}={b}"

                        for a, b
                        in rule["conditions"]
                    )
                )

                print(

                    f"VALIDATION CANDIDATE: "
                    f"{condition_text} -> "
                    f"{rule['direction']} | "
                    f"calib_conf={rule['confidence']:.2%} | "
                    f"val_matches={item['validation_matches']} | "
                    f"val_accuracy={item['validation_accuracy']:.2%} | "
                    f"baseline={baseline_accuracy:.2%}"
                )

        # ----------------------------------------------------
        # FOLD RESULT
        # ----------------------------------------------------

        fold_results.append({

            "fold":
                fold,

            "calibration":
                len(calibration_records),

            "purged":
                len(purged_records),

            "validation":
                len(validation_records),

            "rules_discovered":
                len(rules),

            "rules_used_for_validation":
                len(validation_rules),

            "predictions":
                predictions,

            "metrics":
                metrics,

            "individual_validation":
                individual_validation,
        })

        aggregated_predictions.extend(
            predictions
        )

    # ========================================================
    # AGGREGATED RESULT
    # ========================================================

    print()
    print("=" * 78)
    print(
        "AGGREGATED LOCKED "
        "OUT-OF-SAMPLE RESULT"
    )
    print("=" * 78)

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

            if x["prediction"]
            == "BUY"
        ]

        sells = [

            x

            for x in
            aggregated_predictions

            if x["prediction"]
            == "SELL"
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
            "Correct predictions:",
            correct
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
            "No locked validation predictions."
        )

    # ========================================================
    # CROSS-FOLD CALIBRATION STABILITY
    # ========================================================

    print()
    print("=" * 78)
    print(
        "CALIBRATION STABILITY "
        "AUDIT"
    )
    print("=" * 78)

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

    print()
    print(
        "IMPORTANT:"
    )

    print(
        "Stable calibration rules are NOT "
        "automatically validated rules."
    )

    for signature, occurrences in sorted(

        stable_rules,

        key=lambda x:
            len(x[1]),

        reverse=True
    )[

        :TOP_RULES_TO_PRINT
    ]:

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

        print(

            f"STABLE CALIBRATION: "
            f"{condition_text} -> "
            f"{direction} | "
            f"folds={len(occurrences)}"
        )

    # ========================================================
    # CURRENT MARKET DIAGNOSTIC
    # ========================================================

    print()
    print("=" * 78)
    print(
        "CURRENT 60-CANDLE "
        "MARKET STRUCTURE"
    )
    print("=" * 78)

    latest_index = (
        len(closes) - 1
    )

    latest_raw = raw_features(
        latest_index
    )

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
print("=" * 78)
print(
    "MLAI v3.4.0 FINAL VERDICT"
)
print("=" * 78)

print("""
This experiment is diagnostic only.

No production model was changed.
No learning memory was changed.
market_data.bin was READ ONLY.
mlai_v31.py was NOT modified.

v3.4.0 specifically investigates the distinction between:

    CALIBRATION STABILITY

and:

    OUT-OF-SAMPLE VALIDATION PERFORMANCE.

IMPORTANT METHODOLOGY:

1. Quantile boundaries are fitted ONLY on calibration.

2. Quantile boundaries are locked.

3. The same boundaries are applied to validation.

4. Calibration labels overlapping validation are purged.

5. Rules are discovered ONLY from calibration.

6. Rules are locked before validation.

7. Each validation record receives at most ONE prediction.

8. Validation results are compared with the local
   chronological majority baseline.

9. Individual rules are separately audited against
   unseen validation data.

10. Calibration "score" is NOT called statistical lift.

11. Stable calibration rules are NOT automatically
    considered validated rules.

12. No rule is promoted to production.

A rule should only be considered a serious candidate when
it demonstrates meaningful out-of-sample validation evidence.

The next decision must be based on the actual v3.4.0 output,
not assumptions.
""")

print()
print(
    "MLAI v3.4.0 COMPLETE"
)
