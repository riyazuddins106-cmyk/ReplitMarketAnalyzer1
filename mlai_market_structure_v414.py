"""
MLAI v4.1.4 — CANONICAL MARKET LANGUAGE FOUNDATION
===================================================

Research / validation only.

Bridge release from v4.1.3 toward the Market Language Brain roadmap.

Adds:
- canonical causal MarketState
- causal regime representation
- causal sequence representation
- ATR-normalized future outcomes
- UP/DOWN/NEUTRAL outcome representation
- historical experience records
- causal conditional historical baselines
- v4.1.3 predictive benchmark retained
- strict chronological/OOS protection

No trading.
No live API.
No automatic knowledge promotion.
"""

from __future__ import annotations

import hashlib
import math
import os
import pickle

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple


# ==============================================================================
# CONFIGURATION
# ==============================================================================

VERSION = "4.1.4"

MARKET_DATA_FILE = "market_data.bin"

VALIDATION_BIN = (
    "MLAI_V414_MARKET_LANGUAGE_FOUNDATION.bin"
)

VALIDATION_REPORT = (
    "MLAI_V414_MARKET_LANGUAGE_FOUNDATION_REPORT.md"
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

WEIGHT_LOGISTIC = 0.55
WEIGHT_KNN = 0.25
WEIGHT_STATE = 0.20

MIN_CONFIDENCE = 0.45
MIN_MARGIN = 0.02
MIN_SUPPORT_FOR_FULL_CONFIDENCE = 20

EPS = 1e-12

# ATR-normalized target threshold.
# Values between -0.25 ATR and +0.25 ATR are treated as NEUTRAL.
NEUTRAL_ATR_BAND = 0.25


# ==============================================================================
# DATA TYPES
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
class WalkForwardWindow:
    number: int
    train_start: int
    train_end: int
    oos_start: int
    oos_end: int


@dataclass
class MarketState:
    index: int
    timestamp: Any
    instrument: str
    timeframe: str

    candle_direction: str
    body_ratio: float
    range_ratio: float

    sequence_state: str
    trend: str
    structure_event: str

    high_label: str
    low_label: str

    location: str

    volatility_regime: str
    volatility_ratio: float

    momentum_state: str
    regime: str

    state_key: Tuple[Any, ...]

    availability_index: int


@dataclass
class Outcome:
    direction: str
    raw_return: float
    atr_return: Optional[float]
    mfe_atr: Optional[float]
    mae_atr: Optional[float]


@dataclass
class ExperienceRecord:
    index: int
    state_key: Tuple[Any, ...]
    sequence_state: str
    regime: str
    structure_event: str
    horizon: int
    outcome: Outcome


@dataclass
class Prediction:
    probability_up: float
    probability_down: float
    confidence: float
    support: int
    abstain: bool
    model_components: Dict[str, float]


# ==============================================================================
# PROTECTION
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
        return self.before_hash == sha256_file(
            self.path
        )


# ==============================================================================
# MARKET DATA
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

    if isinstance(
        raw,
        (list, tuple),
    ) and len(raw) >= 5:

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
            "Unsupported market_data.bin format"
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
        else:
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
# WALK-FORWARD WINDOWS
# ==============================================================================

def create_walk_forward_windows(
    n: int,
    count: int,
    oos_size: int,
) -> List[WalkForwardWindow]:

    if n <= count * oos_size:
        raise ValueError(
            "Insufficient candles"
        )

    initial_train = (
        n
        - count * oos_size
    )

    output = []

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
            output.append(
                WalkForwardWindow(
                    number=i + 1,
                    train_start=0,
                    train_end=train_end,
                    oos_start=oos_start,
                    oos_end=oos_end,
                )
            )

    return output


# ==============================================================================
# MATH
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

    mean_value = mean_or_zero(values)

    variance = (
        sum(
            (x - mean_value) ** 2
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

    output: List[
        Optional[float]
    ] = [None] * len(candles)

    true_ranges: List[float] = []

    for i, candle in enumerate(candles):

        if i == 0:
            tr = (
                candle.high
                - candle.low
            )

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

        true_ranges.append(
            max(tr, EPS)
        )

        if len(true_ranges) >= period:
            output[i] = (
                sum(
                    true_ranges[-period:]
                )
                / period
            )

    return output


# ==============================================================================
# CAUSAL MARKET STRUCTURE
# ==============================================================================

class CausalStructureEngine:

    def __init__(
        self,
        candles: Sequence[Candle],
    ):
        self.candles = candles
        self.swings: List[Swing] = []
        self.events: Dict[int, str] = {}
        self.states: List[
            StructureState
        ] = []

        self.high_used = set()
        self.low_used = set()

    def _high(
        self,
        j: int,
    ) -> bool:

        if (
            j < SWING_LEFT
            or j + SWING_RIGHT
            >= len(self.candles)
        ):
            return False

        price = self.candles[j].high

        return all(
            (
                k == j
                or self.candles[k].high < price
            )
            for k in range(
                j - SWING_LEFT,
                j + SWING_RIGHT + 1,
            )
        )

    def _low(
        self,
        j: int,
    ) -> bool:

        if (
            j < SWING_LEFT
            or j + SWING_RIGHT
            >= len(self.candles)
        ):
            return False

        price = self.candles[j].low

        return all(
            (
                k == j
                or self.candles[k].low > price
            )
            for k in range(
                j - SWING_LEFT,
                j + SWING_RIGHT + 1,
            )
        )

    def build(
        self,
    ) -> List[StructureState]:

        last_high: Optional[Swing] = None
        last_low: Optional[Swing] = None

        high_label = "UNKNOWN"
        low_label = "UNKNOWN"

        trend = "NEUTRAL"

        event_index: Optional[int] = None

        structure_start = 0

        for i, candle in enumerate(
            self.candles
        ):

            pivot_index = (
                i - SWING_RIGHT
            )

            if pivot_index >= SWING_LEFT:

                if self._high(
                    pivot_index
                ):

                    label = (
                        "HH"
                        if (
                            last_high is None
                            or self.candles[
                                pivot_index
                            ].high
                            > last_high.price
                        )
                        else "LH"
                    )

                    last_high = Swing(
                        pivot_index,
                        i,
                        "HIGH",
                        self.candles[
                            pivot_index
                        ].high,
                        label,
                    )

                    self.swings.append(
                        last_high
                    )

                    high_label = label

                if self._low(
                    pivot_index
                ):

                    label = (
                        "HL"
                        if (
                            last_low is None
                            or self.candles[
                                pivot_index
                            ].low
                            > last_low.price
                        )
                        else "LL"
                    )

                    last_low = Swing(
                        pivot_index,
                        i,
                        "LOW",
                        self.candles[
                            pivot_index
                        ].low,
                        label,
                    )

                    self.swings.append(
                        last_low
                    )

                    low_label = label

            event = "NONE"

            if (
                last_high is not None
                and i
                > last_high.confirmation_index
                and candle.close
                > last_high.price
                and (
                    last_high.pivot_index,
                    "H",
                ) not in self.high_used
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

                self.high_used.add(
                    (
                        last_high.pivot_index,
                        "H",
                    )
                )

                trend = "BULLISH"
                event_index = i
                structure_start = i

            if (
                last_low is not None
                and i
                > last_low.confirmation_index
                and candle.close
                < last_low.price
                and (
                    last_low.pivot_index,
                    "L",
                ) not in self.low_used
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

                self.low_used.add(
                    (
                        last_low.pivot_index,
                        "L",
                    )
                )

                trend = "BEARISH"
                event_index = i
                structure_start = i

            event_age = (
                None
                if event_index is None
                else i - event_index
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
                    event_index=event_index,
                    event_age=event_age,
                    structure_age=(
                        i - structure_start
                    ),
                )
            )

        return self.states


# ==============================================================================
# CAUSALITY AUDIT
# ==============================================================================

def audit_structure_causality(
    candles: Sequence[Candle],
    swings: Sequence[Swing],
    states: Sequence[StructureState],
    events: Dict[int, str],
) -> Dict[str, Any]:

    reasons = []

    lookup = {
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
                "early swing"
            )

    for state in states:

        if state.last_high_index is not None:

            swing = lookup.get(
                (
                    state.last_high_index,
                    "HIGH",
                )
            )

            if (
                swing is not None
                and swing.confirmation_index
                > state.index
            ):
                reasons.append(
                    f"future high {state.index}"
                )

        if state.last_low_index is not None:

            swing = lookup.get(
                (
                    state.last_low_index,
                    "LOW",
                )
            )

            if (
                swing is not None
                and swing.confirmation_index
                > state.index
            ):
                reasons.append(
                    f"future low {state.index}"
                )

        event = events.get(
            state.index,
            "NONE",
        )

        if (
            event != "NONE"
            and (
                state.event_index is None
                or state.event_index
                > state.index
            )
        ):
            reasons.append(
                f"future event {state.index}"
            )

    return {
        "passed": not reasons,
        "reasons": reasons,
    }


# ==============================================================================
# CAUSAL PRICE FEATURES
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
        candle.high
        for candle in candles[
            start : i + 1
        ]
    ]

    lows = [
        candle.low
        for candle in candles[
            start : i + 1
        ]
    ]

    if not highs:
        return 0.0

    return safe_div(
        max(highs) - min(lows),
        candles[i].close,
    )


# ==============================================================================
# REGIME
# ==============================================================================

def classify_regime(
    state: StructureState,
    volatility_ratio: float,
    return_8: float,
) -> str:

    if volatility_ratio >= 1.35:
        return "VOL_EXPANSION"

    if volatility_ratio <= 0.75:
        return "VOL_CONTRACTION"

    if (
        state.trend == "BULLISH"
        and return_8 > 0
    ):
        return "TRENDING_UP"

    if (
        state.trend == "BEARISH"
        and return_8 < 0
    ):
        return "TRENDING_DOWN"

    if state.trend == "NEUTRAL":
        return "RANGING"

    return "TRANSITION"


def classify_momentum(
    r1: float,
    r3: float,
    r8: float,
) -> str:

    if (
        r1 > 0
        and r3 > 0
        and r8 > 0
    ):
        return "BULLISH_ACCELERATION"

    if (
        r1 < 0
        and r3 < 0
        and r8 < 0
    ):
        return "BEARISH_ACCELERATION"

    if (
        r8 > 0
        and r1 < 0
    ):
        return "BULLISH_MOMENTUM_LOSS"

    if (
        r8 < 0
        and r1 > 0
    ):
        return "BEARISH_MOMENTUM_LOSS"

    return "MIXED"


# ==============================================================================
# SEQUENCE
# ==============================================================================

def update_sequence(
    history: Sequence[Candle],
    last_state: StructureState,
) -> str:

    if len(history) < 3:
        return "INITIAL"

    event = last_state.event

    if event in (
        "BOS_BULLISH",
        "CHoCH_BULLISH",
    ):
        return "BULLISH_BREAK"

    if event in (
        "BOS_BEARISH",
        "CHoCH_BEARISH",
    ):
        return "BEARISH_BREAK"

    if (
        history[-1].close
        > history[-2].close
        and history[-2].close
        <= history[-3].close
    ):
        return "BULLISH_RESPONSE"

    if (
        history[-1].close
        < history[-2].close
        and history[-2].close
        >= history[-3].close
    ):
        return "BEARISH_RESPONSE"

    recent_range = max(
        history[-1].high
        - history[-1].low,
        EPS,
    )

    recent_body = abs(
        history[-1].close
        - history[-1].open
    )

    if recent_body < 0.25 * recent_range:
        return "COMPRESSION"

    if last_state.trend == "BULLISH":
        return "RECOVERY_OR_CONTINUATION"

    if last_state.trend == "BEARISH":
        return "SELLING_OR_CONTINUATION"

    return "MIXED_SEQUENCE"


# ==============================================================================
# MARKET LANGUAGE STATE
# ==============================================================================

def build_market_states(
    candles: Sequence[Candle],
    states: Sequence[StructureState],
    atr: Sequence[Optional[float]],
    instrument: str = "XAUUSD",
    timeframe: str = "UNKNOWN",
) -> List[MarketState]:

    output = []

    for i, candle in enumerate(candles):

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

        r1 = rolling_return(
            candles,
            i,
            1,
        )

        r3 = rolling_return(
            candles,
            i,
            3,
        )

        r8 = rolling_return(
            candles,
            i,
            8,
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

        recent_volatility = (
            mean_or_zero(
                recent_ranges
            )
        )

        older_volatility = (
            mean_or_zero(
                older_ranges
            )
        )

        volatility_ratio = safe_div(
            recent_volatility,
            (
                older_volatility
                if older_volatility > EPS
                else recent_volatility + EPS
            ),
        )

        location = "UNKNOWN"

        if (
            state.last_low is not None
            and abs(
                candle.close
                - state.last_low
            ) <= a
        ):
            location = "NEAR_SUPPORT"

        elif (
            state.last_high is not None
            and abs(
                candle.close
                - state.last_high
            ) <= a
        ):
            location = "NEAR_RESISTANCE"

        else:
            location = "MID_STRUCTURE"

        sequence = update_sequence(
            candles[: i + 1],
            state,
        )

        regime = classify_regime(
            state,
            volatility_ratio,
            r8,
        )

        momentum = classify_momentum(
            r1,
            r3,
            r8,
        )

        candle_direction = (
            "UP"
            if candle.close > candle.open
            else "DOWN"
            if candle.close < candle.open
            else "FLAT"
        )

        state_key = (
            state.trend,
            state.event,
            location,
            regime,
            momentum,
            sequence,
        )

        output.append(
            MarketState(
                index=i,
                timestamp=candle.timestamp,
                instrument=instrument,
                timeframe=timeframe,
                candle_direction=candle_direction,
                body_ratio=safe_div(
                    abs(
                        candle.close
                        - candle.open
                    ),
                    a,
                ),
                range_ratio=safe_div(
                    candle.high
                    - candle.low,
                    a,
                ),
                sequence_state=sequence,
                trend=state.trend,
                structure_event=state.event,
                high_label=state.high_label,
                low_label=state.low_label,
                location=location,
                volatility_regime=regime,
                volatility_ratio=volatility_ratio,
                momentum_state=momentum,
                regime=regime,
                state_key=state_key,
                availability_index=i,
            )
        )

    return output


# ==============================================================================
# OUTCOME
# ==============================================================================

def make_binary_label(
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

    if (
        candles[target].close
        > candles[index].close
    ):
        return 1

    if (
        candles[target].close
        < candles[index].close
    ):
        return 0

    return None


def make_outcome(
    candles: Sequence[Candle],
    atr: Sequence[Optional[float]],
    index: int,
    horizon: int,
) -> Optional[Outcome]:

    target = (
        index
        + horizon
    )

    if target >= len(candles):
        return None

    base_price = (
        candles[index].close
    )

    current_atr = atr[index]

    if (
        current_atr is None
        or current_atr <= EPS
    ):
        return None

    raw_return = safe_div(
        candles[target].close
        - base_price,
        base_price,
    )

    atr_return = safe_div(
        candles[target].close
        - base_price,
        current_atr,
    )

    if atr_return > NEUTRAL_ATR_BAND:
        direction = "UP"

    elif atr_return < -NEUTRAL_ATR_BAND:
        direction = "DOWN"

    else:
        direction = "NEUTRAL"

    future_high = max(
        candle.high
        for candle in candles[
            index + 1 : target + 1
        ]
    )

    future_low = min(
        candle.low
        for candle in candles[
            index + 1 : target + 1
        ]
    )

    mfe_atr = safe_div(
        future_high
        - base_price,
        current_atr,
    )

    mae_atr = safe_div(
        future_low
        - base_price,
        current_atr,
    )

    return Outcome(
        direction=direction,
        raw_return=raw_return,
        atr_return=atr_return,
        mfe_atr=mfe_atr,
        mae_atr=mae_atr,
    )


# ==============================================================================
# EXPERIENCE MEMORY
# ==============================================================================

def build_experience_records(
    candles: Sequence[Candle],
    atr: Sequence[Optional[float]],
    states: Sequence[StructureState],
    market_states: Sequence[MarketState],
    start: int,
    end: int,
    horizon: int,
) -> List[ExperienceRecord]:

    records = []

    for i in range(
        start,
        end,
    ):

        outcome = make_outcome(
            candles,
            atr,
            i,
            horizon,
        )

        if outcome is None:
            continue

        state = market_states[i]

        records.append(
            ExperienceRecord(
                index=i,
                state_key=state.state_key,
                sequence_state=state.sequence_state,
                regime=state.regime,
                structure_event=state.structure_event,
                horizon=horizon,
                outcome=outcome,
            )
        )

    return records


# ==============================================================================
# HISTORICAL CONDITIONAL BASELINE
# ==============================================================================

def historical_conditional_baseline(
    records: Sequence[ExperienceRecord],
    current: MarketState,
) -> Dict[str, Any]:

    rows = [
        record
        for record in records
        if record.state_key
        == current.state_key
    ]

    level = "EXACT"

    if len(rows) < MIN_STATE_SUPPORT:

        rows = [
            record
            for record in records
            if (
                record.regime
                == current.regime
                and record.structure_event
                == current.structure_event
            )
        ]

        level = "REGIME+EVENT"

    if len(rows) < MIN_STATE_SUPPORT:

        rows = [
            record
            for record in records
            if record.regime
            == current.regime
        ]

        level = "REGIME"

    if not rows:

        rows = list(records)
        level = "GLOBAL"

    counts = Counter(
        record.outcome.direction
        for record in rows
    )

    total = len(rows)

    return {
        "level": level,
        "samples": total,
        "UP": safe_div(
            counts["UP"],
            total,
        ),
        "DOWN": safe_div(
            counts["DOWN"],
            total,
        ),
        "NEUTRAL": safe_div(
            counts["NEUTRAL"],
            total,
        ),
    }


# ==============================================================================
# BENCHMARK FEATURE ENGINE
# ==============================================================================

def create_benchmark_signals(
    candles: Sequence[Candle],
    states: Sequence[StructureState],
    atr: Sequence[Optional[float]],
) -> List[Signal]:

    signals = []

    for i, candle in enumerate(
        candles
    ):

        state = states[i]

        current_atr = (
            atr[i]
            if atr[i] is not None
            else max(
                candle.high
                - candle.low,
                EPS,
            )
        )

        r1 = rolling_return(
            candles,
            i,
            1,
        )

        r3 = rolling_return(
            candles,
            i,
            3,
        )

        r8 = rolling_return(
            candles,
            i,
            8,
        )

        r16 = rolling_return(
            candles,
            i,
            16,
        )

        r32 = rolling_return(
            candles,
            i,
            32,
        )

        range4 = rolling_range(
            candles,
            i,
            4,
        )

        range8 = rolling_range(
            candles,
            i,
            8,
        )

        range16 = rolling_range(
            candles,
            i,
            16,
        )

        feature = (
            r1,
            r3,
            r8,
            r16,
            r32,
            range4,
            range8,
            range16,

            safe_div(
                abs(
                    candle.close
                    - candle.open
                ),
                current_atr,
            ),

            safe_div(
                candle.high
                - candle.low,
                current_atr,
            ),

            safe_div(
                candle.high
                - max(
                    candle.open,
                    candle.close,
                ),
                current_atr,
            ),

            safe_div(
                min(
                    candle.open,
                    candle.close,
                )
                - candle.low,
                current_atr,
            ),

            (
                safe_div(
                    candle.close
                    - state.last_high,
                    current_atr,
                )
                if state.last_high
                is not None
                else 0.0
            ),

            (
                safe_div(
                    candle.close
                    - state.last_low,
                    current_atr,
                )
                if state.last_low
                is not None
                else 0.0
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
                state.event_age
                if state.event_age is not None
                else 999,
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
# STRICT TRAINING / OOS ROW COLLECTION
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

        if (
            signal.index
            + horizon
            >= window.train_end
        ):
            continue

        label = make_binary_label(
            candles,
            signal.index,
            horizon,
        )

        if label is None:
            continue

        rows.append(signal)
        labels.append(label)

    return rows, labels


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

        if (
            signal.index
            + horizon
            >= len(candles)
        ):
            continue

        label = make_binary_label(
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

                if (
                    signal.index
                    + horizon
                    >= window.train_end
                ):
                    continue

                if (
                    make_binary_label(
                        candles,
                        signal.index,
                        horizon,
                    )
                    is None
                ):
                    continue

                expected_signals.append(
                    signal
                )

            if [
                signal.index
                for signal in actual_signals
            ] != [
                signal.index
                for signal in expected_signals
            ]:
                return False

            if (
                len(actual_signals)
                != len(actual_labels)
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

                if (
                    signal.index
                    + horizon
                    >= len(candles)
                ):
                    continue

                if (
                    make_binary_label(
                        candles,
                        signal.index,
                        horizon,
                    )
                    is None
                ):
                    continue

                expected_signals.append(
                    signal
                )

            if [
                signal.index
                for signal in actual_signals
            ] != [
                signal.index
                for signal in expected_signals
            ]:
                return False

            if (
                len(actual_signals)
                != len(actual_labels)
            ):
                return False

    return True


# ==============================================================================
# STANDARDIZER
# ==============================================================================

class Standardizer:

    def __init__(self):
        self.means = []
        self.stds = []

    def fit(
        self,
        X: Sequence[Sequence[float]],
    ) -> None:

        if not X:
            raise ValueError(
                "Cannot fit standardizer on empty data."
            )

        width = len(X[0])

        self.means = [
            mean_or_zero(
                [
                    float(row[j])
                    for row in X
                ]
            )
            for j in range(width)
        ]

        self.stds = [
            std_or_one(
                [
                    float(row[j])
                    for row in X
                ]
            )
            for j in range(width)
        ]

    def one(
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
            self.one(row)
            for row in X
        ]


# ==============================================================================
# LOGISTIC MODEL
# ==============================================================================

class LogisticModel:

    def __init__(self):

        self.weights = []
        self.bias = 0.0

    @staticmethod
    def sigmoid(
        z: float,
    ) -> float:

        if z >= 0:

            e = math.exp(
                -min(z, 60)
            )

            return 1.0 / (
                1.0 + e
            )

        e = math.exp(
            max(z, -60)
        )

        return e / (
            1.0 + e
        )

    def fit(
        self,
        X: Sequence[Sequence[float]],
        y: Sequence[int],
    ) -> None:

        n = len(X)
        d = len(X[0])

        self.weights = [
            0.0
        ] * d

        self.bias = 0.0

        positives = sum(y)
        negatives = (
            n - positives
        )

        positive_weight = (
            n
            / max(
                2 * positives,
                1,
            )
        )

        negative_weight = (
            n
            / max(
                2 * negatives,
                1,
            )
        )

        for epoch in range(
            LOGISTIC_EPOCHS
        ):

            gradient_weights = [
                0.0
            ] * d

            gradient_bias = 0.0

            learning_rate = (
                LOGISTIC_LR
                / (
                    1
                    + 0.003 * epoch
                )
            )

            for row, target in zip(
                X,
                y,
            ):

                z = (
                    self.bias
                    + sum(
                        weight * value
                        for weight, value
                        in zip(
                            self.weights,
                            row,
                        )
                    )
                )

                probability = (
                    self.sigmoid(z)
                )

                sample_weight = (
                    positive_weight
                    if target
                    else negative_weight
                )

                error = (
                    probability
                    - target
                ) * sample_weight

                gradient_bias += error

                for j in range(d):
                    gradient_weights[j] += (
                        error
                        * row[j]
                    )

            inverse_n = 1.0 / n

            self.bias -= (
                learning_rate
                * gradient_bias
                * inverse_n
            )

            for j in range(d):

                gradient = (
                    gradient_weights[j]
                    * inverse_n
                    + LOGISTIC_L2
                    * self.weights[j]
                )

                self.weights[j] -= (
                    learning_rate
                    * gradient
                )

    def predict(
        self,
        x: Sequence[float],
    ) -> float:

        z = (
            self.bias
            + sum(
                weight * value
                for weight, value
                in zip(
                    self.weights,
                    x,
                )
            )
        )

        return self.sigmoid(z)


# ==============================================================================
# STATE MODEL
# ==============================================================================

class StateModel:

    def __init__(self):
        self.global_up = 0.5
        self.exact = {}
        self.cat = {}

    def fit(
        self,
        signals: Sequence[Signal],
        labels: Sequence[int],
    ) -> None:

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
            ][0] += int(label)

            exact[
                signal.state_key
            ][1] += 1

            categorical[
                signal.categorical_key
            ][0] += int(label)

            categorical[
                signal.categorical_key
            ][1] += 1

        self.exact = {
            key: tuple(value)
            for key, value
            in exact.items()
        }

        self.cat = {
            key: tuple(value)
            for key, value
            in categorical.items()
        }

    def predict(
        self,
        signal: Signal,
    ) -> Tuple[float, int]:

        categorical_up, categorical_n = (
            self.cat.get(
                signal.categorical_key,
                (0, 0),
            )
        )

        categorical_probability = (
            categorical_up
            + STATE_PRIOR_STRENGTH
            * self.global_up
        ) / max(
            categorical_n
            + STATE_PRIOR_STRENGTH,
            EPS,
        )

        exact_up, exact_n = (
            self.exact.get(
                signal.state_key,
                (0, 0),
            )
        )

        exact_probability = (
            exact_up
            + STATE_PRIOR_STRENGTH
            * categorical_probability
        ) / max(
            exact_n
            + STATE_PRIOR_STRENGTH,
            EPS,
        )

        if (
            exact_n
            < MIN_STATE_SUPPORT
        ):

            probability = (
                0.35
                * exact_probability
                + 0.65
                * categorical_probability
            )

        else:

            probability = (
                0.70
                * exact_probability
                + 0.30
                * categorical_probability
            )

        return (
            probability,
            exact_n,
        )


# ==============================================================================
# KNN
# ==============================================================================

class KNNModel:

    def __init__(self):
        self.X = []
        self.y = []

    @staticmethod
    def distance(
        a: Sequence[float],
        b: Sequence[float],
    ) -> float:

        return math.sqrt(
            sum(
                (x - y) ** 2
                for x, y in zip(
                    a,
                    b,
                )
            )
        )

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

    def predict(
        self,
        x: Sequence[float],
    ) -> float:

        if not self.X:
            return 0.5

        rows = sorted(
            (
                self.distance(
                    x,
                    row,
                ),
                target,
            )
            for row, target
            in zip(
                self.X,
                self.y,
            )
        )

        rows = rows[
            :min(
                KNN_K,
                len(rows),
            )
        ]

        numerator = 0.0
        denominator = 0.0

        for distance, target in rows:

            weight = math.exp(
                -distance
                / max(
                    KNN_TEMPERATURE,
                    EPS,
                )
            )

            numerator += (
                weight
                * target
            )

            denominator += weight

        if denominator <= EPS:
            return 0.5

        return (
            numerator
            / denominator
        )


# ==============================================================================
# V4.1.3 BENCHMARK MODEL
# ==============================================================================

class PredictiveModel:

    def __init__(self):

        self.scaler = Standardizer()
        self.logistic = LogisticModel()
        self.knn = KNNModel()
        self.state = StateModel()

        self.train_support = 0

    def fit(
        self,
        signals: Sequence[Signal],
        labels: Sequence[int],
    ) -> None:

        if len(signals) < MIN_TRAIN_SAMPLES:
            raise ValueError(
                f"Insufficient training samples: "
                f"{len(signals)}"
            )

        raw_features = [
            signal.feature
            for signal in signals
        ]

        self.scaler.fit(
            raw_features
        )

        X = self.scaler.transform(
            raw_features
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

        x = self.scaler.one(
            signal.feature
        )

        probability_logistic = (
            self.logistic.predict(x)
        )

        probability_knn = (
            self.knn.predict(x)
        )

        probability_state, support = (
            self.state.predict(
                signal
            )
        )

        probability = (
            WEIGHT_LOGISTIC
            * probability_logistic

            + WEIGHT_KNN
            * probability_knn

            + WEIGHT_STATE
            * probability_state
        )

        probability = min(
            max(
                probability,
                0.001,
            ),
            0.999,
        )

        margin = (
            abs(
                probability
                - 0.5
            )
            * 2
        )

        agreement = max(
            0.0,
            min(
                1.0,
                1.0
                - (
                    abs(
                        probability_logistic
                        - probability_knn
                    )

                    + abs(
                        probability_logistic
                        - probability_state
                    )

                    + abs(
                        probability_knn
                        - probability_state
                    )
                )
                / 3.0,
            ),
        )

        support_factor = min(
            1.0,
            support
            / MIN_SUPPORT_FOR_FULL_CONFIDENCE,
        )

        train_factor = min(
            1.0,
            self.train_support / 500.0,
        )

        confidence = (
            0.55 * margin
            + 0.25 * agreement
            + 0.10 * support_factor
            + 0.10 * train_factor
        )

        abstain = (
            confidence
            < MIN_CONFIDENCE
            or margin
            < MIN_MARGIN
        )

        return Prediction(
            probability_up=probability,
            probability_down=1.0 - probability,
            confidence=confidence,
            support=support,
            abstain=abstain,
            model_components={
                "logistic": probability_logistic,
                "knn": probability_knn,
                "state": probability_state,
                "agreement": agreement,
            },
        )


# ==============================================================================
# EVALUATION
# ==============================================================================

def evaluate(
    y: Sequence[int],
    probabilities: Sequence[float],
    abstain: Sequence[bool],
) -> Dict[str, Any]:

    usable_y = []
    usable_predictions = []
    usable_probabilities = []

    for actual, probability, abstained in zip(
        y,
        probabilities,
        abstain,
    ):

        if abstained:
            continue

        usable_y.append(actual)
        usable_probabilities.append(
            probability
        )

        usable_predictions.append(
            1
            if probability >= 0.5
            else 0
        )

    if usable_y:

        accuracy_value = (
            sum(
                actual == prediction
                for actual, prediction
                in zip(
                    usable_y,
                    usable_predictions,
                )
            )
            / len(usable_y)
        )

        base = max(
            sum(usable_y)
            / len(usable_y),
            1
            - (
                sum(usable_y)
                / len(usable_y)
            ),
        )

        tp = tn = fp = fn = 0

        for actual, prediction in zip(
            usable_y,
            usable_predictions,
        ):

            if actual == 1 and prediction == 1:
                tp += 1

            elif actual == 0 and prediction == 0:
                tn += 1

            elif actual == 0 and prediction == 1:
                fp += 1

            else:
                fn += 1

        balanced = 0.5 * (
            tp / max(
                tp + fn,
                1,
            )
            + tn / max(
                tn + fp,
                1,
            )
        )

        brier = mean_or_zero(
            [
                (
                    probability
                    - actual
                ) ** 2
                for actual, probability
                in zip(
                    usable_y,
                    usable_probabilities,
                )
            ]
        )

        log_loss_value = mean_or_zero(
            [
                -math.log(
                    max(
                        min(
                            (
                                probability
                                if actual
                                else
                                1
                                - probability
                            ),
                            1 - 1e-6,
                        ),
                        1e-6,
                    )
                )
                for actual, probability
                in zip(
                    usable_y,
                    usable_probabilities,
                )
            ]
        )

        edge = (
            accuracy_value
            - base
        )

    else:

        accuracy_value = None
        balanced = None
        brier = None
        log_loss_value = None
        base = None
        edge = None

    return {
        "samples": len(y),
        "used": len(usable_y),
        "abstained": (
            len(y)
            - len(usable_y)
        ),
        "accuracy": accuracy_value,
        "balanced_accuracy": balanced,
        "baseline_accuracy": base,
        "edge": edge,
        "coverage": safe_div(
            len(usable_y),
            len(y),
        ),
        "brier_score": brier,
        "log_loss": log_loss_value,
        "probabilities": list(
            probabilities
        ),
        "abstain_mask": list(
            abstain
        ),
        "actual": list(y),
    }


# ==============================================================================
# RUN WINDOW
# ==============================================================================

def run_window(
    candles: Sequence[Candle],
    signals: Sequence[Signal],
    window: WalkForwardWindow,
) -> Dict[str, Any]:

    result = {
        "window": asdict(window),
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
                set(train_labels)
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

                "result":
                    evaluate(
                        oos_labels,
                        [
                            0.5
                        ] * len(oos_labels),
                        [
                            True
                        ] * len(oos_labels),
                    ),

                "encoder_states":
                    0,
            }

            continue

        model.fit(
            train_signals,
            train_labels,
        )

        probabilities = []
        abstained = []
        confidence_values = []

        for signal in oos_signals:

            prediction = (
                model.predict(
                    signal
                )
            )

            probabilities.append(
                prediction.probability_up
            )

            abstained.append(
                prediction.abstain
            )

            confidence_values.append(
                prediction.confidence
            )

        metrics = evaluate(
            oos_labels,
            probabilities,
            abstained,
        )

        metrics[
            "mean_confidence"
        ] = mean_or_zero(
            confidence_values
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

            "result":
                metrics,
        }

    return result


# ==============================================================================
# AGGREGATION
# ==============================================================================

def aggregate(
    results: Sequence[
        Dict[str, Any]
    ],
) -> Dict[int, Dict[str, Any]]:

    output = {}

    for horizon in HORIZONS:

        rows = [
            result[
                "horizons"
            ][horizon]["result"]
            for result in results
        ]

        valid_accuracies = [
            row["accuracy"]
            for row in rows
            if row["accuracy"]
            is not None
        ]

        valid_edges = [
            row["edge"]
            for row in rows
            if row["edge"]
            is not None
        ]

        valid_brier = [
            row["brier_score"]
            for row in rows
            if row["brier_score"]
            is not None
        ]

        valid_log_loss = [
            row["log_loss"]
            for row in rows
            if row["log_loss"]
            is not None
        ]

        output[horizon] = {

            "mean_accuracy":
                (
                    mean_or_zero(
                        valid_accuracies
                    )
                    if valid_accuracies
                    else None
                ),

            "mean_edge":
                (
                    mean_or_zero(
                        valid_edges
                    )
                    if valid_edges
                    else None
                ),

            "mean_coverage":
                mean_or_zero(
                    [
                        row["coverage"]
                        for row in rows
                    ]
                ),

            "mean_brier":
                (
                    mean_or_zero(
                        valid_brier
                    )
                    if valid_brier
                    else None
                ),

            "mean_log_loss":
                (
                    mean_or_zero(
                        valid_log_loss
                    )
                    if valid_log_loss
                    else None
                ),

            "positive_edge_windows":
                sum(
                    value > 0
                    for value
                    in valid_edges
                ),

            "negative_edge_windows":
                sum(
                    value < 0
                    for value
                    in valid_edges
                ),

            "window_count":
                len(rows),
        }

    return output


# ==============================================================================
# FORMATTERS
# ==============================================================================

def fmt_pct(
    value: Optional[float],
) -> str:

    if value is None:
        return "N/A"

    return f"{100 * value:.2f}%"


def fmt_num(
    value: Optional[float],
) -> str:

    if value is None:
        return "N/A"

    return f"{value:.4f}"


# ==============================================================================
# MAIN
# ==============================================================================

def main():

    print("=" * 88)

    print(
        "MLAI v4.1.4 CANONICAL MARKET LANGUAGE FOUNDATION"
    )

    print("=" * 88)

    print(
        "RESEARCH / VALIDATION ONLY"
    )

    # --------------------------------------------------------------------------
    # PROTECTION
    # --------------------------------------------------------------------------

    print()
    print("=" * 88)
    print("PROTECTION CHECK")
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
    print("DATA LOAD")
    print("=" * 88)

    candles, invalid = (
        load_market_data(
            MARKET_DATA_FILE
        )
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
            "Insufficient candle history"
        )

    # --------------------------------------------------------------------------
    # CHRONOLOGY
    # --------------------------------------------------------------------------

    print()
    print("=" * 88)
    print("CHRONOLOGICAL DATA AUDIT")
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
            "Chronology audit failed"
        )

    if chronology["duplicates"]:
        raise RuntimeError(
            "Chronology audit failed"
        )

    # --------------------------------------------------------------------------
    # WALK FORWARD
    # --------------------------------------------------------------------------

    windows = (
        create_walk_forward_windows(
            len(candles),
            DEFAULT_TRAIN_WINDOWS,
            DEFAULT_OOS_SIZE,
        )
    )

    # --------------------------------------------------------------------------
    # ATR
    # --------------------------------------------------------------------------

    atr = calculate_atr(
        candles
    )

    # --------------------------------------------------------------------------
    # STRUCTURE
    # --------------------------------------------------------------------------

    engine = CausalStructureEngine(
        candles
    )

    states = engine.build()

    # --------------------------------------------------------------------------
    # BENCHMARK SIGNALS
    # --------------------------------------------------------------------------

    signals = create_benchmark_signals(
        candles,
        states,
        atr,
    )

    # --------------------------------------------------------------------------
    # CAUSALITY
    # --------------------------------------------------------------------------

    causality = (
        audit_structure_causality(
            candles,
            engine.swings,
            states,
            engine.events,
        )
    )

    if not causality["passed"]:
        raise RuntimeError(
            "Causality audit failed"
        )

    # --------------------------------------------------------------------------
    # BOUNDARY AUDITS
    # --------------------------------------------------------------------------

    training_boundary_pass = (
        audit_training_boundaries(
            candles,
            signals,
            windows,
        )
    )

    oos_boundary_pass = (
        audit_oos_boundaries(
            candles,
            signals,
            windows,
        )
    )

    if not training_boundary_pass:
        raise RuntimeError(
            "Training boundary audit failed"
        )

    if not oos_boundary_pass:
        raise RuntimeError(
            "OOS boundary audit failed"
        )

    # --------------------------------------------------------------------------
    # MARKET LANGUAGE STATES
    # --------------------------------------------------------------------------

    market_states = build_market_states(
        candles,
        states,
        atr,
        instrument="XAUUSD",
        timeframe="UNKNOWN",
    )

    # --------------------------------------------------------------------------
    # EXPERIENCE MEMORY
    # --------------------------------------------------------------------------

    all_experience = {
        horizon: build_experience_records(
            candles,
            atr,
            states,
            market_states,
            0,
            len(candles) - horizon,
            horizon,
        )
        for horizon in HORIZONS
    }

    # --------------------------------------------------------------------------
    # REPORT BASIC STATUS
    # --------------------------------------------------------------------------

    print()
    print("=" * 88)
    print("MLAI 4.1.4 FOUNDATION STATUS")
    print("=" * 88)

    print(
        f"Dataset                 : "
        f"{len(candles)} valid / "
        f"{invalid} invalid"
    )

    print(
        "Causality               : "
        + (
            "PASS"
            if causality["passed"]
            else "FAIL"
        )
    )

    print(
        "Training boundary       : "
        + (
            "PASS"
            if training_boundary_pass
            else "FAIL"
        )
    )

    print(
        "OOS boundary            : "
        + (
            "PASS"
            if oos_boundary_pass
            else "FAIL"
        )
    )

    print(
        f"Confirmed swings        : "
        f"{len(engine.swings)}"
    )

    print(
        f"Structural events       : "
        f"{sum(1 for event in engine.events.values() if event != 'NONE')}"
    )

    # --------------------------------------------------------------------------
    # MARKET LANGUAGE
    # --------------------------------------------------------------------------

    print()
    print("=" * 88)
    print("MARKET LANGUAGE REPRESENTATION")
    print("=" * 88)

    sequence_counts = Counter(
        state.sequence_state
        for state in market_states
    )

    regime_counts = Counter(
        state.regime
        for state in market_states
    )

    print(
        "Sequence states:"
    )

    for name, count in (
        sequence_counts.most_common()
    ):
        print(
            f"  {name:<32}: {count}"
        )

    print()
    print(
        "Regimes:"
    )

    for name, count in (
        regime_counts.most_common()
    ):
        print(
            f"  {name:<32}: {count}"
        )

    # --------------------------------------------------------------------------
    # WALK-FORWARD BENCHMARK
    # --------------------------------------------------------------------------

    print()
    print("=" * 88)
    print("V4.1.3 BINARY BENCHMARK")
    print("=" * 88)

    window_results = []

    for window in windows:

        result = run_window(
            candles,
            signals,
            window,
        )

        window_results.append(
            result
        )

        print()

        print(
            f"Window {window.number} "
            f"TRAIN [{window.train_start}:{window.train_end}] "
            f"OOS [{window.oos_start}:{window.oos_end}]"
        )

        for horizon in HORIZONS:

            metrics = (
                result[
                    "horizons"
                ][horizon]["result"]
            )

            print(
                f"  H+{horizon}: "
                f"Accuracy="
                f"{fmt_pct(metrics['accuracy'])} | "
                f"Edge="
                f"{fmt_pct(metrics['edge'])} | "
                f"Coverage="
                f"{fmt_pct(metrics['coverage'])}"
            )

    benchmark_aggregate = aggregate(
        window_results
    )

    # --------------------------------------------------------------------------
    # HISTORICAL CONDITIONAL BASELINES
    # --------------------------------------------------------------------------

    print()
    print("=" * 88)
    print(
        "HISTORICAL CONDITIONAL BASELINES"
    )
    print("=" * 88)

    baseline_summary = {}

    for horizon in HORIZONS:

        baseline_rows = []

        for window in windows:

            training_end = (
                window.train_end
                - horizon
            )

            if training_end <= 0:
                continue

            records = (
                build_experience_records(
                    candles,
                    atr,
                    states,
                    market_states,
                    0,
                    training_end,
                    horizon,
                )
            )

            for index in range(
                window.oos_start,
                window.oos_end,
            ):

                if (
                    index + horizon
                    >= len(candles)
                ):
                    continue

                baseline = (
                    historical_conditional_baseline(
                        records,
                        market_states[index],
                    )
                )

                baseline_rows.append(
                    baseline
                )

        if baseline_rows:

            baseline_summary[horizon] = {

                "UP":
                    mean_or_zero(
                        [
                            row["UP"]
                            for row
                            in baseline_rows
                        ]
                    ),

                "DOWN":
                    mean_or_zero(
                        [
                            row["DOWN"]
                            for row
                            in baseline_rows
                        ]
                    ),

                "NEUTRAL":
                    mean_or_zero(
                        [
                            row["NEUTRAL"]
                            for row
                            in baseline_rows
                        ]
                    ),
            }

            summary = (
                baseline_summary[horizon]
            )

            print(
                f"H+{horizon}: "
                f"UP="
                f"{fmt_pct(summary['UP'])} | "
                f"DOWN="
                f"{fmt_pct(summary['DOWN'])} | "
                f"NEUTRAL="
                f"{fmt_pct(summary['NEUTRAL'])}"
            )

    # --------------------------------------------------------------------------
    # PROTECTION
    # --------------------------------------------------------------------------

    protection_after = (
        sha256_file(
            MARKET_DATA_FILE
        )
    )

    if (
        protection_before
        != protection_after
    ):
        raise RuntimeError(
            "market_data.bin changed"
        )

    # --------------------------------------------------------------------------
    # ARTIFACT
    # --------------------------------------------------------------------------

    validation_artifact = {

        "version":
            VERSION,

        "candles":
            len(candles),

        "invalid":
            invalid,

        "causality":
            causality,

        "training_boundary":
            training_boundary_pass,

        "oos_boundary":
            oos_boundary_pass,

        "market_states":
            [
                asdict(state)
                for state
                in market_states
            ],

        "experience_counts":
            {
                horizon:
                    len(records)
                for horizon, records
                in all_experience.items()
            },

        "benchmark_aggregate":
            benchmark_aggregate,

        "baseline_summary":
            baseline_summary,

        "protection":
            {
                "before":
                    protection_before,

                "after":
                    protection_after,
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

    # --------------------------------------------------------------------------
    # REPORT
    # --------------------------------------------------------------------------

    report = [

        "# MLAI v4.1.4 Market Language Foundation",

        "",

        "## Scientific Status",

        "",

        "- Research / validation only",
        "- Trading: DISABLED",

        f"- Valid candles: {len(candles)}",

        f"- Confirmed swings: "
        f"{len(engine.swings)}",

        (
            "- Causal structure: PASS"
            if causality["passed"]
            else "- Causal structure: FAIL"
        ),

        (
            "- Training boundary: PASS"
            if training_boundary_pass
            else "- Training boundary: FAIL"
        ),

        (
            "- OOS boundary: PASS"
            if oos_boundary_pass
            else "- OOS boundary: FAIL"
        ),

        "",

        "## Market Language Representation",

        "",

        "- Canonical MarketState: ENABLED",
        "- Causal sequence state: ENABLED",
        "- Causal regime state: ENABLED",
        "- Historical experience records: ENABLED",
        "- ATR-normalized outcomes: ENABLED",
        "- UP/DOWN/NEUTRAL outcomes: ENABLED",
        "- v4.1.3 binary benchmark retained: YES",

        "",

        "## Benchmark",

        "",
    ]

    for horizon, result in (
        benchmark_aggregate.items()
    ):

        report.extend(
            [
                f"### H+{horizon}",

                (
                    f"- Mean accuracy: "
                    f"{fmt_pct(result['mean_accuracy'])}"
                ),

                (
                    f"- Mean edge: "
                    f"{fmt_pct(result['mean_edge'])}"
                ),

                (
                    f"- Mean coverage: "
                    f"{fmt_pct(result['mean_coverage'])}"
                ),

                (
                    f"- Positive-edge windows: "
                    f"{result['positive_edge_windows']}"
                ),

                (
                    f"- Negative-edge windows: "
                    f"{result['negative_edge_windows']}"
                ),

                "",
            ]
        )

    report.extend(
        [

            "## Historical Conditional Baselines",

            "",
        ]
    )

    for horizon, result in (
        baseline_summary.items()
    ):

        report.extend(
            [
                f"### H+{horizon}",

                (
                    f"- UP: "
                    f"{fmt_pct(result['UP'])}"
                ),

                (
                    f"- DOWN: "
                    f"{fmt_pct(result['DOWN'])}"
                ),

                (
                    f"- NEUTRAL: "
                    f"{fmt_pct(result['NEUTRAL'])}"
                ),

                "",
            ]
        )

    report.extend(
        [

            "## Protection",

            "",

            (
                "- market_data.bin unchanged: PASS"
                if protection_before
                == protection_after
                else
                "- market_data.bin unchanged: FAIL"
            ),

            "- Production MLAI modified: NO",
            "- Learning memory modified: NO",
            "- Trading enabled: NO",

            "",

            "MLAI v4.1.4 COMPLETE",
        ]
    )

    with open(
        VALIDATION_REPORT,
        "w",
        encoding="utf-8",
    ) as f:

        f.write(
            "\n".join(report)
        )

    # --------------------------------------------------------------------------
    # FINAL OUTPUT
    # --------------------------------------------------------------------------

    print()
    print("=" * 88)

    print(
        "VALIDATION ARTIFACT:"
    )

    print(
        f"    {VALIDATION_BIN}"
    )

    print(
        "VALIDATION REPORT:"
    )

    print(
        f"    {VALIDATION_REPORT}"
    )

    print()
    print(
        "MARKET DATA PROTECTION: PASS"
    )

    print(
        "PRODUCTION MLAI: NOT MODIFIED"
    )

    print(
        "LEARNING MEMORY: NOT MODIFIED"
    )

    print(
        "TRADING: DISABLED"
    )

    print()
    print("=" * 88)

    print(
        "MLAI v4.1.4 COMPLETE"
    )

    print("=" * 88)


# ==============================================================================
# ENTRY POINT
# ==============================================================================

if __name__ == "__main__":
    main()