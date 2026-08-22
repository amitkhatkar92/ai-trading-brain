# IMPLEMENTATION MASTER PLAN

**Document Code:** IIOS-IMP-001
**Title:** Implementation Master Plan
**Subtitle:** The Single Authoritative Implementation Roadmap for the Investment Intelligence Operating System
**Version:** 1.0.0
**Status:** ACTIVE
**Owner:** Architecture Council
**Classification:** Engineering Implementation — Authoritative Roadmap
**Scope:** All IIOS subsystems, waves, components, dependencies, milestones, and future expansion
**Review Cycle:** Quarterly
**Related Documents:**
- IIOS-ENG-STD-001 Engineering Development Standards
- IIOS-RCF-001 Repository Certification Framework
- IIOS-TST-FRM-001 Testing Engineering Framework
- IIOS-BLD-DEP-001 Build and Deployment Engineering Framework
- IIOS-EXC-FRM-001 Exception and Failure Framework
- IIOS-ARC-001 Architecture Overview

---

## Document Revision History

| Version | Date | Type | Author | Summary |
|---------|------|------|--------|---------|
| 0.1.0 | 2024-01-01 | INITIAL | Architecture Council | Initial roadmap |
| 0.5.0 | 2024-03-01 | MINOR | Engineering Leads | Waves 11-20 detailed |
| 1.0.0 | 2024-06-01 | MAJOR | Architecture Council | Full document activated |

---

## Table of Contents

`
Part I    — Implementation Philosophy               (9 principles)
Part II   — Complete Implementation Roadmap         (20 waves)
Part III  — Dependency Graph                        (full subsystem dependencies)
Part IV   — Implementation Standards                (7 standard categories)
Part V    — Milestone Framework                     (8 milestone levels)
Part VI   — Risk Framework                          (8 risk categories)
Part VII  — Progress Tracking                       (6 tracking systems)
Part VIII — Engineering Constitution                (90 implementation rules)
Part IX   — Readiness Checklists                    (5 readiness gates)
`

---

# PART I — IMPLEMENTATION PHILOSOPHY

## 1.1 Why Implementation Order Matters

Implementation order is not a scheduling convenience. It is an engineering
discipline that determines whether a complex, multi-layer system can be
built correctly, verified continuously, and maintained indefinitely. In a
system as intricate as the Investment Intelligence Operating System — 17
architectural layers, approximately 62 agents, real-time market data, autonomous
trading decisions, and financial consequences — the order in which subsystems
are built determines the quality of every subsystem that comes after.

Building in the wrong order creates dependency inversions: a component built
before the system it depends on exists must be built with assumptions about
that dependency. Assumptions are not contracts. When the dependency is later
built correctly, the assuming component may work, may need adjustment, or
may need reconstruction. Each assumption adds entropy to the system.

Building in the right order — dependency-first, from the foundation upward —
means every component is built on verified reality. Its dependencies exist,
work correctly, and are available for integration testing during construction.
The component does not need to simulate what it depends on; it interacts with
the actual dependency. This is the only way to build a system where integration
is a discovery of what already works, not a fire drill to make things work
for the first time.

For an autonomous financial system, the stakes of incorrect implementation
order are financial. A kill switch built before the decision engine it monitors
is built on a simulated decision interface. If the real decision engine deviates
from the simulation — and it will, in edge cases — the kill switch may not
fire when it should. Implementation order is not an administrative preference;
it is the first engineering safeguard.

---

## 1.2 Dependency-First Engineering

Dependency-first engineering means: before any component begins implementation,
all components it depends on must be: specified (a complete specification exists),
implemented (the component is built), verified (the component passes all its
acceptance criteria), and available (the component can be imported and used).

This rule admits no exceptions for the critical path of IIOS. The critical path
runs through: Core Foundation → Infrastructure → Knowledge System → Ontology Engine
→ Observation Engine → Reasoning Engine → Decision Engine → Risk Intelligence →
Execution System. Any component on this path that is built before its dependencies
are verified creates a structural weakness that propagates forward through all
components built after it.

Dependency-first engineering is not slow. It is disciplined. The alternative —
building components in parallel with simulated dependencies and integrating
later — is faster at the start and exponentially slower at integration. IIOS
implements the patient approach: complete each layer before building the next.
Time invested in verification at each layer is time saved at integration.

The dependency-first rule produces a secondary benefit: it makes progress
visible. When each dependency layer is complete and verified, there is no
ambiguity about what the team has built. It works. It is verified. The next
layer can begin. Progress is a sequence of verified completions, not a
percentage estimate of parallel in-progress work.

---

## 1.3 Bottom-Up Construction

Bottom-up construction is the structural consequence of dependency-first
engineering. In a layered system, the lowest layers have the fewest dependencies.
They depend only on external libraries, operating system interfaces, and
well-established standards. They can be built and verified in isolation.
Each layer built above them has exactly the layers below as verified foundations.

In IIOS, bottom-up construction begins at the data layer: the mechanisms
that receive, store, and retrieve market data. Above this sits the knowledge
and ontology layer: the structures that give meaning to raw data. Above this
sits the reasoning and intelligence layer: the processes that derive insight
from structured knowledge. Above this sits the decision and risk layer: the
governance that translates insight into controlled action. Above this sits
the execution layer: the bridge to the market. Above all of this sits the
monitoring and learning layer: the feedback loop that improves the system over time.

This is not an arbitrary construction order. It follows the information flow
of the system. Data flows in at the bottom, insight emerges in the middle,
decisions are made toward the top, and execution and learning close the loop.
Building bottom-up means the information flow is never simulated; it is real
from the moment the lowest layer is complete.

---

## 1.4 Verification Before Expansion

Every wave of implementation must be verified before the next wave begins.
Verification is not optional, and it is not abbreviated when schedule pressure
is high. The correct response to schedule pressure is scope reduction, not
quality reduction.

Verification in IIOS means: all defined tests pass (unit, integration,
performance where applicable), all defined acceptance criteria are met,
all defined documentation is complete, and the Architecture Council has
reviewed the wave completion evidence. Only when all four conditions are
satisfied is a wave verified.

Verification before expansion prevents the accumulation of integration debt.
Integration debt is the cost of discovering, at integration time, that two
components that were built separately do not interact correctly. The cost
grows quadratically with the number of unverified components being integrated.
A system with twenty unverified components integrating simultaneously has
many more potential incompatibilities than a system where each component
was verified against its dependencies before the next was built.

The IIOS verification standard is exact: the completion of a wave is a
governance event, not an engineering estimate. Evidence is collected,
reviewed, and approved. The Architecture Council records the completion.
The next wave begins only after this approval.

---

## 1.5 Architecture Preservation

Implementation is the process of converting an architectural specification into
a working system. The primary engineering risk of this process is architectural
drift: the accumulating divergence between the intended architecture and the
implemented architecture. Architectural drift is invisible in small increments
and catastrophic in aggregate.

IIOS prevents architectural drift through three mechanisms: the architectural
specification is the primary reference for all implementation decisions
(not convention, not habit, not local expedience); the architecture is verified
continuously (import graph analysis, interface signature checking, and layer
latency measurement run at every CI build); and the Architecture Council
reviews every completed wave to confirm architectural fidelity before approving
completion.

Architecture preservation is not the responsibility of the architecture team
alone. Every engineer implementing a component is responsible for knowing the
architectural specification for that component, understanding where it sits
in the 17-layer hierarchy, understanding its dependencies, and implementing
to the specification rather than to a convenient approximation.

When an implementation decision would deviate from the specification — even
for a good reason — the correct process is to raise the deviation through an
Engineering Decision Record and have the Architecture Council decide whether
the specification should be updated or the implementation should conform.
Unilateral architectural deviations, however well-intentioned, accumulate into
architectural drift.

---

## 1.6 Incremental Delivery

Incremental delivery means the IIOS system produces value at each wave completion,
not only at the end of full implementation. At Wave 3 completion, a functional
knowledge system exists. At Wave 9 completion, a functional decision engine exists.
At Wave 15 completion, a functional execution system exists. Each of these is a
deliverable that can be demonstrated, tested in a realistic context, and used
as a foundation for the next wave.

Incremental delivery serves several engineering purposes. It provides early
feedback: the behavior of real components interacting with real dependencies
reveals issues that design cannot anticipate. It provides early value: parts
of the system can be used — for paper trading, for knowledge validation, for
strategy research — before the full system is complete. It provides early
risk reduction: integration issues are discovered at each wave rather than
accumulated until final integration.

Incremental delivery requires that each wave produces a complete, independently
usable unit — not a fragment that has meaning only in the context of the full
system. This drives a discipline of completeness at each wave: a wave is not
done when the code is written; it is done when the code is tested, documented,
and produces demonstrable value.

---

## 1.7 Continuous Integration Readiness

From Wave 1 onward, the IIOS implementation is continuous-integration ready.
Every commit runs the full test suite for completed components. Every commit
runs the import graph analysis to detect architectural violations. Every
commit runs the security scan for the modified modules. Every commit runs
the linter for naming and consistency violations.

Continuous integration readiness is not an end-of-project requirement; it
is a Wave 1 requirement. The CI pipeline is one of the first deliverables
of the implementation. Every subsequent wave adds its tests and checks to
the pipeline. By the time the full system is implemented, the CI pipeline
has been running, maintained, and improving for the entire implementation
lifecycle. It is not assembled at the end; it grows with the system.

This approach means that the quality of the system is verifiable at any
point in the implementation. There is never a period where the system is
"untestable" or "too early for CI." The CI pipeline is the continuous
engineering conscience of the implementation.

---

## 1.8 Risk Minimization

Implementation risk is minimized through three strategies: front-loading
uncertainty resolution, back-loading complexity, and maintaining rollback
capability at every stage.

Front-loading uncertainty resolution means that the highest-uncertainty
components are addressed early in the implementation, not deferred to later
waves. If the market data feed reliability is uncertain, it is explored in
Wave 2 (Infrastructure), not Wave 12 (Market Intelligence). If the knowledge
schema design is uncertain, it is resolved in Wave 3 (Knowledge System), not
Wave 8 (Reasoning Engine). Uncertainty deferred to later waves compounds with
the complexity of later waves.

Back-loading complexity means that the most complex components — the debate
engine, the learning system, the walk-forward validator — are built late,
when all the foundation they depend on is verified and stable. Complexity
built on verified foundation is manageable. Complexity built on uncertain
foundation is uncontrollable.

Maintaining rollback capability means that at every wave, the system can be
rolled back to the previous verified state. This requires that completed waves
are tagged in version control and that deployment processes support rollback.
Rollback is not a sign of failure; it is the safety net that makes bold
implementation decisions acceptable.

---

## 1.9 Long-Term Maintainability

Every implementation decision must be evaluated not only by its immediate
correctness but by its long-term maintainability. The IIOS system has a
multi-decade operating horizon. The engineers who maintain it in Year 10
may not have been involved in its implementation. The implementation must
be legible to future engineers who were not present at creation.

Long-term maintainability is achieved through: complete documentation at every
wave (not deferred to a documentation phase that never happens); naming that
reveals intent (future engineers should not need to reverse-engineer the
naming to understand the system); structure that reflects the architecture
(the folder structure mirrors the 17-layer hierarchy; the module organization
reflects layer responsibilities); and tests that document behavior (tests
are executable specifications that explain what the system is supposed to do).

The implementation is not complete when the code runs. It is complete when
a skilled engineer, encountering the code for the first time, can understand
what it does, why it does it, how it fits into the architecture, and how to
modify it safely.

---

*End of Part I*

---

# PART II — COMPLETE IMPLEMENTATION ROADMAP

## 2.1 Roadmap Overview

The IIOS implementation is organized into 20 sequential waves. Each wave
represents a complete, verifiable unit of implementation that delivers
defined engineering value. Waves follow the dependency-first order: no wave
begins until all waves it depends on are verified. The 20-wave structure
maps directly to the 17-layer architecture, with additional waves for
infrastructure, integration, optimization, and institutional expansion.

**Wave Map:**
`
Wave 1  — Core Foundation       (Prerequisite for all waves)
Wave 2  — Infrastructure        (Prerequisite for Waves 3–20)
Wave 3  — Knowledge System      (Prerequisite for Waves 4, 8)
Wave 4  — Ontology Engine       (Prerequisite for Waves 5, 6, 7, 8)
Wave 5  — Observation Engine    (Prerequisite for Waves 8, 12)
Wave 6  — Relationship Engine   (Prerequisite for Wave 8)
Wave 7  — Event Engine          (Prerequisite for Waves 8, 17)
Wave 8  — Reasoning Engine      (Prerequisite for Waves 9, 11, 12)
Wave 9  — Decision Engine       (Prerequisite for Waves 10, 15)
Wave 10 — Portfolio Intelligence (Prerequisite for Wave 11)
Wave 11 — Risk Intelligence     (Prerequisite for Wave 15)
Wave 12 — Market Intelligence   (Prerequisite for Waves 8, 13)
Wave 13 — AI Agents             (Prerequisite for Wave 14)
Wave 14 — Learning System       (Prerequisite for Wave 18)
Wave 15 — Execution System      (Prerequisite for Waves 16, 17)
Wave 16 — Dashboard             (Prerequisite for Wave 19)
Wave 17 — Integration           (Prerequisite for Wave 19)
Wave 18 — Optimization          (Prerequisite for Wave 19)
Wave 19 — Production Readiness  (Prerequisite for Wave 20)
Wave 20 — Institutional Expansion (Terminal wave)
`

---

## 2.2 Wave 1 — Core Foundation

**Purpose:** Establish the irreducible engineering foundation on which every
subsequent wave depends: version control, CI/CD pipeline, project structure,
configuration management, logging framework, and base testing infrastructure.

**Architecture Layer:** Cross-cutting (supports all 17 layers)

**Components to Implement:**
- Repository structure following the 17-layer folder hierarchy.
- CI/CD pipeline (commit hooks, test runner, security scanner, linter).
- config.py with all architectural constants (VIX threshold, decision threshold,
  performance baselines, all named constants).
- Logging framework (structured logging, log levels, rotation).
- Base exception hierarchy (all exception types as defined in IIOS-EXC-FRM-001).
- Shared utilities (timing utilities, decimal arithmetic helpers, date utilities).
- Base test infrastructure (test runner configuration, fixture library, mock patterns).
- Health check framework (basis for ControlTower monitoring).
- Secrets management mechanism.
- Environment configuration mechanism.

**Prerequisites:** None. Wave 1 has no engineering dependencies.

**Deliverables:**
- Fully operational CI/CD pipeline with all checks passing.
- config.py verified to contain all architectural constants.
- Logging framework producing structured output.
- Exception hierarchy complete and importable.
- Shared utilities tested and verified.
- Test infrastructure running and reporting correctly.

**Completion Criteria:**
- CI/CD pipeline runs and passes on every commit.
- All config constants documented with their architectural source.
- Logging produces parseable structured output.
- All shared utilities pass unit tests (100% coverage target for Wave 1).
- Architecture Council review completed.

**Estimated Effort:** 2–3 weeks.

**Key Risks:**
- CI/CD pipeline configuration complexity: start minimal; expand incrementally.
- Config constant proliferation: establish governance early for constant additions.

**Verification Approach:**
- CI/CD self-verifying: run CI on the CI configuration.
- Config audit: every constant has its architectural source documented.
- Logging test: produce a log entry; verify parseable structure.

---

## 2.3 Wave 2 — Infrastructure

**Purpose:** Implement the data storage, data feed, and operational infrastructure
that all domain components depend on for data persistence and retrieval.

**Architecture Layer:** Data Layer (foundational to all 17 layers)

**Components to Implement:**
- SQLite database initialization (schema creation, index creation, migration framework).
- Data feed framework: BaseFeed abstract definition, feed manager (singleton), 
  data feed registry.
- Dhan feed implementation (auth, connection, error handling, 451 detection).
- yfinance feed implementation (fallback, timeout configuration).
- Data feed auto-fallback mechanism (Dhan → yfinance on failure).
- Paper trading journal (data/paper_trades.csv mechanism).
- Backup and restoration utilities.
- Docker infrastructure (Dockerfile, docker-compose.yml, health checks).
- VPS deployment scripts.
- Environment variable management.

**Prerequisites:** Wave 1 (Core Foundation) fully verified.

**Deliverables:**
- Database initialized with complete schema and indexes.
- Both data feeds operational (Dhan and yfinance).
- Fallback mechanism verified (Dhan failure → yfinance activation).
- Paper trading journal writing correctly.
- Docker containers build and run with health checks passing.
- Backup and restore verified.

**Completion Criteria:**
- BaseFeed interface verified: get_quote, get_multiple_quotes, get_history all pass integration tests.
- Fallback tested: Dhan deliberately failed; yfinance engaged correctly.
- SQLite schema matches specification; all indexes present.
- Docker health check passes for both containers.
- Backup restoration tested and within recovery time bound.

**Estimated Effort:** 3–4 weeks.

**Key Risks:**
- Dhan API 451 error: design fallback from the beginning; do not treat as edge case.
- yfinance rate limiting: implement retry and backoff from Wave 2.
- SQLite schema evolution: establish migration framework now; schema changes later are costly.

---

## 2.4 Wave 3 — Knowledge System

**Purpose:** Implement the knowledge base — the persistent, versioned, queryable
store of all IIOS knowledge: empirical market facts, engineering-specified rules,
and learned strategic insights.

**Architecture Layer:** Knowledge Layer (foundational to Layers 1–10)

**Components to Implement:**
- Knowledge base schema (tables for knowledge items, provenance, confidence scores,
  version history, knowledge type classification).
- Knowledge item CRUD operations (create, read, update-via-new-version, deprecate).
- Provenance recording mechanism.
- Confidence score validation (0.0–1.0 range enforcement).
- Knowledge versioning (each update creates a new version; previous versions accessible).
- Knowledge contradiction detection (automated check for contradictory items).
- Knowledge staleness tracking (age of each item tracked; staleness threshold alert).
- Knowledge query interface (by type, by topic, by regime, by confidence range).
- Knowledge backup and restoration.
- Knowledge integrity check utility.

**Prerequisites:** Wave 2 (Infrastructure) fully verified.

**Deliverables:**
- Knowledge base schema initialized.
- All CRUD operations working and tested.
- Provenance and confidence requirements enforced at write time.
- Contradiction detection running and alerting correctly.
- Knowledge query interface tested across all query patterns.

**Completion Criteria:**
- Knowledge items without provenance are rejected at write (HARD).
- Knowledge items without confidence score are rejected at write (HARD).
- Contradiction detection correctly identifies contradictory pairs.
- Version history is complete and recoverable.
- Knowledge query returns correct results for all defined query types.
- Knowledge backup restoration verified.

**Estimated Effort:** 3–4 weeks.

**Key Risks:**
- Schema over-engineering: start simple; extend through migration.
- Contradiction definition ambiguity: define contradiction formally before implementing detection.

---

## 2.5 Wave 4 — Ontology Engine

**Purpose:** Implement the market ontology — the formal specification of entities,
relationships, events, and vocabulary — and the engine that validates knowledge
and data against this specification.

**Architecture Layer:** Ontology Layer (above Knowledge, below Reasoning)

**Components to Implement:**
- Entity registry (all IIOS entity types: Instrument, Market, Strategy, Portfolio,
  Agent, Regime, etc.).
- Relationship registry (all defined relationship types between entities).
- Event type registry (all system and domain event types).
- Attribute schema registry (attribute definitions for each entity type).
- Ontology validator (verifies knowledge items reference defined entities and relationships).
- Ontology versioning (ontology changes are versioned; version history maintained).
- Ontology consistency checker (internal contradiction detection within ontology).
- SEBI classification mapping (instrument and market types mapped to SEBI categories).
- Ontology query interface (entity by type, relationships by source/target entity).

**Prerequisites:** Wave 3 (Knowledge System) fully verified.

**Deliverables:**
- All entity types defined and registered.
- All relationship types defined and registered.
- Ontology validator operational (blocks knowledge items with undefined references).
- Ontology consistency check passing (zero internal contradictions).
- SEBI classification mapping complete and reviewed.

**Completion Criteria:**
- Every entity type used by any IIOS component is defined in the ontology.
- Every relationship type used by any IIOS component is defined in the ontology.
- Ontology validator blocks undefined entity references.
- Ontology consistency check: zero contradictions.
- SEBI alignment reviewed and confirmed.
- Architecture Council review completed.

**Estimated Effort:** 2–3 weeks.

**Key Risks:**
- Ontology scope creep: define only what the system currently uses; extend formally.
- SEBI classification ambiguity: resolve with legal review before implementing.

---

## 2.6 Wave 5 — Observation Engine

**Purpose:** Implement the observation layer — the components that receive raw
market data from the data feeds and transform it into structured, validated,
ontology-consistent observations that the reasoning engine can use.

**Architecture Layer:** Layer 1 (GlobalIntelligence) and data processing components

**Components to Implement:**
- Market data parser (transforms raw feed output into typed observation objects).
- Observation validator (validates observations against ontology; rejects invalid).
- Observation schema (typed data classes for PriceBar, TickerQuote, OptionsChain, etc.).
- GlobalSnapshot builder (assembles the GlobalSnapshot from multiple observations).
- GlobalDataAI implementation (fetch method, 5-minute cache, background pre-warm thread).
- Observation provenance recorder (all observations carry their feed source and timestamp).
- Observation storage (raw observation history in SQLite for backtesting and learning).
- Staleness detection (observations older than defined threshold flagged).
- Options chain parser (for options opportunity detection in later waves).

**Prerequisites:** Waves 2 (Infrastructure), 3 (Knowledge), 4 (Ontology) fully verified.

**Deliverables:**
- GlobalDataAI operational with verified cache behavior.
- Observations correctly typed and validated.
- Provenance recorded for all observations.
- Cache hit latency verified: <= 17ms p99.
- Options chain parsing verified against known chain structures.

**Completion Criteria:**
- GlobalDataAI.fetch() interface signature exactly matches specification.
- Cache hit path latency <= 17ms p99 in benchmark.
- Background pre-warm thread does not block the main cycle.
- Observations with undefined ontology references rejected.
- Observation storage verified: raw data recoverable from SQLite.

**Estimated Effort:** 3–4 weeks.

**Key Risks:**
- Data feed format changes: implement format abstraction so feed-specific parsing is isolated.
- Cache invalidation edge cases: test force=True, TTL expiry, and concurrent access.

---

## 2.7 Wave 6 — Relationship Engine

**Purpose:** Implement the relationship layer — the components that maintain
and query the relationships between IIOS entities: instrument correlations,
strategy-instrument mappings, portfolio-strategy allocations, and market regime associations.

**Architecture Layer:** Knowledge-Reasoning bridge

**Components to Implement:**
- Relationship store (persistent storage for all entity relationships).
- Correlation engine (computes and maintains instrument correlation matrices).
- Strategy-instrument mapping (which strategies apply to which instruments).
- Regime-strategy mapping (which strategies are appropriate in which regimes).
- Portfolio-strategy allocation tracker (which strategies are in which portfolios).
- Relationship query interface (by entity pair, by relationship type, by regime).
- Relationship update mechanism (relationships evolve as market conditions change).
- Relationship integrity checker (no orphaned relationships; no undefined entities).
- get_regime_strategy_map() singleton implementation.

**Prerequisites:** Waves 3 (Knowledge), 4 (Ontology), 5 (Observation) fully verified.

**Deliverables:**
- Correlation engine producing verified matrices.
- Strategy-instrument mappings complete and queryable.
- Regime-strategy map singleton operational.
- Relationship integrity passing on all defined test cases.

**Completion Criteria:**
- get_regime_strategy_map() singleton getter works correctly; no direct instantiation.
- Correlation matrices verified against reference data.
- All relationship types have integrity constraints enforced.
- Relationship update does not break existing valid relationships.

**Estimated Effort:** 2–3 weeks.

---

## 2.8 Wave 7 — Event Engine

**Purpose:** Implement the EventBus — the central event routing mechanism that
enables inter-layer communication — and all defined system and domain event types.

**Architecture Layer:** Layer 17 (ControlTower) — EventBus component

**Components to Implement:**
- EventBus (publish-subscribe routing; all events pass through the EventBus).
- Event type registry (all 30+ system and domain event types defined).
- Event subscription mechanism (components subscribe to event types).
- Event publication mechanism (components publish events to the EventBus).
- Event persistence (all events logged to SQLite with timestamp and payload).
- Event replay mechanism (for learning and audit purposes).
- Dead letter queue (events that cannot be delivered are queued and alerted).
- Event ordering guarantee (events from same source in publication order).
- Critical event paths verified: CYCLE_STARTED, TRADE_APPROVED, TRADE_REJECTED,
  KILL_SWITCH_ACTIVATED, REGIME_CHANGED.

**Prerequisites:** Waves 1 (Core Foundation), 2 (Infrastructure) fully verified.

**Deliverables:**
- EventBus operational: publish and subscribe working.
- All critical event types defined and tested.
- Event persistence verified: events recoverable from SQLite.
- Dead letter queue alerting on undeliverable events.

**Completion Criteria:**
- KILL_SWITCH_ACTIVATED event chain verified end-to-end.
- Zero events dropped under defined load test.
- Event ordering verified: same-source events delivered in order.
- All critical event types documented and tested.

**Estimated Effort:** 2–3 weeks.

---

## 2.9 Wave 8 — Reasoning Engine

**Purpose:** Implement the regime classification, market intelligence reasoning,
and meta-learning components that transform structured observations into
actionable market insights.

**Architecture Layer:** Layers 2 (MarketIntelligence), 3 (MetaLearning)

**Components to Implement:**
- Regime classifier (classifies current market conditions into one of 6 defined regimes:
  trending_up, trending_down, ranging, volatile, breakout, consolidating).
- MarketIntelligenceEngine (Layer 2: NIFTY/BANKNIFTY regime, sector rotation,
  liquidity conditions, scheduled events).
- MarketMonitor (continuous 30-second scan; 6 deep-scan slots).
- MetaStrategyController (Layer 3: k-NN strategy weight predictor).
- k-NN training pipeline (nightly retraining on historical regime-performance data).
- Strategy weight normalization (weights sum to 1.0 always).
- MarketIntelligence latency optimization (target <= 19ms p99).
- Regime change event emission (REGIME_CHANGED event on EventBus).

**Prerequisites:** Waves 3–7 fully verified.

**Deliverables:**
- Regime classifier producing correct regime classifications on test cases.
- MarketIntelligenceEngine cycle latency <= 19ms p99.
- MarketMonitor running on its own scheduler thread.
- MetaStrategyController k-NN weights verified on historical data.

**Completion Criteria:**
- Regime classifier accuracy >= defined threshold on labeled historical data.
- MarketIntelligence cycle latency <= 19ms p99 in benchmark.
- Strategy weights always sum to 1.0 (enforced by normalization).
- REGIME_CHANGED event emitted correctly when regime changes.
- MarketMonitor thread does not block the main trading cycle.

**Estimated Effort:** 4–5 weeks (machine learning training pipeline is complex).

---

## 2.10 Wave 9 — Decision Engine

**Purpose:** Implement the 5-agent debate system and the DecisionEngine that
applies the 6.5 threshold to produce trade approval or rejection decisions.

**Architecture Layer:** Layer 10 (DebateAndDecision)

**Components to Implement:**
- All 5 debate agents (each scoring trades from 0–10 on their respective perspective:
  momentum, value, risk, market structure, meta-learning).
- Score aggregation engine (average of all 5 agent scores).
- Decision threshold enforcement (score >= 6.5: TRADE_APPROVED; < 6.5: TRADE_REJECTED).
- Agent timeout handling (agent fails to respond within budget: score recorded as 0).
- Decision logging (all decisions: agent scores, rationale, final score, outcome).
- TRADE_APPROVED event emission.
- TRADE_REJECTED event emission with rejection reason.
- Decision isolation (each agent scores independently; no agent sees other agents' scores).
- Tie-breaking mechanism (for scores exactly at threshold: conservative approach).

**Prerequisites:** Waves 7 (Event Engine), 8 (Reasoning Engine) fully verified.

**Deliverables:**
- All 5 agents operational with independent scoring.
- Threshold correctly enforced: 6.5 boundary tested on both sides.
- All decisions logged with full context.
- Agent timeout handled: timed-out agent score = 0; decision proceeds.
- Score distribution non-degenerate: not always max or always min.

**Completion Criteria:**
- Threshold enforcement: score < 6.5 always rejected; >= 6.5 always approved (HARD test).
- All 5 agents complete before score computation (no partial aggregation).
- Decision log contains all required fields for every decision.
- Agent timeout tested: decision proceeds after timeout; score recorded as 0.
- Architecture Council review of decision logic completed.

**Estimated Effort:** 3–4 weeks.

**Key Risks:**
- Agent disagreement patterns: verify debate produces meaningful diversity.
- Score boundary edge case: exactly 6.5 is approved; 6.499 is rejected. Test explicitly.

---

## 2.11 Wave 10 — Portfolio Intelligence

**Purpose:** Implement the portfolio allocation and capital budgeting components
that determine how capital is distributed across strategies and instruments.

**Architecture Layer:** Layer 6 (CapitalRiskEngine), Layer 7 (RiskControl — Portfolio component)

**Components to Implement:**
- Strategy capital budget manager (each strategy has an isolated capital allocation).
- PortfolioAllocation (enforces concentration limits; prevents over-concentration).
- Position sizing engine (decimal arithmetic; MAX_POSITION_PCT from config.py).
- Position request schema (structured PositionRequest objects).
- Portfolio state tracker (current positions, unrealized P&L, exposure by sector/regime).
- Rebalancing trigger (conditions under which portfolio rebalancing is recommended).
- Capital budget enforcement (positions exceeding budget are blocked).
- Correlation-aware sizing (position size reduced for correlated positions).

**Prerequisites:** Waves 8 (Reasoning Engine), 9 (Decision Engine) fully verified.

**Deliverables:**
- Portfolio allocation running with correct concentration limits.
- Position sizing using decimal arithmetic throughout.
- Portfolio state accurately reflecting all open positions.

**Completion Criteria:**
- Concentration limits enforced: over-concentrated positions blocked.
- Position sizing uses decimal arithmetic: verified by code review and test.
- Portfolio state consistent with execution records.
- All position requests are structured PositionRequest objects.

**Estimated Effort:** 2–3 weeks.

---
## 2.12 Wave 11 — Risk Intelligence

**Purpose:** Implement the full risk management stack — RiskManagerAI, stress
testing, Monte Carlo simulation, and the RiskGuardian kill switch — that
protects capital and enforces all defined risk limits.

**Architecture Layer:** Layers 7 (RiskControl), 8 (MarketSimulation), 9 (RiskGuardian)

**Components to Implement:**
- RiskManagerAI (portfolio-level risk assessment; veto authority within Layer 7).
- StressTest engine (minimum 14 Monte Carlo scenarios; stress outcome distribution).
- Monte Carlo simulation (Layer 8: 14 predefined scenarios, confidence intervals).
- Scenario definitions (the 14 scenarios are fixed and documented; changes require Council).
- RiskGuardian (Layer 9, PROTECTED): kill switch logic for VIX >= 45.0 and daily loss >= 2.0%.
- Kill switch state management (readable by all layers; writable only by Layer 9).
- Kill switch event emission (KILL_SWITCH_ACTIVATED on EventBus).
- Daily P&L tracker (tracks intraday P&L against the 2.0% daily loss threshold).
- VIX monitoring integration (current VIX sourced from GlobalIntelligence).
- Risk limit enforcement (position-level stops in addition to portfolio-level kill switch).

**Prerequisites:** Waves 9 (Decision Engine), 10 (Portfolio Intelligence) fully verified.

**Deliverables:**
- RiskGuardian kill switch operational with correct thresholds.
- All 14 Monte Carlo scenarios producing output.
- Kill switch integration tested end-to-end: trigger → event → no new trades.
- Daily P&L tracker correctly computing intraday loss.

**Completion Criteria:**
- VIX >= 45.0 triggers kill switch: no new trades executed (HARD test).
- Daily loss >= 2.0% triggers kill switch: no new trades executed (HARD test).
- Kill switch does not close existing positions: verified by test.
- No Layer 1-8 component can deactivate kill switch: verified by architecture review.
- All 14 Monte Carlo scenarios produce statistically valid output distributions.
- RiskGuardian is PROTECTED: no modifications without explicit Council instruction.

**Estimated Effort:** 4–5 weeks (kill switch safety is the most critical engineering item in IIOS).

**Key Risks:**
- Kill switch edge case: VIX drops below 45.0 mid-cycle; kill switch should deactivate for next cycle.
- Monte Carlo scenario correctness: scenarios must be calibrated against historical crisis data.

---

## 2.13 Wave 12 — Market Intelligence (Deep)

**Purpose:** Implement the full depth of the MarketIntelligence layer: sector
rotation signals, liquidity conditions, scheduled events calendar, and the
continuous monitoring infrastructure.

**Architecture Layer:** Layer 2 (MarketIntelligence — full depth)

**Components to Implement:**
- Sector rotation engine (relative strength by sector; rotation signal generation).
- Liquidity condition assessment (bid-ask spread tracking; market depth signals).
- Scheduled events calendar (earnings, FOMC, RBI policy, index rebalancing).
- Event risk scoring (risk score for each upcoming event).
- Breadth multiplier (market breadth calculation; breadth-weighted signals).
- Expiry detection (weekly options expiry on correct day; Tuesday expiry correction applied).
- Options open interest analysis (OI distribution by strike; support/resistance identification).
- Deep scan orchestration (6 deep-scan slots; scan rotates across instruments).
- MarketIntelligence latency tuning (target <= 19ms p99 maintained with full depth).

**Prerequisites:** Waves 5 (Observation Engine), 8 (Reasoning Engine) fully verified.

**Deliverables:**
- Sector rotation signals generating correct directional indications on test cases.
- Liquidity conditions producing meaningful differentiation between high/low liquidity.
- Scheduled events calendar accurate for the upcoming 30-day window.
- Expiry detection correct for all tested dates including Tuesday expiry.
- Full-depth MarketIntelligence cycle latency <= 19ms p99.

**Completion Criteria:**
- Breadth multiplier verified: computation matches specification.
- Expiry detection tested for Tuesday expiry edge cases.
- Deep scan completes within the 30-second continuous scan interval.
- Latency maintained at <= 19ms p99 with full depth active.

**Estimated Effort:** 3–4 weeks.

---

## 2.14 Wave 13 — AI Agents

**Purpose:** Implement all remaining AI agents across the 17 layers: OpportunityEngine
scanner agents, arbitrage detection, strategy evolution agents, and the full
suite of analysis agents.

**Architecture Layer:** Layer 4 (OpportunityEngine), Layer 5 (StrategyLab)

**Components to Implement:**
- Equity scanner agents (scan equity universe for opportunity signals).
- Options opportunity agents (identify options strategies: spreads, straddles, etc.).
- Arbitrage detection agents (index-futures arbitrage, cash-carry opportunities).
- StrategyGeneratorAI (evolves strategy variants using configured fitness function).
- Strategy fitness evaluator (evaluates generated strategies against fitness criteria).
- min_signal_rr filter enforcement (rejects strategies below minimum risk-reward).
- MetaStrategyController integration (connects evolved strategies to k-NN weighting).
- Strategy persistence (evolved strategies saved to evolved_strategies/ after filter).
- Agent isolation testing (each agent failure does not propagate to other agents).
- Agent performance budget enforcement (each agent within its per-cycle time budget).

**Prerequisites:** Waves 8 (Reasoning Engine), 9 (Decision Engine), 12 (Market Intelligence) fully verified.

**Deliverables:**
- All scanner agents producing signals on verified test market data.
- StrategyGeneratorAI producing strategies that pass defined filters.
- min_signal_rr filter correctly rejecting below-threshold strategies.
- Agent isolation verified: one agent timeout does not block others.

**Completion Criteria:**
- All 5 equity scanner agents operational and passing integration tests.
- StrategyGeneratorAI honours explicit min_rr from JSON configuration.
- Evolved strategies only saved when all filters pass.
- Agent isolation: simulated agent failure does not propagate to cycle.
- All agent operations within per-cycle time budget.

**Estimated Effort:** 4–5 weeks.

---

## 2.15 Wave 14 — Learning System

**Purpose:** Implement the full learning infrastructure: strategy performance
tracking, auto-disable of underperforming strategies, regime-strategy learning,
and the EOD learning cycle.

**Architecture Layer:** Layers 13 (LearningSystem), 14 (PerformanceAnalytics), 15 (ResearchLab)

**Components to Implement:**
- StrategyPerformanceTracker (tracks win rate, P&L per strategy; auto-disable trigger).
- get_performance_tracker() singleton implementation.
- LearningEngine (coordinates learning activities; updates regime-strategy map).
- DrawdownAnalyzer (peak-to-trough drawdown computation using decimal arithmetic).
- WalkForwardTester (OOS walk-forward validation with configurable windows).
- ResearchLab promotion gate implementation (WinRate >= 50%, Sharpe > 0.8, MaxDD < 15%).
- ValidationEngine (Layer 16, PROTECTED): 6-stage pipeline.
- EOD learning cycle (post-market: recover CSV closed trades, update metrics, persist).
- Post-restart state recovery (state fully reconstructed from SQLite after container restart).
- Learning improvement tracking (strategy quality trends over time).

**Prerequisites:** Waves 11 (Risk Intelligence), 13 (AI Agents) fully verified.

**Deliverables:**
- StrategyPerformanceTracker correctly computing win rate and auto-disable.
- EOD cycle recovering CSV trades after restart.
- Promotion gates enforced: all three metrics must pass simultaneously.
- ValidationEngine 6-stage pipeline operational on test strategies.
- State fully recoverable from SQLite after simulated container restart.

**Completion Criteria:**
- Auto-disable triggered correctly when win rate falls below threshold.
- EOD learning cycle recovers trades from CSV correctly after restart simulation.
- All three promotion gates enforced simultaneously (not independently).
- Walk-forward tester produces OOS performance metrics matching specification.
- 6-stage validation: all stages execute; partial passes do not promote.
- ValidationEngine is PROTECTED: no modifications without explicit Council instruction.

**Estimated Effort:** 4–5 weeks.

---

## 2.16 Wave 15 — Execution System

**Purpose:** Implement the order management and execution engine that translates
approved trade decisions into broker orders, with complete paper trading support
and audit trail.

**Architecture Layer:** Layer 11 (ExecutionEngine)

**Components to Implement:**
- OrderManager (primary execution class; explicit PAPER_TRADING check).
- ZerodhaBroker simulation layer (simulation mode; no live order routing in paper mode).
- Paper trading journal (persistent CSV at data/paper_trades.csv).
- Order deduplication (SAME_ZONE pattern: blocks duplicate orders for same instrument
  at similar price levels; accesses constants as self.CONSTANT_NAME).
- Order ID generation (unique, traceable order identifiers).
- Execution confirmation logging (all executed orders logged with full context).
- Position reconciliation (executed orders reconcile against portfolio state).
- Partial fill handling (partial executions tracked and reported).
- Execution latency monitoring (execution operations logged with timing).
- Index symbol routing (NIFTY/BANKNIFTY use bare names; GLOBAL_SYMBOL_MAP routes to correct feed).

**Prerequisites:** Waves 9 (Decision Engine), 11 (Risk Intelligence) fully verified.

**Deliverables:**
- OrderManager operational with correct PAPER_TRADING gate.
- Paper trades writing to data/paper_trades.csv correctly.
- Order deduplication preventing same-zone duplicate orders.
- Index symbol routing verified: NIFTY routes to correct feed symbol.

**Completion Criteria:**
- PAPER_TRADING check explicit and tested: live broker call blocked in paper mode (HARD).
- Paper trade CSV journal: entries verified complete after execution.
- SAME_ZONE_PCT accessed as self._SAME_ZONE_PCT inside methods (class scope).
- Index symbols use bare names in GLOBAL_SYMBOL_MAP routing.
- All order constants accessed via self.CONSTANT_NAME (no bare constant references).

**Estimated Effort:** 3–4 weeks.

**Key Risks:**
- Class-level constant scope: all class-level constants must use self.CONSTANT_NAME inside methods.
  This is the pattern documented in user memory as a common production bug.

---

## 2.17 Wave 16 — Dashboard

**Purpose:** Implement the Streamlit trading dashboard that provides real-time
visibility into the system state, portfolio performance, agent activity,
and system health.

**Architecture Layer:** Layer 17 (ControlTower — Dashboard component)

**Components to Implement:**
- Streamlit dashboard application (trading-dashboard container).
- Real-time portfolio view (positions, P&L, exposure by strategy and sector).
- System health view (all 17 layers monitored; latency and status).
- Agent activity view (current debate scores, recent decisions, strategy weights).
- Performance analytics view (win rate by strategy, drawdown chart, Sharpe trend).
- Knowledge base view (recent knowledge updates, knowledge health metrics).
- Regime view (current regime classification, regime history).
- Alert view (active alerts, recent incidents).
- Telegram bot command integration (/perf, /learn, /status and all defined commands).
- Dashboard refresh rate: <= 5 seconds for all live data.

**Prerequisites:** Wave 15 (Execution System) fully verified.

**Deliverables:**
- Dashboard operational in the trading-dashboard container.
- All 6 views rendering correctly with live data.
- Telegram bot commands responding correctly.
- Dashboard refresh rate verified <= 5 seconds.

**Completion Criteria:**
- Dashboard reflects system state with <= 5-second lag.
- All 13 Telegram bot commands operational.
- Dashboard accessible without application restart when underlying data changes.
- Health view shows all 17 layers.

**Estimated Effort:** 3–4 weeks.

---

## 2.18 Wave 17 — Integration

**Purpose:** Verify that all 17 layers and supporting components operate
correctly as a unified system: end-to-end cycle testing, cross-layer event
propagation, and full pipeline verification.

**Architecture Layer:** All layers (integration verification)

**Components to Implement:**
- Master orchestrator full-cycle test (complete cycle from GlobalIntelligence to execution).
- End-to-end event propagation test (events from Wave 7 verified through all subscribers).
- Kill switch end-to-end test (VIX spike → kill switch → no execution).
- Full cycle latency measurement (target <= 172ms baseline; <= 200ms SLA).
- Pre-market initialization sequence (Layer ordering verified for pre-market setup).
- Market-hours guard (trading only during defined market hours).
- Post-market EOD learning cycle integration test.
- Scheduler integration (all 10 schedule slots verified with correct timing).
- SIGTERM handler verification (clean scheduler shutdown on signal).

**Prerequisites:** Waves 1–16 all fully verified.

**Deliverables:**
- Full cycle runs end-to-end with all 17 layers participating.
- Kill switch integration verified end-to-end.
- Full cycle latency <= 172ms baseline in benchmark.
- Pre-market, market-hours, and post-market phases all operational.

**Completion Criteria:**
- Full cycle latency p99 <= 172ms (baseline); <= 200ms (SLA).
- Kill switch integration: VIX >= 45.0 → no execution (HARD end-to-end test).
- All 10 scheduler slots execute in correct order.
- SIGTERM handler verified: clean shutdown without data loss.
- No unhandled exceptions in 1000-cycle integration test run.

**Estimated Effort:** 3–4 weeks.

---

## 2.19 Wave 18 — Optimization

**Purpose:** Profile the integrated system, identify performance bottlenecks,
and optimize to meet or exceed all performance baselines without regressing
any quality metric.

**Architecture Layer:** All layers (performance optimization)

**Optimization Targets:**
- Full cycle latency: target <= 172ms p99 (baseline); must stay <= 200ms SLA.
- GlobalIntelligence cache hit: maintain <= 17ms p99.
- MarketIntelligence cycle: maintain <= 19ms p99.
- Memory stability: < 5% growth over 8-hour session.
- Database query performance: all frequent queries within defined latency.

**Activities:**
- Profile full cycle with production-equivalent data.
- Identify top-3 latency contributors.
- Optimize without architectural change where possible.
- Architectural optimization: propose via EDR; implement with Council approval.
- Re-profile after each optimization; verify no regression.
- Memory profiling: 8-hour session simulation; identify leaks.
- Database index audit: verify indexes are used for all profiled queries.

**Completion Criteria:**
- Full cycle p99 <= 172ms baseline achieved and documented.
- GlobalIntelligence cache hit <= 17ms p99 maintained.
- MarketIntelligence <= 19ms p99 maintained.
- Memory stable over 8-hour simulation.
- No quality metric (test coverage, security) regressed during optimization.

**Estimated Effort:** 2–3 weeks.

---

## 2.20 Wave 19 — Production Readiness

**Purpose:** Complete all requirements for PRODUCTION-READY (Level 4) certification
across all certification types, including operational readiness, security hardening,
documentation completion, and Architecture Council approval.

**Architecture Layer:** All layers (production certification)

**Activities:**
- Complete all certification evidence packages for all 30 certification types.
- Security hardening: resolve all remaining CVEs; complete OWASP assessment.
- Documentation completion: all module docstrings >= 95%; all frameworks reviewed.
- Operational drill: execute all runbooks; verify MTRDs within bounds.
- DR exercise: execute disaster recovery; verify RTO/RPO met.
- Architecture Council certification review: full evidence package review.
- CI/CD deployment gate activation: production deployment requires passing certification.
- Monitoring activation: all 17 layers monitored; all alerts configured.
- Operator qualification: minimum 2 operators qualified for production operations.

**Completion Criteria:**
- TQS >= 0.90 (Test Quality Score).
- SCS >= 0.92 (System Certification Score).
- All HARD certification checks passing.
- Architecture Council unanimous PRODUCTION-READY vote.
- Both Docker containers healthy.
- All runbooks tested within 90 days.
- DR exercise completed.

**Estimated Effort:** 3–4 weeks (evidence collection and review is ongoing; final activities compress to 3 weeks).

---

## 2.21 Wave 20 — Institutional Expansion

**Purpose:** Extend IIOS beyond its initial design to achieve Level 5
(Institutional Grade) certification and support multi-market, multi-strategy,
multi-portfolio operations at institutional scale.

**Architecture Layer:** All layers (institutional extension)

**Expansion Components:**
- Multi-market support (NSE equities, BSE, Nifty derivatives, currency derivatives).
- Multi-portfolio management (separate portfolios with different mandates and risk profiles).
- Extended strategy universe (new strategy types beyond initial set).
- Expanded agent count (additional debate agents for specific market regimes).
- Advanced learning (reinforcement learning integration for strategy adaptation).
- Institutional reporting (regulatory reports, performance attribution, risk reports).
- Advanced risk analytics (factor risk models, scenario analysis beyond 14 Monte Carlo).
- High-availability deployment (multi-instance with load balancing).
- Regulatory reporting automation (SEBI reporting directly from system data).

**Prerequisites:** Wave 19 (Production Readiness) certified.

**Completion Criteria:**
- SCS >= 0.98; TQS >= 0.98 (Institutional Grade).
- Zero SOFT exceptions.
- 90-day stable operational history.
- Architecture Council institutional excellence certification.

**Estimated Effort:** Ongoing. Wave 20 has no defined completion; it is the continuous
improvement and expansion phase of IIOS operation.

---

*End of Part II*

---

# PART III — DEPENDENCY GRAPH

## 3.1 Dependency Graph Overview

The IIOS Dependency Graph defines the complete set of dependencies for every
implementation wave and major subsystem. Reading the graph correctly is essential
for understanding the critical path and identifying safe parallelism opportunities.

**Graph Notation:**
`
DEPENDS ON:    Components that must be complete before this one begins.
REQUIRED BEFORE: Components that cannot begin until this one is complete.
CAN PARALLELIZE: Components that can be built concurrently with this one.
CRITICAL PATH:   Whether this component is on the implementation critical path.
`

---

## 3.2 Wave Dependency Matrix

`
WAVE DEPENDENCY MATRIX

Wave  Name                    Depends On      Critical Path   Parallelizable With
----  ----                    ----------      -------------   -------------------
W1    Core Foundation         None            YES             None
W2    Infrastructure          W1              YES             None
W3    Knowledge System        W2              YES             W7 (Event Engine)
W4    Ontology Engine         W3              YES             None
W5    Observation Engine      W2, W3, W4      YES             W6, W7
W6    Relationship Engine     W3, W4, W5      No              W5, W7
W7    Event Engine            W1, W2          No              W3, W4, W5, W6
W8    Reasoning Engine        W3-W7           YES             None
W9    Decision Engine         W7, W8          YES             None
W10   Portfolio Intelligence  W8, W9          No              W7, W12
W11   Risk Intelligence       W9, W10         YES             W12
W12   Market Intelligence     W5, W8          No              W10, W13
W13   AI Agents               W8, W9, W12     No              W14 partial
W14   Learning System         W11, W13        No              W16 partial
W15   Execution System        W9, W11         YES             W16
W16   Dashboard               W15             No              W14, W17 partial
W17   Integration             W1-W16          YES             None
W18   Optimization            W17             YES             None
W19   Production Readiness    W18             YES             None
W20   Institutional Expansion W19             No (terminal)   Continuous
`

---

## 3.3 Critical Path Analysis

`
CRITICAL PATH: W1 → W2 → W3 → W4 → W5 → W8 → W9 → W11 → W15 → W17 → W18 → W19

This path defines the minimum implementation time. No wave on the critical path
can be accelerated by adding resources beyond a single focused team; it is a
sequential dependency chain.

Minimum critical path duration (single team, no acceleration):
W1: 3 weeks
W2: 4 weeks
W3: 4 weeks
W4: 3 weeks
W5: 4 weeks
W8: 5 weeks
W9: 4 weeks
W11: 5 weeks
W15: 4 weeks
W17: 4 weeks
W18: 3 weeks
W19: 4 weeks
Total critical path: ~47 weeks (approximately 12 months for critical path alone)

Off-critical-path waves (W6, W7, W10, W12, W13, W14, W16) overlap with
critical path waves where their dependencies are met:
W7 can begin at W1+W2 completion (alongside W3).
W6 can begin at W3+W4+W5 completion (alongside W8).
W10 can begin at W8+W9 completion (alongside W11).
W12 can begin at W5+W8 completion (alongside W11).
W13 can begin at W8+W9+W12 completion (alongside W14 start).
W16 can begin at W15 completion (alongside W17 start).
`

---

## 3.4 Subsystem Dependency Specifications

### Core Foundation Subsystem (Wave 1)

`
DEPENDS ON:
  None.

REQUIRED BEFORE:
  ALL other waves. Wave 1 is an absolute prerequisite.

CAN PARALLELIZE:
  None. Wave 1 is the starting point.

CRITICAL PATH: YES — first step.

OPTIONAL DEPENDENCIES:
  None.

FUTURE DEPENDENCIES:
  Wave 20 may extend config.py with additional institutional constants.
`

### Data Feed Subsystem (Wave 2)

`
DEPENDS ON:
  Core Foundation (Wave 1) — config.py constants, logging, exception hierarchy.

REQUIRED BEFORE:
  All waves that access market data (W3, W5, W8, W12, W15).

CAN PARALLELIZE:
  None at Wave 2. Wave 1 must be complete.

CRITICAL PATH: YES.

OPTIONAL DEPENDENCIES:
  Additional broker integrations (Wave 20) are optional extensions.

FUTURE DEPENDENCIES:
  Wave 20: multi-broker support; additional data sources.
`

### Knowledge System (Wave 3)

`
DEPENDS ON:
  Infrastructure (Wave 2) — SQLite database, environment config.

REQUIRED BEFORE:
  Ontology Engine (Wave 4) — ontology validator needs knowledge store.
  Observation Engine (Wave 5) — observations stored in knowledge-aware structures.
  Relationship Engine (Wave 6) — relationships stored in knowledge store.
  Reasoning Engine (Wave 8) — reasoning reads from knowledge store.
  Learning System (Wave 14) — learned knowledge persisted to knowledge store.

CAN PARALLELIZE:
  Event Engine (Wave 7) — shares only Wave 1+2 dependencies.

CRITICAL PATH: YES.

OPTIONAL DEPENDENCIES:
  Advanced knowledge schemas (Wave 20).
`

### Ontology Engine (Wave 4)

`
DEPENDS ON:
  Knowledge System (Wave 3) — ontology validator checks knowledge store.

REQUIRED BEFORE:
  Observation Engine (Wave 5) — observations validated against ontology.
  Relationship Engine (Wave 6) — relationships must reference defined entity types.
  Reasoning Engine (Wave 8) — regime types are ontology entities.
  AI Agents (Wave 13) — opportunity types are ontology entities.

CAN PARALLELIZE:
  None (depends on Wave 3; must complete before Waves 5, 6, 8).

CRITICAL PATH: YES.

FUTURE DEPENDENCIES:
  Wave 20: extended ontology for new market segments.
`

### Observation Engine (Wave 5)

`
DEPENDS ON:
  Infrastructure (Wave 2) — data feeds.
  Knowledge System (Wave 3) — observation storage.
  Ontology Engine (Wave 4) — observation validation.

REQUIRED BEFORE:
  Market Intelligence deep (Wave 12) — sector data, liquidity observations.
  Reasoning Engine (Wave 8) — regime classifier uses price observations.

CAN PARALLELIZE:
  Relationship Engine (Wave 6).
  Event Engine (Wave 7).

CRITICAL PATH: YES.

PERFORMANCE REQUIREMENT:
  GlobalDataAI.fetch() cache hit: <= 17ms p99. This is a HARD baseline.
`

### Event Engine (Wave 7)

`
DEPENDS ON:
  Core Foundation (Wave 1) — logging, base infrastructure.
  Infrastructure (Wave 2) — SQLite for event persistence.

REQUIRED BEFORE:
  Decision Engine (Wave 9) — TRADE_APPROVED/REJECTED events.
  Risk Intelligence (Wave 11) — KILL_SWITCH_ACTIVATED event.
  Integration (Wave 17) — end-to-end event propagation test.

CAN PARALLELIZE:
  Knowledge System (Wave 3).
  Ontology Engine (Wave 4).
  Observation Engine (Wave 5).
  Relationship Engine (Wave 6).

CRITICAL PATH: NO (off critical path; begins at W1+W2 completion).

PERFORMANCE REQUIREMENT:
  Zero events dropped. EventBus availability is a reliability requirement.
`

### Decision Engine (Wave 9)

`
DEPENDS ON:
  Event Engine (Wave 7) — events published on decision.
  Reasoning Engine (Wave 8) — regime and strategy context for scoring.

REQUIRED BEFORE:
  Portfolio Intelligence (Wave 10) — decisions produce position requests.
  Execution System (Wave 15) — execution processes approved decisions.

CAN PARALLELIZE:
  None (sequential dependency from Wave 8).

CRITICAL PATH: YES.

ARCHITECTURAL CONSTANT:
  Decision threshold = 6.5. This may not be changed without Architecture Council
  unanimous vote and an Engineering Decision Record.
`

### Risk Intelligence (Wave 11)

`
DEPENDS ON:
  Decision Engine (Wave 9) — risk assessed for approved decisions.
  Portfolio Intelligence (Wave 10) — portfolio state informs risk assessment.

REQUIRED BEFORE:
  Execution System (Wave 15) — risk must be assessed before execution.
  Learning System (Wave 14) — risk outcomes feed learning.

CAN PARALLELIZE:
  Market Intelligence deep (Wave 12).

CRITICAL PATH: YES.

PROTECTED COMPONENTS:
  RiskGuardian (Layer 9) and ValidationEngine (Layer 16) are PROTECTED.
  Modification requires explicit Architecture Council instruction.
`

### Execution System (Wave 15)

`
DEPENDS ON:
  Decision Engine (Wave 9) — only approved decisions reach execution.
  Risk Intelligence (Wave 11) — risk assessment must pass before execution.

REQUIRED BEFORE:
  Dashboard (Wave 16) — execution data feeds dashboard.
  Integration (Wave 17) — execution is the final step in end-to-end test.

CAN PARALLELIZE:
  Dashboard (Wave 16) can begin simultaneously.

CRITICAL PATH: YES.

PROTECTED COMPONENTS:
  ZerodhaBroker — modification requires explicit instruction.

IMPLEMENTATION NOTES:
  All class-level constants must be accessed as self.CONSTANT_NAME inside methods.
  PAPER_TRADING check must be explicit, not implicit.
`

---

## 3.5 Dependency Hierarchy Diagram

`
IIOS DEPENDENCY HIERARCHY

WAVE 1: CORE FOUNDATION
        |
        v
WAVE 2: INFRASTRUCTURE
        |
   +---------+----------+
   |         |          |
   v         v          v
WAVE 3:   WAVE 7:   (other W2 consumers)
KNOWLEDGE  EVENT
   |       ENGINE
   |           |
   v           |
WAVE 4:        |
ONTOLOGY       |
   |           |
   v           |
WAVE 5:   +-----------+
OBSERVATION|   WAVE 6: |
ENGINE     | RELATION  |
   |       |   ENGINE  |
   +-------+-----------+
            |
            v
        WAVE 8: REASONING ENGINE
                |
                v
           WAVE 9: DECISION ENGINE
                |         |
           +----+         +----+
           |                   |
           v                   v
     WAVE 10:            WAVE 15:
     PORTFOLIO           EXECUTION
     INTELLIGENCE        SYSTEM
           |                   |
           v                   |
     WAVE 11:                  |
     RISK INTELLIGENCE         |
           |                   |
           +--------+----------+
                    |
                    v
              WAVE 12-14: (parallel)
              MARKET INTEL
              AI AGENTS
              LEARNING
                    |
                    v
              WAVE 16: DASHBOARD
                    |
                    v
              WAVE 17: INTEGRATION
                    |
                    v
              WAVE 18: OPTIMIZATION
                    |
                    v
              WAVE 19: PRODUCTION READINESS
                    |
                    v
              WAVE 20: INSTITUTIONAL EXPANSION
                    (continuous)
`

---

*End of Part III*

# PART IV — IMPLEMENTATION STANDARDS

## 4.1 Standards Overview

Implementation standards define the engineering contract for every wave of
IIOS implementation. They answer four questions for every deliverable:
What does done mean? How is completion verified? What documentation is required?
And what happens when something fails? These standards apply uniformly across
all 20 waves. No wave is exempt. No exception exists without Architecture Council approval.

---

## 4.2 Completion Criteria

A wave is complete when all of the following are true, without exception:

**Engineering Completion:**
1. All defined components are implemented.
2. All unit tests pass (line coverage >= 95% for all new modules).
3. All integration tests pass (all components interact correctly with their dependencies).
4. All performance tests pass (all latency targets met or documented as not applicable).
5. All security checks pass (no CRITICAL or HIGH CVEs; no secrets; no SQL injection).
6. CI/CD pipeline passes (all automated checks green).

**Documentation Completion:**
7. All new modules have complete module-level docstrings.
8. All new public classes have class docstrings.
9. All new public methods have method docstrings with parameters and return types.
10. Wave completion summary written (purpose, components, tests, known limitations).

**Governance Completion:**
11. Architecture Council review meeting conducted (all Council members present).
12. Architectural fidelity verified (import graph clean; interfaces match specification).
13. Wave completion record created (WCR: component list, test results, review record).
14. Next wave prerequisites confirmed (dependent waves can begin).

**The Architecture Council issues wave completion approval. Only after this
approval does the next wave begin. Completion is a governance event, not an
engineering estimate.**

---

## 4.3 Verification Criteria

Verification is the technical process of confirming that completion criteria
are met. For each criterion, a specific verification method applies:

| Criterion | Verification Method | Tool | Owner |
|-----------|--------------------|----|-------|
| Unit tests pass | Test runner output | pytest | Testing Team |
| Line coverage >= 95% | Coverage report | pytest-cov | Testing Team |
| Integration tests pass | Integration test runner | pytest | Testing Team |
| Latency targets met | Benchmark suite output | Custom benchmarks | Platform Team |
| No CRITICAL CVEs | Dependency scan output | safety / pip-audit | Security Team |
| No secrets | Secret scan output | detect-secrets | Security Team |
| CI/CD passes | Pipeline status | CI/CD system | Platform Team |
| Module docstrings | Coverage scan | pydocstyle | Engineering Leads |
| Import graph clean | Import analysis output | Custom tool | Arch Council |
| Interface signatures match | Signature comparison | Custom tool | Arch Council |

**Automated Verification:** Items with automated verification run on every
commit in the CI/CD pipeline. They are not checked manually at wave completion;
they are confirmed by the CI/CD record for the wave's final commit.

**Manual Verification:** Architecture Council review (items 11–14) is conducted
in a review meeting. Evidence is reviewed; findings are documented.

---

## 4.4 Acceptance Criteria

Acceptance criteria define the conditions under which the Architecture Council
accepts a wave as complete and authorizes the next wave to begin.

**Wave Acceptance Gate — Architecture Council Decision Matrix:**

`
CONDITION                          AUTHORITY DECISION
---------                          ------------------
All completion criteria met:       ACCEPTED — next wave authorized.

One or more HARD criteria failed:  NOT ACCEPTED — wave not complete.
                                   Remediation required.
                                   Next wave blocked.

One or more SOFT criteria failed   CONDITIONAL — Council documents
with documented reason:            condition, authorizes next wave
                                   with remediation commitment.
                                   Remediation due at next wave start.

Architectural violation detected:  NOT ACCEPTED — architecture must be
                                   corrected before acceptance.
                                   Next wave blocked indefinitely.

Performance regression > 10%:      NOT ACCEPTED — regression must be
                                   resolved before acceptance.
`

**HARD Completion Criteria (no exceptions):**
- All unit tests pass.
- No CRITICAL or HIGH CVEs.
- No secrets in code.
- Import graph clean (no upward dependencies).
- CI/CD pipeline passes.
- Architecture Council review conducted.

**SOFT Completion Criteria (exceptions with documentation):**
- Line coverage >= 95% (exception if third-party code limits coverage).
- Latency targets met (exception with documented plan for Wave 18).
- All module docstrings complete (exception with documented remediation timeline).

---

## 4.5 Documentation Requirements

Every wave produces three mandatory documentation artifacts:

**Artifact 1 — Wave Specification (pre-implementation):**
Written before implementation begins. Contains:
- Wave purpose and scope.
- Component list with descriptions.
- Dependency list (all waves that must be complete).
- Expected deliverables.
- Acceptance criteria (wave-specific application of the standard criteria).
- Estimated effort.
- Key risks.

**Artifact 2 — Wave Implementation Log (during implementation):**
Maintained throughout implementation. Contains:
- Daily or significant-change updates.
- Decisions made (with rationale).
- Issues encountered and resolved.
- Deviations from specification (with justification or EDR reference).

**Artifact 3 — Wave Completion Record (post-implementation):**
Written at wave completion. Contains:
- Actual components implemented (may differ from plan with documentation).
- Test results summary (coverage numbers, pass/fail counts).
- Performance benchmark results.
- Security scan results.
- Known limitations or deferred items.
- Architecture Council review outcome.
- Approval date and approvers.

**Documentation is not optional.** Wave completion is not accepted without all
three artifacts. Artifacts are stored in the repository under docs/waves/.

---

## 4.6 Engineering Checkpoints

Engineering checkpoints are mandatory mid-wave reviews that prevent implementation
from diverging from the specification before wave completion review.

**Checkpoint 1 — Design Review (Wave day 3–5):**
Architecture Council reviews the detailed implementation design before significant
code is written. Finds design-level architectural violations early.

**Checkpoint 2 — Integration Preview (Wave midpoint):**
Components partially complete are reviewed against their dependency interfaces.
Integration issues are found while code is still being written, not at completion.

**Checkpoint 3 — Security Review (Wave day -5 to -3, before completion):**
Security scan run; findings addressed before completion review.
Security issues discovered at completion review add 1–2 weeks to the wave.

**Checkpoint 4 — Performance Review (Wave day -3 to -1, before completion):**
Latency benchmarks run against completed components; regressions addressed
before completion review.

**The checkpoint cadence is determined per wave based on estimated effort.
For a 4-week wave: checkpoints at days 3, 10, 22, and 26.**

---

## 4.7 Rollback Policy

Every wave completion produces a rollback point. If a subsequent wave introduces
a regression or incompatibility, the system can be rolled back to the previous
wave's state.

**Rollback Trigger Conditions:**
- A wave introduces an architectural violation that cannot be resolved forward.
- A wave introduces a performance regression > 10% that cannot be resolved within Wave 18.
- A wave introduces a security vulnerability that cannot be resolved in the current wave.
- The Architecture Council determines a wave must be repeated with a corrected design.

**Rollback Process:**
1. Architecture Council authorizes rollback (majority vote).
2. Platform Team restores the previous wave's version tag in version control.
3. CI/CD pipeline re-runs on the previous wave's code; confirms it passes.
4. The failed wave is redesigned from the checkpoint where the root cause originated.
5. The redesigned wave is re-implemented from that checkpoint.
6. Full completion criteria re-applied.

**Rollback Constraints:**
- Rollback is to the immediately previous wave only.
- Data migrations (SQLite schema changes) that are irreversible must be addressed
  with forward migrations, not rollback.
- Rollback of more than one wave requires Architecture Council unanimous vote
  and an Engineering Decision Record.

---

## 4.8 Version Policy

Each wave completion increments the IIOS version:

`
VERSION POLICY

MAJOR version (X.0.0):
  Incremented when: A new architectural layer is added; a critical interface
  signature changes; a fundamental data structure changes.
  Authority: Architecture Council unanimous vote.
  Requires: Breaking change documentation; migration guide if needed.

MINOR version (0.X.0):
  Incremented when: A wave is completed successfully; a new non-breaking
  feature is added; a significant optimization is achieved.
  Authority: Domain owner + Architecture Council sign-off.
  Requires: Wave completion record; CHANGELOG entry.

PATCH version (0.0.X):
  Incremented when: A bug is fixed; a security patch is applied;
  a performance fix is applied.
  Authority: Domain owner.
  Requires: Fix description; test confirming fix.

PRE-RELEASE versions (1.0.0-alpha.1, 1.0.0-beta.1, 1.0.0-rc.1):
  Used during Waves 1-18 (pre-production).
  Alpha: Waves 1-8.
  Beta: Waves 9-16.
  Release Candidate: Waves 17-19.
  Stable: Wave 19 completion (PRODUCTION-READY certification).

Wave-to-Version Mapping:
  W1  complete: v0.1.0-alpha.1
  W2  complete: v0.2.0-alpha.1
  W3  complete: v0.3.0-alpha.1
  W4  complete: v0.4.0-alpha.1
  W5  complete: v0.5.0-alpha.1
  W6  complete: v0.6.0-alpha.1
  W7  complete: v0.7.0-alpha.1
  W8  complete: v0.8.0-alpha.1
  W9  complete: v0.9.0-beta.1
  W10 complete: v0.10.0-beta.1
  W11 complete: v0.11.0-beta.1
  W12 complete: v0.12.0-beta.1
  W13 complete: v0.13.0-beta.2
  W14 complete: v0.14.0-beta.2
  W15 complete: v0.15.0-beta.3
  W16 complete: v0.16.0-rc.1
  W17 complete: v0.17.0-rc.1
  W18 complete: v0.18.0-rc.2
  W19 complete: v1.0.0 (STABLE — PRODUCTION-READY)
  W20 ongoing:  v1.X.0 (institutional expansion)
`

---

*End of Part IV*

---

# PART V — MILESTONE FRAMEWORK

## 5.1 Milestone Philosophy

Milestones are the architectural waypoints of the IIOS implementation. They
are not simply wave completions; they are transitions between fundamental
operational states. A milestone marks the point at which IIOS can do something
it could not do before — not just incrementally better, but categorically different.

Each milestone has a name, a definition, a set of waves that must be complete,
entry criteria, exit criteria, operational capabilities unlocked, and a
certification level requirement.

---

## 5.2 Milestone 1 — Foundation Complete

**Definition:** The irreducible technical foundation exists. The system can
receive configuration, produce structured logs, run automated tests, and manage
data. No trading capability exists, but the infrastructure that supports all
trading capability is verified.

**Waves Required:** W1 (Core Foundation), W2 (Infrastructure).

**Entry Criteria:**
- Wave 1 and Wave 2 completion records approved.

**Exit Criteria:**
- CI/CD pipeline running and passing on every commit.
- Both Docker containers building and running with health checks.
- SQLite database initialized with schema and indexes.
- Data feeds (Dhan and yfinance) operational with fallback verified.
- All architectural constants in config.py.
- Logging producing structured output.

**Operational Capabilities Unlocked:**
- Can receive and store market data.
- Can persist engineering data to SQLite.
- Can run automated tests continuously.

**Certification Level:** Level 2 (VERIFIED) for infrastructure components.

**Milestone Record:** MR-001 issued by Architecture Council.

---

## 5.3 Milestone 2 — Infrastructure Complete

**Definition:** The knowledge, ontology, observation, relationship, and event
systems are complete. The system can receive, classify, validate, and store
market knowledge. The first layer of intelligence exists.

**Waves Required:** W1–W7 complete.

**Entry Criteria:**
- All Waves W1–W7 completion records approved.
- Knowledge base operational with contradiction detection running.
- Ontology validator operational.
- EventBus routing events correctly.

**Exit Criteria:**
- Knowledge base stores, versions, and queries knowledge items correctly.
- Ontology validator blocks undefined entity references.
- EventBus delivers critical events reliably (zero drops in load test).
- Observations stored with provenance.
- Relationship registry operational.

**Operational Capabilities Unlocked:**
- Can process and store market observations.
- Can validate knowledge against ontology.
- Can route system events to all subscribers.
- Can query knowledge by regime, topic, and confidence.

**Certification Level:** Level 2 (VERIFIED) for all W1–W7 components.
Level 3 (CERTIFIED) for Core Foundation and Infrastructure.

**Milestone Record:** MR-002 issued by Architecture Council.

---

## 5.4 Milestone 3 — Knowledge Complete

**Definition:** The full reasoning and intelligence layer is complete. The system
can classify market regimes, weight strategies by regime, run the complete
reasoning pipeline, and produce structured insights ready for decision-making.

**Waves Required:** W1–W8 complete.

**Entry Criteria:**
- Milestone 2 complete.
- Wave 8 (Reasoning Engine) completion record approved.
- Regime classifier validated on labeled historical data.

**Exit Criteria:**
- Market regime classified correctly on all 6 regime types.
- Strategy weights correct and summing to 1.0.
- MarketIntelligence cycle latency <= 19ms p99.
- k-NN model validated on OOS data.
- MarketMonitor running independently of main cycle.

**Operational Capabilities Unlocked:**
- Can classify the current market regime.
- Can weight strategies appropriate to the regime.
- Can run the market intelligence pipeline.
- Can process incoming market observations into regime-aware insights.

**Certification Level:** Level 3 (CERTIFIED) for W3–W8 components.

**Milestone Record:** MR-003 issued by Architecture Council.

---

## 5.5 Milestone 4 — AI Complete

**Definition:** All AI and decision-making components are complete. The full
debate system operates, all scanner agents generate signals, and the system can
produce trade decisions from market observations.

**Waves Required:** W1–W13 complete.

**Entry Criteria:**
- Milestone 3 complete.
- Waves 9–13 completion records approved.
- Decision engine tested end-to-end: observation → debate → decision.

**Exit Criteria:**
- All 5 debate agents operational and independently scoring.
- Decision threshold 6.5 correctly enforced on both sides.
- All scanner agents generating signals on test market data.
- StrategyGeneratorAI producing strategy variants within fitness criteria.
- Kill switch operational (though execution not yet present).

**Operational Capabilities Unlocked:**
- Can run the full decision pipeline from observation to TRADE_APPROVED or TRADE_REJECTED.
- Can generate strategy variants.
- Can identify trading opportunities in market data.
- Kill switch will halt new decisions when triggered.

**Certification Level:** Level 3 (CERTIFIED) for W9–W13 components.

**Paper Trading Eligibility:** With execution not yet present, the system
can be demonstrated in simulation using mocked execution.

**Milestone Record:** MR-004 issued by Architecture Council.

---

## 5.6 Milestone 5 — Decision Complete

**Definition:** The full decision and risk system is operational including
the learning system. The system can decide, risk-assess, learn from outcomes,
and evolve strategies.

**Waves Required:** W1–W14 complete.

**Entry Criteria:**
- Milestone 4 complete.
- Wave 14 (Learning System) completion record approved.
- Promotion gates operational.
- ValidationEngine 6-stage pipeline operational.

**Exit Criteria:**
- Learning system updating strategy performance metrics after each cycle.
- Auto-disable triggered correctly for underperforming strategies.
- Promotion gates enforced: all three criteria required simultaneously.
- Walk-forward tester producing OOS validation results.
- State fully recovered after simulated container restart.

**Operational Capabilities Unlocked:**
- Full decision pipeline with learning feedback.
- Strategy promotion from research to production.
- Walk-forward validation of strategies.
- Adaptive strategy weighting based on performance history.

**Certification Level:** Level 3 (CERTIFIED) for W14 components; Level 4 target for W1–W11.

**Milestone Record:** MR-005 issued by Architecture Council.

---

## 5.7 Milestone 6 — Execution Complete

**Definition:** The full execution system is operational including the dashboard
and Telegram bot. The system can execute trades (in paper mode), report on
positions and performance, and be operated remotely.

**Waves Required:** W1–W16 complete.

**Entry Criteria:**
- Milestone 5 complete.
- Waves 15 and 16 completion records approved.
- Paper trading operational end-to-end.

**Exit Criteria:**
- Paper trades executing and logging to data/paper_trades.csv.
- Dashboard showing real-time positions, P&L, and system health.
- All 13 Telegram bot commands operational.
- Full cycle latency <= 172ms p99 baseline.

**Operational Capabilities Unlocked:**
- Full paper trading operation (all 17 layers active).
- Real-time monitoring via dashboard.
- Remote monitoring and query via Telegram.
- Performance reporting operational.

**PAPER TRADING START:** From Milestone 6, IIOS is eligible to begin paper
trading operations. Paper trading generates the first real performance data
for the learning system.

**Certification Level:** Level 4 (PRODUCTION-READY) target for W1–W14; Level 3 for W15–W16.

**Milestone Record:** MR-006 issued by Architecture Council.

---

## 5.8 Milestone 7 — Production Complete

**Definition:** The system is fully integrated, optimized, and certified as
PRODUCTION-READY. All 20 waves through Wave 19 are complete. The system is
authorized for live trading operations.

**Waves Required:** W1–W19 complete.

**Entry Criteria:**
- Milestone 6 complete.
- Waves 17–19 completion records approved.
- PRODUCTION-READY certification issued by Architecture Council.

**Exit Criteria:**
- TQS >= 0.90, SCS >= 0.92.
- All HARD certification checks passing.
- Architecture Council unanimous PRODUCTION-READY vote.
- Full cycle latency <= 172ms p99 (optimized baseline).
- All runbooks tested within 90 days.
- DR exercise completed.
- Both Docker containers healthy.

**Operational Capabilities Unlocked:**
- Full production operation authorized.
- Live trading with real capital (subject to separate authorization).
- Full institutional-quality audit trail.
- Certified PRODUCTION-READY for all 30 certification types.

**LIVE TRADING AUTHORIZATION:** Milestone 7 completion is necessary but not
sufficient for live trading authorization. Separate regulatory review and
explicit Architecture Council live trading authorization are also required.

**Certification Level:** Level 4 (PRODUCTION-READY) for all components.

**Milestone Record:** MR-007 issued by Architecture Council (unanimous vote).

---

## 5.9 Milestone 8 — Institutional Grade Complete

**Definition:** The system has achieved Level 5 (Institutional Grade) certification
across all components and has a demonstrated track record of stable, high-quality
production operation.

**Waves Required:** W20 ongoing (no defined completion date for Wave 20).

**Entry Criteria:**
- Milestone 7 complete.
- Minimum 90 days of production operation at Level 4.
- Zero P1 incidents in 180 days.

**Exit Criteria:**
- TQS >= 0.98, SCS >= 0.98 for all components.
- Zero SOFT certification exceptions.
- 4-quarter performance stability demonstrated.
- Architecture Council institutional excellence certification (unanimous).

**Certification Level:** Level 5 (INSTITUTIONAL GRADE) for all components.

**Milestone Record:** MR-008 issued by Architecture Council (unanimous vote with
excellence evidence review).

---

## 5.10 Milestone Summary Table

`
MILESTONE SUMMARY

ID    Name                     Waves      Version       Status Unlocked
----  ----                     -----      -------       ----------------
MR-001  Foundation Complete    W1-W2      v0.2.0-alpha  Infrastructure ready
MR-002  Infrastructure Complete W1-W7    v0.7.0-alpha  Knowledge & events ready
MR-003  Knowledge Complete     W1-W8      v0.8.0-alpha  Reasoning ready
MR-004  AI Complete            W1-W13     v0.13.0-beta  Decision ready
MR-005  Decision Complete      W1-W14     v0.14.0-beta  Learning ready
MR-006  Execution Complete     W1-W16     v0.16.0-rc    Paper trading begins
MR-007  Production Complete    W1-W19     v1.0.0        Live trading authorized
MR-008  Institutional Grade    W1-W20+    v1.X.0        Institutional grade
`

---

*End of Part V*

---

# PART VI — RISK FRAMEWORK

## 6.1 Risk Philosophy

Implementation risk management is the discipline of identifying what could
go wrong, assessing how likely and how severe each risk is, and planning
in advance how each risk will be mitigated or responded to. In an autonomous
financial system, risk management is not optional — it is the difference between
a controlled implementation and a chaotic one.

The IIOS implementation risk framework identifies eight categories of risk:
dependency, architecture drift, knowledge inconsistency, integration failure,
testing gaps, operational, scalability, and recovery. Each category has defined
indicators, probability and impact assessments, mitigation strategies, and
response plans.

---

## 6.2 Risk Category 1 — Dependency Risks

**Description:** Dependencies that are not complete, not correct, or not available
when they are needed by a subsequent wave.

**Specific Risks:**

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Dhan API unavailable during Infrastructure wave | HIGH | HIGH | Implement yfinance fallback in same wave; test fallback first |
| Third-party library breaking change | MEDIUM | HIGH | Pin exact versions; CVE scan at every update |
| SQLite schema change cascade | MEDIUM | HIGH | Migration framework from Wave 2; no manual schema edits |
| yfinance rate limiting under load | MEDIUM | MEDIUM | Retry/backoff implemented in Wave 2 |
| Network latency to market data sources | LOW | MEDIUM | Local caching in Observation Engine |

**Response Plan:** Dependency risk is detected at Integration Preview checkpoint.
If a dependency is not available when expected, wave completion is delayed.
No wave proceeds with a missing dependency. Dependency risk response: delay
next wave, not reduce verification of current wave.

---

## 6.3 Risk Category 2 — Architecture Drift

**Description:** The implemented system diverges from the architectural specification,
creating a gap that grows with each subsequent wave.

**Specific Risks:**

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Upward cross-layer import introduced | MEDIUM | CRITICAL | Import graph analysis in CI; blocks merge |
| Critical interface signature changed | LOW | CRITICAL | Interface comparison tool in CI |
| Singleton instantiated directly | MEDIUM | HIGH | Singleton audit in Architecture Review |
| Layer latency threshold violated | MEDIUM | HIGH | Benchmark in CI; alert on regression |
| Protected module modified without instruction | LOW | CRITICAL | Code review; protected file flag in CI |

**Response Plan:** Architecture drift is a blocking issue. Any confirmed
architectural violation halts the current wave and triggers an Architecture
Council emergency session. The violation is corrected before the wave proceeds.
Architecture drift is never accepted as "technical debt to be resolved later."

---

## 6.4 Risk Category 3 — Knowledge Inconsistency

**Description:** The knowledge base develops internal inconsistencies — contradictions,
stale items, undefined references — that propagate into incorrect trading decisions.

**Specific Risks:**

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Knowledge contradiction not detected | LOW | HIGH | Automated contradiction detection; daily scan |
| Stale knowledge used in live decision | MEDIUM | HIGH | Staleness tracking; cycle-time staleness check |
| Knowledge-ontology reference mismatch | LOW | HIGH | Ontology validator at write time |
| Learned knowledge drifts from reality | MEDIUM | MEDIUM | Confidence score threshold; auto-disable |
| Provenance gap for critical knowledge | LOW | HIGH | Provenance enforcement at write time |

**Response Plan:** Knowledge inconsistency detected in production halts new
trade execution until resolved. All knowledge items are versioned; rollback
to previous knowledge state is possible.

---

## 6.5 Risk Category 4 — Integration Failure

**Description:** Components that pass their unit tests fail when integrated
with their dependencies, revealing interface incompatibilities or behavioral
assumptions.

**Specific Risks:**

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Event schema mismatch between emitter and consumer | MEDIUM | HIGH | Event schema validation in EventBus |
| Data type mismatch between feed and parser | MEDIUM | HIGH | Strong typing; type validation at boundary |
| Regime output not matching reasoning input | LOW | HIGH | Integration test: full reasoning pipeline |
| Kill switch event not received by execution | LOW | CRITICAL | End-to-end kill switch test at Wave 17 |
| Debate agent score format inconsistency | LOW | MEDIUM | Score schema validation in aggregation |

**Response Plan:** Integration failures discovered at Wave 17 (Integration) are
resolved within Wave 17. Integration failure resolution may require modifications
to one or both sides of the interface. Interface changes follow the critical
interface governance process.

---

## 6.6 Risk Category 5 — Testing Gaps

**Description:** The test suite does not cover scenarios that occur in production,
leading to undetected defects.

**Specific Risks:**

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Kill switch threshold boundary not tested | LOW | CRITICAL | Explicit boundary tests: 44.99 vs 45.0 vs 45.01 |
| Decision threshold exactly 6.5 not tested | LOW | HIGH | Explicit boundary test: 6.499, 6.5, 6.501 |
| Regime transition edge case not tested | MEDIUM | MEDIUM | Labeled historical data for all 6 regime transitions |
| Market closure/holiday not handled | MEDIUM | HIGH | Holiday calendar test fixture |
| Post-restart state recovery not tested | MEDIUM | HIGH | Restart simulation test |

**Response Plan:** Testing gaps discovered in production trigger a post-incident
review. The gap is documented, a test is written immediately, and the test
is verified before the next production deployment. Testing gaps are never
closed by a fix alone; they are closed by a fix plus a test.

---

## 6.7 Risk Category 6 — Operational Risks

**Description:** Risks to the operational continuity of the system after deployment.

**Specific Risks:**

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Container restart during market hours | MEDIUM | HIGH | Health checks; restart policy; state recovery |
| Telegram bot API rate limiting | MEDIUM | MEDIUM | Rate limiting in bot implementation |
| VPS disk full | LOW | HIGH | Disk monitoring; log rotation; retention limits |
| Docker image push failure during deployment | LOW | HIGH | Deployment rollback procedure |
| SSH key expires during emergency | LOW | HIGH | Key rotation procedure; backup access method |

**Response Plan:** Operational risks are mitigated through runbooks tested
quarterly. Each specific risk has a runbook entry. Operational drill confirms
runbook coverage and correctness.

---

## 6.8 Risk Category 7 — Scalability Risks

**Description:** Risks that the system cannot handle growth in data volume,
strategy count, instrument universe, or trading frequency.

**Specific Risks:**

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| SQLite performance degradation at volume | MEDIUM | MEDIUM | Index audit; query performance monitoring |
| Full cycle latency growth with more strategies | MEDIUM | HIGH | Latency budget per strategy; load test |
| Knowledge base size causing query slowdown | LOW | MEDIUM | Knowledge base index; query optimization |
| EventBus queue depth growing under load | LOW | MEDIUM | Queue depth monitoring; load test |
| Memory growth with more instruments | LOW | MEDIUM | Memory profiling; per-instrument memory analysis |

**Response Plan:** Scalability risks are identified in Wave 18 (Optimization)
and the Wave 20 (Institutional Expansion) planning process. Architectural
constraints that limit scalability require EDRs before expansion beyond the
designed capacity.

---

## 6.9 Risk Category 8 — Recovery Plans

**Master Recovery Decision Tree:**

`
ISSUE DETECTED
     |
     +--- Is it a CRITICAL severity? ----YES---> Immediate Architecture Council
     |                                           notification. Trading suspended.
     |                                           Emergency response team activated.
     |
     +--- Is it an architectural violation? --YES---> Wave halted.
     |                                                Architecture Council session.
     |                                                Violation corrected.
     |
     +--- Is it a data integrity issue? ---YES---> Trading suspended.
     |                                             Knowledge state rolled back.
     |                                             Integrity restored and verified.
     |
     +--- Is it a performance regression? --YES---> Profiling initiated.
     |                                              Root cause identified.
     |                                              Fix applied and benchmarked.
     |
     +--- Is it a testing gap? -----------YES---> Test written.
     |                                            Fix applied.
     |                                            Both verified.
     |
     +--- Is it an operational issue? ----YES---> Runbook followed.
                                                  If no runbook: immediate creation.
                                                  Post-incident review scheduled.
`

---

*End of Part VI*

---

# PART VII — PROGRESS TRACKING

## 7.1 Master Progress Dashboard

The Master Progress Dashboard provides a single view of IIOS implementation
status across all waves, milestones, quality metrics, and risks.

**Dashboard Structure:**

`
IIOS IMPLEMENTATION MASTER DASHBOARD

DATE: {current date}
CURRENT WAVE: {wave name}
CURRENT MILESTONE: {milestone name}
OVERALL PROGRESS: {percentage complete based on waves}

WAVE STATUS
Wave  Name                    Status           Completion Date    Version
W1    Core Foundation         [COMPLETE]       {date}             v0.1.0-alpha.1
W2    Infrastructure          [COMPLETE]       {date}             v0.2.0-alpha.1
W3    Knowledge System        [IN PROGRESS]    Target: {date}     v0.3.0-alpha.1
W4    Ontology Engine         [NOT STARTED]    Depends on W3      —
W5    Observation Engine      [NOT STARTED]    Depends on W2,3,4  —
W6    Relationship Engine     [NOT STARTED]    Depends on W3,4,5  —
W7    Event Engine            [IN PROGRESS]    Target: {date}     v0.7.0-alpha.1
...   (all 20 waves)

MILESTONE STATUS
MR-001  Foundation Complete        [COMPLETE]   {date}
MR-002  Infrastructure Complete    [IN PROGRESS]
MR-003  Knowledge Complete         [NOT STARTED]
...

QUALITY SNAPSHOT
Average Line Coverage:      ____%   (target >= 95%)
HARD Check Failures:        ___     (target = 0)
Open CRITICAL Findings:     ___     (target = 0)
Architecture Violations:    ___     (target = 0)

RISK SNAPSHOT
Open HIGH risks:            ___
Open MEDIUM risks:          ___
Risks with no mitigation:   ___     (target = 0)

CERTIFICATION STATUS
Components at Level 4:      ___
Components at Level 3:      ___
Components at Level 2:      ___
Components at Level < 2:    ___
`

---

## 7.2 Module Completion Matrix

The Module Completion Matrix tracks the implementation status of every individual
module within each wave.

`
MODULE COMPLETION MATRIX (excerpt)

Module                          Wave  Status           Coverage   Tests Passing
------                          ----  ------           --------   -------------
config.py                       W1    COMPLETE         100%       YES
logging/logger.py               W1    COMPLETE         97%        YES
exceptions/base_exceptions.py   W1    COMPLETE         100%       YES
utils/decimal_utils.py          W1    COMPLETE         100%       YES
data_feeds/base_feed.py         W2    COMPLETE         95%        YES
data_feeds/dhan_feed.py         W2    COMPLETE         91%        YES
data_feeds/yahoo_feed.py        W2    COMPLETE         95%        YES
data_feeds/data_feed_manager.py W2    COMPLETE         94%        YES
knowledge_base/knowledge_store.py W3  IN PROGRESS     72%        PARTIAL
knowledge_base/provenance.py    W3    IN PROGRESS      65%        PARTIAL
ontology/entity_registry.py     W4    NOT STARTED      —          —
...
`

---

## 7.3 Dependency Tracker

The Dependency Tracker confirms that all dependencies for the next wave are
verified before that wave begins.

`
DEPENDENCY TRACKER

Wave to Start: Wave 8 (Reasoning Engine)
Required Dependencies:
  Wave 3 Knowledge System:     STATUS: [VERIFIED / PENDING / FAILED]
  Wave 4 Ontology Engine:      STATUS: [VERIFIED / PENDING / FAILED]
  Wave 5 Observation Engine:   STATUS: [VERIFIED / PENDING / FAILED]
  Wave 6 Relationship Engine:  STATUS: [VERIFIED / PENDING / FAILED]
  Wave 7 Event Engine:         STATUS: [VERIFIED / PENDING / FAILED]

AUTHORIZATION TO BEGIN WAVE 8:
  [ ] All dependencies VERIFIED.
  [ ] Architecture Council approval for Wave 7 (final Wave 8 dependency).
  Authorization issued by: _______________ Date: ___________
`

---

## 7.4 Risk Tracker

The Risk Tracker maintains the current state of all identified implementation risks.

`
RISK TRACKER

Risk ID  Category         Description                     Prob   Impact   Status
R-001    Dependency       Dhan API 451 during W2          HIGH   HIGH     MITIGATED
R-002    Architecture     Upward import in W3              MED    CRIT     MONITORING
R-003    Knowledge        Contradiction not detected       LOW    HIGH     MITIGATED
R-004    Integration      Kill switch event not received   LOW    CRIT     PLANNED
R-005    Testing          Threshold boundary not tested    LOW    HIGH     OPEN
R-006    Operational      Container restart market hours   MED    HIGH     MITIGATED
...

STATUS DEFINITIONS:
OPEN:       Risk identified; no mitigation yet.
PLANNED:    Mitigation planned; not yet implemented.
MONITORING: Mitigation implemented; actively monitoring for trigger.
MITIGATED:  Mitigation implemented and verified effective.
CLOSED:     Risk condition no longer applies.
TRIGGERED:  Risk has materialized; response plan active.
`

---

## 7.5 Quality Tracker

The Quality Tracker monitors quality metrics across all completed waves.

`
QUALITY TRACKER

Metric                    Target    Current   Trend      Status
------                    ------    -------   -----      ------
Line Coverage (avg)       >= 95%    ____%     IMPROVING  [PASS / WARN / FAIL]
Branch Coverage (avg)     >= 90%    ____%     STABLE     [PASS / WARN / FAIL]
MC/DC (safety-critical)   100%      ____%     STABLE     [PASS / WARN / FAIL]
Max Cyclomatic Complexity  <= 15     ___       IMPROVING  [PASS / WARN / FAIL]
Code Duplication           < 5%     ____%     STABLE     [PASS / WARN / FAIL]
CRITICAL CVEs              0        ___       STABLE     [PASS / WARN / FAIL]
HIGH CVEs                  0        ___       STABLE     [PASS / WARN / FAIL]
Architecture Violations    0        ___       STABLE     [PASS / WARN / FAIL]
Full Cycle Latency p99     <= 200ms ___ms     STABLE     [PASS / WARN / FAIL]
Unhandled Exceptions       0        ___       STABLE     [PASS / WARN / FAIL]
Module Docstring Coverage  >= 95%   ____%     IMPROVING  [PASS / WARN / FAIL]
`

---

## 7.6 Certification Tracker

The Certification Tracker monitors the certification level of all components.

`
CERTIFICATION TRACKER

Component                       Level   Score   Expiry      Status
---------                       -----   -----   ------      ------
Core Foundation (W1)            L4      0.95    {date}      CERTIFIED
Infrastructure (W2)             L4      0.93    {date}      CERTIFIED
Knowledge System (W3)           L3      0.83    {date}      CERTIFIED
Ontology Engine (W4)            L2      0.74    {date}      IN REVIEW
Observation Engine (W5)         L1      —       —           STRUCTURED
Relationship Engine (W6)        L0      —       —           DRAFT
Event Engine (W7)               L3      0.81    {date}      CERTIFIED
Reasoning Engine (W8)           L0      —       —           NOT STARTED
Decision Engine (W9)            L0      —       —           NOT STARTED
...

CERTIFICATION SUMMARY:
  Level 4 components: ___
  Level 3 components: ___
  Level 2 components: ___
  Level 1 components: ___
  Level 0 components: ___

NEXT CERTIFICATION EVENTS:
  {Component}: Renewal due {date}
  {Component}: Review scheduled {date}
`

---

*End of Part VII*

# PART VIII — ENGINEERING CONSTITUTION

## 8.1 Constitution Overview

The Engineering Constitution is the irreducible set of implementation rules
that govern every engineering decision in the IIOS project. Constitution rules
have no exceptions. If a situation arises that appears to require violating a
rule, the correct response is to convene the Architecture Council, not to violate
the rule. A rule violation that is never reviewed becomes a precedent. A precedent
that is never challenged becomes a new standard. The Engineering Constitution
is protected from accumulation of invalid precedents.

**Rule Categories:**
- C.F  — Foundation Rules
- C.A  — Architecture Compliance Rules
- C.D  — Dependency Enforcement Rules
- C.V  — Verification Rules
- C.T  — Testing Rules
- C.DC — Documentation Rules
- C.CN — Configuration Rules
- C.S  — Security Rules
- C.P  — Performance Rules
- C.I  — Integration Rules
- C.DE — Deployment Rules
- C.G  — Governance Rules
- C.EV — Evolution Rules

---

## 8.2 Foundation Rules

**C.F.1 — Single Source of Truth**
All configuration values live in config.py and only in config.py. No magic
numbers, thresholds, or constants appear anywhere else. Any module that requires
a threshold imports it from config.py. This rule has no exceptions.

**C.F.2 — Layer Hierarchy is Inviolable**
The 17-layer architectural hierarchy is the canonical system structure. Lower
layer numbers provide services; higher layer numbers consume them. A layer may
import from any lower-numbered layer but never from an equal or higher-numbered
layer. This rule is enforced by automated import graph analysis in CI.

**C.F.3 — Singletons Through Factory Functions**
All singleton instances are obtained through factory functions:
get_performance_tracker(), get_regime_strategy_map(), get_telegram_bot(),
get_feed_manager(). Direct instantiation of any singleton class is prohibited.
Factory functions enforce single-instance semantics. This rule prevents
initialization race conditions and duplicate state.

**C.F.4 — Protected Modules Through Explicit Instruction**
Five protected module categories exist: risk_guardian, backtesting_ai,
validation_engine, evolved_strategies, and the data directory. These modules
are modified only when the user explicitly instructs modification. No incidental
or speculative modification occurs. This rule prevents trading-system failures
caused by unintended side-effect changes.

**C.F.5 — Interface Signatures Are Contracts**
All critical interface signatures are contracts. They may not be changed without
an Architecture Council vote and an Engineering Decision Record. The four critical
interfaces are: GlobalDataAI.fetch(), SystemMonitor.time_layer(),
MasterOrchestrator.run_full_cycle(), and BaseFeed.get_quote().

**C.F.6 — Preserve All Public Interfaces**
When modifying any module, all existing public interfaces (class names, method
signatures, return types) are preserved. If an interface must change, this
constitutes a breaking change and requires the full breaking change governance
process. Accidental interface breakage is detected by the interface comparison
tool in CI.

**C.F.7 — Smallest Effective Change**
Every modification is the smallest change that achieves the goal. Do not refactor
working code as a side effect of a bug fix. Do not rename modules as a side effect
of adding functionality. Do not reorganize imports as a side effect of adding
a constant. The Smallest Effective Change principle minimizes the risk of
unintended side effects.

---

## 8.3 Architecture Compliance Rules

**C.A.1 — Import Graph Must Be Acyclic**
The import graph must be acyclic at all times. No circular import chains are
permitted. Circular imports cause initialization failures that are difficult
to debug and often environment-dependent. CI enforces this with import graph
analysis on every commit.

**C.A.2 — Cross-Layer Communication Through Interfaces**
Layers communicate through defined interfaces, not through direct attribute
access or internal method calls. A higher layer calls a lower layer's public
interface method. It does not access internal attributes. This maintains the
abstraction boundaries that make each layer independently testable.

**C.A.3 — Class-Level Constants Accessed as self.CONSTANT**
All constants defined at class level are accessed as self.CONSTANT inside
instance methods. Bare name access (without self.) fails at runtime in the
specific code path that reaches the constant, not at import time. This produces
hard-to-reproduce bugs. All class-level constants are audited at code review.

**C.A.4 — Architecture Violations Halt Waves**
Any confirmed architectural violation immediately halts the current wave.
No new code is written on the wave until the violation is corrected and the
Architecture Council confirms the correction. Architectural violations are never
deferred as technical debt.

**C.A.5 — No Rewrites Without Explicit Instruction**
Working modules are not rewritten. A module that functions correctly is
not rewritten for reasons of style, personal preference, or theoretical
improvement. Rewriting working code is the highest-risk action available
and is only undertaken when the user explicitly instructs it.

**C.A.6 — No Module Renaming or Moving**
Module renaming or moving breaks imports across 17 layers. No module is renamed
or moved without explicit user instruction and a complete impact analysis
covering all 17 layers. If a rename is authorized, all import sites are updated
in the same commit with the rename.

**C.A.7 — No Accidental Global State**
No module introduces unintended global state. Every module that requires state
persistence manages it through the defined state persistence mechanism (SQLite,
the file system, or explicit class state). Accidental global variables cause
initialization order bugs.

**C.A.8 — EventBus as Communication Boundary**
Cross-layer events are transmitted through the EventBus, not through direct
method calls from higher layers to lower layers. The EventBus decouples
publishers from subscribers and enables the monitoring and auditing of all
significant system events.

---

## 8.4 Dependency Enforcement Rules

**C.D.1 — Dependencies Verified Before Wave Start**
No wave begins until all its declared dependencies are verified complete.
Dependency verification is a Dependency Tracker check, not an assumption.
The Architecture Council confirms dependency verification before issuing
wave start authorization.

**C.D.2 — Library Versions Are Pinned**
All external library dependencies are pinned to exact versions in
equirements.txt. Unpinned dependencies allow updates that introduce
incompatibilities or security vulnerabilities between installations.
Version updates require testing and deliberate approval.

**C.D.3 — Dependency Upgrades Are Separate Commits**
Dependency version upgrades are committed separately from feature changes.
Mixing dependency upgrades with feature changes makes bisecting failures
significantly more difficult. Each dependency upgrade commit contains only
that upgrade and its verification.

**C.D.4 — Vendor Dependencies Audited Quarterly**
All external dependencies are security-scanned quarterly using safety
and pip-audit. Critical CVE findings are addressed within 7 days. High
CVE findings are addressed within 30 days. Low findings are tracked in the
dependency risk register.

**C.D.5 — No Implicit Transitive Dependencies**
No code relies on a module that is available only because a direct dependency
happens to import it. All modules used by IIOS code are direct dependencies
declared in equirements.txt. Implicit transitive dependencies cause failures
when the direct dependency is updated.

---

## 8.5 Verification Rules

**C.V.1 — CI/CD Is the Verification Arbiter**
The CI/CD pipeline is the definitive arbiter of whether code is acceptable.
A change that passes locally but fails in CI is a failing change. A change
that fails locally but passes in CI is investigated, not deployed. All
verification results referenced in wave completion records are CI/CD outputs,
not local outputs.

**C.V.2 — Coverage Gates Are Hard Checks**
Line coverage falling below 95% on any new module is a hard CI failure that
blocks merge. Coverage targets are not aspirational — they are engineering
requirements. A PR that decreases average coverage requires documented justification
and Architecture Council acknowledgment.

**C.V.3 — Performance Benchmarks Run on Every Merge**
Performance benchmarks for all latency-sensitive paths run on every merge to
the main branch. A merge that increases GlobalIntelligence cycle time above
17ms or full cycle time above 172ms triggers a performance review before the
next merge is accepted.

**C.V.4 — Security Scan on Every Commit**
Secret detection (detect-secrets) and dependency CVE scan (safety) run on
every commit. A commit introducing a secret or a critical CVE is blocked
immediately. There is no grace period for secrets in committed code.

**C.V.5 — Architectural Fidelity Verified at Wave Completion**
The import graph analysis tool runs at wave completion as part of the
Architecture Council review. The interface comparison tool verifies that no
critical interface signature has changed since the previous wave. Both checks
must pass before wave completion is accepted.

**C.V.6 — No Self-Certification**
Engineering teams do not certify their own work. Certification is issued by
the Architecture Council after external review. Self-certification is invalid
regardless of the quality of the work being reviewed.

---

## 8.6 Testing Rules

**C.T.1 — Tests Are Written Alongside Code**
Tests are written alongside the code they verify, not after the code is
considered complete. A module is not "implemented and needs tests" — it is
either implemented and tested, or it is work in progress.

**C.T.2 — Test Names Describe Scenarios**
Test function names describe the scenario being tested, not the method being
called. 	est_risk_guardian_halts_trading_when_VIX_exceeds_45() describes
the scenario. 	est_check_kill_switch() describes the method. Scenario names
make test failures self-explanatory.

**C.T.3 — Boundary Values Are Mandatory**
Any system value with defined thresholds has mandatory boundary tests:
at the threshold minus epsilon, at the threshold exactly, and at the threshold
plus epsilon. The IIOS kill switch at VIX 45.0, the decision threshold at 6.5,
the daily loss limit at 2.0%, and all other critical thresholds require
boundary tests.

**C.T.4 — Test Fixtures Are Isolated**
Each test creates and destroys its own fixtures. Tests do not share mutable state
through module-level variables or class-level state. Test order does not affect
test results. Any test that passes in isolation but fails in sequence is a
broken test.

**C.T.5 — Integration Tests Cover the Critical Path**
Integration tests must cover the complete critical path: observation → regime
classification → strategy weighting → opportunity identification → debate →
decision → risk check → execution (paper). This path is exercised in full in
at least one integration test suite.

**C.T.6 — Recovery Is Tested**
Disaster recovery and restart procedures are tested, not assumed to work.
Every wave that introduces stateful components also introduces a test that
simulates a container restart and verifies state is fully recovered.

**C.T.7 — Kill Switch Is Tested End-to-End**
The kill switch path — from the trigger condition (VIX > 45.0 or daily loss
> 2.0%) through RiskGuardian signal emission to execution halt — is tested
end-to-end with a test that exercises the full signal chain, not mocks that
short-circuit the path.

**C.T.8 — No Testing Production Databases**
Test suites use isolated databases in temporary directories. They do not
read from or write to data/ (the production SQLite database directory).
A test that contaminates production data is a production incident waiting
to happen.

**C.T.9 — Flaky Tests Are Fixed Immediately**
A test that passes sometimes and fails sometimes is a flaky test. Flaky tests
are fixed before any other work continues. A flaky test that is ignored teaches
the team to ignore CI failures. Every CI failure is investigated.

---

## 8.7 Documentation Rules

**C.DC.1 — Module Docstrings Are Mandatory**
Every Python module has a module-level docstring describing: what the module does,
which wave introduced it, which layer it belongs to, and any critical constraints.

**C.DC.2 — Class Docstrings Are Mandatory**
Every public class has a class docstring describing: the class purpose, its
role in the IIOS architecture, key invariants, and thread-safety assumptions.

**C.DC.3 — Method Docstrings for Public Methods**
Every public method has a docstring with: description, parameters with types,
return type, exceptions raised, and side effects if any.

**C.DC.4 — Engineering Decision Records for Changes**
All changes that deviate from the specification require an Engineering Decision
Record (EDR). The EDR describes the problem, the alternatives considered,
the decision, and the rationale. EDRs live in docs/decisions/.

**C.DC.5 — Wave Artifacts Are Stored in Repository**
All three wave documentation artifacts (specification, implementation log,
completion record) are stored in docs/waves/wave-{N}/. They are committed
to the repository and become part of the permanent engineering record.

**C.DC.6 — ARCHITECTURE.md Stays Current**
ARCHITECTURE.md is updated whenever the architecture changes. It is not allowed
to drift from the implemented system. ARCHITECTURE.md review is part of every
Architecture Council wave completion review.

**C.DC.7 — CHANGELOG.md Is Updated on Every Version**
Every version increment produces a CHANGELOG.md entry. The entry includes:
version number, date, wave associated, components changed, and any breaking
changes.

---

## 8.8 Configuration Rules

**C.CN.1 — No Environment-Specific Values in Code**
Values that differ between environments (development, staging, production)
are not hardcoded. They are read from environment variables or environment
configuration files. The code is environment-agnostic; configuration is
environment-specific.

**C.CN.2 — No Secrets in Repository**
API keys, passwords, access tokens, private keys, and any other secrets are
not committed to the repository. They are managed through environment variables
set outside the repository. Secret detection runs on every commit.

**C.CN.3 — Configuration Is Validated at Startup**
All required configuration values are validated at startup before any
trading-related code runs. A missing required configuration value causes
a clean startup failure with a descriptive error, not a cryptic runtime failure
when the missing value is first accessed.

**C.CN.4 — Production Configuration Is Version-Controlled**
The template for production configuration (environment variable names and
their expected types) is version-controlled. The actual values are not.
The template enables recreating the configuration requirements at any time.

---

## 8.9 Security Rules

**C.S.1 — OWASP Top 10 Compliance**
All IIOS code complies with OWASP Top 10 security requirements. No SQL injection,
no insecure deserialization, no exposure of sensitive data, no broken access
control. Security compliance is verified at every wave completion.

**C.S.2 — Input Validation at System Boundaries**
All external input — market data, API responses, configuration values, user
commands — is validated at the point of entry. Internal functions do not
validate their inputs unless they are also called with external input.
Validation at every internal boundary is unnecessary overhead.

**C.S.3 — Least Privilege Principle**
Every component operates with the minimum permissions it requires. The Docker
container does not run as root. File system access is scoped to the working
directory. Network access is scoped to required endpoints.

**C.S.4 — Audit Trail Is Tamper-Evident**
The SQLite telemetry audit trail is append-only. No record is deleted or
modified post-insertion. Audit trail integrity is verified by hash-chaining
or equivalent mechanism.

**C.S.5 — Dependency CVEs Are Zero-Tolerance for CRITICAL/HIGH**
Critical and High CVEs in direct or transitive dependencies are resolved
within the defined SLAs: 7 days for CRITICAL, 30 days for HIGH. An unresolved
Critical CVE is an operational incident.

---

## 8.10 Performance Rules

**C.P.1 — Latency Budgets Are Non-Negotiable**
Layer latency budgets as defined in system_monitor.py are engineering
requirements, not aspirational targets. GlobalIntelligence <= 17ms.
MarketIntelligence <= 19ms. Full cycle <= 172ms (baseline), <= 200ms (SLA).
Code that violates latency budgets is not accepted.

**C.P.2 — Profile Before Optimizing**
No optimization is implemented without profiling data that confirms the target
is the actual bottleneck. Intuitive optimization without profiling data routinely
optimizes the wrong function while leaving the real bottleneck untouched.

**C.P.3 — Caching Is Intentional**
Caches are intentional design decisions with defined TTLs and invalidation
strategies. The GlobalDataAI 5-minute cache with background pre-warm is a
documented design decision. An accidental cache (a value stored in a class
attribute and never refreshed) is a bug.

**C.P.4 — Load Tests Before Production**
Every production deployment is preceded by a load test at 2x expected peak
load. Load tests confirm that performance budgets are met under stress conditions,
not only under nominal conditions.

---

## 8.11 Integration Rules

**C.I.1 — Integration Test Suite Runs Before Every Wave Completion**
The full integration test suite runs before every wave completion review.
Wave completion is not accepted if any integration test is failing, even if
all unit tests pass.

**C.I.2 — Event Schemas Are Validated**
Every event published to the EventBus is validated against its schema before
publication. An event with an incorrect schema is rejected at publication time,
not silently delivered to subscribers that then fail.

**C.I.3 — Feed Fallback Is Verified**
The Dhan-to-yfinance fallback is tested at every wave completion after
Wave 2. A failure of the primary feed that does not trigger correct fallback
behavior is an integration failure.

**C.I.4 — End-to-End Kill Switch Test**
The kill switch end-to-end test (rule C.T.7) is run at every integration test
cycle. The kill switch is never assumed to work; it is always verified.

---

## 8.12 Deployment Rules

**C.DE.1 — Every Code Change Requires a Full Deploy Cycle**
Every code modification is followed by a full deploy cycle as defined in the
copilot instructions: git add → git commit → git push → SSH deploy to VPS →
docker compose build --no-cache → docker compose down → docker compose up -d →
verify both containers healthy. This cycle has no exceptions.

**C.DE.2 — Deployment Is Complete Only When Both Containers Are Healthy**
Deployment is not complete until docker compose ps shows both containers
as Up ... (healthy). A partial deployment (one container healthy, one not)
is a production incident and must be resolved before declaring deployment complete.

**C.DE.3 — No Deployment During Market Hours Without Approval**
Deployments during Indian market hours (09:15–15:30 IST, Monday–Friday)
require explicit Architecture Council approval. Unplanned deployments during
market hours have caused production incidents in live trading systems.

**C.DE.4 — Rollback Procedure Is Tested Quarterly**
The deployment rollback procedure is tested quarterly as part of the operational
drill. A rollback procedure that has never been tested will fail at the worst
possible moment.

**C.DE.5 — --no-cache Build Is Mandatory**
docker compose build --no-cache is mandatory for all deployments. Build
cache can serve stale layers that do not include recent changes. The additional
build time is worth the elimination of mysterious "I deployed but the change
isn't there" incidents.

---

## 8.13 Governance Rules

**C.G.1 — Architecture Council Approves Waves**
No wave is declared complete without Architecture Council approval. The Council
is the governance authority for wave completion. Engineering leads cannot
self-certify wave completion.

**C.G.2 — Engineering Decision Records Are Mandatory for Deviations**
Any deviation from the specified design requires an EDR before the deviation
is implemented. "We decided to do it differently" is not an acceptable
governance record. The decision, alternatives considered, and rationale are
documented.

**C.G.3 — Retrospective After Each Milestone**
A retrospective is conducted after each milestone. Retrospectives identify
what worked, what did not, and what should change. Retrospective outputs are
implementation decisions for the next set of waves.

**C.G.4 — Risk Register Updated Weekly**
The risk register (Risk Tracker) is updated weekly. Risks are not reviewed
only at wave completion; they are actively monitored. New risks are added
as identified; resolved risks are closed with a record of the resolution.

**C.G.5 — No Unapproved External Dependencies**
External dependencies are not added without Architecture Council approval.
Each new dependency is evaluated for: license compatibility, security posture,
maintenance status, and architectural fitness.

---

## 8.14 Evolution Rules

**C.EV.1 — Additive Changes Preferred**
When adding capability, prefer adding new modules, classes, and methods over
modifying existing ones. Additive changes are lower risk because they do not
affect existing callers. Existing callers continue to work unchanged.

**C.EV.2 — Deprecation Before Removal**
Any interface that is no longer needed is deprecated (with documentation and
warning) for at least one full wave before it is removed. Removal without
deprecation is a breaking change that catches callers by surprise.

**C.EV.3 — Wave 20 Changes Are Additive Only**
Wave 20 (Institutional Expansion) introduces changes only by adding new components.
It does not modify existing Wave 1–19 components. The stability of the production
system is not compromised by institutional expansion work.

**C.EV.4 — Evolved Strategies Are Earned**
Strategies in the evolved_strategies/ directory are the product of the
evolution engine. They are not hand-authored. New evolved strategies enter
through the evolution process and the promotion gate (WinRate >= 50%,
Sharpe > 0.8, MaxDD < 15%). The promotion gate cannot be bypassed.

**C.EV.5 — Learning System Feedback Is Respected**
When the learning system auto-disables a strategy (below performance threshold),
that strategy is not manually re-enabled without explicitly addressing the
root cause of the performance failure. The learning system exists to make
objective performance decisions; circumventing it defeats its purpose.

---

*End of Part VIII*

---

# PART IX — READINESS CHECKLISTS

## 9.1 Checklist Philosophy

Readiness checklists are structured pre-condition verification tools. They
exist because engineering confidence is not a reliable signal that a system
is ready for the next stage. A checklist is a documented, repeatable
verification that the same conditions are checked consistently every time.

**Checklist Check Types:**
- HARD: Must be verified TRUE. Failure blocks progression. No exception.
- SOFT: Should be verified TRUE. Failure must be documented with remediation plan. Progression with acknowledgment.
- INFO: Information-only item. Records the state but does not affect progression.

---

## 9.2 Gate 1 — Before Coding Begins (Per Wave)

**Purpose:** Verify that all preconditions for safe implementation are present
before any code is written. Writing code before these conditions are met
multiplies the cost of discovering the problem.

`
GATE 1 — BEFORE CODING BEGINS
Wave: ____________   Date: ____________   Responsible Engineer: ____________

HARD CHECKS (must all be TRUE before coding begins):
[  ]  All dependency waves have Architecture Council completion approval.
[  ]  Dependency Tracker shows all dependencies VERIFIED.
[  ]  Wave specification document is complete and Architecture Council reviewed.
[  ]  CI/CD pipeline is passing on main branch at this moment.
[  ]  Security scan shows zero CRITICAL or HIGH CVEs on current dependencies.
[  ]  Import graph is clean (no violations in current codebase).
[  ]  Interface comparison shows no unplanned critical interface changes.
[  ]  Production data/ directory is backed up (if applicable for this wave).

SOFT CHECKS (failure requires documentation):
[  ]  Wave design review checkpoint is scheduled (Checkpoint 1).
[  ]  Test strategy for this wave is outlined in the wave specification.
[  ]  Performance benchmark baseline is recorded for comparison at completion.
[  ]  Known risks for this wave are in the Risk Tracker.

INFO:
[  ]  Estimated wave effort: _____ weeks.
[  ]  Wave start date: ____________.
[  ]  Target completion date: ____________.
[  ]  Architecture Council contact for this wave: ____________.

GATE 1 APPROVAL:
Hard checks all TRUE:           [ YES / NO ]
Soft check exceptions:          ___________________________
Gate 1 approved by:             _________________________ Date: __________
`

---

## 9.3 Gate 2 — Before Testing Begins (Per Wave)

**Purpose:** Verify that the implementation is ready for systematic testing.
Running tests before implementation is stable wastes testing effort and
produces confusing failure signals.

`
GATE 2 — BEFORE TESTING BEGINS
Wave: ____________   Date: ____________   Responsible Engineer: ____________

HARD CHECKS:
[  ]  All planned components for this wave are implemented.
[  ]  All module-level docstrings are written.
[  ]  All class-level docstrings are written.
[  ]  All public method docstrings are written.
[  ]  No import errors on any new module (all imports resolve).
[  ]  No syntax errors in any new or modified file.
[  ]  Class-level constants audit complete: all accessed as self.CONSTANT in methods.
[  ]  Factory functions used for all singleton access (no direct instantiation).

SOFT CHECKS:
[  ]  Code review by a team member not involved in implementation.
[  ]  Checkpoint 2 (Integration Preview) has been conducted.
[  ]  All EDRs for deviations from specification are written.
[  ]  Wave implementation log is current.

INFO:
[  ]  Number of new modules in this wave: _____.
[  ]  Estimated test effort: _____ days.
[  ]  Known edge cases to test: ___________________________

GATE 2 APPROVAL:
Hard checks all TRUE:           [ YES / NO ]
Soft check exceptions:          ___________________________
Gate 2 approved by:             _________________________ Date: __________
`

---

## 9.4 Gate 3 — Before Integration (Per Wave)

**Purpose:** Verify that unit-tested components are ready for integration with
their dependencies. Unit tests pass in isolation; integration testing reveals
interface and behavioral assumption failures.

`
GATE 3 — BEFORE INTEGRATION
Wave: ____________   Date: ____________   Responsible Engineer: ____________

HARD CHECKS:
[  ]  All unit tests pass (100% of test suite).
[  ]  Line coverage >= 95% for all new modules.
[  ]  Branch coverage >= 90% for all new modules.
[  ]  No CRITICAL or HIGH CVEs in dependency scan.
[  ]  No secrets detected in new or modified code.
[  ]  Import graph analysis shows no new violations.
[  ]  All critical interface signatures are unchanged.
[  ]  Checkpoint 3 (Security Review) has been conducted.

SOFT CHECKS:
[  ]  Performance benchmarks run; no regressions > 5% from baseline.
[  ]  All boundary value tests passing (VIX 45.0, threshold 6.5, loss 2.0%).
[  ]  All disaster recovery and restart tests passing.
[  ]  Checkpoint 4 (Performance Review) has been conducted.

INFO:
[  ]  Unit test pass rate: _____% (should be 100%).
[  ]  Lowest coverage module: ____________ at ____%.
[  ]  Any performance regressions: ___________________________

GATE 3 APPROVAL:
Hard checks all TRUE:           [ YES / NO ]
Soft check exceptions:          ___________________________
Gate 3 approved by:             _________________________ Date: __________
`

---

## 9.5 Gate 4 — Before Deployment (Per Wave)

**Purpose:** Verify that fully integrated code is ready for deployment.
A deployment that fails in production has significantly higher cost than
a failure caught at this gate.

`
GATE 4 — BEFORE DEPLOYMENT
Wave: ____________   Date: ____________   Responsible Engineer: ____________

HARD CHECKS:
[  ]  Full integration test suite passes (100%).
[  ]  End-to-end kill switch test passes.
[  ]  Feed fallback test passes (Dhan to yfinance).
[  ]  CI/CD pipeline passes on the wave's final commit.
[  ]  Docker image builds successfully with --no-cache.
[  ]  Both containers start and reach healthy status in staging.
[  ]  No new CRITICAL or HIGH CVEs.
[  ]  No new architectural violations.
[  ]  Architecture Council wave completion review is scheduled.
[  ]  Wave completion record is drafted (ready for final completion date).

SOFT CHECKS:
[  ]  Full cycle latency <= 172ms p99 in staging load test.
[  ]  Memory usage within expected bounds in staging load test.
[  ]  Deployment is not planned during Indian market hours (09:15–15:30 IST).
[  ]  Rollback procedure is ready and verified.

INFO:
[  ]  Deployment target: VPS at 178.18.252.24.
[  ]  Deployment command: ssh + git pull + docker compose build --no-cache + compose up.
[  ]  Post-deployment verification: docker compose ps shows both containers healthy.
[  ]  On-call contact for deployment: _________________________.

GATE 4 APPROVAL:
Hard checks all TRUE:           [ YES / NO ]
Soft check exceptions:          ___________________________
Gate 4 approved by:             _________________________ Date: __________
`

---

## 9.6 Gate 5 — Before Production Authorization

**Purpose:** The final gate before the system is authorized for live trading
operations. This gate is the most consequential; errors at this stage
involve real capital.

`
GATE 5 — BEFORE PRODUCTION AUTHORIZATION
Date: ____________   Architecture Council presiding: ____________

WAVE COMPLETION HARD CHECKS:
[  ]  All 19 waves (W1–W19) have Architecture Council completion approval.
[  ]  All 7 milestones (MR-001 through MR-007) have been issued.
[  ]  Version tag v1.0.0 has been created and pushed.
[  ]  PRODUCTION-READY certification issued by Architecture Council.

QUALITY HARD CHECKS:
[  ]  TQS >= 0.90 (Technical Quality Score from IIOS-ENG-STD-001).
[  ]  SCS >= 0.92 (Standard Compliance Score from IIOS-RCF-001).
[  ]  Zero HARD certification check failures.
[  ]  Zero CRITICAL CVEs in any dependency.
[  ]  Zero HIGH CVEs in any dependency.
[  ]  Zero architectural violations in current codebase.
[  ]  Full cycle latency <= 172ms p99 (optimized baseline).
[  ]  GlobalIntelligence latency <= 17ms p99.
[  ]  MarketIntelligence latency <= 19ms p99.

OPERATIONAL HARD CHECKS:
[  ]  Both Docker containers healthy in production.
[  ]  All runbooks tested within 90 days.
[  ]  Disaster recovery exercise completed within 90 days.
[  ]  Monitoring alerts verified (all critical alerts firing correctly in test).
[  ]  Backup and restore procedure tested within 90 days.
[  ]  All 13 Telegram bot commands operational.
[  ]  Dashboard showing correct data.

RISK HARD CHECKS:
[  ]  Risk Tracker shows zero OPEN risks (all risks MITIGATED or MONITORING).
[  ]  No TRIGGERED risks with open response plans.
[  ]  Kill switch tested end-to-end within 30 days.
[  ]  Kill switch thresholds: VIX > 45.0 and daily loss > 2.0% confirmed correct.

PAPER TRADING HARD CHECKS:
[  ]  Minimum 30 days of paper trading operation.
[  ]  Paper trading P&L reporting verified correct.
[  ]  Paper trading strategy performance tracker operational.
[  ]  At least one strategy auto-disabled and at least one strategy promoted
      through promotion gate in paper trading period.

GOVERNANCE HARD CHECKS:
[  ]  Architecture Council unanimous vote for PRODUCTION-READY.
[  ]  Regulatory review completed (if applicable).
[  ]  Risk management sign-off obtained.
[  ]  Capital allocation authorization obtained.

GATE 5 PRODUCTION AUTHORIZATION:
All HARD checks TRUE:           [ YES / NO ]
Architecture Council vote:      UNANIMOUS [ YES / NO ]
Approved by (all Council members must sign):
  _________________________  Date: __________
  _________________________  Date: __________
  _________________________  Date: __________

LIVE TRADING AUTHORIZED FROM: _________________________ (date and time)
`

---

*End of Part IX*

---

# PART X — DOCUMENT METRICS AND CLOSING

## 10.1 Document Metrics

`
DOCUMENT METRICS TABLE

Metric                                Value
------                                -----
Document Code                         IIOS-IMP-001
Document Version                      1.0
Document Status                       APPROVED
Document Classification               CONTROLLED
Issuing Authority                     Architecture Council
Issue Date                            [Date of final approval]
Review Cycle                          Quarterly or after each milestone

Parts                                 10
Sections                              70+
Milestones Defined                    8
Waves Covered                         20
Engineering Constitution Rules        90
Readiness Gates                       5
Risk Categories                       8
Implementation Standards Sections     7
Milestone Records                     8

Dependency Specifications             20 waves fully specified
Critical Path Defined                 Yes (W1→W2→W3→W4→W5→W8→W9→W11→W15→W17→W18→W19)
Critical Path Duration                47 weeks
Parallel Opportunities                W6‖W7, W10‖W11‖W12, W13‖W14, W15‖W16

Systems Referenced:
  Layers in Architecture              17
  Debate Agents                       5
  Decision Threshold                  6.5
  Kill Switch VIX Threshold           45.0
  Daily Loss Kill Switch              2.0%
  GlobalIntelligence Latency SLA      17ms p99
  MarketIntelligence Latency SLA      19ms p99
  Full Cycle Latency Baseline         172ms p99
  Full Cycle Latency SLA              200ms p99
  Promotion Gate WinRate              >= 50%
  Promotion Gate Sharpe               > 0.8
  Promotion Gate MaxDD                < 15%

Protected Modules                     5 categories
Critical Interface Signatures         4 (immutable)
Singleton Factory Functions           4
`

---

## 10.2 Amendment History

`
AMENDMENT HISTORY

Version  Date           Author              Description
-------  ----           ------              -----------
1.0      [Issue Date]   Architecture        Initial issue. All 10 parts
                        Council             drafted and approved.
                                            20 waves defined.
                                            8 milestones established.
                                            90 constitution rules codified.
                                            5 readiness gates defined.
                                            8 risk categories specified.
                                            Full dependency graph completed.
                                            Critical path computed at 47 weeks.

AMENDMENT POLICY:
Amendments to this document require Architecture Council review and approval.
An Engineering Decision Record is issued for each amendment.
The amendment history is updated in the same commit as the amendment.
Minor editorial corrections (spelling, formatting) may be made without
an Architecture Council vote, at the discretion of the Document Owner.
All other changes require Architecture Council vote.
`

---

## 10.3 Document Control

**Document Owner:** Architecture Council
**Document Category:** Implementation Roadmap
**Applicability:** All engineering teams contributing to IIOS
**Supersedes:** None (initial document)
**Superseded By:** Future version of this document, to be issued by the Architecture Council upon the next amendment.

**Related Documents:**
- IIOS-ENG-STD-001: Engineering Development Standards
- IIOS-RCF-001: Repository Certification Framework
- ARCHITECTURE.md: System Architecture Specification
- ENGINEERING_DEVELOPMENT_STANDARDS.md: Detailed engineering standards
- REPOSITORY_CERTIFICATION_FRAMEWORK.md: Certification standards

---

## 10.4 Closing Statement

The IMPLEMENTATION_MASTER_PLAN for the Investment Intelligence Operating System
defines the authoritative engineering order, standards, governance, and completion
criteria for the construction of a 17-layer, 62-agent autonomous trading system.

This document is not aspirational. Every standard defined here is enforceable.
Every checklist item is verifiable. Every rule in the Engineering Constitution is
binding. Every milestone certification is non-negotiable.

The purpose of implementation planning at this level of detail is not
bureaucratic constraint — it is engineering confidence. When a team can show that
every wave was completed against these standards, every milestone was certified
by an independent council, and every Constitution rule was followed without
exception, the resulting system earns a qualification that no amount of informal
assurance can provide: it is known to be correct.

An autonomous financial system that manages real capital must be known to be
correct. Known — not believed, not hoped, not assumed. Known through
documented verification, independent review, and repeatable process.

This document is the foundation of that knowledge.

**IMPLEMENTATION_MASTER_PLAN — END OF DOCUMENT**

*Document Code: IIOS-IMP-001 | Version: 1.0 | Status: CONTROLLED*
*Issuing Authority: Architecture Council*
*Investment Intelligence Operating System*

---

*[End of IMPLEMENTATION_MASTER_PLAN.md]*
# APPENDIX A — WAVE IMPLEMENTATION SPECIFICATIONS

## A.1 Purpose of Wave Specifications

Each wave in the IIOS implementation follows a detailed specification that
defines exactly what will be built, in what order, with what interfaces, and
verified against what success criteria. Appendix A provides the expanded
specification template and detailed component breakdowns for the most complex
waves.

---

## A.2 Expanded Wave 9 Specification — Decision Engine

**Wave 9: Decision Engine**
**Estimated Effort:** 6 weeks
**Target Version:** v0.9.0-beta.1

**Wave Purpose:**
Wave 9 implements the full multi-agent debate and decision system. The decision
engine receives structured opportunities and classified regimes, convenes the
five independent debate agents, aggregates their scored assessments, applies
the 6.5 threshold governance, and produces structured trade decision records.

**Component Specifications:**

Component 1 — OpportunityScorer
  Purpose: Scores raw opportunities from the Opportunity Engine using
  regime context, historical performance, and risk indicators.
  Input: Opportunity record from OpportunityEngine, regime classification
  from MarketIntelligence, strategy weights from MetaLearning.
  Output: Scored opportunity with confidence, regime-adjusted weight, and
  preliminary risk assessment.
  Dependencies: Wave 4 (Ontology), Wave 5 (Observation), Wave 8 (Reasoning).
  Latency budget: <= 5ms per opportunity.
  Critical constraint: Score normalization ensures all agent scores are
  on the same 0.0–10.0 scale regardless of agent internal scoring method.

Component 2 — DebateAgent base class
  Purpose: Defines the common interface for all five debate agents.
  All five agents inherit from this base class and implement a single
  abstract method: score(opportunity, context) -> AgentScore.
  Input: Scored opportunity, market context.
  Output: AgentScore with value (0.0–10.0), confidence (0.0–1.0), reasoning.
  Dependencies: Wave 8 (Reasoning Engine for context).
  Critical constraint: Agent scores are independent. Agents do not share
  state or communicate with each other. Each agent produces its score
  from its own analytical perspective.

Component 3 — BullAgent
  Purpose: Bullish bias agent. Evaluates opportunities from an optimistic
  perspective. Weights upside potential, trend continuation, momentum.
  Score range: Tends toward higher scores when trend is bullish.
  Internal methodology: Trend strength, momentum indicators, volume confirmation.

Component 4 — BearAgent
  Purpose: Bearish bias agent. Evaluates opportunities from a pessimistic
  perspective. Weights downside risk, reversal signals, distribution patterns.
  Score range: Tends toward lower scores when opportunity carries high risk.
  Internal methodology: Risk factors, reversal patterns, overbought indicators.

Component 5 — NeutralAgent
  Purpose: Balanced agent. Evaluates opportunities based on fundamental and
  statistical validity without directional bias. Weights quality of setup,
  risk-reward ratio, historical statistical validity.
  Internal methodology: Historical win rate, R:R ratio, setup quality.

Component 6 — RiskAgent
  Purpose: Risk-focused agent. Evaluates opportunities based on the risk
  they introduce to the portfolio. Weights correlation with existing positions,
  drawdown potential, tail risk.
  Internal methodology: VaR, correlation matrix, stress scenario outcomes.

Component 7 — RegimeAgent
  Purpose: Regime-alignment agent. Evaluates opportunities based on how well
  they align with the current market regime and strategy-regime map.
  Score is high when opportunity aligns with the regime; low when it conflicts.
  Internal methodology: Strategy-regime fitness, regime confidence, historical
  regime-adjusted returns.

Component 8 — DebateOrchestrator
  Purpose: Coordinates the five debate agents. Submits the same opportunity
  and context to all five agents. Collects their scores.
  Does not influence individual agent scores. Does not implement a sixth vote.
  Output: Five individual AgentScore records for aggregation.

Component 9 — ScoreAggregator
  Purpose: Aggregates the five agent scores into a single composite score.
  Default aggregation: Weighted average with equal weights (0.20 per agent).
  Future evolution: Regime-dependent agent weights (higher weight to RiskAgent
  in VOLATILE regime) is a Wave 18 optimization, not a Wave 9 feature.
  Output: CompositeScore with value (0.0–10.0), agent breakdown, and
  confidence interval.

Component 10 — DecisionEngine
  Purpose: Applies the 6.5 threshold governance to the composite score.
  CompositeScore >= 6.5: TRADE_APPROVED. CompositeScore < 6.5: TRADE_REJECTED.
  Output: TradeDecision record with approval status, composite score, all
  agent scores, timestamp, and reasoning summary.
  Critical constraint: The 6.5 threshold is imported from config.py.
  It is never hardcoded. The threshold comparison is composite_score >= 6.5
  (inclusive on the TRADE_APPROVED side).

**Acceptance Criteria:**
- All five agents produce independent scores in the correct 0.0–10.0 range.
- Score aggregation produces a composite score that is a correct weighted average.
- Threshold application correctly classifies: score 6.499 as TRADE_REJECTED,
  score 6.5 as TRADE_APPROVED, score 6.501 as TRADE_APPROVED.
- DecisionEngine produces a complete TradeDecision record.
- OpportunityScorer latency <= 5ms per opportunity (p99).
- Full debate cycle latency <= 30ms (p99) for a single opportunity.
- All five agents tested with synthetic opportunity data.

---

## A.3 Expanded Wave 11 Specification — Risk Intelligence

**Wave 11: Risk Intelligence**
**Estimated Effort:** 5 weeks
**Target Version:** v0.11.0-beta.1

**Wave Purpose:**
Wave 11 implements the complete risk management stack. The risk stack operates
between the decision engine and the execution engine, applying a series of
independent risk filters that can reject an approved trade decision before it
reaches order management.

**Risk Filter Stack (applied in order):**

Filter 1 — RiskManagerAI
  Purpose: Validates trade decisions against portfolio-level risk constraints.
  Checks: Position count, gross exposure, net exposure, sector concentration,
  instrument concentration.
  Output: RISK_APPROVED or RISK_REJECTED with reason code.
  Cannot: Override a kill switch rejection.

Filter 2 — PortfolioAllocation
  Purpose: Validates that the trade can be sized within the available capital
  allocation for the strategy budget.
  Checks: Strategy budget remaining, position size feasibility,
  capital allocation by strategy class.
  Output: ALLOCATION_APPROVED with computed position size, or ALLOCATION_REJECTED.

Filter 3 — StressTestFilter
  Purpose: Runs fast stress test on the proposed position.
  Uses Monte Carlo scenarios from Wave 8 (14 scenarios).
  Checks: Portfolio VaR impact, worst-case drawdown after adding position.
  Output: STRESS_APPROVED or STRESS_REJECTED with scenario results.
  Latency budget: <= 15ms (fast stress path, not full Monte Carlo).

Filter 4 — RiskGuardian
  Purpose: Final kill switch. Protected module. Not modified in Wave 11.
  Already operational from its initial implementation.
  Wave 11 work: Integration testing only — verify RiskGuardian correctly
  receives the EventBus KILL_SWITCH_TRIGGERED event and correctly halts
  the decision pipeline.
  Checks: VIX > 45.0, daily loss > 2.0% (imported from config.py).

**Acceptance Criteria:**
- RiskManagerAI correctly rejects positions that exceed concentration limits.
- PortfolioAllocation correctly computes position sizes within strategy budgets.
- StressTestFilter produces results within 15ms p99.
- End-to-end risk stack test: approved trade decision enters, correct
  RISK_APPROVED or RISK_REJECTED exits each filter correctly.
- Kill switch event received and execution halt confirmed.

---

## A.4 Expanded Wave 17 Specification — System Integration

**Wave 17: Integration**
**Estimated Effort:** 6 weeks
**Target Version:** v0.17.0-rc.1

**Wave Purpose:**
Wave 17 is the validation wave. It does not add significant new components;
instead it verifies that all components built in Waves 1–16 function
correctly as an integrated system. Wave 17 is the first time the entire
17-layer pipeline runs from data ingestion through execution in a systematic
integration test suite.

**Integration Test Categories:**

Category 1 — Full Pipeline Tests (end-to-end, all 17 layers)
  Test 1.1: Market data arrives → TRADE_APPROVED decision produced → paper order created.
  Test 1.2: Market data arrives → VIX > 45.0 detected → kill switch fires → no orders.
  Test 1.3: Market data arrives → daily loss > 2.0% → kill switch fires → no orders.
  Test 1.4: Strategy below performance threshold → auto-disabled → no signals from that strategy.
  Test 1.5: Container restart → state recovered → pipeline resumes correctly.

Category 2 — Data Feed Tests (Feeds + Fallback)
  Test 2.1: Dhan feed operational → all symbols return quotes.
  Test 2.2: Dhan feed returns 451 → yfinance fallback triggers automatically.
  Test 2.3: yfinance rate limit → retry with backoff → eventually succeeds.
  Test 2.4: Both feeds unavailable → clean error handling → no partial state.

Category 3 — Knowledge System Tests (Knowledge + Ontology + Contradiction)
  Test 3.1: Knowledge item with undefined ontology reference → rejected at write time.
  Test 3.2: Two contradictory knowledge items inserted → contradiction detected.
  Test 3.3: Stale knowledge item accessed after TTL → staleness warning produced.

Category 4 — Regime and Strategy Tests
  Test 4.1: Regime transitions through all 6 types → strategy weights update correctly.
  Test 4.2: k-NN weights validated on held-out historical regime data.
  Test 4.3: Strategy promoted through gate → appears in active strategy list.
  Test 4.4: Strategy auto-disabled → removed from active strategy list.

Category 5 — Event System Tests (EventBus reliability)
  Test 5.1: Critical event published → received by all subscribers.
  Test 5.2: Event with invalid schema → rejected at publication time.
  Test 5.3: High event volume → queue depth remains bounded.

Category 6 — Operational Tests (Deployment + Recovery)
  Test 6.1: Docker build succeeds with --no-cache.
  Test 6.2: Both containers reach healthy status within 60 seconds of start.
  Test 6.3: Container restart simulation → both containers recover correctly.
  Test 6.4: Full deploy procedure executed and verified.

**Acceptance Criteria:**
- All integration test categories pass.
- No category 1 (full pipeline) test failures.
- No event delivery failures under load.
- Full deploy procedure executed successfully at end of wave.

---

## A.5 Pre-Production Verification Checklist (Expanded)

The following expanded verification checklist extends Gate 5 with specific
technical evidence requirements that must be produced and attached to the
Gate 5 approval record.

**Technical Evidence Requirements:**

Evidence E1 — CI/CD Pass Record
  Description: Export of the CI/CD pipeline result for the v1.0.0 tag build.
  Must show: All stages green. Total build and test duration. Coverage numbers.
  Stored in: docs/certification/e1_cicd_pass_v1.0.0.pdf

Evidence E2 — Coverage Report
  Description: Full HTML coverage report for all IIOS modules.
  Must show: Average line coverage >= 95%. No module below 85%.
  Stored in: docs/certification/e2_coverage_report_v1.0.0/

Evidence E3 — Performance Benchmark Results
  Description: Benchmark run results for all latency-sensitive paths.
  Must show: GlobalIntelligence p99 <= 17ms. MarketIntelligence p99 <= 19ms.
  Full cycle p99 <= 172ms.
  Stored in: docs/certification/e3_benchmark_results_v1.0.0.json

Evidence E4 — Security Scan Certificates
  Description: Output of safety and detect-secrets on v1.0.0 code.
  Must show: Zero CRITICAL CVEs. Zero HIGH CVEs. Zero secrets.
  Stored in: docs/certification/e4_security_scans_v1.0.0/

Evidence E5 — Import Graph Analysis
  Description: Full import graph analysis showing no violations.
  Must show: Acyclic graph. No upward layer imports.
  Stored in: docs/certification/e5_import_graph_v1.0.0.png

Evidence E6 — Kill Switch Test Record
  Description: Test execution record for end-to-end kill switch tests.
  Must show: VIX 45.0 boundary test pass. Daily loss 2.0% boundary test pass.
  Full signal chain exercised (not mocked).
  Stored in: docs/certification/e6_kill_switch_test_v1.0.0.txt

Evidence E7 — Paper Trading Record
  Description: 30-day paper trading performance summary.
  Must show: System ran continuously for 30 trading days.
  At least one strategy auto-disabled and at least one strategy promoted.
  P&L reporting is correct (manually verified sample).
  Stored in: docs/certification/e7_paper_trading_record_v1.0.0.pdf

Evidence E8 — Architecture Council Review Minutes
  Description: Minutes from the Architecture Council wave completion reviews
  for all 19 waves and the final PRODUCTION-READY vote.
  Must show: All Council members present for PRODUCTION-READY vote.
  Unanimous approval recorded.
  Stored in: docs/certification/e8_council_minutes_v1.0.0/

Evidence E9 — Wave Completion Records
  Description: All 19 Wave Completion Records for W1–W19.
  Stored in: docs/waves/wave-{01..19}/completion_record.md

Evidence E10 — Disaster Recovery Exercise Record
  Description: Record of the most recent DR exercise.
  Must show: Exercise date within 90 days of production authorization.
  All runbooks tested. Recovery time within defined RTO.
  Stored in: docs/certification/e10_dr_exercise_v1.0.0.pdf

---

## A.6 Glossary of Implementation Terms

**Architecture Council:** The governance body responsible for approving all
architectural decisions, wave completions, and milestone certifications.
The Council is the final authority on all implementation decisions.

**Engineering Decision Record (EDR):** A document that captures a significant
engineering decision, the alternatives considered, and the rationale for the
chosen approach. Required for all deviations from specification and all
changes to critical interfaces.

**HARD Check:** A checklist item or acceptance criterion that must be satisfied
without exception. No wave proceeds, no gate is passed, and no certification
is issued if any HARD check fails.

**SOFT Check:** A checklist item or acceptance criterion that should be satisfied
but may be waived with documented justification and Architecture Council acknowledgment.

**Kill Switch:** The RiskGuardian mechanism that halts all new trade execution
when VIX exceeds 45.0 or daily portfolio loss exceeds 2.0%. The kill switch
is implemented in the protected module isk_guardian/risk_guardian.py.

**Promotion Gate:** The set of criteria a strategy must meet to be promoted
from research to production status: WinRate >= 50%, Sharpe > 0.8, MaxDD < 15%.
All three criteria must be met simultaneously.

**Singleton Factory Function:** A function that provides the single shared
instance of a singleton class. The four IIOS singleton factory functions are:
get_performance_tracker(), get_regime_strategy_map(), get_telegram_bot(),
and get_feed_manager(). Direct class instantiation is prohibited.

**Wave:** A cohesive unit of implementation that adds one complete layer or
subsystem capability to IIOS. Waves have defined dependencies, completion
criteria, and produce Architecture Council completion records.

**Wave Completion Record (WCR):** The post-implementation document that records
actual components implemented, test results, performance benchmark results,
security scan results, known limitations, and Architecture Council approval.

**yfinance Fallback:** The automatic switch from the Dhan data feed to the
yfinance data feed when the Dhan API returns a 451 status (blocked) or is
otherwise unavailable.

**17-Layer Architecture:** The canonical IIOS system structure with layers
numbered 1 (GlobalIntelligence) through 17 (ControlTower). Each layer
depends only on lower-numbered layers.

**5-Agent Debate:** The IIOS decision mechanism in which five independent agents
(BullAgent, BearAgent, NeutralAgent, RiskAgent, RegimeAgent) independently score
an opportunity and their scores are aggregated to a composite.

**6.5 Threshold:** The composite score threshold below which a trade decision
is TRADE_REJECTED and at or above which it is TRADE_APPROVED.

---

*End of Appendix A*

---