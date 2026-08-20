import os
import random
import pickle
import math
from collections import Counter, defaultdict


# ============================================================
# MLAI v3.4.2
# VALIDATION INVESTIGATION + RULE QUALITY AUDIT
#
# PURPOSE
# ------------------------------------------------------------
# Diagnostic experiment only.
#
# This version:
#
#   1. Keeps market_data.bin READ ONLY.
#   2. Does not modify mlai_v31.py.
#   3. Fits quantiles only on calibration data.
#   4. Purges future-label overlap.
#   5. Discovers rules only from calibration.
#   6. Performs inner chronological rule selection.
#   7. Locks rules before outer validation.
#   8. Ensures ONE prediction per validation record.
#   9. Separates calibration stability from validation success.
#  10. Measures validation performance against baseline.
#  11. Audits rule redundancy.
#  12. Performs permutation/null testing.
#  13. Does NOT promote anything to production.
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

MAX_RULES_FOR_VALIDATION = 500


# ============================================================
# HEADER
# ============================================================

print("=" * 78)
print("MLAI v3.4.2 VALIDATION INVESTIGATION + RULE QUALITY AUDIT")
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

    # Use 59 because the window contains 60 prices.
    r60 = safe_return(segment, 59)

    returns = []

    for i in range(1, len(segment)):

        previous = segment[i - 1]

        if previous != 0:

            returns.append(
                (segment[i] / previous) - 1.0
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
            recent_volatility / volatility
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
            bullish / total_directional
        )

        bearish_ratio = (
            bearish / total_directional
        )

        directional_imbalance = (
            bullish_ratio - bearish_ratio
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
            segment[-1] / segment[0]
        ) - 1.0

    else:

        normalized_slope = 0.0

    momentum_5 = r5
    momentum_10 = r10
    momentum_20 = r20

    momentum_acceleration = (
        momentum_5 - momentum_10
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
                    current_value - previous
                ) / previous
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

    return (
        confidence
        * directional_rate
    )


# ============================================================
# OUTCOME DISTRIBUTION
# ============================================================

def outcome_distribution(records):

    counts = Counter(
        record["outcome"]
        for record in records
    )

    total = len(records)

    return {
        "BUY": counts.get("BUY", 0),
        "SELL": counts.get("SELL", 0),
        "NEUTRAL": counts.get("NEUTRAL", 0),
        "total": total,
    }


def print_outcome_distribution(
    title,
    records
):

    distribution = outcome_distribution(
        records
    )

    total = distribution["total"]

    print()
    print("-" * 78)
    print(title)
    print("-" * 78)

    print(
        "Total:",
        total
    )

    if total == 0:

        print("BUY     : 0")
        print("SELL    : 0")
        print("NEUTRAL : 0")

        return distribution

    print(
        f"BUY     : "
        f"{distribution['BUY']} "
        f"({distribution['BUY'] / total:.2%})"
    )

    print(
        f"SELL    : "
        f"{distribution['SELL']} "
        f"({distribution['SELL'] / total:.2%})"
    )

    print(
        f"NEUTRAL : "
        f"{distribution['NEUTRAL']} "
        f"({distribution['NEUTRAL'] / total:.2%})"
    )

    return distribution


# ============================================================
# RULE SEARCH DIAGNOSTICS
# ============================================================

def rule_length_distribution(
    rules
):

    counts = Counter(
        rule.get(
            "rule_length",
            0
        )
        for rule in rules
    )

    return counts


def print_rule_search_diagnostics(
    title,
    discovered_rules,
    selected_candidates,
    locked_rules
):

    discovered_lengths = (
        rule_length_distribution(
            discovered_rules
        )
    )

    selected_lengths = (
        rule_length_distribution(
            selected_candidates
        )
    )

    locked_lengths = (
        rule_length_distribution(
            locked_rules
        )
    )

    print()
    print("-" * 78)
    print(title)
    print("-" * 78)

    print(
        "Rules discovered:",
        len(discovered_rules)
    )

    print(
        "Rules passing inner validation:",
        len(selected_candidates)
    )

    print(
        "Rules locked for outer validation:",
        len(locked_rules)
    )

    print(
        "Discovered 1-feature rules:",
        discovered_lengths.get(1, 0)
    )

    print(
        "Discovered 2-feature rules:",
        discovered_lengths.get(2, 0)
    )

    print(
        "Selected 1-feature rules:",
        selected_lengths.get(1, 0)
    )

    print(
        "Selected 2-feature rules:",
        selected_lengths.get(2, 0)
    )

    print(
        "Locked 1-feature rules:",
        locked_lengths.get(1, 0)
    )

    print(
        "Locked 2-feature rules:",
        locked_lengths.get(2, 0)
    )


# ============================================================
# VALIDATION SUMMARY
# ============================================================

def calculate_rule_validation_summary(
    validation_results
):

    if not validation_results:

        return {
            "rules": 0,
            "average_accuracy": 0.0,
            "best_accuracy": 0.0,
            "average_matches": 0.0,
        }

    accuracies = [
        item["validation_accuracy"]
        for item in validation_results
    ]

    matches = [
        item["validation_matches"]
        for item in validation_results
    ]

    return {

        "rules":
            len(validation_results),

        "average_accuracy":
            sum(accuracies)
            / len(accuracies),

        "best_accuracy":
            max(accuracies),

        "average_matches":
            sum(matches)
            / len(matches),
    }


def print_validation_selection_diagnostics(
    title,
    validation_results,
    baseline_accuracy
):

    summary = (
        calculate_rule_validation_summary(
            validation_results
        )
    )

    print()
    print("-" * 78)
    print(title)
    print("-" * 78)

    print(
        "Rules individually validated:",
        summary["rules"]
    )

    print(
        f"Average rule validation accuracy: "
        f"{summary['average_accuracy']:.2%}"
    )

    print(
        f"Best rule validation accuracy: "
        f"{summary['best_accuracy']:.2%}"
    )

    print(
        f"Average validation matches: "
        f"{summary['average_matches']:.2f}"
    )

    print(
        f"Validation baseline: "
        f"{baseline_accuracy:.2%}"
    )

    above_baseline = sum(
        item["validation_accuracy"]
        > baseline_accuracy
        for item in validation_results
    )

    print(
        "Rules above validation baseline:",
        above_baseline
    )

    if validation_results:

        print(
            f"Selection rate above baseline: "
            f"{above_baseline / len(validation_results):.2%}"
        )


# ============================================================
# SHUFFLED CALIBRATION RECORDS
# ============================================================

def shuffled_calibration_records(
    records,
    rng
):

    shuffled = [
        dict(record)
        for record in records
    ]

    outcomes = [
        record["outcome"]
        for record in shuffled
    ]

    rng.shuffle(
        outcomes
    )

    for record, outcome in zip(
        shuffled,
        outcomes
    ):

        record["outcome"] = outcome

    return shuffled


# ============================================================
# PERMUTATION / NULL TEST
# ============================================================

def run_permutation_null_test(
    calibration_records,
    validation_records,
    quantile_model,
    permutations=25,
    seed=341
):

    """
    Diagnostic null test.

    Calibration labels are randomly shuffled while feature
    values remain unchanged.

    Validation labels remain untouched.

    The purpose is to determine whether the rule-search
    process can create apparently strong validation results
    even when the calibration feature/outcome relationship
    has been destroyed.

    This is NOT a production model test.
    """

    rng = random.Random(
        seed
    )

    validation_transformed = (
        transform_records(
            validation_records,
            quantile_model
        )
    )

    baseline = baseline_metrics(
        validation_records
    )

    baseline_accuracy = (
        baseline["accuracy"]
    )

    best_accuracies = []

    candidate_counts = []

    above_baseline_counts = []

    for iteration in range(
        permutations
    ):

        shuffled = (
            shuffled_calibration_records(
                calibration_records,
                rng
            )
        )

        # IMPORTANT:
        # The null test uses the SAME quantile model
        # that was fitted before label shuffling.
        #
        # This keeps the null test focused on destroying
        # the feature/outcome relationship rather than
        # changing the feature transformation itself.

        shuffled_transformed = (
            transform_records(
                shuffled,
                quantile_model
            )
        )

        rules = discover_rules(
            shuffled_transformed
        )

        validation_results = (
            audit_rule_validation(
                rules[
                    :MAX_RULES_FOR_VALIDATION
                ],
                validation_transformed
            )
        )

        if validation_results:

            best_accuracy = max(
                item["validation_accuracy"]
                for item in validation_results
            )

            above_baseline = sum(
                item["validation_accuracy"]
                > baseline_accuracy
                for item in validation_results
            )

        else:

            best_accuracy = 0.0

            above_baseline = 0

        best_accuracies.append(
            best_accuracy
        )

        candidate_counts.append(
            len(rules)
        )

        above_baseline_counts.append(
            above_baseline
        )

    if not best_accuracies:

        return {

            "permutations":
                0,

            "baseline_accuracy":
                baseline_accuracy,

            "mean_best_accuracy":
                0.0,

            "max_best_accuracy":
                0.0,

            "mean_rule_count":
                0.0,

            "mean_above_baseline":
                0.0,
        }

    return {

        "permutations":
            permutations,

        "baseline_accuracy":
            baseline_accuracy,

        "mean_best_accuracy":
            sum(best_accuracies)
            / len(best_accuracies),

        "max_best_accuracy":
            max(best_accuracies),

        "mean_rule_count":
            sum(candidate_counts)
            / len(candidate_counts),

        "mean_above_baseline":
            sum(above_baseline_counts)
            / len(above_baseline_counts),
    }


def print_permutation_null_result(
    result
):

    print()
    print("=" * 78)
    print(
        "PERMUTATION / NULL TEST"
    )
    print("=" * 78)

    print(
        "Permutations:",
        result["permutations"]
    )

    print(
        f"Real validation baseline: "
        f"{result['baseline_accuracy']:.2%}"
    )

    print(
        f"Mean best null-rule accuracy: "
        f"{result['mean_best_accuracy']:.2%}"
    )

    print(
        f"Maximum best null-rule accuracy: "
        f"{result['max_best_accuracy']:.2%}"
    )

    print(
        f"Mean rules discovered under null: "
        f"{result['mean_rule_count']:.2f}"
    )

    print(
        f"Mean null rules above baseline: "
        f"{result['mean_above_baseline']:.2f}"
    )

    print()
    print(
        "INTERPRETATION:"
    )

    print(
        "If randomized labels regularly produce "
        "apparently strong validation rules, the "
        "rule-search process has substantial "
        "selection-overfitting risk."
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
                count / len(outcomes)
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
                    count / len(outcomes)
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
    # ONE validation record gets at most ONE prediction.
    #
    # Multiple matching rules are not counted as multiple
    # predictions.
    #
    # The strongest locked calibration rule wins.
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
            majority_count / total,

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
            correct / len(matches)
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
# PRINT TOP RULES
# ============================================================

def print_top_rules(
    title,
    rules,
    limit=TOP_RULES_TO_PRINT
):

    print()
    print("-" * 78)
    print(title)
    print("-" * 78)

    if not rules:

        print("No rules.")

        return

    for number, rule in enumerate(
        rules[:limit],
        start=1
    ):

        conditions = " AND ".join(
            f"{feature}={value}"
            for feature, value
            in rule["conditions"]
        )

        print(
            f"{number:02d}. "
            f"{conditions} "
            f"=> {rule['direction']} | "
            f"samples={rule['samples']} | "
            f"confidence={rule['confidence']:.2%} | "
            f"directional={rule['directional_rate']:.2%} | "
            f"score={rule['score']:.4f}"
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

    if len(records) < (
        FOLDS * MIN_VALIDATION_MATCHES
    ):

        print(
            "Not enough records."
        )

        continue

    print_outcome_distribution(
        "FULL DATA OUTCOME DISTRIBUTION",
        records
    )

    # --------------------------------------------------------
    # OUTER WALK-FORWARD
    # --------------------------------------------------------

    fold_size = (
        len(records)
        // (FOLDS + 1)
    )

    fold_results = []

    aggregated_predictions = []

    for fold in range(
        FOLDS,
        0,
        -1
    ):

        outer_validation_start = (
            len(records)
            - fold_size * fold
        )

        outer_validation_end = (
            outer_validation_start
            + fold_size
        )

        outer_validation = records[
            outer_validation_start:
            outer_validation_end
        ]

        if not outer_validation:
            continue

        outer_start_index = (
            outer_validation[0]["index"]
        )

        print()
        print("-" * 78)
        print(
            f"OUTER FOLD {fold}"
        )
        print("-" * 78)

        print(
            "Outer validation start index:",
            outer_start_index
        )

        print(
            "Outer validation records:",
            len(outer_validation)
        )

        # ----------------------------------------------------
        # OUTER CALIBRATION
        # ----------------------------------------------------

        outer_calibration, outer_purged = (
            build_purged_calibration(
                records,
                outer_start_index,
                horizon
            )
        )

        print(
            "Outer calibration records:",
            len(outer_calibration)
        )

        print(
            "Outer purged records:",
            len(outer_purged)
        )

        if not outer_calibration:

            print(
                "Skipping fold: no outer calibration data."
            )

            continue

        # ----------------------------------------------------
        # INNER WALK-FORWARD SELECTION
        # ----------------------------------------------------

        inner_size = (
            len(outer_calibration)
            // 3
        )

        if inner_size < MIN_VALIDATION_MATCHES:

            print(
                "Skipping fold: insufficient inner data."
            )

            continue

        inner_train_end = (
            len(outer_calibration)
            - inner_size
        )

        inner_validation = outer_calibration[
            inner_train_end:
        ]

        inner_train_source = outer_calibration[
            :inner_train_end
        ]

        inner_validation_start_index = (
            inner_validation[0]["index"]
        )

        inner_calibration, inner_purged = (
            build_purged_calibration(
                inner_train_source,
                inner_validation_start_index,
                horizon
            )
        )

        print()
        print(
            "INNER SELECTION"
        )

        print(
            "Inner calibration records:",
            len(inner_calibration)
        )

        print(
            "Inner purged records:",
            len(inner_purged)
        )

        print(
            "Inner validation records:",
            len(inner_validation)
        )

        if len(inner_calibration) < (
            MIN_CALIBRATION_SAMPLES
        ):

            print(
                "Skipping fold: insufficient inner calibration."
            )

            continue

        # ----------------------------------------------------
        # LEAKAGE CHECK
        # ----------------------------------------------------

        leakage_found = False

        for record in inner_calibration:

            if (
                record["index"] + horizon
                >= inner_validation_start_index
            ):

                leakage_found = True

                break

        if leakage_found:

            raise RuntimeError(
                "CRITICAL: inner calibration contains "
                "future-label overlap."
            )

        print(
            "PASS: Inner calibration future-label overlap = NONE"
        )

        # ----------------------------------------------------
        # INNER QUANTILE MODEL
        # ----------------------------------------------------

        inner_quantile_model = (
            fit_quantile_model(
                inner_calibration
            )
        )

        inner_calibration_transformed = (
            transform_records(
                inner_calibration,
                inner_quantile_model
            )
        )

        inner_validation_transformed = (
            transform_records(
                inner_validation,
                inner_quantile_model
            )
        )

        # ----------------------------------------------------
        # INNER RULE DISCOVERY
        # ----------------------------------------------------

        inner_rules = discover_rules(
            inner_calibration_transformed
        )

        print(
            "Inner rules discovered:",
            len(inner_rules)
        )

        print_top_rules(
            "TOP INNER CALIBRATION RULES",
            inner_rules
        )

        # ----------------------------------------------------
        # INNER RULE VALIDATION
        # ----------------------------------------------------

        inner_rule_validation = (
            audit_rule_validation(
                inner_rules[
                    :MAX_RULES_FOR_VALIDATION
                ],
                inner_validation_transformed
            )
        )

        inner_baseline = baseline_metrics(
            inner_validation
        )

        inner_baseline_accuracy = (
            inner_baseline["accuracy"]
        )

        print_validation_selection_diagnostics(
            "INNER RULE VALIDATION DIAGNOSTICS",
            inner_rule_validation,
            inner_baseline_accuracy
        )

        print_top_rules(
            "TOP INNER VALIDATED RULES",
            [
                item["rule"]
                for item
                in inner_rule_validation
            ],
            TOP_VALIDATED_RULES_TO_PRINT
        )

        # ----------------------------------------------------
        # PERMUTATION / NULL TEST
        # ----------------------------------------------------

        permutation_null_result = (
            run_permutation_null_test(
                inner_calibration,
                inner_validation,
                inner_quantile_model,
                permutations=25,
                seed=341 + horizon + fold
            )
        )

        print_permutation_null_result(
            permutation_null_result
        )

        # ----------------------------------------------------
        # INNER RULE SELECTION
        #
        # Only inner validation is used for selection.
        # Outer validation remains untouched.
        # ----------------------------------------------------

        selected_candidates = []

        for item in inner_rule_validation:

            if (
                item["validation_accuracy"]
                <= inner_baseline_accuracy
            ):

                continue

            selected_candidates.append(
                item
            )

        selected_candidates.sort(

            key=lambda x: (

                x["validation_accuracy"],

                x["validation_matches"],

                x["rule"]["confidence"],

                x["rule"]["score"],
            ),

            reverse=True
        )

        # ----------------------------------------------------
        # LOCKED RULES
        # ----------------------------------------------------

        locked_rules = [

            item["rule"]

            for item
            in selected_candidates[
                :MAX_RULES_FOR_VALIDATION
            ]
        ]

        print(
            "Inner rules passing selection:",
            len(selected_candidates)
        )

        print(
            "LOCKED rules for outer validation:",
            len(locked_rules)
        )

        print_rule_search_diagnostics(
            "RULE SEARCH DIAGNOSTICS",
            inner_rules,
            selected_candidates,
            locked_rules
        )

        # ----------------------------------------------------
        # IMPORTANT FIX:
        #
        # The locked rules were generated using the INNER
        # quantile model.
        #
        # Therefore the outer validation MUST use the SAME
        # locked feature transformation.
        #
        # We intentionally do NOT replace it with a newly
        # fitted outer quantile model here because that would
        # change q1/q2 bucket meanings after the rules were
        # locked.
        #
        # The inner quantile model is fitted strictly before
        # outer validation and therefore does not leak outer
        # validation information.
        # ----------------------------------------------------

        outer_validation_transformed = (
            transform_records(
                outer_validation,
                inner_quantile_model
            )
        )

        # ----------------------------------------------------
        # OUTER VALIDATION
        #
        # LOCKED RULES ONLY.
        # NO SELECTION.
        # ----------------------------------------------------

        predictions = validate_rules(
            locked_rules,
            outer_validation_transformed
        )

        metrics = calculate_metrics(
            predictions,
            outer_validation_transformed
        )

        outer_baseline = baseline_metrics(
            outer_validation
        )

        baseline_accuracy = (
            outer_baseline["accuracy"]
        )

        accuracy_difference = (
            metrics["accuracy"]
            - baseline_accuracy
        )

        print()
        print(
            "LOCKED OUTER VALIDATION RESULT"
        )

        print(
            "Outer validation records:",
            len(outer_validation)
        )

        print(
            "Locked rules:",
            len(locked_rules)
        )

        print(
            "Outer validation predictions:",
            metrics["predictions"]
        )

        print(
            f"Outer directional accuracy: "
            f"{metrics['accuracy']:.2%}"
        )

        print(
            f"Outer majority baseline: "
            f"{baseline_accuracy:.2%}"
        )

        print(
            f"Outer accuracy vs baseline: "
            f"{accuracy_difference:+.2%}"
        )

        print(
            f"Outer coverage: "
            f"{metrics['coverage']:.2%}"
        )

        print(
            f"Outer BUY precision: "
            f"{metrics['buy_precision']:.2%}"
        )

        print(
            f"Outer SELL precision: "
            f"{metrics['sell_precision']:.2%}"
        )

        fold_results.append({

            "fold":
                fold,

            "outer_calibration":
                len(outer_calibration),

            "outer_purged":
                len(outer_purged),

            "inner_calibration":
                len(inner_calibration),

            "inner_purged":
                len(inner_purged),

            "inner_validation":
                len(inner_validation),

            "outer_validation":
                len(outer_validation),

            "rules_discovered_inner":
                len(inner_rules),

            "rules_selected_inner":
                len(selected_candidates),

            "locked_rules":
                len(locked_rules),

            "predictions":
                predictions,

            "metrics":
                metrics,

            "inner_rule_validation":
                inner_rule_validation,

            "permutation_null_result":
                permutation_null_result,
        })

        aggregated_predictions.extend(
            predictions
        )

    # ========================================================
    # AGGREGATED OUTER RESULT
    # ========================================================

    print()
    print("=" * 78)
    print(
        "AGGREGATED LOCKED "
        "OUTER OUT-OF-SAMPLE RESULT"
    )
    print("=" * 78)

    if aggregated_predictions:

        total_predictions = len(
            aggregated_predictions
        )

        correct = sum(

            x["prediction"] == x["actual"]

            for x in aggregated_predictions
        )

        accuracy = (
            correct
            / total_predictions
        )

        buys = [

            x

            for x in aggregated_predictions

            if x["prediction"] == "BUY"
        ]

        sells = [

            x

            for x in aggregated_predictions

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
            "Outer validation predictions:",
            total_predictions
        )

        print(
            "Correct predictions:",
            correct
        )

        print(
            f"Outer directional accuracy: "
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
            "No locked outer validation predictions."
        )

    # ========================================================
    # FINAL FOLD INFORMATION
    # ========================================================

    all_results[horizon] = {

        "fold_results":
            fold_results,

        "aggregated_predictions":
            aggregated_predictions,
    }


# ============================================================
# FINAL VERDICT
# ============================================================

print()
print("=" * 78)
print(
    "MLAI v3.4.2 FINAL VERDICT"
)
print("=" * 78)

print("""
This experiment is diagnostic only.

No production model was changed.
No learning memory was changed.
market_data.bin was READ ONLY.
mlai_v31.py was NOT modified.

METHODOLOGY:

1. Quantile boundaries are fitted ONLY from available
   calibration data.

2. Quantile boundaries are not refitted using outer
   validation data.

3. Calibration labels overlapping validation are purged.

4. Rules are discovered ONLY from calibration.

5. Rules are selected using INNER chronological validation.

6. Selected rules are LOCKED before outer validation.

7. Each validation record receives at most ONE prediction.

8. Validation results are compared with a chronological
   majority baseline.

9. Individual rules are separately audited against unseen
   validation data.

10. Calibration score is NOT called statistical lift.

11. Stable calibration rules are NOT automatically
    considered validated rules.

12. A permutation/null test is performed to investigate
    rule-search selection overfitting.

13. No rule is promoted to production.

A rule should only be considered a serious candidate when
it demonstrates meaningful out-of-sample validation evidence.

The actual output must be examined before making any
decision about the MLAI production system.
""")

print()
print(
    "MLAI v3.4.2 COMPLETE"
)