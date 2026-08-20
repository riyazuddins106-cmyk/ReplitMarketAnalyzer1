import mlai_market_structure_v416 as m

print("=" * 110)
print("MLAI v4.1.6 — PATH DISCRIMINATION FORENSIC TEST")
print("=" * 110)

# ----------------------------------------------------------------
# 1. Correctly unpack production loader
# ----------------------------------------------------------------

candles, invalid_count = m.load_market_data(m.MARKET_DATA_FILE)

print()
print("DATA")
print("-" * 110)
print("candles type :", type(candles).__name__)
print("candles count:", len(candles))
print("invalid count:", invalid_count)
print("first type   :", type(candles[0]).__name__)

# ----------------------------------------------------------------
# 2. Production ATR / structure / market states
# ----------------------------------------------------------------

atr = m.calculate_atr(candles)

structure_states = m.build_structure_states(candles)

market_states = m.build_market_states(
    candles,
    structure_states,
    atr,
)

print()
print("STATE BUILD")
print("-" * 110)
print("ATR count            :", len(atr))
print("structure states     :", len(structure_states))
print("market states        :", len(market_states))
print("PATH_LENGTH          :", m.PATH_LENGTH)

# ----------------------------------------------------------------
# 3. Query
# ----------------------------------------------------------------

query_index = 904
query = market_states[query_index]

print()
print("QUERY")
print("-" * 110)
print("query index          :", query_index)
print("query path length    :", len(query.path_vector))

# ----------------------------------------------------------------
# 4. Production experience records
# ----------------------------------------------------------------

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
    4,
)

eligible = [
    r
    for r in records
    if r.index < query_index
    and query_index - r.index >= m.MIN_HISTORY_GAP
]

print()
print("EXPERIENCE RECORDS")
print("-" * 110)
print("records              :", len(records))
print("MIN_HISTORY_GAP      :", m.MIN_HISTORY_GAP)
print("eligible              :", len(eligible))

# ----------------------------------------------------------------
# 5. Path similarity
# ----------------------------------------------------------------

path_scores = []

for record in eligible:
    score = m.path_similarity(query, record)
    path_scores.append((score, record))

path_scores.sort(key=lambda x: x[0], reverse=True)

scores = [score for score, _ in path_scores]

print()
print("PATH SCORE DISTRIBUTION")
print("-" * 110)
print("min                  :", min(scores))
print("mean                 :", sum(scores) / len(scores))
print("max                  :", max(scores))

for threshold in (0.50, 0.60, 0.70, 0.75, 0.80, 0.85, 0.90):
    count = sum(1 for score in scores if score >= threshold)
    print(f">= {threshold:.2f}             :", count)

# ----------------------------------------------------------------
# 6. Top 20 path matches
# ----------------------------------------------------------------

print()
print("=" * 110)
print("TOP 20 PATH MATCHES")
print("=" * 110)

for rank, (path_score, record) in enumerate(path_scores[:20], 1):

    components = m.similarity_score(query, record)

    print(
        f"{rank:02d} "
        f"index={record.index:4d} "
        f"episode={record.episode_id:4d} "
        f"path={path_score:.6f} "
        f"total={components['total']:.6f}"
    )

# ----------------------------------------------------------------
# 7. Best match row-level inspection
# ----------------------------------------------------------------

best_score, best_record = path_scores[0]

print()
print("=" * 110)
print("BEST PATH MATCH")
print("=" * 110)

print("historical index     :", best_record.index)
print("episode              :", best_record.episode_id)
print("path similarity      :", best_score)

print()
print("ROW SCORES")
print("-" * 110)

row_total = 0.0

for i, (current_row, historical_row) in enumerate(
    zip(query.path_vector, best_record.path_vector)
):

    row_score = m.path_row_similarity(
        current_row,
        historical_row,
    )

    row_total += row_score

    print(
        f"{i}: "
        f"score={row_score:.6f} "
        f"current=({current_row[0]:.4f},"
        f"{current_row[1]:.4f},"
        f"{current_row[2]:.1f},"
        f"{current_row[3]:.4f}) "
        f"historical=({historical_row[0]:.4f},"
        f"{historical_row[1]:.4f},"
        f"{historical_row[2]:.1f},"
        f"{historical_row[3]:.4f})"
    )

print()
print("row mean             :", row_total / len(query.path_vector))
print("path_similarity      :", m.path_similarity(query, best_record))

# ----------------------------------------------------------------
# 8. Discrimination test
# ----------------------------------------------------------------

rows = []

for path_score, record in path_scores:

    components = m.similarity_score(query, record)

    rows.append(
        (
            path_score,
            components["total"],
            record.index,
        )
    )

rows_by_total = sorted(
    rows,
    key=lambda x: x[1],
    reverse=True,
)

top_n = min(40, len(rows_by_total))

top_group = rows_by_total[:top_n]
bottom_group = rows_by_total[-top_n:]

top_mean_path = sum(x[0] for x in top_group) / len(top_group)
bottom_mean_path = sum(x[0] for x in bottom_group) / len(bottom_group)

print()
print("=" * 110)
print("PATH DISCRIMINATION")
print("=" * 110)

print("group size           :", top_n)
print("top-total mean path  :", top_mean_path)
print("bottom-total mean    :", bottom_mean_path)
print("difference            :", top_mean_path - bottom_mean_path)

print()
print("=" * 110)
print("FORENSIC TEST COMPLETE — NO SOURCE FILES MODIFIED")
print("=" * 110)

