import mlai_market_structure_v416 as m
from collections import Counter

print("=" * 100)
print("MLAI v4.1.6 — RETRIEVAL DISCRIMINATIVE POWER AUDIT")
print("=" * 100)

# ================================================================
# 1. BUILD DATA
# ================================================================

candles, invalid = m.load_market_data(m.MARKET_DATA_FILE)

atr = m.calculate_atr(candles)

engine = m.CausalStructureEngine(candles)
structure_states = engine.build()

states = m.build_market_states(
    candles,
    structure_states,
    atr,
)

episode_ids = m.assign_episode_ids(states)

windows = m.create_walk_forward_windows(
    len(candles),
    m.DEFAULT_TRAIN_WINDOWS,
    m.DEFAULT_OOS_SIZE,
)

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

candidates = m.coarse_filter(
    current,
    records,
    query_index,
)

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
print("RAW CANDIDATES =", len(candidates))

# ================================================================
# 2. DISTINCT CATEGORICAL STATE COMBINATIONS
# ================================================================

def categorical_key(record):
    return (
        record.state_key[0],       # trend
        record.structure_event,
        record.state_key[2],       # high label
        record.state_key[3],       # low label
        record.sequence_state,
        record.regime,
        record.location,
        record.momentum_state,
    )

state_counter = Counter(
    categorical_key(record)
    for record in candidates
)

print()
print("=" * 100)
print("CATEGORICAL STATE DIVERSITY")
print("=" * 100)

print("unique categorical states =", len(state_counter))
print("raw candidates            =", len(candidates))

if state_counter:
    print(
        "average records/state     =",
        round(len(candidates) / len(state_counter), 3),
    )

print()
print("TOP 20 MOST REPEATED STATES")
print("-" * 100)

for rank, (key, count) in enumerate(
    state_counter.most_common(20),
    1,
):
    print()
    print(f"RANK {rank}")
    print("count =", count)
    print("state =", key)

# ================================================================
# 3. QUERY STATE FREQUENCY
# ================================================================

query_state = (
    current.trend,
    current.structure_event,
    current.high_label,
    current.low_label,
    current.sequence_state,
    current.regime,
    current.location,
    current.momentum_state,
)

print()
print("=" * 100)
print("QUERY STATE FREQUENCY")
print("=" * 100)

print("query state =", query_state)
print("historical occurrences =", state_counter.get(query_state, 0))

# ================================================================
# 4. TOP SIMILARITY DISTRIBUTION
# ================================================================

scored = []

for record in candidates:
    components = m.similarity_score(current, record)
    scored.append(
        (
            components["total"],
            record,
            components,
        )
    )

scored.sort(
    key=lambda x: (x[0], x[1].index),
    reverse=True,
)

print()
print("=" * 100)
print("SIMILARITY DISTRIBUTION")
print("=" * 100)

values = [x[0] for x in scored]

for threshold in (
    0.90,
    0.85,
    0.80,
    0.75,
    0.70,
    0.60,
    0.50,
):
    count = sum(v >= threshold for v in values)
    print(f">= {threshold:.2f} : {count}")

# ================================================================
# 5. NUMERIC FEATURE DISTRIBUTIONS
# ================================================================

print()
print("=" * 100)
print("NUMERIC FEATURE DISTRIBUTIONS — CANDIDATES")
print("=" * 100)

def stats(name, values):
    values = [float(v) for v in values]

    if not values:
        print(name, ": EMPTY")
        return

    print(
        f"{name:<25} "
        f"min={min(values):.8f} "
        f"mean={sum(values)/len(values):.8f} "
        f"max={max(values):.8f}"
    )

stats(
    "volatility_ratio",
    [r.volatility_ratio for r in candidates],
)

stats(
    "body_ratio",
    [r.body_ratio for r in candidates],
)

stats(
    "range_ratio",
    [r.range_ratio for r in candidates],
)

stats(
    "r1",
    [r.r1 for r in candidates],
)

stats(
    "r3",
    [r.r3 for r in candidates],
)

stats(
    "r8",
    [r.r8 for r in candidates],
)

stats(
    "r16",
    [r.r16 for r in candidates],
)

# ================================================================
# 6. PATH FEATURE DISTRIBUTIONS
# ================================================================

print()
print("=" * 100)
print("PATH VECTOR FEATURE DISTRIBUTIONS")
print("=" * 100)

path_returns = []
path_ranges = []
path_directions = []
path_bodies = []

for record in candidates:
    for row in record.path_vector:
        ret, rng, direction, body = row

        path_returns.append(ret)
        path_ranges.append(rng)
        path_directions.append(direction)
        path_bodies.append(body)

stats("path_return", path_returns)
stats("path_range", path_ranges)
stats("path_body", path_bodies)

print()
print("path directions =", Counter(path_directions))

# ================================================================
# 7. TOP MATCHES WITH NUMERIC DIFFERENCES
# ================================================================

print()
print("=" * 100)
print("TOP 10 MATCHES — NUMERIC FEATURE COMPARISON")
print("=" * 100)

for rank, (total, record, c) in enumerate(scored[:10], 1):

    print()
    print(f"RANK {rank}")
    print("-" * 100)

    print(
        "index=",
        record.index,
        "episode=",
        record.episode_id,
        "similarity=",
        round(total, 6),
    )

    print(
        "volatility:",
        round(current.volatility_ratio, 6),
        "vs",
        round(record.volatility_ratio, 6),
    )

    print(
        "body:",
        round(current.body_ratio, 6),
        "vs",
        round(record.body_ratio, 6),
    )

    print(
        "range:",
        round(current.range_ratio, 6),
        "vs",
        round(record.range_ratio, 6),
    )

    print(
        "r1:",
        round(current.r1, 6),
        "vs",
        round(record.r1, 6),
    )

    print(
        "r3:",
        round(current.r3, 6),
        "vs",
        round(record.r3, 6),
    )

    print(
        "r8:",
        round(current.r8, 6),
        "vs",
        round(record.r8, 6),
    )

    print(
        "r16:",
        round(current.r16, 6),
        "vs",
        round(record.r16, 6),
    )

    print(
        "components:",
        {
            k: round(v, 6)
            for k, v in c.items()
        }
    )

print()
print("=" * 100)
print("AUDIT COMPLETE")
print("=" * 100)

