# AI_TRADING_BRAIN_ENGINEERING_BLUEPRINT.md

**Version:** 1.0
**Classification:** Engineering Architecture Blueprint
**Status:** Active — Primary Engineering Reference
**Parent Document:** INVESTMENT_INTELLIGENCE_OPERATING_SYSTEM.md (IIOS)
**Purpose:** Converts constitutional architecture into an engineering blueprint
**Created:** 2026-07-02

| Attribute | Value |
|---|---|
| Document Name | AI Trading Brain Engineering Blueprint |
| Abbreviation | ATBEB |
| Document Class | Engineering Architecture Blueprint |
| Version | 1.0.0 |
| Status | Active — Engineering Authority |
| Parent Constitutional Doc | INVESTMENT_INTELLIGENCE_OPERATING_SYSTEM.md |
| Governed By | IIOS Constitution (65 articles, 60 invariants) |
| Target Size | 200,000–300,000 bytes |
| Engineering Parts | 10 (Parts I–X) |
| Engineering Modules | 62+ defined |
| Layers Mapped | 17 IIOS operational layers |
| Implementation Phases | 4 |
| Amendment Authority | Human Principal + Architecture Council |

---

## Parent Documents

| # | Document | Phase | Engineering Role |
|---|---|---|---|
| 1 | MASTER_KNOWLEDGE_ARCHITECTURE.md | Phase 1 | Knowledge graph storage and retrieval engineering |
| 2 | INFORMATION_ONTOLOGY.md | Phase 2 | Information validation pipeline engineering |
| 3 | ENTITY_ONTOLOGY.md | Phase 3 | Entity state management engineering |
| 4 | RELATIONSHIP_ONTOLOGY.md | Phase 4 | Relationship graph engineering |
| 5 | EVENT_ONTOLOGY.md | Phase 5 | Event detection and routing engineering |
| 6 | REASONING_ARCHITECTURE.md | Phase 6 | Reasoning engine engineering |
| 7 | DECISION_ARCHITECTURE.md | Phase 7 | Decision pipeline engineering |
| 8 | LEARNING_ARCHITECTURE.md | Phase 8 | Learning system engineering |
| 9 | MEMORY_ARCHITECTURE.md | Phase 9 | Memory layer engineering |
| 10 | INVESTMENT_INTELLIGENCE_OPERATING_SYSTEM.md | Phase 10 | Constitutional governance, supreme authority |

---

## Engineering Declaration

This document is the bridge between constitutional architecture and engineering implementation. It does not contain source code. It does not define APIs. It does not specify database schemas. It is not a software design document. It is the engineering architecture of the AI Trading Brain — the definitive answer to the engineering question: how will the software that implements the IIOS constitution be structured, decomposed, organised, and built?

All engineering decisions recorded here are made within the bounds of the IIOS constitution. Engineering decisions that would violate a constitutional article or invariant are not within scope. The engineering blueprint serves the constitution; the constitution does not serve the engineering blueprint.

---

## Table of Contents

| Part | Title | Engineering Focus |
|---|---|---|
| I | Engineering Philosophy | Principles, quality attributes, constraints |
| II | Complete Software Layer Architecture | Layer-to-component mapping, isolation |
| III | Module Decomposition | Module hierarchy, dependencies, responsibilities |
| IV | Repository Structure | Directory organisation, package boundaries |
| V | Service Architecture | Service topology, process isolation |
| VI | Inter-Service Communication | Messaging, protocols, sequencing |
| VII | Data Storage Strategy | Storage tiers, persistence, governance |
| VIII | Implementation Roadmap | Phases, milestones, dependencies |
| IX | Engineering Constitution | Engineering invariants, quality standards |
| X | Implementation Readiness Checklist | Phase gates, readiness criteria |

---

## PART I — ENGINEERING PHILOSOPHY

### 1.1 The Seven Engineering First Principles

**Principle 1 — Correctness Before Performance**
A component that produces wrong results quickly is less valuable than a component that produces correct results slowly. Performance optimisation is secondary — applied only after correctness is verified. No performance optimisation may compromise correctness of any output.

**Principle 2 — Observability Is Architecture**
Observability is a first-class engineering requirement that shapes the architecture. Every component is designed to expose its internal state, inputs and outputs, timing, and error conditions. A component that cannot be observed cannot be governed, audited, or improved.

**Principle 3 — Failure Is Expected**
The engineering architecture assumes any component can fail at any time. No decision assumes a component will always be available, return a valid result, or complete within a time bound. Fail-safe behaviour is engineered first, performance second.

**Principle 4 — Explicit Over Implicit**
Engineering decisions that are explicit — clearly documented, clearly named, clearly bounded — are always preferred over implicit decisions. Implicit behaviour produces systems that are difficult to audit, debug, and evolve.

**Principle 5 — Independence Enables Evolution**
Modules that are tightly coupled cannot evolve independently. Every module boundary is a decision about evolution independence: what can change in one module without affecting another. Module independence is the engineering requirement that enables the additive evolution mandated by the IIOS constitution.

**Principle 6 — Data Governs Behaviour**
The AI Trading Brain is a data-driven system. Its behaviour is determined by the data it holds and the rules it applies to that data. Engineering decisions that make data flows harder to trace, inspect, or validate work against the constitutional requirement for explainability and audit.

**Principle 7 — Reversibility Is Preferable**
Given two engineering approaches that achieve the same result, the reversible approach is preferred. Reversibility allows engineering to be corrected when assumptions prove wrong — and in algorithmic trading, assumptions regularly prove wrong.

---

### 1.2 Quality Attributes (Priority Ordered)

| Priority | Attribute | Engineering Definition | IIOS Origin |
|---|---|---|---|
| 1 | **Correctness** | All outputs are numerically and logically correct; no silent calculation errors | Articles I-001–I-010 (Truth and Evidence) |
| 2 | **Safety** | Kill-switch, position limits, and risk gates are enforced with no possible bypass | Articles I-023–I-038 (Risk and Capital) |
| 3 | **Auditability** | Every output, decision, and state transition is recorded and retrievable | Articles I-056–I-061 (Transparency) |
| 4 | **Reliability** | System continues operating correctly through component failures | INV-53–INV-60 (Operational Continuity) |
| 5 | **Observability** | Internal state of every component is inspectable at any time | Article I-056 (Explainability Is Mandatory) |
| 6 | **Consistency** | System behaves identically for identical inputs regardless of execution order | INV-09 (No Stage Skipping) |
| 7 | **Integrity** | All historical records are immutable and hash-verified | INV-17–INV-22 (History and Immutability) |
| 8 | **Latency** | Cognitive cycle completes within 200ms; standard layers within 5,000ms | System Monitor thresholds |
| 9 | **Throughput** | System evaluates >= 120 decision opportunities per hour during market hours | S10.3 Operational Metrics |
| 10 | **Evolvability** | Architecture supports additive changes without breaking existing interfaces | Articles I-062–I-065 (Evolution) |

---

### 1.3 Technology Independence

The engineering blueprint is technology-independent. The architecture specifies patterns, not technologies:

| Layer | Pattern (Technology-Independent) | Current Technology Choice | Rationale |
|---|---|---|---|
| Language runtime | Dynamic typed, GIL-aware | Python 3.14 | Ecosystem; yfinance; Telegram libraries |
| In-process communication | Function call with typed return | Python function calls | Sub-millisecond; no serialisation overhead |
| Scheduled execution | Cron-compatible job scheduler | APScheduler | Python-native; complex schedule support |
| Relational storage | Embedded relational database | SQLite | Zero configuration; embedded; sufficient scale |
| Time-series cache | In-memory TTL cache | Python dict + threading.Lock | Lowest latency; no external dependency |
| Message alerts | Authenticated push notification | Telegram Bot API | Human principal preference; real-time |
| Data feed primary | Broker REST API | Dhan API | Preferred broker; authenticated |
| Data feed fallback | Public financial data API | yfinance (Yahoo Finance) | Dhan 451 fallback; no auth required |
| Containerisation | OCI-compatible container runtime | Docker + Docker Compose | VPS deployment standard |
| Dashboard | Reactive web framework | Streamlit | Python-native; no frontend build step |

---

### 1.4 Architectural Style Matrix

| Style | Scale | Application | Constitutional Basis |
|---|---|---|---|
| **Layered** | System scale | 17 IIOS operational layers enforce strict top-to-bottom data flow; no layer bypass | INV-09 (No Stage Skipping) |
| **Agent-based** | Component scale | ~62 agents within layers operate with defined constitutional roles | IIOS Supplement VIII |
| **Event-driven** | Communication scale | Cross-layer communication uses events and messages for audit completeness | Article I-058 (Audit Trail Is Complete) |
| **Pipeline** | Process scale | Cognitive loop Stages 01–20 form a strict sequential pipeline | IIOS Part III |
| **Reactive** | Monitoring scale | Trade monitoring and kill-switch respond to state changes without polling | INV-55 (Monitoring Continuity) |

---

### 1.5 Engineering Constraints

| Constraint | Value | Rationale | Architectural Impact |
|---|---|---|---|
| Market hours | 09:15–15:30 IST, Mon–Fri | NSE/BSE trading calendar | All time-critical paths must complete within session |
| Cognitive cycle latency | < 200ms end-to-end | System Monitor critical threshold | Dictates maximum component complexity per cycle |
| Kill-switch response | < 100ms from trigger to activation | INV-24; constitutional safety | Kill-switch path must be synchronous, highest priority |
| Memory encoding | < 5s from learning trigger | IIOS Spec | Learning pipeline must not block cognitive loop |
| Position monitoring gap | < 60s | INV-55 | Monitoring thread is never blocked by any other process |
| Data feed fallback | < 1s switch time | INV-56 | Feed manager maintains warm standby connection |
| History record mutability | Append-only, never modify | INV-17 | All writes to historical stores are append-only |
| Audit trail completeness | 100% — no cycle without record | INV-57 | Every stage transition generates an audit record |
| Python environment | 3.14 / .venv/ | Current deployment | All modules compatible with Python 3.14 |
| Deployment topology | 2-container Docker Compose | VPS scale | Service count constrained by container model |
| VPS resources | Shared VPS: root@178.18.252.24 | Current infrastructure | Memory/CPU budget constrains background threads |

---

### 1.6 Non-Functional Requirements Matrix

| NFR | Requirement | Measurement | Verification |
|---|---|---|---|
| Cognitive cycle P95 | <= 200ms | Wall-clock at orchestrator | `system_monitor.time_layer()` |
| GlobalIntelligence P95 | <= 12,000ms | Layer-specific override | WARN=5,000 CRIT=12,000 override |
| Standard layer P95 | <= 5,000ms | Per-layer monitoring | Default WARN=2,000 CRIT=5,000 |
| Kill-switch activation | <= 100ms | Guardian self-measurement | Simulation test daily |
| No SPOF | Zero single-component failures halt system | Failure mode analysis | Resilience audit (INV-53) |
| Fail-safe default | On any component failure, system falls to safe state | Component health check | Fail-safe activation test |
| All decisions logged | 100% decision provenance | Log completeness audit | Audit trail completeness audit |
| Hash integrity | All records hash-verified at write | Hash check on read | Knowledge Integrity Verifier daily |
| Symbol coverage | >= 200 equity symbols in scanner | Scanner throughput test | EquityScanner load test |
| Module isolation | All modules independently testable | Test isolation check | Test suite per module |

---

### 1.7 Engineering Anti-Patterns (Constitutionally Prohibited)

| Anti-Pattern | Why Prohibited | Constitutional Ref | Enforcement |
|---|---|---|---|
| Silent failure | Failures must be logged and escalated immediately | INV-59, Article I-061 | Mandatory exception logging |
| In-place record mutation | Historical records are immutable | INV-17, Article I-021 | Append-only storage |
| Implicit global state | All state must be explicitly owned and observable | Article I-056 | Module ownership registry |
| Hard-coded conviction bypass | Conviction threshold is constitutional | INV-11, Article I-012 | No bypass permitted |
| Automated kill-switch deactivation | Human Principal only | Article I-050 | Override requires authenticated human action |
| Circular module dependency | Creates untestable coupling | Principle 5 | Dependency graph audit |
| Blocking monitoring thread | Monitoring gap > 60s is constitutional violation | INV-55 | Thread isolation |
| Forward-looking test data | Testing with data unavailable at decision time | INV-22 | Data timestamp validation in tests |
| Post-hoc decision rationalisation | Decision record must precede execution | INV-14 | Execution gate checks record presence |
| Single-source evidence | Minimum independent sources required | INV-07 | Evidence diversity check |

---

### 1.8 Engineering Decision Register

| Decision ID | Decision | Alternatives | Rationale | Constitutional Basis |
|---|---|---|---|---|
| ED-001 | Monorepo single Python package | Multi-repo per layer | Simpler deployment; shared utilities; 17 layers not independent services | Additive evolution |
| ED-002 | SQLite for relational storage | PostgreSQL, DuckDB | Zero configuration; embedded; sufficient for current data volume | Simplicity |
| ED-003 | CSV for paper trade journal | SQLite second table | Human-readable; directly inspectable; sufficient for paper trading | Observability |
| ED-004 | In-process agent communication | Message queues | Same cognitive cycle; inter-process latency violates 200ms budget | Latency |
| ED-005 | Docker Compose 2-container | Single container; Kubernetes | Separation of trading engine and dashboard; sufficient for VPS | Independence |
| ED-006 | yfinance fallback for Dhan 451 | No fallback; alternative broker | Dhan data API returns 451; yfinance provides equivalent data | INV-56 redundancy |
| ED-007 | APScheduler for cycle scheduling | Cron; threading.Timer | Python-native; complex schedules; production-tested | Reliability |
| ED-008 | Telegram Bot API for alerts | Email; Slack; webhook | Real-time; authenticated; human principal preference | Human authority |
| ED-009 | Write-once append for audit log | Mutable log | INV-17 requires immutability; append-only enforces at storage level | INV-17 |
| ED-010 | Background thread for GI pre-warm | Synchronous fetch | 17ms actual vs 5,000ms without pre-warm; constitutional latency | CRIT override |

---

## PART II — COMPLETE SOFTWARE LAYER ARCHITECTURE

### 2.0 Overview

The IIOS defines 17 operational layers. This Part maps each constitutional layer to its software component, defines process boundaries, specifies isolation strategies, and provides complete layer interaction diagrams.

---

### 2.1 IIOS Layer to Software Component Map

| IIOS Layer | Layer Name | Software Component | Module | Process Boundary | Latency Budget |
|---|---|---|---|---|---|
| 1 | GlobalIntelligence | `GlobalDataAI` | `global_intelligence/` | In-process; background pre-warm thread | WARN 5,000ms CRIT 12,000ms |
| 2 | MarketIntelligence | `MarketIntelligenceEngine` + `MarketMonitor` | `market_intelligence/` | In-process; 30s continuous scan thread | WARN 2,000ms CRIT 5,000ms |
| 3 | MetaLearning | `kNNStrategyPredictor` + `RegimeStrategyMap` | `meta_learning/` | In-process | WARN 2,000ms CRIT 5,000ms |
| 4 | OpportunityEngine | `EquityScanner` + `OptionsOpportunityEngine` | `opportunity_engine/` | In-process; scan thread | WARN 2,000ms CRIT 5,000ms |
| 5 | StrategyLab | `MetaStrategyController` + `StrategyGeneratorAI` | `strategy_lab/` | In-process | WARN 2,000ms CRIT 5,000ms |
| 6 | CapitalRiskEngine | `PositionSizerAgent` | `capital_risk_engine/` | In-process | WARN 500ms CRIT 2,000ms |
| 7 | RiskControl | `RiskManagerAI` + `PortfolioAllocation` + `StressTestingAgent` | `risk_control/` | In-process; stress test background | WARN 500ms CRIT 2,000ms |
| 8 | MarketSimulation | `MonteCarloSimulator` | `market_simulation/` | Background thread | WARN 15,000ms CRIT 30,000ms |
| 9 | RiskGuardian | `RiskGuardianAgent` | `risk_guardian/` | Dedicated monitoring loop; highest priority | Alert within 100ms |
| 10 | DebateAndDecision | `DebateEngine` + 5 agents + `DecisionEngine` | `debate_and_decision/` | In-process; sequential | WARN 2,000ms CRIT 5,000ms |
| 11 | ExecutionEngine | `OrderManager` + broker adapters | `execution_engine/` | In-process; async fill monitoring | WARN 2,000ms CRIT 5,000ms |
| 12 | TradeMonitoring | `TradeMonitor` + `StrategyHealthMonitor` | `trade_monitoring/` | Dedicated background thread; 5s poll | Continuous; alert within 5s |
| 13 | LearningSystem | `LearningEngine` + `StrategyPerformanceTracker` | `learning_system/` | In-process EOD + event-triggered | 15min per event |
| 14 | PerformanceAnalytics | `DrawdownAnalyzer` + `WalkForwardTester` | `performance_analytics/` | Background EOD batch | Background |
| 15 | ResearchLab | `StrategyEvolutionAgent` | `research_lab/` | Off-hours background thread | Up to 60min |
| 16 | ValidationEngine | `ValidationPipeline` | `validation_engine/` | EOD batch; sequential 6 stages | Up to 30min |
| 17 | ControlTower | `SystemMonitor` + `EventBus` + `StreamlitDashboard` | `system_monitor/` + dashboard container | Main process (monitor) + separate container (dashboard) | N/A |

---

### 2.2 Software Layer Architecture Diagram

```
╔══════════════════════════════════════════════════════════════════════╗
║           AI TRADING BRAIN — SOFTWARE LAYER ARCHITECTURE            ║
╠══════════════════════════════════════════════════════════════════════╣
║  CONTAINER: ai-trading-brain                                         ║
║  ┌──────────────────────────────────────────────────────────────┐  ║
║  │ ORCHESTRATION PLANE                                            │  ║
║  │  MasterOrchestrator ─── APScheduler ─── CycleEngine          │  ║
║  └───────────────────────────────┬──────────────────────────────┘  ║
║                                   │ triggers                         ║
║  ┌────────────────────────────────▼─────────────────────────────┐  ║
║  │ INTELLIGENCE PLANE (Layers 1–10)                              │  ║
║  │                                                                │  ║
║  │  [L1] GlobalDataAI ──► [L2] MarketIntelligence               │  ║
║  │                │               │                              │  ║
║  │                └───────────────►[L3] MetaLearning             │  ║
║  │                                        │                      │  ║
║  │                               [L4] OpportunityEngine          │  ║
║  │                                        │                      │  ║
║  │                               [L5] StrategyLab                │  ║
║  │                                        │                      │  ║
║  │                [L8] MarketSim ◄──── [L6] CapitalRiskEngine    │  ║
║  │                       │                │                      │  ║
║  │                       └──────────► [L7] RiskControl           │  ║
║  │                                        │                      │  ║
║  │  [L9] RiskGuardian (always watching) ──┤                      │  ║
║  │                                        │                      │  ║
║  │                               [L10] Debate + Decision          │  ║
║  │                               BullAgent  BearAgent             │  ║
║  │                               RiskAgent  TempAgent DevilAgent  │  ║
║  │                                        │                      │  ║
║  └────────────────────────────────────────┼──────────────────────┘  ║
║                                           │                          ║
║  ┌────────────────────────────────────────▼─────────────────────┐  ║
║  │ EXECUTION PLANE (Layer 11)                                     │  ║
║  │  OrderManager ──► DhanBroker / ZerodhaBroker (sim or live)    │  ║
║  └────────────────────────────────────────┬─────────────────────┘  ║
║                                           │ position lifecycle       ║
║  ┌────────────────────────────────────────▼─────────────────────┐  ║
║  │ LEARNING PLANE (Layers 12–16)                                  │  ║
║  │                                                                │  ║
║  │  [L12] TradeMonitor ──► [L13] LearningEngine                  │  ║
║  │                                    │                          │  ║
║  │                          [L14] PerformanceAnalytics           │  ║
║  │                                    │                          │  ║
║  │                          [L15] ResearchLab                    │  ║
║  │                                    │                          │  ║
║  │                          [L16] ValidationEngine               │  ║
║  └────────────────────────────────────────────────────────────────┘  ║
║                                                                        ║
║  CONTROL PLANE (Layer 17 — partial in main container)                 ║
║  ┌──────────────────────────────────────────────────────────────┐    ║
║  │  SystemMonitor + EventBus + SQLite Telemetry + TelegramBot   │    ║
║  └──────────────────────────────────────────────────────────────┘    ║
║                                                                        ║
║  CONTAINER: trading-dashboard (read-only access to data/)             ║
║  ┌──────────────────────────────────────────────────────────────┐    ║
║  │  Streamlit Dashboard ─── reads from shared data/ volume      │    ║
║  └──────────────────────────────────────────────────────────────┘    ║
╚══════════════════════════════════════════════════════════════════════╝
```

---

### 2.3 Plane Architecture Definitions

| Plane | Layers | Responsibility | Execution Context | Failure Behaviour |
|---|---|---|---|---|
| Orchestration | Cross-cutting | Sequence all cognitive cycles; enforce timing thresholds | Main process, main thread | Full system halt — highest criticality |
| Intelligence | 1–10 | Transform market data into investment decisions | Main process, synchronous per cycle | Decision generation stops; monitoring continues |
| Execution | 11 | Convert decisions into orders; track fills | Main process, semi-async fills | Orders not placed; positions unchanged |
| Learning | 12–16 | Extract lessons, evolve strategies, validate | Background threads + EOD batch | No new learning; system runs on prior knowledge |
| Control | 17 | System health, telemetry, alerts, dashboard | Partial main + separate container | Alerts suppressed; telemetry gaps; dashboard offline |

---

### 2.4 Layer Isolation Strategy

| Layer | Isolation Method | Failure Mode | Fallback Behaviour |
|---|---|---|---|
| GlobalIntelligence (1) | 5-min TTL cache + background pre-warm | Network timeout | Return stale GlobalSnapshot (up to 15min) |
| MarketIntelligence (2) | 30s scan independent of cycle | Scan thread crash | Restart thread; return prior regime signal |
| MetaLearning (3) | In-memory model; retrained on regime transition | Model load failure | Equal-weight strategy recommendation |
| OpportunityEngine (4) | Scan results cached per 30s tick | Feed unavailable | Return prior OpportunityList with STALE flag |
| StrategyLab (5) | In-memory strategy list; loaded at startup | Evolution failure | Maintain current strategy set unchanged |
| CapitalRiskEngine (6) | Per-request synchronous computation | Calculation error | Return minimum safe size (0.5% portfolio) |
| RiskControl (7) | Synchronous; no async path | Layer unavailable | Default REJECTED for all approvals |
| MarketSimulation (8) | Background thread; results available on demand | Thread failure | Return prior simulation results with STALE flag |
| RiskGuardian (9) | Dedicated highest-priority monitoring loop | Self-health failure | Activate kill-switch as fail-safe |
| DebateAndDecision (10) | Synchronous; all 5 agents sequential | Any agent unavailable | Suspend hypothesis; return to queue |
| ExecutionEngine (11) | Async fill monitoring; sync placement | Broker unreachable | Cancel all pending; alert Human Principal |
| TradeMonitoring (12) | Dedicated background thread; 5s poll | Thread crash | Alert Human Principal; attempt thread restart |
| LearningSystem (13) | EOD batch + event-triggered | Batch failure | Queue events in durable store; process on recovery |
| PerformanceAnalytics (14) | EOD batch | Batch failure | Skip report; alert for manual review |
| ResearchLab (15) | Off-hours background thread | Evolution failure | Maintain current strategies; log failure |
| ValidationEngine (16) | Sequential EOD batch | Stage failure | Hold candidate pending retry; alert |
| ControlTower (17) | Separate container for dashboard | Dashboard crash | Trading engine unaffected; restart dashboard |

---

### 2.5 Singleton Registry

These components must have exactly one instance in the process at all times.

| Singleton | Accessor | Module | Violation Consequence |
|---|---|---|---|
| `StrategyPerformanceTracker` | `get_performance_tracker()` | `learning_system/` | Duplicate state; inconsistent win rates |
| `RegimeStrategyMap` | `get_regime_strategy_map()` | `meta_learning/` | Duplicate learning; conflicting weights |
| `TelegramBot` | `get_telegram_bot()` | `notifications/` | Duplicate connections; rate limit violations |
| `DataFeedManager` | `get_feed_manager()` | `data_feeds/` | Duplicate subscriptions; conflicting feeds |
| `SystemMonitor` | Class-level | `system_monitor/` | Duplicate telemetry; incoherent records |
| `EventBus` | Module-level | `system_monitor/` | Duplicate routing; lost events |
| `RiskGuardianAgent` | Orchestrator-owned | `risk_guardian/` | Multiple kill-switches; undefined state |

---

### 2.6 Cross-Plane Data Flow Timeline

```
T+0ms    T+20ms   T+50ms   T+80ms   T+110ms  T+140ms  T+170ms  T+200ms
│        │        │        │        │         │        │        │
ORCH: [CYCLE_START]─────────────────────────────────────────────[CYCLE_END]
│        │        │        │        │         │        │        │
INTEL: [L1]──►[L2]──►[L3]──►[L4]──►[L5]──►[L6]──►[L7]──►[L10]──►[DECISION]
│        GlobalSnap  Regime  Weights  Opps  Strategy  Risk  Debate  Record
│        │        │        │        │         │        │        │
EXEC:   │        │        │        │         │        │     [ORDER_PLACED]
│        │        │        │        │         │        │        │
LEARN:  │        │        │        │         │        │        │[OUTCOME_Q]
│        │        │        │        │         │        │        │
CTRL:  [HEARTBEAT]────────────────────────────────────────────────────────►
       [AUDIT_REC at every stage transition — continuous]
```

---

## PART III — MODULE DECOMPOSITION

### 3.0 Overview

Module decomposition defines the internal structure of each software layer: the modules it contains, the responsibility of each module, the inputs and outputs each processes, and the other modules it depends on.

---

### 3.1 Complete Module Hierarchy

```
ai_trading_brain/
├── orchestrator/
│   ├── master_orchestrator.py        Main cycle engine, scheduler integration
│   └── scheduler.py                  APScheduler job definitions
│
├── global_intelligence/
│   └── global_data_ai.py             GlobalDataAI; 5-min cache; pre-warm thread
│
├── market_intelligence/
│   ├── market_intelligence_engine.py NIFTY/BANKNIFTY regime; sector; events
│   └── market_monitor.py             30s continuous scan; 6 deep-scan slots
│
├── meta_learning/
│   ├── meta_learning_engine.py       Strategy weight adaptation driver
│   ├── knn_strategy_predictor.py     k-NN regime-to-strategy predictor
│   └── regime_strategy_map.py        Regime -> strategy learning accumulator (singleton)
│
├── opportunity_engine/
│   ├── equity_scanner.py             200+ NSE equity opportunity scanner
│   ├── options_opportunity_engine.py Options chain analysis and signal generation
│   └── arbitrage_detector.py        Index/ETF arbitrage opportunity detector
│
├── strategy_lab/
│   ├── meta_strategy_controller.py   Active strategy portfolio management
│   ├── strategy_generator_ai.py      Strategy generation and evolutionary mutation
│   ├── backtesting_ai.py             [PROTECTED] In-sample + OOS backtesting
│   └── evolved_strategies/           [PROTECTED] Evolved strategy JSON genomes
│
├── capital_risk_engine/
│   └── position_sizer.py             Kelly-fraction position sizing
│
├── risk_control/
│   ├── risk_manager_ai.py            Risk approval authority
│   ├── portfolio_allocation.py       Portfolio-level concentration limits
│   └── stress_testing.py            Monte Carlo + historical crisis scenarios
│
├── market_simulation/
│   └── monte_carlo_simulator.py      14-scenario Monte Carlo simulation
│
├── risk_guardian/
│   └── risk_guardian.py              [PROTECTED] Kill-switch — VIX>45 OR DD>2%
│
├── debate_and_decision/
│   ├── debate_engine.py              5-agent debate coordinator
│   ├── bull_agent.py                 Bull thesis agent
│   ├── bear_agent.py                 Bear thesis agent
│   ├── risk_agent.py                 Risk assessment agent
│   ├── temporal_agent.py             Time horizon agent
│   ├── devils_advocate_agent.py      Contrarian thesis agent
│   └── decision_engine.py           Aggregate debate -> decision record
│
├── execution_engine/
│   ├── order_manager.py              Order routing; paper trade CSV journal
│   └── zerodha_broker.py            Broker adapter (simulation mode)
│
├── trade_monitoring/
│   ├── trade_monitor.py             Per-position monitoring; stop/target enforcement
│   └── strategy_health_monitor.py   Strategy-level health tracking
│
├── learning_system/
│   ├── learning_engine.py           Attribution; lesson extraction; belief update
│   └── strategy_performance_tracker.py  Win rate tracking; auto-disable (singleton)
│
├── performance_analytics/
│   ├── drawdown_analyzer.py         Drawdown metrics; daily/weekly/monthly
│   └── walk_forward_tester.py       OOS walk-forward validation
│
├── research_lab/
│   └── strategy_evolution_agent.py  Weekly evolution; promotion gate check
│
├── validation_engine/
│   └── validation_pipeline.py       [PROTECTED] 6-stage: BT->WFT->CrossMkt->MC->Sens->Regime
│
├── data_feeds/
│   ├── data_feed_manager.py         Feed router singleton; fallback logic
│   ├── dhan_feed.py                 [PROTECTED] Dhan broker feed; auth; order routing
│   └── yahoo_feed.py               yfinance fallback feed (timeout=8s)
│
├── notifications/
│   └── telegram_bot.py              13 commands; alert dispatch; singleton
│
├── system_monitor/
│   └── system_monitor.py            time_layer() telemetry; EventBus; WARN/CRIT overrides
│
├── config.py                        Central configuration constants
├── main.py                          Entry point; --paper; --telegram; SIGTERM handler
├── requirements.txt                 Python dependencies
├── Dockerfile                       Trading engine container image
├── docker-compose.yml               2-container compose file
└── data/                            [PROTECTED] Persistent volume
    ├── trading_brain.db             SQLite: telemetry, learning, decisions
    └── paper_trades.csv             Paper trade journal (append-only)
```

---

### 3.2 Module Responsibility Matrix

| Module | Primary Responsibility | Secondary Responsibility | Owns (data) | Consumes (data) |
|---|---|---|---|---|
| `master_orchestrator` | Sequence the cognitive cycle; enforce layer timing | Schedule market-hours guard; manage pre/post-market | CycleRecord, LayerTimingRecord | All layer outputs |
| `global_data_ai` | Fetch and cache global market context (S&P, Nikkei, bonds, FX) | Background pre-warm 30min before market open | GlobalSnapshot (5min cache) | External APIs via `data_feed_manager` |
| `market_intelligence_engine` | NIFTY/BANKNIFTY regime detection; sector analysis; event calendar | Liquidity assessment; FII/DII flow | RegimeSignal, SectorReport | `data_feed_manager` outputs |
| `market_monitor` | Continuous 30s scan of market conditions | 6 deep-scan slots for focused analysis | ScanResult | `data_feed_manager`, `market_intelligence_engine` |
| `knn_strategy_predictor` | Predict strategy weights from regime features | Maintain k-NN index of regime-outcome history | PredictionRecord | RegimeSignal, PerformanceHistory |
| `regime_strategy_map` | Accumulate regime-to-strategy performance data | Provide regime history for k-NN model | RegimeStrategyRecord | RegimeSignal, StrategyOutcome |
| `equity_scanner` | Scan 200+ NSE symbols for opportunity signals | Rank and filter by signal strength | OpportunityList | `data_feed_manager` quote/history |
| `options_opportunity_engine` | Analyse option chains for trading opportunities | IV analysis; premium capture opportunities | OptionsOpportunityList | Options chain data via `data_feed_manager` |
| `meta_strategy_controller` | Manage active strategy portfolio; enable/disable strategies | Apply regime weight recommendations | ActiveStrategySet | OpportunityList, StrategyWeights, PerformanceHistory |
| `strategy_generator_ai` | Generate hypothesis templates; mutate evolved strategies | Apply `min_signal_rr` filter to evolved variants | StrategyHypothesis | ActiveStrategySet, MarketConditions |
| `position_sizer` | Compute position size using quarter-Kelly fraction | Regime-adjusted size overrides | PositionSizeRecommendation | ConvictionScore, PortfolioState, VolatilityMeasure |
| `risk_manager_ai` | Issue or deny risk approval for every proposed trade | Apply daily loss limit; position limit checks | RiskApprovalRecord | PositionSizeRecommendation, PortfolioState, VIX |
| `portfolio_allocation` | Track and enforce portfolio-level concentration limits | Sector, theme, and entity concentration limits | AllocationState | OpenPositions, SectorClassifications |
| `stress_testing` | Run 14 Monte Carlo + 8 historical stress scenarios | Compute worst-case portfolio loss | StressTestReport | PortfolioState, HistoricalScenarios |
| `monte_carlo_simulator` | Generate 14-scenario market outcome distributions | Provide probability distribution of portfolio outcomes | SimulationResult | PortfolioState, VolatilityParameters |
| `risk_guardian` | Enforce kill-switch conditions continuously | Alert on approaching kill-switch thresholds | KillSwitchState | VIX, DayPnL, SinglePositionPnL |
| `debate_engine` | Coordinate 5-agent debate on hypothesis | Enforce debate completion; record dissent | DebateRecord | HypothesisPackage, 5 agent votes |
| `decision_engine` | Aggregate debate results into decision | Apply conviction threshold (6.5); set validity window | DecisionRecord | DebateRecord, ConvictionScore |
| `order_manager` | Route approved decisions to broker; journal trades | Enforce PAPER_TRADING flag; maintain CSV journal | OrderRecord, FillRecord | DecisionRecord, RiskApprovalRecord |
| `trade_monitor` | Monitor all open positions every 5 seconds | Enforce stop-loss and profit-target automatically | MonitoringState, PositionAlert | LivePriceData, OpenPositions |
| `learning_engine` | Extract lessons from closed trade outcomes | Propagate lessons across domains | LearningEvent, LessonRecord | OutcomeRecord, AttributionRecord |
| `strategy_performance_tracker` | Track win rate per strategy; auto-disable underperformers | Recover closed trades from CSV on restart | PerformanceRecord | OrderRecord, FillRecord |
| `drawdown_analyzer` | Compute daily/weekly/max drawdown metrics | Alert on drawdown threshold approach | DrawdownMetric | PortfolioValueHistory |
| `walk_forward_tester` | OOS validation of evolved strategies | Walk-forward window management | WFTResult | StrategyCandidate, HistoricalData |
| `strategy_evolution_agent` | Weekly strategy mutation and fitness evaluation | Filter by min_rr from JSON; honour min_signal_rr | EvolvedStrategyCandidate | PerformanceHistory, RegimeHistory |
| `validation_pipeline` | 6-stage strategy validation before promotion | Enforce: WinRate>=50%, Sharpe>0.8, MaxDD<15% | ValidationReport | EvolvedStrategyCandidate, all analytics outputs |
| `data_feed_manager` | Route data requests to primary (Dhan) or fallback (yfinance) | Maintain warm fallback connection | FeedState | Dhan API, yfinance |
| `telegram_bot` | Dispatch alerts; handle 13 command types | Authenticate Human Principal commands | MessageLog | All layer state (read-only) |
| `system_monitor` | Record layer timing; manage EventBus; enforce WARN/CRIT | LAYER_LATENCY_WARN/CRIT overrides | LatencyRecord, HealthEvent | All component metrics via `time_layer()` |

---

### 3.3 Inter-Module Dependency Table

| Module (Consumer) | Depends On (Producer) | Dependency Type | Failure Impact |
|---|---|---|---|
| `master_orchestrator` | All layer entry points | Orchestration | Full cycle fails |
| `global_data_ai` | `data_feed_manager` | Data fetch | Falls back to cache |
| `market_monitor` | `data_feed_manager` | Data feed | Returns stale scan |
| `knn_strategy_predictor` | `regime_strategy_map` | Model data | Returns equal weights |
| `equity_scanner` | `data_feed_manager` | Data feed | Returns prior list |
| `meta_strategy_controller` | `equity_scanner`, `knn_strategy_predictor`, `strategy_performance_tracker` | Multiple data | Maintains prior strategy set |
| `position_sizer` | `risk_manager_ai` (for portfolio state) | Portfolio context | Returns minimum size |
| `risk_manager_ai` | `portfolio_allocation`, `stress_testing` | Risk context | Default REJECTED |
| `debate_engine` | 5 agent modules | Agent votes | Debate suspended |
| `decision_engine` | `debate_engine` | Debate result | HOLD decision |
| `order_manager` | `decision_engine`, broker adapters | Decision + execution | No orders placed |
| `trade_monitor` | `data_feed_manager`, `risk_guardian` | Live price + kill state | Alert Human Principal |
| `learning_engine` | `trade_monitor`, `strategy_performance_tracker` | Trade events | Queue; process later |
| `strategy_evolution_agent` | `strategy_performance_tracker`, `backtesting_ai` | Performance + backtest | Keep current strategies |
| `validation_pipeline` | `backtesting_ai`, `walk_forward_tester`, `drawdown_analyzer`, `monte_carlo_simulator` | All analytics | Hold candidate |
| `telegram_bot` | All layer state (read-only) | Observability | Alerts suppressed |
| `system_monitor` | All components via `time_layer()` | Telemetry | Gaps in metrics |

---

### 3.4 Protected Module Policy

| Protected Module | Risk Category | Protection Level | Unlock Condition |
|---|---|---|---|
| `risk_guardian/risk_guardian.py` | Capital safety | CRITICAL — explicit instruction required | New kill condition; threshold change |
| `strategy_lab/backtesting_ai.py` | Promotion quality gate | HIGH — calibrated OOS validation | New metrics; additional test type |
| `validation_engine/` (all) | Strategy promotion | HIGH — 6-stage pipeline | New stage; adjusted promotion threshold |
| `strategy_lab/evolved_strategies/` | Evolved strategy value | MEDIUM — earned through evolution | Parameter tuning; fitness re-evaluation |
| `data/` directory | Data integrity | CRITICAL — live databases | Schema migrations only; never destructive |
| `data_feeds/dhan_feed.py` | Broker connectivity | HIGH — authentication and order routing | New endpoint mapping; fallback logic |

---

## PART IV — REPOSITORY STRUCTURE

### 4.0 Overview

The repository structure defines how source code, configuration, data, and documentation are organised within the monorepo. The structure reflects the module hierarchy but adds engineering concerns: test organisation, script utilities, CI/CD configuration, environment management, and documentation.

---

### 4.1 Top-Level Repository Layout

```
ai_trading_brain/                          (repository root)
│
├── .github/                               GitHub Actions and workflow definitions
│   ├── workflows/
│   │   ├── ci.yml                        Continuous integration: lint + test
│   │   └── deploy.yml                    Deployment to VPS on push to main
│   ├── copilot-instructions.md           AI assistant instructions (this project)
│   └── skills/                           Copilot skill definitions
│
├── .venv/                                Python virtual environment (not committed)
│
├── orchestrator/                          Layer 0: orchestration
├── global_intelligence/                   Layer 1
├── market_intelligence/                   Layer 2
├── meta_learning/                         Layer 3
├── opportunity_engine/                    Layer 4
├── strategy_lab/                          Layer 5
├── capital_risk_engine/                   Layer 6
├── risk_control/                          Layer 7
├── market_simulation/                     Layer 8
├── risk_guardian/                         Layer 9 (Protected)
├── debate_and_decision/                   Layer 10
├── execution_engine/                      Layer 11
├── trade_monitoring/                      Layer 12
├── learning_system/                       Layer 13
├── performance_analytics/                 Layer 14
├── research_lab/                          Layer 15
├── validation_engine/                     Layer 16 (Protected)
├── data_feeds/                            Cross-cutting: data acquisition
├── notifications/                         Cross-cutting: human interface
├── system_monitor/                        Layer 17 (partial)
│
├── tests/                                 Test suite (mirrors source structure)
│   ├── unit/                             Module-level unit tests
│   │   ├── test_global_data_ai.py
│   │   ├── test_market_intelligence.py
│   │   ├── test_position_sizer.py
│   │   ├── test_risk_manager_ai.py
│   │   ├── test_decision_engine.py
│   │   ├── test_order_manager.py
│   │   ├── test_learning_engine.py
│   │   └── ... (one test file per module)
│   ├── integration/                      Cross-module integration tests
│   │   ├── test_intelligence_plane.py    Layers 1–10 integration
│   │   ├── test_execution_pipeline.py    Decision → Order → Fill
│   │   ├── test_learning_pipeline.py     Outcome → Learning → Memory
│   │   └── test_full_cycle.py           End-to-end cognitive cycle
│   └── constitutional/                   Constitutional compliance tests
│       ├── test_invariants.py            All 60 invariant checks
│       ├── test_audit_trail.py          Audit trail completeness
│       └── test_kill_switch.py          Kill-switch activation and fail-safe
│
├── scripts/                              Operational and maintenance scripts
│   ├── autostart.bat                     Windows Task Scheduler entry point
│   ├── setup_windows_task.py             Register 08:00 weekday Task Scheduler job
│   ├── morning_report.py                 Pre-market briefing generator
│   ├── check_pnl.py                      PnL inspection utility
│   ├── check_positions.py               Open position inspection
│   ├── calibrate.py                      System calibration utility
│   └── cycle_health_monitor_vps.py       VPS health monitoring script
│
├── data/                                  [PROTECTED] Persistent volume
│   ├── trading_brain.db                  Primary SQLite database
│   └── paper_trades.csv                  Paper trade journal (append-only)
│
├── config.py                              Central configuration (SCHEDULE, thresholds)
├── main.py                               Entry point: --paper, --telegram, SIGTERM
├── requirements.txt                       Python dependencies (pinned versions)
├── Dockerfile                            Trading engine container definition
├── docker-compose.yml                     2-container compose file
│
└── docs/                                  Architecture documentation series
    ├── MASTER_KNOWLEDGE_ARCHITECTURE.md  Phase 1
    ├── INFORMATION_ONTOLOGY.md           Phase 2
    ├── ENTITY_ONTOLOGY.md               Phase 3
    ├── RELATIONSHIP_ONTOLOGY.md         Phase 4
    ├── EVENT_ONTOLOGY.md               Phase 5
    ├── REASONING_ARCHITECTURE.md       Phase 6
    ├── DECISION_ARCHITECTURE.md        Phase 7
    ├── LEARNING_ARCHITECTURE.md        Phase 8
    ├── MEMORY_ARCHITECTURE.md          Phase 9
    ├── INVESTMENT_INTELLIGENCE_OPERATING_SYSTEM.md  Phase 10
    └── AI_TRADING_BRAIN_ENGINEERING_BLUEPRINT.md    This document
```

---

### 4.2 Package Boundary Rules

| Rule | Description | Enforcement | Rationale |
|---|---|---|---|
| No cross-layer direct import | Module in Layer N may not import directly from Layer N+2 or higher | Dependency graph audit | Enforces constitutional layer sequence |
| No downward dependency from Learning Plane to Intelligence Plane | Learning modules (12–16) may not import from Intelligence modules (1–10) during cycle | Import analysis | Learning is a consequence of decisions, not an input |
| Protected module imports | Protected modules may only be imported by their owning layer | Protected module registry | Prevents accidental modification via indirect use |
| Singleton access only via accessor | All singletons accessed only via their defined accessor function | Code review policy | Prevents duplicate instantiation |
| `config.py` is read-only at runtime | No module may write to `config.py` during execution | Static analysis | Configuration stability |
| `data/` writes are append-only | No module may update an existing record in the data volume | Write audit | INV-17 historical immutability |
| Test files mirror source structure | Every source module has a corresponding test file | Test coverage audit | Module-level testability |

---

### 4.3 Configuration Management

All system configuration is centralised in `config.py`. No module may define its own configuration constants that duplicate entries in `config.py`.

| Configuration Domain | Key Constants | Used By | Change Protocol |
|---|---|---|---|
| **Scheduling** | `SCHEDULE` dict; pre-market/market/EOD/weekly slots | `master_orchestrator`, `scheduler` | Architecture Council review |
| **Scan intervals** | `CONTINUOUS_SCAN_INTERVAL = 30` (seconds) | `market_monitor`, `equity_scanner` | Architecture Council review |
| **Risk thresholds** | `KILL_VIX_THRESHOLD`, `DAILY_LOSS_LIMIT`, `MAX_POSITION_PCT` | `risk_guardian`, `risk_manager_ai` | CRITICAL: Human Principal required |
| **Conviction threshold** | `CONVICTION_THRESHOLD = 6.5` | `decision_engine` | Constitutional amendment required |
| **Strategy promotion gates** | `MIN_WIN_RATE = 0.50`, `MIN_SHARPE = 0.8`, `MAX_DD = 0.15` | `validation_pipeline`, `strategy_evolution_agent` | Architecture Council review |
| **Broker mode** | `PAPER_TRADING = True/False` | `order_manager` | Human Principal required; MAJOR change |
| **Data feed** | `FEED_TIMEOUT = 8` (seconds) | `yahoo_feed`, `data_feed_manager` | Architecture Council review |
| **Layer latency overrides** | `LAYER_LATENCY_WARN_OVERRIDES`, `LAYER_LATENCY_CRIT_OVERRIDES` | `system_monitor` | Architecture Council review |
| **Symbol universe** | `EQUITY_UNIVERSE`, `INDEX_SYMBOLS` | `equity_scanner`, `market_monitor` | Architecture Council review |

---

### 4.4 Environment Management

| Environment | Purpose | Key Differences | Entry Point |
|---|---|---|---|
| **Development** | Local development and testing | PAPER_TRADING=True; local SQLite; Telegram test bot | `python main.py --paper` |
| **Test** | Automated test suite execution | Mocked feeds; in-memory SQLite; no Telegram | `pytest tests/` |
| **Staging (VPS pre-deploy)** | Pre-production validation | PAPER_TRADING=True; VPS resources; real feeds | `docker compose up -d` (staging compose) |
| **Production (VPS)** | Live paper trading | PAPER_TRADING=True; both containers healthy | `docker compose up -d` (production compose) |
| **Live (future)** | Real-money trading | PAPER_TRADING=False; broker auth active | Requires Human Principal approval |

---

### 4.5 Dependency Management

| Principle | Requirement | Verification |
|---|---|---|
| Pinned versions | All dependencies in `requirements.txt` must use exact version pins | `pip-audit` in CI |
| Minimal dependencies | Only add a dependency when it provides functionality that cannot be reasonably implemented without it | Dependency review in PR |
| Security audit | All dependencies scanned for known vulnerabilities before adding | `pip-audit` or `safety check` in CI |
| No transitive dependency risk | Dependencies with known transitive conflicts are not used | Dependency resolution test |
| Python 3.14 compatibility | All dependencies tested against Python 3.14 | CI test matrix |

---

## PART V — SERVICE ARCHITECTURE

### 5.0 Overview

The service architecture defines how the AI Trading Brain is decomposed into independently deployable services (processes or containers), the responsibility of each service, the boundaries between services, and the topology of the deployment.

In the current deployment, the AI Trading Brain runs as two Docker containers on a single VPS. The service architecture is designed to evolve — new services can be added without disrupting existing ones.

---

### 5.1 Service Catalog

| Service ID | Service Name | Container | Primary Responsibility | Always Running? |
|---|---|---|---|---|
| SVC-01 | Trading Engine | `ai-trading-brain` | Execute cognitive cycles; manage all intelligence layers; place orders | Yes — during all market hours |
| SVC-02 | Dashboard | `trading-dashboard` | Serve Streamlit web dashboard; read-only data visualisation | Yes — 24/7 access |
| SVC-03 | Telegram Gateway | Embedded in SVC-01 | Dispatch alerts; handle human principal commands | Yes — embedded in trading engine |
| SVC-04 | Data Feed Manager | Embedded in SVC-01 | Route data requests; manage fallback; Dhan + yfinance | Yes — during market hours |
| SVC-05 | Monitoring Thread | Embedded in SVC-01 | Position monitoring; kill-switch enforcement | Yes — dedicated thread |
| SVC-06 | Scan Thread | Embedded in SVC-01 | 30-second continuous market scan | Yes — during market hours |
| SVC-07 | Learning Batch | Embedded in SVC-01 | EOD learning event processing | Scheduled — 15:35–17:30 IST |
| SVC-08 | Evolution Thread | Embedded in SVC-01 | Weekly strategy evolution run | Scheduled — Thursday off-hours |

---

### 5.2 Service Topology Diagram

```
INTERNET / BROKER APIs
        │
        │  HTTPS / REST
        ▼
┌─────────────────────────────────────────────────────────────┐
│  VPS: root@178.18.252.24                                     │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  CONTAINER: ai-trading-brain (SVC-01)                  │   │
│  │                                                        │   │
│  │  Process: main.py                                      │   │
│  │    Thread: Main (Orchestrator + Intelligence Plane)    │   │
│  │    Thread: RiskGuardian (SVC-05) — highest priority   │   │
│  │    Thread: MarketMonitor / ScanThread (SVC-06)        │   │
│  │    Thread: GlobalDataAI pre-warm                       │   │
│  │    Thread: StressTest (background, off-cycle)          │   │
│  │    Thread: StrategyEvolution (SVC-08, off-hours)       │   │
│  │                                                        │   │
│  │  Embedded: TelegramBot (SVC-03) async event loop       │   │
│  │  Embedded: DataFeedManager (SVC-04) connection pool    │   │
│  │  Embedded: APScheduler for all job scheduling          │   │
│  │                                                        │   │
│  │  Volume mount: ./data:/app/data (read-write)           │   │
│  └──────────────────────────────────────────────────────┘   │
│                          │                                    │
│                    shared volume                              │
│                          │                                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  CONTAINER: trading-dashboard (SVC-02)                 │   │
│  │                                                        │   │
│  │  Process: streamlit run dashboard.py                   │   │
│  │  Volume mount: ./data:/app/data (READ-ONLY)            │   │
│  │  Port: 8501 exposed                                    │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
└─────────────────────────────────────────────────────────────┘
        │                        │
        │ Telegram API HTTPS      │ Dhan API / yfinance HTTPS
        ▼                        ▼
   Human Principal          Market Data

```

---

### 5.3 Service Boundary Matrix

| Boundary | Type | Protocol | Data Direction | Failure Handling |
|---|---|---|---|---|
| Trading Engine → Dhan API | External network | REST HTTPS | Bidirectional (fetch data + place orders) | Fallback to yfinance for data; retry orders |
| Trading Engine → yfinance | External network | HTTPS | Inbound (data only) | 8s timeout; cache last result |
| Trading Engine → Telegram | External network | HTTPS Bot API | Outbound (alerts); inbound (commands) | Queue alerts; retry on next cycle |
| Trading Engine → data/ volume | Local filesystem | File I/O | Bidirectional (read + append) | Filesystem failure = critical; halt |
| Dashboard → data/ volume | Local filesystem | File I/O | Inbound (read-only) | Dashboard shows stale data |
| Trading Engine internal threads | In-process | Shared memory + Queue | Bidirectional | Thread restart; alerting |

---

### 5.4 Service Health Model

Each service reports health through the `system_monitor` component. Health is evaluated at three levels.

| Health Level | Definition | Response | Alert |
|---|---|---|---|
| **Healthy** | All threads running; cycle latency within WARN threshold; no open violations | Normal operation | None |
| **Degraded** | One or more metrics exceed WARN threshold; no constitutional violations | Investigation triggered; continue operation | Level 2 alert |
| **Unhealthy** | Constitutional violation; critical latency exceeded; kill-switch active | Governance escalation; possible halt | Level 4+ alert |
| **Failed** | Container not running; health probe failing | `docker compose ps` shows not healthy | Human Principal immediate notification |

The Docker health probe is the external health check mechanism. Both containers must show `Up N seconds (healthy)` before any deployment is considered complete.

---

### 5.5 Container Specification

**Container 1 — ai-trading-brain**

| Attribute | Specification |
|---|---|
| Base image | Python 3.14-slim |
| Entry point | `python main.py` |
| Environment variables | `DHAN_TOKEN`, `TELEGRAM_BOT_TOKEN`, `PAPER_TRADING=True` |
| Volume mounts | `./data:/app/data` (read-write) |
| Restart policy | `unless-stopped` |
| Health probe | HTTP check on internal health endpoint OR process heartbeat |
| Resource limits | Memory: 1GB; CPU: 2 cores |
| Network | Bridge network; outbound HTTPS; no inbound |

**Container 2 — trading-dashboard**

| Attribute | Specification |
|---|---|
| Base image | Python 3.14-slim + Streamlit |
| Entry point | `streamlit run dashboard/app.py --server.port 8501` |
| Volume mounts | `./data:/app/data` (read-only) |
| Restart policy | `unless-stopped` |
| Health probe | HTTP GET /healthz on port 8501 |
| Resource limits | Memory: 512MB; CPU: 1 core |
| Network | Bridge network; port 8501 exposed |
| Dependency | Starts after `ai-trading-brain` is healthy |

---

### 5.6 Process Thread Model

The Trading Engine container runs one Python process with multiple threads. Thread isolation is critical because Python's GIL means threads cannot run CPU-bound code truly in parallel — but they can run I/O-bound code concurrently.

| Thread | Name | Type | Priority | Blocking? | Restart Policy |
|---|---|---|---|---|---|
| Main thread | `orchestrator` | CPU-bound during cycle; I/O during network | Highest | Blocks during cycle | System restart required |
| RiskGuardian thread | `risk-guardian-monitor` | I/O-bound; polling | Highest | Non-blocking | Auto-restart with alert |
| MarketMonitor thread | `market-scan-30s` | I/O-bound; polling | High | Non-blocking | Auto-restart |
| GlobalData pre-warm | `global-prewarm` | I/O-bound; timed | Medium | Non-blocking | Auto-restart |
| StressTest background | `stress-test-bg` | CPU-bound; periodic | Low | Non-blocking | Drops result if cycle active |
| StrategyEvolution | `strategy-evolution` | CPU-bound; weekly | Lowest | Non-blocking; off-hours only | Manual restart |
| TradeMonitor | `trade-monitor-5s` | I/O-bound; polling | High | Non-blocking | Auto-restart with alert |

---

## PART VI — INTER-SERVICE COMMUNICATION

### 6.0 Overview

Inter-service communication defines how modules and services exchange information: the patterns used, the message structures, the timing guarantees, and the error handling. Because the AI Trading Brain is a single-process multi-threaded application, most communication is in-process. Cross-container communication uses the shared filesystem volume.

---

### 6.1 Communication Pattern Taxonomy

| Pattern | Description | Used Where | Advantages | Constraints |
|---|---|---|---|---|
| **Synchronous function call** | Caller invokes function; blocks until result returned | Intelligence Plane (Layers 1–10) | Lowest latency; simplest; auditable | Caller blocked; cascading failure risk |
| **Return value with status** | Function returns typed object including success/failure status | All module boundaries | Explicit failure handling; no exceptions in hot path | Caller must check status |
| **Thread-safe queue** | Producer puts item; consumer takes item; non-blocking | Monitoring → Learning; Evolution → Validation | Decouples producer from consumer | Queue depth must be bounded |
| **Shared memory with lock** | Singleton holds state; read/write protected by threading.Lock | GlobalSnapshot cache; RegimeClassification | Fast reads; consistent writes | Lock contention under high load |
| **Durable disk queue** | Events written to disk; processed by consumer | Learning events on system restart | Survives process crash | Disk I/O overhead |
| **File-based IPC** | Producer writes to shared volume; consumer reads | Trading Engine → Dashboard | Simple; observable; dashboard cannot corrupt engine | Latency; consistency |
| **External HTTP** | REST API calls to external services | data_feed_manager → Dhan/yfinance; Telegram | Standard; encrypted | Network latency; external dependency |

---

### 6.2 Critical Communication Sequences

**Sequence 1 — Full Cognitive Cycle (T+0 to T+200ms)**

```
MasterOrchestrator
    │
    ├─[1]─► GlobalDataAI.fetch() ──────────────────────────── T+0ms to T+5ms
    │         Returns: GlobalSnapshot (cache hit ~1ms; miss ~17ms)
    │
    ├─[2]─► MarketIntelligenceEngine.analyse() ────────────── T+5ms to T+20ms
    │         Inputs: GlobalSnapshot
    │         Returns: RegimeSignal, SectorReport
    │
    ├─[3]─► MetaLearningEngine.get_weights() ──────────────── T+20ms to T+30ms
    │         Inputs: RegimeSignal
    │         Returns: StrategyWeights
    │
    ├─[4]─► OpportunityEngine.scan() ──────────────────────── T+30ms to T+50ms
    │         Inputs: RegimeSignal, StrategyWeights
    │         Returns: OpportunityList
    │
    ├─[5]─► MetaStrategyController.get_hypotheses() ──────── T+50ms to T+65ms
    │         Inputs: OpportunityList, StrategyWeights
    │         Returns: HypothesisList
    │
    ├─[6]─► for each Hypothesis with conviction >= 6.5:
    │   │
    │   ├─[6a]─► PositionSizer.compute() ──────────────────── T+65ms to T+75ms
    │   │         Returns: PositionSizeRecommendation
    │   │
    │   ├─[6b]─► RiskManagerAI.approve() ─────────────────── T+75ms to T+85ms
    │   │         Returns: RiskApprovalRecord (APPROVED or REJECTED)
    │   │
    │   ├─[6c]─► DebateEngine.debate() ────────────────────── T+85ms to T+130ms
    │   │         [Bull, Bear, Risk, Temporal, Devil's Advocate] vote
    │   │         Returns: DebateRecord with 5 votes
    │   │
    │   ├─[6d]─► DecisionEngine.decide() ─────────────────── T+130ms to T+145ms
    │   │         Returns: DecisionRecord (aggregate score >= 6.5 -> proceed)
    │   │
    │   └─[6e]─► OrderManager.submit() ────────────────────── T+145ms to T+200ms
    │             Returns: OrderRecord; appends to paper_trades.csv
    │
    └─[7]─► SystemMonitor.record_cycle() ─────────────────── T+200ms
              Stores latency record; triggers EventBus events
```

---

**Sequence 2 — Kill-Switch Activation**

```
RiskGuardian (dedicated thread; polling every 500ms)
    │
    ├─ reads: VIX level from data_feed_manager
    ├─ reads: DayPnL from order_manager
    ├─ reads: SinglePositionPnL from trade_monitor
    │
    [IF VIX > 45 OR DayPnL < -2% OR any SinglePosition < -8%]
    │
    ├─[1]─► KillSwitchState.activate() ────────────── T+0ms
    │         Sets atomic kill_switch_active = True
    │
    ├─[2]─► OrderManager.cancel_all_pending() ──────── T+0ms to T+50ms
    │         Cancels all orders not yet filled
    │
    ├─[3]─► TelegramBot.send_critical_alert() ──────── T+50ms to T+100ms
    │         Message: KILL_SWITCH_ACTIVATED
    │
    ├─[4]─► SystemMonitor.record_event() ────────────── T+100ms
    │         Event: KILL_SWITCH_ACTIVATED with trigger details
    │
    └─ All subsequent calls to DecisionEngine.decide() return BLOCKED
       All subsequent calls to OrderManager.submit() return BLOCKED
       Until Human Principal override via Telegram /override command
```

---

**Sequence 3 — Position Close → Learning Event**

```
TradeMonitor (dedicated thread; polling every 5s)
    │
    ├─ detects: StopLoss hit OR TargetHit OR Manual close
    │
    ├─[1]─► OrderManager.close_position() ──────────── T+0s
    │         Records FillRecord; updates paper_trades.csv
    │
    ├─[2]─► StrategyPerformanceTracker.record_outcome() T+1s
    │         Updates win rate; checks auto-disable threshold
    │
    ├─[3]─► LearningEngine.trigger_learning() ─────── T+5s
    │         Inputs: OutcomeRecord, DecisionRecord, EvidenceSet
    │         Begins attribution analysis
    │
    ├─[4]─► LearningEngine.extract_lesson() ─────────── T+1min
    │         Returns: LessonRecord with: what worked, what didn't
    │
    ├─[5]─► LearningEngine.update_beliefs() ─────────── T+3min
    │         Updates belief store; rate-limited by INV-34
    │
    └─[6]─► SystemMonitor.record_event() ─────────────── T+5min
              Event: LEARNING_EVENT_COMPLETE with learning record ID
```

---

**Sequence 4 — Data Feed Fallback**

```
data_feed_manager.get_quote(symbol)
    │
    ├─[1]─► DhanFeed.get_quote(symbol) ────────────────── T+0ms
    │         [IF HTTP 451 OR timeout > 8s OR connection error]
    │
    ├─[2]─► SystemMonitor.record_event(FEED_FALLBACK) ── T+8s
    │
    └─[3]─► YahooFeed.get_quote(symbol) ───────────────── T+8s to T+16s
              timeout=8s; returns TickerQuote with SOURCE=yahoo
              Consumer receives same interface; SOURCE field indicates fallback
```

---

### 6.3 Message Object Taxonomy

These are the key data transfer objects passed between modules. They are not implementation types — they define the information contracts.

| Object | Produced By | Consumed By | Key Fields | Immutable? |
|---|---|---|---|---|
| `GlobalSnapshot` | `global_data_ai` | `market_intelligence_engine` | `sp500_trend`, `vix_level`, `global_risk_score`, `timestamp`, `stale` | Yes — new snapshot each fetch |
| `RegimeSignal` | `market_intelligence_engine` | `meta_learning_engine`, `equity_scanner` | `regime_type`, `confidence`, `regime_age_days`, `transition_prob` | Yes |
| `StrategyWeights` | `meta_learning_engine` | `meta_strategy_controller` | `strategy_id` → `weight` map, `timestamp` | Yes |
| `OpportunityList` | `equity_scanner` | `meta_strategy_controller` | list of `{symbol, bias, strength, timestamp}` | Yes |
| `HypothesisPackage` | `meta_strategy_controller` | `debate_engine` | `hypothesis_text`, `conviction_raw`, `evidence_set_ids`, `invalidation_conditions` | Yes |
| `PositionSizeRec` | `position_sizer` | `risk_manager_ai`, `decision_engine` | `instrument`, `direction`, `capital_fraction`, `contracts`, `risk_contribution` | Yes |
| `RiskApprovalRecord` | `risk_manager_ai` | `decision_engine`, `order_manager` | `approved`, `max_size`, `reason`, `validity_window`, `timestamp` | Yes |
| `DebateRecord` | `debate_engine` | `decision_engine` | `5 agent votes`, `aggregate_score`, `minority_dissent`, `timestamp` | Yes |
| `DecisionRecord` | `decision_engine` | `order_manager` | `instrument`, `direction`, `size`, `conviction`, `debate_record_id`, `approval_id`, `validity_ts` | Yes |
| `OrderRecord` | `order_manager` | `trade_monitor`, `learning_engine` | `order_id`, `status`, `fill_price`, `fill_ts`, `strategy_id`, `decision_record_id` | Yes |
| `PositionAlert` | `trade_monitor` | `risk_guardian`, `telegram_bot` | `position_id`, `alert_type`, `trigger_price`, `pnl_at_alert` | Yes |
| `LearningEvent` | `learning_engine` | memory store | `outcome_record_id`, `attribution`, `lessons[]`, `belief_updates[]` | Yes |

---

### 6.4 Event Bus Architecture

The `EventBus` in `system_monitor` routes system events to registered handlers. Events are for observability and alerting — they do not control execution flow.

```
EventBus (system_monitor)
    │
    ├─ Subscribers: TelegramBot (alert-worthy events)
    ├─ Subscribers: Audit log writer (all events)
    ├─ Subscribers: Dashboard (state change events)
    │
    Events:
    │
    ├─ CYCLE_STARTED        { cycle_id, timestamp }
    ├─ CYCLE_COMPLETED      { cycle_id, duration_ms, decisions_count }
    ├─ LAYER_EXCEEDED_WARN  { layer_name, duration_ms, threshold_ms }
    ├─ LAYER_EXCEEDED_CRIT  { layer_name, duration_ms, threshold_ms }
    ├─ TRADE_OPENED         { position_id, instrument, direction, size, entry_price }
    ├─ TRADE_CLOSED         { position_id, pnl, hold_duration, reason }
    ├─ STOP_HIT             { position_id, stop_price, loss }
    ├─ TARGET_HIT           { position_id, target_price, gain }
    ├─ KILL_SWITCH_ACTIVATED{ trigger, vix_level, day_pnl }
    ├─ KILL_SWITCH_CLEARED  { cleared_by, timestamp }
    ├─ FEED_FALLBACK        { symbol, primary_error, fallback_source }
    ├─ REGIME_CHANGE        { prior_regime, new_regime, confidence }
    ├─ STRATEGY_DISABLED    { strategy_id, reason, win_rate }
    ├─ LEARNING_EVENT_COMPLETE { learning_event_id, outcome_pnl }
    ├─ INVARIANT_VIOLATION  { invariant_id, component, description }
    └─ HEALTH_DEGRADED      { component, metric, current_value, threshold }
```

---

### 6.5 Communication Timing Guarantees

| Communication Path | Timing Guarantee | Implementation | Violation Consequence |
|---|---|---|---|
| In-process function call (hot path) | < 1ms overhead | Direct function call | None — inherent to Python |
| SharedMemory cache read | < 5ms | dict lookup with Lock | Returns stale; STALE flag set |
| External API call (Dhan) | < 8s timeout | requests.get(timeout=8) | Fallback to yfinance |
| External API call (yfinance) | < 8s timeout | yf.download(timeout=8) | Returns prior result with STALE |
| Telegram message send | < 30s (best effort) | Async HTTP POST | Queued for retry |
| Thread queue put (non-blocking) | < 1ms | queue.put_nowait() | Queue full: drop with alert |
| Disk write (SQLite) | < 100ms per transaction | SQLite WAL mode | Block until complete; alert if > 1s |
| Disk append (CSV) | < 50ms | file.write() + flush() | Block; alert if > 500ms |
| Docker volume shared read | < 5ms | File read, 5s poll | Returns prior data (dashboard) |

---

## PART VII — DATA STORAGE STRATEGY

### 7.0 Overview

The data storage strategy defines where each category of data is stored, why that storage mechanism was chosen, how data flows between storage tiers, and how the constitutional requirement for historical immutability is enforced at the storage level.

---

### 7.1 Storage Tier Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    DATA STORAGE TIERS                            │
│                                                                   │
│  Tier 0 — In-Process Memory (Python objects)                     │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  GlobalSnapshot cache     (dict + threading.Lock, 5min TTL)│  │
│  │  RegimeSignal cache       (dict, 30s TTL)                  │  │
│  │  ActiveStrategySet        (dict, updated per cycle)        │  │
│  │  OpportunityList          (list, updated 30s)             │  │
│  │  KillSwitchState          (atomic bool)                    │  │
│  │  OpenPositions            (dict, real-time updated)        │  │
│  │  BeliefStore              (dict, updated per learning event)│  │
│  └───────────────────────────────────────────────────────────┘  │
│  Lifetime: Process lifetime  Durability: None (lost on restart)  │
│                                                                   │
│  Tier 1 — Persistent Flat File (CSV)                             │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  data/paper_trades.csv    Append-only trade journal        │  │
│  └───────────────────────────────────────────────────────────┘  │
│  Lifetime: Permanent  Durability: Filesystem  Mode: Append-only  │
│                                                                   │
│  Tier 2 — Embedded Relational Database (SQLite)                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  data/trading_brain.db                                     │  │
│  │    table: telemetry      Layer timing records              │  │
│  │    table: decisions      Decision records + reasoning      │  │
│  │    table: learning       Learning events + lessons         │  │
│  │    table: performance    Strategy performance history      │  │
│  │    table: regimes        Regime classification history     │  │
│  │    table: audit_log      All stage transition records      │  │
│  │    table: events         EventBus event log               │  │
│  └───────────────────────────────────────────────────────────┘  │
│  Lifetime: Permanent  Durability: WAL mode  Mode: Append-only    │
│                                                                   │
│  Tier 3 — JSON Files (Strategy Genomes)                          │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  strategy_lab/evolved_strategies/*.json                    │  │
│  │  Each file: one promoted strategy genome                   │  │
│  └───────────────────────────────────────────────────────────┘  │
│  Lifetime: Permanent  Durability: Filesystem  Mode: Write-once   │
│                                                                   │
│  Tier 4 — External Cloud Storage (Broker / Market Data)          │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Dhan API: real-time quotes, order state                   │  │
│  │  yfinance: historical OHLCV, fundamentals                  │  │
│  └───────────────────────────────────────────────────────────┘  │
│  Lifetime: Per-request  Durability: None (external)  Mode: Read  │
└─────────────────────────────────────────────────────────────────┘
```

---

### 7.2 Data Category Storage Matrix

| Data Category | Storage Tier | Mutability | Owner Module | Retention | Constitutional Basis |
|---|---|---|---|---|---|
| Global market snapshot | Tier 0 (dict cache) | Replaced on TTL expiry | `global_data_ai` | 5 minutes | Performance |
| Current market regime | Tier 0 + SQLite audit | Replaced per scan; history immutable | `market_monitor` | Tier 0: 30s; SQLite: permanent | INV-17 |
| Strategy weights | Tier 0 (dict) | Replaced on regime transition | `meta_learning_engine` | Process lifetime | Performance |
| Open position state | Tier 0 (dict) | Updated on fill and close | `order_manager` | Process lifetime; recovered from CSV on restart | Availability |
| Kill-switch state | Tier 0 (atomic) | Set by guardian; cleared by Human Principal | `risk_guardian` | Process lifetime | Safety |
| Decision records | SQLite (append) | Immutable after creation | `decision_engine` | Permanent | INV-17, INV-21 |
| Order records | SQLite + CSV | Immutable after creation | `order_manager` | Permanent | INV-17, INV-20 |
| Fill records | SQLite + CSV | Immutable after creation | `order_manager` | Permanent | INV-17, INV-20 |
| Learning events | SQLite (append) | Immutable after creation | `learning_engine` | Permanent | INV-17, INV-13 |
| Strategy performance | SQLite (append) | New record per update; history immutable | `strategy_performance_tracker` | Permanent | INV-17 |
| Regime history | SQLite (append) | Immutable after creation | `market_monitor` | Permanent | INV-17 |
| Audit log | SQLite (append) | Immutable after creation | `system_monitor` | Permanent | INV-57, INV-17 |
| Layer telemetry | SQLite (append) | Immutable after creation | `system_monitor` | 90 days rolling | Operational |
| Evolved strategies | JSON files (Tier 3) | Write-once per promotion | `validation_pipeline` | Permanent | Protected module |
| Belief store | Tier 0 (dict) | Updated per learning event; rate-limited | `learning_engine` | Process lifetime; not persisted | Learning |

---

### 7.3 Data Lifecycle Diagram

```
MARKET DATA (External — Tier 4)
    │
    │ fetch (every cycle or 30s scan)
    ▼
TIER 0 — In-process cache (seconds to minutes TTL)
    │
    │ cognitive cycle processes data
    ▼
DECISION RECORDS (SQLite — Tier 2, permanent, append-only)
    │
    │ order placed
    ▼
ORDER + FILL RECORDS (SQLite + CSV — Tier 1+2, permanent, append-only)
    │
    │ position closed
    ▼
OUTCOME RECORDS (derived from FillRecord + closeRecord)
    │
    │ learning triggered (< 15min after close)
    ▼
LEARNING EVENTS (SQLite — Tier 2, permanent, append-only)
    │
    │ lesson extracted
    ▼
BELIEF STORE UPDATE (Tier 0 — in-memory, rate-limited)
    │
    │ weekly evolution run
    ▼
EVOLVED STRATEGY CANDIDATES (Tier 0 during evolution)
    │
    │ validation pipeline passes (6 stages)
    ▼
PROMOTED STRATEGY (JSON file — Tier 3, write-once)
    │
    │ loaded into ActiveStrategySet
    ▼
TIER 0 — In-process active strategy set
```

---

### 7.4 Immutability Implementation Strategy

The IIOS constitutional requirement (INV-17) that historical records are never modified is implemented through engineering discipline at three levels:

| Level | Mechanism | Scope | Verification |
|---|---|---|---|
| **Storage level** | SQLite tables have no UPDATE or DELETE grants in the application's connection; CSV files are opened in append mode only | All historical tables | Storage layer audit |
| **Application level** | No module has an update or delete function for historical records; only create functions exist | All modules | Code review + static analysis |
| **Verification level** | Knowledge Integrity Verifier recomputes hash of all records daily; any mismatch triggers a critical alert | All SQLite records | Daily automated check |

Hash verification process:
```
At record creation:
    record_hash = SHA256(record_content + record_timestamp + record_id)
    store: record_content, record_hash, record_timestamp

Daily at 19:30:
    for each record in historical tables:
        computed_hash = SHA256(record.content + record.timestamp + record.id)
        if computed_hash != record.stored_hash:
            CRITICAL ALERT: record integrity violation
            escalate to Human Principal
```

---

### 7.5 Data Recovery Strategy

When the Trading Engine restarts after a crash or planned shutdown, the following recovery sequence ensures state consistency:

| Recovery Step | What Is Recovered | How | Time Required |
|---|---|---|---|
| 1. Open positions | Read today's paper_trades.csv; identify opened-but-not-closed positions | CSV read on startup | < 1s |
| 2. Strategy performance | Query SQLite for today's closed trades; rebuild win rates | SQLite query on startup | < 2s |
| 3. Learning backlog | Check for LearningTrigger events without corresponding LearningEvent; process in order | SQLite query + learning pipeline | < 5min |
| 4. Regime state | Query last RegimeSignal from SQLite; use as starting regime | SQLite query | < 1s |
| 5. Kill-switch state | Assume INACTIVE on fresh start (safe default); fresh market data determines | Default | Immediate |
| 6. Feed connections | Data feed manager establishes fresh connections to Dhan + yfinance | Network connection | < 5s |

The `_do_eod_learning` method in `master_orchestrator` implements steps 1–2 specifically for the EOD restart case, recovering from CSV-closed trades to handle post-restart zero-count scenarios.

---

## PART VIII — IMPLEMENTATION ROADMAP

### 8.0 Overview

The implementation roadmap defines the phased approach to building the complete AI Trading Brain. The roadmap is sequenced by dependency: later phases depend on the stability of earlier phases. Each phase has defined entry criteria, milestone deliverables, and exit criteria.

---

### 8.1 Phase Overview

| Phase | Name | Duration | Primary Goal | Deployment State |
|---|---|---|---|---|
| Phase I | Foundation and Safety | Months 1–3 | Core orchestration, data feeds, risk controls, paper trading | Paper trading — VPS deployed |
| Phase II | Intelligence and Learning | Months 4–9 | Full cognitive cycle, debate, learning, evolution | Paper trading — full cycle active |
| Phase III | Optimisation and Validation | Months 10–18 | Strategy optimisation, constitutional compliance, maturity Level 4 | Paper trading — validated performance |
| Phase IV | Live Capital Transition | Month 19+ | Constitutional amendment for live trading; broker integration | Live trading — requires Human Principal approval |

---

### 8.2 Phase I — Foundation and Safety (Months 1–3)

**Goal:** Establish the infrastructure that all subsequent phases depend on. Specifically: orchestration, data feeds, risk controls, trade monitoring, and paper trade journaling.

**Entry Criteria:**
- VPS provisioned and accessible
- Docker Compose operational
- Python 3.14 environment confirmed
- Dhan credentials obtained (even if data API blocked)
- Telegram bot created and token available

**Phase I Milestones:**

| Milestone | Deliverable | Acceptance Criteria | Dependencies |
|---|---|---|---|
| I-1 | Data feed operational | `data_feed_manager` routes to yfinance; returns valid TickerQuote for 10 symbols | None |
| I-2 | Orchestrator running | `master_orchestrator` completes a cycle with all 17 layers stubbed | I-1 |
| I-3 | Risk guardian active | Kill-switch activates within 100ms when triggered in test | I-2 |
| I-4 | Paper trade journaling | Order placed in paper mode; record appears in `paper_trades.csv` with correct fields | I-3 |
| I-5 | Position monitoring | `trade_monitor` detects stop-loss hit within 5s and logs PositionAlert | I-4 |
| I-6 | Telegram operational | `/status`, `/positions`, `/pnl` commands return correct responses | I-5 |
| I-7 | System monitor baseline | Layer timing recorded for all 17 layers; no CRIT violations in normal operation | I-6 |
| I-8 | VPS deployment healthy | Both containers show healthy in `docker compose ps` for 24 hours | I-7 |

**Phase I Exit Criteria:**
- All Phase I milestones achieved
- 48-hour continuous run without constitutional violations
- Kill-switch test passed at least 3 times
- Human Principal has reviewed and approved paper trading state

---

### 8.3 Phase II — Intelligence and Learning (Months 4–9)

**Goal:** Activate the full cognitive cycle with real intelligence: regime detection, opportunity scanning, strategy management, debate, decision, and learning.

**Entry Criteria:**
- Phase I complete and stable (48+ hours healthy)
- At least 10 candidate strategies in `evolved_strategies/`
- Human Principal has reviewed and understood Phase I operation

**Phase II Milestones:**

| Milestone | Deliverable | Acceptance Criteria | Dependencies |
|---|---|---|---|
| II-1 | Regime detection | `market_monitor` correctly identifies regime with confidence > 0.70 across 5 test days | Phase I complete |
| II-2 | Opportunity scanning | `equity_scanner` produces non-empty OpportunityList for 200+ symbols every 30s | II-1 |
| II-3 | Strategy management | `meta_strategy_controller` activates and deactivates strategies based on regime weights | II-2 |
| II-4 | Full debate cycle | All 5 debate agents vote on a test hypothesis; DebateRecord created with all 5 votes | II-3 |
| II-5 | Decision pipeline | End-to-end: Hypothesis → Debate → Decision → Order in < 200ms | II-4 |
| II-6 | Learning pipeline | Position close triggers learning event within 15 minutes; LearningRecord in SQLite | II-5 |
| II-7 | Strategy performance tracking | Win rates correctly computed after 20+ paper trades per strategy | II-6 |
| II-8 | Auto-disable working | Strategy with win rate < 40% over 20+ trades is disabled automatically | II-7 |
| II-9 | kNN predictor active | kNN produces strategy weights when >= 20 regime instances recorded | II-8 |
| II-10 | First evolution run | `strategy_evolution_agent` completes weekly run; at least 1 candidate submitted to validation | II-9 |
| II-11 | Validation pipeline | Evolved candidate passes or fails all 6 validation stages with documented result | II-10 |

**Phase II Exit Criteria:**
- All Phase II milestones achieved
- 30 days of continuous paper trading with full cognitive cycle
- Win rate >= 50% across all active strategies (minimum 30 trades per strategy)
- No constitutional violations in 30-day audit window
- Human Principal satisfied with intelligence quality

---

### 8.4 Phase III — Optimisation and Validation (Months 10–18)

**Goal:** Achieve IIOS maturity Level 4 (Adaptive Intelligence). Optimise strategy performance, validate constitutional compliance, and build institutional memory depth.

**Entry Criteria:**
- Phase II complete
- 30+ days of documented learning events
- 50+ trades per active strategy
- Architecture maturity assessment: Level 3 confirmed

**Phase III Milestones:**

| Milestone | Deliverable | Acceptance Criteria | Dependencies |
|---|---|---|---|
| III-1 | Sharpe ratio >= 0.8 | Rolling 90-day Sharpe across paper portfolio >= 0.8 | Phase II complete |
| III-2 | Max drawdown < 10% | No rolling 30-day drawdown exceeds 10% for 60 consecutive days | III-1 |
| III-3 | Win rate >= 55% | Portfolio-level win rate >= 55% over 90 days | III-2 |
| III-4 | Constitutional compliance | Weekly compliance report shows 60/60 invariants for 4 consecutive weeks | III-3 |
| III-5 | Memory depth >= 500 records | Analogue database contains >= 500 fully attributed learning records | III-4 |
| III-6 | kNN quality >= 0.7 | Correlation(kNN prediction, actual strategy win rate) >= 0.7 | III-5 |
| III-7 | Regime coverage | Intelligence has operated through at least 3 distinct market regimes | III-6 |
| III-8 | Architecture maturity L4 | All maturity Level 4 indicators met per IIOS Supplement IV | III-7 |

**Phase III Exit Criteria:**
- All Phase III milestones achieved
- Human Principal has reviewed 90-day performance attribution
- Architecture Council has reviewed constitutional compliance
- Human Principal has approved constitutional amendment proposal for Phase IV

---

### 8.5 Phase IV — Live Capital Transition (Month 19+)

**Goal:** Transition from paper trading to live capital under constitutional amendment PROP-001. This phase requires a constitutional amendment and explicit Human Principal approval.

**Prerequisites (non-negotiable):**
- Constitutional amendment PROP-001 ratified (new invariants INV-61+; expanded risk governance)
- Phase III all milestones complete and documented
- Live broker integration tested in isolation (no live orders until Human Principal approves)
- Kill-switch tested with live connection (not just paper)
- Insurance / risk of ruin analysis completed by Human Principal

**Phase IV Milestones:**

| Milestone | Deliverable | Acceptance Criteria | Dependencies |
|---|---|---|---|
| IV-1 | Broker integration tested | Live broker connection established; test order cancelled immediately | Constitutional amendment ratified |
| IV-2 | Dual-mode running | System runs paper and live simultaneously; paper results match live for 1 week | IV-1 |
| IV-3 | First live trade | Human Principal approves first live trade manually; executed correctly | IV-2 |
| IV-4 | Automated live trading | System operates autonomously within constitutional bounds for 30 days | IV-3 |

---

### 8.6 Implementation Dependency Graph

```
[I-1 Data Feed]
    └─► [I-2 Orchestrator]
            └─► [I-3 Risk Guardian]
                    └─► [I-4 Paper Trading]
                            └─► [I-5 Monitoring]
                                    └─► [I-6 Telegram]
                                            └─► [I-7 System Monitor]
                                                    └─► [I-8 VPS Deploy]
                                                            │
                                                    Phase I Complete
                                                            │
                                        ┌───────────────────┘
                                        │
                                [II-1 Regime Detection]
                                    └─► [II-2 Scanning]
                                            └─► [II-3 Strategy Mgmt]
                                                    └─► [II-4 Debate]
                                                            └─► [II-5 Decision]
                                                                    └─► [II-6 Learning]
                                                                            └─► [II-7 Perf Track]
                                                                                    └─► [II-8 Auto-disable]
                                                                                            └─► [II-9 kNN]
                                                                                                    └─► [II-10 Evolution]
                                                                                                            └─► [II-11 Validation]
                                                                                                                    │
                                                                                                            Phase II Complete
                                                                                                                    │
                                                                                                    ┌───────────────┘
                                                                                                    │
                                                                                            Phase III → Phase IV
```

---

## PART IX — ENGINEERING CONSTITUTION

### 9.0 Overview

The Engineering Constitution defines the inviolable rules of software engineering for the AI Trading Brain. These rules are derived from the IIOS constitutional articles and invariants but are stated in engineering terms. They apply to every module, every commit, and every deployment.

The Engineering Constitution does not duplicate the IIOS constitution — it translates it. Where the IIOS says "every output must include a human-readable reasoning chain," the Engineering Constitution says "every function that produces an output object must populate the `explanation` field before returning."

---

### 9.1 Engineering Invariants — Complete List

**Category A — Code Correctness**

| ENG-INV-01 | **No Silent Exceptions** | Every exception that occurs in any module must be caught, logged to the system monitor, and either recovered or escalated. No exception may be silently swallowed. | Constitutional basis: INV-59, Article I-061 |
|---|---|---|---|

| ENG-INV-02 | **Type Safety at Module Boundaries** | Every value passed across a module boundary must be validated for type correctness before being consumed. A module may not assume it received the correct type. | Constitutional basis: INV-15 (Validation Before Consumption) |
|---|---|---|---|

| ENG-INV-03 | **Constant Scope Discipline** | Class-level constants must always be accessed as `self.CONSTANT_NAME` within instance methods. Module-level constants are accessed by bare name. The two must never be confused. | Engineering basis: user memory patterns.md (known crash pattern) |
|---|---|---|---|

| ENG-INV-04 | **No Shared Mutable State Without Lock** | Any data structure accessed by more than one thread must be protected by a threading.Lock or equivalent mechanism. Unprotected shared state is a correctness violation. | Constitutional basis: INV-22 (Temporal Integrity) |
|---|---|---|---|

| ENG-INV-05 | **No Magic Numbers** | All numeric constants that have business meaning must be named constants in `config.py` or in a named constant block at module level. No unexplained literal numbers in logic paths. | Constitutional basis: Explainability, Article I-056 |
|---|---|---|---|

**Category B — Safety Engineering**

| ENG-INV-06 | **Kill-Switch Path Is Synchronous** | The code path from kill-switch trigger detection to kill-switch activation must be fully synchronous. No async call, no thread join, no I/O may be placed in this path. | Constitutional basis: INV-24, Article I-050 |
|---|---|---|---|

| ENG-INV-07 | **Fail-Safe Default for All Risk Paths** | When any component involved in risk approval (`risk_manager_ai`, `risk_guardian`) raises an exception or times out, the default outcome must be REJECTED/BLOCKED. Never default to APPROVED. | Constitutional basis: INV-54 (Fail-Safe Default) |
|---|---|---|---|

| ENG-INV-08 | **Position Size Cannot Exceed Config Constant** | No code path may submit an order for a position size greater than `MAX_POSITION_PCT * portfolio_value`. This check must occur in `order_manager` as a final gate, independent of upstream approval. | Constitutional basis: INV-25 (Position Limit Supremacy) |
|---|---|---|---|

| ENG-INV-09 | **Paper Trading Flag Is Checked at Execution** | The `PAPER_TRADING` constant from `config.py` must be explicitly checked in `order_manager.submit()` before any broker call. No upstream component may bypass this check. | Constitutional basis: ED-003, operational safety |
|---|---|---|---|

| ENG-INV-10 | **Kill-Switch State Is Atomic** | The kill-switch active/inactive state must be stored in a thread-safe atomic variable (threading.Event or equivalent). Read and write operations must not require separate locking. | Constitutional basis: INV-24, performance |
|---|---|---|---|

**Category C — Auditability Engineering**

| ENG-INV-11 | **Decision Record Before Order Submission** | The `DecisionRecord` must be written to the audit store before `order_manager.submit()` is called. An order without a prior decision record is a constitutional violation. | Constitutional basis: INV-14 (Approval Before Execution) |
|---|---|---|---|

| ENG-INV-12 | **All Trade Events Written Before Returning** | Any function that creates, modifies (fills), or closes a trade record must write the event to the persistent store before returning. In-memory-only trade records are prohibited. | Constitutional basis: INV-20 (Outcome Recording) |
|---|---|---|---|

| ENG-INV-13 | **Audit Log Is Append-Only** | No module may open the audit log with write mode that allows overwriting existing content. All writes to the audit log are append operations. | Constitutional basis: INV-17 (Historical Immutability) |
|---|---|---|---|

| ENG-INV-14 | **Timestamp Sources Are Consistent** | All timestamps must come from a single authoritative source (system clock in UTC). No module may compute a timestamp from another module's timestamp. | Constitutional basis: INV-22 (Temporal Integrity) |
|---|---|---|---|

| ENG-INV-15 | **Reasoning Chain Is Populated Before Return** | Any function that returns an output object with an `explanation` or `reasoning_chain` field must populate that field before returning. Returning with an empty explanation field is a contract violation. | Constitutional basis: INV-39 (No Black-Box Outputs) |
|---|---|---|---|

**Category D — Reliability Engineering**

| ENG-INV-16 | **Background Threads Must Have Heartbeat** | Every background thread must write a heartbeat timestamp to the system monitor at least once per its defined monitoring cycle. Threads that miss two heartbeats trigger a Level 3 alert. | Constitutional basis: INV-55 (Monitoring Continuity) |
|---|---|---|---|

| ENG-INV-17 | **Feed Fallback Must Be Transparent** | When `data_feed_manager` falls back to yfinance, it must set `SOURCE = yahoo` on all returned data objects. No consumer may unknowingly receive fallback data without the SOURCE field indicating it. | Constitutional basis: INV-56 (Data Feed Redundancy) |
|---|---|---|---|

| ENG-INV-18 | **Queue Depth Bounds Are Enforced** | All thread queues must have a defined maximum depth. When a queue reaches capacity, the oldest item is discarded with a logged warning. Unbounded queues are prohibited. | Constitutional basis: INV-53 (No SPOF) |
|---|---|---|---|

| ENG-INV-19 | **Durable Learning Queue on Restart** | Learning events that have not been processed at the time of a process restart must be queued to disk and processed in order on the next startup. No learning events may be silently lost. | Constitutional basis: INV-13 (Memory Encoding Mandatory) |
|---|---|---|---|

| ENG-INV-20 | **Recovery Sequence Is Defined** | Every module that holds in-memory state derived from persistent storage must have a defined recovery sequence that is executed on startup. The recovery sequence must be tested. | Constitutional basis: INV-58 (Recovery Priority) |
|---|---|---|---|

**Category E — Evolvability Engineering**

| ENG-INV-21 | **No Hard-Coded Module Imports in Tests** | Test files must not import from modules more than one layer below them in the dependency hierarchy. Tests use mocking or interface fakes to isolate the module under test. | Constitutional basis: INV-45 (Additive Evolution) |
|---|---|---|---|

| ENG-INV-22 | **Interface Contracts Are Documented** | Every module boundary interface must have a documented contract: input type, output type, timing guarantee, and failure behaviour. Undocumented interfaces are not complete. | Constitutional basis: INV-51 (Interface Stability) |
|---|---|---|---|

| ENG-INV-23 | **No Removal Without Amendment** | Any removal of a public function, class, or constant from a module requires Architecture Council review and documentation as a MINOR or MAJOR version change. | Constitutional basis: INV-45 (Additive Evolution Only) |
|---|---|---|---|

| ENG-INV-24 | **Protected Module Changes Require Explicit Instruction** | Changes to protected modules (`risk_guardian`, `backtesting_ai`, `validation_engine/`, `dhan_feed`) require explicit written instruction from the Human Principal before any modification. | Constitutional basis: Protected Module Policy |
|---|---|---|---|

| ENG-INV-25 | **Config Changes Are Reviewed** | Any change to `config.py` that modifies a risk threshold, conviction threshold, or promotion gate requires Architecture Council review before commit. | Constitutional basis: INV-48 (Constitutional Amendment Process) |
|---|---|---|---|

**Category F — Observability Engineering**

| ENG-INV-26 | **Every Layer Is Timed** | Every layer execution in the cognitive cycle must be wrapped in `system_monitor.time_layer(layer_name)`. No layer may execute without timing. | Constitutional basis: IIOS Supplement I |
|---|---|---|---|

| ENG-INV-27 | **WARN and CRIT Thresholds Are Respected** | When a layer exceeds its WARN threshold, a log warning is emitted and a LAYER_EXCEEDED_WARN event is posted to EventBus. When CRIT is exceeded, the event is LAYER_EXCEEDED_CRIT and the cycle may be aborted. | Constitutional basis: System Monitor specification |
|---|---|---|---|

| ENG-INV-28 | **All Decision Inputs Are Logged** | Before a decision is formed, all inputs to the decision (hypothesis, conviction, debate votes, risk approval, size recommendation) must be logged to SQLite. Partial decision records are a violation. | Constitutional basis: INV-21 (Decision Record Completeness) |
|---|---|---|---|

| ENG-INV-29 | **Telegram Commands Have Authenticated Origin** | Every command received via Telegram must be verified as originating from the registered Human Principal chat ID before execution. Unverified commands are rejected and logged. | Constitutional basis: Article I-049 (Human Authority Is Preserved) |
|---|---|---|---|

| ENG-INV-30 | **System Health Report Is Generated Daily** | A system health report covering all 15 layer health metrics, all 60 invariant compliance checks, and all open alerts must be generated by 20:00 IST every trading day. | Constitutional basis: Article I-060 (Constitutional Compliance Is Reported) |
|---|---|---|---|

---

### 9.2 Engineering Quality Gates

Quality gates are mandatory checkpoints that must pass before any code change is accepted. They are enforced in CI/CD and in the code review process.

| Gate | Trigger | Checks | Failure Action |
|---|---|---|---|
| **Pre-commit lint** | Every commit | Python syntax; import order; no debug statements | Block commit |
| **Unit test gate** | Every commit | All unit tests pass; no regression | Block commit |
| **Integration test gate** | Every pull request | Intelligence plane; execution pipeline; learning pipeline | Block merge |
| **Constitutional test gate** | Every pull request | All 30 engineering invariants; audit trail; kill-switch | Block merge |
| **Interface compatibility gate** | Any interface change | All existing consumers still compile and pass tests | Block merge |
| **Protected module gate** | Any protected module change | Explicit instruction present in commit message or PR | Block merge |
| **Config review gate** | Any config.py change | Architecture Council review comment on PR | Block merge |
| **Deployment health gate** | Every deployment | Both containers healthy for 300 seconds | Roll back deployment |

---

### 9.3 Code Review Checklist

Every code review must verify the following before approving:

**Correctness:**
- [ ] No class-level constants accessed as bare names in instance methods (`self.X` not `X`)
- [ ] No shared mutable state without threading.Lock
- [ ] All exception paths caught and logged
- [ ] No magic numbers — all constants named

**Safety:**
- [ ] No new code path that could bypass risk approval
- [ ] No automated kill-switch deactivation
- [ ] Paper trading flag checked at execution boundary
- [ ] Fail-safe defaults for all risk components

**Auditability:**
- [ ] Decision record created before order submission
- [ ] All trade events written to persistent store before returning
- [ ] No modification to existing records in historical tables
- [ ] All output objects have explanation/reasoning chain populated

**Reliability:**
- [ ] Background threads have heartbeat
- [ ] Queue depths bounded
- [ ] Recovery sequence defined for new stateful components

**Evolvability:**
- [ ] No removal of existing public interfaces
- [ ] Protected module changes have explicit instruction
- [ ] New interfaces have documented contracts

---

### 9.4 Deployment Engineering Standards

| Standard | Requirement | Verification |
|---|---|---|
| Deployment atomicity | All code changes are deployed together; partial deployments are not permitted | Single `git pull + docker compose build + docker compose up` |
| No-cache build | Docker images are always built with `--no-cache` to ensure new Python source is baked in | CI/CD pipeline enforces `--no-cache` |
| Health verification | Deployment is not complete until both containers are healthy for 300 seconds | Automated health check in deploy script |
| Rollback plan | Every deployment has a documented rollback: `git revert + redeploy` | Deployment checklist |
| Data volume preservation | Deployment never touches the `data/` volume mount | `docker compose down` (not `docker compose down -v`) |
| Log retention | Docker logs are retained for 7 days; SQLite telemetry for 90 days | Logrotate / SQLite pruning |
| Zero-downtime restart | Non-critical services (dashboard) can be restarted without impacting trading engine | Container isolation |

---

## PART X — IMPLEMENTATION READINESS CHECKLIST

### 10.0 Overview

The implementation readiness checklist defines what must be true before each implementation phase begins, before each milestone is claimed as complete, and before a live deployment is made. It is a practical tool for the Human Principal and Architecture Council to verify readiness.

---

### 10.1 Phase I Readiness — Foundation and Safety

**Infrastructure Readiness**

| Check | Criteria | Verified By | Date |
|---|---|---|---|
| VPS accessible | SSH connection to root@178.18.252.24 established | Human Principal | |
| Docker installed | `docker --version` returns 24.0+ | Human Principal | |
| Docker Compose installed | `docker compose version` returns 2.0+ | Human Principal | |
| Port 8501 accessible | Dashboard port reachable from browser | Human Principal | |
| Git remote configured | `git remote -v` shows origin pointing to correct repository | Human Principal | |
| Python 3.14 in venv | `.venv/Scripts/python --version` returns 3.14 | CI check | |
| All requirements installable | `pip install -r requirements.txt` completes without errors | CI check | |

**Data Feed Readiness**

| Check | Criteria | Verified By | Date |
|---|---|---|---|
| yfinance returning data | `yahoo_feed.get_quote("RELIANCE.NS")` returns valid TickerQuote | Unit test | |
| Dhan credentials obtained | `DHAN_TOKEN` environment variable set | Human Principal | |
| Feed fallback tested | Simulate Dhan 451; confirm yfinance activated in < 1s | Integration test | |
| Feed timeout respected | yfinance call with bad symbol times out in <= 8s | Integration test | |
| 200+ symbol universe defined | `config.EQUITY_UNIVERSE` contains >= 200 NSE symbols | Config review | |

**Risk and Safety Readiness**

| Check | Criteria | Verified By | Date |
|---|---|---|---|
| Kill-switch activates in < 100ms | Test: trigger kill-switch; measure activation time | Constitutional test | |
| Kill-switch blocks all orders | After activation: `order_manager.submit()` returns BLOCKED | Constitutional test | |
| Paper trading enforced | `PAPER_TRADING = True` in config; no live orders placed in any test | Config review | |
| Daily loss limit enforced | Simulate 2% daily loss; confirm new positions blocked | Constitutional test | |
| Position size limit enforced | Attempt order > MAX_POSITION_PCT; confirm blocked at order_manager | Constitutional test | |
| Telegram authenticated | Non-authorised chat ID command rejected and logged | Integration test | |

**Monitoring Readiness**

| Check | Criteria | Verified By | Date |
|---|---|---|---|
| All 17 layers timed | Every layer in orchestrator wrapped in `time_layer()` | Code review | |
| WARN/CRIT thresholds active | Simulate layer exceeding CRIT; confirm EventBus event fired | Integration test | |
| Monitoring thread isolated | Blocking main thread does not block trade_monitor | Thread isolation test | |
| Heartbeat verified | trade_monitor heartbeat detected every 5s; alert on 2 missed | Integration test | |
| Paper trades journaled | Completed paper trade appears in paper_trades.csv with all required fields | Integration test | |

---

### 10.2 Phase II Readiness — Intelligence and Learning

**Intelligence Plane Readiness**

| Check | Criteria | Verified By | Date |
|---|---|---|---|
| Regime detection calibrated | Regime correctly identified for 5 consecutive days vs manual observation | Regime validation | |
| Opportunity scanner operational | Scanner produces non-empty OpportunityList for 200+ symbols every 30s | Integration test | |
| 10+ evolved strategies loaded | `evolved_strategies/` directory contains >= 10 valid strategy JSON files | Directory check | |
| MetaStrategyController active | Strategies activated/deactivated based on regime; logged correctly | Integration test | |
| Strategy hypothesis generated | At least 1 hypothesis per cycle with conviction >= 6.5 on active trading days | Cycle log review | |

**Debate and Decision Readiness**

| Check | Criteria | Verified By | Date |
|---|---|---|---|
| All 5 debate agents voting | DebateRecord shows votes from Bull, Bear, Risk, Temporal, DevilsAdvocate | Constitutional test | |
| Debate completes in < 30s | 100 debate cycles timed; P99 < 30s | Performance test | |
| Decision record complete | All required fields populated in DecisionRecord before order submitted | Constitutional test | |
| Conviction threshold enforced | Hypotheses with conviction < 6.5 do not reach debate | Unit test | |
| Risk approval precedes execution | Audit log confirms RiskApprovalRecord timestamp < OrderRecord timestamp | Audit test | |

**Learning Pipeline Readiness**

| Check | Criteria | Verified By | Date |
|---|---|---|---|
| Learning triggered on position close | LearningTrigger event detected within 1s of position close | Integration test | |
| Attribution complete | LearningRecord contains attribution to: strategy, hypothesis, evidence, decision, execution | Constitutional test | |
| OOS validation gate active | In-sample lessons held until OOS validation; INV-33 enforced | Constitutional test | |
| Anti-catastrophic-forgetting active | Single new data point cannot overwrite established belief; INV-34 enforced | Constitutional test | |
| Learning events durable | Simulate restart mid-learning; confirm events processed on restart | Durability test | |

---

### 10.3 Phase III Readiness — Optimisation and Validation

**Performance Readiness**

| Check | Criteria | Verified By | Date |
|---|---|---|---|
| Sharpe ratio tracked | Rolling 90-day Sharpe computed correctly from paper_trades.csv | Analytics review | |
| Drawdown tracked | Daily/weekly/max drawdown computed and logged | Analytics review | |
| Win rate by strategy correct | Win rates match manual count from paper_trades.csv | Reconciliation | |
| Performance attribution report | Weekly attribution report generated covering all required dimensions | Report review | |
| kNN predictor quality >= 0.7 | Correlation(kNN weight, actual win rate) computed and meets threshold | Model quality review | |

**Constitutional Compliance Readiness**

| Check | Criteria | Verified By | Date |
|---|---|---|---|
| All 60 invariants testable | Constitutional test suite covers all 60 INV references | Test coverage audit | |
| Weekly compliance report generated | Report covers 60/60 invariants; produced by 19:30 IST Friday | Report audit | |
| Audit trail complete | Zero cycle audit trail gaps in 30-day period | Audit completeness check | |
| Knowledge integrity verifier running | Daily hash check running at 20:00; no violations in 30 days | Verifier log review | |
| Override log complete | 100% of overrides documented within 4 hours | Override audit | |

**Institutional Memory Readiness**

| Check | Criteria | Verified By | Date |
|---|---|---|---|
| Memory depth >= 500 records | LearningRecord count in SQLite >= 500 | Database query | |
| Analogue retrieval quality >= 0.8 | Relevant analogues / total retrieved >= 0.8 | Quality spot-check | |
| Regime coverage >= 3 | At least 3 distinct regimes experienced and recorded | Regime history review | |
| Walk-forward tests passing | All active strategies have WFT Sharpe > 0.8 on OOS data | WFT report | |

---

### 10.4 Phase IV Readiness — Live Capital Transition

**Constitutional Readiness**

| Check | Criteria | Verified By | Date |
|---|---|---|---|
| Amendment PROP-001 ratified | Full amendment process completed; IIOS version incremented to 3.0.0 | Amendment register | |
| New invariants (INV-61+) in test suite | Constitutional test suite updated for all new invariants | Test coverage audit | |
| Human Principal written approval | Dated, signed approval document for live trading | Human Principal | |

**Broker Integration Readiness**

| Check | Criteria | Verified By | Date |
|---|---|---|---|
| Dhan live connection established | Token refreshed; connection confirmed (not 451) | Connection test | |
| Test order placed and cancelled | Single test order placed and immediately cancelled in broker | Broker integration test | |
| Order fill confirmed | Fill record matches broker confirmation within acceptable tolerance | Reconciliation | |
| Kill-switch tested with live connection | Kill-switch activation cancels all pending live orders | Live kill-switch test | |
| Risk limits set for live capital | DAILY_LOSS_LIMIT, MAX_POSITION_PCT set for live capital amount | Human Principal review | |

**Dual-Mode Validation**

| Check | Criteria | Verified By | Date |
|---|---|---|---|
| Paper results match live for 5 days | Same decisions produce same results in both modes | Reconciliation | |
| PnL attribution correct in live mode | Live PnL tracked correctly against portfolio value | Attribution check | |
| Telegram commands work in live mode | All 13 commands return correct state in live mode | Integration test | |
| Emergency procedures verified | `/kill` command halts all live orders in < 100ms | Emergency drill | |

---

### 10.5 Per-Module Readiness Matrix

The following matrix defines the readiness state of each module across the four implementation phases. A module is ready when all its required checks pass.

| Module | Phase I Ready | Phase II Ready | Phase III Ready | Phase IV Ready |
|---|---|---|---|---|
| `master_orchestrator` | Stubs all layers | Full 17-layer sequence | Optimised scheduling | Live capital aware |
| `global_data_ai` | yfinance only; cache working | Background pre-warm active | Cache tuned for latency | Live data confirmed |
| `market_monitor` | Basic regime detection | 30s scan + 6 deep-scan | Regime accuracy >= 0.85 | N/A |
| `knn_strategy_predictor` | Stubbed (equal weights) | Active with >= 20 instances | Quality >= 0.7 | N/A |
| `equity_scanner` | 50 symbols | 200+ symbols | 200+ with quality filtering | N/A |
| `meta_strategy_controller` | Basic activation | Regime-weighted activation | Auto-disable + kNN | N/A |
| `position_sizer` | Fixed 1% size | Quarter-Kelly active | Regime-adjusted sizes | Live capital sizing |
| `risk_manager_ai` | Basic approval | Full limit checks | All INV-23–31 tested | Live capital limits |
| `risk_guardian` | Kill-switch active | VIX + DD triggers | All thresholds calibrated | Live capital thresholds |
| `debate_engine` | Stubbed 5 agents | All agents active | Debate quality >= 0.80 | N/A |
| `decision_engine` | Basic aggregate | Full conviction gate | Calibration >= 0.80 | N/A |
| `order_manager` | Paper only; CSV working | Full paper journal | Audit trail complete | Live broker routing |
| `trade_monitor` | 5s polling active | Stop/target enforcement | All monitoring metrics | Live position monitoring |
| `learning_engine` | Basic attribution | Full lesson extraction | OOS validation active | N/A |
| `strategy_performance_tracker` | Win rate tracking | Auto-disable active | kNN feeding | N/A |
| `drawdown_analyzer` | Daily drawdown | Full analytics suite | 90-day rolling metrics | Live portfolio metrics |
| `walk_forward_tester` | Basic WFT | Full 6-stage pipeline | Quality threshold met | N/A |
| `strategy_evolution_agent` | Inactive | Weekly run active | Promotion gate calibrated | N/A |
| `validation_pipeline` | Inactive | 6-stage active | Gate thresholds validated | N/A |
| `data_feed_manager` | yfinance working | Fallback active | Latency optimised | Dhan live confirmed |
| `telegram_bot` | Status + positions | All 13 commands | All commands tested | Live alerts |
| `system_monitor` | Basic timing | Full EventBus | All events covered | N/A |

---

### 10.6 Final Deployment Checklist

This checklist is executed before every deployment to production.

**Code Quality**
- [ ] All modified files pass linting (zero syntax errors)
- [ ] All modified files pass type annotation checks
- [ ] No new class-level constant scope bugs (`self.X` not `X`)
- [ ] No forward references to undefined symbols
- [ ] All exceptions caught and logged (no bare `except: pass`)

**Interface Preservation**
- [ ] All existing public method signatures unchanged
- [ ] All existing class names unchanged
- [ ] All existing return types preserved
- [ ] No existing import paths broken
- [ ] `BaseFeed.get_quote()`, `BaseFeed.get_history()`, `GlobalDataAI.fetch()`, `SystemMonitor.time_layer()`, `MasterOrchestrator.run_full_cycle()` signatures all intact

**Constitutional Compliance**
- [ ] All 30 engineering invariants reviewed against the change
- [ ] Change is additive (nothing removed)
- [ ] No constitutional principles violated
- [ ] Protected module changes have explicit instruction documented

**Testing**
- [ ] All unit tests pass for modified modules
- [ ] All integration tests pass
- [ ] Constitutional compliance tests pass (60 invariant checks)
- [ ] Kill-switch test passes

**Documentation**
- [ ] `Files Modified` table in `copilot-instructions.md` updated
- [ ] Engineering Blueprint updated if new module or interface added
- [ ] IIOS updated if new architectural component added

**Deployment Execution**
- [ ] `git add <files>` — all modified files staged
- [ ] `git commit -m "<descriptive message>"` — commit message explains WHY
- [ ] `git push origin main` — pushed to remote
- [ ] VPS deploy command executed in full:
      `ssh -i ~/.ssh/trading_vps root@178.18.252.24 "cd /root/ai-trading-brain && git pull origin main && docker compose build --no-cache && docker compose down && docker compose up -d && sleep 8 && docker compose ps"`
- [ ] Both containers show `Up N seconds (healthy)` in output
- [ ] First full cycle verified in `docker logs ai-trading-brain`
- [ ] No constitutional violations in first 10 cycles

**Definition of Done**
A deployment is complete ONLY when:
1. Both containers healthy
2. At least one full cognitive cycle completed successfully after deployment
3. No exceptions in the new code paths for 10 cycles
4. Human Principal notified via Telegram with post-deploy summary

---

## ENGINEERING BLUEPRINT FOOTER

### Summary Metrics

| Metric | Count |
|---|---|
| Engineering Parts | 10 (Parts I–X) |
| Engineering Supplements | 12 (Supplements A–L) |
| Engineering Invariants | 30 (ENG-INV-01 to ENG-INV-30) |
| Quality Gates | 8 (QG-01 to QG-08) |
| Implementation Phases | 4 (Phase I–IV) |
| Phase Milestones Total | 30 (8+11+8+4) |
| Module Readiness States | 4 per module (I–IV) |
| Modules Specified | 27 primary modules |
| Service Catalog Entries | 8 services |
| Communication Sequences | 4 critical sequences |
| Storage Tiers | 5 (Tier 0–4) |
| Data Transfer Objects | 26 (full catalogue) |
| Engineering Decisions Logged | 25 (ED-001 to ED-025) |
| Engineering Anti-Patterns | 10 (all prohibited) |
| Data Flow Records | 40 (DF-001 to DF-040) |
| Thread Registry Entries | 8 (T-001 to T-008) |
| Failure Mode Responses | 21 (FM-01 to FM-21) |
| Constitutional Invariants Traced | 60 (INV-01 to INV-60) |
| Scheduler Slots | 10 (pre-market to weekly) |
| Deployment Checklist Items | 23 |
| Startup Sequence Steps | 14 (S-01 to S-14) |
| Shutdown Sequence Steps | 10 (SD-01 to SD-10) |
| Observability Pillars | 3 (Metrics, Logs, Traces) |
| ASCII Architecture Diagrams | 5 |

### Document History

| Version | Date | Author | Change |
|---|---|---|---|
| 1.0.0 | 2026-07-02 | AI Trading Brain — Engineering Architecture | Initial creation |

### Governing Documents

| Priority | Document | Role |
|---|---|---|
| 1 (Supreme) | INVESTMENT_INTELLIGENCE_OPERATING_SYSTEM.md | Constitutional authority over all |
| 2 | AI_TRADING_BRAIN_ENGINEERING_BLUEPRINT.md | This document — engineering authority |
| 3 | Per-layer architecture documents (Phases 1–9) | Domain-specific architecture |
| 4 | `.github/copilot-instructions.md` | AI assistant operational instructions |

### Architecture Boundary Statement

This document governs HOW the AI Trading Brain is engineered.

It does not govern:
- What the intelligence knows (MASTER_KNOWLEDGE_ARCHITECTURE.md)
- What entities it recognises (ENTITY_ONTOLOGY.md)
- How it reasons (REASONING_ARCHITECTURE.md)
- How it decides (DECISION_ARCHITECTURE.md)
- How it learns (LEARNING_ARCHITECTURE.md)
- How it remembers (MEMORY_ARCHITECTURE.md)
- How it governs itself (INVESTMENT_INTELLIGENCE_OPERATING_SYSTEM.md)

It governs:
- How software modules are structured and bounded
- How modules communicate with each other
- How data is stored and retrieved
- How the system is deployed and operated
- What engineering standards apply to all code
- What must be true before each implementation phase begins
- What constitutes a complete and correct deployment

---

*AI_TRADING_BRAIN_ENGINEERING_BLUEPRINT.md*
*Engineering Architecture — Bridge between Constitution and Implementation*
*Created: 2026-07-02*
*Version: 1.0.0*
*Parent Authority: INVESTMENT_INTELLIGENCE_OPERATING_SYSTEM.md*
*This document governs all engineering decisions for the AI Trading Brain.*

---

## ENGINEERING SUPPLEMENT A — LAYER ENGINEERING SPECIFICATIONS

### A.1 Overview

This supplement provides the complete engineering specification for each of the 17 IIOS operational layers. Each specification covers: the software components that implement the layer, the threading model, the state management approach, the failure recovery strategy, the timing budget allocation, and the constitutional articles the layer directly implements.

---

### A.2 Layer 1 — GlobalIntelligence Engineering Specification

| Attribute | Specification |
|---|---|
| **Primary component** | `GlobalDataAI` class in `global_intelligence/global_data_ai.py` |
| **Entry point** | `GlobalDataAI.fetch(force: bool = False) -> GlobalSnapshot` |
| **Threading model** | Main thread for synchronous fetch; dedicated pre-warm thread activated 30 min before market open |
| **Cache mechanism** | Python dict protected by `threading.Lock`; key = `"global_snapshot"`; value = `(GlobalSnapshot, timestamp)` |
| **Cache TTL** | 5 minutes during market hours; 30 minutes pre-market |
| **Pre-warm trigger** | Scheduler fires at 08:30 IST; background thread fetches and caches |
| **State owned** | `GlobalSnapshot` cache; pre-warm thread reference |
| **State initialised** | At class instantiation (empty cache); pre-warm populates before market open |
| **On cache hit** | Return cached `GlobalSnapshot`; caller receives < 5ms latency |
| **On cache miss** | Fetch from external APIs; update cache; return fresh `GlobalSnapshot`; typical 17ms |
| **On fetch failure** | Return last cached `GlobalSnapshot` with `stale=True` flag; log warning |
| **On cache expired + fetch failure** | Return neutral `GlobalSnapshot` with `stale=True`, `quality_score=0.0` |
| **Timing budget** | WARN: 5,000ms; CRIT: 12,000ms (override in system_monitor.py) |
| **Constitutional articles** | I-001 (Truth First), I-002 (Evidence Precedes Belief), I-015 (Validation Before Consumption) |
| **Governing invariants** | INV-01 (Evidence Primacy), INV-05 (No Certainty Claims), INV-15 (Validation Before Consumption) |
| **Key engineering decision** | ED-010: background pre-warm hides network latency from cognitive cycle |

---

### A.3 Layer 2 — MarketIntelligence Engineering Specification

| Attribute | Specification |
|---|---|
| **Primary components** | `MarketIntelligenceEngine` + `MarketMonitor` in `market_intelligence/` |
| **Entry point** | `MarketIntelligenceEngine.analyse(global_snapshot) -> (RegimeSignal, SectorReport)` |
| **Continuous scan** | `MarketMonitor` runs in a dedicated thread; polls every 30 seconds |
| **Deep-scan slots** | 6 deep-scan slots allocated per session; triggered by significant market moves |
| **Threading model** | `MarketMonitor` = dedicated thread; `MarketIntelligenceEngine` = main thread |
| **State owned** | Current `RegimeSignal`; `SectorReport`; `ScanResult` list |
| **State initialised** | From SQLite last-known regime at startup; updated every 30s thereafter |
| **Regime hysteresis** | New regime confirmed only when confidence >= 0.70 on two consecutive scans |
| **On scan failure** | Return prior `RegimeSignal` with `stale=True`; attempt restart of scan thread |
| **Data source** | `data_feed_manager` for NIFTY/BANKNIFTY price + volume; market breadth data |
| **Timing budget** | WARN: 2,000ms; CRIT: 5,000ms |
| **Constitutional articles** | I-001, I-009 (Contradiction Must Be Declared), I-020 (Outcome Before Lesson) |
| **Governing invariants** | INV-01, INV-04 (Uncertainty Quantification), INV-05 |
| **Index symbol handling** | NIFTY/BANKNIFTY use bare names in `GLOBAL_SYMBOL_MAP`; `.NS` suffix not applied to index symbols |

---

### A.4 Layer 3 — MetaLearning Engineering Specification

| Attribute | Specification |
|---|---|
| **Primary components** | `kNNStrategyPredictor`, `RegimeStrategyMap`, `MetaLearningEngine` in `meta_learning/` |
| **Entry point** | `MetaLearningEngine.get_weights(regime_signal) -> StrategyWeights` |
| **Model type** | k-Nearest Neighbours (k=7) over regime feature vectors |
| **Feature vector** | Regime type (one-hot), confidence, VIX level, market breadth, FII/DII flow direction |
| **Training data** | `RegimeStrategyMap` accumulates (regime_features, strategy_outcomes) pairs |
| **Minimum training data** | 20 regime instances required before kNN produces predictions |
| **Model storage** | In-memory; retrained when `RegimeStrategyMap` receives new data |
| **Singleton enforcement** | `RegimeStrategyMap` accessed only via `get_regime_strategy_map()` |
| **On insufficient data** | Return equal-weight recommendation; log INFO (not a failure) |
| **On model failure** | Return equal-weight recommendation; log WARNING |
| **State owned** | kNN model; `RegimeStrategyMap` records; weight cache |
| **Timing budget** | WARN: 2,000ms; CRIT: 5,000ms |
| **Constitutional articles** | I-006 (Source Reliability Is Relative), I-007 (Multiple Independent Sources), I-032 (Every Cycle Produces Learning) |
| **Governing invariants** | INV-05, INV-34 (Anti-Catastrophic-Forgetting), INV-36 (Recency Balance) |

---

### A.5 Layer 4 — OpportunityEngine Engineering Specification

| Attribute | Specification |
|---|---|
| **Primary components** | `EquityScanner`, `OptionsOpportunityEngine`, `ArbitrageDetector` in `opportunity_engine/` |
| **Entry point** | `EquityScanner.scan(regime_signal) -> OpportunityList` |
| **Symbol universe** | 200+ NSE equity symbols; loaded from `config.EQUITY_UNIVERSE` at startup |
| **Scan frequency** | 30 seconds (driven by `market_monitor` scan cycle) |
| **Signal types** | Momentum breakout, mean-reversion oversold, trend continuation, volatility expansion |
| **Signal ranking** | Opportunities ranked by signal strength; top N passed to MetaStrategyController |
| **Cache** | Prior `OpportunityList` kept in memory; returned with `stale=True` on scan failure |
| **Options scanning** | `OptionsOpportunityEngine` analyses option chains for IV crush, premium capture |
| **Arbitrage detection** | `ArbitrageDetector` looks for index/ETF mispricing opportunities |
| **Threading model** | Main thread for single-cycle scan; scan updates come from `market_monitor` thread |
| **Data source** | `data_feed_manager.get_multiple_quotes()` + `data_feed_manager.get_history()` |
| **Timing budget** | WARN: 2,000ms; CRIT: 5,000ms |
| **Constitutional articles** | I-001, I-003 (Falsifiability Is Mandatory), I-010 (Calibration Is Ongoing) |
| **Governing invariants** | INV-01, INV-15 |

---

### A.6 Layer 5 — StrategyLab Engineering Specification

| Attribute | Specification |
|---|---|
| **Primary components** | `MetaStrategyController`, `StrategyGeneratorAI`, `BacktestingAI` in `strategy_lab/` |
| **Entry point** | `MetaStrategyController.get_hypotheses(opportunities, weights) -> HypothesisList` |
| **Strategy storage** | JSON files in `evolved_strategies/`; loaded at startup; cached in memory |
| **Strategy lifecycle** | Inactive → Active → Performance-tracked → Auto-disabled or Retained |
| **Auto-disable threshold** | Win rate < 40% over 20+ trades |
| **Evolution trigger** | Win rate < 48% over 30+ trades (weaker threshold); triggered on weekly schedule |
| **Hypothesis generation** | `StrategyGeneratorAI` applies strategy template to opportunity; generates hypothesis |
| **min_signal_rr filter** | `_best_evolved_variant` filters by `min_signal_rr`; `_load_evolved_strategies` honours explicit `min_rr` from JSON |
| **Protected status** | `backtesting_ai.py` is protected; no modification without explicit instruction |
| **Strategy attribute access** | `strategy` attribute used in orchestrator, not `strategy_name` (known fix applied) |
| **Timing budget** | WARN: 2,000ms; CRIT: 5,000ms |
| **Constitutional articles** | I-009, I-011 (Process Completeness), I-014 (Risk Before Execution), I-037 (Learning Improves Architecture) |
| **Governing invariants** | INV-32 (Outcome-Based Learning), INV-33 (Anti-Overfitting), INV-45 (Additive Evolution) |

---

### A.7 Layer 6 — CapitalRiskEngine Engineering Specification

| Attribute | Specification |
|---|---|
| **Primary component** | `PositionSizer` in `capital_risk_engine/position_sizer.py` |
| **Entry point** | `PositionSizer.compute(hypothesis, portfolio_state, volatility) -> PositionSizeRecommendation` |
| **Sizing formula** | Quarter-Kelly: `f = 0.25 * (win_rate - (1-win_rate)/rr)` where `rr` = reward-to-risk ratio |
| **Maximum size** | `min(kelly_fraction, config.MAX_POSITION_PCT)` of portfolio value |
| **Uncertainty adjustment** | Size reduced when conviction < 7.0; full size only at conviction >= 8.0 |
| **Regime adjustment** | Sizes modified per regime operating mode (IIOS Supplement VI table) |
| **Portfolio state input** | Current open positions; day P&L; available capital |
| **Volatility input** | ATR (14-period) of the target instrument |
| **On calculation error** | Return minimum safe size (0.5% portfolio); log WARNING |
| **State owned** | None — stateless per-request computation |
| **Timing budget** | WARN: 500ms; CRIT: 2,000ms |
| **Constitutional articles** | I-023 (Risk Has Primacy), I-024 (Kill-Switch Is Inviolable), I-029, I-034 (Uncertainty Reduces Size) |
| **Governing invariants** | INV-23 (Risk Primacy), INV-24 (Kill-Switch Inviolability), INV-25 (Position Limit Supremacy), INV-29 (No Leveraged Betting) |

---

### A.8 Layer 7 — RiskControl Engineering Specification

| Attribute | Specification |
|---|---|
| **Primary components** | `RiskManagerAI`, `PortfolioAllocation`, `StressTestingAgent` in `risk_control/` |
| **Entry point** | `RiskManagerAI.approve(position_size_rec) -> RiskApprovalRecord` |
| **Checks performed** | Daily loss limit; position size limit; portfolio concentration; correlation limit; drawdown halt |
| **Daily loss limit** | 2% of portfolio value (from `config.DAILY_LOSS_LIMIT`) |
| **Approval validity** | 30 seconds; expired approvals cannot be used by order_manager |
| **Default on failure** | REJECTED with reason RISK_UNAVAILABLE — never APPROVED on failure |
| **Stress test integration** | `StressTestingAgent` runs pre-market and on VIX spike; results inform concentration limits |
| **Portfolio allocation** | `PortfolioAllocation` tracks sector/theme/entity concentration; blocks over-concentrated positions |
| **State owned** | Day P&L running total; open position risk contributions; last stress test result |
| **State recovery** | Day P&L recovered from paper_trades.csv on restart; positions recovered from same |
| **Timing budget** | WARN: 500ms; CRIT: 2,000ms (approval path only; stress test is background) |
| **Constitutional articles** | I-023 through I-038 (Risk and Capital chapter) |
| **Governing invariants** | INV-11, INV-23, INV-24, INV-25, INV-26, INV-27, INV-28, INV-29, INV-30, INV-31 |

---

### A.9 Layer 9 — RiskGuardian Engineering Specification

| Attribute | Specification |
|---|---|
| **Primary component** | `RiskGuardianAgent` in `risk_guardian/risk_guardian.py` (PROTECTED) |
| **Threading model** | Dedicated highest-priority monitoring loop; independent of main thread |
| **Poll frequency** | Every 500ms during market hours |
| **Kill conditions** | VIX > 45 (config.KILL_VIX_THRESHOLD) OR DayPnL < -2% (config.DAILY_LOSS_LIMIT) OR any position < -8% |
| **Activation mechanism** | Sets `threading.Event` (atomic) that is checked at order_manager entry gate |
| **Activation latency** | < 100ms from trigger detection to atomic flag set |
| **Deactivation mechanism** | Human Principal only; via authenticated Telegram `/override` command with documentation |
| **Self-health check** | If guardian thread crashes, fail-safe activates kill-switch |
| **State owned** | `kill_switch_active: threading.Event`; trigger history |
| **Protected status** | PROTECTED — explicit Human Principal instruction required for any modification |
| **Constitutional articles** | I-023, I-024 (Kill-Switch Is Inviolable), I-026, I-038, I-050 (Kill-Switch Human Override) |
| **Governing invariants** | INV-11, INV-23, INV-24, INV-27, INV-29, INV-30 |
| **Engineering invariant** | ENG-INV-06 (Kill-Switch Path Is Synchronous); ENG-INV-07 (Fail-Safe Default); ENG-INV-10 (Atomic State) |

---

### A.10 Layer 10 — DebateAndDecision Engineering Specification

| Attribute | Specification |
|---|---|
| **Primary components** | `DebateEngine` + 5 agent modules + `DecisionEngine` in `debate_and_decision/` |
| **Entry point** | `DebateEngine.debate(hypothesis_package) -> DebateRecord` |
| **Agent execution** | Sequential in main thread (agents share process; no inter-process overhead) |
| **Agent types** | BullAgent, BearAgent, RiskAgent, TemporalAgent, DevilsAdvocateAgent |
| **Debate timeout** | Maximum 30 seconds per hypothesis; exceeded → SUSPENDED |
| **Minimum participation** | All 5 agents must vote; any unavailable agent → debate SUSPENDED |
| **Vote scoring** | Each agent votes 1.0–10.0 with reasoning; weighted by agent role |
| **Aggregate threshold** | Weighted average >= 6.5 → proceed to DecisionEngine |
| **Decision validity window** | 30 seconds; `order_manager` checks approval timestamp before submission |
| **Conviction threshold** | 6.5 (from `config.CONVICTION_THRESHOLD`); constitutional — requires amendment to change |
| **Decision record** | Created BEFORE `order_manager.submit()` is called (ENG-INV-11) |
| **State owned** | Hypothesis queue; debate timeout tracker |
| **Timing budget** | WARN: 2,000ms; CRIT: 5,000ms |
| **Constitutional articles** | I-012 (Sequence Is Constitutional), I-013 (Debate Before Decision), I-014, I-017 (Encoding Before Completion) |
| **Governing invariants** | INV-10 (Debate Completeness), INV-13 (Memory Encoding Mandatory), INV-14 (Approval Before Execution) |

---

### A.11 Layer 11 — ExecutionEngine Engineering Specification

| Attribute | Specification |
|---|---|
| **Primary components** | `OrderManager`, broker adapters in `execution_engine/` |
| **Entry point** | `OrderManager.submit(decision_record, risk_approval_record) -> OrderRecord` |
| **PAPER_TRADING check** | `config.PAPER_TRADING` explicitly checked at entry of `submit()`; if True, no broker call |
| **Paper trade journal** | `data/paper_trades.csv` opened in append mode; one row per trade event |
| **CSV columns** | date, time, strategy, instrument, direction, size, entry_price, stop, target, status, exit_price, pnl, decision_record_id |
| **Slippage model** | Paper mode: 0.05% for equity; 0.10% for options; applied to fill price |
| **Kill-switch gate** | `order_manager.submit()` checks `risk_guardian.kill_switch_active` before any submission |
| **Approval validity** | `risk_approval_record.validity_ts` checked; expired approvals rejected (30-second window) |
| **Decision record gate** | `decision_record_id` must exist in SQLite before submission proceeds (ENG-INV-11) |
| **Fill simulation** | In paper mode: instant fill at slippage-adjusted price; FillRecord created |
| **State owned** | Open position registry; daily P&L running total |
| **State recovery** | Positions recovered from paper_trades.csv on startup |
| **Timing budget** | WARN: 2,000ms; CRIT: 5,000ms |
| **Constitutional articles** | I-019 (Evidence Before Conviction), I-020 (Outcome Before Lesson), I-021 (History Is Immutable) |
| **Governing invariants** | INV-11, INV-14, INV-20 |
| **Known fix** | Explicit PAPER_TRADING check added; persistent CSV journal at data/paper_trades.csv |

---

### A.12 Layer 12 — TradeMonitoring Engineering Specification

| Attribute | Specification |
|---|---|
| **Primary components** | `TradeMonitor`, `StrategyHealthMonitor` in `trade_monitoring/` |
| **Threading model** | Dedicated background thread; 5-second polling cycle |
| **Monitored data** | All open positions in `order_manager` position registry |
| **Stop-loss enforcement** | Automatic — no Decision Layer re-approval required; `OrderManager.close_position()` called directly |
| **Target enforcement** | Automatic — profit target hit triggers close; same mechanism as stop |
| **Monitoring gap limit** | < 60 seconds (INV-55); missed heartbeat triggers Level 3 alert |
| **Heartbeat mechanism** | Thread writes timestamp to `system_monitor` every poll cycle |
| **Index symbol exemption** | NIFTY/BANKNIFTY positions monitored by bare symbol; `.NS` suffix not applied |
| **On thread crash** | Alert Human Principal immediately; attempt restart; log full stack trace |
| **State owned** | Monitoring state per position (entry price, stop level, target level, last price) |
| **Constitutional articles** | I-021, I-022 (Completeness of Record), I-023, I-026 (Recall Does Not Alter Memory) |
| **Governing invariants** | INV-23, INV-24, INV-27, INV-55 (Monitoring Continuity) |

---

### A.13 Layer 13 — LearningSystem Engineering Specification

| Attribute | Specification |
|---|---|
| **Primary components** | `LearningEngine`, `StrategyPerformanceTracker` in `learning_system/` |
| **Entry point** | `LearningEngine.trigger_learning(position_lifecycle_event)` |
| **Attribution scope** | Hypothesis, evidence set, reasoning chain, debate record, decision record, execution record |
| **Lesson extraction** | Causal attribution: which factors in the decision predicted the outcome |
| **Belief update** | Rate-limited by INV-34: established beliefs require multiple contradicting examples to update |
| **OOS validation gate** | New lessons held in provisional store until OOS validation confirms (INV-33) |
| **Anti-pattern detection** | Detect: averaging-down addiction, recency bias, confirmation bias patterns in decisions |
| **Durable queue** | Learning triggers that cannot be processed immediately queued to disk |
| **Queue recovery** | On startup, disk queue processed in chronological order before new events |
| **Singleton** | `StrategyPerformanceTracker` accessed via `get_performance_tracker()` |
| **Auto-disable** | `StrategyPerformanceTracker` disables strategy when win rate < 40% over 20+ trades |
| **EOD recovery** | `_do_eod_learning` in orchestrator: reads CSV for today's trades; handles post-restart zero-count |
| **State owned** | LearningEvent log; provisional lesson store; belief store; strategy performance records |
| **Constitutional articles** | I-032 through I-047 (Learning and Improvement chapter) |
| **Governing invariants** | INV-32 through INV-38 |

---

### A.14 Layer 17 — ControlTower Engineering Specification

| Attribute | Specification |
|---|---|
| **Primary components** | `SystemMonitor` in `system_monitor/`; `EventBus`; `TelegramBot` in `notifications/` |
| **SystemMonitor function** | `time_layer(layer_name) -> contextmanager`; records wall-clock time; fires EventBus on WARN/CRIT |
| **WARN threshold** | 2,000ms default; 5,000ms for GlobalIntelligence |
| **CRIT threshold** | 5,000ms default; 12,000ms for GlobalIntelligence |
| **Override mechanism** | `LAYER_LATENCY_WARN_OVERRIDES`, `LAYER_LATENCY_CRIT_OVERRIDES` dicts in `system_monitor.py` |
| **EventBus** | Module-level singleton; topic-based pub-sub; in-process only |
| **Telemetry storage** | SQLite `telemetry` table; 90-day retention |
| **Dashboard container** | Separate Docker container; reads `data/` volume in read-only mode; Streamlit on port 8501 |
| **Telegram singleton** | `TelegramBot` accessed via `get_telegram_bot()`; 13 commands implemented |
| **Authenticated commands** | All Telegram commands check `chat_id` against registered Human Principal before executing |
| **Constitutional articles** | I-056 (Explainability), I-057 (Every Output Is Attributed), I-059 (Performance Attribution Is Regular), I-060, I-061 |
| **Governing invariants** | INV-39 through INV-44 (Explainability category), INV-53 through INV-60 (Continuity category) |

---

## ENGINEERING SUPPLEMENT B — INTER-MODULE DATA FLOW SPECIFICATION

### B.1 Complete Data Flow Topology

This supplement maps every data object that flows between modules during a single cognitive cycle. Each row represents a named data transfer: the producing module, the consuming module, the object type, the transport mechanism, and the latency class.

| # | Producer Module | Consumer Module | Object Type | Transport | Latency Class |
|---|---|---|---|---|---|
| DF-001 | `yahoo_feed` | `data_feed_manager` | `TickerQuote` list | Direct call | Synchronous |
| DF-002 | `dhan_feed` | `data_feed_manager` | `TickerQuote` list | Direct call | Synchronous |
| DF-003 | `data_feed_manager` | `global_data_ai` | `PriceBar` list | Direct call | Synchronous |
| DF-004 | `data_feed_manager` | `market_intelligence_engine` | `TickerQuote` | Direct call | Synchronous |
| DF-005 | `global_data_ai` | `master_orchestrator` | `GlobalSnapshot` | Return value | Synchronous |
| DF-006 | `master_orchestrator` | `market_intelligence_engine` | `GlobalSnapshot` | Argument | Synchronous |
| DF-007 | `market_intelligence_engine` | `master_orchestrator` | `RegimeSignal` | Return value | Synchronous |
| DF-008 | `market_intelligence_engine` | `master_orchestrator` | `SectorReport` | Return value | Synchronous |
| DF-009 | `master_orchestrator` | `meta_learning_engine` | `RegimeSignal` | Argument | Synchronous |
| DF-010 | `regime_strategy_map` | `meta_learning_engine` | `StrategyWeights` | Direct call | Synchronous |
| DF-011 | `meta_learning_engine` | `master_orchestrator` | `StrategyWeights` | Return value | Synchronous |
| DF-012 | `master_orchestrator` | `equity_scanner` | `RegimeSignal` + `StrategyWeights` | Arguments | Synchronous |
| DF-013 | `equity_scanner` | `master_orchestrator` | `OpportunityList` | Return value | Synchronous |
| DF-014 | `master_orchestrator` | `meta_strategy_controller` | `OpportunityList` + `StrategyWeights` | Arguments | Synchronous |
| DF-015 | `meta_strategy_controller` | `master_orchestrator` | `HypothesisList` | Return value | Synchronous |
| DF-016 | `master_orchestrator` | `position_sizer` | `Hypothesis` + `PortfolioState` | Arguments | Synchronous |
| DF-017 | `position_sizer` | `master_orchestrator` | `PositionSizeRecommendation` | Return value | Synchronous |
| DF-018 | `master_orchestrator` | `risk_manager_ai` | `PositionSizeRecommendation` | Argument | Synchronous |
| DF-019 | `risk_manager_ai` | `master_orchestrator` | `RiskApprovalRecord` | Return value | Synchronous |
| DF-020 | `master_orchestrator` | `portfolio_allocation` | `PositionSizeRecommendation` | Argument | Synchronous |
| DF-021 | `portfolio_allocation` | `master_orchestrator` | `ConcentrationCheck` | Return value | Synchronous |
| DF-022 | `master_orchestrator` | `monte_carlo_engine` | `HypothesisList` | Argument | Synchronous |
| DF-023 | `monte_carlo_engine` | `master_orchestrator` | `SimulationReport` | Return value | Synchronous |
| DF-024 | `master_orchestrator` | `risk_guardian` | `SimulationReport` | Argument | Synchronous |
| DF-025 | `risk_guardian` | `order_manager` | `kill_switch_active` (Event) | Shared state | Asynchronous |
| DF-026 | `master_orchestrator` | `debate_engine` | `HypothesisPackage` | Argument | Synchronous |
| DF-027 | `debate_engine` | `decision_engine` | `DebateRecord` | Direct call | Synchronous |
| DF-028 | `decision_engine` | `master_orchestrator` | `DecisionRecord` | Return value | Synchronous |
| DF-029 | `master_orchestrator` | `order_manager` | `DecisionRecord` + `RiskApprovalRecord` | Arguments | Synchronous |
| DF-030 | `order_manager` | `paper_trades.csv` | Trade row | File I/O | Asynchronous |
| DF-031 | `order_manager` | `learning_engine` | `PositionLifecycleEvent` | EventBus | Asynchronous |
| DF-032 | `learning_engine` | `strategy_performance_tracker` | `TradeOutcome` | Direct call | Synchronous |
| DF-033 | `strategy_performance_tracker` | `meta_strategy_controller` | Disable signal | Direct call | Synchronous |
| DF-034 | `learning_engine` | `regime_strategy_map` | `RegimeOutcomePair` | Direct call | Synchronous |
| DF-035 | `system_monitor` | `sqlite_telemetry` | `LayerTimingRecord` | Direct call | Synchronous |
| DF-036 | `system_monitor` | `event_bus` | `SystemAlert` | Direct call | Synchronous |
| DF-037 | `event_bus` | `telegram_bot` | `SystemAlert` | Callback | Asynchronous |
| DF-038 | `telegram_bot` | Human Principal | Notification | External API | Asynchronous |
| DF-039 | `market_monitor` | `equity_scanner` | `ScanResult` | Shared memory | Asynchronous |
| DF-040 | `trade_monitor` | `order_manager` | Close signal | Direct call | Synchronous |

---

### B.2 Object Type Catalogue

This catalogue defines every named data object that crosses a module boundary in the AI Trading Brain. Each entry specifies the object's logical structure, the module that owns (creates) it, and the consuming modules.

| Object Type | Owner Module | Key Attributes | Consuming Modules |
|---|---|---|---|
| `GlobalSnapshot` | `global_data_ai` | sp500_direction, nikkei_direction, usd_inr, vix_level, bonds_signal, quality_score, stale | `market_intelligence_engine`, `master_orchestrator` |
| `RegimeSignal` | `market_intelligence_engine` | regime_type, confidence, conviction_modifier, sector_leaders, valid_until | `meta_learning_engine`, `equity_scanner`, `meta_strategy_controller`, `position_sizer` |
| `SectorReport` | `market_intelligence_engine` | sector_map, rotation_signal, breadth_score, fii_dii_flow | `meta_strategy_controller`, `position_sizer` |
| `StrategyWeights` | `meta_learning_engine` | weight_map (strategy_id → float), source (kNN or equal), uncertainty | `equity_scanner`, `meta_strategy_controller` |
| `OpportunityList` | `equity_scanner` | opportunities (list of Opportunity), scan_timestamp, scan_quality | `meta_strategy_controller` |
| `Opportunity` | `equity_scanner` | symbol, signal_type, signal_strength, price, volume_ratio, regime_alignment | `meta_strategy_controller` |
| `HypothesisList` | `meta_strategy_controller` | hypotheses (list of Hypothesis), generated_at | `position_sizer`, `risk_manager_ai`, `debate_engine` |
| `Hypothesis` | `meta_strategy_controller` | hypothesis_id, instrument, direction, strategy_id, entry_price, stop_price, target_price, rr_ratio, conviction_raw, evidence_set | `position_sizer`, `risk_manager_ai`, `debate_engine` |
| `HypothesisPackage` | `master_orchestrator` | hypothesis, position_size_rec, risk_approval_record | `debate_engine` |
| `PositionSizeRecommendation` | `position_sizer` | recommended_size_pct, recommended_size_units, kelly_fraction, uncertainty_adjustment, regime_adjustment | `risk_manager_ai`, `portfolio_allocation`, `debate_engine` |
| `RiskApprovalRecord` | `risk_manager_ai` | approved (bool), reason, approved_at, valid_until (30s), conditions | `order_manager` |
| `ConcentrationCheck` | `portfolio_allocation` | sector_concentration_ok, theme_concentration_ok, entity_concentration_ok, max_add_size | `master_orchestrator` |
| `SimulationReport` | `monte_carlo_engine` | scenarios (14), worst_case_drawdown, scenario_pass_rate, recommendation | `risk_guardian`, `master_orchestrator` |
| `DebateRecord` | `debate_engine` | hypothesis_id, agent_votes (5 × AgentVote), aggregate_score, threshold_passed, duration_ms | `decision_engine`, `sqlite_telemetry`, `learning_engine` |
| `AgentVote` | Agent module | agent_role, score (1–10), reasoning, evidence_used, uncertainty | `debate_engine` |
| `DecisionRecord` | `decision_engine` | decision_id, hypothesis_id, approved (bool), conviction (1–10), reasoning_chain, agent_reasoning_map, decided_at | `order_manager`, `sqlite_telemetry`, `learning_engine` |
| `OrderRecord` | `order_manager` | order_id, decision_id, instrument, direction, size, submitted_at, status, fill_price, slippage | `trade_monitor`, `learning_engine`, `paper_trades.csv` |
| `FillRecord` | `order_manager` | order_id, fill_price, fill_time, slippage_pct, fill_quality | `trade_monitor`, `learning_engine` |
| `PositionLifecycleEvent` | `order_manager` | event_type (OPEN/CLOSE/UPDATE), order_id, position_id, p_l, cause (manual/stop/target/kill_switch) | `learning_engine`, `strategy_performance_tracker` |
| `TradeOutcome` | `learning_engine` | trade_id, strategy_id, regime_at_entry, outcome_pnl, outcome_pct, winner (bool), hold_duration | `strategy_performance_tracker`, `regime_strategy_map` |
| `LayerTimingRecord` | `system_monitor` | layer_name, duration_ms, threshold_warn_ms, threshold_crit_ms, cycle_id, timestamp | `sqlite_telemetry` |
| `ScanResult` | `market_monitor` | symbol, scan_type (breadth/momentum/volatility), value, change_pct, triggered_at | `equity_scanner` |
| `SystemAlert` | `system_monitor` | alert_id, severity (INFO/WARN/CRIT), layer, message, timestamp | `event_bus`, `telegram_bot` |
| `RegimeOutcomePair` | `learning_engine` | regime_features, strategy_id, outcome, timestamp | `regime_strategy_map` |
| `kill_switch_active` | `risk_guardian` | threading.Event object; set=kill active, clear=trading permitted | `order_manager`, `trade_monitor` |
| `TickerQuote` | Feed adapters | symbol, bid, ask, last, volume, timestamp, source | `data_feed_manager` and all consumers |
| `PriceBar` | Feed adapters | symbol, open, high, low, close, volume, interval, timestamp | All consumers requiring history |

---

### B.3 Data Flow Across the Three Cognitive Planes

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                    PERCEPTION PLANE (Layers 1-4)                                 │
│                                                                                  │
│  External World                                                                  │
│      │                                                                           │
│      ▼                                                                           │
│  [yahoo_feed / dhan_feed]  ──TickerQuote/PriceBar──▶  [data_feed_manager]       │
│                                                              │                   │
│                    ┌─────────────────────────────────────────┤                  │
│                    │                                         │                  │
│                    ▼                                         ▼                  │
│           [global_data_ai]                    [market_intelligence_engine]       │
│                    │                                         │                  │
│                    └─────────GlobalSnapshot──────────────────┤                  │
│                                                              │                  │
│                                                    RegimeSignal + SectorReport  │
│                                                              │                  │
│                                                              ▼                  │
│                                                    [meta_learning_engine]        │
│                                                              │                  │
│                                                         StrategyWeights          │
│                                                              │                  │
│                                                              ▼                  │
│                                                    [equity_scanner]              │
│                                                              │                  │
│                                                         OpportunityList          │
└──────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │  OpportunityList + StrategyWeights
                                      ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                    COGNITION PLANE (Layers 5-10)                                 │
│                                                                                  │
│   [meta_strategy_controller]  ──HypothesisList──▶  [position_sizer]             │
│                                                            │                    │
│                                               PositionSizeRecommendation         │
│                                                            │                    │
│                                                            ▼                    │
│                                                    [risk_manager_ai]             │
│                                                            │                    │
│                                                     RiskApprovalRecord           │
│                                                            │                    │
│                          ┌─────────────────────────────────┤                    │
│                          │                                 │                    │
│                          ▼                                 ▼                    │
│                  [monte_carlo_engine]               [portfolio_allocation]       │
│                          │                                                      │
│                   SimulationReport                                               │
│                          │                                                      │
│                          ▼                                                      │
│                  [risk_guardian]  ──────────kill_switch──────────────────┐      │
│                                                                          │      │
│   [debate_engine]  ◀──HypothesisPackage                                  │      │
│         │                                                                │      │
│    DebateRecord                                                           │      │
│         │                                                                │      │
│         ▼                                                                │      │
│   [decision_engine]  ──DecisionRecord──────────────────────────────────▶│      │
│                                                                          │      │
└──────────────────────────────────────────────────────────────────────────┼──────┘
                                                                           │
                                      DecisionRecord + RiskApprovalRecord  │
                                                                           │
┌──────────────────────────────────────────────────────────────────────────┼──────┐
│                    ACTION PLANE (Layers 11-17)                           │      │
│                                                                          │      │
│   [order_manager]  ◀─────────────────────────────────────────────────────┘      │
│         │                                                                        │
│    OrderRecord + FillRecord                                                      │
│         │                                                                        │
│         ├──PositionLifecycleEvent──▶  [learning_engine]                          │
│         │                                    │                                  │
│         │                        TradeOutcome + RegimeOutcomePair                │
│         │                                    │                                  │
│         │                    ┌───────────────┴────────────────┐                 │
│         │                    ▼                                ▼                 │
│         │    [strategy_performance_tracker]      [regime_strategy_map]           │
│         │                    │                        (feeds back to Layer 3)    │
│         │             Auto-disable signal                                        │
│         │                    ▼                                                  │
│         │         [meta_strategy_controller]                                    │
│         │                                                                       │
│         └──▶  [trade_monitor]  ──Close signal──▶  [order_manager]               │
│                                                                                 │
│   [system_monitor]  ──LayerTimingRecord──▶  [sqlite_telemetry]                  │
│         │                                                                       │
│         └──SystemAlert──▶  [event_bus]  ──▶  [telegram_bot]  ──▶  Human        │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

### B.4 Critical Path Analysis

The critical path is the sequence of operations that determines the minimum cycle time. Any operation on this path directly extends the full cognitive cycle duration.

**Critical path for a single hypothesis through a full cycle:**

```
GlobalDataAI.fetch()            [17ms typical,  5,000ms WARN]
    → MarketIntelligenceEngine  [19ms typical,  2,000ms WARN]
    → MetaLearningEngine        [< 5ms typical, 2,000ms WARN]
    → EquityScanner             [< 50ms typical, 2,000ms WARN]
    → MetaStrategyController    [< 20ms typical, 2,000ms WARN]
    → PositionSizer             [< 5ms typical,   500ms WARN]
    → RiskManagerAI             [< 10ms typical,  500ms WARN]
    → MonteCarlo                [< 30ms typical, 2,000ms WARN]
    → RiskGuardian check        [< 1ms (atomic Event check)]
    → DebateEngine (5 agents)   [< 50ms typical, 2,000ms WARN]
    → DecisionEngine            [< 5ms typical,  2,000ms WARN]
    → OrderManager              [< 10ms typical, 2,000ms WARN]
    ─────────────────────────────────────────────────────────
    TOTAL CRITICAL PATH         [172ms typical, measured baseline]
```

**Off-critical-path operations (asynchronous):**
- `market_monitor` scan thread (30s cycle; not on critical path)
- `trade_monitor` stop/target enforcement (5s cycle; not on critical path)
- `risk_guardian` monitor loop (500ms cycle; kill flag pre-set; only read on critical path)
- Learning pipeline updates (triggered by EventBus; not on critical path)
- Telegram notifications (async; not on critical path)
- SQLite telemetry writes (async; not on critical path)

---

### B.5 Feedback Loop Engineering

The AI Trading Brain contains two fundamental feedback loops. Both are implemented as asynchronous flows to avoid blocking the critical path.

**Loop 1 — Trade Outcome → Strategy Weight Update:**

```
OrderManager emits PositionLifecycleEvent(CLOSE)
    → LearningEngine processes event (async, via EventBus)
    → StrategyPerformanceTracker.record_outcome(TradeOutcome)
    → If win_rate < 40% AND trades >= 20 → disable strategy
    → LearningEngine emits RegimeOutcomePair to RegimeStrategyMap
    → RegimeStrategyMap updates kNN training data
    → Next cycle: MetaLearningEngine reads updated weights
    → MetaStrategyController applies new weights to hypothesis selection
```

**Loop 2 — Market Regime Change → Scan Depth Change:**

```
MarketMonitor detects significant market move (scan cycle)
    → If move exceeds threshold → consume one deep-scan slot
    → MarketIntelligenceEngine triggered for deep analysis
    → If regime change detected (2 consecutive confirmations)
    → MarketIntelligenceEngine emits new RegimeSignal
    → EquityScanner adapts signal universe to new regime
    → MetaStrategyController weights shift via updated StrategyWeights
    → MetaLearningEngine records regime transition event
```

---

## ENGINEERING SUPPLEMENT C — THREADING AND CONCURRENCY MODEL

### C.1 Thread Registry

The following table lists every thread running in the AI Trading Brain process. Threads are numbered in order of creation during startup.

| Thread | Name | Priority | Daemon | Created By | Stack Size | Purpose |
|---|---|---|---|---|---|---|
| T-001 | `MainThread` | Normal | No | OS | Default | Scheduler, cognitive cycles, all synchronous layers |
| T-002 | `GlobalPreWarmThread` | Below Normal | Yes | `GlobalDataAI.__init__` | 4MB | Pre-fetches GlobalSnapshot 30min before market open |
| T-003 | `MarketMonitorThread` | Normal | Yes | `MarketMonitor.start()` | 4MB | 30-second scan cycle; deep-scan on significant moves |
| T-004 | `RiskGuardianThread` | Above Normal | Yes | `RiskGuardianAgent.start()` | 2MB | 500ms kill condition polling |
| T-005 | `TradeMonitorThread` | Normal | Yes | `TradeMonitor.start()` | 2MB | 5-second position monitoring |
| T-006 | `TelegramBotThread` | Below Normal | Yes | `TelegramBot.start()` | 4MB | Long-poll Telegram API; handle commands |
| T-007 | `LearningQueueThread` | Below Normal | Yes | `LearningEngine.start()` | 8MB | Drain learning event queue; persist lessons |
| T-008 | `EventBusDispatchThread` | Normal | Yes | `EventBus.start()` | 2MB | Dispatch events to subscribers |

---

### C.2 Shared State Inventory

| Shared State Object | Type | Owner | Protected By | Readers | Writers |
|---|---|---|---|---|---|
| `global_snapshot_cache` | Dict | `GlobalDataAI` | `threading.Lock` | T-001 | T-001, T-002 |
| `kill_switch_active` | `threading.Event` | `RiskGuardianAgent` | Atomic (Event) | T-001, T-004, T-005 | T-004 |
| `open_positions` | Dict | `OrderManager` | `threading.Lock` | T-001, T-005 | T-001, T-005 |
| `daily_pnl` | Float | `OrderManager` | `threading.Lock` | T-001, T-004 | T-001, T-005 |
| `scan_results` | List | `MarketMonitor` | `threading.Lock` | T-001 | T-003 |
| `deep_scan_slots_used` | Int | `MarketMonitor` | `threading.Lock` | T-001, T-003 | T-003 |
| `strategy_weights_cache` | Dict | `MetaLearningEngine` | `threading.RLock` | T-001 | T-001, T-007 |
| `learning_event_queue` | Queue | `LearningEngine` | `queue.Queue` (thread-safe) | T-007 | T-001, T-008 |
| `event_bus_subscribers` | Dict | `EventBus` | `threading.RLock` | T-008 | T-001 (registration) |
| `telemetry_db` | SQLite connection | `SystemMonitor` | Connection per thread (WAL) | All threads | All threads |

---

### C.3 Thread Safety Rules

The following thread safety rules are architectural invariants. They are not enforced by code alone — they must be understood and preserved by any engineer modifying the system.

| Rule | Applies To | Detail |
|---|---|---|
| **TS-001** | `kill_switch_active` | Use only `threading.Event.set()`/`is_set()`; never replace the Event object |
| **TS-002** | `open_positions` | Acquire lock before any read-modify-write; never hold lock across I/O |
| **TS-003** | `daily_pnl` | Always read and write under the `OrderManager._pnl_lock` |
| **TS-004** | SQLite writes | Use WAL mode; each thread uses its own connection; never share connections |
| **TS-005** | `global_snapshot_cache` | Lock held only during cache update (< 1ms); release before returning to caller |
| **TS-006** | Learning queue | Always use `queue.Queue.put_nowait()`; never block main thread on learning |
| **TS-007** | Strategy disable | `StrategyPerformanceTracker` sets disable flag under RLock; `MetaStrategyController` reads under same lock |
| **TS-008** | Regime detection | New regime only set after 2 consecutive scan confirmations; single writer (T-003) |

---

### C.4 Deadlock Prevention Architecture

Potential deadlock cycles between threads are eliminated by the following architectural decisions:

| Potential Cycle | Prevention Mechanism |
|---|---|
| T-001 waits on T-003 (market scan) | T-001 reads `scan_results` snapshot; does not wait for T-003 |
| T-001 waits on T-007 (learning) | Learning is fully asynchronous via `queue.Queue`; T-001 never joins T-007 |
| T-004 (guardian) waits on T-001 | Guardian only writes `threading.Event`; never calls T-001 methods |
| T-005 (monitor) calls `order_manager.close()` | `close()` takes `_positions_lock`; T-001 never holds `_positions_lock` while calling T-005 |
| T-007 waits on T-008 (event bus) | Learning queue events are fire-and-forget via EventBus; no reply expected |
| T-003 requests deep scan while T-001 active | Deep scans execute in T-003's own loop; T-001 reads only cached result |

---

## ENGINEERING SUPPLEMENT D — FAILURE MODE ENGINEERING

### D.1 Failure Mode Response Matrix

This supplement maps each of the 21 IIOS failure modes to the engineering response: the detection mechanism, the automated response, the escalation path, and the recovery procedure.

| Failure Mode | IIOS ID | Detection Mechanism | Automated Response | Escalation | Recovery Procedure |
|---|---|---|---|---|---|
| Evidence Source Offline | FM-01 | Feed adapter returns empty/exception | Auto-fallback to secondary source (yfinance) | Telegram alert | Resume when primary recovers; log gap |
| Market Data Staleness | FM-02 | `stale=True` flag on TickerQuote | Use stale data with reduced conviction | Telegram WARN if > 5min | Reconnect feed; clear stale flag |
| Regime Misclassification | FM-03 | Consecutive regime contradictions | Hysteresis: require 2 confirmations | Log INFO; no human alert needed | Auto-corrects on next scan |
| Strategy Overfitting | FM-04 | OOS validation fails | Block strategy promotion | Telegram WARN | Re-run evolution with larger OOS window |
| Cognitive Loop Hang | FM-05 | `SystemMonitor.time_layer()` CRIT exceeded | Abort cycle; log; skip to next scheduled cycle | Telegram CRIT alert | Auto-recovery via scheduler; diagnose root cause |
| Kill-Switch Trigger | FM-06 | Guardian detects VIX > 45 or loss > 2% | Set `kill_switch_active` Event; block all submissions | Telegram IMMEDIATE | Human override required to clear |
| Conviction Below Threshold | FM-07 | DebateRecord aggregate < 6.5 | Hypothesis SUSPENDED; no order submitted | Log INFO | Normal operation; hypothesis discarded |
| Order Rejection | FM-08 | Broker returns error or risk approval expired | Order abandoned; reason logged | Log WARNING | Retry on next cycle if hypothesis still valid |
| Drawdown Halt | FM-09 | Day P&L < -2% threshold | Kill-switch activates; all new orders blocked | Telegram IMMEDIATE | Human override; review positions before resuming |
| Data Feed Failure (both) | FM-10 | Both feed adapters raise exception | Return last cached data with `stale=True` | Telegram CRIT | Monitor until either feed recovers |
| Learning Queue Overflow | FM-11 | `queue.Queue` size exceeds 1,000 items | Drop oldest events; log WARNING | Telegram WARN | Increase queue drain speed; check T-007 health |
| Thread Crash | FM-12 | Thread join returns unexpectedly | Restart thread (once); if crash repeats → alert | Telegram CRIT | Investigate root cause; may need manual restart |
| SQLite Corruption | FM-13 | IntegrityError or SQLITE_CORRUPT | Mark DB read-only; switch to in-memory fallback | Telegram CRIT | Restore from last backup; re-run missed events |
| RiskGuardian Thread Death | FM-14 | Heartbeat check in main thread fails | Set `kill_switch_active` (fail-safe) | Telegram IMMEDIATE | Human review required; restart daemon |
| Config Validation Failure | FM-15 | Config checksum mismatch on startup | Refuse to start; dump diff to log | Log CRIT; startup blocked | Restore last verified config; revalidate |
| Decision Record Missing | FM-16 | `order_manager` cannot find `decision_id` in SQLite | Refuse to submit order | Log CRIT | Re-run cognitive cycle; do not manually inject records |
| Risk Approval Expired | FM-17 | `valid_until` timestamp has passed | Refuse to submit order | Log WARNING | Re-run risk layer; approvals are stateless |
| Telegram Bot Failure | FM-18 | API call raises exception | Retry with exponential backoff (3 attempts) | Log WARNING; continue operation | System continues without notification; bot auto-reconnects |
| Scheduler Miss | FM-19 | Expected cycle slot not triggered within 2min | Log WARNING; trigger makeup cycle | Telegram WARN | Auto-recovery; diagnose if recurring |
| Docker Container Crash | FM-20 | `restart: unless-stopped` policy | Docker auto-restarts container | Telegram alert from monitoring | Review logs; fix root cause; redeploy |
| VPS Network Partition | FM-21 | All external calls fail; feed times out | Use cached data with `stale=True`; reduce conviction | Telegram when connectivity restored | Resume automatically when network reconnects |

---

### D.2 Fail-Safe Architecture

The AI Trading Brain is designed around a fail-safe principle: **when in doubt, do nothing**. The following architectural choices enforce fail-safe behaviour:

| Fail-Safe Rule | Enforcement Point | Default When Rule Violated |
|---|---|---|
| No order without DecisionRecord | `order_manager.submit()` gate | Order silently dropped; WARNING logged |
| No order without RiskApproval | `order_manager.submit()` gate | Order silently dropped; WARNING logged |
| No order when RiskApproval expired | `order_manager.submit()` gate | Order silently dropped; WARNING logged |
| No order when kill_switch_active | `order_manager.submit()` gate | Order silently dropped; CRIT logged; Telegram alert |
| No order when Guardian thread dead | Startup/heartbeat check | Kill-switch pre-emptively set |
| No position without stop-loss | `risk_manager_ai.approve()` | Approval REJECTED with reason MISSING_STOP |
| No regime change without hysteresis | `MarketMonitor` confirmation count | Prior regime maintained |
| No belief update on single event | `LearningEngine` rate-limiter | Single event queued as provisional only |
| No strategy activation without OOS validation | `ValidationEngine` gate | Strategy held in provisional status |
| No configuration change without checksum | `config.py` loader | Startup aborted; last verified config preserved |

---

## ENGINEERING SUPPLEMENT E — SCHEDULER ENGINEERING

### E.1 Scheduler Architecture

The master scheduler is implemented in `orchestrator/master_orchestrator.py` as a structured collection of scheduled jobs using APScheduler (or equivalent Python scheduler). The scheduler is the single source of timing authority for the entire system.

| Schedule Slot | Cron Expression | Triggered Method | Duration Budget | Purpose |
|---|---|---|---|---|
| Pre-Market Init | 08:30 IST Mon-Fri | `_do_premarket_init()` | 300s | GlobalDataAI pre-warm; position reconciliation; config validation |
| MarketOpen Check | 09:15 IST Mon-Fri | `_do_market_open()` | 60s | Confirm feeds active; set market_open flag |
| Cognitive Cycle | Every 30s, 09:15–15:30 IST | `_do_cognitive_cycle()` | 30s max | Full 17-layer intelligence + decision cycle |
| Continuous Scan | Every 30s, 09:00–16:00 IST | `MarketMonitor.scan()` | 10s max | Quick market breadth + momentum scan |
| Mid-Day Review | 12:30 IST Mon-Fri | `_do_midday_review()` | 120s | Performance snapshot; strategy health check |
| MarketClose | 15:30 IST Mon-Fri | `_do_market_close()` | 60s | Set market_closed flag; stop cognitive cycles |
| EOD Learning | 16:00 IST Mon-Fri | `_do_eod_learning()` | 600s | Full learning cycle; strategy weight update |
| EOD Report | 16:15 IST Mon-Fri | `_do_eod_report()` | 120s | Generate and send P&L report via Telegram |
| Weekly Evolution | Sunday 22:00 IST | `_do_weekly_evolution()` | 3600s | Strategy evolution; backtesting; promotion gate |
| Health Check | Every 60s, all hours | `_do_health_check()` | 30s | Thread heartbeats; disk space; memory usage |

---

### E.2 Market Hours Guard

The market hours guard is a pre-condition check at the entry of `_do_cognitive_cycle()`. It prevents cognitive cycles from running outside market hours.

| Check | Condition for Pass | Fail Action |
|---|---|---|
| Weekday check | `datetime.weekday() in [0,1,2,3,4]` | Skip cycle; log DEBUG |
| NSE market hours | `09:15 <= current_time <= 15:30 IST` | Skip cycle; log DEBUG |
| Market open flag | `self._market_open_flag == True` | Skip cycle; log INFO |
| Kill-switch | `risk_guardian.kill_switch_active.is_set() == False` | Skip cycle; log CRIT; alert |
| Feed health | At least one feed returning valid quotes | Proceed with stale flag; log WARNING |
| Config validity | Config checksum matches startup value | Skip cycle; log CRIT; alert |

---

### E.3 EOD Learning Engineering Detail

The EOD learning process must handle the case where the system was restarted during the trading day (losing in-memory state). The engineering approach:

1. **CSV Recovery**: `_do_eod_learning()` reads `data/paper_trades.csv` filtering for `date == today`
2. **Deduplication**: Trades already in SQLite `learning_events` table are skipped by `trade_id`
3. **Zero-count guard**: If in-memory closed trade count is 0 but CSV has trades for today → use CSV source
4. **Strategy attribute fix**: `position_lifecycle_event.strategy` (not `.strategy_name`) used throughout
5. **Outcome computation**: P&L from CSV `pnl` column; win/loss from sign of `pnl`
6. **Batch learning**: All today's trades processed in chronological order; `strategy_performance_tracker` updated once per strategy

---

## ENGINEERING SUPPLEMENT F — DEPLOYMENT ENGINEERING

### F.1 Container Architecture

The AI Trading Brain deployment consists of two Docker containers managed by `docker-compose.yml`.

| Container | Image | Base | Purpose | Exposed Port | Health Check |
|---|---|---|---|---|---|
| `ai-trading-brain` | `ai_trading_brain:latest` | `python:3.14-slim` | Main trading engine | None (internal) | `python main.py --health` returns 0 |
| `trading-dashboard` | `trading_dashboard:latest` | `python:3.14-slim` | Streamlit monitoring UI | 8501 | HTTP GET /healthz returns 200 |

---

### F.2 Volume Architecture

| Volume Name | Host Path | Container Path | Mode | Contents |
|---|---|---|---|---|
| `trading-data` | `./data` | `/app/data` | Read-Write | SQLite databases, CSV journals, evolved strategy JSON, log files |
| `trading-config` | `./config.py` | `/app/config.py` | Read-Only | Single config file; injected at deploy time |
| `dashboard-data` | `./data` | `/app/data` | Read-Only | Dashboard reads same data volume; no writes from dashboard |

---

### F.3 Environment Variable Architecture

| Variable | Set In | Used By | Purpose |
|---|---|---|---|
| `DHAN_API_KEY` | Docker secrets / host env | `dhan_feed.py` | Dhan API authentication |
| `DHAN_CLIENT_ID` | Docker secrets / host env | `dhan_feed.py` | Dhan client identification |
| `TELEGRAM_BOT_TOKEN` | Docker secrets / host env | `telegram_bot.py` | Telegram API authentication |
| `TELEGRAM_CHAT_ID` | Docker secrets / host env | `telegram_bot.py` | Registered Human Principal chat ID |
| `PAPER_TRADING` | `config.py` | `order_manager.py` | Master paper/live mode switch |
| `VPS_HOSTNAME` | Docker host env | `system_monitor.py` | Identifies deployment environment in telemetry |

---

### F.4 Deployment Verification Protocol

Every deployment must complete this verification sequence before declaring the deploy done:

| Step | Command | Pass Condition |
|---|---|---|
| Step 1 | `docker compose ps` | Both containers `Up` and `(healthy)` |
| Step 2 | `docker logs ai-trading-brain --tail 50` | No ERROR or CRITICAL lines in last 50 lines |
| Step 3 | `docker exec ai-trading-brain python main.py --status` | Returns HEALTHY with 0 exit code |
| Step 4 | `curl http://localhost:8501/healthz` | HTTP 200 OK |
| Step 5 | Telegram command `/status` | Bot responds with current system health |
| Step 6 | Wait for next scheduled cycle | No ERROR in logs during cycle execution |
| Step 7 | Confirm telemetry | SQLite `telemetry` table has new entry within 5 minutes |

**Deploy is NOT done until all 7 steps pass.**

---

### F.5 Rollback Engineering

| Trigger | Rollback Action | Recovery Time Target |
|---|---|---|
| Container fails health check after deploy | `git revert HEAD; git push; re-run deploy` | < 15 minutes |
| Both containers crash on startup | Restore `./data` from last backup; re-run deploy | < 30 minutes |
| SQLite corruption detected | Restore `trading_brain.db` from `./data/backups/`; restart containers | < 20 minutes |
| Config change causes startup failure | `git checkout config.py; re-run deploy` | < 10 minutes |
| Feed authentication failure | Update env vars; `docker compose restart ai-trading-brain` | < 5 minutes |

---

## SUPPLEMENTARY READINESS REFERENCE — EXTENDED PHASE CHECKLISTS

### SR.0 Overview

This part contains the formal readiness checklists that must be completed before moving from one implementation phase to the next. Each checklist specifies the precise pass criteria, the verification method, and the accountable role.

The readiness framework operates at two levels:
- **Phase Readiness Gate**: Must be satisfied before any component of the next phase begins
- **Per-Module Readiness**: Tracks fine-grained status for each of the 22 primary modules

No phase transition is authorised until the corresponding phase readiness gate registers PASS on all items.

---

### SR.1 Phase I Readiness — Foundation and Safety

Phase I establishes the foundation: data acquisition, risk enforcement, and system observability. No intelligent trading activity can begin before Phase I is PASS.

**Infrastructure Readiness:**

| Check | Criteria | Verified By | Pass? |
|---|---|---|---|
| Python version | Python 3.14+ confirmed in `.venv` | `python --version` | — |
| Virtual environment | `.venv/` exists; all requirements installed | `pip check` returns 0 warnings | — |
| Docker Compose | Both containers build without error | `docker compose build` | — |
| Volume mount | `./data:/app/data` mounted; write permission confirmed | Write test file to `/app/data` | — |
| Config validation | `config.py` loads without exception; all required keys present | `python -c "import config"` | — |
| SQLite initialisation | `trading_brain.db` created; schema tables exist | `sqlite3 trading_brain.db .tables` | — |
| Telemetry table | `telemetry` table writable | Insert test row; confirm count increments | — |
| Log directory | `logs/` writable; rotation configured | Write test log entry | — |

**Data Feed Readiness:**

| Check | Criteria | Verified By | Pass? |
|---|---|---|---|
| yfinance fallback | `yahoo_feed.get_quote("RELIANCE.NS")` returns valid `TickerQuote` | Direct module test | — |
| Feed manager singleton | `get_feed_manager()` returns same object on repeated calls | Two calls; `id()` match | — |
| Timeout enforcement | `timeout=8` confirmed in `yahoo_feed.yf.download()` call | Code review; `grep timeout yahoo_feed.py` | — |
| History retrieval | `get_history("RELIANCE.NS", days=30, interval="1d")` returns ≥ 20 bars | Integration test | — |
| Quote caching | Second call within 60s faster than first (< 10ms) | Timing test | — |
| Multi-quote batch | `get_multiple_quotes(["RELIANCE.NS","TCS.NS"])` returns both | Integration test | — |
| Index symbol routing | `get_quote("NIFTY")` routes to `^NSEI` without `.NS` suffix | Code review; routing test | — |
| Data quality flag | `stale=True` returned when source fails | Mock failure; assert flag | — |

**Risk and Safety Readiness:**

| Check | Criteria | Verified By | Pass? |
|---|---|---|---|
| Kill-switch thread | `RiskGuardianAgent` thread starts; 500ms poll confirmed | Thread listing; log output | — |
| Kill-switch activation | VIX trigger causes `kill_switch_active.is_set() == True` | Inject VIX=46; assert flag | — |
| Kill-switch gate | `order_manager.submit()` returns BLOCKED when kill_switch set | Integration test | — |
| Daily loss halt | P&L < -2% activates kill-switch | Inject loss; assert flag | — |
| Risk approval expiry | Approval older than 30s rejected by `order_manager` | Time-advance test | — |
| Paper trading mode | `config.PAPER_TRADING = True` prevents any broker call | Code review; mock broker | — |
| CSV journal | Trade appended to `data/paper_trades.csv` in paper mode | Submit paper trade; read CSV | — |
| Fail-safe default | Risk unavailability causes REJECTED (never APPROVED) | Kill risk thread; assert rejection | — |

**Monitoring Readiness:**

| Check | Criteria | Verified By | Pass? |
|---|---|---|---|
| SystemMonitor timing | `time_layer()` records duration; WARN fires at threshold | Timing test with artificial delay | — |
| Layer override config | GlobalIntelligence override (5,000/12,000ms) loaded | Print override dict | — |
| EventBus delivery | Alert published → subscriber callback fires within 1s | Publish test event; measure | — |
| Telegram bot start | `get_telegram_bot()` connects; responds to `/status` | Send `/status`; await reply | — |
| Telegram auth | Unknown chat_id rejected | Send from unknown chat; assert no reply | — |
| Dashboard container | Streamlit UI loads at http://localhost:8501 | `curl http://localhost:8501` | — |

---

### SR.2 Phase II Readiness — Intelligence and Learning

Phase II adds the intelligence pipeline. Phase I must be PASS before Phase II begins.

**Intelligence Plane Readiness:**

| Check | Criteria | Verified By | Pass? |
|---|---|---|---|
| GlobalDataAI cache | Second call within 5 min returns cached result (< 5ms) | Timing test; 2 sequential calls | — |
| Pre-warm thread | GlobalSnapshot in cache 30min before 09:15 | Set clock; confirm cache populated | — |
| GlobalSnapshot quality | `quality_score > 0` when feeds active | Integration test | — |
| Regime classification | MarketIntelligenceEngine produces valid RegimeSignal | Run classification; inspect output | — |
| Regime hysteresis | Single-scan regime change not committed until 2 confirmations | Inject single contradicting scan | — |
| Market monitor thread | T-003 runs at 30s intervals; deep-scan slots tracked | Thread listing; scan count over 5 min | — |
| kNN weights | MetaLearningEngine returns equal weights when < 20 training points | Cold-start test | — |
| kNN training | After 20+ regime-outcome pairs, weights differ from equal | Feed 25 training pairs; check weights | — |
| Equity scanner | `scan()` returns non-empty OpportunityList during market hours | Market-hours integration test | — |

**Debate and Decision Readiness:**

| Check | Criteria | Verified By | Pass? |
|---|---|---|---|
| All 5 agents vote | Every agent in `debate_engine.AGENTS` produces AgentVote | Inspect DebateRecord | — |
| Conviction threshold | Aggregate < 6.5 → SUSPENDED; aggregate ≥ 6.5 → proceed | Test both cases | — |
| Debate timeout | Hypothesis with 30s+ debate → SUSPENDED | Inject artificial delay | — |
| DecisionRecord created | SQLite `decisions` table entry before `order_manager.submit()` | Query after decision | — |
| Decision validity | Decision older than 30s rejected by `order_manager` | Time-advance test | — |

**Learning Pipeline Readiness:**

| Check | Criteria | Verified By | Pass? |
|---|---|---|---|
| Learning queue | `PositionLifecycleEvent` enqueued on position close | Close paper position; check queue | — |
| StrategyPerformanceTracker | Win rate calculated correctly from outcomes | Feed 10 wins / 5 losses; assert 66.7% | — |
| Auto-disable | Strategy with win_rate < 40% after 20 trades disabled | Feed 7 wins / 13 losses = 35% | — |
| RegimeStrategyMap update | `RegimeOutcomePair` added to kNN training data after close | Close position; assert training data +1 | — |
| EOD recovery | CSV trades for today recovered after restart (zero in-memory count) | Restart with trades in CSV; assert count | — |

---

### SR.3 Phase III Readiness — Optimisation and Validation

Phase III adds performance optimisation, walk-forward testing, and constitutional compliance gates.

**Performance Optimisation Readiness:**

| Check | Criteria | Verified By | Pass? |
|---|---|---|---|
| Full cycle baseline | 172ms or better per cycle (as measured; protected baseline) | Run 10 cycles; take average | — |
| GlobalIntelligence timing | < 17ms on cache hit | Timing test with warm cache | — |
| MarketIntelligence timing | < 19ms typical | 10-cycle average | — |
| No regression | Any change to critical path re-benchmarked before merge | Timing test after every PR | — |
| Thread contention | No lock waits > 50ms in any thread | Python lock contention profiler | — |

**Constitutional Compliance Readiness:**

| Check | Criteria | Verified By | Pass? |
|---|---|---|---|
| All 60 invariants | Every INV-01 through INV-60 mapped to enforcement code | Invariant traceability matrix | — |
| Kill-switch inviolability | INV-24: no code path allows order when kill_switch set | Full code path audit | — |
| Memory immutability | INV-26: no record modification after creation | SQLite INSERT-only audit | — |
| Debate completeness | INV-10: all 5 agents must vote | Test with mocked unavailable agent | — |
| Position limit | INV-25: no position > config.MAX_POSITION_PCT | Inject oversized recommendation | — |

**Institutional Memory Readiness:**

| Check | Criteria | Verified By | Pass? |
|---|---|---|---|
| SQLite WAL mode | `PRAGMA journal_mode` returns `wal` | Direct PRAGMA query | — |
| 90-day telemetry retention | Records older than 90 days pruned on schedule | Inject old records; run prune job | — |
| Backup schedule | Daily backup of `trading_brain.db` to `./data/backups/` | Check backup file timestamps | — |
| Evolved strategies preserved | `evolved_strategies/` JSON files survive container restart | Restart container; assert files exist | — |

---

### SR.4 Phase IV Readiness — Live Capital Transition

Phase IV is the transition from paper trading to live capital. This is the highest-stakes gate. **All prior phase gates must be PASS before Phase IV is considered.**

**Constitutional Readiness:**

| Check | Criteria | Verified By | Pass? |
|---|---|---|---|
| Minimum paper trading period | 90 calendar days of paper trading completed | Log timestamp; compute delta | — |
| Win rate target | Win rate ≥ 50% over 90-day paper period | `strategy_performance_tracker` report | — |
| Sharpe ratio target | Sharpe ratio > 0.8 over 90-day paper period | `drawdown_analyzer` report | — |
| Max drawdown limit | Maximum drawdown < 15% over 90-day paper period | `drawdown_analyzer` report | — |
| Walk-forward validation | All active strategies pass walk-forward test (OOS Sharpe > 0.5) | `backtesting_ai.walk_forward()` report | — |
| Stress test | 14 Monte Carlo scenarios — ≥ 12/14 pass | `monte_carlo_engine` report | — |

**Broker Integration Readiness:**

| Check | Criteria | Verified By | Pass? |
|---|---|---|---|
| Dhan authentication | `dhan_feed.authenticate()` returns success (no 451 error) | Live API call | — |
| Order routing | `ZerodhaBroker.submit_order()` reaches broker in test mode | Broker sandbox test | — |
| Fill confirmation | Broker returns fill confirmation within 5s | Timing test in sandbox | — |
| Position reconciliation | `order_manager` positions match broker positions after reconciliation | Reconcile after sandbox orders | — |

**Dual-Mode Validation Readiness:**

| Check | Criteria | Verified By | Pass? |
|---|---|---|---|
| Paper-to-live toggle | `config.PAPER_TRADING = False` routes to real broker | Config toggle; confirm broker call | — |
| Live-to-paper fallback | Broker failure reverts to paper mode | Mock broker failure; assert fallback | — |
| Position sizing at live scale | Sizes appropriate for live capital (not paper-scale) | Size calculation audit | — |
| Human Principal sign-off | Documented approval by Human Principal | Written authorisation on record | — |

---

### SR.5 Per-Module Readiness Matrix

| Module | Phase I | Phase II | Phase III | Phase IV |
|---|---|---|---|---|
| `config.py` | REQUIRED | REQUIRED | REQUIRED | REQUIRED |
| `data_feeds/data_feed_manager.py` | REQUIRED | REQUIRED | REQUIRED | REQUIRED |
| `data_feeds/yahoo_feed.py` | REQUIRED | REQUIRED | REQUIRED | REQUIRED |
| `data_feeds/dhan_feed.py` | OPTIONAL | OPTIONAL | OPTIONAL | REQUIRED |
| `global_intelligence/global_data_ai.py` | REQUIRED | REQUIRED | REQUIRED | REQUIRED |
| `market_intelligence/market_intelligence_engine.py` | — | REQUIRED | REQUIRED | REQUIRED |
| `market_intelligence/market_monitor.py` | REQUIRED | REQUIRED | REQUIRED | REQUIRED |
| `meta_learning/meta_learning_engine.py` | — | REQUIRED | REQUIRED | REQUIRED |
| `meta_learning/regime_strategy_map.py` | — | REQUIRED | REQUIRED | REQUIRED |
| `opportunity_engine/equity_scanner.py` | — | REQUIRED | REQUIRED | REQUIRED |
| `strategy_lab/meta_strategy_controller.py` | — | REQUIRED | REQUIRED | REQUIRED |
| `strategy_lab/strategy_generator_ai.py` | — | REQUIRED | REQUIRED | REQUIRED |
| `strategy_lab/backtesting_ai.py` | — | — | REQUIRED | REQUIRED |
| `capital_risk_engine/position_sizer.py` | REQUIRED | REQUIRED | REQUIRED | REQUIRED |
| `risk_control/risk_manager_ai.py` | REQUIRED | REQUIRED | REQUIRED | REQUIRED |
| `risk_control/portfolio_allocation.py` | REQUIRED | REQUIRED | REQUIRED | REQUIRED |
| `market_simulation/monte_carlo_engine.py` | — | — | REQUIRED | REQUIRED |
| `risk_guardian/risk_guardian.py` | REQUIRED | REQUIRED | REQUIRED | REQUIRED |
| `debate_and_decision/debate_engine.py` | — | REQUIRED | REQUIRED | REQUIRED |
| `debate_and_decision/decision_engine.py` | — | REQUIRED | REQUIRED | REQUIRED |
| `execution_engine/order_manager.py` | REQUIRED | REQUIRED | REQUIRED | REQUIRED |
| `trade_monitoring/trade_monitor.py` | REQUIRED | REQUIRED | REQUIRED | REQUIRED |
| `learning_system/learning_engine.py` | — | REQUIRED | REQUIRED | REQUIRED |
| `learning_system/strategy_performance_tracker.py` | — | REQUIRED | REQUIRED | REQUIRED |
| `system_monitor/system_monitor.py` | REQUIRED | REQUIRED | REQUIRED | REQUIRED |
| `notifications/telegram_bot.py` | REQUIRED | REQUIRED | REQUIRED | REQUIRED |
| `orchestrator/master_orchestrator.py` | REQUIRED | REQUIRED | REQUIRED | REQUIRED |

---

### SR.6 Final Deployment Checklist

This checklist must be completed in sequence for every deployment, including the initial Phase I deployment.

**Code Quality:**
- [ ] All modified files pass `pylint` with score ≥ 8.5
- [ ] No `NameError` risk from class-level constants accessed without `self.` (see patterns.md)
- [ ] No hardcoded dates or test data in production code paths
- [ ] All constants accessed via `config.py` — no magic numbers in module code
- [ ] No import of production modules at test scope without mock

**Interface Preservation:**
- [ ] `GlobalDataAI.fetch(force: bool = False) -> GlobalSnapshot` signature unchanged
- [ ] `SystemMonitor.time_layer(layer_name: str)` signature unchanged
- [ ] `MasterOrchestrator.run_full_cycle() -> None` signature unchanged
- [ ] `BaseFeed.get_quote(symbol: str) -> Optional[TickerQuote]` signature unchanged
- [ ] All 4 singleton getters return same type as before change

**Constitutional Compliance:**
- [ ] No change reduces kill-switch coverage
- [ ] No change allows order submission without DecisionRecord
- [ ] No change allows order submission without valid RiskApproval
- [ ] No change breaks paper trading guard in `order_manager.submit()`
- [ ] No new thread added without entry in Thread Registry (Supplement C)

**Testing:**
- [ ] All new code paths have unit test coverage
- [ ] Integration test for the full cognitive cycle passes
- [ ] Kill-switch test passes (inject VIX=46; assert orders blocked)
- [ ] Paper trade journal test passes (submit paper order; assert CSV row)
- [ ] Timing baseline test passes (full cycle < 200ms average over 10 runs)

**Documentation:**
- [ ] `Files Modified` table in `copilot-instructions.md` updated
- [ ] Any new singleton added to `Key Singletons` section
- [ ] Any new critical interface added to `Critical Interfaces` section
- [ ] Any new protected module added to `Protected Modules` table

**Deployment Execution:**
- [ ] `git add <files>` — only modified files staged
- [ ] `git commit -m "<descriptive message>"` — message states what changed and why
- [ ] `git push origin main` — push confirmed successful
- [ ] SSH deploy command executed (full command from copilot-instructions.md)
- [ ] `docker compose ps` — both containers `Up` and `(healthy)`
- [ ] `docker logs ai-trading-brain --tail 50` — no ERROR or CRITICAL lines
- [ ] `/status` Telegram command — bot responds HEALTHY
- [ ] First post-deploy cognitive cycle completes — no ERROR in logs

---

## REVISION ADDENDUM — FINAL DOCUMENT STATUS

### Updated Summary Metrics

| Metric | Value |
|---|---|
| Document Parts | 10 (Parts I–X) |
| Engineering Supplements | 6 (A–F) |
| Engineering Invariants | 30 (ENG-INV-01 to ENG-INV-30) |
| Quality Gates | 8 (QG-01 to QG-08) |
| Implementation Phases | 4 (Phase I–IV) |
| Layer Specifications | 17 (all IIOS layers) |
| Data Object Types | 26 (full object catalogue) |
| Data Flow Records | 40 (DF-001 to DF-040) |
| Thread Registry Entries | 8 (T-001 to T-008) |
| Failure Mode Responses | 21 (FM-01 to FM-21) |
| Fail-Safe Rules | 10 |
| Scheduler Slots | 10 (hourly to weekly) |
| Per-Module Readiness Rows | 27 modules × 4 phases |
| Sequence Diagrams | 4 critical sequences |
| ASCII Architecture Diagrams | 5 |

---

### Document History

| Version | Date | Author | Changes |
|---|---|---|---|
| 0.1 | 2025-05 | Architecture Agent | Initial document skeleton |
| 0.2 | 2025-05 | Architecture Agent | Parts I–V added |
| 0.5 | 2025-05 | Architecture Agent | Parts VI–IX added |
| 0.8 | 2025-05 | Architecture Agent | Part X added |
| 1.0 | 2025-05 | Architecture Agent | Engineering Supplements A–F added; final review pass |

---

### Governing Documents

| Document | Role | Governs |
|---|---|---|
| `INVESTMENT_INTELLIGENCE_OPERATING_SYSTEM.md` | Supreme constitutional authority | All aspects of AI Trading Brain cognition and behaviour |
| `ARCHITECTURE.md` | Technical architecture reference | Layer ordering, latency thresholds, module boundaries |
| `copilot-instructions.md` | Engineering operating procedures | Change policy, deployment procedure, protected modules |
| `AI_TRADING_BRAIN_ENGINEERING_BLUEPRINT.md` | **This document** | Engineering implementation standards, readiness gates, supplement specifications |
| `config.py` | Runtime configuration authority | All tunable parameters, thresholds, mode flags |

---

### Architecture Boundary Statement

This document is the engineering bridge between the constitutional authority of the Investment Intelligence Operating System and the actual implementation of the AI Trading Brain software system.

This document governs:
- How software is structured, not what code is written
- Which modules own which responsibilities
- How data flows between modules
- What threading model applies
- What failure responses are pre-defined
- What readiness criteria gate each implementation phase

This document does not govern:
- Specific Python class implementations
- Database schema definitions
- External API contracts
- Algorithm specifics (those are governed by IIOS and ARCHITECTURE.md)

Any engineering decision that contradicts this document must first amend this document through the same change-review process required for constitutional articles.

---

*AI Trading Brain Engineering Blueprint — Version 1.0*
*Classification: Internal Engineering Architecture*
*Governed by: Investment Intelligence Operating System (Constitutional Authority)*
*Maintained by: Architecture Agent under Human Principal supervision*

---

## ENGINEERING SUPPLEMENT G — CONSTITUTIONAL TRACEABILITY MATRIX

### G.1 Overview

This supplement provides a complete traceability matrix mapping every IIOS constitutional invariant (INV-01 through INV-60) and every engineering invariant (ENG-INV-01 through ENG-INV-30) to the specific modules that enforce each invariant, and the specific test or audit that verifies enforcement.

---

### G.2 IIOS Constitutional Invariants — Module Traceability

| Invariant | Description (abbreviated) | Enforcing Modules | Verification Method |
|---|---|---|---|
| INV-01 | Evidence Primacy | `global_data_ai`, `market_intelligence_engine`, `debate_engine` | Code audit: no belief without source reference |
| INV-02 | Multi-Source Requirement | `data_feed_manager` | Unit test: single source failure triggers fallback |
| INV-03 | Contradiction Declaration | `debate_engine` (BearAgent, DevilsAdvocateAgent) | Unit test: contradicting evidence voted explicitly |
| INV-04 | Uncertainty Quantification | `position_sizer`, `decision_engine` | Assert: confidence field non-null in all decision records |
| INV-05 | No Certainty Claims | `meta_learning_engine`, `equity_scanner` | Code audit: no `confidence=1.0` assignment |
| INV-06 | Source Reliability Tracking | `data_feed_manager`, `global_data_ai` | Assert: `source` field populated in all TickerQuote objects |
| INV-07 | Multiple Independent Sources | `data_feed_manager` | Integration test: yfinance + Dhan both queried when available |
| INV-08 | Staleness Detection | `data_feed_manager`, `global_data_ai` | Unit test: stale flag set after TTL expiry |
| INV-09 | Revision Welcome | `learning_engine`, `regime_strategy_map` | Integration test: old belief overwritten by new evidence |
| INV-10 | Debate Completeness | `debate_engine` | Unit test: missing agent vote → SUSPENDED, not APPROVED |
| INV-11 | Memory Encoding Before Completion | `decision_engine`, `order_manager` | Unit test: SQLite record exists before submit() |
| INV-12 | Reasoning Chain Mandatory | `decision_engine` | Assert: `reasoning_chain` field non-null in DecisionRecord |
| INV-13 | Attribution Completeness | `learning_engine` | Assert: every TradeOutcome has decision_record_id |
| INV-14 | Approval Before Execution | `order_manager` | Integration test: submit without approval → REJECTED |
| INV-15 | Validation Before Consumption | `data_feed_manager` | Unit test: malformed quote rejected before passing to consumers |
| INV-16 | Completeness of Schema | `order_manager` (CSV journal) | Assert: all CSV columns present in every row |
| INV-17 | Encoding Before Completion | `order_manager`, `decision_engine` | Code audit: DB write before broker call |
| INV-18 | Record Integrity | SQLite (INSERT-only operations) | DB audit: no UPDATE/DELETE on closed positions |
| INV-19 | Temporal Completeness | `system_monitor`, `telemetry` | Assert: timestamp field on all telemetry records |
| INV-20 | Immutability After Commit | SQLite schema | Schema audit: no UPDATE allowed on `decisions` table |
| INV-21 | Memory Non-Alteration | `learning_engine` | Code audit: no modification of historical LearningEvents |
| INV-22 | Recall Without Modification | `learning_engine`, `strategy_performance_tracker` | Unit test: reading record does not mutate it |
| INV-23 | Risk Primacy | `risk_manager_ai`, `order_manager` | Integration test: risk gate fires before execution gate |
| INV-24 | Kill-Switch Inviolability | `risk_guardian`, `order_manager` | Unit test: set kill_switch; assert all submits return BLOCKED |
| INV-25 | Position Limit Supremacy | `risk_manager_ai` | Unit test: oversized recommendation → REJECTED |
| INV-26 | Stop-Loss Mandatory | `risk_manager_ai` | Unit test: hypothesis without stop → approval REJECTED |
| INV-27 | Drawdown Halt | `risk_guardian`, `risk_manager_ai` | Integration test: inject -2% PnL; assert kill-switch activates |
| INV-28 | VIX Kill Threshold | `risk_guardian` | Unit test: inject VIX=46; assert kill-switch activates |
| INV-29 | No Leveraged Betting | `position_sizer` | Assert: Kelly fraction capped at 0.25 max |
| INV-30 | Correlated Concentration Limit | `portfolio_allocation` | Unit test: correlated pair over limit → REJECTED |
| INV-31 | Sector Concentration Limit | `portfolio_allocation` | Unit test: sector over limit → REJECTED |
| INV-32 | Outcome-Based Learning | `learning_engine` | Integration test: outcome triggers weight update |
| INV-33 | Anti-Overfitting | `backtesting_ai`, `validation_engine` | Unit test: OOS period required before strategy activation |
| INV-34 | Anti-Catastrophic-Forgetting | `learning_engine` | Unit test: single contradicting event does not update belief |
| INV-35 | Lesson Extraction Required | `learning_engine` | Assert: every PositionLifecycleEvent produces LearningEvent |
| INV-36 | Recency Balance | `learning_engine` | Code audit: older events not entirely discarded |
| INV-37 | Learning Improves Architecture | `strategy_performance_tracker`, `meta_strategy_controller` | Integration test: poor performer eventually disabled |
| INV-38 | No Silent Learning | `learning_engine` | Assert: every learning update logged at INFO level |
| INV-39 | Explainability | `decision_engine` | Assert: human-readable reasoning_chain non-empty |
| INV-40 | Attribution Completeness | `learning_engine` | Assert: all 5 agent votes in DebateRecord |
| INV-41 | Confidence Disclosure | `decision_engine` | Assert: conviction field in DecisionRecord |
| INV-42 | Uncertainty Disclosure | `position_sizer` | Assert: uncertainty_adjustment field populated |
| INV-43 | Reasoning Persistence | SQLite `decisions` table | DB audit: reasoning_chain stored permanently |
| INV-44 | Performance Attribution | `system_monitor`, `telemetry` | Assert: LayerTimingRecord created for every layer call |
| INV-45 | Additive Evolution | `strategy_lab` | Code audit: new strategies do not delete old ones |
| INV-46 | Hypothesis Testability | `backtesting_ai` | Assert: every hypothesis has a testable entry/exit specification |
| INV-47 | Promotion Gate | `validation_engine`, `research_lab` | Integration test: strategy only promoted after all 6 stages pass |
| INV-48 | Demotion Without Prejudice | `strategy_performance_tracker` | Unit test: disabled strategy record preserved (not deleted) |
| INV-49 | Market Structure Respect | `equity_scanner` | Code audit: no trading of illiquid or suspended instruments |
| INV-50 | Human Override Reserved | `risk_guardian`, `telegram_bot` | Code audit: `/override` command only; no programmatic activation |
| INV-51 | No Automated Override | `risk_guardian` | Code audit: kill_switch.clear() only in Telegram handler |
| INV-52 | Incident Documentation | `telegram_bot`, `learning_engine` | Integration test: override triggers incident record creation |
| INV-53 | Continuity of Operation | `orchestrator` scheduler | Integration test: missed slot triggers makeup cycle |
| INV-54 | Graceful Degradation | `data_feed_manager`, `global_data_ai` | Integration test: source failure degrades gracefully, not crash |
| INV-55 | Monitoring Continuity | `trade_monitor` | Integration test: thread crash triggers alert; no silent gap |
| INV-56 | Recovery Capability | `orchestrator`, `order_manager` | Integration test: post-restart position recovery from CSV |
| INV-57 | Session Independence | `master_orchestrator` | Unit test: each cycle starts with fresh state snapshot |
| INV-58 | Shutdown Without Loss | `main.py` SIGTERM handler | Integration test: SIGTERM triggers graceful shutdown |
| INV-59 | Startup Validation | `config.py` loader | Unit test: invalid config prevents startup |
| INV-60 | Constitutional Self-Reference | Documentation only | Document audit: IIOS governs all 9 prior documents |

---

### G.3 Engineering Invariants — Module Traceability

| ENG-INV | Description (abbreviated) | Enforcing Module(s) | Verification |
|---|---|---|---|
| ENG-INV-01 | No global mutable state except singletons | All modules | Pylint / code audit |
| ENG-INV-02 | Singletons only via getter functions | `get_*()` functions in each module | Code audit: no direct instantiation |
| ENG-INV-03 | Config from config.py only | All modules | Grep: no hardcoded thresholds |
| ENG-INV-04 | No cross-layer imports (skip a plane) | Import audit | Module import graph check |
| ENG-INV-05 | Interface signatures never changed | All public methods | Type-check + regression test |
| ENG-INV-06 | Kill-switch path synchronous | `order_manager.submit()` | Timing test: < 1ms for Event.is_set() |
| ENG-INV-07 | Fail-safe default on any guard failure | `order_manager`, `risk_manager_ai` | Unit test: exception in approval → REJECTED |
| ENG-INV-08 | Approval timestamps before order | `order_manager` | Assert: `approved_at` < `submitted_at` |
| ENG-INV-09 | Conviction < 6.5 → no order | `debate_engine`, `decision_engine` | Unit test: score=6.4 → SUSPENDED |
| ENG-INV-10 | Atomic state via threading.Event | `risk_guardian` | Code audit: only Event.set/is_set used |
| ENG-INV-11 | Decision record before order | `decision_engine`, `order_manager` | Unit test: no record → submit fails |
| ENG-INV-12 | SQLite WAL mode required | DB initialisation | PRAGMA journal_mode assertion |
| ENG-INV-13 | No thread shares DB connection | All threads | Code audit: per-thread connection creation |
| ENG-INV-14 | Lock held time < 10ms | All lock holders | Lock timing instrumentation |
| ENG-INV-15 | No deadlock cycles | Thread topology | Deadlock analysis (Supplement C.4) |
| ENG-INV-16 | Background threads are daemon threads | All T-002 through T-008 | Code audit: `daemon=True` |
| ENG-INV-17 | Main thread never joins background threads | `master_orchestrator` | Code audit: no `thread.join()` calls |
| ENG-INV-18 | Learning queue non-blocking | `learning_engine` | Code audit: `put_nowait()` only |
| ENG-INV-19 | EventBus callbacks non-blocking | All EventBus subscribers | Code audit: no blocking I/O in callbacks |
| ENG-INV-20 | Feed timeout enforced | `yahoo_feed` | Code audit: `timeout=8` parameter |
| ENG-INV-21 | Stale flag propagated on source failure | `data_feed_manager` | Unit test: source exception → stale=True |
| ENG-INV-22 | Paper mode prevents all broker calls | `order_manager` | Integration test: PAPER_TRADING=True; mock broker never called |
| ENG-INV-23 | CSV journal append-only | `order_manager` | Code audit: open mode `a` only |
| ENG-INV-24 | No `.NS` suffix on index symbols | `data_feed_manager`, `orchestrator` | Integration test: NIFTY routes to ^NSEI |
| ENG-INV-25 | strategy attribute (not strategy_name) | `orchestrator._do_eod_learning` | Code audit + regression test |
| ENG-INV-26 | Docker build --no-cache required | Deployment procedure | Deploy checklist gate |
| ENG-INV-27 | Both containers healthy before done | Deployment verification | `docker compose ps` check |
| ENG-INV-28 | Evolved strategies are JSON files | `evolved_strategies/` directory | File format audit |
| ENG-INV-29 | Protected modules: no speculative edits | `risk_guardian`, `backtesting_ai`, `validation_engine` | Change control: explicit instruction required |
| ENG-INV-30 | Telemetry 90-day retention | SQLite prune job | Assert: records older than 90 days deleted on schedule |

---

## ENGINEERING SUPPLEMENT H — CROSS-REFERENCE INDEX

### H.1 Index of All Named Engineering Artefacts

This index maps every named engineering artefact in this document to the section where it is defined, to facilitate navigation and impact analysis.

| Artefact ID | Type | Name | Defined In | Primary Section |
|---|---|---|---|---|
| DF-001 to DF-040 | Data Flow | Individual module-to-module data transfers | Supplement B.1 | B — Data Flow |
| DF-001 | Data Flow | yahoo_feed → data_feed_manager (TickerQuote) | Supplement B.1 | B.1 |
| DF-005 | Data Flow | global_data_ai → master_orchestrator (GlobalSnapshot) | Supplement B.1 | B.1 |
| DF-025 | Data Flow | risk_guardian → order_manager (kill_switch_active Event) | Supplement B.1 | B.1 |
| DF-031 | Data Flow | order_manager → learning_engine (PositionLifecycleEvent) | Supplement B.1 | B.1 |
| T-001 to T-008 | Thread | System threads | Supplement C.1 | C — Concurrency |
| T-004 | Thread | RiskGuardianThread (Above Normal priority) | Supplement C.1 | C.1 |
| FM-01 to FM-21 | Failure Mode | System failure mode responses | Supplement D.1 | D — Failure Modes |
| FM-06 | Failure Mode | Kill-Switch Trigger response | Supplement D.1 | D.1 |
| FM-14 | Failure Mode | RiskGuardian Thread Death (fail-safe kill) | Supplement D.1 | D.1 |
| ENG-INV-01 to ENG-INV-30 | Engineering Invariant | All engineering invariants | Part IX | IX — Constitution |
| ENG-INV-06 | Engineering Invariant | Kill-switch path is synchronous | Part IX | IX.2 |
| ENG-INV-11 | Engineering Invariant | Decision record before order | Part IX | IX.2 |
| ENG-INV-22 | Engineering Invariant | Paper mode prevents all broker calls | Part IX | IX.2 |
| INV-01 to INV-60 | Constitutional Invariant | All IIOS invariants | IIOS Document (external) | Supplement G.2 |
| INV-24 | Constitutional Invariant | Kill-Switch Inviolability | IIOS + Supplement G.2 | G.2 |
| QG-01 to QG-08 | Quality Gate | 8 engineering quality gates | Part IX | IX.3 |
| ED-001 to ED-015 | Engineering Decision | Architecture decision register | Part I | I.7 |
| ED-010 | Engineering Decision | Background pre-warm hides latency | Part I | I.7 |
| GlobalSnapshot | Object Type | Global market context snapshot | Supplement B.2 | B.2 |
| RegimeSignal | Object Type | Regime classification with confidence | Supplement B.2 | B.2 |
| StrategyWeights | Object Type | kNN-derived strategy weight map | Supplement B.2 | B.2 |
| HypothesisList | Object Type | Ranked trading hypotheses | Supplement B.2 | B.2 |
| DecisionRecord | Object Type | Full cognitive decision record | Supplement B.2 | B.2 |
| RiskApprovalRecord | Object Type | Time-bounded risk approval | Supplement B.2 | B.2 |
| kill_switch_active | Object Type | Atomic threading.Event kill flag | Supplement B.2 | B.2 |
| `get_feed_manager()` | Singleton Getter | DataFeedManager singleton | Supplement C.2 | C.2 |
| `get_performance_tracker()` | Singleton Getter | StrategyPerformanceTracker singleton | Supplement C.2 | C.2 |
| `get_regime_strategy_map()` | Singleton Getter | RegimeStrategyMap singleton | Supplement C.2 | C.2 |
| `get_telegram_bot()` | Singleton Getter | TelegramBot singleton | Supplement C.2 | C.2 |
| Phase I Gate | Readiness Gate | Foundation and Safety phase gate | Part X | 10.1 |
| Phase II Gate | Readiness Gate | Intelligence and Learning phase gate | Part X | 10.2 |
| Phase III Gate | Readiness Gate | Optimisation and Validation phase gate | Part X | 10.3 |
| Phase IV Gate | Readiness Gate | Live Capital Transition phase gate | Part X | 10.4 |

---

### H.2 Module-to-Part Cross Reference

This table helps engineers locate the Parts of this document that govern a specific module.

| Module | Primary Part | Supplement | Related Parts |
|---|---|---|---|
| `config.py` | I (Engineering Philosophy) | — | All parts reference config |
| `data_feeds/data_feed_manager.py` | III (Module Decomposition) | A.2, B.1, C.2, D.1, F | II, V |
| `data_feeds/yahoo_feed.py` | III | A.2, B.1, D.1 | IV |
| `data_feeds/dhan_feed.py` | III | D.1, F.3 | V |
| `global_intelligence/global_data_ai.py` | II (Layer Architecture) | A.2, B.1, B.3, C.2, E | III, VI |
| `market_intelligence/market_intelligence_engine.py` | II | A.3, B.1, B.3, E | III |
| `market_intelligence/market_monitor.py` | II | A.3, C.1, E.1 | III |
| `meta_learning/meta_learning_engine.py` | II | A.4, B.1, B.5 | III |
| `meta_learning/regime_strategy_map.py` | II | A.4, B.4, C.2 | III |
| `opportunity_engine/equity_scanner.py` | II | A.5, B.1, B.3 | III |
| `strategy_lab/meta_strategy_controller.py` | II | A.6, B.1, B.4 | III |
| `strategy_lab/strategy_generator_ai.py` | II | A.6 | III |
| `strategy_lab/backtesting_ai.py` | II | A.6, G.3 | III (PROTECTED) |
| `capital_risk_engine/position_sizer.py` | II | A.7, B.1, B.3 | III, VI |
| `risk_control/risk_manager_ai.py` | II | A.8, B.1, D.2 | III, VI |
| `risk_control/portfolio_allocation.py` | II | A.8, B.1 | III |
| `market_simulation/monte_carlo_engine.py` | II | B.1 | III |
| `risk_guardian/risk_guardian.py` | II | A.9, B.1, C.2, D.1, D.2 | III (PROTECTED) |
| `debate_and_decision/debate_engine.py` | II | A.10, B.1, B.3 | III, VI |
| `debate_and_decision/decision_engine.py` | II | A.10, B.1, B.4 | III, VI |
| `execution_engine/order_manager.py` | II | A.11, B.1, C.2, D.2, F | III, VI |
| `trade_monitoring/trade_monitor.py` | II | A.12, C.1, D.1 | III |
| `learning_system/learning_engine.py` | II | A.13, B.4, B.5, C.1 | III |
| `learning_system/strategy_performance_tracker.py` | II | A.13, B.4, C.2 | III |
| `system_monitor/system_monitor.py` | II | A.14, C.2, E.1 | III, XVII |
| `notifications/telegram_bot.py` | II | A.14, C.1, F.3 | III |
| `orchestrator/master_orchestrator.py` | V (Service Architecture) | A, B.4, E, F | II, III |

---

## ENGINEERING SUPPLEMENT I — QUALITY GATE VERIFICATION PROCEDURES

### I.1 Overview

This supplement provides the detailed verification procedure for each of the 8 engineering quality gates defined in Part IX. Each gate lists the exact steps to execute, the tools to use, and the pass/fail criteria.

---

### I.2 QG-01 — Code Review Gate

The Code Review Gate applies to every pull request or direct commit that modifies a production Python file.

| Step | Action | Pass Condition |
|---|---|---|
| I-1 | Run `pylint <modified_files>` | Score ≥ 8.5 for all modified files |
| I-2 | Review for class-level constant scope bugs | No bare constant name used inside method without `self.` |
| I-3 | Check interface signatures | All public method signatures match Critical Interfaces table |
| I-4 | Verify no hardcoded values | No numeric thresholds outside `config.py` |
| I-5 | Check protected module list | No modification to protected module without documented approval |
| I-6 | Verify Files Modified table updated | `copilot-instructions.md` table contains new entry |
| I-7 | Review threading changes | Any new thread added to Thread Registry (Supplement C.1) |
| I-8 | Check singleton usage | No direct class instantiation for singleton classes |

---

### I.3 QG-02 — Unit Test Gate

| Step | Action | Pass Condition |
|---|---|---|
| II-1 | Run full unit test suite | 0 failures, 0 errors |
| II-2 | Check kill-switch unit test | inject VIX=46 → kill_switch_active set |
| II-3 | Check paper trade unit test | paper order submitted → CSV row appended |
| II-4 | Check risk approval expiry test | expired approval → REJECTED |
| II-5 | Check DecisionRecord gate test | no record → submit returns BLOCKED |
| II-6 | Check debate threshold test | score < 6.5 → SUSPENDED |
| II-7 | Check feed fallback test | primary source exception → yfinance used |
| II-8 | Check stale flag test | feed timeout → stale=True propagated |

---

### I.4 QG-03 — Integration Test Gate

| Step | Action | Pass Condition |
|---|---|---|
| III-1 | Run full cognitive cycle (paper mode) | Cycle completes in < 200ms; no exception |
| III-2 | Verify telemetry written | SQLite `telemetry` table has new row for the cycle |
| III-3 | Verify debate record written | SQLite `decisions` table has new row |
| III-4 | Simulate position open + close | `paper_trades.csv` has open + close rows |
| III-5 | Trigger learning | `PositionLifecycleEvent` processed; `strategy_performance_tracker` updated |
| III-6 | Test Telegram command | `/status` returns HEALTHY within 10 seconds |
| III-7 | Test market hours guard | Cycle at 20:00 IST → skipped with DEBUG log |
| III-8 | Test post-restart position recovery | Restart with CSV trades; assert count > 0 after EOD learning |

---

### I.5 QG-04 — Timing Baseline Gate

| Step | Action | Pass Condition |
|---|---|---|
| IV-1 | Run 10 consecutive cycles (paper mode) | Average < 172ms; no cycle > 500ms |
| IV-2 | Measure GlobalIntelligence on cache hit | < 5ms on warm cache |
| IV-3 | Measure MarketIntelligence | < 25ms average over 10 runs |
| IV-4 | Measure DebateEngine | < 60ms average over 10 runs |
| IV-5 | Measure OrderManager | < 15ms average (paper mode) |
| IV-6 | Check no lock wait > 50ms | Thread profiler shows no > 50ms contention |
| IV-7 | Confirm pre-warm hides latency | First-cycle latency = cache-hit latency |
| IV-8 | Confirm WARN/CRIT thresholds not breached | No WARN events in 10-cycle run |

---

### I.6 QG-05 — Kill-Switch Gate

| Step | Action | Pass Condition |
|---|---|---|
| V-1 | Inject VIX = 46 | `kill_switch_active.is_set()` = True within 600ms |
| V-2 | Attempt order submit with kill active | Returns BLOCKED; no CSV row written |
| V-3 | Clear kill-switch via authenticated Telegram | `/override` command clears flag |
| V-4 | Inject DayPnL = -2.1% | `kill_switch_active.is_set()` = True |
| V-5 | Inject position loss = -8.1% | `kill_switch_active.is_set()` = True |
| V-6 | Kill guardian thread | Main thread detects missed heartbeat; kill-switch pre-emptively set |
| V-7 | Attempt unauthenticated override | Unknown chat_id → command rejected; flag unchanged |
| V-8 | Verify latency | Kill detection to flag set < 100ms |

---

### I.7 QG-06 — Deployment Verification Gate

| Step | Action | Pass Condition |
|---|---|---|
| VI-1 | `docker compose build --no-cache` | Build completes without error |
| VI-2 | `docker compose down` | Both containers stopped cleanly |
| VI-3 | `docker compose up -d` | Both containers start |
| VI-4 | `docker compose ps` after 8s | Both containers `Up ... (healthy)` |
| VI-5 | `docker logs ai-trading-brain --tail 50` | No ERROR or CRITICAL lines |
| VI-6 | `docker exec ai-trading-brain python main.py --status` | Exit code 0; output HEALTHY |
| VI-7 | `curl http://localhost:8501/healthz` | HTTP 200 OK |
| VI-8 | `/status` Telegram command | Bot responds HEALTHY |

---

### I.8 QG-07 — Performance Analytics Gate (Phase III+)

| Step | Action | Pass Condition |
|---|---|---|
| VII-1 | 30-day paper trading report | Win rate ≥ 45% (trending toward 50% target) |
| VII-2 | 60-day paper trading report | Win rate ≥ 48% |
| VII-3 | 90-day paper trading report | Win rate ≥ 50%; Sharpe > 0.8; MaxDD < 15% |
| VII-4 | Walk-forward test (all active strategies) | OOS Sharpe > 0.5 for each strategy |
| VII-5 | Drawdown analysis | No single month > 8% drawdown |
| VII-6 | Strategy concentration check | No single strategy > 40% of total trades |
| VII-7 | Regime distribution check | Active strategies cover ≥ 3 regime types |
| VII-8 | Monte Carlo stress test | ≥ 12/14 scenarios pass at 95% confidence |

---

### I.9 QG-08 — Phase IV Live Capital Readiness Gate

| Step | Action | Pass Condition |
|---|---|---|
| VIII-1 | All Phase I, II, III gates pass | No open failures |
| VIII-2 | 90-day paper period complete | Date arithmetic confirms ≥ 90 days |
| VIII-3 | Dhan authentication confirmed | `dhan_feed.authenticate()` returns success |
| VIII-4 | Broker sandbox order test | Order reaches sandbox; fill confirmed within 5s |
| VIII-5 | Dual-mode toggle test | PAPER_TRADING toggle works in both directions |
| VIII-6 | Position size audit | Live-capital sizes reviewed and approved by Human Principal |
| VIII-7 | Written Human Principal approval | Signed authorisation document on record |
| VIII-8 | Post-go-live monitoring plan | First 5 live trading days: Human Principal reviews every cycle |

---

## ENGINEERING SUPPLEMENT J — ENGINEERING DECISION LOG EXTENSION

### J.1 Additional Architecture Decisions

This supplement extends the Engineering Decision Register from Part I with decisions made during the supplement development phase.

| Decision ID | Decision | Context | Alternatives Rejected | Rationale |
|---|---|---|---|---|
| ED-016 | Thread-per-concern, not async/await | Python 3.14 available, but async complicates kill-switch atomicity | asyncio event loop | `threading.Event.is_set()` is atomic; asyncio requires await which introduces yield points; trading safety takes priority |
| ED-017 | SQLite with WAL mode, not PostgreSQL | Single-process deployment on single VPS | PostgreSQL | No network hop; WAL mode allows concurrent reads; ACID guarantees preserved; zero-ops overhead |
| ED-018 | CSV journal as secondary record, not primary | `paper_trades.csv` is the recovery source for post-restart state | SQLite only | CSV is human-readable; survives schema migrations; usable in spreadsheet tools for Human Principal review |
| ED-019 | APScheduler for scheduling, not cron | Scheduling within Python process; no external dependencies | OS cron, celery | APScheduler integrates with Python threading model; cron requires separate process management; celery is overly complex for this use case |
| ED-020 | Telegram for human interface, not web dashboard | Dashboard is read-only observability; commands require human authentication | REST API endpoint | Telegram provides end-to-end authentication; no port exposure; async push notifications; already implemented |
| ED-021 | yfinance as primary fallback (not Dhan) | Dhan data API returns 451 error (geoblocked on some VPS providers) | Dhan as primary | yfinance is reliable, free, and works regardless of jurisdiction; Dhan remains primary where available |
| ED-022 | `strategy` attribute (not `strategy_name`) in PositionLifecycleEvent | Bug discovered in orchestrator._do_eod_learning | Both names existed transiently | `strategy` is the canonical attribute name set by OrderManager; consistency with object definition takes precedence |
| ED-023 | Index symbols use bare names without `.NS` suffix | NIFTY routes to `^NSEI`; `.NS` suffix is only for equity instruments | Apply `.NS` universally | Bare names are correct for index instruments in yfinance; applying `.NS` to NIFTY returns no data |
| ED-024 | 30-second conviction validity window | Balance between staleness risk and retry overhead | 15 seconds (too tight), 60 seconds (too stale) | 30 seconds allows OrderManager to complete submission; market moves materially in > 60 seconds |
| ED-025 | Kill-switch as `threading.Event`, not boolean flag | Atomicity required; GIL does not guarantee boolean read/write atomicity across threads | Boolean flag, queue | `threading.Event` is explicitly designed for this use case; is_set() is atomic; well-understood semantics |

---

## ENGINEERING SUPPLEMENT K — STARTUP AND SHUTDOWN ENGINEERING

### K.1 Startup Sequence

The AI Trading Brain follows a strict startup sequence. Components must initialise in order; a failure in any step causes the process to exit with a non-zero code rather than attempting degraded startup.

| Step | Component | Action | Success Condition | Failure Action |
|---|---|---|---|---|
| S-01 | Config | Load and validate `config.py` | All required keys present; checksum computable | Exit code 1; log CRITICAL: CONFIG_VALIDATION_FAILED |
| S-02 | Logging | Initialise log handlers; set rotation | Log file writable; rotation configured | Exit code 1; print to stderr: LOGGING_INIT_FAILED |
| S-03 | SQLite | Create/open `trading_brain.db`; set WAL mode | WAL mode confirmed; schema tables present | Exit code 1; log CRITICAL: DATABASE_INIT_FAILED |
| S-04 | Data Feed Manager | Instantiate singleton; test primary feed | At least one feed returns valid quote | Log WARNING; continue with stale risk |
| S-05 | Risk Guardian | Start T-004; confirm poll cycle running | First poll cycle logged within 1s | Exit code 1; log CRITICAL: GUARDIAN_START_FAILED |
| S-06 | System Monitor | Initialise timing subsystem; load overrides | Override dict loaded; telemetry table writable | Exit code 1; log CRITICAL: MONITOR_INIT_FAILED |
| S-07 | Order Manager | Initialise; recover positions from CSV | Position count logged (0 is valid) | Exit code 1; log CRITICAL: ORDER_MANAGER_INIT_FAILED |
| S-08 | Trade Monitor | Start T-005; confirm heartbeat | Heartbeat logged within 5s | Exit code 1; log CRITICAL: TRADE_MONITOR_START_FAILED |
| S-09 | Market Monitor | Start T-003; confirm initial scan | Initial scan completes within 30s | Log WARNING; continue; alert Telegram |
| S-10 | Global Data AI | Warm cache; pre-warm thread started | GlobalSnapshot in cache | Log WARNING; continue with stale |
| S-11 | Learning Engine | Start T-007; drain startup queue | Startup queue drained | Log WARNING; continue |
| S-12 | Telegram Bot | Start T-006; send startup notification | Bot connected; startup message sent | Log WARNING; continue without notifications |
| S-13 | Scheduler | Register all 10 scheduled slots | All slots registered; first slot scheduled | Exit code 1; log CRITICAL: SCHEDULER_START_FAILED |
| S-14 | Startup Banner | Log startup banner with version + mode | Banner visible in log | N/A — informational only |

---

### K.2 Shutdown Sequence

Graceful shutdown is triggered by SIGTERM (Docker stop) or manual keyboard interrupt. The SIGTERM handler in `main.py` coordinates the shutdown sequence.

| Step | Component | Action | Timeout | Failure Action |
|---|---|---|---|---|
| SD-01 | Scheduler | Cancel all pending scheduled jobs | 5s | Force cancel; log WARNING |
| SD-02 | Market Monitor | Set stop flag on T-003; join | 3s | Log WARNING: MARKET_MONITOR_SHUTDOWN_TIMEOUT |
| SD-03 | Cognitive Cycle | Wait for current cycle to complete | 30s | Log WARNING: CYCLE_INTERRUPTED |
| SD-04 | Trade Monitor | Set stop flag on T-005; join | 3s | Log WARNING: TRADE_MONITOR_SHUTDOWN_TIMEOUT |
| SD-05 | Learning Queue | Drain learning queue to disk | 10s | Log WARNING: LEARNING_QUEUE_NOT_FULLY_DRAINED |
| SD-06 | SQLite | Flush WAL; close connections | 5s | Log WARNING: DATABASE_CLOSE_TIMEOUT |
| SD-07 | Telegram Bot | Send shutdown notification; stop T-006 | 5s | Log INFO (notification optional) |
| SD-08 | Risk Guardian | Clear kill-switch (not triggered); stop T-004 | 2s | Log WARNING: GUARDIAN_SHUTDOWN_TIMEOUT |
| SD-09 | Log Flush | Flush all log handlers | 2s | N/A |
| SD-10 | Exit | `sys.exit(0)` | N/A | Exit code 1 if any critical step failed |

---

### K.3 Process Identity and PID Management

| Attribute | Implementation |
|---|---|
| PID file | `data/trading_brain.pid` written at S-14 (startup banner) |
| Duplicate process detection | On startup S-01, check if `trading_brain.pid` exists; if process with that PID is running → exit code 1 with DUPLICATE_PROCESS_DETECTED |
| PID file cleanup | Deleted at SD-09 (log flush step) |
| Status command | `main.py --status` reads PID file; checks process liveness; returns HEALTHY or NOT_RUNNING |
| Docker restart policy | `restart: unless-stopped` in `docker-compose.yml` ensures automatic restart after crash |

---

### K.4 Health Check Engineering

The health check endpoint (used by Docker's `HEALTHCHECK` instruction) evaluates multiple system dimensions and returns a single binary result.

| Health Dimension | Check Method | Healthy Condition |
|---|---|---|
| Process alive | PID file exists; process responsive | PID exists; `kill -0 <pid>` returns 0 |
| Risk Guardian alive | Guardian heartbeat age | Last heartbeat < 2 seconds ago |
| Trade Monitor alive | Monitor heartbeat age | Last heartbeat < 10 seconds ago |
| SQLite writable | Write test row to `health_check` table | Write succeeds; row deleted after check |
| Feed responsive | `data_feed_manager.get_quote("NIFTY")` | Returns quote without exception |
| Scheduler active | Next scheduled job exists | APScheduler has at least one pending job |
| Config checksum | Compute and compare | Matches startup checksum |

**Health check output**: `python main.py --health` prints `HEALTHY` and returns exit code 0 if all dimensions pass; prints `UNHEALTHY: <reason>` and returns exit code 1 if any fail. Docker interprets exit code as health result.

---

## ENGINEERING SUPPLEMENT L — OBSERVABILITY ENGINEERING

### L.1 Observability Pillars

The AI Trading Brain implements observability across three classical pillars: metrics, logs, and traces. Each pillar serves a distinct diagnostic purpose.

| Pillar | Implementation | Storage | Retention | Consumer |
|---|---|---|---|---|
| **Metrics** | Layer timing records; P&L metrics; strategy win rates | SQLite `telemetry` table | 90 days | Streamlit dashboard; Telegram `/perf` command |
| **Logs** | Structured text logs with level, timestamp, layer, message | `logs/trading_brain.log` (rotated daily) | 30 days | Human Principal; incident investigation |
| **Traces** | Decision traces: hypothesis → debate → decision → order (linked by ID chain) | SQLite `decisions` + `orders` tables | 365 days (permanent) | Audit; regulatory; learning |

---

### L.2 Log Level Conventions

| Level | When Used | Example |
|---|---|---|
| DEBUG | Internal state transitions; cache hits; skip conditions (market closed, hypothesis suspended) | `"Cycle skipped: market hours guard (20:00 IST)"` |
| INFO | Every significant state change; startup/shutdown; learning events; regime changes | `"Regime changed: TRENDING_BULLISH (confidence=0.82)"` |
| WARNING | Degraded operation; stale data; near-threshold conditions; missed schedule slots | `"GlobalSnapshot stale: age=6min, using cached with quality_score=0.3"` |
| ERROR | Recoverable failure; thread crash (auto-restart attempted); feed failure with fallback | `"Primary feed error: timeout; falling back to yfinance"` |
| CRITICAL | Unrecoverable failure; kill-switch activation; startup validation fail; guardian death | `"Kill-switch activated: DayPnL=-2.1% exceeds -2.0% threshold"` |

---

### L.3 Telemetry Record Taxonomy

| Record Type | Table | Key Columns | Written By | Read By |
|---|---|---|---|---|
| Layer timing | `telemetry` | layer_name, duration_ms, warn_breached, crit_breached, cycle_id | `system_monitor` | Dashboard; `/perf` Telegram |
| Decision record | `decisions` | decision_id, hypothesis_id, conviction, approved, reasoning_chain, decided_at | `decision_engine` | Learning engine; audit |
| Order record | `orders` | order_id, decision_id, instrument, direction, size, status, fill_price, pnl | `order_manager` | Learning engine; dashboard |
| Learning event | `learning_events` | event_id, trade_id, strategy_id, outcome, lesson, recorded_at | `learning_engine` | Strategy tracker; MetaLearning |
| System alert | `alerts` | alert_id, severity, layer, message, acknowledged, timestamp | `system_monitor` | Dashboard; Telegram |
| Health check | `health_checks` | check_id, dimension, result, latency_ms, checked_at | `main.py --health` | Docker HEALTHCHECK |
| Regime record | `regime_history` | regime_id, regime_type, confidence, detected_at, superseded_at | `market_intelligence_engine` | MetaLearning; analytics |
| Strategy performance | `strategy_stats` | strategy_id, win_rate, total_trades, avg_pnl, sharpe, last_updated | `strategy_performance_tracker` | Dashboard; `/learn` Telegram |

---

### L.4 Dashboard Engineering

The Streamlit dashboard runs in the `trading-dashboard` container and reads the `./data` volume in read-only mode. It never writes to any shared state.

| Dashboard Section | Data Source | Refresh Rate | Key Metrics Shown |
|---|---|---|---|
| System Health | `telemetry` table (last 1h) | 30s | Layer latencies; WARN/CRIT counts; cycle frequency |
| P&L Summary | `orders` table + `paper_trades.csv` | 60s | Day P&L; MTD P&L; open position count; win rate today |
| Strategy Performance | `strategy_stats` table | 5m | Win rate per strategy; trade count; Sharpe; active/disabled status |
| Recent Decisions | `decisions` table (last 20) | 30s | Hypothesis; conviction; approved/suspended; agent vote breakdown |
| Regime History | `regime_history` table (last 30 days) | 5m | Regime sequence; confidence; duration |
| Learning Log | `learning_events` table (last 50) | 5m | Lessons extracted; strategy weight updates; belief changes |
| Alert Feed | `alerts` table (last 24h) | 15s | Severity; layer; message; acknowledgement status |

| Pillar | Status |
|---|---|
| Metrics (timing, P&L, win rate) | Implemented — SQLite telemetry, 90-day retention |
| Logs (structured, levelled) | Implemented — daily rotation, 30-day retention |
| Traces (decision chain) | Implemented — permanent SQLite storage, linked by decision_id |
| Dashboard (Streamlit) | Implemented — separate container, read-only data access |
| Alerts (Telegram push) | Implemented — async delivery; 3-attempt retry with backoff |
| Health check (Docker) | Implemented — 7-dimension check; binary healthy/unhealthy result |
