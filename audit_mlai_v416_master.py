import ast
import inspect
import math
import os
import traceback
from collections import Counter
from datetime import datetime

TARGET = "mlai_market_structure_v416"
SOURCE = TARGET + ".py"
REPORT = "MLAI_V416_MASTER_AUDIT_REPORT.md"
RAW = "MLAI_V416_MASTER_AUDIT_RAW.txt"

out = []

def log(x=""):
    print(x)
    out.append(str(x))

def section(title):
    log("")
    log("=" * 100)
    log(title)
    log("=" * 100)

def check(name, value, detail=""):
    if value is True:
        status = "PASS"
    elif value is False:
        status = "FAIL"
    else:
        status = "INFO"
    log(f"[{status:5}] {name}")
    if detail:
        log(f"       {detail}")

section("MLAI v4.1.6 MASTER FORENSIC AUDIT")
log("Research / validation only")
log("Source file : " + os.path.abspath(SOURCE))
log("Started     : " + datetime.now().isoformat())
log("NO SOURCE FILES WILL BE MODIFIED.")

# ----------------------------------------------------------------------
# 1. FILE / AST AUDIT
# ----------------------------------------------------------------------

section("1. SOURCE / AST INTEGRITY")

if not os.path.exists(SOURCE):
    check("Source file exists", False, SOURCE)
    raise SystemExit(1)

check("Source file exists", True, SOURCE)

source_text = open(SOURCE, "r", encoding="utf-8").read()

try:
    tree = ast.parse(source_text)
    check("Python syntax", True)
except Exception as e:
    check("Python syntax", False, repr(e))
    raise SystemExit(1)

try:
    import mlai_market_structure_v416 as m
    check("Module import", True)
except Exception:
    check("Module import", False, traceback.format_exc())
    raise SystemExit(1)

# ----------------------------------------------------------------------
# 2. STATIC FUNCTION / CLASS INVENTORY
# ----------------------------------------------------------------------

section("2. IMPLEMENTATION INVENTORY")

functions = {}
classes = {}

for node in ast.walk(tree):
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        functions[node.name] = node.lineno
    elif isinstance(node, ast.ClassDef):
        classes[node.name] = node.lineno

log(f"Functions discovered : {len(functions)}")
log(f"Classes discovered   : {len(classes)}")

for name in sorted(functions):
    log(f"  FUNCTION {name:45s} line={functions[name]}")

log("")
for name in sorted(classes):
    log(f"  CLASS    {name:45s} line={classes[name]}")

required_functions = [
    "load_market_data",
    "calculate_atr",
    "build_market_states",
    "build_experience_records",
    "path_similarity",
    "path_row_similarity",
    "similarity_score",
    "retrieve_historical_experience",
]

for name in required_functions:
    check(
        f"Required function: {name}",
        hasattr(m, name),
        f"line={functions.get(name, 'NOT FOUND')}"
    )

# ----------------------------------------------------------------------
# 3. STATIC FUTURE-REFERENCE AUDIT
# ----------------------------------------------------------------------

section("3. STATIC CAUSALITY / FUTURE-REFERENCE AUDIT")

future_terms = [
    "future",
    "future_return",
    "future_close",
    "target",
    "outcome",
]

for name in [
    "build_market_states",
    "build_experience_records",
    "path_similarity",
    "path_row_similarity",
    "similarity_score",
    "retrieve_historical_experience",
]:
    if not hasattr(m, name):
        continue

    try:
        src = inspect.getsource(getattr(m, name))
    except Exception:
        continue

    hits = []
    for line_no, line in enumerate(src.splitlines(), 1):
        low = line.lower()
        if any(term in low for term in future_terms):
            hits.append((line_no, line.strip()))

    if hits:
        log(f"{name}: future-related tokens found:")
        for line_no, line in hits[:30]:
            log(f"    {line_no}: {line}")
    else:
        log(f"{name}: no obvious future-related tokens found")

# ----------------------------------------------------------------------
# 4. DATA FOUNDATION
# ----------------------------------------------------------------------

section("4. DATA FOUNDATION")

try:
    candles, invalid_count = m.load_market_data(m.MARKET_DATA_FILE)

    check(
        "Market data loaded",
        True,
        f"candles={len(candles)} invalid={invalid_count}"
    )

    timestamps = [c.timestamp for c in candles]

    chronological = all(
        timestamps[i] < timestamps[i + 1]
        for i in range(len(timestamps) - 1)
    )

    duplicates = len(timestamps) != len(set(timestamps))

    check(
        "Timestamp chronology",
        chronological,
        f"count={len(timestamps)}"
    )

    check(
        "Duplicate timestamps",
        not duplicates
    )

except Exception:
    check("Market data foundation", False, traceback.format_exc())
    raise SystemExit(1)

# ----------------------------------------------------------------------
# 5. CORE STATE BUILD
# ----------------------------------------------------------------------

section("5. CORE MARKET REPRESENTATION")

try:
    atr = m.calculate_atr(candles)

    structure_engine = m.CausalStructureEngine(candles)
    structure_states = structure_engine.build()

    market_states = m.build_market_states(
        candles,
        structure_states,
        atr,
    )

    check("ATR construction", True, f"records={len(atr)}")
    check(
        "Structure construction",
        True,
        f"records={len(structure_states)}"
    )
    check(
        "Market-state construction",
        True,
        f"records={len(market_states)}"
    )

except Exception:
    check("Core representation", False, traceback.format_exc())
    raise SystemExit(1)

# ----------------------------------------------------------------------
# 6. STATE DISTRIBUTIONS
# ----------------------------------------------------------------------

section("6. STATE DISTRIBUTIONS")

def distribution(label, values):
    counter = Counter(values)
    log(label)
    for k, v in counter.most_common():
        log(f"  {str(k):45s} {v}")

try:
    if structure_states:
        for attr in [
            "trend",
            "event",
            "acceptance",
            "retest",
        ]:
            vals = [
                getattr(x, attr, "MISSING")
                for x in structure_states
            ]
            distribution("STRUCTURE " + attr.upper(), vals)

    for attr in [
        "candle_type",
        "rejection",
        "pressure",
        "direction",
    ]:
        vals = [
            getattr(x, attr, "MISSING")
            for x in market_states
        ]
        distribution("MARKET " + attr.upper(), vals)

    for attr in [
        "sequence",
        "state",
        "regime",
    ]:
        vals = [
            getattr(x, attr, None)
            for x in market_states
        ]
        if any(v is not None for v in vals):
            distribution("MARKET " + attr.upper(), vals)

except Exception:
    log(traceback.format_exc())

# ----------------------------------------------------------------------
# 7. CAUSAL PREFIX AUDIT
# ----------------------------------------------------------------------

section("7. CAUSAL PREFIX AUDIT")

prefix_result = None

if hasattr(m, "causal_prefix_audit"):
    try:
        test_indices = [
            i for i in
            [
                100, 150, 200, 300, 400,
                500, 600, 700, 800,
                900, 1000, 1100, 1200
            ]
            if i < len(candles)
        ]

        result = m.causal_prefix_audit(
            candles,
            test_indices,
        )

        failures = result[0] if isinstance(result, tuple) else result

        prefix_result = failures

        check(
            "Causal prefix consistency",
            len(failures) == 0,
            f"failures={len(failures)}"
        )

        if failures:
            for failure in failures[:30]:
                log("  " + repr(failure))

    except Exception:
        check(
            "Causal prefix audit",
            False,
            traceback.format_exc()
        )
else:
    check(
        "Causal prefix audit function",
        False,
        "function not present"
    )

# ----------------------------------------------------------------------
# 8. SYNTHETIC TESTS
# ----------------------------------------------------------------------

section("8. SYNTHETIC / P2 TESTS")

if hasattr(m, "synthetic_tests"):
    try:
        result = m.synthetic_tests()
        log(repr(result))

        if isinstance(result, list):
            for item in result:
                log("  " + repr(item))

        check("Synthetic test execution", True)
    except Exception:
        check(
            "Synthetic tests",
            False,
            traceback.format_exc()
        )
else:
    check(
        "Synthetic tests",
        False,
        "synthetic_tests() not found"
    )

# ----------------------------------------------------------------------
# 9. EXPERIENCE RECORD AUDIT
# ----------------------------------------------------------------------

section("9. HISTORICAL EXPERIENCE RECORD AUDIT")

records = []

try:
    if hasattr(m, "build_experience_records"):
        state_index_map = {
            i: market_states[i].index
            for i in range(len(market_states))
        }

        query_index = min(904, len(candles) - 20)
        horizon = 4

        records = m.build_experience_records(
            candles,
            atr,
            market_states,
            state_index_map,
            0,
            query_index,
            horizon,
        )

        eligible = [
            r for r in records
            if r.index < query_index
            and query_index - r.index >= getattr(
                m,
                "MIN_HISTORY_GAP",
                0,
            )
            and r.index + horizon < len(candles)
        ]

        check(
            "Experience record construction",
            True,
            f"records={len(records)} eligible={len(eligible)}"
        )

        if records:
            sample = records[0]

            log("")
            log("ExperienceRecord fields:")
            for field in vars(sample):
                log(f"  {field}")

    else:
        check(
            "Experience record construction",
            False,
            "function missing"
        )

except Exception:
    check(
        "Experience record construction",
        False,
        traceback.format_exc()
    )

# ----------------------------------------------------------------------
# 10. SIMILARITY FORENSIC
# ----------------------------------------------------------------------

section("10. HISTORICAL SIMILARITY FORENSIC")

similarity_rows = []

try:
    query_index = min(904, len(market_states) - 20)
    horizon = 4
    query = market_states[query_index]

    if not records:
        state_index_map = {
            i: market_states[i].index
            for i in range(len(market_states))
        }

        records = m.build_experience_records(
            candles,
            atr,
            market_states,
            state_index_map,
            0,
            query_index,
            horizon,
        )

    eligible = [
        r for r in records
        if r.index < query_index
        and query_index - r.index >= getattr(
            m,
            "MIN_HISTORY_GAP",
            0,
        )
        and r.index + horizon < len(candles)
    ]

    def future_return(index):
        if index + horizon >= len(candles):
            return None

        entry = candles[index].close
        future = candles[index + horizon].close

        if abs(entry) < 1e-12:
            return None

        return (future - entry) / entry

    query_future = future_return(query_index)

    for record in eligible:
        try:
            similarity = m.path_similarity(
                query,
                record,
            )
        except Exception:
            continue

        fr = future_return(record.index)

        if fr is not None:
            similarity_rows.append(
                (
                    float(similarity),
                    float(fr),
                    record.index,
                )
            )

    similarity_rows.sort(
        key=lambda x: x[0],
        reverse=True,
    )

    check(
        "Similarity calculation",
        len(similarity_rows) > 0,
        f"usable_pairs={len(similarity_rows)}"
    )

    if similarity_rows:
        log("")
        log("Top 20 similarity matches:")
        for s, fr, idx in similarity_rows[:20]:
            log(
                f"  index={idx:4d} "
                f"similarity={s:.6f} "
                f"future_return={fr:+.8f}"
            )

        values = [x[0] for x in similarity_rows]
        futures = [x[1] for x in similarity_rows]

        mean_s = sum(values) / len(values)
        mean_f = sum(futures) / len(futures)

        cov = sum(
            (a - mean_s) * (b - mean_f)
            for a, b in zip(values, futures)
        )

        var_s = sum(
            (a - mean_s) ** 2
            for a in values
        )

        var_f = sum(
            (b - mean_f) ** 2
            for b in futures
        )

        corr = (
            cov / math.sqrt(var_s * var_f)
            if var_s > 0 and var_f > 0
            else 0.0
        )

        log("")
        log(f"Query future return : {query_future}")
        log(f"Path/future corr.   : {corr:.6f}")
        log(f"Maximum similarity  : {max(values):.6f}")
        log(f"Mean similarity     : {mean_s:.6f}")

        for threshold in [
            0.50,
            0.60,
            0.65,
            0.70,
            0.75,
            0.80,
            0.90,
        ]:
            selected = [
                x for x in similarity_rows
                if x[0] >= threshold
            ]

            if selected:
                positive = sum(
                    1 for x in selected
                    if x[1] > 0
                )

                agreement = (
                    positive / len(selected)
                )

                mean_future = (
                    sum(x[1] for x in selected)
                    / len(selected)
                )

                log(
                    f"Similarity >= {threshold:.2f}: "
                    f"count={len(selected):4d} "
                    f"positive={agreement:.4f} "
                    f"mean_future={mean_future:+.8f}"
                )
            else:
                log(
                    f"Similarity >= {threshold:.2f}: EMPTY"
                )

except Exception:
    check(
        "Similarity forensic",
        False,
        traceback.format_exc()
    )

# ----------------------------------------------------------------------
# 11. SIMILARITY FUNCTION SOURCE
# ----------------------------------------------------------------------

section("11. SIMILARITY ARCHITECTURE")

for name in [
    "path_similarity",
    "path_row_similarity",
    "similarity_score",
    "retrieve_historical_experience",
]:
    if hasattr(m, name):
        try:
            src = inspect.getsource(getattr(m, name))
            log("")
            log(f"--- {name} ---")
            log(src)
        except Exception as e:
            log(f"{name}: unable to inspect: {e}")

# ----------------------------------------------------------------------
# 12. GOAL COMPONENT PRESENCE AUDIT
# ----------------------------------------------------------------------

section("12. MLAI GOAL COMPONENT AUDIT")

goal_components = {
    "raw_market_data": [
        "load_market_data",
    ],
    "causal_data_handling": [
        "CausalStructureEngine",
        "causal_prefix_audit",
    ],
    "candle_anatomy": [
        "CandleAnatomy",
        "build_candle_anatomy",
    ],
    "market_structure": [
        "CausalStructureEngine",
    ],
    "sequence_understanding": [
        "build_sequence_states",
    ],
    "volatility_momentum": [
        "calculate_atr",
    ],
    "context_regime": [
        "regime",
        "build_market_states",
    ],
    "historical_outcomes": [
        "build_experience_records",
    ],
    "historical_experience_memory": [
        "ExperienceRecord",
        "build_experience_records",
    ],
    "non_exact_similarity": [
        "path_similarity",
        "similarity_score",
    ],
    "probability_estimation": [
        "retrieve_historical_experience",
    ],
    "probability_calibration": [
        "calibration",
        "brier",
        "logloss",
    ],
    "scenario_reasoning": [
        "scenario",
    ],
    "confirmation_conditions": [
        "confirmation",
        "confirm",
    ],
    "invalidation_conditions": [
        "invalidation",
        "invalidate",
    ],
    "human_language_explanation": [
        "explanation",
        "narrative",
        "language",
    ],
    "multi_timeframe": [
        "timeframe",
        "multi_timeframe",
    ],
    "continuous_learning": [
        "learning",
        "update_memory",
        "learn",
    ],
    "live_pipeline": [
        "live",
        "stream",
        "websocket",
    ],
}

source_lower = source_text.lower()

for component, tokens in goal_components.items():
    hits = [
        token for token in tokens
        if token.lower() in source_lower
    ]

    if hits:
        log(
            f"[PRESENT] {component}: "
            + ", ".join(hits)
        )
    else:
        log(
            f"[ABSENT ] {component}"
        )

# ----------------------------------------------------------------------
# 13. RISK FLAGS
# ----------------------------------------------------------------------

section("13. AUTOMATIC RISK FLAGS")

risk_flags = []

def risk(condition, message):
    if condition:
        risk_flags.append(message)
        log("[RISK] " + message)

risk(
    len(similarity_rows) > 0
    and max(x[0] for x in similarity_rows) < 0.80,
    "Historical similarity does not currently produce very-high similarity matches."
)

if similarity_rows:
    values = [x[0] for x in similarity_rows]
    futures = [x[1] for x in similarity_rows]

    mean_s = sum(values) / len(values)
    mean_f = sum(futures) / len(futures)

    cov = sum(
        (a - mean_s) * (b - mean_f)
        for a, b in zip(values, futures)
    )

    var_s = sum(
        (a - mean_s) ** 2
        for a in values
    )

    var_f = sum(
        (b - mean_f) ** 2
        for b in futures
    )

    corr = (
        cov / math.sqrt(var_s * var_f)
        if var_s > 0 and var_f > 0
        else 0.0
    )

    risk(
        abs(corr) < 0.15,
        f"Path/future correlation is weak: {corr:.6f}"
    )

risk(
    prefix_result is not None
    and len(prefix_result) > 0,
    f"Causal-prefix mismatches detected: {len(prefix_result or [])}"
)

risk(
    "scenario" not in source_lower,
    "Scenario reasoning infrastructure is not clearly implemented."
)

risk(
    "invalidation" not in source_lower,
    "Invalidation-condition infrastructure is not clearly implemented."
)

risk(
    "confirmation" not in source_lower,
    "Confirmation-condition infrastructure is not clearly implemented."
)

risk(
    "timeframe" not in source_lower,
    "Multi-timeframe infrastructure is not clearly implemented."
)

risk(
    "calibration" not in source_lower,
    "Probability calibration infrastructure is not clearly implemented."
)

# ----------------------------------------------------------------------
# 14. FINAL AUTOMATIC ASSESSMENT
# ----------------------------------------------------------------------

section("14. MASTER AUDIT CONCLUSION")

log("This is a forensic assessment, not a trading recommendation.")
log("")

if not risk_flags:
    verdict = "GREEN — NO MAJOR AUTOMATIC RISK FLAG"
elif any(
    "Causal-prefix" in x
    for x in risk_flags
):
    verdict = "BLOCKED — CAUSALITY ISSUE MUST BE FIXED FIRST"
elif any(
    "similarity" in x.lower()
    or "correlation" in x.lower()
    for x in risk_flags
):
    verdict = "FIX REQUIRED — HISTORICAL EXPERIENCE REPRESENTATION/RETRIEVAL IS THE NEXT PRIORITY"
else:
    verdict = "RESEARCH INCOMPLETE — CORE FOUNDATION EXISTS BUT HIGH-LEVEL INTELLIGENCE IS STILL MISSING"

log("MASTER VERDICT:")
log(verdict)

log("")
log("Recommended order:")
log("1. Protect and freeze the verified causal foundation.")
log("2. Fix/validate the candle synthetic-test issue if confirmed.")
log("3. Audit and redesign historical experience representation.")
log("4. Validate similarity without future leakage.")
log("5. Build calibrated probability estimation.")
log("6. Add scenario / confirmation / invalidation reasoning.")
log("7. Add human-language market explanation.")
log("8. Add multi-timeframe reasoning.")
log("9. Test unseen-chart generalization.")
log("10. Only then consider controlled learning/live infrastructure.")

section("15. AUDIT COMPLETE")

log("No source files were modified.")
log("No market data was modified.")
log("No learning memory was modified.")
log("Trading remains disabled.")

# ----------------------------------------------------------------------
# SAVE REPORT
# ----------------------------------------------------------------------

with open(RAW, "w", encoding="utf-8") as f:
    f.write("\n".join(out))

with open(REPORT, "w", encoding="utf-8") as f:
    f.write("# MLAI v4.1.6 Master Forensic Audit\n\n")
    f.write("Generated: " + datetime.now().isoformat() + "\n\n")
    f.write("```text\n")
    f.write("\n".join(out))
    f.write("\n```\n")

print("")
print("=" * 100)
print("REPORT SAVED")
print("=" * 100)
print(REPORT)
print(RAW)

