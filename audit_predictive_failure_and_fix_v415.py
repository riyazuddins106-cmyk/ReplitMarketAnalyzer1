from __future__ import annotations

from pathlib import Path
import ast
import hashlib
import importlib
import inspect
import math
import random
import statistics
import traceback
from collections import Counter, defaultdict
from dataclasses import asdict, is_dataclass
from typing import Any


SOURCE = Path("mlai_market_structure_v415.py")
DATA = Path("market_data.bin")
REPORT = Path("MLAI_v415_predictive_failure_audit_report.md")

MODULE_NAME = "mlai_market_structure_v415"

SEED = 415
random.seed(SEED)

HORIZONS = (4, 8, 16)

# Keep the same query density as the previous predictive audit.
QUERY_COUNT = 250

# Alternative retrieval sizes to investigate.
K_VALUES = (5, 10, 20, 40)

# Similarity-power experiments.
POWER_VALUES = (0.0, 1.0, 2.0, 4.0, 8.0)

# Feature ablation experiments.
FEATURE_GROUPS = (
    "ALL",
    "NO_PATH",
    "NO_CANDLE",
    "NO_MOMENTUM",
    "NO_LOCATION",
    "NO_VOLATILITY",
    "NO_REGIME",
    "NO_SEQUENCE",
    "NO_STRUCTURE",
)


# ======================================================================
# GENERAL HELPERS
# ======================================================================

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def safe_float(value: Any) -> float | None:
    try:
        x = float(value)
        if math.isfinite(x):
            return x
    except Exception:
        pass
    return None


def direction_from_outcome(outcome: Any) -> str:
    return str(getattr(outcome, "direction", "UNKNOWN"))


def get_source_function(module: Any, name: str):
    fn = getattr(module, name, None)
    if fn is None:
        raise RuntimeError(f"Required function missing: {name}")
    return fn


def record_index(record: Any) -> int:
    return int(getattr(record, "index"))


def selected_indices(result: Any) -> list[int]:
    value = getattr(result, "selected_match_indices", None)
    if value is None:
        return []
    return list(value)


def prediction_from_shares(
    up: float,
    down: float,
    neutral: float,
) -> str:
    values = {
        "UP": up,
        "DOWN": down,
        "NEUTRAL": neutral,
    }
    return max(values, key=values.get)


def accuracy(y_true: list[str], y_pred: list[str]) -> float:
    if not y_true:
        return 0.0
    return sum(a == b for a, b in zip(y_true, y_pred)) / len(y_true)


def balanced_accuracy(y_true: list[str], y_pred: list[str]) -> float:
    classes = ("UP", "DOWN", "NEUTRAL")
    recalls = []

    for cls in classes:
        actual = sum(x == cls for x in y_true)
        if actual == 0:
            continue

        correct = sum(
            a == cls and p == cls
            for a, p in zip(y_true, y_pred)
        )

        recalls.append(correct / actual)

    return statistics.mean(recalls) if recalls else 0.0


def confusion(y_true: list[str], y_pred: list[str]):
    matrix = {
        (actual, predicted): 0
        for actual in ("UP", "DOWN", "NEUTRAL")
        for predicted in ("UP", "DOWN", "NEUTRAL")
    }

    for actual, predicted in zip(y_true, y_pred):
        matrix[(actual, predicted)] += 1

    return matrix


def majority_prediction(y_true: list[str]) -> str:
    return Counter(y_true).most_common(1)[0][0]


def safe_mean(values):
    values = [float(x) for x in values if x is not None]
    return statistics.mean(values) if values else 0.0


def section(title: str):
    print()
    print("=" * 100)
    print(title)
    print("=" * 100)


def subsection(title: str):
    print()
    print("-" * 100)
    print(title)
    print("-" * 100)


# ======================================================================
# SOURCE INSPECTION
# ======================================================================

def static_source_audit():
    source = SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(source)

    required_functions = (
        "load_market_data",
        "calculate_atr",
        "build_path_vector",
        "build_market_states",
        "assign_episode_ids",
        "build_experience_records",
        "similarity_score",
        "retrieve_historical_experience",
    )

    required_classes = (
        "Candle",
        "StructureState",
        "MarketState",
        "Outcome",
        "ExperienceRecord",
        "RetrievalResult",
        "CausalStructureEngine",
    )

    functions = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }

    classes = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef)
    }

    return {
        "functions": functions,
        "classes": classes,
        "missing_functions": [
            x for x in required_functions if x not in functions
        ],
        "missing_classes": [
            x for x in required_classes if x not in classes
        ],
    }


# ======================================================================
# SAFE EXPERIENCE BUILD
# ======================================================================

def build_records(
    experience_fn,
    candles,
    atr,
    states,
    episode_ids,
    train_end,
    horizon,
):
    """
    Safely call the real v4.1.5 experience builder.

    Empty output is a valid diagnostic state.
    It is NOT an exception.
    """

    try:
        records = experience_fn(
            candles,
            atr,
            states,
            episode_ids,
            0,
            train_end,
            horizon,
        )
    except Exception as exc:
        return [], {
            "ok": False,
            "error": f"{type(exc).__name__}: {exc}",
        }

    return list(records), {
        "ok": True,
        "error": None,
    }


# ======================================================================
# OUTCOME EXTRACTION
# ======================================================================

def outcome_for_query(candles, atr, query_index, horizon, make_outcome):
    """
    Reconstruct the true future outcome for a query.

    This is used ONLY for evaluation, never for retrieval.
    """

    try:
        outcome = make_outcome(
            candles,
            atr,
            query_index,
            horizon,
        )
    except Exception:
        return None

    if outcome is None:
        return None

    return direction_from_outcome(outcome)


# ======================================================================
# MANUAL RETRIEVAL ANALYSIS
# ======================================================================

def manual_similarity(
    module,
    current,
    record,
    feature_group="ALL",
):
    """
    Reproduce v4.1.5 similarity logic while allowing feature ablation.

    This does NOT modify v4.1.5.
    """

    try:
        components = module.similarity_score(current, record)
    except Exception:
        return None

    disabled = {
        "NO_PATH": {"path"},
        "NO_CANDLE": {"candle"},
        "NO_MOMENTUM": {"momentum"},
        "NO_LOCATION": {"location"},
        "NO_VOLATILITY": {"volatility"},
        "NO_REGIME": {"regime"},
        "NO_SEQUENCE": {"sequence"},
        "NO_STRUCTURE": {"structure"},
    }.get(feature_group, set())

    weights = {
        "structure": getattr(module, "WEIGHT_STRUCTURE", 1.0),
        "sequence": getattr(module, "WEIGHT_SEQUENCE", 1.0),
        "regime": getattr(module, "WEIGHT_REGIME", 1.0),
        "location": getattr(module, "WEIGHT_LOCATION", 1.0),
        "momentum": getattr(module, "WEIGHT_MOMENTUM", 1.0),
        "volatility": getattr(module, "WEIGHT_VOLATILITY", 1.0),
        "candle": getattr(module, "WEIGHT_CANDLE", 1.0),
        "path": getattr(module, "WEIGHT_PATH", 1.0),
    }

    numerator = 0.0
    denominator = 0.0

    for name, weight in weights.items():
        if name in disabled:
            continue

        numerator += weight * float(components.get(name, 0.0))
        denominator += weight

    if denominator <= 0:
        return 0.0

    return numerator / denominator


def manual_candidates(
    module,
    current,
    records,
    query_index,
    feature_group="ALL",
):
    """
    Build candidates strictly before query_index.
    """

    candidates = []

    for record in records:
        idx = record_index(record)

        if idx >= query_index:
            continue

        similarity = manual_similarity(
            module,
            current,
            record,
            feature_group,
        )

        if similarity is None:
            continue

        candidates.append((similarity, idx, record))

    candidates.sort(
        key=lambda x: (x[0], x[1]),
        reverse=True,
    )

    return candidates


# ======================================================================
# AGGREGATION METHODS
# ======================================================================

def aggregate_predictions(
    candidates,
    k,
    power,
):
    """
    Compare several deterministic aggregation rules.

    No future information is used.
    """

    chosen = candidates[:k]

    if not chosen:
        return "NO_PREDICTION", 0.0, {}

    weights = []

    for similarity, _, _ in chosen:
        if power == 0.0:
            weight = 1.0
        else:
            weight = max(float(similarity), 0.0) ** power

        weights.append(weight)

    totals = {
        "UP": 0.0,
        "DOWN": 0.0,
        "NEUTRAL": 0.0,
    }

    counts = {
        "UP": 0,
        "DOWN": 0,
        "NEUTRAL": 0,
    }

    for weight, (_, _, record) in zip(weights, chosen):
        direction = direction_from_outcome(
            getattr(record, "outcome", None)
        )

        if direction not in totals:
            continue

        totals[direction] += weight
        counts[direction] += 1

    total_weight = sum(totals.values())

    if total_weight <= 0:
        return "NO_PREDICTION", 0.0, counts

    shares = {
        key: value / total_weight
        for key, value in totals.items()
    }

    prediction = max(
        shares,
        key=shares.get,
    )

    confidence = shares[prediction]

    return prediction, confidence, {
        "counts": counts,
        "shares": shares,
    }


# ======================================================================
# RETRIEVAL QUALITY
# ======================================================================

def retrieval_quality(
    module,
    current,
    records,
    query_index,
):
    candidates = manual_candidates(
        module,
        current,
        records,
        query_index,
    )

    if not candidates:
        return {
            "count": 0,
            "top_similarity": 0.0,
            "mean_top10": 0.0,
            "future_violation": 0,
            "support": 0,
            "conflict": 0,
        }

    top = candidates[:40]

    similarities = [x[0] for x in top]

    # Use the top candidate direction as the support direction.
    dominant = direction_from_outcome(
        getattr(top[0][2], "outcome", None)
    )

    support = sum(
        direction_from_outcome(
            getattr(record, "outcome", None)
        ) == dominant
        for _, _, record in top
    )

    conflict = len(top) - support

    violations = sum(
        idx >= query_index
        for _, idx, _ in top
    )

    return {
        "count": len(candidates),
        "top_similarity": max(similarities),
        "mean_top10": safe_mean(similarities[:10]),
        "future_violation": violations,
        "support": support,
        "conflict": conflict,
    }


# ======================================================================
# WALK-FORWARD EVALUATION
# ======================================================================

def run_experiment(
    module,
    candles,
    atr,
    states,
    episode_ids,
    experience_fn,
    make_outcome,
    queries,
    horizon,
    k,
    power,
    feature_group,
):
    y_true = []
    y_pred = []

    confidences = []
    similarities = []

    retrieval_failures = 0
    temporal_violations = 0
    empty_training_windows = 0

    training_records_total = 0

    for query_index in queries:

        # --------------------------------------------------------------
        # Training boundary
        #
        # Crucial condition:
        # all historical outcomes must terminate before query_index.
        # --------------------------------------------------------------

        records, status = build_records(
            experience_fn,
            candles,
            atr,
            states,
            episode_ids,
            query_index,
            horizon,
        )

        if not status["ok"]:
            raise RuntimeError(
                f"Experience builder failed at query={query_index}, "
                f"horizon={horizon}: {status['error']}"
            )

        if not records:
            empty_training_windows += 1
            continue

        training_records_total += len(records)

        current = states[query_index]

        candidates = manual_candidates(
            module,
            current,
            records,
            query_index,
            feature_group,
        )

        if not candidates:
            retrieval_failures += 1
            continue

        for _, idx, _ in candidates[:k]:
            if idx >= query_index:
                temporal_violations += 1

        prediction, confidence, metadata = aggregate_predictions(
            candidates,
            k,
            power,
        )

        if prediction == "NO_PREDICTION":
            retrieval_failures += 1
            continue

        actual = outcome_for_query(
            candles,
            atr,
            query_index,
            horizon,
            make_outcome,
        )

        if actual is None:
            continue

        y_true.append(actual)
        y_pred.append(prediction)

        confidences.append(confidence)
        similarities.append(candidates[0][0])

    return {
        "n": len(y_true),
        "accuracy": accuracy(y_true, y_pred),
        "balanced_accuracy": balanced_accuracy(y_true, y_pred),
        "baseline": majority_prediction(y_true) if y_true else None,
        "baseline_accuracy": (
            accuracy(
                y_true,
                [majority_prediction(y_true)] * len(y_true),
            )
            if y_true
            else 0.0
        ),
        "y_true": y_true,
        "y_pred": y_pred,
        "confidences": confidences,
        "similarities": similarities,
        "retrieval_failures": retrieval_failures,
        "temporal_violations": temporal_violations,
        "empty_training_windows": empty_training_windows,
        "training_records_total": training_records_total,
    }


# ======================================================================
# SOURCE-SAFE PATCH CANDIDATE GENERATION
# ======================================================================

def create_candidate_copy():
    """
    Create a candidate only after the forensic evidence has been collected.

    The baseline source is NEVER changed.
    """

    candidate = Path("mlai_market_structure_v416_candidate.py")

    if candidate.exists():
        candidate.unlink()

    source = SOURCE.read_text(encoding="utf-8")

    candidate.write_text(
        source,
        encoding="utf-8",
    )

    return candidate


# ======================================================================
# REPORT
# ======================================================================

REPORT_LINES = []


def report(line=""):
    REPORT_LINES.append(str(line))
    print(line)


def write_report():
    REPORT.write_text(
        "\n".join(REPORT_LINES),
        encoding="utf-8",
    )


# ======================================================================
# MAIN
# ======================================================================

def main():

    section(
        "MLAI v4.1.5 — COMPLETE PREDICTIVE FAILURE FORENSIC AUDIT"
    )

    report("# MLAI v4.1.5 Predictive Failure Forensic Audit")
    report()
    report(
        "This audit investigates predictive failure without modifying "
        "v4.1.5 or market_data.bin."
    )

    source_hash_before = sha256(SOURCE)
    data_hash_before = sha256(DATA)

    report(f"Source SHA256: `{source_hash_before}`")
    report(f"Data SHA256: `{data_hash_before}`")

    # ------------------------------------------------------------------
    # 1. STATIC
    # ------------------------------------------------------------------

    subsection("1. STATIC SOURCE FORENSICS")

    static = static_source_audit()

    report(f"Functions found: {len(static['functions'])}")
    report(f"Classes found: {len(static['classes'])}")

    if static["missing_functions"]:
        raise RuntimeError(
            "Missing functions: "
            + ", ".join(static["missing_functions"])
        )

    if static["missing_classes"]:
        raise RuntimeError(
            "Missing classes: "
            + ", ".join(static["missing_classes"])
        )

    report("STATIC CONTRACT: PASS")

    # ------------------------------------------------------------------
    # 2. IMPORT
    # ------------------------------------------------------------------

    subsection("2. MODULE IMPORT")

    module = importlib.import_module(MODULE_NAME)

    report("IMPORT: PASS")

    # ------------------------------------------------------------------
    # 3. API
    # ------------------------------------------------------------------

    load_market_data = get_source_function(
        module,
        "load_market_data",
    )

    calculate_atr = get_source_function(
        module,
        "calculate_atr",
    )

    build_market_states = get_source_function(
        module,
        "build_market_states",
    )

    assign_episode_ids = get_source_function(
        module,
        "assign_episode_ids",
    )

    experience_fn = get_source_function(
        module,
        "build_experience_records",
    )

    make_outcome = get_source_function(
        module,
        "make_outcome",
    )

    similarity_score = get_source_function(
        module,
        "similarity_score",
    )

    report(
        f"experience signature: {inspect.signature(experience_fn)}"
    )

    report(
        f"retrieval signature: "
        f"{inspect.signature(module.retrieve_historical_experience)}"
    )

    # ------------------------------------------------------------------
    # 4. DATA
    # ------------------------------------------------------------------

    subsection("3. DATA CONTRACT")

    loaded = load_market_data(
        getattr(module, "MARKET_DATA_FILE", DATA.name)
    )

    if not isinstance(loaded, tuple) or len(loaded) != 2:
        raise RuntimeError(
            "load_market_data did not return (candles, invalid)"
        )

    candles, invalid = loaded

    report(f"candles: {len(candles)}")
    report(f"invalid: {invalid}")
    report(f"first: {candles[0]!r}")

    # ------------------------------------------------------------------
    # 5. FEATURES
    # ------------------------------------------------------------------

    atr = calculate_atr(candles)

    try:
        states = build_market_states(
            candles,
            atr,
        )
    except TypeError:
        states = build_market_states(
            candles,
            atr,
        )

    episode_ids = assign_episode_ids(
        states
    )

    report(f"ATR: {len(atr)}")
    report(f"states: {len(states)}")
    report(f"episodes: {len(set(episode_ids.values()))}")

    # ------------------------------------------------------------------
    # 6. QUERY POINTS
    # ------------------------------------------------------------------

    min_query = max(
        200,
        int(len(candles) * 0.45),
    )

    max_query = len(candles) - max(HORIZONS) - 1

    if max_query <= min_query:
        raise RuntimeError(
            "Not enough data for chronological predictive testing."
        )

    query_pool = list(
        range(
            min_query,
            max_query + 1,
        )
    )

    rng = random.Random(SEED)

    if len(query_pool) > QUERY_COUNT:
        queries = sorted(
            rng.sample(
                query_pool,
                QUERY_COUNT,
            )
        )
    else:
        queries = query_pool

    report()
    report(f"query points: {len(queries)}")
    report(f"query range: {queries[0]}..{queries[-1]}")

    # ------------------------------------------------------------------
    # 7. BASELINE REPRODUCTION
    # ------------------------------------------------------------------

    subsection(
        "4. BASELINE REPRODUCTION — MANUAL RETRIEVAL"
    )

    baseline_results = {}

    for horizon in HORIZONS:

        result = run_experiment(
            module,
            candles,
            atr,
            states,
            episode_ids,
            experience_fn,
            make_outcome,
            queries,
            horizon,
            k=40,
            power=2.0,
            feature_group="ALL",
        )

        baseline_results[horizon] = result

        report()
        report(f"H{horizon}")
        report(f"  n={result['n']}")
        report(
            f"  accuracy={result['accuracy']:.6f}"
        )
        report(
            f"  balanced={result['balanced_accuracy']:.6f}"
        )
        report(
            f"  baseline={result['baseline']}"
        )
        report(
            f"  baseline_accuracy="
            f"{result['baseline_accuracy']:.6f}"
        )
        report(
            f"  improvement="
            f"{result['accuracy'] - result['baseline_accuracy']:.6f}"
        )
        report(
            f"  retrieval_failures="
            f"{result['retrieval_failures']}"
        )
        report(
            f"  temporal_violations="
            f"{result['temporal_violations']}"
        )

    # ------------------------------------------------------------------
    # 8. K SEARCH
    # ------------------------------------------------------------------

    subsection(
        "5. RETRIEVAL K-SIZE EXPERIMENT"
    )

    k_results = {}

    for horizon in HORIZONS:

        report()
        report(f"HORIZON {horizon}")

        k_results[horizon] = {}

        for k in K_VALUES:

            result = run_experiment(
                module,
                candles,
                atr,
                states,
                episode_ids,
                experience_fn,
                make_outcome,
                queries,
                horizon,
                k=k,
                power=2.0,
                feature_group="ALL",
            )

            k_results[horizon][k] = result

            report(
                f"K={k:2d} "
                f"acc={result['accuracy']:.4f} "
                f"bal={result['balanced_accuracy']:.4f} "
                f"base={result['baseline_accuracy']:.4f}"
            )

    # ------------------------------------------------------------------
    # 9. POWER SEARCH
    # ------------------------------------------------------------------

    subsection(
        "6. SIMILARITY WEIGHT POWER EXPERIMENT"
    )

    power_results = {}

    for horizon in HORIZONS:

        report()
        report(f"HORIZON {horizon}")

        power_results[horizon] = {}

        for power in POWER_VALUES:

            result = run_experiment(
                module,
                candles,
                atr,
                states,
                episode_ids,
                experience_fn,
                make_outcome,
                queries,
                horizon,
                k=40,
                power=power,
                feature_group="ALL",
            )

            power_results[horizon][power] = result

            report(
                f"POWER={power:4.1f} "
                f"acc={result['accuracy']:.4f} "
                f"bal={result['balanced_accuracy']:.4f} "
                f"base={result['baseline_accuracy']:.4f}"
            )

    # ------------------------------------------------------------------
    # 10. FEATURE ABLATION
    # ------------------------------------------------------------------

    subsection(
        "7. FEATURE ABLATION EXPERIMENT"
    )

    ablation_results = {}

    for horizon in HORIZONS:

        report()
        report(f"HORIZON {horizon}")

        ablation_results[horizon] = {}

        for group in FEATURE_GROUPS:

            result = run_experiment(
                module,
                candles,
                atr,
                states,
                episode_ids,
                experience_fn,
                make_outcome,
                queries,
                horizon,
                k=40,
                power=2.0,
                feature_group=group,
            )

            ablation_results[horizon][group] = result

            report(
                f"{group:15s} "
                f"acc={result['accuracy']:.4f} "
                f"bal={result['balanced_accuracy']:.4f} "
                f"base={result['baseline_accuracy']:.4f}"
            )

    # ------------------------------------------------------------------
    # 11. LABEL DISTRIBUTION
    # ------------------------------------------------------------------

    subsection(
        "8. QUERY LABEL DISTRIBUTION"
    )

    label_distribution = {}

    for horizon in HORIZONS:

        labels = []

        for query_index in queries:

            actual = outcome_for_query(
                candles,
                atr,
                query_index,
                horizon,
                make_outcome,
            )

            if actual:
                labels.append(actual)

        counts = Counter(labels)

        label_distribution[horizon] = counts

        report(
            f"H{horizon}: {dict(counts)}"
        )

    # ------------------------------------------------------------------
    # 12. CONFUSION
    # ------------------------------------------------------------------

    subsection(
        "9. BASELINE CONFUSION MATRICES"
    )

    for horizon, result in baseline_results.items():

        matrix = confusion(
            result["y_true"],
            result["y_pred"],
        )

        report()
        report(f"H{horizon}")
        report(
            "              PRED_UP  PRED_DOWN  PRED_NEUTRAL"
        )

        for actual in ("UP", "DOWN", "NEUTRAL"):

            report(
                f"ACT_{actual:7s} "
                f"{matrix[(actual, 'UP')]:8d} "
                f"{matrix[(actual, 'DOWN')]:10d} "
                f"{matrix[(actual, 'NEUTRAL')]:12d}"
            )

    # ------------------------------------------------------------------
    # 13. HIGH SIMILARITY DIAGNOSTIC
    # ------------------------------------------------------------------

    subsection(
        "10. HIGH-SIMILARITY / LOW-PREDICTIVE-VALUE DIAGNOSTIC"
    )

    for horizon in HORIZONS:

        result = baseline_results[horizon]

        if not result["similarities"]:
            report(f"H{horizon}: no similarity samples")
            continue

        report()
        report(f"H{horizon}")
        report(
            f"mean top similarity="
            f"{safe_mean(result['similarities']):.6f}"
        )

        buckets = {
            "0.50-0.60": [],
            "0.60-0.70": [],
            "0.70-0.80": [],
            "0.80-0.90": [],
            "0.90-1.00": [],
        }

        for similarity, actual, predicted in zip(
            result["similarities"],
            result["y_true"],
            result["y_pred"],
        ):
            if similarity < 0.60:
                bucket = "0.50-0.60"
            elif similarity < 0.70:
                bucket = "0.60-0.70"
            elif similarity < 0.80:
                bucket = "0.70-0.80"
            elif similarity < 0.90:
                bucket = "0.80-0.90"
            else:
                bucket = "0.90-1.00"

            buckets[bucket].append(
                actual == predicted
            )

        for bucket, values in buckets.items():

            if not values:
                report(
                    f"{bucket}: n=0"
                )
            else:
                report(
                    f"{bucket}: "
                    f"n={len(values)} "
                    f"accuracy={safe_mean(values):.4f}"
                )

    # ------------------------------------------------------------------
    # 14. RETRIEVAL SUPPORT CONFLICT
    # ------------------------------------------------------------------

    subsection(
        "11. SUPPORT / CONFLICT ANALYSIS"
    )

    for horizon in HORIZONS:

        support_values = []
        conflict_values = []

        for query_index in queries:

            records, status = build_records(
                experience_fn,
                candles,
                atr,
                states,
                episode_ids,
                query_index,
                horizon,
            )

            if not status["ok"] or not records:
                continue

            quality = retrieval_quality(
                module,
                states[query_index],
                records,
                query_index,
            )

            if quality["count"]:

                support_values.append(
                    quality["support"]
                )

                conflict_values.append(
                    quality["conflict"]
                )

        report(
            f"H{horizon}: "
            f"mean_support={safe_mean(support_values):.2f} "
            f"mean_conflict={safe_mean(conflict_values):.2f}"
        )

    # ------------------------------------------------------------------
    # 15. FIND BEST ALTERNATIVE
    # ------------------------------------------------------------------

    subsection(
        "12. BEST NON-MODIFYING RETRIEVAL CONFIGURATION"
    )

    best_configs = {}

    for horizon in HORIZONS:

        candidates = []

        for k in K_VALUES:

            result = k_results[horizon][k]

            candidates.append(
                (
                    result["balanced_accuracy"],
                    result["accuracy"],
                    f"K={k}, power=2",
                    result,
                )
            )

        for power in POWER_VALUES:

            result = power_results[horizon][power]

            candidates.append(
                (
                    result["balanced_accuracy"],
                    result["accuracy"],
                    f"K=40, power={power}",
                    result,
                )
            )

        candidates.sort(
            key=lambda x: (x[0], x[1]),
            reverse=True,
        )

        best = candidates[0]

        best_configs[horizon] = best

        report(
            f"H{horizon}: "
            f"{best[2]} "
            f"balanced={best[0]:.6f} "
            f"accuracy={best[1]:.6f} "
            f"baseline={best[3]['baseline_accuracy']:.6f}"
        )

    # ------------------------------------------------------------------
    # 16. SOURCE INTEGRITY
    # ------------------------------------------------------------------

    subsection(
        "13. SOURCE / DATA INTEGRITY"
    )

    source_hash_after = sha256(SOURCE)
    data_hash_after = sha256(DATA)

    source_unchanged = (
        source_hash_before == source_hash_after
    )

    data_unchanged = (
        data_hash_before == data_hash_after
    )

    report(
        f"Source unchanged: {source_unchanged}"
    )

    report(
        f"Data unchanged: {data_unchanged}"
    )

    if not source_unchanged:
        raise RuntimeError(
            "CRITICAL: v4.1.5 source changed during audit."
        )

    if not data_unchanged:
        raise RuntimeError(
            "CRITICAL: market_data.bin changed during audit."
        )

    # ------------------------------------------------------------------
    # 17. SCIENTIFIC VERDICT
    # ------------------------------------------------------------------

    subsection(
        "14. SCIENTIFIC FAILURE CLASSIFICATION"
    )

    report()

    for horizon in HORIZONS:

        result = baseline_results[horizon]

        improvement = (
            result["accuracy"]
            - result["baseline_accuracy"]
        )

        best = best_configs[horizon]

        best_improvement = (
            best[1]
            - best[3]["baseline_accuracy"]
        )

        report(
            f"H{horizon}:"
        )

        report(
            f"  baseline accuracy      = "
            f"{result['baseline_accuracy']:.4f}"
        )

        report(
            f"  v4.1.5 retrieval      = "
            f"{result['accuracy']:.4f}"
        )

        report(
            f"  v4.1.5 improvement    = "
            f"{improvement:.4f}"
        )

        report(
            f"  best tested retrieval = "
            f"{best[2]}"
        )

        report(
            f"  best accuracy         = "
            f"{best[1]:.4f}"
        )

        report(
            f"  best improvement      = "
            f"{best_improvement:.4f}"
        )

        if best_improvement > 0:
            report(
                "  FINDING: retrieval decision rule may be "
                "contributing to the failure."
            )
        else:
            report(
                "  FINDING: changing K/power alone does NOT "
                "demonstrate predictive recovery."
            )

    # ------------------------------------------------------------------
    # 18. CANDIDATE POLICY
    # ------------------------------------------------------------------

    subsection(
        "15. FIX DECISION"
    )

    overall_recovery = any(
        (
            best_configs[h][1]
            > best_configs[h][3]["baseline_accuracy"]
        )
        for h in HORIZONS
    )

    if overall_recovery:

        report(
            "A non-modifying experiment found at least one "
            "configuration that improves over the majority baseline."
        )

        report(
            "This is evidence for a RETRIEVAL/DECISION-LAYER "
            "investigation, but NOT proof that the source itself "
            "should be patched."
        )

        report(
            "No automatic source patch is applied."
        )

    else:

        report(
            "No tested retrieval K/power configuration recovered "
            "predictive advantage."
        )

        report(
            "Therefore the failure is deeper than simple "
            "top-K or similarity-power selection."
        )

        report(
            "Likely investigation targets:"
        )

        report(
            "1. feature separability"
        )

        report(
            "2. episode segmentation"
        )

        report(
            "3. state representation"
        )

        report(
            "4. direction-label definition"
        )

        report(
            "5. market-data sample size / regime coverage"
        )

        report(
            "6. whether historical state similarity actually "
            "contains directional information"
        )

        report(
            "NO SOURCE PATCH IS JUSTIFIED YET."
        )

    # ------------------------------------------------------------------
    # 19. CREATE SAFE CANDIDATE ONLY IF REQUESTED BY EVIDENCE
    # ------------------------------------------------------------------

    candidate_path = Path(
        "mlai_market_structure_v416_candidate.py"
    )

    if candidate_path.exists():
        candidate_path.unlink()

    report()
    report(
        "Candidate source created: NO"
    )

    report(
        "v4.1.5 source modified: NO"
    )

    report(
        "market_data.bin modified: NO"
    )

    report()
    report(
        "AUDIT COMPLETE."
    )

    write_report()

    print()
    print("=" * 100)
    print("FINAL")
    print("=" * 100)
    print()
    print(f"Report written to: {REPORT}")
    print()
    print("v4.1.5 source modified: NO")
    print("market_data.bin modified: NO")
    print("v4.1.6 candidate created: NO")
    print()
    print(
        "IMPORTANT: This run investigates the failure and compares "
        "retrieval strategies. It does NOT silently patch the model."
    )
    print("=" * 100)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:

        print()
        print("=" * 100)
        print("AUDIT PROGRAM FAILURE")
        print("=" * 100)
        print(
            f"{type(exc).__name__}: {exc}"
        )
        print()

        traceback.print_exc()

        try:
            source_hash = sha256(SOURCE)
            data_hash = sha256(DATA)

            print()
            print("POST-FAILURE SAFETY CHECK")
            print(
                f"Source SHA256 : {source_hash}"
            )
            print(
                f"Data SHA256   : {data_hash}"
            )
        except Exception:
            pass

        raise