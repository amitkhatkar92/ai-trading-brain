# PHYSICAL REPOSITORY STRUCTURE
## Investment Intelligence Operating System (IIOS)

**Document Code:** IIOS-PHYS-REPO-001
**Version:** 1.0.0
**Status:** AUTHORITATIVE
**Classification:** Engineering Foundation
**Issued:** 2026-07-04
**Maintained By:** Architecture Council
**Companion To:** IIOS-REPO-ENG-001 (Repository Engineering Specification)

---

> **SCOPE STATEMENT**
>
> This document converts the repository engineering specification (IIOS-REPO-ENG-001)
> into a concrete physical directory organization. It defines the exact folder
> hierarchy, file placement rules, content expectations, lifecycle policies, and
> growth strategies for every artifact in the IIOS repository.
>
> This is not software architecture. This is the physical blueprint of the repository:
> where every directory lives, what it contains, who owns it, and how it grows.
>
> The structure defined here is designed to remain valid — without reorganization —
> across a 20-year operational life, hundreds of engines, thousands of Python modules,
> and multiple deployment models.

---

## TABLE OF CONTENTS

- [Part I — Physical Repository Philosophy](#part-i)
- [Part II — Complete Repository Tree](#part-ii)
- [Part III — Engine Directory Standards](#part-iii)
- [Part IV — Core Library Structure](#part-iv)
- [Part V — Documentation Organization](#part-v)
- [Part VI — Configuration Organization](#part-vi)
- [Part VII — Testing Organization](#part-vii)
- [Part VIII — Repository Growth Strategy](#part-viii)
- [Part IX — Repository Constitution](#part-ix)
- [Part X — Repository Certification](#part-x)
- [Supplement A — Complete Repository Tree](#supplement-a)
- [Supplement B — Directory Catalog](#supplement-b)
- [Supplement C — Naming Examples](#supplement-c)
- [Supplement D — Growth Examples](#supplement-d)
- [Supplement E — Anti-Patterns](#supplement-e)
- [Supplement F — Repository Glossary](#supplement-f)

---

## PART I — PHYSICAL REPOSITORY PHILOSOPHY

### 1.1 Physical Organization vs. Logical Architecture

The logical architecture of IIOS describes what the system does and how its
components relate conceptually: 17 processing layers, 62 agents, 18 engines,
an event bus, a governance framework. The logical architecture lives in
docs/architecture/ — in diagrams and specifications.

The physical organization describes where things live on disk: which directory
contains which file, how directories nest, what belongs beside what. The physical
organization is what every developer interacts with every working day.

The distinction matters because the same logical architecture can be implemented
with vastly different physical organizations, and the physical organization
profoundly affects developer productivity, system maintainability, and the ability
of the repository to scale over time.

A poorly organized physical structure can undermine a sound logical architecture:
engines that should be independent become entangled because their source files
are mixed in a shared directory; domain knowledge becomes diffuse because documentation
is scattered; configuration becomes fragile because constants are buried in source
files across the repository. The physical structure is the enforcement mechanism
for the logical architecture.

---

### 1.2 Why Directory Structure Affects Maintainability

**Discovery time:** A developer who needs to find the Kill Switch logic in the Risk
Guardian should find it in 30 seconds, not 30 minutes. A physical structure that
co-locates related things and separates unrelated things is the mechanism.

**Change impact assessment:** When a developer modifies a component, the directory
structure tells them immediately what else might be affected. Source in engines/?
Affects that engine. Source in shared/? Could affect every engine. Source in
core/? Could affect the entire system. The directory reveals the impact radius.

**Onboarding acceleration:** A new developer who understands the directory structure
understands the system organization. The physical structure is a navigational aid
that works even before the developer has read a single line of documentation.

**Cognitive load reduction:** A consistent, well-defined structure means developers
never have to wonder where something belongs. The answer is always derivable from
the structure's rules. This eliminates the low-level decision-making that consumes
mental energy in disorganized repositories.

**Mechanical enforcement:** Directory-level rules are enforceable by CI tools without
requiring developers to reason about intent. "No Python source in docs/" is a
mechanical check. "Don't mix business logic with infrastructure" requires judgment.
Physical structure converts judgment calls into mechanical rules where possible.

---

### 1.3 Principles of Physical Separation

**Principle 1 — Colocation of Cohesion:** Things that change together live together.
An engine's source, its tests, its documentation, and its configuration are not
spread across the repository — they are co-located under the engine's package
directory (or in directly corresponding mirror directories under 	ests/ and docs/).

**Principle 2 — Separation of Concerns:** Things that serve different purposes
live separately, even if they are closely related in content. Source code lives in
engines/. Tests for that source live in 	ests/. Documentation for that source
lives in docs/ (for formal architecture documents) or in README.md files
adjacent to the source.

**Principle 3 — Hierarchy of Stability:** The most stable artifacts live deepest
in the hierarchy. core/ changes rarely and is the most referenced. It is given
its own top-level directory and protected governance rules. Individual agent
implementations change frequently and live in sub-packages deep inside their
engine's directory.

**Principle 4 — Physical Isolation of Risk:** High-risk artifacts (production
secrets, live database files, executable deployment scripts) are physically
separated from low-risk artifacts (documentation, test fixtures, example code).
The separation makes it harder to accidentally deploy the wrong thing.

**Principle 5 — One Canonical Home:** Every artifact has exactly one canonical
location. There is no valid reason to have the same content in two places. If two
directories need the same content, one directory contains it and the other contains
a reference (link, import, or documented pointer).

**Principle 6 — Predictable Mirroring:** The tests/ directory mirrors the source
directory structure. The docs/architecture/ directory mirrors the engine hierarchy.
The deployment/environments/ directory mirrors the operational environments. Mirroring
makes the repository navigable without a map.

---

### 1.4 Future Scalability

The physical structure defined in this document is designed to accommodate the
following growth without reorganization:

**Engine growth:** The engines/ directory is flat — all engine packages are
siblings. A repository with 100 engine packages has exactly the same engines/
structure as a repository with 18. The only change is more subdirectories.

**Module growth:** Each engine's internal structure uses subdirectories to organize
modules by function (components, models, utils, adapters). Growth within an engine
adds files to these subdirectories without changing the engine's external interface
or the top-level repository structure.

**Documentation growth:** Documentation directories are organized by type and domain,
not by creation date or volume. A docs/architecture/ directory with 100 documents
is navigated the same way as one with 10.

**Team growth:** The ownership model (CODEOWNERS) scales from 1 to 100 developers.
Each engine has a designated owner; the Architecture Council owns cross-cutting
artifacts. Adding a new developer means assigning them to engine ownership.

**Deployment model growth:** The deployment/ directory accommodates new deployment
models (Kubernetes, service mesh, multi-region) by adding new subdirectories. Existing
Docker-based deployment is unchanged.

---

*End of Part I*

---

## PART II — COMPLETE REPOSITORY TREE

### 2.1 Top-Level Overview

The IIOS repository root structure:

`
ai_trading_brain/                    # Repository root
|
|-- main.py                          # Single system entry point
|-- config.py                        # Global configuration module
|-- requirements.txt                 # Pinned production dependencies
|-- requirements-dev.txt             # Pinned development dependencies
|-- requirements.in                  # High-level dep source (pip-compile)
|-- pyproject.toml                   # Python project metadata + tool config
|-- docker-compose.yml               # Service definitions (dev + prod)
|-- Dockerfile                       # Container build definition
|-- README.md                        # Project overview and quick-start
|-- ARCHITECTURE.md                  # Architecture overview with links
|-- CHANGELOG.md                     # Version history
|-- LICENSE                          # Software license
|-- .gitignore                       # VCS exclusion patterns
|-- .env.example                     # Environment variable documentation
|-- .pre-commit-config.yaml          # Pre-commit hook definitions
|-- .gitattributes                   # Line ending enforcement
|-- .secrets.baseline                # detect-secrets baseline
|-- mkdocs.yml                       # Documentation site config (optional)
|
|-- docs/                            # All documentation
|-- engines/                         # All engine packages
|-- core/                            # Infrastructure and framework
|-- domain/                          # Domain type definitions
|-- shared/                          # Cross-engine utilities
|-- config/                          # Configuration definitions
|-- resources/                       # Static runtime assets
|-- data/                            # Runtime data (gitignored)
|-- datasets/                        # Training and reference datasets
|-- cache/                           # Application caches (gitignored)
|-- logs/                            # Runtime logs (gitignored)
|-- monitoring/                      # Observability definitions
|-- deployment/                      # Deployment artifacts
|-- docker/                          # Docker-specific files
|-- scripts/                         # Operational scripts
|-- tools/                           # Development tools
|-- research/                        # Academic and quantitative research
|-- experiments/                     # Exploratory work
|-- examples/                        # Runnable examples
|-- benchmarks/                      # Performance benchmarks
|-- tests/                           # All test code
|-- archive/                         # Inactive/superseded artifacts
|-- .github/                         # GitHub configuration
|-- .venv/                           # Python virtual environment (gitignored)
`

---

### 2.2 docs/ — Documentation Directory

**Purpose:** The canonical home for all non-code documentation. Every document
that describes, explains, or governs IIOS lives here.

**Complete tree:**
`
docs/
|-- README.md                        # Documentation index
|
|-- architecture/                    # Architecture documents
|   |-- README.md
|   |-- IIOS_MASTER_ARCHITECTURE.md
|   |-- IIOS_INTEGRATION_AND_OPERATIONAL_ARCHITECTURE.md
|   |-- IIOS_MASTER_ORCHESTRATOR_ARCHITECTURE.md
|   |-- engines/                     # Per-engine architecture docs
|   |   |-- README.md
|   |   |-- IIOS_RISK_ENGINE_ARCH.md
|   |   |-- IIOS_KNOWLEDGE_ENGINE_ARCH.md
|   |   |-- [one doc per engine]
|   |-- ontologies/                  # Ontology architecture docs
|   |   |-- IIOS_ENTITY_ONTOLOGY.md
|   |   |-- IIOS_EVENT_ONTOLOGY.md
|   |   |-- [one doc per ontology]
|   |-- workflows/                   # Workflow architecture docs
|   |   |-- IIOS_WORKFLOW_CATALOGUE.md
|   |   |-- [per-workflow docs]
|   |-- layers/                      # Layer-by-layer architecture docs
|
|-- engineering/                     # Engineering specifications
|   |-- README.md
|   |-- REPOSITORY_ENGINEERING.md
|   |-- PHYSICAL_REPOSITORY_STRUCTURE.md
|   |-- IIOS_CODE_STANDARDS.md       # (future)
|   |-- IIOS_TEST_STANDARDS.md       # (future)
|   |-- IIOS_SECURITY_STANDARDS.md   # (future)
|   |-- IIOS_DEPLOYMENT_STANDARDS.md # (future)
|
|-- decisions/                       # Architecture Decision Records
|   |-- README.md                    # ADR index
|   |-- ADR-001-engine-isolation.md
|   |-- ADR-002-event-bus.md
|   |-- ADR-003-domain-types.md
|   |-- ADR-004-paper-trading.md
|   |-- ADR-005-dhan-fallback.md
|   |-- [sequential ADRs]
|
|-- operations/                      # Operational runbooks
|   |-- README.md
|   |-- RB-DEPLOY-001-vps-deployment.md
|   |-- RB-OPS-001-startup-procedure.md
|   |-- RB-OPS-002-shutdown-procedure.md
|   |-- RB-OPS-003-emergency-stop.md
|   |-- RB-OPS-004-recovery-procedure.md
|   |-- RB-OPS-005-kill-switch-response.md
|   |-- RB-MAINT-001-daily-checks.md
|   |-- RB-MAINT-002-weekly-maintenance.md
|   |-- RB-MAINT-003-monthly-review.md
|   |-- RB-MAINT-004-quarterly-audit.md
|
|-- standards/                       # Engineering standards reference
|   |-- README.md
|   |-- naming_conventions.md
|   |-- code_style_reference.md
|   |-- documentation_standards.md
|   |-- testing_standards.md
|   |-- security_standards.md
|
|-- migrations/                      # Schema and API migration guides
|   |-- README.md
|   |-- [MIGRATION-VERSION-description.md]
|
|-- tutorials/                       # Step-by-step tutorials
|   |-- README.md
|   |-- getting_started.md
|   |-- adding_a_new_engine.md
|   |-- adding_a_new_strategy.md
|   |-- configuring_paper_trading.md
|   |-- interpreting_pnl_reports.md
|
|-- developer_guides/                # Developer reference guides
|   |-- README.md
|   |-- local_development_setup.md
|   |-- writing_engine_tests.md
|   |-- debugging_the_decision_cycle.md
|   |-- working_with_the_event_bus.md
|   |-- extending_the_knowledge_graph.md
|
|-- user_guides/                     # Operator guides
|   |-- README.md
|   |-- telegram_bot_commands.md
|   |-- reading_the_dashboard.md
|   |-- understanding_risk_reports.md
|   |-- configuring_alerts.md
|
|-- reference/                       # Reference manuals
|   |-- README.md
|   |-- engine_api_reference.md
|   |-- configuration_reference.md
|   |-- telegram_command_reference.md
|   |-- metric_definitions.md
|
|-- glossaries/                      # Glossaries
|   |-- README.md
|   |-- domain_glossary.md
|   |-- technical_glossary.md
|   |-- market_terms_glossary.md
|
|-- archive/                         # Superseded documents
|   |-- README.md
|   |-- [superseded docs with ARCHIVED.md markers]
`

**Ownership:** Architecture Council
**Allowed files:** .md, .svg, .png, .drawio, .pdf
**Forbidden files:** Python source, configuration files, test files
**Growth policy:** Documents accumulate indefinitely; superseded documents move
to docs/archive/ rather than being deleted.

---

### 2.3 engines/ — Engine Packages Directory

**Purpose:** The primary source directory for all IIOS engine packages.

**Complete tree:**
`
engines/
|-- README.md                        # Engine directory index
|
|-- global_intelligence/             # Stratum 1 — Global context
|-- market_intelligence/             # Stratum 2 — Regime classification
|-- meta_learning/                   # Stratum 3 — Strategy weights
|-- opportunity_engine/              # Stratum 4 — Opportunity scanner
|-- strategy_lab/                    # Stratum 5 — Strategy evolution
|-- capital_risk_engine/             # Stratum 6 — Position sizing
|-- risk_control/                    # Stratum 7 — Portfolio risk
|-- market_simulation/               # Stratum 8 — Monte Carlo
|-- risk_guardian/                   # Stratum 9 — Kill-switch guardian
|-- debate_and_decision/             # Stratum 10 — Decision scoring
|-- execution_engine/                # Stratum 11 — Order routing
|-- trade_monitoring/                # Stratum 12 — Trade monitoring
|-- learning_system/                 # Stratum 13 — Model learning
|-- performance_analytics/           # Stratum 14 — Performance analysis
|-- research_lab/                    # Stratum 15 — Promotion gates
|-- validation_engine/               # Stratum 16 — Strategy validation
|-- control_tower/                   # Stratum 17 — Telemetry + dashboard
|-- orchestrator/                    # Coordination — Master Orchestrator
`

Each engine follows the standard structure defined in Part III.

**Ownership:** Per-engine owners (see CODEOWNERS)
**Allowed contents:** Python packages only — one subdirectory per engine
**Forbidden contents:** Shared utilities, cross-engine imports, test files
**Growth policy:** New engines add new sibling directories; engines never nest

---

### 2.4 core/ — Infrastructure and Framework

**Purpose:** Base frameworks, lifecycle protocols, event bus, health infrastructure,
and all cross-cutting infrastructure that every engine depends on.

**Complete tree:**
`
core/
|-- __init__.py
|-- README.md
|
|-- engine/                          # Base engine framework
|   |-- __init__.py
|   |-- base_engine.py               # Abstract base engine class
|   |-- lifecycle.py                 # Lifecycle protocol definition
|   |-- registry.py                  # Engine registry
|   |-- status.py                    # Engine status types
|   |-- protocol.py                  # Engine protocol (typing)
|
|-- events/                          # Event bus infrastructure
|   |-- __init__.py
|   |-- bus.py                       # Event bus implementation
|   |-- event.py                     # Base event type
|   |-- dispatcher.py                # Event dispatcher
|   |-- subscriber.py                # Subscriber protocol
|   |-- filters.py                   # Event filter utilities
|
|-- health/                          # Health check infrastructure
|   |-- __init__.py
|   |-- health_check.py              # Health check protocol
|   |-- ohs.py                       # Operational Health Score computation
|   |-- status.py                    # Health status types
|   |-- reporter.py                  # Health report builder
|
|-- logging/                         # Logging infrastructure
|   |-- __init__.py
|   |-- logger.py                    # Structured logger factory
|   |-- formatters.py                # Log formatters (JSON, text)
|   |-- handlers.py                  # Log handlers (file, stream)
|   |-- sanitizer.py                 # Log output sanitizer
|   |-- context.py                   # Request/session context for logs
|
|-- errors/                          # Error hierarchy
|   |-- __init__.py
|   |-- base_errors.py               # Base error classes
|   |-- engine_errors.py             # Engine-specific error types
|   |-- data_errors.py               # Data-related error types
|   |-- governance_errors.py         # Governance-related error types
|
|-- messaging/                       # Inter-engine messaging
|   |-- __init__.py
|   |-- router.py                    # Message router
|   |-- serializer.py                # Message serialization
|   |-- envelope.py                  # Message envelope type
|
|-- registry/                        # Engine registry
|   |-- __init__.py
|   |-- engine_registry.py           # Registry implementation
|   |-- capability.py                # Engine capability declaration
|
|-- config/                          # Configuration loading infrastructure
|   |-- __init__.py
|   |-- loader.py                    # Configuration loader
|   |-- validator.py                 # Configuration validator
|   |-- schema.py                    # Configuration schema types
|
|-- tracing/                         # Distributed tracing
|   |-- __init__.py
|   |-- tracer.py                    # Trace context management
|   |-- span.py                      # Span types
|
|-- security/                        # Security utilities
|   |-- __init__.py
|   |-- sanitizer.py                 # Input sanitizer
|   |-- validator.py                 # Security validation utilities
`

**Ownership:** Architecture Council (changes require Architecture Council approval)
**Allowed contents:** Infrastructure code only — no business logic
**Forbidden contents:** Market data, investment logic, engine-specific code
**Growth policy:** Maximum 5 changes per year; every change requires an ADR

---

### 2.5 domain/ — Domain Type Definitions

**Purpose:** Canonical Python representations of all IIOS domain entities,
value objects, enumerations, and constants.

**Complete tree:**
`
domain/
|-- __init__.py
|-- README.md
|
|-- entities/                        # Entity type definitions
|   |-- __init__.py
|   |-- market_entity.py             # Market-facing entity types
|   |-- strategy_entity.py           # Strategy entity types
|   |-- agent_entity.py              # Agent entity types
|   |-- position_entity.py           # Position entity types
|   |-- trade_entity.py              # Trade entity types
|
|-- events/                          # Domain event types
|   |-- __init__.py
|   |-- market_events.py             # Market data events
|   |-- decision_events.py           # Decision lifecycle events
|   |-- risk_events.py               # Risk signal events
|   |-- system_events.py             # System lifecycle events
|   |-- learning_events.py           # Learning events
|
|-- values/                          # Value objects
|   |-- __init__.py
|   |-- price.py                     # Price value objects
|   |-- quantity.py                  # Quantity and volume value objects
|   |-- signal.py                    # Signal value objects
|   |-- score.py                     # Score and rating value objects
|   |-- budget.py                    # Risk budget value objects
|
|-- enumerations/                    # Enumeration types
|   |-- __init__.py
|   |-- regime.py                    # Market regime types
|   |-- order_types.py               # Order type enumerations
|   |-- asset_class.py               # Asset class enumerations
|   |-- engine_status.py             # Engine status enumerations
|   |-- decision_outcome.py          # Decision outcome enumerations
|
|-- constants/                       # Domain constants
|   |-- __init__.py
|   |-- market_hours.py              # Market calendar constants
|   |-- thresholds.py                # System threshold constants
|   |-- symbols.py                   # Canonical symbol definitions
|
|-- protocols/                       # Typing protocols
|   |-- __init__.py
|   |-- observable.py                # Observable protocol
|   |-- serializable.py              # Serializable protocol
|   |-- identifiable.py              # Identifiable protocol
`

**Ownership:** Architecture Council
**Allowed contents:** Data class definitions, enumerations, value objects, constants
**Forbidden contents:** Business logic, database mapping, serialization code
**Growth policy:** Additive only; existing types are versioned, not modified destructively

---

### 2.6 shared/ — Cross-Engine Utilities

**Purpose:** Shared library code used by multiple engines. Pure utilities with
no business logic.

**Complete tree:**
`
shared/
|-- __init__.py
|-- README.md
|
|-- math/                            # Mathematical utilities
|   |-- __init__.py
|   |-- statistics.py                # Statistical computation utilities
|   |-- indicators.py                # Technical indicator computations
|   |-- normalization.py             # Normalization utilities
|
|-- stats/                           # Statistical functions
|   |-- __init__.py
|   |-- distributions.py             # Probability distribution utilities
|   |-- sampling.py                  # Sampling utilities
|   |-- hypothesis.py                # Hypothesis testing utilities
|
|-- datetime/                        # Date and time utilities
|   |-- __init__.py
|   |-- market_calendar.py           # Market trading calendar
|   |-- session.py                   # Trading session utilities
|   |-- formatting.py                # Date/time formatting
|
|-- io/                              # File and network I/O utilities
|   |-- __init__.py
|   |-- file_utils.py                # File operations
|   |-- path_utils.py                # Path construction utilities
|   |-- csv_utils.py                 # CSV read/write utilities
|   |-- json_utils.py                # JSON serialization utilities
|
|-- cache/                           # Caching utilities
|   |-- __init__.py
|   |-- memory_cache.py              # In-memory cache with TTL
|   |-- disk_cache.py                # Disk-backed cache utilities
|   |-- cache_key.py                 # Cache key construction
|
|-- retry/                           # Retry and resilience utilities
|   |-- __init__.py
|   |-- retry_policy.py              # Retry policy definitions
|   |-- circuit_breaker.py           # Circuit breaker pattern
|   |-- backoff.py                   # Backoff strategy utilities
|
|-- serial/                          # Serialization utilities
|   |-- __init__.py
|   |-- json_serial.py               # JSON serialization
|   |-- pickle_serial.py             # Pickle serialization (for models)
|   |-- schema_serial.py             # Schema-validated serialization
|
|-- validation/                      # Input validation utilities
|   |-- __init__.py
|   |-- type_validators.py           # Type validation utilities
|   |-- range_validators.py          # Range validation utilities
|   |-- schema_validators.py         # Schema validation utilities
|
|-- formatting/                      # Output formatting utilities
|   |-- __init__.py
|   |-- number_formatting.py         # Number and percentage formatting
|   |-- table_formatting.py          # Table and grid formatting
|   |-- report_formatting.py         # Report layout utilities
|
|-- collections/                     # Collection utilities
|   |-- __init__.py
|   |-- ring_buffer.py               # Ring buffer data structure
|   |-- sorted_list.py               # Sorted list utilities
|   |-- time_series.py               # Time-series data structure
|
|-- concurrency/                     # Concurrency utilities
|   |-- __init__.py
|   |-- thread_safe.py               # Thread-safe data structure wrappers
|   |-- lock_manager.py              # Lock management utilities
|
|-- telemetry/                       # Telemetry utilities
|   |-- __init__.py
|   |-- metrics.py                   # Metric collection utilities
|   |-- counters.py                  # Counter utilities
|   |-- timers.py                    # Timing utilities
`

**Ownership:** Architecture Council
**Allowed contents:** Utilities used by >= 2 engine packages; no business logic
**Forbidden contents:** Engine-specific code, investment logic
**Growth policy:** A utility enters shared/ only when used by >= 2 engines

---

### 2.7 config/ — Configuration Directory

**Purpose:** All configuration definitions, templates, and environment-specific
configuration files. See Part VI for complete specification.

**Complete tree:**
`
config/
|-- README.md
|-- __init__.py
|
|-- global_config.py                 # Global configuration dataclass
|-- config_loader.py                 # Configuration loading and merging
|
|-- environments/                    # Environment-specific configs
|   |-- base.yaml                    # Base configuration (all envs)
|   |-- production.yaml              # Production overrides
|   |-- paper.yaml                   # Paper trading overrides
|   |-- development.yaml             # Development overrides
|   |-- testing.yaml                 # Test environment config
|
|-- engines/                         # Per-engine configuration schemas
|   |-- README.md
|   |-- [engine_name]_config.py      # One per engine
|
|-- templates/                       # Configuration templates
|   |-- .env.example                 # Environment variable template
|   |-- base_template.yaml           # Base YAML template
|
|-- profiles/                        # Named configuration profiles
|   |-- aggressive_trading.yaml
|   |-- conservative_trading.yaml
|   |-- backtest_mode.yaml
|
|-- feature_flags/                   # Feature flag definitions
|   |-- README.md
|   |-- flags.yaml                   # Feature flag registry
`

---

### 2.8 resources/ — Static Runtime Assets

`
resources/
|-- README.md
|
|-- data/                            # Static reference data
|   |-- market_calendars/            # NSE, BSE trading calendars
|   |-- symbol_maps/                 # Symbol to instrument ID maps
|   |-- instrument_lists/            # Tradeable instrument lists
|   |-- sector_classifications/      # Sector/industry classifications
|
|-- models/                          # Pre-trained model files
|   |-- meta_learning/               # MetaLearning model artifacts
|   |-- prediction/                  # Prediction model artifacts
|   |-- regime_classifier/           # Regime classification models
|
|-- templates/                       # Report and document templates
|   |-- reports/                     # Report templates
|   |-- dashboards/                  # Dashboard layout templates
|   |-- dossiers/                    # Evidence dossier templates
|   |-- notifications/               # Telegram notification templates
|
|-- assets/                          # Visual assets
|   |-- icons/                       # Dashboard icons
|   |-- logos/                       # System logos
|
|-- prompts/                         # AI/LLM prompt templates (if used)
|   |-- [prompt_name].md
`

---

### 2.9 data/ — Runtime Data Directory (Gitignored)

`
data/                                # GITIGNORED — runtime generated
|
|-- databases/                       # SQLite databases
|   |-- telemetry.db                 # System telemetry (Control Tower)
|   |-- trades.db                    # Trade history
|   |-- learning.db                  # Learning engine data
|   |-- strategies.db                # Strategy performance data
|
|-- paper_trades.csv                 # Paper trading journal
|
|-- snapshots/                       # Knowledge graph snapshots
|   |-- [YYYY-MM-DD]_knowledge.pkl
|
|-- dossiers/                        # Strategy evidence dossiers
|   |-- [strategy_id]_dossier.json
|
|-- positions/                       # Open position state
|   |-- current_positions.json
|
|-- checkpoints/                     # Engine state checkpoints
|   |-- [engine_name]_checkpoint.pkl
`

---

### 2.10 datasets/ — Training and Reference Datasets

`
datasets/
|-- README.md
|
|-- market_data/                     # Historical market data
|   |-- nifty50/                     # NIFTY 50 historical OHLCV
|   |-- banknifty/                   # BANKNIFTY historical OHLCV
|   |-- equities/                    # Individual equity OHLCV
|   |-- options/                     # Options chain historical data
|
|-- macro_data/                      # Macroeconomic datasets
|   |-- global_indices/              # S&P, Nikkei, DAX historical
|   |-- fx_rates/                    # Currency pair historical
|   |-- bonds/                       # Treasury yield historical
|   |-- commodities/                 # Oil, Gold, commodities historical
|
|-- events/                          # Event data
|   |-- earnings_calendar/           # Corporate earnings events
|   |-- rbi_meetings/                # RBI policy meeting dates
|   |-- expiry_dates/                # Options expiry calendar
|
|-- labels/                          # Labeled training datasets
|   |-- regime_labels/               # Manually labeled regime periods
|   |-- strategy_labels/             # Strategy performance labels
`

---

### 2.11 deployment/ — Deployment Artifacts

`
deployment/
|-- README.md
|
|-- docker/                          # Docker files
|   |-- Dockerfile.production        # Production image
|   |-- Dockerfile.development       # Development image
|   |-- docker-compose.prod.yml      # Production compose
|   |-- docker-compose.dev.yml       # Development compose
|   |-- .dockerignore                # Docker build exclusions
|
|-- kubernetes/                      # K8s manifests (future)
|   |-- README.md
|   |-- base/
|   |-- overlays/
|
|-- helm/                            # Helm charts (future)
|   |-- README.md
|
|-- ci/                              # CI/CD pipeline definitions
|   |-- pr.yml                       # Pull request pipeline
|   |-- main.yml                     # Main branch pipeline
|   |-- release.yml                  # Release pipeline
|   |-- nightly.yml                  # Nightly health check
|
|-- scripts/                         # Deployment scripts
|   |-- deploy_vps.sh                # VPS deployment script
|   |-- rollback.sh                  # Rollback script
|   |-- health_check.sh              # Post-deploy health check
|   |-- backup_data.sh               # Data volume backup
|
|-- environments/                    # Per-environment config
|   |-- production/
|   |   |-- .env.example
|   |   |-- config.yaml
|   |-- paper_trading/
|   |   |-- .env.example
|   |   |-- config.yaml
|   |-- development/
|       |-- .env.example
|       |-- config.yaml
`

---

*End of Part II (overview — complete directory tree in Supplement A)*

---
## PART III — ENGINE DIRECTORY STANDARDS

### 3.1 Standard Engine Package Structure

Every engine in IIOS follows the same physical package structure. This uniformity
means a developer can navigate any engine's internals using the same mental map,
regardless of which engine they are looking at.

`
engines/[engine_name]/
|
|-- __init__.py                      # Public interface (MANDATORY)
|-- [engine_name].py                 # Main engine class (MANDATORY)
|-- README.md                        # Engine documentation (MANDATORY)
|
|-- documentation/                   # Engine-local documentation
|   |-- DESIGN.md                    # Internal design notes
|   |-- INTERFACE.md                 # Interface specification
|   |-- PERFORMANCE.md               # Performance characteristics
|   |-- CHANGELOG.md                 # Engine version history
|
|-- interfaces/                      # Interface definitions and protocols
|   |-- __init__.py
|   |-- [engine_name]_interface.py   # Formal interface definition
|   |-- input_types.py               # Input type definitions
|   |-- output_types.py              # Output type definitions
|
|-- models/                          # Engine-local data models
|   |-- __init__.py
|   |-- [domain_model].py            # Domain model for this engine
|   |-- [result_model].py            # Result/output model types
|
|-- services/                        # Internal service logic
|   |-- __init__.py
|   |-- [service_name].py            # One file per service
|
|-- processors/                      # Data processing components
|   |-- __init__.py
|   |-- [processor_name].py          # One file per processor
|
|-- validators/                      # Input and business rule validators
|   |-- __init__.py
|   |-- input_validator.py           # Input validation logic
|   |-- business_validator.py        # Business rule validation
|
|-- adapters/                        # External system adapters
|   |-- __init__.py
|   |-- [external_system]_adapter.py # One per external system
|
|-- workflows/                       # Multi-step workflow implementations
|   |-- __init__.py
|   |-- [workflow_name].py           # One file per workflow
|
|-- policies/                        # Business policy implementations
|   |-- __init__.py
|   |-- [policy_name].py             # One file per policy
|
|-- governance/                      # Engine-local governance checks
|   |-- __init__.py
|   |-- compliance_checker.py        # Compliance check logic
|   |-- audit_logger.py              # Audit logging for this engine
|
|-- analytics/                       # Engine-local analytical functions
|   |-- __init__.py
|   |-- [analytics_name].py
|
|-- monitoring/                      # Engine-local monitoring
|   |-- __init__.py
|   |-- health_provider.py           # Health check implementation
|   |-- metrics_provider.py          # Metrics for this engine
|
|-- config/                          # Engine-local configuration
|   |-- __init__.py
|   |-- defaults.py                  # Default configuration values
|   |-- schema.py                    # Configuration schema definition
|
|-- resources/                       # Engine-local static data
|   |-- [static_file.json]
|   |-- [reference_data.yaml]
|
|-- examples/                        # Engine usage examples
|   |-- README.md
|   |-- [example_name].py            # Self-contained examples
|
|-- future/                          # Planned but not yet implemented
|   |-- README.md                    # What is planned and why deferred
|   |-- [PLANNED-feature.md]
`

---

### 3.2 Engine Subdirectory Specifications

#### 3.2.1 documentation/

**Purpose:** Engine-level documentation that is too detailed for the top-level
README.md but too internal for docs/architecture/. This is the engineer's notebook
for the engine.

**Contents:**
- DESIGN.md — Internal design decisions, non-obvious choices, known limitations.
- INTERFACE.md — Detailed interface specification beyond what docstrings provide.
- PERFORMANCE.md — Performance benchmarks, latency targets, optimization notes.
- CHANGELOG.md — Engine-specific version history (separate from repo CHANGELOG.md).

**Ownership:** Engine Owner

**Why this directory exists:** Architecture-level documentation lives in docs/.
But every engine has internal design context that doesn't belong in the architecture
docs — it's too detailed. This directory is the designated location for that internal
context. Without it, this documentation either ends up in source code comments (where
it is hard to find) or is never written at all.

---

#### 3.2.2 interfaces/

**Purpose:** Formal interface definitions. The public interface of the engine —
the contract that the Orchestrator and other consumers depend on — is defined here
as Python protocols and type definitions.

**Contents:**
- Interface protocol class
- Input type definitions
- Output type definitions

**Why separated from models/:** Models are data structures. Interfaces are behavioral
contracts. The distinction matters: an interface says "this engine accepts X and returns Y."
A model says "X looks like this." They serve different audiences.

---

#### 3.2.3 models/

**Purpose:** Engine-local data models — Python dataclasses and type definitions that
represent the engine's specific domain concepts. These are internal to the engine.
If a model needs to be shared with other engines, it is promoted to domain/.

**Contents:**
- Domain models specific to this engine's processing
- Result models that carry the engine's output
- Internal state models

---

#### 3.2.4 services/

**Purpose:** The core business logic of the engine, organized into service classes.
Each service has a single, clear responsibility. Services may use processors,
validators, and adapters but do not directly import from other engines.

**Contents:**
- Core computation services
- State management services
- Orchestration services (within the engine)

**What belongs here:** Complex business logic that doesn't fit in the main engine
class. If the main engine class's methods are longer than 30 lines, the logic
should be delegated to service classes in this directory.

---

#### 3.2.5 processors/

**Purpose:** Data transformation and processing components. Processors receive
data, transform it, and return results. They are stateless where possible.

**Contents:**
- Data transformation processors
- Signal processing components
- Aggregation processors

**Why separate from services/:** Processors are transformation-focused (input → output)
whereas services may be stateful and orchestrate multiple steps. The distinction
helps identify where state lives and where pure computation lives.

---

#### 3.2.6 validators/

**Purpose:** Input validation and business rule enforcement. Validators confirm
that inputs meet expectations before processing begins. They also enforce business
constraints that are specific to this engine.

**Contents:**
- input_validator.py — Validates all inputs entering the engine.
- usiness_validator.py — Validates business rule compliance.

**Why important:** Validators are the engine's boundary enforcement. Every external
input that enters an engine passes through its validator before any processing.
This ensures that business logic never sees malformed data.

---

#### 3.2.7 adapters/

**Purpose:** Adapters translate between IIOS's internal representations and external
system representations. Each external system that the engine communicates with has
its own adapter.

**Contents:**
- Broker API adapters (Dhan, etc.)
- Data feed adapters (yfinance, Dhan data API)
- External notification adapters (Telegram)
- Database adapters

**Why adapters, not services?** Adapters encapsulate the translation concern, keeping
the service logic independent of external API conventions. If the external API changes
its response format, only the adapter changes — not the service logic.

---

#### 3.2.8 workflows/

**Purpose:** Multi-step process implementations that coordinate several services
and processors. A workflow represents a named, sequenced business process.

**Contents:**
- Decision cycle workflow
- Strategy evaluation workflow
- Session startup workflow
- Recovery workflow

**Why separate from services/:** A workflow orchestrates services without containing
business logic itself. It is the "recipe" layer: "do A, then B, then C, handle errors
with D." Service logic is in services/; the sequence is here.

---

#### 3.2.9 policies/

**Purpose:** Business policy implementations. Policies are decision rules that
determine behavior in specific situations. They are pure logic: given conditions,
return a decision.

**Contents:**
- Sizing policy (how much capital for this trade)
- Regime policy (which strategies active in this regime)
- Risk policy (budget allocation rules)
- Exit policy (when to exit a trade)

**Why separate from services/:** Policies are designed to be replaceable. The same
engine can use an aggressive policy or a conservative policy by swapping the policy
object. Keeping policies as distinct classes in their own directory makes them
findable, replaceable, and testable in isolation.

---

#### 3.2.10 governance/

**Purpose:** Engine-local governance checks and audit logging. Every engine that
makes significant decisions logs those decisions here.

**Contents:**
- compliance_checker.py — Verifies decisions against constitutional rules.
- udit_logger.py — Records all significant engine actions to the audit log.

**Why every engine has governance/:** The IIOS constitution requires that all
significant decisions are auditable. The governance/ directory in each engine
is the implementation of that requirement. It is separate from monitoring/ because
governance is about compliance and audit, not operational health.

---

#### 3.2.11 analytics/

**Purpose:** Engine-local analytical functions that are too specific to go in
shared/ but are complex enough to deserve their own module.

**Contents:**
- Risk analytics (for the Risk Engine)
- Backtest analytics (for Strategy Lab)
- Performance analytics (for Performance Analytics Engine)
- Learning analytics (for Learning System)

---

#### 3.2.12 monitoring/

**Purpose:** Engine-level monitoring and metrics. Each engine provides its own
health check and metrics, consumed by the Control Tower.

**Contents:**
- health_provider.py — Implements the health check protocol from core/health/.
- metrics_provider.py — Defines and publishes metrics for this engine.

**Key distinction:** The monitoring/ directory provides operational visibility into
the engine's current state. It does not implement business logic.

---

#### 3.2.13 config/

**Purpose:** Engine-local default configuration. The engine's configuration schema
and its default values live here.

**Contents:**
- defaults.py — Default values for all configuration parameters.
- schema.py — Configuration schema as a Python dataclass.

**Inheritance:** The engine's default configuration is a base layer. The global
configuration system in config/ can override any value. The defaults represent
the engine's "works without any override" state.

---

#### 3.2.14 resources/

**Purpose:** Static data files that the engine needs at runtime. These are committed
to version control because they are reference data, not generated data.

**Contents:**
- Symbol lists
- Reference tables
- Constant data files that are too large for source code
- Pre-computed lookup tables

---

#### 3.2.15 examples/

**Purpose:** Standalone, runnable examples demonstrating how to use this engine.

**Contents:**
- Example scripts showing basic engine usage
- Example configuration files
- Example integration patterns

**Rule:** Every example must work as-is with the engine's default configuration.
Examples are tested in CI.

---

#### 3.2.16 future/

**Purpose:** A formal holding area for planned features and capability extensions
that have been designed but not yet implemented.

**Contents:**
- README.md — Index of planned features with estimated effort and priority.
- PLANNED-[feature].md — Specification for each planned feature.

**Why this directory matters:** Without a designated place for planned-but-not-yet-
implemented features, they end up as code comments, TODO items, or informal
communication. The uture/ directory makes the engine's roadmap visible,
reviewable, and governable.

---

### 3.3 Engine Package Examples — Risk Guardian

To illustrate the standard structure, here is the physical layout of the
isk_guardian engine, one of the most safety-critical engines in IIOS:

`
engines/risk_guardian/
|
|-- __init__.py                      # Exports: RiskGuardianEngine
|-- risk_guardian.py                 # Main class: RiskGuardianEngine
|-- README.md                        # "Kill-switch guardian — PROTECTED MODULE"
|
|-- documentation/
|   |-- DESIGN.md                    # Why three kill conditions; threshold logic
|   |-- INTERFACE.md                 # check_kill_switch() specification
|   |-- PERFORMANCE.md               # < 5ms evaluation target
|   |-- CHANGELOG.md
|
|-- interfaces/
|   |-- __init__.py
|   |-- risk_guardian_interface.py   # RiskGuardianProtocol
|   |-- input_types.py               # RiskSnapshot input type
|   |-- output_types.py              # KillSwitchDecision output type
|
|-- models/
|   |-- __init__.py
|   |-- kill_switch_state.py         # KillSwitchState model
|   |-- risk_snapshot.py             # RiskSnapshot model
|
|-- services/
|   |-- __init__.py
|   |-- kill_switch_service.py       # Kill switch evaluation logic
|   |-- position_risk_service.py     # Per-position risk evaluation
|
|-- processors/
|   |-- __init__.py
|   |-- vix_processor.py             # VIX signal processing
|   |-- loss_processor.py            # Daily loss computation
|   |-- drawdown_processor.py        # Strategy drawdown computation
|
|-- validators/
|   |-- __init__.py
|   |-- input_validator.py           # Validates risk snapshot inputs
|
|-- policies/
|   |-- __init__.py
|   |-- kill_switch_policy.py        # Defines the 3 kill conditions
|   |-- recovery_policy.py           # Post-kill-switch recovery rules
|
|-- governance/
|   |-- __init__.py
|   |-- compliance_checker.py        # NNH rule compliance verification
|   |-- audit_logger.py              # Kill-switch event audit logging
|
|-- monitoring/
|   |-- __init__.py
|   |-- health_provider.py           # Always returns CRITICAL if kill fired
|   |-- metrics_provider.py          # VIX level, daily loss, drawdown metrics
|
|-- config/
|   |-- __init__.py
|   |-- defaults.py                  # VIX_THRESHOLD=45, LOSS_PCT=0.02, DD_PCT=0.15
|   |-- schema.py                    # RiskGuardianConfig schema
|
|-- future/
|   |-- README.md
|   |-- PLANNED-dynamic-thresholds.md
`

---

### 3.4 Engine Package Examples — Debate and Decision

`
engines/debate_and_decision/
|
|-- __init__.py                      # Exports: DebateEngine, DecisionEngine
|-- debate_and_decision.py           # Main class
|-- README.md
|
|-- documentation/
|   |-- DESIGN.md                    # 5-agent debate design rationale
|   |-- INTERFACE.md
|   |-- PERFORMANCE.md               # Target: < 40ms for full debate
|
|-- interfaces/
|   |-- __init__.py
|   |-- debate_interface.py          # DebateProtocol
|   |-- input_types.py               # PredictionSignals, RiskEnvelope
|   |-- output_types.py              # DebateResult, DecisionRecord
|
|-- models/
|   |-- __init__.py
|   |-- agent.py                     # Agent model (one per debate agent)
|   |-- debate_round.py              # DebateRound model
|   |-- vote.py                      # Vote model
|   |-- consensus.py                 # ConsensusScore model
|
|-- services/
|   |-- __init__.py
|   |-- debate_facilitator.py        # Orchestrates the 5-agent debate
|   |-- decision_service.py          # 6.5 threshold evaluation
|   |-- evidence_collector.py        # Evidence dossier assembly
|
|-- processors/
|   |-- __init__.py
|   |-- signal_aggregator.py         # Aggregates signals from 5 agents
|   |-- score_normalizer.py          # Normalizes debate scores
|
|-- validators/
|   |-- __init__.py
|   |-- debate_validator.py          # Validates debate inputs
|
|-- policies/
|   |-- __init__.py
|   |-- consensus_policy.py          # Consensus rules (threshold 6.5)
|   |-- tie_break_policy.py          # Tie-breaking rules
|
|-- governance/
|   |-- __init__.py
|   |-- compliance_checker.py
|   |-- audit_logger.py              # Logs every debate and decision
|
|-- monitoring/
|   |-- __init__.py
|   |-- health_provider.py
|   |-- metrics_provider.py          # Debate duration, score distribution
|
|-- config/
|   |-- __init__.py
|   |-- defaults.py                  # DECISION_THRESHOLD=6.5, N_AGENTS=5
|   |-- schema.py
`

---

*End of Part III*

---

## PART IV — CORE LIBRARY STRUCTURE

### 4.1 Core vs. Shared — The Distinction

core/ contains infrastructure and framework code. shared/ contains application-
level utility code. The distinction:

| Aspect | core/ | shared/ |
|--------|-------|---------|
| Change frequency | Very low (< 5/year) | Moderate |
| Impact of change | System-wide | Multi-engine |
| Business logic | None | None |
| Domain knowledge | None | Minimal (dates, numbers) |
| Who uses it | All engines, shared/, domain/ | Multiple engines |
| Governance | Architecture Council approval | Architecture Council review |

---

### 4.2 Core Library Physical Organization

The core/ directory is documented in Part II (Section 2.4). This section
provides deeper specification for each core library.

#### 4.2.1 core/engine/ — Base Engine Framework

This is the most critical library in the entire repository. Every engine inherits
from or implements the protocols defined here.

**Physical files:**

ase_engine.py — The abstract base class. Defines the lifecycle interface that
every engine must implement. Contains abstract methods for: initialize(), start(),
stop(), health_check(). Contains concrete implementations of: engine registration,
status management, logging setup.

lifecycle.py — The lifecycle state machine. Defines the valid states
(UNINITIALIZED, INITIALIZING, READY, RUNNING, STOPPING, STOPPED, FAILED) and
the valid transitions between them. The lifecycle protocol is implemented here
and inherited by ase_engine.py.

egistry.py — The engine registry. A singleton that maintains the authoritative
list of all registered engine instances. Provides: egister(engine), get(name),
list_all(), health_summary(). The Orchestrator uses this registry to coordinate
all engines.

status.py — Engine status enumeration and associated types.

protocol.py — Python Protocol classes for typing purposes. Allows type checkers
to verify that an engine implementation satisfies the engine contract.

#### 4.2.2 core/events/ — Event Bus

The event bus is the primary communication mechanism between engines.

**Physical files:**

us.py — The event bus implementation. Provides: subscribe(event_type, handler),
unsubscribe(event_type, handler), publish(event), publish_async(event).
Thread-safe.

event.py — The base event type. Every domain event in domain/events/ extends
this base type. Contains: event ID (UUID), timestamp (UTC), event type string,
source engine name, payload.

dispatcher.py — The dispatcher that routes events from producers to subscribers.
Manages the subscription registry and dispatches to all matching subscribers.

subscriber.py — The Subscriber protocol. Defines the interface that event
handlers must implement.

ilters.py — Event filtering utilities. Allows subscribers to filter events
by source engine, by payload content, or by time window.

#### 4.2.3 core/health/ — Health Check Infrastructure

**Physical files:**

health_check.py — The health check protocol. Every engine implements this
protocol. Defines: HealthCheckResult, HealthStatus (HEALTHY, DEGRADED, CRITICAL,
FAILED), and the check() -> HealthCheckResult method signature.

ohs.py — Operational Health Score computation. Aggregates the health results
from all registered engines into a single system-level OHS value between 0 and 1.
Implements the weighted aggregation formula. Defines OHS tiers:
OPTIMAL (>= 0.95), NOMINAL (>= 0.80), DEGRADED (>= 0.60), CRITICAL (>= 0.35),
FAILED (< 0.35).

eporter.py — Health report builder. Formats the health summary into the
standard report structure consumed by the Control Tower and Telegram bot.

#### 4.2.4 core/logging/ — Logging Infrastructure

**Physical files:**

logger.py — The logger factory. Provides get_logger(name) -> Logger which
returns a structured logger configured for IIOS. All application logging goes
through this factory.

ormatters.py — Log formatters. Provides JSON format (for machine processing)
and human-readable text format.

sanitizer.py — Log sanitization. Intercepts all log output and strips sensitive
values before they are written to any log destination.

#### 4.2.5 core/errors/ — Error Hierarchy

**Physical files:**

ase_errors.py — The root error classes. Defines IIOSError (base), 
IIOSConfigurationError, IIOSStartupError, IIOSShutdownError.

engine_errors.py — Engine-specific errors. EngineNotReadyError,
EngineRegistrationError, EngineTimeoutError.

data_errors.py — Data-related errors. DataQualityError, DataFeedError,
DataValidationError.

governance_errors.py — Governance errors. ComplianceViolationError,
UnauthorizedDecisionError, CertificateExpiredError.

---

### 4.3 Shared Library Physical Organization

The shared/ directory is documented in Part II (Section 2.6). This section
provides deeper specification.

#### 4.3.1 shared/math/ — Mathematical Utilities

Used by: Prediction Engine, Risk Engine, Strategy Lab, Performance Analytics.

statistics.py — Rolling statistics (mean, std, variance, rolling window).
indicators.py — Technical indicator calculations (RSI, MACD, Bollinger).

ormalization.py — Feature normalization and scaling utilities.

#### 4.3.2 shared/datetime/ — Date/Time Utilities

Used by: All engines (universal dependency).

market_calendar.py — NSE/BSE market calendar. Provides: is_trading_day(date),

ext_trading_day(date), session_open_time(), session_close_time().

session.py — Trading session utilities. Provides: current_session(),
	ime_to_open(), 	ime_to_close(), is_pre_market(), is_market_hours().

#### 4.3.3 shared/cache/ — Caching Utilities

Used by: Knowledge Engine (5-minute cache), Global Intelligence (pre-warm cache).

memory_cache.py — In-memory cache with TTL. The primary implementation used
by the Knowledge Engine's background cache.

disk_cache.py — Disk-backed cache. For assets that survive process restarts
(model files, large datasets).

cache_key.py — Canonical cache key construction. Ensures consistent key formats
across all caching usage.

#### 4.3.4 shared/retry/ — Retry and Resilience

Used by: Data feed engines, Execution Engine.

etry_policy.py — Configurable retry with: max_attempts, delay_seconds,
exponential_backoff, jitter.

circuit_breaker.py — Circuit breaker pattern. Opens after N consecutive failures,
closes after recovery period. Used by data feed adapters.

---

### 4.4 Domain Library Physical Organization

The domain/ directory is documented in Part II (Section 2.5). The domain library
is organized into 5 categories:

| Category | Location | Contents |
|----------|----------|---------|
| Entity types | domain/entities/ | Market, strategy, trade, position entity types |
| Event types | domain/events/ | Market, decision, risk, system event types |
| Value objects | domain/values/ | Price, quantity, signal, score, budget types |
| Enumerations | domain/enumerations/ | Regime, order type, asset class enumerations |
| Constants | domain/constants/ | Market hours, system thresholds, symbol maps |

---

*End of Part IV*

---

## PART V — DOCUMENTATION ORGANIZATION

### 5.1 Documentation Architecture

IIOS documentation is organized into 9 categories, each in its own subdirectory
under docs/. The categories are ordered from most abstract (philosophy) to most
operational (reference):

| Category | Directory | Audience |
|----------|-----------|---------|
| Architecture | docs/architecture/ | System architects |
| Engineering | docs/engineering/ | Platform engineers |
| Decisions | docs/decisions/ | All contributors |
| Operations | docs/operations/ | Operations team |
| Standards | docs/standards/ | All contributors |
| Tutorials | docs/tutorials/ | New contributors |
| Developer guides | docs/developer_guides/ | Engine developers |
| User guides | docs/user_guides/ | Operators |
| Reference | docs/reference/ | All users |

---

### 5.2 Architecture Documentation Physical Organization

Architecture documents are formal, versioned specifications of what the system
is and how it is structured.

**Naming convention:** IIOS-[DOMAIN]-ARCH-[NNN].md for formal documents;
descriptive UPPER_SNAKE_CASE.md for others.

**Required architecture documents:**

| Document | Location | Status |
|----------|----------|--------|
| Master Integration Architecture | docs/architecture/IIOS_INTEGRATION_AND_OPERATIONAL_ARCHITECTURE.md | COMPLETE |
| Master Orchestrator Architecture | docs/architecture/IIOS_MASTER_ORCHESTRATOR_ARCHITECTURE.md | COMPLETE |
| Engine Architectures (18) | docs/architecture/engines/ | Per-engine |
| Ontology Documents (8) | docs/architecture/ontologies/ | Per-ontology |
| Workflow Catalogue | docs/architecture/workflows/ | Complete |
| Layer Architecture | docs/architecture/layers/ | Per-layer |

**Archive sub-directory:** docs/architecture/archive/ — Superseded architecture
documents with ARCHIVED.md markers.

---

### 5.3 Engineering Documentation Physical Organization

Engineering documents define the HOW of building IIOS: standards, conventions,
specifications.

**Required engineering documents:**

| Document | Location | Status |
|----------|----------|--------|
| Repository Engineering Spec | docs/engineering/REPOSITORY_ENGINEERING.md | COMPLETE |
| Physical Repository Structure | docs/engineering/PHYSICAL_REPOSITORY_STRUCTURE.md | THIS DOCUMENT |
| Code Standards | docs/engineering/IIOS_CODE_STANDARDS.md | Planned |
| Test Standards | docs/engineering/IIOS_TEST_STANDARDS.md | Planned |
| Security Standards | docs/engineering/IIOS_SECURITY_STANDARDS.md | Planned |
| Deployment Standards | docs/engineering/IIOS_DEPLOYMENT_STANDARDS.md | Planned |

---

### 5.4 Architecture Decision Records Physical Organization

ADRs document significant decisions. They accumulate over time and are never deleted.

**Physical organization:**
`
docs/decisions/
|-- README.md                        # ADR index (table of all ADRs)
|-- ADR-001-engine-isolation.md      # Sequential numbering
|-- ADR-002-event-bus-protocol.md
|-- ADR-003-domain-type-separation.md
|-- ADR-004-paper-trading-mode.md
|-- ADR-005-dhan-yfinance-fallback.md
|-- ADR-006-kill-switch-thresholds.md
|-- ADR-007-decision-score-threshold.md
|-- ADR-008-knowledge-cache-ttl.md
|-- ADR-009-monte-carlo-paths.md
|-- ADR-010-evidence-dossier-validity.md
|-- [continuing sequentially]
`

**ADR lifecycle:**
- Status: PROPOSED → ACCEPTED → (DEPRECATED / SUPERSEDED)
- Superseded ADRs remain in the directory with Status: SUPERSEDED by ADR-NNN
- Never deleted; the decision history is permanent

---

### 5.5 Operational Runbook Physical Organization

Runbooks document step-by-step operational procedures.

**Naming convention:** RB-[CATEGORY]-[NNN]-[short-slug].md

**Categories:**
- RB-DEPLOY- — Deployment procedures
- RB-OPS- — Operational procedures
- RB-MAINT- — Maintenance procedures
- RB-INCIDENT- — Incident response procedures
- RB-RECOVERY- — Recovery procedures

**Physical organization:**
`
docs/operations/
|-- README.md                        # Runbook index
|-- RB-DEPLOY-001-vps-deployment.md
|-- RB-DEPLOY-002-docker-rebuild.md
|-- RB-OPS-001-daily-startup.md
|-- RB-OPS-002-daily-shutdown.md
|-- RB-OPS-003-emergency-stop.md
|-- RB-OPS-004-kill-switch-response.md
|-- RB-OPS-005-telegram-bot-restart.md
|-- RB-MAINT-001-daily-log-review.md
|-- RB-MAINT-002-weekly-health-check.md
|-- RB-MAINT-003-monthly-dependency-review.md
|-- RB-INCIDENT-001-data-feed-failure.md
|-- RB-INCIDENT-002-broker-api-failure.md
|-- RB-INCIDENT-003-database-corruption.md
|-- RB-RECOVERY-001-full-system-recovery.md
|-- RB-RECOVERY-002-knowledge-graph-recovery.md
`

---

### 5.6 Developer Guide Physical Organization

Developer guides provide narrative explanations for common development tasks.

`
docs/developer_guides/
|-- README.md
|-- local_development_setup.md        # First-time setup
|-- adding_a_new_engine.md            # Step-by-step new engine guide
|-- adding_a_new_strategy.md          # Strategy development guide
|-- adding_a_new_agent.md             # Agent development guide
|-- writing_engine_tests.md           # Testing patterns for engines
|-- debugging_the_decision_cycle.md   # Decision cycle debugging
|-- working_with_the_event_bus.md     # Event-driven development guide
|-- extending_the_knowledge_graph.md  # Knowledge Engine extension guide
|-- configuring_new_environments.md   # Environment configuration guide
|-- migrating_engine_interfaces.md    # Interface migration guide
`

---

*End of Part V*

---

## PART VI — CONFIGURATION ORGANIZATION

### 6.1 Configuration Philosophy

IIOS configuration is hierarchical, explicit, and validated at startup. The
hierarchy resolves from most general to most specific:

`
Layer 1 — Engine defaults    (engines/[name]/config/defaults.py)
     |
     v
Layer 2 — Base configuration  (config/environments/base.yaml)
     |
     v
Layer 3 — Environment config  (config/environments/[environment].yaml)
     |
     v
Layer 4 — Environment vars    (.env file or host environment)
     |
     v
Layer 5 — Runtime overrides   (--flag arguments to main.py)
`

Each layer overrides the one above it. A setting at Layer 4 always wins over
a setting at Layer 2.

---

### 6.2 Global Configuration Physical Organization

`
config/
|-- README.md                         # Configuration system documentation
|-- __init__.py
|-- global_config.py                  # GlobalConfig dataclass (top-level)
|-- config_loader.py                  # Loads and merges all config layers
|-- config_validator.py               # Validates assembled configuration
|
|-- environments/
|   |-- base.yaml                     # Defaults for all environments
|   |-- production.yaml               # Production-specific overrides
|   |-- paper.yaml                    # Paper trading overrides
|   |-- development.yaml              # Development-specific settings
|   |-- testing.yaml                  # Test environment settings
|   |-- ci.yaml                       # CI pipeline settings
|
|-- engines/
|   |-- README.md
|   |-- global_intelligence_config.py
|   |-- market_intelligence_config.py
|   |-- meta_learning_config.py
|   |-- opportunity_engine_config.py
|   |-- strategy_lab_config.py
|   |-- capital_risk_engine_config.py
|   |-- risk_control_config.py
|   |-- market_simulation_config.py
|   |-- risk_guardian_config.py
|   |-- debate_and_decision_config.py
|   |-- execution_engine_config.py
|   |-- trade_monitoring_config.py
|   |-- learning_system_config.py
|   |-- performance_analytics_config.py
|   |-- research_lab_config.py
|   |-- validation_engine_config.py
|   |-- control_tower_config.py
|   |-- orchestrator_config.py
|
|-- templates/
|   |-- .env.example                  # Template for required env vars
|   |-- base_template.yaml            # YAML config template
|   |-- engine_config_template.py     # Engine config class template
|
|-- profiles/
|   |-- aggressive_trading.yaml       # Wider position limits, larger budget
|   |-- conservative_trading.yaml     # Tighter limits, smaller budget
|   |-- backtest_mode.yaml            # Settings for backtest runs
|   |-- paper_trading.yaml            # Paper trading defaults
|   |-- live_trading.yaml             # Live trading defaults
|
|-- feature_flags/
|   |-- README.md
|   |-- flags.yaml                    # Feature flag registry
|   |-- schema.py                     # Feature flag schema definition
`

---

### 6.3 Environment Configuration Specification

Each environment configuration file follows this structure:

**base.yaml** — Contains all configuration keys with their default values:
`yaml
system:
  environment: development
  paper_trading: true
  log_level: INFO
  decision_threshold: 6.5

risk:
  max_daily_loss_pct: 0.02
  vix_kill_threshold: 45
  max_strategy_drawdown_pct: 0.15

scheduling:
  pre_market_check_time: "08:30"
  market_open_time: "09:15"
  market_close_time: "15:30"
  eod_processing_time: "16:00"

data_feeds:
  primary: dhan
  fallback: yfinance
  timeout_seconds: 8

monte_carlo:
  min_paths: 1000
  simulation_periods: 252
`

**production.yaml** — Overrides for live production:
`yaml
system:
  environment: production
  paper_trading: false
  log_level: WARNING

risk:
  max_daily_loss_pct: 0.02   # same as base — never loosen in production
`

**paper.yaml** — Overrides for paper trading:
`yaml
system:
  environment: paper
  paper_trading: true
  log_level: INFO
`

---

### 6.4 Secrets Strategy (Logical Only)

Secrets are never stored in the repository. The physical repository contains only:

**What IS committed:**
- .env.example — Documents every environment variable with a description and
  placeholder value (no real values).
- config/templates/.env.example — Same, as a template.

**What is NEVER committed:**
- .env — Contains real values. Always in .gitignore.
- API keys, tokens, passwords in any source or config file.
- Database connection strings with credentials.

**Physical secret locations (outside the repository):**
- Local development: .env file in the repository root (gitignored).
- CI/CD: GitHub Actions secrets (configured in repository settings).
- Production VPS: Environment variables set on the host.

**Documented secrets (in .env.example):**

| Variable | Description | Required For |
|----------|-------------|-------------|
| IIOS_FEED_DHAN_TOKEN | Dhan API access token | Live data |
| IIOS_BROKER_DHAN_CLIENT_ID | Dhan client ID | Live trading |
| IIOS_TELEGRAM_BOT_TOKEN | Telegram bot token | Notifications |
| IIOS_TELEGRAM_CHAT_ID | Telegram chat/channel ID | Notifications |
| IIOS_DB_ENCRYPTION_KEY | Database encryption key | Data security |

---

### 6.5 Feature Flag Physical Organization

Feature flags control behavior at runtime without code changes. They are committed
to the repository (they are boolean configuration, not secrets).

`
config/feature_flags/
|-- README.md                         # Feature flag documentation
|-- flags.yaml                        # Active feature flags
|-- schema.py                         # FeatureFlag dataclass definition
`

**flags.yaml structure:**
`yaml
feature_flags:
  enable_live_trading:
    default: false
    description: "Enable real order execution via broker"
    introduced: "1.0.0"
    
  enable_telegram_alerts:
    default: true
    description: "Send trade alerts via Telegram"
    introduced: "1.0.0"
    
  enable_continuous_scan:
    default: true
    description: "Run 30-second market monitoring cycles"
    introduced: "1.1.0"
`

---

*End of Part VI*

---

## PART VII — TESTING ORGANIZATION

### 7.1 Testing Philosophy

Tests in IIOS are first-class citizens with the same organizational discipline as
source code. Every test has:
- A canonical location (mirrors source tree)
- A clear scope (unit, integration, system)
- A documented purpose
- Deterministic execution

---

### 7.2 Physical Test Tree

`
tests/
|-- README.md                         # Test suite overview
|-- conftest.py                       # Root pytest configuration + global fixtures
|-- pytest.ini                        # Pytest settings (or in pyproject.toml)
|
|-- unit/                             # Unit tests — isolated, fast, no I/O
|   |-- __init__.py
|   |-- conftest.py                   # Unit test fixtures
|   |
|   |-- core/                         # Tests for core/
|   |   |-- __init__.py
|   |   |-- test_base_engine.py
|   |   |-- test_event_bus.py
|   |   |-- test_health_check.py
|   |   |-- test_ohs.py
|   |   |-- test_registry.py
|   |   |-- test_logger.py
|   |   |-- test_errors.py
|   |
|   |-- domain/                       # Tests for domain/
|   |   |-- __init__.py
|   |   |-- test_entities.py
|   |   |-- test_events.py
|   |   |-- test_values.py
|   |   |-- test_enumerations.py
|   |   |-- test_constants.py
|   |
|   |-- shared/                       # Tests for shared/
|   |   |-- __init__.py
|   |   |-- math/
|   |   |   |-- test_statistics.py
|   |   |   |-- test_indicators.py
|   |   |-- datetime/
|   |   |   |-- test_market_calendar.py
|   |   |   |-- test_session.py
|   |   |-- cache/
|   |   |   |-- test_memory_cache.py
|   |   |-- retry/
|   |       |-- test_retry_policy.py
|   |       |-- test_circuit_breaker.py
|   |
|   |-- engines/                      # Unit tests for all engines
|       |-- __init__.py
|       |-- global_intelligence/
|       |   |-- __init__.py
|       |   |-- conftest.py           # Engine-specific fixtures
|       |   |-- test_global_intelligence.py
|       |   |-- test_components.py
|       |
|       |-- risk_guardian/
|       |   |-- __init__.py
|       |   |-- conftest.py
|       |   |-- test_risk_guardian.py
|       |   |-- test_kill_switch_service.py
|       |   |-- test_kill_switch_policy.py
|       |   |-- test_vix_processor.py
|       |   |-- test_loss_processor.py
|       |
|       |-- [one directory per engine]
|
|-- integration/                      # Integration tests — cross-component
|   |-- __init__.py
|   |-- conftest.py                   # Integration fixtures (mock event bus, etc.)
|   |
|   |-- decision_cycle/               # End-to-end decision cycle tests
|   |   |-- __init__.py
|   |   |-- test_observation_to_decision.py
|   |   |-- test_decision_to_execution.py
|   |   |-- test_full_cycle.py
|   |
|   |-- kill_switch/                  # Kill switch integration tests
|   |   |-- __init__.py
|   |   |-- test_vix_kill_trigger.py
|   |   |-- test_loss_kill_trigger.py
|   |   |-- test_recovery_from_kill.py
|   |
|   |-- learning/                     # Learning system integration tests
|   |   |-- __init__.py
|   |   |-- test_session_learning.py
|   |   |-- test_strategy_adaptation.py
|   |
|   |-- governance/                   # Governance integration tests
|       |-- __init__.py
|       |-- test_certification_cycle.py
|       |-- test_authorization_flow.py
|
|-- regression/                       # Regression tests — prevent known bugs
|   |-- README.md                     # Index of what each regression test catches
|   |-- __init__.py
|   |-- conftest.py
|   |-- test_constant_scope_bug.py    # RE: user memory patterns.md
|   |-- test_strategy_rr_filter.py    # RE: bug in strategy_generator_ai
|   |-- test_eod_recovery.py          # RE: zero-count post-restart bug
|   |-- [test_[slug].py per bug]
|
|-- simulation/                       # Simulation tests — paper trading mode
|   |-- __init__.py
|   |-- conftest.py
|   |-- test_paper_trade_cycle.py     # Full paper trading cycle
|   |-- test_paper_pnl_accuracy.py    # P&L calculation accuracy
|   |-- test_paper_position_limits.py # Position limit enforcement
|
|-- performance/                      # Performance benchmarks
|   |-- __init__.py
|   |-- conftest.py
|   |-- test_decision_cycle_latency.py  # Target: 172ms
|   |-- test_knowledge_cache_speed.py   # Target: < 5ms read
|   |-- test_event_bus_throughput.py    # Target: > 1000 events/sec
|   |-- test_ohs_computation_speed.py   # Target: < 10ms
|
|-- security/                         # Security tests
|   |-- __init__.py
|   |-- test_log_sanitization.py      # No credentials in logs
|   |-- test_input_validation.py      # Boundary/invalid input handling
|   |-- test_sql_injection.py         # Parameterized query verification
|   |-- test_path_traversal.py        # Path traversal prevention
|
|-- ai_validation/                    # AI/ML-specific validation tests
|   |-- __init__.py
|   |-- test_prediction_consistency.py  # Prediction outputs are consistent
|   |-- test_learning_stability.py      # Learning doesn't diverge
|   |-- test_strategy_fitness.py        # Strategy fitness functions
|
|-- acceptance/                       # Acceptance tests — business criteria
|   |-- __init__.py
|   |-- conftest.py
|   |-- test_daily_loss_limit.py      # 2% daily loss enforced
|   |-- test_kill_switch_stops_trading.py
|   |-- test_paper_mode_no_real_orders.py
|   |-- test_governance_blocks_uncertified.py
|
|-- fixtures/                         # Shared test fixtures
|   |-- __init__.py
|   |-- market_data.py                # Market data fixtures
|   |-- domain_objects.py             # Domain object constructors
|   |-- engine_mocks.py               # Mock engine implementations
|   |-- event_bus_mock.py             # Mock event bus
|   |-- config_fixtures.py            # Test configuration fixtures
|
|-- utils/                            # Test utilities
|   |-- __init__.py
|   |-- assertions.py                 # Custom assertion utilities
|   |-- builders.py                   # Test data builders
|   |-- generators.py                 # Random data generators
|   |-- comparators.py                # Complex object comparison utilities
|
|-- reports/                          # Test reports (gitignored, runtime)
|   |-- coverage/                     # Coverage HTML reports
|   |-- performance/                  # Performance benchmark results
|   |-- security/                     # Security scan results
`

---

### 7.3 Test Data Organization

`
tests/fixtures/
|-- data/
|   |-- market_data/                  # Sample OHLCV data files
|   |   |-- nifty_sample.csv
|   |   |-- banknifty_sample.csv
|   |   |-- equity_sample.csv
|   |
|   |-- option_chains/                # Sample option chain snapshots
|   |   |-- nifty_chain_sample.json
|   |
|   |-- global_data/                  # Sample global intelligence data
|   |   |-- sp500_sample.csv
|   |   |-- vix_sample.csv
|   |
|   |-- decisions/                    # Sample decision records
|   |   |-- approved_decision.json
|   |   |-- rejected_decision.json
|   |
|   |-- strategies/                   # Sample strategy definitions
|       |-- valid_strategy.json
|       |-- invalid_strategy.json
`

---

*End of Part VII*

---
## PART VIII — REPOSITORY GROWTH STRATEGY

### 8.1 The Non-Reorganization Principle

The most important property of the repository growth strategy is that the top-level
structure must never need reorganization. A reorganization at scale (thousands of
files, dozens of engineers) is enormously expensive: all references must be updated,
all tooling must be reconfigured, all documentation must be updated, all team members
must adapt. The structure defined in this document is designed to absorb the expected
growth of IIOS without reorganization at any point in its 20-year life.

The mechanism is simple: every growth dimension has a pre-defined place.

- New engines go in engines/ as new sibling directories.
- New shared utilities go in shared/[category]/.
- New domain types go in domain/[category]/.
- New tests mirror the source structure they test.
- New documentation goes in the appropriate docs/ subdirectory.
- New deployment configurations go in deployment/environments/.

There is never a "where does this go?" question that requires structural invention.

---

### 8.2 Year 1 — Foundation Phase

**Starting state:** ~18 engine packages, ~50 modules in core/shared/domain,
~200 test files, ~30 documentation files.

**Expected growth:**
- 3–5 new agents added within existing engines.
- 5–10 new shared utilities added as patterns emerge.
- 20+ ADRs as architectural decisions are formalized.
- All 18 operational runbooks written and tested.
- 500+ test cases.

**What changes in structure:**
- New modules added within existing engine packages.
- New utilities added in shared/.
- ADR directory grows from ~5 to ~25.
- Runbook directory grows from ~5 to ~18.

**What does NOT change:**
- Top-level directory structure.
- Engine package names.
- Core library structure.
- Naming conventions.

**Year 1 size estimate:**
- ~250 Python modules
- ~40,000 lines of source code
- ~600 test cases
- ~60 documentation files

---

### 8.3 Year 3 — Growth Phase

**Expected growth:**
- 2–4 new engines (new intelligence capabilities or new market capabilities).
- Engine internal complexity growth (more components, more services).
- Dataset growth (3 years of market data).
- Documentation maturity (tutorials, developer guides completed).
- Research activity increases (10+ research papers integrated).

**What changes in structure:**
- New engine packages added to engines/.
- datasets/ grows significantly.
- esearch/ grows with accumulated literature.
- experiments/ grows with completed/archived experiments.
- rchive/ begins to accumulate superseded implementations.

**Scaling test:**
`
At Year 3, the repository should have:
  engines/          → 22+ engine packages (flat, no nesting)
  datasets/         → 3 years of market data (gitignored)
  docs/             → 100+ documents
  tests/            → 1,500+ test cases
  archive/          → 3+ archived experiments
`

**Year 3 size estimate:**
- ~500 Python modules
- ~80,000 lines of source code
- ~1,500 test cases
- ~120 documentation files

---

### 8.4 Year 5 — Maturity Phase

**Expected growth:**
- 5–10 additional engines (new asset classes, new intelligence layers).
- First consideration of microservice extraction for high-traffic engines.
- Multi-deployment environment support (cloud provider, on-premise options).
- Formalized research pipeline (experiments → datasets → engine improvements).

**What changes in structure:**
- deployment/kubernetes/ becomes active (was placeholder).
- deployment/helm/ becomes active.
- New deployment/cloud/ subdirectory added.
- 2–3 archived engines (superseded implementations).
- engines/ has 25–30 packages.

**Microservice consideration:**
When an engine is extracted to a microservice, its source code remains in engines/.
A new adapter appears in the engine's dapters/ directory for the network interface.
The engine's physical directory structure does not change.

**Year 5 size estimate:**
- ~800 Python modules
- ~130,000 lines of source code
- ~3,000 test cases
- ~200 documentation files

---

### 8.5 Year 10 — Scale Phase

**Expected growth:**
- 30–50 engine packages.
- Multiple asset class coverage (equities, derivatives, commodities).
- Multiple market coverage (NSE, BSE, potentially global markets).
- Distributed deployment fully operational.
- Rich accumulated archive (10 years of superseded implementations).

**What changes in structure:**
- engines/ has 30–50 packages (still flat — the flat structure scales).
- datasets/ has 10 years of market data (volume managed by data retention policy).
- rchive/ has 20+ archived items.
- Documentation system may evolve to a documentation site (mkdocs builds from docs/).

**What does NOT change:**
- The flat engine package structure.
- The naming conventions.
- The dependency direction rules.
- The test mirroring convention.
- The core/ and domain/ stability model.

---

### 8.6 Year 20 — Legacy Management Phase

**Expected state:**
- 50–100 engine packages.
- Some engines are 10+ years old with deep institutional knowledge encoded in their
  documentation and tests.
- Multiple generations of developers have contributed.
- 5–10 complete architectural generations archived.

**What the structure does for long-term maintainability:**
- docs/decisions/ has 100+ ADRs documenting every significant decision made
  across 20 years. A new engineer can trace the entire architectural evolution.
- rchive/ has organized records of every superseded implementation, each with
  an ARCHIVED.md explaining why it was retired and what replaced it.
- engines/ has a flat directory of 50–100 packages, each self-contained with
  its own README.md, CHANGELOG.md, and internal documentation.
- The naming conventions from Year 1 are still valid — a test file created in
  Year 1 is still named and organized the same way as a test file created in Year 20.

**The 20-year invariant:**
The structure defined in this document remains valid at Year 20 because:
1. All growth is additive (new directories and files, not reorganization).
2. Naming conventions are dimensional (engine count growth adds directories,
   not new naming schemes).
3. The flat engine structure accommodates hundreds of packages without nesting.
4. Documentation accumulates without restructuring because ADRs, runbooks, and
   tutorials are individually additive.

---

### 8.7 Scaling Without Reorganization — Pattern Analysis

Five specific growth scenarios and how the structure handles them:

**Scenario 1 — 100 Engine Packages**
The engines/ directory has 100 sibling packages. Navigation is by name (IDE
file finder) and documentation (engine catalog in docs/architecture/). No
subdirectory grouping is required because IDE tooling makes flat-large directories
navigable.

**Scenario 2 — 10,000 Test Cases**
Tests mirror the source structure. With 10,000 tests across 100 engines, each
engine has ~100 test cases in its own test directory. No restructuring needed.
CI runs tests in parallel by engine package.

**Scenario 3 — 500 ADRs**
The docs/decisions/ directory has 500 .md files, each numbered sequentially.
The README.md in the directory is the index. Search (by number or keyword) finds
any ADR in seconds.

**Scenario 4 — 50 Engineers**
The CODEOWNERS file maps each of 50+ engine packages to its owners. Each engineer
knows their packages and the rules. The structure enforces the same conventions for
all 50 engineers without coordination.

**Scenario 5 — Multiple Deployment Targets**
The deployment/ directory adds new target subdirectories. Existing deployment
configurations are unchanged. The deployment structure is extensible by addition.

---

*End of Part VIII*

---

## PART IX — REPOSITORY CONSTITUTION

### 9.1 Constitution Overview

The Physical Repository Constitution contains 100 rules governing the physical
organization of the IIOS repository. Rules are classified:

**[H] — HARD:** CI-enforced. Violation blocks merge.
**[S] — SOFT:** Warning triggered. Requires documented justification.
**[A] — ADVISORY:** Best practice. Encouraged.

---

### Category 1 — Root Organization (PHYS-ROOT-001 through PHYS-ROOT-010)

**PHYS-ROOT-001 [H]:** The repository root contains exactly the files listed in
Part II Section 2.1. No additional files at the root. A file that belongs somewhere
else must be moved, not left at the root for convenience.

**PHYS-ROOT-002 [H]:** main.py is the single entry point. No other Python file
at the root may be executed as a program entry point.

**PHYS-ROOT-003 [H]:** config.py is the single global configuration module at
the root. All other configuration lives in config/.

**PHYS-ROOT-004 [H]:** .env is always in .gitignore. It is never committed.
Only .env.example is committed.

**PHYS-ROOT-005 [H]:** .gitattributes enforces LF line endings for all text files.
This ensures cross-platform consistency between Windows development and Linux deployment.

**PHYS-ROOT-006 [H]:** docker-compose.yml at the root is the canonical development
and production compose file. Alternative compose files live in deployment/docker/.

**PHYS-ROOT-007 [S]:** README.md at the root contains: system overview, quick-start
instructions (< 5 steps), link to full documentation, and status badges from CI.

**PHYS-ROOT-008 [H]:** CHANGELOG.md uses Keep-a-Changelog format. Every version
section has an ISO date. Unreleased changes are in an [Unreleased] section.

**PHYS-ROOT-009 [H]:** .secrets.baseline is kept up-to-date. The secret scanner
baseline is reviewed whenever a new string pattern is added that might false-positive.

**PHYS-ROOT-010 [S]:** Root-level Markdown files other than README.md, ARCHITECTURE.md,
and CHANGELOG.md are justified by an ADR explaining why they cannot live in docs/.

---

### Category 2 — Engine Directory Organization (PHYS-ENG-001 through PHYS-ENG-015)

**PHYS-ENG-001 [H]:** Every engine is a direct child of engines/. No engine is nested
inside another engine's directory.

**PHYS-ENG-002 [H]:** Every engine package has: __init__.py, [name].py,
README.md, components/ or equivalent subdivision, config/defaults.py.
An engine missing any of these fails the repository readiness check.

**PHYS-ENG-003 [H]:** Engine package names match the IIOS engine catalog. The
canonical names are defined in the engine catalog (Supplement B).

**PHYS-ENG-004 [H]:** No Python file in an engine's directory imports from another
engine's directory except through the other engine's __init__.py (public interface).

**PHYS-ENG-005 [S]:** Every engine has a documentation/ subdirectory with at
minimum a DESIGN.md explaining the engine's internal design decisions.

**PHYS-ENG-006 [H]:** Every engine has a governance/ subdirectory with an
udit_logger.py that implements the audit logging protocol.

**PHYS-ENG-007 [S]:** Every engine has a uture/ subdirectory (even if empty)
with a README.md listing planned capabilities or stating "No planned extensions."

**PHYS-ENG-008 [H]:** Engine __init__.py has an __all__ list that explicitly
names every exported symbol. Implicit exports via star import are forbidden.

**PHYS-ENG-009 [S]:** Engine package versions in __init__.py are maintained
independently from the system version in pyproject.toml.

**PHYS-ENG-010 [H]:** The isk_guardian/ engine is a protected module. Its
kill_switch_policy.py may only be modified with explicit Architecture Council
sign-off. A CODEOWNERS rule enforces review.

**PHYS-ENG-011 [S]:** Engine documentation/DESIGN.md is updated whenever a
significant internal change is made. An engine with a DESIGN.md that hasn't been
updated in 12 months but has had source changes is flagged for documentation review.

**PHYS-ENG-012 [H]:** Engine examples in examples/ are executable without
modification. CI runs example scripts and confirms they exit 0.

**PHYS-ENG-013 [S]:** The uture/ directory contains planned features as
specification documents, not as commented-out code. Commented-out code is deleted.

**PHYS-ENG-014 [H]:** No test files exist inside the engine's directory. Tests for
the engine live in 	ests/unit/engines/[engine_name]/.

**PHYS-ENG-015 [S]:** Engine alidators/ exists and contains at minimum
input_validator.py for any engine that accepts external data.

---

### Category 3 — Core Library Organization (PHYS-CORE-001 through PHYS-CORE-010)

**PHYS-CORE-001 [H]:** core/ contains only infrastructure code. No business logic,
no investment decision logic, no market-data-specific code.

**PHYS-CORE-002 [H]:** core/ has zero imports from engines/, shared/, or
domain/. The CI dependency validator confirms this.

**PHYS-CORE-003 [H]:** Every module in core/ has 100% docstring coverage on public
symbols. This is enforced by CI.

**PHYS-CORE-004 [H]:** Changes to core/ are reviewed by at least two Architecture
Council members. The CODEOWNERS file enforces this.

**PHYS-CORE-005 [S]:** core/ changes are accompanied by a migration guide if
they affect any interface.

**PHYS-CORE-006 [H]:** The core/engine/base_engine.py lifecycle protocol may not
be changed in a way that breaks existing engine implementations. Breaking changes
require a deprecation cycle.

**PHYS-CORE-007 [H]:** core/health/ohs.py OHS tier thresholds (OPTIMAL, NOMINAL,
DEGRADED, CRITICAL, FAILED) are treated as constitutional constants. Changes require
an ADR.

**PHYS-CORE-008 [H]:** core/logging/sanitizer.py must be applied to all log output.
A test in 	ests/security/test_log_sanitization.py confirms no sensitive values
appear in log output.

**PHYS-CORE-009 [S]:** The total number of modules in core/ does not exceed 30.
If more are needed, the structure is reviewed for possible extraction to shared/.

**PHYS-CORE-010 [A]:** Core modules are designed for the general case, not for IIOS-
specific behavior. A core module that references engine-specific logic is a design error.

---

### Category 4 — Documentation Organization (PHYS-DOC-001 through PHYS-DOC-010)

**PHYS-DOC-001 [H]:** Every directory in docs/ has a README.md that lists its
contents and provides navigation guidance.

**PHYS-DOC-002 [H]:** Architecture documents have document codes following the pattern
IIOS-[DOMAIN]-[TYPE]-[NNN].

**PHYS-DOC-003 [H]:** ADRs are numbered sequentially in docs/decisions/ and the
README.md in that directory contains a table of all ADRs.

**PHYS-DOC-004 [S]:** ADRs are created within 5 business days of a significant
architectural decision being made. An architectural decision without an ADR is
a governance violation.

**PHYS-DOC-005 [H]:** Operational runbooks follow the naming convention
RB-[CATEGORY]-[NNN]-[slug].md and the mandatory section structure.

**PHYS-DOC-006 [S]:** Runbooks are tested quarterly. A runbook not tested in 6 months
is flagged as potentially stale.

**PHYS-DOC-007 [H]:** Superseded documents are not deleted. They are moved to
docs/archive/ with an ARCHIVED.md notice pointing to the successor.

**PHYS-DOC-008 [H]:** Documentation files contain no Python code, configuration
secrets, or database schemas. Documentation is documentation.

**PHYS-DOC-009 [S]:** Each engine's documentation/ subdirectory has at minimum
DESIGN.md and INTERFACE.md. The engine is not considered fully documented
without these.

**PHYS-DOC-010 [A]:** Documentation diagrams are stored in the same directory as
the document that references them, named [document-slug]-[diagram-name].[ext].

---

### Category 5 — Test Organization (PHYS-TEST-001 through PHYS-TEST-010)

**PHYS-TEST-001 [H]:** All test files live under 	ests/. No test files exist inside
source packages. The presence of a 	est_*.py file outside 	ests/ fails CI.

**PHYS-TEST-002 [H]:** The 	ests/ directory structure mirrors the source structure.
engines/risk_guardian/ has a corresponding 	ests/unit/engines/risk_guardian/.

**PHYS-TEST-003 [H]:** Every public method of every engine's public interface has
at least one unit test in 	ests/unit/engines/[engine_name]/.

**PHYS-TEST-004 [H]:** Test files are named 	est_[module_being_tested].py.
The name matches the source module exactly, prefixed with 	est_.

**PHYS-TEST-005 [H]:** 	ests/regression/ contains a named test for every bug
that has been fixed in production. Bug fixes without a regression test are not
merged.

**PHYS-TEST-006 [S]:** 	ests/acceptance/ contains tests for every business rule
in the IIOS constitution (NNH rules). A constitutional rule without an acceptance
test is flagged.

**PHYS-TEST-007 [H]:** Test fixtures in 	ests/fixtures/ are not imported by
application code. Fixtures are test-only artifacts.

**PHYS-TEST-008 [H]:** 	ests/performance/ benchmark tests define explicit timing
targets. A benchmark without a defined target is not meaningful.

**PHYS-TEST-009 [S]:** Integration tests in 	ests/integration/ use mocked external
systems (data feeds, broker API). No integration test makes real API calls.

**PHYS-TEST-010 [S]:** 	ests/security/ has tests for each security rule in the
IIOS Security Engineering specification.

---

### Category 6 — Configuration Organization (PHYS-CFG-001 through PHYS-CFG-010)

**PHYS-CFG-001 [H]:** All environment-specific configuration lives in
config/environments/. No environment-specific values are hardcoded in source files.

**PHYS-CFG-002 [H]:** Every engine has a configuration dataclass in
config/engines/[engine_name]_config.py with all configurable parameters documented.

**PHYS-CFG-003 [H]:** .env.example documents every environment variable the system
uses. An environment variable used in code but not in .env.example fails CI.

**PHYS-CFG-004 [H]:** No real secrets appear in any committed file. The secret scanner
confirms this on every PR.

**PHYS-CFG-005 [S]:** Feature flags in config/feature_flags/flags.yaml have a
description and introduced version for every flag.

**PHYS-CFG-006 [H]:** Configuration profiles in config/profiles/ override only
the values they are designed to override. They do not duplicate base configuration.

**PHYS-CFG-007 [H]:** Configuration is validated at startup by config/config_validator.py.
A missing required configuration value causes startup to fail with a clear message.

**PHYS-CFG-008 [S]:** Configuration values for kill switch thresholds (VIX limit,
daily loss limit, drawdown limit) are centralized in config/environments/base.yaml
and referenced by name from engine configurations. They are not duplicated.

**PHYS-CFG-009 [H]:** config/environments/production.yaml never relaxes risk
limits compared to ase.yaml. Production limits are equal to or tighter than
base limits.

**PHYS-CFG-010 [A]:** A developer reading .env.example alone should understand
what every environment variable does, its expected format, and whether it is required
or optional.

---

### Category 7 — Data and Resources Organization (PHYS-DATA-001 through PHYS-DATA-010)

**PHYS-DATA-001 [H]:** The data/ directory is always in .gitignore. Runtime-
generated data is never committed.

**PHYS-DATA-002 [H]:** data/databases/ SQLite files are never committed. Schema
migrations exist in scripts/migrations/.

**PHYS-DATA-003 [S]:** datasets/ files larger than 100MB use Git LFS. Files
larger than 500MB use an external data store with a reference file in the repository.

**PHYS-DATA-004 [H]:** esources/ files are static and versioned with the source
code. Files that change frequently (market calendars) have an explicit update
procedure documented in docs/operations/.

**PHYS-DATA-005 [H]:** esources/models/ contains only serialized ML model
artifacts. Model training code lives in engine source, not in resources/.

**PHYS-DATA-006 [S]:** All files in esources/ are documented in the engine that
uses them. An undocumented resource file is flagged for review.

**PHYS-DATA-007 [H]:** logs/ is in .gitignore. Log files are never committed.

**PHYS-DATA-008 [H]:** cache/ is in .gitignore. Cached data is never committed.

**PHYS-DATA-009 [S]:** datasets/ has a README.md per subdirectory documenting:
data source, update frequency, last update date, and format specification.

**PHYS-DATA-010 [H]:** No file in esources/ contains credentials, API keys, or
other sensitive values.

---

### Category 8 — Deployment Organization (PHYS-DEP-001 through PHYS-DEP-010)

**PHYS-DEP-001 [H]:** The production Docker image tag uses the system version number.
The latest tag is also maintained but the versioned tag is the canonical reference.

**PHYS-DEP-002 [H]:** Dockerfile uses a pinned base image version. Never FROM python:latest.

**PHYS-DEP-003 [H]:** The container runs as a non-root user. The Dockerfile includes
USER appuser (or equivalent) before the CMD instruction.

**PHYS-DEP-004 [H]:** deployment/scripts/deploy_vps.sh performs the complete VPS
deployment: git pull, docker build --no-cache, docker compose down, docker compose up,
health check. No partial deployments.

**PHYS-DEP-005 [H]:** Health checks are defined in Dockerfile using the HEALTHCHECK
instruction. Both containers (i-trading-brain and 	rading-dashboard) have health
checks.

**PHYS-DEP-006 [S]:** deployment/environments/ has a subdirectory for every supported
deployment environment. Each subdirectory has .env.example and config.yaml.

**PHYS-DEP-007 [H]:** No production secrets appear in deployment/environments/.
Secrets are injected at deployment time via environment variables.

**PHYS-DEP-008 [S]:** deployment/kubernetes/ has a README.md even before K8s
manifests are implemented, documenting the planned K8s architecture.

**PHYS-DEP-009 [H]:** CI pipeline definitions in .github/workflows/ use pinned
action versions (ctions/checkout@v4, not ctions/checkout@latest).

**PHYS-DEP-010 [S]:** Deployment scripts in deployment/scripts/ are idempotent.
Running the same deployment script twice has the same result as running it once.

---

### Category 9 — Archive and Experiment Organization (PHYS-ARC-001 through PHYS-ARC-010)

**PHYS-ARC-001 [H]:** All archived items are in rchive/. Nothing is deleted from
the repository without first being archived for at least 90 days.

**PHYS-ARC-002 [H]:** Every item in rchive/ has an ARCHIVED.md file documenting:
why archived, when archived, what replaced it, and who approved the archival.

**PHYS-ARC-003 [H]:** No active source code imports from rchive/. CI confirms.

**PHYS-ARC-004 [H]:** Every item in experiments/ has an experiment.md file
documenting: hypothesis, owner, start date, planned end date.

**PHYS-ARC-005 [H]:** Experiments without experiment.md are deleted at the next
quarterly maintenance cycle (they are given 30 days' notice via a GitHub issue).

**PHYS-ARC-006 [H]:** No active source code imports from experiments/. CI confirms.

**PHYS-ARC-007 [S]:** Experiments that have been "in progress" for more than 90 days
are reviewed. They are either extended (with updated experiment.md) or archived.

**PHYS-ARC-008 [S]:** rchive/ is organized by category (archive/engines/,
archive/strategies/, archive/documents/) for navigability.

**PHYS-ARC-009 [A]:** Before archiving an engine or strategy, a post-mortem document
is written explaining what was learned from the implementation and what informed the
replacement design.

**PHYS-ARC-010 [S]:** Archived items retain their original internal structure. They
are not flattened or reorganized when moved to rchive/.

---

### Category 10 — Growth and Evolution (PHYS-GROW-001 through PHYS-GROW-010)

**PHYS-GROW-001 [H]:** New top-level directories require an ADR documenting the
rationale. The directory structure defined in this document is not extended without
governance.

**PHYS-GROW-002 [H]:** New engine packages are added to engines/ as new sibling
directories. Engines never nest inside other engines.

**PHYS-GROW-003 [H]:** New shared utilities are added to shared/[category]/.
If no appropriate category exists, a new shared/[category]/ is created with
Architecture Council approval.

**PHYS-GROW-004 [S]:** When an engine's internal directory count exceeds 15, the
engine is reviewed for potential split into two engines with narrower responsibilities.

**PHYS-GROW-005 [H]:** The physical repository structure is reviewed against this
specification annually. Non-compliances found during review are remediated within
30 days.

**PHYS-GROW-006 [H]:** Repository structure amendments follow the formal amendment
process in IIOS-REPO-ENG-001 Section RE-04. No unilateral changes to top-level structure.

**PHYS-GROW-007 [S]:** When a subsystem grows to more than 20 engine packages of
similar type, a subdirectory grouping strategy within engines/ is proposed to the
Architecture Council for evaluation.

**PHYS-GROW-008 [H]:** All growth is additive. No existing directory is renamed.
No existing file is moved without a migration note. Renames and moves require an ADR.

**PHYS-GROW-009 [S]:** The total number of files at the repository root is reviewed
quarterly. Root file count creeping beyond 25 triggers a cleanup review.

**PHYS-GROW-010 [A]:** Repository growth is monitored annually against the growth
projections in Part VIII. Significant deviations from projections trigger a structural
review.

---

*End of Part IX — Repository Constitution (100 rules: 60 HARD, 30 SOFT, 10 ADVISORY)*

---

## PART X — REPOSITORY CERTIFICATION

### 10.1 Certification Overview

The Physical Repository Certification (PRC) confirms that the physical structure
complies with the standards defined in this document. Certification is performed:
- Before the first production deployment.
- After any repository reorganization.
- Annually as a maintenance health check.
- After any new engine is added.

| Phase | Name | Gates | Type |
|-------|------|-------|------|
| PRC-01 | Root Structure | 8 | HARD |
| PRC-02 | Engine Packages | 10 | HARD |
| PRC-03 | Core Library | 6 | HARD |
| PRC-04 | Documentation | 8 | HARD |
| PRC-05 | Testing | 8 | HARD |
| PRC-06 | Configuration | 6 | HARD |
| PRC-07 | Data and Resources | 5 | HARD |
| PRC-08 | Deployment | 5 | HARD |
| PRC-09 | Governance | 5 | SOFT |
| PRC-10 | Growth Compliance | 4 | SOFT |

**Total: 65 gates (55 HARD, 10 SOFT)**

---

### PRC-01: Root Structure (8 HARD)

**PRC-01-01 [H]:** All required root files exist (see Part II 2.1).
**PRC-01-02 [H]:** No extra files at root beyond approved list.
**PRC-01-03 [H]:** .env is absent from the repository (never committed).
**PRC-01-04 [H]:** .env.example exists and documents all environment variables.
**PRC-01-05 [H]:** All required top-level directories exist.
**PRC-01-06 [H]:** .gitignore excludes: .env, data/, logs/, cache/, .venv/, __pycache__/.
**PRC-01-07 [H]:** .gitattributes enforces LF line endings.
**PRC-01-08 [H]:** CHANGELOG.md has entries for all tagged versions.

---

### PRC-02: Engine Packages (10 HARD)

**PRC-02-01 [H]:** All 18 canonical IIOS engines have packages in engines/.
**PRC-02-02 [H]:** Every engine has __init__.py, [name].py, README.md.
**PRC-02-03 [H]:** Every engine has config/defaults.py.
**PRC-02-04 [H]:** Every engine has governance/audit_logger.py.
**PRC-02-05 [H]:** Every engine has monitoring/health_provider.py.
**PRC-02-06 [H]:** No engine package is nested inside another engine package.
**PRC-02-07 [H]:** No engine-to-engine internal imports exist (CI dependency validator).
**PRC-02-08 [H]:** Every engine's __init__.py has a non-empty __all__ list.
**PRC-02-09 [H]:** No test files exist inside any engine directory.
**PRC-02-10 [H]:** isk_guardian/ has a CODEOWNERS entry requiring Architecture Council review.

---

### PRC-03: Core Library (6 HARD)

**PRC-03-01 [H]:** All required core/ subdirectories exist (engine, events, health, logging, errors, messaging).
**PRC-03-02 [H]:** core/ has zero imports from engines/, shared/, or domain/.
**PRC-03-03 [H]:** All public symbols in core/ have docstrings (100% coverage).
**PRC-03-04 [H]:** core/health/ohs.py contains the 5 OHS tier constants.
**PRC-03-05 [H]:** core/logging/sanitizer.py exists and is referenced by the logger factory.
**PRC-03-06 [H]:** core/ tests exist in 	ests/unit/core/ with >= 90% coverage.

---

### PRC-04: Documentation (8 HARD)

**PRC-04-01 [H]:** All required docs/ subdirectories exist.
**PRC-04-02 [H]:** Every top-level directory has a README.md.
**PRC-04-03 [H]:** Every engine package has a documentation/ subdirectory with DESIGN.md.
**PRC-04-04 [H]:** At least 5 ADRs exist in docs/decisions/.
**PRC-04-05 [H]:** docs/decisions/README.md is an index of all ADRs.
**PRC-04-06 [H]:** At least 5 operational runbooks exist in docs/operations/.
**PRC-04-07 [H]:** All formal documents have document codes in their headers.
**PRC-04-08 [H]:** docs/archive/ exists for receiving superseded documents.

---

### PRC-05: Testing (8 HARD)

**PRC-05-01 [H]:** All test directories exist: unit/, integration/, regression/, simulation/, performance/, security/, acceptance/.
**PRC-05-02 [H]:** No test files exist outside 	ests/.
**PRC-05-03 [H]:** Every engine has a corresponding test directory under 	ests/unit/engines/.
**PRC-05-04 [H]:** 	ests/regression/ has at least one test (confirm the regression suite is in use).
**PRC-05-05 [H]:** 	ests/acceptance/ has tests for the three kill switch conditions.
**PRC-05-06 [H]:** 	ests/fixtures/ exists with shared fixtures.
**PRC-05-07 [H]:** All tests pass (zero failures).
**PRC-05-08 [H]:** Coverage for core/ and shared/ is >= 90%.

---

### PRC-06: Configuration (6 HARD)

**PRC-06-01 [H]:** config/environments/base.yaml exists with all base configuration.
**PRC-06-02 [H]:** config/environments/production.yaml exists.
**PRC-06-03 [H]:** config/environments/paper.yaml exists.
**PRC-06-04 [H]:** All 18 engine configuration files exist in config/engines/.
**PRC-06-05 [H]:** No real secrets in any committed file (secret scanner confirms).
**PRC-06-06 [H]:** Configuration is validated at startup (startup test confirms).

---

### PRC-07: Data and Resources (5 HARD)

**PRC-07-01 [H]:** data/ is not tracked in git (confirmed via git ls-files).
**PRC-07-02 [H]:** logs/ is not tracked in git.
**PRC-07-03 [H]:** cache/ is not tracked in git.
**PRC-07-04 [H]:** esources/ exists and has a README.md.
**PRC-07-05 [H]:** No credentials or secrets in esources/ files.

---

### PRC-08: Deployment (5 HARD)

**PRC-08-01 [H]:** Dockerfile uses a pinned base image.
**PRC-08-02 [H]:** Container runs as non-root user (Dockerfile confirmed).
**PRC-08-03 [H]:** Both service containers have HEALTHCHECK instructions in Dockerfile.
**PRC-08-04 [H]:** deployment/scripts/deploy_vps.sh exists and is executable.
**PRC-08-05 [H]:** .github/workflows/ has at least pr.yml and main.yml.

---

### PRC-09: Governance (5 SOFT)

**PRC-09-01 [S]:** .github/CODEOWNERS covers all top-level directories.
**PRC-09-02 [S]:** Every engine has a designated owner in CODEOWNERS.
**PRC-09-03 [S]:** At least 3 ADRs document significant structural decisions.
**PRC-09-04 [S]:** Every item in rchive/ has an ARCHIVED.md.
**PRC-09-05 [S]:** Every item in experiments/ has an experiment.md.

---

### PRC-10: Growth Compliance (4 SOFT)

**PRC-10-01 [S]:** Root file count does not exceed 25.
**PRC-10-02 [S]:** No engine package is nested inside another engine.
**PRC-10-03 [S]:** shared/ utilities are each used by >= 2 engines (confirmed by import analysis).
**PRC-10-04 [S]:** The repository structure has been reviewed against this specification
within the last 12 months.

---

*End of Part X*

---
## SUPPLEMENT A — COMPLETE REPOSITORY TREE

This supplement provides the complete repository tree in a single reference view.

`
ai_trading_brain/
|
|-- main.py
|-- config.py
|-- requirements.txt
|-- requirements-dev.txt
|-- requirements.in
|-- pyproject.toml
|-- docker-compose.yml
|-- Dockerfile
|-- README.md
|-- ARCHITECTURE.md
|-- CHANGELOG.md
|-- LICENSE
|-- .gitignore
|-- .env.example
|-- .pre-commit-config.yaml
|-- .gitattributes
|-- .secrets.baseline
|-- mkdocs.yml
|
|-- docs/
|   |-- README.md
|   |-- architecture/
|   |   |-- README.md
|   |   |-- IIOS_INTEGRATION_AND_OPERATIONAL_ARCHITECTURE.md
|   |   |-- IIOS_MASTER_ORCHESTRATOR_ARCHITECTURE.md
|   |   |-- engines/
|   |   |   |-- README.md
|   |   |   |-- [18 engine architecture docs]
|   |   |-- ontologies/
|   |   |   |-- [8 ontology docs]
|   |   |-- workflows/
|   |   |   |-- IIOS_WORKFLOW_CATALOGUE.md
|   |   |-- layers/
|   |   |   |-- [17 layer docs]
|   |   |-- archive/
|   |
|   |-- engineering/
|   |   |-- README.md
|   |   |-- REPOSITORY_ENGINEERING.md
|   |   |-- PHYSICAL_REPOSITORY_STRUCTURE.md
|   |   |-- IIOS_CODE_STANDARDS.md
|   |   |-- IIOS_TEST_STANDARDS.md
|   |   |-- IIOS_SECURITY_STANDARDS.md
|   |   |-- IIOS_DEPLOYMENT_STANDARDS.md
|   |
|   |-- decisions/
|   |   |-- README.md
|   |   |-- ADR-001-engine-isolation.md
|   |   |-- ADR-002-event-bus-protocol.md
|   |   |-- ADR-003-domain-type-separation.md
|   |   |-- ADR-004-paper-trading-mode.md
|   |   |-- ADR-005-dhan-yfinance-fallback.md
|   |   |-- ADR-006-kill-switch-thresholds.md
|   |   |-- ADR-007-decision-score-threshold.md
|   |   |-- ADR-008-knowledge-cache-ttl.md
|   |   |-- [continuing sequentially]
|   |
|   |-- operations/
|   |   |-- README.md
|   |   |-- RB-DEPLOY-001-vps-deployment.md
|   |   |-- RB-DEPLOY-002-docker-rebuild.md
|   |   |-- RB-OPS-001-daily-startup.md
|   |   |-- RB-OPS-002-daily-shutdown.md
|   |   |-- RB-OPS-003-emergency-stop.md
|   |   |-- RB-OPS-004-kill-switch-response.md
|   |   |-- RB-MAINT-001-daily-log-review.md
|   |   |-- RB-INCIDENT-001-data-feed-failure.md
|   |   |-- RB-RECOVERY-001-full-system-recovery.md
|   |
|   |-- standards/
|   |   |-- README.md
|   |   |-- naming_conventions.md
|   |   |-- code_style_reference.md
|   |   |-- documentation_standards.md
|   |   |-- testing_standards.md
|   |   |-- security_standards.md
|   |
|   |-- migrations/
|   |-- tutorials/
|   |   |-- getting_started.md
|   |   |-- adding_a_new_engine.md
|   |   |-- adding_a_new_strategy.md
|   |
|   |-- developer_guides/
|   |   |-- local_development_setup.md
|   |   |-- writing_engine_tests.md
|   |   |-- debugging_the_decision_cycle.md
|   |
|   |-- user_guides/
|   |   |-- telegram_bot_commands.md
|   |   |-- reading_the_dashboard.md
|   |
|   |-- reference/
|   |   |-- engine_api_reference.md
|   |   |-- configuration_reference.md
|   |
|   |-- glossaries/
|   |   |-- domain_glossary.md
|   |   |-- technical_glossary.md
|   |
|   |-- archive/
|
|-- engines/
|   |-- README.md
|   |
|   |-- global_intelligence/
|   |   |-- __init__.py
|   |   |-- global_intelligence.py
|   |   |-- README.md
|   |   |-- documentation/
|   |   |-- interfaces/
|   |   |-- models/
|   |   |-- services/
|   |   |-- processors/
|   |   |-- validators/
|   |   |-- adapters/
|   |   |-- workflows/
|   |   |-- policies/
|   |   |-- governance/
|   |   |-- analytics/
|   |   |-- monitoring/
|   |   |-- config/
|   |   |-- resources/
|   |   |-- examples/
|   |   |-- future/
|   |
|   |-- market_intelligence/         [same structure as above]
|   |-- meta_learning/               [same structure]
|   |-- opportunity_engine/          [same structure]
|   |-- strategy_lab/                [same structure]
|   |-- capital_risk_engine/         [same structure]
|   |-- risk_control/                [same structure]
|   |-- market_simulation/           [same structure]
|   |-- risk_guardian/               [same structure — PROTECTED]
|   |-- debate_and_decision/         [same structure]
|   |-- execution_engine/            [same structure]
|   |-- trade_monitoring/            [same structure]
|   |-- learning_system/             [same structure]
|   |-- performance_analytics/       [same structure]
|   |-- research_lab/                [same structure]
|   |-- validation_engine/           [same structure]
|   |-- control_tower/               [same structure]
|   |-- orchestrator/                [same structure — owned by Architecture Council]
|
|-- core/
|   |-- __init__.py
|   |-- README.md
|   |-- engine/
|   |   |-- base_engine.py
|   |   |-- lifecycle.py
|   |   |-- registry.py
|   |   |-- status.py
|   |   |-- protocol.py
|   |-- events/
|   |   |-- bus.py
|   |   |-- event.py
|   |   |-- dispatcher.py
|   |   |-- subscriber.py
|   |   |-- filters.py
|   |-- health/
|   |   |-- health_check.py
|   |   |-- ohs.py
|   |   |-- status.py
|   |   |-- reporter.py
|   |-- logging/
|   |   |-- logger.py
|   |   |-- formatters.py
|   |   |-- handlers.py
|   |   |-- sanitizer.py
|   |   |-- context.py
|   |-- errors/
|   |   |-- base_errors.py
|   |   |-- engine_errors.py
|   |   |-- data_errors.py
|   |   |-- governance_errors.py
|   |-- messaging/
|   |   |-- router.py
|   |   |-- serializer.py
|   |   |-- envelope.py
|   |-- registry/
|   |   |-- engine_registry.py
|   |   |-- capability.py
|   |-- config/
|   |   |-- loader.py
|   |   |-- validator.py
|   |   |-- schema.py
|   |-- tracing/
|   |   |-- tracer.py
|   |   |-- span.py
|   |-- security/
|       |-- sanitizer.py
|       |-- validator.py
|
|-- domain/
|   |-- __init__.py
|   |-- README.md
|   |-- entities/
|   |   |-- market_entity.py
|   |   |-- strategy_entity.py
|   |   |-- agent_entity.py
|   |   |-- position_entity.py
|   |   |-- trade_entity.py
|   |-- events/
|   |   |-- market_events.py
|   |   |-- decision_events.py
|   |   |-- risk_events.py
|   |   |-- system_events.py
|   |   |-- learning_events.py
|   |-- values/
|   |   |-- price.py
|   |   |-- quantity.py
|   |   |-- signal.py
|   |   |-- score.py
|   |   |-- budget.py
|   |-- enumerations/
|   |   |-- regime.py
|   |   |-- order_types.py
|   |   |-- asset_class.py
|   |   |-- engine_status.py
|   |   |-- decision_outcome.py
|   |-- constants/
|   |   |-- market_hours.py
|   |   |-- thresholds.py
|   |   |-- symbols.py
|   |-- protocols/
|       |-- observable.py
|       |-- serializable.py
|       |-- identifiable.py
|
|-- shared/
|   |-- __init__.py
|   |-- README.md
|   |-- math/
|   |   |-- statistics.py
|   |   |-- indicators.py
|   |   |-- normalization.py
|   |-- stats/
|   |   |-- distributions.py
|   |   |-- sampling.py
|   |   |-- hypothesis.py
|   |-- datetime/
|   |   |-- market_calendar.py
|   |   |-- session.py
|   |   |-- formatting.py
|   |-- io/
|   |   |-- file_utils.py
|   |   |-- path_utils.py
|   |   |-- csv_utils.py
|   |   |-- json_utils.py
|   |-- cache/
|   |   |-- memory_cache.py
|   |   |-- disk_cache.py
|   |   |-- cache_key.py
|   |-- retry/
|   |   |-- retry_policy.py
|   |   |-- circuit_breaker.py
|   |   |-- backoff.py
|   |-- serial/
|   |   |-- json_serial.py
|   |   |-- pickle_serial.py
|   |   |-- schema_serial.py
|   |-- validation/
|   |   |-- type_validators.py
|   |   |-- range_validators.py
|   |   |-- schema_validators.py
|   |-- formatting/
|   |   |-- number_formatting.py
|   |   |-- table_formatting.py
|   |   |-- report_formatting.py
|   |-- collections/
|   |   |-- ring_buffer.py
|   |   |-- sorted_list.py
|   |   |-- time_series.py
|   |-- concurrency/
|   |   |-- thread_safe.py
|   |   |-- lock_manager.py
|   |-- telemetry/
|       |-- metrics.py
|       |-- counters.py
|       |-- timers.py
|
|-- config/
|   |-- README.md
|   |-- __init__.py
|   |-- global_config.py
|   |-- config_loader.py
|   |-- config_validator.py
|   |-- environments/
|   |   |-- base.yaml
|   |   |-- production.yaml
|   |   |-- paper.yaml
|   |   |-- development.yaml
|   |   |-- testing.yaml
|   |   |-- ci.yaml
|   |-- engines/
|   |   |-- [18 engine config files]
|   |-- templates/
|   |   |-- .env.example
|   |   |-- base_template.yaml
|   |-- profiles/
|   |   |-- aggressive_trading.yaml
|   |   |-- conservative_trading.yaml
|   |   |-- backtest_mode.yaml
|   |-- feature_flags/
|       |-- README.md
|       |-- flags.yaml
|       |-- schema.py
|
|-- resources/
|   |-- README.md
|   |-- data/
|   |   |-- market_calendars/
|   |   |-- symbol_maps/
|   |   |-- instrument_lists/
|   |   |-- sector_classifications/
|   |-- models/
|   |   |-- meta_learning/
|   |   |-- prediction/
|   |   |-- regime_classifier/
|   |-- templates/
|   |   |-- reports/
|   |   |-- dashboards/
|   |   |-- dossiers/
|   |   |-- notifications/
|   |-- assets/
|       |-- icons/
|       |-- logos/
|
|-- data/                            [GITIGNORED — runtime]
|   |-- databases/
|   |-- paper_trades.csv
|   |-- snapshots/
|   |-- dossiers/
|   |-- positions/
|   |-- checkpoints/
|
|-- datasets/
|   |-- README.md
|   |-- market_data/
|   |-- macro_data/
|   |-- events/
|   |-- labels/
|
|-- logs/                            [GITIGNORED — runtime]
|-- cache/                           [GITIGNORED — runtime]
|
|-- monitoring/
|   |-- README.md
|   |-- prometheus/
|   |-- grafana/
|   |-- alerts/
|
|-- deployment/
|   |-- README.md
|   |-- docker/
|   |-- kubernetes/
|   |-- helm/
|   |-- ci/
|   |-- scripts/
|   |-- environments/
|
|-- scripts/
|   |-- README.md
|   |-- setup/
|   |-- migrations/
|   |-- maintenance/
|   |-- PROD_*.py               [PROD_ prefix = elevated risk]
|
|-- tools/
|   |-- README.md
|   |-- validate_deps.py
|   |-- check_naming.py
|   |-- generate_docs.py
|   |-- analyze_coverage.py
|
|-- research/
|   |-- README.md
|   |-- papers/
|   |-- quantitative/
|   |-- market_studies/
|
|-- experiments/
|   |-- README.md
|   |-- [YYYY-MM]/
|       |-- [experiment-slug]/
|           |-- experiment.md
|
|-- examples/
|   |-- README.md
|   |-- [subsystem examples]
|
|-- benchmarks/
|   |-- README.md
|   |-- [benchmark scripts]
|
|-- tests/
|   |-- README.md
|   |-- conftest.py
|   |-- unit/
|   |   |-- core/
|   |   |-- domain/
|   |   |-- shared/
|   |   |-- engines/
|   |       |-- [one dir per engine]
|   |-- integration/
|   |-- regression/
|   |-- simulation/
|   |-- performance/
|   |-- security/
|   |-- ai_validation/
|   |-- acceptance/
|   |-- fixtures/
|   |-- utils/
|   |-- reports/               [GITIGNORED — runtime]
|
|-- archive/
|   |-- README.md
|   |-- engines/
|   |-- strategies/
|   |-- documents/
|   |-- experiments/
|
|-- .github/
    |-- copilot-instructions.md
    |-- CODEOWNERS
    |-- PULL_REQUEST_TEMPLATE.md
    |-- workflows/
    |   |-- pr.yml
    |   |-- main.yml
    |   |-- release.yml
    |-- ISSUE_TEMPLATE/
    |-- skills/
`

---

*End of Supplement A*

---

## SUPPLEMENT B — DIRECTORY CATALOG

This catalog provides a concise reference for every top-level directory.

| Directory | Purpose | Owner | Committed | Growth Model |
|-----------|---------|-------|-----------|-------------|
| docs/ | All documentation | Arch Council | Yes | Additive |
| engines/ | Engine packages | Per-engine | Yes | New siblings |
| core/ | Infrastructure | Arch Council | Yes | Rare additions |
| domain/ | Domain types | Arch Council | Yes | Additive |
| shared/ | Cross-engine utils | Arch Council | Yes | New categories |
| config/ | Configuration | Arch Council | Yes | New envs/engines |
| esources/ | Static assets | Per-subsystem | Yes | Additive |
| data/ | Runtime data | N/A | No | N/A (runtime) |
| datasets/ | Training data | Arch Council | Partial (small) | Accumulates |
| cache/ | Application cache | N/A | No | N/A (runtime) |
| logs/ | Runtime logs | N/A | No | N/A (runtime) |
| monitoring/ | Observability | Ops Lead | Yes | New dashboards |
| deployment/ | Deploy artifacts | Ops Lead | Yes | New targets |
| docker/ | Docker files | Ops Lead | Yes | New variants |
| scripts/ | Operational scripts | Ops Lead | Yes | Additive |
| 	ools/ | Dev tools | Arch Council | Yes | Additive |
| esearch/ | Academic research | Arch Council | Yes | Accumulates |
| experiments/ | Exploratory work | Per-experimenter | Yes | Time-boxed |
| examples/ | Usage examples | Per-subsystem | Yes | Additive |
| enchmarks/ | Performance tests | Eng Lead | Yes | Additive |
| 	ests/ | All test code | Per-engine | Yes | Mirrors source |
| rchive/ | Inactive artifacts | Arch Council | Yes | Permanent |
| .github/ | GitHub config | Arch Council | Yes | Additive |
| .venv/ | Python venv | N/A | No | N/A (local) |

---

### B.2 Engine Directory Catalog

| Engine | Package Name | Stratum | Protected |
|--------|-------------|---------|-----------|
| Global Intelligence | global_intelligence | 1 | No |
| Market Intelligence | market_intelligence | 2 | No |
| Meta Learning | meta_learning | 3 | No |
| Opportunity Engine | opportunity_engine | 4 | No |
| Strategy Lab | strategy_lab | 5 | No |
| Capital Risk Engine | capital_risk_engine | 6 | No |
| Risk Control | isk_control | 7 | No |
| Market Simulation | market_simulation | 8 | No |
| Risk Guardian | isk_guardian | 9 | YES |
| Debate and Decision | debate_and_decision | 10 | No |
| Execution Engine | execution_engine | 11 | No |
| Trade Monitoring | 	rade_monitoring | 12 | No |
| Learning System | learning_system | 13 | No |
| Performance Analytics | performance_analytics | 14 | No |
| Research Lab | esearch_lab | 15 | No |
| Validation Engine | alidation_engine | 16 | No |
| Control Tower | control_tower | 17 | No |
| Orchestrator | orchestrator | Coord | YES |

---

*End of Supplement B*

---

## SUPPLEMENT C — NAMING EXAMPLES

This supplement provides concrete naming examples for every artifact type.

### C.1 Directory Naming Examples

| Artifact | Correct Name | Incorrect Names |
|----------|-------------|----------------|
| Engine package | isk_guardian | RiskGuardian, isk-guardian, g |
| Engine component dir | components | component, Components, comps |
| Test directory | unit | Unit, unit_tests, unittests |
| Year-month experiment | 2026-07 | 2026_07, July2026, 202607 |
| Config environment | production | Production, prod, PRODUCTION |

---

### C.2 File Naming Examples

| Artifact | Correct Name | Incorrect Names |
|----------|-------------|----------------|
| Engine module | isk_guardian.py | RiskGuardian.py, isk-guardian.py |
| Test file | 	est_risk_guardian.py | RiskGuardianTest.py, 	est-risk_guardian.py |
| Architecture doc | IIOS_RISK_ENGINE_ARCH.md | isk_engine_arch.md, IIOSRiskEngineArch.md |
| ADR | ADR-001-engine-isolation.md | dr_001.md, ADR001.md |
| Runbook | RB-OPS-001-daily-startup.md | daily-startup.md, b_ops_001.md |
| Config file | production.yaml | production.yml, Production.yaml |
| Migration script | 2026-07-04_001_init.py | init_migration.py,  01_init.py |

---

### C.3 Python Symbol Naming Examples

| Symbol Type | Correct | Incorrect |
|-------------|---------|-----------|
| Engine class | RiskGuardianEngine | isk_guardian_engine, RiskGuardian |
| Kill switch method | check_kill_switch() | CheckKillSwitch(), killSwitch() |
| Class constant | MAX_DAILY_LOSS_PCT = 0.02 | max_daily_loss_pct, maxDailyLossPct |
| Error class | KillSwitchTriggeredError | KillSwitchTriggered, kill_switch_error |
| Regime enum | MarketRegime.BULL_TRENDING | MarketRegime.bull_trending, BULL_TRENDING |
| Protected method | _compute_vix_signal() | compute_vix_signal_internal() |
| Test class | TestRiskGuardianEngine | RiskGuardianEngineTest, 	est_risk_guardian |
| Test method | 	est_vix_exceeds_threshold_triggers_kill() | 	est_kill_switch(), 	estVIX() |

---

### C.4 Configuration Naming Examples

| Variable | Correct | Incorrect |
|----------|---------|-----------|
| System env | IIOS_ENV | env, ENVIRONMENT, iios_env |
| Risk threshold | IIOS_RISK_VIX_THRESHOLD | VIX_THRESHOLD, ix |
| Dhan token | IIOS_FEED_DHAN_TOKEN | DHAN_TOKEN, dhan_api_key |
| Paper mode | IIOS_BROKER_PAPER_MODE | PAPER_MODE, paper |
| Telegram | IIOS_TELEGRAM_BOT_TOKEN | TELEGRAM_TOKEN, ot_token |

---

*End of Supplement C*

---

## SUPPLEMENT D — GROWTH EXAMPLES

### D.1 Adding a New Engine — Physical Steps

When a new engine sector_intelligence is added to IIOS:

**Step 1 — Create directory structure:**
`
engines/sector_intelligence/
|-- __init__.py
|-- sector_intelligence.py
|-- README.md
|-- documentation/
|   |-- DESIGN.md
|   |-- INTERFACE.md
|-- interfaces/
|   |-- __init__.py
|   |-- sector_intelligence_interface.py
|   |-- input_types.py
|   |-- output_types.py
|-- models/
|   |-- __init__.py
|-- services/
|   |-- __init__.py
|-- processors/
|   |-- __init__.py
|-- validators/
|   |-- __init__.py
|   |-- input_validator.py
|-- governance/
|   |-- __init__.py
|   |-- audit_logger.py
|-- monitoring/
|   |-- __init__.py
|   |-- health_provider.py
|   |-- metrics_provider.py
|-- config/
|   |-- __init__.py
|   |-- defaults.py
|   |-- schema.py
|-- future/
    |-- README.md
`

**Step 2 — Create test directory:**
`
tests/unit/engines/sector_intelligence/
|-- __init__.py
|-- conftest.py
|-- test_sector_intelligence.py
`

**Step 3 — Create configuration:**
config/engines/sector_intelligence_config.py

**Step 4 — Create ADR:**
docs/decisions/ADR-NNN-sector-intelligence-engine.md

**Step 5 — Update documentation:**
- Add engine to engines/README.md
- Add engine to engine catalog in docs/architecture/engines/
- Update CODEOWNERS with engine owner

---

### D.2 Adding a New Shared Utility — Physical Steps

When a new utility market_breadth.py is needed by both opportunity_engine and
market_intelligence:

**Step 1 — Confirm dual usage:**
Both opportunity_engine and market_intelligence need this utility. It qualifies
for shared/.

**Step 2 — Identify category:**
Market breadth is a statistical measure of market internals. It belongs in
shared/stats/ or shared/math/. Decision: shared/stats/market_breadth.py.

**Step 3 — Create the file:**
shared/stats/market_breadth.py

**Step 4 — Create test:**
	ests/unit/shared/stats/test_market_breadth.py

**Step 5 — Remove from engine utils:**
Delete the existing per-engine copy. Update imports in both engines.

---

### D.3 Repository Growth at Year 5 — File Count Projection

`
Directory              Year 1    Year 3    Year 5    Year 10
docs/                     30        80       150       300
engines/ (dirs)           18        22        28        50
engines/ (py files)      180       400       600     1,200
core/ (py files)          20        22        24        28
domain/ (py files)        20        30        40        60
shared/ (py files)        30        50        70       120
config/ (files)           30        45        60        90
tests/ (py files)        200       600     1,200     2,500
archive/ (items)           0         5        15        40
experiments/ (active)      3         5         3         2
datasets/ (MB)            50       500     2,000    10,000
`

---

*End of Supplement D*

---

## SUPPLEMENT E — ANTI-PATTERNS

Physical repository anti-patterns that the IIOS structure is designed to prevent.

---

### EP-01: The Accretion Root

**Description:** The repository root grows from 20 files to 60 files as scripts,
analysis outputs, temporary fixes, and miscellaneous documents are created at the
root "just for now."

**Harm:** The root becomes a junk drawer. New developers cannot identify the actual
system entry point amid dozens of miscellaneous files.

**Prevention:** PHYS-ROOT-001 and PHYS-ROOT-009 enforce a root whitelist and quarterly
review. The CI pipeline checks that no unlisted files appear at the root.

---

### EP-02: The Nested Engine

**Description:** An engine implementation is placed inside another engine's directory
because "it's used only by this engine."

**Example (wrong):** engines/risk_control/sub_engines/portfolio_engine/

**Harm:** The nested engine cannot be independently extracted to a microservice.
It inherits all the coupling of its parent engine. It cannot be independently tested
with its own lifecycle. It cannot be registered with the Orchestrator as a first-class
engine.

**Prevention:** PHYS-ENG-001 enforces flat engine structure. PHYS-ENG-002 requires
all engines to be direct children of engines/.

---

### EP-03: The Test-Source Tangle

**Description:** Test files are placed adjacent to source files within engine
packages:
`
engines/risk_guardian/
|-- risk_guardian.py
|-- test_risk_guardian.py      # WRONG
|-- kill_switch_service.py
|-- test_kill_switch.py        # WRONG
`

**Harm:** The engine package's public surface is ambiguous — it appears to export
test artifacts. The test suite cannot be easily excluded from deployment. Source
metrics (line count, complexity) are inflated.

**Prevention:** PHYS-TEST-001 and PHYS-ENG-014 enforce that test files live only
in 	ests/.

---

### EP-04: The Shadow Config

**Description:** Configuration values appear in multiple places: some in config/,
some hardcoded in engine source files, some in environment variables without
documentation.

**Example (wrong):** The kill switch VIX threshold appears in:
- config/environments/base.yaml (correct)
- engines/risk_guardian/config/defaults.py as a separate hardcoded constant (wrong)
- A comment in engines/risk_guardian/policies/kill_switch_policy.py (wrong)

**Harm:** When the threshold needs to change, three places must be updated. When
they diverge (as they inevitably do), the system has ambiguous behavior.

**Prevention:** PHYS-CFG-008 centralizes threshold constants. PHYS-CFG-001 defines
config/environments/ as the single source of truth.

---

### EP-05: The Undated Archive

**Description:** The rchive/ directory contains directories and files without
ARCHIVED.md markers. Nobody knows why items were archived, when, or what replaced them.

**Harm:** The archive becomes a mystery. Developers may accidentally try to use
archived code thinking it is still active.

**Prevention:** PHYS-ARC-002 requires ARCHIVED.md for every archived item.
PRC-09-04 checks this during certification.

---

### EP-06: The Infinite Experiment

**Description:** An experiments/ directory fills with experiments that were never
completed, never cleaned up, and never documented. The directory grows from 5 to 50
items over two years, most of which are irrelevant.

**Harm:** The experiments directory loses its signal value — when everything is an
"experiment," it's impossible to identify active work.

**Prevention:** PHYS-ARC-004 and PHYS-ARC-005 require experiment.md and enforce
a 90-day review cycle. Experiments without documentation are deleted.

---

### EP-07: The Direct Dataset Import

**Description:** Engine source files directly reference paths to datasets/
with hardcoded paths:
`python
data = load_csv("/absolute/path/to/datasets/market_data/nifty50/data.csv")
`

**Harm:** The code is not portable. It breaks on any machine with a different
directory layout. It creates an implicit dependency between source code and a
specific file system layout.

**Prevention:** PHYS-DATA-003 mandates that large files use LFS references.
All dataset access goes through a data loading service with configurable paths,
not hardcoded path strings.

---

### EP-08: The Version-Named File

**Description:** Files are versioned by including the version in the filename:
isk_guardian_v1.py, isk_guardian_v2.py, isk_guardian_FINAL.py,
isk_guardian_FINAL_2.py.

**Harm:** Multiple files with similar names cause confusion about which is active.
The version history is duplicated between file names and version control.

**Prevention:** Version control (git) manages file versions. Source files never
include version numbers in their names. Only migration scripts (which are inherently
versioned) include dates in their names.

---

### EP-09: The Uncommitted Test Data

**Description:** Actual trade records, position files, or other sensitive runtime
data end up committed to the repository as "test data."

**Harm:** Sensitive financial data is exposed in version control history. Even if
deleted from the current commit, it remains in history.

**Prevention:** PHYS-DATA-001 through PHYS-DATA-003 ensure data/ is gitignored.
The CI secret scanner would catch committed financial data.

---

### EP-10: The Missing Engine Documentation

**Description:** An engine is implemented and works, but has no README.md,
no DESIGN.md, no INTERFACE.md. The only documentation is in code comments.

**Harm:** The next developer who works on this engine must read all source files
to understand what it does and why it exists. The engine's interface contract is
implicit, not explicit. The engine cannot be properly reviewed without documentation.

**Prevention:** PHYS-ENG-002 requires every engine to have README.md.
PHYS-ENG-005 requires documentation/DESIGN.md. PRC-04-03 checks this in certification.

---

*End of Supplement E*

---

## SUPPLEMENT F — REPOSITORY GLOSSARY

Definitions of terms used specifically in the context of the physical repository structure.

**Adapter:** An engine subdirectory (dapters/) containing modules that translate
between IIOS internal representations and external system interfaces.

**Archive:** The rchive/ directory, containing inactive but preserved artifacts
with ARCHIVED.md documentation.

**Benchmark:** A test in enchmarks/ that measures performance against a defined
target. Distinguished from a performance test in 	ests/performance/ by its role
as an ongoing measurement rather than a CI gate.

**Canonical Home:** The single correct location for a given type of artifact in the
repository. Every artifact has exactly one canonical home.

**Committed:** Tracked by version control (git). Appears in git ls-files. The
opposite of gitignored or runtime-generated.

**Component:** An engine subdirectory (or individual module) implementing a part
of the engine's logic. Internal to the engine. Not independently deployable.

**Configuration inheritance:** The layered system by which engine defaults are
overridden by base configuration, which is overridden by environment configuration,
which is overridden by environment variables.

**Data volume:** In Docker terminology, ./data:/app/data — the mapping of the
host's data/ directory to the container's /app/data. This is how data persists
across container restarts.

**Documentation directory:** The documentation/ subdirectory within an engine
package, containing internal engineering documentation.

**Engine Owner:** The person or team designated as the responsible owner for a
specific engine package. Listed in .github/CODEOWNERS.

**Experiment:** A time-boxed exploratory investigation in experiments/, with a
formal experiment.md documenting its hypothesis, scope, and timeline.

**Feature flag:** A boolean configuration value in config/feature_flags/flags.yaml
that enables or disables system behavior without code deployment.

**Future directory:** The uture/ subdirectory within an engine package,
containing specification documents for planned but not yet implemented capabilities.

**Gitignored:** Excluded from version control by .gitignore. Files that are
gitignored may exist on the filesystem but are not tracked by git.

**Governance directory:** The governance/ subdirectory within an engine package,
containing compliance checking and audit logging logic.

**Mirror structure:** The convention by which the 	ests/ directory structure
mirrors the source directory structure. engines/risk_guardian/ has a corresponding
	ests/unit/engines/risk_guardian/.

**Physical structure:** The actual directory and file organization on disk, as
opposed to the logical architecture (which exists in documentation and design).

**Policy directory:** The policies/ subdirectory within an engine package,
containing replaceable business policy implementations.

**Protected module:** An engine or module designated as requiring Architecture
Council approval for any modification. Currently: isk_guardian/ and orchestrator/.

**Regression test:** A test in 	ests/regression/ that confirms a previously
discovered bug has not returned.

**Repository root:** The top-level directory of the version-controlled repository.
In IIOS: i_trading_brain/.

**Runtime directory:** A directory that exists on the filesystem during operation
but is never committed to version control. Examples: data/, logs/, cache/.

**Service directory:** The services/ subdirectory within an engine package,
containing the engine's core business logic organized as service classes.

**Static asset:** A file in esources/ that is committed to version control
because it is reference data required at runtime, not generated data.

**Stratum:** The vertical layer in the IIOS engine hierarchy (1 through 17, plus
Coordination). A higher-stratum engine consumes from lower-stratum engines.

**Validator directory:** The alidators/ subdirectory within an engine package,
containing input validation and business rule enforcement logic.

**Workflow directory:** The workflows/ subdirectory within an engine package,
containing multi-step process orchestration logic.

---

*End of Supplement F*

---

## DOCUMENT METRICS

| Metric | Value |
|--------|-------|
| Document Code | IIOS-PHYS-REPO-001 |
| Version | 1.0.0 |
| Status | AUTHORITATIVE |
| Parts | 10 (I through X) |
| Supplements | 6 (A through F) |
| Constitutional rules | 100 [60H, 30S, 10A] |
| Certification gates | 65 [55H, 10S] |
| Engine packages defined | 18 |
| Engine subdirectories defined | 16 per engine |
| Top-level directories | 24 |
| Anti-patterns | 10 |
| Glossary entries | 30+ |

---

## AMENDMENT HISTORY

| Version | Date | Change | Author |
|---------|------|--------|--------|
| 1.0.0 | 2026-07-04 | Initial release | Architecture Council |

---

*IIOS-PHYS-REPO-001 Version 1.0.0*
*Investment Intelligence Operating System — Physical Repository Structure*
*Architecture Council — 2026-07-04*
*End of Document.*
---

## SUPPLEMENT G — ENGINE INTERNAL ANATOMY REFERENCE

This supplement provides the complete internal anatomy specification for each of the
18 IIOS engine packages. Each section defines every subdirectory and its purpose,
the mandatory files, and the content rules.

---

### G.1 Global Intelligence Engine — engines/global_intelligence/

The Global Intelligence Engine collects and processes overnight global market signals
from international equity indices, bond markets, currency pairs, and commodity markets.
It provides a consolidated GlobalSnapshot object to Layer 2 engines.

**Mandatory subdirectory contents:**

interfaces/
- global_intelligence_interface.py — Abstract base class defining the engine's
  public API. Contains etch(force: bool = False) -> GlobalSnapshot.
- input_types.py — Input dataclasses: GlobalFetchRequest.
- output_types.py — Output dataclasses: GlobalSnapshot, GlobalMarketData,
  RegionalSignal, FXSignal, BondSignal.

models/
- global_snapshot.py — The GlobalSnapshot dataclass: contains regional signals
  from US, Europe, Asia-Pacific, plus bond yields, USD index, commodity signals.
- egional_signal.py — Per-region market signal aggregated from index movements.
- signal_aggregator.py — Aggregation logic converting raw feeds to regional signals.

services/
- global_data_ai.py — Core service implementing multi-source data collection.
  Queries yfinance for S&P 500, NASDAQ, Nikkei, Hang Seng, DAX, FTSE.
  Contains 5-minute caching with background pre-warm thread.
- cache_service.py — In-process caching layer for global snapshots.
  Cache TTL is 300 seconds (5 minutes). Thread-safe.
- pre_warm_service.py — Background pre-warming thread. Starts at engine startup
  and refreshes cache before TTL expiry.

processors/
- signal_processor.py — Converts raw market data (prices, % changes) into
  directional signals and sentiment scores.
- correlation_processor.py — Computes rolling correlations between global indices
  and NSE performance.
- egime_implication_processor.py — Derives regime implications from global signals.

alidators/
- input_validator.py — Validates fetch request parameters.
- data_validator.py — Validates data completeness from external feeds.
  Handles NaN, stale data (last update > 24 hours), missing instruments.

dapters/
- yfinance_adapter.py — yfinance data source adapter. Maps IIOS symbol names
  to yfinance ticker symbols.
- dhan_adapter.py — Dhan data source adapter (currently blocked by API 451).

workflows/
- global_fetch_workflow.py — Orchestrates the multi-step global data collection:
  check cache → fetch from sources → validate → aggregate → cache → return.

policies/
- staleness_policy.py — Defines what "stale global data" means and how to handle it.
  Data stale > 24 hours: return last known + warn. Data stale > 48 hours: error.

governance/
- udit_logger.py — Logs every external data fetch: timestamp, source, symbols,
  latency, result count, cache hit/miss.

nalytics/
- global_regime_scorer.py — Scores global market conditions as bullish/neutral/
  bearish on a -100 to +100 scale.

monitoring/
- health_provider.py — Reports engine health. OPTIMAL if last fetch < 5 min ago.
  DEGRADED if last fetch between 5-30 min. CRITICAL if last fetch > 30 min.
- latency_tracker.py — Tracks per-fetch latency. Target: < 2,000ms.
  Alert if > 5,000ms (LAYER_LATENCY_CRIT override: 12,000ms).

config/
- defaults.py — Default configuration: cache TTL, timeout settings, symbol list,
  pre-warm interval.
- schema.py — Configuration validation schema.

---

### G.2 Market Intelligence Engine — engines/market_intelligence/

The Market Intelligence Engine analyzes NSE/BSE market conditions, including NIFTY
and BANKNIFTY regime classification, sector rotation, liquidity conditions, and
event calendar. It provides the local market context that Global Intelligence provides
for global context.

**Key service files:**

services/
- market_monitor.py — Continuous 30-second scan of market conditions.
  Implements 6 deep-scan slots per hour for detailed analysis.
  Tracks breadth, volatility, sector performance, and liquidity.
- egime_classifier.py — Classifies current market regime using price action,
  volatility, and breadth. Regimes: BULL_TRENDING, BULL_VOLATILE, BEAR_TRENDING,
  BEAR_VOLATILE, RANGING, BREAKOUT, CAPITULATION.
- sector_analyzer.py — Analyzes 11 NSE sectors for relative strength, rotation
  signals, and momentum.
- liquidity_analyzer.py — Analyzes market depth, bid-ask spreads, and volume
  patterns across key instruments.
- event_calendar.py — Tracks RBI events, budget announcements, F&O expiry dates,
  and other market-moving events.

models/
- market_snapshot.py — The MarketSnapshot dataclass: regime, sector scores,
  liquidity score, breadth, trend strength, key support/resistance levels.
- egime.py — MarketRegime enum with all regime values.
- sector_snapshot.py — Per-sector performance and rotation signal.

---

### G.3 Risk Guardian Engine — engines/risk_guardian/

The Risk Guardian Engine is the kill-switch authority for IIOS. It is a PROTECTED
engine requiring Architecture Council approval for any modification.

**Kill switch conditions (constitutional, not configurable by operators):**
1. VIX (India VIX) exceeds threshold (default: 45)
2. Daily portfolio loss exceeds threshold (default: 2%)
3. Any single strategy drawdown exceeds threshold (default: 15%)

**Key protected files:**

policies/
- kill_switch_policy.py — PROTECTED FILE. Defines the three kill conditions,
  their thresholds, and the response sequence. Changes require Architecture Council
  sign-off. CODEOWNERS enforces mandatory review.
- position_close_policy.py — Defines the procedure for closing all open positions
  when a kill switch is triggered.

services/
- isk_guardian_service.py — Main service. Pre-execution check (before any order)
  and continuous monitoring (every 60 seconds during market hours).
- ix_monitor.py — Dedicated VIX monitoring service. Queries India VIX every
  60 seconds. Triggers kill switch at defined threshold.
- pnl_monitor.py — Real-time P&L monitoring against daily loss threshold.
- drawdown_monitor.py — Strategy-level drawdown monitoring.

governance/
- kill_switch_audit.py — Immutable audit log of every kill switch event: timestamp,
  trigger condition, portfolio state at trigger, response taken, and resolution.
  Kill switch events are never deleted from the audit log.

---

### G.4 Debate and Decision Engine — engines/debate_and_decision/

The Debate and Decision Engine runs a multi-agent debate protocol to produce final
trade decisions. Five specialized agents present and challenge arguments before a
decision engine synthesizes the final decision.

**Decision threshold:** Score >= 6.5 on a 0-10 scale. This is a constitutional constant.

**Key service files:**

services/
- debate_coordinator.py — Orchestrates the 5-agent debate protocol.
  Sequence: Signal Analysis Agent → Contrarian Agent → Risk Assessment Agent →
  Opportunity Agent → Synthesis Agent.
- decision_engine.py — Synthesizes agent outputs into a final score. Score >= 6.5
  produces an approved decision. Score < 6.5 produces a reject.
- cooldown_manager.py — Enforces decision cooldown periods to prevent rapid
  re-entry after a recent trade.

models/
- debate_session.py — Represents a complete debate session: all 5 agent arguments,
  rebuttals, final score, decision, and rationale.
- gent_argument.py — A single agent's position: stance, evidence, confidence.
- decision_result.py — The final decision: approve/reject, score, rationale,
  position sizing recommendation, expiry.

nalytics/
- debate_quality_scorer.py — Assesses debate quality: argument diversity, reasoning
  depth, dissent rate, prediction accuracy.

---

### G.5 Execution Engine — engines/execution_engine/

The Execution Engine translates approved trade decisions into actual orders, managing
the lifecycle from decision receipt through order placement, fill tracking, and
position maintenance.

**Dual mode operation:** Paper mode (simulated fills, CSV journal) and Live mode
(Dhan broker API with order placement).

**Key service files:**

services/
- order_manager.py — Core order management. Validates orders against current
  positions, risk limits, and market conditions. Routes to broker adapter.
  Maintains live position book.
- paper_trading_service.py — Paper trading simulator. Simulates fills at bid/ask
  with configurable slippage. Writes to data/paper_trades.csv.
- position_tracker.py — Real-time position tracking: open positions, unrealized P&L,
  exposure by symbol and strategy.

dapters/
- dhan_broker_adapter.py — Dhan API adapter. Handles authentication, order
  placement, order modification, order cancellation, and position queries.
- paper_broker_adapter.py — Paper trading adapter. Simulates broker responses.

policies/
- order_routing_policy.py — Determines which broker adapter handles each order
  based on instrument type, order size, and mode.
- ill_simulation_policy.py — In paper mode: defines fill price, partial fill
  probability, and slippage model.

---

### G.6 Control Tower Engine — engines/control_tower/

The Control Tower Engine provides system-wide observability, telemetry, and the
Streamlit dashboard interface. All engines publish metrics to Control Tower.

**Key service files:**

services/
- system_monitor.py — Per-layer latency tracking with configurable WARN/CRIT
  thresholds. The 	ime_layer(layer_name) context manager is a critical interface
  that must not change.
- 	elemetry_service.py — SQLite telemetry database. Stores cycle metrics, decision
  outcomes, position changes, and system events.
- event_bus_service.py — System-wide event bus. Engines publish events; subscribers
  receive them asynchronously.
- dashboard_service.py — Streamlit dashboard server. Provides real-time system
  status, position overview, P&L, and strategy performance.

models/
- system_event.py — Generic system event: type, source engine, payload, timestamp.
- cycle_metrics.py — Per-cycle metrics: layer latencies, decision count, trade count.
- 	elemetry_record.py — SQLite record schema for telemetry storage.

---

### G.7 Orchestrator — engines/orchestrator/

The Orchestrator is a PROTECTED engine and the coordination layer that drives the
IIOS cycle. It sequences the 17-engine execution, manages the scheduler, and
coordinates pre-market initialization, market-hours operation, and end-of-day learning.

**Cycle structure:**
- Pre-market (before 09:15 IST): Global Intelligence, Market Intelligence pre-load.
- Market hours (09:15-15:30 IST): Full 17-engine cycle at scheduled intervals.
- Post-market (after 15:30 IST): EOD learning, performance analytics, research updates.

**Key service files:**

services/
- master_orchestrator.py — Main orchestration service. un_full_cycle() is the
  critical interface. start_scheduler() drives scheduled execution.
- cycle_coordinator.py — Manages inter-engine data flow within a cycle.
  Ensures outputs from lower-stratum engines are available to higher-stratum engines.
- scheduler_service.py — APScheduler-based scheduling. Market hours guard prevents
  cycle execution outside NSE trading hours.

policies/
- cycle_policy.py — Defines which engines participate in each cycle type
  (full cycle, pre-market cycle, EOD cycle, weekend cycle).
- market_hours_policy.py — NSE market hours definitions including pre-open,
  continuous trading, closing auction, and after-market sessions.

---

## SUPPLEMENT H — ENGINE INTERACTION PROTOCOLS

### H.1 Inter-Engine Communication Standards

All inter-engine communication in IIOS follows four protocols:

**Protocol 1: Synchronous Interface Call**
Used when: Layer N calls Layer N-1 for a required input before proceeding.
Mechanism: Direct method call on the engine's public interface.
Requirement: The called engine's response must be received before the caller proceeds.

`
Example:
  debate_and_decision calls risk_guardian.pre_check() before approving any trade.
  Execution blocks until risk_guardian returns a response.
`

**Protocol 2: Event Bus Publication**
Used when: An engine publishes a state change that multiple engines may consume.
Mechanism: Engine calls event_bus.publish(event_type, payload).
Requirement: Publication is fire-and-forget. The publisher does not wait for consumers.

`
Example:
  risk_guardian publishes KillSwitchTriggeredEvent when triggered.
  execution_engine, trade_monitoring, and control_tower all receive and react.
`

**Protocol 3: Shared Domain Object**
Used when: Multiple engines need to read the same snapshot of market state.
Mechanism: A domain object (e.g., GlobalSnapshot, MarketSnapshot) is computed
once per cycle and passed by reference to consuming engines.
Requirement: Domain objects are immutable once created. No engine modifies them.

**Protocol 4: Database Read/Write**
Used when: An engine persists state that must survive across cycles or system restarts.
Mechanism: Engine writes to its dedicated SQLite table in data/databases/.
Requirement: No two engines write to the same database table.
  Read-sharing across engines is permitted (e.g., control_tower reads all tables
  for dashboard display).

---

### H.2 Dependency Direction Reference

The legal dependency directions between engine strata:

`
Stratum N can depend on: Any stratum M where M < N
Stratum N cannot depend on: Any stratum M where M >= N

Cross-stratum: Only via event bus or shared domain objects.
Reverse dependency: Always forbidden. A lower-stratum engine may not call
  a higher-stratum engine under any circumstances.

Exceptions (approved by Architecture Council ADR only):
  control_tower (Stratum 17) may READ telemetry from all strata (read-only,
  one-way, for dashboard display only).
`

---

### H.3 Event Type Catalog

All published event types in the IIOS system:

| Event Type | Publisher | Subscribers |
|-----------|-----------|------------|
| GlobalSnapshotReady | global_intelligence | market_intelligence, meta_learning |
| MarketRegimeChanged | market_intelligence | strategy_lab, risk_control, meta_learning |
| KillSwitchTriggered | risk_guardian | execution_engine, trade_monitoring, control_tower |
| KillSwitchLifted | risk_guardian | execution_engine, control_tower |
| DecisionApproved | debate_and_decision | execution_engine, control_tower |
| DecisionRejected | debate_and_decision | control_tower, learning_system |
| OrderPlaced | execution_engine | trade_monitoring, control_tower, learning_system |
| OrderFilled | execution_engine | trade_monitoring, control_tower, learning_system |
| OrderCancelled | execution_engine | trade_monitoring, control_tower |
| PositionClosed | execution_engine | learning_system, performance_analytics |
| DailyPnlThreshold | risk_guardian | control_tower, execution_engine |
| StrategyDisabled | learning_system | strategy_lab, control_tower |
| CycleStarted | orchestrator | control_tower |
| CycleCompleted | orchestrator | control_tower |
| SystemStarted | orchestrator | control_tower |
| SystemShuttingDown | orchestrator | All engines |

---

### H.4 Data Flow Diagram Reference

The primary data flow in the IIOS cycle follows this sequence:

`
[External: yfinance, Dhan API]
         |
         v
[Layer 1: global_intelligence] ---- GlobalSnapshot
         |
         v
[Layer 2: market_intelligence] ---- MarketSnapshot + RegimeClassification
         |
         v
[Layer 3: meta_learning] ---- StrategyWeights (k-NN predictions)
         |
         v
[Layer 4: opportunity_engine] ---- OpportunityList (ranked candidates)
         |
         v
[Layer 5: strategy_lab] ---- StrategySignals (entry criteria, sizing guidance)
         |
         v
[Layer 6: capital_risk_engine] ---- PositionBudgets (per-strategy capital allocations)
         |
         v
[Layer 7: risk_control] ---- PortfolioAllocation (risk-adjusted allocation)
         |
         v
[Layer 8: market_simulation] ---- MonteCarloScenarios (14 scenarios + stress tests)
         |
         v
[Layer 9: risk_guardian] ---- PreCheckResult (ALLOW or KILL)
         |
         v (only if ALLOW)
[Layer 10: debate_and_decision] ---- DecisionResult (score, approve/reject)
         |
         v (only if approve, score >= 6.5)
[Layer 11: execution_engine] ---- OrderResult (placed/filled/rejected)
         |
         v
[Layer 12: trade_monitoring] ---- TradeHealth (monitoring + alerts)
         |
         v
[Layer 13: learning_system] ---- PerformanceUpdate (win rate, strategy fitness)
         |
         v
[Layer 14: performance_analytics] ---- DrawdownMetrics + WalkForwardResults
         |
         v
[Layer 15: research_lab] ---- PromotionDecisions (new strategies from lab)
         |
         v
[Layer 16: validation_engine] ---- ValidationResults (6-stage gate pass/fail)
         |
         v
[Layer 17: control_tower] ---- Telemetry + Dashboard + Alerts
`

---

## SUPPLEMENT I — CI/CD PIPELINE PHYSICAL STRUCTURE

### I.1 Pipeline Files Location

All CI/CD pipeline definitions live in .github/workflows/:

`
.github/
|-- workflows/
|   |-- pr.yml             -- Pull request validation pipeline
|   |-- main.yml           -- Main branch CI pipeline
|   |-- release.yml        -- Release and deployment pipeline
|   |-- nightly.yml        -- Nightly extended test and benchmark suite
|   |-- security.yml       -- Security scanning pipeline
|   |-- docs.yml           -- Documentation build and publish pipeline
`

---

### I.2 PR Pipeline (pr.yml) — Checks Run on Every Pull Request

`
pr.yml stages (sequential):

1. lint
   - flake8 (PEP 8 compliance, max complexity E501 / C901)
   - pylint (code quality score threshold)
   - mypy (type checking with strict mode for core/)
   - black --check (formatting compliance)
   - isort --check (import order compliance)

2. test
   - pytest tests/unit/ (full unit suite)
   - Coverage: core/ and shared/ must be >= 90%
   - pytest tests/integration/ (integration suite)
   - pytest tests/security/ (security suite)

3. validate-structure
   - tools/validate_deps.py (dependency direction check)
   - tools/check_naming.py (naming convention check)
   - detect-secrets scan (no new secrets introduced)

4. acceptance
   - pytest tests/acceptance/ (kill switch acceptance tests)
`

---

### I.3 Main Pipeline (main.yml) — Runs on Merge to Main

`
main.yml stages (sequential):

1. All PR pipeline stages (from above)

2. regression
   - pytest tests/regression/ (full regression suite)

3. performance
   - pytest tests/performance/ (benchmark suite with thresholds)

4. simulation
   - pytest tests/simulation/ (Monte Carlo and scenario tests)

5. build
   - docker build --no-cache (confirm image builds clean)
   - docker image smoke test (container starts and passes healthcheck)

6. tag-version
   - Auto-tag with version from pyproject.toml if all stages pass
`

---

### I.4 Release Pipeline (elease.yml) — Runs on Version Tag Push

`
release.yml stages (sequential):

1. All main.yml stages (from above)

2. deploy-vps
   - SSH to VPS (root@178.18.252.24)
   - git pull origin main
   - docker compose build --no-cache
   - docker compose down
   - docker compose up -d
   - Sleep 8 seconds
   - docker compose ps — confirm both containers healthy

3. smoke-test-production
   - HTTP health check on production endpoint
   - Telegram notification: system version + healthy status

4. publish-changelog
   - Extract latest CHANGELOG.md entry
   - Post to GitHub Release notes
`

---

## SUPPLEMENT J — SECRETS AND SECURITY PHYSICAL STRUCTURE

### J.1 Secret Categories and Storage Locations

| Secret Category | Storage Location | Committed? | Rotation |
|----------------|------------------|-----------|----------|
| Dhan API token | VPS environment variable | Never | Daily (token regenerated by Dhan OAuth flow) |
| Telegram bot token | VPS environment variable | Never | On compromise only |
| VPS SSH private key | Developer local only | Never | On compromise only |
| Database encryption key | VPS environment variable | Never | Annually |
| CI/CD secrets | GitHub repository secrets | Never | On compromise only |

---

### J.2 .env.example Structure

The .env.example file at the repository root documents every environment variable.
New environment variables may not be introduced without corresponding .env.example
entries.

`
# ===================================================================
# IIOS — Environment Variables Reference
# Copy to .env and fill in actual values. Never commit .env
# ===================================================================

# ---- System ----
IIOS_ENV=development            # development | paper | production
IIOS_LOG_LEVEL=INFO             # DEBUG | INFO | WARNING | ERROR

# ---- Data Feeds ----
IIOS_FEED_DHAN_TOKEN=           # Required for live data. Regenerated daily.
IIOS_FEED_DHAN_CLIENT_ID=       # Required for live data.
IIOS_FEED_FALLBACK_ENABLED=true # Enable yfinance fallback if Dhan unavailable

# ---- Broker ----
IIOS_BROKER_PAPER_MODE=true     # true = paper trading; false = live orders
IIOS_BROKER_DHAN_TOKEN=         # Same as IIOS_FEED_DHAN_TOKEN (broker context)
IIOS_BROKER_DHAN_CLIENT_ID=     # Same as IIOS_FEED_DHAN_CLIENT_ID

# ---- Notifications ----
IIOS_TELEGRAM_BOT_TOKEN=        # Telegram bot token from BotFather
IIOS_TELEGRAM_CHAT_ID=          # Telegram chat ID for trade notifications

# ---- Risk Thresholds ----
IIOS_RISK_VIX_THRESHOLD=45      # Kill switch: India VIX threshold
IIOS_RISK_DAILY_LOSS_PCT=0.02   # Kill switch: daily loss threshold (2%)
IIOS_RISK_MAX_DRAWDOWN_PCT=0.15 # Kill switch: strategy drawdown threshold (15%)

# ---- Decision ----
IIOS_DECISION_THRESHOLD=6.5     # Minimum score to approve a trade decision

# ---- Database ----
IIOS_DB_PATH=data/databases/    # Path to SQLite database directory
IIOS_DB_ENCRYPTION_KEY=         # Database encryption key (required in production)
`

---

### J.3 Secret Scanner Configuration

The .secrets.baseline file at the repository root contains the secret scanner
configuration and baseline. All scan findings that have been reviewed and marked
as false positives are recorded in this baseline.

The secret scanner runs:
- On every PR (CI pipeline).
- On every developer's local pre-commit hook.
- Nightly on the main branch as a scheduled scan.

Rules for baseline management:
- A finding may be added to the baseline only after explicit review by the security owner.
- The reason for false-positive classification must be documented in the baseline entry.
- Baseline entries are reviewed quarterly.

---

## SUPPLEMENT K — OPERATIONAL CALENDAR

### K.1 Daily Operations

| Time (IST) | Operation | Engine | Physical Artifact |
|-----------|-----------|--------|------------------|
| 08:30 | Pre-market warm-up | global_intelligence | Cache pre-loaded |
| 09:00 | Market readiness check | market_intelligence | Regime classification run |
| 09:15 | Market open — cycle begins | orchestrator | Full 17-engine cycle |
| 10:00 | First deep scan | market_intelligence | 6-deep-scan-slot consumed |
| 12:00 | Midday review | control_tower | Dashboard refresh |
| 15:30 | Market close | orchestrator | EOD cycle initiated |
| 16:00 | EOD learning | learning_system | Strategy performance updated |
| 16:30 | Log archival | system monitor | Logs rotated to logs/archive/ |
| 17:00 | Nightly research | research_lab | Lab runs on previous day data |
| 18:00 | Health report | control_tower | Telegram summary sent |

---

### K.2 Weekly Operations

| Day | Operation | Responsible Engine |
|-----|-----------|-------------------|
| Monday | Strategy fitness review | learning_system |
| Wednesday | Research lab strategy evolution run | research_lab |
| Friday | Weekly P&L reconciliation | performance_analytics |
| Friday | Experiment review (active items) | Architecture Council |
| Sunday | Repository structure compliance check | CI tools |

---

### K.3 Monthly Operations

| Operation | Physical Artifact Updated |
|-----------|--------------------------|
| ADR review | docs/decisions/ — stale ADRs updated |
| Runbook test | docs/operations/ — runbook tested + dated |
| Archive cleanup | rchive/ — items older than 90 days reviewed |
| Dependency update | equirements.in → repin equirements.txt |
| Secret rotation review | .env.example — confirm all variables documented |
| Performance baseline review | 	ests/performance/ — thresholds validated |

---

### K.4 Annual Operations

| Operation | Physical Artifact Updated |
|-----------|--------------------------|
| Repository certification (PRC) | docs/engineering/CERTIFICATION_RESULTS.md |
| CODEOWNERS review | .github/CODEOWNERS |
| Constitutional review | This document — amendment history updated |
| Security audit | docs/standards/security_audit_YYYY.md |
| Growth projection review | Part VIII projections validated against reality |
| Technical debt audit | docs/engineering/TECH_DEBT_REGISTER.md |

---

*End of Supplement K*

---

## SUPPLEMENT L — PHYSICAL REPOSITORY STRUCTURE CHECKLIST

This checklist is provided for use during onboarding, repository certification,
and post-modification verification.

### L.1 Initial Setup Checklist

[ ] Repository cloned to local development machine.
[ ] Python 3.14 virtual environment created at .venv/.
[ ] All dependencies installed from equirements.txt.
[ ] .env created from .env.example with actual values.
[ ] Pre-commit hooks installed: pre-commit install.
[ ] All tests pass: pytest tests/.
[ ] 	ools/validate_deps.py passes with zero violations.
[ ] 	ools/check_naming.py passes with zero violations.
[ ] Docker build succeeds: docker compose build.
[ ] Both containers start healthy: docker compose up -d && docker compose ps.

---

### L.2 New Engine Addition Checklist

[ ] Engine package directory created at engines/[engine_name]/.
[ ] All 16 required subdirectories created.
[ ] __init__.py created with __all__ list.
[ ] [engine_name].py main module created.
[ ] README.md written (engine overview, interface summary, usage example).
[ ] documentation/DESIGN.md written.
[ ] documentation/INTERFACE.md written.
[ ] governance/audit_logger.py implemented.
[ ] monitoring/health_provider.py implemented.
[ ] config/defaults.py created with all configurable values.
[ ] Configuration file created at config/engines/[engine_name]_config.py.
[ ] Test directory created at 	ests/unit/engines/[engine_name]/.
[ ] At least one unit test written and passing.
[ ] Engine added to engines/README.md.
[ ] ADR written for adding the engine.
[ ] CODEOWNERS updated with engine owner.
[ ] Engine registered with Orchestrator (if appropriate stratum).

---

### L.3 Pre-Deployment Checklist

[ ] All modified files committed.
[ ] All tests pass locally.
[ ] 	ools/validate_deps.py passes.
[ ] detect-secrets scan shows no new findings.
[ ] docker compose build --no-cache succeeds.
[ ] Docker smoke test passes.
[ ] CHANGELOG.md updated.
[ ] git push origin main completed.
[ ] VPS deployment script run and both containers confirmed healthy.
[ ] Telegram notification received confirming new version deployed.

---

*End of Supplement L*

---

## REVISION AND CHANGE MANAGEMENT

### Managing Document Changes

This document (IIOS-PHYS-REPO-001) defines the physical structure of the IIOS
repository. Changes to this document must follow the formal amendment process:

1. **Propose:** An issue is raised describing the proposed change and its rationale.
2. **Draft ADR:** An ADR is drafted explaining the decision, alternatives considered,
   and consequences.
3. **Review:** Architecture Council reviews the proposal and the ADR.
4. **Approve:** Two Architecture Council members approve the proposal.
5. **Implement:** The document is updated and the repository structure is adjusted.
6. **Record:** The amendment history table is updated with the change, date, and author.

### Change Categories

**Minor changes (no governance required):**
- Correcting typographical errors.
- Clarifying existing rules without changing their meaning.
- Adding examples that illustrate existing rules.
- Updating amendment history.

**Major changes (full governance process required):**
- Adding, removing, or renaming top-level directories.
- Changing an engine package name.
- Adding, removing, or reclassifying constitutional rules.
- Modifying certification gate counts or requirements.
- Changing naming conventions.
- Adding or removing engine packages from the canonical list.

### Version Numbering

This document uses MAJOR.MINOR.PATCH versioning:
- MAJOR: Changes to fundamental structure (top-level directories, engine list).
- MINOR: New supplement, new rules, new certification gates.
- PATCH: Clarifications, examples, corrections.

---

*End of Revision and Change Management*

---

## CLOSING STATEMENT

The Physical Repository Structure specification (IIOS-PHYS-REPO-001) defines the
canonical physical organization of the Investment Intelligence Operating System
repository. It establishes:

- A 24-directory root structure accommodating 20+ years of additive growth.
- 18 engine packages in a flat hierarchy, each with 16 standardized subdirectories.
- A dependency architecture that can be verified by CI with zero ambiguity.
- 100 constitutional rules governing every aspect of physical organization.
- 65 certification gates that confirm compliance before every production deployment.
- 6 supplements providing reference trees, catalogs, naming examples, growth
  projections, anti-patterns, and a glossary.
- 6 extended supplements covering engine anatomy, interaction protocols, CI/CD
  pipeline structure, secrets management, operational calendar, and checklists.

The structure is designed to remain valid and non-reorganizable for the entire
operational life of IIOS. Every growth dimension has a pre-defined canonical home.
Every artifact type has a naming convention. Every constitutional rule is enforced
by CI or human review.

This document is the physical foundation of the IIOS repository. Its rules are the
physical laws of the codebase.

---

*IIOS-PHYS-REPO-001 Version 1.0.0*
*Investment Intelligence Operating System — Physical Repository Structure*
*Architecture Council — 2026-07-04*
*Status: AUTHORITATIVE*
*This document supersedes all prior informal repository structure decisions.*
*End of Document.*
---

## SUPPLEMENT M — COMPLETE CONFIGURATION REFERENCE

### M.1 Base Configuration Structure

The config/environments/base.yaml file is the foundation of all IIOS configuration.
Every configuration key used by any engine must have an entry in ase.yaml.
Environment-specific files (production.yaml, paper.yaml) override only the
values that differ from the base.

This supplement documents the complete configuration taxonomy organized by subsystem.

---

### M.2 System Configuration (system.*)

| Key | Default | Description | Overridden In |
|-----|---------|-------------|--------------|
| system.env | development | Current environment name | production.yaml, paper.yaml |
| system.log_level | INFO | Log verbosity | production.yaml (INFO), development (DEBUG) |
| system.timezone | Asia/Kolkata | System timezone | Never |
| system.version | rom pyproject.toml | System version string | Never |
| system.instance_id | auto-generated | Unique deployment instance ID | production.yaml |
| system.maintenance_mode | alse | Suppress trading when true | production.yaml |
| system.debug_mode | alse | Enable debug logging and diagnostics | development |

---

### M.3 Data Feed Configuration (eeds.*)

| Key | Default | Description | Overridden In |
|-----|---------|-------------|--------------|
| eeds.primary | dhan | Primary data feed provider | paper.yaml (yfinance) |
| eeds.fallback_enabled | 	rue | Enable yfinance fallback | Never |
| eeds.fallback_delay_ms | 500 | Wait before fallback switch | production.yaml |
| eeds.dhan.timeout_ms | 8000 | Dhan API request timeout | production.yaml |
| eeds.dhan.retry_count | 3 | Retry attempts for Dhan requests | production.yaml |
| eeds.dhan.reconnect_interval_s | 30 | Reconnect interval after disconnect | production.yaml |
| eeds.yfinance.timeout_s | 8 | yfinance download timeout | production.yaml |
| eeds.yfinance.session_reuse | 	rue | Reuse HTTP session for yfinance | production.yaml |
| eeds.cache.market_data_ttl_s | 60 | Market data cache TTL | production.yaml |
| eeds.cache.global_snapshot_ttl_s | 300 | Global snapshot cache TTL (5 min) | Never |

---

### M.4 Risk Configuration (isk.*)

| Key | Default | Description | Overridden In |
|-----|---------|-------------|--------------|
| isk.kill_switch.vix_threshold | 45 | India VIX kill threshold | production.yaml (tighter allowed) |
| isk.kill_switch.daily_loss_pct |  .02 | Daily portfolio loss limit | production.yaml (tighter allowed) |
| isk.kill_switch.strategy_drawdown_pct |  .15 | Single strategy drawdown limit | production.yaml (tighter allowed) |
| isk.kill_switch.check_interval_s | 60 | Kill switch check frequency | production.yaml |
| isk.position_limits.max_open_positions | 5 | Maximum concurrent open positions | production.yaml |
| isk.position_limits.max_position_size_pct |  .20 | Max position size as portfolio pct | production.yaml |
| isk.position_limits.max_sector_exposure_pct |  .40 | Max exposure in one sector | production.yaml |
| isk.daily_limits.max_trades_per_day | 10 | Max trade entries per day | production.yaml |
| isk.daily_limits.max_loss_per_trade_pct |  .005 | Max loss per single trade (0.5%) | production.yaml |

---

### M.5 Decision Configuration (decision.*)

| Key | Default | Description | Overridden In |
|-----|---------|-------------|--------------|
| decision.threshold | 6.5 | Minimum score to approve a trade | production.yaml (tighter allowed) |
| decision.cooldown_minutes | 30 | Min time between decisions on same symbol | production.yaml |
| decision.debate.max_duration_s | 15 | Max seconds for debate to complete | production.yaml |
| decision.debate.agent_count | 5 | Number of debate agents | Never |
| decision.debate.quorum_required | 3 | Min agents to achieve quorum | Never |
| decision.expiry_minutes | 60 | Trade decision expires after N minutes | production.yaml |

---

### M.6 Broker Configuration (roker.*)

| Key | Default | Description | Overridden In |
|-----|---------|-------------|--------------|
| roker.mode | paper | Operating mode: paper or live | production.yaml (live) |
| roker.dhan.order_timeout_ms | 5000 | Order placement timeout | production.yaml |
| roker.dhan.max_retries | 2 | Order retry attempts on timeout | production.yaml |
| roker.paper.slippage_bps | 5 | Simulated slippage in basis points | Never |
| roker.paper.fill_probability |  .99 | Probability of simulated fill | Never |
| roker.paper.journal_path | data/paper_trades.csv | Paper trade journal file | Never |
| roker.order_log_path | data/databases/orders.db | Order history database | Never |

---

### M.7 Scheduler Configuration (scheduler.*)

| Key | Default | Description | Overridden In |
|-----|---------|-------------|--------------|
| scheduler.pre_market_time |  8:30 | Pre-market warm-up time (IST) | Never |
| scheduler.market_open_time |  9:15 | Market open time (NSE, IST) | Never |
| scheduler.market_close_time | 15:30 | Market close time (NSE, IST) | Never |
| scheduler.eod_learning_time | 16:00 | EOD learning run time (IST) | Never |
| scheduler.nightly_research_time | 17:00 | Nightly research run time (IST) | Never |
| scheduler.full_cycle_interval_min | 5 | Full cycle interval during market hours | production.yaml |
| scheduler.continuous_scan_interval_s | 30 | Continuous market scan interval | production.yaml |
| scheduler.weekend_enabled | alse | Allow cycles on weekends | Never |

---

### M.8 Notification Configuration (
otifications.*)

| Key | Default | Description | Overridden In |
|-----|---------|-------------|--------------|
| 
otifications.telegram.enabled | 	rue | Enable Telegram notifications | Never |
| 
otifications.telegram.trade_alerts | 	rue | Send alerts for trade events | Never |
| 
otifications.telegram.kill_switch_alerts | 	rue | Send kill switch notifications | Never |
| 
otifications.telegram.daily_summary | 	rue | Send daily P&L summary | Never |
| 
otifications.telegram.system_events | 	rue | Send system start/stop events | Never |
| 
otifications.telegram.max_alerts_per_hour | 20 | Rate limit on alert delivery | production.yaml |

---

### M.9 Monitoring Configuration (monitoring.*)

| Key | Default | Description | Overridden In |
|-----|---------|-------------|--------------|
| monitoring.dashboard.port | 8501 | Streamlit dashboard port | production.yaml |
| monitoring.dashboard.refresh_interval_s | 10 | Dashboard refresh interval | production.yaml |
| monitoring.telemetry.db_path | data/databases/telemetry.db | Telemetry database path | Never |
| monitoring.telemetry.retention_days | 90 | How long to keep telemetry | production.yaml |
| monitoring.health_check.interval_s | 60 | System health check interval | production.yaml |
| monitoring.latency.warn_ms | 2000 | Per-layer latency warn threshold | production.yaml |
| monitoring.latency.critical_ms | 5000 | Per-layer latency critical threshold | production.yaml |
| monitoring.latency.global_intel_warn_ms | 5000 | Global Intel layer latency warn | Never |
| monitoring.latency.global_intel_critical_ms | 12000 | Global Intel layer latency critical | Never |

---

## SUPPLEMENT N — LOGGING PHYSICAL STRUCTURE

### N.1 Log File Organization

Runtime log files are stored in logs/ (gitignored). The internal structure is:

`
logs/
|-- app.log                    -- Main application log (current day)
|-- app-YYYY-MM-DD.log         -- Rotated daily logs
|-- errors.log                 -- ERROR and CRITICAL only (current day)
|-- errors-YYYY-MM-DD.log      -- Rotated error logs
|-- trades.log                 -- Trade event log (all order events)
|-- trades-YYYY-MM-DD.log      -- Rotated trade logs
|-- kill_switch.log            -- Kill switch events (immutable)
|-- performance.log            -- Per-cycle timing and latency
|-- archive/
    |-- [older rotated logs]
`

---

### N.2 Log Format Standards

All log entries follow a structured format for machine parsability and human readability:

`
[ISO_TIMESTAMP] [LEVEL] [ENGINE] [COMPONENT] [EVENT_TYPE] MESSAGE {json_context}

Example:
[2026-07-04T09:17:42.123+05:30] [INFO] [risk_guardian] [kill_switch_service]
[KILL_SWITCH_CHECK] VIX check passed {"vix": 18.4, "threshold": 45, "result": "ALLOW"}

[2026-07-04T11:43:17.891+05:30] [WARNING] [execution_engine] [order_manager]
[ORDER_REJECTED] Position limit reached {"symbol": "TATASTEEL", "reason": "max_positions",
"current_positions": 5, "limit": 5}
`

---

### N.3 Log Sanitization Rules

The core/logging/sanitizer.py module enforces these sanitization rules:

**Always redacted in logs:**
- Dhan API tokens (pattern: 32+ alphanumeric chars in specific formats)
- Telegram bot tokens (pattern: \d+:.*)
- Database passwords
- SSH keys
- Any value associated with key names: 	oken, password, secret, key, credential

**Always included in logs (never redacted):**
- Symbol names (NIFTY, BANKNIFTY, TATASTEEL, etc.)
- Price values (these are market data, not secrets)
- Trade quantities
- Score values
- Latency measurements

---

### N.4 Log Rotation Configuration

Log rotation is configured in config/global_config.py and managed by Python's
logging.handlers.TimedRotatingFileHandler:

`
Rotation interval: Daily (at midnight IST)
Backup count: 30 (retain 30 days of rotated logs)
File encoding: UTF-8
Compression: gzip after rotation (applied next day)
Archive path: logs/archive/
Archive retention: 90 days (older logs deleted at quarterly maintenance)
`

---

### N.5 Kill Switch Log Requirements

The kill_switch.log file has special immutability requirements:

1. It is opened with append mode only. Nothing is ever overwritten.
2. Every kill switch trigger writes a complete record: trigger condition, portfolio
   state, positions at time of trigger, P&L at time of trigger, resolution timestamp.
3. Kill switch log entries are never deleted by log rotation or archival.
4. Annual compliance review reads kill_switch.log to confirm all events are documented.

---

## SUPPLEMENT O — DATABASE PHYSICAL STRUCTURE

### O.1 SQLite Database Organization

All SQLite databases live in data/databases/ (gitignored). The database catalog:

| Database File | Owner Engine | Purpose | Schema File |
|--------------|-------------|---------|------------|
| 	elemetry.db | control_tower | System metrics, cycle data | scripts/migrations/telemetry_schema.sql |
| orders.db | execution_engine | Order history, fill records | scripts/migrations/orders_schema.sql |
| positions.db | execution_engine | Position history | scripts/migrations/positions_schema.sql |
| strategies.db | strategy_lab | Strategy registry, fitness scores | scripts/migrations/strategies_schema.sql |
| learning.db | learning_system | Win rate tracking, performance | scripts/migrations/learning_schema.sql |
| decisions.db | debate_and_decision | Decision history, debate sessions | scripts/migrations/decisions_schema.sql |
| egime.db | market_intelligence | Regime history, transition log | scripts/migrations/regime_schema.sql |
| esearch.db | research_lab | Research findings, experiment results | scripts/migrations/research_schema.sql |
| udit.db | governance layer | Cross-engine audit events | scripts/migrations/audit_schema.sql |

---

### O.2 Schema Migration Rules

Database schema changes follow these rules:

1. **Migration files:** Every schema change has a migration script in
   scripts/migrations/YYYY-MM-DD_NNN_description.py.
   The date is the creation date. NNN is a sequence number starting at 001 per day.

2. **Up and down:** Every migration provides both upgrade() and downgrade()
   functions. The downgrade is tested before the migration is merged.

3. **Additive preferred:** New columns, new tables, new indices are preferred over
   modifying existing columns or dropping tables.

4. **No destructive migrations in production:** Dropping a column or table in
   production requires: data export, architecture review, and a 30-day retirement notice.

5. **Version tracking:** The current schema version is stored in the database itself
   (in a schema_versions table) and in config/engines/[engine_name]_config.py.

---

### O.3 Paper Trade Journal

The data/paper_trades.csv file is the persistent journal for paper trading mode.
Its schema:

`
timestamp,symbol,direction,quantity,entry_price,exit_price,pnl,strategy,
decision_score,hold_duration_s,close_reason
`

The file persists across container restarts because data/ is a Docker volume.
The EOD learning cycle reads this file to compute strategy performance metrics.

---

*End of Supplement O*

---

## SUPPLEMENT P — PYTHON ENVIRONMENT PHYSICAL STRUCTURE

### P.1 Virtual Environment Location

The Python virtual environment is always at .venv/ relative to the repository root.
This location is in .gitignore. It is never committed.

On the VPS (Docker), the environment is the Docker image itself (installed at build time),
not a .venv/ directory.

---

### P.2 Dependency Management Files

| File | Purpose | How Generated |
|------|---------|--------------|
| equirements.in | Human-maintained list of direct dependencies | Hand-edited |
| equirements.txt | Pinned full dependency tree (direct + transitive) | pip-compile requirements.in |
| equirements-dev.txt | Pinned development dependencies | pip-compile requirements-dev.in |
| pyproject.toml | Project metadata, build configuration | Hand-maintained |

**Update procedure for dependencies:**
1. Edit equirements.in or equirements-dev.in with the new or changed dependency.
2. Run pip-compile requirements.in -o requirements.txt.
3. Run pip-compile requirements-dev.in -o requirements-dev.txt.
4. Install new dependencies: pip install -r requirements.txt -r requirements-dev.txt.
5. Run the full test suite to confirm no regressions.
6. Commit both the .in files and the compiled .txt files.

---

### P.3 Key Dependencies

| Package | Version Strategy | Purpose |
|---------|-----------------|---------|
| yfinance | Pinned minor | Market data fallback feed |
| pscheduler | Pinned minor | Cycle scheduler |
| streamlit | Pinned minor | Dashboard UI |
| python-telegram-bot | Pinned minor | Telegram notifications |
| sqlalchemy | Pinned minor | Database abstraction |
| pandas | Pinned minor | Data processing |
| 
umpy | Pinned minor | Numerical computing |
| scipy | Pinned minor | Statistical analysis |
| scikit-learn | Pinned minor | ML utilities (k-NN, etc.) |
| pytest | Pinned minor | Test framework |
| mypy | Pinned minor | Static type checking |
| lack | Pinned minor | Code formatting |
| lake8 | Pinned minor | Linting |
| pre-commit | Pinned minor | Pre-commit hooks |
| pip-tools | Pinned minor | Dependency compilation |

"Pinned minor" means the major and minor versions are pinned, and the patch version
is allowed to float: yfinance>=0.2.40,<0.3.0.

---

*End of Supplement P*

---

## EXTENDED AMENDMENT HISTORY

| Version | Date | Change | Author |
|---------|------|--------|--------|
| 1.0.0 | 2026-07-04 | Initial release with Parts I–X and Supplements A–P | Architecture Council |

---

*IIOS-PHYS-REPO-001 Version 1.0.0 — Investment Intelligence Operating System*
*Physical Repository Structure — Architecture Council — 2026-07-04*
*Status: AUTHORITATIVE — End of Document.*