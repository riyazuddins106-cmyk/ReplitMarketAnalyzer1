# MLAI Market Language Brain — Architecture Audit

**Audit status:** COMPLETE  
**Audit date:** 2026-08-23  
**Scope:** repository inventory and architecture review only. Existing research files
and raw market data were not modified.

## 1. Current architecture

The repository contains two distinct MLAI paths:

1. **Canonical unified console:** `mlai_unified.py`
   - Standard-library Python implementation.
   - Loads the corrected candle-language knowledge book and the smaller
     `data/market_data.bin` corpus.
   - Builds causal candle/market states, retrieves persisted experience, emits
     scenarios, and supports causal walk-forward `predict -> reveal -> learn`.
   - Experience persistence is opt-in.

2. **Preserved v4.x/v4.20 research path**
   - `mlai_market_structure_v420.py`
   - `MLAI_V420_RETRIEVAL_FORENSIC_REPAIR.py`
   - `MLAI_V420_PRICE_INTERPRETER.py`
   - `MLAI_V420_PRICE_INTERPRETER_FORENSIC.py`
   - Uses the larger `data/market_data_50d.bin` XAU/USD corpus.
   - Provides causal structure, historical retrieval, probability evidence,
     forensic diagnostics, and price-anchored English interpretation.

The repository also contains a large historical archive from v3.2 through v4.20,
including backups, patch scripts, source snapshots, validation reports, and
attached specifications. Those files are valuable comparison material but are
not a single canonical runtime.

The TypeScript/API and mockup artifacts are present as Replit scaffolding. They
are not connected to the Python MLAI console and are not required by the current
command-line product.

## 2. File inventory

Repository-level inventory:

- 202 Python files at the repository root.
- 49 Markdown files at the repository root.
- 61 files whose names indicate reports or validation outputs.
- 13 files under `data/`.
- Numerous attached specifications, source snapshots, backups, and archived
  assets under `attached_assets/` and `data/audit_archive/`.

Important active or active-looking files:

- `mlai_unified.py`
- `mlai_market_language_brain.py`
- `mlai_market_representation_v1.py`
- `mlai_market_representation_v2.py`
- `mlai_market_structure_v420.py`
- `MLAI_V420_PRICE_INTERPRETER.py`
- `MLAI_V420_PRICE_INTERPRETER_FORENSIC.py`
- `MLAI_V420_RETRIEVAL_FORENSIC_REPAIR.py`
- `MLAI_V420_UNSEEN_8_2_VALIDATION.py`
- `MLAI_CANDLE_LANGUAGE_ENGINE_V1.py`
- `MLAI_CANDLE_LANGUAGE_ENGINE_V2.py`
- `MLAI_CANDLE_LANGUAGE_ARCHIVE_BUILDER_V1.py`
- `MLAI_CANDLE_LANGUAGE_KB_*`

## 3. Data inventory

### Foundational candle-language data

| File | Size | SHA-256 | Payload |
|---|---:|---|---|
| `data/candle_language_v2.bin` | 27,382 bytes | `d76039b86cec6940a345bd5977d345c58ad6a377ab67d0147c6e71975d4105c6` | Pickle dictionary, 179 records |
| `data/candle_language_v2.pre_correction_backup.bin` | 26,620 bytes | `c866adcfef33b5cfb59ec6ccf9d103cf42b37fa65b347148ce46b86884164d14` | Pickle backup, 179 records |

### Market data

| File | Size | SHA-256 | Payload |
|---|---:|---|---|
| `data/market_data.bin` | 297,175 bytes | `dd57bccc3526ebaeb900181096adcbf48a84b5a3a334da1f1990a443cde091b5` | Pickle dictionary, 1,309 candles |
| `data/market_data_50d.bin` | 3,683,623 bytes | `9d97cd759a69bf45c4597fdfdd207fc19455361ce28b4825c365415372936ece` | Pickle dictionary, 35,403 candles |

`data/market_data.bin` spans 2026-08-10 through 2026-08-14 and is the corpus
used by the canonical console. `data/market_data_50d.bin` is labeled as a 50-day
dataset but its observed timestamps span 2026-02-02 through 2026-07-31, with
approximately six calendar months represented. Its metadata identifies XAU/USD,
symbol XAUUSD, and 5-minute candles.

The larger corpus has 155 distinct UTC dates and the latest ten are:

```text
2026-07-21, 2026-07-22, 2026-07-23, 2026-07-24,
2026-07-26, 2026-07-27, 2026-07-28, 2026-07-29,
2026-07-30, 2026-07-31
```

The larger corpus contains natural timestamp gaps. They were preserved rather
than filled with synthetic candles. The smaller corpus has four reported gaps
that the existing audit marks for review.

Other data artifacts include JSON indexes, an optional experience index, and
split archive parts under `data/audit_archive/`. No database is required by the
Python console path.

## 4. Memory file inventory

Persistent agent memory contains three project-level decisions:

- causal unified console is separate from preserved v4.x comparison engines;
- imported market data must satisfy the actual pickle loader contract;
- human interpretation must anchor claims to observed prices, zones, evidence,
  probabilities, and confirmation/invalidation levels.

`replit.md` documents the command-line product and protected-component policy.
It also contains a stale-looking reference to `MLAI_ARCHITECTURE.md` and the
smaller `market_data.bin` path; this audit is now the current architecture
record for the broader v4.20 work.

## 5. Active engine candidates

### Recommended canonical foundation

`mlai_unified.py` is the strongest canonical integration candidate because it
has explicit dataclasses, a unified state, causal ATR/structure logic,
experience memory, probability metrics, scenarios, and a walk-forward command.

### Recommended interpretation layer

`MLAI_V420_PRICE_INTERPRETER.py` is the strongest current human-language layer
for the larger XAU/USD corpus. It emits exact OHLC, candle evidence, price
zones, historical distributions, scenarios, and confirmation/invalidation text.

### Recommended forensic comparison layer

`MLAI_V420_RETRIEVAL_FORENSIC_REPAIR.py` is the strongest preserved retrieval
and diagnostic implementation. It includes causal records, configurable
retrieval, calibration, Brier/log-loss analysis, permutation/bootstrap tools,
and stability diagnostics.

### Recommended structural foundation

`mlai_market_structure_v420.py` is the current v4.20 causal structure and
market-state implementation used by the price interpreter and forensic engine.

## 6. Legacy engines

The v3.x through v4.19 files should remain preserved, not deleted. They include
market-structure implementations, candle-language engines, retrieval variants,
diagnostic scripts, backups, and validation experiments. They are useful for
regression comparison but create substantial duplicate logic and should not be
treated as interchangeable production components.

The attached source archives and pasted source files are evidence and design
inputs, not automatically executable canonical code.

## 7. Validation scripts and reports

Validation coverage exists across:

- candle-language knowledge inspection;
- market-data and chronology audits;
- causal market-structure tests;
- v3.x–v4.1 predictive walk-forward experiments;
- v4.15–v4.19 retrieval and robustness audits;
- v4.20 predictive-information and forensic audits;
- the newly added `MLAI_V420_UNSEEN_8_2_VALIDATION.py`.

The required full 5-minute 8-day/2-day holdout has **not completed**. The
current retrieval implementation exceeded the execution window. An hourly
sampling option was added to the new validator, but it is diagnostic only and
must not be presented as the definitive experiment. No holdout metrics should
be treated as completed until the full 5-minute run finishes.

## 8. Data generators

Known writers include:

- `download_market_data.py`
- `MLAI_CANDLE_LANGUAGE_KB_*` builders
- `MLAI_CANDLE_LANGUAGE_ARCHIVE_BUILDER_V1.py`
- older `mlai_market_structure_v*.py` variants
- `mlai_unified.py` when explicitly invoked with experience persistence

The raw market corpora are read by the current interpretation and validation
paths. Future work must write derived features, experience, and reports to
separate paths and must not overwrite raw data.

## 9. Retrieval engines

The canonical console has a compact state-key and experience-bucket retrieval
path. The v4.20 forensic engine performs richer similarity retrieval with
configuration, candidate filtering, regime/policy controls, calibration, and
diagnostics.

The current bottleneck is repeated expensive Python-level retrieval over the
large 35,403-candle corpus for every query and horizon. The bottleneck is
implementation performance, not a scientific justification for changing
5-minute observations to hourly observations.

## 10. Structure engines

- `mlai_unified.py`: compact causal structure snapshot.
- `mlai_market_structure_v420.py`: richer causal swing, trend, event, and
  market-state engine.
- `mlai_market_structure_v3*` through `v4*`: preserved historical variants.

The v4.20 structure engine explicitly delays confirmed swings until their
confirmation information is available. This boundary must be retained.

## 11. Sequence engines

Sequence behavior is represented in the unified state and v4.20 market-state
construction. The v4.20 interpreter translates states such as bullish impulse,
bearish response, rejection, recovery, and related sequence descriptions into
human-readable text. The older candle-language engines provide foundational
anatomy and sequence knowledge but are separate from learned historical
experience.

## 12. Probability engines

- `mlai_unified.py`: smoothed experience probabilities, calibration metrics,
  and baseline comparison.
- `MLAI_V420_RETRIEVAL_FORENSIC_REPAIR.py`: retrieval probabilities,
  calibration, Brier score, log loss, permutation/bootstrap diagnostics.
- `MLAI_V420_PRICE_INTERPRETER.py`: human-facing historical outcome
  distribution and probability presentation.

The probability output is evidence, not certainty. Small match counts require
uncertainty and sparse-data warnings.

## 13. Explanation engines

`MLAI_V420_PRICE_INTERPRETER.py` is the current strongest explanation engine.
It anchors output to observed prices, support/resistance zones, rejection
evidence, comparable cases, scenarios, and confirmation/invalidation levels.
It does not need to claim hidden orders or trader intent.

`mlai_unified.py` provides a more compact console explanation and scenario
report. The legacy candle-language engines provide lower-level human
descriptions but should not independently become the final evidence layer.

## 14. Read/write map

### Read-only or primarily read paths

- `data/market_data.bin`
- `data/market_data_50d.bin`
- `data/candle_language_v2.bin`
- JSON indexes
- historical reports and source snapshots

### Derived-output paths

- `data/market_experience.bin` when explicitly requested
- `data/market_experience.index.json`
- Markdown, JSON, and text reports generated by audit scripts
- archive outputs generated by the archive builder

### Protection concern

Several historical scripts contain write logic and should not be run blindly
against protected data. Builders and persistence commands need explicit output
paths and immutable-input checks in the canonical architecture.

## 15. External API map

The Python MLAI console currently has no required live external API. The market
data download script is a separate ingestion utility. The TypeScript scaffold
contains Replit connector SDK dependencies and an API server, but no verified
connection to the Python MLAI runtime.

Live ingestion is therefore not the immediate architectural priority.

## 16. Dependency map

### Python MLAI

The current v4.20 and unified paths use Python standard-library modules
including `pickle`, `json`, `math`, `dataclasses`, `pathlib`, and timezone
utilities. They do not require a database or third-party Python package.

### Replit TypeScript scaffold

The workspace includes pnpm/TypeScript artifacts, an API server, database
packages, Express, Drizzle, Pino, and Replit connector SDK dependencies. These
are separate from the current Python console.

## 17. Protected files

Protect from mutation during experiments:

- `data/market_data.bin`
- `data/market_data_50d.bin`
- `data/candle_language_v2.bin`
- `data/candle_language_v2.pre_correction_backup.bin`
- `MLAI_V420_PRICE_INTERPRETER.py`
- `MLAI_V420_PRICE_INTERPRETER_BACKUP.py`
- `MLAI_V420_RETRIEVAL_FORENSIC_REPAIR.py`
- preserved v3.x–v4.x research implementations
- existing validation reports and source snapshots

New work should use new modules or separate derived-output files unless a
measured, reviewed change is explicitly intended.

## 18. Duplicate implementations

The main duplicates are:

- many versions of market-structure code from v3.8 through v4.20;
- multiple candle-language engines and knowledge-base builders;
- multiple retrieval and predictive audit scripts;
- backup and phase snapshots of the large market-language-brain file;
- multiple reports covering overlapping claims.

This duplication is useful historical evidence but increases the risk of
running the wrong version, mixing data contracts, or interpreting a legacy
result as a current result.

## 19. Contradictions and risks

1. **Two market corpora are treated as canonical by different paths.**
   The unified console uses 1,309 candles; v4.20 uses 35,403 candles.

2. **The `50d` filename is misleading.**
   The observed date span is approximately six months, not 50 calendar days.

3. **The v4.20 corpus contains natural gaps.**
   Gaps are preserved, but horizon and timestamp semantics need to remain
   explicit.

4. **The full 5-minute 8/2 validation is computationally blocked.**
   The correct response is retrieval optimization, not silently changing the
   definitive test to hourly sampling.

5. **Several “active-looking” scripts are historical experiments.**
   They should not be selected by filename alone.

6. **The API/UI artifacts are not integrated with the Python product.**
   Treating them as the user-facing MLAI application would overstate current
   capability.

7. **Experience persistence can contaminate clean experiments if enabled
   unintentionally.**
   Clean runs must remain read-only unless persistence is explicitly requested.

## 20. Recommended canonical architecture

```text
RAW MARKET DATA (immutable)
        ↓
NORMALIZED CANDLE CONTRACT
        ↓
CAUSAL DERIVED FEATURES
        ↓
UNIFIED MARKET STATE
        ↓
CAUSAL SEQUENCE / STRUCTURE / CONTEXT
        ↓
HISTORICAL EXPERIENCE RECORDS
        ↓
OPTIMIZED CAUSAL RETRIEVAL
        ↓
CALIBRATED PROBABILITY + UNCERTAINTY
        ↓
COMPETING SCENARIOS
        ↓
PRICE-ANCHORED HUMAN EXPLANATION
        ↓
WALK-FORWARD / LOCKED HOLDOUT VALIDATION
```

Recommended component policy:

- use `mlai_unified.py` as the integration contract to preserve;
- use the v4.20 structure and explanation components as measured comparison
  candidates;
- keep v4.20 forensic evaluation separate from live inference;
- normalize the two data contracts before shared use;
- create a formal feature causality registry;
- optimize retrieval with precomputed/vectorized representations while
  preserving the candidate population and causal cutoff;
- keep raw data, derived features, experience, validated knowledge, and reports
  in separate layers.

## 21. Implementation phases

1. Freeze and hash protected inputs.
2. Define one normalized candle contract and loader audit.
3. Add a formal causality registry for every feature.
4. Reconcile unified and v4.20 state representations through adapters.
5. Define targets, overlap/purging rules, and baseline metrics.
6. Optimize causal retrieval without reducing the definitive 5-minute test.
7. Complete the full 8-day/2-day unseen validation.
8. Add structured experience records and validation status.
9. Unify scenario and explanation contracts.
10. Add performance benchmarks and regression tests.
11. Only afterward consider multi-timeframe, live ingestion, or controlled
    continuous learning.

## 22. Test gates

Before promoting a component:

- loader contract and OHLC validation pass;
- raw-data hashes and immutability checks pass;
- chronology and gap policy are recorded;
- feature availability timestamps are auditable;
- swing confirmation does not leak future candles;
- target labels never enter state inputs;
- retrieval candidate cutoff is mechanically tested;
- baseline comparison includes Brier score and log loss;
- sparse evidence reduces confidence;
- explanation claims map to structured evidence;
- full 5-minute holdout completes;
- incomplete experiments are labeled `INCOMPLETE`, never `PASS` or `FAIL`.

## 23. Immediate next action

Optimize `MLAI_V420_RETRIEVAL_FORENSIC_REPAIR.py` and its supporting state
representation so the definitive 5-minute Days 9–10 holdout can complete.
The hourly option in `MLAI_V420_UNSEEN_8_2_VALIDATION.py` is diagnostic only and
must not replace that experiment.