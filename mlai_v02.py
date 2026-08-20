
import pickle
from datetime import datetime, timezone


# ============================================================
# MLAI v0.2 — MARKET STORY ENGINE
#
# Input:
#     market_data.bin
#
# Output:
#     Human-readable market interpretation
#
# Purpose:
#     Move from individual candle analysis toward
#     sequence-based market-language understanding.
#
# IMPORTANT:
#     This is an analytical prototype.
#     It does NOT predict the future or provide trading advice.
# ============================================================


INPUT_FILE = "market_data.bin"


# ============================================================
# 1. LOAD MLAI MARKET MEMORY
# ============================================================

def load_market_memory():

    print("Loading MLAI market memory...")
    print(f"File: {INPUT_FILE}")
    print()

    with open(INPUT_FILE, "rb") as file:
        data = pickle.load(file)

    if "candles" not in data:
        raise RuntimeError(
            "The binary file does not contain MLAI candles."
        )

    candles = data["candles"]

    if not candles:
        raise RuntimeError(
            "The binary file contains no candles."
        )

    return data, candles


# ============================================================
# 2. BASIC HELPERS
# ============================================================

def average(values):

    if not values:
        return 0.0

    return sum(values) / len(values)


def percentage_change(old, new):

    if old == 0:
        return 0.0

    return ((new - old) / abs(old)) * 100.0


def candle_direction(candle):

    return candle.get("direction", "neutral")


def is_bullish(candle):

    return candle["close"] > candle["open"]


def is_bearish(candle):

    return candle["close"] < candle["open"]


def candle_range(candle):

    return candle["high"] - candle["low"]


# ============================================================
# 3. ANALYSE RECENT CANDLE GROUP
# ============================================================

def analyse_recent_candles(candles, window=12):

    recent = candles[-window:]

    bullish_count = 0
    bearish_count = 0
    neutral_count = 0

    ranges = []
    bodies = []
    upper_wicks = []
    lower_wicks = []

    for candle in recent:

        direction = candle_direction(candle)

        if direction == "bullish":
            bullish_count += 1

        elif direction == "bearish":
            bearish_count += 1

        else:
            neutral_count += 1

        ranges.append(candle.get("range", candle_range(candle)))
        bodies.append(candle.get("body", abs(
            candle["close"] - candle["open"]
        )))

        upper_wicks.append(
            candle.get(
                "upper_wick",
                candle["high"] - max(
                    candle["open"],
                    candle["close"]
                )
            )
        )

        lower_wicks.append(
            candle.get(
                "lower_wick",
                min(
                    candle["open"],
                    candle["close"]
                ) - candle["low"]
            )
        )

    return {
        "candles": recent,
        "bullish_count": bullish_count,
        "bearish_count": bearish_count,
        "neutral_count": neutral_count,
        "average_range": average(ranges),
        "average_body": average(bodies),
        "average_upper_wick": average(upper_wicks),
        "average_lower_wick": average(lower_wicks),
    }


# ============================================================
# 4. DETECT DIRECTIONAL PRESSURE
# ============================================================

def detect_pressure(stats):

    bullish = stats["bullish_count"]
    bearish = stats["bearish_count"]

    if bullish >= bearish + 4:

        return {
            "state": "bullish_pressure",
            "description": (
                "Recent candles show a clear bullish bias."
            )
        }

    if bearish >= bullish + 4:

        return {
            "state": "bearish_pressure",
            "description": (
                "Recent candles show a clear bearish bias."
            )
        }

    if bullish > bearish:

        return {
            "state": "slight_bullish_pressure",
            "description": (
                "Bullish candles slightly outnumber bearish candles."
            )
        }

    if bearish > bullish:

        return {
            "state": "slight_bearish_pressure",
            "description": (
                "Bearish candles slightly outnumber bullish candles."
            )
        }

    return {
        "state": "balanced",
        "description": (
            "Bullish and bearish candles are relatively balanced."
        )
    }


# ============================================================
# 5. DETECT MOMENTUM CHANGE
# ============================================================

def detect_momentum_change(candles, window=12):

    if len(candles) < window:
        return {
            "state": "insufficient_data",
            "description": "Not enough candles to compare momentum."
        }

    recent = candles[-window:]

    half = window // 2

    first_half = recent[:half]
    second_half = recent[half:]

    first_ranges = [
        candle_range(candle)
        for candle in first_half
    ]

    second_ranges = [
        candle_range(candle)
        for candle in second_half
    ]

    first_bodies = [
        abs(candle["close"] - candle["open"])
        for candle in first_half
    ]

    second_bodies = [
        abs(candle["close"] - candle["open"])
        for candle in second_half
    ]

    first_range_avg = average(first_ranges)
    second_range_avg = average(second_ranges)

    first_body_avg = average(first_bodies)
    second_body_avg = average(second_bodies)

    range_change = percentage_change(
        first_range_avg,
        second_range_avg
    )

    body_change = percentage_change(
        first_body_avg,
        second_body_avg
    )

    if range_change > 20 and body_change > 20:

        return {
            "state": "expanding",
            "description": (
                "Recent candles are becoming larger, "
                "indicating increased price activity."
            ),
            "range_change": range_change,
            "body_change": body_change
        }

    if range_change < -20 and body_change < -20:

        return {
            "state": "contracting",
            "description": (
                "Recent candles are becoming smaller, "
                "indicating reduced price activity."
            ),
            "range_change": range_change,
            "body_change": body_change
        }

    return {
        "state": "stable",
        "description": (
            "Recent candle size does not show a strong "
            "expansion or contraction."
        ),
        "range_change": range_change,
        "body_change": body_change
    }


# ============================================================
# 6. DETECT REJECTION
# ============================================================

def detect_rejection(candles, window=6):

    recent = candles[-window:]

    upper_rejection = 0
    lower_rejection = 0

    for candle in recent:

        total_range = candle_range(candle)

        if total_range <= 0:
            continue

        upper_wick = candle.get(
            "upper_wick",
            candle["high"] - max(
                candle["open"],
                candle["close"]
            )
        )

        lower_wick = candle.get(
            "lower_wick",
            min(
                candle["open"],
                candle["close"]
            ) - candle["low"]
        )

        if upper_wick / total_range >= 0.40:
            upper_rejection += 1

        if lower_wick / total_range >= 0.40:
            lower_rejection += 1

    if lower_rejection >= upper_rejection + 2:

        return {
            "state": "lower_rejection",
            "description": (
                "Recent candles show repeated rejection "
                "of lower prices."
            )
        }

    if upper_rejection >= lower_rejection + 2:

        return {
            "state": "upper_rejection",
            "description": (
                "Recent candles show repeated rejection "
                "of higher prices."
            )
        }

    return {
        "state": "balanced_rejection",
        "description": (
            "Recent wick behaviour does not show a "
            "strong directional rejection."
        )
    }


# ============================================================
# 7. DETECT CONSECUTIVE MOVEMENT
# ============================================================

def detect_recent_sequence(candles):

    if not candles:
        return {
            "state": "none",
            "count": 0,
            "description": "No candles available."
        }

    last_direction = candle_direction(candles[-1])

    count = 0

    for candle in reversed(candles):

        if candle_direction(candle) == last_direction:
            count += 1
        else:
            break

    if count >= 4:

        return {
            "state": last_direction,
            "count": count,
            "description": (
                f"The latest {count} candles are "
                f"{last_direction}."
            )
        }

    return {
        "state": last_direction,
        "count": count,
        "description": (
            f"The latest directional sequence contains "
            f"{count} {last_direction} candle(s)."
        )
    }


# ============================================================
# 8. DETECT SHORT-TERM PRICE STRUCTURE
# ============================================================

def detect_structure(candles, window=10):

    if len(candles) < window:
        return {
            "state": "insufficient_data",
            "description": "Not enough candles for structure analysis."
        }

    recent = candles[-window:]

    midpoint = window // 2

    first_part = recent[:midpoint]
    second_part = recent[midpoint:]

    first_high = max(
        candle["high"]
        for candle in first_part
    )

    second_high = max(
        candle["high"]
        for candle in second_part
    )

    first_low = min(
        candle["low"]
        for candle in first_part
    )

    second_low = min(
        candle["low"]
        for candle in second_part
    )

    higher_high = second_high > first_high
    higher_low = second_low > first_low

    lower_high = second_high < first_high
    lower_low = second_low < first_low

    if higher_high and higher_low:

        return {
            "state": "short_term_higher_structure",
            "description": (
                "The second part of the recent window "
                "formed both a higher high and a higher low "
                "relative to the first part."
            )
        }

    if lower_high and lower_low:

        return {
            "state": "short_term_lower_structure",
            "description": (
                "The second part of the recent window "
                "formed both a lower high and a lower low "
                "relative to the first part."
            )
        }

    if higher_high:

        return {
            "state": "higher_high_only",
            "description": (
                "Recent price exceeded the earlier high, "
                "but the complete higher-high/higher-low "
                "structure is not established."
            )
        }

    if lower_low:

        return {
            "state": "lower_low_only",
            "description": (
                "Recent price moved below the earlier low, "
                "but the complete lower-high/lower-low "
                "structure is not established."
            )
        }

    return {
        "state": "unclear",
        "description": (
            "Recent price does not show a clear short-term "
            "structural direction."
        )
    }


# ============================================================
# 9. DETECT RECENT EXPANSION / CONTRACTION
# ============================================================

def detect_range_condition(candles, window=12):

    recent = candles[-window:]

    if len(recent) < 4:

        return {
            "state": "insufficient_data"
        }

    ranges = [
        candle_range(candle)
        for candle in recent
    ]

    early_average = average(
        ranges[:len(ranges) // 2]
    )

    late_average = average(
        ranges[len(ranges) // 2:]
    )

    if early_average == 0:

        return {
            "state": "unknown"
        }

    change = percentage_change(
        early_average,
        late_average
    )

    if change > 25:

        return {
            "state": "range_expansion",
            "change": change,
            "description": (
                "Recent candle ranges expanded materially."
            )
        }

    if change < -25:

        return {
            "state": "range_contraction",
            "change": change,
            "description": (
                "Recent candle ranges contracted materially."
            )
        }

    return {
        "state": "stable_range",
        "change": change,
        "description": (
            "Recent candle ranges remain relatively stable."
        )
    }


# ============================================================
# 10. BUILD EVIDENCE
# ============================================================

def build_evidence(
    pressure,
    momentum,
    rejection,
    sequence,
    structure,
    range_condition
):

    evidence = []

    # Pressure

    if pressure["state"] == "bullish_pressure":

        evidence.append(
            "Recent candles show a clear bullish bias."
        )

    elif pressure["state"] == "bearish_pressure":

        evidence.append(
            "Recent candles show a clear bearish bias."
        )

    elif pressure["state"] == "slight_bullish_pressure":

        evidence.append(
            "Bullish candles slightly outnumber bearish candles."
        )

    elif pressure["state"] == "slight_bearish_pressure":

        evidence.append(
            "Bearish candles slightly outnumber bullish candles."
        )

    else:

        evidence.append(
            "Bullish and bearish candles are relatively balanced."
        )

    # Momentum

    evidence.append(
        momentum["description"]
    )

    # Rejection

    evidence.append(
        rejection["description"]
    )

    # Sequence

    evidence.append(
        sequence["description"]
    )

    # Structure

    evidence.append(
        structure["description"]
    )

    # Range condition

    evidence.append(
        range_condition["description"]
    )

    return evidence


# ============================================================
# 11. BUILD CURRENT INTERPRETATION
# ============================================================

def build_interpretation(
    pressure,
    momentum,
    rejection,
    sequence,
    structure
):

    # Strong bullish combination

    if (
        pressure["state"] == "bullish_pressure"
        and structure["state"]
        == "short_term_higher_structure"
    ):

        return (
            "Recent price behaviour shows relatively strong "
            "bullish pressure together with improving short-term "
            "structure. The evidence suggests buyers have gained "
            "relative control over the recent sequence."
        )

    # Strong bearish combination

    if (
        pressure["state"] == "bearish_pressure"
        and structure["state"]
        == "short_term_lower_structure"
    ):

        return (
            "Recent price behaviour shows relatively strong "
            "bearish pressure together with weakening short-term "
            "structure. The evidence suggests sellers have gained "
            "relative control over the recent sequence."
        )

    # Bullish pressure + lower rejection

    if (
        pressure["state"]
        in [
            "bullish_pressure",
            "slight_bullish_pressure"
        ]
        and rejection["state"]
        == "lower_rejection"
    ):

        return (
            "The recent sequence shows a bullish response combined "
            "with repeated rejection of lower prices. This suggests "
            "buyers are responding more effectively to downward "
            "movement, although the evidence does not by itself "
            "confirm a complete trend reversal."
        )

    # Bearish pressure + upper rejection

    if (
        pressure["state"]
        in [
            "bearish_pressure",
            "slight_bearish_pressure"
        ]
        and rejection["state"]
        == "upper_rejection"
    ):

        return (
            "The recent sequence shows bearish pressure combined "
            "with repeated rejection of higher prices. This suggests "
            "sellers are responding more effectively to upward "
            "movement, although the evidence does not by itself "
            "confirm a complete trend reversal."
        )

    # Momentum contraction

    if momentum["state"] == "contracting":

        return (
            "Recent candle ranges and bodies have contracted. "
            "This suggests that directional activity has weakened "
            "and the market may be entering a period of compression "
            "or temporary balance."
        )

    # Momentum expansion

    if momentum["state"] == "expanding":

        if pressure["state"] in [
            "bullish_pressure",
            "slight_bullish_pressure"
        ]:

            return (
                "Recent candle ranges are expanding while bullish "
                "candles dominate the sequence. This indicates an "
                "increase in upward price activity."
            )

        if pressure["state"] in [
            "bearish_pressure",
            "slight_bearish_pressure"
        ]:

            return (
                "Recent candle ranges are expanding while bearish "
                "candles dominate the sequence. This indicates an "
                "increase in downward price activity."
            )

    # Structure

    if structure["state"] == "higher_high_only":

        return (
            "Price has recently exceeded an earlier high, but the "
            "available evidence does not yet establish a complete "
            "higher-high and higher-low structure."
        )

    if structure["state"] == "lower_low_only":

        return (
            "Price has recently moved below an earlier low, but the "
            "available evidence does not yet establish a complete "
            "lower-high and lower-low structure."
        )

    # Default

    return (
        "The recent market behaviour contains mixed or incomplete "
        "evidence. No single interpretation has enough support to "
        "be treated as dominant."
    )


# ============================================================
# 12. BUILD MARKET STORY
# ============================================================

def build_market_story(
    candles,
    pressure,
    momentum,
    rejection,
    sequence,
    structure,
    range_condition
):

    recent = candles[-12:]

    first_price = recent[0]["open"]
    latest_price = recent[-1]["close"]

    price_change = percentage_change(
        first_price,
        latest_price
    )

    # --------------------------------------------------------
    # Beginning
    # --------------------------------------------------------

    if price_change > 0.20:

        beginning = (
            "The recent observation window began at a lower "
            "price and developed upward."
        )

    elif price_change < -0.20:

        beginning = (
            "The recent observation window began at a higher "
            "price and developed downward."
        )

    else:

        beginning = (
            "The recent observation window remained relatively "
            "close to its starting price."
        )

    # --------------------------------------------------------
    # Development
    # --------------------------------------------------------

    development = pressure["description"]

    # --------------------------------------------------------
    # Conflict / rejection
    # --------------------------------------------------------

    if rejection["state"] == "lower_rejection":

        conflict = (
            "The market repeatedly rejected lower prices, "
            "creating evidence of a response against the "
            "downward movement."
        )

    elif rejection["state"] == "upper_rejection":

        conflict = (
            "The market repeatedly rejected higher prices, "
            "creating evidence of a response against the "
            "upward movement."
        )

    else:

        conflict = (
            "The recent candles do not show a strong repeated "
            "rejection from either side."
        )

    # --------------------------------------------------------
    # Change
    # --------------------------------------------------------

    if momentum["state"] == "contracting":

        change = (
            "Candle size has decreased, suggesting that the "
            "previous movement is losing some immediate energy."
        )

    elif momentum["state"] == "expanding":

        change = (
            "Candle size has increased, showing that price activity "
            "has become more aggressive."
        )

    else:

        change = (
            "Candle size has remained relatively stable."
        )

    # --------------------------------------------------------
    # Current state
    # --------------------------------------------------------

    interpretation = build_interpretation(
        pressure,
        momentum,
        rejection,
        sequence,
        structure
    )

    # --------------------------------------------------------
    # Conditional future
    # --------------------------------------------------------

    if structure["state"] == "short_term_higher_structure":

        confirmation = (
            "Further higher highs and higher lows would strengthen "
            "the current bullish interpretation."
        )

        invalidation = (
            "A strong move below a meaningful recent low would "
            "weaken the bullish interpretation."
        )

    elif structure["state"] == "short_term_lower_structure":

        confirmation = (
            "Further lower highs and lower lows would strengthen "
            "the current bearish interpretation."
        )

        invalidation = (
            "A strong move above a meaningful recent high would "
            "weaken the bearish interpretation."
        )

    else:

        confirmation = (
            "Additional directional follow-through and a clear "
            "structural change would strengthen whichever side "
            "eventually gains control."
        )

        invalidation = (
            "A strong move in the opposite direction would weaken "
            "the current interpretation."
        )

    return {
        "beginning": beginning,
        "development": development,
        "conflict": conflict,
        "change": change,
        "current_state": interpretation,
        "confirmation": confirmation,
        "invalidation": invalidation,
        "price_change_percent": price_change
    }


# ============================================================
# 13. PRINT REPORT
# ============================================================

def print_report(
    metadata,
    candles,
    pressure,
    momentum,
    rejection,
    sequence,
    structure,
    range_condition,
    evidence,
    story
):

    print()
    print("=" * 90)
    print("                 MLAI v0.2 — MARKET STORY ENGINE")
    print("=" * 90)

    print()
    print("MARKET MEMORY")
    print("-" * 90)

    print(
        f"Provider : "
        f"{metadata.get('provider', 'Unknown')}"
    )

    print(
        f"Symbol   : "
        f"{metadata.get('symbol', 'Unknown')}"
    )

    print(
        f"Interval : "
        f"{metadata.get('interval', 'Unknown')}"
    )

    print(
        f"Range    : "
        f"{metadata.get('range', 'Unknown')}"
    )

    print(
        f"Candles  : "
        f"{len(candles)}"
    )

    print()
    print("CURRENT MARKET STATE")
    print("-" * 90)

    print(
        f"Pressure : "
        f"{pressure['state']}"
    )

    print(
        f"Momentum : "
        f"{momentum['state']}"
    )

    print(
        f"Rejection: "
        f"{rejection['state']}"
    )

    print(
        f"Sequence : "
        f"{sequence['state']} "
        f"({sequence['count']} candles)"
    )

    print(
        f"Structure: "
        f"{structure['state']}"
    )

    print(
        f"Range    : "
        f"{range_condition['state']}"
    )

    print()
    print("EVIDENCE")
    print("-" * 90)

    for number, item in enumerate(evidence, start=1):

        print(
            f"{number}. {item}"
        )

    print()
    print("=" * 90)
    print("                         MARKET STORY")
    print("=" * 90)

    print()
    print("1. BEGINNING")
    print(story["beginning"])

    print()
    print("2. DEVELOPMENT")
    print(story["development"])

    print()
    print("3. CONFLICT")
    print(story["conflict"])

    print()
    print("4. CHANGE")
    print(story["change"])

    print()
    print("5. CURRENT STATE")
    print(story["current_state"])

    print()
    print("6. CONFIRMATION")
    print(story["confirmation"])

    print()
    print("7. INVALIDATION")
    print(story["invalidation"])

    print()
    print(
        f"Recent price change: "
        f"{story['price_change_percent']:.3f}%"
    )

    print()
    print("=" * 90)
    print("MLAI INTERPRETATION COMPLETE")
    print("=" * 90)

    print()
    print(
        "IMPORTANT: This is a market-behaviour interpretation, "
        "not a guaranteed prediction or trading signal."
    )


# ============================================================
# 14. MAIN
# ============================================================

def main():

    try:

        # ----------------------------------------------------
        # LOAD
        # ----------------------------------------------------

        data, candles = load_market_memory()

        print(
            f"Loaded {len(candles)} candles successfully."
        )

        # ----------------------------------------------------
        # SOURCE INFORMATION
        # ----------------------------------------------------

        source = data.get(
            "source",
            {}
        )

        # ----------------------------------------------------
        # ANALYSIS
        # ----------------------------------------------------

        stats = analyse_recent_candles(
            candles,
            window=12
        )

        pressure = detect_pressure(
            stats
        )

        momentum = detect_momentum_change(
            candles,
            window=12
        )

        rejection = detect_rejection(
            candles,
            window=6
        )

        sequence = detect_recent_sequence(
            candles
        )

        structure = detect_structure(
            candles,
            window=10
        )

        range_condition = detect_range_condition(
            candles,
            window=12
        )

        # ----------------------------------------------------
        # EVIDENCE
        # ----------------------------------------------------

        evidence = build_evidence(
            pressure,
            momentum,
            rejection,
            sequence,
            structure,
            range_condition
        )

        # ----------------------------------------------------
        # MARKET STORY
        # ----------------------------------------------------

        story = build_market_story(
            candles,
            pressure,
            momentum,
            rejection,
            sequence,
            structure,
            range_condition
        )

        # ----------------------------------------------------
        # REPORT
        # ----------------------------------------------------

        print_report(
            source,
            candles,
            pressure,
            momentum,
            rejection,
            sequence,
            structure,
            range_condition,
            evidence,
            story
        )

    except FileNotFoundError:

        print()
        print("ERROR:")
        print(
            f"{INPUT_FILE} was not found."
        )

        print()
        print(
            "Make sure mlai_v02.py is in the same folder "
            "as market_data.bin."
        )

    except Exception as error:

        print()
        print("MLAI ERROR:")
        print(error)


if __name__ == "__main__":

    main() 