import os
import pickle
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone


# ============================================================
# MLAI v2.9 FIXED
# ADAPTIVE FAILURE-ADJUSTED DECISION ENGINE
#
# FIX:
# - Robustly loads v2.7 mlai_error_memory.bin
# - Handles dictionaries/lists/nested memory structures
# - Recovers detailed records and failure patterns
# - Never silently converts valid memory to zero
# - Uses adaptive failure penalty based on:
#       failure rate
#       sample strength
#       pattern frequency
# - Current market evidence remains primary
# ============================================================

VERSION = "2.9-fixed"

MARKET_FILE = "market_data.bin"
ERROR_FILE = "mlai_error_memory.bin"
OUTPUT_FILE = "mlai_adaptive_failure_memory.bin"
STATUS_FILE = "MLAI_PROJECT_STATUS.md"

WINDOW = 60
HORIZONS = [4, 8, 16]

MAX_FAILURE_PENALTY = 25.0


# ============================================================
# BASIC HELPERS
# ============================================================

def pct(value):
    return f"{float(value):.1f}%"


def safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def clamp(value, low, high):
    return max(low, min(high, value))


def normalize_distribution(bullish, bearish, neutral):
    bullish = max(0.0, float(bullish))
    bearish = max(0.0, float(bearish))
    neutral = max(0.0, float(neutral))

    total = bullish + bearish + neutral

    if total <= 0:
        return 33.3333, 33.3333, 33.3333

    return (
        bullish / total * 100.0,
        bearish / total * 100.0,
        neutral / total * 100.0,
    )


def get_value(obj, *names, default=None):
    """
    Safely retrieve a field from either:
    - dictionary
    - object attribute
    """
    if isinstance(obj, dict):
        for name in names:
            if name in obj:
                return obj[name]

    for name in names:
        try:
            if hasattr(obj, name):
                return getattr(obj, name)
        except Exception:
            pass

    return default


# ============================================================
# MEMORY LOADING
# ============================================================

def load_pickle_file(filename):
    if not os.path.exists(filename):
        raise FileNotFoundError(
            f"Required memory file not found: {filename}"
        )

    with open(filename, "rb") as f:
        return pickle.load(f)


def recursively_find_values(obj, target_names, depth=0, max_depth=8):
    """
    Searches nested dictionaries/lists/objects for useful fields.

    This is intentionally tolerant because v2.7 memory structures
    may differ slightly between generated versions.
    """
    results = []

    if depth > max_depth:
        return results

    if isinstance(obj, dict):
        for key, value in obj.items():

            key_lower = str(key).lower()

            if key_lower in target_names:
                results.append(value)

            results.extend(
                recursively_find_values(
                    value,
                    target_names,
                    depth + 1,
                    max_depth
                )
            )

    elif isinstance(obj, (list, tuple)):
        for item in obj:
            results.extend(
                recursively_find_values(
                    item,
                    target_names,
                    depth + 1,
                    max_depth
                )
            )

    return results


# ============================================================
# MARKET MEMORY
# ============================================================

def extract_candles(memory):
    """
    Supports common v0.1 MLAI memory layouts.
    """

    possible_names = {
        "candles",
        "data",
        "market_data",
        "ohlcv",
        "bars",
        "records",
    }

    found = recursively_find_values(
        memory,
        possible_names
    )

    candidates = []

    for item in found:
        if isinstance(item, list) and len(item) > len(candidates):
            candidates = item

    # Direct dictionary case
    if isinstance(memory, dict):
        for name in possible_names:
            value = memory.get(name)

            if isinstance(value, list) and len(value) > len(candidates):
                candidates = value

    return candidates


def candle_ohlc(candle):
    """
    Supports dictionaries and list/tuple candle structures.
    """

    if isinstance(candle, dict):

        open_price = get_value(
            candle,
            "open",
            "Open",
            default=None
        )

        high_price = get_value(
            candle,
            "high",
            "High",
            default=None
        )

        low_price = get_value(
            candle,
            "low",
            "Low",
            default=None
        )

        close_price = get_value(
            candle,
            "close",
            "Close",
            default=None
        )

        if close_price is None:
            return None

        return (
            safe_float(open_price, safe_float(close_price)),
            safe_float(high_price, safe_float(close_price)),
            safe_float(low_price, safe_float(close_price)),
            safe_float(close_price),
        )

    if isinstance(candle, (list, tuple)):

        if len(candle) >= 5:
            try:
                return (
                    float(candle[1]),
                    float(candle[2]),
                    float(candle[3]),
                    float(candle[4]),
                )
            except Exception:
                pass

        if len(candle) >= 4:
            try:
                return (
                    float(candle[0]),
                    float(candle[1]),
                    float(candle[2]),
                    float(candle[3]),
                )
            except Exception:
                pass

    return None


# ============================================================
# CURRENT MARKET ANALYSIS
# ============================================================

def calculate_market_context(candles):

    if len(candles) < WINDOW:
        raise ValueError(
            f"Need at least {WINDOW} candles, found {len(candles)}."
        )

    selected = candles[-WINDOW:]

    parsed = []

    for candle in selected:
        values = candle_ohlc(candle)

        if values:
            parsed.append(values)

    if len(parsed) < WINDOW:
        raise ValueError(
            f"Could only parse {len(parsed)} of {WINDOW} candles."
        )

    opens = [x[0] for x in parsed]
    highs = [x[1] for x in parsed]
    lows = [x[2] for x in parsed]
    closes = [x[3] for x in parsed]

    first_close = closes[0]
    latest_close = closes[-1]

    net_change = latest_close - first_close

    if first_close != 0:
        net_change_pct = net_change / first_close * 100.0
    else:
        net_change_pct = 0.0

    bullish = 0
    bearish = 0
    neutral = 0

    for o, h, l, c in parsed:

        threshold = max(abs(o) * 0.00005, 0.00001)

        if c > o + threshold:
            bullish += 1
        elif c < o - threshold:
            bearish += 1
        else:
            neutral += 1

    # --------------------------------------------------------
    # Direction
    # --------------------------------------------------------

    if net_change_pct > 0.10:
        direction = "bullish"
    elif net_change_pct < -0.10:
        direction = "bearish"
    else:
        direction = "neutral"

    # --------------------------------------------------------
    # Structure
    # --------------------------------------------------------

    recent = closes[-20:]

    if len(recent) >= 10:

        first_half = recent[:10]
        second_half = recent[10:]

        first_high = max(first_half)
        second_high = max(second_half)

        first_low = min(first_half)
        second_low = min(second_half)

        if second_high > first_high and second_low > first_low:
            structure = "bullish_structure"

        elif second_high < first_high and second_low < first_low:
            structure = "bearish_structure"

        else:
            structure = "range_structure"

    else:
        structure = "range_structure"

    # --------------------------------------------------------
    # Momentum
    # --------------------------------------------------------

    if len(closes) >= 20:

        old_move = closes[-20] - closes[-10]
        new_move = closes[-10] - closes[-1]

        # Correct sign handling:
        recent_change = closes[-1] - closes[-10]
        previous_change = closes[-10] - closes[-20]

        if abs(recent_change) > abs(previous_change) * 1.10:
            momentum = "increasing"
        elif abs(recent_change) < abs(previous_change) * 0.90:
            momentum = "decreasing"
        else:
            momentum = "stable"
    else:
        momentum = "stable"

    # --------------------------------------------------------
    # Volatility
    # --------------------------------------------------------

    ranges = []

    for h, l in zip(highs, lows):
        ranges.append(abs(h - l))

    if len(ranges) >= 20:

        old_vol = sum(ranges[-20:-10]) / 10.0
        new_vol = sum(ranges[-10:]) / 10.0

        if new_vol > old_vol * 1.10:
            volatility = "expanding"
        elif new_vol < old_vol * 0.90:
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

    for o, h, l, c in parsed[-20:]:

        body_high = max(o, c)
        body_low = min(o, c)

        upper_wick = h - body_high
        lower_wick = body_low - l

        if upper_wick > lower_wick * 1.25:
            upper_rejections += 1

        elif lower_wick > upper_wick * 1.25:
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
        "net_change": net_change,
        "net_change_pct": net_change_pct,
        "bullish_candles": bullish,
        "bearish_candles": bearish,
        "neutral_candles": neutral,
        "candles": parsed,
    }


# ============================================================
# BASELINE EVIDENCE
# ============================================================

def calculate_baseline(context):

    bullish = 0.0
    bearish = 0.0
    neutral = 0.0

    # Candle participation
    total = (
        context["bullish_candles"]
        + context["bearish_candles"]
        + context["neutral_candles"]
    )

    if total:

        bullish += context["bullish_candles"] / total * 45.0
        bearish += context["bearish_candles"] / total * 45.0
        neutral += context["neutral_candles"] / total * 10.0

    # Net direction
    if context["net_change_pct"] > 0:
        bullish += 20.0
    elif context["net_change_pct"] < 0:
        bearish += 20.0
    else:
        neutral += 20.0

    # Structure
    if context["structure"] == "bullish_structure":
        bullish += 20.0

    elif context["structure"] == "bearish_structure":
        bearish += 20.0

    else:
        neutral += 10.0

    # Momentum
    if context["momentum"] == "increasing":

        if context["direction"] == "bullish":
            bullish += 10.0
        elif context["direction"] == "bearish":
            bearish += 10.0

    elif context["momentum"] == "decreasing":

        neutral += 5.0

    # Rejection
    if context["rejection"] == "lower_rejection_dominant":
        bullish += 5.0

    elif context["rejection"] == "upper_rejection_dominant":
        bearish += 5.0

    return normalize_distribution(
        bullish,
        bearish,
        neutral
    )


# ============================================================
# RECORD NORMALIZATION
# ============================================================

def normalize_failure_record(record):
    """
    Convert different possible v2.7 record layouts into one
    standard structure.
    """

    if not isinstance(record, dict):
        return None

    prediction = get_value(
        record,
        "prediction",
        "predicted_direction",
        "direction",
        "decision",
        "primary_direction",
        default=None
    )

    structure = get_value(
        record,
        "structure",
        "market_structure",
        default="unknown"
    )

    momentum = get_value(
        record,
        "momentum",
        default="unknown"
    )

    volatility = get_value(
        record,
        "volatility",
        default="unknown"
    )

    horizon = get_value(
        record,
        "horizon",
        "horizon_candles",
        "outcome_horizon",
        default=None
    )

    correct = get_value(
        record,
        "correct",
        "is_correct",
        "success",
        default=None
    )

    outcome = get_value(
        record,
        "outcome",
        "actual_direction",
        "actual",
        "resolved_direction",
        default=None
    )

    confidence = get_value(
        record,
        "confidence",
        "evidence_confidence",
        "decision_confidence",
        default=0.0
    )

    if prediction is None:
        return None

    prediction = str(prediction).lower().strip()

    if prediction in ("buy", "long", "up"):
        prediction = "bullish"

    elif prediction in ("sell", "short", "down"):
        prediction = "bearish"

    elif prediction not in ("bullish", "bearish", "neutral"):
        return None

    try:
        horizon = int(horizon)
    except Exception:
        return None

    if horizon not in HORIZONS:
        return None

    if correct is None and outcome is not None:

        actual = str(outcome).lower().strip()

        if actual in ("up", "bullish", "long"):
            actual = "bullish"
        elif actual in ("down", "bearish", "short"):
            actual = "bearish"
        elif actual in ("flat", "range"):
            actual = "neutral"

        correct = actual == prediction

    if correct is None:
        return None

    return {
        "prediction": prediction,
        "structure": str(structure),
        "momentum": str(momentum),
        "volatility": str(volatility),
        "horizon": horizon,
        "correct": bool(correct),
        "confidence": safe_float(confidence),
        "outcome": outcome,
    }


# ============================================================
# RECOVER V2.7 DETAILED RECORDS
# ============================================================

def recover_detailed_records(memory):

    candidate_names = {
        "detailed_records",
        "historical_records",
        "error_records",
        "failure_records",
        "records",
        "outcomes",
        "historical_outcomes",
        "decision_records",
        "validation_records",
        "samples",
    }

    candidates = recursively_find_values(
        memory,
        candidate_names
    )

    best_records = []

    for candidate in candidates:

        if not isinstance(candidate, (list, tuple)):
            continue

        normalized = []

        for item in candidate:

            record = normalize_failure_record(item)

            if record is not None:
                normalized.append(record)

        if len(normalized) > len(best_records):
            best_records = normalized

    return best_records


# ============================================================
# RECOVER FAILURE PATTERNS
# ============================================================

def recover_failure_patterns(memory):

    candidate_names = {
        "failure_patterns",
        "patterns",
        "errors",
        "failure_pattern_memory",
    }

    candidates = recursively_find_values(
        memory,
        candidate_names
    )

    best = []

    for candidate in candidates:

        if isinstance(candidate, dict):

            for key, value in candidate.items():

                if isinstance(value, dict):

                    item = dict(value)

                    if "pattern" not in item:
                        item["pattern"] = key

                    best.append(item)

                elif isinstance(value, (int, float)):

                    best.append({
                        "pattern": key,
                        "failures": int(value),
                    })

        elif isinstance(candidate, list):

            for item in candidate:

                if isinstance(item, dict):
                    best.append(item)

    return best


# ============================================================
# BUILD FAILURE PATTERNS FROM DETAILED RECORDS
# ============================================================

def build_failure_patterns(records):

    groups = defaultdict(
        lambda: {
            "samples": 0,
            "failures": 0,
            "correct": 0,
        }
    )

    for record in records:

        key = (
            record["prediction"],
            record["structure"],
            record["momentum"],
            record["volatility"],
            record["horizon"],
        )

        groups[key]["samples"] += 1

        if record["correct"]:
            groups[key]["correct"] += 1
        else:
            groups[key]["failures"] += 1

    patterns = []

    for key, stats in groups.items():

        prediction, structure, momentum, volatility, horizon = key

        samples = stats["samples"]
        failures = stats["failures"]

        failure_rate = (
            failures / samples
            if samples
            else 0.0
        )

        patterns.append({
            "prediction": prediction,
            "structure": structure,
            "momentum": momentum,
            "volatility": volatility,
            "horizon": horizon,
            "samples": samples,
            "failures": failures,
            "correct": stats["correct"],
            "failure_rate": failure_rate,
        })

    patterns.sort(
        key=lambda x: (
            x["failures"],
            x["failure_rate"],
            x["samples"],
        ),
        reverse=True
    )

    return patterns


# ============================================================
# MATCH CURRENT CONTEXT
# ============================================================

def match_failure_patterns(
    context,
    patterns
):

    matches = []

    for pattern in patterns:

        if pattern.get("prediction") != context["direction"]:
            continue

        if pattern.get("structure") != context["structure"]:
            continue

        if pattern.get("momentum") != context["momentum"]:
            continue

        if pattern.get("volatility") != context["volatility"]:
            continue

        matches.append(pattern)

    return matches


# ============================================================
# ADAPTIVE PENALTY
# ============================================================

def calculate_adaptive_penalty(matches):

    if not matches:
        return {
            "penalty": 0.0,
            "historical_failures": 0,
            "historical_samples": 0,
            "failure_rate": 0.0,
            "sample_strength": 0.0,
        }

    total_failures = sum(
        int(x.get("failures", 0))
        for x in matches
    )

    total_samples = sum(
        int(x.get("samples", 0))
        for x in matches
    )

    if total_samples <= 0:

        # Pattern-only fallback.
        total_failures = sum(
            int(x.get("failures", 0))
            for x in matches
        )

        total_samples = total_failures

    if total_samples <= 0:

        return {
            "penalty": 0.0,
            "historical_failures": 0,
            "historical_samples": 0,
            "failure_rate": 0.0,
            "sample_strength": 0.0,
        }

    failure_rate = total_failures / total_samples

    # --------------------------------------------------------
    # Sample strength
    #
    # 0 samples -> 0 influence
    # 25 samples -> 50%
    # 100 samples -> ~100%
    # --------------------------------------------------------

    sample_strength = min(
        1.0,
        math.sqrt(total_samples / 100.0)
    )

    # --------------------------------------------------------
    # Failure severity
    # --------------------------------------------------------

    failure_component = clamp(
        failure_rate,
        0.0,
        1.0
    )

    # --------------------------------------------------------
    # Number of matching patterns
    # More independent matching patterns = more caution.
    # --------------------------------------------------------

    pattern_factor = min(
        1.0,
        0.50 + len(matches) * 0.15
    )

    penalty = (
        MAX_FAILURE_PENALTY
        * failure_component
        * sample_strength
        * pattern_factor
    )

    penalty = clamp(
        penalty,
        0.0,
        MAX_FAILURE_PENALTY
    )

    return {
        "penalty": penalty,
        "historical_failures": total_failures,
        "historical_samples": total_samples,
        "failure_rate": failure_rate,
        "sample_strength": sample_strength,
    }


# ============================================================
# APPLY PENALTY
# ============================================================

def apply_failure_penalty(
    bullish,
    bearish,
    neutral,
    direction,
    penalty
):

    if direction == "bullish":

        reduction = min(
            bullish,
            penalty
        )

        bullish -= reduction
        neutral += reduction

    elif direction == "bearish":

        reduction = min(
            bearish,
            penalty
        )

        bearish -= reduction
        neutral += reduction

    return normalize_distribution(
        bullish,
        bearish,
        neutral
    )


# ============================================================
# CONFIDENCE
# ============================================================

def calculate_confidence(
    bullish,
    bearish,
    neutral
):

    values = [
        bullish,
        bearish,
        neutral,
    ]

    highest = max(values)

    second = sorted(
        values,
        reverse=True
    )[1]

    # Agreement based on separation.
    separation = max(
        0.0,
        highest - second
    )

    concentration = max(
        0.0,
        highest - 33.3333
    )

    confidence = (
        separation * 0.60
        + concentration * 0.40
    )

    confidence = clamp(
        confidence,
        0.0,
        100.0
    )

    if confidence >= 70:
        level = "high"

    elif confidence >= 45:
        level = "moderate"

    elif confidence >= 25:
        level = "low"

    else:
        level = "very_low"

    return confidence, level


# ============================================================
# PRIMARY DIRECTION
# ============================================================

def primary_direction(
    bullish,
    bearish,
    neutral
):

    values = {
        "bullish": bullish,
        "bearish": bearish,
        "neutral": neutral,
    }

    return max(
        values,
        key=values.get
    )


# ============================================================
# SAVE MEMORY
# ============================================================

def save_memory(memory):

    with open(
        OUTPUT_FILE,
        "wb"
    ) as f:

        pickle.dump(
            memory,
            f
        )


# ============================================================
# UPDATE PROJECT STATUS
# ============================================================

def update_status(
    context,
    patterns,
    records,
    result
):

    timestamp = datetime.now(
        timezone.utc
    ).isoformat()

    text = f"""
# MLAI v2.9 Fixed Status

Updated: {timestamp}

## Current Market

- Direction: {context["direction"]}
- Structure: {context["structure"]}
- Momentum: {context["momentum"]}
- Volatility: {context["volatility"]}
- Rejection: {context["rejection"]}
- Latest price: {context["latest_close"]:.4f}
- Net change: {context["net_change_pct"]:.3f}%

## Historical Failure Memory

- Detailed records: {len(records)}
- Failure patterns: {len(patterns)}
- Matched patterns: {len(result["matches"])}
- Historical failures: {result["historical_failures"]}
- Historical samples: {result["historical_samples"]}
- Failure rate: {result["failure_rate"] * 100:.2f}%
- Sample strength: {result["sample_strength"] * 100:.2f}%

## Adaptive Decision

- Baseline bullish: {result["baseline"][0]:.2f}%
- Baseline bearish: {result["baseline"][1]:.2f}%
- Baseline neutral: {result["baseline"][2]:.2f}%

- Adjusted bullish: {result["adjusted"][0]:.2f}%
- Adjusted bearish: {result["adjusted"][1]:.2f}%
- Adjusted neutral: {result["adjusted"][2]:.2f}%

- Primary direction: {result["direction"]}
- Evidence confidence: {result["confidence"]:.2f}%
- Confidence level: {result["confidence_level"]}
- Adaptive penalty: {result["penalty"]:.2f} percentage points

## Memory Integrity

v2.9 loaded and validated detailed historical failure memory.
Historical failure memory is contextual evidence and is not treated as a future probability.
"""

    with open(
        STATUS_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(text)


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 70)
    print("MLAI v2.9 FIXED - LOADING MARKET MEMORY")
    print("=" * 70)
    print()

    print(f"File: {MARKET_FILE}")
    print()

    # --------------------------------------------------------
    # Load market memory
    # --------------------------------------------------------

    try:

        market_memory = load_pickle_file(
            MARKET_FILE
        )

    except Exception as exc:

        print(
            f"ERROR: Could not load {MARKET_FILE}: {exc}"
        )
        return 1

    print(
        "PASS: market_data.bin loaded as MLAI memory object."
    )
    print()

    candles = extract_candles(
        market_memory
    )

    print(
        f"Found {len(candles)} stored candles."
    )
    print()

    if len(candles) < WINDOW:

        print(
            f"ERROR: Need at least {WINDOW} candles."
        )

        return 1

    print(
        f"PASS: Using latest {WINDOW} candles."
    )
    print()

    print(
        "Analysing latest candles..."
    )
    print()

    context = calculate_market_context(
        candles
    )

    # --------------------------------------------------------
    # Load v2.7 error memory
    # --------------------------------------------------------

    print(
        "PASS: Loading MLAI failure memory..."
    )

    try:

        error_memory = load_pickle_file(
            ERROR_FILE
        )

    except Exception as exc:

        print(
            f"ERROR: Could not load {ERROR_FILE}: {exc}"
        )
        return 1

    print(
        "PASS: Failure memory loaded."
    )
    print()

    # --------------------------------------------------------
    # Recover detailed records
    # --------------------------------------------------------

    detailed_records = recover_detailed_records(
        error_memory
    )

    # --------------------------------------------------------
    # Recover existing patterns
    # --------------------------------------------------------

    stored_patterns = recover_failure_patterns(
        error_memory
    )

    # --------------------------------------------------------
    # Prefer detailed records because these are the source
    # of truth for v2.7 failure learning.
    # --------------------------------------------------------

    if detailed_records:

        failure_patterns = build_failure_patterns(
            detailed_records
        )

        memory_source = (
            "v2.7 detailed historical records"
        )

    elif stored_patterns:

        failure_patterns = stored_patterns

        memory_source = (
            "v2.7 stored failure patterns"
        )

    else:

        failure_patterns = []

        memory_source = "no usable failure memory"

    print(
        f"Failure patterns available: "
        f"{len(failure_patterns)}"
    )

    print(
        f"Detailed historical records: "
        f"{len(detailed_records)}"
    )

    # --------------------------------------------------------
    # CRITICAL MEMORY INTEGRITY CHECK
    # --------------------------------------------------------

    if os.path.exists(ERROR_FILE):

        if len(detailed_records) == 0 and len(failure_patterns) == 0:

            print()
            print(
                "WARNING: mlai_error_memory.bin was found, "
                "but no usable detailed failure records or "
                "failure patterns could be recovered."
            )

            print(
                "WARNING: Adaptive failure learning will NOT "
                "pretend that historical data exists."
            )

    # --------------------------------------------------------
    # Baseline
    # --------------------------------------------------------

    baseline = calculate_baseline(
        context
    )

    # --------------------------------------------------------
    # Match failures
    # --------------------------------------------------------

    matches = match_failure_patterns(
        context,
        failure_patterns
    )

    stats = calculate_adaptive_penalty(
        matches
    )

    adjusted = apply_failure_penalty(
        baseline[0],
        baseline[1],
        baseline[2],
        context["direction"],
        stats["penalty"]
    )

    direction = primary_direction(
        adjusted[0],
        adjusted[1],
        adjusted[2]
    )

    confidence, confidence_level = calculate_confidence(
        adjusted[0],
        adjusted[1],
        adjusted[2]
    )

    # --------------------------------------------------------
    # Save unified memory
    # --------------------------------------------------------

    output_memory = {
        "version": VERSION,
        "created_at": datetime.now(
            timezone.utc
        ).isoformat(),

        "source": {
            "market_memory": MARKET_FILE,
            "failure_memory": ERROR_FILE,
            "engine": "MLAI v2.9 Fixed",
        },

        "market_context": {
            k: v
            for k, v in context.items()
            if k != "candles"
        },

        "memory_integrity": {
            "detailed_records": len(detailed_records),
            "failure_patterns": len(failure_patterns),
            "matched_patterns": len(matches),
            "memory_source": memory_source,
        },

        "baseline_distribution": {
            "bullish": baseline[0],
            "bearish": baseline[1],
            "neutral": baseline[2],
        },

        "adaptive_failure_analysis": {
            "historical_failures":
                stats["historical_failures"],

            "historical_samples":
                stats["historical_samples"],

            "failure_rate":
                stats["failure_rate"],

            "sample_strength":
                stats["sample_strength"],

            "adaptive_penalty":
                stats["penalty"],

            "matched_patterns":
                len(matches),
        },

        "decision": {
            "direction": direction,
            "bullish": adjusted[0],
            "bearish": adjusted[1],
            "neutral": adjusted[2],
            "confidence": confidence,
            "confidence_level": confidence_level,
        },

        "matched_failure_patterns": matches,
    }

    save_memory(
        output_memory
    )

    print()
    print(
        "PASS: mlai_adaptive_failure_memory.bin saved."
    )

    # ========================================================
    # OUTPUT
    # ========================================================

    print()
    print("=" * 70)
    print(
        "MLAI v2.9 FIXED ADAPTIVE FAILURE-ADJUSTED "
        "DECISION ENGINE"
    )
    print("=" * 70)

    print()
    print("CURRENT MARKET CONTEXT")
    print("-" * 70)

    print(
        f"Direction              : "
        f"{context['direction']}"
    )

    print(
        f"Structure              : "
        f"{context['structure']}"
    )

    print(
        f"Momentum               : "
        f"{context['momentum']}"
    )

    print(
        f"Volatility             : "
        f"{context['volatility']}"
    )

    print(
        f"Rejection              : "
        f"{context['rejection']}"
    )

    print(
        f"Latest price           : "
        f"{context['latest_close']:.4f}"
    )

    print(
        f"Net change %           : "
        f"{context['net_change_pct']:.3f}%"
    )

    print()
    print("BASELINE EVIDENCE")
    print("-" * 70)

    print(
        f"Bullish                : "
        f"{pct(baseline[0])}"
    )

    print(
        f"Bearish                : "
        f"{pct(baseline[1])}"
    )

    print(
        f"Neutral                : "
        f"{pct(baseline[2])}"
    )

    print()
    print("FAILURE MEMORY INTEGRITY")
    print("-" * 70)

    print(
        f"Memory source          : "
        f"{memory_source}"
    )

    print(
        f"Failure patterns       : "
        f"{len(failure_patterns)}"
    )

    print(
        f"Detailed records       : "
        f"{len(detailed_records)}"
    )

    print()
    print("ADAPTIVE FAILURE ANALYSIS")
    print("-" * 70)

    print(
        f"Available patterns     : "
        f"{len(failure_patterns)}"
    )

    print(
        f"Matched patterns       : "
        f"{len(matches)}"
    )

    print(
        f"Historical failures    : "
        f"{stats['historical_failures']}"
    )

    print(
        f"Historical samples     : "
        f"{stats['historical_samples']}"
    )

    print(
        f"Failure rate           : "
        f"{stats['failure_rate'] * 100:.1f}%"
    )

    print(
        f"Sample strength        : "
        f"{stats['sample_strength'] * 100:.1f}%"
    )

    print(
        f"Adaptive penalty       : "
        f"{stats['penalty']:.1f} percentage points"
    )

    if matches:
        failure_state = (
            "historical_failure_pattern_detected"
        )
    elif failure_patterns:
        failure_state = (
            "historical_failure_memory_available"
        )
    else:
        failure_state = (
            "no_usable_failure_memory"
        )

    print(
        f"Failure state          : "
        f"{failure_state}"
    )

    print()
    print("FAILURE-ADJUSTED DISTRIBUTION")
    print("-" * 70)

    print(
        f"Bullish                : "
        f"{pct(adjusted[0])}"
    )

    print(
        f"Bearish                : "
        f"{pct(adjusted[1])}"
    )

    print(
        f"Neutral                : "
        f"{pct(adjusted[2])}"
    )

    print()
    print("ADAPTIVE DECISION")
    print("-" * 70)

    print(
        f"Primary direction      : "
        f"{direction}"
    )

    print(
        f"Evidence confidence    : "
        f"{confidence:.1f}%"
    )

    print(
        f"Confidence level       : "
        f"{confidence_level}"
    )

    print()
    print("MATCHED FAILURE PATTERNS")
    print("-" * 70)

    if matches:

        display_matches = sorted(
            matches,
            key=lambda x: (
                int(x.get("failures", 0)),
                safe_float(
                    x.get("failure_rate", 0)
                ),
            ),
            reverse=True
        )

        for index, pattern in enumerate(
            display_matches[:15],
            start=1
        ):

            print(
                f"{index:02d}. "
                f"prediction={pattern.get('prediction')} | "
                f"structure={pattern.get('structure')} | "
                f"momentum={pattern.get('momentum')} | "
                f"volatility={pattern.get('volatility')} | "
                f"horizon={pattern.get('horizon')} | "
                f"samples={pattern.get('samples', 0)} | "
                f"failures={pattern.get('failures', 0)} | "
                f"failure_rate="
                f"{safe_float(pattern.get('failure_rate', 0)) * 100:.1f}%"
            )

    else:

        print(
            "No historical failure patterns matched "
            "the current context."
        )

    print()
    print("ADAPTIVE INTERPRETATION")
    print("-" * 70)

    if matches:

        print(
            "Historical failure patterns matching the "
            "current context were detected."
        )

        print(
            "MLAI reduced the influence of the dominant "
            "direction instead of automatically reversing it."
        )

        print(
            "The adaptive penalty is based on historical "
            "failure frequency and sample strength."
        )

    elif failure_patterns:

        print(
            "Historical failure memory is available, "
            "but no exact current-context failure pattern matched."
        )

        print(
            "No adaptive failure penalty was applied."
        )

    else:

        print(
            "No usable historical failure patterns were "
            "recovered from mlai_error_memory.bin."
        )

        print(
            "Adaptive failure learning was therefore "
            "disabled for this run."
        )

    print()
    print("IMPORTANT CALIBRATION")
    print("-" * 70)

    print(
        "Failure frequency is NOT a prediction probability."
    )

    print(
        "Historical failure patterns do NOT guarantee future failure."
    )

    print(
        "Sample size limits the influence of historical failure evidence."
    )

    print(
        "Adaptive penalties are capped so historical failures "
        "cannot completely override current market evidence."
    )

    print(
        "The engine does NOT create a BUY/SELL signal."
    )

    print()
    print("LEARNING PRINCIPLES")
    print("-" * 70)

    principles = [
        "v2.7 historical failure patterns are used as contextual evidence.",
        "Failure penalties are adaptive rather than fixed.",
        "Failure frequency and sample size both influence penalty strength.",
        "Small historical samples receive reduced influence.",
        "Multiple matching failures increase caution.",
        "Failure evidence reduces confidence rather than automatically reversing direction.",
        "Current market evidence remains the primary evidence layer.",
        "Future candles are never used for the current decision.",
        "Historical failure frequency is not future probability.",
        "Confidence represents evidence agreement rather than certainty.",
        "Historical evidence does not guarantee future market behaviour.",
        "The engine does not create an automatic trading signal.",
    ]

    for index, principle in enumerate(
        principles,
        start=1
    ):

        print(
            f"{index}. {principle}"
        )

    update_status(
        context,
        failure_patterns,
        detailed_records,
        {
            "baseline": baseline,
            "adjusted": adjusted,
            "matches": matches,
            "historical_failures":
                stats["historical_failures"],
            "historical_samples":
                stats["historical_samples"],
            "failure_rate":
                stats["failure_rate"],
            "sample_strength":
                stats["sample_strength"],
            "penalty":
                stats["penalty"],
            "direction":
                direction,
            "confidence":
                confidence,
            "confidence_level":
                confidence_level,
        }
    )

    print()
    print(
        "PASS: MLAI_PROJECT_STATUS.md updated."
    )

    print()
    print("=" * 70)
    print(
        "PASS: MLAI v2.9 FIXED Adaptive Failure-Adjusted "
        "Decision Engine completed."
    )
    print("=" * 70)

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )