"""
MLAI V4.2.0 — PRICE-ANCHORED MARKET LANGUAGE INTERPRETER
=========================================================

Research-only companion to MLAI_V420_RETRIEVAL_FORENSIC_REPAIR.py.

This script translates the latest (or a selected) causal market state into
plain English anchored to actual prices:

    candle data -> structure and price zones -> evidence -> scenarios

It does not modify the v4.2 engine, market_data.bin, production MLAI, or
learning memory. It does not place trades.

Run:
    python MLAI_V420_PRICE_INTERPRETER.py
    python MLAI_V420_PRICE_INTERPRETER.py --index 1200 --horizon 8
    python MLAI_V420_PRICE_INTERPRETER.py --json
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple
from zoneinfo import ZoneInfo

import mlai_market_structure_v420 as v420


ROOT = Path(__file__).resolve().parent
DATA_FILE = ROOT / "data" / Path(v420.MARKET_DATA_FILE).name
REPORT_FILE = ROOT / "MLAI_V420_PRICE_INTERPRETATION.md"
CLASSES = ("UP", "DOWN", "NEUTRAL")
EPS = 1e-12


def safe_div(a: float, b: float) -> float:
    return a / b if abs(b) > EPS else 0.0


def price(value: Optional[float]) -> str:
    return "unavailable" if value is None else f"${value:,.2f}"


def pct(value: float) -> str:
    return f"{100.0 * value:.1f}%"


def signed_pct(value: float) -> str:
    sign = "+" if value >= 0 else ""
    return f"{sign}{100.0 * value:.2f}%"


def format_timestamp(value: Any, timezone_name: str) -> str:
    """Format a source timestamp without pretending it is a live quote time."""
    try:
        number = float(value)
        # Unix milliseconds are common in imported market data.
        if number > 100_000_000_000:
            number /= 1000.0
        dt = datetime.fromtimestamp(number, tz=timezone.utc)
        return dt.astimezone(ZoneInfo(timezone_name)).strftime(
            "%A, %d %B %Y at %I:%M:%S %p %Z"
        )
    except (TypeError, ValueError, OSError):
        return str(value)


def candle_direction(candle: Any) -> str:
    if candle.close > candle.open:
        return "bullish (closed higher)"
    if candle.close < candle.open:
        return "bearish (closed lower)"
    return "flat (closed at its open)"


@dataclass
class PriceZone:
    kind: str
    low: float
    high: float
    center: float
    source_swings: List[int]
    tests: int
    rejection_tests: int
    last_test_index: Optional[int]

    @property
    def width(self) -> float:
        return self.high - self.low


def confirmed_swings(
    engine: Any,
    query_index: int,
    kind: str,
) -> List[Any]:
    return [
        swing
        for swing in engine.swings
        if swing.kind == kind and swing.confirmation_index <= query_index
    ]


def build_zones(
    candles: Sequence[Any],
    swings: Sequence[Any],
    query_index: int,
    atr: float,
    kind: str,
    tolerance: float,
    lookback: int,
) -> List[PriceZone]:
    """Cluster confirmed swing prices into observable support/resistance areas."""
    recent = [
        swing for swing in swings
        if swing.confirmation_index <= query_index
        and swing.pivot_index >= max(0, query_index - lookback)
    ]
    recent.sort(key=lambda item: item.price)

    clusters: List[List[Any]] = []
    for swing in recent:
        if not clusters or abs(swing.price - sum(s.price for s in clusters[-1]) / len(clusters[-1])) > tolerance:
            clusters.append([swing])
        else:
            clusters[-1].append(swing)

    zones: List[PriceZone] = []
    for cluster in clusters:
        center = sum(s.price for s in cluster) / len(cluster)
        low = min(s.price for s in cluster) - tolerance * 0.25
        high = max(s.price for s in cluster) + tolerance * 0.25
        test_indices = []
        rejection_indices = []

        for candle in candles[max(0, query_index - lookback): query_index + 1]:
            if kind == "RESISTANCE":
                touched = candle.high >= low and candle.low <= high
                rejected = touched and candle.close < center
            else:
                touched = candle.low <= high and candle.high >= low
                rejected = touched and candle.close > center
            if touched:
                test_indices.append(candle.index)
            if rejected:
                rejection_indices.append(candle.index)

        zones.append(
            PriceZone(
                kind=kind,
                low=low,
                high=high,
                center=center,
                source_swings=[s.pivot_index for s in cluster],
                tests=len(test_indices),
                rejection_tests=len(rejection_indices),
                last_test_index=max(test_indices) if test_indices else None,
            )
        )

    return zones


def nearest_zones(
    zones: Sequence[PriceZone],
    close: float,
) -> Tuple[List[PriceZone], List[PriceZone]]:
    below = sorted(
        [z for z in zones if z.center < close],
        key=lambda z: close - z.center,
    )
    above = sorted(
        [z for z in zones if z.center > close],
        key=lambda z: z.center - close,
    )
    return below, above


def zone_text(zone: Optional[PriceZone]) -> str:
    if zone is None:
        return "No confirmed zone was found in the selected lookback."
    return (
        f"{price(zone.low)}–{price(zone.high)} "
        f"(center {price(zone.center)}, {zone.tests} tests, "
        f"{zone.rejection_tests} rejection tests)"
    )


def structure_story(state: Any, candle: Any) -> str:
    trend = state.trend
    if trend == "BULLISH":
        return (
            f"The confirmed structure is bullish. The latest confirmed swing "
            f"labels are {state.high_label} on highs and {state.low_label} on lows."
        )
    if trend == "BEARISH":
        return (
            f"The confirmed structure is bearish. The latest confirmed swing "
            f"labels are {state.high_label} on highs and {state.low_label} on lows."
        )
    return (
        f"The confirmed structure is currently neutral or ranging. "
        f"The latest candle is {candle_direction(candle)}."
    )


def candle_evidence(candle: Any, atr: float) -> List[str]:
    candle_range = max(candle.high - candle.low, EPS)
    body = abs(candle.close - candle.open)
    upper_wick = candle.high - max(candle.open, candle.close)
    lower_wick = min(candle.open, candle.close) - candle.low
    evidence = [
        f"OHLC: open {price(candle.open)}, high {price(candle.high)}, "
        f"low {price(candle.low)}, close {price(candle.close)}.",
        f"The candle range is {price(candle_range)} "
        f"({safe_div(candle_range, atr):.2f} ATR) and the body is "
        f"{price(body)}.",
    ]
    if upper_wick / candle_range >= 0.35:
        evidence.append(
            f"The upper wick is {price(upper_wick)}, showing rejection "
            f"near {price(candle.high)}."
        )
    if lower_wick / candle_range >= 0.35:
        evidence.append(
            f"The lower wick is {price(lower_wick)}, showing rejection "
            f"near {price(candle.low)}."
        )
    return evidence


def historical_evidence(
    candles: Sequence[Any],
    atr: Sequence[Optional[float]],
    states: Sequence[Any],
    episode_ids: Dict[int, int],
    query_index: int,
    horizon: int,
) -> Dict[str, Any]:
    """Use only records whose outcomes completed before the query."""
    records = v420.build_experience_records(
        candles, atr, states, episode_ids, 0, query_index, horizon
    )
    retrieval = v420.retrieve_historical_experience(
        states[query_index], records, horizon, query_index
    )
    return {
        "records": len(records),
        "retrieval": asdict(retrieval),
    }


def build_interpretation(
    candles: Sequence[Any],
    states: Sequence[Any],
    engine: Any,
    atr_values: Sequence[Optional[float]],
    query_index: int,
    horizon: int,
    lookback: int,
    timezone_name: str,
    generated_at: str,
) -> Dict[str, Any]:
    candle = candles[query_index]
    state = states[query_index]
    atr = atr_values[query_index] or max(candle.high - candle.low, EPS)
    tolerance = max(atr * 0.60, abs(candle.close) * 0.001)

    resistance_swings = confirmed_swings(engine, query_index, "HIGH")
    support_swings = confirmed_swings(engine, query_index, "LOW")
    resistances = build_zones(
        candles, resistance_swings, query_index, atr, "RESISTANCE", tolerance, lookback
    )
    supports = build_zones(
        candles, support_swings, query_index, atr, "SUPPORT", tolerance, lookback
    )
    below_resistance, above_resistance = nearest_zones(resistances, candle.close)
    below_support, above_support = nearest_zones(supports, candle.close)

    nearest_support = below_support[0] if below_support else (supports[-1] if supports else None)
    nearest_resistance = above_resistance[0] if above_resistance else (resistances[0] if resistances else None)

    episode_ids = v420.assign_episode_ids(states)
    historical = historical_evidence(
        candles, atr_values, states, episode_ids, query_index, horizon
    )
    retrieval = historical["retrieval"]

    return {
        "query_index": query_index,
        "timestamp": str(candle.timestamp),
        "timestamp_display": format_timestamp(candle.timestamp, timezone_name),
        "instrument": state.instrument,
        "timeframe": state.timeframe,
        "timezone": timezone_name,
        "generated_at": generated_at,
        "data_start": format_timestamp(candles[0].timestamp, timezone_name),
        "data_end": format_timestamp(candles[-1].timestamp, timezone_name),
        "data_start_close": candles[0].close,
        "data_end_close": candles[-1].close,
        "current_candle": {
            "open": candle.open,
            "high": candle.high,
            "low": candle.low,
            "close": candle.close,
            "direction": candle_direction(candle),
        },
        "state": {
            "trend": state.trend,
            "sequence": state.sequence_state,
            "event": state.structure_event,
            "high_label": state.high_label,
            "low_label": state.low_label,
            "location": state.location,
            "regime": state.regime,
            "momentum": state.momentum_state,
            "returns": {
                "1_candle": state.r1,
                "3_candle": state.r3,
                "8_candle": state.r8,
                "16_candle": state.r16,
            },
        },
        "levels": {
            "support": asdict(nearest_support) if nearest_support else None,
            "resistance": asdict(nearest_resistance) if nearest_resistance else None,
            "all_support": [asdict(zone) for zone in supports],
            "all_resistance": [asdict(zone) for zone in resistances],
        },
        "atr": atr,
        "candle_evidence": candle_evidence(candle, atr),
        "historical": historical,
    }


def render_report(result: Dict[str, Any]) -> str:
    candle = result["current_candle"]
    state = result["state"]
    support = result["levels"]["support"]
    resistance = result["levels"]["resistance"]
    retrieval = result["historical"]["retrieval"]

    def level_line(zone: Optional[Dict[str, Any]]) -> str:
        if not zone:
            return "No confirmed price zone was found."
        return (
            f"{price(zone['low'])}–{price(zone['high'])}, centered at "
            f"{price(zone['center'])}; tested {zone['tests']} times and rejected "
            f"{zone['rejection_tests']} times."
        )

    lines = [
        "# MLAI Price-Anchored Market Language Interpretation",
        "",
        "This is a causal, research-only interpretation. It does not place trades.",
        "",
        "## Chart identity and time",
        "",
        f"- Chart / asset: **{result['instrument']}**",
        f"- Timeframe: **{result['timeframe']}** "
        "(the imported dataset does not identify its candle interval)",
        f"- Price-data coverage: **{result['data_start']}** to **{result['data_end']}**",
        f"- First recorded close: **{price(result['data_start_close'])}**",
        f"- Latest available candle time: **{result['timestamp_display']}**",
        f"- Latest recorded close: **{price(result['data_end_close'])}**",
        f"- Report generated: **{result['generated_at']}**",
        "",
        "This is the latest candle in the imported historical dataset, not a "
        "live exchange quote. The source file does not include a live connection "
        "or a confirmed timeframe, so the report cannot claim that the price is "
        "the live price right now.",
        "",
        "## Current price",
        "",
        f"- Candle index: `{result['query_index']}`",
        f"- Candle date and time: **{result['timestamp_display']}**",
        f"- Current close: **{price(candle['close'])}**",
        f"- Open: {price(candle['open'])}; high: {price(candle['high'])}; "
        f"low: {price(candle['low'])}; close: {price(candle['close'])}",
        f"- Candle reading: {candle['direction']}",
        "",
        "## Price levels",
        "",
        f"- Nearest confirmed support: **{level_line(support)}**",
        f"- Nearest confirmed resistance: **{level_line(resistance)}**",
        "",
        "A zone is reported instead of a magical single price because nearby "
        "candles can react across a range.",
        "",
        "## What the candles and structure are saying",
        "",
        f"- {structure_story_from_result(state)}",
        f"- The sequence is **{state['sequence']}** and the regime is **{state['regime']}**.",
        f"- Momentum classification: **{state['momentum']}**.",
        f"- One-candle return: {signed_pct(state['returns']['1_candle'])}; "
        f"three-candle return: {signed_pct(state['returns']['3_candle'])}; "
        f"eight-candle return: {signed_pct(state['returns']['8_candle'])}.",
        "",
        "## Price evidence",
        "",
    ]
    lines.extend(f"- {item}" for item in result["candle_evidence"])
    lines.extend(
        [
            "",
            "## Historical probability evidence",
            "",
            f"- Horizon tested: H+{retrieval['horizon']}",
            f"- Historical records available: {result['historical']['records']}",
            f"- Comparable matches: {retrieval['deduplicated_matches']} "
            f"of {retrieval['raw_candidates']} candidates",
            f"- Similarity evidence: {retrieval['level']} "
            f"(top similarity {retrieval['top_similarity']:.3f})",
            f"- UP probability: {pct(retrieval['up_share'])}",
            f"- DOWN probability: {pct(retrieval['down_share'])}",
            f"- NEUTRAL probability: {pct(retrieval['neutral_share'])}",
            f"- Evidence warning: "
            f"{'sparse evidence' if retrieval['sparse_warning'] else 'not sparse, but still not a guarantee'}",
            "",
            "## Plain-English interpretation",
            "",
            plain_story(result),
            "",
            "## Professional market reading",
            "",
            professional_reading(result),
            "",
            "## Confirmation and invalidation",
            "",
            confirmation_text(result),
            "",
            invalidation_text(result),
            "",
            "## Important limitation",
            "",
            "The words “buying pressure” and “selling pressure” describe observable "
            "price behavior. OHLCV data cannot prove hidden orders, institutions, "
            "or trader intention. Probabilities describe historical outcomes; they "
            "are not promises about the future.",
            "",
        ]
    )
    return "\n".join(lines)


def structure_story_from_result(state: Dict[str, Any]) -> str:
    if state["trend"] == "BULLISH":
        return (
            f"The confirmed structure is bullish, with latest labels "
            f"{state['high_label']} on highs and {state['low_label']} on lows."
        )
    if state["trend"] == "BEARISH":
        return (
            f"The confirmed structure is bearish, with latest labels "
            f"{state['high_label']} on highs and {state['low_label']} on lows."
        )
    return "The confirmed structure is neutral or ranging."


def plain_story(result: Dict[str, Any]) -> str:
    close = result["current_candle"]["close"]
    state = result["state"]
    support = result["levels"]["support"]
    resistance = result["levels"]["resistance"]
    if state["trend"] == "BULLISH":
        opening = f"At {price(close)}, the chart is showing a bullish structure."
    elif state["trend"] == "BEARISH":
        opening = f"At {price(close)}, the chart is showing a bearish structure."
    else:
        opening = f"At {price(close)}, the chart is showing a mixed or ranging structure."

    parts = [opening]
    if support:
        parts.append(
            f"The nearest confirmed support is {price(support['low'])}–"
            f"{price(support['high'])}, where price has been tested "
            f"{support['tests']} times."
        )
    if resistance:
        parts.append(
            f"The nearest confirmed resistance is {price(resistance['low'])}–"
            f"{price(resistance['high'])}, where price has been tested "
            f"{resistance['tests']} times and rejected "
            f"{resistance['rejection_tests']} times."
        )
    parts.append(
        f"The current candle is {result['current_candle']['direction']}. "
        f"This is an evidence-based reading of the prices available through "
        f"candle {result['query_index']}, not a certainty about the next move."
    )
    return " ".join(parts)


def professional_reading(result: Dict[str, Any]) -> str:
    """A concise trader-style read that remains tied to observable evidence."""
    candle = result["current_candle"]
    state = result["state"]
    support = result["levels"]["support"]
    resistance = result["levels"]["resistance"]
    retrieval = result["historical"]["retrieval"]

    if support:
        support_text = (
            f"Support is {price(support['low'])}–{price(support['high'])}. "
            f"It has {support['tests']} observed tests and "
            f"{support['rejection_tests']} closes rejecting below the zone."
        )
    else:
        support_text = "No confirmed support zone was found in the selected lookback."

    if resistance:
        resistance_text = (
            f"Resistance is {price(resistance['low'])}–{price(resistance['high'])}. "
            f"It has {resistance['tests']} observed tests and "
            f"{resistance['rejection_tests']} rejection tests."
        )
    else:
        resistance_text = "No confirmed resistance zone was found in the selected lookback."

    return (
        f"At {price(candle['close'])}, on the candle dated "
        f"{result['timestamp_display']}, the market structure is {state['trend']} "
        f"and the sequence is {state['sequence']}. {support_text} "
        f"{resistance_text} The latest candle was {candle['direction']}; "
        f"its close was {price(candle['close'])} after trading between "
        f"{price(candle['low'])} and {price(candle['high'])}. "
        f"Historical H+{retrieval['horizon']} comparisons currently show "
        f"{pct(retrieval['up_share'])} UP, {pct(retrieval['down_share'])} DOWN, "
        f"and {pct(retrieval['neutral_share'])} NEUTRAL across "
        f"{retrieval['deduplicated_matches']} comparable cases. "
        "That evidence describes what happened in the past; it does not "
        "guarantee the next candle."
    )


def confirmation_text(result: Dict[str, Any]) -> str:
    resistance = result["levels"]["resistance"]
    if resistance:
        return (
            f"Continuation would receive confirmation from a candle close above "
            f"{price(resistance['high'])}, followed by another candle holding above "
            f"that price area."
        )
    return "Confirmation requires a new, clearly observed break of a confirmed level."


def invalidation_text(result: Dict[str, Any]) -> str:
    support = result["levels"]["support"]
    if support:
        return (
            f"The current support-based interpretation would weaken after a candle "
            f"close below {price(support['low'])}."
        )
    return "The interpretation would weaken after a confirmed break against the current structure."


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=int, default=None, help="Candle index; default is latest.")
    parser.add_argument("--horizon", type=int, choices=v420.HORIZONS, default=8)
    parser.add_argument("--lookback", type=int, default=240)
    parser.add_argument(
        "--timezone",
        default="Asia/Kolkata",
        help="Timezone for displayed dates and times (default: Asia/Kolkata).",
    )
    parser.add_argument("--json", action="store_true", help="Print structured JSON instead of English.")
    args = parser.parse_args()
    try:
        ZoneInfo(args.timezone)
    except Exception as exc:
        raise ValueError(f"Unknown timezone: {args.timezone}") from exc

    candles, invalid = v420.load_market_data(str(DATA_FILE))
    chronology = v420.audit_chronology(candles)
    if not chronology["ordered"] or chronology["duplicates"]:
        raise RuntimeError("Market chronology audit failed.")

    query_index = len(candles) - 1 if args.index is None else args.index
    if query_index < 0 or query_index >= len(candles):
        raise ValueError(f"--index must be between 0 and {len(candles) - 1}.")

    atr = v420.calculate_atr(candles)
    engine = v420.CausalStructureEngine(candles)
    structure_states = engine.build()
    causality = v420.audit_structure_causality(
        candles, engine.swings, structure_states, engine.events
    )
    if not causality["passed"]:
        raise RuntimeError("Causal structure audit failed.")

    states = v420.build_market_states(candles, structure_states, atr)
    result = build_interpretation(
        candles,
        states,
        engine,
        atr,
        query_index,
        args.horizon,
        args.lookback,
        args.timezone,
        format_timestamp(
            datetime.now(tz=ZoneInfo(args.timezone)).timestamp(),
            args.timezone,
        ),
    )
    result["dataset"] = {
        "file": str(DATA_FILE),
        "candles": len(candles),
        "invalid": invalid,
        "chronology": chronology,
        "causality": causality,
    }

    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        report = render_report(result)
        print(report)
        REPORT_FILE.write_text(report, encoding="utf-8")
        print(f"\nSaved readable report to {REPORT_FILE.name}")


if __name__ == "__main__":
    main()