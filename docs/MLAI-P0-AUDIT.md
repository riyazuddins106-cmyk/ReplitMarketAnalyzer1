# MLAI Project Audit — P0 Baseline

Status: Baseline recorded before the next implementation phase.

## Purpose

This document is the current project inventory for the MLAI Market Language Brain
roadmap. It distinguishes runnable implementation from architecture/reference
material so that historical ideas are not accidentally treated as validated
behavior.

## Current project position

The runnable product surface is a deterministic, command-line OHLCV analysis
vertical slice. It accepts CSV or JSON candles, normalizes them, calculates
basic candle anatomy and market context, and emits structured JSON.

The repository does **not** currently contain:

- Runnable legacy MLAI engines from the versions described in the planning
  material.
- Historical candle datasets in CSV, JSON, pickle, Parquet, NumPy, or similar
  formats.
- A persisted historical experience memory.
- A database schema for MLAI entities.
- An application API beyond the health endpoint.
- A chart, replay workspace, AI narration layer, or live-data connector.

The `attached_assets/` directory contains planning documents and prompts. Those
assets are reference material, not executable research artifacts.

## File classification

| Area | Classification | Current authority |
|---|---|---|
| `lib/market-engine/src/normalize.ts` | Active research implementation | Canonical input normalization behavior |
| `lib/market-engine/src/analyze.ts` | Active research implementation | Current deterministic analysis behavior |
| `lib/market-engine/src/types.ts` | Active contract | Current in-memory analysis types |
| `lib/market-engine/src/index.ts` | Active public API | Market-engine exports |
| `scripts/src/analyze.ts` | Active data tool | CLI input and output behavior |
| `lib/db/src/schema/index.ts` | Scaffold | No MLAI persistence is implemented |
| `lib/api-spec/openapi.yaml` | Scaffold contract | Health endpoint only |
| `artifacts/api-server/src/` | Scaffold service | Health endpoint only |
| `artifacts/mockup-sandbox/` | Reusable design infrastructure | Not the MLAI product UI |
| `docs/MLAI-ARCHITECTURE.md` | Architecture proposal | Design target, not implementation |
| `attached_assets/` | Reference/archive material | Planning documents and prompts only |
| `.agents/memory/mlai-reasoning-boundary.md` | Project policy | Deterministic evidence and grounded narration boundary |
| `package.json`, `pnpm-workspace.yaml`, `pnpm-lock.yaml` | Build/configuration | Workspace and dependency behavior |

## Read/write surface audit

### Market engine

- Reads candle rows supplied by the caller.
- Produces normalized candles and an analysis object in memory.
- Does not write market data.
- Does not write memory, reports, or project files.
- Does not call external APIs.
- Does not access future candles beyond the supplied snapshot, but it does not
  yet expose a replay visibility boundary.

### CLI

- Reads one caller-selected CSV or JSON file.
- Writes JSON analysis to standard output.
- Writes errors to standard error.
- Does not mutate the input file.
- Does not persist analysis results.

### Database and API scaffolds

- No MLAI database tables or persistence writes exist.
- The API currently exposes health behavior only.

## Existing protections confirmed

- OHLCV analysis is deterministic and does not require an LLM.
- Future outcomes are represented as targets and are not used as current inputs.
- The explanation explicitly avoids claims about hidden orders or trader intent.
- Duplicate timestamps are rejected by normalization.
- Invalid timestamps and invalid OHLC relationships are rejected.
- Source-order violations are reported rather than silently hidden.
- Accepted candles are returned in a stable chronological order.
- The repository typecheck passes.

## Contradictions or risks to resolve

1. The planning documents describe a broad research archive with legacy engines,
   serialized data, and validation reports, but those executable artifacts are
   not present in the current imported tree. Treat the current source files as
   authoritative until those materials are restored and audited.
2. The normalizer reports source-order violations and sorts accepted records, but
   there is no immutable raw-data copy that preserves the original payload and
   order.
3. The current `MarketAnalysis` type contains scenario and causality fields, but
   historical probabilities, replay boundaries, evidence quality, and dataset
   versions are not yet implemented.
4. The API, database, and UI scaffolds exist beside the CLI, but none of them
   currently expose the market-analysis vertical slice.
5. The current architecture document is marked proposed, while the market engine
   is already implemented. The implementation and acceptance tests must become
   the source of truth as each roadmap milestone is completed.

## P0 gate result

The project is sufficiently inventoried to begin the next step. The current
analysis engine and CLI are identified as the protected active foundation.

## Canonical data-foundation result

The first data-foundation slice is now implemented and documented in
`docs/MLAI-DATA-CONTRACT.md`:

1. Raw input records are separate from normalized candles.
2. Dataset metadata includes identity, version, source, format, and normalizer
   version.
3. Quality outcomes distinguish accepted, rejected, error, and warning states.
4. Normalized candles retain source-row provenance.
5. Deterministic contract tests cover preserved raw payloads, duplicate
   timestamps, out-of-order records, invalid volume, and malformed OHLC rows.

The remaining data-foundation work is persistent storage, raw-payload content
hashes, retrieval timestamps, timezone/source-calendar metadata, and immutable
dataset snapshots.

The next roadmap step is the full causality contract and visibility-boundary
registry.
