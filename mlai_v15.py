import os
import pickle
import math
from datetime import datetime, timezone


# ============================================================
# MLAI v1.5
# ADAPTIVE LEARNING + PATTERN SCORING ENGINE
#
# Inputs:
#   market_data.bin
#   mlai_experience.bin
#   mlai_pattern_memory.bin
#   mlai_learning_memory.bin
#
# Output:
#   mlai_adaptive_memory.bin
#   MLAI_PROJECT_STATUS.md
#
# Principles:
#   Observe -> Resolve -> Learn -> Compare -> Adapt
#
# No automatic BUY/SELL signal is produced.
# ============================================================


MARKET_FILE = "market_data.bin"
EXPERIENCE_FILE = "mlai_experience.bin"
PATTERN_FILE = "mlai_pattern_memory.bin"
LEARNING_FILE = "mlai_learning_memory.bin"
ADAPTIVE_FILE = "mlai_adaptive_memory.bin"

WINDOW_SIZE = 60
PATTERN_SIZE = 6

HORIZONS = (4, 8, 16)

MIN_PATTERN_OCCURRENCES = 3


# ============================================================
# BASIC UTILITIES
# ============================================================

def safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def clamp(value, low=0.0, high=100.0):
    return max(low, min(high, value))


def pct(value):
    return f"{value:.1f}%"


def load_pickle(path):
    if not os.path.exists(path):
        return None

    with open(path, "rb") as f:
        return pickle.load(f)


def save_pickle(path, obj):
    with open(path, "wb") as f:
        pickle.dump(obj, f)


def now_iso():
    return datetime.now(timezone.utc).isoformat()


# ============================================================
# CANDLE NORMALIZATION
# ============================================================

def normalize_candle(candle):
    if isinstance(candle, dict):
        return {
            "open": safe_float(
                candle.get("open", candle.get("Open", 0))
            ),
            "high": safe_float(
                candle.get("high", candle.get("High", 0))
            ),
            "low": safe_float(
                candle.get("low", candle.get("Low", 0))
            ),
            "close": safe_float(
                candle.get("close", candle.get("Close", 0))
            ),
            "volume": safe_float(
                candle.get("volume", candle.get("Volume", 0))
            ),
        }

    if isinstance(candle, (list, tuple)) and len(candle) >= 4:
        return {
            "open": safe_float(candle[0]),
            "high": safe_float(candle[1]),
            "low": safe_float(candle[2]),
            "close": safe_float(candle[3]),
            "volume": safe_float(candle[4]) if len(candle) > 4 else 0.0,
        }

    return {
        "open": 0.0,
        "high": 0.0,
        "low": 0.0,
        "close": 0.0,
        "volume": 0.0,
    }


def extract_candles(memory):
    if isinstance(memory, list):
        return memory

    if isinstance(memory, dict):

        for key in (
            "candles",
            "data",
            "market_data",
            "records",
            "ohlcv",
        ):
            value = memory.get(key)

            if isinstance(value, list):
                return value

    return []


# ============================================================
# DIRECTION
# ============================================================

def candle_direction(candle):
    o = candle["open"]
    c = candle["close"]

    if c > o:
        return "B"

    if c < o:
        return "S"

    return "N"


def direction_name(code):
    if code == "B":
        return "bullish"

    if code == "S":
        return "bearish"

    return "neutral"


# ============================================================
# CURRENT MARKET CONTEXT
# ============================================================

def calculate_context(candles):
    bullish = 0
    bearish = 0
    neutral = 0

    upper_rejection = 0
    lower_rejection = 0

    body_sizes = []
    ranges = []

    for c in candles:

        o = c["open"]
        h = c["high"]
        l = c["low"]
        close = c["close"]

        if close > o:
            bullish += 1
        elif close < o:
            bearish += 1
        else:
            neutral += 1

        body = abs(close - o)
        total_range = max(h - l, 0.0)

        upper_wick = max(h - max(o, close), 0.0)
        lower_wick = max(min(o, close) - l, 0.0)

        body_sizes.append(body)
        ranges.append(total_range)

        if upper_wick > body:
            upper_rejection += 1

        if lower_wick > body:
            lower_rejection += 1

    first_close = candles[0]["close"]
    latest_close = candles[-1]["close"]

    movement = latest_close - first_close

    if first_close != 0:
        change_pct = (movement / first_close) * 100
    else:
        change_pct = 0.0

    if bullish > bearish:
        direction = "bullish"
    elif bearish > bullish:
        direction = "bearish"
    else:
        direction = "neutral"

    if len(body_sizes) >= 20:
        recent_body = sum(body_sizes[-10:]) / 10
        previous_body = sum(body_sizes[-20:-10]) / 10

        if recent_body > previous_body * 1.10:
            momentum = "increasing"
        elif recent_body < previous_body * 0.90:
            momentum = "decreasing"
        else:
            momentum = "stable"
    else:
        momentum = "unknown"

    if len(ranges) >= 20:
        recent_range = sum(ranges[-10:]) / 10
        previous_range = sum(ranges[-20:-10]) / 10

        if recent_range > previous_range * 1.10:
            volatility = "expanding"
        elif recent_range < previous_range * 0.90:
            volatility = "contracting"
        else:
            volatility = "stable"
    else:
        volatility = "unknown"

    if lower_rejection > upper_rejection:
        rejection = "lower_rejection_dominant"
    elif upper_rejection > lower_rejection:
        rejection = "upper_rejection_dominant"
    else:
        rejection = "balanced"

    return {
        "bullish_candles": bullish,
        "bearish_candles": bearish,
        "neutral_candles": neutral,
        "direction": direction,
        "first_close": first_close,
        "latest_close": latest_close,
        "movement": movement,
        "change_pct": change_pct,
        "momentum": momentum,
        "volatility": volatility,
        "upper_rejection": upper_rejection,
        "lower_rejection": lower_rejection,
        "rejection": rejection,
    }


# ============================================================
# STRUCTURE
# ============================================================

def calculate_structure(candles):
    if len(candles) < 5:
        return {
            "structure": "insufficient_data",
            "swing_highs": 0,
            "swing_lows": 0,
            "higher_highs": 0,
            "lower_highs": 0,
            "higher_lows": 0,
            "lower_lows": 0,
            "latest_swing_high": None,
            "latest_swing_low": None,
        }

    highs = []
    lows = []

    for i in range(2, len(candles) - 2):

        h = candles[i]["high"]
        l = candles[i]["low"]

        if (
            h >= candles[i - 1]["high"]
            and h >= candles[i - 2]["high"]
            and h >= candles[i + 1]["high"]
            and h >= candles[i + 2]["high"]
        ):
            highs.append(h)

        if (
            l <= candles[i - 1]["low"]
            and l <= candles[i - 2]["low"]
            and l <= candles[i + 1]["low"]
            and l <= candles[i + 2]["low"]
        ):
            lows.append(l)

    higher_highs = 0
    lower_highs = 0

    for i in range(1, len(highs)):
        if highs[i] > highs[i - 1]:
            higher_highs += 1
        elif highs[i] < highs[i - 1]:
            lower_highs += 1

    higher_lows = 0
    lower_lows = 0

    for i in range(1, len(lows)):
        if lows[i] > lows[i - 1]:
            higher_lows += 1
        elif lows[i] < lows[i - 1]:
            lower_lows += 1

    if higher_highs + higher_lows > lower_highs + lower_lows:
        structure = "bullish_structure"
    elif lower_highs + lower_lows > higher_highs + higher_lows:
        structure = "bearish_structure"
    else:
        structure = "mixed_structure"

    return {
        "structure": structure,
        "swing_highs": len(highs),
        "swing_lows": len(lows),
        "higher_highs": higher_highs,
        "lower_highs": lower_highs,
        "higher_lows": higher_lows,
        "lower_lows": lower_lows,
        "latest_swing_high": highs[-1] if highs else None,
        "latest_swing_low": lows[-1] if lows else None,
    }


# ============================================================
# PATTERN EXTRACTION
# ============================================================

def direction_pattern(candles):
    return " ".join(
        candle_direction(c)
        for c in candles[-PATTERN_SIZE:]
    )


def pattern_from_codes(codes):
    return " ".join(codes)


# ============================================================
# HISTORICAL PATTERN SCORING
# ============================================================

def outcome_for_horizon(candles, index, horizon):
    future_index = index + horizon

    if future_index >= len(candles):
        return None

    current_close = candles[index]["close"]
    future_close = candles[future_index]["close"]

    if current_close == 0:
        return "neutral"

    change = ((future_close - current_close) / current_close) * 100

    # Small movement is neutral.
    if abs(change) < 0.03:
        return "neutral"

    if change > 0:
        return "bullish"

    return "bearish"


def collect_pattern_statistics(candles):
    stats = {}

    max_start = len(candles) - PATTERN_SIZE - max(HORIZONS)

    for i in range(max_start + 1):

        pattern_codes = [
            candle_direction(candles[j])
            for j in range(i, i + PATTERN_SIZE)
        ]

        pattern = pattern_from_codes(pattern_codes)

        if pattern not in stats:
            stats[pattern] = {
                "occurrences": 0,
                "4": {"bullish": 0, "bearish": 0, "neutral": 0},
                "8": {"bullish": 0, "bearish": 0, "neutral": 0},
                "16": {"bullish": 0, "bearish": 0, "neutral": 0},
            }

        stats[pattern]["occurrences"] += 1

        anchor = i + PATTERN_SIZE - 1

        for horizon in HORIZONS:

            outcome = outcome_for_horizon(
                candles,
                anchor,
                horizon
            )

            if outcome:
                stats[pattern][str(horizon)][outcome] += 1

    return stats


# ============================================================
# PATTERN SIMILARITY
# ============================================================

def pattern_similarity(pattern_a, pattern_b):
    a = pattern_a.split()
    b = pattern_b.split()

    if len(a) != len(b):
        return 0.0

    if not a:
        return 0.0

    matches = sum(
        1
        for x, y in zip(a, b)
        if x == y
    )

    return matches / len(a)


def find_similar_patterns(current_pattern, stats, limit=10):
    results = []

    for pattern, data in stats.items():

        occurrences = data["occurrences"]

        if occurrences < MIN_PATTERN_OCCURRENCES:
            continue

        similarity = pattern_similarity(
            current_pattern,
            pattern
        )

        if similarity <= 0:
            continue

        results.append(
            {
                "pattern": pattern,
                "similarity": similarity,
                "occurrences": occurrences,
                "data": data,
            }
        )

    results.sort(
        key=lambda x: (
            x["similarity"],
            x["occurrences"]
        ),
        reverse=True
    )

    return results[:limit]


# ============================================================
# DISTRIBUTION
# ============================================================

def distribution(data):
    total = (
        data["bullish"]
        + data["bearish"]
        + data["neutral"]
    )

    if total == 0:
        return {
            "bullish": 0.0,
            "bearish": 0.0,
            "neutral": 0.0,
        }

    return {
        "bullish": data["bullish"] / total * 100,
        "bearish": data["bearish"] / total * 100,
        "neutral": data["neutral"] / total * 100,
    }


def dominant_outcome(data):
    dist = distribution(data)

    values = {
        "bullish": dist["bullish"],
        "bearish": dist["bearish"],
        "neutral": dist["neutral"],
    }

    return max(values, key=values.get)


# ============================================================
# EXPERIENCE MEMORY
# ============================================================

def normalize_experience(memory):
    if memory is None:
        return {
            "version": "1.5-compatible",
            "observations": [],
        }

    if isinstance(memory, dict):

        observations = memory.get("observations")

        if isinstance(observations, list):
            return memory

    return {
        "version": "1.5-compatible",
        "observations": [],
    }


def get_experience_statistics(memory):
    observations = memory.get("observations", [])

    total = len(observations)

    resolved_windows = 0
    confirmed = 0
    not_confirmed = 0
    neutral = 0
    pending = 0

    horizon_stats = {}

    for h in HORIZONS:
        horizon_stats[h] = {
            "resolved": 0,
            "confirmed": 0,
            "not_confirmed": 0,
            "neutral": 0,
        }

    for observation in observations:

        outcomes = observation.get("outcomes", {})

        for h in HORIZONS:

            value = outcomes.get(str(h))

            if value is None:
                value = outcomes.get(h)

            if isinstance(value, dict):
                status = value.get("status")
            else:
                status = value

            if status in ("pending", None):
                pending += 1
                continue

            resolved_windows += 1
            horizon_stats[h]["resolved"] += 1

            if status == "confirmed":
                confirmed += 1
                horizon_stats[h]["confirmed"] += 1

            elif status == "not_confirmed":
                not_confirmed += 1
                horizon_stats[h]["not_confirmed"] += 1

            elif status == "neutral":
                neutral += 1
                horizon_stats[h]["neutral"] += 1

    return {
        "total_observations": total,
        "resolved_windows": resolved_windows,
        "confirmed": confirmed,
        "not_confirmed": not_confirmed,
        "neutral": neutral,
        "pending_windows": pending,
        "horizon_stats": horizon_stats,
    }


# ============================================================
# EXPERIENCE RELIABILITY
# ============================================================

def experience_reliability(stats):
    resolved = stats["resolved_windows"]

    if resolved == 0:
        return 0.0

    confirmed = stats["confirmed"]
    not_confirmed = stats["not_confirmed"]

    decisive = confirmed + not_confirmed

    if decisive == 0:
        return 0.0

    raw = confirmed / decisive * 100

    # Reliability grows gradually with actual experience.
    sample_factor = min(1.0, resolved / 30.0)

    return raw * sample_factor


# ============================================================
# ADAPTIVE PATTERN SCORE
# ============================================================

def calculate_pattern_score(
    current_pattern,
    similar_patterns,
    experience_stats
):

    if not similar_patterns:
        return {
            "bullish": 0.0,
            "bearish": 0.0,
            "neutral": 0.0,
            "coverage": 0.0,
            "reliability": 0.0,
        }

    weighted = {
        "bullish": 0.0,
        "bearish": 0.0,
        "neutral": 0.0,
    }

    total_weight = 0.0

    for item in similar_patterns:

        similarity = item["similarity"]
        occurrences = item["occurrences"]
        data = item["data"]

        # Limit frequency influence so huge patterns do not dominate.
        frequency_weight = min(
            2.0,
            math.sqrt(max(occurrences, 1))
        )

        weight = similarity * frequency_weight

        dist = distribution(data["8"])

        for outcome in weighted:
            weighted[outcome] += (
                dist[outcome] * weight
            )

        total_weight += weight

    if total_weight == 0:
        return {
            "bullish": 0.0,
            "bearish": 0.0,
            "neutral": 0.0,
            "coverage": 0.0,
            "reliability": 0.0,
        }

    for outcome in weighted:
        weighted[outcome] /= total_weight

    coverage = min(
        100.0,
        total_weight * 20.0
    )

    reliability = experience_reliability(
        experience_stats
    )

    return {
        "bullish": weighted["bullish"],
        "bearish": weighted["bearish"],
        "neutral": weighted["neutral"],
        "coverage": coverage,
        "reliability": reliability,
    }


# ============================================================
# EVIDENCE FUSION
# ============================================================

def build_adaptive_evidence(
    context,
    structure,
    pattern_score,
    experience_stats
):

    bullish = 0.0
    bearish = 0.0
    neutral = 0.0

    reasons_bullish = []
    reasons_bearish = []
    reasons_neutral = []

    # --------------------------------------------------------
    # Candle direction
    # --------------------------------------------------------

    if context["bullish_candles"] > context["bearish_candles"]:
        bullish += 1.5
        reasons_bullish.append(
            "Bullish candle count exceeds bearish candle count."
        )

    elif context["bearish_candles"] > context["bullish_candles"]:
        bearish += 1.5
        reasons_bearish.append(
            "Bearish candle count exceeds bullish candle count."
        )

    else:
        neutral += 1.0
        reasons_neutral.append(
            "Bullish and bearish candle counts are balanced."
        )

    # --------------------------------------------------------
    # Price movement
    # --------------------------------------------------------

    if context["movement"] > 0:
        bullish += 1.5
        reasons_bullish.append(
            "Net price movement is upward."
        )

    elif context["movement"] < 0:
        bearish += 1.5
        reasons_bearish.append(
            "Net price movement is downward."
        )

    else:
        neutral += 1.0

    # --------------------------------------------------------
    # Structure
    # --------------------------------------------------------

    if structure["structure"] == "bullish_structure":
        bullish += 2.0
        reasons_bullish.append(
            "Market structure contains stronger bullish swing relationships."
        )

    elif structure["structure"] == "bearish_structure":
        bearish += 2.0
        reasons_bearish.append(
            "Market structure contains stronger bearish swing relationships."
        )

    else:
        neutral += 1.0
        reasons_neutral.append(
            "Market structure is mixed."
        )

    # --------------------------------------------------------
    # Rejection
    # --------------------------------------------------------

    if (
        context["rejection"]
        == "lower_rejection_dominant"
        and context["direction"] == "bullish"
    ):
        bullish += 1.0
        reasons_bullish.append(
            "Lower-price rejection is dominant within a bullish context."
        )

    elif (
        context["rejection"]
        == "upper_rejection_dominant"
        and context["direction"] == "bearish"
    ):
        bearish += 1.0
        reasons_bearish.append(
            "Upper-price rejection is dominant within a bearish context."
        )

    # --------------------------------------------------------
    # Momentum
    # --------------------------------------------------------

    if context["momentum"] == "increasing":

        if context["direction"] == "bullish":
            bullish += 1.0
            reasons_bullish.append(
                "Momentum is increasing in the bullish context."
            )

        elif context["direction"] == "bearish":
            bearish += 1.0
            reasons_bearish.append(
                "Momentum is increasing in the bearish context."
            )

    # --------------------------------------------------------
    # Pattern evidence
    # --------------------------------------------------------

    pattern_bullish = pattern_score["bullish"]
    pattern_bearish = pattern_score["bearish"]
    pattern_neutral = pattern_score["neutral"]

    pattern_weight = (
        pattern_score["coverage"] / 100.0
    )

    bullish += (
        pattern_bullish / 100.0
        * 2.0
        * pattern_weight
    )

    bearish += (
        pattern_bearish / 100.0
        * 2.0
        * pattern_weight
    )

    neutral += (
        pattern_neutral / 100.0
        * 1.0
        * pattern_weight
    )

    if pattern_score["coverage"] > 0:

        if pattern_bullish > pattern_bearish:
            reasons_bullish.append(
                "Similar historical patterns show a bullish-weighted distribution."
            )

        elif pattern_bearish > pattern_bullish:
            reasons_bearish.append(
                "Similar historical patterns show a bearish-weighted distribution."
            )

        else:
            reasons_neutral.append(
                "Similar historical patterns are directionally mixed."
            )

    # --------------------------------------------------------
    # Actual experience
    # --------------------------------------------------------

    reliability = experience_reliability(
        experience_stats
    )

    if reliability > 0:

        experience_weight = reliability / 100.0

        if (
            experience_stats["confirmed"]
            > experience_stats["not_confirmed"]
        ):
            bullish += 1.5 * experience_weight

            reasons_bullish.append(
                "Resolved MLAI experience currently favours confirmed observations."
            )

        elif (
            experience_stats["not_confirmed"]
            > experience_stats["confirmed"]
        ):
            bearish += 1.5 * experience_weight

            reasons_bearish.append(
                "Resolved MLAI experience currently contains more not-confirmed outcomes."
            )

    total = bullish + bearish + neutral

    if total <= 0:
        direction = "neutral"
        confidence = 0.0

    else:

        scores = {
            "bullish": bullish,
            "bearish": bearish,
            "neutral": neutral,
        }

        direction = max(
            scores,
            key=scores.get
        )

        dominant = scores[direction]

        confidence = (
            dominant / total * 100.0
        )

    return {
        "bullish_score": bullish,
        "bearish_score": bearish,
        "neutral_score": neutral,
        "direction": direction,
        "confidence": confidence,
        "bullish_reasons": reasons_bullish,
        "bearish_reasons": reasons_bearish,
        "neutral_reasons": reasons_neutral,
    }


# ============================================================
# CONFIDENCE LEVEL
# ============================================================

def confidence_level(confidence, experience_stats):

    resolved = experience_stats["resolved_windows"]

    if resolved == 0:

        if confidence >= 70:
            return "moderate_historical_confidence"

        if confidence >= 50:
            return "low_historical_confidence"

        return "insufficient_learning_experience"

    if confidence >= 80:
        return "high"

    if confidence >= 65:
        return "moderate"

    if confidence >= 50:
        return "low"

    return "very_low"


# ============================================================
# ADAPTIVE MEMORY
# ============================================================

def create_adaptive_memory(
    context,
    structure,
    current_pattern,
    similar_patterns,
    pattern_score,
    evidence,
    experience_stats
):

    return {
        "version": "1.5",
        "created_at": now_iso(),

        "market_context": context,
        "structure": structure,

        "current_pattern": current_pattern,

        "pattern_analysis": {
            "similar_patterns": similar_patterns,
            "pattern_score": pattern_score,
        },

        "experience": experience_stats,

        "adaptive_evidence": evidence,

        "confidence": {
            "score": evidence["confidence"],
            "level": confidence_level(
                evidence["confidence"],
                experience_stats
            ),
        },

        "principles": [
            "Historical pattern frequency is not the same as learned experience.",
            "Unresolved observations are excluded from experience scoring.",
            "Pattern similarity is weighted by similarity and occurrence frequency.",
            "Resolved experience gradually receives more influence as sample size grows.",
            "Confidence represents evidence agreement, not certainty.",
            "Mixed evidence remains visible.",
            "No single candle or pattern determines the interpretation.",
            "The engine does not create an automatic trading signal.",
        ],
    }


# ============================================================
# STATUS DOCUMENT
# ============================================================

def update_status(memory, context, structure, evidence):

    path = "MLAI_PROJECT_STATUS.md"

    lines = []

    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.read().splitlines()
        except Exception:
            lines = []

    marker = "# MLAI v1.5"

    lines = [
        line
        for line in lines
        if not line.startswith(marker)
    ]

    lines.extend([
        "",
        marker,
        "",
        f"Updated: {now_iso()}",
        "",
        "## Adaptive Learning State",
        "",
        f"- Direction: {evidence['direction']}",
        f"- Confidence: {evidence['confidence']:.1f}%",
        f"- Confidence level: {confidence_level(evidence['confidence'], memory['experience'])}",
        f"- Current pattern: {memory['current_pattern']}",
        f"- Experience observations: {memory['experience']['total_observations']}",
        f"- Resolved windows: {memory['experience']['resolved_windows']}",
        f"- Pending windows: {memory['experience']['pending_windows']}",
        "",
        "## Market Context",
        "",
        f"- Market direction: {context['direction']}",
        f"- Structure: {structure['structure']}",
        f"- Momentum: {context['momentum']}",
        f"- Volatility: {context['volatility']}",
        f"- Rejection: {context['rejection']}",
        f"- Net change: {context['change_pct']:.3f}%",
        "",
        "## Evidence Scores",
        "",
        f"- Bullish score: {evidence['bullish_score']:.3f}",
        f"- Bearish score: {evidence['bearish_score']:.3f}",
        f"- Neutral score: {evidence['neutral_score']:.3f}",
        "",
        "## v1.5 Principle",
        "",
        "MLAI v1.5 combines current market evidence, historical pattern similarity and resolved experience while keeping unresolved observations separate.",
        "",
        "The system does not treat confidence as certainty and does not produce an automatic trading signal.",
        "",
    ])

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


# ============================================================
# PRINT HELPERS
# ============================================================

def print_distribution(label, data):
    dist = distribution(data)

    print(
        f"{label:<20} "
        f"B={dist['bullish']:.1f}% | "
        f"S={dist['bearish']:.1f}% | "
        f"N={dist['neutral']:.1f}%"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("MLAI v1.5 - LOADING MARKET MEMORY")
    print("=" * 70)

    print(f"File: {MARKET_FILE}")
    print()

    if not os.path.exists(MARKET_FILE):
        print("ERROR: market_data.bin was not found.")
        return

    market_memory = load_pickle(MARKET_FILE)

    print("PASS: market_data.bin loaded as MLAI memory object.")
    print()

    metadata = {}

    if isinstance(market_memory, dict):
        metadata = market_memory.get(
            "metadata",
            market_memory.get("meta", {})
        )

    print("MEMORY METADATA")
    print("-" * 70)

    if isinstance(metadata, dict):
        print(
            f"MLAI version : "
            f"{metadata.get('mlai_version', metadata.get('version', 'unknown'))}"
        )

        print(
            f"Created at   : "
            f"{metadata.get('created_at', 'unknown')}"
        )

        print(
            f"Source       : "
            f"{metadata.get('source', 'unknown')}"
        )

    candles_raw = extract_candles(market_memory)

    candles = [
        normalize_candle(c)
        for c in candles_raw
    ]

    candles = [
        c
        for c in candles
        if c["close"] != 0
    ]

    print()
    print(f"Found {len(candles)} stored candles.")

    if len(candles) < WINDOW_SIZE:
        print()
        print(
            f"ERROR: At least {WINDOW_SIZE} candles are required."
        )
        return

    analysis_candles = candles[-WINDOW_SIZE:]

    print()
    print(
        f"PASS: Using latest {len(analysis_candles)} candles."
    )

    print()
    print("Analysing latest 60 candles...")
    print()

    context = calculate_context(
        analysis_candles
    )

    structure = calculate_structure(
        analysis_candles
    )

    current_pattern = direction_pattern(
        analysis_candles
    )

    print(
        "PASS: Loading MLAI experience memory..."
    )

    experience_memory = normalize_experience(
        load_pickle(EXPERIENCE_FILE)
    )

    experience_stats = get_experience_statistics(
        experience_memory
    )

    print(
        "PASS: Loading MLAI pattern memory..."
    )

    pattern_memory = load_pickle(
        PATTERN_FILE
    )

    # v1.3/v1.4 pattern memory may have a nested
    # statistics dictionary. We still recalculate from
    # the market memory to guarantee consistency.
    print(
        "PASS: Calculating adaptive historical pattern experience..."
    )

    pattern_stats = collect_pattern_statistics(
        candles
    )

    similar_patterns = find_similar_patterns(
        current_pattern,
        pattern_stats,
        limit=10
    )

    pattern_score = calculate_pattern_score(
        current_pattern,
        similar_patterns,
        experience_stats
    )

    evidence = build_adaptive_evidence(
        context,
        structure,
        pattern_score,
        experience_stats
    )

    adaptive_memory = create_adaptive_memory(
        context,
        structure,
        current_pattern,
        similar_patterns,
        pattern_score,
        evidence,
        experience_stats
    )

    save_pickle(
        ADAPTIVE_FILE,
        adaptive_memory
    )

    print(
        f"PASS: {ADAPTIVE_FILE} saved."
    )

    print()
    print("=" * 70)
    print("MLAI v1.5 ADAPTIVE LEARNING + PATTERN SCORING ENGINE")
    print("=" * 70)

    print()
    print("CURRENT MARKET CONTEXT")
    print("-" * 70)

    print(
        f"Directional character : "
        f"{context['direction']}"
    )

    print(
        f"Bullish candles       : "
        f"{context['bullish_candles']}"
    )

    print(
        f"Bearish candles       : "
        f"{context['bearish_candles']}"
    )

    print(
        f"Neutral candles       : "
        f"{context['neutral_candles']}"
    )

    print(
        f"Momentum              : "
        f"{context['momentum']}"
    )

    print(
        f"Volatility            : "
        f"{context['volatility']}"
    )

    print(
        f"Rejection             : "
        f"{context['rejection']}"
    )

    print()
    print("CURRENT PATTERN")
    print("-" * 70)
    print(current_pattern)

    print()
    print("HISTORICAL PATTERN SIMILARITY")
    print("-" * 70)

    if similar_patterns:

        for i, item in enumerate(
            similar_patterns,
            start=1
        ):

            print(
                f"{i:02d}. "
                f"{item['pattern']} | "
                f"similarity={item['similarity']:.3f} | "
                f"occurrences={item['occurrences']}"
            )

            print_distribution(
                "    8-candle",
                item["data"]["8"]
            )

    else:
        print(
            "No sufficiently repeated similar patterns found."
        )

    print()
    print("ADAPTIVE PATTERN SCORE")
    print("-" * 70)

    print(
        f"Bullish pattern weight : "
        f"{pattern_score['bullish']:.1f}%"
    )

    print(
        f"Bearish pattern weight : "
        f"{pattern_score['bearish']:.1f}%"
    )

    print(
        f"Neutral pattern weight  : "
        f"{pattern_score['neutral']:.1f}%"
    )

    print(
        f"Pattern coverage       : "
        f"{pattern_score['coverage']:.1f}%"
    )

    print(
        f"Experience reliability : "
        f"{pattern_score['reliability']:.1f}%"
    )

    print()
    print("EXPERIENCE MEMORY")
    print("-" * 70)

    print(
        f"Observations stored   : "
        f"{experience_stats['total_observations']}"
    )

    print(
        f"Resolved windows      : "
        f"{experience_stats['resolved_windows']}"
    )

    print(
        f"Pending windows       : "
        f"{experience_stats['pending_windows']}"
    )

    print(
        f"Confirmed outcomes    : "
        f"{experience_stats['confirmed']}"
    )

    print(
        f"Not confirmed         : "
        f"{experience_stats['not_confirmed']}"
    )

    print(
        f"Neutral outcomes      : "
        f"{experience_stats['neutral']}"
    )

    print()
    print("ADAPTIVE EVIDENCE FUSION")
    print("-" * 70)

    print(
        f"Bullish evidence score : "
        f"{evidence['bullish_score']:.3f}"
    )

    print(
        f"Bearish evidence score : "
        f"{evidence['bearish_score']:.3f}"
    )

    print(
        f"Neutral evidence score : "
        f"{evidence['neutral_score']:.3f}"
    )

    print()
    print("ADAPTIVE INTERPRETATION")
    print("-" * 70)

    print(
        f"Integrated direction : "
        f"{evidence['direction']}"
    )

    print(
        f"Evidence confidence  : "
        f"{evidence['confidence']:.1f}%"
    )

    print(
        f"Confidence level     : "
        f"{confidence_level(evidence['confidence'], experience_stats)}"
    )

    print()
    print("BULLISH SUPPORTING EVIDENCE")
    print("-" * 70)

    if evidence["bullish_reasons"]:
        for reason in evidence["bullish_reasons"]:
            print(f"- {reason}")
    else:
        print("- None identified.")

    print()
    print("BEARISH SUPPORTING EVIDENCE")
    print("-" * 70)

    if evidence["bearish_reasons"]:
        for reason in evidence["bearish_reasons"]:
            print(f"- {reason}")
    else:
        print("- None identified.")

    print()
    print("NEUTRAL / LIMITING EVIDENCE")
    print("-" * 70)

    if evidence["neutral_reasons"]:
        for reason in evidence["neutral_reasons"]:
            print(f"- {reason}")
    else:
        print("- None identified.")

    print()
    print("ADAPTIVE LEARNING PRINCIPLES")
    print("-" * 70)

    principles = adaptive_memory["principles"]

    for i, principle in enumerate(
        principles,
        start=1
    ):
        print(f"{i}. {principle}")

    print()
    print("CURRENT MARKET STORY")
    print("-" * 70)

    story = (
        f"The current {PATTERN_SIZE}-candle direction pattern "
        f"is {current_pattern}. "
        f"The broader market context has a "
        f"{context['direction']} directional character. "
        f"Market structure is {structure['structure']}. "
        f"Momentum is {context['momentum']} and volatility is "
        f"{context['volatility']}. "
        f"MLAI found {len(similar_patterns)} sufficiently repeated "
        f"similar historical patterns for adaptive comparison. "
        f"The adaptive evidence engine currently produces a "
        f"{evidence['direction']} interpretation with "
        f"{evidence['confidence']:.1f}% evidence agreement. "
        f"MLAI has {experience_stats['total_observations']} "
        f"stored experience observations, with "
        f"{experience_stats['resolved_windows']} resolved outcome "
        f"windows and "
        f"{experience_stats['pending_windows']} pending windows. "
        f"Resolved experience receives increasing influence only "
        f"as actual future market outcomes become available. "
        f"Historical pattern similarity is treated as contextual "
        f"evidence rather than certainty. "
        f"The adaptive engine preserves uncertainty and does not "
        f"produce an automatic trading signal."
    )

    print(story)

    update_status(
        adaptive_memory,
        context,
        structure,
        evidence
    )

    print()
    print(
        "PASS: MLAI_PROJECT_STATUS.md updated."
    )

    print()
    print(
        "PASS: MLAI v1.5 Adaptive Learning + Pattern Scoring Engine completed."
    )

    print("=" * 70)


if __name__ == "__main__":
    main()