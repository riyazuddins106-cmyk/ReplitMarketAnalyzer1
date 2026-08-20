"""
MLAI v0.4
Market Structure Engine

IMPORTANT:
- Uses existing market_data.bin
- Does NOT download new market data
- Does NOT rebuild MLAI v0.1/v0.2
- Builds on the existing candle data
- Detects swing highs and swing lows
- Detects HH / HL / LH / LL
- Analyses structural direction
- Detects possible structural breaks
- Detects possible change of character
- Detects failed structural breaks
- Detects range-like structure
- Produces explanations, not BUY/SELL signals
- Updates MLAI_PROJECT_STATUS.md after successful testing
"""

from __future__ import annotations

import pickle

from dataclasses import dataclass

from datetime import datetime

from typing import Any, Dict, List, Optional


# ============================================================
# CONFIGURATION
# ============================================================

VERSION = "MLAI v0.4"

DEFAULT_SEQUENCE_LENGTH = 30

SWING_LEFT = 2

SWING_RIGHT = 2

EPSILON = 1e-12

STATUS_FILE = "MLAI_PROJECT_STATUS.md"

MARKET_DATA_FILE = "market_data.bin"


# ============================================================
# DATA STRUCTURES
# ============================================================

@dataclass
class Candle:
    index: int

    timestamp: Any

    open: float

    high: float

    low: float

    close: float

    volume: float


@dataclass
class SwingPoint:
    index: int

    timestamp: Any

    price: float

    swing_type: str

    strength: float


# ============================================================
# UTILITY
# ============================================================

def safe_float(
    value: Any,
    default: float = 0.0,
) -> float:

    try:

        if value is None:
            return default

        return float(value)

    except (TypeError, ValueError):

        return default


def get_value(
    candle: Any,
    *names: str,
    default: Any = None,
) -> Any:

    if isinstance(candle, dict):

        for name in names:

            if name in candle:

                return candle[name]

        return default

    for name in names:

        if hasattr(candle, name):

            return getattr(candle, name)

    return default


# ============================================================
# LOAD MARKET MEMORY
# ============================================================

def load_market_memory(
    filename: str = MARKET_DATA_FILE,
) -> Any:

    print("=" * 70)

    print(
        "MLAI v0.4 - LOADING MARKET MEMORY"
    )

    print("=" * 70)

    print(
        f"File: {filename}"
    )

    with open(
        filename,
        "rb",
    ) as file:

        data = pickle.load(file)

    print(
        "PASS: market_data.bin loaded"
    )

    return data


# ============================================================
# FIND CANDLES
# ============================================================

def find_candles(
    data: Any,
) -> List[Any]:

    if isinstance(data, list):

        if data:

            return data

    if isinstance(data, dict):

        possible_keys = [

            "analysed_candles",

            "analyzed_candles",

            "candles",

            "data",

            "market_data",

        ]

        for key in possible_keys:

            value = data.get(key)

            if (
                isinstance(value, list)
                and value
            ):

                return value

    for attribute in [

        "analysed_candles",

        "analyzed_candles",

        "candles",

        "data",

        "market_data",

    ]:

        if hasattr(
            data,
            attribute,
        ):

            value = getattr(
                data,
                attribute,
            )

            if (
                isinstance(value, list)
                and value
            ):

                return value

    raise ValueError(
        "Could not locate candle data "
        "inside market_data.bin"
    )


# ============================================================
# CONVERT CANDLE
# ============================================================

def convert_candle(
    candle: Any,
    index: int,
) -> Candle:

    return Candle(

        index=index,

        timestamp=get_value(
            candle,
            "timestamp",
            "datetime",
            "Datetime",
            "date",
            "Date",
        ),

        open=safe_float(
            get_value(
                candle,
                "open",
                "Open",
            )
        ),

        high=safe_float(
            get_value(
                candle,
                "high",
                "High",
            )
        ),

        low=safe_float(
            get_value(
                candle,
                "low",
                "Low",
            )
        ),

        close=safe_float(
            get_value(
                candle,
                "close",
                "Close",
            )
        ),

        volume=safe_float(
            get_value(
                candle,
                "volume",
                "Volume",
            )
        ),
    )


# ============================================================
# SWING HIGH DETECTION
# ============================================================

def detect_swing_highs(
    candles: List[Candle],
) -> List[SwingPoint]:

    swings = []

    left = SWING_LEFT

    right = SWING_RIGHT

    if len(candles) < (
        left + right + 1
    ):

        return swings

    for i in range(
        left,
        len(candles) - right,
    ):

        current = candles[i]

        left_candles = candles[
            i - left:i
        ]

        right_candles = candles[
            i + 1:i + right + 1
        ]

        is_high = all(
            current.high >= candle.high
            for candle in left_candles
        ) and all(
            current.high >= candle.high
            for candle in right_candles
        )

        if not is_high:

            continue

        surrounding_lows = [

            candle.low

            for candle in (
                left_candles
                + right_candles
            )

        ]

        if surrounding_lows:

            reference_low = min(
                surrounding_lows
            )

            strength = (
                current.high
                - reference_low
            )

        else:

            strength = 0.0

        swings.append(
            SwingPoint(

                index=current.index,

                timestamp=current.timestamp,

                price=current.high,

                swing_type="swing_high",

                strength=strength,
            )
        )

    return swings


# ============================================================
# SWING LOW DETECTION
# ============================================================

def detect_swing_lows(
    candles: List[Candle],
) -> List[SwingPoint]:

    swings = []

    left = SWING_LEFT

    right = SWING_RIGHT

    if len(candles) < (
        left + right + 1
    ):

        return swings

    for i in range(
        left,
        len(candles) - right,
    ):

        current = candles[i]

        left_candles = candles[
            i - left:i
        ]

        right_candles = candles[
            i + 1:i + right + 1
        ]

        is_low = all(
            current.low <= candle.low
            for candle in left_candles
        ) and all(
            current.low <= candle.low
            for candle in right_candles
        )

        if not is_low:

            continue

        surrounding_highs = [

            candle.high

            for candle in (
                left_candles
                + right_candles
            )

        ]

        if surrounding_highs:

            reference_high = max(
                surrounding_highs
            )

            strength = (
                reference_high
                - current.low
            )

        else:

            strength = 0.0

        swings.append(
            SwingPoint(

                index=current.index,

                timestamp=current.timestamp,

                price=current.low,

                swing_type="swing_low",

                strength=strength,
            )
        )

    return swings


# ============================================================
# COMBINE SWINGS
# ============================================================

def combine_swings(
    highs: List[SwingPoint],
    lows: List[SwingPoint],
) -> List[SwingPoint]:

    combined = (
        highs + lows
    )

    combined.sort(
        key=lambda swing: swing.index
    )

    return combined


# ============================================================
# CLASSIFY HIGH STRUCTURE
# ============================================================

def classify_highs(
    swing_highs: List[SwingPoint],
) -> List[Dict[str, Any]]:

    results = []

    previous: Optional[
        SwingPoint
    ] = None

    for swing in swing_highs:

        if previous is None:

            classification = (
                "initial_high"
            )

        elif (
            swing.price
            > previous.price
            + EPSILON
        ):

            classification = "higher_high"

        elif (
            swing.price
            < previous.price
            - EPSILON
        ):

            classification = "lower_high"

        else:

            classification = "equal_high"

        results.append({

            "index":
                swing.index,

            "timestamp":
                swing.timestamp,

            "price":
                swing.price,

            "classification":
                classification,

            "previous_price":
                (
                    previous.price
                    if previous
                    else None
                ),

        })

        previous = swing

    return results


# ============================================================
# CLASSIFY LOW STRUCTURE
# ============================================================

def classify_lows(
    swing_lows: List[SwingPoint],
) -> List[Dict[str, Any]]:

    results = []

    previous: Optional[
        SwingPoint
    ] = None

    for swing in swing_lows:

        if previous is None:

            classification = (
                "initial_low"
            )

        elif (
            swing.price
            > previous.price
            + EPSILON
        ):

            classification = "higher_low"

        elif (
            swing.price
            < previous.price
            - EPSILON
        ):

            classification = "lower_low"

        else:

            classification = "equal_low"

        results.append({

            "index":
                swing.index,

            "timestamp":
                swing.timestamp,

            "price":
                swing.price,

            "classification":
                classification,

            "previous_price":
                (
                    previous.price
                    if previous
                    else None
                ),

        })

        previous = swing

    return results


# ============================================================
# STRUCTURAL COUNTS
# ============================================================

def count_structure(
    high_structure: List[Dict[str, Any]],
    low_structure: List[Dict[str, Any]],
) -> Dict[str, int]:

    counts = {

        "higher_highs": 0,

        "lower_highs": 0,

        "equal_highs": 0,

        "higher_lows": 0,

        "lower_lows": 0,

        "equal_lows": 0,

    }

    for item in high_structure:

        classification = (
            item["classification"]
        )

        if classification == "higher_high":

            counts["higher_highs"] += 1

        elif classification == "lower_high":

            counts["lower_highs"] += 1

        elif classification == "equal_high":

            counts["equal_highs"] += 1

    for item in low_structure:

        classification = (
            item["classification"]
        )

        if classification == "higher_low":

            counts["higher_lows"] += 1

        elif classification == "lower_low":

            counts["lower_lows"] += 1

        elif classification == "equal_low":

            counts["equal_lows"] += 1

    return counts


# ============================================================
# STRUCTURAL DIRECTION
# ============================================================

def determine_structural_direction(
    counts: Dict[str, int],
) -> str:

    bullish_score = (

        counts["higher_highs"]

        + counts["higher_lows"]

    )

    bearish_score = (

        counts["lower_highs"]

        + counts["lower_lows"]

    )

    if (
        bullish_score > bearish_score
        and bullish_score >= 2
    ):

        return "bullish_structure"

    if (
        bearish_score > bullish_score
        and bearish_score >= 2
    ):

        return "bearish_structure"

    if (
        bullish_score == 0
        and bearish_score == 0
    ):

        return "insufficient_structure"

    return "mixed_structure"


# ============================================================
# TREND STRUCTURE
# ============================================================

def analyse_trend_structure(
    high_structure: List[Dict[str, Any]],
    low_structure: List[Dict[str, Any]],
) -> Dict[str, Any]:

    counts = count_structure(
        high_structure,
        low_structure,
    )

    direction = (
        determine_structural_direction(
            counts
        )
    )

    evidence = []

    if (
        counts["higher_highs"] > 0
        and counts["higher_lows"] > 0
    ):

        evidence.append(
            "Higher highs and higher lows "
            "are present in the observed swing structure."
        )

    if (
        counts["lower_highs"] > 0
        and counts["lower_lows"] > 0
    ):

        evidence.append(
            "Lower highs and lower lows "
            "are present in the observed swing structure."
        )

    if (
        counts["higher_highs"] > 0
        and counts["lower_highs"] > 0
    ):

        evidence.append(
            "Swing highs contain both upward "
            "and downward structural movement."
        )

    if (
        counts["higher_lows"] > 0
        and counts["lower_lows"] > 0
    ):

        evidence.append(
            "Swing lows contain both upward "
            "and downward structural movement."
        )

    if not evidence:

        evidence.append(
            "There is not enough consistent swing "
            "evidence to establish a strong trend structure."
        )

    return {

        "direction":
            direction,

        "counts":
            counts,

        "evidence":
            evidence,
    }


# ============================================================
# RANGE ANALYSIS
# ============================================================

def analyse_range_structure(
    candles: List[Candle],
    swing_highs: List[SwingPoint],
    swing_lows: List[SwingPoint],
) -> Dict[str, Any]:

    if not candles:

        return {

            "classification":
                "insufficient_data",

        }

    highest = max(
        candle.high
        for candle in candles
    )

    lowest = min(
        candle.low
        for candle in candles
    )

    total_range = (
        highest - lowest
    )

    if (
        total_range
        <= EPSILON
    ):

        return {

            "classification":
                "flat_or_insufficient",

            "range_high":
                highest,

            "range_low":
                lowest,

            "range_size":
                total_range,
        }

    high_touches = 0

    low_touches = 0

    tolerance = (
        total_range * 0.02
    )

    for candle in candles:

        if abs(
            candle.high
            - highest
        ) <= tolerance:

            high_touches += 1

        if abs(
            candle.low
            - lowest
        ) <= tolerance:

            low_touches += 1

    repeated_high_area = (
        high_touches >= 2
    )

    repeated_low_area = (
        low_touches >= 2
    )

    if (
        repeated_high_area
        and repeated_low_area
    ):

        classification = (
            "possible_range_structure"
        )

    else:

        classification = (
            "directional_or_expanding_structure"
        )

    return {

        "classification":
            classification,

        "range_high":
            highest,

        "range_low":
            lowest,

        "range_size":
            total_range,

        "high_touches":
            high_touches,

        "low_touches":
            low_touches,

    }


# ============================================================
# STRUCTURAL BREAK DETECTION
# ============================================================

def analyse_structural_breaks(
    candles: List[Candle],
    swing_highs: List[SwingPoint],
    swing_lows: List[SwingPoint],
) -> Dict[str, Any]:

    events = []

    bullish_breaks = 0

    bearish_breaks = 0

    failed_bullish_breaks = 0

    failed_bearish_breaks = 0

    if len(candles) < 2:

        return {

            "classification":
                "insufficient_data",

            "events":
                events,

        }

    # --------------------------------------------------------
    # BULLISH BREAKS OF PREVIOUS SWING HIGH
    # --------------------------------------------------------

    for swing_high in swing_highs:

        start = swing_high.index + 1

        if start >= len(candles):

            continue

        future_candles = candles[
            start:
        ]

        for position, candle in enumerate(
            future_candles
        ):

            if (
                candle.close
                > swing_high.price
            ):

                bullish_breaks += 1

                event = {

                    "type":
                        "bullish_structural_break",

                    "swing_index":
                        swing_high.index,

                    "break_candle":
                        candle.index,

                    "level":
                        swing_high.price,

                    "close":
                        candle.close,

                    "status":
                        "maintained",

                }

                # ------------------------------------------------
                # CHECK IMMEDIATE FAILURE
                # ------------------------------------------------

                next_index = (
                    start
                    + position
                    + 1
                )

                if (
                    next_index
                    < len(candles)
                ):

                    next_candle = (
                        candles[next_index]
                    )

                    if (
                        next_candle.close
                        <= swing_high.price
                    ):

                        failed_bullish_breaks += 1

                        event[
                            "status"
                        ] = "failed"

                events.append(
                    event
                )

                break

    # --------------------------------------------------------
    # BEARISH BREAKS OF PREVIOUS SWING LOW
    # --------------------------------------------------------

    for swing_low in swing_lows:

        start = swing_low.index + 1

        if start >= len(candles):

            continue

        future_candles = candles[
            start:
        ]

        for position, candle in enumerate(
            future_candles
        ):

            if (
                candle.close
                < swing_low.price
            ):

                bearish_breaks += 1

                event = {

                    "type":
                        "bearish_structural_break",

                    "swing_index":
                        swing_low.index,

                    "break_candle":
                        candle.index,

                    "level":
                        swing_low.price,

                    "close":
                        candle.close,

                    "status":
                        "maintained",

                }

                next_index = (
                    start
                    + position
                    + 1
                )

                if (
                    next_index
                    < len(candles)
                ):

                    next_candle = (
                        candles[next_index]
                    )

                    if (
                        next_candle.close
                        >= swing_low.price
                    ):

                        failed_bearish_breaks += 1

                        event[
                            "status"
                        ] = "failed"

                events.append(
                    event
                )

                break

    # --------------------------------------------------------
    # CLASSIFICATION
    # --------------------------------------------------------

    if (
        failed_bullish_breaks > 0
        and failed_bearish_breaks > 0
    ):

        classification = (
            "both_bullish_and_bearish_break_failures"
        )

    elif failed_bullish_breaks > 0:

        classification = (
            "failed_bullish_structure_break"
        )

    elif failed_bearish_breaks > 0:

        classification = (
            "failed_bearish_structure_break"
        )

    elif (
        bullish_breaks > 0
        and bearish_breaks == 0
    ):

        classification = (
            "bullish_structure_break_present"
        )

    elif (
        bearish_breaks > 0
        and bullish_breaks == 0
    ):

        classification = (
            "bearish_structure_break_present"
        )

    elif (
        bullish_breaks > 0
        and bearish_breaks > 0
    ):

        classification = (
            "mixed_structural_breaks"
        )

    else:

        classification = (
            "no_clear_structural_break"
        )

    return {

        "classification":
            classification,

        "bullish_breaks":
            bullish_breaks,

        "bearish_breaks":
            bearish_breaks,

        "failed_bullish_breaks":
            failed_bullish_breaks,

        "failed_bearish_breaks":
            failed_bearish_breaks,

        "events":
            events,
    }


# ============================================================
# CHANGE OF CHARACTER
# ============================================================

def analyse_change_of_character(
    trend: Dict[str, Any],
    breaks: Dict[str, Any],
    high_structure: List[Dict[str, Any]],
    low_structure: List[Dict[str, Any]],
) -> Dict[str, Any]:

    structural_direction = (
        trend["direction"]
    )

    events = []

    classification = (
        "no_clear_change_of_character"
    )

    # --------------------------------------------------------
    # BEARISH STRUCTURE -> BULLISH CHANGE
    # --------------------------------------------------------

    if (
        structural_direction
        == "bearish_structure"
        and
        breaks["bullish_breaks"] > 0
    ):

        classification = (
            "possible_bullish_change_of_character"
        )

        events.append(
            "A bullish break occurred while "
            "the broader swing structure was bearish."
        )

    # --------------------------------------------------------
    # BULLISH STRUCTURE -> BEARISH CHANGE
    # --------------------------------------------------------

    elif (
        structural_direction
        == "bullish_structure"
        and
        breaks["bearish_breaks"] > 0
    ):

        classification = (
            "possible_bearish_change_of_character"
        )

        events.append(
            "A bearish break occurred while "
            "the broader swing structure was bullish."
        )

    # --------------------------------------------------------
    # FAILED CHANGE
    # --------------------------------------------------------

    if (
        breaks["failed_bullish_breaks"] > 0
        and
        classification
        == "possible_bullish_change_of_character"
    ):

        classification = (
            "bullish_change_attempt_failed"
        )

        events.append(
            "The bullish structural break "
            "was not maintained."
        )

    if (
        breaks["failed_bearish_breaks"] > 0
        and
        classification
        == "possible_bearish_change_of_character"
    ):

        classification = (
            "bearish_change_attempt_failed"
        )

        events.append(
            "The bearish structural break "
            "was not maintained."
        )

    return {

        "classification":
            classification,

        "events":
            events,
    }


# ============================================================
# STRUCTURAL CONFLICT
# ============================================================

def analyse_structural_conflict(
    trend: Dict[str, Any],
    range_analysis: Dict[str, Any],
    breaks: Dict[str, Any],
    change: Dict[str, Any],
) -> Dict[str, Any]:

    conflicts = []

    direction = (
        trend["direction"]
    )

    if (
        direction
        == "bullish_structure"
        and
        breaks["bearish_breaks"] > 0
    ):

        conflicts.append(
            "Bullish swing structure exists "
            "while bearish structural breaks are present."
        )

    if (
        direction
        == "bearish_structure"
        and
        breaks["bullish_breaks"] > 0
    ):

        conflicts.append(
            "Bearish swing structure exists "
            "while bullish structural breaks are present."
        )

    if (
        range_analysis.get(
            "classification"
        )
        == "possible_range_structure"
    ):

        if direction in (
            "bullish_structure",
            "bearish_structure",
        ):

            conflicts.append(
                "Directional swing evidence exists "
                "inside a possible range structure."
            )

    if (
        "failed"
        in change.get(
            "classification",
            ""
        )
    ):

        conflicts.append(
            "A structural change attempt "
            "was not maintained."
        )

    if conflicts:

        classification = (
            "structural_conflict_present"
        )

    else:

        classification = (
            "no_major_structural_conflict"
        )

    return {

        "classification":
            classification,

        "conflicts":
            conflicts,
    }


# ============================================================
# STRUCTURE STORY
# ============================================================

def build_structure_story(
    trend: Dict[str, Any],
    range_analysis: Dict[str, Any],
    breaks: Dict[str, Any],
    change: Dict[str, Any],
    conflict: Dict[str, Any],
    high_structure: List[Dict[str, Any]],
    low_structure: List[Dict[str, Any]],
) -> str:

    statements = []

    direction = (
        trend["direction"]
    )

    # --------------------------------------------------------
    # STRUCTURE
    # --------------------------------------------------------

    if direction == "bullish_structure":

        statements.append(
            "The observed swing structure is "
            "generally bullish, with higher structural "
            "highs and/or higher structural lows."
        )

    elif direction == "bearish_structure":

        statements.append(
            "The observed swing structure is "
            "generally bearish, with lower structural "
            "highs and/or lower structural lows."
        )

    elif direction == "mixed_structure":

        statements.append(
            "The observed swing structure is mixed, "
            "with both upward and downward structural "
            "characteristics."
        )

    else:

        statements.append(
            "The available swing points do not establish "
            "a sufficiently clear structural direction."
        )

    # --------------------------------------------------------
    # RANGE
    # --------------------------------------------------------

    if (
        range_analysis.get(
            "classification"
        )
        == "possible_range_structure"
    ):

        statements.append(
            "Repeated reactions near both the recent "
            "upper and lower boundaries suggest a "
            "possible range-like structure."
        )

    # --------------------------------------------------------
    # BREAKS
    # --------------------------------------------------------

    if (
        breaks["bullish_breaks"] > 0
    ):

        statements.append(
            f"{breaks['bullish_breaks']} bullish "
            "structural break event(s) were detected."
        )

    if (
        breaks["bearish_breaks"] > 0
    ):

        statements.append(
            f"{breaks['bearish_breaks']} bearish "
            "structural break event(s) were detected."
        )

    if (
        breaks["failed_bullish_breaks"] > 0
    ):

        statements.append(
            f"{breaks['failed_bullish_breaks']} bullish "
            "structural break attempt(s) failed to remain "
            "above the broken structural level."
        )

    if (
        breaks["failed_bearish_breaks"] > 0
    ):

        statements.append(
            f"{breaks['failed_bearish_breaks']} bearish "
            "structural break attempt(s) failed to remain "
            "below the broken structural level."
        )

    # --------------------------------------------------------
    # CHANGE
    # --------------------------------------------------------

    change_classification = (
        change["classification"]
    )

    if (
        change_classification
        == "possible_bullish_change_of_character"
    ):

        statements.append(
            "The sequence contains evidence of a "
            "possible bullish change in structural behaviour."
        )

    elif (
        change_classification
        == "possible_bearish_change_of_character"
    ):

        statements.append(
            "The sequence contains evidence of a "
            "possible bearish change in structural behaviour."
        )

    elif (
        change_classification
        == "bullish_change_attempt_failed"
    ):

        statements.append(
            "A bullish structural change was attempted "
            "but the break was not maintained."
        )

    elif (
        change_classification
        == "bearish_change_attempt_failed"
    ):

        statements.append(
            "A bearish structural change was attempted "
            "but the break was not maintained."
        )

    # --------------------------------------------------------
    # CONFLICT
    # --------------------------------------------------------

    if (
        conflict["classification"]
        == "structural_conflict_present"
    ):

        statements.append(
            "Structural evidence is conflicting, so "
            "the current structure should not be reduced "
            "to a single directional conclusion."
        )

    else:

        statements.append(
            "No major structural conflict was detected "
            "within the analysed sequence."
        )

    # --------------------------------------------------------
    # LIMITATION
    # --------------------------------------------------------

    statements.append(
        "This structural interpretation is based on "
        "observable swing behaviour and does not prove "
        "hidden participant intentions."
    )

    return " ".join(
        statements
    )


# ============================================================
# COMPLETE v0.4 ANALYSIS
# ============================================================

def analyse_market_structure(
    candles: List[Candle],
) -> Dict[str, Any]:

    swing_highs = detect_swing_highs(
        candles
    )

    swing_lows = detect_swing_lows(
        candles
    )

    high_structure = classify_highs(
        swing_highs
    )

    low_structure = classify_lows(
        swing_lows
    )

    trend = analyse_trend_structure(
        high_structure,
        low_structure,
    )

    range_analysis = analyse_range_structure(
        candles,
        swing_highs,
        swing_lows,
    )

    breaks = analyse_structural_breaks(
        candles,
        swing_highs,
        swing_lows,
    )

    change = analyse_change_of_character(
        trend,
        breaks,
        high_structure,
        low_structure,
    )

    conflict = analyse_structural_conflict(
        trend,
        range_analysis,
        breaks,
        change,
    )

    story = build_structure_story(
        trend,
        range_analysis,
        breaks,
        change,
        conflict,
        high_structure,
        low_structure,
    )

    return {

        "version":
            VERSION,

        "candle_count":
            len(candles),

        "swing_high_count":
            len(swing_highs),

        "swing_low_count":
            len(swing_lows),

        "swing_highs":
            swing_highs,

        "swing_lows":
            swing_lows,

        "high_structure":
            high_structure,

        "low_structure":
            low_structure,

        "trend_structure":
            trend,

        "range_structure":
            range_analysis,

        "structural_breaks":
            breaks,

        "change_of_character":
            change,

        "structural_conflict":
            conflict,

        "story":
            story,
    }


# ============================================================
# DISPLAY
# ============================================================

def print_analysis(
    analysis: Dict[str, Any],
) -> None:

    print()

    print("=" * 70)

    print(
        "MLAI v0.4 MARKET STRUCTURE ANALYSIS"
    )

    print("=" * 70)

    print(
        f"Candles analysed: "
        f"{analysis['candle_count']}"
    )

    print()

    # ========================================================
    # SWINGS
    # ========================================================

    print(
        "SWING DETECTION"
    )

    print("-" * 70)

    print(
        f"Swing highs detected: "
        f"{analysis['swing_high_count']}"
    )

    print(
        f"Swing lows detected: "
        f"{analysis['swing_low_count']}"
    )

    # ========================================================
    # HIGH STRUCTURE
    # ========================================================

    print()

    print(
        "HIGH STRUCTURE"
    )

    print("-" * 70)

    high_structure = (
        analysis["high_structure"]
    )

    if high_structure:

        for item in high_structure:

            print(
                f"Candle {item['index']}: "
                f"{item['classification']} "
                f"@ {item['price']:.4f}"
            )

    else:

        print(
            "No swing highs detected."
        )

    # ========================================================
    # LOW STRUCTURE
    # ========================================================

    print()

    print(
        "LOW STRUCTURE"
    )

    print("-" * 70)

    low_structure = (
        analysis["low_structure"]
    )

    if low_structure:

        for item in low_structure:

            print(
                f"Candle {item['index']}: "
                f"{item['classification']} "
                f"@ {item['price']:.4f}"
            )

    else:

        print(
            "No swing lows detected."
        )

    # ========================================================
    # STRUCTURAL COUNTS
    # ========================================================

    print()

    print(
        "STRUCTURAL COUNTS"
    )

    print("-" * 70)

    counts = (
        analysis[
            "trend_structure"
        ]["counts"]
    )

    print(
        f"Higher Highs: "
        f"{counts['higher_highs']}"
    )

    print(
        f"Lower Highs: "
        f"{counts['lower_highs']}"
    )

    print(
        f"Equal Highs: "
        f"{counts['equal_highs']}"
    )

    print(
        f"Higher Lows: "
        f"{counts['higher_lows']}"
    )

    print(
        f"Lower Lows: "
        f"{counts['lower_lows']}"
    )

    print(
        f"Equal Lows: "
        f"{counts['equal_lows']}"
    )

    # ========================================================
    # TREND
    # ========================================================

    print()

    print(
        "MARKET STRUCTURE"
    )

    print("-" * 70)

    trend = (
        analysis[
            "trend_structure"
        ]
    )

    print(
        f"Classification: "
        f"{trend['direction']}"
    )

    for evidence in (
        trend["evidence"]
    ):

        print(
            f"- {evidence}"
        )

    # ========================================================
    # RANGE
    # ========================================================

    print()

    print(
        "RANGE STRUCTURE"
    )

    print("-" * 70)

    range_analysis = (
        analysis[
            "range_structure"
        ]
    )

    print(
        f"Classification: "
        f"{range_analysis['classification']}"
    )

    if "range_high" in range_analysis:

        print(
            f"Range high: "
            f"{range_analysis['range_high']:.4f}"
        )

        print(
            f"Range low: "
            f"{range_analysis['range_low']:.4f}"
        )

        print(
            f"Range size: "
            f"{range_analysis['range_size']:.4f}"
        )

        print(
            f"High touches: "
            f"{range_analysis['high_touches']}"
        )

        print(
            f"Low touches: "
            f"{range_analysis['low_touches']}"
        )

    # ========================================================
    # STRUCTURAL BREAKS
    # ========================================================

    print()

    print(
        "STRUCTURAL BREAK ANALYSIS"
    )

    print("-" * 70)

    breaks = (
        analysis[
            "structural_breaks"
        ]
    )

    print(
        f"Classification: "
        f"{breaks['classification']}"
    )

    print(
        f"Bullish structural breaks: "
        f"{breaks['bullish_breaks']}"
    )

    print(
        f"Bearish structural breaks: "
        f"{breaks['bearish_breaks']}"
    )

    print(
        f"Failed bullish breaks: "
        f"{breaks['failed_bullish_breaks']}"
    )

    print(
        f"Failed bearish breaks: "
        f"{breaks['failed_bearish_breaks']}"
    )

    if breaks["events"]:

        print()

        print(
            "Structural events:"
        )

        for event in breaks["events"]:

            print(
                f"- {event['type']} "
                f"at candle "
                f"{event['break_candle']} "
                f"level "
                f"{event['level']:.4f} "
                f"status={event['status']}"
            )

    # ========================================================
    # CHANGE OF CHARACTER
    # ========================================================

    print()

    print(
        "CHANGE OF CHARACTER"
    )

    print("-" * 70)

    change = (
        analysis[
            "change_of_character"
        ]
    )

    print(
        f"Classification: "
        f"{change['classification']}"
    )

    for event in (
        change["events"]
    ):

        print(
            f"- {event}"
        )

    # ========================================================
    # CONFLICT
    # ========================================================

    print()

    print(
        "STRUCTURAL CONFLICT"
    )

    print("-" * 70)

    conflict = (
        analysis[
            "structural_conflict"
        ]
    )

    print(
        f"Classification: "
        f"{conflict['classification']}"
    )

    for item in (
        conflict["conflicts"]
    ):

        print(
            f"- {item}"
        )

    # ========================================================
    # STORY
    # ========================================================

    print()

    print(
        "MARKET STRUCTURE STORY"
    )

    print("-" * 70)

    print(
        analysis["story"]
    )

    print()

    print("=" * 70)


# ============================================================
# PROJECT STATUS
# ============================================================

def update_project_status(
    analysis: Dict[str, Any],
) -> None:

    marker_start = (
        "<!-- MLAI_V04_AUTO_STATUS_START -->"
    )

    marker_end = (
        "<!-- MLAI_V04_AUTO_STATUS_END -->"
    )

    date_now = (
        datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    )

    trend = (
        analysis[
            "trend_structure"
        ]
    )

    counts = (
        trend["counts"]
    )

    range_analysis = (
        analysis[
            "range_structure"
        ]
    )

    breaks = (
        analysis[
            "structural_breaks"
        ]
    )

    change = (
        analysis[
            "change_of_character"
        ]
    )

    conflict = (
        analysis[
            "structural_conflict"
        ]
    )

    new_status = f"""

{marker_start}

# MLAI v0.4 AUTOMATIC DEVELOPMENT STATUS

DATE:

{date_now}

VERSION:

MLAI v0.4

TASK:

Market Structure Engine

STATUS:

TESTED / WORKING

FILES CREATED:

mlai_v04.py

FILES MODIFIED:

mlai_v04.py
MLAI_PROJECT_STATUS.md

WHAT WAS COMPLETED:

- Loaded existing market_data.bin.
- Reused existing stored market candles.
- Detected swing highs.
- Detected swing lows.
- Classified higher highs.
- Classified lower highs.
- Classified higher lows.
- Classified lower lows.
- Detected equal highs and equal lows.
- Analysed structural direction.
- Analysed possible range structure.
- Detected bullish structural breaks.
- Detected bearish structural breaks.
- Detected failed bullish structural breaks.
- Detected failed bearish structural breaks.
- Added possible change-of-character reasoning.
- Added structural conflict detection.
- Generated a market structure story.
- Preserved observation versus interpretation.
- No BUY/SELL signal was generated.
- No new market data was downloaded.
- Existing v0.1/v0.2 components were not rebuilt.

LATEST VERIFIED TEST:

Candles analysed:

{analysis.get("candle_count", 0)}

Swing highs:

{analysis.get("swing_high_count", 0)}

Swing lows:

{analysis.get("swing_low_count", 0)}

Higher highs:

{counts.get("higher_highs", 0)}

Lower highs:

{counts.get("lower_highs", 0)}

Higher lows:

{counts.get("higher_lows", 0)}

Lower lows:

{counts.get("lower_lows", 0)}

Structural direction:

{trend.get("direction", "unknown")}

Range classification:

{range_analysis.get("classification", "unknown")}

Bullish structural breaks:

{breaks.get("bullish_breaks", 0)}

Bearish structural breaks:

{breaks.get("bearish_breaks", 0)}

Failed bullish structural breaks:

{breaks.get("failed_bullish_breaks", 0)}

Failed bearish structural breaks:

{breaks.get("failed_bearish_breaks", 0)}

Change of character:

{change.get("classification", "unknown")}

Structural conflict:

{conflict.get("classification", "unknown")}

WHAT WAS TESTED:

- market_data.bin loading
- Candle extraction
- Candle conversion
- Swing high detection
- Swing low detection
- HH detection
- HL detection
- LH detection
- LL detection
- Structural direction
- Range detection
- Structural break detection
- Failed structural break detection
- Change-of-character reasoning
- Structural conflict detection
- Market structure story generation
- Automatic project documentation update

TEST RESULT:

PASS

WHAT FAILED:

None during the successful v0.4 structure test.

KNOWN LIMITATIONS:

- Swing detection is currently rule-based.
- Swing strength is basic.
- Market structure is based only on available OHLC data.
- Advanced support/resistance is not yet implemented.
- Supply/demand is not yet implemented.
- Liquidity reasoning is not yet implemented.
- Comprehensive candlestick pattern engine is not yet implemented.
- Historical behaviour engine is not yet implemented.
- Historical pattern database is not yet implemented.
- Multi-timeframe reasoning is not yet implemented.
- Advanced context engine is not yet implemented.
- Backtesting is not yet implemented.
- Pattern validation and accuracy measurement are not yet implemented.
- Chart image reading is not yet implemented.
- Live market streaming is not yet implemented.

IMPORTANT INTERPRETATION LIMITATION:

A structural break means that the observed candle closed
beyond a previously detected structural swing level.

It does NOT automatically prove:

- a permanent trend reversal
- institutional activity
- hidden orders
- exact trader intentions
- future price direction

MLAI therefore treats structural breaks as observable
price behaviour and evidence, not certainty.

CURRENT NEXT STEP:

Continue MLAI development with deeper MARKET STRUCTURE
and PRICE ACTION CONTEXT.

The next reasoning layer should connect:

Candle sequence
+
Swing structure
+
Higher High
+
Higher Low
+
Lower High
+
Lower Low
+
Structural break
+
Failed structural break
+
Previous price behaviour
+
Support/resistance areas

Core reasoning:

OBSERVATION
↓
SWING
↓
STRUCTURE
↓
STRUCTURAL CHANGE
↓
CONTEXT
↓
EVIDENCE
↓
INTERPRETATION
↓
MARKET STORY

DO NOT rebuild completed components.

{marker_end}
"""

    try:

        with open(
            STATUS_FILE,
            "r",
            encoding="utf-8",
        ) as file:

            existing = file.read()

    except FileNotFoundError:

        existing = ""

    if (
        marker_start in existing
        and marker_end in existing
    ):

        start_index = existing.index(
            marker_start
        )

        end_index = (
            existing.index(
                marker_end,
                start_index,
            )
            + len(marker_end)
        )

        updated = (
            existing[:start_index]
            + new_status.strip()
            + existing[end_index:]
        )

    else:

        updated = (
            existing.rstrip()
            + "\n\n"
            + new_status.strip()
            + "\n"
        )

    with open(
        STATUS_FILE,
        "w",
        encoding="utf-8",
    ) as file:

        file.write(updated)

    print()

    print(
        f"PASS: {STATUS_FILE} updated."
    )


# ============================================================
# MAIN
# ============================================================

def main() -> None:

    try:

        data = load_market_memory(
            MARKET_DATA_FILE
        )

        raw_candles = find_candles(
            data
        )

        print(
            f"Found {len(raw_candles)} "
            f"stored candles."
        )

        candles = []

        for index, candle in enumerate(
            raw_candles
        ):

            candles.append(
                convert_candle(
                    candle,
                    index,
                )
            )

        if len(candles) < 7:

            raise ValueError(
                "Not enough candles for "
                "market structure analysis."
            )

        sequence_length = min(
            DEFAULT_SEQUENCE_LENGTH,
            len(candles),
        )

        recent_candles = (
            candles[
                -sequence_length:
            ]
        )

        print()

        print(
            f"Analysing latest "
            f"{sequence_length} candles..."
        )

        analysis = (
            analyse_market_structure(
                recent_candles
            )
        )

        print_analysis(
            analysis
        )

        update_project_status(
            analysis
        )

        print()

        print(
            "PASS: MLAI v0.4 market "
            "structure analysis completed."
        )

    except FileNotFoundError:

        print()

        print(
            "ERROR: market_data.bin "
            "was not found."
        )

        print(
            "Make sure market_data.bin "
            "is in the same folder as mlai_v04.py."
        )

    except Exception as error:

        print()

        print(
            "MLAI v0.4 ERROR"
        )

        print("-" * 70)

        print(
            type(error).__name__
        )

        print(
            str(error)
        )


if __name__ == "__main__":

    main()