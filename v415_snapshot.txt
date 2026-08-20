"""
MLAI v4.1.5 — ROBUST CAUSAL HISTORICAL EXPERIENCE RETRIEVAL
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

VERSION = "4.1.5"
MARKET_DATA_FILE = "market_data.bin"
VALIDATION_BIN = "MLAI_V415_ROBUST_HISTORICAL_EXPERIENCE_RETRIEVAL.bin"
VALIDATION_REPORT = "MLAI_V415_ROBUST_HISTORICAL_EXPERIENCE_RETRIEVAL_REPORT.md"

HORIZONS = (4, 8, 16)
SWING_LEFT = 3
SWING_RIGHT = 3
DEFAULT_TRAIN_WINDOWS = 5
DEFAULT_OOS_SIZE = 81

NEUTRAL_ATR_BAND = 0.25
RETRIEVAL_TOP_K = 40
MIN_RETRIEVAL_MATCHES = 8
MIN_HISTORY_GAP = max(HORIZONS)
EPISODE_GAP = 8
PATH_LENGTH = 8
NULL_PERMUTATIONS = 25
EPS = 1e-12

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


def coarse_filter(
    current: MarketState,
    records: Sequence[ExperienceRecord],
    query_index: int,
) -> List[ExperienceRecord]:
    """Causal coarse retrieval before numeric similarity."""
    compatible = []
    for record in records:
        if record.index >= query_index:
            continue
        if query_index - record.index < MIN_HISTORY_GAP:
            continue
        if (
            record.regime == current.regime
            or record.structure_event == current.structure_event
            or record.sequence_state == current.sequence_state
        ):
            compatible.append(record)

    if len(compatible) >= MIN_RETRIEVAL_MATCHES:
        return compatible

    return [
        record
        for record in records
        if record.index < query_index
        and query_index - record.index >= MIN_HISTORY_GAP
    ]


def numeric_similarity(a: float, b: float, scale: float) -> float:
    return math.exp(-abs(a - b) / max(abs(scale), EPS))


def path_row_similarity(
    current_row: Tuple[float, float, float, float],
    historical_row: Tuple[float, float, float, float],
) -> float:
    current_return, current_range, current_direction, current_body = current_row
    historical_return, historical_range, historical_direction, historical_body = historical_row

    return_similarity = numeric_similarity(current_return, historical_return, 1.0)
    range_similarity = numeric_similarity(current_range, historical_range, 1.0)
    body_similarity = numeric_similarity(current_body, historical_body, 1.0)
    direction_similarity = 1.0 if current_direction == historical_direction else 0.0

    return (
        0.45 * return_similarity
        + 0.25 * range_similarity
        + 0.20 * body_similarity
        + 0.10 * direction_similarity
    )


def path_similarity(current: MarketState, record: ExperienceRecord) -> float:
    values = [
        path_row_similarity(a, b)
        for a, b in zip(current.path_vector, record.path_vector)
    ]
    return mean_or_zero(values)


def similarity_score(current: MarketState, record: ExperienceRecord) -> Dict[str, float]:
    structure = mean_or_zero(
        [
            1.0 if current.trend == record.state_key[0] else 0.0,
            1.0 if current.structure_event == record.structure_event else 0.0,
            1.0 if current.high_label == record.state_key[2] else 0.0,
            1.0 if current.low_label == record.state_key[3] else 0.0,
        ]
    )

    sequence = 1.0 if current.sequence_state == record.sequence_state else 0.0
    regime = 1.0 if current.regime == record.regime else 0.0
    location = 1.0 if current.location == record.location else 0.0
    momentum = 1.0 if current.momentum_state == record.momentum_state else 0.0
    volatility = numeric_similarity(current.volatility_ratio, record.volatility_ratio, 0.50)

    candle = mean_or_zero(
        [
            numeric_similarity(current.body_ratio, record.body_ratio, 1.0),
            numeric_similarity(current.range_ratio, record.range_ratio, 1.0),
        ]
    )

    path = path_similarity(current, record)

    total = (
        WEIGHT_STRUCTURE * structure
        + WEIGHT_SEQUENCE * sequence
        + WEIGHT_REGIME * regime
        + WEIGHT_LOCATION * location
        + WEIGHT_MOMENTUM * momentum
        + WEIGHT_VOLATILITY * volatility
        + WEIGHT_CANDLE * candle
        + WEIGHT_PATH * path
    )

    return {
        "total": clamp(total),
        "structure": clamp(structure),
        "sequence": clamp(sequence),
        "regime": clamp(regime),
        "location": clamp(location),
        "momentum": clamp(momentum),
        "volatility": clamp(volatility),
        "candle": clamp(candle),
        "path": clamp(path),
    }


def select_episode_representatives(matches: Sequence[SimilarityMatch]) -> List[SimilarityMatch]:
    """Retain the strongest representative from each historical episode."""
    by_episode: Dict[int, SimilarityMatch] = {}
    for match in matches:
        current = by_episode.get(match.episode_id)
        if current is None or match.similarity > current.similarity:
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

    for record in coarse_filter(current, records, query_index):
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

    record_by_index = {record.index: record for record in records}
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

    weights = [match.similarity ** 2 for match, _ in selected_rows]
    total_weight = sum(weights)

    up_share = safe_div(
        sum(weight for weight, (_, record) in zip(weights, selected_rows) if record.outcome.direction == "UP"),
        total_weight,
    )
    down_share = safe_div(
        sum(weight for weight, (_, record) in zip(weights, selected_rows) if record.outcome.direction == "DOWN"),
        total_weight,
    )
    neutral_share = safe_div(
        sum(weight for weight, (_, record) in zip(weights, selected_rows) if record.outcome.direction == "NEUTRAL"),
        total_weight,
    )

    dominant = max(
        ("UP", up_share),
        ("DOWN", down_share),
        ("NEUTRAL", neutral_share),
        key=lambda x: x[1],
    )[0]

    supporting_matches = sum(
        1
        for _, record in selected_rows
        if record.outcome.direction == dominant
    )

    conflicting_matches = len(selected_rows) - supporting_matches

    top_similarity = selected[0].similarity
    mean_similarity = mean_or_zero([match.similarity for match, _ in selected_rows])

    regime_agreement = mean_or_zero([match.regime_similarity for match, _ in selected_rows])
    structure_agreement = mean_or_zero([match.structure_similarity for match, _ in selected_rows])
    context_agreement = mean_or_zero(
        [
            mean_or_zero(
                [
                    match.sequence_similarity,
                    match.regime_similarity,
                    match.location_similarity,
                    match.momentum_similarity,
                    match.path_similarity,
                ]
            )
            for match, _ in selected_rows
        ]
    )

    mean_atr_return = safe_div(
        sum(
            weight * (record.outcome.atr_return or 0.0)
            for weight, (_, record) in zip(weights, selected_rows)
        ),
        total_weight,
    )

    mean_mfe_atr = safe_div(
        sum(
            weight * (record.outcome.mfe_atr or 0.0)
            for weight, (_, record) in zip(weights, selected_rows)
        ),
        total_weight,
    )

    mean_mae_atr = safe_div(
        sum(
            weight * (record.outcome.mae_atr or 0.0)
            for weight, (_, record) in zip(weights, selected_rows)
        ),
        total_weight,
    )

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

    if len(selected_rows) < MIN_RETRIEVAL_MATCHES:
        evidence = "LOW"
    elif top_similarity >= 0.70:
        evidence = "MODERATE"
    else:
        evidence = "LOW_TO_MODERATE"

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
        up_share=up_share,
        down_share=down_share,
        neutral_share=neutral_share,
        mean_atr_return=mean_atr_return,
        mean_mfe_atr=mean_mfe_atr,
        mean_mae_atr=mean_mae_atr,
        supporting_matches=supporting_matches,
        conflicting_matches=conflicting_matches,
        historical_min_index=min(indices) if indices else None,
        historical_max_index=max(indices) if indices else None,
        selected_match_indices=indices,
    )


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


def main() -> None:
    print("=" * 96)
    print("MLAI v4.1.5 ROBUST CAUSAL HISTORICAL EXPERIENCE RETRIEVAL")
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

                outcome = make_outcome(
                    candles,
                    atr,
                    query_index,
                    horizon,
                )
                if outcome is None:
                    continue

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
    report.append("# MLAI v4.1.5 Robust Causal Historical Experience Retrieval")
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
        "v4.1.5 tests retrieval quality, not trading performance. Historical "
        "outcome shares are evidence distributions and are not presented as "
        "calibrated probabilities."
    )
    report.append("")
    report.append(
        "Promotion to v4.1.6 should require retrieval to demonstrate stable "
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
    report.append("MLAI v4.1.5 COMPLETE")

    with open(VALIDATION_REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(report))

    print()
    print("=" * 96)
    print("V4.1.5 RETRIEVAL PHASE COMPLETE")
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
    print("MLAI v4.1.5 ROBUST HISTORICAL EXPERIENCE RETRIEVAL COMPLETE")
    print("=" * 96)


if __name__ == "__main__":
    main()
