# Market Language AI (MLAI)

## Architecture and System Design

**Status:** Proposed — no application implementation has started  
**Purpose:** Architecture review and roadmap approval  
**Product:** An evidence-based market education platform that translates observable chart behavior into plain English.

---

## 1. Executive architecture decision

MLAI should begin as a **modular monolith with asynchronous workers**, not as a collection of microservices and not as an LLM-first application.

The core rule is:

> MLAI is a Market Reasoning Engine, not an indicator or signal generator. The system first understands the visible market, then explains that understanding. Deterministic analysis establishes observable facts and evidence; AI expresses the resulting reasoning in clear language.

The canonical reasoning cycle is:

```text
Observe
  → Understand
  → Collect Evidence
  → Build Market Story
  → Reason
  → Explain
  → Update Memory
  → Wait for New Evidence
```

This is a domain invariant, not merely a prompt instruction. A reasoning cycle cannot publish a conclusion until it has passed through the prior stages, and it cannot begin its next cycle until a new completed candle or other explicitly supported market event becomes visible.

This gives the product:

- Reproducible analysis.
- Exact chart locations for every claim.
- A market understanding layer that exists before language generation.
- Protection against future-candle leakage in replay mode.
- Testable market logic independent of model behavior.
- Lower latency and lower inference cost.
- A clean path to specialized workers and services when scale requires them.

The first production architecture should contain one API application, one web application, one PostgreSQL database, and one worker process. The modules inside the API and worker should have strict boundaries even though they initially share a deployable unit.

At higher scale, the data ingestion, historical analysis, and AI narration workloads can be separated without rewriting the domain model.

### 1.1 What MLAI is not

MLAI must not be designed, named, tested, or marketed as:

- A technical indicator.
- A signal generator.
- A buy/sell alert system.
- A pattern classifier whose label is the conclusion.
- A directional prediction bot.
- A mathematical score that hides its reasoning.

Features such as momentum, volatility, volume, and candle measurements are inputs to understanding. They are not the product output. The product output is a cited explanation of market behavior, including uncertainty and what evidence the system is waiting for next.

### 1.2 Market Reasoning Engine boundary

The **Market Reasoning Engine** is the central domain coordinator. It does not replace the specialized modules; it composes them in a fixed reasoning order:

1. **Observe:** ingest only what is visible and completed.
2. **Understand:** translate observations into participant behavior and market state.
3. **Collect Evidence:** gather independent, chart-visible support and data-quality context.
4. **Build Market Story:** update the temporal narrative and competing interpretations.
5. **Reason:** compare interpretations, identify stronger/weaker participants, changes, uncertainty, and invalidation conditions.
6. **Explain:** render the reasoning in plain English with citations and annotations.
7. **Update Memory:** persist the market-state transition and the learner-visible reasoning.
8. **Wait for New Evidence:** publish a waiting state until the next eligible event.

The LLM is an optional explanation and conversation component inside step 6. It is not the authority for steps 1–5 or 7–8.

---

## 2. Product vision analysis

### 2.1 What is strong in the original vision

The brief has a differentiated product thesis:

1. It teaches market behavior rather than presenting opaque signals.
2. It uses observable evidence instead of unsupported predictions.
3. It treats the market as an evolving story, which is more useful pedagogically than isolated pattern labels.
4. It includes visual teaching, making the explanation inspectable.
5. Replay mode creates a natural learning loop and provides a strong defense against hindsight bias.
6. The calm mentor personality is appropriate for beginners and reduces the temptation to overstate certainty.

### 2.2 Weaknesses and missing concepts

#### A. “The AI reasons every candle” needs a cost and latency policy

Running a large model for every completed candle is expensive, slow, and unnecessary. Many candles do not materially change the market story.

**Improvement:** Every candle should pass through a deterministic change detector. The system always computes a compact analysis record, but invokes a language model only when:

- The story materially changes.
- A meaningful event occurs.
- The user asks a question.
- Replay mode is configured to narrate every step.

Routine updates can use templated language generated from trusted facts.

#### B. “World’s first” is a positioning claim, not an engineering requirement

The product should not depend on proving an absolute market-first claim. The defensible differentiator is a verifiable experience: every explanation is linked to chart evidence, bounded by available information, and designed for learning.

**Improvement:** Position the product around “evidence-backed market explanations” and “learn to read what the chart is saying,” while preserving the larger vision internally.

#### C. Market interpretation is not a single objective truth

Different professional traders can interpret the same chart differently. A system that claims to identify the one correct story will lose trust.

**Improvement:** Represent:

- Observations: directly measurable facts.
- Interpretations: plausible explanations supported by those facts.
- Confidence: calibrated support strength, not probability of price direction.
- Invalidations: what new evidence would weaken or change the interpretation.

The UI should distinguish these explicitly.

#### D. “Evidence” needs provenance and quality scoring

It is not enough to say that volume, momentum, or structure supports a conclusion. The product must know:

- Which candles or price ranges supplied the evidence.
- Which calculation produced it.
- Which data source and timeframe were used.
- Whether volume was available and trustworthy.
- Whether the evidence is confirmed, developing, or weak.

**Improvement:** Every evidence item receives a stable ID, source range, engine version, timestamp, quality state, and contribution to the interpretation.

#### E. Replay mode can accidentally leak future information

Future leakage can happen through:

- Indicators calculated over the full dataset.
- Support/resistance levels detected using future swing points.
- Normalization based on the entire series.
- Training labels or cached annotations created after the replay point.
- LLM prompts containing full chart history.

**Improvement:** Replay uses an explicit `visibleThroughCandleId` boundary. All feature calculations, levels, stories, memory retrieval, and prompts are evaluated against that boundary. This must be enforced in the domain API, not only in the UI.

#### F. The vision needs a learning model, not only an explanation model

Explanations alone do not prove that users learn.

**Improvement:** Add a learning loop:

- Ask the learner what they think happens next or what buyers/sellers are doing.
- Reveal the next candle or event.
- Compare the learner’s explanation with the observable evidence.
- Provide a non-predictive coaching explanation.
- Track concepts mastered, recurring misconceptions, and replay performance.

This should be introduced after the core interpreter is reliable, but it should influence the data model from the beginning.

#### G. The system needs explicit supported-market boundaries

Crypto, equities, futures, and forex differ in session behavior, volume quality, gaps, leverage, and liquidity.

**Improvement:** Start with one market family and a small number of timeframes. Add a market capability profile that describes:

- Session and timezone rules.
- Trading calendar.
- Volume semantics.
- Tick-size and price precision.
- Data quality expectations.
- Whether overnight gaps exist.

#### H. Safety and compliance are product requirements

The system could be interpreted as financial advice, especially if users ask for entries, exits, or guaranteed outcomes.

**Improvement:** Treat educational framing, uncertainty, suitability boundaries, auditability, and refusal/redirect behavior as first-class product requirements. MLAI should explain what the chart currently supports, not instruct users to buy or sell.

### 2.3 Recommended product definition

MLAI is a **chart literacy and market reasoning coach**.

Its primary output is not a trade signal. It is a structured explanation:

1. What is observable?
2. What behavior does that observation suggest?
3. How does it fit into the recent market structure?
4. Which evidence supports the interpretation?
5. What remains uncertain?
6. What would confirm or invalidate the current story?

---

## 3. System boundaries

### 3.1 In scope

- Historical OHLCV chart analysis.
- Candle-by-candle behavior translation.
- Market structure and level detection.
- Evidence-backed market stories.
- Chart annotations tied to explanations.
- Replay mode with strict information boundaries.
- Conversational questions grounded in the current chart state.
- Learning exercises and historical evaluation.
- Versioned analysis and reproducible replay sessions.

### 3.2 Initially out of scope

- Automated trade execution.
- Brokerage account access.
- Personalized investment advice.
- Guaranteed forecasts or price targets.
- Portfolio management.
- High-frequency or tick-level trading.
- Social sentiment as a primary source of truth.
- Autonomous strategy optimization for live capital.

These may be considered later, but introducing them early would weaken the teaching product and substantially increase compliance and operational risk.

---

## 4. High-level architecture

```text
                         ┌──────────────────────────┐
                         │        Web Client         │
                         │  chart · story · replay   │
                         │  learning · conversation  │
                         └────────────┬─────────────┘
                                      │ HTTPS / SSE
                                      ▼
                         ┌──────────────────────────┐
                         │       API / BFF Layer     │
                         │ auth · validation · ACL    │
                         │ query composition · rate  │
                         └────────────┬─────────────┘
                                      │ application commands/queries
                  ┌───────────────────┼───────────────────┐
                  ▼                   ▼                   ▼
        ┌────────────────┐  ┌────────────────┐  ┌──────────────────┐
        │ Analysis       │  │ Replay         │  │ Conversation     │
        │ Orchestrator   │  │ Application    │  │ Application      │
        └───────┬────────┘  └───────┬────────┘  └────────┬─────────┘
                │                   │                    │
                ▼                   ▼                    ▼
        ┌──────────────────────────────────────────────────────────┐
        │                    Domain Engines                         │
        │ data · candle language · knowledge · structure            │
        │ evidence · story · annotation · learning · memory         │
        └──────────────────────────────┬───────────────────────────┘
                                       │
                          ┌────────────┴────────────┐
                          ▼                         ▼
                 ┌────────────────┐       ┌────────────────────┐
                 │ PostgreSQL     │       │ Object storage     │
                 │ source data    │       │ imports/exports    │
                 │ analysis       │       │ large datasets    │
                 │ sessions       │       │ chart snapshots    │
                 └────────────────┘       └────────────────────┘

        ┌──────────────────────────────────────────────────────────┐
        │                    Background Workers                     │
        │ ingestion · historical analysis · narration · evaluation  │
        └──────────────────────────────┬───────────────────────────┘
                                       │
                                       ▼
                              ┌─────────────────┐
                              │ AI provider     │
                              │ adapter         │
                              │ structured JSON │
                              └─────────────────┘
```

### 4.1 Architectural style

Use clean architecture inside a modular monolith:

- **Domain:** Pure market concepts and deterministic rules.
- **Application:** Use cases, orchestration, transactions, authorization.
- **Adapters:** HTTP, persistence, chart serialization, model providers, data providers.
- **Infrastructure:** PostgreSQL, object storage, queues, logging, metrics.

The domain must not import Express, database clients, UI code, or an AI SDK.

### 4.2 Why not microservices first?

The product is still discovering its domain language. Microservices would introduce distributed transactions, deployment overhead, versioning problems, and observability work before the analysis model is stable.

The proposed boundaries are service-ready:

- Each module has explicit ports.
- Cross-module communication uses commands, queries, and domain events.
- Long-running work is asynchronous.
- Analysis artifacts are immutable and versioned.

When required, a worker or module can be extracted behind the same contract.

---

## 5. Module architecture

### 5.1 Data Engine

**Responsibility**

- Import and normalize OHLCV data.
- Validate ordering, duplicates, gaps, timestamps, precision, and missing fields.
- Maintain source and dataset provenance.
- Expose candles in bounded chronological windows.

**Must not do**

- Interpret market behavior.
- Generate narratives.
- Look ahead beyond a caller-provided visibility boundary.

**Key concepts**

- `Instrument`
- `MarketProfile`
- `Timeframe`
- `Candle`
- `CandleSeries`
- `DataQualityReport`
- `DatasetVersion`

### 5.2 Market Reasoning Engine

**Responsibility**

Coordinate one complete reasoning cycle and enforce the canonical order:

```text
Observe → Understand → Collect Evidence → Build Market Story
→ Reason → Explain → Update Memory → Wait for New Evidence
```

This is the domain-level orchestrator. It owns the lifecycle and completion rules for a `MarketReasoningCycle`, while the specialized engines own the calculations and state transitions inside each stage.

**A cycle must answer**

- What happened?
- Why does the evidence support that interpretation?
- Who currently appears stronger?
- Who currently appears weaker?
- What changed from the previous market state?
- What is the market communicating?
- Which visible evidence supports each claim?
- What is the system waiting to see next?

**Cycle states**

- `observing`
- `understanding`
- `collecting_evidence`
- `building_story`
- `reasoning`
- `explaining`
- `memory_updated`
- `waiting_for_new_evidence`
- `insufficient_evidence`
- `failed_with_explicit_reason`

`waiting_for_new_evidence` is a successful, publishable state. It is not a missing-result or error state.

**Must not do**

- Emit a buy/sell signal.
- Collapse the market into a single numeric score.
- Continue reasoning after the evidence boundary without a new visible event.
- Ask the language model to fill a missing reasoning stage.

### 5.3 Candle Language Engine

**Responsibility**

Translate each completed candle into behavior:

- Buying or selling pressure.
- Rejection of higher or lower prices.
- Expansion or contraction.
- Relative body and wick behavior.
- Closing location.
- Relationship to preceding candles.

The output should use behavioral vocabulary, never rely on pattern names as the primary user-facing language.

**Output**

- Structured observations.
- Human-readable behavior candidates.
- Chart ranges and candle references.
- Confidence and data quality.

### 5.4 Market Knowledge Engine

**Responsibility**

Provide explicit, versioned market concepts and teaching rules:

- Definitions of pressure, rejection, consolidation, breakout, failed breakout, and reversal.
- Market-profile-specific rules.
- Educational language guidelines.
- Concept relationships and prerequisites.

This is not a generic vector-search knowledge base. It should start as reviewed, versioned domain knowledge. Retrieval can be added later for longer educational content.

### 5.5 Market Structure Engine

**Responsibility**

Infer current structure from visible history:

- Swing candidates and confirmed swings.
- Higher highs, higher lows, lower highs, lower lows.
- Trend, range, transition, and compression states.
- Breakout and failed-breakout candidates.
- Support/resistance zones only when evidence crosses a defined threshold.

Levels must be represented as zones with:

- Price range.
- Time range.
- Supporting reactions.
- Strength score.
- Confirmation state.
- Invalidation conditions.

### 5.6 Evidence Engine

**Responsibility**

Combine independent evidence into an auditable interpretation.

Evidence sources may include:

- Candle behavior.
- Structure.
- Level reactions.
- Momentum.
- Volatility.
- Volume, if valid.
- Liquidity events, if the data source supports them.
- Consolidation and expansion.
- Previous market state.

The engine should avoid simple “one signal equals one conclusion” behavior. It should produce an evidence graph:

```text
Observation → Evidence item → Interpretation → Story claim
```

Each edge carries a contribution, not a false claim of mathematical certainty.

For every conclusion candidate, the engine must explicitly return:

- Supporting evidence IDs and chart ranges.
- Contradicting or missing evidence.
- Evidence quality and freshness.
- Whether the evidence is sufficient to reason.
- What additional evidence would increase or reduce support.

An empty or conflicting evidence set is a valid outcome. The engine must return `insufficient_evidence` rather than force an interpretation.

### 5.7 Story Engine

**Responsibility**

Maintain a temporal market narrative:

- Previous story state.
- Current dominant participants.
- Attempts and defenses.
- Momentum changes.
- Current phase.
- What the market is waiting to confirm.
- What would invalidate the story.

The story is a state machine with append-only transitions, not a single mutable paragraph. The paragraph is a projection generated from the structured state.

The story must distinguish:

- Observable events.
- Participant behavior inferred from those events.
- The current interpretation.
- Alternative interpretations.
- The next evidence requirement.

### 5.8 Annotation Engine

**Responsibility**

Turn evidence into visual teaching objects:

- Highlighted candles.
- Arrows.
- Circles.
- Labels.
- Support/resistance zones.
- Trend lines.
- Breakout/failure boxes.

Every annotation must reference at least one evidence item and one explanation claim. An annotation without provenance should be rejected.

The engine outputs chart-coordinate-neutral annotations. The frontend converts them into pixels for the current viewport.

### 5.9 Replay Engine

**Responsibility**

- Create a replay session from a dataset version.
- Select a starting candle and reveal boundary.
- Advance one candle, a chosen number of candles, or to the next event.
- Recompute analysis using only visible candles.
- Store what the user saw and when.
- Prevent future data from entering analysis, prompts, cache keys, or memory.

The replay boundary is part of every analysis request and every cache key.

### 5.10 AI Conversation Engine

**Responsibility**

Answer user questions about the current chart state using grounded facts.

The engine should:

1. Resolve the current session and visibility boundary.
2. Retrieve the relevant structured analysis, evidence, story, and annotations.
3. Classify the question: explanation, clarification, learning, or disallowed advice request.
4. Build a compact, provenance-rich context.
5. Call the model through a provider adapter only when necessary.
6. Validate structured output.
7. Link each statement to evidence IDs and chart ranges.
8. Render the answer in the mentor voice.

The model should not receive unrestricted raw datasets by default.

### 5.11 Memory Engine

The memory engine has two distinct meanings and they must not be conflated.

**Market memory**

- Prior states in the current chart.
- Previous reactions to zones.
- Historical structure in the visible session.

**Learner memory**

- Concepts introduced.
- Misconceptions.
- Replay performance.
- Preferred explanation depth.
- Completed learning exercises.

Market memory must never expose future chart information. Learner memory must not be used to create a financial profile or infer sensitive traits without explicit product justification.

The memory update occurs after explanation and before the waiting state. It records the completed reasoning cycle, not a prediction of what happens next. Memory should include:

- The visible boundary.
- Market state before and after the cycle.
- Evidence used and evidence rejected.
- Story transition.
- Reasoning conclusion or explicit insufficient-evidence state.
- What the system is waiting for next.

### 5.12 Historical Learning Engine

**Responsibility**

Turn historical data into learning experiences and validate system behavior:

- Generate replay episodes.
- Label observable events after the fact for evaluation only.
- Measure whether the system explained the event using evidence available at the time.
- Track consistency, calibration, and educational usefulness.
- Compare engine versions without mixing datasets.

This engine should not optimize for directional prediction accuracy as the primary metric. It should optimize for evidence fidelity, temporal correctness, explanation quality, and learner improvement.

### 5.13 Cross-cutting modules

These are required even though they are not in the original list:

- **Identity and authorization:** account, session, entitlements, ownership.
- **Safety policy:** educational boundary, advice refusal, uncertainty language.
- **Analysis versioning:** engine versions, model versions, prompt versions, dataset versions.
- **Observability:** traces, structured logs, latency, token cost, error rates.
- **Audit:** immutable record of analysis inputs and outputs.
- **Feature flags:** controlled rollout of new rules and models.

---

## 6. Communication contracts

### 6.1 Communication rules

1. Modules communicate through application ports, not direct table reads.
2. Commands mutate state; queries read projections; events announce completed facts.
3. Domain events are immutable and versioned.
4. Long-running operations return a job/session reference rather than blocking an HTTP request.
5. Every analysis request carries:
   - Dataset version.
   - Instrument and timeframe.
   - `visibleThroughCandleId`.
   - Analysis engine version.
   - Request correlation ID.
6. A reasoning-cycle response exposes its current stage, provenance, uncertainty, and next evidence requirement.
7. No module may silently fall back from missing data to an invented value.
8. No module may expose an indicator-like score or signal as the product conclusion.
9. A cycle may conclude with `insufficient_evidence` or `waiting_for_new_evidence`; it must never force a conclusion.

### 6.2 Synchronous request path

Used for fast reads and actions:

```text
Web Client
  → API
  → Replay Application / Analysis Query
  → Analysis Read Model
  → chart + story + evidence + annotations
```

Examples:

- Load a chart session.
- Fetch the current story.
- Ask for the evidence behind a claim.
- Advance a replay by one candle when analysis is already cached.

### 6.3 Asynchronous analysis path

Used for ingestion, cold analysis, historical runs, and model narration:

```text
Application command
  → outbox event
  → worker queue
  → Data / Analysis / AI module
  → immutable analysis artifact
  → projection update
  → client notification
```

The initial queue can use PostgreSQL-backed jobs to avoid an early infrastructure dependency. A Redis-backed queue can be introduced when throughput requires it.

### 6.4 Core domain events

Conceptual events include:

- `DatasetImported`
- `DatasetValidated`
- `CandleVisibilityAdvanced`
- `CandleBehaviorAnalyzed`
- `MarketReasoningCycleStarted`
- `MarketReasoningStageCompleted`
- `MarketStructureUpdated`
- `EvidenceBundleCreated`
- `MarketStoryAdvanced`
- `MarketReasoningConcluded`
- `WaitingForNewEvidencePublished`
- `AnnotationsPublished`
- `NarrationRequested`
- `NarrationPublished`
- `ReplayCompleted`
- `LearningObservationRecorded`

Events should include IDs and versions, not large embedded payloads. Consumers load the immutable artifact by ID.

### 6.5 Market reasoning cycle contract

The primary cross-module contract is a `MarketReasoningCycle`. It is an immutable record of one pass through the reasoning pipeline:

```text
MarketReasoningCycle
├── observation
├── understanding
├── evidenceBundle
├── marketStory
├── reasoning
├── explanation
├── memoryUpdate
└── waitingState
```

Each stage must carry:

- Stage status and completion timestamp.
- Input artifact IDs.
- Output artifact IDs.
- Dataset version and visible candle boundary.
- Engine/configuration version.
- Data-quality warnings.

The `reasoning` stage must explicitly contain:

- What happened.
- Why it happened, expressed as an evidence-backed interpretation.
- Who appears stronger and the supporting evidence.
- Who appears weaker and the supporting evidence.
- What changed from the previous state.
- What the market is communicating.
- Supporting and contradicting evidence.
- What the system is waiting to see next.
- Whether evidence is sufficient.

If evidence is insufficient, `reasoning` must contain a non-forced state such as:

> “There is not enough visible evidence to support a stronger interpretation yet. The system is waiting for confirmation from [specific chart-visible event or reaction].”

The `waitingState` is required for every successful cycle. It records the event class that can start the next cycle, without predicting that event will occur.

### 6.6 Analysis artifact contract

The central cross-module object should be an immutable `AnalysisSnapshot`:

- Session identity.
- Dataset and candle boundary.
- Engine versions.
- Current structured market state.
- Evidence bundle IDs.
- Story transition ID.
- Annotation IDs.
- Optional narration ID.
- Created timestamp.
- Data quality status.
- Reasoning-cycle ID.
- Current waiting-for-evidence state.

The UI can safely render this snapshot because all visible claims have references.

---

## 7. End-to-end Market Reasoning Cycle

For each newly visible completed candle or explicitly supported market event:

1. **Observe:** Replay and Data Engines establish the newly visible boundary and return only eligible completed data.
2. **Understand:** Candle Language, Market Knowledge, and Market Structure Engines translate observations into participant behavior and market state.
3. **Collect Evidence:** Evidence Engine gathers independent chart-visible support, contradiction, freshness, and quality.
4. **Build Market Story:** Story Engine updates the temporal narrative, including current and alternative interpretations.
5. **Reason:** Market Reasoning Engine compares interpretations and determines what happened, why, stronger/weaker participants, what changed, what the market is communicating, and what evidence is still needed.
6. **Explain:** Annotation Engine anchors the explanation to the chart; deterministic templates or the AI Conversation Engine render it in plain English.
7. **Update Memory:** Memory Engine persists the completed market-state transition and learner-visible reasoning.
8. **Wait for New Evidence:** The cycle publishes its waiting state and stops. No new conclusion is generated until a new eligible event becomes visible.

If the Evidence Engine reports insufficient evidence, the cycle still completes stages 5–8, but the reasoning result is explicitly non-conclusive. The system explains the observable facts, states what remains unknown, and identifies the evidence required for confirmation.

The `Explain` stage may be skipped for an unchanged routine state only as a presentation optimization; the structured reasoning cycle, memory update, and waiting state must still be produced. A user request always triggers an explanation grounded in the current cycle.

The sequence must be deterministic for a fixed:

- Dataset version.
- Visibility boundary.
- Engine version set.
- Configuration.

Model narration may vary, but the underlying facts and citations must remain stable.

---

## 8. Frontend architecture

### 8.1 Primary user surfaces

The first web application should support:

- **Workspace:** chart, current story, evidence, and annotations.
- **Replay:** controlled reveal and event navigation.
- **Conversation:** questions grounded in the current visible state.
- **Learning:** exercises and feedback.
- **History:** saved sessions and completed replays.
- **Settings:** explanation depth, data preferences, and safety/disclaimer acknowledgement.

### 8.2 Frontend responsibilities

- Render chart data and chart-coordinate annotations.
- Keep transient viewport state locally.
- Fetch server-owned analysis through typed API hooks.
- Never compute authoritative market conclusions in the browser.
- Display loading, uncertain, developing, and insufficient-evidence states distinctly.
- Show evidence links that focus the chart on the cited range.
- Make replay state obvious at all times.

### 8.3 Frontend state separation

Separate:

- **Server state:** datasets, analysis snapshots, stories, evidence, sessions, learning records.
- **Session state:** active replay boundary, selected annotation, expanded evidence.
- **View state:** zoom, pan, chart dimensions, panel visibility.
- **Conversation state:** messages and pending requests.

This prevents a chart interaction from accidentally changing the authoritative replay state.

### 8.4 Realtime updates

Use normal request/response for the first version. Add Server-Sent Events for:

- Replay analysis completion.
- Long-running historical analysis.
- Narration completion.

WebSockets are not necessary until there is a genuine collaborative or streaming requirement.

---

## 9. Backend architecture

### 9.1 API layer

The existing Express API should become a thin boundary for:

- Request validation.
- Authentication and authorization.
- Rate limits.
- Use-case invocation.
- Response serialization.
- Correlation IDs.

Business rules should not live in route handlers.

### 9.2 Application layer

Use cases should be explicit, for example:

- Import dataset.
- Create analysis session.
- Advance replay.
- Get current analysis snapshot.
- Explain evidence item.
- Ask chart question.
- Start historical learning run.
- Submit learner response.

Each use case coordinates domain services and repositories.

### 9.3 Worker layer

The worker executes jobs that should not block the API:

- Dataset validation and normalization.
- Batch candle analysis.
- Story reconstruction.
- Narration generation.
- Replay episode generation.
- Evaluation and regression runs.

Jobs must be idempotent. A retry must not create duplicate analysis artifacts or duplicate learner events.

---

## 10. AI narration architecture

The language model is an optional **narration and conversation adapter**. It is not the Market Reasoning Engine. It may not observe raw candles and independently decide what the market means.

### 10.1 Grounded narration pipeline

```text
Completed reasoning cycle
  → explanation plan
  → model response in strict schema
  → schema/provenance/safety validation
  → rendered explanation
```

The model receives:

- The completed reasoning cycle.
- Current and relevant prior story transitions.
- Selected evidence items and chart range references.
- Data quality warnings and known missing inputs.
- The user's question, if any.
- Voice, educational, and safety constraints.

The model does not receive future candles in replay mode.

The model must not be asked to:

- Detect a signal.
- Produce a buy/sell recommendation.
- Calculate an indicator as the conclusion.
- Choose a market direction without an evidence bundle.
- Fill in an absent reasoning stage.
- Convert insufficient evidence into a confident opinion.

### 10.2 Model output requirements

The model output should be structured, not free text only:

- Main explanation.
- Observable facts.
- Interpretation.
- Uncertainty.
- Invalidation condition.
- Evidence IDs.
- Annotation IDs or chart ranges.
- Educational follow-up.
- What the system is waiting to see next.
- Explicit `insufficientEvidence` state when applicable.

The backend rejects or repairs output that:

- Cites unknown evidence.
- Makes a directional guarantee.
- Claims data that is not available.
- Uses future candles.
- Gives unsupported trade instructions.
- Presents a signal, alert, or directional guarantee as the conclusion.
- Omits the reason, evidence, or next-evidence requirement.

### 10.3 Provider strategy

Use a provider adapter so the domain never imports an AI vendor SDK. The initial implementation should use Replit-managed AI integrations rather than requiring the user to supply an API key.

The adapter should support:

- Model selection by task.
- Structured output.
- Timeout and retry policy.
- Token and cost accounting.
- Prompt/version identifiers.
- Redaction and audit logging.

Use a smaller/cheaper model for routine narration and a stronger model for difficult questions or quality review. The product should remain useful when the model is unavailable by rendering deterministic explanations.

### 10.4 AI quality controls

Evaluation must measure:

- Evidence citation accuracy.
- Temporal correctness.
- Unsupported claim rate.
- Calibration of uncertainty.
- Consistency across repeated runs.
- Reading level and clarity.
- User learning improvement.

“Sounds like a trader” is not a sufficient quality metric.

---

## 11. Database and storage design

### 11.1 Primary database

Use PostgreSQL as the system of record. The existing workspace already provides Drizzle ORM and a database package, which is a good foundation.

Use relational tables for:

- Identity and ownership.
- Instruments and market profiles.
- Datasets and dataset versions.
- Candles and indexes.
- Analysis sessions.
- Replay boundaries and steps.
- Analysis snapshots.
- Evidence and evidence links.
- Story transitions.
- Annotations.
- Conversation messages.
- Narration artifacts.
- Learning exercises and responses.
- Job records and outbox events.
- Evaluation runs and metrics.

### 11.2 Storage pattern

Keep authoritative, queryable metadata in PostgreSQL. Store large raw imports, exports, and generated artifacts in object storage. Do not put large chart files or model transcripts directly into hot relational rows.

### 11.3 Important invariants

- A candle belongs to exactly one immutable dataset version.
- An analysis snapshot references exactly one dataset version and visibility boundary.
- Evidence references only candles visible at snapshot creation.
- An annotation references evidence.
- A story transition has a predecessor or is an initial state.
- Engine and model versions are recorded for every derived artifact.
- User-owned sessions cannot be read across accounts.

### 11.4 Query and indexing strategy

Optimize initially for:

- Instrument/timeframe/time ordered candle windows.
- Replay session and boundary.
- Latest snapshot for a session.
- Evidence by snapshot and chart range.
- Story transitions by session.
- Job status by owner and state.

Partition or move historical candle storage to a columnar system only after measured workload justifies it. Prematurely adding a second analytical database will slow product discovery.

### 11.5 Caching

Cache only immutable or safely keyed results. Every analysis cache key must include:

- Dataset version.
- Visibility boundary.
- Instrument.
- Timeframe.
- Engine configuration/version.
- Market profile version.

Never cache a full-history result and serve it to replay mode.

---

## 12. Proposed clean folder structure

This is a design target, not an instruction to create the files yet.

```text
/
├── artifacts/
│   ├── api-server/
│   │   └── src/
│   │       ├── app/
│   │       │   ├── commands/
│   │       │   ├── queries/
│   │       │   ├── services/
│   │       │   └── policies/
│   │       ├── domains/
│   │       │   ├── market-data/
│   │       │   ├── candle-language/
│   │       │   ├── market-knowledge/
│   │       │   ├── market-structure/
│   │       │   ├── evidence/
│   │       │   ├── story/
│   │       │   ├── annotations/
│   │       │   ├── replay/
│   │       │   ├── conversation/
│   │       │   ├── memory/
│   │       │   └── learning/
│   │       ├── adapters/
│   │       │   ├── http/
│   │       │   ├── persistence/
│   │       │   ├── ai/
│   │       │   ├── market-data/
│   │       │   ├── jobs/
│   │       │   └── storage/
│   │       ├── workers/
│   │       └── routes/
│   │
│   └── mlai-web/
│       └── src/
│           ├── app/
│           ├── pages/
│           ├── features/
│           │   ├── workspace/
│           │   ├── replay/
│           │   ├── story/
│           │   ├── evidence/
│           │   ├── conversation/
│           │   ├── learning/
│           │   └── history/
│           ├── components/
│           ├── chart/
│           ├── state/
│           └── styles/
│
├── lib/
│   ├── api-spec/
│   ├── api-client-react/
│   ├── api-zod/
│   ├── db/
│   │   └── src/
│   │       ├── schema/
│   │       ├── migrations/
│   │       └── repositories/
│   └── domain-contracts/
│
├── docs/
│   ├── MLAI-ARCHITECTURE.md
│   ├── decisions/
│   ├── domain/
│   └── evaluation/
│
└── scripts/
```

### 12.1 Dependency direction

```text
routes/adapters → application → domain
                         ↘ ports
infrastructure adapters ──┘
```

Domain packages may depend on shared primitives and schemas, but never on HTTP, database, UI, or model provider implementations.

### 12.2 Naming and versioning principles

- Prefer domain nouns and explicit use-case verbs.
- Keep event schemas versioned.
- Keep engine configuration serializable.
- Treat analysis outputs as immutable records.
- Do not hide market decisions inside generic utility functions.

---

## 13. Recommended technology stack

### 13.1 Initial stack

| Area | Recommendation | Reason |
|---|---|---|
| Web | React + Vite + TypeScript | Matches the workspace direction and supports a fast, interactive chart workspace. |
| Server | Node.js + TypeScript + Express 5 | Already present; sufficient for API and orchestration while keeping one language across product layers. |
| API contract | OpenAPI + generated React Query/Zod clients | Keeps frontend and backend aligned and makes contracts reviewable. |
| Client data | TanStack Query | Correct separation of server state and UI state. |
| Charting | A financial candlestick chart library with custom overlay support | The annotation engine requires candle/range anchored overlays, not just generic charts. |
| UI | Accessible component primitives and a focused design system | Supports dense chart workspaces without creating an inaccessible custom UI. |
| Database | PostgreSQL + Drizzle ORM | Strong transactional model, JSON support for evolving artifacts, and already available in the workspace. |
| Jobs | PostgreSQL-backed durable jobs initially | Avoids operating Redis before throughput proves the need. |
| Large files | Object storage | Correct place for raw imports and generated exports. |
| AI | Provider adapter using Replit-managed AI integrations | No user API keys, vendor isolation, structured output, and future provider choice. |
| Validation | Zod at boundaries | Runtime validation of API, events, AI output, and imported data. |
| Observability | Pino logs, traces/metrics, cost and model telemetry | Required for debugging asynchronous analysis and AI quality. |
| Testing | Unit, property, contract, replay leakage, and fixture-based evaluation tests | Market reasoning requires deterministic and temporal testing, not only endpoint tests. |

### 13.2 When to add other technologies

- Add Redis only when job throughput, rate limiting, or realtime fan-out requires it.
- Add a columnar analytics database only when PostgreSQL query measurements show a real bottleneck.
- Add Python workers only if the research/evaluation workload needs Python-specific numerical or ML libraries. Keep their input/output contracts language-neutral.
- Add vector search only for educational documents and long-form knowledge retrieval. Do not use embeddings as the source of truth for chart interpretation.
- Add microservices only when team ownership, scaling profile, or deployment isolation makes the cost worthwhile.

---

## 14. Development roadmap

Each milestone ends with a review and approval gate. Work on the next milestone should not begin until the previous milestone is accepted.

### Milestone 0 — Architecture approval

**Purpose:** Agree on the product boundary, source-of-truth principles, initial market scope, and quality bar.

**Deliverables**

- Approved architecture document.
- Initial supported instrument/timeframe decision.
- Safety and educational positioning decision.
- Definition of “evidence-backed explanation.”
- Decision on the first historical dataset.

**Acceptance criteria**

- No unresolved decision affects the first prototype’s data model.
- Future-data leakage policy is accepted.
- Deterministic analysis vs AI narration boundary is accepted.

### Milestone 1 — Domain model and data contract

**Purpose:** Establish stable market concepts before building UI polish.

**Deliverables**

- Versioned domain glossary.
- Candle, dataset, instrument, timeframe, and market-profile contracts.
- Data quality rules.
- Dataset provenance model.
- `MarketReasoningCycle` contract and stage state machine.
- Definitions for observation, understanding, evidence, story, reasoning, explanation, memory, and waiting state.
- Initial OpenAPI contract.

**Acceptance criteria**

- A malformed dataset is rejected with actionable reasons.
- Candle windows are reproducible and ordered.
- Visibility boundaries are part of the contract.
- A reasoning cycle cannot skip stages or publish a conclusion without an evidence result.
- `insufficient_evidence` and `waiting_for_new_evidence` are valid domain states.

### Milestone 2 — Historical data foundation

**Purpose:** Import and serve a reliable, bounded historical series.

**Deliverables**

- Dataset import path.
- Validation and normalization.
- PostgreSQL persistence.
- Queryable candle windows.
- Data quality report.

**Acceptance criteria**

- Duplicate, out-of-order, missing, and malformed records are detected.
- The same dataset version produces the same candle windows.
- Source and timezone metadata are preserved.

### Milestone 3 — Deterministic candle language

**Purpose:** Translate individual candle behavior without relying on an LLM.

**Deliverables**

- Candle feature extraction.
- Behavior observations.
- Human-readable behavioral templates.
- Fixture suite for representative candle sequences.

**Acceptance criteria**

- Every observation references its candle.
- The output avoids pattern-name-only explanations.
- Missing volume does not silently become zero or “normal.”

### Milestone 4 — Structure and evidence engine

**Purpose:** Move from isolated candles to evidence-backed market interpretation.

**Deliverables**

- Trend/range/transition state.
- Confirmed and potential zones.
- Rejection, breakout, failed-breakout, and consolidation evidence.
- Evidence graph and quality scoring.
- Evidence sufficiency and contradiction assessment.

**Acceptance criteria**

- Weak swing points do not automatically become levels.
- Every interpretation identifies supporting evidence and uncertainty.
- The engine explicitly identifies what happened, why it is believed, and what evidence is still missing.
- Insufficient or contradictory evidence produces a non-forced waiting state.
- The same fixture produces stable results across runs.

### Milestone 5 — Story and annotation engine

**Purpose:** Produce a continuous market story that can point back to the chart.

**Deliverables**

- Story state machine.
- Append-only story transitions.
- Chart-coordinate-neutral annotations.
- Evidence-to-annotation links.
- Stronger/weaker participant assessment with supporting evidence.
- Explicit next-evidence requirements.

**Acceptance criteria**

- A user can inspect why a story changed.
- Every annotation has evidence provenance.
- The story separates observable events from interpretation and states what it is waiting to see.
- Story transitions are reproducible from the visible candle sequence.

### Milestone 6 — Replay mode

**Purpose:** Make temporal reasoning and learning possible without hindsight.

**Deliverables**

- Replay session creation.
- Single-step and event-step reveal.
- Visibility-bound analysis.
- Replay timeline and saved sessions.
- Leakage test fixtures.
- Full Market Reasoning Cycle execution at each reveal boundary.

**Acceptance criteria**

- Future candles cannot affect current analysis, cache keys, annotations, or prompts.
- Each reveal follows Observe → Understand → Collect Evidence → Build Market Story → Reason → Explain → Update Memory → Wait for New Evidence.
- The system stops after waiting and does not create a new conclusion without a new eligible event.
- Replaying the same dataset with the same settings reproduces the same deterministic state.
- The UI makes the visible boundary unmistakable.

### Milestone 7 — First market interpreter workspace

**Purpose:** Give users the complete deterministic teaching experience.

**Deliverables**

- Chart workspace.
- Story presentation.
- Evidence inspection.
- Annotation focus.
- Replay controls.
- Data quality and uncertainty states.
- Market communication view showing what happened, why, stronger/weaker participants, what changed, and what is awaited next.

**Acceptance criteria**

- A new user can load a dataset, start replay, advance candles, and understand why the story changed.
- Every displayed conclusion can be traced to visible chart evidence.
- The workspace clearly distinguishes a reasoned interpretation from an explicit insufficient-evidence state.
- All primary interactions use real persisted data.
- No trust-critical flow is mocked.

### Milestone 8 — Grounded AI narration and conversation

**Purpose:** Add the mentor voice without making the model authoritative.

**Deliverables**

- AI provider adapter.
- Structured narration schema.
- Grounded prompt builder.
- Evidence/provenance validator.
- Narration adapter that consumes completed reasoning cycles only.
- Conversation UI.
- Safety policy and refusal behavior.

**Acceptance criteria**

- Narration cites valid evidence.
- Narration explains what happened, why, stronger/weaker participants, what changed, market communication, and what to watch for next.
- Unsupported claims are rejected or repaired.
- The model cannot create a signal, replace a reasoning stage, or turn insufficient evidence into certainty.
- The system works in deterministic-only mode when AI is unavailable.
- Replay prompts contain no future information.

### Milestone 9 — Learning engine

**Purpose:** Turn interpretation into measurable learning.

**Deliverables**

- Replay exercises.
- Learner response model.
- Coaching feedback.
- Concept progress.
- Misconception tracking.

**Acceptance criteria**

- Exercises are generated from visible evidence boundaries.
- Feedback explains reasoning rather than grading a directional guess as “correct.”
- Progress is based on observable concepts and repeated performance.

### Milestone 10 — Historical evaluation and quality program

**Purpose:** Validate the system before expanding markets or adding live data.

**Deliverables**

- Versioned evaluation datasets.
- Temporal leakage tests.
- Evidence fidelity metrics.
- Explanation consistency metrics.
- Model regression suite.
- Human review workflow.
- Full reasoning-cycle conformance tests.

**Acceptance criteria**

- A new engine version can be compared against the previous version.
- Regressions in evidence fidelity are detected before release.
- Tests detect skipped stages, unsupported conclusions, signal-like outputs, and missing waiting states.
- Quality dashboards distinguish market logic failures from language-model failures.

### Milestone 11 — Scale and market expansion

**Purpose:** Expand only after the core experience is trusted.

**Deliverables**

- Additional market profiles.
- More data providers through adapters.
- Worker scaling and queue monitoring.
- Optional Redis/columnar storage based on measurements.
- Production hardening and cost controls.

**Acceptance criteria**

- New market support does not fork core reasoning logic unnecessarily.
- Provider failures degrade clearly.
- Cost and latency remain within defined budgets.

---

## 15. Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Hallucinated explanations | Destroys trust | Deterministic evidence layer, structured model output, provenance validation, AI fallback. |
| Future-data leakage | Invalidates replay and learning | Boundary-aware APIs, cache keys, prompts, datasets, and automated leakage tests. |
| Overconfident financial language | Safety and compliance exposure | Explicit uncertainty schema, safety policy, blocked guarantees, educational framing. |
| Noisy support/resistance detection | Users learn bad habits | Require multiple reactions and measurable confirmation; show potential levels separately. |
| Data vendor inconsistency | Reproducibility failures | Immutable dataset versions, source metadata, normalization reports, provider adapters. |
| LLM latency and cost | Poor UX and unsustainable margins | Change detector, templates for routine updates, model routing, caching, quotas. |
| Model output drift | Inconsistent teaching | Prompt/model versioning, golden fixtures, structured validation, regression review. |
| Overbuilding infrastructure early | Slow product learning | Modular monolith, PostgreSQL-backed jobs, add services only after measurement. |
| Weak educational outcomes | Product feels like commentary | Learning engine, user exercises, misconception tracking, outcome metrics. |
| Chart annotation mismatch | Explanations feel untrustworthy | Domain-coordinate annotations, stable candle IDs, viewport transform tests. |
| Market-specific assumptions | Incorrect explanations in new asset classes | Market profiles and capability flags; expand one market family at a time. |
| Privacy and sensitive profiling | Trust and policy risk | Minimize learner data, clear retention policy, user controls, no unnecessary inference. |
| Operational opacity | Hard to debug failures | Correlation IDs, immutable artifacts, job states, model telemetry, audit trails. |

---

## 16. Better approaches than the original assumptions

### 16.1 Build a “fact compiler” before an AI analyst

The strongest implementation is not “send chart data to an LLM.” It is:

```text
Price data → measurable features → evidence graph → interpretation state → narration
```

This makes the AI a communication layer over a trustworthy reasoning substrate.

### 16.2 Use a multi-hypothesis story instead of one absolute story

When evidence conflicts, the system should be able to say:

- Primary interpretation.
- Alternative interpretation.
- Evidence favoring each.
- What would resolve the uncertainty.

This better matches how experienced traders reason and avoids pretending the market has only one explainable state.

### 16.3 Teach “what would change my mind”

This is more valuable than a directional forecast. Every explanation should end, when appropriate, with an invalidation or confirmation condition. It teaches conditional reasoning and naturally limits overconfidence.

### 16.4 Separate analysis confidence from price confidence

The system can be highly confident that sellers rejected a level while remaining unable to say what price will do next. These must be separate fields:

- `observationConfidence`
- `interpretationSupport`
- `futureOutcomeUncertainty`

### 16.5 Make no-conclusion states a product feature

“Insufficient evidence,” “mixed participation,” and “the market is waiting” should be valid, useful states, not errors. This is central to the brand promise and protects users from forced narratives.

### 16.6 Treat replay as the core product loop, not a later add-on

Replay is the most defensible learning feature and the best test of whether the reasoning engine is honest. The data model and APIs should be replay-safe from the first analysis milestone, even if the polished replay UI comes later.

---

## 17. Success metrics

### Product quality

- Percentage of explanation claims with valid evidence citations.
- Unsupported claim rate.
- Future-leakage test pass rate.
- Deterministic reproducibility rate.
- Annotation-to-evidence link validity.
- Data quality warning visibility.

### AI quality

- Structured output validation pass rate.
- Evidence citation precision.
- Model response latency and cost per session.
- Uncertainty-language compliance.
- Human reviewer agreement on explanation usefulness.

### Learning quality

- Improvement in identifying pressure, structure, and confirmation over time.
- Reduction in recurring misconceptions.
- Replay completion rate.
- Ability to explain a new chart event using cited evidence.

Directional prediction accuracy should not be the leading success metric for this product.

---

## 18. Approval decisions required before implementation

The following choices should be confirmed before Milestone 1 begins:

1. First supported market family: equities, crypto, forex, or futures.
2. First supported timeframe set.
3. First historical dataset/source.
4. Whether accounts and saved sessions are required in the first user-facing prototype.
5. Whether the first release is education-only with no live market feed.
6. Desired explanation depth: beginner only, or beginner plus advanced mode.
7. Retention policy for chart data, conversations, and learner history.
8. Target latency for a single replay step and for a conversational answer.
9. Initial budget ceiling for AI narration.
10. Required legal/safety review before external users access the product.

No application code should be written until this architecture and the first milestone scope are approved.
