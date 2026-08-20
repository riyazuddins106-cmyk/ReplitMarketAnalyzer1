import math
import mlai_market_structure_v416 as m

print("=" * 110)
print("MLAI v4.1.6 — PATH → FUTURE OUTCOME FORENSIC TEST")
print("=" * 110)

# ---------------------------------------------------------------
# 1. Production data/state construction
# ---------------------------------------------------------------

candles, invalid_count = m.load_market_data(m.MARKET_DATA_FILE)

structure_engine = m.CausalStructureEngine(candles)
structure_states = structure_engine.build()

atr = m.calculate_atr(candles)

market_states = m.build_market_states(
    candles,
    structure_states,
    atr,
)

# ---------------------------------------------------------------
# 2. Query
# ---------------------------------------------------------------

query_index = 904
horizon = 4

query = market_states[query_index]

print()
print("QUERY")
print("-" * 110)
print("query index :", query_index)
print("horizon     :", horizon)
print("query close :", candles[query_index].close)

# ---------------------------------------------------------------
# 3. Build experience records
# ---------------------------------------------------------------

records = m.build_experience_records(
    candles,
    atr,
    market_states,
    {
        i: market_states[i].index
        for i in range(len(market_states))
    },
    0,
    query_index,
    horizon,
)

eligible = [
    r
    for r in records
    if r.index < query_index
    and query_index - r.index >= m.MIN_HISTORY_GAP
    and r.index + horizon < len(candles)
]

print()
print("ELIGIBLE HISTORICAL RECORDS")
print("-" * 110)
print("count:", len(eligible))

# ---------------------------------------------------------------
# 4. Define actual future return
# ---------------------------------------------------------------

def future_return(index):
    if index + horizon >= len(candles):
        return None

    entry = candles[index].close
    future = candles[index + horizon].close

    if abs(entry) < 1e-12:
        return None

    return (future - entry) / entry


query_future = future_return(query_index)

print()
print("QUERY FUTURE OUTCOME")
print("-" * 110)
print("future return:", query_future)

# ---------------------------------------------------------------
# 5. Path similarity + historical future outcome
# ---------------------------------------------------------------

rows = []

for record in eligible:
    fr = future_return(record.index)

    if fr is None:
        continue

    ps = m.path_similarity(query, record)

    rows.append(
        {
            "index": record.index,
            "path": ps,
            "future_return": fr,
        }
    )

rows.sort(key=lambda x: x["path"], reverse=True)

print()
print("PATH / FUTURE SAMPLE")
print("-" * 110)

for row in rows[:20]:
    print(
        f"index={row['index']:4d} "
        f"path={row['path']:.6f} "
        f"future_return={row['future_return']:+.8f}"
    )

# ---------------------------------------------------------------
# 6. Correlation
# ---------------------------------------------------------------

path_values = [r["path"] for r in rows]
future_values = [r["future_return"] for r in rows]

mean_path = sum(path_values) / len(path_values)
mean_future = sum(future_values) / len(future_values)

cov = sum(
    (p - mean_path) * (f - mean_future)
    for p, f in zip(path_values, future_values)
)

var_path = sum(
    (p - mean_path) ** 2
    for p in path_values
)

var_future = sum(
    (f - mean_future) ** 2
    for f in future_values
)

if var_path > 0 and var_future > 0:
    correlation = cov / math.sqrt(var_path * var_future)
else:
    correlation = 0.0

print()
print("=" * 110)
print("PATH / FUTURE CORRELATION")
print("=" * 110)
print("correlation:", correlation)

# ---------------------------------------------------------------
# 7. Similarity buckets
# ---------------------------------------------------------------

print()
print("=" * 110)
print("PATH SIMILARITY BUCKETS")
print("=" * 110)

buckets = [
    ("TOP 10%", 0.90, 1.00),
    ("TOP 20%", 0.80, 0.90),
    ("0.70-0.80", 0.70, 0.80),
    ("0.60-0.70", 0.60, 0.70),
    ("0.50-0.60", 0.50, 0.60),
    ("<0.50", 0.00, 0.50),
]

for name, low, high in buckets:
    bucket = [
        r for r in rows
        if low <= r["path"] < high
    ]

    if not bucket:
        print(name, ": EMPTY")
        continue

    mean_future = sum(
        r["future_return"] for r in bucket
    ) / len(bucket)

    positive = sum(
        1 for r in bucket
        if r["future_return"] > 0
    )

    positive_rate = positive / len(bucket)

    print(
        f"{name:12s} "
        f"count={len(bucket):4d} "
        f"mean_future={mean_future:+.8f} "
        f"positive_rate={positive_rate:.4f}"
    )

# ---------------------------------------------------------------
# 8. Directional outcome agreement
# ---------------------------------------------------------------

query_direction = (
    1 if query_future > 0
    else -1 if query_future < 0
    else 0
)

print()
print("=" * 110)
print("PATH MATCH DIRECTION AGREEMENT")
print("=" * 110)
print("query direction:", query_direction)

for threshold in (0.50, 0.60, 0.65, 0.70, 0.75):

    selected = [
        r for r in rows
        if r["path"] >= threshold
    ]

    if not selected:
        print(f">= {threshold:.2f}: EMPTY")
        continue

    agreements = sum(
        1
        for r in selected
        if (
            (r["future_return"] > 0 and query_direction > 0)
            or
            (r["future_return"] < 0 and query_direction < 0)
            or
            (r["future_return"] == 0 and query_direction == 0)
        )
    )

    rate = agreements / len(selected)

    mean_future = sum(
        r["future_return"] for r in selected
    ) / len(selected)

    print(
        f">= {threshold:.2f} "
        f"count={len(selected):4d} "
        f"agreement={rate:.4f} "
        f"mean_future={mean_future:+.8f}"
    )

print()
print("=" * 110)
print("FORENSIC TEST COMPLETE — NO SOURCE FILES MODIFIED")
print("=" * 110)
