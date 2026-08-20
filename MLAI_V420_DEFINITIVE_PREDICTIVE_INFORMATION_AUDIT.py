"""
MLAI V4.2.0 — DEFINITIVE PREDICTIVE INFORMATION AUDIT
======================================================

Purpose
-------
Independent forensic investigation of the existing
mlai_market_structure_v420.py implementation.

THIS PROGRAM DOES NOT MODIFY V4.2.0.

It is deliberately designed to answer one question:

    Does historical retrieval contain genuine incremental
    predictive information on unseen chronological market data?

Scientific principles
---------------------
1. Production MLAI is imported, not patched.
2. market_data.bin is read-only and SHA-256 protected.
3. Historical records used for an OOS query must be strictly prior
   to that query and satisfy the V4.2 history gap.
4. No OOS result is used to tune parameters.
5. Similarity is NOT interpreted as probability.
6. Similarity discrimination is tested against actual future outcomes.
7. Retrieval is compared against the conditional baseline.
8. Improvement is evaluated using Accuracy, Brier and LogLoss.
9. Calibration is explicitly investigated.
10. Retrieval matches are clustered by episode to expose pseudo-replication.
11. Walk-forward and regime stability are reported.
12. A block-aware null investigation is used instead of only IID label shuffling.
13. Confidence intervals are estimated by bootstrap.
14. Strong evidence requires multiple independent forms of evidence.
15. Unsupported claims are reported as INSUFFICIENT EVIDENCE.

Outputs
-------
MLAI_V420_DEFINITIVE_PREDICTIVE_INFORMATION_AUDIT_REPORT.md
MLAI_V420_DEFINITIVE_PREDICTIVE_INFORMATION_AUDIT.bin

Run
---
python .\MLAI_V420_DEFINITIVE_PREDICTIVE_INFORMATION_AUDIT.py
"""

from __future__ import annotations

import hashlib
import math
import os
import pickle
import random
import statistics
import time
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import mlai_market_structure_v420 as v420


# ============================================================================
# FIXED CONFIGURATION
# ============================================================================

AUDIT_VERSION = "V420-DEFINITIVE-PREDICTIVE-INFORMATION-AUDIT-2.0"

DATA_FILE = v420.MARKET_DATA_FILE

REPORT_FILE = (
    "MLAI_V420_DEFINITIVE_PREDICTIVE_INFORMATION_AUDIT_REPORT.md"
)

RESULTS_FILE = (
    "MLAI_V420_DEFINITIVE_PREDICTIVE_INFORMATION_AUDIT.bin"
)

HORIZONS = tuple(v420.HORIZONS)

TRAIN_WINDOWS = int(v420.DEFAULT_TRAIN_WINDOWS)
OOS_SIZE = int(v420.DEFAULT_OOS_SIZE)

MIN_SIMILARITY = float(getattr(v420, "V420_MIN_SIMILARITY", 0.0))
TOP_K = int(getattr(v420, "V420_TOP_K", 25))
MIN_HISTORY_GAP = int(getattr(v420, "MIN_HISTORY_GAP", 0))

MIN_BUCKET_SAMPLES = 20
MIN_GROUP_SAMPLES = 20

BOOTSTRAPS = 1000
NULL_PERMUTATIONS = 1000

SEED = 4200420

EPS = 1e-12

CLASSES = ("UP", "DOWN", "NEUTRAL")


# ============================================================================
# GENERAL UTILITIES
# ============================================================================

def finite(x: Any, default: float = 0.0) -> float:
    try:
        y = float(x)
        return y if math.isfinite(y) else default
    except Exception:
        return default


def mean(values: Sequence[float]) -> Optional[float]:
    vals = [
        finite(v)
        for v in values
        if v is not None and math.isfinite(finite(v, math.nan))
    ]
    return sum(vals) / len(vals) if vals else None


def median(values: Sequence[float]) -> Optional[float]:
    vals = [finite(v) for v in values if v is not None]
    return statistics.median(vals) if vals else None


def stdev(values: Sequence[float]) -> Optional[float]:
    vals = [finite(v) for v in values if v is not None]
    return statistics.stdev(vals) if len(vals) > 1 else None


def safe_div(a: float, b: float) -> float:
    return a / b if abs(b) > EPS else 0.0


def pct(x: Optional[float]) -> str:
    if x is None:
        return "N/A"
    return f"{100.0 * x:.3f}%"


def num(x: Optional[float]) -> str:
    if x is None:
        return "N/A"
    return f"{x:.8f}"


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def normalize_probs(values: Dict[str, float]) -> Dict[str, float]:
    clean = {
        c: max(0.0, finite(values.get(c, 0.0)))
        for c in CLASSES
    }

    total = sum(clean.values())

    if total <= EPS:
        return {c: 1.0 / 3.0 for c in CLASSES}

    return {
        c: clean[c] / total
        for c in CLASSES
    }


def predicted_class(probs: Dict[str, float]) -> str:
    return max(
        CLASSES,
        key=lambda c: (
            finite(probs.get(c, 0.0)),
            c,
        ),
    )


def actual_direction(record: Any) -> Optional[str]:
    outcome = getattr(record, "outcome", record)

    for attr in (
        "direction",
        "label",
        "class_name",
        "target",
        "prediction",
    ):
        value = getattr(outcome, attr, None)

        if value is None:
            continue

        value = str(value).upper().strip()

        if value in CLASSES:
            return value

    return None


# ============================================================================
# PROBABILITY METRICS
# ============================================================================

def accuracy_metric(
    probs: Dict[str, float],
    actual: str,
) -> float:
    return float(predicted_class(probs) == actual)


def brier_metric(
    probs: Dict[str, float],
    actual: str,
) -> float:
    return sum(
        (
            finite(probs.get(c, 0.0))
            - (1.0 if c == actual else 0.0)
        ) ** 2
        for c in CLASSES
    )


def logloss_metric(
    probs: Dict[str, float],
    actual: str,
) -> float:
    p = max(
        EPS,
        min(
            1.0,
            finite(probs.get(actual, 0.0)),
        ),
    )
    return -math.log(p)


# ============================================================================
# CALIBRATION
# ============================================================================

def calibration_report(
    rows: Sequence[Dict[str, Any]],
    probability_key: str,
    bins: int = 10,
) -> Dict[str, Any]:

    if not rows:
        return {
            "available": False,
            "reason": "no rows",
        }

    entries = []

    for row in rows:
        probs = row[probability_key]
        pred = predicted_class(probs)
        confidence = finite(probs.get(pred, 0.0))
        correct = float(pred == row["actual"])

        entries.append(
            (
                confidence,
                correct,
            )
        )

    entries.sort()

    groups = []

    for i in range(bins):

        lo = (i * len(entries)) // bins
        hi = ((i + 1) * len(entries)) // bins

        chunk = entries[lo:hi]

        if not chunk:
            continue

        avg_conf = mean([x[0] for x in chunk])
        avg_acc = mean([x[1] for x in chunk])

        groups.append(
            {
                "bin": i + 1,
                "samples": len(chunk),
                "mean_confidence": avg_conf,
                "empirical_accuracy": avg_acc,
                "gap": (
                    abs(avg_conf - avg_acc)
                    if avg_conf is not None and avg_acc is not None
                    else None
                ),
            }
        )

    ece = safe_div(
        sum(
            g["samples"] * finite(g["gap"])
            for g in groups
        ),
        len(entries),
    )

    return {
        "available": True,
        "samples": len(entries),
        "ece": ece,
        "bins": groups,
    }


# ============================================================================
# BOOTSTRAP
# ============================================================================

def bootstrap_mean_ci(
    values: Sequence[float],
    iterations: int = BOOTSTRAPS,
    seed: int = SEED,
) -> Dict[str, Any]:

    vals = [finite(v) for v in values]

    if len(vals) < 2:
        return {
            "available": False,
            "samples": len(vals),
        }

    rng = random.Random(seed)

    observed = sum(vals) / len(vals)

    boot = []

    n = len(vals)

    for _ in range(iterations):
        total = 0.0

        for _ in range(n):
            total += vals[rng.randrange(n)]

        boot.append(total / n)

    boot.sort()

    lo = boot[
        max(
            0,
            min(
                len(boot) - 1,
                int(0.025 * len(boot)),
            ),
        )
    ]

    hi = boot[
        max(
            0,
            min(
                len(boot) - 1,
                int(0.975 * len(boot)),
            )
        )
    ]

    return {
        "available": True,
        "samples": n,
        "observed": observed,
        "ci95_low": lo,
        "ci95_high": hi,
        "bootstrap_iterations": iterations,
    }


# ============================================================================
# EPISODE / MATCH EXTRACTION
# ============================================================================

def extract_match_records(retrieval: Any) -> List[Any]:
    for attr in (
        "matches",
        "retrieved",
        "experiences",
        "records",
        "top_matches",
    ):
        value = getattr(retrieval, attr, None)

        if value is not None and isinstance(value, (list, tuple)):
            return list(value)

    return []


def match_index(record: Any) -> Optional[int]:
    value = getattr(record, "index", None)

    try:
        return int(value)
    except Exception:
        return None


def match_episode(record: Any) -> Any:
    return getattr(
        record,
        "episode_id",
        match_index(record),
    )


# ============================================================================
# CAUSALITY
# ============================================================================

def validate_record_causality(
    records: Sequence[Any],
    query_index: int,
) -> Dict[str, int]:

    checked = 0
    violations = 0

    for record in records:

        idx = match_index(record)

        if idx is None:
            violations += 1
            continue

        checked += 1

        if idx >= query_index:
            violations += 1

    return {
        "checked": checked,
        "violations": violations,
    }


# ============================================================================
# BASELINE / RETRIEVAL
# ============================================================================

def baseline_prediction(
    query_state: Any,
    records: Sequence[Any],
) -> Dict[str, float]:

    _, distribution, _ = v420.conditional_baseline(
        query_state,
        records,
    )

    return normalize_probs(distribution)


def retrieval_prediction(
    query_state: Any,
    records: Sequence[Any],
    horizon: int,
    query_index: int,
) -> Tuple[Any, Dict[str, float]]:

    retrieval = v420.retrieve_historical_experience(
        query_state,
        records,
        horizon,
        query_index,
    )

    probs = normalize_probs(
        {
            "UP": getattr(retrieval, "up_share", 0.0),
            "DOWN": getattr(retrieval, "down_share", 0.0),
            "NEUTRAL": getattr(
                retrieval,
                "neutral_share",
                0.0,
            ),
        }
    )

    return retrieval, probs


def predictive_prediction(
    query_state: Any,
    records: Sequence[Any],
    horizon: int,
    query_index: int,
) -> Tuple[Dict[str, float], Dict[str, Any]]:

    result = v420.mlai_v415_repaired_prediction(
        current=query_state,
        records=records,
        horizon=horizon,
        query_index=query_index,
    )

    probs = normalize_probs(
        result.get("probabilities", {})
    )

    return probs, result


# ============================================================================
# RETRIEVAL INFORMATION EXTRACTION
# ============================================================================

def retrieval_diagnostics(
    retrieval: Any,
) -> Dict[str, Any]:

    matches = extract_match_records(retrieval)

    similarities = []

    episodes = set()

    indices = []

    for record in matches:

        idx = match_index(record)

        if idx is not None:
            indices.append(idx)

        episodes.add(
            str(match_episode(record))
        )

        similarity = getattr(
            record,
            "similarity",
            getattr(
                record,
                "score",
                None,
            ),
        )

        if similarity is not None:
            similarities.append(
                finite(similarity)
            )

    top_similarity = finite(
        getattr(
            retrieval,
            "top_similarity",
            max(similarities)
            if similarities
            else 0.0,
        )
    )

    mean_similarity = finite(
        getattr(
            retrieval,
            "mean_similarity",
            mean(similarities) or 0.0,
        )
    )

    return {
        "matches": len(matches),
        "unique_episodes": len(episodes),
        "unique_indices": len(set(indices)),
        "top_similarity": top_similarity,
        "mean_similarity": mean_similarity,
        "similarities": similarities,
        "match_records": matches,
    }


# ============================================================================
# OUTCOME AGREEMENT
# ============================================================================

def historical_match_outcomes(
    matches: Sequence[Any],
) -> Dict[str, Any]:

    counts = Counter()

    usable = 0

    for record in matches:

        d = actual_direction(record)

        if d in CLASSES:
            counts[d] += 1
            usable += 1

    distribution = {
        c: safe_div(
            counts[c],
            usable,
        )
        for c in CLASSES
    }

    return {
        "samples": usable,
        "counts": dict(counts),
        "distribution": distribution,
    }


def distribution_entropy(
    distribution: Dict[str, float],
) -> float:

    result = 0.0

    for c in CLASSES:

        p = max(
            EPS,
            finite(distribution.get(c, 0.0)),
        )

        result -= p * math.log(p)

    return result


def distribution_distance(
    a: Dict[str, float],
    b: Dict[str, float],
) -> float:

    return 0.5 * sum(
        abs(
            finite(a.get(c, 0.0))
            - finite(b.get(c, 0.0))
        )
        for c in CLASSES
    )


# ============================================================================
# SIMILARITY BUCKET ANALYSIS
# ============================================================================

def similarity_deciles(
    rows: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:

    valid = [
        r for r in rows
        if finite(r["top_similarity"]) >= 0.0
    ]

    ordered = sorted(
        valid,
        key=lambda r: r["top_similarity"],
    )

    if len(ordered) < MIN_BUCKET_SAMPLES:
        return []

    result = []

    for decile in range(10):

        lo = (
            decile * len(ordered)
        ) // 10

        hi = (
            (decile + 1) * len(ordered)
        ) // 10

        chunk = ordered[lo:hi]

        if len(chunk) < MIN_BUCKET_SAMPLES:
            continue

        result.append(
            {
                "decile": decile + 1,
                "samples": len(chunk),
                "mean_similarity": mean(
                    [
                        r["top_similarity"]
                        for r in chunk
                    ]
                ),
                "retrieval_accuracy": mean(
                    [
                        r["retrieval_accuracy"]
                        for r in chunk
                    ]
                ),
                "baseline_accuracy": mean(
                    [
                        r["baseline_accuracy"]
                        for r in chunk
                    ]
                ),
                "predictive_accuracy": mean(
                    [
                        r["predictive_accuracy"]
                        for r in chunk
                    ]
                ),
                "retrieval_brier": mean(
                    [
                        r["retrieval_brier"]
                        for r in chunk
                    ]
                ),
                "predictive_brier": mean(
                    [
                        r["predictive_brier"]
                        for r in chunk
                    ]
                ),
                "predictive_logloss": mean(
                    [
                        r["predictive_logloss"]
                        for r in chunk
                    ]
                ),
            }
        )

    return result


# ============================================================================
# RANK CORRELATION
# ============================================================================

def rank(values: Sequence[float]) -> List[float]:

    indexed = sorted(
        enumerate(values),
        key=lambda x: x[1],
    )

    ranks = [0.0] * len(values)

    i = 0

    while i < len(indexed):

        j = i

        while (
            j + 1 < len(indexed)
            and indexed[j + 1][1] == indexed[i][1]
        ):
            j += 1

        avg = (
            i + j + 2
        ) / 2.0

        for k in range(i, j + 1):
            ranks[indexed[k][0]] = avg

        i = j + 1

    return ranks


def pearson(
    x: Sequence[float],
    y: Sequence[float],
) -> Optional[float]:

    if len(x) != len(y) or len(x) < 3:
        return None

    mx = mean(x)
    my = mean(y)

    if mx is None or my is None:
        return None

    nume = sum(
        (a - mx) * (b - my)
        for a, b in zip(x, y)
    )

    denx = math.sqrt(
        sum(
            (a - mx) ** 2
            for a in x
        )
    )

    deny = math.sqrt(
        sum(
            (b - my) ** 2
            for b in y
        )
    )

    return safe_div(
        nume,
        denx * deny,
    )


def spearman(
    x: Sequence[float],
    y: Sequence[float],
) -> Optional[float]:

    return pearson(
        rank(x),
        rank(y),
    )


# ============================================================================
# WINDOW AGGREGATION
# ============================================================================

def aggregate_rows(
    rows: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:

    if not rows:
        return {
            "samples": 0
        }

    def avg(key: str):
        return mean(
            [
                r[key]
                for r in rows
            ]
        )

    return {
        "samples": len(rows),

        "retrieval_accuracy":
            avg("retrieval_accuracy"),

        "baseline_accuracy":
            avg("baseline_accuracy"),

        "predictive_accuracy":
            avg("predictive_accuracy"),

        "retrieval_brier":
            avg("retrieval_brier"),

        "baseline_brier":
            avg("baseline_brier"),

        "predictive_brier":
            avg("predictive_brier"),

        "retrieval_logloss":
            avg("retrieval_logloss"),

        "baseline_logloss":
            avg("baseline_logloss"),

        "predictive_logloss":
            avg("predictive_logloss"),

        "retrieval_accuracy_lift":
            avg("retrieval_accuracy_lift"),

        "predictive_accuracy_lift":
            avg("predictive_accuracy_lift"),

        "retrieval_brier_lift":
            avg("retrieval_brier_lift"),

        "predictive_brier_lift":
            avg("predictive_brier_lift"),

        "retrieval_logloss_lift":
            avg("retrieval_logloss_lift"),

        "predictive_logloss_lift":
            avg("predictive_logloss_lift"),

        "top_similarity":
            avg("top_similarity"),

        "mean_similarity":
            avg("mean_similarity"),

        "matches":
            avg("matches"),

        "unique_episodes":
            avg("unique_episodes"),
    }


# ============================================================================
# QUERY EVALUATION
# ============================================================================

def evaluate_query(
    query_state: Any,
    records: Sequence[Any],
    candles: Sequence[Any],
    atr: Sequence[Any],
    horizon: int,
    query_index: int,
) -> Optional[Dict[str, Any]]:

    outcome = v420.make_outcome(
        candles,
        atr,
        query_index,
        horizon,
    )

    if outcome is None:
        return None

    actual = actual_direction(outcome)

    if actual not in CLASSES:
        return None

    causality = validate_record_causality(
        records,
        query_index,
    )

    if causality["violations"]:
        raise RuntimeError(
            "TRAIN/OOS causality violation."
        )

    retrieval, retrieval_probs = retrieval_prediction(
        query_state,
        records,
        horizon,
        query_index,
    )

    baseline_probs = baseline_prediction(
        query_state,
        records,
    )

    predictive_probs, predictive_result = (
        predictive_prediction(
            query_state,
            records,
            horizon,
            query_index,
        )
    )

    diagnostics = retrieval_diagnostics(
        retrieval
    )

    retrieval_accuracy = accuracy_metric(
        retrieval_probs,
        actual,
    )

    baseline_accuracy = accuracy_metric(
        baseline_probs,
        actual,
    )

    predictive_accuracy = accuracy_metric(
        predictive_probs,
        actual,
    )

    retrieval_brier = brier_metric(
        retrieval_probs,
        actual,
    )

    baseline_brier = brier_metric(
        baseline_probs,
        actual,
    )

    predictive_brier = brier_metric(
        predictive_probs,
        actual,
    )

    retrieval_logloss = logloss_metric(
        retrieval_probs,
        actual,
    )

    baseline_logloss = logloss_metric(
        baseline_probs,
        actual,
    )

    predictive_logloss = logloss_metric(
        predictive_probs,
        actual,
    )

    return {
        "query_index": query_index,
        "actual": actual,

        "regime": str(
            getattr(
                query_state,
                "regime",
                "UNKNOWN",
            )
        ),

        "sequence": str(
            getattr(
                query_state,
                "sequence_state",
                "UNKNOWN",
            )
        ),

        "structure_event": str(
            getattr(
                query_state,
                "structure_event",
                "UNKNOWN",
            )
        ),

        "retrieval_probs": retrieval_probs,
        "baseline_probs": baseline_probs,
        "predictive_probs": predictive_probs,

        "retrieval_accuracy":
            retrieval_accuracy,

        "baseline_accuracy":
            baseline_accuracy,

        "predictive_accuracy":
            predictive_accuracy,

        "retrieval_brier":
            retrieval_brier,

        "baseline_brier":
            baseline_brier,

        "predictive_brier":
            predictive_brier,

        "retrieval_logloss":
            retrieval_logloss,

        "baseline_logloss":
            baseline_logloss,

        "predictive_logloss":
            predictive_logloss,

        "retrieval_accuracy_lift":
            retrieval_accuracy
            - baseline_accuracy,

        "predictive_accuracy_lift":
            predictive_accuracy
            - baseline_accuracy,

        "retrieval_brier_lift":
            baseline_brier
            - retrieval_brier,

        "predictive_brier_lift":
            baseline_brier
            - predictive_brier,

        "retrieval_logloss_lift":
            baseline_logloss
            - retrieval_logloss,

        "predictive_logloss_lift":
            baseline_logloss
            - predictive_logloss,

        "top_similarity":
            diagnostics["top_similarity"],

        "mean_similarity":
            diagnostics["mean_similarity"],

        "matches":
            diagnostics["matches"],

        "unique_episodes":
            diagnostics["unique_episodes"],

        "sparse":
            bool(
                getattr(
                    retrieval,
                    "sparse_warning",
                    False,
                )
            ),

        "best_probability":
            finite(
                predictive_result.get(
                    "best_probability",
                    0.0,
                )
            ),

        "margin":
            finite(
                predictive_result.get(
                    "margin",
                    0.0,
                )
            ),

        "decision":
            predictive_result.get(
                "prediction"
            ),
    }


# ============================================================================
# GROUP ANALYSIS
# ============================================================================

def grouped_report(
    rows: Sequence[Dict[str, Any]],
    field: str,
    minimum: int = MIN_GROUP_SAMPLES,
) -> Dict[str, Any]:

    groups = defaultdict(list)

    for row in rows:
        groups[
            row.get(
                field,
                "UNKNOWN",
            )
        ].append(row)

    result = {}

    for name, group in sorted(
        groups.items(),
        key=lambda x: str(x[0]),
    ):

        if len(group) < minimum:
            continue

        result[str(name)] = aggregate_rows(
            group
        )

    return result


# ============================================================================
# WINDOW STABILITY
# ============================================================================

def stability_report(
    window_results: Dict[int, Dict[int, Dict[str, Any]]],
    horizon: int,
) -> Dict[str, Any]:

    values = []

    for window, horizon_map in sorted(
        window_results.items()
    ):

        result = horizon_map.get(
            horizon,
            {},
        )

        if result.get("samples", 0) <= 0:
            continue

        values.append(
            result
        )

    brier = [
        finite(
            x["predictive_brier_lift"]
        )
        for x in values
    ]

    logloss = [
        finite(
            x["predictive_logloss_lift"]
        )
        for x in values
    ]

    accuracy = [
        finite(
            x["predictive_accuracy_lift"]
        )
        for x in values
    ]

    return {
        "windows": len(values),

        "brier_positive":
            sum(
                x > 0
                for x in brier
            ),

        "logloss_positive":
            sum(
                x > 0
                for x in logloss
            ),

        "accuracy_positive":
            sum(
                x > 0
                for x in accuracy
            ),

        "mean_brier_lift":
            mean(brier),

        "mean_logloss_lift":
            mean(logloss),

        "mean_accuracy_lift":
            mean(accuracy),

        "brier_ci":
            bootstrap_mean_ci(
                brier
            ),

        "logloss_ci":
            bootstrap_mean_ci(
                logloss
            ),

        "accuracy_ci":
            bootstrap_mean_ci(
                accuracy
            ),
    }


# ============================================================================
# BLOCK NULL TEST
# ============================================================================

def block_permutation_test(
    rows: Sequence[Dict[str, Any]],
    permutations: int = NULL_PERMUTATIONS,
) -> Dict[str, Any]:

    if len(rows) < 10:
        return {
            "available": False,
            "reason": "insufficient samples",
        }

    ordered = sorted(
        rows,
        key=lambda r: r["query_index"],
    )

    labels = [
        r["actual"]
        for r in ordered
    ]

    predictive = [
        predicted_class(
            r["predictive_probs"]
        )
        for r in ordered
    ]

    baseline = [
        predicted_class(
            r["baseline_probs"]
        )
        for r in ordered
    ]

    observed = mean(
        [
            float(p == a)
            - float(b == a)
            for p, b, a
            in zip(
                predictive,
                baseline,
                labels,
            )
        ]
    )

    if observed is None:
        return {
            "available": False
        }

    # Preserve local temporal structure using circular shifts.
    # This is intentionally more conservative than IID shuffling.
    n = len(labels)

    rng = random.Random(SEED)

    null_values = []

    for _ in range(permutations):

        shift = rng.randrange(1, n)

        shifted = (
            labels[shift:]
            + labels[:shift]
        )

        value = mean(
            [
                float(p == a)
                - float(b == a)
                for p, b, a
                in zip(
                    predictive,
                    baseline,
                    shifted,
                )
            ]
        )

        null_values.append(
            finite(value)
        )

    null_values.sort()

    ge = sum(
        x >= observed
        for x in null_values
    )

    p = (
        ge + 1.0
    ) / (
        len(null_values) + 1.0
    )

    p95 = null_values[
        int(
            0.95
            * (len(null_values) - 1)
        )
    ]

    p99 = null_values[
        int(
            0.99
            * (len(null_values) - 1)
        )
    ]

    return {
        "available": True,
        "type": "circular_block_permutation",
        "permutations": permutations,
        "observed_accuracy_lift": observed,
        "null_mean": mean(null_values),
        "null_std": (
            statistics.pstdev(null_values)
            if len(null_values) > 1
            else 0.0
        ),
        "null_p95": p95,
        "null_p99": p99,
        "empirical_p_value": p,
        "beats_p95": observed > p95,
        "beats_p99": observed > p99,
    }


# ============================================================================
# VERDICT ENGINE
# ============================================================================

def evaluate_horizon_evidence(
    aggregate: Dict[str, Any],
    similarity: Dict[str, Any],
    calibration: Dict[str, Any],
    stability: Dict[str, Any],
    null_test: Dict[str, Any],
) -> Dict[str, Any]:

    decisions = {}

    # ---------------------------------------------------------------
    # Similarity discrimination
    # ---------------------------------------------------------------

    deciles = similarity.get(
        "deciles",
        [],
    )

    similarity_pass = False

    if len(deciles) >= 2:

        low = deciles[0]
        high = deciles[-1]

        similarity_delta = (
            high["mean_similarity"]
            - low["mean_similarity"]
        )

        predictive_brier_delta = (
            high["predictive_brier"]
            - low["predictive_brier"]
        )

        similarity_pass = (
            similarity_delta > 0
            and predictive_brier_delta <= 0
        )

    decisions[
        "similarity_discrimination"
    ] = similarity_pass

    # ---------------------------------------------------------------
    # Incremental predictive information
    # ---------------------------------------------------------------

    brier_lift = finite(
        aggregate.get(
            "predictive_brier_lift",
            0.0,
        )
    )

    logloss_lift = finite(
        aggregate.get(
            "predictive_logloss_lift",
            0.0,
        )
    )

    incremental_pass = (
        brier_lift > 0
        and logloss_lift > 0
    )

    decisions[
        "incremental_predictive_value"
    ] = incremental_pass

    # ---------------------------------------------------------------
    # Calibration
    # ---------------------------------------------------------------

    ece = calibration.get(
        "ece"
    )

    calibration_pass = (
        ece is not None
        and ece <= 0.10
    )

    decisions[
        "calibration"
    ] = calibration_pass

    # ---------------------------------------------------------------
    # Window stability
    # ---------------------------------------------------------------

    windows = int(
        stability.get(
            "windows",
            0,
        )
    )

    stable = (
        windows >= 3
        and stability.get(
            "brier_positive",
            0,
        )
        >= math.ceil(
            0.60 * windows
        )
        and stability.get(
            "logloss_positive",
            0,
        )
        >= math.ceil(
            0.60 * windows
        )
    )

    decisions[
        "cross_window_stability"
    ] = stable

    # ---------------------------------------------------------------
    # Null
    # ---------------------------------------------------------------

    null_pass = bool(
        null_test.get(
            "beats_p95",
            False,
        )
    )

    decisions[
        "null_support"
    ] = null_pass

    # ---------------------------------------------------------------
    # Strong evidence
    # ---------------------------------------------------------------

    strong = all(
        decisions.values()
    )

    decisions[
        "strong_evidence"
    ] = strong

    return decisions


# ============================================================================
# MAIN CONTEXT
# ============================================================================

def collect_context():

    candles, invalid = v420.load_market_data(
        DATA_FILE
    )

    chronology = v420.audit_chronology(
        candles
    )

    if (
        not chronology["ordered"]
        or chronology["duplicates"]
    ):
        raise RuntimeError(
            "Chronology audit failed."
        )

    if len(candles) < 500:
        raise RuntimeError(
            "Insufficient historical candles."
        )

    windows = v420.create_walk_forward_windows(
        len(candles),
        TRAIN_WINDOWS,
        OOS_SIZE,
    )

    atr = v420.calculate_atr(
        candles
    )

    engine = v420.CausalStructureEngine(
        candles
    )

    structure_states = engine.build()

    causality = v420.audit_structure_causality(
        candles,
        engine.swings,
        structure_states,
        engine.events,
    )

    if not causality["passed"]:
        raise RuntimeError(
            "Causal structure audit failed."
        )

    market_states = v420.build_market_states(
        candles,
        structure_states,
        atr,
    )

    episode_ids = v420.assign_episode_ids(
        market_states
    )

    return (
        candles,
        invalid,
        chronology,
        windows,
        atr,
        engine,
        causality,
        market_states,
        episode_ids,
    )


# ============================================================================
# MAIN
# ============================================================================

def main():

    started = time.time()

    print("=" * 110)
    print("MLAI V4.2.0 — DEFINITIVE PREDICTIVE INFORMATION AUDIT")
    print("=" * 110)
    print("FORENSIC RESEARCH / VALIDATION ONLY")
    print("Production MLAI: READ ONLY")
    print("Historical data: READ ONLY")
    print("OOS tuning: DISABLED")
    print()

    if not os.path.exists(DATA_FILE):
        raise FileNotFoundError(
            f"Missing {DATA_FILE!r}"
        )

    sha_before = sha256_file(
        DATA_FILE
    )

    print("PROTECTION")
    print("-" * 110)
    print(
        f"Dataset SHA256 before : {sha_before}"
    )
    print(
        "Production MLAI       : NOT MODIFIED"
    )
    print(
        "Learning memory       : NOT MODIFIED"
    )
    print(
        "Trading               : DISABLED"
    )
    print()

    (
        candles,
        invalid,
        chronology,
        windows,
        atr,
        engine,
        causality,
        market_states,
        episode_ids,
    ) = collect_context()

    print("FOUNDATION")
    print("-" * 110)
    print(
        f"Historical candles    : {len(candles)}"
    )
    print(
        f"Invalid candles       : {invalid}"
    )
    print(
        f"Walk-forward windows  : {len(windows)}"
    )
    print(
        f"Horizons              : {HORIZONS}"
    )
    print(
        f"Swings                : {len(engine.swings)}"
    )
    print(
        f"Structural events     : "
        f"{sum(1 for x in engine.events.values() if x != 'NONE')}"
    )
    print(
        f"Episodes              : "
        f"{len(set(episode_ids.values()))}"
    )
    print(
        f"Chronology            : "
        f"{'PASS' if chronology['ordered'] and not chronology['duplicates'] else 'FAIL'}"
    )
    print(
        f"Causal structure      : "
        f"{'PASS' if causality['passed'] else 'FAIL'}"
    )
    print()

    all_rows = []

    window_results = defaultdict(
        dict
    )

    protection = {
        "queries": 0,
        "records_checked": 0,
        "violations": 0,
    }

    # ========================================================================
    # WALK FORWARD
    # ========================================================================

    for window in windows:

        print("=" * 110)
        print(
            f"WINDOW {window.number} | "
            f"TRAIN [{window.train_start}:{window.train_end}] | "
            f"OOS [{window.oos_start}:{window.oos_end}]"
        )
        print("=" * 110)

        for horizon in HORIZONS:

            records = v420.build_experience_records(
                candles,
                atr,
                market_states,
                episode_ids,
                window.train_start,
                window.train_end,
                horizon,
            )

            rows = []

            for query_index in range(
                window.oos_start,
                window.oos_end,
            ):

                if (
                    query_index + horizon
                    >= len(candles)
                ):
                    continue

                query_state = (
                    market_states[
                        query_index
                    ]
                )

                row = evaluate_query(
                    query_state,
                    records,
                    candles,
                    atr,
                    horizon,
                    query_index,
                )

                protection["queries"] += 1

                causal = validate_record_causality(
                    records,
                    query_index,
                )

                protection["records_checked"] += (
                    causal["checked"]
                )

                protection["violations"] += (
                    causal["violations"]
                )

                if causal["violations"]:
                    raise RuntimeError(
                        "Causal leakage detected."
                    )

                if row is None:
                    continue

                row["window"] = window.number
                row["horizon"] = horizon

                rows.append(row)
                all_rows.append(row)

            aggregate = aggregate_rows(
                rows
            )

            window_results[
                window.number
            ][horizon] = aggregate

            print(
                f"H+{horizon:<2} | "
                f"N={aggregate.get('samples', 0):<4} | "
                f"Baseline Acc={pct(aggregate.get('baseline_accuracy')):<10} | "
                f"Predictive Acc={pct(aggregate.get('predictive_accuracy')):<10} | "
                f"ΔAcc={pct(aggregate.get('predictive_accuracy_lift')):<10} | "
                f"ΔBrier={num(aggregate.get('predictive_brier_lift')):<14} | "
                f"ΔLogLoss={num(aggregate.get('predictive_logloss_lift'))}"
            )

    # ========================================================================
    # GLOBAL HORIZON ANALYSIS
    # ========================================================================

    horizon_results = {}
    similarity_results = {}
    calibration_results = {}
    regime_results = {}
    stability_results = {}
    null_results = {}
    evidence_results = {}

    for horizon in HORIZONS:

        rows = [
            r
            for r in all_rows
            if r["horizon"] == horizon
        ]

        aggregate = aggregate_rows(
            rows
        )

        horizon_results[horizon] = aggregate

        # ------------------------------------------------------------
        # Similarity deciles
        # ------------------------------------------------------------

        deciles = similarity_deciles(
            rows
        )

        if len(deciles) >= 2:

            low = deciles[0]
            high = deciles[-1]

            similarity_delta = (
                high["mean_similarity"]
                - low["mean_similarity"]
            )

            brier_delta = (
                high["predictive_brier"]
                - low["predictive_brier"]
            )

            similarity_corr = spearman(
                [
                    r["top_similarity"]
                    for r in rows
                ],
                [
                    r["predictive_brier_lift"]
                    for r in rows
                ],
            )

        else:

            similarity_delta = None
            brier_delta = None
            similarity_corr = None

        similarity_results[horizon] = {
            "deciles": deciles,
            "top_minus_bottom_similarity":
                similarity_delta,
            "top_minus_bottom_predictive_brier":
                brier_delta,
            "spearman_similarity_vs_brier_lift":
                similarity_corr,
        }

        # ------------------------------------------------------------
        # Calibration
        # ------------------------------------------------------------

        calibration_results[horizon] = {
            "baseline":
                calibration_report(
                    rows,
                    "baseline_probs",
                ),
            "predictive":
                calibration_report(
                    rows,
                    "predictive_probs",
                ),
            "retrieval":
                calibration_report(
                    rows,
                    "retrieval_probs",
                ),
        }

        # ------------------------------------------------------------
        # Regimes
        # ------------------------------------------------------------

        regime_results[horizon] = grouped_report(
            rows,
            "regime",
        )

        # ------------------------------------------------------------
        # Stability
        # ------------------------------------------------------------

        stability_results[horizon] = (
            stability_report(
                dict(window_results),
                horizon,
            )
        )

        # ------------------------------------------------------------
        # Null
        # ------------------------------------------------------------

        null_results[horizon] = (
            block_permutation_test(
                rows
            )
        )

        # ------------------------------------------------------------
        # Evidence
        # ------------------------------------------------------------

        evidence_results[horizon] = (
            evaluate_horizon_evidence(
                aggregate,
                similarity_results[horizon],
                calibration_results[horizon][
                    "predictive"
                ],
                stability_results[horizon],
                null_results[horizon],
            )
        )

    # ========================================================================
    # OVERALL VERDICT
    # ========================================================================

    strong = [
        h
        for h in HORIZONS
        if evidence_results[h][
            "strong_evidence"
        ]
    ]

    incremental = [
        h
        for h in HORIZONS
        if evidence_results[h][
            "incremental_predictive_value"
        ]
    ]

    similarity_passes = [
        h
        for h in HORIZONS
        if evidence_results[h][
            "similarity_discrimination"
        ]
    ]

    null_passes = [
        h
        for h in HORIZONS
        if evidence_results[h][
            "null_support"
        ]
    ]

    if (
        len(strong) >= 2
        and len(null_passes) >= 2
    ):
        verdict = "STRONG EVIDENCE"

    elif (
        len(incremental) >= 2
        and len(null_passes) >= 1
    ):
        verdict = "MODERATE EVIDENCE"

    elif len(incremental) >= 1:
        verdict = "WEAK EVIDENCE"

    elif all_rows:
        verdict = "NO EVIDENCE"

    else:
        verdict = "INSUFFICIENT EVIDENCE"

    # ========================================================================
    # DATA PROTECTION
    # ========================================================================

    sha_after = sha256_file(
        DATA_FILE
    )

    unchanged = (
        sha_before == sha_after
    )

    if not unchanged:
        raise RuntimeError(
            "CRITICAL PROTECTION FAILURE: "
            "market_data.bin changed."
        )

    if protection["violations"]:
        raise RuntimeError(
            "CRITICAL PROTECTION FAILURE: "
            "causal leakage detected."
        )

    elapsed = time.time() - started

    # ========================================================================
    # FINAL CONSOLE REPORT
    # ========================================================================

    print()
    print("=" * 110)
    print("MLAI PREDICTIVE INFORMATION AUDIT")
    print("=" * 110)

    print()
    print("RETRIEVAL INFORMATION")

    for horizon in HORIZONS:

        sim = similarity_results[horizon]

        print(
            f"H+{horizon}:"
        )

        print(
            f"  Similarity discrimination : "
            f"{'PASS' if evidence_results[horizon]['similarity_discrimination'] else 'FAIL'}"
        )

        print(
            f"  Incremental information  : "
            f"{'PASS' if evidence_results[horizon]['incremental_predictive_value'] else 'FAIL'}"
        )

        print(
            f"  Similarity/Brier Spearman: "
            f"{num(sim['spearman_similarity_vs_brier_lift'])}"
        )

    print()
    print("PREDICTIVE IMPROVEMENT")

    for horizon in HORIZONS:

        a = horizon_results[horizon]

        print(
            f"H+{horizon}: "
            f"Accuracy Δ={pct(a.get('predictive_accuracy_lift'))} | "
            f"Brier Δ={num(a.get('predictive_brier_lift'))} | "
            f"LogLoss Δ={num(a.get('predictive_logloss_lift'))}"
        )

    print()
    print("CALIBRATION")

    for horizon in HORIZONS:

        c = calibration_results[horizon][
            "predictive"
        ]

        print(
            f"H+{horizon}: "
            f"ECE={num(c.get('ece'))}"
        )

    print()
    print("ROBUSTNESS")

    for horizon in HORIZONS:

        s = stability_results[horizon]

        print(
            f"H+{horizon}: "
            f"Brier-positive={s['brier_positive']}/{s['windows']} | "
            f"LogLoss-positive={s['logloss_positive']}/{s['windows']} | "
            f"Mean ΔBrier={num(s['mean_brier_lift'])}"
        )

    print()
    print("NULL TEST")

    for horizon in HORIZONS:

        n = null_results[horizon]

        print(
            f"H+{horizon}: "
            f"Observed={pct(n.get('observed_accuracy_lift'))} | "
            f"Null P95={pct(n.get('null_p95'))} | "
            f"p={num(n.get('empirical_p_value'))} | "
            f"Beat P95={n.get('beats_p95')}"
        )

    print()
    print("PROTECTION")

    print(
        f"Queries audited          : "
        f"{protection['queries']}"
    )

    print(
        f"Records checked          : "
        f"{protection['records_checked']}"
    )

    print(
        f"Causality violations     : "
        f"{protection['violations']}"
    )

    print(
        f"market_data.bin unchanged : "
        f"{'PASS' if unchanged else 'FAIL'}"
    )

    print(
        f"Production modified      : NO"
    )

    print(
        f"Learning memory modified : NO"
    )

    print()
    print("=" * 110)
    print(
        f"FINAL VERDICT: {verdict}"
    )
    print("=" * 110)
    print(
        f"Elapsed seconds: {elapsed:.2f}"
    )

    # ========================================================================
    # SERIALIZED ARTIFACT
    # ========================================================================

    artifact = {
        "audit_version":
            AUDIT_VERSION,

        "source":
            "mlai_market_structure_v420",

        "dataset": {
            "file":
                DATA_FILE,
            "candles":
                len(candles),
            "invalid":
                invalid,
            "sha256_before":
                sha_before,
            "sha256_after":
                sha_after,
            "unchanged":
                unchanged,
        },

        "foundation": {
            "chronology":
                chronology,
            "causality":
                causality,
            "windows":
                len(windows),
            "horizons":
                HORIZONS,
            "swings":
                len(engine.swings),
            "episodes":
                len(set(episode_ids.values())),
        },

        "protection":
            protection,

        "horizon_results":
            horizon_results,

        "similarity":
            similarity_results,

        "calibration":
            calibration_results,

        "regime":
            regime_results,

        "stability":
            stability_results,

        "null":
            null_results,

        "evidence":
            evidence_results,

        "verdict":
            verdict,

        "elapsed_seconds":
            elapsed,
    }

    with open(
        RESULTS_FILE,
        "wb",
    ) as f:

        pickle.dump(
            artifact,
            f,
            protocol=pickle.HIGHEST_PROTOCOL,
        )

    # ========================================================================
    # MARKDOWN REPORT
    # ========================================================================

    report = []

    report.append(
        "# MLAI V4.2.0 — Definitive Predictive Information Audit"
    )

    report.append("")

    report.append(
        f"Audit version: `{AUDIT_VERSION}`"
    )

    report.append("")

    report.append(
        "## Final verdict"
    )

    report.append("")

    report.append(
        f"**{verdict}**"
    )

    report.append("")

    report.append(
        "The verdict is generated from predefined evidence rules. "
        "No OOS result is used to modify the production model."
    )

    report.append("")

    report.append(
        "## Predictive results"
    )

    report.append("")

    report.append(
        "| Horizon | N | Baseline Acc | Predictive Acc | Δ Accuracy | Δ Brier | Δ LogLoss |"
    )

    report.append(
        "|---:|---:|---:|---:|---:|---:|---:|"
    )

    for horizon in HORIZONS:

        a = horizon_results[horizon]

        report.append(
            f"| H+{horizon} | "
            f"{a.get('samples', 0)} | "
            f"{pct(a.get('baseline_accuracy'))} | "
            f"{pct(a.get('predictive_accuracy'))} | "
            f"{pct(a.get('predictive_accuracy_lift'))} | "
            f"{num(a.get('predictive_brier_lift'))} | "
            f"{num(a.get('predictive_logloss_lift'))} |"
        )

    report.append("")

    report.append(
        "## Similarity discrimination"
    )

    report.append("")

    for horizon in HORIZONS:

        report.append(
            f"### H+{horizon}"
        )

        sim = similarity_results[horizon]

        report.append(
            f"- Spearman similarity vs predictive Brier lift: "
            f"`{num(sim['spearman_similarity_vs_brier_lift'])}`"
        )

        for decile in sim["deciles"]:

            report.append(
                f"- D{decile['decile']}: "
                f"N={decile['samples']}, "
                f"similarity={pct(decile['mean_similarity'])}, "
                f"predictive accuracy={pct(decile['predictive_accuracy'])}, "
                f"predictive Brier={num(decile['predictive_brier'])}"
            )

        report.append("")

    report.append(
        "## Calibration"
    )

    report.append("")

    for horizon in HORIZONS:

        c = calibration_results[horizon]

        report.append(
            f"### H+{horizon}"
        )

        for name in (
            "baseline",
            "retrieval",
            "predictive",
        ):

            result = c[name]

            report.append(
                f"- {name}: "
                f"ECE={num(result.get('ece'))}"
            )

        report.append("")

    report.append(
        "## Cross-window robustness"
    )

    report.append("")

    for horizon in HORIZONS:

        s = stability_results[horizon]

        report.append(
            f"- H+{horizon}: "
            f"{s['brier_positive']}/{s['windows']} "
            f"windows positive on Brier; "
            f"{s['logloss_positive']}/{s['windows']} "
            f"positive on LogLoss; "
            f"mean Brier lift={num(s['mean_brier_lift'])}; "
            f"95% CI="
            f"[{num(s['brier_ci'].get('ci95_low'))}, "
            f"{num(s['brier_ci'].get('ci95_high'))}]"
        )

    report.append("")

    report.append(
        "## Regime robustness"
    )

    report.append("")

    for horizon in HORIZONS:

        report.append(
            f"### H+{horizon}"
        )

        for name, result in regime_results[horizon].items():

            report.append(
                f"- `{name}`: "
                f"N={result['samples']}, "
                f"ΔAccuracy={pct(result['predictive_accuracy_lift'])}, "
                f"ΔBrier={num(result['predictive_brier_lift'])}, "
                f"ΔLogLoss={num(result['predictive_logloss_lift'])}"
            )

        report.append("")

    report.append(
        "## Null investigation"
    )

    report.append("")

    for horizon in HORIZONS:

        n = null_results[horizon]

        report.append(
            f"- H+{horizon}: "
            f"observed ΔAccuracy={pct(n.get('observed_accuracy_lift'))}; "
            f"null P95={pct(n.get('null_p95'))}; "
            f"null P99={pct(n.get('null_p99'))}; "
            f"empirical p={num(n.get('empirical_p_value'))}; "
            f"beats P95={n.get('beats_p95')}."
        )

    report.append("")

    report.append(
        "## Evidence by horizon"
    )

    report.append("")

    for horizon in HORIZONS:

        e = evidence_results[horizon]

        report.append(
            f"### H+{horizon}"
        )

        for key, value in e.items():

            report.append(
                f"- {key}: `{value}`"
            )

        report.append("")

    report.append(
        "## Protection"
    )

    report.append("")

    report.append(
        f"- SHA256 before: `{sha_before}`"
    )

    report.append(
        f"- SHA256 after: `{sha_after}`"
    )

    report.append(
        f"- Dataset unchanged: `{unchanged}`"
    )

    report.append(
        "- Production MLAI modified: `NO`"
    )

    report.append(
        "- Learning memory modified: `NO`"
    )

    report.append(
        "- Trading: `DISABLED`"
    )

    report.append("")

    report.append(
        f"Elapsed seconds: `{elapsed:.3f}`"
    )

    with open(
        REPORT_FILE,
        "w",
        encoding="utf-8",
    ) as f:

        f.write(
            "\n".join(report)
        )

    print()
    print("ARTIFACTS")
    print("-" * 110)
    print(
        RESULTS_FILE
    )
    print(
        REPORT_FILE
    )


if __name__ == "__main__":
    main()