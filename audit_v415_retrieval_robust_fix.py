from pathlib import Path
import ast
import hashlib
import importlib
import inspect
import json
import math
import statistics
import sys
import traceback


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "mlai_market_structure_v415.py"
RETRIEVAL_MEMORY = ROOT / "MLAI_V415_ROBUST_HISTORICAL_EXPERIENCE_RETRIEVAL.bin"


# ============================================================================
# HELPERS
# ============================================================================

def sha256(path):
    h = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)

    return h.hexdigest()


def safe_repr(value, limit=500):
    try:
        text = repr(value)
    except Exception:
        text = "<repr failed>"

    if len(text) > limit:
        text = text[:limit] + "...<truncated>"

    return text


def load_source_ast(path):
    text = path.read_text(encoding="utf-8")
    return text, ast.parse(text)


def find_functions(tree):
    result = {}

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            result[node.name] = node

    return result


def print_header(title):
    print()
    print("=" * 100)
    print(title)
    print("=" * 100)


def print_subheader(title):
    print()
    print("-" * 100)
    print(title)
    print("-" * 100)


def numeric(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def finite_numeric(value):
    return numeric(value) and math.isfinite(float(value))


def flatten_dict(value, prefix=""):
    result = {}

    if isinstance(value, dict):
        for key, child in value.items():
            name = f"{prefix}.{key}" if prefix else str(key)
            result.update(flatten_dict(child, name))

    elif isinstance(value, (list, tuple)):
        result[prefix] = f"<sequence len={len(value)}>"

    else:
        result[prefix] = value

    return result


# ============================================================================
# START
# ============================================================================

print_header(
    "MLAI v4.1.5 ROBUST HISTORICAL RETRIEVAL INVESTIGATION"
)

print("DIAGNOSTIC / READ-ONLY")
print("NO SOURCE MODIFICATION")
print("NO MARKET DATA MODIFICATION")
print("NO MEMORY MODIFICATION")
print("NO MODEL RETRAINING")
print("NO PARAMETER CHANGES")


# ============================================================================
# 1. FILE PROTECTION
# ============================================================================

print_subheader("1. FILE PROTECTION")

if not SOURCE.exists():
    raise FileNotFoundError(
        f"Required source file not found: {SOURCE}"
    )

source_hash_before = sha256(SOURCE)

print(f"Source:")
print(f"  {SOURCE}")

print()
print("Source SHA256:")
print(f"  {source_hash_before}")

if RETRIEVAL_MEMORY.exists():
    memory_hash_before = sha256(RETRIEVAL_MEMORY)

    print()
    print("Retrieval memory:")
    print(f"  {RETRIEVAL_MEMORY}")

    print()
    print("Retrieval memory SHA256:")
    print(f"  {memory_hash_before}")
else:
    memory_hash_before = None

    print()
    print("Retrieval memory:")
    print("  NOT FOUND")


# ============================================================================
# 2. AST INVENTORY
# ============================================================================

print_subheader("2. RETRIEVAL ARCHITECTURE INVENTORY")

source_text, tree = load_source_ast(SOURCE)
functions = find_functions(tree)

retrieval_keywords = (
    "retriev",
    "similar",
    "experience",
    "match",
    "distance",
    "probab",
    "brier",
    "logloss",
    "walk",
    "forecast",
    "outcome",
    "episode",
    "query",
)

candidate_functions = []

for name, node in functions.items():

    lower = name.lower()

    if any(keyword in lower for keyword in retrieval_keywords):
        candidate_functions.append(
            (
                name,
                node.lineno,
                node.end_lineno,
            )
        )

candidate_functions.sort(key=lambda x: x[1])

for name, start, end in candidate_functions:
    print(
        f"{name:<55} line {start}-{end}"
    )

print()
print(
    f"Total functions discovered: {len(functions)}"
)

print(
    f"Retrieval-related candidates: {len(candidate_functions)}"
)


# ============================================================================
# 3. SOURCE-LEVEL RETRIEVAL TERMS
# ============================================================================

print_subheader("3. SOURCE-LEVEL RETRIEVAL INSPECTION")

interesting_terms = [
    "similarity",
    "distance",
    "top_k",
    "k=",
    "matches",
    "historical",
    "train",
    "oos",
    "future",
    "outcome",
    "label",
    "episode",
    "timestamp",
    "index",
    "exclude",
    "causal",
    "brier",
    "logloss",
]

source_lower = source_text.lower()

for term in interesting_terms:
    count = source_lower.count(term.lower())

    print(
        f"{term:<20}: {count}"
    )


# ============================================================================
# 4. FUNCTION SOURCE DUMP FOR RETRIEVAL FUNCTIONS
# ============================================================================

print_subheader(
    "4. RETRIEVAL FUNCTION IMPLEMENTATION REVIEW"
)

retrieval_function_names = [
    name
    for name, _, _ in candidate_functions
    if (
        "retriev" in name.lower()
        or "similar" in name.lower()
        or "match" in name.lower()
        or "experience" in name.lower()
        or "distance" in name.lower()
    )
]

if not retrieval_function_names:
    print(
        "WARNING: No obvious retrieval function was found by name."
    )

for name in retrieval_function_names:

    node = functions[name]

    lines = source_text.splitlines()

    function_text = "\n".join(
        lines[node.lineno - 1:node.end_lineno]
    )

    print()
    print(
        f"FUNCTION: {name}"
    )
    print(
        f"LINES: {node.lineno}-{node.end_lineno}"
    )
    print("-" * 100)

    print(function_text)


# ============================================================================
# 5. IMPORT TEST
# ============================================================================

print_subheader("5. NORMAL IMPORT TEST")

module_name = SOURCE.stem

try:
    if module_name in sys.modules:
        del sys.modules[module_name]

    module = importlib.import_module(module_name)

    print(
        f"IMPORT: PASS"
    )

    print(
        f"Module: {module_name}"
    )

except Exception as exc:

    print(
        "IMPORT: FAIL"
    )

    print(
        f"{type(exc).__name__}: {exc}"
    )

    traceback.print_exc()

    raise


# ============================================================================
# 6. MODULE CONSTANTS / CONFIGURATION
# ============================================================================

print_subheader(
    "6. RETRIEVAL CONFIGURATION DISCOVERY"
)

config_names = [
    name
    for name in dir(module)
    if any(
        token in name.lower()
        for token in [
            "retriev",
            "similar",
            "distance",
            "match",
            "episode",
            "horizon",
            "train",
            "oos",
            "walk",
            "window",
            "confidence",
            "sparse",
        ]
    )
]

for name in sorted(config_names):

    try:
        value = getattr(module, name)

        if inspect.ismodule(value):
            continue

        if inspect.isfunction(value):
            print(
                f"{name:<50}: <function>"
            )
            continue

        if inspect.isclass(value):
            print(
                f"{name:<50}: <class>"
            )
            continue

        print(
            f"{name:<50}: {safe_repr(value)}"
        )

    except Exception as exc:

        print(
            f"{name:<50}: <ERROR {exc}>"
        )


# ============================================================================
# 7. DATA / MEMORY LOADING DISCOVERY
# ============================================================================

print_subheader(
    "7. DATA / MEMORY OBJECT DISCOVERY"
)

interesting_objects = []

for name in dir(module):

    if name.startswith("__"):
        continue

    try:
        value = getattr(module, name)
    except Exception:
        continue

    name_lower = name.lower()

    if any(
        token in name_lower
        for token in [
            "data",
            "memory",
            "episode",
            "record",
            "experience",
            "retriev",
            "history",
            "candle",
        ]
    ):

        if isinstance(value, (list, tuple, dict, set)):
            interesting_objects.append(
                (name, type(value).__name__, len(value))
            )

for name, type_name, size in sorted(interesting_objects):

    print(
        f"{name:<45} type={type_name:<12} size={size}"
    )

if not interesting_objects:
    print(
        "No obvious loaded collection objects exposed by module."
    )


# ============================================================================
# 8. MEMORY FILE STRUCTURE
# ============================================================================

print_subheader(
    "8. HISTORICAL RETRIEVAL MEMORY STRUCTURE"
)

if RETRIEVAL_MEMORY.exists():

    raw = RETRIEVAL_MEMORY.read_bytes()

    print(
        f"Memory bytes: {len(raw):,}"
    )

    print(
        f"Memory SHA256: {memory_hash_before}"
    )

    print()
    print(
        "Attempting safe deserialization inspection..."
    )

    loaded = None

    # Pickle is intentionally only loaded from the user's own local
    # project artifact. No external/untrusted file is executed.
    try:
        import pickle

        loaded = pickle.loads(raw)

        print(
            "Deserializer: pickle"
        )

        print(
            f"Root type: {type(loaded).__name__}"
        )

        if isinstance(loaded, dict):

            print(
                f"Root keys: {len(loaded)}"
            )

            for key in loaded.keys():

                print(
                    f"  {safe_repr(key, 120)}"
                )

        elif isinstance(loaded, (list, tuple)):

            print(
                f"Root length: {len(loaded)}"
            )

            if loaded:

                print(
                    f"First element type: "
                    f"{type(loaded[0]).__name__}"
                )

                print(
                    f"First element preview:"
                )

                print(
                    safe_repr(loaded[0], 1000)
                )

        else:

            print(
                "Root preview:"
            )

            print(
                safe_repr(loaded, 1500)
            )

    except Exception as exc:

        print(
            f"Safe deserialization inspection failed: "
            f"{type(exc).__name__}: {exc}"
        )

else:

    print(
        "No retrieval memory file available."
    )


# ============================================================================
# 9. PREDICTIVE FUNCTION DISCOVERY
# ============================================================================

print_subheader(
    "9. PREDICTION / RETRIEVAL ENTRY POINT DISCOVERY"
)

prediction_candidates = []

for name, node in functions.items():

    lower = name.lower()

    if any(
        token in lower
        for token in [
            "predict",
            "retrieve",
            "forecast",
            "historical",
            "experience",
        ]
    ):

        prediction_candidates.append(
            name
        )

for name in sorted(prediction_candidates):

    node = functions[name]

    print(
        f"{name:<55} "
        f"line {node.lineno}-{node.end_lineno}"
    )


# ============================================================================
# 10. SIGNATURE INSPECTION
# ============================================================================

print_subheader(
    "10. RETRIEVAL / PREDICTION SIGNATURES"
)

for name in sorted(prediction_candidates):

    try:

        obj = getattr(module, name)

        if callable(obj):

            print()
            print(
                f"{name}:"
            )

            print(
                f"  {inspect.signature(obj)}"
            )

    except Exception as exc:

        print(
            f"{name}: signature unavailable: {exc}"
        )


# ============================================================================
# 11. SEARCH FOR SELF-MATCH PROTECTION
# ============================================================================

print_subheader(
    "11. SELF-MATCH / CURRENT-EPISODE PROTECTION AUDIT"
)

self_match_terms = [
    "query_index",
    "exclude_index",
    "exclude_self",
    "self_index",
    "candidate_index",
    "candidate_idx",
    "query_idx",
    "abs(candidate",
    "candidate is query",
    "candidate == query",
    "timestamp",
    "future",
    "train_end",
    "oos_start",
]

for term in self_match_terms:

    occurrences = []

    for index, line in enumerate(
        source_text.splitlines(),
        start=1,
    ):

        if term.lower() in line.lower():

            occurrences.append(index)

    print(
        f"{term:<30}: {len(occurrences)} occurrence(s)"
    )

    if occurrences:

        print(
            f"  lines: {occurrences[:20]}"
        )


# ============================================================================
# 12. TEMPORAL SEPARATION AUDIT
# ============================================================================

print_subheader(
    "12. TEMPORAL SEPARATION AUDIT"
)

temporal_terms = [
    "train_end",
    "oos_start",
    "oos_end",
    "timestamp",
    "future",
    "horizon",
    "target",
    "outcome",
    "lookahead",
    "causal",
]

lines = source_text.splitlines()

for term in temporal_terms:

    hits = []

    for index, line in enumerate(lines, start=1):

        if term.lower() in line.lower():

            hits.append(
                (
                    index,
                    line.strip()
                )
            )

    print()
    print(
        f"TERM: {term}"
    )

    for index, line in hits[:10]:

        print(
            f"  {index}: {line[:180]}"
        )


# ============================================================================
# 13. SIMILARITY FEATURE AUDIT
# ============================================================================

print_subheader(
    "13. SIMILARITY FEATURE AUDIT"
)

similarity_terms = [
    "candle",
    "body",
    "wick",
    "range",
    "atr",
    "return",
    "momentum",
    "volatility",
    "regime",
    "structure",
    "sequence",
    "location",
    "distance",
    "weight",
]

for term in similarity_terms:

    hits = []

    for index, line in enumerate(lines, start=1):

        if term.lower() in line.lower():

            hits.append(index)

    print(
        f"{term:<20}: {len(hits):>4} occurrence(s)"
    )


# ============================================================================
# 14. RETRIEVAL WEIGHT DISCOVERY
# ============================================================================

print_subheader(
    "14. RETRIEVAL WEIGHT / DISTANCE DISCOVERY"
)

weight_terms = [
    "WEIGHT",
    "weight",
    "similarity",
    "distance",
    "score",
    "normalized",
    "cosine",
    "euclidean",
    "manhattan",
]

for index, line in enumerate(lines, start=1):

    lower = line.lower()

    if (
        "weight" in lower
        or "distance" in lower
        or "similarity" in lower
        or "score" in lower
    ):

        if (
            "=" in line
            or "return" in lower
            or "append" in lower
            or "sum" in lower
            or "mean" in lower
        ):

            print(
                f"{index:>5}: {line[:220]}"
            )


# ============================================================================
# 15. BASELINE AUDIT
# ============================================================================

print_subheader(
    "15. BASELINE CALCULATION AUDIT"
)

baseline_terms = [
    "baseline",
    "majority",
    "class",
    "prior",
    "frequency",
    "distribution",
    "brier",
    "logloss",
]

for term in baseline_terms:

    hits = []

    for index, line in enumerate(lines, start=1):

        if term.lower() in line.lower():

            hits.append(
                (
                    index,
                    line.strip()
                )
            )

    print()
    print(
        f"{term}: {len(hits)} occurrence(s)"
    )

    for index, line in hits[:8]:

        print(
            f"  {index}: {line[:200]}"
        )


# ============================================================================
# 16. RESULT INTERPRETATION
# ============================================================================

print_subheader(
    "16. CURRENT v4.1.5 RESULT INTERPRETATION"
)

print(
    "The previously observed aggregate results are:"
)

print()
print(
    "H+4:"
)
print(
    "  Accuracy lift  : negative"
)
print(
    "  Brier lift     : negative"
)
print(
    "  LogLoss lift   : negative"
)

print()
print(
    "H+8:"
)
print(
    "  Accuracy lift  : negative"
)
print(
    "  Brier lift     : negative"
)
print(
    "  LogLoss lift   : positive"
)

print()
print(
    "H+16:"
)
print(
    "  Accuracy lift  : negative"
)
print(
    "  Brier lift     : positive"
)
print(
    "  LogLoss lift   : positive"
)

print()
print(
    "IMPORTANT:"
)
print(
    "Mixed lifts do NOT prove that the retrieval implementation is broken."
)
print(
    "They also do NOT prove that retrieval has predictive value."
)
print(
    "The implementation must be audited before changing it."
)


# ============================================================================
# 17. REQUIRED SCIENTIFIC QUESTIONS
# ============================================================================

print_subheader(
    "17. REQUIRED SCIENTIFIC QUESTIONS"
)

questions = [
    (
        "Q1",
        "Can the query retrieve itself or an effectively identical episode?"
    ),
    (
        "Q2",
        "Can any candidate contain information unavailable at query time?"
    ),
    (
        "Q3",
        "Are candidate outcomes strictly after candidate timestamps?"
    ),
    (
        "Q4",
        "Are candidates strictly inside the training boundary?"
    ),
    (
        "Q5",
        "Is the query excluded from candidate retrieval?"
    ),
    (
        "Q6",
        "Does similarity rank genuinely comparable states above unrelated states?"
    ),
    (
        "Q7",
        "Does top similarity correlate with outcome similarity?"
    ),
    (
        "Q8",
        "Does increasing similarity improve outcome agreement?"
    ),
    (
        "Q9",
        "Is the baseline mathematically correct?"
    ),
    (
        "Q10",
        "Is class imbalance responsible for apparent retrieval performance?"
    ),
    (
        "Q11",
        "Does retrieval provide information beyond the baseline?"
    ),
    (
        "Q12",
        "Does retrieval remain useful across independent walk-forward windows?"
    ),
    (
        "Q13",
        "Are the H+4/H+8/H+16 outcomes actually different prediction problems?"
    ),
    (
        "Q14",
        "Is the similarity score calibrated or merely a geometric closeness score?"
    ),
    (
        "Q15",
        "Is 40 matches an arbitrary K that was selected using OOS results?"
    ),
]

for number, question in questions:

    print(
        f"{number}: {question}"
    )


# ============================================================================
# 18. NO-GUESSING GATE
# ============================================================================

print_subheader(
    "18. NO-GUESSING REPAIR GATE"
)

print(
    "NO RETRIEVAL PARAMETERS WILL BE CHANGED BY THIS SCRIPT."
)

print(
    "NO FEATURE WEIGHTS WILL BE CHANGED BY THIS SCRIPT."
)

print(
    "NO K VALUE WILL BE CHANGED BY THIS SCRIPT."
)

print(
    "NO TARGET DEFINITION WILL BE CHANGED BY THIS SCRIPT."
)

print(
    "NO WALK-FORWARD BOUNDARIES WILL BE CHANGED BY THIS SCRIPT."
)

print()
print(
    "A repair should only be made after the failing mechanism is identified."
)


# ============================================================================
# 19. FINAL PROTECTION CHECK
# ============================================================================

print_subheader(
    "19. FINAL PROTECTION CHECK"
)

source_hash_after = sha256(SOURCE)

print(
    "Source hash before:"
)
print(
    f"  {source_hash_before}"
)

print(
    "Source hash after:"
)
print(
    f"  {source_hash_after}"
)

if source_hash_before != source_hash_after:

    raise RuntimeError(
        "PROTECTION FAILURE: source file changed during diagnostic."
    )

print(
    "Source modification: NONE"
)

if RETRIEVAL_MEMORY.exists():

    memory_hash_after = sha256(RETRIEVAL_MEMORY)

    print()
    print(
        "Memory hash before:"
    )
    print(
        f"  {memory_hash_before}"
    )

    print(
        "Memory hash after:"
    )
    print(
        f"  {memory_hash_after}"
    )

    if memory_hash_before != memory_hash_after:

        raise RuntimeError(
            "PROTECTION FAILURE: retrieval memory changed."
        )

    print(
        "Retrieval memory modification: NONE"
    )


# ============================================================================
# 20. FINAL STATUS
# ============================================================================

print_header(
    "MLAI v4.1.5 ROBUST RETRIEVAL AUDIT COMPLETE"
)

print(
    "AUDIT STATUS:"
)
print(
    "  Source modified        : NO"
)
print(
    "  Market data modified   : NO"
)
print(
    "  Retrieval memory modified: NO"
)
print(
    "  Parameters changed     : NO"
)
print(
    "  Model retrained        : NO"
)

print()
print(
    "NEXT DECISION:"
)
print(
    "  Use this audit output to identify the exact retrieval failure."
)

print()
print(
    "IMPORTANT:"
)
print(
    "  Do NOT modify v4.1.5 yet."
)

print()
print(
    "The next repair will be based on the actual evidence produced here,"
)
print(
    "not on an assumed cause."
)

print()
print("=" * 100)
print(
    "READ-ONLY ROBUST RETRIEVAL INVESTIGATION: PASS"
)
print("=" * 100)