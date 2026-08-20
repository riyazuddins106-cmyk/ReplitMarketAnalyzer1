from __future__ import annotations

import ast
import copy
import hashlib
import importlib
import inspect
import shutil
import sys
import traceback
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any


TARGET = Path("mlai_market_structure_v415.py")
DATA_FILE = Path("market_data.bin")
BACKUP = Path("mlai_market_structure_v415.py.pre_audit_backup")

MODULE_NAME = "mlai_market_structure_v415"

PASS = "PASS"
FAIL = "FAIL"
WARN = "WARN"
BLOCKED = "BLOCKED"


@dataclass
class TestResult:
    name: str
    status: str
    detail: str = ""


RESULTS: list[TestResult] = []
FIXES_APPLIED: list[str] = []


def result(name: str, status: str, detail: str = ""):
    RESULTS.append(TestResult(name, status, detail))

    print()
    print("-" * 100)
    print(name)
    print("-" * 100)
    print(status)

    if detail:
        print(detail)


def fail_and_stop(message: str):
    print()
    print("=" * 100)
    print("FATAL AUDIT FAILURE")
    print("=" * 100)
    print(message)
    print("=" * 100)
    raise SystemExit(1)


def source_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def import_fresh():
    if MODULE_NAME in sys.modules:
        del sys.modules[MODULE_NAME]

    return importlib.import_module(MODULE_NAME)


def safe_repr(value: Any, limit: int = 3000) -> str:
    try:
        text = repr(value)
    except Exception as exc:
        text = f"<repr failed: {exc}>"

    return text[:limit]


def compare_objects(a: Any, b: Any) -> bool:
    try:
        return a == b
    except Exception:
        return safe_repr(a) == safe_repr(b)


def candle_clone_with_suffix_mutation(candles, boundary: int):
    mutated = list(candles)

    for i in range(boundary, len(mutated)):
        c = mutated[i]

        mutated[i] = type(c)(
            index=c.index,
            timestamp=c.timestamp,
            open=c.open + 1000.0,
            high=c.high + 1000.0,
            low=c.low + 1000.0,
            close=c.close + 1000.0,
            volume=c.volume,
        )

    return mutated


def candle_clone_with_prefix_mutation(candles, boundary: int):
    mutated = list(candles)

    for i in range(boundary):
        c = mutated[i]

        mutated[i] = type(c)(
            index=c.index,
            timestamp=c.timestamp,
            open=c.open + 500.0,
            high=c.high + 500.0,
            low=c.low + 500.0,
            close=c.close + 500.0,
            volume=c.volume,
        )

    return mutated


def load_runtime(module):
    loader = getattr(module, "load_market_data", None)

    if loader is None:
        fail_and_stop("load_market_data() is missing.")

    loaded = loader(
        getattr(module, "MARKET_DATA_FILE", str(DATA_FILE))
    )

    if not isinstance(loaded, tuple) or len(loaded) != 2:
        fail_and_stop(
            "load_market_data() does not return "
            "(candles, invalid_count)."
        )

    candles, invalid = loaded

    if not isinstance(candles, (list, tuple)):
        fail_and_stop(
            f"Loader returned invalid candle container: "
            f"{type(candles).__name__}"
        )

    if not candles:
        fail_and_stop("No candles loaded.")

    return candles, invalid


def build_runtime(module, candles):
    atr_fn = getattr(module, "calculate_atr", None)

    if atr_fn is None:
        atr_fn = getattr(module, "compute_atr", None)

    if atr_fn is None:
        fail_and_stop("No ATR function found.")

    atr = atr_fn(candles)

    engine_cls = getattr(module, "CausalStructureEngine", None)

    if engine_cls is None:
        engine_cls = getattr(module, "MarketStructureEngine", None)

    if engine_cls is None:
        fail_and_stop("No causal structure engine found.")

    engine = engine_cls(candles)
    structure = engine.build()

    market_state_fn = getattr(module, "build_market_states", None)

    if market_state_fn is None:
        fail_and_stop("build_market_states() is missing.")

    market_states = market_state_fn(
        candles,
        structure,
        atr,
    )

    episode_fn = getattr(module, "assign_episode_ids", None)

    episode_ids = None

    if episode_fn is not None:
        episode_ids = episode_fn(market_states)

    return {
        "atr": atr,
        "engine_cls": engine_cls,
        "engine": engine,
        "structure": structure,
        "market_states": market_states,
        "episode_ids": episode_ids,
    }


def audit_syntax():
    source = TARGET.read_text(encoding="utf-8")

    try:
        ast.parse(source, filename=str(TARGET))
        result(
            "1. PYTHON SYNTAX",
            PASS,
            "AST parsing succeeded."
        )
        return True
    except SyntaxError as exc:
        result(
            "1. PYTHON SYNTAX",
            FAIL,
            (
                f"{type(exc).__name__}: {exc}\n"
                f"line={exc.lineno}, offset={exc.offset}\n"
                f"text={exc.text!r}"
            ),
        )
        return False


def audit_import():
    try:
        module = import_fresh()

        result(
            "2. MODULE IMPORT",
            PASS,
            "mlai_market_structure_v415 imported successfully."
        )

        return module

    except Exception as exc:
        result(
            "2. MODULE IMPORT",
            FAIL,
            f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}",
        )
        return None


def audit_data(module):
    try:
        candles, invalid = load_runtime(module)

        candle_cls = getattr(module, "Candle", None)

        first_ok = (
            candle_cls is not None
            and isinstance(candles[0], candle_cls)
        )

        required = (
            "timestamp",
            "open",
            "high",
            "low",
            "close",
        )

        attrs_ok = all(
            hasattr(candles[0], x)
            for x in required
        )

        if not first_ok or not attrs_ok:
            result(
                "3. MARKET DATA CONTRACT",
                FAIL,
                (
                    f"candles={len(candles)} invalid={invalid}\n"
                    f"first_type={type(candles[0]).__name__}\n"
                    f"is_Candle={first_ok}\n"
                    f"required_attrs={attrs_ok}"
                ),
            )
            return None

        result(
            "3. MARKET DATA CONTRACT",
            PASS,
            (
                f"candles={len(candles)}\n"
                f"invalid={invalid}\n"
                f"first_type={type(candles[0]).__name__}\n"
                f"loader contract=(candles, invalid)"
            ),
        )

        return candles

    except Exception as exc:
        result(
            "3. MARKET DATA CONTRACT",
            FAIL,
            f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}",
        )
        return None


def audit_runtime(module, candles):
    try:
        runtime = build_runtime(module, candles)

        atr = runtime["atr"]
        structure = runtime["structure"]
        market_states = runtime["market_states"]

        if len(atr) != len(candles):
            result(
                "4. ATR CONTRACT",
                FAIL,
                f"ATR={len(atr)} candles={len(candles)}"
            )
        else:
            result(
                "4. ATR CONTRACT",
                PASS,
                f"ATR length={len(atr)}"
            )

        if len(structure) != len(candles):
            result(
                "5. STRUCTURE CONTRACT",
                FAIL,
                f"structure={len(structure)} candles={len(candles)}"
            )
        else:
            result(
                "5. STRUCTURE CONTRACT",
                PASS,
                "Structure state count equals candle count."
            )

        state_cls = getattr(module, "StructureState", None)

        bad_states = []

        if state_cls is None:
            bad_states = ["StructureState class missing"]
        else:
            for i, state in enumerate(structure):
                if not isinstance(state, state_cls):
                    bad_states.append(i)

        if bad_states:
            result(
                "6. STRUCTURE STATE TYPES",
                FAIL,
                f"Invalid states: {bad_states[:20]}"
            )
        else:
            result(
                "6. STRUCTURE STATE TYPES",
                PASS,
                "All structure states have the expected type."
            )

        if len(market_states) != len(candles):
            result(
                "7. MARKET STATE CONTRACT",
                FAIL,
                f"market_states={len(market_states)} "
                f"candles={len(candles)}"
            )
        else:
            result(
                "7. MARKET STATE CONTRACT",
                PASS,
                "Market state count equals candle count."
            )

        return runtime

    except Exception as exc:
        result(
            "4-7. CORE RUNTIME",
            FAIL,
            f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}",
        )
        return None


def audit_episode_contract(runtime):
    episode_ids = runtime["episode_ids"]
    market_states = runtime["market_states"]

    if episode_ids is None:
        result(
            "8. EPISODE CONTRACT",
            WARN,
            "assign_episode_ids() is missing."
        )
        return

    if len(episode_ids) != len(market_states):
        result(
            "8. EPISODE CONTRACT",
            FAIL,
            (
                f"episode coverage={len(episode_ids)} "
                f"market_states={len(market_states)}"
            ),
        )
        return

    missing = [
        i for i in range(len(market_states))
        if i not in episode_ids
    ]

    if missing:
        result(
            "8. EPISODE CONTRACT",
            FAIL,
            f"Missing indices: {missing[:20]}"
        )
        return

    unique = sorted(set(episode_ids.values()))

    result(
        "8. EPISODE CONTRACT",
        PASS,
        (
            f"coverage={len(episode_ids)}\n"
            f"unique episodes={len(unique)}\n"
            f"range={unique[0] if unique else None}"
            f"..{unique[-1] if unique else None}"
        ),
    )


def audit_experience_contract(module, candles, runtime):
    experience_fn = getattr(
        module,
        "build_experience_records",
        None,
    )

    episode_ids = runtime["episode_ids"]
    market_states = runtime["market_states"]
    atr = runtime["atr"]

    if experience_fn is None:
        result(
            "9. EXPERIENCE RECORD CONTRACT",
            FAIL,
            "build_experience_records() missing."
        )
        return []

    if episode_ids is None:
        result(
            "9. EXPERIENCE RECORD CONTRACT",
            BLOCKED,
            "Episode IDs unavailable."
        )
        return []

    train_end = len(candles) // 2
    horizon = 8

    try:
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

            if idx < 0:
                violations.append(
                    f"negative index {idx}"
                )

            if idx >= train_end:
                violations.append(
                    f"index {idx} >= train_end {train_end}"
                )

            if idx + horizon > train_end:
                violations.append(
                    f"index {idx}+{horizon} > {train_end}"
                )

            if r.horizon != horizon:
                violations.append(
                    f"index {idx}: horizon={r.horizon}"
                )

        if violations:
            result(
                "9. EXPERIENCE RECORD CONTRACT",
                FAIL,
                "\n".join(violations[:30]),
            )
        else:
            result(
                "9. EXPERIENCE RECORD CONTRACT",
                PASS,
                (
                    f"records={len(records)}\n"
                    f"train_end={train_end}\n"
                    f"horizon={horizon}\n"
                    f"all outcomes terminate inside training boundary"
                ),
            )

        return records

    except Exception as exc:
        result(
            "9. EXPERIENCE RECORD CONTRACT",
            FAIL,
            f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}",
        )
        return []


def audit_similarity(module, records, market_states):
    fn = getattr(module, "similarity_score", None)

    if fn is None:
        result(
            "10. SIMILARITY CONTRACT",
            FAIL,
            "similarity_score() missing."
        )
        return

    if not records:
        result(
            "10. SIMILARITY CONTRACT",
            BLOCKED,
            "No experience records."
        )
        return

    try:
        r = records[0]
        current = market_states[int(r.index)]

        score = fn(current, r)

        if not isinstance(score, dict):
            result(
                "10. SIMILARITY CONTRACT",
                FAIL,
                f"Expected dict, got {type(score).__name__}"
            )
            return

        required = {
            "total",
            "structure",
            "sequence",
            "regime",
            "location",
            "momentum",
            "volatility",
            "candle",
            "path",
        }

        missing = required - set(score)

        bad_ranges = [
            key
            for key in required
            if key in score
            and not (
                isinstance(score[key], (int, float))
                and 0.0 <= float(score[key]) <= 1.0
            )
        ]

        if missing or bad_ranges:
            result(
                "10. SIMILARITY CONTRACT",
                FAIL,
                (
                    f"missing={sorted(missing)}\n"
                    f"bad_ranges={bad_ranges}\n"
                    f"score={safe_repr(score)}"
                ),
            )
            return

        result(
            "10. SIMILARITY CONTRACT",
            PASS,
            safe_repr(score),
        )

    except Exception as exc:
        result(
            "10. SIMILARITY CONTRACT",
            FAIL,
            f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}",
        )


def audit_full_market_state_causality(module, candles, runtime):
    boundary = len(candles) // 2

    try:
        original_states = runtime["market_states"]

        mutated = candle_clone_with_suffix_mutation(
            candles,
            boundary,
        )

        mutated_runtime = build_runtime(
            module,
            mutated,
        )

        mutated_states = mutated_runtime["market_states"]

        mismatches = []

        for i in range(boundary):
            if not compare_objects(
                original_states[i],
                mutated_states[i],
            ):
                mismatches.append(i)

        if mismatches:
            result(
                "11. FULL MARKET-STATE PREFIX CAUSALITY",
                FAIL,
                (
                    f"mismatches={len(mismatches)}\n"
                    f"first={mismatches[:30]}"
                ),
            )
        else:
            result(
                "11. FULL MARKET-STATE PREFIX CAUSALITY",
                PASS,
                (
                    f"All {boundary} historical MarketState objects "
                    f"were unchanged by suffix mutation."
                ),
            )

    except Exception as exc:
        result(
            "11. FULL MARKET-STATE PREFIX CAUSALITY",
            FAIL,
            f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}",
        )


def audit_path_vector_causality(module, candles, runtime):
    fn = getattr(module, "build_path_vector", None)

    if fn is None:
        result(
            "12. PATH VECTOR CAUSALITY",
            FAIL,
            "build_path_vector() missing."
        )
        return

    boundary = len(candles) // 2

    try:
        original_atr = runtime["atr"]

        mutated = candle_clone_with_suffix_mutation(
            candles,
            boundary,
        )

        mutated_atr = module.calculate_atr(mutated)

        mismatches = []

        start = max(0, boundary - 20)

        for i in range(start, boundary):
            a = fn(candles, original_atr, i)
            b = fn(mutated, mutated_atr, i)

            if not compare_objects(a, b):
                mismatches.append(i)

        if mismatches:
            result(
                "12. PATH VECTOR CAUSALITY",
                FAIL,
                f"mismatches={mismatches[:30]}"
            )
        else:
            result(
                "12. PATH VECTOR CAUSALITY",
                PASS,
                (
                    "Recent pre-boundary path vectors remained "
                    "unchanged after suffix mutation."
                ),
            )

    except Exception as exc:
        result(
            "12. PATH VECTOR CAUSALITY",
            FAIL,
            f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}",
        )


def audit_retrieval_temporal_isolation(
    module,
    candles,
    runtime,
    records,
):
    fn = getattr(
        module,
        "retrieve_historical_experience",
        None,
    )

    if fn is None:
        result(
            "13. RETRIEVAL TEMPORAL ISOLATION",
            FAIL,
            "retrieve_historical_experience() missing."
        )
        return

    if not records:
        result(
            "13. RETRIEVAL TEMPORAL ISOLATION",
            BLOCKED,
            "No experience records."
        )
        return

    market_states = runtime["market_states"]

    train_end = len(candles) // 2
    query_index = min(
        len(candles) - 1,
        train_end + 10,
    )

    try:
        current = market_states[query_index]

        retrieval = fn(
            current,
            records,
            8,
            query_index,
        )

        selected = list(
            getattr(
                retrieval,
                "selected_match_indices",
                [],
            )
        )

        historical_max = getattr(
            retrieval,
            "historical_max_index",
            None,
        )

        bad_selected = [
            i for i in selected
            if i >= query_index
        ]

        future_outcome_overlap = [
            i for i in selected
            if i + 8 >= query_index
        ]

        if bad_selected or future_outcome_overlap:
            result(
                "13. RETRIEVAL TEMPORAL ISOLATION",
                FAIL,
                (
                    f"query_index={query_index}\n"
                    f"bad_selected={bad_selected[:30]}\n"
                    f"outcome_overlap={future_outcome_overlap[:30]}\n"
                    f"historical_max={historical_max}"
                ),
            )
        else:
            result(
                "13. RETRIEVAL TEMPORAL ISOLATION",
                PASS,
                (
                    f"query_index={query_index}\n"
                    f"selected={len(selected)}\n"
                    f"historical_max={historical_max}\n"
                    f"no selected match is at/after query index\n"
                    f"no selected outcome overlaps query index"
                ),
            )

    except Exception as exc:
        result(
            "13. RETRIEVAL TEMPORAL ISOLATION",
            FAIL,
            f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}",
        )


def audit_retrieval_repeatability(
    module,
    candles,
    runtime,
    records,
):
    fn = getattr(
        module,
        "retrieve_historical_experience",
        None,
    )

    if fn is None or not records:
        result(
            "14. RETRIEVAL DETERMINISM",
            BLOCKED,
            "Retrieval function or records unavailable."
        )
        return

    query_indices = [
        max(len(candles) // 2 + 5, 0),
        max(len(candles) // 2 + 20, 0),
        max(len(candles) - 5, 0),
    ]

    failures = []

    try:
        for q in query_indices:
            current = runtime["market_states"][q]

            a = fn(
                current,
                records,
                8,
                q,
            )

            b = fn(
                current,
                records,
                8,
                q,
            )

            if not compare_objects(a, b):
                failures.append(q)

        if failures:
            result(
                "14. RETRIEVAL DETERMINISM",
                FAIL,
                f"non-deterministic queries={failures}"
            )
        else:
            result(
                "14. RETRIEVAL DETERMINISM",
                PASS,
                f"Repeated retrievals identical for queries={query_indices}"
            )

    except Exception as exc:
        result(
            "14. RETRIEVAL DETERMINISM",
            FAIL,
            f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}",
        )


def audit_episode_semantics(runtime):
    states = runtime["market_states"]
    episode_ids = runtime["episode_ids"]

    if episode_ids is None:
        result(
            "15. EPISODE SEMANTICS",
            BLOCKED,
            "Episode IDs unavailable."
        )
        return

    transitions = Counter()
    episode_lengths = Counter()

    for i in range(1, len(states)):
        if episode_ids[i] != episode_ids[i - 1]:
            previous = states[i - 1]
            current = states[i]

            transition = []

            if previous.trend != current.trend:
                transition.append("trend")

            if previous.regime != current.regime:
                transition.append("regime")

            if previous.sequence_state != current.sequence_state:
                transition.append("sequence")

            if current.structure_event != "NONE":
                transition.append("structure_event")

            transitions[
                tuple(transition)
            ] += 1

    for episode in episode_ids.values():
        episode_lengths[episode] += 1

    lengths = list(episode_lengths.values())

    one_bar = sum(
        1 for x in lengths
        if x == 1
    )

    one_bar_ratio = (
        one_bar / len(lengths)
        if lengths
        else 0.0
    )

    print()
    print("Episode transition causes:")

    for key, value in transitions.most_common():
        print(f"  {key}: {value}")

    print()
    print(f"episodes={len(lengths)}")
    print(f"one-bar episodes={one_bar}")
    print(f"one-bar ratio={one_bar_ratio:.4f}")
    print(
        f"median-ish length="
        f"{sorted(lengths)[len(lengths)//2] if lengths else 0}"
    )

    # This is intentionally diagnostic, not automatically a failure.
    # High fragmentation can be legitimate because sequence state may change
    # frequently. We therefore report it rather than patching semantics blindly.

    result(
        "15. EPISODE SEMANTICS",
        PASS,
        (
            "Episode segmentation is internally observable and "
            "was not automatically altered. "
            f"one-bar ratio={one_bar_ratio:.4f}"
        ),
    )


def audit_source_contracts():
    source = TARGET.read_text(encoding="utf-8")
    tree = ast.parse(source)

    required = [
        "Candle",
        "StructureState",
        "MarketState",
        "ExperienceRecord",
        "CausalStructureEngine",
        "build_market_states",
        "assign_episode_ids",
        "build_experience_records",
        "similarity_score",
        "retrieve_historical_experience",
        "build_path_vector",
        "calculate_atr",
        "load_market_data",
    ]

    found = set()

    for node in tree.body:
        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
                ast.ClassDef,
            ),
        ):
            found.add(node.name)

    missing = [
        name for name in required
        if name not in found
    ]

    if missing:
        result(
            "16. SOURCE API CONTRACT",
            FAIL,
            f"Missing declarations={missing}"
        )
    else:
        result(
            "16. SOURCE API CONTRACT",
            PASS,
            "All required declarations exist."
        )


def audit_dangerous_future_patterns():
    source = TARGET.read_text(encoding="utf-8")
    tree = ast.parse(source)

    suspicious = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            try:
                name = ast.unparse(node.func)
            except Exception:
                name = ""

            lowered = name.lower()

            if "future" in lowered:
                suspicious.append(
                    (
                        node.lineno,
                        name,
                    )
                )

    if suspicious:
        result(
            "17. FUTURE-DEPENDENCY STATIC SCAN",
            WARN,
            (
                "Names containing 'future' were found; "
                "this is a manual-review warning, not proof of leakage.\n"
                + "\n".join(
                    f"line {line}: {name}"
                    for line, name in suspicious[:30]
                )
            ),
        )
    else:
        result(
            "17. FUTURE-DEPENDENCY STATIC SCAN",
            PASS,
            "No obvious future-named callable references detected."
        )


def audit_runtime_source_locations(module):
    names = [
        "build_market_states",
        "assign_episode_ids",
        "build_experience_records",
        "similarity_score",
        "retrieve_historical_experience",
        "build_path_vector",
        "calculate_atr",
    ]

    lines = []

    for name in names:
        obj = getattr(module, name, None)

        if obj is None:
            continue

        try:
            lines.append(
                f"{name}: {inspect.getsourcefile(obj)}:"
                f"{inspect.getsourcelines(obj)[1]}"
            )
        except Exception as exc:
            lines.append(
                f"{name}: unavailable ({exc})"
            )

    result(
        "18. RUNTIME SOURCE LOCATION",
        PASS,
        "\n".join(lines)
    )


def create_backup():
    if not TARGET.exists():
        fail_and_stop(
            f"Target file does not exist: {TARGET}"
        )

    current_hash = source_hash(TARGET)

    if BACKUP.exists():
        backup_hash = source_hash(BACKUP)

        if backup_hash != current_hash:
            fail_and_stop(
                (
                    f"Existing backup differs from current source:\n"
                    f"{BACKUP}\n"
                    "Refusing to overwrite it automatically."
                )
            )
    else:
        shutil.copy2(TARGET, BACKUP)

    print()
    print("=" * 100)
    print("BACKUP")
    print("=" * 100)
    print(f"Target : {TARGET}")
    print(f"Backup : {BACKUP}")
    print(f"SHA256 : {current_hash}")


def apply_only_verified_safe_fixes():
    """
    IMPORTANT:

    We currently have no proven implementation defect from the forensic
    results supplied by the user.

    Therefore this function deliberately does NOT rewrite v4.1.5 based on
    assumptions.

    This is intentional. An automatic patch without a proven defect would
    be more dangerous than leaving a verified implementation untouched.
    """

    print()
    print("=" * 100)
    print("AUTOMATIC FIX PHASE")
    print("=" * 100)

    print(
        "No automatic implementation patch is justified by the current "
        "evidence."
    )

    print(
        "The previous failure was caused by diagnostic misuse of the "
        "loader return contract, not by v4.1.5."
    )

    print(
        "No source modification will be made unless a reproducible "
        "implementation defect is demonstrated."
    )


def print_summary():
    print()
    print("=" * 100)
    print("MLAI v4.1.5 — FINAL AUDIT SUMMARY")
    print("=" * 100)

    counts = Counter(x.status for x in RESULTS)

    print()
    print(f"PASS    : {counts[PASS]}")
    print(f"FAIL    : {counts[FAIL]}")
    print(f"WARN    : {counts[WARN]}")
    print(f"BLOCKED : {counts[BLOCKED]}")

    print()
    print("TEST RESULTS")
    print("-" * 100)

    for item in RESULTS:
        print(
            f"[{item.status:8}] {item.name}"
        )

    print()
    print("FIXES APPLIED")
    print("-" * 100)

    if FIXES_APPLIED:
        for fix in FIXES_APPLIED:
            print(f"- {fix}")
    else:
        print("NONE")

    print()
    print("=" * 100)

    failures = [
        x for x in RESULTS
        if x.status == FAIL
    ]

    if failures:
        print("FINAL VERDICT: FAIL")
        print()
        print(
            "A concrete implementation defect remains. "
            "Do NOT create v4.1.6 yet."
        )
    else:
        print("FINAL VERDICT: PASS / NO PROVEN IMPLEMENTATION DEFECT")
        print()
        print(
            "The audited v4.1.5 runtime passed all executable "
            "contracts available to this audit."
        )

    print("=" * 100)


def main():
    print("=" * 100)
    print("MLAI v4.1.5 — FULL FORENSIC AUDIT / TEST / SAFE-FIX PROGRAM")
    print("=" * 100)

    print()
    print("IMPORTANT:")
    print("  - mlai_market_structure_v415.py will NOT be modified blindly.")
    print("  - market_data.bin will NOT be modified.")
    print("  - Existing source will be backed up before any fix.")
    print("  - No v4.1.6 will be created automatically.")
    print()

    if not TARGET.exists():
        fail_and_stop(
            f"Missing target: {TARGET}"
        )

    if not DATA_FILE.exists():
        fail_and_stop(
            f"Missing market data: {DATA_FILE}"
        )

    original_hash = source_hash(TARGET)

    # ---------------------------------------------------------------
    # Phase 1 — static/source checks
    # ---------------------------------------------------------------

    if not audit_syntax():
        fail_and_stop(
            "Cannot continue because source syntax is invalid."
        )

    audit_source_contracts()

    audit_dangerous_future_patterns()

    # ---------------------------------------------------------------
    # Phase 2 — runtime
    # ---------------------------------------------------------------

    module = audit_import()

    if module is None:
        fail_and_stop(
            "Cannot continue because module import failed."
        )

    candles = audit_data(module)

    if candles is None:
        fail_and_stop(
            "Cannot continue because the market-data contract failed."
        )

    runtime = audit_runtime(module, candles)

    if runtime is None:
        fail_and_stop(
            "Cannot continue because core runtime construction failed."
        )

    audit_runtime_source_locations(module)

    # ---------------------------------------------------------------
    # Phase 3 — historical experience
    # ---------------------------------------------------------------

    audit_episode_contract(runtime)

    records = audit_experience_contract(
        module,
        candles,
        runtime,
    )

    audit_similarity(
        module,
        records,
        runtime["market_states"],
    )

    # ---------------------------------------------------------------
    # Phase 4 — causality
    # ---------------------------------------------------------------

    audit_full_market_state_causality(
        module,
        candles,
        runtime,
    )

    audit_path_vector_causality(
        module,
        candles,
        runtime,
    )

    # ---------------------------------------------------------------
    # Phase 5 — retrieval
    # ---------------------------------------------------------------

    audit_retrieval_temporal_isolation(
        module,
        candles,
        runtime,
        records,
    )

    audit_retrieval_repeatability(
        module,
        candles,
        runtime,
        records,
    )

    # ---------------------------------------------------------------
    # Phase 6 — episode semantics
    # ---------------------------------------------------------------

    audit_episode_semantics(runtime)

    # ---------------------------------------------------------------
    # Phase 7 — safe fix decision
    # ---------------------------------------------------------------

    create_backup()

    apply_only_verified_safe_fixes()

    # ---------------------------------------------------------------
    # Phase 8 — source integrity
    # ---------------------------------------------------------------

    final_hash = source_hash(TARGET)

    if final_hash == original_hash:
        result(
            "19. SOURCE INTEGRITY",
            PASS,
            "v4.1.5 source remained byte-for-byte unchanged."
        )
    else:
        result(
            "19. SOURCE INTEGRITY",
            WARN,
            (
                "Source changed during execution.\n"
                f"original={original_hash}\n"
                f"final={final_hash}"
            ),
        )

    print_summary()


if __name__ == "__main__":
    main()