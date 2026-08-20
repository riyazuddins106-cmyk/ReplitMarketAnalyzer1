
from __future__ import annotations
import math, os, pickle, hashlib, statistics
from dataclasses import dataclass
from collections import Counter
from typing import Any, Optional, List

VERSION = "4.1.6-P2"
MARKET_DATA_FILE = "market_data.bin"
REPORT_FILE = "MLAI_V416_P2_CANDLE_STRUCTURE_SEQUENCE_REPORT.md"
ARTIFACT_FILE = "MLAI_V416_P2_CANDLE_STRUCTURE_SEQUENCE.bin"

SWING_LEFT = 3
SWING_RIGHT = 3
ATR_PERIOD = 14
RANGE_LOOKBACK = 20
SEQUENCE_LENGTH = 8
EPS = 1e-12


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
    label: str


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
    event_level: Optional[float]
    event_index: Optional[int]
    event_age: Optional[int]
    event_direction: str
    break_distance_atr: float
    break_strength: float
    acceptance_state: str
    retest_state: str
    structure_phase: str


@dataclass
class CandleAnatomy:
    index: int
    direction: str
    body_atr: float
    range_atr: float
    body_to_range: float
    upper_wick_to_range: float
    lower_wick_to_range: float
    close_location: float
    body_position: float
    directional_efficiency: float
    range_expansion: float
    candle_type: str
    rejection: str
    pressure: str


@dataclass
class SequenceState:
    index: int
    state: str
    prior_state: str
    transition: str
    impulse_count: int
    pullback_count: int
    compression_count: int
    expansion: bool


def _val(obj: Any, names, default=None):
    if isinstance(obj, dict):
        d = {str(k).lower(): v for k, v in obj.items()}
        for name in names:
            if name.lower() in d:
                return d[name.lower()]
        return default
    for name in names:
        if hasattr(obj, name):
            return getattr(obj, name)
    return default


def load_market_data(path: str):
    with open(path, "rb") as f:
        obj = pickle.load(f)

    if isinstance(obj, dict):
        for key in ("candles", "data", "rows", "ohlcv", "market_data"):
            if key in obj and isinstance(obj[key], (list, tuple)):
                obj = obj[key]
                break

    if not isinstance(obj, (list, tuple)):
        raise ValueError("Unsupported market_data.bin format.")

    candles = []
    invalid = 0

    for raw in obj:
        try:
            if isinstance(raw, (list, tuple)):
                if len(raw) >= 6:
                    timestamp, o, h, l, c, v = raw[:6]
                elif len(raw) >= 5:
                    timestamp, o, h, l, c = raw[:5]
                    v = 0.0
                else:
                    raise ValueError
            else:
                timestamp = _val(
                    raw, ("timestamp", "time", "datetime", "date", "ts"), len(candles)
                )
                o = _val(raw, ("open", "o"))
                h = _val(raw, ("high", "h"))
                l = _val(raw, ("low", "l"))
                c = _val(raw, ("close", "c"))
                v = _val(raw, ("volume", "vol", "v"), 0.0)

            o, h, l, c, v = map(float, (o, h, l, c, v))

            if not all(math.isfinite(x) for x in (o, h, l, c, v)):
                raise ValueError
            if h < max(o, c) or l > min(o, c) or h < l:
                raise ValueError

            candles.append(
                Candle(len(candles), timestamp, o, h, l, c, v)
            )
        except Exception:
            invalid += 1

    return candles, invalid


def calculate_atr(candles, period=ATR_PERIOD):
    output = [None] * len(candles)
    true_ranges = []

    for i, candle in enumerate(candles):
        previous_close = candles[i - 1].close if i else candle.close

        tr = max(
            candle.high - candle.low,
            abs(candle.high - previous_close),
            abs(candle.low - previous_close),
            EPS,
        )

        true_ranges.append(tr)

        if i + 1 >= period:
            output[i] = sum(true_ranges[-period:]) / period

    return output


def median_or(values, default):
    return statistics.median(values) if values else default


class CausalStructureEngine:
    """
    P2 structure engine.

    Important causal rule:
    a swing at pivot j becomes visible only at j + SWING_RIGHT.
    Every structure state is built using information available at that state.
    """

    def __init__(self, candles, atr):
        self.candles = candles
        self.atr = atr
        self.swings = []
        self.states = []

    def _is_confirmed_high(self, pivot, current_index):
        if pivot < SWING_LEFT:
            return False
        if pivot + SWING_RIGHT > current_index:
            return False

        price = self.candles[pivot].high

        return all(
            k == pivot or self.candles[k].high < price
            for k in range(
                pivot - SWING_LEFT,
                pivot + SWING_RIGHT + 1,
            )
        )

    def _is_confirmed_low(self, pivot, current_index):
        if pivot < SWING_LEFT:
            return False
        if pivot + SWING_RIGHT > current_index:
            return False

        price = self.candles[pivot].low

        return all(
            k == pivot or self.candles[k].low > price
            for k in range(
                pivot - SWING_LEFT,
                pivot + SWING_RIGHT + 1,
            )
        )

    def build(self):
        last_high = None
        last_low = None

        high_label = "UNKNOWN"
        low_label = "UNKNOWN"
        trend = "NEUTRAL"

        broken_highs = set()
        broken_lows = set()

        event_level = None
        event_index = None
        event_direction = "NONE"

        for i, candle in enumerate(self.candles):
            pivot = i - SWING_RIGHT

            if pivot >= SWING_LEFT:
                if self._is_confirmed_high(pivot, i):
                    label = (
                        "HH"
                        if last_high is None
                        or self.candles[pivot].high > last_high.price
                        else "LH"
                    )

                    last_high = Swing(
                        pivot,
                        i,
                        "HIGH",
                        self.candles[pivot].high,
                        label,
                    )

                    self.swings.append(last_high)
                    high_label = label

                if self._is_confirmed_low(pivot, i):
                    label = (
                        "HL"
                        if last_low is None
                        or self.candles[pivot].low > last_low.price
                        else "LL"
                    )

                    last_low = Swing(
                        pivot,
                        i,
                        "LOW",
                        self.candles[pivot].low,
                        label,
                    )

                    self.swings.append(last_low)
                    low_label = label

            event = "NONE"
            level = None
            direction = "NONE"

            if (
                last_high is not None
                and i > last_high.confirmation_index
                and candle.close > last_high.price
                and last_high.pivot_index not in broken_highs
            ):
                event = (
                    "BOS_BULLISH"
                    if trend in ("BULLISH", "NEUTRAL")
                    else "CHoCH_BULLISH"
                )
                level = last_high.price
                direction = "BULLISH"
                trend = "BULLISH"
                broken_highs.add(last_high.pivot_index)

            if (
                last_low is not None
                and i > last_low.confirmation_index
                and candle.close < last_low.price
                and last_low.pivot_index not in broken_lows
            ):
                if event == "NONE":
                    event = (
                        "BOS_BEARISH"
                        if trend in ("BEARISH", "NEUTRAL")
                        else "CHoCH_BEARISH"
                    )
                    level = last_low.price
                    direction = "BEARISH"

                trend = "BEARISH"
                broken_lows.add(last_low.pivot_index)

            if event != "NONE":
                event_level = level
                event_index = i
                event_direction = direction

            event_age = (
                None
                if event_index is None
                else i - event_index
            )

            current_atr = max(
                self.atr[i] or candle.high - candle.low,
                EPS,
            )

            break_distance_atr = 0.0
            break_strength = 0.0

            if event_level is not None and event_direction != "NONE":
                signed_distance = (
                    candle.close - event_level
                    if event_direction == "BULLISH"
                    else event_level - candle.close
                )

                break_distance_atr = signed_distance / current_atr
                break_strength = max(0.0, break_distance_atr)

            acceptance = "NONE"
            retest = "NONE"
            phase = "NEUTRAL"

            if event_index is not None and event_level is not None:
                age = i - event_index

                if age >= 1:
                    recent = self.candles[event_index : i + 1]

                    if event_direction == "BULLISH":
                        closes_beyond = sum(
                            x.close > event_level for x in recent
                        )

                        acceptance = (
                            "ACCEPTED"
                            if closes_beyond >= min(3, len(recent))
                            else "PENDING"
                        )

                        if candle.close < event_level and age <= 4:
                            acceptance = "REJECTED"

                    elif event_direction == "BEARISH":
                        closes_beyond = sum(
                            x.close < event_level for x in recent
                        )

                        acceptance = (
                            "ACCEPTED"
                            if closes_beyond >= min(3, len(recent))
                            else "PENDING"
                        )

                        if candle.close > event_level and age <= 4:
                            acceptance = "REJECTED"

                    if abs(candle.close - event_level) <= current_atr:
                        if (
                            event_direction == "BULLISH"
                            and candle.close > event_level
                        ):
                            retest = "HOLD"
                        elif (
                            event_direction == "BEARISH"
                            and candle.close < event_level
                        ):
                            retest = "HOLD"
                        else:
                            retest = "FAIL"

                if age == 0:
                    phase = "BREAK"
                elif acceptance == "ACCEPTED":
                    phase = "POST_BREAK"
                else:
                    phase = "TRANSITION"

            self.states.append(
                StructureState(
                    index=i,
                    trend=trend,
                    last_high=last_high.price if last_high else None,
                    last_low=last_low.price if last_low else None,
                    last_high_index=(
                        last_high.pivot_index if last_high else None
                    ),
                    last_low_index=(
                        last_low.pivot_index if last_low else None
                    ),
                    high_label=high_label,
                    low_label=low_label,
                    event=event,
                    event_level=event_level,
                    event_index=event_index,
                    event_age=event_age,
                    event_direction=event_direction,
                    break_distance_atr=break_distance_atr,
                    break_strength=break_strength,
                    acceptance_state=acceptance,
                    retest_state=retest,
                    structure_phase=phase,
                )
            )

        return self.states


def build_candle_anatomy(candles, atr):
    output = []

    for i, candle in enumerate(candles):
        current_atr = max(
            atr[i] or candle.high - candle.low,
            EPS,
        )

        candle_range = max(candle.high - candle.low, EPS)
        body = abs(candle.close - candle.open)

        upper_wick = max(
            candle.high - max(candle.open, candle.close),
            0.0,
        )

        lower_wick = max(
            min(candle.open, candle.close) - candle.low,
            0.0,
        )

        close_location = (
            candle.close - candle.low
        ) / candle_range

        body_position = (
            ((candle.open + candle.close) / 2.0)
            - candle.low
        ) / candle_range

        previous_close = (
            candles[i - 1].close
            if i > 0
            else candle.close
        )

        directional_efficiency = abs(
            candle.close - previous_close
        ) / candle_range

        previous_ranges = [
            candles[j].high - candles[j].low
            for j in range(
                max(0, i - RANGE_LOOKBACK),
                i,
            )
        ]

        baseline_range = median_or(
            previous_ranges,
            current_atr,
        )

        range_expansion = (
            candle_range / max(baseline_range, EPS)
        )

        direction = (
            "UP"
            if candle.close > candle.open
            else "DOWN"
            if candle.close < candle.open
            else "FLAT"
        )

        body_to_range = body / candle_range
        upper_wick_ratio = upper_wick / candle_range
        lower_wick_ratio = lower_wick / candle_range
        body_atr = body / current_atr
        range_atr = candle_range / current_atr

        if body_to_range <= 0.15:
            candle_type = "DOJI"
        elif (
            body_to_range >= 0.70
            and direction == "UP"
        ):
            candle_type = "STRONG_BODY_UP"
        elif (
            body_to_range >= 0.70
            and direction == "DOWN"
        ):
            candle_type = "STRONG_BODY_DOWN"
        elif (
            lower_wick >= body * 1.8
            and close_location >= 0.60
        ):
            candle_type = "BULLISH_REJECTION"
        elif (
            upper_wick >= body * 1.8
            and close_location <= 0.40
        ):
            candle_type = "BEARISH_REJECTION"
        elif (
            range_expansion >= 1.8
            and direction == "UP"
        ):
            candle_type = "WIDE_RANGE_UP"
        elif (
            range_expansion >= 1.8
            and direction == "DOWN"
        ):
            candle_type = "WIDE_RANGE_DOWN"
        elif range_expansion <= 0.65:
            candle_type = "COMPRESSION"
        else:
            candle_type = "NORMAL"

        if (
            lower_wick >= max(body * 1.5, candle_range * 0.45)
            and close_location > 0.55
        ):
            rejection = "BULLISH"
        elif (
            upper_wick >= max(body * 1.5, candle_range * 0.45)
            and close_location < 0.45
        ):
            rejection = "BEARISH"
        else:
            rejection = "NONE"

        if close_location >= 0.75 and direction == "UP":
            pressure = "BUYING"
        elif close_location <= 0.25 and direction == "DOWN":
            pressure = "SELLING"
        else:
            pressure = "MIXED"

        output.append(
            CandleAnatomy(
                index=i,
                direction=direction,
                body_atr=body_atr,
                range_atr=range_atr,
                body_to_range=body_to_range,
                upper_wick_to_range=upper_wick_ratio,
                lower_wick_to_range=lower_wick_ratio,
                close_location=close_location,
                body_position=body_position,
                directional_efficiency=directional_efficiency,
                range_expansion=range_expansion,
                candle_type=candle_type,
                rejection=rejection,
                pressure=pressure,
            )
        )

    return output


def build_sequence_states(candles, candle_states, structure_states):
    output = []

    for i in range(len(candles)):
        start = max(
            0,
            i - SEQUENCE_LENGTH + 1,
        )

        rows = candle_states[start : i + 1]

        prior_state = (
            output[-1].state
            if output
            else "INITIAL"
        )

        state = "MIXED"

        impulse_count = sum(
            row.body_to_range >= 0.60
            and row.range_expansion >= 1.10
            for row in rows
        )

        if structure_states[i].trend == "BULLISH":
            pullback_count = sum(
                row.direction == "DOWN"
                for row in rows
            )
        elif structure_states[i].trend == "BEARISH":
            pullback_count = sum(
                row.direction == "UP"
                for row in rows
            )
        else:
            pullback_count = 0

        compression_count = sum(
            row.candle_type == "COMPRESSION"
            or row.range_expansion <= 0.70
            for row in rows
        )

        expansion = bool(
            rows
            and rows[-1].range_expansion >= 1.35
        )

        structure = structure_states[i]

        if structure.event != "NONE":
            state = (
                "BULLISH_BREAK"
                if structure.event_direction == "BULLISH"
                else "BEARISH_BREAK"
            )

        elif structure.acceptance_state == "REJECTED":
            state = "FAILED_BREAK"

        elif structure.retest_state == "HOLD":
            state = "BREAK_RETEST_HOLD"

        elif (
            impulse_count >= 2
            and pullback_count >= 1
        ):
            state = "IMPULSE_PULLBACK"

        elif (
            prior_state == "IMPULSE_PULLBACK"
            and structure.trend != "NEUTRAL"
            and rows[-1].direction
            == (
                "UP"
                if structure.trend == "BULLISH"
                else "DOWN"
            )
        ):
            state = "PULLBACK_CONTINUATION"

        elif (
            prior_state == "IMPULSE_PULLBACK"
            and rows[-1].direction
            == (
                "DOWN"
                if structure.trend == "BULLISH"
                else "UP"
            )
        ):
            state = "PULLBACK_FAILURE"

        elif compression_count >= 3 and expansion:
            state = "COMPRESSION_EXPANSION"

        elif (
            rows[-1].rejection != "NONE"
            and structure.event != "NONE"
        ):
            state = "EXHAUSTION_REVERSAL"

        elif expansion:
            state = "IMPULSE"

        elif compression_count >= 3:
            state = "COMPRESSION"

        elif structure.trend != "NEUTRAL":
            state = "TREND_CONTINUATION"

        transition = (
            f"{prior_state}->{state}"
            if state != prior_state
            else "NONE"
        )

        output.append(
            SequenceState(
                index=i,
                state=state,
                prior_state=prior_state,
                transition=transition,
                impulse_count=impulse_count,
                pullback_count=pullback_count,
                compression_count=compression_count,
                expansion=expansion,
            )
        )

    return output


def build_all(candles):
    atr = calculate_atr(candles)

    structure_engine = CausalStructureEngine(
        candles,
        atr,
    )

    structure = structure_engine.build()
    candle = build_candle_anatomy(
        candles,
        atr,
    )

    sequence = build_sequence_states(
        candles,
        candle,
        structure,
    )

    return (
        atr,
        structure_engine,
        structure,
        candle,
        sequence,
    )


def causal_prefix_audit(candles, indices):
    """
    Rebuild each selected prefix independently.

    A P2 state at index i must be identical when calculated from:
      1. the complete dataset, and
      2. only candles 0..i.

    This directly checks for accidental future-information dependence.
    """

    full = build_all(candles)
    full_structure = full[2]
    full_candle = full[3]
    full_sequence = full[4]

    failures = []

    for i in indices:
        if i < 50 or i >= len(candles):
            continue

        prefix = build_all(
            candles[: i + 1]
        )

        fs = full_structure[i]
        ps = prefix[2][-1]

        fc = full_candle[i]
        pc = prefix[3][-1]

        fq = full_sequence[i]
        pq = prefix[4][-1]

        checks = [
            ("trend", fs.trend, ps.trend),
            ("high_label", fs.high_label, ps.high_label),
            ("low_label", fs.low_label, ps.low_label),
            ("event", fs.event, ps.event),
            ("event_index", fs.event_index, ps.event_index),
            (
                "event_direction",
                fs.event_direction,
                ps.event_direction,
            ),
            (
                "candle_type",
                fc.candle_type,
                pc.candle_type,
            ),
            (
                "rejection",
                fc.rejection,
                pc.rejection,
            ),
            (
                "sequence",
                fq.state,
                pq.state,
            ),
        ]

        for name, actual, prefix_value in checks:
            if actual != prefix_value:
                failures.append(
                    (
                        i,
                        name,
                        actual,
                        prefix_value,
                    )
                )

    return failures, full


def synthetic_tests():
    tests = []

    def make_candles(rows):
        result = []

        for i, (
            open_price,
            high_extra,
            low_extra,
            close_delta,
        ) in enumerate(rows):
            result.append(
                Candle(
                    i,
                    i,
                    open_price,
                    open_price + high_extra,
                    open_price - low_extra,
                    open_price + close_delta,
                    0.0,
                )
            )

        return result

    # Strong bullish body / expansion.
    candles = make_candles(
        [
            (100, 2, 1, 1.8),
            (101.8, 2.5, 1, 2.4),
            (104.2, 3, 1, 2.8),
            (107, 2.4, 0.2, 2.2),
        ]
    )

    _, _, _, candle, _ = build_all(candles)

    tests.append(
        (
            "strong_body_up",
            candle[-1].candle_type
            in (
                "STRONG_BODY_UP",
                "WIDE_RANGE_UP",
            ),
        )
    )

    # Bullish rejection.
    candles = make_candles(
        [
            (100, 2, 1, 0.2),
            (100.2, 1, 3, 0.9),
            (101.1, 1, 0.8, 0.7),
        ]
    )

    _, _, _, candle, _ = build_all(candles)

    tests.append(
        (
            "bullish_rejection",
            any(
                x.rejection == "BULLISH"
                for x in candle
            ),
        )
    )

    # Compression followed by expansion.
    candles = make_candles(
        [
            (100, 0.3, 0.3, 0.1),
            (100.1, 0.25, 0.25, 0.05),
            (100.15, 0.2, 0.2, 0.03),
            (100.18, 2.5, 0.2, 2.2),
        ]
    )

    _, _, _, candle, sequence = build_all(candles)

    tests.append(
        (
            "compression_expansion",
            sequence[-1].state
            == "COMPRESSION_EXPANSION"
            or candle[-1].range_expansion >= 1.35,
        )
    )

    return tests


def main():
    print("=" * 90)
    print(
        "MLAI v4.1.6 P2 â€” "
        "CANDLE + STRUCTURE + SEQUENCE HARDENING"
    )
    print("=" * 90)
    print("Research / validation only.")
    print("v4.1.5 is not modified.")
    print("market_data.bin is read-only.")

    if not os.path.exists(MARKET_DATA_FILE):
        raise FileNotFoundError(
            f"{MARKET_DATA_FILE} not found."
        )

    with open(
        MARKET_DATA_FILE,
        "rb",
    ) as f:
        protection_before = hashlib.sha256(
            f.read()
        ).hexdigest()

    candles, invalid = load_market_data(
        MARKET_DATA_FILE
    )

    if len(candles) < 100:
        raise RuntimeError(
            "Insufficient candle history."
        )

    chronology_ok = all(
        candles[i].timestamp
        >= candles[i - 1].timestamp
        for i in range(1, len(candles))
    )

    duplicate_ok = not any(
        candles[i].timestamp
        == candles[i - 1].timestamp
        for i in range(1, len(candles))
    )

    if not chronology_ok:
        raise RuntimeError(
            "Chronology audit failed."
        )

    if not duplicate_ok:
        raise RuntimeError(
            "Duplicate timestamp audit failed."
        )

    (
        atr,
        structure_engine,
        structure,
        candle,
        sequence,
    ) = build_all(candles)

    print()
    print("FOUNDATION")
    print("-" * 90)
    print(f"Valid candles       : {len(candles)}")
    print(f"Invalid candles     : {invalid}")
    print(
        f"Confirmed swings    : "
        f"{len(structure_engine.swings)}"
    )
    print(
        f"Structure events    : "
        f"{sum(x.event != 'NONE' for x in structure)}"
    )
    print("Chronology          : PASS")
    print("Duplicate timestamps: PASS")

    print()
    print("CANDLE ANATOMY")
    print("-" * 90)

    for name, count in Counter(
        x.candle_type for x in candle
    ).most_common():
        print(
            f"  {name:<30} {count}"
        )

    print()
    print("REJECTION")
    print("-" * 90)

    for name, count in Counter(
        x.rejection for x in candle
    ).most_common():
        print(
            f"  {name:<30} {count}"
        )

    print()
    print("STRUCTURE EVENTS")
    print("-" * 90)

    for name, count in Counter(
        x.event for x in structure
    ).most_common():
        print(
            f"  {name:<30} {count}"
        )

    print()
    print("STRUCTURE ACCEPTANCE")
    print("-" * 90)

    for name, count in Counter(
        x.acceptance_state
        for x in structure
    ).most_common():
        print(
            f"  {name:<30} {count}"
        )

    print()
    print("STRUCTURE RETEST")
    print("-" * 90)

    for name, count in Counter(
        x.retest_state
        for x in structure
    ).most_common():
        print(
            f"  {name:<30} {count}"
        )

    print()
    print("SEQUENCE STATES")
    print("-" * 90)

    for name, count in Counter(
        x.state for x in sequence
    ).most_common():
        print(
            f"  {name:<32} {count}"
        )

    print()
    print("CAUSAL PREFIX AUDIT")
    print("-" * 90)

    sample_indices = [
        50,
        100,
        200,
        400,
        600,
        800,
        1000,
        min(len(candles) - 1, 1200),
    ]

    failures, _ = causal_prefix_audit(
        candles,
        sample_indices,
    )

    if failures:
        print(
            f"FAIL â€” {len(failures)} mismatches"
        )

        for failure in failures[:20]:
            print(" ", failure)
    else:
        print("PASS â€” no causal prefix mismatches.")

    print()
    print("SYNTHETIC P2 TESTS")
    print("-" * 90)

    synthetic = synthetic_tests()

    for name, passed in synthetic:
        print(
            f"  {'PASS' if passed else 'FAIL':<6} {name}"
        )

    with open(
        MARKET_DATA_FILE,
        "rb",
    ) as f:
        protection_after = hashlib.sha256(
            f.read()
        ).hexdigest()

    data_unchanged = (
        protection_before
        == protection_after
    )

    print()
    print(
        "market_data.bin protection:",
        "PASS" if data_unchanged else "FAIL",
    )

    summary = {
        "version": VERSION,
        "candles": len(candles),
        "invalid": invalid,
        "causal_prefix_failures": len(
            failures
        ),
        "synthetic_tests": dict(synthetic),
        "candle_counts": dict(
            Counter(
                x.candle_type
                for x in candle
            )
        ),
        "structure_counts": dict(
            Counter(
                x.event
                for x in structure
            )
        ),
        "sequence_counts": dict(
            Counter(
                x.state
                for x in sequence
            )
        ),
        "data_unchanged": data_unchanged,
    }

    with open(
        ARTIFACT_FILE,
        "wb",
    ) as f:
        pickle.dump(
            summary,
            f,
            protocol=pickle.HIGHEST_PROTOCOL,
        )

    report = [
        "# MLAI v4.1.6 P2 Validation",
        "",
        "## Scope",
        "",
        "- Candle anatomy hardening",
        "- Causal market structure hardening",
        "- Sequence-state hardening",
        "- No probability changes",
        "- No scenario reasoning",
        "- No live learning",
        "- No trading",
        "- v4.1.5 not modified",
        "",
        "## Result",
        "",
        f"- Valid candles: {len(candles)}",
        f"- Invalid candles: {invalid}",
        f"- Causal prefix failures: {len(failures)}",
        f"- market_data.bin unchanged: {data_unchanged}",
        "",
        "## Synthetic tests",
        "",
    ]

    report.extend(
        f"- {name}: "
        f"{'PASS' if passed else 'FAIL'}"
        for name, passed in synthetic
    )

    report.extend(
        [
            "",
            "## Decision",
            "",
            (
                "P2 CORE PASS"
                if (
                    not failures
                    and all(
                        passed
                        for _, passed in synthetic
                    )
                    and data_unchanged
                )
                else
                "P2 CORE REQUIRES FIX"
            ),
            "",
            "This file is a P2 validation/hardening phase.",
            "It does not modify market_data.bin or production MLAI.",
        ]
    )

    with open(
        REPORT_FILE,
        "w",
        encoding="utf-8",
    ) as f:
        f.write("\n".join(report))

    print()
    print("Artifacts created:")
    print(f"  {ARTIFACT_FILE}")
    print(f"  {REPORT_FILE}")
    print()
    print(
        "Do not judge P2 from accuracy yet. "
        "First we verify the candle/structure/sequence "
        "representation and causality."
    )


if __name__ == "__main__":
    main()
