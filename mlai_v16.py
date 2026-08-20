
import os
import pickle
from datetime import datetime, timezone


# ============================================================
# MLAI v1.6
# MULTI-TIMEFRAME MARKET CONTEXT ENGINE
#
# Builds on:
#   v1.1  Experience Memory
#   v1.2  Outcome Resolution
#   v1.3  Pattern Discovery
#   v1.4  Pattern + Experience Learning
#   v1.5  Adaptive Pattern Scoring
#
# IMPORTANT:
#   This system describes market evidence.
#   It does NOT create an automatic trading signal.
# ============================================================


MEMORY_FILE = "market_data.bin"
EXPERIENCE_FILE = "mlai_experience.bin"
PATTERN_FILE = "mlai_pattern_memory.bin"
ADAPTIVE_FILE = "mlai_adaptive_memory.bin"
STATUS_FILE = "MLAI_PROJECT_STATUS.md"

LATEST_WINDOW = 60

# Context windows are expressed in candles from the stored dataset.
# They are not claiming to be actual broker timeframes.
CONTEXT_WINDOWS = {
    "short": 20,
    "medium": 60,
    "higher": 120,
}


# ============================================================
# GENERAL HELPERS
# ============================================================

def safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def safe_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default


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


def get_field(candle, name, default=None):
    if isinstance(candle, dict):
        return candle.get(name, default)

    try:
        return getattr(candle, name)
    except Exception:
        return default


def normalize_candles(raw):
    """
    Convert common market-data structures into a list of
    candle dictionaries containing open/high/low/close.
    """

    if raw is None:
        return []

    if isinstance(raw, dict):

        for key in (
            "candles",
            "data",
            "rows",
            "records",
            "market_data",
        ):
            if key in raw and isinstance(raw[key], (list, tuple)):
                raw = raw[key]
                break

    if not isinstance(raw, (list, tuple)):
        return []

    result = []

    for item in raw:

        if isinstance(item, dict):
            o = item.get("open")
            h = item.get("high")
            l = item.get("low")
            c = item.get("close")

            if o is None or h is None or l is None or c is None:
                continue

            candle = dict(item)

        else:
            try:
                o = getattr(item, "open")
                h = getattr(item, "high")
                l = getattr(item, "low")
                c = getattr(item, "close")

                candle = {
                    "open": o,
                    "high": h,
                    "low": l,
                    "close": c,
                }

            except Exception:
                continue

        try:
            candle["open"] = float(o)
            candle["high"] = float(h)
            candle["low"] = float(l)
            candle["close"] = float(c)
        except Exception:
            continue

        result.append(candle)

    return result


# ============================================================
# MEMORY EXTRACTION
# ============================================================

def extract_market_memory(memory):
    metadata = {}
    candles = []

    if isinstance(memory, dict):

        metadata = memory.get("metadata", {})

        for key in (
            "candles",
            "data",
            "rows",
            "records",
            "market_data",
        ):
            if key in memory:
                candles = normalize_candles(memory[key])
                if candles:
                    break

    elif isinstance(memory, (list, tuple)):
        candles = normalize_candles(memory)

    else:

        for key in (
            "candles",
            "data",
            "rows",
            "records",
        ):
            value = getattr(memory, key, None)

            if value is not None:
                candles = normalize_candles(value)

                if candles:
                    break

        metadata = getattr(memory, "metadata", {}) or {}

    return metadata, candles


# ============================================================
# CANDLE CLASSIFICATION
# ============================================================

def candle_direction(candle):
    o = safe_float(candle["open"])
    c = safe_float(candle["close"])

    if c > o:
        return "B"

    if c < o:
        return "S"

    return "N"


def body_size(candle):
    return abs(
        safe_float(candle["close"])
        - safe_float(candle["open"])
    )


def candle_range(candle):
    return max(
        0.0,
        safe_float(candle["high"])
        - safe_float(candle["low"])
    )


def upper_wick(candle):
    o = safe_float(candle["open"])
    c = safe_float(candle["close"])
    h = safe_float(candle["high"])

    return max(0.0, h - max(o, c))


def lower_wick(candle):
    o = safe_float(candle["open"])
    c = safe_float(candle["close"])
    l = safe_float(candle["low"])

    return max(0.0, min(o, c) - l)


# ============================================================
# BASIC CONTEXT ANALYSIS
# ============================================================

def analyse_context(candles):

    if not candles:
        return {
            "direction": "unknown",
            "bullish": 0,
            "bearish": 0,
            "neutral": 0,
            "first_close": 0.0,
            "latest_close": 0.0,
            "net_change": 0.0,
            "net_change_pct": 0.0,
            "momentum": "unknown",
            "volatility": "unknown",
            "upper_rejection": 0,
            "lower_rejection": 0,
            "rejection": "unknown",
            "higher_highs": 0,
            "lower_highs": 0,
            "higher_lows": 0,
            "lower_lows": 0,
            "structure": "unknown",
        }

    directions = [candle_direction(c) for c in candles]

    bullish = directions.count("B")
    bearish = directions.count("S")
    neutral = directions.count("N")

    first_close = safe_float(candles[0]["close"])
    latest_close = safe_float(candles[-1]["close"])

    net_change = latest_close - first_close

    if first_close != 0:
        net_change_pct = (net_change / first_close) * 100.0
    else:
        net_change_pct = 0.0

    if bullish > bearish:
        direction = "bullish"
    elif bearish > bullish:
        direction = "bearish"
    else:
        direction = "mixed"

    # --------------------------------------------------------
    # Wick / rejection behaviour
    # --------------------------------------------------------

    upper_rejection = 0
    lower_rejection = 0

    for candle in candles:

        rng = candle_range(candle)

        if rng <= 0:
            continue

        uw = upper_wick(candle)
        lw = lower_wick(candle)

        if uw / rng >= 0.35:
            upper_rejection += 1

        if lw / rng >= 0.35:
            lower_rejection += 1

    if lower_rejection > upper_rejection:
        rejection = "lower_rejection_dominant"
    elif upper_rejection > lower_rejection:
        rejection = "upper_rejection_dominant"
    else:
        rejection = "balanced_rejection"

    # --------------------------------------------------------
    # Structure approximation
    # --------------------------------------------------------

    highs = [
        safe_float(c["high"])
        for c in candles
    ]

    lows = [
        safe_float(c["low"])
        for c in candles
    ]

    higher_highs = 0
    lower_highs = 0
    higher_lows = 0
    lower_lows = 0

    for i in range(1, len(candles)):
        if highs[i] > highs[i - 1]:
            higher_highs += 1
        elif highs[i] < highs[i - 1]:
            lower_highs += 1

        if lows[i] > lows[i - 1]:
            higher_lows += 1
        elif lows[i] < lows[i - 1]:
            lower_lows += 1

    bullish_structure_score = higher_highs + higher_lows
    bearish_structure_score = lower_highs + lower_lows

    if bullish_structure_score > bearish_structure_score:
        structure = "bullish_structure"
    elif bearish_structure_score > bullish_structure_score:
        structure = "bearish_structure"
    else:
        structure = "mixed_structure"

    # --------------------------------------------------------
    # Momentum
    # --------------------------------------------------------

    midpoint = max(1, len(candles) // 2)

    first_half = candles[:midpoint]
    second_half = candles[midpoint:]

    first_body = (
        sum(body_size(c) for c in first_half)
        / max(1, len(first_half))
    )

    second_body = (
        sum(body_size(c) for c in second_half)
        / max(1, len(second_half))
    )

    if second_body > first_body * 1.10:
        momentum = "increasing"
    elif second_body < first_body * 0.90:
        momentum = "decreasing"
    else:
        momentum = "stable"

    # --------------------------------------------------------
    # Volatility
    # --------------------------------------------------------

    first_range = (
        sum(candle_range(c) for c in first_half)
        / max(1, len(first_half))
    )

    second_range = (
        sum(candle_range(c) for c in second_half)
        / max(1, len(second_half))
    )

    if second_range > first_range * 1.10:
        volatility = "expanding"
    elif second_range < first_range * 0.90:
        volatility = "contracting"
    else:
        volatility = "stable"

    return {
        "direction": direction,
        "bullish": bullish,
        "bearish": bearish,
        "neutral": neutral,
        "first_close": first_close,
        "latest_close": latest_close,
        "net_change": net_change,
        "net_change_pct": net_change_pct,
        "momentum": momentum,
        "volatility": volatility,
        "upper_rejection": upper_rejection,
        "lower_rejection": lower_rejection,
        "rejection": rejection,
        "higher_highs": higher_highs,
        "lower_highs": lower_highs,
        "higher_lows": higher_lows,
        "lower_lows": lower_lows,
        "structure": structure,
    }


# ============================================================
# MULTI-TIMEFRAME ALIGNMENT
# ============================================================

def calculate_alignment(contexts):

    directions = [
        c["direction"]
        for c in contexts.values()
        if c["direction"] != "unknown"
    ]

    bullish_count = directions.count("bullish")
    bearish_count = directions.count("bearish")
    mixed_count = directions.count("mixed")

    total = len(directions)

    if total == 0:
        return {
            "direction": "unknown",
            "alignment": "insufficient_data",
            "score": 0.0,
            "bullish_contexts": 0,
            "bearish_contexts": 0,
            "mixed_contexts": 0,
        }

    if bullish_count > bearish_count:
        integrated_direction = "bullish"
    elif bearish_count > bullish_count:
        integrated_direction = "bearish"
    else:
        integrated_direction = "mixed"

    dominant = max(
        bullish_count,
        bearish_count,
        mixed_count
    )

    score = (dominant / total) * 100.0

    if score >= 100:
        alignment = "full_alignment"
    elif score >= 66.7:
        alignment = "majority_alignment"
    elif score >= 50:
        alignment = "partial_alignment"
    else:
        alignment = "conflicted"

    return {
        "direction": integrated_direction,
        "alignment": alignment,
        "score": score,
        "bullish_contexts": bullish_count,
        "bearish_contexts": bearish_count,
        "mixed_contexts": mixed_count,
    }


def calculate_structure_alignment(contexts):

    structures = [
        c["structure"]
        for c in contexts.values()
        if c["structure"] != "unknown"
    ]

    bullish = structures.count("bullish_structure")
    bearish = structures.count("bearish_structure")
    mixed = structures.count("mixed_structure")

    if bullish > bearish:
        direction = "bullish"
    elif bearish > bullish:
        direction = "bearish"
    else:
        direction = "mixed"

    total = max(1, len(structures))

    score = max(bullish, bearish, mixed) / total * 100.0

    return {
        "direction": direction,
        "score": score,
        "bullish": bullish,
        "bearish": bearish,
        "mixed": mixed,
    }


def calculate_momentum_alignment(contexts):

    increasing = 0
    decreasing = 0
    stable = 0

    for context in contexts.values():

        value = context["momentum"]

        if value == "increasing":
            increasing += 1
        elif value == "decreasing":
            decreasing += 1
        else:
            stable += 1

    total = max(
        1,
        increasing + decreasing + stable
    )

    if increasing > decreasing:
        dominant = "increasing"
        score = increasing / total * 100.0
    elif decreasing > increasing:
        dominant = "decreasing"
        score = decreasing / total * 100.0
    else:
        dominant = "stable"
        score = stable / total * 100.0

    return {
        "direction": dominant,
        "score": score,
        "increasing": increasing,
        "decreasing": decreasing,
        "stable": stable,
    }


def calculate_volatility_alignment(contexts):

    expanding = 0
    contracting = 0
    stable = 0

    for context in contexts.values():

        value = context["volatility"]

        if value == "expanding":
            expanding += 1
        elif value == "contracting":
            contracting += 1
        else:
            stable += 1

    total = max(
        1,
        expanding + contracting + stable
    )

    if expanding > contracting:
        dominant = "expanding"
        score = expanding / total * 100.0
    elif contracting > expanding:
        dominant = "contracting"
        score = contracting / total * 100.0
    else:
        dominant = "stable"
        score = stable / total * 100.0

    return {
        "direction": dominant,
        "score": score,
        "expanding": expanding,
        "contracting": contracting,
        "stable": stable,
    }


# ============================================================
# EVIDENCE FUSION
# ============================================================

def calculate_mtf_evidence(
    directional,
    structural,
    momentum,
    volatility,
    contexts,
):

    bullish = 0.0
    bearish = 0.0
    neutral = 0.0

    # Directional alignment
    if directional["direction"] == "bullish":
        bullish += directional["score"] * 0.40
    elif directional["direction"] == "bearish":
        bearish += directional["score"] * 0.40
    else:
        neutral += directional["score"] * 0.40

    # Structure alignment
    if structural["direction"] == "bullish":
        bullish += structural["score"] * 0.30
    elif structural["direction"] == "bearish":
        bearish += structural["score"] * 0.30
    else:
        neutral += structural["score"] * 0.30

    # Momentum contribution
    if directional["direction"] == "bullish":
        if momentum["direction"] == "increasing":
            bullish += momentum["score"] * 0.15
        elif momentum["direction"] == "decreasing":
            bearish += momentum["score"] * 0.05

    elif directional["direction"] == "bearish":
        if momentum["direction"] == "increasing":
            bearish += momentum["score"] * 0.15
        elif momentum["direction"] == "decreasing":
            bullish += momentum["score"] * 0.05

    # Volatility is contextual rather than directional.
    if volatility["direction"] == "expanding":
        neutral += volatility["score"] * 0.05
    else:
        neutral += volatility["score"] * 0.02

    # Direct context evidence
    for context in contexts.values():

        if context["direction"] == "bullish":
            bullish += 1.0
        elif context["direction"] == "bearish":
            bearish += 1.0
        else:
            neutral += 1.0

    total = bullish + bearish + neutral

    if total <= 0:
        return {
            "bullish": 0.0,
            "bearish": 0.0,
            "neutral": 0.0,
            "direction": "mixed",
            "confidence": 0.0,
        }

    if bullish > bearish and bullish > neutral:
        direction = "bullish"
        confidence = bullish / total * 100.0
    elif bearish > bullish and bearish > neutral:
        direction = "bearish"
        confidence = bearish / total * 100.0
    else:
        direction = "mixed"
        confidence = neutral / total * 100.0

    return {
        "bullish": bullish,
        "bearish": bearish,
        "neutral": neutral,
        "direction": direction,
        "confidence": confidence,
    }


# ============================================================
# EXPERIENCE / PATTERN / ADAPTIVE MEMORY
# ============================================================

def memory_counts():

    experience = load_pickle(EXPERIENCE_FILE, {})
    pattern = load_pickle(PATTERN_FILE, {})
    adaptive = load_pickle(ADAPTIVE_FILE, {})

    observations = 0
    resolved = 0
    pending = 0

    if isinstance(experience, dict):

        obs = experience.get("observations")

        if isinstance(obs, list):
            observations = len(obs)

            for item in obs:

                outcomes = item.get("outcomes", {})

                for value in outcomes.values():

                    if isinstance(value, dict):

                        status = value.get("status")

                        if status == "pending":
                            pending += 1
                        elif status:
                            resolved += 1

    return {
        "observations": observations,
        "resolved_windows": resolved,
        "pending_windows": pending,
        "pattern_memory_loaded": bool(pattern),
        "adaptive_memory_loaded": bool(adaptive),
    }


# ============================================================
# PROJECT STATUS
# ============================================================

def update_project_status(
    metadata,
    total_candles,
    contexts,
    directional,
    structural,
    momentum,
    volatility,
    evidence,
    counts,
):

    timestamp = datetime.now(timezone.utc).isoformat()

    source = metadata.get("source", "unknown")
    version = metadata.get("mlai_version", "unknown")
    created = metadata.get("created_at", "unknown")

    lines = []

    lines.append("# MLAI PROJECT STATUS")
    lines.append("")
    lines.append("## Current Version")
    lines.append("")
    lines.append("MLAI v1.6 — Multi-Timeframe Market Context Engine")
    lines.append("")
    lines.append(f"Updated: {timestamp}")
    lines.append("")
    lines.append("## Market Memory")
    lines.append("")
    lines.append(f"- Stored candles: {total_candles}")
    lines.append(f"- Memory MLAI version: {version}")
    lines.append(f"- Memory created at: {created}")
    lines.append(f"- Source: {source}")
    lines.append("")
    lines.append("## Multi-Timeframe Context")
    lines.append("")

    for name, context in contexts.items():

        lines.append(
            f"### {name.capitalize()} Context "
            f"({CONTEXT_WINDOWS[name]} candles)"
        )

        lines.append(
            f"- Direction: {context['direction']}"
        )

        lines.append(
            f"- Structure: {context['structure']}"
        )

        lines.append(
            f"- Momentum: {context['momentum']}"
        )

        lines.append(
            f"- Volatility: {context['volatility']}"
        )

        lines.append(
            f"- Change: {context['net_change_pct']:.3f}%"
        )

        lines.append("")

    lines.append("## Multi-Timeframe Alignment")
    lines.append("")

    lines.append(
        f"- Direction: {directional['direction']}"
    )

    lines.append(
        f"- Alignment: {directional['alignment']}"
    )

    lines.append(
        f"- Directional alignment score: "
        f"{directional['score']:.1f}%"
    )

    lines.append(
        f"- Structural alignment: "
        f"{structural['direction']}"
    )

    lines.append(
        f"- Structural score: "
        f"{structural['score']:.1f}%"
    )

    lines.append(
        f"- Momentum alignment: "
        f"{momentum['direction']}"
    )

    lines.append(
        f"- Volatility alignment: "
        f"{volatility['direction']}"
    )

    lines.append("")

    lines.append("## Multi-Timeframe Evidence")
    lines.append("")

    lines.append(
        f"- Bullish score: {evidence['bullish']:.3f}"
    )

    lines.append(
        f"- Bearish score: {evidence['bearish']:.3f}"
    )

    lines.append(
        f"- Neutral score: {evidence['neutral']:.3f}"
    )

    lines.append(
        f"- Integrated direction: {evidence['direction']}"
    )

    lines.append(
        f"- Evidence confidence: "
        f"{evidence['confidence']:.1f}%"
    )

    lines.append("")

    lines.append("## Learning Memory")
    lines.append("")

    lines.append(
        f"- Experience observations: "
        f"{counts['observations']}"
    )

    lines.append(
        f"- Resolved windows: "
        f"{counts['resolved_windows']}"
    )

    lines.append(
        f"- Pending windows: "
        f"{counts['pending_windows']}"
    )

    lines.append("")

    lines.append("## v1.6 Principles")
    lines.append("")

    principles = [
        "Multiple market contexts are compared instead of relying on one window.",
        "Short, medium and higher contexts are kept separate.",
        "Directional agreement and structural agreement are measured independently.",
        "Momentum and volatility are treated as contextual evidence.",
        "Conflicting contexts remain visible.",
        "Historical memory is not treated as guaranteed future behaviour.",
        "Experience memory is not counted until outcomes are actually resolved.",
        "Evidence confidence represents agreement between observations, not certainty.",
        "The engine does not create an automatic trading signal.",
    ]

    for i, principle in enumerate(principles, 1):
        lines.append(f"{i}. {principle}")

    lines.append("")

    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("MLAI v1.6 - LOADING MARKET MEMORY")
    print("=" * 70)
    print(f"File: {MEMORY_FILE}")
    print()

    memory = load_pickle(MEMORY_FILE)

    if memory is None:
        print("ERROR: market_data.bin could not be loaded.")
        print("Make sure the market memory file exists.")
        return

    print("PASS: market_data.bin loaded as MLAI memory object.")
    print()

    metadata, candles = extract_market_memory(memory)

    if not candles:
        print("ERROR: No valid candles found in market_data.bin.")
        return

    print("MEMORY METADATA")
    print("-" * 70)
    print(
        f"MLAI version : "
        f"{metadata.get('mlai_version', 'unknown')}"
    )
    print(
        f"Created at   : "
        f"{metadata.get('created_at', 'unknown')}"
    )
    print(
        f"Source       : "
        f"{metadata.get('source', 'unknown')}"
    )
    print()

    print(f"Found {len(candles)} stored candles.")
    print()

    latest = candles[-LATEST_WINDOW:]

    print(
        f"PASS: Using latest {len(latest)} candles."
    )
    print()

    print(
        f"Analysing latest {len(latest)} candles..."
    )
    print()

    # --------------------------------------------------------
    # Build contexts
    # --------------------------------------------------------

    contexts = {}

    for name, window in CONTEXT_WINDOWS.items():

        if len(candles) < window:
            context_candles = candles
        else:
            context_candles = candles[-window:]

        contexts[name] = analyse_context(
            context_candles
        )

    print("PASS: Multi-timeframe contexts calculated.")
    print()

    # --------------------------------------------------------
    # Alignment
    # --------------------------------------------------------

    directional = calculate_alignment(contexts)

    structural = calculate_structure_alignment(contexts)

    momentum = calculate_momentum_alignment(contexts)

    volatility = calculate_volatility_alignment(contexts)

    evidence = calculate_mtf_evidence(
        directional,
        structural,
        momentum,
        volatility,
        contexts,
    )

    counts = memory_counts()

    # --------------------------------------------------------
    # Save v1.6 memory
    # --------------------------------------------------------

    mtf_memory = {
        "version": "1.6",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_metadata": metadata,
        "contexts": contexts,
        "directional_alignment": directional,
        "structural_alignment": structural,
        "momentum_alignment": momentum,
        "volatility_alignment": volatility,
        "evidence": evidence,
        "experience_memory": counts,
    }

    save_pickle(
        "mlai_multitimeframe_memory.bin",
        mtf_memory,
    )

    print(
        "PASS: mlai_multitimeframe_memory.bin saved."
    )
    print()

    # --------------------------------------------------------
    # Display
    # --------------------------------------------------------

    print("=" * 70)
    print(
        "MLAI v1.6 MULTI-TIMEFRAME MARKET CONTEXT ENGINE"
    )
    print("=" * 70)
    print()

    print("TIMEFRAME CONTEXTS")
    print("-" * 70)

    for name, context in contexts.items():

        print(
            f"{name.capitalize():<12} "
            f"| candles={CONTEXT_WINDOWS[name]:<3} "
            f"| direction={context['direction']:<8} "
            f"| structure={context['structure']}"
        )

    print()

    print("SHORT CONTEXT")
    print("-" * 70)
    short = contexts["short"]

    print(
        f"Direction             : {short['direction']}"
    )

    print(
        f"Bullish candles       : {short['bullish']}"
    )

    print(
        f"Bearish candles       : {short['bearish']}"
    )

    print(
        f"Neutral candles       : {short['neutral']}"
    )

    print(
        f"Net change %          : "
        f"{short['net_change_pct']:.3f}%"
    )

    print(
        f"Structure             : {short['structure']}"
    )

    print(
        f"Momentum              : {short['momentum']}"
    )

    print(
        f"Volatility            : {short['volatility']}"
    )

    print()

    print("MEDIUM CONTEXT")
    print("-" * 70)
    medium = contexts["medium"]

    print(
        f"Direction             : {medium['direction']}"
    )

    print(
        f"Bullish candles       : {medium['bullish']}"
    )

    print(
        f"Bearish candles       : {medium['bearish']}"
    )

    print(
        f"Neutral candles       : {medium['neutral']}"
    )

    print(
        f"Net change %          : "
        f"{medium['net_change_pct']:.3f}%"
    )

    print(
        f"Structure             : {medium['structure']}"
    )

    print(
        f"Momentum              : {medium['momentum']}"
    )

    print(
        f"Volatility            : {medium['volatility']}"
    )

    print()

    print("HIGHER CONTEXT")
    print("-" * 70)
    higher = contexts["higher"]

    print(
        f"Direction             : {higher['direction']}"
    )

    print(
        f"Bullish candles       : {higher['bullish']}"
    )

    print(
        f"Bearish candles       : {higher['bearish']}"
    )

    print(
        f"Neutral candles       : {higher['neutral']}"
    )

    print(
        f"Net change %          : "
        f"{higher['net_change_pct']:.3f}%"
    )

    print(
        f"Structure             : {higher['structure']}"
    )

    print(
        f"Momentum              : {higher['momentum']}"
    )

    print(
        f"Volatility            : {higher['volatility']}"
    )

    print()

    print("MULTI-TIMEFRAME ALIGNMENT")
    print("-" * 70)

    print(
        f"Integrated direction  : "
        f"{directional['direction']}"
    )

    print(
        f"Alignment             : "
        f"{directional['alignment']}"
    )

    print(
        f"Alignment score       : "
        f"{directional['score']:.1f}%"
    )

    print(
        f"Bullish contexts      : "
        f"{directional['bullish_contexts']}"
    )

    print(
        f"Bearish contexts      : "
        f"{directional['bearish_contexts']}"
    )

    print(
        f"Mixed contexts        : "
        f"{directional['mixed_contexts']}"
    )

    print()

    print("STRUCTURAL ALIGNMENT")
    print("-" * 70)

    print(
        f"Structure direction    : "
        f"{structural['direction']}"
    )

    print(
        f"Structure score        : "
        f"{structural['score']:.1f}%"
    )

    print()

    print("MOMENTUM ALIGNMENT")
    print("-" * 70)

    print(
        f"Dominant momentum      : "
        f"{momentum['direction']}"
    )

    print(
        f"Momentum agreement     : "
        f"{momentum['score']:.1f}%"
    )

    print()

    print("VOLATILITY ALIGNMENT")
    print("-" * 70)

    print(
        f"Dominant volatility    : "
        f"{volatility['direction']}"
    )

    print(
        f"Volatility agreement   : "
        f"{volatility['score']:.1f}%"
    )

    print()

    print("MULTI-TIMEFRAME EVIDENCE FUSION")
    print("-" * 70)

    print(
        f"Bullish evidence score : "
        f"{evidence['bullish']:.3f}"
    )

    print(
        f"Bearish evidence score : "
        f"{evidence['bearish']:.3f}"
    )

    print(
        f"Neutral evidence score : "
        f"{evidence['neutral']:.3f}"
    )

    print(
        f"Integrated direction    : "
        f"{evidence['direction']}"
    )

    print(
        f"Evidence confidence     : "
        f"{evidence['confidence']:.1f}%"
    )

    print()

    print("EXPERIENCE MEMORY")
    print("-" * 70)

    print(
        f"Observations stored     : "
        f"{counts['observations']}"
    )

    print(
        f"Resolved windows        : "
        f"{counts['resolved_windows']}"
    )

    print(
        f"Pending windows         : "
        f"{counts['pending_windows']}"
    )

    print()

    print("MULTI-TIMEFRAME INTERPRETATION")
    print("-" * 70)

    if evidence["direction"] == "bullish":
        interpretation = (
            "Multi-timeframe evidence currently favours "
            "a bullish market context."
        )

    elif evidence["direction"] == "bearish":
        interpretation = (
            "Multi-timeframe evidence currently favours "
            "a bearish market context."
        )

    else:
        interpretation = (
            "Multi-timeframe evidence is mixed and does "
            "not establish a dominant directional context."
        )

    print(
        f"Classification: {evidence['direction']}_"
        f"multi_timeframe_context"
    )

    print()
    print(interpretation)

    print()

    print("LEARNING PRINCIPLES")
    print("-" * 70)

    principles = [
        "Short, medium and higher contexts are analysed separately.",
        "Agreement between contexts strengthens evidence.",
        "Disagreement between contexts is preserved.",
        "Structure is evaluated independently from candle direction.",
        "Momentum and volatility provide context rather than automatic direction.",
        "Historical and experience memory remain separate from direct observation.",
        "Confidence measures evidence agreement rather than certainty.",
        "No single timeframe determines the market interpretation.",
        "The engine does not create an automatic trading signal.",
    ]

    for i, principle in enumerate(principles, 1):
        print(f"{i}. {principle}")

    print()

    print("CURRENT MARKET STORY")
    print("-" * 70)

    print(
        f"The v1.6 engine compares {len(contexts)} market "
        f"contexts using the available stored candle memory. "
        f"The short context is {short['direction']}, the medium "
        f"context is {medium['direction']}, and the higher "
        f"context is {higher['direction']}. "
        f"Multi-timeframe directional alignment is "
        f"{directional['score']:.1f}%. "
        f"Structural alignment is "
        f"{structural['score']:.1f}%. "
        f"The integrated multi-timeframe evidence currently "
        f"favours {evidence['direction']} with "
        f"{evidence['confidence']:.1f}% evidence agreement. "
        f"This represents agreement among observed contexts, "
        f"not certainty about future market behaviour."
    )

    print()

    print(
        "PASS: MLAI_PROJECT_STATUS.md updated."
    )

    update_project_status(
        metadata,
        len(candles),
        contexts,
        directional,
        structural,
        momentum,
        volatility,
        evidence,
        counts,
    )

    print()
    print(
        "PASS: MLAI v1.6 Multi-Timeframe Market Context "
        "Engine completed."
    )
    print("=" * 70)


if __name__ == "__main__":
    main()
