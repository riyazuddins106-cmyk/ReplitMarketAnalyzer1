"""
================================================================================
MLAI v4.1.1 DIAGNOSTIC / STATE GENERALIZATION AUDIT
================================================================================

PURPOSE
-------
Diagnose the v4.1.0 predictive validation result before changing the model.

This version DOES NOT:
    - modify market_data.bin
    - modify production MLAI
    - modify learning memory
    - modify v4.1.0 validation artifact
    - optimize against OOS data
    - tune prediction thresholds
    - enable trading
    - perform live inference

This version DOES:
    1. Re-run the existing v4.1.0 causal pipeline.
    2. Measure state fragmentation.
    3. Measure signal/event distributions.
    4. Measure OOS coverage and abstention.
    5. Inspect model-result structures.
    6. Diagnose event-diagnostic sparsity.
    7. Identify whether the current representation is too fragmented.
    8. Produce a detailed diagnostic report.

BASELINE:
    mlai_market_structure_v411.py

IMPORTANT:
    This file is diagnostic only.
    No predictive rule is promoted from this experiment.
================================================================================
"""

from __future__ import annotations

import os
import json
import pickle
import hashlib
import statistics
from collections import Counter, defaultdict
from dataclasses import asdict, is_dataclass
from typing import Any


# ==============================================================================
# IMPORT BASELINE ENGINE
# ==============================================================================

import mlai_market_structure_v411 as BASE


# ==============================================================================
# VERSION
# ==============================================================================

VERSION = "4.1.1-DIAGNOSTIC"


# ==============================================================================
# FILES
# ==============================================================================

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


def pct(value):
    return f"{safe_float(value) * 100.0:.2f}%"


def fmt(value):
    return f"{safe_float(value):.6f}"


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


def object_to_dict(obj):
    """
    Convert arbitrary project objects into dictionaries without
    assuming their exact dataclass structure.
    """

    if obj is None:
        return None

    if is_dataclass(obj):
        try:
            return asdict(obj)
        except Exception:
            pass

    if isinstance(obj, dict):
        return obj

    if isinstance(obj, (list, tuple)):
        return list(obj)

    if hasattr(obj, "__dict__"):
        try:
            return vars(obj)
        except Exception:
            pass

    return {
        "value": str(obj)
    }


# ==============================================================================
# RECURSIVE INSPECTION
# ==============================================================================

def flatten_keys(obj, prefix=""):
    """
    Recursively collect dictionary/object keys.

    Used only for diagnostics.
    """

    found = set()

    if isinstance(obj, dict):
        for key, value in obj.items():

            key_name = (
                f"{prefix}.{key}"
                if prefix
                else str(key)
            )

            found.add(key_name)

            found.update(
                flatten_keys(
                    value,
                    key_name,
                )
            )

    elif isinstance(obj, (list, tuple)):

        for i, value in enumerate(obj[:10]):

            key_name = (
                f"{prefix}[{i}]"
                if prefix
                else f"[{i}]"
            )

            found.update(
                flatten_keys(
                    value,
                    key_name,
                )
            )

    return found


# ==============================================================================
# ATTRIBUTE EXTRACTION
# ==============================================================================

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

    value = get_attr(
        signal,
        [
            "index",
            "i",
            "position",
            "candle_index",
        ],
        None,
    )

    return value


# ==============================================================================
# STATE EXTRACTION
# ==============================================================================

def state_key(state):

    """
    Convert a structure state into a stable diagnostic key.

    We intentionally do not alter the state representation.
    """

    if state is None:
        return "NONE"

    if isinstance(state, (str, int, float, bool)):
        return str(state)

    if is_dataclass(state):

        try:
            data = asdict(state)

            return json.dumps(
                data,
                sort_keys=True,
                default=str,
            )

        except Exception:
            return str(state)

    if isinstance(state, dict):

        try:
            return json.dumps(
                state,
                sort_keys=True,
                default=str,
            )

        except Exception:
            return str(state)

    if hasattr(state, "__dict__"):

        try:
            return json.dumps(
                vars(state),
                sort_keys=True,
                default=str,
            )

        except Exception:
            return str(state)

    return str(state)


# ==============================================================================
# STATE FREQUENCY AUDIT
# ==============================================================================

def audit_state_frequency(states):

    frequencies = Counter()

    for state in states:
        frequencies[state_key(state)] += 1

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
            statistics.median(frequencies.values())
            if frequencies
            else 0.0
        ),
        "frequency_distribution": dict(
            sorted(
                frequencies.items(),
                key=lambda x: x[1],
                reverse=True,
            )
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
            states[state_key(state)] += 1

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
# RESULT INSPECTION
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

            r = data.get(
                "result"
            )

            if isinstance(r, dict):

                entry["result_keys"] = list(
                    r.keys()
                )

                entry["abstained"] = r.get(
                    "abstained"
                )

                entry["coverage"] = r.get(
                    "coverage"
                )

                entry["accuracy"] = r.get(
                    "accuracy"
                )

                entry["balanced_accuracy"] = r.get(
                    "balanced_accuracy"
                )

                entry["baseline_accuracy"] = r.get(
                    "baseline_accuracy"
                )

                entry["edge"] = r.get(
                    "edge"
                )

                entry["brier_score"] = r.get(
                    "brier_score"
                )

                entry["log_loss"] = r.get(
                    "log_loss"
                )

                entry["calibration_error"] = r.get(
                    "calibration_error"
                )

        information["horizons"][str(horizon)] = entry

    return information


# ==============================================================================
# ABSTENTION AUDIT
# ==============================================================================

def audit_abstention(window_results):

    output = {}

    for window in window_results:

        number = window.get(
            "window",
            window.get(
                "number",
                "UNKNOWN",
            ),
        )

        horizons = window.get(
            "horizons",
            {},
        )

        output[number] = {}

        for horizon, data in horizons.items():

            r = data.get(
                "result",
                {},
            )

            if not isinstance(r, dict):
                continue

            oos_count = safe_int(
                data.get(
                    "oos_count",
                    0,
                )
            )

            abstained = safe_int(
                r.get(
                    "abstained",
                    0,
                )
            )

            coverage = safe_float(
                r.get(
                    "coverage",
                    0.0,
                )
            )

            predicted = max(
                0,
                oos_count - abstained,
            )

            output[number][str(horizon)] = {
                "oos": oos_count,
                "predicted": predicted,
                "abstained": abstained,
                "coverage": coverage,
                "abstention_rate": (
                    safe_div(
                        abstained,
                        oos_count,
                    )
                ),
            }

    return output


def safe_div(a, b):

    try:
        if b == 0:
            return 0.0

        return float(a) / float(b)

    except Exception:
        return 0.0


# ==============================================================================
# EVENT DIAGNOSTIC AUDIT
# ==============================================================================

def independent_event_audit(
    signals,
    windows,
):

    """
    Independent event counting.

    This does NOT calculate predictive performance.

    It verifies whether events actually occur inside
    the OOS windows and whether the current event diagnostic
    system is unnecessarily filtering them.
    """

    result = {}

    for event in (
        "BOS_BULLISH",
        "BOS_BEARISH",
        "CHoCH_BULLISH",
        "CHoCH_BEARISH",
    ):
        result[event] = {
            "total": 0,
            "train": 0,
            "oos": 0,
            "windows": Counter(),
        }

    for signal in signals:

        event = signal_event(signal)
        idx = signal_index(signal)

        if event not in result:
            continue

        result[event]["total"] += 1

        if idx is None:
            continue

        for window in windows:

            train_start = getattr(
                window,
                "train_start",
                None,
            )

            train_end = getattr(
                window,
                "train_end",
                None,
            )

            oos_start = getattr(
                window,
                "oos_start",
                None,
            )

            oos_end = getattr(
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
                train_start is not None
                and train_end is not None
                and train_start <= idx < train_end
            ):
                result[event]["train"] += 1

            if (
                oos_start is not None
                and oos_end is not None
                and oos_start <= idx < oos_end
            ):
                result[event]["oos"] += 1
                result[event]["windows"][number] += 1

    return result


# ==============================================================================
# COVERAGE SUMMARY
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

            r = data.get(
                "result",
                {},
            )

            if not isinstance(r, dict):
                continue

            oos = safe_int(
                data.get(
                    "oos_count",
                    0,
                )
            )

            abstained = safe_int(
                r.get(
                    "abstained",
                    0,
                )
            )

            predicted = max(
                0,
                oos - abstained,
            )

            coverage = safe_float(
                r.get(
                    "coverage",
                    0.0,
                )
            )

            h = str(horizon)

            summary[h]["windows"] += 1
            summary[h]["oos"] += oos
            summary[h]["predicted"] += predicted
            summary[h]["abstained"] += abstained
            summary[h]["coverage_values"].append(
                coverage
            )

    for h, data in summary.items():

        data["global_coverage"] = safe_div(
            data["predicted"],
            data["oos"],
        )

        data["global_abstention_rate"] = safe_div(
            data["abstained"],
            data["oos"],
        )

        data["mean_window_coverage"] = mean(
            data["coverage_values"]
        )

    return dict(summary)


# ==============================================================================
# DIAGNOSTIC INTERPRETATION
# ==============================================================================

def diagnose(
    state_audit,
    coverage,
    event_audit,
):

    findings = []
    severity = []

    # --------------------------------------------------------------------------
    # STATE FRAGMENTATION
    # --------------------------------------------------------------------------

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

        if uniqueness_ratio > 0.10:

            findings.append(
                "STATE FRAGMENTATION: "
                f"{unique} unique states across {total} observations "
                f"({pct(uniqueness_ratio)} unique/observation ratio)."
            )

        if singleton_ratio > 0.40:

            severity.append(
                "HIGH"
            )

            findings.append(
                "HIGH STATE FRAGMENTATION: "
                f"{singleton} of {unique} states are singletons "
                f"({pct(singleton_ratio)}). "
                "Historical state learning may be too sparse."
            )

    # --------------------------------------------------------------------------
    # COVERAGE
    # --------------------------------------------------------------------------

    for horizon, data in coverage.items():

        global_coverage = data[
            "global_coverage"
        ]

        if global_coverage == 0:

            severity.append(
                "HIGH"
            )

            findings.append(
                f"H+{horizon}: ZERO prediction coverage "
                "across all available OOS observations."
            )

        elif global_coverage < 0.10:

            severity.append(
                "HIGH"
            )

            findings.append(
                f"H+{horizon}: extremely low coverage "
                f"({pct(global_coverage)})."
            )

        elif global_coverage < 0.25:

            severity.append(
                "MEDIUM"
            )

            findings.append(
                f"H+{horizon}: low coverage "
                f"({pct(global_coverage)})."
            )

    # --------------------------------------------------------------------------
    # EVENT DIAGNOSTICS
    # --------------------------------------------------------------------------

    for event, data in event_audit.items():

        if data["total"] > 0 and data["oos"] == 0:

            findings.append(
                f"{event}: {data['total']} total events exist "
                "but none occur inside the tested OOS windows."
            )

        elif data["oos"] > 0:

            findings.append(
                f"{event}: {data['oos']} OOS events are available "
                "for independent diagnostic analysis."
            )

    # --------------------------------------------------------------------------
    # FINAL DIAGNOSIS
    # --------------------------------------------------------------------------

    if not findings:

        findings.append(
            "No major diagnostic anomaly was automatically detected."
        )

    if "HIGH" in severity:

        overall = "HIGH PRIORITY DIAGNOSTIC ISSUE"

    elif "MEDIUM" in severity:

        overall = "MEDIUM PRIORITY DIAGNOSTIC ISSUE"

    else:

        overall = "NO AUTOMATIC HIGH-SEVERITY ISSUE"

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
    chronology,
    swings,
    states,
    events,
    signals,
    state_audit,
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

    add("## Purpose")
    add()
    add(
        "This is a diagnostic-only investigation of MLAI v4.1.0."
    )
    add(
        "No predictive rule, threshold, model, or production component "
        "was modified."
    )
    add()

    add("## Protection")
    add()
    add(
        f"- Market data SHA256 before: `{protection_before}`"
    )
    add(
        f"- Market data SHA256 after: `{protection_after}`"
    )
    add(
        "- Market data modification: "
        + (
            "NO"
            if protection_before == protection_after
            else "FAIL"
        )
    )
    add("- Production MLAI modification: NO")
    add("- Learning memory modification: NO")
    add("- Trading: DISABLED")
    add()

    add("## Dataset")
    add()
    add(f"- Valid candles: {len(candles)}")
    add(
        f"- Invalid candles: "
        f"{0}"
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

    add("## State Fragmentation Audit")
    add()

    total = state_audit[
        "total_observations"
    ]

    unique = state_audit[
        "unique_states"
    ]

    singleton = state_audit[
        "singleton_states"
    ]

    add(
        f"- State observations: {total}"
    )

    add(
        f"- Unique states: {unique}"
    )

    add(
        f"- Singleton states: {singleton}"
    )

    add(
        f"- Two-occurrence states: "
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
        f"- Maximum state frequency: "
        f"{state_audit['max_state_frequency']}"
    )

    add(
        f"- Mean state frequency: "
        f"{state_audit['mean_state_frequency']:.2f}"
    )

    add(
        f"- Median state frequency: "
        f"{state_audit['median_state_frequency']:.2f}"
    )

    if unique:

        add(
            f"- Singleton-state ratio: "
            f"{pct(safe_div(singleton, unique))}"
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
            f"- Signal event {event}: {count}"
        )

    add()

    add("## OOS Coverage / Abstention Audit")
    add()

    for horizon, data in sorted(
        coverage.items(),
        key=lambda x: int(x[0]),
    ):

        add(
            f"### H+{horizon}"
        )

        add(
            f"- OOS observations: "
            f"{data['oos']}"
        )

        add(
            f"- Predictions: "
            f"{data['predicted']}"
        )

        add(
            f"- Abstentions: "
            f"{data['abstained']}"
        )

        add(
            f"- Global coverage: "
            f"{pct(data['global_coverage'])}"
        )

        add(
            f"- Global abstention rate: "
            f"{pct(data['global_abstention_rate'])}"
        )

        add(
            f"- Mean window coverage: "
            f"{pct(data['mean_window_coverage'])}"
        )

        add()

    add("## Independent Event Audit")
    add()

    for event, data in event_audit.items():

        add(f"### {event}")

        add(
            f"- Total: {data['total']}"
        )

        add(
            f"- Training: {data['train']}"
        )

        add(
            f"- OOS: {data['oos']}"
        )

        if data["windows"]:

            for window, count in sorted(
                data["windows"].items()
            ):
                add(
                    f"- Window {window}: {count}"
                )

        add()

    add("## Existing v4.1.0 Result Structure")
    add()

    for window, information in window_inspection.items():

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
        "The v4.1.0 result must not be interpreted as a 0% predictive "
        "accuracy result for H+4 and H+8 because the model abstained "
        "on essentially all observations."
    )

    add()

    add(
        "The primary question is therefore not 'how do we increase "
        "accuracy?' but 'why does the current representation/model "
        "have insufficient confidence to produce predictions?'"
    )

    add()

    add(
        "Potential causes include state fragmentation, insufficient "
        "historical support, excessive ensemble disagreement, overly "
        "strict abstention behavior, or an interaction between these "
        "components."
    )

    add()

    add(
        "This diagnostic does not change any of those components."
    )

    add(
        "A subsequent research version should only change a component "
        "after this diagnostic evidence identifies the cause."
    )

    add()

    add("## Required Next Decision")
    add()

    add(
        "1. Inspect state-frequency distribution."
    )

    add(
        "2. Inspect prediction coverage."
    )

    add(
        "3. Inspect ensemble disagreement."
    )

    add(
        "4. Verify event-to-OOS matching."
    )

    add(
        "5. Determine whether the representation is too fragmented."
    )

    add(
        "6. Only then design the next representation change."
    )

    add()

    add("## Protection Result")
    add()

    add(
        "Market data unchanged: "
        + (
            "PASS"
            if protection_before == protection_after
            else "FAIL"
        )
    )

    add(
        "Production MLAI modified: NO"
    )

    add(
        "Learning memory modified: NO"
    )

    add(
        "Trading enabled: NO"
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
    print(
        "DIAGNOSTIC ONLY"
    )

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

    # --------------------------------------------------------------------------
    # PROTECTION
    # --------------------------------------------------------------------------

    protection_before = sha256_file(
        MARKET_DATA_FILE
    )

    # --------------------------------------------------------------------------
    # LOAD DATA
    # --------------------------------------------------------------------------

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

    # --------------------------------------------------------------------------
    # CHRONOLOGY
    # --------------------------------------------------------------------------

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

    # --------------------------------------------------------------------------
    # ATR
    # --------------------------------------------------------------------------

    print()
    print("=" * 88)
    print("CAUSAL FEATURE PREPARATION")
    print("=" * 88)

    atr = BASE.calculate_atr(
        candles
    )

    print(
        f"ATR observations             : "
        f"{sum(x is not None for x in atr)}"
    )

    # --------------------------------------------------------------------------
    # STRUCTURE
    # --------------------------------------------------------------------------

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
        f"Confirmed swings             : "
        f"{len(swings)}"
    )

    print(
        f"Structure states              : "
        f"{len(states)}"
    )

    print(
        f"Structural events             : "
        f"{len(events)}"
    )

    # --------------------------------------------------------------------------
    # CAUSALITY
    # --------------------------------------------------------------------------

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
                + str(reason)
            )

        raise RuntimeError(
            "Causality audit failed."
        )

    # --------------------------------------------------------------------------
    # SIGNALS
    # --------------------------------------------------------------------------

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
        f"Signal records                : "
        f"{len(signals)}"
    )

    # --------------------------------------------------------------------------
    # STATE AUDIT
    # --------------------------------------------------------------------------

    print()
    print("=" * 88)
    print("STATE FRAGMENTATION AUDIT")
    print("=" * 88)

    state_audit = audit_state_frequency(
        states
    )

    print(
        f"State observations            : "
        f"{state_audit['total_observations']}"
    )

    print(
        f"Unique states                 : "
        f"{state_audit['unique_states']}"
    )

    print(
        f"Singleton states              : "
        f"{state_audit['singleton_states']}"
    )

    print(
        f"2-occurrence states           : "
        f"{state_audit['two_occurrence_states']}"
    )

    print(
        f"3-5 occurrence states         : "
        f"{state_audit['three_to_five_states']}"
    )

    print(
        f"6-10 occurrence states        : "
        f"{state_audit['six_to_ten_states']}"
    )

    print(
        f">10 occurrence states         : "
        f"{state_audit['over_ten_states']}"
    )

    print(
        f"Maximum state frequency       : "
        f"{state_audit['max_state_frequency']}"
    )

    print(
        f"Median state frequency        : "
        f"{state_audit['median_state_frequency']:.2f}"
    )

    if state_audit[
        "unique_states"
    ]:

        print(
            "Singleton-state ratio         : "
            + pct(
                safe_div(
                    state_audit[
                        "singleton_states"
                    ],
                    state_audit[
                        "unique_states"
                    ],
                )
            )
        )

    # --------------------------------------------------------------------------
    # SIGNAL AUDIT
    # --------------------------------------------------------------------------

    print()
    print("=" * 88)
    print("SIGNAL / EVENT DISTRIBUTION")
    print("=" * 88)

    signal_audit = audit_signal_distribution(
        signals
    )

    print(
        f"Signals                       : "
        f"{signal_audit['signals']}"
    )

    for event, count in sorted(
        signal_audit["events"].items()
    ):
        print(
            f"{event:<30}: {count}"
        )

    # --------------------------------------------------------------------------
    # WALK FORWARD WINDOWS
    # --------------------------------------------------------------------------

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
        f"Windows created               : "
        f"{len(windows)}"
    )

    for w in windows:

        print(
            f"Window {w.number} | "
            f"TRAIN [{w.train_start}:{w.train_end}] | "
            f"OOS [{w.oos_start}:{w.oos_end}]"
        )

    # --------------------------------------------------------------------------
    # RUN EXISTING VALIDATION
    # --------------------------------------------------------------------------

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

    # --------------------------------------------------------------------------
    # COVERAGE
    # --------------------------------------------------------------------------

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
            f"  OOS observations            : "
            f"{data['oos']}"
        )

        print(
            f"  Predictions                 : "
            f"{data['predicted']}"
        )

        print(
            f"  Abstentions                 : "
            f"{data['abstained']}"
        )

        print(
            f"  Global coverage             : "
            f"{pct(data['global_coverage'])}"
        )

        print(
            f"  Abstention rate             : "
            f"{pct(data['global_abstention_rate'])}"
        )

    # --------------------------------------------------------------------------
    # EVENT AUDIT
    # --------------------------------------------------------------------------

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
            f"  Total                       : "
            f"{data['total']}"
        )

        print(
            f"  Training                    : "
            f"{data['train']}"
        )

        print(
            f"  OOS                         : "
            f"{data['oos']}"
        )

        for window, count in sorted(
            data["windows"].items()
        ):

            print(
                f"  Window {window:<18}: "
                f"{count}"
            )

    # --------------------------------------------------------------------------
    # RESULT STRUCTURE
    # --------------------------------------------------------------------------

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

        information = inspect_window_result(
            result
        )

# ------------------------------------------------------------------
# FIX: ensure walk-forward window identifier is hashable
# ------------------------------------------------------------------

if isinstance(number, dict):
    window_number = number.get("number")

    if window_number is None:
        window_number = number.get("window")

    if window_number is None:
        raise RuntimeError(
            "Unable to determine walk-forward window number."
        )
else:
    window_number = number

window_inspection[window_number] = information	      
        print()

        print(
            f"Window {number}"
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

    # --------------------------------------------------------------------------
    # DIAGNOSIS
    # --------------------------------------------------------------------------

    print()
    print("=" * 88)
    print("AUTOMATIC DIAGNOSIS")
    print("=" * 88)

    diagnosis = diagnose(
        state_audit=state_audit,
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

    # --------------------------------------------------------------------------
    # PROTECTION
    # --------------------------------------------------------------------------

    protection_after = sha256_file(
        MARKET_DATA_FILE
    )

    # --------------------------------------------------------------------------
    # ARTIFACT
    # --------------------------------------------------------------------------

    artifact = {
        "version": VERSION,

        "purpose": (
            "Diagnostic-only investigation "
            "of MLAI v4.1.0"
        ),

        "protection": {
            "market_data": MARKET_DATA_FILE,
            "sha256_before": protection_before,
            "sha256_after": protection_after,
            "unchanged": (
                protection_before
                == protection_after
            ),
            "production_modified": False,
            "learning_memory_modified": False,
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

        "state_audit": state_audit,

        "signal_audit": signal_audit,

        "coverage": coverage,

        "event_audit": event_audit,

        "window_inspection": window_inspection,

        "diagnosis": diagnosis,
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

    # --------------------------------------------------------------------------
    # REPORT
    # --------------------------------------------------------------------------

    report = build_report(
        protection_before=protection_before,
        protection_after=protection_after,
        candles=candles,
        chronology=chronology,
        swings=swings,
        states=states,
        events=events,
        signals=signals,
        state_audit=state_audit,
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

        f.write(report)

    # --------------------------------------------------------------------------
    # FINAL PROTECTION
    # --------------------------------------------------------------------------

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