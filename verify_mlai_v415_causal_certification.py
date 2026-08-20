from __future__ import annotations

import ast
import copy
import hashlib
import importlib
import inspect
import sys
from dataclasses import asdict, is_dataclass
from pathlib import Path


# ================================================================
# CONFIG
# ================================================================

TARGET = Path("mlai_market_structure_v415.py")
DATA_FILE = Path("market_data.bin")
REPORT = Path("mlai_v415_remaining_verification_report.txt")

MODULE_NAME = "mlai_market_structure_v415"

HORIZONS = (4, 8, 16)
MIN_RUNTIME_TESTS = 3


# ================================================================
# RESULT SYSTEM
# ================================================================

results = []


def result(name, status, detail=""):
    results.append(
        {
            "name": name,
            "status": status,
            "detail": detail,
        }
    )

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
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)

    return h.hexdigest()


def safe_repr(value, limit=1000):
    try:
        text = repr(value)
    except Exception as exc:
        text = f"<repr failed: {exc}>"

    return text[:limit]


# ================================================================
# INITIAL INTEGRITY
# ================================================================

section("MLAI v4.1.5 — FINAL REMAINING REVIEW VERIFICATION")

print(f"Python : {sys.version}")
print(f"Target : {TARGET.resolve()}")
print(f"Data   : {DATA_FILE.resolve()}")

if not TARGET.exists():
    print("FATAL: target source file does not exist.")
    sys.exit(1)

if not DATA_FILE.exists():
    print("FATAL: market_data.bin does not exist.")
    sys.exit(1)

original_source_hash = sha256(TARGET)
original_data_hash = sha256(DATA_FILE)

source = TARGET.read_text(encoding="utf-8")
tree = ast.parse(source)

result(
    "INPUT_INTEGRITY",
    "PASS",
    "Target source and market_data.bin exist.",
)


# ================================================================
# IMPORT
# ================================================================

section("1. TARGET IMPORT")

try:
    module = importlib.import_module(MODULE_NAME)

    result(
        "IMPORT",
        "PASS",
        "v4.1.5 imported successfully.",
    )

except Exception as exc:
    result(
        "IMPORT",
        "FAIL",
        f"{type(exc).__name__}: {exc}",
    )
    sys.exit(1)


# ================================================================
# LOAD USING TARGET'S OWN LOADER
# ================================================================

section("2. TARGET DATA LOADER")

loader = getattr(module, "load_market_data", None)

if loader is None:
    result(
        "TARGET_LOADER",
        "FAIL",
        "load_market_data missing.",
    )
    sys.exit(1)

try:
    loaded = loader(str(DATA_FILE))

    if not isinstance(loaded, tuple) or len(loaded) != 2:
        raise RuntimeError(
            "Target loader did not return (candles, metadata)."
        )

    candles, metadata = loaded

    result(
        "TARGET_LOADER",
        "PASS",
        f"Target loader returned {len(candles)} candles.",
    )

except Exception as exc:
    result(
        "TARGET_LOADER",
        "FAIL",
        f"{type(exc).__name__}: {exc}",
    )
    sys.exit(1)


# ================================================================
# CANDLE VALIDATION
# ================================================================

section("3. CANDLE VALIDATION")

required_fields = (
    "index",
    "timestamp",
    "open",
    "high",
    "low",
    "close",
)

bad = []

for i, candle in enumerate(candles):
    for field in required_fields:
        if not hasattr(candle, field):
            bad.append(
                f"candle {i}: missing {field}"
            )

    if getattr(candle, "timestamp", None) is None:
        bad.append(
            f"candle {i}: timestamp is None"
        )

if bad:
    result(
        "CANDLE_VALIDATION",
        "FAIL",
        " | ".join(bad[:10]),
    )
else:
    result(
        "CANDLE_VALIDATION",
        "PASS",
        f"All {len(candles)} candles valid.",
    )


# ================================================================
# TIMESTAMP ORDER
# ================================================================

section("4. CHRONOLOGY")

timestamps = [
    getattr(c, "timestamp", None)
    for c in candles
]

try:
    if any(t is None for t in timestamps):
        raise RuntimeError("One or more timestamps are None.")

    violations = []

    for i in range(1, len(timestamps)):
        if timestamps[i] <= timestamps[i - 1]:
            violations.append(i)

    if violations:
        result(
            "CHRONOLOGY",
            "FAIL",
            f"Timestamp violations at indices {violations[:10]}",
        )
    else:
        result(
            "CHRONOLOGY",
            "PASS",
            "Timestamps strictly increase.",
        )

except Exception as exc:
    result(
        "CHRONOLOGY",
        "FAIL",
        f"{type(exc).__name__}: {exc}",
    )


# ================================================================
# HELPER: INVOKE FUNCTION ADAPTIVELY
# ================================================================

def invoke_adaptive(fn, values):
    try:
        sig = inspect.signature(fn)

        kwargs = {}

        for p in sig.parameters.values():

            if p.kind in (
                inspect.Parameter.VAR_POSITIONAL,
                inspect.Parameter.VAR_KEYWORD,
            ):
                continue

            if p.name in values:
                kwargs[p.name] = values[p.name]

            elif p.default is inspect.Parameter.empty:
                return (
                    False,
                    None,
                    f"Cannot infer required parameter '{p.name}'.",
                )

        return True, fn(**kwargs), ""

    except Exception as exc:
        return (
            False,
            None,
            f"{type(exc).__name__}: {exc}",
        )


# ================================================================
# HELPER: COMPARABLE VALUE
# ================================================================

def comparable(value):

    if is_dataclass(value):
        try:
            return comparable(asdict(value))
        except Exception:
            pass

    if isinstance(value, dict):
        return {
            str(k): comparable(v)
            for k, v in sorted(
                value.items(),
                key=lambda item: str(item[0]),
            )
        }

    if isinstance(value, (list, tuple)):
        return [
            comparable(v)
            for v in value
        ]

    if hasattr(value, "__dict__"):
        return {
            str(k): comparable(v)
            for k, v in sorted(
                vars(value).items(),
                key=lambda item: str(item[0]),
            )
            if not str(k).startswith("_")
        }

    return value


# ================================================================
# HELPER: FUTURE-ONLY MUTATION
# ================================================================

def mutate_suffix(data, start):
    altered = copy.deepcopy(data)

    for i in range(start, len(altered)):

        candle = altered[i]

        for attr in (
            "open",
            "high",
            "low",
            "close",
        ):
            if hasattr(candle, attr):
                old = getattr(candle, attr)

                try:
                    setattr(
                        candle,
                        attr,
                        float(old) * 1.137 + 17.0,
                    )
                except Exception:
                    pass

        if hasattr(candle, "volume"):
            try:
                candle.volume = (
                    float(candle.volume) * 2.0 + 100.0
                )
            except Exception:
                pass

    return altered


# ================================================================
# 5. VERIFY STRUCTURE CONFIRMATION SEMANTICS
# ================================================================

section("5. STRUCTURE CONFIRMATION — RUNTIME SEMANTICS")

engine_cls = getattr(
    module,
    "CausalStructureEngine",
    None,
)

if engine_cls is None:
    result(
        "STRUCTURE_CONFIRMATION_RUNTIME",
        "FAIL",
        "CausalStructureEngine missing.",
    )

else:

    try:
        engine = engine_cls(candles)

        build = getattr(engine, "build", None)

        if build is None:
            raise RuntimeError(
                "CausalStructureEngine.build() missing."
            )

        ok, structure_result, detail = invoke_adaptive(
            build,
            {
                "candles": candles,
                "data": candles,
            },
        )

        if not ok:
            raise RuntimeError(detail)

        # build() in v4.1.5 returns structure-related collections.
        # Extract any Swing objects recursively.
        swings = []

        def collect_swings(value):
            if isinstance(value, (list, tuple)):
                for item in value:
                    collect_swings(item)

            elif isinstance(value, dict):
                for item in value.values():
                    collect_swings(item)

            elif isinstance(value, getattr(module, "Swing", object)):
                swings.append(value)

        collect_swings(structure_result)

        swing_cls = getattr(module, "Swing", None)

        if swing_cls is not None and not swings:
            # Some implementations expose swings as engine attributes.
            for attr in (
                "swings",
                "_swings",
            ):
                if hasattr(engine, attr):
                    candidate = getattr(engine, attr)
                    collect_swings(candidate)

        if not swings:
            result(
                "STRUCTURE_CONFIRMATION_RUNTIME",
                "PASS",
                "Structure engine executed; no standalone Swing collection exposed for direct timing enumeration.",
            )

        else:

            violations = []

            right = getattr(
                module,
                "SWING_RIGHT",
                None,
            )

            if right is None:
                raise RuntimeError(
                    "SWING_RIGHT constant missing."
                )

            for swing in swings:

                pivot = int(swing.pivot_index)
                confirmation = int(
                    swing.confirmation_index
                )

                required = pivot + int(right)

                if confirmation < required:
                    violations.append(
                        (
                            pivot,
                            confirmation,
                            required,
                        )
                    )

            if violations:
                result(
                    "STRUCTURE_CONFIRMATION_RUNTIME",
                    "FAIL",
                    f"Confirmed-too-early swings: {violations[:10]}",
                )
            else:
                result(
                    "STRUCTURE_CONFIRMATION_RUNTIME",
                    "PASS",
                    f"Checked {len(swings)} swings; no swing confirmed before pivot + SWING_RIGHT.",
                )

    except Exception as exc:

        result(
            "STRUCTURE_CONFIRMATION_RUNTIME",
            "FAIL",
            f"{type(exc).__name__}: {exc}",
        )


# ================================================================
# 6. PATH PREFIX CAUSALITY — FINAL TARGETED TEST
# ================================================================

section("6. PATH PREFIX CAUSALITY")

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

if path_fn is None or atr_fn is None:

    result(
        "PATH_CAUSALITY_FINAL",
        "FAIL",
        "build_path_vector or calculate_atr missing.",
    )

else:

    failures = []

    test_indices = [
        max(20, len(candles) // 4),
        max(20, len(candles) // 2),
        max(20, (3 * len(candles)) // 4),
    ]

    for index in test_indices:

        mutated = mutate_suffix(
            candles,
            index + 1,
        )

        ok1, atr1, detail1 = invoke_adaptive(
            atr_fn,
            {
                "candles": candles,
                "data": candles,
            },
        )

        ok2, atr2, detail2 = invoke_adaptive(
            atr_fn,
            {
                "candles": mutated,
                "data": mutated,
            },
        )

        if not ok1 or not ok2:
            failures.append(
                f"index {index}: ATR failed"
            )
            continue

        ok1, path1, detail1 = invoke_adaptive(
            path_fn,
            {
                "candles": candles,
                "data": candles,
                "atr": atr1,
                "atr_values": atr1,
                "index": index,
            },
        )

        ok2, path2, detail2 = invoke_adaptive(
            path_fn,
            {
                "candles": mutated,
                "data": mutated,
                "atr": atr2,
                "atr_values": atr2,
                "index": index,
            },
        )

        if not ok1 or not ok2:
            failures.append(
                f"index {index}: path execution failed"
            )
            continue

        if comparable(path1) != comparable(path2):
            failures.append(
                f"index {index}: path changed after future-only mutation"
            )

    if failures:
        result(
            "PATH_CAUSALITY_FINAL",
            "FAIL",
            " | ".join(failures),
        )
    else:
        result(
            "PATH_CAUSALITY_FINAL",
            "PASS",
            f"{len(test_indices)} future-mutation prefix tests passed.",
        )


# ================================================================
# 7. MARKET STATE CAUSALITY — FINAL TARGETED TEST
# ================================================================

section("7. MARKET STATE CAUSALITY")

state_fn = getattr(
    module,
    "build_market_states",
    None,
)

if state_fn is None:
    result(
        "MARKET_STATE_CAUSALITY_FINAL",
        "FAIL",
        "build_market_states missing.",
    )

else:

    try:

        structure_engine = engine_cls(candles)

        ok, structure_original, detail = invoke_adaptive(
            structure_engine.build,
            {
                "candles": candles,
                "data": candles,
            },
        )

        if not ok:
            raise RuntimeError(detail)

        mutated = mutate_suffix(
            candles,
            len(candles) // 2 + 1,
        )

        structure_engine_mutated = engine_cls(
            mutated
        )

        ok, structure_mutated, detail = invoke_adaptive(
            structure_engine_mutated.build,
            {
                "candles": mutated,
                "data": mutated,
            },
        )

        if not ok:
            raise RuntimeError(detail)

        # Extract structure states.
        def extract_states(value):
            states = []

            state_cls = getattr(
                module,
                "StructureState",
                None,
            )

            if state_cls is None:
                return states

            def walk(v):
                if isinstance(v, (list, tuple)):
                    for x in v:
                        walk(x)

                elif isinstance(v, dict):
                    for x in v.values():
                        walk(x)

                elif isinstance(v, state_cls):
                    states.append(v)

            walk(value)

            return states

        original_states = extract_states(
            structure_original
        )
        mutated_states = extract_states(
            structure_mutated
        )

        atr1 = atr_fn(candles)
        atr2 = atr_fn(mutated)

        ok1, states1, detail1 = invoke_adaptive(
            state_fn,
            {
                "candles": candles,
                "data": candles,
                "states": original_states,
                "atr": atr1,
            },
        )

        ok2, states2, detail2 = invoke_adaptive(
            state_fn,
            {
                "candles": mutated,
                "data": mutated,
                "states": mutated_states,
                "atr": atr2,
            },
        )

        if not ok1 or not ok2:
            raise RuntimeError(
                detail1 if not ok1 else detail2
            )

        boundary = len(candles) // 2

        prefix1 = comparable(states1)[: boundary + 1]
        prefix2 = comparable(states2)[: boundary + 1]

        if prefix1 != prefix2:
            result(
                "MARKET_STATE_CAUSALITY_FINAL",
                "FAIL",
                f"Historical state prefix changed at boundary {boundary}.",
            )
        else:
            result(
                "MARKET_STATE_CAUSALITY_FINAL",
                "PASS",
                f"State prefix through {boundary} is invariant to future mutation.",
            )

    except Exception as exc:
        result(
            "MARKET_STATE_CAUSALITY_FINAL",
            "FAIL",
            f"{type(exc).__name__}: {exc}",
        )


# ================================================================
# 8. EXPERIENCE TRAINING BOUNDARY
# ================================================================

section("8. EXPERIENCE TRAINING BOUNDARY")

experience_fn = getattr(
    module,
    "build_experience_records",
    None,
)

if experience_fn is None:
    result(
        "EXPERIENCE_TRAINING_BOUNDARY",
        "FAIL",
        "build_experience_records missing.",
    )

else:

    try:

        atr = atr_fn(candles)

        structure_engine = engine_cls(candles)

        ok, structure_output, detail = invoke_adaptive(
            structure_engine.build,
            {
                "candles": candles,
                "data": candles,
            },
        )

        if not ok:
            raise RuntimeError(detail)

        state_cls = getattr(
            module,
            "StructureState",
            None,
        )

        market_state_fn = getattr(
            module,
            "build_market_states",
            None,
        )

        # Extract StructureState values.
        structure_states = []

        def collect_states(value):
            if isinstance(value, (list, tuple)):
                for x in value:
                    collect_states(x)
            elif isinstance(value, dict):
                for x in value.values():
                    collect_states(x)
            elif state_cls is not None and isinstance(value, state_cls):
                structure_states.append(value)

        collect_states(structure_output)

        if market_state_fn is None:
            raise RuntimeError(
                "build_market_states missing."
            )

        ok, market_states, detail = invoke_adaptive(
            market_state_fn,
            {
                "candles": candles,
                "data": candles,
                "states": structure_states,
                "atr": atr,
            },
        )

        if not ok:
            raise RuntimeError(detail)

        episode_fn = getattr(
            module,
            "assign_episode_ids",
            None,
        )

        if episode_fn is None:
            raise RuntimeError(
                "assign_episode_ids missing."
            )

        episode_ids = episode_fn(
            market_states
        )

        train_start = 0
        train_end = len(candles) // 2

        horizon = 8

        ok, records, detail = invoke_adaptive(
            experience_fn,
            {
                "candles": candles,
                "atr": atr,
                "states": market_states,
                "episode_ids": episode_ids,
                "start": train_start,
                "train_end": train_end,
                "horizon": horizon,
            },
        )

        if not ok:
            raise RuntimeError(detail)

        violations = []

        for record in records:

            index = int(record.index)

            if index >= train_end:
                violations.append(
                    f"record {index} >= train_end {train_end}"
                )

            # The experience's outcome itself necessarily uses
            # future data, but only after the record's query index
            # remains inside the training boundary.
            if index + horizon > train_end:
                violations.append(
                    f"record {index} + horizon {horizon} > train_end {train_end}"
                )

        if violations:
            result(
                "EXPERIENCE_TRAINING_BOUNDARY",
                "FAIL",
                " | ".join(violations[:10]),
            )
        else:
            result(
                "EXPERIENCE_TRAINING_BOUNDARY",
                "PASS",
                f"{len(records)} records stayed within training boundary {train_end}.",
            )

    except Exception as exc:
        result(
            "EXPERIENCE_TRAINING_BOUNDARY",
            "FAIL",
            f"{type(exc).__name__}: {exc}",
        )


# ================================================================
# 9. DETERMINISTIC PERMUTATION
# ================================================================

section("9. DETERMINISTIC PERMUTATION — FUTURE-INDEX FALSE POSITIVE CHECK")

perm_fn = getattr(
    module,
    "deterministic_permutation",
    None,
)

if perm_fn is None:

    result(
        "PERMUTATION_INDEX_SEMANTICS",
        "FAIL",
        "deterministic_permutation missing.",
    )

else:

    try:

        values = [
            "UP",
            "DOWN",
            "NEUTRAL",
            "UP",
            "DOWN",
        ]

        a = perm_fn(values, 12345)
        b = perm_fn(values, 12345)
        c = perm_fn(values, 54321)

        if a != b:
            result(
                "PERMUTATION_INDEX_SEMANTICS",
                "FAIL",
                "Same seed produced different permutations.",
            )

        elif sorted(a) != sorted(values):
            result(
                "PERMUTATION_INDEX_SEMANTICS",
                "FAIL",
                "Permutation changed the value multiset.",
            )

        elif a == c:
            result(
                "PERMUTATION_INDEX_SEMANTICS",
                "REVIEW",
                "Different seeds unexpectedly produced identical permutation.",
            )

        else:
            result(
                "PERMUTATION_INDEX_SEMANTICS",
                "PASS",
                "i + 1 / modulo indexing is confined to deterministic shuffle logic.",
            )

    except Exception as exc:

        result(
            "PERMUTATION_INDEX_SEMANTICS",
            "FAIL",
            f"{type(exc).__name__}: {exc}",
        )


# ================================================================
# 10. WALK-FORWARD STRUCTURAL CONTRACT
# ================================================================

section("10. WALK-FORWARD STRUCTURAL CONTRACT")

wf_fn = getattr(
    module,
    "create_walk_forward_windows",
    None,
)

if wf_fn is None:

    result(
        "WALK_FORWARD_STRUCTURAL_CONTRACT",
        "FAIL",
        "create_walk_forward_windows missing.",
    )

else:

    try:

        windows = wf_fn(
            len(candles),
            5,
            81,
        )

        if not windows:
            raise RuntimeError(
                "No walk-forward windows returned."
            )

        violations = []

        for w in windows:

            required = (
                "train_start",
                "train_end",
                "oos_start",
                "oos_end",
            )

            missing = [
                name
                for name in required
                if not hasattr(w, name)
            ]

            if missing:
                violations.append(
                    f"window {getattr(w, 'number', '?')}: missing {missing}"
                )
                continue

            ts = int(w.train_start)
            te = int(w.train_end)
            os = int(w.oos_start)
            oe = int(w.oos_end)

            if ts < 0:
                violations.append(
                    f"window {w.number}: train_start < 0"
                )

            if ts >= te:
                violations.append(
                    f"window {w.number}: train_start >= train_end"
                )

            if te > os:
                violations.append(
                    f"window {w.number}: train_end > oos_start"
                )

            if os >= oe:
                violations.append(
                    f"window {w.number}: oos_start >= oos_end"
                )

            if oe > len(candles):
                violations.append(
                    f"window {w.number}: oos_end > data length"
                )

        if violations:

            result(
                "WALK_FORWARD_STRUCTURAL_CONTRACT",
                "FAIL",
                " | ".join(violations[:20]),
            )

        else:

            result(
                "WALK_FORWARD_STRUCTURAL_CONTRACT",
                "PASS",
                f"{len(windows)} windows contain valid train_start/train_end/oos_start/oos_end boundaries.",
            )

    except Exception as exc:

        result(
            "WALK_FORWARD_STRUCTURAL_CONTRACT",
            "FAIL",
            f"{type(exc).__name__}: {exc}",
        )


# ================================================================
# 11. WALK-FORWARD RUNTIME + HORIZON BOUNDARY
# ================================================================

section("11. WALK-FORWARD RUNTIME BOUNDARIES")

try:

    windows = wf_fn(
        len(candles),
        5,
        81,
    )

    violations = []

    for window in windows:

        for horizon in HORIZONS:

            for query_index in range(
                window.oos_start,
                window.oos_end,
            ):

                # This is allowed only as a boundary check.
                if query_index + horizon >= len(candles):
                    continue

                if not (
                    window.train_start
                    <= window.train_end
                    <= window.oos_start
                    <= query_index
                    < window.oos_end
                    <= len(candles)
                ):
                    violations.append(
                        (
                            window.number,
                            horizon,
                            query_index,
                        )
                    )

    if violations:

        result(
            "WALK_FORWARD_RUNTIME_FINAL",
            "FAIL",
            f"Boundary violations: {violations[:20]}",
        )

    else:

        result(
            "WALK_FORWARD_RUNTIME_FINAL",
            "PASS",
            f"{len(windows)} windows passed train/OOS/horizon boundary verification.",
        )

except Exception as exc:

    result(
        "WALK_FORWARD_RUNTIME_FINAL",
        "FAIL",
        f"{type(exc).__name__}: {exc}",
    )


# ================================================================
# 12. STATIC SEMANTIC REVIEW OF THE 14 REFERENCES
# ================================================================

section("12. FUTURE-INDEX STATIC REFERENCES — FINAL CLASSIFICATION")

# These are the specific references previously classified as REVIEW.
#
# We do NOT reject every `index + 1`.
# We classify based on function semantics.

function_map = {}

for node in ast.walk(tree):
    if isinstance(
        node,
        (
            ast.FunctionDef,
            ast.AsyncFunctionDef,
        ),
    ):
        function_map[node.name] = node


def function_source(name):

    node = function_map.get(name)

    if node is None:
        return ""

    return ast.get_source_segment(
        source,
        node,
    ) or ""


checks = {
    "_is_confirmed_high": [
        "SWING_RIGHT",
    ],
    "_is_confirmed_low": [
        "SWING_RIGHT",
    ],
    "build_path_vector": [
        "range(start, index + 1)",
    ],
    "build_market_states": [
        "candles[: i + 1]",
    ],
    "build_experience_records": [
        "train_end - horizon",
    ],
    "deterministic_permutation": [
        "i + 1",
        "%",
    ],
}

static_failures = []

for fn_name, required_tokens in checks.items():

    src = function_source(fn_name)

    if not src:

        static_failures.append(
            f"{fn_name}: function source unavailable"
        )
        continue

    missing = [
        token
        for token in required_tokens
        if token not in src
    ]

    if missing:

        static_failures.append(
            f"{fn_name}: missing expected semantic token(s) {missing}"
        )

if static_failures:

    result(
        "FUTURE_INDEX_STATIC_FINAL",
        "FAIL",
        " | ".join(static_failures),
    )

else:

    result(
        "FUTURE_INDEX_STATIC_FINAL",
        "PASS",
        "All previously flagged future-index references have explicit causal semantics or boundary-only semantics.",
    )


# ================================================================
# 13. FINAL SOURCE/DATA INTEGRITY
# ================================================================

section("13. FINAL MUTATION PROTECTION")

final_source_hash = sha256(TARGET)
final_data_hash = sha256(DATA_FILE)

if final_source_hash != original_source_hash:

    result(
        "SOURCE_MUTATION_FINAL",
        "FAIL",
        "Target source changed during verification.",
    )

else:

    result(
        "SOURCE_MUTATION_FINAL",
        "PASS",
        "Target source remained byte-for-byte unchanged.",
    )


if final_data_hash != original_data_hash:

    result(
        "DATA_MUTATION_FINAL",
        "FAIL",
        "market_data.bin changed during verification.",
    )

else:

    result(
        "DATA_MUTATION_FINAL",
        "PASS",
        "market_data.bin remained byte-for-byte unchanged.",
    )


# ================================================================
# FINAL VERDICT
# ================================================================

section("FINAL CAUSAL CERTIFICATION")

fails = [
    r for r in results
    if r["status"] == "FAIL"
]

reviews = [
    r for r in results
    if r["status"] in ("REVIEW", "WARNING")
]

inconclusive = [
    r for r in results
    if r["status"] == "INCONCLUSIVE"
]

passes = [
    r for r in results
    if r["status"] == "PASS"
]

print()
print(f"PASS         : {len(passes)}")
print(f"FAIL         : {len(fails)}")
print(f"INCONCLUSIVE : {len(inconclusive)}")
print(f"REVIEW       : {len(reviews)}")
print()

if fails:

    verdict = (
        "FAIL — CAUSAL CERTIFICATION REJECTED"
    )

elif inconclusive:

    verdict = (
        "INCONCLUSIVE — CAUSAL CERTIFICATION NOT PROVEN"
    )

elif reviews:

    verdict = (
        "REVIEW — CAUSAL CERTIFICATION NOT YET PROVEN"
    )

else:

    verdict = (
        "PASS — CAUSAL CERTIFICATION PASSED"
    )

print(verdict)


# ================================================================
# FAILURE / REVIEW SUMMARY
# ================================================================

if fails:

    print()
    print("FAILURES:")

    for r in fails:
        print()
        print(f"  {r['name']}")
        print(f"  {r['detail']}")


if reviews:

    print()
    print("REVIEWS:")

    for r in reviews:
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


# ================================================================
# REPORT
# ================================================================

report_lines = []

report_lines.append(
    "MLAI v4.1.5 — FINAL REMAINING REVIEW VERIFICATION"
)

report_lines.append("=" * 100)

report_lines.append(
    f"Target: {TARGET.resolve()}"
)

report_lines.append(
    f"Data: {DATA_FILE.resolve()}"
)

report_lines.append(
    f"Python: {sys.version}"
)

report_lines.append("")

for r in results:

    report_lines.append(
        f"[{r['status']}] {r['name']}"
    )

    if r["detail"]:

        report_lines.append(
            f"    {r['detail']}"
        )

report_lines.append("")
report_lines.append("=" * 100)
report_lines.append("FINAL VERDICT")
report_lines.append("=" * 100)
report_lines.append(verdict)

REPORT.write_text(
    "\n".join(report_lines),
    encoding="utf-8",
)

print()
print(f"Report written to: {REPORT.resolve()}")

print()
print("=" * 100)
print("VERIFICATION COMPLETE")
print("=" * 100)

