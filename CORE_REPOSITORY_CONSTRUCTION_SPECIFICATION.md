# CORE_REPOSITORY_CONSTRUCTION_SPECIFICATION.md

**Document Code:** IIOS-RCS-001
**Version:** 1.0
**Status:** CONTROLLED
**Classification:** Engineering Specification — Repository Construction Reference
**Issuing Authority:** Architecture Council
**System:** Investment Intelligence Operating System (IIOS)
**Scope:** Complete repository physical construction — folders, packages, modules, ownership, dependencies
**Related Documents:** IIOS-IMP-001, IIOS-BSS-001, IIOS-ENG-STD-001, IIOS-RCF-001, ARCHITECTURE.md

---

## Revision History

| Version | Date | Author | Description |
|---------|------|--------|-------------|
| 1.0 | 2026-07-05 | Architecture Council | Initial issue. Complete repository construction specification for all 17 layers. |

---

## Table of Contents

`
PART I     Repository Construction Philosophy .............  Section 1
PART II    Complete Repository Blueprint ..................  Section 2
PART III   Package Architecture ...........................  Section 3
PART IV    Module Organization ............................  Section 4
PART V     Dependency Framework ...........................  Section 5
PART VI    Construction Lifecycle .........................  Section 6
PART VII   Quality Framework ..............................  Section 7
PART VIII  Governance .....................................  Section 8
PART IX    Engineering Constitution .......................  Section 9
PART X     Repository Certification Checklist .............  Section 10
APPENDIX A Repository Tree Reference ......................  Appendix A
APPENDIX B Package Catalog ................................  Appendix B
APPENDIX C Dependency Matrix ..............................  Appendix C
APPENDIX D Ownership Matrix ...............................  Appendix D
APPENDIX E Construction Workflow ..........................  Appendix E
APPENDIX F Repository Anti-Patterns .......................  Appendix F
APPENDIX G Operational Runbook ............................  Appendix G
APPENDIX H Glossary .......................................  Appendix H
`

---

# PART I — REPOSITORY CONSTRUCTION PHILOSOPHY

## 1.1 Why Repository Structure Matters

Repository structure is the most consequential architectural decision made
before a single line of code is written. It determines whether the codebase
is navigable or labyrinthine, whether its dependencies are clear or hidden,
whether new engineers can orient themselves in hours or weeks, and whether
the system can grow over years without becoming unmaintainable.

For the Investment Intelligence Operating System, repository structure carries
additional weight. IIOS is a 17-layer autonomous trading system with 62 agents,
multiple independent data paths, protected modules, singleton factory constraints,
and strict import directionality. Every structural decision either reinforces
or erodes these constraints. A repository structure that allows upward imports
is a repository structure that will eventually have upward imports.

The structure is the enforcement mechanism. Not documentation. Not code review.
Not good intentions. The folder hierarchy, the package boundaries, and the
import rules built into those boundaries are what prevent the architectural
violations that kill financial software systems.

Repository structure matters because:
1. It communicates the architecture to every engineer who opens the repository.
2. It enforces dependency boundaries through physical package separation.
3. It enables independent testing of each layer without coupling to others.
4. It makes ownership unambiguous — every file belongs to exactly one domain.
5. It enables the certification process — a repository with clear structure
   is auditable; a repository without structure is not.

---

## 1.2 Architecture-Driven Construction

The IIOS repository structure is architecture-driven. This means the repository
hierarchy mirrors the 17-layer architectural hierarchy. The correspondence is
not coincidental — it is enforced. Layer N components live in Layer N packages.
Layer N packages import only from Layer N-1 and below. This structural mirror
of the architecture is what makes architectural violations detectable by
automated tooling rather than discoverable only through bugs in production.

Architecture-driven construction principles:
- Each architectural layer has exactly one corresponding package cluster.
- The package cluster for Layer N depends only on package clusters for Layers N-1 and below.
- No package cluster spans multiple layers (single-layer ownership rule).
- The layer hierarchy is encoded in the package structure, not just in documentation.

The payoff of architecture-driven construction is this: when the import graph
analysis tool runs on the repository, any architectural violation appears as
a graph edge that crosses a layer boundary upward. That edge points to a line
of code that needs to be fixed. Not a principle that needs to be re-explained.
A specific line of code.

---

## 1.3 Domain-Driven Organization

Within each architectural layer, packages are organized by domain. A domain
is the coherent set of concepts and behaviors that belong together.
Domain-driven organization means that code that changes together is located together.

IIOS domains and their ownership boundaries:
- **Intelligence Domain:** Global context acquisition, market regime classification.
- **Knowledge Domain:** Knowledge base, ontology, entity, relationship, observation.
- **Strategy Domain:** Strategy generation, backtesting, evolution, lab.
- **Risk Domain:** Capital allocation, risk management, stress testing, kill switch.
- **Decision Domain:** Debate agents, score aggregation, decision engine.
- **Execution Domain:** Order management, broker integration, trade monitoring.
- **Learning Domain:** Performance tracking, learning engine, regime strategy map.
- **Analytics Domain:** Performance analytics, walk-forward testing, drawdown analysis.
- **Research Domain:** Research lab, validation engine, promotion gates.
- **Infrastructure Domain:** Data feeds, database, cache, event bus, logging.
- **Platform Domain:** Configuration, utilities, monitoring, deployment, security.
- **Interface Domain:** Dashboard, Telegram bot, API, reporting.

Each domain owns its packages. Domain ownership means: one team (or one engineer,
in a single-engineer project) is responsible for the packages in that domain.
Cross-domain changes require the owning team's review.

---

## 1.4 Layer Isolation

Layer isolation is the physical enforcement of the principle that higher layers
depend on lower layers, never the reverse. In a repository with layer isolation:
- Each layer's packages import freely from packages in lower layers.
- Each layer's packages do not import from packages in higher layers.
- Cross-layer communication flows through defined interfaces.

Layer isolation is enforced by:
1. Package hierarchy that places lower layers deeper in the package tree.
2. Import graph analysis tool that detects upward dependencies.
3. CI/CD gate that rejects any commit introducing an upward dependency.
4. __init__.py files that export only the public interface of each package.

A common failure mode in multi-layer systems is "just this one" upward import.
An urgent fix creates an upward dependency. The fix ships. The dependency stays.
The dependency spawns children. Within six months, the architecture is a tangle.
Layer isolation prevents "just this one" from ever shipping.

---

## 1.5 High Cohesion

High cohesion means that each package contains code that belongs together —
code that serves the same purpose, changes for the same reason, and forms
a coherent unit of functionality. A highly cohesive package can be described
in one sentence. A package that cannot be described in one sentence lacks cohesion.

**IIOS Cohesion Standard:**
Each package must have a single-sentence description of its purpose that is:
- Accurate (it truly describes what the package does).
- Complete (it covers everything the package does).
- Non-redundant (it does not describe what another package does).

If a package's single-sentence description requires the word "and" to be
accurate, the package should be split. Two separate purposes belong in two
separate packages.

---

## 1.6 Low Coupling

Low coupling means that each package depends on as few other packages as possible,
and those dependencies are through narrow, stable interfaces. Low coupling enables:
- Independent testing of each package (mock the interfaces, test the package).
- Independent evolution of each package (change internals without affecting dependents).
- Independent deployment of components built around each package.

**IIOS Coupling Standard:**
Each package declares its direct dependencies in __manifest__.json.
The number of direct dependencies is tracked. Packages with more than
MAX_PACKAGE_DEPENDENCIES direct dependencies are reviewed for decomposition.
Default MAX_PACKAGE_DEPENDENCIES is 7. More than 7 direct dependencies
is a coupling warning.

---

## 1.7 Scalable Repository Design

Scalable repository design means the repository can grow from its current size
to institutional scale without requiring structural reorganization. Growth
paths are designed in, not retrofitted.

**IIOS Scalability Design Decisions:**

Decision 1 — Plugin Architecture
New capabilities (data sources, strategies, agents) are added as plugins or
registered components, not by modifying existing packages. The repository
grows by addition, not modification.

Decision 2 — Namespace Packages
The top-level iios/ namespace package can be distributed across multiple
repositories in institutional scale. Each sub-domain can become an independent
package distributed via pip. The structure supports this without reorganization.

Decision 3 — Progressive Disclosure
External consumers of IIOS packages see only the public interface defined in
each package's __init__.py. Internal modules can be reorganized without
affecting external consumers.

Decision 4 — Wave-Aligned Growth
Repository growth is wave-aligned. Each wave adds exactly the packages it
requires. No speculative packages are created. No placeholder directories.

---

## 1.8 Long-Term Maintainability

Long-term maintainability is achieved through consistency. Every package
follows the same structure. Every module follows the same layout. Every
public interface follows the same documentation standard. An engineer who
knows one package can navigate any other package.

**Maintainability Invariants:**
- Every package has: __init__.py, __manifest__.json, README.md, 	ests/.
- Every module has: module docstring, exports list in __init__.py.
- Every public class has: class docstring with single-sentence purpose.
- Every public method has: method docstring with parameters and return type.
- Every package directory name uses lowercase with underscores.
- No package directory name is a Python keyword.

---

## 1.9 Institutional-Grade Engineering

Institutional-grade engineering means the repository meets the standards
expected of financial software systems that handle real capital. These standards
include: audit trail of all changes, immutable history, protected modules,
certification records, and governance documentation.

Institutional-grade markers in the IIOS repository:
- Every commit is signed (author identity traceable).
- Protected modules are flagged in the build manifest.
- Certification records are stored in docs/certification/.
- Engineering Decision Records are stored in docs/decisions/.
- Wave completion records are stored in docs/waves/.
- The repository's structural history is never rewritten (no force-push to main).

---

## 1.10 Repository Evolution

The repository evolves through 20 waves. Each wave adds packages and modules.
Evolution rules:
1. New wave packages are added; existing packages are not reorganized.
2. A package that must be reorganized for wave N+1 produces an EDR.
3. Deprecated packages are moved to _deprecated/, not deleted.
4. Experimental packages live in experimental/ and are explicitly not production-certified.
5. The main branch always reflects a production-deployable state.

---

*End of Part I*

---

# PART II — COMPLETE REPOSITORY BLUEPRINT

## 2.1 Root Repository Structure

`
ai_trading_brain/                     (repository root — project name)
|
|-- iios/                             (main Python namespace package)
|   |-- core/                         (Layer 1-2: foundation + infrastructure)
|   |-- intelligence/                 (Layer 1-2: global + market intelligence)
|   |-- knowledge/                    (Layer 3-4: knowledge + ontology)
|   |-- observation/                  (Layer 5: observation engine)
|   |-- relationship/                 (Layer 6: relationship engine)
|   |-- events/                       (Layer 7: event engine)
|   |-- reasoning/                    (Layer 8: reasoning engine)
|   |-- strategy/                     (Layer 5+13: strategy lab + generation)
|   |-- decision/                     (Layer 10: debate + decision)
|   |-- risk/                         (Layer 6-9: capital + risk + guardian)
|   |-- execution/                    (Layer 11: order management)
|   |-- monitoring/                   (Layer 12: trade monitoring)
|   |-- learning/                     (Layer 13-14: learning + analytics)
|   |-- research/                     (Layer 15-16: research + validation)
|   |-- control/                      (Layer 17: control tower)
|   |-- agents/                       (all AI agent implementations)
|   |-- models/                       (ML models, k-NN, evolved strategies)
|   |-- simulation/                   (Monte Carlo, scenario engine)
|   |-- replay/                       (historical replay engine)
|   |-- plugins/                      (optional plugin framework)
|
|-- infrastructure/                   (non-Python infrastructure)
|   |-- database/                     (schema, migrations, seed data)
|   |-- logging/                      (logging configuration + rotation)
|   |-- security/                     (secret templates, CVE policy)
|   |-- deployment/                   (Docker, Compose, startup scripts)
|
|-- interfaces/                       (external-facing components)
|   |-- dashboard/                    (Streamlit dashboard)
|   |-- telegram/                     (Telegram bot)
|   |-- api/                          (REST API, if applicable)
|   |-- reporting/                    (report generation)
|
|-- data/                             (runtime data — NOT version controlled)
|   |-- paper_trades.csv
|   |-- main.db
|   |-- backups/
|   |-- historical/
|   |-- replay/
|   |-- exports/
|
|-- tests/                            (test suite root)
|   |-- unit/
|   |-- integration/
|   |-- performance/
|   |-- security/
|   |-- replay_tests/
|   |-- fixtures/
|
|-- docs/                             (engineering documentation)
|   |-- architecture/
|   |-- decisions/                    (EDRs)
|   |-- waves/                        (wave specs + completion records)
|   |-- certification/
|   |-- runbooks/
|   |-- api/                          (auto-generated API docs)
|
|-- scripts/                          (operational scripts)
|   |-- autostart.bat
|   |-- setup_windows_task.py
|   |-- deploy.sh
|   |-- health_check.sh
|   |-- db_backup.sh
|
|-- tools/                            (engineering tools)
|   |-- import_graph_analyzer.py
|   |-- interface_comparator.py
|   |-- module_auditor.py
|   |-- coverage_reporter.py
|   |-- manifest_validator.py
|
|-- resources/                        (static resources)
|   |-- ontology/                     (ontology definition files)
|   |-- market_calendars/             (NSE holiday calendars)
|   |-- strategy_templates/           (strategy template definitions)
|
|-- experimental/                     (non-production, not certified)
|-- _deprecated/                      (retired components, not deleted)
|-- examples/                         (usage examples, not production code)
|-- templates/                        (code and document templates)
|
|-- config.py                         (single source of truth for all config)
|-- main.py                           (entry point)
|-- requirements.txt                  (pinned dependencies)
|-- Dockerfile
|-- docker-compose.yml
|-- build_manifest.json               (protected module hashes, wave records)
|-- .github/                          (CI/CD, skills, instructions)
|-- ARCHITECTURE.md
|-- README.md
|-- CHANGELOG.md
`

---

## 2.2 iios/core/ — Core Foundation

**Purpose:** The irreducible technical foundation. Provides the shared utilities,
exception hierarchy, constants, and type definitions used by all other packages.

**Owner:** Platform Team
**IIOS Layer:** 1 (Core Foundation)
**Wave:** W1

`
iios/core/
|-- __init__.py
|-- __manifest__.json
|-- README.md
|-- exceptions/
|   |-- __init__.py
|   |-- base_exceptions.py       (BaseIIOSException, all exception classes)
|   |-- trading_exceptions.py    (TradingError, ExecutionError, ValidationError)
|   |-- data_exceptions.py       (DataFeedError, DataValidationError)
|   |-- config_exceptions.py     (ConfigurationError, MissingKeyError)
|   |-- registry_exceptions.py   (RegistrationError, DuplicateError)
|-- types/
|   |-- __init__.py
|   |-- trading_types.py         (TickerQuote, PriceBar, TradeSignal, OrderRecord)
|   |-- regime_types.py          (RegimeEnum, RegimeContext)
|   |-- score_types.py           (AgentScore, CompositeScore, TradeDecision)
|   |-- knowledge_types.py       (KnowledgeItem, OntologyEntity, ProvenanceRecord)
|   |-- common_types.py          (Timestamp, Identifier, Amount, Percentage)
|-- utils/
|   |-- __init__.py
|   |-- decimal_utils.py         (precise financial arithmetic — no float)
|   |-- datetime_utils.py        (market calendar, trading day, session)
|   |-- symbol_utils.py          (GLOBAL_SYMBOL_MAP, symbol normalization)
|   |-- validation_utils.py      (boundary validation, type coercion)
|   |-- hash_utils.py            (SHA-256 for audit trail, manifest checks)
|   |-- uuid_utils.py            (Startup ID generation, record IDs)
|-- constants/
|   |-- __init__.py
|   |-- layer_constants.py       (LAYER_NAMES, LAYER_COUNT = 17)
|   |-- regime_constants.py      (RegimeEnum values, regime names)
|   |-- market_constants.py      (NSE open/close times, lot sizes)
|-- interfaces/
|   |-- __init__.py
|   |-- base_feed.py             (BaseFeed abstract interface — PROTECTED)
|   |-- base_agent.py            (BaseAgent abstract interface)
|   |-- base_strategy.py         (BaseStrategy abstract interface)
|   |-- base_scanner.py          (BaseScanner abstract interface)
|-- tests/
|   |-- test_exceptions.py
|   |-- test_types.py
|   |-- test_utils.py
|   |-- test_constants.py
|   |-- test_interfaces.py
`

**Allowed Imports:** Python standard library only. No IIOS packages.
**Restricted Imports:** Nothing from iios.intelligence or higher layers.
**Public Interface:** All types in 	ypes/, all utils in utils/, all interfaces in interfaces/.
**Certification Requirement:** Level 4 (PRODUCTION-READY) — used by all other packages.

---

## 2.3 iios/infrastructure/ (config + data feeds + database)

**Purpose:** All infrastructure services that the trading system depends on:
configuration management, data feed management, database access, caching,
event bus, and system monitoring.

**Owner:** Platform Team
**IIOS Layer:** 2 (Infrastructure)
**Wave:** W2

`
iios/infrastructure/
|-- __init__.py
|-- __manifest__.json
|-- README.md
|-- config/
|   |-- __init__.py
|   |-- config_loader.py         (ConfigurationLoader — reads config.py)
|   |-- config_snapshot.py       (immutable ConfigurationSnapshot)
|   |-- config_validator.py      (validates all CRITICAL keys at startup)
|   |-- env_loader.py            (EnvironmentLoader — reads env vars)
|   |-- secrets_loader.py        (SecretsLoader — API tokens, never logged)
|-- data_feeds/
|   |-- __init__.py
|   |-- base_feed.py             (re-export from core.interfaces.base_feed)
|   |-- dhan_feed.py             (Dhan broker feed — PROTECTED MODULE)
|   |-- yahoo_feed.py            (yfinance fallback feed)
|   |-- data_feed_manager.py     (singleton DataFeedManager + fallback logic)
|   |-- feed_health_monitor.py   (monitors feed latency and availability)
|-- database/
|   |-- __init__.py
|   |-- connection_manager.py    (SQLite connection pool, WAL mode)
|   |-- schema_manager.py        (schema version, migrations)
|   |-- query_builder.py         (parameterized query builder — no SQL injection)
|   |-- integrity_checker.py     (PRAGMA integrity_check, index_check)
|   |-- backup_manager.py        (pre-migration backup, rotation)
|-- cache/
|   |-- __init__.py
|   |-- memory_cache.py          (ring-buffer in-memory cache)
|   |-- global_data_cache.py     (GlobalDataAI 5-minute cache + pre-warm)
|   |-- cache_policy.py          (TTL, eviction, staleness rules)
|-- event_bus/
|   |-- __init__.py
|   |-- event_bus.py             (EventBus: publish/subscribe, schema validation)
|   |-- event_schema.py          (event type definitions + schema validation)
|   |-- event_router.py          (routing table, subscriber registry)
|   |-- event_monitor.py         (queue depth, delivery latency monitoring)
|-- system_monitor/
|   |-- __init__.py
|   |-- system_monitor.py        (SystemMonitor.time_layer() — PROTECTED INTERFACE)
|   |-- latency_tracker.py       (per-layer latency history)
|   |-- performance_counter.py   (cycle latency, throughput metrics)
|-- logging_system/
|   |-- __init__.py
|   |-- logger.py                (structured logger, rotation, level control)
|   |-- startup_log.py           (startup log — first to open, last to close)
|   |-- audit_log.py             (append-only audit log, trade events)
|   |-- log_context.py           (startup ID context, structured fields)
|-- tests/
|   |-- test_config_loader.py
|   |-- test_data_feeds.py
|   |-- test_database.py
|   |-- test_event_bus.py
|   |-- test_system_monitor.py
`

**Allowed Imports:** iios.core. Python standard library. yfinance. sqlite3.
**Restricted Imports:** Nothing from iios.intelligence or higher.
**Protected Modules:** dhan_feed.py — no modification without explicit instruction.
**Public Interface:** get_feed_manager() factory function. EventBus. SystemMonitor.

---

## 2.4 iios/intelligence/ — Market Intelligence Layers

**Purpose:** Global market context acquisition (Layer 1) and NSE market
regime classification (Layer 2). These are the two outermost sensing layers
of the IIOS 17-layer architecture.

**Owner:** Intelligence Team
**IIOS Layers:** 1 (GlobalIntelligence), 2 (MarketIntelligence)
**Waves:** W1 (bootstrap stub), W2 (full implementation)

`
iios/intelligence/
|-- __init__.py
|-- __manifest__.json
|-- README.md
|-- global_intelligence/
|   |-- __init__.py
|   |-- global_data_ai.py        (GlobalDataAI — PROTECTED INTERFACE: fetch())
|   |-- global_snapshot.py       (GlobalSnapshot data structure)
|   |-- global_sources.py        (S&P, Nikkei, bonds, FX, VIX source configs)
|   |-- global_cache.py          (5-minute cache + background pre-warm thread)
|-- market_intelligence/
|   |-- __init__.py
|   |-- market_intelligence_ai.py (MarketIntelligenceAI)
|   |-- market_snapshot.py       (MarketSnapshot: NIFTY, BANKNIFTY, breadth)
|   |-- regime_classifier.py     (regime classification: 6 regime types)
|   |-- sector_analyzer.py       (sector rotation, sector weights)
|   |-- liquidity_analyzer.py    (market liquidity, bid-ask spreads)
|   |-- event_calendar.py        (scheduled market events, earnings, RBI)
|   |-- market_monitor.py        (MarketMonitor: 30s continuous scan — NEW)
|-- tests/
|   |-- test_global_data_ai.py
|   |-- test_market_intelligence.py
|   |-- test_regime_classifier.py
|   |-- test_market_monitor.py
`

**Allowed Imports:** iios.core, iios.infrastructure.
**Latency Constraints:** GlobalIntelligence <= 17ms p99. MarketIntelligence <= 19ms p99.
**Public Interface:** GlobalDataAI.fetch(), MarketIntelligenceAI.get_snapshot().

---

## 2.5 iios/knowledge/ — Knowledge and Ontology Layers

**Purpose:** The structured knowledge repository (Layer W3) and the entity
ontology (Layer W4) that defines valid entity types, relationships, and attributes.

**Owner:** Knowledge Team
**IIOS Layers:** 3 (Knowledge System), 4 (Ontology Engine)
**Waves:** W3, W4

`
iios/knowledge/
|-- __init__.py
|-- __manifest__.json
|-- README.md
|-- knowledge_base/
|   |-- __init__.py
|   |-- knowledge_store.py       (KnowledgeStore: read, write, query, version)
|   |-- knowledge_item.py        (KnowledgeItem with confidence, staleness)
|   |-- knowledge_query.py       (query by regime, topic, confidence range)
|   |-- knowledge_cache.py       (in-memory hot cache for frequent queries)
|   |-- contradiction_detector.py (detects contradictory knowledge items)
|   |-- staleness_tracker.py     (tracks knowledge age against MAX_KB_AGE)
|   |-- provenance_manager.py    (provenance records for all knowledge items)
|   |-- knowledge_versioner.py   (version history for each knowledge item)
|-- ontology/
|   |-- __init__.py
|   |-- ontology_loader.py       (loads ontology from YAML/SQLite source)
|   |-- ontology_validator.py    (validates entity references against ontology)
|   |-- entity_registry.py       (entity type registry)
|   |-- relationship_registry.py (relationship type registry)
|   |-- attribute_registry.py    (attribute type registry)
|   |-- constraint_engine.py     (cardinality and required attribute enforcement)
|-- tests/
|   |-- test_knowledge_store.py
|   |-- test_contradiction_detector.py
|   |-- test_ontology_validator.py
|   |-- test_provenance_manager.py
`

**Allowed Imports:** iios.core, iios.infrastructure.
**Restricted Imports:** Nothing from iios.intelligence (knowledge is not regime-aware at storage level).
**Certification Requirement:** Level 3 (CERTIFIED) before reasoning layer can depend on it.

---

## 2.6 iios/observation/ — Observation Engine (Layer 5)

**Purpose:** Receives raw market data from infrastructure, validates it against
the ontology, classifies it as structured observations, and stores observations
with full provenance.

**Owner:** Knowledge Team
**IIOS Layer:** 5 (Observation Engine)
**Wave:** W5

`
iios/observation/
|-- __init__.py
|-- __manifest__.json
|-- README.md
|-- observation_engine.py        (ObservationEngine: orchestrates all observers)
|-- price_observer.py            (price and volume observations)
|-- volume_observer.py           (volume profile observations)
|-- breadth_observer.py          (market breadth: advance/decline, new highs)
|-- options_observer.py          (options chain observations, PCR, OI)
|-- futures_observer.py          (futures basis, rollover, cost of carry)
|-- event_observer.py            (market event observations: news, corporate actions)
|-- observation_validator.py     (validates observations against ontology)
|-- observation_store.py         (persists observations to SQLite)
|-- observation_query.py         (query observations by time, type, symbol)
|-- tests/
|   |-- test_observation_engine.py
|   |-- test_observation_validator.py
|   |-- test_observation_store.py
`

**Allowed Imports:** iios.core, iios.infrastructure, iios.knowledge.
**Public Interface:** ObservationEngine.observe(symbol, data_point) -> Observation.

---

## 2.7 iios/relationship/ — Relationship Engine (Layer 6)

**Purpose:** Discovers, validates, and maintains the relationships between entities
in the knowledge base. Tracks correlations, causation hypotheses, and structural dependencies.

**Owner:** Knowledge Team
**IIOS Layer:** 6 (Relationship Engine)
**Wave:** W6

`
iios/relationship/
|-- __init__.py
|-- __manifest__.json
|-- README.md
|-- relationship_engine.py       (RelationshipEngine: orchestrates discovery)
|-- relationship_registry.py     (runtime registry of known relationships)
|-- correlation_tracker.py       (price correlations between instruments)
|-- sector_relationship.py       (sector membership, peer group relationships)
|-- strategy_relationship.py     (strategy-instrument relationships)
|-- regime_relationship.py       (regime-strategy fitness relationships)
|-- relationship_validator.py    (validates relationships against ontology)
|-- relationship_store.py        (persists relationships to SQLite)
|-- tests/
|   |-- test_relationship_engine.py
|   |-- test_correlation_tracker.py
`

**Allowed Imports:** iios.core, iios.infrastructure, iios.knowledge, iios.observation.

---

## 2.8 iios/events/ — Event Engine (Layer 7)

**Purpose:** Manages the IIOS event system at the application level. While
infrastructure.event_bus handles transport, events/ handles event semantics:
event schemas, event handlers, event routing rules, and event audit.

**Owner:** Platform Team
**IIOS Layer:** 7 (Event Engine)
**Wave:** W7

`
iios/events/
|-- __init__.py
|-- __manifest__.json
|-- README.md
|-- event_types/
|   |-- __init__.py
|   |-- system_events.py         (SYSTEM_READY, SHUTDOWN_INITIATED, KILL_SWITCH)
|   |-- market_events.py         (REGIME_CHANGE, MARKET_OPEN, MARKET_CLOSE)
|   |-- trading_events.py        (TRADE_APPROVED, TRADE_REJECTED, TRADE_EXECUTED)
|   |-- learning_events.py       (STRATEGY_DISABLED, STRATEGY_PROMOTED)
|   |-- data_events.py           (FEED_FAILED, FEED_RECOVERED, DATA_STALE)
|-- event_handlers/
|   |-- __init__.py
|   |-- kill_switch_handler.py   (handles KILL_SWITCH_TRIGGERED)
|   |-- regime_change_handler.py (handles REGIME_CHANGE)
|   |-- trade_event_handler.py   (handles TRADE_EXECUTED for learning)
|-- event_audit/
|   |-- __init__.py
|   |-- event_auditor.py         (append-only event audit log to SQLite)
|-- tests/
|   |-- test_event_types.py
|   |-- test_event_handlers.py
|   |-- test_event_audit.py
`

**Allowed Imports:** iios.core, iios.infrastructure.
**Critical Event:** KILL_SWITCH_TRIGGERED is handled with highest priority.

---

## 2.9 iios/reasoning/ — Reasoning Engine (Layer 8)

**Purpose:** Processes classified market observations, applies the k-NN regime
weighting model, and produces structured market insights ready for the
decision pipeline.

**Owner:** Intelligence Team
**IIOS Layer:** 8 (Reasoning Engine)
**Wave:** W8

`
iios/reasoning/
|-- __init__.py
|-- __manifest__.json
|-- README.md
|-- reasoning_engine.py          (ReasoningEngine: full reasoning pipeline)
|-- insight_producer.py          (produces structured insights from observations)
|-- regime_insight.py            (regime-specific insight generation)
|-- technical_reasoner.py        (technical analysis: trend, momentum, S/R)
|-- fundamental_reasoner.py      (fundamental context: earnings, valuation)
|-- options_reasoner.py          (options-based insights: PCR, gamma)
|-- breadth_reasoner.py          (market breadth insights)
|-- meta_learning/
|   |-- __init__.py
|   |-- meta_strategy_controller.py (MetaStrategyController)
|   |-- knn_strategy_weighter.py    (k-NN model for regime-to-strategy mapping)
|   |-- regime_strategy_map.py      (singleton RegimeStrategyMap)
|   |-- weight_normalizer.py        (ensures strategy weights sum to 1.0)
|-- tests/
|   |-- test_reasoning_engine.py
|   |-- test_meta_strategy_controller.py
|   |-- test_knn_weighter.py
`

**Allowed Imports:** iios.core, iios.infrastructure, iios.knowledge, iios.intelligence, iios.observation.
**Public Interface:** get_regime_strategy_map() factory function.

---

## 2.10 iios/strategy/ — Strategy Lab (Layer 5 + Wave 13)

**Purpose:** Strategy generation, evolution, backtesting, and management.
Contains both the base strategy framework (Wave 5) and the AI strategy
generator (Wave 13).

**Owner:** Strategy Team
**IIOS Layers:** 5 (Strategy Lab), 13 (AI Agents — strategy generation)
**Waves:** W5, W13

`
iios/strategy/
|-- __init__.py
|-- __manifest__.json
|-- README.md
|-- base/
|   |-- __init__.py
|   |-- base_strategy.py         (BaseStrategy abstract class — PROTECTED INTERFACE)
|   |-- strategy_registry.py     (registry of all active strategies)
|   |-- strategy_catalog.py      (catalog of all known strategies including disabled)
|-- evolved_strategies/          (PROTECTED DIRECTORY — earned through evolution)
|   |-- __init__.py
|   |-- README.md                (describes each evolved strategy)
|   |-- (strategy JSON files)
|-- generators/
|   |-- __init__.py
|   |-- strategy_generator_ai.py (StrategyGeneratorAI — bug-fixed)
|   |-- parameter_evolver.py     (parameter evolution using fitness)
|   |-- variant_generator.py     (generates variants from base strategies)
|   |-- fitness_evaluator.py     (evaluates strategy fitness: RR, winrate)
|-- backtesting/
|   |-- __init__.py
|   |-- backtesting_ai.py        (BacktestingAI — PROTECTED MODULE)
|   |-- backtest_runner.py       (orchestrates backtests)
|   |-- backtest_result.py       (BacktestResult data structure)
|   |-- walk_forward_engine.py   (WalkForwardTester)
|   |-- cross_market_validator.py (cross-market validation)
|-- tests/
|   |-- test_strategy_generator.py
|   |-- test_backtesting.py
|   |-- test_walk_forward.py
`

**Protected Modules:** evolved_strategies/ directory — not hand-authored.
**Protected Module:** acktesting_ai.py — calibrated; no modification without instruction.

---

## 2.11 iios/decision/ — Debate and Decision Layer (Layer 10)

**Purpose:** The five-agent debate system and decision engine. Receives scored
opportunities, convenes the debate, aggregates scores, and applies the 6.5
threshold to produce TRADE_APPROVED or TRADE_REJECTED decisions.

**Owner:** Decision Team
**IIOS Layer:** 10 (DebateAndDecision)
**Wave:** W9

`
iios/decision/
|-- __init__.py
|-- __manifest__.json
|-- README.md
|-- opportunity_scorer.py        (scores raw opportunities for debate input)
|-- debate/
|   |-- __init__.py
|   |-- base_debate_agent.py     (DebateAgent abstract base class)
|   |-- bull_agent.py            (BullAgent: bullish perspective)
|   |-- bear_agent.py            (BearAgent: bearish perspective)
|   |-- neutral_agent.py         (NeutralAgent: balanced perspective)
|   |-- risk_agent.py            (RiskAgent: risk-focused perspective)
|   |-- regime_agent.py          (RegimeAgent: regime-alignment perspective)
|   |-- debate_orchestrator.py   (DebateOrchestrator: coordinates the 5 agents)
|-- aggregation/
|   |-- __init__.py
|   |-- score_aggregator.py      (ScoreAggregator: weighted average)
|   |-- score_validator.py       (validates all scores are in [0.0, 10.0])
|   |-- aggregation_policy.py    (aggregation weights, future: regime-dependent)
|-- engine/
|   |-- __init__.py
|   |-- decision_engine.py       (DecisionEngine: threshold 6.5 from config.py)
|   |-- decision_record.py       (TradeDecision data structure)
|   |-- decision_history.py      (stores all decisions to SQLite)
|-- tests/
|   |-- test_debate_agents.py
|   |-- test_score_aggregator.py
|   |-- test_decision_engine.py
|   |-- test_threshold_boundaries.py  (6.499, 6.5, 6.501 boundary tests — MANDATORY)
`

**MANDATORY Test:** 	est_threshold_boundaries.py must exist and pass.
**Config Reference:** DECISION_THRESHOLD = 6.5 must come from config.py, never hardcoded.

---

## 2.12 iios/risk/ — Risk Management Stack (Layers 6-9)

**Purpose:** Complete risk management: capital allocation, position sizing,
portfolio risk assessment, stress testing, and the kill switch (RiskGuardian).

**Owner:** Risk Team
**IIOS Layers:** 6 (CapitalRiskEngine), 7 (RiskControl), 9 (RiskGuardian)
**Waves:** W6, W7, W11

`
iios/risk/
|-- __init__.py
|-- __manifest__.json
|-- README.md
|-- capital/
|   |-- __init__.py
|   |-- capital_risk_engine.py   (CapitalRiskEngine: strategy budget allocation)
|   |-- budget_calculator.py     (position size within strategy budget)
|   |-- budget_tracker.py        (real-time budget consumption tracking)
|-- portfolio/
|   |-- __init__.py
|   |-- risk_manager_ai.py       (RiskManagerAI: portfolio risk validation)
|   |-- portfolio_allocation.py  (PortfolioAllocation: exposure management)
|   |-- position_tracker.py      (real-time position state)
|   |-- exposure_calculator.py   (gross, net, sector exposure)
|   |-- concentration_checker.py (position and sector concentration limits)
|-- stress/
|   |-- __init__.json
|   |-- stress_test_filter.py    (StressTestFilter: fast Monte Carlo path)
|   |-- scenario_engine.py       (14-scenario stress engine)
|   |-- var_calculator.py        (Value at Risk computation)
|   |-- drawdown_estimator.py    (drawdown impact of proposed position)
|-- guardian/
|   |-- __init__.py
|   |-- risk_guardian.py         (RiskGuardian: kill switch — PROTECTED MODULE)
|   |-- kill_switch_monitor.py   (VIX monitoring: threshold 45.0)
|   |-- loss_monitor.py          (daily loss monitoring: threshold 2.0%)
|-- tests/
|   |-- test_capital_risk_engine.py
|   |-- test_risk_manager_ai.py
|   |-- test_stress_test_filter.py
|   |-- test_risk_guardian.py
|   |-- test_kill_switch_boundaries.py  (VIX 44.99, 45.0, 45.01 — MANDATORY)
`

**Protected Module:** isk_guardian.py — kill-switch logic is intentional.
**MANDATORY Test:** Kill switch boundary tests: VIX 44.99, 45.0, 45.01.

---

## 2.13 iios/execution/ — Execution Engine (Layer 11)

**Purpose:** Order management, broker integration, and paper/live trade execution.
Receives RISK_APPROVED trade decisions and converts them to orders.

**Owner:** Execution Team
**IIOS Layer:** 11 (ExecutionEngine)
**Wave:** W15

`
iios/execution/
|-- __init__.py
|-- __manifest__.json
|-- README.md
|-- order_manager.py             (OrderManager: PAPER_TRADING explicit check — bug-fixed)
|-- order_record.py              (OrderRecord data structure)
|-- paper_journal.py             (paper trade CSV journal: data/paper_trades.csv)
|-- broker/
|   |-- __init__.py
|   |-- base_broker.py           (BaseBroker abstract interface)
|   |-- dhan_broker.py           (ZerodhaBroker/DhanBroker — sim mode)
|   |-- broker_health.py         (broker connection health check)
|-- order_flow/
|   |-- __init__.py
|   |-- order_validator.py       (validates order before submission)
|   |-- order_router.py          (routes to paper journal or broker)
|   |-- order_sizer.py           (applies position size from CapitalRiskEngine)
|   |-- slippage_model.py        (paper trading slippage estimation)
|-- tests/
|   |-- test_order_manager.py
|   |-- test_paper_journal.py
|   |-- test_order_router.py
`

**PAPER_TRADING check:** OrderManager explicitly checks PAPER_TRADING flag.
**Journal location:** data/paper_trades.csv (persistent volume, not version-controlled).

---

*End of Part II first half*

## 2.14 iios/monitoring/ — Trade Monitoring (Layer 12)

**Purpose:** Monitors open trades, tracks P&L in real time, evaluates strategy
health, and feeds trade outcomes to the learning system.

**Owner:** Execution Team
**IIOS Layer:** 12 (TradeMonitoring)
**Wave:** W15

`
iios/monitoring/
|-- __init__.py
|-- __manifest__.json
|-- README.md
|-- trade_monitor.py             (TradeMonitor: monitors open positions)
|-- strategy_health_monitor.py   (StrategyHealthMonitor: per-strategy metrics)
|-- pnl_tracker.py               (real-time P&L computation)
|-- position_reconciler.py       (reconciles paper journal vs broker state)
|-- alert_manager.py             (threshold alerts: stop-loss, target)
|-- monitoring_dashboard_feed.py (feeds position data to dashboard)
|-- tests/
|   |-- test_trade_monitor.py
|   |-- test_pnl_tracker.py
|   |-- test_position_reconciler.py
`

**Allowed Imports:** iios.core, iios.infrastructure, iios.execution.
**Subscribes to:** TRADE_EXECUTED events via EventBus.

---

## 2.15 iios/learning/ — Learning System (Layers 13-14)

**Purpose:** The adaptive learning layer. Tracks strategy performance, updates
regime-to-strategy weightings, auto-disables underperforming strategies,
and maintains the performance tracker singleton.

**Owner:** Learning Team
**IIOS Layers:** 13 (LearningSystem), 14 (PerformanceAnalytics)
**Wave:** W14

`
iios/learning/
|-- __init__.py
|-- __manifest__.json
|-- README.md
|-- learning_engine.py           (LearningEngine: cycle-by-cycle learning)
|-- strategy_performance_tracker.py (singleton via get_performance_tracker())
|-- auto_disable_manager.py      (auto-disable strategies below threshold)
|-- regime_learner.py            (learns regime-strategy fitness from history)
|-- outcome_recorder.py          (records trade outcomes for learning)
|-- win_rate_calculator.py       (rolling win rate per strategy)
|-- sharpe_calculator.py         (rolling Sharpe ratio per strategy)
|-- performance_state.py         (persists learning state to SQLite)
|-- analytics/
|   |-- __init__.py
|   |-- drawdown_analyzer.py     (DrawdownAnalyzer: max drawdown computation)
|   |-- walk_forward_tester.py   (WalkForwardTester: OOS validation)
|   |-- performance_report.py    (generates performance summary reports)
|   |-- attribution_analyzer.py  (P&L attribution by strategy, regime)
|-- tests/
|   |-- test_learning_engine.py
|   |-- test_strategy_performance_tracker.py
|   |-- test_auto_disable.py
|   |-- test_win_rate_calculator.py
|   |-- test_drawdown_analyzer.py
`

**Public Interface:** get_performance_tracker() factory function.
**Auto-disable Threshold:** WIN_RATE_THRESHOLD from config.py.

---

## 2.16 iios/research/ — Research and Validation (Layers 15-16)

**Purpose:** Strategy research pipeline and the 6-stage validation engine.
Manages the promotion of strategies from research to production.

**Owner:** Research Team
**IIOS Layers:** 15 (ResearchLab), 16 (ValidationEngine)
**Waves:** W13, W16

`
iios/research/
|-- __init__.py
|-- __manifest__.json
|-- README.md
|-- research_lab/
|   |-- __init__.py
|   |-- strategy_research_agent.py  (StrategyResearchAgent)
|   |-- promotion_gate.py           (gate: WinRate>=50%, Sharpe>0.8, MaxDD<15%)
|   |-- research_pipeline.py        (orchestrates full research cycle)
|   |-- candidate_manager.py        (tracks strategy candidates)
|-- validation_engine/              (PROTECTED MODULE DIRECTORY)
|   |-- __init__.py
|   |-- validation_engine.py        (ValidationEngine: 6-stage pipeline — PROTECTED)
|   |-- stage_1_backtest.py         (Stage 1: Backtest validation)
|   |-- stage_2_walk_forward.py     (Stage 2: Walk-Forward Testing)
|   |-- stage_3_cross_market.py     (Stage 3: Cross-Market validation)
|   |-- stage_4_monte_carlo.py      (Stage 4: Monte Carlo validation)
|   |-- stage_5_sensitivity.py      (Stage 5: Sensitivity analysis)
|   |-- stage_6_regime.py           (Stage 6: Regime validation)
|   |-- validation_result.py        (ValidationResult with all 6 stage outcomes)
|-- tests/
|   |-- test_promotion_gate.py
|   |-- test_validation_engine.py
|   |-- test_promotion_boundaries.py  (win_rate 0.499, 0.50 boundary — MANDATORY)
`

**Protected Module:** alidation_engine/ — 6-stage pipeline and promotion criteria set.
**MANDATORY Test:** Promotion gate boundary tests.

---

## 2.17 iios/control/ — Control Tower (Layer 17)

**Purpose:** SQLite telemetry, Streamlit data bridge, and operational event
coordination. Layer 17 is the observability and control layer of IIOS.

**Owner:** Platform Team
**IIOS Layer:** 17 (ControlTower)
**Wave:** W17

`
iios/control/
|-- __init__.py
|-- __manifest__.json
|-- README.md
|-- telemetry_writer.py          (writes cycle telemetry to SQLite)
|-- telemetry_schema.py          (telemetry table schemas)
|-- event_bus_monitor.py         (monitors EventBus queue depth, delivery)
|-- dashboard_bridge.py          (feeds real-time data to Streamlit)
|-- cycle_recorder.py            (records each trading cycle outcome)
|-- operational_state.py         (tracks overall system operational state)
|-- tests/
|   |-- test_telemetry_writer.py
|   |-- test_dashboard_bridge.py
`

**Layer Position:** Layer 17 is the highest layer. It imports from all lower layers for monitoring.
**Note:** Imports from lower layers are monitoring-only (read-only calls). No trading decisions.

---

## 2.18 iios/agents/ — All AI Agent Implementations

**Purpose:** Central location for all AI agent classes. Agents are organized
by their functional role (debate, scanner, strategy, regime, meta).

**Owner:** Decision Team (debate agents), Intelligence Team (scanner/regime agents)
**IIOS Layer:** Multiple layers — agents are components of their host layer

`
iios/agents/
|-- __init__.py
|-- __manifest__.json
|-- README.md
|-- debate/
|   |-- __init__.py
|   |-- bull_agent.py            (BullAgent: bullish perspective scorer)
|   |-- bear_agent.py            (BearAgent: bearish perspective scorer)
|   |-- neutral_agent.py         (NeutralAgent: balanced scorer)
|   |-- risk_agent.py            (RiskAgent: risk-focused scorer)
|   |-- regime_agent.py          (RegimeAgent: regime-alignment scorer)
|-- scanner/
|   |-- __init__.py
|   |-- equity_scanner.py        (equity opportunity scanner)
|   |-- options_scanner.py       (options opportunity scanner)
|   |-- arbitrage_scanner.py     (arbitrage opportunity scanner)
|   |-- breakout_scanner.py      (breakout pattern scanner)
|   |-- momentum_scanner.py      (momentum scanner)
|-- strategy/
|   |-- __init__.py
|   |-- strategy_generator_ai.py (StrategyGeneratorAI — bug-fixed per log)
|   |-- strategy_evolver.py      (evolves strategy parameters)
|   |-- strategy_selector.py     (selects strategies by regime fitness)
|-- meta/
|   |-- __init__.py
|   |-- meta_strategy_controller.py (MetaStrategyController — regime weighting)
|   |-- regime_predictor.py      (predicts next regime from current signals)
|-- tests/
|   |-- test_debate_agents.py    (all 5 agents with synthetic input)
|   |-- test_scanner_agents.py
|   |-- test_strategy_generator.py
`

**Agent Registration:** All agents self-register with the AI Agent Registry via __manifest__.json.
**Debate Agent Invariant:** Exactly 5 debate agents must be registered before SYSTEM_CERTIFIED.

---

## 2.19 iios/simulation/ — Monte Carlo and Market Simulation

**Purpose:** Monte Carlo simulation engine and the 14-scenario market simulation
used by the StressTestFilter and ValidationEngine.

**Owner:** Risk Team
**IIOS Layer:** 8 (MarketSimulation component)
**Wave:** W8 (simulation), W11 (stress integration)

`
iios/simulation/
|-- __init__.py
|-- __manifest__.json
|-- README.md
|-- monte_carlo/
|   |-- __init__.py
|   |-- monte_carlo_engine.py    (Monte Carlo simulation: 14 scenarios)
|   |-- scenario_definitions.py  (14 scenario definitions: crash, rally, etc.)
|   |-- price_path_generator.py  (random price path generation)
|   |-- simulation_result.py     (SimulationResult: distribution of outcomes)
|-- market_simulation/
|   |-- __init__.py
|   |-- market_simulator.py      (full market simulation for backtesting)
|   |-- order_fill_simulator.py  (realistic order fill simulation)
|   |-- slippage_simulator.py    (slippage and market impact simulation)
|-- scenario_engine/
|   |-- __init__.py
|   |-- scenario_runner.py       (runs a strategy through all 14 scenarios)
|   |-- scenario_report.py       (per-scenario P&L, drawdown, Sharpe)
|-- tests/
|   |-- test_monte_carlo.py
|   |-- test_scenario_engine.py
`

---

## 2.20 iios/replay/ — Historical Replay Engine

**Purpose:** Replays historical market data through the full IIOS pipeline
for backtesting, validation, and debugging.

**Owner:** Research Team
**IIOS Layer:** N/A (research tool, not part of trading pipeline)
**Wave:** W14 (replay mode)

`
iios/replay/
|-- __init__.py
|-- __manifest__.json
|-- README.md
|-- replay_engine.py             (ReplayEngine: orchestrates historical replay)
|-- historical_data_loader.py    (loads historical data from data/historical/)
|-- replay_clock.py              (controls replay speed: 1x, 10x, 100x)
|-- replay_feed.py               (ReplayFeed: implements BaseFeed for replay)
|-- replay_database.py           (dedicated replay database: data/replay/)
|-- replay_reporter.py           (generates replay summary report)
|-- replay_comparer.py           (compares replay results to actual history)
|-- tests/
|   |-- test_replay_engine.py
|   |-- test_replay_feed.py
`

---

## 2.21 interfaces/ — External-Facing Components

**Purpose:** All components that face external operators or external systems.
Dashboard, Telegram bot, REST API, reporting. These are presentation layer
components; they read from the system but do not affect trading decisions.

**Owner:** Platform Team
**IIOS Layer:** Not part of 17-layer trading hierarchy (interface layer)
**Wave:** W16

`
interfaces/
|-- dashboard/
|   |-- __init__.py
|   |-- __manifest__.json
|   |-- app.py                   (Streamlit application entry point)
|   |-- pages/
|   |   |-- positions_page.py    (live positions view)
|   |   |-- pnl_page.py          (P&L dashboard)
|   |   |-- strategy_page.py     (strategy performance)
|   |   |-- health_page.py       (system health)
|   |   |-- cycle_page.py        (cycle telemetry)
|   |-- components/
|   |   |-- charts.py            (reusable chart components)
|   |   |-- tables.py            (data table components)
|   |   |-- metrics.py           (metric cards)
|   |-- data/
|       |-- dashboard_queries.py (SQLite queries for dashboard data)
|       |-- refresh_scheduler.py (data refresh scheduling)
|-- telegram/
|   |-- __init__.py
|   |-- __manifest__.json
|   |-- telegram_bot.py          (TelegramBot singleton — get_telegram_bot())
|   |-- commands/
|   |   |-- status_commands.py   (/status, /health, /positions)
|   |   |-- pnl_commands.py      (/pnl, /perf)
|   |   |-- strategy_commands.py (/strategies, /learn)
|   |   |-- control_commands.py  (/shutdown, /resume, /safe)
|   |   |-- diagnostic_commands.py (/diag, /regime)
|   |-- bot_health.py            (Telegram bot connectivity health check)
|   |-- notification_sender.py   (sends structured notifications)
|   |-- rate_limiter.py          (prevents Telegram API rate limiting)
|-- reporting/
|   |-- __init__.py
|   |-- eod_report.py            (end-of-day report generator)
|   |-- performance_report.py    (strategy performance report)
|   |-- cycle_report.py          (cycle-level report)
`

**Public Interface:** get_telegram_bot() factory function.
**Telegram Commands:** Exactly 13 commands registered. Count validated at startup.

---

## 2.22 infrastructure/ — Non-Python Infrastructure

**Purpose:** Deployment, database schema, logging configuration, and security
policy artifacts that are not Python packages.

**Owner:** Platform Team

`
infrastructure/
|-- database/
|   |-- schema/
|   |   |-- v001_initial.sql          (initial schema: all tables + indexes)
|   |   |-- v002_strategy_perf.sql    (strategy performance table)
|   |   |-- v003_learning_state.sql   (learning state table)
|   |   |-- (one file per migration)
|   |-- seed/
|   |   |-- initial_ontology.sql      (seed ontology data)
|   |   |-- initial_strategies.sql    (seed strategy catalog)
|   |-- indexes/
|       |-- performance_indexes.sql   (additional performance indexes)
|-- logging/
|   |-- logging_config.yaml           (log level, format, rotation policy)
|   |-- log_retention_policy.txt      (30-day retention specification)
|-- security/
|   |-- environment_template.txt      (list of required environment variables)
|   |-- cve_policy.md                 (CVE response SLAs)
|   |-- secret_detection_config.yaml  (detect-secrets configuration)
|-- deployment/
|   |-- Dockerfile                    (re-linked to root)
|   |-- docker-compose.yml            (re-linked to root)
|   |-- entrypoint.sh                 (Docker entrypoint script)
|   |-- health_check.sh               (Docker health check script)
|   |-- nginx.conf                    (if reverse proxy used)
`

---

## 2.23 tests/ — Test Suite Root

**Purpose:** The complete test suite organized to mirror the iios/ package structure.

**Owner:** All teams (each team owns tests for their packages)

`
tests/
|-- unit/
|   |-- core/
|   |-- infrastructure/
|   |-- intelligence/
|   |-- knowledge/
|   |-- observation/
|   |-- relationship/
|   |-- events/
|   |-- reasoning/
|   |-- strategy/
|   |-- decision/
|   |-- risk/
|   |-- execution/
|   |-- monitoring/
|   |-- learning/
|   |-- research/
|   |-- control/
|   |-- agents/
|   |-- simulation/
|-- integration/
|   |-- pipeline/
|   |   |-- test_full_cycle.py        (observation → decision → execution)
|   |   |-- test_kill_switch_e2e.py   (kill switch end-to-end — MANDATORY)
|   |   |-- test_feed_fallback.py     (Dhan → yfinance fallback — MANDATORY)
|   |   |-- test_restart_recovery.py  (container restart state recovery)
|   |-- knowledge/
|   |   |-- test_knowledge_ontology.py
|   |-- regime/
|       |-- test_regime_transitions.py
|-- performance/
|   |-- test_global_intelligence_latency.py   (target: <= 17ms p99)
|   |-- test_market_intelligence_latency.py   (target: <= 19ms p99)
|   |-- test_full_cycle_latency.py            (target: <= 172ms baseline)
|   |-- test_database_write_latency.py
|-- security/
|   |-- test_no_secrets_in_logs.py
|   |-- test_sql_injection_prevention.py
|   |-- test_input_validation.py
|-- replay_tests/
|   |-- test_replay_engine.py
|   |-- fixtures/
|       |-- (historical market data fixtures)
|-- fixtures/
|   |-- market_data_fixtures.py
|   |-- strategy_fixtures.py
|   |-- knowledge_fixtures.py
|   |-- regime_fixtures.py
|-- conftest.py                       (pytest configuration, shared fixtures)
|-- pytest.ini                        (pytest settings)
`

**MANDATORY Integration Tests:**
- 	est_kill_switch_e2e.py — end-to-end kill switch test.
- 	est_feed_fallback.py — Dhan to yfinance fallback test.
- 	est_full_cycle.py — complete pipeline test.

---

## 2.24 docs/ — Engineering Documentation

**Purpose:** The complete engineering documentation corpus, version-controlled
alongside the code.

`
docs/
|-- architecture/
|   |-- ARCHITECTURE.md               (system architecture specification — root symlink)
|   |-- layer_diagram.md              (17-layer ASCII diagram)
|   |-- dependency_diagram.md         (layer dependency diagram)
|-- decisions/
|   |-- EDR-001-initial-architecture.md
|   |-- EDR-002-dhan-fallback.md
|   |-- (one file per Engineering Decision Record)
|-- waves/
|   |-- wave-01/
|   |   |-- specification.md          (pre-implementation spec)
|   |   |-- implementation_log.md     (during-implementation log)
|   |   |-- completion_record.md      (post-implementation WCR)
|   |-- wave-02/ ... wave-20/
|-- certification/
|   |-- e1_cicd_pass_v1.0.0.pdf
|   |-- e2_coverage_report_v1.0.0/
|   |-- (10 evidence items per production authorization)
|-- runbooks/
|   |-- RB-001-deployment.md
|   |-- RB-002-database-restore.md
|   |-- RB-003-kill-switch-manual-reset.md
|   |-- RB-004-feed-failover.md
|   |-- RB-005-restart-procedure.md
|-- api/
    |-- (auto-generated pydoc/sphinx output)
`

---

*End of Part II*

---

# PART III — PACKAGE ARCHITECTURE

## 3.1 Package Architecture Standards

Every IIOS Python package follows the same structural contract. This section
defines that contract and then applies it to each major package cluster.

**Universal Package Contract:**
Every package directory contains:
- __init__.py: exports exactly the public interface (nothing more).
- __manifest__.json: machine-readable metadata.
- README.md: human-readable package description.
- 	ests/: package-level test directory.

**__manifest__.json Schema:**
`json
{
  "name": "iios.core",
  "version": "1.0.0",
  "description": "Core Foundation — types, utils, exceptions, interfaces",
  "iios_layer": 1,
  "classification": "CRITICAL",
  "wave": "W1",
  "owner": "Platform Team",
  "dependencies": [],
  "public_interfaces": ["BaseFeed", "BaseAgent", "BaseStrategy"],
  "protected": false,
  "certification_level": 4
}
`

---

## 3.2 iios.core Package Architecture

**Purpose:** Irreducible shared foundation for all IIOS packages.

**Responsibilities:**
- Define all shared data types (TickerQuote, PriceBar, AgentScore, etc.).
- Define all base abstract interfaces (BaseFeed, BaseAgent, BaseStrategy).
- Provide precise financial arithmetic utilities (Decimal-based, no float).
- Define all exception classes in a single hierarchy.
- Provide date/time utilities that are market-calendar-aware.
- Define the GLOBAL_SYMBOL_MAP for symbol normalization.

**Public Interfaces (exported from __init__.py):**
- Types: TickerQuote, PriceBar, AgentScore, CompositeScore, TradeDecision.
- Types: RegimeEnum, KnowledgeItem, OntologyEntity.
- Interfaces: BaseFeed, BaseAgent, BaseStrategy, BaseScanner.
- Utils: DecimalUtils, DatetimeUtils, SymbolUtils, ValidationUtils.
- Exceptions: BaseIIOSException and all subclasses.

**Internal Components (NOT exported):**
- hash_utils.py — used by infrastructure, not exported to all packages.
- uuid_utils.py — internal to bootstrap, not a general utility.

**Dependencies:** None (Python standard library only).

**Allowed Imports:**
- Python standard library: decimal, datetime, enum, bc, 	yping, uuid, hashlib.
- No third-party libraries.
- No other IIOS packages.

**Restricted Imports:**
- Anything from iios.infrastructure or higher. Absolute restriction.

**Ownership:** Platform Team. Any modification requires Platform Team review.

**Lifecycle:** W1 (created), permanent (never retired).

**Versioning:** Major version bump only on breaking interface change.
Major interface changes require Architecture Council vote.

**Certification Requirement:** Level 4 (PRODUCTION-READY).
All other packages depend on iios.core. Any certification regression in iios.core
blocks certification of all dependent packages.

---

## 3.3 iios.infrastructure Package Architecture

**Purpose:** Infrastructure services for data, persistence, events, monitoring.

**Responsibilities:**
- Manage data feed connections (Dhan primary, yfinance fallback).
- Manage SQLite database connections, schema, and migrations.
- Provide the EventBus for system-wide event publish/subscribe.
- Provide the SystemMonitor for layer latency tracking.
- Manage structured logging and log rotation.
- Load configuration and environment variables into immutable snapshots.

**Public Interfaces:**
- DataFeedManager (via get_feed_manager() factory function).
- EventBus (via get_event_bus() factory function).
- SystemMonitor.time_layer() — PROTECTED INTERFACE.
- ConfigurationSnapshot (read-only access).
- DatabaseConnectionManager.

**Internal Components:**
- query_builder.py — not exported; internal to database package.
- log_context.py — not exported; used only by logging system.
- eed_health_monitor.py — not exported; used only by DataFeedManager.

**Dependencies:** iios.core only.

**Allowed Imports:**
- iios.core.
- Python standard library.
- Third-party: yfinance, sqlite3, equests, dhanhq (Dhan SDK).

**Restricted Imports:**
- Nothing from iios.intelligence or higher.
- iios.knowledge, iios.reasoning, iios.decision: ALL restricted.

**Protected Modules:**
- dhan_feed.py: no modification without explicit instruction.
  Bugs here affect live trading orders.

**Ownership:** Platform Team.

**Lifecycle:** W2 (created), permanent.

**Certification Requirement:** Level 4 (PRODUCTION-READY).

---

## 3.4 iios.intelligence Package Architecture

**Purpose:** Global market context and NSE market regime classification.

**Responsibilities:**
- Fetch overnight global context (S&P, Nikkei, bonds, FX, VIX).
- Maintain the GlobalDataAI 5-minute cache with background pre-warm.
- Classify current NIFTY/BANKNIFTY market regime (6 regime types).
- Run MarketMonitor for 30-second continuous market scan.
- Provide sector rotation and liquidity analysis.

**Public Interfaces:**
- GlobalDataAI.fetch(force: bool = False) -> GlobalSnapshot — PROTECTED INTERFACE.
- MarketIntelligenceAI.get_snapshot() -> MarketSnapshot.
- RegimeClassifier.classify() -> RegimeEnum.
- MarketMonitor.start() / MarketMonitor.stop().

**Internal Components:**
- global_sources.py — data source configuration. Not exported.
- global_cache.py — cache internals. Not exported.

**Dependencies:** iios.core, iios.infrastructure.

**Allowed Imports:**
- iios.core, iios.infrastructure.
- Third-party: yfinance (indirect via DataFeedManager).

**Restricted Imports:**
- iios.knowledge, iios.reasoning, iios.decision: ALL restricted.
  Intelligence layers do not depend on the knowledge or decision layers.

**Latency Constraints:**
- GlobalDataAI.fetch() p99 <= 17ms (with cache). Cold fetch <= 12,000ms.
- MarketIntelligenceAI.get_snapshot() p99 <= 19ms.

**Ownership:** Intelligence Team.

**Lifecycle:** W2 (stub), W8 (full implementation).

**Certification Requirement:** Level 3 (CERTIFIED) at W8 completion.

---

## 3.5 iios.knowledge Package Architecture

**Purpose:** Structured knowledge repository and entity ontology.

**Responsibilities:**
- Store, version, and query knowledge items with confidence scores.
- Detect contradictions between knowledge items.
- Track provenance (origin and basis) for all knowledge items.
- Define the valid universe of entity types, relationships, and attributes.
- Validate entity references against the ontology at write time.

**Public Interfaces:**
- KnowledgeStore.write(item: KnowledgeItem) -> KnowledgeId.
- KnowledgeStore.query(regime, topic, confidence_min) -> List[KnowledgeItem].
- OntologyValidator.validate(entity) -> ValidationResult.
- ContradictionDetector.scan() -> List[Contradiction].

**Internal Components:**
- knowledge_versioner.py — versioning is internal implementation detail.
- staleness_tracker.py — not exported; used only by KnowledgeStore.

**Dependencies:** iios.core, iios.infrastructure.database.

**Allowed Imports:**
- iios.core, iios.infrastructure.
- No iios.intelligence imports (knowledge layer is below intelligence).

**Note on Layer Position:**
Knowledge (W3-W4) is below Intelligence (Layer 2). This is correct: knowledge
is a data store, not an intelligent agent. Intelligence layers consume knowledge.
The import direction is: intelligence imports from knowledge; never the reverse.

**Ownership:** Knowledge Team.

**Lifecycle:** W3 (knowledge), W4 (ontology), permanent.

**Certification Requirement:** Level 3 (CERTIFIED).

---

## 3.6 iios.strategy Package Architecture

**Purpose:** Strategy definition, generation, evolution, and backtesting.

**Responsibilities:**
- Define the BaseStrategy interface all strategies implement.
- Maintain the registry of active and disabled strategies.
- Generate new strategy variants through the AI generator.
- Evolve strategy parameters through fitness-based evolution.
- Backtest strategies on historical data (PROTECTED: backtesting_ai.py).
- Store evolved strategies in protected evolved_strategies/ directory.

**Public Interfaces:**
- BaseStrategy (from iios.core.interfaces).
- StrategyRegistry.get_active() -> List[BaseStrategy].
- StrategyGeneratorAI.generate_variants() -> List[StrategyVariant].
- BacktestingAI.run(strategy, data) -> BacktestResult — PROTECTED INTERFACE.

**Protected Modules:**
- acktesting/backtesting_ai.py — calibrated WFT/OOS quality gates.
- evolved_strategies/ directory — earned through evolution; not hand-authored.

**Internal Components:**
- ariant_generator.py — internal to generation pipeline.
- itness_evaluator.py — internal to evolution pipeline.

**Allowed Imports:**
- iios.core, iios.infrastructure, iios.knowledge (for strategy context).
- No iios.intelligence direct imports (receives regime from reasoning layer).

**Ownership:** Strategy Team.
**Protected Module Ownership:** Architecture Council (modification requires explicit instruction).

**Lifecycle:** W5 (base), W13 (generator), permanent.

**Certification Requirement:** Level 3 (CERTIFIED). Evolved strategies: each promoted strategy carries its own certification record.

---

## 3.7 iios.decision Package Architecture

**Purpose:** The five-agent debate system and decision engine.

**Responsibilities:**
- Score opportunities through five independent debate agents.
- Aggregate five agent scores into a weighted composite.
- Apply the 6.5 threshold to produce TRADE_APPROVED or TRADE_REJECTED.
- Record every trade decision in SQLite for audit.
- Ensure debate order is reproducible (same inputs → same output).

**Public Interfaces:**
- DecisionEngine.decide(opportunity: ScoredOpportunity) -> TradeDecision.
- DebateOrchestrator.run_debate(opportunity) -> List[AgentScore].
- ScoreAggregator.aggregate(scores: List[AgentScore]) -> CompositeScore.

**Critical Invariants:**
- Exactly five debate agents registered at all times.
- DECISION_THRESHOLD = 6.5 from config.py. Never hardcoded.
- Agent scoring is independent (agents do not share state).
- Debate is deterministic (same opportunity → same scores if no randomness).

**Allowed Imports:**
- iios.core, iios.infrastructure.
- iios.intelligence (for market context in agent scoring).
- iios.knowledge (for knowledge base queries in agent scoring).
- iios.reasoning (for regime weights).
- iios.strategy (for strategy fitness context).

**Restricted Imports:**
- iios.risk, iios.execution: decision layer does not depend on risk or execution.
  The decision is made first; risk filters are applied after.

**Ownership:** Decision Team.

**Lifecycle:** W9, permanent.

**Certification Requirement:** Level 4 (PRODUCTION-READY). Decision layer is on the critical trading path.

---

## 3.8 iios.risk Package Architecture

**Purpose:** Complete risk management: capital allocation, portfolio risk,
stress testing, and the kill switch.

**Responsibilities:**
- Compute position size within strategy budget (CapitalRiskEngine).
- Validate portfolio concentration and exposure (RiskManagerAI).
- Run fast Monte Carlo stress test on proposed position (StressTestFilter).
- Monitor VIX and daily loss for kill switch conditions (RiskGuardian).
- Publish KILL_SWITCH_TRIGGERED event when thresholds are exceeded.

**Public Interfaces:**
- CapitalRiskEngine.compute_position_size(strategy, signal) -> PositionSize.
- RiskManagerAI.validate(decision, portfolio) -> RiskDecision.
- StressTestFilter.evaluate(position, portfolio) -> StressResult.
- RiskGuardian — PROTECTED. Reacts to market data; publishes kill switch events.

**Critical Invariants:**
- KILL_SWITCH_VIX = 45.0 from config.py. Never hardcoded.
- KILL_SWITCH_DAILY_LOSS_PCT = 0.02 from config.py. Never hardcoded.
- RiskGuardian cannot be disabled without code change (no configuration bypass).
- Kill switch event is published to EventBus; all subscribers halt new operations.

**Protected Modules:**
- guardian/risk_guardian.py — kill-switch logic is intentional.
  Any modification requires explicit Architecture Council instruction.

**Allowed Imports:**
- iios.core, iios.infrastructure, iios.decision (receives TradeDecision).
- iios.simulation (for Monte Carlo stress scenarios).

**Restricted Imports:**
- iios.execution: risk layer does not depend on execution layer.

**Ownership:** Risk Team.
**RiskGuardian Ownership:** Architecture Council.

**Lifecycle:** W6 (capital), W7 (portfolio risk), W11 (stress + guardian integration).

**Certification Requirement:** Level 4 (PRODUCTION-READY). Risk layer failures block production.

---

## 3.9 iios.learning Package Architecture

**Purpose:** Adaptive performance tracking, strategy evaluation, and regime learning.

**Responsibilities:**
- Track win rate and Sharpe ratio per strategy on a rolling basis.
- Auto-disable strategies below performance thresholds.
- Learn regime-to-strategy fitness from historical outcomes.
- Persist learning state to SQLite for cross-restart continuity.
- Provide DrawdownAnalyzer and WalkForwardTester for analytics.

**Public Interfaces:**
- get_performance_tracker() — singleton factory function.
- LearningEngine.update(trade_outcome: TradeOutcome) -> None.
- StrategyPerformanceTracker.get_metrics(strategy_name) -> PerformanceMetrics.
- DrawdownAnalyzer.compute(returns: List) -> DrawdownMetrics.
- WalkForwardTester.run(strategy, data) -> WFTResult.

**Critical Invariants:**
- Performance tracker singleton: always via get_performance_tracker().
- Auto-disable threshold from config.py (WIN_RATE_THRESHOLD, SHARPE_THRESHOLD).
- Auto-disabled strategies are NOT manually re-enabled without root cause analysis.

**Allowed Imports:**
- iios.core, iios.infrastructure, iios.strategy, iios.monitoring.

**Restricted Imports:**
- iios.decision, iios.risk, iios.execution: learning layer does not decide.

**Ownership:** Learning Team.

**Lifecycle:** W14, permanent.

**Certification Requirement:** Level 3 (CERTIFIED).

---

## 3.10 iios.research Package Architecture

**Purpose:** Strategy research pipeline and the 6-stage validation engine.

**Responsibilities:**
- Run the full research pipeline: generate → backtest → validate → promote.
- Enforce the three-criteria promotion gate simultaneously.
- Execute the 6-stage validation pipeline for strategy candidates.
- Manage strategy candidates through the research funnel.

**Public Interfaces:**
- PromotionGate.evaluate(strategy: StrategyCandidate) -> PromotionDecision.
- ValidationEngine.run_pipeline(strategy) -> ValidationResult — PROTECTED INTERFACE.
- ResearchPipeline.submit(strategy) -> CandidateId.

**Critical Invariants:**
- PROMOTION_WIN_RATE, PROMOTION_SHARPE, PROMOTION_MAX_DD from config.py.
- All three promotion criteria must be met simultaneously. Not two of three.
- ValidationEngine 6-stage pipeline cannot be shortened without EDR.

**Protected Modules:**
- alidation_engine/validation_engine.py — 6-stage pipeline, promotion criteria set.

**Ownership:** Research Team.
**ValidationEngine Ownership:** Architecture Council.

**Lifecycle:** W13 (research lab), W16 (validation engine).

**Certification Requirement:** Level 3 (CERTIFIED).

---

*End of Part III*

# PART IV — MODULE ORGANIZATION

## 4.1 Module Boundary Rules

A module is a single Python .py file within a package. Module boundaries define
which concepts belong together in a single file and which must be separated.
The module boundary rules enforce cohesion at the file level.

**Module Boundary Rules:**

Rule MB-1 — Single Responsibility
Each module has exactly one primary responsibility. If a module exports two
classes that change for different reasons, they belong in different modules.

Rule MB-2 — File Size Limit
No module exceeds 500 lines. A module approaching 500 lines is reviewed for
decomposition. Modules exceeding 500 lines without an EDR are specification violations.

Rule MB-3 — One Class Per Module (for substantial classes)
Classes with more than 100 lines of implementation live in their own module.
Small data classes and simple utility functions may coexist in a single module.

Rule MB-4 — Name Mirrors Content
The module filename mirrors its primary export.
decision_engine.py exports DecisionEngine.
isk_guardian.py exports RiskGuardian.
ase_feed.py exports BaseFeed.
A module named utilities.py that exports unrelated utilities is a cohesion violation.

Rule MB-5 — No Circular Module References
Modules within a package may not create circular import chains.
Module A imports Module B; Module B may not import Module A.
Circular references within a package indicate a cohesion problem.

Rule MB-6 — Tests Mirror Source
Every source module has a corresponding test module.
decision_engine.py → 	ests/test_decision_engine.py.
This 1:1 correspondence makes test coverage gaps immediately visible.

---

## 4.2 Internal Modules

Internal modules provide implementation details that are not part of the
package's public interface. They are imported only by other modules within
the same package.

**Internal Module Conventions:**
- Internal modules are NOT exported in __init__.py.
- Internal module names describe their specific implementation role.
- Internal modules may import from any other module in the same package.
- Internal modules are fully tested (internal does not mean untested).

**Examples of Internal Modules:**
- cache_policy.py in iios.infrastructure.cache — cache eviction logic, not exported.
- weight_normalizer.py in iios.reasoning.meta_learning — normalization implementation.
- log_context.py in iios.infrastructure.logging_system — logging context management.

**Internal Module Anti-Patterns:**
- An internal module that is imported by modules in another package is not internal.
  It should be promoted to the public interface.
- An internal module that is larger than 300 lines is reviewed for decomposition.

---

## 4.3 Shared Modules

Shared modules provide functionality used by multiple packages. In IIOS,
shared modules live in iios.core — which is the only package that all
other packages depend on.

**Shared Module Governance:**
- A candidate shared module must be needed by at least three distinct packages.
- Shared modules go through the same Architecture Council review as any core change.
- A shared module added speculatively (before three consumers exist) is a premature
  abstraction and is rejected.
- Shared modules carry the highest certification requirement (Level 4).

**Existing Shared Modules:**
- iios.core.types.trading_types: needed by intelligence, decision, execution, learning.
- iios.core.utils.decimal_utils: needed by all packages involving financial values.
- iios.core.utils.symbol_utils: needed by intelligence, observation, execution.
- iios.core.interfaces.base_feed: needed by infrastructure, intelligence, replay.

---

## 4.4 Private Modules

Private modules (prefixed with underscore: _module.py) contain implementation
details that must not be accessed outside their immediate context.

**Private Module Rules:**
- A private module is accessible only within the same file or the same package init.
- Private modules are used for helper functions that have no semantic meaning outside
  their immediate context (e.g., _parse_response_payload() in dhan_feed.py).
- Private modules are a stronger restriction than internal modules.
- Tests for private modules are in the same test file as the module that uses them.

---

## 4.5 Public Modules

Public modules form the public interface of a package. They are exported
in __init__.py and may be imported by dependent packages.

**Public Module Requirements:**
- Every public module has a module docstring describing: purpose, wave, layer, key constraints.
- Every public class in a public module has a class docstring with single-sentence purpose.
- Every public method has a docstring with parameters and return type.
- Public module interfaces do not change without an EDR.
- Public modules have 95%+ line coverage.

---

## 4.6 Extension Modules

Extension modules extend existing package functionality without modifying
existing packages. They follow the open/closed principle.

**Extension Module Pattern:**
- An extension module lives in the same package as what it extends.
- The extension module imports from the base module and adds capability.
- The base module is not modified.

**Example:** global_cache.py in iios.intelligence.global_intelligence
extends global_data_ai.py by adding caching behavior without modifying
GlobalDataAI directly. The cache is injected as a decorator/wrapper.

---

## 4.7 Plugin Modules

Plugin modules live in iios/plugins/ and provide optional capability
that does not affect the core trading pipeline.

**Plugin Module Rules:**
- Plugin modules must implement a declared plugin interface from iios.core.interfaces.
- Plugin failures must not affect core system operation.
- Plugin modules are loaded by the PluginRegistry, not imported directly.
- Plugin modules declare their capability type in __manifest__.json.
- Plugin modules are classified as OPTIONAL.

**Plugin Types:**
- DATA_PLUGIN: implements BaseFeed, provides an additional data source.
- STRATEGY_PLUGIN: implements BaseStrategy, adds a new strategy type.
- REPORTING_PLUGIN: adds a new reporting output channel.
- NOTIFICATION_PLUGIN: adds a new notification method.
- ANALYTICS_PLUGIN: adds a new analytics computation.

---

## 4.8 Experimental Modules

Experimental modules live in experimental/ and are explicitly not certified
for production use.

**Experimental Module Rules:**
- All experimental modules have a header comment: # EXPERIMENTAL — NOT PRODUCTION CERTIFIED.
- Experimental modules are never imported by production packages.
- CI/CD verifies that no production package imports from experimental/.
- An experimental module that becomes production-ready graduates through Wave promotion,
  not by removing the experimental/ classification.

---

## 4.9 Deprecated Modules

Deprecated modules have been replaced by newer implementations but are
retained for reference and historical auditing.

**Deprecated Module Rules:**
- Deprecated modules are moved to _deprecated/ with their original path preserved.
  Example: data_feeds/old_dhan_feed.py moves to _deprecated/data_feeds/old_dhan_feed.py.
- Deprecated modules have a header comment: # DEPRECATED — replaced by {new_module}.
- Deprecated modules are NOT deleted. They are retained as audit record.
- A deprecated module that was present during a production incident is retained
  with additional comments about the incident.
- Deprecated modules are excluded from coverage requirements.

---

## 4.10 Future Modules

Future modules are planned but not yet implemented. They are represented by
placeholder files in the experimental/ directory with a comment: # FUTURE — Wave N.

**Future Module Rules:**
- Future modules contain only a module docstring and the # FUTURE comment.
- No implementation. No tests. No exports.
- Future module placeholder files do not affect test coverage metrics.
- A future module that begins implementation becomes a wave deliverable
  and leaves the experimental/ directory.

---

*End of Part IV*

---

# PART V — DEPENDENCY FRAMEWORK

## 5.1 Dependency Hierarchy

The IIOS dependency hierarchy is a strict total order. Higher-numbered layers
may depend on lower-numbered layers. The reverse is forbidden.

`
DEPENDENCY HIERARCHY (strict partial order)

Layer 17 (ControlTower)         imports from: 1-16
Layer 16 (ValidationEngine)     imports from: 1-15
Layer 15 (ResearchLab)          imports from: 1-14
Layer 14 (PerformanceAnalytics) imports from: 1-13
Layer 13 (LearningSystem)       imports from: 1-12
Layer 12 (TradeMonitoring)      imports from: 1-11
Layer 11 (ExecutionEngine)      imports from: 1-10
Layer 10 (DebateAndDecision)    imports from: 1-9
Layer 9  (RiskGuardian)         imports from: 1-8
Layer 8  (ReasoningEngine)      imports from: 1-7
Layer 7  (EventEngine)          imports from: 1-6
Layer 6  (RelationshipEngine)   imports from: 1-5
Layer 5  (ObservationEngine)    imports from: 1-4
Layer 4  (OntologyEngine)       imports from: 1-3
Layer 3  (KnowledgeSystem)      imports from: 1-2
Layer 2  (MarketIntelligence)   imports from: 1
Layer 1  (GlobalIntelligence)   imports from: 0 (core and infrastructure)
Layer 0  (Core + Infra)         imports from: Python stdlib only
`

**Dependency Hierarchy Enforcement:**
The import graph analysis tool (	ools/import_graph_analyzer.py) enforces
this hierarchy by verifying that no package contains an import that crosses
a layer boundary upward. It runs on every CI/CD commit.

---

## 5.2 Import Rules

**Import Rule IR-1 — Absolute Imports Only**
All IIOS imports use absolute paths: rom iios.core.types import TickerQuote.
Relative imports (rom .types import TickerQuote) are permitted only within
a package for intra-package imports.

**Import Rule IR-2 — Import from Public Interface Only**
Packages import only from another package's public interface (what is exported
in __init__.py). Importing directly from internal modules of another package
is forbidden.
GOOD: rom iios.infrastructure import get_feed_manager
BAD:  rom iios.infrastructure.data_feeds.feed_health_monitor import FeedHealthMonitor

**Import Rule IR-3 — No Star Imports**
rom module import * is forbidden everywhere except in __init__.py files
that explicitly re-export symbols for public interface purposes.

**Import Rule IR-4 — No Runtime Imports**
Imports inside functions or methods (runtime imports) are forbidden except
for lazy-loading patterns documented in an EDR. Lazy loading is allowed only
for plugins and optional dependencies.

**Import Rule IR-5 — Singleton Access Through Factory Functions**
get_performance_tracker(), get_regime_strategy_map(), get_telegram_bot(),
and get_feed_manager() are the only way to access their respective singletons.
Direct class instantiation is a specification violation.

**Import Rule IR-6 — Config Values From config.py**
All configuration values that affect trading behavior are imported from config.py.
No module contains a duplicate copy of a configuration value.
rom config import DECISION_THRESHOLD — correct.
DECISION_THRESHOLD = 6.5 — forbidden.

**Import Rule IR-7 — Third-Party Imports Are Declared**
All third-party packages used in IIOS are declared in equirements.txt with
exact version pins. An import that is not in equirements.txt is not allowed.

---

## 5.3 Circular Dependency Prevention

**Circular Dependency Detection:**
The import graph analysis tool (	ools/import_graph_analyzer.py) runs a
topological sort on the complete IIOS import graph. If the sort fails
(graph has a cycle), the tool reports the cycle and the CI/CD gate fails.

**Circular Dependency Causes:**
The most common causes of circular dependencies in IIOS:
1. Two packages that need each other's types — solution: move shared types to iios.core.types.
2. A lower-layer package that needs a higher-layer service — solution: invert
   the dependency using EventBus events (publish event, subscribe to it).
3. Two modules in the same package that depend on each other — solution:
   extract shared logic to a third module that both depend on.

**Circular Dependency Resolution Process:**
1. Tool reports the cycle: A → B → C → A.
2. Engineer identifies which dependency in the cycle is the design error.
3. Engineer breaks the cycle using one of the three solutions above.
4. EDR written if the fix changes a public interface.
5. Import graph re-analysis confirms cycle is resolved.

---

## 5.4 Layer Boundaries

Layer boundaries define the physical isolation between IIOS architectural layers.
Layer boundaries are enforced by package structure and the import graph tool.

**Layer Boundary Enforcement Matrix:**

`
FROM LAYER  MAY IMPORT  ENFORCEMENT
0           Nothing     HARD
1           0           HARD
2           0-1         HARD
3           0-2         HARD
4           0-3         HARD
5           0-4         HARD
6           0-5         HARD
7           0-6         HARD
8           0-7         HARD
9           0-8         HARD
10          0-9         HARD
11          0-10        HARD
12          0-11        HARD
13          0-12        HARD
14          0-13        HARD
15          0-14        HARD
16          0-15        HARD
17          0-16        HARD (read-only monitoring)
`

**Layer Boundary Violation Consequences:**
A single layer boundary violation detected by the import graph tool:
1. Blocks the CI/CD merge.
2. Generates a Layer Violation Report in the CI/CD output.
3. Requires Engineering review before the PR can proceed.
4. If the violation was intentional and justified: requires an EDR.
5. Repeated violations from the same contributor trigger code review escalation.

---

## 5.5 Cross-Layer Communication

When a lower-layer component needs to communicate information to a higher-layer
component without creating an upward dependency, two patterns are used:

**Pattern 1 — EventBus Events**
The lower-layer component publishes an event to the EventBus.
The higher-layer component subscribes to the event.
The dependency is inverted: the lower layer depends only on the EventBus interface,
not on the higher-layer component.

Example: RiskGuardian (Layer 9) publishes KILL_SWITCH_TRIGGERED to EventBus.
OrderManager (Layer 11) subscribes to KILL_SWITCH_TRIGGERED.
Layer 9 does not import from Layer 11. Layer 11 subscribes via EventBus.

**Pattern 2 — Callback Registration**
A higher-layer component registers a callback with a lower-layer component
at initialization time. The lower-layer component calls the callback without
importing the higher-layer component.

Example: LearningEngine (Layer 13) registers a callback with TradeMonitor (Layer 12)
at startup. When a trade completes, TradeMonitor calls the callback.
Layer 12 does not import from Layer 13. Layer 13 registered the callback at startup.

**Anti-Pattern — Forbidden:**
Lower-layer component imports from higher-layer component for direct function call.
This is an upward dependency and is forbidden without exception.

---

## 5.6 Shared Services

Shared services are components that are used by multiple layers without
being in the dependency chain of any specific layer. They are always at Layer 0
(core or infrastructure).

**IIOS Shared Services:**

| Service | Package | Access Pattern | Used By |
|---------|---------|----------------|---------|
| EventBus | iios.infrastructure.event_bus | get_event_bus() | All layers |
| Logging | iios.infrastructure.logging_system | Standard logger | All layers |
| SQLite DB | iios.infrastructure.database | DatabaseConnectionManager | 3, 8-17 |
| Config | iios.infrastructure.config | ConfigurationSnapshot | All layers |
| SystemMonitor | iios.infrastructure.system_monitor | SystemMonitor.time_layer() | 1-17 |

**Shared Service Access Rules:**
- Shared services are accessed through their defined factory functions or singletons.
- Shared services are initialized in Layer 0 (bootstrap phase) before any Layer 1+ code runs.
- A layer that uses a shared service declares it in its __manifest__.json dependencies.
- Shared services must not depend on any layer (Layer 0 position is absolute).

---

## 5.7 Common Interfaces

Common interfaces are abstract base classes defined in iios.core.interfaces
that enable polymorphism across the system.

**IIOS Common Interfaces:**

| Interface | Module | Implemented By | Layer |
|-----------|--------|----------------|-------|
| BaseFeed | iios.core.interfaces.base_feed | DhanFeed, YahooFeed, ReplayFeed | 0 |
| BaseAgent | iios.core.interfaces.base_agent | All AI agents | 10+ |
| BaseStrategy | iios.core.interfaces.base_strategy | All strategy classes | 5 |
| BaseScanner | iios.core.interfaces.base_scanner | All scanner agents | 4 |
| DebateAgent | iios.decision.debate.base_debate_agent | 5 debate agents | 10 |

**Interface Change Policy:**
Interfaces in iios.core.interfaces are PROTECTED INTERFACES.
Changing an interface signature requires:
1. Architecture Council vote.
2. Engineering Decision Record.
3. All implementations updated in the same commit.
4. All tests updated in the same commit.
5. MAJOR version bump in all affected packages.

---

## 5.8 Version Compatibility

**Version Compatibility Rules:**

Rule VC-1 — Package versions are independent.
Each package version advances independently. The iios.core package at version 1.3.0
is compatible with iios.intelligence at version 1.1.0 as long as the core
interface version has not introduced breaking changes.

Rule VC-2 — Interface versions are tracked separately.
The interface version (defined in __init__.py as INTERFACE_VERSION) advances
only when the public interface changes. Internal changes do not advance the interface version.

Rule VC-3 — Breaking changes require major version bumps.
Any change to a public interface (method signature, return type, exception type)
is a breaking change and requires a MAJOR version increment.

Rule VC-4 — Additive changes require minor version bumps.
Adding new public methods, new optional parameters, or new exports is additive
and requires a MINOR version increment.

Rule VC-5 — Fix releases require patch version bumps.
Bug fixes with no interface change require only a PATCH version increment.

---

## 5.9 Future Expansion

**Dependency Framework Future Expansion Rules:**

Rule FE-1 — Wave 20 (Institutional) dependencies are additive.
Wave 20 adds new packages. It does not modify dependency relationships
of existing Wave 1-19 packages.

Rule FE-2 — Multi-repo expansion is designed in.
The iios/ namespace package structure supports splitting into multiple
pip-installable repositories. The iios.core package could be published as
iios-core on pip. All other packages depend on iios-core as an external
dependency. No structural change required.

Rule FE-3 — New data sources follow the plugin pattern.
A new data source (Bloomberg, Refinitiv) is a DATA_PLUGIN that implements
BaseFeed. It does not modify the DataFeedManager or any core package.

Rule FE-4 — New AI agents are self-registering.
A new agent type provides a __manifest__.json that declares its type and
interface. The AI Agent Registry discovers and loads it automatically.
No core package modification required.

---

*End of Part V*

---

# PART VI — CONSTRUCTION LIFECYCLE

## 6.1 Lifecycle Overview

The repository construction lifecycle defines how the IIOS repository evolves
from an empty directory to a certified production system. The lifecycle has
ten phases, each with defined entry criteria, activities, exit criteria, and outputs.

`
REPOSITORY CONSTRUCTION LIFECYCLE

Phase 1:  Repository Creation          (one-time)
Phase 2:  Folder Creation              (one-time per wave)
Phase 3:  Package Registration         (per package)
Phase 4:  Module Registration          (per module)
Phase 5:  Dependency Validation        (per wave)
Phase 6:  Certification                (per wave + per package)
Phase 7:  Version Control              (continuous)
Phase 8:  Evolution                    (per wave)
Phase 9:  Refactoring                  (with governance)
Phase 10: Retirement                   (per deprecated component)
`

---

## 6.2 Phase 1 — Repository Creation

**Trigger:** Wave 1 begins.
**Authority:** Architecture Council.

**Activities:**
1. Create the root directory i_trading_brain/.
2. Initialize git repository (git init).
3. Create .gitignore (exclude: data/, .venv/, __pycache__/, .env).
4. Create iios/ namespace package directory with root __init__.py.
5. Create config.py with all required constants (initial values).
6. Create main.py stub.
7. Create equirements.txt with initial pinned dependencies.
8. Create Dockerfile and docker-compose.yml.
9. Create uild_manifest.json (initially empty).
10. Create .github/ directory with CI/CD workflow files.
11. Create root documentation files: README.md, ARCHITECTURE.md, CHANGELOG.md.
12. Initial commit with tag 0.0.0-bootstrap.

**Exit Criteria:**
- Root directory exists with complete structural skeleton.
- Git repository initialized with initial commit.
- CI/CD pipeline can run on the empty skeleton.

**Lifecycle Diagram:**
`
[EMPTY DIRECTORY]
      |
      v
git init + root skeleton
      |
      v
config.py + main.py + requirements.txt
      |
      v
Dockerfile + docker-compose.yml
      |
      v
.github/ CI/CD workflows
      |
      v
Initial commit: v0.0.0-bootstrap
      |
      v
[REPOSITORY CREATED]
`

---

## 6.3 Phase 2 — Folder Creation

**Trigger:** Wave N begins (after Wave N-1 completion).
**Authority:** Domain Owner (with Architecture Council wave start authorization).

**Activities:**
1. Create all package directories for Wave N components.
2. Create __init__.py in each new directory (initially empty).
3. Create __manifest__.json in each new package (from template).
4. Create README.md in each new package (from template).
5. Create 	ests/ subdirectory in each new package.
6. Create conftest.py in each new test directory.
7. Commit folder structure: message [W{N}] Scaffold: {package_name} package structure.

**Folder Creation Rules:**
- Create only the folders required for the current wave. No speculative folders.
- Folder names use lowercase with underscores. No CamelCase.
- Each package directory has exactly one primary responsibility.
- Test directories mirror source directories exactly.

---

## 6.4 Phase 3 — Package Registration

**Trigger:** Package folder structure is created.
**Authority:** Domain Owner.

**Activities:**
1. Fill in __manifest__.json with: name, version, description, layer, classification, wave, owner, dependencies.
2. Run 	ools/manifest_validator.py to verify manifest schema.
3. Register package in uild_manifest.json.
4. Verify Dependency Resolver can parse the manifest without errors.
5. Verify import graph remains acyclic after adding the new package.
6. Commit: [W{N}] Register: {package_name} in module registry.

**Package Registration Validation:**
The 	ools/manifest_validator.py tool checks:
- All required manifest fields present.
- Declared dependencies reference known packages.
- No circular dependencies introduced.
- Layer number consistent with claimed position in the architecture.

---

## 6.5 Phase 4 — Module Registration

**Trigger:** Module implementation begins for a registered package.
**Authority:** Domain Owner.

**Activities:**
1. Create the module file (.py) with the module docstring template:
   `
   Module: {module_name}
   Package: {package_name}
   Wave: W{N}
   Layer: {layer_number} — {layer_name}
   Purpose: {single sentence}
   Constraints: {any critical constraints}
   `
2. Declare public exports in __init__.py after implementation.
3. Create corresponding test file in 	ests/.
4. Add module to module registry entry in uild_manifest.json.
5. Run 	ools/module_auditor.py to verify:
   - Module docstring present.
   - Imports are legal (no upward dependencies).
   - File size within limits.

---

## 6.6 Phase 5 — Dependency Validation

**Trigger:** Before each wave's first PR is merged.
**Authority:** Architecture Council (automated + manual review).

**Activities:**
1. Run 	ools/import_graph_analyzer.py on complete codebase.
2. Verify no cycles in import graph.
3. Verify all layer boundaries are respected.
4. Verify all interface signatures match their specifications.
5. Run 	ools/interface_comparator.py on critical interfaces.
6. Generate Dependency Validation Report.
7. Architecture Council reviews report at wave completion review.

**Dependency Validation Report Contents:**
- Total packages in repository.
- Total edges in import graph.
- Layer boundary violations (should be zero).
- Circular dependency chains (should be zero).
- Interface signature changes since previous wave (should match EDR records).

---

## 6.7 Phase 6 — Certification

**Trigger:** Wave completion review by Architecture Council.
**Authority:** Architecture Council (issues certification).

**Certification Process:**
1. CI/CD report reviewed: all checks green.
2. Coverage report reviewed: all new modules >= 95%.
3. Dependency Validation Report reviewed: zero violations.
4. Security scan reviewed: zero CRITICAL/HIGH CVEs, zero secrets.
5. Performance benchmark reviewed: latency targets met.
6. Architecture Council vote: certification accepted or rejected.
7. Certification record created in docs/certification/.

**Certification Levels Applied:**
- W1 Core Foundation: Level 4 (PRODUCTION-READY).
- W2 Infrastructure: Level 4 (PRODUCTION-READY).
- W3-W8 Knowledge, Observation, Reasoning: Level 3 (CERTIFIED).
- W9-W16 Decision, Risk, Execution, Learning: Level 4 (PRODUCTION-READY) at v1.0.0.
- W17-W19 Integration, Optimization, Production: Level 4 for all.
- W20 Institutional Expansion: Level 5 target.

---

## 6.8 Phase 7 — Version Control

**Continuous activities:**

**Commit Policy:**
- Every commit is focused: one logical change.
- Commit message format: [W{N}] {Type}: {description}.
  Types: Scaffold, Implement, Fix, Test, Refactor, Docs, Register.
- No commit mixes feature changes with dependency upgrades.
- No commit mixes multiple package changes without explicit multi-package context.

**Branch Policy:**
- main branch: always deployable. All CI/CD checks pass.
- Feature branches: wave-{N}/{component}.
- Hotfix branches: hotfix/{description}.
- No direct commits to main (PRs only).

**Tag Policy:**
- Wave completion: tag 0.{N}.0-alpha.1 through 0.{N}.0-rc.1.
- Production release: tag 1.0.0.
- Hotfix: tag {X}.{Y}.{Z+1}.

**Version Control Invariants:**
- main branch history is never rewritten.
- No force-push to main.
- No amend of published commits.

---

## 6.9 Phase 8 — Evolution

**Trigger:** Wave N begins. Requires Wave N-1 completion.
**Authority:** Domain Owner with Architecture Council wave start authorization.

**Evolution Rules:**
- New packages are ADDED. Existing packages are not reorganized.
- If reorganization is needed, it is treated as a separate pre-wave activity with an EDR.
- New modules extend existing packages through addition, not modification of working code.
- Public interfaces are NOT changed (unless an EDR authorizes a breaking change).
- Config values MAY be added to config.py (additive).

**Evolution Anti-Patterns (forbidden):**
- Reorganizing working packages as part of a feature wave.
- Changing module names in a working package during a feature wave.
- Removing or deprecating modules before the replacement is fully operational.

---

## 6.10 Phase 9 — Refactoring

**Trigger:** Explicit Architecture Council decision. Not triggered by wave work.
**Authority:** Architecture Council (unanimous vote for refactors affecting multiple packages).

**Refactoring Governance:**
1. Refactoring proposal submitted with: motivation, affected packages, risk assessment.
2. Architecture Council reviews proposal (NOT the same wave as feature work).
3. If approved: EDR created. Refactoring plan written.
4. Refactoring is a separate wave-like activity with its own completion record.
5. All existing tests must pass after refactoring (no regressions accepted).
6. All existing public interfaces preserved after refactoring.

---

## 6.11 Phase 10 — Retirement

**Trigger:** A component is replaced by a new implementation.
**Authority:** Domain Owner (with Architecture Council acknowledgment).

**Retirement Process:**
1. New implementation is complete and certified at same or higher level than old.
2. All callers of the old module are updated to use the new module.
3. Old module moved to _deprecated/ with original path preserved.
4. Deprecation header added to old module.
5. uild_manifest.json updated to mark old module as DEPRECATED.
6. CHANGELOG.md entry added: version, deprecated component, replacement.
7. Old module retained for minimum one year before archival.

---

*End of Part VI*

# PART VII — QUALITY FRAMEWORK

## 7.1 Repository Quality Standards

Repository quality is measured across six dimensions at the repository level,
the package level, and the module level. Standards are measurable and
enforced by automated tooling.

**Six Quality Dimensions:**
1. **Maintainability** — How easily the codebase can be understood and modified.
2. **Scalability** — How the repository handles growth in modules and teams.
3. **Security** — How protected the system is from compromise.
4. **Performance** — How responsive the system is at defined latency budgets.
5. **Documentation** — How well the system is described and explained.
6. **Consistency** — How uniform the code style, naming, and structure are.

---

## 7.2 Maintainability Standards

| Metric | Standard | Enforcement |
|--------|---------|-------------|
| Module file size | <= 500 lines | Automated linter |
| Cyclomatic complexity | <= 10 per function | Flake8 + radon |
| Cognitive complexity | <= 15 per function | SonarQube equivalent |
| Import count per module | <= 15 imports | Automated check |
| Dependency count per package | <= 6 direct deps | Manifest validator |
| Public interface methods per class | <= 20 | Code review |
| Function length | <= 50 lines | Automated linter |
| Max nesting depth | <= 4 | Automated linter |
| Boolean function arguments | 0 (use enums) | Code review |

**Maintainability Score Computation:**
Each module is assigned a maintainability score 0-100.
Score >= 80: GOOD.
Score 60-79: REVIEW.
Score < 60: REFACTOR — blocks certification.

---

## 7.3 Scalability Standards

| Metric | Standard | Enforcement |
|--------|---------|-------------|
| Package count | No limit (additive) | Architecture registry |
| Module count per package | <= 25 (review above 15) | Manifest check |
| Test count per module | >= 5 (review below 5) | Coverage report |
| Class hierarchy depth | <= 3 | Code review |
| New package isolation | Required | Import graph |
| Package size (lines) | <= 5,000 (review > 3,000) | Automated scan |
| Third-party deps per package | <= 4 | Manifest check |

**Scalability Design Principle:**
The repository must scale to 100 packages and 500 modules without requiring
structural reorganization. This is achieved through the package-per-layer
pattern and the plugin architecture for extensions.

---

## 7.4 Security Standards

| Metric | Standard | Enforcement |
|--------|---------|-------------|
| CRITICAL CVEs in dependencies | 0 tolerance | Dependabot + CI gate |
| HIGH CVEs in dependencies | 0 tolerance | Dependabot + CI gate |
| MEDIUM CVEs in dependencies | Patch within 14 days | Tracking |
| Secrets in code | 0 tolerance | detect-secrets + CI gate |
| SQL injection protection | Parameterized queries only | Code review |
| Input validation at boundaries | Required | Code review |
| Environment variable exposure in logs | Forbidden | Security scan |
| Hardcoded credentials | Forbidden (CI blocks) | detect-secrets |
| OWASP Top 10 compliance | Required at v1.0.0 | Security audit |

**Security Invariants:**
- All broker tokens and API keys are sourced from environment variables only.
- All database queries use parameterized statements.
- All input from Telegram commands is sanitized before use.
- Log statements never include account tokens, positions, or financial values in DEBUG mode when in production.

---

## 7.5 Performance Standards

| Metric | Standard | Enforcement |
|--------|---------|-------------|
| GlobalIntelligence.fetch() p99 | <= 17ms (cached) | Benchmark suite |
| MarketIntelligence p99 | <= 19ms | Benchmark suite |
| Full trading cycle p99 | <= 172ms (baseline) / 200ms (SLA) | Benchmark suite |
| Database write latency p99 | <= 5ms | Benchmark suite |
| EventBus publish latency p99 | <= 1ms | Benchmark suite |
| OrderManager.submit() latency | <= 50ms (paper mode) | Benchmark suite |
| Kill switch trigger latency | <= 100ms | Integration test |
| Telegram command response p99 | <= 2s | Integration test |
| CI/CD pipeline duration | <= 15 minutes | CI configuration |

**Performance Regression Policy:**
Any PR that causes a regression of more than 20% on any benchmark metric
is blocked until the regression is addressed. A regression is measured
against the last-certified baseline.

---

## 7.6 Documentation Standards

| Metric | Standard | Enforcement |
|--------|---------|-------------|
| Package README.md | Required for all packages | CI check |
| Package __manifest__.json | Required for all packages | Manifest validator |
| Module docstring | Required for all public modules | Pylint |
| Class docstring (public classes) | Required | Pylint |
| Method docstring (public methods) | Required | Pylint |
| Non-obvious algorithm documentation | Required | Code review |
| Wave completion record (WCR) | Required at each wave end | Manual process |
| Engineering Decision Record (EDR) | Required for breaking changes | Manual process |
| CHANGELOG.md entry | Required for every version tag | Manual process |
| Architecture diagram up-to-date | Required before v1.0.0 | Manual review |

**Documentation Coverage:**
Documentation coverage is measured as the ratio of documented public symbols
to total public symbols. Target >= 90% at Level 3 certification,
100% at Level 4 certification.

---

## 7.7 Consistency Standards

| Metric | Standard | Enforcement |
|--------|---------|-------------|
| PEP 8 compliance | 100% | Black + isort + flake8 |
| Import order | Standard → Third-party → Local | isort |
| Naming convention (classes) | PascalCase | Pylint |
| Naming convention (functions) | snake_case | Pylint |
| Naming convention (constants) | UPPER_SNAKE_CASE | Pylint |
| Naming convention (private) | _underscore_prefix | Pylint |
| Line length | <= 100 characters | Black |
| String quotes | Double quotes everywhere | Black |
| Type annotations | Required for public functions | mypy |
| Test naming | test_{function}_{scenario} | Convention |

**Consistency Enforcement Tools:**
- Black: auto-formatting (non-negotiable, no manual overrides allowed).
- isort: import sorting (non-negotiable).
- Flake8: style checking (non-negotiable).
- mypy: type checking (required at STRICT level for core and risk packages).

---

## 7.8 Package Quality Scorecard

Each package is evaluated before certification using the package quality scorecard.

**Package Quality Scorecard (all items required for Level 3+):**

| # | Dimension | Check | Pass Threshold |
|---|-----------|-------|----------------|
| PQ-1 | Maintainability | All modules <= 500 lines | 100% |
| PQ-2 | Maintainability | Cyclomatic complexity <= 10 | 100% |
| PQ-3 | Scalability | Module count <= 25 | Pass |
| PQ-4 | Scalability | Class hierarchy depth <= 3 | 100% |
| PQ-5 | Security | Zero CRITICAL/HIGH CVEs | 100% |
| PQ-6 | Security | Zero secrets detected | 100% |
| PQ-7 | Performance | All latency benchmarks met | 100% |
| PQ-8 | Documentation | README.md present and complete | Pass |
| PQ-9 | Documentation | All public symbols documented | >= 90% |
| PQ-10 | Consistency | Black/isort/flake8 all pass | 100% |
| PQ-11 | Testing | Test coverage >= 95% | Pass |
| PQ-12 | Testing | All tests passing | 100% |

---

*End of Part VII*

---

# PART VIII — GOVERNANCE

## 8.1 Ownership Model

IIOS uses a domain-ownership model. Each package is owned by one team.
Ownership means: the owning team is responsible for quality, certification,
and evolution of all modules in the package.

**Ownership Matrix:**

| Package Cluster | Owning Team | Key Responsibilities |
|----------------|-------------|----------------------|
| iios.core | Platform Team | Core types, interfaces, utilities |
| iios.infrastructure | Platform Team | Data feeds, database, events |
| iios.intelligence | Intelligence Team | Global and market intelligence |
| iios.knowledge | Knowledge Team | Knowledge base, ontology |
| iios.observation | Intelligence Team | Opportunity observation |
| iios.relationship | Knowledge Team | Entity relationships |
| iios.events | Platform Team | Event types, handlers |
| iios.reasoning | Intelligence Team | Reasoning, meta-learning |
| iios.strategy | Strategy Team | Strategy definition, generation |
| iios.decision | Decision Team | Debate, aggregation, engine |
| iios.risk | Risk Team | Capital, portfolio, guardian |
| iios.execution | Execution Team | Order management, journal |
| iios.monitoring | Execution Team | Trade monitoring, P&L |
| iios.learning | Learning Team | Performance tracking, analytics |
| iios.research | Research Team | Research pipeline, validation |
| iios.control | Platform Team | Telemetry, dashboards |
| iios.agents | Multiple (by agent type) | Agent implementations |
| iios.simulation | Risk Team | Monte Carlo, scenarios |
| iios.replay | Research Team | Replay engine |
| interfaces/ | Platform Team | Dashboard, Telegram, reporting |

**Protected Module Ownership — Architecture Council:**
- isk_guardian/risk_guardian.py
- strategy_lab/backtesting_ai.py
- alidation_engine/validation_engine.py and all 6 stage files.
- evolved_strategies/ directory.
- data/ directory (schema changes require Architecture Council approval).
- dhan_feed.py (broker auth + order routing).

---

## 8.2 Repository Governance

**Repository Governance Bodies:**

**Architecture Council:**
- Composed of: Lead Architect, Senior Platform Engineer, Senior Risk Engineer.
- Authority: wave start authorization, certification issuance, EDR approval.
- Meeting cadence: per wave completion + on-demand for critical decisions.

**Domain Owners:**
- One per team (Platform, Intelligence, Knowledge, Strategy, Decision, Risk, Execution, Learning, Research).
- Authority: day-to-day development decisions within their package cluster.
- Escalation: Architecture Council for cross-package changes.

**Security Officer:**
- One person.
- Authority: security policy, CVE response, secret detection configuration.
- Must review all PRs that change infrastructure, authentication, or credentials.

---

## 8.3 Package Governance

**Package Change Governance:**

| Change Type | Authority | Process |
|------------|-----------|---------|
| Add new module | Domain Owner | PR + peer review |
| Modify internal module | Domain Owner | PR + peer review |
| Modify public interface | Architecture Council | EDR + Architecture vote |
| Add new public export | Domain Owner | PR + Architecture review |
| Remove public export | Architecture Council | EDR + Architecture vote |
| Rename module | Architecture Council | EDR (blocks imports everywhere) |
| Merge two packages | Architecture Council | EDR + major version bump |
| Add new protected module | Architecture Council | Explicit EDR |
| Change protected module | Architecture Council | Explicit instruction + EDR |

---

## 8.4 Review and Approval Workflow

**Standard Pull Request Workflow:**

`
Developer Creates Feature Branch
         |
         v
Developer Implements + Tests
         |
         v
Developer Runs Local CI (make check)
         |
         v
Developer Opens PR to main
         |
         v
CI/CD Pipeline Runs (automated)
    - Black/isort/flake8
    - mypy type checks
    - pytest full suite
    - Coverage gate (>= 95%)
    - Import graph analysis
    - Security scan (detect-secrets)
    - Performance benchmarks
         |
     [PASS?] ---No---> Developer Fixes Failures
         |
        Yes
         v
Peer Review (Domain Owner or delegate)
    - Code review
    - Documentation review
    - Test coverage review
         |
     [APPROVED?] ---No---> Developer Addresses Comments
         |
        Yes
         v
[Protected Module?] ---Yes---> Architecture Council Review
         |
        No
         v
Merge to main
         |
         v
CI/CD on main branch runs
         |
         v
[Deploy] --- Auto-deploy to VPS (docker compose up -d)
`

**Deployment Invariant:**
Every merge to main is followed by deployment to VPS.
A deployed main must show BOTH containers HEALTHY.
Split-brain state (local committed, VPS not updated) must never persist.

---

## 8.5 Refactoring Governance

**Refactoring Governance Rules:**

Rule RG-1 — Refactoring requires an EDR.
Every refactoring that changes package boundaries, module names, or public interfaces
requires an Engineering Decision Record before implementation.

Rule RG-2 — Refactoring has a dedicated PR.
A refactoring PR contains ONLY refactoring changes. It does not mix feature
changes with refactoring. Mixed PRs are rejected.

Rule RG-3 — Protected modules cannot be refactored speculatively.
Protected modules (isk_guardian.py, acktesting_ai.py, alidation_engine/)
are refactored only with explicit Architecture Council instruction.

Rule RG-4 — Refactoring is regression-free.
After refactoring, all tests pass. All benchmarks meet their targets.
Any regression caused by refactoring blocks the refactoring merge.

Rule RG-5 — Interface preservation.
Refactoring preserves all existing public interfaces. If refactoring
requires an interface change, the interface change goes through the
full EDR + Architecture Council vote process.

---

## 8.6 Architecture Protection

**Architecture Protection Mechanisms:**

**Mechanism AP-1 — Import Graph Enforcement**
The import graph analysis tool is a required CI/CD gate. It cannot be disabled
without Architecture Council vote and EDR. If the tool is unavailable, the
CI/CD pipeline blocks all merges.

**Mechanism AP-2 — Protected Module File Checksums**
Protected module files have their SHA-256 checksums recorded in uild_manifest.json.
A CI/CD check compares current checksums against recorded checksums.
Any unrecorded change to a protected module blocks the PR.
Architecture Council must update the checksum record when authorizing a protected module change.

**Mechanism AP-3 — Manifest Validation**
Every __manifest__.json is validated by the manifest validator tool.
A malformed or inconsistent manifest blocks the PR.

**Mechanism AP-4 — Architectural Invariants Test**
A dedicated test file (	ests/integration/test_architecture_invariants.py)
verifies:
- Exactly 5 debate agents registered.
- DECISION_THRESHOLD is 6.5 (from config, not hardcoded).
- All singletons only accessible through factory functions.
- All kill switch thresholds sourced from config.py.
This test runs on every CI/CD pipeline execution.

---

## 8.7 Audit Process

**Audit Triggers:**
- Wave completion (mandatory).
- Production incident involving a protected module.
- Architecture Council discretion.
- Annual repository health audit (mandatory).

**Audit Activities:**
1. Review import graph for any new boundary violations.
2. Review uild_manifest.json for any unregistered modules.
3. Review protected module checksums for unauthorized changes.
4. Review CHANGELOG.md for completeness.
5. Review certification records for all packages.
6. Review documentation coverage across all packages.
7. Review dependency vulnerability report.
8. Review performance benchmark history.

**Audit Report:**
An audit report is generated and stored in docs/certification/audit-{date}.md.
Audit findings are classified:
- CRITICAL: blocks next wave start until resolved.
- MAJOR: must be resolved within the current wave.
- MINOR: tracked, resolved before next certification.

---

*End of Part VIII*

---

# PART IX — ENGINEERING CONSTITUTION

## 9.0 Preamble

The Engineering Constitution codifies the non-negotiable principles, rules, and
invariants governing the IIOS repository. These rules are not guidelines.
They are enforceable standards that govern every file, every module, every package,
and every deployment. Deviation from the constitution requires an EDR and
Architecture Council vote.

These rules are organized into ten categories. Each rule has a unique identifier.

---

## 9.1 Repository Structure Rules

**RS-001:** The root iios/ namespace package is the only top-level Python package
in the repository. All trading system code lives under iios/.

**RS-002:** config.py lives at the root and contains all trading behavior constants.
No other file may define a duplicate of any constant in config.py.

**RS-003:** main.py is the sole entry point for the trading system.
main.py does not contain business logic. It only orchestrates startup.

**RS-004:** The data/ directory is persistent state. It is never deleted, never
committed to git, and never overwritten without explicit migration scripts.

**RS-005:** The .venv/ virtual environment is never committed to git.

**RS-006:** All environment variables are loaded from .env at startup.
The .env file is never committed to git. An env.example file is committed
with all required variable names (no values).

**RS-007:** No executable script lives in the root of the repository
except main.py. All other scripts live in scripts/ or 	ools/.

**RS-008:** The _deprecated/ directory preserves historical modules.
It is never deleted. Its contents are never imported by production code.

**RS-009:** uild_manifest.json is the authoritative machine-readable registry
of all packages, modules, and their certification status.

**RS-010:** Root documentation files (README.md, ARCHITECTURE.md, CHANGELOG.md)
are always up-to-date before any production release.

---

## 9.2 Package Organization Rules

**PO-001:** Every package directory contains exactly: __init__.py,
__manifest__.json, README.md, and 	ests/ subdirectory.

**PO-002:** A package's __init__.py exports exactly its public interface.
It does not export internal implementation details.

**PO-003:** Package names use lowercase with underscores. No hyphens. No CamelCase.

**PO-004:** Every package has exactly one owning team declared in its manifest.

**PO-005:** Package classification is one of: CRITICAL, CORE, PROTECTED, OPTIONAL.
CRITICAL and CORE packages are always included. OPTIONAL packages may be absent
in minimal deployments.

**PO-006:** A package that grows beyond 25 modules is reviewed for decomposition
into sub-packages. Growth beyond 25 modules does not automatically trigger
decomposition; it triggers a review.

**PO-007:** A new package may not be added without a corresponding entry in
uild_manifest.json and a valid __manifest__.json.

**PO-008:** A package may not declare a dependency on itself (no self-referential deps).

**PO-009:** A package's declared certification level may only INCREASE, never decrease,
without an explicit architectural decision record.

**PO-010:** Packages labeled EXPERIMENTAL are never imported by production packages.
CI/CD enforces this through import graph analysis.

---

## 9.3 Dependency Management Rules

**DM-001:** No circular dependencies. Enforced by the import graph tool on every commit.

**DM-002:** No upward layer dependencies. Layer N may not import from Layer N+1 or higher.

**DM-003:** All third-party imports are declared in equirements.txt with exact version pins.

**DM-004:** A new third-party dependency requires Security Officer review.
Dependencies with known CVEs are not added.

**DM-005:** iios.core depends only on the Python standard library. No exceptions.

**DM-006:** All singletons are accessed through their factory functions.
Direct class instantiation of singletons is a build violation.

**DM-007:** config.py values are imported at module level, not inside functions.
Runtime re-reading of config is forbidden (configuration is immutable after bootstrap).

**DM-008:** Import from another package's private or internal modules is forbidden.
All inter-package imports use the public interface only.

**DM-009:** Plugin dependencies are declared separately from core dependencies.
Plugins that fail to load do not block core system startup.

**DM-010:** Interface version compatibility is checked by the Dependency Resolver at startup.
A version mismatch between a declared interface version and the installed version blocks startup.

---

## 9.4 Modularity Rules

**MD-001:** No module exceeds 500 lines. Modules approaching this limit are candidates
for decomposition in the next wave.

**MD-002:** Module cyclomatic complexity target is <= 10. Modules with complexity > 15
are REQUIRED to be refactored before the next wave.

**MD-003:** A module exports exactly the symbols it declares in its docstring's
"Public Exports" section. Undeclared exports are a specification violation.

**MD-004:** Every module has a module-level docstring that states:
purpose, wave, layer, and any critical constraints.

**MD-005:** Test modules mirror source modules 1:1.
strategy_generator_ai.py → 	ests/test_strategy_generator_ai.py.
A source module without a corresponding test module cannot be certified.

**MD-006:** Internal modules within a package are never imported by external packages.

**MD-007:** Constants that are used only within one module are defined in that module,
not in config.py. Only system-wide trading behavior constants belong in config.py.

**MD-008:** Class-level constants are always accessed as self.CONSTANT_NAME inside
instance methods. Module-level constants are accessed by their bare name.
(This prevents the NameError bug documented in the patterns.md record.)

**MD-009:** No print() statements in production code. All output goes through the
structured logging system.

**MD-010:** No bare except: or except Exception: clauses without explicit logging
and re-raising or handling. Silent exception swallowing is forbidden.

---

## 9.5 Maintainability Rules

**MA-001:** Boolean function parameters are forbidden. Use enums or named configurations.
place_order(True) is a violation. place_order(mode=OrderMode.PAPER) is correct.

**MA-002:** Magic numbers are forbidden. All numeric constants are named.
if vix > 45.0 in a trading method is a violation.
if vix > KILL_SWITCH_VIX_THRESHOLD is correct.

**MA-003:** Max function parameter count is 6. Functions with more than 6 parameters
use a configuration object or a data class.

**MA-004:** Max nesting depth is 4. Code with more than 4 levels of nesting
is required to be refactored using early-return patterns.

**MA-005:** Dead code (unreachable code paths) is forbidden. Any code that cannot
be reached by any test is either deleted or documented with a future-use comment.

**MA-006:** Type annotations are required for all public function signatures.
def fetch(force: bool = False) -> GlobalSnapshot: is correct.
def fetch(force=False): in a public interface is a violation.

**MA-007:** No copy-paste duplication of more than 5 lines between modules.
Duplicate code is extracted to a shared utility in iios.core.utils.

**MA-008:** Every TODO, FIXME, or HACK comment references a tracking ticket.
Undated, untracked comments accumulate technical debt without accountability.

**MA-009:** No commented-out code blocks. Dead code that is removed is permanently
deleted (or archived in _deprecated/). Commented-out code confuses future readers.

**MA-010:** Error messages in exceptions include: what failed, what was expected,
what was received. Generic messages like ValueError: invalid input are violations.

---

## 9.6 Documentation Rules

**DC-001:** README.md in every package describes: purpose, public interface,
dependencies, constraints, and the wave in which it was created.

**DC-002:** Every public method has a docstring with: purpose (one sentence),
parameters (each), return type, and exceptions raised.

**DC-003:** A Wave Completion Record (WCR) is written for every wave that completes.
The WCR records: what was built, what was deferred, what was learned.

**DC-004:** An Engineering Decision Record (EDR) is written for every decision that
changes a public interface, adds a dependency, or deviates from the specification.

**DC-005:** The CHANGELOG.md entry for every version tag includes:
version, date, wave, added components, fixed issues, breaking changes.

**DC-006:** Architectural diagrams are updated when the architecture changes.
An outdated diagram is a documentation defect.

**DC-007:** Non-obvious algorithmic choices are documented with a comment
explaining: why this approach, what alternatives were considered, why they were rejected.

**DC-008:** All configuration parameters in config.py have an inline comment
explaining: what it controls, what its range or valid values are, and what
happens if it is set out of range.

**DC-009:** The __manifest__.json file for every package is kept current.
Stale manifests (version not updated after release) are CI/CD violations.

**DC-010:** Every security-sensitive module (dhan_feed.py, risk_guardian.py)
has a security section in its docstring documenting: what secrets it handles,
how they are protected, and what the blast radius of a compromise would be.

---

## 9.7 Governance Rules

**GV-001:** No commit to main without a passing CI/CD pipeline. No exceptions.

**GV-002:** No breaking interface change without an Engineering Decision Record.

**GV-003:** No modification to a protected module without explicit Architecture Council instruction.

**GV-004:** No deployment without verifying that both Docker containers show
Up ... (healthy) in docker compose ps. A partial deployment is a split-brain state.

**GV-005:** No deletion of files in data/ without explicit Architecture Council approval.
The data directory contains live SQLite databases and operational state.

**GV-006:** The kill switch thresholds (VIX 45.0, daily loss 2.0%) may not be changed
without Architecture Council vote and EDR.

**GV-007:** The DECISION_THRESHOLD (6.5) may not be changed without
Architecture Council vote, EDR, and a backtest demonstrating outcome neutrality or improvement.

**GV-008:** The promotion gate criteria (WinRate >= 50%, Sharpe > 0.8, MaxDD < 15%)
may not be changed without Architecture Council vote and a research study justifying the change.

**GV-009:** No force-push to main. No amendment of published commits.
The main branch history is immutable.

**GV-010:** The uild_manifest.json is the authoritative state of the repository.
Any component that exists in the filesystem but not in uild_manifest.json
is an unregistered component and is not allowed in production.

---

## 9.8 Security Rules

**SC-001:** All secrets (API keys, broker tokens, database passwords) are
loaded from environment variables. No secret is hardcoded in any source file.

**SC-002:** detect-secrets is a required CI/CD gate. Any commit that introduces
a secret pattern (even in test files) is blocked.

**SC-003:** All database queries use parameterized statements.
String concatenation to build SQL queries is forbidden.

**SC-004:** All input received from external sources (Telegram, API, environment variables)
is validated before use. Unvalidated external input is an injection risk.

**SC-005:** Log statements never include account tokens, session tokens, or
personally identifiable information. Sanitized logging helpers are used for
any value that might contain sensitive data.

**SC-006:** CRITICAL and HIGH CVEs in any dependency must be patched within
7 days of notification. All other CVEs within 30 days.

**SC-007:** Docker container runs as a non-root user. Root execution
in production containers is forbidden.

**SC-008:** No unused dependency remains in equirements.txt.
Unused dependencies expand the attack surface.

**SC-009:** The Telegram bot only responds to commands from whitelisted chat IDs.
The whitelist is configured in the environment, not hardcoded.

**SC-010:** Network connections from the trading system are limited to declared
external services: Dhan API, yfinance, Telegram Bot API.
Connections to undeclared endpoints are a security violation.

---

## 9.9 Performance Rules

**PE-001:** GlobalDataAI.fetch() latency p99 <= 17ms in cached mode.
Any regression beyond 20% triggers a performance root cause investigation.

**PE-002:** Full trading cycle latency p99 <= 200ms (SLA).
Any regression beyond 15% triggers a performance review.

**PE-003:** No blocking I/O on the critical trading path.
Database writes on the critical path use async fire-and-forget patterns.

**PE-004:** No synchronous HTTP request on the critical trading path without timeout.
All HTTP requests specify a timeout. The default yfinance timeout is 8 seconds.

**PE-005:** The background pre-warm thread for GlobalDataAI runs continuously.
Any failure of the pre-warm thread is logged as WARNING and the next
direct fetch falls back to synchronous mode.

**PE-006:** The EventBus is non-blocking. Publishers do not wait for subscribers.
Subscriber processing happens asynchronously on subscriber threads.

**PE-007:** The kill switch response (from trigger to order halt) is <= 100ms.
The kill switch path has no I/O, no database calls, no network calls.

**PE-008:** Database queries on the data path use indexed columns only.
Unindexed queries that appear on the data path are a performance violation.

**PE-009:** Memory usage of the main trading process stays below 512MB.
Above 512MB triggers investigation. Above 1GB triggers restart.

**PE-010:** Benchmark results are recorded in docs/performance/ after every
wave that modifies any latency-sensitive component.

---

## 9.10 Future Evolution Rules

**FE-001:** The IIOS repository is designed for 20-wave evolution.
Architecture decisions consider their impact through Wave 20.

**FE-002:** Plugin interfaces are the primary extension mechanism.
New strategies, new data sources, and new analytics are plugins first.
Core modification is the last resort, not the first option.

**FE-003:** The namespace package structure (iios/) supports future
distribution as multiple pip-installable packages without structural change.

**FE-004:** All Wave 20 (Institutional) components are isolated under
iios/institutional/. They do not modify any Wave 1-19 package.

**FE-005:** The replay engine (iios/replay/) is designed to run any
Wave 1-19 component in historical simulation mode. New components
declare their replay compatibility in __manifest__.json.

**FE-006:** Multi-exchange expansion (NSE + BSE + MCX) adds new feed implementations
and new symbol ontology entries. It does not modify the core trading pipeline.

**FE-007:** Distributed deployment (multi-process, multi-machine) is supported
through the EventBus abstraction. Replacing the in-process EventBus with
a network-capable message broker (Redis Pub/Sub, Kafka) requires no change
to any package that publishes or subscribes to events.

**FE-008:** The AI agent framework is open for new agent types.
A new debate agent type (beyond the 5 core types) is added as a plugin.
The DebateOrchestrator accepts additional agents without modification.

**FE-009:** Performance learning models (ML regression, neural networks) are
experimental until Wave 20. They live in iios/experimental/ until they
graduate through the promotion pipeline.

**FE-010:** The constitution itself evolves through Amendment Records.
Each amendment is authored by the Architecture Council and appended to this document.
Amendments may strengthen rules. They may not weaken CRITICAL rules without unanimous vote.

---

*End of Part IX*

# PART X — REPOSITORY CERTIFICATION CHECKLIST

## 10.1 Certification Philosophy

Certification is the formal process by which the Architecture Council declares
that a component, package, wave, or the entire system meets the quality standards
required for production operation. Certification is not a one-time event;
it is a maturity level that each component achieves and maintains.

**Certification Levels:**
- **Level 0 — PLACEHOLDER:** File created, no implementation.
- **Level 1 — DEVELOPMENT:** Implementation in progress. Tests exist but coverage is incomplete.
- **Level 2 — INTEGRATED:** Implementation complete. Tests at >= 80% coverage. Integration tests pass.
- **Level 3 — CERTIFIED:** Tests at >= 95% coverage. All quality gates pass. Peer reviewed.
- **Level 4 — PRODUCTION-READY:** Level 3 plus: performance benchmarks pass, security audit passed, Architecture Council certified.
- **Level 5 — INSTITUTIONAL-GRADE:** Level 4 plus: external audit passed, disaster recovery tested, regulatory compliance verified.

---

## 10.2 Repository Ready Certification Matrix

| # | Check | Required For | Pass Condition |
|---|-------|-------------|----------------|
| RR-01 | Git repository initialized | All | .git/ directory exists |
| RR-02 | Initial commit with tag | All | 0.0.0-bootstrap tag exists |
| RR-03 | .gitignore correct | All | data/, .venv/, .env excluded |
| RR-04 | config.py complete | All | All trading constants defined |
| RR-05 | main.py entry point | All | SIGTERM handler present |
| RR-06 | equirements.txt pinned | All | All deps with exact versions |
| RR-07 | Dockerfile valid | All | Docker build succeeds |
| RR-08 | docker-compose.yml valid | All | Both containers defined |
| RR-09 | CI/CD pipeline active | Level 3+ | Workflow files in .github/ |
| RR-10 | uild_manifest.json exists | Level 3+ | Valid JSON, current content |
| RR-11 | ARCHITECTURE.md current | Level 4 | Matches current 17-layer structure |
| RR-12 | CHANGELOG.md complete | Level 4 | All versions documented |
| RR-13 | Security scan passing | Level 4 | Zero CRITICAL/HIGH CVEs, zero secrets |
| RR-14 | Root README.md complete | Level 4 | Setup and deployment instructions |

---

## 10.3 Folder Ready Certification Matrix

| # | Check | Required For | Pass Condition |
|---|-------|-------------|----------------|
| FR-01 | All 17 iios/ subdirs exist | Level 2+ | All layer packages present |
| FR-02 | All interface/ dirs exist | Level 3 | dashboard/, telegram/, reporting/ |
| FR-03 | All infrastructure/ dirs exist | Level 2 | database/, security/, deployment/ |
| FR-04 | tests/ mirrors iios/ | Level 3 | 1:1 correspondence |
| FR-05 | docs/ structure complete | Level 4 | All docs/ subdirs present |
| FR-06 | experimental/ isolated | Level 3 | No production imports from experimental/ |
| FR-07 | _deprecated/ maintained | Level 4 | All deprecated modules present |
| FR-08 | scripts/ organized | Level 3 | All scripts documented |
| FR-09 | tools/ populated | Level 3 | Import graph analyzer, manifest validator |
| FR-10 | data/ persistent volume | Level 4 | Docker volume mapping configured |

---

## 10.4 Package Ready Certification Matrix

| # | Check | Required For | Pass Condition |
|---|-------|-------------|----------------|
| PR-01 | __init__.py exists | Level 1 | File exists |
| PR-02 | __manifest__.json valid | Level 2 | Schema validates |
| PR-03 | README.md complete | Level 3 | Purpose and interface documented |
| PR-04 | 	ests/ directory exists | Level 2 | Directory created |
| PR-05 | conftest.py present | Level 3 | Shared fixtures defined |
| PR-06 | No upward imports | Level 2 | Import graph passes |
| PR-07 | No circular imports | Level 2 | Import graph passes |
| PR-08 | Coverage >= 95% | Level 3 | Coverage report |
| PR-09 | All tests passing | Level 3 | pytest green |
| PR-10 | Black/isort/flake8 pass | Level 3 | CI/CD gates |
| PR-11 | mypy passes (strict: core, risk) | Level 4 | mypy report |
| PR-12 | Performance benchmarks pass | Level 4 | Benchmark report |
| PR-13 | Security audit pass | Level 4 | Security report |
| PR-14 | Architecture Council sign-off | Level 4 | Council vote record |

---

## 10.5 Module Ready Certification Matrix

| # | Check | Required For | Pass Condition |
|---|-------|-------------|----------------|
| MR-01 | Module docstring present | Level 2 | docstring exists |
| MR-02 | Class docstrings present | Level 3 | all public classes |
| MR-03 | Method docstrings present | Level 3 | all public methods |
| MR-04 | Type annotations present | Level 3 | all public method sigs |
| MR-05 | File size <= 500 lines | Level 2 | line count |
| MR-06 | Cyclomatic complexity <= 10 | Level 3 | radon report |
| MR-07 | No print() statements | Level 2 | grep check |
| MR-08 | No bare except: | Level 2 | flake8 check |
| MR-09 | Corresponding test file exists | Level 2 | file exists |
| MR-10 | Test coverage >= 95% | Level 3 | coverage report |
| MR-11 | No magic numbers | Level 3 | code review |
| MR-12 | No boolean parameters | Level 3 | code review |
| MR-13 | Registered in build_manifest.json | Level 3 | manifest check |
| MR-14 | Protected module checksum recorded | Level 4 | manifest check |

---

## 10.6 Dependency Ready Certification Matrix

| # | Check | Required For | Pass Condition |
|---|-------|-------------|----------------|
| DR-01 | Import graph acyclic | Level 2 | import_graph_analyzer.py |
| DR-02 | No upward layer imports | Level 2 | import_graph_analyzer.py |
| DR-03 | All imports from public interface | Level 3 | code review |
| DR-04 | All third-party deps in requirements.txt | Level 2 | pip check |
| DR-05 | All deps pinned to exact version | Level 3 | requirements.txt review |
| DR-06 | Singletons via factory functions only | Level 3 | architectural invariants test |
| DR-07 | config.py values not duplicated | Level 3 | grep check |
| DR-08 | Interface versions compatible | Level 3 | Dependency Resolver check |
| DR-09 | No unused dependencies | Level 4 | pip-check + manual review |
| DR-10 | Dependency count <= 6 per package | Level 3 | manifest check |

---

## 10.7 Architecture Ready Certification Matrix

| # | Check | Required For | Pass Condition |
|---|-------|-------------|----------------|
| AR-01 | Exactly 5 debate agents registered | Level 4 | architecture invariants test |
| AR-02 | DECISION_THRESHOLD = 6.5 from config | Level 4 | architecture invariants test |
| AR-03 | Kill switch thresholds from config | Level 4 | architecture invariants test |
| AR-04 | All 4 singletons via factory functions | Level 4 | architecture invariants test |
| AR-05 | 17 layers implemented | Level 4 | architecture review |
| AR-06 | Protected modules checksum match | Level 4 | CI/CD gate |
| AR-07 | GlobalIntelligence latency <= 17ms | Level 4 | benchmark |
| AR-08 | MarketIntelligence latency <= 19ms | Level 4 | benchmark |
| AR-09 | Full cycle latency <= 200ms | Level 4 | benchmark |
| AR-10 | Kill switch latency <= 100ms | Level 4 | integration test |
| AR-11 | Feed fallback (Dhan to yfinance) works | Level 4 | integration test |
| AR-12 | Restart recovery works | Level 4 | integration test |

---

## 10.8 Documentation Ready Certification Matrix

| # | Check | Required For | Pass Condition |
|---|-------|-------------|----------------|
| DCR-01 | All packages have README.md | Level 3 | file existence check |
| DCR-02 | All EDRs written for breaking changes | Level 3 | EDR count vs change count |
| DCR-03 | All WCRs written for completed waves | Level 3 | WCR count vs wave count |
| DCR-04 | ARCHITECTURE.md current | Level 4 | manual review |
| DCR-05 | All public symbols documented | Level 4 | documentation coverage >= 90% |
| DCR-06 | Security sections in sensitive modules | Level 4 | code review |
| DCR-07 | config.py all constants commented | Level 3 | code review |
| DCR-08 | Runbooks for all operational procedures | Level 4 | RB-001 through RB-005 exist |
| DCR-09 | Performance benchmarks recorded | Level 4 | docs/performance/ present |
| DCR-10 | API documentation generated | Level 5 | sphinx/pydoc output |

---

## 10.9 Security Ready Certification Matrix

| # | Check | Required For | Pass Condition |
|---|-------|-------------|----------------|
| SR-01 | Zero CRITICAL CVEs | Level 2 | Dependabot + CI gate |
| SR-02 | Zero HIGH CVEs | Level 3 | Dependabot + CI gate |
| SR-03 | Zero secrets in code | Level 2 | detect-secrets |
| SR-04 | All queries parameterized | Level 3 | code review |
| SR-05 | All external input validated | Level 3 | code review |
| SR-06 | Telegram whitelist enforced | Level 4 | integration test |
| SR-07 | Container non-root user | Level 4 | Dockerfile review |
| SR-08 | No credentials in environment logs | Level 4 | security scan |
| SR-09 | OWASP Top 10 compliance | Level 4 | security audit |
| SR-10 | Penetration test clean | Level 5 | external penetration test report |

---

## 10.10 Future Ready Certification Matrix

| # | Check | Required For | Pass Condition |
|---|-------|-------------|----------------|
| FUR-01 | Plugin architecture operational | Level 4 | plugin registry test |
| FUR-02 | Replay engine functional | Level 4 | replay integration test |
| FUR-03 | Feature flags in config.py | Level 4 | all Wave 20 flags documented |
| FUR-04 | Namespace package structure ready | Level 4 | namespace package test |
| FUR-05 | EventBus abstraction layer in place | Level 4 | EventBus interface test |
| FUR-06 | Distributed deployment design validated | Level 5 | architecture review |
| FUR-07 | Multi-exchange expansion designed | Level 5 | EDR written |
| FUR-08 | ML model integration path designed | Level 5 | research proposal |
| FUR-09 | Disaster recovery procedure tested | Level 5 | DR drill record |
| FUR-10 | Institutional-grade audit passed | Level 5 | external audit report |

---

## 10.11 Master Certification Scorecard

**To achieve SYSTEM_CERTIFIED (production authorization for v1.0.0):**

All of the following must be true simultaneously:
- Repository Ready: All Level 4 checks PASS.
- Folder Ready: All Level 3 checks PASS.
- Package Ready: All Level 4 checks PASS for CRITICAL and CORE packages.
- Module Ready: All Level 3 checks PASS for all public modules.
- Dependency Ready: All Level 3 checks PASS.
- Architecture Ready: All Level 4 checks PASS.
- Documentation Ready: All Level 4 checks PASS.
- Security Ready: All Level 4 checks PASS.
- Future Ready: All Level 4 checks PASS.

**Failure on any single Level 4 check blocks SYSTEM_CERTIFIED.**

---

*End of Part X*

---

# APPENDIX A — REPOSITORY TREE REFERENCE

Complete annotated repository tree. This is the reference structure as it
should appear at v1.0.0. Wave numbers indicate when each component is created.

`
ai_trading_brain/                        [REPOSITORY ROOT]
|
|-- iios/                                [W1] Main Python namespace package
|   |-- __init__.py                      [W1] Namespace init (exports nothing)
|   |-- core/                            [W1] CRITICAL: Foundation
|   |   |-- __init__.py                  [W1] Exports all core public symbols
|   |   |-- __manifest__.json            [W1] Package metadata
|   |   |-- README.md                    [W1] Core package documentation
|   |   |-- exceptions/                  [W1] All IIOS exception classes
|   |   |-- types/                       [W1] TickerQuote, PriceBar, AgentScore, etc.
|   |   |-- utils/                       [W1] DecimalUtils, DatetimeUtils, SymbolUtils
|   |   |-- constants/                   [W1] GLOBAL_SYMBOL_MAP, regime constants
|   |   |-- interfaces/                  [W1] BaseFeed, BaseAgent, BaseStrategy
|   |   -- tests/                       [W1] All core tests
|   |
|   |-- infrastructure/                  [W2] CRITICAL: Infrastructure services
|   |   |-- __init__.py                  [W2]
|   |   |-- __manifest__.json            [W2]
|   |   |-- config/                      [W2] ConfigurationSnapshot
|   |   |-- data_feeds/                  [W2] DhanFeed (PROTECTED), YahooFeed, DataFeedManager
|   |   |-- database/                    [W2] SQLite connection, schema, migrations
|   |   |-- cache/                       [W2] In-memory cache with TTL
|   |   |-- event_bus/                   [W2] EventBus singleton, event types
|   |   |-- system_monitor/              [W2] SystemMonitor.time_layer() (PROTECTED INTERFACE)
|   |   |-- logging_system/              [W2] Structured logging, rotation
|   |   -- tests/                       [W2]
|   |
|   |-- intelligence/                    [W2/W8] CORE: Global + Market Intelligence
|   |   |-- global_intelligence/         [W2] GlobalDataAI (17ms cache + pre-warm)
|   |   |-- market_intelligence/         [W8] MarketIntelligenceAI, MarketMonitor (30s)
|   |   -- tests/                       [W8]
|   |
|   |-- knowledge/                       [W3/W4] CORE: Knowledge and Ontology
|   |   |-- knowledge_base/              [W3] KnowledgeStore, ContradictionDetector
|   |   |-- ontology/                    [W4] OntologyValidator, entity registry
|   |   -- tests/                       [W4]
|   |
|   |-- observation/                     [W5] CORE: Opportunity Observation
|   |   |-- opportunity_engine/          [W5] EquityScanner, OptionsEngine, Arbitrage
|   |   -- tests/                       [W5]
|   |
|   |-- relationship/                    [W6] CORE: Entity Relationships
|   |   |-- relationship_engine/         [W6] EntityRelationshipGraph
|   |   -- tests/                       [W6]
|   |
|   |-- events/                          [W7] CORE: Domain Events
|   |   |-- event_types/                 [W7] All IIOS domain event definitions
|   |   |-- event_handlers/              [W7] Event handler registrations
|   |   |-- event_audit/                 [W7] Event audit trail
|   |   -- tests/                       [W7]
|   |
|   |-- reasoning/                       [W8/W9] CORE: Reasoning Engine
|   |   |-- reasoning_engine/            [W9] ReasoningEngine
|   |   |-- meta_learning/               [W8] MetaLearning, get_regime_strategy_map()
|   |   -- tests/                       [W9]
|   |
|   |-- strategy/                        [W5/W13] CORE: Strategy Framework
|   |   |-- base/                        [W5] BaseStrategy, StrategyRegistry
|   |   |-- evolved_strategies/          [W13] PROTECTED: Earned evolved strategies
|   |   |-- generators/                  [W13] StrategyGeneratorAI (bug-fixed)
|   |   |-- backtesting/                 [W13] BacktestingAI (PROTECTED)
|   |   -- tests/                       [W13]
|   |
|   |-- decision/                        [W9] CRITICAL: Debate and Decision
|   |   |-- debate/                      [W9] 5 debate agents (BullAgent, BearAgent, ...)
|   |   |-- aggregation/                 [W9] ScoreAggregator
|   |   |-- engine/                      [W9] DecisionEngine (threshold 6.5)
|   |   -- tests/                       [W9]
|   |
|   |-- risk/                            [W6/W7/W11] CRITICAL: Risk Management
|   |   |-- capital/                     [W6] CapitalRiskEngine
|   |   |-- portfolio/                   [W7] RiskManagerAI, PortfolioAllocation
|   |   |-- stress/                      [W11] StressTestFilter
|   |   |-- guardian/                    [W11] RiskGuardian (PROTECTED) kill switch
|   |   -- tests/                       [W11]
|   |
|   |-- execution/                       [W11] CRITICAL: Order Execution
|   |   |-- order_manager/               [W11] OrderManager (paper + live)
|   |   |-- paper_journal/               [W11] CSV journal: data/paper_trades.csv
|   |   |-- broker/                      [W11] DhanBrokerAdapter (wraps dhan_feed.py)
|   |   |-- order_flow/                  [W11] OrderFlow event processing
|   |   -- tests/                       [W11]
|   |
|   |-- monitoring/                      [W15] CORE: Trade Monitoring
|   |   |-- trade_monitor.py             [W15] TradeMonitor
|   |   |-- strategy_health_monitor.py   [W15] StrategyHealthMonitor
|   |   |-- pnl_tracker.py               [W15] Real-time P&L
|   |   -- tests/                       [W15]
|   |
|   |-- learning/                        [W14] CORE: Learning System
|   |   |-- learning_engine.py           [W14] LearningEngine
|   |   |-- strategy_performance_tracker.py  [W14] Singleton via get_performance_tracker()
|   |   |-- analytics/                   [W14] DrawdownAnalyzer, WalkForwardTester
|   |   -- tests/                       [W14]
|   |
|   |-- research/                        [W13/W16] CORE: Research and Validation
|   |   |-- research_lab/                [W13] ResearchPipeline, PromotionGate
|   |   |-- validation_engine/           [W16] PROTECTED: 6-stage ValidationEngine
|   |   -- tests/                       [W16]
|   |
|   |-- control/                         [W17] CORE: Control Tower
|   |   |-- telemetry_writer.py          [W17] SQLite telemetry
|   |   |-- dashboard_bridge.py          [W17] Streamlit data feed
|   |   -- tests/                       [W17]
|   |
|   |-- agents/                          [W5/W9/W13] Agent implementations
|   |   |-- debate/                      [W9] 5 debate agents
|   |   |-- scanner/                     [W5] Equity, options, arbitrage scanners
|   |   |-- strategy/                    [W13] StrategyGeneratorAI, StrategyEvolver
|   |   |-- meta/                        [W8] MetaStrategyController, RegimePredictor
|   |   -- tests/                       [W13]
|   |
|   |-- simulation/                      [W8] Risk: Monte Carlo + Scenarios
|   |   |-- monte_carlo/                 [W8] 14-scenario Monte Carlo
|   |   |-- market_simulation/           [W8] Order fill and slippage
|   |   |-- scenario_engine/             [W8] Scenario runner
|   |   -- tests/                       [W8]
|   |
|   -- replay/                          [W14] Research: Historical Replay
|       |-- replay_engine.py             [W14] ReplayEngine
|       |-- replay_feed.py               [W14] Implements BaseFeed
|       -- tests/                       [W14]
|
|-- interfaces/                          [W16/W17] External interfaces
|   |-- dashboard/                       [W17] Streamlit app and pages
|   |-- telegram/                        [W16] TelegramBot, 13 commands
|   -- reporting/                       [W16] EOD and performance reports
|
|-- infrastructure/                      [W2] Non-Python infrastructure artifacts
|   |-- database/schema/                 [W2] SQL migration files (v001, v002, ...)
|   |-- logging/                         [W2] logging_config.yaml
|   |-- security/                        [W2] CVE policy, env template
|   -- deployment/                      [W2] Dockerfile, entrypoint.sh, health check
|
|-- tests/                               [W1+] Test suite root
|   |-- unit/                            [all waves] Mirrors iios/ structure
|   |-- integration/                     [W10+] Pipeline integration tests
|   |-- performance/                     [W14] Latency benchmarks
|   |-- security/                        [W12] Security-focused tests
|   |-- replay_tests/                    [W14] Replay-based regression tests
|   |-- fixtures/                        [W1+] Shared test fixtures
|   |-- conftest.py                      [W1] Root pytest configuration
|   -- pytest.ini                       [W1] pytest settings
|
|-- docs/                                [all waves] Engineering documentation
|   |-- architecture/                    [W1+] Architecture docs and diagrams
|   |-- decisions/                       [all] Engineering Decision Records
|   |-- waves/                           [all] Wave specifications and WCRs
|   |-- certification/                   [W10+] Certification records
|   |-- runbooks/                        [W17] Operational runbooks
|   -- api/                             [W20] Auto-generated API docs
|
|-- tools/                               [W2+] Repository management tools
|   |-- import_graph_analyzer.py         [W2] Enforces layer boundaries
|   |-- manifest_validator.py            [W2] Validates __manifest__.json files
|   |-- module_auditor.py                [W2] Checks module size, docstrings
|   |-- interface_comparator.py          [W5] Checks interface sig changes
|   |-- coverage_gate.py                 [W8] Enforces coverage minimums
|   -- benchmark_runner.py              [W14] Runs performance benchmarks
|
|-- scripts/                             [all] Operational scripts
|   |-- autostart.bat                    Windows Task Scheduler entry point
|   |-- setup_windows_task.py            Registers 08:00 weekday task
|   -- (other operational scripts)
|
|-- experimental/                        [all] Non-production experiments
|   -- (all experimental modules tagged # EXPERIMENTAL)
|
|-- _deprecated/                         [all] Retired but retained modules
|   -- (all deprecated modules tagged # DEPRECATED)
|
|-- data/                                [runtime] PERSISTENT — not in git
|   |-- iios.db                          Main SQLite database
|   |-- paper_trades.csv                 Paper trading journal
|   |-- historical/                      Historical market data cache
|   |-- replay/                          Replay engine data store
|   -- (all operational state)
|
|-- config.py                            [W1] ALL trading behavior constants
|-- main.py                              [W1] System entry point
|-- requirements.txt                     [W1] Pinned dependencies
|-- Dockerfile                           [W1] Container definition
|-- docker-compose.yml                   [W1] Service orchestration
|-- build_manifest.json                  [W1] Machine-readable component registry
|-- ARCHITECTURE.md                      [W1] System architecture specification
|-- CHANGELOG.md                         [W1] Version history
|-- README.md                            [W1] Repository overview
|-- .env.example                         [W1] Environment variable template
|-- .gitignore                           [W1] Excludes data/, .venv/, .env
-- .github/                             [W1] CI/CD workflows
    -- workflows/
        |-- ci.yml                       Full CI pipeline
        -- deploy.yml                   VPS deployment pipeline
`

---

# APPENDIX B — PACKAGE CATALOG

Complete catalog of all IIOS Python packages. Sorted by wave, then by package name.

| Package | Wave | Layer | Classification | Owner | Cert Target |
|---------|------|-------|----------------|-------|-------------|
| iios.core | W1 | 0 | CRITICAL | Platform | Level 4 |
| iios.infrastructure | W2 | 0 | CRITICAL | Platform | Level 4 |
| iios.intelligence | W2/W8 | 1-2 | CORE | Intelligence | Level 4 |
| iios.knowledge | W3/W4 | 3-4 | CORE | Knowledge | Level 3 |
| iios.observation | W5 | 4-5 | CORE | Intelligence | Level 3 |
| iios.agents.scanner | W5 | 4-5 | CORE | Intelligence | Level 3 |
| iios.strategy.base | W5 | 5 | CORE | Strategy | Level 3 |
| iios.relationship | W6 | 6 | CORE | Knowledge | Level 3 |
| iios.risk.capital | W6 | 6 | CORE | Risk | Level 4 |
| iios.events | W7 | 7 | CORE | Platform | Level 3 |
| iios.risk.portfolio | W7 | 7 | CORE | Risk | Level 4 |
| iios.reasoning | W8/W9 | 3 | CORE | Intelligence | Level 3 |
| iios.simulation | W8 | 8 | CORE | Risk | Level 3 |
| iios.agents.meta | W8 | 3 | CORE | Intelligence | Level 3 |
| iios.decision | W9 | 10 | CRITICAL | Decision | Level 4 |
| iios.agents.debate | W9 | 10 | CRITICAL | Decision | Level 4 |
| iios.execution | W11 | 11 | CRITICAL | Execution | Level 4 |
| iios.risk.stress | W11 | 9 | CRITICAL | Risk | Level 4 |
| iios.risk.guardian | W11 | 9 | CRITICAL | Council | Level 4 |
| iios.strategy.generators | W13 | 5 | CORE | Strategy | Level 3 |
| iios.strategy.backtesting | W13 | 5 | CORE (PROTECTED) | Council | Level 4 |
| iios.research.research_lab | W13 | 15 | CORE | Research | Level 3 |
| iios.learning | W14 | 13-14 | CORE | Learning | Level 3 |
| iios.replay | W14 | N/A | CORE | Research | Level 3 |
| iios.monitoring | W15 | 12 | CORE | Execution | Level 3 |
| iios.research.validation_engine | W16 | 16 | CORE (PROTECTED) | Council | Level 4 |
| interfaces.telegram | W16 | N/A | CORE | Platform | Level 4 |
| interfaces.reporting | W16 | N/A | OPTIONAL | Platform | Level 3 |
| iios.control | W17 | 17 | CORE | Platform | Level 4 |
| interfaces.dashboard | W17 | N/A | CORE | Platform | Level 3 |

---

# APPENDIX C — DEPENDENCY MATRIX

Which packages depend on which. A checkmark indicates the row package
imports from the column package.

`
DEPENDENCY MATRIX (simplified — only direct dependencies shown)

                  core  infra  intel  know  obs   rel   event  reas  strat  dec   risk  exec  mon   learn  res   ctrl
core              --    --     --     --    --    --    --     --    --     --    --    --    --    --     --    --
infrastructure    Y     --     --     --    --    --    --     --    --     --    --    --    --    --     --    --
intelligence      Y     Y      --     Y     --    --    --     --    --     --    --    --    --    --     --    --
knowledge         Y     Y      --     --    --    --    --     --    --     --    --    --    --    --     --    --
observation       Y     Y      Y      Y     --    --    --     --    --     --    --    --    --    --     --    --
relationship      Y     Y      --     Y     Y     --    --     --    --     --    --    --    --    --     --    --
events            Y     Y      --     --    --    --    --     --    --     --    --    --    --    --     --    --
reasoning         Y     Y      Y      Y     --    --    Y      --    --     --    --    --    --    --     --    --
strategy          Y     Y      --     Y     --    --    --     Y     --     --    --    --    --    --     --    --
decision          Y     Y      Y      Y     --    --    --     Y     Y      --    --    --    --    --     --    --
risk              Y     Y      --     --    --    --    --     --    --     Y     --    --    --    --     --    --
execution         Y     Y      --     --    --    --    --     --    --     Y     Y     --    --    --     --    --
monitoring        Y     Y      --     --    --    --    --     --    --     --    --    Y     --    --     --    --
learning          Y     Y      --     --    --    --    --     --    Y      --    --    --    Y     --     --    --
research          Y     Y      --     --    --    --    --     --    Y      --    --    --    --    Y      --    --
control           Y     Y      Y      Y     --    --    --     --    --     --    Y     --    Y     Y      --    --
`

**Import Direction Rule:**
Rows depend on columns. No column package may depend on a row package
that appears later in the hierarchy. The matrix is strictly lower-triangular.

---

# APPENDIX D — OWNERSHIP MATRIX

Maps each package cluster to its owning team and protected module owner.

| Component | Primary Owner | Secondary Review | Protected By |
|-----------|-------------|------------------|--------------|
| iios.core | Platform Team | Architecture Council | — |
| iios.infrastructure | Platform Team | Security Officer | Architecture Council (dhan_feed.py) |
| iios.intelligence | Intelligence Team | Platform Team | — |
| iios.knowledge | Knowledge Team | Intelligence Team | — |
| iios.observation | Intelligence Team | Strategy Team | — |
| iios.strategy.base | Strategy Team | Architecture Council | — |
| iios.strategy.backtesting | Strategy Team | Architecture Council | Architecture Council |
| iios.strategy.evolved_strategies | Strategy Team | Architecture Council | Architecture Council |
| iios.decision | Decision Team | Architecture Council | — |
| iios.risk.capital | Risk Team | Architecture Council | — |
| iios.risk.portfolio | Risk Team | Architecture Council | — |
| iios.risk.guardian | Risk Team | Architecture Council | Architecture Council |
| iios.execution | Execution Team | Risk Team | — |
| iios.monitoring | Execution Team | Learning Team | — |
| iios.learning | Learning Team | Research Team | — |
| iios.research.validation_engine | Research Team | Architecture Council | Architecture Council |
| iios.control | Platform Team | All Teams | — |
| interfaces.telegram | Platform Team | Security Officer | — |
| data/ directory | Platform Team | Architecture Council | Architecture Council |

---

# APPENDIX E — CONSTRUCTION WORKFLOW

Step-by-step construction process for implementing any IIOS wave.

**Wave Construction Workflow:**

`
Step 1: WAVE START AUTHORIZATION
  - Architecture Council votes to start wave N.
  - Wave N-1 Wave Completion Record is filed.
  - Wave N specification is reviewed and accepted.

Step 2: FOLDER CREATION (Phase 2 of lifecycle)
  - Create all package directories for Wave N.
  - Initialize __init__.py, __manifest__.json, README.md, tests/conftest.py.
  - Commit: [WN] Scaffold: all Wave N package structures.

Step 3: PACKAGE REGISTRATION (Phase 3)
  - Fill in __manifest__.json for each package.
  - Run tools/manifest_validator.py.
  - Register in build_manifest.json.
  - Commit: [WN] Register: {packages} in module registry.

Step 4: MODULE STUBS (Phase 4)
  - Create module files with docstring headers (no implementation).
  - Create corresponding test files with failing test stubs.
  - Commit: [WN] Stub: all Wave N module files.

Step 5: TEST-DRIVEN IMPLEMENTATION
  For each module in Wave N:
    5a. Write test (red — failing test).
    5b. Write implementation (green — test passes).
    5c. Refactor if necessary.
    5d. Verify coverage >= 95% for module.
    5e. Commit: [WN] Implement: {module_name}.

Step 6: INTEGRATION TESTING
  - Write integration tests that verify cross-module behavior.
  - Run full test suite. All tests must pass.
  - Run import graph analyzer. Zero violations.
  - Commit: [WN] Test: integration tests for Wave N.

Step 7: DEPENDENCY VALIDATION (Phase 5)
  - Run tools/import_graph_analyzer.py.
  - Run tools/manifest_validator.py.
  - Run tools/interface_comparator.py.
  - Generate Dependency Validation Report.

Step 8: PERFORMANCE VALIDATION (for waves with latency-sensitive components)
  - Run tools/benchmark_runner.py.
  - Verify all latency targets met.
  - Record results in docs/performance/.

Step 9: WAVE COMPLETION REVIEW
  - Architecture Council reviews: CI/CD report, coverage, dependency report.
  - Architecture Council votes: CERTIFY or REJECT.
  - If CERTIFY: issue certification records. Tag version.
  - If REJECT: engineers address findings. Repeat from Step 6.

Step 10: WAVE COMPLETION RECORD
  - File Wave N WCR in docs/waves/wave-NN/completion_record.md.
  - Update build_manifest.json with certified package versions.
  - Merge feature branch to main.
  - Deploy to VPS. Verify HEALTHY.
  - Announce wave complete.
`

---

# APPENDIX F — REPOSITORY ANTI-PATTERNS

Anti-patterns are structural or organizational patterns that appear initially
reasonable but consistently lead to failures. These are patterns observed
across trading system codebases and are explicitly prohibited in IIOS.

**Anti-Pattern AF-01: The Monolithic Config God Object**
*Pattern:* All configuration is in a single massive class with hundreds of
attributes, accessed as Config.get('key') with string lookup.
*Problem:* Type safety lost. Typos in key names cause silent failures.
Import-time errors are delayed to runtime.
*IIOS Rule:* config.py has named constants. Direct imports: rom config import X.

**Anti-Pattern AF-02: The Circular Service Dependency**
*Pattern:* Service A is injected into Service B at initialization, and Service B
is also injected into Service A.
*Problem:* Initialization order becomes undefined. Breaks singleton patterns.
*IIOS Rule:* EventBus is used for cross-layer communication. No circular injection.

**Anti-Pattern AF-03: The Strategy Hard-Code**
*Pattern:* Trading strategy parameters (stop loss %, target %, position size)
are hardcoded in individual strategy files.
*Problem:* Cannot be tuned without code changes. Hidden parameters spread across files.
*IIOS Rule:* All strategy parameters are in the strategy's data class or in config.py.

**Anti-Pattern AF-04: The Omniscient Orchestrator**
*Pattern:* A single class coordinates every step of a complex pipeline by
knowing all steps and calling them directly.
*Problem:* The orchestrator becomes a bottleneck. Any new step requires orchestrator modification.
*IIOS Rule:* MasterOrchestrator exists but uses the event bus and layer contracts.
Adding a new layer does not require changing MasterOrchestrator's core logic.

**Anti-Pattern AF-05: The Floating Constant**
*Pattern:* A critical threshold value (e.g., kill switch VIX level) is defined
in multiple places: config.py, the risk class, and the test file.
*Problem:* Constants drift. The test might test 40.0 while production uses 45.0.
*IIOS Rule:* All constants defined once in config.py. Tests import from config.

**Anti-Pattern AF-06: The Silent Singleton**
*Pattern:* A singleton is instantiated directly (isk_guardian = RiskGuardian())
in multiple files, with Python module caching providing accidental singleton behavior.
*Problem:* The singleton guarantee depends on module caching, which is fragile.
*IIOS Rule:* All singletons are created through documented factory functions.
Direct instantiation is prohibited.

**Anti-Pattern AF-07: The Layer Skip**
*Pattern:* Layer 11 (Execution) imports directly from Layer 15 (ResearchLab)
to check if a strategy has been promoted.
*Problem:* Creates a hidden upward dependency. Breaks architectural isolation.
*IIOS Rule:* Strategy promotion status is reflected downward through registry state.
Execution checks the registry, which is a Layer 5 artifact.

**Anti-Pattern AF-08: The Shared Mutable Global**
*Pattern:* A module-level dictionary (state = {}) is imported and mutated
by multiple modules across packages.
*Problem:* Concurrency issues. Hidden coupling. Impossible to test in isolation.
*IIOS Rule:* All shared state is encapsulated in a class with controlled access.

**Anti-Pattern AF-09: The Over-Mocked Test**
*Pattern:* Unit tests mock every dependency, including dependencies of the
dependency under test. Tests pass but cover only mock configuration, not actual behavior.
*Problem:* Tests give false confidence. Regressions are not caught.
*IIOS Rule:* Mocks are allowed for external I/O (database, API calls).
Internal business logic is tested with real implementations.

**Anti-Pattern AF-10: The Pre-Emptive Abstraction**
*Pattern:* An abstract base class with 20 methods is created for a concept
that currently has only one implementation.
*Problem:* The interface is designed for imaginary future implementations.
It constrains the real implementation unnecessarily.
*IIOS Rule:* Abstractions are created when a second implementation is needed.
BaseFeed exists because DhanFeed and YahooFeed are both real implementations.

---

# APPENDIX G — OPERATIONAL RUNBOOK

Day-to-day repository management procedures.

**RB-001 — Daily Health Check Procedure:**
`
1. Run: docker compose ps
   Expected: both containers Up ... (healthy)
2. Check: docker logs ai-trading-brain --tail=50
   Expected: No ERROR lines. Daily start banner present.
3. Check: data/paper_trades.csv
   Expected: File exists. New trades appended if market was open.
4. Check Telegram: /health
   Expected: System response with all layers green.
5. If any check fails: run RB-005 (Restart Procedure).
`

**RB-002 — Database Restore Procedure:**
`
1. Stop containers: docker compose down
2. Identify backup: ls data/backups/iios.db.*
3. Restore: cp data/backups/iios.db.{date} data/iios.db
4. Verify integrity: sqlite3 data/iios.db "PRAGMA integrity_check;"
5. Restart: docker compose up -d
6. Verify: docker compose ps (both HEALTHY)
7. Document: log the restore event in docs/certification/incidents.md
`

**RB-003 — Kill Switch Manual Reset:**
`
1. Verify kill switch was triggered for legitimate reason.
   Check: docker logs ai-trading-brain | grep KILL_SWITCH
2. Verify the triggering condition has resolved.
   (VIX below 45.0, daily loss below 2.0%)
3. Reset via Telegram: /resume (if bot is running)
   OR via code: set KILL_SWITCH_ACTIVE=False in operational state.
4. Monitor for 15 minutes before allowing new orders.
5. Document: log the manual reset with reason in incidents.md
`

**RB-004 — Feed Failover Procedure:**
`
1. Detect: Dhan API returning 451 or connection refused.
   Check: docker logs | grep "DhanFeed" | grep "ERROR"
2. Verify: yfinance fallback is active.
   Check: docker logs | grep "YahooFeed" | grep "active"
3. If fallback NOT active: restart containers (RB-005).
4. Notify: send Telegram message /diag to confirm fallback status.
5. Document: log Dhan outage duration in incidents.md
6. Resolution: when Dhan API recovers, it is automatically reactivated
   on the next feed manager health check cycle.
`

**RB-005 — Restart Procedure:**
`
1. Save state: ensure data/iios.db is not being written (check disk I/O).
2. Stop: docker compose down
3. Pull latest: git pull origin main
4. Rebuild: docker compose build --no-cache
5. Start: docker compose up -d
6. Wait 8 seconds: sleep 8
7. Verify: docker compose ps (both HEALTHY)
8. If NOT healthy: docker logs ai-trading-brain > logs/restart-{datetime}.txt
9. Diagnose from logs.
10. Escalate if not resolved in 15 minutes.
`

---

# APPENDIX H — GLOSSARY

**Agent:** An AI component that takes a signal or opportunity as input and
produces a scored output. Agents are specialized; each has one domain of expertise.

**Architecture Council:** The governance body responsible for IIOS architectural decisions.
Composed of: Lead Architect, Senior Platform Engineer, Senior Risk Engineer.

**BaseFeed:** The abstract interface (iios.core.interfaces.base_feed) that
all market data sources must implement.

**build_manifest.json:** The authoritative machine-readable registry of all packages
and modules in the repository, including their certification levels.

**CERTIFIED (Level 3):** The certification level at which a package has >= 95%
test coverage, all quality gates pass, and has been peer reviewed.

**config.py:** The single source of truth for all trading behavior constants.
No constant in config.py may be duplicated in any other file.

**ControlTower:** Layer 17. SQLite telemetry, Streamlit dashboard, EventBus monitoring.

**DECISION_THRESHOLD:** The composite score threshold (6.5) above which a trade
is approved by the DecisionEngine. Sourced from config.py.

**DebateOrchestrator:** The component that runs the five-agent debate for each opportunity.
Requires exactly five agents registered.

**Domain Owner:** The person responsible for the quality and evolution of a package cluster.

**EDR (Engineering Decision Record):** A document written when a breaking change
is made to a public interface or a deviation from the specification is authorized.

**EventBus:** The system-wide publish/subscribe message broker. Used for cross-layer
communication to avoid upward dependencies.

**evolved_strategies/:** The directory containing strategy variants that have
been produced through the evolutionary pipeline. These are PROTECTED modules.

**factory function:** A module-level function (e.g., get_feed_manager()) that
provides access to a singleton. Direct class instantiation of singletons is prohibited.

**GlobalDataAI:** The component in Layer 1 that fetches overnight global market context.
Cache: 5-minute TTL with background pre-warm. Latency target: <= 17ms (cached).

**IIOS:** Investment Intelligence Operating System. The name of the system
defined by this specification.

**import graph:** The directed graph of all import relationships in the IIOS codebase.
Used by 	ools/import_graph_analyzer.py to enforce layer boundaries.

**KILL_SWITCH_DAILY_LOSS_PCT:** 2.0% daily portfolio loss threshold. From config.py.

**KILL_SWITCH_VIX:** VIX index level 45.0. From config.py. Triggers RiskGuardian kill switch.

**Layer:** One of 17 architectural layers in IIOS, numbered 1-17. Each layer
represents a discrete functional domain in the trading pipeline.

**manifest_validator.py:** The tool that validates __manifest__.json files against
the official schema, checks declared dependencies, and verifies layer consistency.

**MasterOrchestrator:** The top-level orchestrator that sequences all 17 layers
through each trading cycle. Entry via un_full_cycle().

**module:** A single .py file within a package.

**namespace package:** A Python package structure that allows splitting into
multiple distribution packages while sharing a common prefix (iios.).

**PAPER_TRADING mode:** Trading mode where OrderManager simulates trades
without sending real orders to the broker. Journal written to data/paper_trades.csv.

**plugin:** An optional, self-contained component that extends IIOS functionality
without modifying core packages. Loaded by the PluginRegistry.

**PRODUCTION-READY (Level 4):** The certification level required for components
on the live trading critical path. Requires passing Architecture Council vote.

**PromotionGate:** The component that enforces the three-criteria promotion rule:
WinRate >= 50%, Sharpe > 0.8, MaxDD < 15% (all from config.py).

**protected module:** A module that may not be modified without explicit Architecture
Council instruction.

**RiskGuardian:** The kill-switch component in Layer 9. PROTECTED.
Monitors VIX and daily loss; publishes KILL_SWITCH_TRIGGERED when thresholds exceeded.

**singleton:** A class of which exactly one instance exists in the entire system.
Accessed via a factory function.

**SYSTEM_CERTIFIED:** The state in which all Level 4 certification checks pass
and the system is authorized for production trading.

**ValidationEngine:** The 6-stage validation pipeline in Layer 16. PROTECTED.
Stages: Backtest, Walk-Forward, Cross-Market, Monte Carlo, Sensitivity, Regime.

**Wave:** A discrete phase of IIOS development with defined deliverables.
Waves 1-20 are defined in IMPLEMENTATION_MASTER_PLAN.md.

**Wave Completion Record (WCR):** A document filed after each wave completes.
Records: what was built, what was deferred, what was learned.

**WFT (Walk-Forward Testing):** Testing strategy performance on data not seen during
parameter optimization. Implemented in WalkForwardTester (PROTECTED via BacktestingAI).

---

# DOCUMENT METRICS

| Metric | Value |
|--------|-------|
| Document Code | IIOS-RCS-001 |
| Version | 1.0 |
| Status | FINAL |
| Total Parts | X (10 Parts) |
| Total Appendices | 8 (A-H) |
| Repository Rules (RS) | 10 |
| Package Organization Rules (PO) | 10 |
| Dependency Management Rules (DM) | 10 |
| Modularity Rules (MD) | 10 |
| Maintainability Rules (MA) | 10 |
| Documentation Rules (DC) | 10 |
| Governance Rules (GV) | 10 |
| Security Rules (SC) | 10 |
| Performance Rules (PE) | 10 |
| Future Evolution Rules (FE) | 10 |
| Total Constitution Rules | 100 |
| Certification Matrices | 10 |
| Anti-Patterns Documented | 10 |
| Packages Catalogued | 30 |
| Architecture Layers Covered | 17 |

---

# AMENDMENT HISTORY

| Amendment | Date | Description | Authority |
|-----------|------|-------------|-----------|
| Initial Release | 2026 | First complete specification | Architecture Council |
| (future amendments here) | — | — | Architecture Council |

---

# CLOSING STATEMENT

This Core Repository Construction Specification defines with complete precision
how the Investment Intelligence Operating System will be physically constructed.
It is the bridge between the architecture vision expressed in ARCHITECTURE.md
and the actual Python implementation realized through the 20-wave development plan.

Every folder, every package, every module, every boundary, every governance
rule, and every quality standard exists for a deliberate reason. This document
provides those reasons and the rules that implement them.

Engineers building IIOS are expected to know this document. Architecture Council
members enforce it. All deviations require Engineering Decision Records.

The repository is not an accident of accumulated code. It is the physical
embodiment of a design intent. This specification is that design intent.

**IIOS-RCS-001 — END OF DOCUMENT**
