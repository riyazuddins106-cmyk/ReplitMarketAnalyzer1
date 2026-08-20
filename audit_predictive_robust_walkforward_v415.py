"""
MLAI v4.1.5
ROBUST WALK-FORWARD PREDICTIVE FORENSIC AUDIT

Purpose
-------
Determine whether the apparent predictive advantage observed in the
previous forensic audit survives genuinely unseen chronological data.

IMPORTANT:
- v4.1.5 source is NEVER modified.
- market_data.bin is NEVER modified.
- No v4.1.6 candidate is created.
- Decision-rule selection occurs ONLY on calibration data.
- Final test data remains untouched until evaluation.

This audit is designed to distinguish:

1. genuine predictive signal
2. decision-rule overfitting
3. feature/similarity weakness
4. regime instability
5. horizon instability
6. insufficient evidence
7. temporal leakage

Baseline:
    v4.1.5 weighted aggregation, similarity power=2

Candidate decision rules:
    power_1
    power_2
    power_4
    top_5
    top_10
    top_20
    vote_5
    vote_10
    vote_20

The selected rule is NEVER chosen using the final test set.
"""

from __future__ import annotations

import ast
import hashlib
import importlib
import inspect
import math
import random
import statistics
from collections import Counter, defaultdict
from pathlib import Path


# ================================================================
# CONFIGURATION
# ================================================================

SOURCE = Path("mlai_market_structure_v415.py")
DATA = Path("market_data.bin")
REPORT = Path("MLAI_v415_robust_walkforward_forensic_report.md")

HORIZONS = (4, 8, 16)

# Minimum history before we begin evaluation.
MIN_HISTORY = 400

# Number of candles in each final test block.
TEST_SIZE = 80

# Number of candles immediately before test used for rule calibration.
CALIBRATION_SIZE = 120

# Maximum number of final test queries per fold.
MAX_TEST_QUERIES = 80

# Candidate rules are deliberately kept fixed.
# DO NOT expand this after seeing results.
RULE_NAMES = (
    "power_1",
    "power_2",
    "power_4",
    "top_5",
    "top_10",
    "top_20",
    "vote_5",
    "vote_10",
    "vote_20",
)

RANDOM_SEED = 415

# Bootstrap repetitions.
BOOTSTRAP_REPS = 5000

# Permutation repetitions.
PERMUTATION_REPS = 5000


# ================================================================
# BASIC HELPERS
# ================================================================

random.seed(RANDOM_SEED)


def sha256(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)

            if not chunk:
                break

            h.update(chunk)

    return h.hexdigest()


def section(title: str) -> None:
    print()
    print("=" * 100)
    print(title)
    print("=" * 100)


def accuracy(actual, predicted) -> float:
    if not actual:
        return 0.0

    return sum(
        a == p
        for a, p in zip(actual, predicted)
    ) / len(actual)


def direction_accuracy(actual, predicted, direction):
    pairs = [
        (a, p)
        for a, p in zip(actual, predicted)
        if a == direction
    ]

    if not pairs:
        return 0.0

    return sum(
        a == p
        for a, p in pairs
    ) / len(pairs)


def precision_for(actual, predicted, direction):
    predicted_direction = [
        (a, p)
        for a, p in zip(actual, predicted)
        if p == direction
    ]

    if not predicted_direction:
        return 0.0

    return sum(
        a == direction
        for a, _ in predicted_direction
    ) / len(predicted_direction)


def balanced_accuracy(actual, predicted):
    directions = ("UP", "DOWN", "NEUTRAL")

    scores = []

    for direction in directions:
        subset = [
            (a, p)
            for a, p in zip(actual, predicted)
            if a == direction
        ]

        if not subset:
            continue

        scores.append(
            sum(a == p for a, p in subset) / len(subset)
        )

    if not scores:
        return 0.0

    return statistics.mean(scores)


def majority_direction(records):
    counts = Counter(
        r.outcome.direction
        for r in records
    )

    if not counts:
        return "NEUTRAL"

    return counts.most_common(1)[0][0]


def mean_or_zero(values):
    if not values:
        return 0.0

    return statistics.mean(values)


def make_prediction_weighted(scored, power):
    if not scored:
        return "NEUTRAL", 0.0

    weights = [
        max(sim, 0.0) ** power
        for sim, _ in scored
    ]

    total_weight = sum(weights)

    if total_weight <= 0:
        return "NEUTRAL", 0.0

    shares = {}

    for direction in ("UP", "DOWN", "NEUTRAL"):
        shares[direction] = (
            sum(
                weight
                for weight, (_, record) in zip(weights, scored)
                if record.outcome.direction == direction
            )
            / total_weight
        )

    prediction = max(
        shares.items(),
        key=lambda item: item[1],
    )[0]

    confidence = shares[prediction]

    return prediction, confidence


def make_prediction_vote(scored):
    if not scored:
        return "NEUTRAL", 0.0

    counts = Counter(
        record.outcome.direction
        for _, record in scored
    )

    prediction, count = counts.most_common(1)[0]

    confidence = count / len(scored)

    return prediction, confidence


def apply_rule(scored, rule_name):
    if rule_name == "power_1":
        return make_prediction_weighted(
            scored,
            power=1,
        )

    if rule_name == "power_2":
        return make_prediction_weighted(
            scored,
            power=2,
        )

    if rule_name == "power_4":
        return make_prediction_weighted(
            scored,
            power=4,
        )

    if rule_name == "top_5":
        return make_prediction_weighted(
            scored[:5],
            power=2,
        )

    if rule_name == "top_10":
        return make_prediction_weighted(
            scored[:10],
            power=2,
        )

    if rule_name == "top_20":
        return make_prediction_weighted(
            scored[:20],
            power=2,
        )

    if rule_name == "vote_5":
        return make_prediction_vote(
            scored[:5]
        )

    if rule_name == "vote_10":
        return make_prediction_vote(
            scored[:10]
        )

    if rule_name == "vote_20":
        return make_prediction_vote(
            scored[:20]
        )

    raise ValueError(
        f"Unknown decision rule: {rule_name}"
    )


# ================================================================
# STATISTICS
# ================================================================

def bootstrap_mean_ci(values, reps=BOOTSTRAP_REPS):
    if not values:
        return 0.0, 0.0, 0.0

    rng = random.Random(RANDOM_SEED)

    observed = statistics.mean(values)

    if len(values) == 1:
        return observed, observed, observed

    boot = []

    for _ in range(reps):
        sample = [
            values[rng.randrange(len(values))]
            for _ in range(len(values))
        ]

        boot.append(
            statistics.mean(sample)
        )

    boot.sort()

    low = boot[
        int(0.025 * len(boot))
    ]

    high = boot[
        int(0.975 * len(boot))
    ]

    return observed, low, high


def paired_sign_test(differences, reps=PERMUTATION_REPS):
    """
    Random-sign permutation test.

    H0:
        The observed paired improvement has no directional advantage.

    Each non-zero paired difference has its sign randomly flipped.
    """

    nonzero = [
        x
        for x in differences
        if x != 0
    ]

    if not nonzero:
        return {
            "n": 0,
            "observed": 0.0,
            "p_value": 1.0,
        }

    observed = sum(nonzero)

    rng = random.Random(
        RANDOM_SEED + 991
    )

    extreme = 0

    for _ in range(reps):
        randomized = sum(
            x if rng.random() < 0.5 else -x
            for x in nonzero
        )

        if abs(randomized) >= abs(observed):
            extreme += 1

    p_value = (
        extreme + 1
    ) / (
        reps + 1
    )

    return {
        "n": len(nonzero),
        "observed": observed,
        "p_value": p_value,
    }


# ================================================================
# STATIC FORENSICS
# ================================================================

section("MLAI v4.1.5 — ROBUST WALK-FORWARD FORENSIC AUDIT")

print(
    """
This audit is STRICTLY READ-ONLY.

No baseline source modification.
No market-data modification.
No v4.1.6 creation.
No decision-rule selection from final test data.
"""
)

if not SOURCE.exists():
    raise FileNotFoundError(SOURCE)

if not DATA.exists():
    raise FileNotFoundError(DATA)

source_hash_before = sha256(SOURCE)
data_hash_before = sha256(DATA)

print("SOURCE SHA256:", source_hash_before)
print("DATA SHA256  :", data_hash_before)


section("1. STATIC SOURCE CONTRACT")

tree = ast.parse(
    SOURCE.read_text(
        encoding="utf-8"
    )
)

functions = {
    n.name: n.lineno
    for n in ast.walk(tree)
    if isinstance(
        n,
        (
            ast.FunctionDef,
            ast.AsyncFunctionDef,
        ),
    )
}

classes = {
    n.name: n.lineno
    for n in ast.walk(tree)
    if isinstance(
        n,
        ast.ClassDef,
    )
}

required_functions = (
    "load_market_data",
    "calculate_atr",
    "build_path_vector",
    "build_market_states",
    "assign_episode_ids",
    "build_experience_records",
    "make_outcome",
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

missing_functions = [
    x
    for x in required_functions
    if x not in functions
]

missing_classes = [
    x
    for x in required_classes
    if x not in classes
]

if missing_functions or missing_classes:
    raise RuntimeError(
        "Baseline contract missing."
    )


# ================================================================
# IMPORT
# ================================================================

section("2. MODULE IMPORT")

module = importlib.import_module(
    "mlai_market_structure_v415"
)

print("IMPORT: PASS")


# ================================================================
# API SIGNATURES
# ================================================================

section("3. ACTUAL API SIGNATURES")

for name in (
    "load_market_data",
    "calculate_atr",
    "build_market_states",
    "assign_episode_ids",
    "build_experience_records",
    "make_outcome",
    "similarity_score",
    "retrieve_historical_experience",
):
    obj = getattr(module, name)

    print()
    print(name)
    print(inspect.signature(obj))


# ================================================================
# MARKET DATA
# ================================================================

section("4. MARKET DATA")

candles, invalid = module.load_market_data(
    module.MARKET_DATA_FILE
)

print("candles:", len(candles))
print("invalid:", invalid)

if invalid != 0:
    raise RuntimeError(
        "Invalid candle count is non-zero."
    )

if len(candles) < MIN_HISTORY + TEST_SIZE:
    raise RuntimeError(
        "Insufficient candle history for robust walk-forward audit."
    )

print("first:", candles[0])
print("last :", candles[-1])


# ================================================================
# ATR
# ================================================================

section("5. ATR")

atr = module.calculate_atr(candles)

print("ATR length:", len(atr))

if len(atr) != len(candles):
    raise RuntimeError(
        "ATR length mismatch."
    )

print("ATR: PASS")


# ================================================================
# CAUSAL STRUCTURE
# ================================================================

section("6. CAUSAL STRUCTURE")

engine_cls = module.CausalStructureEngine

constructor = inspect.signature(
    engine_cls
)

print("constructor:", constructor)

engine = engine_cls(candles)

build_method = getattr(
    engine,
    "build",
)

print(
    "build:",
    inspect.signature(build_method)
)

structure = build_method()

print(
    "structure length:",
    len(structure)
)

if len(structure) != len(candles):
    raise RuntimeError(
        "Structure length mismatch."
    )

print("STRUCTURE: PASS")


# ================================================================
# MARKET STATES
# ================================================================

section("7. MARKET STATES")

states = module.build_market_states(
    candles,
    structure,
    atr,
)

print(
    "market states:",
    len(states)
)

if len(states) != len(candles):
    raise RuntimeError(
        "Market state length mismatch."
    )

print("MARKET STATES: PASS")


# ================================================================
# EPISODES
# ================================================================

section("8. EPISODES")

episode_ids = module.assign_episode_ids(
    states
)

print(
    "episode coverage:",
    len(episode_ids)
)

print(
    "unique episodes:",
    len(set(episode_ids.values()))
)

if len(episode_ids) != len(candles):
    raise RuntimeError(
        "Episode coverage mismatch."
    )

print("EPISODES: PASS")


# ================================================================
# BUILD HISTORICAL RECORDS
# ================================================================

section("9. HISTORICAL EXPERIENCE CONTRACT")

experience_fn = (
    module.build_experience_records
)

make_outcome = module.make_outcome
similarity_fn = module.similarity_score
retrieval_fn = (
    module.retrieve_historical_experience
)

print(
    "experience:",
    inspect.signature(experience_fn)
)

print(
    "make_outcome:",
    inspect.signature(make_outcome)
)


# ================================================================
# WALK-FORWARD FOLD CREATION
# ================================================================

section("10. WALK-FORWARD DESIGN")

folds = []

fold_id = 1

test_start = MIN_HISTORY

while test_start < len(candles) - TEST_SIZE:

    test_end = min(
        test_start + TEST_SIZE,
        len(candles) - 1,
    )

    calibration_start = max(
        MIN_HISTORY - CALIBRATION_SIZE,
        test_start - CALIBRATION_SIZE,
    )

    calibration_end = test_start

    if calibration_end - calibration_start < 40:
        test_start += TEST_SIZE
        continue

    folds.append(
        {
            "fold": fold_id,
            "calibration_start": calibration_start,
            "calibration_end": calibration_end,
            "test_start": test_start,
            "test_end": test_end,
        }
    )

    fold_id += 1

    test_start = test_end

print("fold count:", len(folds))

for fold in folds:
    print(
        f"FOLD {fold['fold']}: "
        f"CALIBRATION "
        f"[{fold['calibration_start']}:{fold['calibration_end']}) "
        f"TEST "
        f"[{fold['test_start']}:{fold['test_end']})"
    )

if len(folds) < 3:
    raise RuntimeError(
        "Robust audit requires at least 3 walk-forward folds."
    )


# ================================================================
# QUERY SCORING
# ================================================================

def build_historical_records(query_index, horizon):
    """
    Strict causal historical records.

    build_experience_records() guarantees that every historical
    outcome completes before train_end=query_index.

    Therefore:
        record.index + horizon < query_index
    is enforced by the baseline implementation.
    """

    return experience_fn(
        candles,
        atr,
        states,
        episode_ids,
        0,
        query_index,
        horizon,
    )


def score_query(query_index, horizon):
    """
    Score one chronological query.

    Returns:
        target
        scored historical records
        retrieval result
        temporal violation count
    """

    target_outcome = make_outcome(
        candles,
        atr,
        query_index,
        horizon,
    )

    if target_outcome is None:
        return None

    historical = build_historical_records(
        query_index,
        horizon,
    )

    if not historical:
        return None

    current = states[query_index]

    retrieval = retrieval_fn(
        current,
        historical,
        horizon,
        query_index,
    )

    # Re-score all historical records so every decision rule
    # uses the SAME candidate population.
    scored = []

    temporal_violations = 0

    for record in historical:

        if record.index >= query_index:
            temporal_violations += 1

        if record.index + horizon >= query_index:
            temporal_violations += 1

        components = similarity_fn(
            current,
            record,
        )

        scored.append(
            (
                components["total"],
                record,
            )
        )

    scored.sort(
        key=lambda x: (
            x[0],
            x[1].index,
        ),
        reverse=True,
    )

    # Retrieval-selected records must also be causal.
    for idx in getattr(
        retrieval,
        "selected_match_indices",
        [],
    ):
        if idx >= query_index:
            temporal_violations += 1

        if idx + horizon >= query_index:
            temporal_violations += 1

    return {
        "target": target_outcome.direction,
        "historical_count": len(historical),
        "scored": scored,
        "retrieval": retrieval,
        "temporal_violations": temporal_violations,
    }


# ================================================================
# CALIBRATION
# ================================================================

def collect_queries(start, end, horizon):
    rows = []

    for query_index in range(
        start,
        min(end, len(candles) - horizon),
    ):
        result = score_query(
            query_index,
            horizon,
        )

        if result is not None:
            rows.append(
                (
                    query_index,
                    result,
                )
            )

    return rows


def select_rule(calibration_rows):
    """
    Select rule ONLY from calibration rows.

    Tie-breaking intentionally prefers power_2, the existing
    v4.1.5 rule, rather than introducing arbitrary complexity.
    """

    scores = {}

    actual = [
        result["target"]
        for _, result in calibration_rows
    ]

    for rule_name in RULE_NAMES:

        predictions = []

        for _, result in calibration_rows:
            prediction, _ = apply_rule(
                result["scored"],
                rule_name,
            )

            predictions.append(
                prediction
            )

        scores[rule_name] = accuracy(
            actual,
            predictions,
        )

    # Deterministic tie-break:
    # prefer existing v4.1.5 power_2.
    ranking = {
        name: (
            scores[name],
            1 if name == "power_2" else 0,
        )
        for name in RULE_NAMES
    }

    selected = max(
        RULE_NAMES,
        key=lambda name: ranking[name],
    )

    return selected, scores


# ================================================================
# RUN WALK-FORWARD AUDIT
# ================================================================

section("11. NESTED WALK-FORWARD AUDIT")

all_results = defaultdict(
    lambda: {
        "actual": [],
        "predictions": [],
        "baseline": [],
        "folds": [],
        "similarities": [],
        "historical_counts": [],
        "temporal_violations": 0,
    }
)

fold_reports = []

for horizon in HORIZONS:

    print()
    print(
        "#" * 100
    )
    print(
        f"HORIZON {horizon}"
    )
    print(
        "#" * 100
    )

    for fold in folds:

        print()
        print(
            f"FOLD {fold['fold']}"
        )

        calibration_rows = collect_queries(
            fold["calibration_start"],
            fold["calibration_end"],
            horizon,
        )

        if len(calibration_rows) < 20:
            print(
                "SKIP: insufficient calibration rows"
            )
            continue

        selected_rule, calibration_scores = (
            select_rule(
                calibration_rows
            )
        )

        print(
            "calibration samples:",
            len(calibration_rows),
        )

        print(
            "selected rule:",
            selected_rule,
        )

        print(
            "calibration scores:",
            {
                k: round(v, 4)
                for k, v in calibration_scores.items()
            },
        )

        test_rows = collect_queries(
            fold["test_start"],
            fold["test_end"],
            horizon,
        )

        if not test_rows:
            print(
                "SKIP: no test rows"
            )
            continue

        fold_actual = []
        fold_selected = []
        fold_baseline = []
        fold_power2 = []

        fold_similarities = []

        fold_violations = 0

        for query_index, result in test_rows:

            target = result["target"]

            selected_prediction, _ = (
                apply_rule(
                    result["scored"],
                    selected_rule,
                )
            )

            power2_prediction, _ = (
                apply_rule(
                    result["scored"],
                    "power_2",
                )
            )

            baseline_prediction = (
                majority_direction(
                    [
                        record
                        for _, record
                        in result["scored"]
                    ]
                )
            )

            fold_actual.append(
                target
            )

            fold_selected.append(
                selected_prediction
            )

            fold_power2.append(
                power2_prediction
            )

            fold_baseline.append(
                baseline_prediction
            )

            if result["scored"]:
                fold_similarities.append(
                    result["scored"][0][0]
                )

            fold_violations += (
                result["temporal_violations"]
            )

        selected_accuracy = accuracy(
            fold_actual,
            fold_selected,
        )

        power2_accuracy = accuracy(
            fold_actual,
            fold_power2,
        )

        baseline_accuracy = accuracy(
            fold_actual,
            fold_baseline,
        )

        print(
            "test samples:",
            len(fold_actual),
        )

        print(
            "selected accuracy:",
            f"{selected_accuracy:.4f}",
        )

        print(
            "fixed power_2:",
            f"{power2_accuracy:.4f}",
        )

        print(
            "majority:",
            f"{baseline_accuracy:.4f}",
        )

        print(
            "selected rule improvement:",
            f"{selected_accuracy - baseline_accuracy:+.4f}",
        )

        print(
            "selected vs power_2:",
            f"{selected_accuracy - power2_accuracy:+.4f}",
        )

        print(
            "temporal violations:",
            fold_violations,
        )

        all_results[horizon][
            "actual"
        ].extend(fold_actual)

        all_results[horizon][
            "predictions"
        ].extend(fold_selected)

        all_results[horizon][
            "baseline"
        ].extend(fold_baseline)

        all_results[horizon][
            "folds"
        ].append(
            {
                "fold": fold["fold"],
                "selected_rule": selected_rule,
                "calibration_scores": calibration_scores,
                "test_samples": len(fold_actual),
                "selected_accuracy": selected_accuracy,
                "power2_accuracy": power2_accuracy,
                "baseline_accuracy": baseline_accuracy,
                "selected_balanced_accuracy":
                    balanced_accuracy(
                        fold_actual,
                        fold_selected,
                    ),
                "power2_balanced_accuracy":
                    balanced_accuracy(
                        fold_actual,
                        fold_power2,
                    ),
                "baseline_balanced_accuracy":
                    balanced_accuracy(
                        fold_actual,
                        fold_baseline,
                    ),
                "temporal_violations":
                    fold_violations,
            }
        )

        all_results[horizon][
            "similarities"
        ].extend(fold_similarities)

        all_results[horizon][
            "historical_counts"
        ].extend(
            result["historical_count"]
            for _, result in test_rows
        )

        all_results[horizon][
            "temporal_violations"
        ] += fold_violations


# ================================================================
# ROBUST SUMMARY
# ================================================================

section("12. ROBUST WALK-FORWARD RESULTS")

summary = {}

for horizon in HORIZONS:

    data = all_results[horizon]

    actual = data["actual"]
    selected = data["predictions"]
    baseline = data["baseline"]

    print()
    print(
        f"HORIZON {horizon}"
    )

    if not actual:
        print(
            "NO VALID TEST DATA"
        )
        continue

    selected_acc = accuracy(
        actual,
        selected,
    )

    baseline_acc = accuracy(
        actual,
        baseline,
    )

    selected_balanced = balanced_accuracy(
        actual,
        selected,
    )

    baseline_balanced = balanced_accuracy(
        actual,
        baseline,
    )

    differences = [
        (1 if p == a else 0)
        -
        (1 if b == a else 0)
        for a, p, b in zip(
            actual,
            selected,
            baseline,
        )
    ]

    mean_diff = statistics.mean(
        differences
    )

    observed, ci_low, ci_high = (
        bootstrap_mean_ci(
            differences
        )
    )

    permutation = paired_sign_test(
        differences
    )

    print(
        "samples:",
        len(actual),
    )

    print(
        "selected accuracy:",
        f"{selected_acc:.6f}",
    )

    print(
        "majority accuracy:",
        f"{baseline_acc:.6f}",
    )

    print(
        "improvement:",
        f"{selected_acc - baseline_acc:+.6f}",
    )

    print(
        "selected balanced accuracy:",
        f"{selected_balanced:.6f}",
    )

    print(
        "majority balanced accuracy:",
        f"{baseline_balanced:.6f}",
    )

    print(
        "paired improvement mean:",
        f"{mean_diff:+.6f}",
    )

    print(
        "bootstrap 95% CI:",
        f"[{ci_low:+.6f}, {ci_high:+.6f}]",
    )

    print(
        "paired permutation p:",
        f"{permutation['p_value']:.6f}",
    )

    print(
        "temporal violations:",
        data["temporal_violations"],
    )

    if data["similarities"]:
        print(
            "mean top similarity:",
            f"{statistics.mean(data['similarities']):.6f}",
        )

    if data["historical_counts"]:
        print(
            "mean historical records:",
            f"{statistics.mean(data['historical_counts']):.2f}",
        )

    rule_counts = Counter(
        fold["selected_rule"]
        for fold in data["folds"]
    )

    print(
        "selected rules:",
        dict(rule_counts),
    )

    summary[horizon] = {
        "samples": len(actual),
        "selected_accuracy": selected_acc,
        "baseline_accuracy": baseline_acc,
        "improvement": (
            selected_acc
            - baseline_acc
        ),
        "selected_balanced_accuracy":
            selected_balanced,
        "baseline_balanced_accuracy":
            baseline_balanced,
        "paired_mean":
            mean_diff,
        "bootstrap_low":
            ci_low,
        "bootstrap_high":
            ci_high,
        "permutation_p":
            permutation["p_value"],
        "temporal_violations":
            data["temporal_violations"],
        "mean_similarity":
            mean_or_zero(
                data["similarities"]
            ),
        "mean_history":
            mean_or_zero(
                data["historical_counts"]
            ),
        "rule_counts":
            dict(rule_counts),
    }


# ================================================================
# FOLD STABILITY
# ================================================================

section("13. FOLD STABILITY")

for horizon in HORIZONS:

    data = all_results[horizon]

    fold_acc = [
        fold["selected_accuracy"]
        for fold in data["folds"]
    ]

    if not fold_acc:
        continue

    print()
    print(
        "HORIZON",
        horizon,
    )

    print(
        "fold accuracies:",
        [
            round(x, 4)
            for x in fold_acc
        ],
    )

    print(
        "mean:",
        f"{statistics.mean(fold_acc):.6f}",
    )

    print(
        "median:",
        f"{statistics.median(fold_acc):.6f}",
    )

    print(
        "min:",
        f"{min(fold_acc):.6f}",
    )

    print(
        "max:",
        f"{max(fold_acc):.6f}",
    )

    if len(fold_acc) >= 2:
        print(
            "stdev:",
            f"{statistics.stdev(fold_acc):.6f}",
        )


# ================================================================
# RULE SELECTION STABILITY
# ================================================================

section("14. DECISION-RULE SELECTION STABILITY")

for horizon in HORIZONS:

    counts = Counter(
        fold["selected_rule"]
        for fold in all_results[horizon]["folds"]
    )

    print()
    print(
        "HORIZON",
        horizon,
    )

    print(
        "rule selection frequency:",
        dict(counts),
    )

    if counts:
        most_common_rule, frequency = (
            counts.most_common(1)[0]
        )

        print(
            "most frequently selected:",
            most_common_rule,
        )

        print(
            "selection frequency:",
            f"{frequency}/{sum(counts.values())}",
        )


# ================================================================
# DIRECTIONAL FORENSICS
# ================================================================

section("15. DIRECTIONAL FORENSICS")

for horizon in HORIZONS:

    data = all_results[horizon]

    actual = data["actual"]
    pred = data["predictions"]

    print()
    print(
        "HORIZON",
        horizon,
    )

    print(
        "actual distribution:",
        dict(Counter(actual)),
    )

    print(
        "prediction distribution:",
        dict(Counter(pred)),
    )

    for direction in (
        "UP",
        "DOWN",
        "NEUTRAL",
    ):
        print(
            f"{direction:8s} "
            f"recall={direction_accuracy(actual, pred, direction):.4f} "
            f"precision={precision_for(actual, pred, direction):.4f}"
        )


# ================================================================
# TEMPORAL SAFETY
# ================================================================

section("16. TEMPORAL ISOLATION")

total_violations = 0

for horizon in HORIZONS:

    violations = (
        all_results[horizon][
            "temporal_violations"
        ]
    )

    total_violations += violations

    print(
        f"H{horizon}: "
        f"{'PASS' if violations == 0 else 'FAIL'} "
        f"violations={violations}"
    )

if total_violations != 0:
    raise RuntimeError(
        "CRITICAL: temporal leakage detected."
    )


# ================================================================
# FILE INTEGRITY
# ================================================================

section("17. FINAL FILE INTEGRITY")

source_hash_after = sha256(SOURCE)
data_hash_after = sha256(DATA)

source_unchanged = (
    source_hash_before
    == source_hash_after
)

data_unchanged = (
    data_hash_before
    == data_hash_after
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
        "CRITICAL: baseline source changed."
    )

if not data_unchanged:
    raise RuntimeError(
        "CRITICAL: market data changed."
    )


# ================================================================
# FORENSIC VERDICT
# ================================================================

section("18. FORENSIC VERDICT")

print(
    """
The audit is now complete.

No source patch has been applied.

The result must NOT be interpreted as proof of predictive
intelligence merely because accuracy exceeds 50% or exceeds
the majority baseline.

The critical evidence is:

1. whether the selected decision rule survives unseen folds,
2. whether its advantage survives paired statistical testing,
3. whether fold performance is stable,
4. whether rule selection is stable,
5. whether balanced accuracy also improves,
6. whether temporal violations remain zero,
7. whether improvements occur across multiple horizons.

Possible conclusions:

A. ROBUST SIGNAL
   The walk-forward selected rule consistently beats the
   fixed v4.1.5 rule and majority baseline on unseen data,
   with stable folds and statistically meaningful paired gains.

B. DECISION-RULE WEAKNESS
   A different rule consistently improves unseen performance,
   suggesting v4.1.5 aggregation is the primary weakness.

C. FEATURE/SIMILARITY WEAKNESS
   No decision rule consistently improves out-of-sample results.
   The retrieval representation is therefore suspect.

D. REGIME INSTABILITY
   Some chronological folds perform strongly while others
   collapse, suggesting the representation does not generalize
   across regimes.

E. INSUFFICIENT EVIDENCE
   Results are mixed and the sample is too small to justify
   changing the architecture.

NO v4.1.6 SHOULD BE CREATED FROM THIS AUDIT AUTOMATICALLY.
"""
)


# ================================================================
# WRITE REPORT
# ================================================================

section("19. WRITE FORENSIC REPORT")

report = []

report.append(
    "# MLAI v4.1.5 — Robust Walk-Forward Predictive Forensic Audit"
)

report.append("")

report.append("## Baseline Integrity")
report.append("")
report.append(
    f"- Source SHA256: `{source_hash_before}`"
)
report.append(
    f"- Data SHA256: `{data_hash_before}`"
)
report.append(
    f"- Source unchanged: `{source_unchanged}`"
)
report.append(
    f"- Data unchanged: `{data_unchanged}`"
)
report.append(
    "- v4.1.5 modified: NO"
)
report.append(
    "- v4.1.6 created: NO"
)

report.append("")

report.append("## Audit Design")
report.append("")
report.append(
    f"- Minimum history: {MIN_HISTORY}"
)
report.append(
    f"- Calibration size: {CALIBRATION_SIZE}"
)
report.append(
    f"- Test size: {TEST_SIZE}"
)
report.append(
    f"- Walk-forward folds: {len(folds)}"
)
report.append(
    "- Decision rule selected only from calibration data"
)
report.append(
    "- Final test data never used for rule selection"
)
report.append(
    "- Query targets obtained using make_outcome()"
)
report.append(
    "- Historical records obtained using build_experience_records()"
)
report.append(
    "- Temporal leakage explicitly checked"
)

report.append("")

report.append("## Results")

for horizon in HORIZONS:

    if horizon not in summary:
        continue

    s = summary[horizon]

    report.append("")
    report.append(
        f"### H{horizon}"
    )
    report.append("")

    report.append(
        f"- Samples: {s['samples']}"
    )

    report.append(
        f"- Walk-forward selected accuracy: "
        f"{s['selected_accuracy']:.6f}"
    )

    report.append(
        f"- Majority baseline: "
        f"{s['baseline_accuracy']:.6f}"
    )

    report.append(
        f"- Improvement over majority: "
        f"{s['improvement']:+.6f}"
    )

    report.append(
        f"- Selected balanced accuracy: "
        f"{s['selected_balanced_accuracy']:.6f}"
    )

    report.append(
        f"- Majority balanced accuracy: "
        f"{s['baseline_balanced_accuracy']:.6f}"
    )

    report.append(
        f"- Paired mean improvement: "
        f"{s['paired_mean']:+.6f}"
    )

    report.append(
        f"- Bootstrap 95% CI: "
        f"[{s['bootstrap_low']:+.6f}, "
        f"{s['bootstrap_high']:+.6f}]"
    )

    report.append(
        f"- Paired permutation p-value: "
        f"{s['permutation_p']:.6f}"
    )

    report.append(
        f"- Mean top similarity: "
        f"{s['mean_similarity']:.6f}"
    )

    report.append(
        f"- Mean historical records: "
        f"{s['mean_history']:.2f}"
    )

    report.append(
        f"- Temporal violations: "
        f"{s['temporal_violations']}"
    )

    report.append(
        f"- Rule selections: "
        f"`{s['rule_counts']}`"
    )

report.append("")

report.append("## Fold Details")

for horizon in HORIZONS:

    report.append("")
    report.append(
        f"### H{horizon}"
    )
    report.append("")

    for fold in all_results[horizon]["folds"]:

        report.append(
            f"- Fold {fold['fold']}: "
            f"selected=`{fold['selected_rule']}`, "
            f"test_samples={fold['test_samples']}, "
            f"selected_accuracy="
            f"{fold['selected_accuracy']:.6f}, "
            f"power_2="
            f"{fold['power2_accuracy']:.6f}, "
            f"majority="
            f"{fold['baseline_accuracy']:.6f}, "
            f"violations="
            f"{fold['temporal_violations']}"
        )

report.append("")

report.append("## Final Interpretation")

for horizon in HORIZONS:

    if horizon not in summary:
        continue

    s = summary[horizon]

    if (
        s["temporal_violations"] == 0
        and s["improvement"] > 0
        and s["bootstrap_low"] > 0
        and s["permutation_p"] < 0.05
    ):
        verdict = (
            "STRONGER EVIDENCE OF OUT-OF-SAMPLE ADVANTAGE"
        )

    elif (
        s["temporal_violations"] == 0
        and s["improvement"] > 0
    ):
        verdict = (
            "POSITIVE BUT NOT STATISTICALLY CONFIRMED"
        )

    else:
        verdict = (
            "NO ROBUST OUT-OF-SAMPLE ADVANTAGE ESTABLISHED"
        )

    report.append(
        f"- H{horizon}: **{verdict}**"
    )

report.append("")

report.append(
    "## Safety"
)

report.append("")

report.append(
    "- Baseline v4.1.5 source was not modified."
)

report.append(
    "- market_data.bin was not modified."
)

report.append(
    "- No v4.1.6 source was generated."
)

REPORT.write_text(
    "\n".join(report),
    encoding="utf-8",
)

print()
print(
    "REPORT WRITTEN:"
)
print(
    REPORT
)

print()
print(
    "=" * 100
)
print(
    "ROBUST WALK-FORWARD AUDIT COMPLETE"
)
print(
    "=" * 100
)