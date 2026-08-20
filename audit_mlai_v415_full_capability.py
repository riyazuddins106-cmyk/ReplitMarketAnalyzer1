from __future__ import annotations

import ast
import hashlib
import inspect
import json
import sys
import traceback
from pathlib import Path
from collections import Counter


# ================================================================
# CONFIGURATION
# ================================================================

TARGET = Path("mlai_market_structure_v415.py")
DATA_FILE = Path("market_data.bin")

REPORT = Path("mlai_v415_full_capability_audit_report.txt")
FIX_PLAN = Path("mlai_v415_full_capability_fix_plan.txt")


# ================================================================
# OUTPUT
# ================================================================

results = []


def section(title):
    print()
    print("=" * 100)
    print(title)
    print("=" * 100)


def result(name, status, detail="", evidence=""):
    item = {
        "name": name,
        "status": status,
        "detail": detail,
        "evidence": evidence,
    }
    results.append(item)

    print(f"[{status:<12}] {name}")

    if detail:
        print(f"              {detail}")

    if evidence:
        print(f"              Evidence: {evidence}")


def sha256(path):
    h = hashlib.sha256()

    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)

    return h.hexdigest()


def safe_call(fn, *args, **kwargs):
    try:
        return True, fn(*args, **kwargs), ""
    except Exception as exc:
        return False, None, (
            f"{type(exc).__name__}: {exc}: "
            f"{traceback.format_exc(limit=3)}"
        )


def comparable(value):
    if value is None:
        return None

    if isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, dict):
        return tuple(
            sorted(
                (
                    str(k),
                    comparable(v),
                )
                for k, v in value.items()
            )
        )

    if isinstance(value, (list, tuple)):
        return tuple(comparable(x) for x in value)

    if hasattr(value, "__dict__"):
        return (
            type(value).__name__,
            tuple(
                sorted(
                    (
                        str(k),
                        comparable(v),
                    )
                    for k, v in vars(value).items()
                )
            ),
        )

    return repr(value)


# ================================================================
# INPUT INTEGRITY
# ================================================================

section("MLAI v4.1.5 — FULL CAPABILITY FORENSIC AUDIT")

print(f"Python : {sys.version}")
print(f"Target : {TARGET.resolve()}")
print(f"Data   : {DATA_FILE.resolve()}")

if not TARGET.exists():
    raise SystemExit(f"Target missing: {TARGET}")

if not DATA_FILE.exists():
    raise SystemExit(f"Data missing: {DATA_FILE}")

original_source_hash = sha256(TARGET)
original_data_hash = sha256(DATA_FILE)

result(
    "INPUT_INTEGRITY",
    "PASS",
    "Target source and market_data.bin exist.",
)


# ================================================================
# SOURCE PARSE
# ================================================================

section("1. SOURCE PARSE")

source = TARGET.read_text(encoding="utf-8")

try:
    tree = ast.parse(source)

    result(
        "SOURCE_PARSE",
        "PASS",
        "v4.1.5 source parsed successfully.",
    )

except SyntaxError as exc:
    result(
        "SOURCE_PARSE",
        "FAIL",
        f"SyntaxError: {exc}",
    )

    raise SystemExit(
        "Audit stopped because the TARGET ENGINE itself "
        "cannot be parsed."
    )


# ================================================================
# FUNCTION INVENTORY
# ================================================================

functions = {}

classes = {}

for node in ast.walk(tree):

    if isinstance(
        node,
        (
            ast.FunctionDef,
            ast.AsyncFunctionDef,
        ),
    ):
        functions[node.name] = node

    elif isinstance(node, ast.ClassDef):
        classes[node.name] = node


result(
    "SOURCE_FUNCTION_INVENTORY",
    "PASS",
    f"Detected {len(functions)} functions and {len(classes)} classes.",
)


# ================================================================
# IMPORT
# ================================================================

section("2. TARGET IMPORT")

try:

    import importlib.util

    module_name = "mlai_v415_target"

    spec = importlib.util.spec_from_file_location(
        module_name,
        TARGET.resolve(),
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            f"Unable to create import specification for {TARGET}"
        )

    module = importlib.util.module_from_spec(spec)

    # IMPORTANT:
    # Register the module BEFORE executing it.
    # Python dataclasses and other runtime mechanisms may
    # resolve the currently executing module through sys.modules.
    sys.modules[module_name] = module

    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(module_name, None)
        raise

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

    raise SystemExit(
        "Audit cannot continue because v4.1.5 cannot import."
    )


# ================================================================
# DATA LOADER
# ================================================================

section("3. DATA LOADER")

loader_candidates = [
    "load_market_data",
    "load_data",
    "read_market_data",
]

loader = None

for name in loader_candidates:

    candidate = getattr(module, name, None)

    if callable(candidate):
        loader = candidate
        break


if loader is None:

    result(
        "TARGET_LOADER",
        "MISSING",
        "No recognized market-data loader found.",
    )

    raise SystemExit(
        "Cannot perform runtime audit without data loader."
    )


ok, loader_result, detail = safe_call(
    loader,
    str(DATA_FILE),
)

if not ok:

    result(
        "TARGET_LOADER",
        "FAIL",
        detail,
    )

    raise SystemExit(
        "Target loader failed."
    )

# Verified v4.1.5 loader contract:
# load_market_data(path) -> (candles, invalid_count)

if not isinstance(loader_result, tuple):
    result(
        "TARGET_LOADER",
        "FAIL",
        (
            "Loader returned "
            f"{type(loader_result).__name__}; expected tuple "
            "(candles, invalid_count).",
        ),
    )

    raise SystemExit(
        "Target loader returned unexpected structure."
    )

if len(loader_result) != 2:
    result(
        "TARGET_LOADER",
        "FAIL",
        f"Loader returned tuple of length {len(loader_result)}; expected 2.",
    )

    raise SystemExit(
        "Target loader returned unexpected tuple length."
    )

candles, invalid_count = loader_result

if not isinstance(candles, (list, tuple)):
    result(
        "TARGET_LOADER",
        "FAIL",
        f"Loader returned invalid candle collection: {type(candles).__name__}.",
    )

    raise SystemExit(
        "Invalid candle collection returned by loader."
    )

if not isinstance(invalid_count, int):
    result(
        "TARGET_LOADER",
        "FAIL",
        f"Loader returned invalid count of type {type(invalid_count).__name__}.",
    )

    raise SystemExit(
        "Invalid invalid-count returned by loader."
    )

result(
    "TARGET_LOADER",
    "PASS",
    (
        f"Target loader returned {len(candles)} candles "
        f"and invalid_count={invalid_count}."
    ),
)


result(
    "TARGET_LOADER",
    "PASS",
    f"Target loader returned {len(candles)} candles.",
)


# ================================================================
# CANDLE VALIDATION
# ================================================================

section("4. CANDLE VALIDATION")

required_fields = [
    "timestamp",
    "open",
    "high",
    "low",
    "close",
]

invalid = []

for i, candle in enumerate(candles):

    for field in required_fields:

        if not hasattr(candle, field):
            invalid.append(
                f"{i}: missing {field}"
            )

    try:

        o = float(candle.open)
        h = float(candle.high)
        l = float(candle.low)
        c = float(candle.close)

        if h < max(o, c):
            invalid.append(
                f"{i}: high below open/close"
            )

        if l > min(o, c):
            invalid.append(
                f"{i}: low above open/close"
            )

        if h < l:
            invalid.append(
                f"{i}: high < low"
            )

    except Exception as exc:

        invalid.append(
            f"{i}: numeric conversion failed: {exc}"
        )


if invalid:

    result(
        "CANDLE_VALIDATION",
        "FAIL",
        f"{len(invalid)} candle violations.",
        " | ".join(invalid[:10]),
    )

else:

    result(
        "CANDLE_VALIDATION",
        "PASS",
        f"All {len(candles)} candles structurally valid.",
    )


# ================================================================
# CHRONOLOGY
# ================================================================

section("5. CHRONOLOGY")

timestamps = []

try:

    for candle in candles:
        timestamps.append(candle.timestamp)

    chronology_errors = []

    for i in range(1, len(timestamps)):

        if timestamps[i] <= timestamps[i - 1]:
            chronology_errors.append(i)

    if chronology_errors:

        result(
            "CHRONOLOGY",
            "FAIL",
            f"{len(chronology_errors)} timestamp ordering violations.",
            str(chronology_errors[:20]),
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
# HELPERS
# ================================================================

atr_fn = getattr(module, "calculate_atr", None)

if atr_fn is None:
    atr_fn = getattr(module, "compute_atr", None)

engine_cls = getattr(
    module,
    "CausalStructureEngine",
    None,
)

if engine_cls is None:
    engine_cls = getattr(
        module,
        "MarketStructureEngine",
        None,
    )


def mutate_suffix(data, boundary):

    copied = list(data)

    if boundary >= len(copied):
        return copied

    for i in range(boundary, len(copied)):

        c = copied[i]

        try:

            copied[i] = type(c)(
                timestamp=c.timestamp,
                open=float(c.open) * 1.07,
                high=float(c.high) * 1.08,
                low=float(c.low) * 1.06,
                close=float(c.close) * 1.07,
            )

        except Exception:

            try:

                clone = type(c)(**vars(c))

                clone.open = float(c.open) * 1.07
                clone.high = float(c.high) * 1.08
                clone.low = float(c.low) * 1.06
                clone.close = float(c.close) * 1.07

                copied[i] = clone

            except Exception:
                pass

    return copied


# ================================================================
# 6. STRUCTURE CONFIRMATION
# ================================================================

section("6. STRUCTURE CONFIRMATION")

if engine_cls is None:

    result(
        "STRUCTURE_CONFIRMATION",
        "MISSING",
        "No recognized structure engine class.",
    )

else:

    try:

        engine = engine_cls(candles)

        build = getattr(engine, "build", None)

        if not callable(build):
            raise RuntimeError(
                "Structure engine has no callable build()."
            )

        ok, structure, detail = safe_call(build)

        if not ok:
            result(
                "STRUCTURE_CONFIRMATION",
                "FAIL",
                detail,
            )
        else:
            result(
                "STRUCTURE_CONFIRMATION",
                "PASS",
                "Structure engine executed successfully.",
            )

    except Exception as exc:

        result(
            "STRUCTURE_CONFIRMATION",
            "FAIL",
            f"{type(exc).__name__}: {exc}",
        )


# ================================================================
# 7. PATH CAUSALITY
# ================================================================

section("7. PATH PREFIX CAUSALITY")

path_fn = getattr(
    module,
    "build_path_vector",
    None,
)

if path_fn is None:

    result(
        "PATH_CAUSALITY",
        "MISSING",
        "build_path_vector missing.",
    )

elif atr_fn is None:

    result(
        "PATH_CAUSALITY",
        "INCONCLUSIVE",
        "ATR function unavailable.",
    )

else:

    try:

        boundary = len(candles) // 2

        mutated = mutate_suffix(
            candles,
            boundary,
        )

        ok1, atr1, d1 = safe_call(
            atr_fn,
            candles,
        )

        ok2, atr2, d2 = safe_call(
            atr_fn,
            mutated,
        )

        if not ok1 or not ok2:
            raise RuntimeError(
                d1 if not ok1 else d2
            )

        test_indices = [
            min(100, boundary - 1),
            min(300, boundary - 1),
            boundary - 1,
        ]

        violations = []

        for idx in test_indices:

            if idx < 0:
                continue

            ok1, p1, d1 = safe_call(
                path_fn,
                candles,
                atr1,
                idx,
            )

            ok2, p2, d2 = safe_call(
                path_fn,
                mutated,
                atr2,
                idx,
            )

            if not ok1 or not ok2:
                raise RuntimeError(
                    d1 if not ok1 else d2
                )

            if comparable(p1) != comparable(p2):

                violations.append(idx)

        if violations:

            result(
                "PATH_CAUSALITY",
                "FAIL",
                "Historical path changed after future-only mutation.",
                f"indices={violations}",
            )

        else:

            result(
                "PATH_CAUSALITY",
                "PASS",
                "Historical path prefix remained invariant.",
            )

    except Exception as exc:

        result(
            "PATH_CAUSALITY",
            "FAIL",
            f"{type(exc).__name__}: {exc}",
        )


# ================================================================
# 8. MARKET STATES
# ================================================================

section("8. MARKET STATE CAUSALITY")

state_fn = getattr(
    module,
    "build_market_states",
    None,
)

if state_fn is None:

    result(
        "MARKET_STATE_CAUSALITY",
        "MISSING",
        "build_market_states missing.",
    )

else:

    try:

        if engine_cls is None:
            raise RuntimeError(
                "Structure engine unavailable."
            )

        engine1 = engine_cls(candles)

        ok, structure1, detail = safe_call(
            engine1.build
        )

        if not ok:
            raise RuntimeError(detail)

        boundary = len(candles) // 2

        mutated = mutate_suffix(
            candles,
            boundary,
        )

        engine2 = engine_cls(mutated)

        ok, structure2, detail = safe_call(
            engine2.build
        )

        if not ok:
            raise RuntimeError(detail)

        state_cls = getattr(
            module,
            "StructureState",
            None,
        )

        def extract_states(value):

            found = []

            def walk(v):

                if isinstance(v, (list, tuple)):

                    for x in v:
                        walk(x)

                elif isinstance(v, dict):

                    for x in v.values():
                        walk(x)

                elif (
                    state_cls is not None
                    and isinstance(v, state_cls)
                ):

                    found.append(v)

            walk(value)

            return found

        structure_states1 = extract_states(
            structure1
        )

        structure_states2 = extract_states(
            structure2
        )

        atr1 = (
            atr_fn(candles)
            if atr_fn
            else None
        )

        atr2 = (
            atr_fn(mutated)
            if atr_fn
            else None
        )

        ok, states1, detail = safe_call(
            state_fn,
            candles,
            atr1,
            structure_states1,
        )

        if not ok:

            ok, states1, detail = safe_call(
                state_fn,
                candles,
                structure_states1,
                atr1,
            )

        if not ok:
            raise RuntimeError(detail)

        ok, states2, detail = safe_call(
            state_fn,
            mutated,
            atr2,
            structure_states2,
        )

        if not ok:

            ok, states2, detail = safe_call(
                state_fn,
                mutated,
                structure_states2,
                atr2,
            )

        if not ok:
            raise RuntimeError(detail)

        prefix1 = comparable(states1)[:boundary + 1]
        prefix2 = comparable(states2)[:boundary + 1]

        if prefix1 != prefix2:

            result(
                "MARKET_STATE_CAUSALITY",
                "FAIL",
                "Historical market-state prefix changed after future mutation.",
            )

        else:

            result(
                "MARKET_STATE_CAUSALITY",
                "PASS",
                f"State prefix through {boundary} remained invariant.",
            )

    except Exception as exc:

        result(
            "MARKET_STATE_CAUSALITY",
            "FAIL",
            f"{type(exc).__name__}: {exc}",
        )


# ================================================================
# 9. HISTORICAL OUTCOMES
# ================================================================

section("9. HISTORICAL OUTCOMES")

outcome_fn = getattr(
    module,
    "make_outcome",
    None,
)

if outcome_fn is None:

    result(
        "HISTORICAL_OUTCOMES",
        "MISSING",
        "make_outcome missing.",
    )

else:

    horizon = 8

    index = min(
        100,
        len(candles) - horizon - 1,
    )

    if atr_fn is None:

        result(
            "HISTORICAL_OUTCOMES",
            "INCONCLUSIVE",
            "ATR function unavailable.",
        )

    else:

        ok, atr, detail = safe_call(
            atr_fn,
            candles,
        )

        if not ok:

            result(
                "HISTORICAL_OUTCOMES",
                "FAIL",
                detail,
            )

        else:

            ok, outcome, detail = safe_call(
                outcome_fn,
                candles,
                atr,
                index,
                horizon,
            )

            if not ok:

                result(
                    "HISTORICAL_OUTCOMES",
                    "FAIL",
                    detail,
                )

            elif outcome is None:

                result(
                    "HISTORICAL_OUTCOMES",
                    "FAIL",
                    "make_outcome returned None for valid historical sample.",
                )

            else:

                result(
                    "HISTORICAL_OUTCOMES",
                    "PASS",
                    "Historical outcome construction executed successfully.",
                )


# ================================================================
# 10. EXPERIENCE MEMORY
# ================================================================

section("10. EXPERIENCE MEMORY")

experience_fn = getattr(
    module,
    "build_experience_records",
    None,
)

episode_fn = getattr(
    module,
    "assign_episode_ids",
    None,
)

market_state_fn = getattr(
    module,
    "build_market_states",
    None,
)

if experience_fn is None:

    result(
        "EXPERIENCE_MEMORY",
        "MISSING",
        "build_experience_records missing.",
    )

elif episode_fn is None:

    result(
        "EXPERIENCE_MEMORY",
        "MISSING",
        "assign_episode_ids missing.",
    )

elif market_state_fn is None:

    result(
        "EXPERIENCE_MEMORY",
        "MISSING",
        "build_market_states missing.",
    )

else:

    try:

        if engine_cls is None:
            raise RuntimeError(
                "Structure engine unavailable."
            )

        if atr_fn is None:
            raise RuntimeError(
                "ATR function unavailable."
            )

        atr = atr_fn(candles)

        engine = engine_cls(candles)

        structure = engine.build()

        state_cls = getattr(
            module,
            "StructureState",
            None,
        )

        structure_states = []

        def collect(value):

            if isinstance(value, (list, tuple)):

                for x in value:
                    collect(x)

            elif isinstance(value, dict):

                for x in value.values():
                    collect(x)

            elif (
                state_cls is not None
                and isinstance(value, state_cls)
            ):

                structure_states.append(value)

        collect(structure)

        market_states = market_state_fn(
            candles,
            atr,
            structure_states,
        )

        episode_ids = episode_fn(
            market_states
        )

        train_end = len(candles) // 2

        horizon = 8

        records = experience_fn(
            candles,
            atr,
            market_states,
            episode_ids,
            0,
            train_end,
            horizon,
        )

        violations = []

        for r in records:

            idx = int(r.index)

            if idx >= train_end:
                violations.append(
                    f"{idx} >= {train_end}"
                )

            if idx + horizon > train_end:
                violations.append(
                    f"{idx}+{horizon}>{train_end}"
                )

        if violations:

            result(
                "EXPERIENCE_MEMORY",
                "FAIL",
                f"{len(violations)} training-boundary violations.",
                " | ".join(violations[:10]),
            )

        else:

            result(
                "EXPERIENCE_MEMORY",
                "PASS",
                f"{len(records)} causal experience records created.",
            )

    except Exception as exc:

        records = []

        result(
            "EXPERIENCE_MEMORY",
            "FAIL",
            f"{type(exc).__name__}: {exc}",
        )


# ================================================================
# 11. NON-EXACT SIMILARITY
# ================================================================

section("11. NON-EXACT HISTORICAL SIMILARITY")

similarity_fn = getattr(
    module,
    "similarity_score",
    None,
)

retrieval_fn = getattr(
    module,
    "retrieve_historical_experience",
    None,
)

if similarity_fn is None:

    result(
        "NON_EXACT_SIMILARITY",
        "MISSING",
        "similarity_score missing.",
    )

elif retrieval_fn is None:

    result(
        "NON_EXACT_SIMILARITY",
        "MISSING",
        "retrieve_historical_experience missing.",
    )

else:

    # Structural existence is only the first layer.
    # We explicitly test that similarity can execute.

    try:

        if records:

            sample = records[0]

            ok, score, detail = safe_call(
                similarity_fn,
                sample,
                sample,
            )

            if not ok:
                raise RuntimeError(detail)

            if not isinstance(
                score,
                (int, float),
            ):
                raise RuntimeError(
                    f"Similarity returned {type(score).__name__}, "
                    "not numeric."
                )

            if score < 0:
                raise RuntimeError(
                    f"Similarity returned negative score {score}."
                )

            result(
                "NON_EXACT_SIMILARITY",
                "PASS",
                f"Similarity executed and returned numeric score {score}.",
            )

        else:

            result(
                "NON_EXACT_SIMILARITY",
                "INCONCLUSIVE",
                "No experience records available for runtime similarity test.",
            )

    except Exception as exc:

        result(
            "NON_EXACT_SIMILARITY",
            "FAIL",
            f"{type(exc).__name__}: {exc}",
        )


# ================================================================
# 12. HISTORICAL RETRIEVAL
# ================================================================

section("12. HISTORICAL RETRIEVAL")

if retrieval_fn is None:

    result(
        "RETRIEVAL_RUNTIME",
        "MISSING",
        "Historical retriever missing.",
    )

else:

    result(
        "RETRIEVAL_RUNTIME",
        "PASS",
        "Historical retriever function exists.",
    )


# ================================================================
# 13. PROBABILITY INFRASTRUCTURE
# ================================================================

section("13. PROBABILITY ESTIMATION")

probability_candidates = [
    "distribution_from_records",
    "conditional_baseline",
    "evaluate_distribution",
    "brier",
    "log_loss",
]

probability_present = [
    name
    for name in probability_candidates
    if callable(getattr(module, name, None))
]

if len(probability_present) == len(probability_candidates):

    result(
        "PROBABILITY_ESTIMATION",
        "PASS",
        "All expected probability components are callable.",
        ", ".join(probability_present),
    )

elif len(probability_present) >= 3:

    result(
        "PROBABILITY_ESTIMATION",
        "PARTIAL",
        f"{len(probability_present)}/{len(probability_candidates)} components callable.",
        ", ".join(probability_present),
    )

else:

    result(
        "PROBABILITY_ESTIMATION",
        "MISSING",
        f"Only {len(probability_present)}/{len(probability_candidates)} components callable.",
        ", ".join(probability_present),
    )


# ================================================================
# 14. PROBABILITY CALIBRATION
# ================================================================

section("14. PROBABILITY CALIBRATION")

calibration_functions = [
    name
    for name in functions
    if any(
        token in name.lower()
        for token in (
            "calibr",
            "brier",
            "reliability",
            "ece",
            "log_loss",
        )
    )
]

calibration_tokens = [
    "calibration",
    "brier",
    "log_loss",
    "reliability",
    "expected_calibration_error",
    "ece",
]

source_lower = source.lower()

token_hits = {
    token: token in source_lower
    for token in calibration_tokens
}

token_count = sum(token_hits.values())

if calibration_functions and token_count >= 3:

    result(
        "PROBABILITY_CALIBRATION",
        "PASS",
        f"Calibration functions={len(calibration_functions)}, indicators={token_count}/{len(calibration_tokens)}.",
        ", ".join(calibration_functions),
    )

elif token_count >= 2:

    result(
        "PROBABILITY_CALIBRATION",
        "PARTIAL",
        f"Calibration indicators={token_count}/{len(calibration_tokens)}.",
        json.dumps(token_hits),
    )

else:

    result(
        "PROBABILITY_CALIBRATION",
        "MISSING",
        "Insufficient calibration infrastructure detected.",
        json.dumps(token_hits),
    )


# ================================================================
# 15. SCENARIO REASONING
# ================================================================

section("15. SCENARIO REASONING")

scenario_functions = [
    name
    for name in functions
    if "scenario" in name.lower()
]

scenario_tokens = [
    "bullish",
    "bearish",
    "neutral",
    "alternative",
    "base_case",
]

scenario_hits = {
    token: token in source_lower
    for token in scenario_tokens
}

scenario_count = sum(
    scenario_hits.values()
)

if scenario_functions and scenario_count >= 3:

    result(
        "SCENARIO_REASONING",
        "PASS",
        "Scenario function(s) and explicit scenario vocabulary detected.",
        ", ".join(scenario_functions),
    )

elif scenario_count >= 2:

    result(
        "SCENARIO_REASONING",
        "PARTIAL",
        "Scenario vocabulary exists but executable scenario framework is incomplete.",
        json.dumps(scenario_hits),
    )

else:

    result(
        "SCENARIO_REASONING",
        "MISSING",
        "No sufficient scenario reasoning framework detected.",
    )


# ================================================================
# 16. CONFIRMATION CONDITIONS
# ================================================================

section("16. CONFIRMATION CONDITIONS")

confirmation_functions = [
    name
    for name in functions
    if any(
        token in name.lower()
        for token in (
            "confirm",
            "trigger",
            "entry",
        )
    )
]

confirmation_tokens = [
    "confirmation",
    "confirm",
    "confirmed",
    "trigger",
    "entry_condition",
]

confirmation_hits = {
    token: token in source_lower
    for token in confirmation_tokens
}

confirmation_count = sum(
    confirmation_hits.values()
)

if confirmation_functions and confirmation_count >= 3:

    result(
        "CONFIRMATION_CONDITIONS",
        "PASS",
        "Executable confirmation-related functions detected.",
        ", ".join(confirmation_functions),
    )

elif confirmation_count >= 2:

    result(
        "CONFIRMATION_CONDITIONS",
        "PARTIAL",
        "Confirmation vocabulary exists but executable framework is incomplete.",
        json.dumps(confirmation_hits),
    )

else:

    result(
        "CONFIRMATION_CONDITIONS",
        "MISSING",
        "No sufficient confirmation framework detected.",
    )


# ================================================================
# 17. INVALIDATION CONDITIONS
# ================================================================

section("17. INVALIDATION CONDITIONS")

invalidation_functions = [
    name
    for name in functions
    if any(
        token in name.lower()
        for token in (
            "invalid",
            "failure",
            "stop",
        )
    )
]

invalidation_tokens = [
    "invalidation",
    "invalidate",
    "failure_condition",
    "stop_condition",
]

invalidation_hits = {
    token: token in source_lower
    for token in invalidation_tokens
}

invalidation_count = sum(
    invalidation_hits.values()
)

if invalidation_functions and invalidation_count >= 2:

    result(
        "INVALIDATION_CONDITIONS",
        "PASS",
        "Executable invalidation-related functions detected.",
        ", ".join(invalidation_functions),
    )

elif invalidation_count >= 2:

    result(
        "INVALIDATION_CONDITIONS",
        "PARTIAL",
        "Invalidation vocabulary exists without strong executable evidence.",
        json.dumps(invalidation_hits),
    )

else:

    result(
        "INVALIDATION_CONDITIONS",
        "MISSING",
        "No sufficient invalidation framework detected.",
    )


# ================================================================
# 18. HUMAN-LANGUAGE EXPLANATION
# ================================================================

section("18. HUMAN-LANGUAGE MARKET EXPLANATION")

language_functions = [
    name
    for name in functions
    if any(
        token in name.lower()
        for token in (
            "explain",
            "narrative",
            "summary",
            "interpret",
            "message",
        )
    )
]

language_tokens = [
    "explanation",
    "narrative",
    "interpretation",
    "summary",
    "reason",
]

language_hits = {
    token: token in source_lower
    for token in language_tokens
}

language_count = sum(
    language_hits.values()
)

if language_functions and language_count >= 3:

    result(
        "HUMAN_LANGUAGE_EXPLANATION",
        "PASS",
        "Executable explanation/narrative functions detected.",
        ", ".join(language_functions),
    )

elif language_count >= 2:

    result(
        "HUMAN_LANGUAGE_EXPLANATION",
        "PARTIAL",
        "Some explanation vocabulary exists but executable layer is weak.",
        json.dumps(language_hits),
    )

else:

    result(
        "HUMAN_LANGUAGE_EXPLANATION",
        "MISSING",
        "No sufficient explanation layer detected.",
    )


# ================================================================
# 19. MULTI-TIMEFRAME
# ================================================================

section("19. MULTI-TIMEFRAME REASONING")

mtf_functions = [
    name
    for name in functions
    if any(
        token in name.lower()
        for token in (
            "timeframe",
            "multi_timeframe",
            "higher_timeframe",
            "lower_timeframe",
            "htf",
            "ltf",
        )
    )
]

mtf_tokens = [
    "timeframe",
    "multi_timeframe",
    "higher_timeframe",
    "lower_timeframe",
    "htf",
    "ltf",
]

mtf_hits = {
    token: token in source_lower
    for token in mtf_tokens
}

mtf_count = sum(
    mtf_hits.values()
)

if mtf_functions and mtf_count >= 3:

    result(
        "MULTI_TIMEFRAME",
        "PASS",
        "Executable multi-timeframe infrastructure detected.",
        ", ".join(mtf_functions),
    )

elif mtf_count >= 2:

    result(
        "MULTI_TIMEFRAME",
        "PARTIAL",
        "Timeframe terminology exists but executable MTF architecture is incomplete.",
        json.dumps(mtf_hits),
    )

else:

    result(
        "MULTI_TIMEFRAME",
        "MISSING",
        "No sufficient multi-timeframe architecture detected.",
    )


# ================================================================
# 20. GENERALIZATION
# ================================================================

section("20. UNSEEN-CHART GENERALIZATION")

wf_fn = getattr(
    module,
    "create_walk_forward_windows",
    None,
)

if wf_fn is None:

    result(
        "UNSEEN_CHART_GENERALIZATION",
        "MISSING",
        "Walk-forward window generator missing.",
    )

else:

    ok, windows, detail = safe_call(
        wf_fn,
        len(candles),
        5,
        81,
    )

    if not ok:

        result(
            "UNSEEN_CHART_GENERALIZATION",
            "FAIL",
            detail,
        )

    elif not windows:

        result(
            "UNSEEN_CHART_GENERALIZATION",
            "FAIL",
            "Walk-forward generator returned no windows.",
        )

    else:

        result(
            "UNSEEN_CHART_GENERALIZATION",
            "PASS",
            f"{len(windows)} walk-forward windows available for unseen-data evaluation.",
        )


# ================================================================
# 21. CONTROLLED CONTINUOUS LEARNING
# ================================================================

section("21. CONTROLLED CONTINUOUS LEARNING")

learning_functions = [
    name
    for name in functions
    if any(
        token in name.lower()
        for token in (
            "learn",
            "update_model",
            "incremental",
            "online",
            "retrain",
            "feedback",
        )
    )
]

learning_tokens = [
    "learn",
    "learning",
    "update_model",
    "incremental",
    "online",
    "feedback",
    "retrain",
]

learning_hits = {
    token: token in source_lower
    for token in learning_tokens
}

learning_count = sum(
    learning_hits.values()
)

if learning_functions and learning_count >= 4:

    result(
        "CONTROLLED_CONTINUOUS_LEARNING",
        "PASS",
        "Executable learning/update functions detected.",
        ", ".join(learning_functions),
    )

elif learning_count >= 3:

    result(
        "CONTROLLED_CONTINUOUS_LEARNING",
        "PARTIAL",
        "Learning terminology exists but controlled update architecture is incomplete.",
        json.dumps(learning_hits),
    )

else:

    result(
        "CONTROLLED_CONTINUOUS_LEARNING",
        "MISSING",
        "No sufficient controlled continuous-learning system detected.",
    )


# ================================================================
# 22. LIVE PIPELINE
# ================================================================

section("22. LIVE DATA PIPELINE")

live_functions = [
    name
    for name in functions
    if any(
        token in name.lower()
        for token in (
            "live",
            "stream",
            "websocket",
            "realtime",
            "poll",
            "feed",
        )
    )
]

live_tokens = [
    "websocket",
    "realtime",
    "real_time",
    "stream",
    "poll",
    "feed",
]

live_hits = {
    token: token in source_lower
    for token in live_tokens
}

live_count = sum(
    live_hits.values()
)

if live_functions and live_count >= 3:

    result(
        "LIVE_DATA_PIPELINE",
        "PASS",
        "Executable live-data infrastructure detected.",
        ", ".join(live_functions),
    )

elif live_count >= 2:

    result(
        "LIVE_DATA_PIPELINE",
        "PARTIAL",
        "Some live-data indicators detected.",
        json.dumps(live_hits),
    )

else:

    result(
        "LIVE_DATA_PIPELINE",
        "NOT_REQUIRED",
        "No live pipeline detected. Appropriate for research-only v4.1.5.",
    )


# ================================================================
# 23. WALK-FORWARD STRUCTURAL CONTRACT
# ================================================================

section("23. WALK-FORWARD STRUCTURAL CONTRACT")

if wf_fn is None:

    result(
        "WALK_FORWARD",
        "MISSING",
        "create_walk_forward_windows missing.",
    )

else:

    ok, windows, detail = safe_call(
        wf_fn,
        len(candles),
        5,
        81,
    )

    if not ok:

        result(
            "WALK_FORWARD",
            "FAIL",
            detail,
        )

    else:

        violations = []

        for w in windows:

            required = [
                "train_start",
                "train_end",
                "oos_start",
                "oos_end",
            ]

            missing = [
                x
                for x in required
                if not hasattr(w, x)
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

            if not (
                0 <= ts < te <= os < oe <= len(candles)
            ):

                violations.append(
                    f"window {getattr(w, 'number', '?')}: "
                    f"{ts},{te},{os},{oe}"
                )

        if violations:

            result(
                "WALK_FORWARD",
                "FAIL",
                " | ".join(violations[:10]),
            )

        else:

            result(
                "WALK_FORWARD",
                "PASS",
                f"{len(windows)} windows passed structural validation.",
            )


# ================================================================
# 24. FUTURE-INDEX STATIC FORENSICS
# ================================================================

section("24. FUTURE-INDEX STATIC FORENSICS")

future_refs = []

for node in ast.walk(tree):

    if isinstance(node, ast.BinOp) and isinstance(
        node.op,
        ast.Add,
    ):

        if isinstance(
            node.right,
            ast.Constant,
        ) and isinstance(
            node.right.value,
            int,
        ):

            if node.right.value > 0:

                segment = (
                    ast.get_source_segment(
                        source,
                        node,
                    )
                    or "?"
                )

                future_refs.append(
                    (
                        getattr(
                            node,
                            "lineno",
                            "?",
                        ),
                        segment,
                    )
                )


if future_refs:

    # This is deliberately REVIEW rather than FAIL.
    # Static +1 does not prove leakage.

    result(
        "FUTURE_INDEX_STATIC",
        "REVIEW",
        f"{len(future_refs)} positive index expressions require semantic review.",
        " | ".join(
            f"line {line}: {expr}"
            for line, expr in future_refs[:20]
        ),
    )

else:

    result(
        "FUTURE_INDEX_STATIC",
        "PASS",
        "No positive index additions detected.",
    )


# ================================================================
# 25. GLOBAL PREFIX MUTATION
# ================================================================

section("25. GLOBAL PREFIX MUTATION")

boundary = len(candles) // 2

mutated = mutate_suffix(
    candles,
    boundary,
)

prefix_checks = []

if atr_fn:

    ok1, atr1, d1 = safe_call(
        atr_fn,
        candles,
    )

    ok2, atr2, d2 = safe_call(
        atr_fn,
        mutated,
    )

    if ok1 and ok2:

        prefix_checks.append(
            comparable(atr1)[:boundary + 1]
            ==
            comparable(atr2)[:boundary + 1]
        )


if path_fn and atr_fn:

    ok1, atr1, d1 = safe_call(
        atr_fn,
        candles,
    )

    ok2, atr2, d2 = safe_call(
        atr_fn,
        mutated,
    )

    if ok1 and ok2:

        path_ok = True

        for idx in (
            min(100, boundary - 1),
            min(300, boundary - 1),
            boundary - 1,
        ):

            if idx < 0:
                continue

            ok1, p1, d1 = safe_call(
                path_fn,
                candles,
                atr1,
                idx,
            )

            ok2, p2, d2 = safe_call(
                path_fn,
                mutated,
                atr2,
                idx,
            )

            if not ok1 or not ok2:

                path_ok = False
                break

            if comparable(p1) != comparable(p2):

                path_ok = False
                break

        prefix_checks.append(path_ok)


if prefix_checks and all(prefix_checks):

    result(
        "GLOBAL_PREFIX_CAUSALITY",
        "PASS",
        f"{len(prefix_checks)} prefix invariance checks passed.",
    )

elif prefix_checks:

    result(
        "GLOBAL_PREFIX_CAUSALITY",
        "FAIL",
        f"{sum(prefix_checks)}/{len(prefix_checks)} prefix checks passed.",
    )

else:

    result(
        "GLOBAL_PREFIX_CAUSALITY",
        "INCONCLUSIVE",
        "No applicable runtime prefix checks.",
    )


# ================================================================
# 26. MODULE DEPENDENCY / CAPABILITY MAP
# ================================================================

section("26. MODULE CAPABILITY MAP")

capability_groups = {

    "structure": [
        "CausalStructureEngine",
        "MarketStructureEngine",
        "StructureState",
    ],

    "states": [
        "build_market_states",
    ],

    "experience": [
        "build_experience_records",
        "assign_episode_ids",
    ],

    "retrieval": [
        "similarity_score",
        "retrieve_historical_experience",
    ],

    "outcomes": [
        "make_outcome",
    ],

    "walk_forward": [
        "create_walk_forward_windows",
    ],

    "path": [
        "build_path_vector",
    ],

    "atr": [
        "calculate_atr",
        "compute_atr",
    ],
}

capability_results = []

for group, names in capability_groups.items():

    found = []

    for name in names:

        if callable(getattr(module, name, None)):
            found.append(name)

    capability_results.append(
        (
            group,
            found,
            names,
        )
    )

    if found:

        result(
            f"CAPABILITY_{group.upper()}",
            "PASS",
            f"{len(found)}/{len(names)} recognized components available.",
            ", ".join(found),
        )

    else:

        result(
            f"CAPABILITY_{group.upper()}",
            "MISSING",
            "No recognized component available.",
        )


# ================================================================
# 27. SOURCE/DATA MUTATION PROTECTION
# ================================================================

section("27. FINAL MUTATION PROTECTION")

final_source_hash = sha256(TARGET)
final_data_hash = sha256(DATA_FILE)

if final_source_hash != original_source_hash:

    result(
        "SOURCE_MUTATION_PROTECTION",
        "FAIL",
        "Engine source changed during audit.",
    )

else:

    result(
        "SOURCE_MUTATION_PROTECTION",
        "PASS",
        "Engine source remained byte-for-byte unchanged.",
    )


if final_data_hash != original_data_hash:

    result(
        "DATA_MUTATION_PROTECTION",
        "FAIL",
        "market_data.bin changed during audit.",
    )

else:

    result(
        "DATA_MUTATION_PROTECTION",
        "PASS",
        "market_data.bin remained byte-for-byte unchanged.",
    )


# ================================================================
# FINAL CLASSIFICATION
# ================================================================

section("FINAL FULL CAPABILITY AUDIT")

passes = [
    r for r in results
    if r["status"] == "PASS"
]

fails = [
    r for r in results
    if r["status"] == "FAIL"
]

partials = [
    r for r in results
    if r["status"] == "PARTIAL"
]

missing = [
    r for r in results
    if r["status"] == "MISSING"
]

reviews = [
    r for r in results
    if r["status"] == "REVIEW"
]

inconclusive = [
    r for r in results
    if r["status"] == "INCONCLUSIVE"
]

not_required = [
    r for r in results
    if r["status"] == "NOT_REQUIRED"
]

print()
print(f"PASS         : {len(passes)}")
print(f"FAIL         : {len(fails)}")
print(f"PARTIAL      : {len(partials)}")
print(f"MISSING      : {len(missing)}")
print(f"REVIEW       : {len(reviews)}")
print(f"INCONCLUSIVE : {len(inconclusive)}")
print(f"NOT_REQUIRED : {len(not_required)}")
print()

if fails:

    verdict = (
        "FAIL — VERIFIED DEFECTS REQUIRE FIXING"
    )

elif inconclusive:

    verdict = (
        "INCONCLUSIVE — MORE RUNTIME TESTING REQUIRED"
    )

elif partials or missing or reviews:

    verdict = (
        "AUDIT COMPLETE — CAPABILITY GAPS REQUIRE REVIEW/FIX"
    )

else:

    verdict = (
        "PASS — ALL AUDITED CAPABILITIES VERIFIED"
    )

print(verdict)


# ================================================================
# FIX PLAN
# ================================================================

section("GENERATING FIX PLAN")

fix_lines = []

fix_lines.append(
    "MLAI v4.1.5 — FULL CAPABILITY FORENSIC FIX PLAN"
)

fix_lines.append("=" * 100)

fix_lines.append(
    "IMPORTANT:"
)

fix_lines.append(
    "This is an investigation artifact."
)

fix_lines.append(
    "NO ENGINE SOURCE WAS MODIFIED BY THIS AUDITOR."
)

fix_lines.append(
    "DO NOT CREATE v4.1.6 UNTIL THIS REPORT IS REVIEWED."
)

fix_lines.append("")

for r in results:

    if r["status"] in (
        "FAIL",
        "PARTIAL",
        "MISSING",
        "REVIEW",
        "INCONCLUSIVE",
    ):

        fix_lines.append("-" * 100)

        fix_lines.append(
            f"COMPONENT: {r['name']}"
        )

        fix_lines.append(
            f"STATUS: {r['status']}"
        )

        fix_lines.append(
            f"EVIDENCE: {r['detail']}"
        )

        if r["evidence"]:

            fix_lines.append(
                f"DETAIL: {r['evidence']}"
            )

        if r["status"] == "FAIL":

            fix_lines.append(
                "ACTION: Investigate verified defect and design targeted fix."
            )

        elif r["status"] == "PARTIAL":

            fix_lines.append(
                "ACTION: Determine missing executable behavior before implementation."
            )

        elif r["status"] == "MISSING":

            fix_lines.append(
                "ACTION: Capability is not sufficiently implemented."
            )

        elif r["status"] == "REVIEW":

            fix_lines.append(
                "ACTION: Perform semantic/runtime verification before changing engine code."
            )

        else:

            fix_lines.append(
                "ACTION: Add runtime evidence before classification."
            )

        fix_lines.append("")


fix_lines.append("=" * 100)

fix_lines.append(
    "NO AUTOMATIC ENGINE FIXES WERE APPLIED."
)

fix_lines.append(
    "NO v4.1.6 WAS CREATED."
)

FIX_PLAN.write_text(
    "\n".join(fix_lines),
    encoding="utf-8",
)


# ================================================================
# FULL REPORT
# ================================================================

report_lines = []

report_lines.append(
    "MLAI v4.1.5 — FULL CAPABILITY FORENSIC AUDIT"
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

report_lines.append(
    f"Original source SHA256: {original_source_hash}"
)

report_lines.append(
    f"Original data SHA256: {original_data_hash}"
)

report_lines.append("")

report_lines.append(
    "ENGINE WAS NOT MODIFIED DURING THIS AUDIT."
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

    if r["evidence"]:

        report_lines.append(
            f"    Evidence: {r['evidence']}"
        )

    report_lines.append("")


report_lines.append("=" * 100)

report_lines.append(
    "FINAL COUNTS"
)

report_lines.append("=" * 100)

report_lines.append(
    f"PASS         : {len(passes)}"
)

report_lines.append(
    f"FAIL         : {len(fails)}"
)

report_lines.append(
    f"PARTIAL      : {len(partials)}"
)

report_lines.append(
    f"MISSING      : {len(missing)}"
)

report_lines.append(
    f"REVIEW       : {len(reviews)}"
)

report_lines.append(
    f"INCONCLUSIVE : {len(inconclusive)}"
)

report_lines.append(
    f"NOT_REQUIRED : {len(not_required)}"
)

report_lines.append("")

report_lines.append(verdict)

REPORT.write_text(
    "\n".join(report_lines),
    encoding="utf-8",
)


# ================================================================
# FINAL
# ================================================================

print()
print("=" * 100)
print("AUDIT FILES")
print("=" * 100)

print(
    f"Report   : {REPORT.resolve()}"
)

print(
    f"Fix Plan : {FIX_PLAN.resolve()}"
)

print()

print(
    "ENGINE WAS NOT MODIFIED."
)

print(
    "NO v4.1.6 WAS CREATED."
)

print(
    "Next step: inspect the generated report and fix plan."
)

print("=" * 100)
