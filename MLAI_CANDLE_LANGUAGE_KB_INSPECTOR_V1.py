"""
MLAI CANDLE LANGUAGE KB V2
FOUNDATIONAL MARKET LANGUAGE KNOWLEDGE BUILDER

Purpose
-------
Build the foundational candle-language knowledge required by the
MLAI Market Language Brain specification.

IMPORTANT
---------
This file builds KNOWLEDGE only.

It does NOT:
    - learn from future market data
    - perform prediction
    - modify market_data.bin
    - modify market_experience.bin
    - modify existing MLAI v4.x engines
    - claim BUY / SELL signals
    - claim hidden liquidity
    - claim trader intent

Knowledge and historical experience remain separate.

Output
------
    candle_language_v2.bin
    candle_language_v2.index.json

The binary is accompanied by an auditable JSON index containing:
    - schema version
    - record count
    - category counts
    - SHA256
    - source information
    - vocabulary inventory
"""

from __future__ import annotations

import hashlib
import json
import os
import pickle
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


# ============================================================
# CONFIGURATION
# ============================================================

VERSION = "2.0"
SCHEMA_VERSION = "2.0"

KB_FILE = Path("candle_language_v2.bin")
INDEX_FILE = Path("candle_language_v2.index.json")


# ============================================================
# HELPERS
# ============================================================

def utc_now():
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)

    return h.hexdigest()


def make_rule(
    rule_id,
    key,
    category,
    meaning,
    technical_definition,
    human_meaning,
    dependencies=None,
    source="MLAI foundational specification",
):
    return {
        "id": rule_id,
        "key": key,
        "category": category,
        "meaning": meaning,
        "technical_definition": technical_definition,
        "human_meaning": human_meaning,
        "dependencies": dependencies or [],
        "source": source,
        "status": "candidate",
    }


# ============================================================
# KNOWLEDGE SOURCES
# ============================================================

SOURCES = [
    {
        "id": "NISON_2001",
        "title": "Japanese Candlestick Charting Techniques, Second Edition",
        "author": "Steve Nison",
        "role": "candlestick interpretation",
    },
    {
        "id": "BULKOWSKI_2008",
        "title": "Encyclopedia of Candlestick Charts",
        "author": "Thomas N. Bulkowski",
        "role": "candlestick identification and statistical behavior",
    },
    {
        "id": "MURPHY_1999",
        "title": "Technical Analysis of the Financial Markets",
        "author": "John J. Murphy",
        "role": "trend, chart patterns, support/resistance and technical analysis",
    },
    {
        "id": "WILDER_1978",
        "title": "New Concepts in Technical Trading Systems",
        "author": "J. Welles Wilder Jr.",
        "role": "RSI, ATR and directional/momentum concepts",
    },
    {
        "id": "BOLLINGER_2001",
        "title": "Bollinger on Bollinger Bands",
        "author": "John Bollinger",
        "role": "Bollinger Bands and volatility-aware interpretation",
    },
]


# ============================================================
# CANDLE ANATOMY
# ============================================================

CANDLE_ANATOMY = {
    "OHLC": {
        "open": "Opening price of the candle.",
        "high": "Highest traded price represented by the candle.",
        "low": "Lowest traded price represented by the candle.",
        "close": "Closing price of the completed candle.",
    },

    "body": "abs(close - open)",

    "range": "high - low",

    "upper_wick":
        "high - max(open, close)",

    "lower_wick":
        "min(open, close) - low",

    "body_to_range":
        "body / range when range > 0",

    "upper_wick_to_body":
        "upper_wick / body when body > 0",

    "lower_wick_to_body":
        "lower_wick / body when body > 0",

    "close_position":
        "(close - low) / (high - low) when range > 0",
}


# ============================================================
# CANDLE VOCABULARY
# ============================================================

CANDLE_TYPES = [
    "bullish",
    "bearish",
    "neutral",
    "doji",
    "large_body",
    "medium_body",
    "small_body",
    "long_upper_wick",
    "long_lower_wick",
    "two_sided_rejection",
    "marubozu_like",
    "hammer_like",
    "inverted_hammer_like",
    "shooting_star_like",
    "hanging_man_like",
    "inside_bar",
    "outside_bar",
    "expansion_candle",
    "compression_candle",
]


# ============================================================
# PATTERN VOCABULARY
# ============================================================

PATTERNS = [
    "Doji",
    "Hammer",
    "Hanging Man",
    "Inverted Hammer",
    "Shooting Star",
    "Bullish Engulfing",
    "Bearish Engulfing",
    "Harami",
    "Morning Star",
    "Evening Star",
    "Three White Soldiers",
    "Three Black Crows",
    "Piercing Pattern",
    "Dark Cloud Cover",
    "Inside Bar",
    "Outside Bar",
    "Double Top",
    "Double Bottom",
    "Head and Shoulders",
    "Inverse Head and Shoulders",
    "Triangle",
    "Rectangle",
    "Flag",
    "Pennant",
    "Channel",
]


# ============================================================
# SEQUENCE VOCABULARY
# ============================================================

SEQUENCE_STATES = [
    "selling",
    "buying",
    "selling_slowing",
    "buying_slowing",
    "rejection",
    "recovery",
    "pullback",
    "retracement",
    "momentum_loss",
    "exhaustion",
    "consolidation",
    "compression",
    "expansion",
    "breakout_candidate",
    "breakdown_candidate",
    "failed_breakout",
    "failed_breakdown",
    "retest",
    "continuation",
    "transition",
    "reversal_candidate",
    "impulse",
    "correction",
]


# ============================================================
# MARKET STRUCTURE
# ============================================================

STRUCTURE_STATES = [
    "HH",
    "HL",
    "LH",
    "LL",
    "uptrend",
    "downtrend",
    "range",
    "consolidation",
    "BOS_BULLISH",
    "BOS_BEARISH",
    "CHoCH_BULLISH",
    "CHoCH_BEARISH",
    "structural_failure",
    "structural_transition",
    "continuation",
    "reversal_candidate",
]


# ============================================================
# SUPPORT / RESISTANCE
# ============================================================

SUPPORT_RESISTANCE_TYPES = [
    "support_area",
    "resistance_area",
    "prior_swing_low_area",
    "prior_swing_high_area",
    "repeated_reaction_area",
    "breakout_area",
    "breakdown_area",
    "retest_area",
    "failed_support_area",
    "failed_resistance_area",
    "role_reversal_area",
]


SUPPORT_RESISTANCE_ATTRIBUTES = [
    "price_low",
    "price_high",
    "creation_reason",
    "test_count",
    "reaction_strength",
    "freshness",
    "break_status",
    "retest_status",
    "failure_status",
]


# ============================================================
# VOLATILITY
# ============================================================

VOLATILITY_STATES = [
    "low_volatility",
    "normal_volatility",
    "high_volatility",
    "volatility_expansion",
    "volatility_contraction",
    "ATR_relative_expansion",
    "ATR_relative_contraction",
    "Bollinger_bandwidth_expansion",
    "Bollinger_bandwidth_contraction",
]


# ============================================================
# MOMENTUM
# ============================================================

MOMENTUM_STATES = [
    "momentum_increase",
    "momentum_decrease",
    "acceleration",
    "deceleration",
    "directional_strength",
    "weak_directional_strength",
    "follow_through",
    "failed_push",
    "exhaustion",
    "momentum_disagreement",
]


# ============================================================
# REGIMES
# ============================================================

REGIMES = [
    "trending",
    "ranging",
    "high_volatility",
    "low_volatility",
    "volatility_expansion",
    "volatility_contraction",
    "transitioning",
    "strong_directional_movement",
    "weak_directional_movement",
]


# ============================================================
# LIQUIDITY PROXIES
# ============================================================

LIQUIDITY_PROXIES = [
    "equal_highs",
    "equal_lows",
    "prior_high",
    "prior_low",
    "sweep_like_movement",
    "rejection_after_level_break",
    "false_break_behavior",
]


# ============================================================
# SUPPLY / DEMAND OBSERVABLE PROXIES
# ============================================================

SUPPLY_DEMAND_PROXIES = [
    "strong_movement_away",
    "repeated_reaction",
    "fresh_reaction_area",
    "retest",
    "weakening_reaction",
    "zone_failure",
    "return_to_reaction_area",
]


# ============================================================
# CONTEXT
# ============================================================

CONTEXT_FIELDS = [
    "instrument",
    "timeframe",
    "session",
    "trend",
    "range_state",
    "location",
    "previous_movement",
    "structure",
    "volatility",
    "momentum",
    "volume",
    "recent_reactions",
    "higher_timeframe_context",
]


# ============================================================
# SAFETY / SCIENTIFIC RULES
# ============================================================

RULES = [

    make_rule(
        "R001",
        "completed_candles_only",
        "causality",
        "Only completed candles may be interpreted as completed candle states.",
        "Current candle is eligible only after its close.",
        "The system must not treat an unfinished candle as a completed observation.",
        ["timestamp", "close"],
    ),

    make_rule(
        "R002",
        "future_outcomes_are_targets",
        "causality",
        "Future returns, highs, lows, MFE, MAE and future events are targets only.",
        "Future price movement tells us what happened later; it cannot be used to describe the current state.",
        ["future_data"],
    ),

    make_rule(
        "R003",
        "pattern_is_description",
        "interpretation",
        "A named candle or chart pattern describes observed geometry or sequence.",
        "A pattern name describes what happened; it does not automatically mean the market will rise or fall.",
        ["patterns"],
    ),

    make_rule(
        "R004",
        "context_required",
        "interpretation",
        "Pattern interpretation must consider context.",
        "The same candle can mean something different depending on trend, location, structure, volatility and momentum.",
        ["context"],
    ),

    make_rule(
        "R005",
        "historical_evidence_not_certainty",
        "prediction",
        "Historical frequency is evidence, not certainty.",
        "Past behavior can change the probability of a scenario but cannot guarantee the next move.",
        ["historical_experience"],
    ),

    make_rule(
        "R006",
        "no_hidden_order_claims",
        "observability",
        "OHLCV does not directly expose hidden orders or exact participant intent.",
        "MLAI may describe observable price behavior but must not claim to see hidden institutional orders.",
        ["OHLCV"],
    ),

    make_rule(
        "R007",
        "support_resistance_are_areas",
        "support_resistance",
        "Support and resistance are represented as reaction areas rather than magical exact prices.",
        "A support or resistance zone represents an area where price previously reacted.",
        ["swing_points", "reactions"],
    ),

    make_rule(
        "R008",
        "supply_demand_is_proxy",
        "supply_demand",
        "Supply and demand concepts must be based only on observable price behavior.",
        "MLAI may describe strong movement away from a reaction area, but must not claim invisible order flow.",
        ["price_behavior"],
    ),

    make_rule(
        "R009",
        "liquidity_is_price_proxy",
        "liquidity",
        "Liquidity representation without depth data is restricted to price-derived proxies.",
        "Equal highs, equal lows and sweep-like movements may be represented without claiming hidden orders.",
        ["OHLC"],
    ),

    make_rule(
        "R010",
        "HH_HL_bullish_structure",
        "structure",
        "Repeated higher highs and higher lows describe bullish structural behavior.",
        "The market is maintaining higher structural highs and lows.",
        ["HH", "HL"],
    ),

    make_rule(
        "R011",
        "LH_LL_bearish_structure",
        "structure",
        "Repeated lower highs and lower lows describe bearish structural behavior.",
        "The market is maintaining lower structural highs and lows.",
        ["LH", "LL"],
    ),

    make_rule(
        "R012",
        "BOS_is_structural_event",
        "structure",
        "BOS represents a structural break according to the causal structure engine.",
        "Price has broken a previously relevant structural level.",
        ["swing_structure"],
    ),

    make_rule(
        "R013",
        "CHoCH_is_transition",
        "structure",
        "CHoCH represents a possible structural transition according to the causal structure engine.",
        "The previous structural behavior may be changing, but this is not automatically a confirmed reversal.",
        ["swing_structure"],
    ),

    make_rule(
        "R014",
        "probability_requires_evidence",
        "probability",
        "Probabilities must be derived from observed evidence.",
        "A visually strong pattern must not automatically receive a high probability.",
        ["historical_experience"],
    ),

    make_rule(
        "R015",
        "small_sample_warning",
        "probability",
        "Small historical samples require uncertainty or reduced confidence.",
        "Three or five examples are not enough to justify strong historical confidence.",
        ["sample_count"],
    ),

    make_rule(
        "R016",
        "knowledge_separate_from_experience",
        "architecture",
        "Foundational definitions and learned historical statistics are separate information types.",
        "Knowledge tells MLAI what a pattern or structure is; experience tells MLAI how comparable cases behaved.",
        ["knowledge", "experience"],
    ),

    make_rule(
        "R017",
        "confirmation_not_prediction",
        "reasoning",
        "Confirmation conditions describe evidence that would strengthen a scenario.",
        "A confirmation condition is not a guarantee; it is a measurable event that would increase support for a scenario.",
        ["scenario_reasoning"],
    ),

    make_rule(
        "R018",
        "invalidation_not_guarantee",
        "reasoning",
        "Invalidation conditions identify when a current interpretation becomes inconsistent with observed structure.",
        "An invalidation condition means the current interpretation has weakened or failed; it does not guarantee the opposite direction.",
        ["scenario_reasoning"],
    ),

    make_rule(
        "R019",
        "multi_timeframe_separation",
        "causality",
        "Each timeframe must maintain its own causal history.",
        "A bullish five-minute move does not automatically mean a higher-timeframe reversal.",
        ["multi_timeframe"],
    ),

    make_rule(
        "R020",
        "human_language_traceability",
        "explanation",
        "Every human-language statement must be traceable to structured data or measured historical evidence.",
        "MLAI must explain only what its measured inputs support.",
        ["structured_state"],
    ),
]


# ============================================================
# HUMAN LANGUAGE DEFINITIONS
# ============================================================

HUMAN_TRANSLATIONS = {

    "bullish":
        "The candle closed above its open, showing upward net price displacement.",

    "bearish":
        "The candle closed below its open, showing downward net price displacement.",

    "neutral":
        "The candle produced little net directional displacement relative to its range.",

    "long_upper_wick":
        "Price explored higher levels but moved back down before the candle closed.",

    "long_lower_wick":
        "Price explored lower levels but recovered before the candle closed.",

    "large_body":
        "The candle produced relatively large net movement compared with the chosen recent reference.",

    "small_body":
        "The candle produced relatively limited net movement and may indicate hesitation or balance.",

    "compression":
        "Recent price movement has contracted relative to its recent reference range or volatility.",

    "expansion":
        "Recent price movement has increased relative to its recent reference range or volatility.",

    "rejection":
        "Price moved into an area and then moved away before the candle or sequence completed.",

    "pullback":
        "Price is temporarily moving against the immediately preceding directional movement.",

    "retracement":
        "Price is giving back part of a previous movement without necessarily changing the larger structure.",

    "momentum_loss":
        "Directional movement is continuing but appears weaker than earlier movement.",

    "exhaustion":
        "The recent directional movement shows signs of losing strength or follow-through.",

    "consolidation":
        "Price is moving repeatedly in both directions without strong directional progression.",

    "breakout_candidate":
        "Price is approaching or testing a boundary where a structural break may occur.",

    "failed_breakout":
        "Price moved beyond a relevant boundary but did not maintain the break.",

    "retest":
        "Price has returned to a previously broken or reacted-to area for another test.",

    "HH":
        "Price has formed a higher structural high relative to the relevant prior confirmed high.",

    "HL":
        "Price has formed a higher structural low relative to the relevant prior confirmed low.",

    "LH":
        "Price has formed a lower structural high relative to the relevant prior confirmed high.",

    "LL":
        "Price has formed a lower structural low relative to the relevant prior confirmed low.",

    "BOS_BULLISH":
        "Price has broken a relevant structural level in the bullish direction according to the causal structure rules.",

    "BOS_BEARISH":
        "Price has broken a relevant structural level in the bearish direction according to the causal structure rules.",

    "CHoCH_BULLISH":
        "The causal structure shows a possible transition toward bullish behavior.",

    "CHoCH_BEARISH":
        "The causal structure shows a possible transition toward bearish behavior.",

    "support_area":
        "An area where previous price behavior indicates repeated or meaningful lower-price reaction.",

    "resistance_area":
        "An area where previous price behavior indicates repeated or meaningful higher-price reaction.",

    "role_reversal_area":
        "An area whose observed role changed after a break and subsequent retest.",

    "high_volatility":
        "Recent price movement is large relative to the selected volatility reference.",

    "low_volatility":
        "Recent price movement is small relative to the selected volatility reference.",

    "momentum_increase":
        "Directional movement is becoming stronger relative to the selected recent reference.",

    "momentum_decrease":
        "Directional movement is becoming weaker relative to the selected recent reference.",

    "trending":
        "Price is showing persistent directional structural progression.",

    "ranging":
        "Price is repeatedly moving between relatively defined boundaries without persistent directional progression.",

    "equal_highs":
        "Multiple relevant highs have formed near a similar price area.",

    "equal_lows":
        "Multiple relevant lows have formed near a similar price area.",

    "sweep_like_movement":
        "Price moved beyond a previously relevant high or low and subsequently moved back, based only on observable price behavior.",
}


# ============================================================
# BUILD RECORDS
# ============================================================

def build_records():

    records = []

    # --------------------------------------------------------
    # CANDLE ANATOMY
    # --------------------------------------------------------

    for name, formula in CANDLE_ANATOMY.items():

        records.append({
            "type": "definition",
            "category": "candle_anatomy",
            "key": name,
            "technical_definition": formula,
            "human_meaning": (
                HUMAN_TRANSLATIONS.get(
                    name,
                    f"Technical candle-anatomy quantity: {name}."
                )
            ),
            "status": "validated_definition",
        })

    # --------------------------------------------------------
    # CANDLE TYPES
    # --------------------------------------------------------

    for name in CANDLE_TYPES:

        records.append({
            "type": "vocabulary",
            "category": "candle_type",
            "key": name,
            "human_meaning": HUMAN_TRANSLATIONS.get(
                name,
                f"Observable candle classification: {name}."
            ),
            "interpretation_rule":
                "Classification must be derived from measurable OHLC relationships and recent reference values.",
            "status": "candidate",
        })

    # --------------------------------------------------------
    # PATTERNS
    # --------------------------------------------------------

    for name in PATTERNS:

        records.append({
            "type": "pattern",
            "category": "candlestick_or_chart_pattern",
            "key": name,
            "human_meaning":
                f"{name} is a descriptive candle or chart-sequence pattern. "
                "It does not automatically imply a future direction.",
            "prediction_rule":
                "Pattern meaning must be conditioned on context and historical experience.",
            "status": "candidate",
        })

    # --------------------------------------------------------
    # SEQUENCES
    # --------------------------------------------------------

    for name in SEQUENCE_STATES:

        records.append({
            "type": "sequence_state",
            "category": "sequence",
            "key": name,
            "human_meaning": HUMAN_TRANSLATIONS.get(
                name,
                f"The current candle sequence is classified as {name}."
            ),
            "status": "candidate",
        })

    # --------------------------------------------------------
    # STRUCTURE
    # --------------------------------------------------------

    for name in STRUCTURE_STATES:

        records.append({
            "type": "structure_state",
            "category": "market_structure",
            "key": name,
            "human_meaning": HUMAN_TRANSLATIONS.get(
                name,
                f"Structural market state: {name}."
            ),
            "causality":
                "Structural states must be generated only when the required swing information was causally available.",
            "status": "candidate",
        })

    # --------------------------------------------------------
    # SUPPORT / RESISTANCE
    # --------------------------------------------------------

    for name in SUPPORT_RESISTANCE_TYPES:

        records.append({
            "type": "context_area",
            "category": "support_resistance",
            "key": name,
            "human_meaning": HUMAN_TRANSLATIONS.get(
                name,
                f"Observable price-reaction area classified as {name}."
            ),
            "required_attributes": SUPPORT_RESISTANCE_ATTRIBUTES,
            "status": "candidate",
        })

    # --------------------------------------------------------
    # VOLATILITY
    # --------------------------------------------------------

    for name in VOLATILITY_STATES:

        records.append({
            "type": "state",
            "category": "volatility",
            "key": name,
            "human_meaning":
                f"Volatility state: {name}. It describes movement magnitude, not future direction.",
            "status": "candidate",
        })

    # --------------------------------------------------------
    # MOMENTUM
    # --------------------------------------------------------

    for name in MOMENTUM_STATES:

        records.append({
            "type": "state",
            "category": "momentum",
            "key": name,
            "human_meaning":
                HUMAN_TRANSLATIONS.get(
                    name,
                    f"Momentum condition: {name}."
                ),
            "status": "candidate",
        })

    # --------------------------------------------------------
    # REGIME
    # --------------------------------------------------------

    for name in REGIMES:

        records.append({
            "type": "regime",
            "category": "market_regime",
            "key": name,
            "human_meaning":
                HUMAN_TRANSLATIONS.get(
                    name,
                    f"Market regime classification: {name}."
                ),
            "status": "candidate",
        })

    # --------------------------------------------------------
    # LIQUIDITY PROXIES
    # --------------------------------------------------------

    for name in LIQUIDITY_PROXIES:

        records.append({
            "type": "observable_proxy",
            "category": "liquidity_proxy",
            "key": name,
            "human_meaning":
                HUMAN_TRANSLATIONS.get(
                    name,
                    f"Price-derived liquidity proxy: {name}."
                ),
            "restriction":
                "This is an observable price proxy and does not prove hidden orders or trader intent.",
            "status": "candidate",
        })

    # --------------------------------------------------------
    # SUPPLY / DEMAND PROXIES
    # --------------------------------------------------------

    for name in SUPPLY_DEMAND_PROXIES:

        records.append({
            "type": "observable_proxy",
            "category": "supply_demand_proxy",
            "key": name,
            "human_meaning":
                f"Observable price-behavior proxy related to reaction-area behavior: {name}.",
            "restriction":
                "This does not prove hidden institutional supply or demand.",
            "status": "candidate",
        })

    # --------------------------------------------------------
    # CONTEXT
    # --------------------------------------------------------

    for name in CONTEXT_FIELDS:

        records.append({
            "type": "context_field",
            "category": "context",
            "key": name,
            "human_meaning":
                f"Context dimension used to interpret market behavior: {name}.",
            "status": "candidate",
        })

    # --------------------------------------------------------
    # SCIENTIFIC RULES
    # --------------------------------------------------------

    for rule in RULES:
        records.append({
            "type": "rule",
            "category": rule["category"],
            **rule,
        })

    return records


# ============================================================
# VALIDATION
# ============================================================

def validate_records(records):

    errors = []

    required_categories = {
        "candle_anatomy",
        "candle_type",
        "candlestick_or_chart_pattern",
        "sequence",
        "market_structure",
        "support_resistance",
        "volatility",
        "momentum",
        "market_regime",
        "liquidity_proxy",
        "supply_demand_proxy",
        "context",
        "causality",
        "probability",
        "architecture",
        "interpretation",
        "reasoning",
        "explanation",
    }

    found_categories = {
        r.get("category")
        for r in records
    }

    for category in required_categories:
        if category not in found_categories:
            errors.append(
                f"Missing required category: {category}"
            )

    required_keys = {
        "HH",
        "HL",
        "LH",
        "LL",
        "BOS_BULLISH",
        "BOS_BEARISH",
        "CHoCH_BULLISH",
        "CHoCH_BEARISH",
        "support_area",
        "resistance_area",
        "retest",
        "failed_breakout",
        "momentum_increase",
        "momentum_decrease",
        "trending",
        "ranging",
        "equal_highs",
        "equal_lows",
        "hammer_like",
        "doji",
        "inside_bar",
        "outside_bar",
    }

    found_keys = {
        r.get("key")
        for r in records
    }

    for key in required_keys:
        if key not in found_keys:
            errors.append(
                f"Missing required vocabulary/state: {key}"
            )

    return errors


# ============================================================
# BUILD INDEX
# ============================================================

def build_index(records):

    category_counts = Counter(
        r.get("category", "unknown")
        for r in records
    )

    type_counts = Counter(
        r.get("type", "unknown")
        for r in records
    )

    return {
        "format": "MLAI_CANDLE_LANGUAGE_KB",
        "version": VERSION,
        "schema_version": SCHEMA_VERSION,
        "purpose":
            "Foundational market-language knowledge for MLAI.",
        "created_utc": utc_now(),
        "record_count": len(records),
        "category_counts": dict(sorted(category_counts.items())),
        "type_counts": dict(sorted(type_counts.items())),
        "source_count": len(SOURCES),
        "sources": SOURCES,
        "candle_types": CANDLE_TYPES,
        "patterns": PATTERNS,
        "sequence_states": SEQUENCE_STATES,
        "structure_states": STRUCTURE_STATES,
        "support_resistance_types": SUPPORT_RESISTANCE_TYPES,
        "volatility_states": VOLATILITY_STATES,
        "momentum_states": MOMENTUM_STATES,
        "regimes": REGIMES,
        "liquidity_proxies": LIQUIDITY_PROXIES,
        "supply_demand_proxies": SUPPLY_DEMAND_PROXIES,
        "context_fields": CONTEXT_FIELDS,
        "candle_anatomy": CANDLE_ANATOMY,
    }


# ============================================================
# WRITE BINARY
# ============================================================

def write_binary(records):

    payload = {
        "format": "MLAI_CANDLE_LANGUAGE_KB",
        "version": VERSION,
        "schema_version": SCHEMA_VERSION,
        "created_utc": utc_now(),
        "sources": SOURCES,
        "records": records,
    }

    with KB_FILE.open("wb") as f:
        pickle.dump(
            payload,
            f,
            protocol=pickle.HIGHEST_PROTOCOL,
        )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 100)
    print("MLAI CANDLE LANGUAGE KB V2 — FOUNDATIONAL KNOWLEDGE BUILDER")
    print("=" * 100)

    print()
    print("PURPOSE")
    print("-" * 100)
    print("Building foundational market-language knowledge.")
    print("No market data is modified.")
    print("No historical experience is created.")
    print("No prediction model is changed.")
    print()

    print("=" * 100)
    print("BUILDING KNOWLEDGE")
    print("=" * 100)

    records = build_records()

    print(f"Records generated : {len(records)}")

    print()
    print("=" * 100)
    print("VALIDATION")
    print("=" * 100)

    errors = validate_records(records)

    if errors:

        print("STATUS : FAIL")
        print()

        for error in errors:
            print("ERROR:", error)

        raise SystemExit(
            "Knowledge-base validation failed."
        )

    print("STATUS : PASS")
    print("Required foundational categories present.")
    print("Required structural vocabulary present.")
    print("Support/resistance vocabulary present.")
    print("Causality rules present.")
    print("Observable liquidity/supply-demand restrictions present.")

    print()
    print("=" * 100)
    print("WRITING BINARY KNOWLEDGE BASE")
    print("=" * 100)

    write_binary(records)

    print(f"KB file : {KB_FILE}")
    print("Status  : CREATED")

    print()
    print("=" * 100)
    print("HASHING")
    print("=" * 100)

    kb_hash = sha256_file(KB_FILE)

    print("KB SHA256:")
    print(kb_hash)

    print()
    print("=" * 100)
    print("CREATING AUDIT INDEX")
    print("=" * 100)

    index = build_index(records)
    index["kb_sha256"] = kb_hash

    with INDEX_FILE.open(
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            index,
            f,
            indent=2,
            ensure_ascii=False,
        )

    print(f"Index file : {INDEX_FILE}")
    print("Status     : CREATED")

    print()
    print("=" * 100)
    print("FOUNDATION SUMMARY")
    print("=" * 100)

    print(f"Version              : {VERSION}")
    print(f"Schema               : {SCHEMA_VERSION}")
    print(f"Records              : {len(records)}")
    print(f"Candle types         : {len(CANDLE_TYPES)}")
    print(f"Patterns             : {len(PATTERNS)}")
    print(f"Sequence states      : {len(SEQUENCE_STATES)}")
    print(f"Structure states     : {len(STRUCTURE_STATES)}")
    print(f"S/R area types       : {len(SUPPORT_RESISTANCE_TYPES)}")
    print(f"Volatility states    : {len(VOLATILITY_STATES)}")
    print(f"Momentum states      : {len(MOMENTUM_STATES)}")
    print(f"Regimes              : {len(REGIMES)}")
    print(f"Liquidity proxies    : {len(LIQUIDITY_PROXIES)}")
    print(f"Supply/demand proxy  : {len(SUPPLY_DEMAND_PROXIES)}")
    print(f"Context fields       : {len(CONTEXT_FIELDS)}")
    print(f"Scientific rules     : {len(RULES)}")

    print()
    print("=" * 100)
    print("IMPORTANT SEPARATION")
    print("=" * 100)

    print("Knowledge base      : FOUNDATIONAL DEFINITIONS")
    print("Historical memory   : NOT CREATED")
    print("Prediction          : NOT CREATED")
    print("Retrieval           : NOT MODIFIED")
    print("MLAI v4.x           : NOT MODIFIED")
    print("market_data.bin     : NOT MODIFIED")

    print()
    print("=" * 100)
    print("FINAL STATUS")
    print("=" * 100)

    print("FOUNDATION KB BUILD : PASS")
    print()
    print("Next gate:")
    print("Build a READ-ONLY FOUNDATION INSPECTOR V2.")
    print()
    print("After the inspector passes:")
    print("1. Audit market_data.bin")
    print("2. Verify canonical candle schema")
    print("3. Build causal candle-language parser")
    print("4. Then build chronological experience memory")
    print()
    print("=" * 100)


if __name__ == "__main__":
    main()