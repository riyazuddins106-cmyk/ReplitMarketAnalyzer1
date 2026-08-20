from pathlib import Path
import importlib
import inspect
import math
import random
import statistics
import traceback


# =============================================================================
# MLAI v4.1.5 — CAUSAL PREDICTIVE VALUE AUDIT
# =============================================================================
#
# PURPOSE
# -------
# v4.1.5 has already passed implementation/causality/runtime contracts.
#
# This program does NOT modify v4.1.5.
# This program does NOT modify market_data.bin.
# This program does NOT create v4.1.6.
#
# It investigates a different question:
#
#     "Does the historical-experience retrieval system contain measurable
#      predictive information on unseen chronological data?"
#
# IMPORTANT:
# This is a diagnostic/scientific evaluation.
# A poor score is NOT automatically an implementation bug.
# A good score is NOT automatically proof of a tradable system.
# =============================================================================


MODULE_NAME = "mlai_market_structure_v415"
MODULE_FILE = Path("mlai_market_structure_v415.py")
DATA_FILE = "market_data.bin"

HORIZONS = (4, 8, 16)

# Number of chronological walk-forward query points.
# Kept moderate so the audit remains practical.
MAX_QUERIES_PER_HORIZON = 250

# Minimum historical training data before querying.
MIN_TRAIN_END = 300

# Number of historical records required before retrieval.
MIN_RECORDS = 50

# Null/permutation repetitions.
NULL_REPETITIONS = 100

# Deterministic seed.
RANDOM_SEED = 415


# =============================================================================
# HELPERS
# =============================================================================

def section(number, title):
    print()
    print("=" * 100)
    print(f"{number}. {title}")
    print("=" * 100)


def sub(title):
    print()
    print("-" * 100)
    print(title)
    print("-" * 100)


def safe_float(x):
    try:
        value = float(x)
        if math.isfinite(value):
            return value
    except Exception:
        pass
    return None


def outcome_direction(record):
    """
    Extract direction from an ExperienceRecord.

    Expected:
        UP
        DOWN
        NEUTRAL
    """
    outcome = getattr(record, "outcome", None)

    if outcome is None:
        return None

    direction = getattr(outcome, "direction", None)

    if direction is None:
        return None

    return str(direction).upper()


def result_direction(result):
    """
    Convert retrieval result into a predicted direction.

    v4.1.5 retrieval exposes:
        up_share
        down_share
        neutral_share

    Prediction:
        highest share wins.

    Ties are treated as NEUTRAL.
    """

    up = safe_float(getattr(result, "up_share", None))
    down = safe_float(getattr(result, "down_share", None))
    neutral = safe_float(getattr(result, "neutral_share", None))

    if up is None or down is None or neutral is None:
        return None

    values = {
        "UP": up,
        "DOWN": down,
        "NEUTRAL": neutral,
    }

    best = max(values.values())

    winners = [
        key for key, value in values.items()
        if abs(value - best) < 1e-12
    ]

    if len(winners) != 1:
        return "NEUTRAL"

    return winners[0]


def majority_direction(records):
    counts = {
        "UP": 0,
        "DOWN": 0,
        "NEUTRAL": 0,
    }

    for record in records:
        direction = outcome_direction(record)

        if direction in counts:
            counts[direction] += 1

    if sum(counts.values()) == 0:
        return None

    return max(counts, key=counts.get)


def direction_counts(records):
    counts = {
        "UP": 0,
        "DOWN": 0,
        "NEUTRAL": 0,
    }

    for record in records:
        direction = outcome_direction(record)

        if direction in counts:
            counts[direction] += 1

    return counts


def actual_future_direction(candles, index, horizon):
    """
    Independently determine the actual future direction.

    This is deliberately calculated directly from candles rather than
    trusting the retrieval result.

    Uses close[index] -> close[index + horizon].
    """

    if index < 0:
        return None

    future_index = index + horizon

    if future_index >= len(candles):
        return None

    current_close = safe_float(candles[index].close)
    future_close = safe_float(candles[future_index].close)

    if current_close is None or future_close is None:
        return None

    if future_close > current_close:
        return "UP"

    if future_close < current_close:
        return "DOWN"

    return "NEUTRAL"


def balanced_accuracy(rows):
    """
    Macro recall over UP/DOWN/NEUTRAL.
    """

    labels = ("UP", "DOWN", "NEUTRAL")

    recalls = []

    for label in labels:

        actual = [
            row
            for row in rows
            if row["actual"] == label
        ]

        if not actual:
            continue

        correct = sum(
            1
            for row in actual
            if row["predicted"] == label
        )

        recalls.append(correct / len(actual))

    if not recalls:
        return float("nan")

    return sum(recalls) / len(recalls)


def accuracy(rows):
    if not rows:
        return float("nan")

    return sum(
        row["predicted"] == row["actual"]
        for row in rows
    ) / len(rows)


def print_metrics(name, rows):

    print()
    print(name)

    if not rows:
        print("  samples       : 0")
        print("  accuracy       : N/A")
        print("  balanced acc.  : N/A")
        return

    acc = accuracy(rows)
    bal = balanced_accuracy(rows)

    print(f"  samples       : {len(rows)}")
    print(f"  accuracy      : {acc:.4f} ({acc * 100:.2f}%)")
    print(f"  balanced acc. : {bal:.4f} ({bal * 100:.2f}%)")

    for label in ("UP", "DOWN", "NEUTRAL"):

        subset = [
            row
            for row in rows
            if row["actual"] == label
        ]

        if subset:

            hit = sum(
                row["predicted"] == label
                for row in subset
            )

            print(
                f"  recall {label:<7}: "
                f"{hit / len(subset):.4f}"
            )


# =============================================================================
# START
# =============================================================================

print("=" * 100)
print("MLAI v4.1.5 — CAUSAL PREDICTIVE VALUE AUDIT")
print("=" * 100)

print()
print("SAFETY:")
print("  Source modification : NO")
print("  Data modification   : NO")
print("  v4.1.6 creation     : NO")
print("  Random seed         :", RANDOM_SEED)

random.seed(RANDOM_SEED)


# =============================================================================
# 1. SOURCE INTEGRITY SNAPSHOT
# =============================================================================

section(1, "SOURCE / DATA SAFETY SNAPSHOT")

if not MODULE_FILE.exists():
    print("FAIL: mlai_market_structure_v415.py not found.")
    raise SystemExit(1)

data_path = Path(DATA_FILE)

if not data_path.exists():
    print("FAIL: market_data.bin not found.")
    raise SystemExit(1)

source_before = MODULE_FILE.read_bytes()
data_before = data_path.read_bytes()

print("Source bytes :", len(source_before))
print("Data bytes   :", len(data_before))

print("SAFETY SNAPSHOT: PASS")


# =============================================================================
# 2. IMPORT
# =============================================================================

section(2, "MODULE IMPORT")

try:
    module = importlib.import_module(MODULE_NAME)
    print("IMPORT: PASS")
except Exception as exc:
    print("IMPORT: FAIL")
    print(type(exc).__name__, exc)
    traceback.print_exc()
    raise SystemExit(1)


# =============================================================================
# 3. LOAD DATA
# =============================================================================

section(3, "MARKET DATA")

loader = getattr(module, "load_market_data", None)

if loader is None:
    print("FAIL: load_market_data missing.")
    raise SystemExit(1)

try:
    loaded = loader(
        getattr(module, "MARKET_DATA_FILE", DATA_FILE)
    )

    candles, invalid = loaded

    print("candles :", len(candles))
    print("invalid :", invalid)

    if not candles:
        raise RuntimeError("No candles loaded.")

    if invalid != 0:
        print("WARNING: invalid candles =", invalid)

    candle_cls = getattr(module, "Candle", None)

    if candle_cls is not None:
        print(
            "first candle Candle:",
            isinstance(candles[0], candle_cls)
        )

    print("MARKET DATA: PASS")

except Exception as exc:
    print("MARKET DATA: FAIL")
    print(type(exc).__name__, exc)
    traceback.print_exc()
    raise SystemExit(1)


# =============================================================================
# 4. ATR
# =============================================================================

section(4, "ATR")

atr_fn = getattr(module, "calculate_atr", None)

if atr_fn is None:
    atr_fn = getattr(module, "compute_atr", None)

if atr_fn is None:
    print("ATR FUNCTION: MISSING")
    raise SystemExit(1)

try:
    atr = atr_fn(candles)

    print("ATR length:", len(atr))

    if len(atr) != len(candles):
        print("ATR LENGTH: FAIL")
        raise SystemExit(1)

    print("ATR: PASS")

except Exception as exc:
    print("ATR: FAIL")
    print(type(exc).__name__, exc)
    traceback.print_exc()
    raise SystemExit(1)


# =============================================================================
# 5. STRUCTURE
# =============================================================================

section(5, "CAUSAL STRUCTURE")

engine_cls = getattr(module, "CausalStructureEngine", None)

if engine_cls is None:
    engine_cls = getattr(module, "MarketStructureEngine", None)

if engine_cls is None:
    print("STRUCTURE ENGINE: MISSING")
    raise SystemExit(1)

try:
    engine = engine_cls(candles)
    structure = engine.build()

    print("structure length:", len(structure))

    if len(structure) != len(candles):
        raise RuntimeError(
            "Structure length does not equal candle length."
        )

    print("STRUCTURE: PASS")

except Exception as exc:
    print("STRUCTURE: FAIL")
    print(type(exc).__name__, exc)
    traceback.print_exc()
    raise SystemExit(1)


# =============================================================================
# 6. MARKET STATES
# =============================================================================

section(6, "MARKET STATES")

market_state_fn = getattr(
    module,
    "build_market_states",
    None
)

if market_state_fn is None:
    print("build_market_states missing.")
    raise SystemExit(1)

try:
    market_states = market_state_fn(
        candles,
        structure,
        atr,
    )

    print("market states:", len(market_states))

    if len(market_states) != len(candles):
        raise RuntimeError(
            "Market-state length mismatch."
        )

    print("MARKET STATES: PASS")

except Exception as exc:
    print("MARKET STATES: FAIL")
    print(type(exc).__name__, exc)
    traceback.print_exc()
    raise SystemExit(1)


# =============================================================================
# 7. EPISODES
# =============================================================================

section(7, "EPISODES")

episode_fn = getattr(
    module,
    "assign_episode_ids",
    None
)

if episode_fn is None:
    print("assign_episode_ids missing.")
    raise SystemExit(1)

try:
    episode_ids = episode_fn(market_states)

    print("episode coverage:", len(episode_ids))
    print(
        "unique episodes:",
        len(set(episode_ids.values()))
    )

    print("EPISODES: PASS")

except Exception as exc:
    print("EPISODES: FAIL")
    print(type(exc).__name__, exc)
    traceback.print_exc()
    raise SystemExit(1)


# =============================================================================
# 8. EXPERIENCE RECORD BUILDER
# =============================================================================

section(8, "EXPERIENCE RECORD BUILDER")

experience_fn = getattr(
    module,
    "build_experience_records",
    None
)

if experience_fn is None:
    print("build_experience_records missing.")
    raise SystemExit(1)


# =============================================================================
# 9. RETRIEVAL FUNCTION
# =============================================================================

section(9, "HISTORICAL RETRIEVAL API")

retrieve_fn = getattr(
    module,
    "retrieve_historical_experience",
    None
)

if retrieve_fn is None:
    print("retrieve_historical_experience missing.")
    raise SystemExit(1)

print("signature:")
try:
    print(inspect.signature(retrieve_fn))
except Exception:
    print("unavailable")


# =============================================================================
# 10. WALK-FORWARD PREDICTIVE TEST
# =============================================================================

section(10, "CHRONOLOGICAL WALK-FORWARD PREDICTIVE TEST")

print()
print("IMPORTANT:")
print("  Training records are constructed only from data before each query.")
print("  Query outcomes are NOT allowed into the historical record set.")
print("  Retrieval must therefore operate strictly backward in time.")

all_results = {h: [] for h in HORIZONS}

query_counts = {h: 0 for h in HORIZONS}

retrieval_failures = {h: 0 for h in HORIZONS}

temporal_violations = {h: [] for h in HORIZONS}

similarities = {h: [] for h in HORIZONS}

levels = {h: {} for h in HORIZONS}


for horizon in HORIZONS:

    print()
    print("#" * 100)
    print(f"HORIZON = {horizon}")
    print("#" * 100)

    max_query = len(candles) - horizon - 1

    if max_query <= MIN_TRAIN_END:
        print("Not enough data.")
        continue

    possible_queries = list(
        range(
            MIN_TRAIN_END,
            max_query + 1
        )
    )

    # Evenly sample chronological query points.
    if len(possible_queries) > MAX_QUERIES_PER_HORIZON:

        step = (
            len(possible_queries)
            / MAX_QUERIES_PER_HORIZON
        )

        query_indices = [
            possible_queries[
                min(
                    int(i * step),
                    len(possible_queries) - 1
                )
            ]
            for i in range(MAX_QUERIES_PER_HORIZON)
        ]

        query_indices = sorted(set(query_indices))

    else:
        query_indices = possible_queries

    print("query points:", len(query_indices))

    for query_index in query_indices:

        train_end = query_index

        try:

            records = experience_fn(
                candles,
                atr,
                market_states,
                episode_ids,
                0,
                train_end,
                horizon,
            )

            if len(records) < MIN_RECORDS:
                continue

            current = market_states[query_index]

            result = retrieve_fn(
                current,
                records,
                horizon,
                query_index,
            )

            predicted = result_direction(result)

            actual = actual_future_direction(
                candles,
                query_index,
                horizon,
            )

            if predicted is None or actual is None:
                continue

            # -------------------------------------------------------------
            # Temporal isolation verification
            # -------------------------------------------------------------

            selected = getattr(
                result,
                "selected_match_indices",
                ()
            )

            historical_max = max(
                [int(r.index) for r in records],
                default=-1
            )

            for selected_index in selected:

                selected_index = int(selected_index)

                if selected_index >= query_index:
                    temporal_violations[horizon].append(
                        (
                            query_index,
                            selected_index,
                            "selected match at/after query"
                        )
                    )

                if selected_index + horizon > query_index:
                    temporal_violations[horizon].append(
                        (
                            query_index,
                            selected_index,
                            "selected outcome overlaps query"
                        )
                    )

            # -------------------------------------------------------------
            # Store result
            # -------------------------------------------------------------

            row = {
                "query_index": query_index,
                "predicted": predicted,
                "actual": actual,
                "top_similarity": safe_float(
                    getattr(
                        result,
                        "top_similarity",
                        None
                    )
                ),
                "mean_similarity": safe_float(
                    getattr(
                        result,
                        "mean_similarity",
                        None
                    )
                ),
                "evidence": getattr(
                    result,
                    "evidence",
                    None
                ),
                "level": getattr(
                    result,
                    "level",
                    None
                ),
                "up_share": safe_float(
                    getattr(
                        result,
                        "up_share",
                        None
                    )
                ),
                "down_share": safe_float(
                    getattr(
                        result,
                        "down_share",
                        None
                    )
                ),
                "neutral_share": safe_float(
                    getattr(
                        result,
                        "neutral_share",
                        None
                    )
                ),
                "historical_max": historical_max,
                "selected_count": len(selected),
            }

            all_results[horizon].append(row)

            query_counts[horizon] += 1

            if row["top_similarity"] is not None:
                similarities[horizon].append(
                    row["top_similarity"]
                )

            level = str(row["level"])

            levels[horizon][level] = (
                levels[horizon].get(level, 0) + 1
            )

        except Exception:
            retrieval_failures[horizon] += 1


# =============================================================================
# 11. PREDICTIVE METRICS
# =============================================================================

section(11, "PREDICTIVE RESULTS")

for horizon in HORIZONS:

    rows = all_results[horizon]

    print()
    print(f"HORIZON {horizon}")
    print("-" * 60)

    print_metrics(
        "MLAI RETRIEVAL",
        rows
    )

    if not rows:
        continue

    # -------------------------------------------------------------------------
    # Majority baseline
    # -------------------------------------------------------------------------

    counts = {
        "UP": sum(
            r["actual"] == "UP"
            for r in rows
        ),
        "DOWN": sum(
            r["actual"] == "DOWN"
            for r in rows
        ),
        "NEUTRAL": sum(
            r["actual"] == "NEUTRAL"
            for r in rows
        ),
    }

    majority = max(
        counts,
        key=counts.get
    )

    baseline_rows = [
        {
            "actual": r["actual"],
            "predicted": majority,
        }
        for r in rows
    ]

    print()
    print(
        "MAJORITY BASELINE:",
        majority
    )

    print_metrics(
        "MAJORITY BASELINE",
        baseline_rows
    )

    mla_acc = accuracy(rows)
    base_acc = accuracy(baseline_rows)

    print()
    print(
        "accuracy improvement:",
        f"{mla_acc - base_acc:+.4f}"
    )

    print(
        "accuracy improvement %:",
        f"{(mla_acc - base_acc) * 100:+.2f} percentage points"
    )

    if similarities[horizon]:

        print()
        print(
            "mean top similarity:",
            f"{statistics.mean(similarities[horizon]):.6f}"
        )

        print(
            "median top similarity:",
            f"{statistics.median(similarities[horizon]):.6f}"
        )

    print()
    print("retrieval levels:")

    for key, value in sorted(
        levels[horizon].items()
    ):
        print(
            f"  {key:<25} {value}"
        )

    print()
    print(
        "retrieval failures:",
        retrieval_failures[horizon]
    )

    print(
        "temporal violations:",
        len(temporal_violations[horizon])
    )


# =============================================================================
# 12. TEMPORAL ISOLATION
# =============================================================================

section(12, "TEMPORAL ISOLATION RESULTS")

temporal_fail = False

for horizon in HORIZONS:

    violations = temporal_violations[horizon]

    print(
        f"H{horizon}:",
        "PASS" if not violations else "FAIL",
        f"violations={len(violations)}"
    )

    if violations:

        temporal_fail = True

        for violation in violations[:10]:
            print(" ", violation)

if temporal_fail:
    print()
    print("CRITICAL: temporal leakage detected.")
else:
    print()
    print(
        "TEMPORAL ISOLATION: PASS"
    )


# =============================================================================
# 13. DIRECTIONAL CONFUSION MATRICES
# =============================================================================

section(13, "DIRECTIONAL CONFUSION MATRICES")

for horizon in HORIZONS:

    rows = all_results[horizon]

    if not rows:
        continue

    labels = (
        "UP",
        "DOWN",
        "NEUTRAL",
    )

    print()
    print(f"H{horizon}")
    print()

    print(
        f"{'ACTUAL/PRED':<15}"
        + "".join(
            f"{label:>12}"
            for label in labels
        )
    )

    for actual in labels:

        values = []

        for predicted in labels:

            count = sum(
                1
                for row in rows
                if row["actual"] == actual
                and row["predicted"] == predicted
            )

            values.append(count)

        print(
            f"{actual:<15}"
            + "".join(
                f"{value:>12}"
                for value in values
            )
        )


# =============================================================================
# 14. SIMILARITY / PERFORMANCE RELATIONSHIP
# =============================================================================

section(14, "SIMILARITY VS CORRECTNESS")

for horizon in HORIZONS:

    rows = all_results[horizon]

    if not rows:
        continue

    buckets = {
        "0.50-0.60": [],
        "0.60-0.70": [],
        "0.70-0.80": [],
        "0.80-0.90": [],
        "0.90-1.00": [],
    }

    for row in rows:

        score = row["top_similarity"]

        if score is None:
            continue

        if score < 0.60:
            key = "0.50-0.60"
        elif score < 0.70:
            key = "0.60-0.70"
        elif score < 0.80:
            key = "0.70-0.80"
        elif score < 0.90:
            key = "0.80-0.90"
        else:
            key = "0.90-1.00"

        buckets[key].append(row)

    print()
    print(f"H{horizon}")

    for key, bucket in buckets.items():

        if not bucket:
            print(
                f"  {key}: no samples"
            )
            continue

        acc = accuracy(bucket)

        print(
            f"  {key}: "
            f"n={len(bucket):4d} "
            f"accuracy={acc:.4f}"
        )


# =============================================================================
# 15. NULL / PERMUTATION TEST
# =============================================================================

section(15, "NULL / PERMUTATION TEST")

print(
    "The null test asks whether the observed prediction accuracy"
)
print(
    "is unusually high relative to randomized predictions."
)
print()

null_results = {h: [] for h in HORIZONS}

for horizon in HORIZONS:

    rows = all_results[horizon]

    if len(rows) < 20:
        print(
            f"H{horizon}: insufficient samples for null test."
        )
        continue

    actuals = [
        row["actual"]
        for row in rows
    ]

    predictions = [
        row["predicted"]
        for row in rows
    ]

    observed = accuracy(rows)

    # -------------------------------------------------------------------------
    # Preserve prediction class distribution.
    # Randomly shuffle predictions.
    # -------------------------------------------------------------------------

    rng = random.Random(
        RANDOM_SEED + horizon
    )

    for _ in range(NULL_REPETITIONS):

        shuffled = predictions.copy()

        rng.shuffle(shuffled)

        score = sum(
            shuffled[i] == actuals[i]
            for i in range(len(actuals))
        ) / len(actuals)

        null_results[horizon].append(score)

    mean_null = statistics.mean(
        null_results[horizon]
    )

    std_null = statistics.pstdev(
        null_results[horizon]
    )

    exceed = sum(
        score >= observed
        for score in null_results[horizon]
    )

    # +1 correction prevents p=0.
    p_value = (
        exceed + 1
    ) / (
        len(null_results[horizon]) + 1
    )

    z = (
        (observed - mean_null) / std_null
        if std_null > 0
        else float("inf")
    )

    print()
    print(f"H{horizon}")
    print(f"  observed accuracy : {observed:.6f}")
    print(f"  null mean         : {mean_null:.6f}")
    print(f"  null std          : {std_null:.6f}")
    print(f"  z-score           : {z:.4f}")
    print(f"  permutation p     : {p_value:.4f}")

    if p_value < 0.05:
        print(
            "  interpretation    : "
            "OBSERVED RESULT BEATS NULL AT 5% THRESHOLD"
        )
    else:
        print(
            "  interpretation    : "
            "NO SIGNIFICANT EVIDENCE AGAINST NULL"
        )


# =============================================================================
# 16. PREDICTIVE STABILITY ACROSS TIME
# =============================================================================

section(16, "TEMPORAL STABILITY")

for horizon in HORIZONS:

    rows = all_results[horizon]

    if len(rows) < 30:
        print(
            f"H{horizon}: insufficient samples."
        )
        continue

    chunks = []

    chunk_size = max(
        10,
        len(rows) // 5
    )

    for start in range(
        0,
        len(rows),
        chunk_size
    ):
        chunk = rows[
            start:start + chunk_size
        ]

        if chunk:
            chunks.append(chunk)

    print()
    print(f"H{horizon}")

    for i, chunk in enumerate(chunks, 1):

        print(
            f"  period {i}: "
            f"n={len(chunk):4d} "
            f"accuracy={accuracy(chunk):.4f} "
            f"balanced={balanced_accuracy(chunk):.4f}"
        )


# =============================================================================
# 17. RETRIEVAL SUPPORT QUALITY
# =============================================================================

section(17, "RETRIEVAL SUPPORT QUALITY")

for horizon in HORIZONS:

    rows = all_results[horizon]

    if not rows:
        continue

    supporting = []
    conflicting = []

    for query_index in [
        row["query_index"]
        for row in rows
    ]:

        try:

            train_end = query_index

            records = experience_fn(
                candles,
                atr,
                market_states,
                episode_ids,
                0,
                train_end,
                horizon,
            )

            if len(records) < MIN_RECORDS:
                continue

            result = retrieve_fn(
                market_states[query_index],
                records,
                horizon,
                query_index,
            )

            value = getattr(
                result,
                "supporting_matches",
                None
            )

            if value is not None:
                supporting.append(
                    int(value)
                )

            value = getattr(
                result,
                "conflicting_matches",
                None
            )

            if value is not None:
                conflicting.append(
                    int(value)
                )

        except Exception:
            pass

    if supporting:

        print()
        print(f"H{horizon}")

        print(
            "  mean supporting matches :",
            f"{statistics.mean(supporting):.2f}"
        )

        print(
            "  mean conflicting matches:",
            f"{statistics.mean(conflicting):.2f}"
        )


# =============================================================================
# 18. FINAL CLASSIFICATION
# =============================================================================

section(18, "FINAL SCIENTIFIC INTERPRETATION")

print()
print("This section does NOT change the source code.")
print()

overall_warning = False

for horizon in HORIZONS:

    rows = all_results[horizon]

    if not rows:
        print(
            f"H{horizon}: INSUFFICIENT DATA"
        )
        overall_warning = True
        continue

    mla = accuracy(rows)

    counts = {
        "UP": sum(
            r["actual"] == "UP"
            for r in rows
        ),
        "DOWN": sum(
            r["actual"] == "DOWN"
            for r in rows
        ),
        "NEUTRAL": sum(
            r["actual"] == "NEUTRAL"
            for r in rows
        ),
    }

    majority = max(
        counts,
        key=counts.get
    )

    baseline = sum(
        r["actual"] == majority
        for r in rows
    ) / len(rows)

    improvement = mla - baseline

    null_scores = null_results[horizon]

    if null_scores:

        mean_null = statistics.mean(
            null_scores
        )

        null_exceed = sum(
            score >= mla
            for score in null_scores
        )

        p = (
            null_exceed + 1
        ) / (
            len(null_scores) + 1
        )

    else:

        mean_null = float("nan")
        p = float("nan")

    print()
    print(
        f"H{horizon}:"
    )

    print(
        f"  MLAI accuracy       = {mla:.4f}"
    )

    print(
        f"  majority baseline   = {baseline:.4f}"
    )

    print(
        f"  improvement         = {improvement:+.4f}"
    )

    print(
        f"  null mean           = {mean_null:.4f}"
        if math.isfinite(mean_null)
        else "  null mean           = N/A"
    )

    print(
        f"  null p-value        = {p:.4f}"
        if math.isfinite(p)
        else "  null p-value        = N/A"
    )

    if improvement > 0 and p < 0.05:

        print(
            "  RESULT              = "
            "PROMISING EVIDENCE"
        )

    elif improvement > 0:

        print(
            "  RESULT              = "
            "IMPROVEMENT BUT NOT STATISTICALLY STRONG"
        )

    else:

        print(
            "  RESULT              = "
            "NO DEMONSTRATED PREDICTIVE ADVANTAGE"
        )


# =============================================================================
# 19. SOURCE INTEGRITY AFTER ENTIRE AUDIT
# =============================================================================

section(19, "POST-AUDIT SOURCE INTEGRITY")

source_after = MODULE_FILE.read_bytes()
data_after = data_path.read_bytes()

source_unchanged = (
    source_before == source_after
)

data_unchanged = (
    data_before == data_after
)

print(
    "v4.1.5 source unchanged:",
    source_unchanged
)

print(
    "market_data.bin unchanged:",
    data_unchanged
)

if not source_unchanged:
    print(
        "CRITICAL: SOURCE CHANGED DURING AUDIT"
    )

if not data_unchanged:
    print(
        "CRITICAL: DATA FILE CHANGED DURING AUDIT"
    )


# =============================================================================
# 20. FINAL SUMMARY
# =============================================================================

section(20, "FINAL AUDIT SUMMARY")

total_rows = sum(
    len(rows)
    for rows in all_results.values()
)

print()
print(
    "Total predictive query evaluations:",
    total_rows
)

print(
    "Temporal leakage violations:",
    sum(
        len(v)
        for v in temporal_violations.values()
    )
)

print(
    "Source modified:",
    not source_unchanged
)

print(
    "Data modified:",
    not data_unchanged
)

print()

if not source_unchanged or not data_unchanged:

    print(
        "FINAL VERDICT: CRITICAL SAFETY FAILURE"
    )

elif temporal_fail:

    print(
        "FINAL VERDICT: TEMPORAL LEAKAGE DETECTED"
    )

elif total_rows == 0:

    print(
        "FINAL VERDICT: INSUFFICIENT PREDICTIVE TEST DATA"
    )

else:

    print(
        "FINAL VERDICT: PREDICTIVE EVIDENCE AUDIT COMPLETE"
    )

print()
print("=" * 100)
print("NO SOURCE FIX WAS APPLIED.")
print("NO DATA FILE WAS MODIFIED.")
print("NO v4.1.6 WAS CREATED.")
print("=" * 100)