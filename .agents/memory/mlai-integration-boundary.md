---
name: MLAI integration boundary
description: The imported MLAI project keeps legacy v4.x engines preserved while one causal console entry point validates candle language first.
---

The unified MLAI path must keep foundational candle knowledge separate from learned historical experience and enforce `predict -> reveal -> learn`.

**Why:** The project specification treats future leakage and knowledge/experience mixing as non-negotiable audit risks, and the imported v4.x files are valuable comparison baselines.

**How to apply:** Extend `mlai_unified.py` through explicit state contracts and measured comparisons; do not silently replace or mutate v4.x retrieval, kNN, logistic, ensemble, or causal implementations.

Probability output must use evidence smoothing and expose sample size; persisted experience must be opt-in for walk-forward runs.

**Why:** Sparse state matches can otherwise turn one revealed outcome into false certainty or contaminate a clean chronological evaluation.

**How to apply:** Keep clean runs blank by default, use explicit resume/persist controls, and report Brier/log-loss alongside accuracy and baseline results.