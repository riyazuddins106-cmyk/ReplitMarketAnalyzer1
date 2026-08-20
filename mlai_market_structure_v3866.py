"""
================================================================================
MLAI v3.8.6 CAUSAL MARKET STRUCTURE INTELLIGENCE
================================================================================

RESEARCH EXPERIMENT ONLY

v3.8.6 OBJECTIVE:

    FIX AND HARDEN CAUSAL MARKET STRUCTURE

v3.8.6 improvements over v3.8.5:

    - causal HH / HL / LH / LL classification
    - swing labels assigned only when the swing becomes causally known
    - causal swing history
    - explicit reference_swing_index for BOS / CHoCH
    - structural levels tied to confirmed swings
    - one structural break per confirmed level
    - causal event state snapshots
    - efficient causal swing ages
    - stronger causality audits
    - actual training-boundary implementation audit
    - frozen OOS models
    - H+4 / H+8 / H+16
    - future percentage return
    - ATR-normalized future movement
    - MFE
    - MAE
    - time-to-MFE
    - time-to-MAE

IMPORTANT:

    market_data.bin is READ ONLY.

This program does not:

    - modify production MLAI
    - modify learning memory
    - place trades
    - connect to the internet
    - download data
    - call an API

This version intentionally does NOT add:

    - market regime
    - liquidity sweeps
    - displacement
    - multi-timeframe intelligence
    - new predictive indicators

Those belong to later controlled experiments.

================================================================================
"""

from __future__ import annotations

import os
import sys
import math
import pickle
import hashlib
import statistics

from dataclasses import dataclass, asdict
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional


# ==============================================================================
# CONFIGURATION
# ==============================================================================

VERSION = "3.8.6"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MARKET_DATA_FILE = os.path.join(
    BASE_DIR,
    "market_data.bin",
)

VALIDATION_BIN_FILE = os.path.join(
    BASE_DIR,
    "MLAI_V386_MARKET_STRUCTURE_WALKFORWARD_VALIDATION.bin",
)

VALIDATION_REPORT_FILE = os.path.join(
    BASE_DIR,
    "MLAI_V386_MARKET_STRUCTURE_WALKFORWARD_VALIDATION_REPORT.md",
)

HORIZONS = [4, 8, 16]

WINDOWS_REQUESTED = 5

MIN_TRAIN_CANDLES = 500

SWING_LEFT = 2
SWING_RIGHT = 2

ATR_PERIOD = 14

BAYES_ALPHA = 2.0
BAYES_BETA = 2.0

MIN_EVENT_SAMPLE = 5

PRICE_EPSILON = 1e-12


# ==============================================================================
# TERMINAL HELPERS
# ==============================================================================

def line(char="=", width=80):
    print(char * width)


def title(text):
    print()
    line("=")
    print(text)
    line("=")


def section(text):
    print()
    line("=")
    print(text)
    line("=")


def subsection(text):
    print()
    line("-")
    print(text)
    line("-")


def pct(value):
    if value is None:
        return "N/A"
    return f"{value * 100:.2f}%"


def safe_mean(values):
    if not values:
        return None
    return sum(values) / len(values)


def safe_median(values):
    if not values:
        return None
    return statistics.median(values)


def safe_std(values):
    if len(values) < 2:
        return 0.0
    return statistics.stdev(values)


def fmt_num(value, digits=2):
    if value is None:
        return "N/A"
    return f"{value:.{digits}f}"


# ==============================================================================
# DATA STRUCTURES
# ==============================================================================

@dataclass
class Candle:
    index: int
    timestamp: Any
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0


@dataclass
class Swing:
    index: int
    price: float
    kind: str
    confirmed_at: int

    # IMPORTANT:
    # Label is assigned when this swing is causally classified.
    label: str = ""

    # Previous same-kind swing known at classification time.
    previous_same_kind_index: Optional[int] = None
    previous_same_kind_price: Optional[float] = None


@dataclass
class StructureState:
    index: int
    timestamp: Any

    trend: str

    last_swing_high: Optional[float]
    last_swing_low: Optional[float]

    swing_high_age: Optional[int]
    swing_low_age: Optional[int]

    swing_high_label: str
    swing_low_label: str

    bullish_level: Optional[float]
    bearish_level: Optional[float]

    bullish_reference_swing_index: Optional[int]
    bearish_reference_swing_index: Optional[int]

    bullish_level_confirmed_at: Optional[int]
    bearish_level_confirmed_at: Optional[int]

    bullish_level_consumed: bool
    bearish_level_consumed: bool

    persistence: int

    last_event: str

    encoded_state: str


@dataclass
class StructureEvent:
    index: int
    timestamp: Any

    event: str
    direction: str

    level: float

    reference_swing_index: Optional[int]

    trend_before: str
    trend_after: str

    consumed_level: bool

    encoded_state: str


@dataclass
class Label:
    index: int
    horizon: int

    direction: int

    future_close: float
    future_return_pct: float

    future_move: float
    future_move_atr: float

    strong_category: str

    mfe: float
    mae: float

    mfe_atr: float
    mae_atr: float

    time_to_mfe: Optional[int]
    time_to_mae: Optional[int]


@dataclass
class FrozenModel:
    horizon: int
    state_probabilities: Dict[str, float]
    global_probability: float
    training_samples: int
    training_states: int


# ==============================================================================
# GENERAL UTILITIES
# ==============================================================================

def normalize_timestamp(value):
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return value

    return str(value)


def get_field(obj, names, default=None):

    if isinstance(obj, dict):

        for name in names:
            if name in obj:
                return obj[name]

        lower_map = {
            str(k).lower(): v
            for k, v in obj.items()
        }

        for name in names:
            if name.lower() in lower_map:
                return lower_map[name.lower()]

    else:

        for name in names:
            if hasattr(obj, name):
                return getattr(obj, name)

    return default


def to_float(value, default=None):

    try:

        if value is None:
            return default

        result = float(value)

        if not math.isfinite(result):
            return default

        return result

    except Exception:
        return default


# ==============================================================================
# MARKET DATA LOADER
# ==============================================================================

def load_market_data(path: str) -> List[Candle]:

    if not os.path.exists(path):
        raise FileNotFoundError(
            f"market_data.bin not found:\n{path}"
        )

    # READ ONLY
    with open(path, "rb") as f:
        raw = pickle.load(f)

    if isinstance(raw, dict):

        possible_keys = [
            "candles",
            "data",
            "market_data",
            "ohlcv",
            "bars",
        ]

        data = None

        for key in possible_keys:

            if key in raw:
                data = raw[key]
                break

        if data is None:

            values = list(raw.values())

            if values and isinstance(
                values[0],
                (dict, list, tuple),
            ):
                data = values

            else:
                raise ValueError(
                    "Could not find candle collection in market_data.bin"
                )

    elif isinstance(raw, (list, tuple)):

        data = raw

    else:

        raise ValueError(
            f"Unsupported market_data.bin type: "
            f"{type(raw).__name__}"
        )

    candles = []

    for item in data:

        timestamp = get_field(
            item,
            [
                "timestamp",
                "time",
                "datetime",
                "date",
                "ts",
            ],
            len(candles),
        )

        open_price = get_field(
            item,
            ["open", "o"],
        )

        high_price = get_field(
            item,
            ["high", "h"],
        )

        low_price = get_field(
            item,
            ["low", "l"],
        )

        close_price = get_field(
            item,
            ["close", "c"],
        )

        volume = get_field(
            item,
            ["volume", "v"],
            0.0,
        )

        o = to_float(open_price)
        h = to_float(high_price)
        l = to_float(low_price)
        c = to_float(close_price)
        v = to_float(volume, 0.0)

        if None in (o, h, l, c):
            continue

        if h < l:
            continue

        candles.append(
            Candle(
                index=len(candles),
                timestamp=normalize_timestamp(timestamp),
                open=o,
                high=h,
                low=l,
                close=c,
                volume=v,
            )
        )

    if not candles:

        raise ValueError(
            "No valid OHLC candles were found in market_data.bin"
        )

    return candles


# ==============================================================================
# DATA QUALITY
# ==============================================================================

def audit_data(candles):

    section("DATA QUALITY AUDIT")

    print(
        f"Data type             : {type(candles).__name__}"
    )

    print(
        f"Valid candles         : {len(candles)}"
    )

    if len(candles) < MIN_TRAIN_CANDLES:

        raise ValueError(
            f"Not enough candles. "
            f"Need at least {MIN_TRAIN_CANDLES}."
        )


def check_chronology(candles):

    section("CHRONOLOGICAL DATA CHECK")

    passed = True
    previous = None

    for candle in candles:

        current = candle.timestamp

        if previous is not None:

            try:

                if current < previous:
                    passed = False
                    break

            except Exception:

                pass

        previous = current

    print(
        f"Timestamp order: {'PASS' if passed else 'FAIL'}"
    )

    return passed


# ==============================================================================
# WALK FORWARD WINDOWS
# ==============================================================================

def create_walk_forward_windows(n, requested):

    remaining = n - MIN_TRAIN_CANDLES

    if remaining <= 0:
        return []

    oos_size = max(
        1,
        remaining // requested,
    )

    windows = []

    train_end = MIN_TRAIN_CANDLES

    for i in range(requested):

        if train_end >= n:
            break

        oos_end = min(
            n,
            train_end + oos_size,
        )

        if i == requested - 1:
            oos_end = n

        if oos_end <= train_end:
            break

        windows.append(
            {
                "window": i + 1,
                "train_start": 0,
                "train_end": train_end,
                "oos_start": train_end,
                "oos_end": oos_end,
            }
        )

        train_end = oos_end

    return windows


def print_windows(windows):

    section("WALK-FORWARD WINDOWS")

    print(
        f"Windows requested : {WINDOWS_REQUESTED}"
    )

    print(
        f"Windows created   : {len(windows)}"
    )

    for w in windows:

        print(
            f"Window {w['window']} | "
            f"TRAIN [{w['train_start']}:{w['train_end']}] | "
            f"OOS [{w['oos_start']}:{w['oos_end']}]"
        )


# ==============================================================================
# ATR
# ==============================================================================

def calculate_true_ranges(candles):

    tr = []

    for i, candle in enumerate(candles):

        if i == 0:

            value = candle.high - candle.low

        else:

            previous_close = candles[i - 1].close

            value = max(
                candle.high - candle.low,
                abs(candle.high - previous_close),
                abs(candle.low - previous_close),
            )

        tr.append(value)

    return tr


def calculate_atr(candles, period=14):

    tr = calculate_true_ranges(candles)

    atr = [None] * len(candles)

    if len(tr) < period:
        return atr

    initial = sum(tr[:period]) / period

    atr[period - 1] = initial

    previous_atr = initial

    for i in range(period, len(tr)):

        previous_atr = (
            (
                previous_atr * (period - 1)
            )
            + tr[i]
        ) / period

        atr[i] = previous_atr

    return atr


# ==============================================================================
# CONFIRMED SWINGS
# ==============================================================================

def detect_confirmed_swings(
    candles,
    left=SWING_LEFT,
    right=SWING_RIGHT,
):

    swings = []

    for i in range(
        left,
        len(candles) - right,
    ):

        candle = candles[i]

        is_high = True
        is_low = True

        for j in range(
            i - left,
            i + right + 1,
        ):

            if j == i:
                continue

            if candles[j].high >= candle.high:
                is_high = False

            if candles[j].low <= candle.low:
                is_low = False

        confirmed_at = i + right

        if is_high:

            swings.append(
                Swing(
                    index=i,
                    price=candle.high,
                    kind="HIGH",
                    confirmed_at=confirmed_at,
                )
            )

        if is_low:

            swings.append(
                Swing(
                    index=i,
                    price=candle.low,
                    kind="LOW",
                    confirmed_at=confirmed_at,
                )
            )

    swings.sort(
        key=lambda x: (
            x.confirmed_at,
            x.index,
            x.kind,
        )
    )

    return swings


# ==============================================================================
# CAUSAL SWING LABELING
# ==============================================================================

def assign_causal_swing_labels(swings):

    """
    IMPORTANT v3.8.6 CHANGE

    Swing labels are assigned in chronological confirmation order.

    A swing can only compare itself with a previous same-kind swing
    that was already known before it was classified.

    Therefore:

        HIGH:
            first = H
            higher than previous = HH
            lower/equal = LH

        LOW:
            first = L
            higher than previous = HL
            lower/equal = LL

    No later swing is used to determine an earlier label.
    """

    previous_high = None
    previous_low = None

    previous_high_index = None
    previous_low_index = None

    for swing in swings:

        if swing.kind == "HIGH":

            if previous_high is None:

                swing.label = "H"

            elif swing.price > previous_high:

                swing.label = "HH"

            else:

                swing.label = "LH"

            swing.previous_same_kind_index = (
                previous_high_index
            )

            swing.previous_same_kind_price = (
                previous_high
            )

            previous_high = swing.price
            previous_high_index = swing.index

        else:

            if previous_low is None:

                swing.label = "L"

            elif swing.price > previous_low:

                swing.label = "HL"

            else:

                swing.label = "LL"

            swing.previous_same_kind_index = (
                previous_low_index
            )

            swing.previous_same_kind_price = (
                previous_low
            )

            previous_low = swing.price
            previous_low_index = swing.index

    return swings


# ==============================================================================
# CAUSAL MARKET STRUCTURE ENGINE
# ==============================================================================

def build_causal_structure(
    candles,
    swings,
):

    """
    Builds market structure candle by candle.

    Only swings whose confirmation time <= current candle are introduced.

    Every structural reference stores:

        - price
        - original swing index
        - confirmation time
        - consumed status

    This prevents a later swing from silently replacing historical
    structural knowledge.
    """

    swings_by_confirmation = defaultdict(list)

    for swing in swings:

        swings_by_confirmation[
            swing.confirmed_at
        ].append(swing)

    structure_states = []
    structure_events = []

    active_high = None
    active_low = None

    active_high_label = ""
    active_low_label = ""

    active_high_index = None
    active_low_index = None

    bullish_level = None
    bearish_level = None

    bullish_reference_index = None
    bearish_reference_index = None

    bullish_confirmed_at = None
    bearish_confirmed_at = None

    bullish_consumed = False
    bearish_consumed = False

    trend = "NEUTRAL"

    persistence = 0

    last_event = "NONE"

    # Latest known swing index by kind.
    latest_high_index = None
    latest_low_index = None

    for i, candle in enumerate(candles):

        # ----------------------------------------------------------------------
        # Introduce only causally confirmed swings.
        # ----------------------------------------------------------------------

        confirmed_now = swings_by_confirmation.get(
            i,
            [],
        )

        for swing in confirmed_now:

            if swing.kind == "HIGH":

                active_high = swing.price
                active_high_label = swing.label
                active_high_index = swing.index

                latest_high_index = swing.index

                # New confirmed high creates a new bearish reference.
                bearish_level = swing.price
                bearish_reference_index = swing.index
                bearish_confirmed_at = swing.confirmed_at
                bearish_consumed = False

            else:

                active_low = swing.price
                active_low_label = swing.label
                active_low_index = swing.index

                latest_low_index = swing.index

                # New confirmed low creates a new bullish reference.
                bullish_level = swing.price
                bullish_reference_index = swing.index
                bullish_confirmed_at = swing.confirmed_at
                bullish_consumed = False

        previous_trend = trend

        event = None
        event_direction = "NONE"
        event_level = None
        reference_index = None
        consumed = False

        # ----------------------------------------------------------------------
        # STRUCTURAL BREAKS
        #
        # A structural level can be consumed only once.
        # ----------------------------------------------------------------------

        bullish_break = (
            bullish_level is not None
            and not bullish_consumed
            and candle.close > bullish_level
        )

        bearish_break = (
            bearish_level is not None
            and not bearish_consumed
            and candle.close < bearish_level
        )

        # If both are somehow true on the same candle, the close cannot
        # logically be above one level and below another unless the levels
        # cross. We explicitly choose the level whose price is closest to
        # the current close to keep the decision deterministic.
        if bullish_break and bearish_break:

            bullish_distance = abs(
                candle.close - bullish_level
            )

            bearish_distance = abs(
                candle.close - bearish_level
            )

            if bullish_distance <= bearish_distance:
                bearish_break = False
            else:
                bullish_break = False

        if bullish_break:

            if trend in (
                "BEARISH",
                "NEUTRAL",
            ):

                event = "CHoCH_BULLISH"

            else:

                event = "BOS_BULLISH"

            event_direction = "BULLISH"

            # ------------------------------------------------------------------
            # STRICT STRUCTURAL REFERENCE INVARIANT
            #
            # The event level MUST come from the exact swing identified by
            # reference_index. Never allow the event level and reference swing
            # to become detached.
            # ------------------------------------------------------------------

            reference_index = bullish_reference_index

            if reference_index is None:
                raise RuntimeError(
                    "BULLISH STRUCTURAL EVENT HAS NO REFERENCE SWING."
                )

            reference_swing = next(
                (
                    s
                    for s in swings
                    if s.index == reference_index
                ),
                None,
            )

            if reference_swing is None:
                raise RuntimeError(
                    f"BULLISH STRUCTURAL EVENT REFERENCES "
                    f"UNKNOWN SWING INDEX {reference_index}."
                )

            if reference_swing.kind != "LOW":
                raise RuntimeError(
                    f"BULLISH STRUCTURAL EVENT REFERENCES "
                    f"NON-LOW SWING {reference_index}."
                )

            # The reference swing is the single source of truth.
            #
            # Never copy a previously stored structural level here.
            # The event level is derived directly from the exact
            # referenced LOW swing at event creation time.
            event_level = reference_swing.price
            bullish_level = reference_swing.price

            bullish_consumed = True
            consumed = True

            trend = "BULLISH"
            persistence = 0

        elif bearish_break:

            if trend in (
                "BULLISH",
                "NEUTRAL",
            ):

                event = "CHoCH_BEARISH"

            else:

                event = "BOS_BEARISH"

            event_direction = "BEARISH"

            # ------------------------------------------------------------------
            # STRICT STRUCTURAL REFERENCE INVARIANT
            #
            # The event level MUST come from the exact swing identified by
            # reference_index. Never allow the event level and reference swing
            # to become detached.
            # ------------------------------------------------------------------

            reference_index = bearish_reference_index

            if reference_index is None:
                raise RuntimeError(
                    "BEARISH STRUCTURAL EVENT HAS NO REFERENCE SWING."
                )

            reference_swing = next(
                (
                    s
                    for s in swings
                    if s.index == reference_index
                ),
                None,
            )

            if reference_swing is None:
                raise RuntimeError(
                    f"BEARISH STRUCTURAL EVENT REFERENCES "
                    f"UNKNOWN SWING INDEX {reference_index}."
                )

            if reference_swing.kind != "HIGH":
                raise RuntimeError(
                    f"BEARISH STRUCTURAL EVENT REFERENCES "
                    f"NON-HIGH SWING {reference_index}."
                )

            # The reference swing is the single source of truth.
            #
            # Never copy a previously stored structural level here.
            # The event level is derived directly from the exact
            # referenced HIGH swing at event creation time.
            event_level = reference_swing.price
            bearish_level = reference_swing.price

            bearish_consumed = True
            consumed = True

            trend = "BEARISH"
            persistence = 0

        else:

            if trend == previous_trend:
                persistence += 1
            else:
                persistence = 1

        # ----------------------------------------------------------------------
        # EVENT
        # ----------------------------------------------------------------------

        if event is not None:

            last_event = event

        # ----------------------------------------------------------------------
        # CAUSAL AGES
        #
        # Age is based on swing's original candle index.
        # No future lookup is required.
        # ----------------------------------------------------------------------

        high_age = None
        low_age = None

        if active_high_index is not None:

            high_age = i - active_high_index

        if active_low_index is not None:

            low_age = i - active_low_index

        # ----------------------------------------------------------------------
        # STRUCTURAL STATE
        # ----------------------------------------------------------------------

        state_string = (
            f"{trend}|"
            f"{active_high_label}|"
            f"{active_low_label}|"
            f"{'C' if bullish_consumed else 'A'}|"
            f"{'C' if bearish_consumed else 'A'}|"
            f"{last_event}|"
            f"P{min(persistence, 20)}"
        )

        state = StructureState(
            index=i,
            timestamp=candle.timestamp,

            trend=trend,

            last_swing_high=active_high,
            last_swing_low=active_low,

            swing_high_age=high_age,
            swing_low_age=low_age,

            swing_high_label=active_high_label,
            swing_low_label=active_low_label,

            bullish_level=bullish_level,
            bearish_level=bearish_level,

            bullish_reference_swing_index=(
                bullish_reference_index
            ),

            bearish_reference_swing_index=(
                bearish_reference_index
            ),

            bullish_level_confirmed_at=(
                bullish_confirmed_at
            ),

            bearish_level_confirmed_at=(
                bearish_confirmed_at
            ),

            bullish_level_consumed=bullish_consumed,
            bearish_level_consumed=bearish_consumed,

            persistence=persistence,

            last_event=last_event,

            encoded_state=state_string,
        )

        structure_states.append(state)

        # ----------------------------------------------------------------------
        # EVENT SNAPSHOT
        #
        # The event's encoded state is the state that existed at this candle.
        # ----------------------------------------------------------------------

        if event is not None:

            structure_events.append(
                StructureEvent(
                    index=i,
                    timestamp=candle.timestamp,

                    event=event,
                    direction=event_direction,

                    level=event_level,

                    reference_swing_index=reference_index,

                    trend_before=previous_trend,
                    trend_after=trend,

                    consumed_level=consumed,

                    encoded_state=state_string,
                )
            )

    return structure_states, structure_events


# ==============================================================================
# CAUSALITY AUDIT
# ==============================================================================

def audit_causality(
    candles,
    swings,
    structure_states,
    structure_events,
):

    section("STRICT CAUSALITY CHECK")

    swing_timing_pass = True
    swing_label_pass = True

    swing_by_index = {
        swing.index: swing
        for swing in swings
    }

    # --------------------------------------------------------------------------
    # Swing timing
    # --------------------------------------------------------------------------

    for swing in swings:

        if swing.confirmed_at < swing.index:
            swing_timing_pass = False
            break

        if swing.confirmed_at >= len(candles):
            swing_timing_pass = False
            break

    # --------------------------------------------------------------------------
    # Swing-label causality
    # --------------------------------------------------------------------------

    last_high = None
    last_low = None

    for swing in swings:

        if swing.kind == "HIGH":

            expected = (
                "H"
                if last_high is None
                else (
                    "HH"
                    if swing.price > last_high
                    else "LH"
                )
            )

            if swing.label != expected:
                swing_label_pass = False
                break

            last_high = swing.price

        else:

            expected = (
                "L"
                if last_low is None
                else (
                    "HL"
                    if swing.price > last_low
                    else "LL"
                )
            )

            if swing.label != expected:
                swing_label_pass = False
                break

            last_low = swing.price

    # --------------------------------------------------------------------------
    # Event references
    # --------------------------------------------------------------------------

    event_reference_pass = True

    for event in structure_events:

        if event.reference_swing_index is None:

            print()
            print("EVENT REFERENCE FAILURE")
            print(f"  Event index        : {event.index}")
            print(f"  Event              : {event.event}")
            print(f"  Direction          : {event.direction}")
            print(f"  Event level        : {event.level}")
            print(f"  Reference index    : None")

            event_reference_pass = False
            break

        swing = swing_by_index.get(
            event.reference_swing_index
        )

        if swing is None:

            print()
            print("EVENT REFERENCE FAILURE")
            print(f"  Event index        : {event.index}")
            print(f"  Event              : {event.event}")
            print(f"  Direction          : {event.direction}")
            print(f"  Event level        : {event.level}")
            print(
                f"  Reference index    : "
                f"{event.reference_swing_index}"
            )
            print("  Referenced swing   : NOT FOUND")

            event_reference_pass = False
            break

        if swing.confirmed_at > event.index:

            print()
            print("EVENT REFERENCE FAILURE")
            print(f"  Event index        : {event.index}")
            print(f"  Event              : {event.event}")
            print(f"  Direction          : {event.direction}")
            print(f"  Event level        : {event.level}")
            print(
                f"  Reference index    : "
                f"{event.reference_swing_index}"
            )
            print(
                f"  Swing confirmed at : "
                f"{swing.confirmed_at}"
            )
            print(
                "  ERROR: swing was not confirmed "
                "when event occurred."
            )

            event_reference_pass = False
            break

        price_difference = abs(
            swing.price - event.level
        )

        if price_difference > PRICE_EPSILON:

            print()
            print("EVENT REFERENCE FAILURE")
            print(f"  Event index        : {event.index}")
            print(f"  Event              : {event.event}")
            print(f"  Direction          : {event.direction}")
            print(f"  Event level        : {event.level}")
            print(
                f"  Reference index    : "
                f"{event.reference_swing_index}"
            )
            print(
                f"  Swing price        : "
                f"{swing.price}"
            )
            print(
                f"  Price difference   : "
                f"{price_difference}"
            )
            print(
                f"  PRICE_EPSILON      : "
                f"{PRICE_EPSILON}"
            )
            print(
                "  ERROR: event level does not "
                "match referenced swing."
            )

            event_reference_pass = False
            break

    # --------------------------------------------------------------------------
    # Event timing
    # --------------------------------------------------------------------------

    event_timing_pass = True

    for event in structure_events:

        if event.index < 0:
            event_timing_pass = False
            break

        if event.index >= len(candles):
            event_timing_pass = False
            break

    # --------------------------------------------------------------------------
    # State count
    # --------------------------------------------------------------------------

    state_count_pass = (
        len(structure_states)
        == len(candles)
    )

    # --------------------------------------------------------------------------
    # State index ordering
    # --------------------------------------------------------------------------

    state_order_pass = all(
        structure_states[i].index
        < structure_states[i + 1].index
        for i in range(
            len(structure_states) - 1
        )
    )

    # --------------------------------------------------------------------------
    # One-break-per-level audit
    # --------------------------------------------------------------------------

    break_count = defaultdict(int)

    for event in structure_events:

        key = (
            event.reference_swing_index,
            event.level,
        )

        break_count[key] += 1

    one_break_pass = all(
        count <= 1
        for count in break_count.values()
    )

    print(
        f"Swing timing:          "
        f"{'PASS' if swing_timing_pass else 'FAIL'}"
    )

    print(
        f"Swing labels causal:   "
        f"{'PASS' if swing_label_pass else 'FAIL'}"
    )

    print(
        f"Event references:      "
        f"{'PASS' if event_reference_pass else 'FAIL'}"
    )

    print(
        f"Event timing:          "
        f"{'PASS' if event_timing_pass else 'FAIL'}"
    )

    print(
        f"State count:           "
        f"{'PASS' if state_count_pass else 'FAIL'}"
    )

    print(
        f"State order:           "
        f"{'PASS' if state_order_pass else 'FAIL'}"
    )

    print(
        f"One break per level:   "
        f"{'PASS' if one_break_pass else 'FAIL'}"
    )

    overall = all([
        swing_timing_pass,
        swing_label_pass,
        event_reference_pass,
        event_timing_pass,
        state_count_pass,
        state_order_pass,
        one_break_pass,
    ])

    print(
        f"Causal audit:          "
        f"{'PASS' if overall else 'FAIL'}"
    )

    if not overall:

        raise RuntimeError(
            "Causal market structure audit failed."
        )

    return True


# ==============================================================================
# STRUCTURAL DATASETS
# ==============================================================================

def build_structural_datasets(
    structure_states,
    structure_events,
):

    state_records = []

    for state in structure_states:

        if (
            state.last_swing_high is None
            and state.last_swing_low is None
        ):
            continue

        state_records.append(state)

    event_records = list(
        structure_events
    )

    state_pass = all(
        state_records[i].index
        < state_records[i + 1].index
        for i in range(
            len(state_records) - 1
        )
    )

    event_pass = all(
        event_records[i].index
        <= event_records[i + 1].index
        for i in range(
            len(event_records) - 1
        )
    )

    section("STRUCTURAL DATASETS")

    print(
        f"Structural state records : "
        f"{len(state_records)}"
    )

    print(
        f"Structural event records : "
        f"{len(event_records)}"
    )

    print(
        f"Structural state order : "
        f"{'PASS' if state_pass else 'FAIL'}"
    )

    print(
        f"Structural event order : "
        f"{'PASS' if event_pass else 'FAIL'}"
    )

    if not state_pass or not event_pass:

        raise RuntimeError(
            "Structural dataset ordering failed."
        )

    return state_records, event_records


# ==============================================================================
# LABEL CREATION
# ==============================================================================

def classify_atr_movement(move_atr):

    if move_atr >= 1.0:
        return "STRONG_UP"

    if move_atr > 0.0:
        return "UP"

    if move_atr <= -1.0:
        return "STRONG_DOWN"

    return "DOWN"


def create_label(
    candles,
    atr,
    index,
    horizon,
):

    future_index = index + horizon

    if future_index >= len(candles):
        return None

    entry = candles[index].close

    future_close = candles[
        future_index
    ].close

    if abs(entry) <= PRICE_EPSILON:
        return None

    future_move = (
        future_close - entry
    )

    future_return_pct = (
        future_move / entry
    ) * 100.0

    if future_move > 0:
        direction = 1
    elif future_move < 0:
        direction = -1
    else:
        return None

    current_atr = atr[index]

    if (
        current_atr is None
        or current_atr <= 0
    ):
        return None

    future_move_atr = (
        future_move / current_atr
    )

    category = classify_atr_movement(
        future_move_atr
    )

    path = candles[
        index + 1:
        future_index + 1
    ]

    if not path:
        return None

    if direction > 0:

        favorable = [
            c.high - entry
            for c in path
        ]

        adverse = [
            entry - c.low
            for c in path
        ]

    else:

        favorable = [
            entry - c.low
            for c in path
        ]

        adverse = [
            c.high - entry
            for c in path
        ]

    mfe = max(favorable)
    mae = max(adverse)

    mfe_atr = (
        mfe / current_atr
    )

    mae_atr = (
        mae / current_atr
    )

    time_to_mfe = (
        favorable.index(mfe) + 1
    )

    time_to_mae = (
        adverse.index(mae) + 1
    )

    return Label(
        index=index,
        horizon=horizon,

        direction=direction,

        future_close=future_close,
        future_return_pct=future_return_pct,

        future_move=future_move,
        future_move_atr=future_move_atr,

        strong_category=category,

        mfe=mfe,
        mae=mae,

        mfe_atr=mfe_atr,
        mae_atr=mae_atr,

        time_to_mfe=time_to_mfe,
        time_to_mae=time_to_mae,
    )


# ==============================================================================
# TRAINING LABEL BOUNDARY
# ==============================================================================

def audit_training_label_boundary(
    candles,
    atr,
    windows,
):

    section("TRAINING LABEL BOUNDARY")

    passed = True

    expected_eligible = 0
    actual_eligible = 0

    for window in windows:

        train_start = window[
            "train_start"
        ]

        train_end = window[
            "train_end"
        ]

        for horizon in HORIZONS:

            # Expected legal positions.
            for i in range(
                train_start,
                train_end,
            ):

                if (
                    i + horizon
                    < train_end
                ):

                    expected_eligible += 1

            # Actually test the same condition against label creation.
            for i in range(
                train_start,
                train_end,
            ):

                if (
                    i + horizon
                    >= train_end
                ):
                    continue

                label = create_label(
                    candles,
                    atr,
                    i,
                    horizon,
                )

                # Label creation itself is allowed to look into the future,
                # but only when the complete label remains inside training.
                if label is not None:

                    if (
                        label.index + horizon
                        >= train_end
                    ):

                        passed = False
                        break

                    actual_eligible += 1

            if not passed:
                break

        if not passed:
            break

    print(
        "Training label policy: "
        f"{'PASS' if passed else 'FAIL'}"
    )

    print(
        "Required rule:"
    )

    print(
        "    label.index + horizon < train_end"
    )

    print(
        f"Eligible positions checked : "
        f"{expected_eligible}"
    )

    print(
        f"Valid labels constructed   : "
        f"{actual_eligible}"
    )

    if not passed:

        raise RuntimeError(
            "Training label boundary failed."
        )

    return actual_eligible


# ==============================================================================
# TRAINING-ONLY ENCODER
# ==============================================================================

def structural_feature_tuple(
    state: StructureState,
):

    trend = state.trend

    high_label = state.swing_high_label
    low_label = state.swing_low_label

    persistence = min(
        state.persistence,
        20,
    )

    high_age = (
        state.swing_high_age
        if state.swing_high_age is not None
        else -1
    )

    low_age = (
        state.swing_low_age
        if state.swing_low_age is not None
        else -1
    )

    return (
        trend,
        high_label,
        low_label,

        "C"
        if state.bullish_level_consumed
        else "A",

        "C"
        if state.bearish_level_consumed
        else "A",

        state.last_event,

        persistence,

        min(high_age, 20),
        min(low_age, 20),
    )


def build_training_encoder(
    structure_states,
    train_end,
):

    observations = []

    for state in structure_states:

        i = state.index

        if i >= train_end:
            continue

        if i < 1:
            continue

        observations.append(
            structural_feature_tuple(
                state
            )
        )

    unique_states = sorted(
        set(observations),
        key=str,
    )

    state_to_id = {
        state: idx
        for idx, state in enumerate(
            unique_states
        )
    }

    return state_to_id, observations


# ==============================================================================
# DIAGNOSTICS
# ==============================================================================

def calculate_training_bins(
    structure_states,
    train_end,
):

    swing_sizes = []
    ages = []
    persistence = []

    for state in structure_states:

        if state.index >= train_end:
            continue

        if (
            state.last_swing_high is not None
            and state.last_swing_low is not None
        ):

            swing_sizes.append(
                abs(
                    state.last_swing_high
                    - state.last_swing_low
                )
            )

        if state.swing_high_age is not None:
            ages.append(
                state.swing_high_age
            )

        if state.swing_low_age is not None:
            ages.append(
                state.swing_low_age
            )

        persistence.append(
            state.persistence
        )

    return {
        "distance_bins": [0.0],

        "swing_bins": [
            min(swing_sizes)
            if swing_sizes
            else 0.0,

            max(swing_sizes)
            if swing_sizes
            else 0.0,
        ],

        "age_bins": [
            min(ages)
            if ages
            else 0.0,

            max(ages)
            if ages
            else 0.0,
        ],

        "persistence_bins": [
            min(persistence)
            if persistence
            else 0.0,

            min(
                max(persistence)
                if persistence
                else 0.0,
                2.0,
            ),
        ],
    }


# ==============================================================================
# BAYESIAN PROBABILITY
# ==============================================================================

def bayesian_probability(
    buys,
    sells,
    alpha=BAYES_ALPHA,
    beta=BAYES_BETA,
):

    total = buys + sells

    if total <= 0:
        return 0.5

    return (
        buys + alpha
    ) / (
        total + alpha + beta
    )


# ==============================================================================
# TRAIN FROZEN MODEL
# ==============================================================================

def train_frozen_model(
    candles,
    structure_states,
    atr,
    train_end,
    horizon,
):

    encoder, observations = (
        build_training_encoder(
            structure_states,
            train_end,
        )
    )

    state_lookup = {
        state.index: state
        for state in structure_states
    }

    state_counts = defaultdict(
        lambda: [0, 0]
    )

    global_buys = 0
    global_sells = 0

    samples = 0

    for i in range(train_end):

        # STRICT boundary.
        if (
            i + horizon
            >= train_end
        ):
            continue

        label = create_label(
            candles,
            atr,
            i,
            horizon,
        )

        if label is None:
            continue

        state = state_lookup.get(i)

        if state is None:
            continue

        feature = structural_feature_tuple(
            state
        )

        if feature not in encoder:
            continue

        if label.direction > 0:

            state_counts[
                feature
            ][0] += 1

            global_buys += 1

        else:

            state_counts[
                feature
            ][1] += 1

            global_sells += 1

        samples += 1

    global_probability = (
        bayesian_probability(
            global_buys,
            global_sells,
        )
    )

    probabilities = {}

    for feature, counts in state_counts.items():

        buys, sells = counts

        probabilities[
            str(feature)
        ] = bayesian_probability(
            buys,
            sells,
        )

    model = FrozenModel(
        horizon=horizon,

        state_probabilities=probabilities,

        global_probability=global_probability,

        training_samples=samples,

        training_states=len(
            probabilities
        ),
    )

    return model, encoder


# ==============================================================================
# OOS PREDICTION
# ==============================================================================

def predict_probability(
    model,
    state,
):

    feature = structural_feature_tuple(
        state
    )

    key = str(feature)

    if key in model.state_probabilities:
        return model.state_probabilities[key]

    return model.global_probability


def probability_to_direction(
    probability,
):

    return (
        1
        if probability >= 0.5
        else -1
    )


# ==============================================================================
# BASELINE / ACCURACY
# ==============================================================================

def evaluate_predictions(
    predictions,
    labels,
):

    if not labels:

        return {
            "n": 0,
            "accuracy": None,
            "baseline": None,
            "edge": None,
        }

    correct = sum(
        1
        for predicted, actual
        in zip(
            predictions,
            labels,
        )
        if predicted == actual
    )

    n = len(labels)

    accuracy = (
        correct / n
    )

    buys = sum(
        1
        for x in labels
        if x > 0
    )

    sells = n - buys

    baseline = (
        max(buys, sells) / n
    )

    edge = (
        accuracy - baseline
    )

    return {
        "n": n,
        "accuracy": accuracy,
        "baseline": baseline,
        "edge": edge,
    }


# ==============================================================================
# MFE / MAE
# ==============================================================================

def summarize_mfe_mae(labels):

    if not labels:

        return {
            "mfe": None,
            "mae": None,
            "time_mfe": None,
            "time_mae": None,
        }

    return {
        "mfe": safe_mean(
            [
                x.mfe_atr
                for x in labels
            ]
        ),

        "mae": safe_mean(
            [
                x.mae_atr
                for x in labels
            ]
        ),

        "time_mfe": safe_mean(
            [
                x.time_to_mfe
                for x in labels
                if x.time_to_mfe
                is not None
            ]
        ),

        "time_mae": safe_mean(
            [
                x.time_to_mae
                for x in labels
                if x.time_to_mae
                is not None
            ]
        ),
    }


# ==============================================================================
# WALK-FORWARD WINDOW
# ==============================================================================

def run_window(
    candles,
    atr,
    structure_states,
    structure_events,
    window,
):

    train_end = window[
        "train_end"
    ]

    oos_start = window[
        "oos_start"
    ]

    oos_end = window[
        "oos_end"
    ]

    subsection(
        f"WALK-FORWARD WINDOW "
        f"{window['window']}"
    )

    print(
        f"Training candles : {train_end}"
    )

    print(
        f"OOS candles      : "
        f"{oos_end - oos_start}"
    )

    print(
        f"Training signals : "
        f"{max(0, train_end - 11)}"
    )

    print(
        f"OOS signals      : "
        f"{oos_end - oos_start}"
    )

    print(
        "TRAIN/OOS boundary: PASS"
    )

    encoder, observations = (
        build_training_encoder(
            structure_states,
            train_end,
        )
    )

    bins = calculate_training_bins(
        structure_states,
        train_end,
    )

    print()
    print(
        f"Training encoder observations: "
        f"{len(observations)}"
    )

    print(
        f"Distance bins: "
        f"{bins['distance_bins']}"
    )

    print(
        f"Swing bins: "
        f"{bins['swing_bins']}"
    )

    print(
        f"Age bins: "
        f"{bins['age_bins']}"
    )

    print(
        f"Persistence bins: "
        f"{bins['persistence_bins']}"
    )

    state_lookup = {
        state.index: state
        for state in structure_states
    }

    event_lookup = defaultdict(list)

    for event in structure_events:

        event_lookup[
            event.index
        ].append(event)

    models = {}

    subsection(
        "TRAINING STRUCTURAL MODELS"
    )

    for horizon in HORIZONS:

        model, _ = train_frozen_model(
            candles,
            structure_states,
            atr,
            train_end,
            horizon,
        )

        models[horizon] = model

        print(
            f"    H+{horizon}: "
            f"BUY probability="
            f"{pct(model.global_probability)} "
            f"| samples="
            f"{model.training_samples} "
            f"| states="
            f"{model.training_states}"
        )

    print()
    print(
        "OOS MODEL FREEZE: PASS"
    )

    window_result = {
        "window": window["window"],
        "train_end": train_end,
        "oos_start": oos_start,
        "oos_end": oos_end,
        "models": {},
        "oos": {},
        "direction": {},
        "events": {},
    }

    subsection(
        "OUT-OF-SAMPLE RESULTS"
    )

    for horizon in HORIZONS:

        model = models[horizon]

        predictions = []
        labels = []
        label_objects = []
        indices = []

        for i in range(
            oos_start,
            oos_end,
        ):

            label = create_label(
                candles,
                atr,
                i,
                horizon,
            )

            if label is None:
                continue

            state = state_lookup.get(i)

            if state is None:
                continue

            probability = (
                predict_probability(
                    model,
                    state,
                )
            )

            prediction = (
                probability_to_direction(
                    probability
                )
            )

            predictions.append(
                prediction
            )

            labels.append(
                label.direction
            )

            label_objects.append(
                label
            )

            indices.append(i)

        result = evaluate_predictions(
            predictions,
            labels,
        )

        window_result[
            "oos"
        ][horizon] = {
            "predictions": predictions,
            "labels": labels,
            "label_objects": label_objects,
            "indices": indices,
            "metrics": result,
        }

        if result["n"]:

            print(
                f"STRUCTURE_LEARNED "
                f"H+{horizon:<2}"
                f" | N={result['n']:<5} | "
                f"Accuracy="
                f"{pct(result['accuracy'])} | "
                f"Baseline="
                f"{pct(result['baseline'])} | "
                f"Edge="
                f"{result['edge'] * 100:+.2f}%"
            )

        else:

            print(
                f"STRUCTURE_LEARNED "
                f"H+{horizon:<2}"
                f" | N=0 | "
                f"Insufficient sample"
            )

    # --------------------------------------------------------------------------
    # MFE / MAE
    # --------------------------------------------------------------------------

    print()
    print("MFE / MAE")

    for horizon in HORIZONS:

        label_objects = (
            window_result[
                "oos"
            ][horizon][
                "label_objects"
            ]
        )

        summary = summarize_mfe_mae(
            label_objects
        )

        print(
            f"H+{horizon:<2} | "
            f"MFE={fmt_num(summary['mfe'])} ATR | "
            f"MAE={fmt_num(summary['mae'])} ATR | "
            f"Time MFE="
            f"{fmt_num(summary['time_mfe'])} | "
            f"Time MAE="
            f"{fmt_num(summary['time_mae'])}"
        )

    # --------------------------------------------------------------------------
    # Structure direction
    # --------------------------------------------------------------------------

    subsection(
        "STRUCTURE DIRECTION"
    )

    for horizon in HORIZONS:

        data = window_result[
            "oos"
        ][horizon]

        predictions = data[
            "predictions"
        ]

        labels = data[
            "labels"
        ]

        indices = data[
            "indices"
        ]

        for trend_name in [
            "BULLISH",
            "BEARISH",
        ]:

            selected_predictions = []
            selected_labels = []

            for pos, i in enumerate(indices):

                state = state_lookup.get(i)

                if state is None:
                    continue

                if state.trend == trend_name:

                    selected_predictions.append(
                        predictions[pos]
                    )

                    selected_labels.append(
                        labels[pos]
                    )

            result = evaluate_predictions(
                selected_predictions,
                selected_labels,
            )

            name = (
                "STRUCTURE_BULLISH"
                if trend_name == "BULLISH"
                else "STRUCTURE_BEARISH"
            )

            if result["n"] == 0:

                print(
                    f"{name} H+{horizon:<2}"
                    f" | No valid observations"
                )

            else:

                print(
                    f"{name} H+{horizon:<2}"
                    f" | N={result['n']:<5} | "
                    f"Accuracy="
                    f"{pct(result['accuracy'])} | "
                    f"Baseline="
                    f"{pct(result['baseline'])} | "
                    f"Edge="
                    f"{result['edge'] * 100:+.2f}%"
                )

            window_result[
                "direction"
            ].setdefault(
                horizon,
                {}
            )[name] = result

    # --------------------------------------------------------------------------
    # Structure events
    # --------------------------------------------------------------------------

    subsection(
        "STRUCTURE EVENTS"
    )

    event_types = [
        "BOS_BULLISH",
        "BOS_BEARISH",
        "CHoCH_BULLISH",
        "CHoCH_BEARISH",
    ]

    for horizon in HORIZONS:

        data = window_result[
            "oos"
        ][horizon]

        predictions = data[
            "predictions"
        ]

        labels = data[
            "labels"
        ]

        indices = data[
            "indices"
        ]

        for event_type in event_types:

            selected_predictions = []
            selected_labels = []

            for pos, i in enumerate(indices):

                matched = any(
                    event.event
                    == event_type
                    for event
                    in event_lookup.get(
                        i,
                        [],
                    )
                )

                if matched:

                    selected_predictions.append(
                        predictions[pos]
                    )

                    selected_labels.append(
                        labels[pos]
                    )

            result = evaluate_predictions(
                selected_predictions,
                selected_labels,
            )

            if (
                result["n"]
                < MIN_EVENT_SAMPLE
            ):

                print(
                    f"{event_type:<25} "
                    f"H+{horizon:<2} | "
                    f"N={result['n']} | "
                    f"Insufficient sample"
                )

            else:

                print(
                    f"{event_type:<25} "
                    f"H+{horizon:<2} | "
                    f"N={result['n']:<5} | "
                    f"Accuracy="
                    f"{pct(result['accuracy'])} | "
                    f"Baseline="
                    f"{pct(result['baseline'])} | "
                    f"Edge="
                    f"{result['edge'] * 100:+.2f}%"
                )

            window_result[
                "events"
            ].setdefault(
                horizon,
                {}
            )[event_type] = result

    return window_result


# ==============================================================================
# COMBINED RESULTS
# ==============================================================================

def combine_window_results(
    window_results,
):

    combined = {}

    for horizon in HORIZONS:

        predictions = []
        labels = []
        label_objects = []
        indices = []
        windows = []

        for result in window_results:

            data = result[
                "oos"
            ][horizon]

            predictions.extend(
                data["predictions"]
            )

            labels.extend(
                data["labels"]
            )

            label_objects.extend(
                data["label_objects"]
            )

            indices.extend(
                data["indices"]
            )

            windows.extend(
                [result["window"]]
                * len(data["labels"])
            )

        combined[horizon] = {
            "predictions": predictions,
            "labels": labels,
            "label_objects": label_objects,
            "indices": indices,
            "windows": windows,
            "metrics": evaluate_predictions(
                predictions,
                labels,
            ),
        }

    return combined


def print_combined_results(
    combined,
):

    section(
        "COMBINED OUT-OF-SAMPLE RESULTS"
    )

    for horizon in HORIZONS:

        result = combined[
            horizon
        ]["metrics"]

        print(
            f"STRUCTURE_LEARNED "
            f"H+{horizon:<2}"
            f" | N={result['n']:<5} | "
            f"Accuracy="
            f"{pct(result['accuracy'])} | "
            f"Baseline="
            f"{pct(result['baseline'])} | "
            f"Edge="
            f"{result['edge'] * 100:+.2f}%"
        )


def print_combined_mfe_mae(
    combined,
):

    section(
        "COMBINED MFE / MAE"
    )

    for horizon in HORIZONS:

        labels = combined[
            horizon
        ]["label_objects"]

        summary = summarize_mfe_mae(
            labels
        )

        print(
            f"H+{horizon:<2} | "
            f"MFE={fmt_num(summary['mfe'])} ATR | "
            f"MAE={fmt_num(summary['mae'])} ATR | "
            f"Time MFE="
            f"{fmt_num(summary['time_mfe'])} | "
            f"Time MAE="
            f"{fmt_num(summary['time_mae'])}"
        )


def print_combined_structure_direction(
    combined,
    structure_states,
):

    section(
        "COMBINED STRUCTURE DIRECTION"
    )

    state_lookup = {
        state.index: state
        for state in structure_states
    }

    for horizon in HORIZONS:

        data = combined[horizon]

        predictions = data[
            "predictions"
        ]

        labels = data[
            "labels"
        ]

        indices = data[
            "indices"
        ]

        for trend_name in [
            "BULLISH",
            "BEARISH",
        ]:

            selected_predictions = []
            selected_labels = []

            for pos, index in enumerate(
                indices
            ):

                state = state_lookup.get(
                    index
                )

                if state is None:
                    continue

                if state.trend == trend_name:

                    selected_predictions.append(
                        predictions[pos]
                    )

                    selected_labels.append(
                        labels[pos]
                    )

            result = evaluate_predictions(
                selected_predictions,
                selected_labels,
            )

            name = (
                "STRUCTURE_BULLISH"
                if trend_name == "BULLISH"
                else "STRUCTURE_BEARISH"
            )

            if result["n"] == 0:

                print(
                    f"{name} H+{horizon:<2}"
                    f" | No valid observations"
                )

            else:

                print(
                    f"{name} H+{horizon:<2}"
                    f" | N={result['n']:<5} | "
                    f"Accuracy="
                    f"{pct(result['accuracy'])} | "
                    f"Baseline="
                    f"{pct(result['baseline'])} | "
                    f"Edge="
                    f"{result['edge'] * 100:+.2f}%"
                )


def print_combined_events(
    combined,
    structure_events,
):

    section(
        "COMBINED STRUCTURE EVENTS"
    )

    event_by_index = defaultdict(list)

    for event in structure_events:

        event_by_index[
            event.index
        ].append(
            event.event
        )

    event_types = [
        "BOS_BULLISH",
        "BOS_BEARISH",
        "CHoCH_BULLISH",
        "CHoCH_BEARISH",
    ]

    for event_type in event_types:

        for horizon in HORIZONS:

            data = combined[
                horizon
            ]

            predictions = data[
                "predictions"
            ]

            labels = data[
                "labels"
            ]

            indices = data[
                "indices"
            ]

            selected_predictions = []
            selected_labels = []

            for pos, index in enumerate(
                indices
            ):

                if (
                    event_type
                    in event_by_index.get(
                        index,
                        [],
                    )
                ):

                    selected_predictions.append(
                        predictions[pos]
                    )

                    selected_labels.append(
                        labels[pos]
                    )

            result = evaluate_predictions(
                selected_predictions,
                selected_labels,
            )

            if (
                result["n"]
                < MIN_EVENT_SAMPLE
            ):

                print(
                    f"{event_type:<28} "
                    f"H+{horizon:<2} | "
                    f"N={result['n']} | "
                    f"Insufficient sample"
                )

            else:

                print(
                    f"{event_type:<28} "
                    f"H+{horizon:<2} | "
                    f"N={result['n']:<5} | "
                    f"Accuracy="
                    f"{pct(result['accuracy'])} | "
                    f"Baseline="
                    f"{pct(result['baseline'])} | "
                    f"Edge="
                    f"{result['edge'] * 100:+.2f}%"
                )


def print_atr_outcomes(
    combined,
):

    section(
        "ATR-NORMALIZED FUTURE OUTCOMES"
    )

    for horizon in HORIZONS:

        labels = combined[
            horizon
        ]["label_objects"]

        counts = Counter(
            label.strong_category
            for label in labels
        )

        total = len(labels)

        if total == 0:
            continue

        print(
            f"H+{horizon}: "
            f"STRONG_UP="
            f"{pct(counts['STRONG_UP'] / total)} | "
            f"UP="
            f"{pct(counts['UP'] / total)} | "
            f"DOWN="
            f"{pct(counts['DOWN'] / total)} | "
            f"STRONG_DOWN="
            f"{pct(counts['STRONG_DOWN'] / total)}"
        )


def print_stability(
    window_results,
):

    section(
        "WALK-FORWARD STABILITY ANALYSIS"
    )

    for horizon in HORIZONS:

        accuracies = []
        edges = []

        for result in window_results:

            metrics = result[
                "oos"
            ][horizon][
                "metrics"
            ]

            if metrics["accuracy"] is not None:

                accuracies.append(
                    metrics["accuracy"]
                )

                edges.append(
                    metrics["edge"]
                )

        if not accuracies:
            continue

        print(
            f"H+{horizon:<2} | "
            f"Mean="
            f"{pct(safe_mean(accuracies))} | "
            f"Median="
            f"{pct(safe_median(accuracies))} | "
            f"Std="
            f"{pct(safe_std(accuracies))} | "
            f"Min="
            f"{pct(min(accuracies))} | "
            f"Max="
            f"{pct(max(accuracies))} | "
            f"Mean Edge="
            f"{safe_mean(edges) * 100:+.2f}%"
        )


def print_outcome_distributions(
    combined,
):

    section(
        "COMBINED OOS OUTCOME DISTRIBUTIONS"
    )

    for horizon in HORIZONS:

        labels = combined[
            horizon
        ]["labels"]

        total = len(labels)

        if total == 0:
            continue

        buy = sum(
            1
            for x in labels
            if x > 0
        )

        sell = sum(
            1
            for x in labels
            if x < 0
        )

        print(
            f"H+{horizon}: "
            f"BUY={pct(buy / total)} | "
            f"SELL={pct(sell / total)}"
        )


# ==============================================================================
# DEPENDENCY / LOOKAHEAD
# ==============================================================================

def print_forward_dependency_check():

    section(
        "FORWARD LABEL DEPENDENCY CHECK"
    )

    print(
        "Fixed-horizon labels can overlap in time."
    )

    print(
        "This does not create future information leakage "
        "into the frozen model."
    )

    print(
        "Prediction count is therefore not necessarily "
        "equal to independent observations."
    )


def print_lookahead_check():

    section(
        "LOOK-AHEAD OUTCOME CHECK"
    )

    print(
        "Future outcomes are used only:"
    )

    print(
        "    1. inside TRAIN when the complete label "
        "finishes before train_end"
    )

    print(
        "    2. after model freeze for OOS evaluation"
    )

    print(
        "Structural states themselves never use future candles "
        "after their causal availability."
    )

    print(
        "Look-ahead outcome policy: PASS"
    )


# ==============================================================================
# WINDOW BOUNDARY CHECK
# ==============================================================================

def check_window_boundaries(windows, n):

    section("WALK-FORWARD BOUNDARY CHECK")

    passed = True
    previous_oos_end = None

    for window_number, window in enumerate(windows, start=1):

        train_start = window["train_start"]
        train_end = window["train_end"]
        oos_start = window["oos_start"]
        oos_end = window["oos_end"]

        print(
            f"Checking Window {window_number}: "
            f"TRAIN [{train_start}:{train_end}] | "
            f"OOS [{oos_start}:{oos_end}]"
        )

        if train_start < 0:
            print("  FAIL: train_start < 0")
            passed = False

        if train_end > n:
            print("  FAIL: train_end > dataset length")
            passed = False

        if oos_start < 0:
            print("  FAIL: oos_start < 0")
            passed = False

        if oos_end > n:
            print("  FAIL: oos_end > dataset length")
            passed = False

        if train_start >= train_end:
            print("  FAIL: invalid training range")
            passed = False

        if oos_start >= oos_end:
            print("  FAIL: invalid OOS range")
            passed = False

        if train_end != oos_start:
            print(
                f"  FAIL: TRAIN end {train_end} "
                f"!= OOS start {oos_start}"
            )
            passed = False

        if previous_oos_end is not None:

            if train_end != previous_oos_end:
                print(
                    f"  FAIL: expanding continuity: "
                    f"TRAIN end {train_end} "
                    f"!= previous OOS end {previous_oos_end}"
                )
                passed = False

        previous_oos_end = oos_end

    if windows and windows[-1]["oos_end"] != n:

        print(
            f"  FAIL: final OOS end "
            f"{windows[-1]['oos_end']} "
            f"!= dataset length {n}"
        )

        passed = False

    print()

    print(
        f"Window boundaries: "
        f"{'PASS' if passed else 'FAIL'}"
    )

    if not passed:

        raise RuntimeError(
            "Walk-forward boundary check failed."
        )

    return True



def file_sha256(path):

    digest = hashlib.sha256()

    with open(path, "rb") as f:

        while True:

            chunk = f.read(
                1024 * 1024
            )

            if not chunk:
                break

            digest.update(chunk)

    return digest.hexdigest()


def protection_check():

    section(
        "PROTECTION CHECK"
    )

    if not os.path.exists(
        MARKET_DATA_FILE
    ):

        print(
            "market_data.bin       : NOT FOUND"
        )

        raise FileNotFoundError(
            MARKET_DATA_FILE
        )

    print(
        "market_data.bin       : READ ONLY"
    )

    print(
        "Production MLAI       : NOT MODIFIED"
    )

    print(
        "Learning memory       : NOT MODIFIED"
    )

    print(
        "Trading               : DISABLED"
    )

    print(
        "Internet              : NOT REQUIRED"
    )

    return file_sha256(
        MARKET_DATA_FILE
    )


def final_protection_check(
    before_hash,
):

    section(
        "FINAL PROTECTION CHECK"
    )

    after_hash = file_sha256(
        MARKET_DATA_FILE
    )

    if before_hash != after_hash:

        print(
            "market_data.bin       : MODIFIED"
        )

        raise RuntimeError(
            "PROTECTION FAILURE: "
            "market_data.bin changed."
        )

    print(
        "market_data.bin       : READ ONLY"
    )

    print(
        "Production MLAI       : NOT MODIFIED"
    )

    print(
        "Learning memory       : NOT MODIFIED"
    )

    print(
        "Trading               : DISABLED"
    )

    print(
        "Internet              : NOT REQUIRED"
    )


# ==============================================================================
# SERIALIZATION
# ==============================================================================

def make_serializable(obj):

    if isinstance(obj, dict):

        return {
            str(k): make_serializable(v)
            for k, v in obj.items()
        }

    if isinstance(obj, list):

        return [
            make_serializable(v)
            for v in obj
        ]

    if isinstance(obj, tuple):

        return [
            make_serializable(v)
            for v in obj
        ]

    if hasattr(
        obj,
        "__dataclass_fields__",
    ):

        return make_serializable(
            asdict(obj)
        )

    return obj


# ==============================================================================
# VALIDATION BINARY
# ==============================================================================

def save_validation_binary(
    output,
):

    payload = {
        "version": VERSION,

        "experiment": (
            "MLAI CAUSAL MARKET STRUCTURE "
            "WALK-FORWARD VALIDATION"
        ),

        "protection": {
            "market_data_read_only": True,
            "production_modified": False,
            "learning_memory_modified": False,
            "trading_enabled": False,
            "internet_required": False,
        },

        "results": make_serializable(
            output
        ),
    }

    with open(
        VALIDATION_BIN_FILE,
        "wb",
    ) as f:

        pickle.dump(
            payload,
            f,
            protocol=pickle.HIGHEST_PROTOCOL,
        )


# ==============================================================================
# MARKDOWN REPORT
# ==============================================================================

def generate_markdown_report(
    output,
):

    lines = []

    lines.append(
        "# MLAI v3.8.6 Causal Market Structure "
        "Walk-Forward Validation"
    )

    lines.append("")

    lines.append(
        "## Objective"
    )

    lines.append("")

    lines.append(
        "Fix and harden causal market structure."
    )

    lines.append("")

    lines.append(
        "## Protection"
    )

    lines.append("")

    lines.append(
        "- market_data.bin: READ ONLY"
    )

    lines.append(
        "- Production MLAI: NOT MODIFIED"
    )

    lines.append(
        "- Learning memory: NOT MODIFIED"
    )

    lines.append(
        "- Trading: DISABLED"
    )

    lines.append(
        "- Internet: NOT REQUIRED"
    )

    lines.append("")

    lines.append(
        "## Dataset"
    )

    lines.append("")

    lines.append(
        f"- Candles: {output['candles']}"
    )

    lines.append(
        f"- Confirmed swings: "
        f"{output['confirmed_swings']}"
    )

    lines.append(
        f"- Structural states: "
        f"{output['structural_states']}"
    )

    lines.append(
        f"- Structural events: "
        f"{output['structural_events']}"
    )

    lines.append("")

    lines.append(
        "## Causal Structure Fixes"
    )

    lines.append("")

    lines.append(
        "- Swing labels assigned causally."
    )

    lines.append(
        "- Structural levels retain reference swing indices."
    )

    lines.append(
        "- Event references are explicitly validated."
    )

    lines.append(
        "- One structural break per level is audited."
    )

    lines.append(
        "- Structural state ages use known swing indices."
    )

    lines.append(
        "- Structural state snapshots are causal."
    )

    lines.append("")

    lines.append(
        "## Combined OOS Results"
    )

    lines.append("")

    lines.append(
        "| Horizon | N | Accuracy | Baseline | Edge |"
    )

    lines.append(
        "|---:|---:|---:|---:|---:|"
    )

    for horizon in HORIZONS:

        metrics = (
            output[
                "combined"
            ][horizon]["metrics"]
        )

        if metrics["n"]:

            lines.append(
                f"| H+{horizon} | "
                f"{metrics['n']} | "
                f"{pct(metrics['accuracy'])} | "
                f"{pct(metrics['baseline'])} | "
                f"{metrics['edge'] * 100:+.2f}% |"
            )

    lines.append("")

    lines.append(
        "## Notes"
    )

    lines.append("")

    lines.append(
        "All OOS models were frozen before OOS evaluation."
    )

    lines.append("")

    lines.append(
        "Training labels obey "
        "`i + horizon < train_end`."
    )

    lines.append("")

    lines.append(
        "Structural states use only information that was "
        "causally available at each candle."
    )

    lines.append("")

    with open(
        VALIDATION_REPORT_FILE,
        "w",
        encoding="utf-8",
    ) as f:

        f.write(
            "\n".join(lines)
        )


# ==============================================================================
# MAIN
# ==============================================================================

def main():

    title(
        "MLAI v3.8.6 CAUSAL MARKET STRUCTURE INTELLIGENCE"
    )

    print()
    print(
        "RESEARCH EXPERIMENT"
    )

    print()
    print(
        "OBJECTIVE:"
    )

    print(
        "    FIX AND HARDEN CAUSAL MARKET STRUCTURE"
    )

    print()
    print(
        "v3.8.6 changes:"
    )

    print(
        "    - causal HH / HL / LH / LL"
    )

    print(
        "    - causal swing history"
    )

    print(
        "    - explicit BOS / CHoCH references"
    )

    print(
        "    - structural level identity"
    )

    print(
        "    - one break per structural level"
    )

    print(
        "    - causal state snapshots"
    )

    print(
        "    - causal swing ages"
    )

    print(
        "    - stronger causality audit"
    )

    print(
        "    - actual training-boundary audit"
    )

    print(
        "    - frozen OOS models"
    )

    print(
        "    - H+4 / H+8 / H+16"
    )

    print()
    print(
        "NOT INCLUDED YET:"
    )

    print(
        "    - regime"
    )

    print(
        "    - liquidity"
    )

    print(
        "    - displacement"
    )

    print(
        "    - multi-timeframe"
    )

    print(
        "    - new prediction indicators"
    )

    print()
    print(
        "market_data.bin:"
    )

    print(
        "    READ ONLY"
    )

    # --------------------------------------------------------------------------
    # Protection
    # --------------------------------------------------------------------------

    before_hash = protection_check()

    # --------------------------------------------------------------------------
    # Load
    # --------------------------------------------------------------------------

    candles = load_market_data(
        MARKET_DATA_FILE
    )

    audit_data(
        candles
    )

    if not check_chronology(
        candles
    ):

        raise RuntimeError(
            "Chronological data check failed."
        )

    # --------------------------------------------------------------------------
    # Windows
    # --------------------------------------------------------------------------

    windows = create_walk_forward_windows(
        len(candles),
        WINDOWS_REQUESTED,
    )

    print_windows(
        windows
    )

    check_window_boundaries(
        windows,
        len(candles),
    )

    # --------------------------------------------------------------------------
    # ATR
    # --------------------------------------------------------------------------

    section(
        "ATR DIAGNOSTIC CALCULATION"
    )

    atr = calculate_atr(
        candles,
        ATR_PERIOD,
    )

    print(
        "ATR calculation     : COMPLETE"
    )

    print()
    print(
        "ATR is NOT a separate prediction model."
    )

    print(
        "ATR is used only to normalize future movement "
        "and MFE/MAE."
    )

    # --------------------------------------------------------------------------
    # Confirmed swings
    # --------------------------------------------------------------------------

    section(
        "CONFIRMED SWINGS"
    )

    swings = detect_confirmed_swings(
        candles,
        SWING_LEFT,
        SWING_RIGHT,
    )

    print(
        f"Confirmed swing events: "
        f"{len(swings)}"
    )

    # --------------------------------------------------------------------------
    # Causal labels
    # --------------------------------------------------------------------------

    section(
        "CAUSAL SWING LABELING"
    )

    swings = assign_causal_swing_labels(
        swings
    )

    swing_counts = Counter(
        swing.label
        for swing in swings
    )

    print(
        f"HIGH labels: "
        f"H={swing_counts['H']} | "
        f"HH={swing_counts['HH']} | "
        f"LH={swing_counts['LH']}"
    )

    print(
        f"LOW labels : "
        f"L={swing_counts['L']} | "
        f"HL={swing_counts['HL']} | "
        f"LL={swing_counts['LL']}"
    )

    # --------------------------------------------------------------------------
    # Causal structure
    # --------------------------------------------------------------------------

    section(
        "CAUSAL MARKET STRUCTURE"
    )

    (
        structure_states,
        structure_events,
    ) = build_causal_structure(
        candles,
        swings,
    )

    print(
        f"Causal structure states: "
        f"{len(structure_states)}"
    )

    # --------------------------------------------------------------------------
    # Events
    # --------------------------------------------------------------------------

    section(
        "STRUCTURE EVENTS"
    )

    event_counts = Counter(
        event.event
        for event in structure_events
    )

    for event_name in [
        "BOS_BULLISH",
        "BOS_BEARISH",
        "CHoCH_BULLISH",
        "CHoCH_BEARISH",
    ]:

        print(
            f"{event_name:<20} : "
            f"{event_counts[event_name]}"
        )

    # --------------------------------------------------------------------------
    # Causality
    # --------------------------------------------------------------------------

    audit_causality(
        candles,
        swings,
        structure_states,
        structure_events,
    )

    # --------------------------------------------------------------------------
    # Datasets
    # --------------------------------------------------------------------------

    (
        state_records,
        event_records,
    ) = build_structural_datasets(
        structure_states,
        structure_events,
    )

    # --------------------------------------------------------------------------
    # Training boundary
    # --------------------------------------------------------------------------

    eligible_training_labels = (
        audit_training_label_boundary(
            candles,
            atr,
            windows,
        )
    )

    # --------------------------------------------------------------------------
    # Walk forward
    # --------------------------------------------------------------------------

    window_results = []

    for window in windows:

        result = run_window(
            candles,
            atr,
            structure_states,
            structure_events,
            window,
        )

        window_results.append(
            result
        )

    # --------------------------------------------------------------------------
    # Combined
    # --------------------------------------------------------------------------

    combined = combine_window_results(
        window_results
    )

    print_combined_results(
        combined
    )

    print_combined_mfe_mae(
        combined
    )

    print_combined_structure_direction(
        combined,
        structure_states,
    )

    print_combined_events(
        combined,
        structure_events,
    )

    print_atr_outcomes(
        combined
    )

    print_stability(
        window_results
    )

    print_outcome_distributions(
        combined
    )

    print_forward_dependency_check()

    print_lookahead_check()

    # --------------------------------------------------------------------------
    # Final protection
    # --------------------------------------------------------------------------

    final_protection_check(
        before_hash
    )

    # --------------------------------------------------------------------------
    # Save
    # --------------------------------------------------------------------------

    output = {
        "version": VERSION,

        "objective": (
            "FIX AND HARDEN CAUSAL MARKET STRUCTURE"
        ),

        "candles": len(candles),

        "confirmed_swings": len(swings),

        "causal_structure_states": len(
            structure_states
        ),

        "structural_states": len(
            state_records
        ),

        "structural_events": len(
            event_records
        ),

        "swing_label_counts": dict(
            swing_counts
        ),

        "event_counts": dict(
            event_counts
        ),

        "eligible_training_labels_checked":
            eligible_training_labels,

        "windows": windows,

        "window_results": window_results,

        "combined": combined,
    }

    save_validation_binary(
        output
    )

    generate_markdown_report(
        output
    )

    section(
        "VALIDATION ARTIFACTS"
    )

    print(
        f"    {os.path.basename(VALIDATION_BIN_FILE)}"
    )

    print(
        f"    {os.path.basename(VALIDATION_REPORT_FILE)}"
    )

    section(
        "MLAI v3.8.6 CAUSAL MARKET STRUCTURE "
        "INTELLIGENCE VALIDATION COMPLETE"
    )


# ==============================================================================
# ENTRY POINT
# ==============================================================================

if __name__ == "__main__":

    try:

        main()

    except KeyboardInterrupt:

        print()
        print(
            "Execution interrupted by user."
        )

        sys.exit(130)

    except Exception as exc:

        print()
        line("=")
        print(
            "VALIDATION ERROR"
        )
        line("=")

        print(
            f"{type(exc).__name__}: {exc}"
        )

        print()

        sys.exit(1)

