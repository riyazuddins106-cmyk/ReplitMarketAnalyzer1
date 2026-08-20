import mlai_market_structure_v416 as m

print("=" * 96)
print("MLAI v4.1.6 — RETRIEVAL PIPELINE DIAGNOSTIC")
print("=" * 96)

print()
print("CONFIG")
print("-" * 96)
print("RETRIEVAL_TOP_K       =", m.RETRIEVAL_TOP_K)
print("MIN_RETRIEVAL_MATCHES=", m.MIN_RETRIEVAL_MATCHES)
print("MIN_HISTORY_GAP      =", m.MIN_HISTORY_GAP)
print("EPISODE_GAP          =", m.EPISODE_GAP)
print("PATH_LENGTH           =", m.PATH_LENGTH)

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

print()
print("DATA")
print("-" * 96)
print("candles =", len(candles))
print("windows =", len(windows))

for window in windows[:2]:

    print()
    print("=" * 96)
    print(
        f"WINDOW {window.number} "
        f"TRAIN [{window.train_start}:{window.train_end}] "
        f"OOS [{window.oos_start}:{window.oos_end}]"
    )
    print("=" * 96)

    for horizon in m.HORIZONS:

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
        print(f"HORIZON {horizon}")
        print("-" * 96)
        print("training records =", len(records))

        if not records:
            print("NO RECORDS")
            continue

        for query_index in list(range(window.oos_start, window.oos_end))[:10]:

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

            retrieval = m.retrieve_historical_experience(
                current,
                records,
                horizon,
                query_index,
            )

            print()
            print(
                f"query={query_index} "
                f"regime={current.regime} "
                f"event={current.structure_event} "
                f"sequence={current.sequence_state}"
            )
            print(
                f"eligible={len(eligible)} "
                f"OR-compatible={len(compatible)} "
                f"selected={retrieval.deduplicated_matches}"
            )
            print(
                f"top_similarity={retrieval.top_similarity:.6f} "
                f"mean_similarity={retrieval.mean_similarity:.6f} "
                f"level={retrieval.level} "
                f"evidence={retrieval.evidence}"
            )
            print(
                f"shares: "
                f"UP={retrieval.up_share:.3f} "
                f"DOWN={retrieval.down_share:.3f} "
                f"NEUTRAL={retrieval.neutral_share:.3f}"
            )

            if retrieval.selected_match_indices:
                print(
                    "selected indices:",
                    retrieval.selected_match_indices[:10]
                )
