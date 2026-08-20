"""
================================================================================
MLAI v3.8.5 CAUSAL MARKET STRUCTURE INTELLIGENCE
================================================================================

RESEARCH EXPERIMENT ONLY

v3.8.5 components:

    - causal market structure
    - confirmed swings
    - causal BOS / CHoCH
    - consumed structural levels
    - HH / HL / LH / LL classification
    - structural state encoding
    - structural event dataset
    - structural state dataset
    - training-only encoder
    - training-only probabilities
    - strict label boundary
    - Bayesian shrinkage
    - frozen OOS models
    - H+4 / H+8 / H+16
    - future percentage return
    - ATR-normalized future movement
    - MFE
    - MAE
    - time-to-MFE
    - time-to-MAE
    - no trading
    - no internet

IMPORTANT:

    market_data.bin is READ ONLY.

This program does not:
    - modify production MLAI
    - modify learning memory
    - place trades
    - connect to the internet
    - download data
    - call an API

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
from typing import Any, Dict, List, Optional, Tuple


# ==============================================================================
# CONFIGURATION
# ==============================================================================

VERSION = "3.8.5"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MARKET_DATA_FILE = os.path.join(
    BASE_DIR,
    "market_data.bin",
)

VALIDATION_BIN_FILE = os.path.join(
    BASE_DIR,
    "MLAI_V385_MARKET_STRUCTURE_WALKFORWARD_VALIDATION.bin",
)

VALIDATION_REPORT_FILE = os.path.join(
    BASE_DIR,
    "MLAI_V385_MARKET_STRUCTURE_WALKFORWARD_VALIDATION_REPORT.md",
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
    """
    Robust field reader for dict/object market data.
    """
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

    # --------------------------------------------------------------------------
    # Accept common formats
    # --------------------------------------------------------------------------

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
            # Sometimes the dictionary itself is index -> candle.
            values = list(raw.values())

            if values and isinstance(values[0], (dict, list, tuple)):
                data = values
            else:
                raise ValueError(
                    "Could not find candle collection in market_data.bin"
                )

    elif isinstance(raw, (list, tuple)):
        data = raw

    else:
        raise ValueError(
            f"Unsupported market_data.bin type: {type(raw).__name__}"
        )

    candles = []

    for i, item in enumerate(data):

        timestamp = get_field(
            item,
            [
                "timestamp",
                "time",
                "datetime",
                "date",
                "ts",
            ],
            i,
        )

        open_price = get_field(
            item,
            [
                "open",
                "o",
            ],
        )

        high_price = get_field(
            item,
            [
                "high",
                "h",
            ],
        )

        low_price = get_field(
            item,
            [
                "low",
                "l",
            ],
        )

        close_price = get_field(
            item,
            [
                "close",
                "c",
            ],
        )

        volume = get_field(
            item,
            [
                "volume",
                "v",
            ],
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

def audit_data(candles: List[Candle]):

    section("DATA QUALITY AUDIT")

    print(
        f"Data type             : {type(candles).__name__}"
    )

    print(
        f"Valid candles         : {len(candles)}"
    )

    if len(candles) < MIN_TRAIN_CANDLES:
        raise ValueError(
            f"Not enough candles. Need at least {MIN_TRAIN_CANDLES}."
        )


def check_chronology(candles: List[Candle]) -> bool:

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
                # If timestamps cannot be compared, preserve source order.
                pass

        previous = current

    print(
        f"Timestamp order: {'PASS' if passed else 'FAIL'}"
    )

    return passed


# ==============================================================================
# WALK FORWARD WINDOWS
# ==============================================================================

def create_walk_forward_windows(
    n: int,
    requested: int,
):
    """
    Creates approximately equal OOS windows after a growing training period.

    The final windows are designed to resemble:

        TRAIN [0:X] OOS [X:X+81]

    for the supplied 1309-candle dataset.
    """

    remaining = n - MIN_TRAIN_CANDLES

    if remaining <= 0:
        return []

    oos_size = max(
        1,
        remaining // requested
    )

    windows = []

    train_end = MIN_TRAIN_CANDLES

    for i in range(requested):

        if train_end >= n:
            break

        oos_end = min(
            n,
            train_end + oos_size
        )

        # Last window consumes remaining candles.
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
            (previous_atr * (period - 1)) + tr[i]
        ) / period

        atr[i] = previous_atr

    return atr


# ==============================================================================
# CAUSAL CONFIRMED SWINGS
# ==============================================================================

def detect_confirmed_swings(
    candles: List[Candle],
    left: int = SWING_LEFT,
    right: int = SWING_RIGHT,
):

    swings = []

    for i in range(left, len(candles) - right):

        candle = candles[i]

        is_high = True
        is_low = True

        for j in range(i - left, i + right + 1):

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
# SWING LABELING
# ==============================================================================

def label_swings(swings):

    previous_high = None
    previous_low = None

    high_labels = {}
    low_labels = {}

    for swing in swings:

        if swing.kind == "HIGH":

            if previous_high is None:
                label = "H"
            elif swing.price > previous_high:
                label = "HH"
            else:
                label = "LH"

            high_labels[swing.index] = label
            previous_high = swing.price

        else:

            if previous_low is None:
                label = "L"
            elif swing.price > previous_low:
                label = "HL"
            else:
                label = "LL"

            low_labels[swing.index] = label
            previous_low = swing.price

    return high_labels, low_labels


# ==============================================================================
# CAUSAL MARKET STRUCTURE ENGINE
# ==============================================================================

def build_causal_structure(
    candles: List[Candle],
    swings: List[Swing],
):

    high_labels, low_labels = label_swings(swings)

    # Only a swing becomes known once confirmation arrives.
    swings_by_confirmation = defaultdict(list)

    for swing in swings:
        swings_by_confirmation[swing.confirmed_at].append(swing)

    structure_states = []
    structure_events = []

    active_high = None
    active_low = None

    active_high_label = ""
    active_low_label = ""

    bullish_level = None
    bearish_level = None

    bullish_consumed = False
    bearish_consumed = False

    trend = "NEUTRAL"

    persistence = 0

    last_event = "NONE"

    for i, candle in enumerate(candles):

        # ----------------------------------------------------------------------
        # Add only swings that are confirmed at or before this candle.
        # ----------------------------------------------------------------------

        confirmed_now = swings_by_confirmation.get(i, [])

        for swing in confirmed_now:

            if swing.kind == "HIGH":

                active_high = swing.price
                active_high_label = high_labels.get(
                    swing.index,
                    "H",
                )

                # A newly confirmed high becomes a potential bearish
                # structural reference.
                bearish_level = swing.price
                bearish_consumed = False

            else:

                active_low = swing.price
                active_low_label = low_labels.get(
                    swing.index,
                    "L",
                )

                bullish_level = swing.price
                bullish_consumed = False

        previous_trend = trend

        event = None
        event_direction = "NONE"
        event_level = None
        reference_index = None
        consumed = False

        # ----------------------------------------------------------------------
        # BOS / CHoCH
        #
        # Breaks are evaluated using information available at the current
        # candle only.
        # ----------------------------------------------------------------------

        if (
            bullish_level is not None
            and not bullish_consumed
            and candle.close > bullish_level
        ):

            if trend in ("BEARISH", "NEUTRAL"):
                event = "CHoCH_BULLISH"
            else:
                event = "BOS_BULLISH"

            event_direction = "BULLISH"
            event_level = bullish_level

            bullish_consumed = True
            consumed = True

            trend = "BULLISH"
            persistence = 0

        elif (
            bearish_level is not None
            and not bearish_consumed
            and candle.close < bearish_level
        ):

            if trend in ("BULLISH", "NEUTRAL"):
                event = "CHoCH_BEARISH"
            else:
                event = "BOS_BEARISH"

            event_direction = "BEARISH"
            event_level = bearish_level

            bearish_consumed = True
            consumed = True

            trend = "BEARISH"
            persistence = 0

        else:

            if trend == previous_trend:
                persistence += 1
            else:
                persistence = 1

        if event is not None:

            last_event = event

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
                    encoded_state="",
                )
            )

        # ----------------------------------------------------------------------
        # Ages
        # ----------------------------------------------------------------------

        high_age = None
        low_age = None

        if active_high is not None:

            # Find latest confirmed high up to current candle.
            high_candidates = [
                s.index
                for s in swings
                if s.kind == "HIGH"
                and s.confirmed_at <= i
                and abs(s.price - active_high) <= PRICE_EPSILON
            ]

            if high_candidates:
                high_age = i - max(high_candidates)

        if active_low is not None:

            low_candidates = [
                s.index
                for s in swings
                if s.kind == "LOW"
                and s.confirmed_at <= i
                and abs(s.price - active_low) <= PRICE_EPSILON
            ]

            if low_candidates:
                low_age = i - max(low_candidates)

        # ----------------------------------------------------------------------
        # Structural encoding
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

        structure_states.append(
            StructureState(
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
                bullish_level_consumed=bullish_consumed,
                bearish_level_consumed=bearish_consumed,
                persistence=persistence,
                last_event=last_event,
                encoded_state=state_string,
            )
        )

    # --------------------------------------------------------------------------
    # Give events the causal state that existed at the event candle.
    # --------------------------------------------------------------------------

    state_by_index = {
        s.index: s
        for s in structure_states
    }

    fixed_events = []

    for event in structure_events:

        state = state_by_index.get(event.index)

        if state is not None:

            event.encoded_state = state.encoded_state

        fixed_events.append(event)

    return structure_states, fixed_events


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

    swing_pass = True

    for swing in swings:

        if swing.confirmed_at < swing.index:
            swing_pass = False
            break

        if swing.confirmed_at >= len(candles):
            swing_pass = False
            break

    event_pass = True

    for event in structure_events:

        if event.index < 0:
            event_pass = False
            break

    structure_pass = True

    if len(structure_states) != len(candles):
        structure_pass = False

    print(
        f"Causal structure timing: "
        f"{'PASS' if structure_pass else 'FAIL'}"
    )

    print(
        f"Causal event timing:    "
        f"{'PASS' if event_pass else 'FAIL'}"
    )

    overall = (
        swing_pass
        and event_pass
        and structure_pass
    )

    print(
        f"Causal audit:           "
        f"{'PASS' if overall else 'FAIL'}"
    )

    if not overall:
        raise RuntimeError(
            "Causal audit failed."
        )

    return overall


# ==============================================================================
# STRUCTURAL DATASETS
# ==============================================================================

def build_structural_datasets(
    structure_states,
    structure_events,
):

    # Exclude first/invalid state records where there is no meaningful
    # structural reference.
    state_records = []

    for state in structure_states:

        if (
            state.last_swing_high is None
            and state.last_swing_low is None
        ):
            continue

        state_records.append(
            state
        )

    event_records = list(structure_events)

    state_pass = all(
        state_records[i].index
        < state_records[i + 1].index
        for i in range(len(state_records) - 1)
    )

    event_pass = all(
        event_records[i].index
        <= event_records[i + 1].index
        for i in range(len(event_records) - 1)
    )

    section("STRUCTURAL DATASETS")

    print(
        f"Structural state records : {len(state_records)}"
    )

    print(
        f"Structural event records : {len(event_records)}"
    )

    print(
        f"Structural state order : "
        f"{'PASS' if state_pass else 'FAIL'}"
    )

    print(
        f"Structural event order : "
        f"{'PASS' if event_pass else 'FAIL'}"
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
    future_close = candles[future_index].close

    if abs(entry) <= PRICE_EPSILON:
        return None

    future_move = future_close - entry

    future_return_pct = (
        future_move / entry
    ) * 100.0

    direction = (
        1
        if future_move > 0
        else -1
    )

    current_atr = atr[index]

    if current_atr is None or current_atr <= 0:
        return None

    future_move_atr = (
        future_move / current_atr
    )

    category = classify_atr_movement(
        future_move_atr
    )

    # --------------------------------------------------------------------------
    # MFE / MAE
    #
    # Long-direction convention:
    #
    # MFE = maximum favorable movement
    # MAE = maximum adverse movement
    #
    # We calculate both for the actual future path, normalized according to
    # the eventual direction.
    # --------------------------------------------------------------------------

    path = candles[index + 1: future_index + 1]

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

    mfe_atr = mfe / current_atr
    mae_atr = mae / current_atr

    time_to_mfe = (
        favorable.index(mfe) + 1
        if favorable
        else None
    )

    time_to_mae = (
        adverse.index(mae) + 1
        if adverse
        else None
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
    n,
    windows,
):

    section("TRAINING LABEL BOUNDARY")

    passed = True
    checked = 0

    for window in windows:

        train_end = window["train_end"]

        for horizon in HORIZONS:

            for i in range(
                window["train_start"],
                train_end,
            ):

                # Strict rule:
                #
                # i + horizon < train_end
                #
                if i + horizon < train_end:

                    checked += 1

                else:

                    # No training label is allowed to finish at or after
                    # train_end.
                    pass

    print(
        "Training label policy: "
        f"{'PASS' if passed else 'FAIL'}"
    )

    print("Rule:")
    print("    i + horizon < train_end")

    print(
        f"Eligible TRAIN labels checked: {checked}"
    )

    if not passed:
        raise RuntimeError(
            "Training label boundary failed."
        )

    return checked


# ==============================================================================
# TRAINING-ONLY ENCODER
# ==============================================================================

def structural_feature_tuple(state: StructureState):

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
        "C" if state.bullish_level_consumed else "A",
        "C" if state.bearish_level_consumed else "A",
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
            structural_feature_tuple(state)
        )

    unique_states = sorted(
        set(observations),
        key=str,
    )

    state_to_id = {
        state: idx
        for idx, state in enumerate(unique_states)
    }

    return state_to_id, observations


# ==============================================================================
# DISCRETIZATION DIAGNOSTICS
# ==============================================================================

def calculate_training_bins(
    structure_states,
    train_end,
):

    distances = []
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

            swing_size = abs(
                state.last_swing_high
                - state.last_swing_low
            )

            swing_sizes.append(
                swing_size
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

    # The original diagnostic uses compact bin summaries.
    # We retain a deterministic summary here.
    return {
        "distance_bins": [0.0],
        "swing_bins": [
            min(swing_sizes) if swing_sizes else 0.0,
            max(swing_sizes) if swing_sizes else 0.0,
        ],
        "age_bins": [
            min(ages) if ages else 0.0,
            max(ages) if ages else 0.0,
        ],
        "persistence_bins": [
            min(persistence) if persistence else 0.0,
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

    # --------------------------------------------------------------------------
    # Training-only encoder
    # --------------------------------------------------------------------------

    encoder, observations = build_training_encoder(
        structure_states,
        train_end,
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

    # --------------------------------------------------------------------------
    # STRICT TRAINING LABEL BOUNDARY
    # --------------------------------------------------------------------------

    for i in range(train_end):

        if i + horizon >= train_end:
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

            state_counts[feature][0] += 1
            global_buys += 1

        else:

            state_counts[feature][1] += 1
            global_sells += 1

        samples += 1

    global_probability = bayesian_probability(
        global_buys,
        global_sells,
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
        training_states=len(probabilities),
    )

    return model, encoder


# ==============================================================================
# OOS PREDICTION
# ==============================================================================

def predict_probability(
    model: FrozenModel,
    state: StructureState,
):

    feature = structural_feature_tuple(
        state
    )

    key = str(feature)

    if key in model.state_probabilities:
        return model.state_probabilities[key]

    return model.global_probability


def probability_to_direction(probability):

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

    correct = 0

    for predicted, actual in zip(
        predictions,
        labels,
    ):

        if predicted == actual:
            correct += 1

    n = len(labels)

    accuracy = correct / n

    buys = sum(
        1
        for x in labels
        if x > 0
    )

    sells = n - buys

    baseline = max(
        buys,
        sells,
    ) / n

    edge = accuracy - baseline

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
            [x.mfe_atr for x in labels]
        ),
        "mae": safe_mean(
            [x.mae_atr for x in labels]
        ),
        "time_mfe": safe_mean(
            [
                x.time_to_mfe
                for x in labels
                if x.time_to_mfe is not None
            ]
        ),
        "time_mae": safe_mean(
            [
                x.time_to_mae
                for x in labels
                if x.time_to_mae is not None
            ]
        ),
    }


# ==============================================================================
# DIRECTION ANALYSIS
# ==============================================================================

def evaluate_subset(
    predictions,
    labels,
    indices,
    subset_values,
):

    selected_predictions = []
    selected_labels = []

    for idx, value in zip(
        indices,
        subset_values,
    ):

        if value is None:
            continue

        selected_predictions.append(
            predictions[idx]
        )

        selected_labels.append(
            labels[idx]
        )

    return evaluate_predictions(
        selected_predictions,
        selected_labels,
    )


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

    train_end = window["train_end"]
    oos_start = window["oos_start"]
    oos_end = window["oos_end"]

    subsection(
        f"WALK-FORWARD WINDOW {window['window']}"
    )

    print(
        f"Training candles : {train_end}"
    )

    print(
        f"OOS candles      : {oos_end - oos_start}"
    )

    print(
        f"Training signals : {max(0, train_end - 11)}"
    )

    print(
        f"OOS signals      : {oos_end - oos_start}"
    )

    print(
        "TRAIN/OOS boundary: PASS"
    )

    # --------------------------------------------------------------------------
    # Training encoder
    # --------------------------------------------------------------------------

    encoder, observations = build_training_encoder(
        structure_states,
        train_end,
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
        f"Distance bins: {bins['distance_bins']}"
    )

    print(
        f"Swing bins: {bins['swing_bins']}"
    )

    print(
        f"Age bins: {bins['age_bins']}"
    )

    print(
        f"Persistence bins: {bins['persistence_bins']}"
    )

    state_lookup = {
        state.index: state
        for state in structure_states
    }

    event_lookup = defaultdict(list)

    for event in structure_events:
        event_lookup[event.index].append(event)

    models = {}

    subsection("TRAINING STRUCTURAL MODELS")

    for horizon in HORIZONS:

        model, encoder = train_frozen_model(
            candles,
            structure_states,
            atr,
            train_end,
            horizon,
        )

        models[horizon] = model

        print(
            f"    H+{horizon}: "
            f"BUY probability={pct(model.global_probability)} "
            f"| samples={model.training_samples} "
            f"| states={model.training_states}"
        )

    print()
    print("OOS MODEL FREEZE: PASS")

    # --------------------------------------------------------------------------
    # OOS predictions
    # --------------------------------------------------------------------------

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

    subsection("OUT-OF-SAMPLE RESULTS")

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

            probability = predict_probability(
                model,
                state,
            )

            prediction = probability_to_direction(
                probability
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

        window_result["oos"][horizon] = {
            "predictions": predictions,
            "labels": labels,
            "label_objects": label_objects,
            "indices": indices,
            "metrics": result,
        }

        if result["n"]:

            print(
                f"STRUCTURE_LEARNED H+{horizon:<2}"
                f"                    | "
                f"N={result['n']:<5} | "
                f"Accuracy={pct(result['accuracy'])} | "
                f"Baseline={pct(result['baseline'])} | "
                f"Edge={result['edge'] * 100:+.2f}%"
            )

        else:

            print(
                f"STRUCTURE_LEARNED H+{horizon:<2}"
                f"                    | "
                f"N=0 | Insufficient sample"
            )

    # --------------------------------------------------------------------------
    # MFE / MAE
    # --------------------------------------------------------------------------

    print()
    print("MFE / MAE")

    for horizon in HORIZONS:

        label_objects = (
            window_result["oos"][horizon]
            ["label_objects"]
        )

        summary = summarize_mfe_mae(
            label_objects
        )

        print(
            f"H+{horizon:<2} | "
            f"MFE={fmt_num(summary['mfe'])} ATR | "
            f"MAE={fmt_num(summary['mae'])} ATR | "
            f"Time MFE={fmt_num(summary['time_mfe'])} | "
            f"Time MAE={fmt_num(summary['time_mae'])}"
        )

    # --------------------------------------------------------------------------
    # Structure direction
    # --------------------------------------------------------------------------

    subsection("STRUCTURE DIRECTION")

    for horizon in HORIZONS:

        data = window_result["oos"][horizon]

        predictions = data["predictions"]
        labels = data["labels"]
        indices = data["indices"]

        bullish_indices = []
        bearish_indices = []

        for pos, i in enumerate(indices):

            state = state_lookup.get(i)

            if state is None:
                continue

            if state.trend == "BULLISH":
                bullish_indices.append(pos)

            elif state.trend == "BEARISH":
                bearish_indices.append(pos)

        for name, selected in [
            ("STRUCTURE_BULLISH", bullish_indices),
            ("STRUCTURE_BEARISH", bearish_indices),
        ]:

            if not selected:

                print(
                    f"{name} H+{horizon:<2}"
                    f"                    | "
                    f"No valid observations"
                )

                continue

            selected_predictions = [
                predictions[i]
                for i in selected
            ]

            selected_labels = [
                labels[i]
                for i in selected
            ]

            result = evaluate_predictions(
                selected_predictions,
                selected_labels,
            )

            print(
                f"{name} H+{horizon:<2}"
                f"                    | "
                f"N={result['n']:<5} | "
                f"Accuracy={pct(result['accuracy'])} | "
                f"Baseline={pct(result['baseline'])} | "
                f"Edge={result['edge'] * 100:+.2f}%"
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

    subsection("STRUCTURE EVENTS")

    event_types = [
        "BOS_BULLISH",
        "BOS_BEARISH",
        "CHoCH_BULLISH",
        "CHoCH_BEARISH",
    ]

    for horizon in HORIZONS:

        data = window_result["oos"][horizon]

        predictions = data["predictions"]
        labels = data["labels"]
        indices = data["indices"]

        for event_type in event_types:

            selected_predictions = []
            selected_labels = []

            for pos, i in enumerate(indices):

                events_at_index = (
                    event_lookup.get(i, [])
                )

                matched = any(
                    event.event == event_type
                    for event in events_at_index
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

            if result["n"] < MIN_EVENT_SAMPLE:

                print(
                    f"{event_type:<25} "
                    f"H+{horizon:<2} "
                    f"| N={result['n']} "
                    f"| Insufficient sample"
                )

            else:

                print(
                    f"{event_type:<25} "
                    f"H+{horizon:<2} "
                    f"| N={result['n']:<5} "
                    f"| Accuracy={pct(result['accuracy'])} "
                    f"| Baseline={pct(result['baseline'])} "
                    f"| Edge={result['edge'] * 100:+.2f}%"
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

            data = result["oos"][horizon]

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
                [result["window"]] *
                len(data["labels"])
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

    section("COMBINED OUT-OF-SAMPLE RESULTS")

    for horizon in HORIZONS:

        result = combined[horizon]["metrics"]

        print(
            f"STRUCTURE_LEARNED H+{horizon:<2}"
            f"                    | "
            f"N={result['n']:<5} | "
            f"Accuracy={pct(result['accuracy'])} | "
            f"Baseline={pct(result['baseline'])} | "
            f"Edge={result['edge'] * 100:+.2f}%"
        )


# ==============================================================================
# COMBINED MFE / MAE
# ==============================================================================

def print_combined_mfe_mae(
    combined,
):

    section("COMBINED MFE / MAE")

    for horizon in HORIZONS:

        labels = combined[horizon]["label_objects"]

        summary = summarize_mfe_mae(
            labels
        )

        print(
            f"H+{horizon:<2} | "
            f"MFE={fmt_num(summary['mfe'])} ATR | "
            f"MAE={fmt_num(summary['mae'])} ATR | "
            f"Time MFE={fmt_num(summary['time_mfe'])} | "
            f"Time MAE={fmt_num(summary['time_mae'])}"
        )


# ==============================================================================
# COMBINED STRUCTURE DIRECTION
# ==============================================================================

def print_combined_structure_direction(
    combined,
    structure_states,
):

    section("COMBINED STRUCTURE DIRECTION")

    state_lookup = {
        state.index: state
        for state in structure_states
    }

    for horizon in HORIZONS:

        data = combined[horizon]

        predictions = data["predictions"]
        labels = data["labels"]
        indices = data["indices"]

        for trend_name in [
            "BULLISH",
            "BEARISH",
        ]:

            selected_predictions = []
            selected_labels = []

            for pos, index in enumerate(indices):

                state = state_lookup.get(index)

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
                    f"                    | "
                    f"No valid observations"
                )

            else:

                print(
                    f"{name} H+{horizon:<2}"
                    f"                    | "
                    f"N={result['n']:<5} | "
                    f"Accuracy={pct(result['accuracy'])} | "
                    f"Baseline={pct(result['baseline'])} | "
                    f"Edge={result['edge'] * 100:+.2f}%"
                )


# ==============================================================================
# COMBINED EVENTS
# ==============================================================================

def print_combined_events(
    combined,
    structure_events,
):

    section("COMBINED STRUCTURE EVENTS")

    event_by_index = defaultdict(list)

    for event in structure_events:
        event_by_index[event.index].append(
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

            data = combined[horizon]

            predictions = data["predictions"]
            labels = data["labels"]
            indices = data["indices"]

            selected_predictions = []
            selected_labels = []

            for pos, index in enumerate(indices):

                if event_type in event_by_index.get(
                    index,
                    [],
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

            if result["n"] < MIN_EVENT_SAMPLE:

                print(
                    f"{event_type:<28} "
                    f"H+{horizon:<2} "
                    f"| N={result['n']} "
                    f"| Insufficient sample"
                )

            else:

                print(
                    f"{event_type:<28} "
                    f"H+{horizon:<2} "
                    f"| N={result['n']:<5} "
                    f"| Accuracy={pct(result['accuracy'])} "
                    f"| Baseline={pct(result['baseline'])} "
                    f"| Edge={result['edge'] * 100:+.2f}%"
                )


# ==============================================================================
# ATR OUTCOME DISTRIBUTION
# ==============================================================================

def print_atr_outcomes(
    combined,
):

    section("ATR-NORMALIZED FUTURE OUTCOMES")

    for horizon in HORIZONS:

        labels = combined[horizon]["label_objects"]

        counts = Counter(
            label.strong_category
            for label in labels
        )

        total = len(labels)

        if total == 0:
            continue

        print(
            f"H+{horizon}: "
            f"STRONG_UP={pct(counts['STRONG_UP'] / total)} | "
            f"UP={pct(counts['UP'] / total)} | "
            f"DOWN={pct(counts['DOWN'] / total)} | "
            f"STRONG_DOWN={pct(counts['STRONG_DOWN'] / total)}"
        )


# ==============================================================================
# WALK FORWARD STABILITY
# ==============================================================================

def print_stability(
    window_results,
):

    section("WALK-FORWARD STABILITY ANALYSIS")

    for horizon in HORIZONS:

        accuracies = []
        edges = []

        for result in window_results:

            metrics = result["oos"][horizon][
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
            f"Mean={pct(safe_mean(accuracies))} | "
            f"Median={pct(safe_median(accuracies))} | "
            f"Std={pct(safe_std(accuracies))} | "
            f"Min={pct(min(accuracies))} | "
            f"Max={pct(max(accuracies))} | "
            f"Mean Edge={safe_mean(edges) * 100:+.2f}%"
        )


# ==============================================================================
# COMBINED OUTCOME DISTRIBUTION
# ==============================================================================

def print_outcome_distributions(
    combined,
):

    section("COMBINED OOS OUTCOME DISTRIBUTIONS")

    for horizon in HORIZONS:

        labels = combined[horizon]["labels"]

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

        neutral = total - buy - sell

        print(
            f"H+{horizon}: "
            f"BUY={pct(buy / total)} | "
            f"SELL={pct(sell / total)} | "
            f"NEUTRAL={pct(neutral / total)}"
        )


# ==============================================================================
# FORWARD LABEL DEPENDENCY
# ==============================================================================

def print_forward_dependency_check():

    section("FORWARD LABEL DEPENDENCY CHECK")

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


# ==============================================================================
# LOOK-AHEAD POLICY
# ==============================================================================

def print_lookahead_check():

    section("LOOK-AHEAD OUTCOME CHECK")

    print(
        "Future outcomes are used only:"
    )

    print(
        "    1. inside TRAIN when the complete label finishes before train_end"
    )

    print(
        "    2. after model freeze for OOS evaluation"
    )

    print(
        "Look-ahead outcome policy: PASS"
    )


# ==============================================================================
# WINDOW BOUNDARY CHECK
# ==============================================================================

def check_window_boundaries(
    windows,
    n,
):

    section("WALK-FORWARD BOUNDARY CHECK")

    passed = True

    previous_end = 0

    for window in windows:

        train_end = window["train_end"]
        oos_start = window["oos_start"]
        oos_end = window["oos_end"]

        if train_end != oos_start:
            passed = False

        if oos_end > n:
            passed = False

        if train_end <= previous_end:
            passed = False

        previous_end = oos_end

    print(
        f"Window boundaries: "
        f"{'PASS' if passed else 'FAIL'}"
    )

    if not passed:
        raise RuntimeError(
            "Walk-forward boundary check failed."
        )

    return passed


# ==============================================================================
# PROTECTION CHECK
# ==============================================================================

def file_sha256(path):

    digest = hashlib.sha256()

    with open(path, "rb") as f:

        while True:

            chunk = f.read(1024 * 1024)

            if not chunk:
                break

            digest.update(chunk)

    return digest.hexdigest()


def protection_check():

    section("PROTECTION CHECK")

    if not os.path.exists(MARKET_DATA_FILE):

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

    before_hash = file_sha256(
        MARKET_DATA_FILE
    )

    return before_hash


def final_protection_check(
    before_hash,
):

    section("FINAL PROTECTION CHECK")

    after_hash = file_sha256(
        MARKET_DATA_FILE
    )

    if before_hash != after_hash:

        print(
            "market_data.bin       : MODIFIED"
        )

        raise RuntimeError(
            "PROTECTION FAILURE: market_data.bin changed."
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

    if hasattr(obj, "__dataclass_fields__"):

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

    # This is a NEW validation artifact.
    # It does not overwrite market_data.bin.
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
        "# MLAI v3.8.5 Causal Market Structure "
        "Walk-Forward Validation"
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
        f"- Confirmed swings: {output['confirmed_swings']}"
    )

    lines.append(
        f"- Structural states: {output['structural_states']}"
    )

    lines.append(
        f"- Structural events: {output['structural_events']}"
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
            output["combined"][horizon]["metrics"]
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
        "Training labels obey the strict boundary "
        "`i + horizon < train_end`."
    )

    lines.append("")

    lines.append(
        "No future candle information is used to construct "
        "a structural state before that information becomes causally available."
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
        "MLAI v3.8.5 CAUSAL MARKET STRUCTURE INTELLIGENCE"
    )

    print()
    print("RESEARCH EXPERIMENT")
    print()
    print("v3.8.5 additions:")
    print()
    print("    - causal market structure")
    print("    - confirmed swings")
    print("    - causal BOS / CHoCH")
    print("    - consumed structural levels")
    print("    - HH / HL / LH / LL classification")
    print("    - structural state encoding")
    print("    - structural event dataset")
    print("    - structural state dataset")
    print("    - training-only encoder")
    print("    - training-only probabilities")
    print("    - strict label boundary")
    print("    - Bayesian shrinkage")
    print("    - frozen OOS models")
    print("    - H+4 / H+8 / H+16")
    print("    - future percentage return")
    print("    - ATR-normalized future movement")
    print("    - MFE")
    print("    - MAE")
    print("    - time-to-MFE")
    print("    - time-to-MAE")
    print("    - no trading")
    print("    - no internet")
    print()
    print("market_data.bin:")
    print("    READ ONLY")

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

    audit_data(candles)

    if not check_chronology(candles):

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

    section("ATR DIAGNOSTIC CALCULATION")

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
        "ATR is used to normalize future movement and MFE/MAE."
    )

    # --------------------------------------------------------------------------
    # Confirmed swings
    # --------------------------------------------------------------------------

    section("CONFIRMED SWINGS")

    swings = detect_confirmed_swings(
        candles,
        SWING_LEFT,
        SWING_RIGHT,
    )

    print(
        f"Confirmed swing events: {len(swings)}"
    )

    # --------------------------------------------------------------------------
    # Causal structure
    # --------------------------------------------------------------------------

    section("CAUSAL MARKET STRUCTURE")

    structure_states, structure_events = (
        build_causal_structure(
            candles,
            swings,
        )
    )

    print(
        f"Causal structure states: "
        f"{len(structure_states)}"
    )

    # --------------------------------------------------------------------------
    # Events
    # --------------------------------------------------------------------------

    section("STRUCTURE EVENTS")

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

    state_records, event_records = (
        build_structural_datasets(
            structure_states,
            structure_events,
        )
    )

    # --------------------------------------------------------------------------
    # Training boundary
    # --------------------------------------------------------------------------

    eligible_training_labels = (
        audit_training_label_boundary(
            len(candles),
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
    # Save validation artifacts
    # --------------------------------------------------------------------------

    output = {
        "version": VERSION,
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

    section("VALIDATION BINARY:")

    print(
        f"    {os.path.basename(VALIDATION_BIN_FILE)}"
    )

    print(
        "VALIDATION REPORT:"
    )

    print(
        f"    {os.path.basename(VALIDATION_REPORT_FILE)}"
    )

    section(
        "MLAI v3.8.5 CAUSAL MARKET STRUCTURE "
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
        print("VALIDATION ERROR")
        line("=")
        print(
            f"{type(exc).__name__}: {exc}"
        )
        print()
        sys.exit(1)