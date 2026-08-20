
import os
import pickle
import math
from collections import defaultdict

# ============================================================
# MLAI v3.3.5
# LOCKED REGIME EDGE VALIDATION
#
# PURPOSE
# -------
# Validate whether structures discovered in calibration data
# continue to work on completely unseen chronological data.
#
# PROTECTION
# ----------
# market_data.bin        READ ONLY
# mlai_v31.py            NOT MODIFIED
# learning memory        NOT MODIFIED
# production thresholds  NOT MODIFIED
#
# IMPORTANT:
# This program is diagnostic only.
# It does NOT create a trading signal.
# ============================================================

MARKET_FILE = "market_data.bin"

CURRENT_WINDOW = 60
HORIZONS = [4, 8, 16]

CLASSIFICATION_THRESHOLD = 0.0015

# Four chronological walk-forward folds.
# Each fold:
#   calibration = earlier data
#   validation  = immediately following unseen data
#
# The candidate structure is discovered ONLY from calibration.
# It is then frozen and evaluated on validation.
N_FOLDS = 4

# Percentage of the usable history allocated to each validation
# section.
VALIDATION_RATIO = 0.20

# A candidate regime/volatility combination must have at least
# this many calibration observations before it can be considered.
MIN_CALIBRATION_SAMPLES = 25

# Minimum validation observations required before reporting
# a validation edge as meaningful.
MIN_VALIDATION_SAMPLES = 20

# Candidate confidence levels.
CONFIDENCE_THRESHOLDS = [50, 55, 60, 65, 70, 75, 80, 85]

# Candidate structures we specifically want to investigate.
TARGET_STRUCTURES = [
    ("bullish", "stable"),
    ("bullish_bias", "stable"),
    ("bullish", "contracting"),
    ("bullish", "expanding"),
    ("bearish", "stable"),
    ("bearish_bias", "stable"),
]


# ============================================================
# PROTECTION / LOAD
# ============================================================

def protection_check():
    print("=" * 70)
    print("PROTECTION CHECK")
    print("=" * 70)

    print("market_data.bin: READ ONLY")

    if os.path.exists("mlai_v31.py"):
        print("mlai_v31.py: NOT MODIFIED")
    else:
        print("mlai_v31.py: NOT TOUCHED / FILE NOT REQUIRED")

    print("learning memory: NOT MODIFIED")
    print("production thresholds: NOT MODIFIED")
    print()


def load_market():
    with open(MARKET_FILE, "rb") as f:
        data = pickle.load(f)

    if isinstance(data, dict):
        print("Data type: dict")

        # Common MLAI storage possibilities.
        if "candles" in data:
            candles = data["candles"]
        elif "data" in data:
            candles = data["data"]
        elif "market_data" in data:
            candles = data["market_data"]
        else:
            # Try to locate a list of candle dictionaries.
            candles = None

            for value in data.values():
                if isinstance(value, list) and value:
                    if isinstance(value[0], dict):
                        sample = value[0]
                        keys = {str(k).lower() for k in sample.keys()}

                        if (
                            "close" in keys
                            or "c" in keys
                        ):
                            candles = value
                            break

            if candles is None:
                raise ValueError(
                    "Could not locate candle data inside market_data.bin"
                )

    elif isinstance(data, list):
        candles = data
    else:
        raise ValueError(
            "Unsupported market_data.bin format"
        )

    return candles


# ============================================================
# CANDLE HELPERS
# ============================================================

def get_value(candle, *names):
    if not isinstance(candle, dict):
        return None

    lower_map = {
        str(k).lower(): v
        for k, v in candle.items()
    }

    for name in names:
        if name.lower() in lower_map:
            return lower_map[name.lower()]

    return None


def extract_close(candle):
    value = get_value(
        candle,
        "close",
        "Close",
        "c",
    )

    if value is None:
        raise ValueError(
            "Candle does not contain a close price."
        )

    return float(value)


def extract_timestamp(candle, index):
    value = get_value(
        candle,
        "timestamp",
        "time",
        "datetime",
        "date",
        "t",
    )

    if value is None:
        return index

    return value


def safe_return(closes, start, end):
    if start < 0 or end >= len(closes):
        return None

    base = closes[start]

    if base == 0:
        return None

    return (closes[end] - base) / base


# ============================================================
# STRUCTURE FEATURES
# ============================================================

def calculate_features(closes, index):
    """
    Calculates the same general 60-candle structural concepts
    investigated by v3.3.4.

    The feature vector is deliberately simple and deterministic.
    """

    if index < CURRENT_WINDOW - 1:
        return None

    start = index - CURRENT_WINDOW + 1
    window = closes[start:index + 1]

    if len(window) < CURRENT_WINDOW:
        return None

    r15 = safe_return(
        closes,
        index - 14,
        index
    )

    r30 = safe_return(
        closes,
        index - 29,
        index
    )

    r60 = safe_return(
        closes,
        index - 59,
        index
    )

    if r15 is None or r30 is None or r60 is None:
        return None

    bullish = 0
    bearish = 0

    for j in range(start + 1, index + 1):
        if closes[j] > closes[j - 1]:
            bullish += 1
        elif closes[j] < closes[j - 1]:
            bearish += 1

    total_directional = bullish + bearish

    if total_directional == 0:
        bullish_ratio = 0.0
        bearish_ratio = 0.0
    else:
        bullish_ratio = bullish / total_directional
        bearish_ratio = bearish / total_directional

    directional_imbalance = (
        bullish_ratio - bearish_ratio
    )

    returns = []

    for j in range(start + 1, index + 1):
        if closes[j - 1] != 0:
            returns.append(
                (closes[j] - closes[j - 1])
                / closes[j - 1]
            )

    if not returns:
        volatility = 0.0
    else:
        mean_r = sum(returns) / len(returns)

        variance = sum(
            (x - mean_r) ** 2
            for x in returns
        ) / len(returns)

        volatility = math.sqrt(variance)

    # Compare recent volatility with the older portion
    # of the 60-candle window.
    recent_returns = returns[-20:]
    old_returns = returns[:40]

    def std(values):
        if not values:
            return 0.0

        mean_v = sum(values) / len(values)

        return math.sqrt(
            sum((x - mean_v) ** 2 for x in values)
            / len(values)
        )

    recent_vol = std(recent_returns)
    old_vol = std(old_returns)

    if old_vol == 0:
        volatility_ratio = 1.0
    else:
        volatility_ratio = (
            recent_vol / old_vol
        )

    minimum = min(window)
    maximum = max(window)

    if maximum == minimum:
        location_in_range = 0.5
    else:
        location_in_range = (
            closes[index] - minimum
        ) / (maximum - minimum)

    normalized_slope = r60

    # --------------------------------------------------------
    # Regime classification
    # --------------------------------------------------------

    if r60 > 0.004 and directional_imbalance > 0.05:
        directional_regime = "bullish"

    elif r60 > 0.001 and directional_imbalance > 0.02:
        directional_regime = "bullish_bias"

    elif r60 < -0.004 and directional_imbalance < -0.05:
        directional_regime = "bearish"

    elif r60 < -0.001 and directional_imbalance < -0.02:
        directional_regime = "bearish_bias"

    else:
        directional_regime = "neutral"

    if volatility_ratio > 1.20:
        volatility_regime = "expanding"

    elif volatility_ratio < 0.85:
        volatility_regime = "contracting"

    else:
        volatility_regime = "stable"

    return {
        "return_15": r15,
        "return_30": r30,
        "return_60": r60,
        "bullish_ratio": bullish_ratio,
        "bearish_ratio": bearish_ratio,
        "directional_imbalance": directional_imbalance,
        "volatility": volatility,
        "volatility_ratio": volatility_ratio,
        "location_in_range": location_in_range,
        "normalized_slope": normalized_slope,
        "directional_regime": directional_regime,
        "volatility_regime": volatility_regime,
    }


# ============================================================
# OUTCOME
# ============================================================

def classify_outcome(
    closes,
    index,
    horizon
):
    future_index = index + horizon

    if future_index >= len(closes):
        return None

    base = closes[index]

    if base == 0:
        return None

    future = closes[future_index]

    change = (
        future - base
    ) / base

    if change >= CLASSIFICATION_THRESHOLD:
        return "bullish"

    if change <= -CLASSIFICATION_THRESHOLD:
        return "bearish"

    return "neutral"


# ============================================================
# RECORD CREATION
# ============================================================

def build_records(closes, horizon):
    records = []

    last_index = (
        len(closes)
        - horizon
        - 1
    )

    for index in range(
        CURRENT_WINDOW - 1,
        last_index + 1
    ):
        features = calculate_features(
            closes,
            index
        )

        if features is None:
            continue

        outcome = classify_outcome(
            closes,
            index,
            horizon
        )

        if outcome is None:
            continue

        records.append({
            "index": index,
            "features": features,
            "outcome": outcome,
        })

    return records


# ============================================================
# STRUCTURE KEY
# ============================================================

def structure_key(record):
    f = record["features"]

    return (
        f["directional_regime"],
        f["volatility_regime"],
    )


# ============================================================
# DISCOVER RULES FROM CALIBRATION ONLY
# ============================================================

def discover_rules(calibration):
    groups = defaultdict(list)

    for record in calibration:
        groups[
            structure_key(record)
        ].append(record["outcome"])

    rules = {}

    for key, outcomes in groups.items():
        n = len(outcomes)

        if n < MIN_CALIBRATION_SAMPLES:
            continue

        bullish = outcomes.count("bullish")
        neutral = outcomes.count("neutral")
        bearish = outcomes.count("bearish")

        directional_total = (
            bullish + bearish
        )

        if directional_total == 0:
            continue

        if bullish > bearish:
            prediction = "BUY"
            directional_count = bullish
        elif bearish > bullish:
            prediction = "SELL"
            directional_count = bearish
        else:
            prediction = "NO TRADE"
            directional_count = 0

        confidence = (
            directional_count / n
        ) * 100

        # Only lock a directional rule.
        if prediction in ("BUY", "SELL"):
            rules[key] = {
                "prediction": prediction,
                "confidence": confidence,
                "samples": n,
                "bullish": bullish,
                "neutral": neutral,
                "bearish": bearish,
            }

    return rules


# ============================================================
# LOCKED VALIDATION
# ============================================================

def evaluate_locked_rule(
    validation,
    rule
):
    selected = []

    for record in validation:
        key = structure_key(record)

        if key not in rule:
            continue

        locked = rule[key]

        selected.append({
            "prediction": locked["prediction"],
            "confidence": locked["confidence"],
            "outcome": record["outcome"],
            "key": key,
        })

    if not selected:
        return None

    correct = 0
    buy_predictions = 0
    sell_predictions = 0

    buy_correct = 0
    sell_correct = 0

    for item in selected:
        prediction = item["prediction"]
        outcome = item["outcome"]

        if prediction == "BUY":
            buy_predictions += 1

            if outcome == "bullish":
                correct += 1
                buy_correct += 1

        elif prediction == "SELL":
            sell_predictions += 1

            if outcome == "bearish":
                correct += 1
                sell_correct += 1

    total = len(selected)

    directional_accuracy = (
        correct / total * 100
        if total
        else 0.0
    )

    buy_precision = (
        buy_correct / buy_predictions * 100
        if buy_predictions
        else 0.0
    )

    sell_precision = (
        sell_correct / sell_predictions * 100
        if sell_predictions
        else 0.0
    )

    return {
        "total": total,
        "correct": correct,
        "directional_accuracy":
            directional_accuracy,
        "coverage": total,
        "buy_predictions":
            buy_predictions,
        "sell_predictions":
            sell_predictions,
        "buy_precision":
            buy_precision,
        "sell_precision":
            sell_precision,
        "selected":
            selected,
    }


# ============================================================
# WALK-FORWARD FOLD CREATION
# ============================================================

def make_folds(records):
    n = len(records)

    folds = []

    validation_size = max(
        1,
        int(n * VALIDATION_RATIO)
    )

    # Leave enough history before every validation block.
    for fold in range(N_FOLDS):

        validation_end = (
            n - fold * validation_size
        )

        validation_start = (
            validation_end
            - validation_size
        )

        if validation_start <= 0:
            break

        calibration = records[
            :validation_start
        ]

        validation = records[
            validation_start:
            validation_end
        ]

        if (
            len(calibration)
            < MIN_CALIBRATION_SAMPLES
            or len(validation) == 0
        ):
            continue

        folds.append(
            (
                len(folds) + 1,
                calibration,
                validation
            )
        )

    folds.reverse()

    return folds


# ============================================================
# CONFIDENCE TEST
# ============================================================

def confidence_test(
    selected,
    thresholds
):
    results = []

    for threshold in thresholds:
        usable = [
            x for x in selected
            if x["confidence"] >= threshold
        ]

        if not usable:
            continue

        correct = sum(
            1
            for x in usable
            if (
                (x["prediction"] == "BUY"
                 and x["outcome"] == "bullish")
                or
                (x["prediction"] == "SELL"
                 and x["outcome"] == "bearish")
            )
        )

        buys = [
            x for x in usable
            if x["prediction"] == "BUY"
        ]

        sells = [
            x for x in usable
            if x["prediction"] == "SELL"
        ]

        buy_correct = sum(
            1
            for x in buys
            if x["outcome"] == "bullish"
        )

        sell_correct = sum(
            1
            for x in sells
            if x["outcome"] == "bearish"
        )

        accuracy = (
            correct / len(usable) * 100
        )

        coverage = (
            len(usable)
            / len(selected)
            * 100
        )

        buy_precision = (
            buy_correct / len(buys) * 100
            if buys
            else 0.0
        )

        sell_precision = (
            sell_correct / len(sells) * 100
            if sells
            else 0.0
        )

        results.append({
            "threshold": threshold,
            "accuracy": accuracy,
            "coverage": coverage,
            "buy_precision":
                buy_precision,
            "sell_precision":
                sell_precision,
            "count": len(usable),
        })

    return results


# ============================================================
# MAIN HORIZON TEST
# ============================================================

def run_horizon(
    closes,
    horizon
):
    print()
    print("=" * 70)
    print(
        f"HORIZON: {horizon} CANDLES"
    )
    print("=" * 70)

    records = build_records(
        closes,
        horizon
    )

    print(
        f"Historical records: "
        f"{len(records)}"
    )

    folds = make_folds(records)

    print(
        f"Walk-forward folds: "
        f"{len(folds)}"
    )

    print()

    all_validation_predictions = []

    fold_results = []

    for (
        fold_number,
        calibration,
        validation
    ) in folds:

        print("-" * 70)
        print(
            f"FOLD {fold_number}"
        )
        print("-" * 70)

        print(
            f"Calibration records: "
            f"{len(calibration)}"
        )

        print(
            f"Validation records:  "
            f"{len(validation)}"
        )

        print(
            "Rule discovery: CALIBRATION ONLY"
        )

        rules = discover_rules(
            calibration
        )

        print(
            f"Locked directional rules: "
            f"{len(rules)}"
        )

        print()

        for key in TARGET_STRUCTURES:
            if key in rules:
                r = rules[key]

                print(
                    f"LOCKED {key[0]} + "
                    f"{key[1]} -> "
                    f"{r['prediction']} "
                    f"({r['confidence']:.2f}% "
                    f"confidence, "
                    f"{r['samples']} samples)"
                )
            else:
                print(
                    f"LOCKED {key[0]} + "
                    f"{key[1]} -> "
                    f"NO DIRECTIONAL RULE"
                )

        print()

        evaluation = evaluate_locked_rule(
            validation,
            rules
        )

        if evaluation is None:
            print(
                "No locked rule matched "
                "the validation period."
            )
            continue

        selected = evaluation["selected"]

        all_validation_predictions.extend(
            selected
        )

        print(
            f"Validation matched records: "
            f"{evaluation['total']}"
        )

        print(
            f"Directional accuracy: "
            f"{evaluation['directional_accuracy']:.2f}%"
        )

        print(
            f"Coverage: "
            f"{evaluation['coverage'] / len(validation) * 100:.2f}%"
        )

        print(
            f"BUY precision: "
            f"{evaluation['buy_precision']:.2f}%"
        )

        print(
            f"SELL precision: "
            f"{evaluation['sell_precision']:.2f}%"
        )

        fold_results.append(
            evaluation
        )

    # --------------------------------------------------------
    # Aggregate locked validation result
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("AGGREGATED LOCKED OUT-OF-SAMPLE RESULT")
    print("=" * 70)

    if not all_validation_predictions:
        print(
            "No directional predictions "
            "survived into validation."
        )
        return

    total = len(
        all_validation_predictions
    )

    correct = sum(
        1
        for x in all_validation_predictions
        if (
            (x["prediction"] == "BUY"
             and x["outcome"] == "bullish")
            or
            (x["prediction"] == "SELL"
             and x["outcome"] == "bearish")
        )
    )

    buys = [
        x for x in all_validation_predictions
        if x["prediction"] == "BUY"
    ]

    sells = [
        x for x in all_validation_predictions
        if x["prediction"] == "SELL"
    ]

    buy_correct = sum(
        1
        for x in buys
        if x["outcome"] == "bullish"
    )

    sell_correct = sum(
        1
        for x in sells
        if x["outcome"] == "bearish"
    )

    accuracy = (
        correct / total * 100
    )

    buy_precision = (
        buy_correct / len(buys) * 100
        if buys
        else 0.0
    )

    sell_precision = (
        sell_correct / len(sells) * 100
        if sells
        else 0.0
    )

    print(
        f"Validation predictions: {total}"
    )

    print(
        f"Directional accuracy: "
        f"{accuracy:.2f}%"
    )

    print(
        f"BUY predictions: "
        f"{len(buys)}"
    )

    print(
        f"SELL predictions: "
        f"{len(sells)}"
    )

    print(
        f"BUY precision: "
        f"{buy_precision:.2f}%"
    )

    print(
        f"SELL precision: "
        f"{sell_precision:.2f}%"
    )

    print()

    # --------------------------------------------------------
    # Confidence test on LOCKED predictions
    # --------------------------------------------------------

    print(
        "=" * 70
    )
    print(
        "LOCKED CONFIDENCE TEST"
    )
    print(
        "=" * 70
    )

    confidence_results = confidence_test(
        all_validation_predictions,
        CONFIDENCE_THRESHOLDS
    )

    if confidence_results:
        print()
        print(
            "THRESHOLD    DIR ACC    COVERAGE"
            "    BUY PREC    SELL PREC    N"
        )
        print("-" * 70)

        for r in confidence_results:
            print(
                f"{r['threshold']:>8}%"
                f"{r['accuracy']:>11.2f}%"
                f"{r['coverage']:>12.2f}%"
                f"{r['buy_precision']:>13.2f}%"
                f"{r['sell_precision']:>13.2f}%"
                f"{r['count']:>7}"
            )

    # --------------------------------------------------------
    # Specific target structure validation
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print(
        "TARGET STRUCTURE OUT-OF-SAMPLE VALIDATION"
    )
    print("=" * 70)

    for target in TARGET_STRUCTURES:

        target_records = [
            x
            for x in all_validation_predictions
            if x["key"] == target
        ]

        if len(target_records) < MIN_VALIDATION_SAMPLES:
            print()
            print(
                f"{target[0]} + {target[1]}"
            )
            print(
                f"Validation samples: "
                f"{len(target_records)}"
            )
            print(
                "STATUS: INSUFFICIENT "
                "VALIDATION SAMPLE"
            )
            continue

        correct_target = sum(
            1
            for x in target_records
            if (
                (x["prediction"] == "BUY"
                 and x["outcome"] == "bullish")
                or
                (x["prediction"] == "SELL"
                 and x["outcome"] == "bearish")
            )
        )

        target_accuracy = (
            correct_target
            / len(target_records)
            * 100
        )

        target_buys = [
            x for x in target_records
            if x["prediction"] == "BUY"
        ]

        target_sells = [
            x for x in target_records
            if x["prediction"] == "SELL"
        ]

        target_buy_correct = sum(
            1
            for x in target_buys
            if x["outcome"] == "bullish"
        )

        target_sell_correct = sum(
            1
            for x in target_sells
            if x["outcome"] == "bearish"
        )

        target_buy_precision = (
            target_buy_correct
            / len(target_buys)
            * 100
            if target_buys
            else 0.0
        )

        target_sell_precision = (
            target_sell_correct
            / len(target_sells)
            * 100
            if target_sells
            else 0.0
        )

        print()
        print(
            f"{target[0]} + {target[1]}"
        )
        print(
            f"Validation samples: "
            f"{len(target_records)}"
        )
        print(
            f"Directional accuracy: "
            f"{target_accuracy:.2f}%"
        )
        print(
            f"BUY precision: "
            f"{target_buy_precision:.2f}%"
        )
        print(
            f"SELL precision: "
            f"{target_sell_precision:.2f}%"
        )

        # Strict validation verdict.
        if (
            target_accuracy >= 60.0
            and len(target_records)
                >= MIN_VALIDATION_SAMPLES
        ):
            print(
                "STATUS: POTENTIAL OUT-OF-SAMPLE EDGE"
            )
        else:
            print(
                "STATUS: EDGE NOT CONFIRMED"
            )


# ============================================================
# CURRENT MARKET STRUCTURE
# ============================================================

def print_current_structure(
    closes
):
    index = len(closes) - 1

    features = calculate_features(
        closes,
        index
    )

    print()
    print("=" * 70)
    print(
        "CURRENT 60-CANDLE MARKET STRUCTURE"
    )
    print("=" * 70)

    print(
        f"Latest index: {index}"
    )

    print(
        f"Latest price: "
        f"{closes[index]}"
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

    print()
    print("STRUCTURE FEATURES")

    display_features = [
        "return_15",
        "return_30",
        "return_60",
        "bullish_ratio",
        "bearish_ratio",
        "directional_imbalance",
        "volatility",
        "volatility_ratio",
        "location_in_range",
        "normalized_slope",
    ]

    for name in display_features:
        print(
            f"{name:<24}: "
            f"{features[name]:.6f}"
        )

    print()
    print(
        "IMPORTANT:"
    )
    print(
        "Current-market structure is "
        "diagnostic only."
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
        "MLAI v3.3.5 "
        "LOCKED REGIME EDGE VALIDATION"
    )
    print("=" * 70)

    print()
    print(
        "Purpose:"
    )
    print(
        "Determine whether structures discovered "
        "in earlier calibration data survive "
        "completely unseen chronological testing."
    )

    print()
    print(
        "Rules are discovered FIRST."
    )
    print(
        "Rules are then LOCKED."
    )
    print(
        "Validation data is NEVER used "
        "to discover or modify rules."
    )

    print()
    print(
        f"Market file: {MARKET_FILE}"
    )

    print(
        f"Current window: {CURRENT_WINDOW}"
    )

    print(
        f"Horizons: {HORIZONS}"
    )

    print(
        f"Classification threshold: "
        f"+/- {CLASSIFICATION_THRESHOLD * 100:.2f}%"
    )

    print(
        f"Walk-forward folds: {N_FOLDS}"
    )

    print(
        f"Minimum calibration samples: "
        f"{MIN_CALIBRATION_SAMPLES}"
    )

    print(
        f"Minimum validation samples: "
        f"{MIN_VALIDATION_SAMPLES}"
    )

    print()

    protection_check()

    candles = load_market()

    closes = [
        extract_close(candle)
        for candle in candles
    ]

    print(
        f"Total candles: {len(closes)}"
    )

    print(
        "PASS: market_data.bin loaded."
    )

    print(
        "PASS: Close prices extracted."
    )

    print(
        "PASS: market_data.bin will NOT "
        "be modified."
    )

    print(
        "PASS: Production MLAI will NOT "
        "be modified."
    )

    print()

    for horizon in HORIZONS:
        run_horizon(
            closes,
            horizon
        )

    print_current_structure(
        closes
    )

    print()
    print("=" * 70)
    print(
        "MLAI v3.3.5 FINAL VERDICT"
    )
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
        "The 88.89% v3.3.4 candidate edge "
        "must survive locked walk-forward "
        "validation before it can be considered "
        "a genuine structural edge."
    )

    print()
    print(
        "MLAI v3.3.5 COMPLETE"
    )


if __name__ == "__main__":
    main()
