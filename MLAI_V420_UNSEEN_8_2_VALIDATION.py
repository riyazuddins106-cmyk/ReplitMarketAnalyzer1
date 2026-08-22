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
import json
import pickle
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
    calibration_start = max(0, train_end - max(30, int(train_end * 0.20)))
    calibration_indices = list(range(calibration_start, train_end - horizon))
    selection_info = {
        "selection": "PREDECLARED_FIXED_CONFIGURATION",
        "reason": "Focused 8/2 holdout; no holdout tuning",
    }
    cache = forensic.QueryCache(states, records, horizon)
    calibration_rows = forensic.evaluate_config(
        config,
        states,
        candles,
        atr,
        records,
        calibration_indices,
        horizon,
        cache,
    )
    calibration = forensic.fit_calibration(calibration_rows)

    rows: List[Dict[str, Any]] = []
    for query_index in holdout_indices:
        # The prediction is made before calculating or reading the target.
        current = states[query_index]
        raw, info = forensic.retrieve(
            current, query_index, horizon, config, cache
        )
        retrieval_probs = forensic.apply_calibration(raw, calibration)
        baseline_probs = cache.baseline_for(query_index)

        # Target/outcome is revealed only after the prediction above.
        if query_index + horizon >= len(candles):
            continue
        outcome = v420.make_outcome(candles, atr, query_index, horizon)
        actual = forensic.direction(outcome)
        if actual not in forensic.CLASSES:
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
            }
        )

    aggregate = forensic.evaluate_rows(rows)
    return {
        "horizon": horizon,
        "training_records": len(records),
        "selected_config": vars(config),
        "selection": selection_info,
        "calibration": vars(calibration),
        "causal_training_end": train_end - 1,
        "holdout_first_index": holdout_indices[0] if holdout_indices else None,
        "rows": rows,
        "aggregate": aggregate,
    }


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
        f"- Total candles: {result['total_candles']}",
        "",
        "## Results",
        "",
        "| Horizon | Holdout N | Baseline accuracy | Retrieval accuracy | Accuracy lift | Brier lift | LogLoss lift | Coverage |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for horizon in HORIZONS:
        aggregate = result["horizons"][str(horizon)]["aggregate"]
        lines.append(
            f"| H+{horizon} | {aggregate['samples']} | "
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
    for horizon in HORIZONS:
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
                f"- Training records available before holdout: "
                f"{payload['training_records']}",
                f"- Selected configuration: `{payload['selected_config']}`",
                "",
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
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", default=str(DEFAULT_DATA))
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    parser.add_argument(
        "--stride",
        type=int,
        default=12,
        help="Score every Nth 5-minute holdout candle (default: 12 = hourly).",
    )
    args = parser.parse_args()
    if args.stride < 1:
        raise ValueError("--stride must be at least 1.")

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

    result: Dict[str, Any] = {
        "data": str(data_path),
        "train_dates": train_dates,
        "holdout_dates": holdout_dates,
        "train_candles": len(train_indices),
        "holdout_candles": len(holdout_indices),
        "holdout_candles_available": len(all_holdout_indices),
        "holdout_stride": args.stride,
        "total_candles": len(candles),
        "causality": causality,
        "horizons": {},
    }
    for horizon in HORIZONS:
        result["horizons"][str(horizon)] = score_holdout(
            candles, states, atr, episode_ids, train_end, holdout_indices, horizon
        )

    report = render_report(result)
    Path(args.report).write_text(report, encoding="utf-8")
    print(report)
    print(f"Saved report to {args.report}")


if __name__ == "__main__":
    main()