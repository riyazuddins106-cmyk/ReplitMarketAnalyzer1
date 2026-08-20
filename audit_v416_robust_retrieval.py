import math
from collections import Counter
import mlai_market_structure_v416 as m

print("=" * 110)
print("MLAI v4.1.6 — ROBUST RETRIEVAL ARCHITECTURE AUDIT")
print("=" * 110)


# =====================================================================
# 1. SOURCE / CONSTANT INSPECTION
# =====================================================================

print()
print("=" * 110)
print("RETRIEVAL CONSTANTS")
print("=" * 110)

constants = [
    "MIN_HISTORY_GAP",
    "MIN_RETRIEVAL_MATCHES",
    "RETRIEVAL_TOP_K",
    "HORIZONS",
    "DEFAULT_TRAIN_WINDOWS",
    "DEFAULT_OOS_SIZE",
]

for name in constants:
    print(f"{name:<30} =", getattr(m, name, "MISSING"))


# =====================================================================
# 2. WEIGHT VALIDATION
# =====================================================================

print()
print("=" * 110)
print("RETRIEVAL WEIGHTS")
print("=" * 110)

weight_names = [
    "WEIGHT_STRUCTURE",
    "WEIGHT_SEQUENCE",
    "WEIGHT_REGIME",
    "WEIGHT_LOCATION",
    "WEIGHT_MOMENTUM",
    "WEIGHT_VOLATILITY",
    "WEIGHT_CANDLE",
    "WEIGHT_PATH",
]

weights = {}

for name in weight_names:
    value = float(getattr(m, name))
    weights[name] = value
    print(f"{name:<30} = {value}")

total_weight = sum(weights.values())

print()
print("TOTAL =", total_weight)

if math.isclose(total_weight, 1.0, rel_tol=1e-9, abs_tol=1e-9):
    print("PASS: weights sum to 1.0")
else:
    print("FAIL: weights do not sum to 1.0")


# =====================================================================
# 3. BUILD MARKET DATA
# =====================================================================

print()
print("=" * 110)
print("BUILDING MARKET STATE")
print("=" * 110)

loaded = m.load_market_data(m.MARKET_DATA_FILE)

if not isinstance(loaded, tuple) or len(loaded) != 2:
    raise RuntimeError(
        "Unexpected load_market_data() return format: "
        + repr(type(loaded))
    )

candles, invalid = loaded

print("candles =", len(candles))

# v4.1.6 returns invalid as an integer count.
if isinstance(invalid, int):
    invalid_count = invalid
elif hasattr(invalid, "__len__"):
    invalid_count = len(invalid)
else:
    invalid_count = int(invalid)

print("invalid =", invalid_count)

if not candles:
    raise RuntimeError("NO CANDLES")

if invalid_count != 0:
    print("WARNING: invalid candle count =", invalid_count)
else:
    print("PASS: no invalid candles")


# =====================================================================
# 4. ATR
# =====================================================================

atr = m.calculate_atr(candles)

print()
print("=" * 110)
print("ATR")
print("=" * 110)

print("atr length =", len(atr))

valid_atr = [
    x for x in atr
    if x is not None and math.isfinite(float(x))
]

print("valid ATR values =", len(valid_atr))

if not valid_atr:
    raise RuntimeError("NO VALID ATR VALUES")

print("PASS: ATR contains valid values")


# =====================================================================
# 5. STRUCTURE
# =====================================================================

engine = m.CausalStructureEngine(candles)

structure_states = engine.build()

print()
print("=" * 110)
print("CAUSAL STRUCTURE")
print("=" * 110)

print("structure states =", len(structure_states))

if len(structure_states) != len(candles):
    print(
        "WARNING: structure state count differs from candle count:",
        len(structure_states),
        "vs",
        len(candles),
    )
else:
    print("PASS: structure state count matches candles")


# =====================================================================
# 6. MARKET STATES
# =====================================================================

states = m.build_market_states(
    candles,
    structure_states,
    atr,
)

print()
print("=" * 110)
print("MARKET STATES")
print("=" * 110)

print("states =", len(states))

if len(states) != len(candles):
    raise RuntimeError(
        f"STATE COUNT MISMATCH: candles={len(candles)} states={len(states)}"
    )

print("PASS: market state count matches candles")


# =====================================================================
# 7. EPISODES
# =====================================================================

episode_ids = m.assign_episode_ids(states)

print()
print("=" * 110)
print("EPISODE SEGMENTATION")
print("=" * 110)

print("episode mapping =", len(episode_ids))

unique_episodes = sorted(set(episode_ids.values()))

print("unique episodes =", len(unique_episodes))

if not unique_episodes:
    raise RuntimeError("NO EPISODES")

print(
    "first episode =",
    unique_episodes[0],
    "last episode =",
    unique_episodes[-1],
)

# Verify every state has an episode.
missing_episode_ids = [
    i for i in range(len(states))
    if i not in episode_ids
]

print("missing episode IDs =", len(missing_episode_ids))

if missing_episode_ids:
    print("FAIL: missing episode assignments")
else:
    print("PASS: every state has an episode")


# =====================================================================
# 8. WALK-FORWARD WINDOW
# =====================================================================

windows = m.create_walk_forward_windows(
    len(candles),
    m.DEFAULT_TRAIN_WINDOWS,
    m.DEFAULT_OOS_SIZE,
)

if not windows:
    raise RuntimeError("NO WALK-FORWARD WINDOWS")

window = windows[0]
horizon = m.HORIZONS[0]

print()
print("=" * 110)
print("WALK-FORWARD WINDOW")
print("=" * 110)

print("train_start =", window.train_start)
print("train_end   =", window.train_end)
print("oos_start   =", window.oos_start)
print("oos_end     =", window.oos_end)
print("horizon     =", horizon)


# =====================================================================
# 9. EXPERIENCE RECORDS
# =====================================================================

records = m.build_experience_records(
    candles,
    atr,
    states,
    episode_ids,
    window.train_start,
    window.train_end,
    horizon,
)

print()
print("=" * 110)
print("EXPERIENCE RECORDS")
print("=" * 110)

print("records =", len(records))

if not records:
    raise RuntimeError("NO EXPERIENCE RECORDS")

print(
    "record index range =",
    min(r.index for r in records),
    "->",
    max(r.index for r in records),
)

# Future leakage check inside training records.
record_future_violations = []

for r in records:
    if r.index >= window.train_end:
        record_future_violations.append(
            ("record_after_train_end", r.index)
        )

if record_future_violations:
    print(
        "FAIL: records exist at/after train_end:",
        record_future_violations[:10],
    )
else:
    print("PASS: records stay before train_end")


# =====================================================================
# 10. QUERY
# =====================================================================

query_index = window.oos_start
current = states[query_index]

print()
print("=" * 110)
print("QUERY STATE")
print("=" * 110)

print("query_index =", query_index)
print("trend       =", current.trend)
print("event       =", current.structure_event)
print("high_label  =", current.high_label)
print("low_label   =", current.low_label)
print("sequence    =", current.sequence_state)
print("regime      =", current.regime)
print("location    =", current.location)
print("momentum    =", current.momentum_state)

print()
print("numeric:")
print("volatility  =", current.volatility_ratio)
print("body        =", current.body_ratio)
print("range       =", current.range_ratio)
print("r1          =", current.r1)
print("r3          =", current.r3)
print("r8          =", current.r8)
print("r16         =", current.r16)


# =====================================================================
# 11. RAW CAUSAL ELIGIBILITY
# =====================================================================

eligible = [
    r
    for r in records
    if r.index < query_index
    and query_index - r.index >= m.MIN_HISTORY_GAP
]

print()
print("=" * 110)
print("CAUSAL ELIGIBILITY")
print("=" * 110)

print("eligible =", len(eligible))

violations = [
    r
    for r in eligible
    if r.index >= query_index
    or query_index - r.index < m.MIN_HISTORY_GAP
]

print("causality violations =", len(violations))

if violations:
    print("FAIL: causal eligibility violation")
else:
    print("PASS: all eligible records are causal")


# =====================================================================
# 12. COARSE FILTER
# =====================================================================

candidates = m.coarse_filter(
    current,
    records,
    query_index,
)

print()
print("=" * 110)
print("COARSE FILTER")
print("=" * 110)

print("eligible   =", len(eligible))
print("candidates =", len(candidates))

if eligible:
    retention = len(candidates) / len(eligible)
else:
    retention = 0.0

print("retention ratio =", round(retention, 6))
print("rejection ratio =", round(1.0 - retention, 6))

candidate_violations = [
    r
    for r in candidates
    if r.index >= query_index
    or query_index - r.index < m.MIN_HISTORY_GAP
]

print("candidate causal violations =", len(candidate_violations))

if candidate_violations:
    print("FAIL: coarse filter introduced causal violation")
else:
    print("PASS: coarse-filter candidates remain causal")


# =====================================================================
# 13. FULL CATEGORICAL STATE
# =====================================================================

def full_state(record):
    return (
        record.state_key[0],
        record.structure_event,
        record.state_key[2],
        record.state_key[3],
        record.sequence_state,
        record.regime,
        record.location,
        record.momentum_state,
    )


query_full_state = (
    current.trend,
    current.structure_event,
    current.high_label,
    current.low_label,
    current.sequence_state,
    current.regime,
    current.location,
    current.momentum_state,
)

exact_matches = [
    r
    for r in eligible
    if full_state(r) == query_full_state
]

candidate_exact_matches = [
    r
    for r in candidates
    if full_state(r) == query_full_state
]

print()
print("=" * 110)
print("FULL CATEGORICAL STATE DISCRIMINATION")
print("=" * 110)

print("exact full-state matches =", len(exact_matches))
print("candidate exact matches  =", len(candidate_exact_matches))
print("OR-filter candidates     =", len(candidates))

if candidates:
    print(
        "exact-state / candidate ratio =",
        round(
            len(candidate_exact_matches) / len(candidates),
            6,
        ),
    )


# =====================================================================
# 14. COARSE FILTER ADMISSION LOGIC
# =====================================================================

condition_counts = Counter()

for r in eligible:

    regime = r.regime == current.regime
    event = r.structure_event == current.structure_event
    sequence = r.sequence_state == current.sequence_state

    if regime and event and sequence:
        condition_counts["REGIME+EVENT+SEQUENCE"] += 1
    elif regime and event:
        condition_counts["REGIME+EVENT"] += 1
    elif regime and sequence:
        condition_counts["REGIME+SEQUENCE"] += 1
    elif event and sequence:
        condition_counts["EVENT+SEQUENCE"] += 1
    elif regime:
        condition_counts["REGIME_ONLY"] += 1
    elif event:
        condition_counts["EVENT_ONLY"] += 1
    elif sequence:
        condition_counts["SEQUENCE_ONLY"] += 1
    else:
        condition_counts["NONE"] += 1

print()
print("=" * 110)
print("COARSE FILTER ADMISSION BREAKDOWN")
print("=" * 110)

for name, count in condition_counts.most_common():
    print(f"{name:<35} = {count}")


# =====================================================================
# 15. SIMILARITY
# =====================================================================

scored = []

for record in candidates:

    components = m.similarity_score(
        current,
        record,
    )

    scored.append(
        (
            float(components["total"]),
            record,
            components,
        )
    )

scored.sort(
    key=lambda x: (x[0], x[1].index),
    reverse=True,
)

values = [x[0] for x in scored]

print()
print("=" * 110)
print("SIMILARITY DISTRIBUTION")
print("=" * 110)

for threshold in (
    0.99,
    0.95,
    0.90,
    0.85,
    0.80,
    0.75,
    0.70,
    0.60,
    0.50,
):

    print(
        f">= {threshold:.2f} :",
        sum(v >= threshold for v in values),
    )

if values:
    print()
    print("min  =", min(values))
    print("mean =", sum(values) / len(values))
    print("max  =", max(values))


# =====================================================================
# 16. SIMILARITY COMPONENT DISTRIBUTION
# =====================================================================

print()
print("=" * 110)
print("COMPONENT CONTRIBUTION ANALYSIS")
print("=" * 110)

component_names = [
    "structure",
    "sequence",
    "regime",
    "location",
    "momentum",
    "volatility",
    "candle",
    "path",
]

weight_map = {
    "structure": m.WEIGHT_STRUCTURE,
    "sequence": m.WEIGHT_SEQUENCE,
    "regime": m.WEIGHT_REGIME,
    "location": m.WEIGHT_LOCATION,
    "momentum": m.WEIGHT_MOMENTUM,
    "volatility": m.WEIGHT_VOLATILITY,
    "candle": m.WEIGHT_CANDLE,
    "path": m.WEIGHT_PATH,
}

for name in component_names:

    component_values = [
        float(item[2][name])
        for item in scored
    ]

    if not component_values:
        continue

    print()
    print(name.upper())
    print("-" * 70)

    print("weight      =", weight_map[name])
    print("mean raw    =", round(sum(component_values) / len(component_values), 6))
    print("min raw     =", round(min(component_values), 6))
    print("max raw     =", round(max(component_values), 6))

    high_count = sum(v >= 0.90 for v in component_values)

    print(">= 0.90     =", high_count)


# =====================================================================
# 17. PATH SIMILARITY SENSITIVITY
# =====================================================================

print()
print("=" * 110)
print("PATH SIMILARITY SENSITIVITY")
print("=" * 110)

path_values = []

for record in candidates:

    try:
        value = float(
            m.path_similarity(
                current,
                record,
            )
        )

        path_values.append(value)

    except Exception as exc:

        print("ERROR:", exc)
        break

if path_values:

    print("count =", len(path_values))
    print("min   =", min(path_values))
    print("mean  =", sum(path_values) / len(path_values))
    print("max   =", max(path_values))

    unique_rounded = len(
        set(round(v, 6) for v in path_values)
    )

    print(
        "unique rounded path scores =",
        unique_rounded,
    )


# =====================================================================
# 18. NUMERIC SIMILARITY SANITY
# =====================================================================

print()
print("=" * 110)
print("NUMERIC SIMILARITY SANITY CHECK")
print("=" * 110)

if candidates:

    test_pairs = [
        (
            "volatility",
            current.volatility_ratio,
            candidates[0].volatility_ratio,
            0.50,
        ),
        (
            "body",
            current.body_ratio,
            candidates[0].body_ratio,
            1.00,
        ),
        (
            "range",
            current.range_ratio,
            candidates[0].range_ratio,
            1.00,
        ),
    ]

    for name, a, b, scale in test_pairs:

        result = float(
            m.numeric_similarity(a, b, scale)
        )

        reverse = float(
            m.numeric_similarity(b, a, scale)
        )

        print()
        print(name)
        print("a =", a)
        print("b =", b)
        print("similarity(a,b) =", result)
        print("similarity(b,a) =", reverse)

        if not math.isclose(
            result,
            reverse,
            rel_tol=1e-9,
            abs_tol=1e-9,
        ):
            print("FAIL: numeric similarity asymmetric")
        else:
            print("PASS: symmetric")


# =====================================================================
# 19. TOP MATCHES
# =====================================================================

print()
print("=" * 110)
print("TOP 15 MATCHES")
print("=" * 110)

for rank, (total_score, record, components) in enumerate(
    scored[:15],
    1,
):

    print()
    print(f"RANK {rank}")
    print("-" * 110)

    print(
        "index=",
        record.index,
        "episode=",
        record.episode_id,
        "similarity=",
        round(total_score, 6),
    )

    print(
        "categorical:",
        record.state_key[0],
        record.structure_event,
        record.state_key[2],
        record.state_key[3],
        record.sequence_state,
        record.regime,
        record.location,
        record.momentum_state,
    )

    print(
        "numeric:",
        "vol=", round(record.volatility_ratio, 6),
        "body=", round(record.body_ratio, 6),
        "range=", round(record.range_ratio, 6),
        "r1=", round(record.r1, 6),
        "r3=", round(record.r3, 6),
        "r8=", round(record.r8, 6),
        "r16=", round(record.r16, 6),
    )

    print(
        "components:",
        {
            k: round(v, 6)
            for k, v in components.items()
        },
    )


# =====================================================================
# 20. EPISODE DEDUPLICATION
# =====================================================================

matches = [
    m.SimilarityMatch(
        index=record.index,
        episode_id=record.episode_id,
        similarity=components["total"],
        structure_similarity=components["structure"],
        sequence_similarity=components["sequence"],
        regime_similarity=components["regime"],
        location_similarity=components["location"],
        momentum_similarity=components["momentum"],
        volatility_similarity=components["volatility"],
        candle_similarity=components["candle"],
        path_similarity=components["path"],
    )
    for _, record, components in scored
]

selected = m.select_episode_representatives(matches)

selected_episodes = [
    match.episode_id
    for match in selected
]

duplicate_selected_episodes = [
    episode
    for episode, count in Counter(selected_episodes).items()
    if count > 1
]

print()
print("=" * 110)
print("EPISODE DEDUPLICATION")
print("=" * 110)

print("raw matches =", len(matches))
print("selected    =", len(selected))
print("top_k       =", m.RETRIEVAL_TOP_K)

print(
    "duplicate episode IDs in selected =",
    duplicate_selected_episodes,
)

if duplicate_selected_episodes:
    print("FAIL: deduplication violation")
else:
    print("PASS: one representative per episode")


# =====================================================================
# 21. SELECTED REPRESENTATIVE QUALITY
# =====================================================================

print()
print("=" * 110)
print("SELECTED REPRESENTATIVE QUALITY")
print("=" * 110)

if selected:

    selected_scores = [
        float(x.similarity)
        for x in selected
    ]

    print("selected count =", len(selected))
    print("selected min   =", min(selected_scores))
    print("selected mean  =", sum(selected_scores) / len(selected_scores))
    print("selected max   =", max(selected_scores))

    print(
        "selected >= 0.90 =",
        sum(v >= 0.90 for v in selected_scores),
    )

    print(
        "selected >= 0.80 =",
        sum(v >= 0.80 for v in selected_scores),
    )


# =====================================================================
# 22. FINAL SUMMARY
# =====================================================================

print()
print("=" * 110)
print("ROBUST AUDIT SUMMARY")
print("=" * 110)

print(
    "1. Weight normalization          :",
    "PASS"
    if math.isclose(total_weight, 1.0, rel_tol=1e-9, abs_tol=1e-9)
    else "FAIL",
)

print(
    "2. Valid candles                :",
    "PASS" if invalid_count == 0 else "WARNING",
)

print(
    "3. State count                  :",
    "PASS" if len(states) == len(candles) else "FAIL",
)

print(
    "4. Causal eligibility           :",
    "PASS" if not violations else "FAIL",
)

print(
    "5. Candidate causal safety     :",
    "PASS" if not candidate_violations else "FAIL",
)

print(
    "6. Coarse retention             :",
    round(retention, 6),
)

print(
    "7. Exact full-state matches     :",
    len(exact_matches),
)

print(
    "8. OR-filter candidates         :",
    len(candidates),
)

print(
    "9. Similarity >= 0.90           :",
    sum(v >= 0.90 for v in values),
)

print(
    "10. Similarity >= 0.80          :",
    sum(v >= 0.80 for v in values),
)

print(
    "11. Selected representatives    :",
    len(selected),
)

print(
    "12. Duplicate selected episodes :",
    len(duplicate_selected_episodes),
)

print()
print("=" * 110)
print("AUDIT COMPLETE — NO SOURCE FILES MODIFIED")
print("=" * 110)

