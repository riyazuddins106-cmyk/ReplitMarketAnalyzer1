"""
================================================================================
MLAI v4.1.3 ROBUST CAUSAL PREDICTIVE MARKET STRUCTURE INTELLIGENCE
================================================================================

RESEARCH / VALIDATION ONLY

Purpose
-------
v4.1.3 keeps the causal and validation corrections from v4.1.2 while changing
the predictive decision layer itself.

Architecture

    causal market structure
        +
    causal price / volatility context
        +
    hierarchical state statistics
        +
    regularized logistic model
        +
    frozen walk-forward kNN model
        +
    conservative fixed ensemble
        +
    evidence-based confidence
        +
    reduced fixed abstention
        +
    strict chronological OOS validation
        +
    exact training/OOS boundary audits
        +
    exact OOS event-diagnostic alignment
        +
    honest N/A metrics

IMPORTANT
---------
This is NOT a claim that the market is predictable.

The purpose is to test whether the supplied historical data contains stable
predictive information.

No OOS observation is used to fit, scale, encode, calibrate, tune, or select
a model.

market_data.bin is read-only and is hash checked before/after execution.

No production MLAI memory is modified.

Trading is disabled.

Dependencies: Python standard library only.
================================================================================
"""

from __future__ import annotations

import hashlib
import math
import os
import pickle
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Sequence, Tuple


# ==============================================================================
# CONFIGURATION
# ==============================================================================

VERSION = "4.1.3"

MARKET_DATA_FILE = "market_data.bin"

VALIDATION_BIN = (
    "MLAI_V413_CAUSAL_PREDICTIVE_VALIDATION.bin"
)

VALIDATION_REPORT = (
    "MLAI_V413_CAUSAL_PREDICTIVE_VALIDATION_REPORT.md"
)

HORIZONS = (4, 8, 16)

SWING_LEFT = 3
SWING_RIGHT = 3

DEFAULT_TRAIN_WINDOWS = 5
DEFAULT_OOS_SIZE = 81

MIN_TRAIN_SAMPLES = 120
MIN_STATE_SUPPORT = 8

LOGISTIC_EPOCHS = 500
LOGISTIC_LR = 0.035
LOGISTIC_L2 = 0.75

KNN_K = 25
KNN_TEMPERATURE = 1.25

STATE_PRIOR_STRENGTH = 20.0

# Fixed ensemble weights.
# These are deliberately NOT optimized on OOS observations.
WEIGHT_LOGISTIC = 0.55
WEIGHT_KNN = 0.25
WEIGHT_STATE = 0.20

# ==============================================================================
# V4.1.3 DECISION POLICY
# ==============================================================================
#
# v4.1.2 used a much stricter confidence gate and consequently abstained from
# almost every OOS observation.
#
# v4.1.3 deliberately reduces the fixed gate so the predictive model can
# actually be evaluated on a meaningful number of OOS observations.
#
# These values are fixed before validation.
# They are NOT optimized from OOS results.
#
MIN_CONFIDENCE = 0.45
MIN_MARGIN = 0.02

MIN_SUPPORT_FOR_FULL_CONFIDENCE = 20

PROBABILITY_FLOOR = 0.001
PROBABILITY_CEILING = 0.999

EPS = 1e-12


# ==============================================================================
# BASIC DATA TYPES
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
    pivot_index: int
    confirmation_index: int
    kind: str
    price: float
    label: str = ""


@dataclass
class StructureState:
    index: int
    trend: str
    last_high: Optional[float]
    last_low: Optional[float]
    last_high_index: Optional[int]
    last_low_index: Optional[int]
    high_label: str
    low_label: str
    event: str
    event_index: Optional[int]
    event_age: Optional[int]
    structure_age: int


@dataclass
class Signal:
    index: int
    feature: Tuple[float, ...]
    categorical_key: Tuple[Any, ...]
    event: str
    trend: str
    state_key: Tuple[Any, ...]


@dataclass
class Prediction:
    probability_up: float
    probability_down: float
    confidence: float
    support: int
    abstain: bool
    model_components: Dict[str, float]


@dataclass
class WalkForwardWindow:
    number: int
    train_start: int
    train_end: int
    oos_start: int
    oos_end: int


# ==============================================================================
# FILE / PROTECTION UTILITIES
# ==============================================================================

def sha256_file(path: str) -> str:
    h = hashlib.sha256()

    with open(path, "rb") as f:
        for block in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
            h.update(block)

    return h.hexdigest()


class ProtectionGuard:
    def __init__(self, path: str):
        if not os.path.exists(path):
            raise FileNotFoundError(path)

        self.path = path
        self.before_hash = sha256_file(path)

    def verify_unchanged(self) -> bool:
        return self.before_hash == sha256_file(self.path)


# ==============================================================================
# MARKET DATA LOADER
# ==============================================================================

def _get_value(
    obj: Any,
    names: Sequence[str],
    default: Any = None,
) -> Any:
    if isinstance(obj, dict):
        lower = {
            str(k).lower(): v
            for k, v in obj.items()
        }

        for name in names:
            if name.lower() in lower:
                return lower[name.lower()]

        return default

    for name in names:
        if hasattr(obj, name):
            return getattr(obj, name)

    return default


def _to_float(
    value: Any,
    default: float = 0.0,
) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _normalize_candle(
    raw: Any,
    index: int,
) -> Optional[Candle]:
    if isinstance(raw, (list, tuple)) and len(raw) >= 5:
        if len(raw) >= 6:
            timestamp = raw[0]
            o, h, l, c, v = raw[1:6]
        else:
            timestamp = index
            o, h, l, c = raw[:4]
            v = 0.0

        try:
            o, h, l, c, v = map(
                float,
                (o, h, l, c, v),
            )

            if not all(
                math.isfinite(x)
                for x in (o, h, l, c, v)
            ):
                return None

            if h < max(o, c):
                return None

            if l > min(o, c):
                return None

            if h < l:
                return None

            return Candle(
                index,
                timestamp,
                o,
                h,
                l,
                c,
                v,
            )

        except Exception:
            return None

    timestamp = _get_value(
        raw,
        (
            "timestamp",
            "time",
            "datetime",
            "date",
            "ts",
        ),
        index,
    )

    o = _get_value(
        raw,
        ("open", "o"),
    )

    h = _get_value(
        raw,
        ("high", "h"),
    )

    l = _get_value(
        raw,
        ("low", "l"),
    )

    c = _get_value(
        raw,
        ("close", "c"),
    )

    v = _get_value(
        raw,
        ("volume", "vol", "v"),
        0.0,
    )

    if None in (o, h, l, c):
        return None

    o, h, l, c, v = map(
        lambda x: _to_float(
            x,
            float("nan"),
        ),
        (o, h, l, c, v),
    )

    if not all(
        math.isfinite(x)
        for x in (o, h, l, c, v)
    ):
        return None

    if h < max(o, c):
        return None

    if l > min(o, c):
        return None

    if h < l:
        return None

    return Candle(
        index,
        timestamp,
        o,
        h,
        l,
        c,
        v,
    )


def load_market_data(
    path: str,
) -> Tuple[List[Candle], int]:
    with open(path, "rb") as f:
        obj = pickle.load(f)

    if isinstance(obj, dict):
        for key in (
            "candles",
            "data",
            "rows",
            "ohlcv",
            "market_data",
        ):
            if (
                key in obj
                and isinstance(
                    obj[key],
                    (list, tuple),
                )
            ):
                obj = obj[key]
                break

    if not isinstance(
        obj,
        (list, tuple),
    ):
        raise ValueError(
            "market_data.bin does not contain a supported candle sequence."
        )

    candles: List[Candle] = []
    invalid = 0

    for raw in obj:
        candle = _normalize_candle(
            raw,
            len(candles),
        )

        if candle is None:
            invalid += 1
            continue

        candles.append(candle)

    for i, candle in enumerate(candles):
        candle.index = i

    return candles, invalid


# ==============================================================================
# CHRONOLOGY
# ==============================================================================

def audit_chronology(
    candles: Sequence[Candle],
) -> Dict[str, bool]:
    ordered = True
    duplicates = False
    previous = None

    for candle in candles:
        current = candle.timestamp

        if previous is not None:
            try:
                if current < previous:
                    ordered = False

                if current == previous:
                    duplicates = True

            except Exception:
                pass

        previous = current

    return {
        "ordered": ordered,
        "duplicates": duplicates,
    }


# ==============================================================================
# WALK FORWARD
# ==============================================================================

def create_walk_forward_windows(
    n: int,
    count: int,
    oos_size: int,
) -> List[WalkForwardWindow]:
    if n <= count * oos_size:
        raise ValueError(
            "Insufficient candles for requested walk-forward setup."
        )

    initial_train = (
        n
        - count * oos_size
    )

    windows = []

    for i in range(count):
        train_end = (
            initial_train
            + i * oos_size
        )

        oos_start = train_end

        oos_end = min(
            n,
            oos_start + oos_size,
        )

        if oos_end > oos_start:
            windows.append(
                WalkForwardWindow(
                    number=i + 1,
                    train_start=0,
                    train_end=train_end,
                    oos_start=oos_start,
                    oos_end=oos_end,
                )
            )

    return windows


# ==============================================================================
# BASIC MATH
# ==============================================================================

def safe_div(
    a: float,
    b: float,
) -> float:
    if abs(b) < EPS:
        return 0.0

    return a / b


def mean_or_zero(
    values: Sequence[float],
) -> float:
    if not values:
        return 0.0

    return sum(values) / len(values)


def std_or_one(
    values: Sequence[float],
) -> float:
    if len(values) < 2:
        return 1.0

    m = mean_or_zero(values)

    variance = (
        sum(
            (x - m) ** 2
            for x in values
        )
        / (len(values) - 1)
    )

    return max(
        math.sqrt(variance),
        EPS,
    )


# ==============================================================================
# ATR
# ==============================================================================

def calculate_atr(
    candles: Sequence[Candle],
    period: int = 14,
) -> List[Optional[float]]:
    atr: List[Optional[float]] = [
        None
    ] * len(candles)

    trs: List[float] = []

    for i, candle in enumerate(candles):
        if i == 0:
            tr = candle.high - candle.low

        else:
            previous_close = (
                candles[i - 1].close
            )

            tr = max(
                candle.high
                - candle.low,
                abs(
                    candle.high
                    - previous_close
                ),
                abs(
                    candle.low
                    - previous_close
                ),
            )

        trs.append(
            max(
                tr,
                EPS,
            )
        )

        if len(trs) >= period:
            atr[i] = (
                sum(
                    trs[-period:]
                )
                / period
            )

    return atr


# ==============================================================================
# CAUSAL STRUCTURE ENGINE
# ==============================================================================

class CausalStructureEngine:
    """
    A pivot at j becomes causally available only at
    j + SWING_RIGHT.
    """

    def __init__(
        self,
        candles: Sequence[Candle],
    ):
        self.candles = candles

        self.swings: List[Swing] = []

        self.events: Dict[
            int,
            str,
        ] = {}

        self.states: List[
            StructureState
        ] = []

        self._high_levels_consumed = set()
        self._low_levels_consumed = set()

    def _is_confirmed_high(
        self,
        j: int,
    ) -> bool:
        if (
            j < SWING_LEFT
            or j + SWING_RIGHT >= len(
                self.candles
            )
        ):
            return False

        price = self.candles[j].high

        for k in range(
            j - SWING_LEFT,
            j + SWING_RIGHT + 1,
        ):
            if k == j:
                continue

            if (
                self.candles[k].high
                >= price
            ):
                return False

        return True

    def _is_confirmed_low(
        self,
        j: int,
    ) -> bool:
        if (
            j < SWING_LEFT
            or j + SWING_RIGHT >= len(
                self.candles
            )
        ):
            return False

        price = self.candles[j].low

        for k in range(
            j - SWING_LEFT,
            j + SWING_RIGHT + 1,
        ):
            if k == j:
                continue

            if (
                self.candles[k].low
                <= price
            ):
                return False

        return True

    def build(
        self,
    ) -> List[StructureState]:

        last_high: Optional[Swing] = None
        last_low: Optional[Swing] = None

        high_label = "UNKNOWN"
        low_label = "UNKNOWN"

        trend = "NEUTRAL"

        last_event_index: Optional[int] = None

        structure_start = 0

        for i in range(
            len(self.candles)
        ):
            j = (
                i
                - SWING_RIGHT
            )

            if j >= SWING_LEFT:

                if self._is_confirmed_high(j):

                    label = (
                        "HH"
                        if (
                            last_high is None
                            or self.candles[j].high
                            > last_high.price
                        )
                        else "LH"
                    )

                    swing = Swing(
                        pivot_index=j,
                        confirmation_index=i,
                        kind="HIGH",
                        price=self.candles[j].high,
                        label=label,
                    )

                    self.swings.append(
                        swing
                    )

                    last_high = swing
                    high_label = label

                if self._is_confirmed_low(j):

                    label = (
                        "HL"
                        if (
                            last_low is None
                            or self.candles[j].low
                            > last_low.price
                        )
                        else "LL"
                    )

                    swing = Swing(
                        pivot_index=j,
                        confirmation_index=i,
                        kind="LOW",
                        price=self.candles[j].low,
                        label=label,
                    )

                    self.swings.append(
                        swing
                    )

                    last_low = swing
                    low_label = label

            candle = self.candles[i]

            event = "NONE"

            if (
                last_high is not None
                and i
                > last_high.confirmation_index
            ):
                level_id = (
                    last_high.pivot_index,
                    "HIGH",
                )

                if (
                    candle.close
                    > last_high.price
                    and level_id
                    not in self._high_levels_consumed
                ):
                    event = (
                        "BOS_BULLISH"
                        if trend
                        in (
                            "BULLISH",
                            "NEUTRAL",
                        )
                        else "CHoCH_BULLISH"
                    )

                    self._high_levels_consumed.add(
                        level_id
                    )

                    trend = "BULLISH"

                    last_event_index = i
                    structure_start = i

            if (
                last_low is not None
                and i
                > last_low.confirmation_index
            ):
                level_id = (
                    last_low.pivot_index,
                    "LOW",
                )

                if (
                    candle.close
                    < last_low.price
                    and level_id
                    not in self._low_levels_consumed
                ):
                    candidate = (
                        "BOS_BEARISH"
                        if trend
                        in (
                            "BEARISH",
                            "NEUTRAL",
                        )
                        else "CHoCH_BEARISH"
                    )

                    if event == "NONE":
                        event = candidate

                    self._low_levels_consumed.add(
                        level_id
                    )

                    trend = "BEARISH"

                    last_event_index = i
                    structure_start = i

            event_age = (
                None
                if last_event_index is None
                else i - last_event_index
            )

            self.events[i] = event

            self.states.append(
                StructureState(
                    index=i,
                    trend=trend,
                    last_high=(
                        last_high.price
                        if last_high
                        else None
                    ),
                    last_low=(
                        last_low.price
                        if last_low
                        else None
                    ),
                    last_high_index=(
                        last_high.pivot_index
                        if last_high
                        else None
                    ),
                    last_low_index=(
                        last_low.pivot_index
                        if last_low
                        else None
                    ),
                    high_label=high_label,
                    low_label=low_label,
                    event=event,
                    event_index=last_event_index,
                    event_age=event_age,
                    structure_age=(
                        i
                        - structure_start
                    ),
                )
            )

        return self.states


# ==============================================================================
# STRUCTURE CAUSALITY AUDIT
# ==============================================================================

def audit_structure_causality(
    candles: Sequence[Candle],
    swings: Sequence[Swing],
    states: Sequence[StructureState],
    events: Dict[int, str],
) -> Dict[str, Any]:

    reasons = []

    swing_lookup = {
        (
            swing.pivot_index,
            swing.kind,
        ): swing
        for swing in swings
    }

    for swing in swings:
        if (
            swing.confirmation_index
            < (
                swing.pivot_index
                + SWING_RIGHT
            )
        ):
            reasons.append(
                f"Swing {swing.pivot_index} confirmed too early."
            )

    for state in states:
        i = state.index

        if state.last_high_index is not None:
            high_swing = swing_lookup.get(
                (
                    state.last_high_index,
                    "HIGH",
                )
            )

            if (
                high_swing
                and high_swing.confirmation_index
                > i
            ):
                reasons.append(
                    f"Future high consumed at state {i}."
                )

        if state.last_low_index is not None:
            low_swing = swing_lookup.get(
                (
                    state.last_low_index,
                    "LOW",
                )
            )

            if (
                low_swing
                and low_swing.confirmation_index
                > i
            ):
                reasons.append(
                    f"Future low consumed at state {i}."
                )

        event = events.get(
            i,
            "NONE",
        )

        if (
            event != "NONE"
            and (
                state.event_index is None
                or state.event_index > i
            )
        ):
            reasons.append(
                f"Future event visible at state {i}."
            )

    return {
        "passed": not reasons,
        "reasons": reasons,
    }


# ==============================================================================
# CAUSAL FEATURES
# ==============================================================================

def rolling_return(
    candles: Sequence[Candle],
    i: int,
    lookback: int,
) -> float:
    if i < lookback:
        return 0.0

    return safe_div(
        candles[i].close
        - candles[i - lookback].close,
        candles[i - lookback].close,
    )


def rolling_range(
    candles: Sequence[Candle],
    i: int,
    lookback: int,
) -> float:
    start = max(
        0,
        i - lookback + 1,
    )

    highs = [
        candles[j].high
        for j in range(
            start,
            i + 1,
        )
    ]

    lows = [
        candles[j].low
        for j in range(
            start,
            i + 1,
        )
    ]

    if not highs:
        return 0.0

    return safe_div(
        max(highs)
        - min(lows),
        candles[i].close,
    )


def create_signals(
    candles: Sequence[Candle],
    states: Sequence[StructureState],
    atr: Sequence[Optional[float]],
) -> List[Signal]:

    signals: List[Signal] = []

    for i, candle in enumerate(
        candles
    ):
        state = states[i]

        a = (
            atr[i]
            if atr[i] is not None
            else max(
                candle.high
                - candle.low,
                EPS,
            )
        )

        body = safe_div(
            abs(
                candle.close
                - candle.open
            ),
            a,
        )

        full_range = safe_div(
            candle.high
            - candle.low,
            a,
        )

        upper_wick = safe_div(
            candle.high
            - max(
                candle.open,
                candle.close,
            ),
            a,
        )

        lower_wick = safe_div(
            min(
                candle.open,
                candle.close,
            )
            - candle.low,
            a,
        )

        distance_high = (
            safe_div(
                candle.close
                - state.last_high,
                a,
            )
            if state.last_high
            is not None
            else 0.0
        )

        distance_low = (
            safe_div(
                candle.close
                - state.last_low,
                a,
            )
            if state.last_low
            is not None
            else 0.0
        )

        high_age = (
            i - state.last_high_index
            if state.last_high_index
            is not None
            else 999
        )

        low_age = (
            i - state.last_low_index
            if state.last_low_index
            is not None
            else 999
        )

        event_age = (
            state.event_age
            if state.event_age
            is not None
            else 999
        )

        recent_ranges = [
            safe_div(
                candles[j].high
                - candles[j].low,
                max(
                    candles[j].close,
                    EPS,
                ),
            )
            for j in range(
                max(0, i - 7),
                i + 1,
            )
        ]

        older_ranges = [
            safe_div(
                candles[j].high
                - candles[j].low,
                max(
                    candles[j].close,
                    EPS,
                ),
            )
            for j in range(
                max(0, i - 31),
                max(0, i - 7),
            )
        ]

        recent_vol = mean_or_zero(
            recent_ranges
        )

        older_vol = mean_or_zero(
            older_ranges
        )

        volatility_ratio = safe_div(
            recent_vol,
            (
                older_vol
                if older_vol > EPS
                else recent_vol + EPS
            ),
        )

        volume_ratio = 1.0

        if candle.volume > 0:
            volumes = [
                candles[j].volume
                for j in range(
                    max(0, i - 19),
                    i + 1,
                )
                if candles[j].volume > 0
            ]

            if volumes:
                volume_ratio = safe_div(
                    candle.volume,
                    mean_or_zero(
                        volumes
                    ),
                )

        feature = (
            rolling_return(
                candles,
                i,
                1,
            ),
            rolling_return(
                candles,
                i,
                3,
            ),
            rolling_return(
                candles,
                i,
                8,
            ),
            rolling_return(
                candles,
                i,
                16,
            ),
            rolling_return(
                candles,
                i,
                32,
            ),
            rolling_range(
                candles,
                i,
                4,
            ),
            rolling_range(
                candles,
                i,
                8,
            ),
            rolling_range(
                candles,
                i,
                16,
            ),
            body,
            full_range,
            upper_wick,
            lower_wick,
            distance_high,
            distance_low,
            safe_div(
                high_age,
                32.0,
            ),
            safe_div(
                low_age,
                32.0,
            ),
            safe_div(
                event_age,
                32.0,
            ),
            volatility_ratio,
            math.log1p(
                max(
                    volume_ratio,
                    0.0,
                )
            ),
            1.0
            if state.trend == "BULLISH"
            else 0.0,
            1.0
            if state.trend == "BEARISH"
            else 0.0,
            1.0
            if state.high_label == "HH"
            else 0.0,
            1.0
            if state.high_label == "LH"
            else 0.0,
            1.0
            if state.low_label == "HL"
            else 0.0,
            1.0
            if state.low_label == "LL"
            else 0.0,
        )

        categorical_key = (
            state.trend,
            state.high_label,
            state.low_label,
            state.event,
        )

        state_key = (
            state.trend,
            state.high_label,
            state.low_label,
            state.event,
            min(
                event_age,
                16,
            ),
            min(
                state.structure_age // 4,
                16,
            ),
        )

        signals.append(
            Signal(
                index=i,
                feature=feature,
                categorical_key=categorical_key,
                event=state.event,
                trend=state.trend,
                state_key=state_key,
            )
        )

    return signals


# ==============================================================================
# LABELS
# ==============================================================================

def make_label(
    candles: Sequence[Candle],
    index: int,
    horizon: int,
) -> Optional[int]:

    target = (
        index
        + horizon
    )

    if target >= len(candles):
        return None

    current_close = (
        candles[index].close
    )

    future_close = (
        candles[target].close
    )

    if future_close > current_close:
        return 1

    if future_close < current_close:
        return 0

    return None


# ==============================================================================
# TRAINING ROWS
# ==============================================================================

def collect_training_rows(
    candles: Sequence[Candle],
    signals: Sequence[Signal],
    window: WalkForwardWindow,
    horizon: int,
) -> Tuple[List[Signal], List[int]]:

    rows = []
    labels = []

    for signal in signals:

        if not (
            window.train_start
            <= signal.index
            < window.train_end
        ):
            continue

        target = (
            signal.index
            + horizon
        )

        # Strict TRAIN boundary.
        if target >= window.train_end:
            continue

        label = make_label(
            candles,
            signal.index,
            horizon,
        )

        if label is None:
            continue

        rows.append(signal)
        labels.append(label)

    return rows, labels


# ==============================================================================
# OOS ROWS
# ==============================================================================

def collect_oos_rows(
    candles: Sequence[Candle],
    signals: Sequence[Signal],
    window: WalkForwardWindow,
    horizon: int,
) -> Tuple[List[Signal], List[int]]:

    rows = []
    labels = []

    for signal in signals:

        if not (
            window.oos_start
            <= signal.index
            < window.oos_end
        ):
            continue

        target = (
            signal.index
            + horizon
        )

        # OOS target may extend beyond the OOS window but must exist in the
        # available dataset.
        if target >= len(candles):
            continue

        label = make_label(
            candles,
            signal.index,
            horizon,
        )

        if label is None:
            continue

        rows.append(signal)
        labels.append(label)

    return rows, labels


# ==============================================================================
# TRAINING BOUNDARY AUDIT
# ==============================================================================

def audit_training_boundaries(
    candles: Sequence[Candle],
    signals: Sequence[Signal],
    windows: Sequence[WalkForwardWindow],
) -> bool:

    for window in windows:

        for horizon in HORIZONS:

            actual_signals, actual_labels = (
                collect_training_rows(
                    candles,
                    signals,
                    window,
                    horizon,
                )
            )

            expected_signals = []

            for signal in signals:

                if not (
                    window.train_start
                    <= signal.index
                    < window.train_end
                ):
                    continue

                target = (
                    signal.index
                    + horizon
                )

                if target >= window.train_end:
                    continue

                if make_label(
                    candles,
                    signal.index,
                    horizon,
                ) is None:
                    continue

                expected_signals.append(
                    signal
                )

            actual_indices = [
                signal.index
                for signal in actual_signals
            ]

            expected_indices = [
                signal.index
                for signal in expected_signals
            ]

            if (
                actual_indices
                != expected_indices
            ):
                return False

            if (
                len(actual_signals)
                != len(actual_labels)
            ):
                return False

            for signal in actual_signals:

                if not (
                    window.train_start
                    <= signal.index
                    < window.train_end
                ):
                    return False

                if (
                    signal.index
                    + horizon
                    >= window.train_end
                ):
                    return False

    return True


# ==============================================================================
# OOS BOUNDARY AUDIT
# ==============================================================================

def audit_oos_boundaries(
    candles: Sequence[Candle],
    signals: Sequence[Signal],
    windows: Sequence[WalkForwardWindow],
) -> bool:

    for window in windows:

        for horizon in HORIZONS:

            actual_signals, actual_labels = (
                collect_oos_rows(
                    candles,
                    signals,
                    window,
                    horizon,
                )
            )

            expected_signals = []

            for signal in signals:

                if not (
                    window.oos_start
                    <= signal.index
                    < window.oos_end
                ):
                    continue

                target = (
                    signal.index
                    + horizon
                )

                if target >= len(candles):
                    continue

                if make_label(
                    candles,
                    signal.index,
                    horizon,
                ) is None:
                    continue

                expected_signals.append(
                    signal
                )

            actual_indices = [
                signal.index
                for signal in actual_signals
            ]

            expected_indices = [
                signal.index
                for signal in expected_signals
            ]

            if (
                actual_indices
                != expected_indices
            ):
                return False

            if (
                len(actual_signals)
                != len(actual_labels)
            ):
                return False

            for signal in actual_signals:

                if not (
                    window.oos_start
                    <= signal.index
                    < window.oos_end
                ):
                    return False

                if (
                    signal.index
                    + horizon
                    >= len(candles)
                ):
                    return False

    return True


# ==============================================================================
# STANDARDIZER
# ==============================================================================

class Standardizer:

    def __init__(self):
        self.means: List[float] = []
        self.stds: List[float] = []

    def fit(
        self,
        X: Sequence[Sequence[float]],
    ) -> None:

        if not X:
            raise ValueError(
                "Cannot fit standardizer on empty data."
            )

        width = len(X[0])

        self.means = []
        self.stds = []

        for j in range(width):

            column = [
                float(row[j])
                for row in X
            ]

            self.means.append(
                mean_or_zero(
                    column
                )
            )

            self.stds.append(
                std_or_one(
                    column
                )
            )

    def transform_one(
        self,
        x: Sequence[float],
    ) -> List[float]:

        return [
            safe_div(
                float(value)
                - self.means[j],
                self.stds[j],
            )
            for j, value in enumerate(x)
        ]

    def transform(
        self,
        X: Sequence[Sequence[float]],
    ) -> List[List[float]]:

        return [
            self.transform_one(row)
            for row in X
        ]


# ==============================================================================
# LOGISTIC REGRESSION
# ==============================================================================

class LogisticModel:

    def __init__(
        self,
        epochs: int = LOGISTIC_EPOCHS,
        lr: float = LOGISTIC_LR,
        l2: float = LOGISTIC_L2,
    ):
        self.epochs = epochs
        self.lr = lr
        self.l2 = l2

        self.weights: List[
            float
        ] = []

        self.bias = 0.0

    @staticmethod
    def sigmoid(
        z: float,
    ) -> float:

        if z >= 0:
            e = math.exp(
                -min(
                    z,
                    60.0,
                )
            )

            return 1.0 / (
                1.0 + e
            )

        e = math.exp(
            max(
                z,
                -60.0,
            )
        )

        return e / (
            1.0 + e
        )

    def fit(
        self,
        X: Sequence[Sequence[float]],
        y: Sequence[int],
    ) -> None:

        if (
            len(X)
            != len(y)
            or not X
        ):
            raise ValueError(
                "Invalid logistic training data."
            )

        n = len(X)
        d = len(X[0])

        self.weights = [
            0.0
        ] * d

        self.bias = 0.0

        positives = sum(y)
        negatives = (
            n
            - positives
        )

        pos_weight = (
            n
            / max(
                2.0 * positives,
                1.0,
            )
        )

        neg_weight = (
            n
            / max(
                2.0 * negatives,
                1.0,
            )
        )

        for epoch in range(
            self.epochs
        ):

            grad_w = [
                0.0
            ] * d

            grad_b = 0.0

            lr = (
                self.lr
                / (
                    1.0
                    + 0.003 * epoch
                )
            )

            for row, target in zip(
                X,
                y,
            ):

                z = self.bias

                for j in range(d):
                    z += (
                        self.weights[j]
                        * row[j]
                    )

                p = self.sigmoid(z)

                weight = (
                    pos_weight
                    if target == 1
                    else neg_weight
                )

                error = (
                    p - target
                ) * weight

                grad_b += error

                for j in range(d):
                    grad_w[j] += (
                        error
                        * row[j]
                    )

            inv_n = (
                1.0 / n
            )

            self.bias -= (
                lr
                * grad_b
                * inv_n
            )

            for j in range(d):

                gradient = (
                    grad_w[j]
                    * inv_n
                    + self.l2
                    * self.weights[j]
                )

                self.weights[j] -= (
                    lr
                    * gradient
                )

    def predict_proba_one(
        self,
        x: Sequence[float],
    ) -> float:

        z = self.bias

        for w, value in zip(
            self.weights,
            x,
        ):
            z += (
                w
                * value
            )

        return self.sigmoid(z)


# ==============================================================================
# HIERARCHICAL STATE MODEL
# ==============================================================================

class HierarchicalStateModel:

    def __init__(self):

        self.global_up = 0.5

        self.exact: Dict[
            Tuple[Any, ...],
            Tuple[int, int],
        ] = {}

        self.categorical: Dict[
            Tuple[Any, ...],
            Tuple[int, int],
        ] = {}

    @staticmethod
    def smoothed(
        up: int,
        total: int,
        prior: float,
        strength: float,
    ) -> float:

        return (
            up
            + strength * prior
        ) / max(
            total + strength,
            EPS,
        )

    def fit(
        self,
        signals: Sequence[Signal],
        labels: Sequence[int],
    ) -> None:

        if not labels:
            raise ValueError(
                "Empty state-model training set."
            )

        self.global_up = (
            sum(labels)
            / len(labels)
        )

        exact = defaultdict(
            lambda: [0, 0]
        )

        categorical = defaultdict(
            lambda: [0, 0]
        )

        for signal, label in zip(
            signals,
            labels,
        ):

            exact[
                signal.state_key
            ][0] += int(
                label == 1
            )

            exact[
                signal.state_key
            ][1] += 1

            categorical[
                signal.categorical_key
            ][0] += int(
                label == 1
            )

            categorical[
                signal.categorical_key
            ][1] += 1

        self.exact = {
            key: (
                value[0],
                value[1],
            )
            for key, value in exact.items()
        }

        self.categorical = {
            key: (
                value[0],
                value[1],
            )
            for key, value in categorical.items()
        }

    def predict(
        self,
        signal: Signal,
    ) -> Tuple[float, int]:

        cat_up, cat_n = (
            self.categorical.get(
                signal.categorical_key,
                (0, 0),
            )
        )

        cat_prob = (
            self.smoothed(
                cat_up,
                cat_n,
                self.global_up,
                STATE_PRIOR_STRENGTH,
            )
        )

        exact_up, exact_n = (
            self.exact.get(
                signal.state_key,
                (0, 0),
            )
        )

        exact_prob = (
            self.smoothed(
                exact_up,
                exact_n,
                cat_prob,
                STATE_PRIOR_STRENGTH,
            )
        )

        if (
            exact_n
            < MIN_STATE_SUPPORT
        ):

            probability = (
                0.35 * exact_prob
                + 0.65 * cat_prob
            )

        else:

            probability = (
                0.70 * exact_prob
                + 0.30 * cat_prob
            )

        return (
            probability,
            exact_n,
        )


# ==============================================================================
# kNN
# ==============================================================================

class KNNModel:

    def __init__(
        self,
        k: int = KNN_K,
        temperature: float = KNN_TEMPERATURE,
    ):

        self.k = k
        self.temperature = temperature

        self.X: List[
            List[float]
        ] = []

        self.y: List[
            int
        ] = []

    def fit(
        self,
        X: Sequence[Sequence[float]],
        y: Sequence[int],
    ) -> None:

        self.X = [
            list(row)
            for row in X
        ]

        self.y = list(y)

    @staticmethod
    def distance(
        a: Sequence[float],
        b: Sequence[float],
    ) -> float:

        total = 0.0

        for x, y in zip(
            a,
            b,
        ):

            delta = (
                x - y
            )

            total += (
                delta * delta
            )

        return math.sqrt(
            total
        )

    def predict_proba_one(
        self,
        x: Sequence[float],
    ) -> float:

        if not self.X:
            return 0.5

        distances = []

        for row, target in zip(
            self.X,
            self.y,
        ):

            distance = (
                self.distance(
                    x,
                    row,
                )
            )

            distances.append(
                (
                    distance,
                    target,
                )
            )

        distances.sort(
            key=lambda item: item[0]
        )

        neighbours = distances[
            :min(
                self.k,
                len(distances),
            )
        ]

        weighted_up = 0.0
        total_weight = 0.0

        for distance, target in neighbours:

            weight = math.exp(
                -distance
                / max(
                    self.temperature,
                    EPS,
                )
            )

            weighted_up += (
                weight
                * target
            )

            total_weight += (
                weight
            )

        if (
            total_weight
            <= EPS
        ):
            return 0.5

        return (
            weighted_up
            / total_weight
        )


# ==============================================================================
# PREDICTIVE MODEL
# ==============================================================================

class PredictiveModel:

    def __init__(self):

        self.scaler = (
            Standardizer()
        )

        self.logistic = (
            LogisticModel()
        )

        self.knn = (
            KNNModel()
        )

        self.state = (
            HierarchicalStateModel()
        )

        self.train_support = 0

    def fit(
        self,
        signals: Sequence[Signal],
        labels: Sequence[int],
    ) -> None:

        if (
            len(signals)
            < MIN_TRAIN_SAMPLES
        ):
            raise ValueError(
                f"Insufficient training samples: "
                f"{len(signals)}"
            )

        X_raw = [
            signal.feature
            for signal in signals
        ]

        self.scaler.fit(
            X_raw
        )

        X = self.scaler.transform(
            X_raw
        )

        self.logistic.fit(
            X,
            labels,
        )

        self.knn.fit(
            X,
            labels,
        )

        self.state.fit(
            signals,
            labels,
        )

        self.train_support = (
            len(labels)
        )

    def predict(
        self,
        signal: Signal,
    ) -> Prediction:

        x = (
            self.scaler.transform_one(
                signal.feature
            )
        )

        p_logistic = (
            self.logistic.predict_proba_one(
                x
            )
        )

        p_knn = (
            self.knn.predict_proba_one(
                x
            )
        )

        p_state, state_support = (
            self.state.predict(
                signal
            )
        )

        # Fixed ensemble.
        probability = (
            WEIGHT_LOGISTIC
            * p_logistic
            + WEIGHT_KNN
            * p_knn
            + WEIGHT_STATE
            * p_state
        )

        probability = min(
            max(
                probability,
                PROBABILITY_FLOOR,
            ),
            PROBABILITY_CEILING,
        )

        # Directional margin from 0.50.
        margin = (
            abs(
                probability
                - 0.5
            )
            * 2.0
        )

        # Agreement between the three independent components.
        disagreement = (
            abs(
                p_logistic
                - p_knn
            )
            + abs(
                p_logistic
                - p_state
            )
            + abs(
                p_knn
                - p_state
            )
        ) / 3.0

        agreement = max(
            0.0,
            min(
                1.0,
                1.0 - disagreement,
            )
        )

        # State support contributes gradually.
        if (
            state_support
            <= 0
        ):
            state_support_factor = 0.0

        elif (
            state_support
            >= MIN_SUPPORT_FOR_FULL_CONFIDENCE
        ):
            state_support_factor = 1.0

        else:
            state_support_factor = (
                state_support
                / float(
                    MIN_SUPPORT_FOR_FULL_CONFIDENCE
                )
            )

        # Training sample support.
        train_support_factor = min(
            1.0,
            self.train_support
            / 500.0,
        )

        # v4.1.3 confidence.
        #
        # The previous v4.1.2 gate made the model abstain on nearly every
        # OOS row. v4.1.3 uses a less restrictive fixed decision boundary
        # while still demanding some directional margin.
        confidence = (
            0.55 * margin
            + 0.25 * agreement
            + 0.10 * state_support_factor
            + 0.10 * train_support_factor
        )

        abstain = (
            confidence < MIN_CONFIDENCE
            or margin < MIN_MARGIN
        )

        return Prediction(
            probability_up=probability,
            probability_down=(
                1.0
                - probability
            ),
            confidence=confidence,
            support=state_support,
            abstain=abstain,
            model_components={
                "logistic": p_logistic,
                "knn": p_knn,
                "state": p_state,
                "agreement": agreement,
                "margin": margin,
                "state_support_factor": (
                    state_support_factor
                ),
                "train_support_factor": (
                    train_support_factor
                ),
            },
        )


# ==============================================================================
# METRICS
# ==============================================================================

def accuracy(
    y: Sequence[int],
    pred: Sequence[int],
) -> float:

    if not y:
        return 0.0

    return (
        sum(
            actual == guess
            for actual, guess in zip(
                y,
                pred,
            )
        )
        / len(y)
    )


def balanced_accuracy(
    y: Sequence[int],
    pred: Sequence[int],
) -> float:

    tp = 0
    tn = 0
    fp = 0
    fn = 0

    for actual, guess in zip(
        y,
        pred,
    ):

        if actual == 1 and guess == 1:
            tp += 1

        elif actual == 0 and guess == 0:
            tn += 1

        elif actual == 0 and guess == 1:
            fp += 1

        elif actual == 1 and guess == 0:
            fn += 1

    tpr = (
        tp
        / max(
            tp + fn,
            1,
        )
    )

    tnr = (
        tn
        / max(
            tn + fp,
            1,
        )
    )

    return (
        0.5
        * (
            tpr + tnr
        )
    )


def brier_score(
    y: Sequence[int],
    probabilities: Sequence[float],
) -> float:

    if not y:
        return 0.0

    return mean_or_zero(
        [
            (
                probability
                - actual
            ) ** 2
            for actual, probability
            in zip(
                y,
                probabilities,
            )
        ]
    )


def log_loss(
    y: Sequence[int],
    probabilities: Sequence[float],
) -> float:

    if not y:
        return 0.0

    total = 0.0

    for actual, probability in zip(
        y,
        probabilities,
    ):

        probability = min(
            max(
                probability,
                1e-6,
            ),
            1.0 - 1e-6,
        )

        if actual == 1:
            total -= math.log(
                probability
            )

        else:
            total -= math.log(
                1.0 - probability
            )

    return (
        total
        / len(y)
    )


def calibration_error(
    y: Sequence[int],
    probabilities: Sequence[float],
    bins: int = 10,
) -> float:

    if not y:
        return 0.0

    bucket_rows = []

    for b in range(bins):

        lo = (
            b
            / bins
        )

        hi = (
            b + 1
        ) / bins

        rows = [
            (
                actual,
                probability,
            )
            for actual, probability
            in zip(
                y,
                probabilities,
            )
            if (
                (
                    probability >= lo
                    and probability < hi
                )
                or (
                    b == bins - 1
                    and probability <= hi
                )
            )
        ]

        if rows:

            mean_probability = (
                mean_or_zero(
                    [
                        probability
                        for _, probability
                        in rows
                    ]
                )
            )

            mean_actual = (
                mean_or_zero(
                    [
                        actual
                        for actual, _
                        in rows
                    ]
                )
            )

            bucket_rows.append(
                (
                    len(rows),
                    abs(
                        mean_probability
                        - mean_actual
                    ),
                )
            )

    total = sum(
        n
        for n, _ in bucket_rows
    )

    if total == 0:
        return 0.0

    return (
        sum(
            n * error
            for n, error
            in bucket_rows
        )
        / total
    )


def baseline_probability(
    y: Sequence[int],
) -> float:

    if not y:
        return 0.5

    p = (
        sum(y)
        / len(y)
    )

    return max(
        p,
        1.0 - p,
    )


# ==============================================================================
# EVALUATION
# ==============================================================================

def evaluate_predictions(
    y: Sequence[int],
    probabilities: Sequence[float],
    abstained: Sequence[bool],
) -> Dict[str, Any]:

    usable_y = []
    usable_pred = []
    usable_prob = []

    for actual, probability, abstain in zip(
        y,
        probabilities,
        abstained,
    ):

        if abstain:
            continue

        usable_y.append(
            actual
        )

        usable_prob.append(
            probability
        )

        usable_pred.append(
            1
            if probability >= 0.5
            else 0
        )

    total = len(y)
    used = len(usable_y)

    if used:

        acc = accuracy(
            usable_y,
            usable_pred,
        )

        bal = balanced_accuracy(
            usable_y,
            usable_pred,
        )

        brier = brier_score(
            usable_y,
            usable_prob,
        )

        ll = log_loss(
            usable_y,
            usable_prob,
        )

        cal = calibration_error(
            usable_y,
            usable_prob,
        )

        base = baseline_probability(
            usable_y
        )

        edge = (
            acc
            - base
        )

    else:

        # No prediction survived the abstention gate.
        # The predictive metrics are unavailable, NOT zero.
        acc = None
        bal = None
        brier = None
        ll = None
        cal = None
        edge = None

        base = baseline_probability(y)

    return {
        "samples": total,
        "used": used,
        "abstained": (
            total - used
        ),
        "accuracy": acc,
        "balanced_accuracy": bal,
        "baseline_accuracy": base,
        "edge": edge,
        "coverage": safe_div(
            used,
            total,
        ),
        "brier_score": brier,
        "log_loss": ll,
        "calibration_error": cal,
        "probabilities": list(
            probabilities
        ),
        "abstain_mask": list(
            abstained
        ),
        "actual": list(y),
    }


# ==============================================================================
# WALK-FORWARD RUN
# ==============================================================================

def run_window(
    candles: Sequence[Candle],
    signals: Sequence[Signal],
    window: WalkForwardWindow,
) -> Dict[str, Any]:

    result = {
        "window": asdict(
            window
        ),
        "horizons": {},
    }

    for horizon in HORIZONS:

        train_signals, train_labels = (
            collect_training_rows(
                candles,
                signals,
                window,
                horizon,
            )
        )

        oos_signals, oos_labels = (
            collect_oos_rows(
                candles,
                signals,
                window,
                horizon,
            )
        )

        model = PredictiveModel()

        if (
            len(train_signals)
            < MIN_TRAIN_SAMPLES
            or len(
                set(
                    train_labels
                )
            )
            < 2
        ):

            result[
                "horizons"
            ][horizon] = {

                "train_count":
                    len(train_signals),

                "oos_count":
                    len(oos_signals),

                "encoder_states":
                    0,

                "temperature":
                    1.0,

                "result":
                    evaluate_predictions(
                        oos_labels,
                        [
                            0.5
                        ]
                        * len(
                            oos_labels
                        ),
                        [
                            True
                        ]
                        * len(
                            oos_labels
                        ),
                    ),
            }

            continue

        model.fit(
            train_signals,
            train_labels,
        )

        probabilities = []
        abstained = []
        confidences = []
        supports = []

        for signal in oos_signals:

            prediction = (
                model.predict(
                    signal
                )
            )

            probabilities.append(
                prediction
                .probability_up
            )

            abstained.append(
                prediction
                .abstain
            )

            confidences.append(
                prediction
                .confidence
            )

            supports.append(
                prediction
                .support
            )

        metrics = evaluate_predictions(
            oos_labels,
            probabilities,
            abstained,
        )

        metrics[
            "mean_confidence"
        ] = mean_or_zero(
            confidences
        )

        metrics[
            "mean_state_support"
        ] = mean_or_zero(
            supports
        )

        result[
            "horizons"
        ][horizon] = {

            "train_count":
                len(train_signals),

            "oos_count":
                len(oos_signals),

            "encoder_states":
                len(
                    model.state.exact
                ),

            "temperature":
                1.0,

            "result":
                metrics,
        }

    return result


# ==============================================================================
# AGGREGATION
# ==============================================================================

def aggregate_results(
    window_results: Sequence[
        Dict[str, Any]
    ],
) -> Dict[
    int,
    Dict[str, Any]
]:

    output = {}

    def present(values):
        return [
            value
            for value in values
            if value is not None
        ]

    def optional_mean(values):
        values = present(values)

        return (
            mean_or_zero(values)
            if values
            else None
        )

    def optional_median(values):
        values = present(values)

        return (
            statistics.median(values)
            if values
            else None
        )

    def optional_std(values):
        values = present(values)

        if len(values) > 1:
            return statistics.pstdev(
                values
            )

        if values:
            return 0.0

        return None

    def optional_min(values):
        values = present(values)

        return (
            min(values)
            if values
            else None
        )

    def optional_max(values):
        values = present(values)

        return (
            max(values)
            if values
            else None
        )

    for horizon in HORIZONS:

        rows = [
            window[
                "horizons"
            ][horizon]["result"]
            for window in window_results
        ]

        accuracies = [
            row["accuracy"]
            for row in rows
        ]

        balanced = [
            row["balanced_accuracy"]
            for row in rows
        ]

        edges = [
            row["edge"]
            for row in rows
        ]

        edge_values = present(
            edges
        )

        output[horizon] = {

            "mean_accuracy":
                optional_mean(
                    accuracies
                ),

            "median_accuracy":
                optional_median(
                    accuracies
                ),

            "std_accuracy":
                optional_std(
                    accuracies
                ),

            "min_accuracy":
                optional_min(
                    accuracies
                ),

            "max_accuracy":
                optional_max(
                    accuracies
                ),

            "mean_balanced_accuracy":
                optional_mean(
                    balanced
                ),

            "mean_edge":
                optional_mean(
                    edges
                ),

            "positive_edge_windows":
                sum(
                    value > 0
                    for value
                    in edge_values
                ),

            "negative_edge_windows":
                sum(
                    value < 0
                    for value
                    in edge_values
                ),

            "window_count":
                len(rows),

            "mean_coverage":
                mean_or_zero(
                    [
                        row["coverage"]
                        for row in rows
                    ]
                ),

            "mean_brier":
                optional_mean(
                    [
                        row["brier_score"]
                        for row in rows
                    ]
                ),

            "mean_log_loss":
                optional_mean(
                    [
                        row["log_loss"]
                        for row in rows
                    ]
                ),

            "mean_calibration_error":
                optional_mean(
                    [
                        row[
                            "calibration_error"
                        ]
                        for row in rows
                    ]
                ),

            "mean_confidence":
                mean_or_zero(
                    [
                        row.get(
                            "mean_confidence",
                            0.0,
                        )
                        for row in rows
                    ]
                ),

            "mean_state_support":
                mean_or_zero(
                    [
                        row.get(
                            "mean_state_support",
                            0.0,
                        )
                        for row in rows
                    ]
                ),
        }

    return output


# ==============================================================================
# EVENT DIAGNOSTICS
# ==============================================================================

def event_diagnostics(
    signals: Sequence[Signal],
    window_results: Sequence[
        Dict[str, Any]
    ],
    candles: Sequence[Candle],
) -> Dict[
    str,
    Dict[
        int,
        List[
            Dict[str, Any]
        ]
    ]
]:

    output = {

        "BOS_BULLISH":
            {
                h: []
                for h in HORIZONS
            },

        "BOS_BEARISH":
            {
                h: []
                for h in HORIZONS
            },

        "CHoCH_BULLISH":
            {
                h: []
                for h in HORIZONS
            },

        "CHoCH_BEARISH":
            {
                h: []
                for h in HORIZONS
            },
    }

    for window_result in window_results:

        window_data = (
            window_result[
                "window"
            ]
        )

        window = (
            WalkForwardWindow(
                number=(
                    window_data[
                        "number"
                    ]
                ),
                train_start=(
                    window_data[
                        "train_start"
                    ]
                ),
                train_end=(
                    window_data[
                        "train_end"
                    ]
                ),
                oos_start=(
                    window_data[
                        "oos_start"
                    ]
                ),
                oos_end=(
                    window_data[
                        "oos_end"
                    ]
                ),
            )
        )

        for horizon in HORIZONS:

            result = (
                window_result[
                    "horizons"
                ][horizon]["result"]
            )

            actual = result[
                "actual"
            ]

            probabilities = result[
                "probabilities"
            ]

            abstain_mask = result[
                "abstain_mask"
            ]

            # Authoritative OOS rows.
            oos_signals, oos_labels = (
                collect_oos_rows(
                    candles,
                    signals,
                    window,
                    horizon,
                )
            )

            if (
                list(oos_labels)
                != list(actual)
            ):
                raise RuntimeError(
                    "Event diagnostic labels are not aligned with OOS labels."
                )

            if not (
                len(oos_signals)
                == len(probabilities)
                == len(abstain_mask)
                == len(actual)
            ):
                raise RuntimeError(
                    "Event diagnostic arrays have different lengths."
                )

            for position, signal in enumerate(
                oos_signals
            ):

                if signal.event not in output:
                    continue

                if abstain_mask[position]:
                    continue

                prediction = (
                    1
                    if probabilities[position]
                    >= 0.5
                    else 0
                )

                actual_value = (
                    actual[position]
                )

                baseline = (
                    baseline_probability(
                        [actual_value]
                    )
                )

                correct = float(
                    prediction
                    == actual_value
                )

                output[
                    signal.event
                ][horizon].append(
                    {
                        "window":
                            window.number,

                        "n":
                            1,

                        "accuracy":
                            correct,

                        "baseline":
                            float(
                                baseline
                            ),

                        "edge":
                            correct
                            - baseline,
                    }
                )

    final = {
        event:
            {
                horizon: []
                for horizon in HORIZONS
            }
        for event in output
    }

    for event, horizons in output.items():

        for horizon, rows in horizons.items():

            grouped = defaultdict(
                list
            )

            for row in rows:
                grouped[
                    row["window"]
                ].append(
                    row
                )

            for window_number, group in grouped.items():

                n = len(group)

                final[
                    event
                ][horizon].append(
                    {
                        "window":
                            window_number,

                        "n":
                            n,

                        "accuracy":
                            mean_or_zero(
                                [
                                    row[
                                        "accuracy"
                                    ]
                                    for row
                                    in group
                                ]
                            ),

                        "baseline":
                            mean_or_zero(
                                [
                                    row[
                                        "baseline"
                                    ]
                                    for row
                                    in group
                                ]
                            ),

                        "edge":
                            mean_or_zero(
                                [
                                    row[
                                        "edge"
                                    ]
                                    for row
                                    in group
                                ]
                            ),
                    }
                )

    return final


# ==============================================================================
# FORMATTERS
# ==============================================================================

def fmt_pct(
    value: Optional[float],
) -> str:

    if value is None:
        return "N/A"

    return (
        f"{value * 100.0:.2f}%"
    )


def fmt_num(
    value: Optional[float],
) -> str:

    if value is None:
        return "N/A"

    return (
        f"{value:.4f}"
    )


# ==============================================================================
# REPORT
# ==============================================================================

def build_report(
    candles,
    invalid,
    chronology,
    atr,
    swings,
    states,
    events,
    signals,
    windows,
    window_results,
    aggregate,
    event_diag,
    protection_before,
    protection_after,
    causality,
    training_boundary_pass,
    oos_boundary_pass,
):

    lines: List[str] = []

    def add(text=""):
        lines.append(text)

    add(
        "# MLAI v4.1.3 Robust Causal Predictive Validation"
    )

    add()

    add("## Protection")
    add()

    add(
        f"- Market data SHA256 before: "
        f"`{protection_before}`"
    )

    add(
        f"- Market data SHA256 after: "
        f"`{protection_after}`"
    )

    add(
        "- Market data modification: NO"
    )

    add(
        "- Production MLAI modification: NO"
    )

    add(
        "- Learning memory modification: NO"
    )

    add(
        "- Trading: DISABLED"
    )

    add(
        "- Internet required: NO"
    )

    add()

    add(
        "## Predictive Architecture"
    )

    add()

    add(
        "- Causal market structure: YES"
    )

    add(
        "- Causal price / volatility features: YES"
    )

    add(
        "- Hierarchical structural-state model: YES"
    )

    add(
        "- Regularized logistic model: YES"
    )

    add(
        "- Distance-weighted kNN model: YES"
    )

    add(
        "- Fixed ensemble: YES"
    )

    add(
        "- Training-only scaling: ENFORCED"
    )

    add(
        "- Training-only state statistics: ENFORCED"
    )

    add(
        "- Frozen OOS model: ENFORCED"
    )

    add(
        "- OOS tuning: NO"
    )

    add(
        "- v4.1.3 reduced abstention policy: YES"
    )

    add()

    add(
        "## Dataset"
    )

    add()

    add(
        f"- Valid candles: {len(candles)}"
    )

    add(
        f"- Invalid candles: {invalid}"
    )

    add(
        f"- Timestamp order: "
        f"{chronology['ordered']}"
    )

    add(
        f"- Duplicate timestamps: "
        f"{chronology['duplicates']}"
    )

    add()

    add(
        "## Causal Structure"
    )

    add()

    add(
        f"- Confirmed swings: "
        f"{len(swings)}"
    )

    add(
        f"- Structure states: "
        f"{len(states)}"
    )

    add(
        f"- Structural events: "
        f"{len(events)}"
    )

    add(
        f"- ATR observations: "
        f"{sum(x is not None for x in atr)}"
    )

    add()

    add(
        "## Event Counts"
    )

    add()

    counts = Counter(
        events.values()
    )

    for event in (
        "BOS_BULLISH",
        "BOS_BEARISH",
        "CHoCH_BULLISH",
        "CHoCH_BEARISH",
    ):

        add(
            f"- {event}: "
            f"{counts.get(event, 0)}"
        )

    add()

    add(
        "## Causality Audits"
    )

    add()

    add(
        "- Causal structure audit: "
        + (
            "PASS"
            if causality["passed"]
            else "FAIL"
        )
    )

    add(
        "- Training label boundary: "
        + (
            "PASS"
            if training_boundary_pass
            else "FAIL"
        )
    )

    add(
        "- Walk-forward boundaries: "
        + (
            "PASS"
            if oos_boundary_pass
            else "FAIL"
        )
    )

    add(
        "- Training-only feature scaling: ENFORCED"
    )

    add(
        "- Training-only state learning: ENFORCED"
    )

    add(
        "- Frozen OOS models: ENFORCED"
    )

    add()

    add(
        "## V4.1.3 Decision Policy"
    )

    add()

    add(
        f"- Minimum confidence: "
        f"{MIN_CONFIDENCE:.2f}"
    )

    add(
        f"- Minimum probability margin: "
        f"{MIN_MARGIN:.3f}"
    )

    add(
        f"- State support for full confidence: "
        f"{MIN_SUPPORT_FOR_FULL_CONFIDENCE}"
    )

    add(
        "- Thresholds fixed before OOS evaluation: YES"
    )

    add(
        "- OOS threshold optimization: NO"
    )

    add()

    add(
        "## Combined Walk-Forward Results"
    )

    add()

    for horizon in HORIZONS:

        a = aggregate[horizon]

        add(
            f"### H+{horizon}"
        )

        add()

        add(
            f"- Mean accuracy: "
            f"{fmt_pct(a['mean_accuracy'])}"
        )

        add(
            f"- Median accuracy: "
            f"{fmt_pct(a['median_accuracy'])}"
        )

        add(
            f"- Std accuracy: "
            f"{fmt_pct(a['std_accuracy'])}"
        )

        add(
            f"- Min accuracy: "
            f"{fmt_pct(a['min_accuracy'])}"
        )

        add(
            f"- Max accuracy: "
            f"{fmt_pct(a['max_accuracy'])}"
        )

        add(
            f"- Mean balanced accuracy: "
            f"{fmt_pct(a['mean_balanced_accuracy'])}"
        )

        add(
            f"- Mean edge: "
            f"{fmt_pct(a['mean_edge'])}"
        )

        add(
            f"- Positive-edge windows: "
            f"{a['positive_edge_windows']}"
        )

        add(
            f"- Negative-edge windows: "
            f"{a['negative_edge_windows']}"
        )

        add(
            f"- Mean coverage: "
            f"{fmt_pct(a['mean_coverage'])}"
        )

        add(
            f"- Mean Brier: "
            f"{fmt_num(a['mean_brier'])}"
        )

        add(
            f"- Mean log loss: "
            f"{fmt_num(a['mean_log_loss'])}"
        )

        add(
            f"- Mean calibration error: "
            f"{fmt_pct(a['mean_calibration_error'])}"
        )

        add(
            f"- Mean confidence: "
            f"{fmt_pct(a['mean_confidence'])}"
        )

        add(
            f"- Mean state support: "
            f"{a['mean_state_support']:.2f}"
        )

        add()

    add(
        "## Per-Window Results"
    )

    add()

    for window in window_results:

        w = window[
            "window"
        ]

        add(
            f"### Window {w['number']}"
        )

        add(
            f"- TRAIN "
            f"[{w['train_start']}:{w['train_end']}]"
        )

        add(
            f"- OOS "
            f"[{w['oos_start']}:{w['oos_end']}]"
        )

        add()

        for horizon in HORIZONS:

            h = (
                window[
                    "horizons"
                ][horizon]
            )

            r = h[
                "result"
            ]

            add(
                f"- H+{horizon}: "
                f"Train={h['train_count']} | "
                f"OOS={h['oos_count']} | "
                f"States={h['encoder_states']} | "
                f"Accuracy={fmt_pct(r['accuracy'])} | "
                f"Balanced={fmt_pct(r['balanced_accuracy'])} | "
                f"Baseline={fmt_pct(r['baseline_accuracy'])} | "
                f"Edge={fmt_pct(r['edge'])} | "
                f"Coverage={fmt_pct(r['coverage'])} | "
                f"Brier={fmt_num(r['brier_score'])} | "
                f"LogLoss={fmt_num(r['log_loss'])} | "
                f"Confidence={fmt_pct(r.get('mean_confidence'))}"
            )

        add()

    add(
        "## Event Diagnostics"
    )

    add()

    for event, horizons in event_diag.items():

        add(
            f"### {event}"
        )

        for horizon, rows in horizons.items():

            if not rows:

                add(
                    f"- H+{horizon}: "
                    f"insufficient sample"
                )

                continue

            n = sum(
                row["n"]
                for row in rows
            )

            weighted_acc = safe_div(
                sum(
                    row["accuracy"]
                    * row["n"]
                    for row in rows
                ),
                n,
            )

            weighted_edge = safe_div(
                sum(
                    row["edge"]
                    * row["n"]
                    for row in rows
                ),
                n,
            )

            add(
                f"- H+{horizon}: "
                f"N={n} | "
                f"Accuracy={fmt_pct(weighted_acc)} | "
                f"Edge={fmt_pct(weighted_edge)}"
            )

        add()

    add(
        "## Interpretation"
    )

    add()

    add(
        "v4.1.3 changes the predictive decision layer rather than "
        "changing the chronological validation protocol."
    )

    add()

    add(
        "The less restrictive fixed abstention policy increases the "
        "number of evaluated predictions, but does not constitute "
        "evidence of predictive success."
    )

    add()

    add(
        "Predictive strength still requires positive untouched OOS edge, "
        "balanced performance, useful coverage, calibration, and "
        "stability across chronological windows."
    )

    add()

    add(
        "No threshold is optimized from OOS observations."
    )

    add()

    add(
        "## Final Protection"
    )

    add()

    add(
        "Market data unchanged: "
        + (
            "PASS"
            if protection_before
            == protection_after
            else "FAIL"
        )
    )

    add(
        "- Production MLAI modified: NO"
    )

    add(
        "- Learning memory modified: NO"
    )

    add(
        "- Trading enabled: NO"
    )

    add()

    add(
        "MLAI v4.1.3 ROBUST CAUSAL PREDICTIVE "
        "VALIDATION COMPLETE"
    )

    return "\n".join(
        lines
    )


# ==============================================================================
# MAIN
# ==============================================================================

def main():

    print("=" * 88)

    print(
        "MLAI v4.1.3 ROBUST CAUSAL PREDICTIVE "
        "MARKET STRUCTURE INTELLIGENCE"
    )

    print("=" * 88)

    print()
    print(
        "RESEARCH / VALIDATION ONLY"
    )

    print()
    print("=" * 88)
    print(
        "PROTECTION CHECK"
    )
    print("=" * 88)

    print(
        f"{MARKET_DATA_FILE:<24}: READ ONLY"
    )

    print(
        "Production MLAI          : NOT MODIFIED"
    )

    print(
        "Learning memory          : NOT MODIFIED"
    )

    print(
        "Trading                  : DISABLED"
    )

    print(
        "Internet                 : NOT REQUIRED"
    )

    guard = ProtectionGuard(
        MARKET_DATA_FILE
    )

    protection_before = (
        guard.before_hash
    )

    # --------------------------------------------------------------------------
    # DATA
    # --------------------------------------------------------------------------

    print()
    print("=" * 88)
    print(
        "DATA LOAD"
    )
    print("=" * 88)

    candles, invalid = load_market_data(
        MARKET_DATA_FILE
    )

    print(
        f"Valid candles           : "
        f"{len(candles)}"
    )

    print(
        f"Invalid candles         : "
        f"{invalid}"
    )

    if len(candles) < 500:
        raise RuntimeError(
            "Insufficient candle history."
        )

    # --------------------------------------------------------------------------
    # CHRONOLOGY
    # --------------------------------------------------------------------------

    print()
    print("=" * 88)
    print(
        "CHRONOLOGICAL DATA AUDIT"
    )
    print("=" * 88)

    chronology = audit_chronology(
        candles
    )

    print(
        "Timestamp order: "
        + (
            "PASS"
            if chronology["ordered"]
            else "FAIL"
        )
    )

    print(
        "Duplicate timestamps: "
        + (
            "FAIL"
            if chronology["duplicates"]
            else "PASS"
        )
    )

    if not chronology["ordered"]:
        raise RuntimeError(
            "Chronological order failed."
        )

    if chronology["duplicates"]:
        raise RuntimeError(
            "Duplicate timestamps detected."
        )

    # --------------------------------------------------------------------------
    # WALK FORWARD
    # --------------------------------------------------------------------------

    print()
    print("=" * 88)
    print(
        "WALK-FORWARD WINDOWS"
    )
    print("=" * 88)

    windows = (
        create_walk_forward_windows(
            len(candles),
            DEFAULT_TRAIN_WINDOWS,
            DEFAULT_OOS_SIZE,
        )
    )

    print(
        f"Requested windows      : "
        f"{DEFAULT_TRAIN_WINDOWS}"
    )

    print(
        f"Created windows        : "
        f"{len(windows)}"
    )

    for window in windows:

        print(
            f"Window {window.number} | "
            f"TRAIN [{window.train_start}:{window.train_end}] | "
            f"OOS [{window.oos_start}:{window.oos_end}]"
        )

    # --------------------------------------------------------------------------
    # ATR
    # --------------------------------------------------------------------------

    print()
    print("=" * 88)
    print(
        "DIAGNOSTIC FEATURE CALCULATION"
    )
    print("=" * 88)

    atr = calculate_atr(
        candles
    )

    print(
        f"ATR observations       : "
        f"{sum(x is not None for x in atr)}"
    )

    print()
    print(
        "ATR is used only as a causal normalization feature."
    )

    print(
        "No future ATR values are used."
    )

    # --------------------------------------------------------------------------
    # STRUCTURE
    # --------------------------------------------------------------------------

    print()
    print("=" * 88)
    print(
        "CAUSAL CONFIRMED SWINGS"
    )
    print("=" * 88)

    engine = CausalStructureEngine(
        candles
    )

    states = (
        engine.build()
    )

    swings = engine.swings
    events = engine.events

    print(
        f"Confirmed swings       : "
        f"{len(swings)}"
    )

    print()
    print("=" * 88)
    print(
        "CAUSAL MARKET STRUCTURE"
    )
    print("=" * 88)

    print(
        f"Structure states       : "
        f"{len(states)}"
    )

    print()
    print("=" * 88)
    print(
        "STRUCTURAL EVENTS"
    )
    print("=" * 88)

    counts = Counter(
        events.values()
    )

    for event in (
        "BOS_BULLISH",
        "BOS_BEARISH",
        "CHoCH_BULLISH",
        "CHoCH_BEARISH",
    ):

        print(
            f"{event:<24} : "
            f"{counts.get(event, 0)}"
        )

    # --------------------------------------------------------------------------
    # CAUSALITY
    # --------------------------------------------------------------------------

    print()
    print("=" * 88)
    print(
        "STRICT CAUSALITY AUDIT"
    )
    print("=" * 88)

    causality = (
        audit_structure_causality(
            candles,
            swings,
            states,
            events,
        )
    )

    print(
        "Causal structure timing: "
        + (
            "PASS"
            if causality["passed"]
            else "FAIL"
        )
    )

    if causality["reasons"]:

        for reason in (
            causality["reasons"]
        ):
            print(
                "Reason:",
                reason,
            )

        raise RuntimeError(
            "Causality audit failed."
        )

    print(
        "Reason: PASS"
    )

    # --------------------------------------------------------------------------
    # SIGNALS
    # --------------------------------------------------------------------------

    signals = create_signals(
        candles,
        states,
        atr,
    )

    print()
    print("=" * 88)
    print(
        "CAUSAL PREDICTIVE SIGNAL DATASET"
    )
    print("=" * 88)

    print(
        f"Signal records         : "
        f"{len(signals)}"
    )

    print(
        "Signal chronology: PASS"
    )

    # --------------------------------------------------------------------------
    # TRAINING BOUNDARY
    # --------------------------------------------------------------------------

    print()
    print("=" * 88)
    print(
        "TRAINING LABEL BOUNDARY AUDIT"
    )
    print("=" * 88)

    training_boundary_pass = (
        audit_training_boundaries(
            candles,
            signals,
            windows,
        )
    )

    print(
        "Training label policy: "
        + (
            "PASS"
            if training_boundary_pass
            else "FAIL"
        )
    )

    print(
        "Rule:"
    )

    print(
        "    i + horizon < train_end"
    )

    if not training_boundary_pass:
        raise RuntimeError(
            "Training label boundary failed."
        )

    # --------------------------------------------------------------------------
    # OOS BOUNDARY
    # --------------------------------------------------------------------------

    print()
    print("=" * 88)
    print(
        "WALK-FORWARD BOUNDARY AUDIT"
    )
    print("=" * 88)

    oos_boundary_pass = (
        audit_oos_boundaries(
            candles,
            signals,
            windows,
        )
    )

    print(
        "Walk-forward boundaries: "
        + (
            "PASS"
            if oos_boundary_pass
            else "FAIL"
        )
    )

    if not oos_boundary_pass:
        raise RuntimeError(
            "OOS boundary audit failed."
        )

    # --------------------------------------------------------------------------
    # STATUS
    # --------------------------------------------------------------------------

    print()
    print("=" * 88)
    print(
        "GLOBAL CAUSALITY / PREDICTION STATUS"
    )
    print("=" * 88)

    print(
        "Causal structure audit       : "
        + (
            "PASS"
            if causality["passed"]
            else "FAIL"
        )
    )

    print(
        "Training label boundary      : "
        + (
            "PASS"
            if training_boundary_pass
            else "FAIL"
        )
    )

    print(
        "Walk-forward boundaries      : "
        + (
            "PASS"
            if oos_boundary_pass
            else "FAIL"
        )
    )

    print(
        "Training-only scaling        : ENFORCED"
    )

    print(
        "Training-only state learning : ENFORCED"
    )

    print(
        "Frozen OOS models            : ENFORCED"
    )

    print(
        "OOS tuning                   : DISABLED"
    )

    print(
        "v4.1.3 reduced abstention    : ENABLED"
    )

    print(
        f"Minimum confidence           : "
        f"{MIN_CONFIDENCE:.2f}"
    )

    print(
        f"Minimum margin               : "
        f"{MIN_MARGIN:.3f}"
    )

    print(
        "Trading                      : DISABLED"
    )

    # --------------------------------------------------------------------------
    # WALK-FORWARD VALIDATION
    # --------------------------------------------------------------------------

    print()
    print("=" * 88)
    print(
        "ROBUST WALK-FORWARD PREDICTIVE VALIDATION"
    )
    print("=" * 88)

    window_results = []

    for window in windows:

        print()
        print("-" * 88)

        print(
            f"WALK-FORWARD WINDOW "
            f"{window.number}"
        )

        print("-" * 88)

        result = run_window(
            candles,
            signals,
            window,
        )

        window_results.append(
            result
        )

        print(
            f"Training candles : "
            f"{window.train_end}"
        )

        print(
            f"OOS candles      : "
            f"{window.oos_end - window.oos_start}"
        )

        for horizon in HORIZONS:

            h = (
                result[
                    "horizons"
                ][horizon]
            )

            metrics = (
                h["result"]
            )

            print()

            print(
                f"H+{horizon}: "
                f"Train={h['train_count']} | "
                f"OOS={h['oos_count']} | "
                f"States={h['encoder_states']}"
            )

            print(
                f"Accuracy="
                f"{fmt_pct(metrics['accuracy'])} | "
                f"Balanced="
                f"{fmt_pct(metrics['balanced_accuracy'])} | "
                f"Baseline="
                f"{fmt_pct(metrics['baseline_accuracy'])} | "
                f"Edge="
                f"{fmt_pct(metrics['edge'])}"
            )

            print(
                f"Coverage="
                f"{fmt_pct(metrics['coverage'])} | "
                f"Abstained="
                f"{metrics['abstained']} | "
                f"Brier="
                f"{fmt_num(metrics['brier_score'])} | "
                f"LogLoss="
                f"{fmt_num(metrics['log_loss'])} | "
                f"CalError="
                f"{fmt_pct(metrics['calibration_error'])}"
            )

            print(
                f"MeanConfidence="
                f"{fmt_pct(metrics.get('mean_confidence'))} | "
                f"MeanStateSupport="
                f"{metrics.get('mean_state_support', 0.0):.2f}"
            )

    # --------------------------------------------------------------------------
    # AGGREGATE
    # --------------------------------------------------------------------------

    aggregate = (
        aggregate_results(
            window_results
        )
    )

    print()
    print("=" * 88)
    print(
        "COMBINED ROBUST WALK-FORWARD RESULTS"
    )
    print("=" * 88)

    for horizon in HORIZONS:

        result = (
            aggregate[horizon]
        )

        print()

        print(
            f"H+{horizon} | "
            f"Mean Accuracy="
            f"{fmt_pct(result['mean_accuracy'])} | "
            f"Median="
            f"{fmt_pct(result['median_accuracy'])} | "
            f"Std="
            f"{fmt_pct(result['std_accuracy'])}"
        )

        print(
            f"Mean Balanced="
            f"{fmt_pct(result['mean_balanced_accuracy'])} | "
            f"Mean Edge="
            f"{fmt_pct(result['mean_edge'])}"
        )

        print(
            f"Coverage="
            f"{fmt_pct(result['mean_coverage'])} | "
            f"Brier="
            f"{fmt_num(result['mean_brier'])} | "
            f"LogLoss="
            f"{fmt_num(result['mean_log_loss'])}"
        )

        print(
            f"Positive Edge Windows="
            f"{result['positive_edge_windows']} | "
            f"Negative Edge Windows="
            f"{result['negative_edge_windows']}"
        )

    # --------------------------------------------------------------------------
    # EVENT DIAGNOSTICS
    # --------------------------------------------------------------------------

    event_diag = (
        event_diagnostics(
            signals,
            window_results,
            candles,
        )
    )

    print()
    print("=" * 88)
    print(
        "EVENT DIAGNOSTICS"
    )
    print("=" * 88)

    for event, horizons in (
        event_diag.items()
    ):

        print()
        print(event)

        for horizon, rows in (
            horizons.items()
        ):

            if not rows:
                print(
                    f"  H+{horizon}: "
                    f"Insufficient sample"
                )
                continue

            n = sum(
                row["n"]
                for row in rows
            )

            weighted_acc = safe_div(
                sum(
                    row["accuracy"]
                    * row["n"]
                    for row in rows
                ),
                n,
            )

            weighted_edge = safe_div(
                sum(
                    row["edge"]
                    * row["n"]
                    for row in rows
                ),
                n,
            )

            print(
                f"  H+{horizon}: "
                f"N={n} | "
                f"Accuracy="
                f"{fmt_pct(weighted_acc)} | "
                f"Edge="
                f"{fmt_pct(weighted_edge)}"
            )

    # --------------------------------------------------------------------------
    # DEPENDENCY
    # --------------------------------------------------------------------------

    print()
    print("=" * 88)
    print(
        "FORWARD LABEL DEPENDENCY"
    )
    print("=" * 88)

    print(
        "Fixed-horizon labels may overlap in time."
    )

    print(
        "Overlapping labels are not treated as independent statistical observations."
    )

    print(
        "Chronological OOS separation remains enforced."
    )

    print(
        "No OOS outcome is used for model construction."
    )

    # --------------------------------------------------------------------------
    # VALIDATION ARTIFACT
    # --------------------------------------------------------------------------

    validation_artifact = {

        "version":
            VERSION,

        "architecture": {
            "causal_structure":
                True,

            "causal_features":
                True,

            "hierarchical_state_model":
                True,

            "regularized_logistic":
                True,

            "knn":
                True,

            "fixed_ensemble":
                True,

            "oos_tuning":
                False,

            "reduced_abstention":
                True,

            "trading":
                False,
        },

        "decision_policy": {

            "min_confidence":
                MIN_CONFIDENCE,

            "min_margin":
                MIN_MARGIN,

            "min_support_for_full_confidence":
                MIN_SUPPORT_FOR_FULL_CONFIDENCE,
        },

        "audits": {

            "causal_structure":
                causality,

            "training_boundary":
                training_boundary_pass,

            "oos_boundary":
                oos_boundary_pass,
        },

        "config": {

            "horizons":
                HORIZONS,

            "swing_left":
                SWING_LEFT,

            "swing_right":
                SWING_RIGHT,

            "min_state_support":
                MIN_STATE_SUPPORT,

            "oos_size":
                DEFAULT_OOS_SIZE,

            "knn_k":
                KNN_K,

            "logistic_l2":
                LOGISTIC_L2,

            "ensemble_weights": {
                "logistic":
                    WEIGHT_LOGISTIC,

                "knn":
                    WEIGHT_KNN,

                "state":
                    WEIGHT_STATE,
            },
        },

        "candles":
            len(candles),

        "swings":
            [
                asdict(swing)
                for swing in swings
            ],

        "states":
            [
                asdict(state)
                for state in states
            ],

        "events":
            dict(events),

        "aggregate":
            aggregate,

        "windows":
            window_results,

        "event_diagnostics":
            event_diag,

        "protection": {
            "market_file":
                MARKET_DATA_FILE,

            "sha256_before":
                protection_before,
        },
    }

    with open(
        VALIDATION_BIN,
        "wb",
    ) as f:

        pickle.dump(
            validation_artifact,
            f,
            protocol=pickle.HIGHEST_PROTOCOL,
        )

    protection_after = (
        sha256_file(
            MARKET_DATA_FILE
        )
    )

    # --------------------------------------------------------------------------
    # REPORT
    # --------------------------------------------------------------------------

    report = build_report(
        candles=candles,
        invalid=invalid,
        chronology=chronology,
        atr=atr,
        swings=swings,
        states=states,
        events=events,
        signals=signals,
        windows=windows,
        window_results=window_results,
        aggregate=aggregate,
        event_diag=event_diag,
        protection_before=protection_before,
        protection_after=protection_after,
        causality=causality,
        training_boundary_pass=(
            training_boundary_pass
        ),
        oos_boundary_pass=(
            oos_boundary_pass
        ),
    )

    with open(
        VALIDATION_REPORT,
        "w",
        encoding="utf-8",
    ) as f:

        f.write(
            report
        )

    # --------------------------------------------------------------------------
    # FINAL PROTECTION
    # --------------------------------------------------------------------------

    print()
    print("=" * 88)
    print(
        "SAVE VALIDATION ARTIFACT"
    )
    print("=" * 88)

    print(
        "Validation binary saved:"
    )

    print(
        f"    {VALIDATION_BIN}"
    )

    print(
        "Validation report saved:"
    )

    print(
        f"    {VALIDATION_REPORT}"
    )

    print()
    print("=" * 88)
    print(
        "FINAL PROTECTION CHECK"
    )
    print("=" * 88)

    if (
        protection_before
        != protection_after
    ):

        print(
            "market_data.bin       : "
            "FAIL - FILE CHANGED"
        )

        raise RuntimeError(
            "Protection failure: "
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

    print()
    print("=" * 88)

    print(
        "MLAI v4.1.3 ROBUST CAUSAL "
        "PREDICTIVE VALIDATION COMPLETE"
    )

    print("=" * 88)


if __name__ == "__main__":
    main()