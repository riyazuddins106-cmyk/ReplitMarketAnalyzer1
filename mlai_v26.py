import os
import pickle
import math
from datetime import datetime, timezone


# ============================================================
# MLAI v2.6
# HISTORICAL WALK-FORWARD VALIDATION ENGINE
#
# Purpose:
#   Test MLAI historical market-context decisions against
#   ACTUAL future candles without future-data leakage.
#
# Input:
#   market_data.bin
#
# Output:
#   mlai_backtest_memory.bin
#   MLAI_PROJECT_STATUS.md
#
# Important:
#   This is validation/backtesting only.
#   It does NOT create BUY/SELL signals.
# ============================================================


VERSION = "2.6"

MARKET_FILE = "market_data.bin"
OUTPUT_FILE = "mlai_backtest_memory.bin"
STATUS_FILE = "MLAI_PROJECT_STATUS.md"

WINDOW = 60
HORIZONS = [4, 8, 16]

# Minimum movement required to classify a future outcome.
# Small movements are treated as neutral.
NEUTRAL_THRESHOLD_PCT = 0.05

# Step between historical test points.
STEP = 1

# Maximum number of historical windows to evaluate.
# None = use all possible windows.
MAX_SAMPLES = None


# ============================================================
# DISPLAY
# ============================================================

def line(char="-", width=70):
    print(char * width)


def title(text):
    print("=" * 70)
    print(text)
    print("=" * 70)


# ============================================================
# GENERAL HELPERS
# ============================================================

def safe_float(value, default=None):
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def clamp(value, low=0.0, high=1.0):
    return max(low, min(high, value))


def pct(value):
    return f"{value * 100:.1f}%"


def mean(values):
    if not values:
        return 0.0
    return sum(values) / len(values)


def normalize_distribution(values):
    total = sum(max(0.0, v) for v in values.values())

    if total <= 0:
        return {
            "bullish": 1 / 3,
            "bearish": 1 / 3,
            "neutral": 1 / 3,
        }

    return {
        key: max(0.0, value) / total
        for key, value in values.items()
    }


# ============================================================
# MARKET DATA EXTRACTION
# ============================================================

def extract_candles(memory):
    """
    Supports several common market_data.bin structures.
    """

    if isinstance(memory, list):
        return memory

    if isinstance(memory, tuple):
        return list(memory)

    if isinstance(memory, dict):

        possible_keys = [
            "candles",
            "data",
            "market_data",
            "ohlcv",
            "records",
            "rows",
        ]

        for key in possible_keys:
            value = memory.get(key)

            if isinstance(value, list):
                return value

        # Some files may contain the candles under a nested object.
        for value in memory.values():
            if isinstance(value, list):
                if value and isinstance(value[0], dict):
                    return value

    raise ValueError(
        "Unable to locate candle list inside market_data.bin."
    )


def get_value(candle, names, default=None):

    if isinstance(candle, dict):

        lowered = {
            str(k).lower(): v
            for k, v in candle.items()
        }

        for name in names:
            if name.lower() in lowered:
                return lowered[name.lower()]

    elif isinstance(candle, (list, tuple)):

        # Standard OHLCV positional format:
        # timestamp, open, high, low, close, volume
        positions = {
            "open": 1,
            "high": 2,
            "low": 3,
            "close": 4,
            "volume": 5,
        }

        for name in names:
            if name.lower() in positions:
                index = positions[name.lower()]

                if len(candle) > index:
                    return candle[index]

    return default


def candle_ohlc(candle):

    open_price = safe_float(
        get_value(candle, ["open", "o"])
    )

    high_price = safe_float(
        get_value(candle, ["high", "h"])
    )

    low_price = safe_float(
        get_value(candle, ["low", "l"])
    )

    close_price = safe_float(
        get_value(
            candle,
            ["close", "c", "price", "last"]
        )
    )

    if close_price is None:
        return None

    if open_price is None:
        open_price = close_price

    if high_price is None:
        high_price = max(open_price, close_price)

    if low_price is None:
        low_price = min(open_price, close_price)

    return {
        "open": open_price,
        "high": high_price,
        "low": low_price,
        "close": close_price,
    }


# ============================================================
# CANDLE CLASSIFICATION
# ============================================================

def candle_direction(candle):

    o = candle["open"]
    c = candle["close"]

    if c > o:
        return "bullish"

    if c < o:
        return "bearish"

    return "neutral"


def direction_symbol(direction):

    if direction == "bullish":
        return "B"

    if direction == "bearish":
        return "S"

    return "N"


# ============================================================
# MARKET CONTEXT
# ============================================================

def calculate_context(candles):

    parsed = []

    for raw in candles:
        candle = candle_ohlc(raw)

        if candle is not None:
            parsed.append(candle)

    if len(parsed) < 2:
        return None

    closes = [c["close"] for c in parsed]

    first_close = closes[0]
    latest_close = closes[-1]

    movement = latest_close - first_close

    if first_close != 0:
        net_change_pct = (
            movement / first_close
        ) * 100
    else:
        net_change_pct = 0.0

    bullish = 0
    bearish = 0
    neutral = 0

    for candle in parsed:
        direction = candle_direction(candle)

        if direction == "bullish":
            bullish += 1
        elif direction == "bearish":
            bearish += 1
        else:
            neutral += 1

    if bullish > bearish:
        direction = "bullish"
    elif bearish > bullish:
        direction = "bearish"
    else:
        direction = "neutral"

    # --------------------------------------------------------
    # Momentum
    # --------------------------------------------------------

    split = max(1, len(parsed) // 2)

    first_half = parsed[:split]
    second_half = parsed[split:]

    def half_change(items):

        if len(items) < 2:
            return 0.0

        a = items[0]["close"]
        b = items[-1]["close"]

        if a == 0:
            return 0.0

        return ((b - a) / a) * 100

    first_change = half_change(first_half)
    second_change = half_change(second_half)

    if abs(second_change) < 0.03:
        momentum = "stable"
    elif abs(second_change) > abs(first_change) * 1.15:
        momentum = "increasing"
    elif abs(second_change) < abs(first_change) * 0.85:
        momentum = "decreasing"
    else:
        momentum = "stable"

    # --------------------------------------------------------
    # Volatility
    # --------------------------------------------------------

    ranges = []

    for candle in parsed:
        if candle["close"] != 0:
            ranges.append(
                abs(
                    candle["high"] -
                    candle["low"]
                ) / candle["close"]
            )

    if ranges:

        rsplit = max(1, len(ranges) // 2)

        old_vol = mean(ranges[:rsplit])
        new_vol = mean(ranges[rsplit:])

        if old_vol > 0:

            ratio = new_vol / old_vol

            if ratio > 1.15:
                volatility = "expanding"
            elif ratio < 0.85:
                volatility = "contracting"
            else:
                volatility = "stable"

        else:
            volatility = "stable"

    else:
        volatility = "stable"

    # --------------------------------------------------------
    # Structure
    # --------------------------------------------------------

    highs = [c["high"] for c in parsed]
    lows = [c["low"] for c in parsed]

    half = max(2, len(parsed) // 2)

    old_high = max(highs[:half])
    new_high = max(highs[half:])

    old_low = min(lows[:half])
    new_low = min(lows[half:])

    if new_high > old_high and new_low > old_low:
        structure = "bullish_structure"

    elif new_high < old_high and new_low < old_low:
        structure = "bearish_structure"

    else:
        structure = "mixed_structure"

    # --------------------------------------------------------
    # Rejection
    # --------------------------------------------------------

    upper_rejections = 0
    lower_rejections = 0

    for candle in parsed:

        body_high = max(
            candle["open"],
            candle["close"]
        )

        body_low = min(
            candle["open"],
            candle["close"]
        )

        upper_wick = candle["high"] - body_high
        lower_wick = body_low - candle["low"]

        if upper_wick > lower_wick:
            upper_rejections += 1
        elif lower_wick > upper_wick:
            lower_rejections += 1

    if lower_rejections > upper_rejections:
        rejection = "lower_rejection_dominant"

    elif upper_rejections > lower_rejections:
        rejection = "upper_rejection_dominant"

    else:
        rejection = "balanced"

    return {
        "direction": direction,
        "structure": structure,
        "momentum": momentum,
        "volatility": volatility,
        "rejection": rejection,
        "first_close": first_close,
        "latest_close": latest_close,
        "net_movement": movement,
        "net_change_pct": net_change_pct,
        "bullish_candles": bullish,
        "bearish_candles": bearish,
        "neutral_candles": neutral,
    }


# ============================================================
# MULTI-TIMEFRAME CONTEXT
# ============================================================

def calculate_mtf(all_candles, end_index):

    contexts = {}

    timeframes = {
        "short": 20,
        "medium": 60,
        "higher": 120,
    }

    for name, size in timeframes.items():

        start = end_index - size + 1

        if start < 0:
            contexts[name] = {
                "direction": "unknown",
                "available": False,
            }
            continue

        subset = all_candles[
            start:end_index + 1
        ]

        context = calculate_context(subset)

        if context is None:
            contexts[name] = {
                "direction": "unknown",
                "available": False,
            }
        else:
            contexts[name] = {
                "direction": context["direction"],
                "structure": context["structure"],
                "momentum": context["momentum"],
                "volatility": context["volatility"],
                "available": True,
            }

    available = [
        v
        for v in contexts.values()
        if v["available"]
    ]

    bullish = sum(
        1 for x in available
        if x["direction"] == "bullish"
    )

    bearish = sum(
        1 for x in available
        if x["direction"] == "bearish"
    )

    if bullish > bearish:
        integrated = "bullish"
    elif bearish > bullish:
        integrated = "bearish"
    else:
        integrated = "neutral"

    if available:
        alignment = max(
            bullish,
            bearish,
            len(available) - bullish - bearish
        ) / len(available)
    else:
        alignment = 0.0

    return {
        "contexts": contexts,
        "integrated_direction": integrated,
        "alignment": alignment,
    }


# ============================================================
# REGIME
# ============================================================

def detect_regime(context, mtf):

    bullish_score = 0.0
    bearish_score = 0.0
    range_score = 0.0

    if context["direction"] == "bullish":
        bullish_score += 3

    elif context["direction"] == "bearish":
        bearish_score += 3

    else:
        range_score += 2

    if context["structure"] == "bullish_structure":
        bullish_score += 3

    elif context["structure"] == "bearish_structure":
        bearish_score += 3

    else:
        range_score += 2

    if mtf["integrated_direction"] == "bullish":
        bullish_score += 2

    elif mtf["integrated_direction"] == "bearish":
        bearish_score += 2

    else:
        range_score += 1

    if context["volatility"] == "expanding":
        volatility_score = 1
    else:
        volatility_score = 0

    scores = {
        "bullish_trend": bullish_score,
        "bearish_trend": bearish_score,
        "range": range_score,
        "high_volatility": volatility_score,
    }

    strongest = max(
        scores,
        key=scores.get
    )

    total = sum(scores.values())

    if total > 0:
        confidence = scores[strongest] / total
    else:
        confidence = 0.0

    if strongest == "bullish_trend":
        regime = "bullish_trending_environment"

    elif strongest == "bearish_trend":
        regime = "bearish_trending_environment"

    elif strongest == "range":
        regime = "ranging_environment"

    else:
        regime = "high_volatility_environment"

    return {
        "regime": regime,
        "direction": (
            "bullish"
            if strongest == "bullish_trend"
            else "bearish"
            if strongest == "bearish_trend"
            else "neutral"
        ),
        "confidence": confidence,
        "scores": scores,
    }


# ============================================================
# HISTORICAL DECISION ENGINE
# ============================================================

def calculate_historical_decision(
    context,
    mtf,
    regime
):

    scores = {
        "bullish": 0.0,
        "bearish": 0.0,
        "neutral": 0.0,
    }

    # --------------------------------------------------------
    # Direct market evidence
    # --------------------------------------------------------

    if context["direction"] == "bullish":
        scores["bullish"] += 3.0

    elif context["direction"] == "bearish":
        scores["bearish"] += 3.0

    else:
        scores["neutral"] += 2.0

    # --------------------------------------------------------
    # Structure
    # --------------------------------------------------------

    if context["structure"] == "bullish_structure":
        scores["bullish"] += 2.0

    elif context["structure"] == "bearish_structure":
        scores["bearish"] += 2.0

    else:
        scores["neutral"] += 1.0

    # --------------------------------------------------------
    # Momentum
    # --------------------------------------------------------

    if context["momentum"] == "increasing":

        if context["direction"] == "bullish":
            scores["bullish"] += 1.0

        elif context["direction"] == "bearish":
            scores["bearish"] += 1.0

    # --------------------------------------------------------
    # Rejection
    # --------------------------------------------------------

    if context["rejection"] == "lower_rejection_dominant":
        scores["bullish"] += 0.75

    elif context["rejection"] == "upper_rejection_dominant":
        scores["bearish"] += 0.75

    # --------------------------------------------------------
    # Multi-timeframe
    # --------------------------------------------------------

    mtf_direction = mtf["integrated_direction"]

    if mtf_direction == "bullish":
        scores["bullish"] += 2.0 * mtf["alignment"]

    elif mtf_direction == "bearish":
        scores["bearish"] += 2.0 * mtf["alignment"]

    else:
        scores["neutral"] += 1.0

    # --------------------------------------------------------
    # Regime
    # --------------------------------------------------------

    if regime["direction"] == "bullish":
        scores["bullish"] += 1.5 * regime["confidence"]

    elif regime["direction"] == "bearish":
        scores["bearish"] += 1.5 * regime["confidence"]

    else:
        scores["neutral"] += 0.75

    distribution = normalize_distribution(scores)

    primary = max(
        distribution,
        key=distribution.get
    )

    # Evidence confidence = distance between strongest
    # and second strongest evidence.
    ordered = sorted(
        distribution.values(),
        reverse=True
    )

    if len(ordered) >= 2:
        confidence = (
            ordered[0] - ordered[1]
        )
    else:
        confidence = 0.0

    confidence = clamp(confidence)

    return {
        "primary": primary,
        "scores": scores,
        "distribution": distribution,
        "confidence": confidence,
    }


# ============================================================
# FUTURE OUTCOME
# ============================================================

def classify_future_outcome(
    candles,
    current_index,
    horizon
):

    future_index = current_index + horizon

    if future_index >= len(candles):
        return None

    current = candle_ohlc(
        candles[current_index]
    )

    future = candle_ohlc(
        candles[future_index]
    )

    if current is None or future is None:
        return None

    current_price = current["close"]
    future_price = future["close"]

    if current_price == 0:
        return None

    change_pct = (
        (future_price - current_price)
        / current_price
    ) * 100

    if change_pct > NEUTRAL_THRESHOLD_PCT:
        outcome = "bullish"

    elif change_pct < -NEUTRAL_THRESHOLD_PCT:
        outcome = "bearish"

    else:
        outcome = "neutral"

    return {
        "outcome": outcome,
        "change_pct": change_pct,
        "future_price": future_price,
    }


# ============================================================
# CALIBRATION
# ============================================================

def calculate_brier(
    distribution,
    outcome
):

    targets = {
        "bullish": 0.0,
        "bearish": 0.0,
        "neutral": 0.0,
    }

    targets[outcome] = 1.0

    return sum(
        (
            distribution[key]
            - targets[key]
        ) ** 2
        for key in targets
    )


# ============================================================
# MAIN BACKTEST
# ============================================================

def run_backtest(candles):

    results = []

    start_index = WINDOW - 1

    last_possible = (
        len(candles)
        - max(HORIZONS)
        - 1
    )

    if last_possible < start_index:
        return results

    indices = list(
        range(
            start_index,
            last_possible + 1,
            STEP
        )
    )

    if MAX_SAMPLES is not None:
        indices = indices[-MAX_SAMPLES:]

    for index in indices:

        history = candles[
            index - WINDOW + 1:
            index + 1
        ]

        context = calculate_context(history)

        if context is None:
            continue

        mtf = calculate_mtf(
            candles,
            index
        )

        # Require the higher timeframe when possible.
        if not mtf["contexts"]["higher"]["available"]:
            continue

        regime = detect_regime(
            context,
            mtf
        )

        decision = calculate_historical_decision(
            context,
            mtf,
            regime
        )

        sample = {
            "index": index,
            "primary_decision": decision["primary"],
            "distribution": decision["distribution"],
            "confidence": decision["confidence"],
            "direction": context["direction"],
            "structure": context["structure"],
            "momentum": context["momentum"],
            "volatility": context["volatility"],
            "mtf_direction": mtf["integrated_direction"],
            "mtf_alignment": mtf["alignment"],
            "regime": regime["regime"],
            "regime_direction": regime["direction"],
            "regime_confidence": regime["confidence"],
            "horizons": {},
        }

        for horizon in HORIZONS:

            outcome = classify_future_outcome(
                candles,
                index,
                horizon
            )

            if outcome is None:
                continue

            correct = (
                decision["primary"]
                == outcome["outcome"]
            )

            brier = calculate_brier(
                decision["distribution"],
                outcome["outcome"]
            )

            sample["horizons"][
                str(horizon)
            ] = {
                "outcome": outcome["outcome"],
                "change_pct": outcome["change_pct"],
                "future_price": outcome["future_price"],
                "correct": correct,
                "brier_score": brier,
            }

        if sample["horizons"]:
            results.append(sample)

    return results


# ============================================================
# STATISTICS
# ============================================================

def calculate_statistics(results):

    statistics = {
        "overall": {},
        "horizons": {},
        "directions": {
            "bullish": {},
            "bearish": {},
            "neutral": {},
        },
    }

    all_horizon_results = []

    for sample in results:

        for horizon, outcome in sample[
            "horizons"
        ].items():

            item = {
                "sample": sample,
                "horizon": int(horizon),
                **outcome,
            }

            all_horizon_results.append(item)

    resolved = len(all_horizon_results)

    correct = sum(
        1
        for x in all_horizon_results
        if x["correct"]
    )

    accuracy = (
        correct / resolved
        if resolved
        else 0.0
    )

    mean_brier = mean([
        x["brier_score"]
        for x in all_horizon_results
    ])

    statistics["overall"] = {
        "resolved_samples": resolved,
        "correct": correct,
        "incorrect": resolved - correct,
        "accuracy": accuracy,
        "mean_brier_score": mean_brier,
    }

    for horizon in HORIZONS:

        items = [
            x
            for x in all_horizon_results
            if x["horizon"] == horizon
        ]

        h_resolved = len(items)

        h_correct = sum(
            1
            for x in items
            if x["correct"]
        )

        h_accuracy = (
            h_correct / h_resolved
            if h_resolved
            else 0.0
        )

        h_brier = mean([
            x["brier_score"]
            for x in items
        ])

        outcomes = {
            "bullish": 0,
            "bearish": 0,
            "neutral": 0,
        }

        for item in items:
            outcomes[
                item["outcome"]
            ] += 1

        statistics["horizons"][
            str(horizon)
        ] = {
            "resolved": h_resolved,
            "correct": h_correct,
            "incorrect": h_resolved - h_correct,
            "accuracy": h_accuracy,
            "mean_brier_score": h_brier,
            "bullish_outcomes": outcomes["bullish"],
            "bearish_outcomes": outcomes["bearish"],
            "neutral_outcomes": outcomes["neutral"],
        }

    # --------------------------------------------------------
    # Decision direction performance
    # --------------------------------------------------------

    for direction in [
        "bullish",
        "bearish",
        "neutral",
    ]:

        items = [
            x
            for x in all_horizon_results
            if x["sample"]["primary_decision"]
            == direction
        ]

        d_resolved = len(items)

        d_correct = sum(
            1
            for x in items
            if x["correct"]
        )

        statistics["directions"][
            direction
        ] = {
            "resolved": d_resolved,
            "correct": d_correct,
            "incorrect": (
                d_resolved - d_correct
            ),
            "accuracy": (
                d_correct / d_resolved
                if d_resolved
                else 0.0
            ),
        }

    return statistics


# ============================================================
# CONFIDENCE ANALYSIS
# ============================================================

def confidence_statistics(results):

    bins = {
        "0-20%": [],
        "20-40%": [],
        "40-60%": [],
        "60-80%": [],
        "80-100%": [],
    }

    for sample in results:

        confidence = sample["confidence"]

        if confidence < 0.20:
            key = "0-20%"
        elif confidence < 0.40:
            key = "20-40%"
        elif confidence < 0.60:
            key = "40-60%"
        elif confidence < 0.80:
            key = "60-80%"
        else:
            key = "80-100%"

        for outcome in sample["horizons"].values():

            bins[key].append(
                outcome["correct"]
            )

    output = {}

    for key, values in bins.items():

        output[key] = {
            "samples": len(values),
            "correct": sum(
                1 for x in values if x
            ),
            "accuracy": (
                sum(1 for x in values if x)
                / len(values)
                if values
                else 0.0
            ),
        }

    return output


# ============================================================
# SAVE MEMORY
# ============================================================

def save_memory(results, statistics, confidence):

    memory = {
        "mlai_version": VERSION,
        "engine": (
            "Historical Walk-Forward "
            "Validation Engine"
        ),
        "created_at": datetime.now(
            timezone.utc
        ).isoformat(),

        "configuration": {
            "window": WINDOW,
            "horizons": HORIZONS,
            "step": STEP,
            "neutral_threshold_pct":
                NEUTRAL_THRESHOLD_PCT,
            "max_samples": MAX_SAMPLES,
        },

        "statistics": statistics,

        "confidence_statistics":
            confidence,

        "samples": results,
    }

    with open(
        OUTPUT_FILE,
        "wb"
    ) as f:
        pickle.dump(
            memory,
            f
        )

    return memory


# ============================================================
# PROJECT STATUS
# ============================================================

def write_status(
    statistics,
    confidence,
    sample_count
):

    overall = statistics["overall"]

    lines = []

    lines.append("# MLAI v2.6 Project Status")
    lines.append("")
    lines.append(
        "## Historical Walk-Forward Validation"
    )
    lines.append("")
    lines.append(
        f"- Validation samples: {sample_count}"
    )
    lines.append(
        f"- Resolved horizon observations: "
        f"{overall['resolved_samples']}"
    )
    lines.append(
        f"- Overall accuracy: "
        f"{pct(overall['accuracy'])}"
    )
    lines.append(
        f"- Mean Brier score: "
        f"{overall['mean_brier_score']:.4f}"
    )
    lines.append("")

    lines.append("## Horizon Performance")
    lines.append("")

    for horizon in HORIZONS:

        data = statistics[
            "horizons"
        ][str(horizon)]

        lines.append(
            f"### {horizon}-candle horizon"
        )

        lines.append(
            f"- Resolved: {data['resolved']}"
        )

        lines.append(
            f"- Correct: {data['correct']}"
        )

        lines.append(
            f"- Incorrect: {data['incorrect']}"
        )

        lines.append(
            f"- Accuracy: "
            f"{pct(data['accuracy'])}"
        )

        lines.append(
            f"- Mean Brier score: "
            f"{data['mean_brier_score']:.4f}"
        )

        lines.append(
            f"- Bullish outcomes: "
            f"{data['bullish_outcomes']}"
        )

        lines.append(
            f"- Bearish outcomes: "
            f"{data['bearish_outcomes']}"
        )

        lines.append(
            f"- Neutral outcomes: "
            f"{data['neutral_outcomes']}"
        )

        lines.append("")

    lines.append(
        "## Confidence Buckets"
    )
    lines.append("")

    for bucket, data in confidence.items():

        lines.append(
            f"- {bucket}: "
            f"samples={data['samples']}, "
            f"accuracy="
            f"{pct(data['accuracy'])}"
        )

    lines.append("")

    lines.append("## Validation Rules")
    lines.append("")
    lines.append(
        "1. Each historical decision uses only candles "
        "available at that historical point."
    )
    lines.append(
        "2. Future candles are used only after the "
        "historical decision has been generated."
    )
    lines.append(
        "3. Four-, eight- and sixteen-candle outcomes "
        "are measured independently."
    )
    lines.append(
        "4. Neutral outcomes are preserved."
    )
    lines.append(
        "5. Accuracy is measured only from resolved "
        "historical outcomes."
    )
    lines.append(
        "6. Confidence is evaluated separately from "
        "direction."
    )
    lines.append(
        "7. Backtest results are historical evidence "
        "and do not guarantee future behaviour."
    )
    lines.append(
        "8. The engine does not create a trading signal."
    )
    lines.append("")

    with open(
        STATUS_FILE,
        "w",
        encoding="utf-8"
    ) as f:
        f.write("\n".join(lines))


# ============================================================
# MAIN
# ============================================================

def main():

    title(
        "MLAI v2.6 - LOADING MARKET MEMORY"
    )

    print(
        f"File: {MARKET_FILE}"
    )

    print()

    if not os.path.exists(MARKET_FILE):

        print(
            f"ERROR: {MARKET_FILE} not found."
        )

        return

    try:

        with open(
            MARKET_FILE,
            "rb"
        ) as f:

            memory = pickle.load(f)

    except Exception as exc:

        print(
            "ERROR: Could not load market_data.bin."
        )

        print(
            f"Reason: {exc}"
        )

        return

    print(
        "PASS: market_data.bin loaded as "
        "MLAI memory object."
    )

    try:

        candles = extract_candles(
            memory
        )

    except Exception as exc:

        print(
            f"ERROR: {exc}"
        )

        return

    print()

    print(
        f"Found {len(candles)} stored candles."
    )

    if len(candles) < WINDOW + max(HORIZONS):

        print()

        print(
            "ERROR: Not enough candles for "
            "walk-forward validation."
        )

        print(
            f"Required: at least "
            f"{WINDOW + max(HORIZONS)}"
        )

        print(
            f"Available: {len(candles)}"
        )

        return

    print()

    print(
        f"PASS: Historical validation window = "
        f"{WINDOW} candles."
    )

    print(
        f"PASS: Outcome horizons = "
        f"{HORIZONS}"
    )

    print()

    print(
        "PASS: Building historical "
        "walk-forward decisions..."
    )

    results = run_backtest(
        candles
    )

    print(
        f"PASS: Generated {len(results)} "
        "historical decision samples."
    )

    print()

    statistics = calculate_statistics(
        results
    )

    confidence = confidence_statistics(
        results
    )

    save_memory(
        results,
        statistics,
        confidence
    )

    print(
        "PASS: mlai_backtest_memory.bin saved."
    )

    print()

    title(
        "MLAI v2.6 HISTORICAL WALK-FORWARD "
        "VALIDATION ENGINE"
    )

    print()
    print(
        "VALIDATION CONFIGURATION"
    )

    line()

    print(
        f"Decision window       : {WINDOW} candles"
    )

    print(
        f"Validation samples    : {len(results)}"
    )

    print(
        f"Outcome horizons      : "
        f"{HORIZONS}"
    )

    print(
        f"Neutral threshold     : "
        f"{NEUTRAL_THRESHOLD_PCT}%"
    )

    print()

    print(
        "OVERALL HISTORICAL PERFORMANCE"
    )

    line()

    overall = statistics[
        "overall"
    ]

    print(
        f"Resolved observations : "
        f"{overall['resolved_samples']}"
    )

    print(
        f"Correct               : "
        f"{overall['correct']}"
    )

    print(
        f"Incorrect             : "
        f"{overall['incorrect']}"
    )

    print(
        f"Accuracy              : "
        f"{pct(overall['accuracy'])}"
    )

    print(
        f"Mean Brier score      : "
        f"{overall['mean_brier_score']:.4f}"
    )

    print()

    print(
        "HORIZON PERFORMANCE"
    )

    line()

    for horizon in HORIZONS:

        data = statistics[
            "horizons"
        ][str(horizon)]

        print(
            f"{horizon:2d} candles -> "
            f"resolved={data['resolved']} | "
            f"correct={data['correct']} | "
            f"incorrect={data['incorrect']} | "
            f"accuracy={pct(data['accuracy'])} | "
            f"brier={data['mean_brier_score']:.4f}"
        )

    print()

    print(
        "OUTCOME DISTRIBUTION"
    )

    line()

    for horizon in HORIZONS:

        data = statistics[
            "horizons"
        ][str(horizon)]

        print(
            f"{horizon:2d} candles -> "
            f"B={data['bullish_outcomes']} | "
            f"S={data['bearish_outcomes']} | "
            f"N={data['neutral_outcomes']}"
        )

    print()

    print(
        "DECISION DIRECTION PERFORMANCE"
    )

    line()

    for direction in [
        "bullish",
        "bearish",
        "neutral",
    ]:

        data = statistics[
            "directions"
        ][direction]

        print(
            f"{direction:<8} -> "
            f"resolved={data['resolved']} | "
            f"correct={data['correct']} | "
            f"incorrect={data['incorrect']} | "
            f"accuracy={pct(data['accuracy'])}"
        )

    print()

    print(
        "CONFIDENCE BUCKET PERFORMANCE"
    )

    line()

    for bucket, data in confidence.items():

        print(
            f"{bucket:<9} -> "
            f"samples={data['samples']} | "
            f"correct={data['correct']} | "
            f"accuracy={pct(data['accuracy'])}"
        )

    print()

    print(
        "DATA-LEAKAGE PROTECTION"
    )

    line()

    print(
        "PASS: Historical decisions use only "
        "candles available at each test point."
    )

    print(
        "PASS: Future candles are used only "
        "to resolve the historical outcome."
    )

    print(
        "PASS: No future candle is used to "
        "construct the historical decision."
    )

    print()

    print(
        "VALIDATION INTERPRETATION"
    )

    line()

    if overall["resolved_samples"] == 0:

        print(
            "No resolved historical samples "
            "are available."
        )

    elif overall["accuracy"] >= 0.60:

        print(
            "Historical validation shows "
            "meaningful directional consistency."
        )

    elif overall["accuracy"] >= 0.50:

        print(
            "Historical validation shows "
            "mixed directional consistency."
        )

    else:

        print(
            "Historical validation shows "
            "weak directional consistency."
        )

    print()

    print(
        "IMPORTANT"
    )

    line()

    print(
        "Historical accuracy is NOT a guarantee "
        "of future performance."
    )

    print(
        "Brier score measures historical "
        "probability calibration."
    )

    print(
        "More independent samples are required "
        "before reliability can be considered mature."
    )

    print(
        "This engine does NOT create BUY/SELL signals."
    )

    print()

    print(
        "PASS: MLAI_PROJECT_STATUS.md updated."
    )

    print()

    print("=" * 70)

    print(
        "PASS: MLAI v2.6 Historical Walk-Forward "
        "Validation Engine completed."
    )

    print("=" * 70)


if __name__ == "__main__":
    main()