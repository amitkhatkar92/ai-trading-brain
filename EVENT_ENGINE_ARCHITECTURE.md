# EVENT_ENGINE_ARCHITECTURE.md
# Investment Intelligence Operating System (IIOS)
# Event Engine — Complete Engineering Architecture

---

**Document authority:** Architecture Board  
**Classification:** INTERNAL — Architecture Board Confidential  
**Version:** 1.0  
**Status:** FINAL  
**Date:** 2026-Q2  
**Target system:** IIOS Event Engine  

---

## SCOPE AND PURPOSE

This document defines the complete engineering architecture of the Event Engine for the Investment Intelligence Operating System (IIOS). The Event Engine is the system's real-time nervous system — the component responsible for detecting, ingesting, validating, classifying, propagating, correlating, prioritising, governing, storing, reasoning over, and learning from every event that occurs within or around the IIOS.

This document is:
- The authoritative design specification for the Event Engine
- The mandatory reference for all Event Engine implementations
- A governance instrument defining the 22 components, 15 services, 13 lifecycle stages, and 80+ constitutional rules governing all events

This document is NOT:
- Source code or pseudocode
- A programming specification or API contract
- A database schema

---

## PARENT DOCUMENTS

| Document | Role |
|---|---|
| INVESTMENT_INTELLIGENCE_OPERATING_SYSTEM.md | System root — IIOS mission and boundaries |
| MASTER_KNOWLEDGE_ARCHITECTURE.md | Knowledge layer architecture |
| ENTITY_ONTOLOGY.md | All entity types — events connect to entities |
| RELATIONSHIP_ONTOLOGY.md | All relationship types — events create and modify relationships |
| EVENT_ONTOLOGY.md | Complete event taxonomy — canonical reference |
| INFORMATION_ONTOLOGY.md | Information types produced and consumed by events |
| KNOWLEDGE_ENGINE_ARCHITECTURE.md | Knowledge Engine — consumer of event intelligence |
| ENTITY_ENGINE_ARCHITECTURE.md | Entity Engine — provider of entity context to events |
| RELATIONSHIP_ENGINE_ARCHITECTURE.md | Relationship Engine — events trigger relationship updates |
| CORE_FRAMEWORK_ARCHITECTURE.md | Core framework — shared infrastructure |
| ENGINEERING_STANDARDS.md | Engineering standards — naming, versioning, audit |

---

## IIOS POSITION OF THE EVENT ENGINE

```
┌─────────────────────────────────────────────────────────────────┐
│                   IIOS — 17-Layer Architecture                  │
├─────────────────────────────────────────────────────────────────┤
│  GlobalIntelligence  │  MarketIntelligence  │  MetaLearning     │
├──────────────────────┴──────────────────────┴───────────────────┤
│              EVENT ENGINE  ◄──── Central Nervous System         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ Detection    │  │ Processing   │  │ Propagation          │  │
│  │ Ingestion    │  │ Pipeline     │  │ Correlation          │  │
│  │ Validation   │  │ Real-time    │  │ Learning             │  │
│  │ Classification│  │ Streaming    │  │ Governance           │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│  Entity Engine  │  Relationship Engine  │  Knowledge Engine     │
├─────────────────┴───────────────────────┴───────────────────────┤
│  OpportunityEngine  │  StrategyLab  │  CapitalRiskEngine        │
├─────────────────────┴──────────────────┴────────────────────────┤
│  RiskControl  │  MarketSimulation  │  RiskGuardian              │
├───────────────┴────────────────────┴────────────────────────────┤
│  DebateAndDecision  │  ExecutionEngine  │  TradeMonitoring       │
├─────────────────────┴───────────────────┴───────────────────────┤
│  LearningSystem  │  PerformanceAnalytics  │  ResearchLab        │
├──────────────────┴────────────────────────┴─────────────────────┤
│  ValidationEngine  │  ControlTower  │  SystemMonitor            │
└─────────────────────────────────────────────────────────────────┘
```

---

## EVENT DATA FLOW OVERVIEW

```
External World                    Event Engine                    IIOS Consumers
─────────────────                 ────────────────                ───────────────
Market data feeds  ──[raw signal]──► Detection Layer             Knowledge Engine
News / NLP feeds   ──[text event]──► Ingestion Manager           Relationship Engine
Broker callbacks   ──[order fill]──► Validation Engine           Strategy Layer
System monitors    ──[health evt]──► Classification Engine       Risk Engine
Internal agents    ──[AI event]────► Priority Manager            Learning System
Scheduler          ──[scheduled]──► Event Queue Manager          Notification System
                                    │
                                    ▼
                              Event Registry
                              (immutable store)
                                    │
                                    ├──► Propagation Engine ──► Downstream events
                                    ├──► Correlation Engine ──► Event clusters
                                    ├──► Timeline Manager ───► Temporal index
                                    └──► Analytics Manager ──► Intelligence reports
```

---

## ENTITY → EVENT CONCEPTUAL MODEL

```
Entity (stable, persistent)
   │
   │ experiences
   ▼
Event (timestamped, immutable, ephemeral impact)
   │
   │ triggers
   ▼
State Change (in one or more entities or relationships)
   │
   │ generates
   ▼
Derived Event (event caused by another event)
   │
   │ forms
   ▼
Event Chain (ordered sequence of causally linked events)
   │
   │ produces
   ▼
Intelligence (learning, signals, hypotheses)
```

---

## TABLE OF CONTENTS

| Part | Title |
|---|---|
| I | Event Engine Philosophy |
| II | Event Engine Architecture |
| III | Core Components (22 components) |
| IV | Event Lifecycle (13 stages) |
| V | Event Services (15 services) |
| VI | Event Processing Architecture |
| VII | Event Intelligence Framework |
| VIII | Event Governance |
| IX | Event Constitution (80+ rules) |
| X | Event Readiness Checklist (14 sections) |
| Supplement A | Event Type Catalogue |
| Supplement B | Component Interface Reference |
| Supplement C | Processing Pipeline Patterns |
| Supplement D | Intelligence Framework Reference |
| Supplement E | Governance Decision Records |
| Supplement F | Anti-Pattern Reference |
| Supplement G | Event Glossary |

---
## PART I — EVENT ENGINE PHILOSOPHY

### 1.1 Why Events Are First-Class Citizens

In the IIOS, three kinds of things exist: **entities** (things that persist), **relationships** (connections between persistent things), and **events** (changes that happen at a point in time). Entities and relationships describe the structure of the world. Events describe how the world changes.

Events are first-class citizens in the IIOS for the following reasons:

**1. All intelligence is change-driven.** A portfolio that is static generates no intelligence. Intelligence is created when conditions change — when a price crosses a threshold, when a strategy fills an order, when a regime transitions, when an economic announcement moves markets. The IIOS cannot reason about change without a rigorous event model.

**2. All decisions are event-triggered.** No agent in the IIOS makes a decision in a vacuum. Decisions are triggered by events: a new hypothesis event, a confidence threshold event, a risk limit breach event, a market open event. Without a governed event layer, decisions are not traceable to their causes.

**3. All learning is history of events.** The Learning System learns by studying sequences of events — what happened before a profitable trade, what events preceded a regime change, what patterns of events indicate a strategy is degrading. Events are the raw material of machine learning in financial intelligence.

**4. All accountability requires events.** An audit trail is a sequence of events. If the system cannot record every event that led to a decision, it cannot explain or justify that decision. Regulators, risk officers, and the Human Principal require event-level accountability.

**5. Events create time.** Without events, the IIOS would exist in a timeless state. Events are the mechanism by which time advances in the system — each event moves the system from one state to another. The Event Timeline is the system's experience of history.

---

### 1.2 Conceptual Distinctions — 21 Event-Related Terms

The following 21 distinctions are foundational to the Event Engine's design. Confusing these concepts leads to architectural errors that are expensive to correct.

---

#### 1.2.1 Entity

An **Entity** is a persistent, named thing in the IIOS that maintains identity across time. A strategy, an instrument, a portfolio, a macroeconomic indicator — these are entities. An entity may be involved in many events over its lifetime, but it does not cease to exist when an event involving it concludes. The Entity Engine manages all entities.

---

#### 1.2.2 Relationship

A **Relationship** is a typed, directed or undirected connection between two entities that persists over time and has a defined strength and confidence. A CORRELATED_WITH relationship between TATASTEEL.NS and NIFTY50 exists independently of any particular event. Events may create, strengthen, weaken, or destroy relationships — but a relationship is not itself an event. The Relationship Engine manages all relationships.

---

#### 1.2.3 Information

**Information** is structured knowledge about the state of the world — a price quote, a news article, a risk report, a hypothesis. Information is produced by processes and consumed by other processes. An event may carry information as payload, but information itself is not an event. Information is static in the sense that a price quote for NIFTY at 10:30:00 does not change — it is a fact about a moment in time.

---

#### 1.2.4 Observation

An **Observation** is a specific, timestamped measurement of the state of an entity or system — a price reading, a VIX level, a P&L value. Observations are information elements. An observation is not an event, but a sequence of observations may trigger an event (e.g., VIX crossing 30 is an event derived from multiple consecutive VIX observations).

---

#### 1.2.5 Event

An **Event** is an immutable, timestamped, atomic occurrence that marks a state change in the IIOS or the external world. Events are:
- **Immutable** — once recorded, the event record does not change
- **Timestamped** — precise occurrence time is mandatory
- **Atomic** — an event is a single occurrence, not a process
- **Categorised** — every event belongs to a defined type in the Event Catalog
- **Consequential** — every event has observable effects on the system state

The distinction from Observation: an observation is a measurement; an event is a change. The VIX level at 10:30 is an observation. The VIX crossing 30 for the first time in a session is an event.

---

#### 1.2.6 Incident

An **Incident** is a high-severity, operationally significant event that requires active management and response. An incident is not merely an event to be logged — it is an event that requires the system or Human Principal to take a defined remedial action within a specified time window. All incidents are events, but not all events are incidents. A broker connectivity failure is an incident. A strategy generating a new hypothesis is an event but not normally an incident.

---

#### 1.2.7 Trigger

A **Trigger** is a predefined condition that, when met, causes the Event Engine to generate a new event. Triggers are event preconditions — they define "when X happens, generate event Y". A price threshold trigger, a time-based trigger, a sequence-completion trigger — all are trigger definitions. The trigger is the rule; the resulting event is the consequence. Triggers are managed by the Event Detector.

---

#### 1.2.8 Signal

A **Signal** is a derived, analytical output produced from one or more events that indicates something meaningful to a consuming agent or system. A signal is more abstracted than an event — it synthesises multiple observations and events into a single directional conclusion. "VIX elevated → RISK_HEIGHTENED signal" is an example. Signals are produced by the Event Intelligence Framework and consumed by strategy and risk layers.

---

#### 1.2.9 State Change

A **State Change** is the consequence of an event — the transition of one or more entities or relationships from one documented state to another. An event is the occurrence; a state change is the result. When a portfolio position is opened (event: POSITION_OPENED), the portfolio entity transitions from a state with N positions to a state with N+1 positions (state change). State changes must be traceable to the triggering event.

---

#### 1.2.10 Transition

A **Transition** is a formal lifecycle state change for an entity, relationship, or event — a move from one defined lifecycle state to another (CREATED → ACTIVE, ACTIVE → DEPRECATED). Transitions are themselves events (every lifecycle transition generates a LIFECYCLE_TRANSITION event). Transitions are governed by the state machine defined for each entity/relationship/event type.

---

#### 1.2.11 Action

An **Action** is a deliberate, goal-directed operation performed by an agent or the system in response to an event. "Buy 100 shares of TATASTEEL" is an action. "Send Telegram alert" is an action. Actions are not events themselves — they are the system's response to events. However, the completion of an action generates an action completion event (e.g., ORDER_FILLED).

---

#### 1.2.12 Cause

A **Cause** is an antecedent event or condition that is responsible for another event occurring. In the IIOS, causes are represented by CAUSED_BY relationships in the Relationship Engine. The Event Dependency Engine traces causal chains. A cause must precede its effect in time, must have a mechanism of influence, and must have a confidence score reflecting the certainty of the causal claim.

---

#### 1.2.13 Effect

An **Effect** is a consequent event or state change that results from a cause. In a causal chain, the effect follows the cause. Effects are modelled as downstream events in the Event Propagation Engine. A single cause may have multiple effects, and a single effect may have multiple contributing causes.

---

#### 1.2.14 Root Cause

A **Root Cause** is the initiating cause in a causal chain — the event at the origin that, if prevented, would have prevented all downstream effects. Root Cause Analysis (RCA) is one of the core operations of the Event Intelligence Framework. In financial intelligence, root causes are frequently macroeconomic events (e.g., a Federal Reserve announcement) that trigger cascading effects through market, sector, instrument, strategy, and portfolio layers.

---

#### 1.2.15 Derived Event

A **Derived Event** is an event generated by the Event Engine's analytical processes in response to one or more primary events — not directly from an external source. A "VOLATILITY_SPIKE event" derived from 20 consecutive price events; a "REGIME_CHANGE event" derived from a cluster of market structure events. Derived events are annotated with their derivation logic and source events.

---

#### 1.2.16 Composite Event

A **Composite Event** is an event that can only be identified by observing a specific combination or pattern of multiple simpler events. A "MARKET_CRASH composite event" is not a single price drop — it is a defined pattern involving price, volume, breadth, and volatility events over a defined time window. Composite event detection requires pattern-matching logic in the Event Detector and Classification Engine.

---

#### 1.2.17 Event Chain

An **Event Chain** is an ordered sequence of causally or temporally linked events in which each event either causes, triggers, or follows from the previous event. Event chains are the primary unit of analysis for the Event Intelligence Framework. A complete event chain might be: FED_ANNOUNCEMENT → CURRENCY_MOVE → INDEX_DECLINE → VOLATILITY_SPIKE → RISK_LIMIT_BREACH → POSITION_REDUCED → PORTFOLIO_REBALANCED.

---

#### 1.2.18 Event Context

**Event Context** is the structured state of the IIOS at the moment an event occurs — the regime, the portfolio state, the active strategies, the current risk levels, the recent event history. Event context is captured and attached to every event record. Without context, events cannot be interpreted correctly: a 2% NIFTY50 decline means different things in a bull regime than in a bear regime.

---

#### 1.2.19 Event Instance

An **Event Instance** is a specific, recorded occurrence of an event — the unique record in the Event Registry capturing this particular occurrence at this particular time with this particular payload. "NIFTY50 crossed 22,000 at 14:37:22 on 2026-06-15" is an event instance of event type PRICE_THRESHOLD_CROSSED.

---

#### 1.2.20 Event Type

An **Event Type** is the definition in the Event Catalog that describes a class of events — their schema, expected properties, severity levels, propagation rules, and governance policies. Event instances are instances of an event type. The Event Type is the template; the Event Instance is the realisation.

---

#### 1.2.21 Event Severity

**Event Severity** classifies the operational impact of an event. The IIOS uses five severity levels:

| Level | Name | Description |
|---|---|---|
| 5 | CRITICAL | System must act immediately; Human Principal notification required |
| 4 | HIGH | Significant impact on portfolio, risk, or strategy; agent action required |
| 3 | MEDIUM | Notable signal; monitoring and analysis required |
| 2 | LOW | Informational; no immediate action required |
| 1 | TRACE | Internal system event; diagnostic value only |

---

#### 1.2.22 Event Criticality

**Event Criticality** is distinct from severity — it measures the operational consequence of an event if it is missed, delayed, or misclassified. A HIGH severity event that is correctly handled has no criticality impact. A MEDIUM severity event that is missed (because it was misclassified as TRACE) may result in a CRITICAL risk management failure. Criticality is a governance metric; severity is an operational metric.

---

#### 1.2.23 Event Confidence

**Event Confidence** measures the system's certainty that the event has occurred, that its classification is correct, and that its payload is accurate. Market data events from authoritative feeds have confidence 1.0. Derived events from analytical processes may have confidence 0.60–0.90. Hypothesis-triggering events from AI agents may have confidence 0.50–0.85. Events with confidence below 0.50 are flagged for Human Principal review before acting on them.

---

### 1.3 Design Principles

| Principle | Statement |
|---|---|
| Immutability | All recorded events are permanently immutable. No event record is modified after creation. |
| Completeness | Every event that occurs in the IIOS or that affects IIOS decisions is recorded. |
| Traceability | Every event can be traced to its source, its cause, and its downstream effects. |
| Priority ordering | The system always processes higher-severity events before lower-severity events. |
| Idempotency | Receiving the same event signal multiple times produces at most one event record. |
| Bounded latency | Every event type has a defined maximum acceptable detection-to-processing latency. |
| Governance first | Every event is governed — owned, classified, audited, and retained per policy. |
| Learning always | Every processed event contributes to the Learning System's dataset. |

---
## PART II — EVENT ENGINE ARCHITECTURE

### 2.1 Architecture Philosophy

The Event Engine architecture is a 15-layer hierarchy that mirrors the domain structure of the IIOS. Events are produced at the outermost layers (global market events, government events) and cascade inward toward portfolio, risk, AI, and system events. This layering reflects the direction of information flow in financial markets: macro conditions shape market conditions, which shape instrument conditions, which shape trading conditions, which shape portfolio conditions.

---

### 2.2 Event Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      EVENT ROOT (Layer 0)                               │
│     All events trace to this root. No event exists outside the tree.    │
├─────────────────────────────────────────────────────────────────────────┤
│  Layer 1: MARKET EVENTS      │  Layer 2: CORPORATE EVENTS               │
│  Price, Volume, Spread,      │  Earnings, Dividends, M&A,               │
│  Breadth, Circuit Breakers   │  Leadership changes, Restructuring        │
├──────────────────────────────┴─────────────────────────────────────────┤
│  Layer 3: ECONOMIC EVENTS    │  Layer 4: GOVERNMENT EVENTS              │
│  GDP, Inflation, Trade,      │  Policy, Budget, Tax, Regulation,        │
│  Industrial Output           │  Sanctions, Elections                    │
├──────────────────────────────┴─────────────────────────────────────────┤
│  Layer 5: CENTRAL BANK EVENTS │  Layer 6: SECTOR EVENTS                 │
│  Rate decisions, QE/QT,       │  Rotation, Regulation, Supply chain,    │
│  Guidance, Minutes            │  Technology disruption                  │
├───────────────────────────────┴────────────────────────────────────────┤
│  Layer 7: COMPANY EVENTS     │  Layer 8: TRADING EVENTS                 │
│  Results, Guidance,          │  Order, Fill, Cancel, Reject,            │
│  Insider, Analyst rating     │  Partial fill, Slippage                  │
├──────────────────────────────┴─────────────────────────────────────────┤
│  Layer 9: PORTFOLIO EVENTS   │  Layer 10: RISK EVENTS                   │
│  Rebalance, NAV change,      │  Limit breach, Drawdown, VIX spike,      │
│  Allocation, P&L milestone   │  Margin call, Kill switch                │
├──────────────────────────────┴─────────────────────────────────────────┤
│  Layer 11: AI EVENTS         │  Layer 12: LEARNING EVENTS               │
│  Agent decision, Debate,     │  Strategy promotion, Demotion,           │
│  Hypothesis creation,        │  Weight update, Parameter evolution,     │
│  Confidence change           │  Calibration complete                    │
├──────────────────────────────┴─────────────────────────────────────────┤
│  Layer 13: SYSTEM EVENTS     │  Layer 14: KNOWLEDGE EVENTS              │
│  Health, Latency, Error,     │  Entity create/update/retire,            │
│  Connectivity, Restart       │  Relationship create/update,             │
│                              │  Hypothesis validate                     │
└──────────────────────────────┴─────────────────────────────────────────┘
                               │
                    Layer 15: DECISION EVENTS
                    Strategy select, Approval, Override,
                    Instruction, Execution authorise
```

---

### 2.3 Layer 0: Event Root

The Event Root is the abstract ancestor of all events in the IIOS. It defines the common mandatory attributes that all events inherit: event_id, event_type, timestamp, source, severity, confidence, context, version, and immutability guarantee. The Event Root is not an event type itself — it is the architectural supertype from which all event categories descend.

---

### 2.4 Layer 1: Market Events

Market events are generated by price formation, volume activity, and market structure changes. They are the most frequent event type in the IIOS — hundreds or thousands per session — and the primary input to the trading and risk layers.

| Sub-category | Events |
|---|---|
| Price Events | PRICE_TICK, PRICE_THRESHOLD_CROSSED, PRICE_GAP_UP, PRICE_GAP_DOWN, INTRADAY_HIGH, INTRADAY_LOW, CLOSE_PRICE_SET |
| Volume Events | VOLUME_SPIKE, VOLUME_DROUGHT, BLOCK_TRADE_DETECTED |
| Spread Events | SPREAD_WIDENED, SPREAD_NARROWED, ILLIQUIDITY_DETECTED |
| Breadth Events | ADVANCE_DECLINE_EXTREME, BREADTH_COLLAPSE, BREADTH_RECOVERY |
| Structure Events | CIRCUIT_BREAKER_TRIGGERED, TRADING_HALT, MARKET_OPEN, MARKET_CLOSE, PRE_MARKET_START |
| Volatility Events | VOLATILITY_SPIKE, VOLATILITY_COLLAPSE, VOLATILITY_REGIME_CHANGE, IV_RANK_EXTREME |
| Regime Events | REGIME_TRANSITION, REGIME_CONFIRMED, TREND_ESTABLISHED, TREND_BROKEN |

**Architectural importance:** Market events are the engine of derived events. A PRICE_THRESHOLD_CROSSED event may trigger a POSITION_OPENED event, which triggers a PORTFOLIO_NAV_CHANGED event, which triggers a RISK_RECALCULATION_REQUIRED event.

---

### 2.5 Layer 2: Corporate Events

Corporate events arise from the actions and disclosures of publicly listed companies. They have well-defined scheduled and unscheduled variants. Scheduled corporate events (earnings, dividends, ex-dates) are anticipated by the system. Unscheduled events (unexpected management changes, regulatory actions) require rapid detection and classification.

| Sub-category | Events |
|---|---|
| Earnings Events | EARNINGS_ANNOUNCED, EARNINGS_SURPRISE_POSITIVE, EARNINGS_SURPRISE_NEGATIVE, EARNINGS_IN_LINE, GUIDANCE_RAISED, GUIDANCE_LOWERED |
| Dividend Events | DIVIDEND_DECLARED, DIVIDEND_INCREASED, DIVIDEND_DECREASED, DIVIDEND_OMITTED, EX_DIVIDEND_DATE |
| Corporate Action Events | STOCK_SPLIT, REVERSE_SPLIT, RIGHTS_ISSUE, BONUS_ISSUE, BUYBACK_ANNOUNCED |
| M&A Events | ACQUISITION_ANNOUNCED, MERGER_APPROVED, MERGER_BLOCKED, HOSTILE_TAKEOVER |
| Leadership Events | CEO_CHANGE, CFO_CHANGE, BOARD_CHANGE, INSIDER_BUY, INSIDER_SELL |
| Regulatory Events | REGULATORY_ACTION, PENALTY_IMPOSED, LICENCE_SUSPENDED |
| Analyst Events | RATING_UPGRADE, RATING_DOWNGRADE, PRICE_TARGET_CHANGE, COVERAGE_INITIATION |

---

### 2.6 Layer 3: Economic Events

Economic events arise from the release of macroeconomic indicators and the publication of government statistical data. These are scheduled events with defined release calendars, making them amenable to anticipatory preparation in the IIOS.

| Sub-category | Events |
|---|---|
| Growth Events | GDP_RELEASED, GDP_REVISION, IIP_RELEASED, MANUFACTURING_PMI, SERVICES_PMI |
| Inflation Events | CPI_RELEASED, WPI_RELEASED, CORE_INFLATION_ELEVATED, INFLATION_TARGET_MET |
| Employment Events | UNEMPLOYMENT_RELEASED, PAYROLLS_RELEASED, LABOUR_MARKET_TIGHTENING |
| Trade Events | TRADE_BALANCE_RELEASED, EXPORT_SURGE, IMPORT_SURGE, CURRENT_ACCOUNT_CHANGE |
| Credit Events | CREDIT_GROWTH_RELEASED, NPL_RATE_CHANGED, CREDIT_DEFAULT_EVENT |
| Commodity Events | OIL_PRICE_SHOCK, GOLD_PRICE_MOVE, METAL_PRICE_SHOCK |

---

### 2.7 Layer 4: Government Events

Government events include legislative, fiscal, and regulatory actions that directly or indirectly affect financial markets. These are among the highest-impact events in the IIOS — a budget announcement or regulatory change can restructure entire sectors.

| Sub-category | Events |
|---|---|
| Budget Events | UNION_BUDGET_ANNOUNCED, FISCAL_STIMULUS_ANNOUNCED, TAX_RATE_CHANGED |
| Policy Events | ECONOMIC_POLICY_CHANGED, TRADE_POLICY_CHANGED, SECTOR_POLICY_CHANGED |
| Regulatory Events | NEW_REGULATION_ISSUED, REGULATION_AMENDED, COMPLIANCE_DEADLINE |
| Election Events | ELECTION_ANNOUNCED, ELECTION_RESULT, GOVERNMENT_FORMED |
| Sanctions Events | SANCTIONS_IMPOSED, SANCTIONS_LIFTED |
| International Events | TRADE_AGREEMENT, GEOPOLITICAL_ESCALATION, GEOPOLITICAL_DE_ESCALATION |

---

### 2.8 Layer 5: Central Bank Events

Central bank events are among the most market-moving events in the financial system. The IIOS assigns the highest monitoring priority to central bank actions. In India, the primary source is the Reserve Bank of India (RBI); globally, the Federal Reserve, European Central Bank, and Bank of Japan are monitored for cross-market influence.

| Sub-category | Events |
|---|---|
| Rate Events | RBI_RATE_DECISION, RATE_CUT, RATE_HIKE, RATE_HOLD, SURPRISE_RATE_CHANGE |
| Liquidity Events | REPO_OPERATION, OMO_PURCHASE, OMO_SALE, LIQUIDITY_INJECTION |
| Guidance Events | MONETARY_POLICY_STATEMENT, MPC_MINUTES_RELEASED, GOVERNOR_SPEECH |
| QE/QT Events | QUANTITATIVE_EASING_ANNOUNCED, QUANTITATIVE_TIGHTENING_ANNOUNCED |
| Reserve Events | RESERVE_REQUIREMENT_CHANGED, CRR_CHANGED, SLR_CHANGED |

---

### 2.9 Layer 6: Sector Events

Sector events capture structural changes at the industry level — regulatory changes that affect all companies in a sector, technology disruptions, supply chain shifts, and sector rotation signals.

| Sub-category | Events |
|---|---|
| Rotation Events | SECTOR_ROTATION_SIGNAL, SECTOR_OUTPERFORMANCE, SECTOR_UNDERPERFORMANCE |
| Regulatory Events | SECTOR_REGULATION_CHANGED, SUBSIDY_ANNOUNCED, TARIFF_CHANGED |
| Supply Chain Events | SUPPLY_SHOCK, SUPPLY_RECOVERY, LOGISTICS_DISRUPTION |
| Technology Events | TECHNOLOGY_DISRUPTION_SIGNAL, AUTOMATION_IMPACT_DETECTED |
| Sentiment Events | INSTITUTIONAL_FLOW_SHIFT, FII_ACTIVITY_SPIKE, DII_ACTIVITY_SPIKE |

---

### 2.10 Layer 7: Company Events

Company events are the instrument-specific events that most directly drive trading decisions. They combine scheduled corporate events (Layer 2) with unscheduled company-specific events that arise from monitoring.

| Sub-category | Events |
|---|---|
| Financial Events | RESULTS_RELEASED, INTERIM_RESULTS, ANNUAL_RESULTS |
| Operational Events | NEW_CONTRACT_WON, PLANT_SHUTDOWN, CAPACITY_EXPANSION |
| Risk Events | DEBT_DOWNGRADE, CREDIT_WATCH, LITIGATION_ANNOUNCED |
| Market Events | NIFTY50_INCLUSION, NIFTY50_EXCLUSION, F&O_ADDITION, F&O_REMOVAL |

---

### 2.11 Layer 8: Trading Events

Trading events are generated by the Execution Engine — they record the lifecycle of every order and position in the system. These are among the most operationally critical events because they directly update portfolio state.

| Sub-category | Events |
|---|---|
| Order Events | ORDER_CREATED, ORDER_SUBMITTED, ORDER_ACKNOWLEDGED, ORDER_CANCELLED, ORDER_REJECTED, ORDER_EXPIRED |
| Fill Events | ORDER_FILLED, ORDER_PARTIALLY_FILLED, FILL_CONFIRMED, FILL_REJECTED |
| Position Events | POSITION_OPENED, POSITION_INCREASED, POSITION_DECREASED, POSITION_CLOSED, POSITION_FLIPPED |
| Execution Events | SLIPPAGE_DETECTED, EXECUTION_DELAY, BROKER_REJECTION, PRICE_IMPROVEMENT |
| Paper Events | PAPER_ORDER_CREATED, PAPER_FILL_SIMULATED, PAPER_POSITION_UPDATED |

---

### 2.12 Layer 9: Portfolio Events

Portfolio events aggregate trading events into portfolio-level state changes. They represent the consequence of trading activity for the portfolio as a whole.

| Sub-category | Events |
|---|---|
| NAV Events | PORTFOLIO_NAV_UPDATED, NAV_MILESTONE, DAILY_NAV_CLOSE |
| P&L Events | DAILY_PNL_COMPUTED, UNREALISED_PNL_CHANGE, REALISED_PNL_RECORDED, PNL_MILESTONE |
| Allocation Events | PORTFOLIO_REBALANCED, ALLOCATION_CHANGED, CASH_LEVEL_CHANGED |
| Performance Events | DRAWDOWN_NEW_LOW, DRAWDOWN_RECOVERY, SHARPE_UPDATED, ALPHA_UPDATED |
| Benchmark Events | BENCHMARK_OUTPERFORMED, BENCHMARK_UNDERPERFORMED |

---

### 2.13 Layer 10: Risk Events

Risk events are generated when risk thresholds are approached or breached. They represent the risk management layer's observations of the system state. Risk events trigger the most immediate responses — including automatic position reduction and kill-switch activation.

| Sub-category | Events |
|---|---|
| Limit Events | POSITION_LIMIT_APPROACHED, POSITION_LIMIT_BREACHED, DAILY_LOSS_LIMIT_BREACHED |
| Volatility Risk Events | VIX_SPIKE, PORTFOLIO_VOLATILITY_ELEVATED, CORRELATION_BREAKDOWN |
| Drawdown Events | MAX_DRAWDOWN_APPROACHED, MAX_DRAWDOWN_BREACHED, TRAILING_STOP_TRIGGERED |
| Kill Switch Events | KILL_SWITCH_TRIGGERED, KILL_SWITCH_RESET, TRADING_SUSPENDED |
| Stress Events | STRESS_SCENARIO_ACTIVATED, TAIL_RISK_DETECTED, BLACK_SWAN_SIGNAL |
| Margin Events | MARGIN_CALL_RECEIVED, MARGIN_LIQUIDATION_RISK |

---

### 2.14 Layer 11: AI Events

AI events are generated by the 62 AI agents in the IIOS — they record decisions, hypotheses, debates, confidence changes, and reasoning outputs.

| Sub-category | Events |
|---|---|
| Decision Events | AGENT_DECISION_MADE, AGENT_OVERRIDE, AGENT_ABSTAIN |
| Hypothesis Events | HYPOTHESIS_CREATED, HYPOTHESIS_VALIDATED, HYPOTHESIS_REFUTED, HYPOTHESIS_EVOLVED |
| Debate Events | DEBATE_INITIATED, DEBATE_CONCLUDED, CONSENSUS_REACHED, DISSENT_RECORDED |
| Confidence Events | AGENT_CONFIDENCE_CHANGED, MODEL_CONFIDENCE_BELOW_THRESHOLD |
| Reasoning Events | CAUSAL_CHAIN_IDENTIFIED, INFLUENCE_PROPAGATION_COMPUTED, PATTERN_MATCHED |

---

### 2.15 Layer 12: Learning Events

Learning events record the evolution of the IIOS's intelligence — when strategies are promoted or demoted, when models are recalibrated, when parameter weights are updated.

| Sub-category | Events |
|---|---|
| Strategy Events | STRATEGY_PROMOTED, STRATEGY_DEMOTED, STRATEGY_DISABLED, STRATEGY_ENABLED |
| Calibration Events | MODEL_RECALIBRATED, WEIGHT_UPDATED, PARAMETER_EVOLVED, BACKTEST_COMPLETED |
| Performance Events | WIN_RATE_MILESTONE, SHARPE_THRESHOLD_MET, DRAWDOWN_RECOVERY_COMPLETE |
| Knowledge Events | NEW_PATTERN_LEARNED, ANOMALY_ADDED_TO_CATALOG, REGIME_MODEL_UPDATED |

---

### 2.16 Layer 13: System Events

System events monitor the operational health of the IIOS infrastructure — connectivity, latency, errors, restarts, and performance metrics.

| Sub-category | Events |
|---|---|
| Health Events | SYSTEM_HEALTHY, SYSTEM_DEGRADED, COMPONENT_FAILURE, COMPONENT_RECOVERY |
| Connectivity Events | BROKER_CONNECTED, BROKER_DISCONNECTED, FEED_CONNECTED, FEED_DISCONNECTED |
| Latency Events | LATENCY_THRESHOLD_EXCEEDED, LATENCY_CRITICAL, LATENCY_NORMALIZED |
| Error Events | UNHANDLED_EXCEPTION, TIMEOUT, RETRY_LIMIT_EXCEEDED, DATA_CORRUPTION_DETECTED |
| Lifecycle Events | SYSTEM_STARTUP, SYSTEM_SHUTDOWN, SCHEDULER_STARTED, SCHEDULER_STOPPED |
| Audit Events | AUDIT_CHAIN_BROKEN, INTEGRITY_CHECK_FAILED, TAMPER_DETECTED |

---

### 2.17 Layer 14: Knowledge Events

Knowledge events record structural changes to the IIOS's knowledge graph — entity creation, relationship updates, and hypothesis validation.

| Sub-category | Events |
|---|---|
| Entity Events | ENTITY_CREATED, ENTITY_UPDATED, ENTITY_ARCHIVED, ENTITY_RETIRED |
| Relationship Events | RELATIONSHIP_CREATED, RELATIONSHIP_STRENGTH_CHANGED, RELATIONSHIP_DEPRECATED |
| Knowledge Events | KNOWLEDGE_GRAPH_UPDATED, KNOWLEDGE_INCONSISTENCY_DETECTED |
| Governance Events | GOVERNANCE_POLICY_APPLIED, GOVERNANCE_VIOLATION_DETECTED |

---

### 2.18 Layer 15: Decision Events

Decision events record the high-level decisions made by the IIOS as a system — strategy selections, approvals, overrides, and execution authorisations.

| Sub-category | Events |
|---|---|
| Strategy Selection Events | STRATEGY_SELECTED, STRATEGY_REJECTED, STRATEGY_DEFERRED |
| Approval Events | DECISION_APPROVED, DECISION_REJECTED, DECISION_ESCALATED |
| Override Events | HUMAN_OVERRIDE, AUTOMATED_OVERRIDE, EMERGENCY_STOP |
| Instruction Events | INSTRUCTION_ISSUED, INSTRUCTION_ACKNOWLEDGED, INSTRUCTION_EXECUTED |
| Authorisation Events | EXECUTION_AUTHORISED, EXECUTION_BLOCKED, EXECUTION_DEFERRED |

---

### 2.19 Cross-Layer Event Flow

```
MACRO TRIGGER
└── Layer 3: GDP_RELEASED (Economic Event)
    └── Layer 1: REGIME_TRANSITION (Market Event) [derived]
        └── Layer 1: VOLATILITY_SPIKE (Market Event) [derived]
            └── Layer 10: VIX_SPIKE (Risk Event) [derived]
                └── Layer 10: POSITION_LIMIT_APPROACHED (Risk Event) [derived]
                    ├── Layer 11: AGENT_DECISION_MADE (AI Event) — reduce exposure
                    │   └── Layer 8: ORDER_CREATED (Trading Event)
                    │       └── Layer 8: ORDER_FILLED (Trading Event)
                    │           └── Layer 9: PORTFOLIO_NAV_UPDATED (Portfolio Event)
                    └── Layer 15: DECISION_ESCALATED (Decision Event) — alert Human Principal
```

This cross-layer flow diagram illustrates why the Event Engine must support depth-first propagation tracking — each layer's events depend on preceding layers.

---
## PART III — CORE COMPONENTS

### 3.1 Component Architecture Overview

The Event Engine consists of 22 core components. Components are organised into four functional groups:

| Group | Components | Purpose |
|---|---|---|
| Foundation | Registry, Catalog, Factory, Identity Manager | Core event data management |
| Processing | Detector, Ingestion Manager, Classification Engine, Validator, Metadata Manager | Event acquisition and classification |
| Intelligence | Correlation Engine, Propagation Engine, Dependency Engine, Priority Manager, Timeline Manager | Event analysis and ordering |
| Management | Queue Manager, Lifecycle Manager, Audit Manager, Governance Manager, Search Engine, Analytics Manager, Archive Manager, Evolution Manager | Event lifecycle and governance |

---

### 3.2 Component 1: Event Registry

**Purpose:** The Event Registry is the authoritative, persistent store of all event instances in the IIOS. It is the single source of truth for "what events have occurred".

**Responsibilities:**
- Accept new event registrations from the Factory
- Assign canonical event_id (UUID4) to every new event
- Persist every event record to the immutable event store
- Provide lookup by event_id, event_type, source, time range
- Support partitioned access by event category (market, trading, risk, etc.)
- Enforce the immutability constraint — no event record is ever modified or deleted
- Maintain the Registry metadata index (count by type, count by day, last event per type)

**Inputs:** Event record draft from Factory; lookup requests from consumers

**Outputs:** Registration confirmation with assigned event_id; event records on query

**Dependencies:** Persistence Layer (Database Architecture); Identity Manager; Audit Manager

**Failure Handling:**
- On persistence failure: queue event to in-memory buffer; retry with exponential backoff; alert after 3 failed retries
- On duplicate detection: return existing event_id (idempotent); do not create second record
- On corrupt input: FAIL_FAST with ValidationError; do not persist corrupt records

---

### 3.3 Component 2: Event Catalog

**Purpose:** The Event Catalog is the authoritative definition store for all event types in the IIOS. It defines the schema, properties, constraints, severity rules, and governance policies for every event type.

**Responsibilities:**
- Maintain the complete, versioned list of approved event types
- Define the mandatory and optional fields for each event type
- Define severity and criticality classification rules for each event type
- Define propagation rules (which event types trigger which downstream events)
- Define governance policies (retention, audit level, sensitivity) per event type
- Define detection triggers for each event type
- Provide event type lookup and validation services to all other components

**Event type definition attributes:**

| Attribute | Description |
|---|---|
| type_name | Canonical event type identifier |
| category | Layer (Market, Corporate, Economic, etc.) |
| description | Human-readable description |
| severity | Default severity level (1–5) |
| criticality | CRITICAL / HIGH / MEDIUM / LOW |
| detection_mode | REAL_TIME / SCHEDULED / DERIVED / COMPOSITE |
| schema | Mandatory and optional fields with types |
| trigger_rules | Conditions that generate this event |
| propagation_rules | Downstream events this event triggers |
| governance_policy | Retention, audit level, sensitivity |
| freshness_sla | Maximum acceptable detection-to-registration latency |
| version | Catalog schema version |

**Inputs:** Schema update requests from Governance Manager; type lookup requests from all components

**Outputs:** Event type definitions; allowed type list; governance policies

**Dependencies:** Governance Manager (for policy updates)

**Failure Handling:** Static read — failure modes are persistence-layer failures only. Catalog is cached in memory; read failures fall through to local cache. Never fails on type lookup.

---

### 3.4 Component 3: Event Factory

**Purpose:** The Event Factory is the sole authorised creator of event records in the IIOS. Every event — regardless of source — must be created by the Factory.

**Responsibilities:**
- Accept raw event signals (from Detector, external feeds, internal agents)
- Look up the matching event type in the Catalog
- Validate the raw signal against the type schema
- Enrich the event record with context (regime, portfolio state, active strategies)
- Compute initial severity and confidence scores
- Produce a validated event record draft for the Registry
- Enforce idempotency (deduplicate signals received multiple times)

**Event Record Structure:**

| Field | Type | Description |
|---|---|---|
| event_id | UUID4 | Assigned by Registry after creation |
| event_type | string | Catalog event type name |
| category | string | Event category (Layer 1–15) |
| timestamp | UTC datetime | Precise occurrence time |
| detection_time | UTC datetime | Time of detection (may differ from occurrence) |
| source | string | System component or external feed that originated the event |
| severity | integer 1–5 | Operational severity |
| criticality | enum | CRITICAL / HIGH / MEDIUM / LOW |
| confidence | float [0,1] | System's certainty in this event |
| payload | object | Event-type-specific data |
| context | object | IIOS state at event time (regime, risk level, etc.) |
| parent_event_id | UUID4 | For derived events — the triggering event |
| correlation_group | string | For correlated events — the group identifier |
| lifecycle_state | enum | DETECTED / REGISTERED / PROCESSING / CONSUMED / ARCHIVED |
| version | integer | Event record version (always starts at 1) |
| immutable_hash | string | SHA-256 hash of the event record (tamper detection) |

**Inputs:** Raw event signals from Detector; direct event creation requests from internal components

**Outputs:** Validated event record (draft) → Registry

**Dependencies:** Catalog; Identity Manager; Context Builder (for event context enrichment)

**Failure Handling:**
- On unknown event type: log with WARN; create a GENERIC_EVENT record; alert Governance Manager
- On schema validation failure: FAIL_FAST; reject; return error to caller with field-level details
- On duplicate signal: return existing event_id; log as INFO

---

### 3.5 Component 4: Event Detector

**Purpose:** The Event Detector monitors all data sources and internal state for conditions that indicate an event has occurred or is about to occur. It is the event engine's sensory layer.

**Responsibilities:**
- Continuously monitor market data feeds for price, volume, and volatility triggers
- Monitor internal system state (risk levels, portfolio state, agent decisions)
- Evaluate trigger rules from the Catalog for each monitored data source
- Generate event signals when trigger conditions are met
- Detect composite events by matching multi-condition patterns
- Detect scheduled events based on the economic calendar
- Detect anomalies that may indicate unclassified events
- Route detected signals to the Ingestion Manager

**Detection modes:**

| Mode | Description | Examples |
|---|---|---|
| Threshold | Single measurement crosses a predefined threshold | VIX > 30, Price crosses MA |
| Pattern | A sequence of measurements matches a defined pattern | Head-and-shoulders, three consecutive lower highs |
| Scheduled | A calendar-based trigger fires at a predefined time | Economic data release, market open |
| Composite | Multiple simultaneous conditions all met | Crash pattern: price down >3% + volume spike + breadth collapse |
| Anomaly | Statistical outlier detected in monitored data | Price move > 5σ from mean |
| Cascade | A prior event triggers detection of related events | Regime change triggers sector rotation detection |

**Trigger evaluation latency targets:**

| Event category | Maximum detection latency |
|---|---|
| Market Events (price/volume) | < 100 ms |
| Risk Events (limit breach) | < 200 ms |
| Trading Events (order/fill) | < 50 ms |
| System Events | < 500 ms |
| Economic Events (data release) | < 2 seconds |
| Derived Events | < 1 second after trigger |

**Inputs:** Market data feeds; broker callbacks; internal component state updates; economic calendar

**Outputs:** Event signals → Ingestion Manager

**Dependencies:** Data Feed Manager; Catalog (trigger rules); Market Monitor; Risk Guardian

**Failure Handling:**
- On feed failure: continue monitoring available feeds; log feed failure as FEED_DISCONNECTED system event; alert
- On trigger evaluation error: log; skip trigger; do not generate false event
- On capacity overload: buffer signals; priority-order processing (higher severity first)

---

### 3.6 Component 5: Event Ingestion Manager

**Purpose:** The Event Ingestion Manager is the entry point for all event signals entering the Event Engine. It normalises, deduplicates, and routes signals to the appropriate processing components.

**Responsibilities:**
- Receive event signals from Detector, external feeds, and internal components
- Normalise signal format to IIOS standard event signal schema
- Deduplicate signals (same event from multiple sources arrives once)
- Rate-limit inbound signals to prevent processing overload
- Route signals to the Factory based on detected event type
- Buffer signals during processing backpressure
- Track signal processing time (detection-to-registration latency)

**Ingestion pipeline:**

```
Raw Signal
    │
    ▼
Normalisation (format standardisation)
    │
    ▼
Deduplication check (idempotency key)
    │
    ├── [duplicate] → discard; return existing event_id
    │
    ▼
Rate limit check
    │
    ├── [over limit] → buffer with priority queue
    │
    ▼
Type detection (preliminary Catalog lookup)
    │
    ▼
Route to Factory
```

**Inputs:** Raw event signals from all sources

**Outputs:** Normalised event signals → Factory

**Dependencies:** Detector; Catalog; Factory

**Failure Handling:**
- On normalisation failure: log; route to DEAD_LETTER queue; alert Governance Manager
- On rate limit exceeded: buffer with priority queue (severity 5 events bypass rate limit always)
- On dead letter accumulation: alert if dead letter queue exceeds 100 events

---

### 3.7 Component 6: Event Classification Engine

**Purpose:** The Classification Engine determines the definitive type, severity, criticality, and analytical classification of every event passing through the Event Engine.

**Responsibilities:**
- Assign or confirm the event type from the Catalog
- Classify event severity (1–5) based on type rules and payload
- Classify event criticality (CRITICAL / HIGH / MEDIUM / LOW)
- Determine if the event is a primary, derived, or composite event
- Assign event category (Layer 1–15)
- Assign temporal class (REAL_TIME, SCHEDULED, DELAYED, HISTORICAL)
- Detect composite events by matching multi-event patterns
- Apply machine-learned classification for novel or ambiguous events

**Classification decision table:**

| Input condition | Classification |
|---|---|
| Known event type, payload matches schema | Primary classification: confirmed |
| Known event type, payload incomplete | Primary classification: flagged for validation |
| Unknown event type, high confidence analogue | Derived classification: nearest type |
| Unknown event type, no analogue | UNCLASSIFIED_EVENT type assigned |
| Composite pattern matched | Composite event created; source events linked |
| Event received with 5+ min delay | Classified as DELAYED_EVENT |

**Inputs:** Event record from Factory; event classification request

**Outputs:** Classified event record with type, severity, criticality, category

**Dependencies:** Catalog; ML classification models (for novel events)

**Failure Handling:**
- On classification failure: assign UNCLASSIFIED_EVENT; log; alert Governance Manager
- On ML model unavailable: fall back to rule-based classification
- On composite detection timeout: release partial composite; generate COMPOSITE_DETECTION_TIMEOUT event

---

### 3.8 Component 7: Event Validator

**Purpose:** The Event Validator ensures that every event record is structurally correct, semantically valid, and contextually coherent before it is registered as a permanent event.

**Responsibilities:**
- Validate mandatory field presence for the event's type
- Validate field types, ranges, and formats
- Validate timestamp logical consistency (timestamp ≤ detection_time)
- Validate that referenced entities (source, target entities) exist in the Entity Registry
- Validate severity and criticality assignments against type rules
- Validate confidence score is in [0.0, 1.0]
- Validate payload against the Catalog type schema
- Generate ValidationResult with pass/fail and field-level details

**Validation layers:**

| Layer | Checks | Required |
|---|---|---|
| Structural | All mandatory fields present, correct types | Always |
| Semantic | Severity and criticality match type rules; confidence in range | Always |
| Referential | Referenced entities exist and are ACTIVE | Always |
| Temporal | Timestamp is logically consistent | Always |
| Contextual | Event context is coherent with current system state | Advisory |
| Duplicate | Event is not a duplicate of a recently registered event | Always |

**Inputs:** Event record from Factory or Classification Engine

**Outputs:** Validation result (PASS / FAIL with details)

**Dependencies:** Catalog; Entity Registry; Identity Manager

**Failure Handling:**
- On referential failure (entity not found): FAIL validation; return EntityNotFound error
- On structural failure: FAIL_FAST; return field-level error list
- On contextual advisory failure: PASS with WARN flag; log advisory

---

### 3.9 Component 8: Event Identity Manager

**Purpose:** The Event Identity Manager maintains the identity of every event in the IIOS and provides identity resolution services for all identifier types.

**Responsibilities:**
- Generate and assign canonical event_id (UUID4) at registration
- Assign human-readable Reference ID (format: EVT-{CATEGORY}-{YYYYMMDD}-{SEQUENCE})
- Maintain alias registry (external IDs, broker reference IDs, feed IDs)
- Resolve any valid identifier to the canonical event_id
- Detect and prevent identity collision
- Track event_id ownership (which component created the event)
- Support parent_event_id resolution for derived events

**Reference ID format:**

| Component | Example |
|---|---|
| Category | MKT (Market), TRD (Trading), RSK (Risk), AI, SYS (System), etc. |
| Date | YYYYMMDD |
| Sequence | 6-digit zero-padded sequence number per category per day |
| Full example | EVT-MKT-20260615-000342 |

**Inputs:** Registration request; identity lookup request; alias registration request

**Outputs:** Assigned event_id; resolved canonical_id; Reference ID

**Dependencies:** Registry (for collision detection)

**Failure Handling:**
- On UUID collision (astronomically rare): regenerate; log; do not fail
- On alias conflict: FAIL; return AliasConflict error; existing alias takes precedence

---

### 3.10 Component 9: Event Metadata Manager

**Purpose:** The Event Metadata Manager manages the rich metadata associated with every event — beyond the core event record fields — including analytical annotations, governance tags, and system metadata.

**Responsibilities:**
- Store and retrieve extended metadata for any event_id
- Accept metadata updates from analytical components (correlation annotations, propagation chains)
- Manage governance metadata (owner, sensitivity, retention policy)
- Track processing metadata (which components have processed this event)
- Track learning metadata (which strategies and agents have consumed this event)
- Maintain tag index for faceted search

**Metadata categories:**

| Category | Examples |
|---|---|
| Analytical | correlation_group, propagation_depth, influence_chain, root_cause_id |
| Governance | owner_id, sensitivity, retention_policy, compliance_flags |
| Processing | ingestion_time, classification_time, propagation_time, queue_time |
| Learning | consumed_by_strategies, consumed_by_agents, learning_signal_generated |
| Search | tags, keywords, natural_language_summary |

**Inputs:** Metadata write requests from any component; metadata read requests

**Outputs:** Metadata records; tag index entries

**Dependencies:** Registry (for event_id validation); Audit Manager

**Failure Handling:** FAIL_SAFE on read failures (return partial metadata); FAIL_FAST on write to critical metadata fields (governance, sensitivity)

---

### 3.11 Component 10: Event Correlation Engine

**Purpose:** The Correlation Engine identifies and records relationships between events — detecting patterns, clusters, and causal relationships across the event stream.

**Responsibilities:**
- Detect temporal correlation between events occurring close in time
- Detect semantic correlation between events of related types
- Detect causal correlation between events using causal inference
- Group correlated events into correlation groups with shared identifiers
- Compute cross-market correlations (e.g., VIX events correlating with NIFTY decline events)
- Detect recurring event patterns and update the pattern catalog
- Publish correlation signals to the Knowledge Engine for hypothesis generation

**Correlation types:**

| Type | Description | Example |
|---|---|---|
| Temporal | Events occur within a defined time window | GDP_RELEASED followed by REGIME_TRANSITION within 2 hours |
| Semantic | Events are of related types and share entities | Multiple EARNINGS_SURPRISE_NEGATIVE events for same sector |
| Causal | One event is identified as a cause of another | RATE_HIKE → BOND_YIELD_RISE → EQUITY_SELLOFF |
| Cross-market | Events in different markets correlate | US_FED_HIKE → INR_DEPRECIATION → IT_SECTOR_BOOST |
| Clustering | Events cluster around a common driver | Five sector events all driven by same macro announcement |

**Inputs:** Event stream from Registry; correlation configuration from Catalog

**Outputs:** Correlation group records; causal chain annotations; pattern signals

**Dependencies:** Registry; Catalog; Relationship Engine (for causal chain storage); Knowledge Engine

**Failure Handling:** FAIL_SAFE — correlation is advisory; no correlation result does not block event processing

---

### 3.12 Component 11: Event Propagation Engine

**Purpose:** The Propagation Engine manages the downstream effects of events — generating derived events, triggering state changes, and notifying consuming components.

**Responsibilities:**
- Evaluate propagation rules from the Catalog for every processed event
- Generate derived events based on propagation rules
- Notify consuming components of events via a publish/subscribe model
- Track propagation chains (event → derived event → further derived events)
- Enforce propagation depth limits (maximum 15 levels)
- Detect and prevent propagation loops
- Compute propagation latency metrics

**Propagation model:**

```
Primary Event (e.g., RATE_HIKE)
    │
    ├──[Propagation Rule: triggers]──► BOND_YIELD_RISE (derived)
    │       │
    │       └──[Propagation Rule: triggers]──► EQUITY_SECTOR_ROTATION (derived)
    │               │
    │               └──[Propagation Rule: triggers]──► PORTFOLIO_REBALANCE_SIGNAL (derived)
    │
    ├──[Propagation Rule: triggers]──► CURRENCY_DEPRECIATION (derived)
    │
    └──[Propagation Rule: triggers]──► REAL_ESTATE_SECTOR_IMPACT (derived)
```

**Propagation priority ordering:**
- Severity 5 derived events are generated and dispatched before severity 4, and so on
- Within the same severity, propagation order follows the Catalog-defined propagation sequence

**Inputs:** Registered events from Registry; propagation rules from Catalog

**Outputs:** Derived event signals → Ingestion Manager; propagation chain records → Metadata Manager

**Dependencies:** Registry; Catalog; Ingestion Manager; Metadata Manager

**Failure Handling:**
- On propagation loop detected: terminate chain; log PROPAGATION_LOOP_DETECTED event; alert
- On propagation depth limit (15): terminate; log PROPAGATION_DEPTH_EXCEEDED event
- On derived event creation failure: log; do not retry in same cycle; re-evaluate in next cycle

---
### 3.13 Component 12: Event Dependency Engine

**Purpose:** The Dependency Engine models and enforces the ordering and dependency constraints between events — ensuring that dependent events are not processed before their prerequisite events.

**Responsibilities:**
- Model event dependency relationships (Event A must occur before Event B can be processed)
- Enforce dependency-based processing order in the Queue Manager
- Detect missing prerequisite events and issue MISSING_PREREQUISITE alerts
- Track dependency chains for causal analysis
- Define and enforce "event gates" — conditions that must be satisfied before certain events are acted upon
- Resolve circular dependencies (detect and break)

**Dependency types:**

| Type | Description | Example |
|---|---|---|
| Temporal dependency | Event B can only be processed after Event A occurs | ORDER_FILLED cannot occur before ORDER_SUBMITTED |
| Causal dependency | Event B is only valid if Event A occurred | POSITION_CLOSED requires POSITION_OPENED |
| Logical dependency | Event B requires Event A to have completed processing | PORTFOLIO_REBALANCED requires all constituent POSITION events processed |
| Gate dependency | Event B processing is gated by a system state condition | STRATEGY_SELECTED requires REGIME_CONFIRMED |

**Inputs:** Event records; dependency rules from Catalog; processing completion signals from Queue Manager

**Outputs:** Dependency satisfaction signals; MISSING_PREREQUISITE events; dependency chain records

**Dependencies:** Registry; Catalog; Queue Manager; Timeline Manager

**Failure Handling:**
- On circular dependency detected: break the weakest dependency link; log; alert Governance Manager
- On missing prerequisite (timeout): generate MISSING_PREREQUISITE event; allow downstream processing with DEGRADED flag

---

### 3.14 Component 13: Event Priority Manager

**Purpose:** The Priority Manager maintains the processing priority of every event in the queue and ensures that the most important events are always processed first.

**Responsibilities:**
- Assign initial priority score to every new event
- Update priority scores dynamically based on system state (e.g., elevate risk events during high-volatility periods)
- Maintain the priority ordering of the event queue
- Implement priority aging (old unprocessed events increase in priority)
- Enforce priority lanes (CRITICAL events always in the fast lane)
- Prevent low-priority event starvation through aging mechanism

**Priority score formula:**

$$\text{priority} = (\text{severity} \times 20) + (\text{criticality\_weight} \times 15) + \text{age\_bonus} + \text{system\_state\_modifier}$$

Where:
- `severity` is 1–5 (TRACE to CRITICAL)
- `criticality_weight` is 0.5 (LOW), 1.0 (MEDIUM), 1.5 (HIGH), 2.0 (CRITICAL)
- `age_bonus` is seconds_in_queue / 10 (prevents starvation)
- `system_state_modifier` is +25 during kill switch activation, +15 during risk alerts

**Priority lanes:**

| Lane | Priority range | Processing SLA | Examples |
|---|---|---|---|
| EMERGENCY | 150+ | < 50 ms | Kill switch, system failure, limit breach CRITICAL |
| HIGH | 100–149 | < 200 ms | Severity 4–5 events, risk limit approach |
| STANDARD | 50–99 | < 1 second | Normal trading events, AI decisions |
| BACKGROUND | 0–49 | < 30 seconds | Learning events, analytics, archival |

**Inputs:** New event registrations; system state updates; queue depth signals

**Outputs:** Priority scores; priority ordering directives to Queue Manager

**Dependencies:** Registry; Queue Manager; System Monitor

**Failure Handling:**
- On priority calculation error: assign default priority based on severity alone; log
- On priority inversion detected (lower-severity event ahead of higher): emergency reordering

---

### 3.15 Component 14: Event Queue Manager

**Purpose:** The Queue Manager is the Event Engine's central work scheduler — it manages the ordered queue of events awaiting processing and routes events to the appropriate consumers.

**Responsibilities:**
- Maintain the priority-ordered event processing queue
- Route events to registered consumers based on subscription rules
- Implement publish/subscribe event distribution
- Manage multiple queues (real-time, scheduled, background, dead letter)
- Handle consumer backpressure (slow consumers)
- Implement at-least-once delivery semantics
- Track queue depth and processing latency per queue

**Queue architecture:**

```
Event Stream
    │
    ├──► EMERGENCY Queue ──► Real-time consumers (Risk Guardian, Kill Switch)
    │     (severity 5, CRITICAL)
    │
    ├──► HIGH Priority Queue ──► Strategy consumers, Risk consumers
    │     (severity 4-5, HIGH criticality)
    │
    ├──► STANDARD Queue ──► General consumers (agents, learning, analytics)
    │     (severity 2-3)
    │
    ├──► SCHEDULED Queue ──► Batch consumers (EOD processes, daily learning)
    │     (calendar-triggered)
    │
    └──► DEAD LETTER Queue ──► Governance Manager (failed processing events)
          (failed events)
```

**Consumer subscription model:**
Each consumer registers with the Queue Manager specifying:
- Event types it subscribes to (or wildcard for all)
- Maximum severity it can handle
- Processing capacity (events per second)
- Delivery mode (push or pull)

**Inputs:** Registered events from Registry; priority scores from Priority Manager; consumer subscriptions

**Outputs:** Events delivered to registered consumers; dead letter events to Governance Manager

**Dependencies:** Registry; Priority Manager; Dependency Engine; all consuming components

**Failure Handling:**
- On consumer failure: retry delivery up to 3 times with exponential backoff; then route to dead letter
- On queue overflow: apply backpressure to Ingestion Manager; drop only TRACE-severity background events
- On dead letter overflow: immediate alert to Human Principal

---

### 3.16 Component 15: Event Timeline Manager

**Purpose:** The Timeline Manager maintains the temporal order of all events in the IIOS and provides temporal query services — enabling point-in-time reconstruction of system state and event history.

**Responsibilities:**
- Maintain a chronologically ordered event timeline index
- Support temporal range queries (events in time window)
- Support point-in-time queries (system state at a specific moment)
- Maintain per-entity timelines (all events involving a specific entity)
- Maintain per-type timelines (all events of a specific type)
- Detect temporal anomalies (events with timestamps out of sequence)
- Support "replay" operations (re-processing of historical event sequences)
- Calculate inter-event timing (time between related events)

**Timeline index structure:**

```
Global Timeline (chronological order, all events)
    │
    ├── Entity Timelines (per entity — all events touching this entity)
    │
    ├── Type Timelines (per event type — all instances)
    │
    ├── Category Timelines (per layer — market events, risk events, etc.)
    │
    ├── Correlation Group Timelines (correlated event sequences)
    │
    └── Chain Timelines (event chains — causally linked sequences)
```

**Temporal query examples:**

| Query | Description |
|---|---|
| All events between T1 and T2 | Time range query on global timeline |
| All market events on 2026-06-15 | Type + date query on type timeline |
| All events involving TATASTEEL.NS | Entity timeline query |
| System state at 14:37:22 | Point-in-time reconstruction |
| Events within 5 minutes of RATE_HIKE event | Relative time query |

**Inputs:** Event registrations (chronological stream); temporal query requests

**Outputs:** Ordered event sequences; timeline index entries; temporal query results

**Dependencies:** Registry; Index (for fast temporal lookup)

**Failure Handling:**
- On timestamp anomaly (future timestamp): log; record with current timestamp as registration time; preserve original timestamp as payload field
- On out-of-order event: insert into correct timeline position; log reordering event

---

### 3.17 Component 16: Event Lifecycle Manager

**Purpose:** The Lifecycle Manager governs the complete lifecycle of every event record — from detection through archival and retirement.

**Responsibilities:**
- Enforce the event lifecycle state machine
- Manage lifecycle transitions for all event records
- Generate lifecycle transition events (every transition is itself an event)
- Enforce lifecycle-dependent access rules (e.g., archived events are read-only)
- Coordinate cascade lifecycle changes (when a parent event is archived, derived children are also archived)
- Track lifecycle state for all events in the Registry

**Event lifecycle states:**

| State | Description | Access |
|---|---|---|
| DETECTED | Signal received, not yet registered | Not in Registry |
| REGISTERED | event_id assigned, record in Registry | Read-write |
| PROCESSING | Currently being processed by one or more consumers | Read-only during processing |
| CONSUMED | All registered consumers have processed this event | Read-only |
| SUPERSEDED | Replaced by a correction or more accurate event | Read-only |
| ARCHIVED | Moved to archive tier; no longer in hot storage | Read-only (archive tier) |
| RETIRED | Permanently retired; accessible only via audit | Read-only (audit tier) |

**Lifecycle state machine:**

```
DETECTED → REGISTERED → PROCESSING → CONSUMED → ARCHIVED → RETIRED
                │                        │
                └──[validation fail]──► SUPERSEDED
```

**Inputs:** Lifecycle transition requests from all components; archive schedule from Archive Manager

**Outputs:** Lifecycle state updates; lifecycle transition events; cascade archive instructions

**Dependencies:** Registry; Audit Manager; Archive Manager

**Failure Handling:**
- On invalid transition: FAIL_FAST; reject; log; return LifecycleError
- On cascade archive failure: retry; if persistent failure, alert Governance Manager

---

### 3.18 Component 17: Event Audit Manager

**Purpose:** The Audit Manager creates and maintains the immutable, hash-chained audit trail for all events in the IIOS.

**Responsibilities:**
- Generate an audit record for every event lifecycle transition
- Hash-chain all audit records for tamper detection
- Store audit records in the immutable audit tier
- Provide audit record retrieval by event_id
- Run periodic audit chain integrity verification
- Enforce audit retention policies per event category
- Alert on audit chain breaks

**Audit events generated:**

| Trigger | Audit event type |
|---|---|
| Event registered | EVENT_REGISTERED |
| Event processed by consumer | EVENT_CONSUMED |
| Event lifecycle transition | LIFECYCLE_TRANSITION |
| Event severity changed | SEVERITY_CHANGED |
| Event confidence changed | CONFIDENCE_CHANGED |
| Event archived | EVENT_ARCHIVED |
| Event superseded | EVENT_SUPERSEDED |
| Correlation assigned | CORRELATION_ASSIGNED |
| Propagation triggered | PROPAGATION_TRIGGERED |

**Inputs:** Lifecycle transitions from Lifecycle Manager; processing completions from Queue Manager; all component state changes

**Outputs:** Audit records; integrity check results; tamper alerts

**Dependencies:** Persistence Layer (audit tier); Governance Manager

**Failure Handling:** NEVER_FAIL — audit writes are queued with persistent retry; audit queue is drained before system shutdown

---

### 3.19 Component 18: Event Governance Manager

**Purpose:** The Governance Manager enforces all governance policies across the Event Engine — ownership, sensitivity classification, compliance monitoring, and violation management.

**Responsibilities:**
- Assign governance policy to every new event based on type rules
- Assign event ownership
- Monitor compliance with retention, audit, and sensitivity policies
- Detect governance violations and generate GOVERNANCE_VIOLATION events
- Maintain the governance health report
- Manage the Governance Policy Catalog
- Escalate violations to the appropriate authority

**Governance policy elements per event:**

| Element | Description |
|---|---|
| owner_id | Component or agent responsible for this event |
| sensitivity | PUBLIC / INTERNAL / CONFIDENTIAL / RESTRICTED |
| retention_policy | Retention duration by category |
| audit_level | FULL / STANDARD / MINIMAL |
| compliance_schedule | Frequency of compliance checks |

**Inputs:** New event registrations; governance policy catalog; compliance check results

**Outputs:** Governance policy assignments; GOVERNANCE_VIOLATION events; monthly governance report

**Dependencies:** Catalog; Audit Manager; Notification System

**Failure Handling:**
- On governance violation (CRITICAL): immediate Telegram notification; Human Principal review required
- On missing governance policy for event type: assign default policy; log WARNING; alert Governance Manager

---

### 3.20 Component 19: Event Search Engine

**Purpose:** The Search Engine provides efficient discovery and retrieval of events across all dimensions — type, entity, time range, severity, content, and metadata.

**Responsibilities:**
- Maintain a searchable index of all events
- Support full-text search across event payloads and metadata
- Support structured queries (event type, time range, severity, entity)
- Support semantic search (events similar to a given context)
- Provide ranked results with relevance scoring
- Maintain search index consistency with the Registry
- Support faceted search (filter by type, category, severity simultaneously)

**Search dimensions:**

| Dimension | Example query |
|---|---|
| Type | All PRICE_THRESHOLD_CROSSED events |
| Entity | All events involving TATASTEEL.NS |
| Time | All events on 2026-06-15 between 09:15 and 15:30 |
| Severity | All CRITICAL and HIGH events this week |
| Source | All events from DataFeedManager |
| Content | Events with payload containing "regime_change" |
| Correlation | All events in correlation group CG-20260615-0042 |

**Performance targets:**

| Query type | Latency target |
|---|---|
| Exact event_id lookup | < 1 ms |
| Time range (< 1 day) | < 50 ms |
| Entity timeline (< 30 days) | < 100 ms |
| Full-text search | < 500 ms |
| Semantic similarity search | < 1 second |

**Inputs:** Search queries; new event registrations (index updates)

**Outputs:** Ranked event result lists; faceted search results

**Dependencies:** Registry; Metadata Manager; Timeline Manager

**Failure Handling:** FAIL_SAFE — return partial results on index failure; log index gap

---

### 3.21 Component 20: Event Analytics Manager

**Purpose:** The Analytics Manager computes aggregate analytics, metrics, and intelligence reports from the event stream.

**Responsibilities:**
- Compute event frequency distributions by type and category
- Compute event severity distributions and trends
- Compute event chain statistics (average chain length, average propagation depth)
- Track event-to-decision latency (event occurrence to system action)
- Compute correlation statistics across event categories
- Generate session analytics reports (per trading session)
- Generate daily and weekly analytics summaries
- Provide real-time analytics dashboards

**Key analytics metrics:**

| Metric | Description |
|---|---|
| Event Rate | Events per second / per minute / per session |
| Severity Distribution | % of events at each severity level |
| Detection Latency | Average and P99 detection-to-registration latency |
| Propagation Depth | Average derived event chain depth |
| Correlation Rate | % of events belonging to a correlation group |
| Decision Impact | % of events that triggered a system action |
| Novelty Rate | % of events classified as novel (no prior match) |

**Inputs:** Event stream; analytics configuration; schedule

**Outputs:** Analytics reports; real-time metrics; dashboard data

**Dependencies:** Registry; Timeline Manager; Search Engine

**Failure Handling:** FAIL_SAFE — analytics are advisory; failures do not block event processing

---

### 3.22 Component 21: Event Archive Manager

**Purpose:** The Archive Manager manages the retention lifecycle of events — moving events from hot storage to warm and cold storage tiers according to retention policies.

**Responsibilities:**
- Monitor event ages against retention policies
- Execute tiered archival: hot → warm → cold → permanent
- Compress archived events to reduce storage footprint
- Maintain archive index for historical retrieval
- Enforce deletion (where permitted) after retention expiry
- Restore archived events to hot storage on demand
- Generate archival activity reports

**Storage tiers:**

| Tier | Storage type | Latency | Retention |
|---|---|---|---|
| HOT | In-memory + fast SSD | < 1 ms | Last 7 days |
| WARM | SSD | < 10 ms | Last 90 days |
| COLD | Compressed disk | < 500 ms | Per retention policy |
| PERMANENT | Compliance archive | < 5 seconds | Forever (Critical, Financial) |

**Archival schedule:**

| Event category | HOT → WARM | WARM → COLD | COLD → PERMANENT or expire |
|---|---|---|---|
| Market Events | After 7 days | After 90 days | Expire after 1 year |
| Trading Events | After 30 days | After 1 year | Permanent (financial) |
| Risk Events | After 30 days | After 1 year | Permanent |
| AI Events | After 7 days | After 90 days | Expire after 2 years |
| System Events | After 3 days | After 30 days | Expire after 1 year |

**Inputs:** Archive schedule from Governance Manager; retention policies from Catalog; archival requests

**Outputs:** Archived event records; archive index; archival reports

**Dependencies:** Registry; Governance Manager; Lifecycle Manager; Persistence Layer

**Failure Handling:**
- On archive write failure: retain in current tier; retry; alert if unresolved after 24 hours
- On retention enforcement failure: log; defer deletion; escalate

---

### 3.23 Component 22: Event Evolution Manager

**Purpose:** The Evolution Manager monitors how event patterns change over time and updates the Event Catalog's detection rules, classification rules, and propagation rules to reflect evolving market and system behaviour.

**Responsibilities:**
- Analyse historical event patterns for drift (events that used to be predictive are no longer)
- Detect novel event types that do not fit existing Catalog definitions
- Propose Catalog updates for new event types and rule changes
- Monitor detection effectiveness (events that should have been detected but were not)
- Monitor classification accuracy (events that were misclassified)
- Track event confidence calibration (are confidence scores accurate?)
- Feed evolution signals to the Learning System

**Evolution signals:**

| Signal | Description |
|---|---|
| DETECTION_MISS | An event occurred but was not detected |
| CLASSIFICATION_ERROR | An event was classified incorrectly |
| PROPAGATION_MISS | An expected derived event was not generated |
| CONFIDENCE_MISCALIBRATION | Confidence scores are systematically too high or too low |
| NEW_PATTERN_DETECTED | A novel event pattern with no catalog equivalent |
| RULE_DECAY | An existing detection rule has decreasing effectiveness |

**Inputs:** Event analytics from Analytics Manager; learning feedback from Learning System; human feedback

**Outputs:** Evolution signals → Learning System; Catalog update proposals → Governance Manager

**Dependencies:** Analytics Manager; Catalog; Learning System; Governance Manager

**Failure Handling:** FAIL_SAFE — evolution is advisory; evolution failures do not affect live event processing

---
## PART IV — EVENT LIFECYCLE

### 4.1 Lifecycle Philosophy

The event lifecycle defines the complete journey of an event from its first detection to its final archival or retirement. Understanding the lifecycle is critical because different lifecycle states have different access rules, different processing expectations, and different governance requirements.

Unlike entity or relationship lifecycles (which are primarily about the persistence of a stable thing), the event lifecycle is about the management of a timestamped occurrence. Events are inherently ephemeral in their operational impact — but their records must be permanent.

---

### 4.2 Complete Lifecycle: 13 Stages

**Stage 1: DETECTION**

The event begins when the Event Detector identifies a condition that matches a trigger rule, or when an external signal arrives at the Ingestion Manager. At this stage, no event record exists in the Registry. The event exists only as a signal — a raw measurement or notification.

Detection is the most latency-sensitive stage. Missing detection means missing the event entirely. Detection quality is measured by detection rate (events detected / events that occurred) and detection latency (time from event occurrence to signal generation).

**Lifecycle state:** Not yet assigned  
**Record existence:** Signal only — no Registry record  
**Access:** None (not yet in system)  
**Transition trigger:** Signal arrives at Ingestion Manager

---

**Stage 2: DISCOVERY (Composite and Derived Events)**

For composite events and derived events, there is an intermediate discovery stage where the system determines whether multiple signals together constitute a single composite event, or whether a primary event implies a derived secondary event.

During Discovery, the Classification Engine matches multi-signal patterns against the Catalog's composite event definitions. A MARKET_CRASH_DETECTED composite event, for example, requires simultaneous detection of a price decline event, a volume spike event, and a breadth collapse event within a defined time window. Discovery is complete when the composite is confirmed or rejected.

**Lifecycle state:** DISCOVERY_CANDIDATE  
**Record existence:** Candidate record (no event_id; not in Registry)  
**Access:** Classification Engine only  
**Transition trigger:** Composite confirmed (→ Stage 3) or rejected (discarded)

---

**Stage 3: CREATION**

The Factory creates the event record, enriching the raw signal with:
- Contextual information (current regime, portfolio state, risk level)
- Initial severity and criticality classification
- Initial confidence score
- Lineage information (parent event for derived events)
- Correlation group assignment (if part of a correlated event cluster)
- Immutable hash for tamper detection

The created event record is a draft — it has not yet been assigned an event_id and has not been persisted to the Registry.

**Lifecycle state:** CREATED  
**Record existence:** Draft record — not yet persisted  
**Access:** Factory, Validator  
**Transition trigger:** Validator returns PASS (→ Stage 4)

---

**Stage 4: VALIDATION**

The Validator subjects the draft event record to structural, semantic, referential, and temporal checks. Validation is a mandatory gate. Events that fail validation are rejected and do not receive an event_id.

The Validator checks:
- All mandatory fields are present and correctly typed
- Severity and criticality are within allowed ranges for the event type
- Referenced entities exist and are in ACTIVE lifecycle state
- Timestamp is logically consistent
- Confidence is in [0.0, 1.0]
- The event is not a duplicate of a recently registered event

Failed validation generates a VALIDATION_REJECTED event (recorded separately) with the specific failure reasons.

**Lifecycle state:** VALIDATING  
**Record existence:** Draft — not yet persisted  
**Access:** Validator, Factory  
**Transition trigger:** Validation PASS (→ Stage 5) or FAIL (draft discarded; VALIDATION_REJECTED recorded)

---

**Stage 5: CLASSIFICATION**

Post-validation, the Classification Engine performs definitive type, severity, criticality, and category classification. For well-known event types from authoritative sources (e.g., ORDER_FILLED from the broker), classification is trivial confirmation. For derived or novel events, classification may involve ML-based type matching.

Classification produces:
- Confirmed event type (or UNCLASSIFIED_EVENT)
- Final severity (1–5)
- Final criticality (CRITICAL / HIGH / MEDIUM / LOW)
- Category (Layer 1–15)
- Temporal class (REAL_TIME / SCHEDULED / DELAYED / HISTORICAL)
- Primary / Derived / Composite classification

**Lifecycle state:** CLASSIFYING  
**Record existence:** Draft — enhanced with classification  
**Access:** Classification Engine  
**Transition trigger:** Classification complete (→ Stage 6)

---

**Stage 6: PRIORITISATION**

The Priority Manager assigns a priority score to the event based on severity, criticality, system state, and age. The priority score determines the event's position in the processing queue.

Priority assignment is dynamic — priority scores can increase as an event ages unprocessed (anti-starvation mechanism) or as system conditions change (a market volatility spike causes all unprocessed risk events to have their priority elevated).

**Lifecycle state:** PRIORITISING  
**Record existence:** Draft — with priority score assigned  
**Access:** Priority Manager  
**Transition trigger:** Priority assigned (→ Stage 7)

---

**Stage 7: REGISTRATION**

The Registry assigns a canonical event_id (UUID4) and Reference ID, persists the event record to the immutable event store, adds the event to all relevant indexes (type, entity, temporal), and confirms registration. Registration is the moment the event becomes an official, permanent record in the IIOS.

From this point, the event record is immutable — it cannot be modified. Corrections must be made by creating a new event record and marking the original as SUPERSEDED.

**Lifecycle state:** REGISTERED  
**Record existence:** Persisted in Registry — event_id assigned  
**Access:** All components (read); Lifecycle Manager (state changes)  
**Transition trigger:** Placed in Queue Manager (→ Stage 8)

---

**Stage 8: PROPAGATION**

The Propagation Engine evaluates the registered event against all applicable propagation rules. For each applicable rule, the engine generates derived event signals, which are routed back through the Ingestion Manager to begin their own lifecycle journeys.

Propagation is tracked: a propagation chain record is created linking the primary event to all its derived events. The propagation chain depth is bounded (maximum 15 levels).

**Lifecycle state:** PROPAGATING  
**Record existence:** Persisted; propagation chain being built  
**Access:** Propagation Engine; Correlation Engine  
**Transition trigger:** All propagation rules evaluated (→ Stage 9)

---

**Stage 9: CONSUMPTION**

The Queue Manager delivers the event to all registered consumers. Each consumer processes the event according to its own internal logic. The Queue Manager tracks delivery acknowledgements — an event is not considered CONSUMED until all mandatory consumers have acknowledged receipt.

Consumer types:
- Risk Engine (mandatory for CRITICAL risk events)
- Strategy Layer (mandatory for trading events)
- Learning System (mandatory for all events)
- Knowledge Engine (mandatory for knowledge events)
- Notification System (mandatory for CRITICAL and HIGH events)
- Analytics Manager (advisory — best effort)

**Lifecycle state:** PROCESSING → CONSUMED  
**Record existence:** Persisted; consumption tracked per consumer  
**Access:** All consumers (read); Lifecycle Manager (state change on full consumption)  
**Transition trigger:** All mandatory consumers acknowledged (→ Stage 10)

---

**Stage 10: RESOLUTION**

The event is resolved when all expected consequences have been addressed — the risk has been managed, the trade has been executed, the learning signal has been generated, the notification has been sent. Resolution is a logical state, not a technical one — it marks the event as "operationally complete".

Not all events have a defined resolution — some events (e.g., MARKET_OPEN) are simply consumed and complete. For incident events (KILL_SWITCH_TRIGGERED), resolution requires explicit Human Principal acknowledgement.

**Lifecycle state:** CONSUMED (RESOLVED sub-state for incidents)  
**Record existence:** Persisted  
**Access:** Audit Manager; Governance Manager  
**Transition trigger:** Operational resolution confirmed (→ Stage 11) or immediate progression for non-incident events

---

**Stage 11: HISTORICAL RECORDING**

Every event transitions to a historical recording phase where it is indexed for long-term analytical use. The Timeline Manager adds the event to all long-term timeline indexes. The Analytics Manager incorporates the event into trend analysis. The Learning System extracts learning features.

**Lifecycle state:** CONSUMED (HISTORICAL sub-state)  
**Record existence:** Persisted; indexed in all long-term indexes  
**Access:** Analytics Manager; Learning System; Timeline Manager  
**Transition trigger:** All historical indexing complete (→ Stage 12)

---

**Stage 12: LEARNING**

The Learning System processes the event for training signals. Every event contributes to at least one learning dataset:
- Market events → regime learning, correlation learning
- Trading events → strategy performance learning
- Risk events → risk model calibration
- AI events → agent calibration
- System events → operational reliability models

Learning is asynchronous and best-effort — a learning failure does not affect the event lifecycle.

**Lifecycle state:** CONSUMED (LEARNING sub-state)  
**Record existence:** Persisted  
**Access:** Learning System  
**Transition trigger:** Learning signals extracted (→ Stage 12)

---

**Stage 13: ARCHIVAL**

The Archive Manager moves the event from hot storage to the appropriate storage tier based on the retention policy for the event's category. Eventually, events may be retired to the permanent audit archive.

**Lifecycle state:** ARCHIVED → RETIRED  
**Record existence:** Archive tier; eventually permanent audit tier  
**Access:** Read-only; Archive Manager; Audit Manager  
**Transition trigger:** Retention period expiry or explicit archival instruction

---

### 4.3 Lifecycle State Machine Diagram

```
Signal arrives
    │
    ▼
[DETECTION] — Detector generates signal
    │
    ▼
[DISCOVERY_CANDIDATE] — (composite/derived only)
    │
    │ [simple event]──────────────────────────────────┐
    │                                                  │
    ▼                                                  ▼
[CREATED] — Factory creates draft record          [discarded if composite rejected]
    │
    ▼
[VALIDATING]
    │
    ├──[FAIL]──► Draft discarded; VALIDATION_REJECTED event created
    │
    ▼
[CLASSIFYING]
    │
    ▼
[PRIORITISING]
    │
    ▼
[REGISTERED] — event_id assigned; persisted; IMMUTABLE from this point
    │
    ▼
[PROPAGATING] — derived events generated
    │
    ▼
[PROCESSING] — consumers receiving and processing
    │
    ├──[consumer failure]──► retry → dead letter → alert
    │
    ▼
[CONSUMED] — all mandatory consumers acknowledged
    │
    ├──[incident]──► RESOLVED sub-state (awaits Human Principal acknowledgement)
    │
    ▼
[HISTORICAL] — timeline and analytics indexing
    │
    ▼
[LEARNING] — learning signals extracted
    │
    ▼
[ARCHIVED] — moved to warm/cold storage
    │
    ▼
[RETIRED] — permanent archive; never deleted for CRITICAL/Financial events
```

---

### 4.4 Lifecycle Event Table

| Lifecycle Stage | Events Generated | Actor |
|---|---|---|
| DETECTION | DETECTION_SIGNAL_RECEIVED | Detector |
| CREATION | EVENT_DRAFT_CREATED | Factory |
| VALIDATION | VALIDATION_PASSED / VALIDATION_REJECTED | Validator |
| CLASSIFICATION | EVENT_CLASSIFIED | Classification Engine |
| REGISTRATION | EVENT_REGISTERED | Registry |
| PROPAGATION | PROPAGATION_CHAIN_CREATED; derived signals | Propagation Engine |
| CONSUMPTION | EVENT_DELIVERED; EVENT_CONSUMED (per consumer) | Queue Manager |
| RESOLUTION | EVENT_RESOLVED / INCIDENT_ACKNOWLEDGED | Lifecycle Manager / Human Principal |
| ARCHIVAL | EVENT_ARCHIVED | Archive Manager |
| RETIREMENT | EVENT_RETIRED | Archive Manager |

---

### 4.5 Special Lifecycle Cases

**Correction (Supersession):**
When an event is discovered to have incorrect payload or classification, a correction event is created. The correction event carries the corrected data and includes a `supersedes_event_id` reference. The original event is transitioned to SUPERSEDED state (read-only). Both records are retained permanently.

```
EVENT_A (original, SUPERSEDED) ◄──[supersedes]── EVENT_B (correction, ACTIVE)
```

**Incident Resolution:**
For events classified as INCIDENT (severity 5, criticality CRITICAL), the lifecycle does not progress from CONSUMED to HISTORICAL until an explicit resolution is recorded by the Human Principal or by the system under explicit governance rules.

**Delayed Events:**
Events detected after their actual occurrence time (e.g., a news event from a delayed data source) are registered with both the actual event timestamp and the detection timestamp. They are inserted into the Timeline Manager at the correct chronological position.

---
## PART V — EVENT SERVICES

### 5.1 Services Architecture

The Event Engine exposes 15 services to consuming components across the IIOS. Services are the only authorised interface to Event Engine capabilities — no component may directly access the Registry, Catalog, or any Engine component except through a defined service interface.

---

### 5.2 Service 1: Detection Service

**Purpose:** Provides event detection capabilities to all IIOS components — enabling any component to register detection triggers and receive notifications when those triggers fire.

**Inputs:**
- Trigger registration request (condition definition, event type to generate)
- Trigger deregistration request
- Manual signal injection (for testing or Human Principal override)

**Outputs:**
- Trigger registration confirmation
- Trigger fire notification (event signal sent to Ingestion Manager)
- Trigger evaluation status report

**Consumers:** All IIOS layers (Risk Guardian, Strategy Lab, Market Intelligence, etc.)

**Dependencies:** Event Detector; Catalog; Ingestion Manager

**Failure Recovery:**
- On trigger evaluation failure: log; retain trigger; retry on next evaluation cycle
- On signal injection failure: FAIL_FAST; return error to caller; no signal sent

---

### 5.3 Service 2: Registration Service

**Purpose:** The sole authorised path for creating new event records in the IIOS. All events must be created through this service.

**Inputs:**
- Event creation request (raw signal or structured event payload)
- Source identifier (which component is requesting creation)

**Outputs:**
- Registration confirmation with assigned event_id and Reference ID
- Validation error details (on failure)
- Idempotency response (existing event_id if duplicate)

**Consumers:** Detector, Ingestion Manager, all IIOS components that produce events

**Dependencies:** Factory; Validator; Classification Engine; Registry; Identity Manager

**Failure Recovery:**
- On validation failure: return specific field-level errors; do not create record
- On Registry persistence failure: buffer; retry with exponential backoff; alert after 3 failures
- On duplicate detection: return existing event_id; log as INFO

**Processing pipeline:**

```
Registration Request
    └── Normalise → Validate → Classify → Prioritise → Register → Propagate → Confirm
```

---

### 5.4 Service 3: Validation Service

**Purpose:** Provides standalone event validation for external consumers and for pre-registration validation of event drafts.

**Inputs:**
- Event record draft (full or partial)
- Validation mode (STRICT / ADVISORY / DRAFT)

**Outputs:**
- ValidationResult: PASS / FAIL / WARN
- Field-level error details
- Advisory recommendations

**Consumers:** Factory; external feeds; integration adapters; Human Principal (for manual event submission)

**Dependencies:** Validator; Catalog; Entity Registry

**Failure Recovery:**
- On Catalog lookup failure: perform structural validation only; note Catalog unavailability in result
- On Entity Registry timeout: mark referential checks as INCONCLUSIVE; do not FAIL on timeout

---

### 5.5 Service 4: Classification Service

**Purpose:** Provides event classification — assigning type, severity, criticality, and category — as a standalone service for internal and external use.

**Inputs:**
- Unclassified or partially-classified event record
- Classification mode (AUTO / ASSISTED / MANUAL)

**Outputs:**
- Classified event record with type, severity, criticality, category
- Classification confidence score
- Candidate types (top 3) with confidence scores (for ASSISTED mode)

**Consumers:** Factory; external integration adapters; Human Principal (for manual review)

**Dependencies:** Classification Engine; Catalog; ML classification models

**Failure Recovery:**
- On ML model failure: fall back to rule-based classification
- On no-match classification: assign UNCLASSIFIED_EVENT; flag for Human Principal review

---

### 5.6 Service 5: Propagation Service

**Purpose:** Manages the propagation of events to downstream derived events and notifies consumers of propagation results.

**Inputs:**
- Registered event record
- Propagation scope request (FULL / LIMITED_DEPTH / DISABLED)

**Outputs:**
- Propagation chain record (list of derived events generated)
- Propagation depth
- Failed propagation alerts

**Consumers:** Registry (triggers propagation after registration); consuming components that need propagation chain details

**Dependencies:** Propagation Engine; Ingestion Manager; Catalog

**Failure Recovery:**
- On derived event creation failure: log; generate PROPAGATION_FAILURE event; continue with remaining propagation rules
- On loop detection: immediately terminate chain; log; generate PROPAGATION_LOOP event

---

### 5.7 Service 6: Correlation Service

**Purpose:** Provides event correlation analysis — identifying related, clustered, and causally linked events.

**Inputs:**
- Event record (or event_id for post-registration correlation)
- Correlation time window
- Correlation type request (TEMPORAL / SEMANTIC / CAUSAL / ALL)

**Outputs:**
- Correlation group assignment
- Correlation confidence score
- Correlation cluster record (all related events)
- Causal chain (for CAUSAL correlation type)

**Consumers:** Knowledge Engine; Analytics Manager; Research Lab; Human Principal (via dashboard)

**Dependencies:** Correlation Engine; Registry; Timeline Manager; Relationship Engine

**Failure Recovery:** FAIL_SAFE — correlation is advisory; correlation failure does not block event processing; returns null result with diagnostic message

---

### 5.8 Service 7: Timeline Service

**Purpose:** Provides temporal event queries and point-in-time system state reconstruction.

**Inputs:**
- Time range query (from_time, to_time, optional filters)
- Entity timeline query (entity_id, time range)
- Type timeline query (event_type, time range)
- Point-in-time query (timestamp)
- Event replay request (replay historical sequence from T1 to T2)

**Outputs:**
- Ordered event sequences
- Entity event history
- Type event history
- Point-in-time system state snapshot
- Replay event stream

**Consumers:** Analytics Manager; Research Lab; Audit Service; Human Principal (historical analysis); Validation Engine (backtesting)

**Dependencies:** Timeline Manager; Registry; Archive Manager (for historical queries beyond hot storage)

**Performance targets:**

| Query type | Target |
|---|---|
| Recent events (< 1 hour) | < 10 ms |
| Day's events (< 8 hours) | < 50 ms |
| Week's events | < 200 ms |
| Historical (> 90 days, cold storage) | < 2 seconds |
| Replay (100 events) | < 1 second |

**Failure Recovery:**
- On Archive Manager unavailability: return hot and warm tier results only; note data gap in response
- On timeline index corruption: fallback to Registry scan; log TIMELINE_INDEX_CORRUPT event

---

### 5.9 Service 8: Priority Service

**Purpose:** Provides priority management — querying, adjusting, and monitoring event processing priorities.

**Inputs:**
- Priority query (what is the priority of event X?)
- Priority adjustment request (elevate/demote event X)
- System state update (for dynamic priority recalculation)
- Queue depth report request

**Outputs:**
- Current priority score for requested event
- Queue state snapshot (depth per lane)
- Priority adjustment confirmation

**Consumers:** Queue Manager; Human Principal (emergency priority override); Governance Manager

**Dependencies:** Priority Manager; Queue Manager; System Monitor

**Failure Recovery:**
- On priority calculation failure: use severity-based fallback priority; log
- On queue overflow alert: trigger backpressure notification to Ingestion Manager

---

### 5.10 Service 9: Search Service

**Purpose:** Provides comprehensive event discovery across all search dimensions.

**Inputs:**
- Structured query (type, entity, time range, severity)
- Full-text query (keyword or phrase)
- Semantic query (contextual similarity)
- Faceted query (multiple filters combined)

**Outputs:**
- Ranked result list (event records with relevance scores)
- Facet counts (how many results per type, severity, etc.)
- Total result count
- Pagination token (for large result sets)

**Consumers:** Human Principal (dashboard); Analytics Manager; Knowledge Engine; Research Lab; Audit Service

**Dependencies:** Search Engine; Registry; Metadata Manager; Archive Manager

**Failure Recovery:** FAIL_SAFE — return partial results from available tiers; indicate storage tier coverage in response

---

### 5.11 Service 10: Analytics Service

**Purpose:** Provides event analytics, metrics, and reporting capabilities.

**Inputs:**
- Analytics query (metric name, time range, aggregation)
- Report generation request (session report, daily summary, weekly summary)
- Real-time metrics subscription request

**Outputs:**
- Aggregated metric values
- Trend analysis reports
- Session analytics summary
- Real-time metric stream (for dashboard)

**Consumers:** Control Tower (dashboard); Human Principal; Performance Analytics Layer; Governance Manager

**Dependencies:** Analytics Manager; Registry; Timeline Manager

**Performance targets:**

| Query | Target |
|---|---|
| Today's event rate | < 100 ms |
| Weekly trend | < 500 ms |
| Monthly aggregate | < 2 seconds |
| Real-time dashboard | < 1 second refresh |

**Failure Recovery:** FAIL_SAFE — analytics is advisory; return last-known values on failure; log

---

### 5.12 Service 11: Archive Service

**Purpose:** Provides archival operations — manual archiving, retrieval from archive, and archival status queries.

**Inputs:**
- Archive request (event_id or event range)
- Retrieval request (archived event_id)
- Archival status query (is event X archived?)
- Retention policy query

**Outputs:**
- Archival confirmation
- Retrieved event record
- Archival status
- Retention policy details

**Consumers:** Lifecycle Manager; Governance Manager; Audit Service; Human Principal

**Dependencies:** Archive Manager; Lifecycle Manager; Persistence Layer

**Failure Recovery:**
- On archive write failure: retain in current tier; retry; escalate if unresolved after 24 hours
- On retrieval failure: return partial record from available tier; indicate data completeness

---

### 5.13 Service 12: Governance Service

**Purpose:** Provides governance management — policy assignment, violation reporting, and compliance monitoring.

**Inputs:**
- Governance policy query (what policies apply to event X?)
- Violation report (component detected a governance issue)
- Compliance status request
- Policy update request (from Human Principal)

**Outputs:**
- Governance policy for event type or instance
- Governance health report
- Violation alerts
- Compliance status

**Consumers:** Human Principal; all components (for policy lookup); Audit Service

**Dependencies:** Governance Manager; Catalog; Notification Service

**Failure Recovery:**
- On policy lookup failure: apply default restrictive policy; log WARNING
- On violation reporting failure: buffer violation; retry; escalate if buffer exceeds 10 violations

---

### 5.14 Service 13: Audit Service

**Purpose:** Provides complete audit access — audit trail retrieval, integrity verification, and audit reporting.

**Inputs:**
- Audit trail request (event_id)
- Integrity check request (event_id or range)
- Audit report request (time range, category)

**Outputs:**
- Complete audit trail for event (all lifecycle events)
- Integrity check result (hash chain VALID / BROKEN)
- Audit report

**Consumers:** Human Principal; Governance Manager; Compliance (external); Risk Officer

**Dependencies:** Audit Manager; Registry; Archive Manager

**Failure Recovery:** NEVER_FAIL for audit reads — audit data is replicated; failover to replica automatically

---

### 5.15 Service 14: Learning Service

**Purpose:** Provides the interface between the Event Engine and the IIOS Learning System — extracting learning signals and receiving feedback.

**Inputs:**
- Learning signal extraction request (event_id or event range)
- Learning feedback (was the system's response to this event correct?)
- Calibration request (update confidence scoring for event type X)

**Outputs:**
- Learning signals (structured training data)
- Confidence calibration updates → Classification Engine
- Evolution signals → Evolution Manager

**Consumers:** Learning System; Strategy Performance Tracker; Meta Learning Layer

**Dependencies:** Evolution Manager; Analytics Manager; Registry

**Failure Recovery:** FAIL_SAFE — learning is advisory; failures do not affect live event processing

---

### 5.16 Service 15: Notification Service

**Purpose:** Delivers event notifications to external recipients — Telegram, email, dashboard alerts, and webhook callbacks.

**Inputs:**
- Notification request (event_id, recipient list, notification type)
- Notification template selection
- Urgency level

**Outputs:**
- Notification delivery confirmations
- Delivery failure alerts
- Notification history

**Notification routing:**

| Severity | Default channel | Escalation channel |
|---|---|---|
| CRITICAL (5) | Telegram (immediate) | Phone / SMS (if Telegram unavailable) |
| HIGH (4) | Telegram | Dashboard alert |
| MEDIUM (3) | Dashboard alert | Telegram (if dashboard unavailable) |
| LOW (2) | Dashboard (next refresh) | None |
| TRACE (1) | Log only | None |

**Consumers:** Human Principal; Risk Officer; Governance Manager; External monitoring

**Dependencies:** Telegram Bot; Dashboard; Email system

**Failure Recovery:**
- On Telegram failure: retry 3x with 10s backoff; escalate to alternate channel; log NOTIFICATION_FAILED event
- On all channels unavailable: log to persistent notification queue; deliver when channel restored

---
## PART VI — EVENT PROCESSING ARCHITECTURE

### 6.1 Processing Architecture Philosophy

The Event Engine must process events across wildly different time scales — from microsecond latency trading events to monthly economic calendar events — with radically different processing requirements for each. A single processing model cannot serve all these needs. The Event Processing Architecture defines 12 distinct processing modes, each optimised for its specific event category.

---

### 6.2 Processing Mode 1: Real-Time Events

**Definition:** Events that must be processed within milliseconds of occurrence. Latency matters — a 500 ms delay in processing a KILL_SWITCH_TRIGGERED event is operationally unacceptable.

**Examples:** Price threshold events, order fill events, risk limit breach events, broker connectivity events

**Processing pipeline:**

```
Detection (< 50ms)
    │
    ▼
Ingestion [high priority lane] (< 10ms)
    │
    ▼
Validation [simplified schema check only] (< 5ms)
    │
    ▼
Registration [synchronous] (< 5ms)
    │
    ▼
EMERGENCY / HIGH queue dispatch (< 5ms)
    │
    ▼
Consumer processing (< 100ms)
    │
    ▼
Total: < 200ms end-to-end
```

**Optimisations:**
- Pre-warmed Factory templates for known real-time event types
- In-memory Registry write buffer (flushed to disk asynchronously)
- Simplified contextual enrichment (only critical context fields)
- Priority queue bypass for severity 5 events

---

### 6.3 Processing Mode 2: Streaming Events

**Definition:** Events that arrive as a continuous high-frequency stream from market data feeds. Individual events in the stream may be low importance, but the stream as a whole must be monitored for threshold-crossing events and pattern events.

**Examples:** Price ticks, volume updates, bid-ask spread updates

**Processing pipeline:**

```
Data Feed Stream
    │
    ▼
Stream Buffer (rolling window)
    │
    ├──[threshold check]──► Generate threshold crossing event (→ Real-Time pipeline)
    │
    ├──[pattern check]──► Accumulate pattern state; generate composite event when pattern complete
    │
    └──[anomaly check]──► Flag statistical outlier; generate anomaly event
```

**Optimisations:**
- Stream processing is in-memory — individual ticks are not registered as events unless they trigger
- Pattern state is maintained in a bounded rolling window
- Pattern completion triggers a new event via the Real-Time pipeline
- Stream statistics (OHLCV per interval) are computed and stored, not individual ticks

---

### 6.4 Processing Mode 3: Scheduled Events

**Definition:** Events that are expected at known times based on the economic calendar, trading schedule, or IIOS internal schedule.

**Examples:** MARKET_OPEN, MARKET_CLOSE, GDP_RELEASE, RBI_RATE_DECISION, EOD_PROCESSING_START

**Processing pipeline:**

```
Economic Calendar / IIOS Scheduler
    │
    ▼
Scheduled Event Buffer (T-30 minutes: pre-warm context)
    │
    ▼
Scheduled Event Trigger (T=0: exact release time)
    │
    ▼
Registration Service (standard pipeline, pre-built draft)
    │
    ▼
Processing (with pre-built context — context was prepared at T-30)
```

**Optimisations:**
- Context is pre-built 30 minutes before scheduled events to reduce registration latency
- Propagation rules are pre-evaluated at T-30 (which derived events will this trigger?)
- Consumers are pre-notified at T-30 (prepare for incoming event)

**Calendar management:**
The Scheduled Event Buffer maintains the IIOS economic calendar — all known event types with their expected occurrence times. The calendar is updated daily from authoritative sources (RBI calendar, NSE calendar, economic data release schedule).

---

### 6.5 Processing Mode 4: Historical Events

**Definition:** Events from the past that are being re-processed — for backtesting, for audit, or for replay operations.

**Examples:** Replay of last month's trading events, historical correlation analysis, backtesting against 2019 market crash events

**Processing pipeline:**

```
Historical Query (time range specification)
    │
    ▼
Archive Manager retrieval
    │
    ▼
Chronological replay stream (events replayed in original timestamp order)
    │
    ▼
Consumer processing (in simulation context — no live state changes)
    │
    ▼
Replay analytics output
```

**Constraints:**
- Historical event processing must not create new events in the live Registry
- Historical events are processed in an isolated replay context
- System state is not modified by historical event replay

---

### 6.6 Processing Mode 5: Composite Events

**Definition:** Events that are defined by the coincidence of multiple simpler events matching a pattern within a time window. Composite events require pattern-matching across the event stream.

**Examples:** MARKET_CRASH (requires simultaneous price decline, volume spike, breadth collapse), REGIME_CHANGE_CONFIRMED (requires regime indicators from multiple independent sources)

**Processing pipeline:**

```
Simple Event Stream
    │
    ▼
Composite Pattern Matcher (rolling time window)
    │
    ├──[partial match]──► Maintain partial match state
    │
    ├──[match expired without completion]──► Discard partial match; log
    │
    └──[pattern complete]──► Generate composite event
                              │
                              ▼
                         Registration Service (composite event with source event list)
```

**Pattern match state:**
For each active composite pattern, the Detector maintains:
- Events matched so far
- Time remaining in the match window
- Match progress (e.g., 2 of 3 required conditions met)
- Partial confidence score

**Composite event record extras:**
- `source_event_ids`: list of all component events that formed this composite
- `pattern_id`: catalog identifier of the matched composite pattern
- `match_confidence`: confidence that all components belong to this pattern

---

### 6.7 Processing Mode 6: Cascading Events

**Definition:** Events that trigger other events in a chain — the cascade continues through the system, with each derived event potentially triggering further events.

**Examples:** RATE_HIKE cascades through bond yields → equity rotation → sector impacts → portfolio rebalancing

**Cascade control diagram:**

```
Primary Event (RATE_HIKE)
    │
    ├─[depth 1]─► BOND_YIELD_RISE
    │                 │
    │                 ├─[depth 2]─► EQUITY_SELLOFF
    │                 │                 │
    │                 │                 └─[depth 3]─► PORTFOLIO_REBALANCE_SIGNAL
    │                 │                                   │
    │                 │                                   └─[depth 4]─► POSITION_REDUCE
    │                 │
    │                 └─[depth 2]─► CURRENCY_IMPACT
    │
    └─[depth 1]─► LIQUIDITY_IMPACT
```

**Cascade controls:**
- Maximum cascade depth: 15 levels
- Each derived event gets its own full lifecycle (not a shortcut)
- Cascade depth is tracked and included in each derived event's metadata
- Loop detection at each level (if an event type would trigger itself, break the chain)

---

### 6.8 Processing Mode 7: Concurrent Events

**Definition:** Multiple events occurring simultaneously — within the same processing cycle — requiring careful ordering and potential conflict resolution.

**Examples:** Multiple risk limit breaches in the same second; simultaneous fill confirmations from multiple instruments

**Concurrent event handling:**

```
Concurrent Event Set {E1, E2, E3} arrive in same processing window
    │
    ▼
Priority ordering by Priority Manager (E2 > E1 > E3)
    │
    ▼
Dependency check (does E3 depend on E1?)
    │
    ├──[dependency exists]──► Reorder: E2 → E1 → E3
    │
    ▼
Sequential processing in priority order
    │
    ▼
Conflict detection (do E1 and E3 produce contradictory state changes?)
    │
    ├──[conflict detected]──► Generate CONFLICT_DETECTED event; escalate
    │
    ▼
Sequential state updates
```

---

### 6.9 Processing Mode 8: Dependent Events

**Definition:** Events that can only be generated, processed, or acted upon after a prerequisite event has occurred.

**Examples:** ORDER_FILLED depends on ORDER_SUBMITTED; POSITION_CLOSED depends on POSITION_OPENED; STRATEGY_DEMOTED depends on WIN_RATE_BELOW_THRESHOLD

**Dependency resolution:**

```
Dependent Event E2 arrives (requires E1 as prerequisite)
    │
    ├──[E1 found in Registry]──► Process E2 normally
    │
    └──[E1 not found]──► Place E2 in DEPENDENCY_HOLD queue
                             │
                             ├──[E1 arrives within timeout]──► Release E2; process
                             │
                             └──[timeout exceeded]──► Generate MISSING_PREREQUISITE event;
                                                      process E2 with DEGRADED_CONTEXT flag
```

---

### 6.10 Processing Mode 9: Recursive Events

**Definition:** Events that are generated by the very process of handling an event — for example, auditing an event generates an audit event, which itself must be audited (but without infinite recursion).

**Recursive event controls:**
- Audit events generated for audit operations are stored directly without triggering further audit events (recursive exemption)
- System lifecycle events are not propagated to downstream analytical pipelines that would re-generate system events
- Maximum recursion depth for any event type: 3 levels (enforced by Dependency Engine)

---

### 6.11 Processing Mode 10: Derived Events

**Definition:** Events generated analytically from one or more source events — not from direct external observation but from computation over observed events.

**Examples:** VOLATILITY_REGIME_CHANGE derived from 20 consecutive VIX readings; REGIME_TRANSITION derived from regime indicator confluence

**Derived event provenance:**

```
Derived Event Record includes:
- derivation_method: "Exponential smoothing of VIX observations over 20 days"
- source_event_ids: [list of contributing events]
- derivation_confidence: computed confidence in the derivation
- derivation_timestamp: when the derivation was computed
- primary: false (flag indicating this is a derived, not primary, event)
```

---

### 6.12 Processing Mode 11: Delayed Events

**Definition:** Events whose occurrence time is significantly earlier than their detection time — events from delayed data sources, from reconnected feeds, or from manual data entry.

**Delayed event handling:**

```
Delayed Event Signal (original_time = T-60min; detection_time = NOW)
    │
    ▼
Factory enrichment: record both timestamps
    │
    ▼
Registration with original timestamp
    │
    ▼
Timeline Manager: insert at chronological position T-60min
    │
    ▼
Retroactive propagation: evaluate what this event would have triggered at T-60min
    │
    ├──[if propagated events would have changed live decisions]──► Flag for Human Principal review
    │
    └──[if retroactive propagation has no live impact]──► Log; process normally
```

---

### 6.13 Processing Mode 12: Expired Events

**Definition:** Events that arrive after their actionable window has closed — events that would have been relevant at T-0 but are now beyond the time window where they can affect decisions.

**Expired event handling:**
- Expired events are still registered (for historical completeness)
- Propagation rules are evaluated with EXPIRED context flag — derived events may not be generated
- Expired events are marked with `lifecycle_state: EXPIRED` after registration
- Expired events are archived immediately to warm storage (bypassing hot storage)
- Expired events still contribute to learning datasets

---

### 6.14 Complete Processing Pipeline Diagram

```
                        EVENT PROCESSING PIPELINE
                        ─────────────────────────

External Sources                    Event Engine                         Consumers
────────────────                    ────────────                         ─────────
Market Data ──────────────────► DETECTION SERVICE
News Feed  ──────────────────►     │
Broker API ──────────────────►     ▼
Scheduler  ──────────────────► INGESTION MANAGER
Internal   ──────────────────►     │ (Normalise, Deduplicate, Rate-limit)
                                   ▼
                              FACTORY (Create draft, Enrich context)
                                   │
                                   ▼
                              VALIDATOR (Structural, Semantic, Referential)
                                   │
                             [FAIL]─────────────────────────────► DEAD LETTER
                                   │[PASS]
                                   ▼
                              CLASSIFICATION ENGINE (Type, Severity, Category)
                                   │
                                   ▼
                              PRIORITY MANAGER (Assign priority score)
                                   │
                                   ▼
                              REGISTRY (Assign event_id; persist; index)
                                   │
                              [IMMUTABLE from this point]
                                   │
                              ─────┼─────────────────────────────────────
                                   │
                                   ├──► TIMELINE MANAGER (temporal index)
                                   │
                                   ├──► CORRELATION ENGINE (cluster analysis)
                                   │
                                   ├──► PROPAGATION ENGINE ──────────────────►
                                   │         (generate derived events)   INGESTION (loop)
                                   │
                              QUEUE MANAGER (Priority routing)
                                   │
                        ┌──────────┼──────────┐──────────┐
                        ▼          ▼          ▼          ▼
                  Risk Engine  Strategy   Learning   Knowledge
                  (EMERGENCY)  (HIGH)     (STANDARD) (STANDARD)
                        │          │          │          │
                        └──────────┴──────────┴──────────┘
                                   │
                              LIFECYCLE MGR (CONSUMED state)
                                   │
                              AUDIT MANAGER (record consumption)
                                   │
                              ANALYTICS MGR (aggregate metrics)
                                   │
                              LEARNING SERVICE (extract signals)
                                   │
                              ARCHIVE MANAGER (tiered archival)
```

---

### 6.15 Propagation Depth and Attenuation Diagram

```
PRIMARY EVENT (Confidence: 1.0)
    │
    ├─[depth 1 derived]──► DERIVED_A (Confidence: 0.90 × 1.0 = 0.90)
    │       │
    │       └─[depth 2 derived]──► DERIVED_A1 (Confidence: 0.85 × 0.90 = 0.77)
    │               │
    │               └─[depth 3 derived]──► DERIVED_A1a (Confidence: 0.80 × 0.77 = 0.61)
    │
    └─[depth 1 derived]──► DERIVED_B (Confidence: 0.95 × 1.0 = 0.95)

Rule: Each propagation level applies a confidence attenuation factor (type-specific, default 0.85–0.95).
      Propagation stops when accumulated confidence falls below 0.10.
```

---
## PART VII — EVENT INTELLIGENCE FRAMEWORK

### 7.1 Intelligence Framework Purpose

The Event Intelligence Framework (EIF) transforms raw event records into actionable intelligence. While the previous parts covered how events are detected, registered, and delivered, the EIF is concerned with what events mean — individually and in combination.

The EIF has 16 analytical capabilities, organised into four analytical dimensions: root understanding (why did this happen?), impact understanding (what will this affect?), pattern understanding (have we seen this before?), and prediction (what will happen next?).

---

### 7.2 Capability 1: Root Cause Analysis (RCA)

**Purpose:** Identify the initiating cause in an event chain — the root event that, if prevented, would have broken the downstream cascade.

**RCA algorithm:**

```
Given: Target event E (the effect we want to explain)

Step 1: Retrieve all events in the 6-hour window before E
Step 2: Filter to events with CAUSAL relationship confidence > 0.70 to E
Step 3: Build causal tree (reverse BFS from E following CAUSED_BY edges)
Step 4: Identify root nodes (nodes with no CAUSED_BY predecessors in the tree)
Step 5: Score each root node by causal chain strength (product of confidence along path)
Step 6: Return top 3 root causes with causal path and chain confidence
```

**RCA output:**

| Field | Description |
|---|---|
| root_event_id | The identified root cause event |
| causal_path | Ordered list of events from root to target |
| chain_confidence | Product of causal confidences along the path |
| alternative_roots | Other candidate root causes with their chain confidence |
| rca_timestamp | When the RCA was computed |

**RCA use cases:**
- Post-trade analysis: "Why was this trade triggered?"
- Risk attribution: "What caused this drawdown?"
- Strategy debugging: "Why did this strategy fail in this session?"

---

### 7.3 Capability 2: Impact Analysis

**Purpose:** Given a new event, predict and quantify its downstream impact on entities, relationships, strategies, and portfolio.

**Impact analysis dimensions:**

| Dimension | Description | Computation |
|---|---|---|
| Entity impact | Which entities are directly or indirectly affected | Graph traversal from event source entity |
| Relationship impact | Which relationships will be strengthened, weakened, or destroyed | Propagation rule evaluation |
| Strategy impact | Which strategies will be affected (regime change, new hypothesis) | Strategy-event sensitivity map |
| Portfolio impact | Estimated P&L impact, risk metric change | Monte Carlo sensitivity |
| Temporal impact | How long will the impact last | Historical precedent analysis |

**Impact severity matrix:**

| Impact dimension | Severity 5 | Severity 4 | Severity 3 |
|---|---|---|---|
| Portfolio P&L effect | > 2% daily capital | 1–2% | 0.5–1% |
| Strategy count affected | > 30% | 15–30% | 5–15% |
| Risk metric change | Kill switch threshold | Risk alert | Monitor |
| Entity count affected | > 100 | 20–100 | 5–20 |

---

### 7.4 Capability 3: Dependency Analysis

**Purpose:** Map the full dependency graph of an event — what depends on this event having occurred correctly, and what does this event depend on.

**Dependency graph structure:**

```
Event E
    │
    ├──[what E depends on]──► Prerequisite events (DEPENDS_ON edges — historical)
    │                          Prerequisite entities (entity state requirements)
    │
    └──[what depends on E]──► Downstream events (events that require E to exist)
                               Consuming components (who subscribed to E)
                               Derived events (what E generates via propagation)
```

**Dependency analysis use cases:**
- Impact of missing event: "If GDP_RELEASED had not been detected, what downstream analytics would be missing?"
- Correctness assessment: "Is this event's context complete given its dependencies?"
- Sequence validation: "Are all prerequisite events present before acting on E?"

---

### 7.5 Capability 4: Propagation Analysis

**Purpose:** Trace the full downstream propagation of an event — what derived events were generated, what state changes occurred, what decisions were triggered.

**Propagation trace output:**

```
EVENT_ID: EVT-ECO-20260615-000042 (RBI_RATE_CUT)
Propagation Depth: 4
Total Derived Events: 12
────────────────────────────────────────────────
Level 1: [EVT-MKT-20260615-000043] BOND_YIELD_FALL (confidence: 0.95)
          [EVT-MKT-20260615-000044] BANKING_SECTOR_BOOST (confidence: 0.88)
          [EVT-MKT-20260615-000045] INR_APPRECIATION (confidence: 0.82)
Level 2: [EVT-MKT-20260615-000047] NIFTY_BANK_RALLY (confidence: 0.84)
          [EVT-MKT-20260615-000048] REAL_ESTATE_SECTOR_BOOST (confidence: 0.79)
          [EVT-MKT-20260615-000049] REGIME_SHIFT_SIGNAL (confidence: 0.71)
Level 3: [EVT-AI-20260615-000051] HYPOTHESIS_CREATED (confidence: 0.85)
          [EVT-PRF-20260615-000052] PORTFOLIO_REBALANCE_SIGNAL (confidence: 0.75)
Level 4: [EVT-TRD-20260615-000053] ORDER_CREATED (confidence: 1.00)
          [EVT-TRD-20260615-000054] ORDER_FILLED (confidence: 1.00)
          [EVT-PRF-20260615-000055] PORTFOLIO_NAV_UPDATED (confidence: 1.00)
          [EVT-RSK-20260615-000056] RISK_METRICS_UPDATED (confidence: 1.00)
────────────────────────────────────────────────
Full propagation chain: 12 events across 4 levels
Propagation chain confidence (min): 0.71
```

---

### 7.6 Capability 5: Event Clustering

**Purpose:** Group events into meaningful clusters — events that share a common underlying driver, events that form a coherent market narrative, or events that represent a regime shift.

**Clustering algorithms:**

| Algorithm | Use case | Distance metric |
|---|---|---|
| Temporal clustering | Events occurring in the same time window | Time distance |
| Type clustering | Events of related types (same category) | Type taxonomy distance |
| Entity clustering | Events involving the same or related entities | Entity relationship distance |
| Causal clustering | Events linked by causal or propagation chains | Chain depth |
| Semantic clustering | Events with similar payloads or impacts | Semantic embedding distance |

**Cluster output:**
- Cluster ID and label
- Member event list with membership confidence
- Cluster centroid event (most representative event)
- Cluster driver (the event most likely responsible for the cluster)
- Cluster narrative (natural language description of the cluster's meaning)

---

### 7.7 Capability 6: Temporal Correlation

**Purpose:** Identify events that consistently co-occur within a defined time window — indicating a systematic relationship in timing.

**Temporal correlation computation:**

For event types A and B, temporal correlation at lag τ is:

$$\rho_{AB}(\tau) = \frac{P(\text{event B within } [\tau, \tau + \delta] \text{ after event A}) - P(\text{event B})}{P(\text{event B})}$$

High positive ρ indicates event B consistently follows event A by approximately τ time. This is used to:
- Build the propagation delay model (how long does a rate cut take to affect equity prices?)
- Detect broken correlations (previously reliable timing relationships that are no longer holding)
- Anticipate downstream events (if ρ is high, event B is expected when event A occurs)

---

### 7.8 Capability 7: Spatial Correlation

**Purpose:** Identify which markets, sectors, or instruments are spatially connected — where an event in one location consistently produces correlated events in related locations.

**Spatial correlation map for Indian equities:**

```
Global
    ├── US Markets (VIX, S&P 500)
    │       └──[high correlation]──► NIFTY50 direction
    │               └──[medium correlation]──► Banking sector
    │                       └──[high correlation]──► BANKNIFTY
    │
    ├── Oil price
    │       └──[high correlation]──► OMC stocks (HPCL, BPCL, IOC)
    │       └──[negative correlation]──► Aviation stocks
    │
    └── INR/USD
            └──[high correlation]──► IT sector (export revenue effect)
            └──[negative correlation]──► Import-heavy sectors
```

Spatial correlations are maintained as CORRELATED_WITH relationships in the Relationship Engine, with strength updated by the Correlation Engine based on recent event correlation data.

---

### 7.9 Capability 8: Cross-Market Correlation

**Purpose:** Track correlations between events across different financial markets — Indian equities, US equities, commodities, currencies, and fixed income.

**Cross-market event correlation table:**

| Trigger event | Correlated market events | Lag | Strength |
|---|---|---|---|
| US_FED_RATE_HIKE | INR_DEPRECIATION | 2–4 hours | 0.78 |
| US_FED_RATE_HIKE | NIFTY_SELLOFF | 1 day | 0.65 |
| OIL_PRICE_SPIKE > 5% | INR_DEPRECIATION | 1 day | 0.72 |
| OIL_PRICE_SPIKE > 5% | OMC_SECTOR_SELLOFF | 1 day | 0.80 |
| US_RECESSION_SIGNAL | FII_OUTFLOW_SPIKE | 1 week | 0.85 |
| GLOBAL_VIX_SPIKE > 30 | NIFTY_CIRCUIT_BREAKER_RISK | 1 day | 0.70 |

Cross-market correlations are reviewed and updated monthly by the Evolution Manager.

---

### 7.10 Capability 9: Historical Similarity

**Purpose:** Given a new event or event sequence, identify historical events or sequences that are most similar — enabling the system to apply historical outcome distributions to current situations.

**Similarity computation:**

```
New Event E (type: RATE_CUT, payload: {cut_magnitude: 50bps, regime: BEAR})
    │
    ▼
Historical search: all RATE_CUT events in history
    │
    ▼
Filter by payload similarity (cut_magnitude ± 15bps)
    │
    ▼
Filter by context similarity (regime = BEAR or NEUTRAL)
    │
    ▼
Rank by overall similarity score (weighted: 40% type, 30% magnitude, 30% context)
    │
    ▼
Return top 5 historical analogues with outcome distributions
```

**Historical analogue output:**
- Analogue event record
- Similarity score
- Outcome distribution (what happened in the 5 sessions following the analogue)
- Context divergence (how current context differs from analogue)

---

### 7.11 Capability 10: Novelty Detection

**Purpose:** Identify events that have no significant historical precedent — events that represent genuinely new market conditions or system behaviours.

**Novelty detection algorithm:**

1. Classify the event using the ML classification model
2. Query historical similarity — find top 5 analogues
3. If best historical similarity score < 0.40: event is NOVEL
4. If event type is UNCLASSIFIED_EVENT: event is NOVEL
5. Compute Novelty Score: 1 − max(historical_similarity_scores)

**Novelty response protocol:**

| Novelty Score | Response |
|---|---|
| 0.90–1.00 (completely novel) | Human Principal immediate alert; no automated action |
| 0.70–0.89 (highly novel) | Human Principal notification; conservative automated response |
| 0.50–0.69 (somewhat novel) | Telegram alert; standard automated response with elevated monitoring |
| 0.00–0.49 (precedented) | No novelty alert; standard response |

---

### 7.12 Capability 11: Pattern Recognition

**Purpose:** Identify recurring event patterns — sequences of events that consistently precede specific outcomes — and match new event sequences against these patterns.

**Pattern types:**

| Pattern type | Description | Example |
|---|---|---|
| Sequential | A → B → C in that order within time window | RATE_HIKE → BOND_YIELD_RISE → EQUITY_SELLOFF |
| Concurrent | A ∧ B ∧ C simultaneously | PRICE_DOWN + VOLUME_SPIKE + BREADTH_COLLAPSE |
| Alternating | A, B, A, B (alternating pattern) | Accumulation: BUY_SIGNAL, MINOR_DECLINE, BUY_SIGNAL |
| Nested | A triggers B, B triggers C, A triggers C independently | Complex market structure events |
| Anti-pattern | A occurs WITHOUT B (absence pattern) | VOLUME_SPIKE without PRICE_MOVE = manipulation signal |

**Pattern catalog:** The Event Catalog maintains a growing pattern catalog, updated by the Evolution Manager as new patterns are discovered and validated.

---

### 7.13 Capability 12: Anomaly Detection

**Purpose:** Identify events that are statistically unusual — events whose properties fall significantly outside the expected distribution for their type.

**Anomaly detection models:**

| Model | Anomaly type detected | Threshold |
|---|---|---|
| Univariate Z-score | Single metric outlier (price, volume) | > 3σ |
| Multivariate Mahalanobis | Multi-metric outlier | > 3σ Mahalanobis distance |
| Isolation Forest | Unusual combination of metrics | Top 5% isolation score |
| Temporal | Unusual timing (event too early/late) | > 2× historical standard deviation in timing |
| Frequency | Unusual event frequency (too many/few) | > 3σ from historical frequency |

**Anomaly response:**
- Anomaly score attached to event metadata
- Events with anomaly score > 0.90 generate ANOMALY_DETECTED derived event
- ANOMALY_DETECTED events are classified at severity 3+

---

### 7.14 Capability 13: Event Prediction

**Purpose:** Given the current event state and historical patterns, predict which events are most likely to occur in the near future.

**Prediction model:**

```
Current state: {active events, recent event history, market regime, portfolio state}
    │
    ▼
Pattern matcher: find historical states most similar to current state
    │
    ▼
Outcome distributions: what events followed similar historical states?
    │
    ▼
Prediction: top 5 most likely next events with probability and time horizon
```

**Prediction output:**

| Predicted event | Probability | Time horizon | Confidence |
|---|---|---|---|
| NIFTY_CIRCUIT_BREAKER_RISK | 0.25 | Within 2 hours | 0.70 |
| PORTFOLIO_REBALANCE_SIGNAL | 0.60 | Within 30 minutes | 0.85 |
| FII_OUTFLOW_SPIKE | 0.40 | Within 1 day | 0.65 |

Predictions are advisory only — they are used to pre-position consumers, not to trigger automated actions.

---

### 7.15 Capability 14: Event Probability

**Purpose:** Assign and update probability estimates for uncertain events — events whose occurrence is not yet confirmed but has some probability.

**Event probability model:**

$$P(\text{event occurs}) = \frac{\text{confirmed indicators}}{\text{total indicators monitored}} \times \text{historical\_base\_rate} \times \text{regime\_modifier}$$

Events with probability > 0.80 generate PROBABLE_EVENT signals, which cause the system to pre-warm consumers and pre-evaluate propagation chains.

---

### 7.16 Capability 15: Event Confidence

**Purpose:** Maintain and update the confidence score for every event — reflecting the system's certainty that the event occurred, was classified correctly, and has correct payload.

**Confidence update sources:**

| Source | Effect on confidence | Example |
|---|---|---|
| Additional confirming signal from second data source | +0.10 | Second feed confirms price threshold crossing |
| Human Principal confirmation | → 1.0 (manual override to maximum) | Human confirms an unusual event |
| Automated validation pass | +0.05 | All validation checks passed |
| Conflicting signal received | −0.15 | Alternative data feed shows different value |
| Human Principal correction | → correction event (original superseded) | Human identifies misclassification |

---

### 7.17 Capability 16: Learning Feedback

**Purpose:** Close the intelligence loop — take the outcomes of events and feed them back into the Event Engine's detection, classification, and prediction models.

**Learning feedback loop:**

```
Event E occurs → System responds → Outcome observed → Outcome quality assessed
    │                                                          │
    └──────────────────────────────────────────────────────────┘
                            │
                            ▼
               Evolution Manager receives outcome signal
                            │
                    ┌───────┼───────┐
                    ▼       ▼       ▼
           Detection    Classification  Prediction
           rule update  model update    model update
```

**Learning signals:**
- Was the event detected promptly? (detection quality)
- Was the classification correct? (classification quality)
- Was the impact prediction accurate? (impact model quality)
- Was the propagation chain correct? (propagation rule quality)
- Were similar historical events correctly identified? (similarity model quality)

---
## PART VIII — EVENT GOVERNANCE

### 8.1 Governance Philosophy

Event governance ensures that every event in the IIOS is managed responsibly — owned, classified appropriately, retained as required, audited completely, and secured correctly. Event governance has a unique challenge not present in entity or relationship governance: events are immutable. This means corrections must be managed through supersession (creating correction events), not modification. Governance of an immutable record system demands rigorous classification at creation time because post-creation correction is always more expensive than getting it right on entry.

---

### 8.2 Governance Dimension 1: Ownership

**Ownership rules:**

| Rule | Description |
|---|---|
| Every event has an owner | No event may exist without a responsible owner |
| Owner is assigned at creation | Ownership is determined by the event source or creator |
| Owner is accountable | The owner is responsible for the event's accuracy and appropriate lifecycle management |
| Critical events have a secondary owner | The Human Principal is secondary owner of all CRITICAL events |

**Ownership assignment matrix:**

| Event category | Primary owner | Secondary owner |
|---|---|---|
| Market Events | Data Feed Manager | Human Principal |
| Corporate Events | News / Data Feed | Human Principal |
| Economic Events | Market Intelligence | Human Principal |
| Government Events | Market Intelligence | Human Principal |
| Central Bank Events | Market Intelligence | Human Principal |
| Trading Events | Order Manager | Human Principal |
| Portfolio Events | Portfolio Allocation | Human Principal |
| Risk Events | Risk Guardian | Human Principal (always) |
| AI Events | Originating agent | Human Principal |
| Learning Events | Learning Engine | Human Principal |
| System Events | System Monitor | Human Principal |
| Knowledge Events | Knowledge Engine | Human Principal |
| Decision Events | Decision Engine | Human Principal (always) |

---

### 8.3 Governance Dimension 2: Approval

**Approval requirements:**

| Event type | Approval required | Approver | Rationale |
|---|---|---|---|
| KILL_SWITCH_RESET | Yes — before reset | Human Principal | Kill switch reset must be deliberate |
| STRATEGY_PROMOTED | Yes | Human Principal | Strategy promotion affects live capital |
| HUMAN_OVERRIDE | Yes — initiates own creation | Human Principal | Overrides are by definition human decisions |
| EXECUTION_AUTHORISED (large orders) | Yes | Human Principal | Large orders require explicit authorisation |
| NOVEL event (novelty score > 0.90) | Yes — before action taken | Human Principal | Completely novel events require human judgement |
| GOVERNANCE_VIOLATION (CRITICAL) | Yes — for remediation plan | Human Principal | Critical violations demand deliberate response |

For non-approval-required events: automatic processing continues without pause.

---

### 8.4 Governance Dimension 3: Severity Classification

**Severity classification authority:**

| Initial classification | Authority | Override authority |
|---|---|---|
| Factory (automated) | Initial classification based on Catalog rules | Classification Engine (post-classification review) |
| Classification Engine (automated) | Definitive automated classification | Human Principal (manual override) |
| Human Principal (manual) | Final authority — cannot be overridden | None |

**Misclassification remediation:**
When a severity misclassification is detected (an event was classified too low or too high):
1. A SEVERITY_RECLASSIFICATION event is created referencing the original event
2. The original event is NOT modified (immutable)
3. Downstream consumers are notified of the reclassification
4. The Evolution Manager records the misclassification as a learning signal

---

### 8.5 Governance Dimension 4: Priority Rules

**Priority governance rules:**

| Rule | Description |
|---|---|
| CRITICAL events bypass rate limits | Severity 5 events are never throttled |
| CRITICAL events bypass queue length limits | Severity 5 events are never dropped |
| Kill switch events bypass all queues | Kill switch events have absolute priority |
| Priority aging prevents starvation | Events gain priority over time in queue |
| Human Principal can always elevate priority | Manual priority override is always available |
| Background events may be deferred | TRACE events may be deferred during high-load periods |

---

### 8.6 Governance Dimension 5: Conflict Resolution

**Event conflicts arise in three scenarios:**

**Scenario 1: Contradictory simultaneous events**
Two events arrive simultaneously making contradictory claims (e.g., MARKET_OPEN and MARKET_HALT for the same exchange at the same time).

Resolution:
1. Generate CONFLICT_DETECTED event
2. Both original events are registered (immutable)
3. Consuming components are flagged: contradictory events exist
4. Human Principal is notified
5. Human Principal creates a RESOLUTION event that indicates which event is authoritative

**Scenario 2: Duplicate events from multiple sources**
The same real-world occurrence generates events from two different data sources.

Resolution:
1. Idempotency check detects the duplicate
2. First-received event is registered; second is deduplicated
3. Second source is recorded in the first event's metadata as `confirming_source`
4. Confidence is elevated for the original event (confirming source found)

**Scenario 3: Correction of a registered event**
A registered event is discovered to have incorrect data.

Resolution:
1. Create a CORRECTION event with corrected data
2. Original event is transitioned to SUPERSEDED state
3. CORRECTION event references original event via `supersedes_event_id`
4. Consuming components that acted on the original are notified via CORRECTION_NOTIFICATION

---

### 8.7 Governance Dimension 6: Duplicate Detection

**Duplication detection rules:**

| Deduplication key | Scope | Action |
|---|---|---|
| (event_type, source, timestamp, payload_hash) | Global | Exact duplicate — reject second; return first event_id |
| (event_type, entity_id, timestamp ± 1 second) | Per entity | Near-duplicate — register with POTENTIAL_DUPLICATE flag |
| (event_type, same session, same trigger condition) | Per session | Session duplicate — register; flag for review |

**Near-duplicate policy:** Near-duplicates are registered (not rejected) because two similar-but-distinct events may represent two genuine occurrences. The POTENTIAL_DUPLICATE flag causes the Governance Manager to review within 24 hours.

---

### 8.8 Governance Dimension 7: Merge Rules

Unlike entities and relationships, events are never merged. Two distinct event records remain distinct, even if they describe the same occurrence. The approved resolution mechanism is supersession — one event supersedes another, and both records are preserved.

**Prohibition:** Event merging is prohibited. Any request to merge event records must be rejected with a documented explanation of why supersession should be used instead.

---

### 8.9 Governance Dimension 8: Split Rules

An event cannot be split into two events after registration (immutability). If an event that should have been two separate events was registered as one:
1. The original event is SUPERSEDED
2. Two new events are created, both referencing the original via `derived_from_event_id`
3. A SPLIT_PERFORMED governance record is created

---

### 8.10 Governance Dimension 9: Versioning

Events themselves are immutable — they do not have versions in the traditional sense. Versioning applies to:
- **Event Type Definitions** (Catalog versioning — each schema update creates a new version)
- **Event Metadata** (metadata updates are versioned and append-only)
- **Governance Policies** (policy updates are versioned)

**Metadata versioning:** Every metadata update for an event creates a new metadata version record. The metadata history is preserved in full, enabling reconstruction of the event's complete metadata history at any point in time.

---

### 8.11 Governance Dimension 10: Audit Policy

**Audit requirements by event category:**

| Category | Audit level | Retention period |
|---|---|---|
| Risk Events (all severity) | FULL | Relationship lifetime + 10 years |
| Trading Events (orders, fills) | FULL | 7 years (financial record requirement) |
| Decision Events | FULL | 7 years |
| Kill Switch Events | FULL | Permanent |
| System Events (CRITICAL) | FULL | 5 years |
| AI Events | STANDARD | 2 years |
| Market Events | STANDARD | 1 year |
| Learning Events | STANDARD | 2 years |
| System Events (LOW/TRACE) | MINIMAL | 90 days |

**Audit chain integrity:** The Audit Manager runs weekly integrity checks on the hash chain for all CONFIDENTIAL and RESTRICTED events. Any break in the hash chain generates an immediate TAMPER_DETECTED event with severity 5.

---

### 8.12 Governance Dimension 11: Security

**Event sensitivity classification:**

| Sensitivity | Description | Access |
|---|---|---|
| PUBLIC | No sensitive content | All IIOS components |
| INTERNAL | Internal operational data | All IIOS components; not external |
| CONFIDENTIAL | Contains strategic or financial data | Owner + authorised components only |
| RESTRICTED | Contains high-sensitivity financial or personal data | Owner + explicit authorisation only |

**Sensitivity inheritance rules:**
- Events involving RESTRICTED entities are automatically classified RESTRICTED
- Kill switch events are always RESTRICTED
- Position events are CONFIDENTIAL
- Market events are PUBLIC

**Access control matrix:**

| Sensitivity | Read | Write (create new) | Admin (manage lifecycle) |
|---|---|---|---|
| PUBLIC | All | Owner only | Human Principal |
| INTERNAL | All IIOS | Owner only | Human Principal |
| CONFIDENTIAL | Owner + authorised | Owner only | Human Principal |
| RESTRICTED | Explicit authorisation | Owner only | Human Principal |

---

### 8.13 Governance Dimension 12: Compliance

**Compliance monitoring schedule:**

| Check | Frequency | Responsible component |
|---|---|---|
| Ownership validation | Every session | Governance Manager |
| Retention policy compliance | Daily | Archive Manager |
| Audit chain integrity | Weekly | Audit Manager |
| Security access review | Weekly | Governance Manager |
| Sensitivity classification review | Monthly | Governance Manager |
| Full governance health report | Monthly | Governance Manager |

**Compliance violation escalation:**

| Severity | Action | Timeline |
|---|---|---|
| INFO | Log; monthly report | N/A |
| WARNING | Log; weekly Telegram summary | Within 7 days |
| ERROR | Governance alert; Telegram notification | Within 24 hours |
| CRITICAL | Immediate Telegram; Human Principal review required | Immediate |

---

### 8.14 Governance Dimension 13: Retention

**Retention policy framework:**

| Category | Minimum retention | Maximum retention | Archive tier |
|---|---|---|---|
| Kill switch events | Permanent | Permanent | Permanent |
| Trading events | 7 years | Permanent | COLD → PERMANENT |
| Risk events (CRITICAL) | 10 years | Permanent | COLD → PERMANENT |
| Decision events | 7 years | Permanent | COLD → PERMANENT |
| AI events | 2 years | 5 years | COLD |
| Market events | 1 year | 2 years | COLD |
| System events (TRACE) | 90 days | 1 year | WARM → expire |

**Retention override:** The Human Principal may override retention policies to extend retention for specific events (e.g., for regulatory investigation purposes). Retention overrides are recorded as governance events and require documented justification.

---

### 8.15 Governance Dimension 14: Archival

**Archival governance rules:**

| Rule | Description |
|---|---|
| Archival is policy-driven | Events are archived by policy, not manually (except override) |
| Archival is not deletion | Archival moves to lower storage tier; the record is never deleted (for CRITICAL events) |
| Archival is reversible | Archived events can be restored to hot storage on request |
| Archival requires audit | Every archival operation generates an EVENT_ARCHIVED audit record |
| Permanent archive is write-once | Events in the permanent archive cannot be modified or deleted |

**Archival state diagram:**

```
HOT STORAGE (< 7 days)
    │
    ▼ [age > hot retention policy]
WARM STORAGE (7 days – 90 days)
    │
    ▼ [age > warm retention policy]
COLD STORAGE (90 days – retention limit)
    │
    ├──[CRITICAL/Financial]──► PERMANENT ARCHIVE (forever)
    │
    └──[others]──► EXPIRE (record deleted after retention limit)
```

---

### 8.16 Governance Responsibility Matrix

| Governance function | Governance Manager | Audit Manager | Archive Manager | Human Principal | Lifecycle Manager |
|---|---|---|---|---|---|
| Policy assignment | PRIMARY | Advisory | Advisory | OVERRIDE | — |
| Violation detection | PRIMARY | SUPPORT | SUPPORT | REVIEW | — |
| Severity override | FACILITATED | — | — | PRIMARY | — |
| Audit chain | OVERSIGHT | PRIMARY | — | REVIEW | — |
| Retention enforcement | OVERSIGHT | — | PRIMARY | OVERRIDE | — |
| Archival execution | OVERSIGHT | AUDIT | PRIMARY | OVERRIDE | COORDINATE |
| Conflict resolution | COORDINATE | — | — | PRIMARY | EXECUTE |
| Compliance reporting | PRIMARY | SUPPORT | SUPPORT | REVIEW | — |

---
## PART IX — EVENT CONSTITUTION

### 9.1 Overview

The Event Constitution is the supreme set of mandatory rules governing every event in the IIOS. These 82 rules are non-negotiable. Rules are organised into nine categories: Identity (EC-A), Immutability (EC-B), Temporality (EC-C), Structure (EC-D), Quality (EC-E), Lifecycle (EC-F), Audit (EC-G), Governance (EC-H), and Intelligence (EC-I).

---

### 9.2 Category A: Identity Rules

| Rule ID | Rule | Rationale |
|---|---|---|
| EC-A-01 | Every event has exactly one permanent canonical identity (UUID4 event_id) assigned at registration. | Identity is the foundation of all event operations. |
| EC-A-02 | An event's canonical identity never changes after assignment. | Changing identity breaks all references and audit chains. |
| EC-A-03 | A retired event's event_id is never reused. | Reuse breaks historical audit continuity. |
| EC-A-04 | Every event has a Reference ID in the format EVT-{CATEGORY}-{YYYYMMDD}-{SEQUENCE}. | Human-readable identifiers are required for operational use. |
| EC-A-05 | Identity resolution must return the canonical event_id for any valid identifier (UUID4, Reference ID, external ID). | All identifier types must be resolvable to the canonical identity. |
| EC-A-06 | No two event records may represent exactly the same occurrence (same type, same source, same timestamp, same entity) — one must be a duplicate and resolved. | Duplicate events corrupt analytics and learning datasets. |
| EC-A-07 | Every event has a `source` field identifying the IIOS component or external feed that originated the event. | Sourceless events cannot be attributed, audited, or diagnosed. |
| EC-A-08 | Every derived event includes a `parent_event_id` reference to the event that caused it. | Derived events must be traceable to their origin. |
| EC-A-09 | Every composite event includes a `source_event_ids` list referencing all component events. | Composite events must be fully decomposable. |
| EC-A-10 | Every event has an `owner_id` assigned at creation. | Ownerless events have no accountability. |

---

### 9.3 Category B: Immutability Rules

| Rule ID | Rule | Rationale |
|---|---|---|
| EC-B-01 | Every event record is immutable after registration — no field may be modified. | Immutability is the foundation of an audit-grade event system. |
| EC-B-02 | Corrections to event records are made by creating a new event with a `supersedes_event_id` reference to the original. | Immutability + correctability = supersession model. |
| EC-B-03 | Original events are never deleted, even when superseded. | Both the error and the correction are part of the historical record. |
| EC-B-04 | Every event record includes an `immutable_hash` (SHA-256 of all event fields at creation). | The hash enables tamper detection for immutable records. |
| EC-B-05 | Any attempt to modify a registered event record is rejected and generates a TAMPER_ATTEMPT event. | The system actively detects and responds to integrity violations. |
| EC-B-06 | Event metadata (supplementary annotations) may be updated, but updates are version-controlled and append-only. | Metadata is not part of the immutable core; it provides supplementary context. |
| EC-B-07 | The immutable hash is verified on every read of an event record. | Verification on read prevents use of tampered records. |

---

### 9.4 Category C: Temporality Rules

| Rule ID | Rule | Rationale |
|---|---|---|
| EC-C-01 | Every event has a precise occurrence timestamp in UTC. | All temporal reasoning depends on consistent timestamp precision. |
| EC-C-02 | Every event has a registration timestamp (the time the Registry assigned the event_id). | The gap between occurrence and registration is a quality metric. |
| EC-C-03 | The occurrence timestamp is always the actual event occurrence time, not the detection time. | Detecting an event 30 seconds after it occurred does not change when it occurred. |
| EC-C-04 | Delayed events (occurrence time significantly before detection time) are registered with both timestamps. | Both times are analytically relevant. |
| EC-C-05 | Events whose occurrence timestamp is in the future (at registration time) are rejected. | Future-timestamped events are likely errors. |
| EC-C-06 | The Timeline Manager inserts every event at its chronological occurrence position. | Timeline integrity requires occurrence-time ordering. |
| EC-C-07 | Every event has a defined `freshness_sla` — the maximum acceptable detection-to-registration latency for its type. | Timeliness is a quality attribute; violations must be tracked. |
| EC-C-08 | Events detected after their `freshness_sla` are registered with a LATE_DETECTION flag. | Late detection is an operational quality issue that must be visible. |
| EC-C-09 | Expired events (detected after their actionable window) are registered with an EXPIRED flag. | Expired events should not trigger automated actions. |
| EC-C-10 | The system never generates events with synthetic timestamps that differ from actual occurrence times. | Timestamp integrity is absolute; fabricated timestamps are prohibited. |

---

### 9.5 Category D: Structure Rules

| Rule ID | Rule | Rationale |
|---|---|---|
| EC-D-01 | Every event has a type that matches a definition in the Event Catalog. | Typeless events cannot be governed or acted upon correctly. |
| EC-D-02 | Every event has a severity level (1–5). | All events must be categorised by operational impact. |
| EC-D-03 | Every event has a criticality level (CRITICAL / HIGH / MEDIUM / LOW). | Criticality is separate from severity and governs governance response. |
| EC-D-04 | Every event has a confidence score in [0.0, 1.0]. | Uncertainty is a real property of detected events. |
| EC-D-05 | Every event has a category (Market, Corporate, Economic, etc. — Layer 1–15). | Category determines routing, retention, and governance policy. |
| EC-D-06 | Every event has a context payload capturing IIOS state at the time of occurrence. | Events without context cannot be correctly interpreted. |
| EC-D-07 | Every event type defines its mandatory and optional payload fields in the Catalog. | Type-specific schema is required for correct interpretation. |
| EC-D-08 | Events that fail schema validation are rejected and not registered. | Corrupt events are worse than missing events. |
| EC-D-09 | UNCLASSIFIED_EVENT is a valid event type used when automatic classification fails. | The system must handle unknown events without crashing. |
| EC-D-10 | Every event has a `temporal_class` (REAL_TIME / SCHEDULED / DELAYED / HISTORICAL). | Temporal class affects processing mode and priority assignment. |
| EC-D-11 | Every event has a `primary` boolean field (true for primary events; false for derived/composite). | Consumers need to distinguish observations from derivations. |
| EC-D-12 | Composite events include a `pattern_id` referencing the Catalog pattern they matched. | Pattern identification is required for analytics and learning. |

---

### 9.6 Category E: Quality Rules

| Rule ID | Rule | Rationale |
|---|---|---|
| EC-E-01 | Every event's confidence score is computed using the rules defined in the Catalog for its event type. | Consistent confidence computation is required for calibration. |
| EC-E-02 | Events from authoritative, primary data sources have initial confidence ≥ 0.90. | Primary sources are high-confidence by definition. |
| EC-E-03 | Derived events start with a confidence no higher than the minimum confidence of their source events. | Derived events cannot be more certain than their inputs. |
| EC-E-04 | Events with confidence < 0.50 are flagged for Human Principal review before triggering automated financial actions. | Low-confidence events must not drive automated financial decisions. |
| EC-E-05 | Events with confidence < 0.30 do not trigger propagation. | Propagation of very uncertain events spreads uncertainty through the system. |
| EC-E-06 | Event confidence may increase if a confirming signal is received from an independent source. | Confirmation from independent sources increases certainty. |
| EC-E-07 | Every event has a `detection_quality` metadata field recording the quality of the detection process. | Detection quality is separate from event confidence. |
| EC-E-08 | Every event type has a defined `freshness_sla` — events detected after this window are marked LATE_DETECTION. | Timeliness is a quality attribute. |
| EC-E-09 | Duplicate events (same real occurrence arriving from two sources) do not increase event count — they increase the original event's confidence. | Duplicates are confirming signals, not new events. |
| EC-E-10 | Novel events (novelty score > 0.70) require Human Principal review before automated action. | High novelty demands human judgement. |

---

### 9.7 Category F: Lifecycle Rules

| Rule ID | Rule | Rationale |
|---|---|---|
| EC-F-01 | Every event follows the defined lifecycle state machine from DETECTED to RETIRED/ARCHIVED. | Unmanaged event lifecycles create operational uncertainty. |
| EC-F-02 | Events in DETECTION state have no event_id and no Registry record. | An event does not exist until it is registered. |
| EC-F-03 | Events in REGISTERED state are immutable and accessible to all authorised consumers. | Registration creates the permanent record. |
| EC-F-04 | Events in PROCESSING state are being consumed — their state must not be acted upon by additional consumers until CONSUMED. | Concurrent processing of the same event can cause duplicate actions. |
| EC-F-05 | Events in CONSUMED state have had all mandatory consumers acknowledge receipt. | Consumed events have completed their operational cycle. |
| EC-F-06 | Events in SUPERSEDED state are read-only — they were replaced by a correction event. | Superseded records are preserved for audit but must not be acted upon. |
| EC-F-07 | Events in ARCHIVED state are in a lower storage tier — not in hot storage. | Archived events are historical, not operational. |
| EC-F-08 | RETIRED is a terminal state — it is irreversible. | Retirement is final. |
| EC-F-09 | Every lifecycle transition generates an audit event. | Lifecycle changes are governance events. |
| EC-F-10 | Kill switch events immediately bypass all queue depth and rate limits. | Kill switch activation cannot be delayed. |
| EC-F-11 | Cascade lifecycle changes (when a source entity's events are archived) must complete within the same session. | Stale lifecycle states corrupt the historical record. |
| EC-F-12 | Events do not progress from CONSUMED to ARCHIVED during market hours (for market and trading events). | Hot storage retention during market hours ensures instant historical access. |
| EC-F-13 | Incident events do not progress to HISTORICAL until explicitly resolved by the Human Principal. | Incidents must be acknowledged before they are considered closed. |

---

### 9.8 Category G: Audit Rules

| Rule ID | Rule | Rationale |
|---|---|---|
| EC-G-01 | Every event registration generates an EVENT_REGISTERED audit record. | Birth of every event must be permanently recorded. |
| EC-G-02 | Every lifecycle transition generates a LIFECYCLE_TRANSITION audit record. | State changes are governance events. |
| EC-G-03 | Every severity change generates a SEVERITY_CHANGED audit record. | Severity changes affect downstream processing decisions. |
| EC-G-04 | Every confidence change > 0.10 generates a CONFIDENCE_CHANGED audit record. | Significant confidence changes affect operational use. |
| EC-G-05 | Every propagation event generates a PROPAGATION_TRIGGERED audit record. | Propagation chains must be auditable. |
| EC-G-06 | All audit records are hash-chained for tamper detection. | Chain breaks reveal tampering. |
| EC-G-07 | Audit records are never deleted, modified, or overwritten. | Tampered audit records are worthless. |
| EC-G-08 | Financial event audit records are retained for 7 years. | Regulatory compliance. |
| EC-G-09 | Risk event audit records are retained for 10 years. | Risk management compliance. |
| EC-G-10 | Kill switch audit records are retained permanently. | Kill switch activations are the most critical system events. |
| EC-G-11 | Audit chain integrity is verified weekly for all CONFIDENTIAL and RESTRICTED events. | Regular verification detects tampering proactively. |
| EC-G-12 | The Audit Manager never caches event audit records — all reads are from the persistence layer. | Cached audit records can be stale after tampering. |

---

### 9.9 Category H: Governance Rules

| Rule ID | Rule | Rationale |
|---|---|---|
| EC-H-01 | Every event has an owner at all times from registration. | Ownerless events have no accountability. |
| EC-H-02 | Kill switch events require Human Principal confirmation before the kill switch is reset. | Kill switch resets are operational decisions. |
| EC-H-03 | Novel events (novelty score > 0.90) require Human Principal review before automated response. | Completely novel events are outside the system's learned response space. |
| EC-H-04 | Event conflicts (contradictory simultaneous events about the same state) are escalated to Human Principal within 1 hour. | Contradictory events cannot both be acted upon. |
| EC-H-05 | Events are never merged — correction via supersession only. | Merging immutable records violates the immutability principle. |
| EC-H-06 | Event merging requests are always rejected with a documented explanation. | Merging immutable events is architecturally wrong. |
| EC-H-07 | Every CRITICAL governance violation generates an immediate Telegram notification to the Human Principal. | Critical violations demand immediate human awareness. |
| EC-H-08 | The Governance Manager generates a monthly event governance health report. | Regular reporting enables proactive governance. |
| EC-H-09 | Retention policy overrides require documented justification and Human Principal authorisation. | Extending retention has storage cost implications; it must be deliberate. |
| EC-H-10 | Governance policies are per-event-type in the Catalog — generic defaults are insufficient. | Domain-specific governance is required. |
| EC-H-11 | Security access violations (attempts to read RESTRICTED events without authorisation) generate SECURITY_VIOLATION events. | Access control failures must be immediately visible. |
| EC-H-12 | The Governance Manager maintains a governance audit trail separate from the event audit trail. | Governance decisions are themselves auditable records. |
| EC-H-13 | All governance violations are classified by severity before escalation. | Proportionate response requires knowing violation severity. |

---

### 9.10 Category I: Intelligence Rules

| Rule ID | Rule | Rationale |
|---|---|---|
| EC-I-01 | Every event contributes to at least one learning dataset. | No event is informationally sterile. |
| EC-I-02 | Learning signals are extracted from every event within 24 hours of registration. | Timely learning requires timely signal extraction. |
| EC-I-03 | Derived events include their derivation method in metadata. | Traceability of derived intelligence is required. |
| EC-I-04 | Propagation chains are bounded to 15 levels maximum. | Unbounded propagation creates computational intractability. |
| EC-I-05 | Events with confidence < 0.30 do not trigger derived event generation. | Low-confidence events should not propagate uncertainty through the system. |
| EC-I-06 | Root Cause Analysis is performed for all severity 4+ events within 24 hours. | High-severity events demand causal explanation. |
| EC-I-07 | Impact Analysis is performed for all CRITICAL events immediately upon registration. | Critical event impact must be understood before responses are executed. |
| EC-I-08 | Anomaly detection runs on every registered event in real-time. | Anomalies require immediate identification. |
| EC-I-09 | Novel events are flagged immediately upon detection of novelty score > 0.70. | Novel events are operationally significant regardless of their severity. |
| EC-I-10 | The Evolution Manager reviews detection quality metrics monthly and proposes rule improvements. | Continuous improvement of detection quality is mandatory. |
| EC-I-11 | Predictions generated by the Event Prediction capability are advisory only — they do not trigger automated actions. | Predictions are probabilistic; automated action on predictions requires explicit governance approval. |
| EC-I-12 | Correlation results from the Correlation Engine are advisory to the Relationship Engine — they propose relationships; the Relationship Engine decides whether to create them. | The Event Engine and Relationship Engine have defined interfaces; neither overrides the other. |
| EC-I-13 | Cross-market correlation tables are reviewed and updated monthly by the Evolution Manager. | Stale correlations lead to incorrect intelligence. |
| EC-I-14 | Historical similarity analysis must use at least 100 historical analogues for statistical reliability. | Small analogue sets produce unreliable outcome distributions. |
| EC-I-15 | Pattern recognition models are retrained at least monthly using the latest event data. | Event patterns evolve; stale models produce stale intelligence. |
| EC-I-16 | Every propagation chain is logged with its full depth and confidence attenuation. | Propagation chain analytics require complete chain records. |
| EC-I-17 | Event clustering results are available within 60 seconds of the cluster-triggering event. | Cluster intelligence must be timely to be operationally relevant. |

---

### 9.11 Total Rule Count

| Category | Rule count |
|---|---|
| EC-A: Identity | 10 |
| EC-B: Immutability | 7 |
| EC-C: Temporality | 10 |
| EC-D: Structure | 12 |
| EC-E: Quality | 10 |
| EC-F: Lifecycle | 13 |
| EC-G: Audit | 12 |
| EC-H: Governance | 13 |
| EC-I: Intelligence | 17 |
| **TOTAL** | **104 rules** |

---
## PART X — EVENT READINESS CHECKLIST

### 10.1 Checklist Purpose and Structure

The Event Readiness Checklist (ERC) is the definitive gate used to determine whether an event is fully operational within the IIOS. An event that passes all required checks (PASS) is Ready. An event with any FAIL is Not Ready. An event with warnings (WARN) is Conditionally Ready and must be reviewed within 24 hours for real-time events and 7 days for background events.

The ERC has 14 sections. Sections 1 through 8 cover structural and operational readiness. Sections 9 through 14 cover analytical and intelligence readiness.

---

### 10.2 Section 1: Detection Readiness

**Purpose:** Confirms the event was correctly detected — with appropriate latency, from the correct source, and with adequate confidence.

| Check ID | Check | Level |
|---|---|---|
| ERC-1.01 | Event was detected within the `freshness_sla` for its event type | REQUIRED |
| ERC-1.02 | Detection source is recognised and authorised in the Catalog | REQUIRED |
| ERC-1.03 | Detection method is appropriate for the event type | REQUIRED |
| ERC-1.04 | Detection signal was not a false positive (confirmed by second signal or system state) | ADVISORY |
| ERC-1.05 | Occurrence timestamp is accurate and matches the actual event occurrence | REQUIRED |
| ERC-1.06 | Detection latency (occurrence to detection) is within acceptable bounds | REQUIRED |
| ERC-1.07 | Duplicate detection ran and confirmed this is not a duplicate signal | REQUIRED |
| ERC-1.08 | For composite events: all component signals were received within the pattern window | REQUIRED |
| ERC-1.09 | For scheduled events: event fired within ±5 seconds of scheduled time | REQUIRED for scheduled |
| ERC-1.10 | Detection quality metadata is recorded | ADVISORY |

**Section 1 Result:** PASS if all REQUIRED checks pass. WARN if ADVISORY checks fail. FAIL if any REQUIRED check fails.

---

### 10.3 Section 2: Validation Readiness

**Purpose:** Confirms the event passed all validation layers.

| Check ID | Check | Level |
|---|---|---|
| ERC-2.01 | Structural validation passed: all mandatory fields present | REQUIRED |
| ERC-2.02 | Structural validation passed: all fields within valid types and ranges | REQUIRED |
| ERC-2.03 | Semantic validation passed: severity is within allowed range for type | REQUIRED |
| ERC-2.04 | Semantic validation passed: confidence is in [0.0, 1.0] | REQUIRED |
| ERC-2.05 | Semantic validation passed: criticality matches Catalog rules for event type | REQUIRED |
| ERC-2.06 | Referential validation passed: source entity exists if event references an entity | REQUIRED |
| ERC-2.07 | Temporal validation passed: occurrence timestamp ≤ detection timestamp | REQUIRED |
| ERC-2.08 | Contextual validation passed: event context is coherent with registered system state | ADVISORY |
| ERC-2.09 | Payload schema validation passed against Catalog type definition | REQUIRED |
| ERC-2.10 | Validation record stored and accessible | REQUIRED |
| ERC-2.11 | Validation result was PASS (not WARN or FAIL) | REQUIRED |

**Section 2 Result:** PASS if ERC-2.01 through ERC-2.09 and ERC-2.10, ERC-2.11 pass. WARN if ERC-2.08 fails. FAIL if any REQUIRED check fails.

---

### 10.4 Section 3: Classification Readiness

**Purpose:** Confirms the event has been definitively and correctly classified.

| Check ID | Check | Level |
|---|---|---|
| ERC-3.01 | Event type is assigned and found in the Catalog | REQUIRED |
| ERC-3.02 | If UNCLASSIFIED_EVENT: Human Principal review is pending | REQUIRED |
| ERC-3.03 | Severity (1–5) is assigned | REQUIRED |
| ERC-3.04 | Criticality (CRITICAL/HIGH/MEDIUM/LOW) is assigned | REQUIRED |
| ERC-3.05 | Category (Layer 1–15) is assigned | REQUIRED |
| ERC-3.06 | Temporal class (REAL_TIME/SCHEDULED/DELAYED/HISTORICAL) is assigned | REQUIRED |
| ERC-3.07 | Primary/Derived/Composite classification is set | REQUIRED |
| ERC-3.08 | Classification confidence is ≥ 0.70 | REQUIRED |
| ERC-3.09 | For composite events: pattern_id is assigned | REQUIRED for composite |
| ERC-3.10 | Classification model version is recorded | ADVISORY |
| ERC-3.11 | Alternative classification candidates are recorded (top 3) | ADVISORY |

**Section 3 Result:** PASS if applicable REQUIRED checks pass. WARN if ADVISORY checks fail. FAIL if any REQUIRED check fails.

---

### 10.5 Section 4: Prioritisation Readiness

**Purpose:** Confirms the event has been correctly prioritised for processing.

| Check ID | Check | Level |
|---|---|---|
| ERC-4.01 | Priority score is assigned | REQUIRED |
| ERC-4.02 | Priority lane is assigned (EMERGENCY/HIGH/STANDARD/BACKGROUND) | REQUIRED |
| ERC-4.03 | Severity 5 events are in EMERGENCY lane | REQUIRED for sev 5 |
| ERC-4.04 | Kill switch events have maximum priority | REQUIRED for kill switch |
| ERC-4.05 | Priority score matches severity and criticality per the priority formula | REQUIRED |
| ERC-4.06 | Anti-starvation age bonus is applied correctly for aged events | ADVISORY |
| ERC-4.07 | System state modifier is applied during elevated risk periods | ADVISORY |

**Section 4 Result:** PASS if ERC-4.01 through ERC-4.05 pass. WARN if ADVISORY checks fail. FAIL if any REQUIRED check fails.

---

### 10.6 Section 5: Registration Readiness

**Purpose:** Confirms the event is permanently and correctly registered in the Registry.

| Check ID | Check | Level |
|---|---|---|
| ERC-5.01 | event_id (UUID4) is assigned | REQUIRED |
| ERC-5.02 | Reference ID is assigned (format: EVT-{CAT}-{DATE}-{SEQ}) | REQUIRED |
| ERC-5.03 | Event record is persisted to the Registry | REQUIRED |
| ERC-5.04 | Event record is persisted to the immutable event store | REQUIRED |
| ERC-5.05 | Immutable hash (SHA-256) is computed and stored | REQUIRED |
| ERC-5.06 | Hash is verified immediately after storage (read-back verify) | REQUIRED |
| ERC-5.07 | Registration timestamp is recorded | REQUIRED |
| ERC-5.08 | Event appears in the type index | REQUIRED |
| ERC-5.09 | Event appears in the entity index (if entity-linked) | REQUIRED |
| ERC-5.10 | Event appears in the temporal index | REQUIRED |
| ERC-5.11 | Ownership is assigned | REQUIRED |
| ERC-5.12 | Governance policy is assigned | REQUIRED |
| ERC-5.13 | Lifecycle state is set to REGISTERED | REQUIRED |

**Section 5 Result:** PASS if all REQUIRED checks pass. FAIL if any REQUIRED check fails.

---

### 10.7 Section 6: Indexing Readiness

**Purpose:** Confirms the event is correctly indexed for all access patterns.

| Check ID | Check | Level |
|---|---|---|
| ERC-6.01 | Event appears in the search index (full-text searchable) | REQUIRED |
| ERC-6.02 | Event is retrievable by event_id | REQUIRED |
| ERC-6.03 | Event is retrievable by event type | REQUIRED |
| ERC-6.04 | Event is retrievable by time range | REQUIRED |
| ERC-6.05 | Event is retrievable by source entity (if entity-linked) | REQUIRED |
| ERC-6.06 | Event is retrievable by severity | REQUIRED |
| ERC-6.07 | Event appears in the Timeline Manager's temporal index at the correct position | REQUIRED |
| ERC-6.08 | Event appears in the correlation group index (if assigned to a correlation group) | REQUIRED |
| ERC-6.09 | Event cache entry exists or is scheduled for population | ADVISORY |
| ERC-6.10 | Search index consistency check passed (all index entries reference the same event record) | REQUIRED |

**Section 6 Result:** PASS if ERC-6.01 through ERC-6.08 and ERC-6.10 pass. WARN if ERC-6.09 fails. FAIL if any REQUIRED check fails.

---

### 10.8 Section 7: Governance Readiness

**Purpose:** Confirms the event satisfies all governance requirements.

| Check ID | Check | Level |
|---|---|---|
| ERC-7.01 | Owner is assigned | REQUIRED |
| ERC-7.02 | Owner is authorised for this event type | REQUIRED |
| ERC-7.03 | Governance policy is assigned per Catalog rules | REQUIRED |
| ERC-7.04 | Sensitivity classification is set (PUBLIC/INTERNAL/CONFIDENTIAL/RESTRICTED) | REQUIRED |
| ERC-7.05 | Retention policy is assigned | REQUIRED |
| ERC-7.06 | Audit level (FULL/STANDARD/MINIMAL) is set | REQUIRED |
| ERC-7.07 | For approval-required events: approval is received | REQUIRED |
| ERC-7.08 | No open conflicts (contradictory events) unresolved | REQUIRED |
| ERC-7.09 | Compliance schedule assigned for this event category | ADVISORY |
| ERC-7.10 | For CRITICAL events: secondary owner (Human Principal) is set | REQUIRED for CRITICAL |
| ERC-7.11 | Governance metadata record is complete and accessible | REQUIRED |

**Section 7 Result:** PASS if applicable REQUIRED checks pass. WARN if ERC-7.09 fails. FAIL if any REQUIRED check fails.

---

### 10.9 Section 8: Audit Readiness

**Purpose:** Confirms the event has a complete and valid audit trail.

| Check ID | Check | Level |
|---|---|---|
| ERC-8.01 | EVENT_REGISTERED audit record exists | REQUIRED |
| ERC-8.02 | EVENT_REGISTERED record has all required fields (event_id, actor, timestamp, state) | REQUIRED |
| ERC-8.03 | Audit chain starts with this event's registration | REQUIRED |
| ERC-8.04 | Audit records are hash-chained | REQUIRED |
| ERC-8.05 | Hash chain integrity check passes | REQUIRED |
| ERC-8.06 | Retention policy is applied to audit records | REQUIRED |
| ERC-8.07 | Audit records are stored in the correct tier for sensitivity level | REQUIRED |
| ERC-8.08 | Audit trail is accessible via the Audit Service | REQUIRED |
| ERC-8.09 | Propagation chain audit records exist (if event triggered derived events) | REQUIRED |
| ERC-8.10 | Last audit read timestamp is tracked | ADVISORY |

**Section 8 Result:** PASS if ERC-8.01 through ERC-8.09 pass. WARN if ERC-8.10 fails. FAIL if any REQUIRED check fails.

---

### 10.10 Section 9: Propagation Readiness

**Purpose:** Confirms the event has been correctly propagated to downstream consumers and derived events.

| Check ID | Check | Level |
|---|---|---|
| ERC-9.01 | Propagation rules evaluated for this event type | REQUIRED |
| ERC-9.02 | All applicable derived events were generated | REQUIRED |
| ERC-9.03 | Propagation chain depth is within limit (≤ 15) | REQUIRED |
| ERC-9.04 | No propagation loops detected | REQUIRED |
| ERC-9.05 | Propagation chain record is stored in metadata | REQUIRED |
| ERC-9.06 | All mandatory consumers received the event | REQUIRED |
| ERC-9.07 | Consumer delivery confirmations received | REQUIRED |
| ERC-9.08 | Dead letter events (failed deliveries) were alerted | REQUIRED if any |
| ERC-9.09 | Propagation latency within defined SLA | ADVISORY |
| ERC-9.10 | Propagation confidence attenuation applied correctly at each level | ADVISORY |

**Section 9 Result:** PASS if ERC-9.01 through ERC-9.08 pass. WARN if ADVISORY checks fail. FAIL if any REQUIRED check fails.

---

### 10.11 Section 10: Searchability Readiness

**Purpose:** Confirms the event is fully discoverable through all search channels.

| Check ID | Check | Level |
|---|---|---|
| ERC-10.01 | Event is retrievable by exact event_id lookup | REQUIRED |
| ERC-10.02 | Event is retrievable by time range query | REQUIRED |
| ERC-10.03 | Event is retrievable by type query | REQUIRED |
| ERC-10.04 | Event is retrievable by entity query (if entity-linked) | REQUIRED |
| ERC-10.05 | Event payload content is full-text indexed | REQUIRED |
| ERC-10.06 | Event appears in faceted search across type, severity, and category | REQUIRED |
| ERC-10.07 | Search performance: event_id lookup < 1 ms | ADVISORY |
| ERC-10.08 | Search performance: type + date query < 50 ms | ADVISORY |
| ERC-10.09 | Event metadata is included in search results | ADVISORY |

**Section 10 Result:** PASS if ERC-10.01 through ERC-10.06 pass. WARN if ADVISORY checks fail. FAIL if any REQUIRED check fails.

---

### 10.12 Section 11: Reasoning Readiness

**Purpose:** Confirms the event can be used as input to reasoning and intelligence operations.

| Check ID | Check | Level |
|---|---|---|
| ERC-11.01 | Event confidence ≥ 0.50 (minimum for reasoning input) | REQUIRED |
| ERC-11.02 | Event context payload is complete and coherent | REQUIRED |
| ERC-11.03 | Event is resolvable by the Reasoning Manager | REQUIRED |
| ERC-11.04 | For causal reasoning: CAUSED_BY relationships are established or in review | REQUIRED for causal |
| ERC-11.05 | Impact Analysis has been triggered (for severity ≥ 3 events) | REQUIRED for sev 3+ |
| ERC-11.06 | Root Cause Analysis has been triggered (for severity ≥ 4 events) | REQUIRED for sev 4+ |
| ERC-11.07 | Historical similarity search has been run | ADVISORY |
| ERC-11.08 | Novelty score has been computed | ADVISORY |
| ERC-11.09 | Anomaly detection has been run | REQUIRED |
| ERC-11.10 | For novel events (novelty score > 0.70): Human Principal review is pending | REQUIRED |

**Section 11 Result:** PASS if applicable REQUIRED checks pass. WARN if ADVISORY checks fail. FAIL if any REQUIRED check fails.

---

### 10.13 Section 12: Learning Readiness

**Purpose:** Confirms the event is correctly configured for learning system consumption.

| Check ID | Check | Level |
|---|---|---|
| ERC-12.01 | Learning signals are scheduled for extraction | REQUIRED |
| ERC-12.02 | Event is registered with the Learning Service | REQUIRED |
| ERC-12.03 | Event payload is in the format expected by the relevant learning datasets | REQUIRED |
| ERC-12.04 | Event context is in the format expected for regime learning | REQUIRED |
| ERC-12.05 | For strategy-relevant events: strategy performance tracker notified | REQUIRED |
| ERC-12.06 | Evolution Manager has registered this event type for monitoring | REQUIRED |
| ERC-12.07 | Detection quality metadata is available for calibration | ADVISORY |
| ERC-12.08 | Classification quality metadata is available for calibration | ADVISORY |

**Section 12 Result:** PASS if ERC-12.01 through ERC-12.06 pass. WARN if ADVISORY checks fail. FAIL if any REQUIRED check fails.

---

### 10.14 Section 13: Historical Readiness

**Purpose:** Confirms the event is correctly stored and indexed for long-term historical analysis.

| Check ID | Check | Level |
|---|---|---|
| ERC-13.01 | Event is in the correct storage tier for its age | REQUIRED |
| ERC-13.02 | Event is accessible via the Timeline Service for its occurrence time | REQUIRED |
| ERC-13.03 | Event is included in the historical analytics datasets | REQUIRED |
| ERC-13.04 | For temporal events: event appears at correct position in chronological timeline | REQUIRED |
| ERC-13.05 | For point-in-time queries at the event's timestamp: event appears in state reconstruction | REQUIRED |
| ERC-13.06 | Event is available for historical replay operations | REQUIRED |
| ERC-13.07 | Archive tier access latency within SLA (< 500ms for cold; < 5s for permanent) | ADVISORY |
| ERC-13.08 | Retention expiry date is set correctly | REQUIRED |

**Section 13 Result:** PASS if applicable REQUIRED checks pass. WARN if ADVISORY checks fail. FAIL if any REQUIRED check fails.

---

### 10.15 Section 14: Future Readiness

**Purpose:** Confirms the event contributes to the system's forward-looking intelligence capabilities.

| Check ID | Check | Level |
|---|---|---|
| ERC-14.01 | Event is added to the prediction model's training dataset | REQUIRED |
| ERC-14.02 | Event is added to the pattern recognition model's training dataset | REQUIRED |
| ERC-14.03 | Event is added to the cross-market correlation tracking dataset | REQUIRED |
| ERC-14.04 | Event is included in the temporal correlation computation | REQUIRED |
| ERC-14.05 | Event is registered with the Evolution Manager for rule improvement analysis | REQUIRED |
| ERC-14.06 | If the event type has a prediction model: the event's outcome is fed back to update the model | ADVISORY |
| ERC-14.07 | Event is included in the next scheduled correlation update | ADVISORY |
| ERC-14.08 | Event's novelty score is recorded for calibration of the novelty detection model | REQUIRED |
| ERC-14.09 | Event's propagation chain is available for propagation rule improvement analysis | REQUIRED |

**Section 14 Result:** PASS if ERC-14.01 through ERC-14.05, ERC-14.08, ERC-14.09 pass. WARN if ADVISORY checks fail. FAIL if any REQUIRED check fails.

---

### 10.16 Overall Event Readiness Classification

| Classification | Criteria | Operational status |
|---|---|---|
| FULLY READY | All 14 sections PASS | Full operational use permitted |
| CONDITIONALLY READY | All sections PASS or WARN; no FAIL | Operational use permitted; WARN items reviewed within 24h (real-time) or 7 days (background) |
| NOT READY | Any REQUIRED check FAIL in any section | Event must not be used in automated decisions until FAIL resolved |
| CRITICALLY NOT READY | 3+ FAIL in Registration, Validation, Governance, or Audit sections | Immediate Human Principal notification required |

**Critical path sections:** Sections 2 (Validation), 5 (Registration), 7 (Governance), and 8 (Audit) are always evaluated first. FAIL in any of these four sections automatically triggers NOT READY regardless of other sections.

---
---

## SUPPLEMENT A — EVENT TYPE CATALOGUE SUMMARY

This supplement provides a consolidated reference of all key event types across all 15 categories, with their severity, detection mode, and freshness SLA.

### A.1 Market Events (Layer 1)

| Event type | Default severity | Detection mode | Freshness SLA |
|---|---|---|---|
| PRICE_TICK | 1 | STREAMING | < 100 ms |
| PRICE_THRESHOLD_CROSSED | 3 | REAL_TIME | < 200 ms |
| PRICE_GAP_UP | 3 | REAL_TIME | < 500 ms |
| PRICE_GAP_DOWN | 3 | REAL_TIME | < 500 ms |
| VOLUME_SPIKE | 3 | REAL_TIME | < 500 ms |
| VOLATILITY_SPIKE | 4 | REAL_TIME | < 200 ms |
| REGIME_TRANSITION | 5 | DERIVED | < 2 seconds |
| CIRCUIT_BREAKER_TRIGGERED | 5 | REAL_TIME | < 100 ms |
| MARKET_OPEN | 3 | SCHEDULED | ± 5 seconds |
| MARKET_CLOSE | 3 | SCHEDULED | ± 5 seconds |
| BREADTH_COLLAPSE | 4 | COMPOSITE | < 1 second |
| VOLATILITY_REGIME_CHANGE | 4 | DERIVED | < 5 seconds |
| INTRADAY_HIGH | 2 | REAL_TIME | < 500 ms |
| INTRADAY_LOW | 2 | REAL_TIME | < 500 ms |

### A.2 Corporate Events (Layer 2)

| Event type | Default severity | Detection mode | Freshness SLA |
|---|---|---|---|
| EARNINGS_ANNOUNCED | 4 | SCHEDULED | < 5 seconds |
| EARNINGS_SURPRISE_POSITIVE | 4 | DERIVED | < 10 seconds |
| EARNINGS_SURPRISE_NEGATIVE | 4 | DERIVED | < 10 seconds |
| DIVIDEND_DECLARED | 3 | REAL_TIME | < 1 minute |
| STOCK_SPLIT | 3 | SCHEDULED | < 1 minute |
| ACQUISITION_ANNOUNCED | 5 | REAL_TIME | < 5 seconds |
| CEO_CHANGE | 4 | REAL_TIME | < 1 minute |
| INSIDER_BUY | 3 | REAL_TIME | < 5 minutes |
| INSIDER_SELL | 3 | REAL_TIME | < 5 minutes |
| RATING_UPGRADE | 3 | REAL_TIME | < 1 minute |
| RATING_DOWNGRADE | 4 | REAL_TIME | < 1 minute |
| REGULATORY_ACTION | 5 | REAL_TIME | < 30 seconds |

### A.3 Economic Events (Layer 3)

| Event type | Default severity | Detection mode | Freshness SLA |
|---|---|---|---|
| GDP_RELEASED | 5 | SCHEDULED | < 2 seconds |
| CPI_RELEASED | 5 | SCHEDULED | < 2 seconds |
| WPI_RELEASED | 4 | SCHEDULED | < 5 seconds |
| MANUFACTURING_PMI | 4 | SCHEDULED | < 5 seconds |
| TRADE_BALANCE_RELEASED | 3 | SCHEDULED | < 5 seconds |
| UNEMPLOYMENT_RELEASED | 4 | SCHEDULED | < 5 seconds |
| IIP_RELEASED | 3 | SCHEDULED | < 5 seconds |

### A.4 Central Bank Events (Layer 5)

| Event type | Default severity | Detection mode | Freshness SLA |
|---|---|---|---|
| RBI_RATE_DECISION | 5 | SCHEDULED | < 2 seconds |
| RATE_CUT | 5 | DERIVED | < 5 seconds |
| RATE_HIKE | 5 | DERIVED | < 5 seconds |
| SURPRISE_RATE_CHANGE | 5 | REAL_TIME | < 2 seconds |
| MONETARY_POLICY_STATEMENT | 4 | SCHEDULED | < 5 seconds |
| MPC_MINUTES_RELEASED | 3 | SCHEDULED | < 1 minute |
| QUANTITATIVE_EASING_ANNOUNCED | 5 | REAL_TIME | < 5 seconds |

### A.5 Trading Events (Layer 8)

| Event type | Default severity | Detection mode | Freshness SLA |
|---|---|---|---|
| ORDER_CREATED | 3 | REAL_TIME | < 50 ms |
| ORDER_SUBMITTED | 3 | REAL_TIME | < 50 ms |
| ORDER_FILLED | 4 | REAL_TIME | < 50 ms |
| ORDER_PARTIALLY_FILLED | 3 | REAL_TIME | < 50 ms |
| ORDER_CANCELLED | 3 | REAL_TIME | < 100 ms |
| ORDER_REJECTED | 4 | REAL_TIME | < 50 ms |
| POSITION_OPENED | 4 | REAL_TIME | < 100 ms |
| POSITION_CLOSED | 4 | REAL_TIME | < 100 ms |
| SLIPPAGE_DETECTED | 3 | REAL_TIME | < 200 ms |
| BROKER_REJECTION | 4 | REAL_TIME | < 100 ms |

### A.6 Risk Events (Layer 10)

| Event type | Default severity | Detection mode | Freshness SLA |
|---|---|---|---|
| POSITION_LIMIT_APPROACHED | 4 | REAL_TIME | < 100 ms |
| POSITION_LIMIT_BREACHED | 5 | REAL_TIME | < 50 ms |
| DAILY_LOSS_LIMIT_BREACHED | 5 | REAL_TIME | < 50 ms |
| VIX_SPIKE | 4 | REAL_TIME | < 200 ms |
| MAX_DRAWDOWN_BREACHED | 5 | REAL_TIME | < 50 ms |
| KILL_SWITCH_TRIGGERED | 5 | REAL_TIME | < 50 ms |
| KILL_SWITCH_RESET | 5 | REAL_TIME | < 100 ms |
| TRAILING_STOP_TRIGGERED | 4 | REAL_TIME | < 100 ms |
| MARGIN_CALL_RECEIVED | 5 | REAL_TIME | < 50 ms |
| STRESS_SCENARIO_ACTIVATED | 4 | DERIVED | < 1 second |

### A.7 AI and Decision Events (Layers 11, 15)

| Event type | Default severity | Detection mode | Freshness SLA |
|---|---|---|---|
| AGENT_DECISION_MADE | 3 | REAL_TIME | < 200 ms |
| HYPOTHESIS_CREATED | 3 | REAL_TIME | < 500 ms |
| HYPOTHESIS_VALIDATED | 3 | DERIVED | < 1 second |
| DEBATE_CONCLUDED | 3 | REAL_TIME | < 500 ms |
| AGENT_CONFIDENCE_CHANGED | 2 | REAL_TIME | < 500 ms |
| STRATEGY_SELECTED | 4 | REAL_TIME | < 200 ms |
| EXECUTION_AUTHORISED | 4 | REAL_TIME | < 100 ms |
| HUMAN_OVERRIDE | 5 | REAL_TIME | < 100 ms |
| DECISION_ESCALATED | 4 | REAL_TIME | < 200 ms |

### A.8 System Events (Layer 13)

| Event type | Default severity | Detection mode | Freshness SLA |
|---|---|---|---|
| BROKER_DISCONNECTED | 5 | REAL_TIME | < 200 ms |
| BROKER_CONNECTED | 3 | REAL_TIME | < 200 ms |
| FEED_DISCONNECTED | 4 | REAL_TIME | < 500 ms |
| LATENCY_CRITICAL | 4 | REAL_TIME | < 500 ms |
| TAMPER_DETECTED | 5 | REAL_TIME | < 100 ms |
| AUDIT_CHAIN_BROKEN | 5 | REAL_TIME | < 100 ms |
| SYSTEM_STARTUP | 3 | REAL_TIME | < 1 second |
| SYSTEM_SHUTDOWN | 3 | REAL_TIME | < 1 second |
| PROPAGATION_LOOP_DETECTED | 4 | REAL_TIME | < 200 ms |
| GOVERNANCE_VIOLATION_DETECTED | 4 | REAL_TIME | < 500 ms |

---

## SUPPLEMENT B — COMPONENT INTERFACE REFERENCE

| Component | Primary input | Primary output | Latency target | Failure mode |
|---|---|---|---|---|
| Event Registry | Event draft + registration request | event_id + confirmation | < 5 ms write | FAIL_FAST on corrupt input; FAIL_SAFE on read |
| Event Catalog | Type name / category | Type definition | < 1 ms | Static cache — never fails |
| Event Factory | Raw signal | Event draft | < 5 ms | FAIL_FAST on invalid type |
| Event Detector | Data streams / triggers | Event signals | < 100 ms | FAIL_SAFE per feed; continue on partial |
| Ingestion Manager | Raw signals | Normalised signals | < 10 ms | FAIL_SAFE; buffer overflow → priority drop |
| Classification Engine | Event draft | Classified draft | < 10 ms | Fallback to rule-based on ML failure |
| Validator | Event draft | PASS / FAIL result | < 5 ms | FAIL_FAST on structural; FAIL_SAFE on contextual |
| Identity Manager | Any identifier | Canonical event_id | < 2 ms | FAIL_FAST on unresolvable |
| Metadata Manager | event_id + metadata | Metadata record | < 5 ms | FAIL_SAFE on read |
| Correlation Engine | Event stream | Correlation groups | < 30 seconds | FAIL_SAFE — advisory |
| Propagation Engine | Registered event | Derived signals | < 200 ms | FAIL_SAFE — log; continue |
| Dependency Engine | Event + prereqs | Dependency result | < 10 ms | FAIL_SAFE — release with DEGRADED flag |
| Priority Manager | Event + state | Priority score | < 2 ms | Fallback to severity-based |
| Queue Manager | Events + priorities | Delivered events | < 50 ms (EMERGENCY) | Retry 3x; then dead letter |
| Timeline Manager | Events | Timeline index | < 10 ms insert | FAIL_SAFE — insert async |
| Lifecycle Manager | State transition | State update | < 5 ms | FAIL_FAST on invalid transition |
| Audit Manager | Lifecycle events | Audit records | < 10 ms | NEVER_FAIL — queued with retry |
| Governance Manager | Events + policies | Policy assignments | < 10 ms | Default restrictive policy on failure |
| Search Engine | Queries | Result lists | < 50 ms (structured) | FAIL_SAFE — return partial |
| Analytics Manager | Event stream | Analytics reports | < 500 ms | FAIL_SAFE — advisory |
| Archive Manager | Archive requests | Archive confirmations | < 100 ms | Retain in tier; retry |
| Evolution Manager | Analytics + feedback | Evolution signals | < 30 min | FAIL_SAFE — advisory |

---

## SUPPLEMENT C — PROCESSING PIPELINE PATTERNS

### C.1 Pattern: Kill Switch Event Pipeline

**Trigger:** DAILY_LOSS_LIMIT_BREACHED (severity 5, CRITICAL)

```
Risk Guardian detects: daily loss > 2%
    │
    │ (< 50 ms)
    ▼
Detector signal → Ingestion Manager [EMERGENCY bypass]
    │
    │ (< 10 ms)
    ▼
Factory [pre-built template] → Validator [simplified check]
    │
    │ (< 5 ms)
    ▼
Registry [priority persist] → Queue Manager [EMERGENCY lane]
    │
    │ (< 5 ms)
    ▼
Risk Guardian (primary consumer): KILL_SWITCH_TRIGGERED event generated
    │
    │ (< 50 ms)
    ▼
Kill switch activates: all new order creation blocked
    │
    │ (parallel)
    ▼
Notification Service: Telegram alert → Human Principal
    │
    ▼
Total: < 200 ms from detection to kill switch activation
```

---

### C.2 Pattern: Scheduled Economic Data Release Pipeline

**Trigger:** GDP_RELEASED (severity 5, scheduled at 05:30 IST)

```
T-30 minutes: Context pre-build
    ├── Portfolio state snapshot
    ├── Current regime
    └── Pre-evaluated propagation chain

T=0: GDP data released
    │
    ▼
Detector: validates data against expected format
    │
    ▼
Factory: enriches with pre-built context (< 1 ms — context ready)
    │
    ▼
Registry: registered; propagation triggered
    │
    ├── DERIVED: REGIME_SHIFT_SIGNAL (if GDP ≠ consensus)
    ├── DERIVED: CURRENCY_IMPACT (INR/USD effect)
    └── DERIVED: SECTOR_ROTATION_SIGNAL (if GDP direction clear)
    │
    ▼
Consumers: Market Intelligence, Strategy Layer, Risk Engine
    │
    ▼
Total detection-to-consumption: < 2 seconds
```

---

### C.3 Pattern: Composite Market Crash Detection

**Trigger:** MARKET_CRASH composite event

**Required components (all within 30-minute window):**
- NIFTY50 decline > 3% (PRICE_THRESHOLD_CROSSED)
- Volume > 2× 20-day average (VOLUME_SPIKE)
- Advance-Decline ratio < 0.10 (BREADTH_COLLAPSE)
- VIX > 30 (VOLATILITY_SPIKE)

```
Detection accumulator (rolling 30-minute window):
    T+0m: VOLUME_SPIKE detected ────────────────────► partial match (1/4)
    T+5m: NIFTY PRICE_THRESHOLD_CROSSED ────────────► partial match (2/4)
    T+12m: BREADTH_COLLAPSE detected ───────────────► partial match (3/4)
    T+18m: VOLATILITY_SPIKE: VIX > 30 ─────────────► PATTERN COMPLETE (4/4)
                │
                ▼
    MARKET_CRASH composite event created
    severity: 5, criticality: CRITICAL
    source_event_ids: [vol_spike_id, price_id, breadth_id, vix_id]
    confidence: min(component confidences) = 0.88
                │
                ├──► KILL_SWITCH_RISK alert (derived)
                ├──► PORTFOLIO_DEFENSIVE_SIGNAL (derived)
                └──► Human Principal Telegram: "Market crash pattern detected"
```

---

### C.4 Pattern: Learning Feedback Loop

**Trigger:** Strategy performance outcome (WIN/LOSS)

```
STRATEGY_A generates HYPOTHESIS_H
    │
    ▼
ORDER_CREATED → ORDER_FILLED → POSITION_OPENED
    │
    [time passes — position evolves]
    │
    ▼
POSITION_CLOSED → REALISED_PNL_RECORDED
    │
    ├── [WIN] → POSITIVE_OUTCOME event
    │               │
    │               ▼
    │           Learning Service:
    │           - HYPOTHESIS_H reinforced
    │           - STRATEGY_A win rate updated +1
    │           - All upstream events tagged: POSITIVE_OUTCOME_LINK
    │
    └── [LOSS] → NEGATIVE_OUTCOME event
                    │
                    ▼
                Learning Service:
                - HYPOTHESIS_H weakened
                - STRATEGY_A win rate updated -1
                - Root Cause Analysis triggered
                - Evolution Manager: review detection/classification quality
```

---

## SUPPLEMENT D — INTELLIGENCE FRAMEWORK REFERENCE

### D.1 Root Cause Analysis Reference

| Analysis parameter | Value |
|---|---|
| Maximum lookback window | 6 hours |
| Minimum causal confidence for inclusion | 0.70 |
| Maximum causal chain depth | 10 |
| Maximum root candidates returned | 5 |
| Required trigger severity | 4+ |
| Computation time target | < 30 seconds |

### D.2 Impact Analysis Dimensions and Weights

| Dimension | Weight in composite impact score |
|---|---|
| Portfolio P&L impact | 0.30 |
| Risk metric change | 0.25 |
| Strategy count affected | 0.20 |
| Entity count affected | 0.15 |
| Temporal impact duration | 0.10 |

### D.3 Novelty Detection Thresholds

| Novelty score | Classification | System response |
|---|---|---|
| 0.90–1.00 | COMPLETELY_NOVEL | Human Principal immediate; no automated action |
| 0.70–0.89 | HIGHLY_NOVEL | Human Principal notification; conservative response |
| 0.50–0.69 | SOMEWHAT_NOVEL | Telegram alert; standard response with monitoring |
| 0.00–0.49 | PRECEDENTED | No novelty response; standard processing |

### D.4 Anomaly Detection Model Reference

| Model | Trigger threshold | ANOMALY_DETECTED generated? |
|---|---|---|
| Univariate Z-score | > 3σ | Yes if > 4σ |
| Multivariate Mahalanobis | > 3σ | Yes if > 4σ |
| Isolation Forest | Top 5% isolation | Yes if top 1% |
| Temporal anomaly | > 2× historical std in timing | Yes if > 3× |
| Frequency anomaly | > 3σ from historical frequency | Yes |

### D.5 Temporal Correlation Lag Reference

| Trigger event | Affected event | Typical lag τ | Correlation strength |
|---|---|---|---|
| RBI_RATE_CUT | BOND_YIELD_FALL | 0–30 minutes | 0.92 |
| RBI_RATE_CUT | BANKING_SECTOR_RALLY | 30–120 minutes | 0.85 |
| GDP_SURPRISE_POSITIVE | NIFTY_RALLY | 0–60 minutes | 0.75 |
| US_FED_HIKE | NIFTY_DECLINE | 4–8 hours (next day) | 0.65 |
| OIL_SPIKE > 5% | OMC_SELLOFF | 30–120 minutes | 0.80 |
| VIX_SPIKE > 30 | FII_OUTFLOW | 1–3 days | 0.70 |

---

## SUPPLEMENT E — GOVERNANCE DECISION RECORDS

### GDR-001: Events Are Immutable After Registration

**Date:** 2026-Q2  
**Decision:** No event record may be modified after registration. Corrections must be made through supersession.  
**Rationale:** Financial and regulatory audit requirements demand that the historical record be unaltered. A modifiable event system cannot be trusted as an audit source. The additional complexity of supersession is a necessary cost for audit integrity.  
**Implications:** The Registry must reject all write operations to registered event records. Correction workflows must create supersession events.

---

### GDR-002: Propagation Depth Limit = 15

**Date:** 2026-Q2  
**Decision:** No event propagation chain may exceed 15 levels of derived events.  
**Rationale:** Unconstrained propagation in a densely connected event graph can cause computational runaway. At 15 hops with a 0.85 confidence attenuation factor, the effective confidence is approximately 0.85^15 ≈ 0.087 — approaching the 0.05 minimum propagation confidence threshold. The limit is therefore both computationally and analytically justified.  
**Implications:** The Propagation Engine must track depth and terminate chains at 15. Every chain termination generates a PROPAGATION_DEPTH_REACHED metadata annotation.

---

### GDR-003: Kill Switch Events Have Absolute Priority

**Date:** 2026-Q2  
**Decision:** KILL_SWITCH_TRIGGERED and DAILY_LOSS_LIMIT_BREACHED events bypass all queue depth limits, rate limits, and priority calculations.  
**Rationale:** The entire purpose of a kill switch is to halt trading before financial damage increases. A kill switch event that waits in a queue because the queue is full has failed its purpose. Absolute priority is a hard requirement.  
**Implications:** The Queue Manager must maintain a separate EMERGENCY bypass path. Rate limiting logic must explicitly exclude severity-5 CRITICAL events.

---

### GDR-004: Events With Confidence < 0.30 Do Not Propagate

**Date:** 2026-Q2  
**Decision:** Events with confidence below 0.30 do not trigger propagation rules.  
**Rationale:** Propagating very uncertain events spreads uncertainty through the system. If an event has 30% confidence (more likely false than true), generating derived events from it would fill the event stream with ~70% spurious signals.  
**Implications:** The Propagation Engine must check confidence before evaluating propagation rules. Low-confidence events are still registered and available for reference — they just do not drive downstream processing.

---

### GDR-005: UNCLASSIFIED_EVENT Is a Valid Type

**Date:** 2026-Q2  
**Decision:** Events that cannot be automatically classified are registered with type UNCLASSIFIED_EVENT rather than rejected.  
**Rationale:** Rejecting unclassifiable events means potentially missing genuinely novel market events. An unclassifiable event may be the first instance of a new event type — rejecting it discards potentially valuable intelligence. Registering it as UNCLASSIFIED_EVENT preserves the record for Human Principal review and Evolution Manager analysis.  
**Implications:** The Classification Engine must not FAIL on no-match. The Governance Manager must flag UNCLASSIFIED_EVENTs for review within 24 hours.

---

### GDR-006: Detection Latency Standards Are Per-Event-Type

**Date:** 2026-Q2  
**Decision:** Each event type in the Catalog defines its own `freshness_sla` (maximum acceptable detection-to-registration latency).  
**Rationale:** A 100 ms latency is entirely acceptable for an annual budget announcement; it is completely unacceptable for an order fill event. A single global latency standard would force either over-engineering the economic calendar processing or under-engineering the trading event processing.  
**Implications:** The Catalog must include `freshness_sla` for every event type. The Audit Manager must track and report SLA violations.

---

## SUPPLEMENT F — ANTI-PATTERN REFERENCE

### F.1 Anti-Pattern: The Mutable Event

**Description:** An event record is modified after registration — perhaps to "fix" a wrong severity or update a price level.

**Symptoms:** Event records with modification timestamps after their registration timestamp; audit trail has gaps between creation and current state.

**Root cause:** Developer bypassed the Registry's immutability enforcement by writing directly to the persistence layer.

**Resolution:** All persistence writes to event records must go through the Registry's write path, which rejects all post-registration modifications. Direct database access for event records must be blocked.

---

### F.2 Anti-Pattern: The Infinite Cascade

**Description:** A propagation rule creates a cycle — Event A triggers Event B, which triggers Event A, causing an infinite loop.

**Symptoms:** Propagation chain growing indefinitely; memory exhaustion; Queue Manager overflow; system latency spike.

**Root cause:** Propagation rules were added to the Catalog without cycle detection validation.

**Resolution:** The Catalog must validate propagation rules for cycles at definition time. The Propagation Engine must track all events generated in a single propagation chain and detect if the same event type appears twice.

---

### F.3 Anti-Pattern: The Confidence Inflation

**Description:** Derived events are assigned higher confidence than their source events — creating a false sense of certainty as events propagate through the system.

**Symptoms:** Fourth-level derived events with confidence 0.95 when the source event had confidence 0.60; risk models using high-confidence derived events that are actually highly uncertain.

**Root cause:** Propagation engine applied a default confidence without accounting for the source event's confidence.

**Resolution:** Every derived event's initial confidence is capped at the minimum confidence of its source events. The Propagation Engine must enforce this cap at creation time.

---

### F.4 Anti-Pattern: The Phantom Timestamp

**Description:** Events are registered with a timestamp that is not the actual occurrence time — perhaps the server time when the message was received rather than when the market event occurred.

**Symptoms:** Timeline Manager shows events out of chronological order relative to their true occurrence; correlation analysis finds events "before" their causes.

**Root cause:** The event source sent the server-side receipt time instead of the actual occurrence time, and the Factory did not validate or correct this.

**Resolution:** Every event source must document its timestamp semantics. The Factory must validate that the timestamp is reasonable given the detection time. If a discrepancy > 10 seconds is detected without explanation, the event is registered with a TIMESTAMP_SUSPICIOUS flag.

---

### F.5 Anti-Pattern: The Missing Context

**Description:** Events are registered without the system context payload — making them impossible to interpret correctly for historical analysis or causal reasoning.

**Symptoms:** Events with empty or null `context` field; historical analysis that cannot determine what regime or risk state existed at event time; causal chains that cannot be validated.

**Root cause:** The Factory context enrichment was bypassed or failed silently.

**Resolution:** Context enrichment is mandatory for all non-TRACE events. If context enrichment fails, the event registration must fail (FAIL_FAST). Alternatively, use a minimal emergency context (only regime and risk level) to avoid complete context failure.

---

### F.6 Anti-Pattern: The Stale Pattern Model

**Description:** The event pattern recognition models are not retrained as market conditions evolve — patterns that were valid in a bull regime continue to fire in a bear regime, generating false signals.

**Symptoms:** Increasing misclassification rate; composite events are detected that human observers do not recognise as valid; historical similarity returns analogues that are clearly inapplicable.

**Root cause:** The Evolution Manager's retraining schedule was not configured, or retraining jobs were failing silently.

**Resolution:** Monthly model retraining is a constitutional requirement (Rule EC-I-15). Retraining job failures must generate LEARNING_JOB_FAILED events at severity 3. The Evolution Manager must alert if pattern model performance metrics (precision, recall) degrade by more than 10% between retraining cycles.

---

### F.7 Anti-Pattern: The Governance Orphan

**Description:** An event exists in the Registry with no owner, no governance policy, and no retention policy assigned.

**Symptoms:** Events with `owner_id: null` or `governance_policy: null` in the Registry; events that never appear in compliance reports.

**Root cause:** The Governance Manager's policy assignment failed at creation time without generating an alert.

**Resolution:** Governance policy assignment is mandatory at registration time. If the Governance Manager is unavailable, the Registry must apply a default INTERNAL-sensitivity, FULL-audit, 2-year-retention policy and log a GOVERNANCE_ASSIGNMENT_FAILED event.

---

### F.8 Anti-Pattern: The Lost Kill Switch

**Description:** A KILL_SWITCH_TRIGGERED event is generated but is lost in a full queue — the kill switch activation is delayed by minutes because the event could not be processed.

**Symptoms:** KILL_SWITCH_TRIGGERED event in the queue with normal priority; continued order creation after the kill switch event was generated.

**Root cause:** The EMERGENCY queue bypass was not implemented correctly — severity 5 events were placed in the standard queue.

**Resolution:** Kill switch events must bypass the standard queue entirely. The Queue Manager must maintain a dedicated EMERGENCY path with a guaranteed maximum latency of 50 ms from event registration to consumer delivery.

---

## SUPPLEMENT G — EVENT GLOSSARY

| Term | Definition |
|---|---|
| Anomaly | An event or observation that is statistically unusual relative to the expected distribution for its type. |
| Audit Chain | The complete, hash-linked sequence of audit records for an event from registration through archival. |
| Cascade | A sequence of events in which each event triggers one or more downstream events. |
| Composite Event | An event defined by the coincidence of multiple simpler events matching a pattern within a time window. |
| Confidence | The system's certainty that an event occurred, was classified correctly, and has accurate payload. |
| Context | The structured state of the IIOS at the time an event occurred — regime, portfolio state, risk levels. |
| Criticality | The operational consequence of missing, misclassifying, or delaying an event — a governance metric. |
| Dead Letter | An event that failed delivery to all registered consumers after retry exhaustion. |
| Derived Event | An event generated analytically from one or more source events — not from direct external observation. |
| Detection Latency | The time elapsed from an event's actual occurrence to its detection by the Event Engine. |
| Event Chain | An ordered sequence of causally or temporally linked events. |
| Event Constitution | The supreme set of 104 mandatory rules governing all events in the IIOS. |
| Event Instance | A specific, recorded occurrence of an event — the unique Registry record. |
| Event Readiness Checklist (ERC) | The 14-section checklist certifying that an event is fully operational in the IIOS. |
| Event Type | The Catalog definition of a class of events — their schema, severity rules, and governance policies. |
| Freshness SLA | The maximum acceptable detection-to-registration latency for a given event type. |
| Governance Decision Record (GDR) | A permanent record documenting a significant architectural or policy decision. |
| Idempotency | The property that receiving the same event signal multiple times produces at most one event record. |
| Immutable Hash | A SHA-256 hash of all event record fields at creation — enables tamper detection. |
| Incident | A high-severity event requiring active management and explicit resolution by the Human Principal. |
| Novelty Score | A measure of how different an event is from all historical events — 1.0 = completely novel. |
| Occurrence Timestamp | The precise UTC time of the actual event occurrence — not the detection or registration time. |
| Pattern Recognition | The process of matching new event sequences against a catalog of known event patterns. |
| Prioritisation | The assignment of processing priority to ensure high-severity events are always processed first. |
| Propagation | The generation of downstream derived events from a primary event via Catalog-defined rules. |
| Propagation Depth | The number of derived event levels generated from a single primary event. |
| Reference ID | Human-readable event identifier in format EVT-{CATEGORY}-{YYYYMMDD}-{SEQUENCE}. |
| Root Cause Analysis (RCA) | The process of identifying the initiating event in a causal chain. |
| Severity | A 1–5 classification of an event's operational impact — 5 = CRITICAL; 1 = TRACE. |
| Signal | A derived analytical output from one or more events indicating something meaningful to a consumer. |
| State Change | The consequence of an event — the transition of an entity or relationship from one state to another. |
| Supersession | The correction mechanism for immutable event records — a new correcting event supersedes the original. |
| Temporal Class | Classification of an event by its time relationship: REAL_TIME, SCHEDULED, DELAYED, HISTORICAL. |
| Trigger | A predefined condition that, when met, causes the Event Detector to generate an event. |

---
---

## DOCUMENT SUMMARY AND MASTER COMPLIANCE CHECKLIST

### Summary Metrics

| Metric | Value |
|---|---|
| Document title | EVENT_ENGINE_ARCHITECTURE.md |
| Version | 1.0 |
| Status | FINAL |
| Total parts | 10 (I–X) |
| Total supplements | 7 (A–G) |
| Event categories | 15 (Layer 0–15) |
| Event types documented | 120+ across all categories |
| Lifecycle stages defined | 13 |
| Engine components specified | 22 |
| Services specified | 15 |
| Constitutional rules | 104 (across 9 categories) |
| Readiness checklist items | 130+ (across 14 sections) |
| Processing modes | 12 |
| Intelligence capabilities | 16 |
| Governance dimensions | 14 |
| Anti-patterns documented | 8 |
| Glossary terms | 34 |
| Governance Decision Records | 6 |
| Priority lanes | 4 (EMERGENCY, HIGH, STANDARD, BACKGROUND) |
| Storage tiers | 4 (HOT, WARM, COLD, PERMANENT) |

---

### Master Compliance Checklist

The following checklist is used during Event Engine audits to confirm the implementation satisfies all architectural requirements.

| Category | Requirement | Status |
|---|---|---|
| Identity | UUID4 event_id assigned at registration | ☐ |
| Identity | Reference ID format EVT-{CAT}-{DATE}-{SEQ} enforced | ☐ |
| Identity | Identity resolution works for all identifier types | ☐ |
| Immutability | Event records rejected for post-registration modification | ☐ |
| Immutability | SHA-256 immutable hash computed and stored | ☐ |
| Immutability | Hash verified on every read | ☐ |
| Immutability | Corrections use supersession, not modification | ☐ |
| Temporality | Occurrence timestamp is actual occurrence time | ☐ |
| Temporality | Registration timestamp is recorded | ☐ |
| Temporality | Future-timestamped events rejected | ☐ |
| Temporality | Freshness SLA tracked per event type | ☐ |
| Structure | Every event has severity (1–5) | ☐ |
| Structure | Every event has criticality (CRITICAL/HIGH/MEDIUM/LOW) | ☐ |
| Structure | Every event has confidence in [0.0, 1.0] | ☐ |
| Structure | Every event has context payload | ☐ |
| Quality | Events with confidence < 0.30 do not propagate | ☐ |
| Quality | Events with confidence < 0.50 flagged before automated action | ☐ |
| Quality | Novel events (> 0.70) require Human Principal review | ☐ |
| Lifecycle | Lifecycle state machine enforced | ☐ |
| Lifecycle | Kill switch events bypass all queue limits | ☐ |
| Lifecycle | Incident events require Human Principal resolution | ☐ |
| Audit | EVENT_REGISTERED audit record created for every event | ☐ |
| Audit | Audit records hash-chained | ☐ |
| Audit | Audit records never deleted or modified | ☐ |
| Audit | Financial event audit retained 7 years | ☐ |
| Audit | Kill switch event audit retained permanently | ☐ |
| Governance | Every event has an owner | ☐ |
| Governance | Kill switch reset requires Human Principal confirmation | ☐ |
| Governance | Event merging is rejected (supersession only) | ☐ |
| Processing | Propagation depth bounded to 15 levels | ☐ |
| Processing | Propagation loops detected and broken | ☐ |
| Processing | Kill switch events in EMERGENCY bypass path | ☐ |
| Processing | Composite event pattern matching active | ☐ |
| Intelligence | Root Cause Analysis for severity 4+ events | ☐ |
| Intelligence | Anomaly detection on every registered event | ☐ |
| Intelligence | Pattern models retrained monthly | ☐ |
| Constitution | All 104 constitutional rules implemented | ☐ |
| Readiness | ERC evaluated before event declared operationally ready | ☐ |

---

### Version History

| Version | Date | Change | Author |
|---|---|---|---|
| 1.0 | 2026-Q2 | Initial release | IIOS Architecture Board |

---

### Governing Documents

| Document | Role |
|---|---|
| DATABASE_PERSISTENCE_ARCHITECTURE.md | Storage contracts — all event persistence |
| KNOWLEDGE_ENGINE_ARCHITECTURE.md | Consumer architecture — reasoning over events |
| ENTITY_ENGINE_ARCHITECTURE.md | Entity provider — entities referenced by events |
| RELATIONSHIP_ENGINE_ARCHITECTURE.md | Relationship provider — events create/modify relationships |
| EVENT_ONTOLOGY.md | Event taxonomy — canonical event type definitions |
| ARCHITECTURE.md | System-level architecture — 17-layer IIOS hierarchy |

---

### Closing Statement

The Event Engine Architecture defined in this document is the authoritative design for all event management in the IIOS. Every implementation decision, every service interface, every detection trigger, every propagation rule, and every governance policy for events must conform to this document.

The Event Engine is the system's experience of time. Without it, the IIOS would be a collection of static entities and relationships — a map of the world, but not a model of a world that is changing. The Event Engine is the mechanism by which the IIOS understands that things happen, that they happen in a specific order, that some things cause other things, and that the system must respond.

The quality of the Event Engine's output — its detection rate, classification accuracy, propagation correctness, and analytical intelligence — directly determines the quality of every decision the IIOS makes. An Event Engine that misses events, misclassifies them, allows false propagation, or permits immutability violations is not a foundation for reliable financial intelligence — it is a systematic source of error that compounds over time.

Every event in the IIOS deserves:
- A timestamp that is true
- A record that is immutable
- A lifecycle that is managed
- An audit trail that is complete
- A governance policy that is enforced
- An intelligence analysis that is honest
- A learning signal that improves the system

This is the Event Constitution. It does not bend.

---

*EVENT_ENGINE_ARCHITECTURE.md — Investment Intelligence Operating System (IIOS)*  
*Classification: INTERNAL — Architecture Board Confidential*  
*Next review: 2026-Q4*
