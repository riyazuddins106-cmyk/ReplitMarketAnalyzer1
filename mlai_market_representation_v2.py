import os
import math
import pickle
import random
from collections import Counter, defaultdict


# ============================================================
# MLAI MARKET REPRESENTATION v2
# ============================================================
#
# PURPOSE
# -------
# Research-only market representation and chronological
# walk-forward validation.
#
# IMPORTANT PROTECTION
# --------------------
# market_data.bin is READ ONLY.
# mlai_v31.py is NOT modified.
# Production files are NOT modified.
# Learning memory is NOT modified.
#
# v2 CORRECTIONS
# ---------------
#
# 1. Calibration rules are discovered using calibration data only.
#
# 2. Validation observations remain chronologically unseen.
#
# 3. Numeric discretization uses precomputed q1/q3 boundaries.
#
# 4. Quantile reference arrays are NOT repeatedly sorted.
#
# 5. Fold states are precomputed and reused.
#
# 6. Permutation testing preserves the exact chronological
#    walk-forward fold boundaries.
#
# 7. Permutation accuracy is aggregated across ALL validation
#    folds, exactly like the observed locked OOS accuracy.
#
# 8. Permutation testing changes only outcome labels.
#
# 9. Feature representation remains fixed during permutation.
#
# 10. Empirical permutation p-value is reported.
#
# ============================================================


MARKET_FILE = "market_data.bin"

OUTPUT_BIN = "mlai_market_representation_v2.bin"
OUTPUT_REPORT = "MLAI_MARKET_REPRESENTATION_V2_REPORT.md"

RANDOM_SEED = 42

VALIDATION_FOLDS = 4

MIN_RULE_SAMPLES = 20

MIN_RULE_CONFIDENCE = 0.50

MAX_RULES_TO_PRINT = 20

PERMUTATION_COUNT = 100

# Show progress every N permutations.
PERMUTATION_PROGRESS_INTERVAL = 10

LABELS = (
    "BUY",
    "SELL",
    "NEUTRAL"
)


# ============================================================
# PROTECTION
# ============================================================

def file_hash(path):
    import hashlib

    h = hashlib.sha256()

    with open(path, "rb") as f:

        while True:

            block = f.read(1024 * 1024)

            if not block:
                break

            h.update(block)

    return h.hexdigest()


def protection_check():

    print("=" * 80)
    print("PROTECTION CHECK")
    print("=" * 80)

    print(f"{MARKET_FILE:<20}: READ ONLY")
    print(f"{'mlai_v31.py':<20}: NOT MODIFIED")
    print(f"{'production':<20}: NOT MODIFIED")
    print(f"{'learning memory':<20}: NOT MODIFIED")

    if not os.path.exists(MARKET_FILE):

        raise FileNotFoundError(
            f"{MARKET_FILE} was not found."
        )

    print()


# ============================================================
# LOAD MARKET DATA
# ============================================================

def load_market_data():

    with open(MARKET_FILE, "rb") as f:

        data = pickle.load(f)

    print(
        f"Data type: {type(data).__name__}"
    )

    if isinstance(data, dict):

        if "candles" in data:

            candles = data["candles"]

        elif "data" in data:

            candles = data["data"]

        elif "market_data" in data:

            candles = data["market_data"]

        else:

            candidates = []

            for value in data.values():

                if isinstance(value, list):

                    candidates.append(value)

            if candidates:

                candles = max(
                    candidates,
                    key=len
                )

            else:

                raise ValueError(
                    "Dictionary loaded, but no candle "
                    "list was found."
                )

    elif isinstance(data, list):

        candles = data

    else:

        raise ValueError(
            "Unsupported market_data.bin structure."
        )

    print(
        f"Total candles: {len(candles)}"
    )

    return candles


# ============================================================
# OHLC EXTRACTION
# ============================================================

def get_value(
    candle,
    names,
    default=None
):

    if isinstance(candle, dict):

        for name in names:

            if name in candle:

                return candle[name]

        lowered = {
            str(k).lower(): v
            for k, v in candle.items()
        }

        for name in names:

            if name.lower() in lowered:

                return lowered[name.lower()]

    return default


def extract_ohlc(candle):

    o = get_value(
        candle,
        ["open", "o", "Open"]
    )

    h = get_value(
        candle,
        ["high", "h", "High"]
    )

    l = get_value(
        candle,
        ["low", "l", "Low"]
    )

    c = get_value(
        candle,
        ["close", "c", "Close"]
    )

    try:

        return (
            float(o),
            float(h),
            float(l),
            float(c)
        )

    except Exception:

        return None


def audit_ohlc(candles):

    valid = []

    invalid = 0
    non_positive_closes = 0
    negative_prices = 0
    malformed_ranges = 0

    for candle in candles:

        ohlc = extract_ohlc(candle)

        if ohlc is None:

            invalid += 1

            continue

        o, h, l, c = ohlc

        if c <= 0:

            non_positive_closes += 1

        if min(o, h, l, c) < 0:

            negative_prices += 1

        if (
            h < max(o, c)
            or l > min(o, c)
            or h < l
        ):

            malformed_ranges += 1

        valid.append(
            {
                "open": o,
                "high": h,
                "low": l,
                "close": c
            }
        )

    print("=" * 80)
    print("DATA QUALITY AUDIT")
    print("=" * 80)

    print(
        f"Invalid candles: {invalid}"
    )

    print(
        f"Non-positive closes: "
        f"{non_positive_closes}"
    )

    print(
        f"Negative prices: "
        f"{negative_prices}"
    )

    print(
        f"Malformed OHLC ranges: "
        f"{malformed_ranges}"
    )

    if (
        invalid == 0
        and non_positive_closes == 0
        and negative_prices == 0
        and malformed_ranges == 0
    ):

        print(
            "PASS: basic OHLC integrity appears valid."
        )

    print()

    return valid


# ============================================================
# SAFE MATH
# ============================================================

def safe_div(a, b):

    if b is None:

        return 0.0

    if abs(b) < 1e-12:

        return 0.0

    return a / b


def clamp(x, low, high):

    return max(
        low,
        min(high, x)
    )


# ============================================================
# CANDLE CLASSIFICATION
# ============================================================

def classify_candle(
    o,
    h,
    l,
    c
):

    rng = max(
        h - l,
        1e-12
    )

    body = abs(
        c - o
    )

    body_ratio = (
        body / rng
    )

    upper_wick = (
        h - max(o, c)
    )

    lower_wick = (
        min(o, c) - l
    )

    upper_ratio = (
        upper_wick / rng
    )

    lower_ratio = (
        lower_wick / rng
    )

    if body_ratio <= 0.10:

        return "doji"

    if (
        c > o
        and body_ratio >= 0.65
        and safe_div(
            c - l,
            rng
        ) >= 0.75
    ):

        return "strong_bullish"

    if (
        c < o
        and body_ratio >= 0.65
        and safe_div(
            h - c,
            rng
        ) >= 0.75
    ):

        return "strong_bearish"

    if (
        c > o
        and body_ratio >= 0.50
    ):

        return "bullish_close_strong"

    if (
        c < o
        and body_ratio >= 0.50
    ):

        return "bearish_close_strong"

    if (
        lower_ratio >= 0.55
        and body_ratio <= 0.35
    ):

        return "hammer_like"

    if (
        upper_ratio >= 0.55
        and body_ratio <= 0.35
    ):

        return "shooting_star_like"

    return "normal"


# ============================================================
# RETURNS
# ============================================================

def return_n(
    closes,
    i,
    n
):

    if i < n:

        return 0.0

    previous = closes[
        i - n
    ]

    if abs(previous) < 1e-12:

        return 0.0

    return (
        closes[i] - previous
    ) / previous


# ============================================================
# ROLLING VOLATILITY
# ============================================================

def rolling_returns(
    closes,
    i,
    window
):

    start = max(
        1,
        i - window + 1
    )

    values = []

    for j in range(
        start,
        i + 1
    ):

        previous = closes[
            j - 1
        ]

        if abs(previous) < 1e-12:

            continue

        values.append(
            (
                closes[j] - previous
            ) / previous
        )

    return values


def volatility(
    closes,
    i,
    window=20
):

    if i < 0:

        return 0.0

    values = rolling_returns(
        closes,
        i,
        window
    )

    if len(values) < 2:

        return 0.0

    mean = (
        sum(values)
        / len(values)
    )

    variance = sum(
        (x - mean) ** 2
        for x in values
    ) / len(values)

    return math.sqrt(
        max(
            variance,
            0.0
        )
    )


# ============================================================
# QUANTILE HELPERS
# ============================================================

def quantile(
    values,
    q
):

    if not values:

        return 0.0

    values = sorted(values)

    position = (
        (len(values) - 1)
        * q
    )

    lower = int(
        math.floor(position)
    )

    upper = int(
        math.ceil(position)
    )

    if lower == upper:

        return values[lower]

    fraction = (
        position - lower
    )

    return (
        values[lower]
        +
        (
            values[upper]
            - values[lower]
        )
        * fraction
    )


# ============================================================
# OPTIMIZED QUANTILE DISCRETIZATION
# ============================================================
#
# OLD APPROACH
# ------------
# Every call to quantile_label() sorted the complete
# calibration reference list again.
#
# NEW APPROACH
# ------------
# fit_discretizer() calculates q1 and q3 ONCE.
#
# references become:
#
#     {
#         feature: {
#             "q1": ...,
#             "q3": ...
#         }
#     }
#
# Discretization then performs only two comparisons.
#
# ============================================================

def quantile_label(
    value,
    reference
):

    if not reference:

        return "q2"

    if isinstance(
        reference,
        dict
    ):

        q1 = reference.get(
            "q1",
            0.0
        )

        q3 = reference.get(
            "q3",
            0.0
        )

    else:

        # Compatibility fallback.
        #
        # The optimized research path never reaches
        # this branch because fit_discretizer()
        # stores q1/q3 dictionaries.

        q1 = quantile(
            reference,
            0.25
        )

        q3 = quantile(
            reference,
            0.75
        )

    if value <= q1:

        return "q1"

    if value >= q3:

        return "q3"

    return "q2"


# ============================================================
# FEATURE ENGINE
# ============================================================

def build_raw_features(candles):

    n = len(candles)

    opens = [
        x["open"]
        for x in candles
    ]

    highs = [
        x["high"]
        for x in candles
    ]

    lows = [
        x["low"]
        for x in candles
    ]

    closes = [
        x["close"]
        for x in candles
    ]

    features = []

    candle_labels = []

    for i in range(n):

        o = opens[i]
        h = highs[i]
        l = lows[i]
        c = closes[i]

        rng = max(
            h - l,
            1e-12
        )

        body = abs(
            c - o
        )

        upper_wick = (
            h - max(o, c)
        )

        lower_wick = (
            min(o, c) - l
        )

        recent_start = max(
            0,
            i - 19
        )

        recent_high = max(
            highs[
                recent_start:i + 1
            ]
        )

        recent_low = min(
            lows[
                recent_start:i + 1
            ]
        )

        recent_range = (
            recent_high
            - recent_low
        )

        location = safe_div(
            c - recent_low,
            recent_range
        )

        label = classify_candle(
            o,
            h,
            l,
            c
        )

        candle_labels.append(
            label
        )

        ret5 = return_n(
            closes,
            i,
            5
        )

        ret10 = return_n(
            closes,
            i,
            10
        )

        ret20 = return_n(
            closes,
            i,
            20
        )

        ret30 = return_n(
            closes,
            i,
            30
        )

        ret60 = return_n(
            closes,
            i,
            60
        )

        vol20 = volatility(
            closes,
            i,
            20
        )

        previous_vol = (
            volatility(
                closes,
                i - 10,
                20
            )
            if i >= 11
            else vol20
        )

        vol_ratio = safe_div(
            vol20,
            previous_vol
        )

        bullish_count = 0
        bearish_count = 0

        direction_window = max(
            0,
            i - 19
        )

        for j in range(
            direction_window,
            i + 1
        ):

            if closes[j] > opens[j]:

                bullish_count += 1

            elif closes[j] < opens[j]:

                bearish_count += 1

        total_directional = (
            bullish_count
            + bearish_count
        )

        bullish_ratio = safe_div(
            bullish_count,
            total_directional
        )

        bearish_ratio = safe_div(
            bearish_count,
            total_directional
        )

        directional_imbalance = (
            bullish_ratio
            - bearish_ratio
        )

        slope = ret60

        momentum_acceleration = (
            ret10 - ret20
        )

        if slope > 0.002:

            directional_regime = (
                "bullish"
            )

        elif slope < -0.002:

            directional_regime = (
                "bearish"
            )

        else:

            directional_regime = (
                "neutral"
            )

        if vol_ratio > 1.15:

            volatility_regime = (
                "expanding"
            )

        elif vol_ratio < 0.85:

            volatility_regime = (
                "contracting"
            )

        else:

            volatility_regime = (
                "stable"
            )

        if location >= 0.75:

            location_state = (
                "upper_range"
            )

        elif location <= 0.25:

            location_state = (
                "lower_range"
            )

        else:

            location_state = (
                "middle_range"
            )

        if abs(slope) >= 0.003:

            trend_consistency = (
                "strong"
            )

        elif abs(slope) >= 0.001:

            trend_consistency = (
                "moderate"
            )

        else:

            trend_consistency = (
                "weak"
            )

        if directional_imbalance > 0.15:

            pressure = "bullish"

        elif directional_imbalance < -0.15:

            pressure = "bearish"

        else:

            pressure = "neutral"

        if location >= 0.90:

            range_event = "near_high"

        elif location <= 0.10:

            range_event = "near_low"

        else:

            range_event = "inside_range"

        if i >= 20:

            prior_high = max(
                highs[i - 20:i]
            )

            prior_low = min(
                lows[i - 20:i]
            )

            if h > prior_high:

                swing_high_state = (
                    "higher_high"
                )

            elif h < prior_high:

                swing_high_state = (
                    "lower_high"
                )

            else:

                swing_high_state = (
                    "equal_high"
                )

            if l < prior_low:

                swing_low_state = (
                    "lower_low"
                )

            elif l > prior_low:

                swing_low_state = (
                    "higher_low"
                )

            else:

                swing_low_state = (
                    "equal_low"
                )

        else:

            swing_high_state = (
                "unknown"
            )

            swing_low_state = (
                "unknown"
            )

        if (
            directional_regime == "bullish"
            and
            swing_high_state == "higher_high"
        ):

            structure_regime = (
                "up_structure"
            )

        elif (
            directional_regime == "bearish"
            and
            swing_low_state == "lower_low"
        ):

            structure_regime = (
                "down_structure"
            )

        else:

            structure_regime = (
                "mixed_structure"
            )

        features.append(
            {
                "latest_candle":
                    label,

                "return_5":
                    ret5,

                "return_10":
                    ret10,

                "return_20":
                    ret20,

                "return_30":
                    ret30,

                "return_60":
                    ret60,

                "bullish_ratio":
                    bullish_ratio,

                "bearish_ratio":
                    bearish_ratio,

                "directional_imbalance":
                    directional_imbalance,

                "volatility":
                    vol20,

                "volatility_ratio":
                    vol_ratio,

                "location_in_range":
                    location,

                "normalized_slope":
                    slope,

                "momentum_acceleration":
                    momentum_acceleration,

                "recent_body_ratio":
                    safe_div(
                        body,
                        rng
                    ),

                "recent_upper_wick":
                    safe_div(
                        upper_wick,
                        rng
                    ),

                "recent_lower_wick":
                    safe_div(
                        lower_wick,
                        rng
                    ),

                "directional_regime":
                    directional_regime,

                "volatility_regime":
                    volatility_regime,

                "location_state":
                    location_state,

                "trend_consistency":
                    trend_consistency,

                "pressure":
                    pressure,

                "range_event":
                    range_event,

                "swing_high_state":
                    swing_high_state,

                "swing_low_state":
                    swing_low_state,

                "structure_regime":
                    structure_regime
            }
        )

    return (
        features,
        candle_labels
    )


# ============================================================
# OUTCOME LABEL
# ============================================================

def outcome_label(
    closes,
    index,
    horizon
):

    future_index = (
        index + horizon
    )

    if future_index >= len(closes):

        return None

    current = closes[index]

    future = closes[
        future_index
    ]

    if current <= 0:

        return None

    change = (
        future - current
    ) / current

    threshold = 0.0005

    if change > threshold:

        return "BUY"

    if change < -threshold:

        return "SELL"

    return "NEUTRAL"


# ============================================================
# DATASET CREATION
# ============================================================

def build_dataset(
    candles,
    features,
    horizon
):

    closes = [
        x["close"]
        for x in candles
    ]

    records = []

    start = 60

    end = (
        len(candles)
        - horizon
    )

    for i in range(
        start,
        end
    ):

        outcome = outcome_label(
            closes,
            i,
            horizon
        )

        if outcome is None:

            continue

        records.append(
            {
                "index": i,
                "features": features[i],
                "outcome": outcome
            }
        )

    return records


# ============================================================
# FEATURE DEFINITIONS
# ============================================================

NUMERIC_FEATURES = [

    "return_5",
    "return_10",
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
    "momentum_acceleration",

    "recent_body_ratio",
    "recent_upper_wick",
    "recent_lower_wick"
]


CATEGORICAL_FEATURES = [

    "latest_candle",

    "directional_regime",
    "volatility_regime",
    "location_state",
    "trend_consistency",
    "pressure",
    "range_event",

    "swing_high_state",
    "swing_low_state",

    "structure_regime"
]


# ============================================================
# OPTIMIZED DISCRETIZER
# ============================================================

def fit_discretizer(records):

    references = {}

    for feature in NUMERIC_FEATURES:

        values = []

        for record in records:

            value = record[
                "features"
            ].get(
                feature
            )

            if isinstance(
                value,
                (int, float)
            ):

                if math.isfinite(value):

                    values.append(
                        value
                    )

        if values:

            # IMPORTANT:
            # Sort exactly once per feature.
            #
            # The resulting q1/q3 are reused for every
            # record in this calibration fold.

            values.sort()

            q1 = quantile(
                values,
                0.25
            )

            q3 = quantile(
                values,
                0.75
            )

        else:

            q1 = 0.0
            q3 = 0.0

        references[feature] = {
            "q1": q1,
            "q3": q3
        }

    return references


def discretize_record(
    record,
    references
):

    features = record[
        "features"
    ]

    result = {}

    for feature in NUMERIC_FEATURES:

        result[feature] = (
            quantile_label(
                features.get(
                    feature,
                    0.0
                ),
                references.get(
                    feature,
                    {}
                )
            )
        )

    for feature in CATEGORICAL_FEATURES:

        result[feature] = str(
            features.get(
                feature,
                "unknown"
            )
        )

    return result


def discretize_records(
    records,
    references
):

    return [
        discretize_record(
            record,
            references
        )
        for record in records
    ]


# ============================================================
# RULE DISCOVERY
# ============================================================

def discover_rules_from_states(
    records,
    states
):

    if not records:

        return []

    candidate_counts = defaultdict(
        Counter
    )

    pair_counts = defaultdict(
        Counter
    )

    for record, state in zip(
        records,
        states
    ):

        outcome = record[
            "outcome"
        ]

        keys = list(
            state.keys()
        )

        for key in keys:

            candidate_counts[
                (
                    key,
                    state[key]
                )
            ][outcome] += 1

        for a in range(
            len(keys)
        ):

            for b in range(
                a + 1,
                len(keys)
            ):

                key1 = keys[a]
                key2 = keys[b]

                pair_key = (
                    key1,
                    state[key1],
                    key2,
                    state[key2]
                )

                pair_counts[
                    pair_key
                ][outcome] += 1

    rules = []

    # --------------------------------------------------------
    # SINGLE FEATURE RULES
    # --------------------------------------------------------

    for condition, counts in (
        candidate_counts.items()
    ):

        total = sum(
            counts.values()
        )

        if total < MIN_RULE_SAMPLES:

            continue

        label, count = (
            counts.most_common(1)[0]
        )

        confidence = safe_div(
            count,
            total
        )

        if confidence < MIN_RULE_CONFIDENCE:

            continue

        rules.append(
            {
                "type": "single",
                "condition": condition,
                "prediction": label,
                "samples": total,
                "confidence": confidence
            }
        )

    # --------------------------------------------------------
    # TWO FEATURE RULES
    # --------------------------------------------------------

    for condition, counts in (
        pair_counts.items()
    ):

        total = sum(
            counts.values()
        )

        if total < MIN_RULE_SAMPLES:

            continue

        label, count = (
            counts.most_common(1)[0]
        )

        confidence = safe_div(
            count,
            total
        )

        if confidence < MIN_RULE_CONFIDENCE:

            continue

        rules.append(
            {
                "type": "pair",
                "condition": condition,
                "prediction": label,
                "samples": total,
                "confidence": confidence
            }
        )

    rules.sort(
        key=lambda x: (
            x["confidence"],
            x["samples"]
        ),
        reverse=True
    )

    return rules


def discover_rules(
    calibration_records
):

    if not calibration_records:

        return []

    references = fit_discretizer(
        calibration_records
    )

    states = discretize_records(
        calibration_records,
        references
    )

    return discover_rules_from_states(
        calibration_records,
        states
    )


# ============================================================
# RULE MATCHING
# ============================================================

def rule_matches(
    rule,
    state
):

    condition = rule[
        "condition"
    ]

    if rule["type"] == "single":

        feature, value = condition

        return (
            state.get(feature)
            == value
        )

    if rule["type"] == "pair":

        f1, v1, f2, v2 = condition

        return (
            state.get(f1) == v1
            and
            state.get(f2) == v2
        )

    return False


# ============================================================
# VALIDATION PREDICTION
# ============================================================

def predict_from_state(
    state,
    rules
):

    matches = []

    for rule in rules:

        if rule_matches(
            rule,
            state
        ):

            matches.append(
                rule
            )

    if not matches:

        return (
            None,
            None
        )

    matches.sort(
        key=lambda x: (
            x["confidence"],
            x["samples"]
        ),
        reverse=True
    )

    best = matches[0]

    return (
        best["prediction"],
        best
    )


def predict_with_rules(
    record,
    rules,
    references
):

    state = discretize_record(
        record,
        references
    )

    prediction, rule = (
        predict_from_state(
            state,
            rules
        )
    )

    return (
        prediction,
        rule,
        state
    )


# ============================================================
# EVALUATION
# ============================================================

def evaluate_fold(
    calibration,
    validation
):

    if not calibration:

        return {
            "rules": [],
            "predictions": [],
            "accuracy": 0.0,
            "coverage": 0.0,
            "references": {}
        }

    references = fit_discretizer(
        calibration
    )

    calibration_states = (
        discretize_records(
            calibration,
            references
        )
    )

    validation_states = (
        discretize_records(
            validation,
            references
        )
    )

    rules = discover_rules_from_states(
        calibration,
        calibration_states
    )

    predictions = []

    correct = 0

    for record, state in zip(
        validation,
        validation_states
    ):

        prediction, rule = (
            predict_from_state(
                state,
                rules
            )
        )

        if prediction is None:

            continue

        actual = record[
            "outcome"
        ]

        is_correct = (
            prediction == actual
        )

        if is_correct:

            correct += 1

        predictions.append(
            {
                "index":
                    record["index"],

                "prediction":
                    prediction,

                "actual":
                    actual,

                "correct":
                    is_correct,

                "rule":
                    rule,

                "state":
                    state
            }
        )

    total_validation = len(
        validation
    )

    prediction_count = len(
        predictions
    )

    accuracy = safe_div(
        correct,
        prediction_count
    )

    coverage = safe_div(
        prediction_count,
        total_validation
    )

    return {
        "rules":
            rules,

        "predictions":
            predictions,

        "accuracy":
            accuracy,

        "coverage":
            coverage,

        "references":
            references
    }


# ============================================================
# BASELINE
# ============================================================

def baseline_report(records):

    counts = Counter(
        record["outcome"]
        for record in records
    )

    total = len(records)

    percentages = {}

    for label in LABELS:

        percentages[label] = (
            100
            * safe_div(
                counts[label],
                total
            )
        )

    majority = max(
        LABELS,
        key=lambda x: counts[x]
    )

    return {
        "counts":
            dict(counts),

        "percentages":
            percentages,

        "majority":
            majority,

        "majority_percentage":
            percentages[majority]
    }


# ============================================================
# WALK FORWARD
# ============================================================

def walk_forward(
    records,
    folds=VALIDATION_FOLDS
):

    n = len(records)

    validation_size = n // (
        folds + 1
    )

    if validation_size <= 0:

        raise ValueError(
            "Not enough records for "
            "walk-forward validation."
        )

    fold_results = []

    all_predictions = []

    for fold in range(
        1,
        folds + 1
    ):

        validation_start = (
            fold
            * validation_size
        )

        validation_end = (
            validation_start
            + validation_size
        )

        calibration = records[
            :validation_start
        ]

        validation = records[
            validation_start:
            validation_end
        ]

        result = evaluate_fold(
            calibration,
            validation
        )

        result["fold"] = fold

        result["calibration_size"] = (
            len(calibration)
        )

        result["validation_size"] = (
            len(validation)
        )

        # Explicit boundaries are stored so that the
        # permutation test can reproduce the EXACT
        # chronological validation windows.

        result["validation_start"] = (
            validation_start
        )

        result["validation_end"] = (
            validation_end
        )

        fold_results.append(
            result
        )

        all_predictions.extend(
            result["predictions"]
        )

    total_validation = sum(
        x["validation_size"]
        for x in fold_results
    )

    total_predictions = len(
        all_predictions
    )

    correct = sum(
        1
        for x in all_predictions
        if x["correct"]
    )

    accuracy = safe_div(
        correct,
        total_predictions
    )

    coverage = safe_div(
        total_predictions,
        total_validation
    )

    return {
        "folds":
            fold_results,

        "predictions":
            all_predictions,

        "validation_observations":
            total_validation,

        "prediction_count":
            total_predictions,

        "accuracy":
            accuracy,

        "coverage":
            coverage
    }


# ============================================================
# SEQUENCE ANALYSIS
# ============================================================

def sequence_analysis(
    records,
    candle_labels,
    length
):

    counts = defaultdict(
        Counter
    )

    for record in records:

        i = record[
            "index"
        ]

        start = (
            i - length + 1
        )

        if start < 0:

            continue

        sequence = tuple(
            candle_labels[
                start:i + 1
            ]
        )

        counts[
            sequence
        ][
            record["outcome"]
        ] += 1

    candidates = []

    for sequence, counter in (
        counts.items()
    ):

        total = sum(
            counter.values()
        )

        if total < 20:

            continue

        label, count = (
            counter.most_common(1)[0]
        )

        confidence = safe_div(
            count,
            total
        )

        if confidence < 0.20:

            continue

        candidates.append(
            {
                "sequence":
                    sequence,

                "prediction":
                    label,

                "samples":
                    total,

                "confidence":
                    confidence
            }
        )

    candidates.sort(
        key=lambda x: (
            x["confidence"],
            x["samples"]
        ),
        reverse=True
    )

    return candidates[:10]


# ============================================================
# CURRENT MARKET STATE
# ============================================================

def current_state(
    candles,
    features,
    candle_labels
):

    i = (
        len(candles)
        - 1
    )

    state = features[i]

    sequence_start = max(
        0,
        i - 4
    )

    sequence = candle_labels[
        sequence_start:i + 1
    ]

    return {
        "index":
            i,

        "close":
            candles[i]["close"],

        "features":
            state,

        "sequence":
            sequence
    }


# ============================================================
# PERMUTATION FOLD CACHE
# ============================================================
#
# This is the major performance improvement.
#
# Feature states do NOT change when outcome labels are
# shuffled.
#
# Therefore:
#
#     calibration references
#     calibration states
#     validation states
#
# can be calculated ONCE for every fold.
#
# During every permutation, only the labels and rules change.
#
# ============================================================

def build_permutation_fold_cache(
    records,
    fold_structure
):

    cache = []

    for fold in fold_structure:

        calibration_size = (
            fold["calibration_size"]
        )

        validation_start = (
            fold["validation_start"]
        )

        validation_end = (
            fold["validation_end"]
        )

        calibration = records[
            :calibration_size
        ]

        validation = records[
            validation_start:
            validation_end
        ]

        references = fit_discretizer(
            calibration
        )

        calibration_states = (
            discretize_records(
                calibration,
                references
            )
        )

        validation_states = (
            discretize_records(
                validation,
                references
            )
        )

        cache.append(
            {
                "fold":
                    fold["fold"],

                "calibration_size":
                    calibration_size,

                "validation_start":
                    validation_start,

                "validation_end":
                    validation_end,

                "calibration_states":
                    calibration_states,

                "validation_states":
                    validation_states
            }
        )

    return cache


# ============================================================
# FAST PERMUTATION FOLD EVALUATION
# ============================================================

def evaluate_permutation_fold(
    calibration_records,
    validation_records,
    calibration_states,
    validation_states
):

    rules = discover_rules_from_states(
        calibration_records,
        calibration_states
    )

    correct = 0
    predictions = 0

    for record, state in zip(
        validation_records,
        validation_states
    ):

        prediction, _ = (
            predict_from_state(
                state,
                rules
            )
        )

        if prediction is None:

            continue

        predictions += 1

        if prediction == record[
            "outcome"
        ]:

            correct += 1

    accuracy = safe_div(
        correct,
        predictions
    )

    coverage = safe_div(
        predictions,
        len(validation_records)
    )

    return (
        correct,
        predictions,
        accuracy,
        coverage
    )


# ============================================================
# CORRECTED PERMUTATION NULL TEST
# ============================================================
#
# IMPORTANT STATISTICAL CORRECTION
# --------------------------------
#
# The previous implementation compared:
#
#     observed = aggregate accuracy across all folds
#
# against:
#
#     null = BEST individual fold accuracy
#
# That is not an apples-to-apples comparison.
#
# This implementation calculates:
#
#     observed:
#         aggregate locked OOS accuracy
#
#     null:
#         aggregate accuracy across ALL corresponding
#         chronological validation folds
#
# Every permutation therefore uses exactly the same
# fold boundaries as the observed experiment.
#
# ============================================================

def permutation_test(
    records,
    fold_structure,
    observed_accuracy,
    count=100
):

    if not records:

        return {
            "observed":
                0.0,

            "mean_null":
                0.0,

            "max_null":
                0.0,

            "count":
                count,

            "empirical_p_value":
                1.0,

            "null_results":
                []
        }

    if count <= 0:

        return {
            "observed":
                observed_accuracy,

            "mean_null":
                0.0,

            "max_null":
                0.0,

            "count":
                0,

            "empirical_p_value":
                1.0,

            "null_results":
                []
        }

    print()

    print(
        "Preparing optimized permutation fold cache..."
    )

    fold_cache = (
        build_permutation_fold_cache(
            records,
            fold_structure
        )
    )

    print(
        "Permutation fold cache ready."
    )

    original_labels = [
        record["outcome"]
        for record in records
    ]

    rng = random.Random(
        RANDOM_SEED
    )

    null_results = []

    for permutation_number in range(
        1,
        count + 1
    ):

        shuffled = list(
            original_labels
        )

        rng.shuffle(
            shuffled
        )

        total_correct = 0
        total_predictions = 0

        for cached_fold in (
            fold_cache
        ):

            calibration_size = (
                cached_fold[
                    "calibration_size"
                ]
            )

            validation_start = (
                cached_fold[
                    "validation_start"
                ]
            )

            validation_end = (
                cached_fold[
                    "validation_end"
                ]
            )

            # --------------------------------------------
            # EXACT ORIGINAL CHRONOLOGICAL WINDOWS
            # --------------------------------------------

            calibration_original = records[
                :calibration_size
            ]

            validation_original = records[
                validation_start:
                validation_end
            ]

            # --------------------------------------------
            # Apply shuffled labels while preserving
            # every original feature and candle index.
            # --------------------------------------------

            calibration = []

            for i, record in enumerate(
                calibration_original
            ):

                calibration.append(
                    {
                        "index":
                            record["index"],

                        "features":
                            record["features"],

                        "outcome":
                            shuffled[i]
                    }
                )

            validation = []

            for i in range(
                validation_start,
                validation_end
            ):

                original_record = (
                    validation_original[
                        i - validation_start
                    ]
                )

                validation.append(
                    {
                        "index":
                            original_record[
                                "index"
                            ],

                        "features":
                            original_record[
                                "features"
                            ],

                        "outcome":
                            shuffled[i]
                    }
                )

            correct, predictions, _, _ = (
                evaluate_permutation_fold(
                    calibration,
                    validation,
                    cached_fold[
                        "calibration_states"
                    ],
                    cached_fold[
                        "validation_states"
                    ]
                )
            )

            total_correct += correct

            total_predictions += (
                predictions
            )

        permutation_accuracy = safe_div(
            total_correct,
            total_predictions
        )

        null_results.append(
            permutation_accuracy
        )

        if (
            permutation_number
            % PERMUTATION_PROGRESS_INTERVAL
            == 0
            or
            permutation_number == count
        ):

            print(
                f"Permutation "
                f"{permutation_number}/"
                f"{count}"
                f" | null accuracy="
                f"{permutation_accuracy * 100:.2f}%"
            )

    mean_null = (
        sum(null_results)
        / len(null_results)
        if null_results
        else 0.0
    )

    max_null = (
        max(null_results)
        if null_results
        else 0.0
    )

    # --------------------------------------------------------
    # Empirical one-sided p-value.
    #
    # Add-one correction avoids a reported p-value of exactly
    # zero when no permutation reaches the observed result.
    # --------------------------------------------------------

    extreme_count = sum(
        1
        for value in null_results
        if value >= observed_accuracy
    )

    empirical_p_value = (
        extreme_count + 1
    ) / (
        len(null_results) + 1
    )

    return {
        "observed":
            observed_accuracy,

        "mean_null":
            mean_null,

        "max_null":
            max_null,

        "count":
            count,

        "empirical_p_value":
            empirical_p_value,

        "null_results":
            null_results
    }


# ============================================================
# REPORT HELPERS
# ============================================================

def format_rule(rule):

    condition = rule[
        "condition"
    ]

    if rule["type"] == "single":

        text = (
            f"{condition[0]}="
            f"{condition[1]}"
        )

    else:

        text = (
            f"{condition[0]}="
            f"{condition[1]}"
            f" + "
            f"{condition[2]}="
            f"{condition[3]}"
        )

    return (
        f"{text} -> "
        f"{rule['prediction']} | "
        f"n={rule['samples']} | "
        f"confidence="
        f"{rule['confidence'] * 100:.2f}%"
    )


def print_rules(
    rules,
    limit=MAX_RULES_TO_PRINT
):

    for rule in rules[:limit]:

        print(
            format_rule(rule)
        )


# ============================================================
# HORIZON RESEARCH
# ============================================================

def run_horizon(
    candles,
    features,
    horizon,
    candle_labels
):

    print("=" * 80)

    print(
        f"HORIZON {horizon} CANDLES"
    )

    print("=" * 80)

    records = build_dataset(
        candles,
        features,
        horizon
    )

    print(
        f"Historical records: "
        f"{len(records)}"
    )

    print()

    # --------------------------------------------------------
    # BASELINE
    # --------------------------------------------------------

    print("-" * 80)
    print("BASELINE")
    print("-" * 80)

    baseline = baseline_report(
        records
    )

    for label in LABELS:

        print(
            f"{label:<10}: "
            f"{baseline['percentages'][label]:.2f}%"
        )

    print(
        f"Majority : "
        f"{baseline['majority']} "
        f"("
        f"{baseline['majority_percentage']:.2f}%"
        f")"
    )

    print()

    print(
        f"Walk-forward folds: "
        f"{VALIDATION_FOLDS}"
    )

    print()

    # --------------------------------------------------------
    # WALK FORWARD
    # --------------------------------------------------------

    wf = walk_forward(
        records,
        VALIDATION_FOLDS
    )

    for fold in wf["folds"]:

        print("-" * 80)

        print(
            f"FOLD {fold['fold']}"
        )

        print("-" * 80)

        print(
            f"Calibration: "
            f"{fold['calibration_size']}"
        )

        print(
            f"Validation: "
            f"{fold['validation_size']}"
        )

        print(
            f"Rules discovered: "
            f"{len(fold['rules'])}"
        )

        print()

        print_rules(
            fold["rules"]
        )

        print()

        print(
            f"Validation predictions: "
            f"{len(fold['predictions'])}"
        )

        print(
            f"Accuracy: "
            f"{fold['accuracy'] * 100:.2f}%"
        )

        print(
            f"Coverage: "
            f"{fold['coverage'] * 100:.2f}%"
        )

    print()

    # --------------------------------------------------------
    # LOCKED OOS
    # --------------------------------------------------------

    print("=" * 80)
    print("LOCKED OUT-OF-SAMPLE RESULT")
    print("=" * 80)

    print(
        f"Validation observations: "
        f"{wf['validation_observations']}"
    )

    print(
        f"Predictions: "
        f"{wf['prediction_count']}"
    )

    print(
        f"Accuracy: "
        f"{wf['accuracy'] * 100:.2f}%"
    )

    print(
        f"Coverage: "
        f"{wf['coverage'] * 100:.2f}%"
    )

    # --------------------------------------------------------
    # SEQUENCE ANALYSIS
    # --------------------------------------------------------

    print()

    print("=" * 80)
    print("CANDLE SEQUENCE ANALYSIS")
    print("=" * 80)

    sequence_results = {}

    for length in (
        2,
        3,
        5
    ):

        results = sequence_analysis(
            records,
            candle_labels,
            length
        )

        sequence_results[
            length
        ] = results

        print()

        print(
            f"SEQUENCE LENGTH {length}"
        )

        print(
            f"Candidate sequences: "
            f"{len(results)}"
        )

        for item in results:

            sequence_text = (
                " -> ".join(
                    item["sequence"]
                )
            )

            print(
                f"  {sequence_text} "
                f"=> "
                f"{item['prediction']} "
                f"| n={item['samples']} "
                f"| confidence="
                f"{item['confidence'] * 100:.2f}%"
            )

    # --------------------------------------------------------
    # PERMUTATION NULL TEST
    # --------------------------------------------------------

    print()

    print("=" * 80)
    print("PERMUTATION NULL TEST")
    print("=" * 80)

    print(
        "Purpose:"
    )

    print(
        "Estimate how strong a result can appear "
        "when outcome labels contain no real "
        "predictive structure."
    )

    print(
        "Method:"
    )

    print(
        "Outcome labels are shuffled while "
        "features remain fixed."
    )

    print(
        "Chronological fold boundaries are "
        "preserved exactly."
    )

    print(
        "Null accuracy is aggregated across "
        "all validation folds."
    )

    print(
        f"Permutation count: "
        f"{PERMUTATION_COUNT}"
    )

    permutation = permutation_test(
        records,
        wf["folds"],
        wf["accuracy"],
        PERMUTATION_COUNT
    )

    print()

    print(
        f"Observed locked accuracy: "
        f"{permutation['observed'] * 100:.2f}%"
    )

    print(
        f"Mean null accuracy: "
        f"{permutation['mean_null'] * 100:.2f}%"
    )

    print(
        f"Maximum null accuracy: "
        f"{permutation['max_null'] * 100:.2f}%"
    )

    print(
        f"Empirical permutation p-value: "
        f"{permutation['empirical_p_value']:.4f}"
    )

    if (
        permutation["observed"]
        <= permutation["max_null"]
    ):

        print()

        print(
            "WARNING:"
        )

        print(
            "Observed result does not exceed "
            "the maximum null result."
        )

    else:

        print()

        print(
            "Observed result exceeds the "
            "maximum null result in this test."
        )

    if (
        permutation["observed"]
        <= baseline["majority_percentage"]
        / 100.0
    ):

        print()

        print(
            "BASELINE WARNING:"
        )

        print(
            "Locked OOS accuracy does not exceed "
            "the simple majority-class baseline."
        )

    return {
        "records":
            len(records),

        "baseline":
            baseline,

        "walk_forward":
            wf,

        "sequence_analysis":
            sequence_results,

        "permutation":
            permutation
    }


# ============================================================
# CURRENT MARKET DISPLAY
# ============================================================

def print_current_market(
    current
):

    print()

    print("=" * 80)
    print("CURRENT MARKET STRUCTURE")
    print("=" * 80)

    print(
        f"Latest candle index: "
        f"{current['index']}"
    )

    print(
        f"Latest close: "
        f"{current['close']}"
    )

    f = current[
        "features"
    ]

    print()

    print(
        f"Directional regime: "
        f"{f['directional_regime']}"
    )

    print(
        f"Trend consistency: "
        f"{f['trend_consistency']}"
    )

    print(
        f"Volatility regime: "
        f"{f['volatility_regime']}"
    )

    print(
        f"Location: "
        f"{f['location_state']}"
    )

    if (
        f["momentum_acceleration"]
        > 0
    ):

        momentum = "bullish"

    elif (
        f["momentum_acceleration"]
        < 0
    ):

        momentum = "bearish"

    else:

        momentum = "neutral"

    print(
        f"Momentum: "
        f"{momentum}"
    )

    print(
        f"Pressure: "
        f"{f['pressure']}"
    )

    print(
        f"Range event: "
        f"{f['range_event']}"
    )

    print(
        f"Latest candle: "
        f"{f['latest_candle']}"
    )

    print()

    print(
        f"Swing-high state: "
        f"{f['swing_high_state']}"
    )

    print(
        f"Swing-low state: "
        f"{f['swing_low_state']}"
    )

    print(
        f"Structure regime: "
        f"{f['structure_regime']}"
    )

    print()

    print(
        "Recent candle sequence:"
    )

    print(
        " -> ".join(
            current["sequence"]
        )
    )

    print()

    display_features = [

        "return_5",
        "return_10",
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
        "momentum_acceleration",

        "recent_body_ratio",
        "recent_upper_wick",
        "recent_lower_wick"
    ]

    for key in display_features:

        print(
            f"{key:<28}: "
            f"{f[key]:.8f}"
        )


# ============================================================
# FINAL DIAGNOSTIC
# ============================================================

def final_diagnostic(
    results
):

    print()

    print("=" * 80)
    print(
        "MLAI v3.4.1 MARKET REPRESENTATION DIAGNOSTIC"
    )
    print("=" * 80)

    print()

    print(
        "The purpose of this experiment is NOT "
        "to maximize historical accuracy."
    )

    print(
        "The important question is whether market "
        "observations contain repeatable information "
        "that survives unseen chronological data."
    )

    print()

    for horizon, result in (
        results.items()
    ):

        wf = result[
            "walk_forward"
        ]

        baseline = result[
            "baseline"
        ]

        print(
            f"Horizon {horizon}: "
            f"{wf['accuracy'] * 100:.2f}% accuracy | "
            f"{wf['coverage'] * 100:.2f}% coverage | "
            f"baseline "
            f"{baseline['majority_percentage']:.2f}%"
        )

    print()

    print("-" * 80)
    print("IMPORTANT VALIDATION CHECK")
    print("-" * 80)

    total_predictions = sum(
        result[
            "walk_forward"
        ][
            "prediction_count"
        ]
        for result in results.values()
    )

    if total_predictions == 0:

        print(
            "WARNING: The validation engine still "
            "produced zero predictions."
        )

        print()

        print(
            "This indicates that no discovered "
            "calibration rule matched the validation "
            "state representation."
        )

    else:

        print(
            f"PASS: The validation engine produced "
            f"{total_predictions} chronological "
            f"out-of-sample predictions."
        )

        print()

        print(
            "Accuracy and coverage can now be "
            "interpreted as actual validation results."
        )

    print()

    print("-" * 80)
    print("RESEARCH INTERPRETATION")
    print("-" * 80)

    print()

    print(
        "1. Calibration rules are not validation evidence."
    )

    print(
        "2. Validation observations remain chronologically unseen."
    )

    print(
        "3. Rules are discovered from calibration data only."
    )

    print(
        "4. Validation states are matched against those rules."
    )

    print(
        "5. Coverage must be reported together with accuracy."
    )

    print(
        "6. High-confidence historical rules may still fail "
        "on unseen periods."
    )

    print(
        "7. Null/permutation testing is required before "
        "claiming predictive information."
    )

    print(
        "8. The permutation null now uses the same aggregate "
        "locked-OOS metric as the observed result."
    )

    print(
        "9. Numeric quantile boundaries are calculated once "
        "per calibration fold instead of repeatedly."
    )

    print(
        "10. This remains a statistical research layer, "
        "not a complete Market Language Brain."
    )

    print()

    print(
        "The next architectural stage should preserve this "
        "research layer while adding richer market-state "
        "representation, historical experience indexing, "
        "probability calibration, sequence modelling, and "
        "multi-timeframe context."
    )


# ============================================================
# SAVE RESEARCH OUTPUT
# ============================================================

def save_output(
    results,
    current,
    market_count
):

    output = {
        "version":
            "MLAI v3.4.1",

        "market_file":
            MARKET_FILE,

        "market_count":
            market_count,

        "results":
            results,

        "current_market":
            current
    }

    with open(
        OUTPUT_BIN,
        "wb"
    ) as f:

        pickle.dump(
            output,
            f
        )

    # --------------------------------------------------------
    # Markdown report
    # --------------------------------------------------------

    lines = []

    lines.append(
        "# MLAI v3.4.1 Market Representation Research"
    )

    lines.append("")

    lines.append(
        "Research-only chronological validation."
    )

    lines.append("")

    lines.append(
        "## Protection"
    )

    lines.append("")

    lines.append(
        f"- `{MARKET_FILE}`: READ ONLY"
    )

    lines.append(
        "- `mlai_v31.py`: NOT MODIFIED"
    )

    lines.append(
        "- Production files: NOT MODIFIED"
    )

    lines.append(
        "- Learning memory: NOT MODIFIED"
    )

    lines.append("")

    lines.append(
        "## Horizon Results"
    )

    lines.append("")

    lines.append(
        "| Horizon | Records | Predictions | "
        "Baseline | Accuracy | Coverage | "
        "Null Mean | Null Max | Permutation p |"
    )

    lines.append(
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    )

    for horizon, result in (
        results.items()
    ):

        wf = result[
            "walk_forward"
        ]

        baseline = result[
            "baseline"
        ]

        permutation = result[
            "permutation"
        ]

        lines.append(
            f"| {horizon} | "
            f"{result['records']} | "
            f"{wf['prediction_count']} | "
            f"{baseline['majority_percentage']:.2f}% | "
            f"{wf['accuracy'] * 100:.2f}% | "
            f"{wf['coverage'] * 100:.2f}% | "
            f"{permutation['mean_null'] * 100:.2f}% | "
            f"{permutation['max_null'] * 100:.2f}% | "
            f"{permutation['empirical_p_value']:.4f} |"
        )

    lines.append("")

    lines.append(
        "## Permutation Method"
    )

    lines.append("")

    lines.append(
        "Outcome labels were shuffled while market features "
        "remained unchanged."
    )

    lines.append("")

    lines.append(
        "The exact chronological walk-forward fold boundaries "
        "used by the observed locked out-of-sample result "
        "were reused for every permutation."
    )

    lines.append("")

    lines.append(
        "Null accuracy was aggregated across all validation "
        "folds rather than selecting the best individual fold."
    )

    lines.append("")

    lines.append(
        "Numeric feature quartile boundaries were calculated "
        "once per calibration fold and reused during "
        "discretization."
    )

    lines.append("")

    lines.append(
        "## Current Market"
    )

    lines.append("")

    lines.append(
        f"- Index: `{current['index']}`"
    )

    lines.append(
        f"- Close: `{current['close']}`"
    )

    lines.append(
        f"- Directional regime: "
        f"`{current['features']['directional_regime']}`"
    )

    lines.append(
        f"- Volatility regime: "
        f"`{current['features']['volatility_regime']}`"
    )

    lines.append(
        f"- Location: "
        f"`{current['features']['location_state']}`"
    )

    lines.append(
        f"- Structure: "
        f"`{current['features']['structure_regime']}`"
    )

    lines.append("")

    lines.append(
        "## Validation Engine"
    )

    lines.append("")

    lines.append(
        "The validation engine explicitly applies "
        "calibration rules to chronologically unseen "
        "validation states."
    )

    lines.append("")

    lines.append(
        "The permutation engine uses the same validation "
        "windows and aggregates predictions across all "
        "walk-forward folds."
    )

    lines.append("")

    with open(
        OUTPUT_REPORT,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(
            "\n".join(lines)
        )


# ============================================================
# MAIN
# ============================================================

def main():

    random.seed(
        RANDOM_SEED
    )

    protection_check()

    candles_raw = load_market_data()

    candles = audit_ohlc(
        candles_raw
    )

    if len(candles) < 200:

        raise ValueError(
            "Not enough valid candles for research."
        )

    print(
        "PASS: OHLC extracted."
    )

    print()

    print("=" * 80)

    print(
        "MLAI v3.4.1 MARKET LANGUAGE RESEARCH AUDIT"
    )

    print("=" * 80)

    print()

    print(
        "Optimized discretization: ENABLED"
    )

    print(
        "Corrected permutation test: ENABLED"
    )

    print(
        f"Permutation count: "
        f"{PERMUTATION_COUNT}"
    )

    print()

    features, candle_labels = (
        build_raw_features(
            candles
        )
    )

    results = {}

    for horizon in (
        4,
        8,
        16
    ):

        results[horizon] = run_horizon(
            candles,
            features,
            horizon,
            candle_labels
        )

    current = current_state(
        candles,
        features,
        candle_labels
    )

    print_current_market(
        current
    )

    final_diagnostic(
        results
    )

    save_output(
        results,
        current,
        len(candles)
    )

    print()

    print("=" * 80)
    print("RESEARCH AUDIT COMPLETE")
    print("=" * 80)

    print()

    print(
        f"Output binary : "
        f"{OUTPUT_BIN}"
    )

    print(
        f"Output report : "
        f"{OUTPUT_REPORT}"
    )

    print()

    print(
        "IMPORTANT:"
    )

    print(
        "The original market_data.bin was only READ."
    )

    print(
        "mlai_v31.py was not modified."
    )

    print(
        "No production files were modified."
    )

    print(
        "No learning memory was modified."
    )


if __name__ == "__main__":

    main()