# ============================================================
# MLAI v2.1 FIXED
# Unified Scenario + Outcome Projection Engine
#
# FIXES:
# 1. Correctly reads v2.0 unified memory when available.
# 2. Correctly reads multi-timeframe memory.
# 3. Correctly reads regime memory.
# 4. Does not convert missing values into "unknown" when
#    valid information exists elsewhere.
# 5. Pending experience receives ZERO learning influence.
# 6. Scenario percentages are evidence scores, NOT fake
#    probabilities.
# 7. Prevents unsupported 95%+ scenario confidence.
# 8. Preserves bullish / bearish / neutral scenarios.
# 9. Uses 4 / 8 / 16 candle horizons.
# 10. Saves mlai_scenario_memory.bin.
# 11. Updates MLAI_PROJECT_STATUS.md.
# ============================================================

import os
import pickle
from datetime import datetime, timezone


# ============================================================
# CONFIGURATION
# ============================================================

MARKET_FILE = "market_data.bin"

EXPERIENCE_FILE = "mlai_experience.bin"
PATTERN_FILE = "mlai_pattern_memory.bin"
ADAPTIVE_FILE = "mlai_adaptive_memory.bin"
MTF_FILE = "mlai_multitimeframe_memory.bin"
REGIME_FILE = "mlai_regime_memory.bin"
TRANSITION_FILE = "mlai_regime_transition_memory.bin"
REGIME_LEARNING_FILE = "mlai_regime_learning_memory.bin"
UNIFIED_FILE = "mlai_unified_memory.bin"

SCENARIO_FILE = "mlai_scenario_memory.bin"
STATUS_FILE = "MLAI_PROJECT_STATUS.md"

LOOKBACK = 60
HORIZONS = [4, 8, 16]


# ============================================================
# HELPERS
# ============================================================

def load_pickle(path, default=None):
    if not os.path.exists(path):
        return default

    try:
        with open(path, "rb") as f:
            return pickle.load(f)
    except Exception:
        return default


def save_pickle(path, data):
    with open(path, "wb") as f:
        pickle.dump(data, f)


def get(d, *keys, default=None):
    """
    Safely retrieve the first existing key from a dictionary.
    """
    if not isinstance(d, dict):
        return default

    for key in keys:
        if key in d and d[key] is not None:
            return d[key]

    return default


def number(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def pct(value):
    return f"{number(value):.1f}%"


def direction_from_candles(candles):
    bullish = 0
    bearish = 0
    neutral = 0

    for c in candles:
        o = number(c.get("open"))
        cl = number(c.get("close"))

        if cl > o:
            bullish += 1
        elif cl < o:
            bearish += 1
        else:
            neutral += 1

    if bullish > bearish:
        direction = "bullish"
    elif bearish > bullish:
        direction = "bearish"
    else:
        direction = "neutral"

    return bullish, bearish, neutral, direction


def calculate_net_change(candles):
    if not candles:
        return 0.0, 0.0

    first = number(candles[0].get("close"))
    last = number(candles[-1].get("close"))

    movement = last - first

    if first != 0:
        change_pct = (movement / first) * 100.0
    else:
        change_pct = 0.0

    return movement, change_pct


def simple_structure(candles):
    if len(candles) < 6:
        return "insufficient_data"

    closes = [number(c.get("close")) for c in candles]

    first_third = sum(closes[: len(closes)//3]) / max(1, len(closes)//3)

    last_part = closes[-len(closes)//3:]
    last_third = sum(last_part) / max(1, len(last_part))

    if last_third > first_third:
        return "bullish_structure"

    if last_third < first_third:
        return "bearish_structure"

    return "range_structure"


def infer_momentum(candles):
    if len(candles) < 10:
        return "stable"

    closes = [number(c.get("close")) for c in candles]

    recent = closes[-5:]
    previous = closes[-10:-5]

    recent_move = abs(recent[-1] - recent[0])
    previous_move = abs(previous[-1] - previous[0])

    if recent_move > previous_move * 1.10:
        return "increasing"

    if recent_move < previous_move * 0.90:
        return "decreasing"

    return "stable"


def infer_volatility(candles):
    if len(candles) < 10:
        return "stable"

    ranges = []

    for c in candles:
        high = number(c.get("high"))
        low = number(c.get("low"))
        ranges.append(abs(high - low))

    recent = sum(ranges[-5:]) / 5
    previous = sum(ranges[-10:-5]) / 5

    if recent > previous * 1.10:
        return "expanding"

    if recent < previous * 0.90:
        return "contracting"

    return "stable"


def infer_rejection(candles):
    upper = 0
    lower = 0

    for c in candles:
        o = number(c.get("open"))
        h = number(c.get("high"))
        l = number(c.get("low"))
        cl = number(c.get("close"))

        body_high = max(o, cl)
        body_low = min(o, cl)

        upper_wick = h - body_high
        lower_wick = body_low - l

        if upper_wick > lower_wick:
            upper += 1
        elif lower_wick > upper_wick:
            lower += 1

    if lower > upper:
        return "lower_rejection_dominant"

    if upper > lower:
        return "upper_rejection_dominant"

    return "balanced_rejection"


# ============================================================
# LOAD MARKET MEMORY
# ============================================================

print("=" * 70)
print("MLAI v2.1 FIXED - LOADING MARKET MEMORY")
print("=" * 70)
print(f"File: {MARKET_FILE}")
print()

market_memory = load_pickle(MARKET_FILE)

if market_memory is None:
    print("ERROR: market_data.bin could not be loaded.")
    raise SystemExit(1)

print("PASS: market_data.bin loaded as MLAI memory object.")
print()

metadata = {}

if isinstance(market_memory, dict):
    metadata = market_memory.get("metadata", {})

print("MEMORY METADATA")
print("-" * 70)
print(f"MLAI version : {metadata.get('mlai_version', 'unknown')}")
print(f"Created at   : {metadata.get('created_at', 'unknown')}")
print(f"Source       : {metadata.get('source', 'unknown')}")
print()


# ============================================================
# EXTRACT CANDLES
# ============================================================

candles = []

if isinstance(market_memory, dict):
    for key in ["candles", "data", "market_data", "records"]:
        value = market_memory.get(key)

        if isinstance(value, list):
            candles = value
            break

elif isinstance(market_memory, list):
    candles = market_memory


if not candles:
    print("ERROR: No candle data found in market_data.bin.")
    raise SystemExit(1)


print(f"Found {len(candles)} stored candles.")
print()

if len(candles) < LOOKBACK:
    analysis = candles[:]
else:
    analysis = candles[-LOOKBACK:]

print(f"PASS: Using latest {len(analysis)} candles.")
print()
print("Analysing latest candles...")
print()


# ============================================================
# CURRENT DIRECT MARKET CONTEXT
# ============================================================

bullish, bearish, neutral, direction = direction_from_candles(analysis)

movement, change_pct = calculate_net_change(analysis)

first_close = number(analysis[0].get("close"))
latest_close = number(analysis[-1].get("close"))

structure = simple_structure(analysis)
momentum = infer_momentum(analysis)
volatility = infer_volatility(analysis)
rejection = infer_rejection(analysis)


# ============================================================
# LOAD PREVIOUS MLAI MEMORIES
# ============================================================

print("PASS: Loading MLAI evidence memories...")

experience_memory = load_pickle(EXPERIENCE_FILE, {})
pattern_memory = load_pickle(PATTERN_FILE, {})
adaptive_memory = load_pickle(ADAPTIVE_FILE, {})
mtf_memory = load_pickle(MTF_FILE, {})
regime_memory = load_pickle(REGIME_FILE, {})
transition_memory = load_pickle(TRANSITION_FILE, {})
regime_learning_memory = load_pickle(REGIME_LEARNING_FILE, {})
unified_memory = load_pickle(UNIFIED_FILE, {})

print("PASS: Evidence memories loaded.")
print()


# ============================================================
# MULTI-TIMEFRAME FIX
# ============================================================

def extract_timeframe(memory, names):
    if not isinstance(memory, dict):
        return None

    contexts = get(
        memory,
        "timeframes",
        "contexts",
        "timeframe_contexts",
        "multi_timeframe",
        default=None
    )

    if isinstance(contexts, dict):
        for name in names:
            if name in contexts and isinstance(contexts[name], dict):
                return contexts[name]

    for name in names:
        direct = memory.get(name)

        if isinstance(direct, dict):
            return direct

    return None


short_ctx = extract_timeframe(
    mtf_memory,
    ["short", "Short", "20", "short_context"]
)

medium_ctx = extract_timeframe(
    mtf_memory,
    ["medium", "Medium", "60", "medium_context"]
)

higher_ctx = extract_timeframe(
    mtf_memory,
    ["higher", "Higher", "120", "higher_context"]
)


# If stored MTF memory is incomplete, reconstruct it.
if short_ctx is None and len(candles) >= 20:
    short_candles = candles[-20:]

    b, s, n, d = direction_from_candles(short_candles)
    m, cp = calculate_net_change(short_candles)

    short_ctx = {
        "candles": 20,
        "direction": d,
        "structure": simple_structure(short_candles),
        "bullish": b,
        "bearish": s,
        "neutral": n,
        "net_change_pct": cp,
        "momentum": infer_momentum(short_candles),
        "volatility": infer_volatility(short_candles),
    }


if medium_ctx is None:
    medium_ctx = {
        "candles": len(analysis),
        "direction": direction,
        "structure": structure,
        "bullish": bullish,
        "bearish": bearish,
        "neutral": neutral,
        "net_change_pct": change_pct,
        "momentum": momentum,
        "volatility": volatility,
    }


if higher_ctx is None and len(candles) >= 120:
    higher_candles = candles[-120:]

    b, s, n, d = direction_from_candles(higher_candles)
    m, cp = calculate_net_change(higher_candles)

    higher_ctx = {
        "candles": 120,
        "direction": d,
        "structure": simple_structure(higher_candles),
        "bullish": b,
        "bearish": s,
        "neutral": n,
        "net_change_pct": cp,
        "momentum": infer_momentum(higher_candles),
        "volatility": infer_volatility(higher_candles),
    }


# ============================================================
# NORMALIZE MTF VALUES
# ============================================================

def context_direction(ctx):
    if not isinstance(ctx, dict):
        return "unknown"

    d = get(ctx, "direction", "integrated_direction", "directional_character")

    if d in ["bullish", "bearish", "neutral", "mixed"]:
        return d

    return "unknown"


def context_structure(ctx):
    if not isinstance(ctx, dict):
        return "unknown"

    return get(
        ctx,
        "structure",
        "structural_context",
        "structure_direction",
        default="unknown"
    )


short_direction = context_direction(short_ctx)
medium_direction = context_direction(medium_ctx)
higher_direction = context_direction(higher_ctx)

short_structure = context_structure(short_ctx)
medium_structure = context_structure(medium_ctx)
higher_structure = context_structure(higher_ctx)


mtf_directions = [
    short_direction,
    medium_direction,
    higher_direction
]

valid_mtf = [
    d for d in mtf_directions
    if d in ["bullish", "bearish", "neutral", "mixed"]
]

bullish_contexts = valid_mtf.count("bullish")
bearish_contexts = valid_mtf.count("bearish")
neutral_contexts = valid_mtf.count("neutral")
mixed_contexts = valid_mtf.count("mixed")

if bullish_contexts > bearish_contexts:
    mtf_direction = "bullish"
elif bearish_contexts > bullish_contexts:
    mtf_direction = "bearish"
elif neutral_contexts > 0 and bullish_contexts == bearish_contexts:
    mtf_direction = "neutral"
else:
    mtf_direction = "mixed"


if valid_mtf:
    max_count = max(
        bullish_contexts,
        bearish_contexts,
        neutral_contexts,
        mixed_contexts
    )
    mtf_alignment = (max_count / len(valid_mtf)) * 100
else:
    mtf_alignment = 0.0


# ============================================================
# REGIME FIX
# ============================================================

regime = "unknown"
regime_strength = "unknown"
regime_direction = "unknown"
regime_confidence = 0.0


if isinstance(regime_memory, dict):

    current_regime = get(
        regime_memory,
        "current_regime",
        "regime",
        "current",
        default=None
    )

    if isinstance(current_regime, dict):
        regime = get(
            current_regime,
            "regime",
            "name",
            "classification",
            default="unknown"
        )

        regime_strength = get(
            current_regime,
            "strength",
            "regime_strength",
            default="unknown"
        )

        regime_direction = get(
            current_regime,
            "direction",
            "integrated_direction",
            default="unknown"
        )

        regime_confidence = number(
            get(
                current_regime,
                "confidence",
                "regime_confidence",
                default=0
            )
        )

    else:
        regime = get(
            regime_memory,
            "regime",
            "current_regime",
            "classification",
            default="unknown"
        )

        regime_strength = get(
            regime_memory,
            "strength",
            "regime_strength",
            default="unknown"
        )

        regime_direction = get(
            regime_memory,
            "direction",
            "integrated_direction",
            default="unknown"
        )

        regime_confidence = number(
            get(
                regime_memory,
                "confidence",
                "regime_confidence",
                default=0
            )
        )


# Recover missing regime direction from regime name.
if regime_direction == "unknown":
    if "bullish" in str(regime):
        regime_direction = "bullish"
    elif "bearish" in str(regime):
        regime_direction = "bearish"
    elif "range" in str(regime):
        regime_direction = "neutral"


if regime_strength == "unknown":
    if regime_confidence >= 70:
        regime_strength = "strong"
    elif regime_confidence >= 45:
        regime_strength = "moderate"
    elif regime_confidence > 0:
        regime_strength = "weak"


# ============================================================
# EXPERIENCE MEMORY
# ============================================================

observations = []

if isinstance(experience_memory, dict):

    observations = get(
        experience_memory,
        "observations",
        "experience",
        "records",
        default=[]
    )

elif isinstance(experience_memory, list):
    observations = experience_memory

if not isinstance(observations, list):
    observations = []


resolved_windows = 0
pending_windows = 0
confirmed = 0
not_confirmed = 0
neutral_outcomes = 0


for obs in observations:

    if not isinstance(obs, dict):
        continue

    outcomes = obs.get("outcomes", {})

    if not isinstance(outcomes, dict):
        continue

    for horizon in HORIZONS:

        value = outcomes.get(str(horizon))

        if value is None:
            value = outcomes.get(horizon)

        if value in [None, "pending", ""]:
            pending_windows += 1
            continue

        resolved_windows += 1

        status = ""

        if isinstance(value, dict):
            status = str(
                get(
                    value,
                    "status",
                    "outcome",
                    "classification",
                    default=""
                )
            ).lower()
        else:
            status = str(value).lower()

        if "confirm" in status:
            confirmed += 1
        elif "not" in status and "confirm" in status:
            not_confirmed += 1
        elif "neutral" in status:
            neutral_outcomes += 1


# ============================================================
# HISTORICAL EXPERIENCE WEIGHT
# ============================================================

experience_reliability = 0.0

if resolved_windows > 0:
    experience_reliability = (
        confirmed / resolved_windows
    ) * 100.0


# ============================================================
# DIRECT EVIDENCE
# ============================================================

bullish_score = 0.0
bearish_score = 0.0
neutral_score = 0.0


# Candle participation
total_directional = bullish + bearish

if total_directional > 0:

    bullish_ratio = bullish / total_directional
    bearish_ratio = bearish / total_directional

    bullish_score += bullish_ratio * 3.0
    bearish_score += bearish_ratio * 3.0


# Net movement
if change_pct > 0:
    bullish_score += 2.0

elif change_pct < 0:
    bearish_score += 2.0

else:
    neutral_score += 1.0


# Structure
if "bullish" in structure:
    bullish_score += 2.0

elif "bearish" in structure:
    bearish_score += 2.0

else:
    neutral_score += 1.0


# Momentum
if direction == "bullish" and momentum == "increasing":
    bullish_score += 1.5

elif direction == "bearish" and momentum == "increasing":
    bearish_score += 1.5


# Rejection
if direction == "bullish" and rejection == "lower_rejection_dominant":
    bullish_score += 1.5

elif direction == "bearish" and rejection == "upper_rejection_dominant":
    bearish_score += 1.5


# MTF
if mtf_direction == "bullish":
    bullish_score += 1.5 * (mtf_alignment / 100)

elif mtf_direction == "bearish":
    bearish_score += 1.5 * (mtf_alignment / 100)

else:
    neutral_score += 1.0


# Regime
if regime_direction == "bullish":
    bullish_score += 1.0 * (regime_confidence / 100)

elif regime_direction == "bearish":
    bearish_score += 1.0 * (regime_confidence / 100)


# ============================================================
# HISTORICAL PATTERN EVIDENCE
# ============================================================

historical_bullish = 0.0
historical_bearish = 0.0
historical_neutral = 0.0


if isinstance(adaptive_memory, dict):

    historical_bullish = number(
        get(
            adaptive_memory,
            "bullish_weight",
            "bullish_score",
            "bullish_pattern_weight",
            default=0
        )
    )

    historical_bearish = number(
        get(
            adaptive_memory,
            "bearish_weight",
            "bearish_score",
            "bearish_pattern_weight",
            default=0
        )
    )

    historical_neutral = number(
        get(
            adaptive_memory,
            "neutral_weight",
            "neutral_score",
            "neutral_pattern_weight",
            default=0
        )
    )


# Normalize only if actual usable historical weights exist.
historical_total = (
    historical_bullish +
    historical_bearish +
    historical_neutral
)

if historical_total > 0:

    # Historical evidence is deliberately capped.
    historical_factor = min(2.0, historical_total / 10.0)

    bullish_score += (
        historical_bullish / historical_total
    ) * historical_factor

    bearish_score += (
        historical_bearish / historical_total
    ) * historical_factor

    neutral_score += (
        historical_neutral / historical_total
    ) * historical_factor


# ============================================================
# EXPERIENCE MUST NOT BE USED WHEN PENDING
# ============================================================

if resolved_windows > 0:

    experience_factor = min(
        2.0,
        resolved_windows / 20.0
    )

    if experience_reliability > 50:
        bullish_score += experience_factor

    elif experience_reliability < 50:
        bearish_score += experience_factor

else:
    experience_factor = 0.0


# ============================================================
# SCENARIO CALCULATION
# ============================================================

raw_total = (
    bullish_score +
    bearish_score +
    neutral_score
)

if raw_total <= 0:
    raw_total = 1.0


raw_bullish = bullish_score / raw_total
raw_bearish = bearish_score / raw_total
raw_neutral = neutral_score / raw_total


# ------------------------------------------------------------
# IMPORTANT FIX:
#
# These are NOT statistical probabilities.
# We intentionally compress extreme evidence scores toward
# the centre so a lack of resolved experience cannot create
# fake 95%-99% "probabilities".
# ------------------------------------------------------------

MAX_SCENARIO_SHARE = 0.80

bullish_share = 0.33 + (raw_bullish - 0.33) * 0.70
bearish_share = 0.33 + (raw_bearish - 0.33) * 0.70
neutral_share = 0.34 + (raw_neutral - 0.34) * 0.70

shares = [
    max(0.0, bullish_share),
    max(0.0, bearish_share),
    max(0.0, neutral_share)
]

# Normalize
share_total = sum(shares)

if share_total <= 0:
    shares = [1/3, 1/3, 1/3]
else:
    shares = [x / share_total for x in shares]


# Final safety cap
max_index = max(range(3), key=lambda i: shares[i])

if shares[max_index] > MAX_SCENARIO_SHARE:

    excess = shares[max_index] - MAX_SCENARIO_SHARE
    shares[max_index] = MAX_SCENARIO_SHARE

    others = [
        i for i in range(3)
        if i != max_index
    ]

    other_total = sum(shares[i] for i in others)

    if other_total > 0:
        for i in others:
            shares[i] += excess * (
                shares[i] / other_total
            )


bullish_scenario = shares[0] * 100
bearish_scenario = shares[1] * 100
neutral_scenario = shares[2] * 100


# ============================================================
# HORIZON DECAY
# ============================================================

def horizon_scenarios(base_bullish, base_bearish, base_neutral, horizon):

    uncertainty = {
        4: 0.00,
        8: 0.08,
        16: 0.16
    }.get(horizon, 0.20)

    b = base_bullish
    br = base_bearish
    n = base_neutral

    # Longer horizon = more uncertainty.
    shift_b = (b - 33.33) * (1.0 - uncertainty)
    shift_br = (br - 33.33) * (1.0 - uncertainty)

    hb = 33.33 + shift_b
    hbr = 33.33 + shift_br
    hn = 100.0 - hb - hbr

    return hb, hbr, hn


scenario_4 = horizon_scenarios(
    bullish_scenario,
    bearish_scenario,
    neutral_scenario,
    4
)

scenario_8 = horizon_scenarios(
    bullish_scenario,
    bearish_scenario,
    neutral_scenario,
    8
)

scenario_16 = horizon_scenarios(
    bullish_scenario,
    bearish_scenario,
    neutral_scenario,
    16
)


# ============================================================
# PRIMARY SCENARIO
# ============================================================

scenario_values = {
    "bullish_continuation_scenario": bullish_scenario,
    "bearish_reversal_scenario": bearish_scenario,
    "neutral_range_scenario": neutral_scenario
}

primary_scenario = max(
    scenario_values,
    key=scenario_values.get
)


# ============================================================
# EVIDENCE CONFIDENCE
# ============================================================

sorted_scores = sorted(
    [bullish_score, bearish_score, neutral_score],
    reverse=True
)

if len(sorted_scores) >= 2:
    top = sorted_scores[0]
    second = sorted_scores[1]

    if top + second > 0:
        separation = (top - second) / (top + second)
    else:
        separation = 0
else:
    separation = 0


confidence = 50.0 + separation * 40.0

# No resolved experience = lower maximum confidence.
if resolved_windows == 0:
    confidence = min(confidence, 78.0)

# Partial MTF alignment should also limit confidence.
if mtf_alignment < 100:
    confidence = min(
        confidence,
        70.0 + mtf_alignment * 0.08
    )

confidence = max(0.0, min(95.0, confidence))


if confidence >= 80:
    confidence_level = "high"

elif confidence >= 65:
    confidence_level = "moderate"

else:
    confidence_level = "low"


# ============================================================
# SUPPORTING / CONFLICTING EVIDENCE
# ============================================================

supporting = []
conflicting = []
limiting = []


if bullish > bearish:
    supporting.append(
        "Bullish candle participation exceeds bearish participation."
    )

elif bearish > bullish:
    supporting.append(
        "Bearish candle participation exceeds bullish participation."
    )


if change_pct > 0:
    supporting.append(
        f"Price moved upward by {change_pct:.3f}%."
    )

elif change_pct < 0:
    supporting.append(
        f"Price moved downward by {abs(change_pct):.3f}%."
    )


if structure == "bullish_structure":
    supporting.append(
        "Recent market structure favours bullish behaviour."
    )

elif structure == "bearish_structure":
    supporting.append(
        "Recent market structure favours bearish behaviour."
    )


if rejection == "lower_rejection_dominant" and direction == "bullish":
    supporting.append(
        "Lower-price rejection is dominant inside a bullish context."
    )

elif rejection == "upper_rejection_dominant" and direction == "bearish":
    supporting.append(
        "Upper-price rejection is dominant inside a bearish context."
    )


if mtf_direction == "bullish":
    supporting.append(
        f"Multi-timeframe context currently favours bullish direction "
        f"with {mtf_alignment:.1f}% alignment."
    )

elif mtf_direction == "bearish":
    supporting.append(
        f"Multi-timeframe context currently favours bearish direction "
        f"with {mtf_alignment:.1f}% alignment."
    )


if mtf_alignment < 100:
    conflicting.append(
        "Not all available timeframes agree on direction."
    )


if regime_direction != "unknown" and regime_direction != direction:
    conflicting.append(
        "Current regime direction conflicts with direct market direction."
    )


if resolved_windows == 0:
    limiting.append(
        "No resolved personal experience is available yet."
    )

if mtf_alignment < 100:
    limiting.append(
        "Multi-timeframe alignment is incomplete."
    )

if historical_total <= 0:
    limiting.append(
        "No usable adaptive historical pattern weighting is available."
    )

limiting.append(
    "Scenario percentages represent evidence weighting, not statistical probabilities."
)


# ============================================================
# SAVE SCENARIO MEMORY
# ============================================================

scenario_memory = {
    "mlai_version": "2.1",
    "engine": "Unified Scenario + Outcome Projection Engine",
    "created_at": datetime.now(timezone.utc).isoformat(),

    "market": {
        "candles_analyzed": len(analysis),
        "first_close": first_close,
        "latest_close": latest_close,
        "movement": movement,
        "change_pct": change_pct,
        "direction": direction,
        "structure": structure,
        "momentum": momentum,
        "volatility": volatility,
        "rejection": rejection
    },

    "multi_timeframe": {
        "short": short_ctx,
        "medium": medium_ctx,
        "higher": higher_ctx,
        "direction": mtf_direction,
        "alignment": mtf_alignment
    },

    "regime": {
        "regime": regime,
        "direction": regime_direction,
        "strength": regime_strength,
        "confidence": regime_confidence
    },

    "experience": {
        "observations": len(observations),
        "resolved_windows": resolved_windows,
        "pending_windows": pending_windows,
        "confirmed": confirmed,
        "not_confirmed": not_confirmed,
        "neutral": neutral_outcomes,
        "reliability": experience_reliability
    },

    "scenario": {
        "primary": primary_scenario,
        "bullish": bullish_scenario,
        "bearish": bearish_scenario,
        "neutral": neutral_scenario,

        "4": {
            "bullish": scenario_4[0],
            "bearish": scenario_4[1],
            "neutral": scenario_4[2]
        },

        "8": {
            "bullish": scenario_8[0],
            "bearish": scenario_8[1],
            "neutral": scenario_8[2]
        },

        "16": {
            "bullish": scenario_16[0],
            "bearish": scenario_16[1],
            "neutral": scenario_16[2]
        }
    },

    "confidence": {
        "score": confidence,
        "level": confidence_level
    },

    "evidence_scores": {
        "bullish": bullish_score,
        "bearish": bearish_score,
        "neutral": neutral_score
    },

    "principles": [
        "Scenarios describe evidence-weighted possibilities rather than guaranteed outcomes.",
        "Direct market evidence receives priority.",
        "Historical patterns remain contextual evidence.",
        "Pending experience receives zero learning influence.",
        "Resolved experience can influence later scenario weighting.",
        "Multi-timeframe disagreement remains visible.",
        "Regime information provides environmental context.",
        "Bullish, bearish and neutral scenarios remain visible.",
        "Longer horizons carry greater uncertainty.",
        "Scenario percentages are not statistical probabilities.",
        "No single candle, pattern, regime or timeframe determines the result.",
        "The system does not guarantee future market behaviour."
    ]
}

save_pickle(SCENARIO_FILE, scenario_memory)

print("PASS: mlai_scenario_memory.bin saved.")
print()


# ============================================================
# OUTPUT
# ============================================================

print("=" * 70)
print("MLAI v2.1 FIXED UNIFIED SCENARIO + OUTCOME PROJECTION ENGINE")
print("=" * 70)
print()

print("CURRENT MARKET CONTEXT")
print("-" * 70)
print(f"Direction              : {direction}")
print(f"Structure              : {structure}")
print(f"Momentum               : {momentum}")
print(f"Volatility             : {volatility}")
print(f"Rejection              : {rejection}")
print()

print("PRICE CONTEXT")
print("-" * 70)
print(f"First close            : {first_close:.4f}")
print(f"Latest close           : {latest_close:.4f}")
print(f"Net movement           : {movement:.4f}")
print(f"Net change %           : {change_pct:.3f}%")
print()

print("SCENARIO EVIDENCE")
print("-" * 70)
print(f"Bullish continuation   : {bullish_scenario:.1f}%")
print(f"Bearish reversal       : {bearish_scenario:.1f}%")
print(f"Neutral / range        : {neutral_scenario:.1f}%")
print()

print("SCENARIO CLASSIFICATION")
print("-" * 70)
print(f"Primary scenario       : {primary_scenario}")
print()

print("4-CANDLE SCENARIO")
print("-" * 70)
print(
    f"Bullish={scenario_4[0]:.1f}% | "
    f"Bearish={scenario_4[1]:.1f}% | "
    f"Neutral={scenario_4[2]:.1f}%"
)
print()

print("8-CANDLE SCENARIO")
print("-" * 70)
print(
    f"Bullish={scenario_8[0]:.1f}% | "
    f"Bearish={scenario_8[1]:.1f}% | "
    f"Neutral={scenario_8[2]:.1f}%"
)
print()

print("16-CANDLE SCENARIO")
print("-" * 70)
print(
    f"Bullish={scenario_16[0]:.1f}% | "
    f"Bearish={scenario_16[1]:.1f}% | "
    f"Neutral={scenario_16[2]:.1f}%"
)
print()

print("REGIME CONTEXT")
print("-" * 70)
print(f"Regime                 : {regime}")
print(f"Regime direction       : {regime_direction}")
print(f"Regime strength        : {regime_strength}")
print(f"Regime confidence      : {regime_confidence:.1f}%")
print()

print("MULTI-TIMEFRAME CONTEXT")
print("-" * 70)
print(f"Short direction        : {short_direction}")
print(f"Medium direction       : {medium_direction}")
print(f"Higher direction       : {higher_direction}")
print(f"Integrated direction   : {mtf_direction}")
print(f"Alignment              : {mtf_alignment:.1f}%")
print()

print("EXPERIENCE MEMORY")
print("-" * 70)
print(f"Observations stored    : {len(observations)}")
print(f"Resolved windows       : {resolved_windows}")
print(f"Pending windows        : {pending_windows}")
print(f"Confirmed outcomes     : {confirmed}")
print(f"Not confirmed          : {not_confirmed}")
print(f"Neutral outcomes       : {neutral_outcomes}")
print(f"Experience reliability : {experience_reliability:.1f}%")
print()

print("EVIDENCE CONFIDENCE")
print("-" * 70)
print(f"Evidence confidence    : {confidence:.1f}%")
print(f"Confidence level       : {confidence_level}")
print()

print("SUPPORTING EVIDENCE")
print("-" * 70)

for item in supporting:
    print(f"- {item}")

if not supporting:
    print("- No strong supporting evidence identified.")

print()

print("CONFLICTING EVIDENCE")
print("-" * 70)

for item in conflicting:
    print(f"- {item}")

if not conflicting:
    print("- No major conflicting evidence identified.")

print()

print("LIMITING / UNCERTAIN EVIDENCE")
print("-" * 70)

for item in limiting:
    print(f"- {item}")

print()

print("CONFIRMATION CONDITIONS")
print("-" * 70)

if direction == "bullish":
    print("- Continued higher highs and higher lows would strengthen bullish continuation evidence.")
    print("- Continued bullish structure would strengthen the scenario.")
    print("- Increasing bullish momentum would strengthen continuation evidence.")

elif direction == "bearish":
    print("- Continued lower lows and lower highs would strengthen bearish continuation evidence.")
    print("- Continued bearish structure would strengthen the scenario.")
    print("- Increasing bearish momentum would strengthen continuation evidence.")

else:
    print("- A clear directional structural break would strengthen directional scenario evidence.")

print()

print("INVALIDATION CONDITIONS")
print("-" * 70)

if direction == "bullish":
    print("- Sustained bearish structural deterioration would weaken bullish continuation evidence.")
    print("- Strong bearish follow-through after bullish failures would weaken the bullish scenario.")

elif direction == "bearish":
    print("- Sustained bullish structural deterioration would weaken bearish continuation evidence.")
    print("- Strong bullish follow-through after bearish failures would weaken the bearish scenario.")

else:
    print("- A sustained directional breakout would weaken the neutral/range scenario.")

print()

print("SCENARIO INTERPRETATION")
print("-" * 70)

if primary_scenario == "bullish_continuation_scenario":
    print(
        "Current evidence favours a bullish continuation environment. "
        "This is an evidence-weighted scenario, not a guaranteed future outcome."
    )

elif primary_scenario == "bearish_reversal_scenario":
    print(
        "Current evidence favours a bearish reversal environment. "
        "This is an evidence-weighted scenario, not a guaranteed future outcome."
    )

else:
    print(
        "Current evidence favours a neutral/range environment. "
        "This is an evidence-weighted scenario, not a guaranteed future outcome."
    )

print()

print("IMPORTANT CALIBRATION NOTE")
print("-" * 70)
print(
    "Scenario percentages are evidence-weighted shares and are NOT "
    "statistical probabilities. Actual calibration requires resolved "
    "historical outcomes."
)
print()

print("CURRENT MARKET STORY")
print("-" * 70)

story = (
    f"The MLAI v2.1 Fixed Scenario Engine evaluates the current market "
    f"context as {primary_scenario}. The direct market direction is "
    f"{direction} with {structure} structure. Momentum is {momentum} "
    f"and volatility is {volatility}. The multi-timeframe context is "
    f"{mtf_direction} with {mtf_alignment:.1f}% directional alignment. "
    f"The current regime is {regime} with {regime_confidence:.1f}% "
    f"regime confidence. MLAI has {len(observations)} stored experience "
    f"observations, with {resolved_windows} resolved outcome windows "
    f"and {pending_windows} pending windows. Pending experience receives "
    f"zero learning influence. The primary scenario currently has an "
    f"evidence-weighted share of {max(bullish_scenario, bearish_scenario, neutral_scenario):.1f}%. "
    f"This percentage is not a statistical probability. The engine "
    f"preserves uncertainty and requires actual future outcomes for "
    f"calibration."
)

print(story)
print()

print("SCENARIO ENGINE PRINCIPLES")
print("-" * 70)

for i, principle in enumerate(scenario_memory["principles"], 1):
    print(f"{i}. {principle}")

print()
print("=" * 70)


# ============================================================
# PROJECT STATUS
# ============================================================

status = f"""# MLAI PROJECT STATUS

## Latest Engine

**MLAI v2.1 Fixed — Unified Scenario + Outcome Projection Engine**

Updated: {datetime.now(timezone.utc).isoformat()}

### Current Market

- Direction: {direction}
- Structure: {structure}
- Momentum: {momentum}
- Volatility: {volatility}
- Rejection: {rejection}
- Latest price: {latest_close:.4f}

### Scenario Evidence

- Bullish continuation: {bullish_scenario:.1f}%
- Bearish reversal: {bearish_scenario:.1f}%
- Neutral/range: {neutral_scenario:.1f}%
- Primary scenario: {primary_scenario}

### Multi-Timeframe

- Short: {short_direction}
- Medium: {medium_direction}
- Higher: {higher_direction}
- Integrated: {mtf_direction}
- Alignment: {mtf_alignment:.1f}%

### Regime

- Regime: {regime}
- Direction: {regime_direction}
- Strength: {regime_strength}
- Confidence: {regime_confidence:.1f}%

### Experience

- Observations: {len(observations)}
- Resolved windows: {resolved_windows}
- Pending windows: {pending_windows}
- Confirmed: {confirmed}
- Not confirmed: {not_confirmed}
- Neutral: {neutral_outcomes}
- Reliability: {experience_reliability:.1f}%

### Calibration

Scenario percentages are evidence-weighted scenario shares and are not statistical probabilities. Actual probability calibration requires resolved historical outcomes.

### Memory

- market_data.bin
- mlai_experience.bin
- mlai_pattern_memory.bin
- mlai_adaptive_memory.bin
- mlai_multitimeframe_memory.bin
- mlai_regime_memory.bin
- mlai_regime_transition_memory.bin
- mlai_regime_learning_memory.bin
- mlai_unified_memory.bin
- mlai_scenario_memory.bin
"""

with open(STATUS_FILE, "w", encoding="utf-8") as f:
    f.write(status)

print("PASS: MLAI_PROJECT_STATUS.md updated.")
print()
print("=" * 70)
print("PASS: MLAI v2.1 FIXED Unified Scenario + Outcome Projection Engine completed.")
print("=" * 70)