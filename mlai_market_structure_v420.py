"""
MLAI v4.2.0 — ADVANCED CAUSAL HISTORICAL EXPERIENCE RETRIEVAL
Research / validation only.

This phase validates the Historical Experience layer before probability,
scenario reasoning, explanation, multi-timeframe reasoning, or live learning.

Included:
- causal MarketState
- causal structure / sequence / regime
- ATR-normalized outcomes
- historical experience records
- temporal eligibility barrier
- coarse-to-fine retrieval
- multi-layer similarity
- recent causal path similarity
- temporal episode de-duplication
- supporting/conflicting evidence
- sparse evidence handling
- retrieval vs baseline comparison
- similarity-bucket diagnostics
- fixed training-only null retrieval sanity test
- strict walk-forward OOS validation
- immutable market-data protection
"""

from __future__ import annotations

import hashlib
import math
import os
import pickle
from collections import Counter
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

VERSION = "4.2.0"
MARKET_DATA_FILE = "market_data.bin"
VALIDATION_BIN = "MLAI_V420_ADVANCED_CAUSAL_HISTORICAL_EXPERIENCE_RETRIEVAL.bin"
VALIDATION_REPORT = "MLAI_V420_ADVANCED_CAUSAL_HISTORICAL_EXPERIENCE_RETRIEVAL_REPORT.md"

HORIZONS = (4, 8, 16)
SWING_LEFT = 3
SWING_RIGHT = 3
DEFAULT_TRAIN_WINDOWS = 5
DEFAULT_OOS_SIZE = 81

NEUTRAL_ATR_BAND = 0.25
RETRIEVAL_TOP_K = 16
MIN_RETRIEVAL_MATCHES = 6
MIN_HISTORY_GAP = max(HORIZONS)
EPISODE_GAP = 8
PATH_LENGTH = 12
NULL_PERMUTATIONS = 25
EPS = 1e-12

# v4.1.6 retrieval design: fixed before OOS evaluation; never OOS-tuned.
V416_CONTEXT_MIN_MATCHES = 12
V416_CONTEXT_REQUIRED = 2
V416_PATH_DECAY = 0.86
V416_PATH_RETURN_WEIGHT = 0.40
V416_PATH_SHAPE_WEIGHT = 0.25
V416_PATH_CANDLE_WEIGHT = 0.20
V416_PATH_DIRECTION_WEIGHT = 0.15
V416_NUMERIC_WEIGHT = 0.24
V416_PATH_WEIGHT = 0.34
V416_STRUCTURE_WEIGHT = 0.16
V416_CONTEXT_WEIGHT = 0.16
V416_CANDLE_WEIGHT = 0.10
V416_TEMPORAL_WEIGHT = 0.00
V416_PREDICT_TEMPERATURE = 0.10
V416_PREDICT_MIN_PROBABILITY = 0.42
V416_PREDICT_MIN_MARGIN = 0.08
V416_DISCRIMINATION_RANDOM_TRIALS = 12

# Fixed, predeclared retrieval weights. Never OOS-tuned.
WEIGHT_STRUCTURE = 0.20
WEIGHT_SEQUENCE = 0.15
WEIGHT_REGIME = 0.15
WEIGHT_LOCATION = 0.10
WEIGHT_MOMENTUM = 0.10
WEIGHT_VOLATILITY = 0.10
WEIGHT_CANDLE = 0.05
WEIGHT_PATH = 0.15

SIMILARITY_BUCKETS = (
    (0.00, 0.50, "LOW"),
    (0.50, 0.60, "LOW_MODERATE"),
    (0.60, 0.70, "MODERATE"),
    (0.70, 0.80, "MODERATE_STRONG"),
    (0.80, 1.01, "STRONG"),
)


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
    r1: float
    r3: float
    r8: float
    r16: float
    path_vector: Tuple[Tuple[float, float, float, float], ...]
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
    episode_id: int
    state_key: Tuple[Any, ...]
    sequence_state: str
    regime: str
    structure_event: str
    location: str
    momentum_state: str
    volatility_ratio: float
    body_ratio: float
    range_ratio: float
    r1: float
    r3: float
    r8: float
    r16: float
    path_vector: Tuple[Tuple[float, float, float, float], ...]
    horizon: int
    outcome: Outcome


@dataclass
class SimilarityMatch:
    index: int
    episode_id: int
    similarity: float
    structure_similarity: float
    sequence_similarity: float
    regime_similarity: float
    location_similarity: float
    momentum_similarity: float
    volatility_similarity: float
    candle_similarity: float
    path_similarity: float


@dataclass
class RetrievalResult:
    horizon: int
    query_index: int
    raw_candidates: int
    deduplicated_matches: int
    top_similarity: float
    mean_similarity: float
    level: str
    evidence: str
    sparse_warning: bool
    regime_agreement: float
    structure_agreement: float
    context_agreement: float
    up_share: float
    down_share: float
    neutral_share: float
    mean_atr_return: Optional[float]
    mean_mfe_atr: Optional[float]
    mean_mae_atr: Optional[float]
    supporting_matches: int
    conflicting_matches: int
    historical_min_index: Optional[int]
    historical_max_index: Optional[int]
    selected_match_indices: List[int]


class ProtectionGuard:
    def __init__(self, path: str):
        if not os.path.exists(path):
            raise FileNotFoundError(path)
        self.path = path
        self.before_hash = sha256_file(path)

    def verify_unchanged(self) -> bool:
        return self.before_hash == sha256_file(self.path)


def sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def safe_div(a: float, b: float) -> float:
    return 0.0 if abs(b) < EPS else a / b


def mean_or_zero(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return min(high, max(low, value))


def fmt_pct(value: Optional[float]) -> str:
    return "N/A" if value is None else f"{100.0 * value:.2f}%"


def fmt_num(value: Optional[float]) -> str:
    return "N/A" if value is None else f"{value:.4f}"


def _get_value(obj: Any, names: Sequence[str], default: Any = None) -> Any:
    if isinstance(obj, dict):
        lower = {str(k).lower(): v for k, v in obj.items()}
        for name in names:
            if name.lower() in lower:
                return lower[name.lower()]
        return default
    for name in names:
        if hasattr(obj, name):
            return getattr(obj, name)
    return default


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _normalize_candle(raw: Any, index: int) -> Optional[Candle]:
    if isinstance(raw, (list, tuple)) and len(raw) >= 5:
        if len(raw) >= 6:
            timestamp = raw[0]
            o, h, l, c, v = raw[1:6]
        else:
            timestamp = index
            o, h, l, c = raw[:4]
            v = 0.0
        try:
            o, h, l, c, v = map(float, (o, h, l, c, v))
            if not all(math.isfinite(x) for x in (o, h, l, c, v)):
                return None
            if h < max(o, c) or l > min(o, c) or h < l:
                return None
            return Candle(index, timestamp, o, h, l, c, v)
        except Exception:
            return None

    timestamp = _get_value(raw, ("timestamp", "time", "datetime", "date", "ts"), index)
    o = _get_value(raw, ("open", "o"))
    h = _get_value(raw, ("high", "h"))
    l = _get_value(raw, ("low", "l"))
    c = _get_value(raw, ("close", "c"))
    v = _get_value(raw, ("volume", "vol", "v"), 0.0)

    if None in (o, h, l, c):
        return None

    o, h, l, c, v = map(lambda x: _to_float(x, float("nan")), (o, h, l, c, v))
    if not all(math.isfinite(x) for x in (o, h, l, c, v)):
        return None
    if h < max(o, c) or l > min(o, c) or h < l:
        return None
    return Candle(index, timestamp, o, h, l, c, v)


def load_market_data(path: str) -> Tuple[List[Candle], int]:
    with open(path, "rb") as f:
        obj = pickle.load(f)

    if isinstance(obj, dict):
        for key in ("candles", "data", "rows", "ohlcv", "market_data"):
            if key in obj and isinstance(obj[key], (list, tuple)):
                obj = obj[key]
                break

    if not isinstance(obj, (list, tuple)):
        raise ValueError("Unsupported market_data.bin format.")

    candles: List[Candle] = []
    invalid = 0
    for raw in obj:
        candle = _normalize_candle(raw, len(candles))
        if candle is None:
            invalid += 1
        else:
            candles.append(candle)

    for i, candle in enumerate(candles):
        candle.index = i
    return candles, invalid


def audit_chronology(candles: Sequence[Candle]) -> Dict[str, bool]:
    ordered = True
    duplicates = False
    previous = None
    for candle in candles:
        if previous is not None:
            try:
                ordered &= not (candle.timestamp < previous)
                duplicates |= candle.timestamp == previous
            except Exception:
                pass
        previous = candle.timestamp
    return {"ordered": ordered, "duplicates": duplicates}


def create_walk_forward_windows(n: int, count: int, oos_size: int) -> List[WalkForwardWindow]:
    if n <= count * oos_size:
        raise ValueError("Insufficient candles for requested walk-forward setup.")
    initial_train = n - count * oos_size
    windows = []
    for i in range(count):
        train_end = initial_train + i * oos_size
        oos_start = train_end
        oos_end = min(n, oos_start + oos_size)
        if oos_end > oos_start:
            windows.append(WalkForwardWindow(i + 1, 0, train_end, oos_start, oos_end))
    return windows


def calculate_atr(candles: Sequence[Candle], period: int = 14) -> List[Optional[float]]:
    output: List[Optional[float]] = [None] * len(candles)
    true_ranges: List[float] = []
    for i, candle in enumerate(candles):
        if i == 0:
            tr = candle.high - candle.low
        else:
            previous_close = candles[i - 1].close
            tr = max(
                candle.high - candle.low,
                abs(candle.high - previous_close),
                abs(candle.low - previous_close),
            )
        true_ranges.append(max(tr, EPS))
        if len(true_ranges) >= period:
            output[i] = sum(true_ranges[-period:]) / period
    return output


class CausalStructureEngine:
    def __init__(self, candles: Sequence[Candle]):
        self.candles = candles
        self.swings: List[Swing] = []
        self.events: Dict[int, str] = {}
        self.states: List[StructureState] = []
        self.high_used = set()
        self.low_used = set()

    def _is_confirmed_high(self, j: int) -> bool:
        if j < SWING_LEFT or j + SWING_RIGHT >= len(self.candles):
            return False
        price = self.candles[j].high
        return all(
            k == j or self.candles[k].high < price
            for k in range(j - SWING_LEFT, j + SWING_RIGHT + 1)
        )

    def _is_confirmed_low(self, j: int) -> bool:
        if j < SWING_LEFT or j + SWING_RIGHT >= len(self.candles):
            return False
        price = self.candles[j].low
        return all(
            k == j or self.candles[k].low > price
            for k in range(j - SWING_LEFT, j + SWING_RIGHT + 1)
        )

    def build(self) -> List[StructureState]:
        last_high: Optional[Swing] = None
        last_low: Optional[Swing] = None
        high_label = "UNKNOWN"
        low_label = "UNKNOWN"
        trend = "NEUTRAL"
        event_index: Optional[int] = None
        structure_start = 0

        for i, candle in enumerate(self.candles):
            j = i - SWING_RIGHT

            if j >= SWING_LEFT:
                if self._is_confirmed_high(j):
                    label = "HH" if last_high is None or self.candles[j].high > last_high.price else "LH"
                    last_high = Swing(j, i, "HIGH", self.candles[j].high, label)
                    self.swings.append(last_high)
                    high_label = label

                if self._is_confirmed_low(j):
                    label = "HL" if last_low is None or self.candles[j].low > last_low.price else "LL"
                    last_low = Swing(j, i, "LOW", self.candles[j].low, label)
                    self.swings.append(last_low)
                    low_label = label

            event = "NONE"

            if (
                last_high is not None
                and i > last_high.confirmation_index
                and candle.close > last_high.price
                and (last_high.pivot_index, "HIGH") not in self.high_used
            ):
                event = "BOS_BULLISH" if trend in ("BULLISH", "NEUTRAL") else "CHoCH_BULLISH"
                self.high_used.add((last_high.pivot_index, "HIGH"))
                trend = "BULLISH"
                event_index = i
                structure_start = i

            if (
                last_low is not None
                and i > last_low.confirmation_index
                and candle.close < last_low.price
                and (last_low.pivot_index, "LOW") not in self.low_used
            ):
                candidate = "BOS_BEARISH" if trend in ("BEARISH", "NEUTRAL") else "CHoCH_BEARISH"
                if event == "NONE":
                    event = candidate
                self.low_used.add((last_low.pivot_index, "LOW"))
                trend = "BEARISH"
                event_index = i
                structure_start = i

            event_age = None if event_index is None else i - event_index
            self.events[i] = event

            self.states.append(
                StructureState(
                    index=i,
                    trend=trend,
                    last_high=last_high.price if last_high else None,
                    last_low=last_low.price if last_low else None,
                    last_high_index=last_high.pivot_index if last_high else None,
                    last_low_index=last_low.pivot_index if last_low else None,
                    high_label=high_label,
                    low_label=low_label,
                    event=event,
                    event_index=event_index,
                    event_age=event_age,
                    structure_age=i - structure_start,
                )
            )

        return self.states


def audit_structure_causality(
    candles: Sequence[Candle],
    swings: Sequence[Swing],
    states: Sequence[StructureState],
    events: Dict[int, str],
) -> Dict[str, Any]:
    reasons = []
    lookup = {(s.pivot_index, s.kind): s for s in swings}

    for swing in swings:
        if swing.confirmation_index < swing.pivot_index + SWING_RIGHT:
            reasons.append(f"Swing {swing.pivot_index} confirmed too early.")

    for state in states:
        if state.last_high_index is not None:
            swing = lookup.get((state.last_high_index, "HIGH"))
            if swing and swing.confirmation_index > state.index:
                reasons.append(f"Future high visible at state {state.index}.")

        if state.last_low_index is not None:
            swing = lookup.get((state.last_low_index, "LOW"))
            if swing and swing.confirmation_index > state.index:
                reasons.append(f"Future low visible at state {state.index}.")

        if events.get(state.index, "NONE") != "NONE":
            if state.event_index is None or state.event_index > state.index:
                reasons.append(f"Future event visible at state {state.index}.")

    return {"passed": not reasons, "reasons": reasons}


def rolling_return(candles: Sequence[Candle], index: int, lookback: int) -> float:
    if index < lookback:
        return 0.0
    return safe_div(
        candles[index].close - candles[index - lookback].close,
        candles[index - lookback].close,
    )


def classify_regime(state: StructureState, volatility_ratio: float, r8: float) -> str:
    if volatility_ratio >= 1.35:
        return "VOL_EXPANSION"
    if volatility_ratio <= 0.75:
        return "VOL_CONTRACTION"
    if state.trend == "BULLISH" and r8 > 0:
        return "TRENDING_UP"
    if state.trend == "BEARISH" and r8 < 0:
        return "TRENDING_DOWN"
    if state.trend == "NEUTRAL":
        return "RANGING"
    return "TRANSITION"


def classify_momentum(r1: float, r3: float, r8: float) -> str:
    if r1 > 0 and r3 > 0 and r8 > 0:
        return "BULLISH_ACCELERATION"
    if r1 < 0 and r3 < 0 and r8 < 0:
        return "BEARISH_ACCELERATION"
    if r8 > 0 and r1 < 0:
        return "BULLISH_MOMENTUM_LOSS"
    if r8 < 0 and r1 > 0:
        return "BEARISH_MOMENTUM_LOSS"
    return "MIXED"


def update_sequence(history: Sequence[Candle], state: StructureState) -> str:
    if len(history) < 3:
        return "INITIAL"
    if state.event in ("BOS_BULLISH", "CHoCH_BULLISH"):
        return "BULLISH_BREAK"
    if state.event in ("BOS_BEARISH", "CHoCH_BEARISH"):
        return "BEARISH_BREAK"
    if history[-1].close > history[-2].close and history[-2].close <= history[-3].close:
        return "BULLISH_RESPONSE"
    if history[-1].close < history[-2].close and history[-2].close >= history[-3].close:
        return "BEARISH_RESPONSE"

    current_range = max(history[-1].high - history[-1].low, EPS)
    current_body = abs(history[-1].close - history[-1].open)
    if current_body < 0.25 * current_range:
        return "COMPRESSION"
    if state.trend == "BULLISH":
        return "RECOVERY_OR_CONTINUATION"
    if state.trend == "BEARISH":
        return "SELLING_OR_CONTINUATION"
    return "MIXED_SEQUENCE"


def build_path_vector(
    candles: Sequence[Candle],
    atr: Sequence[Optional[float]],
    index: int,
) -> Tuple[Tuple[float, float, float, float], ...]:
    rows = []
    start = max(0, index - PATH_LENGTH + 1)

    for current in range(start, index + 1):
        current_atr = atr[current] if atr[current] is not None else max(candles[current].high - candles[current].low, EPS)
        candle = candles[current]
        previous_close = candles[current - 1].close if current > 0 else candle.close

        normalized_return = safe_div(candle.close - previous_close, current_atr)
        normalized_range = safe_div(candle.high - candle.low, current_atr)
        direction = 1.0 if candle.close > candle.open else -1.0 if candle.close < candle.open else 0.0
        body_ratio = safe_div(abs(candle.close - candle.open), current_atr)

        rows.append((normalized_return, normalized_range, direction, body_ratio))

    while len(rows) < PATH_LENGTH:
        rows.insert(0, (0.0, 0.0, 0.0, 0.0))

    return tuple(rows)


def build_market_states(
    candles: Sequence[Candle],
    states: Sequence[StructureState],
    atr: Sequence[Optional[float]],
) -> List[MarketState]:
    output = []

    for i, candle in enumerate(candles):
        state = states[i]
        current_atr = atr[i] if atr[i] is not None else max(candle.high - candle.low, EPS)

        r1 = rolling_return(candles, i, 1)
        r3 = rolling_return(candles, i, 3)
        r8 = rolling_return(candles, i, 8)
        r16 = rolling_return(candles, i, 16)

        recent_ranges = [
            safe_div(candles[j].high - candles[j].low, max(candles[j].close, EPS))
            for j in range(max(0, i - 7), i + 1)
        ]
        older_ranges = [
            safe_div(candles[j].high - candles[j].low, max(candles[j].close, EPS))
            for j in range(max(0, i - 31), max(0, i - 7))
        ]

        recent_vol = mean_or_zero(recent_ranges)
        older_vol = mean_or_zero(older_ranges)
        volatility_ratio = safe_div(
            recent_vol,
            older_vol if older_vol > EPS else recent_vol + EPS,
        )

        if state.last_low is not None and abs(candle.close - state.last_low) <= current_atr:
            location = "NEAR_SUPPORT"
        elif state.last_high is not None and abs(candle.close - state.last_high) <= current_atr:
            location = "NEAR_RESISTANCE"
        else:
            location = "MID_STRUCTURE"

        sequence = update_sequence(candles[: i + 1], state)
        regime = classify_regime(state, volatility_ratio, r8)
        momentum = classify_momentum(r1, r3, r8)
        candle_direction = "UP" if candle.close > candle.open else "DOWN" if candle.close < candle.open else "FLAT"
        path_vector = build_path_vector(candles, atr, i)

        state_key = (
            state.trend,
            state.event,
            state.high_label,
            state.low_label,
            location,
            regime,
            momentum,
            sequence,
        )

        output.append(
            MarketState(
                index=i,
                timestamp=candle.timestamp,
                instrument="XAUUSD",
                timeframe="UNKNOWN",
                candle_direction=candle_direction,
                body_ratio=safe_div(abs(candle.close - candle.open), current_atr),
                range_ratio=safe_div(candle.high - candle.low, current_atr),
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
                r1=r1,
                r3=r3,
                r8=r8,
                r16=r16,
                path_vector=path_vector,
                state_key=state_key,
                availability_index=i,
            )
        )

    return output


def make_outcome(
    candles: Sequence[Candle],
    atr: Sequence[Optional[float]],
    index: int,
    horizon: int,
) -> Optional[Outcome]:
    target = index + horizon
    if target >= len(candles):
        return None

    current_atr = atr[index]
    if current_atr is None or current_atr <= EPS:
        return None

    base = candles[index].close
    future_close = candles[target].close
    raw_return = safe_div(future_close - base, base)
    atr_return = safe_div(future_close - base, current_atr)

    if atr_return > NEUTRAL_ATR_BAND:
        direction = "UP"
    elif atr_return < -NEUTRAL_ATR_BAND:
        direction = "DOWN"
    else:
        direction = "NEUTRAL"

    future_high = max(c.high for c in candles[index + 1 : target + 1])
    future_low = min(c.low for c in candles[index + 1 : target + 1])

    return Outcome(
        direction=direction,
        raw_return=raw_return,
        atr_return=atr_return,
        mfe_atr=safe_div(future_high - base, current_atr),
        mae_atr=safe_div(future_low - base, current_atr),
    )


def assign_episode_ids(states: Sequence[MarketState]) -> Dict[int, int]:
    """
    Deterministic temporal episode segmentation.

    An episode changes when a material causal state transition occurs.
    EPISODE_GAP is used as an additional temporal grouping constraint during
    de-duplication; it is not used to inspect future information.
    """
    episode_ids: Dict[int, int] = {}
    episode = 0
    last_change = 0

    for i, state in enumerate(states):
        if i == 0:
            episode_ids[i] = episode
            continue

        previous = states[i - 1]
        changed = (
            state.trend != previous.trend
            or state.regime != previous.regime
            or state.sequence_state != previous.sequence_state
            or state.structure_event != "NONE"
        )

        if changed:
            episode += 1
            last_change = i
        elif i - last_change >= EPISODE_GAP:
            episode += 1
            last_change = i

        episode_ids[i] = episode

    return episode_ids


def build_experience_records(
    candles: Sequence[Candle],
    atr: Sequence[Optional[float]],
    states: Sequence[MarketState],
    episode_ids: Dict[int, int],
    start: int,
    train_end: int,
    horizon: int,
) -> List[ExperienceRecord]:
    """Create records whose entire future outcome completes before train_end."""
    records = []
    safe_end = min(train_end - horizon, len(candles) - horizon)

    if safe_end <= start:
        return records

    for i in range(start, safe_end):
        outcome = make_outcome(candles, atr, i, horizon)
        if outcome is None:
            continue

        state = states[i]
        records.append(
            ExperienceRecord(
                index=i,
                episode_id=episode_ids[i],
                state_key=state.state_key,
                sequence_state=state.sequence_state,
                regime=state.regime,
                structure_event=state.structure_event,
                location=state.location,
                momentum_state=state.momentum_state,
                volatility_ratio=state.volatility_ratio,
                body_ratio=state.body_ratio,
                range_ratio=state.range_ratio,
                r1=state.r1,
                r3=state.r3,
                r8=state.r8,
                r16=state.r16,
                path_vector=state.path_vector,
                horizon=horizon,
                outcome=outcome,
            )
        )

    return records


def _v416_context_matches(current: MarketState, record: ExperienceRecord) -> int:
    return sum(
        (
            current.trend == record.state_key[0],
            current.structure_event == record.structure_event,
            current.high_label == record.state_key[2],
            current.low_label == record.state_key[3],
            current.location == record.location,
            current.regime == record.regime,
            current.momentum_state == record.momentum_state,
            current.sequence_state == record.sequence_state,
        )
    )


def coarse_filter(
    current: MarketState,
    records: Sequence[ExperienceRecord],
    query_index: int,
) -> List[ExperienceRecord]:
    """Causal candidate gate that preserves discrimination.

    The old implementation admitted a record when *any one* of three broad
    categorical fields matched.  That made the candidate pool too generic.
    v4.1.6 requires multiple independent context agreements when enough data
    exists, with a controlled fallback only when the historical pool is sparse.
    """
    eligible = [
        record
        for record in records
        if record.index < query_index
        and query_index - record.index >= MIN_HISTORY_GAP
    ]

    strict = [
        record
        for record in eligible
        if _v416_context_matches(current, record) >= V416_CONTEXT_REQUIRED
    ]
    if len(strict) >= V416_CONTEXT_MIN_MATCHES:
        return strict

    relaxed = [
        record
        for record in eligible
        if _v416_context_matches(current, record) >= 1
    ]
    if len(relaxed) >= V416_CONTEXT_MIN_MATCHES:
        return relaxed

    return eligible


def _v416_exp_similarity(value_a: float, value_b: float, scale: float) -> float:
    """Compare two scalar observations with a fixed exponential distance scale.

    The v4.1.6 similarity call sites pass (current_value, historical_value,
    scale).  The previous v4.2.0 file declared a two-argument helper, which
    made the inherited causal similarity layer internally inconsistent.
    This implementation restores the intended three-argument contract and
    computes similarity from the actual pairwise difference.
    """
    try:
        a = float(value_a)
        b = float(value_b)
        s = abs(float(scale))
    except (TypeError, ValueError):
        return 0.0
    if not (math.isfinite(a) and math.isfinite(b) and math.isfinite(s)):
        return 0.0
    return math.exp(-abs(a - b) / max(s, EPS))


def _v416_weighted_mean(values: Sequence[float], decay: float = V416_PATH_DECAY) -> float:
    if not values:
        return 0.0
    weights = [decay ** (len(values) - 1 - i) for i in range(len(values))]
    total = sum(weights)
    return safe_div(sum(v * w for v, w in zip(values, weights)), total)


def _v416_path_similarity(current: MarketState, record: ExperienceRecord) -> Dict[str, float]:
    """Compare the recent causal path as a trajectory, not as an unweighted mean."""
    cur = current.path_vector
    hist = record.path_vector
    if not cur or not hist:
        return {"total": 0.0, "returns": 0.0, "shape": 0.0, "candle": 0.0, "direction": 0.0}

    rows = min(len(cur), len(hist))
    cur = cur[-rows:]
    hist = hist[-rows:]

    return_sims = []
    range_sims = []
    body_sims = []
    direction_sims = []
    cur_cum = 0.0
    hist_cum = 0.0
    trajectory_sims = []

    for c, h in zip(cur, hist):
        cr, c_range, c_dir, c_body = c
        hr, h_range, h_dir, h_body = h
        return_sims.append(_v416_exp_similarity(cr, hr, 0.65))
        range_sims.append(_v416_exp_similarity(c_range, h_range, 0.80))
        body_sims.append(_v416_exp_similarity(c_body, h_body, 0.70))
        direction_sims.append(1.0 if c_dir == h_dir else 0.0)
        cur_cum += cr
        hist_cum += hr
        trajectory_sims.append(_v416_exp_similarity(cur_cum, hist_cum, 1.25))

    returns = _v416_weighted_mean(return_sims)
    shape = _v416_weighted_mean(trajectory_sims)
    candle = _v416_weighted_mean([
        0.65 * a + 0.35 * b for a, b in zip(range_sims, body_sims)
    ])
    direction = _v416_weighted_mean(direction_sims)
    total = (
        V416_PATH_RETURN_WEIGHT * returns
        + V416_PATH_SHAPE_WEIGHT * shape
        + V416_PATH_CANDLE_WEIGHT * candle
        + V416_PATH_DIRECTION_WEIGHT * direction
    )
    return {
        "total": clamp(total),
        "returns": clamp(returns),
        "shape": clamp(shape),
        "candle": clamp(candle),
        "direction": clamp(direction),
    }


def path_row_similarity(
    current_row: Tuple[float, float, float, float],
    historical_row: Tuple[float, float, float, float],
) -> float:
    c = current_row
    h = historical_row
    return (
        0.40 * _v416_exp_similarity(c[0], h[0], 0.65)
        + 0.25 * _v416_exp_similarity(c[1], h[1], 0.80)
        + 0.20 * _v416_exp_similarity(c[3], h[3], 0.70)
        + 0.15 * (1.0 if c[2] == h[2] else 0.0)
    )


def path_similarity(current: MarketState, record: ExperienceRecord) -> float:
    return _v416_path_similarity(current, record)["total"]


def _v416_numeric_similarity(current: MarketState, record: ExperienceRecord) -> float:
    # Fixed scales are intentionally broad enough to avoid treating tiny
    # floating-point differences as different regimes, while still separating
    # materially different multi-scale returns.
    sims = [
        _v416_exp_similarity(current.r1, record.r1, 0.0030),
        _v416_exp_similarity(current.r3, record.r3, 0.0060),
        _v416_exp_similarity(current.r8, record.r8, 0.0120),
        _v416_exp_similarity(current.r16, record.r16, 0.0200),
        _v416_exp_similarity(current.volatility_ratio, record.volatility_ratio, 0.35),
    ]
    return clamp(_v416_weighted_mean(sims, 0.90))


def _v416_structure_similarity(current: MarketState, record: ExperienceRecord) -> float:
    values = [
        1.0 if current.trend == record.state_key[0] else 0.0,
        1.0 if current.structure_event == record.structure_event else 0.0,
        1.0 if current.high_label == record.state_key[2] else 0.0,
        1.0 if current.low_label == record.state_key[3] else 0.0,
    ]
    return clamp(sum(values) / len(values))


def _v416_context_similarity(current: MarketState, record: ExperienceRecord) -> float:
    values = [
        1.0 if current.sequence_state == record.sequence_state else 0.0,
        1.0 if current.regime == record.regime else 0.0,
        1.0 if current.location == record.location else 0.0,
        1.0 if current.momentum_state == record.momentum_state else 0.0,
    ]
    return clamp(sum(values) / len(values))


def _v416_candle_similarity(current: MarketState, record: ExperienceRecord) -> float:
    return clamp(
        0.45 * _v416_exp_similarity(current.body_ratio, record.body_ratio, 0.75)
        + 0.35 * _v416_exp_similarity(current.range_ratio, record.range_ratio, 0.90)
        + 0.20 * (1.0 if current.candle_direction == record.state_key[0] else 0.0)
    )


def similarity_score(current: MarketState, record: ExperienceRecord) -> Dict[str, float]:
    """v4.1.6 fixed multi-scale similarity.

    The score is built from independent evidence families.  No outcome field
    is inspected here, so the ranking remains strictly causal.
    """
    structure = _v416_structure_similarity(current, record)
    context = _v416_context_similarity(current, record)
    numeric = _v416_numeric_similarity(current, record)
    path_parts = _v416_path_similarity(current, record)
    path = path_parts["total"]
    candle = _v416_candle_similarity(current, record)

    # Direction is compared explicitly because state_key[0] is trend, not
    # candle direction.  This keeps the candle term semantically correct.
    candle_direction = 1.0 if current.candle_direction == (
        "UP" if record.path_vector[-1][2] > 0 else "DOWN" if record.path_vector[-1][2] < 0 else "FLAT"
    ) else 0.0
    candle = clamp(0.80 * candle + 0.20 * candle_direction)

    total = (
        V416_NUMERIC_WEIGHT * numeric
        + V416_PATH_WEIGHT * path
        + V416_STRUCTURE_WEIGHT * structure
        + V416_CONTEXT_WEIGHT * context
        + V416_CANDLE_WEIGHT * candle
    )

    return {
        "total": clamp(total),
        "structure": structure,
        "sequence": 1.0 if current.sequence_state == record.sequence_state else 0.0,
        "regime": 1.0 if current.regime == record.regime else 0.0,
        "location": 1.0 if current.location == record.location else 0.0,
        "momentum": 1.0 if current.momentum_state == record.momentum_state else 0.0,
        "volatility": _v416_exp_similarity(current.volatility_ratio, record.volatility_ratio, 0.35),
        "candle": candle,
        "path": path,
        "numeric": numeric,
        "context": context,
        "path_returns": path_parts["returns"],
        "path_shape": path_parts["shape"],
        "path_direction": path_parts["direction"],
    }


def select_episode_representatives(matches: Sequence[SimilarityMatch]) -> List[SimilarityMatch]:
    """Select at most one representative per historical episode."""
    by_episode: Dict[int, SimilarityMatch] = {}
    for match in matches:
        previous = by_episode.get(match.episode_id)
        if previous is None or (match.similarity, match.index) > (previous.similarity, previous.index):
            by_episode[match.episode_id] = match
    selected = list(by_episode.values())
    selected.sort(key=lambda item: (item.similarity, item.index), reverse=True)
    return selected[:RETRIEVAL_TOP_K]


def retrieve_historical_experience(
    current: MarketState,
    records: Sequence[ExperienceRecord],
    horizon: int,
    query_index: int,
) -> RetrievalResult:
    candidates: List[SimilarityMatch] = []
    candidate_records = coarse_filter(current, records, query_index)

    for record in candidate_records:
        components = similarity_score(current, record)
        candidates.append(
            SimilarityMatch(
                index=record.index,
                episode_id=record.episode_id,
                similarity=components["total"],
                structure_similarity=components["structure"],
                sequence_similarity=components["sequence"],
                regime_similarity=components["regime"],
                location_similarity=components["location"],
                momentum_similarity=components["momentum"],
                volatility_similarity=components["volatility"],
                candle_similarity=components["candle"],
                path_similarity=components["path"],
            )
        )

    candidates.sort(key=lambda item: (item.similarity, item.index), reverse=True)
    raw_candidate_count = len(candidates)
    selected = select_episode_representatives(candidates)
    record_by_index = {record.index: record for record in candidate_records}
    selected_rows = [
        (match, record_by_index[match.index])
        for match in selected
        if match.index in record_by_index
    ]

    if not selected_rows:
        return RetrievalResult(
            horizon=horizon,
            query_index=query_index,
            raw_candidates=raw_candidate_count,
            deduplicated_matches=0,
            top_similarity=0.0,
            mean_similarity=0.0,
            level="NONE",
            evidence="NONE",
            sparse_warning=True,
            regime_agreement=0.0,
            structure_agreement=0.0,
            context_agreement=0.0,
            up_share=0.0,
            down_share=0.0,
            neutral_share=0.0,
            mean_atr_return=None,
            mean_mfe_atr=None,
            mean_mae_atr=None,
            supporting_matches=0,
            conflicting_matches=0,
            historical_min_index=None,
            historical_max_index=None,
            selected_match_indices=[],
        )

    # Similarity weighting is deliberately steep enough to reward genuinely
    # close analogues, while episode de-duplication prevents a single episode
    # from dominating the evidence.
    weights = [max(match.similarity, EPS) ** 4 for match, _ in selected_rows]
    total_weight = sum(weights)

    shares = {
        cls: safe_div(
            sum(weight for weight, (_, record) in zip(weights, selected_rows)
                if record.outcome.direction == cls),
            total_weight,
        )
        for cls in ("UP", "DOWN", "NEUTRAL")
    }

    dominant = max(shares.items(), key=lambda item: (item[1], item[0]))[0]
    supporting_matches = sum(1 for _, record in selected_rows if record.outcome.direction == dominant)
    conflicting_matches = len(selected_rows) - supporting_matches

    top_similarity = selected[0].similarity
    mean_similarity = mean_or_zero([match.similarity for match, _ in selected_rows])
    regime_agreement = mean_or_zero([match.regime_similarity for match, _ in selected_rows])
    structure_agreement = mean_or_zero([match.structure_similarity for match, _ in selected_rows])
    context_agreement = mean_or_zero([
        mean_or_zero([
            match.sequence_similarity,
            match.regime_similarity,
            match.location_similarity,
            match.momentum_similarity,
            match.path_similarity,
        ])
        for match, _ in selected_rows
    ])

    mean_atr_return = safe_div(sum(
        weight * (record.outcome.atr_return or 0.0)
        for weight, (_, record) in zip(weights, selected_rows)
    ), total_weight)
    mean_mfe_atr = safe_div(sum(
        weight * (record.outcome.mfe_atr or 0.0)
        for weight, (_, record) in zip(weights, selected_rows)
    ), total_weight)
    mean_mae_atr = safe_div(sum(
        weight * (record.outcome.mae_atr or 0.0)
        for weight, (_, record) in zip(weights, selected_rows)
    ), total_weight)

    if len(selected_rows) < MIN_RETRIEVAL_MATCHES:
        level = "SPARSE"
    elif top_similarity >= 0.78:
        level = "STRONG_SIMILARITY"
    elif top_similarity >= 0.68:
        level = "MODERATE_STRONG"
    elif top_similarity >= 0.58:
        level = "MODERATE"
    else:
        level = "LOW_MODERATE"

    evidence = "LOW" if len(selected_rows) < MIN_RETRIEVAL_MATCHES else (
        "MODERATE" if top_similarity >= 0.68 else "LOW_TO_MODERATE"
    )
    indices = [record.index for _, record in selected_rows]

    return RetrievalResult(
        horizon=horizon,
        query_index=query_index,
        raw_candidates=raw_candidate_count,
        deduplicated_matches=len(selected_rows),
        top_similarity=top_similarity,
        mean_similarity=mean_similarity,
        level=level,
        evidence=evidence,
        sparse_warning=len(selected_rows) < MIN_RETRIEVAL_MATCHES,
        regime_agreement=regime_agreement,
        structure_agreement=structure_agreement,
        context_agreement=context_agreement,
        up_share=shares["UP"],
        down_share=shares["DOWN"],
        neutral_share=shares["NEUTRAL"],
        mean_atr_return=mean_atr_return,
        mean_mfe_atr=mean_mfe_atr,
        mean_mae_atr=mean_mae_atr,
        supporting_matches=supporting_matches,
        conflicting_matches=conflicting_matches,
        historical_min_index=min(indices) if indices else None,
        historical_max_index=max(indices) if indices else None,
        selected_match_indices=indices,
    )


def _v416_deterministic_indices(length: int, count: int, seed: int) -> List[int]:
    if length <= 0 or count <= 0:
        return []
    state = seed & 0xFFFFFFFF
    available = list(range(length))
    selected: List[int] = []
    count = min(count, length)
    for _ in range(count):
        state = (state * 1664525 + 1013904223) & 0xFFFFFFFF
        pos = state % len(available)
        selected.append(available.pop(pos))
    return selected


def v416_discrimination_test(
    current: MarketState,
    records: Sequence[ExperienceRecord],
    query_index: int,
    horizon: int,
) -> Dict[str, Any]:
    """Outcome-blind top-vs-random similarity discrimination test."""
    eligible = [
        r for r in records
        if r.index < query_index and query_index - r.index >= MIN_HISTORY_GAP
    ]
    if len(eligible) < max(MIN_RETRIEVAL_MATCHES, 10):
        return {
            "available": False,
            "real_top_similarity": None,
            "random_top_similarity_mean": None,
            "random_top_similarity_p95": None,
            "discrimination_lift": None,
        }

    ranked = sorted(
        ((similarity_score(current, r)["total"], r.index) for r in eligible),
        key=lambda x: (x[0], x[1]),
        reverse=True,
    )
    real_top = ranked[0][0]
    trial_count = min(RETRIEVAL_TOP_K, len(eligible))
    random_maxes = []
    for trial in range(V416_DISCRIMINATION_RANDOM_TRIALS):
        indices = _v416_deterministic_indices(
            len(eligible), trial_count, 7919 + query_index * 37 + horizon * 101 + trial
        )
        random_maxes.append(max(similarity_score(current, eligible[i])["total"] for i in indices))

    ordered = sorted(random_maxes)
    p95 = ordered[min(len(ordered) - 1, int(0.95 * (len(ordered) - 1)))]
    random_mean = mean_or_zero(random_maxes)
    return {
        "available": True,
        "real_top_similarity": real_top,
        "random_top_similarity_mean": random_mean,
        "random_top_similarity_p95": p95,
        "discrimination_lift": real_top - random_mean,
    }


def distribution_from_records(records: Sequence[ExperienceRecord]) -> Dict[str, float]:
    counts = Counter(record.outcome.direction for record in records)
    total = len(records)
    return {
        "UP": safe_div(counts["UP"], total),
        "DOWN": safe_div(counts["DOWN"], total),
        "NEUTRAL": safe_div(counts["NEUTRAL"], total),
    }


def conditional_baseline(
    current: MarketState,
    records: Sequence[ExperienceRecord],
) -> Tuple[str, Dict[str, float], int]:
    exact = [
        record for record in records
        if (
            record.regime == current.regime
            and record.structure_event == current.structure_event
            and record.sequence_state == current.sequence_state
        )
    ]
    if len(exact) >= MIN_RETRIEVAL_MATCHES:
        return "REGIME+EVENT+SEQUENCE", distribution_from_records(exact), len(exact)

    regime = [record for record in records if record.regime == current.regime]
    if len(regime) >= MIN_RETRIEVAL_MATCHES:
        return "REGIME", distribution_from_records(regime), len(regime)

    return "GLOBAL", distribution_from_records(records), len(records)


def brier(distribution: Dict[str, float], actual: str) -> float:
    return sum(
        (
            distribution[key]
            - (1.0 if key == actual else 0.0)
        ) ** 2
        for key in ("UP", "DOWN", "NEUTRAL")
    ) / 3.0


def log_loss(distribution: Dict[str, float], actual: str) -> float:
    probability = distribution.get(actual, 0.0)
    return -math.log(max(min(probability, 1.0 - 1e-6), 1e-6))


def evaluate_distribution(distribution: Dict[str, float], actual: str) -> Dict[str, Any]:
    ranked = sorted(distribution.items(), key=lambda x: (x[1], x[0]), reverse=True)
    predicted = ranked[0][0]
    return {
        "predicted": predicted,
        "actual": actual,
        "correct": predicted == actual,
        "brier": brier(distribution, actual),
        "log_loss": log_loss(distribution, actual),
    }


def deterministic_permutation(values: Sequence[str], seed: int) -> List[str]:
    items = list(values)
    state = seed & 0xFFFFFFFF
    for i in range(len(items) - 1, 0, -1):
        state = (state * 1664525 + 1013904223) & 0xFFFFFFFF
        j = state % (i + 1)
        items[i], items[j] = items[j], items[i]
    return items


def null_retrieval_sanity_test(
    current: MarketState,
    records: Sequence[ExperienceRecord],
    query_index: int,
    horizon: int,
) -> Dict[str, Any]:
    """Fixed training-only null sanity test; never used to tune retrieval."""
    eligible = [
        record
        for record in records
        if record.index < query_index
        and query_index - record.index >= MIN_HISTORY_GAP
    ]
    if len(eligible) < MIN_RETRIEVAL_MATCHES:
        return {
            "available": False,
            "permutations": 0,
            "real_max_share": None,
            "null_max_share_mean": None,
            "null_max_share_p95": None,
            "real_minus_null_mean": None,
        }

    real = retrieve_historical_experience(current, eligible, horizon, query_index)
    real_max_share = max(real.up_share, real.down_share, real.neutral_share)

    outcomes = [record.outcome.direction for record in eligible]
    null_max = []

    for permutation in range(NULL_PERMUTATIONS):
        shuffled = deterministic_permutation(
            outcomes,
            seed=1009 * (permutation + 1) + query_index,
        )
        permuted_records = []
        for record, direction in zip(eligible, shuffled):
            permuted_records.append(
                ExperienceRecord(
                    index=record.index,
                    episode_id=record.episode_id,
                    state_key=record.state_key,
                    sequence_state=record.sequence_state,
                    regime=record.regime,
                    structure_event=record.structure_event,
                    location=record.location,
                    momentum_state=record.momentum_state,
                    volatility_ratio=record.volatility_ratio,
                    body_ratio=record.body_ratio,
                    range_ratio=record.range_ratio,
                    r1=record.r1,
                    r3=record.r3,
                    r8=record.r8,
                    r16=record.r16,
                    path_vector=record.path_vector,
                    horizon=record.horizon,
                    outcome=Outcome(
                        direction=direction,
                        raw_return=record.outcome.raw_return,
                        atr_return=record.outcome.atr_return,
                        mfe_atr=record.outcome.mfe_atr,
                        mae_atr=record.outcome.mae_atr,
                    ),
                )
            )
        null_result = retrieve_historical_experience(
            current,
            permuted_records,
            horizon,
            query_index,
        )
        null_max.append(
            max(
                null_result.up_share,
                null_result.down_share,
                null_result.neutral_share,
            )
        )

    ordered = sorted(null_max)
    p95 = ordered[min(len(ordered) - 1, int(0.95 * (len(ordered) - 1)))]
    null_mean = mean_or_zero(null_max)

    return {
        "available": True,
        "permutations": len(null_max),
        "real_max_share": real_max_share,
        "null_max_share_mean": null_mean,
        "null_max_share_p95": p95,
        "real_minus_null_mean": real_max_share - null_mean,
    }


def bucket_name(similarity: float) -> str:
    for low, high, name in SIMILARITY_BUCKETS:
        if low <= similarity < high:
            return name
    return "UNKNOWN"



# =====================================================================
# REPAIRED PREDICTIVE LAYER
# Must be defined before main() because main() executes this path.
# =====================================================================

def _mlai_fix_safe_float(value, default=0.0):
    try:
        x = float(value)
        if math.isfinite(x):
            return x
    except Exception:
        pass
    return float(default)


def _mlai_fix_similarity_total(similarity):
    """
    Existing similarity_score() returns component scores.

    We deliberately avoid trusting an existing 'total' blindly.
    The repaired layer uses the component evidence when available.
    """
    if not isinstance(similarity, dict):
        return 0.0

    components = (
        "candle",
        "location",
        "momentum",
        "path",
        "regime",
        "sequence",
        "structure",
        "volatility",
    )

    values = []

    for key in components:
        if key in similarity:
            value = _mlai_fix_safe_float(similarity[key], 0.0)
            value = max(0.0, min(1.0, value))
            values.append(value)

    if values:
        return sum(values) / len(values)

    return max(
        0.0,
        min(1.0, _mlai_fix_safe_float(similarity.get("total"), 0.0))
    )


def _mlai_fix_outcome_direction(record):
    """
    Extract the direction from an ExperienceRecord/Outcome object
    without assuming one exact internal representation.
    """
    outcome = getattr(record, "outcome", record)

    value = getattr(outcome, "direction", None)

    if value is None:
        value = getattr(outcome, "label", None)

    if value is None:
        value = getattr(outcome, "class_name", None)

    if value is None:
        value = getattr(outcome, "target", None)

    if value is None:
        value = getattr(outcome, "prediction", None)

    if value is None:
        return None

    value = str(value).upper().strip()

    if value in ("UP", "DOWN", "NEUTRAL"):
        return value

    return None

def _mlai_fix_class_evidence(
    current,
    records,
    horizon,
    query_index,
    *,
    temperature=0.12,
    min_similarity=0.0,
):
    """
    Causal class-evidence estimator.

    Every record must already belong to the historical training/calibration
    set supplied by the caller.

    No record with an index >= query_index is allowed.

    Evidence is similarity-weighted but class-balanced so that a large
    historical class does not automatically dominate the result.

    The class prior is therefore not allowed to become the prediction.
    """

    buckets = {
        "UP": [],
        "DOWN": [],
        "NEUTRAL": [],
    }

    for record in records:
        record_index = getattr(record, "index", None)

        if record_index is None:
            record_index = getattr(record, "query_index", None)

        if record_index is not None:
            try:
                if int(record_index) >= int(query_index):
                    continue
            except Exception:
                continue

        direction = _mlai_fix_outcome_direction(record)

        if direction not in buckets:
            continue

        try:
            similarity = similarity_score(current, record)
        except Exception:
            continue

        score = _mlai_fix_similarity_total(similarity)

        if score < min_similarity:
            continue

        # Soft kernel.
        #
        # High similarity receives more weight, but we do not allow one
        # single historical record to dominate the entire prediction.
        distance = max(0.0, 1.0 - score)

        weight = math.exp(-distance / max(temperature, 1e-6))

        buckets[direction].append(weight)

    # No evidence.
    if not any(buckets.values()):
        return {
            "UP": 1.0 / 3.0,
            "DOWN": 1.0 / 3.0,
            "NEUTRAL": 1.0 / 3.0,
        }

    # -----------------------------------------------------------------
    # Class-balanced evidence
    # -----------------------------------------------------------------
    #
    # Raw vote totals are dangerous:
    #
    #   if UP has 200 records and DOWN has 100,
    #   raw similarity sums naturally favor UP.
    #
    # We normalize each class by its own historical support.
    #
    # This makes the model ask:
    #
    #   "How strongly does the retrieved evidence support this class?"
    #
    # rather than:
    #
    #   "Which class has the most records?"
    # -----------------------------------------------------------------

    evidence = {}

    for cls, values in buckets.items():
        if not values:
            evidence[cls] = 0.0
            continue

        support = len(values)

        # Mean evidence is intentionally used instead of raw sum.
        mean_weight = sum(values) / support

        # Mild support confidence.
        #
        # This prevents one matching record from receiving the same
        # credibility as a well-supported historical pattern.
        support_factor = 1.0 - math.exp(-support / 8.0)

        evidence[cls] = mean_weight * support_factor

    total = sum(evidence.values())

    if total <= 1e-12:
        return {
            "UP": 1.0 / 3.0,
            "DOWN": 1.0 / 3.0,
            "NEUTRAL": 1.0 / 3.0,
        }

    probabilities = {
        cls: evidence[cls] / total
        for cls in ("UP", "DOWN", "NEUTRAL")
    }

    return probabilities

def _mlai_fix_predict_from_evidence(
    current,
    records,
    horizon,
    query_index,
    *,
    min_probability=0.40,
    min_margin=0.05,
):
    """
    Final repaired decision rule.

    The decision layer no longer blindly follows:
      - raw top-k majority
      - power aggregation
      - the historical class prior

    It requires positive evidence and a minimum separation between the
    best and second-best classes.

    Otherwise it returns NEUTRAL.

    This is deliberately conservative.
    """

    probabilities = _mlai_fix_class_evidence(
        current,
        records,
        horizon,
        query_index,
    )

    ranked = sorted(
        probabilities.items(),
        key=lambda x: x[1],
        reverse=True,
    )

    best_class, best_probability = ranked[0]
    second_probability = ranked[1][1]

    margin = best_probability - second_probability

    # If evidence is ambiguous, do not manufacture a directional signal.
    if best_probability < min_probability:
        prediction = "NEUTRAL"
    elif margin < min_margin:
        prediction = "NEUTRAL"
    else:
        prediction = best_class

    return {
        "prediction": prediction,
        "probabilities": probabilities,
        "margin": margin,
        "best_probability": best_probability,
    }

def mlai_v415_repaired_prediction(
    current,
    records,
    horizon,
    query_index,
):
    """
    Public repaired predictive layer.

    Existing v4.1.6 retrieval remains available.

    Use this function for the repaired decision path.
    """

    return _mlai_fix_predict_from_evidence(
        current=current,
        records=records,
        horizon=horizon,
        query_index=query_index,
    )


# =====================================================================
# MLAI v4.2.0 ADVANCED CAUSAL RETRIEVAL LAYER
#
# This layer is deliberately deterministic and predeclared.  It does not
# inspect OOS outcomes, does not tune parameters on OOS data, and does not
# manufacture confidence.  It strengthens evidence quality through:
#   1. multi-scale causal similarity;
#   2. horizon-specific, fixed priors;
#   3. evidence-quality adaptive gating (not OOS learning);
#   4. contradiction-aware candidate filtering;
#   5. episode de-duplication + diversity-aware MMR selection;
#   6. class-balanced predictive evidence;
#   7. deterministic reliability/abstention diagnostics.
# =====================================================================

V420_VERSION = "4.2.0"
V420_TOP_K = 16
V420_MIN_CANDIDATES = 12
V420_MMR_LAMBDA = 0.78
V420_MIN_SIMILARITY = 0.42
V420_MAX_CONTRADICTION = 0.42
V420_PREDICT_TEMPERATURE = 0.10
V420_MIN_PROBABILITY = 0.42
V420_MIN_MARGIN = 0.08
V420_MIN_CLASS_SUPPORT = 2

# Predeclared horizon-specific priors.  These are fixed structural priors,
# not learned from OOS results.  They sum to 1.0 for each horizon.
V420_HORIZON_WEIGHTS = {
    4:  {"structure": 0.20, "sequence": 0.16, "regime": 0.14, "location": 0.08,
         "momentum": 0.12, "volatility": 0.08, "candle": 0.06, "path": 0.16},
    8:  {"structure": 0.22, "sequence": 0.15, "regime": 0.16, "location": 0.08,
         "momentum": 0.10, "volatility": 0.08, "candle": 0.05, "path": 0.16},
    16: {"structure": 0.24, "sequence": 0.13, "regime": 0.17, "location": 0.07,
         "momentum": 0.08, "volatility": 0.09, "candle": 0.04, "path": 0.18},
}


def _v420_clamp(x, lo=0.0, hi=1.0):
    try:
        x = float(x)
    except Exception:
        return lo
    if not math.isfinite(x):
        return lo
    return max(lo, min(hi, x))


def _v420_horizon_weights(horizon):
    return dict(V420_HORIZON_WEIGHTS.get(int(horizon), V420_HORIZON_WEIGHTS[8]))


def _v420_component_vector(current, record):
    """Return semantically distinct causal evidence families in [0,1]."""
    try:
        base = similarity_score.__wrapped__(current, record)  # defensive path
    except Exception:
        base = None
    if not isinstance(base, dict):
        # Call the original implementation captured below.
        base = _V420_ORIGINAL_SIMILARITY(current, record)

    values = {}
    for key in ("structure", "sequence", "regime", "location",
                "momentum", "volatility", "candle", "path"):
        values[key] = _v420_clamp(base.get(key, 0.0))

    # Additional causal numeric scale checks.  These are derived only from
    # the state at the query time and the historical record state.
    numeric = []
    for a, b in ((current.r1, record.r1), (current.r3, record.r3),
                 (current.r8, record.r8), (current.r16, record.r16)):
        scale = max(abs(float(a)), abs(float(b)), 0.01)
        numeric.append(_v420_clamp(1.0 - abs(float(a) - float(b)) / (2.0 * scale)))
    numeric_similarity = sum(numeric) / len(numeric)

    # Long-horizon trajectory is explicitly represented without replacing the
    # path score.  This avoids allowing one short pattern to dominate H16.
    trajectory = _v420_clamp(1.0 - (
        abs(current.r16 - record.r16) /
        max(2.0 * max(abs(current.r16), abs(record.r16), 0.01), 0.01)
    ))

    values["numeric"] = numeric_similarity
    values["trajectory"] = trajectory
    return values


# Preserve the complete pre-v4.2 implementation before replacing the public
# similarity function.  This keeps the v4.1.x evidence families intact.
_V420_ORIGINAL_SIMILARITY = similarity_score


def _v420_quality_gates(values):
    """Deterministic evidence-quality gate; never uses an outcome."""
    active = [values[k] for k in ("structure", "sequence", "regime", "location",
                                 "momentum", "volatility", "candle", "path")]
    nonzero = sum(1 for x in active if x > 0.0)
    coverage = nonzero / len(active)
    # Structure + context must not be simultaneously absent.
    structural_context = max(values["structure"], values["sequence"], values["regime"])
    return _v420_clamp(0.55 * coverage + 0.45 * structural_context)


def _v420_similarity(current, record, horizon):
    values = _v420_component_vector(current, record)
    weights = _v420_horizon_weights(horizon)
    quality = _v420_quality_gates(values)

    # Evidence-quality gating changes the influence of weak representations;
    # it does not boost a strong score beyond its observed components.
    total = sum(weights[k] * values[k] for k in weights)
    total = _v420_clamp(total * (0.75 + 0.25 * quality))

    values["total"] = total
    values["quality"] = quality
    return values


def similarity_score(current: MarketState, record: ExperienceRecord) -> Dict[str, float]:
    # Public compatibility API.  Horizon is carried by ExperienceRecord.
    return _v420_similarity(current, record, getattr(record, "horizon", 8))


def _v420_contradiction(current, record, values):
    """Measure causal contradiction, not future outcome disagreement."""
    contradictions = []
    if current.regime != record.regime and values["regime"] < 0.25:
        contradictions.append(1.0)
    if current.structure_event != record.structure_event and values["structure"] < 0.25:
        contradictions.append(1.0)
    if current.sequence_state != record.sequence_state and values["sequence"] < 0.25:
        contradictions.append(0.7)
    if current.momentum_state != record.momentum_state and values["momentum"] < 0.25:
        contradictions.append(0.5)
    return _v420_clamp(sum(contradictions) / max(len(contradictions), 1)) if contradictions else 0.0


def _v420_match_similarity(a, b):
    """Causal representation overlap used only for diversity selection."""
    keys = ("structure_similarity", "sequence_similarity", "regime_similarity",
            "location_similarity", "momentum_similarity", "volatility_similarity",
            "candle_similarity", "path_similarity")
    vals = []
    for key in keys:
        vals.append(1.0 - abs(_v420_clamp(getattr(a, key, 0.0)) -
                              _v420_clamp(getattr(b, key, 0.0))))
    return sum(vals) / len(vals)


def _v420_select_diverse(candidates, record_by_index, horizon):
    """Episode-aware MMR: quality first, redundancy second."""
    ranked = sorted(candidates, key=lambda x: (x.similarity, x.index), reverse=True)
    selected = []
    selected_episodes = set()
    limit = min(V420_TOP_K, len(ranked))

    # First pass: enforce one representative per episode.
    for match in ranked:
        if match.episode_id in selected_episodes:
            continue
        selected.append(match)
        selected_episodes.add(match.episode_id)
        if len(selected) >= limit:
            break

    # Second pass: if too few unique episodes exist, fill by MMR.
    if len(selected) < limit:
        remaining = [m for m in ranked if m.index not in {x.index for x in selected}]
        while remaining and len(selected) < limit:
            best = None
            best_score = -1e9
            for candidate in remaining:
                redundancy = max((_v420_match_similarity(candidate, s) for s in selected), default=0.0)
                mmr = V420_MMR_LAMBDA * candidate.similarity - (1.0 - V420_MMR_LAMBDA) * redundancy
                if mmr > best_score:
                    best_score = mmr
                    best = candidate
            if best is None:
                break
            selected.append(best)
            remaining = [m for m in remaining if m.index != best.index]

    selected.sort(key=lambda x: (x.similarity, x.index), reverse=True)
    return selected[:V420_TOP_K]


def retrieve_historical_experience(current, records, horizon, query_index):
    """V4.2.0 causal retrieval with quality gating and diversity control."""
    candidates = []
    coarse_records = coarse_filter(current, records, query_index)
    record_by_index = {r.index: r for r in records}

    for record in coarse_records:
        if record.index >= query_index:
            continue
        if query_index - record.index < MIN_HISTORY_GAP:
            continue
        if getattr(record, "horizon", horizon) != horizon:
            continue

        values = _v420_similarity(current, record, horizon)
        contradiction = _v420_contradiction(current, record, values)
        # Hard contradiction rejection only applies to very weak matches.  A
        # high-quality match is allowed to cross a regime boundary because
        # transitions themselves are historically meaningful.
        if contradiction > V420_MAX_CONTRADICTION and values["total"] < 0.60:
            continue
        if values["total"] < V420_MIN_SIMILARITY:
            continue

        candidates.append(SimilarityMatch(
            index=record.index,
            episode_id=record.episode_id,
            similarity=values["total"],
            structure_similarity=values["structure"],
            sequence_similarity=values["sequence"],
            regime_similarity=values["regime"],
            location_similarity=values["location"],
            momentum_similarity=values["momentum"],
            volatility_similarity=values["volatility"],
            candle_similarity=values["candle"],
            path_similarity=values["path"],
        ))

    candidates.sort(key=lambda x: (x.similarity, x.index), reverse=True)
    raw_count = len(candidates)

    if not candidates:
        return RetrievalResult(
            horizon=horizon, query_index=query_index, raw_candidates=0,
            deduplicated_matches=0, top_similarity=0.0, mean_similarity=0.0,
            level="NONE", evidence="NONE", sparse_warning=True,
            regime_agreement=0.0, structure_agreement=0.0, context_agreement=0.0,
            up_share=0.0, down_share=0.0, neutral_share=0.0,
            mean_atr_return=None, mean_mfe_atr=None, mean_mae_atr=None,
            supporting_matches=0, conflicting_matches=0,
            historical_min_index=None, historical_max_index=None,
            selected_match_indices=[],
        )

    selected = _v420_select_diverse(candidates, record_by_index, horizon)
    selected_rows = [(m, record_by_index[m.index]) for m in selected if m.index in record_by_index]
    if not selected_rows:
        return RetrievalResult(
            horizon=horizon, query_index=query_index, raw_candidates=raw_count,
            deduplicated_matches=0, top_similarity=0.0, mean_similarity=0.0,
            level="NONE", evidence="NONE", sparse_warning=True,
            regime_agreement=0.0, structure_agreement=0.0, context_agreement=0.0,
            up_share=0.0, down_share=0.0, neutral_share=0.0,
            mean_atr_return=None, mean_mfe_atr=None, mean_mae_atr=None,
            supporting_matches=0, conflicting_matches=0,
            historical_min_index=None, historical_max_index=None,
            selected_match_indices=[],
        )

    # Similarity is reliability, not confidence.  Squaring is intentionally
    # avoided here to reduce winner-takes-all concentration.
    weights = [max(m.similarity, EPS) for m, _ in selected_rows]
    total_weight = sum(weights)
    shares = {}
    for cls in ("UP", "DOWN", "NEUTRAL"):
        shares[cls] = safe_div(sum(w for w, (_, r) in zip(weights, selected_rows)
                                  if r.outcome.direction == cls), total_weight)

    dominant = max(shares.items(), key=lambda x: (x[1], x[0]))[0]
    supporting = sum(1 for _, r in selected_rows if r.outcome.direction == dominant)
    conflicting = len(selected_rows) - supporting
    indices = [r.index for _, r in selected_rows]
    mean_similarity = mean_or_zero([m.similarity for m, _ in selected_rows])
    top_similarity = selected_rows[0][0].similarity

    def wmean(field):
        return safe_div(sum(w * float(getattr(m, field)) for w, (m, _) in zip(weights, selected_rows)), total_weight)

    mean_atr_return = safe_div(sum(w * (r.outcome.atr_return or 0.0)
                                   for w, (_, r) in zip(weights, selected_rows)), total_weight)
    mean_mfe_atr = safe_div(sum(w * (r.outcome.mfe_atr or 0.0)
                                 for w, (_, r) in zip(weights, selected_rows)), total_weight)
    mean_mae_atr = safe_div(sum(w * (r.outcome.mae_atr or 0.0)
                                 for w, (_, r) in zip(weights, selected_rows)), total_weight)

    if len(selected_rows) < MIN_RETRIEVAL_MATCHES:
        level = "SPARSE"
    elif top_similarity >= 0.80:
        level = "STRONG_SIMILARITY"
    elif top_similarity >= 0.70:
        level = "MODERATE_STRONG"
    elif top_similarity >= 0.60:
        level = "MODERATE"
    else:
        level = "LOW_MODERATE"

    evidence = "LOW"
    if len(selected_rows) >= MIN_RETRIEVAL_MATCHES and top_similarity >= 0.70:
        evidence = "MODERATE"
    if len(selected_rows) >= 10 and top_similarity >= 0.80:
        evidence = "STRONG"

    return RetrievalResult(
        horizon=horizon, query_index=query_index, raw_candidates=raw_count,
        deduplicated_matches=len(selected_rows), top_similarity=top_similarity,
        mean_similarity=mean_similarity, level=level, evidence=evidence,
        sparse_warning=len(selected_rows) < MIN_RETRIEVAL_MATCHES,
        regime_agreement=wmean("regime_similarity"),
        structure_agreement=wmean("structure_similarity"),
        context_agreement=mean_or_zero([mean_or_zero([m.sequence_similarity,
                                                       m.regime_similarity,
                                                       m.location_similarity,
                                                       m.momentum_similarity,
                                                       m.path_similarity])
                                        for m, _ in selected_rows]),
        up_share=shares["UP"], down_share=shares["DOWN"], neutral_share=shares["NEUTRAL"],
        mean_atr_return=mean_atr_return, mean_mfe_atr=mean_mfe_atr, mean_mae_atr=mean_mae_atr,
        supporting_matches=supporting, conflicting_matches=conflicting,
        historical_min_index=min(indices), historical_max_index=max(indices),
        selected_match_indices=indices,
    )


def _v420_class_evidence_from_retrieval(current, records, horizon, query_index):
    """Predict only from the actual V4.2.0 retrieved historical set."""
    retrieval = retrieve_historical_experience(current, records, horizon, query_index)
    selected = set(retrieval.selected_match_indices)
    if not selected:
        return {"UP": 1/3, "DOWN": 1/3, "NEUTRAL": 1/3}

    buckets = {"UP": [], "DOWN": [], "NEUTRAL": []}
    for record in records:
        if record.index not in selected or record.index >= query_index:
            continue
        direction = _mlai_fix_outcome_direction(record)
        if direction not in buckets:
            continue
        score = _v420_similarity(current, record, horizon)["total"]
        buckets[direction].append(math.exp(-(1.0 - score) / V420_PREDICT_TEMPERATURE))

    evidence = {}
    for cls, values in buckets.items():
        if len(values) < V420_MIN_CLASS_SUPPORT:
            evidence[cls] = 0.0
        else:
            # Mean within class prevents historical class size from becoming
            # the prediction; support factor supplies reliability.
            mean_weight = sum(values) / len(values)
            support_factor = 1.0 - math.exp(-len(values) / 6.0)
            evidence[cls] = mean_weight * support_factor

    total = sum(evidence.values())
    if total <= EPS:
        return {"UP": 1/3, "DOWN": 1/3, "NEUTRAL": 1/3}
    return {k: evidence[k] / total for k in evidence}


def _mlai_fix_class_evidence(current, records, horizon, query_index, *, temperature=0.12, min_similarity=0.0):
    # V4.2.0 replaces the prior independent historical scan.  Prediction is
    # downstream of the causal retrieval result.
    return _v420_class_evidence_from_retrieval(current, records, horizon, query_index)


def _v420_prediction(current, records, horizon, query_index):
    probabilities = _v420_class_evidence_from_retrieval(current, records, horizon, query_index)
    ranked = sorted(probabilities.items(), key=lambda x: (x[1], x[0]), reverse=True)
    best_class, best_probability = ranked[0]
    second_probability = ranked[1][1]
    margin = best_probability - second_probability

    # Abstention is based on evidence separation, not a boosted margin.
    if best_probability < V420_MIN_PROBABILITY:
        prediction, reason = "NEUTRAL", "LOW_PROBABILITY"
    elif margin < V420_MIN_MARGIN:
        prediction, reason = "NEUTRAL", "LOW_MARGIN"
    else:
        prediction, reason = best_class, "SUPPORTED"
    return {"prediction": prediction, "probabilities": probabilities,
            "margin": margin, "best_probability": best_probability,
            "best_class": best_class, "decision_reason": reason}


def mlai_v415_repaired_prediction(current, records, horizon, query_index):
    # Compatibility name retained so the existing validation harness exercises
    # the V4.2.0 decision path without changing its call contract.
    return _v420_prediction(current, records, horizon, query_index)


# =====================================================================
# V4.2.0 MAIN-LABEL OVERRIDE
# =====================================================================
def main() -> None:
    print("=" * 96)
    print("MLAI v4.2.0 ADVANCED CAUSAL HISTORICAL EXPERIENCE RETRIEVAL")
    print("=" * 96)
    print("RESEARCH / VALIDATION ONLY")
    print("Multi-scale causal similarity        : ENABLED")
    print("Horizon-specific fixed priors        : ENABLED")
    print("Evidence-quality adaptive gating     : ENABLED")
    print("Contradiction-aware retrieval        : ENABLED")
    print("Episode + diversity-aware selection  : ENABLED")
    print("Retrieval-grounded prediction        : ENABLED")
    print("OOS parameter tuning                 : DISABLED")
    print("Confidence/margin inflation          : DISABLED")
    print()
    # Execute the mature, already audited walk-forward harness.  Its global
    # function bindings resolve to the V4.2.0 overrides above.
    _v420_legacy_main()

# =====================================================================
def _v420_legacy_main() -> None:
    print("=" * 96)
    print("MLAI v4.2.0 ADVANCED CAUSAL HISTORICAL EXPERIENCE RETRIEVAL")
    print("=" * 96)
    print("RESEARCH / VALIDATION ONLY")

    print()
    print("=" * 96)
    print("PROTECTION CHECK")
    print("=" * 96)
    print(f"{MARKET_DATA_FILE:<26}: READ ONLY")
    print("Production MLAI            : NOT MODIFIED")
    print("Learning memory            : NOT MODIFIED")
    print("Trading                    : DISABLED")

    guard = ProtectionGuard(MARKET_DATA_FILE)
    protection_before = guard.before_hash

    candles, invalid = load_market_data(MARKET_DATA_FILE)
    chronology = audit_chronology(candles)

    if not chronology["ordered"] or chronology["duplicates"]:
        raise RuntimeError("Chronology audit failed.")
    if len(candles) < 500:
        raise RuntimeError("Insufficient candle history.")

    windows = create_walk_forward_windows(
        len(candles),
        DEFAULT_TRAIN_WINDOWS,
        DEFAULT_OOS_SIZE,
    )

    atr = calculate_atr(candles)
    engine = CausalStructureEngine(candles)
    structure_states = engine.build()

    causality = audit_structure_causality(
        candles,
        engine.swings,
        structure_states,
        engine.events,
    )
    if not causality["passed"]:
        raise RuntimeError("Causality audit failed.")

    market_states = build_market_states(
        candles,
        structure_states,
        atr,
    )

    episode_ids = assign_episode_ids(market_states)

    print()
    print("=" * 96)
    print("FOUNDATION STATUS")
    print("=" * 96)
    print(f"Valid candles             : {len(candles)}")
    print(f"Invalid candles           : {invalid}")
    print(f"Confirmed swings          : {len(engine.swings)}")
    print(
        f"Structural events         : "
        f"{sum(1 for e in engine.events.values() if e != 'NONE')}"
    )
    print("Chronology                : PASS")
    print("Causal structure          : PASS")
    print(f"Episodes                  : {len(set(episode_ids.values()))}")

    print()
    print("Sequence states:")
    for name, count in Counter(state.sequence_state for state in market_states).most_common():
        print(f"  {name:<34}: {count}")

    print()
    print("Regimes:")
    for name, count in Counter(state.regime for state in market_states).most_common():
        print(f"  {name:<34}: {count}")

    all_windows: List[Dict[str, Any]] = []
    bucket_rows: List[Dict[str, Any]] = []
    null_rows: List[Dict[str, Any]] = []

    print()
    print("=" * 96)
    print("STRICT WALK-FORWARD HISTORICAL RETRIEVAL")
    print("=" * 96)

    for window in windows:
        window_result = {
            "window": asdict(window),
            "horizons": {},
        }

        print()
        print("-" * 96)
        print(
            f"WINDOW {window.number} | "
            f"TRAIN [{window.train_start}:{window.train_end}] | "
            f"OOS [{window.oos_start}:{window.oos_end}]"
        )

        for horizon in HORIZONS:
            records = build_experience_records(
                candles,
                atr,
                market_states,
                episode_ids,
                window.train_start,
                window.train_end,
                horizon,
            )

            evaluations = []

            for query_index in range(window.oos_start, window.oos_end):
                if query_index + horizon >= len(candles):
                    continue

                query_state = market_states[query_index]
                retrieval = retrieve_historical_experience(
                    query_state,
                    records,
                    horizon,
                    query_index,
                )

                # ---------------------------------------------------------
                # REPAIRED PREDICTIVE DECISION PATH
                #
                # The historical retrieval object remains available for
                # diagnostics, but the actual directional decision now
                # comes from the repaired evidence layer.
                #
                # This is deliberately evaluated using only:
                #   - query_state
                #   - training records
                #   - horizon
                #   - query_index
                #
                # No OOS outcome is supplied to the predictor.
                # ---------------------------------------------------------

                repaired_prediction = mlai_v415_repaired_prediction(
                    current=query_state,
                    records=records,
                    horizon=horizon,
                    query_index=query_index,
                )

                outcome = make_outcome(
                    candles,
                    atr,
                    query_index,
                    horizon,
                )
                if outcome is None:
                    continue

                # ---------------------------------------------------------
                # REPAIRED PREDICTION EVALUATION
                #
                # This is the first point where the repaired predictive
                # layer is connected to an actual out-of-sample evaluation.
                #
                # The outcome is used ONLY AFTER prediction has been
                # generated, so it cannot leak into the prediction.
                # ---------------------------------------------------------

                repaired_prediction_value = repaired_prediction["prediction"]
                repaired_probabilities = repaired_prediction["probabilities"]

                repaired_eval = evaluate_distribution(
                    repaired_probabilities,
                    outcome.direction,
                )

                retrieval_distribution = {
                    "UP": retrieval.up_share,
                    "DOWN": retrieval.down_share,
                    "NEUTRAL": retrieval.neutral_share,
                }

                retrieval_eval = evaluate_distribution(
                    retrieval_distribution,
                    outcome.direction,
                )

                baseline_level, baseline_distribution, baseline_samples = conditional_baseline(
                    query_state,
                    records,
                )

                baseline_eval = evaluate_distribution(
                    baseline_distribution,
                    outcome.direction,
                )

                row = {
                    "query_index": query_index,
                    "actual": outcome.direction,

                    # -----------------------------------------------------
                    # REPAIRED PREDICTIVE RESULT
                    # -----------------------------------------------------
                    "repaired_prediction": repaired_prediction_value,
                    "repaired_probabilities": repaired_probabilities,
                    "repaired_margin": repaired_prediction["margin"],
                    "repaired_best_probability": repaired_prediction[
                        "best_probability"
                    ],
                    "repaired_evaluation": repaired_eval,
                    "retrieval": asdict(retrieval),
                    "retrieval_evaluation": retrieval_eval,
                    "baseline": baseline_distribution,
                    "baseline_level": baseline_level,
                    "baseline_samples": baseline_samples,
                    "baseline_evaluation": baseline_eval,
                    "brier_lift": baseline_eval["brier"] - retrieval_eval["brier"],
                    "log_loss_lift": baseline_eval["log_loss"] - retrieval_eval["log_loss"],
                    "similarity_bucket": bucket_name(retrieval.top_similarity),
                }

                null_result = null_retrieval_sanity_test(
                    query_state,
                    records,
                    query_index,
                    horizon,
                )
                row["null_test"] = null_result

                evaluations.append(row)
                bucket_rows.append(row)
                if null_result["available"]:
                    null_rows.append(null_result)

            repaired_accuracy = (
                mean_or_zero(
                    [
                        1.0
                        if row["repaired_evaluation"]["correct"]
                        else 0.0
                        for row in evaluations
                    ]
                )
                if evaluations
                else None
            )

            repaired_brier = (
                mean_or_zero(
                    [
                        row["repaired_evaluation"]["brier"]
                        for row in evaluations
                    ]
                )
                if evaluations
                else None
            )

            repaired_log_loss = (
                mean_or_zero(
                    [
                        row["repaired_evaluation"]["log_loss"]
                        for row in evaluations
                    ]
                )
                if evaluations
                else None
            )

            retrieval_accuracy = (
                mean_or_zero(
                    [
                        1.0
                        if row["retrieval_evaluation"]["correct"]
                        else 0.0
                        for row in evaluations
                    ]
                )
                if evaluations
                else None
            )

            baseline_accuracy = (
                mean_or_zero(
                    [
                        1.0
                        if row["baseline_evaluation"]["correct"]
                        else 0.0
                        for row in evaluations
                    ]
                )
                if evaluations
                else None
            )

            retrieval_brier = (
                mean_or_zero(
                    [row["retrieval_evaluation"]["brier"] for row in evaluations]
                )
                if evaluations
                else None
            )
            baseline_brier = (
                mean_or_zero(
                    [row["baseline_evaluation"]["brier"] for row in evaluations]
                )
                if evaluations
                else None
            )
            retrieval_log_loss = (
                mean_or_zero(
                    [row["retrieval_evaluation"]["log_loss"] for row in evaluations]
                )
                if evaluations
                else None
            )
            baseline_log_loss = (
                mean_or_zero(
                    [row["baseline_evaluation"]["log_loss"] for row in evaluations]
                )
                if evaluations
                else None
            )

            non_sparse = [
                row
                for row in evaluations
                if not row["retrieval"]["sparse_warning"]
            ]

            result = {
                "training_records": len(records),
                "oos_queries": len(evaluations),

                # Repaired predictive layer
                "repaired_accuracy": repaired_accuracy,
                "repaired_brier": repaired_brier,
                "repaired_log_loss": repaired_log_loss,
                "retrieval_accuracy": retrieval_accuracy,
                "baseline_accuracy": baseline_accuracy,
                "retrieval_brier": retrieval_brier,
                "baseline_brier": baseline_brier,
                "brier_lift": (
                    baseline_brier - retrieval_brier
                    if retrieval_brier is not None and baseline_brier is not None
                    else None
                ),
                "retrieval_log_loss": retrieval_log_loss,
                "baseline_log_loss": baseline_log_loss,
                "log_loss_lift": (
                    baseline_log_loss - retrieval_log_loss
                    if retrieval_log_loss is not None and baseline_log_loss is not None
                    else None
                ),
                "retrieval_coverage": safe_div(len(non_sparse), len(evaluations)),
                "sparse_rate": 1.0 - safe_div(len(non_sparse), len(evaluations)),
                "mean_top_similarity": mean_or_zero(
                    [row["retrieval"]["top_similarity"] for row in evaluations]
                ),
                "mean_matches": mean_or_zero(
                    [row["retrieval"]["deduplicated_matches"] for row in evaluations]
                ),
                "mean_supporting_matches": mean_or_zero(
                    [row["retrieval"]["supporting_matches"] for row in evaluations]
                ),
                "mean_conflicting_matches": mean_or_zero(
                    [row["retrieval"]["conflicting_matches"] for row in evaluations]
                ),
                "evaluations": evaluations,
            }

            window_result["horizons"][horizon] = result

            print()
            print(
                f"H+{horizon}: "
                f"TrainRecords={len(records)} | OOSQueries={len(evaluations)}"
            )
            print(
                f"Retrieval Accuracy={fmt_pct(retrieval_accuracy)} | "
                f"Baseline={fmt_pct(baseline_accuracy)}"
            )

            print(
                f"REPAIRED Accuracy={fmt_pct(repaired_accuracy)} | "
                f"REPAIRED Brier={fmt_num(repaired_brier)} | "
                f"REPAIRED LogLoss={fmt_num(repaired_log_loss)}"
            )
            print(
                f"Retrieval Brier={fmt_num(retrieval_brier)} | "
                f"Baseline Brier={fmt_num(baseline_brier)} | "
                f"Lift={fmt_num(result['brier_lift'])}"
            )
            print(
                f"Retrieval LogLoss={fmt_num(retrieval_log_loss)} | "
                f"Baseline LogLoss={fmt_num(baseline_log_loss)} | "
                f"Lift={fmt_num(result['log_loss_lift'])}"
            )
            print(
                f"Coverage={fmt_pct(result['retrieval_coverage'])} | "
                f"Sparse={fmt_pct(result['sparse_rate'])} | "
                f"Matches={result['mean_matches']:.2f} | "
                f"TopSimilarity={fmt_pct(result['mean_top_similarity'])}"
            )

        all_windows.append(window_result)

    # ---------------------------------------------------------------------
    # AGGREGATION
    # ---------------------------------------------------------------------
    aggregate: Dict[int, Dict[str, Any]] = {}

    for horizon in HORIZONS:
        rows = [w["horizons"][horizon] for w in all_windows]
        valid = lambda key: [r[key] for r in rows if r.get(key) is not None]

        aggregate[horizon] = {
            "mean_retrieval_accuracy": mean_or_zero(valid("retrieval_accuracy")) if valid("retrieval_accuracy") else None,
            "mean_baseline_accuracy": mean_or_zero(valid("baseline_accuracy")) if valid("baseline_accuracy") else None,
            "mean_retrieval_brier": mean_or_zero(valid("retrieval_brier")) if valid("retrieval_brier") else None,
            "mean_baseline_brier": mean_or_zero(valid("baseline_brier")) if valid("baseline_brier") else None,
            "mean_brier_lift": mean_or_zero(valid("brier_lift")) if valid("brier_lift") else None,
            "mean_retrieval_log_loss": mean_or_zero(valid("retrieval_log_loss")) if valid("retrieval_log_loss") else None,
            "mean_baseline_log_loss": mean_or_zero(valid("baseline_log_loss")) if valid("baseline_log_loss") else None,
            "mean_log_loss_lift": mean_or_zero(valid("log_loss_lift")) if valid("log_loss_lift") else None,
            "mean_coverage": mean_or_zero([r["retrieval_coverage"] for r in rows]),
            "mean_sparse_rate": mean_or_zero([r["sparse_rate"] for r in rows]),
            "mean_top_similarity": mean_or_zero([r["mean_top_similarity"] for r in rows]),
            "mean_matches": mean_or_zero([r["mean_matches"] for r in rows]),
        }

    # ---------------------------------------------------------------------
    # SIMILARITY BUCKETS
    # ---------------------------------------------------------------------
    bucket_summary: Dict[str, Dict[str, Any]] = {}

    for bucket in [name for _, _, name in SIMILARITY_BUCKETS]:
        rows = [row for row in bucket_rows if row["similarity_bucket"] == bucket]
        if not rows:
            continue

        retrieval_brier = mean_or_zero(
            [row["retrieval_evaluation"]["brier"] for row in rows]
        )
        baseline_brier = mean_or_zero(
            [row["baseline_evaluation"]["brier"] for row in rows]
        )
        accuracy = mean_or_zero(
            [
                1.0 if row["retrieval_evaluation"]["correct"] else 0.0
                for row in rows
            ]
        )

        bucket_summary[bucket] = {
            "samples": len(rows),
            "accuracy": accuracy,
            "retrieval_brier": retrieval_brier,
            "baseline_brier": baseline_brier,
            "brier_lift": baseline_brier - retrieval_brier,
        }

    # ---------------------------------------------------------------------
    # NULL SUMMARY
    # ---------------------------------------------------------------------
    if null_rows:
        null_summary = {
            "queries": len(null_rows),
            "mean_real_max_share": mean_or_zero([r["real_max_share"] for r in null_rows]),
            "mean_null_max_share": mean_or_zero([r["null_max_share_mean"] for r in null_rows]),
            "mean_null_p95": mean_or_zero([r["null_max_share_p95"] for r in null_rows]),
            "mean_real_minus_null": mean_or_zero([r["real_minus_null_mean"] for r in null_rows]),
        }
    else:
        null_summary = {
            "queries": 0,
            "mean_real_max_share": None,
            "mean_null_max_share": None,
            "mean_null_p95": None,
            "mean_real_minus_null": None,
        }

    # ---------------------------------------------------------------------
    # FINAL PROTECTION
    # ---------------------------------------------------------------------
    protection_after = sha256_file(MARKET_DATA_FILE)
    if protection_before != protection_after:
        raise RuntimeError("market_data.bin changed.")

    # ---------------------------------------------------------------------
    # ARTIFACT
    # ---------------------------------------------------------------------
    artifact = {
        "version": VERSION,
        "objective": "ROBUST_CAUSAL_HISTORICAL_EXPERIENCE_RETRIEVAL",
        "candles": len(candles),
        "invalid_candles": invalid,
        "chronology": chronology,
        "causality": causality,
        "walk_forward": all_windows,
        "aggregate": aggregate,
        "similarity_buckets": bucket_summary,
        "null_test": null_summary,
        "retrieval_config": {
            "top_k": RETRIEVAL_TOP_K,
            "min_matches": MIN_RETRIEVAL_MATCHES,
            "min_history_gap": MIN_HISTORY_GAP,
            "episode_gap": EPISODE_GAP,
            "path_length": PATH_LENGTH,
            "null_permutations": NULL_PERMUTATIONS,
            "weights": {
                "structure": WEIGHT_STRUCTURE,
                "sequence": WEIGHT_SEQUENCE,
                "regime": WEIGHT_REGIME,
                "location": WEIGHT_LOCATION,
                "momentum": WEIGHT_MOMENTUM,
                "volatility": WEIGHT_VOLATILITY,
                "candle": WEIGHT_CANDLE,
                "path": WEIGHT_PATH,
            },
        },
        "market_language": {
            "sequence_counts": dict(
                Counter(state.sequence_state for state in market_states)
            ),
            "regime_counts": dict(
                Counter(state.regime for state in market_states)
            ),
            "episode_count": len(set(episode_ids.values())),
        },
        "protection": {
            "sha256_before": protection_before,
            "sha256_after": protection_after,
            "market_data_modified": False,
            "production_modified": False,
            "learning_memory_modified": False,
            "trading": False,
        },
    }

    with open(VALIDATION_BIN, "wb") as f:
        pickle.dump(artifact, f, protocol=pickle.HIGHEST_PROTOCOL)

    # ---------------------------------------------------------------------
    # REPORT
    # ---------------------------------------------------------------------
    report: List[str] = []
    report.append("# MLAI v4.1.6 Robust Causal Historical Experience Retrieval")
    report.append("")
    report.append("## Phase scope")
    report.append("")
    report.append("- Historical retrieval only")
    report.append("- Probability calibration: NOT ADDED")
    report.append("- Scenario reasoning: NOT ADDED")
    report.append("- Human-language generation: NOT ADDED")
    report.append("- Multi-timeframe reasoning: NOT ADDED")
    report.append("- Continuous learning: NOT ADDED")
    report.append("- Live data: NOT ADDED")
    report.append("")
    report.append("## Architecture")
    report.append("")
    report.append("- Canonical causal MarketState: ENABLED")
    report.append("- Causal structure / sequence / regime: ENABLED")
    report.append("- ATR-normalized outcomes: ENABLED")
    report.append("- Causal eligibility filter: ENABLED")
    report.append("- Coarse-to-fine retrieval: ENABLED")
    report.append("- Multi-layer similarity: ENABLED")
    report.append("- Causal path similarity: ENABLED")
    report.append("- Temporal episode de-duplication: ENABLED")
    report.append("- Supporting/conflicting evidence: ENABLED")
    report.append("- Sparse-evidence warning: ENABLED")
    report.append("- Retrieval-vs-baseline diagnostics: ENABLED")
    report.append("- Similarity bucket analysis: ENABLED")
    report.append("- Training-only null retrieval sanity test: ENABLED")
    report.append("- OOS outcomes used for retrieval: NO")
    report.append("")
    report.append("## Dataset / causality")
    report.append("")
    report.append(f"- Valid candles: {len(candles)}")
    report.append(f"- Invalid candles: {invalid}")
    report.append(f"- Confirmed swings: {len(engine.swings)}")
    report.append("- Chronology: PASS")
    report.append("- Duplicate timestamps: PASS")
    report.append("- Causal structure: PASS")
    report.append("")
    report.append("## Walk-forward results")
    report.append("")

    for horizon, result in aggregate.items():
        report.append(f"### H+{horizon}")
        report.append(f"- Retrieval accuracy: {fmt_pct(result['mean_retrieval_accuracy'])}")
        report.append(f"- Baseline accuracy: {fmt_pct(result['mean_baseline_accuracy'])}")
        report.append(f"- Retrieval Brier: {fmt_num(result['mean_retrieval_brier'])}")
        report.append(f"- Baseline Brier: {fmt_num(result['mean_baseline_brier'])}")
        report.append(f"- Brier lift: {fmt_num(result['mean_brier_lift'])}")
        report.append(f"- Retrieval log loss: {fmt_num(result['mean_retrieval_log_loss'])}")
        report.append(f"- Baseline log loss: {fmt_num(result['mean_baseline_log_loss'])}")
        report.append(f"- Log-loss lift: {fmt_num(result['mean_log_loss_lift'])}")
        report.append(f"- Coverage: {fmt_pct(result['mean_coverage'])}")
        report.append(f"- Sparse rate: {fmt_pct(result['mean_sparse_rate'])}")
        report.append(f"- Mean top similarity: {fmt_pct(result['mean_top_similarity'])}")
        report.append(f"- Mean independent matches: {result['mean_matches']:.2f}")
        report.append("")

    report.append("## Similarity bucket diagnostics")
    report.append("")
    if bucket_summary:
        for bucket, result in bucket_summary.items():
            report.append(f"### {bucket}")
            report.append(f"- Samples: {result['samples']}")
            report.append(f"- Accuracy: {fmt_pct(result['accuracy'])}")
            report.append(f"- Retrieval Brier: {fmt_num(result['retrieval_brier'])}")
            report.append(f"- Baseline Brier: {fmt_num(result['baseline_brier'])}")
            report.append(f"- Brier lift: {fmt_num(result['brier_lift'])}")
            report.append("")
    else:
        report.append("No similarity buckets contained evaluations.")
        report.append("")

    report.append("## Null retrieval sanity test")
    report.append("")
    report.append(f"- Queries: {null_summary['queries']}")
    report.append(f"- Mean real maximum share: {fmt_pct(null_summary['mean_real_max_share'])}")
    report.append(f"- Mean null maximum share: {fmt_pct(null_summary['mean_null_max_share'])}")
    report.append(f"- Mean null 95th percentile: {fmt_pct(null_summary['mean_null_p95'])}")
    report.append(f"- Mean real-minus-null: {fmt_pct(null_summary['mean_real_minus_null'])}")
    report.append("")

    report.append("## Interpretation")
    report.append("")
    report.append(
        "v4.1.6 tests retrieval quality, not trading performance. Historical "
        "outcome shares are evidence distributions and are not presented as "
        "calibrated probabilities."
    )
    report.append("")
    report.append(
        "Promotion to v4.1.7 should require retrieval to demonstrate stable "
        "out-of-sample usefulness against appropriate baselines and sensible "
        "behaviour across similarity buckets."
    )
    report.append("")
    report.append("## Protection")
    report.append("")
    report.append("- market_data.bin unchanged: PASS")
    report.append("- Production MLAI modified: NO")
    report.append("- Learning memory modified: NO")
    report.append("- Trading enabled: NO")
    report.append("")
    report.append("MLAI v4.1.6 COMPLETE")

    with open(VALIDATION_REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(report))

    print()
    print("=" * 96)
    print("V4.1.6 RETRIEVAL PHASE COMPLETE")
    print("=" * 96)

    for horizon, result in aggregate.items():
        print()
        print(f"H+{horizon}")
        print(f"  Retrieval Accuracy : {fmt_pct(result['mean_retrieval_accuracy'])}")
        print(f"  Baseline Accuracy  : {fmt_pct(result['mean_baseline_accuracy'])}")
        print(f"  Brier Lift         : {fmt_num(result['mean_brier_lift'])}")
        print(f"  LogLoss Lift       : {fmt_num(result['mean_log_loss_lift'])}")
        print(f"  Coverage           : {fmt_pct(result['mean_coverage'])}")
        print(f"  Sparse Rate        : {fmt_pct(result['mean_sparse_rate'])}")
        print(f"  Top Similarity     : {fmt_pct(result['mean_top_similarity'])}")

    print()
    print("Validation binary saved:")
    print(f"    {VALIDATION_BIN}")
    print("Validation report saved:")
    print(f"    {VALIDATION_REPORT}")
    print()
    print("market_data.bin       : READ ONLY")
    print("Production MLAI       : NOT MODIFIED")
    print("Learning memory       : NOT MODIFIED")
    print("Trading               : DISABLED")
    print()
    print("=" * 96)
    print("MLAI v4.1.6 ROBUST HISTORICAL EXPERIENCE RETRIEVAL COMPLETE")
    print("=" * 96)


if __name__ == "__main__":
    main()