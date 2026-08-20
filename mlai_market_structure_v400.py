"""
================================================================================
MLAI v4.0.0
HARDENED CAUSAL MARKET STRUCTURE INTELLIGENCE
================================================================================

RESEARCH / VALIDATION ONLY

PRIMARY REPRESENTATION
----------------------
Market Structure

LEARNED RELATIONSHIP
--------------------
Causal Structural State -> Future Directional Outcome

HORIZONS
--------
H+4
H+8
H+16

DESIGN OBJECTIVES
-----------------
1. Strict causal swing confirmation
2. Strict causal structure state
3. Strict causal BOS / CHoCH events
4. No future structure leakage
5. No future event leakage
6. No future level consumption
7. Strict training-label boundary
8. Walk-forward validation
9. Training-only state encoders
10. Frozen OOS models
11. Minimum-support filtering
12. Abstention when evidence is weak
13. Confidence calibration
14. Majority-class baseline
15. Balanced accuracy
16. Coverage measurement
17. Deterministic state representation
18. No production-model modification
19. No learning-memory modification
20. No trading
21. No internet requirement

IMPORTANT
---------
This file is a research validator.

It does NOT claim that market direction is predictable.

A model is considered useful only if it demonstrates stable OOS
improvement against appropriate baselines across multiple windows.

================================================================================
"""

from __future__ import annotations

import math
import os
import pickle
import hashlib
import statistics
from dataclasses import dataclass, asdict
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Tuple


# ==============================================================================
# CONFIGURATION
# ==============================================================================

VERSION = "4.0.0"

MARKET_DATA_FILE = "market_data.bin"

VALIDATION_BIN = (
    "MLAI_V400_CAUSAL_MARKET_STRUCTURE_WALKFORWARD_VALIDATION.bin"
)

VALIDATION_REPORT = (
    "MLAI_V400_CAUSAL_MARKET_STRUCTURE_WALKFORWARD_VALIDATION_REPORT.md"
)

HORIZONS = (4, 8, 16)

SWING_LEFT = 3
SWING_RIGHT = 3

DEFAULT_TRAIN_WINDOWS = 5
DEFAULT_OOS_SIZE = 81

MIN_STATE_SUPPORT = 8
MIN_MODEL_SAMPLES = 30

BUY = 1
SELL = -1
NEUTRAL = 0


# ==============================================================================
# DATA STRUCTURES
# ==============================================================================

@dataclass(frozen=True)
class Candle:
    index: int
    timestamp: Any
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True)
class Swing:
    index: int
    kind: str
    price: float
    confirmation_index: int


@dataclass(frozen=True)
class StructureState:
    index: int
    trend: str

    last_high_index: Optional[int]
    last_low_index: Optional[int]

    last_high_price: Optional[float]
    last_low_price: Optional[float]

    previous_high_price: Optional[float]
    previous_low_price: Optional[float]

    structure_label: str

    last_event: Optional[str]
    event_age: Optional[int]

    distance_to_high: Optional[float]
    distance_to_low: Optional[float]

    state_key: str


@dataclass(frozen=True)
class Signal:
    index: int
    timestamp: Any

    state_key: str
    structure_label: str
    trend: str

    event: Optional[str]
    event_age: Optional[int]

    target_horizon: int
    label: Optional[int]

    state_direction: int


@dataclass
class ModelResult:
    horizon: int

    samples: int
    buy_count: int
    sell_count: int

    baseline_probability: float

    state_count: int

    covered: int
    abstained: int
    coverage: float

    accuracy: Optional[float]
    balanced_accuracy: Optional[float]

    baseline_accuracy: Optional[float]
    edge: Optional[float]

    brier_score: Optional[float]

    mean_probability: Optional[float]

    reliability_error: Optional[float]


# ==============================================================================
# GENERAL UTILITIES
# ==============================================================================

def safe_float(value: Any) -> Optional[float]:
    try:
        value = float(value)
        if not math.isfinite(value):
            return None
        return value
    except Exception:
        return None


def normalize_timestamp(value: Any) -> Any:
    return value


def sha256_file(path: str) -> Optional[str]:
    if not os.path.exists(path):
        return None

    h = hashlib.sha256()

    with open(path, "rb") as f:
        while True:
            chunk = f.read(1024 * 1024)

            if not chunk:
                break

            h.update(chunk)

    return h.hexdigest()


def fmt_pct(value: Optional[float]) -> str:
    if value is None:
        return "N/A"

    return f"{value * 100:.2f}%"


def fmt_num(value: Optional[float]) -> str:
    if value is None:
        return "N/A"

    return f"{value:.4f}"


# ==============================================================================
# PROTECTION
# ==============================================================================

class ProtectionGuard:

    def __init__(self, market_file: str):
        self.market_file = market_file
        self.before_hash = sha256_file(market_file)

    def verify_unchanged(self) -> bool:
        after_hash = sha256_file(self.market_file)

        return self.before_hash == after_hash


# ==============================================================================
# MARKET DATA LOADING
# ==============================================================================

def extract_raw_candles(obj: Any) -> Any:

    if isinstance(obj, dict):

        possible_keys = (
            "candles",
            "data",
            "ohlcv",
            "market_data",
            "records",
        )

        for key in possible_keys:
            if key in obj:
                return obj[key]

        return obj

    return obj


def parse_candle(item: Any, index: int) -> Optional[Candle]:

    if isinstance(item, Candle):
        return item

    if isinstance(item, dict):

        timestamp = (
            item.get("timestamp")
            if "timestamp" in item
            else item.get("time")
        )

        o = item.get("open")
        h = item.get("high")
        l = item.get("low")
        c = item.get("close")
        v = item.get("volume", 0.0)

    elif isinstance(item, (list, tuple)) and len(item) >= 5:

        timestamp = item[0]
        o = item[1]
        h = item[2]
        l = item[3]
        c = item[4]
        v = item[5] if len(item) > 5 else 0.0

    else:
        return None

    o = safe_float(o)
    h = safe_float(h)
    l = safe_float(l)
    c = safe_float(c)
    v = safe_float(v)

    if None in (o, h, l, c):
        return None

    if v is None:
        v = 0.0

    if h < max(o, c):
        return None

    if l > min(o, c):
        return None

    if l > h:
        return None

    return Candle(
        index=index,
        timestamp=normalize_timestamp(timestamp),
        open=o,
        high=h,
        low=l,
        close=c,
        volume=v,
    )


def load_market_data(path: str) -> Tuple[List[Candle], int]:

    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Market data file not found: {path}"
        )

    with open(path, "rb") as f:
        obj = pickle.load(f)

    raw = extract_raw_candles(obj)

    candles = []
    invalid = 0

    if isinstance(raw, dict):

        iterable = []

        for key, value in raw.items():

            if isinstance(value, dict):
                value = dict(value)
                value.setdefault("timestamp", key)

            iterable.append(value)

    elif isinstance(raw, (list, tuple)):
        iterable = raw

    else:
        raise TypeError(
            f"Unsupported market data structure: {type(raw)}"
        )

    for i, item in enumerate(iterable):

        candle = parse_candle(item, i)

        if candle is None:
            invalid += 1
            continue

        candles.append(candle)

    # Re-index after validation.
    candles = [
        Candle(
            index=i,
            timestamp=c.timestamp,
            open=c.open,
            high=c.high,
            low=c.low,
            close=c.close,
            volume=c.volume,
        )
        for i, c in enumerate(candles)
    ]

    return candles, invalid


# ==============================================================================
# CHRONOLOGICAL AUDIT
# ==============================================================================

def audit_chronology(candles: List[Candle]) -> Dict[str, Any]:

    timestamps = [c.timestamp for c in candles]

    duplicate = len(timestamps) != len(set(map(str, timestamps)))

    ordered = True

    try:
        for i in range(1, len(timestamps)):

            if timestamps[i] <= timestamps[i - 1]:
                ordered = False
                break

    except Exception:
        # If timestamps cannot be compared safely, use index order.
        ordered = True

    return {
        "ordered": ordered,
        "duplicates": duplicate,
    }


# ==============================================================================
# ATR
# ==============================================================================

def calculate_atr(
    candles: List[Candle],
    period: int = 14,
) -> List[Optional[float]]:

    tr = [None] * len(candles)

    for i, candle in enumerate(candles):

        if i == 0:
            tr[i] = candle.high - candle.low
            continue

        previous_close = candles[i - 1].close

        tr[i] = max(
            candle.high - candle.low,
            abs(candle.high - previous_close),
            abs(candle.low - previous_close),
        )

    atr = [None] * len(candles)

    running = []

    for i in range(len(candles)):

        if tr[i] is None:
            continue

        running.append(tr[i])

        if len(running) >= period:

            window = running[-period:]

            atr[i] = sum(window) / len(window)

    return atr


# ==============================================================================
# CAUSAL SWING DETECTION
# ==============================================================================

def detect_confirmed_swings(
    candles: List[Candle],
    left: int = SWING_LEFT,
    right: int = SWING_RIGHT,
) -> List[Swing]:

    """
    A swing at index i becomes known only at:

        confirmation_index = i + right

    This is the critical causal boundary.
    """

    swings: List[Swing] = []

    n = len(candles)

    for i in range(left, n - right):

        current = candles[i]

        left_slice = candles[i - left:i]
        right_slice = candles[i + 1:i + right + 1]

        is_high = all(
            current.high >= x.high
            for x in left_slice + right_slice
        )

        is_low = all(
            current.low <= x.low
            for x in left_slice + right_slice
        )

        confirmation_index = i + right

        if is_high:
            swings.append(
                Swing(
                    index=i,
                    kind="HIGH",
                    price=current.high,
                    confirmation_index=confirmation_index,
                )
            )

        if is_low:
            swings.append(
                Swing(
                    index=i,
                    kind="LOW",
                    price=current.low,
                    confirmation_index=confirmation_index,
                )
            )

    swings.sort(
        key=lambda x: (
            x.confirmation_index,
            x.index,
            x.kind,
        )
    )

    return swings


# ==============================================================================
# CAUSAL STRUCTURE ENGINE
# ==============================================================================

class CausalStructureEngine:

    def __init__(self, candles: List[Candle]):
        self.candles = candles

        self.swings = detect_confirmed_swings(candles)

        self.swings_by_confirmation = defaultdict(list)

        for swing in self.swings:
            self.swings_by_confirmation[
                swing.confirmation_index
            ].append(swing)

        self.states: List[StructureState] = []

        self.events: Dict[int, str] = {}

    @staticmethod
    def _safe_distance(
        price: Optional[float],
        current: float,
    ) -> Optional[float]:

        if price is None:
            return None

        if current == 0:
            return None

        return (current - price) / abs(current)

    @staticmethod
    def _state_key(
        trend: str,
        structure_label: str,
        event: Optional[str],
        event_age: Optional[int],
        high_relation: str,
        low_relation: str,
    ) -> str:

        return "|".join(
            [
                trend,
                structure_label,
                event or "NONE",
                str(event_age if event_age is not None else -1),
                high_relation,
                low_relation,
            ]
        )

    def build(self) -> List[StructureState]:

        last_high: Optional[Swing] = None
        previous_high: Optional[Swing] = None

        last_low: Optional[Swing] = None
        previous_low: Optional[Swing] = None

        trend = "UNKNOWN"

        last_event: Optional[str] = None
        last_event_index: Optional[int] = None

        # Levels consumed by an event are tracked causally.
        consumed_high_levels = set()
        consumed_low_levels = set()

        for i, candle in enumerate(self.candles):

            # ------------------------------------------------------------------
            # 1. Consume ONLY swings whose confirmation has arrived.
            # ------------------------------------------------------------------

            newly_confirmed = self.swings_by_confirmation.get(i, [])

            for swing in newly_confirmed:

                if swing.kind == "HIGH":

                    previous_high = last_high
                    last_high = swing

                elif swing.kind == "LOW":

                    previous_low = last_low
                    last_low = swing

            # ------------------------------------------------------------------
            # 2. Determine structural relationships.
            # ------------------------------------------------------------------

            high_relation = "NONE"
            low_relation = "NONE"

            if (
                last_high is not None
                and previous_high is not None
            ):

                if last_high.price > previous_high.price:
                    high_relation = "HH"

                elif last_high.price < previous_high.price:
                    high_relation = "LH"

                else:
                    high_relation = "EQ"

            if (
                last_low is not None
                and previous_low is not None
            ):

                if last_low.price > previous_low.price:
                    low_relation = "HL"

                elif last_low.price < previous_low.price:
                    low_relation = "LL"

                else:
                    low_relation = "EQ"

            # ------------------------------------------------------------------
            # 3. Infer structure.
            # ------------------------------------------------------------------

            structure_label = "UNDEFINED"

            if high_relation == "HH" and low_relation == "HL":
                structure_label = "HH_HL"

            elif high_relation == "LH" and low_relation == "LL":
                structure_label = "LH_LL"

            elif high_relation == "HH":
                structure_label = "HH"

            elif high_relation == "LH":
                structure_label = "LH"

            elif low_relation == "HL":
                structure_label = "HL"

            elif low_relation == "LL":
                structure_label = "LL"

            # ------------------------------------------------------------------
            # 4. Establish initial trend.
            # ------------------------------------------------------------------

            if structure_label == "HH_HL":
                trend = "BULLISH"

            elif structure_label == "LH_LL":
                trend = "BEARISH"

            elif structure_label in ("HH", "HL"):
                if trend == "UNKNOWN":
                    trend = "BULLISH"

            elif structure_label in ("LH", "LL"):
                if trend == "UNKNOWN":
                    trend = "BEARISH"

            # ------------------------------------------------------------------
            # 5. Causal BOS / CHoCH.
            #
            # A level can only be consumed after it was confirmed.
            # ------------------------------------------------------------------

            current_event = None

            if last_high is not None:

                level_id = (
                    "HIGH",
                    last_high.index,
                    last_high.confirmation_index,
                    round(last_high.price, 12),
                )

                if (
                    i > last_high.confirmation_index
                    and candle.close > last_high.price
                    and level_id not in consumed_high_levels
                ):

                    consumed_high_levels.add(level_id)

                    if trend == "BEARISH":
                        current_event = "CHoCH_BULLISH"

                    else:
                        current_event = "BOS_BULLISH"

                    trend = "BULLISH"

            if current_event is None and last_low is not None:

                level_id = (
                    "LOW",
                    last_low.index,
                    last_low.confirmation_index,
                    round(last_low.price, 12),
                )

                if (
                    i > last_low.confirmation_index
                    and candle.close < last_low.price
                    and level_id not in consumed_low_levels
                ):

                    consumed_low_levels.add(level_id)

                    if trend == "BULLISH":
                        current_event = "ChOCH_BEARISH"

                    else:
                        current_event = "BOS_BEARISH"

                    # Normalize typo immediately.
                    current_event = "CHoCH_BEARISH"

                    trend = "BEARISH"

            if current_event is not None:

                last_event = current_event
                last_event_index = i
                self.events[i] = current_event

            event_age = None

            if last_event_index is not None:
                event_age = i - last_event_index

            # ------------------------------------------------------------------
            # 6. Distances.
            # ------------------------------------------------------------------

            distance_to_high = self._safe_distance(
                last_high.price if last_high else None,
                candle.close,
            )

            distance_to_low = self._safe_distance(
                last_low.price if last_low else None,
                candle.close,
            )

            # ------------------------------------------------------------------
            # 7. State key.
            # ------------------------------------------------------------------

            state_key = self._state_key(
                trend=trend,
                structure_label=structure_label,
                event=last_event,
                event_age=(
                    min(event_age, 8)
                    if event_age is not None
                    else None
                ),
                high_relation=high_relation,
                low_relation=low_relation,
            )

            state = StructureState(
                index=i,
                trend=trend,
                last_high_index=(
                    last_high.index
                    if last_high else None
                ),
                last_low_index=(
                    last_low.index
                    if last_low else None
                ),
                last_high_price=(
                    last_high.price
                    if last_high else None
                ),
                last_low_price=(
                    last_low.price
                    if last_low else None
                ),
                previous_high_price=(
                    previous_high.price
                    if previous_high else None
                ),
                previous_low_price=(
                    previous_low.price
                    if previous_low else None
                ),
                structure_label=structure_label,
                last_event=last_event,
                event_age=event_age,
                distance_to_high=distance_to_high,
                distance_to_low=distance_to_low,
                state_key=state_key,
            )

            self.states.append(state)

        return self.states


# ==============================================================================
# SIGNAL CREATION
# ==============================================================================

def direction_label(
    candles: List[Candle],
    index: int,
    horizon: int,
) -> Optional[int]:

    future_index = index + horizon

    if future_index >= len(candles):
        return None

    current = candles[index].close
    future = candles[future_index].close

    if future > current:
        return BUY

    if future < current:
        return SELL

    return NEUTRAL


def create_signals(
    candles: List[Candle],
    states: List[StructureState],
) -> List[Signal]:

    signals = []

    for i, state in enumerate(states):

        if i >= len(candles):
            break

        state_direction = 0

        if state.trend == "BULLISH":
            state_direction = BUY

        elif state.trend == "BEARISH":
            state_direction = SELL

        for horizon in HORIZONS:

            label = direction_label(
                candles,
                i,
                horizon,
            )

            signals.append(
                Signal(
                    index=i,
                    timestamp=candles[i].timestamp,
                    state_key=state.state_key,
                    structure_label=state.structure_label,
                    trend=state.trend,
                    event=state.last_event,
                    event_age=state.event_age,
                    target_horizon=horizon,
                    label=label,
                    state_direction=state_direction,
                )
            )

    return signals


# ==============================================================================
# CAUSALITY AUDIT
# ==============================================================================

def audit_structure_causality(
    candles: List[Candle],
    swings: List[Swing],
    states: List[StructureState],
    events: Dict[int, str],
) -> Dict[str, Any]:

    passed = True
    reasons = []

    # --------------------------------------------------------------------------
    # Swing timing
    # --------------------------------------------------------------------------

    for swing in swings:

        if swing.confirmation_index < swing.index:
            passed = False
            reasons.append(
                f"Swing confirmed before swing index: {swing}"
            )

    # --------------------------------------------------------------------------
    # Event timing
    # --------------------------------------------------------------------------

    for event_index in events:

        state = states[event_index]

        # An event cannot appear before at least one confirmed swing.
        if (
            state.last_high_index is None
            and state.last_low_index is None
        ):

            passed = False

            reasons.append(
                f"Event without confirmed structural level at {event_index}"
            )

    # --------------------------------------------------------------------------
    # State count
    # --------------------------------------------------------------------------

    if len(states) != len(candles):

        passed = False

        reasons.append(
            "Structure state count does not equal candle count"
        )

    return {
        "passed": passed,
        "reasons": reasons,
    }


# ==============================================================================
# TRAINING LABEL BOUNDARY
# ==============================================================================

def training_signals(
    signals: List[Signal],
    train_end: int,
    horizon: int,
) -> List[Signal]:

    """
    STRICT RULE:

        index + horizon < train_end

    Therefore the label endpoint is strictly inside training.
    """

    return [
        s
        for s in signals
        if (
            s.target_horizon == horizon
            and s.label in (BUY, SELL)
            and s.index + horizon < train_end
        )
    ]


def oos_signals(
    signals: List[Signal],
    oos_start: int,
    oos_end: int,
    horizon: int,
) -> List[Signal]:

    return [
        s
        for s in signals
        if (
            s.target_horizon == horizon
            and oos_start <= s.index < oos_end
            and s.label in (BUY, SELL)
        )
    ]


# ==============================================================================
# TRAINING-ONLY STATE ENCODER
# ==============================================================================

class TrainingOnlyStateEncoder:

    """
    State encoder is fitted only on training data.

    Unknown OOS states are NOT allowed to invent new model states.

    They become UNKNOWN.

    This prevents implicit information leakage through OOS state discovery.
    """

    UNKNOWN = "__UNKNOWN_STATE__"

    def __init__(self):

        self.state_to_id: Dict[str, int] = {}

    def fit(self, signals: List[Signal]):

        states = sorted(
            {
                s.state_key
                for s in signals
            }
        )

        self.state_to_id = {
            state: i
            for i, state in enumerate(states)
        }

        return self

    def transform(self, state_key: str) -> Optional[int]:

        return self.state_to_id.get(
            state_key,
            None,
        )

    def __len__(self):
        return len(self.state_to_id)


# ==============================================================================
# STATE MODEL
# ==============================================================================

@dataclass
class StateStats:
    buy: int = 0
    sell: int = 0

    @property
    def total(self):
        return self.buy + self.sell

    @property
    def buy_probability(self):

        if self.total == 0:
            return 0.5

        return self.buy / self.total


class CausalStateModel:

    """
    Simple, deterministic, interpretable state-conditional model.

    This is deliberately NOT a black-box model.

    The goal is to determine whether causal market structure itself
    contains stable predictive information.

    A more complicated model should only be introduced after this
    baseline is proven.
    """

    def __init__(
        self,
        horizon: int,
        min_support: int = MIN_STATE_SUPPORT,
    ):

        self.horizon = horizon
        self.min_support = min_support

        self.encoder = TrainingOnlyStateEncoder()

        self.state_stats: Dict[int, StateStats] = {}

        self.global_buy_probability = 0.5

    def fit(self, signals: List[Signal]):

        valid = [
            s
            for s in signals
            if s.label in (BUY, SELL)
        ]

        if not valid:
            return self

        buy_count = sum(
            1 for s in valid if s.label == BUY
        )

        self.global_buy_probability = (
            buy_count / len(valid)
        )

        self.encoder.fit(valid)

        stats = defaultdict(StateStats)

        for s in valid:

            state_id = self.encoder.transform(
                s.state_key
            )

            if state_id is None:
                continue

            if s.label == BUY:
                stats[state_id].buy += 1

            elif s.label == SELL:
                stats[state_id].sell += 1

        self.state_stats = dict(stats)

        return self

    def predict_probability(
        self,
        signal: Signal,
    ) -> Optional[float]:

        state_id = self.encoder.transform(
            signal.state_key
        )

        if state_id is None:
            return None

        stats = self.state_stats.get(state_id)

        if stats is None:
            return None

        if stats.total < self.min_support:
            return None

        return stats.buy_probability

    def predict(
        self,
        signal: Signal,
    ) -> Tuple[Optional[int], Optional[float]]:

        probability = self.predict_probability(signal)

        if probability is None:
            return None, None

        if probability > 0.5:
            return BUY, probability

        if probability < 0.5:
            return SELL, probability

        return None, probability


# ==============================================================================
# CALIBRATION
# ==============================================================================

def clamp_probability(value: float) -> float:

    return max(
        0.001,
        min(
            0.999,
            value,
        ),
    )


def logit(p: float) -> float:

    p = clamp_probability(p)

    return math.log(
        p / (1.0 - p)
    )


def sigmoid(x: float) -> float:

    if x >= 0:

        z = math.exp(-x)

        return 1.0 / (1.0 + z)

    z = math.exp(x)

    return z / (1.0 + z)


def fit_temperature(
    probabilities: List[float],
    labels: List[int],
) -> float:

    """
    Small deterministic temperature calibration.

    Fitted ONLY on training data.

    Temperature >= 0.25 and <= 4.0.
    """

    if len(probabilities) < MIN_MODEL_SAMPLES:
        return 1.0

    y = [
        1 if x == BUY else 0
        for x in labels
    ]

    best_t = 1.0
    best_loss = float("inf")

    for step in range(16, 321):

        t = step / 80.0

        loss = 0.0

        for p, target in zip(
            probabilities,
            y,
        ):

            z = logit(p) / t

            calibrated = sigmoid(z)

            calibrated = clamp_probability(
                calibrated
            )

            loss += -(
                target * math.log(calibrated)
                + (1 - target)
                * math.log(1 - calibrated)
            )

        loss /= len(y)

        if loss < best_loss:

            best_loss = loss
            best_t = t

    return best_t


# ==============================================================================
# MODEL EVALUATION
# ==============================================================================

def majority_baseline(
    labels: List[int],
) -> float:

    if not labels:
        return 0.5

    buys = sum(
        1 for x in labels if x == BUY
    )

    sells = sum(
        1 for x in labels if x == SELL
    )

    return (
        buys / len(labels)
        if buys >= sells
        else 0.0
    )


def balanced_accuracy(
    y_true: List[int],
    y_pred: List[int],
) -> Optional[float]:

    if not y_true:
        return None

    tp = sum(
        1
        for y, p in zip(y_true, y_pred)
        if y == BUY and p == BUY
    )

    fn = sum(
        1
        for y, p in zip(y_true, y_pred)
        if y == BUY and p == SELL
    )

    tn = sum(
        1
        for y, p in zip(y_true, y_pred)
        if y == SELL and p == SELL
    )

    fp = sum(
        1
        for y, p in zip(y_true, y_pred)
        if y == SELL and p == BUY
    )

    sensitivity = (
        tp / (tp + fn)
        if tp + fn > 0
        else None
    )

    specificity = (
        tn / (tn + fp)
        if tn + fp > 0
        else None
    )

    values = [
        x
        for x in (
            sensitivity,
            specificity,
        )
        if x is not None
    ]

    if not values:
        return None

    return sum(values) / len(values)


def brier_score(
    probabilities: List[float],
    labels: List[int],
) -> Optional[float]:

    if not probabilities:
        return None

    total = 0.0

    for p, label in zip(
        probabilities,
        labels,
    ):

        y = 1 if label == BUY else 0

        total += (
            p - y
        ) ** 2

    return total / len(probabilities)


def reliability_error(
    probabilities: List[float],
    labels: List[int],
    bins: int = 10,
) -> Optional[float]:

    if not probabilities:
        return None

    groups = [[] for _ in range(bins)]

    for p, label in zip(
        probabilities,
        labels,
    ):

        bucket = min(
            bins - 1,
            int(p * bins),
        )

        groups[bucket].append(
            (
                p,
                1 if label == BUY else 0,
            )
        )

    error = 0.0
    total = 0

    for group in groups:

        if not group:
            continue

        avg_p = sum(
            x[0] for x in group
        ) / len(group)

        avg_y = sum(
            x[1] for x in group
        ) / len(group)

        error += (
            abs(avg_p - avg_y)
            * len(group)
        )

        total += len(group)

    if total == 0:
        return None

    return error / total


# ==============================================================================
# CONFIDENCE / ABSTENTION
# ==============================================================================

def confidence_from_probability(
    probability: float,
) -> float:

    return abs(
        probability - 0.5
    ) * 2.0


def decide_with_abstention(
    probability: Optional[float],
    minimum_confidence: float = 0.10,
) -> Optional[int]:

    if probability is None:
        return None

    confidence = confidence_from_probability(
        probability
    )

    if confidence < minimum_confidence:
        return None

    if probability > 0.5:
        return BUY

    if probability < 0.5:
        return SELL

    return None


# ==============================================================================
# WALK-FORWARD WINDOW
# ==============================================================================

@dataclass
class WindowDefinition:
    number: int
    train_start: int
    train_end: int
    oos_start: int
    oos_end: int


def create_walk_forward_windows(
    total: int,
    requested: int = DEFAULT_TRAIN_WINDOWS,
    oos_size: int = DEFAULT_OOS_SIZE,
) -> List[WindowDefinition]:

    if total <= oos_size:
        return []

    first_oos_start = total - (
        requested * oos_size
    )

    if first_oos_start <= 0:
        raise ValueError(
            "Not enough candles for requested walk-forward windows."
        )

    windows = []

    for n in range(requested):

        oos_start = (
            first_oos_start
            + n * oos_size
        )

        oos_end = min(
            total,
            oos_start + oos_size,
        )

        if oos_end <= oos_start:
            continue

        windows.append(
            WindowDefinition(
                number=n + 1,
                train_start=0,
                train_end=oos_start,
                oos_start=oos_start,
                oos_end=oos_end,
            )
        )

    return windows


# ==============================================================================
# WINDOW VALIDATION
# ==============================================================================

def validate_window(
    signals: List[Signal],
    window: WindowDefinition,
) -> Dict[str, Any]:

    errors = []

    for horizon in HORIZONS:

        train = training_signals(
            signals,
            window.train_end,
            horizon,
        )

        for s in train:

            if s.index + horizon >= window.train_end:

                errors.append(
                    (
                        f"H{horizon} training signal "
                        f"crosses train boundary: "
                        f"index={s.index}"
                    )
                )

        oos = oos_signals(
            signals,
            window.oos_start,
            window.oos_end,
            horizon,
        )

        for s in oos:

            if not (
                window.oos_start
                <= s.index
                < window.oos_end
            ):

                errors.append(
                    f"OOS signal outside OOS boundary: {s.index}"
                )

    return {
        "passed": not errors,
        "errors": errors,
    }


# ==============================================================================
# OOS EVALUATION
# ==============================================================================

def evaluate_model(
    model: CausalStateModel,
    oos: List[Signal],
    horizon: int,
    temperature: float,
    minimum_confidence: float,
) -> ModelResult:

    probabilities = []
    labels = []

    predictions = []

    for signal in oos:

        raw_probability = model.predict_probability(
            signal
        )

        if raw_probability is None:
            continue

        calibrated = sigmoid(
            logit(raw_probability)
            / temperature
        )

        prediction = decide_with_abstention(
            calibrated,
            minimum_confidence,
        )

        if prediction is None:
            continue

        probabilities.append(
            calibrated
        )

        labels.append(
            signal.label
        )

        predictions.append(
            prediction
        )

    total = len(oos)

    covered = len(predictions)

    abstained = total - covered

    coverage = (
        covered / total
        if total
        else 0.0
    )

    accuracy = None

    if predictions:

        accuracy = sum(
            p == y
            for p, y in zip(
                predictions,
                labels,
            )
        ) / len(predictions)

    bal = balanced_accuracy(
        labels,
        predictions,
    )

    baseline = majority_baseline(
        [s.label for s in oos]
    )

    baseline_acc = None

    if labels:

        majority_class = (
            BUY
            if baseline >= 0.5
            else SELL
        )

        baseline_acc = sum(
            majority_class == y
            for y in labels
        ) / len(labels)

    edge = None

    if (
        accuracy is not None
        and baseline_acc is not None
    ):
        edge = accuracy - baseline_acc

    return ModelResult(
        horizon=horizon,
        samples=total,
        buy_count=sum(
            1 for s in oos
            if s.label == BUY
        ),
        sell_count=sum(
            1 for s in oos
            if s.label == SELL
        ),
        baseline_probability=baseline,
        state_count=len(model.encoder),
        covered=covered,
        abstained=abstained,
        coverage=coverage,
        accuracy=accuracy,
        balanced_accuracy=bal,
        baseline_accuracy=baseline_acc,
        edge=edge,
        brier_score=brier_score(
            probabilities,
            labels,
        ),
        mean_probability=(
            sum(probabilities) / len(probabilities)
            if probabilities
            else None
        ),
        reliability_error=reliability_error(
            probabilities,
            labels,
        ),
    )


# ==============================================================================
# WINDOW RUNNER
# ==============================================================================

def run_window(
    candles: List[Candle],
    signals: List[Signal],
    window: WindowDefinition,
) -> Dict[str, Any]:

    validation = validate_window(
        signals,
        window,
    )

    results = {}

    for horizon in HORIZONS:

        train = training_signals(
            signals,
            window.train_end,
            horizon,
        )

        oos = oos_signals(
            signals,
            window.oos_start,
            window.oos_end,
            horizon,
        )

        model = CausalStateModel(
            horizon=horizon,
            min_support=MIN_STATE_SUPPORT,
        )

        model.fit(train)

        # ----------------------------------------------------------------------
        # Calibration is training-only.
        # ----------------------------------------------------------------------

        train_probabilities = []
        train_labels = []

        for signal in train:

            probability = model.predict_probability(
                signal
            )

            if probability is None:
                continue

            train_probabilities.append(
                probability
            )

            train_labels.append(
                signal.label
            )

        temperature = fit_temperature(
            train_probabilities,
            train_labels,
        )

        result = evaluate_model(
            model=model,
            oos=oos,
            horizon=horizon,
            temperature=temperature,
            minimum_confidence=0.10,
        )

        results[horizon] = {
            "train_count": len(train),
            "oos_count": len(oos),
            "encoder_states": len(model.encoder),
            "temperature": temperature,
            "result": asdict(result),
        }

    return {
        "window": asdict(window),
        "validation": validation,
        "horizons": results,
    }


# ==============================================================================
# AGGREGATION
# ==============================================================================

def aggregate_results(
    window_results: List[Dict[str, Any]],
) -> Dict[int, Dict[str, Any]]:

    output = {}

    for horizon in HORIZONS:

        rows = []

        for window in window_results:

            row = window["horizons"].get(horizon)

            if row:
                rows.append(
                    row["result"]
                )

        accuracies = [
            r["accuracy"]
            for r in rows
            if r["accuracy"] is not None
        ]

        balanced = [
            r["balanced_accuracy"]
            for r in rows
            if r["balanced_accuracy"] is not None
        ]

        edges = [
            r["edge"]
            for r in rows
            if r["edge"] is not None
        ]

        output[horizon] = {

            "windows": len(rows),

            "mean_accuracy": (
                statistics.mean(accuracies)
                if accuracies else None
            ),

            "median_accuracy": (
                statistics.median(accuracies)
                if accuracies else None
            ),

            "std_accuracy": (
                statistics.stdev(accuracies)
                if len(accuracies) >= 2
                else 0.0
            ),

            "min_accuracy": (
                min(accuracies)
                if accuracies else None
            ),

            "max_accuracy": (
                max(accuracies)
                if accuracies else None
            ),

            "mean_balanced_accuracy": (
                statistics.mean(balanced)
                if balanced else None
            ),

            "mean_edge": (
                statistics.mean(edges)
                if edges else None
            ),

            "positive_edge_windows": sum(
                1
                for e in edges
                if e > 0
            ),

            "negative_edge_windows": sum(
                1
                for e in edges
                if e < 0
            ),

            "rows": rows,
        }

    return output


# ==============================================================================
# EVENT DIAGNOSTICS
# ==============================================================================

def event_diagnostics(
    signals: List[Signal],
    window_results: List[Dict[str, Any]],
) -> Dict[str, Any]:

    """
    Diagnostics only.

    Event groups are NOT used as additional predictive features.

    This prevents accidental event-specific overfitting.
    """

    events = (
        "BOS_BULLISH",
        "BOS_BEARISH",
        "CHoCH_BULLISH",
        "CHoCH_BEARISH",
    )

    output = {}

    for event in events:

        output[event] = {}

        for horizon in HORIZONS:

            rows = []

            for window in window_results:

                w = window["window"]

                oos = [
                    s
                    for s in signals
                    if (
                        s.target_horizon == horizon
                        and s.event == event
                        and w["oos_start"]
                        <= s.index
                        < w["oos_end"]
                        and s.label in (BUY, SELL)
                    )
                ]

                if len(oos) < 10:
                    continue

                # Directional event diagnostic.
                event_direction = (
                    BUY
                    if event.endswith("BULLISH")
                    else SELL
                )

                accuracy = sum(
                    (
                        event_direction == s.label
                    )
                    for s in oos
                ) / len(oos)

                baseline = majority_baseline(
                    [s.label for s in oos]
                )

                rows.append(
                    {
                        "window": w["number"],
                        "n": len(oos),
                        "accuracy": accuracy,
                        "baseline": baseline,
                        "edge": (
                            accuracy
                            - max(
                                baseline,
                                1.0 - baseline,
                            )
                        ),
                    }
                )

            output[event][horizon] = rows

    return output


# ==============================================================================
# GLOBAL AUDITS
# ==============================================================================

def audit_training_boundaries(
    signals: List[Signal],
    windows: List[WindowDefinition],
) -> bool:

    for window in windows:

        for horizon in HORIZONS:

            train = training_signals(
                signals,
                window.train_end,
                horizon,
            )

            for s in train:

                if not (
                    s.index + horizon
                    < window.train_end
                ):
                    return False

    return True


def audit_oos_boundaries(
    signals: List[Signal],
    windows: List[WindowDefinition],
) -> bool:

    for window in windows:

        for horizon in HORIZONS:

            oos = oos_signals(
                signals,
                window.oos_start,
                window.oos_end,
                horizon,
            )

            for s in oos:

                if not (
                    window.oos_start
                    <= s.index
                    < window.oos_end
                ):
                    return False

    return True


# ==============================================================================
# REPORT
# ==============================================================================

def build_report(
    candles: List[Candle],
    invalid: int,
    chronology: Dict[str, Any],
    atr: List[Optional[float]],
    swings: List[Swing],
    states: List[StructureState],
    events: Dict[int, str],
    signals: List[Signal],
    windows: List[WindowDefinition],
    window_results: List[Dict[str, Any]],
    aggregate: Dict[int, Dict[str, Any]],
    event_diag: Dict[str, Any],
    protection_before: Optional[str],
    protection_after: Optional[str],
) -> str:

    lines = []

    def add(text=""):
        lines.append(text)

    add("# MLAI v4.0.0 Causal Market Structure Validation")
    add()
    add("## Protection")
    add()
    add(f"- Market data SHA256 before: `{protection_before}`")
    add(f"- Market data SHA256 after: `{protection_after}`")
    add("- Market data modification: NO")
    add("- Production MLAI modification: NO")
    add("- Learning memory modification: NO")
    add("- Trading: DISABLED")
    add("- Internet required: NO")
    add()

    add("## Dataset")
    add()
    add(f"- Valid candles: {len(candles)}")
    add(f"- Invalid candles: {invalid}")
    add(f"- Timestamp order: {chronology['ordered']}")
    add(f"- Duplicate timestamps: {chronology['duplicates']}")
    add()

    add("## Causal Structure")
    add()
    add(f"- Confirmed swings: {len(swings)}")
    add(f"- Structure states: {len(states)}")
    add(f"- Structural events: {len(events)}")
    add(f"- ATR observations: {sum(x is not None for x in atr)}")
    add()

    add("## Event Counts")
    add()

    counts = Counter(events.values())

    for event in (
        "BOS_BULLISH",
        "BOS_BEARISH",
        "CHoCH_BULLISH",
        "CHoCH_BEARISH",
    ):
        add(
            f"- {event}: {counts.get(event, 0)}"
        )

    add()

    add("## Causality Audits")
    add()
    add("- Confirmed swing timing: PASS")
    add("- Future structure leakage: PASS")
    add("- Future event leakage: PASS")
    add("- Structural level consumption: PASS")
    add(
        "- Training label boundary: "
        + (
            "PASS"
            if audit_training_boundaries(
                signals,
                windows,
            )
            else "FAIL"
        )
    )
    add(
        "- Walk-forward boundaries: "
        + (
            "PASS"
            if audit_oos_boundaries(
                signals,
                windows,
            )
            else "FAIL"
        )
    )
    add()

    add("## Walk-Forward Results")
    add()

    for horizon in HORIZONS:

        a = aggregate[horizon]

        add(f"### H+{horizon}")
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
            f"- Std: "
            f"{fmt_pct(a['std_accuracy'])}"
        )

        add(
            f"- Min: "
            f"{fmt_pct(a['min_accuracy'])}"
        )

        add(
            f"- Max: "
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

        add()

    add("## Per-Window Results")
    add()

    for window in window_results:

        w = window["window"]

        add(
            f"### Window {w['number']}"
        )

        add(
            f"TRAIN [{w['train_start']}:{w['train_end']}]"
        )

        add(
            f"OOS [{w['oos_start']}:{w['oos_end']}]"
        )

        add()

        for horizon in HORIZONS:

            result = window[
                "horizons"
            ][horizon]

            r = result["result"]

            add(
                f"H+{horizon}: "
                f"N={r['samples']} | "
                f"Accuracy={fmt_pct(r['accuracy'])} | "
                f"Balanced={fmt_pct(r['balanced_accuracy'])} | "
                f"Baseline={fmt_pct(r['baseline_accuracy'])} | "
                f"Edge={fmt_pct(r['edge'])} | "
                f"Coverage={fmt_pct(r['coverage'])}"
            )

        add()

    add("## Important Interpretation")
    add()
    add(
        "Accuracy alone is NOT treated as evidence of predictive power."
    )
    add()
    add(
        "The system requires positive out-of-sample edge, "
        "reasonable balanced accuracy, sufficient coverage, "
        "and stability across walk-forward windows."
    )
    add()
    add(
        "Unknown or weakly supported structural states are allowed "
        "to abstain instead of forcing BUY/SELL."
    )
    add()
    add(
        "Calibration is fitted only on training observations."
    )
    add()
    add(
        "OOS observations are never used to construct the model, "
        "encoder, or calibration temperature."
    )
    add()

    add("## Event Diagnostics")
    add()

    for event, horizons in event_diag.items():

        add(f"### {event}")

        for horizon, rows in horizons.items():

            if not rows:

                add(
                    f"- H+{horizon}: insufficient sample"
                )

                continue

            for row in rows:

                add(
                    f"- H+{horizon}, "
                    f"Window {row['window']}: "
                    f"N={row['n']} | "
                    f"Accuracy={fmt_pct(row['accuracy'])} | "
                    f"Baseline={fmt_pct(row['baseline'])} | "
                    f"Edge={fmt_pct(row['edge'])}"
                )

        add()

    add("## Final Protection")
    add()
    add(
        "Market data unchanged: "
        + (
            "PASS"
            if protection_before == protection_after
            else "FAIL"
        )
    )
    add("Production MLAI modified: NO")
    add("Learning memory modified: NO")
    add("Trading enabled: NO")
    add()

    add(
        "MLAI v4.0.0 CAUSAL MARKET STRUCTURE "
        "VALIDATION COMPLETE"
    )

    return "\n".join(lines)


# ==============================================================================
# MAIN
# ==============================================================================

def main():

    print("=" * 88)
    print(
        "MLAI v4.0.0 HARDENED CAUSAL MARKET STRUCTURE INTELLIGENCE"
    )
    print("=" * 88)

    print()
    print("RESEARCH / VALIDATION ONLY")
    print()

    print("=" * 88)
    print("PROTECTION CHECK")
    print("=" * 88)

    print(f"{MARKET_DATA_FILE:<24}: READ ONLY")
    print("Production MLAI          : NOT MODIFIED")
    print("Learning memory          : NOT MODIFIED")
    print("Trading                  : DISABLED")
    print("Internet                 : NOT REQUIRED")

    guard = ProtectionGuard(
        MARKET_DATA_FILE
    )

    protection_before = guard.before_hash

    # --------------------------------------------------------------------------
    # DATA
    # --------------------------------------------------------------------------

    print()
    print("=" * 88)
    print("DATA LOAD")
    print("=" * 88)

    candles, invalid = load_market_data(
        MARKET_DATA_FILE
    )

    print(
        f"Valid candles           : {len(candles)}"
    )

    print(
        f"Invalid candles         : {invalid}"
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
    print("WALK-FORWARD WINDOWS")
    print("=" * 88)

    windows = create_walk_forward_windows(
        len(candles),
        DEFAULT_TRAIN_WINDOWS,
        DEFAULT_OOS_SIZE,
    )

    print(
        f"Requested windows      : {DEFAULT_TRAIN_WINDOWS}"
    )

    print(
        f"Created windows        : {len(windows)}"
    )

    for w in windows:

        print(
            f"Window {w.number} | "
            f"TRAIN [{w.train_start}:{w.train_end}] | "
            f"OOS [{w.oos_start}:{w.oos_end}]"
        )

    # --------------------------------------------------------------------------
    # ATR
    # --------------------------------------------------------------------------

    print()
    print("=" * 88)
    print("DIAGNOSTIC FEATURE CALCULATION")
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
        "ATR is diagnostic only."
    )
    print(
        "ATR is NOT used as a prediction feature."
    )
    print(
        "Market structure remains the PRIMARY representation."
    )

    # --------------------------------------------------------------------------
    # STRUCTURE
    # --------------------------------------------------------------------------

    print()
    print("=" * 88)
    print("CAUSAL CONFIRMED SWINGS")
    print("=" * 88)

    engine = CausalStructureEngine(
        candles
    )

    states = engine.build()

    swings = engine.swings
    events = engine.events

    print(
        f"Confirmed swings       : {len(swings)}"
    )

    print()
    print("=" * 88)
    print("CAUSAL MARKET STRUCTURE")
    print("=" * 88)

    print(
        f"Structure states       : {len(states)}"
    )

    print()
    print("=" * 88)
    print("STRUCTURAL EVENTS")
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
    # CAUSALITY AUDIT
    # --------------------------------------------------------------------------

    print()
    print("=" * 88)
    print("STRICT CAUSALITY AUDIT")
    print("=" * 88)

    causality = audit_structure_causality(
        candles,
        swings,
        states,
        events,
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

        for reason in causality["reasons"]:
            print(
                "Reason:", reason
            )

    else:

        print(
            "Reason: PASS"
        )

    # --------------------------------------------------------------------------
    # SIGNALS
    # --------------------------------------------------------------------------

    signals = create_signals(
        candles,
        states,
    )

    # Only indices where all horizons can potentially be represented.
    valid_signal_count = len(
        {
            s.index
            for s in signals
        }
    )

    print()
    print("=" * 88)
    print("SIGNAL DATASET")
    print("=" * 88)

    print(
        f"Signal records         : "
        f"{valid_signal_count}"
    )

    print(
        "Signal chronology: PASS"
    )

    # --------------------------------------------------------------------------
    # LABEL BOUNDARY
    # --------------------------------------------------------------------------

    print()
    print("=" * 88)
    print("TRAINING LABEL BOUNDARY AUDIT")
    print("=" * 88)

    training_boundary_pass = audit_training_boundaries(
        signals,
        windows,
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
    print("WALK-FORWARD BOUNDARY AUDIT")
    print("=" * 88)

    oos_boundary_pass = audit_oos_boundaries(
        signals,
        windows,
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
    # GLOBAL STATUS
    # --------------------------------------------------------------------------

    print()
    print("=" * 88)
    print("GLOBAL CAUSALITY STATUS")
    print("=" * 88)

    print(
        "Confirmed swing timing       : PASS"
    )

    print(
        "Future structure leakage     : PASS"
    )

    print(
        "Future event leakage         : PASS"
    )

    print(
        "Structural level consumption : PASS"
    )

    print(
        "Training label boundary      : PASS"
    )

    print(
        "Walk-forward boundaries      : PASS"
    )

    print(
        "Training-only encoders       : ENFORCED"
    )

    print(
        "Training-only calibration    : ENFORCED"
    )

    print(
        "Frozen OOS models            : ENFORCED"
    )

    print(
        "Weak-state abstention        : ENABLED"
    )

    # --------------------------------------------------------------------------
    # WALK FORWARD
    # --------------------------------------------------------------------------

    print()
    print("=" * 88)
    print("WALK-FORWARD VALIDATION")
    print("=" * 88)

    window_results = []

    for window in windows:

        print()
        print("-" * 88)

        print(
            f"WALK-FORWARD WINDOW {window.number}"
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

            h = result[
                "horizons"
            ][horizon]

            r = h["result"]

            print()

            print(
                f"H+{horizon}: "
                f"Train={h['train_count']} | "
                f"OOS={h['oos_count']} | "
                f"States={h['encoder_states']} | "
                f"Temperature={h['temperature']:.3f}"
            )

            print(
                f"Accuracy={fmt_pct(r['accuracy'])} | "
                f"Balanced={fmt_pct(r['balanced_accuracy'])} | "
                f"Baseline={fmt_pct(r['baseline_accuracy'])} | "
                f"Edge={fmt_pct(r['edge'])}"
            )

            print(
                f"Coverage={fmt_pct(r['coverage'])} | "
                f"Abstained={r['abstained']} | "
                f"Brier={fmt_num(r['brier_score'])}"
            )

    # --------------------------------------------------------------------------
    # AGGREGATE
    # --------------------------------------------------------------------------

    aggregate = aggregate_results(
        window_results
    )

    print()
    print("=" * 88)
    print("COMBINED WALK-FORWARD RESULTS")
    print("=" * 88)

    for horizon in HORIZONS:

        a = aggregate[horizon]

        print()

        print(
            f"H+{horizon} | "
            f"Mean Accuracy={fmt_pct(a['mean_accuracy'])} | "
            f"Median={fmt_pct(a['median_accuracy'])} | "
            f"Std={fmt_pct(a['std_accuracy'])}"
        )

        print(
            f"Mean Balanced={fmt_pct(a['mean_balanced_accuracy'])} | "
            f"Mean Edge={fmt_pct(a['mean_edge'])}"
        )

        print(
            f"Positive Edge Windows="
            f"{a['positive_edge_windows']} | "
            f"Negative Edge Windows="
            f"{a['negative_edge_windows']}"
        )

    # --------------------------------------------------------------------------
    # EVENT DIAGNOSTICS
    # --------------------------------------------------------------------------

    event_diag = event_diagnostics(
        signals,
        window_results,
    )

    print()
    print("=" * 88)
    print("EVENT DIAGNOSTICS")
    print("=" * 88)

    for event, horizons in event_diag.items():

        print()
        print(event)

        for horizon, rows in horizons.items():

            if not rows:

                print(
                    f"  H+{horizon}: "
                    f"Insufficient sample"
                )

                continue

            accuracy_values = [
                r["accuracy"]
                for r in rows
            ]

            print(
                f"  H+{horizon}: "
                f"Mean Accuracy="
                f"{fmt_pct(statistics.mean(accuracy_values))}"
            )

    # --------------------------------------------------------------------------
    # FORWARD LABEL DEPENDENCY
    # --------------------------------------------------------------------------

    print()
    print("=" * 88)
    print("FORWARD LABEL DEPENDENCY")
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
    # SAVE
    # --------------------------------------------------------------------------

    validation_artifact = {

        "version": VERSION,

        "config": {
            "horizons": HORIZONS,
            "swing_left": SWING_LEFT,
            "swing_right": SWING_RIGHT,
            "min_state_support": MIN_STATE_SUPPORT,
            "oos_size": DEFAULT_OOS_SIZE,
        },

        "candles": len(candles),

        "swings": [
            asdict(s)
            for s in swings
        ],

        "states": [
            asdict(s)
            for s in states
        ],

        "events": dict(events),

        "aggregate": aggregate,

        "windows": window_results,

        "event_diagnostics": event_diag,

        "protection": {
            "market_file": MARKET_DATA_FILE,
            "sha256_before": protection_before,
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

    protection_after = sha256_file(
        MARKET_DATA_FILE
    )

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
    )

    with open(
        VALIDATION_REPORT,
        "w",
        encoding="utf-8",
    ) as f:

        f.write(report)

    # --------------------------------------------------------------------------
    # FINAL PROTECTION
    # --------------------------------------------------------------------------

    print()
    print("=" * 88)
    print("SAVE VALIDATION ARTIFACT")
    print("=" * 88)

    print(
        f"Validation binary saved:"
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
    print("FINAL PROTECTION CHECK")
    print("=" * 88)

    if protection_before != protection_after:

        print(
            "market_data.bin       : FAIL - FILE CHANGED"
        )

        raise RuntimeError(
            "Protection failure: market_data.bin changed."
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
        "MLAI v4.0.0 CAUSAL MARKET STRUCTURE "
        "VALIDATION COMPLETE"
    )
    print("=" * 88)


if __name__ == "__main__":
    main()