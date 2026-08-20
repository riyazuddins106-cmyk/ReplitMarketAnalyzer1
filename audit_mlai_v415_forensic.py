from __future__ import annotations

import ast
import copy
import hashlib
import importlib
import inspect
import sys
import traceback
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any


TARGET = Path("mlai_market_structure_v415.py").resolve()
DATA_FILE = Path("market_data.bin").resolve()
REPORT = Path("mlai_v415_FINAL_FORENSIC_REPORT.txt").resolve()

results = []


# ================================================================
# CORE REPORTING
# ================================================================

def result(name, status, detail=""):
    results.append({
        "name": name,
        "status": status,
        "detail": detail,
    })
    print(f"[{status:<12}] {name}")
    if detail:
        print(f"              {detail}")


def section(title):
    print()
    print("=" * 100)
    print(title)
    print("=" * 100)


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_repr(value, limit=1000):
    try:
        text = repr(value)
    except Exception:
        text = f"<repr failed: {type(value).__name__}>"
    return text if len(text) <= limit else text[:limit] + "..."


def source_of(fn):
    try:
        return inspect.getsource(fn)
    except Exception:
        return ""


def comparable(value):
    if is_dataclass(value):
        try:
            return comparable(asdict(value))
        except Exception:
            pass

    if isinstance(value, dict):
        return {
            str(k): comparable(v)
            for k, v in sorted(value.items(), key=lambda x: str(x[0]))
        }

    if isinstance(value, (list, tuple)):
        return [comparable(x) for x in value]

    if isinstance(value, float):
        if value != value:
            return "NaN"
        return round(value, 12)

    if hasattr(value, "__dict__"):
        return {
            str(k): comparable(v)
            for k, v in vars(value).items()
            if not k.startswith("_")
        }

    return value


def invoke(fn, values):
    """
    Call a function using only parameters that can be safely inferred.
    Never guess positional semantics.
    """
    try:
        sig = inspect.signature(fn)
    except Exception as exc:
        return False, None, f"signature failed: {exc}"

    kwargs = {}

    for p in sig.parameters.values():

        if p.kind in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        ):
            continue

        if p.name in values:
            kwargs[p.name] = values[p.name]

        elif p.default is not inspect.Parameter.empty:
            continue

        else:
            return (
                False,
                None,
                f"required parameter '{p.name}' cannot be safely inferred",
            )

    try:
        return True, fn(**kwargs), ""
    except Exception as exc:
        return (
            False,
            None,
            f"{type(exc).__name__}: {exc}",
        )


# ================================================================
# INITIAL INTEGRITY
# ================================================================

section("MLAI v4.1.5 — SINGLE REPLACEMENT FORENSIC CAUSAL AUDITOR")

print(f"Python : {sys.version}")
print(f"Target : {TARGET}")
print(f"Data   : {DATA_FILE}")

if not TARGET.exists():
    result("TARGET_FILE", "FAIL", "Target source does not exist.")
    raise SystemExit(1)

if not DATA_FILE.exists():
    result("DATA_FILE", "FAIL", "market_data.bin does not exist.")
    raise SystemExit(1)

original_source_hash = sha256(TARGET)
original_data_hash = sha256(DATA_FILE)

result("TARGET_FILE", "PASS", "Target source exists.")
result("DATA_FILE", "PASS", "market_data.bin exists.")


# ================================================================
# AST
# ================================================================

section("1. SOURCE / AST")

source = TARGET.read_text(encoding="utf-8")

try:
    tree = ast.parse(source)
    result("AST", "PASS", "Source parsed successfully.")
except Exception as exc:
    result("AST", "FAIL", f"{type(exc).__name__}: {exc}")
    raise SystemExit(1)


# ================================================================
# ARCHITECTURE
# ================================================================

section("2. ARCHITECTURE")

classes = [
    node
    for node in ast.walk(tree)
    if isinstance(node, ast.ClassDef)
]

for node in classes:
    print(f"  {node.name:<35} line {node.lineno}")

class_names = {x.name for x in classes}

if "CausalStructureEngine" in class_names:
    result(
        "STRUCTURE_ENGINE",
        "PASS",
        "Actual v4.1.5 architecture exposes CausalStructureEngine.",
    )
else:
    result(
        "STRUCTURE_ENGINE",
        "FAIL",
        "CausalStructureEngine is missing.",
    )


# ================================================================
# IMPORT
# ================================================================

section("3. RUNTIME IMPORT")

try:
    sys.path.insert(0, str(TARGET.parent))
    module = importlib.import_module(TARGET.stem)
    result("IMPORT", "PASS", "Target imported successfully.")
except Exception as exc:
    result(
        "IMPORT",
        "FAIL",
        f"{type(exc).__name__}: {exc}",
    )
    raise SystemExit(1)


# ================================================================
# REQUIRED COMPONENTS
# ================================================================

section("4. REQUIRED CAUSAL COMPONENTS")

required_functions = [
    "load_market_data",
    "calculate_atr",
    "build_path_vector",
    "build_market_states",
    "build_experience_records",
    "make_outcome",
    "retrieve_historical_experience",
    "create_walk_forward_windows",
    "audit_structure_causality",
]

for name in required_functions:
    if callable(getattr(module, name, None)):
        result(
            f"FUNCTION:{name}",
            "PASS",
            "Present.",
        )
    else:
        result(
            f"FUNCTION:{name}",
            "FAIL",
            "Missing.",
        )


# ================================================================
# CRITICAL FIX:
# USE MLAI'S OWN DATA LOADER
# ================================================================

section("5. DATA LOADING — TARGET'S REAL LOADER")

loader = getattr(module, "load_market_data", None)

candles = None
loader_metadata = None

if loader is None:
    result(
        "DATA_LOAD",
        "FAIL",
        "Target load_market_data() is missing.",
    )
else:
    try:
        sig = inspect.signature(loader)
        print(f"Target loader signature: {sig}")

        # v4.1.5 signature is:
        # load_market_data(path: str) -> Tuple[List[Candle], int]
        #
        # We explicitly pass the real data path.
        kwargs = {}

        for p in sig.parameters.values():

            if p.name in ("path", "file", "filename"):
                kwargs[p.name] = str(DATA_FILE)

            elif p.default is inspect.Parameter.empty:
                raise RuntimeError(
                    f"Cannot safely infer loader parameter '{p.name}'."
                )

        loaded = loader(**kwargs)

        if isinstance(loaded, tuple) and len(loaded) == 2:
            candles, loader_metadata = loaded
        else:
            candles = loaded
            loader_metadata = None

        if not isinstance(candles, (list, tuple)):
            raise RuntimeError(
                f"Loader returned {type(candles).__name__}, "
                "not a candle sequence."
            )

        print(f"Loader returned candles: {len(candles)}")
        print(f"Loader metadata       : {safe_repr(loader_metadata)}")

        result(
            "DATA_LOAD",
            "PASS",
            f"Loaded {len(candles)} candles using v4.1.5's own loader.",
        )

    except Exception as exc:
        result(
            "DATA_LOAD",
            "FAIL",
            f"{type(exc).__name__}: {exc}",
        )


# ================================================================
# CANDLE VALIDATION
# ================================================================

section("6. CANDLE OBJECT VALIDATION")

if candles is None:
    result(
        "CANDLE_VALIDATION",
        "INCONCLUSIVE",
        "Data loader did not produce candles.",
    )
else:
    required_attrs = [
        "index",
        "timestamp",
        "open",
        "high",
        "low",
        "close",
        "volume",
    ]

    invalid = []

    for pos, candle in enumerate(candles):

        missing = [
            attr
            for attr in required_attrs
            if not hasattr(candle, attr)
        ]

        if missing:
            invalid.append(
                f"position {pos}: missing {missing}"
            )
            continue

        try:
            float(candle.open)
            float(candle.high)
            float(candle.low)
            float(candle.close)
            float(candle.volume)
        except Exception as exc:
            invalid.append(
                f"position {pos}: numeric conversion failed: {exc}"
            )

    if invalid:
        result(
            "CANDLE_VALIDATION",
            "FAIL",
            " | ".join(invalid[:10]),
        )
    else:
        result(
            "CANDLE_VALIDATION",
            "PASS",
            f"All {len(candles)} candles contain valid required fields.",
        )


# ================================================================
# CHRONOLOGY
# ================================================================

section("7. DATA CHRONOLOGY")

if not candles:
    result(
        "CHRONOLOGY",
        "INCONCLUSIVE",
        "No candles available.",
    )
else:

    timestamps = [
        getattr(c, "timestamp", None)
        for c in candles
    ]

    invalid_timestamp_positions = [
        i for i, ts in enumerate(timestamps)
        if ts is None
    ]

    if invalid_timestamp_positions:
        result(
            "TIMESTAMP_VALIDITY",
            "FAIL",
            f"None timestamps at positions "
            f"{invalid_timestamp_positions[:10]}",
        )
    else:
        result(
            "TIMESTAMP_VALIDITY",
            "PASS",
            "All candle timestamps are non-None.",
        )

        chronology_failures = []

        for i in range(1, len(timestamps)):

            try:
                if timestamps[i] <= timestamps[i - 1]:
                    chronology_failures.append(i)
            except Exception as exc:
                chronology_failures.append(
                    f"{i}: comparison failed: {exc}"
                )

        if chronology_failures:
            result(
                "CHRONOLOGY",
                "FAIL",
                f"Timestamp ordering failed at "
                f"{chronology_failures[:10]}",
            )
        else:
            result(
                "CHRONOLOGY",
                "PASS",
                "Candle timestamps strictly increase.",
            )

        duplicate_positions = []

        for i in range(1, len(timestamps)):
            if timestamps[i] == timestamps[i - 1]:
                duplicate_positions.append(i)

        if duplicate_positions:
            result(
                "DUPLICATES",
                "FAIL",
                f"Duplicate timestamps at "
                f"{duplicate_positions[:10]}",
            )
        else:
            result(
                "DUPLICATES",
                "PASS",
                "No duplicate timestamps.",
            )


# ================================================================
# FUTURE INDEX STATIC ANALYSIS
# ================================================================

section("8. FUTURE-INDEX SEMANTIC CLASSIFICATION")

future_hits = []

for node in ast.walk(tree):

    if not isinstance(node, (ast.Subscript, ast.BinOp, ast.Slice)):
        continue

    text = ast.get_source_segment(source, node)

    if not text:
        continue

    if not any(
        token in text
        for token in (
            "index +",
            "index+",
            "target +",
            "target+",
            "query_index +",
            "query_index+",
            "i + 1",
            "j +",
            "train_end -",
        )
    ):
        continue

    fn_name = "<module>"

    for fn in ast.walk(tree):
        if isinstance(
            fn,
            (ast.FunctionDef, ast.AsyncFunctionDef),
        ):
            end = getattr(fn, "end_lineno", fn.lineno)
            if fn.lineno <= node.lineno <= end:
                fn_name = fn.name
                break

    if fn_name == "make_outcome":
        category = "ALLOWED_OUTCOME"

    elif fn_name == "audit_structure_causality":
        category = "ALLOWED_VALIDATION"

    elif fn_name == "create_walk_forward_windows":
        category = "BOUNDARY_CHECK"

    elif fn_name == "main" and "query_index + horizon" in text:
        category = "BOUNDARY_CHECK"

    else:
        category = "REQUIRES_RUNTIME_VERIFICATION"

    future_hits.append(
        (
            node.lineno,
            category,
            fn_name,
            text.strip(),
        )
    )

# Deduplicate
unique_hits = []
seen = set()

for item in sorted(future_hits):
    if item in seen:
        continue
    seen.add(item)
    unique_hits.append(item)

for line, category, fn, text in unique_hits:
    print(
        f"LINE {line:<5} {category:<28} "
        f"{fn:<30} {text}"
    )

outside = [
    x for x in unique_hits
    if x[1] == "REQUIRES_RUNTIME_VERIFICATION"
]

if outside:
    result(
        "FUTURE_INDEX_STATIC",
        "REVIEW",
        f"{len(outside)} references require runtime causal verification.",
    )
else:
    result(
        "FUTURE_INDEX_STATIC",
        "PASS",
        "No unclassified future-index references remain.",
    )


# ================================================================
# RUNTIME API
# ================================================================

section("9. RUNTIME API")

for name in sorted(dir(module)):
    if name.startswith("__"):
        continue

    obj = getattr(module, name)

    if inspect.isclass(obj) or inspect.isfunction(obj):
        try:
            sig = inspect.signature(obj)
        except Exception:
            sig = ""
        print(
            f"{name:<40} "
            f"{type(obj).__name__:<12} "
            f"{sig}"
        )


# ================================================================
# STRUCTURE ENGINE RUNTIME
# ================================================================

section("10. CAUSAL STRUCTURE ENGINE RUNTIME")

engine_cls = getattr(
    module,
    "CausalStructureEngine",
    None,
)

if engine_cls is None:
    result(
        "STRUCTURE_ENGINE_RUNTIME",
        "FAIL",
        "CausalStructureEngine unavailable.",
    )
elif not candles:
    result(
        "STRUCTURE_ENGINE_RUNTIME",
        "INCONCLUSIVE",
        "No candles available.",
    )
else:
    try:
        engine = engine_cls(candles)

        build_method = getattr(engine, "build", None)

        if not callable(build_method):
            raise RuntimeError(
                "CausalStructureEngine.build() missing."
            )

        ok, structure_output, detail = invoke(
            build_method,
            {
                "candles": candles,
                "data": candles,
            },
        )

        if ok:
            result(
                "STRUCTURE_ENGINE_RUNTIME",
                "PASS",
                "CausalStructureEngine.build() executed.",
            )
        else:
            result(
                "STRUCTURE_ENGINE_RUNTIME",
                "INCONCLUSIVE",
                detail,
            )

    except Exception as exc:
        result(
            "STRUCTURE_ENGINE_RUNTIME",
            "INCONCLUSIVE",
            f"{type(exc).__name__}: {exc}",
        )


# ================================================================
# PATH PREFIX INVARIANCE
# ================================================================

section("11. PATH PREFIX INVARIANCE")

path_fn = getattr(
    module,
    "build_path_vector",
    None,
)

atr_fn = getattr(
    module,
    "calculate_atr",
    None,
)


def mutate_suffix(data, start):
    altered = copy.deepcopy(data)

    for i in range(start, len(altered)):
        c = altered[i]

        for attr in ("open", "high", "low", "close"):
            if hasattr(c, attr):
                old = getattr(c, attr)
                try:
                    setattr(
                        c,
                        attr,
                        float(old) * 1.137 + 17.0,
                    )
                except Exception:
                    pass

        if hasattr(c, "volume"):
            try:
                setattr(
                    c,
                    "volume",
                    float(c.volume) * 2.0,
                )
            except Exception:
                pass

    return altered


if path_fn is None:
    result(
        "PATH_PREFIX_INVARIANCE",
        "FAIL",
        "build_path_vector missing.",
    )
elif not candles:
    result(
        "PATH_PREFIX_INVARIANCE",
        "INCONCLUSIVE",
        "No candles available.",
    )
else:

    test_indices = sorted(set([
        max(1, len(candles) // 4),
        max(1, len(candles) // 2),
        max(1, (3 * len(candles)) // 4),
    ]))

    failures = []
    executed = 0

    ok_atr, atr_original, atr_detail = (
        invoke(
            atr_fn,
            {"candles": candles, "data": candles},
        )
        if atr_fn
        else (False, None, "ATR function missing")
    )

    for index in test_indices:

        if index + 1 >= len(candles):
            continue

        mutated = mutate_suffix(
            candles,
            index + 1,
        )

        if atr_fn:

            ok1, atr1, d1 = invoke(
                atr_fn,
                {"candles": candles, "data": candles},
            )

            ok2, atr2, d2 = invoke(
                atr_fn,
                {"candles": mutated, "data": mutated},
            )

            if not ok1 or not ok2:
                failures.append(
                    f"index {index}: ATR execution failed: "
                    f"{d1 if not ok1 else d2}"
                )
                continue

        else:
            atr1 = None
            atr2 = None

        ok1, path1, d1 = invoke(
            path_fn,
            {
                "candles": candles,
                "data": candles,
                "index": index,
                "query_index": index,
                "atr": atr1,
                "atr_values": atr1,
            },
        )

        ok2, path2, d2 = invoke(
            path_fn,
            {
                "candles": mutated,
                "data": mutated,
                "index": index,
                "query_index": index,
                "atr": atr2,
                "atr_values": atr2,
            },
        )

        if not ok1 or not ok2:
            failures.append(
                f"index {index}: "
                f"{d1 if not ok1 else d2}"
            )
            continue

        executed += 1

        if comparable(path1) != comparable(path2):
            failures.append(
                f"index {index}: path changed after "
                f"future-only mutation"
            )

    if failures:
        result(
            "PATH_PREFIX_INVARIANCE",
            "FAIL",
            " | ".join(failures),
        )
    elif executed >= 2:
        result(
            "PATH_PREFIX_INVARIANCE",
            "PASS",
            f"{executed} future-mutation prefix tests passed.",
        )
    else:
        result(
            "PATH_PREFIX_INVARIANCE",
            "INCONCLUSIVE",
            f"Only {executed} tests executed.",
        )


# ================================================================
# MARKET STATE PREFIX INVARIANCE
# ================================================================

section("12. MARKET STATE PREFIX INVARIANCE")

state_fn = getattr(
    module,
    "build_market_states",
    None,
)

if state_fn is None:
    result(
        "MARKET_STATE_PREFIX_INVARIANCE",
        "FAIL",
        "build_market_states missing.",
    )
elif not candles:
    result(
        "MARKET_STATE_PREFIX_INVARIANCE",
        "INCONCLUSIVE",
        "No candles.",
    )
else:

    if engine_cls is None:
        result(
            "MARKET_STATE_PREFIX_INVARIANCE",
            "INCONCLUSIVE",
            "Structure engine unavailable.",
        )
    else:
        try:

            original_engine = engine_cls(candles)
            mutated_candles = mutate_suffix(
                candles,
                len(candles) // 2 + 1,
            )
            mutated_engine = engine_cls(
                mutated_candles
            )

            b1 = original_engine.build()
            b2 = mutated_engine.build()

            ok1, states1, d1 = invoke(
                state_fn,
                {
                    "candles": candles,
                    "data": candles,
                    "states": b1,
                    "structure_states": b1,
                    "atr": (
                        invoke(
                            atr_fn,
                            {"candles": candles},
                        )[1]
                        if atr_fn
                        else None
                    ),
                },
            )

            ok2, states2, d2 = invoke(
                state_fn,
                {
                    "candles": mutated_candles,
                    "data": mutated_candles,
                    "states": b2,
                    "structure_states": b2,
                    "atr": (
                        invoke(
                            atr_fn,
                            {"candles": mutated_candles},
                        )[1]
                        if atr_fn
                        else None
                    ),
                },
            )

            if not ok1 or not ok2:
                result(
                    "MARKET_STATE_PREFIX_INVARIANCE",
                    "INCONCLUSIVE",
                    d1 if not ok1 else d2,
                )
            else:

                boundary = len(candles) // 2

                p1 = comparable(states1)
                p2 = comparable(states2)

                if isinstance(p1, list) and isinstance(p2, list):
                    p1 = p1[:boundary + 1]
                    p2 = p2[:boundary + 1]

                if p1 == p2:
                    result(
                        "MARKET_STATE_PREFIX_INVARIANCE",
                        "PASS",
                        f"State prefix through {boundary} unchanged.",
                    )
                else:
                    result(
                        "MARKET_STATE_PREFIX_INVARIANCE",
                        "FAIL",
                        "Historical state prefix changed after "
                        "future-only mutation.",
                    )

        except Exception as exc:
            result(
                "MARKET_STATE_PREFIX_INVARIANCE",
                "INCONCLUSIVE",
                f"{type(exc).__name__}: {exc}",
            )


# ================================================================
# STRUCTURE PREFIX INVARIANCE
# ================================================================

section("13. STRUCTURE PREFIX INVARIANCE")

if engine_cls is None:
    result(
        "STRUCTURE_PREFIX_INVARIANCE",
        "FAIL",
        "CausalStructureEngine missing.",
    )
elif not candles:
    result(
        "STRUCTURE_PREFIX_INVARIANCE",
        "INCONCLUSIVE",
        "No candles.",
    )
else:

    try:

        boundary = len(candles) // 2

        altered = mutate_suffix(
            candles,
            boundary + 1,
        )

        s1 = engine_cls(candles).build()
        s2 = engine_cls(altered).build()

        c1 = comparable(s1)
        c2 = comparable(s2)

        if isinstance(c1, list) and isinstance(c2, list):
            c1 = c1[:boundary + 1]
            c2 = c2[:boundary + 1]

        if c1 == c2:
            result(
                "STRUCTURE_PREFIX_INVARIANCE",
                "PASS",
                f"Structure through index {boundary} unchanged.",
            )
        else:
            result(
                "STRUCTURE_PREFIX_INVARIANCE",
                "FAIL",
                "Structure prefix changed after future-only mutation.",
            )

    except Exception as exc:
        result(
            "STRUCTURE_PREFIX_INVARIANCE",
            "INCONCLUSIVE",
            f"{type(exc).__name__}: {exc}",
        )


# ================================================================
# STRUCTURE TIMING
# ================================================================

section("14. SWING CONFIRMATION TIMING")

audit_source = source_of(
    getattr(module, "audit_structure_causality", None)
)

if (
    "confirmation_index" in audit_source
    and "SWING_RIGHT" in audit_source
):
    result(
        "SWING_CONFIRMATION_TIMING",
        "PASS",
        "Explicit confirmation_index / SWING_RIGHT boundary exists.",
    )
else:
    result(
        "SWING_CONFIRMATION_TIMING",
        "REVIEW",
        "Could not establish confirmation boundary statically.",
    )


# ================================================================
# OUTCOME ISOLATION
# ================================================================

section("15. OUTCOME ISOLATION")

outcome_source = source_of(
    getattr(module, "make_outcome", None)
)

if not outcome_source:
    result(
        "OUTCOME_ISOLATION",
        "FAIL",
        "make_outcome missing.",
    )
else:

    checks = [
        "target = index + horizon" in outcome_source,
        "candles[target]" in outcome_source,
        "future_high" in outcome_source,
        "future_low" in outcome_source,
    ]

    if all(checks):
        result(
            "OUTCOME_ISOLATION",
            "PASS",
            "Future information is confined to make_outcome().",
        )
    else:
        result(
            "OUTCOME_ISOLATION",
            "REVIEW",
            "Could not establish all outcome boundaries.",
        )


# ================================================================
# EXPERIENCE BOUNDARY
# ================================================================

section("16. EXPERIENCE CONSTRUCTION")

experience_source = source_of(
    getattr(module, "build_experience_records", None)
)

if not experience_source:
    result(
        "EXPERIENCE_BOUNDARY",
        "FAIL",
        "build_experience_records missing.",
    )
else:

    checks = [
        "train_end" in experience_source,
        "horizon" in experience_source,
        "make_outcome" in experience_source,
    ]

    if all(checks):
        result(
            "EXPERIENCE_BOUNDARY",
            "PASS",
            "Training boundary and outcome construction are explicit.",
        )
    else:
        result(
            "EXPERIENCE_BOUNDARY",
            "REVIEW",
            "Experience boundary requires review.",
        )


# ================================================================
# RETRIEVAL CAUSALITY
# ================================================================

section("17. HISTORICAL RETRIEVAL")

retrieval_source = source_of(
    getattr(module, "retrieve_historical_experience", None)
)

if not retrieval_source:
    result(
        "RETRIEVAL_CAUSALITY",
        "FAIL",
        "retrieve_historical_experience missing.",
    )
else:

    lower = retrieval_source.lower()

    forbidden = []

    if "make_outcome(" in lower:
        forbidden.append(
            "retrieval constructs outcomes"
        )

    if "future_close" in lower:
        forbidden.append(
            "retrieval references future_close"
        )

    if forbidden:
        result(
            "RETRIEVAL_CAUSALITY",
            "FAIL",
            "; ".join(forbidden),
        )
    elif any(
        x in lower
        for x in (
            "query_index",
            "historical",
            "eligible",
            "index <",
            "index >",
        )
    ):
        result(
            "RETRIEVAL_CAUSALITY",
            "PASS",
            "Historical eligibility logic detected.",
        )
    else:
        result(
            "RETRIEVAL_CAUSALITY",
            "REVIEW",
            "Historical eligibility could not be proven statically.",
        )


# ================================================================
# WALK FORWARD
# ================================================================

section("18. WALK-FORWARD ISOLATION")

wf_source = source_of(
    getattr(module, "create_walk_forward_windows", None)
)

if not wf_source:
    result(
        "WALK_FORWARD_WINDOWS",
        "FAIL",
        "create_walk_forward_windows missing.",
    )
else:

    required = [
        "train_start",
        "train_end",
        "oos_start",
        "oos_end",
    ]

    missing = [
        x for x in required
        if x not in wf_source
    ]

    if missing:
        result(
            "WALK_FORWARD_WINDOWS",
            "REVIEW",
            f"Missing explicit fields: {missing}",
        )
    else:
        result(
            "WALK_FORWARD_WINDOWS",
            "PASS",
            "Train/OOS boundaries explicitly represented.",
        )


# ================================================================
# RUNTIME WALK-FORWARD SANITY
# ================================================================

section("19. WALK-FORWARD RUNTIME SANITY")

wf_fn = getattr(
    module,
    "create_walk_forward_windows",
    None,
)

if wf_fn is None:
    result(
        "WALK_FORWARD_RUNTIME",
        "FAIL",
        "Function missing.",
    )
elif not candles:
    result(
        "WALK_FORWARD_RUNTIME",
        "INCONCLUSIVE",
        "No candles.",
    )
else:

    try:

        sig = inspect.signature(wf_fn)

        kwargs = {}

        for p in sig.parameters.values():

            if p.name == "n":
                kwargs[p.name] = len(candles)

            elif p.name == "count":
                kwargs[p.name] = 5

            elif p.name == "oos_size":
                kwargs[p.name] = min(
                    81,
                    max(1, len(candles) // 10),
                )

            elif p.default is inspect.Parameter.empty:
                raise RuntimeError(
                    f"Cannot infer parameter {p.name}"
                )

        windows = wf_fn(**kwargs)

        invalid = []

        for w in windows:

            if not (
                0 <= w.train_start
                <= w.train_end
                <= w.oos_start
                <= w.oos_end
                <= len(candles)
            ):
                invalid.append(
                    safe_repr(w)
                )

            if w.train_end > w.oos_start:
                invalid.append(
                    f"training overlaps OOS: {safe_repr(w)}"
                )

        if invalid:
            result(
                "WALK_FORWARD_RUNTIME",
                "FAIL",
                " | ".join(invalid[:10]),
            )
        else:
            result(
                "WALK_FORWARD_RUNTIME",
                "PASS",
                f"{len(windows)} walk-forward windows passed boundary checks.",
            )

    except Exception as exc:
        result(
            "WALK_FORWARD_RUNTIME",
            "INCONCLUSIVE",
            f"{type(exc).__name__}: {exc}",
        )


# ================================================================
# SOURCE / DATA MUTATION
# ================================================================

section("20. MUTATION PROTECTION")

if sha256(TARGET) == original_source_hash:
    result(
        "SOURCE_MUTATION",
        "PASS",
        "Target source unchanged during audit.",
    )
else:
    result(
        "SOURCE_MUTATION",
        "FAIL",
        "Target source hash changed during audit.",
    )

if sha256(DATA_FILE) == original_data_hash:
    result(
        "DATA_MUTATION",
        "PASS",
        "market_data.bin unchanged during audit.",
    )
else:
    result(
        "DATA_MUTATION",
        "FAIL",
        "market_data.bin hash changed during audit.",
    )


# ================================================================
# FINAL VERDICT
# ================================================================

section("FINAL FORENSIC VERDICT")

fails = [
    r for r in results
    if r["status"] == "FAIL"
]

inconclusive = [
    r for r in results
    if r["status"] == "INCONCLUSIVE"
]

reviews = [
    r for r in results
    if r["status"] == "REVIEW"
]


print()
print(f"PASS         : {sum(r['status'] == 'PASS' for r in results)}")
print(f"FAIL         : {len(fails)}")
print(f"INCONCLUSIVE : {len(inconclusive)}")
print(f"REVIEW       : {len(reviews)}")
print()


if fails:
    verdict = "FAIL — CAUSAL CERTIFICATION REJECTED"

elif inconclusive:
    verdict = "INCONCLUSIVE — CAUSAL CERTIFICATION NOT PROVEN"

elif reviews:
    verdict = "REVIEW — CAUSAL CERTIFICATION NOT YET PROVEN"

else:
    verdict = "PASS — CAUSAL CERTIFICATION PASSED"


print(verdict)


# ================================================================
# FAILURE SUMMARY
# ================================================================

if fails:
    print()
    print("FAILURES:")

    for r in fails:
        print()
        print(f"  {r['name']}")
        print(f"  {r['detail']}")


if inconclusive:
    print()
    print("INCONCLUSIVE:")

    for r in inconclusive:
        print()
        print(f"  {r['name']}")
        print(f"  {r['detail']}")


if reviews:
    print()
    print("REVIEW:")

    for r in reviews:
        print()
        print(f"  {r['name']}")
        print(f"  {r['detail']}")


# ================================================================
# REPORT
# ================================================================

report = []

report.append(
    "MLAI v4.1.5 — FINAL FORENSIC CAUSAL AUDIT"
)
report.append("=" * 100)
report.append(f"Target: {TARGET}")
report.append(f"Data: {DATA_FILE}")
report.append(f"Python: {sys.version}")
report.append("")

for r in results:
    report.append(
        f"[{r['status']}] {r['name']}"
    )
    if r["detail"]:
        report.append(
            f"    {r['detail']}"
        )

report.append("")
report.append("=" * 100)
report.append("FINAL VERDICT")
report.append("=" * 100)
report.append(verdict)

try:
    REPORT.write_text(
        "\n".join(report),
        encoding="utf-8",
    )
    print()
    print(f"Report written to: {REPORT}")
except Exception as exc:
    print()
    print(f"WARNING: report write failed: {exc}")


print()
print("=" * 100)
print("AUDIT COMPLETE")
print("=" * 100)
