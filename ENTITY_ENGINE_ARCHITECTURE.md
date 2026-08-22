# ENTITY ENGINE ARCHITECTURE

**Document Series:** Investment Intelligence Operating System — Engineering Document Library
**Document Number:** 8 of 10
**Document Class:** Entity Engineering Architecture
**Status:** Authoritative
**Version:** 1.0.0
**Date:** 2026-07-02
**Authors:** Human Principal / Engineering Foundation
**Governs:** Every entity type, entity component, entity lifecycle, entity service, and entity governance policy in the IIOS

---

## Scope and Authority

This document is the authoritative engineering design for the Entity Engine of the Investment Intelligence Operating System. The Entity Engine is the component responsible for creating, managing, validating, maintaining, evolving, indexing, searching, versioning, and governing every entity that the system recognises and works with.

Entities are the fundamental nouns of the IIOS domain. Every meaningful object that the system tracks — from a trading strategy to a market regime, from an AI agent to a risk threshold, from a single order to the entire portfolio — is an entity. Without a well-designed Entity Engine, the system has no stable foundation for knowledge, decisions, or audit.

This document does **NOT** contain:
- Source code or implementation
- Database schema definitions
- ORM or query design
- Prompt engineering

This document **DOES** contain:
- The philosophical foundation of entities in the IIOS
- The complete 13-level entity hierarchy
- Design of all 15 entity engine components
- The complete 12-stage entity lifecycle with diagrams
- All 11 entity services with full specifications
- The entity identity framework (global IDs, aliases, identity resolution)
- The entity quality framework with scoring models
- Entity governance policies and ownership structures
- 75 mandatory Entity Constitution rules
- A comprehensive Entity Readiness Checklist

---

## Parent Documents

| Document | Authority |
|---|---|
| `INVESTMENT_INTELLIGENCE_OPERATING_SYSTEM.md` | Supreme constitutional authority |
| `AI_TRADING_BRAIN_ENGINEERING_BLUEPRINT.md` | Engineering design bridge |
| `ENGINEERING_STANDARDS.md` | Mandatory engineering standards |
| `CORE_FRAMEWORK_ARCHITECTURE.md` | Core framework and base classes |
| `DATABASE_PERSISTENCE_ARCHITECTURE.md` | Persistence design authority |
| `KNOWLEDGE_ENGINE_ARCHITECTURE.md` | Knowledge design authority |

---

## Entity Engine Position in the IIOS

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                  IIOS SYSTEM ARCHITECTURE                                    │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  L17 ControlTower       │  L15-16 Research + Validation             │   │
│  │  L13-14 Learning + Analytics  │  L10-12 Decision + Execution        │   │
│  │  L3-9  Data, Analysis, Strategy, Risk                                │   │
│  └─────────────────────────────┬────────────────────────────────────────┘   │
│                                │ ALL LAYERS USE ENTITIES                    │
│  ┌─────────────────────────────▼────────────────────────────────────────┐   │
│  │                   ENTITY ENGINE  (This document)                     │   │
│  │                                                                      │   │
│  │  ┌────────────┐  ┌───────────┐  ┌────────────┐  ┌────────────────┐ │   │
│  │  │  Registry  │  │ Validator │  │  Lifecycle │  │  Search/Index  │ │   │
│  │  └────────────┘  └───────────┘  └────────────┘  └────────────────┘ │   │
│  │  ┌────────────┐  ┌───────────┐  ┌────────────┐  ┌────────────────┐ │   │
│  │  │  Identity  │  │ Versioner │  │  History   │  │   Governance   │ │   │
│  │  └────────────┘  └───────────┘  └────────────┘  └────────────────┘ │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                │                                             │
│  ┌─────────────────────────────▼────────────────────────────────────────┐   │
│  │              ENTITY STORES (via DATABASE_PERSISTENCE)                │   │
│  │   trading_brain.db │ knowledge.db │ learning.db │ configuration.db  │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Entity Engine Data Flow

```
External World             IIOS Internal
(Markets, Exchanges,  ──►  Information Layer
 Brokers, Events)          │
                           ▼
                      [Entity Discovery]
                           │
                           ▼
                      [Entity Validation] ──► REJECT ──► Rejection Archive
                           │
                           ▼
                      [Entity Creation]
                           │
                      ┌────┴────────────────────────────────┐
                      ▼                                     ▼
               [Entity Registry]                    [Entity Identity]
               [Entity Catalog]                     [Alias Resolution]
               [Entity Index]                       [Duplicate Detection]
                      │                                     │
                      └──────────────┬──────────────────────┘
                                     ▼
                            [Entity Lifecycle Manager]
                                     │
                          ┌──────────┼──────────┐
                          ▼          ▼          ▼
                     [Update]    [Version]  [Merge/Split]
                          │          │          │
                          └──────────┼──────────┘
                                     ▼
                          [Entity Audit Manager]
                                     │
                                     ▼
                            [Entity Governance]
                                     │
                                     ▼
                         All 17 IIOS Layers (consumers)
```

---

## Table of Contents

- [Part I — Entity Engine Philosophy](#part-i)
- [Part II — Entity Architecture](#part-ii)
- [Part III — Entity Components](#part-iii)
- [Part IV — Entity Lifecycle](#part-iv)
- [Part V — Entity Services](#part-v)
- [Part VI — Entity Identity Framework](#part-vi)
- [Part VII — Entity Quality](#part-vii)
- [Part VIII — Entity Governance](#part-viii)
- [Part IX — Entity Constitution](#part-ix)
- [Part X — Entity Readiness Checklist](#part-x)
- [Document Footer](#document-footer)
- [Supplement A — Entity Type Catalogue](#supplement-a)
- [Supplement B — Entity Component Interface Reference](#supplement-b)
- [Supplement C — Entity Lifecycle State Machine](#supplement-c)
- [Supplement D — Entity Quality Scoring Reference](#supplement-d)
- [Supplement E — Entity Identity Patterns](#supplement-e)
- [Supplement F — Entity Governance Decision Records](#supplement-f)
- [Supplement G — Entity Anti-Pattern Reference](#supplement-g)

---
## PART I — ENTITY ENGINE PHILOSOPHY

### 1.1 What Is an Entity?

An entity is the most fundamental architectural concept in the IIOS. It is a **named, uniquely identified, persistent object in the domain that has a defined lifecycle and meaningful behaviour**.

Entities are the nouns of the system's domain language — the objects that matter, that the system creates, tracks, modifies, and reasons about. Every decision the IIOS makes is ultimately about entities: which strategy to activate, which order to submit, how much capital to allocate to which portfolio, whether a specific risk threshold entity has been breached.

Without a rigorous definition of what an entity is — and what it is not — the system has no stable foundation for knowledge representation, audit, or governance.

---

### 1.2 Distinguishing Foundational Concepts

Understanding what separates entities from related concepts is essential to understanding why the Entity Engine is architecturally distinct.

**Object:**

An object is the most general computational concept — any data structure in memory. Objects are transient. They are created, used, and garbage-collected. An object has no inherent identity beyond its memory address. The same data in two different objects are not the same thing — they are two copies.

In the IIOS, objects are the in-memory representations of entities. They are ephemeral. They are rebuilt from the entity store on each access. They carry the entity's current state but are not the entity itself.

**Entity:**

An entity is a domain concept with **persistent identity that transcends any specific in-memory representation**. A `Strategy` entity exists regardless of whether the system is running. Its identity (`strategy_id`) uniquely identifies it across all time, across all restarts, and across all representations. Two `Strategy` objects with the same `strategy_id` represent the same entity — they are not two different things.

Key properties that distinguish an entity from a mere object:
- **Persistent identity:** UUID4 that never changes after creation
- **Persistent lifecycle:** The entity exists before, during, and after any system session
- **Mutable state:** Entities change over time; their state is tracked across versions
- **Audit trail:** Every change to an entity is recorded permanently

**Information:**

Information is structured data — a measurement, a price, a rate, a volume. Information is typically immutable after creation (a closing price does not change) and has no lifecycle beyond its validity window. Information is the raw material from which entities are populated and updated.

Information flows into the entity engine as inputs (updating entity attributes), not as entities themselves. A NIFTY50 daily bar is information. The NIFTY50 index symbol is an entity (specifically, a Market Entity). The distinction is critical: information does not have a lifecycle; it has a validity window. Entities have a lifecycle; they are born, they evolve, they retire.

**Knowledge:**

Knowledge is validated, structured understanding derived from information and entity behaviour over time. Knowledge exists about entities (e.g., "this strategy has a 61% win rate in BULL regimes") but is not itself an entity in the traditional sense. Knowledge records are a specialised entity subtype (Knowledge Entity) because they have identity, lifecycle, and versioning — but they are semantically distinct from operational entities like orders and strategies.

**Relationship:**

A relationship is a defined connection between two entities. Relationships are first-class objects in the IIOS: they are named, typed, directional, and versioned. A `Strategy GENERATES Hypothesis` is not just a foreign key — it is a domain fact about how these two entities are connected.

Relationships are not entities themselves. They are edge records in the entity graph. However, complex relationships that carry significant domain meaning (e.g., `Portfolio CONTAINS Position`) may be promoted to relationship entities with their own identity and lifecycle.

**Event:**

An event is a discrete, timestamped occurrence that changes the state of one or more entities. Events are immutable facts about what happened. An event does not have a lifecycle — it exists permanently, exactly as it was when it occurred. Events are the primary mechanism by which entity state changes are recorded and audited.

Events and entities interact in a fundamental way: every entity state change is recorded as an event. The complete history of an entity's state is reconstructable from its event stream.

**Identity:**

Identity is the property that makes an entity the same entity across time, restarts, and representations. In the IIOS, identity is established by the `entity_id` (UUID4) assigned at entity creation. This ID never changes. It is the entity's permanent, system-wide, time-invariant identifier.

Identity is what makes the question "is this the same order we submitted yesterday?" answerable with certainty. Without stable identity, every restart would lose continuity with all prior state.

**Instance:**

An instance is a specific realisation of an entity at a specific point in time. The `Strategy` entity "MomentumBreakoutV3" has existed across 300 cycles. At any given moment, the current instance is the entity in its present state. At any point in history, a historical instance (a specific version) is the entity as it was at that time.

The Entity Engine manages both the current instance (served from cache) and all historical instances (served from the version store).

**Value Object:**

A value object is a domain concept that is defined entirely by its value — it has no identity beyond what it contains. A price (₹21,450.50), a percentage (0.61), a date (2026-07-02) — these are value objects. Two value objects with the same value are equivalent and interchangeable.

Value objects are used as the attributes of entities. They are not tracked independently by the Entity Engine. They are validated when entities are created or updated.

**Aggregate:**

An aggregate is a cluster of entities and value objects treated as a single unit for data consistency. The `Portfolio` aggregate, for example, contains the `Portfolio` entity plus all its `Position` entities. Changes to the aggregate are applied atomically — you cannot modify a `Position` without going through the `Portfolio` aggregate root.

Aggregate design is critical for maintaining business invariants. The Entity Engine respects aggregate boundaries: writes to any entity within an aggregate are routed through the aggregate root to ensure consistency.

---

### 1.3 Why Entities Are the Foundation of the IIOS

Every intelligent function in the IIOS ultimately operates on entities:

**Decision-making** requires entities: which Strategy, targeting which Symbol, producing which Hypothesis, evaluated by which Agents, resulting in which Order.

**Risk management** requires entities: which Portfolio, holding which Positions, relative to which RiskThreshold, with what stop-loss and target.

**Learning** requires entities: which Trade taught which LearningRecord, associated with which Strategy and Regime, contributing what evidence to which Knowledge record.

**Audit** requires entities: which Order was created by which Cycle, in response to which DecisionRecord, approved by which Agent ensemble, executed at which price.

Remove entities from any of these functions, and the function becomes stateless, unauditable, and unable to learn. The Entity Engine is therefore not just a data management component — it is the identity infrastructure that makes all higher-order system intelligence possible.

---

### 1.4 Entity Lifecycle Philosophy

Entities are not created and forgotten — they are born, they evolve, they age, and they retire. This lifecycle is not incidental; it is the central mechanism by which the system accumulates knowledge about its own domain.

**Birth:** An entity comes into existence when a domain event demands it. A new strategy variant is created by StrategyLab. A new order is created when a hypothesis is approved. A new trade is created when an order is filled.

**Evolution:** Entities change state in response to events. A position's unrealised P&L updates every cycle. A strategy's win rate improves as trades close. An agent's accuracy calibration shifts as predictions are evaluated against outcomes.

**Retirement:** Entities reach the end of their active life. A strategy is retired when it consistently underperforms. An order is closed when filled or cancelled. A position is closed when the trade exits.

**Permanence:** In the IIOS, no entity is ever destroyed. Retired entities are archived but remain permanently accessible. This is not a technical convenience — it is a governance requirement. The audit trail of every decision depends on the permanent accessibility of every entity that participated in that decision.

---

### 1.5 The Entity Engine's Role

The Entity Engine is the central steward of all entities in the IIOS. It has five primary roles:

| Role | Description |
|---|---|
| **Registrar** | Maintains the authoritative record of every entity that exists or has ever existed in the system |
| **Validator** | Enforces entity invariants at creation and update time |
| **Versioner** | Captures every state change as an immutable version record |
| **Identity resolver** | Answers the question "which entity is this?" when multiple identifiers, aliases, or external IDs might refer to the same entity |
| **Governor** | Enforces quality standards, ownership rules, and compliance requirements across the entity population |

---

### 1.6 Design Principles of the Entity Engine

| Principle | Description |
|---|---|
| **Identity first** | Every entity has exactly one canonical identifier before any other attribute is assigned |
| **Lifecycle enforced** | Every entity's state transitions are governed by a defined state machine |
| **Immutable history** | Entity history is append-only — no past state is ever deleted or rewritten |
| **Aggregate consistency** | Entity writes within an aggregate boundary are atomic and consistent |
| **Single owner** | Every entity has exactly one responsible owner at any given time |
| **Searchable by design** | Every entity is indexed for discovery at creation time |
| **Audit by default** | Every state change generates an audit record without explicit action by the changing component |
| **Quality measured** | Every entity carries a quality score computed from defined dimensions |

---

## PART II — ENTITY ARCHITECTURE

### 2.1 Entity Hierarchy Overview

The IIOS defines 13 categories of entities organised in a hierarchy. Each category has a defined set of entity types, lifecycle rules, and governance policies.

```
ROOT ENTITY (abstract base for all entities)
│
├── FINANCIAL ENTITY
│   ├── Order
│   ├── Trade
│   ├── Position
│   └── Fill
│
├── MARKET ENTITY
│   ├── Symbol
│   ├── Index
│   ├── Sector
│   └── MarketSession
│
├── ECONOMIC ENTITY
│   ├── Regime
│   ├── MacroIndicator
│   └── EconomicEvent
│
├── CORPORATE ENTITY
│   ├── Company
│   ├── FIIParticipant
│   └── ListedSecurity
│
├── PORTFOLIO ENTITY
│   ├── Portfolio
│   ├── Allocation
│   └── BudgetEnvelope
│
├── EXECUTION ENTITY
│   ├── ExecutionRecord
│   ├── SlippageRecord
│   └── BrokerSession
│
├── RISK ENTITY
│   ├── RiskThreshold
│   ├── KillSwitch
│   ├── DrawdownRecord
│   └── StressScenario
│
├── KNOWLEDGE ENTITY
│   ├── KnowledgeRecord
│   ├── KnowledgePattern
│   ├── KnowledgeRule
│   └── KnowledgeFact
│
├── AI ENTITY
│   ├── Agent
│   ├── AgentOpinion
│   ├── Hypothesis
│   └── DecisionRecord
│
├── SYSTEM ENTITY
│   ├── Cycle
│   ├── ScheduledJob
│   ├── DataFeed
│   └── SystemConfiguration
│
├── REFERENCE ENTITY
│   ├── Calendar
│   ├── ExpirySchedule
│   ├── TradingHoliday
│   └── SymbolMaster
│
├── DERIVED ENTITY
│   ├── LearningRecord
│   ├── BacktestSnapshot
│   └── WalkForwardResult
│
└── (StrategyLab entities — cross-cutting)
    ├── Strategy
    ├── Hypothesis (also AI Entity)
    ├── EvolvedVariant
    └── BacktestResult
```

---

### 2.2 Root Entity

**Definition:** The Root Entity is the abstract base from which all concrete entity types are derived. It defines the universal set of fields and behaviours that every entity must have.

**Root Entity fields (every entity has these):**

| Field | Type | Description |
|---|---|---|
| `entity_id` | UUID4 | Globally unique, permanent identifier |
| `entity_type` | EntityType enum | The specific entity type |
| `entity_category` | EntityCategory enum | One of the 13 categories |
| `display_name` | string | Human-readable label |
| `status` | EntityStatus enum | Current lifecycle state |
| `version` | int | Monotonically increasing version number |
| `created_at` | UTC datetime | Creation timestamp |
| `created_by` | string | Service or actor that created the entity |
| `updated_at` | UTC datetime | Last update timestamp |
| `updated_by` | string | Service or actor that last updated |
| `owner_id` | string | Current responsible owner |
| `is_active` | bool | Whether the entity is in an active lifecycle state |
| `is_deleted` | bool | Soft-delete flag (never physically deleted) |
| `metadata` | JSON | Type-specific additional metadata |
| `tags` | List[string] | Searchable tags |
| `quality_score` | float | Computed quality score (0.0–1.0) |
| `schema_version` | int | Schema version at which this entity was created |
| `lineage_id` | UUID4 | Reference to Entity Lineage record |

---

### 2.3 Financial Entity

**Purpose:** Financial entities represent the primary financial transactions and positions of the trading system. They are the most critical entities from a governance and audit perspective — every financial entity is subject to permanent retention and full audit.

**Financial entity types:**

| Entity Type | Description | Lifecycle |
|---|---|---|
| `Order` | A request to buy or sell a financial instrument | PENDING → SUBMITTED → FILLED/REJECTED/CANCELLED |
| `Trade` | A confirmed financial transaction (filled order pair — entry and exit) | OPEN → PARTIAL_CLOSE → CLOSED |
| `Position` | The current holding of an instrument | OPENING → OPEN → REDUCING → CLOSED |
| `Fill` | The specific price and quantity of a single execution event | Created on fill; immutable |

**Financial entity invariants (all must be true at all times):**
- An Order cannot be both FILLED and CANCELLED
- A Trade cannot have `exit_price` set while `status = OPEN`
- A Position's `quantity` must equal the sum of all associated Open Fill quantities
- A Fill's `filled_price` is immutable after creation
- Total open position value cannot exceed `RiskThreshold.max_portfolio_exposure`

**Financial entity governance:**
- Owned exclusively by the OrderManager (orders, fills) and TradeMonitor (trades, positions)
- Read by all layers through repository interfaces
- Permanently retained — no archival cutoff
- Full audit event for every state change

---

### 2.4 Market Entity

**Purpose:** Market entities represent the instruments, indices, sectors, and market sessions that the system operates within. They are reference entities — they are defined by external market structure, not by the system's decisions.

**Market entity types:**

| Entity Type | Description | Identity basis |
|---|---|---|
| `Symbol` | A tradeable financial instrument | NSE symbol string (e.g., `TATASTEEL`) |
| `Index` | A market index tracked by the system | Standard index code (e.g., `^NSEI`) |
| `Sector` | A sector grouping of symbols | Sector name (e.g., `BANKING`, `IT`) |
| `MarketSession` | A specific trading day's market session | Date (YYYY-MM-DD) + market identifier |

**Symbol entity enrichment:** A Symbol entity carries not just the NSE symbol string but a rich set of attributes derived from the reference data layer:
- Exchange: NSE, BSE, NSE_FO
- Instrument type: EQ, FUT, OPT
- ISIN code
- Company name
- Sector classification
- Index membership list
- Market cap tier (LARGE, MID, SMALL)
- Lot size (for derivatives)
- Tick size

**Market entity lifecycle:** Market entities are created at reference data load time and remain ACTIVE for the duration of the system's operation. A Symbol may become SUSPENDED (trading halted) or DELISTED (no longer tradeable). It is never deleted — historical trades referencing it must remain auditable.

---

### 2.5 Economic Entity

**Purpose:** Economic entities represent high-level macroeconomic conditions and events that contextualise all market and strategy behaviour.

**Economic entity types:**

| Entity Type | Description | Examples |
|---|---|---|
| `Regime` | A defined market regime state | BULL_TRENDING, BEAR_VOLATILE, RANGE_BOUND, CRISIS, SIDEWAYS |
| `MacroIndicator` | A macroeconomic measurement | VIX reading, US 10Y yield, USD/INR rate, crude oil price |
| `EconomicEvent` | A scheduled or unscheduled macro event | RBI rate decision, US CPI release, Q1 GDP announcement |

**Regime entity lifecycle:**

```
DETECTED ──► CONFIRMED ──► ACTIVE ──► TRANSITION_INITIATED ──► ENDED
                │                              │
                ▼                              ▼
           PROVISIONAL                    BRIEF (< 3 days duration)
          (< 3 days old,                  regime is excluded from
           not yet confirmed)             long-term pattern analysis
```

**Regime entity significance:** The Regime entity is one of the most influential entities in the IIOS. It determines which strategies are active, how agents are weighted, and what risk thresholds apply. A correctly maintained Regime entity is foundational to intelligent decision-making.

---

### 2.6 Corporate Entity

**Purpose:** Corporate entities represent the companies whose securities the system trades. They are the underlying economic reality behind market symbols.

**Corporate entity types:**

| Entity Type | Description |
|---|---|
| `Company` | A publicly listed Indian company |
| `FIIParticipant` | A foreign institutional investor tracked for sentiment signals |
| `ListedSecurity` | A specific security listing (equity, bond, derivative) of a company |

**Corporate entity attributes:**

| Attribute | Description |
|---|---|
| `company_name` | Full registered name |
| `exchange_symbol` | NSE symbol |
| `isin` | International Securities Identification Number |
| `sector` | Sector classification |
| `market_cap_tier` | LARGE, MID, SMALL |
| `index_memberships` | List of indices the company is a constituent of |
| `results_frequency` | Quarterly reporting schedule |
| `promoter_holding_pct` | Promoter shareholding percentage |
| `fii_holding_pct` | FII shareholding percentage |

---

### 2.7 Portfolio Entity

**Purpose:** Portfolio entities represent the capital management layer — how funds are organised, allocated, and tracked across strategies.

**Portfolio entity types:**

| Entity Type | Description |
|---|---|
| `Portfolio` | The single portfolio managing all capital (one active portfolio per process) |
| `Allocation` | A capital assignment from the portfolio to a specific strategy |
| `BudgetEnvelope` | A bounded budget available to a specific strategy type |

**Portfolio entity as aggregate root:** The `Portfolio` entity is the aggregate root of the portfolio aggregate. All `Position` entities within the portfolio are part of this aggregate. All capital allocation decisions go through the `Portfolio` entity.

**Portfolio entity invariants:**
- `total_capital = available_capital + allocated_capital`
- `allocated_capital = sum(all active Position.market_value)`
- `daily_loss_pct` never exceeds `RiskThreshold.max_daily_loss_pct` (enforced by RiskGuardian)
- Total open positions never exceed `RiskThreshold.max_open_positions`

---

### 2.8 Execution Entity

**Purpose:** Execution entities represent the communication record between the IIOS and the broker — request, response, confirmation, and quality measurement.

**Execution entity types:**

| Entity Type | Description |
|---|---|
| `ExecutionRecord` | The complete record of a broker order submission and response |
| `SlippageRecord` | The difference between expected and actual fill price |
| `BrokerSession` | A connection session to the Dhan broker API |

**Execution entity significance:** Execution entities are the performance audit layer. They answer: "How well did the system execute its decisions?" Slippage records, in particular, accumulate into knowledge about optimal execution timing and order types.

---

### 2.9 Risk Entity

**Purpose:** Risk entities represent the risk management constraints, events, and measurements that govern the system's capital safety.

**Risk entity types:**

| Entity Type | Description | Mutability |
|---|---|---|
| `RiskThreshold` | A defined risk limit (daily loss limit, position limit, VIX limit) | Mutable (Human Principal may update) |
| `KillSwitch` | The current state of the system-wide kill switch | Mutable (active/inactive) |
| `DrawdownRecord` | A documented drawdown event with start, depth, and recovery | Immutable after close |
| `StressScenario` | A defined stress test scenario used in Monte Carlo runs | Mutable (Human Principal may add/update) |

**Risk entity authority:** Risk entities have special authority. Their state directly determines whether any trading activity can occur. The `KillSwitch` entity, in particular, is the single source of truth for whether the system is permitted to open new positions. Its state is checked at the start of every cognitive cycle.

**Risk entity ownership:** All risk entities are owned exclusively by RiskGuardian. No other component may write to risk entities. Any service that needs to trigger a kill switch activates it through RiskGuardian, which owns and manages the `KillSwitch` entity.

---

### 2.10 Knowledge Entity

**Purpose:** Knowledge entities represent validated, versioned knowledge about market behaviour, strategy performance, agent accuracy, and system behaviour. They are the knowledge base of the IIOS.

**Knowledge entity types:** See KNOWLEDGE_ENGINE_ARCHITECTURE.md for complete design. Within the Entity Engine, Knowledge entities are managed with the same lifecycle principles as all other entities but with additional knowledge-specific quality requirements.

**Key distinction:** Knowledge entities are entities because they have identity, lifecycle, versioning, and governance. But they are knowledge because they represent validated understanding, not raw operational facts.

---

### 2.11 AI Entity

**Purpose:** AI entities represent the artificial intelligence components that produce opinions, hypotheses, and decisions.

**AI entity types:**

| Entity Type | Description | Lifecycle |
|---|---|---|
| `Agent` | One of the 62 AI debate agents | Created at startup; ACTIVE or INACTIVE |
| `AgentOpinion` | A specific agent's opinion on a specific hypothesis | Created per cycle; immutable |
| `Hypothesis` | A proposed trade opportunity generated by a strategy | CANDIDATE → EVALUATED → APPROVED/REJECTED |
| `DecisionRecord` | The final decision on a hypothesis | Created on decision; immutable |

**Agent entity:** The 62 agents in the IIOS are entities with persistent identity and a calibration history. Each agent accumulates an accuracy record over time — its predictions are compared against actual trade outcomes, and its calibration entity is updated accordingly. Agent entities are one of the primary inputs to the MetaLearning layer.

---

### 2.12 System Entity

**Purpose:** System entities represent the operational infrastructure of the IIOS — cycles, jobs, feeds, and configurations.

**System entity types:**

| Entity Type | Description | Lifecycle |
|---|---|---|
| `Cycle` | A complete cognitive cycle execution | STARTED → IN_PROGRESS → COMPLETED/FAILED |
| `ScheduledJob` | A scheduled maintenance or intelligence task | SCHEDULED → RUNNING → COMPLETED/FAILED |
| `DataFeed` | A specific data source connection | CONNECTING → ACTIVE → DEGRADED → FAILED |
| `SystemConfiguration` | The current active configuration of the system | ACTIVE (always has exactly one active version) |

**Cycle entity as audit anchor:** The `Cycle` entity is the primary audit anchor. Every decision, every order, every trade is associated with the cycle in which it occurred. Cycle entities form the timeline of the system's operation.

---

### 2.13 Reference Entity

**Purpose:** Reference entities represent stable reference data that does not change frequently and is loaded from external sources at startup.

**Reference entity types:**

| Entity Type | Description | Update frequency |
|---|---|---|
| `Calendar` | NSE market calendar for a year | Annual |
| `ExpirySchedule` | Monthly option expiry schedule | Annual |
| `TradingHoliday` | A specific market holiday | Annual |
| `SymbolMaster` | The complete NSE symbol master list | Weekly |

**Reference entity caching:** Reference entities are fully loaded into the in-memory reference cache at system startup. They are not queried from the database during cycles — cycle-time reference lookups go to the cache exclusively.

---

### 2.14 Derived Entity

**Purpose:** Derived entities are produced by the system's analytical and learning processes — they do not represent direct market or operational facts, but rather computed conclusions.

**Derived entity types:**

| Entity Type | Source | Description |
|---|---|---|
| `LearningRecord` | Closed Trade + Strategy performance | The learning extracted from one closed trade |
| `BacktestSnapshot` | Historical market data + Strategy | Strategy performance on a historical window |
| `WalkForwardResult` | BacktestSnapshot + OOS period | Out-of-sample test result |
| `EvolvedVariant` | Strategy + Evolution run | A new strategy variant produced by evolutionary optimisation |

**Derived entity provenance:** Every derived entity carries a complete provenance trace — the inputs (source entities and data) and the method (backtesting, walk-forward, evolution) that produced it. This provenance is the entity's lineage record.

---
## PART III — ENTITY COMPONENTS

### 3.1 Component Overview

The Entity Engine is composed of fifteen distinct components, each with a precisely defined purpose and responsibility boundary. These components are not independent microservices — they are cohesive sub-systems within the Entity Engine that collaborate through well-defined internal interfaces.

```
ENTITY ENGINE COMPONENT MAP

┌─────────────────────────────────────────────────────────────────────────────┐
│                          ENTITY ENGINE                                      │
│                                                                             │
│  ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────────────┐  │
│  │  Entity Registry │   │  Entity Catalog  │   │    Entity Factory       │  │
│  │  (What exists)  │   │  (What it is)   │   │    (How to create)      │  │
│  └────────┬────────┘   └────────┬─────────┘   └────────────┬────────────┘  │
│           │                     │                           │               │
│  ┌────────▼─────────────────────▼───────────────────────────▼────────────┐  │
│  │                    Entity Validator                                    │  │
│  │           (Is it correct? Is it complete? Is it consistent?)          │  │
│  └────────────────────────────────┬───────────────────────────────────────┘  │
│                                   │                                          │
│  ┌────────────────┐   ┌───────────▼──────────┐   ┌───────────────────────┐  │
│  │ Identity Mgr   │   │ Lifecycle Manager     │   │ Version Manager       │  │
│  │ (Who is this?) │   │ (Where in lifecycle?) │   │ (Which version?)      │  │
│  └────────────────┘   └──────────────────────┘   └───────────────────────┘  │
│                                                                              │
│  ┌────────────────┐   ┌──────────────────────┐   ┌───────────────────────┐  │
│  │ Metadata Mgr   │   │ Search Engine        │   │ Entity Cache          │  │
│  │ (What else     │   │ (Find me entities    │   │ (Fast access to       │  │
│  │  do we know?)  │   │  matching this)      │   │  active entities)     │  │
│  └────────────────┘   └──────────────────────┘   └───────────────────────┘  │
│                                                                              │
│  ┌────────────────┐   ┌──────────────────────┐   ┌───────────────────────┐  │
│  │ Entity Index   │   │ Audit Manager        │   │ History Manager       │  │
│  │ (Structured    │   │ (What changed, when  │   │ (What did it look     │  │
│  │  lookup)       │   │  and who changed it) │   │  like before?)        │  │
│  └────────────────┘   └──────────────────────┘   └───────────────────────┘  │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │                   Integrity Checker + Governance Manager               │  │
│  │   (Are all rules satisfied? Who owns this? What policy applies?)       │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### 3.2 Entity Registry

**Purpose:** The Entity Registry is the single authoritative index of all entities that exist in the IIOS. It is the source of truth for the question: "Does this entity exist?"

**Responsibilities:**

| Responsibility | Description |
|---|---|
| Entity enrollment | Record a new entity into the registry at creation time |
| Entity lookup | Resolve an `entity_id` to confirm the entity exists and return its current status |
| Entity count | Report how many entities of each type currently exist in each lifecycle state |
| Existence validation | Confirm that a referenced entity (e.g., an order's symbol reference) is a valid registered entity |
| Soft-deletion tracking | Record which entities have been soft-deleted and when |
| Cross-reference validation | Confirm that all foreign entity references within an entity point to valid registered entities |

**Registry design principles:**

The Registry is read-dominated. The vast majority of registry operations are lookups, not writes. A new entity is registered once; it may be looked up thousands of times during its active life.

The Registry is hot-path critical. Many operations — including every order submission, every position update, and every risk check — query the Registry to validate entity existence. Registry lookup must be sub-millisecond.

The Registry maintains a dual representation:
- **Persistent store:** Complete entity record in the persistence layer (SQLite entity_registry table)
- **In-memory index:** A dictionary keyed on `entity_id` with lightweight summary records for hot-path lookups

**Registry data per entry:**

| Field | Description |
|---|---|
| `entity_id` | UUID4 — the permanent key |
| `entity_type` | Type enum value |
| `entity_category` | Category enum value |
| `status` | Current lifecycle status |
| `created_at` | Registration timestamp |
| `owner_id` | Current owner identifier |
| `is_active` | Active/inactive flag |
| `schema_version` | Schema version at registration time |
| `storage_ref` | Reference to full entity record location in persistence layer |

**Registry capacity:** The registry is expected to accumulate hundreds of thousands of entity records over the system's operational lifetime. The in-memory index holds only active entities; historical entries are paged in from the persistence layer on demand.

---

### 3.3 Entity Catalog

**Purpose:** The Entity Catalog is the descriptive registry — where the Registry records existence, the Catalog records what each entity type is, what attributes it has, what its invariants are, and what governance rules apply to it.

**Responsibilities:**

| Responsibility | Description |
|---|---|
| Entity type registration | Register the definition of each entity type (fields, constraints, defaults) |
| Schema management | Manage the schema version history for each entity type |
| Attribute catalogue | Maintain the complete attribute list for each entity type |
| Constraint catalogue | Maintain the invariant rules for each entity type |
| Lifecycle definition | Define the allowed state transitions for each entity type |
| Default values | Define default values for optional fields |
| Documentation | Maintain human-readable descriptions of each entity type and attribute |

**Catalog design:** The Catalog is loaded at system startup from the entity type definitions and is read-only during normal operation. It is only modified during schema migrations, which are performed offline with the system stopped. The Catalog is the bridge between the code-level entity definitions and the runtime entity management logic.

**Catalog structure per entity type:**

| Field | Description |
|---|---|
| `entity_type` | The type identifier |
| `category` | The entity category |
| `version` | Current schema version |
| `fields` | List of field definitions (name, type, required, default) |
| `invariants` | List of invariant rule IDs that apply |
| `lifecycle_states` | Valid states for this entity type |
| `valid_transitions` | Allowed state transitions |
| `required_owners` | List of owner types that may own this entity type |
| `retention_policy` | How long this entity type is retained |
| `audit_level` | Audit verbosity: MINIMAL, STANDARD, FULL |

---

### 3.4 Entity Factory

**Purpose:** The Entity Factory is the standardised creation mechanism for all entities. No entity may be created by directly constructing its data structure — all entity creation goes through the Factory.

**Responsibilities:**

| Responsibility | Description |
|---|---|
| Identity assignment | Generate and assign the permanent `entity_id` (UUID4) at creation time |
| Default population | Apply default values from the Catalog |
| Required field validation | Ensure all required fields are present before the entity is registered |
| Lineage initialisation | Create the initial lineage record for the new entity |
| Version initialisation | Set `version = 1` and create the initial version record |
| Registry enrollment | Enroll the new entity in the Registry after successful validation |
| Audit record creation | Create the initial audit record (entity created event) |
| Cache population | Place the new entity into the active entity cache |

**Factory creation sequence:**

```
Caller provides creation parameters
         │
         ▼
[Factory: Validate required fields]
         │
         ├──► [FAIL] → ValidationError raised; no entity created
         │
         ▼
[Factory: Generate entity_id (UUID4)]
         │
         ▼
[Factory: Apply Catalog defaults]
         │
         ▼
[Factory: Initialise Root Entity fields]
         │
         ▼
[Factory: Create initial Version record (v1)]
         │
         ▼
[Factory: Create initial Lineage record]
         │
         ▼
[Factory: Enroll in Registry]
         │
         ▼
[Factory: Create ENTITY_CREATED audit event]
         │
         ▼
[Factory: Populate cache]
         │
         ▼
[Factory: Return created entity to caller]
```

**Factory invariant:** The Factory is idempotent with respect to identity — if a caller provides an idempotency key (e.g., for order creation where the same order should not be created twice), the Factory checks for an existing entity with that key and returns the existing entity rather than creating a duplicate.

---

### 3.5 Entity Validator

**Purpose:** The Entity Validator enforces all entity invariants at creation time, update time, and on-demand when integrity checks are performed.

**Responsibilities:**

| Responsibility | Description |
|---|---|
| Type validation | Verify that each field's value conforms to its declared type |
| Required field validation | Confirm all required fields are present and non-null |
| Invariant validation | Check all entity-specific invariants (see 2.3 for examples) |
| Aggregate invariant validation | Check invariants that span multiple entities within an aggregate |
| Cross-entity reference validation | Confirm that all referenced entities exist and are in valid states |
| State transition validation | Verify that a proposed state transition is valid per the Catalog |
| Business rule validation | Check domain-specific business rules beyond simple data typing |

**Validation layers:**

| Layer | When triggered | Description |
|---|---|---|
| Structural validation | On creation and every update | Type, format, required fields |
| Referential validation | On creation and every update that changes a reference field | Referenced entities exist |
| Business rule validation | On creation, update, and state transition | Domain-specific invariants |
| Aggregate validation | On creation of a new child entity in an aggregate | Aggregate-level consistency |
| Integrity validation | On-demand and scheduled | Full cross-entity consistency scan |

**Validation failure handling:**

When validation fails, the Entity Validator raises a `EntityValidationError` containing:
- The entity_id (if known — may be absent during creation)
- The entity_type
- The violated invariant rule ID
- A human-readable description of what was violated
- The value(s) that caused the violation

The caller is responsible for handling the error. The Entity Engine never silently swallows validation failures.

---

### 3.6 Entity Identity Manager

**Purpose:** The Entity Identity Manager is responsible for maintaining the complete identity record of every entity — including its canonical ID, all aliases, all external system IDs, and its version ID history.

**Responsibilities:**

| Responsibility | Description |
|---|---|
| Identity record maintenance | Maintain the canonical identity record per entity |
| Alias registration | Register human-readable or alternative names for entities |
| External ID mapping | Map external system IDs (broker order IDs, NSE ISIN codes) to `entity_id` |
| Identity resolution | Given any identifier, return the canonical `entity_id` |
| Duplicate detection | Detect when a new entity might be a duplicate of an existing entity |
| Conflict resolution | Resolve identity conflicts using defined rules |
| Version ID tracking | Track the series of version IDs for each entity |

**Identity resolution is described in full in Part VI.**

---

### 3.7 Entity Lifecycle Manager

**Purpose:** The Entity Lifecycle Manager governs all entity state transitions. It is the gatekeeper that ensures entities move through their lifecycle states in the correct order and with the correct preconditions satisfied.

**Responsibilities:**

| Responsibility | Description |
|---|---|
| State transition execution | Move an entity from one lifecycle state to another |
| Precondition validation | Verify all preconditions for a state transition are met |
| Postcondition enforcement | Verify postconditions after a successful transition |
| Side effect coordination | Trigger necessary side effects (version increment, audit record, downstream events) |
| Blocked transition handling | Handle and record blocked transitions (transition attempted but precondition not met) |
| Lifecycle event publishing | Publish lifecycle events to the EventBus for downstream consumption |

**State transition sequence:**

```
Caller requests: TRANSITION(entity_id, target_state)
         │
         ▼
[Lifecycle Manager: Fetch current state]
         │
         ▼
[Lifecycle Manager: Check transition validity (Catalog)]
         │
         ├──► [INVALID] → raise InvalidTransitionError
         │
         ▼
[Lifecycle Manager: Check preconditions]
         │
         ├──► [FAIL] → raise LifecyclePreConditionError
         │
         ▼
[Lifecycle Manager: Execute transition]
         │
         ▼
[Lifecycle Manager: Version Manager increment version]
         │
         ▼
[Lifecycle Manager: Audit Manager record transition event]
         │
         ▼
[Lifecycle Manager: Check postconditions]
         │
         ▼
[Lifecycle Manager: EventBus publish lifecycle event]
         │
         ▼
Return updated entity to caller
```

---

### 3.8 Entity Version Manager

**Purpose:** The Entity Version Manager records every state of every entity over time. Every change to an entity's attributes generates a new version record. Versions are immutable after creation — they are the permanent archive of entity history.

**Responsibilities:**

| Responsibility | Description |
|---|---|
| Version creation | Create a new version record on every entity update |
| Version numbering | Assign monotonically increasing version numbers |
| Version storage | Persist version records to the entity version store |
| Version retrieval | Retrieve the state of an entity at any past version |
| Version diff | Compute the difference between two versions of the same entity |
| Version series management | Maintain the ordered series of versions per entity |
| Branch version management | For entities that split (e.g., position splits), maintain version branches |

**Version record contents:**

| Field | Description |
|---|---|
| `version_id` | UUID4 for this specific version |
| `entity_id` | Reference to parent entity |
| `version_number` | Monotonically increasing integer |
| `state_snapshot` | Complete entity state at this version (JSON) |
| `diff_from_previous` | JSON diff from previous version (for efficiency) |
| `changed_by` | Service or actor that triggered the change |
| `change_reason` | Human-readable reason for the change |
| `changed_at` | UTC timestamp |
| `lifecycle_state` | Entity lifecycle state at this version |
| `is_current` | Boolean — only one version per entity is current |

---

### 3.9 Entity Metadata Manager

**Purpose:** The Entity Metadata Manager maintains all supplementary information associated with an entity that is not part of its core attributes — tags, labels, notes, external links, classification attributes, and custom key-value pairs.

**Responsibilities:**

| Responsibility | Description |
|---|---|
| Tag management | Add, update, and remove searchable tags on entities |
| Classification management | Maintain classification attributes (tier, category, priority) |
| Custom attribute management | Store arbitrary key-value metadata for entities |
| External link management | Maintain links to external system records (broker IDs, exchange codes) |
| Annotation management | Store human-added notes and annotations |
| Metadata search support | Maintain metadata indices for search |

**Metadata is append-friendly:** New metadata fields may be added to any entity without a schema migration, because metadata is stored as a JSON blob. Structured metadata that needs to be indexed or searched must be declared and indexed explicitly.

---

### 3.10 Entity Search Engine

**Purpose:** The Entity Search Engine provides discovery capabilities — the ability to find entities matching criteria across the full entity population.

**Responsibilities:**

| Responsibility | Description |
|---|---|
| Full-text search | Search entity names, descriptions, and text fields |
| Attribute search | Search by specific attribute values (e.g., all ACTIVE Orders for TATASTEEL) |
| Tag search | Search by entity tags |
| Category/type search | Find all entities of a specific type or category |
| Temporal search | Find entities created or updated within a time range |
| Status search | Find all entities in a specific lifecycle state |
| Relationship search | Find entities connected to a specified entity by a specified relationship |
| Composite search | Combine multiple criteria with AND/OR operators |

**Search index maintenance:** The Search Engine maintains a set of indices that are updated on every entity create, update, or delete operation. These indices are designed for read performance — writes are batched asynchronously to avoid blocking entity operations.

**Search response format:** All search operations return a ranked list of entity summaries (not full entities). Full entity retrieval is a separate operation that goes through the Entity Cache.

---

### 3.11 Entity Cache

**Purpose:** The Entity Cache provides fast in-memory access to active entities, avoiding repeated database reads during cycle-time operations.

**Responsibilities:**

| Responsibility | Description |
|---|---|
| Active entity caching | Keep all ACTIVE entities of high-access types in memory |
| Cache population | Load entities into cache on startup and on first access |
| Cache invalidation | Invalidate and refresh cache entries when entities are updated |
| Cache eviction | Evict stale or low-access entities when memory pressure increases |
| Cache warm-up | Pre-load expected entities before market-hours cycles begin |
| Cache statistics | Track hit/miss rates, eviction rates, and cache size |

**Cache hierarchy:**

| Tier | Description | Access time |
|---|---|---|
| L1 — Hot entity cache | Critical entities always in memory (RiskThreshold, KillSwitch, Portfolio) | < 1 ms |
| L2 — Active entity cache | All ACTIVE entities of operational types | < 2 ms |
| L3 — Recent history cache | Recently accessed historical entities | < 5 ms |
| L4 — Persistence layer | Full entity store | 10–50 ms |

---

### 3.12 Entity Index

**Purpose:** The Entity Index provides structured, high-performance lookup indices for the most common access patterns. Unlike the Search Engine (which is flexible and discovery-oriented), the Index is purpose-built for specific, repeated access patterns.

**Indices maintained:**

| Index | Key | Use case |
|---|---|---|
| Entity by type | entity_type → [entity_id list] | List all orders, all positions, etc. |
| Entity by status | entity_type + status → [entity_id list] | All ACTIVE strategies |
| Entity by owner | owner_id → [entity_id list] | All entities owned by OrderManager |
| Entity by symbol | symbol → [entity_id list] | All orders and positions for TATASTEEL |
| Entity by date | date → [entity_id list] | All cycles on 2026-07-02 |
| Entity by parent | parent_entity_id → [child_entity_id list] | All fills for an order |
| Entity by tag | tag → [entity_id list] | All entities tagged CRITICAL |
| Entity by regime | regime_id → [entity_id list] | All strategies active in a regime |

---

### 3.13 Entity Audit Manager

**Purpose:** The Entity Audit Manager records every significant event in the life of every entity — creation, updates, state transitions, ownership changes, and governance actions. The audit log is the permanent, immutable record of entity history from a compliance perspective.

**Responsibilities:**

| Responsibility | Description |
|---|---|
| Event recording | Record every audit-eligible event with full context |
| Event immutability | Ensure audit records cannot be modified or deleted |
| Event querying | Allow authorised queries against the audit log |
| Audit level enforcement | Apply entity-type-specific audit levels (MINIMAL, STANDARD, FULL) |
| Compliance report generation | Generate compliance-formatted audit reports |
| Retention enforcement | Ensure audit records meet mandated retention periods |

**Audit event structure:**

| Field | Description |
|---|---|
| `audit_id` | UUID4 — permanent audit event identifier |
| `entity_id` | Entity that was affected |
| `entity_type` | Type of the affected entity |
| `event_type` | CREATED, UPDATED, TRANSITION, OWNERSHIP_CHANGE, GOVERNANCE_ACTION |
| `actor_id` | Service or person that triggered the event |
| `timestamp` | UTC timestamp |
| `previous_state` | Snapshot of relevant state before the event |
| `new_state` | Snapshot of relevant state after the event |
| `reason` | Human-readable reason for the change |
| `cycle_id` | The cycle during which this event occurred |
| `session_id` | The system session during which this event occurred |

---

### 3.14 Entity History Manager

**Purpose:** The Entity History Manager provides access to the temporal history of entities — the ability to reconstruct what an entity looked like at any point in its past.

**Responsibilities:**

| Responsibility | Description |
|---|---|
| History retrieval | Return the complete version history for an entity |
| Point-in-time retrieval | Return an entity's state at a specified timestamp |
| Version comparison | Compare two versions of an entity and return the diff |
| History analytics | Compute statistics over entity history (update frequency, field churn, etc.) |
| History compression | Compress old version records for storage efficiency while preserving accessibility |
| History export | Export entity history in standard formats for external analysis |

**History retrieval use cases:**

- "What was the state of the TATASTEEL position at 10:30:00 on 2026-06-15?" → Point-in-time retrieval
- "How many times did this strategy's parameters change in the last 30 days?" → History analytics
- "What did the RiskThreshold look like before the last update?" → Version comparison

---

### 3.15 Entity Integrity Checker

**Purpose:** The Entity Integrity Checker performs scheduled and on-demand cross-entity consistency checks — verifying that the entity population as a whole satisfies all system-level invariants.

**Responsibilities:**

| Responsibility | Description |
|---|---|
| Scheduled integrity checks | Run full integrity scans on a daily schedule |
| On-demand integrity checks | Run targeted integrity checks when triggered |
| Orphan detection | Find entities that reference deleted or non-existent parent entities |
| Aggregate invariant validation | Verify aggregate-level invariants hold across all entities |
| Reference integrity | Verify all foreign entity references are valid |
| Status consistency | Verify entity statuses are consistent with their containing aggregates |
| Integrity report generation | Produce a report of all integrity violations found |

---

### 3.16 Entity Governance Manager

**Purpose:** The Entity Governance Manager enforces ownership policies, approval workflows, classification rules, and compliance requirements across the entity population.

**Responsibilities:**

| Responsibility | Description |
|---|---|
| Ownership management | Track and enforce entity ownership assignments |
| Approval workflow | Manage approval chains for entities requiring sign-off |
| Classification enforcement | Ensure all entities carry required classification labels |
| Policy enforcement | Apply entity-type-specific governance policies |
| Compliance monitoring | Monitor the entity population for compliance with mandatory rules |
| Governance reporting | Generate governance health reports |

---
## PART IV — ENTITY LIFECYCLE

### 4.1 Lifecycle Overview

Every entity in the IIOS follows a defined lifecycle — a progression through named states from first registration to final retirement. The lifecycle is not optional or advisory; it is enforced by the Entity Lifecycle Manager. No entity may skip states, no entity may regress to a prior state without an explicit restore operation, and no entity may exist in an undefined state.

The lifecycle has twelve stages. Not all entity types pass through all twelve stages — the Catalog defines which stages apply to each type. However, every entity type must define at least: registration, creation, activation, update, and retirement.

---

### 4.2 The Twelve Lifecycle Stages

**Stage 1: Registration**

An entity enters the system through registration. At this point, the entity has been identified as a domain object that the system needs to track, but it does not yet exist as a fully formed entity. Registration is the act of assigning an `entity_id` and enrolling the entity in the Registry.

Registration occurs automatically as part of the Factory creation sequence. It is not a separate manual step. The distinction is important: registration is the act of claiming an identity slot in the system, before any entity-specific data is validated or stored.

**Stage 2: Validation**

After registration, the proposed entity data is validated by the Entity Validator. This includes structural validation (field types, required fields), referential validation (referenced entities exist), and business rule validation (domain invariants are satisfied).

If validation fails, the registration is rolled back — the entity_id is released, the partial Registry entry is removed, and a `REGISTRATION_REJECTED` audit event is created. The caller receives a `EntityValidationError`.

**Stage 3: Creation**

If validation succeeds, the entity is created. The Entity Factory completes the creation sequence — defaults applied, version 1 created, lineage record initialised, initial audit record written. The entity now exists in the CREATED state.

An entity in CREATED state is not yet ready for use by other components. It has been created but has not yet been activated. Some entity types may remain in CREATED briefly while a separate activation step occurs (e.g., an Order that is created but not yet submitted to the broker).

**Stage 4: Activation**

Activation is the transition from CREATED to ACTIVE. This transition may have preconditions. For an Order, activation occurs when the order is submitted to the broker. For a Strategy, activation occurs when it passes validation gates and is explicitly approved. For a DataFeed, activation occurs when the connection is established.

Once ACTIVE, the entity is a full participant in the system. Other entities may reference it, decisions may depend on it, and risk checks may depend on its state.

**Stage 5: Update**

ACTIVE entities are updated as their state evolves. Updates increment the version number and create a new version record. Updates must pass validation — an update that would violate an entity invariant is rejected.

Updates may be:
- **Attribute updates:** Field values change (e.g., Position.unrealised_pnl, Trade.exit_price)
- **Status updates:** The entity's status changes (e.g., Order from SUBMITTED to PARTIALLY_FILLED)
- **Metadata updates:** Tags or metadata change (no version increment for pure metadata changes)
- **Ownership updates:** The responsible owner changes (rare — requires governance approval)

**Stage 6: Versioning**

Versioning is not a state — it is a parallel process that records every update. Every time an entity transitions through an update, a new version record is written. The version number increments monotonically. There is no maximum version number.

Versioning may also be triggered explicitly for significant milestones — e.g., when a Strategy entity completes a full backtesting cycle, an explicit "milestone version" may be created with a descriptive `change_reason`.

**Stage 7: Merge**

Merge is the process of combining two entities of the same type into a single entity. This occurs when duplicate detection reveals that two separately created entities represent the same domain object.

The Merge process:
1. Designates one entity as the **primary** (survives the merge)
2. Designates the other as the **secondary** (absorbed by the merge)
3. Copies any valuable unique attributes from secondary to primary
4. Updates all references from secondary `entity_id` to primary `entity_id`
5. Transitions the secondary entity to MERGED status (not deleted)
6. Creates a merge audit record on both entities
7. Increments the primary entity's version

Merged entities are preserved in MERGED state for audit purposes. Their `entity_id` remains valid but they are flagged as merged, and all lookups by the secondary ID are transparently forwarded to the primary.

**Stage 8: Split**

Split is the inverse of merge — dividing one entity into two separate entities. This occurs when an entity that was modelled as a single object is discovered to represent two distinct domain objects.

Example: A `Position` that was tracking a single symbol is split when the system discovers that two different strategies both hold the same symbol — these should be tracked as separate positions per strategy, not as a single combined position.

The Split process:
1. Creates two new entities (successor-A and successor-B) with new `entity_id` values
2. Divides the original entity's attributes between the successors appropriately
3. Transitions the original entity to SPLIT status
4. Creates lineage links from both successors back to the original
5. Updates all references to use the appropriate successor
6. Creates split audit records

**Stage 9: Deprecation**

Deprecation is the formal notice that an entity will be retired. A deprecated entity is still ACTIVE — it continues to function — but it is flagged to consumers that it will cease to be used.

Deprecation is used for:
- Strategies that have been superseded by evolved variants
- Data feeds that are being replaced by a higher-quality source
- Reference data that will be updated at a future date

A deprecated entity displays a `deprecated_at` timestamp and a `deprecation_reason`. The system may optionally include a `successor_entity_id` pointing to the replacement entity.

**Stage 10: Archive**

Archival transitions an entity from ACTIVE or DEPRECATED to ARCHIVED. An archived entity is no longer a participant in operational decisions. It is preserved for audit, historical analysis, and regulatory compliance.

Archive rules per entity type:

| Entity Type | Archive trigger | Archive after |
|---|---|---|
| Order | Filled, Rejected, or Cancelled | Immediate (same day) |
| Trade | Closed | End of trading week |
| Position | Closed | End of trading week |
| Strategy | Manually retired or auto-disabled | After cooling-off period (30 days) |
| Regime | Ended | On regime transition |
| KnowledgeRecord | Superseded by newer version | After 30 days |
| Cycle | Completed | After 7 days |

**Stage 11: Restore**

Restore is the reverse of archival — transitioning an ARCHIVED entity back to ACTIVE. This is an unusual operation, typically requiring explicit authorisation from the Human Principal.

Use cases for restore:
- A strategy is restored after a software bug caused it to be incorrectly auto-disabled
- A position is restored after a data feed error caused it to appear closed
- A reference entity is restored after incorrect archival

Restore creates a `RESTORE` audit event, increments the version, and requires a restore justification to be recorded.

**Stage 12: Retirement**

Retirement is the final lifecycle stage. A retired entity has permanently ceased to be operationally relevant. Unlike archival, retirement is not reversible — a retired entity cannot be restored to active use.

Retirement differs from archival in intent:
- **Archive:** Temporarily inactive, may be referenced, historically important, accessible for reporting
- **Retired:** Permanently inactive, superseded, only preserved for audit compliance

Retired entities remain in the Registry and the entity store permanently, flagged as RETIRED. They may be queried by the History Manager and the Audit Manager.

---

### 4.3 Entity Lifecycle State Machine

```
                        ENTITY LIFECYCLE STATE MACHINE
                        ═══════════════════════════════

                          ┌──────────────────┐
                          │   REGISTRATION   │ ◄── Entity identified
                          └────────┬─────────┘
                                   │
                          ┌────────▼─────────┐
              ┌── FAIL ── │   VALIDATION     │
              │           └────────┬─────────┘
              ▼                    │ PASS
    ┌─────────────────┐   ┌────────▼─────────┐
    │  REJECTED       │   │   CREATED        │
    └─────────────────┘   └────────┬─────────┘
                                   │ Activate
                          ┌────────▼─────────┐
                          │    ACTIVE         │ ◄────────────────┐
                          └───────┬──┬────────┘                  │
                                  │  │                           │
                      ┌───────────┘  └──────────────┐           │
                      │                             │           │
              ┌───────▼────────┐         ┌──────────▼──────┐    │
              │  DEPRECATED    │         │    MERGED        │    │
              └───────┬────────┘         └──────────────────┘    │
                      │                                          │
              ┌───────▼────────┐         ┌──────────────────┐    │
              │    ARCHIVED    │         │     SPLIT        │    │
              └───────┬────────┘         └──────────────────┘    │
                      │                                          │
                      │ Restore ──────────────────────────────────┘
                      │
              ┌───────▼────────┐
              │    RETIRED     │  ◄── Terminal state (permanent)
              └────────────────┘
```

---

### 4.4 Lifecycle State Definitions

| State | Description | Entities can be... |
|---|---|---|
| `REGISTERED` | Identity assigned, awaiting validation | Looked up by ID only |
| `VALIDATION_FAILED` | Failed validation checks | Accessible for audit investigation |
| `CREATED` | Passed validation, not yet activated | Inspected but not operationally used |
| `ACTIVE` | Fully operational | Used by all system components |
| `DEPRECATED` | Scheduled for retirement, still operational | Used but marked for replacement |
| `MERGED` | Absorbed into another entity | Looked up — forwarded to primary |
| `SPLIT` | Divided into two successor entities | Looked up — forwarded to successors |
| `ARCHIVED` | Inactive, preserved for audit | Queried historically |
| `RESTORED` | Brought back from ARCHIVED to ACTIVE | Same as ACTIVE after restore |
| `RETIRED` | Permanently inactive | Historical and audit access only |

---

### 4.5 Lifecycle Transitions Table

| From State | To State | Trigger | Preconditions |
|---|---|---|---|
| REGISTERED | CREATED | Validation passes | All required fields valid |
| REGISTERED | VALIDATION_FAILED | Validation fails | — |
| CREATED | ACTIVE | Activation call | Entity-type-specific activation preconditions |
| ACTIVE | DEPRECATED | Deprecation request | Human Principal or system trigger |
| ACTIVE | MERGED | Merge operation | Target entity exists, merge approved |
| ACTIVE | SPLIT | Split operation | Split approved, successor definitions valid |
| ACTIVE | ARCHIVED | Archive trigger | No open dependencies on this entity |
| DEPRECATED | ARCHIVED | Archive trigger | No open dependencies on this entity |
| ARCHIVED | ACTIVE | Restore operation | Human Principal approval |
| ACTIVE | RETIRED | Retirement | Human Principal approval |
| DEPRECATED | RETIRED | Retirement | Human Principal approval |
| ARCHIVED | RETIRED | Retirement | Human Principal approval |

---

### 4.6 Lifecycle by Entity Category

| Entity Category | Required Stages | Archive Policy | Retirement Policy |
|---|---|---|---|
| Financial (Order, Trade, Fill) | R→V→C→A→Update→Archive | Same day (Order/Fill); Week-end (Trade) | After 7 years (regulatory) |
| Market (Symbol, Index) | R→V→C→A→Update | Delisting triggers archival | Manual only |
| Economic (Regime) | R→V→C→A→Update→Archive | Regime end triggers archival | Manual only |
| Portfolio (Portfolio) | R→V→C→A→Update | Never archived (one lifetime) | System decommission only |
| Risk (RiskThreshold, KillSwitch) | R→V→C→A→Update | Manual only | Manual only |
| AI (Agent, Hypothesis) | R→V→C→A→Update→Archive | Cycle end (Hypothesis); never (Agent) | Manual (Agent) |
| System (Cycle, Job) | R→V→C→A→Archive | 7 days (Cycle); 30 days (Job) | Manual only |
| Derived (LearningRecord) | R→V→C→A→Update→Archive | After superseded by newer | After 1 year |
| Reference (Calendar, SymbolMaster) | R→V→C→A→Update | Annual refresh | Annual refresh |

---

### 4.7 Lifecycle Event Publishing

Every lifecycle state transition triggers an event published to the IIOS EventBus. Downstream components subscribe to lifecycle events to stay current with entity state changes.

**Published lifecycle events:**

| Event | Published when | Consumers |
|---|---|---|
| `entity.created` | Entity transitions to CREATED | Knowledge Engine, Audit Manager, Dashboard |
| `entity.activated` | Entity transitions to ACTIVE | All layers (depends on entity type) |
| `entity.updated` | Any attribute update on ACTIVE entity | Depends on entity type |
| `entity.deprecated` | Entity deprecated | All consumers of that entity |
| `entity.archived` | Entity archived | LearningSystem, Dashboard |
| `entity.retired` | Entity retired | Dashboard, Audit |
| `entity.merged` | Merge completed | All components holding reference to merged entity |
| `entity.split` | Split completed | All components holding reference to split entity |
| `entity.restored` | Entity restored from archive | All components |

---
## PART V — ENTITY SERVICES

### 5.1 Service Architecture Overview

Entity Services are the external interface through which all other IIOS components interact with the Entity Engine. No component accesses entity data or performs entity operations directly — all entity interactions go through one of the eleven Entity Services.

Services are stateless — they do not hold entity data between calls. They coordinate the underlying Entity Engine components to fulfil each request. Services are the only authorised callers of Entity Engine internal components.

```
ENTITY SERVICE INTERFACE MAP

External Consumer                   Entity Services                 Engine Components
─────────────────    ──────────────────────────────────    ─────────────────────────────
OrderManager     ──► Registration Service          ──►      Registry + Factory + Validator
StrategyLab      ──► Validation Service            ──►      Validator + Catalog
All Layers       ──► Search Service                ──►      Search Engine + Index
All Layers       ──► Query Service                 ──►      Cache + Index + Registry
LearningSystem   ──► History Service               ──►      History Manager + Version Manager
Entity Engine    ──► Merge Service                 ──►      Identity Manager + Lifecycle Manager
Entity Engine    ──► Split Service                 ──►      Lifecycle Manager + Version Manager
All Writers      ──► Version Service               ──►      Version Manager
All Layers       ──► Cache Service                 ──►      Entity Cache
Audit System     ──► Audit Service                 ──►      Audit Manager
Governance       ──► Governance Service            ──►      Governance Manager
```

---

### 5.2 Entity Registration Service

**Purpose:** The Registration Service is the entry point for all new entity creation. Consumers call the Registration Service whenever they need to create a new entity.

**Service specification:**

| Attribute | Detail |
|---|---|
| **Purpose** | Create and register a new entity in the IIOS entity population |
| **Service authority** | Entity Factory (creation) + Entity Registry (enrollment) + Entity Validator (validation) |
| **Operation** | WRITE — creates persistent records |
| **Idempotency** | Idempotent when called with an idempotency_key (same key returns same entity) |
| **Transactional** | Full creation is atomic — either complete or fully rolled back |

**Inputs:**

| Input | Type | Required | Description |
|---|---|---|---|
| `entity_type` | EntityType enum | Yes | Type of entity to create |
| `creation_params` | dict | Yes | All required and optional attribute values |
| `owner_id` | string | Yes | The service/actor creating the entity |
| `idempotency_key` | string | No | Prevents duplicate creation for the same domain event |
| `source_entity_id` | UUID4 | No | Parent entity (for child entities in an aggregate) |
| `tags` | List[string] | No | Initial tags |
| `metadata` | dict | No | Initial metadata |

**Outputs:**

| Output | Type | Description |
|---|---|---|
| `entity` | EntityRecord | The fully created entity (current version) |
| `entity_id` | UUID4 | The permanent entity identifier |
| `was_idempotent` | bool | True if an existing entity was returned due to idempotency key match |
| `validation_errors` | List[str] | Populated only if creation failed validation (entity not created) |

**Dependencies:**

| Dependency | Role |
|---|---|
| Entity Validator | Validates creation parameters before entity is created |
| Entity Factory | Executes the creation sequence |
| Entity Registry | Enrolls the new entity |
| Entity Audit Manager | Records the ENTITY_CREATED audit event |
| Entity Cache | Populates cache with the new entity |

**Consumers:** OrderManager (orders, fills), StrategyLab (strategies, evolved variants, hypotheses), TradeMonitor (trades, positions), MarketIntelligence (regime changes), LearningEngine (learning records), all 17 layers for system entities (cycles, jobs).

**Failure handling:**

| Failure | Response |
|---|---|
| ValidationError | Return error list; entity not created; Registry enrollment rolled back |
| Duplicate creation (no idempotency key) | Return EntityDuplicateError with existing entity_id |
| Duplicate creation (with idempotency key) | Return existing entity with `was_idempotent = True` |
| Registry write failure | Raise RegistryWriteError; entity not created |
| Unexpected error | Raise EntityServiceError; full rollback; error logged with full context |

---

### 5.3 Entity Validation Service

**Purpose:** The Validation Service provides standalone entity validation — validating entities that already exist (re-validation) or validating proposed update parameters before applying them.

**Service specification:**

| Attribute | Detail |
|---|---|
| **Purpose** | Validate entity data against all defined constraints |
| **Operation** | READ (no entity is modified) |
| **Use cases** | Pre-flight validation before update; scheduled re-validation; integrity checks |

**Inputs:**

| Input | Type | Required | Description |
|---|---|---|---|
| `entity_id` | UUID4 | No | Validate an existing entity (re-validation) |
| `entity_type` | EntityType | No | Required when entity_id not provided |
| `data` | dict | Yes | The entity data or update parameters to validate |
| `validation_level` | ValidationLevel enum | No | STRUCTURAL, REFERENTIAL, BUSINESS (default: ALL) |

**Outputs:**

| Output | Type | Description |
|---|---|---|
| `is_valid` | bool | True if all checks pass |
| `validation_results` | List[ValidationResult] | Detailed result per check |
| `violated_rules` | List[str] | Rule IDs that were violated |
| `severity_breakdown` | dict | Count of ERROR, WARNING, INFO findings |

**Dependencies:** Entity Validator, Entity Catalog, Entity Registry (for cross-reference checks).

**Consumers:** All services that modify entities; StrategyLab before activating evolved variants; RiskGuardian before applying new risk thresholds; scheduled integrity checks.

**Failure handling:** The Validation Service never raises errors for validation failures — validation failures are returned as structured results. Service errors (connectivity, timeout) are raised as `ValidationServiceError` and are retried with exponential backoff up to 3 attempts.

---

### 5.4 Entity Search Service

**Purpose:** The Search Service provides flexible discovery of entities based on criteria. It is designed for infrequent, exploratory queries (not for cycle-time hot paths).

**Service specification:**

| Attribute | Detail |
|---|---|
| **Purpose** | Discover entities matching specified criteria |
| **Operation** | READ — no entity modifications |
| **Performance target** | < 100 ms for single-index queries; < 500 ms for composite queries |
| **Not suitable for** | Cycle-time hot paths (use Query Service or Cache Service instead) |

**Inputs:**

| Input | Type | Required | Description |
|---|---|---|---|
| `query` | SearchQuery | Yes | Structured query with criteria, filters, ordering |
| `entity_types` | List[EntityType] | No | Restrict to specific entity types |
| `limit` | int | No | Maximum results (default 100, max 1000) |
| `offset` | int | No | Pagination offset |
| `include_archived` | bool | No | Whether to include ARCHIVED entities |
| `include_retired` | bool | No | Whether to include RETIRED entities |

**SearchQuery structure:**

| Field | Description |
|---|---|
| `text` | Full-text search string |
| `attribute_filters` | List of (attribute_name, operator, value) triples |
| `tag_filters` | Required tags |
| `status_filters` | Required lifecycle states |
| `date_range` | Created/updated date range |
| `relationship_filters` | Entities related to a specified entity |
| `sort_by` | Attribute to sort by |
| `sort_direction` | ASC or DESC |

**Outputs:**

| Output | Type | Description |
|---|---|---|
| `results` | List[EntitySummary] | Matching entities (summaries, not full records) |
| `total_count` | int | Total matching entities (before limit/offset) |
| `query_time_ms` | float | Query execution time |
| `index_used` | str | Which index was used to answer the query |

**Dependencies:** Entity Search Engine, Entity Index.

**Consumers:** Telegram bot search commands, dashboard entity browser, Knowledge Engine entity discovery, ResearchLab strategy analysis.

**Failure handling:** Timeouts return partial results with a `truncated = True` flag. Index unavailability falls back to slow full-scan with a warning.

---

### 5.5 Entity Query Service

**Purpose:** The Query Service provides high-performance, purpose-built lookups for the specific access patterns used in cycle-time operations. Unlike Search, Query is designed for exact lookups that must complete in under 2 ms.

**Service specification:**

| Attribute | Detail |
|---|---|
| **Purpose** | Fast entity retrieval for cycle-time hot paths |
| **Operation** | READ |
| **Performance target** | < 2 ms from cache; < 20 ms from persistence on cache miss |
| **Primary path** | Entity Cache (hot entities always served from memory) |

**Query methods:**

| Method | Description | Target latency |
|---|---|---|
| `get_by_id(entity_id)` | Retrieve any entity by UUID4 | < 1 ms (from cache) |
| `get_by_type(entity_type, status)` | List all entities of a type in a status | < 2 ms (from index) |
| `get_by_symbol(symbol, entity_type)` | All entities for a specific symbol | < 2 ms (from index) |
| `get_active_portfolio()` | Return the single active Portfolio entity | < 0.5 ms (L1 cache) |
| `get_active_risk_threshold()` | Return all active risk threshold entities | < 0.5 ms (L1 cache) |
| `get_kill_switch_state()` | Return the current KillSwitch entity | < 0.5 ms (L1 cache) |
| `get_active_strategies()` | Return all ACTIVE Strategy entities | < 2 ms (from index + cache) |
| `get_open_positions()` | Return all OPEN Position entities | < 2 ms (from index + cache) |
| `get_children(parent_entity_id, child_type)` | Return all child entities of a parent | < 2 ms (from index) |
| `exists(entity_id)` | Check if an entity exists (boolean) | < 0.5 ms (from Registry) |

**Inputs:** Method-specific (see table above). All methods accept `entity_id` or typed identifiers.

**Outputs:** Full entity records (current version). All outputs are served from cache by default.

**Dependencies:** Entity Cache, Entity Index, Entity Registry.

**Consumers:** All 17 IIOS layers during cycle execution. This is the most frequently called service in the entire entity engine.

**Failure handling:** Cache misses on critical entities (KillSwitch, Portfolio, RiskThreshold) trigger immediate persistence reads. Cache misses on non-critical entities trigger asynchronous cache population and return from persistence. If persistence read fails for a critical entity, raise `CriticalEntityUnavailableError` and abort the current cycle.

---

### 5.6 Entity History Service

**Purpose:** The History Service provides access to the temporal history of any entity — the sequence of states it has been through over its lifetime.

**Service specification:**

| Attribute | Detail |
|---|---|
| **Purpose** | Retrieve entity history for analysis, audit, and learning |
| **Operation** | READ — no entity modifications |
| **Performance** | Not cycle-time; acceptable latency is 50–500 ms for complex history queries |

**Inputs:**

| Input | Type | Required | Description |
|---|---|---|---|
| `entity_id` | UUID4 | Yes | Entity to retrieve history for |
| `from_version` | int | No | Start version (default 1) |
| `to_version` | int | No | End version (default current) |
| `from_timestamp` | datetime | No | Start timestamp |
| `to_timestamp` | datetime | No | End timestamp |
| `fields` | List[str] | No | Only return these specific fields in history |
| `include_diffs` | bool | No | Include field-level diffs between versions |

**Outputs:**

| Output | Type | Description |
|---|---|---|
| `versions` | List[VersionRecord] | Ordered list of version records |
| `point_in_time_state` | EntityRecord | Entity state at specified timestamp |
| `field_history` | dict | Per-field value history |
| `update_count` | int | Total number of updates in range |
| `change_frequency` | float | Average updates per day in range |

**Dependencies:** Entity History Manager, Entity Version Manager.

**Consumers:** LearningEngine (strategy performance history), PerformanceAnalytics (drawdown history), Telegram bot `/history` commands, ResearchLab (strategy evolution analysis), Audit system (historical reconstruction).

**Failure handling:** If version records are corrupted or missing, return available versions with a `has_gaps = True` flag. Raise `HistoryCorruptionError` for gaps in version sequences and trigger an integrity check.

---

### 5.7 Entity Merge Service

**Purpose:** The Merge Service combines two entities that have been identified as duplicates into a single canonical entity.

**Service specification:**

| Attribute | Detail |
|---|---|
| **Purpose** | Resolve entity duplicates by merging two records into one |
| **Operation** | WRITE — modifies both entities and all their references |
| **Authorization** | Requires Human Principal approval for financial entities; automatic for reference entities |
| **Transactional** | Fully atomic — either complete merge or full rollback |

**Inputs:**

| Input | Type | Required | Description |
|---|---|---|---|
| `primary_entity_id` | UUID4 | Yes | The entity that will survive the merge |
| `secondary_entity_id` | UUID4 | Yes | The entity that will be absorbed |
| `merge_strategy` | MergeStrategy enum | Yes | PREFER_PRIMARY, PREFER_SECONDARY, UNION, MANUAL |
| `field_overrides` | dict | No | Manual field selections for MANUAL merge strategy |
| `authorization_token` | string | Conditional | Required for financial entities |
| `merge_reason` | string | Yes | Human-readable reason for the merge |

**Outputs:**

| Output | Type | Description |
|---|---|---|
| `merged_entity` | EntityRecord | The resulting merged entity (primary, updated) |
| `references_updated` | int | Count of entity references updated to primary_id |
| `merge_id` | UUID4 | The merge operation record identifier |

**Dependencies:** Entity Identity Manager, Entity Lifecycle Manager, Entity Registry, Entity Audit Manager, Entity Version Manager.

**Consumers:** Identity Manager (post-duplicate-detection), Human Principal (manual merge instructions), Data quality processes.

**Failure handling:** If reference updates partially fail, the merge is rolled back. If references are found that cannot be updated (locked by active transaction), the merge is queued and retried. A merge failure audit event is always created.

---

### 5.8 Entity Split Service

**Purpose:** The Split Service divides a single entity into two separate entities when a domain modelling error is discovered.

**Service specification:**

| Attribute | Detail |
|---|---|
| **Purpose** | Divide one entity into two separate, distinct entities |
| **Operation** | WRITE — creates two entities, transitions original to SPLIT |
| **Authorization** | Always requires Human Principal approval |
| **Transactional** | Fully atomic |

**Inputs:**

| Input | Type | Required | Description |
|---|---|---|---|
| `source_entity_id` | UUID4 | Yes | The entity to split |
| `split_definition_a` | dict | Yes | Attribute assignment for successor-A |
| `split_definition_b` | dict | Yes | Attribute assignment for successor-B |
| `reference_routing` | dict | No | How to route existing references to A or B |
| `authorization_token` | string | Yes | Required always |
| `split_reason` | string | Yes | Human-readable reason |

**Outputs:**

| Output | Type | Description |
|---|---|---|
| `entity_a` | EntityRecord | First successor entity |
| `entity_b` | EntityRecord | Second successor entity |
| `original_status` | EntityStatus | SPLIT (original entity state) |
| `references_routed` | int | References successfully routed to A or B |

**Dependencies:** Entity Lifecycle Manager, Entity Factory (creates two new entities), Entity Audit Manager, Entity Version Manager.

**Consumers:** Human Principal (only authorised caller). Split is never performed automatically.

**Failure handling:** Any failure during the creation of successors A or B triggers a full rollback. The source entity remains ACTIVE if the split fails.

---

### 5.9 Entity Version Service

**Purpose:** The Version Service provides structured access to entity versioning — creating explicit milestone versions and retrieving version information.

**Service specification:**

| Attribute | Detail |
|---|---|
| **Purpose** | Manage entity version records; provide version access |
| **Operation** | READ (version retrieval) and WRITE (milestone version creation) |

**Version Service operations:**

| Operation | Description |
|---|---|
| `create_milestone_version(entity_id, label, reason)` | Create an explicitly labelled milestone version |
| `get_version(entity_id, version_number)` | Retrieve a specific version of an entity |
| `get_current_version(entity_id)` | Retrieve the current (latest) version |
| `list_versions(entity_id)` | List all version numbers with timestamps |
| `diff_versions(entity_id, v1, v2)` | Return field-level differences between two versions |
| `rollback_version(entity_id, target_version)` | Roll back to a specific version (requires authorisation) |

**Dependencies:** Entity Version Manager, Entity Audit Manager, Entity History Manager.

**Consumers:** StrategyLab (milestone versions on strategy evolution), Human Principal (rollback operations), LearningEngine (version comparison for learning records).

**Failure handling:** Version rollback requires Human Principal authorisation token. Failed rollbacks are fully reverted. All version operations create audit records.

---

### 5.10 Entity Cache Service

**Purpose:** The Cache Service provides direct cache management operations — warming, invalidating, and inspecting the entity cache.

**Service specification:**

| Attribute | Detail |
|---|---|
| **Purpose** | Manage entity cache state and provide cache diagnostic operations |
| **Operation** | CACHE MANAGEMENT — no persistent entity modifications |

**Cache Service operations:**

| Operation | Description |
|---|---|
| `warm_cache(entity_types)` | Pre-load specified entity types into cache |
| `invalidate(entity_id)` | Remove a specific entity from cache (forces next access to hit persistence) |
| `invalidate_type(entity_type)` | Remove all entities of a type from cache |
| `get_cache_stats()` | Return cache hit/miss/eviction statistics |
| `get_cache_inventory()` | Return list of entities currently in each cache tier |
| `set_cache_priority(entity_id, priority)` | Adjust cache priority for a specific entity |

**Dependencies:** Entity Cache.

**Consumers:** MasterOrchestrator (pre-market cache warm-up), System Monitor (cache health diagnostics), all components that know when their entities have been updated externally.

**Failure handling:** Cache warm-up failures are logged as warnings — the system remains operational without the cache (slower, but correct). Cache invalidation failures are retried up to 3 times.

---

### 5.11 Entity Audit Service

**Purpose:** The Audit Service provides access to the entity audit log — for querying, reporting, and compliance purposes.

**Service specification:**

| Attribute | Detail |
|---|---|
| **Purpose** | Query and export entity audit records |
| **Operation** | READ — audit log is never modified |
| **Access control** | All reads are themselves logged |

**Audit Service operations:**

| Operation | Description |
|---|---|
| `get_audit_log(entity_id)` | Retrieve all audit events for an entity |
| `get_audit_events_by_type(event_type, date_range)` | Retrieve all events of a specific type |
| `get_audit_events_by_actor(actor_id, date_range)` | Retrieve all events by a specific actor |
| `generate_compliance_report(entity_type, date_range)` | Generate a compliance audit report |
| `get_daily_event_summary(date)` | Summary count of all event types on a date |
| `verify_audit_integrity(entity_id)` | Verify audit chain integrity for an entity |

**Dependencies:** Entity Audit Manager, Entity Registry.

**Consumers:** Human Principal (compliance audits), ControlTower dashboard (audit views), Telegram bot `/audit` commands, external compliance reporting.

**Failure handling:** Audit queries are always served from the persistence layer (never from cache). Query timeouts return partial results. Integrity verification failures raise `AuditIntegrityError`.

---

### 5.12 Entity Governance Service

**Purpose:** The Governance Service provides all governance operations — ownership management, policy enforcement, compliance monitoring, and governance reporting.

**Service specification:**

| Attribute | Detail |
|---|---|
| **Purpose** | Enforce and monitor entity governance policies |
| **Operation** | READ (monitoring/reporting) and WRITE (governance actions) |

**Governance Service operations:**

| Operation | Description |
|---|---|
| `get_entity_owner(entity_id)` | Return current owner |
| `transfer_ownership(entity_id, new_owner, reason)` | Transfer entity ownership |
| `get_governance_status(entity_id)` | Return complete governance status (classification, compliance, health) |
| `enforce_policies(entity_type)` | Run all governance policies for an entity type and report violations |
| `generate_governance_report(date_range)` | Generate a governance health report |
| `approve_entity(entity_id, approver, notes)` | Record governance approval for an entity |
| `flag_entity(entity_id, reason, severity)` | Flag an entity for governance review |

**Dependencies:** Entity Governance Manager, Entity Registry, Entity Audit Manager.

**Consumers:** Human Principal, ControlTower dashboard, scheduled governance compliance checks.

**Failure handling:** Governance policy enforcement failures are recorded as governance violations (not system errors). The system continues operating — governance is advisory except for `CRITICAL` severity violations, which trigger Human Principal notification via Telegram.

---
## PART VI — ENTITY IDENTITY FRAMEWORK

### 6.1 Identity Philosophy

Identity is the answer to the question: **"Is this the same thing I knew about before?"**

In the IIOS, identity is not merely a database key — it is the philosophical foundation that allows the system to accumulate understanding over time. Without stable identity, the learning system cannot associate a new trade outcome with the strategy that generated it. Without stable identity, the audit system cannot trace an order back to the hypothesis that proposed it. Without stable identity, the risk system cannot know whether a new position increases or decreases an existing exposure.

The Entity Identity Framework defines how identity is established, maintained, resolved, and protected across the full lifecycle of every entity in the system.

---

### 6.2 Global Entity IDs

**Design:** Every entity in the IIOS is assigned a **UUID4** (Universally Unique Identifier, version 4) at creation time. This identifier is the entity's global, permanent, immutable identity.

**UUID4 properties that make it suitable for entity identity:**
- **Globally unique:** The probability of collision is astronomically small (2^-122 per generation)
- **No coordination required:** Generated independently by the Factory without consulting any external authority
- **No embedded information:** UUID4 carries no timestamp, no sequence, no process ID — it is pure randomness, which means it cannot be guessed, predicted, or enumerated
- **Fixed length:** 36 characters in canonical form (8-4-4-4-12)

**Canonical representation:** `xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx` where x is random hexadecimal and y is 8, 9, a, or b.

**Example:** `3fa85f64-5717-4562-b3fc-2c963f66afa6`

**ID assignment rules:**

| Rule | Description |
|---|---|
| EID-ID-01 | UUID4 is assigned by the Entity Factory — never by the caller |
| EID-ID-02 | UUID4 is assigned exactly once — at creation |
| EID-ID-03 | UUID4 is never reused — even after entity retirement |
| EID-ID-04 | UUID4 is stored as the first field in every entity record |
| EID-ID-05 | UUID4 must be included in every API response involving an entity |

---

### 6.3 Aliases

**Purpose:** Aliases are human-readable or business-meaningful names that may be used to refer to an entity in addition to its canonical UUID4.

**When aliases are used:**
- `Strategy` entities have aliases like "MomentumBreakoutV3" or "EMA-Cross-NIFTY-BULL"
- `Symbol` entities have aliases like "TATASTEEL" (NSE code), "TATASTL" (older code), "TATA Steel" (company name)
- `Agent` entities have aliases like "momentum_bull_agent" (functional name)
- `DataFeed` entities have aliases like "yfinance_primary", "dhan_market_feed"

**Alias rules:**

| Rule | Description |
|---|---|
| EID-ALIAS-01 | Aliases are unique within an entity type (two strategies cannot share the same alias) |
| EID-ALIAS-02 | Aliases are registered through the Identity Manager — not set directly on the entity |
| EID-ALIAS-03 | Multiple aliases may exist for a single entity |
| EID-ALIAS-04 | Aliases may change over time (with audit) |
| EID-ALIAS-05 | Resolution of an alias always returns the canonical entity_id |

**Alias resolution:** All IIOS services accept both UUID4 and aliases as inputs. The Identity Manager transparently resolves aliases to entity IDs before routing the request.

---

### 6.4 External IDs

**Purpose:** External IDs are identifiers assigned by external systems — broker systems, exchanges, market data providers, regulatory bodies — that the IIOS must track to correlate internal entities with external records.

**External ID catalogue:**

| External System | ID type | Entity type | Example |
|---|---|---|---|
| Dhan broker | `dhan_order_id` | Order | `"1234567890"` |
| Dhan broker | `dhan_trade_id` | Trade | `"TRD9876543"` |
| NSE | `exchange_order_id` | Order | `"NSE-OID-20260702-001234"` |
| NSE | `isin` | Symbol / ListedSecurity | `"INE081A01020"` |
| Bloomberg | `bbgid` | Symbol | `"BBG000BVPXP1"` |
| Reuters | `ric` | Symbol | `"TISC.NS"` |
| RBI | `category_code` | MacroIndicator | `"WPI-OVERALL"` |

**External ID management:**

| Rule | Description |
|---|---|
| EID-EXT-01 | External IDs are stored in the Metadata Manager, not in core entity fields |
| EID-EXT-02 | Each external system gets its own namespace in the external ID map |
| EID-EXT-03 | External IDs are indexed for lookup (resolve external_id → entity_id) |
| EID-EXT-04 | A single entity may have external IDs from multiple systems |
| EID-EXT-05 | External IDs may change (e.g., broker resets order ID sequence) — the history of external IDs is preserved |

---

### 6.5 Version IDs

**Purpose:** Each version of an entity — each historical snapshot — has its own Version ID (UUID4). Version IDs allow pinpoint access to a specific state of an entity at a specific moment in time.

**Version ID assignment:** The Version Manager assigns a new UUID4 Version ID every time a new version record is created. The Version ID is separate from the entity's `entity_id` — the `entity_id` identifies the entity, the `version_id` identifies a specific state of that entity.

**Version ID significance:**

- **Immutability anchor:** A Version ID uniquely and permanently identifies the exact state of an entity at a point in time. Given a Version ID, the same state can always be retrieved.
- **Audit reference:** Audit events reference the `version_id` at the time of the event — not just the entity_id and timestamp. This makes audit reconstruction unambiguous.
- **Reproducibility:** BacktestResult entities reference the specific version IDs of the strategies and parameters they used — so the backtest can be exactly reproduced by loading those specific versions.

---

### 6.6 Reference IDs

**Purpose:** Reference IDs are entity-type-specific, human-friendly identifiers that follow a defined naming convention for readability and operational use.

**Reference ID naming conventions:**

| Entity type | Format | Example |
|---|---|---|
| Order | `ORD-{YYYYMMDD}-{sequence:06d}` | `ORD-20260702-000001` |
| Trade | `TRD-{YYYYMMDD}-{sequence:06d}` | `TRD-20260702-000001` |
| Position | `POS-{symbol}-{YYYYMMDD}` | `POS-TATASTEEL-20260702` |
| Strategy | `STR-{name_slug}-{version}` | `STR-MOMBREAK-V3` |
| Hypothesis | `HYP-{strategy_id_short}-{YYYYMMDD}-{seq}` | `HYP-MOMBRK-20260702-001` |
| Cycle | `CYC-{YYYYMMDD}-{HHMMSS}` | `CYC-20260702-093000` |
| Regime | `REG-{type}-{start_date}` | `REG-BULL-20260601` |
| Agent | `AGT-{name}` | `AGT-MOMENTUM-BULL` |

**Reference ID rules:**

| Rule | Description |
|---|---|
| EID-REF-01 | Reference IDs are generated automatically by the Factory |
| EID-REF-02 | Reference IDs are unique within their entity type for their date scope |
| EID-REF-03 | Reference IDs are indexable and searchable |
| EID-REF-04 | The canonical identity remains the UUID4 — the Reference ID is supplementary |
| EID-REF-05 | Reference IDs are immutable after assignment |

---

### 6.7 Canonical Identity

**Purpose:** Canonical identity is the definitive, system-authoritative identity of an entity — its UUID4 `entity_id`. All other identifiers (aliases, external IDs, reference IDs) are subordinate to the canonical identity.

**Canonical identity rules:**

| Rule | Description |
|---|---|
| EID-CAN-01 | One entity, one canonical identity |
| EID-CAN-02 | The canonical identity never changes after assignment |
| EID-CAN-03 | All other identifiers resolve through the Identity Manager to the canonical identity |
| EID-CAN-04 | All entity operations use the canonical identity as the primary key |
| EID-CAN-05 | In a merge, the primary entity's canonical identity becomes the canonical identity for the merged entity |

**Identity hierarchy:**

```
Any identifier presented to the IIOS
         │
         ▼
[Identity Manager: What type of identifier is this?]
         │
    ┌────┼──────────┬──────────┬──────────────┐
    ▼    ▼          ▼          ▼              ▼
 UUID4  Alias  External ID  Reference ID  Unknown
    │    │          │          │              │
    │    ▼          ▼          ▼              ▼
    │  [Alias   [ExtID      [RefID         Error:
    │   Index]   Index]      Index]    UnknownIdentifier
    │    │          │          │
    └────┴──────────┴──────────┘
                  │
                  ▼
        Canonical entity_id (UUID4)
                  │
                  ▼
         Entity record returned
```

---

### 6.8 Identity Resolution

**Purpose:** Identity resolution is the process of converting any identifier — UUID4, alias, external ID, reference ID — into the canonical `entity_id`. This is performed by the Identity Manager transparently at service boundaries.

**Resolution process:**

1. Receive identifier string from caller
2. Detect identifier type (UUID4 format → direct lookup; else → index search)
3. Consult appropriate index (alias index, external ID index, reference ID index)
4. Return canonical entity_id
5. If not found: raise `IdentityResolutionError`

**Resolution performance targets:**

| Identifier type | Resolution target |
|---|---|
| UUID4 (canonical) | < 0.1 ms (direct registry lookup) |
| Alias | < 0.5 ms (in-memory alias index) |
| Reference ID | < 0.5 ms (in-memory reference ID index) |
| External ID | < 1 ms (indexed external ID map) |

**Resolution cache:** The Identity Manager maintains an in-memory resolution cache. All non-UUID4 identifiers that have been resolved are cached (entity_id → canonical_id mapping) for the duration of the system session. Cache invalidation occurs on entity merge (secondary's identifiers now resolve to primary).

---

### 6.9 Duplicate Detection

**Purpose:** Duplicate detection is the proactive identification of entities that represent the same domain object but have been created with separate `entity_id` values.

**How duplicates arise:**

| Scenario | Example |
|---|---|
| Network retry creates second entity | Order creation request timed out; retried without idempotency key; broker received both |
| Reference data import conflict | Symbol master import creates TATASTEEL entity; manual creation also creates TATASTEEL |
| Feed fallback creates parallel entity | Dhan feed creates Symbol entity; yfinance fallback creates another |
| Historical migration creates overlap | Migrated data creates entity that already exists in live database |

**Duplicate detection methods:**

| Method | Description | Applied to |
|---|---|---|
| Idempotency key check | Caller provides key; Factory checks before creation | All creation operations |
| Exact field match | All required fields match between two entities | During reference data import |
| External ID collision | Two entities have the same external ID for the same system | During External ID registration |
| Alias collision | Two entities of the same type have the same alias | During alias registration |
| Similarity scoring | Fuzzy match on display name and type-specific fields | Scheduled duplicate scan |

**Duplicate detection scanning:**

A scheduled duplicate detection scan runs nightly (after market hours). It checks the entity population for potential duplicates using:
- Exact match on unique fields
- Fuzzy name matching (Levenshtein distance < 0.1) within same entity type
- External ID collision analysis

Detected duplicates are flagged in the governance queue for Human Principal review. Automatic merging is performed only for reference entities (Symbols, Companies) with confirmed identical ISIN codes.

---

### 6.10 Identity Conflict Resolution

**Purpose:** When identity conflicts arise — two entities that might be duplicates, or a new external ID that matches an existing entity's external ID — the conflict resolution process determines the correct outcome.

**Conflict resolution decision matrix:**

| Conflict type | Resolution strategy | Authority |
|---|---|---|
| Identical external ID, same entity type | Automatic merge (primary = older entity) | Identity Manager |
| Identical ISIN code | Automatic merge + notification | Identity Manager |
| Fuzzy name match (confidence > 0.95) | Flag for review; do not merge | Human Principal |
| Fuzzy name match (confidence 0.80–0.95) | Flag for review; tentative alias added | Human Principal |
| Fuzzy name match (confidence < 0.80) | No action | N/A |
| Idempotency key match | Return existing entity; no merge needed | Factory (automatic) |
| Financial entity conflict | Always escalate to Human Principal | Human Principal |

**Conflict resolution audit:** Every identity conflict — detected, reviewed, resolved, or dismissed — is recorded as a governance audit event. The resolution decision and the authority who made it are permanently logged.

---
## PART VII — ENTITY QUALITY

### 7.1 Quality Philosophy

Entity quality is not an afterthought — it is a first-class property of every entity in the IIOS. A low-quality entity is not merely an inconvenience; it is a risk. A strategy entity with missing backtesting data may be incorrectly approved for live trading. A position entity with stale P&L may cause incorrect risk calculations. A regime entity with low confidence may cause the system to deploy the wrong strategies.

The Entity Quality Framework defines ten dimensions of entity quality, a scoring methodology that combines them into a composite quality score, and a quality governance process that ensures low-quality entities are flagged, improved, or retired.

---

### 7.2 Quality Dimension 1: Completeness

**Definition:** Completeness measures the degree to which all required and expected fields of an entity are populated.

**Measurement:**

$$\text{Completeness} = \frac{\text{Populated Fields}}{\text{Expected Fields}}$$

Where:
- **Required fields:** Fields that must be populated (missing = validation failure)
- **Expected fields:** All fields that should be populated for a complete entity (optional fields that should have values for this entity type in this state)

**Completeness scoring:**

| Score | Interpretation |
|---|---|
| 1.00 | All fields populated |
| 0.90–0.99 | Minor gaps (optional secondary fields) |
| 0.70–0.89 | Notable gaps (expected but optional enrichment fields) |
| 0.50–0.69 | Significant gaps (important optional fields missing) |
| < 0.50 | Severely incomplete — flag for immediate review |

**Completeness by entity type:** Each entity type has a defined completeness weight — the set of fields that count in the completeness calculation, and whether each is required or expected. This is maintained in the Entity Catalog.

---

### 7.3 Quality Dimension 2: Integrity

**Definition:** Integrity measures whether the entity satisfies all defined invariants and business rules — internal consistency.

**Integrity check categories:**

| Category | Description | Example |
|---|---|---|
| Structural invariants | Field types, ranges, and formats | `price > 0`, `quantity > 0` |
| Relational invariants | Fields are consistent with each other | `exit_price` only set when `status = CLOSED` |
| Aggregate invariants | Entity is consistent with its aggregate | Position.quantity matches sum of fills |
| Temporal invariants | Timestamps are logically ordered | `closed_at > opened_at` |

**Integrity scoring:**

$$\text{Integrity} = 1 - \frac{\text{Violated Invariants}}{\text{Total Invariants Checked}}$$

An entity with any CRITICAL invariant violation has an integrity score of 0.0 regardless of other checks.

---

### 7.4 Quality Dimension 3: Consistency

**Definition:** Consistency measures whether the entity's attributes are consistent with related entities in the system.

**Consistency checks:**

| Check | Description |
|---|---|
| Cross-entity consistency | Fields that must match between related entities (e.g., Order.symbol must match Position.symbol for the same trade) |
| Regime consistency | Active strategies are consistent with the current regime |
| Historical consistency | Entity's current state is reachable from its initial state via recorded transitions |
| Reference data consistency | Entity references to reference data (symbols, sectors) are consistent with current reference master |

**Consistency scoring:**

$$\text{Consistency} = \frac{\text{Consistent Cross-Checks Passed}}{\text{Total Cross-Checks Applied}}$$

---

### 7.5 Quality Dimension 4: Validity

**Definition:** Validity measures whether the entity's field values are valid in the context of the current system state — not just structurally valid, but domain-valid.

**Validity dimensions:**

| Dimension | Description |
|---|---|
| Domain validity | Values within allowed domain ranges (e.g., `confidence` in [0.0, 1.0]) |
| Temporal validity | Timestamps within expected ranges (not in the future, not too far in the past) |
| Referential validity | Referenced entities exist and are in valid states |
| Business validity | Values make business sense (e.g., stop-loss price below entry price for a LONG position) |

**Validity scoring:**

$$\text{Validity} = \frac{\text{Valid Fields}}{\text{Total Fields Validated}}$$

---

### 7.6 Quality Dimension 5: Accuracy

**Definition:** Accuracy measures whether the entity's values reflect ground truth — whether they are correct, not merely valid.

**Accuracy sources:** Accuracy cannot always be directly measured — it depends on comparison to a known truth source. For different entity types:

| Entity type | Accuracy source |
|---|---|
| Order | Broker confirmation matches IIOS order record |
| Trade | P&L matches executed fill prices |
| Position | Current position matches broker portfolio snapshot |
| Regime | Regime classification matches post-hoc analysis |
| MacroIndicator | IIOS value matches authoritative macro source |

**Accuracy scoring:** Accuracy is scored on a per-entity-type basis using comparison to available ground truth. When ground truth is not available, accuracy is marked as UNKNOWN (0.5 default).

---

### 7.7 Quality Dimension 6: Freshness

**Definition:** Freshness measures whether the entity's data is current — whether it has been updated recently enough to be trusted.

**Freshness standards by entity type:**

| Entity type | Maximum staleness for FRESH | STALE threshold | CRITICAL STALE threshold |
|---|---|---|---|
| Position | 1 cycle (30s) | 5 minutes | 15 minutes |
| Regime | 1 cycle | 30 minutes | 2 hours |
| RiskThreshold | Session start | 24 hours | 1 week |
| MacroIndicator | 1 hour | 4 hours | 24 hours |
| Symbol (price) | 1 minute | 5 minutes | 30 minutes |
| KnowledgeRecord | 7 days | 30 days | 90 days |
| Strategy (parameters) | 30 days | 90 days | 180 days |

**Freshness scoring:**

$$\text{Freshness} = \max\left(0, 1 - \frac{\text{time\_since\_update}}{\text{max\_staleness}}\right)$$

---

### 7.8 Quality Dimension 7: Confidence

**Definition:** Confidence measures the system's degree of certainty that the entity's values are correct — separate from accuracy (which compares to truth) and validity (which checks rules).

**Confidence sources:**

| Entity type | Confidence source |
|---|---|
| Regime | Ensemble model agreement score |
| Hypothesis | Agent ensemble agreement (debate score) |
| KnowledgeRecord | Evidence volume and consistency |
| MacroIndicator | Source reliability score × data latency factor |
| EvolvedVariant | Backtest + walk-forward result quality |

**Confidence scoring:** Confidence is entity-type-specific and is computed by the relevant intelligence layer at entity creation or update time. The confidence value is stored directly on the entity and contributes to the quality score.

---

### 7.9 Quality Dimension 8: Traceability

**Definition:** Traceability measures the degree to which the entity's origin, derivation, and history can be fully reconstructed from available records.

**Traceability elements:**

| Element | Description |
|---|---|
| Lineage record | Complete derivation path from source data to this entity |
| Version history | Full version chain from creation to current state |
| Audit trail | Complete event log (creation, updates, transitions, ownership changes) |
| Source references | Links to source entities, data feeds, and external inputs |
| Cycle references | The cycle(s) during which this entity was created or significantly updated |

**Traceability scoring:**

$$\text{Traceability} = \frac{\text{Available Traceability Elements}}{\text{Required Traceability Elements for this entity type}}$$

An entity with no lineage record has a Traceability score of 0.0 regardless of audit trail completeness.

---

### 7.10 Quality Dimension 9: Ownership

**Definition:** Ownership measures the clarity and currency of the entity's ownership assignment — whether it has a defined owner who is currently active.

**Ownership criteria:**

| Criterion | Description |
|---|---|
| Owner assigned | Entity has a non-null `owner_id` |
| Owner is active | The assigned owner service/component is currently running |
| Ownership is current | Ownership was confirmed within the entity's ownership review window |
| Ownership is appropriate | The assigned owner is an authorised owner for this entity type |

**Ownership scoring:**

| Condition | Score |
|---|---|
| All four criteria met | 1.00 |
| Owner assigned but not confirmed recently | 0.75 |
| Owner assigned but not currently active | 0.50 |
| No owner assigned | 0.00 (triggers governance alert) |

---

### 7.11 Quality Dimension 10: Quality Scoring

**Composite quality score formula:**

The Entity Quality Score (EQS) is a weighted composite of the nine dimensional scores:

$$\text{EQS} = w_1 \cdot C_{completeness} + w_2 \cdot C_{integrity} + w_3 \cdot C_{consistency} + w_4 \cdot C_{validity} + w_5 \cdot C_{accuracy} + w_6 \cdot C_{freshness} + w_7 \cdot C_{confidence} + w_8 \cdot C_{traceability} + w_9 \cdot C_{ownership}$$

**Default dimension weights:**

| Dimension | Default Weight | Rationale |
|---|---|---|
| Completeness | 0.10 | Important but most fields default to optional |
| Integrity | 0.20 | Highest weight — violated invariants are dangerous |
| Consistency | 0.15 | Cross-entity consistency is critical for correctness |
| Validity | 0.15 | Domain validity is foundational |
| Accuracy | 0.10 | Cannot always be measured; lower default weight |
| Freshness | 0.10 | Important but entity-type-specific |
| Confidence | 0.10 | Computed by intelligence layers; variable |
| Traceability | 0.05 | Important for audit, less for operation |
| Ownership | 0.05 | Critical governance signal but simple to satisfy |
| **Total** | **1.00** | |

**Quality score thresholds:**

| Score range | Classification | System action |
|---|---|---|
| 0.90–1.00 | EXCELLENT | No action |
| 0.75–0.89 | GOOD | Monitor |
| 0.60–0.74 | ACCEPTABLE | Flag for improvement |
| 0.40–0.59 | POOR | Governance alert; restrict use |
| 0.00–0.39 | CRITICAL | Governance alert; consider suspension |

**Weight overrides by entity type:** Entity types that are operationally critical (RiskThreshold, KillSwitch, Portfolio, Regime) have elevated integrity, freshness, and accuracy weights. Financial entities (Order, Trade, Fill) have elevated traceability and audit weights.

**Quality score update frequency:** Quality scores are recomputed:
- On every entity update
- On every cycle completion (for entities that have freshness decay)
- On the nightly integrity scan
- On-demand via the Validation Service

---

### 7.12 Quality Monitoring Dashboard

The Entity Engine exposes quality metrics to the ControlTower dashboard:

| Metric | Description |
|---|---|
| `average_quality_by_type` | Average EQS per entity type |
| `poor_quality_entity_count` | Count of entities with EQS < 0.60 |
| `critical_quality_entity_count` | Count of entities with EQS < 0.40 |
| `freshness_violations_today` | Entities that exceeded their staleness threshold today |
| `integrity_violations_today` | Entities with integrity check failures today |
| `ownership_gaps` | Entities with no owner assigned |
| `traceability_gaps` | Entities with missing lineage records |

---
## PART VIII — ENTITY GOVERNANCE

### 8.1 Governance Overview

Entity governance is the system of rules, policies, ownership assignments, approval processes, and compliance checks that ensure every entity is managed responsibly throughout its lifetime.

Governance is not bureaucracy — it is safety. In a live trading system, poor governance leads directly to financial losses: strategies that should be retired stay active, risk thresholds that have been superseded are still enforced, and entities that should have been merged accumulate as duplicates that confuse intelligence layers.

The Entity Governance Framework covers ten pillars: ownership, approval, classification, versioning, deprecation, migration, security, audit, compliance, and compatibility.

---

### 8.2 Pillar 1: Entity Ownership

Ownership defines who is responsible for each entity and what that responsibility entails.

**Ownership principles:**

| Principle | Description |
|---|---|
| Single owner | Every entity has exactly one owner at any given time |
| Owner accountability | The owner is responsible for the entity's quality, accuracy, and appropriate lifecycle management |
| Owner capability | Owners must be active, authorised components or roles |
| Owner traceability | Every ownership change is audit-logged |
| Ownership inheritance | Child entities in an aggregate inherit their owner from the aggregate root unless explicitly overridden |

**Ownership assignment by entity type:**

| Entity Category | Primary Owner | Secondary Owner (approvals) |
|---|---|---|
| Financial (Order, Fill) | OrderManager | Human Principal (for large orders) |
| Financial (Trade, Position) | TradeMonitor | OrderManager |
| Market (Symbol, Index) | DataFeedManager | Human Principal |
| Economic (Regime) | MarketIntelligence | Human Principal |
| Portfolio | PortfolioAllocation | Human Principal |
| Risk | RiskGuardian | Human Principal |
| AI (Agent, Hypothesis) | DecisionEngine | Human Principal |
| Knowledge | KnowledgeEngine | LearningEngine |
| Strategy | StrategyLab | Human Principal |
| System (Cycle, Job) | MasterOrchestrator | Human Principal |
| Reference | DataFeedManager | Human Principal |
| Derived | Generating system | LearningEngine |

**Ownership transfer:** Ownership may be transferred for valid operational reasons (e.g., a DataFeedManager is being replaced by a new implementation). Transfer requires:
- A valid transfer reason
- Confirmation that the new owner is authorised
- An audit record
- Human Principal notification (for financial entities)

---

### 8.3 Pillar 2: Approval Workflows

Some entities require explicit approval before they can become ACTIVE. Approval workflows ensure that potentially impactful entities are reviewed before they participate in live decisions.

**Entities requiring approval:**

| Entity type | Required approval | Approver |
|---|---|---|
| Strategy (NEW) | Pre-activation approval | Human Principal |
| EvolvedVariant | Promotion to production | Human Principal |
| RiskThreshold (change) | Change approval | Human Principal |
| KillSwitch (deactivation) | Deactivation approval | Human Principal |
| BudgetEnvelope (increase) | Increase approval | Human Principal |
| Agent (new) | New agent approval | Human Principal |
| StressScenario (new) | Scenario approval | Human Principal |

**Approval workflow stages:**

```
Entity created in PENDING_APPROVAL state
           │
           ▼
[Governance Manager: Notification to approver]
           │
           ▼
[Approver reviews entity and supporting data]
           │
    ┌──────┴──────┐
    ▼             ▼
APPROVED      REJECTED
    │             │
    ▼             ▼
Entity           Entity
ACTIVATED        RETIRED
                 (with rejection reason)
```

**Approval timeout:** If an approval is not received within the configured timeout (default: 24 hours for non-urgent; 4 hours for risk entities), the entity remains in PENDING_APPROVAL and a reminder notification is sent. After 3 reminder cycles with no response, the entity is automatically retired with a `APPROVAL_TIMEOUT` retirement reason.

---

### 8.4 Pillar 3: Entity Classification

Classification assigns governance attributes to entities that determine how they are managed, retained, and secured.

**Classification dimensions:**

| Dimension | Values | Governance impact |
|---|---|---|
| **Sensitivity** | PUBLIC, INTERNAL, CONFIDENTIAL, RESTRICTED | Determines access control rules |
| **Criticality** | LOW, MEDIUM, HIGH, CRITICAL | Determines backup frequency, monitoring intensity |
| **Volatility** | STATIC, SLOW_CHANGING, FAST_CHANGING, EPHEMERAL | Determines cache TTL and update frequency |
| **Retention class** | OPERATIONAL, ANALYTICAL, REGULATORY, PERMANENT | Determines archival schedule and storage tier |
| **Auditability** | MINIMAL, STANDARD, FULL | Determines audit event verbosity |

**Classification by entity type:**

| Entity type | Sensitivity | Criticality | Volatility | Retention | Auditability |
|---|---|---|---|---|---|
| Order | CONFIDENTIAL | CRITICAL | FAST_CHANGING | REGULATORY | FULL |
| Trade | CONFIDENTIAL | CRITICAL | SLOW_CHANGING | REGULATORY | FULL |
| Position | CONFIDENTIAL | CRITICAL | FAST_CHANGING | REGULATORY | FULL |
| Strategy | INTERNAL | HIGH | SLOW_CHANGING | ANALYTICAL | STANDARD |
| Hypothesis | INTERNAL | MEDIUM | FAST_CHANGING | OPERATIONAL | STANDARD |
| Regime | INTERNAL | HIGH | SLOW_CHANGING | ANALYTICAL | STANDARD |
| RiskThreshold | RESTRICTED | CRITICAL | STATIC | PERMANENT | FULL |
| KillSwitch | RESTRICTED | CRITICAL | SLOW_CHANGING | PERMANENT | FULL |
| Agent | INTERNAL | HIGH | STATIC | ANALYTICAL | STANDARD |
| KnowledgeRecord | INTERNAL | MEDIUM | SLOW_CHANGING | ANALYTICAL | STANDARD |
| Cycle | INTERNAL | LOW | FAST_CHANGING | OPERATIONAL | MINIMAL |
| Symbol | PUBLIC | LOW | STATIC | PERMANENT | MINIMAL |

---

### 8.5 Pillar 4: Entity Versioning Policy

The versioning policy defines when new versions are created, what changes require a version increment, and how many versions are retained.

**Version creation triggers:**

| Trigger | Version type | Description |
|---|---|---|
| Any attribute update | AUTOMATIC | Every field-level change creates a new version |
| Lifecycle transition | AUTOMATIC | State changes (ACTIVE → DEPRECATED) create a version |
| Ownership transfer | AUTOMATIC | Owner changes create a version |
| Milestone event | EXPLICIT | Named milestones (e.g., "Backtest Passed") create a labelled version |
| Schema migration | STRUCTURAL | Schema changes create a structural version |

**Version retention policy:**

| Entity category | Online versions retained | Archived versions | Permanent archive |
|---|---|---|---|
| Financial | Last 1,000 versions | Yes | Yes |
| Risk | All versions | Yes | Yes |
| Strategy | Last 100 versions | Yes | Yes (milestones) |
| Market / Reference | Last 50 versions | Yes | Latest only |
| System (Cycle, Job) | Last 10 versions | No | No |
| Derived | Last 20 versions | Yes | Milestones only |

**Version compression:** Versions older than 90 days are stored as diff records against the preceding version rather than full snapshots. Versions older than 1 year are stored in compressed format. The Entity History Manager handles transparent decompression.

---

### 8.6 Pillar 5: Deprecation Policy

Deprecation is the formal process for marking entities that are approaching end-of-life.

**Deprecation triggers:**

| Entity type | Deprecation trigger |
|---|---|
| Strategy | Win rate < 40% for 30 consecutive trading days; or Human Principal instruction |
| EvolvedVariant | Superseded by a newer evolved variant |
| DataFeed | Replaced by higher-quality source |
| Agent | Accuracy BELOW threshold for 60 days |
| KnowledgeRecord | Superseded by higher-confidence knowledge |
| RiskThreshold | New threshold approved and activated |

**Deprecation notice requirements:**

| Requirement | Description |
|---|---|
| Deprecation reason | Machine-readable reason code (SUPERSEDED, UNDERPERFORMING, MANUAL, etc.) |
| Deprecation notice | Human-readable explanation |
| Sunset date | When the entity will transition from DEPRECATED to ARCHIVED |
| Successor reference | entity_id of the replacement entity (where applicable) |
| Consumer notification | All known consumers of the entity receive a deprecation event via EventBus |

---

### 8.7 Pillar 6: Entity Migration

Migration is the process of updating entity records when the schema changes — adding fields, removing fields, changing field types.

**Migration principles:**

| Principle | Description |
|---|---|
| Zero downtime | Migrations do not require system shutdown for additive changes |
| Backward compatible by default | New fields must have defaults; old fields are never removed without a migration period |
| Explicit migration records | Every schema change is recorded in the migration log |
| No data destruction | Old field values are preserved in the version history even when fields are removed |
| Migration validation | Migrated entities are re-validated against the new schema before the migration is committed |

**Migration types:**

| Type | Description | Risk level |
|---|---|---|
| Additive | New field added with default value | LOW |
| Transformation | Existing field value transformed | MEDIUM |
| Removal | Old field removed (after deprecation period) | HIGH |
| Structural | Multiple fields reorganised | HIGH |
| Merge | Two entity types consolidated | CRITICAL |
| Split | One entity type split into two | CRITICAL |

---

### 8.8 Pillar 7: Entity Security

Security policy defines who can read, write, and modify entities of each sensitivity classification.

**Access control matrix:**

| Actor | PUBLIC entities | INTERNAL entities | CONFIDENTIAL entities | RESTRICTED entities |
|---|---|---|---|---|
| All IIOS services | Read | Read | Read (own category) | Read (authorised only) |
| Owner service | Read + Write | Read + Write | Read + Write | Read + Write |
| Human Principal | Full access | Full access | Full access | Full access |
| External (API) | Read only | Deny | Deny | Deny |
| Audit Service | Read only | Read only | Read only | Read only |
| Telegram bot | Read summary | Read summary | Summary only | Deny |

**Security controls:**

| Control | Description |
|---|---|
| Service identity | Every service has a registered identity that determines its access level |
| Operation logging | All write operations on CONFIDENTIAL and RESTRICTED entities are logged |
| Write-through audit | Changes to RESTRICTED entities always create an audit record before the change is committed |
| Rate limiting | Entity write operations are rate-limited per service to prevent runaway updates |
| Anomaly detection | Unusual write patterns (burst updates, off-hours writes) trigger security alerts |

---

### 8.9 Pillar 8: Entity Audit

Audit is the permanent, tamper-evident record of everything that has happened to every entity.

**Audit coverage requirements:**

| Entity sensitivity | Minimum audit coverage |
|---|---|
| PUBLIC | CREATED event only |
| INTERNAL | CREATED, major state transitions, ownership changes |
| CONFIDENTIAL | All state changes, all attribute updates, all ownership events |
| RESTRICTED | Every event, including reads by non-owner services |

**Audit log immutability:** Audit records are written to a write-once audit store. The audit store is:
- Append-only (no updates)
- No-delete (no removals)
- Hash-chained (each record includes a hash of the previous record, enabling tamper detection)
- Periodically exported to a backup store for disaster recovery

**Audit log retention:** Audit logs are retained for the lifetime of the corresponding entity plus a mandatory post-retirement retention period:
- Financial entities: Entity lifetime + 7 years
- Risk entities: Entity lifetime + 10 years
- All other entities: Entity lifetime + 2 years

---

### 8.10 Pillar 9: Compliance

Compliance monitoring ensures that entity governance rules are being followed systematically and that any deviations are identified and addressed.

**Compliance checks schedule:**

| Check | Frequency | Scope |
|---|---|---|
| Entity ownership validation | Every cycle | ACTIVE operational entities |
| Quality score review | Every cycle | All ACTIVE entities |
| Classification completeness | Daily | Full entity population |
| Retention compliance | Weekly | Archived entities past retention dates |
| Audit chain integrity | Weekly | All CONFIDENTIAL + RESTRICTED entities |
| Version retention cleanup | Monthly | Purge excess old versions per policy |
| Full integrity scan | Monthly | Complete entity population |

**Compliance violation handling:**

| Severity | Response |
|---|---|
| INFO | Logged; included in weekly governance report |
| WARNING | Logged; Telegram notification to Human Principal |
| ERROR | Logged; Telegram alert; Governance Manager flags entity |
| CRITICAL | Logged; immediate Telegram alert; entity suspended pending resolution |

---

### 8.11 Pillar 10: Schema Compatibility

Schema compatibility ensures that existing entities remain accessible and functional when schema changes are introduced.

**Compatibility levels:**

| Level | Description | Migration required |
|---|---|---|
| FULLY_COMPATIBLE | New schema reads and writes old entity format without change | No |
| READ_COMPATIBLE | Old entities can be read; writes require migration | No (for reads); Yes (for writes) |
| MIGRATION_REQUIRED | Old entities must be migrated before use | Yes |
| BREAKING | Old entities cannot be used until system is fully migrated | System downtime required |

**Compatibility enforcement:**

- Schema versions are tracked in the Entity Catalog
- The entity engine checks schema version compatibility before reading an entity
- If a schema incompatibility is detected, the entity is flagged and a migration is triggered
- Breaking schema changes require a formal migration plan approved by the Human Principal

---
## PART IX — ENTITY CONSTITUTION

### 9.1 Overview

The Entity Constitution is the supreme set of mandatory rules that govern every entity in the IIOS. These rules are non-negotiable. No exception, override, or workaround to a Constitutional rule is permitted without an explicit amendment recorded as a governance decision record.

Rules are organised into eight categories: Identity (EC-A), Lifecycle (EC-B), Integrity (EC-C), Versioning (EC-D), Audit (EC-E), Quality (EC-F), Governance (EC-G), and Service (EC-H).

---

### 9.2 Category A: Identity Rules

| Rule ID | Rule | Rationale |
|---|---|---|
| EC-A-01 | Every entity has exactly one permanent identity (UUID4) assigned at creation. | Identity is the foundation of all entity operations. |
| EC-A-02 | An entity's canonical identity (entity_id) is never changed after assignment, even after merge or split. | Changing identity breaks all references and audit chains. |
| EC-A-03 | A retired entity's entity_id is never reused for a new entity. | Reuse breaks historical audit continuity. |
| EC-A-04 | Every alias must be unique within its entity type. | Duplicate aliases cause identity ambiguity. |
| EC-A-05 | Every external ID must be registered through the Identity Manager before use. | Unregistered external IDs cannot be resolved. |
| EC-A-06 | Identity resolution (alias → entity_id) must complete in under 1 ms for hot-path identifiers. | Identity resolution is on the cycle-time critical path. |
| EC-A-07 | Every entity has exactly one canonical reference ID assigned at creation. | Reference IDs must be stable for operational communication. |
| EC-A-08 | Every new entity is checked for potential duplicates before creation. | Duplicate entities corrupt identity resolution and knowledge. |
| EC-A-09 | Merge operations preserve the primary entity's canonical identity. | The primary survives; the secondary is absorbed. |
| EC-A-10 | Split operations create two new entities with new canonical identities; the source entity transitions to SPLIT. | New identities prevent confusion with the original entity. |

---

### 9.3 Category B: Lifecycle Rules

| Rule ID | Rule | Rationale |
|---|---|---|
| EC-B-01 | Every entity follows a defined lifecycle state machine. | Entities without lifecycle governance are unmanageable. |
| EC-B-02 | Every entity has exactly one lifecycle state at any given time. | Ambiguous state causes inconsistent behaviour across consumers. |
| EC-B-03 | No entity may skip a mandatory lifecycle stage. | Skipping stages bypasses validation and audit. |
| EC-B-04 | No entity may regress to a previous lifecycle state except through an explicit Restore operation. | Uncontrolled regression corrupts entity history. |
| EC-B-05 | Every lifecycle state transition is validated against the Catalog before execution. | Invalid transitions corrupt aggregate consistency. |
| EC-B-06 | Every lifecycle transition is recorded as an audit event. | Transitions are significant governance events. |
| EC-B-07 | A RETIRED entity cannot transition to any other state. | Retirement is the final, irreversible lifecycle stage. |
| EC-B-08 | Restore from ARCHIVED requires Human Principal authorisation for financial entities. | Financial entities require accountability for operational restoration. |
| EC-B-09 | An entity in VALIDATION_FAILED state cannot be Activated without first passing a full re-validation. | Failed entities must be corrected before becoming operational. |
| EC-B-10 | Entity deprecation must include a reason code, a deprecation notice, and (where applicable) a successor reference. | Deprecation without explanation is ungoverned. |
| EC-B-11 | Entity archival is blocked if the entity has active dependencies (other entities referencing it as ACTIVE). | Archiving a referenced entity causes referential failures. |
| EC-B-12 | Every entity type must define its valid lifecycle states and transitions in the Entity Catalog before the type may be instantiated. | Unregistered entity types cannot be lifecycle-managed. |

---

### 9.4 Category C: Integrity Rules

| Rule ID | Rule | Rationale |
|---|---|---|
| EC-C-01 | Every entity must satisfy all required field invariants before transitioning to CREATED. | Required fields are required for a reason. |
| EC-C-02 | Every entity must satisfy all relational invariants at all times when ACTIVE. | Relational consistency is a fundamental correctness requirement. |
| EC-C-03 | Every aggregate invariant must hold across the full aggregate at all times. | Partial consistency is worse than no consistency. |
| EC-C-04 | An entity update that would violate a CRITICAL invariant is rejected without exception. | CRITICAL invariants protect against unsafe states. |
| EC-C-05 | An entity update that would violate a WARNING invariant is applied but generates a governance alert. | WARNING invariants are important but not safety-critical. |
| EC-C-06 | The Entity Integrity Checker runs a full population integrity scan at least once per day. | Runtime validation catches individual entity errors; scheduled scans catch cross-entity errors. |
| EC-C-07 | An entity with Integrity score 0.0 (any CRITICAL invariant violated) is automatically suspended pending investigation. | Integrity-zero entities cannot be trusted as inputs to decisions. |
| EC-C-08 | An entity cannot be ACTIVE if any of its required referenced entities are RETIRED or ARCHIVED. | An entity cannot be active if its dependencies are gone. |
| EC-C-09 | Temporal invariants (timestamps must be logically ordered) are enforced at creation and update time. | Out-of-order timestamps corrupt history and audit. |
| EC-C-10 | No entity field may be set to a value that would require a forbidden lifecycle transition to be consistent. | State and field consistency must be maintained together. |

---

### 9.5 Category D: Versioning Rules

| Rule ID | Rule | Rationale |
|---|---|---|
| EC-D-01 | Every entity is versioned from creation. | Version 1 is created by the Factory; subsequent updates create subsequent versions. |
| EC-D-02 | Every attribute update to an ACTIVE entity creates a new version. | All changes must be traceable through the version history. |
| EC-D-03 | Version numbers are monotonically increasing integers; they never decrease. | Decreasing version numbers would imply rollback, which must be explicit. |
| EC-D-04 | Version records are immutable after creation. | Historical states must not be alterable. |
| EC-D-05 | The Entity History Service must be able to reconstruct any past version from the version store. | Historical access is a fundamental audit capability. |
| EC-D-06 | Version rollback requires Human Principal authorisation and a version rollback justification record. | Rollback is a destructive operation that requires accountability. |
| EC-D-07 | Milestone versions may be created explicitly for significant domain events; they are labelled and retained permanently. | Milestones provide semantic anchors in the version history. |
| EC-D-08 | Version diffs are stored alongside full snapshots for storage efficiency. | Diff storage reduces storage footprint without sacrificing accessibility. |
| EC-D-09 | A version record includes the `changed_by` actor and a machine-readable `change_reason`. | Blind changes (no actor, no reason) are ungoverned. |
| EC-D-10 | No entity may have two versions with the same version number. | Version uniqueness is a fundamental assumption of the version system. |

---

### 9.6 Category E: Audit Rules

| Rule ID | Rule | Rationale |
|---|---|---|
| EC-E-01 | Every entity creation generates a ENTITY_CREATED audit event. | The birth of every entity must be permanently recorded. |
| EC-E-02 | Every entity state transition generates an ENTITY_TRANSITION audit event. | Lifecycle transitions are governance events. |
| EC-E-03 | Every ownership change generates an ENTITY_OWNERSHIP_CHANGE audit event. | Ownership changes affect accountability. |
| EC-E-04 | Audit records are never deleted, modified, or overwritten. | Tampered audit logs are worthless for compliance. |
| EC-E-05 | Audit records are hash-chained to enable tamper detection. | Chain breaks reveal attempts to alter the audit trail. |
| EC-E-06 | Every audit record includes: entity_id, entity_type, event_type, actor_id, timestamp, previous state, new state. | Incomplete audit records are not audit records. |
| EC-E-07 | The audit log is stored in a write-once, no-delete persistence store. | The persistence mechanism must enforce audit immutability. |
| EC-E-08 | All audit logs for REGULATORY retention-class entities are retained for at least 7 years after the entity's retirement. | Regulatory compliance mandate. |
| EC-E-09 | Audit records for CONFIDENTIAL entities are themselves classified INTERNAL and subject to access control. | Audit records may contain sensitive information. |
| EC-E-10 | An entity is never promoted to ACTIVE if the Entity Factory failed to create its initial audit record. | Entities without audit trails cannot be governed. |
| EC-E-11 | The Audit Service verifies audit chain integrity for CONFIDENTIAL and RESTRICTED entities weekly. | Chain integrity verification detects tampering proactively. |

---

### 9.7 Category F: Quality Rules

| Rule ID | Rule | Rationale |
|---|---|---|
| EC-F-01 | Every entity carries a computed quality score (EQS). | Quality without measurement is not quality — it is aspiration. |
| EC-F-02 | The EQS is recomputed on every entity update. | Stale quality scores are misleading. |
| EC-F-03 | An entity with EQS < 0.40 generates a CRITICAL governance alert. | Critical-quality entities are dangerous inputs to decisions. |
| EC-F-04 | An entity with EQS < 0.40 cannot be used as a primary input to a trading decision. | Low-quality entities must not influence live positions. |
| EC-F-05 | Freshness is computed per the entity-type-specific freshness standards defined in this document. | Generic freshness standards are meaningless for real-time entities. |
| EC-F-06 | Every entity with an Accuracy dimension must have its accuracy source defined in the Entity Catalog. | Accuracy without a defined truth source is not accuracy. |
| EC-F-07 | Completeness is computed only over the fields defined as completeness-relevant in the Entity Catalog. | Measuring optional fields penalises intentionally sparse entities. |
| EC-F-08 | Dimension weights in the EQS formula may be overridden per entity type; overrides are recorded in the Catalog. | Entity-type-specific importance requires entity-type-specific weights. |
| EC-F-09 | Quality scores are exposed to the ControlTower dashboard and the Telegram bot on request. | Quality is only actionable when it is visible. |
| EC-F-10 | A quality improvement plan is required for any entity that has maintained EQS < 0.60 for more than 7 consecutive days. | Persistent low quality requires explicit action, not just alerts. |

---

### 9.8 Category G: Governance Rules

| Rule ID | Rule | Rationale |
|---|---|---|
| EC-G-01 | Every entity has exactly one owner at all times after creation. | Ownerless entities have no accountability. |
| EC-G-02 | The owner of an entity must be an authorised owner for that entity type. | Unauthorised ownership prevents proper accountability. |
| EC-G-03 | Every entity carries a classification on all four classification dimensions (Sensitivity, Criticality, Volatility, Retention). | Unclassified entities cannot be governed. |
| EC-G-04 | Financial entities require Human Principal approval before activation. | Live-trading entities demand explicit human sign-off. |
| EC-G-05 | Risk threshold changes require Human Principal approval before becoming effective. | Risk parameters directly constrain live trading. |
| EC-G-06 | Entity governance policies are defined per entity type in the Governance Policy Catalog. | Generic policies are insufficient for domain-specific governance. |
| EC-G-07 | Governance violations are recorded as governance events and are never silently dismissed. | Silent dismissal undermines the governance framework. |
| EC-G-08 | CRITICAL governance violations trigger immediate Human Principal notification via Telegram. | Critical violations demand immediate human awareness. |
| EC-G-09 | The Governance Manager generates a weekly governance health report. | Regular reporting enables proactive governance management. |
| EC-G-10 | Every entity migration requires a migration plan and a migration approval record. | Schema changes without plans cause data corruption. |
| EC-G-11 | Entity merge and entity split operations are never performed automatically for financial entities. | Financial entity identity changes require human accountability. |
| EC-G-12 | Every entity deprecation requires a successor entity reference where a successor exists. | Deprecation without succession leaves consumers without guidance. |
| EC-G-13 | The Entity Governance Service generates compliance reports on the schedule defined in this document. | Scheduled compliance reporting is a governance commitment, not an optional feature. |
| EC-G-14 | Security access control for entities is applied at the service boundary; no entity should be readable by an unauthorised consumer via any bypass path. | Security cannot have back-doors. |

---

### 9.9 Category H: Service Rules

| Rule ID | Rule | Rationale |
|---|---|---|
| EC-H-01 | No entity may be created, updated, or deleted except through an authorised Entity Service. | Direct entity store access bypasses validation and audit. |
| EC-H-02 | All Entity Services are idempotent on reads. | Read operations must never change entity state. |
| EC-H-03 | The Registration Service is the only authorised path for entity creation. | All creation must go through the Factory + Validator + Registry sequence. |
| EC-H-04 | The Query Service must serve hot-path entity requests in under 2 ms. | Slow entity access is a system performance problem. |
| EC-H-05 | The Cache Service maintains at least a 95% cache hit rate for L1-L2 entities during market hours. | Low cache hit rates indicate incorrect cache warm-up or eviction policy. |
| EC-H-06 | The Audit Service never serves audit records from cache; it always reads from the persistence layer. | Cached audit records may lag behind reality — compliance requires current data. |
| EC-H-07 | Every Entity Service failure is logged with full context (entity_id, entity_type, operation, error, caller_id, timestamp). | Service failures without context cannot be diagnosed. |
| EC-H-08 | Entity Services do not expose raw persistence layer access to consumers. | Consumers interact with entities through services, never with stores directly. |
| EC-H-09 | All Entity Service responses include the entity's current `version` number. | Consumers must know which version they received to detect stale data. |
| EC-H-10 | Entity Services enforce rate limits per calling component. | Runaway entity updates can destabilise the persistence layer. |
| EC-H-11 | The Merge Service and Split Service log their full decision trace as a governance record. | Identity change operations must be fully documented. |
| EC-H-12 | Cache invalidation after an entity update must complete before the update response is returned to the caller. | Stale cache entries after a write lead to stale reads by subsequent callers. |

---

### 9.10 Total Rule Count

| Category | Rule count |
|---|---|
| EC-A: Identity | 10 |
| EC-B: Lifecycle | 12 |
| EC-C: Integrity | 10 |
| EC-D: Versioning | 10 |
| EC-E: Audit | 11 |
| EC-F: Quality | 10 |
| EC-G: Governance | 14 |
| EC-H: Service | 12 |
| **TOTAL** | **79 rules** |

---
## PART X — ENTITY READINESS CHECKLIST

### 10.1 Overview

The Entity Readiness Checklist is the master gate that an entity must pass before it is considered fully ready for operational use in the IIOS. It applies to all entity types, with entity-type-specific items noted where applicable.

The checklist is divided into nine sections corresponding to the nine readiness dimensions. Each section has a set of checks with a required status (PASS/FAIL) and an optional advisory status (WARN).

The Readiness Check is performed:
- Automatically by the Entity Factory at entity creation (initial readiness check)
- By the Validation Service on explicit request
- By the Governance Service during governance compliance checks
- By the Human Principal before manual entity activation (for approval-required entities)

---

### 10.2 Readiness Section 1: Entity Registered

This section verifies that the entity has been correctly enrolled in the Entity Registry.

| Check | Required | Description | Failure action |
|---|---|---|---|
| RDY-REG-01 | PASS | Entity has a non-null, unique UUID4 entity_id | Block activation — identity failure |
| RDY-REG-02 | PASS | entity_id is enrolled in the Entity Registry | Block activation — registry failure |
| RDY-REG-03 | PASS | entity_type is a valid registered entity type in the Entity Catalog | Block activation — type unknown |
| RDY-REG-04 | PASS | entity_category matches the registered category for this entity type | Block activation — category mismatch |
| RDY-REG-05 | PASS | Reference ID is assigned and registered in the reference ID index | Block activation — reference ID missing |
| RDY-REG-06 | PASS | display_name is non-null and non-empty | Block activation — nameless entity |
| RDY-REG-07 | WARN | entity has at least one tag assigned | Advisory — tagging improves searchability |
| RDY-REG-08 | WARN | All external IDs have been registered in the external ID index | Advisory — unregistered external IDs cannot be resolved |
| RDY-REG-09 | PASS | schema_version matches the current schema version for this entity type | Block activation — stale schema |
| RDY-REG-10 | PASS | created_at is set to a valid UTC timestamp within the last 24 hours | Block activation — creation timestamp anomaly |

---

### 10.3 Readiness Section 2: Entity Validated

This section verifies that the entity has passed all validation checks.

| Check | Required | Description | Failure action |
|---|---|---|---|
| RDY-VAL-01 | PASS | All required fields are populated | Block activation — structural failure |
| RDY-VAL-02 | PASS | All field values conform to their declared types | Block activation — type failure |
| RDY-VAL-03 | PASS | All field values are within their defined value domains | Block activation — domain failure |
| RDY-VAL-04 | PASS | All referenced entities exist and are in valid states | Block activation — referential failure |
| RDY-VAL-05 | PASS | All relational invariants are satisfied | Block activation — consistency failure |
| RDY-VAL-06 | PASS | All temporal invariants are satisfied | Block activation — temporal ordering failure |
| RDY-VAL-07 | PASS | Aggregate-level invariants are satisfied | Block activation — aggregate failure |
| RDY-VAL-08 | PASS | Business rule validation passes | Block activation — business rule failure |
| RDY-VAL-09 | WARN | No WARNING-level validation findings | Advisory — warnings may indicate data quality gaps |
| RDY-VAL-10 | PASS | Entity Integrity score >= 0.70 at time of activation | Block activation — integrity too low |

---

### 10.4 Readiness Section 3: Entity Classified

This section verifies that the entity carries complete classification on all four dimensions.

| Check | Required | Description | Failure action |
|---|---|---|---|
| RDY-CLS-01 | PASS | Sensitivity classification is assigned (PUBLIC/INTERNAL/CONFIDENTIAL/RESTRICTED) | Block activation — unclassified sensitivity |
| RDY-CLS-02 | PASS | Criticality classification is assigned (LOW/MEDIUM/HIGH/CRITICAL) | Block activation — unclassified criticality |
| RDY-CLS-03 | PASS | Volatility classification is assigned | Block activation — unclassified volatility |
| RDY-CLS-04 | PASS | Retention class is assigned | Block activation — unclassified retention |
| RDY-CLS-05 | PASS | Auditability level is assigned | Block activation — unclassified auditability |
| RDY-CLS-06 | PASS | Classification matches the defaults in the Entity Catalog for this entity type | Warn if overridden; block if missing |
| RDY-CLS-07 | WARN | Entity has at least two searchable tags for discovery | Advisory — untagged entities are hard to find |
| RDY-CLS-08 | PASS | Ownership is assigned and owner is an authorised owner type | Block activation — ownership failure |

---

### 10.5 Readiness Section 4: Entity Indexed

This section verifies that the entity is discoverable through the Entity Index.

| Check | Required | Description | Failure action |
|---|---|---|---|
| RDY-IDX-01 | PASS | Entity appears in the type index (entity_type → entity_id list) | Block activation — index enrollment failure |
| RDY-IDX-02 | PASS | Entity appears in the status index with status CREATED | Block — index status mismatch |
| RDY-IDX-03 | PASS | Entity appears in the owner index | Block — ownership not indexed |
| RDY-IDX-04 | PASS | Entity appears in the reference ID index | Block — reference ID not indexed |
| RDY-IDX-05 | WARN | Entity appears in at least one tag index | Advisory — tagging improves search performance |
| RDY-IDX-06 | PASS | Entity appears in the symbol index if it carries a symbol reference | Block — symbol-related entities must be symbol-indexed |
| RDY-IDX-07 | PASS | All external IDs are enrolled in the external ID index | Block — unindexed external IDs cannot be resolved |
| RDY-IDX-08 | PASS | Entity is accessible via the Search Service | Block — non-searchable entities violate EC-A-07 |

---

### 10.6 Readiness Section 5: Entity Versioned

This section verifies that the entity's version infrastructure is correctly initialised.

| Check | Required | Description | Failure action |
|---|---|---|---|
| RDY-VER-01 | PASS | Version 1 record exists in the version store | Block activation — version chain broken |
| RDY-VER-02 | PASS | Version 1 contains a complete state snapshot of the entity at creation | Block — incomplete version record |
| RDY-VER-03 | PASS | version_id for version 1 is a valid UUID4 | Block — invalid version identity |
| RDY-VER-04 | PASS | Version 1 record includes created_by (actor) and change_reason = CREATED | Block — unattributed version |
| RDY-VER-05 | PASS | current entity.version field = 1 at creation | Block — version counter out of sync |
| RDY-VER-06 | PASS | is_current = true on version 1 record at creation | Block — current version flag not set |
| RDY-VER-07 | WARN | Version record size is within storage limits (< 1 MB JSON) | Advisory — large version records should use diff compression |

---

### 10.7 Readiness Section 6: Entity Searchable

This section verifies that the entity can be discovered through all defined search pathways.

| Check | Required | Description | Failure action |
|---|---|---|---|
| RDY-SRH-01 | PASS | Entity is returned by get_by_id(entity_id) from the Query Service | Block — entity not retrievable by ID |
| RDY-SRH-02 | PASS | Entity is returned by get_by_type(entity_type) from the Query Service | Block — entity not in type list |
| RDY-SRH-03 | PASS | Entity is returned by a full-text search on its display_name | Block — entity not in search index |
| RDY-SRH-04 | WARN | Entity is returned by a search on at least one assigned tag | Advisory — if no tags, tag search is impossible |
| RDY-SRH-05 | PASS | Entity reference ID resolves correctly through the Identity Manager | Block — identity resolution failure |
| RDY-SRH-06 | PASS | All aliases resolve correctly to entity_id through the Identity Manager | Block — alias resolution failure |
| RDY-SRH-07 | PASS | Entity appears in the Cache for ACTIVE high-access types | Block for L1 entities; WARN for L2 entities |
| RDY-SRH-08 | WARN | Entity has a non-empty metadata.description field | Advisory — undescribed entities are hard to identify |

---

### 10.8 Readiness Section 7: Entity Governed

This section verifies that the entity satisfies all governance requirements.

| Check | Required | Description | Failure action |
|---|---|---|---|
| RDY-GOV-01 | PASS | Entity has a single, named, active owner | Block activation — ownerless entity |
| RDY-GOV-02 | PASS | Owner is an authorised owner for this entity type (per Governance Policy Catalog) | Block — unauthorised owner |
| RDY-GOV-03 | PASS | For approval-required entity types: approval record exists and is APPROVED | Block — missing or pending approval |
| RDY-GOV-04 | PASS | Quality score (EQS) >= 0.60 at activation | Block — low-quality activation |
| RDY-GOV-05 | PASS | All four classification dimensions are populated | Block — unclassified entity |
| RDY-GOV-06 | WARN | Entity has a populated deprecation_plan field if it is in DEPRECATED state | Advisory — deprecated entities should have plans |
| RDY-GOV-07 | PASS | Governance Manager has no active CRITICAL flags on this entity | Block — CRITICAL governance flag blocks activation |
| RDY-GOV-08 | WARN | Entity lineage record is populated | Advisory — untraced entities fail traceability dimension |
| RDY-GOV-09 | PASS | Entity type is registered in the Entity Catalog | Block — unregistered type cannot be governed |
| RDY-GOV-10 | PASS | No active identity conflicts involving this entity | Block — unresolved conflicts create duplicate risks |

---

### 10.9 Readiness Section 8: Entity Audited

This section verifies that the entity's audit infrastructure is correctly initialised.

| Check | Required | Description | Failure action |
|---|---|---|---|
| RDY-AUD-01 | PASS | ENTITY_CREATED audit event exists in the audit log for this entity | Block activation — birth event missing |
| RDY-AUD-02 | PASS | ENTITY_CREATED audit event contains valid entity_id, actor_id, and timestamp | Block — incomplete audit event |
| RDY-AUD-03 | PASS | Audit log for this entity passes hash chain integrity verification | Block — audit chain corrupt |
| RDY-AUD-04 | PASS | Audit log is stored in the write-once audit store | Block — audit in wrong store |
| RDY-AUD-05 | PASS | Auditability level matches the entity's classification (from Entity Catalog) | Block — misconfigured audit level |
| RDY-AUD-06 | WARN | Audit event includes a meaningful change_reason (not empty string) | Advisory — reason-less audit events are ungoverned |
| RDY-AUD-07 | PASS | For RESTRICTED sensitivity entities: creation event is timestamped and signed by the Audit Manager | Block — unsigned audit for restricted entity |

---

### 10.10 Readiness Section 9: Entity Recoverable

This section verifies that the entity can be fully recovered in the event of a system failure, data corruption, or emergency restore scenario.

| Check | Required | Description | Failure action |
|---|---|---|---|
| RDY-REC-01 | PASS | Entity record exists in the primary persistence store (trading_brain.db or equivalent) | Block activation — no primary record |
| RDY-REC-02 | PASS | Version 1 record can be retrieved from the version store | Block — version 1 missing; recovery from initial state impossible |
| RDY-REC-03 | PASS | Entity audit log can be retrieved from the audit store | Block — no audit record; compliance breach |
| RDY-REC-04 | WARN | Entity state can be fully reconstructed from the event stream alone (event sourcing compliance) | Advisory — event-stream reconstruction is a best-practice target |
| RDY-REC-05 | PASS | Entity backup exists in the most recent daily backup | Block for CRITICAL entities; WARN for others |
| RDY-REC-06 | PASS | Entity can be retrieved via the History Service at its creation timestamp | Block — history retrieval failure |
| RDY-REC-07 | WARN | Entity lineage record allows full provenance reconstruction | Advisory — lineage gaps limit post-incident investigation |
| RDY-REC-08 | PASS | For REGULATORY retention class: entity is enrolled in the regulatory backup scheme | Block — regulatory entities must be in regulated backup |

---

### 10.11 Readiness Summary Matrix

| Section | # Required checks | # Advisory checks | Block threshold |
|---|---|---|---|
| 1 — Registered | 9 | 2 | Any PASS failure |
| 2 — Validated | 9 | 1 | Any PASS failure |
| 3 — Classified | 7 | 1 | Any PASS failure |
| 4 — Indexed | 7 | 1 | Any PASS failure |
| 5 — Versioned | 6 | 1 | Any PASS failure |
| 6 — Searchable | 6 | 2 | Any PASS failure |
| 7 — Governed | 8 | 2 | Any PASS failure or CRITICAL flag |
| 8 — Audited | 6 | 1 | Any PASS failure |
| 9 — Recoverable | 5 | 3 | Any PASS failure (CRITICAL entities) |
| **Total** | **63 required** | **14 advisory** | |

**Entity Readiness outcome:**

| Outcome | Condition | Effect |
|---|---|---|
| READY | All 63 required checks pass | Entity may be Activated |
| READY_WITH_WARNINGS | All 63 required checks pass; 1+ advisory warnings | Entity may be Activated; warnings logged |
| NOT_READY | Any required check fails | Entity remains in CREATED; failure details returned |
| BLOCKED | CRITICAL governance flag active | Entity may not be Activated until flag resolved |

---
---

## DOCUMENT FOOTER

### Document Summary Metrics

| Metric | Value |
|---|---|
| Document title | ENTITY ENGINE ARCHITECTURE |
| Document number | 8 of 10 |
| Total parts | 10 |
| Entity categories defined | 13 |
| Entity components designed | 15 |
| Entity lifecycle stages | 12 |
| Entity services specified | 11 |
| Identity framework elements | 9 |
| Quality dimensions defined | 9 |
| Governance pillars | 10 |
| Constitution rules total | 79 |
| Readiness checklist items | 77 (63 required + 14 advisory) |
| Parent documents | 10 |
| Supplements | 7 (A through G) |

---

### Master Compliance Checklist

| Requirement | Status |
|---|---|
| Entity philosophy defined (Object vs Entity vs Information vs Knowledge vs Relationship vs Event vs Identity vs Instance vs Value Object vs Aggregate) | COMPLETE |
| 13-level entity hierarchy designed | COMPLETE |
| 15 entity components specified | COMPLETE |
| 12-stage entity lifecycle with state machine diagram | COMPLETE |
| 11 entity services with 6-attribute specification each | COMPLETE |
| Entity identity framework (Global IDs, Aliases, External IDs, Version IDs, Reference IDs, Canonical Identity, Resolution, Duplicate Detection, Conflict Resolution) | COMPLETE |
| 9 quality dimensions with formulas and thresholds | COMPLETE |
| 10 governance pillars with policies and compliance | COMPLETE |
| 79 mandatory Entity Constitution rules | COMPLETE |
| Entity Readiness Checklist (9 sections, 77 checks) | COMPLETE |
| No source code or implementation | CONFIRMED |
| No database schema | CONFIRMED |
| Lifecycle diagrams included | CONFIRMED |
| Responsibility matrices included | CONFIRMED |
| Governance tables included | CONFIRMED |

---

### Version History

| Version | Date | Change | Author |
|---|---|---|---|
| 1.0.0 | 2026-07-02 | Initial authoritative version | Human Principal / Engineering Foundation |

---

### Governing Documents

| Document | Role |
|---|---|
| `INVESTMENT_INTELLIGENCE_OPERATING_SYSTEM.md` | Supreme system authority |
| `ENTITY_ONTOLOGY.md` | Entity type definitions |
| `MASTER_KNOWLEDGE_ARCHITECTURE.md` | Knowledge domain authority |
| `INFORMATION_ONTOLOGY.md` | Information layer design |
| `AI_TRADING_BRAIN_ENGINEERING_BLUEPRINT.md` | Engineering design bridge |
| `ENGINEERING_STANDARDS.md` | Mandatory standards |
| `REPOSITORY_ARCHITECTURE.md` | Repository pattern authority |
| `CORE_FRAMEWORK_ARCHITECTURE.md` | Core framework authority |
| `DATABASE_PERSISTENCE_ARCHITECTURE.md` | Persistence design authority |
| `KNOWLEDGE_ENGINE_ARCHITECTURE.md` | Knowledge Engine authority |

---

### Closing Statement

The Entity Engine Architecture is the complete engineering design for the identity, lifecycle, quality, and governance of every entity in the Investment Intelligence Operating System.

Every entity in the IIOS — from the simplest reference record to the most complex AI agent — is governed by this document. The Entity Engine is the identity infrastructure that makes the IIOS a coherent, auditable, and intelligent system over time.

No entity exists outside this architecture. No entity escapes its lifecycle. No entity is ungoverned. No entity is forgotten.

**End of Document**

---
---

## SUPPLEMENT A — ENTITY TYPE CATALOGUE

### A.1 Financial Entities

| Entity Type | Category | Parent Aggregate | Lifecycle States | Retention Class | Audit Level |
|---|---|---|---|---|---|
| `Order` | Financial | Portfolio | REGISTERED→CREATED→ACTIVE→ARCHIVED | REGULATORY | FULL |
| `Trade` | Financial | Portfolio | REGISTERED→CREATED→ACTIVE→ARCHIVED | REGULATORY | FULL |
| `Position` | Financial | Portfolio | REGISTERED→CREATED→ACTIVE→ARCHIVED | REGULATORY | FULL |
| `Fill` | Financial | Order | REGISTERED→CREATED→ACTIVE (immutable) | REGULATORY | FULL |

### A.2 Market Entities

| Entity Type | Category | Parent Aggregate | Lifecycle States | Retention Class | Audit Level |
|---|---|---|---|---|---|
| `Symbol` | Market | — (root) | REGISTERED→CREATED→ACTIVE→ARCHIVED | PERMANENT | MINIMAL |
| `Index` | Market | — (root) | REGISTERED→CREATED→ACTIVE→ARCHIVED | PERMANENT | MINIMAL |
| `Sector` | Market | — (root) | REGISTERED→CREATED→ACTIVE | PERMANENT | MINIMAL |
| `MarketSession` | Market | Calendar | REGISTERED→CREATED→ACTIVE→ARCHIVED | ANALYTICAL | MINIMAL |

### A.3 Economic Entities

| Entity Type | Category | Parent Aggregate | Lifecycle States | Retention Class | Audit Level |
|---|---|---|---|---|---|
| `Regime` | Economic | — (root) | REGISTERED→CREATED→ACTIVE→ARCHIVED | ANALYTICAL | STANDARD |
| `MacroIndicator` | Economic | — (root) | REGISTERED→CREATED→ACTIVE | ANALYTICAL | STANDARD |
| `EconomicEvent` | Economic | — (root) | REGISTERED→CREATED→ACTIVE→ARCHIVED | ANALYTICAL | STANDARD |

### A.4 Corporate Entities

| Entity Type | Category | Parent Aggregate | Lifecycle States | Retention Class | Audit Level |
|---|---|---|---|---|---|
| `Company` | Corporate | — (root) | REGISTERED→CREATED→ACTIVE | PERMANENT | MINIMAL |
| `FIIParticipant` | Corporate | — (root) | REGISTERED→CREATED→ACTIVE | ANALYTICAL | MINIMAL |
| `ListedSecurity` | Corporate | Company | REGISTERED→CREATED→ACTIVE→ARCHIVED | PERMANENT | MINIMAL |

### A.5 Portfolio Entities

| Entity Type | Category | Parent Aggregate | Lifecycle States | Retention Class | Audit Level |
|---|---|---|---|---|---|
| `Portfolio` | Portfolio | — (root, single) | REGISTERED→CREATED→ACTIVE | PERMANENT | FULL |
| `Allocation` | Portfolio | Portfolio | REGISTERED→CREATED→ACTIVE→ARCHIVED | REGULATORY | STANDARD |
| `BudgetEnvelope` | Portfolio | Portfolio | REGISTERED→CREATED→ACTIVE→ARCHIVED | ANALYTICAL | STANDARD |

### A.6 Execution Entities

| Entity Type | Category | Parent Aggregate | Lifecycle States | Retention Class | Audit Level |
|---|---|---|---|---|---|
| `ExecutionRecord` | Execution | Order | REGISTERED→CREATED→ACTIVE (immutable) | REGULATORY | FULL |
| `SlippageRecord` | Execution | Trade | REGISTERED→CREATED→ACTIVE (immutable) | ANALYTICAL | STANDARD |
| `BrokerSession` | Execution | — (root) | REGISTERED→CREATED→ACTIVE→ARCHIVED | OPERATIONAL | STANDARD |

### A.7 Risk Entities

| Entity Type | Category | Parent Aggregate | Lifecycle States | Retention Class | Audit Level |
|---|---|---|---|---|---|
| `RiskThreshold` | Risk | — (root) | REGISTERED→CREATED→ACTIVE | PERMANENT | FULL |
| `KillSwitch` | Risk | — (root, singleton) | REGISTERED→CREATED→ACTIVE | PERMANENT | FULL |
| `DrawdownRecord` | Risk | Portfolio | REGISTERED→CREATED→ACTIVE (immutable) | REGULATORY | FULL |
| `StressScenario` | Risk | — (root) | REGISTERED→CREATED→ACTIVE→ARCHIVED | ANALYTICAL | STANDARD |

### A.8 AI Entities

| Entity Type | Category | Parent Aggregate | Lifecycle States | Retention Class | Audit Level |
|---|---|---|---|---|---|
| `Agent` | AI | — (root) | REGISTERED→CREATED→ACTIVE | ANALYTICAL | STANDARD |
| `AgentOpinion` | AI | Hypothesis | REGISTERED→CREATED→ACTIVE (immutable) | ANALYTICAL | STANDARD |
| `Hypothesis` | AI | Cycle | REGISTERED→CREATED→ACTIVE→ARCHIVED | OPERATIONAL | STANDARD |
| `DecisionRecord` | AI | Cycle | REGISTERED→CREATED→ACTIVE (immutable) | REGULATORY | FULL |

### A.9 Strategy Entities

| Entity Type | Category | Parent Aggregate | Lifecycle States | Retention Class | Audit Level |
|---|---|---|---|---|---|
| `Strategy` | Strategy | — (root) | REGISTERED→CREATED→ACTIVE→DEPRECATED→ARCHIVED | ANALYTICAL | STANDARD |
| `EvolvedVariant` | Strategy | Strategy | REGISTERED→CREATED→ACTIVE→DEPRECATED→ARCHIVED | ANALYTICAL | STANDARD |
| `BacktestResult` | Derived | Strategy | REGISTERED→CREATED→ACTIVE (immutable) | ANALYTICAL | STANDARD |
| `WalkForwardResult` | Derived | Strategy | REGISTERED→CREATED→ACTIVE (immutable) | ANALYTICAL | STANDARD |

### A.10 System Entities

| Entity Type | Category | Parent Aggregate | Lifecycle States | Retention Class | Audit Level |
|---|---|---|---|---|---|
| `Cycle` | System | — (root) | REGISTERED→CREATED→ACTIVE→ARCHIVED | OPERATIONAL | MINIMAL |
| `ScheduledJob` | System | — (root) | REGISTERED→CREATED→ACTIVE→ARCHIVED | OPERATIONAL | MINIMAL |
| `DataFeed` | System | — (root) | REGISTERED→CREATED→ACTIVE→ARCHIVED | OPERATIONAL | STANDARD |
| `SystemConfiguration` | System | — (root, singleton) | REGISTERED→CREATED→ACTIVE | PERMANENT | FULL |

### A.11 Reference Entities

| Entity Type | Category | Parent Aggregate | Lifecycle States | Retention Class | Audit Level |
|---|---|---|---|---|---|
| `Calendar` | Reference | — (root) | REGISTERED→CREATED→ACTIVE | PERMANENT | MINIMAL |
| `ExpirySchedule` | Reference | Calendar | REGISTERED→CREATED→ACTIVE | PERMANENT | MINIMAL |
| `TradingHoliday` | Reference | Calendar | REGISTERED→CREATED→ACTIVE→ARCHIVED | PERMANENT | MINIMAL |
| `SymbolMaster` | Reference | — (root) | REGISTERED→CREATED→ACTIVE | PERMANENT | MINIMAL |

### A.12 Knowledge Entities

| Entity Type | Category | Parent Aggregate | Lifecycle States | Retention Class | Audit Level |
|---|---|---|---|---|---|
| `KnowledgeRecord` | Knowledge | — (root) | REGISTERED→CREATED→ACTIVE→DEPRECATED→ARCHIVED | ANALYTICAL | STANDARD |
| `KnowledgePattern` | Knowledge | KnowledgeRecord | REGISTERED→CREATED→ACTIVE→ARCHIVED | ANALYTICAL | STANDARD |
| `KnowledgeRule` | Knowledge | KnowledgeRecord | REGISTERED→CREATED→ACTIVE→DEPRECATED | ANALYTICAL | STANDARD |
| `KnowledgeFact` | Knowledge | KnowledgeRecord | REGISTERED→CREATED→ACTIVE→ARCHIVED | ANALYTICAL | STANDARD |
| `LearningRecord` | Derived | Trade | REGISTERED→CREATED→ACTIVE→ARCHIVED | ANALYTICAL | STANDARD |

---

## SUPPLEMENT B — ENTITY COMPONENT INTERFACE REFERENCE

### B.1 Entity Registry Interface

| Operation | Inputs | Outputs | Latency target |
|---|---|---|---|
| `enroll(entity)` | Full entity record | RegistryEntry | < 10 ms |
| `exists(entity_id)` | UUID4 | bool | < 0.5 ms |
| `get_entry(entity_id)` | UUID4 | RegistryEntry or None | < 1 ms |
| `update_status(entity_id, status)` | UUID4, EntityStatus | RegistryEntry | < 5 ms |
| `get_count_by_type(entity_type)` | EntityType | int | < 5 ms |
| `get_count_by_status(entity_type, status)` | EntityType, EntityStatus | int | < 5 ms |
| `list_by_type(entity_type)` | EntityType | List[UUID4] | < 20 ms |
| `mark_deleted(entity_id)` | UUID4 | bool | < 10 ms |

### B.2 Entity Catalog Interface

| Operation | Inputs | Outputs | Description |
|---|---|---|---|
| `get_type_definition(entity_type)` | EntityType | EntityTypeDefinition | Returns full type definition |
| `get_lifecycle_states(entity_type)` | EntityType | List[EntityStatus] | Valid states for type |
| `get_valid_transitions(entity_type, from_state)` | EntityType, EntityStatus | List[EntityStatus] | Valid next states |
| `get_invariants(entity_type)` | EntityType | List[InvariantRule] | All invariants for type |
| `get_completeness_fields(entity_type)` | EntityType | List[FieldDefinition] | Fields counted in completeness |
| `get_quality_weights(entity_type)` | EntityType | QualityWeights | EQS dimension weights |
| `get_classification_defaults(entity_type)` | EntityType | ClassificationDefaults | Default classifications |
| `register_type(type_definition)` | EntityTypeDefinition | bool | Register new entity type |

### B.3 Entity Factory Interface

| Operation | Inputs | Outputs | Description |
|---|---|---|---|
| `create(entity_type, params, owner_id, idempotency_key)` | EntityType, dict, str, str | EntityRecord | Full creation sequence |
| `create_bulk(entity_type, params_list, owner_id)` | EntityType, List[dict], str | List[EntityRecord] | Batch creation |
| `generate_entity_id()` | — | UUID4 | Generate a new UUID4 |
| `generate_reference_id(entity_type, date)` | EntityType, date | str | Generate reference ID |
| `apply_defaults(entity_type, params)` | EntityType, dict | dict | Apply catalog defaults |
| `check_idempotency(idempotency_key)` | str | Optional[EntityRecord] | Check for duplicate |

### B.4 Entity Validator Interface

| Operation | Inputs | Outputs | Description |
|---|---|---|---|
| `validate_structural(entity_type, data)` | EntityType, dict | ValidationResult | Type and format checks |
| `validate_referential(entity_type, data)` | EntityType, dict | ValidationResult | Cross-entity reference checks |
| `validate_business(entity_type, data)` | EntityType, dict | ValidationResult | Domain rule checks |
| `validate_aggregate(aggregate_root, child_type, child_data)` | EntityRecord, EntityType, dict | ValidationResult | Aggregate-level checks |
| `validate_transition(entity_id, target_state)` | UUID4, EntityStatus | ValidationResult | State transition check |
| `validate_all(entity_type, data)` | EntityType, dict | ValidationResult | All validation layers |

### B.5 Entity Identity Manager Interface

| Operation | Inputs | Outputs | Description |
|---|---|---|---|
| `resolve(identifier)` | str | UUID4 | Any identifier → entity_id |
| `register_alias(entity_id, alias)` | UUID4, str | bool | Register alias |
| `register_external_id(entity_id, system, external_id)` | UUID4, str, str | bool | Register external ID |
| `detect_duplicates(entity_type, data)` | EntityType, dict | List[DuplicateCandidate] | Find potential duplicates |
| `get_all_identifiers(entity_id)` | UUID4 | IdentityRecord | All IDs for entity |
| `resolve_conflict(conflict_id, resolution)` | UUID4, ConflictResolution | bool | Resolve identity conflict |

### B.6 Entity Lifecycle Manager Interface

| Operation | Inputs | Outputs | Description |
|---|---|---|---|
| `transition(entity_id, target_state, reason)` | UUID4, EntityStatus, str | EntityRecord | Execute state transition |
| `activate(entity_id)` | UUID4 | EntityRecord | Shortcut to ACTIVE transition |
| `deprecate(entity_id, reason, successor_id)` | UUID4, str, Optional[UUID4] | EntityRecord | Deprecate entity |
| `archive(entity_id, reason)` | UUID4, str | EntityRecord | Archive entity |
| `retire(entity_id, reason, auth_token)` | UUID4, str, str | EntityRecord | Permanently retire |
| `restore(entity_id, reason, auth_token)` | UUID4, str, str | EntityRecord | Restore from archived |
| `get_lifecycle_history(entity_id)` | UUID4 | List[LifecycleEvent] | Full transition history |

### B.7 Entity Version Manager Interface

| Operation | Inputs | Outputs | Description |
|---|---|---|---|
| `create_version(entity_id, state_snapshot, changed_by, reason)` | UUID4, dict, str, str | VersionRecord | Create version record |
| `get_version(entity_id, version_number)` | UUID4, int | VersionRecord | Get specific version |
| `get_current_version(entity_id)` | UUID4 | VersionRecord | Get latest version |
| `list_versions(entity_id)` | UUID4 | List[VersionSummary] | All version summaries |
| `diff(entity_id, v1, v2)` | UUID4, int, int | VersionDiff | Field-level diff |
| `rollback(entity_id, target_version, auth_token)` | UUID4, int, str | EntityRecord | Authorised rollback |
| `create_milestone(entity_id, label, reason)` | UUID4, str, str | VersionRecord | Named milestone version |

---
---

## SUPPLEMENT C — ENTITY LIFECYCLE STATE MACHINE

### C.1 Financial Entity Lifecycle (Order)

```
              ┌─────────────────────────┐
              │    REGISTERED           │
              └────────────┬────────────┘
                           │ Validation passes
              ┌────────────▼────────────┐
              │    CREATED              │
              └────────────┬────────────┘
                           │ Submitted to broker
              ┌────────────▼────────────┐
              │    ACTIVE (PENDING)     │
              └───┬────────┬────────────┘
                  │        │
      ┌───────────▼─┐    ┌─▼─────────────────┐
      │ PARTIALLY   │    │ REJECTED / CANCELLED│
      │ FILLED      │    └─────────────────────┘
      └───────┬─────┘               │
              │ Fully filled         │
    ┌─────────▼──────────┐          │
    │     FILLED          │          │
    └─────────┬───────────┘          │
              └──────────────────────┘
                           │ Archive trigger
              ┌────────────▼────────────┐
              │     ARCHIVED            │
              └─────────────────────────┘
```

### C.2 AI Entity Lifecycle (Hypothesis)

```
         ┌─────────────────────────┐
         │      REGISTERED         │
         └──────────────┬──────────┘
                        │ Created by StrategyLab
         ┌──────────────▼──────────┐
         │      CANDIDATE          │ (hypothesis proposed)
         └──────────────┬──────────┘
                        │ Submitted to debate ensemble
         ┌──────────────▼──────────┐
         │     UNDER_EVALUATION    │ (agents debating)
         └───────┬─────────────────┘
                 │
    ┌────────────┴────────────────┐
    ▼                             ▼
APPROVED                      REJECTED
(score >= 6.5)               (score < 6.5)
    │                             │
    ▼                             ▼
Submitted as             Archived with
Order → Trade            rejection reason
    │
    ▼
ARCHIVED (end of cycle)
```

### C.3 Economic Entity Lifecycle (Regime)

```
    ┌─────────────────────────┐
    │  DETECTED               │  (MarketIntelligence signals regime shift)
    └──────────┬──────────────┘
               │ < 3 days: PROVISIONAL
    ┌──────────▼──────────────┐
    │  PROVISIONAL            │  (too recent to confirm)
    └──────────┬──────────────┘
               │ >= 3 consecutive days confirmed
    ┌──────────▼──────────────┐
    │  CONFIRMED / ACTIVE     │  ← all strategies calibrated to this regime
    └──────────┬──────────────┘
               │ New regime detected
    ┌──────────▼──────────────┐
    │  TRANSITION_INITIATED   │
    └──────────┬──────────────┘
               │ New regime confirmed
    ┌──────────▼──────────────┐
    │  ENDED                  │  → archived with duration record
    └─────────────────────────┘
```

### C.4 Risk Entity Lifecycle (KillSwitch)

```
    ┌─────────────────────────┐
    │  ACTIVE (INACTIVE)      │  (kill switch present but not triggered)
    └──────────┬──────────────┘
               │ VIX > 45 / daily loss > 2% / manual
    ┌──────────▼──────────────┐
    │  ACTIVE (TRIGGERED)     │  ← ALL trading halted
    └──────────┬──────────────┘
               │ Human Principal deactivation (with auth)
    ┌──────────▼──────────────┐
    │  ACTIVE (INACTIVE)      │  ← trading resumes next cycle
    └─────────────────────────┘
    (KillSwitch never leaves ACTIVE state; it toggles its trigger flag)
```

### C.5 Strategy Entity Lifecycle

```
         ┌─────────────────────────┐
         │   REGISTERED            │
         └──────────────┬──────────┘
                        │ Research Lab proposes
         ┌──────────────▼──────────┐
         │   CANDIDATE             │ (awaiting validation gates)
         └──────────────┬──────────┘
                        │ All gates pass (WinRate>=50%, Sharpe>0.8, MaxDD<15%)
         ┌──────────────▼──────────┐
         │   PENDING_APPROVAL      │ (awaiting Human Principal approval)
         └──────────────┬──────────┘
                        │ Approved
         ┌──────────────▼──────────┐
         │     ACTIVE              │ ← participating in cycles
         └───────┬─────────────────┘
                 │ Performance decay / Manual instruction
    ┌────────────▼───────────────────────┐
    │       DEPRECATED                   │ (still active; successor flagged)
    └────────────┬───────────────────────┘
                 │ Sunset date reached
    ┌────────────▼───────────────────────┐
    │       ARCHIVED                     │ (no longer active)
    └────────────────────────────────────┘
```

---

## SUPPLEMENT D — ENTITY QUALITY SCORING REFERENCE

### D.1 Completeness Reference by Entity Type

| Entity Type | Required fields (weight 1.0) | Expected fields (weight 0.5) | Completeness weight in EQS |
|---|---|---|---|
| Order | entity_id, symbol, side, quantity, order_type, created_at | broker_order_id, execution_notes, strategy_id | 0.10 |
| Trade | entity_id, entry_order_id, exit_order_id, symbol, pnl | entry_time, exit_time, regime_at_entry | 0.12 |
| Position | entity_id, symbol, quantity, avg_price | unrealised_pnl, days_held, strategy_id | 0.12 |
| Regime | entity_id, regime_type, detected_at, confidence | vix_at_detection, confirming_signals | 0.08 |
| Strategy | entity_id, name, strategy_type, parameters | win_rate, sharpe_ratio, max_drawdown | 0.10 |
| Agent | entity_id, agent_name, agent_type, calibration_score | last_accuracy_update, total_predictions | 0.08 |
| KnowledgeRecord | entity_id, knowledge_type, content, confidence | source_entities, evidence_count | 0.10 |
| RiskThreshold | entity_id, threshold_type, threshold_value, effective_from | approved_by, review_date | 0.10 |
| Hypothesis | entity_id, strategy_id, symbol, direction, confidence | debate_score, agent_opinions_count | 0.10 |
| Cycle | entity_id, cycle_start, cycle_end, layer_results | hypothesis_count, orders_submitted | 0.05 |

### D.2 Freshness Standards by Entity Type

| Entity Type | FRESH threshold | STALE threshold | CRITICAL STALE | Freshness weight in EQS |
|---|---|---|---|---|
| Position | 30 seconds | 5 minutes | 15 minutes | 0.20 |
| KillSwitch | 30 seconds | 2 minutes | 5 minutes | 0.25 |
| RiskThreshold | session start | 1 day | 7 days | 0.15 |
| Regime | 30 seconds | 30 minutes | 2 hours | 0.20 |
| MacroIndicator | 1 hour | 4 hours | 24 hours | 0.12 |
| Symbol (price) | 1 minute | 5 minutes | 30 minutes | 0.15 |
| Portfolio | 30 seconds | 5 minutes | 30 minutes | 0.20 |
| Strategy | session start | 30 days | 90 days | 0.08 |
| Agent (calibration) | session start | 7 days | 30 days | 0.08 |
| KnowledgeRecord | creation | 30 days | 90 days | 0.06 |

### D.3 EQS Weight Overrides by Entity Type

| Entity Type | Integrity weight | Freshness weight | Accuracy weight | Traceability weight |
|---|---|---|---|---|
| Order | 0.25 | 0.05 | 0.15 | 0.15 |
| Trade | 0.25 | 0.05 | 0.15 | 0.15 |
| Position | 0.25 | 0.20 | 0.10 | 0.10 |
| RiskThreshold | 0.30 | 0.15 | 0.10 | 0.10 |
| KillSwitch | 0.35 | 0.25 | 0.10 | 0.05 |
| Regime | 0.20 | 0.20 | 0.20 | 0.05 |
| Strategy | 0.20 | 0.05 | 0.15 | 0.10 |
| Hypothesis | 0.20 | 0.10 | 0.10 | 0.10 |
| KnowledgeRecord | 0.15 | 0.08 | 0.15 | 0.10 |
| Cycle | 0.15 | 0.05 | 0.05 | 0.10 |

### D.4 Quality Score Alert Thresholds

| Score | Alert type | Telegram notification | System action |
|---|---|---|---|
| 0.90–1.00 | None | None | None |
| 0.75–0.89 | MONITOR | None | Quality dashboard flag |
| 0.60–0.74 | WARNING | Weekly summary | Governance queue entry |
| 0.40–0.59 | POOR | Daily alert | Governance flag; restricted use |
| 0.00–0.39 | CRITICAL | Immediate alert | Entity suspended; Human Principal review required |

### D.5 Quality Dimension Scoring Formulas Summary

| Dimension | Formula | Range |
|---|---|---|
| Completeness | (populated fields) / (expected fields) | [0.0, 1.0] |
| Integrity | 1 - (violated invariants / total invariants) | [0.0, 1.0]; = 0.0 if any CRITICAL violated |
| Consistency | (cross-checks passed) / (total cross-checks) | [0.0, 1.0] |
| Validity | (valid fields) / (total validated fields) | [0.0, 1.0] |
| Accuracy | comparison to truth source; UNKNOWN = 0.5 | [0.0, 1.0] |
| Freshness | max(0, 1 - time_since_update / max_staleness) | [0.0, 1.0] |
| Confidence | entity-type-specific computation | [0.0, 1.0] |
| Traceability | (available traceability elements) / (required elements) | [0.0, 1.0] |
| Ownership | criteria-based (see Part VII) | {0.0, 0.5, 0.75, 1.0} |

---

## SUPPLEMENT E — ENTITY IDENTITY PATTERNS

### E.1 Reference ID Pattern Registry

| Entity Type | Pattern | Example | Uniqueness scope |
|---|---|---|---|
| Order | ORD-{YYYYMMDD}-{seq:06d} | ORD-20260702-000001 | Per day |
| Trade | TRD-{YYYYMMDD}-{seq:06d} | TRD-20260702-000001 | Per day |
| Position | POS-{symbol}-{YYYYMMDD} | POS-TATASTEEL-20260702 | Per symbol per day |
| Fill | FIL-{order_ref}-{seq:02d} | FIL-ORD-20260702-000001-01 | Per order |
| Strategy | STR-{slug}-V{major} | STR-MOMBREAK-V3 | Global |
| EvolvedVariant | EVR-{strategy_slug}-{gen:04d} | EVR-MOMBREAK-0024 | Per strategy |
| Hypothesis | HYP-{date}-{seq:04d} | HYP-20260702-0001 | Per day |
| DecisionRecord | DEC-{date}-{seq:04d} | DEC-20260702-0001 | Per day |
| Cycle | CYC-{YYYYMMDD}-{HHMMSS} | CYC-20260702-093000 | Per second |
| Regime | REG-{type}-{startdate} | REG-BULL-20260601 | Per regime start |
| Agent | AGT-{function}-{num:03d} | AGT-MOMENTUM-001 | Global |
| RiskThreshold | RSK-{type}-{version:03d} | RSK-DAILY-LOSS-003 | Per type |

### E.2 External ID System Registry

| External System | ID Field Name | Entity Types | Example | Notes |
|---|---|---|---|---|
| Dhan broker | `dhan_order_id` | Order | `1234567890` | Assigned on broker receipt |
| Dhan broker | `dhan_trade_id` | Trade | `TRD9876543` | Assigned on fill confirmation |
| NSE exchange | `exchange_order_id` | Order | `NSE-OID-20260702-001234` | Assigned by exchange |
| NSE exchange | `isin` | Symbol, Company, ListedSecurity | `INE081A01020` | Permanent ISIN |
| NSE exchange | `series` | Symbol | `EQ`, `FUT`, `OPT` | Instrument series |
| SEBI | `sebi_category` | FIIParticipant | `FPI-CAT-2` | SEBI FPI category |
| Bloomberg | `bbgid` | Symbol | `BBG000BVPXP1` | Bloomberg Global ID |
| Reuters | `ric` | Symbol | `TISC.NS` | Reuters Instrument Code |
| RBI | `indicator_code` | MacroIndicator | `WPI-OVERALL` | RBI data code |
| Yahoo Finance | `yahoo_ticker` | Symbol, Index | `TATASTEEL.NS` | Yahoo Finance ticker |

### E.3 Alias Registration Rules

| Rule ID | Description |
|---|---|
| ALI-01 | Aliases must be registered before use — no ad-hoc alias lookups |
| ALI-02 | An alias may only be assigned to one entity_id within a given entity_type |
| ALI-03 | Aliases are case-insensitive for resolution purposes |
| ALI-04 | Alias history is maintained — former aliases that are revoked are preserved in the alias history |
| ALI-05 | An alias revocation must specify the reason and the date of revocation |
| ALI-06 | The canonical alias (primary display name) is the display_name field — all other aliases are secondary |
| ALI-07 | Alias resolution cache TTL is 5 minutes; cache is invalidated immediately on alias change |
| ALI-08 | When a merge occurs, all aliases of the secondary entity are transferred to the primary entity |

### E.4 Identity Conflict Severity Matrix

| Conflict type | Severity | Auto-resolve | Human notification |
|---|---|---|---|
| Identical UUID4 (impossible — UUID4 collision) | CRITICAL | No | Immediate |
| Identical external ID, same type | HIGH | Yes (older entity is primary) | Yes |
| Identical ISIN | HIGH | Yes | Yes |
| Identical reference ID, same day | MEDIUM | No | Yes |
| Identical alias, same type | MEDIUM | No | Yes |
| Near-duplicate display name (>0.95 similarity) | LOW | No | Yes (weekly summary) |
| Near-duplicate display name (0.80–0.95 similarity) | INFO | No | Weekly summary only |
| Near-duplicate display name (<0.80 similarity) | NONE | No | No |

---

## SUPPLEMENT F — ENTITY GOVERNANCE DECISION RECORDS

### F.1 GDR-ENTITY-001: Entity Retirement Is Irreversible

**Decision:** Entity retirement is irreversible. A retired entity cannot transition to any other lifecycle state.

**Rationale:** Retirement is the declaration that an entity is permanently done. Allowing retirement reversal would create confusion about what "retired" means and could lead to zombie entities — entities that appear to be gone but can suddenly reappear.

**Alternative considered:** Allow retirement reversal with Human Principal approval (same as restore from archive).

**Why rejected:** Archive → Active is appropriate for entities that were temporarily deactivated. Retirement is a permanent declaration, not a temporary deactivation. The appropriate pattern for "we retired this strategy but now want to use it again" is to create a new strategy entity with the same parameters — not to un-retire the old one.

**Date recorded:** 2026-07-02

---

### F.2 GDR-ENTITY-002: One Owner at All Times

**Decision:** Every entity must have exactly one owner at all times, from creation through retirement.

**Rationale:** Multiple owners create accountability ambiguity. If three services all "own" an entity, none of them is truly responsible for its quality.

**Implementation note:** The entity factory enforces that owner_id is a required field at creation. The lifecycle manager verifies that ownership never becomes null during transitions.

**Date recorded:** 2026-07-02

---

### F.3 GDR-ENTITY-003: Financial Entities Never Auto-Merge

**Decision:** Financial entities (Order, Trade, Position, Fill) are never automatically merged, even when identical external IDs are detected.

**Rationale:** A financial entity merge could cause two separate financial records to collapse into one — erasing evidence of a genuine duplicate transaction. This is dangerous for both risk management (double position) and regulatory compliance (erased audit trail).

**Implication:** When identical external IDs are detected for financial entities, a CRITICAL governance alert is raised, trading on the affected symbol is paused, and the Human Principal must resolve the conflict manually.

**Date recorded:** 2026-07-02

---

### F.4 GDR-ENTITY-004: UUID4 for All Entity IDs

**Decision:** All entity IDs use UUID4 (random UUID). Sequential integer IDs, timestamp-based IDs, and UUID1 (time-based) are not used.

**Rationale:** Sequential IDs are enumerable — an attacker (or a bug) could iterate through all entity IDs. UUID1 embeds the machine's MAC address and creation timestamp, which is an information leak. UUID4 is random, non-guessable, and globally unique with no coordination required.

**Date recorded:** 2026-07-02

---

### F.5 GDR-ENTITY-005: Aggregate Invariants Enforce at Write Time

**Decision:** All aggregate-level invariants are checked synchronously at write time, not deferred to a background checker.

**Rationale:** Deferred invariant checking allows the system to be in an inconsistent state between the write and the check. In a trading system, an inconsistent aggregate state (e.g., portfolio capital exceeds allocation total) can cause incorrect decisions in the next cycle.

**Implication:** Writes to entities within an aggregate are slightly slower (aggregate invariant check runs), but correctness is guaranteed at all times.

**Date recorded:** 2026-07-02

---

### F.6 GDR-ENTITY-006: Quality Score Persisted on Entity Record

**Decision:** The quality score (EQS) is persisted directly on the entity record, not computed on demand.

**Rationale:** Computing quality on every entity read would be expensive, especially for entities with many quality dimensions that require cross-entity lookups. Persisting the score allows it to be served at query time with no additional computation.

**Implication:** The EQS must be invalidated and recomputed whenever any input to the quality calculation changes. The Version Manager triggers EQS recomputation on every entity update.

**Date recorded:** 2026-07-02

---

## SUPPLEMENT G — ENTITY ANTI-PATTERN REFERENCE

### G.1 Anti-Pattern: Stateless Entity Tracking

**Description:** Storing only the current state of an entity without preserving historical states.

**Example:** Updating a Position record in-place without creating version records.

**Consequence:** All history is lost. When a trade is reviewed post-closure, there is no record of what the position looked like during the hold period. Learning algorithms cannot analyse how the position evolved.

**Correct pattern:** Every update creates a new version record. The version store is the permanent archive of all entity states.

---

### G.2 Anti-Pattern: Shared Mutable Identity

**Description:** Using a mutable, non-UUID identifier (e.g., strategy name, symbol string) as the primary key for entity relationships.

**Example:** Storing `strategy_name = "MomentumBreakoutV3"` as the foreign key in Trade records instead of `strategy_id` (UUID4).

**Consequence:** When the strategy is renamed or replaced, all Trade records are broken. The string key cannot be reliably resolved.

**Correct pattern:** All entity relationships use UUID4 entity_id as the foreign key. Display names are aliases — they are supplementary, not primary.

---

### G.3 Anti-Pattern: Silent Validation Bypass

**Description:** Creating entities by directly writing to the persistence layer, bypassing the Factory and Validator.

**Example:** Inserting a row directly into the entity table in SQLite, bypassing the Registration Service.

**Consequence:** The entity has no version record, no audit record, no identity resolution registration, no cache entry, and may violate invariants. It is a phantom entity that corrupts the system.

**Correct pattern:** All entity creation goes through the Registration Service → Factory → Validator → Registry sequence. No exceptions.

---

### G.4 Anti-Pattern: Entity Explosion (Over-Granular Entities)

**Description:** Creating too many fine-grained entity types for things that should be value objects or attributes.

**Example:** Creating a separate `EntryPrice` entity, an `ExitPrice` entity, and a `StopLossPrice` entity instead of storing these as value object fields on the Trade entity.

**Consequence:** Entity explosion creates enormous registries, complicated lifecycle management, and poor search performance. The Entity Engine is designed for meaningful domain objects — not for every field value.

**Correct pattern:** Only create entities for domain objects that need identity (they are the same thing across different contexts), lifecycle management, and audit trails. Everything else is a field value.

---

### G.5 Anti-Pattern: Owner Ambiguity

**Description:** Assigning multiple owners to an entity, or assigning a generic owner like "system" that doesn't correspond to any specific accountable component.

**Example:** Assigning `owner = "trading_system"` instead of `owner = "OrderManager"`.

**Consequence:** When the entity degrades in quality, has incorrect data, or needs lifecycle management, there is no specific, accountable owner who can be notified and held responsible.

**Correct pattern:** Every entity has exactly one specific, named, accountable owner — a specific service, agent, or the Human Principal. Generic owners are not permitted.

---

### G.6 Anti-Pattern: Immutable Entity Misuse

**Description:** Treating entities that should evolve as immutable, or creating a new entity for every state change instead of versioning the same entity.

**Example:** Creating a new `Order` entity every time the order status changes, instead of updating the existing Order entity and creating a new version record.

**Consequence:** The entity population grows uncontrollably. Orders have no clear identity — searching for "the order for TATASTEEL from this morning" returns multiple records with different statuses.

**Correct pattern:** Create one entity per domain object. Use versioning to record state changes. Use lifecycle states to represent the current status. Create new entities only when a genuinely new domain object comes into existence.

---

### G.7 Anti-Pattern: Audit Log Gaps

**Description:** Not recording audit events for certain "minor" entity changes to reduce write volume.

**Example:** Skipping audit records for Position.unrealised_pnl updates because they happen every cycle.

**Consequence:** The audit trail is incomplete. If a position shows an unexpected P&L value, there is no audit record to trace when and why it changed.

**Correct pattern:** Define the audit level (MINIMAL, STANDARD, FULL) per entity type. For FULL audit entities, every attribute change creates an audit record. For MINIMAL entities, only creation and retirement are audited. Do not make case-by-case exceptions — they always create gaps.

---

### G.8 Anti-Pattern: Lazy Identity Resolution

**Description:** Assuming that the same display name or reference code always refers to the same entity, without going through the Identity Manager.

**Example:** Querying by `display_name = "TATASTEEL"` in the database instead of resolving via the Identity Manager.

**Consequence:** If the entity's display name changes (e.g., company name change after merger), the query breaks. If two entities have similar names, the wrong entity may be returned.

**Correct pattern:** Always resolve identifiers through the Identity Manager. Never assume that a human-readable string uniquely and reliably identifies an entity.

---

### G.9 Entity Governance Health Dashboard — Reference Metrics

| Metric | Target | Warning threshold | Critical threshold |
|---|---|---|---|
| Entity population (total active) | Monitored | N/A | N/A |
| Average EQS across all entities | >= 0.80 | < 0.75 | < 0.60 |
| Entities with EQS < 0.60 | 0 | > 5 | > 20 |
| Entities with no owner | 0 | > 0 | > 5 |
| Audit chain integrity failures | 0 | > 0 (any) | > 0 (immediate alert) |
| Duplicate detection flags (unresolved) | 0 | > 2 | > 10 |
| Version records lag (behind live entity) | < 1 second | > 5 seconds | > 30 seconds |
| Cache hit rate (L1 + L2) | >= 0.95 | < 0.90 | < 0.80 |
| Registry enrollment latency | < 10 ms | > 50 ms | > 200 ms |
| Entities pending approval (> 24 hours) | 0 | > 2 | > 5 |
| Governance compliance rate | 1.00 (100%) | < 0.98 | < 0.95 |
| Integrity check completion (daily) | Within 1 hour | > 2 hours | Not completed |

---

### G.10 Entity Engine Glossary

| Term | Definition |
|---|---|
| **Aggregate** | A cluster of entities treated as a single unit for consistency; has one aggregate root |
| **Aggregate root** | The entity through which all writes to an aggregate are routed |
| **Alias** | A human-readable alternative name for an entity |
| **Audit chain** | The hash-linked sequence of audit records for an entity |
| **Canonical identity** | The UUID4 entity_id — the permanent, authoritative identifier |
| **Entity** | A named, uniquely identified, persistent domain object with a lifecycle |
| **Entity category** | One of 13 broad groupings of entity types |
| **Entity Constitution** | The 79 mandatory rules governing all entities |
| **Entity Quality Score (EQS)** | The weighted composite quality score for an entity |
| **Entity type** | A specific named entity within a category (e.g., Order within Financial) |
| **External ID** | An identifier assigned by an external system (broker, exchange, regulatory) |
| **Idempotency key** | A caller-provided key that prevents duplicate entity creation |
| **Identity conflict** | A situation where two entities may represent the same domain object |
| **Identity resolution** | Converting any identifier into the canonical entity_id |
| **Invariant** | A rule that must be true about an entity at all times |
| **Lifecycle** | The defined set of states an entity passes through from creation to retirement |
| **Lineage** | The derivation history of an entity — where it came from |
| **Merge** | The process of combining two entities into one |
| **Milestone version** | An explicitly labelled version record at a significant event |
| **Object** | A transient in-memory representation; not an entity |
| **Owner** | The single accountable service or role responsible for an entity |
| **Reference ID** | A human-readable, formatted identifier for an entity |
| **Retirement** | The permanent, irreversible end of an entity's lifecycle |
| **Root entity** | The abstract base from which all entity types derive |
| **Split** | The process of dividing one entity into two |
| **Value object** | A domain concept defined entirely by its value, with no identity |
| **Version** | An immutable snapshot of an entity's state at a specific moment |
| **Version ID** | UUID4 identifying a specific version record |

---
