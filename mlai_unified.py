#!/usr/bin/env python3
"""
MLAI Unified Market Language Console
====================================

This is the integration boundary for the imported MLAI project.  It deliberately
keeps the existing v4.x files available as historical/reference implementations
while providing one executable path for the newer candle-language foundation.

The pipeline is intentionally causal:

    raw candles
        -> candle anatomy/language
        -> market state
        -> experience lookup
        -> prediction
        -> future reveal
        -> experience update

No database, network service, or UI is required.  All persisted state is
pickle-compatible binary with a small auditable manifest alongside it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import pickle
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
KB_PATH = DATA_DIR / "candle_language_v2.bin"
KB_INDEX_PATH = DATA_DIR / "candle_language_v2.index.json"
MARKET_PATH = DATA_DIR / "market_data.bin"
EXPERIENCE_PATH = DATA_DIR / "market_experience.bin"
EXPERIENCE_INDEX_PATH = DATA_DIR / "market_experience.index.json"
HORIZONS = (4, 8, 16)
OUTCOMES = ("bullish", "bearish", "neutral")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_pickle(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"Required binary is missing: {path}")
    with path.open("rb") as handle:
        return pickle.load(handle)


def write_pickle(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("wb") as handle:
        pickle.dump(value, handle, protocol=pickle.HIGHEST_PROTOCOL)
    temporary.replace(path)


@dataclass(frozen=True)
class Candle:
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0
    instrument: str = "unknown"
    timeframe: str = "unknown"


@dataclass(frozen=True)
class CandleLanguage:
    direction: str
    body_size: str
    range_size: str
    wick_profile: str
    behaviours: tuple[str, ...]
    body_range_ratio: float
    range_value: float
    close_location: float
    human: str


@dataclass(frozen=True)
class MarketState:
    index: int
    timestamp: int
    language: CandleLanguage
    trend: str
    volatility: str
    location: str
    sequence: str

    def key(self) -> str:
        """Stable, interpretable key used by the experience memory."""
        return "|".join(
            (
                self.language.direction,
                self.language.body_size,
                self.language.wick_profile,
                self.trend,
                self.volatility,
                self.location,
                self.sequence,
            )
        )


@dataclass
class ExperienceBucket:
    count: int = 0
    outcomes: dict[str, int] | None = None

    def __post_init__(self) -> None:
        if self.outcomes is None:
            self.outcomes = {outcome: 0 for outcome in OUTCOMES}

    def observe(self, outcome: str) -> None:
        if outcome not in OUTCOMES:
            raise ValueError(f"Unsupported outcome: {outcome}")
        self.count += 1
        assert self.outcomes is not None
        self.outcomes[outcome] += 1

    def distribution(self) -> dict[str, float]:
        assert self.outcomes is not None
        if self.count == 0:
            return {outcome: 1.0 / len(OUTCOMES) for outcome in OUTCOMES}
        return {outcome: self.outcomes[outcome] / self.count for outcome in OUTCOMES}


def _number(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    return result if math.isfinite(result) else default


def load_market(path: Path = MARKET_PATH) -> tuple[list[Candle], dict[str, Any]]:
    payload = load_pickle(path)
    if not isinstance(payload, dict) or not isinstance(payload.get("candles"), list):
        raise ValueError(f"Unsupported market data format in {path}")
    source = payload.get("source") or {}
    instrument = str(source.get("symbol") or source.get("instrument") or "unknown")
    timeframe = str(source.get("interval") or source.get("timeframe") or "unknown")
    candles: list[Candle] = []
    for row in payload["candles"]:
        if not isinstance(row, dict):
            continue
        candles.append(
            Candle(
                timestamp=int(_number(row.get("timestamp"))),
                open=_number(row.get("open")),
                high=_number(row.get("high")),
                low=_number(row.get("low")),
                close=_number(row.get("close")),
                volume=_number(row.get("volume")),
                instrument=instrument,
                timeframe=timeframe,
            )
        )
    return candles, {"source": source, "mlai_version": payload.get("mlai_version")}


def load_knowledge(path: Path = KB_PATH) -> dict[str, Any]:
    payload = load_pickle(path)
    if not isinstance(payload, dict) or not isinstance(payload.get("records"), list):
        raise ValueError(f"Unsupported candle-language format in {path}")
    return payload


def validate_knowledge(path: Path = KB_PATH, index_path: Path = KB_INDEX_PATH) -> dict[str, Any]:
    payload = load_knowledge(path)
    actual_hash = sha256(path)
    report: dict[str, Any] = {
        "file": str(path.relative_to(ROOT)),
        "format": payload.get("format"),
        "version": payload.get("version"),
        "schema_version": payload.get("schema_version"),
        "record_count": len(payload["records"]),
        "sha256": actual_hash,
        "index_status": "REVIEW",
        "required_terms": {},
    }
    if index_path.exists():
        index = json.loads(index_path.read_text())
        report["index_status"] = (
            "PASS"
            if index.get("kb_sha256") == actual_hash
            and index.get("kb_size") == path.stat().st_size
            and index.get("record_count") == len(payload["records"])
            else "FAIL"
        )
        report["indexed_sha256"] = index.get("kb_sha256")
    text = json.dumps(payload["records"], sort_keys=True).lower()
    required = ("open", "high", "low", "close", "look_ahead", "higher high", "lower low")
    report["required_terms"] = {term: term in text for term in required}
    report["vocabulary_status"] = "PASS" if all(report["required_terms"].values()) else "REVIEW"
    return report


def audit_market(candles: list[Candle]) -> dict[str, Any]:
    timestamps = [c.timestamp for c in candles]
    invalid_ohlc = [
        c
        for c in candles
        if not (c.low <= min(c.open, c.close) <= max(c.open, c.close) <= c.high)
        or c.high < c.low
    ]
    duplicates = len(timestamps) - len(set(timestamps))
    ordered = timestamps == sorted(timestamps)
    gaps: list[int] = []
    if len(timestamps) > 2:
        deltas = [b - a for a, b in zip(timestamps, timestamps[1:]) if b > a]
        if deltas:
            expected = Counter(deltas).most_common(1)[0][0]
            gaps = [delta for delta in deltas if delta > expected * 1.5]
    return {
        "candle_count": len(candles),
        "first_timestamp": timestamps[0] if timestamps else None,
        "last_timestamp": timestamps[-1] if timestamps else None,
        "ordered": ordered,
        "duplicates": duplicates,
        "invalid_ohlc": len(invalid_ohlc),
        "gaps": len(gaps),
        "gap_status": "PASS" if not gaps else "REVIEW",
        "status": (
            "PASS"
            if candles and ordered and not duplicates and not invalid_ohlc
            else "FAIL"
        ),
    }


def _percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int((len(ordered) - 1) * fraction)))
    return ordered[index]


def classify_candle(candle: Candle, recent: list[Candle]) -> CandleLanguage:
    range_value = max(0.0, candle.high - candle.low)
    body = abs(candle.close - candle.open)
    body_ratio = body / range_value if range_value else 0.0
    upper = max(0.0, candle.high - max(candle.open, candle.close))
    lower = max(0.0, min(candle.open, candle.close) - candle.low)
    average_range = sum(max(0.0, c.high - c.low) for c in recent) / max(1, len(recent))
    average_body = sum(abs(c.close - c.open) for c in recent) / max(1, len(recent))
    range_ratio = range_value / average_range if average_range else 1.0
    body_ratio_relative = body / average_body if average_body else 1.0
    direction = "bullish" if candle.close > candle.open else "bearish" if candle.close < candle.open else "neutral"
    body_size = (
        "large" if body_ratio_relative >= 1.5 else
        "small" if body_ratio_relative <= 0.6 else "medium"
    )
    range_size = "expansion" if range_ratio >= 1.5 else "compression" if range_ratio <= 0.6 else "normal"
    upper_ratio = upper / body if body else float("inf")
    lower_ratio = lower / body if body else float("inf")
    if lower_ratio >= 2.0 and lower > upper * 1.25:
        wick_profile = "long_lower_rejection"
    elif upper_ratio >= 2.0 and upper > lower * 1.25:
        wick_profile = "long_upper_rejection"
    elif body_ratio <= 0.12:
        wick_profile = "doji_like"
    elif upper <= range_value * 0.08 and lower <= range_value * 0.08:
        wick_profile = "marubozu_like"
    else:
        wick_profile = "balanced"
    behaviours: list[str] = []
    if range_size == "expansion":
        behaviours.append("expansion")
    if range_size == "compression":
        behaviours.append("compression")
    if "rejection" in wick_profile:
        behaviours.append("rejection")
    if body_size == "large" and range_size == "expansion":
        behaviours.append("momentum")
    if not behaviours:
        behaviours.append("ordinary")
    close_location = (candle.close - candle.low) / range_value if range_value else 0.5
    human_direction = {
        "bullish": "buying pressure",
        "bearish": "selling pressure",
        "neutral": "short-term hesitation",
    }[direction]
    human = (
        f"The candle closed {direction}, showing {human_direction}. "
        f"It has a {body_size} body, {wick_profile.replace('_', ' ')}, "
        f"and {range_size} range."
    )
    return CandleLanguage(
        direction, body_size, range_size, wick_profile, tuple(behaviours),
        body_ratio, range_value, close_location, human,
    )


def build_state(candles: list[Candle], index: int) -> Optional[MarketState]:
    if index < 20 or index >= len(candles):
        return None
    current = candles[index]
    recent = candles[max(0, index - 20): index + 1]
    language = classify_candle(current, recent)
    closes = [c.close for c in recent]
    change = closes[-1] / closes[0] - 1.0 if closes[0] else 0.0
    if change > 0.01:
        trend = "bullish"
    elif change < -0.01:
        trend = "bearish"
    else:
        trend = "range"
    ranges = [max(0.0, c.high - c.low) for c in recent]
    range_ratio = ranges[-1] / (sum(ranges[:-1]) / max(1, len(ranges) - 1))
    volatility = "high" if range_ratio > 1.5 else "low" if range_ratio < 0.6 else "normal"
    recent_high = max(c.high for c in recent)
    recent_low = min(c.low for c in recent)
    position = (current.close - recent_low) / (recent_high - recent_low) if recent_high != recent_low else 0.5
    location = "near_high" if position >= 0.8 else "near_low" if position <= 0.2 else "middle"
    directions = [classify_candle(c, recent).direction for c in recent[-4:]]
    sequence = " -> ".join(directions)
    return MarketState(index, current.timestamp, language, trend, volatility, location, sequence)


def outcome_at(candles: list[Candle], index: int, horizon: int) -> str:
    if index + horizon >= len(candles):
        raise IndexError("Future outcome is not available")
    start = candles[index].close
    end = candles[index + horizon].close
    threshold = max(start * 0.001, 1e-9)
    if end - start > threshold:
        return "bullish"
    if start - end > threshold:
        return "bearish"
    return "neutral"


def load_experience(path: Path = EXPERIENCE_PATH) -> dict[str, ExperienceBucket]:
    if not path.exists():
        return {}
    payload = load_pickle(path)
    raw = payload.get("buckets", {}) if isinstance(payload, dict) else {}
    result: dict[str, ExperienceBucket] = {}
    for key, value in raw.items():
        if isinstance(value, ExperienceBucket):
            result[key] = value
        elif isinstance(value, dict):
            result[key] = ExperienceBucket(int(value.get("count", 0)), dict(value.get("outcomes", {})))
    return result


def save_experience(buckets: dict[str, ExperienceBucket], path: Path = EXPERIENCE_PATH) -> None:
    payload = {
        "format": "MLAI_MARKET_EXPERIENCE",
        "version": "1.0",
        "schema_version": "1.0",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "knowledge_sha256": sha256(KB_PATH) if KB_PATH.exists() else None,
        "buckets": {key: asdict(value) for key, value in buckets.items()},
    }
    write_pickle(path, payload)
    index = {
        "format": payload["format"],
        "version": payload["version"],
        "record_count": sum(bucket.count for bucket in buckets.values()),
        "bucket_count": len(buckets),
        "experience_sha256": sha256(path),
        "knowledge_sha256": payload["knowledge_sha256"],
    }
    path.with_suffix(".index.json").write_text(json.dumps(index, indent=2, sort_keys=True) + "\n")


def predict(state: MarketState, buckets: dict[str, ExperienceBucket]) -> dict[str, Any]:
    bucket = buckets.get(state.key())
    if bucket is None or bucket.count < 1:
        probabilities = {outcome: 1.0 / len(OUTCOMES) for outcome in OUTCOMES}
        evidence = 0
        confidence = "insufficient historical evidence"
    else:
        probabilities = bucket.distribution()
        evidence = bucket.count
        confidence = "weak" if evidence < 20 else "moderate" if evidence < 100 else "strong"
    favored = max(probabilities, key=probabilities.get)
    return {
        "favored": favored,
        "probabilities": probabilities,
        "evidence": evidence,
        "confidence": confidence,
        "explanation": (
            f"Current state is {state.trend} with a {state.language.wick_profile} "
            f"candle near {state.location}. Historical evidence is {confidence}; "
            f"the favored scenario is {favored}, not a certainty."
        ),
    }


def run_walk_forward(
    candles: list[Candle],
    horizon: int = 4,
    start: int = 60,
    limit: Optional[int] = None,
    persist: bool = False,
) -> dict[str, Any]:
    if horizon not in HORIZONS:
        raise ValueError(f"horizon must be one of {HORIZONS}")
    buckets: dict[str, ExperienceBucket] = {}
    rows: list[dict[str, Any]] = []
    end = min(len(candles) - horizon, start + limit) if limit else len(candles) - horizon
    for index in range(start, max(start, end)):
        state = build_state(candles, index)
        if state is None:
            continue
        # Prediction is made before outcome_at is called.  The current bucket
        # contains only outcomes revealed at earlier prediction points.
        forecast = predict(state, buckets)
        actual = outcome_at(candles, index, horizon)
        correct = forecast["favored"] == actual
        rows.append({
            "index": index,
            "timestamp": state.timestamp,
            "state_key": state.key(),
            "favored": forecast["favored"],
            "probabilities": forecast["probabilities"],
            "evidence": forecast["evidence"],
            "actual": actual,
            "correct": correct,
        })
        # The chronological learning cycle is always part of this in-memory
        # run. Persistence is a separate concern controlled by the caller.
        buckets.setdefault(state.key(), ExperienceBucket()).observe(actual)
    accuracy = sum(row["correct"] for row in rows) / len(rows) if rows else 0.0
    baseline_counts = Counter(row["actual"] for row in rows)
    baseline = max(baseline_counts.values()) / len(rows) if rows else 0.0
    return {
        "horizon": horizon,
        "predictions": len(rows),
        "accuracy": accuracy,
        "majority_baseline": baseline,
        "incremental_value": accuracy - baseline,
        "experience_buckets": len(buckets),
        "rows": rows,
        "buckets": buckets,
    }


def print_audit() -> int:
    candles, metadata = load_market()
    knowledge = validate_knowledge()
    market = audit_market(candles)
    print("MLAI UNIFIED FOUNDATION AUDIT")
    print("=============================")
    print(json.dumps({
        "knowledge": knowledge,
        "market": market,
        "source": metadata,
        "causality": "PREDICT -> REVEAL -> LEARN",
        "status": (
            "PASS"
            if knowledge["index_status"] == "PASS"
            and market["status"] == "PASS"
            and market["gap_status"] == "PASS"
            else "REVIEW"
        ),
    }, indent=2, sort_keys=True))
    return 0


def print_translation(index: int) -> int:
    candles, _ = load_market()
    state = build_state(candles, index)
    if state is None:
        raise ValueError("At least 20 prior candles are required for translation")
    print("MLAI CANDLE LANGUAGE TRANSLATION")
    print("================================")
    print(json.dumps({
        "index": state.index,
        "timestamp": state.timestamp,
        "technical": {
            "direction": state.language.direction,
            "body_size": state.language.body_size,
            "range_size": state.language.range_size,
            "wick_profile": state.language.wick_profile,
            "behaviours": state.language.behaviours,
            "trend": state.trend,
            "volatility": state.volatility,
            "location": state.location,
            "sequence": state.sequence,
        },
        "human_language": state.language.human,
    }, indent=2))
    return 0


def print_walk_forward(args: argparse.Namespace) -> int:
    candles, _ = load_market()
    result = run_walk_forward(
        candles,
        args.horizon,
        args.start,
        args.limit,
        persist=args.persist,
    )
    summary = {key: value for key, value in result.items() if key not in ("rows", "buckets")}
    print("MLAI CAUSAL WALK-FORWARD")
    print("=======================")
    print(json.dumps(summary, indent=2, sort_keys=True))
    for row in result["rows"][: min(5, len(result["rows"]))]:
        print(json.dumps(row, sort_keys=True))
    if args.persist:
        save_experience(result["buckets"])
        print(f"Persisted experience: {EXPERIENCE_PATH}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Causal MLAI market-language console")
    subparsers = parser.add_subparsers(dest="command", required=False)
    subparsers.add_parser("audit", help="audit the imported knowledge book and market corpus")
    subparsers.add_parser("inspect-kb", help="print the knowledge-book manifest and vocabulary checks")
    translate = subparsers.add_parser("translate", help="translate one candle using prior context")
    translate.add_argument("--index", type=int, default=-1)
    walk = subparsers.add_parser("walk-forward", help="run predict -> reveal -> learn chronology")
    walk.add_argument("--horizon", type=int, choices=HORIZONS, default=4)
    walk.add_argument("--start", type=int, default=60)
    walk.add_argument("--limit", type=int)
    walk.add_argument(
        "--persist",
        action="store_true",
        help="persist the revealed experience after the causal run",
    )
    return parser


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    command = args.command or "audit"
    if command in ("audit", "inspect-kb"):
        return print_audit()
    if command == "translate":
        candles, _ = load_market()
        index = args.index if args.index >= 0 else len(candles) - 1
        return print_translation(index)
    if command == "walk-forward":
        return print_walk_forward(args)
    raise ValueError(f"Unknown command: {command}")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileNotFoundError, ValueError, pickle.UnpicklingError) as exc:
        print(f"MLAI ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)