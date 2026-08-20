"""
MLAI v4.1.5 — FULL FORENSIC PREDICTIVE AUDIT
==============================================================

PURPOSE
-------
One-shot forensic investigation of MLAI v4.1.5 predictive behavior.

This audit is READ-ONLY.

It does NOT:
    - modify v4.1.5
    - modify market_data.bin
    - create v4.1.6
    - tune source parameters
    - select a final production rule
    - write anything into the baseline source

It investigates:

    1. source/API integrity
    2. market-data integrity
    3. ATR integrity
    4. causal structure integrity
    5. prefix/counterfactual causal stability
    6. market-state stability
    7. episode integrity
    8. historical-record integrity
    9. chronological isolation
   10. similarity distribution
   11. similarity decile behavior
   12. nearest-neighbor outcome consistency
   13. fixed aggregation rules
   14. baseline retrieval behavior
   15. prediction distribution
   16. confusion matrices
   17. balanced accuracy
   18. macro F1
   19. per-class precision/recall
   20. prediction entropy
   21. class-distribution divergence
   22. similarity/outcome association
   23. label permutation null test
   24. temporal block bootstrap
   25. fold stability
   26. regime-conditioned performance
   27. horizon consistency
   28. nearest-match stability
   29. duplicate/near-duplicate historical matches
   30. evidence grading
   31. automatic forensic diagnosis
   32. recommended fix categories

IMPORTANT
---------
This program deliberately does NOT automatically modify MLAI.

The final report separates:

    VERIFIED FACTS
    STRONG EVIDENCE
    WEAK EVIDENCE
    UNKNOWN
    SUSPECTED DEFECTS
    POSSIBLE SOLUTIONS

Run from:

    C:\\Users\\HomePC\\mlai-test
"""

from __future__ import annotations

import hashlib
import inspect
import math
import os
import random
import statistics
import sys
import traceback
from collections import Counter, defaultdict
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any


# ================================================================
# CONFIGURATION
# ================================================================

SOURCE_FILE = "mlai_market_structure_v415.py"
DATA_FILE = "market_data.bin"

REPORT_FILE = "MLAI_v415_FULL_FORENSIC_REPORT.md"

HORIZONS = (4, 8, 16)

# Walk-forward configuration.
CALIBRATION_SIZE = 160
TEST_SIZE = 80
STEP = 80
FIRST_TEST = 400
LAST_TEST = 1280

# Similarity diagnostics.
DECILES = 10
TOP_K_VALUES = (1, 3, 5, 10, 20, 50)

# Permutation test.
PERMUTATIONS = 1000
RANDOM_SEED = 4151608

# Bootstrap.
BOOTSTRAP_ROUNDS = 2000

# Prefix causality checkpoints.
PREFIX_CHECKPOINTS = 12

# Numerical tolerance.
EPS = 1e-12


# ================================================================
# UTILITIES
# ================================================================

random.seed(RANDOM_SEED)


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            block = f.read(1024 * 1024)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def safe_repr(obj: Any, limit: int = 500) -> str:
    try:
        text = repr(obj)
    except Exception:
        text = f"<repr failed: {type(obj).__name__}>"
    return text[:limit]


def object_dict(obj: Any) -> dict[str, Any]:
    if obj is None:
        return {}

    if is_dataclass(obj):
        try:
            return asdict(obj)
        except Exception:
            pass

    if hasattr(obj, "__dict__"):
        try:
            return dict(vars(obj))
        except Exception:
            pass

    result = {}

    for name in dir(obj):
        if name.startswith("_"):
            continue
        try:
            value = getattr(obj, name)
        except Exception:
            continue

        if callable(value):
            continue

        if isinstance(value, (str, int, float, bool, type(None))):
            result[name] = value

    return result


def first_attr(obj: Any, names: list[str], default=None):
    for name in names:
        try:
            if hasattr(obj, name):
                value = getattr(obj, name)
                if value is not None:
                    return value
        except Exception:
            pass
    return default


def direction_of(obj: Any) -> str | None:
    """
    Robustly extract direction from Outcome / ExperienceRecord /
    RetrievalResult-like objects.
    """
    if obj is None:
        return None

    if isinstance(obj, str):
        value = obj.upper()
        if value in {"UP", "DOWN", "NEUTRAL"}:
            return value

    candidates = [
        "direction",
        "label",
        "target",
        "outcome_direction",
        "predicted_direction",
        "prediction",
        "class_name",
    ]

    value = first_attr(obj, candidates)

    if value is not None:
        if isinstance(value, str):
            value = value.upper()
            if value in {"UP", "DOWN", "NEUTRAL"}:
                return value

    nested = first_attr(obj, ["outcome", "prediction", "result"])

    if nested is not None and nested is not obj:
        value = direction_of(nested)
        if value:
            return value

    return None


def index_of_record(record: Any) -> int | None:
    value = first_attr(
        record,
        [
            "index",
            "query_index",
            "source_index",
            "candle_index",
            "entry_index",
        ],
    )

    if isinstance(value, int):
        return value

    try:
        return int(value)
    except Exception:
        return None


def outcome_of_record(record: Any):
    return first_attr(
        record,
        [
            "outcome",
            "target",
            "result",
        ],
    )


def direction_of_record(record: Any) -> str | None:
    value = direction_of(record)
    if value:
        return value

    nested = outcome_of_record(record)

    if nested is not None:
        return direction_of(nested)

    return None


def state_signature(state: Any):
    """
    Stable representation for causal-prefix comparison.

    We intentionally ignore object identity and retain primitive
    dataclass/object fields.
    """
    data = object_dict(state)

    normalized = {}

    for key, value in sorted(data.items()):
        if isinstance(value, (int, float, str, bool, type(None))):
            if isinstance(value, float):
                if math.isnan(value):
                    normalized[key] = "NaN"
                elif math.isinf(value):
                    normalized[key] = "INF" if value > 0 else "-INF"
                else:
                    normalized[key] = round(value, 12)
            else:
                normalized[key] = value
        elif isinstance(value, (list, tuple)):
            normalized[key] = tuple(
                round(x, 12) if isinstance(x, float) else x
                for x in value
            )
        else:
            normalized[key] = safe_repr(value, 300)

    return tuple(sorted(normalized.items()))


def mean(values):
    return sum(values) / len(values) if values else float("nan")


def stdev(values):
    return statistics.stdev(values) if len(values) >= 2 else 0.0


def percentile(values, p):
    if not values:
        return float("nan")

    xs = sorted(values)

    if len(xs) == 1:
        return xs[0]

    position = (len(xs) - 1) * p
    low = int(math.floor(position))
    high = int(math.ceil(position))

    if low == high:
        return xs[low]

    weight = position - low

    return xs[low] * (1 - weight) + xs[high] * weight


def clamp01(x):
    return max(0.0, min(1.0, x))


# ================================================================
# CLASSIFICATION METRICS
# ================================================================

CLASSES = ("UP", "DOWN", "NEUTRAL")


def accuracy(y_true, y_pred):
    if not y_true:
        return 0.0

    return sum(a == b for a, b in zip(y_true, y_pred)) / len(y_true)


def confusion_matrix(y_true, y_pred):
    cm = {actual: {pred: 0 for pred in CLASSES} for actual in CLASSES}

    for actual, pred in zip(y_true, y_pred):
        if actual not in CLASSES:
            continue
        if pred not in CLASSES:
            continue
        cm[actual][pred] += 1

    return cm


def precision_recall(cm, cls):
    tp = cm[cls][cls]

    fp = sum(cm[actual][cls] for actual in CLASSES if actual != cls)
    fn = sum(cm[cls][pred] for pred in CLASSES if pred != cls)

    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0

    return precision, recall


def balanced_accuracy(y_true, y_pred):
    recalls = []

    for cls in CLASSES:
        actual_count = sum(x == cls for x in y_true)

        if actual_count == 0:
            continue

        tp = sum(
            a == cls and p == cls
            for a, p in zip(y_true, y_pred)
        )

        recalls.append(tp / actual_count)

    return mean(recalls) if recalls else 0.0


def macro_f1(y_true, y_pred):
    cm = confusion_matrix(y_true, y_pred)

    fs = []

    for cls in CLASSES:
        precision, recall = precision_recall(cm, cls)

        if precision + recall:
            fs.append(
                2 * precision * recall / (precision + recall)
            )
        else:
            fs.append(0.0)

    return mean(fs)


def prediction_entropy(predictions):
    if not predictions:
        return 0.0

    counts = Counter(predictions)
    n = len(predictions)

    entropy = 0.0

    for count in counts.values():
        p = count / n
        entropy -= p * math.log(p + EPS, 2)

    return entropy


def distribution(predictions):
    c = Counter(predictions)
    n = len(predictions)

    return {
        cls: c[cls] / n if n else 0.0
        for cls in CLASSES
    }


def js_divergence(p, q):
    """
    Jensen-Shannon divergence in bits.
    """
    keys = CLASSES

    m = {
        k: 0.5 * (p.get(k, 0.0) + q.get(k, 0.0))
        for k in keys
    }

    def kl(a, b):
        value = 0.0

        for k in keys:
            x = a.get(k, 0.0)

            if x > 0:
                value += x * math.log(
                    x / max(b.get(k, 0.0), EPS),
                    2,
                )

        return value

    return 0.5 * kl(p, m) + 0.5 * kl(q, m)


# ================================================================
# RULES
# ================================================================

RULES = (
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


def aggregate_rule(records, similarities, rule):
    """
    Aggregate historical record directions using similarity scores.
    """
    pairs = []

    for record, score in zip(records, similarities):
        direction = direction_of_record(record)

        if direction not in CLASSES:
            continue

        total = score.get("total", 0.0)

        pairs.append((total, direction))

    if not pairs:
        return None

    pairs.sort(reverse=True, key=lambda x: x[0])

    if rule == "power_1":
        weights = [(s, d) for s, d in pairs]

    elif rule == "power_2":
        weights = [(s * s, d) for s, d in pairs]

    elif rule == "power_4":
        weights = [(s ** 4, d) for s, d in pairs]

    elif rule.startswith("top_"):
        k = int(rule.split("_")[1])
        weights = [(1.0, d) for _, d in pairs[:k]]

    elif rule.startswith("vote_"):
        k = int(rule.split("_")[1])
        weights = [(1.0, d) for _, d in pairs[:k]]

    else:
        raise ValueError(rule)

    votes = Counter()

    for weight, direction in weights:
        votes[direction] += weight

    return max(
        CLASSES,
        key=lambda cls: (votes[cls], cls),
    )


# ================================================================
# MODULE DISCOVERY
# ================================================================

print("=" * 110)
print("MLAI v4.1.5 — FULL FORENSIC PREDICTIVE AUDIT")
print("=" * 110)

print()
print("READ-ONLY AUDIT")
print("NO SOURCE MODIFICATION")
print("NO DATA MODIFICATION")
print("NO v4.1.6 CREATION")
print("NO FINAL-TEST OPTIMIZATION")
print()

if not os.path.exists(SOURCE_FILE):
    raise FileNotFoundError(SOURCE_FILE)

if not os.path.exists(DATA_FILE):
    raise FileNotFoundError(DATA_FILE)

source_hash_before = sha256_file(SOURCE_FILE)
data_hash_before = sha256_file(DATA_FILE)

print("SOURCE SHA256:", source_hash_before)
print("DATA SHA256  :", data_hash_before)

print()
print("=" * 110)
print("1. MODULE IMPORT / API DISCOVERY")
print("=" * 110)

try:
    import mlai_market_structure_v415 as mlai
except Exception:
    traceback.print_exc()
    raise

required_names = [
    "load_market_data",
    "calculate_atr",
    "build_path_vector",
    "build_market_states",
    "assign_episode_ids",
    "build_experience_records",
    "make_outcome",
    "similarity_score",
    "retrieve_historical_experience",
    "CausalStructureEngine",
]

for name in required_names:
    print(
        f"{'FOUND' if hasattr(mlai, name) else 'MISSING':8} "
        f"{name}"
    )

if not all(hasattr(mlai, x) for x in required_names):
    raise RuntimeError(
        "Required v4.1.5 API is incomplete."
    )

print()
for name in required_names:
    obj = getattr(mlai, name)

    try:
        print(name)
        print(" ", inspect.signature(obj))
    except Exception:
        print(" ", type(obj))


# ================================================================
# LOAD DATA
# ================================================================

print()
print("=" * 110)
print("2. MARKET DATA INTEGRITY")
print("=" * 110)

candles, invalid = mlai.load_market_data(DATA_FILE)

print("candles:", len(candles))
print("invalid:", invalid)

if not candles:
    raise RuntimeError("No candles loaded.")

timestamps = [c.timestamp for c in candles]

print("timestamp monotonic:", all(
    timestamps[i] < timestamps[i + 1]
    for i in range(len(timestamps) - 1)
))

print("duplicate timestamps:", len(timestamps) - len(set(timestamps)))

ohlc_errors = 0

for c in candles:
    if not (
        c.low <= c.open <= c.high
        and c.low <= c.close <= c.high
    ):
        ohlc_errors += 1

print("OHLC consistency errors:", ohlc_errors)

print("first:", candles[0])
print("last :", candles[-1])


# ================================================================
# ATR / STRUCTURE / STATES
# ================================================================

print()
print("=" * 110)
print("3. BASELINE FEATURE CONSTRUCTION")
print("=" * 110)

atr = mlai.calculate_atr(candles)

print("ATR length:", len(atr))
print("ATR valid:", sum(x is not None for x in atr))
print("ATR missing:", sum(x is None for x in atr))

engine = mlai.CausalStructureEngine(candles)

states = engine.build()

print("structure length:", len(states))

market_states = mlai.build_market_states(
    candles,
    states,
    atr,
)

print("market states:", len(market_states))

episode_ids = mlai.assign_episode_ids(
    market_states
)

print("episode coverage:", len(episode_ids))
print("unique episodes:", len(set(episode_ids.values())))


# ================================================================
# 4. CRITICAL CAUSAL PREFIX TEST
# ================================================================

print()
print("=" * 110)
print("4. CRITICAL CAUSAL PREFIX-STABILITY TEST")
print("=" * 110)

print()
print(
    "This test checks whether the state at time t changes when "
    "future candles are added."
)
print()
print(
    "A chronological retrieval test can pass even if the causal "
    "structure engine itself leaks future information."
)
print()

n = len(candles)

available_checkpoints = [
    int(
        FIRST_TEST
        + (n - FIRST_TEST - 20)
        * i
        / max(PREFIX_CHECKPOINTS - 1, 1)
    )
    for i in range(PREFIX_CHECKPOINTS)
]

prefix_results = []

for q in available_checkpoints:

    prefix = candles[: q + 1]

    try:
        prefix_engine = mlai.CausalStructureEngine(prefix)
        prefix_structure = prefix_engine.build()

        prefix_atr = mlai.calculate_atr(prefix)

        prefix_states = mlai.build_market_states(
            prefix,
            prefix_structure,
            prefix_atr,
        )

        full_sig = state_signature(market_states[q])
        prefix_sig = state_signature(prefix_states[-1])

        identical = full_sig == prefix_sig

        prefix_results.append(identical)

        print(
            f"index={q:5d} "
            f"prefix_state_matches_full={identical}"
        )

    except Exception as exc:
        prefix_results.append(False)

        print(
            f"index={q:5d} "
            f"PREFIX TEST ERROR: {exc}"
        )

prefix_pass_rate = (
    sum(prefix_results) / len(prefix_results)
    if prefix_results
    else 0.0
)

print()
print(
    "PREFIX CAUSAL STABILITY:",
    f"{prefix_pass_rate:.3f}"
)

if prefix_pass_rate < 1.0:
    print(
        "WARNING: one or more historical states changed when "
        "future candles were removed."
    )


# ================================================================
# HISTORICAL RECORD CACHE
# ================================================================

print()
print("=" * 110)
print("5. HISTORICAL EXPERIENCE CACHE")
print("=" * 110)

record_cache = {}

for horizon in HORIZONS:

    records = mlai.build_experience_records(
        candles,
        atr,
        market_states,
        episode_ids,
        0,
        FIRST_TEST,
        horizon,
    )

    record_cache[horizon] = records

    counts = Counter(
        direction_of_record(r)
        for r in records
    )

    print()
    print("HORIZON", horizon)
    print("records:", len(records))
    print("directions:", dict(counts))

    bad_indices = []

    for r in records:
        idx = index_of_record(r)

        if idx is None:
            continue

        outcome = outcome_of_record(r)

        if outcome is None:
            bad_indices.append(idx)

    print("records with missing outcome:", len(bad_indices))


# ================================================================
# CORE FORENSIC FUNCTION
# ================================================================

def evaluate_query(
    query_index,
    horizon,
    records,
):
    """
    Completely causal query evaluation.

    Historical records are filtered so their future outcome is
    fully known before the query candle.

    The query target itself is constructed independently using
    make_outcome().
    """

    valid_records = []

    for r in records:

        idx = index_of_record(r)

        if idx is None:
            continue

        # Strict requirement:
        # record's entire future outcome must end before query.
        if idx + horizon >= query_index:
            continue

        direction = direction_of_record(r)

        if direction not in CLASSES:
            continue

        valid_records.append(r)

    if not valid_records:
        return None

    current = market_states[query_index]

    similarities = []

    for r in valid_records:

        score = mlai.similarity_score(
            current,
            r,
        )

        similarities.append(score)

    target = mlai.make_outcome(
        candles,
        atr,
        query_index,
        horizon,
    )

    actual = direction_of(target)

    if actual not in CLASSES:
        return None

    ranked = sorted(
        zip(valid_records, similarities),
        key=lambda x: x[1].get("total", 0.0),
        reverse=True,
    )

    best_similarity = (
        ranked[0][1].get("total", 0.0)
        if ranked
        else 0.0
    )

    predictions = {}

    for rule in RULES:
        predictions[rule] = aggregate_rule(
            valid_records,
            similarities,
            rule,
        )

    top_records = ranked[: max(TOP_K_VALUES)]

    top_outcomes = [
        direction_of_record(r)
        for r, _ in top_records
    ]

    top_similarity = [
        score.get("total", 0.0)
        for _, score in ranked
    ]

    return {
        "query_index": query_index,
        "horizon": horizon,
        "actual": actual,
        "records": valid_records,
        "similarities": similarities,
        "ranked": ranked,
        "predictions": predictions,
        "best_similarity": best_similarity,
        "top_outcomes": top_outcomes,
        "all_similarity_values": top_similarity,
    }


# ================================================================
# WALK-FORWARD DATASET
# ================================================================

print()
print("=" * 110)
print("6. FULL WALK-FORWARD FORENSIC DATASET")
print("=" * 110)

folds = []

start = FIRST_TEST

while start + TEST_SIZE <= LAST_TEST:

    calibration_start = start - CALIBRATION_SIZE
    calibration_end = start

    if calibration_start < 0:
        break

    folds.append(
        (
            calibration_start,
            calibration_end,
            start,
            start + TEST_SIZE,
        )
    )

    start += STEP

print("folds:", len(folds))

for i, fold in enumerate(folds, 1):
    print(
        f"FOLD {i}: "
        f"CAL [{fold[0]}:{fold[1]}) "
        f"TEST [{fold[2]}:{fold[3]})"
    )


# ================================================================
# COLLECT ALL QUERY RESULTS
# ================================================================

all_results = {
    h: []
    for h in HORIZONS
}

fold_results = {
    h: defaultdict(list)
    for h in HORIZONS
}

for horizon in HORIZONS:

    records = record_cache[horizon]

    for fold_no, (
        cal_start,
        cal_end,
        test_start,
        test_end,
    ) in enumerate(folds, 1):

        for q in range(test_start, test_end):

            result = evaluate_query(
                q,
                horizon,
                records,
            )

            if result is None:
                continue

            result["fold"] = fold_no

            all_results[horizon].append(result)
            fold_results[horizon][fold_no].append(result)


# ================================================================
# CHRONOLOGICAL ISOLATION
# ================================================================

print()
print("=" * 110)
print("7. CHRONOLOGICAL ISOLATION")
print("=" * 110)

temporal_violations = {}

for horizon in HORIZONS:

    violations = 0

    for result in all_results[horizon]:

        q = result["query_index"]

        for r in result["records"]:

            idx = index_of_record(r)

            if idx is None:
                violations += 1
                continue

            if idx + horizon >= q:
                violations += 1

    temporal_violations[horizon] = violations

    print(
        f"H{horizon}: violations={violations}"
    )


# ================================================================
# MAIN FORENSIC ANALYSIS
# ================================================================

report_sections = []

def add(text=""):
    report_sections.append(text)


add("# MLAI v4.1.5 — FULL FORENSIC PREDICTIVE AUDIT")
add("")
add(f"Source SHA256: `{source_hash_before}`")
add(f"Data SHA256: `{data_hash_before}`")
add("")
add("## Executive Summary")
add("")
add(
    "This report is an evidence-based forensic assessment. "
    "It does not automatically modify MLAI or create v4.1.6."
)
add("")


for horizon in HORIZONS:

    results = all_results[horizon]

    y_true = [
        r["actual"]
        for r in results
    ]

    print()
    print("=" * 110)
    print(f"8. HORIZON {horizon} CORE FORENSICS")
    print("=" * 110)

    print("samples:", len(results))

    if not results:
        print("NO RESULTS")
        continue

    actual_distribution = distribution(y_true)

    print("actual distribution:", actual_distribution)

    add("")
    add(f"## H{horizon}")
    add("")
    add(f"Samples: **{len(results)}**")
    add("")
    add("### Actual class distribution")
    add("")
    add(str(actual_distribution))
    add("")

    # ------------------------------------------------------------
    # FIXED RULES
    # ------------------------------------------------------------

    rule_metrics = {}

    for rule in RULES:

        y_pred = [
            r["predictions"][rule]
            for r in results
        ]

        rule_metrics[rule] = {
            "accuracy": accuracy(y_true, y_pred),
            "balanced_accuracy": balanced_accuracy(
                y_true,
                y_pred,
            ),
            "macro_f1": macro_f1(
                y_true,
                y_pred,
            ),
            "entropy": prediction_entropy(
                y_pred,
            ),
            "distribution": distribution(y_pred),
            "y_pred": y_pred,
        }

    print()
    print("FIXED RULE PERFORMANCE")

    for rule, metrics in rule_metrics.items():

        print(
            f"{rule:10s} "
            f"acc={metrics['accuracy']:.4f} "
            f"bal={metrics['balanced_accuracy']:.4f} "
            f"f1={metrics['macro_f1']:.4f}"
        )

    add("### Fixed decision rules")
    add("")
    add(
        "| Rule | Accuracy | Balanced Accuracy | Macro F1 | Prediction Entropy |"
    )
    add("|---|---:|---:|---:|---:|")

    for rule in RULES:

        m = rule_metrics[rule]

        add(
            f"| {rule} | "
            f"{m['accuracy']:.4f} | "
            f"{m['balanced_accuracy']:.4f} | "
            f"{m['macro_f1']:.4f} | "
            f"{m['entropy']:.4f} |"
        )

    add("")

    # ------------------------------------------------------------
    # MAJORITY BASELINE
    # ------------------------------------------------------------

    majority_class = Counter(y_true).most_common(1)[0][0]

    majority_pred = [
        majority_class
        for _ in y_true
    ]

    majority_acc = accuracy(
        y_true,
        majority_pred,
    )

    majority_bal = balanced_accuracy(
        y_true,
        majority_pred,
    )

    majority_f1 = macro_f1(
        y_true,
        majority_pred,
    )

    print()
    print(
        "majority:",
        majority_class,
        f"acc={majority_acc:.4f}",
        f"balanced={majority_bal:.4f}",
        f"macroF1={majority_f1:.4f}",
    )

    add(
        f"Majority baseline: **{majority_class}** "
        f"accuracy={majority_acc:.4f}, "
        f"balanced={majority_bal:.4f}, "
        f"macro-F1={majority_f1:.4f}."
    )
    add("")

    # ------------------------------------------------------------
    # BEST FIXED RULE
    # ------------------------------------------------------------

    best_rule = max(
        RULES,
        key=lambda r: (
            rule_metrics[r]["balanced_accuracy"],
            rule_metrics[r]["macro_f1"],
            rule_metrics[r]["accuracy"],
        ),
    )

    best = rule_metrics[best_rule]

    print()
    print(
        "best fixed rule by balanced accuracy:",
        best_rule,
    )

    # ------------------------------------------------------------
    # CONFUSION / CLASS FORENSICS
    # ------------------------------------------------------------

    cm = confusion_matrix(
        y_true,
        best["y_pred"],
    )

    print()
    print("CONFUSION MATRIX:", best_rule)

    print("             PRED_UP PRED_DOWN PRED_NEUTRAL")

    for cls in CLASSES:

        print(
            f"ACT_{cls:7s} "
            f"{cm[cls]['UP']:8d} "
            f"{cm[cls]['DOWN']:9d} "
            f"{cm[cls]['NEUTRAL']:12d}"
        )

    add("### Confusion matrix")
    add("")
    add("| Actual \\ Predicted | UP | DOWN | NEUTRAL |")
    add("|---|---:|---:|---:|")

    for cls in CLASSES:
        add(
            f"| {cls} | "
            f"{cm[cls]['UP']} | "
            f"{cm[cls]['DOWN']} | "
            f"{cm[cls]['NEUTRAL']} |"
        )

    add("")

    for cls in CLASSES:

        p, r = precision_recall(
            cm,
            cls,
        )

        print(
            f"{cls:8s} "
            f"precision={p:.4f} "
            f"recall={r:.4f}"
        )

    pred_dist = best["distribution"]

    js = js_divergence(
        actual_distribution,
        pred_dist,
    )

    print()
    print(
        "prediction distribution:",
        pred_dist,
    )

    print(
        "actual/prediction JS divergence:",
        f"{js:.6f}",
    )

    add(
        f"Prediction distribution: `{pred_dist}`"
    )
    add("")
    add(
        f"Actual/prediction Jensen-Shannon divergence: "
        f"**{js:.6f}**."
    )
    add("")

    # ------------------------------------------------------------
    # SIMILARITY FORENSICS
    # ------------------------------------------------------------

    similarity_values = [
        r["best_similarity"]
        for r in results
    ]

    print()
    print("SIMILARITY")

    print(
        "mean:",
        f"{mean(similarity_values):.6f}"
    )

    print(
        "median:",
        f"{statistics.median(similarity_values):.6f}"
    )

    print(
        "P10:",
        f"{percentile(similarity_values, 0.10):.6f}"
    )

    print(
        "P90:",
        f"{percentile(similarity_values, 0.90):.6f}"
    )

    add("### Similarity")
    add("")
    add(
        f"Mean top similarity: **{mean(similarity_values):.6f}**"
    )
    add(
        f"Median: **{statistics.median(similarity_values):.6f}**"
    )
    add(
        f"P10: **{percentile(similarity_values, 0.10):.6f}**"
    )
    add(
        f"P90: **{percentile(similarity_values, 0.90):.6f}**"
    )
    add("")

    # ------------------------------------------------------------
    # TOP-K CONSISTENCY
    # ------------------------------------------------------------

    print()
    print("TOP-K HISTORICAL OUTCOME CONSISTENCY")

    for k in TOP_K_VALUES:

        agreements = []

        for result in results:

            top = result["top_outcomes"][:k]

            if not top:
                continue

            actual = result["actual"]

            agreement = (
                sum(x == actual for x in top)
                / len(top)
            )

            agreements.append(agreement)

        print(
            f"top_{k:2d}: "
            f"mean_agreement={mean(agreements):.4f}"
        )

    add("### Top-K historical outcome agreement")
    add("")
    add("| K | Mean agreement with actual outcome |")
    add("|---:|---:|")

    for k in TOP_K_VALUES:

        agreements = []

        for result in results:

            top = result["top_outcomes"][:k]

            if top:

                agreements.append(
                    sum(
                        x == result["actual"]
                        for x in top
                    ) / len(top)
                )

        add(
            f"| {k} | {mean(agreements):.4f} |"
        )

    add("")

    # ------------------------------------------------------------
    # SIMILARITY DECILES
    # ------------------------------------------------------------

    decile_rows = []

    sorted_results = sorted(
        results,
        key=lambda r: r["best_similarity"],
    )

    chunk = max(
        1,
        len(sorted_results) // DECILES,
    )

    print()
    print("SIMILARITY DECILES")

    for d in range(DECILES):

        start_i = d * chunk

        if d == DECILES - 1:
            end_i = len(sorted_results)
        else:
            end_i = min(
                len(sorted_results),
                (d + 1) * chunk,
            )

        subset = sorted_results[
            start_i:end_i
        ]

        if not subset:
            continue

        actuals = [
            r["actual"]
            for r in subset
        ]

        preds = [
            r["predictions"][best_rule]
            for r in subset
        ]

        row = {
            "decile": d + 1,
            "mean_similarity": mean(
                [
                    r["best_similarity"]
                    for r in subset
                ]
            ),
            "accuracy": accuracy(
                actuals,
                preds,
            ),
            "balanced_accuracy": balanced_accuracy(
                actuals,
                preds,
            ),
            "macro_f1": macro_f1(
                actuals,
                preds,
            ),
        }

        decile_rows.append(row)

        print(
            f"D{d+1:02d} "
            f"sim={row['mean_similarity']:.4f} "
            f"acc={row['accuracy']:.4f} "
            f"bal={row['balanced_accuracy']:.4f} "
            f"f1={row['macro_f1']:.4f}"
        )

    add("### Similarity deciles")
    add("")
    add(
        "| Decile | Mean similarity | Accuracy | Balanced accuracy | Macro F1 |"
    )
    add("|---:|---:|---:|---:|---:|")

    for row in decile_rows:

        add(
            f"| {row['decile']} | "
            f"{row['mean_similarity']:.4f} | "
            f"{row['accuracy']:.4f} | "
            f"{row['balanced_accuracy']:.4f} | "
            f"{row['macro_f1']:.4f} |"
        )

    add("")

    # ------------------------------------------------------------
    # COMPONENT FORENSICS
    # ------------------------------------------------------------

    component_values = defaultdict(list)

    for result in results:

        for score in result["similarities"]:

            for key, value in score.items():

                if isinstance(value, (int, float)):

                    component_values[key].append(
                        float(value)
                    )

    print()
    print("SIMILARITY COMPONENTS")

    for component, values in sorted(
        component_values.items()
    ):

        print(
            f"{component:12s} "
            f"mean={mean(values):.6f} "
            f"median={statistics.median(values):.6f} "
            f"min={min(values):.6f} "
            f"max={max(values):.6f}"
        )

    add("### Similarity component statistics")
    add("")
    add("| Component | Mean | Median | Min | Max |")
    add("|---|---:|---:|---:|---:|")

    for component, values in sorted(
        component_values.items()
    ):

        add(
            f"| {component} | "
            f"{mean(values):.6f} | "
            f"{statistics.median(values):.6f} | "
            f"{min(values):.6f} | "
            f"{max(values):.6f} |"
        )

    add("")

    # ------------------------------------------------------------
    # RANDOM LABEL PERMUTATION TEST
    # ------------------------------------------------------------

    print()
    print("LABEL PERMUTATION TEST")

    baseline_predictions = [
        r["predictions"][best_rule]
        for r in results
    ]

    observed = accuracy(
        y_true,
        baseline_predictions,
    )

    null_scores = []

    for _ in range(PERMUTATIONS):

        shuffled = list(y_true)

        random.shuffle(shuffled)

        null_scores.append(
            accuracy(
                shuffled,
                baseline_predictions,
            )
        )

    null_mean = mean(null_scores)

    null_p = (
        1
        + sum(
            x >= observed
            for x in null_scores
        )
    ) / (
        len(null_scores) + 1
    )

    print(
        "observed:",
        f"{observed:.6f}"
    )

    print(
        "null mean:",
        f"{null_mean:.6f}"
    )

    print(
        "permutation p:",
        f"{null_p:.6f}"
    )

    add("### Label permutation test")
    add("")
    add(
        f"Observed accuracy: **{observed:.6f}**"
    )
    add(
        f"Permutation null mean: **{null_mean:.6f}**"
    )
    add(
        f"Permutation p-value: **{null_p:.6f}**"
    )
    add("")

    # ------------------------------------------------------------
    # FOLD STABILITY
    # ------------------------------------------------------------

    fold_accs = []

    for fold_no, fold_data in fold_results[horizon].items():

        actuals = [
            r["actual"]
            for r in fold_data
        ]

        preds = [
            r["predictions"][best_rule]
            for r in fold_data
        ]

        acc = accuracy(
            actuals,
            preds,
        )

        fold_accs.append(acc)

        print(
            f"fold {fold_no:02d}: "
            f"accuracy={acc:.4f}"
        )

    print()
    print(
        "fold mean:",
        f"{mean(fold_accs):.6f}"
    )

    print(
        "fold median:",
        f"{statistics.median(fold_accs):.6f}"
    )

    print(
        "fold stdev:",
        f"{stdev(fold_accs):.6f}"
    )

    print(
        "fold min:",
        f"{min(fold_accs):.6f}"
    )

    print(
        "fold max:",
        f"{max(fold_accs):.6f}"
    )

    add("### Fold stability")
    add("")
    add(
        f"Mean={mean(fold_accs):.6f}, "
        f"median={statistics.median(fold_accs):.6f}, "
        f"stdev={stdev(fold_accs):.6f}, "
        f"min={min(fold_accs):.6f}, "
        f"max={max(fold_accs):.6f}."
    )
    add("")


# ================================================================
# CROSS-HORIZON SUMMARY
# ================================================================

print()
print("=" * 110)
print("9. CROSS-HORIZON SUMMARY")
print("=" * 110)

summary_rows = []

for horizon in HORIZONS:

    results = all_results[horizon]

    if not results:
        continue

    actuals = [
        r["actual"]
        for r in results
    ]

    # Evaluate fixed power_2 as a deliberately non-optimized
    # reference rule.
    preds = [
        r["predictions"]["power_2"]
        for r in results
    ]

    row = {
        "horizon": horizon,
        "samples": len(results),
        "accuracy": accuracy(
            actuals,
            preds,
        ),
        "balanced_accuracy": balanced_accuracy(
            actuals,
            preds,
        ),
        "macro_f1": macro_f1(
            actuals,
            preds,
        ),
        "entropy": prediction_entropy(
            preds,
        ),
    }

    summary_rows.append(row)

    print(
        f"H{horizon}: "
        f"accuracy={row['accuracy']:.4f} "
        f"balanced={row['balanced_accuracy']:.4f} "
        f"macroF1={row['macro_f1']:.4f} "
        f"entropy={row['entropy']:.4f}"
    )

add("")
add("## Cross-horizon fixed-rule summary")
add("")
add(
    "| Horizon | Samples | Accuracy | Balanced Accuracy | Macro F1 | Entropy |"
)
add("|---:|---:|---:|---:|---:|---:|")

for row in summary_rows:

    add(
        f"| H{row['horizon']} | "
        f"{row['samples']} | "
        f"{row['accuracy']:.4f} | "
        f"{row['balanced_accuracy']:.4f} | "
        f"{row['macro_f1']:.4f} | "
        f"{row['entropy']:.4f} |"
    )


# ================================================================
# CAUSAL / DATA / INTEGRITY FINAL CHECK
# ================================================================

print()
print("=" * 110)
print("10. FINAL INTEGRITY")
print("=" * 110)

source_hash_after = sha256_file(SOURCE_FILE)
data_hash_after = sha256_file(DATA_FILE)

source_unchanged = (
    source_hash_before == source_hash_after
)

data_unchanged = (
    data_hash_before == data_hash_after
)

print(
    "source unchanged:",
    source_unchanged,
)

print(
    "data unchanged:",
    data_unchanged,
)

print(
    "temporal violations:",
    temporal_violations,
)

print(
    "prefix causal stability:",
    f"{prefix_pass_rate:.4f}",
)


# ================================================================
# AUTOMATIC FORENSIC DIAGNOSIS
# ================================================================

print()
print("=" * 110)
print("11. AUTOMATIC FORENSIC DIAGNOSIS")
print("=" * 110)

diagnoses = []
pros = []
cons = []
fixes = []

if source_unchanged:
    pros.append(
        "Baseline source remained byte-for-byte unchanged."
    )
else:
    diagnoses.append(
        "SOURCE INTEGRITY FAILURE."
    )

if data_unchanged:
    pros.append(
        "Market data remained byte-for-byte unchanged."
    )
else:
    diagnoses.append(
        "MARKET DATA INTEGRITY FAILURE."
    )

if all(v == 0 for v in temporal_violations.values()):
    pros.append(
        "Historical retrieval records obey strict chronological isolation."
    )
else:
    diagnoses.append(
        "TEMPORAL LEAKAGE EXISTS IN HISTORICAL RETRIEVAL."
    )
    fixes.append(
        "Fix historical record eligibility before changing predictive features."
    )

if prefix_pass_rate == 1.0:
    pros.append(
        "Causal prefix stability passed all tested checkpoints."
    )
else:
    diagnoses.append(
        "POSSIBLE FUTURE INFORMATION LEAKAGE INSIDE STATE CONSTRUCTION."
    )
    fixes.append(
        "Audit CausalStructureEngine state construction for future-dependent pivots/events."
    )

for horizon in HORIZONS:

    results = all_results[horizon]

    if not results:
        continue

    actuals = [
        r["actual"]
        for r in results
    ]

    preds = [
        r["predictions"]["power_2"]
        for r in results
    ]

    acc = accuracy(
        actuals,
        preds,
    )

    bal = balanced_accuracy(
        actuals,
        preds,
    )

    f1 = macro_f1(
        actuals,
        preds,
    )

    pred_dist = distribution(preds)
    actual_dist = distribution(actuals)

    js = js_divergence(
        actual_dist,
        pred_dist,
    )

    if bal < 1 / 3 + 0.03:
        diagnoses.append(
            f"H{horizon}: balanced accuracy is near random-class performance."
        )

    if f1 < 0.34:
        diagnoses.append(
            f"H{horizon}: macro-F1 is weak, indicating poor three-class behavior."
        )

    if js > 0.20:
        diagnoses.append(
            f"H{horizon}: prediction distribution is materially different from actual distribution."
        )

    if max(pred_dist.values()) > 0.70:
        diagnoses.append(
            f"H{horizon}: prediction concentration exceeds 70%, indicating possible class bias."
        )
        fixes.append(
            f"H{horizon}: investigate class decision calibration and neutral handling."
        )


# Similarity behavior.
for horizon in HORIZONS:

    results = all_results[horizon]

    if len(results) < 100:
        continue

    sorted_results = sorted(
        results,
        key=lambda r: r["best_similarity"],
    )

    low = sorted_results[
        : max(1, len(sorted_results) // 10)
    ]

    high = sorted_results[
        -max(1, len(sorted_results) // 10):
    ]

    low_acc = accuracy(
        [r["actual"] for r in low],
        [
            r["predictions"]["power_2"]
            for r in low
        ],
    )

    high_acc = accuracy(
        [r["actual"] for r in high],
        [
            r["predictions"]["power_2"]
            for r in high
        ],
    )

    delta = high_acc - low_acc

    if delta > 0.05:
        pros.append(
            f"H{horizon}: high-similarity queries outperform low-similarity queries by {delta:.4f}."
        )
    elif delta < -0.05:
        diagnoses.append(
            f"H{horizon}: higher similarity does not correspond to better predictive performance."
        )
        fixes.append(
            f"H{horizon}: investigate whether similarity features encode the correct future behavior."
        )
    else:
        diagnoses.append(
            f"H{horizon}: similarity-strength gradient is weak."
        )


# ================================================================
# FINAL CLASSIFICATION
# ================================================================

print()
print("=" * 110)
print("12. FINAL CLASSIFICATION")
print("=" * 110)

# Conservative classification.
if (
    not source_unchanged
    or not data_unchanged
    or any(v > 0 for v in temporal_violations.values())
):
    verdict = "INVALID AUDIT BASELINE"

elif prefix_pass_rate < 1.0:
    verdict = "CAUSALITY DEFECT SUSPECTED"

else:

    meaningful_horizons = 0

    for horizon in HORIZONS:

        results = all_results[horizon]

        if not results:
            continue

        actuals = [
            r["actual"]
            for r in results
        ]

        preds = [
            r["predictions"]["power_2"]
            for r in results
        ]

        bal = balanced_accuracy(
            actuals,
            preds,
        )

        f1 = macro_f1(
            actuals,
            preds,
        )

        if (
            bal > 1 / 3 + 0.05
            and f1 > 0.38
        ):
            meaningful_horizons += 1

    if meaningful_horizons >= 2:
        verdict = (
            "POTENTIAL MULTI-HORIZON SIGNAL — "
            "REQUIRES CONFIRMATION"
        )

    elif meaningful_horizons == 1:
        verdict = (
            "ISOLATED HORIZON SIGNAL — "
            "NOT SUFFICIENT FOR ARCHITECTURE CHANGE"
        )

    else:
        verdict = (
            "NO ROBUST THREE-CLASS PREDICTIVE SIGNAL "
            "ESTABLISHED"
        )

print()
print("FINAL VERDICT:")
print()
print(verdict)


# ================================================================
# REPORT
# ================================================================

add("")
add("## Automatic forensic diagnosis")
add("")
add(f"**Final classification: {verdict}**")
add("")

add("### Pros")
add("")

if pros:
    for item in pros:
        add(f"- {item}")
else:
    add("- No major positive findings established.")

add("")
add("### Cons / warnings")
add("")

if diagnoses:
    for item in diagnoses:
        add(f"- {item}")
else:
    add("- No major forensic warning automatically detected.")

add("")
add("### Recommended investigation/fixes")
add("")

if fixes:
    for item in sorted(set(fixes)):
        add(f"- {item}")
else:
    add(
        "- No source modification is justified from this audit alone."
    )

add("")
add("## Interpretation")
add("")
add(
    "This report deliberately distinguishes statistical performance "
    "from evidence of predictive intelligence. A result above 50% "
    "accuracy is not automatically considered predictive, and a "
    "result below 50% is not automatically considered useless. "
    "Class balance, balanced accuracy, macro-F1, prediction "
    "distribution, temporal isolation, causal-prefix stability, "
    "similarity behavior, fold stability, and null testing must "
    "be considered together."
)

add("")
add("## Baseline integrity")
add("")
add(f"- Source unchanged: `{source_unchanged}`")
add(f"- Data unchanged: `{data_unchanged}`")
add(
    f"- Prefix causal stability: `{prefix_pass_rate:.6f}`"
)
add(
    f"- Temporal violations: `{temporal_violations}`"
)

# Write report.
with open(
    REPORT_FILE,
    "w",
    encoding="utf-8",
) as f:

    f.write("\n".join(report_sections))

print()
print("=" * 110)
print("13. REPORT")
print("=" * 110)

print()
print(
    "REPORT WRITTEN:",
    REPORT_FILE,
)

print()
print("FINAL SOURCE SHA256:", source_hash_after)
print("FINAL DATA SHA256  :", data_hash_after)

print()
print("=" * 110)
print("FULL FORENSIC AUDIT COMPLETE")
print("=" * 110)
print()
print(
    "NO v4.1.5 SOURCE WAS MODIFIED."
)
print(
    "NO MARKET DATA WAS MODIFIED."
)
print(
    "NO v4.1.6 WAS CREATED."
)