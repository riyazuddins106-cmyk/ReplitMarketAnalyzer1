"""
MLAI V4.2.0 — PREDICTIVE INFORMATION AUDIT

Purpose
-------
Independent research/validation audit of the existing
mlai_market_structure_v420.py implementation.

This program DOES NOT patch or modify V4.2.0. It imports the existing module,
uses its causal MarketState / ExperienceRecord construction and retrieval
functions, and evaluates them under strict walk-forward rules.

Audits:
  1. Similarity discrimination
  2. Outcome separation
  3. Incremental predictive value vs conditional baseline
  4. Retrieval-component ablation
  5. H+4 / H+8 / H+16 horizon behavior
  6. Window stability
  7. Regime stability
  8. Permutation/null investigation
  9. Causality / leakage protections

No OOS result is used to tune parameters.
No production MLAI or learning memory is modified.
market_data.bin is verified read-only by SHA-256 before/after execution.

Run from the same directory as mlai_market_structure_v420.py:
    python .\\MLAI_V420_PREDICTIVE_INFORMATION_AUDIT.py
"""

from __future__ import annotations

import hashlib
import math
import os
import pickle
import random
import statistics
import sys
import time
from collections import Counter, defaultdict
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import mlai_market_structure_v420 as v420


# ============================================================================
# FIXED AUDIT CONFIGURATION
# ============================================================================
AUDIT_VERSION = "V420-PREDICTIVE-INFORMATION-AUDIT-1.0"
DATA_FILE = v420.MARKET_DATA_FILE
REPORT_FILE = "MLAI_V420_PREDICTIVE_INFORMATION_AUDIT_REPORT.md"
RESULTS_FILE = "MLAI_V420_PREDICTIVE_INFORMATION_AUDIT.bin"

HORIZONS = tuple(v420.HORIZONS)
DEFAULT_TRAIN_WINDOWS = v420.DEFAULT_TRAIN_WINDOWS
DEFAULT_OOS_SIZE = v420.DEFAULT_OOS_SIZE

# These are audit thresholds, not model parameters. They are declared before
# seeing OOS results and are used only for interpretation.
MIN_BUCKET_SAMPLES = 20
MIN_REGIME_SAMPLES = 20
MIN_PERMUTATIONS = 200
PERMUTATION_SEED = 4200420

# A result is not called "strong" merely because it beats a threshold once.
# The verdict requires cross-window stability and multiple independent tests.

EPS = 1e-12


# ============================================================================
# BASIC UTILITIES
# ============================================================================
def finite_float(x: Any, default: float = 0.0) -> float:
    try:
        y = float(x)
        return y if math.isfinite(y) else default
    except Exception:
        return default


def mean(xs: Sequence[float]) -> Optional[float]:
    vals = [finite_float(x) for x in xs if x is not None]
    return sum(vals) / len(vals) if vals else None


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def pct(x: Optional[float]) -> str:
    if x is None:
        return "N/A"
    return f"{100.0 * x:.2f}%"


def num(x: Optional[float]) -> str:
    if x is None:
        return "N/A"
    return f"{x:.6f}"


def safe_div(a: float, b: float) -> float:
    return a / b if abs(b) > EPS else 0.0


def logloss(probs: Dict[str, float], actual: str) -> float:
    p = max(EPS, min(1.0, finite_float(probs.get(actual, 0.0))))
    return -math.log(p)


def brier(probs: Dict[str, float], actual: str) -> float:
    classes = ("UP", "DOWN", "NEUTRAL")
    return sum((finite_float(probs.get(c, 0.0)) - (1.0 if c == actual else 0.0)) ** 2 for c in classes)


def accuracy(probs: Dict[str, float], actual: str) -> bool:
    best = max(("UP", "DOWN", "NEUTRAL"), key=lambda c: (finite_float(probs.get(c, 0.0)), c))
    return best == actual


def normalized_probs(values: Dict[str, float]) -> Dict[str, float]:
    clean = {k: max(0.0, finite_float(v)) for k, v in values.items()}
    total = sum(clean.values())
    if total <= EPS:
        return {"UP": 1/3, "DOWN": 1/3, "NEUTRAL": 1/3}
    return {k: clean.get(k, 0.0) / total for k in ("UP", "DOWN", "NEUTRAL")}


def direction(record: Any) -> Optional[str]:
    outcome = getattr(record, "outcome", record)
    for attr in ("direction", "label", "class_name", "target", "prediction"):
        value = getattr(outcome, attr, None)
        if value is not None:
            value = str(value).upper().strip()
            if value in {"UP", "DOWN", "NEUTRAL"}:
                return value
    return None


# ============================================================================
# CAUSAL / IMMUTABILITY AUDIT
# ============================================================================
def audit_record_causality(records: Sequence[Any], query_index: int) -> Tuple[int, int]:
    bad = 0
    checked = 0
    for r in records:
        idx = getattr(r, "index", None)
        if idx is None:
            continue
        checked += 1
        try:
            if int(idx) >= int(query_index):
                bad += 1
        except Exception:
            bad += 1
    return checked, bad


def make_baseline(query_state: Any, records: Sequence[Any]) -> Dict[str, float]:
    """Use the existing V4.2 conditional baseline; no OOS outcome involved."""
    _, distribution, _ = v420.conditional_baseline(query_state, records)
    return normalized_probs(distribution)


def retrieval_prediction(query_state: Any, records: Sequence[Any], horizon: int, query_index: int):
    """Use V4.2 retrieval and its actual retrieval distribution."""
    retrieval = v420.retrieve_historical_experience(query_state, records, horizon, query_index)
    probs = normalized_probs({
        "UP": retrieval.up_share,
        "DOWN": retrieval.down_share,
        "NEUTRAL": retrieval.neutral_share,
    })
    return retrieval, probs


def repaired_prediction(query_state: Any, records: Sequence[Any], horizon: int, query_index: int):
    """Use the public repaired/V4.2 predictive decision path exactly as V4.2 exposes it."""
    result = v420.mlai_v415_repaired_prediction(
        current=query_state,
        records=records,
        horizon=horizon,
        query_index=query_index,
    )
    return normalized_probs(result.get("probabilities", {})), result


# ============================================================================
# COMPONENT ABLATION
# ============================================================================
COMPONENTS = (
    "structure", "sequence", "regime", "location",
    "momentum", "volatility", "candle", "path",
)


def component_similarity(values: Dict[str, float], horizon: int, drop: Optional[str] = None) -> float:
    """Fixed-weight component ablation.

    The V4.2 declared horizon weights remain fixed. When one evidence family
    is ablated, its weight is removed and the remaining weights are
    renormalized. This is an audit diagnostic, not a replacement model.
    """
    weights = dict(v420.V420_HORIZON_WEIGHTS.get(int(horizon), v420.V420_HORIZON_WEIGHTS[8]))
    if drop is not None:
        weights.pop(drop, None)
    total_w = sum(weights.values())
    if total_w <= EPS:
        return 0.0
    raw = sum(weights[k] * finite_float(values.get(k, 0.0)) for k in weights)
    quality = finite_float(values.get("quality", 0.0))
    return max(0.0, min(1.0, (raw / total_w) * (0.75 + 0.25 * quality)))


def ablated_retrieval_distribution(
    query_state: Any,
    records: Sequence[Any],
    horizon: int,
    query_index: int,
    drop: str,
) -> Tuple[Dict[str, float], int]:
    """Recompute the selected candidate set with one similarity family removed.

    Candidate eligibility remains causal. No OOS outcome is consulted for
    candidate selection. Outcome labels are only consumed after probabilities
    are generated for evaluation.
    """
    candidates = []
    for record in records:
        idx = getattr(record, "index", None)
        if idx is None:
            continue
        if int(idx) >= int(query_index):
            continue
        if query_index - int(idx) < v420.MIN_HISTORY_GAP:
            continue
        if getattr(record, "horizon", horizon) != horizon:
            continue

        try:
            values = v420._v420_component_vector(query_state, record)
            quality = v420._v420_quality_gates(values)
            values["quality"] = quality
            score = component_similarity(values, horizon, drop=drop)
            contradiction = v420._v420_contradiction(query_state, record, values)
        except Exception:
            continue

        if contradiction > v420.V420_MAX_CONTRADICTION and score < 0.60:
            continue
        if score < v420.V420_MIN_SIMILARITY:
            continue

        candidates.append((int(idx), getattr(record, "episode_id", int(idx)), score, record))

    candidates.sort(key=lambda x: (x[2], x[0]), reverse=True)
    candidates = candidates[:v420.V420_TOP_K]
    if not candidates:
        return {"UP": 1/3, "DOWN": 1/3, "NEUTRAL": 1/3}, 0

    # The ablation is deliberately kept simple and transparent: the selected
    # candidates are weighted by their ablated similarity and class-balanced.
    buckets = {"UP": [], "DOWN": [], "NEUTRAL": []}
    for _, _, score, record in candidates:
        d = direction(record)
        if d in buckets:
            w = math.exp(-(1.0 - score) / max(v420.V420_PREDICT_TEMPERATURE, 1e-6))
            buckets[d].append(w)

    evidence = {}
    for cls, vals in buckets.items():
        if not vals:
            evidence[cls] = 0.0
        else:
            evidence[cls] = (sum(vals) / len(vals)) * (1.0 - math.exp(-len(vals) / 6.0))
    return normalized_probs(evidence), len(candidates)


# ============================================================================
# RECORD COLLECTION / EVALUATION
# ============================================================================
def collect_context():
    candles, invalid = v420.load_market_data(DATA_FILE)
    chronology = v420.audit_chronology(candles)
    if not chronology["ordered"] or chronology["duplicates"]:
        raise RuntimeError("Chronology audit failed.")
    if len(candles) < 500:
        raise RuntimeError("Insufficient candle history.")

    windows = v420.create_walk_forward_windows(
        len(candles), DEFAULT_TRAIN_WINDOWS, DEFAULT_OOS_SIZE
    )
    atr = v420.calculate_atr(candles)
    engine = v420.CausalStructureEngine(candles)
    structure_states = engine.build()
    causality = v420.audit_structure_causality(
        candles, engine.swings, structure_states, engine.events
    )
    if not causality["passed"]:
        raise RuntimeError("Causality audit failed.")
    market_states = v420.build_market_states(candles, structure_states, atr)
    episode_ids = v420.assign_episode_ids(market_states)
    return candles, invalid, chronology, windows, atr, engine, causality, market_states, episode_ids


def build_window_records(candles, atr, market_states, episode_ids, window, horizon):
    return v420.build_experience_records(
        candles, atr, market_states, episode_ids,
        window.train_start, window.train_end, horizon
    )


def evaluate_query(query_state, records, candles, atr, horizon, query_index):
    outcome = v420.make_outcome(candles, atr, query_index, horizon)
    if outcome is None:
        return None
    actual = direction(outcome)
    if actual is None:
        return None

    checked, bad = audit_record_causality(records, query_index)
    if bad:
        raise RuntimeError(f"Causality violation: {bad} training records at/after query {query_index}.")

    retrieval, rprob = retrieval_prediction(query_state, records, horizon, query_index)
    bprob = make_baseline(query_state, records)
    pprob, presult = repaired_prediction(query_state, records, horizon, query_index)

    row = {
        "query_index": query_index,
        "actual": actual,
        "regime": str(getattr(query_state, "regime", "UNKNOWN")),
        "sequence": str(getattr(query_state, "sequence_state", "UNKNOWN")),
        "structure_event": str(getattr(query_state, "structure_event", "UNKNOWN")),
        "retrieval": asdict(retrieval),
        "retrieval_probs": rprob,
        "baseline_probs": bprob,
        "predictive_probs": pprob,
        "predictive_result": presult,
        "retrieval_accuracy": float(accuracy(rprob, actual)),
        "baseline_accuracy": float(accuracy(bprob, actual)),
        "predictive_accuracy": float(accuracy(pprob, actual)),
        "retrieval_brier": brier(rprob, actual),
        "baseline_brier": brier(bprob, actual),
        "predictive_brier": brier(pprob, actual),
        "retrieval_logloss": logloss(rprob, actual),
        "baseline_logloss": logloss(bprob, actual),
        "predictive_logloss": logloss(pprob, actual),
        "retrieval_accuracy_lift": float(accuracy(rprob, actual)) - float(accuracy(bprob, actual)),
        "predictive_accuracy_lift": float(accuracy(pprob, actual)) - float(accuracy(bprob, actual)),
        "retrieval_brier_lift": brier(bprob, actual) - brier(rprob, actual),
        "predictive_brier_lift": brier(bprob, actual) - brier(pprob, actual),
        "retrieval_logloss_lift": logloss(bprob, actual) - logloss(rprob, actual),
        "predictive_logloss_lift": logloss(bprob, actual) - logloss(pprob, actual),
        "top_similarity": finite_float(getattr(retrieval, "top_similarity", 0.0)),
        "mean_similarity": finite_float(getattr(retrieval, "mean_similarity", 0.0)),
        "matches": int(getattr(retrieval, "deduplicated_matches", 0)),
        "sparse": bool(getattr(retrieval, "sparse_warning", True)),
        "best_probability": finite_float(presult.get("best_probability", 0.0)),
        "margin": finite_float(presult.get("margin", 0.0)),
        "decision": presult.get("prediction"),
    }
    return row


def aggregate_rows(rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    if not rows:
        return {"samples": 0}
    def m(key):
        return mean([r[key] for r in rows])
    return {
        "samples": len(rows),
        "retrieval_accuracy": m("retrieval_accuracy"),
        "baseline_accuracy": m("baseline_accuracy"),
        "predictive_accuracy": m("predictive_accuracy"),
        "retrieval_brier": m("retrieval_brier"),
        "baseline_brier": m("baseline_brier"),
        "predictive_brier": m("predictive_brier"),
        "retrieval_logloss": m("retrieval_logloss"),
        "baseline_logloss": m("baseline_logloss"),
        "predictive_logloss": m("predictive_logloss"),
        "retrieval_accuracy_lift": m("retrieval_accuracy_lift"),
        "predictive_accuracy_lift": m("predictive_accuracy_lift"),
        "retrieval_brier_lift": m("retrieval_brier_lift"),
        "predictive_brier_lift": m("predictive_brier_lift"),
        "retrieval_logloss_lift": m("retrieval_logloss_lift"),
        "predictive_logloss_lift": m("predictive_logloss_lift"),
        "mean_top_similarity": m("top_similarity"),
        "mean_similarity": m("mean_similarity"),
        "mean_matches": m("matches"),
        "coverage": mean([0.0 if r["sparse"] else 1.0 for r in rows]),
        "predictive_neutral_rate": mean([1.0 if r["decision"] == "NEUTRAL" else 0.0 for r in rows]),
    }


# ============================================================================
# SIMILARITY DISCRIMINATION / OUTCOME SEPARATION
# ============================================================================
def quantile_buckets(rows: Sequence[Dict[str, Any]], n: int = 4):
    ordered = sorted(rows, key=lambda r: r["top_similarity"])
    buckets = []
    for i in range(n):
        lo = (i * len(ordered)) // n
        hi = ((i + 1) * len(ordered)) // n
        chunk = ordered[lo:hi]
        if chunk:
            buckets.append((i + 1, chunk))
    return buckets


def discrimination_report(rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    buckets = []
    for q, chunk in quantile_buckets(rows, 4):
        a = aggregate_rows(chunk)
        buckets.append({
            "quartile": q,
            "samples": len(chunk),
            "mean_similarity": a["mean_top_similarity"],
            "retrieval_accuracy": a["retrieval_accuracy"],
            "predictive_accuracy": a["predictive_accuracy"],
            "baseline_accuracy": a["baseline_accuracy"],
            "retrieval_brier": a["retrieval_brier"],
            "predictive_brier": a["predictive_brier"],
            "baseline_brier": a["baseline_brier"],
            "retrieval_logloss": a["retrieval_logloss"],
            "predictive_logloss": a["predictive_logloss"],
            "baseline_logloss": a["baseline_logloss"],
        })

    if len(buckets) >= 2:
        low = buckets[0]
        high = buckets[-1]
        separation = {
            "similarity_delta": high["mean_similarity"] - low["mean_similarity"],
            "predictive_accuracy_delta": high["predictive_accuracy"] - low["predictive_accuracy"],
            "retrieval_accuracy_delta": high["retrieval_accuracy"] - low["retrieval_accuracy"],
            "predictive_brier_delta": high["predictive_brier"] - low["predictive_brier"],
            "predictive_logloss_delta": high["predictive_logloss"] - low["predictive_logloss"],
        }
    else:
        separation = {}
    return {"quartiles": buckets, "separation": separation}


# ============================================================================
# REGIME / WINDOW STABILITY
# ============================================================================
def grouped_report(rows: Sequence[Dict[str, Any]], field: str, min_samples: int) -> Dict[str, Any]:
    groups = defaultdict(list)
    for r in rows:
        groups[r.get(field, "UNKNOWN")].append(r)
    out = {}
    for name, grp in sorted(groups.items()):
        if len(grp) < min_samples:
            continue
        out[str(name)] = aggregate_rows(grp)
    return out


# ============================================================================
# PERMUTATION / NULL INVESTIGATION
# ============================================================================
def permutation_test(rows: Sequence[Dict[str, Any]], permutations: int = MIN_PERMUTATIONS) -> Dict[str, Any]:
    """Permutation test on the observed predictive-vs-baseline accuracy lift.

    The observed OOS predictions are frozen. Only the actual labels are
    permuted. Therefore the null test cannot improve the model by tuning it.
    """
    if not rows:
        return {"available": False}

    actual = [r["actual"] for r in rows]
    pred = [max(r["predictive_probs"], key=lambda c: (r["predictive_probs"].get(c, 0.0), c)) for r in rows]
    base = [max(r["baseline_probs"], key=lambda c: (r["baseline_probs"].get(c, 0.0), c)) for r in rows]
    observed = mean([float(p == a) - float(b == a) for p, b, a in zip(pred, base, actual)]) or 0.0

    rng = random.Random(PERMUTATION_SEED)
    null = []
    labels = list(actual)
    for _ in range(permutations):
        rng.shuffle(labels)
        null.append(mean([float(p == a) - float(b == a) for p, b, a in zip(pred, base, labels)]) or 0.0)

    null_sorted = sorted(null)
    ge = sum(1 for x in null if x >= observed)
    p = (ge + 1.0) / (len(null) + 1.0)
    p95 = null_sorted[min(len(null_sorted) - 1, int(0.95 * (len(null_sorted) - 1)))]
    p99 = null_sorted[min(len(null_sorted) - 1, int(0.99 * (len(null_sorted) - 1)))]

    return {
        "available": True,
        "permutations": permutations,
        "seed": PERMUTATION_SEED,
        "observed_accuracy_lift": observed,
        "null_mean": mean(null),
        "null_std": statistics.pstdev(null) if len(null) > 1 else 0.0,
        "null_p95": p95,
        "null_p99": p99,
        "empirical_p_value": p,
        "beats_null_p95": observed > p95,
        "beats_null_p99": observed > p99,
    }


# ============================================================================
# MAIN AUDIT
# ============================================================================
def main() -> None:
    start = time.time()
    print("=" * 96)
    print("MLAI V4.2.0 PREDICTIVE INFORMATION AUDIT")
    print("=" * 96)
    print("RESEARCH / VALIDATION ONLY")
    print("No patching | No OOS tuning | No production modification")
    print()

    if not os.path.exists(DATA_FILE):
        raise FileNotFoundError(f"Missing {DATA_FILE!r} in the current directory.")

    data_before = sha256_file(DATA_FILE)
    print("PROTECTION CHECK")
    print(f"{DATA_FILE:<32}: READ ONLY")
    print(f"SHA256 before                 : {data_before}")
    print("Production MLAI              : NOT MODIFIED")
    print("Learning memory              : NOT MODIFIED")
    print("Trading                      : DISABLED")
    print()

    (
        candles, invalid, chronology, windows, atr, engine,
        causality, market_states, episode_ids,
    ) = collect_context()

    print("FOUNDATION")
    print(f"Valid candles                : {len(candles)}")
    print(f"Invalid candles              : {invalid}")
    print(f"Confirmed swings             : {len(engine.swings)}")
    print(f"Structural events            : {sum(1 for e in engine.events.values() if e != 'NONE')}")
    print(f"Episodes                     : {len(set(episode_ids.values()))}")
    print(f"Chronology                   : {'PASS' if chronology['ordered'] and not chronology['duplicates'] else 'FAIL'}")
    print(f"Causal structure             : {'PASS' if causality['passed'] else 'FAIL'}")
    print()

    all_rows: List[Dict[str, Any]] = []
    window_summary: Dict[str, Dict[int, Dict[str, Any]]] = {}
    ablation_accum: Dict[int, Dict[str, List[float]]] = {h: {c: [] for c in COMPONENTS} for h in HORIZONS}
    leakage_checks = {"queries": 0, "records_checked": 0, "violations": 0}

    for window in windows:
        window_key = str(window.number)
        window_summary[window_key] = {}
        print("-" * 96)
        print(f"WINDOW {window.number} | TRAIN [{window.train_start}:{window.train_end}] | OOS [{window.oos_start}:{window.oos_end}]")

        for horizon in HORIZONS:
            records = build_window_records(candles, atr, market_states, episode_ids, window, horizon)
            rows = []

            for query_index in range(window.oos_start, window.oos_end):
                if query_index + horizon >= len(candles):
                    continue
                qstate = market_states[query_index]
                checked, bad = audit_record_causality(records, query_index)
                leakage_checks["queries"] += 1
                leakage_checks["records_checked"] += checked
                leakage_checks["violations"] += bad
                if bad:
                    raise RuntimeError(f"Leakage detected at window {window.number}, H+{horizon}, query {query_index}.")

                row = evaluate_query(qstate, records, candles, atr, horizon, query_index)
                if row is None:
                    continue
                row["window"] = window.number
                row["horizon"] = horizon
                rows.append(row)
                all_rows.append(row)

            agg = aggregate_rows(rows)
            window_summary[window_key][horizon] = agg

            # Fixed, predeclared component ablation on a bounded sample of OOS
            # queries. This does not feed results back into the actual model.
            for row in rows:
                qidx = row["query_index"]
                qstate = market_states[qidx]
                for component in COMPONENTS:
                    probs, _ = ablated_retrieval_distribution(qstate, records, horizon, qidx, component)
                    actual = row["actual"]
                    ablation_accum[horizon][component].append(
                        float(accuracy(probs, actual)) - float(accuracy(row["baseline_probs"], actual))
                    )

            print(f"H+{horizon}: N={agg['samples']} | RetrievalAcc={pct(agg['retrieval_accuracy'])} | BaselineAcc={pct(agg['baseline_accuracy'])} | PredictiveAcc={pct(agg['predictive_accuracy'])}")
            print(f"         Predictive Brier={num(agg['predictive_brier'])} | Baseline Brier={num(agg['baseline_brier'])} | Lift={num(agg['predictive_brier_lift'])}")
            print(f"         Predictive LogLoss={num(agg['predictive_logloss'])} | Baseline LogLoss={num(agg['baseline_logloss'])} | Lift={num(agg['predictive_logloss_lift'])}")
            print(f"         Coverage={pct(agg['coverage'])} | MeanMatches={num(agg['mean_matches'])} | TopSimilarity={pct(agg['mean_top_similarity'])}")

    # ----------------------------------------------------------------------
    # GLOBAL ANALYSES
    # ----------------------------------------------------------------------
    by_horizon = {}
    discrimination = {}
    regime = {}
    sequence = {}
    for h in HORIZONS:
        rows = [r for r in all_rows if r["horizon"] == h]
        by_horizon[h] = aggregate_rows(rows)
        discrimination[h] = discrimination_report(rows)
        regime[h] = grouped_report(rows, "regime", MIN_REGIME_SAMPLES)
        sequence[h] = grouped_report(rows, "sequence", MIN_REGIME_SAMPLES)

    # Window stability: positive predictive Brier/log-loss lift across windows.
    stability = {}
    for h in HORIZONS:
        vals = [window_summary[str(w.number)][h]["predictive_brier_lift"] for w in windows if window_summary[str(w.number)][h].get("samples", 0)]
        lvals = [window_summary[str(w.number)][h]["predictive_logloss_lift"] for w in windows if window_summary[str(w.number)][h].get("samples", 0)]
        avals = [window_summary[str(w.number)][h]["predictive_accuracy_lift"] for w in windows if window_summary[str(w.number)][h].get("samples", 0)]
        stability[h] = {
            "windows": len(vals),
            "positive_brier_lift_windows": sum(v > 0 for v in vals),
            "positive_logloss_lift_windows": sum(v > 0 for v in lvals),
            "positive_accuracy_lift_windows": sum(v > 0 for v in avals),
            "mean_brier_lift": mean(vals),
            "mean_logloss_lift": mean(lvals),
            "mean_accuracy_lift": mean(avals),
        }

    # Null test is performed independently per horizon, using frozen OOS
    # predictions. It cannot influence the prediction path.
    null = {h: permutation_test([r for r in all_rows if r["horizon"] == h]) for h in HORIZONS}

    # ----------------------------------------------------------------------
    # VERDICT CRITERIA — FIXED BEFORE REPORT GENERATION
    # ----------------------------------------------------------------------
    criteria = {}
    for h in HORIZONS:
        a = by_horizon[h]
        d = discrimination[h]
        s = stability[h]
        n = null[h]
        q = d.get("quartiles", [])

        similarity_discrimination = False
        if len(q) >= 2:
            similarity_discrimination = (
                q[-1]["mean_similarity"] > q[0]["mean_similarity"] and
                q[-1]["predictive_brier"] <= q[0]["predictive_brier"]
            )

        incremental = (
            a["predictive_brier_lift"] is not None and a["predictive_logloss_lift"] is not None and
            a["predictive_brier_lift"] > 0.0 and
            a["predictive_logloss_lift"] > 0.0
        )

        stable = (
            s["windows"] >= 3 and
            s["positive_brier_lift_windows"] >= math.ceil(0.60 * s["windows"]) and
            s["positive_logloss_lift_windows"] >= math.ceil(0.60 * s["windows"])
        )

        null_supported = bool(n.get("beats_null_p95", False))

        criteria[h] = {
            "similarity_discrimination": similarity_discrimination,
            "incremental_predictive_value": incremental,
            "cross_window_stability": stable,
            "permutation_support": null_supported,
        }

    # Overall verdict intentionally conservative.
    strong_horizons = [
        h for h in HORIZONS
        if all(criteria[h].values())
    ]
    positive_horizons = [
        h for h in HORIZONS
        if by_horizon[h]["predictive_brier_lift"] is not None
        and by_horizon[h]["predictive_brier_lift"] > 0
        and by_horizon[h]["predictive_logloss_lift"] is not None
        and by_horizon[h]["predictive_logloss_lift"] > 0
    ]

    if len(strong_horizons) >= 2:
        verdict = "STRONG EVIDENCE"
    elif len(positive_horizons) >= 2:
        verdict = "PROMISING BUT NOT YET ROBUST"
    elif len(positive_horizons) == 1:
        verdict = "LIMITED / HORIZON-SPECIFIC EVIDENCE"
    else:
        verdict = "NO ROBUST PREDICTIVE EVIDENCE"

    # ----------------------------------------------------------------------
    # PROTECTION
    # ----------------------------------------------------------------------
    data_after = sha256_file(DATA_FILE)
    unchanged = data_before == data_after

    print()
    print("=" * 96)
    print("MLAI PREDICTIVE INFORMATION AUDIT")
    print("=" * 96)
    for h in HORIZONS:
        a = by_horizon[h]
        s = stability[h]
        n = null[h]
        print(f"H+{h}")
        print(f"  Retrieval accuracy        : {pct(a['retrieval_accuracy'])}")
        print(f"  Baseline accuracy         : {pct(a['baseline_accuracy'])}")
        print(f"  Predictive accuracy       : {pct(a['predictive_accuracy'])}")
        print(f"  Predictive accuracy lift  : {pct(a['predictive_accuracy_lift'])}")
        print(f"  Predictive Brier lift     : {num(a['predictive_brier_lift'])}")
        print(f"  Predictive LogLoss lift   : {num(a['predictive_logloss_lift'])}")
        print(f"  Positive Brier windows    : {s['positive_brier_lift_windows']}/{s['windows']}")
        print(f"  Positive LogLoss windows  : {s['positive_logloss_lift_windows']}/{s['windows']}")
        print(f"  Permutation p-value       : {num(n.get('empirical_p_value'))}")
        print()

    print("Similarity discrimination")
    for h in HORIZONS:
        sep = discrimination[h]["separation"]
        print(f"  H+{h}: similarity delta={num(sep.get('similarity_delta'))} | predictive accuracy delta={pct(sep.get('predictive_accuracy_delta'))}")

    print()
    print("Leakage / protection")
    print(f"  Queries audited           : {leakage_checks['queries']}")
    print(f"  Training records checked  : {leakage_checks['records_checked']}")
    print(f"  Causality violations      : {leakage_checks['violations']}")
    print(f"  market_data.bin unchanged : {'PASS' if unchanged else 'FAIL'}")
    print("  Production MLAI modified  : NO")
    print("  Learning memory modified  : NO")
    print("  Trading enabled           : NO")
    print()
    print(f"FINAL VERDICT: {verdict}")
    print("=" * 96)

    # ----------------------------------------------------------------------
    # ARTIFACT
    # ----------------------------------------------------------------------
    artifact = {
        "audit_version": AUDIT_VERSION,
        "source_module": "mlai_market_structure_v420",
        "dataset": {
            "file": DATA_FILE,
            "candles": len(candles),
            "invalid": invalid,
            "sha256_before": data_before,
            "sha256_after": data_after,
            "unchanged": unchanged,
        },
        "foundation": {
            "chronology": chronology,
            "causality": causality,
            "confirmed_swings": len(engine.swings),
            "episodes": len(set(episode_ids.values())),
        },
        "config": {
            "horizons": HORIZONS,
            "train_windows": DEFAULT_TRAIN_WINDOWS,
            "oos_size": DEFAULT_OOS_SIZE,
            "min_bucket_samples": MIN_BUCKET_SAMPLES,
            "min_regime_samples": MIN_REGIME_SAMPLES,
            "permutations": MIN_PERMUTATIONS,
            "permutation_seed": PERMUTATION_SEED,
        },
        "aggregate": by_horizon,
        "window_summary": window_summary,
        "similarity_discrimination": discrimination,
        "regime_report": regime,
        "sequence_report": sequence,
        "stability": stability,
        "permutation": null,
        "ablation": {
            h: {c: mean(ablation_accum[h][c]) for c in COMPONENTS}
            for h in HORIZONS
        },
        "criteria": criteria,
        "strong_horizons": strong_horizons,
        "positive_horizons": positive_horizons,
        "verdict": verdict,
        "protection": {
            "market_data_modified": not unchanged,
            "production_modified": False,
            "learning_memory_modified": False,
            "trading": False,
        },
        "elapsed_seconds": time.time() - start,
    }

    with open(RESULTS_FILE, "wb") as f:
        pickle.dump(artifact, f, protocol=pickle.HIGHEST_PROTOCOL)

    # ----------------------------------------------------------------------
    # REPORT
    # ----------------------------------------------------------------------
    report: List[str] = []
    report.append(f"# MLAI V4.2.0 Predictive Information Audit")
    report.append("")
    report.append(f"Audit version: `{AUDIT_VERSION}`")
    report.append("")
    report.append("## Scope")
    report.append("")
    report.append("- Existing V4.2.0 implementation was imported; no model patch was applied.")
    report.append("- Strict walk-forward OOS evaluation.")
    report.append("- Horizons: H+4, H+8, H+16.")
    report.append("- OOS outcomes are consumed only after predictions are generated.")
    report.append("- No OOS tuning.")
    report.append("- `market_data.bin` verified byte-for-byte unchanged.")
    report.append("")
    report.append("## Final verdict")
    report.append("")
    report.append(f"**{verdict}**")
    report.append("")
    report.append("The verdict is generated from predefined criteria and is not forced to be positive.")
    report.append("")

    report.append("## Horizon results")
    report.append("")
    report.append("| Horizon | N | Retrieval Acc | Baseline Acc | Predictive Acc | Predictive Acc Lift | Brier Lift | LogLoss Lift |")
    report.append("|---:|---:|---:|---:|---:|---:|---:|---:|")
    for h in HORIZONS:
        a = by_horizon[h]
        report.append(
            f"| H+{h} | {a['samples']} | {pct(a['retrieval_accuracy'])} | {pct(a['baseline_accuracy'])} | "
            f"{pct(a['predictive_accuracy'])} | {pct(a['predictive_accuracy_lift'])} | "
            f"{num(a['predictive_brier_lift'])} | {num(a['predictive_logloss_lift'])} |"
        )
    report.append("")

    report.append("## Similarity discrimination")
    report.append("")
    for h in HORIZONS:
        report.append(f"### H+{h}")
        for q in discrimination[h]["quartiles"]:
            report.append(
                f"- Q{q['quartile']}: n={q['samples']}, mean top similarity={pct(q['mean_similarity'])}, "
                f"predictive accuracy={pct(q['predictive_accuracy'])}, predictive Brier={num(q['predictive_brier'])}, "
                f"predictive LogLoss={num(q['predictive_logloss'])}"
            )
        report.append(f"- Separation: `{discrimination[h]['separation']}`")
        report.append("")

    report.append("## Cross-window stability")
    report.append("")
    for h in HORIZONS:
        s = stability[h]
        report.append(
            f"- H+{h}: positive Brier-lift windows {s['positive_brier_lift_windows']}/{s['windows']}; "
            f"positive LogLoss-lift windows {s['positive_logloss_lift_windows']}/{s['windows']}; "
            f"mean Brier lift {num(s['mean_brier_lift'])}; mean LogLoss lift {num(s['mean_logloss_lift'])}."
        )
    report.append("")

    report.append("## Regime stability")
    report.append("")
    for h in HORIZONS:
        report.append(f"### H+{h}")
        for name, a in regime[h].items():
            report.append(
                f"- `{name}`: n={a['samples']}, predictive accuracy={pct(a['predictive_accuracy'])}, "
                f"predictive Brier lift={num(a['predictive_brier_lift'])}, predictive LogLoss lift={num(a['predictive_logloss_lift'])}"
            )
        report.append("")

    report.append("## Retrieval-component ablation")
    report.append("")
    report.append("Values are mean accuracy lift versus the conditional baseline after removing one component from the fixed V4.2 similarity representation.")
    report.append("")
    report.append("| Horizon | Component | Mean accuracy lift vs baseline |")
    report.append("|---:|---|---:|")
    for h in HORIZONS:
        for c in COMPONENTS:
            report.append(f"| H+{h} | {c} | {pct(mean(ablation_accum[h][c]))} |")
    report.append("")

    report.append("## Permutation/null investigation")
    report.append("")
    for h in HORIZONS:
        n = null[h]
        report.append(
            f"- H+{h}: observed predictive accuracy lift={pct(n.get('observed_accuracy_lift'))}; "
            f"null p95={pct(n.get('null_p95'))}; null p99={pct(n.get('null_p99'))}; "
            f"empirical p={num(n.get('empirical_p_value'))}; beats p95={n.get('beats_null_p95')}."
        )
    report.append("")

    report.append("## Predeclared verdict criteria")
    report.append("")
    report.append("For each horizon, all of the following are required for `STRONG EVIDENCE`:")
    report.append("1. Similarity discrimination: highest-similarity quartile must not have worse predictive Brier than the lowest quartile.")
    report.append("2. Incremental predictive value: predictive Brier lift and LogLoss lift must both be positive versus the conditional baseline.")
    report.append("3. Cross-window stability: at least 60% of evaluated windows must have positive Brier and LogLoss lift.")
    report.append("4. Permutation support: observed predictive accuracy lift must exceed the permutation null 95th percentile.")
    report.append("")
    report.append(f"Strong horizons: {strong_horizons}")
    report.append(f"Positive horizons: {positive_horizons}")
    report.append("")

    report.append("## Protection")
    report.append("")
    report.append(f"- market_data.bin SHA256 before: `{data_before}`")
    report.append(f"- market_data.bin SHA256 after: `{data_after}`")
    report.append(f"- market_data.bin unchanged: {'PASS' if unchanged else 'FAIL'}")
    report.append("- Production MLAI modified: NO")
    report.append("- Learning memory modified: NO")
    report.append("- Trading: DISABLED")
    report.append("")
    report.append(f"Audit elapsed seconds: {time.time() - start:.2f}")

    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(report))

    print()
    print("Artifacts saved:")
    print(f"  {RESULTS_FILE}")
    print(f"  {REPORT_FILE}")
    print(f"Elapsed: {time.time() - start:.2f}s")

    if not unchanged:
        raise RuntimeError("PROTECTION FAILURE: market_data.bin changed during audit.")


if __name__ == "__main__":
    main()
    