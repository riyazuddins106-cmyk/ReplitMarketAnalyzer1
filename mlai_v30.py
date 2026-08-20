import os
import pickle
import math
from collections import Counter
from datetime import datetime, timezone


# ============================================================
# MLAI v3.1 CORRECTED ADAPTIVE HISTORICAL LEARNING ENGINE
# ============================================================

VERSION = "MLAI v3.1 CORRECTED ADAPTIVE HISTORICAL LEARNING ENGINE"

MARKET_FILE = "market_data.bin"
LEARNING_FILE = "mlai_learning_memory.bin"
STATUS_FILE = "MLAI_PROJECT_STATUS.md"

# Number of candles used to describe the current market context.
CURRENT_WINDOW = 60

# Independent future outcome horizons.
HORIZONS = [4, 8, 16]

# Minimum difference between bullish and bearish evidence
# before allowing a directional decision.
MIN_DIRECTIONAL_SEPARATION = 5.0

# Strong separation reference.
STRONG_DIRECTION_SEPARATION = 20.0

# Maximum historical influence.
MAX_HISTORICAL_INFLUENCE = 25.0

# Historical accuracy below this level is considered weak.
WEAK_ACCURACY_THRESHOLD = 50.0

# Maximum failure penalty.
MAX_FAILURE_PENALTY = 8.0

# Minimum records required before applying failure penalty.
MIN_FAILURE_SAMPLE = 20

# Historical context weighting.
EXACT_CONTEXT_WEIGHT = 1.50
SIMILAR_CONTEXT_WEIGHT = 1.00

# Horizon weighting.
# Shorter horizons receive slightly more weight because they
# describe nearer-term behavior.
HORIZON_WEIGHTS = {
    4: 1.00,
    8: 0.90,
    16: 0.80,
}

# Recency weighting.
# Older records still matter, but newer historical contexts
# receive somewhat more weight.
RECENCY_MIN_WEIGHT = 0.50
RECENCY_MAX_WEIGHT = 1.00


# ============================================================
# OUTPUT HELPERS
# ============================================================

def print_header(text):
    print()
    print("=" * 70)
    print(text)
    print("=" * 70)


def print_section(text):
    print()
    print(text)
    print("-" * 70)


# ============================================================
# SAFE NUMBER
# ============================================================

def safe_float(value, default=None):
    try:
        if value is None:
            return default

        if isinstance(value, bool):
            return default

        result = float(value)

        if not math.isfinite(result):
            return default

        return result

    except (TypeError, ValueError):
        return default


# ============================================================
# CANDLE NORMALIZATION
# ============================================================

def normalize_candle(raw):
    """
    Accept common candle formats.

    Supported names:
        timestamp / datetime / time / date / ts
        open / o
        high / h
        low / l
        close / c
        volume / v
    """

    if not isinstance(raw, dict):
        return None

    def find_value(names):
        for name in names:
            if name in raw:
                return raw[name]

        return None

    timestamp = find_value([
        "timestamp",
        "datetime",
        "date",
        "time",
        "ts",
    ])

    open_price = safe_float(
        find_value([
            "open",
            "o",
        ])
    )

    high_price = safe_float(
        find_value([
            "high",
            "h",
        ])
    )

    low_price = safe_float(
        find_value([
            "low",
            "l",
        ])
    )

    close_price = safe_float(
        find_value([
            "close",
            "c",
        ])
    )

    volume = safe_float(
        find_value([
            "volume",
            "v",
        ]),
        0.0
    )

    if (
        open_price is None
        or high_price is None
        or low_price is None
        or close_price is None
    ):
        return None

    if high_price < low_price:
        return None

    if high_price < max(
        open_price,
        close_price
    ):
        return None

    if low_price > min(
        open_price,
        close_price
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
# LOAD MARKET DATA
# ============================================================

def load_market_data():

    if not os.path.exists(MARKET_FILE):
        raise FileNotFoundError(
            f"{MARKET_FILE} was not found."
        )

    with open(
        MARKET_FILE,
        "rb"
    ) as f:

        data = pickle.load(f)

    candles = []

    # --------------------------------------------------------
    # Direct list
    # --------------------------------------------------------

    if isinstance(data, list):

        source = data

    # --------------------------------------------------------
    # Dictionary containers
    # --------------------------------------------------------

    elif isinstance(data, dict):

        source = None

        possible_keys = [
            "candles",
            "data",
            "records",
            "market_data",
            "ohlcv",
        ]

        for key in possible_keys:

            if (
                key in data
                and isinstance(data[key], list)
            ):
                source = data[key]
                break

        if source is None:

            values = list(
                data.values()
            )

            if (
                values
                and all(
                    isinstance(x, dict)
                    for x in values
                )
            ):
                source = values

    else:

        source = None

    if source is None:

        raise ValueError(
            "market_data.bin does not contain "
            "a supported candle list."
        )

    for raw in source:

        candle = normalize_candle(raw)

        if candle is not None:

            candles.append(candle)

    if not candles:

        raise ValueError(
            "No valid OHLC candles were found "
            "in market_data.bin."
        )

    return candles


# ============================================================
# BASIC MARKET CALCULATIONS
# ============================================================

def percentage_change(old, new):

    if old is None or new is None:
        return 0.0

    if old == 0:
        return 0.0

    return (
        (new - old)
        / abs(old)
        * 100.0
    )


def average(values):

    if not values:
        return 0.0

    return sum(values) / len(values)


# ============================================================
# MARKET CONTEXT
# ============================================================

def analyze_context(candles):

    if len(candles) < 10:

        raise ValueError(
            "At least 10 candles are required "
            "for analysis."
        )

    closes = [
        c["close"]
        for c in candles
    ]

    latest = closes[-1]

    # --------------------------------------------------------
    # Direction
    # --------------------------------------------------------

    short_start = closes[-10]

    net_change = percentage_change(
        short_start,
        latest
    )

    if net_change > 0.10:

        direction = "bullish"

    elif net_change < -0.10:

        direction = "bearish"

    else:

        direction = "neutral"

    # --------------------------------------------------------
    # Structure
    # --------------------------------------------------------

    split_index = max(
        5,
        len(candles) // 2
    )

    first_half = closes[:split_index]
    second_half = closes[split_index:]

    first_avg = average(first_half)
    second_avg = average(second_half)

    structure_change = percentage_change(
        first_avg,
        second_avg
    )

    if structure_change > 0.20:

        structure = "bullish_structure"

    elif structure_change < -0.20:

        structure = "bearish_structure"

    else:

        structure = "range_structure"

    # --------------------------------------------------------
    # Momentum
    # --------------------------------------------------------

    if len(closes) >= 12:

        previous_change = percentage_change(
            closes[-12],
            closes[-6]
        )

        recent_change = percentage_change(
            closes[-6],
            closes[-1]
        )

        momentum_difference = (
            recent_change
            - previous_change
        )

        if momentum_difference > 0.05:

            momentum = "increasing"

        elif momentum_difference < -0.05:

            momentum = "decreasing"

        else:

            momentum = "stable"

    else:

        momentum = "stable"

    # --------------------------------------------------------
    # Volatility
    # --------------------------------------------------------

    ranges = []

    for candle in candles:

        close = candle["close"]

        if close == 0:
            continue

        candle_range = (
            candle["high"]
            - candle["low"]
        ) / abs(close) * 100.0

        ranges.append(candle_range)

    if len(ranges) >= 10:

        older_volatility = average(
            ranges[:-5]
        )

        recent_volatility = average(
            ranges[-5:]
        )

        if older_volatility == 0:

            volatility = "stable"

        elif (
            recent_volatility
            > older_volatility * 1.15
        ):

            volatility = "expanding"

        elif (
            recent_volatility
            < older_volatility * 0.85
        ):

            volatility = "contracting"

        else:

            volatility = "stable"

    else:

        volatility = "stable"

    # --------------------------------------------------------
    # Rejection
    # --------------------------------------------------------

    upper_rejections = 0
    lower_rejections = 0

    for candle in candles[-20:]:

        body_high = max(
            candle["open"],
            candle["close"]
        )

        body_low = min(
            candle["open"],
            candle["close"]
        )

        upper_wick = (
            candle["high"]
            - body_high
        )

        lower_wick = (
            body_low
            - candle["low"]
        )

        if upper_wick > lower_wick * 1.25:

            upper_rejections += 1

        elif lower_wick > upper_wick * 1.25:

            lower_rejections += 1

    if (
        upper_rejections
        > lower_rejections + 2
    ):

        rejection = (
            "upper_rejection_dominant"
        )

    elif (
        lower_rejections
        > upper_rejections + 2
    ):

        rejection = (
            "lower_rejection_dominant"
        )

    else:

        rejection = (
            "balanced_rejection"
        )

    # ========================================================
    # DIRECT EVIDENCE
    # ========================================================

    bullish_score = 0.0
    bearish_score = 0.0
    neutral_score = 0.0

    # --------------------------------------------------------
    # Direction
    # --------------------------------------------------------

    if direction == "bullish":

        bullish_score += 30.0

    elif direction == "bearish":

        bearish_score += 30.0

    else:

        neutral_score += 30.0

    # --------------------------------------------------------
    # Structure
    # --------------------------------------------------------

    if structure == "bullish_structure":

        bullish_score += 25.0

    elif structure == "bearish_structure":

        bearish_score += 25.0

    else:

        neutral_score += 25.0

    # --------------------------------------------------------
    # Momentum
    # --------------------------------------------------------

    if momentum == "increasing":

        if direction == "bullish":

            bullish_score += 15.0

        elif direction == "bearish":

            bearish_score += 15.0

        else:

            neutral_score += 15.0

    elif momentum == "decreasing":

        if direction == "bullish":

            bearish_score += 8.0
            bullish_score += 4.0

        elif direction == "bearish":

            bullish_score += 8.0
            bearish_score += 4.0

        else:

            neutral_score += 12.0

    else:

        neutral_score += 8.0

    # --------------------------------------------------------
    # Volatility
    # --------------------------------------------------------

    if volatility == "expanding":

        if direction == "bullish":

            bullish_score += 8.0

        elif direction == "bearish":

            bearish_score += 8.0

        else:

            neutral_score += 8.0

    elif volatility == "contracting":

        neutral_score += 8.0

    else:

        neutral_score += 4.0

    # --------------------------------------------------------
    # Rejection
    # --------------------------------------------------------

    if rejection == "upper_rejection_dominant":

        bearish_score += 8.0

    elif rejection == "lower_rejection_dominant":

        bullish_score += 8.0

    else:

        neutral_score += 4.0

    # --------------------------------------------------------
    # Normalize direct evidence
    # --------------------------------------------------------

    total_score = (
        bullish_score
        + bearish_score
        + neutral_score
    )

    if total_score <= 0:

        direct_distribution = {
            "bullish": 33.3333,
            "bearish": 33.3333,
            "neutral": 33.3334,
        }

    else:

        direct_distribution = {

            "bullish": (
                bullish_score
                / total_score
                * 100.0
            ),

            "bearish": (
                bearish_score
                / total_score
                * 100.0
            ),

            "neutral": (
                neutral_score
                / total_score
                * 100.0
            ),
        }

    return {

        "direction": direction,

        "structure": structure,

        "momentum": momentum,

        "volatility": volatility,

        "rejection": rejection,

        "latest_price": latest,

        "net_change_percent": net_change,

        "direct_distribution":
            direct_distribution,
    }


# ============================================================
# HISTORICAL PREDICTION
# ============================================================

def predict_from_context(context):

    direct = context[
        "direct_distribution"
    ]

    bullish = direct["bullish"]
    bearish = direct["bearish"]

    separation = abs(
        bullish
        - bearish
    )

    if (
        separation
        < MIN_DIRECTIONAL_SEPARATION
    ):

        return "neutral"

    if bullish > bearish:

        return "bullish"

    return "bearish"


# ============================================================
# OUTCOME CLASSIFICATION
# ============================================================

def classify_outcome(movement):

    if movement > 0.02:

        return "bullish"

    if movement < -0.02:

        return "bearish"

    return "neutral"


# ============================================================
# WALK-FORWARD HISTORICAL RECORDS
# ============================================================

def build_historical_records(candles):

    """
    Strict walk-forward historical construction.

    For every decision point:

        1. Context contains only candles BEFORE decision.
        2. Prediction is generated from that context.
        3. Future candles are NEVER used by analyze_context().
        4. Future candles are used only to resolve outcomes.
        5. The latest CURRENT_WINDOW candles are excluded.
        6. Each horizon is independently stored.
    """

    records = []

    total_candles = len(candles)

    training_end = (
        total_candles
        - CURRENT_WINDOW
    )

    if training_end <= CURRENT_WINDOW:

        return records

    max_horizon = max(HORIZONS)

    # A decision point must have enough future candles
    # inside the historical/training region.
    last_decision_index = (
        training_end
        - max_horizon
        + 1
    )

    if last_decision_index <= CURRENT_WINDOW:

        return records

    for decision_index in range(
        CURRENT_WINDOW,
        last_decision_index
    ):

        # ----------------------------------------------------
        # IMPORTANT:
        # Only candles BEFORE decision_index are visible.
        # ----------------------------------------------------

        context_candles = candles[
            decision_index - CURRENT_WINDOW:
            decision_index
        ]

        context = analyze_context(
            context_candles
        )

        prediction = predict_from_context(
            context
        )

        current_close = candles[
            decision_index - 1
        ]["close"]

        for horizon in HORIZONS:

            outcome_index = (
                decision_index
                + horizon
                - 1
            )

            # Future outcome must remain inside
            # historical training region.
            if outcome_index >= training_end:

                continue

            future_close = candles[
                outcome_index
            ]["close"]

            movement = percentage_change(
                current_close,
                future_close
            )

            actual_direction = (
                classify_outcome(
                    movement
                )
            )

            correct = (
                prediction
                == actual_direction
            )

            records.append({

                "decision_index":
                    decision_index,

                "horizon":
                    horizon,

                "prediction":
                    prediction,

                "actual":
                    actual_direction,

                "correct":
                    bool(correct),

                "direction":
                    context["direction"],

                "structure":
                    context["structure"],

                "momentum":
                    context["momentum"],

                "volatility":
                    context["volatility"],

                "rejection":
                    context["rejection"],

                "latest_price":
                    current_close,

                "future_price":
                    future_close,

                "future_change_percent":
                    movement,
            })

    return records


# ============================================================
# STATISTICS
# ============================================================

def calculate_statistics(records):

    resolved = len(records)

    correct = sum(
        1
        for record in records
        if record["correct"]
    )

    incorrect = (
        resolved
        - correct
    )

    if resolved > 0:

        accuracy = (
            correct
            / resolved
            * 100.0
        )

    else:

        accuracy = 0.0

    return {

        "resolved":
            resolved,

        "correct":
            correct,

        "incorrect":
            incorrect,

        "accuracy":
            accuracy,
    }


# ============================================================
# CONTEXT MATCH SCORING
# ============================================================

def context_match_score(
    record,
    current_context
):
    """
    Returns:

        0.0 = no useful match
        1.0 = similar match
        1.5 = exact context match
    """

    structure_match = (
        record["structure"]
        == current_context["structure"]
    )

    momentum_match = (
        record["momentum"]
        == current_context["momentum"]
    )

    volatility_match = (
        record["volatility"]
        == current_context["volatility"]
    )

    rejection_match = (
        record["rejection"]
        == current_context["rejection"]
    )

    # Exact match.
    if (
        structure_match
        and momentum_match
        and volatility_match
        and rejection_match
    ):

        return EXACT_CONTEXT_WEIGHT

    # Similar context requires the three
    # main structural characteristics.
    if (
        structure_match
        and momentum_match
        and volatility_match
    ):

        return SIMILAR_CONTEXT_WEIGHT

    return 0.0


# ============================================================
# RECENCY WEIGHT
# ============================================================

def calculate_recency_weight(
    decision_index,
    oldest_index,
    newest_index
):

    if newest_index <= oldest_index:

        return RECENCY_MAX_WEIGHT

    position = (
        decision_index
        - oldest_index
    ) / (
        newest_index
        - oldest_index
    )

    position = max(
        0.0,
        min(
            position,
            1.0
        )
    )

    return (
        RECENCY_MIN_WEIGHT
        + (
            RECENCY_MAX_WEIGHT
            - RECENCY_MIN_WEIGHT
        )
        * position
    )


# ============================================================
# HISTORICAL EVIDENCE
# ============================================================

def calculate_historical_evidence(
    similar_records,
    current_context
):

    scores = {
        "bullish": 0.0,
        "bearish": 0.0,
        "neutral": 0.0,
    }

    if not similar_records:

        return {
            "bullish": 0.0,
            "bearish": 0.0,
            "neutral": 100.0,
            "weighted_records": 0.0,
        }

    oldest_index = min(
        record["decision_index"]
        for record in similar_records
    )

    newest_index = max(
        record["decision_index"]
        for record in similar_records
    )

    weighted_records = 0.0

    for record in similar_records:

        match_weight = context_match_score(
            record,
            current_context
        )

        if match_weight <= 0:
            continue

        horizon_weight = HORIZON_WEIGHTS.get(
            record["horizon"],
            1.0
        )

        recency_weight = (
            calculate_recency_weight(
                record["decision_index"],
                oldest_index,
                newest_index
            )
        )

        total_weight = (
            match_weight
            * horizon_weight
            * recency_weight
        )

        # IMPORTANT:
        #
        # Historical evidence follows the ACTUAL outcome,
        # not the old prediction.
        #
        # This means the learning engine learns what happened
        # after similar historical contexts.
        actual = record["actual"]

        if actual not in scores:
            continue

        scores[actual] += total_weight

        weighted_records += total_weight

    if weighted_records <= 0:

        return {
            "bullish": 0.0,
            "bearish": 0.0,
            "neutral": 100.0,
            "weighted_records": 0.0,
        }

    return {

        "bullish": (
            scores["bullish"]
            / weighted_records
            * 100.0
        ),

        "bearish": (
            scores["bearish"]
            / weighted_records
            * 100.0
        ),

        "neutral": (
            scores["neutral"]
            / weighted_records
            * 100.0
        ),

        "weighted_records":
            weighted_records,
    }


# ============================================================
# FAILURE LEARNING
# ============================================================

def calculate_failure_learning(
    similar_records
):

    matched_resolved_count = len(
        similar_records
    )

    matched_failure_count = sum(
        1
        for record in similar_records
        if not record["correct"]
    )

    if matched_resolved_count > 0:

        failure_rate = (
            matched_failure_count
            / matched_resolved_count
            * 100.0
        )

    else:

        failure_rate = 0.0

    return (
        matched_resolved_count,
        matched_failure_count,
        failure_rate,
    )


# ============================================================
# FAILURE PATTERNS
# ============================================================

def build_failure_patterns(
    similar_records
):

    pattern_failures = Counter()
    pattern_resolved = Counter()

    for record in similar_records:

        key = (

            record["prediction"],

            record["structure"],

            record["momentum"],

            record["volatility"],

            record["horizon"],
        )

        pattern_resolved[key] += 1

        if not record["correct"]:

            pattern_failures[key] += 1

    failure_patterns = []

    for key, failures in (
        pattern_failures.items()
    ):

        resolved = pattern_resolved[
            key
        ]

        if resolved <= 0:
            continue

        rate = (
            failures
            / resolved
            * 100.0
        )

        failure_patterns.append({

            "prediction":
                key[0],

            "structure":
                key[1],

            "momentum":
                key[2],

            "volatility":
                key[3],

            "horizon":
                key[4],

            "failures":
                failures,

            "resolved":
                resolved,

            "failure_rate":
                rate,
        })

    failure_patterns.sort(
        key=lambda item: (
            item["failures"],
            item["failure_rate"],
        ),
        reverse=True,
    )

    return failure_patterns


# ============================================================
# NORMALIZE DISTRIBUTION
# ============================================================

def normalize_distribution(
    bullish,
    bearish,
    neutral
):

    bullish = max(
        0.0,
        safe_float(
            bullish,
            0.0
        )
    )

    bearish = max(
        0.0,
        safe_float(
            bearish,
            0.0
        )
    )

    neutral = max(
        0.0,
        safe_float(
            neutral,
            0.0
        )
    )

    total = (
        bullish
        + bearish
        + neutral
    )

    if total <= 0:

        return (
            0.0,
            0.0,
            100.0
        )

    bullish = (
        bullish
        / total
        * 100.0
    )

    bearish = (
        bearish
        / total
        * 100.0
    )

    neutral = (
        neutral
        / total
        * 100.0
    )

    return (
        bullish,
        bearish,
        neutral
    )


# ============================================================
# MAIN
# ============================================================

try:

    print_header(
        "MLAI v3.1 CORRECTED - "
        "LOADING MARKET MEMORY"
    )

    print()
    print(
        f"File: {MARKET_FILE}"
    )

    candles = load_market_data()

    print()
    print(
        "PASS: market_data.bin loaded."
    )

    print()
    print(
        f"Found {len(candles)} stored candles."
    )

    minimum_required = (
        CURRENT_WINDOW
        + max(HORIZONS)
        + 1
    )

    if len(candles) < minimum_required:

        raise ValueError(
            "Not enough candles for MLAI analysis. "
            f"Need at least {minimum_required}."
        )

    # ========================================================
    # CURRENT WINDOW
    # ========================================================

    current_candles = candles[
        -CURRENT_WINDOW:
    ]

    print()
    print(
        f"PASS: Using latest {CURRENT_WINDOW} "
        "candles for current market analysis."
    )

    print()
    print(
        "Analysing latest candles..."
    )

    current_context = analyze_context(
        current_candles
    )

    # ========================================================
    # HISTORICAL LEARNING
    # ========================================================

    print()
    print(
        "PASS: Building strict walk-forward "
        "historical learning records..."
    )

    historical_records = (
        build_historical_records(
            candles
        )
    )

    print(
        f"PASS: Generated "
        f"{len(historical_records)} "
        "historical outcome records."
    )

    # ========================================================
    # GLOBAL HISTORICAL STATISTICS
    # ========================================================

    historical_stats = (
        calculate_statistics(
            historical_records
        )
    )

    historical_correct = (
        historical_stats["correct"]
    )

    historical_incorrect = (
        historical_stats["incorrect"]
    )

    historical_accuracy = (
        historical_stats["accuracy"]
    )

    # ========================================================
    # CURRENT CONTEXT MATCHING
    # ========================================================

    similar_records = []
    exact_records = []

    for record in historical_records:

        score = context_match_score(
            record,
            current_context
        )

        if score >= SIMILAR_CONTEXT_WEIGHT:

            similar_records.append(
                record
            )

        if score >= EXACT_CONTEXT_WEIGHT:

            exact_records.append(
                record
            )

    # ========================================================
    # HORIZON STATISTICS
    # ========================================================

    horizon_stats = {}

    for horizon in HORIZONS:

        subset = [
            record
            for record in historical_records
            if record["horizon"] == horizon
        ]

        horizon_stats[horizon] = (
            calculate_statistics(
                subset
            )
        )

    # ========================================================
    # DIRECTION STATISTICS
    # ========================================================

    direction_stats = {}

    for direction in [
        "bullish",
        "bearish",
        "neutral",
    ]:

        subset = [
            record
            for record in historical_records
            if record["prediction"] == direction
        ]

        direction_stats[direction] = (
            calculate_statistics(
                subset
            )
        )

    # ========================================================
    # MATCHED FAILURE LEARNING
    # ========================================================

    (
        matched_resolved_count,
        matched_failure_count,
        failure_rate,
    ) = calculate_failure_learning(
        similar_records
    )

    # ========================================================
    # FAILURE PATTERNS
    # ========================================================

    failure_patterns = (
        build_failure_patterns(
            similar_records
        )
    )

    # ========================================================
    # LEARNING STRENGTH
    # ========================================================

    sample_strength = min(
        len(similar_records)
        / 1000.0,
        1.0
    )

    accuracy_factor = max(
        0.0,
        min(
            historical_accuracy
            / 50.0,
            1.0
        )
    )

    learning_strength = (
        sample_strength * 0.50
        + accuracy_factor * 0.50
    ) * 100.0

    # ========================================================
    # HISTORICAL INFLUENCE
    # ========================================================

    historical_influence = (
        MAX_HISTORICAL_INFLUENCE
        * learning_strength
        / 100.0
    )

    # Weak historical accuracy reduces influence.
    if historical_accuracy < (
        WEAK_ACCURACY_THRESHOLD
    ):

        historical_influence *= (
            historical_accuracy
            / WEAK_ACCURACY_THRESHOLD
        )

    historical_influence = max(
        0.0,
        min(
            historical_influence,
            MAX_HISTORICAL_INFLUENCE
        )
    )

    # ========================================================
    # DIRECT CURRENT EVIDENCE
    # ========================================================

    direct = current_context[
        "direct_distribution"
    ]

    bullish_direct = direct[
        "bullish"
    ]

    bearish_direct = direct[
        "bearish"
    ]

    neutral_direct = direct[
        "neutral"
    ]

    # ========================================================
    # HISTORICAL EVIDENCE
    # ========================================================

    historical_evidence = (
        calculate_historical_evidence(
            similar_records,
            current_context
        )
    )

    historical_bullish = (
        historical_evidence["bullish"]
    )

    historical_bearish = (
        historical_evidence["bearish"]
    )

    historical_neutral = (
        historical_evidence["neutral"]
    )

    weighted_historical_records = (
        historical_evidence[
            "weighted_records"
        ]
    )

    # ========================================================
    # COMBINE CURRENT + HISTORICAL
    # ========================================================

    history_weight = (
        historical_influence
        / 100.0
    )

    current_weight = (
        1.0
        - history_weight
    )

    bullish_final = (
        bullish_direct
        * current_weight
        + historical_bullish
        * history_weight
    )

    bearish_final = (
        bearish_direct
        * current_weight
        + historical_bearish
        * history_weight
    )

    neutral_final = (
        neutral_direct
        * current_weight
        + historical_neutral
        * history_weight
    )

    # ========================================================
    # FAILURE PENALTY
    # ========================================================

    failure_penalty = 0.0

    if matched_resolved_count >= (
        MIN_FAILURE_SAMPLE
    ):

        sample_factor = min(
            matched_resolved_count
            / 200.0,
            1.0
        )

        failure_penalty = (
            failure_rate
            / 100.0
            * MAX_FAILURE_PENALTY
            * sample_factor
        )

        failure_penalty = min(
            failure_penalty,
            MAX_FAILURE_PENALTY
        )

    # --------------------------------------------------------
    # Apply penalty only to clearly directional evidence.
    # --------------------------------------------------------

    if (
        failure_penalty > 0
        and
        bullish_final
        > bearish_final
        + MIN_DIRECTIONAL_SEPARATION
    ):

        penalty = min(
            failure_penalty,
            5.0
        )

        bullish_final = max(
            0.0,
            bullish_final - penalty
        )

        neutral_final += penalty

    elif (
        failure_penalty > 0
        and
        bearish_final
        > bullish_final
        + MIN_DIRECTIONAL_SEPARATION
    ):

        penalty = min(
            failure_penalty,
            5.0
        )

        bearish_final = max(
            0.0,
            bearish_final - penalty
        )

        neutral_final += penalty

    # ========================================================
    # FINAL NORMALIZATION
    # ========================================================

    (
        bullish_final,
        bearish_final,
        neutral_final,
    ) = normalize_distribution(
        bullish_final,
        bearish_final,
        neutral_final
    )

    # ========================================================
    # FINAL DECISION
    # ========================================================

    directional_separation = abs(
        bullish_final
        - bearish_final
    )

    if (
        directional_separation
        < MIN_DIRECTIONAL_SEPARATION
    ):

        integrated_direction = (
            "neutral"
        )

        decision_reason = (
            "near_tied_directional_evidence"
        )

    elif bullish_final > bearish_final:

        integrated_direction = (
            "bullish"
        )

        decision_reason = (
            "bullish_directional_separation"
        )

    else:

        integrated_direction = (
            "bearish"
        )

        decision_reason = (
            "bearish_directional_separation"
        )

    # ========================================================
    # CONFIDENCE
    # ========================================================

    evidence_confidence = (
        directional_separation
    )

    # Weak historical performance cannot create
    # artificially strong confidence.
    if historical_accuracy < 50.0:

        evidence_confidence = min(
            evidence_confidence,
            45.0
        )

    # Insufficient historical evidence limits confidence.
    if len(similar_records) < 20:

        evidence_confidence = min(
            evidence_confidence,
            35.0
        )

    # Neutral result has deliberately low confidence.
    if integrated_direction == "neutral":

        evidence_confidence = min(
            evidence_confidence,
            5.0
        )

    evidence_confidence = max(
        0.0,
        min(
            evidence_confidence,
            100.0
        )
    )

    # ========================================================
    # CONFIDENCE LEVEL
    # ========================================================

    if integrated_direction == "neutral":

        confidence_level = (
            "very_low"
        )

    elif evidence_confidence < 10.0:

        confidence_level = (
            "very_low"
        )

    elif evidence_confidence < 25.0:

        confidence_level = (
            "low"
        )

    elif evidence_confidence < 50.0:

        confidence_level = (
            "moderate"
        )

    elif evidence_confidence < 70.0:

        confidence_level = (
            "strong"
        )

    else:

        confidence_level = (
            "very_strong"
        )

    # ========================================================
    # QUALITY MESSAGE
    # ========================================================

    if integrated_direction == "neutral":

        quality_message = (
            "WARNING: Final bullish and bearish "
            "evidence are near-tied."
        )

    elif directional_separation < (
        STRONG_DIRECTION_SEPARATION
    ):

        quality_message = (
            "WARNING: Directional separation is weak. "
            "Confidence remains limited."
        )

    else:

        quality_message = (
            "PASS: Final distribution has sufficient "
            "directional separation."
        )

    # ========================================================
    # FINAL DISTRIBUTION
    # ========================================================

    final_distribution = {

        "bullish":
            bullish_final,

        "bearish":
            bearish_final,

        "neutral":
            neutral_final,
    }

    # ========================================================
    # SAVE LEARNING MEMORY
    # ========================================================

    learning_memory = {

        "mlai_version":
            VERSION,

        "created_at":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "current_window":
            CURRENT_WINDOW,

        "horizons":
            HORIZONS,

        "current_context":
            current_context,

        "historical_records":
            historical_records,

        "historical_statistics": {

            "records":
                len(
                    historical_records
                ),

            "correct":
                historical_correct,

            "incorrect":
                historical_incorrect,

            "accuracy":
                historical_accuracy,
        },

        "horizon_statistics":
            horizon_stats,

        "direction_statistics":
            direction_stats,

        "similar_context_count":
            len(
                similar_records
            ),

        "exact_context_count":
            len(
                exact_records
            ),

        "learning_strength":
            learning_strength,

        "historical_influence":
            historical_influence,

        "historical_evidence": {

            "bullish":
                historical_bullish,

            "bearish":
                historical_bearish,

            "neutral":
                historical_neutral,

            "weighted_records":
                weighted_historical_records,
        },

        "failure_statistics": {

            "matched_records":
                matched_resolved_count,

            "historical_failures":
                matched_failure_count,

            "failure_rate":
                failure_rate,

            "failure_penalty":
                failure_penalty,
        },

        "failure_patterns":
            failure_patterns,

        "final_distribution":
            final_distribution,

        "directional_separation":
            directional_separation,

        "integrated_direction":
            integrated_direction,

        "decision_reason":
            decision_reason,

        "evidence_confidence":
            evidence_confidence,

        "confidence_level":
            confidence_level,

        "quality_message":
            quality_message,

        "methodology": {

            "historical_outcome_based":
                True,

            "exact_context_weight":
                EXACT_CONTEXT_WEIGHT,

            "similar_context_weight":
                SIMILAR_CONTEXT_WEIGHT,

            "horizon_weights":
                HORIZON_WEIGHTS,

            "recency_weighting":
                True,

            "current_window_excluded":
                True,

            "future_only_for_outcome_resolution":
                True,

            "separate_horizons":
                True,

            "aggregate_statistics_not_used_as_records":
                True,

            "historical_influence_capped":
                MAX_HISTORICAL_INFLUENCE,
        },

        "data_leakage_protection": {

            "current_window_excluded":
                True,

            "future_only_for_outcome_resolution":
                True,

            "separate_horizons":
                True,

            "aggregate_statistics_not_used_as_records":
                True,
        },
    }

    with open(
        LEARNING_FILE,
        "wb"
    ) as f:

        pickle.dump(
            learning_memory,
            f,
            protocol=pickle.HIGHEST_PROTOCOL
        )

    # ========================================================
    # DISPLAY
    # ========================================================

    print()
    print(
        f"PASS: {LEARNING_FILE} saved."
    )

    print_header(
        "MLAI v3.1 CORRECTED "
        "ADAPTIVE HISTORICAL LEARNING ENGINE"
    )

    # ========================================================
    # CURRENT MARKET CONTEXT
    # ========================================================

    print_section(
        "CURRENT MARKET CONTEXT"
    )

    print(
        f"Direction              : "
        f"{current_context['direction']}"
    )

    print(
        f"Structure              : "
        f"{current_context['structure']}"
    )

    print(
        f"Momentum               : "
        f"{current_context['momentum']}"
    )

    print(
        f"Volatility             : "
        f"{current_context['volatility']}"
    )

    print(
        f"Rejection              : "
        f"{current_context['rejection']}"
    )

    print(
        f"Latest price           : "
        f"{current_context['latest_price']:.4f}"
    )

    print(
        f"Net change %           : "
        f"{current_context['net_change_percent']:.3f}%"
    )

    # ========================================================
    # DIRECT EVIDENCE
    # ========================================================

    print_section(
        "CURRENT DIRECT EVIDENCE"
    )

    print(
        f"Bullish                : "
        f"{bullish_direct:.1f}%"
    )

    print(
        f"Bearish                : "
        f"{bearish_direct:.1f}%"
    )

    print(
        f"Neutral                : "
        f"{neutral_direct:.1f}%"
    )

    # ========================================================
    # HISTORICAL LEARNING
    # ========================================================

    print_section(
        "HISTORICAL LEARNING"
    )

    print(
        f"Historical records     : "
        f"{len(historical_records)}"
    )

    print(
        f"Historical correct     : "
        f"{historical_correct}"
    )

    print(
        f"Historical incorrect   : "
        f"{historical_incorrect}"
    )

    print(
        f"Historical accuracy    : "
        f"{historical_accuracy:.1f}%"
    )

    print(
        f"Similar context        : "
        f"{len(similar_records)}"
    )

    print(
        f"Exact context          : "
        f"{len(exact_records)}"
    )

    print(
        f"Weighted historical    : "
        f"{weighted_historical_records:.2f}"
    )

    print(
        f"Learning strength      : "
        f"{learning_strength:.1f}%"
    )

    print(
        f"Historical influence   : "
        f"{historical_influence:.1f}%"
    )

    # ========================================================
    # HISTORICAL EVIDENCE
    # ========================================================

    print_section(
        "MATCHED HISTORICAL OUTCOME EVIDENCE"
    )

    print(
        f"Bullish outcomes       : "
        f"{historical_bullish:.1f}%"
    )

    print(
        f"Bearish outcomes       : "
        f"{historical_bearish:.1f}%"
    )

    print(
        f"Neutral outcomes       : "
        f"{historical_neutral:.1f}%"
    )

    # ========================================================
    # HORIZON PERFORMANCE
    # ========================================================

    print_section(
        "HORIZON HISTORICAL PERFORMANCE"
    )

    for horizon in HORIZONS:

        stats = horizon_stats[
            horizon
        ]

        print(
            f"{horizon:2d} candles -> "
            f"resolved={stats['resolved']} | "
            f"correct={stats['correct']} | "
            f"incorrect={stats['incorrect']} | "
            f"accuracy={stats['accuracy']:.1f}%"
        )

    # ========================================================
    # DIRECTION PERFORMANCE
    # ========================================================

    print_section(
        "DIRECTION HISTORICAL PERFORMANCE"
    )

    for direction in [
        "bullish",
        "bearish",
        "neutral",
    ]:

        stats = direction_stats[
            direction
        ]

        print(
            f"{direction:<8} -> "
            f"resolved={stats['resolved']} | "
            f"correct={stats['correct']} | "
            f"incorrect={stats['incorrect']} | "
            f"accuracy={stats['accuracy']:.1f}%"
        )

    # ========================================================
    # FAILURE LEARNING
    # ========================================================

    print_section(
        "FAILURE LEARNING"
    )

    print(
        f"Matched failure records : "
        f"{matched_resolved_count}"
    )

    print(
        f"Historical failures     : "
        f"{matched_failure_count}"
    )

    print(
        f"Failure rate            : "
        f"{failure_rate:.1f}%"
    )

    print(
        f"Failure penalty         : "
        f"{failure_penalty:.2f} percentage points"
    )

    # ========================================================
    # FAILURE PATTERNS
    # ========================================================

    print()
    print(
        "TOP MATCHED FAILURE PATTERNS"
    )

    print("-" * 70)

    if not failure_patterns:

        print(
            "No matching historical "
            "failure patterns."
        )

    else:

        for index, pattern in enumerate(
            failure_patterns[:10],
            start=1
        ):

            print(
                f"{index:02d}. "
                f"prediction={pattern['prediction']} | "
                f"structure={pattern['structure']} | "
                f"momentum={pattern['momentum']} | "
                f"volatility={pattern['volatility']} | "
                f"horizon={pattern['horizon']} | "
                f"failures={pattern['failures']} | "
                f"resolved={pattern['resolved']} | "
                f"failure_rate="
                f"{pattern['failure_rate']:.1f}%"
            )

    # ========================================================
    # FINAL DISTRIBUTION
    # ========================================================

    print_section(
        "FINAL ADAPTIVE DISTRIBUTION"
    )

    print(
        f"Bullish                : "
        f"{bullish_final:.1f}%"
    )

    print(
        f"Bearish                : "
        f"{bearish_final:.1f}%"
    )

    print(
        f"Neutral                : "
        f"{neutral_final:.1f}%"
    )

    distribution_total = (
        bullish_final
        + bearish_final
        + neutral_final
    )

    if abs(
        distribution_total
        - 100.0
    ) < 0.1:

        print()
        print(
            "PASS: Final distribution "
            "normalizes to 100%."
        )

    else:

        print()
        print(
            "WARNING: Distribution normalization "
            f"error = {distribution_total:.4f}%"
        )

    # ========================================================
    # FINAL DECISION
    # ========================================================

    print_section(
        "ADAPTIVE LEARNING DECISION"
    )

    print(
        f"Integrated direction   : "
        f"{integrated_direction}"
    )

    print(
        f"Evidence confidence    : "
        f"{evidence_confidence:.1f}%"
    )

    print(
        f"Confidence level       : "
        f"{confidence_level}"
    )

    print(
        f"Directional separation : "
        f"{directional_separation:.1f} "
        f"percentage points"
    )

    print(
        f"Decision reason        : "
        f"{decision_reason}"
    )

    # ========================================================
    # QUALITY CHECK
    # ========================================================

    print_section(
        "LEARNING QUALITY CHECK"
    )

    if historical_accuracy < 50.0:

        print(
            "WARNING: Historical directional "
            "accuracy is below 50%."
        )

        print(
            "Historical learning influence "
            "has been automatically reduced."
        )

        print(
            "PASS: Confidence ceiling applied "
            "because historical accuracy is weak."
        )

    else:

        print(
            "PASS: Historical directional accuracy "
            "is at or above 50%."
        )

    if len(similar_records) < 20:

        print(
            "WARNING: Fewer than 20 matching "
            "historical records were found."
        )

        print(
            "PASS: Confidence is limited because "
            "matched historical evidence is small."
        )

    else:

        print(
            "PASS: Sufficient matched historical "
            "records are available for failure learning."
        )

    if integrated_direction == "neutral":

        print(
            "WARNING: Final directional evidence "
            "is near-tied."
        )

        print(
            "PASS: Near-tie protection forced "
            "the final decision to neutral."
        )

    elif directional_separation < (
        STRONG_DIRECTION_SEPARATION
    ):

        print(
            "WARNING: Final directional separation "
            "is weak."
        )

        print(
            "PASS: Confidence remains limited."
        )

    else:

        print(
            "PASS: Final directional separation "
            "has sufficient separation."
        )

    # ========================================================
    # DATA LEAKAGE PROTECTION
    # ========================================================

    print_section(
        "DATA-LEAKAGE PROTECTION"
    )

    print(
        "PASS: Historical decisions use only "
        "candles available before each "
        "decision point."
    )

    print(
        "PASS: Future candles are used only "
        "to resolve historical outcomes."
    )

    print(
        f"PASS: Latest {CURRENT_WINDOW}-candle "
        "current decision window is excluded "
        "from historical training."
    )

    print(
        "PASS: 4-, 8- and 16-candle outcomes "
        "are stored separately."
    )

    print(
        "PASS: Historical evidence uses "
        "actual resolved outcomes."
    )

    print(
        "PASS: Historical records receive "
        "context, horizon and recency weighting."
    )

    print(
        "PASS: Aggregate statistics are not "
        "used as individual historical records."
    )

    # ========================================================
    # CALIBRATION
    # ========================================================

    print_section(
        "IMPORTANT CALIBRATION"
    )

    print(
        "Historical accuracy is NOT a "
        "future prediction probability."
    )

    print(
        "Historical similarity does NOT "
        "guarantee future similarity."
    )

    print(
        "Failure frequency is NOT a future "
        "failure probability."
    )

    print(
        "Learning strength measures historical "
        "evidence maturity."
    )

    print(
        "Historical influence is capped at 25%."
    )

    print(
        "Weak historical accuracy cannot create "
        "strong historical influence."
    )

    print(
        "Historical evidence is based on "
        "resolved market outcomes."
    )

    print(
        "Exact contexts receive more weight "
        "than similar contexts."
    )

    print(
        "Recent historical contexts receive "
        "more weight than very old contexts."
    )

    print(
        "Near-tied bullish/bearish evidence "
        "is classified as neutral."
    )

    print(
        "Confidence represents evidence agreement, "
        "not future-price certainty."
    )

    print(
        "The engine does NOT create an automatic "
        "BUY/SELL trading signal."
    )

    # ========================================================
    # PROJECT STATUS
    # ========================================================

    status_text = f"""# MLAI v3.1 Project Status

## Version

{VERSION}

## Current Market

- Direction: {current_context["direction"]}
- Structure: {current_context["structure"]}
- Momentum: {current_context["momentum"]}
- Volatility: {current_context["volatility"]}
- Rejection: {current_context["rejection"]}
- Latest price: {current_context["latest_price"]:.4f}
- Net change: {current_context["net_change_percent"]:.3f}%

## Current Direct Evidence

- Bullish: {bullish_direct:.1f}%
- Bearish: {bearish_direct:.1f}%
- Neutral: {neutral_direct:.1f}%

## Historical Outcome Evidence

- Bullish outcomes: {historical_bullish:.1f}%
- Bearish outcomes: {historical_bearish:.1f}%
- Neutral outcomes: {historical_neutral:.1f}%
- Weighted historical records: {weighted_historical_records:.2f}

## Final Adaptive Distribution

- Bullish: {bullish_final:.1f}%
- Bearish: {bearish_final:.1f}%
- Neutral: {neutral_final:.1f}%

## Final Decision

- Integrated direction: {integrated_direction}
- Evidence confidence: {evidence_confidence:.1f}%
- Confidence level: {confidence_level}
- Directional separation: {directional_separation:.1f} percentage points
- Decision reason: {decision_reason}

## Historical Learning

- Historical records: {len(historical_records)}
- Correct: {historical_correct}
- Incorrect: {historical_incorrect}
- Historical accuracy: {historical_accuracy:.1f}%
- Similar contexts: {len(similar_records)}
- Exact contexts: {len(exact_records)}
- Learning strength: {learning_strength:.1f}%
- Historical influence: {historical_influence:.1f}%

## Failure Learning

- Matched records: {matched_resolved_count}
- Historical failures: {matched_failure_count}
- Failure rate: {failure_rate:.1f}%
- Failure penalty: {failure_penalty:.2f} points

## Data Leakage Protection

- Latest current window excluded from training.
- Future candles used only for historical outcome resolution.
- 4, 8 and 16 candle outcomes stored separately.
- Historical evidence uses actual resolved outcomes.
- Aggregate statistics are not treated as individual records.

## Historical Weighting

- Exact context weight: {EXACT_CONTEXT_WEIGHT}
- Similar context weight: {SIMILAR_CONTEXT_WEIGHT}
- Recency weighting: enabled
- Horizon weighting: enabled
- Historical influence cap: {MAX_HISTORICAL_INFLUENCE:.1f}%

## Decision Protection

- Near-tied directional evidence becomes neutral.
- Weak historical accuracy reduces historical influence.
- Historical influence is capped at 25%.
- Failure penalty is capped.
- Confidence is limited when matching evidence is small.
- Confidence is evidence agreement, not future certainty.

## Calibration

Historical accuracy is not future probability.

Historical similarity is not a guarantee of future similarity.

Failure frequency is not future failure probability.

Historical evidence describes previously observed outcomes.

The engine does not create an automatic BUY/SELL trading signal.

Updated: {datetime.now(timezone.utc).isoformat()}
"""

    with open(
        STATUS_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(status_text)

    print()
    print(
        f"PASS: {STATUS_FILE} updated."
    )

    print_header(
        "PASS: MLAI v3.1 CORRECTED "
        "Adaptive Historical Learning Engine completed."
    )


except FileNotFoundError as error:

    print()
    print(
        "ERROR: Required file was not found."
    )

    print(
        f"DETAIL: {error}"
    )


except (
    pickle.UnpicklingError,
    EOFError
) as error:

    print()

    print(
        "ERROR: market_data.bin could not be "
        "read as a valid pickle object."
    )

    print(
        f"DETAIL: {error}"
    )


except Exception as error:

    print()

    print("=" * 70)
    print(
        "ERROR: MLAI v3.1 execution failed."
    )
    print("=" * 70)

    print(
        f"{type(error).__name__}: {error}"
    )

    print()

    print(
        "The original market_data.bin has NOT "
        "been modified."
    )