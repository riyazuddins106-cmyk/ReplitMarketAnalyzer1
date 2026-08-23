"""
MLAI V4.2.0 — UNSEEN 8-DAY / 2-DAY VALIDATION
===============================================

Chronological holdout validation for the supplied XAU/USD 5-minute corpus.

The latest ten available UTC dates are split into:

    Days 1–8: historical training and calibration
    Days 9–10: locked, unseen holdout

Every holdout candle is interpreted using only records from Days 1–8. The
actual future outcome is read only after the prediction is created, and is used
only for scoring. No candles are fabricated and the source data is read-only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pickle
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import MLAI_V420_RETRIEVAL_FORENSIC_REPAIR as forensic
import mlai_market_structure_v420 as v420


ROOT = Path(__file__).resolve().parent
DEFAULT_DATA = ROOT / "data" / "market_data_50d.bin"
DEFAULT_REPORT = ROOT / "MLAI_V420_UNSEEN_8_2_VALIDATION_REPORT.md"
HORIZONS = tuple(v420.HORIZONS)
VALIDATION_VERSION = "V420-UNSEEN-8-2-FULL-5M-1"


def utc_date(timestamp: int) -> str:
    return datetime.fromtimestamp(timestamp, timezone.utc).date().isoformat()


def load_data(path: Path) -> List[Any]:
    candles, invalid = v420.load_market_data(str(path))
    chronology = v420.audit_chronology(candles)
    if invalid or not chronology["ordered"] or chronology["duplicates"]:
        raise RuntimeError(
            f"Data validation failed: invalid={invalid}, chronology={chronology}"
        )
    return candles


def score_holdout(
    candles: List[Any],
    states: List[Any],
    atr: List[Any],
    episode_ids: Dict[int, int],
    train_end: int,
    holdout_indices: List[int],
    horizon: int,
) -> Dict[str, Any]:
    # This boundary excludes every record whose outcome is not complete before
    # the first holdout candle. No holdout outcome can enter retrieval.
    records = v420.build_experience_records(
        candles, atr, states, episode_ids, 0, train_end, horizon
    )
    # This focused 8/2 experiment uses one predeclared configuration rather
    # than searching 36 candidates. The locked holdout is therefore not used
    # for tuning, and the experiment remains practical on the larger corpus.
    config = forensic.Config(
        k=24,
        halflife=None,
        regime_policy="none",
        similarity_policy="balanced",
    )
    selection_info = {
        "selection": "PREDECLARED_FIXED_CONFIGURATION",
        "reason": "Focused 8/2 holdout; no holdout tuning or calibration fitting",
    }
    cache = forensic.QueryCache(states, records, horizon)
    # Calibration fitting over thousands of historical queries would repeat
    # the full retrieval search without changing the locked-test boundary.
    # The calibration prior is therefore frozen before the holdout, making
    # this experiment both reproducible and computationally bounded.
    calibration = forensic.Calibration(shrink=0.35, temperature=1.0)

    rows: List[Dict[str, Any]] = []
    exclusions: Counter[str] = Counter()
    for query_index in holdout_indices:
        if query_index < train_end:
            exclusions["holdout_index_before_training_boundary"] += 1
            continue
        # The prediction is made before calculating or reading the target.
        current = states[query_index]
        raw, info = forensic.retrieve(
            current, query_index, horizon, config, cache
        )
        retrieval_probs = forensic.apply_calibration(raw, calibration)
        baseline_probs = cache.baseline_for(query_index)

        # Target/outcome is revealed only after the prediction above.
        if query_index + horizon >= len(candles):
            exclusions["future_horizon_unavailable"] += 1
            continue
        outcome = v420.make_outcome(candles, atr, query_index, horizon)
        actual = forensic.direction(outcome)
        if actual not in forensic.CLASSES:
            exclusions["outcome_unavailable_or_invalid"] += 1
            continue

        rows.append(
            {
                "query_index": query_index,
                "date": utc_date(candles[query_index].timestamp),
                "actual": actual,
                "retrieval_probs": retrieval_probs,
                "baseline_probs": baseline_probs,
                "base_acc": forensic.accuracy(baseline_probs, actual),
                "ret_acc": forensic.accuracy(retrieval_probs, actual),
                "base_brier": forensic.brier(baseline_probs, actual),
                "ret_brier": forensic.brier(retrieval_probs, actual),
                "base_logloss": forensic.logloss(baseline_probs, actual),
                "ret_logloss": forensic.logloss(retrieval_probs, actual),
                "usable": bool(info["usable"]),
                "matches": int(info["matches"]),
                "top_similarity": info["top_similarity"],
                "mean_similarity": info["mean_similarity"],
                "homogeneity": float(info.get("homogeneity", 0.0)),
            }
        )

    aggregate = forensic.evaluate_rows(rows)
    aggregate.update(validation_metrics(rows))
    return {
        "horizon": horizon,
        "training_records": len(records),
        "selected_config": vars(config),
        "selection": selection_info,
        "calibration": vars(calibration),
        "causal_training_end": train_end - 1,
        "holdout_first_index": holdout_indices[0] if holdout_indices else None,
        "rows": rows,
        "exclusions": dict(sorted(exclusions.items())),
        "excluded": sum(exclusions.values()),
        "aggregate": aggregate,
    }


def validation_metrics(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Additional locked-test diagnostics; none are used for selection."""
    if not rows:
        return {
            "class_distribution": {},
            "probability_distribution": {},
            "calibration": {"slope": None, "intercept": None, "ece": None},
            "sharpness": None,
        }
    distribution = Counter(row["actual"] for row in rows)
    probs = {
        cls: sum(float(row["retrieval_probs"].get(cls, 0.0)) for row in rows)
        / len(rows)
        for cls in forensic.CLASSES
    }
    confidence = [
        max(float(row["retrieval_probs"].get(cls, 0.0))
            for cls in forensic.CLASSES)
        for row in rows
    ]
    correct = [
        float(max(forensic.CLASSES,
                  key=lambda cls: row["retrieval_probs"].get(cls, 0.0))
              == row["actual"])
        for row in rows
    ]
    # Reliability slope/intercept for confidence versus correctness. This is
    # deliberately descriptive and is not used to tune the locked test.
    mean_x = sum(confidence) / len(confidence)
    mean_y = sum(correct) / len(correct)
    denominator = sum((x - mean_x) ** 2 for x in confidence)
    slope = (
        sum((x - mean_x) * (y - mean_y) for x, y in zip(confidence, correct))
        / denominator
        if denominator > 1e-15 else None
    )
    intercept = mean_y - slope * mean_x if slope is not None else None
    buckets: Dict[int, List[tuple[float, float]]] = {}
    for x, y in zip(confidence, correct):
        bucket = min(9, int(x * 10))
        buckets.setdefault(bucket, []).append((x, y))
    ece = sum(
        len(values) / len(rows)
        * abs(sum(x for x, _ in values) / len(values)
              - sum(y for _, y in values) / len(values))
        for values in buckets.values()
    )
    return {
        "class_distribution": dict(sorted(distribution.items())),
        "probability_distribution": probs,
        "calibration": {
            "slope": slope,
            "intercept": intercept,
            "ece": ece,
        },
        "sharpness": sum(confidence) / len(confidence),
        "by_day": {
            day: {
                "samples": len(day_rows),
                "baseline_accuracy": forensic.mean(
                    [r["base_acc"] for r in day_rows]
                ),
                "retrieval_accuracy": forensic.mean(
                    [r["ret_acc"] for r in day_rows]
                ),
                "brier_lift": forensic.mean(
                    [r["base_brier"] - r["ret_brier"] for r in day_rows]
                ),
            }
            for day in sorted({r["date"] for r in rows})
            for day_rows in [[r for r in rows if r["date"] == day]]
        },
    }


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def render_report(result: Dict[str, Any]) -> str:
    lines = [
        "# MLAI V4.2.0 — Unseen 8-Day / 2-Day Validation",
        "",
        "This is a chronological, research-only holdout test. Days 9–10 were "
        "not used for model selection, calibration, or retrieval.",
        "",
        "## Split",
        "",
        f"- Training dates (Days 1–8): `{result['train_dates'][0]}` through "
        f"`{result['train_dates'][-1]}`",
        f"- Locked holdout dates (Days 9–10): `{result['holdout_dates'][0]}` "
        f"through `{result['holdout_dates'][-1]}`",
        f"- Training candles: {result['train_candles']}",
        f"- Holdout candles: {result['holdout_candles']}",
        f"- Available holdout candles: {result['holdout_candles_available']}",
        f"- Total candles: {result['total_candles']}",
        f"- Sampling frequency: `5-minute; every available candle`",
        f"- Dataset SHA-256: `{result['dataset_sha256']}`",
        f"- Configuration hash: `{result['configuration_hash']}`",
        "",
        "## Results",
        "",
        "| Horizon | Holdout N | Scored | Excluded | Baseline accuracy | Retrieval accuracy | Accuracy lift | Brier lift | LogLoss lift | Coverage |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for horizon in result["horizons"]:
        payload = result["horizons"][str(horizon)]
        aggregate = payload["aggregate"]
        lines.append(
            f"| H+{horizon} | {result['holdout_candles']} | {aggregate['samples']} | "
            f"{payload['excluded']} | "
            f"{100 * aggregate['baseline_accuracy']:.3f}% | "
            f"{100 * aggregate['retrieval_accuracy']:.3f}% | "
            f"{100 * aggregate['accuracy_lift']:.3f}% | "
            f"{aggregate['brier_lift']:.8f} | "
            f"{aggregate['logloss_lift']:.8f} | "
            f"{100 * aggregate['coverage']:.2f}% |"
        )
    lines.extend(
        [
            "",
            "## Holdout probability and evidence summary",
            "",
        ]
    )
    for horizon in result["horizons"]:
        payload = result["horizons"][str(horizon)]
        rows = payload["rows"]
        distribution = Counter(row["actual"] for row in rows)
        usable = sum(row["usable"] for row in rows)
        lines.extend(
            [
                f"### H+{horizon}",
                "",
                f"- Actual outcomes revealed after prediction: "
                f"{dict(sorted(distribution.items()))}",
                f"- Usable retrieval predictions: {usable}/{len(rows)}",
                f"- Exclusions: `{payload['exclusions'] or 'none'}`",
                f"- Training records available before holdout: "
                f"{payload['training_records']}",
                f"- Selected configuration: `{payload['selected_config']}`",
                "",
                f"- UP/DOWN/NEUTRAL distribution: `{aggregate['class_distribution']}`",
                f"- Mean predicted probability: `{aggregate['probability_distribution']}`",
                f"- Calibration slope/intercept/ECE: "
                f"`{aggregate['calibration']['slope']}`, "
                f"`{aggregate['calibration']['intercept']}`, "
                f"`{aggregate['calibration']['ece']}`",
                f"- Probability sharpness: `{aggregate['sharpness']}`",
                f"- Baseline Brier / retrieval Brier: "
                f"`{aggregate['baseline_brier']}` / `{aggregate['retrieval_brier']}`",
                f"- Baseline LogLoss / retrieval LogLoss: "
                f"`{aggregate['baseline_logloss']}` / `{aggregate['retrieval_logloss']}`",
                f"- Performance by UTC holdout day: `{aggregate['by_day']}`",
            ]
        )
    lines.extend(
        [
            "## Scientific interpretation",
            "",
            "A positive result is meaningful only if retrieval improves over the "
            "causal baseline on the locked holdout and remains stable across "
            "predeclared horizons. This test measures historical generalization; "
            "it does not guarantee future market behavior.",
            "",
            "## Protection",
            "",
            "- Synthetic candles created: NO",
            "- Holdout outcomes used before prediction: NO",
            "- Market data modified: NO",
            "- Holdout results added to training memory: NO",
            "- Holdout sampling reduced: NO",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", default=str(DEFAULT_DATA))
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    parser.add_argument(
        "--stride", type=int, default=1,
        help="Compatibility option; definitive validation requires --stride 1.",
    )
    parser.add_argument(
        "--horizon", type=int, choices=HORIZONS, default=None,
        help="Run one horizon; useful for parallel reproducible execution.",
    )
    args = parser.parse_args()
    if args.stride < 1:
        raise ValueError("--stride must be at least 1.")
    if args.stride != 1:
        raise ValueError(
            "Definitive validation processes every available 5-minute candle; "
            "hourly sampling is diagnostic-only and cannot be reported here."
        )

    data_path = Path(args.data)
    candles = load_data(data_path)
    dates = sorted({utc_date(c.timestamp) for c in candles})
    if len(dates) < 10:
        raise RuntimeError(f"Need at least 10 available dates; found {len(dates)}.")
    selected_dates = dates[-10:]
    train_dates = selected_dates[:8]
    holdout_dates = selected_dates[8:]
    train_indices = [
        i for i, candle in enumerate(candles) if utc_date(candle.timestamp) in train_dates
    ]
    all_holdout_indices = [
        i for i, candle in enumerate(candles) if utc_date(candle.timestamp) in holdout_dates
    ]
    holdout_indices = all_holdout_indices[:: args.stride]
    train_end = holdout_indices[0]

    atr = v420.calculate_atr(candles)
    engine = v420.CausalStructureEngine(candles)
    structure_states = engine.build()
    causality = v420.audit_structure_causality(
        candles, engine.swings, structure_states, engine.events
    )
    if not causality["passed"]:
        raise RuntimeError("Causal structure audit failed.")
    states = v420.build_market_states(candles, structure_states, atr)
    episode_ids = v420.assign_episode_ids(states)

    fixed_configuration = {
        "k": 24, "halflife": None, "regime_policy": "none",
        "similarity_policy": "balanced",
        "horizons": list(HORIZONS),
        "calibration": "training-only; fixed predeclared grid",
    }
    config_text = json.dumps(fixed_configuration, sort_keys=True)
    result: Dict[str, Any] = {
        "data": str(data_path),
        "dataset_sha256": file_sha256(data_path),
        "dataset_size": data_path.stat().st_size,
        "validation_version": VALIDATION_VERSION,
        "instrument": getattr(candles[0], "instrument", "XAU/USD"),
        "symbol": "XAUUSD",
        "timeframe": "5m",
        "first_timestamp": candles[0].timestamp,
        "last_timestamp": candles[-1].timestamp,
        "available_dates": dates,
        "train_dates": train_dates,
        "holdout_dates": holdout_dates,
        "training_boundary": candles[train_end - 1].timestamp,
        "holdout_boundary": candles[train_end].timestamp,
        "first_holdout_timestamp": candles[train_end].timestamp,
        "last_holdout_timestamp": candles[all_holdout_indices[-1]].timestamp,
        "train_candles": len(train_indices),
        "holdout_candles": len(holdout_indices),
        "holdout_candles_available": len(all_holdout_indices),
        "holdout_stride": 1,
        "total_candles": len(candles),
        "causality": causality,
        "horizons": {},
        "configuration": fixed_configuration,
        "configuration_hash": hashlib.sha256(config_text.encode()).hexdigest(),
        "feature_version": "v420 causal market-state + forensic components",
        "random_seed": None,
    }
    run_horizons = (args.horizon,) if args.horizon is not None else HORIZONS
    for horizon in run_horizons:
        result["horizons"][str(horizon)] = score_holdout(
            candles, states, atr, episode_ids, train_end, holdout_indices, horizon
        )

    report = render_report(result)
    Path(args.report).write_text(report, encoding="utf-8")
    print(report)
    print(f"Saved report to {args.report}")


if __name__ == "__main__":
    main()