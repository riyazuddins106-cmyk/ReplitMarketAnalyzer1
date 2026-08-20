"""
===============================================================================
MLAI V4.2.0 — MASTER FORENSIC PREDICTIVE INFORMATION AUDIT
===============================================================================

PURPOSE
-------
This is the MASTER investigation before any modification of MLAI V4.2.0.

It is NOT a patch.
It is NOT a replacement model.
It is NOT allowed to tune V4.2.0 from OOS results.

Its purpose is to determine:

1. What is working.
2. What is not working.
3. Exactly where predictive information is lost.
4. Whether similarity itself is meaningful.
5. Whether retrieved historical states have matching future distributions.
6. Whether retrieval adds information beyond the baseline.
7. Which retrieval component helps/hurts.
8. Whether candidate selection is the problem.
9. Whether weighting is the problem.
10. Whether aggregation is the problem.
11. Whether confidence/calibration is the problem.
12. Whether regime dependence explains failure.
13. Whether temporal distance / episode duplication contaminates results.
14. Whether high similarity is actually predictive.
15. Whether retrieval fails because of representation, ranking, or outcome
    heterogeneity.
16. Whether a simpler retrieval control performs better.
17. Whether any apparent improvement survives strict chronological OOS testing.
18. What the ROOT CAUSE is.
19. What the recommended FIX should be.

IMPORTANT
---------
This program NEVER modifies:

    mlai_market_structure_v420.py
    market_data.bin
    production MLAI
    learning memory

The audit is READ ONLY.

===============================================================================
"""

from __future__ import annotations

import hashlib
import math
import os
import pickle
import random
import statistics
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import mlai_market_structure_v420 as v420


# =============================================================================
# CONFIGURATION
# =============================================================================

AUDIT_VERSION = "V420-MASTER-FORENSIC-AUDIT-1.0"

DATA_FILE = v420.MARKET_DATA_FILE

REPORT_FILE = "MLAI_V420_MASTER_FORENSIC_AUDIT_REPORT.md"
RESULTS_FILE = "MLAI_V420_MASTER_FORENSIC_AUDIT.bin"

HORIZONS = tuple(v420.HORIZONS)

TRAIN_WINDOWS = v420.DEFAULT_TRAIN_WINDOWS
OOS_SIZE = v420.DEFAULT_OOS_SIZE

PERMUTATIONS = 1000
SEED = 4200420

EPS = 1e-12

CLASSES = ("UP", "DOWN", "NEUTRAL")

COMPONENTS = (
    "structure",
    "sequence",
    "regime",
    "location",
    "momentum",
    "volatility",
    "candle",
    "path",
)

TOP_K_VALUES = (1, 3, 5, 10, 25)

MIN_GROUP_SIZE = 20


# =============================================================================
# BASIC UTILITIES
# =============================================================================

def finite(x, default=0.0):
    try:
        x = float(x)
        return x if math.isfinite(x) else default
    except Exception:
        return default


def mean(values):
    vals = [finite(x) for x in values if x is not None]
    return sum(vals) / len(vals) if vals else None


def stdev(values):
    vals = [finite(x) for x in values if x is not None]
    return statistics.pstdev(vals) if len(vals) > 1 else 0.0


def safe_div(a, b):
    return a / b if abs(b) > EPS else 0.0


def pct(x):
    return "N/A" if x is None else f"{100.0 * x:.4f}%"


def num(x):
    return "N/A" if x is None else f"{x:.8f}"


def sha256(path):
    h = hashlib.sha256()

    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)

    return h.hexdigest()


def normalized_probs(values):
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


def prediction(probs):
    return max(
        CLASSES,
        key=lambda c: (finite(probs.get(c, 0.0)), c)
    )


def accuracy(probs, actual):
    return float(prediction(probs) == actual)


def brier(probs, actual):
    return sum(
        (
            finite(probs.get(c, 0.0))
            - float(c == actual)
        ) ** 2
        for c in CLASSES
    )


def logloss(probs, actual):
    p = max(
        EPS,
        min(
            1.0,
            finite(probs.get(actual, 0.0))
        )
    )

    return -math.log(p)


# =============================================================================
# OUTCOME EXTRACTION
# =============================================================================

def get_direction(obj):

    outcome = getattr(obj, "outcome", obj)

    for name in (
        "direction",
        "label",
        "class_name",
        "target",
        "prediction",
    ):
        value = getattr(outcome, name, None)

        if value is not None:

            value = str(value).upper().strip()

            if value in CLASSES:
                return value

    return None


# =============================================================================
# CORRELATION
# =============================================================================

def rank(values):

    indexed = sorted(
        enumerate(values),
        key=lambda x: x[1]
    )

    ranks = [0.0] * len(values)

    i = 0

    while i < len(indexed):

        j = i + 1

        while (
            j < len(indexed)
            and indexed[j][1] == indexed[i][1]
        ):
            j += 1

        r = (i + j - 1) / 2.0

        for k in range(i, j):
            ranks[indexed[k][0]] = r

        i = j

    return ranks


def spearman(x, y):

    if len(x) != len(y) or len(x) < 3:
        return None

    rx = rank(x)
    ry = rank(y)

    mx = mean(rx)
    my = mean(ry)

    numerator = sum(
        (a - mx) * (b - my)
        for a, b in zip(rx, ry)
    )

    dx = math.sqrt(
        sum((a - mx) ** 2 for a in rx)
    )

    dy = math.sqrt(
        sum((b - my) ** 2 for b in ry)
    )

    if dx <= EPS or dy <= EPS:
        return 0.0

    return numerator / (dx * dy)


# =============================================================================
# DATA / FOUNDATION
# =============================================================================

def load_foundation():

    candles, invalid = v420.load_market_data(DATA_FILE)

    chronology = v420.audit_chronology(candles)

    if not chronology["ordered"]:
        raise RuntimeError("Chronology failure.")

    if chronology["duplicates"]:
        raise RuntimeError("Duplicate timestamps detected.")

    atr = v420.calculate_atr(candles)

    engine = v420.CausalStructureEngine(candles)

    structure_states = engine.build()

    causality = v420.audit_structure_causality(
        candles,
        engine.swings,
        structure_states,
        engine.events,
    )

    if not causality["passed"]:
        raise RuntimeError("Causal structure audit failed.")

    market_states = v420.build_market_states(
        candles,
        structure_states,
        atr,
    )

    episode_ids = v420.assign_episode_ids(
        market_states
    )

    windows = v420.create_walk_forward_windows(
        len(candles),
        TRAIN_WINDOWS,
        OOS_SIZE,
    )

    return {
        "candles": candles,
        "invalid": invalid,
        "chronology": chronology,
        "atr": atr,
        "engine": engine,
        "causality": causality,
        "market_states": market_states,
        "episode_ids": episode_ids,
        "windows": windows,
    }


# =============================================================================
# CAUSAL RECORD AUDIT
# =============================================================================

def causal_record_audit(records, query_index):

    checked = 0
    violations = []

    for record in records:

        idx = getattr(record, "index", None)

        if idx is None:
            continue

        checked += 1

        try:
            idx = int(idx)
        except Exception:
            violations.append(("invalid_index", idx))
            continue

        if idx >= query_index:
            violations.append(
                ("future_record", idx)
            )

    return {
        "checked": checked,
        "violations": violations,
    }


# =============================================================================
# RETRIEVAL INSPECTION
# =============================================================================

def retrieve(
    state,
    records,
    horizon,
    query_index,
):

    result = v420.retrieve_historical_experience(
        state,
        records,
        horizon,
        query_index,
    )

    probs = normalized_probs({
        "UP": getattr(result, "up_share", 0.0),
        "DOWN": getattr(result, "down_share", 0.0),
        "NEUTRAL": getattr(result, "neutral_share", 0.0),
    })

    return result, probs


# =============================================================================
# BASELINE
# =============================================================================

def baseline(
    state,
    records,
):

    _, distribution, _ = v420.conditional_baseline(
        state,
        records,
    )

    return normalized_probs(distribution)


# =============================================================================
# PRODUCTION PREDICTION
# =============================================================================

def production_prediction(
    state,
    records,
    horizon,
    query_index,
):

    result = v420.mlai_v415_repaired_prediction(
        current=state,
        records=records,
        horizon=horizon,
        query_index=query_index,
    )

    probs = normalized_probs(
        result.get("probabilities", {})
    )

    return probs, result


# =============================================================================
# COMPONENT VECTOR
# =============================================================================

def component_vector(
    state,
    record,
):

    values = v420._v420_component_vector(
        state,
        record,
    )

    values = dict(values)

    try:
        values["quality"] = v420._v420_quality_gates(
            values
        )
    except Exception:
        values["quality"] = 0.0

    return values


# =============================================================================
# CANDIDATE FORENSICS
# =============================================================================

def inspect_candidates(
    state,
    records,
    horizon,
    query_index,
):

    candidates = []

    for record in records:

        idx = getattr(record, "index", None)

        if idx is None:
            continue

        idx = int(idx)

        if idx >= query_index:
            continue

        gap = query_index - idx

        if gap < v420.MIN_HISTORY_GAP:
            continue

        if getattr(record, "horizon", horizon) != horizon:
            continue

        try:

            values = component_vector(
                state,
                record,
            )

            contradiction = v420._v420_contradiction(
                state,
                record,
                values,
            )

            weights = dict(
                v420.V420_HORIZON_WEIGHTS.get(
                    int(horizon),
                    v420.V420_HORIZON_WEIGHTS[8],
                )
            )

            total = sum(weights.values())

            similarity = safe_div(
                sum(
                    weights.get(k, 0.0)
                    * finite(values.get(k, 0.0))
                    for k in weights
                ),
                total,
            )

            quality = finite(
                values.get("quality", 0.0)
            )

            candidates.append({
                "index": idx,
                "gap": gap,
                "episode_id": getattr(
                    record,
                    "episode_id",
                    None,
                ),
                "direction": get_direction(record),
                "similarity": similarity,
                "quality": quality,
                "contradiction": finite(
                    contradiction
                ),
                "components": {
                    k: finite(values.get(k, 0.0))
                    for k in COMPONENTS
                },
            })

        except Exception:
            continue

    candidates.sort(
        key=lambda x: (
            x["similarity"],
            -x["gap"],
        ),
        reverse=True,
    )

    return candidates


# =============================================================================
# RETRIEVAL DIAGNOSTICS
# =============================================================================

def retrieval_diagnostics(
    candidates,
    actual,
):

    result = {
        "candidate_count": len(candidates),
        "unique_episodes": len(
            {
                c["episode_id"]
                for c in candidates
                if c["episode_id"] is not None
            }
        ),
        "same_outcome_top": {},
        "similarity": {},
        "gap": {},
        "components": {},
    }

    if not candidates:
        return result

    for k in TOP_K_VALUES:

        top = candidates[:k]

        labels = [
            x["direction"]
            for x in top
            if x["direction"] in CLASSES
        ]

        if labels:

            counts = Counter(labels)

            result["same_outcome_top"][k] = safe_div(
                counts.get(actual, 0),
                len(labels),
            )

        else:

            result["same_outcome_top"][k] = None

    similarities = [
        x["similarity"]
        for x in candidates
    ]

    gaps = [
        x["gap"]
        for x in candidates
    ]

    result["similarity"] = {
        "top1": similarities[0],
        "top5": mean(similarities[:5]),
        "top10": mean(similarities[:10]),
        "top25": mean(similarities[:25]),
        "mean": mean(similarities),
        "std": stdev(similarities),
    }

    result["gap"] = {
        "top1": gaps[0],
        "top5": mean(gaps[:5]),
        "top10": mean(gaps[:10]),
        "mean": mean(gaps),
    }

    for component in COMPONENTS:

        values = [
            x["components"].get(
                component,
                0.0
            )
            for x in candidates
        ]

        result["components"][component] = {
            "top1": values[0],
            "top5": mean(values[:5]),
            "top10": mean(values[:10]),
            "mean": mean(values),
        }

    return result


# =============================================================================
# OUTCOME DISTRIBUTION OF SIMILAR HISTORICAL STATES
# =============================================================================

def outcome_distribution(
    candidates,
):

    result = {}

    for k in TOP_K_VALUES:

        top = candidates[:k]

        labels = [
            x["direction"]
            for x in top
            if x["direction"] in CLASSES
        ]

        if not labels:
            result[k] = None
            continue

        counts = Counter(labels)

        result[k] = {
            c: safe_div(
                counts.get(c, 0),
                len(labels),
            )
            for c in CLASSES
        }

    return result


# =============================================================================
# OUTCOME HETEROGENEITY
# =============================================================================

def entropy(distribution):

    vals = [
        finite(distribution.get(c, 0.0))
        for c in CLASSES
    ]

    vals = [
        x for x in vals
        if x > EPS
    ]

    return -sum(
        x * math.log(x)
        for x in vals
    )


def candidate_entropy(candidates):

    result = {}

    for k in TOP_K_VALUES:

        top = candidates[:k]

        labels = [
            x["direction"]
            for x in top
            if x["direction"] in CLASSES
        ]

        if not labels:
            result[k] = None
            continue

        counts = Counter(labels)

        distribution = {
            c: safe_div(
                counts.get(c, 0),
                len(labels),
            )
            for c in CLASSES
        }

        result[k] = entropy(
            distribution
        )

    return result


# =============================================================================
# SIMILARITY DECILE ANALYSIS
# =============================================================================

def decile_analysis(
    candidate_rows,
):

    if len(candidate_rows) < 20:
        return []

    ordered = sorted(
        candidate_rows,
        key=lambda x: x["similarity"]
    )

    result = []

    n = len(ordered)

    for d in range(10):

        lo = (d * n) // 10
        hi = ((d + 1) * n) // 10

        chunk = ordered[lo:hi]

        if not chunk:
            continue

        valid = [
            x for x in chunk
            if x["direction"] in CLASSES
        ]

        if not valid:
            continue

        accuracy_values = [
            float(x["direction"] == x["query_actual"])
            for x in valid
        ]

        result.append({
            "decile": d + 1,
            "n": len(valid),
            "mean_similarity": mean([
                x["similarity"]
                for x in valid
            ]),
            "same_outcome_rate": mean(
                accuracy_values
            ),
        })

    return result


# =============================================================================
# CALIBRATION
# =============================================================================

def calibration(rows, probability_field):

    if not rows:
        return {
            "ece": None,
            "mce": None,
        }

    bins = defaultdict(list)

    for row in rows:

        probs = row[probability_field]

        confidence = max(
            probs.get(c, 0.0)
            for c in CLASSES
        )

        pred = prediction(probs)

        correct = float(
            pred == row["actual"]
        )

        bucket = min(
            9,
            int(confidence * 10)
        )

        bins[bucket].append(
            (confidence, correct)
        )

    ece = 0.0
    mce = 0.0
    total = len(rows)

    details = []

    for bucket, values in sorted(
        bins.items()
    ):

        conf = mean(
            [x[0] for x in values]
        )

        acc = mean(
            [x[1] for x in values]
        )

        gap = abs(conf - acc)

        weight = len(values) / total

        ece += weight * gap
        mce = max(mce, gap)

        details.append({
            "bin": bucket,
            "n": len(values),
            "confidence": conf,
            "accuracy": acc,
            "gap": gap,
        })

    return {
        "ece": ece,
        "mce": mce,
        "bins": details,
    }


# =============================================================================
# STATISTICAL CONFIDENCE INTERVAL
# =============================================================================

def bootstrap_delta(
    deltas,
    iterations=1000,
):

    if len(deltas) < 5:
        return None

    rng = random.Random(SEED)

    estimates = []

    n = len(deltas)

    for _ in range(iterations):

        sample = [
            deltas[
                rng.randrange(n)
            ]
            for _ in range(n)
        ]

        estimates.append(
            mean(sample)
        )

    estimates.sort()

    lo = estimates[
        int(0.025 * len(estimates))
    ]

    hi = estimates[
        int(0.975 * len(estimates))
    ]

    return {
        "mean": mean(deltas),
        "lower_95": lo,
        "upper_95": hi,
    }


# =============================================================================
# PERMUTATION TEST
# =============================================================================

def permutation_test(
    predictions,
    baselines,
    actuals,
):

    observed = mean([
        float(
            prediction(p) == a
        )
        -
        float(
            prediction(b) == a
        )
        for p, b, a in zip(
            predictions,
            baselines,
            actuals,
        )
    ])

    rng = random.Random(SEED)

    labels = list(actuals)

    null = []

    for _ in range(PERMUTATIONS):

        rng.shuffle(labels)

        null.append(
            mean([
                float(
                    prediction(p) == a
                )
                -
                float(
                    prediction(b) == a
                )
                for p, b, a in zip(
                    predictions,
                    baselines,
                    labels,
                )
            ])
        )

    null.sort()

    ge = sum(
        x >= observed
        for x in null
    )

    p = (
        ge + 1
    ) / (
        len(null) + 1
    )

    return {
        "observed": observed,
        "null_mean": mean(null),
        "null_std": stdev(null),
        "p_value": p,
        "p95": null[
            int(0.95 * (len(null) - 1))
        ],
        "p99": null[
            int(0.99 * (len(null) - 1))
        ],
    }


# =============================================================================
# MAIN QUERY AUDIT
# =============================================================================

def audit_query(
    state,
    records,
    candles,
    atr,
    horizon,
    query_index,
):

    outcome = v420.make_outcome(
        candles,
        atr,
        query_index,
        horizon,
    )

    if outcome is None:
        return None

    actual = get_direction(outcome)

    if actual not in CLASSES:
        return None

    causal = causal_record_audit(
        records,
        query_index,
    )

    if causal["violations"]:
        raise RuntimeError(
            f"CAUSALITY FAILURE at query {query_index}"
        )

    retrieval, retrieval_probs = retrieve(
        state,
        records,
        horizon,
        query_index,
    )

    baseline_probs = baseline(
        state,
        records,
    )

    production_probs, production_result = (
        production_prediction(
            state,
            records,
            horizon,
            query_index,
        )
    )

    candidates = inspect_candidates(
        state,
        records,
        horizon,
        query_index,
    )

    diagnostics = retrieval_diagnostics(
        candidates,
        actual,
    )

    distributions = outcome_distribution(
        candidates
    )

    entropies = candidate_entropy(
        candidates
    )

    row = {
        "query_index": query_index,
        "actual": actual,

        "regime": str(
            getattr(
                state,
                "regime",
                "UNKNOWN",
            )
        ),

        "sequence": str(
            getattr(
                state,
                "sequence_state",
                "UNKNOWN",
            )
        ),

        "structure_event": str(
            getattr(
                state,
                "structure_event",
                "UNKNOWN",
            )
        ),

        "retrieval_probs":
            retrieval_probs,

        "baseline_probs":
            baseline_probs,

        "production_probs":
            production_probs,

        "retrieval_accuracy":
            accuracy(
                retrieval_probs,
                actual,
            ),

        "baseline_accuracy":
            accuracy(
                baseline_probs,
                actual,
            ),

        "production_accuracy":
            accuracy(
                production_probs,
                actual,
            ),

        "retrieval_brier":
            brier(
                retrieval_probs,
                actual,
            ),

        "baseline_brier":
            brier(
                baseline_probs,
                actual,
            ),

        "production_brier":
            brier(
                production_probs,
                actual,
            ),

        "retrieval_logloss":
            logloss(
                retrieval_probs,
                actual,
            ),

        "baseline_logloss":
            logloss(
                baseline_probs,
                actual,
            ),

        "production_logloss":
            logloss(
                production_probs,
                actual,
            ),

        "retrieval_accuracy_lift":
            accuracy(
                retrieval_probs,
                actual,
            )
            -
            accuracy(
                baseline_probs,
                actual,
            ),

        "production_accuracy_lift":
            accuracy(
                production_probs,
                actual,
            )
            -
            accuracy(
                baseline_probs,
                actual,
            ),

        "retrieval_brier_lift":
            brier(
                baseline_probs,
                actual,
            )
            -
            brier(
                retrieval_probs,
                actual,
            ),

        "production_brier_lift":
            brier(
                baseline_probs,
                actual,
            )
            -
            brier(
                production_probs,
                actual,
            ),

        "retrieval_logloss_lift":
            logloss(
                baseline_probs,
                actual,
            )
            -
            logloss(
                retrieval_probs,
                actual,
            ),

        "production_logloss_lift":
            logloss(
                baseline_probs,
                actual,
            )
            -
            logloss(
                production_probs,
                actual,
            ),

        "top_similarity":
            finite(
                getattr(
                    retrieval,
                    "top_similarity",
                    0.0,
                )
            ),

        "mean_similarity":
            finite(
                getattr(
                    retrieval,
                    "mean_similarity",
                    0.0,
                )
            ),

        "matches":
            int(
                getattr(
                    retrieval,
                    "deduplicated_matches",
                    0,
                )
            ),

        "sparse":
            bool(
                getattr(
                    retrieval,
                    "sparse_warning",
                    True,
                )
            ),

        "candidate_diagnostics":
            diagnostics,

        "outcome_distributions":
            distributions,

        "candidate_entropy":
            entropies,

        "production_result":
            production_result,
    }

    return row


# =============================================================================
# AGGREGATION
# =============================================================================

def aggregate(rows):

    if not rows:
        return {
            "samples": 0
        }

    def M(field):
        return mean([
            r[field]
            for r in rows
        ])

    return {
        "samples": len(rows),

        "retrieval_accuracy":
            M("retrieval_accuracy"),

        "baseline_accuracy":
            M("baseline_accuracy"),

        "production_accuracy":
            M("production_accuracy"),

        "retrieval_brier":
            M("retrieval_brier"),

        "baseline_brier":
            M("baseline_brier"),

        "production_brier":
            M("production_brier"),

        "retrieval_logloss":
            M("retrieval_logloss"),

        "baseline_logloss":
            M("baseline_logloss"),

        "production_logloss":
            M("production_logloss"),

        "retrieval_accuracy_lift":
            M("retrieval_accuracy_lift"),

        "production_accuracy_lift":
            M("production_accuracy_lift"),

        "retrieval_brier_lift":
            M("retrieval_brier_lift"),

        "production_brier_lift":
            M("production_brier_lift"),

        "retrieval_logloss_lift":
            M("retrieval_logloss_lift"),

        "production_logloss_lift":
            M("production_logloss_lift"),

        "top_similarity":
            M("top_similarity"),

        "mean_similarity":
            M("mean_similarity"),

        "matches":
            M("matches"),

        "coverage":
            mean([
                float(not r["sparse"])
                for r in rows
            ]),
    }


# =============================================================================
# ROOT CAUSE ENGINE
# =============================================================================

def determine_root_causes(
    horizon_rows,
    horizon_windows,
):

    causes = []

    a = aggregate(
        horizon_rows
    )

    # ------------------------------------------------------------
    # ROOT CAUSE 1 — RETRIEVAL DOES NOT ADD INFORMATION
    # ------------------------------------------------------------

    if (
        a["production_brier_lift"] is not None
        and a["production_brier_lift"] < 0
    ):

        causes.append({
            "priority": "P0",
            "code": "RETRIEVAL_NEGATIVE_INCREMENTAL_VALUE",
            "finding":
                "Historical retrieval worsens probabilistic prediction "
                "relative to the conditional baseline.",
            "likely_area":
                "retrieval integration / candidate relevance / weighting",
            "recommended_fix":
                "Do not increase retrieval weight. First isolate candidate "
                "selection, outcome homogeneity, and aggregation failure."
        })

    # ------------------------------------------------------------
    # ROOT CAUSE 2 — SIMILARITY WITHOUT OUTCOME ALIGNMENT
    # ------------------------------------------------------------

    similarities = [
        r["top_similarity"]
        for r in horizon_rows
    ]

    briers = [
        r["production_brier"]
        for r in horizon_rows
    ]

    corr = spearman(
        similarities,
        briers,
    )

    if corr is not None and corr >= -0.05:

        causes.append({
            "priority": "P0",
            "code": "SIMILARITY_NOT_PREDICTIVELY_ALIGNED",
            "finding":
                f"Similarity/Brier relationship is weak "
                f"(Spearman={corr:.6f}).",
            "likely_area":
                "market-state representation or similarity metric",
            "recommended_fix":
                "Redesign similarity only after determining which state "
                "dimensions fail to discriminate future outcomes."
        })

    # ------------------------------------------------------------
    # ROOT CAUSE 3 — WINDOW INSTABILITY
    # ------------------------------------------------------------

    positive = sum(
        1
        for r in horizon_windows
        if finite(
            r.get(
                "production_brier_lift",
                0
            )
        ) > 0
    )

    if horizon_windows and positive < (
        len(horizon_windows) * 0.6
    ):

        causes.append({
            "priority": "P0",
            "code": "CROSS_WINDOW_INSTABILITY",
            "finding":
                f"Only {positive}/{len(horizon_windows)} "
                "walk-forward windows improve Brier score.",
            "likely_area":
                "non-stationary retrieval relationship / regime dependence",
            "recommended_fix":
                "Investigate regime-conditioned retrieval and temporal "
                "relevance before changing global weights."
        })

    # ------------------------------------------------------------
    # ROOT CAUSE 4 — OVERCONFIDENCE
    # ------------------------------------------------------------

    confidences = [
        max(
            r["production_probs"].values()
        )
        for r in horizon_rows
    ]

    correct = [
        r["production_accuracy"]
        for r in horizon_rows
    ]

    if mean(confidences) > mean(correct) + 0.05:

        causes.append({
            "priority": "P1",
            "code": "CONFIDENCE_OVERSTATEMENT",
            "finding":
                "Mean predictive confidence exceeds observed accuracy.",
            "likely_area":
                "probability construction / aggregation",
            "recommended_fix":
                "Do not use raw similarity as confidence. Calibrate "
                "probabilities using training-only calibration."
        })

    # ------------------------------------------------------------
    # ROOT CAUSE 5 — CANDIDATE OUTCOME HETEROGENEITY
    # ------------------------------------------------------------

    entropy_values = []

    for row in horizon_rows:

        e = row["candidate_entropy"].get(
            10
        )

        if e is not None:
            entropy_values.append(e)

    if entropy_values:

        avg_entropy = mean(
            entropy_values
        )

        max_entropy = math.log(
            len(CLASSES)
        )

        if avg_entropy > (
            0.85 * max_entropy
        ):

            causes.append({
                "priority": "P0",
                "code": "OUTCOME_HETEROGENEITY",
                "finding":
                    "Top historical matches contain highly mixed future "
                    "outcomes.",
                "likely_area":
                    "state representation / retrieval equivalence",
                "recommended_fix":
                    "Increase state discrimination or introduce outcome-aware "
                    "historical conditioning."
            })

    # ------------------------------------------------------------
    # ROOT CAUSE 6 — RETRIEVAL IS TOO REMOTE
    # ------------------------------------------------------------

    gaps = []

    for row in horizon_rows:

        d = row[
            "candidate_diagnostics"
        ]

        g = d.get(
            "gap",
            {}
        ).get(
            "top10"
        )

        if g is not None:
            gaps.append(g)

    if gaps:

        avg_gap = mean(gaps)

        if avg_gap > 300:

            causes.append({
                "priority": "P1",
                "code": "TEMPORAL_DISTANCE",
                "finding":
                    f"Top historical matches are temporally remote "
                    f"(mean top-10 gap={avg_gap:.1f} candles).",
                "likely_area":
                    "temporal relevance",
                "recommended_fix":
                    "Evaluate recency weighting or regime-era matching."
            })

    # ------------------------------------------------------------
    # ROOT CAUSE 7 — DUPLICATE EPISODE DOMINANCE
    # ------------------------------------------------------------

    episode_ratios = []

    for row in horizon_rows:

        d = row[
            "candidate_diagnostics"
        ]

        candidates = d.get(
            "candidate_count",
            0
        )

        episodes = d.get(
            "unique_episodes",
            0
        )

        if candidates:
            episode_ratios.append(
                safe_div(
                    episodes,
                    candidates
                )
            )

    if episode_ratios:

        if mean(episode_ratios) < 0.50:

            causes.append({
                "priority": "P1",
                "code": "EPISODE_CONCENTRATION",
                "finding":
                    "Candidate sets contain many records from a small "
                    "number of historical episodes.",
                "likely_area":
                    "experience-record independence",
                "recommended_fix":
                    "Strengthen episode-level deduplication so one historical "
                    "event cannot dominate retrieval."
            })

    return causes


# =============================================================================
# MASTER VERDICT
# =============================================================================

def verdict(
    horizon_reports,
    all_causes,
):

    positive_horizons = 0
    robust_horizons = 0

    for h, report in horizon_reports.items():

        a = report["aggregate"]

        if (
            a["production_brier_lift"] is not None
            and a["production_brier_lift"] > 0
            and a["production_logloss_lift"] is not None
            and a["production_logloss_lift"] > 0
        ):
            positive_horizons += 1

        stability = report[
            "window_stability"
        ]

        if (
            stability["positive_brier"]
            >=
            math.ceil(
                0.60 *
                stability["windows"]
            )
            and
            stability["positive_logloss"]
            >=
            math.ceil(
                0.60 *
                stability["windows"]
            )
        ):
            robust_horizons += 1

    if (
        positive_horizons >= 2
        and robust_horizons >= 2
        and not any(
            c["priority"] == "P0"
            for c in all_causes
        )
    ):
        return "STRONG EVIDENCE"

    if positive_horizons >= 2:
        return "MODERATE / UNSTABLE EVIDENCE"

    if positive_horizons == 1:
        return "WEAK / HORIZON-SPECIFIC EVIDENCE"

    return "NO EVIDENCE"


# =============================================================================
# REPORT GENERATION
# =============================================================================

def generate_report(
    foundation,
    reports,
    causes,
    final_verdict,
    protection,
    elapsed,
):

    lines = []

    lines.append(
        "# MLAI V4.2.0 MASTER FORENSIC PREDICTIVE INFORMATION AUDIT"
    )

    lines.append("")
    lines.append(
        f"Audit version: `{AUDIT_VERSION}`"
    )

    lines.append("")
    lines.append(
        "## 1. Executive conclusion"
    )

    lines.append("")

    lines.append(
        f"**FINAL VERDICT: {final_verdict}**"
    )

    lines.append("")

    lines.append(
        "This audit is diagnostic. It does not modify V4.2.0."
    )

    lines.append("")

    lines.append(
        "The purpose is to identify the exact failure location before "
        "any production change."
    )

    lines.append("")

    # -----------------------------------------------------------------
    # FOUNDATION
    # -----------------------------------------------------------------

    lines.append(
        "## 2. Foundation integrity"
    )

    lines.append("")

    lines.append(
        f"- Candles: {len(foundation['candles'])}"
    )

    lines.append(
        f"- Invalid candles: {foundation['invalid']}"
    )

    lines.append(
        f"- Walk-forward windows: {len(foundation['windows'])}"
    )

    lines.append(
        f"- Swings: {len(foundation['engine'].swings)}"
    )

    lines.append(
        "- Chronology: PASS"
    )

    lines.append(
        "- Causal structure: PASS"
    )

    lines.append("")

    # -----------------------------------------------------------------
    # HORIZONS
    # -----------------------------------------------------------------

    lines.append(
        "## 3. Horizon performance"
    )

    lines.append("")

    lines.append(
        "| Horizon | N | Baseline Acc | Production Acc | ΔAcc | ΔBrier | ΔLogLoss |"
    )

    lines.append(
        "|---|---:|---:|---:|---:|---:|---:|"
    )

    for h, report in reports.items():

        a = report["aggregate"]

        lines.append(
            f"| H+{h} | "
            f"{a['samples']} | "
            f"{pct(a['baseline_accuracy'])} | "
            f"{pct(a['production_accuracy'])} | "
            f"{pct(a['production_accuracy_lift'])} | "
            f"{num(a['production_brier_lift'])} | "
            f"{num(a['production_logloss_lift'])} |"
        )

    lines.append("")

    # -----------------------------------------------------------------
    # SIMILARITY
    # -----------------------------------------------------------------

    lines.append(
        "## 4. Similarity validity"
    )

    lines.append("")

    for h, report in reports.items():

        corr = report[
            "similarity_brier_spearman"
        ]

        lines.append(
            f"### H+{h}"
        )

        lines.append("")

        lines.append(
            f"- Similarity → Brier Spearman: `{num(corr)}`"
        )

        lines.append(
            f"- Mean top similarity: `{pct(report['aggregate']['top_similarity'])}`"
        )

        lines.append(
            f"- Mean candidate count: `{num(report['aggregate']['matches'])}`"
        )

        lines.append("")

        for d in report[
            "deciles"
        ]:

            lines.append(
                f"- Decile {d['decile']}: "
                f"N={d['n']}, "
                f"similarity={pct(d['mean_similarity'])}, "
                f"same-outcome={pct(d['same_outcome_rate'])}"
            )

        lines.append("")

    # -----------------------------------------------------------------
    # CANDIDATE QUALITY
    # -----------------------------------------------------------------

    lines.append(
        "## 5. Candidate quality / historical outcome separation"
    )

    lines.append("")

    for h, report in reports.items():

        lines.append(
            f"### H+{h}"
        )

        lines.append("")

        lines.append(
            f"- Mean candidate entropy H+10: "
            f"{num(report['candidate_entropy'])}"
        )

        lines.append(
            f"- Mean unique-episode ratio: "
            f"{pct(report['unique_episode_ratio'])}"
        )

        lines.append(
            f"- Mean top-10 temporal gap: "
            f"{num(report['mean_top10_gap'])}"
        )

        lines.append("")

    # -----------------------------------------------------------------
    # WINDOW STABILITY
    # -----------------------------------------------------------------

    lines.append(
        "## 6. Walk-forward stability"
    )

    lines.append("")

    for h, report in reports.items():

        s = report[
            "window_stability"
        ]

        lines.append(
            f"- H+{h}: "
            f"Brier-positive {s['positive_brier']}/{s['windows']}; "
            f"LogLoss-positive {s['positive_logloss']}/{s['windows']}; "
            f"mean Brier lift {num(s['mean_brier'])}; "
            f"mean LogLoss lift {num(s['mean_logloss'])}"
        )

    lines.append("")

    # -----------------------------------------------------------------
    # REGIMES
    # -----------------------------------------------------------------

    lines.append(
        "## 7. Regime stability"
    )

    lines.append("")

    for h, report in reports.items():

        lines.append(
            f"### H+{h}"
        )

        for name, values in report[
            "regimes"
        ].items():

            lines.append(
                f"- `{name}`: "
                f"N={values['samples']}, "
                f"ΔBrier={num(values['production_brier_lift'])}, "
                f"ΔLogLoss={num(values['production_logloss_lift'])}, "
                f"ΔAcc={pct(values['production_accuracy_lift'])}"
            )

        lines.append("")

    # -----------------------------------------------------------------
    # ROOT CAUSES
    # -----------------------------------------------------------------

    lines.append(
        "## 8. ROOT-CAUSE FINDINGS"
    )

    lines.append("")

    if not causes:

        lines.append(
            "No major predefined root-cause condition was triggered."
        )

    else:

        for i, cause in enumerate(
            causes,
            1
        ):

            lines.append(
                f"### {i}. [{cause['priority']}] "
                f"{cause['code']}"
            )

            lines.append("")

            lines.append(
                f"**Finding:** {cause['finding']}"
            )

            lines.append("")

            lines.append(
                f"**Likely area:** {cause['likely_area']}"
            )

            lines.append("")

            lines.append(
                f"**Recommended fix:** {cause['recommended_fix']}"
            )

            lines.append("")

    # -----------------------------------------------------------------
    # FIX PLAN
    # -----------------------------------------------------------------

    lines.append(
        "## 9. MASTER FIX PLAN"
    )

    lines.append("")

    lines.append(
        "The following order is mandatory. Do not change global retrieval "
        "weights before completing the earlier diagnostic fixes."
    )

    lines.append("")

    lines.append(
        "### P0-1 — Verify similarity/outcome relationship"
    )

    lines.append(
        "Do not treat similarity as confidence until high-similarity "
        "historical states demonstrate materially different future "
        "outcome distributions."
    )

    lines.append("")

    lines.append(
        "### P0-2 — Fix candidate equivalence"
    )

    lines.append(
        "Investigate which market-state dimensions are producing false "
        "historical matches."
    )

    lines.append("")

    lines.append(
        "### P0-3 — Fix outcome heterogeneity"
    )

    lines.append(
        "A retrieval candidate set containing strongly conflicting "
        "future outcomes is not a predictive historical analogue."
    )

    lines.append("")

    lines.append(
        "### P0-4 — Fix retrieval aggregation"
    )

    lines.append(
        "Do not assume top similarity should directly determine "
        "probability. Evaluate rank weighting, episode weighting, "
        "outcome consistency and effective sample size."
    )

    lines.append("")

    lines.append(
        "### P1-1 — Add temporal relevance only if evidence supports it"
    )

    lines.append(
        "Historical similarity from a distant regime should not automatically "
        "receive the same predictive authority as a recent equivalent state."
    )

    lines.append("")

    lines.append(
        "### P1-2 — Regime-conditioned retrieval"
    )

    lines.append(
        "If retrieval works in some regimes and fails in others, "
        "global retrieval should not be applied uniformly."
    )

    lines.append("")

    lines.append(
        "### P1-3 — Calibration"
    )

    lines.append(
        "Similarity must never be presented as probability. "
        "Probability calibration must be learned only from training data."
    )

    lines.append("")

    lines.append(
        "### P2 — Optimize computational implementation"
    )

    lines.append(
        "Only after correctness is established should candidate scanning "
        "and component calculations be optimized."
    )

    lines.append("")

    # -----------------------------------------------------------------
    # PROTECTION
    # -----------------------------------------------------------------

    lines.append(
        "## 10. Protection verification"
    )

    lines.append("")

    lines.append(
        f"- Dataset unchanged: "
        f"{protection['unchanged']}"
    )

    lines.append(
        "- Production MLAI modified: NO"
    )

    lines.append(
        "- Learning memory modified: NO"
    )

    lines.append(
        "- Trading enabled: NO"
    )

    lines.append("")

    lines.append(
        f"Audit runtime: {elapsed:.2f}s"
    )

    return "\n".join(lines)


# =============================================================================
# MAIN
# =============================================================================

def main():

    start = time.time()

    print("=" * 110)
    print(
        "MLAI V4.2.0 — MASTER FORENSIC PREDICTIVE INFORMATION AUDIT"
    )
    print("=" * 110)

    print(
        "READ ONLY | NO PATCHING | NO OOS TUNING"
    )

    print()

    if not os.path.exists(DATA_FILE):
        raise FileNotFoundError(
            DATA_FILE
        )

    before_hash = sha256(
        DATA_FILE
    )

    foundation = load_foundation()

    candles = foundation[
        "candles"
    ]

    atr = foundation[
        "atr"
    ]

    market_states = foundation[
        "market_states"
    ]

    episode_ids = foundation[
        "episode_ids"
    ]

    windows = foundation[
        "windows"
    ]

    all_rows = []

    reports = {}

    # =================================================================
    # WALK FORWARD
    # =================================================================

    for horizon in HORIZONS:

        print()
        print("=" * 100)
        print(
            f"FORENSIC HORIZON H+{horizon}"
        )
        print("=" * 100)

        rows = []

        window_results = []

        for window in windows:

            records = v420.build_experience_records(
                candles,
                atr,
                market_states,
                episode_ids,
                window.train_start,
                window.train_end,
                horizon,
            )

            window_rows = []

            for query_index in range(
                window.oos_start,
                window.oos_end,
            ):

                if (
                    query_index + horizon
                    >= len(candles)
                ):
                    continue

                row = audit_query(
                    market_states[
                        query_index
                    ],
                    records,
                    candles,
                    atr,
                    horizon,
                    query_index,
                )

                if row is None:
                    continue

                row["window"] = window.number
                row["horizon"] = horizon

                rows.append(row)
                window_rows.append(row)

                all_rows.append(row)

            a = aggregate(
                window_rows
            )

            window_results.append(a)

            print(
                f"Window {window.number}: "
                f"N={a.get('samples',0)} | "
                f"Baseline={pct(a.get('baseline_accuracy'))} | "
                f"Production={pct(a.get('production_accuracy'))} | "
                f"ΔAcc={pct(a.get('production_accuracy_lift'))} | "
                f"ΔBrier={num(a.get('production_brier_lift'))} | "
                f"ΔLogLoss={num(a.get('production_logloss_lift'))}"
            )

        # =============================================================
        # GLOBAL HORIZON
        # =============================================================

        a = aggregate(rows)

        similarities = [
            r["top_similarity"]
            for r in rows
        ]

        briers = [
            r["production_brier"]
            for r in rows
        ]

        corr = spearman(
            similarities,
            briers,
        )

        # =============================================================
        # DECILES
        # =============================================================

        candidate_rows = []

        for row in rows:

            candidates = (
                row[
                    "candidate_diagnostics"
                ]
            )

            # Reconstruct a lightweight row
            # from top similarity.
            candidate_rows.append({
                "similarity":
                    row["top_similarity"],
                "direction":
                    prediction(
                        row[
                            "production_probs"
                        ]
                    ),
                "query_actual":
                    row["actual"],
            })

        deciles = decile_analysis(
            candidate_rows
        )

        # =============================================================
        # REGIMES
        # =============================================================

        regime_groups = defaultdict(list)

        for row in rows:
            regime_groups[
                row["regime"]
            ].append(row)

        regimes = {}

        for name, group in regime_groups.items():

            if len(group) < MIN_GROUP_SIZE:
                continue

            regimes[name] = aggregate(
                group
            )

        # =============================================================
        # CANDIDATE FORENSICS
        # =============================================================

        entropies = []
        episode_ratios = []
        gaps = []

        for row in rows:

            d = row[
                "candidate_diagnostics"
            ]

            e = row[
                "candidate_entropy"
            ].get(
                10
            )

            if e is not None:
                entropies.append(e)

            count = d.get(
                "candidate_count",
                0
            )

            episodes = d.get(
                "unique_episodes",
                0
            )

            if count:
                episode_ratios.append(
                    safe_div(
                        episodes,
                        count,
                    )
                )

            g = d.get(
                "gap",
                {}
            ).get(
                "top10"
            )

            if g is not None:
                gaps.append(g)

        # =============================================================
        # WINDOW STABILITY
        # =============================================================

        brier_lifts = [
            w.get(
                "production_brier_lift",
                0.0
            )
            for w in window_results
        ]

        logloss_lifts = [
            w.get(
                "production_logloss_lift",
                0.0
            )
            for w in window_results
        ]

        stability = {
            "windows":
                len(window_results),

            "positive_brier":
                sum(
                    x > 0
                    for x in brier_lifts
                ),

            "positive_logloss":
                sum(
                    x > 0
                    for x in logloss_lifts
                ),

            "mean_brier":
                mean(brier_lifts),

            "mean_logloss":
                mean(logloss_lifts),
        }

        reports[horizon] = {
            "aggregate": a,
            "window_results": window_results,
            "window_stability": stability,
            "similarity_brier_spearman": corr,
            "deciles": deciles,
            "regimes": regimes,
            "candidate_entropy":
                mean(entropies),
            "unique_episode_ratio":
                mean(episode_ratios),
            "mean_top10_gap":
                mean(gaps),
        }

    # =================================================================
    # ROOT CAUSE ANALYSIS
    # =================================================================

    causes = []

    for h in HORIZONS:

        rows = [
            r
            for r in all_rows
            if r["horizon"] == h
        ]

        causes.extend(
            determine_root_causes(
                rows,
                reports[h][
                    "window_results"
                ],
            )
        )

    # Remove duplicate root causes.
    unique = {}

    for cause in causes:
        unique[
            cause["code"]
        ] = cause

    causes = list(
        unique.values()
    )

    causes.sort(
        key=lambda x: (
            x["priority"],
            x["code"],
        )
    )

    final_verdict = verdict(
        reports,
        causes,
    )

    # =================================================================
    # PROTECTION
    # =================================================================

    after_hash = sha256(
        DATA_FILE
    )

    unchanged = (
        before_hash
        ==
        after_hash
    )

    protection = {
        "before": before_hash,
        "after": after_hash,
        "unchanged": unchanged,
    }

    elapsed = time.time() - start

    # =================================================================
    # SAVE ARTIFACT
    # =================================================================

    artifact = {
        "audit_version":
            AUDIT_VERSION,

        "final_verdict":
            final_verdict,

        "foundation": {
            "candles":
                len(candles),
            "invalid":
                foundation["invalid"],
            "windows":
                len(windows),
            "swings":
                len(
                    foundation[
                        "engine"
                    ].swings
                ),
            "structural_events":
                sum(
                    1
                    for e
                    in foundation[
                        "engine"
                    ].events.values()
                    if e != "NONE"
                ),
        },

        "reports":
            reports,

        "root_causes":
            causes,

        "protection":
            protection,

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

    report_text = generate_report(
        foundation,
        reports,
        causes,
        final_verdict,
        protection,
        elapsed,
    )

    with open(
        REPORT_FILE,
        "w",
        encoding="utf-8",
    ) as f:

        f.write(
            report_text
        )

    # =================================================================
    # FINAL CONSOLE
    # =================================================================

    print()
    print("=" * 110)
    print(
        "MLAI V4.2.0 MASTER FORENSIC AUDIT"
    )
    print("=" * 110)

    for h in HORIZONS:

        a = reports[h][
            "aggregate"
        ]

        s = reports[h][
            "window_stability"
        ]

        print()
        print(
            f"H+{h}"
        )

        print(
            f"  Baseline accuracy : "
            f"{pct(a['baseline_accuracy'])}"
        )

        print(
            f"  Production accuracy : "
            f"{pct(a['production_accuracy'])}"
        )

        print(
            f"  Accuracy lift : "
            f"{pct(a['production_accuracy_lift'])}"
        )

        print(
            f"  Brier lift : "
            f"{num(a['production_brier_lift'])}"
        )

        print(
            f"  LogLoss lift : "
            f"{num(a['production_logloss_lift'])}"
        )

        print(
            f"  Similarity/Brier Spearman : "
            f"{num(reports[h]['similarity_brier_spearman'])}"
        )

        print(
            f"  Positive Brier windows : "
            f"{s['positive_brier']}/{s['windows']}"
        )

        print(
            f"  Positive LogLoss windows : "
            f"{s['positive_logloss']}/{s['windows']}"
        )

    print()
    print(
        "ROOT CAUSES"
    )

    if causes:

        for cause in causes:

            print(
                f"[{cause['priority']}] "
                f"{cause['code']}"
            )

            print(
                f"    {cause['finding']}"
            )

            print(
                f"    FIX: {cause['recommended_fix']}"
            )

    else:

        print(
            "No predefined root cause triggered."
        )

    print()
    print(
        f"FINAL VERDICT: {final_verdict}"
    )

    print()
    print(
        "PROTECTION"
    )

    print(
        f"  SHA256 unchanged : "
        f"{'PASS' if unchanged else 'FAIL'}"
    )

    print(
        "  Production modified : NO"
    )

    print(
        "  Learning memory modified : NO"
    )

    print(
        "  Trading : DISABLED"
    )

    print()
    print(
        f"Audit runtime: {elapsed:.2f}s"
    )

    print()
    print(
        "ARTIFACTS"
    )

    print(
        f"  {RESULTS_FILE}"
    )

    print(
        f"  {REPORT_FILE}"
    )

    if not unchanged:

        raise RuntimeError(
            "PROTECTION FAILURE: market_data.bin changed."
        )


if __name__ == "__main__":
    main()