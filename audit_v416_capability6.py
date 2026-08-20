import ast
import hashlib
import math
import pickle
from pathlib import Path
from statistics import mean

SOURCE = Path("mlai_market_structure_v416.py")
ARTIFACT = Path("MLAI_V416_ROBUST_HISTORICAL_EXPERIENCE_RETRIEVAL.bin")
REPORT = Path("MLAI_V416_CAPABILITY6_INCREMENTAL_VALUE_AUDIT.md")

HORIZONS = (4, 8, 16)


# ================================================================
# BASIC HELPERS
# ================================================================

def sha256_file(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def is_num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(float(x))


def fmt(x):
    if x is None:
        return "N/A"
    if isinstance(x, float):
        return f"{x:.8f}"
    return str(x)


def pct(x):
    return "N/A" if x is None else f"{100.0 * x:.4f}%"


def avg(values):
    values = [float(x) for x in values if is_num(x)]
    return mean(values) if values else None


def get(d, *keys):
    cur = d
    for key in keys:
        if not isinstance(cur, dict) or key not in cur:
            return None
        cur = cur[key]
    return cur


# ================================================================
# LOAD
# ================================================================

print("=" * 100)
print("MLAI v4.1.6 — CAPABILITY 6 INCREMENTAL PREDICTIVE VALUE AUDIT")
print("=" * 100)

if not SOURCE.exists():
    raise SystemExit(f"Missing source: {SOURCE}")

if not ARTIFACT.exists():
    raise SystemExit(f"Missing artifact: {ARTIFACT}")

source_hash_before = sha256_file(SOURCE)

source_text = SOURCE.read_text(encoding="utf-8", errors="replace")

try:
    tree = ast.parse(source_text)
    print("\nSOURCE AST PARSE: PASS")
except Exception as e:
    raise SystemExit(f"Source AST parse failed: {e}")

with ARTIFACT.open("rb") as f:
    artifact = pickle.load(f)

if not isinstance(artifact, dict):
    raise SystemExit("Artifact is not a dictionary.")

print("Artifact load: PASS")
print(f"Artifact type: {type(artifact).__name__}")
print(f"Source SHA256: {source_hash_before}")


# ================================================================
# SOURCE-LEVEL INVESTIGATION
# ================================================================

print("\n" + "=" * 100)
print("1. SOURCE IMPLEMENTATION INVESTIGATION")
print("=" * 100)

source_lines = source_text.splitlines()

patterns = [
    "incremental_value",
    "retrieval_brier_lift",
    "predictive_brier_lift",
    "incremental_brier_lift",
    "incremental_log_loss_lift",
    "incremental_accuracy_delta",
    "baseline_brier",
    "retrieval_brier",
    "predictive_brier",
    "baseline_log_loss",
    "retrieval_log_loss",
    "predictive_log_loss",
    "baseline_accuracy",
    "retrieval_accuracy",
    "predictive_accuracy",
]

source_hits = {}

for pattern in patterns:
    hits = []
    for i, line in enumerate(source_lines, 1):
        if pattern.lower() in line.lower():
            hits.append(i)
    source_hits[pattern] = hits

for pattern, hits in source_hits.items():
    print(f"{pattern:35s}: {len(hits)} hit(s)")
    if hits:
        print("   lines:", ", ".join(map(str, hits[:20])))

# Locate functions containing incremental-value logic.
functions = []

for node in ast.walk(tree):
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        start = node.lineno
        end = getattr(node, "end_lineno", start)
        body = "\n".join(source_lines[start - 1:end]).lower()

        if any(
            p.lower() in body
            for p in [
                "incremental_value",
                "incremental_brier_lift",
                "incremental_log_loss_lift",
                "predictive_brier_lift",
                "retrieval_brier_lift",
            ]
        ):
            functions.append((node.name, start, end))

print("\nFunctions containing incremental-value logic:")

if functions:
    for name, start, end in functions:
        print(f"  {name} [{start}:{end}]")
else:
    print("  NONE FOUND")


# ================================================================
# ARTIFACT STRUCTURE
# ================================================================

print("\n" + "=" * 100)
print("2. ARTIFACT STRUCTURE")
print("=" * 100)

walk_forward = artifact.get("walk_forward", [])

print(f"Walk-forward windows: {len(walk_forward)}")

aggregate = artifact.get("aggregate", {})

for h in HORIZONS:
    block = aggregate.get(str(h), aggregate.get(h, {}))
    print(f"\nH+{h} aggregate:")
    if isinstance(block, dict):
        for key in [
            "mean_retrieval_accuracy",
            "mean_baseline_accuracy",
            "mean_predictive_accuracy",
            "mean_brier_lift",
            "mean_retrieval_brier",
            "mean_baseline_brier",
            "mean_predictive_brier",
            "mean_predictive_brier_lift",
            "mean_predictive_log_loss_lift",
        ]:
            if key in block:
                print(f"  {key}: {fmt(block[key])}")


# ================================================================
# COLLECT WINDOW-LEVEL METRICS
# ================================================================

print("\n" + "=" * 100)
print("3. WINDOW-LEVEL INCREMENTAL VALUE")
print("=" * 100)

window_rows = []

for wi, window in enumerate(walk_forward, 1):
    horizons = window.get("horizons", {})

    for h in HORIZONS:
        block = horizons.get(str(h), horizons.get(h))

        if not isinstance(block, dict):
            continue

        row = {
            "window": wi,
            "horizon": h,
            "retrieval_accuracy": block.get("retrieval_accuracy"),
            "baseline_accuracy": block.get("baseline_accuracy"),
            "predictive_accuracy": block.get("predictive_accuracy"),
            "retrieval_brier": block.get("retrieval_brier"),
            "baseline_brier": block.get("baseline_brier"),
            "predictive_brier": block.get("predictive_brier"),
            "retrieval_brier_lift": block.get("brier_lift"),
            "predictive_brier_lift": block.get("predictive_brier_lift"),
            "predictive_log_loss_lift": block.get("predictive_log_loss_lift"),
        }

        window_rows.append(row)

        print(
            f"W{wi} H+{h}: "
            f"retrieval_acc={fmt(row['retrieval_accuracy'])} | "
            f"baseline_acc={fmt(row['baseline_accuracy'])} | "
            f"predictive_acc={fmt(row['predictive_accuracy'])} | "
            f"retrieval_brier={fmt(row['retrieval_brier'])} | "
            f"baseline_brier={fmt(row['baseline_brier'])} | "
            f"predictive_brier={fmt(row['predictive_brier'])} | "
            f"brier_lift={fmt(row['retrieval_brier_lift'])}"
        )


# ================================================================
# RECOMPUTE METRICS DIRECTLY FROM EVALUATIONS
# ================================================================

print("\n" + "=" * 100)
print("4. DIRECT RECOMPUTATION FROM OOS EVALUATIONS")
print("=" * 100)

direct = {}

for h in HORIZONS:
    rows = []

    for wi, window in enumerate(walk_forward, 1):
        horizons = window.get("horizons", {})
        block = horizons.get(str(h), horizons.get(h))

        if not isinstance(block, dict):
            continue

        evaluations = block.get("evaluations", [])

        for ei, evaluation in enumerate(evaluations):
            if not isinstance(evaluation, dict):
                continue

            retrieval_eval = evaluation.get("retrieval_evaluation", {})
            baseline_eval = evaluation.get("baseline_evaluation", {})
            predictive_eval = evaluation.get("predictive_evaluation", {})

            row = {
                "window": wi,
                "evaluation": ei,
                "retrieval_correct": retrieval_eval.get("correct"),
                "baseline_correct": baseline_eval.get("correct"),
                "predictive_correct": predictive_eval.get("correct"),
                "retrieval_brier": retrieval_eval.get("brier"),
                "baseline_brier": baseline_eval.get("brier"),
                "predictive_brier": predictive_eval.get("brier"),
                "retrieval_log_loss": retrieval_eval.get("log_loss"),
                "baseline_log_loss": baseline_eval.get("log_loss"),
                "predictive_log_loss": predictive_eval.get("log_loss"),
            }

            rows.append(row)

    direct[h] = rows

    retrieval_brier = [
        r["retrieval_brier"]
        for r in rows
        if is_num(r["retrieval_brier"])
    ]

    baseline_brier = [
        r["baseline_brier"]
        for r in rows
        if is_num(r["baseline_brier"])
    ]

    predictive_brier = [
        r["predictive_brier"]
        for r in rows
        if is_num(r["predictive_brier"])
    ]

    retrieval_ll = [
        r["retrieval_log_loss"]
        for r in rows
        if is_num(r["retrieval_log_loss"])
    ]

    baseline_ll = [
        r["baseline_log_loss"]
        for r in rows
        if is_num(r["baseline_log_loss"])
    ]

    predictive_ll = [
        r["predictive_log_loss"]
        for r in rows
        if is_num(r["predictive_log_loss"])
    ]

    retrieval_acc = [
        float(r["retrieval_correct"])
        for r in rows
        if isinstance(r["retrieval_correct"], bool)
    ]

    baseline_acc = [
        float(r["baseline_correct"])
        for r in rows
        if isinstance(r["baseline_correct"], bool)
    ]

    predictive_acc = [
        float(r["predictive_correct"])
        for r in rows
        if isinstance(r["predictive_correct"], bool)
    ]

    rb = avg(retrieval_brier)
    bb = avg(baseline_brier)
    pb = avg(predictive_brier)

    rl = avg(retrieval_ll)
    bl = avg(baseline_ll)
    pl = avg(predictive_ll)

    ra = avg(retrieval_acc)
    ba = avg(baseline_acc)
    pa = avg(predictive_acc)

    print(f"\nH+{h}")
    print(f"  OOS evaluations: {len(rows)}")
    print(f"  Retrieval accuracy : {fmt(ra)}")
    print(f"  Baseline accuracy  : {fmt(ba)}")
    print(f"  Predictive accuracy: {fmt(pa)}")
    print(f"  Retrieval Brier    : {fmt(rb)}")
    print(f"  Baseline Brier     : {fmt(bb)}")
    print(f"  Predictive Brier   : {fmt(pb)}")
    print(f"  Retrieval LogLoss  : {fmt(rl)}")
    print(f"  Baseline LogLoss   : {fmt(bl)}")
    print(f"  Predictive LogLoss : {fmt(pl)}")

    if rb is not None and bb is not None:
        print(f"  Direct Retrieval-vs-Baseline Brier lift : {fmt(bb - rb)}")

    if pb is not None and bb is not None:
        print(f"  Direct Predictive-vs-Baseline Brier lift: {fmt(bb - pb)}")

    if pl is not None and bl is not None:
        print(f"  Direct Predictive-vs-Baseline LogLoss lift: {fmt(bl - pl)}")

    if pa is not None and ba is not None:
        print(f"  Direct Predictive-vs-Baseline Accuracy delta: {fmt(pa - ba)}")


# ================================================================
# FORMULA CONSISTENCY CHECK
# ================================================================

print("\n" + "=" * 100)
print("5. FORMULA CONSISTENCY CHECK")
print("=" * 100)

formula_results = []

for row in window_rows:
    h = row["horizon"]

    expected_retrieval_brier_lift = None
    if is_num(row["baseline_brier"]) and is_num(row["retrieval_brier"]):
        expected_retrieval_brier_lift = (
            float(row["baseline_brier"]) - float(row["retrieval_brier"])
        )

    reported = row["retrieval_brier_lift"]

    if expected_retrieval_brier_lift is None or not is_num(reported):
        status = "UNTESTABLE"
        diff = None
    else:
        diff = abs(expected_retrieval_brier_lift - float(reported))
        status = "PASS" if diff <= 1e-9 else "FAIL"

    formula_results.append(
        {
            "window": row["window"],
            "horizon": h,
            "expected": expected_retrieval_brier_lift,
            "reported": reported,
            "difference": diff,
            "status": status,
        }
    )

    print(
        f"W{row['window']} H+{h}: "
        f"expected={fmt(expected_retrieval_brier_lift)} | "
        f"reported={fmt(reported)} | "
        f"diff={fmt(diff)} | {status}"
    )


# ================================================================
# PREDICTIVE INCREMENTAL FORMULA CHECK
# ================================================================

print("\n" + "=" * 100)
print("6. PREDICTIVE-VS-BASELINE FORMULA CHECK")
print("=" * 100)

predictive_formula = []

for row in window_rows:
    expected = None

    if is_num(row["baseline_brier"]) and is_num(row["predictive_brier"]):
        expected = float(row["baseline_brier"]) - float(row["predictive_brier"])

    reported = row["predictive_brier_lift"]

    if expected is None or not is_num(reported):
        status = "UNTESTABLE"
        diff = None
    else:
        diff = abs(expected - float(reported))
        status = "PASS" if diff <= 1e-9 else "FAIL"

    predictive_formula.append(
        {
            "window": row["window"],
            "horizon": row["horizon"],
            "expected": expected,
            "reported": reported,
            "difference": diff,
            "status": status,
        }
    )

    print(
        f"W{row['window']} H+{row['horizon']}: "
        f"expected={fmt(expected)} | "
        f"reported={fmt(reported)} | "
        f"diff={fmt(diff)} | {status}"
    )


# ================================================================
# SIGN / INTERPRETATION AUDIT
# ================================================================

print("\n" + "=" * 100)
print("7. INCREMENTAL VALUE INTERPRETATION")
print("=" * 100)

interpretation = {}

for h in HORIZONS:
    rows = [r for r in window_rows if r["horizon"] == h]

    brier_lifts = [
        r["predictive_brier_lift"]
        for r in rows
        if is_num(r["predictive_brier_lift"])
    ]

    log_lifts = [
        r["predictive_log_loss_lift"]
        for r in rows
        if is_num(r["predictive_log_loss_lift"])
    ]

    accuracy_deltas = []

    for r in rows:
        if is_num(r["predictive_accuracy"]) and is_num(r["baseline_accuracy"]):
            accuracy_deltas.append(
                float(r["predictive_accuracy"])
                - float(r["baseline_accuracy"])
            )

    positive_brier = sum(x > 0 for x in brier_lifts)
    positive_log = sum(x > 0 for x in log_lifts)
    positive_acc = sum(x > 0 for x in accuracy_deltas)

    interpretation[h] = {
        "brier": brier_lifts,
        "log": log_lifts,
        "accuracy": accuracy_deltas,
        "positive_brier": positive_brier,
        "positive_log": positive_log,
        "positive_accuracy": positive_acc,
    }

    print(f"\nH+{h}")
    print(
        f"  Positive Brier lifts: "
        f"{positive_brier}/{len(brier_lifts)}"
    )
    print(
        f"  Positive LogLoss lifts: "
        f"{positive_log}/{len(log_lifts)}"
    )
    print(
        f"  Positive Accuracy deltas: "
        f"{positive_acc}/{len(accuracy_deltas)}"
    )


# ================================================================
# CHECK NULL / PERMUTATION ARTIFACT
# ================================================================

print("\n" + "=" * 100)
print("8. NULL / PERMUTATION CONTROL CHECK")
print("=" * 100)

null_test = artifact.get("null_test")

if isinstance(null_test, dict):
    print("Null-test artifact: FOUND")

    for key, value in null_test.items():
        if isinstance(value, (str, int, float, bool)):
            print(f"  {key}: {value}")
else:
    print("Null-test artifact: NOT FOUND")


# ================================================================
# CHECK RETRIEVAL -> PREDICTIVE CONNECTION
# ================================================================

print("\n" + "=" * 100)
print("9. RETRIEVAL → PREDICTIVE INTEGRATION CHECK")
print("=" * 100)

integration_counts = {}

for h in HORIZONS:
    rows = direct[h]

    total = len(rows)
    both = 0
    retrieval_missing = 0
    predictive_missing = 0

    for r in rows:
        retrieval_ok = (
            is_num(r["retrieval_brier"])
            or isinstance(r["retrieval_correct"], bool)
        )

        predictive_ok = (
            is_num(r["predictive_brier"])
            or isinstance(r["predictive_correct"], bool)
        )

        if retrieval_ok and predictive_ok:
            both += 1
        elif not retrieval_ok:
            retrieval_missing += 1
        elif not predictive_ok:
            predictive_missing += 1

    integration_counts[h] = {
        "total": total,
        "both": both,
        "retrieval_missing": retrieval_missing,
        "predictive_missing": predictive_missing,
    }

    print(
        f"H+{h}: total={total}, "
        f"retrieval+predictive={both}, "
        f"retrieval_missing={retrieval_missing}, "
        f"predictive_missing={predictive_missing}"
    )


# ================================================================
# FINAL CLASSIFICATION
# ================================================================

formula_failures = [
    x for x in formula_results if x["status"] == "FAIL"
]

predictive_formula_failures = [
    x for x in predictive_formula if x["status"] == "FAIL"
]

print("\n" + "=" * 100)
print("10. FINAL CAPABILITY 6 AUDIT")
print("=" * 100)

if formula_failures:
    final_status = "FAIL — RETRIEVAL BRIER-LIFT FORMULA INCONSISTENCY"
elif predictive_formula_failures:
    final_status = "FAIL — PREDICTIVE BRIER-LIFT FORMULA INCONSISTENCY"
elif not any(integration_counts[h]["both"] > 0 for h in HORIZONS):
    final_status = "FAIL — RETRIEVAL/PREDICTIVE INTEGRATION NOT OBSERVED"
else:
    final_status = "EMPIRICALLY MIXED — METRIC CALCULATION CONSISTENT"

print("FINAL STATUS:", final_status)


# ================================================================
# REPORT
# ================================================================

report = []

report.append("# MLAI v4.1.6 — Capability 6 Incremental Predictive Value Audit")
report.append("")
report.append("## Purpose")
report.append("")
report.append(
    "This is an independent read-only audit of Capability 6: "
    "incremental predictive value. It distinguishes implementation, "
    "metric correctness, retrieval/predictive integration, and actual "
    "out-of-sample predictive improvement."
)
report.append("")

report.append("## Source Integrity")
report.append("")
report.append(f"- Source: `{SOURCE.name}`")
report.append(f"- Source SHA256 before audit: `{source_hash_before}`")
report.append("- Source modified by this audit: NO")
report.append("")

report.append("## Source Evidence")
report.append("")

for pattern, hits in source_hits.items():
    report.append(f"- `{pattern}`: {len(hits)} source occurrence(s)")

report.append("")
report.append("Functions containing incremental-value logic:")

for name, start, end in functions:
    report.append(f"- `{name}` — lines {start}-{end}")

if not functions:
    report.append("- NONE FOUND")

report.append("")

report.append("## Direct Out-of-Sample Recalculation")
report.append("")

for h in HORIZONS:
    rows = direct[h]

    retrieval_brier = avg([
        r["retrieval_brier"] for r in rows
    ])

    baseline_brier = avg([
        r["baseline_brier"] for r in rows
    ])

    predictive_brier = avg([
        r["predictive_brier"] for r in rows
    ])

    retrieval_ll = avg([
        r["retrieval_log_loss"] for r in rows
    ])

    baseline_ll = avg([
        r["baseline_log_loss"] for r in rows
    ])

    predictive_ll = avg([
        r["predictive_log_loss"] for r in rows
    ])

    retrieval_acc = avg([
        float(r["retrieval_correct"])
        for r in rows
        if isinstance(r["retrieval_correct"], bool)
    ])

    baseline_acc = avg([
        float(r["baseline_correct"])
        for r in rows
        if isinstance(r["baseline_correct"], bool)
    ])

    predictive_acc = avg([
        float(r["predictive_correct"])
        for r in rows
        if isinstance(r["predictive_correct"], bool)
    ])

    report.append(f"### H+{h}")
    report.append("")
    report.append(f"- OOS evaluations: {len(rows)}")
    report.append(f"- Retrieval accuracy: {fmt(retrieval_acc)}")
    report.append(f"- Baseline accuracy: {fmt(baseline_acc)}")
    report.append(f"- Predictive accuracy: {fmt(predictive_acc)}")
    report.append(f"- Retrieval Brier: {fmt(retrieval_brier)}")
    report.append(f"- Baseline Brier: {fmt(baseline_brier)}")
    report.append(f"- Predictive Brier: {fmt(predictive_brier)}")
    report.append(f"- Retrieval LogLoss: {fmt(retrieval_ll)}")
    report.append(f"- Baseline LogLoss: {fmt(baseline_ll)}")
    report.append(f"- Predictive LogLoss: {fmt(predictive_ll)}")

    if retrieval_brier is not None and baseline_brier is not None:
        report.append(
            f"- Direct retrieval-vs-baseline Brier lift: "
            f"{fmt(baseline_brier - retrieval_brier)}"
        )

    if predictive_brier is not None and baseline_brier is not None:
        report.append(
            f"- Direct predictive-vs-baseline Brier lift: "
            f"{fmt(baseline_brier - predictive_brier)}"
        )

    if predictive_ll is not None and baseline_ll is not None:
        report.append(
            f"- Direct predictive-vs-baseline LogLoss lift: "
            f"{fmt(baseline_ll - predictive_ll)}"
        )

    if predictive_acc is not None and baseline_acc is not None:
        report.append(
            f"- Direct predictive-vs-baseline accuracy delta: "
            f"{fmt(predictive_acc - baseline_acc)}"
        )

    report.append("")

report.append("## Formula Consistency")
report.append("")
report.append(
    "Expected Brier lift is independently recomputed as "
    "`baseline Brier - model Brier`."
)
report.append("")

for x in formula_results:
    report.append(
        f"- W{x['window']} H+{x['horizon']}: "
        f"expected={fmt(x['expected'])}, "
        f"reported={fmt(x['reported'])}, "
        f"difference={fmt(x['difference'])}, "
        f"**{x['status']}**"
    )

report.append("")
report.append("Predictive Brier-lift formula:")
report.append("")

for x in predictive_formula:
    report.append(
        f"- W{x['window']} H+{x['horizon']}: "
        f"expected={fmt(x['expected'])}, "
        f"reported={fmt(x['reported'])}, "
        f"difference={fmt(x['difference'])}, "
        f"**{x['status']}**"
    )

report.append("")
report.append("## Window-Level Predictive Evidence")
report.append("")

for h in HORIZONS:
    data = interpretation[h]

    report.append(f"### H+{h}")
    report.append("")
    report.append(
        f"- Positive Brier lifts: "
        f"{data['positive_brier']}/{len(data['brier'])}"
    )
    report.append(
        f"- Positive LogLoss lifts: "
        f"{data['positive_log']}/{len(data['log'])}"
    )
    report.append(
        f"- Positive accuracy deltas: "
        f"{data['positive_accuracy']}/{len(data['accuracy'])}"
    )
    report.append("")

report.append("## Null / Permutation Control")
report.append("")

if isinstance(null_test, dict):
    report.append("Null-test artifact: FOUND")
    for key, value in null_test.items():
        if isinstance(value, (str, int, float, bool)):
            report.append(f"- `{key}`: {value}")
else:
    report.append(
        "No structured null/permutation control was found in the validation artifact."
    )

report.append("")

report.append("## Retrieval → Predictive Integration")
report.append("")

for h in HORIZONS:
    x = integration_counts[h]
    report.append(
        f"- H+{h}: {x['both']}/{x['total']} evaluations contain "
        "both retrieval and predictive evidence."
    )

report.append("")
report.append("## Final Assessment")
report.append("")
report.append(f"**{final_status}**")
report.append("")

if formula_failures:
    report.append(
        "The reported incremental metric is internally inconsistent with "
        "the underlying Brier scores. Capability 6 cannot be accepted "
        "until the calculation is corrected."
    )
elif predictive_formula_failures:
    report.append(
        "The predictive Brier-lift calculation is internally inconsistent "
        "with the underlying predictive and baseline Brier scores."
    )
else:
    report.append(
        "The available Brier-lift calculations are internally consistent. "
        "This does not establish positive predictive value; it establishes "
        "that the metric calculation agrees with its stated formula."
    )

report.append("")
report.append(
    "Negative out-of-sample predictive results are retained as research "
    "findings and are not converted into PASS merely because the capability "
    "is implemented."
)

REPORT.write_text("\n".join(report), encoding="utf-8")

source_hash_after = sha256_file(SOURCE)

print("\n" + "=" * 100)
print("11. READ-ONLY INTEGRITY")
print("=" * 100)

print("Source SHA256 before:", source_hash_before)
print("Source SHA256 after :", source_hash_after)
print(
    "Source modification:",
    "NONE" if source_hash_before == source_hash_after else "DETECTED"
)

print("\n" + "=" * 100)
print("AUDIT COMPLETE")
print("=" * 100)
print(f"Report saved: {REPORT}")
print(f"Final status: {final_status}")
