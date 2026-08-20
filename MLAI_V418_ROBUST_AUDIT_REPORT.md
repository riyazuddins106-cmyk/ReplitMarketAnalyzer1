# MLAI V4.1.8 Robust Retrieval Audit Report

Generated: `2026-08-20T08:07:09.127831`

## Build decision

**V4.1.8 BUILD: REFUSED / NOT CREATED**

## Protection

- V4.1.7 source is never modified.
- market_data.bin is never modified.
- Existing memory files are never modified.
- Production files are never modified.

## Source

- Source: `mlai_market_structure_v417.py`
- Source SHA256: `8fbe7510abf83ccf70ebd79ee582310050645f747c8c7b1e775e0079d4c14d0e`
- Source lines: `5924`

## Audit checks

- **PASS** Source exists: Found mlai_market_structure_v417.py.
- **PASS** V4.1.7 version: VERSION = "4.1.7" confirmed.
- **PASS** Python AST validation: V4.1.7 parses successfully.
- **PASS** Retrieval function uniqueness: Exactly one retrieve_historical_experience() found at lines 2585-3013.
- **PASS** Similarity-related representation: Found 35 similarity-related AST/source references.
- **WARN** Exact similarity field access: Multiple similarity accesses were found. Automatic repair will not guess which one is authoritative.
- **PASS** Similarity-to-selected-row binding: Similarity field match.similarity is evaluated from selected_rows iterator object 'match'.
- **PASS** Historical candidate generation: Found 16 candidate-related assignments.
- **PASS** Retrieval ranking/selection: Found 2 sorting/selection structures.
- **PASS** Existing sparse classification: Original TOP-K sparse classification block found.
- **PASS** Existing sparse evidence: Original TOP-K sparse evidence block found.
- **PASS** Existing sparse_warning: Original TOP-K sparse_warning block found.
- **WARN** H4 structural reference: No explicit H4 reference inside retrieval function.
- **WARN** H8 structural reference: No explicit H8 reference inside retrieval function.
- **WARN** H16 structural reference: No explicit H16 reference inside retrieval function.
- **PASS** Outcome aggregation: Found 41 outcome-related structures.
- **WARN** Causality screen: Causality-related constructs were found, but AST discovery alone cannot prove that no future information enters retrieval.
- **PASS** Predictive decision integration: Found 5 integration reference(s).
- **PASS** Retrieval return contract: Found 2 return statement(s).
- **FAIL** Automatic sparse repair safety: Automatic repair is refused because the source does not simultaneously prove the exact sparse blocks and an unambiguous similarity field bound to selected historical matches.
- **WARN** V4.1.8 file creation: BUILD REFUSED. No V4.1.8 file was created.

## Discovered architecture

### retrieval_function_lines

```text
2585-3013
```

### retrieval_function_size

```text
429
```

### similarity_discovery

```text
[
  {
    "kind": "name",
    "name": "top_similarity",
    "line": 2790
  },
  {
    "kind": "attribute",
    "name": "similarity",
    "line": 2790
  },
  {
    "kind": "name",
    "name": "mean_similarity",
    "line": 2794
  },
  {
    "kind": "name",
    "name": "SimilarityMatch",
    "line": 2593
  },
  {
    "kind": "name",
    "name": "mean_similarity",
    "line": 2971
  },
  {
    "kind": "name",
    "name": "similarity_score",
    "line": 2604
  },
  {
    "kind": "attribute",
    "name": "match.similarity",
    "line": 2714
  },
  {
    "kind": "attribute",
    "name": "match.similarity",
    "line": 2796
  },
  {
    "kind": "attribute",
    "name": "match.regime_similarity",
    "line": 2804
  },
  {
    "kind": "attribute",
    "name": "match.structure_similarity",
    "line": 2812
  },
  {
    "kind": "name",
    "name": "top_similarity",
    "line": 2889
  },
  {
    "kind": "name",
    "name": "top_similarity",
    "line": 2912
  },
  {
    "kind": "name",
    "name": "top_similarity",
    "line": 2981
  },
  {
    "kind": "name",
    "name": "mean_similarity",
    "line": 2982
  },
  {
    "kind": "name",
    "name": "SimilarityMatch",
    "line": 2610
  },
  {
    "kind": "name",
    "name": "top_similarity",
    "line": 2893
  },
  {
    "kind": "attribute",
    "name": "match.sequence_similarity",
    "line": 2930
  },
  {
    "kind": "attribute",
    "name": "match.location_similarity",
    "line": 2938
  },
  {
    "kind": "attribute",
    "name": "match.momentum_similarity",
    "line": 2945
  },
  {
    "kind": "attribute",
    "name": "match.volatility_similarity",
    "line": 2952
  },
  {
    "kind": "attribute",
    "name": "match.candle_similarity",
    "line": 2959
  },
  {
    "kind": "attribute",
    "name": "match.path_similarity",
    "line": 2966
  },
  {
    "kind": "attribute",
    "name": "item.similarity",
    "line": 2627
  },
  {
    "kind": "attribute",
    "name": "match.sequence_similarity",
    "line": 2822
  },
  {
    "kind": "attribute",
    "name": "match.regime_similarity",
    "line": 2823
  },
  {
    "kind": "attribute",
    "name": "match.location_similarity",
    "line": 2824
  },
  {
    "kind": "attribute",
    "name": "match.momentum_similarity",
    "line": 2825
  },
  {
    "kind": "attribute",
    "name": "match.path_similarity",
    "line": 2826
  },
  {
    "kind": "name",
    "name": "top_similarity",
    "line": 2897
  },
  {
    "kind": "call",
    "name": "similarity_score",
    "line": 2604,
    "source": "similarity_score(\n            current,\n            record,\n        )"
  },
  {
    "kind": "call",
    "name": "SimilarityMatch",
    "line": 2610,
    "source": "SimilarityMatch(\n                index=record.index,\n                episode_id=record.episode_id,\n                similarity=components[\"total\"],\n                structure_similarity=components[\"structure\"],\n                sequence_similarity=components[\"sequence\"],\n                regime_similarity=components[\"regime\"],\n                location_similarity=components[\"location\"],\n                momentum_similarity=components[\"momentum\"],\n                volatility_similarity=components[\"volat"
  },
  {
    "kind": "comparison",
    "line": 2889,
    "source": "top_similarity >= 0.80"
  },
  {
    "kind": "comparison",
    "line": 2912,
    "source": "top_similarity >= 0.70"
  },
  {
    "kind": "comparison",
    "line": 2893,
    "source": "top_similarity >= 0.70"
  },
  {
    "kind": "comparison",
    "line": 2897,
    "source": "top_similarity >= 0.60"
  }
]
```

### exact_similarity_access

```text
[
  {
    "object": "item",
    "pattern": "(?P<obj>[A-Za-z_][A-Za-z0-9_]*)\\.similarity\\b",
    "text": "item.similarity",
    "offset": 1189
  },
  {
    "object": "match",
    "pattern": "(?P<obj>[A-Za-z_][A-Za-z0-9_]*)\\.similarity\\b",
    "text": "match.similarity",
    "offset": 3348
  }
]
```

### similarity_binding

```text
Similarity field match.similarity is evaluated from selected_rows iterator object 'match'.
```

### candidate_generation

```text
[
  {
    "targets": [
      "raw_candidate_count"
    ],
    "line": 2633,
    "source": "raw_candidate_count = len(\n        candidates\n    )"
  },
  {
    "targets": [
      "selected"
    ],
    "line": 2637,
    "source": "selected = select_episode_representatives(\n        candidates\n    )"
  },
  {
    "targets": [
      "selected_rows"
    ],
    "line": 2646,
    "source": "selected_rows = [\n        (\n            match,\n            record_by_index[match.index],\n        )\n        for match in selected\n        if match.index in record_by_index\n    ]"
  },
  {
    "targets": [
      "candidate_records"
    ],
    "line": 2660,
    "source": "candidate_records = [\n        record_by_index[match.index]\n        for match in candidates\n        if match.index in record_by_index\n    ]"
  },
  {
    "targets": [
      "discrimination"
    ],
    "line": 2666,
    "source": "discrimination = calculate_retrieval_discrimination(\n        selected,\n        candidates,\n        selected_records,\n        candidate_records,\n    )"
  },
  {
    "targets": [
      "weights"
    ],
    "line": 2713,
    "source": "weights = [\n        match.similarity ** 2\n        for match, _ in selected_rows\n    ]"
  },
  {
    "targets": [
      "supporting_matches"
    ],
    "line": 2778,
    "source": "supporting_matches = sum(\n        1\n        for _, record in selected_rows\n        if record.outcome.direction\n        == dominant\n    )"
  },
  {
    "targets": [
      "conflicting_matches"
    ],
    "line": 2785,
    "source": "conflicting_matches = (\n        len(selected_rows)\n        - supporting_matches\n    )"
  },
  {
    "targets": [
      "top_similarity"
    ],
    "line": 2790,
    "source": "top_similarity = selected[\n        0\n    ].similarity"
  },
  {
    "targets": [
      "mean_similarity"
    ],
    "line": 2794,
    "source": "mean_similarity = mean_or_zero(\n        [\n            match.similarity\n            for match, _\n            in selected_rows\n        ]\n    )"
  },
  {
    "targets": [
      "regime_agreement"
    ],
    "line": 2802,
    "source": "regime_agreement = mean_or_zero(\n        [\n            match.regime_similarity\n            for match, _\n            in selected_rows\n        ]\n    )"
  },
  {
    "targets": [
      "structure_agreement"
    ],
    "line": 2810,
    "source": "structure_agreement = mean_or_zero(\n        [\n            match.structure_similarity\n            for match, _\n            in selected_rows\n        ]\n    )"
  },
  {
    "targets": [
      "context_agreement"
    ],
    "line": 2818,
    "source": "context_agreement = mean_or_zero(\n        [\n            mean_or_zero(\n                [\n                    match.sequence_similarity,\n                    match.regime_similarity,\n                    match.location_similarity,\n                    match.momentum_similarity,\n                    match.path_similarity,\n                ]\n            )\n            for match, _\n            in selected_rows\n        ]\n    )"
  },
  {
    "targets": [
      "representation"
    ],
    "line": 2926,
    "source": "representation = {\n        \"structure\": structure_agreement,\n        \"sequence\": mean_or_zero(\n            [\n                match.sequence_similarity\n                for match, _\n                in selected_rows\n            ]\n        ),\n        \"regime\": regime_agreement,\n        \"location\": mean_or_zero(\n            [\n                match.location_similarity\n                for match, _\n                in selected_rows\n            ]\n        ),\n        \"momentum\": mean_or_zero(\n            [\n                match.momentum_similarity\n                for match, _\n                in selected_rows\n            ]\n        ),\n        \"volatility\": mean_or_zero(\n            [\n                match.volatility_similarity\n                for match, _\n                in selected_rows\n            ]\n        ),\n        \"candle\": mean_or_zero(\n            [\n                match.candle_similarity\n                for match, _\n                in selected_rows\n            ]\n        ),\n        \"path\": me"
  },
  {
    "targets": [
      "components"
    ],
    "line": 2604,
    "source": "components = similarity_score(\n            current,\n            record,\n        )"
  },
  {
    "targets": [
      "level"
    ],
    "line": 2891,
    "source": "level = \"STRONG_SIMILARITY\""
  }
]
```

### ranking

```text
[
  {
    "kind": "sort",
    "name": "candidates.sort",
    "line": 2625,
    "source": "candidates.sort(\n        key=lambda item: (\n            item.similarity,\n            item.index,\n        ),\n        reverse=True,\n    )"
  },
  {
    "kind": "selection",
    "line": 2762,
    "source": "max(\n        (\n            \"UP\",\n            up_share,\n        ),\n        (\n            \"DOWN\",\n            down_share,\n        ),\n        (\n            \"NEUTRAL\",\n            neutral_share,\n        ),\n        key=lambda x: x[1],\n    )[0]"
  }
]
```

### horizons

```text
{
  "H4": [],
  "H8": [],
  "H16": []
}
```

### outcome_aggregation

```text
[
  {
    "line": 2633,
    "kind": "Assign",
    "source": "raw_candidate_count = len(\n        candidates\n    )"
  },
  {
    "line": 2720,
    "kind": "Assign",
    "source": "up_share = safe_div(\n        sum(\n            weight\n            for weight, (_, record)\n            in zip(\n                weights,\n                selected_rows,\n            )\n            if record.outcome.direction\n            == \"UP\"\n        ),\n        total_weight,\n    )"
  },
  {
    "line": 2734,
    "kind": "Assign",
    "source": "down_share = safe_div(\n        sum(\n            weight\n            for weight, (_, record)\n            in zip(\n                weights,\n                selected_rows,\n            )\n            if record.outcome.direction\n            == \"DOWN\"\n        ),\n        total_weight,\n    )"
  },
  {
    "line": 2748,
    "kind": "Assign",
    "source": "neutral_share = safe_div(\n        sum(\n            weight\n            for weight, (_, record)\n            in zip(\n                weights,\n                selected_rows,\n            )\n            if record.outcome.direction\n            == \"NEUTRAL\"\n        ),\n        total_weight,\n    )"
  },
  {
    "line": 2778,
    "kind": "Assign",
    "source": "supporting_matches = sum(\n        1\n        for _, record in selected_rows\n        if record.outcome.direction\n        == dominant\n    )"
  },
  {
    "line": 2794,
    "kind": "Assign",
    "source": "mean_similarity = mean_or_zero(\n        [\n            match.similarity\n            for match, _\n            in selected_rows\n        ]\n    )"
  },
  {
    "line": 2802,
    "kind": "Assign",
    "source": "regime_agreement = mean_or_zero(\n        [\n            match.regime_similarity\n            for match, _\n            in selected_rows\n        ]\n    )"
  },
  {
    "line": 2810,
    "kind": "Assign",
    "source": "structure_agreement = mean_or_zero(\n        [\n            match.structure_similarity\n            for match, _\n            in selected_rows\n        ]\n    )"
  },
  {
    "line": 2818,
    "kind": "Assign",
    "source": "context_agreement = mean_or_zero(\n        [\n            mean_or_zero(\n                [\n                    match.sequence_similarity,\n                    match.regime_similarity,\n                    match.location_similarity,\n                    match.momentum_similarity,\n                    match.path_similarity,\n                ]\n            )\n            for match, _\n            in selected_rows\n        ]\n    )"
  },
  {
    "line": 2834,
    "kind": "Assign",
    "source": "mean_atr_return = safe_div(\n        sum(\n            weight\n            * (\n                record.outcome.atr_return\n                or 0.0\n            )\n            for weight, (_, record)\n            in zip(\n                weights,\n                selected_rows,\n            )\n        ),\n        total_weight,\n    )"
  },
  {
    "line": 2850,
    "kind": "Assign",
    "source": "mean_mfe_atr = safe_div(\n        sum(\n            weight\n            * (\n                record.outcome.mfe_atr\n                or 0.0\n            )\n            for weight, (_, record)\n            in zip(\n                weights,\n                selected_rows,\n            )\n        ),\n        total_weight,\n    )"
  },
  {
    "line": 2866,
    "kind": "Assign",
    "source": "mean_mae_atr = safe_div(\n        sum(\n            weight\n            * (\n                record.outcome.mae_atr\n                or 0.0\n            )\n            for weight, (_, record)\n            in zip(\n                weights,\n                selected_rows,\n            )\n        ),\n        total_weight,\n    )"
  },
  {
    "line": 2926,
    "kind": "Assign",
    "source": "representation = {\n        \"structure\": structure_agreement,\n        \"sequence\": mean_or_zero(\n            [\n                match.sequence_similarity\n                for match, _\n                in selected_rows\n            ]\n        ),\n        \"regime\": regime_agreement,\n        \"location\": mean_or_zero(\n            [\n                match.location_similarity\n                for match, _\n                in selected_rows\n            ]\n        ),\n        \"momentum\": mean_or_zero(\n            [\n                match.momentum_similarity\n                for match, _\n                in selected_rows\n            ]\n        ),\n        \"volatility\": mean_or_zero(\n            [\n                match.volatility_similarity\n                for match, _\n                in selected_rows\n            ]\n        ),\n        \"candle\": mean_or_zero(\n            [\n                match.candle_similarity\n                for match, _\n                in selected_rows\n            ]\n        ),\n        \"path\": mean_or_zero(\n            [\n                match.path_similarity\n                for match, _\n                in selected_rows\n            ]\n        ),\n        \"total\": mean_similarity,\n    }"
  },
  {
    "line": 2974,
    "kind": "Return",
    "source": "return RetrievalResult(\n        horizon=horizon,\n        query_index=query_index,\n        raw_candidates=raw_candidate_count,\n        deduplicated_matches=len(\n            selected_rows\n        ),\n        top_similarity=top_similarity,\n        mean_similarity=mean_similarity,\n        level=level,\n        evidence=evidence,\n        sparse_warning=(\n            len(selected_rows)\n            < MIN_RETRIEVAL_MATCHES\n        ),\n        regime_agreement=regime_agreement,\n        structure_agreement=structure_agreement,\n        context_agreement=context_agreement,\n        up_share=up_share,\n        down_share=down_share,\n        neutral_share=neutral_share,\n        mean_atr_return=mean_atr_return,\n        mean_mfe_atr=mean_mfe_atr,\n        mean_mae_atr=mean_mae_atr,\n        supporting_matches=supporting_matches,\n        conflicting_matches=conflicting_matches,\n        historical_min_index=(\n            min(indices)\n            if indices\n            else None\n        ),\n        historical_max_index=(\n            max(indices)\n            if indices\n            else None\n        ),\n        selected_match_indices=indices,\n        similarity_representation=representation,\n        discriminat"
  },
  {
    "line": 2675,
    "kind": "Return",
    "source": "return RetrievalResult(\n            horizon=horizon,\n            query_index=query_index,\n            raw_candidates=raw_candidate_count,\n            deduplicated_matches=0,\n            top_similarity=0.0,\n            mean_similarity=0.0,\n            level=\"NONE\",\n            evidence=\"NONE\",\n            sparse_warning=True,\n            regime_agreement=0.0,\n            structure_agreement=0.0,\n            context_agreement=0.0,\n            up_share=0.0,\n            down_share=0.0,\n            neutral_share=0.0,\n            mean_atr_return=None,\n            mean_mfe_atr=None,\n            mean_mae_atr=None,\n            supporting_matches=0,\n            conflicting_matches=0,\n            historical_min_index=None,\n            historical_max_index=None,\n            selected_match_indices=[],\n            similarity_representation={\n                \"structure\": 0.0,\n                \"sequence\": 0.0,\n                \"regime\": 0.0,\n                \"location\": 0.0,\n                \"momentum\": 0.0,\n                \"volatility\": 0.0,\n                \"candle\": 0.0,\n                \"path\": 0.0,\n                \"total\": 0.0,\n            },\n            discrimination=_serialize_discrimination_res"
  },
  {
    "line": 2720,
    "kind": "Call",
    "source": "safe_div(\n        sum(\n            weight\n            for weight, (_, record)\n            in zip(\n                weights,\n                selected_rows,\n            )\n            if record.outcome.direction\n            == \"UP\"\n        ),\n        total_weight,\n    )"
  },
  {
    "line": 2734,
    "kind": "Call",
    "source": "safe_div(\n        sum(\n            weight\n            for weight, (_, record)\n            in zip(\n                weights,\n                selected_rows,\n            )\n            if record.outcome.direction\n            == \"DOWN\"\n        ),\n        total_weight,\n    )"
  },
  {
    "line": 2748,
    "kind": "Call",
    "source": "safe_div(\n        sum(\n            weight\n            for weight, (_, record)\n            in zip(\n                weights,\n                selected_rows,\n            )\n            if record.outcome.direction\n            == \"NEUTRAL\"\n        ),\n        total_weight,\n    )"
  },
  {
    "line": 2778,
    "kind": "Call",
    "source": "sum(\n        1\n        for _, record in selected_rows\n        if record.outcome.direction\n        == dominant\n    )"
  },
  {
    "line": 2794,
    "kind": "Call",
    "source": "mean_or_zero(\n        [\n            match.similarity\n            for match, _\n            in selected_rows\n        ]\n    )"
  },
  {
    "line": 2802,
    "kind": "Call",
    "source": "mean_or_zero(\n        [\n            match.regime_similarity\n            for match, _\n            in selected_rows\n        ]\n    )"
  },
  {
    "line": 2810,
    "kind": "Call",
    "source": "mean_or_zero(\n        [\n            match.structure_similarity\n            for match, _\n            in selected_rows\n        ]\n    )"
  },
  {
    "line": 2818,
    "kind": "Call",
    "source": "mean_or_zero(\n        [\n            mean_or_zero(\n                [\n                    match.sequence_similarity,\n                    match.regime_similarity,\n                    match.location_similarity,\n                    match.momentum_similarity,\n                    match.path_similarity,\n                ]\n            )\n            for match, _\n            in selected_rows\n        ]\n    )"
  },
  {
    "line": 2834,
    "kind": "Call",
    "source": "safe_div(\n        sum(\n            weight\n            * (\n                record.outcome.atr_return\n                or 0.0\n            )\n            for weight, (_, record)\n            in zip(\n                weights,\n                selected_rows,\n            )\n        ),\n        total_weight,\n    )"
  },
  {
    "line": 2850,
    "kind": "Call",
    "source": "safe_div(\n        sum(\n            weight\n            * (\n                record.outcome.mfe_atr\n                or 0.0\n            )\n            for weight, (_, record)\n            in zip(\n                weights,\n                selected_rows,\n            )\n        ),\n        total_weight,\n    )"
  },
  {
    "line": 2866,
    "kind": "Call",
    "source": "safe_div(\n        sum(\n            weight\n            * (\n                record.outcome.mae_atr\n                or 0.0\n            )\n            for weight, (_, record)\n            in zip(\n                weights,\n                selected_rows,\n            )\n        ),\n        total_weight,\n    )"
  },
  {
    "line": 2974,
    "kind": "Call",
    "source": "RetrievalResult(\n        horizon=horizon,\n        query_index=query_index,\n        raw_candidates=raw_candidate_count,\n        deduplicated_matches=len(\n            selected_rows\n        ),\n        top_similarity=top_similarity,\n        mean_similarity=mean_similarity,\n        level=level,\n        evidence=evidence,\n        sparse_warning=(\n            len(selected_rows)\n            < MIN_RETRIEVAL_MATCHES\n        ),\n        regime_agreement=regime_agreement,\n        structure_agreement=structure_agreement,\n        context_agreement=context_agreement,\n        up_share=up_share,\n        down_share=down_share,\n        neutral_share=neutral_share,\n        mean_atr_return=mean_atr_return,\n        mean_mfe_atr=mean_mfe_atr,\n        mean_mae_atr=mean_mae_atr,\n        supporting_matches=supporting_matches,\n        conflicting_matches=conflicting_matches,\n        historical_min_index=(\n            min(indices)\n            if indices\n            else None\n        ),\n        historical_max_index=(\n            max(indices)\n            if indices\n            else None\n        ),\n        selected_match_indices=indices,\n        similarity_representation=representation,\n        discrimination=_se"
  },
  {
    "line": 2675,
    "kind": "Call",
    "source": "RetrievalResult(\n            horizon=horizon,\n            query_index=query_index,\n            raw_candidates=raw_candidate_count,\n            deduplicated_matches=0,\n            top_similarity=0.0,\n            mean_similarity=0.0,\n            level=\"NONE\",\n            evidence=\"NONE\",\n            sparse_warning=True,\n            regime_agreement=0.0,\n            structure_agreement=0.0,\n            context_agreement=0.0,\n            up_share=0.0,\n            down_share=0.0,\n            neutral_share=0.0,\n            mean_atr_return=None,\n            mean_mfe_atr=None,\n            mean_mae_atr=None,\n            supporting_matches=0,\n            conflicting_matches=0,\n            historical_min_index=None,\n            historical_max_index=None,\n            selected_match_indices=[],\n            similarity_representation={\n                \"structure\": 0.0,\n                \"sequence\": 0.0,\n                \"regime\": 0.0,\n                \"location\": 0.0,\n                \"momentum\": 0.0,\n                \"volatility\": 0.0,\n                \"candle\": 0.0,\n                \"path\": 0.0,\n                \"total\": 0.0,\n            },\n            discrimination=_serialize_discrimination_result(dis"
  },
  {
    "line": 2721,
    "kind": "Call",
    "source": "sum(\n            weight\n            for weight, (_, record)\n            in zip(\n                weights,\n                selected_rows,\n            )\n            if record.outcome.direction\n            == \"UP\"\n        )"
  },
  {
    "line": 2735,
    "kind": "Call",
    "source": "sum(\n            weight\n            for weight, (_, record)\n            in zip(\n                weights,\n                selected_rows,\n            )\n            if record.outcome.direction\n            == \"DOWN\"\n        )"
  },
  {
    "line": 2749,
    "kind": "Call",
    "source": "sum(\n            weight\n            for weight, (_, record)\n            in zip(\n                weights,\n                selected_rows,\n            )\n            if record.outcome.direction\n            == \"NEUTRAL\"\n        )"
  },
  {
    "line": 2835,
    "kind": "Call",
    "source": "sum(\n            weight\n            * (\n                record.outcome.atr_return\n                or 0.0\n            )\n            for weight, (_, record)\n            in zip(\n                weights,\n                selected_rows,\n            )\n        )"
  },
  {
    "line": 2851,
    "kind": "Call",
    "source": "sum(\n            weight\n            * (\n                record.outcome.mfe_atr\n                or 0.0\n            )\n            for weight, (_, record)\n            in zip(\n                weights,\n                selected_rows,\n            )\n        )"
  },
  {
    "line": 2867,
    "kind": "Call",
    "source": "sum(\n            weight\n            * (\n                record.outcome.mae_atr\n                or 0.0\n            )\n            for weight, (_, record)\n            in zip(\n                weights,\n                selected_rows,\n            )\n        )"
  },
  {
    "line": 2928,
    "kind": "Call",
    "source": "mean_or_zero(\n            [\n                match.sequence_similarity\n                for match, _\n                in selected_rows\n            ]\n        )"
  },
  {
    "line": 2936,
    "kind": "Call",
    "source": "mean_or_zero(\n            [\n                match.location_similarity\n                for match, _\n                in selected_rows\n            ]\n        )"
  },
  {
    "line": 2943,
    "kind": "Call",
    "source": "mean_or_zero(\n            [\n                match.momentum_similarity\n                for match, _\n                in selected_rows\n            ]\n        )"
  },
  {
    "line": 2950,
    "kind": "Call",
    "source": "mean_or_zero(\n            [\n                match.volatility_similarity\n                for match, _\n                in selected_rows\n            ]\n        )"
  },
  {
    "line": 2957,
    "kind": "Call",
    "source": "mean_or_zero(\n            [\n                match.candle_similarity\n                for match, _\n                in selected_rows\n            ]\n        )"
  },
  {
    "line": 2964,
    "kind": "Call",
    "source": "mean_or_zero(\n            [\n                match.path_similarity\n                for match, _\n                in selected_rows\n            ]\n        )"
  },
  {
    "line": 2820,
    "kind": "Call",
    "source": "mean_or_zero(\n                [\n                    match.sequence_similarity,\n                    match.regime_similarity,\n                    match.location_similarity,\n                    match.momentum_similarity,\n                    match.path_similarity,\n                ]\n            )"
  }
]
```

### causality_signals

```text
[
  {
    "line": 2585,
    "kind": "FunctionDef",
    "source": "def retrieve_historical_experience(\n    current: MarketState,\n    records: Sequence[ExperienceRecord],\n    horizon: int,\n    query_index: int,\n) -> RetrievalResult:\n\n    candidates: List[\n        SimilarityMatch\n    ] = []\n\n    coarse_records = coarse_filter(\n        current,\n        records,\n        query_index,\n    )\n\n    for record in coarse_records:\n\n        components = similarity_score(\n            current,\n            record,\n        )\n\n        candidates.append(\n            SimilarityMatch(\n                index=record.index,\n                episode_id=record.episode_id,\n                similarity=components[\"total\"],\n                structure_similarity=components[\"structure\"],\n                sequence_similarity=components[\"sequence\"],\n                regime_similarity=components[\"regime\"],\n                location_similarity=components[\"location\"],\n                momentum_sim"
  },
  {
    "line": 2596,
    "kind": "Assign",
    "source": "coarse_records = coarse_filter(\n        current,\n        records,\n        query_index,\n    )"
  },
  {
    "line": 2602,
    "kind": "For",
    "source": "for record in coarse_records:\n\n        components = similarity_score(\n            current,\n            record,\n        )\n\n        candidates.append(\n            SimilarityMatch(\n                index=record.index,\n                episode_id=record.episode_id,\n                similarity=components[\"total\"],\n                structure_similarity=components[\"structure\"],\n                sequence_similarity=components[\"sequence\"],\n                regime_similarity=components[\"regime\"],\n                location_similarity=components[\"location\"],\n                momentum_similarity=components[\"momentum\"],\n                volatility_similarity=components[\"volatility\"],\n                candle_similarity=components[\"candle\"],\n                path_similarity=components[\"path\"],\n            )\n        )"
  },
  {
    "line": 2625,
    "kind": "Expr",
    "source": "candidates.sort(\n        key=lambda item: (\n            item.similarity,\n            item.index,\n        ),\n        reverse=True,\n    )"
  },
  {
    "line": 2641,
    "kind": "Assign",
    "source": "record_by_index = {\n        record.index: record\n        for record in records\n    }"
  },
  {
    "line": 2646,
    "kind": "Assign",
    "source": "selected_rows = [\n        (\n            match,\n            record_by_index[match.index],\n        )\n        for match in selected\n        if match.index in record_by_index\n    ]"
  },
  {
    "line": 2660,
    "kind": "Assign",
    "source": "candidate_records = [\n        record_by_index[match.index]\n        for match in candidates\n        if match.index in record_by_index\n    ]"
  },
  {
    "line": 2673,
    "kind": "If",
    "source": "if not selected_rows:\n\n        return RetrievalResult(\n            horizon=horizon,\n            query_index=query_index,\n            raw_candidates=raw_candidate_count,\n            deduplicated_matches=0,\n            top_similarity=0.0,\n            mean_similarity=0.0,\n            level=\"NONE\",\n            evidence=\"NONE\",\n            sparse_warning=True,\n            regime_agreement=0.0,\n            structure_agreement=0.0,\n            context_agreement=0.0,\n            up_share=0.0,\n            down_share=0.0,\n            neutral_share=0.0,\n            mean_atr_return=None,\n            mean_mfe_atr=None,\n            mean_mae_atr=None,\n            supporting_matches=0,\n            conflicting_matches=0,\n            historical_min_index=None,\n            historical_max_index=None,\n            selected_match_indices=[],\n            similarity_representation={\n                \"structure\": "
  },
  {
    "line": 2720,
    "kind": "Assign",
    "source": "up_share = safe_div(\n        sum(\n            weight\n            for weight, (_, record)\n            in zip(\n                weights,\n                selected_rows,\n            )\n            if record.outcome.direction\n            == \"UP\"\n        ),\n        total_weight,\n    )"
  },
  {
    "line": 2734,
    "kind": "Assign",
    "source": "down_share = safe_div(\n        sum(\n            weight\n            for weight, (_, record)\n            in zip(\n                weights,\n                selected_rows,\n            )\n            if record.outcome.direction\n            == \"DOWN\"\n        ),\n        total_weight,\n    )"
  },
  {
    "line": 2748,
    "kind": "Assign",
    "source": "neutral_share = safe_div(\n        sum(\n            weight\n            for weight, (_, record)\n            in zip(\n                weights,\n                selected_rows,\n            )\n            if record.outcome.direction\n            == \"NEUTRAL\"\n        ),\n        total_weight,\n    )"
  },
  {
    "line": 2778,
    "kind": "Assign",
    "source": "supporting_matches = sum(\n        1\n        for _, record in selected_rows\n        if record.outcome.direction\n        == dominant\n    )"
  },
  {
    "line": 2834,
    "kind": "Assign",
    "source": "mean_atr_return = safe_div(\n        sum(\n            weight\n            * (\n                record.outcome.atr_return\n                or 0.0\n            )\n            for weight, (_, record)\n            in zip(\n                weights,\n                selected_rows,\n            )\n        ),\n        total_weight,\n    )"
  },
  {
    "line": 2850,
    "kind": "Assign",
    "source": "mean_mfe_atr = safe_div(\n        sum(\n            weight\n            * (\n                record.outcome.mfe_atr\n                or 0.0\n            )\n            for weight, (_, record)\n            in zip(\n                weights,\n                selected_rows,\n            )\n        ),\n        total_weight,\n    )"
  },
  {
    "line": 2866,
    "kind": "Assign",
    "source": "mean_mae_atr = safe_div(\n        sum(\n            weight\n            * (\n                record.outcome.mae_atr\n                or 0.0\n            )\n            for weight, (_, record)\n            in zip(\n                weights,\n                selected_rows,\n            )\n        ),\n        total_weight,\n    )"
  },
  {
    "line": 2920,
    "kind": "Assign",
    "source": "indices = [\n        record.index\n        for _, record\n        in selected_rows\n    ]"
  },
  {
    "line": 2974,
    "kind": "Return",
    "source": "return RetrievalResult(\n        horizon=horizon,\n        query_index=query_index,\n        raw_candidates=raw_candidate_count,\n        deduplicated_matches=len(\n            selected_rows\n        ),\n        top_similarity=top_similarity,\n        mean_similarity=mean_similarity,\n        level=level,\n        evidence=evidence,\n        sparse_warning=(\n            len(selected_rows)\n            < MIN_RETRIEVAL_MATCHES\n        ),\n        regime_agreement=regime_agreement,\n        structure_agreement=structure_agreement,\n        context_agreement=context_agreement,\n        up_share=up_share,\n        down_share=down_share,\n        neutral_share=neutral_share,\n        mean_atr_return=mean_atr_return,\n        mean_mfe_atr=mean_mfe_atr,\n        mean_mae_atr=mean_mae_atr,\n        supporting_matches=supporting_matches,\n        conflicting_matches=conflicting_matches,\n        historical_min_index=(\n  "
  },
  {
    "line": 2589,
    "kind": "arg",
    "source": "query_index: int"
  },
  {
    "line": 2596,
    "kind": "Call",
    "source": "coarse_filter(\n        current,\n        records,\n        query_index,\n    )"
  },
  {
    "line": 2609,
    "kind": "Expr",
    "source": "candidates.append(\n            SimilarityMatch(\n                index=record.index,\n                episode_id=record.episode_id,\n                similarity=components[\"total\"],\n                structure_similarity=components[\"structure\"],\n                sequence_similarity=components[\"sequence\"],\n                regime_similarity=components[\"regime\"],\n                location_similarity=components[\"location\"],\n                momentum_similarity=components[\"momentum\"],\n                volatility_similarity=components[\"volatility\"],\n                candle_similarity=components[\"candle\"],\n                path_similarity=components[\"path\"],\n            )\n        )"
  },
  {
    "line": 2625,
    "kind": "Call",
    "source": "candidates.sort(\n        key=lambda item: (\n            item.similarity,\n            item.index,\n        ),\n        reverse=True,\n    )"
  },
  {
    "line": 2641,
    "kind": "Name",
    "source": "record_by_index"
  },
  {
    "line": 2641,
    "kind": "DictComp",
    "source": "{\n        record.index: record\n        for record in records\n    }"
  },
  {
    "line": 2646,
    "kind": "ListComp",
    "source": "[\n        (\n            match,\n            record_by_index[match.index],\n        )\n        for match in selected\n        if match.index in record_by_index\n    ]"
  },
  {
    "line": 2660,
    "kind": "ListComp",
    "source": "[\n        record_by_index[match.index]\n        for match in candidates\n        if match.index in record_by_index\n    ]"
  },
  {
    "line": 2675,
    "kind": "Return",
    "source": "return RetrievalResult(\n            horizon=horizon,\n            query_index=query_index,\n            raw_candidates=raw_candidate_count,\n            deduplicated_matches=0,\n            top_similarity=0.0,\n            mean_similarity=0.0,\n            level=\"NONE\",\n            evidence=\"NONE\",\n            sparse_warning=True,\n            regime_agreement=0.0,\n            structure_agreement=0.0,\n            context_agreement=0.0,\n            up_share=0.0,\n            down_share=0.0,\n            neutral_share=0.0,\n            mean_atr_return=None,\n            mean_mfe_atr=None,\n            mean_mae_atr=None,\n            supporting_matches=0,\n            conflicting_matches=0,\n            historical_min_index=None,\n            historical_max_index=None,\n            selected_match_indices=[],\n            similarity_representation={\n                \"structure\": 0.0,\n                \"sequence\""
  },
  {
    "line": 2720,
    "kind": "Call",
    "source": "safe_div(\n        sum(\n            weight\n            for weight, (_, record)\n            in zip(\n                weights,\n                selected_rows,\n            )\n            if record.outcome.direction\n            == \"UP\"\n        ),\n        total_weight,\n    )"
  },
  {
    "line": 2734,
    "kind": "Call",
    "source": "safe_div(\n        sum(\n            weight\n            for weight, (_, record)\n            in zip(\n                weights,\n                selected_rows,\n            )\n            if record.outcome.direction\n            == \"DOWN\"\n        ),\n        total_weight,\n    )"
  },
  {
    "line": 2748,
    "kind": "Call",
    "source": "safe_div(\n        sum(\n            weight\n            for weight, (_, record)\n            in zip(\n                weights,\n                selected_rows,\n            )\n            if record.outcome.direction\n            == \"NEUTRAL\"\n        ),\n        total_weight,\n    )"
  },
  {
    "line": 2778,
    "kind": "Call",
    "source": "sum(\n        1\n        for _, record in selected_rows\n        if record.outcome.direction\n        == dominant\n    )"
  },
  {
    "line": 2834,
    "kind": "Call",
    "source": "safe_div(\n        sum(\n            weight\n            * (\n                record.outcome.atr_return\n                or 0.0\n            )\n            for weight, (_, record)\n            in zip(\n                weights,\n                selected_rows,\n            )\n        ),\n        total_weight,\n    )"
  },
  {
    "line": 2850,
    "kind": "Call",
    "source": "safe_div(\n        sum(\n            weight\n            * (\n                record.outcome.mfe_atr\n                or 0.0\n            )\n            for weight, (_, record)\n            in zip(\n                weights,\n                selected_rows,\n            )\n        ),\n        total_weight,\n    )"
  },
  {
    "line": 2866,
    "kind": "Call",
    "source": "safe_div(\n        sum(\n            weight\n            * (\n                record.outcome.mae_atr\n                or 0.0\n            )\n            for weight, (_, record)\n            in zip(\n                weights,\n                selected_rows,\n            )\n        ),\n        total_weight,\n    )"
  },
  {
    "line": 2920,
    "kind": "ListComp",
    "source": "[\n        record.index\n        for _, record\n        in selected_rows\n    ]"
  },
  {
    "line": 2974,
    "kind": "Call",
    "source": "RetrievalResult(\n        horizon=horizon,\n        query_index=query_index,\n        raw_candidates=raw_candidate_count,\n        deduplicated_matches=len(\n            selected_rows\n        ),\n        top_similarity=top_similarity,\n        mean_similarity=mean_similarity,\n        level=level,\n        evidence=evidence,\n        sparse_warning=(\n            len(selected_rows)\n            < MIN_RETRIEVAL_MATCHES\n        ),\n        regime_agreement=regime_agreement,\n        structure_agreement=structure_agreement,\n        context_agreement=context_agreement,\n        up_share=up_share,\n        down_share=down_share,\n        neutral_share=neutral_share,\n        mean_atr_return=mean_atr_return,\n        mean_mfe_atr=mean_mfe_atr,\n        mean_mae_atr=mean_mae_atr,\n        supporting_matches=supporting_matches,\n        conflicting_matches=conflicting_matches,\n        historical_min_index=(\n         "
  },
  {
    "line": 2599,
    "kind": "Name",
    "source": "query_index"
  },
  {
    "line": 2609,
    "kind": "Call",
    "source": "candidates.append(\n            SimilarityMatch(\n                index=record.index,\n                episode_id=record.episode_id,\n                similarity=components[\"total\"],\n                structure_similarity=components[\"structure\"],\n                sequence_similarity=components[\"sequence\"],\n                regime_similarity=components[\"regime\"],\n                location_similarity=components[\"location\"],\n                momentum_similarity=components[\"momentum\"],\n                volatility_similarity=components[\"volatility\"],\n                candle_similarity=components[\"candle\"],\n                path_similarity=components[\"path\"],\n            )\n        )"
  },
  {
    "line": 2626,
    "kind": "keyword",
    "source": "key=lambda item: (\n            item.similarity,\n            item.index,\n        )"
  },
  {
    "line": 2642,
    "kind": "Attribute",
    "source": "record.index"
  },
  {
    "line": 2647,
    "kind": "Tuple",
    "source": "(\n            match,\n            record_by_index[match.index],\n        )"
  },
  {
    "line": 2661,
    "kind": "Subscript",
    "source": "record_by_index[match.index]"
  },
  {
    "line": 2675,
    "kind": "Call",
    "source": "RetrievalResult(\n            horizon=horizon,\n            query_index=query_index,\n            raw_candidates=raw_candidate_count,\n            deduplicated_matches=0,\n            top_similarity=0.0,\n            mean_similarity=0.0,\n            level=\"NONE\",\n            evidence=\"NONE\",\n            sparse_warning=True,\n            regime_agreement=0.0,\n            structure_agreement=0.0,\n            context_agreement=0.0,\n            up_share=0.0,\n            down_share=0.0,\n            neutral_share=0.0,\n            mean_atr_return=None,\n            mean_mfe_atr=None,\n            mean_mae_atr=None,\n            supporting_matches=0,\n            conflicting_matches=0,\n            historical_min_index=None,\n            historical_max_index=None,\n            selected_match_indices=[],\n            similarity_representation={\n                \"structure\": 0.0,\n                \"sequence\": 0.0,\n"
  },
  {
    "line": 2721,
    "kind": "Call",
    "source": "sum(\n            weight\n            for weight, (_, record)\n            in zip(\n                weights,\n                selected_rows,\n            )\n            if record.outcome.direction\n            == \"UP\"\n        )"
  },
  {
    "line": 2735,
    "kind": "Call",
    "source": "sum(\n            weight\n            for weight, (_, record)\n            in zip(\n                weights,\n                selected_rows,\n            )\n            if record.outcome.direction\n            == \"DOWN\"\n        )"
  },
  {
    "line": 2749,
    "kind": "Call",
    "source": "sum(\n            weight\n            for weight, (_, record)\n            in zip(\n                weights,\n                selected_rows,\n            )\n            if record.outcome.direction\n            == \"NEUTRAL\"\n        )"
  },
  {
    "line": 2778,
    "kind": "GeneratorExp",
    "source": "(\n        1\n        for _, record in selected_rows\n        if record.outcome.direction\n        == dominant\n    )"
  },
  {
    "line": 2835,
    "kind": "Call",
    "source": "sum(\n            weight\n            * (\n                record.outcome.atr_return\n                or 0.0\n            )\n            for weight, (_, record)\n            in zip(\n                weights,\n                selected_rows,\n            )\n        )"
  },
  {
    "line": 2851,
    "kind": "Call",
    "source": "sum(\n            weight\n            * (\n                record.outcome.mfe_atr\n                or 0.0\n            )\n            for weight, (_, record)\n            in zip(\n                weights,\n                selected_rows,\n            )\n        )"
  },
  {
    "line": 2867,
    "kind": "Call",
    "source": "sum(\n            weight\n            * (\n                record.outcome.mae_atr\n                or 0.0\n            )\n            for weight, (_, record)\n            in zip(\n                weights,\n                selected_rows,\n            )\n        )"
  },
  {
    "line": 2921,
    "kind": "Attribute",
    "source": "record.index"
  },
  {
    "line": 2976,
    "kind": "keyword",
    "source": "query_index=query_index"
  },
  {
    "line": 3000,
    "kind": "keyword",
    "source": "historical_min_index=(\n            min(indices)\n            if indices\n            else None\n        )"
  },
  {
    "line": 3005,
    "kind": "keyword",
    "source": "historical_max_index=(\n            max(indices)\n            if indices\n            else None\n        )"
  },
  {
    "line": 2610,
    "kind": "Call",
    "source": "SimilarityMatch(\n                index=record.index,\n                episode_id=record.episode_id,\n                similarity=components[\"total\"],\n                structure_similarity=components[\"structure\"],\n                sequence_similarity=components[\"sequence\"],\n                regime_similarity=components[\"regime\"],\n                location_similarity=components[\"location\"],\n                momentum_similarity=components[\"momentum\"],\n                volatility_similarity=components[\"volatility\"],\n                candle_similarity=components[\"candle\"],\n                path_similarity=components[\"path\"],\n            )"
  },
  {
    "line": 2626,
    "kind": "Lambda",
    "source": "lambda item: (\n            item.similarity,\n            item.index,\n        )"
  },
  {
    "line": 2649,
    "kind": "Subscript",
    "source": "record_by_index[match.index]"
  },
  {
    "line": 2652,
    "kind": "Compare",
    "source": "match.index in record_by_index"
  },
  {
    "line": 2661,
    "kind": "Name",
    "source": "record_by_index"
  },
  {
    "line": 2661,
    "kind": "Attribute",
    "source": "match.index"
  },
  {
    "line": 2663,
    "kind": "Compare",
    "source": "match.index in record_by_index"
  },
  {
    "line": 2677,
    "kind": "keyword",
    "source": "query_index=query_index"
  },
  {
    "line": 2696,
    "kind": "keyword",
    "source": "historical_min_index=None"
  },
  {
    "line": 2697,
    "kind": "keyword",
    "source": "historical_max_index=None"
  },
  {
    "line": 2721,
    "kind": "GeneratorExp",
    "source": "(\n            weight\n            for weight, (_, record)\n            in zip(\n                weights,\n                selected_rows,\n            )\n            if record.outcome.direction\n            == \"UP\"\n        )"
  },
  {
    "line": 2735,
    "kind": "GeneratorExp",
    "source": "(\n            weight\n            for weight, (_, record)\n            in zip(\n                weights,\n                selected_rows,\n            )\n            if record.outcome.direction\n            == \"DOWN\"\n        )"
  },
  {
    "line": 2749,
    "kind": "GeneratorExp",
    "source": "(\n            weight\n            for weight, (_, record)\n            in zip(\n                weights,\n                selected_rows,\n            )\n            if record.outcome.direction\n            == \"NEUTRAL\"\n        )"
  },
  {
    "line": 2835,
    "kind": "GeneratorExp",
    "source": "(\n            weight\n            * (\n                record.outcome.atr_return\n                or 0.0\n            )\n            for weight, (_, record)\n            in zip(\n                weights,\n                selected_rows,\n            )\n        )"
  },
  {
    "line": 2851,
    "kind": "GeneratorExp",
    "source": "(\n            weight\n            * (\n                record.outcome.mfe_atr\n                or 0.0\n            )\n            for weight, (_, record)\n            in zip(\n                weights,\n                selected_rows,\n            )\n        )"
  },
  {
    "line": 2867,
    "kind": "GeneratorExp",
    "source": "(\n            weight\n            * (\n                record.outcome.mae_atr\n                or 0.0\n            )\n            for weight, (_, record)\n            in zip(\n                weights,\n                selected_rows,\n            )\n        )"
  },
  {
    "line": 2976,
    "kind": "Name",
    "source": "query_index"
  },
  {
    "line": 2611,
    "kind": "keyword",
    "source": "index=record.index"
  },
  {
    "line": 2626,
    "kind": "Tuple",
    "source": "(\n            item.similarity,\n            item.index,\n        )"
  },
  {
    "line": 2649,
    "kind": "Name",
    "source": "record_by_index"
  },
  {
    "line": 2649,
    "kind": "Attribute",
    "source": "match.index"
  },
  {
    "line": 2652,
    "kind": "Attribute",
    "source": "match.index"
  },
  {
    "line": 2652,
    "kind": "Name",
    "source": "record_by_index"
  },
  {
    "line": 2663,
    "kind": "Attribute",
    "source": "match.index"
  },
  {
    "line": 2663,
    "kind": "Name",
    "source": "record_by_index"
  },
  {
    "line": 2677,
    "kind": "Name",
    "source": "query_index"
  },
  {
    "line": 2781,
    "kind": "Compare",
    "source": "record.outcome.direction\n        == dominant"
  },
  {
    "line": 2836,
    "kind": "BinOp",
    "source": "weight\n            * (\n                record.outcome.atr_return\n                or 0.0\n            )"
  },
  {
    "line": 2852,
    "kind": "BinOp",
    "source": "weight\n            * (\n                record.outcome.mfe_atr\n                or 0.0\n            )"
  },
  {
    "line": 2868,
    "kind": "BinOp",
    "source": "weight\n            * (\n                record.outcome.mae_atr\n                or 0.0\n            )"
  },
  {
    "line": 2611,
    "kind": "Attribute",
    "source": "record.index"
  },
  {
    "line": 2628,
    "kind": "Attribute",
    "source": "item.index"
  },
  {
    "line": 2728,
    "kind": "Compare",
    "source": "record.outcome.direction\n            == \"UP\""
  },
  {
    "line": 2742,
    "kind": "Compare",
    "source": "record.outcome.direction\n            == \"DOWN\""
  },
  {
    "line": 2756,
    "kind": "Compare",
    "source": "record.outcome.direction\n            == \"NEUTRAL\""
  },
  {
    "line": 2781,
    "kind": "Attribute",
    "source": "record.outcome.direction"
  },
  {
    "line": 2838,
    "kind": "BoolOp",
    "source": "record.outcome.atr_return\n                or 0.0"
  },
  {
    "line": 2854,
    "kind": "BoolOp",
    "source": "record.outcome.mfe_atr\n                or 0.0"
  },
  {
    "line": 2870,
    "kind": "BoolOp",
    "source": "record.outcome.mae_atr\n                or 0.0"
  },
  {
    "line": 2728,
    "kind": "Attribute",
    "source": "record.outcome.direction"
  },
  {
    "line": 2742,
    "kind": "Attribute",
    "source": "record.outcome.direction"
  },
  {
    "line": 2756,
    "kind": "Attribute",
    "source": "record.outcome.direction"
  },
  {
    "line": 2781,
    "kind": "Attribute",
    "source": "record.outcome"
  },
  {
    "line": 2838,
    "kind": "Attribute",
    "source": "record.outcome.atr_return"
  },
  {
    "line": 2854,
    "kind": "Attribute",
    "source": "record.outcome.mfe_atr"
  },
  {
    "line": 2870,
    "kind": "Attribute",
    "source": "record.outcome.mae_atr"
  },
  {
    "line": 2728,
    "kind": "Attribute",
    "source": "record.outcome"
  }
]
```

### decision_integration

```text
[
  {
    "function": "null_retrieval_sanity_test",
    "line": 3196,
    "source": "def null_retrieval_sanity_test(\n    current: MarketState,\n    records: Sequence[ExperienceRecord],\n    query_index: int,\n    horizon: int,\n) -> Dict[str, Any]:\n\n    eligible = [\n        record\n        for record in records\n        if (\n            record.index < query_index\n            and\n            query_index - record.index\n            >= MIN_HISTORY_GAP\n        )\n    ]\n\n    if (\n        len(eligible)\n        < MIN_RETRIEVAL_MATCHES\n    ):\n\n        return {\n            \"available\": False,\n            \"permutations\": 0,\n            \"real_max_share\": None,\n            \"null_max_share_mean\": None,\n            \"null_max_share_p95\": None,\n            \"real_minus_null_mean\": None,\n        }\n\n    real = retrieve_historical_experience(\n        current,\n        eligible,\n        horizon,\n        query_index,\n    )\n\n    real_max_share = max(\n        real.up_share,\n        real.down_share,\n        real.neutral_share,\n    )\n\n    outcomes = [\n        record.outcome.direction\n        for record in eligible\n    ]\n\n    null_max = []\n\n    for permutation in range(\n        NULL_PERMUTATIONS\n    ):\n\n        shuffled = deterministic_permutation(\n            outcomes,\n            seed=1009\n            * (permutation + 1)\n            + query_index,\n        )\n\n        permuted_records = []\n\n        for record, direction in zip(\n            eligible,\n            shuffled,\n        ):\n\n            permuted_records.append(\n                ExperienceRecord(\n                    index=record.index,\n                    episode_id=record.episode_id,\n                    state_key=record.state_key,\n                    sequence_state=record.sequence_state,\n                    regime=record.regime,\n                    structure_event=record.structure_event,\n                    location=record.location"
  },
  {
    "function": "main",
    "line": 3885,
    "source": "def main() -> None:\n\n    print(\"=\" * 100)\n    print(\n        \"MLAI v4.1.7 ROBUST CAUSAL HISTORICAL \"\n        \"EXPERIENCE RETRIEVAL\"\n    )\n    print(\"=\" * 100)\n\n    print(\"RESEARCH / VALIDATION ONLY\")\n\n    print()\n    print(\"=\" * 100)\n    print(\"V4.1.7 CAPABILITIES\")\n    print(\"=\" * 100)\n\n    print(\"1. Similarity representation       : ENABLED\")\n    print(\"2. Retrieval discrimination        : ENABLED\")\n    print(\"3. H4 discrimination               : ENABLED\")\n    print(\"4. H8 discrimination               : ENABLED\")\n    print(\"5. H16 discrimination              : ENABLED\")\n    print(\"6. Incremental predictive value    : ENABLED\")\n    print(\"7. Predictive decision integration : ENABLED\")\n\n    print()\n    print(\"=\" * 100)\n    print(\"PROTECTION CHECK\")\n    print(\"=\" * 100)\n\n    print(\n        f\"{MARKET_DATA_FILE:<28}: READ ONLY\"\n    )\n\n    print(\n        \"Production MLAI              : NOT MODIFIED\"\n    )\n\n    print(\n        \"Learning memory              : NOT MODIFIED\"\n    )\n\n    print(\n        \"Trading                      : DISABLED\"\n    )\n\n    guard = ProtectionGuard(\n        MARKET_DATA_FILE\n    )\n\n    protection_before = (\n        guard.before_hash\n    )\n\n    candles, invalid = load_market_data(\n        MARKET_DATA_FILE\n    )\n\n    chronology = audit_chronology(\n        candles\n    )\n\n    if (\n        not chronology[\"ordered\"]\n        or chronology[\"duplicates\"]\n    ):\n\n        raise RuntimeError(\n            \"Chronology audit failed.\"\n        )\n\n    if len(candles) < 500:\n\n        raise RuntimeError(\n            \"Insufficient candle history.\"\n        )\n\n    windows = create_walk_forward_windows(\n        len(candles),\n        DEFAULT_TRAIN_WINDOWS,\n        DEFAULT_OOS_SIZE,\n    )\n\n    atr = calculate_atr(\n        candles\n    )\n\n    engine = CausalStructureEngine(\n     "
  },
  {
    "function": "<module>",
    "line": 3228,
    "source": "retrieve_historical_experience(\n        current,\n        eligible,\n        horizon,\n        query_index,\n    )"
  },
  {
    "function": "<module>",
    "line": 3295,
    "source": "retrieve_historical_experience(\n            current,\n            permuted_records,\n            horizon,\n            query_index,\n        )"
  },
  {
    "function": "<module>",
    "line": 4134,
    "source": "retrieve_historical_experience(\n                        query_state,\n                        records,\n                        horizon,\n                        query_index,\n                    )"
  }
]
```

### match_memory_classes

```text
[
  {
    "class": "ExperienceRecord",
    "line": 244,
    "source": "class ExperienceRecord:\n    index: int\n    episode_id: int\n    state_key: Tuple[Any, ...]\n    sequence_state: str\n    regime: str\n    structure_event: str\n    location: str\n    momentum_state: str\n    volatility_ratio: float\n    body_ratio: float\n    range_ratio: float\n    r1: float\n    r3: float\n    r8: float\n    r16: float\n    path_vector: Tuple[Tuple[float, float, float, float], ...]\n    horizon: int\n    outcome: Outcome"
  },
  {
    "class": "SimilarityMatch",
    "line": 266,
    "source": "class SimilarityMatch:\n    index: int\n    episode_id: int\n    similarity: float\n    structure_similarity: float\n    sequence_similarity: float\n    regime_similarity: float\n    location_similarity: float\n    momentum_similarity: float\n    volatility_similarity: float\n    candle_similarity: float\n    path_similarity: float"
  },
  {
    "class": "SimilarityRepresentation",
    "line": 285,
    "source": "class SimilarityRepresentation:\n    \"\"\"\n    Explicit similarity representation.\n\n    This makes the representation auditable rather than hiding everything\n    inside one scalar similarity number.\n    \"\"\"\n\n    structure: float\n    sequence: float\n    regime: float\n    location: float\n    momentum: float\n    volatility: float\n    candle: float\n    path: float\n    total: float"
  },
  {
    "class": "RetrievalDiscrimination",
    "line": 305,
    "source": "class RetrievalDiscrimination:\n    \"\"\"\n    Measures whether the retrieved neighbours are actually distinguishable\n    from the broader eligible historical population.\n    \"\"\"\n\n    candidate_count: int\n    selected_count: int\n\n    top_similarity: float\n    mean_selected_similarity: float\n    mean_candidate_similarity: float\n\n    similarity_separation: float\n    ranking_concentration: float\n\n    class_entropy: float\n    baseline_entropy: float\n\n    directional_discrimination: float\n\n    discriminative: bool"
  },
  {
    "class": "RetrievalResult",
    "line": 330,
    "source": "class RetrievalResult:\n    horizon: int\n    query_index: int\n\n    raw_candidates: int\n    deduplicated_matches: int\n\n    top_similarity: float\n    mean_similarity: float\n\n    level: str\n    evidence: str\n\n    sparse_warning: bool\n\n    regime_agreement: float\n    structure_agreement: float\n    context_agreement: float\n\n    up_share: float\n    down_share: float\n    neutral_share: float\n\n    mean_atr_return: Optional[float]\n    mean_mfe_atr: Optional[float]\n    mean_mae_atr: Optional[float]\n\n    supporting_matches: int\n    conflicting_matches: int\n\n    historical_min_index: Optional[int]\n    historical_max_index: Optional[int]\n\n    selected_match_indices: List[int]\n\n    # V4.1.7\n    similarity_representation: Dict[str, float]\n    discrimination: Dict[str, Any]"
  },
  {
    "class": "DiscriminationResult",
    "line": 2128,
    "source": "class DiscriminationResult:\n    \"\"\"\n    Structured diagnostic result for strict retrieval discrimination.\n\n    This object is deliberately independent of the retrieval engine.\n    It contains diagnostics only and does not alter candidate selection,\n    model training, OOS labels, market data, learning memory, or trading.\n    \"\"\"\n\n    queries: int\n    discriminative_queries: int\n    discrimination_rate: float\n    # Compatibility flag used by the existing summary layer.\n    discriminative: bool\n\n    mean_similarity_separation: float\n    mean_ranking_concentration: float\n    mean_directional_discrimination: float\n\n    mean_class_entropy: float\n    mean_baseline_entropy: float\n\n    predictive_accuracy: float\n    retrieval_accuracy: float\n    baseline_accuracy: float\n\n    incremental_brier_lift: float\n    incremental_log_loss_lift: float\n    incremental_accuracy_delta: float\n\n    predictive_margin: float"
  }
]
```

### retrieval_returns

```text
[
  {
    "line": 2974,
    "source": "return RetrievalResult(\n        horizon=horizon,\n        query_index=query_index,\n        raw_candidates=raw_candidate_count,\n        deduplicated_matches=len(\n            selected_rows\n        ),\n        top_similarity=top_similarity,\n        mean_similarity=mean_similarity,\n        level=level,\n        evidence=evidence,\n        sparse_warning=(\n            len(selected_rows)\n            < MIN_RETRIEVAL_MATCHES\n        ),\n        regime_agreement=regime_agreement,\n        structure_agreement=structure_agreement,\n        context_agreement=context_agreement,\n        up_share=up_share,\n        down_share=down_share,\n        neutral_share=neutral_share,\n        mean_atr_return=mean_atr_return,\n        mean_mfe_atr=mean_mfe_atr,\n        mean_mae_atr=mean_mae_atr,\n        supporting_matches=supporting_matches,\n        conflicting_matches=conflicting_matches,\n        historical_min_index=(\n            min(indices)\n            if indices\n            else None\n        ),\n        historical_max_index=(\n            max(indices)\n            if indices\n            else None\n        ),\n        selected_match_indices=indices,\n        similarity_representation=representation,\n        discrimination=_serialize_discrimination_result(discrimination),\n    )"
  },
  {
    "line": 2675,
    "source": "return RetrievalResult(\n            horizon=horizon,\n            query_index=query_index,\n            raw_candidates=raw_candidate_count,\n            deduplicated_matches=0,\n            top_similarity=0.0,\n            mean_similarity=0.0,\n            level=\"NONE\",\n            evidence=\"NONE\",\n            sparse_warning=True,\n            regime_agreement=0.0,\n            structure_agreement=0.0,\n            context_agreement=0.0,\n            up_share=0.0,\n            down_share=0.0,\n            neutral_share=0.0,\n            mean_atr_return=None,\n            mean_mfe_atr=None,\n            mean_mae_atr=None,\n            supporting_matches=0,\n            conflicting_matches=0,\n            historical_min_index=None,\n            historical_max_index=None,\n            selected_match_indices=[],\n            similarity_representation={\n                \"structure\": 0.0,\n                \"sequence\": 0.0,\n                \"regime\": 0.0,\n                \"location\": 0.0,\n                \"momentum\": 0.0,\n                \"volatility\": 0.0,\n                \"candle\": 0.0,\n                \"path\": 0.0,\n                \"total\": 0.0,\n            },\n            discrimination=_serialize_discrimination_result(discrimination),\n        )"
  }
]
```

## Blockers

- Automatic sparse repair safety: Automatic repair is refused because the source does not simultaneously prove the exact sparse blocks and an unambiguous similarity field bound to selected historical matches.

## Warnings

- Exact similarity field access: Multiple similarity accesses were found. Automatic repair will not guess which one is authoritative.
- H4 structural reference: No explicit H4 reference inside retrieval function.
- H8 structural reference: No explicit H8 reference inside retrieval function.
- H16 structural reference: No explicit H16 reference inside retrieval function.
- Causality screen: Causality-related constructs were found, but AST discovery alone cannot prove that no future information enters retrieval.
- V4.1.8 file creation: BUILD REFUSED. No V4.1.8 file was created.

## Scientific interpretation

This audit distinguishes structural existence from scientific validity. Finding a similarity calculation or retrieval ranking does not prove that the representation discriminates useful historical states. Predictive discrimination, calibration, generalization and incremental value require empirical evaluation on chronologically separated data.

Therefore this builder will not manufacture claims of H4/H8/H16 predictive validity merely because corresponding variables or labels exist in the source.
