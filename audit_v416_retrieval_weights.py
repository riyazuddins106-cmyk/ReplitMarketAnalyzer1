import inspect
import mlai_market_structure_v416 as m

print("=" * 100)
print("MLAI v4.1.6 — RETRIEVAL WEIGHT / FILTER / DEDUPLICATION AUDIT")
print("=" * 100)

# ================================================================
# 1. RETRIEVAL WEIGHTS
# ================================================================

print()
print("=" * 100)
print("RETRIEVAL WEIGHTS")
print("=" * 100)

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

total_weight = 0.0

for name in weight_names:
    value = getattr(m, name, None)
    print(f"{name:<24} = {value}")
    if value is not None:
        total_weight += value

print()
print("TOTAL WEIGHT =", total_weight)

# ================================================================
# 2. COARSE FILTER
# ================================================================

print()
print("=" * 100)
print("COARSE FILTER")
print("=" * 100)

print(inspect.getsource(m.coarse_filter))

# ================================================================
# 3. EPISODE REPRESENTATIVE SELECTION
# ================================================================

print()
print("=" * 100)
print("EPISODE REPRESENTATIVE SELECTION")
print("=" * 100)

print(inspect.getsource(m.select_episode_representatives))

# ================================================================
# 4. SIMILARITY SCORE
# ================================================================

print()
print("=" * 100)
print("SIMILARITY SCORE")
print("=" * 100)

print(inspect.getsource(m.similarity_score))

# ================================================================
# 5. BUILD DATA
# ================================================================

candles, invalid = m.load_market_data(m.MARKET_DATA_FILE)

atr = m.calculate_atr(candles)
engine = m.CausalStructureEngine(candles)
structure_states = engine.build()
states = m.build_market_states(candles, structure_states, atr)
episode_ids = m.assign_episode_ids(states)

windows = m.create_walk_forward_windows(
    len(candles),
    m.DEFAULT_TRAIN_WINDOWS,
    m.DEFAULT_OOS_SIZE,
)

# ================================================================
# 6. DETAILED COMPONENT AUDIT
# ================================================================

print()
print("=" * 100)
print("DETAILED COMPONENT AUDIT")
print("=" * 100)

window = windows[0]
horizon = m.HORIZONS[0]

records = m.build_experience_records(
    candles,
    atr,
    states,
    episode_ids,
    window.train_start,
    window.train_end,
    horizon,
)

query_index = window.oos_start
current = states[query_index]

eligible = [
    r for r in records
    if r.index < query_index
    and query_index - r.index >= m.MIN_HISTORY_GAP
]

compatible = [
    r for r in eligible
    if (
        r.regime == current.regime
        or r.structure_event == current.structure_event
        or r.sequence_state == current.sequence_state
    )
]

print()
print("QUERY")
print("-" * 100)
print("query_index =", query_index)
print("regime      =", current.regime)
print("event       =", current.structure_event)
print("sequence    =", current.sequence_state)
print("location    =", current.location)
print("momentum    =", current.momentum_state)
print("trend       =", current.trend)
print("high_label  =", current.high_label)
print("low_label   =", current.low_label)
print()

print("eligible    =", len(eligible))
print("compatible  =", len(compatible))

# ================================================================
# 7. TOP RAW SIMILARITY COMPONENTS
# ================================================================

scored = []

for record in m.coarse_filter(current, records, query_index):
    components = m.similarity_score(current, record)

    scored.append(
        (
            components["total"],
            record.index,
            record,
            components,
        )
    )

scored.sort(key=lambda x: (x[0], x[1]), reverse=True)

print()
print("=" * 100)
print("TOP 20 RAW CANDIDATES — COMPONENT BREAKDOWN")
print("=" * 100)

for rank, (total, index, record, c) in enumerate(scored[:20], 1):

    print()
    print(f"RANK {rank}")
    print("-" * 100)

    print(
        f"index={index} "
        f"episode={record.episode_id} "
        f"total={total:.6f}"
    )

    print(
        f"structure={c['structure']:.3f} "
        f"sequence={c['sequence']:.3f} "
        f"regime={c['regime']:.3f} "
        f"location={c['location']:.3f}"
    )

    print(
        f"momentum={c['momentum']:.3f} "
        f"volatility={c['volatility']:.3f} "
        f"candle={c['candle']:.3f} "
        f"path={c['path']:.3f}"
    )

    print(
        "record state: "
        f"regime={record.regime} "
        f"event={record.structure_event} "
        f"sequence={record.sequence_state} "
        f"location={record.location} "
        f"momentum={record.momentum_state}"
    )

    print(
        "outcome:",
        record.outcome.direction,
        "atr_return=",
        record.outcome.atr_return,
    )

# ================================================================
# 8. COMPONENT STATISTICS
# ================================================================

print()
print("=" * 100)
print("COMPONENT STATISTICS — ALL RAW CANDIDATES")
print("=" * 100)

component_names = [
    "total",
    "structure",
    "sequence",
    "regime",
    "location",
    "momentum",
    "volatility",
    "candle",
    "path",
]

for name in component_names:
    values = [item[3][name] if name != "total" else item[0] for item in scored]

    if values:
        print(
            f"{name:<14} "
            f"min={min(values):.6f} "
            f"mean={sum(values)/len(values):.6f} "
            f"max={max(values):.6f}"
        )

# ================================================================
# 9. SELECTED REPRESENTATIVES
# ================================================================

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
    for _, _, record, components in scored
]

selected = m.select_episode_representatives(matches)

print()
print("=" * 100)
print("EPISODE DEDUPLICATION")
print("=" * 100)

print("raw candidates =", len(matches))
print("selected       =", len(selected))

print()
print("SELECTED MATCHES:")

for rank, match in enumerate(selected, 1):
    print(
        f"{rank:02d}. "
        f"index={match.index:<4} "
        f"episode={match.episode_id:<4} "
        f"similarity={match.similarity:.6f}"
    )

# ================================================================
# 10. FINAL
# ================================================================

print()
print("=" * 100)
print("AUDIT COMPLETE")
print("=" * 100)
