import os
import pickle
from collections import Counter
from datetime import datetime, timezone

# ============================================================
# MLAI v0.7 - HISTORICAL BEHAVIOUR ENGINE
# ============================================================
#
# Purpose:
# Compare the current market behaviour with similar historical
# candle sequences stored in market_data.bin.
#
# v0.7 does NOT:
# - predict the future with certainty
# - create BUY/SELL signals
# - invent volume/order-flow data
# - connect to the Internet
#
# v0.7 DOES:
# - search historical candle sequences
# - measure behavioural similarity
# - inspect what happened afterward
# - classify historical outcomes
# - compare current behaviour with historical evidence
# - document the historical market story
#
# ============================================================

VERSION = "0.7"

DATA_FILE = "market_data.bin"
STATUS_FILE = "MLAI_PROJECT_STATUS.md"

CURRENT_WINDOW = 30
HISTORICAL_WINDOW = 8
OUTCOME_WINDOW = 8

MIN_SIMILARITY = 0.60
MAX_MATCHES = 20


# ============================================================
# DATA LOADING
# ============================================================

def get_value(candle, *names):

    if isinstance(candle, dict):

        for name in names:

            if name in candle:
                return candle[name]

    for name in names:

        if hasattr(candle, name):
            return getattr(candle, name)

    return None


def normalize_candle(candle):

    try:

        open_price = float(
            get_value(candle, "open", "Open", "o")
        )

        high_price = float(
            get_value(candle, "high", "High", "h")
        )

        low_price = float(
            get_value(candle, "low", "Low", "l")
        )

        close_price = float(
            get_value(candle, "close", "Close", "c")
        )

    except (TypeError, ValueError):

        return None

    timestamp = get_value(
        candle,
        "timestamp",
        "time",
        "datetime",
        "date",
        "Date",
        "Timestamp"
    )

    return {
        "open": open_price,
        "high": high_price,
        "low": low_price,
        "close": close_price,
        "timestamp": timestamp
    }


def load_market_memory():

    print("=" * 70)
    print(f"MLAI v{VERSION} - LOADING MARKET MEMORY")
    print("=" * 70)

    print(f"File: {DATA_FILE}")

    if not os.path.exists(DATA_FILE):

        print()
        print(f"ERROR: {DATA_FILE} not found.")
        return []

    try:

        with open(DATA_FILE, "rb") as file:

            data = pickle.load(file)

    except Exception as error:

        print()
        print(f"ERROR: Could not load {DATA_FILE}")
        print(error)

        return []

    if isinstance(data, dict):

        possible_keys = [
            "candles",
            "data",
            "market_data",
            "records"
        ]

        for key in possible_keys:

            if key in data:

                data = data[key]

                break

    if not isinstance(data, (list, tuple)):

        print()
        print("ERROR: Unsupported market_data.bin format.")

        return []

    candles = []

    for item in data:

        candle = normalize_candle(item)

        if candle is not None:

            candles.append(candle)

    print("PASS: market_data.bin loaded")
    print(f"Found {len(candles)} stored candles.")
    print()

    return candles


# ============================================================
# CANDLE FEATURE ENGINE
# ============================================================

def candle_features(candle):

    open_price = candle["open"]
    high_price = candle["high"]
    low_price = candle["low"]
    close_price = candle["close"]

    candle_range = max(high_price - low_price, 0)

    body = abs(close_price - open_price)

    upper_wick = max(
        high_price - max(open_price, close_price),
        0
    )

    lower_wick = max(
        min(open_price, close_price) - low_price,
        0
    )

    if close_price > open_price:

        direction = 1

    elif close_price < open_price:

        direction = -1

    else:

        direction = 0

    if candle_range > 0:

        body_ratio = body / candle_range

        upper_ratio = upper_wick / candle_range

        lower_ratio = lower_wick / candle_range

    else:

        body_ratio = 0

        upper_ratio = 0

        lower_ratio = 0

    return {
        "direction": direction,
        "range": candle_range,
        "body": body,
        "upper_wick": upper_wick,
        "lower_wick": lower_wick,
        "body_ratio": body_ratio,
        "upper_ratio": upper_ratio,
        "lower_ratio": lower_ratio
    }


# ============================================================
# SEQUENCE FEATURE ENGINE
# ============================================================

def sequence_features(candles):

    if not candles:

        return {
            "direction": 0,
            "average_range": 0,
            "average_body": 0,
            "body_ratio": 0,
            "upper_ratio": 0,
            "lower_ratio": 0,
            "net_change": 0,
            "net_change_percent": 0
        }

    features = [
        candle_features(candle)
        for candle in candles
    ]

    average_range = (
        sum(item["range"] for item in features)
        / len(features)
    )

    average_body = (
        sum(item["body"] for item in features)
        / len(features)
    )

    body_ratio = (
        sum(item["body_ratio"] for item in features)
        / len(features)
    )

    upper_ratio = (
        sum(item["upper_ratio"] for item in features)
        / len(features)
    )

    lower_ratio = (
        sum(item["lower_ratio"] for item in features)
        / len(features)
    )

    direction = (
        sum(item["direction"] for item in features)
        / len(features)
    )

    first_close = candles[0]["close"]

    last_close = candles[-1]["close"]

    net_change = last_close - first_close

    if first_close != 0:

        net_change_percent = (
            net_change / first_close
        ) * 100

    else:

        net_change_percent = 0

    return {
        "direction": direction,
        "average_range": average_range,
        "average_body": average_body,
        "body_ratio": body_ratio,
        "upper_ratio": upper_ratio,
        "lower_ratio": lower_ratio,
        "net_change": net_change,
        "net_change_percent": net_change_percent
    }


# ============================================================
# SIMILARITY ENGINE
# ============================================================

def bounded_similarity_difference(a, b, maximum):

    if maximum <= 0:

        return 1

    difference = abs(a - b)

    return max(
        0,
        1 - min(difference / maximum, 1)
    )


def calculate_similarity(current, historical):

    scores = []

    # --------------------------------------------------------
    # Direction
    # --------------------------------------------------------

    direction_score = bounded_similarity_difference(
        current["direction"],
        historical["direction"],
        2
    )

    scores.append(
        direction_score * 0.25
    )

    # --------------------------------------------------------
    # Candle body ratio
    # --------------------------------------------------------

    body_score = bounded_similarity_difference(
        current["body_ratio"],
        historical["body_ratio"],
        1
    )

    scores.append(
        body_score * 0.15
    )

    # --------------------------------------------------------
    # Upper wick behaviour
    # --------------------------------------------------------

    upper_score = bounded_similarity_difference(
        current["upper_ratio"],
        historical["upper_ratio"],
        1
    )

    scores.append(
        upper_score * 0.15
    )

    # --------------------------------------------------------
    # Lower wick behaviour
    # --------------------------------------------------------

    lower_score = bounded_similarity_difference(
        current["lower_ratio"],
        historical["lower_ratio"],
        1
    )

    scores.append(
        lower_score * 0.15
    )

    # --------------------------------------------------------
    # Body / range relationship
    # --------------------------------------------------------

    current_strength = (
        current["average_body"]
        / current["average_range"]
        if current["average_range"] > 0
        else 0
    )

    historical_strength = (
        historical["average_body"]
        / historical["average_range"]
        if historical["average_range"] > 0
        else 0
    )

    strength_score = bounded_similarity_difference(
        current_strength,
        historical_strength,
        1
    )

    scores.append(
        strength_score * 0.15
    )

    # --------------------------------------------------------
    # Net movement
    # --------------------------------------------------------

    current_move = max(
        -1,
        min(
            current["net_change_percent"],
            1
        )
    )

    historical_move = max(
        -1,
        min(
            historical["net_change_percent"],
            1
        )
    )

    movement_score = 1 - (
        abs(
            current_move - historical_move
        ) / 2
    )

    scores.append(
        max(0, movement_score) * 0.15
    )

    return sum(scores)


# ============================================================
# HISTORICAL OUTCOME ENGINE
# ============================================================

def classify_future_outcome(future_candles):

    if len(future_candles) < 2:

        return "insufficient_data", 0

    starting_price = future_candles[0]["close"]

    ending_price = future_candles[-1]["close"]

    if starting_price == 0:

        return "insufficient_data", 0

    change_percent = (
        (ending_price - starting_price)
        / starting_price
    ) * 100

    threshold = 0.05

    if change_percent > threshold:

        return "bullish", change_percent

    if change_percent < -threshold:

        return "bearish", change_percent

    return "neutral", change_percent


# ============================================================
# HISTORICAL SEARCH ENGINE
# ============================================================

def search_historical_behaviour(
    candles,
    current_sequence
):

    current_features = sequence_features(
        current_sequence
    )

    matches = []

    total = len(candles)

    minimum_required = (
        HISTORICAL_WINDOW
        + OUTCOME_WINDOW
    )

    if total < minimum_required:

        return []

    # Do not use the current/latest sequence
    # as its own historical match.

    maximum_start = (
        total
        - minimum_required
        - CURRENT_WINDOW
    )

    if maximum_start < 0:

        maximum_start = (
            total
            - minimum_required
        )

    for start in range(
        maximum_start + 1
    ):

        historical_sequence = candles[
            start:
            start + HISTORICAL_WINDOW
        ]

        future_start = (
            start
            + HISTORICAL_WINDOW
        )

        future_end = (
            future_start
            + OUTCOME_WINDOW
        )

        future_sequence = candles[
            future_start:
            future_end
        ]

        if len(historical_sequence) != HISTORICAL_WINDOW:

            continue

        if len(future_sequence) != OUTCOME_WINDOW:

            continue

        historical_features = sequence_features(
            historical_sequence
        )

        similarity = calculate_similarity(
            current_features,
            historical_features
        )

        if similarity < MIN_SIMILARITY:

            continue

        outcome, change_percent = (
            classify_future_outcome(
                future_sequence
            )
        )

        matches.append({

            "start": start,

            "end": (
                start
                + HISTORICAL_WINDOW
                - 1
            ),

            "similarity": similarity,

            "outcome": outcome,

            "change_percent": change_percent
        })

    matches.sort(
        key=lambda item:
        item["similarity"],
        reverse=True
    )

    return matches[:MAX_MATCHES]


# ============================================================
# REPORT
# ============================================================

def print_report(
    candles,
    matches
):

    print("=" * 70)

    print(
        f"MLAI v{VERSION} "
        "HISTORICAL BEHAVIOUR ANALYSIS"
    )

    print("=" * 70)

    print(
        f"Current candles analysed: "
        f"{CURRENT_WINDOW}"
    )

    print(
        f"Historical sequence size: "
        f"{HISTORICAL_WINDOW}"
    )

    print(
        f"Outcome window: "
        f"{OUTCOME_WINDOW}"
    )

    print()

    # --------------------------------------------------------
    # Search summary
    # --------------------------------------------------------

    print("HISTORICAL SEARCH")
    print("-" * 70)

    print(
        f"Minimum similarity: "
        f"{MIN_SIMILARITY:.2f}"
    )

    print(
        f"Historical matches: "
        f"{len(matches)}"
    )

    print()

    if not matches:

        print(
            "No sufficiently similar historical "
            "situations were found."
        )

        print()

        print(
            "Historical evidence is insufficient "
            "for this current context."
        )

        return matches

    # --------------------------------------------------------
    # Outcome counts
    # --------------------------------------------------------

    outcome_counts = Counter(
        item["outcome"]
        for item in matches
    )

    bullish = outcome_counts.get(
        "bullish",
        0
    )

    bearish = outcome_counts.get(
        "bearish",
        0
    )

    neutral = outcome_counts.get(
        "neutral",
        0
    )

    total = len(matches)

    print("HISTORICAL OUTCOMES")
    print("-" * 70)

    print(
        f"Bullish outcomes : {bullish}"
    )

    print(
        f"Bearish outcomes : {bearish}"
    )

    print(
        f"Neutral outcomes : {neutral}"
    )

    print()

    # --------------------------------------------------------
    # Frequencies
    # --------------------------------------------------------

    print("HISTORICAL FREQUENCY")
    print("-" * 70)

    print(
        f"Bullish : "
        f"{bullish / total * 100:.1f}%"
    )

    print(
        f"Bearish : "
        f"{bearish / total * 100:.1f}%"
    )

    print(
        f"Neutral : "
        f"{neutral / total * 100:.1f}%"
    )

    print()

    # --------------------------------------------------------
    # Best matches
    # --------------------------------------------------------

    print("BEST HISTORICAL MATCHES")
    print("-" * 70)

    for index, match in enumerate(
        matches[:10],
        start=1
    ):

        print(
            f"{index:02d}. "
            f"Candles "
            f"{match['start']}→{match['end']} | "
            f"similarity="
            f"{match['similarity']:.3f} | "
            f"outcome="
            f"{match['outcome']} | "
            f"change="
            f"{match['change_percent']:+.3f}%"
        )

    print()

    # --------------------------------------------------------
    # Weighted evidence
    # --------------------------------------------------------

    weighted = Counter()

    total_weight = 0

    for match in matches:

        weight = match["similarity"]

        weighted[
            match["outcome"]
        ] += weight

        total_weight += weight

    print("WEIGHTED HISTORICAL EVIDENCE")
    print("-" * 70)

    for outcome in (
        "bullish",
        "bearish",
        "neutral"
    ):

        percentage = (
            weighted[outcome]
            / total_weight
            * 100
        )

        print(
            f"{outcome.capitalize():8s}: "
            f"{percentage:.1f}%"
        )

    print()

    # --------------------------------------------------------
    # Dominant historical behaviour
    # --------------------------------------------------------

    dominant = max(
        (
            "bullish",
            "bearish",
            "neutral"
        ),
        key=lambda item:
        weighted[item]
    )

    sorted_weights = sorted(
        weighted.values(),
        reverse=True
    )

    if len(sorted_weights) >= 2:

        gap = (
            sorted_weights[0]
            - sorted_weights[1]
        ) / total_weight * 100

    else:

        gap = 100

    if gap < 10:

        classification = (
            "mixed_historical_behaviour"
        )

    elif dominant == "bullish":

        classification = (
            "historical_bullish_tendency"
        )

    elif dominant == "bearish":

        classification = (
            "historical_bearish_tendency"
        )

    else:

        classification = (
            "historical_neutral_tendency"
        )

    print("HISTORICAL BEHAVIOUR CLASSIFICATION")
    print("-" * 70)

    print(
        f"Classification: "
        f"{classification}"
    )

    print()

    # --------------------------------------------------------
    # Current context
    # --------------------------------------------------------

    current_sequence = candles[
        -CURRENT_WINDOW:
    ]

    current_features = sequence_features(
        current_sequence
    )

    if current_features["direction"] > 0.15:

        current_direction = "bullish"

    elif current_features["direction"] < -0.15:

        current_direction = "bearish"

    else:

        current_direction = "mixed_or_neutral"

    print("CURRENT VS HISTORICAL EVIDENCE")
    print("-" * 70)

    print(
        f"Current directional character: "
        f"{current_direction}"
    )

    print(
        f"Historical dominant outcome: "
        f"{dominant}"
    )

    if (
        current_direction == dominant
    ):

        print(
            "Relationship: current behaviour "
            "agrees with the dominant historical tendency."
        )

    elif (
        dominant == "neutral"
        or current_direction == "mixed_or_neutral"
    ):

        print(
            "Relationship: historical evidence "
            "does not provide a strong directional conclusion."
        )

    else:

        print(
            "Relationship: current behaviour "
            "conflicts with the dominant historical tendency."
        )

    print()

    # --------------------------------------------------------
    # Market story
    # --------------------------------------------------------

    print("HISTORICAL BEHAVIOUR STORY")
    print("-" * 70)

    print(
        f"The current {CURRENT_WINDOW}-candle context "
        f"was compared with {len(matches)} "
        "similar historical sequences."
    )

    print(
        f"Those historical situations produced "
        f"{bullish} bullish, "
        f"{bearish} bearish, and "
        f"{neutral} neutral outcomes."
    )

    if classification == (
        "mixed_historical_behaviour"
    ):

        print(
            "The historical examples produced mixed "
            "results, so historical behaviour does not "
            "support a strong single-direction interpretation."
        )

    elif dominant == "bullish":

        print(
            "Similar historical situations more often "
            "produced bullish follow-through."
        )

    elif dominant == "bearish":

        print(
            "Similar historical situations more often "
            "produced bearish follow-through."
        )

    else:

        print(
            "Similar historical situations more often "
            "produced limited directional movement."
        )

    print(
        "Historical frequency is evidence from the "
        "stored sample, not a guarantee of future behaviour."
    )

    print(
        "This interpretation describes observable "
        "historical price behaviour and does not prove "
        "hidden participant intentions."
    )

    return matches


# ============================================================
# DOCUMENTATION
# ============================================================

def update_project_status(matches):

    timestamp = datetime.now(
        timezone.utc
    ).strftime(
        "%Y-%m-%d %H:%M:%S UTC"
    )

    try:

        with open(
            STATUS_FILE,
            "a",
            encoding="utf-8"
        ) as file:

            file.write("\n")

            file.write(
                "## MLAI v0.7 — Historical Behaviour Engine\n\n"
            )

            file.write(
                f"- Completed: {timestamp}\n"
            )

            file.write(
                f"- Historical matches found: "
                f"{len(matches)}\n"
            )

            file.write(
                f"- Historical sequence window: "
                f"{HISTORICAL_WINDOW} candles\n"
            )

            file.write(
                f"- Outcome window: "
                f"{OUTCOME_WINDOW} candles\n"
            )

            file.write(
                "- Similar historical sequences identified.\n"
            )

            file.write(
                "- Historical outcomes classified.\n"
            )

            file.write(
                "- Similarity-weighted historical evidence added.\n"
            )

            file.write(
                "- Current vs historical comparison added.\n"
            )

            file.write(
                "- Historical evidence treated as evidence, "
                "not certainty.\n"
            )

            file.write(
                "- Internet learning is NOT part of v0.7.\n"
            )

        print()
        print(
            f"PASS: {STATUS_FILE} updated."
        )

    except Exception as error:

        print()
        print(
            f"WARNING: Could not update "
            f"{STATUS_FILE}: {error}"
        )


# ============================================================
# MAIN
# ============================================================

def main():

    candles = load_market_memory()

    if not candles:

        return

    if len(candles) < CURRENT_WINDOW:

        print(
            f"ERROR: Need at least "
            f"{CURRENT_WINDOW} candles."
        )

        return

    print(
        f"Analysing latest "
        f"{CURRENT_WINDOW} candles..."
    )

    print()

    current_sequence = candles[
        -CURRENT_WINDOW:
    ]

    matches = search_historical_behaviour(
        candles,
        current_sequence
    )

    matches = print_report(
        candles,
        matches
    )

    update_project_status(
        matches
    )

    print()

    print("=" * 70)

    print(
        f"PASS: MLAI v{VERSION} "
        "historical behaviour analysis completed."
    )

    print("=" * 70)


if __name__ == "__main__":

    main()