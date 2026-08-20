"""
MLAI V4.2.0 — DEFINITIVE RETRIEVAL FORENSIC REPAIR
====================================================

Research-only candidate evaluator.

This program:
  * never modifies mlai_market_structure_v420.py
  * never modifies market_data.bin
  * never uses OOS outcomes for model/configuration selection
  * enforces a causal record boundary for EVERY query, including inner
    validation and calibration
  * fixes the V4.2.0 forensic-repair runtime defects
  * uses the existing V4.2 causal state/component representation
  * performs nested chronological model selection
  * uses a disjoint training calibration slice
  * evaluates frozen predictions on untouched OOS windows
  * compares against a genuinely causal conditional baseline
  * reports similarity discrimination, outcome separation, incremental
    predictive value, horizon behaviour, stability and permutation tests

IMPORTANT:
A successful run does NOT guarantee that retrieval is predictive.
The only acceptable "genuine predictive result" is one that survives the
frozen OOS tests. A negative result is a valid result.

Run:
    python MLAI_V420_RETRIEVAL_FORENSIC_REPAIR_DEFINITIVE.py
"""

from __future__ import annotations

import hashlib
import math
import os
import pickle
import random
import statistics
import time
from collections import Counter
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

import mlai_market_structure_v420 as v420


# ============================================================================
# FIXED RESEARCH CONFIGURATION
# ============================================================================

VERSION = "V420-DEFINITIVE-RETRIEVAL-FORENSIC-REPAIR-FAST-3.0"

DATA_FILE = v420.MARKET_DATA_FILE
REPORT_FILE = "MLAI_V420_RETRIEVAL_FORENSIC_REPAIR_DEFINITIVE_REPORT.md"
ARTIFACT_FILE = "MLAI_V420_RETRIEVAL_FORENSIC_REPAIR_DEFINITIVE.bin"

HORIZONS = tuple(v420.HORIZONS)
TRAIN_WINDOWS = v420.DEFAULT_TRAIN_WINDOWS
OOS_SIZE = v420.DEFAULT_OOS_SIZE

CLASSES = ("UP", "DOWN", "NEUTRAL")
EPS = 1e-12

# Deliberately smaller than the failed 324-combination search.
# The objective is robustness, not brute-force tuning.
# 36 configurations: deliberately small enough to remain responsive while
# still spanning K, temporal decay, regime handling, and representation.
K_GRID = (8, 16, 24)
HALFLIFE_GRID = (None, 100.0)
REGIME_GRID = ("none", "soft")
POLICY_GRID = ("balanced", "structure_first", "context_first")

MIN_INNER_TRAIN = 50
MIN_INNER_VALIDATION = 30
MIN_CALIBRATION = 30

# The last part of the training window is reserved for calibration.
CALIBRATION_FRACTION = 0.20

# Similarity threshold is fixed and deliberately not OOS-tuned.
MIN_SIMILARITY = float(getattr(v420, "V420_MIN_SIMILARITY", 0.42))
MIN_MATCHES = 5

# Fixed probabilistic shrinkage candidates for training calibration.
SHRINK_GRID = (0.0, 0.15, 0.25, 0.35, 0.50)
TEMP_GRID = (0.80, 1.0, 1.20, 1.50)

PERMUTATIONS = 250
PERMUTATION_SEED = 4200420

BOOTSTRAPS = 500
BOOTSTRAP_SEED = 420420

FEATURES = (
    "structure", "sequence", "regime", "location",
    "momentum", "volatility", "candle", "path",
)


# ============================================================================
# UTILITIES
# ============================================================================

def finite(x: Any, default: float = 0.0) -> float:
    try:
        y = float(x)
        return y if math.isfinite(y) else default
    except Exception:
        return default


def mean(xs: Sequence[float]) -> Optional[float]:
    vals = [finite(x) for x in xs if x is not None]
    return sum(vals) / len(vals) if vals else None


def safe_div(a: float, b: float) -> float:
    return a / b if abs(b) > EPS else 0.0


def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, finite(x)))


def normalize(p: Dict[str, float]) -> Dict[str, float]:
    q = {c: max(0.0, finite(p.get(c, 0.0))) for c in CLASSES}
    s = sum(q.values())
    if s <= EPS:
        return {c: 1.0 / 3.0 for c in CLASSES}
    return {c: q[c] / s for c in CLASSES}


def accuracy(p: Dict[str, float], actual: str) -> float:
    pred = max(CLASSES, key=lambda c: (finite(p.get(c, 0.0)), c))
    return float(pred == actual)


def brier(p: Dict[str, float], actual: str) -> float:
    return sum(
        (finite(p.get(c, 0.0)) - float(c == actual)) ** 2
        for c in CLASSES
    )


def logloss(p: Dict[str, float], actual: str) -> float:
    return -math.log(max(EPS, min(1.0, finite(p.get(actual, 0.0)))))


def entropy(p: Dict[str, float]) -> float:
    q = normalize(p)
    return -sum(q[c] * math.log(max(EPS, q[c])) for c in CLASSES)


def direction(record: Any) -> Optional[str]:
    outcome = getattr(record, "outcome", record)
    for attr in ("direction", "label", "class_name", "target", "prediction"):
        value = getattr(outcome, attr, None)
        if value is not None:
            value = str(value).upper().strip()
            if value in CLASSES:
                return value
    return None


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


# ============================================================================
# CAUSAL BOUNDARY — THIS IS THE CRITICAL REPAIR
# ============================================================================

def causal_records(
    records: Sequence[Any],
    query_index: int,
    horizon: int,
) -> List[Any]:
    """
    Return ONLY records whose complete outcome was known before the query.

    A record at t contains an outcome covering t+1 ... t+horizon.
    Therefore its label is available to a query at q only when:

        t + horizon <= q

    This is stronger than merely checking t < q.

    It also prevents inner validation from seeing labels from later in the
    validation period.
    """
    minimum_gap = max(
        int(getattr(v420, "MIN_HISTORY_GAP", horizon)),
        int(horizon),
    )

    out = []
    for r in records:
        idx = getattr(r, "index", None)
        if idx is None:
            continue
        idx = int(idx)

        if getattr(r, "horizon", horizon) != horizon:
            continue

        if idx + horizon > query_index:
            continue

        if query_index - idx < minimum_gap:
            continue

        if direction(r) not in CLASSES:
            continue

        out.append(r)

    return out


# ============================================================================
# CAUSAL BASELINE
# ============================================================================

def causal_baseline(
    current: Any,
    records: Sequence[Any],
    query_index: int,
    horizon: int,
) -> Dict[str, float]:
    """
    Existing V4.2 conditional baseline, but with a hard causal record fence.

    The original forensic script could call conditional_baseline() on the
    entire training record set during inner validation. That comparator can
    therefore see labels from after the validation query. It is not acceptable
    for model selection. This wrapper removes that defect.
    """
    eligible = causal_records(records, query_index, horizon)

    if not eligible:
        return {c: 1.0 / 3.0 for c in CLASSES}

    try:
        _, distribution, _ = v420.conditional_baseline(current, eligible)
        return normalize(distribution)
    except Exception:
        counts = Counter(direction(r) for r in eligible)
        return normalize({c: counts.get(c, 0) for c in CLASSES})


# ============================================================================
# RETRIEVAL REPRESENTATION
# ============================================================================

def component_values(current: Any, record: Any) -> Dict[str, float]:
    values = v420._v420_component_vector(current, record)
    out = {k: clamp(values.get(k, 0.0)) for k in FEATURES}
    try:
        out["quality"] = clamp(v420._v420_quality_gates(values))
    except Exception:
        out["quality"] = 1.0
    return out


def policy_weights(horizon: int, policy: str) -> Dict[str, float]:
    if policy == "structure_first":
        w = {
            "structure": 0.24, "sequence": 0.16, "regime": 0.16,
            "location": 0.08, "momentum": 0.08, "volatility": 0.07,
            "candle": 0.07, "path": 0.14,
        }
    elif policy == "context_first":
        w = {
            "structure": 0.15, "sequence": 0.10, "regime": 0.25,
            "location": 0.12, "momentum": 0.10, "volatility": 0.09,
            "candle": 0.07, "path": 0.12,
        }
    else:
        w = dict(
            getattr(v420, "V420_HORIZON_WEIGHTS", {}).get(
                int(horizon),
                getattr(v420, "V420_HORIZON_WEIGHTS", {}).get(
                    8,
                    {k: 1.0 / len(FEATURES) for k in FEATURES},
                ),
            )
        )

    total = sum(finite(v) for v in w.values())
    return {k: finite(v) / total for k, v in w.items()}


def similarity_from_components(
    values: Dict[str, float],
    horizon: int,
    policy: str,
) -> float:
    weights = policy_weights(horizon, policy)
    raw = sum(weights[k] * clamp(values.get(k, 0.0)) for k in FEATURES)
    quality = clamp(values.get("quality", 1.0))
    return clamp(raw * (0.75 + 0.25 * quality))


def regime_factor(current: Any, record: Any, policy: str) -> float:
    if policy == "none":
        return 1.0
    same = str(getattr(current, "regime", "UNKNOWN")) == str(
        getattr(record, "regime", "UNKNOWN")
    )
    if policy == "strict":
        return 1.0 if same else 0.0
    return 1.0 if same else 0.35


def temporal_weight(gap: int, halflife: Optional[float]) -> float:
    if halflife is None or halflife <= 0:
        return 1.0
    return math.exp(-math.log(2.0) * gap / halflife)


@dataclass(frozen=True)
class Config:
    k: int
    halflife: Optional[float]
    regime_policy: str
    similarity_policy: str


@dataclass
class Match:
    index: int
    episode_id: int
    score: float
    direction: str
    similarity: float
    temporal: float
    regime: float


# ============================================================================
# FAST QUERY CACHE
# ============================================================================

class QueryCache:
    """
    Fast causal cache. Each query/record pair computes the expensive V4.2
    component vector exactly once. All three similarity policies are then
    stored, and the causally fenced baseline is cached per query.

    This removes the dominant repeated work from nested configuration search.
    """

    def __init__(self, current_states, records, horizon):
        self.states = current_states
        self.records = records
        self.horizon = horizon
        self.cache = {}
        self.baseline_cache = {}

    def rows_for(self, query_index):
        if query_index in self.cache:
            return self.cache[query_index]

        current = self.states[query_index]
        eligible = causal_records(self.records, query_index, self.horizon)
        rows = []
        for record in eligible:
            try:
                values = component_values(current, record)
                sims = {
                    policy: similarity_from_components(values, self.horizon, policy)
                    for policy in POLICY_GRID
                }
                rows.append((record, values, sims))
            except Exception:
                continue
        self.cache[query_index] = rows
        return rows

    def baseline_for(self, query_index):
        if query_index in self.baseline_cache:
            return self.baseline_cache[query_index]
        current = self.states[query_index]
        p = causal_baseline(current, self.records, query_index, self.horizon)
        self.baseline_cache[query_index] = p
        return p


# ============================================================================
# RETRIEVAL
# ============================================================================

def retrieve(
    current: Any,
    query_index: int,
    horizon: int,
    config: Config,
    cache: QueryCache,
) -> Tuple[Dict[str, float], Dict[str, Any]]:
    matches: List[Match] = []

    for record, values, sims in cache.rows_for(query_index):
        base = sims.get(config.similarity_policy, 0.0)

        if base < MIN_SIMILARITY:
            continue

        rf = regime_factor(current, record, config.regime_policy)
        if rf <= 0:
            continue

        gap = query_index - int(record.index)
        tw = temporal_weight(gap, config.halflife)

        score = base * rf * (0.70 + 0.30 * tw)

        # Respect V4.2 contradiction logic when available.
        try:
            contradiction = v420._v420_contradiction(
                current,
                record,
                values,
            )
            if (
                contradiction
                > float(getattr(v420, "V420_MAX_CONTRADICTION", 0.42))
                and score < 0.60
            ):
                continue
        except Exception:
            pass

        d = direction(record)
        if d not in CLASSES:
            continue

        matches.append(
            Match(
                index=int(record.index),
                episode_id=int(getattr(record, "episode_id", record.index)),
                score=score,
                direction=d,
                similarity=base,
                temporal=tw,
                regime=rf,
            )
        )

    matches.sort(
        key=lambda x: (x.score, x.similarity, -x.index),
        reverse=True,
    )

    # One representative per episode first.
    selected = []
    episodes = set()
    for m in matches:
        if m.episode_id in episodes:
            continue
        selected.append(m)
        episodes.add(m.episode_id)
        if len(selected) >= config.k:
            break

    if len(selected) < MIN_MATCHES:
        return (
            {c: 1.0 / 3.0 for c in CLASSES},
            {
                "usable": False,
                "matches": len(selected),
                "pool_size": len(matches),
                "top_similarity": None,
                "mean_similarity": None,
                "homogeneity": 0.0,
                "mean_gap": None,
            },
        )

    counts = Counter(m.direction for m in selected)
    raw_class = normalize({c: counts.get(c, 0) for c in CLASSES})

    h = entropy(raw_class)
    homogeneity = clamp(1.0 - h / math.log(3.0))

    weighted = {c: 0.0 for c in CLASSES}
    total = 0.0

    for rank, m in enumerate(selected):
        # Similarity is evidence strength; it is not allowed to become a
        # probability by itself.
        w = max(0.01, m.score ** 4) / math.sqrt(rank + 1.0)
        weighted[m.direction] += w
        total += w

    probs = normalize(weighted) if total > EPS else raw_class

    # Shrink heterogeneous historical sets toward the neutral prior.
    strength = 0.15 + 0.85 * homogeneity
    probs = normalize({
        c: 1.0 / 3.0 + strength * (probs[c] - 1.0 / 3.0)
        for c in CLASSES
    })

    gaps = [query_index - m.index for m in selected]

    return (
        probs,
        {
            "usable": True,
            "matches": len(selected),
            "pool_size": len(matches),
            "top_similarity": selected[0].similarity,
            "mean_similarity": mean([m.similarity for m in selected]),
            "homogeneity": homogeneity,
            "mean_gap": mean(gaps),
            "mean_temporal": mean([m.temporal for m in selected]),
            "same_regime_fraction": mean([m.regime for m in selected]),
        },
    )


# ============================================================================
# PROBABILITY CALIBRATION
# ============================================================================

@dataclass(frozen=True)
class Calibration:
    shrink: float
    temperature: float


def apply_calibration(
    p: Dict[str, float],
    cal: Calibration,
) -> Dict[str, float]:
    p = normalize(p)
    t = max(0.25, cal.temperature)

    logits = {c: math.log(max(EPS, p[c])) / t for c in CLASSES}
    mx = max(logits.values())
    ex = {c: math.exp(logits[c] - mx) for c in CLASSES}
    s = sum(ex.values())

    q = {c: ex[c] / s for c in CLASSES}

    return normalize({
        c: cal.shrink * (1.0 / 3.0) + (1.0 - cal.shrink) * q[c]
        for c in CLASSES
    })


def fit_calibration(rows: Sequence[Dict[str, Any]]) -> Calibration:
    if len(rows) < MIN_CALIBRATION:
        return Calibration(0.35, 1.0)

    best = None

    for shrink in SHRINK_GRID:
        for temp in TEMP_GRID:
            loss = mean([
                logloss(
                    apply_calibration(r["raw_retrieval"], Calibration(shrink, temp)),
                    r["actual"],
                )
                for r in rows
            ])

            if loss is None:
                continue

            if best is None or loss < best[0]:
                best = (loss, shrink, temp)

    if best is None:
        return Calibration(0.35, 1.0)

    return Calibration(best[1], best[2])


# ============================================================================
# EVALUATION
# ============================================================================

def evaluate_rows(rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    if not rows:
        return {"samples": 0}

    return {
        "samples": len(rows),
        "baseline_accuracy": mean([r["base_acc"] for r in rows]),
        "retrieval_accuracy": mean([r["ret_acc"] for r in rows]),
        "baseline_brier": mean([r["base_brier"] for r in rows]),
        "retrieval_brier": mean([r["ret_brier"] for r in rows]),
        "baseline_logloss": mean([r["base_logloss"] for r in rows]),
        "retrieval_logloss": mean([r["ret_logloss"] for r in rows]),
        "accuracy_lift": mean([r["ret_acc"] - r["base_acc"] for r in rows]),
        "brier_lift": mean([r["base_brier"] - r["ret_brier"] for r in rows]),
        "logloss_lift": mean([r["base_logloss"] - r["ret_logloss"] for r in rows]),
        "coverage": mean([float(r["usable"]) for r in rows]),
        "mean_similarity": mean([
            r["mean_similarity"] for r in rows
            if r["mean_similarity"] is not None
        ]),
        "mean_top_similarity": mean([
            r["top_similarity"] for r in rows
            if r["top_similarity"] is not None
        ]),
        "mean_homogeneity": mean([r["homogeneity"] for r in rows]),
        "mean_matches": mean([r["matches"] for r in rows]),
    }


def evaluate_config(
    config: Config,
    states: Sequence[Any],
    candles: Sequence[Any],
    atr: Sequence[Any],
    records: Sequence[Any],
    indices: Sequence[int],
    horizon: int,
    cache: QueryCache,
) -> List[Dict[str, Any]]:
    rows = []

    for q in indices:
        if q + horizon >= len(candles):
            continue

        outcome = v420.make_outcome(candles, atr, q, horizon)
        actual = direction(outcome)
        if actual not in CLASSES:
            continue

        current = states[q]

        raw, info = retrieve(
            current=current,
            query_index=q,
            horizon=horizon,
            config=config,
            cache=cache,
        )

        base = cache.baseline_for(q)

        rows.append({
            "query_index": q,
            "actual": actual,
            "raw_retrieval": raw,
            "baseline_probs": base,
            "base_acc": accuracy(base, actual),
            "ret_acc": accuracy(raw, actual),
            "base_brier": brier(base, actual),
            "ret_brier": brier(raw, actual),
            "base_logloss": logloss(base, actual),
            "ret_logloss": logloss(raw, actual),
            "usable": bool(info["usable"]),
            "matches": int(info["matches"]),
            "homogeneity": finite(info["homogeneity"]),
            "mean_gap": info["mean_gap"],
            "top_similarity": info["top_similarity"],
            "mean_similarity": info["mean_similarity"],
        })

    return rows


def selection_score(rows: Sequence[Dict[str, Any]]) -> float:
    """
    Conservative incremental objective.

    Positive values are good:
      Brier improvement + LogLoss improvement.

    Accuracy is intentionally small so a model cannot win by producing
    unstable hard labels while worsening probabilities.
    """
    if not rows:
        return -1e9

    a = evaluate_rows(rows)

    return (
        0.50 * finite(a["brier_lift"])
        + 0.40 * finite(a["logloss_lift"])
        + 0.10 * finite(a["accuracy_lift"])
    )


def select_config(
    states: Sequence[Any],
    candles: Sequence[Any],
    atr: Sequence[Any],
    records: Sequence[Any],
    train_start: int,
    train_end: int,
    horizon: int,
) -> Tuple[Config, Dict[str, Any], List[int]]:
    """
    Three-way chronological split:

      fit     -> configuration development
      select  -> configuration validation
      calib   -> probability calibration

    No OOS observation enters this process.
    """

    available_end = train_end - horizon

    usable = available_end - train_start
    if usable < 3 * MIN_INNER_VALIDATION:
        default = Config(16, 100.0, "soft", "balanced")
        return default, {"selection": "DEFAULT_SMALL_TRAIN"}, [],

    fit_end = train_start + int(usable * 0.55)
    val_end = train_start + int(usable * 0.80)

    fit_idx = list(range(train_start, fit_end))
    val_idx = list(range(fit_end, val_end))
    calib_idx = list(range(val_end, available_end))

    if (
        len(fit_idx) < MIN_INNER_TRAIN
        or len(val_idx) < MIN_INNER_VALIDATION
        or len(calib_idx) < MIN_CALIBRATION
    ):
        default = Config(16, 100.0, "soft", "balanced")
        return default, {"selection": "DEFAULT_SPLIT_TOO_SMALL"}, calib_idx

    cache = QueryCache(states, records, horizon)

    candidates = []
    tested = 0
    total = len(K_GRID) * len(HALFLIFE_GRID) * len(REGIME_GRID) * len(POLICY_GRID)
    print(f"    Configuration search : {total} candidates (cached)")

    for k in K_GRID:
        for halflife in HALFLIFE_GRID:
            for regime in REGIME_GRID:
                for policy in POLICY_GRID:
                    cfg = Config(k, halflife, regime, policy)

                    # The fit set is used only as an eligibility/sanity
                    # requirement. Actual selection occurs on later data.
                    fit_rows = evaluate_config(
                        cfg, states, candles, atr, records,
                        fit_idx, horizon, cache,
                    )
                    if len(fit_rows) < MIN_INNER_TRAIN:
                        continue

                    val_rows = evaluate_config(
                        cfg, states, candles, atr, records,
                        val_idx, horizon, cache,
                    )
                    if len(val_rows) < MIN_INNER_VALIDATION:
                        continue

                    score = selection_score(val_rows)

                    candidates.append({
                        "score": score,
                        "config": cfg,
                        "fit": evaluate_rows(fit_rows),
                        "validation": evaluate_rows(val_rows),
                    })
                    tested += 1
                    if tested % 6 == 0 or tested == total:
                        print(f"      tested {tested}/{total}", flush=True)

    if not candidates:
        cfg = Config(16, 100.0, "soft", "balanced")
        return cfg, {"selection": "DEFAULT_NO_CANDIDATE"}, calib_idx

    candidates.sort(
        key=lambda x: (
            x["score"],
            finite(x["validation"]["brier_lift"]),
            finite(x["validation"]["logloss_lift"]),
        ),
        reverse=True,
    )

    best = candidates[0]

    return (
        best["config"],
        {
            "selection": "INNER_CHRONOLOGICAL_VALIDATION",
            "candidate_count": len(candidates),
            "best_score": best["score"],
            "best_fit": best["fit"],
            "best_validation": best["validation"],
            "top_candidates": [
                {
                    "score": x["score"],
                    "config": vars(x["config"]),
                    "validation": x["validation"],
                }
                for x in candidates[:10]
            ],
        },
        calib_idx,
    )


# ============================================================================
# DIAGNOSTICS
# ============================================================================

def spearman(xs: Sequence[float], ys: Sequence[float]) -> Optional[float]:
    if len(xs) != len(ys) or len(xs) < 3:
        return None

    def ranks(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(v):
            j = i
            while j + 1 < len(v) and v[order[j + 1]] == v[order[i]]:
                j += 1
            rank = 0.5 * (i + j) + 1.0
            for k in range(i, j + 1):
                r[order[k]] = rank
            i = j + 1
        return r

    rx, ry = ranks(xs), ranks(ys)
    mx, my = mean(rx), mean(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    dx = math.sqrt(sum((a - mx) ** 2 for a in rx))
    dy = math.sqrt(sum((b - my) ** 2 for b in ry))
    return safe_div(num, dx * dy)


def similarity_diagnostic(rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    valid = [r for r in rows if r["top_similarity"] is not None]
    if len(valid) < 20:
        return {"available": False}

    ordered = sorted(valid, key=lambda r: r["top_similarity"])

    quartiles = []
    for q in range(4):
        lo = q * len(ordered) // 4
        hi = (q + 1) * len(ordered) // 4
        chunk = ordered[lo:hi]
        quartiles.append({
            "quartile": q + 1,
            "n": len(chunk),
            "similarity": mean([r["top_similarity"] for r in chunk]),
            "accuracy": mean([r["ret_acc"] for r in chunk]),
            "brier": mean([r["ret_brier"] for r in chunk]),
            "logloss": mean([r["ret_logloss"] for r in chunk]),
            "brier_lift": mean([
                r["base_brier"] - r["ret_brier"] for r in chunk
            ]),
        })

    return {
        "available": True,
        "spearman_similarity_brier": spearman(
            [r["top_similarity"] for r in valid],
            [r["ret_brier"] for r in valid],
        ),
        "spearman_similarity_accuracy": spearman(
            [r["top_similarity"] for r in valid],
            [r["ret_acc"] for r in valid],
        ),
        "quartiles": quartiles,
    }


def permutation_test(rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Label permutation test for the paired retrieval-vs-baseline accuracy
    difference.

    This is a diagnostic, not a license to call the model predictive.
    """
    if len(rows) < 30:
        return {"available": False}

    pred_r = [
        max(r["retrieval_probs"], key=r["retrieval_probs"].get)
        for r in rows
    ]
    pred_b = [
        max(r["baseline_probs"], key=r["baseline_probs"].get)
        for r in rows
    ]
    actual = [r["actual"] for r in rows]

    observed = mean([
        float(a == p) - float(a == b)
        for p, b, a in zip(pred_r, pred_b, actual)
    ])

    rng = random.Random(PERMUTATION_SEED)
    null = []

    for _ in range(PERMUTATIONS):
        shuffled = actual[:]
        rng.shuffle(shuffled)
        null.append(mean([
            float(a == p) - float(a == b)
            for p, b, a in zip(pred_r, pred_b, shuffled)
        ]))

    ge = sum(x >= observed for x in null)
    p = (ge + 1.0) / (len(null) + 1.0)

    return {
        "available": True,
        "observed_accuracy_difference": observed,
        "null_mean": mean(null),
        "null_std": statistics.pstdev(null),
        "p_value": p,
        "permutations": len(null),
    }


def bootstrap_ci(rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    if len(rows) < 30:
        return {"available": False}

    rng = random.Random(BOOTSTRAP_SEED)
    n = len(rows)
    samples = []

    # Block bootstrap would be preferable for very long serial dependence.
    # Here each OOS window is short; this statistic is reported as a
    # conservative uncertainty diagnostic, not as a formal trading claim.
    for _ in range(BOOTSTRAPS):
        sample = [rows[rng.randrange(n)] for _ in range(n)]
        samples.append(mean([
            x["base_brier"] - x["ret_brier"]
            for x in sample
        ]))

    samples.sort()
    lo = samples[int(0.025 * (len(samples) - 1))]
    hi = samples[int(0.975 * (len(samples) - 1))]

    return {
        "available": True,
        "mean_brier_lift": mean(samples),
        "ci95_low": lo,
        "ci95_high": hi,
    }


def rank_discrimination(rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Check whether stronger retrieval similarity corresponds to better OOS
    probabilistic outcomes. This is diagnostic only and never used for tuning."""
    valid = [r for r in rows if r.get("top_similarity") is not None]
    if len(valid) < 30:
        return {"available": False}
    ordered = sorted(valid, key=lambda r: r["top_similarity"], reverse=True)
    thirds = []
    n = len(ordered)
    for i, name in enumerate(("TOP", "MIDDLE", "BOTTOM")):
        lo = i * n // 3
        hi = (i + 1) * n // 3
        chunk = ordered[lo:hi]
        thirds.append({
            "bucket": name,
            "n": len(chunk),
            "similarity": mean([r["top_similarity"] for r in chunk]),
            "brier": mean([r["ret_brier"] for r in chunk]),
            "logloss": mean([r["ret_logloss"] for r in chunk]),
            "brier_lift": mean([r["base_brier"] - r["ret_brier"] for r in chunk]),
        })
    return {"available": True, "tertiles": thirds,
            "top_beats_bottom_brier": thirds[0]["brier"] < thirds[-1]["brier"]}


# ============================================================================
# MAIN
# ============================================================================

def main():
    start_time = time.time()

    print("=" * 110)
    print("MLAI V4.2.0 — DEFINITIVE RETRIEVAL FORENSIC REPAIR")
    print("=" * 110)
    print("Research only")
    print("Production MLAI        : READ ONLY")
    print("Historical data        : READ ONLY")
    print("OOS tuning             : DISABLED")
    print("Causal inner baseline  : ENABLED")
    print("Disjoint calibration   : ENABLED")
    print("Nested chronological   : ENABLED")
    print("Fast causal cache      : ENABLED")
    print("Configuration grid     : 36")
    print()

    if not os.path.exists(DATA_FILE):
        raise FileNotFoundError(DATA_FILE)

    before_hash = sha256(DATA_FILE)

    candles, invalid = v420.load_market_data(DATA_FILE)
    chronology = v420.audit_chronology(candles)
    if not chronology["ordered"] or chronology["duplicates"]:
        raise RuntimeError("Chronology audit failed.")

    windows = v420.create_walk_forward_windows(
        len(candles), TRAIN_WINDOWS, OOS_SIZE
    )

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

    states = v420.build_market_states(
        candles,
        structure_states,
        atr,
    )

    episode_ids = v420.assign_episode_ids(states)

    print("FOUNDATION")
    print(f"  Candles           : {len(candles)}")
    print(f"  Invalid           : {invalid}")
    print(f"  Windows           : {len(windows)}")
    print(f"  Swings            : {len(engine.swings)}")
    print(f"  Structural events : {sum(1 for e in engine.events.values() if e != 'NONE')}")
    print(f"  Episodes          : {len(set(episode_ids.values()))}")
    print("  Chronology        : PASS")
    print("  Causal structure  : PASS")
    print()

    all_rows: List[Dict[str, Any]] = []
    window_results: Dict[str, Dict[int, Any]] = {}
    selections: Dict[str, Dict[int, Any]] = {}

    for window in windows:
        print("=" * 110)
        print(f"WINDOW {window.number}")
        print(f"TRAIN [{window.train_start}:{window.train_end}]")
        print(f"OOS   [{window.oos_start}:{window.oos_end}]")
        print("=" * 110)

        window_results[str(window.number)] = {}
        selections[str(window.number)] = {}

        for horizon in HORIZONS:
            print()
            print(f"  H+{horizon}")

            records = v420.build_experience_records(
                candles,
                atr,
                states,
                episode_ids,
                window.train_start,
                window.train_end,
                horizon,
            )

            print(f"  Training records : {len(records)}")

            config, selection_info, calib_indices = select_config(
                states,
                candles,
                atr,
                records,
                window.train_start,
                window.train_end,
                horizon,
            )

            selections[str(window.number)][horizon] = {
                "config": vars(config),
                "selection": selection_info,
            }

            print("  SELECTED")
            print(f"    K             : {config.k}")
            print(f"    Half-life     : {config.halflife}")
            print(f"    Regime        : {config.regime_policy}")
            print(f"    Similarity    : {config.similarity_policy}")

            cache = QueryCache(states, records, horizon)

            # Calibration is a separate late-training slice.
            cal_rows = evaluate_config(
                config,
                states,
                candles,
                atr,
                records,
                calib_indices,
                horizon,
                cache,
            )
            calibration = fit_calibration(cal_rows)

            print(f"    Calibration shrink : {calibration.shrink:.3f}")
            print(f"    Calibration temp  : {calibration.temperature:.3f}")

            # OOS is frozen from this point.
            oos_indices = list(range(window.oos_start, window.oos_end))
            rows = []

            for q in oos_indices:
                if q + horizon >= len(candles):
                    continue

                outcome = v420.make_outcome(
                    candles, atr, q, horizon
                )
                actual = direction(outcome)
                if actual not in CLASSES:
                    continue

                current = states[q]

                raw, info = retrieve(
                    current,
                    q,
                    horizon,
                    config,
                    cache,
                )

                retrieval_probs = apply_calibration(
                    raw,
                    calibration,
                )

                base = cache.baseline_for(q)

                rows.append({
                    "window": window.number,
                    "horizon": horizon,
                    "query_index": q,
                    "actual": actual,
                    "retrieval_probs": retrieval_probs,
                    "baseline_probs": base,
                    "raw_retrieval": raw,
                    "base_acc": accuracy(base, actual),
                    "ret_acc": accuracy(retrieval_probs, actual),
                    "base_brier": brier(base, actual),
                    "ret_brier": brier(retrieval_probs, actual),
                    "base_logloss": logloss(base, actual),
                    "ret_logloss": logloss(retrieval_probs, actual),
                    "usable": bool(info["usable"]),
                    "matches": int(info["matches"]),
                    "homogeneity": finite(info["homogeneity"]),
                    "mean_gap": info["mean_gap"],
                    "top_similarity": info["top_similarity"],
                    "mean_similarity": info["mean_similarity"],
                })

            all_rows.extend(rows)
            agg = evaluate_rows(rows)
            window_results[str(window.number)][horizon] = agg

            print(f"    OOS N             : {agg['samples']}")
            print(f"    Baseline Acc      : {100*finite(agg['baseline_accuracy']):.3f}%")
            print(f"    Retrieval Acc     : {100*finite(agg['retrieval_accuracy']):.3f}%")
            print(f"    Accuracy lift     : {100*finite(agg['accuracy_lift']):.3f}%")
            print(f"    Brier lift        : {finite(agg['brier_lift']):.8f}")
            print(f"    LogLoss lift      : {finite(agg['logloss_lift']):.8f}")
            print(f"    Coverage          : {100*finite(agg['coverage']):.2f}%")
            print(f"    Mean similarity   : {agg['mean_similarity']}")
            print(f"    Homogeneity       : {agg['mean_homogeneity']}")

    # =========================================================================
    # GLOBAL
    # =========================================================================

    by_horizon = {}
    similarity = {}
    rank_reports = {}
    nulls = {}
    bootstraps = {}
    stability = {}

    for horizon in HORIZONS:
        rows = [r for r in all_rows if r["horizon"] == horizon]

        by_horizon[horizon] = evaluate_rows(rows)
        similarity[horizon] = similarity_diagnostic(rows)
        rank_reports[horizon] = rank_discrimination(rows)
        nulls[horizon] = permutation_test(rows)
        bootstraps[horizon] = bootstrap_ci(rows)

        windows_with_data = []
        for w in windows:
            a = window_results[str(w.number)].get(horizon, {})
            if a.get("samples", 0):
                windows_with_data.append(a)

        stability[horizon] = {
            "windows": len(windows_with_data),
            "positive_accuracy": sum(
                finite(a["accuracy_lift"]) > 0
                for a in windows_with_data
            ),
            "positive_brier": sum(
                finite(a["brier_lift"]) > 0
                for a in windows_with_data
            ),
            "positive_logloss": sum(
                finite(a["logloss_lift"]) > 0
                for a in windows_with_data
            ),
            "mean_accuracy_lift": mean([
                finite(a["accuracy_lift"]) for a in windows_with_data
            ]),
            "mean_brier_lift": mean([
                finite(a["brier_lift"]) for a in windows_with_data
            ]),
            "mean_logloss_lift": mean([
                finite(a["logloss_lift"]) for a in windows_with_data
            ]),
        }

    # =========================================================================
    # STRICT VERDICT
    # =========================================================================

    verdicts = {}

    for horizon in HORIZONS:
        a = by_horizon[horizon]
        s = stability[horizon]
        n = nulls[horizon]
        sr = similarity[horizon]

        stable = (
            s["windows"] >= 3
            and s["positive_brier"] >= math.ceil(0.60 * s["windows"])
            and s["positive_logloss"] >= math.ceil(0.60 * s["windows"])
        )

        positive_probabilistic = (
            finite(a.get("brier_lift")) > 0
            and finite(a.get("logloss_lift")) > 0
        )

        similarity_supported = False
        if sr.get("available"):
            rho = sr.get("spearman_similarity_brier")
            similarity_supported = rho is not None and rho < -0.10

        null_supported = (
            n.get("available", False)
            and finite(n.get("p_value")) < 0.05
        )

        if (
            positive_probabilistic
            and stable
            and similarity_supported
            and null_supported
        ):
            verdicts[horizon] = "PREDICTIVE_EVIDENCE"
        elif positive_probabilistic and stable:
            verdicts[horizon] = "PARTIAL_EVIDENCE"
        elif positive_probabilistic:
            verdicts[horizon] = "WEAK_EVIDENCE"
        else:
            verdicts[horizon] = "NO_EVIDENCE"

    if all(v == "PREDICTIVE_EVIDENCE" for v in verdicts.values()):
        final_verdict = "STRONG MULTI-HORIZON EVIDENCE"
    elif any(v == "PREDICTIVE_EVIDENCE" for v in verdicts.values()):
        final_verdict = "HORIZON-SPECIFIC PREDICTIVE EVIDENCE"
    elif any(v == "PARTIAL_EVIDENCE" for v in verdicts.values()):
        final_verdict = "PARTIAL / INSUFFICIENT EVIDENCE"
    else:
        final_verdict = "NO CREDIBLE INCREMENTAL EVIDENCE"

    after_hash = sha256(DATA_FILE)
    unchanged = before_hash == after_hash
    if not unchanged:
        raise RuntimeError("PROTECTION FAILURE: market_data.bin changed.")

    elapsed = time.time() - start_time

    print()
    print("=" * 110)
    print("FINAL DEFINITIVE RETRIEVAL FORENSIC RESULT")
    print("=" * 110)

    for horizon in HORIZONS:
        a = by_horizon[horizon]
        s = stability[horizon]
        n = nulls[horizon]
        sr = similarity[horizon]
        rr = rank_reports[horizon]
        bi = bootstraps[horizon]

        print()
        print(f"H+{horizon}")
        print(f"  Verdict            : {verdicts[horizon]}")
        print(f"  Baseline Acc       : {100*finite(a['baseline_accuracy']):.4f}%")
        print(f"  Retrieval Acc      : {100*finite(a['retrieval_accuracy']):.4f}%")
        print(f"  Accuracy lift      : {100*finite(a['accuracy_lift']):.4f}%")
        print(f"  Brier lift         : {finite(a['brier_lift']):.8f}")
        print(f"  LogLoss lift       : {finite(a['logloss_lift']):.8f}")
        print(f"  Positive Brier     : {s['positive_brier']}/{s['windows']}")
        print(f"  Positive LogLoss   : {s['positive_logloss']}/{s['windows']}")
        print(f"  Similarity/Brier   : {sr.get('spearman_similarity_brier')}")
        print(f"  Rank top>bottom    : {rr.get('top_beats_bottom_brier')}")
        print(f"  Permutation p      : {n.get('p_value')}")
        if bi.get("available"):
            print(
                f"  Brier 95% CI      : "
                f"[{bi['ci95_low']:.8f}, {bi['ci95_high']:.8f}]"
            )

    print()
    print(f"FINAL VERDICT: {final_verdict}")
    print()
    print("PROTECTION")
    print(f"  market_data.bin unchanged : {'PASS' if unchanged else 'FAIL'}")
    print("  Production modified       : NO")
    print("  Learning memory modified  : NO")
    print("  Trading                   : DISABLED")
    print(f"  Runtime                   : {elapsed:.2f}s")

    artifact = {
        "version": VERSION,
        "verdict": final_verdict,
        "horizon_verdicts": verdicts,
        "dataset": {
            "file": DATA_FILE,
            "candles": len(candles),
            "invalid": invalid,
            "sha256_before": before_hash,
            "sha256_after": after_hash,
            "unchanged": unchanged,
        },
        "foundation": {
            "chronology": chronology,
            "causality": causality,
            "swings": len(engine.swings),
            "structural_events": sum(
                1 for e in engine.events.values() if e != "NONE"
            ),
            "episodes": len(set(episode_ids.values())),
        },
        "methodology": {
            "causal_record_rule": "record.index + horizon <= query_index",
            "nested_chronological_selection": True,
            "disjoint_calibration": True,
            "oos_tuning": False,
            "production_modified": False,
            "market_data_modified": False,
        },
        "configuration_grid": {
            "K_GRID": K_GRID,
            "HALFLIFE_GRID": HALFLIFE_GRID,
            "REGIME_GRID": REGIME_GRID,
            "POLICY_GRID": POLICY_GRID,
        },
        "selections": selections,
        "window_results": window_results,
        "global": by_horizon,
        "stability": stability,
        "similarity": similarity,
        "rank_discrimination": rank_reports,
        "null_tests": nulls,
        "bootstrap": bootstraps,
        "elapsed_seconds": elapsed,
    }

    with open(ARTIFACT_FILE, "wb") as f:
        pickle.dump(artifact, f, protocol=pickle.HIGHEST_PROTOCOL)

    report = []
    report.append("# MLAI V4.2.0 — Definitive Retrieval Forensic Repair")
    report.append("")
    report.append(f"**Version:** `{VERSION}`")
    report.append("")
    report.append(f"## Final verdict: **{final_verdict}**")
    report.append("")
    report.append(
        "This experiment is research-only. It does not modify production MLAI "
        "or historical data."
    )
    report.append("")
    report.append("## Root-level repairs")
    report.append("")
    report.append(
        "1. Every query now receives only records whose complete outcome "
        "was known before that query."
    )
    report.append(
        "2. The inner validation baseline is causally fenced; it cannot see "
        "labels from later in the validation period."
    )
    report.append(
        "3. Configuration selection is chronological and OOS-blind."
    )
    report.append(
        "4. Calibration uses a disjoint late-training slice."
    )
    report.append(
        "5. Retrieval feature computation, all three similarity policies, and the "
        "causal baseline are cached per query, avoiding repeated nested scans."
    )
    report.append(
        "6. The runtime defect in the original forensic script is eliminated "
        "by a complete retrieval-info contract: diagnostic fields exist even "
        "when retrieval is sparse."
    )
    report.append(
        "7. The missing `Counter` dependency is explicitly imported."
    )
    report.append("")
    report.append("## Global OOS results")
    report.append("")
    report.append(
        "| Horizon | Verdict | Baseline Acc | Retrieval Acc | Acc Lift | Brier Lift | LogLoss Lift | Coverage |"
    )
    report.append(
        "|---:|---|---:|---:|---:|---:|---:|---:|"
    )

    for h in HORIZONS:
        a = by_horizon[h]
        report.append(
            f"| H+{h} | {verdicts[h]} "
            f"| {100*finite(a['baseline_accuracy']):.4f}% "
            f"| {100*finite(a['retrieval_accuracy']):.4f}% "
            f"| {100*finite(a['accuracy_lift']):.4f}% "
            f"| {finite(a['brier_lift']):.8f} "
            f"| {finite(a['logloss_lift']):.8f} "
            f"| {100*finite(a['coverage']):.2f}% |"
        )

    report.append("")
    report.append("## Stability")
    report.append("")
    for h in HORIZONS:
        s = stability[h]
        report.append(
            f"- H+{h}: positive Brier {s['positive_brier']}/{s['windows']}; "
            f"positive LogLoss {s['positive_logloss']}/{s['windows']}; "
            f"mean Brier lift {s['mean_brier_lift']}; "
            f"mean LogLoss lift {s['mean_logloss_lift']}"
        )

    report.append("")
    report.append("## Similarity discrimination")
    report.append("")
    for h in HORIZONS:
        sr = similarity[h]
        report.append(
            f"- H+{h}: Spearman(similarity, Brier) = "
            f"{sr.get('spearman_similarity_brier')}"
        )
        for q in sr.get("quartiles", []):
            report.append(
                f"  - Q{q['quartile']}: n={q['n']}, "
                f"similarity={q['similarity']}, "
                f"accuracy={q['accuracy']}, "
                f"Brier={q['brier']}, "
                f"Brier lift={q['brier_lift']}"
            )

    report.append("")
    report.append("## Rank discrimination")
    report.append("")
    for h in HORIZONS:
        rr = rank_reports[h]
        report.append(f"- H+{h}: top-similarity tertile beats bottom tertile on Brier = {rr.get('top_beats_bottom_brier')}")
        for bucket in rr.get("tertiles", []):
            report.append(f"  - {bucket['bucket']}: n={bucket['n']}, similarity={bucket['similarity']}, Brier={bucket['brier']}, Brier lift={bucket['brier_lift']}")
    report.append("")
    report.append("## Permutation tests")
    report.append("")
    for h in HORIZONS:
        n = nulls[h]
        report.append(
            f"- H+{h}: observed accuracy difference="
            f"{n.get('observed_accuracy_difference')}, "
            f"p={n.get('p_value')}"
        )

    report.append("")
    report.append("## Protection")
    report.append("")
    report.append(f"- market_data.bin unchanged: {'PASS' if unchanged else 'FAIL'}")
    report.append("- Production MLAI modified: NO")
    report.append("- Learning memory modified: NO")
    report.append("- Trading: DISABLED")
    report.append("")
    report.append(
        "## Interpretation"
    )
    report.append("")
    report.append(
        "No positive OOS result is assumed. Retrieval is considered genuinely "
        "useful only when the frozen OOS evidence demonstrates incremental "
        "probabilistic value against the causally fenced baseline, with "
        "cross-window stability and independent diagnostic support."
    )

    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(report))

    print()
    print("ARTIFACTS")
    print(f"  {ARTIFACT_FILE}")
    print(f"  {REPORT_FILE}")
    print()
    print("MLAI production was NOT modified.")


if __name__ == "__main__":
    main()