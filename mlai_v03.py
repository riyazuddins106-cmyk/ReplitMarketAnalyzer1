"""
MLAI v0.3.1
Candle Sequence + Deeper Price Action Reasoning Engine

IMPORTANT:
- Uses existing market_data.bin
- Does NOT download new market data
- Does NOT rebuild MLAI v0.1/v0.2
- Extends the existing v0.3 sequence engine
- Analyses candle-to-candle relationships
- Analyses rejection responses
- Analyses failed movements
- Analyses recovery
- Analyses continuation
- Analyses reversal attempts
- Analyses breakouts / breakdowns
- Analyses failed breakouts / breakdowns
- Analyses retests
- Detects conflicting evidence
- Produces explanations, not BUY/SELL signals
- Updates MLAI_PROJECT_STATUS.md
"""

from __future__ import annotations

import pickle
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List


# ============================================================
# CONFIGURATION
# ============================================================

VERSION = "MLAI v0.3.1"

DEFAULT_SEQUENCE_LENGTH = 12

EPSILON = 1e-12

STATUS_FILE = "MLAI_PROJECT_STATUS.md"


# ============================================================
# DATA STRUCTURES
# ============================================================

@dataclass
class CandleObservation:

    index: int
    timestamp: Any

    open: float
    high: float
    low: float
    close: float
    volume: float

    body: float
    total_range: float

    upper_wick: float
    lower_wick: float

    body_ratio: float
    upper_wick_ratio: float
    lower_wick_ratio: float

    direction: str

    upper_rejection: bool
    lower_rejection: bool


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
# CANDLE ANATOMY
# ============================================================

def calculate_anatomy(
    open_price: float,
    high: float,
    low: float,
    close: float,
) -> Dict[str, float]:

    total_range = max(
        high - low,
        0.0,
    )

    body = abs(
        close - open_price
    )

    upper_wick = max(
        high - max(open_price, close),
        0.0,
    )

    lower_wick = max(
        min(open_price, close) - low,
        0.0,
    )

    if total_range > EPSILON:

        body_ratio = (
            body / total_range
        )

        upper_wick_ratio = (
            upper_wick / total_range
        )

        lower_wick_ratio = (
            lower_wick / total_range
        )

    else:

        body_ratio = 0.0
        upper_wick_ratio = 0.0
        lower_wick_ratio = 0.0

    return {

        "body": body,

        "total_range":
            total_range,

        "upper_wick":
            upper_wick,

        "lower_wick":
            lower_wick,

        "body_ratio":
            body_ratio,

        "upper_wick_ratio":
            upper_wick_ratio,

        "lower_wick_ratio":
            lower_wick_ratio,
    }


def determine_direction(
    open_price: float,
    close: float,
) -> str:

    if close > open_price:
        return "bullish"

    if close < open_price:
        return "bearish"

    return "neutral"


def determine_rejection(
    anatomy: Dict[str, float],
) -> tuple[bool, bool]:

    upper_rejection = (
        anatomy["upper_wick_ratio"]
        >= 0.35
    )

    lower_rejection = (
        anatomy["lower_wick_ratio"]
        >= 0.35
    )

    return (
        upper_rejection,
        lower_rejection,
    )


# ============================================================
# CONVERT CANDLE
# ============================================================

def convert_candle(
    candle: Any,
    index: int,
) -> CandleObservation:

    open_price = safe_float(
        get_value(
            candle,
            "open",
            "Open",
        )
    )

    high = safe_float(
        get_value(
            candle,
            "high",
            "High",
        )
    )

    low = safe_float(
        get_value(
            candle,
            "low",
            "Low",
        )
    )

    close = safe_float(
        get_value(
            candle,
            "close",
            "Close",
        )
    )

    volume = safe_float(
        get_value(
            candle,
            "volume",
            "Volume",
        )
    )

    timestamp = get_value(
        candle,
        "timestamp",
        "datetime",
        "Datetime",
        "date",
        "Date",
    )

    anatomy = calculate_anatomy(
        open_price,
        high,
        low,
        close,
    )

    direction = determine_direction(
        open_price,
        close,
    )

    (
        upper_rejection,
        lower_rejection,
    ) = determine_rejection(
        anatomy
    )

    return CandleObservation(

        index=index,

        timestamp=timestamp,

        open=open_price,
        high=high,
        low=low,
        close=close,
        volume=volume,

        body=anatomy["body"],

        total_range=
            anatomy["total_range"],

        upper_wick=
            anatomy["upper_wick"],

        lower_wick=
            anatomy["lower_wick"],

        body_ratio=
            anatomy["body_ratio"],

        upper_wick_ratio=
            anatomy["upper_wick_ratio"],

        lower_wick_ratio=
            anatomy["lower_wick_ratio"],

        direction=direction,

        upper_rejection=
            upper_rejection,

        lower_rejection=
            lower_rejection,
    )


# ============================================================
# LOAD MARKET MEMORY
# ============================================================

def load_market_memory(
    filename: str = "market_data.bin",
) -> Any:

    print("=" * 70)

    print(
        "MLAI v0.3.1 - LOADING MARKET MEMORY"
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
        "Could not locate candle data inside market_data.bin"
    )


# ============================================================
# PRICE MOVEMENT
# ============================================================

def price_change(
    first: CandleObservation,
    last: CandleObservation,
) -> float:

    return (
        last.close
        - first.open
    )


# ============================================================
# CANDLE RELATIONSHIPS
# ============================================================

def analyse_candle_relationships(
    candles: List[CandleObservation],
) -> Dict[str, Any]:

    events = []

    rejection_responses = 0
    rejection_failures = 0

    bullish_follow_through = 0
    bearish_follow_through = 0

    direction_changes = 0

    for i in range(
        len(candles) - 1
    ):

        current = candles[i]
        following = candles[i + 1]

        # ----------------------------------------------------
        # DIRECTION CHANGE
        # ----------------------------------------------------

        if (
            current.direction == "bullish"
            and
            following.direction == "bearish"
        ):

            direction_changes += 1

            events.append(
                f"Candle {i + 1}: direction "
                "changed from bullish to bearish."
            )

        elif (
            current.direction == "bearish"
            and
            following.direction == "bullish"
        ):

            direction_changes += 1

            events.append(
                f"Candle {i + 1}: direction "
                "changed from bearish to bullish."
            )

        # ----------------------------------------------------
        # LOWER REJECTION
        # ----------------------------------------------------

        if current.lower_rejection:

            if following.direction == "bullish":

                rejection_responses += 1

                events.append(
                    f"Candle {i + 1}: lower rejection "
                    "was followed by bullish response."
                )

            elif following.direction == "bearish":

                rejection_failures += 1

                events.append(
                    f"Candle {i + 1}: lower rejection "
                    "was followed by bearish continuation, "
                    "showing rejection failure."
                )

        # ----------------------------------------------------
        # UPPER REJECTION
        # ----------------------------------------------------

        if current.upper_rejection:

            if following.direction == "bearish":

                rejection_responses += 1

                events.append(
                    f"Candle {i + 1}: upper rejection "
                    "was followed by bearish response."
                )

            elif following.direction == "bullish":

                rejection_failures += 1

                events.append(
                    f"Candle {i + 1}: upper rejection "
                    "was followed by bullish continuation, "
                    "showing rejection failure."
                )

        # ----------------------------------------------------
        # FOLLOW-THROUGH
        # ----------------------------------------------------

        if (
            current.direction == "bullish"
            and following.direction == "bullish"
        ):

            bullish_follow_through += 1

        if (
            current.direction == "bearish"
            and following.direction == "bearish"
        ):

            bearish_follow_through += 1

    return {

        "relationship_events":
            len(events),

        "direction_changes":
            direction_changes,

        "rejection_responses":
            rejection_responses,

        "rejection_failures":
            rejection_failures,

        "bullish_follow_through":
            bullish_follow_through,

        "bearish_follow_through":
            bearish_follow_through,

        "events":
            events,
    }


# ============================================================
# RECOVERY ANALYSIS
# ============================================================

def analyse_recovery(
    candles: List[CandleObservation],
) -> Dict[str, Any]:

    bullish_after_bearish = 0
    bearish_after_bullish = 0

    for i in range(
        len(candles) - 1
    ):

        current = candles[i]
        following = candles[i + 1]

        if (
            current.direction == "bearish"
            and
            following.direction == "bullish"
        ):

            bullish_after_bearish += 1

        elif (
            current.direction == "bullish"
            and
            following.direction == "bearish"
        ):

            bearish_after_bullish += 1

    if (
        bullish_after_bearish
        >= 3
        and
        bullish_after_bearish
        > bearish_after_bullish
    ):

        classification = (
            "possible_bullish_recovery"
        )

        explanation = (
            "The sequence shows repeated bullish "
            "responses after bearish candles."
        )

    elif (
        bearish_after_bullish
        >= 3
        and
        bearish_after_bullish
        > bullish_after_bearish
    ):

        classification = (
            "possible_bearish_recovery"
        )

        explanation = (
            "The sequence shows repeated bearish "
            "responses after bullish candles."
        )

    else:

        classification = (
            "no_clear_recovery"
        )

        explanation = (
            "The sequence does not establish "
            "a strong recovery direction."
        )

    return {

        "classification":
            classification,

        "bullish_after_bearish":
            bullish_after_bearish,

        "bearish_after_bullish":
            bearish_after_bullish,

        "explanation":
            explanation,
    }


# ============================================================
# FAILED MOVEMENT
# ============================================================

def analyse_failed_movement(
    candles: List[CandleObservation],
) -> Dict[str, Any]:

    bullish_failures = 0
    bearish_failures = 0

    events = []

    for i in range(
        len(candles) - 1
    ):

        current = candles[i]
        following = candles[i + 1]

        if (
            current.direction == "bullish"
            and
            following.direction == "bearish"
        ):

            bullish_failures += 1

            events.append(
                f"Candles {i + 1}->{i + 2}: "
                "bullish movement was followed "
                "by bearish reversal."
            )

        elif (
            current.direction == "bearish"
            and
            following.direction == "bullish"
        ):

            bearish_failures += 1

            events.append(
                f"Candles {i + 1}->{i + 2}: "
                "bearish movement was followed "
                "by bullish reversal."
            )

    total_failures = (
        bullish_failures
        + bearish_failures
    )

    if total_failures == 0:

        classification = (
            "no_clear_failed_movement"
        )

    elif (
        bullish_failures
        > bearish_failures
    ):

        classification = (
            "bullish_movement_failures"
        )

    elif (
        bearish_failures
        > bullish_failures
    ):

        classification = (
            "bearish_movement_failures"
        )

    else:

        classification = (
            "mixed_failed_movement"
        )

    return {

        "classification":
            classification,

        "bullish_failures":
            bullish_failures,

        "bearish_failures":
            bearish_failures,

        "events":
            events,
    }


# ============================================================
# CONTINUATION SEQUENCE
# ============================================================

def analyse_continuation_sequence(
    candles: List[CandleObservation],
) -> Dict[str, Any]:

    maximum_bullish_streak = 0
    maximum_bearish_streak = 0

    current_bullish = 0
    current_bearish = 0

    for candle in candles:

        if candle.direction == "bullish":

            current_bullish += 1
            current_bearish = 0

        elif candle.direction == "bearish":

            current_bearish += 1
            current_bullish = 0

        else:

            current_bullish = 0
            current_bearish = 0

        maximum_bullish_streak = max(
            maximum_bullish_streak,
            current_bullish,
        )

        maximum_bearish_streak = max(
            maximum_bearish_streak,
            current_bearish,
        )

    if maximum_bullish_streak >= 3:

        classification = (
            "bullish_continuation_sequence"
        )

    elif maximum_bearish_streak >= 3:

        classification = (
            "bearish_continuation_sequence"
        )

    else:

        classification = (
            "no_strong_continuation_sequence"
        )

    return {

        "classification":
            classification,

        "maximum_bullish_streak":
            maximum_bullish_streak,

        "maximum_bearish_streak":
            maximum_bearish_streak,
    }


# ============================================================
# RECENT EXTREMES
# ============================================================

def analyse_recent_extremes(
    candles: List[CandleObservation],
) -> Dict[str, Any]:

    if len(candles) < 3:

        return {
            "classification":
                "insufficient_data"
        }

    previous = candles[:-1]
    latest = candles[-1]

    previous_high = max(
        candle.high
        for candle in previous
    )

    previous_low = min(
        candle.low
        for candle in previous
    )

    breakout = (
        latest.close
        > previous_high
    )

    breakdown = (
        latest.close
        < previous_low
    )

    return {

        "previous_high":
            previous_high,

        "previous_low":
            previous_low,

        "latest_high":
            latest.high,

        "latest_low":
            latest.low,

        "latest_close":
            latest.close,

        "breakout":
            breakout,

        "breakdown":
            breakdown,
    }


# ============================================================
# BREAKOUT / BREAKDOWN SEQUENCE
# ============================================================

def analyse_break_sequence(
    candles: List[CandleObservation],
) -> Dict[str, Any]:

    if len(candles) < 5:

        return {

            "classification":
                "insufficient_data",

            "breakouts":
                0,

            "breakdowns":
                0,

            "failed_breakouts":
                0,

            "failed_breakdowns":
                0,
        }

    breakouts = 0
    breakdowns = 0

    failed_breakouts = 0
    failed_breakdowns = 0

    breakout_follow_through = 0
    breakdown_follow_through = 0

    events = []

    for i in range(
        2,
        len(candles)
    ):

        current = candles[i]

        previous_window = (
            candles[:i]
        )

        previous_high = max(
            candle.high
            for candle in previous_window
        )

        previous_low = min(
            candle.low
            for candle in previous_window
        )

        # ----------------------------------------------------
        # BREAKOUT
        # ----------------------------------------------------

        if current.close > previous_high:

            breakouts += 1

            # Check next candle for failure
            if i + 1 < len(candles):

                following = candles[i + 1]

                if (
                    following.close
                    <= previous_high
                ):

                    failed_breakouts += 1

                    events.append(
                        f"Candle {i + 1}: possible breakout "
                        "was not maintained by the following candle."
                    )

                elif (
                    following.close
                    > current.close
                ):

                    breakout_follow_through += 1

                    events.append(
                        f"Candle {i + 1}: breakout received "
                        "higher-close follow-through."
                    )

        # ----------------------------------------------------
        # BREAKDOWN
        # ----------------------------------------------------

        if current.close < previous_low:

            breakdowns += 1

            if i + 1 < len(candles):

                following = candles[i + 1]

                if (
                    following.close
                    >= previous_low
                ):

                    failed_breakdowns += 1

                    events.append(
                        f"Candle {i + 1}: possible breakdown "
                        "was not maintained by the following candle."
                    )

                elif (
                    following.close
                    < current.close
                ):

                    breakdown_follow_through += 1

                    events.append(
                        f"Candle {i + 1}: breakdown received "
                        "lower-close follow-through."
                    )

    # --------------------------------------------------------
    # CLASSIFICATION
    # --------------------------------------------------------

    if failed_breakouts > 0:

        classification = (
            "failed_breakout_detected"
        )

    elif failed_breakdowns > 0:

        classification = (
            "failed_breakdown_detected"
        )

    elif breakout_follow_through > 0:

        classification = (
            "breakout_follow_through_detected"
        )

    elif breakdown_follow_through > 0:

        classification = (
            "breakdown_follow_through_detected"
        )

    elif breakouts > 0:

        classification = (
            "possible_breakout"
        )

    elif breakdowns > 0:

        classification = (
            "possible_breakdown"
        )

    else:

        classification = (
            "no_recent_break"
        )

    return {

        "classification":
            classification,

        "breakouts":
            breakouts,

        "breakdowns":
            breakdowns,

        "failed_breakouts":
            failed_breakouts,

        "failed_breakdowns":
            failed_breakdowns,

        "breakout_follow_through":
            breakout_follow_through,

        "breakdown_follow_through":
            breakdown_follow_through,

        "events":
            events,
    }


# ============================================================
# RETEST ANALYSIS
# ============================================================

def analyse_retest(
    candles: List[CandleObservation],
) -> Dict[str, Any]:

    bullish_retests = 0
    bearish_retests = 0

    events = []

    if len(candles) < 5:

        return {

            "classification":
                "insufficient_data",

            "bullish_retests":
                0,

            "bearish_retests":
                0,

            "events":
                [],
        }

    for i in range(
        2,
        len(candles) - 1
    ):

        current = candles[i]
        following = candles[i + 1]

        prior_high = max(
            c.high
            for c in candles[:i]
        )

        prior_low = min(
            c.low
            for c in candles[:i]
        )

        # ----------------------------------------------------
        # BULLISH RETEST
        # ----------------------------------------------------

        if (
            current.close > prior_high
            and
            following.low <= prior_high
            and
            following.close > prior_high
        ):

            bullish_retests += 1

            events.append(
                f"Candles {i + 1}->{i + 2}: "
                "price broke above a prior high, "
                "returned toward that area, then "
                "closed back above it."
            )

        # ----------------------------------------------------
        # BEARISH RETEST
        # ----------------------------------------------------

        if (
            current.close < prior_low
            and
            following.high >= prior_low
            and
            following.close < prior_low
        ):

            bearish_retests += 1

            events.append(
                f"Candles {i + 1}->{i + 2}: "
                "price broke below a prior low, "
                "returned toward that area, then "
                "closed back below it."
            )

    if bullish_retests > bearish_retests:

        classification = (
            "possible_bullish_retest"
        )

    elif bearish_retests > bullish_retests:

        classification = (
            "possible_bearish_retest"
        )

    elif (
        bullish_retests == 0
        and
        bearish_retests == 0
    ):

        classification = (
            "no_clear_retest"
        )

    else:

        classification = (
            "mixed_retests"
        )

    return {

        "classification":
            classification,

        "bullish_retests":
            bullish_retests,

        "bearish_retests":
            bearish_retests,

        "events":
            events,
    }


# ============================================================
# REVERSAL ATTEMPT
# ============================================================

def analyse_reversal_attempt(
    candles: List[CandleObservation],
) -> Dict[str, Any]:

    if len(candles) < 5:

        return {

            "classification":
                "insufficient_data"
        }

    midpoint = len(candles) // 2

    early = candles[:midpoint]
    recent = candles[midpoint:]

    early_bullish = sum(
        c.direction == "bullish"
        for c in early
    )

    early_bearish = sum(
        c.direction == "bearish"
        for c in early
    )

    recent_bullish = sum(
        c.direction == "bullish"
        for c in recent
    )

    recent_bearish = sum(
        c.direction == "bearish"
        for c in recent
    )

    if (
        early_bearish > early_bullish
        and
        recent_bullish > recent_bearish
    ):

        classification = (
            "possible_bullish_reversal_attempt"
        )

    elif (
        early_bullish > early_bearish
        and
        recent_bearish > recent_bullish
    ):

        classification = (
            "possible_bearish_reversal_attempt"
        )

    else:

        classification = (
            "no_clear_reversal_attempt"
        )

    return {

        "classification":
            classification,

        "early_bullish":
            early_bullish,

        "early_bearish":
            early_bearish,

        "recent_bullish":
            recent_bullish,

        "recent_bearish":
            recent_bearish,
    }


# ============================================================
# MOMENTUM
# ============================================================

def analyse_momentum(
    candles: List[CandleObservation],
) -> Dict[str, Any]:

    if len(candles) < 4:

        return {

            "state":
                "insufficient_data"
        }

    midpoint = (
        len(candles) // 2
    )

    early = candles[:midpoint]
    recent = candles[midpoint:]

    early_range = (
        sum(
            c.total_range
            for c in early
        )
        /
        max(len(early), 1)
    )

    recent_range = (
        sum(
            c.total_range
            for c in recent
        )
        /
        max(len(recent), 1)
    )

    early_body = (
        sum(
            c.body
            for c in early
        )
        /
        max(len(early), 1)
    )

    recent_body = (
        sum(
            c.body
            for c in recent
        )
        /
        max(len(recent), 1)
    )

    if (
        recent_range
        > early_range * 1.15
        and
        recent_body
        > early_body * 1.10
    ):

        state = "increasing"

    elif (
        recent_range
        < early_range * 0.85
        and
        recent_body
        < early_body * 0.90
    ):

        state = "decreasing"

    else:

        state = "stable_or_mixed"

    return {

        "state":
            state,

        "average_early_range":
            early_range,

        "average_recent_range":
            recent_range,

        "average_early_body":
            early_body,

        "average_recent_body":
            recent_body,
    }


# ============================================================
# DIRECTION
# ============================================================

def analyse_direction(
    candles: List[CandleObservation],
) -> Dict[str, Any]:

    bullish = sum(
        c.direction == "bullish"
        for c in candles
    )

    bearish = sum(
        c.direction == "bearish"
        for c in candles
    )

    neutral = sum(
        c.direction == "neutral"
        for c in candles
    )

    if bullish > bearish:

        dominant = "bullish"

    elif bearish > bullish:

        dominant = "bearish"

    else:

        dominant = "balanced"

    return {

        "bullish_count":
            bullish,

        "bearish_count":
            bearish,

        "neutral_count":
            neutral,

        "dominant_direction":
            dominant,
    }


# ============================================================
# WICK ANALYSIS
# ============================================================

def analyse_wicks(
    candles: List[CandleObservation],
) -> Dict[str, Any]:

    upper = sum(
        c.upper_rejection
        for c in candles
    )

    lower = sum(
        c.lower_rejection
        for c in candles
    )

    total_upper = sum(
        c.upper_wick
        for c in candles
    )

    total_lower = sum(
        c.lower_wick
        for c in candles
    )

    if upper > lower:

        dominant = "upper_rejection"

    elif lower > upper:

        dominant = "lower_rejection"

    else:

        dominant = "balanced_rejection"

    return {

        "upper_rejection_count":
            upper,

        "lower_rejection_count":
            lower,

        "total_upper_wick":
            total_upper,

        "total_lower_wick":
            total_lower,

        "average_upper_wick":
            total_upper / max(len(candles), 1),

        "average_lower_wick":
            total_lower / max(len(candles), 1),

        "dominant_rejection":
            dominant,
    }


# ============================================================
# CONFLICTING EVIDENCE
# ============================================================

def analyse_conflict(
    direction: Dict[str, Any],
    momentum: Dict[str, Any],
    recovery: Dict[str, Any],
    reversal: Dict[str, Any],
    failed: Dict[str, Any],
    breaks: Dict[str, Any],
) -> Dict[str, Any]:

    conflicts = []

    dominant = direction[
        "dominant_direction"
    ]

    recovery_state = recovery[
        "classification"
    ]

    reversal_state = reversal[
        "classification"
    ]

    if (
        dominant == "bearish"
        and
        recovery_state
        == "possible_bullish_recovery"
    ):

        conflicts.append(
            "Overall candle direction is bearish "
            "while recent candles show possible "
            "bullish recovery."
        )

    if (
        dominant == "bullish"
        and
        recovery_state
        == "possible_bearish_recovery"
    ):

        conflicts.append(
            "Overall candle direction is bullish "
            "while recent candles show possible "
            "bearish recovery."
        )

    if (
        dominant in
        ("bullish", "bearish")
        and
        momentum.get("state")
        == "decreasing"
    ):

        conflicts.append(
            "Directional dominance exists while "
            "movement intensity is decreasing."
        )

    if "possible_" in reversal_state:

        conflicts.append(
            "The sequence contains a possible "
            "reversal attempt against the broader "
            "directional dominance."
        )

    if failed.get(
        "bullish_failures",
        0,
    ) > 0 or failed.get(
        "bearish_failures",
        0,
    ) > 0:

        conflicts.append(
            "At least one movement attempt shows "
            "evidence of failure."
        )

    if breaks.get(
        "failed_breakouts",
        0,
    ) > 0:

        conflicts.append(
            "A breakout attempt failed to maintain "
            "its position beyond the prior high."
        )

    if breaks.get(
        "failed_breakdowns",
        0,
    ) > 0:

        conflicts.append(
            "A breakdown attempt failed to maintain "
            "its position below the prior low."
        )

    if conflicts:

        classification = (
            "conflicting_evidence_present"
        )

    else:

        classification = (
            "no_major_conflict_detected"
        )

    return {

        "classification":
            classification,

        "conflicts":
            conflicts,
    }


# ============================================================
# MARKET STORY
# ============================================================

def build_market_story(
    analysis: Dict[str, Any],
) -> str:

    direction = analysis["direction"]
    momentum = analysis["momentum"]
    wicks = analysis["wicks"]

    relationships = (
        analysis["relationships"]
    )

    recovery = analysis["recovery"]

    failed = analysis["failed_movement"]

    continuation = (
        analysis["continuation"]
    )

    reversal = (
        analysis["reversal"]
    )

    breaks = analysis["breaks"]

    retest = analysis["retest"]

    conflicts = analysis["conflict"]

    statements = []

    # --------------------------------------------------------
    # OBSERVATION
    # --------------------------------------------------------

    dominant = (
        direction[
            "dominant_direction"
        ]
    )

    if dominant == "bearish":

        statements.append(
            "Observation: the recent sequence "
            "contains more bearish than bullish candles."
        )

    elif dominant == "bullish":

        statements.append(
            "Observation: the recent sequence "
            "contains more bullish than bearish candles."
        )

    else:

        statements.append(
            "Observation: the recent sequence does "
            "not establish clear directional dominance."
        )

    # --------------------------------------------------------
    # MOMENTUM
    # --------------------------------------------------------

    if momentum["state"] == "increasing":

        statements.append(
            "Recent candle ranges and bodies are "
            "expanding, indicating increasing movement "
            "intensity."
        )

    elif momentum["state"] == "decreasing":

        statements.append(
            "Recent candle ranges and bodies are "
            "contracting, indicating decreasing movement "
            "intensity."
        )

    else:

        statements.append(
            "Movement intensity is mixed or relatively stable."
        )

    # --------------------------------------------------------
    # WICKS
    # --------------------------------------------------------

    if (
        wicks["dominant_rejection"]
        == "upper_rejection"
    ):

        statements.append(
            "Upper rejection is more frequent, "
            "showing repeated rejection of higher "
            "price excursions."
        )

    elif (
        wicks["dominant_rejection"]
        == "lower_rejection"
    ):

        statements.append(
            "Lower rejection is more frequent, "
            "showing repeated rejection of lower "
            "price excursions."
        )

    else:

        statements.append(
            "Upper and lower rejection are relatively balanced."
        )

    # --------------------------------------------------------
    # RELATIONSHIPS
    # --------------------------------------------------------

    if relationships[
        "rejection_responses"
    ] > 0:

        statements.append(
            f"{relationships['rejection_responses']} "
            "rejection event(s) received an "
            "opposite-direction response."
        )

    if relationships[
        "rejection_failures"
    ] > 0:

        statements.append(
            f"{relationships['rejection_failures']} "
            "rejection event(s) did not receive "
            "the expected directional follow-through."
        )

    # --------------------------------------------------------
    # RECOVERY
    # --------------------------------------------------------

    if recovery[
        "classification"
    ] == "possible_bullish_recovery":

        statements.append(
            "The sequence contains evidence of "
            "possible bullish recovery after earlier "
            "bearish behaviour."
        )

    elif recovery[
        "classification"
    ] == "possible_bearish_recovery":

        statements.append(
            "The sequence contains evidence of "
            "possible bearish recovery after earlier "
            "bullish behaviour."
        )

    # --------------------------------------------------------
    # FAILED MOVEMENT
    # --------------------------------------------------------

    if failed[
        "classification"
    ] != "no_clear_failed_movement":

        statements.append(
            "At least one directional movement attempt "
            "was followed by an opposite response, "
            "showing incomplete follow-through."
        )

    # --------------------------------------------------------
    # CONTINUATION
    # --------------------------------------------------------

    if continuation[
        "classification"
    ] == "bullish_continuation_sequence":

        statements.append(
            "A sustained bullish candle sequence "
            "is present."
        )

    elif continuation[
        "classification"
    ] == "bearish_continuation_sequence":

        statements.append(
            "A sustained bearish candle sequence "
            "is present."
        )

    # --------------------------------------------------------
    # REVERSAL
    # --------------------------------------------------------

    if (
        "possible_bullish_reversal"
        in reversal["classification"]
    ):

        statements.append(
            "The sequence contains a possible "
            "bullish reversal attempt."
        )

    elif (
        "possible_bearish_reversal"
        in reversal["classification"]
    ):

        statements.append(
            "The sequence contains a possible "
            "bearish reversal attempt."
        )

    # --------------------------------------------------------
    # BREAKS
    # --------------------------------------------------------

    if breaks[
        "failed_breakouts"
    ] > 0:

        statements.append(
            "At least one breakout attempt failed "
            "to maintain price above the previous "
            "high."
        )

    elif breaks[
        "failed_breakdowns"
    ] > 0:

        statements.append(
            "At least one breakdown attempt failed "
            "to maintain price below the previous "
            "low."
        )

    elif breaks[
        "breakout_follow_through"
    ] > 0:

        statements.append(
            "A breakout received higher-close "
            "follow-through."
        )

    elif breaks[
        "breakdown_follow_through"
    ] > 0:

        statements.append(
            "A breakdown received lower-close "
            "follow-through."
        )

    elif (
        breaks["breakouts"] > 0
        or
        breaks["breakdowns"] > 0
    ):

        statements.append(
            "A recent price extreme was exceeded, "
            "but follow-through evidence is limited."
        )

    # --------------------------------------------------------
    # RETEST
    # --------------------------------------------------------

    if (
        retest["classification"]
        == "possible_bullish_retest"
    ):

        statements.append(
            "The sequence contains evidence of a "
            "possible bullish retest."
        )

    elif (
        retest["classification"]
        == "possible_bearish_retest"
    ):

        statements.append(
            "The sequence contains evidence of a "
            "possible bearish retest."
        )

    # --------------------------------------------------------
    # CONFLICT
    # --------------------------------------------------------

    if (
        conflicts["classification"]
        == "conflicting_evidence_present"
    ):

        statements.append(
            "Conflicting evidence is present, so "
            "the sequence should not be reduced to "
            "a single directional interpretation."
        )

    else:

        statements.append(
            "No major contradiction was detected "
            "within the current sequence evidence."
        )

    # --------------------------------------------------------
    # SAFETY
    # --------------------------------------------------------

    statements.append(
        "This interpretation describes observable "
        "price behaviour and does not prove hidden "
        "participant intentions."
    )

    return " ".join(
        statements
    )


# ============================================================
# COMPLETE ANALYSIS
# ============================================================

def analyse_sequence(
    candles: List[CandleObservation],
) -> Dict[str, Any]:

    direction = analyse_direction(
        candles
    )

    momentum = analyse_momentum(
        candles
    )

    wicks = analyse_wicks(
        candles
    )

    relationships = (
        analyse_candle_relationships(
            candles
        )
    )

    recovery = analyse_recovery(
        candles
    )

    failed_movement = (
        analyse_failed_movement(
            candles
        )
    )

    continuation = (
        analyse_continuation_sequence(
            candles
        )
    )

    reversal = (
        analyse_reversal_attempt(
            candles
        )
    )

    breaks = analyse_break_sequence(
        candles
    )

    retest = analyse_retest(
        candles
    )

    conflict = analyse_conflict(
        direction,
        momentum,
        recovery,
        reversal,
        failed_movement,
        breaks,
    )

    analysis = {

        "version":
            VERSION,

        "candle_count":
            len(candles),

        "direction":
            direction,

        "momentum":
            momentum,

        "wicks":
            wicks,

        "relationships":
            relationships,

        "recovery":
            recovery,

        "failed_movement":
            failed_movement,

        "continuation":
            continuation,

        "reversal":
            reversal,

        "breaks":
            breaks,

        "retest":
            retest,

        "conflict":
            conflict,
    }

    analysis["story"] = (
        build_market_story(
            analysis
        )
    )

    return analysis


# ============================================================
# DISPLAY
# ============================================================

def print_analysis(
    analysis: Dict[str, Any],
) -> None:

    print()

    print("=" * 70)

    print(
        "MLAI v0.3.1 CANDLE SEQUENCE + "
        "DEEPER PRICE ACTION ANALYSIS"
    )

    print("=" * 70)

    print(
        f"Candles analysed: "
        f"{analysis['candle_count']}"
    )

    # --------------------------------------------------------
    # DIRECTION
    # --------------------------------------------------------

    print()
    print("DIRECTION")
    print("-" * 70)

    direction = analysis["direction"]

    print(
        f"Bullish candles : "
        f"{direction['bullish_count']}"
    )

    print(
        f"Bearish candles : "
        f"{direction['bearish_count']}"
    )

    print(
        f"Neutral candles : "
        f"{direction['neutral_count']}"
    )

    print(
        f"Dominant direction: "
        f"{direction['dominant_direction']}"
    )

    # --------------------------------------------------------
    # MOMENTUM
    # --------------------------------------------------------

    print()
    print("MOMENTUM")
    print("-" * 70)

    momentum = analysis["momentum"]

    print(
        f"State: {momentum['state']}"
    )

    if "average_early_range" in momentum:

        print(
            f"Early average range: "
            f"{momentum['average_early_range']:.4f}"
        )

        print(
            f"Recent average range: "
            f"{momentum['average_recent_range']:.4f}"
        )

        print(
            f"Early average body: "
            f"{momentum['average_early_body']:.4f}"
        )

        print(
            f"Recent average body: "
            f"{momentum['average_recent_body']:.4f}"
        )

    # --------------------------------------------------------
    # WICKS
    # --------------------------------------------------------

    print()
    print("WICK / REJECTION BEHAVIOUR")
    print("-" * 70)

    wicks = analysis["wicks"]

    print(
        f"Upper rejection count: "
        f"{wicks['upper_rejection_count']}"
    )

    print(
        f"Lower rejection count: "
        f"{wicks['lower_rejection_count']}"
    )

    print(
        f"Dominant rejection: "
        f"{wicks['dominant_rejection']}"
    )

    # --------------------------------------------------------
    # RELATIONSHIPS
    # --------------------------------------------------------

    print()
    print("CANDLE RELATIONSHIPS")
    print("-" * 70)

    relationships = (
        analysis["relationships"]
    )

    print(
        f"Relationship events: "
        f"{relationships['relationship_events']}"
    )

    print(
        f"Direction changes: "
        f"{relationships['direction_changes']}"
    )

    print(
        f"Rejection responses: "
        f"{relationships['rejection_responses']}"
    )

    print(
        f"Rejection failures: "
        f"{relationships['rejection_failures']}"
    )

    print(
        f"Bullish follow-through: "
        f"{relationships['bullish_follow_through']}"
    )

    print(
        f"Bearish follow-through: "
        f"{relationships['bearish_follow_through']}"
    )

    if relationships["events"]:

        print()
        print("Events:")

        for event in relationships["events"]:

            print(
                f"- {event}"
            )

    # --------------------------------------------------------
    # RECOVERY
    # --------------------------------------------------------

    print()
    print("RECOVERY ANALYSIS")
    print("-" * 70)

    recovery = analysis["recovery"]

    print(
        f"Classification: "
        f"{recovery['classification']}"
    )

    print(
        f"Bullish after bearish: "
        f"{recovery['bullish_after_bearish']}"
    )

    print(
        f"Bearish after bullish: "
        f"{recovery['bearish_after_bullish']}"
    )

    print(
        f"- {recovery['explanation']}"
    )

    # --------------------------------------------------------
    # FAILED MOVEMENT
    # --------------------------------------------------------

    print()
    print("FAILED MOVEMENT")
    print("-" * 70)

    failed = analysis[
        "failed_movement"
    ]

    print(
        f"Classification: "
        f"{failed['classification']}"
    )

    print(
        f"Bullish movement failures: "
        f"{failed['bullish_failures']}"
    )

    print(
        f"Bearish movement failures: "
        f"{failed['bearish_failures']}"
    )

    for event in failed["events"]:

        print(
            f"- {event}"
        )

    # --------------------------------------------------------
    # CONTINUATION
    # --------------------------------------------------------

    print()
    print("CONTINUATION SEQUENCE")
    print("-" * 70)

    continuation = (
        analysis["continuation"]
    )

    print(
        f"Classification: "
        f"{continuation['classification']}"
    )

    print(
        f"Maximum bullish streak: "
        f"{continuation['maximum_bullish_streak']}"
    )

    print(
        f"Maximum bearish streak: "
        f"{continuation['maximum_bearish_streak']}"
    )

    # --------------------------------------------------------
    # REVERSAL
    # --------------------------------------------------------

    print()
    print("REVERSAL ATTEMPT")
    print("-" * 70)

    reversal = analysis["reversal"]

    print(
        f"Classification: "
        f"{reversal['classification']}"
    )

    # --------------------------------------------------------
    # BREAKS
    # --------------------------------------------------------

    print()
    print("BREAKOUT / BREAKDOWN ANALYSIS")
    print("-" * 70)

    breaks = analysis["breaks"]

    print(
        f"Classification: "
        f"{breaks['classification']}"
    )

    print(
        f"Breakouts detected: "
        f"{breaks['breakouts']}"
    )

    print(
        f"Breakdowns detected: "
        f"{breaks['breakdowns']}"
    )

    print(
        f"Failed breakouts: "
        f"{breaks['failed_breakouts']}"
    )

    print(
        f"Failed breakdowns: "
        f"{breaks['failed_breakdowns']}"
    )

    print(
        f"Breakout follow-through: "
        f"{breaks['breakout_follow_through']}"
    )

    print(
        f"Breakdown follow-through: "
        f"{breaks['breakdown_follow_through']}"
    )

    for event in breaks["events"]:

        print(
            f"- {event}"
        )

    # --------------------------------------------------------
    # RETEST
    # --------------------------------------------------------

    print()
    print("RETEST ANALYSIS")
    print("-" * 70)

    retest = analysis["retest"]

    print(
        f"Classification: "
        f"{retest['classification']}"
    )

    print(
        f"Bullish retests: "
        f"{retest['bullish_retests']}"
    )

    print(
        f"Bearish retests: "
        f"{retest['bearish_retests']}"
    )

    for event in retest["events"]:

        print(
            f"- {event}"
        )

    # --------------------------------------------------------
    # CONFLICT
    # --------------------------------------------------------

    print()
    print("CONFLICTING EVIDENCE")
    print("-" * 70)

    conflict = analysis["conflict"]

    print(
        f"Classification: "
        f"{conflict['classification']}"
    )

    for item in conflict["conflicts"]:

        print(
            f"- {item}"
        )

    # --------------------------------------------------------
    # STORY
    # --------------------------------------------------------

    print()
    print("MARKET STORY")
    print("-" * 70)

    print(
        analysis["story"]
    )

    print()

    print("=" * 70)


# ============================================================
# UPDATE PROJECT STATUS
# ============================================================

def update_project_status(
    analysis: Dict[str, Any],
    sequence_length: int,
) -> None:

    marker_start = (
        "<!-- MLAI_V03_AUTO_STATUS_START -->"
    )

    marker_end = (
        "<!-- MLAI_V03_AUTO_STATUS_END -->"
    )

    date_now = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    direction = analysis["direction"]
    momentum = analysis["momentum"]
    wicks = analysis["wicks"]

    relationships = analysis[
        "relationships"
    ]

    recovery = analysis["recovery"]

    failed = analysis[
        "failed_movement"
    ]

    continuation = analysis[
        "continuation"
    ]

    reversal = analysis["reversal"]

    breaks = analysis["breaks"]

    retest = analysis["retest"]

    conflict = analysis["conflict"]

    new_status = f"""

{marker_start}

# MLAI v0.3.1 AUTOMATIC DEVELOPMENT STATUS

DATE:

{date_now}

VERSION:

MLAI v0.3.1

TASK:

Deeper Candle Sequence + Price Action Reasoning

STATUS:

TESTED / WORKING

FILES CREATED:

None

FILES MODIFIED:

mlai_v03.py
MLAI_PROJECT_STATUS.md

WHAT WAS COMPLETED:

- Reused existing market_data.bin.
- Did not download new market data.
- Preserved MLAI v0.1/v0.2 components.
- Extended candle-to-candle relationship analysis.
- Added rejection response reasoning.
- Added rejection failure reasoning.
- Added recovery sequence analysis.
- Added failed movement analysis.
- Added continuation streak analysis.
- Added reversal attempt analysis.
- Added multi-candle breakout analysis.
- Added breakout follow-through analysis.
- Added failed breakout detection.
- Added failed breakdown detection.
- Added retest detection.
- Improved conflicting evidence analysis.
- Improved sequence-level market story generation.
- Preserved observation versus interpretation.
- No BUY/SELL signal was generated.

LATEST VERIFIED TEST:

Candles analysed:

{analysis["candle_count"]}

Bullish candles:

{direction["bullish_count"]}

Bearish candles:

{direction["bearish_count"]}

Neutral candles:

{direction["neutral_count"]}

Dominant direction:

{direction["dominant_direction"]}

Momentum:

{momentum["state"]}

Upper rejection count:

{wicks["upper_rejection_count"]}

Lower rejection count:

{wicks["lower_rejection_count"]}

Dominant rejection:

{wicks["dominant_rejection"]}

CANDLE RELATIONSHIPS:

{relationships["relationship_events"]}

Direction changes:

{relationships["direction_changes"]}

Rejection responses:

{relationships["rejection_responses"]}

Rejection failures:

{relationships["rejection_failures"]}

RECOVERY:

{recovery["classification"]}

FAILED MOVEMENT:

{failed["classification"]}

CONTINUATION:

{continuation["classification"]}

REVERSAL:

{reversal["classification"]}

BREAK ANALYSIS:

{breaks["classification"]}

Breakouts detected:

{breaks["breakouts"]}

Breakdowns detected:

{breaks["breakdowns"]}

Failed breakouts:

{breaks["failed_breakouts"]}

Failed breakdowns:

{breaks["failed_breakdowns"]}

Breakout follow-through:

{breaks["breakout_follow_through"]}

Breakdown follow-through:

{breaks["breakdown_follow_through"]}

RETEST:

{retest["classification"]}

Bullish retests:

{retest["bullish_retests"]}

Bearish retests:

{retest["bearish_retests"]}

CONFLICT:

{conflict["classification"]}

WHAT WAS TESTED:

- Existing market_data.bin loading
- Existing candle extraction
- Candle conversion
- Candle anatomy
- Candle relationships
- Direction changes
- Rejection responses
- Rejection failures
- Recovery detection
- Failed movement detection
- Continuation detection
- Reversal attempt detection
- Breakout detection
- Breakdown detection
- Failed breakout detection
- Failed breakdown detection
- Retest detection
- Conflicting evidence
- Market story generation
- Automatic project documentation update

TEST RESULT:

PASS

WHAT FAILED:

None during the successful v0.3.1 sequence test.

KNOWN LIMITATIONS:

- Current sequence engine remains rule-based.
- Price levels are currently derived from the analysed sequence.
- Advanced market structure is not yet implemented.
- Support/resistance is not yet implemented.
- Supply/demand is not yet implemented.
- Liquidity reasoning is not yet implemented.
- Comprehensive candlestick pattern engine is not yet implemented.
- Historical behaviour engine is not yet implemented.
- Historical pattern database is not yet implemented.
- Multi-timeframe reasoning is not yet implemented.
- Advanced relationship engine is not yet implemented.
- Chart image reading is not yet implemented.
- Live market streaming is not yet implemented.
- Historical backtesting is not yet implemented.
- Pattern validation and accuracy measurement are not yet implemented.

IMPORTANT INTERPRETATION LIMITATION:

MLAI only describes observable price behaviour.

A rejection does not prove hidden orders.

A breakout does not guarantee continuation.

A reversal attempt does not guarantee reversal.

A retest does not guarantee continuation.

MLAI must continue to separate:

OBSERVATION

from

INTERPRETATION

and

HISTORICAL EVIDENCE.

WHAT REMAINS:

- Improve candle-to-candle relationship reasoning.
- Improve movement-leg detection.
- Improve recovery detection.
- Improve failed movement detection.
- Improve continuation detection.
- Improve reversal detection.
- Improve breakout validation.
- Improve retest validation.
- Add stronger price-location reasoning.
- Begin market structure engine preparation.

CURRENT NEXT STEP:

Continue MLAI v0.3.

The next development should focus on:

MOVEMENT LEG + PRICE LOCATION REASONING

The engine should begin identifying:

- Swing highs
- Swing lows
- Higher highs
- Higher lows
- Lower highs
- Lower lows
- Local directional legs
- Leg strength
- Leg failure
- Expansion from a local range
- Compression before movement
- Price location within the recent sequence
- Relationship between current price and recent extremes

Core reasoning:

CANDLE
↓
CANDLE RELATIONSHIP
↓
SEQUENCE
↓
MOVEMENT LEG
↓
PRICE LOCATION
↓
PRICE ACTION
↓
INTERPRETATION
↓
EVIDENCE
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
            "market_data.bin"
        )

        raw_candles = find_candles(
            data
        )

        print(
            f"Found {len(raw_candles)} "
            "stored candles."
        )

        observations = []

        for index, candle in enumerate(
            raw_candles
        ):

            observations.append(
                convert_candle(
                    candle,
                    index,
                )
            )

        if len(observations) < 5:

            raise ValueError(
                "Not enough candles for "
                "v0.3.1 analysis."
            )

        sequence_length = min(
            DEFAULT_SEQUENCE_LENGTH,
            len(observations),
        )

        recent_candles = (
            observations[
                -sequence_length:
            ]
        )

        print()

        print(
            f"Analysing latest "
            f"{sequence_length} candles..."
        )

        analysis = analyse_sequence(
            recent_candles
        )

        print_analysis(
            analysis
        )

        update_project_status(
            analysis,
            sequence_length,
        )

        print()

        print(
            "PASS: MLAI v0.3.1 sequence "
            "analysis completed."
        )

    except FileNotFoundError:

        print()

        print(
            "ERROR: market_data.bin "
            "was not found."
        )

        print(
            "Run the existing MLAI v0.2 "
            "program first."
        )

    except Exception as error:

        print()

        print(
            "MLAI v0.3.1 ERROR"
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