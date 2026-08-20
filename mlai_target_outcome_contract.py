"""
MLAI — Canonical Target / Outcome Contract
Phase 10

Purpose
-------
Provide one authoritative, causal, reproducible definition of future
targets and historical outcomes for the MLAI research architecture.

Scientific rules
----------------
1. Current-state features must never contain future information.
2. Future values are targets/evaluation outputs only.
3. Target generation is deterministic.
4. Target definitions are declared before validation.
5. Every outcome has an explicit completion boundary.
6. MFE/MAE are evaluation statistics, never predictive inputs.
7. The contract is independent of model selection.
8. No BUY/SELL semantics are used.
9. Overlapping target windows are explicitly detectable.
10. The final locked test must be handled by the validation layer.

This module does NOT train models.
This module does NOT select features.
This module does NOT perform model selection.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
import hashlib
import json
import math


# ============================================================================
# CONTRACT IDENTITY
# ============================================================================

CONTRACT_NAME = "MLAI Canonical Target / Outcome Contract"
CONTRACT_VERSION = "1.0.0"

# These are the currently declared research horizons.
HORIZONS: Tuple[int, ...] = (4, 8, 16)

# Minimum information needed before an outcome can exist.
MIN_HORIZON = min(HORIZONS)


# ============================================================================
# ENUMERATIONS
# ============================================================================

class OutcomeDirection(str, Enum):
    HIGHER = "higher"
    LOWER = "lower"
    NEUTRAL = "neutral"


class OutcomeQuality(str, Enum):
    COMPLETE = "complete"
    INCOMPLETE = "incomplete"
    INVALID = "invalid"


class FieldRole(str, Enum):
    INPUT = "causal_input"
    TARGET = "future_target"
    EVALUATION = "evaluation_only"
    PROHIBITED = "prohibited"


# ============================================================================
# CANDLE CONTRACT
# ============================================================================

@dataclass(frozen=True)
class Candle:
    """
    Minimal canonical candle.

    timestamp:
        Monotonic timestamp identifying the candle.

    open/high/low/close:
        OHLC values.

    volume:
        Optional volume. Volume is not required by this contract because
        the existing MLAI dataset may not always contain reliable volume.
    """

    timestamp: Any
    open: float
    high: float
    low: float
    close: float
    volume: Optional[float] = None

    def validate(self) -> None:
        values = {
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
        }

        for name, value in values.items():
            if not isinstance(value, (int, float)):
                raise TypeError(f"{name} must be numeric")

            if not math.isfinite(float(value)):
                raise ValueError(f"{name} must be finite")

        if self.open <= 0:
            raise ValueError("open must be positive")

        if self.high <= 0:
            raise ValueError("high must be positive")

        if self.low <= 0:
            raise ValueError("low must be positive")

        if self.close <= 0:
            raise ValueError("close must be positive")

        if self.high < max(self.open, self.close):
            raise ValueError("high is below open/close")

        if self.low > min(self.open, self.close):
            raise ValueError("low is above open/close")

        if self.high < self.low:
            raise ValueError("high is below low")

        if self.volume is not None:
            if not math.isfinite(float(self.volume)):
                raise ValueError("volume must be finite")

            if self.volume < 0:
                raise ValueError("volume cannot be negative")


# ============================================================================
# CAUSALITY CONTRACT
# ============================================================================

@dataclass(frozen=True)
class FieldContract:
    name: str
    role: FieldRole
    description: str
    availability_rule: str


FIELD_CONTRACTS: Tuple[FieldContract, ...] = (
    FieldContract(
        name="current_close",
        role=FieldRole.INPUT,
        description="Current candle close.",
        availability_rule="Available at current candle close.",
    ),
    FieldContract(
        name="current_ohlc",
        role=FieldRole.INPUT,
        description="Current candle OHLC.",
        availability_rule="Available at current candle close.",
    ),
    FieldContract(
        name="atr",
        role=FieldRole.INPUT,
        description="ATR calculated only from candles available at evaluation time.",
        availability_rule="Available at current candle close.",
    ),
    FieldContract(
        name="future_close",
        role=FieldRole.TARGET,
        description="Close at a declared future horizon.",
        availability_rule="Available only when the future horizon closes.",
    ),
    FieldContract(
        name="future_high",
        role=FieldRole.TARGET,
        description="Highest future high inside the declared outcome window.",
        availability_rule="Available only after the outcome window completes.",
    ),
    FieldContract(
        name="future_low",
        role=FieldRole.TARGET,
        description="Lowest future low inside the declared outcome window.",
        availability_rule="Available only after the outcome window completes.",
    ),
    FieldContract(
        name="mfe",
        role=FieldRole.EVALUATION,
        description="Maximum favorable excursion after the evaluation point.",
        availability_rule="Available only after the outcome window completes.",
    ),
    FieldContract(
        name="mae",
        role=FieldRole.EVALUATION,
        description="Maximum adverse excursion after the evaluation point.",
        availability_rule="Available only after the outcome window completes.",
    ),
)


def get_field_contract(name: str) -> FieldContract:
    for contract in FIELD_CONTRACTS:
        if contract.name == name:
            return contract

    raise KeyError(f"Unknown field contract: {name}")


def is_future_field(name: str) -> bool:
    return get_field_contract(name).role in {
        FieldRole.TARGET,
        FieldRole.EVALUATION,
    }


# ============================================================================
# SAFE NUMERIC HELPERS
# ============================================================================

def safe_float(value: Any) -> Optional[float]:
    if value is None:
        return None

    try:
        result = float(value)
    except (TypeError, ValueError):
        return None

    if not math.isfinite(result):
        return None

    return result


def safe_div(
    numerator: Optional[float],
    denominator: Optional[float],
) -> Optional[float]:

    if numerator is None or denominator is None:
        return None

    if denominator == 0:
        return None

    return numerator / denominator


# ============================================================================
# TARGET DEFINITION
# ============================================================================

@dataclass(frozen=True)
class TargetDefinition:
    """
    Formal declaration of one target.

    threshold:
        Directional classification threshold expressed as a return fraction.

        Example:
            0.001 = 0.10%

    The threshold is part of the experiment contract and must not be
    silently changed during evaluation.
    """

    horizon: int
    threshold: float = 0.0
    neutral_band: Optional[float] = None

    def __post_init__(self) -> None:
        if self.horizon <= 0:
            raise ValueError("horizon must be positive")

        if self.threshold < 0:
            raise ValueError("threshold cannot be negative")

        if self.neutral_band is not None and self.neutral_band < 0:
            raise ValueError("neutral_band cannot be negative")


def default_target_definitions() -> Tuple[TargetDefinition, ...]:
    return tuple(
        TargetDefinition(
            horizon=horizon,
            threshold=0.0,
            neutral_band=0.0,
        )
        for horizon in HORIZONS
    )


# ============================================================================
# OUTCOME RECORD
# ============================================================================

@dataclass(frozen=True)
class Outcome:
    """
    Historical future outcome.

    IMPORTANT:
    Everything after `evaluation_timestamp` is target/evaluation information.
    It must never be fed into a state representation for the same timestamp.
    """

    horizon: int

    evaluation_timestamp: Any
    completion_timestamp: Any

    start_price: float
    future_close: float

    return_pct: float
    direction: OutcomeDirection

    atr_at_evaluation: Optional[float]
    atr_normalized_return: Optional[float]

    future_high: Optional[float]
    future_low: Optional[float]

    mfe: Optional[float]
    mae: Optional[float]

    mfe_atr: Optional[float]
    mae_atr: Optional[float]

    time_to_mfe: Optional[int]
    time_to_mae: Optional[int]

    quality: OutcomeQuality = OutcomeQuality.COMPLETE

    target_index: Optional[int] = None

    @property
    def return_fraction(self) -> float:
        return self.return_pct / 100.0

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)

        data["direction"] = self.direction.value
        data["quality"] = self.quality.value

        return data


# ============================================================================
# DIRECTION CLASSIFICATION
# ============================================================================

def classify_direction(
    return_fraction: float,
    *,
    threshold: float = 0.0,
    neutral_band: Optional[float] = None,
) -> OutcomeDirection:

    if neutral_band is None:
        neutral_band = threshold

    if neutral_band < 0:
        raise ValueError("neutral_band cannot be negative")

    if return_fraction > neutral_band:
        return OutcomeDirection.HIGHER

    if return_fraction < -neutral_band:
        return OutcomeDirection.LOWER

    return OutcomeDirection.NEUTRAL


# ============================================================================
# MFE / MAE
# ============================================================================

def calculate_excursions(
    entry_price: float,
    future_candles: Sequence[Candle],
) -> Tuple[
    Optional[float],
    Optional[float],
    Optional[int],
    Optional[int],
    Optional[float],
    Optional[float],
]:

    if not future_candles:
        return None, None, None, None, None, None

    if entry_price <= 0:
        return None, None, None, None, None, None

    favorable_moves: List[float] = []
    adverse_moves: List[float] = []

    for candle in future_candles:
        high_move = candle.high - entry_price
        low_move = candle.low - entry_price

        favorable_moves.append(max(high_move, 0.0))
        adverse_moves.append(max(-low_move, 0.0))

    mfe = max(favorable_moves)
    mae = max(adverse_moves)

    mfe_index = favorable_moves.index(mfe) + 1
    mae_index = adverse_moves.index(mae) + 1

    mfe_pct = safe_div(mfe, entry_price)
    mae_pct = safe_div(mae, entry_price)

    return (
        mfe,
        mae,
        mfe_index,
        mae_index,
        mfe_pct,
        mae_pct,
    )


# ============================================================================
# OUTCOME GENERATION
# ============================================================================

def make_outcome(
    candles: Sequence[Candle],
    index: int,
    horizon: int,
    *,
    atr: Optional[float] = None,
    threshold: float = 0.0,
    neutral_band: Optional[float] = None,
) -> Outcome:

    if horizon <= 0:
        raise ValueError("horizon must be positive")

    if index < 0 or index >= len(candles):
        raise IndexError("evaluation index out of range")

    for candle in candles:
        candle.validate()

    target_index = index + horizon

    evaluation_candle = candles[index]

    # ----------------------------------------------------------------------
    # INCOMPLETE FUTURE WINDOW
    # ----------------------------------------------------------------------

    if target_index >= len(candles):
        return Outcome(
            horizon=horizon,
            evaluation_timestamp=evaluation_candle.timestamp,
            completion_timestamp=None,
            start_price=evaluation_candle.close,
            future_close=float("nan"),
            return_pct=float("nan"),
            direction=OutcomeDirection.NEUTRAL,
            atr_at_evaluation=atr,
            atr_normalized_return=None,
            future_high=None,
            future_low=None,
            mfe=None,
            mae=None,
            mfe_atr=None,
            mae_atr=None,
            time_to_mfe=None,
            time_to_mae=None,
            quality=OutcomeQuality.INCOMPLETE,
            target_index=None,
        )

    target_candle = candles[target_index]

    start_price = evaluation_candle.close
    future_close = target_candle.close

    if start_price <= 0:
        raise ValueError("evaluation close must be positive")

    return_fraction = (
        future_close - start_price
    ) / start_price

    return_pct = return_fraction * 100.0

    direction = classify_direction(
        return_fraction,
        threshold=threshold,
        neutral_band=neutral_band,
    )

    future_window = candles[index + 1 : target_index + 1]

    future_high = max(c.high for c in future_window)
    future_low = min(c.low for c in future_window)

    (
        mfe,
        mae,
        time_to_mfe,
        time_to_mae,
        mfe_pct,
        mae_pct,
    ) = calculate_excursions(
        start_price,
        future_window,
    )

    atr_normalized_return = safe_div(
        future_close - start_price,
        atr,
    )

    mfe_atr = safe_div(mfe, atr)
    mae_atr = safe_div(mae, atr)

    return Outcome(
        horizon=horizon,
        evaluation_timestamp=evaluation_candle.timestamp,
        completion_timestamp=target_candle.timestamp,
        start_price=start_price,
        future_close=future_close,
        return_pct=return_pct,
        direction=direction,
        atr_at_evaluation=atr,
        atr_normalized_return=atr_normalized_return,
        future_high=future_high,
        future_low=future_low,
        mfe=mfe,
        mae=mae,
        mfe_atr=mfe_atr,
        mae_atr=mae_atr,
        time_to_mfe=time_to_mfe,
        time_to_mae=time_to_mae,
        quality=OutcomeQuality.COMPLETE,
        target_index=target_index,
    )


# ============================================================================
# BATCH OUTCOME GENERATION
# ============================================================================

def generate_outcomes(
    candles: Sequence[Candle],
    *,
    horizons: Sequence[int] = HORIZONS,
    atr_values: Optional[Sequence[Optional[float]]] = None,
    threshold_by_horizon: Optional[Dict[int, float]] = None,
    neutral_band_by_horizon: Optional[Dict[int, float]] = None,
    include_incomplete: bool = False,
) -> List[Outcome]:

    if not candles:
        return []

    normalized_horizons = tuple(sorted(set(int(h) for h in horizons)))

    for horizon in normalized_horizons:
        if horizon <= 0:
            raise ValueError("all horizons must be positive")

    if atr_values is not None and len(atr_values) != len(candles):
        raise ValueError(
            "atr_values length must equal candle count"
        )

    threshold_by_horizon = threshold_by_horizon or {}
    neutral_band_by_horizon = neutral_band_by_horizon or {}

    results: List[Outcome] = []

    for index in range(len(candles)):

        atr = (
            atr_values[index]
            if atr_values is not None
            else None
        )

        for horizon in normalized_horizons:

            outcome = make_outcome(
                candles,
                index,
                horizon,
                atr=atr,
                threshold=threshold_by_horizon.get(
                    horizon,
                    0.0,
                ),
                neutral_band=neutral_band_by_horizon.get(
                    horizon,
                    None,
                ),
            )

            if (
                outcome.quality == OutcomeQuality.COMPLETE
                or include_incomplete
            ):
                results.append(outcome)

    return results


# ============================================================================
# OUTCOME DISTRIBUTION
# ============================================================================

@dataclass(frozen=True)
class OutcomeDistribution:
    horizon: int

    sample_count: int

    higher_count: int
    lower_count: int
    neutral_count: int

    higher_rate: float
    lower_rate: float
    neutral_rate: float

    mean_return_pct: Optional[float]
    median_return_pct: Optional[float]

    mean_atr_normalized_return: Optional[float]

    mean_mfe_atr: Optional[float]
    mean_mae_atr: Optional[float]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _median(values: Sequence[float]) -> Optional[float]:
    if not values:
        return None

    ordered = sorted(values)
    n = len(ordered)

    middle = n // 2

    if n % 2:
        return ordered[middle]

    return (
        ordered[middle - 1]
        + ordered[middle]
    ) / 2.0


def _mean(values: Sequence[float]) -> Optional[float]:
    if not values:
        return None

    return sum(values) / len(values)


def aggregate_outcomes(
    outcomes: Iterable[Outcome],
    *,
    horizon: int,
) -> OutcomeDistribution:

    selected = [
        outcome
        for outcome in outcomes
        if outcome.horizon == horizon
        and outcome.quality == OutcomeQuality.COMPLETE
    ]

    sample_count = len(selected)

    higher_count = sum(
        outcome.direction == OutcomeDirection.HIGHER
        for outcome in selected
    )

    lower_count = sum(
        outcome.direction == OutcomeDirection.LOWER
        for outcome in selected
    )

    neutral_count = sum(
        outcome.direction == OutcomeDirection.NEUTRAL
        for outcome in selected
    )

    if sample_count:
        higher_rate = higher_count / sample_count
        lower_rate = lower_count / sample_count
        neutral_rate = neutral_count / sample_count
    else:
        higher_rate = 0.0
        lower_rate = 0.0
        neutral_rate = 0.0

    returns = [
        outcome.return_pct
        for outcome in selected
        if math.isfinite(outcome.return_pct)
    ]

    atr_returns = [
        outcome.atr_normalized_return
        for outcome in selected
        if outcome.atr_normalized_return is not None
    ]

    mfe_atr = [
        outcome.mfe_atr
        for outcome in selected
        if outcome.mfe_atr is not None
    ]

    mae_atr = [
        outcome.mae_atr
        for outcome in selected
        if outcome.mae_atr is not None
    ]

    return OutcomeDistribution(
        horizon=horizon,
        sample_count=sample_count,
        higher_count=higher_count,
        lower_count=lower_count,
        neutral_count=neutral_count,
        higher_rate=higher_rate,
        lower_rate=lower_rate,
        neutral_rate=neutral_rate,
        mean_return_pct=_mean(returns),
        median_return_pct=_median(returns),
        mean_atr_normalized_return=_mean(atr_returns),
        mean_mfe_atr=_mean(mfe_atr),
        mean_mae_atr=_mean(mae_atr),
    )


# ============================================================================
# TARGET WINDOW
# ============================================================================

@dataclass(frozen=True)
class TargetWindow:
    """
    Explicit future dependency window.

    start_index:
        Evaluation candle.

    end_index:
        Last future candle used by the target.

    Nothing inside this window may be treated as a causal input to the
    observation at start_index.
    """

    start_index: int
    end_index: int
    horizon: int

    @property
    def future_indices(self) -> Tuple[int, ...]:
        if self.end_index <= self.start_index:
            return ()

        return tuple(
            range(
                self.start_index + 1,
                self.end_index + 1,
            )
        )


def make_target_window(
    index: int,
    horizon: int,
) -> TargetWindow:

    if index < 0:
        raise ValueError("index cannot be negative")

    if horizon <= 0:
        raise ValueError("horizon must be positive")

    return TargetWindow(
        start_index=index,
        end_index=index + horizon,
        horizon=horizon,
    )


# ============================================================================
# OVERLAP DETECTION
# ============================================================================

def target_windows_overlap(
    left: TargetWindow,
    right: TargetWindow,
) -> bool:

    return not (
        left.end_index < right.start_index
        or right.end_index < left.start_index
    )


def find_overlapping_windows(
    windows: Sequence[TargetWindow],
) -> List[Tuple[int, int]]:

    overlaps: List[Tuple[int, int]] = []

    for i in range(len(windows)):
        for j in range(i + 1, len(windows)):

            if target_windows_overlap(
                windows[i],
                windows[j],
            ):
                overlaps.append((i, j))

    return overlaps


# ============================================================================
# CAUSAL BOUNDARY AUDIT
# ============================================================================

@dataclass(frozen=True)
class BoundaryAuditResult:
    passed: bool
    evaluated_index: int
    horizon: int
    target_end_index: int
    input_max_index: int
    future_indices: Tuple[int, ...]
    violations: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def audit_target_boundary(
    *,
    evaluated_index: int,
    horizon: int,
    input_indices: Iterable[int],
) -> BoundaryAuditResult:

    window = make_target_window(
        evaluated_index,
        horizon,
    )

    violations: List[str] = []

    for input_index in input_indices:

        if input_index > evaluated_index:
            violations.append(
                "future input index detected: "
                f"{input_index} > {evaluated_index}"
            )

    input_max = max(
        input_indices,
        default=evaluated_index,
    )

    passed = not violations

    return BoundaryAuditResult(
        passed=passed,
        evaluated_index=evaluated_index,
        horizon=horizon,
        target_end_index=window.end_index,
        input_max_index=input_max,
        future_indices=window.future_indices,
        violations=tuple(violations),
    )


# ============================================================================
# DATASET / CONTRACT FINGERPRINT
# ============================================================================

def contract_payload() -> Dict[str, Any]:
    return {
        "contract_name": CONTRACT_NAME,
        "contract_version": CONTRACT_VERSION,
        "horizons": list(HORIZONS),
        "field_contracts": [
            {
                "name": item.name,
                "role": item.role.value,
                "description": item.description,
                "availability_rule": item.availability_rule,
            }
            for item in FIELD_CONTRACTS
        ],
    }


def contract_hash() -> str:
    payload = json.dumps(
        contract_payload(),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    return hashlib.sha256(payload).hexdigest()


# ============================================================================
# VALIDATION HELPERS
# ============================================================================

def validate_horizon_contract(
    horizons: Sequence[int],
) -> None:

    if not horizons:
        raise ValueError("At least one horizon is required")

    normalized = tuple(sorted(set(horizons)))

    for horizon in normalized:
        if not isinstance(horizon, int):
            raise TypeError(
                f"horizon must be int, got {type(horizon)}"
            )

        if horizon <= 0:
            raise ValueError(
                f"horizon must be positive: {horizon}"
            )


def validate_outcome(outcome: Outcome) -> None:

    if outcome.horizon <= 0:
        raise ValueError("invalid outcome horizon")

    if outcome.quality == OutcomeQuality.INCOMPLETE:
        return

    if outcome.quality != OutcomeQuality.COMPLETE:
        raise ValueError(
            f"invalid outcome quality: {outcome.quality}"
        )

    if not math.isfinite(outcome.start_price):
        raise ValueError("invalid start price")

    if not math.isfinite(outcome.future_close):
        raise ValueError("invalid future close")

    if not math.isfinite(outcome.return_pct):
        raise ValueError("invalid return")

    if outcome.completion_timestamp is None:
        raise ValueError(
            "complete outcome requires completion timestamp"
        )


# ============================================================================
# SELF-TEST
# ============================================================================

def _build_test_candles(count: int = 30) -> List[Candle]:
    candles: List[Candle] = []

    price = 100.0

    for index in range(count):

        open_price = price
        close_price = price + 0.25

        high = close_price + 0.10
        low = open_price - 0.10

        candles.append(
            Candle(
                timestamp=index,
                open=open_price,
                high=high,
                low=low,
                close=close_price,
            )
        )

        price = close_price

    return candles


def run_self_test() -> Dict[str, Any]:

    candles = _build_test_candles()

    # --------------------------------------------------------------
    # Basic target generation
    # --------------------------------------------------------------

    outcome = make_outcome(
        candles,
        index=5,
        horizon=4,
        atr=0.50,
    )

    validate_outcome(outcome)

    assert outcome.quality == OutcomeQuality.COMPLETE
    assert outcome.target_index == 9
    assert outcome.completion_timestamp == 9
    assert outcome.future_close > outcome.start_price
    assert outcome.direction == OutcomeDirection.HIGHER

    # --------------------------------------------------------------
    # Incomplete target
    # --------------------------------------------------------------

    incomplete = make_outcome(
        candles,
        index=28,
        horizon=4,
    )

    assert incomplete.quality == OutcomeQuality.INCOMPLETE

    # --------------------------------------------------------------
    # Boundary test
    # --------------------------------------------------------------

    boundary = audit_target_boundary(
        evaluated_index=10,
        horizon=4,
        input_indices=range(0, 11),
    )

    assert boundary.passed

    bad_boundary = audit_target_boundary(
        evaluated_index=10,
        horizon=4,
        input_indices=range(0, 12),
    )

    assert not bad_boundary.passed

    # --------------------------------------------------------------
    # Overlap test
    # --------------------------------------------------------------

    window_a = make_target_window(10, 4)
    window_b = make_target_window(12, 4)

    assert target_windows_overlap(
        window_a,
        window_b,
    )

    window_c = make_target_window(20, 4)

    assert not target_windows_overlap(
        window_a,
        window_c,
    )

    # --------------------------------------------------------------
    # Batch generation
    # --------------------------------------------------------------

    outcomes = generate_outcomes(
        candles,
        horizons=(4, 8, 16),
        include_incomplete=False,
    )

    assert outcomes

    distribution = aggregate_outcomes(
        outcomes,
        horizon=4,
    )

    assert distribution.sample_count > 0

    # --------------------------------------------------------------
    # Contract hash
    # --------------------------------------------------------------

    fingerprint = contract_hash()

    assert len(fingerprint) == 64

    return {
        "status": "PASS",
        "contract": CONTRACT_NAME,
        "version": CONTRACT_VERSION,
        "horizons": list(HORIZONS),
        "contract_hash": fingerprint,
        "generated_outcomes": len(outcomes),
        "h4_samples": distribution.sample_count,
    }


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":

    result = run_self_test()

    print("=" * 80)
    print("MLAI CANONICAL TARGET / OUTCOME CONTRACT")
    print("=" * 80)

    print(f"Status          : {result['status']}")
    print(f"Contract        : {result['contract']}")
    print(f"Version         : {result['version']}")
    print(f"Horizons        : {result['horizons']}")
    print(f"Contract SHA256  : {result['contract_hash']}")
    print(f"Generated        : {result['generated_outcomes']}")
    print(f"H4 samples       : {result['h4_samples']}")

    print("=" * 80)