"""
================================================================================
MLAI v4.1.1 DIAGNOSTIC / STATE GENERALIZATION AUDIT
================================================================================

PURPOSE
-------
Diagnostic-only investigation of MLAI v4.1.0.

THIS VERSION DOES NOT:
    - modify market_data.bin
    - modify production MLAI
    - modify learning memory
    - modify the v4.1.0 validation artifact
    - tune OOS data
    - change prediction thresholds
    - enable trading
    - perform live inference

THIS VERSION DOES:
    1. Re-run the v4.1.0 causal pipeline.
    2. Verify chronological integrity.
    3. Verify causal structure integrity.
    4. Audit state fragmentation.
    5. Compare raw state identity vs structural state identity.
    6. Audit signal/event distribution.
    7. Audit walk-forward coverage.
    8. Audit abstention.
    9. Inspect v4.1.0 model-result structures.
   10. Audit event/OOS distribution without double-counting training events.
   11. Produce a diagnostic artifact and report.

IMPORTANT
---------
This file does NOT modify the baseline engine.

Baseline:
    mlai_market_structure_v411.py

Research only.
================================================================================
"""

from __future__ import annotations

import json
import pickle
import hashlib
import statistics

from collections import Counter, defaultdict
from dataclasses import asdict, is_dataclass


# ==============================================================================
# IMPORT BASELINE
# ==============================================================================

import mlai_market_structure_v411 as BASE


# ==============================================================================
# VERSION / FILES
# ==============================================================================

VERSION = "4.1.1-DIAGNOSTIC"

MARKET_DATA_FILE = getattr(
    BASE,
    "MARKET_DATA_FILE",
    "market_data.bin",
)

SOURCE_VALIDATION_BIN = getattr(
    BASE,
    "VALIDATION_BIN",
    "MLAI_V410_ROBUST_PREDICTIVE_WALKFORWARD_VALIDATION.bin",
)

DIAGNOSTIC_REPORT = (
    "MLAI_V411_DIAGNOSTIC_REPORT.md"
)

DIAGNOSTIC_BIN = (
    "MLAI_V411_DIAGNOSTIC_ARTIFACT.bin"
)


# ==============================================================================
# SAFE HELPERS
# ==============================================================================

def safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def safe_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default


def safe_div(a, b):
    try:
        if float(b) == 0:
            return 0.0

        return float(a) / float(b)

    except Exception:
        return 0.0


def pct(value):
    return f"{safe_float(value) * 100.0:.2f}%"


def mean(values):
    values = list(values)

    if not values:
        return 0.0

    return sum(values) / len(values)


def sha256_file(path):

    h = hashlib.sha256()

    with open(path, "rb") as f:

        while True:

            chunk = f.read(1024 * 1024)

            if not chunk:
                break

            h.update(chunk)

    return h.hexdigest()


# ==============================================================================
# GENERIC OBJECT HELPERS
# ==============================================================================

def object_to_dict(obj):

    if obj is None:
        return None

    if is_dataclass(obj):

        try:
            return asdict(obj)
        except Exception:
            pass

    if isinstance(obj, dict):
        return dict(obj)

    if isinstance(obj, (list, tuple)):
        return list(obj)

    if hasattr(obj, "__dict__"):

        try:
            return dict(vars(obj))
        except Exception:
            pass

    return {
        "value": str(obj)
    }


def get_attr(obj, names, default=None):

    if obj is None:
        return default

    for name in names:

        if isinstance(obj, dict):

            if name in obj:
                return obj[name]

        if hasattr(obj, name):

            try:
                return getattr(obj, name)
            except Exception:
                pass

    return default


# ==============================================================================
# SIGNAL EXTRACTION
# ==============================================================================

def signal_event(signal):

    return get_attr(
        signal,
        [
            "event",
            "structural_event",
            "signal_event",
        ],
        None,
    )


def signal_state(signal):

    return get_attr(
        signal,
        [
            "state",
            "state_id",
            "state_key",
            "market_state",
            "structure_state",
        ],
        None,
    )


def signal_index(signal):

    return get_attr(
        signal,
        [
            "index",
            "i",
            "position",
            "candle_index",
        ],
        None,
    )


# ==============================================================================
# STATE REPRESENTATION
# ==============================================================================

VOLATILE_STATE_FIELDS = {
    "index",
    "i",
    "position",
    "candle_index",
    "timestamp",
    "time",
    "datetime",
    "date",
    "created_at",
    "updated_at",
    "id",
    "object_id",
}


def raw_state_key(state):

    if state is None:
        return "NONE"

    if isinstance(
        state,
        (str, int, float, bool),
    ):
        return str(state)

    data = object_to_dict(state)

    try:

        return json.dumps(
            data,
            sort_keys=True,
            default=str,
        )

    except Exception:

        return str(data)


def structural_state_key(state):

    """
    Diagnostic canonical state.

    Observation-specific fields are removed ONLY for this audit.

    The actual MLAI state is NOT changed.
    """

    if state is None:
        return "NONE"

    if isinstance(
        state,
        (str, int, float, bool),
    ):
        return str(state)

    data = object_to_dict(state)

    if not isinstance(data, dict):
        return str(data)

    canonical = {}

    for key, value in data.items():

        key_string = str(key)

        if key_string.startswith("_"):
            continue

        if key_string.lower() in VOLATILE_STATE_FIELDS:
            continue

        canonical[key_string] = value

    try:

        return json.dumps(
            canonical,
            sort_keys=True,
            default=str,
        )

    except Exception:

        return str(canonical)


# ==============================================================================
# STATE FREQUENCY AUDIT
# ==============================================================================

def audit_state_frequency(states):

    frequencies = Counter()

    for state in states:

        frequencies[
            structural_state_key(state)
        ] += 1

    total = len(states)

    singleton = sum(
        1
        for n in frequencies.values()
        if n == 1
    )

    two_occurrence = sum(
        1
        for n in frequencies.values()
        if n == 2
    )

    three_to_five = sum(
        1
        for n in frequencies.values()
        if 3 <= n <= 5
    )

    six_to_ten = sum(
        1
        for n in frequencies.values()
        if 6 <= n <= 10
    )

    over_ten = sum(
        1
        for n in frequencies.values()
        if n > 10
    )

    return {
        "total_observations": total,
        "unique_states": len(frequencies),
        "singleton_states": singleton,
        "two_occurrence_states": two_occurrence,
        "three_to_five_states": three_to_five,
        "six_to_ten_states": six_to_ten,
        "over_ten_states": over_ten,
        "max_state_frequency": (
            max(frequencies.values())
            if frequencies
            else 0
        ),
        "mean_state_frequency": (
            mean(frequencies.values())
            if frequencies
            else 0.0
        ),
        "median_state_frequency": (
            statistics.median(
                frequencies.values()
            )
            if frequencies
            else 0.0
        ),
    }


def audit_raw_vs_structural_states(states):

    raw_counter = Counter()
    structural_counter = Counter()

    for state in states:

        raw_counter[
            raw_state_key(state)
        ] += 1

        structural_counter[
            structural_state_key(state)
        ] += 1

    raw_singletons = sum(
        1
        for n in raw_counter.values()
        if n == 1
    )

    structural_singletons = sum(
        1
        for n in structural_counter.values()
        if n == 1
    )

    return {
        "observations": len(states),

        "raw_unique": len(raw_counter),

        "raw_singletons": raw_singletons,

        "raw_unique_ratio": safe_div(
            len(raw_counter),
            len(states),
        ),

        "raw_singleton_ratio": safe_div(
            raw_singletons,
            len(raw_counter),
        ),

        "structural_unique": len(
            structural_counter
        ),

        "structural_singletons": (
            structural_singletons
        ),

        "structural_unique_ratio": safe_div(
            len(structural_counter),
            len(states),
        ),

        "structural_singleton_ratio": safe_div(
            structural_singletons,
            len(structural_counter),
        ),

        "maximum_structural_frequency": (
            max(structural_counter.values())
            if structural_counter
            else 0
        ),

        "median_structural_frequency": (
            statistics.median(
                structural_counter.values()
            )
            if structural_counter
            else 0.0
        ),
    }


# ==============================================================================
# SIGNAL DISTRIBUTION
# ==============================================================================

def audit_signal_distribution(signals):

    events = Counter()
    states = Counter()
    indices = []

    for signal in signals:

        event = signal_event(signal)

        if event is not None:
            events[str(event)] += 1

        state = signal_state(signal)

        if state is not None:
            states[
                structural_state_key(state)
            ] += 1

        idx = signal_index(signal)

        if idx is not None:
            indices.append(idx)

    return {
        "signals": len(signals),
        "events": dict(events),
        "states": dict(states),
        "indices": indices,
    }


# ==============================================================================
# RESULT STRUCTURE INSPECTION
# ==============================================================================

def inspect_window_result(result):

    information = {
        "top_level_keys": [],
        "horizons": {},
    }

    if not isinstance(result, dict):
        return information

    information["top_level_keys"] = list(
        result.keys()
    )

    horizons = result.get(
        "horizons",
        {},
    )

    if not isinstance(horizons, dict):
        return information

    for horizon, data in horizons.items():

        entry = {
            "keys": [],
            "train_count": None,
            "oos_count": None,
            "encoder_states": None,
            "result_keys": [],
            "abstained": None,
            "coverage": None,
            "accuracy": None,
            "balanced_accuracy": None,
            "baseline_accuracy": None,
            "edge": None,
            "brier_score": None,
            "log_loss": None,
            "calibration_error": None,
        }

        if isinstance(data, dict):

            entry["keys"] = list(
                data.keys()
            )

            entry["train_count"] = data.get(
                "train_count"
            )

            entry["oos_count"] = data.get(
                "oos_count"
            )

            entry["encoder_states"] = data.get(
                "encoder_states"
            )

            result_data = data.get(
                "result"
            )

            if isinstance(
                result_data,
                dict,
            ):

                entry["result_keys"] = list(
                    result_data.keys()
                )

                for field in (
                    "abstained",
                    "coverage",
                    "accuracy",
                    "balanced_accuracy",
                    "baseline_accuracy",
                    "edge",
                    "brier_score",
                    "log_loss",
                    "calibration_error",
                ):

                    entry[field] = result_data.get(
                        field
                    )

        information[
            "horizons"
        ][str(horizon)] = entry

    return information


# ==============================================================================
# COVERAGE AUDIT
# ==============================================================================

def coverage_summary(window_results):

    summary = defaultdict(
        lambda: {
            "windows": 0,
            "oos": 0,
            "predicted": 0,
            "abstained": 0,
            "coverage_values": [],
        }
    )

    for window in window_results:

        horizons = window.get(
            "horizons",
            {},
        )

        for horizon, data in horizons.items():

            result = data.get(
                "result",
                {},
            )

            if not isinstance(
                result,
                dict,
            ):
                continue

            oos = safe_int(
                data.get(
                    "oos_count",
                    0,
                )
            )

            abstained = safe_int(
                result.get(
                    "abstained",
                    0,
                )
            )

            predicted = max(
                0,
                oos - abstained,
            )

            coverage = safe_float(
                result.get(
                    "coverage",
                    0.0,
                )
            )

            h = str(horizon)

            summary[h]["windows"] += 1
            summary[h]["oos"] += oos
            summary[h]["predicted"] += predicted
            summary[h]["abstained"] += abstained

            summary[h][
                "coverage_values"
            ].append(
                coverage
            )

    for h, data in summary.items():

        data["global_coverage"] = safe_div(
            data["predicted"],
            data["oos"],
        )

        data[
            "global_abstention_rate"
        ] = safe_div(
            data["abstained"],
            data["oos"],
        )

        data[
            "mean_window_coverage"
        ] = mean(
            data["coverage_values"]
        )

    return dict(summary)


# ==============================================================================
# EVENT / OOS AUDIT
# ==============================================================================

def independent_event_audit(
    signals,
    windows,
):

    """
    Counts UNIQUE event observations.

    Important:
    Walk-forward training windows overlap.

    Therefore training membership must NOT simply be summed
    across all windows.

    This prevents impossible results such as:

        Total = 23
        Training = 96
    """

    target_events = (
        "BOS_BULLISH",
        "BOS_BEARISH",
        "CHoCH_BULLISH",
        "CHoCH_BEARISH",
    )

    result = {}

    for event in target_events:

        result[event] = {
            "total": 0,
            "train": 0,
            "oos": 0,
            "windows": Counter(),
            "indices": [],
        }

    event_indices = defaultdict(set)

    for signal in signals:

        event = signal_event(signal)
        idx = signal_index(signal)

        if event not in result:
            continue

        if idx is None:
            continue

        try:
            idx = int(idx)
        except Exception:
            continue

        event_indices[event].add(idx)

    oos_ranges = []

    for window in windows:

        start = getattr(
            window,
            "oos_start",
            None,
        )

        end = getattr(
            window,
            "oos_end",
            None,
        )

        number = getattr(
            window,
            "number",
            "?",
        )

        if (
            start is not None
            and end is not None
        ):

            oos_ranges.append(
                (
                    int(start),
                    int(end),
                    number,
                )
            )

    for event, indices in event_indices.items():

        ordered = sorted(indices)

        result[event]["total"] = len(
            ordered
        )

        result[event]["indices"] = ordered

        for idx in ordered:

            matched_oos = False

            for (
                oos_start,
                oos_end,
                number,
            ) in oos_ranges:

                if (
                    oos_start
                    <= idx
                    < oos_end
                ):

                    result[event]["oos"] += 1

                    result[event][
                        "windows"
                    ][number] += 1

                    matched_oos = True

                    break

            if not matched_oos:
                result[event]["train"] += 1

    return result


# ==============================================================================
# DIAGNOSIS
# ==============================================================================

def diagnose(
    state_audit,
    state_identity_audit,
    coverage,
    event_audit,
):

    findings = []
    severity = []

    total = state_audit[
        "total_observations"
    ]

    unique = state_audit[
        "unique_states"
    ]

    singleton = state_audit[
        "singleton_states"
    ]

    if total > 0:

        uniqueness_ratio = safe_div(
            unique,
            total,
        )

        singleton_ratio = safe_div(
            singleton,
            unique,
        )

        if uniqueness_ratio > 0.50:

            findings.append(
                "HIGH structural state fragmentation: "
                f"{unique} structural states across "
                f"{total} observations."
            )

            severity.append(
                "HIGH"
            )

        if singleton_ratio > 0.40:

            findings.append(
                "HIGH singleton concentration: "
                f"{singleton} of {unique} structural states "
                f"occur only once "
                f"({pct(singleton_ratio)})."
            )

            severity.append(
                "HIGH"
            )

    raw_unique = state_identity_audit[
        "raw_unique"
    ]

    structural_unique = state_identity_audit[
        "structural_unique"
    ]

    if (
        raw_unique
        > structural_unique
    ):

        reduction = (
            1.0
            - safe_div(
                structural_unique,
                raw_unique,
            )
        )

        findings.append(
            "RAW vs STRUCTURAL state identity: "
            f"canonical structural representation reduces "
            f"unique states by {pct(reduction)}."
        )

    for horizon, data in coverage.items():

        global_coverage = data[
            "global_coverage"
        ]

        if global_coverage == 0:

            findings.append(
                f"H+{horizon}: ZERO prediction coverage."
            )

            severity.append(
                "HIGH"
            )

        elif global_coverage < 0.10:

            findings.append(
                f"H+{horizon}: extremely low coverage "
                f"({pct(global_coverage)})."
            )

            severity.append(
                "HIGH"
            )

        elif global_coverage < 0.25:

            findings.append(
                f"H+{horizon}: low coverage "
                f"({pct(global_coverage)})."
            )

            severity.append(
                "MEDIUM"
            )

    for event, data in event_audit.items():

        findings.append(
            f"{event}: "
            f"{data['total']} total unique events, "
            f"{data['train']} outside OOS, "
            f"{data['oos']} inside OOS."
        )

    if not findings:

        findings.append(
            "No major automatic diagnostic anomaly detected."
        )

    if "HIGH" in severity:

        overall = (
            "HIGH PRIORITY DIAGNOSTIC ISSUE"
        )

    elif "MEDIUM" in severity:

        overall = (
            "MEDIUM PRIORITY DIAGNOSTIC ISSUE"
        )

    else:

        overall = (
            "NO AUTOMATIC HIGH-SEVERITY ISSUE"
        )

    return {
        "overall": overall,
        "findings": findings,
        "severity": severity,
    }


# ==============================================================================
# REPORT
# ==============================================================================

def build_report(
    protection_before,
    protection_after,
    candles,
    invalid,
    chronology,
    swings,
    states,
    events,
    signals,
    state_audit,
    state_identity_audit,
    signal_audit,
    coverage,
    event_audit,
    window_inspection,
    diagnosis,
):

    lines = []

    def add(text=""):
        lines.append(text)

    add(
        "# MLAI v4.1.1 Diagnostic / State Generalization Audit"
    )

    add()

    add("## Protection")
    add()
    add(
        f"- Market data SHA256 before: "
        f"`{protection_before}`"
    )
    add(
        f"- Market data SHA256 after: "
        f"`{protection_after}`"
    )
    add(
        "- Market data unchanged: "
        + (
            "PASS"
            if protection_before
            == protection_after
            else "FAIL"
        )
    )
    add("- Production MLAI modified: NO")
    add("- Learning memory modified: NO")
    add("- Trading: DISABLED")
    add()

    add("## Dataset")
    add()
    add(
        f"- Valid candles: {len(candles)}"
    )
    add(
        f"- Invalid candles: {invalid}"
    )
    add(
        f"- Chronological order: "
        f"{chronology.get('ordered')}"
    )
    add(
        f"- Duplicate timestamps: "
        f"{chronology.get('duplicates')}"
    )
    add()

    add("## Causal Structure")
    add()
    add(
        f"- Confirmed swings: {len(swings)}"
    )
    add(
        f"- Structure states: {len(states)}"
    )
    add(
        f"- Structural events: {len(events)}"
    )
    add(
        f"- Signals: {len(signals)}"
    )
    add()

    add("## Structural Events")
    add()

    event_counts = Counter(
        events.values()
    )

    for event in (
        "BOS_BULLISH",
        "BOS_BEARISH",
        "CHoCH_BULLISH",
        "CHoCH_BEARISH",
    ):

        add(
            f"- {event}: "
            f"{event_counts.get(event, 0)}"
        )

    add()

    add("## State Fragmentation")
    add()

    add(
        f"- Observations: "
        f"{state_audit['total_observations']}"
    )

    add(
        f"- Structural unique states: "
        f"{state_audit['unique_states']}"
    )

    add(
        f"- Structural singleton states: "
        f"{state_audit['singleton_states']}"
    )

    add(
        f"- 2-occurrence states: "
        f"{state_audit['two_occurrence_states']}"
    )

    add(
        f"- 3-5 occurrence states: "
        f"{state_audit['three_to_five_states']}"
    )

    add(
        f"- 6-10 occurrence states: "
        f"{state_audit['six_to_ten_states']}"
    )

    add(
        f"- >10 occurrence states: "
        f"{state_audit['over_ten_states']}"
    )

    add(
        f"- Maximum frequency: "
        f"{state_audit['max_state_frequency']}"
    )

    add(
        f"- Median frequency: "
        f"{state_audit['median_state_frequency']:.2f}"
    )

    add()

    add("### Raw vs Structural Identity")
    add()

    add(
        f"- Raw unique states: "
        f"{state_identity_audit['raw_unique']}"
    )

    add(
        f"- Structural unique states: "
        f"{state_identity_audit['structural_unique']}"
    )

    add(
        f"- Raw singleton ratio: "
        f"{pct(state_identity_audit['raw_singleton_ratio'])}"
    )

    add(
        f"- Structural singleton ratio: "
        f"{pct(state_identity_audit['structural_singleton_ratio'])}"
    )

    add(
        f"- Maximum structural frequency: "
        f"{state_identity_audit['maximum_structural_frequency']}"
    )

    add(
        f"- Median structural frequency: "
        f"{state_identity_audit['median_structural_frequency']:.2f}"
    )

    add()

    add("## Signal Distribution")
    add()

    add(
        f"- Total signals: "
        f"{signal_audit['signals']}"
    )

    for event, count in sorted(
        signal_audit["events"].items()
    ):

        add(
            f"- {event}: {count}"
        )

    add()

    add("## OOS Coverage")
    add()

    for horizon, data in sorted(
        coverage.items(),
        key=lambda x: int(x[0]),
    ):

        add(
            f"### H+{horizon}"
        )

        add(
            f"- OOS: {data['oos']}"
        )

        add(
            f"- Predictions: {data['predicted']}"
        )

        add(
            f"- Abstentions: {data['abstained']}"
        )

        add(
            f"- Coverage: "
            f"{pct(data['global_coverage'])}"
        )

        add(
            f"- Abstention rate: "
            f"{pct(data['global_abstention_rate'])}"
        )

        add()

    add("## Independent Event Audit")
    add()

    for event, data in event_audit.items():

        add(
            f"### {event}"
        )

        add(
            f"- Total unique events: "
            f"{data['total']}"
        )

        add(
            f"- Outside OOS: "
            f"{data['train']}"
        )

        add(
            f"- OOS: "
            f"{data['oos']}"
        )

        for window, count in sorted(
            data["windows"].items()
        ):

            add(
                f"- Window {window}: {count}"
            )

        add()

    add("## Model Result Structure")
    add()

    for window, information in sorted(
        window_inspection.items(),
        key=lambda x: str(x[0]),
    ):

        add(
            f"### Window {window}"
        )

        add(
            f"- Top-level keys: "
            f"{information['top_level_keys']}"
        )

        for horizon, h in information[
            "horizons"
        ].items():

            add(
                f"- H+{horizon}: "
                f"train={h.get('train_count')} | "
                f"oos={h.get('oos_count')} | "
                f"states={h.get('encoder_states')}"
            )

            add(
                f"  result keys: "
                f"{h.get('result_keys')}"
            )

        add()

    add("## Automatic Diagnosis")
    add()

    add(
        f"### {diagnosis['overall']}"
    )

    add()

    for finding in diagnosis[
        "findings"
    ]:

        add(
            f"- {finding}"
        )

    add()

    add("## Scientific Interpretation")
    add()

    add(
        "The v4.1.0 H+4/H+8 zero-accuracy result "
        "must not be interpreted as ordinary 0% predictive "
        "accuracy because the model abstained on all tested "
        "observations."
    )

    add()

    add(
        "The first investigation is therefore prediction "
        "coverage and state support rather than threshold "
        "optimization."
    )

    add()

    add(
        "Raw state identity and canonical structural state "
        "identity are reported separately so that observation-"
        "specific fields cannot automatically be mistaken "
        "for distinct market regimes."
    )

    add()

    add(
        "Walk-forward training-event counts are treated as "
        "unique event observations rather than summed across "
        "overlapping training windows."
    )

    add()

    add(
        "No predictive rule has been promoted from this audit."
    )

    add()

    add(
        "MLAI v4.1.1 DIAGNOSTIC AUDIT COMPLETE"
    )

    return "\n".join(lines)


# ==============================================================================
# MAIN
# ==============================================================================

def main():

    print("=" * 88)
    print(
        "MLAI v4.1.1 DIAGNOSTIC / STATE GENERALIZATION AUDIT"
    )
    print("=" * 88)

    print()
    print("DIAGNOSTIC ONLY")

    print()
    print("=" * 88)
    print("PROTECTION CHECK")
    print("=" * 88)

    print(
        f"{MARKET_DATA_FILE:<30}: READ ONLY"
    )

    print(
        "Production MLAI              : NOT MODIFIED"
    )

    print(
        "Learning memory              : NOT MODIFIED"
    )

    print(
        "Trading                      : DISABLED"
    )

    print(
        "OOS tuning                   : DISABLED"
    )

    # ==========================================================================
    # PROTECTION BEFORE
    # ==========================================================================

    protection_before = sha256_file(
        MARKET_DATA_FILE
    )

    # ==========================================================================
    # DATA LOAD
    # ==========================================================================

    print()
    print("=" * 88)
    print("DATA LOAD")
    print("=" * 88)

    candles, invalid = BASE.load_market_data(
        MARKET_DATA_FILE
    )

    print(
        f"Valid candles                : {len(candles)}"
    )

    print(
        f"Invalid candles              : {invalid}"
    )

    if len(candles) < 500:

        raise RuntimeError(
            "Insufficient candle history."
        )

    # ==========================================================================
    # CHRONOLOGY
    # ==========================================================================

    print()
    print("=" * 88)
    print("CHRONOLOGICAL AUDIT")
    print("=" * 88)

    chronology = BASE.audit_chronology(
        candles
    )

    print(
        "Timestamp order              : "
        + (
            "PASS"
            if chronology["ordered"]
            else "FAIL"
        )
    )

    print(
        "Duplicate timestamps         : "
        + (
            "PASS"
            if not chronology["duplicates"]
            else "FAIL"
        )
    )

    if not chronology["ordered"]:

        raise RuntimeError(
            "Chronological ordering failed."
        )

    if chronology["duplicates"]:

        raise RuntimeError(
            "Duplicate timestamps detected."
        )

    # ==========================================================================
    # ATR
    # ==========================================================================

    print()
    print("=" * 88)
    print("CAUSAL FEATURE PREPARATION")
    print("=" * 88)

    atr = BASE.calculate_atr(
        candles
    )

    print(
        "ATR observations             : "
        f"{sum(x is not None for x in atr)}"
    )

    # ==========================================================================
    # CAUSAL STRUCTURE
    # ==========================================================================

    print()
    print("=" * 88)
    print("CAUSAL STRUCTURE")
    print("=" * 88)

    engine = BASE.CausalStructureEngine(
        candles
    )

    states = engine.build()

    swings = engine.swings
    events = engine.events

    print(
        "Confirmed swings             : "
        f"{len(swings)}"
    )

    print(
        "Structure states             : "
        f"{len(states)}"
    )

    print(
        "Structural events            : "
        f"{len(events)}"
    )

    # ==========================================================================
    # CAUSALITY
    # ==========================================================================

    print()
    print("=" * 88)
    print("CAUSALITY AUDIT")
    print("=" * 88)

    causality = BASE.audit_structure_causality(
        candles,
        swings,
        states,
        events,
    )

    print(
        "Causality                     : "
        + (
            "PASS"
            if causality["passed"]
            else "FAIL"
        )
    )

    if not causality["passed"]:

        for reason in causality.get(
            "reasons",
            [],
        ):

            print(
                "Reason                       : "
                f"{reason}"
            )

        raise RuntimeError(
            "Causality audit failed."
        )

    # ==========================================================================
    # SIGNALS
    # ==========================================================================

    print()
    print("=" * 88)
    print("SIGNAL DATASET")
    print("=" * 88)

    signals = BASE.create_signals(
        candles,
        states,
        atr,
    )

    print(
        "Signal records                : "
        f"{len(signals)}"
    )

    # ==========================================================================
    # STATE AUDIT
    # ==========================================================================

    print()
    print("=" * 88)
    print("STATE FRAGMENTATION AUDIT")
    print("=" * 88)

    state_audit = audit_state_frequency(
        states
    )

    state_identity_audit = (
        audit_raw_vs_structural_states(
            states
        )
    )

    print(
        "State observations            : "
        f"{state_audit['total_observations']}"
    )

    print(
        "Unique structural states      : "
        f"{state_audit['unique_states']}"
    )

    print(
        "Singleton states              : "
        f"{state_audit['singleton_states']}"
    )

    print(
        "2-occurrence states           : "
        f"{state_audit['two_occurrence_states']}"
    )

    print(
        "3-5 occurrence states         : "
        f"{state_audit['three_to_five_states']}"
    )

    print(
        "6-10 occurrence states        : "
        f"{state_audit['six_to_ten_states']}"
    )

    print(
        ">10 occurrence states         : "
        f"{state_audit['over_ten_states']}"
    )

    print(
        "Maximum state frequency       : "
        f"{state_audit['max_state_frequency']}"
    )

    print(
        "Median state frequency        : "
        f"{state_audit['median_state_frequency']:.2f}"
    )

    print()

    print(
        "Raw unique states             : "
        f"{state_identity_audit['raw_unique']}"
    )

    print(
        "Structural unique states      : "
        f"{state_identity_audit['structural_unique']}"
    )

    print(
        "Raw singleton ratio           : "
        f"{pct(state_identity_audit['raw_singleton_ratio'])}"
    )

    print(
        "Structural singleton ratio    : "
        f"{pct(state_identity_audit['structural_singleton_ratio'])}"
    )

    print(
        "Maximum structural frequency  : "
        f"{state_identity_audit['maximum_structural_frequency']}"
    )

    print(
        "Median structural frequency   : "
        f"{state_identity_audit['median_structural_frequency']:.2f}"
    )

    # ==========================================================================
    # SIGNAL AUDIT
    # ==========================================================================

    print()
    print("=" * 88)
    print("SIGNAL / EVENT DISTRIBUTION")
    print("=" * 88)

    signal_audit = audit_signal_distribution(
        signals
    )

    print(
        "Signals                       : "
        f"{signal_audit['signals']}"
    )

    for event, count in sorted(
        signal_audit["events"].items()
    ):

        print(
            f"{event:<30}: {count}"
        )

    # ==========================================================================
    # WALK-FORWARD WINDOWS
    # ==========================================================================

    print()
    print("=" * 88)
    print("WALK-FORWARD WINDOWS")
    print("=" * 88)

    windows = BASE.create_walk_forward_windows(
        len(candles),
        BASE.DEFAULT_TRAIN_WINDOWS,
        BASE.DEFAULT_OOS_SIZE,
    )

    print(
        "Windows created               : "
        f"{len(windows)}"
    )

    for window in windows:

        print(
            f"Window {window.number} | "
            f"TRAIN [{window.train_start}:{window.train_end}] | "
            f"OOS [{window.oos_start}:{window.oos_end}]"
        )

    # ==========================================================================
    # EXISTING VALIDATION
    # ==========================================================================

    print()
    print("=" * 88)
    print("RE-RUNNING EXISTING v4.1.0 VALIDATION")
    print("=" * 88)

    window_results = []

    for window in windows:

        print()
        print(
            f"Window {window.number}"
        )

        result = BASE.run_window(
            candles,
            signals,
            window,
        )

        window_results.append(
            result
        )

        for horizon in BASE.HORIZONS:

            h = result[
                "horizons"
            ][horizon]

            r = h[
                "result"
            ]

            print(
                f"H+{horizon}: "
                f"OOS={h.get('oos_count')} | "
                f"Abstained={r.get('abstained')} | "
                f"Coverage={pct(r.get('coverage', 0))}"
            )

    # ==========================================================================
    # COVERAGE
    # ==========================================================================

    print()
    print("=" * 88)
    print("ABSTENTION / COVERAGE AUDIT")
    print("=" * 88)

    coverage = coverage_summary(
        window_results
    )

    for horizon, data in sorted(
        coverage.items(),
        key=lambda x: int(x[0]),
    ):

        print()
        print(
            f"H+{horizon}"
        )

        print(
            "  OOS observations            : "
            f"{data['oos']}"
        )

        print(
            "  Predictions                 : "
            f"{data['predicted']}"
        )

        print(
            "  Abstentions                 : "
            f"{data['abstained']}"
        )

        print(
            "  Global coverage             : "
            f"{pct(data['global_coverage'])}"
        )

        print(
            "  Abstention rate             : "
            f"{pct(data['global_abstention_rate'])}"
        )

    # ==========================================================================
    # EVENT AUDIT
    # ==========================================================================

    print()
    print("=" * 88)
    print("INDEPENDENT EVENT / OOS AUDIT")
    print("=" * 88)

    event_audit = independent_event_audit(
        signals,
        windows,
    )

    for event, data in event_audit.items():

        print()
        print(event)

        print(
            "  Total unique events        : "
            f"{data['total']}"
        )

        print(
            "  Outside OOS                : "
            f"{data['train']}"
        )

        print(
            "  OOS                        : "
            f"{data['oos']}"
        )

        for window, count in sorted(
            data["windows"].items()
        ):

            print(
                f"  Window {window:<18}: "
                f"{count}"
            )

    # ==========================================================================
    # RESULT STRUCTURE
    # ==========================================================================

    print()
    print("=" * 88)
    print("MODEL RESULT STRUCTURE INSPECTION")
    print("=" * 88)

    window_inspection = {}

    for result in window_results:

        number = result.get(
            "window",
            result.get(
                "number",
                "UNKNOWN",
            ),
        )

        # --------------------------------------------------------------
        # FIX FOR:
        #
        # TypeError:
        # cannot use 'dict' as a dict key
        # --------------------------------------------------------------

        if isinstance(
            number,
            dict,
        ):

            window_number = number.get(
                "number"
            )

            if window_number is None:

                window_number = number.get(
                    "window"
                )

            if window_number is None:

                window_number = "UNKNOWN"

        else:

            window_number = number

        try:

            hash(window_number)

        except TypeError:

            window_number = str(
                window_number
            )

        information = inspect_window_result(
            result
        )

        window_inspection[
            window_number
        ] = information

        print()

        print(
            f"Window {window_number}"
        )

        print(
            "Top-level keys:"
        )

        print(
            information[
                "top_level_keys"
            ]
        )

        for horizon, h in information[
            "horizons"
        ].items():

            print(
                f"H+{horizon}: "
                f"train={h.get('train_count')} | "
                f"oos={h.get('oos_count')} | "
                f"states={h.get('encoder_states')}"
            )

            print(
                "Result keys:"
            )

            print(
                h.get(
                    "result_keys",
                    [],
                )
            )

    # ==========================================================================
    # DIAGNOSIS
    # ==========================================================================

    print()
    print("=" * 88)
    print("AUTOMATIC DIAGNOSIS")
    print("=" * 88)

    diagnosis = diagnose(
        state_audit=state_audit,
        state_identity_audit=state_identity_audit,
        coverage=coverage,
        event_audit=event_audit,
    )

    print()

    print(
        diagnosis["overall"]
    )

    for finding in diagnosis[
        "findings"
    ]:

        print(
            " - "
            + finding
        )

    # ==========================================================================
    # PROTECTION AFTER
    # ==========================================================================

    protection_after = sha256_file(
        MARKET_DATA_FILE
    )

    # ==========================================================================
    # ARTIFACT
    # ==========================================================================

    artifact = {

        "version": VERSION,

        "purpose": (
            "Diagnostic-only investigation "
            "of MLAI v4.1.0"
        ),

        "protection": {

            "market_data": MARKET_DATA_FILE,

            "sha256_before":
                protection_before,

            "sha256_after":
                protection_after,

            "unchanged": (
                protection_before
                == protection_after
            ),

            "production_modified": False,

            "learning_memory_modified":
                False,

            "trading": False,

        },

        "dataset": {

            "candles": len(candles),

            "invalid": invalid,

            "chronology": chronology,

        },

        "structure": {

            "swings": len(swings),

            "states": len(states),

            "events": len(events),

        },

        "state_audit":
            state_audit,

        "state_identity_audit":
            state_identity_audit,

        "signal_audit":
            signal_audit,

        "coverage":
            coverage,

        "event_audit":
            event_audit,

        "window_inspection":
            window_inspection,

        "diagnosis":
            diagnosis,
    }

    with open(
        DIAGNOSTIC_BIN,
        "wb",
    ) as f:

        pickle.dump(
            artifact,
            f,
            protocol=pickle.HIGHEST_PROTOCOL,
        )

    # ==========================================================================
    # REPORT
    # ==========================================================================

    report = build_report(
        protection_before=protection_before,
        protection_after=protection_after,
        candles=candles,
        invalid=invalid,
        chronology=chronology,
        swings=swings,
        states=states,
        events=events,
        signals=signals,
        state_audit=state_audit,
        state_identity_audit=state_identity_audit,
        signal_audit=signal_audit,
        coverage=coverage,
        event_audit=event_audit,
        window_inspection=window_inspection,
        diagnosis=diagnosis,
    )

    with open(
        DIAGNOSTIC_REPORT,
        "w",
        encoding="utf-8",
    ) as f:

        f.write(
            report
        )

    # ==========================================================================
    # FINAL PROTECTION
    # ==========================================================================

    print()
    print("=" * 88)
    print("FINAL PROTECTION CHECK")
    print("=" * 88)

    if (
        protection_before
        != protection_after
    ):

        print(
            "market_data.bin             : FAIL"
        )

        raise RuntimeError(
            "market_data.bin changed."
        )

    print(
        "market_data.bin             : READ ONLY"
    )

    print(
        "Production MLAI             : NOT MODIFIED"
    )

    print(
        "Learning memory             : NOT MODIFIED"
    )

    print(
        "Trading                     : DISABLED"
    )

    print()
    print("=" * 88)
    print("DIAGNOSTIC ARTIFACT")
    print("=" * 88)

    print(
        f"Binary: {DIAGNOSTIC_BIN}"
    )

    print(
        f"Report: {DIAGNOSTIC_REPORT}"
    )

    print()
    print("=" * 88)
    print(
        "MLAI v4.1.1 DIAGNOSTIC AUDIT COMPLETE"
    )
    print("=" * 88)


# ==============================================================================
# ENTRY
# ==============================================================================

if __name__ == "__main__":
    main()