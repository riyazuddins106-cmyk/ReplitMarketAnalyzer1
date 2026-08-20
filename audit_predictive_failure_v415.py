"""
MLAI v4.1.5 — PREDICTIVE FAILURE FORENSIC AUDIT v2

PURPOSE
-------
Investigate the predictive failure of MLAI v4.1.5 without modifying:

    1. mlai_market_structure_v415.py
    2. market_data.bin

CRITICAL DESIGN RULE
--------------------
Historical experience records must contain only outcomes that COMPLETED
strictly before the query candle.

For query q and horizon h:

    historical record i is valid only when:

        i + h < q

The query's own future outcome is NOT constructed through
build_experience_records(), because that function intentionally excludes
outcomes that do not complete before its train_end boundary.

Instead, the query target is obtained directly through the baseline's
actual make_outcome() function.

NO BASELINE SOURCE PATCH IS APPLIED.
NO DATA FILE IS MODIFIED.
NO v4.1.6 IS CREATED.
"""

from __future__ import annotations

import ast
import hashlib
import importlib
import inspect
import math
import statistics
from collections import Counter
from pathlib import Path
from typing import Any


# =====================================================================
# CONFIGURATION
# =====================================================================

SOURCE = Path("mlai_market_structure_v415.py")
DATA = Path("market_data.bin")
REPORT = Path("MLAI_v415_predictive_failure_audit_report_v2.md")

HORIZONS = (4, 8, 16)
QUERY_COUNT = 250
RANDOM_SEED = 415


# =====================================================================
# HELPERS
# =====================================================================

def section(title: str) -> None:
    print()
    print("=" * 100)
    print(title)
    print("=" * 100)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def accuracy(actual, predicted) -> float:
    if not actual:
        return 0.0

    return sum(
        a == p
        for a, p in zip(actual, predicted)
    ) / len(actual)


def majority_direction(records):
    counts = Counter(
        r.outcome.direction
        for r in records
    )

    if not counts:
        return "NEUTRAL"

    return max(
        ("UP", counts.get("UP", 0)),
        ("DOWN", counts.get("DOWN", 0)),
        ("NEUTRAL", counts.get("NEUTRAL", 0)),
        key=lambda x: x[1],
    )[0]


def direction_counts(records):
    return Counter(
        r.outcome.direction
        for r in records
    )


def mean_or_zero(values):
    values = list(values)

    if not values:
        return 0.0

    return statistics.mean(values)


def make_prediction_weighted(scored, power=2.0):
    """
    Weighted directional prediction.

    scored:
        [(similarity, ExperienceRecord), ...]

    Returns:
        (prediction, confidence)
    """

    if not scored:
        return "NEUTRAL", 0.0

    votes = {
        "UP": 0.0,
        "DOWN": 0.0,
        "NEUTRAL": 0.0,
    }

    for similarity, record in scored:
        similarity = max(0.0, float(similarity))
        weight = similarity ** power

        direction = record.outcome.direction

        if direction not in votes:
            continue

        votes[direction] += weight

    total = sum(votes.values())

    if total <= 0.0:
        return "NEUTRAL", 0.0

    prediction = max(
        votes.items(),
        key=lambda x: x[1],
    )[0]

    confidence = votes[prediction] / total

    return prediction, confidence


def make_prediction_vote(scored):
    if not scored:
        return "NEUTRAL", 0.0

    counts = Counter(
        record.outcome.direction
        for _, record in scored
    )

    prediction, count = max(
        counts.items(),
        key=lambda x: x[1],
    )

    confidence = count / len(scored)

    return prediction, confidence


def choose_query_points(
    start: int,
    end_exclusive: int,
    count: int,
):
    possible = list(
        range(start, end_exclusive)
    )

    if len(possible) <= count:
        return possible

    step = len(possible) / count

    return [
        possible[
            min(
                int(i * step),
                len(possible) - 1,
            )
        ]
        for i in range(count)
    ]


def outcome_direction(outcome):
    if outcome is None:
        return None

    direction = getattr(
        outcome,
        "direction",
        None,
    )

    return direction


def outcome_signature_ok(fn):
    try:
        sig = inspect.signature(fn)
    except Exception:
        return False

    params = list(sig.parameters.values())

    # We expect:
    # candles, atr, index, horizon
    if len(params) != 4:
        return False

    return True


# =====================================================================
# INITIAL SAFETY
# =====================================================================

section(
    "MLAI v4.1.5 — PREDICTIVE FAILURE FORENSIC AUDIT v2"
)

print(
    """
This audit investigates predictive failure without modifying the baseline.

SOURCE WILL NOT BE MODIFIED.
DATA WILL NOT BE MODIFIED.
NO v4.1.6 WILL BE CREATED.

IMPORTANT CORRECTION FROM AUDIT v1:

The previous audit attempted to obtain the query target through
build_experience_records(query_index, query_index + 1, horizon).

That is incorrect because build_experience_records() intentionally
requires the future outcome to finish before train_end.

The query target will therefore be obtained directly through the
baseline make_outcome() function.

Historical records remain strictly causal.
"""
)

if not SOURCE.exists():
    raise FileNotFoundError(SOURCE)

if not DATA.exists():
    raise FileNotFoundError(DATA)

source_hash_before = sha256(SOURCE)
data_hash_before = sha256(DATA)

print("Source SHA256:", source_hash_before)
print("Data SHA256  :", data_hash_before)


# =====================================================================
# STATIC SOURCE FORENSICS
# =====================================================================

section("1. STATIC SOURCE FORENSICS")

source_text = SOURCE.read_text(
    encoding="utf-8"
)

tree = ast.parse(source_text)

functions = {
    node.name: node.lineno
    for node in ast.walk(tree)
    if isinstance(
        node,
        (
            ast.FunctionDef,
            ast.AsyncFunctionDef,
        ),
    )
}

classes = {
    node.name: node.lineno
    for node in ast.walk(tree)
    if isinstance(
        node,
        ast.ClassDef,
    )
}

required_functions = [
    "load_market_data",
    "calculate_atr",
    "build_path_vector",
    "build_market_states",
    "assign_episode_ids",
    "build_experience_records",
    "make_outcome",
    "similarity_score",
    "retrieve_historical_experience",
]

required_classes = [
    "Candle",
    "StructureState",
    "MarketState",
    "Outcome",
    "ExperienceRecord",
    "RetrievalResult",
    "CausalStructureEngine",
]

for name in required_functions:
    print(
        f"{'FOUND' if name in functions else 'MISSING':8} "
        f"{name:35} "
        f"line={functions.get(name, '-')}"
    )

for name in required_classes:
    print(
        f"{'FOUND' if name in classes else 'MISSING':8} "
        f"{name}"
    )


if "make_outcome" not in functions:
    raise RuntimeError(
        "CRITICAL: v4.1.5 make_outcome() was not found. "
        "The audit cannot safely construct query targets."
    )


# =====================================================================
# IMPORT
# =====================================================================

section("2. MODULE IMPORT")

module = importlib.import_module(
    "mlai_market_structure_v415"
)

print("IMPORT: PASS")


# =====================================================================
# API SIGNATURES
# =====================================================================

section("3. ACTUAL v4.1.5 API SIGNATURES")

api_names = [
    "load_market_data",
    "calculate_atr",
    "build_market_states",
    "assign_episode_ids",
    "build_experience_records",
    "make_outcome",
    "similarity_score",
    "retrieve_historical_experience",
]

for name in api_names:
    obj = getattr(module, name)

    print()
    print(name)
    print(inspect.signature(obj))


# =====================================================================
# MARKET DATA
# =====================================================================

section("4. MARKET DATA")

candles, invalid = module.load_market_data(
    module.MARKET_DATA_FILE
)

print("candles :", len(candles))
print("invalid :", invalid)
print("first   :", candles[0])
print("type    :", type(candles[0]).__name__)

if invalid != 0:
    raise RuntimeError(
        "Invalid candle count is non-zero."
    )


# =====================================================================
# ATR
# =====================================================================

section("5. ATR")

atr = module.calculate_atr(candles)

print("ATR length:", len(atr))

if len(atr) != len(candles):
    raise RuntimeError(
        "ATR length mismatch."
    )

print("ATR: PASS")


# =====================================================================
# CAUSAL STRUCTURE
# =====================================================================

section("6. CAUSAL STRUCTURE")

engine_cls = module.CausalStructureEngine

print(
    "constructor:",
    inspect.signature(engine_cls),
)

engine = engine_cls(candles)

print(
    "ENGINE CREATED:",
    type(engine).__name__,
)

methods = []

for name in dir(engine):
    if name.startswith("_"):
        continue

    obj = getattr(engine, name)

    if callable(obj):
        try:
            sig = inspect.signature(obj)
        except Exception:
            sig = "?"

        methods.append(
            (name, sig)
        )

for name, sig in methods:
    print(
        f"{name:35} {sig}"
    )

if not hasattr(engine, "build"):
    raise RuntimeError(
        "Expected causal engine build() method was not found."
    )

structure = engine.build()

if len(structure) != len(candles):
    raise RuntimeError(
        "Causal structure length mismatch."
    )

print(
    "STRUCTURE LENGTH:",
    len(structure),
)

print("STRUCTURE: PASS")


# =====================================================================
# MARKET STATES
# =====================================================================

section("7. MARKET STATES")

states = module.build_market_states(
    candles,
    structure,
    atr,
)

print(
    "market states:",
    len(states),
)

if len(states) != len(candles):
    raise RuntimeError(
        "Market state length mismatch."
    )

print("MARKET STATES: PASS")


# =====================================================================
# EPISODES
# =====================================================================

section("8. EPISODES")

episode_ids = module.assign_episode_ids(
    states
)

print(
    "episode coverage:",
    len(episode_ids),
)

print(
    "unique episodes:",
    len(set(episode_ids.values())),
)

if len(episode_ids) != len(candles):
    raise RuntimeError(
        "Episode coverage mismatch."
    )

print("EPISODES: PASS")


# =====================================================================
# EXPERIENCE CONTRACT
# =====================================================================

section("9. EXPERIENCE RECORD CONTRACT")

experience_fn = module.build_experience_records
make_outcome_fn = module.make_outcome
similarity_fn = module.similarity_score
retrieval_fn = module.retrieve_historical_experience

print(
    "build_experience_records:",
    inspect.signature(experience_fn),
)

print(
    "make_outcome:",
    inspect.signature(make_outcome_fn),
)

print(
    "similarity_score:",
    inspect.signature(similarity_fn),
)

print(
    "retrieve_historical_experience:",
    inspect.signature(retrieval_fn),
)

if not outcome_signature_ok(
    make_outcome_fn
):
    raise RuntimeError(
        "Unexpected make_outcome() API. "
        "Refusing to guess."
    )


# =====================================================================
# TRAINING BOUNDARY
# =====================================================================

section("10. DIAGNOSTIC TRAINING BOUNDARY")

train_end = max(
    200,
    int(len(candles) * 0.50),
)

print(
    "diagnostic train_end:",
    train_end,
)

print(
    "The first predictive query will be:",
    train_end,
)

print(
    "Historical records for query q must satisfy:",
)

for h in HORIZONS:
    print(
        f"  H{h}: record.index + {h} < query_index"
    )


# =====================================================================
# EXPERIENCE DISTRIBUTION
# =====================================================================

section("11. HISTORICAL EXPERIENCE DISTRIBUTION")

records_by_horizon = {}

for horizon in HORIZONS:

    records = experience_fn(
        candles,
        atr,
        states,
        episode_ids,
        0,
        train_end,
        horizon,
    )

    records_by_horizon[horizon] = records

    print()
    print("HORIZON", horizon)
    print("records:", len(records))
    print(
        "directions:",
        dict(direction_counts(records))
    )


# =====================================================================
# OUTCOME DISTRIBUTION
# =====================================================================

section("12. OUTCOME DISTRIBUTION")

for horizon, records in records_by_horizon.items():

    raw = [
        r.outcome.raw_return
        for r in records
        if r.outcome.raw_return is not None
    ]

    atr_returns = [
        r.outcome.atr_return
        for r in records
        if r.outcome.atr_return is not None
    ]

    print()
    print("HORIZON", horizon)
    print(
        "direction:",
        dict(direction_counts(records))
    )

    if raw:
        print(
            "raw return mean:",
            statistics.mean(raw)
        )
        print(
            "raw return median:",
            statistics.median(raw)
        )

    if atr_returns:
        print(
            "ATR return mean:",
            statistics.mean(atr_returns)
        )
        print(
            "ATR return median:",
            statistics.median(atr_returns)
        )


# =====================================================================
# TARGET CONSTRUCTION SELF-TEST
# =====================================================================

section("13. QUERY TARGET CONSTRUCTION SELF-TEST")

print(
    """
This is the critical correction.

We do NOT call build_experience_records() with:

    start=query_index
    train_end=query_index + 1

because that function is designed to exclude incomplete future outcomes.

Instead:

    target_outcome = make_outcome(candles, atr, query_index, horizon)

This is the actual future label for the query.
It is used only as the evaluation target and never enters
the historical record set.
"""
)

for horizon in HORIZONS:

    target_count = 0
    none_count = 0

    test_points = choose_query_points(
        train_end,
        len(candles) - horizon,
        min(50, QUERY_COUNT),
    )

    for q in test_points:

        outcome = make_outcome_fn(
            candles,
            atr,
            q,
            horizon,
        )

        if outcome is None:
            none_count += 1
        else:
            target_count += 1

    print()
    print("HORIZON", horizon)
    print("test query points:", len(test_points))
    print("valid targets    :", target_count)
    print("missing targets  :", none_count)

    if target_count == 0:
        raise RuntimeError(
            f"H{horizon}: make_outcome() produced zero "
            "valid query targets. Investigation cannot continue."
        )


# =====================================================================
# CHRONOLOGICAL PREDICTIVE TEST
# =====================================================================

section("14. CORRECTED CHRONOLOGICAL PREDICTIVE TEST")

results = {}

for horizon in HORIZONS:

    print()
    print("#" * 80)
    print("HORIZON", horizon)
    print("#" * 80)

    query_points = choose_query_points(
        train_end,
        len(candles) - horizon,
        QUERY_COUNT,
    )

    print(
        "query points:",
        len(query_points),
    )

    actual = []
    baseline = []
    predictions = []

    top_similarities = []

    temporal_violations = 0
    retrieval_failures = 0

    historical_sizes = []

    for query_index in query_points:

        # -------------------------------------------------------------
        # CORRECT HISTORICAL DATASET
        #
        # build_experience_records() guarantees:
        #
        #     record.index + horizon < query_index
        #
        # because train_end=query_index.
        # -------------------------------------------------------------

        historical_records = experience_fn(
            candles,
            atr,
            states,
            episode_ids,
            0,
            query_index,
            horizon,
        )

        if not historical_records:
            retrieval_failures += 1
            continue

        historical_sizes.append(
            len(historical_records)
        )

        # -------------------------------------------------------------
        # CORRECT QUERY TARGET
        #
        # This MUST NOT be obtained through
        # build_experience_records().
        # -------------------------------------------------------------

        target_outcome = make_outcome_fn(
            candles,
            atr,
            query_index,
            horizon,
        )

        if target_outcome is None:
            retrieval_failures += 1
            continue

        target = outcome_direction(
            target_outcome
        )

        if target is None:
            retrieval_failures += 1
            continue

        actual.append(target)

        # -------------------------------------------------------------
        # BASELINE
        # -------------------------------------------------------------

        baseline_prediction = majority_direction(
            historical_records
        )

        baseline.append(
            baseline_prediction
        )

        # -------------------------------------------------------------
        # RETRIEVAL
        # -------------------------------------------------------------

        current = states[query_index]

        retrieval = retrieval_fn(
            current,
            historical_records,
            horizon,
            query_index,
        )

        selected_indices = list(
            getattr(
                retrieval,
                "selected_match_indices",
                [],
            )
        )

        # -------------------------------------------------------------
        # TEMPORAL ISOLATION
        # -------------------------------------------------------------

        for idx in selected_indices:

            if idx >= query_index:
                temporal_violations += 1

            if idx + horizon >= query_index:
                temporal_violations += 1

        # -------------------------------------------------------------
        # REBUILD SELECTED SCORES
        # -------------------------------------------------------------

        record_by_index = {
            r.index: r
            for r in historical_records
        }

        selected_rows = []

        for idx in selected_indices:

            record = record_by_index.get(idx)

            if record is None:
                continue

            components = similarity_fn(
                current,
                record,
            )

            similarity = float(
                components["total"]
            )

            selected_rows.append(
                (similarity, record)
            )

        selected_rows.sort(
            key=lambda x: x[0],
            reverse=True,
        )

        if not selected_rows:
            retrieval_failures += 1
            continue

        prediction, confidence = (
            make_prediction_weighted(
                selected_rows,
                power=2.0,
            )
        )

        predictions.append(
            prediction
        )

        top_similarities.append(
            selected_rows[0][0]
        )

    results[horizon] = {
        "actual": actual,
        "baseline": baseline,
        "prediction": predictions,
        "top_similarity": top_similarities,
        "temporal_violations": temporal_violations,
        "retrieval_failures": retrieval_failures,
        "historical_sizes": historical_sizes,
    }

    retrieval_accuracy = accuracy(
        actual,
        predictions,
    )

    baseline_accuracy = accuracy(
        actual,
        baseline,
    )

    print()
    print(
        "valid evaluation samples:",
        len(actual),
    )

    print(
        "retrieval predictions:",
        len(predictions),
    )

    print(
        "baseline predictions:",
        len(baseline),
    )

    print(
        "retrieval accuracy:",
        f"{retrieval_accuracy:.6f}",
    )

    print(
        "majority accuracy:",
        f"{baseline_accuracy:.6f}",
    )

    print(
        "difference:",
        f"{retrieval_accuracy - baseline_accuracy:.6f}",
    )

    print(
        "temporal violations:",
        temporal_violations,
    )

    print(
        "retrieval failures:",
        retrieval_failures,
    )

    if historical_sizes:
        print(
            "mean historical records:",
            f"{statistics.mean(historical_sizes):.2f}",
        )

    if top_similarities:
        print(
            "mean top similarity:",
            f"{statistics.mean(top_similarities):.6f}",
        )


# =====================================================================
# DECISION RULE EXPERIMENTS
# =====================================================================

section("15. DECISION RULE FORENSICS")

print(
    """
The same correctly isolated historical records are now tested with
different aggregation rules.

This separates:

    A. feature/similarity failure

from:

    B. decision/aggregation failure
"""
)

experiments = {}

for horizon in HORIZONS:

    query_points = choose_query_points(
        train_end,
        len(candles) - horizon,
        QUERY_COUNT,
    )

    rules = {
        "power_1": [],
        "power_2": [],
        "power_4": [],
        "top_5": [],
        "top_10": [],
        "top_20": [],
        "vote_5": [],
        "vote_10": [],
        "vote_20": [],
    }

    actual = []

    for query_index in query_points:

        historical = experience_fn(
            candles,
            atr,
            states,
            episode_ids,
            0,
            query_index,
            horizon,
        )

        if not historical:
            continue

        target_outcome = make_outcome_fn(
            candles,
            atr,
            query_index,
            horizon,
        )

        if target_outcome is None:
            continue

        target = outcome_direction(
            target_outcome
        )

        if target is None:
            continue

        actual.append(target)

        current = states[query_index]

        scored = []

        for record in historical:

            similarity = similarity_fn(
                current,
                record,
            )["total"]

            scored.append(
                (
                    float(similarity),
                    record,
                )
            )

        scored.sort(
            key=lambda x: x[0],
            reverse=True,
        )

        for power in (1, 2, 4):

            pred, _ = make_prediction_weighted(
                scored,
                power=power,
            )

            rules[
                f"power_{power}"
            ].append(pred)

        for n in (5, 10, 20):

            subset = scored[:n]

            pred, _ = make_prediction_weighted(
                subset,
                power=2,
            )

            rules[
                f"top_{n}"
            ].append(pred)

            pred, _ = make_prediction_vote(
                subset
            )

            rules[
                f"vote_{n}"
            ].append(pred)

    experiments[horizon] = {}

    print()
    print("HORIZON", horizon)
    print("samples:", len(actual))

    for name, predictions in rules.items():

        if len(predictions) != len(actual):
            continue

        acc = accuracy(
            actual,
            predictions,
        )

        experiments[horizon][name] = acc

        print(
            f"{name:12s}: {acc:.6f}"
        )


# =====================================================================
# SIMILARITY COMPONENT FORENSICS
# =====================================================================

section("16. SIMILARITY COMPONENT FORENSICS")

for horizon in HORIZONS:

    query_points = choose_query_points(
        train_end,
        len(candles) - horizon,
        min(50, QUERY_COUNT),
    )

    component_values = {
        "total": [],
        "structure": [],
        "sequence": [],
        "regime": [],
        "location": [],
        "momentum": [],
        "volatility": [],
        "candle": [],
        "path": [],
    }

    records = records_by_horizon[horizon]

    for query_index in query_points:

        historical = experience_fn(
            candles,
            atr,
            states,
            episode_ids,
            0,
            query_index,
            horizon,
        )

        if not historical:
            continue

        current = states[query_index]

        # Sample all historical records for forensic coverage.
        for record in historical:

            components = similarity_fn(
                current,
                record,
            )

            for key in component_values:

                if key in components:
                    component_values[key].append(
                        float(components[key])
                    )

    print()
    print("HORIZON", horizon)

    for key, values in component_values.items():

        if not values:
            print(
                f"{key:12s}: NO DATA"
            )
            continue

        print(
            f"{key:12s}: "
            f"mean={statistics.mean(values):.6f} "
            f"min={min(values):.6f} "
            f"max={max(values):.6f}"
        )


# =====================================================================
# BEST RULE
# =====================================================================

section("17. BEST TESTED DECISION RULE")

best_rules = {}

for horizon in HORIZONS:

    actual = results[horizon]["actual"]
    baseline = results[horizon]["baseline"]

    baseline_acc = accuracy(
        actual,
        baseline,
    )

    candidates = experiments.get(
        horizon,
        {},
    )

    if not candidates:
        continue

    best_name, best_acc = max(
        candidates.items(),
        key=lambda x: x[1],
    )

    improvement = (
        best_acc - baseline_acc
    )

    best_rules[horizon] = (
        best_name,
        best_acc,
        baseline_acc,
        improvement,
    )

    print()
    print("HORIZON", horizon)
    print(
        "majority baseline:",
        f"{baseline_acc:.6f}",
    )
    print(
        "best tested rule:",
        best_name,
    )
    print(
        "best accuracy:",
        f"{best_acc:.6f}",
    )
    print(
        "improvement:",
        f"{improvement:.6f}",
    )


# =====================================================================
# FINAL SAFETY
# =====================================================================

section("18. FINAL FILE INTEGRITY")

source_hash_after = sha256(SOURCE)
data_hash_after = sha256(DATA)

source_unchanged = (
    source_hash_before == source_hash_after
)

data_unchanged = (
    data_hash_before == data_hash_after
)

print(
    "Source unchanged:",
    source_unchanged,
)

print(
    "Data unchanged  :",
    data_unchanged,
)

if not source_unchanged:
    raise RuntimeError(
        "CRITICAL: v4.1.5 source changed."
    )

if not data_unchanged:
    raise RuntimeError(
        "CRITICAL: market_data.bin changed."
    )


# =====================================================================
# REPORT
# =====================================================================

section("19. WRITE FORENSIC REPORT")

report = []

report.append(
    "# MLAI v4.1.5 Predictive Failure Forensic Audit v2"
)

report.append("")

report.append(
    "## Baseline Integrity"
)

report.append("")

report.append(
    f"- Source SHA256: `{source_hash_before}`"
)

report.append(
    f"- Data SHA256: `{data_hash_before}`"
)

report.append(
    "- v4.1.5 source modified: NO"
)

report.append(
    "- market_data.bin modified: NO"
)

report.append("")

report.append(
    "## Audit Method Correction"
)

report.append("")

report.append(
    "The previous audit incorrectly attempted to construct the "
    "query target through `build_experience_records()` with "
    "`train_end=query_index+1`. That function intentionally excludes "
    "future outcomes that do not complete before `train_end`, causing "
    "zero query samples."
)

report.append("")

report.append(
    "The corrected audit obtains the query target directly from the "
    "actual v4.1.5 `make_outcome()` function while retaining strict "
    "historical isolation."
)

report.append("")

report.append(
    "For query index `q` and horizon `h`, historical records must satisfy:"
)

report.append("")

report.append(
    "```text"
)

report.append(
    "record.index + horizon < query_index"
)

report.append(
    "```"
)

report.append("")

report.append(
    "The query outcome is never inserted into the historical retrieval set."
)

report.append("")

report.append(
    "## Corrected Predictive Results"
)

report.append("")

for horizon in HORIZONS:

    result = results[horizon]

    actual = result["actual"]
    predictions = result["prediction"]
    baseline = result["baseline"]

    retrieval_acc = accuracy(
        actual,
        predictions,
    )

    baseline_acc = accuracy(
        actual,
        baseline,
    )

    report.append(
        f"### H{horizon}"
    )

    report.append("")

    report.append(
        f"- Evaluation samples: {len(actual)}"
    )

    report.append(
        f"- Retrieval accuracy: {retrieval_acc:.6f}"
    )

    report.append(
        f"- Majority baseline: {baseline_acc:.6f}"
    )

    report.append(
        f"- Improvement: "
        f"{retrieval_acc - baseline_acc:.6f}"
    )

    report.append(
        f"- Temporal violations: "
        f"{result['temporal_violations']}"
    )

    report.append(
        f"- Retrieval failures: "
        f"{result['retrieval_failures']}"
    )

    if result["top_similarity"]:

        report.append(
            f"- Mean top similarity: "
            f"{statistics.mean(result['top_similarity']):.6f}"
        )

    if horizon in best_rules:

        name, best_acc, baseline_acc, improvement = (
            best_rules[horizon]
        )

        report.append(
            f"- Best tested rule: `{name}`"
        )

        report.append(
            f"- Best tested accuracy: {best_acc:.6f}"
        )

        report.append(
            f"- Best improvement: {improvement:.6f}"
        )

    report.append("")


report.append(
    "## Interpretation"
)

report.append("")

report.append(
    "This audit does not modify v4.1.5 and does not create v4.1.6."
)

report.append("")

report.append(
    "The corrected results must be used to determine whether the "
    "predictive weakness originates from historical experience "
    "construction, similarity representation, retrieval selection, "
    "decision aggregation, outcome definition, or lack of predictive "
    "signal in the supplied data."
)

report.append("")

report.append(
    "## Final Integrity"
)

report.append("")

report.append(
    f"- Source unchanged: `{source_unchanged}`"
)

report.append(
    f"- Data unchanged: `{data_unchanged}`"
)

REPORT.write_text(
    "\n".join(report),
    encoding="utf-8",
)

print()
print("REPORT WRITTEN:")
print(REPORT)


# =====================================================================
# FINAL
# =====================================================================

section("FINAL VERDICT")

print(
    """
CORRECTED FORENSIC AUDIT COMPLETE.

IMPORTANT:

The previous zero-sample result was an AUDIT-PROGRAM ERROR.

This version:

    1. uses the actual v4.1.5 causal engine API,
    2. uses the actual v4.1.5 market-state API,
    3. uses build_experience_records() only for historical data,
    4. obtains query targets directly through make_outcome(),
    5. enforces strict chronological isolation,
    6. tests alternative decision rules,
    7. leaves v4.1.5 untouched,
    8. leaves market_data.bin untouched.

DO NOT PATCH v4.1.5 YET.

The corrected results are the evidence we need before deciding
whether a real v4.1.6 source fix is justified.
"""
)