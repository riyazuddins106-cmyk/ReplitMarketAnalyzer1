import os
import pickle
from datetime import datetime, timezone


# ============================================================
# MLAI v2.3
# EVIDENCE RELIABILITY + TRUST ENGINE
#
# Purpose:
#   - Load all existing MLAI evidence memories.
#   - Measure reliability of each evidence layer.
#   - Separate availability from proven reliability.
#   - Use resolved experience only.
#   - Prevent unsupported confidence inflation.
#   - Save a persistent reliability memory.
#
# IMPORTANT:
# This engine does NOT create an automatic trading signal.
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
CALIBRATION_FILE = "mlai_calibration_memory.bin"

RELIABILITY_FILE = "mlai_reliability_memory.bin"
STATUS_FILE = "MLAI_PROJECT_STATUS.md"


# ============================================================
# HELPERS
# ============================================================

def load_pickle(filename):
    if not os.path.exists(filename):
        return None

    try:
        with open(filename, "rb") as f:
            return pickle.load(f)
    except Exception:
        return None


def save_pickle(filename, data):
    with open(filename, "wb") as f:
        pickle.dump(data, f)


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


# ============================================================
# MARKET MEMORY
# ============================================================

def extract_candles(memory):
    if isinstance(memory, list):
        return memory

    if not isinstance(memory, dict):
        return []

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


def extract_close(candle):
    if isinstance(candle, dict):
        for key in ("close", "Close", "c"):
            if key in candle:
                return safe_float(candle[key], None)

    if isinstance(candle, (list, tuple)) and len(candle) >= 5:
        return safe_float(candle[4], None)

    return None


def analyse_market(candles, window=60):
    usable = candles[-window:]

    closes = []

    for candle in usable:
        close = extract_close(candle)

        if close is not None:
            closes.append(close)

    if len(closes) < 2:
        raise ValueError("Unable to extract enough closing prices.")

    bullish = 0
    bearish = 0
    neutral = 0

    for i in range(1, len(closes)):
        if closes[i] > closes[i - 1]:
            bullish += 1
        elif closes[i] < closes[i - 1]:
            bearish += 1
        else:
            neutral += 1

    if bullish > bearish:
        direction = "bullish"
    elif bearish > bullish:
        direction = "bearish"
    else:
        direction = "neutral"

    first_close = closes[0]
    latest_close = closes[-1]

    net_move = latest_close - first_close

    if first_close:
        net_pct = net_move / first_close * 100.0
    else:
        net_pct = 0.0

    # Basic structure classification.
    half = max(1, len(closes) // 2)

    first_avg = sum(closes[:half]) / len(closes[:half])
    second_avg = sum(closes[half:]) / len(closes[half:])

    if second_avg > first_avg and direction == "bullish":
        structure = "bullish_structure"
    elif second_avg < first_avg and direction == "bearish":
        structure = "bearish_structure"
    else:
        structure = "range_structure"

    # Momentum.
    momentum = "stable"

    if len(closes) >= 12:
        old = closes[-12:-6]
        recent = closes[-6:]

        old_move = abs(old[-1] - old[0])
        recent_move = abs(recent[-1] - recent[0])

        if recent_move > old_move * 1.10:
            momentum = "increasing"
        elif recent_move < old_move * 0.90:
            momentum = "decreasing"

    # Volatility.
    volatility = "stable"

    if len(closes) >= 20:
        changes = []

        for i in range(1, len(closes)):
            if closes[i - 1] != 0:
                changes.append(
                    abs(
                        (closes[i] - closes[i - 1])
                        / closes[i - 1]
                    )
                )

        if len(changes) >= 12:
            old_vol = sum(changes[:6]) / 6
            recent_vol = sum(changes[-6:]) / 6

            if recent_vol > old_vol * 1.15:
                volatility = "expanding"
            elif recent_vol < old_vol * 0.85:
                volatility = "contracting"

    return {
        "candles": len(closes),
        "direction": direction,
        "structure": structure,
        "momentum": momentum,
        "volatility": volatility,
        "first_close": first_close,
        "latest_close": latest_close,
        "net_move": net_move,
        "net_pct": net_pct,
        "bullish": bullish,
        "bearish": bearish,
        "neutral": neutral,
    }


# ============================================================
# EXPERIENCE EXTRACTION
# ============================================================

def find_observations(memory):
    if not isinstance(memory, dict):
        return []

    for key in (
        "observations",
        "experience",
        "records",
        "memory",
    ):
        value = memory.get(key)

        if isinstance(value, list):
            return value

        if isinstance(value, dict):
            return list(value.values())

    return []


def get_outcomes(observation):
    if not isinstance(observation, dict):
        return {}

    value = observation.get("outcomes")

    if isinstance(value, dict):
        return value

    return {}


def classify(value):
    if value is None:
        return "pending"

    if isinstance(value, dict):
        for key in (
            "classification",
            "outcome",
            "direction",
            "result",
            "status",
        ):
            if key in value:
                return classify(value[key])

    text = str(value).lower().strip()

    if text in (
        "bullish",
        "confirmed",
        "up",
        "positive",
    ):
        return "bullish"

    if text in (
        "bearish",
        "not_confirmed",
        "not confirmed",
        "down",
        "negative",
    ):
        return "bearish"

    if text in (
        "neutral",
        "range",
        "mixed",
    ):
        return "neutral"

    if text in (
        "pending",
        "unresolved",
    ):
        return "pending"

    return "unknown"


def experience_statistics(memory):
    observations = find_observations(memory)

    horizons = {
        4: {"bullish": 0, "bearish": 0, "neutral": 0},
        8: {"bullish": 0, "bearish": 0, "neutral": 0},
        16: {"bullish": 0, "bearish": 0, "neutral": 0},
    }

    resolved = 0
    pending = 0

    for observation in observations:
        outcomes = get_outcomes(observation)

        for horizon in (4, 8, 16):
            value = None

            for key in (
                horizon,
                str(horizon),
                f"{horizon}c",
                f"{horizon}_candles",
            ):
                if key in outcomes:
                    value = outcomes[key]
                    break

            result = classify(value)

            if result in ("bullish", "bearish", "neutral"):
                horizons[horizon][result] += 1
                resolved += 1

            elif result == "pending":
                pending += 1

    return {
        "observations": len(observations),
        "resolved_windows": resolved,
        "pending_windows": pending,
        "horizons": horizons,
    }


# ============================================================
# RELIABILITY MODEL
# ============================================================

def calculate_reliability(
    experience_stats,
    calibration_memory,
    layer_memory,
):
    resolved = experience_stats["resolved_windows"]

    # --------------------------------------------------------
    # Experience reliability
    # --------------------------------------------------------

    if resolved == 0:
        experience_score = 0.0
        experience_level = "not_available"
    elif resolved < 5:
        experience_score = 20.0
        experience_level = "very_early"
    elif resolved < 15:
        experience_score = 40.0
        experience_level = "developing"
    elif resolved < 30:
        experience_score = 60.0
        experience_level = "moderate_sample"
    elif resolved < 60:
        experience_score = 75.0
        experience_level = "strong_sample"
    else:
        experience_score = 90.0
        experience_level = "large_sample"

    # --------------------------------------------------------
    # Calibration reliability
    # --------------------------------------------------------

    calibration = 0.0
    calibration_level = "not_available"

    if isinstance(calibration_memory, dict):
        calibration_data = calibration_memory.get(
            "calibration",
            {}
        )

        horizons = calibration_data.get(
            "horizons",
            {}
        )

        valid_errors = []

        if isinstance(horizons, dict):
            for value in horizons.values():
                if not isinstance(value, dict):
                    continue

                error = value.get("calibration_error")

                if error is not None:
                    valid_errors.append(
                        safe_float(error)
                    )

        if valid_errors:
            mean_error = sum(valid_errors) / len(valid_errors)

            calibration = max(
                0.0,
                min(
                    100.0,
                    100.0 - mean_error
                )
            )

            if calibration >= 80:
                calibration_level = "strong"
            elif calibration >= 60:
                calibration_level = "moderate"
            elif calibration >= 40:
                calibration_level = "developing"
            else:
                calibration_level = "weak"

    # --------------------------------------------------------
    # Layer availability
    # --------------------------------------------------------

    layers = {}

    for name, memory in layer_memory.items():
        if memory is None:
            layers[name] = {
                "available": False,
                "reliability": 0.0,
                "level": "unavailable",
            }
        else:
            # Availability does NOT mean proven reliability.
            if name == "experience":
                score = experience_score
                level = experience_level

            elif name == "calibration":
                score = calibration
                level = calibration_level

            elif name == "adaptive":
                if resolved == 0:
                    score = 0.0
                    level = "no_resolved_experience"
                else:
                    score = min(
                        70.0,
                        30.0 + experience_score * 0.45
                    )
                    level = "developing"

            elif name == "pattern":
                score = 50.0
                level = "historical_only"

            elif name == "multi_timeframe":
                score = 60.0
                level = "contextual"

            elif name == "regime":
                score = 55.0
                level = "contextual"

            elif name == "regime_transition":
                score = 40.0
                level = "early_state_memory"

            elif name == "regime_learning":
                score = experience_score
                level = experience_level

            elif name == "scenario":
                score = 50.0
                level = "evidence_only"

            elif name == "unified":
                score = 50.0
                level = "evidence_fusion"

            else:
                score = 0.0
                level = "unknown"

            layers[name] = {
                "available": True,
                "reliability": round(score, 2),
                "level": level,
            }

    return {
        "experience_reliability": experience_score,
        "experience_level": experience_level,
        "calibration_reliability": calibration,
        "calibration_level": calibration_level,
        "layers": layers,
    }


# ============================================================
# TRUST PROFILE
# ============================================================

def calculate_trust_profile(reliability):
    layers = reliability["layers"]

    available = [
        value["reliability"]
        for value in layers.values()
        if value["available"]
    ]

    if not available:
        overall = 0.0
    else:
        overall = sum(available) / len(available)

    if overall >= 80:
        level = "high"
    elif overall >= 60:
        level = "moderate"
    elif overall >= 40:
        level = "developing"
    elif overall > 0:
        level = "low"
    else:
        level = "not_available"

    return {
        "overall_reliability": round(overall, 2),
        "trust_level": level,
    }


# ============================================================
# SAVE MEMORY
# ============================================================

def save_reliability_memory(
    market,
    experience_stats,
    reliability,
    trust,
):
    memory = {
        "mlai_version": "2.3",
        "engine": "evidence_reliability_trust",
        "created_at": datetime.now(timezone.utc).isoformat(),

        "market_context": market,

        "experience_statistics": experience_stats,

        "reliability": reliability,

        "trust_profile": trust,

        "principles": [
            "Availability does not equal reliability.",
            "Pending experience contributes zero learned reliability.",
            "Resolved experience increases reliability gradually.",
            "Historical pattern availability is not proof of predictive accuracy.",
            "Calibration requires actual future outcomes.",
            "Small samples are explicitly classified as unreliable.",
            "Evidence layers remain separate.",
            "Overall reliability is not a trading probability.",
            "Confidence must not exceed the quality of supporting evidence.",
            "The engine does not create an automatic trading signal.",
        ],
    }

    save_pickle(RELIABILITY_FILE, memory)


# ============================================================
# STATUS DOCUMENT
# ============================================================

def update_status(
    market,
    experience_stats,
    reliability,
    trust,
):
    timestamp = datetime.now(timezone.utc).isoformat()

    lines = [
        "# MLAI PROJECT STATUS",
        "",
        f"Last updated: {timestamp}",
        "",
        "## Current Engine",
        "",
        "MLAI v2.3 Evidence Reliability + Trust Engine",
        "",
        "## Market Context",
        "",
        f"- Direction: {market['direction']}",
        f"- Structure: {market['structure']}",
        f"- Momentum: {market['momentum']}",
        f"- Volatility: {market['volatility']}",
        f"- Latest close: {market['latest_close']:.4f}",
        f"- Net change: {market['net_pct']:.3f}%",
        "",
        "## Experience",
        "",
        f"- Observations: {experience_stats['observations']}",
        f"- Resolved windows: {experience_stats['resolved_windows']}",
        f"- Pending windows: {experience_stats['pending_windows']}",
        "",
        "## Reliability",
        "",
        f"- Overall reliability: "
        f"{trust['overall_reliability']:.1f}%",
        f"- Trust level: {trust['trust_level']}",
        f"- Experience reliability: "
        f"{reliability['experience_reliability']:.1f}%",
        f"- Experience level: "
        f"{reliability['experience_level']}",
        f"- Calibration reliability: "
        f"{reliability['calibration_reliability']:.1f}%",
        f"- Calibration level: "
        f"{reliability['calibration_level']}",
        "",
        "## Evidence Layers",
        "",
    ]

    for name, data in reliability["layers"].items():
        lines.append(
            f"- {name}: "
            f"{'available' if data['available'] else 'unavailable'} | "
            f"{data['reliability']:.1f}% | "
            f"{data['level']}"
        )

    lines.extend(
        [
            "",
            "## v2.3 Principle",
            "",
            "MLAI separates evidence availability from evidence reliability.",
            "A module being present does not mean that it has demonstrated "
            "historical predictive reliability.",
            "",
        ]
    )

    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("MLAI v2.3 - LOADING MARKET MEMORY")
    print("=" * 70)
    print(f"File: {MARKET_FILE}")
    print()

    market_memory = load_pickle(MARKET_FILE)

    if market_memory is None:
        print("ERROR: market_data.bin could not be loaded.")
        return

    print("PASS: market_data.bin loaded as MLAI memory object.")
    print()

    candles = extract_candles(market_memory)

    if not candles:
        print("ERROR: No candles found.")
        return

    print(f"Found {len(candles)} stored candles.")
    print()

    if len(candles) >= 60:
        print("PASS: Using latest 60 candles.")
        market = analyse_market(candles, 60)
    else:
        print(
            f"WARNING: Only {len(candles)} candles available."
        )
        market = analyse_market(
            candles,
            len(candles)
        )

    print()
    print("Analysing latest candles...")
    print()

    # --------------------------------------------------------
    # LOAD MEMORIES
    # --------------------------------------------------------

    experience = load_pickle(EXPERIENCE_FILE)
    pattern = load_pickle(PATTERN_FILE)
    adaptive = load_pickle(ADAPTIVE_FILE)
    mtf = load_pickle(MTF_FILE)
    regime = load_pickle(REGIME_FILE)
    transition = load_pickle(TRANSITION_FILE)
    regime_learning = load_pickle(REGIME_LEARNING_FILE)
    unified = load_pickle(UNIFIED_FILE)
    scenario = load_pickle(SCENARIO_FILE)
    calibration = load_pickle(CALIBRATION_FILE)

    print("PASS: Loading MLAI evidence memories...")

    layer_memory = {
        "experience": experience,
        "pattern": pattern,
        "adaptive": adaptive,
        "multi_timeframe": mtf,
        "regime": regime,
        "regime_transition": transition,
        "regime_learning": regime_learning,
        "unified": unified,
        "scenario": scenario,
        "calibration": calibration,
    }

    print("PASS: Evidence memories loaded.")
    print()

    # --------------------------------------------------------
    # EXPERIENCE
    # --------------------------------------------------------

    if experience is None:
        experience = {
            "observations": []
        }

    experience_stats = experience_statistics(
        experience
    )

    # --------------------------------------------------------
    # RELIABILITY
    # --------------------------------------------------------

    reliability = calculate_reliability(
        experience_stats,
        calibration,
        layer_memory,
    )

    trust = calculate_trust_profile(
        reliability
    )

    save_reliability_memory(
        market,
        experience_stats,
        reliability,
        trust,
    )

    print("PASS: Calculating evidence reliability...")
    print("PASS: Reliability profile completed.")
    print()
    print(
        f"PASS: {RELIABILITY_FILE} saved."
    )
    print()

    # ========================================================
    # REPORT
    # ========================================================

    print("=" * 70)
    print(
        "MLAI v2.3 EVIDENCE RELIABILITY + TRUST ENGINE"
    )
    print("=" * 70)
    print()

    print("CURRENT MARKET CONTEXT")
    print("-" * 70)
    print(f"Direction              : {market['direction']}")
    print(f"Structure              : {market['structure']}")
    print(f"Momentum               : {market['momentum']}")
    print(f"Volatility             : {market['volatility']}")
    print(
        f"Latest price           : "
        f"{market['latest_close']:.4f}"
    )
    print(
        f"Net change %           : "
        f"{market['net_pct']:.3f}%"
    )
    print()

    print("EXPERIENCE STATUS")
    print("-" * 70)
    print(
        f"Observations stored    : "
        f"{experience_stats['observations']}"
    )
    print(
        f"Resolved windows       : "
        f"{experience_stats['resolved_windows']}"
    )
    print(
        f"Pending windows        : "
        f"{experience_stats['pending_windows']}"
    )
    print()

    print("RELIABILITY PROFILE")
    print("-" * 70)
    print(
        f"Overall reliability    : "
        f"{trust['overall_reliability']:.1f}%"
    )
    print(
        f"Trust level            : "
        f"{trust['trust_level']}"
    )
    print()

    print("EVIDENCE LAYER RELIABILITY")
    print("-" * 70)

    for name, data in reliability["layers"].items():
        print(
            f"{name:24} | "
            f"{'available' if data['available'] else 'unavailable':12} | "
            f"{data['reliability']:6.1f}% | "
            f"{data['level']}"
        )

    print()

    print("EXPERIENCE RELIABILITY")
    print("-" * 70)
    print(
        f"Reliability            : "
        f"{reliability['experience_reliability']:.1f}%"
    )
    print(
        f"Level                  : "
        f"{reliability['experience_level']}"
    )
    print()

    print("CALIBRATION RELIABILITY")
    print("-" * 70)
    print(
        f"Reliability            : "
        f"{reliability['calibration_reliability']:.1f}%"
    )
    print(
        f"Level                  : "
        f"{reliability['calibration_level']}"
    )
    print()

    print("TRUST INTERPRETATION")
    print("-" * 70)

    if trust["trust_level"] == "not_available":
        print(
            "MLAI does not yet have enough resolved historical "
            "experience to establish meaningful reliability."
        )

    elif trust["trust_level"] == "low":
        print(
            "MLAI has evidence layers available, but historical "
            "reliability remains limited."
        )

    elif trust["trust_level"] == "developing":
        print(
            "MLAI reliability is developing as resolved outcomes "
            "accumulate."
        )

    elif trust["trust_level"] == "moderate":
        print(
            "MLAI has a moderate reliability profile, but additional "
            "resolved outcomes are still required."
        )

    else:
        print(
            "MLAI has a stronger historical reliability profile."
        )

    print()

    print("IMPORTANT")
    print("-" * 70)
    print(
        "A reliability score is NOT a prediction probability."
    )
    print(
        "A high evidence availability does NOT automatically mean "
        "high historical accuracy."
    )
    print(
        "Only resolved future outcomes can establish learned "
        "reliability."
    )

    print()

    print("LEARNING PRINCIPLES")
    print("-" * 70)
    print(
        "1. Evidence availability and reliability are separate."
    )
    print(
        "2. Pending outcomes contribute zero learned reliability."
    )
    print(
        "3. Small samples are explicitly marked as unreliable."
    )
    print(
        "4. Historical patterns are contextual until validated."
    )
    print(
        "5. Calibration requires actual future market outcomes."
    )
    print(
        "6. Different evidence layers retain separate reliability."
    )
    print(
        "7. Overall trust is not a probability of future direction."
    )
    print(
        "8. Reliability cannot guarantee future market behaviour."
    )
    print(
        "9. No single module controls the interpretation."
    )
    print(
        "10. The engine does not create an automatic trading signal."
    )

    print()

    print("CURRENT MARKET STORY")
    print("-" * 70)

    print(
        f"MLAI v2.3 evaluates the current market as "
        f"{market['direction']} with "
        f"{market['structure']}."
    )

    print(
        f"The system has "
        f"{experience_stats['observations']} stored observations, "
        f"{experience_stats['resolved_windows']} resolved outcome "
        f"windows and "
        f"{experience_stats['pending_windows']} pending windows."
    )

    print(
        f"The current overall evidence reliability profile is "
        f"{trust['overall_reliability']:.1f}% with a "
        f"{trust['trust_level']} trust classification."
    )

    print(
        "This reliability profile describes the maturity of MLAI's "
        "evidence and learning layers. It is not a prediction of "
        "future price movement."
    )

    print()

    update_status(
        market,
        experience_stats,
        reliability,
        trust,
    )

    print(
        "PASS: MLAI_PROJECT_STATUS.md updated."
    )

    print()
    print("=" * 70)
    print(
        "PASS: MLAI v2.3 Evidence Reliability + "
        "Trust Engine completed."
    )
    print("=" * 70)


if __name__ == "__main__":
    main()
