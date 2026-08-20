import os
import pickle
from statistics import mean


# ============================================================
# MLAI v0.6 - PATTERN / CONTEXT ENGINE
# ============================================================
#
# Purpose:
#   Detect important candlestick formations and evaluate them
#   inside their surrounding market context.
#
# IMPORTANT:
#   Pattern != automatic trading signal.
#
# The engine asks:
#
#   What pattern appeared?
#          ↓
#   What happened before it?
#          ↓
#   Where did it appear?
#          ↓
#   What happened after it?
#          ↓
#   Did it receive confirmation?
#          ↓
#   Did it fail?
#          ↓
#   What does the complete sequence communicate?
#
# ============================================================


DATA_FILE = "market_data.bin"
STATUS_FILE = "MLAI_PROJECT_STATUS.md"

LOOKBACK = 60


# ============================================================
# HELPERS
# ============================================================

def get_value(candle, *names, default=None):

    if isinstance(candle, dict):
        for name in names:
            if name in candle:
                return candle[name]

    for name in names:
        if hasattr(candle, name):
            return getattr(candle, name)

    return default


def number(value, default=0.0):

    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def values(candle):

    o = number(get_value(candle, "open", "Open", "o"))
    h = number(get_value(candle, "high", "High", "h"))
    l = number(get_value(candle, "low", "Low", "l"))
    c = number(get_value(candle, "close", "Close", "c"))

    return o, h, l, c


def direction(candle):

    o, h, l, c = values(candle)

    if c > o:
        return "bullish"

    if c < o:
        return "bearish"

    return "neutral"


def candle_range(candle):

    o, h, l, c = values(candle)

    return max(0.0, h - l)


def body(candle):

    o, h, l, c = values(candle)

    return abs(c - o)


def upper_wick(candle):

    o, h, l, c = values(candle)

    return max(0.0, h - max(o, c))


def lower_wick(candle):

    o, h, l, c = values(candle)

    return max(0.0, min(o, c) - l)


def body_ratio(candle):

    r = candle_range(candle)

    if r <= 0:
        return 0.0

    return body(candle) / r


def is_bullish(candle):

    return direction(candle) == "bullish"


def is_bearish(candle):

    return direction(candle) == "bearish"


def is_small_body(candle):

    r = candle_range(candle)

    if r <= 0:
        return False

    return body(candle) <= r * 0.30


def is_large_body(candle):

    r = candle_range(candle)

    if r <= 0:
        return False

    return body(candle) >= r * 0.65


# ============================================================
# PATTERN DETECTION
# ============================================================

def detect_single_patterns(candles):

    patterns = []

    ranges = [candle_range(c) for c in candles]

    average_range = mean(ranges) if ranges else 0

    for i, candle in enumerate(candles):

        o, h, l, c = values(candle)

        r = candle_range(candle)
        b = body(candle)
        uw = upper_wick(candle)
        lw = lower_wick(candle)

        if r <= 0:
            continue

        # ----------------------------------------------------
        # DOJI
        # ----------------------------------------------------

        if b <= r * 0.10:

            patterns.append({
                "index": i,
                "name": "Doji",
                "type": "indecision",
                "strength": "context_dependent",
                "reason": "Very small body relative to total range."
            })

        # ----------------------------------------------------
        # HAMMER
        # ----------------------------------------------------

        if (
            lw >= b * 2
            and uw <= max(b * 0.75, r * 0.10)
            and b <= r * 0.40
        ):

            patterns.append({
                "index": i,
                "name": "Hammer-like rejection",
                "type": "potential_bullish_rejection",
                "strength": "context_dependent",
                "reason": "Long lower wick with relatively small upper wick."
            })

        # ----------------------------------------------------
        # SHOOTING STAR
        # ----------------------------------------------------

        if (
            uw >= b * 2
            and lw <= max(b * 0.75, r * 0.10)
            and b <= r * 0.40
        ):

            patterns.append({
                "index": i,
                "name": "Shooting-star-like rejection",
                "type": "potential_bearish_rejection",
                "strength": "context_dependent",
                "reason": "Long upper wick with relatively small lower wick."
            })

        # ----------------------------------------------------
        # SPINNING TOP
        # ----------------------------------------------------

        if (
            b <= r * 0.35
            and uw >= r * 0.20
            and lw >= r * 0.20
        ):

            patterns.append({
                "index": i,
                "name": "Spinning Top",
                "type": "indecision",
                "strength": "context_dependent",
                "reason": "Small body with meaningful wicks on both sides."
            })

        # ----------------------------------------------------
        # BULLISH MARUBOZU-LIKE
        # ----------------------------------------------------

        if (
            is_bullish(candle)
            and b >= r * 0.80
            and uw <= r * 0.10
            and lw <= r * 0.10
        ):

            patterns.append({
                "index": i,
                "name": "Bullish Marubozu-like candle",
                "type": "strong_bullish",
                "strength": "potentially_strong",
                "reason": "Large bullish body with minimal wicks."
            })

        # ----------------------------------------------------
        # BEARISH MARUBOZU-LIKE
        # ----------------------------------------------------

        if (
            is_bearish(candle)
            and b >= r * 0.80
            and uw <= r * 0.10
            and lw <= r * 0.10
        ):

            patterns.append({
                "index": i,
                "name": "Bearish Marubozu-like candle",
                "type": "strong_bearish",
                "strength": "potentially_strong",
                "reason": "Large bearish body with minimal wicks."
            })

        # ----------------------------------------------------
        # LARGE RANGE EXPANSION
        # ----------------------------------------------------

        if average_range > 0 and r >= average_range * 1.50:

            patterns.append({
                "index": i,
                "name": "Range Expansion Candle",
                "type": "volatility_expansion",
                "strength": "context_dependent",
                "reason": "Candle range is substantially larger than average."
            })

    return patterns


# ============================================================
# TWO-CANDLE PATTERNS
# ============================================================

def detect_two_candle_patterns(candles):

    patterns = []

    for i in range(1, len(candles)):

        previous = candles[i - 1]
        current = candles[i]

        po, ph, pl, pc = values(previous)
        co, ch, cl, cc = values(current)

        # ----------------------------------------------------
        # BULLISH ENGULFING
        # ----------------------------------------------------

        if (
            is_bearish(previous)
            and is_bullish(current)
            and co <= pc
            and cc >= po
        ):

            patterns.append({
                "index": i,
                "name": "Bullish Engulfing",
                "type": "potential_bullish_reversal",
                "strength": "context_dependent",
                "reason": "Current bullish body engulfs the previous bearish body."
            })

        # ----------------------------------------------------
        # BEARISH ENGULFING
        # ----------------------------------------------------

        if (
            is_bullish(previous)
            and is_bearish(current)
            and co >= pc
            and cc <= po
        ):

            patterns.append({
                "index": i,
                "name": "Bearish Engulfing",
                "type": "potential_bearish_reversal",
                "strength": "context_dependent",
                "reason": "Current bearish body engulfs the previous bullish body."
            })

        # ----------------------------------------------------
        # BULLISH HARAMI
        # ----------------------------------------------------

        if (
            is_bearish(previous)
            and is_bullish(current)
            and co >= pc
            and cc <= po
        ):

            patterns.append({
                "index": i,
                "name": "Bullish Harami-like structure",
                "type": "potential_bullish_transition",
                "strength": "weak_to_contextual",
                "reason": "Smaller bullish body develops inside previous bearish body."
            })

        # ----------------------------------------------------
        # BEARISH HARAMI
        # ----------------------------------------------------

        if (
            is_bullish(previous)
            and is_bearish(current)
            and co <= pc
            and cc >= po
        ):

            patterns.append({
                "index": i,
                "name": "Bearish Harami-like structure",
                "type": "potential_bearish_transition",
                "strength": "weak_to_contextual",
                "reason": "Smaller bearish body develops inside previous bullish body."
            })

        # ----------------------------------------------------
        # INSIDE BAR
        # ----------------------------------------------------

        if (
            ch <= ph
            and cl >= pl
        ):

            patterns.append({
                "index": i,
                "name": "Inside Bar",
                "type": "compression",
                "strength": "context_dependent",
                "reason": "Current candle remains within previous candle range."
            })

        # ----------------------------------------------------
        # OUTSIDE BAR
        # ----------------------------------------------------

        if (
            ch >= ph
            and cl <= pl
        ):

            patterns.append({
                "index": i,
                "name": "Outside Bar",
                "type": "expansion",
                "strength": "context_dependent",
                "reason": "Current candle exceeds previous high and low."
            })

    return patterns


# ============================================================
# THREE-CANDLE PATTERNS
# ============================================================

def detect_three_candle_patterns(candles):

    patterns = []

    for i in range(2, len(candles)):

        a = candles[i - 2]
        b = candles[i - 1]
        c = candles[i]

        ao, ah, al, ac = values(a)
        bo, bh, bl, bc = values(b)
        co, ch, cl, cc = values(c)

        # ----------------------------------------------------
        # MORNING STAR-LIKE
        # ----------------------------------------------------

        if (
            is_bearish(a)
            and body(b) <= candle_range(b) * 0.35
            and is_bullish(c)
            and cc > (ao + ac) / 2
        ):

            patterns.append({
                "index": i,
                "name": "Morning Star-like sequence",
                "type": "potential_bullish_reversal",
                "strength": "context_dependent",
                "reason": "Bearish candle followed by indecision and bullish recovery."
            })

        # ----------------------------------------------------
        # EVENING STAR-LIKE
        # ----------------------------------------------------

        if (
            is_bullish(a)
            and body(b) <= candle_range(b) * 0.35
            and is_bearish(c)
            and cc < (ao + ac) / 2
        ):

            patterns.append({
                "index": i,
                "name": "Evening Star-like sequence",
                "type": "potential_bearish_reversal",
                "strength": "context_dependent",
                "reason": "Bullish candle followed by indecision and bearish recovery."
            })

        # ----------------------------------------------------
        # THREE WHITE SOLDIERS
        # ----------------------------------------------------

        if (
            is_bullish(a)
            and is_bullish(b)
            and is_bullish(c)
            and bc > ac
            and cc > bc
        ):

            patterns.append({
                "index": i,
                "name": "Three White Soldiers-like sequence",
                "type": "bullish_continuation",
                "strength": "potentially_strong",
                "reason": "Three consecutive bullish closes with upward progression."
            })

        # ----------------------------------------------------
        # THREE BLACK CROWS
        # ----------------------------------------------------

        if (
            is_bearish(a)
            and is_bearish(b)
            and is_bearish(c)
            and bc < ac
            and cc < bc
        ):

            patterns.append({
                "index": i,
                "name": "Three Black Crows-like sequence",
                "type": "bearish_continuation",
                "strength": "potentially_strong",
                "reason": "Three consecutive bearish closes with downward progression."
            })

    return patterns


# ============================================================
# CONTEXT EVALUATION
# ============================================================

def evaluate_pattern(pattern, candles):

    i = pattern["index"]

    candle = candles[i]

    before = candles[max(0, i - 5):i]

    after = candles[i + 1:min(len(candles), i + 4)]

    prior_directions = [direction(c) for c in before]

    after_directions = [direction(c) for c in after]

    prior_bullish = prior_directions.count("bullish")
    prior_bearish = prior_directions.count("bearish")

    after_bullish = after_directions.count("bullish")
    after_bearish = after_directions.count("bearish")

    previous_high = max(
        [values(c)[1] for c in before],
        default=None
    )

    previous_low = min(
        [values(c)[2] for c in before],
        default=None
    )

    current_close = values(candle)[3]

    context = []

    # --------------------------------------------------------
    # PREVIOUS DIRECTION
    # --------------------------------------------------------

    if prior_bearish > prior_bullish:

        context.append("preceded_by_bearish_pressure")

    elif prior_bullish > prior_bearish:

        context.append("preceded_by_bullish_pressure")

    else:

        context.append("preceded_by_balanced_pressure")

    # --------------------------------------------------------
    # LOCATION
    # --------------------------------------------------------

    if previous_low is not None:

        if values(candle)[2] <= previous_low:

            context.append("near_or_below_recent_low")

    if previous_high is not None:

        if values(candle)[1] >= previous_high:

            context.append("near_or_above_recent_high")

    # --------------------------------------------------------
    # CONFIRMATION
    # --------------------------------------------------------

    bullish_types = {
        "potential_bullish_reversal",
        "potential_bullish_transition",
        "bullish_continuation",
        "potential_bullish_rejection",
        "strong_bullish"
    }

    bearish_types = {
        "potential_bearish_reversal",
        "potential_bearish_transition",
        "bearish_continuation",
        "potential_bearish_rejection",
        "strong_bearish"
    }

    if pattern["type"] in bullish_types:

        if after_bullish > after_bearish:

            confirmation = "bullish_follow_through"

        elif after_bearish > after_bullish:

            confirmation = "bullish_pattern_failed"

        else:

            confirmation = "no_clear_confirmation"

    elif pattern["type"] in bearish_types:

        if after_bearish > after_bullish:

            confirmation = "bearish_follow_through"

        elif after_bullish > after_bearish:

            confirmation = "bearish_pattern_failed"

        else:

            confirmation = "no_clear_confirmation"

    else:

        confirmation = "not_directional"

    return {
        "context": context,
        "confirmation": confirmation
    }


# ============================================================
# LOAD MARKET MEMORY
# ============================================================

print("=" * 70)
print("MLAI v0.6 - LOADING MARKET MEMORY")
print("=" * 70)

print(f"File: {DATA_FILE}")


if not os.path.exists(DATA_FILE):

    print("ERROR: market_data.bin was not found.")
    raise SystemExit(1)


try:

    with open(DATA_FILE, "rb") as f:

        market_data = pickle.load(f)

except Exception as e:

    print(f"ERROR: Could not load market_data.bin: {e}")
    raise SystemExit(1)


if isinstance(market_data, dict):

    for key in ("candles", "data", "market_data", "records"):

        if key in market_data and isinstance(market_data[key], list):

            market_data = market_data[key]

            break


if not isinstance(market_data, list):

    print("ERROR: market_data.bin does not contain candle data.")
    raise SystemExit(1)


print("PASS: market_data.bin loaded")
print(f"Found {len(market_data)} stored candles.")
print()


if len(market_data) < LOOKBACK:

    print(
        f"ERROR: At least {LOOKBACK} candles are required."
    )

    raise SystemExit(1)


candles = market_data[-LOOKBACK:]


# ============================================================
# RUN PATTERN DETECTION
# ============================================================

single_patterns = detect_single_patterns(candles)

two_patterns = detect_two_candle_patterns(candles)

three_patterns = detect_three_candle_patterns(candles)

patterns = single_patterns + two_patterns + three_patterns

patterns.sort(key=lambda x: x["index"])


# ============================================================
# EVALUATE PATTERNS
# ============================================================

evaluated_patterns = []


for pattern in patterns:

    evaluation = evaluate_pattern(
        pattern,
        candles
    )

    pattern["context"] = evaluation["context"]

    pattern["confirmation"] = evaluation["confirmation"]

    evaluated_patterns.append(pattern)


# ============================================================
# STATISTICS
# ============================================================

bullish_patterns = 0
bearish_patterns = 0
indecision_patterns = 0
continuation_patterns = 0
compression_patterns = 0
expansion_patterns = 0

confirmed_patterns = 0
failed_patterns = 0


for pattern in evaluated_patterns:

    ptype = pattern["type"]

    if "bullish" in ptype:

        bullish_patterns += 1

    if "bearish" in ptype:

        bearish_patterns += 1

    if "indecision" in ptype:

        indecision_patterns += 1

    if "continuation" in ptype:

        continuation_patterns += 1

    if ptype == "compression":

        compression_patterns += 1

    if ptype == "expansion":

        expansion_patterns += 1

    if pattern["confirmation"] in (
        "bullish_follow_through",
        "bearish_follow_through"
    ):

        confirmed_patterns += 1

    if pattern["confirmation"] in (
        "bullish_pattern_failed",
        "bearish_pattern_failed"
    ):

        failed_patterns += 1


# ============================================================
# RECENT PATTERNS
# ============================================================

recent_patterns = [
    p for p in evaluated_patterns
    if p["index"] >= LOOKBACK - 15
]


# ============================================================
# PATTERN CONTEXT CLASSIFICATION
# ============================================================

if confirmed_patterns > failed_patterns * 1.5 and confirmed_patterns > 0:

    pattern_context = "patterns_show_some_follow_through"

elif failed_patterns > confirmed_patterns * 1.5 and failed_patterns > 0:

    pattern_context = "patterns_show_frequent_failure"

elif confirmed_patterns == 0 and failed_patterns == 0:

    pattern_context = "patterns_lack_directional_confirmation"

else:

    pattern_context = "mixed_pattern_evidence"


# ============================================================
# MARKET STORY
# ============================================================

story = []


story.append(
    f"The latest {LOOKBACK} candles contain "
    f"{len(evaluated_patterns)} detected pattern events."
)


if bullish_patterns > bearish_patterns:

    story.append(
        "Bullish-oriented pattern structures are more frequent "
        "than bearish-oriented structures."
    )

elif bearish_patterns > bullish_patterns:

    story.append(
        "Bearish-oriented pattern structures are more frequent "
        "than bullish-oriented structures."
    )

else:

    story.append(
        "Bullish and bearish pattern structures are relatively balanced."
    )


if confirmed_patterns > 0:

    story.append(
        f"{confirmed_patterns} pattern event(s) received "
        "directionally consistent follow-through."
    )


if failed_patterns > 0:

    story.append(
        f"{failed_patterns} pattern event(s) were followed by "
        "opposite-direction behaviour."
    )


if pattern_context == "patterns_show_frequent_failure":

    story.append(
        "Frequent pattern failure reduces confidence in treating "
        "individual formations as reliable directional evidence."
    )


elif pattern_context == "patterns_show_some_follow_through":

    story.append(
        "Some patterns received follow-through, although confirmation "
        "must still be interpreted within broader market structure."
    )


else:

    story.append(
        "The detected patterns do not provide strong standalone "
        "directional confirmation."
    )


story.append(
    "Pattern recognition is being treated as contextual evidence "
    "rather than an automatic trading signal."
)


story.append(
    "This interpretation describes observable price behaviour "
    "and does not prove hidden participant intentions."
)


market_story = " ".join(story)


# ============================================================
# OUTPUT
# ============================================================

print("Analysing latest 60 candles...")
print()

print("=" * 70)
print("MLAI v0.6 PATTERN / CONTEXT ENGINE")
print("=" * 70)

print(f"Candles analysed: {LOOKBACK}")
print()

print("PATTERN SUMMARY")
print("-" * 70)

print(f"Total pattern events       : {len(evaluated_patterns)}")
print(f"Bullish-oriented patterns  : {bullish_patterns}")
print(f"Bearish-oriented patterns  : {bearish_patterns}")
print(f"Indecision patterns        : {indecision_patterns}")
print(f"Continuation patterns      : {continuation_patterns}")
print(f"Compression patterns       : {compression_patterns}")
print(f"Expansion patterns         : {expansion_patterns}")

print()

print("CONFIRMATION")
print("-" * 70)

print(f"Confirmed patterns : {confirmed_patterns}")
print(f"Failed patterns    : {failed_patterns}")
print(f"Context state      : {pattern_context}")

print()

print("DETECTED PATTERNS")
print("-" * 70)


if not evaluated_patterns:

    print("- No major pattern formations detected.")

else:

    for p in evaluated_patterns:

        candle_number = p["index"] + 1

        print(
            f"- Candle {candle_number}: "
            f"{p['name']} | "
            f"{p['type']} | "
            f"confirmation={p['confirmation']}"
        )

        print(
            f"  Reason: {p['reason']}"
        )

        if p["context"]:

            print(
                f"  Context: {', '.join(p['context'])}"
            )


print()

print("RECENT PATTERN ACTIVITY")
print("-" * 70)


if not recent_patterns:

    print("- No recent pattern events detected.")

else:

    for p in recent_patterns:

        print(
            f"- Candle {p['index'] + 1}: "
            f"{p['name']} → "
            f"{p['confirmation']}"
        )


print()

print("PATTERN INTERPRETATION RULE")
print("-" * 70)

print(
    "A detected pattern is evidence, not an automatic prediction."
)

print(
    "Context, confirmation, failure, structure and historical "
    "behaviour must be evaluated together."
)

print()

print("MARKET STORY")
print("-" * 70)

print(market_story)

print()

print("=" * 70)


# ============================================================
# UPDATE PROJECT STATUS
# ============================================================

status_entry = f"""
## MLAI v0.6 — Pattern / Context Engine

Status: COMPLETED

Input:
- market_data.bin
- Latest {LOOKBACK} candles

Pattern/context capabilities implemented:
- Doji detection
- Hammer-like rejection detection
- Shooting-star-like rejection detection
- Spinning Top detection
- Bullish/Bearish Marubozu-like detection
- Range expansion detection
- Bullish Engulfing
- Bearish Engulfing
- Bullish Harami-like structures
- Bearish Harami-like structures
- Inside Bar
- Outside Bar
- Morning Star-like sequence
- Evening Star-like sequence
- Three White Soldiers-like sequence
- Three Black Crows-like sequence
- Pattern confirmation analysis
- Pattern failure analysis
- Prior directional context
- Recent high/low location
- Follow-through analysis
- Pattern evidence classification
- Pattern Market Story generation

Important:
Patterns are treated as contextual evidence.
Pattern names are NOT automatic trading signals.
The engine separates pattern observation from interpretation.

Next stage:
MLAI v0.7 — Historical Behaviour
"""


try:

    with open(STATUS_FILE, "a", encoding="utf-8") as f:

        f.write("\n" + status_entry)

    print()
    print(f"PASS: {STATUS_FILE} updated.")

except Exception as e:

    print()
    print(
        f"WARNING: Could not update {STATUS_FILE}: {e}"
    )


print()
print("PASS: MLAI v0.6 pattern/context analysis completed.")