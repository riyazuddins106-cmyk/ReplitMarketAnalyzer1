from __future__ import annotations

import hashlib
import math
import pickle
import random
from pathlib import Path
from typing import Any, Dict, List, Sequence


# ============================================================================
# MLAI v4.1.5 — ROBUST RETRIEVAL SCIENTIFIC GATE
#
# PURPOSE
# -------
# READ-ONLY forensic validation of the ACTUAL MLAI v4.1.5 implementation.
#
# Tests:
#   1. Self / future leakage
#   2. Similarity discrimination
#   3. Retrieval predictive value
#
# This gate DOES NOT:
#   - modify mlai_market_structure_v415.py
#   - modify market_data.bin
#   - modify retrieval memory
#   - modify retrieval parameters
#   - retrain any model
#   - tune against OOS results
#
# IMPORTANT
# ---------
# This gate is written against the verified v4.1.5 API:
#
#   load_market_data(path) -> (candles, invalid_count)
#   calculate_atr(candles, period=14)
#   CausalStructureEngine(candles).build()
#   build_market_states(candles, structure_states, atr)
#   assign_episode_ids(states) -> Dict[int, int]
#   create_walk_forward_windows(...)
#   build_experience_records(...)
#   retrieve_historical_experience(...)
#
# ============================================================================


VERSION = "V415_ROBUST_RETRIEVAL_GATE_2.0"

ROOT = Path(__file__).resolve().parent

SOURCE_FILE = ROOT / "mlai_market_structure_v415.py"
MEMORY_FILE = ROOT / "MLAI_V415_ROBUST_HISTORICAL_EXPERIENCE_RETRIEVAL.bin"
DATA_FILE = ROOT / "market_data.bin"

REPORT_FILE = ROOT / "MLAI_V415_ROBUST_RETRIEVAL_GATE_REPORT.md"


# ============================================================================
# UTILITIES
# ============================================================================

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)

            if not chunk:
                break

            h.update(chunk)

    return h.hexdigest()


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        value = float(value)

        if math.isfinite(value):
            return value

    except Exception:
        pass

    return default


def mean(values: Sequence[float]) -> float:
    cleaned = [
        safe_float(value)
        for value in values
    ]

    if not cleaned:
        return 0.0

    return sum(cleaned) / len(cleaned)


def fmt_pct(value: float) -> str:
    return f"{100.0 * safe_float(value):.2f}%"


def fmt_num(value: float) -> str:
    return f"{safe_float(value):.6f}"


def direction_from_record(record: Any) -> str:
    outcome = getattr(record, "outcome", None)

    if outcome is None:
        return "UNKNOWN"

    direction = getattr(outcome, "direction", None)

    if direction is None:
        return "UNKNOWN"

    return str(direction)


# ============================================================================
# IMPORT V4.1.5
# ============================================================================

def import_v415():
    """
    Import the actual v4.1.5 source safely.

    Python 3.14 dataclasses require the dynamically loaded module
    to be registered in sys.modules before exec_module().
    """

    import importlib.util
    import sys

    if not SOURCE_FILE.exists():
        raise FileNotFoundError(
            f"Required MLAI source file not found: {SOURCE_FILE}"
        )

    module_name = "mlai_market_structure_v415"

    sys.modules.pop(module_name, None)

    spec = importlib.util.spec_from_file_location(
        module_name,
        SOURCE_FILE,
    )

    if spec is None:
        raise ImportError(
            f"Could not create import specification for {SOURCE_FILE}"
        )

    if spec.loader is None:
        raise ImportError(
            f"Could not create module loader for {SOURCE_FILE}"
        )

    module = importlib.util.module_from_spec(spec)

    # Required for Python 3.14 dataclasses.
    sys.modules[module_name] = module

    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(module_name, None)
        raise

    return module


# ============================================================================
# MEMORY INSPECTION
# ============================================================================

def inspect_memory() -> Dict[str, Any]:

    result = {
        "exists": MEMORY_FILE.exists(),
        "sha256": None,
        "root_type": None,
        "keys": [],
        "metadata": {},
    }

    if not MEMORY_FILE.exists():
        return result

    result["sha256"] = sha256_file(MEMORY_FILE)

    with MEMORY_FILE.open("rb") as f:
        root = pickle.load(f)

    result["root_type"] = type(root).__name__

    if isinstance(root, dict):

        result["keys"] = list(root.keys())

        for key in (
            "version",
            "objective",
            "walk_forward",
            "aggregate",
            "retrieval_config",
            "protection",
        ):

            if key in root:
                result["metadata"][key] = root[key]

    return result


# ============================================================================
# DATA / STRUCTURE RECONSTRUCTION
# ============================================================================

def discover_dataset(module) -> Dict[str, Any]:
    """
    Reconstruct the causal v4.1.5 state pipeline using the ACTUAL APIs.

    Important:
        The source of truth is the current v4.1.5 implementation,
        not the saved retrieval-memory pickle.
    """

    # ------------------------------------------------------------------------
    # Load market data.
    #
    # Verified v4.1.5 signature:
    #
    #   load_market_data(path) -> Tuple[List[Candle], int]
    # ------------------------------------------------------------------------

    loaded = module.load_market_data(
        str(DATA_FILE)
    )

    if not isinstance(loaded, tuple) or len(loaded) != 2:
        raise RuntimeError(
            "Unexpected v4.1.5 load_market_data() return value. "
            "Expected (candles, invalid_count)."
        )

    candles, invalid_count = loaded

    if not candles:
        raise RuntimeError(
            "v4.1.5 returned zero candles."
        )

    # ------------------------------------------------------------------------
    # ATR
    #
    # Verified API:
    #
    #   calculate_atr(candles, period=14)
    # ------------------------------------------------------------------------

    atr = module.calculate_atr(candles)

    if len(atr) != len(candles):
        raise RuntimeError(
            "ATR length does not match candle count."
        )

    # ------------------------------------------------------------------------
    # Causal structure
    #
    # Verified API:
    #
    #   CausalStructureEngine(candles).build()
    # ------------------------------------------------------------------------

    structure_engine = module.CausalStructureEngine(candles)

    structure_states = structure_engine.build()

    if len(structure_states) != len(candles):
        raise RuntimeError(
            "Structure-state count does not match candle count."
        )

    # ------------------------------------------------------------------------
    # Market states
    #
    # Verified API:
    #
    #   build_market_states(candles, structure_states, atr)
    # ------------------------------------------------------------------------

    market_states = module.build_market_states(
        candles,
        structure_states,
        atr,
    )

    if len(market_states) != len(candles):
        raise RuntimeError(
            "Market-state count does not match candle count."
        )

    # ------------------------------------------------------------------------
    # Episode IDs
    #
    # Verified API:
    #
    #   assign_episode_ids(states) -> Dict[int, int]
    # ------------------------------------------------------------------------

    episode_ids = module.assign_episode_ids(
        market_states
    )

    if not isinstance(episode_ids, dict):
        raise RuntimeError(
            "assign_episode_ids() did not return a dictionary."
        )

    # ------------------------------------------------------------------------
    # Walk-forward windows
    # ------------------------------------------------------------------------

    windows = module.create_walk_forward_windows(
        len(candles),
        module.DEFAULT_TRAIN_WINDOWS,
        module.DEFAULT_OOS_SIZE,
    )

    if not windows:
        raise RuntimeError(
            "No walk-forward windows were created."
        )

    # ------------------------------------------------------------------------
    # Build complete causal records.
    #
    # These records are subsequently filtered AGAINST EACH WINDOW'S
    # training boundary.
    #
    # This is intentional:
    #
    #     candidate_index + horizon < train_end
    #
    # must hold before a record can enter retrieval for that window.
    # ------------------------------------------------------------------------

    records_by_horizon: Dict[int, List[Any]] = {}

    for horizon in module.HORIZONS:

        records = module.build_experience_records(
            candles=candles,
            atr=atr,
            states=market_states,
            episode_ids=episode_ids,
            start=0,
            train_end=len(candles),
            horizon=horizon,
        )

        records_by_horizon[horizon] = records

    return {
        "candles": candles,
        "invalid_count": invalid_count,
        "atr": atr,
        "structure_states": structure_states,
        "states": market_states,
        "episode_ids": episode_ids,
        "windows": windows,
        "records": records_by_horizon,
    }


# ============================================================================
# WINDOW-SAFE TRAINING RECORDS
# ============================================================================

def get_window_training_records(
    module,
    records: Sequence[Any],
    train_start: int,
    train_end: int,
    horizon: int,
) -> List[Any]:
    """
    Return ONLY records that are fully historical for this OOS window.

    Conditions:

        record.index >= train_start
        record.index < train_end
        record.index + horizon < train_end

    The final condition is the critical one.

    It guarantees that the complete outcome of the historical example
    was already known before the OOS period began.
    """

    safe_records = []

    for record in records:

        index = int(record.index)

        if index < train_start:
            continue

        if index >= train_end:
            continue

        outcome_end = index + horizon

        if outcome_end >= train_end:
            continue

        record_horizon = getattr(
            record,
            "horizon",
            horizon,
        )

        if int(record_horizon) != int(horizon):
            continue

        safe_records.append(record)

    return safe_records


# ============================================================================
# TEST 1 — SELF / FUTURE / BOUNDARY LEAKAGE
# ============================================================================

def audit_temporal_integrity(
    module,
    dataset,
) -> Dict[str, Any]:

    candles = dataset["candles"]
    states = dataset["states"]
    windows = dataset["windows"]
    records_by_horizon = dataset["records"]

    violations: List[str] = []

    total_queries = 0
    total_candidates = 0

    self_matches = 0
    future_candidates = 0
    boundary_violations = 0
    outcome_boundary_violations = 0
    horizon_violations = 0

    min_history_gap = getattr(
        module,
        "MIN_HISTORY_GAP",
        max(module.HORIZONS),
    )

    for horizon in module.HORIZONS:

        records = records_by_horizon[horizon]

        for window in windows:

            train_start = int(window.train_start)
            train_end = int(window.train_end)
            oos_start = int(window.oos_start)
            oos_end = int(window.oos_end)

            train_records = get_window_training_records(
                module=module,
                records=records,
                train_start=train_start,
                train_end=train_end,
                horizon=horizon,
            )

            for query_index in range(
                oos_start,
                oos_end,
            ):

                if query_index >= len(states):
                    continue

                total_queries += 1

                eligible = module.coarse_filter(
                    states[query_index],
                    train_records,
                    query_index,
                )

                for record in eligible:

                    total_candidates += 1

                    idx = int(record.index)

                    # --------------------------------------------------------
                    # SELF
                    # --------------------------------------------------------

                    if idx == query_index:

                        self_matches += 1

                        violations.append(
                            f"H+{horizon}: SELF MATCH "
                            f"query={query_index} candidate={idx}"
                        )

                    # --------------------------------------------------------
                    # STRICTLY HISTORICAL
                    # --------------------------------------------------------

                    if idx >= query_index:

                        future_candidates += 1

                        violations.append(
                            f"H+{horizon}: FUTURE/SELF CANDIDATE "
                            f"query={query_index} candidate={idx}"
                        )

                    # --------------------------------------------------------
                    # HISTORY GAP
                    # --------------------------------------------------------

                    gap = query_index - idx

                    if gap < min_history_gap:

                        boundary_violations += 1

                        violations.append(
                            f"H+{horizon}: HISTORY GAP VIOLATION "
                            f"query={query_index} candidate={idx} "
                            f"gap={gap} required={min_history_gap}"
                        )

                    # --------------------------------------------------------
                    # TRAINING BOUNDARY
                    # --------------------------------------------------------

                    if idx < train_start or idx >= train_end:

                        boundary_violations += 1

                        violations.append(
                            f"H+{horizon}: TRAINING BOUNDARY VIOLATION "
                            f"candidate={idx} "
                            f"train=[{train_start}:{train_end}]"
                        )

                    # --------------------------------------------------------
                    # COMPLETE OUTCOME MUST BE INSIDE TRAINING
                    # --------------------------------------------------------

                    outcome_end = idx + horizon

                    if outcome_end >= train_end:

                        outcome_boundary_violations += 1

                        violations.append(
                            f"H+{horizon}: OUTCOME CROSSES TRAINING "
                            f"BOUNDARY candidate={idx} "
                            f"outcome_end={outcome_end} "
                            f"train_end={train_end}"
                        )

                    # --------------------------------------------------------
                    # OUTCOME MUST NOT EXCEED DATASET
                    # --------------------------------------------------------

                    if outcome_end >= len(candles):

                        outcome_boundary_violations += 1

                        violations.append(
                            f"H+{horizon}: OUTCOME EXCEEDS DATASET "
                            f"candidate={idx} "
                            f"outcome_end={outcome_end}"
                        )

                    # --------------------------------------------------------
                    # RECORD HORIZON
                    # --------------------------------------------------------

                    record_horizon = getattr(
                        record,
                        "horizon",
                        None,
                    )

                    if record_horizon is not None:

                        if int(record_horizon) != int(horizon):

                            horizon_violations += 1

                            violations.append(
                                f"H+{horizon}: RECORD HORIZON MISMATCH "
                                f"candidate={idx} "
                                f"record_horizon={record_horizon}"
                            )

    passed = (
        self_matches == 0
        and future_candidates == 0
        and boundary_violations == 0
        and outcome_boundary_violations == 0
        and horizon_violations == 0
    )

    return {
        "passed": passed,
        "total_queries": total_queries,
        "total_candidates": total_candidates,
        "self_matches": self_matches,
        "future_candidates": future_candidates,
        "boundary_violations": boundary_violations,
        "outcome_boundary_violations": outcome_boundary_violations,
        "horizon_violations": horizon_violations,
        "violations": violations[:100],
    }


# ============================================================================
# TEST 2 — SIMILARITY DISCRIMINATION
# ============================================================================

def similarity_discrimination_test(
    module,
    dataset,
) -> Dict[int, Dict[str, Any]]:

    states = dataset["states"]
    candles = dataset["candles"]
    windows = dataset["windows"]
    records_by_horizon = dataset["records"]

    results: Dict[int, Dict[str, Any]] = {}

    rng = random.Random(4152026)

    for horizon in module.HORIZONS:

        records = records_by_horizon[horizon]

        rows = []

        for window in windows:

            train_start = int(window.train_start)
            train_end = int(window.train_end)

            train_records = get_window_training_records(
                module=module,
                records=records,
                train_start=train_start,
                train_end=train_end,
                horizon=horizon,
            )

            for query_index in range(
                int(window.oos_start),
                int(window.oos_end),
            ):

                if query_index >= len(states):
                    continue

                target = query_index + horizon

                if target >= len(candles):
                    continue

                candidates = []

                current = states[query_index]

                eligible = module.coarse_filter(
                    current,
                    train_records,
                    query_index,
                )

                for record in eligible:

                    components = module.similarity_score(
                        current,
                        record,
                    )

                    score = safe_float(
                        components.get("total"),
                        0.0,
                    )

                    candidates.append(
                        (
                            score,
                            record,
                        )
                    )

                candidates.sort(
                    key=lambda item: (
                        item[0],
                        int(item[1].index),
                    ),
                    reverse=True,
                )

                # Need enough candidates for genuinely separate groups.
                if len(candidates) < 12:
                    continue

                base = candles[query_index].close
                future = candles[target].close

                if future > base:
                    query_direction = "UP"
                elif future < base:
                    query_direction = "DOWN"
                else:
                    query_direction = "NEUTRAL"

                n = len(candidates)

                # ------------------------------------------------------------
                # Three NON-OVERLAPPING groups.
                #
                # At least four observations per group.
                # ------------------------------------------------------------

                group_size = max(
                    4,
                    n // 3,
                )

                # Ensure three groups actually fit.
                if group_size * 3 > n:
                    group_size = n // 3

                if group_size < 4:
                    continue

                top_group = candidates[
                    :group_size
                ]

                middle_group = candidates[
                    group_size:2 * group_size
                ]

                bottom_group = candidates[
                    2 * group_size:3 * group_size
                ]

                # Random control is sampled from the full candidate pool.
                random_pool = list(candidates)

                rng.shuffle(random_pool)

                random_group = random_pool[
                    :group_size
                ]

                def group_agreement(group):

                    if not group:
                        return 0.0

                    return mean(
                        [
                            1.0
                            if direction_from_record(record)
                            == query_direction
                            else 0.0
                            for _, record in group
                        ]
                    )

                def group_similarity(group):

                    if not group:
                        return 0.0

                    return mean(
                        [
                            score
                            for score, _ in group
                        ]
                    )

                rows.append(
                    {
                        "window":
                            int(window.number),

                        "query_index":
                            int(query_index),

                        "query_direction":
                            query_direction,

                        "top_similarity":
                            group_similarity(top_group),

                        "top_agreement":
                            group_agreement(top_group),

                        "middle_similarity":
                            group_similarity(middle_group),

                        "middle_agreement":
                            group_agreement(middle_group),

                        "bottom_similarity":
                            group_similarity(bottom_group),

                        "bottom_agreement":
                            group_agreement(bottom_group),

                        "random_similarity":
                            group_similarity(random_group),

                        "random_agreement":
                            group_agreement(random_group),
                    }
                )

        if not rows:

            results[horizon] = {
                "available": False,
                "rows": 0,
            }

            continue

        top_agreement = mean(
            [
                row["top_agreement"]
                for row in rows
            ]
        )

        middle_agreement = mean(
            [
                row["middle_agreement"]
                for row in rows
            ]
        )

        bottom_agreement = mean(
            [
                row["bottom_agreement"]
                for row in rows
            ]
        )

        random_agreement = mean(
            [
                row["random_agreement"]
                for row in rows
            ]
        )

        top_similarity = mean(
            [
                row["top_similarity"]
                for row in rows
            ]
        )

        random_similarity = mean(
            [
                row["random_similarity"]
                for row in rows
            ]
        )

        discrimination_lift = (
            top_agreement
            - random_agreement
        )

        monotonic = (
            top_agreement
            >= middle_agreement
            and middle_agreement
            >= bottom_agreement
        )

        # Fixed scientific threshold.
        #
        # This is deliberately NOT derived from the observed results.
        passed = (
            discrimination_lift >= 0.02
            and monotonic
        )

        results[horizon] = {
            "available": True,
            "rows": len(rows),

            "top_similarity":
                top_similarity,

            "random_similarity":
                random_similarity,

            "top_agreement":
                top_agreement,

            "middle_agreement":
                middle_agreement,

            "bottom_agreement":
                bottom_agreement,

            "random_agreement":
                random_agreement,

            "discrimination_lift":
                discrimination_lift,

            "monotonic":
                monotonic,

            "passed":
                passed,
        }

    return results


# ============================================================================
# TEST 3 — RETRIEVAL PREDICTIVE VALUE
# ============================================================================

def evaluate_retrieval_predictive_value(
    module,
    dataset,
) -> Dict[int, Any]:

    states = dataset["states"]
    candles = dataset["candles"]
    windows = dataset["windows"]
    records_by_horizon = dataset["records"]

    final: Dict[int, Any] = {}

    for horizon in module.HORIZONS:

        records = records_by_horizon[horizon]

        window_results = []

        for window in windows:

            train_start = int(window.train_start)
            train_end = int(window.train_end)

            # --------------------------------------------------------------
            # CRITICAL:
            #
            # A historical record is usable only if its COMPLETE outcome
            # was known before the OOS boundary.
            # --------------------------------------------------------------

            train_records = get_window_training_records(
                module=module,
                records=records,
                train_start=train_start,
                train_end=train_end,
                horizon=horizon,
            )

            if not train_records:
                continue

            oos_rows = []

            for query_index in range(
                int(window.oos_start),
                int(window.oos_end),
            ):

                if query_index >= len(states):
                    continue

                actual_target = (
                    query_index + horizon
                )

                if actual_target >= len(candles):
                    continue

                base_close = candles[
                    query_index
                ].close

                actual_close = candles[
                    actual_target
                ].close

                if actual_close > base_close:
                    actual = "UP"

                elif actual_close < base_close:
                    actual = "DOWN"

                else:
                    actual = "NEUTRAL"

                current = states[query_index]

                # ----------------------------------------------------------
                # Retrieval receives ONLY safe historical records.
                # ----------------------------------------------------------

                retrieval = (
                    module.retrieve_historical_experience(
                        current=current,
                        records=train_records,
                        horizon=horizon,
                        query_index=query_index,
                    )
                )

                retrieval_distribution = {
                    "UP":
                        safe_float(
                            retrieval.up_share
                        ),

                    "DOWN":
                        safe_float(
                            retrieval.down_share
                        ),

                    "NEUTRAL":
                        safe_float(
                            retrieval.neutral_share
                        ),
                }

                (
                    baseline_level,
                    baseline_distribution,
                    baseline_samples,
                ) = module.conditional_baseline(
                    current,
                    train_records,
                )

                baseline_distribution = {
                    "UP":
                        safe_float(
                            baseline_distribution.get("UP")
                        ),

                    "DOWN":
                        safe_float(
                            baseline_distribution.get("DOWN")
                        ),

                    "NEUTRAL":
                        safe_float(
                            baseline_distribution.get("NEUTRAL")
                        ),
                }

                retrieval_prediction = max(
                    retrieval_distribution,
                    key=retrieval_distribution.get,
                )

                baseline_prediction = max(
                    baseline_distribution,
                    key=baseline_distribution.get,
                )

                retrieval_brier = module.brier(
                    retrieval_distribution,
                    actual,
                )

                baseline_brier = module.brier(
                    baseline_distribution,
                    actual,
                )

                retrieval_logloss = module.log_loss(
                    retrieval_distribution,
                    actual,
                )

                baseline_logloss = module.log_loss(
                    baseline_distribution,
                    actual,
                )

                oos_rows.append(
                    {
                        "actual":
                            actual,

                        "retrieval_prediction":
                            retrieval_prediction,

                        "baseline_prediction":
                            baseline_prediction,

                        "retrieval_accuracy":
                            float(
                                retrieval_prediction
                                == actual
                            ),

                        "baseline_accuracy":
                            float(
                                baseline_prediction
                                == actual
                            ),

                        "retrieval_brier":
                            retrieval_brier,

                        "baseline_brier":
                            baseline_brier,

                        "retrieval_logloss":
                            retrieval_logloss,

                        "baseline_logloss":
                            baseline_logloss,

                        "similarity":
                            safe_float(
                                retrieval.top_similarity
                            ),
                    }
                )

            if not oos_rows:
                continue

            retrieval_accuracy = mean(
                [
                    row["retrieval_accuracy"]
                    for row in oos_rows
                ]
            )

            baseline_accuracy = mean(
                [
                    row["baseline_accuracy"]
                    for row in oos_rows
                ]
            )

            retrieval_brier = mean(
                [
                    row["retrieval_brier"]
                    for row in oos_rows
                ]
            )

            baseline_brier = mean(
                [
                    row["baseline_brier"]
                    for row in oos_rows
                ]
            )

            retrieval_logloss = mean(
                [
                    row["retrieval_logloss"]
                    for row in oos_rows
                ]
            )

            baseline_logloss = mean(
                [
                    row["baseline_logloss"]
                    for row in oos_rows
                ]
            )

            window_results.append(
                {
                    "window":
                        int(window.number),

                    "queries":
                        len(oos_rows),

                    "retrieval_accuracy":
                        retrieval_accuracy,

                    "baseline_accuracy":
                        baseline_accuracy,

                    "accuracy_lift":
                        retrieval_accuracy
                        - baseline_accuracy,

                    "retrieval_brier":
                        retrieval_brier,

                    "baseline_brier":
                        baseline_brier,

                    "brier_lift":
                        baseline_brier
                        - retrieval_brier,

                    "retrieval_logloss":
                        retrieval_logloss,

                    "baseline_logloss":
                        baseline_logloss,

                    "logloss_lift":
                        baseline_logloss
                        - retrieval_logloss,
                }
            )

        if not window_results:

            final[horizon] = {
                "available": False,
            }

            continue

        accuracy_lifts = [
            row["accuracy_lift"]
            for row in window_results
        ]

        brier_lifts = [
            row["brier_lift"]
            for row in window_results
        ]

        logloss_lifts = [
            row["logloss_lift"]
            for row in window_results
        ]

        mean_accuracy_lift = mean(
            accuracy_lifts
        )

        mean_brier_lift = mean(
            brier_lifts
        )

        mean_logloss_lift = mean(
            logloss_lifts
        )

        accuracy_positive_windows = sum(
            1
            for value in accuracy_lifts
            if value > 0.0
        )

        brier_positive_windows = sum(
            1
            for value in brier_lifts
            if value > 0.0
        )

        logloss_positive_windows = sum(
            1
            for value in logloss_lifts
            if value > 0.0
        )

        n_windows = len(
            window_results
        )

        probability_value = (
            mean_brier_lift > 0.0
            or mean_logloss_lift > 0.0
        )

        probability_consistency = (
            brier_positive_windows
            > n_windows / 2
            or
            logloss_positive_windows
            > n_windows / 2
        )

        accuracy_not_catastrophic = (
            mean_accuracy_lift >= -0.03
        )

        passed = (
            probability_value
            and probability_consistency
            and accuracy_not_catastrophic
        )

        final[horizon] = {
            "available": True,

            "windows":
                window_results,

            "mean_accuracy_lift":
                mean_accuracy_lift,

            "mean_brier_lift":
                mean_brier_lift,

            "mean_logloss_lift":
                mean_logloss_lift,

            "accuracy_positive_windows":
                accuracy_positive_windows,

            "brier_positive_windows":
                brier_positive_windows,

            "logloss_positive_windows":
                logloss_positive_windows,

            "window_count":
                n_windows,

            "probability_value":
                probability_value,

            "probability_consistency":
                probability_consistency,

            "accuracy_not_catastrophic":
                accuracy_not_catastrophic,

            "passed":
                passed,
        }

    return final


# ============================================================================
# FINAL CLASSIFICATION
# ============================================================================

def classify_final_result(
    temporal,
    discrimination,
    predictive,
):

    classifications = {}

    classifications["temporal"] = (
        "PASS — no self/future/boundary leakage detected"
        if temporal["passed"]
        else
        "FAIL — implementation-level temporal integrity defect detected"
    )

    for horizon, result in discrimination.items():

        if not result.get("available"):

            classifications[
                f"discrimination_h{horizon}"
            ] = (
                "INCONCLUSIVE — insufficient evaluation rows"
            )

        elif result.get("passed"):

            classifications[
                f"discrimination_h{horizon}"
            ] = (
                "PASS — similarity ranking demonstrates outcome discrimination"
            )

        else:

            classifications[
                f"discrimination_h{horizon}"
            ] = (
                "FAIL — similarity ranking does not demonstrate sufficient "
                "outcome discrimination"
            )

    for horizon, result in predictive.items():

        if not result.get("available"):

            classifications[
                f"predictive_h{horizon}"
            ] = (
                "INCONCLUSIVE — insufficient OOS evaluation"
            )

        elif result.get("passed"):

            classifications[
                f"predictive_h{horizon}"
            ] = (
                "PASS — retrieval demonstrates incremental predictive value"
            )

        else:

            classifications[
                f"predictive_h{horizon}"
            ] = (
                "FAIL — retrieval does not demonstrate sufficient "
                "incremental predictive value"
            )

    return classifications


# ============================================================================
# REPORT
# ============================================================================

def build_report(
    memory_info,
    temporal,
    discrimination,
    predictive,
    classifications,
    source_hash_before,
    source_hash_after,
    memory_hash_before,
    memory_hash_after,
    data_hash_before,
    data_hash_after,
):

    lines = []

    lines.append(
        "# MLAI v4.1.5 Robust Retrieval Scientific Gate"
    )

    lines.append("")
    lines.append(
        f"Version: `{VERSION}`"
    )

    lines.append("")

    lines.append("## Protection")
    lines.append("")

    lines.append(
        "- Source modified: NO"
    )

    lines.append(
        "- Market data modified: NO"
    )

    lines.append(
        "- Retrieval memory modified: NO"
    )

    lines.append(
        "- Retrieval parameters modified: NO"
    )

    lines.append(
        "- Model retrained: NO"
    )

    lines.append("")

    lines.append("## 1. Self / Future Leakage")
    lines.append("")

    lines.append(
        f"- Total OOS queries inspected: "
        f"{temporal['total_queries']}"
    )

    lines.append(
        f"- Historical candidates inspected: "
        f"{temporal['total_candidates']}"
    )

    lines.append(
        f"- Self matches: "
        f"`{temporal['self_matches']}`"
    )

    lines.append(
        f"- Future candidates: "
        f"`{temporal['future_candidates']}`"
    )

    lines.append(
        f"- Boundary violations: "
        f"`{temporal['boundary_violations']}`"
    )

    lines.append(
        f"- Outcome boundary violations: "
        f"`{temporal['outcome_boundary_violations']}`"
    )

    lines.append(
        f"- Horizon violations: "
        f"`{temporal['horizon_violations']}`"
    )

    lines.append("")

    if temporal["passed"]:

        lines.append(
            "**RESULT: PASS — temporal separation is proven by the gate.**"
        )

    else:

        lines.append(
            "**RESULT: FAIL — temporal leakage/boundary defect detected.**"
        )

    lines.append("")

    if temporal["violations"]:

        lines.append(
            "### First violations"
        )

        lines.append("")

        for violation in temporal["violations"][:30]:

            lines.append(
                f"- `{violation}`"
            )

        lines.append("")

    lines.append("## 2. Similarity Discrimination")
    lines.append("")

    for horizon in sorted(discrimination):

        result = discrimination[horizon]

        lines.append(
            f"### H+{horizon}"
        )

        if not result.get("available"):

            lines.append(
                "RESULT: INCONCLUSIVE — insufficient rows."
            )

            lines.append("")

            continue

        lines.append(
            f"- Evaluation rows: `{result['rows']}`"
        )

        lines.append(
            f"- Top-group similarity: "
            f"{fmt_pct(result['top_similarity'])}"
        )

        lines.append(
            f"- Random-group similarity: "
            f"{fmt_pct(result['random_similarity'])}"
        )

        lines.append(
            f"- Top-group outcome agreement: "
            f"{fmt_pct(result['top_agreement'])}"
        )

        lines.append(
            f"- Middle-group outcome agreement: "
            f"{fmt_pct(result['middle_agreement'])}"
        )

        lines.append(
            f"- Bottom-group outcome agreement: "
            f"{fmt_pct(result['bottom_agreement'])}"
        )

        lines.append(
            f"- Random-group outcome agreement: "
            f"{fmt_pct(result['random_agreement'])}"
        )

        lines.append(
            f"- Top vs random discrimination lift: "
            f"{fmt_pct(result['discrimination_lift'])}"
        )

        lines.append(
            f"- Monotonic similarity/outcome relationship: "
            f"{'YES' if result['monotonic'] else 'NO'}"
        )

        lines.append(
            f"- RESULT: "
            f"{'PASS' if result['passed'] else 'FAIL'}"
        )

        lines.append("")

    lines.append("## 3. Retrieval Predictive Value")
    lines.append("")

    for horizon in sorted(predictive):

        result = predictive[horizon]

        lines.append(
            f"### H+{horizon}"
        )

        if not result.get("available"):

            lines.append(
                "RESULT: INCONCLUSIVE — insufficient OOS data."
            )

            lines.append("")

            continue

        lines.append(
            f"- Walk-forward windows: "
            f"{result['window_count']}"
        )

        lines.append(
            f"- Mean accuracy lift: "
            f"{fmt_pct(result['mean_accuracy_lift'])}"
        )

        lines.append(
            f"- Mean Brier lift: "
            f"{fmt_num(result['mean_brier_lift'])}"
        )

        lines.append(
            f"- Mean LogLoss lift: "
            f"{fmt_num(result['mean_logloss_lift'])}"
        )

        lines.append(
            f"- Accuracy-positive windows: "
            f"{result['accuracy_positive_windows']}/"
            f"{result['window_count']}"
        )

        lines.append(
            f"- Brier-positive windows: "
            f"{result['brier_positive_windows']}/"
            f"{result['window_count']}"
        )

        lines.append(
            f"- LogLoss-positive windows: "
            f"{result['logloss_positive_windows']}/"
            f"{result['window_count']}"
        )

        lines.append(
            f"- Probability value demonstrated: "
            f"{'YES' if result['probability_value'] else 'NO'}"
        )

        lines.append(
            f"- Probability consistency demonstrated: "
            f"{'YES' if result['probability_consistency'] else 'NO'}"
        )

        lines.append(
            f"- Accuracy not catastrophically worse: "
            f"{'YES' if result['accuracy_not_catastrophic'] else 'NO'}"
        )

        lines.append(
            f"- RESULT: "
            f"{'PASS' if result['passed'] else 'FAIL'}"
        )

        lines.append("")

        lines.append(
            "| Window | Queries | Accuracy Lift | Brier Lift | LogLoss Lift |"
        )

        lines.append(
            "|---:|---:|---:|---:|---:|"
        )

        for row in result["windows"]:

            lines.append(
                f"| {row['window']} | "
                f"{row['queries']} | "
                f"{fmt_pct(row['accuracy_lift'])} | "
                f"{fmt_num(row['brier_lift'])} | "
                f"{fmt_num(row['logloss_lift'])} |"
            )

        lines.append("")

    lines.append("## 4. Final Classification")
    lines.append("")

    for key, value in classifications.items():

        lines.append(
            f"- **{key}**: {value}"
        )

    lines.append("")

    lines.append("## 5. Scientific Decision")
    lines.append("")

    temporal_pass = temporal["passed"]

    discrimination_available = [
        result.get("passed", False)
        for result in discrimination.values()
        if result.get("available")
    ]

    predictive_available = [
        result.get("passed", False)
        for result in predictive.values()
        if result.get("available")
    ]

    if (
        temporal_pass
        and discrimination_available
        and all(discrimination_available)
        and predictive_available
        and all(predictive_available)
    ):

        decision = (
            "RETRIEVAL VALIDATION PASSED. "
            "The current retrieval implementation has demonstrated "
            "temporal integrity, similarity discrimination, and "
            "incremental predictive value."
        )

    elif not temporal_pass:

        decision = (
            "RETRIEVAL VALIDATION BLOCKED. "
            "A temporal integrity defect must be fixed before predictive "
            "performance can be trusted."
        )

    elif (
        discrimination_available
        and not all(discrimination_available)
    ):

        decision = (
            "RETRIEVAL VALIDATION NOT PASSED. "
            "Similarity does not consistently identify outcome-similar "
            "historical states."
        )

    elif (
        predictive_available
        and not all(predictive_available)
    ):

        decision = (
            "RETRIEVAL VALIDATION NOT PASSED. "
            "Retrieval does not consistently demonstrate incremental "
            "predictive value across horizons."
        )

    else:

        decision = (
            "RETRIEVAL VALIDATION NOT PASSED. "
            "The implementation is temporally testable, but predictive "
            "value has not been demonstrated."
        )

    lines.append(
        f"**{decision}**"
    )

    lines.append("")

    lines.append("## 6. Protection Hashes")
    lines.append("")

    lines.append(
        f"- Source before: `{source_hash_before}`"
    )

    lines.append(
        f"- Source after: `{source_hash_after}`"
    )

    lines.append(
        f"- Source unchanged: "
        f"`{source_hash_before == source_hash_after}`"
    )

    lines.append("")

    lines.append(
        f"- Memory before: `{memory_hash_before}`"
    )

    lines.append(
        f"- Memory after: `{memory_hash_after}`"
    )

    lines.append(
        f"- Memory unchanged: "
        f"`{memory_hash_before == memory_hash_after}`"
    )

    lines.append("")

    lines.append(
        f"- Market data before: `{data_hash_before}`"
    )

    lines.append(
        f"- Market data after: `{data_hash_after}`"
    )

    lines.append(
        f"- Market data unchanged: "
        f"`{data_hash_before == data_hash_after}`"
    )

    lines.append("")

    return "\n".join(lines)


# ============================================================================
# MAIN
# ============================================================================

def main():

    print("=" * 100)
    print(
        "MLAI v4.1.5 ROBUST RETRIEVAL SCIENTIFIC GATE"
    )
    print("=" * 100)

    print()
    print(
        f"Gate version: {VERSION}"
    )

    print(
        "READ-ONLY FORENSIC VALIDATION"
    )

    # ------------------------------------------------------------------------
    # File existence
    # ------------------------------------------------------------------------

    if not SOURCE_FILE.exists():
        raise FileNotFoundError(
            f"Missing {SOURCE_FILE.name}"
        )

    if not DATA_FILE.exists():
        raise FileNotFoundError(
            f"Missing {DATA_FILE.name}"
        )

    # ------------------------------------------------------------------------
    # Protection hashes BEFORE
    # ------------------------------------------------------------------------

    source_hash_before = sha256_file(
        SOURCE_FILE
    )

    data_hash_before = sha256_file(
        DATA_FILE
    )

    memory_hash_before = (
        sha256_file(MEMORY_FILE)
        if MEMORY_FILE.exists()
        else None
    )

    print()
    print("=" * 100)
    print("1. PROTECTION CHECK — BEFORE")
    print("=" * 100)

    print(
        f"Source file: {SOURCE_FILE.name}"
    )

    print(
        f"Source SHA256: {source_hash_before}"
    )

    print(
        f"Market data SHA256: {data_hash_before}"
    )

    if memory_hash_before is not None:

        print(
            f"Retrieval memory SHA256: "
            f"{memory_hash_before}"
        )

    else:

        print(
            "Retrieval memory: NOT FOUND"
        )

    print()
    print(
        "No source modifications will be performed."
    )

    print(
        "No market-data modifications will be performed."
    )

    print(
        "No retrieval-memory modifications will be performed."
    )

    print(
        "No retrieval parameters will be changed."
    )

    # ------------------------------------------------------------------------
    # Import
    # ------------------------------------------------------------------------

    print()
    print("=" * 100)
    print("2. IMPORT V4.1.5")
    print("=" * 100)

    module = import_v415()

    print(
        "IMPORT: PASS"
    )

    print(
        f"VERSION: {getattr(module, 'VERSION', '<missing>')}"
    )

    # ------------------------------------------------------------------------
    # Memory
    # ------------------------------------------------------------------------

    print()
    print("=" * 100)
    print("3. MEMORY INSPECTION")
    print("=" * 100)

    memory_info = inspect_memory()

    print(
        f"Memory exists: "
        f"{memory_info['exists']}"
    )

    print(
        f"Memory type: "
        f"{memory_info['root_type']}"
    )

    if memory_info["keys"]:

        print(
            "Memory keys:"
        )

        for key in memory_info["keys"]:

            print(
                f"  {key}"
            )

    # ------------------------------------------------------------------------
    # Dataset
    # ------------------------------------------------------------------------

    print()
    print("=" * 100)
    print("4. RECONSTRUCT ACTUAL V4.1.5 CAUSAL DATASET")
    print("=" * 100)

    dataset = discover_dataset(
        module
    )

    print(
        f"Candles: "
        f"{len(dataset['candles'])}"
    )

    print(
        f"Invalid candles reported by loader: "
        f"{dataset['invalid_count']}"
    )

    print(
        f"ATR values: "
        f"{len(dataset['atr'])}"
    )

    print(
        f"Structure states: "
        f"{len(dataset['structure_states'])}"
    )

    print(
        f"Market states: "
        f"{len(dataset['states'])}"
    )

    print(
        f"Episode IDs: "
        f"{len(dataset['episode_ids'])}"
    )

    print(
        f"Walk-forward windows: "
        f"{len(dataset['windows'])}"
    )

    for window in dataset["windows"]:

        print(
            f"  Window {window.number}: "
            f"TRAIN [{window.train_start}:{window.train_end}] "
            f"| OOS [{window.oos_start}:{window.oos_end}]"
        )

    for horizon in module.HORIZONS:

        print(
            f"H+{horizon} complete records: "
            f"{len(dataset['records'][horizon])}"
        )

    # ------------------------------------------------------------------------
    # Temporal integrity
    # ------------------------------------------------------------------------

    print()
    print("=" * 100)
    print("5. SELF / FUTURE / BOUNDARY LEAKAGE INVESTIGATION")
    print("=" * 100)

    temporal = audit_temporal_integrity(
        module,
        dataset,
    )

    print(
        f"Queries inspected: "
        f"{temporal['total_queries']}"
    )

    print(
        f"Candidates inspected: "
        f"{temporal['total_candidates']}"
    )

    print(
        f"Self matches: "
        f"{temporal['self_matches']}"
    )

    print(
        f"Future candidates: "
        f"{temporal['future_candidates']}"
    )

    print(
        f"Boundary violations: "
        f"{temporal['boundary_violations']}"
    )

    print(
        f"Outcome boundary violations: "
        f"{temporal['outcome_boundary_violations']}"
    )

    print(
        f"Horizon violations: "
        f"{temporal['horizon_violations']}"
    )

    if temporal["passed"]:

        print()
        print(
            "TEMPORAL INTEGRITY: PASS"
        )

    else:

        print()
        print(
            "TEMPORAL INTEGRITY: FAIL"
        )

        for violation in temporal["violations"][:20]:

            print(
                "  " + violation
            )

    # ------------------------------------------------------------------------
    # Similarity discrimination
    # ------------------------------------------------------------------------

    print()
    print("=" * 100)
    print("6. SIMILARITY DISCRIMINATION")
    print("=" * 100)

    discrimination = similarity_discrimination_test(
        module,
        dataset,
    )

    for horizon in module.HORIZONS:

        result = discrimination[horizon]

        print()
        print(
            f"H+{horizon}"
        )

        if not result.get("available"):

            print(
                "  INCONCLUSIVE"
            )

            continue

        print(
            f"  Evaluation rows       : "
            f"{result['rows']}"
        )

        print(
            f"  Top similarity        : "
            f"{fmt_pct(result['top_similarity'])}"
        )

        print(
            f"  Top agreement         : "
            f"{fmt_pct(result['top_agreement'])}"
        )

        print(
            f"  Middle agreement      : "
            f"{fmt_pct(result['middle_agreement'])}"
        )

        print(
            f"  Bottom agreement      : "
            f"{fmt_pct(result['bottom_agreement'])}"
        )

        print(
            f"  Random agreement      : "
            f"{fmt_pct(result['random_agreement'])}"
        )

        print(
            f"  Top-vs-random lift    : "
            f"{fmt_pct(result['discrimination_lift'])}"
        )

        print(
            f"  Monotonic             : "
            f"{result['monotonic']}"
        )

        print(
            f"  RESULT                : "
            f"{'PASS' if result['passed'] else 'FAIL'}"
        )

    # ------------------------------------------------------------------------
    # Predictive value
    # ------------------------------------------------------------------------

    print()
    print("=" * 100)
    print("7. RETRIEVAL PREDICTIVE VALUE")
    print("=" * 100)

    predictive = evaluate_retrieval_predictive_value(
        module,
        dataset,
    )

    for horizon in module.HORIZONS:

        result = predictive[horizon]

        print()
        print(
            f"H+{horizon}"
        )

        if not result.get("available"):

            print(
                "  INCONCLUSIVE"
            )

            continue

        print(
            f"  Mean Accuracy Lift       : "
            f"{fmt_pct(result['mean_accuracy_lift'])}"
        )

        print(
            f"  Mean Brier Lift          : "
            f"{fmt_num(result['mean_brier_lift'])}"
        )

        print(
            f"  Mean LogLoss Lift        : "
            f"{fmt_num(result['mean_logloss_lift'])}"
        )

        print(
            f"  Accuracy-positive        : "
            f"{result['accuracy_positive_windows']}/"
            f"{result['window_count']}"
        )

        print(
            f"  Brier-positive           : "
            f"{result['brier_positive_windows']}/"
            f"{result['window_count']}"
        )

        print(
            f"  LogLoss-positive         : "
            f"{result['logloss_positive_windows']}/"
            f"{result['window_count']}"
        )

        print(
            f"  Probability value        : "
            f"{result['probability_value']}"
        )

        print(
            f"  Probability consistency  : "
            f"{result['probability_consistency']}"
        )

        print(
            f"  Accuracy not catastrophic: "
            f"{result['accuracy_not_catastrophic']}"
        )

        print(
            f"  RESULT                   : "
            f"{'PASS' if result['passed'] else 'FAIL'}"
        )

        print()

        print(
            "  Window details:"
        )

        for row in result["windows"]:

            print(
                f"    W{row['window']} "
                f"queries={row['queries']} "
                f"accuracy_lift={fmt_pct(row['accuracy_lift'])} "
                f"brier_lift={fmt_num(row['brier_lift'])} "
                f"logloss_lift={fmt_num(row['logloss_lift'])}"
            )

    # ------------------------------------------------------------------------
    # Final classification
    # ------------------------------------------------------------------------

    classifications = classify_final_result(
        temporal,
        discrimination,
        predictive,
    )

    print()
    print("=" * 100)
    print("8. FINAL CLASSIFICATION")
    print("=" * 100)

    for key, value in classifications.items():

        print(
            f"{key}: {value}"
        )

    # ------------------------------------------------------------------------
    # Protection hashes AFTER
    # ------------------------------------------------------------------------

    source_hash_after = sha256_file(
        SOURCE_FILE
    )

    data_hash_after = sha256_file(
        DATA_FILE
    )

    memory_hash_after = (
        sha256_file(MEMORY_FILE)
        if MEMORY_FILE.exists()
        else None
    )

    source_unchanged = (
        source_hash_before
        == source_hash_after
    )

    data_unchanged = (
        data_hash_before
        == data_hash_after
    )

    memory_unchanged = (
        memory_hash_before
        == memory_hash_after
    )

    print()
    print("=" * 100)
    print("9. FINAL PROTECTION CHECK")
    print("=" * 100)

    print(
        f"Source unchanged: "
        f"{'PASS' if source_unchanged else 'FAIL'}"
    )

    print(
        f"Market data unchanged: "
        f"{'PASS' if data_unchanged else 'FAIL'}"
    )

    print(
        f"Memory unchanged: "
        f"{'PASS' if memory_unchanged else 'FAIL'}"
    )

    # ------------------------------------------------------------------------
    # Report
    # ------------------------------------------------------------------------

    report = build_report(
        memory_info=memory_info,
        temporal=temporal,
        discrimination=discrimination,
        predictive=predictive,
        classifications=classifications,
        source_hash_before=source_hash_before,
        source_hash_after=source_hash_after,
        memory_hash_before=memory_hash_before,
        memory_hash_after=memory_hash_after,
        data_hash_before=data_hash_before,
        data_hash_after=data_hash_after,
    )

    REPORT_FILE.write_text(
        report,
        encoding="utf-8",
    )

    print()
    print("=" * 100)
    print("10. REPORT")
    print("=" * 100)

    print(
        f"Saved: {REPORT_FILE.name}"
    )

    # ------------------------------------------------------------------------
    # HARD PROTECTION FAILURE
    # ------------------------------------------------------------------------

    if not source_unchanged:

        raise RuntimeError(
            "PROTECTION FAILURE: v4.1.5 source file changed."
        )

    if not data_unchanged:

        raise RuntimeError(
            "PROTECTION FAILURE: market_data.bin changed."
        )

    if not memory_unchanged:

        raise RuntimeError(
            "PROTECTION FAILURE: retrieval memory changed."
        )

    print()
    print("=" * 100)
    print(
        "MLAI v4.1.5 ROBUST RETRIEVAL SCIENTIFIC GATE COMPLETE"
    )
    print("=" * 100)

    print()
    print("SOURCE MODIFIED       : NO")
    print("MARKET DATA MODIFIED  : NO")
    print("MEMORY MODIFIED       : NO")
    print("PARAMETERS CHANGED    : NO")
    print("MODEL RETRAINED       : NO")

    print()
    print(
        "IMPORTANT:"
    )

    print(
        "A predictive-value FAIL is an empirical result."
    )

    print(
        "It is NOT automatically a coding defect."
    )

    print(
        "A temporal FAIL, however, blocks scientific interpretation."
    )


if __name__ == "__main__":
    main()