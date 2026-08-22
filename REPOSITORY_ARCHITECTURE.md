# REPOSITORY ARCHITECTURE
## AI Trading Brain / Investment Intelligence Operating System (IIOS)

**Document Status:** AUTHORITATIVE
**Document Type:** Repository Design Specification
**Version:** 1.0.0
**Date:** 2026-07-02
**Authority:** Human Principal

**Parent Documents:**
- `INVESTMENT_INTELLIGENCE_OPERATING_SYSTEM.md` — Supreme constitutional authority
- `AI_TRADING_BRAIN_ENGINEERING_BLUEPRINT.md` — Engineering design bridge
- `ENGINEERING_STANDARDS.md` — Mandatory engineering standards

---

## Purpose Statement

This document defines the physical and logical organisation of the complete AI Trading Brain / IIOS repository. It governs every folder, file, module, package, artefact, and resource in the project. It is the definitive reference for:

- Where every artefact lives
- Who owns every artefact
- What every folder's responsibility is
- How modules depend on each other
- How the repository grows and evolves over time

This document precedes implementation. No file is created, no folder is made, no module is written without reference to this document. Any deviation from this design requires an Architecture Decision Record (ADR) and Human Principal approval before the deviation is enacted.

---

## Document Authority

| Attribute | Value |
|---|---|
| Governed by | Human Principal |
| Enforced by | Engineering Standards (ENGINEERING_STANDARDS.md Part X) |
| Referenced by | All engineering work in the AI Trading Brain project |
| Supersedes | All ad hoc folder and file placement decisions |
| Amendment process | ADR + Human Principal written approval |
| Version | 1.0.0 |
| Next review | Quarterly (October 2026) |

---

## Scope of Governance

This document governs the following categories of artefacts:

| Category | Examples | Governed |
|---|---|---|
| Source packages | Python packages for all 17 layers | Yes |
| Configuration files | `config.py`, `.env.*`, feature flags | Yes |
| Infrastructure files | `Dockerfile`, `docker-compose.yml`, CI/CD pipelines | Yes |
| Test suites | Unit, integration, performance, security tests | Yes |
| Documentation | All `.md` files, ADRs, READMEs | Yes |
| Data files | SQLite databases, CSV journals, JSON strategy files | Yes |
| Scripts | Deployment, maintenance, tooling scripts | Yes |
| Reports | EOD reports, performance analytics, audit logs | Yes |
| Notebooks | Jupyter analysis notebooks | Yes |
| Prompt library | AI prompt templates | Yes |
| Knowledge assets | Ontologies, entity definitions, taxonomy files | Yes |
| Backups | Database backups, configuration backups | Yes |

---

## Table of Contents

| Part | Title |
|---|---|
| I | Repository Philosophy |
| II | Complete Repository Tree |
| III | Module Ownership |
| IV | Repository Dependency Rules |
| V | Shared Components |
| VI | Configuration Architecture |
| VII | Resource Organisation |
| VIII | Repository Governance |
| IX | Repository Evolution |
| X | Repository Constitution |

---
## PART I — REPOSITORY PHILOSOPHY

### 1.1 Why Repository Architecture Matters

A repository is not merely a container of files. It is the physical expression of the system's intellectual design. The arrangement of folders, the grouping of modules, the naming of directories — all of these decisions communicate intent to every engineer, every automated tool, and every future maintainer who encounters the codebase.

In a system as architecturally complex as the AI Trading Brain — a 17-layer hierarchical multi-agent investment intelligence platform managing real financial decisions — the repository is the first point of contact. It must communicate the architecture before a single line of code is read. A well-designed repository answers four questions on sight:

1. What does this system do?
2. How is it structured?
3. Where do I find what I am looking for?
4. Where do I put what I am building?

When a repository fails to answer these questions — when modules are scattered randomly, when responsibilities are mixed, when dependencies are implicit — the cognitive overhead for every subsequent engineer compounds indefinitely. Each new module placed without reference to an architectural design creates a precedent for the next engineer to place arbitrarily. Within months, the system is a labyrinth rather than a map.

The repository architecture defined in this document prevents this entropy from occurring.

---

### 1.2 Scalability Principle

A scalable repository grows without reorganising its foundation. The architecture defined here is designed for a system that will evolve from its current ~62 agents to hundreds of agents, from a single broker integration to multiple brokers, from NSE/BSE equities to global multi-asset instruments.

Scalability in repository design requires:

| Principle | Description | Applied To |
|---|---|---|
| Additive growth | New modules added inside existing package boundaries | All layers |
| Layer isolation | Each layer's package grows independently | All 17 layers |
| Namespace stability | Package and module names do not change as the system scales | Core packages |
| Index-based discovery | New components are discoverable through registry patterns, not hard-coded imports | Agents, strategies, integrations |
| Plugin-ready layout | The `integrations/` folder accepts new brokers, data sources, and notification channels without core modification | `integrations/` |

A repository that cannot scale without reorganisation will be reorganised under pressure — at the worst possible time. The architecture here eliminates this risk by designing for growth before growth occurs.

---

### 1.3 Maintainability Principle

A maintainable repository is one where the cost of understanding, modifying, and extending any component is low. Maintainability in repository design is achieved through:

| Driver | How This Repository Achieves It |
|---|---|
| Predictable structure | Every engineer can predict where to find any artefact before searching |
| Consistent conventions | All packages follow identical internal structure: `__init__.py`, primary class, utilities, README |
| Self-documenting layout | Folder names communicate purpose without requiring documentation |
| Minimal surface area | Each package exposes only what it intends consumers to use via `__init__.py` |
| No hidden magic | No implicit path manipulation, no environment-dependent imports |
| Single responsibility | Each folder has exactly one declared responsibility |

Maintainability degrades when engineers are uncertain where to put new code. The governance rules in Part X of this document eliminate that uncertainty.

---

### 1.4 Isolation Principle

Isolation ensures that a failure, a change, or a refactoring in one component cannot cascade unexpectedly into another. Repository isolation is achieved through three mechanisms:

**Boundary Isolation**
Each layer package has declared boundaries: allowed imports, forbidden imports, and boundary rules. A module that violates these boundaries introduces a hidden coupling. Hidden couplings are the primary cause of cascading failures in complex systems.

**Data Isolation**
Shared mutable state between layers is prohibited except through explicitly declared interfaces and singleton getters. Each layer owns its data. Data may flow between layers through defined DTOs — never through shared mutable global state.

**Test Isolation**
Unit tests for each package live within the package's own test folder. Tests may not import from other packages' test folders. Test infrastructure (fixtures, mocks, helpers) is shared only through `tests/conftest.py` at the top level.

---

### 1.5 Reusability Principle

Reusability means that a utility, a base class, an interface, or a shared model written once does not need to be rewritten or duplicated for each layer. This repository achieves reusability through a `common/` shared library within `src/`:

| Component Type | Location | Consumers |
|---|---|---|
| Base feed adapter | `src/common/base_feed.py` | All data feed implementations |
| Base agent class | `src/common/base_agent.py` | All 62+ agents |
| Shared DTOs | `src/common/models/` | All layers |
| Validation utilities | `src/common/validation.py` | All input-processing modules |
| Time utilities | `src/common/time_utils.py` | All layers |
| Symbol utilities | `src/common/symbol_utils.py` | All trading and data modules |
| Error hierarchy | `src/common/errors.py` | All layers |
| Logging factory | `src/common/logging_factory.py` | All modules |

Reusability degrades when shared components accumulate too many responsibilities. This document defines explicit scope limits for each shared component in Part V.

---

### 1.6 Separation of Concerns Principle

Separation of concerns is the foundational principle of this repository's design. It states that every folder, every module, every class has exactly one declared concern. No module may span two concerns. No folder may contain artefacts from two unrelated concerns.

The 17-layer architecture of the IIOS is itself the expression of this principle at the highest level. Each layer has a single well-defined cognitive responsibility:

| Layer Range | Concern |
|---|---|
| Layers 1–2 | Market intelligence gathering |
| Layer 3 | Meta-level strategy learning |
| Layers 4–5 | Opportunity and strategy generation |
| Layers 6–7 | Capital allocation and risk management |
| Layer 8 | Market simulation |
| Layer 9 | Final safety enforcement |
| Layer 10 | Debate and decision synthesis |
| Layer 11 | Trade execution |
| Layers 12–13 | Trade monitoring and learning |
| Layer 14 | Performance analytics |
| Layers 15–16 | Research and validation |
| Layer 17 | System orchestration and control |

At the repository level, this separation continues into every sub-folder. `src/` is for source code. `tests/` is for tests. `docs/` is for documentation. `data/` is for runtime data. These boundaries do not blur under any circumstance.

---

### 1.7 Long-Term Evolution Principle

A repository designed only for today's requirements will require a disruptive reorganisation the moment tomorrow's requirements arrive. This repository is designed for a 10-year time horizon of the IIOS. The following evolutionary scenarios are accommodated by the current architecture without requiring any reorganisation:

| Future Scenario | Accommodated How |
|---|---|
| Adding a 18th operational layer | Create a new package in `src/`, register in layer registry |
| Adding a second broker (Zerodha, ICICI) | Add adapter in `src/integrations/brokers/` |
| Adding a second data source (Bloomberg, Reuters) | Add adapter in `src/integrations/data_sources/` |
| Adding new asset classes (FX, commodities) | New strategy files in `strategies/`, new knowledge in `knowledge/` |
| Adding a mobile/API front-end | New service in `src/api/`, existing code unchanged |
| Extracting a layer as a microservice | Each layer package already has a clean interface and no hidden dependencies |
| Adding new ML models | New artefacts in `models/`, imported by existing layer packages |
| Internationalisation | Configuration and knowledge layers already abstract locale concerns |

No architectural change is required for any of these scenarios — only additive growth within the established design.

---

### 1.8 Anti-Patterns This Design Prevents

| Anti-Pattern | Description | How This Design Prevents It |
|---|---|---|
| Flat repository | All files in root or a single `src/` folder without hierarchy | Strict 17-layer package structure |
| Utility dumping ground | A `utils.py` file that grows indefinitely | Named utility modules with specific concerns |
| Circular dependencies | Layer A imports Layer B which imports Layer A | Unidirectional import hierarchy (Part IV) |
| Hidden coupling | Two modules depend on each other through shared global state | Singleton registry pattern + explicit DTOs |
| Mixed test and production | Test files alongside production modules | `tests/` is always separate from `src/` |
| Configuration scattered | Config values hardcoded in random modules | Single `config.py` + layered `.env` files |
| Data files beside code | SQLite or CSV files in source packages | All data in `data/` (separate from `src/`) |
| Undocumented structure | No README, no owner, no declared responsibility | Every folder has a README and owner |
| God package | One package that does too many things | Package responsibility bounded by Part III ownership rules |

---

## PART II — COMPLETE REPOSITORY TREE

### 2.1 Overview

The repository tree below represents the complete physical organisation of the AI Trading Brain / IIOS project. Every folder listed below is a required component of the architecture. No folder is optional. No folder is speculative.

The tree is divided into seven top-level domains:

| Domain | Root Folder | Purpose |
|---|---|---|
| Source code | `src/` | All production Python packages |
| Tests | `tests/` | All test suites mirroring `src/` |
| Documentation | `docs/` | All project documentation |
| Deployment | `deployment/` | Docker, CI/CD, scripts |
| Data | `data/` | Runtime databases, journals, datasets |
| Reports | `reports/` | Generated reports and analytics output |
| Tools | `tools/` | Developer tooling and utilities |

---

### 2.2 Canonical Repository Tree

```
ai_trading_brain/                          # Repository root
│
├── .github/                               # GitHub/CI configuration
│   ├── workflows/                         # GitHub Actions CI/CD pipelines
│   │   ├── ci.yml                         # Continuous integration: test + lint
│   │   ├── deploy.yml                     # Deployment pipeline to VPS
│   │   └── security.yml                   # Dependency vulnerability scan
│   ├── copilot-instructions.md            # AI assistant operational instructions
│   └── skills/                            # AI assistant skill modules
│
├── docs/                                  # All project documentation
│   ├── architecture/                      # Architecture design documents
│   │   ├── INVESTMENT_INTELLIGENCE_OPERATING_SYSTEM.md
│   │   ├── AI_TRADING_BRAIN_ENGINEERING_BLUEPRINT.md
│   │   ├── ENGINEERING_STANDARDS.md
│   │   └── REPOSITORY_ARCHITECTURE.md
│   ├── engineering/                       # Engineering specifications
│   │   ├── adr/                           # Architecture Decision Records
│   │   │   ├── ADR-001-layer-ordering.md
│   │   │   ├── ADR-002-yfinance-fallback.md
│   │   │   ├── ADR-003-sqlite-wal-mode.md
│   │   │   └── ADR-NNN-<description>.md
│   │   ├── DEPLOYMENT_GUIDE.md
│   │   ├── DEPLOYMENT_CHECKLIST.md
│   │   └── AUTOMATED_TRADING_SETUP.md
│   ├── ontology/                          # Domain knowledge models
│   │   ├── market_taxonomy.md
│   │   ├── instrument_classification.md
│   │   ├── regime_taxonomy.md
│   │   └── strategy_taxonomy.md
│   ├── knowledge/                         # Reference knowledge documents
│   │   ├── DHAN_OAUTH_REFERENCE.md
│   │   ├── DHAN_DAILY_TOKEN_REQUIREMENT.md
│   │   └── broker_integration_notes.md
│   └── reports/                           # Historical status reports
│       ├── COMPLETE_STATUS_REPORT_MAR19.md
│       └── EOD_REPORT_APR21_2026.md
│
├── src/                                   # All production source code
│   │
│   ├── common/                            # Shared library (no business logic)
│   │   ├── __init__.py
│   │   ├── base_agent.py                  # Abstract base for all 62+ agents
│   │   ├── base_feed.py                   # Abstract base for all data feeds
│   │   ├── base_strategy.py               # Abstract base for all strategies
│   │   ├── errors.py                      # Full project exception hierarchy
│   │   ├── logging_factory.py             # Centralised logger factory
│   │   ├── time_utils.py                  # Market time utilities
│   │   ├── symbol_utils.py                # Symbol formatting and mapping
│   │   ├── validation.py                  # Input validation primitives
│   │   └── models/                        # Shared data transfer objects
│   │       ├── __init__.py
│   │       ├── ticker_quote.py            # TickerQuote DTO
│   │       ├── price_bar.py               # PriceBar DTO
│   │       ├── global_snapshot.py         # GlobalSnapshot DTO
│   │       ├── regime_signal.py           # RegimeSignal DTO
│   │       ├── hypothesis.py              # TradeHypothesis DTO
│   │       ├── decision_record.py         # DecisionRecord DTO
│   │       ├── order_record.py            # OrderRecord DTO
│   │       └── risk_approval.py           # RiskApproval DTO
│   │
│   ├── config/                            # Configuration management
│   │   ├── __init__.py
│   │   ├── config.py                      # Master configuration (all constants)
│   │   ├── feature_flags.py               # Runtime feature toggle definitions
│   │   ├── validator.py                   # Config validation at startup
│   │   └── schema.py                      # Config schema and allowed ranges
│   │
│   ├── knowledge/                         # Domain knowledge layer
│   │   ├── __init__.py
│   │   ├── entities/                      # Domain entity definitions
│   │   │   ├── __init__.py
│   │   │   ├── instrument.py              # Instrument entity model
│   │   │   ├── market_session.py          # Market session entity
│   │   │   └── economic_event.py          # Economic event entity
│   │   ├── relationships/                 # Entity relationship models
│   │   │   ├── __init__.py
│   │   │   ├── sector_instrument_map.py   # Sector → instrument mapping
│   │   │   └── index_constituent_map.py   # Index → constituent mapping
│   │   ├── events/                        # Market event catalogue
│   │   │   ├── __init__.py
│   │   │   ├── economic_calendar.py       # Economic calendar loader
│   │   │   └── market_holiday.py          # Market holiday calendar
│   │   └── taxonomy/                      # Classification taxonomies
│   │       ├── __init__.py
│   │       ├── regime_taxonomy.py         # Regime type hierarchy
│   │       └── strategy_taxonomy.py       # Strategy family taxonomy
│   │
│   ├── global_intelligence/               # Layer 1: Global market context
│   │   ├── __init__.py
│   │   ├── global_data_ai.py              # GlobalDataAI — primary class
│   │   ├── global_symbol_map.py           # Global → local symbol translation
│   │   └── README.md
│   │
│   ├── market_intelligence/               # Layer 2: NIFTY/sector intelligence
│   │   ├── __init__.py
│   │   ├── market_intelligence_ai.py      # MarketIntelligenceAI — primary class
│   │   ├── market_monitor.py              # Continuous 30s market scan
│   │   ├── sector_analyser.py             # Sector rotation detection
│   │   ├── breadth_analyser.py            # Market breadth calculations
│   │   ├── liquidity_monitor.py           # Intraday liquidity assessment
│   │   └── README.md
│   │
│   ├── meta_learning/                     # Layer 3: Strategy weight learning
│   │   ├── __init__.py
│   │   ├── meta_learning_ai.py            # MetaLearningAI — primary class
│   │   ├── regime_strategy_map.py         # Regime → strategy weight map
│   │   ├── knn_weight_predictor.py        # k-NN weight prediction model
│   │   └── README.md
│   │
│   ├── opportunity_engine/                # Layer 4: Opportunity discovery
│   │   ├── __init__.py
│   │   ├── opportunity_engine.py          # OpportunityEngine — primary class
│   │   ├── equity_scanner.py              # NSE equity universe scanner
│   │   ├── options_scanner.py             # Options chain opportunity finder
│   │   ├── arbitrage_scanner.py           # Statistical arbitrage finder
│   │   └── README.md
│   │
│   ├── strategy_lab/                      # Layer 5: Strategy generation and evolution
│   │   ├── __init__.py
│   │   ├── meta_strategy_controller.py    # MetaStrategyController — primary class
│   │   ├── strategy_generator_ai.py       # AI-driven strategy generation
│   │   ├── backtesting_ai.py              # Walk-forward backtesting engine (PROTECTED)
│   │   ├── strategy_evolver.py            # Genetic strategy evolution
│   │   ├── strategy_fitness.py            # Fitness evaluation for evolved strategies
│   │   ├── evolved_strategies/            # Earned strategies (PROTECTED)
│   │   │   ├── momentum_breakout_v2.json
│   │   │   ├── mean_reversion_v1.json
│   │   │   └── README.md
│   │   └── README.md
│   │
│   ├── capital_risk_engine/               # Layer 6: Position sizing
│   │   ├── __init__.py
│   │   ├── capital_risk_engine.py         # CapitalRiskEngine — primary class
│   │   ├── kelly_calculator.py            # Kelly fraction position sizing
│   │   ├── budget_allocator.py            # Per-strategy budget allocation
│   │   └── README.md
│   │
│   ├── risk_control/                      # Layer 7: Portfolio risk management
│   │   ├── __init__.py
│   │   ├── risk_manager_ai.py             # RiskManagerAI — primary class
│   │   ├── portfolio_allocation.py        # Portfolio-level allocation rules
│   │   ├── stress_test.py                 # Stress test scenarios
│   │   ├── correlation_monitor.py         # Cross-position correlation
│   │   └── README.md
│   │
│   ├── market_simulation/                 # Layer 8: Monte Carlo simulation
│   │   ├── __init__.py
│   │   ├── monte_carlo_engine.py          # Monte Carlo — primary class
│   │   ├── scenario_generator.py          # 14 market scenario definitions
│   │   ├── simulation_runner.py           # Parallel simulation executor
│   │   └── README.md
│   │
│   ├── risk_guardian/                     # Layer 9: Kill-switch enforcement (PROTECTED)
│   │   ├── __init__.py
│   │   ├── risk_guardian.py               # RiskGuardian — primary class
│   │   ├── kill_switch.py                 # Kill-switch state management
│   │   ├── vix_monitor.py                 # VIX threshold monitor
│   │   └── README.md
│   │
│   ├── debate_engine/                     # Layer 10: 5-agent debate system
│   │   ├── __init__.py
│   │   ├── debate_engine.py               # DebateEngine — primary class
│   │   ├── decision_engine.py             # DecisionEngine (threshold 6.5)
│   │   ├── agents/                        # The 5 debate agents
│   │   │   ├── __init__.py
│   │   │   ├── bull_agent.py
│   │   │   ├── bear_agent.py
│   │   │   ├── risk_agent.py
│   │   │   ├── technical_agent.py
│   │   │   └── fundamental_agent.py
│   │   └── README.md
│   │
│   ├── execution_engine/                  # Layer 11: Order execution
│   │   ├── __init__.py
│   │   ├── order_manager.py               # OrderManager — primary class
│   │   └── README.md
│   │
│   ├── trade_monitoring/                  # Layer 12: Active trade supervision
│   │   ├── __init__.py
│   │   ├── trade_monitor.py               # TradeMonitor — primary class
│   │   ├── strategy_health_monitor.py     # StrategyHealthMonitor
│   │   ├── position_tracker.py            # Real-time position state
│   │   └── README.md
│   │
│   ├── learning_system/                   # Layer 13: Continuous learning
│   │   ├── __init__.py
│   │   ├── learning_engine.py             # LearningEngine — primary class
│   │   ├── strategy_performance_tracker.py # Win rate and auto-disable
│   │   ├── outcome_analyser.py            # Trade outcome attribution
│   │   └── README.md
│   │
│   ├── performance_analytics/             # Layer 14: Performance measurement
│   │   ├── __init__.py
│   │   ├── drawdown_analyser.py           # DrawdownAnalyser — primary class
│   │   ├── walk_forward_tester.py         # WalkForwardTester
│   │   ├── sharpe_calculator.py           # Sharpe ratio calculator
│   │   ├── attribution_engine.py          # P&L attribution analysis
│   │   └── README.md
│   │
│   ├── research_lab/                      # Layer 15: Strategy research and promotion
│   │   ├── __init__.py
│   │   ├── research_lab.py                # ResearchLab — primary class
│   │   ├── promotion_gate.py              # Promotion criteria (WinRate≥50%, Sharpe>0.8)
│   │   ├── hypothesis_generator.py        # New strategy hypothesis generator
│   │   └── README.md
│   │
│   ├── validation_engine/                 # Layer 16: 6-stage validation (PROTECTED)
│   │   ├── __init__.py
│   │   ├── validation_engine.py           # ValidationEngine — primary class
│   │   ├── stages/                        # 6 validation stages
│   │   │   ├── __init__.py
│   │   │   ├── stage_1_backtest.py
│   │   │   ├── stage_2_walk_forward.py
│   │   │   ├── stage_3_cross_market.py
│   │   │   ├── stage_4_monte_carlo.py
│   │   │   ├── stage_5_sensitivity.py
│   │   │   └── stage_6_regime.py
│   │   └── README.md
│   │
│   ├── control_tower/                     # Layer 17: Orchestration and telemetry
│   │   ├── __init__.py
│   │   ├── master_orchestrator.py         # MasterOrchestrator — primary class
│   │   ├── system_monitor.py              # SystemMonitor with layer timing
│   │   ├── event_bus.py                   # In-process EventBus
│   │   ├── telemetry.py                   # SQLite telemetry writer
│   │   ├── dashboard.py                   # Streamlit dashboard entry point
│   │   └── README.md
│   │
│   ├── data_feeds/                        # Data acquisition infrastructure
│   │   ├── __init__.py
│   │   ├── data_feed_manager.py           # DataFeedManager singleton
│   │   ├── yahoo_feed.py                  # YahooFeed (primary fallback)
│   │   ├── dhan_feed.py                   # DhanFeed (PROTECTED — broker auth)
│   │   └── README.md
│   │
│   ├── integrations/                      # External system integrations
│   │   ├── __init__.py
│   │   ├── brokers/                       # Broker-specific adapters
│   │   │   ├── __init__.py
│   │   │   ├── dhan_broker.py             # Dhan broker adapter
│   │   │   └── README.md
│   │   ├── data_sources/                  # Market data source adapters
│   │   │   ├── __init__.py
│   │   │   └── README.md
│   │   └── README.md
│   │
│   ├── notifications/                     # Notification delivery
│   │   ├── __init__.py
│   │   ├── telegram_bot.py                # Telegram bot (13 commands)
│   │   └── README.md
│   │
│   ├── security/                          # Security infrastructure
│   │   ├── __init__.py
│   │   ├── secrets_manager.py             # Environment secret loader
│   │   ├── token_store.py                 # API token lifecycle manager
│   │   └── README.md
│   │
│   ├── monitoring/                        # System health monitoring
│   │   ├── __init__.py
│   │   ├── health_checker.py              # Container health check endpoint
│   │   ├── cycle_monitor.py               # Cognitive cycle health tracker
│   │   └── README.md
│   │
│   ├── audit/                             # Compliance and audit
│   │   ├── __init__.py
│   │   ├── audit_writer.py                # Append-only audit log writer
│   │   ├── audit_reader.py                # Audit log query interface
│   │   └── README.md
│   │
│   └── scheduler/                         # Scheduling infrastructure
│       ├── __init__.py
│       ├── trading_scheduler.py           # APScheduler configuration and jobs
│       ├── job_registry.py                # Scheduler job definitions
│       └── README.md
│
├── tests/                                 # All test suites
│   ├── conftest.py                        # Shared fixtures (root level)
│   ├── unit/                              # Unit tests (per-package)
│   │   ├── common/
│   │   ├── config/
│   │   ├── global_intelligence/
│   │   ├── market_intelligence/
│   │   ├── meta_learning/
│   │   ├── opportunity_engine/
│   │   ├── strategy_lab/
│   │   ├── capital_risk_engine/
│   │   ├── risk_control/
│   │   ├── market_simulation/
│   │   ├── risk_guardian/
│   │   ├── debate_engine/
│   │   ├── execution_engine/
│   │   ├── trade_monitoring/
│   │   ├── learning_system/
│   │   ├── performance_analytics/
│   │   ├── research_lab/
│   │   ├── validation_engine/
│   │   ├── control_tower/
│   │   ├── data_feeds/
│   │   ├── integrations/
│   │   ├── notifications/
│   │   ├── security/
│   │   └── scheduler/
│   ├── integration/                       # Integration test suites
│   │   ├── test_full_cycle.py
│   │   ├── test_data_feed_failover.py
│   │   ├── test_kill_switch_propagation.py
│   │   └── test_broker_simulation.py
│   ├── performance/                       # Performance and latency tests
│   │   ├── test_cycle_latency.py
│   │   ├── test_layer_timing.py
│   │   └── test_feed_throughput.py
│   └── security/                          # Security-focused tests
│       ├── test_secrets_not_logged.py
│       ├── test_input_validation.py
│       └── test_sql_injection.py
│
├── deployment/                            # All deployment artefacts
│   ├── docker/                            # Docker configuration
│   │   ├── Dockerfile                     # Application container
│   │   ├── Dockerfile.dashboard           # Dashboard container
│   │   └── docker-compose.yml             # Multi-container composition
│   ├── kubernetes/                        # Future Kubernetes configuration (placeholder)
│   │   └── README.md
│   ├── scripts/                           # Operational scripts
│   │   ├── autostart.bat                  # Windows Task Scheduler entry point
│   │   ├── setup_windows_task.py          # Task Scheduler registration
│   │   ├── deploy.sh                      # VPS deployment script
│   │   └── healthcheck.sh                 # Container health check script
│   └── environments/                      # Environment configuration templates
│       ├── .env.development.template
│       ├── .env.testing.template
│       └── .env.production.template
│
├── data/                                  # Runtime data (persistent, not version controlled)
│   ├── trading_brain.db                   # Primary SQLite database
│   ├── telemetry.db                       # Telemetry and layer timing SQLite
│   ├── paper_trades.csv                   # Paper trading order journal
│   ├── audit.log                          # Append-only audit log
│   ├── datasets/                          # Historical market data snapshots
│   │   ├── nifty_1y_1d.parquet
│   │   ├── banknifty_1y_1d.parquet
│   │   └── README.md
│   └── backups/                           # Automated database backups
│       └── README.md
│
├── reports/                               # Generated report output
│   ├── eod/                               # End-of-day generated reports
│   ├── performance/                       # Performance analytics output
│   ├── audit/                             # Audit report exports
│   └── README.md
│
├── models/                                # Trained ML model artefacts
│   ├── knn_strategy_weights.pkl           # k-NN model for Layer 3
│   ├── regime_classifier.pkl              # Regime classification model
│   └── README.md
│
├── notebooks/                             # Jupyter analysis notebooks
│   ├── strategy_analysis.ipynb
│   ├── regime_analysis.ipynb
│   ├── performance_review.ipynb
│   └── README.md
│
├── prompts/                               # AI prompt template library
│   ├── debate_agent_prompts/
│   │   ├── bull_agent_system.md
│   │   ├── bear_agent_system.md
│   │   ├── risk_agent_system.md
│   │   ├── technical_agent_system.md
│   │   └── fundamental_agent_system.md
│   ├── strategy_generation_prompts/
│   └── README.md
│
├── tools/                                 # Developer tooling (not deployed)
│   ├── audit_stale.py                     # Stale code audit tool
│   ├── readiness_suite.py                 # Deployment readiness checker
│   ├── pnl_analysis.py                    # Manual P&L analysis
│   └── README.md
│
├── logs/                                  # Runtime log output (not version controlled)
│   └── .gitkeep
│
├── main.py                                # Application entry point
├── config.py                              # Master configuration file
├── requirements.txt                       # Python dependency manifest
├── requirements-dev.txt                   # Development-only dependencies
├── .env                                   # Local environment secrets (never committed)
├── .env.example                           # Non-secret env var documentation
├── .gitignore                             # Version control exclusion rules
├── .pylintrc                              # Pylint code quality configuration
├── pyproject.toml                         # Python project metadata and build config
├── README.md                              # Project overview and quickstart
└── ARCHITECTURE.md                        # Architecture overview (executive summary)
```

---

### 2.3 Top-Level Folder Summary

| Folder | Type | Version Controlled | Purpose |
|---|---|---|---|
| `.github/` | Infrastructure | Yes | CI/CD, AI assistant configuration |
| `docs/` | Documentation | Yes | All architectural and engineering documents |
| `src/` | Source code | Yes | All production Python packages |
| `tests/` | Test code | Yes | All test suites |
| `deployment/` | Infrastructure | Yes | Docker, scripts, environment templates |
| `data/` | Runtime data | No (`.gitignore`) | Live databases, journals, datasets |
| `reports/` | Generated output | No | Generated reports |
| `models/` | ML artefacts | Yes (if small) / LFS (if large) | Trained model files |
| `notebooks/` | Analysis | Yes | Jupyter analysis notebooks |
| `prompts/` | AI templates | Yes | AI agent prompt library |
| `tools/` | Dev tooling | Yes | Non-deployed developer scripts |
| `logs/` | Log output | No | Runtime log files |

---

### 2.4 Root-Level File Summary

| File | Purpose |
|---|---|
| `main.py` | Application entry point: `--paper`, `--telegram`, `--status` flags |
| `config.py` | Master configuration: all constants, thresholds, schedule definitions |
| `requirements.txt` | Production Python dependencies |
| `requirements-dev.txt` | Development-only tools (pytest, pylint, mypy) |
| `.env` | Local secrets: API keys, tokens (never committed to version control) |
| `.env.example` | Template of required environment variables (no values, committed) |
| `.gitignore` | Excludes: `data/`, `logs/`, `__pycache__/`, `.env`, model artefacts |
| `.pylintrc` | Pylint rules enforcing ENGINEERING_STANDARDS.md Part IV |
| `pyproject.toml` | Package metadata, build system, test runner configuration |
| `README.md` | Project overview, quickstart instructions |
| `ARCHITECTURE.md` | Executive-level architecture overview (entry point for new readers) |

---

## PART III — MODULE OWNERSHIP

### 3.1 Ownership Framework

Every folder in this repository has exactly one owner, one declared purpose, one set of allowed imports, and one set of forbidden imports. Ownership is not a social designation — it is a governance boundary. The owner of a module is responsible for:

- Maintaining the module's single declared responsibility
- Reviewing all changes proposed to the module
- Ensuring test coverage does not fall below the required minimum
- Keeping the module's `README.md` current
- Ensuring all imports respect the declared boundary rules

---

### 3.2 Shared Library — `src/common/`

| Attribute | Value |
|---|---|
| **Purpose** | Shared library of pure utilities, base classes, interfaces, and DTOs with no business logic |
| **Owner** | Engineering (all teams) |
| **Dependencies** | Python standard library only |
| **Consumers** | All 17 layer packages, data_feeds, integrations, notifications, scheduler |
| **Producers** | N/A — common is never a consumer of project packages |
| **Allowed imports** | Python stdlib: `abc`, `dataclasses`, `datetime`, `enum`, `logging`, `typing`, `uuid` |
| **Forbidden imports** | Any project package: `global_intelligence`, `market_intelligence`, any layer |
| **Boundary rule** | `common/` may NEVER import from any other project package. Violation of this rule introduces a circular dependency. |

**Sub-module ownership:**

| Module | Responsibility | Key Constraint |
|---|---|---|
| `base_agent.py` | Abstract contract for all 62+ agents | No agent business logic |
| `base_feed.py` | Abstract contract for data feed adapters | Defines `get_quote`, `get_history` |
| `base_strategy.py` | Abstract contract for all strategies | No strategy-specific logic |
| `errors.py` | Complete exception hierarchy for the project | All custom exceptions defined here |
| `logging_factory.py` | Returns configured logger instances | Does not configure handlers (done in main) |
| `time_utils.py` | Market hours, UTC conversion, IST helpers | No business rules about market behaviour |
| `symbol_utils.py` | Symbol formatting, NSE/BSE routing, suffix handling | No data fetching |
| `validation.py` | Type, range, and presence validation primitives | Raises typed exceptions from `errors.py` |
| `models/` | All shared DTO classes | Immutable where possible; `frozen=True` |

---

### 3.3 Configuration — `src/config/`

| Attribute | Value |
|---|---|
| **Purpose** | Single source of truth for all configuration values, schemas, and validation |
| **Owner** | Control Tower (Layer 17) |
| **Dependencies** | `src/common/` only |
| **Consumers** | All packages |
| **Producers** | Human Principal (config values), `main.py` (startup validation call) |
| **Allowed imports** | `common/`, Python stdlib |
| **Forbidden imports** | All layer packages, `data_feeds/`, `integrations/`, `notifications/` |
| **Boundary rule** | Config reads environment variables at import time. No network calls. No file I/O beyond env loading. |

---

### 3.4 Layer 1 — `src/global_intelligence/`

| Attribute | Value |
|---|---|
| **Purpose** | Fetch and cache global market context: S&P 500, Nikkei, bonds, FX, VIX. Produce `GlobalSnapshot`. |
| **Owner** | GlobalIntelligence team |
| **Dependencies** | `src/common/`, `src/config/`, `src/data_feeds/` |
| **Consumers** | Layer 2 (`market_intelligence`), Layer 17 (`control_tower`) |
| **Producers** | `data_feeds/` provides raw data |
| **Allowed imports** | `common/`, `config/`, `data_feeds/` |
| **Forbidden imports** | Layers 2–17, `strategy_lab/`, `execution_engine/`, `notifications/` |
| **Boundary rule** | GlobalIntelligence NEVER fetches data from external APIs directly. All data acquisition goes through `data_feeds/DataFeedManager`. Latency WARN: 5,000ms. Latency CRIT: 12,000ms. |

---

### 3.5 Layer 2 — `src/market_intelligence/`

| Attribute | Value |
|---|---|
| **Purpose** | Classify the current market regime, sector leadership, breadth, liquidity, and pending events. Produce `RegimeSignal`. |
| **Owner** | MarketIntelligence team |
| **Dependencies** | `common/`, `config/`, `data_feeds/`, `global_intelligence/` (reads `GlobalSnapshot`) |
| **Consumers** | Layers 3–10, `control_tower/` |
| **Producers** | Layer 1 provides `GlobalSnapshot`; `data_feeds/` provides instrument data |
| **Allowed imports** | `common/`, `config/`, `data_feeds/`, `global_intelligence/` |
| **Forbidden imports** | Layers 3–17, `execution_engine/`, `integrations/` |
| **Boundary rule** | MarketIntelligence reads global data but does NOT generate trade hypotheses. Hypothesis generation belongs in Layer 5. |

---

### 3.6 Layer 3 — `src/meta_learning/`

| Attribute | Value |
|---|---|
| **Purpose** | Learn which strategies perform best in which regimes. Predict strategy weights using k-NN. |
| **Owner** | MetaLearning team |
| **Dependencies** | `common/`, `config/`, `data_feeds/`, `market_intelligence/` |
| **Consumers** | Layer 5 (`strategy_lab/`) — consumes strategy weight recommendations |
| **Producers** | Layer 13 (`learning_system/`) — provides historical strategy performance data |
| **Allowed imports** | `common/`, `config/`, `market_intelligence/` (regime signal only) |
| **Forbidden imports** | Layers 4–17 except Layer 13 performance data (via DTO) |
| **Boundary rule** | MetaLearning predicts weights; it does NOT generate or execute strategies. |

---

### 3.7 Layer 4 — `src/opportunity_engine/`

| Attribute | Value |
|---|---|
| **Purpose** | Scan the NSE equity universe, options chains, and statistical arbitrage opportunities. Output ranked opportunity list. |
| **Owner** | OpportunityEngine team |
| **Dependencies** | `common/`, `config/`, `data_feeds/`, `market_intelligence/`, `meta_learning/` |
| **Consumers** | Layer 5 (`strategy_lab/`) |
| **Producers** | Data feeds provide raw market data |
| **Allowed imports** | `common/`, `config/`, `data_feeds/`, `market_intelligence/`, `meta_learning/` |
| **Forbidden imports** | Layers 5–17 |
| **Boundary rule** | OpportunityEngine identifies opportunities but does NOT generate trade hypotheses or execute orders. |

---

### 3.8 Layer 5 — `src/strategy_lab/`

| Attribute | Value |
|---|---|
| **Purpose** | Generate, evolve, and select trading strategies. Produce trade hypotheses for Layer 6. |
| **Owner** | StrategyLab team |
| **Dependencies** | `common/`, `config/`, `data_feeds/`, Layers 1–4 |
| **Consumers** | Layer 6 (`capital_risk_engine/`) |
| **Producers** | Layers 1–4 provide market context; `evolved_strategies/` provides historical strategies |
| **Allowed imports** | `common/`, `config/`, `data_feeds/`, Layers 1–4 |
| **Forbidden imports** | Layers 6–17 |
| **Boundary rule** | `backtesting_ai.py` and `evolved_strategies/` are PROTECTED. No modification without explicit approval. Strategy generation does NOT access order management or broker interfaces. |

---

### 3.9 Layers 6–9 — Capital, Risk, Simulation, Guardian

| Package | Purpose | Allowed Imports | Forbidden Imports |
|---|---|---|---|
| `capital_risk_engine/` | Kelly fraction sizing, per-strategy budgets | `common/`, `config/`, Layers 1–5 | Layers 7–17 |
| `risk_control/` | Portfolio allocation, correlation, stress testing | `common/`, `config/`, Layers 1–6 | Layers 8–17 |
| `market_simulation/` | 14-scenario Monte Carlo, parallel simulation | `common/`, `config/`, Layers 1–7 | Layers 9–17 |
| `risk_guardian/` | Kill-switch enforcement, VIX monitoring | `common/`, `config/`, Layers 1–8 | Layers 10–17 |

**Critical Rule:** `risk_guardian/` is PROTECTED. The kill-switch logic is intentional and calibrated. No speculative modification.

---

### 3.10 Layer 10 — `src/debate_engine/`

| Attribute | Value |
|---|---|
| **Purpose** | Run the 5-agent debate: Bull, Bear, Risk, Technical, Fundamental. Score conviction. Accept or reject hypothesis at threshold 6.5. |
| **Owner** | DebateEngine team |
| **Dependencies** | `common/`, `config/`, Layers 1–9 |
| **Consumers** | Layer 11 (`execution_engine/`) |
| **Producers** | Layers 1–9 provide context for agents |
| **Allowed imports** | `common/`, `config/`, Layers 1–9 |
| **Forbidden imports** | Layers 11–17 |
| **Boundary rule** | The 5 debate agents within `agents/` may only import from `common/` and `config/`. They do not directly access any data feed or database. Context is provided to them by `debate_engine.py`. |

---

### 3.11 Layer 11 — `src/execution_engine/`

| Attribute | Value |
|---|---|
| **Purpose** | Receive approved `DecisionRecord` and `RiskApproval`. Submit orders to broker (paper or live). |
| **Owner** | ExecutionEngine team |
| **Dependencies** | `common/`, `config/`, `integrations/brokers/` |
| **Consumers** | Layer 12 (`trade_monitoring/`) |
| **Producers** | Layer 10 produces `DecisionRecord`; Layer 7 produces `RiskApproval` |
| **Allowed imports** | `common/`, `config/`, `integrations/brokers/` |
| **Forbidden imports** | All strategy layers (1–10), `market_intelligence/`, `debate_engine/` |
| **Boundary rule** | Execution NEVER generates its own trading decisions. It only executes approved orders. Explicit `PAPER_TRADING` check is mandatory before any real broker call. |

---

### 3.12 Layers 12–16 — Monitoring, Learning, Analytics, Research, Validation

| Package | Purpose | Key Constraint |
|---|---|---|
| `trade_monitoring/` | Supervise open positions, enforce stop-loss, trigger exits | May not open new positions |
| `learning_system/` | Attribute outcomes to strategies, update win rate tracker | Records only; does not modify strategies |
| `performance_analytics/` | Drawdown analysis, Sharpe, walk-forward results | Read-only analysis; no trading decisions |
| `research_lab/` | Evaluate strategy candidates, check promotion gates | May promote to `evolved_strategies/` only with gate pass |
| `validation_engine/` | 6-stage pipeline (PROTECTED) | Promotion criteria hardcoded; no speculative changes |

---

### 3.13 Layer 17 — `src/control_tower/`

| Attribute | Value |
|---|---|
| **Purpose** | Orchestrate all 17 layers. Schedule cognitive cycles. Write telemetry. Expose Streamlit dashboard. |
| **Owner** | Control Tower team (Human Principal) |
| **Dependencies** | All packages (reads from all layers) |
| **Consumers** | `main.py` (entry point) |
| **Producers** | N/A — Control Tower consumes; it does not produce business objects |
| **Allowed imports** | All project packages |
| **Forbidden imports** | None — but must maintain unidirectional data flow |
| **Boundary rule** | `MasterOrchestrator` calls layers in declared order (1→17). It never calls a lower-numbered layer from within a higher-numbered layer's execution context. |

---

### 3.14 Infrastructure Packages

| Package | Purpose | Allowed Imports | Forbidden Imports |
|---|---|---|---|
| `data_feeds/` | Acquire raw market data (Yahoo, Dhan) | `common/`, `config/`, `security/` | All layer packages |
| `integrations/` | Broker and data source adapters | `common/`, `config/`, `security/` | All layer packages |
| `notifications/` | Telegram bot delivery | `common/`, `config/`, `security/` | Layer packages (reads telemetry DB directly) |
| `security/` | Secret loading, token management | `common/`, Python stdlib only | All layer and infrastructure packages |
| `monitoring/` | Health check endpoint, cycle monitor | `common/`, `config/`, `control_tower/` telemetry | Trading layers |
| `audit/` | Append-only audit log | `common/`, `config/` | All other packages |
| `scheduler/` | APScheduler job definitions | `common/`, `config/`, `control_tower/` | Layer packages |

---

## PART IV — REPOSITORY DEPENDENCY RULES

### 4.1 Layer Dependency Hierarchy

Dependencies in this repository follow a strict unidirectional hierarchy. A package may only import from packages at a lower layer number. No upward imports. No cross-layer shortcuts. This rule is absolute.

```
Layer 17: control_tower          ← imports from: all layers
Layer 16: validation_engine      ← imports from: Layers 1–15
Layer 15: research_lab           ← imports from: Layers 1–14
Layer 14: performance_analytics  ← imports from: Layers 1–13
Layer 13: learning_system        ← imports from: Layers 1–12
Layer 12: trade_monitoring       ← imports from: Layers 1–11
Layer 11: execution_engine       ← imports from: common, config, integrations
Layer 10: debate_engine          ← imports from: Layers 1–9
Layer  9: risk_guardian          ← imports from: Layers 1–8
Layer  8: market_simulation      ← imports from: Layers 1–7
Layer  7: risk_control           ← imports from: Layers 1–6
Layer  6: capital_risk_engine    ← imports from: Layers 1–5
Layer  5: strategy_lab           ← imports from: Layers 1–4
Layer  4: opportunity_engine     ← imports from: Layers 1–3
Layer  3: meta_learning          ← imports from: Layers 1–2
Layer  2: market_intelligence    ← imports from: Layer 1
Layer  1: global_intelligence    ← imports from: data_feeds only
─────────────────────────────────
Infrastructure (no layer number):
data_feeds        ← imports from: common, config, security
integrations      ← imports from: common, config, security
notifications     ← imports from: common, config, security
security          ← imports from: common only
audit             ← imports from: common, config
scheduler         ← imports from: common, config, control_tower
monitoring        ← imports from: common, config
─────────────────────────────────
Foundation (no layer number):
common            ← imports from: Python stdlib only
config            ← imports from: common only
```

---

### 4.2 Import Hierarchy Matrix

The following matrix shows allowed imports (✓) and forbidden imports (✗) between top-level packages. The consuming package is in the rows; the producing package is in the columns.

| Consumer → | common | config | data_feeds | L1 | L2 | L3 | L4 | L5 | L6 | L7 | L8 | L9 | L10 | L11 | L12 | L13 | L14 | L15 | L16 | L17 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| common | — | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| config | ✓ | — | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| data_feeds | ✓ | ✓ | — | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| L1 | ✓ | ✓ | ✓ | — | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| L2 | ✓ | ✓ | ✓ | ✓ | — | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| L3 | ✓ | ✓ | ✗ | ✗ | ✓ | — | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| L4 | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | — | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| L5 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| L6 | ✓ | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| L7 | ✓ | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| L8 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| L9 | ✓ | ✓ | ✗ | ✓ | ✓ | ✗ | ✗ | ✗ | ✓ | ✓ | ✓ | — | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| L10 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| L11 | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | — | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| L12 | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ | ✗ | ✓ | ✗ | ✓ | — | ✗ | ✗ | ✗ | ✗ | ✗ |
| L13 | ✓ | ✓ | ✗ | ✗ | ✗ | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ | — | ✗ | ✗ | ✗ | ✗ |
| L14 | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ | ✓ | ✓ | — | ✗ | ✗ | ✗ |
| L15 | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ | ✓ | — | ✗ | ✗ |
| L16 | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ | ✓ | ✓ | ✓ | — | ✗ |
| L17 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — |

---

### 4.3 Circular Dependency Prevention

Circular imports are strictly prohibited. A circular import occurs when package A imports package B, and package B imports package A — directly or transitively. In Python, circular imports cause one of two failure modes:
- `ImportError` at startup
- Partially-initialised module (the more dangerous case — no error, but incorrect state)

**Prevention rules:**

| Rule | Description |
|---|---|
| CD-01 | The unidirectional import hierarchy (4.2 matrix) prevents all direct circular imports. |
| CD-02 | If a higher layer needs to call into a lower layer, it does so by passing a DTO — not by importing the lower layer from within the lower layer's execution context. |
| CD-03 | Data flows down (higher layers consume lower layer outputs). Control flows up (lower layers do not call into higher layers). |
| CD-04 | Callbacks from lower layers to higher layers are implemented through `EventBus` (publish-subscribe) — never through direct imports. |
| CD-05 | Singleton getters (`get_feed_manager()`, `get_performance_tracker()`) are defined in their owning package and registered in `control_tower/`. Higher layers call the getter, not the class constructor. |
| CD-06 | All cross-package communication uses the DTOs defined in `common/models/`. DTOs have no dependencies on any project package. |

---

### 4.4 Shared Library Policy

The `common/` package is the only approved shared library. It is subject to the following governance rules:

| Policy | Detail |
|---|---|
| No business logic | `common/` contains utilities, base classes, and DTOs only. Market-specific logic belongs in a layer. |
| Stdlib-only imports | `common/` imports from Python standard library only. No third-party packages (except `typing`). |
| Stable interface | Changes to `common/` public interfaces require an ADR because all 17+ packages depend on them. |
| Additive only | New additions to `common/` are always additive. Existing public interfaces are never removed or renamed. |
| Review required | All PRs that modify `common/` require review by at least one senior engineer plus Human Principal awareness. |

**What belongs in `common/`:**

| Belongs | Does Not Belong |
|---|---|
| `BaseFeed` abstract class | Any concrete feed implementation |
| `TickerQuote` DTO | Any market data fetching logic |
| `FeedTimeoutError` exception | Any retry or backoff logic |
| `is_market_open()` time utility | Any decisions based on market hours |
| `format_symbol()` utility | Any symbol routing decisions |

---

### 4.5 Core Module Policy

Core modules are modules that other modules depend on. The higher the number of packages that depend on a module, the more strictly it is governed. Core module tiers are:

| Tier | Modules | Dependent Count | Change Policy |
|---|---|---|---|
| Tier 0 (Foundation) | `common/errors.py`, `common/models/` | All packages | ADR + Human Principal approval required |
| Tier 1 (Framework) | `common/base_agent.py`, `common/base_feed.py`, `common/base_strategy.py` | 62+ agents, 3+ feeds | ADR + senior review |
| Tier 2 (Configuration) | `config/config.py` | All packages | Additive allowed freely; deletion requires ADR |
| Tier 3 (Infrastructure) | `data_feeds/data_feed_manager.py`, `security/secrets_manager.py` | 5+ packages | PR review + test |
| Tier 4 (Layer) | Individual layer primary classes | 1–3 packages | Standard PR process |

---

### 4.6 Plugin Policy

The plugin pattern allows new capabilities to be added without modifying existing code. The following extension points use the plugin pattern:

| Extension Point | Location | Plugin Type | Registration |
|---|---|---|---|
| Data feed adapters | `src/data_feeds/` | New `BaseFeed` subclass | Register in `DataFeedManager` |
| Broker adapters | `src/integrations/brokers/` | New broker adapter class | Register in `OrderManager` |
| Notification channels | `src/notifications/` | New notification sender | Register in `NotificationDispatcher` |
| Debate agents | `src/debate_engine/agents/` | New `BaseAgent` subclass | Register in `DebateEngine` |
| Strategies | `src/strategy_lab/evolved_strategies/` | New JSON strategy file | Loaded by `StrategyGeneratorAI` |
| Validation stages | `src/validation_engine/stages/` | New stage module | Register in `ValidationEngine` pipeline |

For each extension point, the plugin follows the pattern:
1. Implement the declared abstract base class from `common/`
2. Place the implementation in the designated folder
3. Register the implementation in the designated registry or manager
4. Write unit tests in the corresponding `tests/unit/` sub-folder
5. Update the package `README.md`

No modification to existing code is required to add a plugin.

---

### 4.7 Extension Policy

An extension is different from a plugin. A plugin adds a new instance of an existing type (a new feed, a new agent). An extension adds a new capability type to the system (a new layer, a new infrastructure service).

Extensions require:
1. An ADR documenting the extension and its placement in the architecture
2. A new package in `src/` following the standard package structure
3. A position in the layer hierarchy declared and documented
4. Dependency rules declared in Part III of this document (via amendment)
5. A test suite in `tests/unit/<new_package>/`
6. Human Principal approval before implementation begins

---

## PART V — SHARED COMPONENTS

### 5.1 Shared Component Catalogue

Shared components are components that are used by more than one package. They live in `src/common/` (or in the designated infrastructure packages for infrastructure concerns). Every shared component has a single, named responsibility. No shared component accumulates more than one responsibility.

This catalogue is authoritative. A component does not exist as a shared component unless it appears in this catalogue.

---

### 5.2 Utilities

#### 5.2.1 Time Utilities (`common/time_utils.py`)

| Function | Signature | Purpose |
|---|---|---|
| `is_market_open()` | `() -> bool` | Returns True if current UTC time falls within NSE market hours |
| `is_pre_market()` | `() -> bool` | Returns True if current time is in the pre-market window |
| `ist_now()` | `() -> datetime` | Returns current datetime in IST (UTC+5:30) |
| `utc_now()` | `() -> datetime` | Returns current UTC datetime (timezone-aware) |
| `to_ist()` | `(dt: datetime) -> datetime` | Converts any timezone-aware datetime to IST |
| `market_open_time()` | `() -> datetime` | Returns today's market open in UTC |
| `market_close_time()` | `() -> datetime` | Returns today's market close in UTC |
| `minutes_to_close()` | `() -> int` | Returns minutes remaining until market close (0 if closed) |
| `trading_day_of_week()` | `() -> bool` | Returns True if today is Monday–Friday |
| `iso_date_str()` | `() -> str` | Returns today's date as `YYYY-MM-DD` string |

**Boundary constraints:** No network calls. No database reads. No business rules beyond market session definition.

---

#### 5.2.2 Symbol Utilities (`common/symbol_utils.py`)

| Function | Signature | Purpose |
|---|---|---|
| `to_nse_symbol()` | `(symbol: str) -> str` | Appends `.NS` suffix if not already present |
| `to_yahoo_symbol()` | `(symbol: str, exchange: str) -> str` | Maps instrument to Yahoo Finance ticker format |
| `strip_exchange_suffix()` | `(symbol: str) -> str` | Removes `.NS`, `.BO`, `.BSE` suffixes |
| `is_index_symbol()` | `(symbol: str) -> bool` | Returns True for NIFTY, BANKNIFTY, and other index symbols |
| `is_options_symbol()` | `(symbol: str) -> bool` | Returns True for an options contract symbol |
| `parse_options_components()` | `(symbol: str) -> OptionsComponents` | Parses expiry, strike, type from options symbol |
| `global_to_local()` | `(global_symbol: str) -> str` | Maps S&P 500 (`^GSPC`) to local equivalent |

**Boundary constraints:** No data fetching. No market state awareness. Pure string transformation.

---

#### 5.2.3 Validation Utilities (`common/validation.py`)

| Function | Signature | Purpose |
|---|---|---|
| `require_not_none()` | `(value: Any, name: str) -> None` | Raises `ValidationError` if value is None |
| `require_positive()` | `(value: float, name: str) -> None` | Raises `ValidationError` if value ≤ 0 |
| `require_in_range()` | `(value: float, min: float, max: float, name: str) -> None` | Raises `ValidationError` if out of range |
| `require_non_empty_string()` | `(value: str, name: str) -> None` | Raises `ValidationError` if empty or whitespace |
| `require_valid_symbol()` | `(symbol: str) -> None` | Raises `ValidationError` if symbol format is invalid |
| `require_positive_int()` | `(value: int, name: str) -> None` | Raises `ValidationError` if not a positive integer |
| `clamp()` | `(value: float, min: float, max: float) -> float` | Returns value clamped to [min, max] range |

**Boundary constraints:** Raises only exceptions from `common/errors.py`. No logging. No side effects.

---

#### 5.2.4 Logging Factory (`common/logging_factory.py`)

| Function | Signature | Purpose |
|---|---|---|
| `get_logger()` | `(name: str) -> logging.Logger` | Returns a logger with the given hierarchical name |
| `get_layer_logger()` | `(layer_name: str, module_name: str) -> logging.Logger` | Returns a layer-namespaced logger |

**Convention:** Modules call `get_logger(__name__)` which produces a logger named `package.module`. Log handler configuration (file rotation, format, level) is done once at startup in `main.py`, not in modules.

---

### 5.3 Error Hierarchy (`common/errors.py`)

Every custom exception in the system extends from one of the project's root exception classes. This enables callers to catch at the appropriate level of specificity.

```
TradingBrainError                    ← root of all custom exceptions
├── ConfigurationError               ← config missing, invalid, out of range
├── ValidationError                  ← input validation failed
├── DataError                        ← data quality problems
│   ├── FeedUnavailableError         ← no data source available
│   ├── FeedTimeoutError             ← data source timed out
│   ├── StaleDataError               ← data older than permitted age
│   └── MalformedDataError           ← data structure is invalid
├── TradingError                     ← trading business logic errors
│   ├── KillSwitchActiveError        ← kill-switch is set
│   ├── InsufficientCapitalError     ← insufficient budget for order
│   ├── RiskApprovalExpiredError     ← risk approval is too old
│   ├── PositionLimitExceededError   ← position count limit reached
│   └── OrderRejectedError           ← broker rejected the order
├── StrategyError                    ← strategy lifecycle errors
│   ├── StrategyNotFoundError        ← strategy ID unknown
│   ├── StrategyDisabledError        ← strategy auto-disabled
│   └── BacktestFailedError          ← backtesting error
├── BrokerError                      ← broker communication errors
│   ├── AuthenticationError          ← broker auth failed
│   ├── TokenExpiredError            ← API token expired
│   └── BrokerAPIError               ← unexpected broker API response
├── SecurityError                    ← security policy violations
│   ├── SecretNotFoundError          ← required secret not in environment
│   └── TokenValidationError         ← token format/signature invalid
└── SystemError                      ← infrastructure errors
    ├── LayerTimeoutError            ← layer exceeded CRIT latency
    ├── DatabaseError                ← SQLite operation failed
    └── SchedulerError               ← job scheduling error
```

---

### 5.4 Abstract Base Classes

#### 5.4.1 `BaseFeed` (`common/base_feed.py`)

Abstract base class for all market data feed adapters.

| Method | Signature | Mandatory | Purpose |
|---|---|---|---|
| `get_quote` | `(symbol: str) -> Optional[TickerQuote]` | Yes | Fetch current price for a single symbol |
| `get_multiple_quotes` | `(symbols: List[str]) -> Dict[str, TickerQuote]` | Yes | Fetch current prices for multiple symbols |
| `get_history` | `(symbol: str, days: int, interval: str) -> List[PriceBar]` | Yes | Fetch historical OHLCV bars |
| `is_available` | `() -> bool` | Yes | Return True if this feed is currently reachable |
| `get_feed_name` | `() -> str` | Yes | Return human-readable name for logging |

#### 5.4.2 `BaseAgent` (`common/base_agent.py`)

Abstract base class for all 62+ AI agents.

| Method | Signature | Mandatory | Purpose |
|---|---|---|---|
| `analyse` | `(context: AgentContext) -> AgentOpinion` | Yes | Produce a scored opinion on the trade hypothesis |
| `get_agent_name` | `() -> str` | Yes | Return the agent's unique name |
| `get_agent_role` | `() -> AgentRole` | Yes | Return the agent's declared role (BULL, BEAR, etc.) |
| `get_weight` | `() -> float` | No | Return this agent's debate weight (default 1.0) |

#### 5.4.3 `BaseStrategy` (`common/base_strategy.py`)

Abstract base class for all trading strategy implementations.

| Method | Signature | Mandatory | Purpose |
|---|---|---|---|
| `generate_hypothesis` | `(context: MarketContext) -> Optional[TradeHypothesis]` | Yes | Generate a trade hypothesis or return None |
| `get_strategy_id` | `() -> str` | Yes | Return stable unique strategy identifier |
| `get_strategy_family` | `() -> StrategyFamily` | Yes | Return strategy family (MOMENTUM, MEAN_REVERSION, etc.) |
| `get_min_confidence` | `() -> float` | Yes | Return minimum context confidence required to generate |
| `get_min_rr` | `() -> float` | Yes | Return minimum reward-to-risk ratio to generate |

---

### 5.5 Shared Data Transfer Objects (`common/models/`)

| DTO | Purpose | Frozen | Key Fields |
|---|---|---|---|
| `TickerQuote` | Current market price for one symbol | Yes | `symbol`, `ltp`, `bid`, `ask`, `volume`, `timestamp` |
| `PriceBar` | One OHLCV bar | Yes | `symbol`, `open`, `high`, `low`, `close`, `volume`, `timestamp`, `interval` |
| `GlobalSnapshot` | Complete global market state | Yes | `sp500_change`, `vix_level`, `nikkei_change`, `bonds_yield_10y`, `usd_inr`, `timestamp` |
| `RegimeSignal` | Classified market regime | Yes | `regime_type`, `confidence`, `sub_regime`, `breadth_score`, `timestamp` |
| `TradeHypothesis` | Proposed trade | No | `symbol`, `direction`, `entry_price`, `stop_loss`, `target`, `strategy_id`, `conviction_basis` |
| `DecisionRecord` | Approved decision after debate | Yes | `hypothesis`, `conviction_score`, `agent_votes`, `approved_at`, `decision_id` |
| `OrderRecord` | Submitted or simulated order | No | `decision_id`, `symbol`, `direction`, `quantity`, `entry_price`, `status`, `submitted_at` |
| `RiskApproval` | Risk management sign-off | Yes | `decision_id`, `approved_quantity`, `approved_capital`, `approved_at`, `expires_at` |

---

### 5.6 Common Model Design Constraints

| Constraint | Rule |
|---|---|
| Immutability | All DTOs that cross layer boundaries use `@dataclass(frozen=True)` |
| No methods | DTOs contain data only. No business logic methods. |
| No circular references | DTO A does not contain DTO B if DTO B also contains DTO A |
| Type annotations | Every field has a type annotation |
| Optional fields | Optional fields use `Optional[T]` and default to `None` |
| Timestamps | All timestamps are UTC, timezone-aware `datetime` objects |
| IDs | All IDs are UUID4 strings |

---

## PART VI — CONFIGURATION ARCHITECTURE

### 6.1 Configuration Philosophy

Configuration is the set of values that governs how the system behaves without changing its code. In the AI Trading Brain, configuration covers three distinct concerns:

| Concern | Examples | Location |
|---|---|---|
| Operational constants | Thresholds, limits, intervals, latency targets | `config.py` |
| Secrets | API keys, tokens, Telegram credentials | Environment variables (`.env`) |
| Feature flags | Paper trading mode, telegram mode, experimental features | `config.py` + `feature_flags.py` |
| Environment-specific config | VPS host, logging level, data paths | Environment variables |

The master rule: **No secret value, no credential, no token ever appears in any source file.** All secrets are loaded from environment variables at runtime. All source files are safe to commit publicly.

---

### 6.2 Master Configuration File (`config.py`)

`config.py` is the single source of truth for all operational constants. It is located at the repository root (current) and will be migrated to `src/config/config.py` as part of the package restructuring.

**Sections within `config.py`:**

| Section | Constants It Contains |
|---|---|
| Layer Latency | `LAYER_LATENCY_WARN_MS`, `LAYER_LATENCY_CRIT_MS`, per-layer overrides |
| Schedule | All `SCHEDULE_*` slot definitions (pre-market, hourly, EOD, etc.) |
| Risk Parameters | `DAILY_LOSS_LIMIT`, `MAX_OPEN_POSITIONS`, `KILL_SWITCH_VIX_THRESHOLD` |
| Capital | `PAPER_CAPITAL`, `LIVE_CAPITAL`, `PER_STRATEGY_BUDGET_PCT` |
| Data Feeds | `YAHOO_TIMEOUT_SECONDS`, `DATA_CACHE_TTL_SECONDS` |
| Strategy | `MIN_SIGNAL_RR`, `MIN_WIN_RATE_PCT`, `AUTO_DISABLE_THRESHOLD` |
| Debate | `CONVICTION_THRESHOLD`, `NUM_DEBATE_AGENTS` |
| Symbol Maps | `GLOBAL_SYMBOL_MAP`, `NSE_INDEX_MAP`, `SECTOR_ETF_MAP` |
| Monitoring | `CONTINUOUS_SCAN_INTERVAL`, `HEARTBEAT_INTERVAL_SECONDS` |
| Paths | `DB_PATH`, `TELEMETRY_DB_PATH`, `PAPER_TRADES_CSV`, `AUDIT_LOG_PATH` |

**Rules for `config.py`:**

| Rule | Detail |
|---|---|
| All values `UPPER_SNAKE_CASE` | Never camelCase, never lowercase |
| Inline comment per value | Explains purpose and allowed range |
| No conditional logic | Config file is data, not code |
| No imports from project packages | May import from `os` and `pathlib` only |
| No network calls | Never fetches remote config |
| No secret values | All secrets loaded from environment |
| Validated at startup | `validate_config()` called from `main.py` |

---

### 6.3 Environment Configuration

The environment defines how the system behaves in a specific deployment context. Three environments are defined:

#### 6.3.1 Development Environment

| Attribute | Value |
|---|---|
| Purpose | Local development and debugging |
| Paper trading | Always enabled |
| Log level | `DEBUG` |
| Data source | Yahoo Finance (no Dhan token required) |
| Database path | `data/trading_brain.db` (local) |
| Scheduler | May be disabled for interactive testing |
| Config file | `.env.development` (loaded from template `.env.development.template`) |

#### 6.3.2 Testing Environment

| Attribute | Value |
|---|---|
| Purpose | Automated test suite execution |
| Paper trading | Always enabled |
| Log level | `WARNING` (suppress normal output in tests) |
| Data source | Mocked feeds (no real network calls) |
| Database path | In-memory SQLite or temporary file |
| Scheduler | Disabled (tests control timing directly) |
| Config file | `.env.testing` (loaded from template `.env.testing.template`) |

#### 6.3.3 Production Environment

| Attribute | Value |
|---|---|
| Purpose | Live VPS deployment (Docker) |
| Paper trading | Controlled by `PAPER_TRADING=true/false` env var |
| Log level | `INFO` |
| Data source | Dhan (primary) → Yahoo Finance (fallback) |
| Database path | `/app/data/trading_brain.db` (Docker volume mount) |
| Scheduler | Always active |
| Config file | Environment variables injected by Docker Compose |

---

### 6.4 Secret Inventory

The following secrets are required. All secrets are loaded from environment variables. None appear in source code.

| Secret Name | Purpose | Required In | Rotation Period |
|---|---|---|---|
| `DHAN_ACCESS_TOKEN` | Dhan API authentication | Production | Daily (auto-refresh via OAuth) |
| `DHAN_CLIENT_ID` | Dhan account identifier | Production | Never (account-bound) |
| `TELEGRAM_BOT_TOKEN` | Telegram bot authentication | All | Never (revoke if compromised) |
| `TELEGRAM_CHAT_ID` | Authorised chat for commands | All | When chat changes |
| `VPS_SSH_KEY` | VPS deployment authentication | CI/CD | Annually |
| `GITHUB_ACTIONS_TOKEN` | CI/CD pipeline authentication | CI/CD | Annually |

**Secret loading pattern:** Secrets are loaded once at startup in `src/security/secrets_manager.py`. The `SecretsManager` validates that all required secrets are present and non-empty. If any required secret is missing, the process raises `SecretNotFoundError` and exits before any market activity begins.

**Secret rotation:** Whenever a secret is rotated, the new value is set in the appropriate environment (Docker secrets, GitHub Actions secrets, local `.env`). The process is restarted. No code change is required.

---

### 6.5 Feature Flags (`feature_flags.py`)

Feature flags are boolean values that enable or disable capabilities at runtime without requiring a code deployment.

| Flag | Default | Purpose | Controlled By |
|---|---|---|---|
| `PAPER_TRADING` | `True` | Disable real order submission; log to CSV only | Environment variable |
| `TELEGRAM_ENABLED` | `True` | Enable/disable Telegram bot | Environment variable |
| `CONTINUOUS_SCAN_ENABLED` | `True` | Enable/disable 30s market monitor | `config.py` |
| `OPTIONS_SCANNING_ENABLED` | `False` | Enable options opportunity scanning | `config.py` |
| `ARBITRAGE_SCANNING_ENABLED` | `False` | Enable arbitrage scanning | `config.py` |
| `WALK_FORWARD_DAILY` | `True` | Run WFT in EOD learning cycle | `config.py` |
| `STRESS_TEST_ENABLED` | `True` | Include stress testing in Layer 7 | `config.py` |
| `MONTE_CARLO_ENABLED` | `True` | Run Monte Carlo simulation | `config.py` |
| `AUTO_DISABLE_STRATEGIES` | `True` | Allow StrategyHealthMonitor to disable strategies | `config.py` |
| `DEBUG_CYCLE_TIMING` | `False` | Log per-layer timing on every cycle | `config.py` |

**Feature flag rule:** Feature flags are read once per cycle, not cached across cycles. This allows flags to be changed via Telegram bot commands and take effect on the next cycle without restart.

---

### 6.6 Runtime Configuration

Runtime configuration is configuration that can change while the process is running, without a restart:

| Capability | Mechanism | Who Controls |
|---|---|---|
| Toggle feature flags | Telegram bot `/flag` command | Human Principal |
| Update strategy weights | Telegram bot `/learn` command triggers meta-learning | Automated (MetaLearningAI) |
| Check current config | Telegram bot `/status` command | Human Principal |
| Emergency kill | Telegram bot `/kill` command | Human Principal |
| Resume after kill | Telegram bot `/resume` command | Human Principal |
| Force EOD learning | Telegram bot `/learn` command | Human Principal |

Runtime configuration changes are not persisted across restarts. On restart, all values return to the values declared in `config.py` and environment variables.

---

### 6.7 Configuration Validation

`validate_config()` in `src/config/validator.py` runs at process startup and validates:

| Validation Category | Checks |
|---|---|
| Required secrets | All secrets in the Secret Inventory are present and non-empty |
| Required constants | All mandatory `config.py` constants are defined and not `None` |
| Range validation | Numeric constants within declared allowed ranges (e.g., `CONVICTION_THRESHOLD` ∈ [5.0, 9.0]) |
| Path validation | All path constants point to existing directories or creatable files |
| Type validation | All constants are of the expected Python type |
| Dependency validation | If `DHAN_ACCESS_TOKEN` is present, `DHAN_CLIENT_ID` must also be present |

If any validation fails, the process logs the specific failure, raises `ConfigurationError`, and exits. The system never starts in a misconfigured state.

---

### 6.8 Configuration Schema (`config/schema.py`)

The configuration schema documents every configuration value in a machine-readable format for validation and documentation purposes.

| Schema Element | Purpose |
|---|---|
| `name` | Constant name |
| `type` | Python type (`float`, `int`, `str`, `bool`, `dict`, `list`) |
| `required` | Whether the value must be present |
| `default` | Default value if not specified (None if no default) |
| `min_value` | Minimum allowed value (numeric only) |
| `max_value` | Maximum allowed value (numeric only) |
| `allowed_values` | Enumerated allowed values (for string constants) |
| `description` | Human-readable explanation |
| `env_var` | Environment variable name (for secret-sourced values) |
| `category` | Grouping for display and documentation |

---

## PART VII — RESOURCE ORGANISATION

### 7.1 Resource Philosophy

Resources are all non-source artefacts that the system creates, reads, or maintains during operation. Resources fall into two categories:

| Category | Description | Version Controlled |
|---|---|---|
| Static resources | Created by humans; committed to the repository | Yes |
| Runtime resources | Created by the running system; excluded from version control | No |

The boundary between these two categories is enforced by `.gitignore`. No runtime resource ever enters version control.

---

### 7.2 Reports Organisation (`reports/`)

Reports are generated outputs produced by the system during operation and by developer tooling.

```
reports/
├── eod/                    # End-of-day performance reports
│   ├── YYYY-MM-DD_eod.md   # Daily EOD report (generated nightly)
│   └── README.md
├── performance/            # Multi-day performance analytics
│   ├── weekly/
│   ├── monthly/
│   └── README.md
├── audit/                  # Compliance and audit exports
│   ├── YYYY-MM-DD_audit_export.csv
│   └── README.md
├── backtesting/            # Strategy backtesting outputs
│   ├── YYYY-MM-DD_<strategy_id>_backtest.md
│   └── README.md
└── README.md
```

**Report naming convention:** `YYYY-MM-DD_<type>_<optional_qualifier>.md`

**Report retention policy:**
- EOD reports: 365 days
- Performance reports: Indefinite
- Audit exports: Indefinite (compliance requirement)
- Backtesting reports: 90 days (retained if strategy is promoted)

**Report format standards:**
- All reports are Markdown for human readability
- All dates in ISO 8601 format
- All monetary values in INR unless otherwise specified
- All performance metrics defined in the Performance Analytics Glossary

---

### 7.3 Log Files Organisation (`logs/`)

Log files are produced by the running process. They are rotated daily and retained according to the retention policy.

```
logs/
├── trading_brain_YYYY-MM-DD.log    # Primary application log (rotated daily)
├── audit_YYYY-MM-DD.log            # Immutable audit trail
├── cycle_YYYY-MM-DD.log            # Per-cycle timing log (if DEBUG mode)
└── .gitkeep                        # Ensures folder exists in version control
```

**Log retention policy:**

| Log Type | Retention | Reason |
|---|---|---|
| Application log | 30 days | Operational troubleshooting |
| Audit log | Indefinite | Compliance and trade audit |
| Cycle timing log | 7 days | Performance debugging only |

**Log rotation:** Python `logging.handlers.TimedRotatingFileHandler` configured at midnight IST. Old logs are compressed (`.gz`) after rotation.

**Log file naming:** Follows the convention `<component>_<YYYY-MM-DD>.log` as specified in ENGINEERING_STANDARDS.md Part III.

---

### 7.4 Data Organisation (`data/`)

Runtime data encompasses all persistent state maintained by the running system.

```
data/
├── trading_brain.db        # Primary SQLite database (WAL mode)
│                           # Tables: decisions, orders, positions,
│                           #         strategy_stats, outcomes, agents
├── telemetry.db            # Layer timing and system health (WAL mode)
│                           # Tables: cycle_timings, layer_timings,
│                           #         feed_health, scheduler_events
├── paper_trades.csv        # Paper trading order journal
│                           # Columns: decision_id, symbol, direction,
│                           #          quantity, entry, stop, target,
│                           #          status, submitted_at, closed_at, pnl
├── audit.log               # Append-only structured audit trail
│                           # Format: timestamp | level | actor | action | detail
├── feature_flags.json      # Runtime feature flag overrides (optional)
├── datasets/               # Historical market data snapshots
│   ├── nifty_1y_1d.parquet     # NIFTY 50 1-year daily OHLCV
│   ├── banknifty_1y_1d.parquet # BANKNIFTY 1-year daily OHLCV
│   ├── nifty_6m_5m.parquet     # NIFTY 50 6-month 5-minute OHLCV
│   └── README.md
└── backups/                # Automated database backups
    ├── trading_brain_backup_YYYYMMDD.db.gz
    └── README.md
```

**Database governance:**

| Rule | Detail |
|---|---|
| WAL mode mandatory | All SQLite databases use `PRAGMA journal_mode=WAL` |
| Single writer | One process writes to each database at a time |
| Concurrent readers | WAL mode allows concurrent reads during writes |
| Schema migrations | Handled by migration scripts in `deployment/scripts/`; never destructive |
| Backup schedule | Daily at EOD (automated by APScheduler) |
| Backup retention | 30 daily backups; then weekly for 6 months |
| No business logic in SQL | Only data storage; no stored procedures |
| No production data in version control | `data/` is in `.gitignore` |

---

### 7.5 Datasets Organisation (`data/datasets/`)

Datasets are historical market data snapshots used for backtesting and strategy validation.

| Dataset | Format | Source | Refresh Frequency |
|---|---|---|---|
| NIFTY 50 daily (1 year) | Parquet | yfinance | Weekly |
| BANKNIFTY daily (1 year) | Parquet | yfinance | Weekly |
| NIFTY 50 5-minute (6 months) | Parquet | yfinance | Weekly |
| Nifty 50 constituent daily | Parquet | yfinance | Monthly |
| NSE sector ETF daily | Parquet | yfinance | Weekly |
| Global indices daily | Parquet | yfinance | Weekly |

**Dataset naming convention:** `<instrument>_<lookback>_<interval>.parquet`

Example: `nifty50_1y_1d.parquet`, `banknifty_6m_5m.parquet`

**Dataset validation:** Every dataset loaded into a backtesting or validation pipeline is validated for:
- No missing dates on trading days
- No extreme outlier prices (>10σ from rolling mean)
- Correct interval consistency
- Minimum required bars (as defined by strategy's minimum history requirement)

---

### 7.6 Backup Organisation (`data/backups/`)

| Backup Type | Naming Convention | Compression | Retention |
|---|---|---|---|
| Daily database | `trading_brain_backup_YYYYMMDD.db.gz` | gzip | 30 days |
| Weekly database | `trading_brain_backup_YYYY-WNN.db.gz` | gzip | 26 weeks |
| Configuration backup | `config_backup_YYYYMMDD.tar.gz` | gzip | 30 days |
| Evolved strategy backup | `strategies_backup_YYYYMMDD.tar.gz` | gzip | 90 days |

Backups are verified for integrity after creation (MD5 checksum). The checksum is stored alongside the backup file: `<backup_filename>.md5`.

---

### 7.7 Templates Organisation (`docs/templates/`)

Templates are Markdown and text file skeletons for recurring document types.

| Template | Path | Used For |
|---|---|---|
| ADR template | `docs/templates/adr_template.md` | Architecture Decision Records |
| EOD report template | `docs/templates/eod_report_template.md` | Nightly EOD reports |
| Incident report template | `docs/templates/incident_report_template.md` | Post-incident analysis |
| Strategy proposal template | `docs/templates/strategy_proposal_template.md` | New strategy proposals |
| Module README template | `docs/templates/module_readme_template.md` | All package READMEs |

---

### 7.8 Prompt Library Organisation (`prompts/`)

The prompt library stores AI agent system prompts as versioned Markdown files.

```
prompts/
├── debate_agent_prompts/
│   ├── bull_agent_system_v1.md      # Bull agent system prompt
│   ├── bear_agent_system_v1.md      # Bear agent system prompt
│   ├── risk_agent_system_v1.md      # Risk agent system prompt
│   ├── technical_agent_system_v1.md # Technical agent system prompt
│   └── fundamental_agent_v1.md      # Fundamental agent system prompt
├── strategy_generation_prompts/
│   ├── hypothesis_generator_v1.md   # Strategy hypothesis generation
│   └── regime_classifier_v1.md      # Regime classification
└── README.md
```

**Prompt versioning:** Prompt files include a version suffix (`_v1`, `_v2`). When a prompt is updated, a new version file is created rather than overwriting the existing one. The active version is declared in `config.py`.

---

### 7.9 Knowledge Assets Organisation (`docs/ontology/`)

Knowledge assets are human-maintained reference documents that define the domain vocabulary and classification systems.

| Asset | Path | Contents |
|---|---|---|
| Market taxonomy | `docs/ontology/market_taxonomy.md` | NSE/BSE market structure, session times, holidays |
| Instrument classification | `docs/ontology/instrument_classification.md` | Equity, index, F&O, currency, commodity classifications |
| Regime taxonomy | `docs/ontology/regime_taxonomy.md` | All regime types and sub-regime types with definitions |
| Strategy taxonomy | `docs/ontology/strategy_taxonomy.md` | Strategy family hierarchy with examples |
| Sector classification | `docs/ontology/sector_classification.md` | NSE sector definitions and ETF mappings |

---

### 7.10 AI Model Artefacts Organisation (`models/`)

Trained machine learning model artefacts are stored in `models/` and version-controlled when their file size permits.

| Artefact | Path | Format | Size Policy |
|---|---|---|---|
| k-NN strategy weight model | `models/knn_strategy_weights.pkl` | pickle | <10 MB: commit directly |
| Regime classifier | `models/regime_classifier.pkl` | pickle | <10 MB: commit directly |
| Strategy score scaler | `models/strategy_score_scaler.pkl` | pickle | <5 MB: commit directly |
| Large model artefacts | `models/<name>.pkl` | pickle | >10 MB: Git LFS |

**Model metadata:** Every model file has a companion metadata file: `models/<name>_metadata.json` containing: training date, training dataset summary, model parameters, validation metrics (accuracy, precision, recall, Sharpe improvement), and the engineer who trained it.

---

## PART VIII — REPOSITORY GOVERNANCE

### 8.1 Governance Overview

Repository governance defines how the repository is owned, how changes are authorised, how versions are managed, and how the repository evolves over time. Governance prevents the repository from drifting from its design without conscious decision-making.

The governance structure has three levels:

| Level | Role | Responsibilities |
|---|---|---|
| L1 | Human Principal | Final approval on architectural changes, protected modules, major releases |
| L2 | Engineering | Day-to-day PR review, code quality, test coverage enforcement |
| L3 | Automated | CI/CD pipeline: lint, test, security scan on every commit |

---

### 8.2 Ownership Model

Every folder and every module has exactly one declared owner. Ownership is not shared. When a change is proposed to a module, the owner reviews it. If the owner cannot review, the review falls to the next higher governance level.

**Ownership Assignment:**

| Package / Folder | Owner Role | Protection Level |
|---|---|---|
| `src/common/` | Engineering | L1 — Human Principal approval for interface changes |
| `src/config/` | Control Tower | L2 — PR review required |
| `src/global_intelligence/` | GlobalIntelligence | L2 — PR review required |
| `src/market_intelligence/` | MarketIntelligence | L2 — PR review required |
| `src/meta_learning/` | MetaLearning | L2 — PR review required |
| `src/opportunity_engine/` | OpportunityEngine | L2 — PR review required |
| `src/strategy_lab/` | StrategyLab | L2 — PR review required |
| `src/strategy_lab/backtesting_ai.py` | StrategyLab | L1 — PROTECTED: Human Principal only |
| `src/strategy_lab/evolved_strategies/` | StrategyLab | L1 — PROTECTED: Human Principal only |
| `src/capital_risk_engine/` | CapitalRisk | L2 — PR review required |
| `src/risk_control/` | RiskControl | L2 — PR review required |
| `src/market_simulation/` | MarketSim | L2 — PR review required |
| `src/risk_guardian/` | RiskGuardian | L1 — PROTECTED: Human Principal only |
| `src/debate_engine/` | DebateEngine | L2 — PR review required |
| `src/execution_engine/` | ExecutionEngine | L2 — PR review required |
| `src/trade_monitoring/` | TradeMonitoring | L2 — PR review required |
| `src/learning_system/` | LearningSystem | L2 — PR review required |
| `src/performance_analytics/` | PerformanceAnalytics | L2 — PR review required |
| `src/research_lab/` | ResearchLab | L2 — PR review required |
| `src/validation_engine/` | ValidationEngine | L1 — PROTECTED: Human Principal only |
| `src/control_tower/` | ControlTower | L1 — Human Principal approval for orchestration changes |
| `src/data_feeds/dhan_feed.py` | DataFeeds | L1 — PROTECTED: broker auth |
| `data/` | Control Tower | L1 — No destructive operations |
| `.github/copilot-instructions.md` | Human Principal | L1 — Human Principal only |

---

### 8.3 Versioning Policy

The AI Trading Brain follows Semantic Versioning (SemVer):

```
MAJOR.MINOR.PATCH

MAJOR: Incremented when backward-incompatible architectural changes are made
MINOR: Incremented when new capabilities are added in a backward-compatible manner
PATCH: Incremented when backward-compatible bug fixes are applied
```

**Version increment rules:**

| Change Type | Version Impact | Example |
|---|---|---|
| New layer added | MAJOR | 1.0.0 → 2.0.0 |
| Existing interface changed | MAJOR | 1.2.0 → 2.0.0 |
| New module added to existing layer | MINOR | 1.2.0 → 1.3.0 |
| New feature flag added | MINOR | 1.2.0 → 1.3.0 |
| Bug fix (no interface change) | PATCH | 1.2.3 → 1.2.4 |
| Documentation only | PATCH | 1.2.3 → 1.2.4 |
| Security fix | PATCH | 1.2.3 → 1.2.4 |
| Performance improvement (no interface change) | PATCH | 1.2.3 → 1.2.4 |

**Version tracking locations:**
- `pyproject.toml`: `[project] version = "M.m.p"`
- Git tag: `vM.m.p` on the commit that increments the version
- `CHANGELOG.md`: Every version has a dated entry

---

### 8.4 Deprecation Policy

When a public interface must be changed rather than extended, the old interface must be deprecated before it is removed.

**Deprecation process:**

| Step | Action | Timeline |
|---|---|---|
| 1 | Mark the interface with a deprecation warning in its docstring | Immediately |
| 2 | Emit a `DeprecationWarning` at runtime when the deprecated path is called | Immediately |
| 3 | Provide the new interface alongside the old | Immediately |
| 4 | Update all internal callers to use the new interface | Within 1 release cycle |
| 5 | Remove the deprecated interface | MAJOR version increment |

**Minimum deprecation window:** One full release cycle (one MAJOR or MINOR version). No interface is removed in the same version it is deprecated.

---

### 8.5 Migration Policy

When a module or package must be moved, renamed, or split:

| Step | Requirement |
|---|---|
| ADR required | Document the migration: what moves, where, and why |
| Compatibility shim | Old import path provides the class from the new location (`from new.module import X`) |
| No broken imports | No PR may merge that breaks any existing import before the shim is in place |
| Shim retention | The compatibility shim stays for one full MAJOR version |
| Update all callers | Before removing the shim, all callers in the project are updated |

**Migration is forbidden for:**
- Protected modules (see 8.2) without explicit Human Principal approval
- Any module while it is currently used by a live trading position

---

### 8.6 Review Policy

All changes to production code must pass through the PR review process.

**PR Requirements Checklist:**

| Requirement | Mandatory |
|---|---|
| Branch follows naming convention (`feature/`, `fix/`, `hotfix/`) | Yes |
| Commit messages follow the conventional commit format | Yes |
| All existing tests pass (CI/CD gate) | Yes |
| New code has unit tests | Yes |
| Code coverage does not decrease | Yes |
| Pylint score ≥ 8.0/10 (or improved) | Yes |
| No new secrets in source code | Yes |
| No new circular dependencies | Yes |
| Module README updated if behaviour changes | Yes |
| `copilot-instructions.md` `Files Modified` table updated | Yes |
| ADR created if the change is architectural | Conditional |
| Human Principal approval if protected module | Conditional |

---

### 8.7 Release Process

A release is a tagged, deployed version of the software that has passed all quality gates.

**Release stages:**

| Stage | Actions | Gate to Pass |
|---|---|---|
| 1. Development | Feature branch → commits → local testing | All unit tests pass |
| 2. Integration | Merge to `main` → CI/CD triggered | CI pipeline green |
| 3. Staging | Deploy to VPS with `PAPER_TRADING=true` | Both containers healthy |
| 4. Production verification | Run paper trading for 1 full trading day | No errors, cycle health ≥ 95% |
| 5. Release tag | `git tag vM.m.p` on verified commit | Human Principal approval |
| 6. Deploy | `docker compose build --no-cache && docker compose up -d` | Both containers Up (healthy) |
| 7. CHANGELOG | Entry added to `CHANGELOG.md` | Document complete |

**Release authority:**
- PATCH: Engineering authorises
- MINOR: Engineering authorises with Human Principal awareness
- MAJOR: Human Principal authorises

---

### 8.8 Approval Workflow

The following changes require written approval before implementation begins:

| Change Category | Approver | Approval Form |
|---|---|---|
| Modification to a protected module | Human Principal | Explicit written instruction in Telegram or document |
| MAJOR version increment | Human Principal | Written in ADR |
| New broker integration | Human Principal | ADR + security review |
| New external data source | Engineering | ADR |
| Schema migration on `data/trading_brain.db` | Human Principal | Migration plan document |
| New environment variable / secret | Engineering | Config PR + secret rotation plan |
| Disabling a kill-switch condition | Human Principal | Explicit written instruction |
| Change to promotion gate thresholds | Human Principal | Written in ADR with rationale |
| New thread (beyond existing 8) | Engineering | ADR |

---

### 8.9 Rollback Policy

A rollback reverts the deployed system to a previously known-good state. Rollback is triggered when:
- A deployment fails (containers not healthy after 5 minutes)
- A live production anomaly is detected post-deployment
- A cycle health metric falls below 90% after deployment

**Rollback procedure:**

| Step | Command | Purpose |
|---|---|---|
| 1 | `docker compose down` | Stop current containers |
| 2 | `git checkout vM.m.p` | Check out the last known-good tag |
| 3 | `docker compose build --no-cache` | Rebuild from known-good source |
| 4 | `docker compose up -d` | Restart |
| 5 | Verify `docker compose ps` | Confirm both containers healthy |
| 6 | Send Telegram alert | Notify Human Principal |
| 7 | Create incident report | Document cause and timeline |

**Rollback authority:** Engineering may initiate a rollback without Human Principal approval in a production emergency. Human Principal must be notified within 30 minutes.

---

## PART IX — REPOSITORY EVOLUTION

### 9.1 Evolution Philosophy

A repository must be able to evolve. Markets change, capabilities grow, and the IIOS vision expands beyond its initial scope. The key challenge is enabling this evolution without destabilising what already works.

The AI Trading Brain's evolution model follows three principles:

**Principle 1 — Add, don't modify.** When in doubt, add a new module rather than modify an existing one. This preserves all existing behaviour while introducing new capability.

**Principle 2 — Grow within established boundaries.** New modules belong inside existing packages when they fit the package's declared responsibility. If they don't fit, a new package is created — but only after an ADR documents the boundary decision.

**Principle 3 — Make new code, not new architecture.** Architecture is stable. Code grows inside it. When new code no longer fits the existing architecture, that is a signal to update the architecture document — not to silently violate it.

---

### 9.2 Adding a New Module to an Existing Package

The most common evolution event. A new capability is added inside an existing layer.

| Step | Action |
|---|---|
| 1 | Confirm the new module's responsibility fits within the existing package's declared responsibility (Part III) |
| 2 | Confirm the new module's required imports are allowed by the package's import rules |
| 3 | Create the module file in the correct package directory |
| 4 | Write the module docstring, class docstring, and method docstrings |
| 5 | Export the class in the package's `__init__.py` |
| 6 | Write unit tests in `tests/unit/<package>/test_<module>.py` |
| 7 | Update the package's `README.md` |
| 8 | Update `copilot-instructions.md` `Files Modified` table |
| 9 | Submit PR following review policy |
| 10 | Deploy after merge |

No ADR is required for an additive module that fits within an existing package boundary.

---

### 9.3 Adding a New Package (New Layer)

When the system needs a capability that does not fit in any existing package, a new package is created.

| Step | Action | Requires |
|---|---|---|
| 1 | Draft a proposal: new package name, responsibility, position in layer order, dependency rules | ADR |
| 2 | Confirm no existing package's responsibility already covers this | Part III review |
| 3 | Determine layer number and update the layer hierarchy | Part III, Part IV amendment |
| 4 | Human Principal approval | Written approval |
| 5 | Create the package directory in `src/` with `__init__.py` and `README.md` | — |
| 6 | Declare ownership, dependencies, allowed/forbidden imports in Part III (via document amendment) | Document amendment |
| 7 | Create mirror test directory in `tests/unit/<new_package>/` | — |
| 8 | Implement the package | Standard development |
| 9 | Integrate with `MasterOrchestrator` if it is an operational layer | Layer 17 update |
| 10 | Update `ARCHITECTURE.md` and this document | Document amendments |

---

### 9.4 Plugin Architecture

The plugin architecture allows new implementations of existing types to be added without modifying the core system. The six plugin extension points are defined in Part IV (4.6). This section describes the plugin lifecycle.

**Plugin Lifecycle:**

| Phase | Description |
|---|---|
| Design | Plugin author defines the concrete implementation of the relevant abstract base class |
| Implementation | Plugin is implemented in the designated folder |
| Registration | Plugin registers itself with the relevant manager or engine |
| Testing | Plugin has dedicated unit tests and integration tests |
| Activation | Plugin is enabled via feature flag or configuration |
| Monitoring | Plugin health is tracked by the system monitor |
| Retirement | Plugin is disabled via feature flag; then deprecated; then removed after one release cycle |

**Plugin discovery pattern:** Plugin managers use one of two discovery patterns:

- **Explicit registration:** The plugin class is imported by name in the manager's configuration (e.g., `DataFeedManager` has a priority-ordered list of feed classes to try)
- **Directory scan:** The manager scans a designated directory and loads all valid plugins found (e.g., `StrategyGeneratorAI` loads all JSON files from `evolved_strategies/`)

---

### 9.5 Extension Mechanism

Extensions are new top-level capabilities added to the system. Unlike plugins (which add new instances of existing types), extensions add new system types.

**Current extension roadmap (planned, not implemented):**

| Extension | Description | Planned Layer |
|---|---|---|
| News Intelligence | Real-time news sentiment feeding Layer 2 | 1.5 (between L1 and L2) |
| Options Intelligence | Full options chain analysis and Greek calculation | New package in L4 |
| Multi-Broker Router | Route orders across multiple brokers by capital efficiency | New package in L11 |
| FX Intelligence | Currency market awareness for global trading | L1 extension |
| Mobile API | REST API for mobile dashboard | New infrastructure package |
| Alerting Engine | Sophisticated alert rules beyond Telegram | New infrastructure package |

Each planned extension has a designated location in the repository architecture. When implemented, the extension must:
1. Fit into the designated location (or justify a different location via ADR)
2. Implement the relevant base class from `common/`
3. Not modify any existing package's public interface
4. Have a complete test suite before activation

---

### 9.6 Backward Compatibility Policy

Backward compatibility means that existing code that calls a module's public interface continues to work correctly after a module is updated.

**Levels of backward compatibility:**

| Level | Guarantee |
|---|---|
| Source compatible | Existing source code compiles without changes |
| Behaviorally compatible | Existing code produces the same results |
| Protocol compatible | Existing data files, databases, and serialised objects are still readable |

**What must remain backward compatible:**
- All public method signatures (names, parameters, return types)
- All DTO field names and types in `common/models/`
- All database table schemas (columns can be added; columns cannot be removed or renamed)
- All configuration constant names in `config.py` (values can change; names cannot)
- All environment variable names
- All Telegram bot command names and responses

**What may change without a backward compatibility concern:**
- Private method implementations (`_` prefix)
- Internal algorithms within a module
- Log message text (not log levels)
- Report output formatting
- Test fixtures

---

### 9.7 Migration Strategy

When a backward-incompatible change is unavoidable, migration is performed in three phases:

| Phase | Duration | Actions |
|---|---|---|
| Phase 1: Dual interface | One release cycle | Old and new interfaces coexist; old emits `DeprecationWarning` |
| Phase 2: Internal migration | Same cycle | All internal callers migrate to new interface |
| Phase 3: Removal | Next MAJOR version | Old interface removed; new interface is canonical |

**Database migration strategy:** Schema changes use numbered migration scripts in `deployment/scripts/migrations/`:
- `migration_001_add_regime_column.sql`
- `migration_002_add_cycle_id_index.sql`

Migrations are applied at startup by the `MasterOrchestrator` if the database version (stored in a `schema_version` table) is behind the current code version. Migrations are additive (add column, add table, add index). Destructive operations (drop column, drop table) are never performed by migration scripts — only by Human Principal manual action.

---

### 9.8 Folder Lifecycle

Every folder in the repository has a lifecycle state:

| State | Description | Governance |
|---|---|---|
| Active | Folder is in use; code is maintained | Standard PR process |
| Deprecated | Folder's responsibility is being migrated; not for new code | Old code still runs; DeprecationWarning on import |
| Archived | Folder is read-only; exists for historical reference | Moved to `archive/` or Git tag |
| Planned | Folder is in the architecture but not yet created | This document declares it; implementation comes later |

**Planned folders** (declared in this document, not yet created):
- `src/knowledge/` — Domain knowledge layer (to be extracted from `config.py` as the system grows)
- `src/integrations/data_sources/` — External data source adapters beyond Yahoo Finance
- `deployment/kubernetes/` — Future Kubernetes deployment configuration
- `docs/templates/` — Document templates

---

### 9.9 Technical Debt Policy

Technical debt is tracked and managed explicitly. All known technical debt is recorded in `docs/engineering/adr/TECH_DEBT.md` with:
- Description of the debt
- Why it was incurred (time pressure, temporary workaround, etc.)
- Estimated cost to repay
- Target repayment version
- Owner

**Technical debt categories:**

| Category | Examples in this system | Priority |
|---|---|---|
| Structural debt | `config.py` at root (should be in `src/config/`) | Medium |
| Test debt | Missing unit tests for some Layer 3–5 modules | High |
| Documentation debt | Some modules lack complete docstrings | Medium |
| Dependency debt | Some utilities in root (should be in `tools/`) | Low |

**Debt repayment rule:** No new feature work begins in a sprint if any HIGH-priority technical debt item is more than 30 days old.

---

## PART X — REPOSITORY CONSTITUTION

### 10.1 Constitutional Authority

The Repository Constitution is the highest-level set of rules governing the AI Trading Brain repository. These rules are not guidelines. They are not recommendations. They are mandatory requirements. Every engineer working on this system is bound by these rules. Every automated tool is configured to enforce them. Every PR that violates these rules is rejected.

These rules exist to protect the system's architectural integrity, prevent hidden technical debt, and ensure that the repository remains a reliable and navigable home for the IIOS for the next ten years.

---

### 10.2 Category A — Structural Rules

| Rule | ID | Statement |
|---|---|---|
| One responsibility per folder | A-01 | Every folder in `src/` has exactly one declared responsibility. No folder accumulates responsibilities from multiple concerns. |
| One owner per module | A-02 | Every module (Python file) in `src/` has exactly one named owner. Shared ownership is not permitted. |
| No cross-layer shortcuts | A-03 | No package may import from a package at a higher layer number than itself. Layer N imports only from layers 1 through N-1. |
| No duplicate modules | A-04 | No two modules in the repository perform the same function. Before creating a new module, search for an existing one. |
| Mirror test structure | A-05 | Every package in `src/` has a corresponding folder in `tests/unit/`. The test folder mirrors the source folder structure exactly. |
| Root-level cleanliness | A-06 | The repository root contains only: `main.py`, `config.py`, `requirements*.txt`, `.env*`, `.gitignore`, `.pylintrc`, `pyproject.toml`, `README.md`, `ARCHITECTURE.md`, and the top-level domain folders. No other files at root. |
| Layer ordering preserved | A-07 | The 17-layer hierarchy may not be reordered. New layers inserted between existing layers require a MAJOR version increment and Human Principal approval. |
| Package structure mandatory | A-08 | Every package in `src/` must have: `__init__.py`, at least one primary class module, and `README.md`. |
| No test files in source | A-09 | No test file (`test_*.py`) may appear in `src/`. Tests live only in `tests/`. |
| Deployment artefacts isolated | A-10 | All Docker, CI/CD, and deployment scripts live in `deployment/`. No `Dockerfile` or `docker-compose.yml` at the repository root. |

---

### 10.3 Category B — Module Boundary Rules

| Rule | ID | Statement |
|---|---|---|
| `common/` never imports project packages | B-01 | `src/common/` imports from Python standard library only. It NEVER imports from any other project package. Violation: circular dependency. |
| `config/` never imports layer packages | B-02 | `src/config/` imports from `common/` and stdlib only. It NEVER imports from any layer package. |
| `security/` never imports layer packages | B-03 | `src/security/` imports from `common/` and stdlib only. It handles secrets; it does not handle trading. |
| `execution_engine/` never generates decisions | B-04 | `src/execution_engine/` receives approved decisions. It NEVER generates trade hypotheses, evaluates strategies, or calls into debate agents. |
| No business logic in `common/` | B-05 | `common/` contains utilities, base classes, and DTOs only. Market analysis, trading decisions, and strategy logic belong in the appropriate layer. |
| No data fetching in layer modules | B-06 | Layer modules (1–17) do not call `yf.download()` or any network API directly. All data acquisition goes through `data_feeds/DataFeedManager`. |
| No direct database access from layer modules | B-07 | Layer modules do not open SQLite connections directly. Database access goes through the designated repository classes in `control_tower/`. |
| No hardcoded credentials | B-08 | No module in `src/` contains a hardcoded API key, token, password, or any credential. All credentials are loaded from environment variables. |
| Kill-switch respected universally | B-09 | Every code path that would submit a real order checks the kill-switch state before proceeding. No code bypasses the kill-switch check. |
| No silent failures | B-10 | No `except Exception: pass` or equivalent. Every caught exception is either handled, re-raised, or logged at ERROR level with full context. |

---

### 10.4 Category C — Safety Rules

| Rule | ID | Statement |
|---|---|---|
| Paper trading mandatory by default | C-01 | `PAPER_TRADING=true` is the default state. Disabling paper trading requires explicit Human Principal instruction on every deployment. |
| Kill-switch is fail-safe | C-02 | The kill-switch defaults to ACTIVE (orders blocked). It must be explicitly cleared to allow orders. Process restart does not automatically clear the kill-switch. |
| No destructive database operations in code | C-03 | No Python module may execute `DROP TABLE`, `DROP COLUMN`, or `DELETE FROM` without a `WHERE` clause on any production database. These operations require a dedicated migration script and Human Principal approval. |
| Risk approval expiry enforced | C-04 | Every `RiskApproval` has an `expires_at` timestamp. `OrderManager` rejects any approval older than `_APPROVAL_VALIDITY_SECONDS`. No approval may be extended programmatically. |
| Stop-loss mandatory on every hypothesis | C-05 | No `TradeHypothesis` may be approved without a valid `stop_loss` price. The debate engine rejects hypotheses with `stop_loss = None` or `stop_loss >= entry_price` (for long positions). |
| Maximum open positions enforced | C-06 | `OrderManager` rejects new orders when the count of open positions reaches `MAX_OPEN_POSITIONS` in `config.py`. This limit is not overridable at runtime. |
| Daily loss limit enforced | C-07 | When intraday realised P&L crosses `DAILY_LOSS_LIMIT`, the kill-switch is activated automatically. It is not reset until the next trading day. |
| VIX kill-switch enforced | C-08 | When VIX exceeds `KILL_SWITCH_VIX_THRESHOLD` (default 45), the kill-switch is activated. It is not reset until VIX falls below the threshold for a sustained period. |
| No order submission outside market hours | C-09 | `OrderManager` rejects order submission when `is_market_open()` returns False. Pre-market and post-market orders are not supported. |
| Protected module immutability | C-10 | Protected modules (`risk_guardian/risk_guardian.py`, `backtesting_ai.py`, `validation_engine/`, `evolved_strategies/`) may not be modified without explicit Human Principal approval. Any PR touching these files without approval is rejected. |

---

### 10.5 Category D — State Management Rules

| Rule | ID | Statement |
|---|---|---|
| Singletons accessed via getters only | D-01 | Singleton objects (`DataFeedManager`, `PerformanceTracker`, `RegimeStrategyMap`, `TelegramBot`) are never instantiated directly. They are always accessed via their registered getter function. |
| Shared state requires a lock | D-02 | Any data structure accessed from multiple threads uses a `threading.Lock` or `threading.RLock`. The lock is acquired via context manager (`with`). |
| No global mutable state in modules | D-03 | No module-level mutable variable is modified after module import. All mutable state lives inside class instances. |
| Database writes serialised | D-04 | Only one process writes to any given SQLite database at a time. WAL mode allows concurrent reads. |
| DTO immutability at boundaries | D-05 | All DTOs crossing layer boundaries are `frozen=True` dataclasses. They are not modified after creation. |
| No caching beyond declared TTL | D-06 | Cached values are invalidated after their declared TTL. No cache entry survives indefinitely. Cache staleness must trigger a refresh or a `StaleDataError`. |
| Thread names declared | D-07 | Every `threading.Thread` in the system has a declared `name`. The thread registry in the Engineering Blueprint is kept current. |
| No thread communication via global | D-08 | Threads communicate via `threading.Queue`, `threading.Event`, or thread-safe data structures. Never via shared module-level variables. |

---

### 10.6 Category E — Observability Rules

| Rule | ID | Statement |
|---|---|---|
| Every cycle has a correlation ID | E-01 | Every cognitive cycle begins by generating a `cycle_id` (UUID4). This ID is propagated through all 17 layers and appears in all log messages and database records for that cycle. |
| Layer timing recorded | E-02 | `SystemMonitor.time_layer()` wraps every layer call in `MasterOrchestrator`. Layer duration is recorded to `telemetry.db`. |
| No silent success for significant events | E-03 | All significant events (order submitted, kill-switch activated, strategy disabled, daily loss limit reached) are logged at INFO level and sent to Telegram. |
| Error logs include context | E-04 | Every error log includes: what was being attempted, what failed, relevant identifiers (symbol, strategy_id, cycle_id), and the exception type. |
| Audit trail is append-only | E-05 | The audit log (`data/audit.log`) is written by `audit/audit_writer.py` using append-only file access. No audit record is ever modified or deleted. |
| EOD report mandatory | E-06 | The scheduler must produce an EOD report every trading day, even if no trades occurred. A missing EOD report is an incident. |
| Health check endpoint active | E-07 | The container health check endpoint (`/health`) must respond within 10 seconds. A non-response causes Docker Compose to mark the container as unhealthy. |
| Heartbeat logged every interval | E-08 | The monitoring thread logs a heartbeat message at `DEBUG` level every `HEARTBEAT_INTERVAL_SECONDS`. Missing heartbeats for >3 intervals is an alert condition. |

---

### 10.7 Category F — Testing Rules

| Rule | ID | Statement |
|---|---|---|
| Every public method has a test | F-01 | Every public method (not prefixed with `_`) in every module in `src/` has at least one unit test. |
| Tests do not touch production databases | F-02 | Unit tests use in-memory SQLite or temporary files. No test opens `data/trading_brain.db` or `data/telemetry.db`. |
| Tests do not call real APIs | F-03 | Unit tests mock all external calls (`yf.download`, Dhan API, Telegram API). No real network call in any unit or integration test. |
| Tests are deterministic | F-04 | Tests produce the same result on every run regardless of time, market state, or external conditions. All time and randomness sources are injected or mocked. |
| Coverage does not decrease | F-05 | No PR may merge if it reduces the overall test coverage below the current baseline. Coverage is measured by the CI/CD pipeline. |
| Regression test for every bug | F-06 | Every bug fix includes a regression test that would have caught the bug before the fix. The test is committed in the same PR as the fix. |
| Test naming follows convention | F-07 | Test functions are named `test_<scenario>_<expected_outcome>`. Example: `test_submit_order_when_kill_switch_active_raises_error`. |
| Security tests mandatory | F-08 | Every module that accepts external input has at least one security test verifying it rejects malformed, oversized, and injection-style inputs. |

---

### 10.8 Category G — Security Rules

| Rule | ID | Statement |
|---|---|---|
| No secrets in source | G-01 | No credential, token, key, or password appears in any committed file. All secrets are loaded from environment variables at runtime. |
| No secrets in logs | G-02 | Log messages never contain credential values. Before logging a data structure, mask any field named `token`, `key`, `password`, `secret`, `credential`. |
| Input validation at boundaries | G-03 | All data entering the system from external sources (Dhan API, Yahoo Finance, Telegram commands) is validated before processing. Invalid input raises `ValidationError`; it is never silently ignored. |
| SQL injection prevention | G-04 | All SQLite queries use parameterised statements. No SQL query is constructed by string concatenation with user-supplied or externally-sourced data. |
| Dependency scanning automated | G-05 | The CI/CD pipeline includes a dependency vulnerability scan (e.g., `pip-audit` or GitHub Dependabot). Any CRITICAL CVE blocks the deployment pipeline. |
| Principle of least privilege | G-06 | The Docker container runs as a non-root user. The database file is readable only by the process user. API tokens have the minimum required permissions. |
| Token validation on every command | G-07 | Every Telegram bot command validates that the sender's `chat_id` matches `TELEGRAM_CHAT_ID`. Commands from unrecognised chat IDs are rejected and logged. |
| Audit all security events | G-08 | All security events (failed authentication, token expiry, rejected commands, kill-switch activations) are written to the audit log. |

---

### 10.9 Category H — Process Rules

| Rule | ID | Statement |
|---|---|---|
| Deploy after every code change | H-01 | Every code modification is followed by a full deploy cycle. No modification exists only locally. |
| Deploy is complete only when healthy | H-02 | A deployment is complete only when `docker compose ps` shows both containers as `Up ... (healthy)`. Partial deployments are not acceptable. |
| No broken main branch | H-03 | The `main` branch is always deployable. No commit to `main` may break the CI/CD pipeline. |
| Modified files documented | H-04 | Every modified file is recorded in the `Files Modified` table in `copilot-instructions.md` with the reason for modification and whether public interfaces changed. |
| No force push to main | H-05 | `git push --force` to `main` is prohibited. History on `main` is immutable once pushed. |
| Hotfix via hotfix branch | H-06 | Production emergencies use a `hotfix/` branch, not direct commits to `main`. The hotfix branch follows the standard PR process with expedited review. |
| Changelog entry per release | H-07 | Every release (PATCH, MINOR, MAJOR) has a dated entry in `CHANGELOG.md` before the release tag is applied. |
| Architecture documents updated first | H-08 | When an architectural decision is made, the relevant architecture document is updated before implementation begins. Documentation is never retroactive for architectural decisions. |
| Incident reports mandatory | H-09 | Every production incident has an incident report completed within 24 hours of resolution, following the post-incident checklist in ENGINEERING_STANDARDS.md Supplement B.5. |
| No speculative modifications | H-10 | No module is modified speculatively. Every modification must answer: Does this improve correctness, performance, or architecture? Does it preserve all existing public interfaces? Is it the smallest change that achieves the goal? If any answer is no — the change does not proceed. |

---

### 10.10 Repository Constitution Reference Table

| ID | Category | Rule Summary | Enforcement |
|---|---|---|---|
| A-01 | Structural | One responsibility per folder | PR review |
| A-02 | Structural | One owner per module | PR review |
| A-03 | Structural | No cross-layer imports | CI + PR review |
| A-04 | Structural | No duplicate modules | PR review |
| A-05 | Structural | Mirror test structure | CI + PR review |
| A-06 | Structural | Root-level cleanliness | PR review |
| A-07 | Structural | Layer ordering preserved | ADR process |
| A-08 | Structural | Package structure mandatory | CI lint |
| A-09 | Structural | No test files in source | CI lint |
| A-10 | Structural | Deployment artefacts isolated | PR review |
| B-01 | Boundaries | `common/` never imports project packages | CI + PR review |
| B-02 | Boundaries | `config/` never imports layer packages | CI + PR review |
| B-03 | Boundaries | `security/` never imports layer packages | CI + PR review |
| B-04 | Boundaries | `execution_engine/` never generates decisions | PR review |
| B-05 | Boundaries | No business logic in `common/` | PR review |
| B-06 | Boundaries | No direct data fetching in layers | PR review |
| B-07 | Boundaries | No direct DB access from layers | PR review |
| B-08 | Boundaries | No hardcoded credentials | CI secret scan |
| B-09 | Boundaries | Kill-switch respected universally | PR review + test |
| B-10 | Boundaries | No silent failures | PR review |
| C-01 | Safety | Paper trading default | Config validation |
| C-02 | Safety | Kill-switch fail-safe | Code + PR review |
| C-03 | Safety | No destructive DB operations | PR review + approval |
| C-04 | Safety | Risk approval expiry enforced | Code + test |
| C-05 | Safety | Stop-loss mandatory | Code + test |
| C-06 | Safety | Max open positions enforced | Code + test |
| C-07 | Safety | Daily loss limit enforced | Code + test |
| C-08 | Safety | VIX kill-switch enforced | Code + test |
| C-09 | Safety | No orders outside market hours | Code + test |
| C-10 | Safety | Protected module immutability | Governance + PR review |
| D-01 | State | Singletons via getters only | PR review |
| D-02 | State | Shared state requires lock | PR review |
| D-03 | State | No global mutable state | PR review |
| D-04 | State | DB writes serialised | Architecture |
| D-05 | State | DTO immutability at boundaries | Code + PR review |
| D-06 | State | No caching beyond TTL | Code + PR review |
| D-07 | State | Thread names declared | PR review |
| D-08 | State | No thread communication via global | PR review |
| E-01 | Observability | Cycle correlation ID | Code |
| E-02 | Observability | Layer timing recorded | Code + test |
| E-03 | Observability | No silent success for key events | PR review |
| E-04 | Observability | Error logs include context | PR review |
| E-05 | Observability | Audit trail append-only | Code + test |
| E-06 | Observability | EOD report mandatory | Scheduler + monitoring |
| E-07 | Observability | Health check active | Docker config |
| E-08 | Observability | Heartbeat logged | Code |
| F-01 | Testing | Every public method tested | CI coverage |
| F-02 | Testing | No production DB in tests | PR review |
| F-03 | Testing | No real API calls in tests | PR review |
| F-04 | Testing | Tests are deterministic | PR review + CI |
| F-05 | Testing | Coverage does not decrease | CI gate |
| F-06 | Testing | Regression test per bug | PR review |
| F-07 | Testing | Test naming convention | PR review |
| F-08 | Testing | Security tests mandatory | PR review |
| G-01 | Security | No secrets in source | CI secret scan |
| G-02 | Security | No secrets in logs | PR review + test |
| G-03 | Security | Input validation at boundaries | Code + test |
| G-04 | Security | SQL injection prevention | PR review + test |
| G-05 | Security | Dependency scanning automated | CI pipeline |
| G-06 | Security | Principle of least privilege | Docker config |
| G-07 | Security | Token validation per command | Code + test |
| G-08 | Security | Audit all security events | Code |
| H-01 | Process | Deploy after every change | Mandatory process |
| H-02 | Process | Deploy complete = healthy | Mandatory process |
| H-03 | Process | No broken main | CI gate |
| H-04 | Process | Modified files documented | PR checklist |
| H-05 | Process | No force push to main | Git config |
| H-06 | Process | Hotfix via hotfix branch | Git process |
| H-07 | Process | Changelog per release | Release process |
| H-08 | Process | Architecture documents updated first | Process |
| H-09 | Process | Incident reports mandatory | Process |
| H-10 | Process | No speculative modifications | Engineering discipline |

**Total mandatory rules: 60**

---

## DOCUMENT FOOTER

### Summary Metrics

| Metric | Value |
|---|---|
| Document title | REPOSITORY ARCHITECTURE |
| Document version | 1.0.0 |
| Date | 2026-07-02 |
| Parts | 10 (I–X) |
| Mandatory rules | 60 (A-01 through H-10) |
| Rule categories | 8 (Structural, Boundaries, Safety, State, Observability, Testing, Security, Process) |
| Packages declared | 25 (17 layers + 8 infrastructure) |
| Extension points | 6 (feeds, brokers, notifications, agents, strategies, validation stages) |
| Folder lifecycle states | 4 (Active, Deprecated, Archived, Planned) |
| Environment types | 3 (Development, Testing, Production) |
| Secret inventory entries | 6 |
| Feature flags | 10 |
| DTO types | 8 |
| Shared utility modules | 7 |
| Governance levels | 3 (L1 Human Principal, L2 Engineering, L3 Automated) |
| Protected modules | 5 |

---

### Master Compliance Checklist

Use this checklist to verify that a proposed code or structural change complies with this document before submitting a PR.

**Structural (Category A)**
- [ ] New module placed in the correct package for its responsibility
- [ ] One owner assigned to the new module
- [ ] Import rules respected (no import from higher layer)
- [ ] No duplicate functionality of an existing module
- [ ] Test mirror created in `tests/unit/`
- [ ] Root-level cleanliness maintained

**Boundaries (Category B)**
- [ ] `common/` imports only stdlib
- [ ] No hardcoded credentials anywhere in the new code
- [ ] Kill-switch checked before any order submission
- [ ] No silent exception swallowing

**Safety (Category C)**
- [ ] Paper trading mode respected
- [ ] Stop-loss present on all hypotheses
- [ ] Risk approval expiry checked before order
- [ ] Protected modules untouched (unless approved)

**State (Category D)**
- [ ] Singletons accessed via getter functions
- [ ] All shared mutable data protected by locks
- [ ] DTOs are frozen at layer boundaries

**Observability (Category E)**
- [ ] `cycle_id` propagated through new code paths
- [ ] Significant events logged at INFO + sent to Telegram
- [ ] Error logs include full context

**Testing (Category F)**
- [ ] All new public methods have unit tests
- [ ] No real API calls in tests
- [ ] Regression test added for any bug fix
- [ ] Coverage baseline maintained

**Security (Category G)**
- [ ] No secrets in source or logs
- [ ] Input validation at every external boundary
- [ ] All SQL uses parameterised queries

**Process (Category H)**
- [ ] `copilot-instructions.md` `Files Modified` updated
- [ ] Deploy planned after merge
- [ ] Changelog entry prepared

---

### Version History

| Version | Date | Author | Change Summary |
|---|---|---|---|
| 1.0.0 | 2026-07-02 | Human Principal | Initial authoritative release |

---

### Governing Documents

| Document | Role |
|---|---|
| `INVESTMENT_INTELLIGENCE_OPERATING_SYSTEM.md` | Supreme constitutional authority |
| `AI_TRADING_BRAIN_ENGINEERING_BLUEPRINT.md` | Engineering design bridge |
| `ENGINEERING_STANDARDS.md` | Mandatory engineering standards |
| `REPOSITORY_ARCHITECTURE.md` | This document — repository design authority |
| `ARCHITECTURE.md` | Executive summary for new readers |
| `.github/copilot-instructions.md` | AI assistant operational instructions |

---

### Closing Statement

This document is the authoritative design of the AI Trading Brain repository. It governs every artefact: every folder, every module, every file, every configuration value, every test, every deployment script, and every generated resource.

No artefact exists outside this design. No change is made without reference to this design. No exception is granted without an ADR and Human Principal approval.

The repository is not merely a directory of files. It is the physical embodiment of the IIOS architecture. Its integrity is inseparable from the integrity of the system it contains.

---

## SUPPLEMENT A — COMPLETE PACKAGE INVENTORY

### A.1 All Declared Packages

This inventory lists every package declared in this repository architecture, with its classification, layer number (if applicable), and current implementation status.

| Package | Type | Layer | Status | Path |
|---|---|---|---|---|
| `common` | Foundation | — | Active | `src/common/` |
| `config` | Foundation | — | Active (at root) | `config.py` → migrate to `src/config/` |
| `global_intelligence` | Operational Layer | 1 | Active | `src/global_intelligence/` |
| `market_intelligence` | Operational Layer | 2 | Active | `src/market_intelligence/` |
| `meta_learning` | Operational Layer | 3 | Active | `src/meta_learning/` |
| `opportunity_engine` | Operational Layer | 4 | Active | `src/opportunity_engine/` |
| `strategy_lab` | Operational Layer | 5 | Active | `src/strategy_lab/` |
| `capital_risk_engine` | Operational Layer | 6 | Active | `src/capital_risk_engine/` |
| `risk_control` | Operational Layer | 7 | Active | `src/risk_control/` |
| `market_simulation` | Operational Layer | 8 | Active | `src/market_simulation/` |
| `risk_guardian` | Operational Layer | 9 | Active (PROTECTED) | `src/risk_guardian/` |
| `debate_engine` | Operational Layer | 10 | Active | `src/debate_engine/` |
| `execution_engine` | Operational Layer | 11 | Active | `src/execution_engine/` |
| `trade_monitoring` | Operational Layer | 12 | Active | `src/trade_monitoring/` |
| `learning_system` | Operational Layer | 13 | Active | `src/learning_system/` |
| `performance_analytics` | Operational Layer | 14 | Active | `src/performance_analytics/` |
| `research_lab` | Operational Layer | 15 | Active | `src/research_lab/` |
| `validation_engine` | Operational Layer | 16 | Active (PROTECTED) | `src/validation_engine/` |
| `control_tower` | Operational Layer | 17 | Active | `src/control_tower/` |
| `data_feeds` | Infrastructure | — | Active | `src/data_feeds/` |
| `integrations` | Infrastructure | — | Active (partial) | `src/integrations/` |
| `notifications` | Infrastructure | — | Active | `src/notifications/` |
| `security` | Infrastructure | — | Active | `src/security/` |
| `monitoring` | Infrastructure | — | Active | `src/monitoring/` |
| `audit` | Infrastructure | — | Active | `src/audit/` |
| `scheduler` | Infrastructure | — | Active | `src/scheduler/` |
| `knowledge` | Domain | — | Planned | `src/knowledge/` |

---

### A.2 Package Internal Structure Standard

Every package in `src/` follows this mandatory internal structure:

```
<package_name>/
├── __init__.py           # Exports: primary class + any secondary public classes
├── <primary_class>.py    # Primary class (named after the package concept)
├── <secondary>.py        # Additional modules (if needed)
├── README.md             # Package documentation (see A.3)
└── [sub_packages/]       # Sub-packages only when clearly needed
```

**`__init__.py` standard:**

The `__init__.py` declares the public API of the package. Only what is listed in `__all__` is considered a public interface.

```
# Example: src/global_intelligence/__init__.py
from global_intelligence.global_data_ai import GlobalDataAI

__all__ = ["GlobalDataAI"]
```

---

### A.3 Package README Standard

Every package has a `README.md` with the following sections:

| Section | Content |
|---|---|
| **Package Name** | Name and one-sentence purpose |
| **Layer** | Layer number (if applicable) and position in IIOS hierarchy |
| **Owner** | Declared owner |
| **Responsibility** | What this package does (2–4 sentences) |
| **Primary Class** | Class name, key public methods |
| **Dependencies** | Packages this package imports from |
| **Consumers** | Packages that import from this package |
| **Allowed Imports** | Explicit list |
| **Forbidden Imports** | Explicit list |
| **Key Thresholds** | Any critical numeric thresholds (latency, win rate, etc.) |
| **Protected** | Whether this package is protected and why |
| **Changelog** | Recent changes (last 5 modifications) |

---

### A.4 `__init__.py` Policy

| Rule | Detail |
|---|---|
| Explicit exports | Always define `__all__` explicitly |
| No side effects | `__init__.py` does not execute business logic, network calls, or file I/O on import |
| No star imports | Never `from module import *` in any `__init__.py` |
| Re-export pattern | Import the class from its module, then export it |
| Singleton registration | Singleton getter functions are registered in `control_tower/__init__.py`, not scattered |

---

## SUPPLEMENT B — DATABASE SCHEMA DESIGN

### B.1 `trading_brain.db` — Primary Database

This database stores all trading decisions, orders, positions, and outcomes.

**Table: `decisions`**

| Column | Type | Constraints | Description |
|---|---|---|---|
| `decision_id` | TEXT | PRIMARY KEY | UUID4 |
| `cycle_id` | TEXT | NOT NULL | UUID4 of the cognitive cycle |
| `symbol` | TEXT | NOT NULL | NSE instrument symbol |
| `direction` | TEXT | NOT NULL, CHECK IN ('LONG','SHORT') | Trade direction |
| `strategy_id` | TEXT | NOT NULL | Originating strategy identifier |
| `conviction_score` | REAL | NOT NULL, CHECK ≥ 0.0 AND ≤ 10.0 | Aggregate conviction from debate |
| `entry_price` | REAL | NOT NULL, CHECK > 0.0 | Proposed entry |
| `stop_loss` | REAL | NOT NULL, CHECK > 0.0 | Stop-loss level |
| `target` | REAL | NOT NULL, CHECK > 0.0 | Profit target level |
| `reward_risk_ratio` | REAL | NOT NULL, CHECK > 0.0 | Calculated R:R |
| `agent_votes` | TEXT | NOT NULL | JSON-serialised agent vote record |
| `approved_at` | TEXT | NOT NULL | ISO 8601 UTC timestamp |
| `regime_type` | TEXT | NOT NULL | Regime at time of decision |
| `notes` | TEXT | | Optional notes |

**Table: `orders`**

| Column | Type | Constraints | Description |
|---|---|---|---|
| `order_id` | TEXT | PRIMARY KEY | UUID4 |
| `decision_id` | TEXT | NOT NULL, FK → decisions | Parent decision |
| `symbol` | TEXT | NOT NULL | NSE instrument symbol |
| `direction` | TEXT | NOT NULL, CHECK IN ('LONG','SHORT') | Order direction |
| `quantity` | INTEGER | NOT NULL, CHECK > 0 | Approved quantity |
| `entry_price` | REAL | NOT NULL | Order entry price |
| `stop_loss` | REAL | NOT NULL | Stop-loss level |
| `target` | REAL | NOT NULL | Profit target |
| `status` | TEXT | NOT NULL, CHECK IN ('PENDING','OPEN','CLOSED','CANCELLED') | Order state |
| `submitted_at` | TEXT | NOT NULL | ISO 8601 UTC timestamp |
| `closed_at` | TEXT | | ISO 8601 UTC (null while open) |
| `close_price` | REAL | | Actual close price |
| `realised_pnl` | REAL | | Realised P&L in INR |
| `is_paper` | INTEGER | NOT NULL, CHECK IN (0,1) | 1 = paper; 0 = live |

**Table: `strategy_stats`**

| Column | Type | Constraints | Description |
|---|---|---|---|
| `strategy_id` | TEXT | PRIMARY KEY | Strategy identifier |
| `total_trades` | INTEGER | NOT NULL, DEFAULT 0 | Cumulative trade count |
| `winning_trades` | INTEGER | NOT NULL, DEFAULT 0 | Cumulative winning trades |
| `win_rate` | REAL | | Calculated: winning/total |
| `avg_rr_achieved` | REAL | | Average realised R:R |
| `total_pnl` | REAL | | Cumulative P&L |
| `max_drawdown` | REAL | | Maximum drawdown observed |
| `sharpe_ratio` | REAL | | Rolling Sharpe ratio |
| `is_active` | INTEGER | NOT NULL, DEFAULT 1, CHECK IN (0,1) | 1 = enabled |
| `auto_disabled_at` | TEXT | | Timestamp of auto-disable (null if never) |
| `auto_disable_reason` | TEXT | | Reason for auto-disable |
| `last_updated_at` | TEXT | NOT NULL | ISO 8601 UTC timestamp |

**Table: `cycle_log`**

| Column | Type | Constraints | Description |
|---|---|---|---|
| `cycle_id` | TEXT | PRIMARY KEY | UUID4 |
| `started_at` | TEXT | NOT NULL | ISO 8601 UTC |
| `completed_at` | TEXT | | ISO 8601 UTC |
| `duration_ms` | INTEGER | | Total cycle duration |
| `regime_type` | TEXT | | Regime detected in this cycle |
| `opportunities_found` | INTEGER | | Count of opportunities scanned |
| `hypotheses_generated` | INTEGER | | Count of hypotheses generated |
| `hypotheses_approved` | INTEGER | | Count approved through debate |
| `orders_submitted` | INTEGER | | Count of orders submitted |
| `kill_switch_active` | INTEGER | NOT NULL, CHECK IN (0,1) | Kill-switch state at cycle end |
| `error` | TEXT | | Error message if cycle failed |

---

### B.2 `telemetry.db` — Telemetry Database

**Table: `layer_timings`**

| Column | Type | Constraints | Description |
|---|---|---|---|
| `timing_id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Row ID |
| `cycle_id` | TEXT | NOT NULL | Parent cycle |
| `layer_name` | TEXT | NOT NULL | Layer identifier |
| `duration_ms` | INTEGER | NOT NULL | Layer execution time |
| `status` | TEXT | NOT NULL, CHECK IN ('OK','WARN','CRIT','ERROR') | Timing status |
| `recorded_at` | TEXT | NOT NULL | ISO 8601 UTC timestamp |

**Table: `feed_health`**

| Column | Type | Constraints | Description |
|---|---|---|---|
| `check_id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Row ID |
| `feed_name` | TEXT | NOT NULL | Feed adapter name |
| `is_available` | INTEGER | NOT NULL, CHECK IN (0,1) | Availability at check time |
| `response_ms` | INTEGER | | Response time |
| `checked_at` | TEXT | NOT NULL | ISO 8601 UTC timestamp |

---

### B.3 Database Index Design

Indexes declared for query performance:

| Index Name | Table | Column(s) | Purpose |
|---|---|---|---|
| `idx_decisions_cycle_id` | decisions | `cycle_id` | Lookup all decisions in a cycle |
| `idx_decisions_symbol` | decisions | `symbol` | Strategy analysis by symbol |
| `idx_decisions_strategy_id` | decisions | `strategy_id` | Strategy performance queries |
| `idx_orders_decision_id` | orders | `decision_id` | Join decisions → orders |
| `idx_orders_status` | orders | `status` | Find open orders |
| `idx_orders_submitted_at` | orders | `submitted_at` | Date-range queries |
| `idx_orders_symbol` | orders | `symbol` | Position queries by symbol |
| `idx_layer_timings_cycle_id` | layer_timings | `cycle_id` | Cycle performance profile |
| `idx_layer_timings_layer_name` | layer_timings | `layer_name` | Layer performance history |
| `idx_cycle_log_started_at` | cycle_log | `started_at` | Date-range cycle queries |

---

## SUPPLEMENT C — CI/CD PIPELINE DESIGN

### C.1 Pipeline Overview

The CI/CD pipeline is defined in `.github/workflows/` and runs automatically on:
- Every push to any branch
- Every pull request targeting `main`
- On schedule (daily security scan)

**Pipelines:**

| Pipeline | File | Trigger | Purpose |
|---|---|---|---|
| Continuous Integration | `ci.yml` | Push, PR | Lint + test + coverage |
| Deployment | `deploy.yml` | Push to `main` | Deploy to VPS |
| Security Scan | `security.yml` | Daily + PR | Dependency vulnerability check |

---

### C.2 CI Pipeline Stages (`ci.yml`)

| Stage | Tool | Pass Criteria | Blocks Merge |
|---|---|---|---|
| Install dependencies | `pip install -r requirements.txt -r requirements-dev.txt` | Exit 0 | Yes |
| Lint | `pylint src/` | Score ≥ 8.0/10 | Yes |
| Type check | `mypy src/ --ignore-missing-imports` | No type errors | Yes |
| Unit tests | `pytest tests/unit/ -v --tb=short` | All pass | Yes |
| Integration tests | `pytest tests/integration/ -v --tb=short` | All pass | Yes |
| Security tests | `pytest tests/security/ -v --tb=short` | All pass | Yes |
| Coverage report | `pytest --cov=src --cov-report=xml` | Coverage ≥ baseline | Yes |
| Secret scan | `trufflehog filesystem --directory=.` | No secrets found | Yes |

---

### C.3 Deployment Pipeline Stages (`deploy.yml`)

This pipeline runs only on commits to `main` after CI passes.

| Stage | Action | Failure Action |
|---|---|---|
| 1. SSH to VPS | `ssh -i ~/.ssh/trading_vps root@178.18.252.24` | Alert + stop |
| 2. Pull latest | `git pull origin main` | Alert + rollback |
| 3. Build | `docker compose build --no-cache` | Alert + rollback |
| 4. Stop old | `docker compose down` | Alert + rollback |
| 5. Start new | `docker compose up -d` | Alert + rollback |
| 6. Health check | `sleep 8 && docker compose ps` | Alert + rollback |
| 7. Verify healthy | Both containers `Up ... (healthy)` | Alert + rollback |
| 8. Notify | Telegram message: deploy complete | — |

---

### C.4 Branch Protection Rules for `main`

| Rule | Setting |
|---|---|
| Require PR before merge | Yes |
| Required status checks | CI pipeline (all stages) |
| Dismiss stale PR approvals | Yes |
| No force push | Yes |
| No deletion | Yes |
| Require linear history | Recommended (squash merge) |

---

## SUPPLEMENT D — DEPLOYMENT ARCHITECTURE

### D.1 Container Architecture

The AI Trading Brain runs as two Docker containers managed by Docker Compose:

| Container | Image | Purpose | Health Check |
|---|---|---|---|
| `ai-trading-brain` | `ai-trading-brain` | Main trading process | `python -c "import health_check; health_check.ok()"` |
| `trading-dashboard` | `trading-dashboard` | Streamlit dashboard | HTTP GET `/health` → 200 |

**Docker Compose volume mounts:**

| Host Path | Container Path | Purpose |
|---|---|---|
| `./data` | `/app/data` | Persistent data (databases, CSV journals) |
| `./logs` | `/app/logs` | Persistent log files |
| `./reports` | `/app/reports` | Generated reports |

**Docker Compose network:** Both containers share a private `trading-net` bridge network. The dashboard accesses the SQLite databases directly via the shared volume. No inter-container API calls are required.

---

### D.2 Environment Variable Injection

Environment variables are injected into the Docker containers via the Docker Compose `env_file` directive:

```
services:
  ai-trading-brain:
    env_file:
      - .env.production
    environment:
      - PAPER_TRADING=${PAPER_TRADING:-true}
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
```

**Required environment variables (production):**

| Variable | Source | Default | Purpose |
|---|---|---|---|
| `DHAN_ACCESS_TOKEN` | Docker secret / `.env` | None | Dhan API authentication |
| `DHAN_CLIENT_ID` | Docker secret / `.env` | None | Dhan account identifier |
| `TELEGRAM_BOT_TOKEN` | Docker secret / `.env` | None | Telegram bot authentication |
| `TELEGRAM_CHAT_ID` | Docker secret / `.env` | None | Authorised Telegram chat |
| `PAPER_TRADING` | Docker Compose override | `true` | Paper vs live mode |
| `LOG_LEVEL` | Docker Compose override | `INFO` | Python logging level |
| `DB_PATH` | Docker Compose | `/app/data/trading_brain.db` | Database path |
| `TELEMETRY_DB_PATH` | Docker Compose | `/app/data/telemetry.db` | Telemetry database |
| `PAPER_TRADES_CSV` | Docker Compose | `/app/data/paper_trades.csv` | Paper trade journal |
| `AUDIT_LOG_PATH` | Docker Compose | `/app/data/audit.log` | Audit log path |

---

### D.3 VPS Server Architecture

| Attribute | Value |
|---|---|
| VPS host | `178.18.252.24` |
| OS | Ubuntu 22.04 LTS |
| SSH user | `root` |
| SSH key | `~/.ssh/trading_vps` |
| Working directory | `/root/ai-trading-brain/` |
| Docker version | Latest stable |
| Docker Compose version | V2 (plugin-based) |
| Git remote | `origin` → GitHub repository |

**VPS directory layout:**

```
/root/ai-trading-brain/
├── (repository contents, same as local)
├── data/                       # Persistent volume (survives restarts)
│   ├── trading_brain.db
│   ├── paper_trades.csv
│   └── ...
└── logs/                       # Persistent volume
```

---

### D.4 Startup Sequence

When the `ai-trading-brain` container starts, the following sequence executes:

| Step | Code Path | Failure Mode |
|---|---|---|
| 1 | Parse CLI arguments (`--paper`, `--telegram`, `--status`) | Print usage, exit |
| 2 | Load environment variables | — |
| 3 | Call `validate_config()` | Log error, exit(1) |
| 4 | Validate all required secrets are present | Log error, exit(1) |
| 5 | Initialise logging (file rotation, console handler) | — |
| 6 | Log startup banner with version and mode | — |
| 7 | Initialise SQLite databases (apply pending migrations) | Log error, exit(1) |
| 8 | Initialise `DataFeedManager` (test feeds) | Log warning, continue with available feeds |
| 9 | Initialise singletons (`PerformanceTracker`, `RegimeStrategyMap`, etc.) | Log error, exit(1) |
| 10 | Start `TelegramBot` if `--telegram` | Log warning, continue without Telegram if fails |
| 11 | Start `RiskGuardianAgent` monitoring thread | Log error, exit(1) — Guardian is mandatory |
| 12 | Start `MarketMonitor` continuous scan thread | Log error, exit(1) — Monitor is mandatory |
| 13 | Start `APScheduler` with all 10 scheduled slots | Log error, exit(1) |
| 14 | Log "System READY" banner | — |
| 15 | Run first cognitive cycle immediately | — |
| 16 | Enter scheduler event loop | — |

---

### D.5 Shutdown Sequence

When the process receives `SIGTERM` (from Docker Compose `down`):

| Step | Action |
|---|---|
| 1 | Set `shutdown_requested` flag |
| 2 | APScheduler pauses — no new jobs started |
| 3 | Wait for current cycle to complete (max 60 seconds) |
| 4 | Stop `MarketMonitor` thread (join with 5s timeout) |
| 5 | Stop `RiskGuardianAgent` thread (join with 5s timeout) |
| 6 | Stop `TelegramBot` if running |
| 7 | Write EOD summary to telemetry database |
| 8 | Close all SQLite connections |
| 9 | Log shutdown banner with session summary |
| 10 | Exit(0) |

This ensures that no cognitive cycle is interrupted mid-execution and all database connections are cleanly closed before the container stops.

---

### D.6 Health Check Design

The Docker health check verifies that the main process is alive and the system is in a healthy state.

**Health check criteria:**

| Criterion | Check Method | Healthy If |
|---|---|---|
| Process alive | Docker process check | Container process running |
| Last cycle age | Check `cycle_log.completed_at` in telemetry.db | < 15 minutes (during market hours) |
| Kill-switch state | Check `kill_switch_active` in last cycle_log row | Reported (not necessarily inactive) |
| Database accessible | Open `trading_brain.db` | No error |
| Feed available | Check `feed_health` table | At least one feed available in last 5 minutes |

**Health check response:** Returns `healthy` if all checks pass; `unhealthy` if any fail. Docker Compose marks the container as `(healthy)` or `(unhealthy)` accordingly.

---

## SUPPLEMENT E — GITIGNORE SPECIFICATION

### E.1 Version Control Exclusion Rules

The following patterns are declared in `.gitignore` at the repository root:

**Runtime data (never committed):**
```
data/trading_brain.db
data/telemetry.db
data/paper_trades.csv
data/audit.log
data/datasets/*.parquet
data/backups/
```

**Log files:**
```
logs/
*.log
!logs/.gitkeep
```

**Secrets:**
```
.env
.env.production
.env.development
.env.testing
!.env.example
!.env.*.template
```

**Python runtime artefacts:**
```
__pycache__/
*.py[cod]
*.pyo
.pytest_cache/
.coverage
coverage.xml
htmlcov/
.mypy_cache/
```

**Build and distribution:**
```
dist/
build/
*.egg-info/
```

**IDE and OS artefacts:**
```
.vscode/settings.json
.idea/
*.DS_Store
Thumbs.db
```

**Reports (generated output):**
```
reports/eod/
reports/performance/
reports/backtesting/
!reports/README.md
```

**Model artefacts (large files via Git LFS if applicable):**
```
models/*.pkl
models/*.h5
models/*.onnx
!models/*_metadata.json
!models/README.md
```

---
