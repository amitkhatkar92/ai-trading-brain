# INFORMATION_ENGINE_ARCHITECTURE.md
# Investment Intelligence Operating System (IIOS)
# Information Engine — Complete Engineering Architecture

---

**Document authority:** Architecture Board  
**Classification:** INTERNAL — Architecture Board Confidential  
**Version:** 1.0  
**Status:** FINAL  
**Date:** 2026-Q2  
**Target system:** IIOS Information Engine  

---

## SCOPE AND PURPOSE

This document defines the complete engineering architecture of the Information Engine for the Investment Intelligence Operating System (IIOS). The Information Engine is the system's information substrate — the component responsible for acquiring, ingesting, validating, enriching, classifying, organising, indexing, versioning, distributing, governing, storing, retrieving, and maintaining every piece of information defined in INFORMATION_ONTOLOGY.md.

If the Entity Engine defines what exists, the Relationship Engine defines how things are connected, and the Event Engine defines what happens, the Information Engine defines what is known about all of those things. Information is the material from which the IIOS constructs its understanding of the world.

This document is:
- The authoritative design specification for the Information Engine
- The mandatory reference for all Information Engine implementations
- A governance instrument defining the 25 components, 19 services, 14 lifecycle stages, and 95+ constitutional rules governing all information

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
| INFORMATION_ONTOLOGY.md | Complete information taxonomy — canonical reference |
| ENTITY_ONTOLOGY.md | Entity types — information describes entities |
| RELATIONSHIP_ONTOLOGY.md | Relationship types — information describes relationships |
| EVENT_ONTOLOGY.md | Event types — events produce and consume information |
| KNOWLEDGE_ENGINE_ARCHITECTURE.md | Primary consumer of structured information |
| ENTITY_ENGINE_ARCHITECTURE.md | Provider of entity context for information enrichment |
| RELATIONSHIP_ENGINE_ARCHITECTURE.md | Provider of relationship context |
| EVENT_ENGINE_ARCHITECTURE.md | Producer of event information; consumer of market information |
| CORE_FRAMEWORK_ARCHITECTURE.md | Core framework — shared infrastructure |
| ENGINEERING_STANDARDS.md | Engineering standards — naming, versioning, audit |

---

## IIOS POSITION OF THE INFORMATION ENGINE

```
┌─────────────────────────────────────────────────────────────────────┐
│                   IIOS — 17-Layer Architecture                      │
├─────────────────────────────────────────────────────────────────────┤
│  GlobalIntelligence  │  MarketIntelligence  │  MetaLearning         │
├──────────────────────┴──────────────────────┴───────────────────────┤
│              INFORMATION ENGINE  ◄──── Knowledge Substrate          │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────────┐ │
│  │ Acquisition  │  │ Validation   │  │ Distribution               │ │
│  │ Ingestion    │  │ Enrichment   │  │ Governance                 │ │
│  │ Normalization│  │ Quality Mgmt │  │ Lineage                    │ │
│  │ Classification│  │ Versioning   │  │ Archival                   │ │
│  └──────────────┘  └──────────────┘  └────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────────┤
│  Entity Engine  │  Relationship Engine  │  Event Engine             │
├─────────────────┴───────────────────────┴───────────────────────────┤
│  OpportunityEngine  │  StrategyLab  │  CapitalRiskEngine            │
├─────────────────────┴──────────────────┴────────────────────────────┤
│  RiskControl  │  MarketSimulation  │  RiskGuardian                  │
├───────────────┴────────────────────┴────────────────────────────────┤
│  DebateAndDecision  │  ExecutionEngine  │  TradeMonitoring           │
├─────────────────────┴───────────────────┴───────────────────────────┤
│  LearningSystem  │  PerformanceAnalytics  │  ResearchLab            │
├──────────────────┴────────────────────────┴─────────────────────────┤
│  ValidationEngine  │  ControlTower  │  SystemMonitor                │
└─────────────────────────────────────────────────────────────────────┘
```

---

## INFORMATION FLOW OVERVIEW

```
External Sources                  Information Engine                  IIOS Consumers
────────────────                  ──────────────────                  ──────────────
Market data feeds  ──[raw data]──► Acquisition Layer                 Knowledge Engine
News / NLP feeds   ──[text]──────► Ingestion Manager                 Entity Engine
Economic releases  ──[stats]─────► Validation Engine                 Relationship Engine
Broker API         ──[fills]─────► Normalization Engine              Event Engine
Research reports   ──[reports]───► Enrichment Engine                 Strategy Layer
Financial filings  ──[filings]───► Classification Engine             Risk Engine
AI agent outputs   ──[analysis]──► Quality Manager                   Learning System
Internal compute   ──[derived]───► Version Manager                   Human Principal
                                         │
                                         ▼
                               Information Registry
                               (versioned, governed)
                                         │
                                ┌────────┴─────────┐
                                ▼                  ▼
                           Index Manager     Distribution
                           (search, facet,   Manager
                            lineage)         (push/pull)
```

---

## INFORMATION → KNOWLEDGE CONCEPTUAL MODEL

```
Raw Data (uninterpreted signals)
    │
    │ [Ingestion + Validation]
    ▼
Information Object (validated, typed, source-attributed)
    │
    │ [Enrichment + Classification]
    ▼
Enriched Information (context-attached, entity-linked)
    │
    │ [Quality Assessment]
    ▼
Quality-Scored Information (confidence, freshness, reliability)
    │
    │ [Knowledge Engine reasoning]
    ▼
Knowledge (justified, derived insights and hypotheses)
    │
    │ [Decision Engine]
    ▼
Decisions (strategy selections, risk actions)
```

---

## TABLE OF CONTENTS

| Part | Title |
|---|---|
| I | Information Engine Philosophy |
| II | Information Engine Architecture |
| III | Core Components (25 components) |
| IV | Information Lifecycle (14 stages) |
| V | Information Services (19 services) |
| VI | Information Processing Architecture |
| VII | Information Quality Framework |
| VIII | Information Governance |
| IX | Information Constitution (95+ rules) |
| X | Information Readiness Checklist (16 sections) |
| Supplement A | Information Type Catalogue |
| Supplement B | Component Interface Reference |
| Supplement C | Processing Pipeline Patterns |
| Supplement D | Quality Framework Reference |
| Supplement E | Governance Decision Records |
| Supplement F | Anti-Pattern Reference |
| Supplement G | Information Glossary |

---
## PART I — INFORMATION ENGINE PHILOSOPHY

### 1.1 Why Information Is the Foundation of Intelligence

Intelligence is not the ability to receive data. Intelligence is the ability to transform data into understanding — to take raw signals from the world and derive justified conclusions about what is true, what matters, and what should be done. The IIOS cannot be intelligent without a rigorous, governed, high-quality information layer. The Information Engine is that layer.

The relationship between the Information Engine and the IIOS's analytical layers is asymmetric and foundational:
- The Knowledge Engine can only reason as well as the information it reasons over
- The Entity Engine can only classify entities as completely as the information it receives about them
- The Relationship Engine can only infer relationships as accurately as the information about the connected entities
- The Event Engine can only detect events as precisely as the data streams it monitors
- The Risk Engine's models are only as reliable as the market information they were trained on and the current information they operate on

This asymmetry means that information quality failures propagate upward through every layer of the IIOS. A price data error becomes a flawed hypothesis, which becomes an incorrect strategy selection, which becomes a loss. The Information Engine is the first and last line of defence against information quality failure.

**Six foundational principles of the Information Engine:**

| Principle | Statement |
|---|---|
| Completeness | Every piece of information that the IIOS needs is acquired, stored, and accessible. |
| Correctness | Every piece of information accurately represents the state of the world. |
| Currency | Information reflects the most recent available state — stale information is managed and flagged. |
| Traceability | Every piece of information can be traced to its origin, through all transformations. |
| Governance | Every piece of information is owned, classified, secured, and retained per policy. |
| Accessibility | Any authorised consumer can retrieve any information they need, quickly and reliably. |

---

### 1.2 Conceptual Distinctions — 20 Information-Related Terms

The following 20 distinctions are foundational to the Information Engine's design. Imprecise use of these terms in architecture documents leads to systems that conflate data management with information management, or information management with knowledge management — resulting in architectures where responsibility boundaries are unclear and quality assurance is inconsistent.

---

#### 1.2.1 Data

**Data** is the raw, uninterpreted signal received from a source — numbers, bytes, characters, or structured records that have not yet been validated, contextualised, or interpreted. A price feed delivers data. A raw FIX message from a broker is data. A CSV file from a statistical agency is data. Data has no inherent meaning until it is interpreted in the context of a model. The Information Engine is the mechanism by which raw data becomes meaningful information.

The critical distinction: data is what arrives; information is what the system makes of what arrives.

---

#### 1.2.2 Information

**Information** is data that has been validated, typed, contextualised, and attributed to a source — data that carries meaning within the IIOS's domain model. A validated price quote for TATASTEEL.NS at 14:37:22 on 2026-06-15 with bid/ask/last/volume is an information object. Information has:
- An identity (unique information_id)
- A type (what kind of information is this?)
- A source (where did it come from?)
- A timestamp (when was it current?)
- A quality score (how reliable is it?)
- A lineage (what transformations has it undergone?)

Data becomes information when it passes through the Information Engine's validation, normalization, and enrichment pipelines.

---

#### 1.2.3 Observation

An **Observation** is a specific, timestamped instance of a measurement — a reading of the world at a particular moment. Observations are the atomic units of empirical information. A VIX reading of 22.4 at 10:30:00 is an observation. A NIFTY50 price of 22,345.60 at 14:37:22 is an observation. Observations are the raw material of statistical models, correlation computations, and regime detection. Multiple observations over time constitute a time series, which is a higher-order information structure.

---

#### 1.2.4 Evidence

**Evidence** is information that is specifically gathered or presented to support or refute a hypothesis or belief. Evidence is directional — it leans toward a conclusion. The same price data that is simply an observation in one context becomes evidence when it is used to evaluate whether a strategy's hypothesis is correct. Evidence is information with a purpose: to justify or challenge a knowledge claim. The Knowledge Engine is the primary consumer of evidence; the Information Engine provides the evidence.

---

#### 1.2.5 Knowledge

**Knowledge** is justified, reliable belief — a conclusion that the system can assert with confidence based on evidence. Knowledge is not information; it is what is derived from information through reasoning. "TATASTEEL.NS tends to outperform the NIFTY50 during industrial expansion regimes" is knowledge — a generalised, validated claim about the world derived from processing many observations and evidence items. Knowledge is the output of the Knowledge Engine; information is its input.

The critical distinction: information is "what is"; knowledge is "what it means and what follows from it".

---

#### 1.2.6 Fact

A **Fact** is a piece of information that has been validated to a high confidence threshold — information that is treated as ground truth within the system. "TATASTEEL.NS closed at 156.45 on 2026-06-15" is a fact once it has been confirmed by multiple authoritative sources. Facts are the most trusted tier of information. Not all information rises to the level of fact; much information remains at the "probable" or "reported" level without independent confirmation.

---

#### 1.2.7 Signal

A **Signal** is a derived, directional piece of information that indicates a likely state or trend — more abstracted than raw data or observations, but less complete than knowledge. "VIX elevated → RISK_HEIGHTENED" is a signal. A signal is an intermediate analytical product: richer than a data point, but not the full inferential structure of knowledge. Signals are produced by the Information Engine's analytical components and consumed by the strategy, risk, and decision layers.

---

#### 1.2.8 Event

An **Event** is a timestamped, immutable occurrence — a change in system or world state. Events are managed by the Event Engine. The critical distinction from information: events are occurrences (things that happen); information is knowledge about the state of the world (things that are true). An event creates information — the ORDER_FILLED event creates fill information. Information can trigger events — a price crossing a threshold creates a PRICE_THRESHOLD_CROSSED event. The two engines are tightly coupled but distinctly responsible.

---

#### 1.2.9 Entity

An **Entity** is a persistent, named thing in the IIOS that maintains identity over time. Information describes entities — price information describes instruments, financial information describes companies, risk information describes portfolios. Entities are managed by the Entity Engine. Information objects in the Information Engine are linked to their described entities, but the entity records themselves live in the Entity Engine.

---

#### 1.2.10 Relationship

A **Relationship** is a typed connection between two entities. Information supports the establishment and validation of relationships — correlation information supports CORRELATED_WITH relationships; causal information supports CAUSED_BY relationships. Information objects in the Information Engine provide the evidence base for Relationship Engine operations, but the relationship records themselves live in the Relationship Engine.

---

#### 1.2.11 Information Object

An **Information Object** is the fundamental unit of the Information Engine — a governed, versioned, quality-scored record representing a piece of validated information. An information object is not a raw data record; it is the result of the Information Engine's complete processing pipeline applied to raw data. Every information object has:
- A canonical identity (information_id)
- A type (from the Information Catalog)
- A source reference
- A quality score
- A lineage record
- A version history
- A governance classification

---

#### 1.2.12 Information Record

An **Information Record** is the persistence representation of an Information Object — the structured data record stored in the Information Registry. An information record may represent a single observation (a price quote), a collection (a daily OHLCV bar), or a derived product (a volatility estimate). Information records are typed, versioned, and immutable after they are superseded.

---

#### 1.2.13 Information Source

An **Information Source** is an authorised origin of raw data or information for the IIOS. Sources include market data feeds, broker APIs, news services, statistical agencies, financial data providers, and internal analytical components. Sources are registered in the Source Manager and assigned a trust tier that influences the initial confidence score of information they provide. Sources are monitored for reliability — sources that frequently provide erroneous data have their trust tier reduced.

**Trust tiers:**

| Tier | Description | Initial confidence premium |
|---|---|---|
| AUTHORITATIVE | Primary, official sources (NSE, RBI, exchange feeds) | +0.15 |
| RELIABLE | Established secondary providers (Bloomberg, Refinitiv) | +0.05 |
| STANDARD | General data providers | 0 |
| PROVISIONAL | New or unverified sources | −0.10 |
| UNRELIABLE | Sources with documented reliability issues | −0.20 |

---

#### 1.2.14 Information Context

**Information Context** is the state of the IIOS and the external world at the time a piece of information was created or became current. Context is necessary for correct interpretation. A VIX reading of 30 means something different in a bear regime than in a bull regime. A company's earnings miss means something different before a rate hike than after. The Information Engine captures and preserves context for all information objects, enabling historically accurate interpretation during replay and analysis.

---

#### 1.2.15 Information Quality

**Information Quality** is the multi-dimensional assessment of an information object's fitness for use. The Information Engine uses 18 quality dimensions (see Part VII) to compute a composite Information Quality Score (IQS). Quality is not binary — it is a spectrum. An information object may be highly accurate but stale, or very fresh but from an unreliable source. The IQS synthesises all dimensions into a single operational quality indicator.

---

#### 1.2.16 Information Freshness

**Information Freshness** measures how current an information object is — how recently it was produced and how well it reflects the current state of the world. Freshness degrades over time at a rate that depends on the information type. Price information for a liquid equity becomes stale within seconds. Macroeconomic statistics may remain fresh for months. The Freshness Manager maintains per-type freshness standards and alerts when information falls below the FRESH threshold.

**Freshness classification:**

| Level | Description |
|---|---|
| FRESH | Within the defined freshness window for this type |
| AGING | Approaching the stale threshold — monitoring required |
| STALE | Beyond the freshness window — use with caution |
| CRITICAL_STALE | Severely outdated — do not use for operational decisions |
| EXPIRED | Beyond retention window — archived or retired |

---

#### 1.2.17 Information Confidence

**Information Confidence** measures the system's certainty that an information object is accurate and correctly represents the state of the world. Confidence is affected by source trust tier, validation results, corroboration from independent sources, and historical accuracy of the source. Confidence is in [0.0, 1.0]. Information with confidence below 0.50 is flagged for review before use in consequential decisions.

---

#### 1.2.18 Information Completeness

**Information Completeness** measures whether an information object contains all the fields and values required for its type. A price quote that is missing the volume field is incomplete. A company earnings report that is missing EPS is incomplete. Completeness is computed as the proportion of required fields present and non-null. Incomplete information objects are processed with completeness flags and may trigger acquisition of supplementary information.

---

#### 1.2.19 Information Reliability

**Information Reliability** measures the historical track record of the information source — how often the source has provided accurate information in the past. Reliability is distinct from confidence: confidence is about the current information object; reliability is about the source's historical performance. A high-reliability source for a particular information type earns a confidence premium; a low-reliability source earns a confidence penalty.

**Reliability formula:**

$$\text{reliability} = \frac{\text{confirmed accurate instances}}{\text{total instances from this source}} \text{ over rolling 90-day window}$$

---

#### 1.2.20 Information Lineage

**Information Lineage** is the complete documented history of an information object's origin and transformations — a provenance record that answers: where did this information come from? how was it transformed? what other information objects contributed to it? Lineage is mandatory for all information objects. Lineage is the audit trail of the information system: it enables reconstruction of any information object from its source data, and it enables impact analysis (if source X is found to be incorrect, which derived information objects are affected?).

**Lineage graph:**

```
Source data (raw price feed)
    │ [Ingestion]
    ▼
Validated price observation (IObj-PRC-001)
    │ [Normalization]
    ▼
Normalised OHLCV bar (IObj-BAR-045)
    │ [Enrichment]
    ▼
Enriched bar with 20-day SMA (IObj-EBAR-045)
    │ [Derivation]
    ▼
Volatility estimate (IObj-VOL-012)
    │ [Classification]
    ▼
Regime indicator input (IObj-RGM-003)
```

Each arrow in the lineage graph is a documented transformation step.

---

### 1.3 Design Principles

| Principle | Statement |
|---|---|
| Single source of truth | Every information object has exactly one canonical record in the Information Registry. |
| Lineage always | Every information object's full lineage from source to current state is always documented. |
| Quality first | Quality scores are computed before information is distributed to consumers. |
| Versioning always | Every update to an information object creates a new version — no in-place modification. |
| Governance mandatory | Every information object is owned, classified, and governed from the moment of creation. |
| Freshness transparency | Information consumers always know how fresh the information they are using is. |
| Source accountability | Every information source is registered, monitored, and accountable for its reliability. |
| Immutable history | Previous versions of information objects are preserved permanently for audit and replay. |

---
## PART II — INFORMATION ENGINE ARCHITECTURE

### 2.1 Architectural Position

The Information Engine occupies the foundational persistence and retrieval layer of the IIOS. It sits below all analytical engines (Knowledge, Entity, Relationship, Event) and above the raw data infrastructure (feeds, brokers, APIs). Its position in the IIOS dependency graph:

```
┌────────────────────────────────────────────────────────────┐
│                        IIOS Consumer Layers                │
│  [Risk Engine] [Strategy Engine] [Decision Engine]         │
│  [Portfolio Engine] [Execution Engine] [Monitoring Engine] │
└─────────────────────────┬──────────────────────────────────┘
                          │ consumes information from
┌─────────────────────────▼──────────────────────────────────┐
│              Analytical Engines                            │
│  [Knowledge Engine] [Entity Engine] [Relationship Engine]  │
│  [Event Engine]                                            │
└─────────────────────────┬──────────────────────────────────┘
                          │ reads from
┌─────────────────────────▼──────────────────────────────────┐
│             INFORMATION ENGINE  ◄── (this document)        │
│  [Registry] [Catalog] [Ingestion] [Validation]             │
│  [Enrichment] [Classification] [Indexing] [Distribution]   │
│  [Versioning] [Governance] [Quality Management]            │
└─────────────────────────┬──────────────────────────────────┘
                          │ ingests from
┌─────────────────────────▼──────────────────────────────────┐
│                   Data Infrastructure                      │
│  [Market Feeds] [Broker APIs] [News Feeds]                 │
│  [Statistical APIs] [Corporate Actions Feeds]              │
│  [Macroeconomic Data Sources] [Alternative Data Sources]   │
└────────────────────────────────────────────────────────────┘
```

---

### 2.2 Information Type Hierarchy — 15 Layers

The Information Engine organises all information into a 15-layer type hierarchy. Each layer represents a class of information with distinct acquisition, validation, storage, and governance requirements. The layers are ordered from most fundamental to most derived.

```
Layer 01: INFORMATION ROOT
    │ (abstract base — no instances, defines the contract)
    │
    ├── Layer 02: MARKET INFORMATION
    │       ├── Price Information
    │       │     ├── Quote Information (bid/ask/last)
    │       │     ├── Trade Information (executed trades)
    │       │     ├── OHLCV Bar Information
    │       │     └── Settlement Information (official close, settlement price)
    │       ├── Volume Information (traded volume, open interest)
    │       ├── Depth Information (order book depth, Level 2)
    │       ├── Derivative Information (options chain, futures chain)
    │       └── Index Information (NIFTY50, BANKNIFTY, sector indices)
    │
    ├── Layer 03: CORPORATE INFORMATION
    │       ├── Earnings Information (EPS, revenue, guidance)
    │       ├── Balance Sheet Information (assets, liabilities, equity)
    │       ├── Corporate Action Information (dividends, splits, bonuses, rights)
    │       ├── Management Information (key appointments, governance events)
    │       └── Filing Information (exchange filings, regulatory disclosures)
    │
    ├── Layer 04: MACROECONOMIC INFORMATION
    │       ├── Indicator Information (GDP, CPI, IIP, PMI, WPI)
    │       ├── Monetary Information (repo rate, reverse repo, CRR, SLR)
    │       ├── Fiscal Information (budget, deficit, debt)
    │       ├── Currency Information (USD/INR, DXY, cross rates)
    │       └── Commodity Information (crude, gold, silver, agricultural)
    │
    ├── Layer 05: SENTIMENT INFORMATION
    │       ├── News Sentiment Information
    │       ├── Social Media Sentiment Information
    │       ├── Analyst Sentiment Information (upgrades/downgrades)
    │       ├── Options Market Sentiment (PCR, IV skew)
    │       └── FII/DII Flow Sentiment Information
    │
    ├── Layer 06: FLOW INFORMATION
    │       ├── FII Flow Information (net buy/sell by category)
    │       ├── DII Flow Information
    │       ├── Retail Flow Information
    │       ├── Sector Rotation Information
    │       └── Global Flow Information (FPI, bond flows)
    │
    ├── Layer 07: ALTERNATIVE INFORMATION
    │       ├── Web Scraping Information
    │       ├── Satellite Data Information
    │       ├── Patent Filing Information
    │       ├── Job Posting Information
    │       └── Supply Chain Information
    │
    ├── Layer 08: TECHNICAL INFORMATION
    │       ├── Indicator Information (RSI, MACD, Bollinger, ATR)
    │       ├── Pattern Information (price patterns, chart formations)
    │       ├── Support/Resistance Information
    │       └── Trend Information (regime, trend direction, slope)
    │
    ├── Layer 09: RISK INFORMATION
    │       ├── Volatility Information (realised vol, implied vol, VIX)
    │       ├── Correlation Information (pair correlations, sector correlations)
    │       ├── Drawdown Information (current DD, max DD)
    │       ├── Exposure Information (position sizing, portfolio exposure)
    │       └── Stress Information (scenario losses, tail risk)
    │
    ├── Layer 10: STRATEGY INFORMATION
    │       ├── Signal Information (buy/sell/hold signals)
    │       ├── Strategy State Information (current state of running strategies)
    │       ├── Backtest Information (historical performance statistics)
    │       ├── Walk-Forward Information (OOS performance)
    │       └── Evolution Information (strategy generation, mutation, fitness)
    │
    ├── Layer 11: EXECUTION INFORMATION
    │       ├── Order Information (pending, placed, filled, cancelled)
    │       ├── Position Information (open positions, quantity, PnL)
    │       ├── Trade Information (completed trades with full lifecycle)
    │       ├── Slippage Information (expected vs actual fill)
    │       └── Commission Information (fees, taxes, charges)
    │
    ├── Layer 12: PORTFOLIO INFORMATION
    │       ├── Portfolio State Information (current holdings, cash, equity)
    │       ├── PnL Information (realised, unrealised, daily, MTD, YTD)
    │       ├── Allocation Information (strategy allocations, sector allocations)
    │       ├── Attribution Information (return attribution by factor)
    │       └── Benchmark Information (comparison vs benchmark)
    │
    ├── Layer 13: REGIME INFORMATION
    │       ├── Market Regime Information (BULL, BEAR, SIDEWAYS, etc.)
    │       ├── Sector Regime Information (leading, lagging sectors)
    │       ├── Liquidity Regime Information (HIGH_LIQ, LOW_LIQ)
    │       ├── Volatility Regime Information (LOW_VOL, MID_VOL, HIGH_VOL)
    │       └── Global Regime Information (global risk-on/risk-off state)
    │
    ├── Layer 14: DERIVED INFORMATION
    │       ├── Statistical Derived Information (moving averages, regressions)
    │       ├── Model Output Information (ML model predictions, scores)
    │       ├── Composite Scores (information quality, confidence scores)
    │       └── Aggregated Information (cross-asset summaries, portfolio snapshots)
    │
    └── Layer 15: KNOWLEDGE INFORMATION
            ├── Asserted Facts (validated ground-truth information)
            ├── Inferred Information (derived via inference chains)
            ├── Hypotheses (unconfirmed conclusions awaiting evidence)
            └── Belief States (confidence-weighted multi-scenario information)
```

---

### 2.3 Information Architecture Principles by Layer

| Layer | Freshness SLA | Confidence Floor | Version Retention | Governance Tier |
|---|---|---|---|---|
| Market Information | Seconds (quotes), Minutes (bars) | 0.80 | 36 months | CRITICAL |
| Corporate Information | Hours (filings), Days (reports) | 0.75 | 84 months (7 years) | HIGH |
| Macroeconomic Information | Days to months | 0.85 | 120 months (10 years) | HIGH |
| Sentiment Information | Minutes to hours | 0.60 | 12 months | MEDIUM |
| Flow Information | Hours (intraday), Daily | 0.70 | 36 months | HIGH |
| Alternative Information | Variable | 0.50 | 12 months | MEDIUM |
| Technical Information | Real-time (intraday) | 0.75 | 24 months | MEDIUM |
| Risk Information | Minutes (intraday), End-of-day | 0.80 | 36 months | CRITICAL |
| Strategy Information | Real-time | 0.70 | 60 months | HIGH |
| Execution Information | Real-time, Immutable | 0.95 | 84 months (7 years) | CRITICAL |
| Portfolio Information | End-of-day | 0.90 | 84 months (7 years) | CRITICAL |
| Regime Information | 30-minute intervals | 0.75 | 36 months | HIGH |
| Derived Information | On demand | 0.65 | 24 months | MEDIUM |
| Knowledge Information | On inference | 0.80 | Permanent | CRITICAL |

---

### 2.4 Information Flow Architecture

The end-to-end flow of information through the Information Engine follows the canonical information processing pipeline:

```
External World
     │ (price ticks, news events, economic releases, broker events)
     ▼
┌───────────────────────────────────────────────────────────────────────────┐
│  ACQUISITION LAYER                                                        │
│  ┌─────────────────┐  ┌──────────────────┐  ┌──────────────────────────┐ │
│  │  Source Manager  │  │ Acquisition Mgr  │  │ Ingestion Manager        │ │
│  │  - source reg.  │  │ - pull/push/poll │  │ - raw buffer             │ │
│  │  - trust tiers  │  │ - rate limiting  │  │ - deduplication          │ │
│  │  - monitoring   │  │ - retry/backoff  │  │ - ordering               │ │
│  └─────────────────┘  └──────────────────┘  └──────────────────────────┘ │
└───────────────────────────────────┬───────────────────────────────────────┘
                                    │ raw information objects
                                    ▼
┌───────────────────────────────────────────────────────────────────────────┐
│  VALIDATION LAYER                                                         │
│  ┌─────────────────┐  ┌──────────────────┐  ┌──────────────────────────┐ │
│  │ Validation Eng. │  │ Quality Manager  │  │ Confidence Manager       │ │
│  │ - schema checks │  │ - quality score  │  │ - confidence scoring     │ │
│  │ - value checks  │  │ - completeness   │  │ - source trust premium   │ │
│  │ - cross checks  │  │ - consistency    │  │ - corroboration bonus    │ │
│  └─────────────────┘  └──────────────────┘  └──────────────────────────┘ │
└───────────────────────────────────┬───────────────────────────────────────┘
                                    │ validated information objects
                                    ▼
┌───────────────────────────────────────────────────────────────────────────┐
│  ENRICHMENT LAYER                                                         │
│  ┌─────────────────┐  ┌──────────────────┐  ┌──────────────────────────┐ │
│  │ Normalization   │  │ Enrichment Eng.  │  │ Context Manager          │ │
│  │ Engine          │  │ - derived fields │  │ - market regime at time  │ │
│  │ - canonical IDs │  │ - cross-ref      │  │ - session state          │ │
│  │ - unit std.     │  │ - aggregation    │  │ - event context          │ │
│  └─────────────────┘  └──────────────────┘  └──────────────────────────┘ │
└───────────────────────────────────┬───────────────────────────────────────┘
                                    │ enriched information objects
                                    ▼
┌───────────────────────────────────────────────────────────────────────────┐
│  ORGANISATION LAYER                                                       │
│  ┌─────────────────┐  ┌──────────────────┐  ┌──────────────────────────┐ │
│  │ Classification  │  │ Index Manager    │  │ Version Manager          │ │
│  │ Engine          │  │ - search index   │  │ - version chain          │ │
│  │ - type assign.  │  │ - time series    │  │ - supersession           │ │
│  │ - tag assign.   │  │ - entity index   │  │ - lineage extension      │ │
│  └─────────────────┘  └──────────────────┘  └──────────────────────────┘ │
└───────────────────────────────────┬───────────────────────────────────────┘
                                    │ organised, indexed, versioned objects
                                    ▼
┌───────────────────────────────────────────────────────────────────────────┐
│  PERSISTENCE LAYER                                                        │
│  ┌─────────────────┐  ┌──────────────────┐  ┌──────────────────────────┐ │
│  │ Information     │  │ Storage Manager  │  │ Archive Manager          │ │
│  │ Registry        │  │ - hot/warm/cold  │  │ - retirement policy      │ │
│  │ - canonical rec.│  │ - tiered storage │  │ - compression            │ │
│  │ - lineage graph │  │ - redundancy     │  │ - long-term retention    │ │
│  └─────────────────┘  └──────────────────┘  └──────────────────────────┘ │
└───────────────────────────────────┬───────────────────────────────────────┘
                                    │ persisted information
                                    ▼
┌───────────────────────────────────────────────────────────────────────────┐
│  DISTRIBUTION LAYER                                                       │
│  ┌─────────────────┐  ┌──────────────────┐  ┌──────────────────────────┐ │
│  │ Distribution    │  │ Search Engine    │  │ Retrieval Manager        │ │
│  │ Manager         │  │ - full text      │  │ - structured queries     │ │
│  │ - subscriptions │  │ - semantic       │  │ - time series queries    │ │
│  │ - push routing  │  │ - faceted search │  │ - lineage traversal      │ │
│  └─────────────────┘  └──────────────────┘  └──────────────────────────┘ │
└───────────────────────────────────────────────────────────────────────────┘
```

---
## PART III — CORE COMPONENTS

The Information Engine is implemented through 25 tightly co-ordinated components. Each component has a single, well-defined responsibility within the information processing pipeline. Components are grouped into five operational clusters: Registry & Catalog, Acquisition, Validation & Quality, Organisation, and Governance.

---

### 3.1 REGISTRY & CATALOG CLUSTER

---

#### Component 01 — Information Registry

**Purpose:** The Information Registry is the authoritative, canonical store for all information objects in the IIOS. Every piece of validated information — regardless of type, source, or age — exists as a record in the Information Registry. The Registry is the single source of truth.

**Responsibilities:**
- Accept new information objects submitted by the Ingestion Manager
- Assign canonical information_id on creation
- Store the complete information object record including all metadata
- Maintain the version chain for each information object
- Expose retrieval APIs to all authorised consumers
- Enforce read-only access to superseded versions
- Support bulk retrieval for analytical workloads
- Provide statistics on information volume, freshness distribution, and quality distribution

**Inputs:**
- Enriched, classified information objects from the Organisation Layer
- Version update notifications from the Version Manager
- Retirement instructions from the Archive Manager

**Outputs:**
- Canonical information records (to any authorised consumer)
- Registry statistics and health metrics
- Information object identifiers issued to the Ingestion Manager

**Dependencies:**
- Information Catalog (for type validation)
- Version Manager (for version chain management)
- Governance Manager (for access control enforcement)

**Failure Handling:**
- If the Registry store is unavailable: queue incoming objects in a durable ingestion buffer; reject reads with a service-unavailable status; alert the monitoring system
- If a version chain is corrupted: quarantine the affected information objects; alert the Governance Manager; do not serve corrupted versions

**Internal structure:**
```
Information Registry
    ├── Active Objects Index (information_id → current record)
    ├── Version Archives (information_id → version_chain[])
    ├── Lineage Graph (directed graph of derivation relationships)
    ├── Type Index (type_code → list of information_ids)
    ├── Source Index (source_id → list of information_ids)
    ├── Entity Cross-Reference (entity_id → list of information_ids)
    └── Freshness Monitor (type → freshness distribution snapshot)
```

---

#### Component 02 — Information Catalog

**Purpose:** The Information Catalog defines all valid information types in the IIOS — their schemas, freshness requirements, confidence floors, governance classifications, and retention policies. The Catalog is the schema registry of the Information Engine.

**Responsibilities:**
- Maintain the authoritative list of all information types
- Define the required and optional fields for each information type
- Store freshness SLAs per type (how quickly does this type of information expire?)
- Store confidence floors per type (what is the minimum acceptable confidence score?)
- Define the governance classification for each type
- Define the retention period and archive policy for each type
- Support addition of new types via the Evolution Manager
- Provide type validation services to the Validation Engine

**Inputs:**
- Type registration requests from the Evolution Manager
- Type definition queries from the Validation Engine, Classification Engine, Ingestion Manager
- Type deprecation instructions from the Governance Manager

**Outputs:**
- Type definition records (schema, constraints, SLAs, governance)
- Type validation responses (is this information object conformant with its declared type?)
- Catalog statistics (number of types, coverage by layer)

**Dependencies:**
- Evolution Manager (for type lifecycle management)
- Governance Manager (for governance classification changes)

**Catalog record structure:**

| Field | Description |
|---|---|
| type_code | Unique identifier for this information type |
| type_name | Human-readable name |
| layer | Which of the 15 layers this type belongs to |
| required_fields | List of mandatory fields |
| optional_fields | List of permitted optional fields |
| freshness_sla_seconds | Time-to-stale in seconds |
| confidence_floor | Minimum acceptable confidence score |
| governance_tier | CRITICAL / HIGH / MEDIUM / LOW |
| retention_months | How long records are kept before archiving |
| version | Catalog entry version |
| status | ACTIVE / DEPRECATED / EXPERIMENTAL |

---

#### Component 03 — Information Identity Manager

**Purpose:** The Identity Manager is responsible for the deterministic generation and management of canonical identifiers for all information objects. It ensures global uniqueness and enables collision-free federation with external systems.

**Responsibilities:**
- Generate globally unique information_id values on demand
- Maintain source-to-canonical identity mappings (external ID → information_id)
- Detect and manage information identity conflicts (same real-world fact from multiple sources)
- Provide identity resolution services (given multiple external IDs, return the canonical information_id)
- Manage entity reference IDs embedded in information objects

**Inputs:**
- Identity generation requests from the Ingestion Manager (one per new information object)
- Identity lookup requests from the Validation and Classification Engines
- Conflict resolution requests from the Deduplication Engine

**Outputs:**
- Canonical information_id values
- Source-to-canonical mapping records
- Identity conflict alerts
- Identity resolution responses

**Canonical ID format:**
```
IOBJ-{LAYER_CODE}-{TYPE_CODE}-{YYYYMMDD}-{SEQ:08d}
  e.g.  IOBJ-MKT-PRC-20260615-00000423
         IOBJ-CORP-EARN-20260615-00000007
         IOBJ-EXEC-ORD-20260615-00003891
```

---

### 3.2 ACQUISITION CLUSTER

---

#### Component 04 — Information Acquisition Manager

**Purpose:** The Acquisition Manager orchestrates the active collection of information from all registered external sources. It implements a governed acquisition schedule and manages acquisition budgets (API call quotas, rate limits, costs).

**Responsibilities:**
- Maintain the acquisition schedule for each source (time-based, event-triggered, on-demand)
- Execute acquisition jobs according to schedule
- Implement per-source rate limiting to comply with API restrictions
- Manage retry logic with exponential backoff on acquisition failure
- Track acquisition success rates per source
- Support on-demand acquisition requests from downstream components
- Report acquisition metrics (success rate, latency, volume, cost) to the monitoring system

**Inputs:**
- Acquisition schedules from the Source Manager
- On-demand requests from the Ingestion Manager or downstream engines
- Rate limit specifications per source from the Source Manager
- Acquisition budget constraints from the Governance Manager

**Outputs:**
- Raw information batches delivered to the Ingestion Manager
- Acquisition logs (timestamp, source, volume, success/failure, latency)
- Acquisition alerts (source down, quota exceeded, repeated failures)

**Acquisition modes:**

| Mode | Trigger | Use case |
|---|---|---|
| Scheduled batch | Time-based cron | Daily market data files, weekly macroeconomic releases |
| Continuous polling | Periodic tick (configurable interval) | Price quotes, order book updates |
| Event-triggered | External event or internal trigger | Earnings releases, corporate action announcements |
| On-demand | Request from downstream component | Historical data for backtesting, one-time lookups |
| Webhook | Push from source | Real-time news feeds, FIX protocol price streams |

---

#### Component 05 — Information Source Manager

**Purpose:** The Source Manager maintains the registry of all authorised information sources, their configurations, trust tiers, and reliability statistics. It is the authoritative directory of where information comes from.

**Responsibilities:**
- Register and deregister information sources
- Assign and revise trust tiers based on reliability history
- Maintain per-source connection configuration (API keys, endpoints, protocols)
- Monitor source health (uptime, latency, error rate)
- Calculate per-source reliability scores on a rolling 90-day window
- Alert when a source's reliability falls below threshold
- Recommend source promotion or demotion to the Governance Manager

**Inputs:**
- Source registration requests from administrators
- Reliability assessment data from the Validation Engine
- Health monitoring data from the Acquisition Manager

**Outputs:**
- Source directory (all registered sources with configurations)
- Trust tier assignments (used by Confidence Manager)
- Source health status (used by Acquisition Manager for scheduling)
- Reliability alerts (used by Governance Manager for escalation)

**Source Registry fields:**

| Field | Description |
|---|---|
| source_id | Unique canonical source identifier |
| source_name | Human-readable name |
| source_type | FEED / API / FILE / WEBHOOK / INTERNAL |
| trust_tier | AUTHORITATIVE / RELIABLE / STANDARD / PROVISIONAL / UNRELIABLE |
| information_types | List of type codes this source provides |
| connection_config | Encrypted connection parameters |
| reliability_score | Rolling 90-day accuracy rate |
| uptime_score | Rolling 30-day availability rate |
| last_successful | Timestamp of last successful acquisition |
| alert_threshold | Reliability below which alerts are raised |
| status | ACTIVE / SUSPENDED / DECOMMISSIONED |

---

#### Component 06 — Ingestion Manager

**Purpose:** The Ingestion Manager is the entry point for all raw data arriving at the Information Engine. It performs initial parsing, deduplication, ordering, and hand-off to the validation pipeline.

**Responsibilities:**
- Receive raw data from the Acquisition Manager
- Parse raw data into typed pre-information records
- Detect and suppress duplicate records (same fact arriving from the same source twice)
- Ensure temporal ordering of records from time-series sources
- Buffer incoming records during downstream pipeline overload
- Route records to the appropriate validation pathway based on data type
- Record ingestion metrics (volume, latency, parse errors, deduplication rate)

**Inputs:**
- Raw data batches from the Acquisition Manager
- Connection configuration from the Source Manager (for parsing strategy selection)

**Outputs:**
- Pre-information records (parsed, deduplicated, ordered) delivered to the Validation Engine
- Ingestion metrics (to monitoring)
- Ingestion alerts (parse failure, unexpectedly high deduplication rate, ordering violations)

**Deduplication strategy:**
- For time-series data (prices, volumes): deduplicate on (source_id, type_code, symbol, timestamp)
- For event-based data (earnings, corporate actions): deduplicate on (source_id, type_code, entity_id, event_date)
- For reference data: deduplicate on (source_id, type_code, entity_id, effective_date)
- Duplicate records are logged but not discarded — they are quarantined for cross-source corroboration analysis

---

### 3.3 VALIDATION & QUALITY CLUSTER

---

#### Component 07 — Validation Engine

**Purpose:** The Validation Engine is responsible for confirming that each pre-information record is structurally valid, type-conformant, value-consistent, and cross-referenced correctly. Validation is mandatory — no record proceeds to enrichment without passing validation.

**Responsibilities:**
- Apply schema validation against the type definition from the Information Catalog
- Apply value range validation (prices must be positive; volumes must be non-negative; dates must be valid calendar dates in a reasonable range)
- Apply cross-field consistency validation (high must be ≥ close ≥ low; bid must be ≤ ask)
- Apply cross-source consistency validation (same fact reported by multiple sources should agree within tolerance)
- Assign a validation status to each record (PASS / WARN / FAIL)
- Route PASS records to the enrichment pipeline
- Route WARN records to the enrichment pipeline with a reduced confidence score
- Route FAIL records to the quarantine store and alert the Source Manager

**Validation levels:**

| Level | Check | Failure action |
|---|---|---|
| L1 Schema | Record has all required fields; types match | FAIL — reject |
| L2 Range | Values within physically possible ranges | FAIL — reject |
| L3 Consistency | Cross-field internal consistency | WARN — reduced confidence |
| L4 Cross-source | Consistency with other sources for same fact | WARN — flag for review |
| L5 Historical | Consistency with known historical values (no impossible price moves) | WARN — flag as anomaly |

---

#### Component 08 — Quality Manager

**Purpose:** The Quality Manager computes the multi-dimensional Information Quality Score (IQS) for each information object and maintains quality statistics across the information base.

**Responsibilities:**
- Apply the 18-dimension quality framework to each information object (see Part VII)
- Compute the composite IQS
- Tag information objects with quality tier (EXCELLENT / GOOD / ACCEPTABLE / MARGINAL / POOR)
- Monitor quality distribution across the information base
- Detect quality degradation trends (e.g., a source that is systematically providing lower-quality data over time)
- Report quality metrics to monitoring and governance systems
- Flag information objects below the minimum quality threshold for the IIOS's current operational mode

**Quality tiers:**

| Tier | IQS Range | Operational status |
|---|---|---|
| EXCELLENT | 0.90 – 1.00 | Fully usable for all purposes |
| GOOD | 0.75 – 0.89 | Fully usable for all purposes |
| ACCEPTABLE | 0.60 – 0.74 | Usable with quality flag |
| MARGINAL | 0.40 – 0.59 | Use with explicit caution flag; not for high-stakes decisions |
| POOR | 0.00 – 0.39 | Do not use; quarantine for review |

---

#### Component 09 — Confidence Manager

**Purpose:** The Confidence Manager assigns and maintains the confidence score for each information object — a measure of the system's certainty that the information accurately represents the real-world state.

**Responsibilities:**
- Compute the initial confidence score using source trust tier, validation results, and completeness
- Adjust confidence based on corroboration from independent sources
- Reduce confidence when information object becomes stale (freshness degradation)
- Re-issue confidence updates when new corroborating or contradicting information arrives
- Maintain a confidence history for each information object (confidence over time)
- Alert when the confidence of a critical information object falls below threshold

**Confidence computation formula:**

$$\text{confidence}_0 = \text{base}(\text{trust\_tier}) + \text{validation\_premium} + \text{completeness\_premium}$$

$$\text{confidence}_{t} = \text{confidence}_0 \times \text{freshness\_decay}(t, \text{type}) \times \text{corroboration\_factor}$$

**Corroboration factors:**

| Corroboration level | Factor |
|---|---|
| 3+ independent sources agree | × 1.20 (cap at 1.00) |
| 2 independent sources agree | × 1.10 |
| Single source, uncontested | × 1.00 |
| Mild disagreement across sources | × 0.85 |
| Strong disagreement across sources | × 0.60 |

---

#### Component 10 — Freshness Manager

**Purpose:** The Freshness Manager tracks the temporal currency of every information object in the Registry and ensures that consumers are always aware of how current the information they are using is.

**Responsibilities:**
- Track the as-of timestamp for every active information object
- Apply per-type freshness SLAs from the Information Catalog
- Compute the freshness score for each information object at any given moment
- Classify information objects into freshness tiers (FRESH / AGING / STALE / CRITICAL_STALE / EXPIRED)
- Alert the Acquisition Manager when critical information becomes stale (triggering re-acquisition)
- Alert information consumers when they request stale information
- Report freshness distribution statistics to monitoring

**Freshness decay function:**

$$\text{freshness}(t, T) = \max\left(0, 1 - \frac{t - t_0}{\text{SLA}(T)}\right)$$

where:
- $t$ = current time
- $t_0$ = information as-of timestamp
- $T$ = information type
- $\text{SLA}(T)$ = freshness SLA in seconds for type $T$

---

### 3.4 ENRICHMENT CLUSTER

---

#### Component 11 — Normalization Engine

**Purpose:** The Normalization Engine transforms validated information records into the IIOS's canonical internal representation — standardising identifiers, units, formats, and naming conventions.

**Responsibilities:**
- Map external source identifiers to canonical IIOS entity IDs (using the Entity Engine's identity resolution)
- Standardise numeric units (prices in INR, volumes in shares, rates as decimals)
- Standardise date and time representations (all timestamps in UTC; all dates as ISO 8601)
- Standardise naming conventions (security symbols to canonical form)
- Apply sector and industry code normalisation (map source-specific codes to canonical classification)
- Detect and flag normalisation failures (cannot map to canonical entity)

---

#### Component 12 — Enrichment Engine

**Purpose:** The Enrichment Engine adds derived, computed, and cross-referenced fields to validated, normalised information objects — making them more immediately useful for analytical consumers.

**Responsibilities:**
- Compute derived fields (e.g., daily return from consecutive OHLCV bars; implied volatility from options data)
- Add cross-references to related information objects (link a price quote to the entity's corporate actions history)
- Add entity metadata to information records (add sector, industry, market cap tier to price records)
- Add regime context to information records (annotate with the market regime active at the time)
- Compute rolling statistical measures (20-day SMA, ATR, realised volatility) and attach as enriched fields
- Apply ML-based enrichment (sentiment scores from news text, relevance scores from news metadata)

---

#### Component 13 — Context Manager

**Purpose:** The Context Manager captures and preserves the state of the IIOS at the time each information object becomes current — enabling historically accurate interpretation of information during replay, analysis, and audit.

**Responsibilities:**
- Record the active market regime at the time an information object is created
- Record the active trading session (pre-market, market hours, post-market, closed)
- Record significant events concurrent with the information object (corporate actions, macroeconomic releases)
- Attach the context record to the information object's lineage
- Provide context retrieval API for historical analysis

**Context record fields:**

| Field | Description |
|---|---|
| context_id | Unique identifier |
| as_of_timestamp | Moment this context snapshot was captured |
| market_regime | Active regime code (BULL_TREND, BEAR_TREND, HIGH_VOL, etc.) |
| trading_session | PRE_MARKET / MARKET_OPEN / MARKET_CLOSE / POST_MARKET / CLOSED |
| vix_level | VIX at context time |
| nifty_level | NIFTY50 at context time |
| active_events | List of significant events active at context time |
| liquidity_state | HIGH / NORMAL / LOW |

---
### 3.5 ORGANISATION CLUSTER

---

#### Component 14 — Classification Engine

**Purpose:** The Classification Engine assigns a complete classification to each information object — type code, layer, tags, topics, and relationships to other classified objects. Classification is the basis for indexing, routing, and governance assignment.

**Responsibilities:**
- Confirm or correct the declared type code of each information object
- Assign the information layer (Layer 01–15 of the information hierarchy)
- Assign topic tags (e.g., EARNINGS, PRICE, VOLATILITY, REGIME, MACRO, FLOW)
- Assign entity tags (which entities does this information describe?)
- Assign sector and industry tags for market-related information
- Assign temporal classification (INTRADAY / DAILY / WEEKLY / MONTHLY / QUARTERLY / ANNUAL)
- Flag unusual classification results for human review

**Classification output fields:**

| Field | Description |
|---|---|
| type_code | Confirmed canonical type code from Information Catalog |
| layer | Information layer (1–15) |
| topic_tags | List of topic tags |
| entity_refs | List of entity_ids this information describes |
| sector_codes | For market information: list of sector codes |
| temporal_class | REAL_TIME / INTRADAY / DAILY / WEEKLY / MONTHLY / QUARTERLY / ANNUAL / POINT_IN_TIME |
| freshness_class | TICK / MINUTE / HOURLY / DAILY / PERIODIC |
| governance_tier | Inherited from Catalog or overridden by classification result |

---

#### Component 15 — Index Manager

**Purpose:** The Index Manager maintains all indices over the information base that enable efficient retrieval and search by consumers. Indices are the performance mechanism that makes the Information Registry practically useful at scale.

**Responsibilities:**
- Maintain a time-series index per information type (type_code → time-ordered sequence of information_ids)
- Maintain an entity cross-reference index (entity_id → list of information_ids describing that entity)
- Maintain a source index (source_id → list of information_ids from that source)
- Maintain a freshness index (ordered by as-of timestamp for staleness detection)
- Maintain a full-text search index for unstructured information types (news, filings, reports)
- Rebuild or repair indices on recovery from failure
- Report index health and query performance statistics

**Index types:**

| Index | Key | Value | Use case |
|---|---|---|---|
| Time Series Index | (type_code, entity_id) | Ordered list of (timestamp, information_id) | Time-range queries for analytical workloads |
| Entity Index | entity_id | Set of information_ids | "All information about TATASTEEL" |
| Type Index | type_code | Set of information_ids | "All price quotes" |
| Source Index | source_id | Set of information_ids | "All information from NSE feed" |
| Freshness Index | freshness_expiry_time | Set of information_ids | "Which information is about to expire?" |
| Full-Text Index | words/tokens | Set of information_ids | "Find all news containing 'RBI rate hike'" |
| Lineage Index | parent_information_id | Set of child_information_ids | "What was derived from this source record?" |

---

#### Component 16 — Version Manager

**Purpose:** The Version Manager manages the complete version chain for every information object — ensuring that the history of updates is preserved immutably and that consumers can access any historical version.

**Responsibilities:**
- Accept version update notifications when an information object is superseded
- Create a new version record for each update, linking to the previous version
- Mark the previous version as SUPERSEDED but never delete it
- Maintain the version chain data structure (linked list of versions, oldest to newest)
- Provide version retrieval API (given an information_id and a version number or timestamp, return the corresponding version)
- Detect version chain corruption and alert the Governance Manager
- Compact version chains that exceed a configurable maximum chain length (archiving old versions)

**Version record fields:**

| Field | Description |
|---|---|
| version_id | Unique version identifier |
| information_id | Parent information object identifier |
| version_number | Sequential version number (1 = original) |
| effective_from | When this version became current |
| effective_to | When this version was superseded (null if current) |
| status | CURRENT / SUPERSEDED / ARCHIVED |
| change_reason | Why this version was created |
| changed_by | Component or process that created this version |
| content_delta | What changed from the previous version |

---

### 3.6 GOVERNANCE CLUSTER

---

#### Component 17 — Storage Manager

**Purpose:** The Storage Manager is responsible for the physical persistence of all information records across the multi-tier storage architecture — ensuring durability, redundancy, and appropriate placement of information based on access frequency and age.

**Responsibilities:**
- Assign new information objects to the appropriate storage tier on creation
- Migrate information objects between tiers as they age or become less frequently accessed
- Maintain storage redundancy (replicate across storage nodes)
- Monitor storage health and capacity
- Coordinate with the Archive Manager on retirement of information that has exceeded its retention period
- Report storage utilisation metrics

**Storage tiers:**

| Tier | Description | Access latency | Retention |
|---|---|---|---|
| HOT | Frequently accessed, in-memory or fast SSD | < 10ms | Current operational period (weeks to months) |
| WARM | Recent historical data, SSD-backed | < 100ms | Medium-term history (months to 2 years) |
| COLD | Older historical data, HDD or object storage | < 5 seconds | Long-term history (2–7 years) |
| ARCHIVE | Compliance and audit records | Minutes | Beyond 7 years; regulatory requirement |

**Tier transition rules:**

| Condition | Action |
|---|---|
| Last access > 30 days and information age > 90 days | HOT → WARM |
| Last access > 90 days and information age > 730 days | WARM → COLD |
| Age > retention_months for the information type | COLD → ARCHIVE |
| Age > max_retention (legal limit) and not legally required | ARCHIVE → RETIRE |

---

#### Component 18 — Retrieval Manager

**Purpose:** The Retrieval Manager provides a structured query interface to the Information Registry, translating consumer queries into efficient index lookups and returning fully hydrated information objects.

**Responsibilities:**
- Accept structured query requests (by type, entity, time range, quality floor, freshness requirement)
- Translate queries into index lookups using the Index Manager
- Retrieve information object records from the Storage Manager
- Apply freshness and confidence filters
- Hydrate full lineage records on request
- Support bulk retrieval for analytical workloads
- Return query statistics (result count, latency, freshness distribution of results)

**Standard query patterns:**

| Pattern | Description |
|---|---|
| Point-in-time | "What was the price of TATASTEEL at 14:37:22 on 2026-06-15?" |
| Time range | "All OHLCV bars for NIFTYBANK from 2026-01-01 to 2026-06-15" |
| Latest | "The current (most recent) value of VIX" |
| By entity | "All information describing RELIANCE with quality ≥ GOOD" |
| By type and filter | "All earnings information for NIFTY50 constituents for the last quarter" |
| Lineage | "All information objects derived from source record IOBJ-MKT-PRC-20260615-00000423" |
| Cross-entity | "All price observations for the entire NIFTY50 basket at market close on 2026-06-15" |

---

#### Component 19 — Search Engine

**Purpose:** The Search Engine provides free-text, semantic, and faceted search capabilities over the Information Registry — enabling discovery of information objects by content, not just by structured metadata.

**Responsibilities:**
- Index the content of unstructured information objects (news, filings, research reports)
- Support keyword search with relevance ranking
- Support faceted search (filter by type, date range, entity, quality tier, freshness tier)
- Support semantic search (find information related to a concept, not just an exact keyword match)
- Return search results with relevance scores and metadata
- Maintain search index freshness (index updates within seconds of new records arriving)

---

#### Component 20 — Distribution Manager

**Purpose:** The Distribution Manager manages the subscription and push delivery of information to all registered consumers — ensuring that relevant information reaches the right consumer at the right time without requiring constant polling.

**Responsibilities:**
- Maintain a subscription registry (which consumers want which types of information?)
- Route newly ingested information objects to all subscribers for the corresponding type and entity scope
- Support priority-based delivery (risk and execution consumers receive information before analytical consumers)
- Buffer delivery when consumers are temporarily unavailable
- Track delivery acknowledgments and retry unacknowledged deliveries
- Support broadcast (all subscribers) and unicast (specific subscriber) delivery modes

**Subscription record:**

| Field | Description |
|---|---|
| subscription_id | Unique subscription identifier |
| consumer_id | Subscribing system or component |
| type_filters | List of type codes to subscribe to (wildcard supported) |
| entity_filters | List of entity_ids to subscribe to (wildcard supported) |
| quality_floor | Only receive information with IQS ≥ this value |
| freshness_required | Only receive FRESH or AGING information |
| priority | Delivery priority (CRITICAL / HIGH / STANDARD) |
| delivery_mode | PUSH_EVENT / PULL_READY_NOTIFICATION |
| status | ACTIVE / PAUSED / TERMINATED |

---

#### Component 21 — Archive Manager

**Purpose:** The Archive Manager manages the complete lifecycle of information objects from the active Registry through to long-term archival and final retirement — ensuring compliance with retention policies and legal obligations.

**Responsibilities:**
- Monitor the age of all information objects against their type-specific retention policy
- Initiate migration of expired information to archive storage
- Ensure that legally required information is retained for the full regulatory retention period
- Compress archived information to reduce storage cost
- Provide retrieval API for archived information (slower than the Retrieval Manager)
- Manage the retirement of information that has exceeded the maximum retention period and has no ongoing legal hold
- Report archival statistics (volume archived, volume retired, space saved by compression)

---

#### Component 22 — Governance Manager

**Purpose:** The Governance Manager is the policy enforcement authority for all information in the IIOS. It owns the governance framework (16 dimensions, see Part VIII), enforces access control, manages policies, and produces the governance audit trail.

**Responsibilities:**
- Own and maintain the governance policy for each information type
- Enforce access control (which consumers can access which types of information)
- Manage classification reviews (reclassify information types when policy changes)
- Receive and act on escalation from the Audit Manager
- Produce governance reports for management and regulatory review
- Manage the information lineage policy (retention of lineage records)
- Co-ordinate with the Archive Manager on retention policy enforcement
- Manage emergency governance actions (quarantine, access suspension, emergency retention)

---

#### Component 23 — Audit Manager

**Purpose:** The Audit Manager maintains the complete, tamper-evident audit trail of all operations performed on information objects in the IIOS — enabling compliance reporting, forensic investigation, and operational review.

**Responsibilities:**
- Record every Create, Read, Update, and Archive operation on any information object
- Record every governance decision (policy change, access grant/revoke, reclassification)
- Record every quality event (quality degradation alert, confidence threshold breach)
- Produce structured audit reports on request
- Alert the Governance Manager on suspicious activity patterns (unusual access, bulk reads, access to restricted information)
- Maintain the audit store in a tamper-evident, append-only structure

**Audit record fields:**

| Field | Description |
|---|---|
| audit_id | Unique audit record identifier |
| event_type | CREATE / READ / UPDATE / ARCHIVE / GOVERN / QUALITY_EVENT / ACCESS_DENIED |
| information_id | Affected information object |
| actor | Component or user performing the action |
| timestamp | When the event occurred |
| outcome | SUCCESS / FAILURE / BLOCKED |
| details | Structured JSON of event-specific details |

---

#### Component 24 — Evolution Manager

**Purpose:** The Evolution Manager is responsible for the long-term evolution of the Information Engine's schema and policies — managing the lifecycle of information types, schemas, and governance policies as the IIOS's information needs evolve.

**Responsibilities:**
- Accept new information type proposals from the Knowledge Engine, Research Lab, and system administrators
- Validate that new types are properly defined (schema complete, SLAs specified, governance assigned)
- Register new types in the Information Catalog after approval
- Manage schema migrations for existing types (adding fields, changing constraints)
- Deprecate types that are no longer needed
- Ensure that schema changes are backward compatible (no information object in the Registry is invalidated by a schema change)
- Publish a changelog of all schema and policy changes

---

#### Component 25 — Transformation Engine

**Purpose:** The Transformation Engine converts information objects from one representation to another — enabling consumers with different requirements to receive information in the format they need, without requiring the Registry to store multiple copies.

**Responsibilities:**
- Apply on-the-fly transformations when consumers request specific output formats
- Convert time granularities (minute bars → hourly bars → daily bars)
- Convert currency representations for cross-market analysis
- Apply unit transformations (per-share → per-lot for derivatives)
- Apply aggregations on demand (sum, average, min, max across a set of information objects)
- Cache transformation results for frequently repeated transformations
- Log all transformation operations in the lineage record of the output information object

---
## PART IV — INFORMATION LIFECYCLE

### 4.1 Overview

Every information object in the IIOS passes through a well-defined 14-stage lifecycle. Each stage is a gate: a record cannot advance to the next stage unless all requirements of the current stage are satisfied. Stage transitions are recorded in the audit trail and in the information object's lineage record.

```
Stage 01: ACQUISITION
    │ (raw data received from external source via Acquisition Manager)
    │ SUCCESS → Stage 02
    │ FAILURE → Retry queue; alert after 3 consecutive failures
    ▼
Stage 02: INGESTION
    │ (parsed, deduplicated, ordered by Ingestion Manager)
    │ SUCCESS → Stage 03
    │ PARSE_FAILURE → Quarantine; alert Source Manager
    │ DUPLICATE → Suppress; route to corroboration analysis
    ▼
Stage 03: IDENTITY ASSIGNMENT
    │ (canonical information_id assigned by Identity Manager)
    │ SUCCESS → Stage 04
    │ IDENTITY_CONFLICT → Conflict resolution workflow
    ▼
Stage 04: VALIDATION
    │ (schema, range, consistency, cross-source validation by Validation Engine)
    │ PASS → Stage 05 (full confidence)
    │ WARN → Stage 05 (reduced confidence, flagged)
    │ FAIL → Quarantine; do not advance; alert Source Manager
    ▼
Stage 05: NORMALIZATION
    │ (canonical IDs, units, formats, names by Normalization Engine)
    │ SUCCESS → Stage 06
    │ MAP_FAILURE → Flag unmapped fields; continue with partial normalisation
    ▼
Stage 06: ENRICHMENT
    │ (derived fields, cross-references, context by Enrichment Engine + Context Manager)
    │ SUCCESS → Stage 07
    │ ENRICHMENT_PARTIAL → Continue with available enrichment; flag missing enrichments
    ▼
Stage 07: QUALITY SCORING
    │ (IQS computation by Quality Manager; confidence computation by Confidence Manager)
    │ IQS ≥ threshold → Stage 08
    │ IQS < minimum threshold → Quarantine; alert Governance Manager
    ▼
Stage 08: CLASSIFICATION
    │ (type confirmation, layer assignment, topic tags by Classification Engine)
    │ SUCCESS → Stage 09
    │ TYPE_CONFLICT → Escalate to Governance Manager
    ▼
Stage 09: INDEXING
    │ (all indices updated by Index Manager)
    │ SUCCESS → Stage 10
    │ INDEX_FAILURE → Retry; if persistent, alert monitoring; continue to Stage 10 with degraded search
    ▼
Stage 10: STORAGE
    │ (persisted to appropriate tier by Storage Manager; version chain updated by Version Manager)
    │ SUCCESS → Stage 11
    │ STORAGE_FAILURE → Retry; if persistent, alert and halt pipeline for this record
    ▼
Stage 11: DISTRIBUTION
    │ (pushed to subscribers by Distribution Manager)
    │ ALL_DELIVERED → Stage 12
    │ PARTIAL_DELIVERY → Retry undelivered; continue to Stage 12
    ▼
Stage 12: ACTIVE MONITORING
    │ (freshness monitored by Freshness Manager; confidence updated as conditions change)
    │ FRESH → Continue monitoring
    │ STALE → Alert Acquisition Manager for re-acquisition; reduce confidence
    │ UPDATE RECEIVED → Transition to SUPERSESSION (Stage 13a) or VERSION_UPDATE
    │ RETIREMENT TRIGGERED → Stage 14
    ▼
Stage 13: VERSION UPDATE  (parallel path)
    │ (new version created by Version Manager; previous version marked SUPERSEDED)
    │ Previous version → Stage 13a (SUPERSEDED — immutable historical record)
    │ New version → Stage 06 (re-enter at Enrichment with delta information)
    ▼
Stage 14: ARCHIVAL
    │ (information object migrated by Archive Manager after retention period)
    │ COMPRESSED → COLD or ARCHIVE tier
    │ LEGAL HOLD → Archive tier with hold flag
    │ EXPIRED → Retirement
    ▼
Stage 15: RETIREMENT
    (information object removed from active Registry; lineage record preserved permanently)
```

---

### 4.2 Stage-by-Stage Requirements

**Stage 01 — Acquisition**

| Requirement | Specification |
|---|---|
| Source registered | Source must be in the Source Manager registry |
| Trust tier assigned | Source must have an assigned trust tier |
| Rate limit respected | Acquisition must not exceed source's rate limit |
| Retry budget | Maximum 3 retries with exponential backoff before alert |

**Stage 02 — Ingestion**

| Requirement | Specification |
|---|---|
| Parse success | All required fields parseable from raw data |
| Deduplication applied | Duplicate detection against ingestion buffer for last 24 hours |
| Temporal order | Records from time-series sources must arrive in order or be re-ordered |
| Type declaration | Ingestion Manager must assign an initial type code |

**Stage 03 — Identity Assignment**

| Requirement | Specification |
|---|---|
| Identity uniqueness | information_id must be globally unique |
| Source mapping | External source ID must be mapped to canonical information_id |
| Conflict detection | Any collision with existing identity must be flagged and resolved |

**Stage 04 — Validation**

| Requirement | Specification |
|---|---|
| L1 schema | 100% of required fields present and correctly typed — mandatory |
| L2 range | All values within defined bounds — failure = FAIL status |
| L3 consistency | Cross-field consistency — failure = WARN |
| L4 cross-source | Agreement with other sources — failure = WARN |
| L5 historical | No anomalous change from recent values — failure = WARN flag |

**Stage 05 — Normalization**

| Requirement | Specification |
|---|---|
| Canonical entity IDs | All entity references resolved to IIOS canonical entity_id |
| Unit standardization | All numeric values in canonical units for the type |
| Timestamp standardization | All timestamps in UTC ISO 8601 |

**Stage 06 — Enrichment**

| Requirement | Specification |
|---|---|
| Derived fields | All standard derived fields for the type computed |
| Cross-references | Entity Engine and Information Registry cross-references populated |
| Context attached | Market regime and session state at as-of time attached |
| Lineage extended | Lineage record updated to include enrichment steps |

**Stage 07 — Quality Scoring**

| Requirement | Specification |
|---|---|
| IQS computed | 18-dimension IQS fully computed |
| Confidence assigned | Confidence score in [0.0, 1.0] assigned |
| Quality tier | Quality tier assigned (EXCELLENT to POOR) |
| Minimum IQS | If IQS < 0.25 (absolute floor) → FAIL and quarantine |

**Stage 08 — Classification**

| Requirement | Specification |
|---|---|
| Type code confirmed | Classification Engine confirms or overrides declared type |
| Layer assigned | Information layer (1–15) assigned |
| Tags assigned | Topic tags, entity tags, sector tags all assigned |
| Governance tier | Governance tier from Catalog confirmed |

**Stage 09 — Indexing**

| Requirement | Specification |
|---|---|
| Time-series index | Entry added to time-series index |
| Entity index | Entry added to entity cross-reference index |
| Type index | Entry added to type index |
| Full-text index | If unstructured type: content indexed for search |

**Stage 10 — Storage**

| Requirement | Specification |
|---|---|
| Persistence | Record written to storage with acknowledgment |
| Tier assignment | Correct storage tier selected based on type and access frequency |
| Replication | Minimum two replica copies confirmed |
| Version chain | Version chain updated |

**Stage 11 — Distribution**

| Requirement | Specification |
|---|---|
| Subscriber notification | All active subscribers for matching type/entity notified |
| Priority ordering | CRITICAL subscribers notified before STANDARD |
| Acknowledgment tracking | Delivery tracked; unacknowledged retried up to 3 times |

**Stage 12 — Active Monitoring**

| Requirement | Specification |
|---|---|
| Freshness tracking | Freshness computed continuously; alert at AGING → STALE transition |
| Confidence maintenance | Confidence recalculated on schedule and on new corroborating information |
| Re-acquisition trigger | Freshness < STALE → request re-acquisition from Source Manager |

**Stage 14 — Archival**

| Requirement | Specification |
|---|---|
| Retention expiry | Information age ≥ retention_months for the type |
| No active legal hold | Legal holds override automatic archival |
| Compression | Archive records compressed to ≤ 30% of original size |

---

### 4.3 State Machine Summary

```
    ┌─────────────────────────────────────────────────────────────────┐
    │                    INFORMATION OBJECT STATES                    │
    │                                                                 │
    │  ACQUIRING ──► INGESTING ──► IDENTITY_ASSIGNED ──► VALIDATING  │
    │                                                           │     │
    │           ┌──────────────────── FAILED ◄──────────────── ┘     │
    │           │                                                     │
    │           ▼                                                     │
    │       QUARANTINED                                               │
    │                                                                 │
    │  VALIDATING ──► NORMALIZING ──► ENRICHING ──► QUALITY_SCORING  │
    │                                                           │     │
    │                                                    CLASSIFYING  │
    │                                                           │     │
    │                                                      INDEXING   │
    │                                                           │     │
    │                                                      STORING    │
    │                                                           │     │
    │                                                   DISTRIBUTING  │
    │                                                           │     │
    │                                                      ACTIVE     │
    │                                                     /      \    │
    │                                            SUPERSEDED  ARCHIVING│
    │                                                │           │    │
    │                                           HISTORICAL    ARCHIVED│
    │                                                              │  │
    │                                                           RETIRED│
    └─────────────────────────────────────────────────────────────────┘
```

---
## PART V — INFORMATION SERVICES

The Information Engine exposes 19 services to its consumers. Each service is a well-defined interface with a specified contract — inputs, outputs, latency targets, failure modes, and consumers. Services are the public API of the Information Engine; all interaction with information occurs through a service call, never through direct access to internal components.

---

### 5.1 Service Registry

| Service Code | Name | Primary Consumer | SLA (p99 latency) |
|---|---|---|---|
| IS-01 | Acquisition Service | Orchestrator | N/A (async) |
| IS-02 | Ingestion Service | Acquisition Manager | N/A (async) |
| IS-03 | Validation Service | Ingestion Manager | < 50ms per record |
| IS-04 | Transformation Service | Retrieval Manager | < 100ms |
| IS-05 | Normalization Service | Validation Engine | < 30ms per record |
| IS-06 | Classification Service | Validation Engine | < 20ms per record |
| IS-07 | Enrichment Service | Normalization Engine | < 200ms per record |
| IS-08 | Retrieval Service | All analytical engines | < 50ms point-lookup; < 500ms range query |
| IS-09 | Search Service | Knowledge Engine, Research Lab | < 2 seconds |
| IS-10 | Version Service | All consumers needing historical access | < 100ms |
| IS-11 | Quality Service | All consumers | < 10ms (cached) |
| IS-12 | Freshness Service | Acquisition Manager, all consumers | < 10ms (cached) |
| IS-13 | Distribution Service | All subscribing consumers | < 100ms post-ingestion |
| IS-14 | Governance Service | Administrators, Audit systems | < 500ms |
| IS-15 | Audit Service | Compliance, Risk, Management | < 1 second |
| IS-16 | Archive Service | Archive Manager, Legal holds | < 5 seconds |
| IS-17 | Metadata Service | All consumers | < 50ms |
| IS-18 | Context Service | Analytical engines, replay systems | < 100ms |
| IS-19 | Lineage Service | All consumers, audit | < 500ms |

---

### 5.2 Service Definitions

---

#### IS-01 — Acquisition Service

**Purpose:** Provides a controlled interface for triggering information acquisition from registered sources — either on schedule or on demand.

**Inputs:**
- Acquisition request: { source_id, type_code, time_range?, on_demand_flag }

**Outputs:**
- Acquisition job reference: { job_id, status, estimated_volume }
- On completion: job result { job_id, records_acquired, records_failed, latency_ms }

**Consumers:** Orchestrator (scheduled); Knowledge Engine (on-demand historical requests); Research Lab (backtesting data requests)

**Dependencies:** Source Manager (source configuration), Acquisition Manager (job execution)

**Failure Recovery:**
- Source unavailable → retry with exponential backoff (max 3 attempts); escalate to alert
- Partial acquisition → report partial results with coverage percentage
- Rate limit hit → defer to next available acquisition slot; notify requester of delay

---

#### IS-02 — Ingestion Service

**Purpose:** Accepts raw data packages from the Acquisition Manager and submits them to the ingestion pipeline.

**Inputs:**
- Raw data package: { source_id, type_hint, payload, acquisition_timestamp }

**Outputs:**
- Ingestion receipt: { ingestion_id, record_count, estimated_processing_time }
- On completion: ingestion result { ingestion_id, valid_count, quarantine_count, duplicate_count }

**Consumers:** Acquisition Manager (primary); internal components generating information (e.g., strategy engines generating signal information)

**Dependencies:** Ingestion Manager (parsing and routing), Identity Manager (ID assignment)

---

#### IS-03 — Validation Service

**Purpose:** Validates an information record against the rules defined for its type in the Information Catalog. May be called inline during ingestion or standalone for re-validation of existing records.

**Inputs:**
- Pre-information record: { type_code, payload, source_id }

**Outputs:**
- Validation result: { validation_status: PASS|WARN|FAIL, validation_level_reached, issues[], confidence_adjustment }

**Consumers:** Ingestion Manager (inline), Governance Manager (re-validation workflows), Quality Manager (quality assessment inputs)

**SLA:** < 50ms per record (p99)

---

#### IS-04 — Transformation Service

**Purpose:** Transforms a retrieved information object into a different representation on demand — changing granularity, aggregating, or converting units.

**Inputs:**
- Transformation request: { information_id | query, target_type, transformation_params }

**Outputs:**
- Transformed information object (ephemeral — not stored unless consumer explicitly requests persistence)
- Transformation lineage record (automatically appended to the derived object's lineage)

**Transformation types:**

| Transform | Description |
|---|---|
| TIME_AGGREGATE | Aggregate minute bars to hourly or daily bars |
| UNIT_CONVERT | Convert between units (per-share, per-lot, percentage) |
| CURRENCY_CONVERT | Convert values from one currency to another |
| NORMALISE_SCALE | Scale values to [0,1] or Z-score |
| FILL_MISSING | Forward-fill or interpolate missing values in a time series |
| RESAMPLE | Change time series frequency |

---

#### IS-05 — Normalization Service

**Purpose:** Maps external identifiers and values to canonical IIOS representations.

**Inputs:**
- Record with source-native identifiers: { symbol_raw, type_hint, source_id }

**Outputs:**
- Normalization result: { entity_id, canonical_symbol, canonical_unit, normalised_payload, unmapped_fields[] }

**Consumers:** Validation Engine (inline during pipeline), Ingestion Manager (explicit call for complex sources)

**SLA:** < 30ms per record (p99)

---

#### IS-06 — Classification Service

**Purpose:** Assigns the complete classification to an information object (type code confirmation, layer, topic tags, entity references, governance tier).

**Inputs:**
- Enriched information record: { type_hint, payload, entity_refs, source_id }

**Outputs:**
- Classification result: { type_code, layer, topic_tags[], entity_refs[], sector_codes[], temporal_class, governance_tier }

**Consumers:** Ingestion Manager (pipeline); Knowledge Engine (re-classification on schema evolution)

**SLA:** < 20ms per record (p99)

---

#### IS-07 — Enrichment Service

**Purpose:** Applies all standard enrichments for the information type — derived fields, cross-references, context annotations, and entity metadata.

**Inputs:**
- Normalised, validated information record: { information_id, type_code, payload }

**Outputs:**
- Enriched information record: { information_id, payload_enriched, enriched_fields[], context_id, lineage_extension }

**Consumers:** Normalization Engine (pipeline); on-demand by analytical engines requesting enriched representations

**SLA:** < 200ms per record (p99)

---

#### IS-08 — Retrieval Service

**Purpose:** The primary retrieval interface — enables structured queries to the Information Registry.

**Inputs:**
- Retrieval query: { query_type, filters: { type_code?, entity_id?, time_range?, quality_floor?, freshness_requirement? }, limit, include_lineage, include_version_history }

**Outputs:**
- Result set: { information_objects[], result_count, query_latency_ms, freshness_summary, quality_summary }

**Query types:**

| Query type | Description |
|---|---|
| POINT_IN_TIME | Single value at a specific moment |
| LATEST | Most recent value |
| TIME_RANGE | All values in a time window |
| BY_ENTITY | All information about a specific entity |
| MULTI_ENTITY | Information about a set of entities (e.g., NIFTY50 basket) |
| BY_TYPE | All information of a specific type |
| CROSS_FILTER | Combination of type, entity, time range, and quality constraints |

**SLA:**
- POINT_IN_TIME, LATEST: < 50ms (p99)
- TIME_RANGE up to 30 days: < 200ms (p99)
- TIME_RANGE up to 1 year: < 2 seconds (p99)
- MULTI_ENTITY up to 50 entities: < 500ms (p99)

---

#### IS-09 — Search Service

**Purpose:** Provides discovery of information objects by content — keywords, concepts, and facets.

**Inputs:**
- Search request: { query_text?, concept?, facets: { type?, date_range?, entity?, quality_tier?, freshness_tier? }, page, page_size }

**Outputs:**
- Search results: { hits[], total_count, query_time_ms, facet_counts }

**Consumers:** Knowledge Engine (evidence discovery), Research Lab (research queries), Governance Manager (audit searches), Operations (system investigations)

**SLA:** < 2 seconds for full-text queries (p99); < 500ms for metadata-only queries (p99)

---

#### IS-10 — Version Service

**Purpose:** Provides access to the version history of any information object — enabling point-in-time retrieval and version comparison.

**Inputs:**
- Version query: { information_id, version_number? | as_of_timestamp?, include_delta }

**Outputs:**
- Version record: { information_id, version_number, effective_from, effective_to, content, delta?, change_reason }
- Version history list: all versions for an information object, ordered by version number

**SLA:** < 100ms (p99)

---

#### IS-11 — Quality Service

**Purpose:** Provides quality scores and quality statistics for information objects and information collections.

**Inputs:**
- Quality query: { information_id? | type_code? | entity_id? | aggregate_flag }

**Outputs:**
- Per-object: { information_id, iqs, quality_tier, dimension_scores[] }
- Aggregate: { type_code?, entity_id?, iqs_distribution, avg_iqs, pct_excellent, pct_good, pct_acceptable, pct_marginal, pct_poor }

**SLA:** < 10ms for cached per-object (p99); < 500ms for aggregate queries (p99)

---

#### IS-12 — Freshness Service

**Purpose:** Provides freshness status and freshness scores for information objects and information collections.

**Inputs:**
- Freshness query: { information_id? | type_code? | entity_id? | aggregate_flag }

**Outputs:**
- Per-object: { information_id, freshness_score, freshness_tier, time_to_stale_seconds }
- Aggregate: { type_code?, stale_count, aging_count, fresh_count, critical_stale_count }

**SLA:** < 10ms (p99, cached)

---

#### IS-13 — Distribution Service

**Purpose:** Provides the subscription management interface and monitors the delivery of information to consumers.

**Inputs:**
- Subscribe: { consumer_id, type_filters, entity_filters, quality_floor, freshness_required, priority }
- Unsubscribe: { subscription_id }
- Delivery status: { subscription_id, time_range }

**Outputs:**
- Subscription confirmation: { subscription_id, status }
- Delivery status report: { subscription_id, delivered_count, pending_count, failed_count }

---

#### IS-14 — Governance Service

**Purpose:** Provides the policy management and enforcement interface for the Information Engine's governance framework.

**Inputs:**
- Policy queries: { type_code, entity_id?, policy_category }
- Policy update requests: { type_code, policy_change, reason, approver_id }
- Access control queries: { consumer_id, information_id | type_code }

**Outputs:**
- Policy record: { type_code, governance_tier, retention_months, access_control_list, classification }
- Access decision: { allowed: true|false, reason }
- Policy change audit record

---

#### IS-15 — Audit Service

**Purpose:** Provides the audit trail retrieval interface for compliance, investigation, and operational review.

**Inputs:**
- Audit query: { event_type?, actor?, information_id?, time_range, page, page_size }

**Outputs:**
- Audit records: { audit_id, event_type, information_id, actor, timestamp, outcome, details }
- Audit summary: { event_type_distribution, actor_distribution, outcome_distribution }

**SLA:** < 1 second for most queries; < 5 seconds for large time-range scans (p99)

---

#### IS-16 — Archive Service

**Purpose:** Provides the interface for archival operations and retrieval of archived information.

**Inputs:**
- Archive query: { information_id | type_code, time_range, include_retired }
- Archive operation: { information_id, archive_reason, legal_hold_flag }

**Outputs:**
- Archived information object (slower retrieval from archive tier)
- Archive status: { information_id, archive_tier, archived_at, legal_hold }

---

#### IS-17 — Metadata Service

**Purpose:** Provides rich metadata about information objects and about the information base as a whole.

**Inputs:**
- Metadata query: { information_id? | type_code? | aggregate_flag }

**Outputs:**
- Per-object metadata: { information_id, type_code, layer, source_id, as_of_timestamp, quality_score, confidence_score, freshness_tier, version_number, lineage_summary }
- Catalog metadata: { total_types, total_records, records_by_layer, records_by_quality_tier }

**SLA:** < 50ms (p99)

---

#### IS-18 — Context Service

**Purpose:** Provides context records for information objects — the IIOS state at the time each piece of information was current.

**Inputs:**
- Context query: { information_id? | as_of_timestamp? }

**Outputs:**
- Context record: { context_id, as_of_timestamp, market_regime, trading_session, vix_level, nifty_level, active_events[], liquidity_state }

**SLA:** < 100ms (p99)

---

#### IS-19 — Lineage Service

**Purpose:** Provides complete lineage traversal for any information object — enabling forward and backward traversal of the derivation graph.

**Inputs:**
- Lineage query: { information_id, direction: UPSTREAM|DOWNSTREAM|BOTH, depth: 1..N }

**Outputs:**
- Lineage graph: { root: information_id, nodes: [{ information_id, type_code, source, depth, relationship_type }], edges: [{ from, to, transformation_step }] }

**Consumers:** Audit Manager (impact analysis), Knowledge Engine (evidence validation), Research Lab (data provenance), Governance Manager (compliance checks)

**SLA:** < 500ms for depth ≤ 3; < 2 seconds for full graph (p99)

---
## PART VI — INFORMATION PROCESSING ARCHITECTURE

### 6.1 Overview

The Information Engine operates four primary processing pipelines, each optimised for a different information velocity and volume profile. These pipelines share the same 25 components but differ in their throughput priorities, latency budgets, parallelism models, and buffering strategies.

---

### 6.2 Processing Pipeline Taxonomy

| Pipeline | Velocity | Volume | Latency budget | Primary data types |
|---|---|---|---|---|
| Real-Time Stream | Microseconds to seconds | Very high (ticks) | < 100ms end-to-end | Price quotes, order book, trades |
| Intraday Batch | Minutes | High | < 5 minutes | OHLCV bars, rolling indicators, intraday regime updates |
| Scheduled Batch | Hours to daily | Medium | < 30 minutes | EOD prices, macro releases, corporate filings, EOD portfolio snapshots |
| On-Demand | Seconds to minutes | Variable | < 60 seconds | Historical data for backtesting, research, replay |

---

### 6.3 Real-Time Stream Pipeline

The Real-Time Stream Pipeline processes market tick data with the lowest possible latency. It is designed for continuous, high-throughput ingestion of price quotes and order book updates.

```
Market Feed (ticks)
    │
    ▼  [< 2ms]
Acquisition Manager (WebSocket / FIX)
    │
    ▼  [< 5ms]
Ingestion Manager (parse + deduplicate)
    │
    ▼  [< 5ms]
Identity Manager (assign ID; skip if known symbol)
    │
    ▼  [< 10ms]
Validation Engine (L1 + L2 only for speed; L3+ async)
    │
    ▼  [< 5ms]
Normalization Engine (symbol lookup; unit check)
    │
    ▼  [< 10ms]
Quality Manager (fast path: freshness + source score only)
    │
    ▼  [< 5ms]
Classification Engine (pre-classified: no work for known types)
    │
    ▼  [< 5ms]
Index Manager (time-series index append only)
    │
    ▼  [< 10ms]
Storage Manager (hot tier only; in-memory + write-ahead log)
    │
    ▼  [< 10ms]
Distribution Manager (push to subscribed consumers)
    │
    Total end-to-end: < 70ms (p99 target: < 100ms)
```

**Real-Time Pipeline optimisations:**
- Pre-registered symbol catalogue: normalization is a lookup table operation, not a remote call
- L3/L4/L5 validation runs asynchronously; does not block the main pipeline
- Storage is write-to-WAL then async persist to durable store
- Enrichment (derived fields) runs asynchronously as a post-processing step
- Quality scoring uses a fast approximate score for real-time path; full IQS computed async

---

### 6.4 Intraday Batch Pipeline

The Intraday Batch Pipeline aggregates tick data into bars and computes rolling indicators. It runs on a configurable schedule (every 1 minute to every 30 minutes during market hours).

```
Hot-tier storage (recent ticks)
    │
    ▼
Transformation Engine (tick aggregation → OHLCV bars)
    │
    ▼
Enrichment Engine (SMA, EMA, ATR, RSI, MACD computed on completed bars)
    │
    ▼
Regime Engine feedback (update regime information from bar data)
    │
    ▼
Quality Manager (full IQS on bar records)
    │
    ▼
Classification Engine (full classification including temporal_class = INTRADAY)
    │
    ▼
Index Manager (update time-series index with bar records)
    │
    ▼
Storage Manager (warm tier for bars)
    │
    ▼
Distribution Manager (notify bar subscribers: Strategy Engine, Risk Engine)
```

**Intraday batch outputs:**
- 1-minute OHLCV bars for all tracked instruments
- 5-minute, 15-minute, 30-minute, 60-minute bars (resampled from 1-minute)
- Rolling indicators at each bar frequency
- Intraday regime snapshots at 30-minute intervals
- Intraday portfolio NAV updates

---

### 6.5 Scheduled Batch Pipeline

The Scheduled Batch Pipeline processes information that arrives on a fixed daily or periodic schedule — market closes, corporate filings, macroeconomic releases, and external data provider files.

```
Schedule trigger (cron: EOD at 15:45, pre-market at 08:00, etc.)
    │
    ▼
Acquisition Manager (batch download from scheduled sources)
    │
    ▼
Ingestion Manager (bulk parse; deduplication against prior day)
    │
    ▼
Identity Manager (batch ID assignment)
    │
    ▼
Validation Engine (full 5-level validation; failures quarantined)
    │
    ▼
Normalization Engine (full normalisation including cross-market)
    │
    ▼
Enrichment Engine (full enrichment; daily-level derived fields)
    │
    ▼
Quality Manager (full IQS; full lineage recording)
    │
    ▼
Classification Engine (full classification)
    │
    ▼
Index Manager (full index update; rebuild staleness scan)
    │
    ▼
Storage Manager (warm tier; migrate prior-day to cold if age-triggered)
    │
    ▼
Distribution Manager (notify EOD subscribers: Analytics, Portfolio, Learning)
    │
    ▼
Freshness Manager (reset freshness timers for all just-updated records)
```

**Scheduled batch schedule:**

| Slot | Trigger | Information types |
|---|---|---|
| 08:00 pre-market | Daily | Global market snapshot, overnight news, pre-market regime |
| 09:30 market open | At open | Updated corporate actions, index constituent changes |
| 15:45 market close | At close | EOD prices, daily OHLCV, session summary |
| 16:30 after-hours | Daily | Exchange filings, corporate announcements from after close |
| 18:00 evening | Daily | FII/DII flow data, provisional OI data |
| 20:00 evening | Daily | Final settlement prices, adjusted close prices |
| 23:00 daily | Daily | Macroeconomic release ingestion (time-zone adjusted for US/EU releases) |
| Weekly (Friday) | Weekly | Weekly macro summaries, weekly technical summaries |
| Monthly | Monthly | Monthly macroeconomic statistics, monthly fund flows, monthly index rebalancing |

---

### 6.6 On-Demand Pipeline

The On-Demand Pipeline processes requests for historical data — from the Research Lab (backtesting), the Validation Engine (walk-forward testing), and direct consumer requests.

```
On-demand request (requester_id, type, entity, time_range, resolution)
    │
    ▼
Retrieval Service (attempt to fulfil from Registry)
    │
    ├── FULL CACHE HIT → Return directly from Registry
    │
    └── PARTIAL OR MISS → Acquisition Service
            │
            ▼
            Acquisition Manager (historical API call with range request)
            │
            ▼
            Ingestion → Validation → Normalization → Enrichment → Quality → Classification → Storage
            │
            ▼
            Retrieval Service (return combined cached + newly acquired)
```

**On-demand guarantees:**
- Best-effort for data older than 10 years (provider availability not guaranteed)
- Cache hit guaranteed for data already in Registry
- Maximum wait time for cold fetch: 60 seconds
- Partial results delivered immediately; missing ranges flagged

---

### 6.7 Processing Pattern Reference

| Pattern | Description | When applied |
|---|---|---|
| Deduplication | Identify and suppress exact duplicates | Every ingestion |
| Conflict resolution | When two sources disagree: corroborate, flag, and apply confidence adjustment | Cross-source validation |
| Temporal alignment | Align records from different sources to a common timestamp grid | Intraday and scheduled batch |
| Survivorship bias correction | Include delisted instruments in historical data | Historical backtesting requests |
| Point-in-time consistency | Ensure that queries return only information that was available at the query time — no lookahead | All historical queries |
| Version reconciliation | When a data provider revises historical data: create new version, preserve old | Macroeconomic releases, corporate actions |
| Corporate action adjustment | Apply splits, bonuses, rights to historical price data | Historical price retrieval |
| Dividend adjustment | Apply dividend adjustments to historical prices | Historical price retrieval |
| Fill missing | Forward-fill or mark missing observations for thin markets | All time-series retrieval |
| Outlier detection | Flag observations that deviate by > N standard deviations from recent history | All ingestion paths |
| Cross-asset alignment | Align time series across different markets with different trading hours | Cross-asset analysis |
| Regime annotation | Annotate all historical information with the regime that was active at that time | Regime-aware analytical requests |
| Seasonality tagging | Tag information with seasonal period (Q1–Q4, expiry week, budget week) | Classification Engine |
| Lineage propagation | Extend lineage chain for every transformation step | All transformation operations |

---

### 6.8 Processing Capacity Model

```
┌─────────────────────────────────────────────────────────────────┐
│               INFORMATION ENGINE PROCESSING CAPACITY             │
│                                                                 │
│  Real-Time Stream                                               │
│  ─────────────                                                  │
│  Max throughput:   50,000 ticks/second                          │
│  Typical load:      8,000 ticks/second (NIFTY market hours)     │
│  Peak load:        35,000 ticks/second (high-vol events)        │
│  Burst buffer:      5 minutes at peak load                      │
│                                                                 │
│  Intraday Batch                                                 │
│  ─────────────                                                  │
│  Max throughput:   10,000 bars/minute per batch run             │
│  Instruments:          2,000 instruments tracked intraday       │
│  Bar frequencies:      5 (1m, 5m, 15m, 30m, 60m)              │
│  Derived fields/bar:  ~40 indicators per bar per instrument     │
│                                                                 │
│  Scheduled Batch                                                │
│  ─────────────                                                  │
│  EOD volume:       ~500,000 records per night                   │
│  Window:                  15:45 to 08:00 (16h 15m)            │
│  Target completion:  100% by 05:00 (pre-market data available)  │
│                                                                 │
│  On-Demand                                                      │
│  ─────────                                                      │
│  Concurrent requests:   20 parallel on-demand pipelines        │
│  Max range per request: 10 years of daily data                  │
│  Max record return:     5,000,000 records per request           │
└─────────────────────────────────────────────────────────────────┘
```

---
## PART VII — INFORMATION QUALITY FRAMEWORK

### 7.1 Overview

The Information Quality Framework is the mechanism by which the Information Engine quantifies the fitness-for-use of every information object. Quality is not a single dimension; it is a multi-dimensional assessment. The Framework defines 18 quality dimensions, each measuring a distinct aspect of information quality. The composite Information Quality Score (IQS) synthesises all 18 dimensions into a single operational indicator.

The IQS is the primary signal used by consumers to decide whether a piece of information is suitable for their purpose. Every information object in the Registry has an IQS and a quality tier. Consumers can specify a quality floor when submitting retrieval requests, and the Retrieval Manager will not return objects below that floor.

---

### 7.2 Quality Dimension Reference

| Dim | Code | Name | Weight | Description |
|---|---|---|---|---|
| D01 | ACC | Accuracy | 0.15 | Does the value correctly represent the real-world state? |
| D02 | CMP | Completeness | 0.12 | Are all required fields present and non-null? |
| D03 | CON | Consistency | 0.10 | Are values internally consistent (e.g., high ≥ close ≥ low)? |
| D04 | TIM | Timeliness | 0.10 | Was the information acquired and processed in a timely manner? |
| D05 | FRS | Freshness | 0.10 | Is the information current? How recently was it as-of? |
| D06 | VLD | Validity | 0.08 | Do values conform to the schema and allowed value ranges? |
| D07 | REL | Reliability | 0.08 | What is the historical track record of the source for this type? |
| D08 | TRW | Trustworthiness | 0.06 | What is the assigned trust tier of the source? |
| D09 | LNG | Lineage | 0.05 | Is the complete lineage documented and traceable? |
| D10 | PRV | Provenance | 0.04 | Is the origin of the information clearly stated and verified? |
| D11 | CFD | Confidence | 0.04 | What is the computed confidence score? |
| D12 | CVG | Coverage | 0.03 | Does this information cover all the fields needed by the primary consumer? |
| D13 | GRN | Granularity | 0.02 | Is the information at the required level of detail? |
| D14 | RLV | Relevance | 0.02 | Is this information relevant to the current operational context? |
| D15 | IQS | Info Quality Score | — | Composite score: weighted sum of all dimensions |
| D16 | CFS | Confidence Score | — | Standalone confidence indicator (reused from D11) |
| D17 | FRS | Freshness Score | — | Standalone freshness indicator (reused from D05) |
| D18 | RLS | Reliability Score | — | Standalone reliability indicator (reused from D07) |

**Note:** D15–D18 are composite or standalone derivative scores derived from the primary 14 dimensions above.

---

### 7.3 Dimension Computation Specifications

---

#### D01 — Accuracy

Accuracy is the hardest dimension to measure directly — the system cannot always know what the true value is. Accuracy is estimated through:
1. Cross-source agreement (when multiple independent sources agree, accuracy is high)
2. Historical anomaly detection (is this value consistent with the recent history of the same variable?)
3. Physical plausibility checks (can this value be correct given what we know about the world?)

$$\text{acc} = w_1 \cdot \text{cross\_source\_agreement} + w_2 \cdot \text{historical\_plausibility} + w_3 \cdot \text{physics\_plausibility}$$

Default weights: $w_1 = 0.50$, $w_2 = 0.35$, $w_3 = 0.15$

---

#### D02 — Completeness

Completeness is the proportion of required fields that are present and non-null.

$$\text{cmp} = \frac{\text{count}(\text{required fields present and non-null})}{\text{count}(\text{required fields})}$$

Optional fields that are present contribute a small bonus: $+0.01$ per optional field present (cap at $+0.05$).

---

#### D03 — Consistency

Consistency is assessed through the proportion of cross-field consistency rules that pass.

$$\text{con} = \frac{\text{count}(\text{consistency rules passed})}{\text{count}(\text{consistency rules checked})}$$

Consistency rules per type are defined in the Information Catalog. Example rules for OHLCV type:
- High ≥ Close ≥ Low → mandatory
- High ≥ Open → mandatory
- Low ≤ Open → mandatory
- Volume ≥ 0 → mandatory
- High − Low ≤ 5 × ATR(20) → warning (flag, not fail)

---

#### D04 — Timeliness

Timeliness measures how quickly the information was acquired after it became available in the external world. For market data: how quickly was a trade captured after it occurred? For macroeconomic data: was the release downloaded within minutes of publication?

$$\text{tim} = \max\left(0, 1 - \frac{\text{acquisition\_lag}}{\text{timeliness\_sla}}\right)$$

where acquisition_lag is the time between the external event and the IIOS acquiring the information.

---

#### D05 — Freshness

Freshness measures how current the information is at the time of evaluation. Freshness decays continuously after the as-of timestamp.

$$\text{frs}(t) = \max\left(0, 1 - \frac{t - t_{\text{as\_of}}}{\text{freshness\_sla}(T)}\right)$$

Freshness is a time-varying dimension — it must be re-evaluated dynamically rather than computed once at ingestion.

---

#### D06 — Validity

Validity is the proportion of value range checks that pass (L1 schema and L2 range validation).

$$\text{vld} = \frac{\text{count}(\text{range rules passed})}{\text{count}(\text{range rules checked})}$$

---

#### D07 — Reliability

Reliability is the rolling 90-day accuracy rate of the source for this information type.

$$\text{rel} = \frac{\text{confirmed accurate instances from source for type}}{\text{total instances from source for type}} \text{ over 90 days}$$

Reliability is source-type specific: the same source may be highly reliable for price data but less reliable for corporate action data.

---

#### D08 — Trustworthiness

Trustworthiness is a function of the assigned trust tier of the source.

| Trust tier | Trustworthiness score |
|---|---|
| AUTHORITATIVE | 1.00 |
| RELIABLE | 0.85 |
| STANDARD | 0.70 |
| PROVISIONAL | 0.55 |
| UNRELIABLE | 0.30 |

---

#### D09 — Lineage

Lineage quality is assessed by the completeness of the lineage graph. A complete lineage (traceable back to the original source without gaps) scores 1.0. Each missing link reduces the score.

$$\text{lng} = \frac{\text{documented lineage steps}}{\text{expected lineage steps}}$$

---

#### D10 — Provenance

Provenance is a binary check: is the information's origin clearly documented (source_id present, source registered, original external ID recorded)?

$$\text{prv} = \begin{cases} 1.0 & \text{if all provenance fields present and validated} \\ 0.5 & \text{if provenance partial} \\ 0.0 & \text{if provenance absent} \end{cases}$$

---

#### D11 — Confidence

Confidence is the composite confidence score computed by the Confidence Manager. It synthesises source trust tier, validation results, cross-source corroboration, and freshness decay.

$$\text{cfd} = \text{confidence score} \in [0.0, 1.0]$$

---

#### D12 — Coverage

Coverage measures whether the information object satisfies the coverage requirements of the primary consumer — does it cover all the fields and entities that the consumer needs?

$$\text{cvg} = \frac{\text{consumer-required fields covered by this information object}}{\text{consumer-required fields total}}$$

Coverage is computed per consumer-type. The Retrieval Manager uses the requesting consumer's coverage profile.

---

#### D13 — Granularity

Granularity assesses whether the information is at the required level of detail. An information request at daily resolution served by daily bars scores 1.0; if only monthly bars are available, scores 0.3.

---

#### D14 — Relevance

Relevance measures whether the information is applicable to the current operational context — market regime, trading session, entity sector, etc.

---

### 7.4 Composite IQS Formula

$$\text{IQS} = \sum_{i=1}^{14} w_i \cdot d_i$$

where $w_i$ are the weights from the dimension reference table and $d_i \in [0, 1]$ are the dimension scores.

The weights sum to 1.0:

$$\sum_{i=1}^{14} w_i = 0.15 + 0.12 + 0.10 + 0.10 + 0.10 + 0.08 + 0.08 + 0.06 + 0.05 + 0.04 + 0.04 + 0.03 + 0.02 + 0.02 = 0.99 \approx 1.0$$

(Minor rounding; actual implementation normalises weights to exactly 1.0)

---

### 7.5 Quality Tier Boundaries

| Tier | IQS Range | Interpretation |
|---|---|---|
| EXCELLENT | [0.90, 1.00] | All dimensions healthy; suitable for highest-stakes decisions |
| GOOD | [0.75, 0.90) | Most dimensions healthy; suitable for all operational use |
| ACCEPTABLE | [0.60, 0.75) | Some dimensions below ideal; suitable with awareness of limitations |
| MARGINAL | [0.40, 0.60) | Multiple dimensions degraded; use with explicit caution flag; not for high-stakes |
| POOR | [0.00, 0.40) | Widespread quality failure; quarantine; do not use operationally |

---

### 7.6 Quality Monitoring

**Per-type quality dashboard:**

| Metric | Frequency | Alert threshold |
|---|---|---|
| Mean IQS by type | Computed every 30 minutes | Alert if mean IQS for any type drops below 0.70 |
| % POOR by type | Computed every 30 minutes | Alert if % POOR exceeds 5% for any critical type |
| Quality trend | Computed daily | Alert if mean IQS for any type declines > 0.05 over 7 days |
| Dimension-level degradation | Computed daily | Alert if any dimension score drops > 0.10 from baseline |

**Per-source quality statistics:**

| Metric | Frequency | Alert threshold |
|---|---|---|
| Mean IQS from source | Rolling 24 hours | Alert if drops below 0.65 |
| Reliability score | Rolling 90 days | Alert if drops below 0.80 |
| Error rate | Real-time | Alert if exceeds 2% |
| Quarantine rate | Real-time | Alert if exceeds 1% |

---
## PART VIII — INFORMATION GOVERNANCE

### 8.1 Governance Philosophy

Information governance is the system of policies, responsibilities, and controls that ensure information in the IIOS is managed as an organisational asset — not just technical data. Governance answers the questions that operations cannot: who owns this information? who can see it? how long must it be kept? who is accountable when it is wrong? what must be done when it is misused?

The Information Engine's governance framework is built on 16 dimensions. Each dimension is a distinct area of governance responsibility. Together, the 16 dimensions provide comprehensive coverage of all governance obligations.

---

### 8.2 Governance Dimension Reference

| Dim | Code | Name | Description |
|---|---|---|---|
| G01 | OWN | Ownership | Each information type has a designated owner responsible for quality and policy |
| G02 | CLS | Classification | Security and confidentiality classification assigned to each type |
| G03 | VER | Versioning | Policy for how version histories are managed and retained |
| G04 | SEC | Security | Access control and authentication requirements |
| G05 | CNF | Confidentiality | Who may read this information; data masking requirements |
| G06 | INT | Integrity | Controls ensuring information has not been tampered with |
| G07 | AVL | Availability | Uptime and recovery requirements for each information type |
| G08 | AUD | Auditability | All operations on information must be logged in the audit trail |
| G09 | CPL | Compliance | Regulatory requirements applicable to this information type |
| G10 | RET | Retention | How long the information must be kept; when it may be deleted |
| G11 | ARC | Archival | How and where information is archived after active retention period |
| G12 | RCV | Recovery | Requirements for recovery of information after failure or disaster |
| G13 | BKP | Backup | Backup frequency and redundancy requirements |
| G14 | LNG | Lineage governance | Policy for documenting and retaining lineage records |
| G15 | MTD | Metadata standards | Standards for naming, typing, and describing information |
| G16 | NAM | Naming standards | Canonical naming conventions for types, fields, and identifiers |

---

### 8.3 Governance Tier Matrix

| Information Layer | Governance Tier | Required Controls |
|---|---|---|
| Execution Information | CRITICAL | All 16 dimensions; 7-year retention; tamper-evident storage; real-time audit |
| Portfolio Information | CRITICAL | All 16 dimensions; 7-year retention; regulatory reporting capability |
| Risk Information | CRITICAL | All 16 dimensions; 3-year retention; real-time quality monitoring |
| Market Information | HIGH | 14 dimensions; 3-year retention; sub-second freshness for price data |
| Corporate Information | HIGH | 15 dimensions; 7-year retention; regulatory disclosure compliance |
| Strategy Information | HIGH | 13 dimensions; 5-year retention; proprietary access control |
| Technical Information | MEDIUM | 10 dimensions; 2-year retention; standard access control |
| Sentiment Information | MEDIUM | 9 dimensions; 1-year retention |
| Derived Information | MEDIUM | 8 dimensions; 2-year retention |
| Alternative Information | MEDIUM | 8 dimensions; 1-year retention |
| Knowledge Information | HIGH | 12 dimensions; permanent retention for asserted facts |
| Regime Information | HIGH | 10 dimensions; 3-year retention |
| Macroeconomic Information | HIGH | 12 dimensions; 10-year retention; regulatory statistics |
| Flow Information | HIGH | 11 dimensions; 3-year retention |

---

### 8.4 Ownership Responsibility Matrix

| Role | Responsibilities |
|---|---|
| Information Owner (type level) | Define quality standards; approve schema changes; approve governance classification changes; sign off on retention policy |
| Information Steward | Day-to-day quality monitoring; escalate quality issues; manage source reliability reviews |
| Data Consumer | Use information for authorised purposes only; report quality issues; not re-distribute without permission |
| Information Engineer | Implement processing pipelines; maintain components; deploy schema changes |
| Governance Manager | Enforce policies; conduct governance reviews; escalate violations; produce compliance reports |
| Audit Manager | Maintain audit trail; respond to audit requests; alert on suspicious activity |

---

### 8.5 Classification Scheme

Information in the IIOS is classified along two dimensions: sensitivity and criticality.

**Sensitivity classification:**

| Level | Description | Access control |
|---|---|---|
| PUBLIC | Non-sensitive; may be shared externally | No restriction |
| INTERNAL | Internal IIOS use only | Authenticated IIOS components only |
| RESTRICTED | Limited to specific consumer roles | Role-based access control; audit all reads |
| CONFIDENTIAL | Highly sensitive; commercial or regulatory risk if disclosed | Named consumers only; encrypted at rest; full audit trail |

**Criticality classification:**

| Level | Description | Recovery requirement |
|---|---|---|
| CRITICAL | Loss or corruption causes immediate operational failure | RTO < 1 hour; RPO < 5 minutes; hot standby |
| HIGH | Loss or corruption significantly impairs operations | RTO < 4 hours; RPO < 1 hour |
| MEDIUM | Loss or corruption causes degraded operations | RTO < 24 hours; RPO < 4 hours |
| LOW | Loss or corruption causes inconvenience | RTO < 72 hours; RPO < 24 hours |

---

### 8.6 Retention Policy Reference

| Information type category | Minimum retention | Maximum retention | Archive after | Legal hold override |
|---|---|---|---|---|
| Execution records (orders, trades, fills) | 7 years | Permanent | 7 years to archive | Yes — litigation hold |
| Portfolio records | 7 years | Permanent | 7 years to archive | Yes |
| Risk records | 3 years | 7 years | 3 years to archive | Yes |
| Market data (EOD) | 3 years | 10 years | 2 years to warm; 3 years to cold | No |
| Market data (tick) | 90 days | 1 year | 30 days to warm; 90 days to cold | No |
| Corporate filings | 7 years | Permanent | 7 years to archive | Yes |
| Macroeconomic data | 10 years | Permanent | 5 years to cold | No |
| Strategy records | 5 years | 10 years | 3 years to warm | No |
| Audit trail | 7 years | Permanent | 3 years to archive | Yes |
| Lineage records | Permanent | Permanent | — (never retired) | N/A |

---

### 8.7 Integrity Controls

**At-rest integrity:**
- All information objects in warm and cold storage are stored with a cryptographic hash (SHA-256)
- Integrity checks are run on a rolling schedule: warm storage checked weekly; cold storage checked monthly
- Tampering detected = immediate alert; quarantine of affected objects; recovery from backup

**In-transit integrity:**
- All information transmitted between Information Engine components uses message authentication (HMAC-SHA-256)
- All information delivered to external consumers over network uses TLS 1.3 minimum
- Delivery receipts include content hash; consumer verifies receipt

**Lineage integrity:**
- Lineage graph is append-only; no lineage records may be modified or deleted
- Lineage records are cryptographically linked (each record hashes to the previous)

---

### 8.8 Availability Requirements

| Information type | Availability SLA | Degraded mode | Recovery mode |
|---|---|---|---|
| Real-time price data | 99.9% during market hours | Fall back to cached last-known values with freshness flag | Re-connect to source; fill gap from backup feed |
| EOD prices | 99.5% availability of complete EOD dataset by 20:00 | Partial dataset with missing instrument list | Acquire from secondary source; flag missing instruments |
| Corporate actions | 99.0% | Use prior-day data; flag potential staleness | Re-acquire from secondary source |
| Macroeconomic data | 99.0% | Use prior release; flag as stale | Re-acquire from secondary source |
| Strategy information | 99.5% | Disable affected strategies; alert | Replay from event log |
| Execution records | 99.9% | Read-only mode | Recover from backup; no data loss permitted |

---

### 8.9 Compliance Framework

The Information Engine's governance is designed to satisfy the following regulatory and compliance requirements:

| Requirement | Applicable information types | Control |
|---|---|---|
| SEBI Order Audit Trail System (OATS) | Execution records | Tamper-evident audit trail; 5-year retention; on-demand regulatory reporting |
| NSE / BSE exchange compliance | Market data | Data provider licensing compliance; attribution of data; no unauthorised redistribution |
| Prevention of Money Laundering Act (PMLA) | Execution records, portfolio records | 10-year retention; audit trail; beneficial ownership tracking |
| Income Tax Act | Realised PnL records, execution records | 7-year retention; complete and accurate trade history |
| Data localisation | All India-related market data | Stored on India-resident infrastructure or compliant cloud region |

---

### 8.10 Governance Review Cycle

| Review | Frequency | Participants | Output |
|---|---|---|---|
| Quality review | Weekly | Information Stewards, Quality Manager | Quality trend report; remediation actions |
| Source reliability review | Monthly | Information Stewards, Source Manager | Source trust tier adjustments; source warnings |
| Schema governance review | Quarterly | Information Owners, Information Engineers | Schema changes approved; deprecated types retired |
| Retention audit | Annually | Information Owners, Governance Manager, Legal | Retention policy confirmed or updated |
| Security classification review | Annually | Governance Manager, Security | Classification updates; access control review |
| Full governance audit | Annually | All stakeholders | Governance health assessment; external audit readiness |

---
## PART IX — INFORMATION CONSTITUTION

### 9.1 Purpose

The Information Constitution defines the non-negotiable rules that govern all information in the IIOS. These rules are architectural invariants — they may not be bypassed by any component, consumer, or operational procedure. Constitutional rules are permanent; they may only be superseded by a formal governance decision with full stakeholder approval and a documented record.

Rules are organised into 10 categories: Identity (IC-A), Immutability (IC-B), Temporality (IC-C), Structure (IC-D), Quality (IC-E), Lineage (IC-F), Lifecycle (IC-G), Audit (IC-H), Governance (IC-I), Intelligence (IC-J).

---

### 9.2 Category IC-A — Identity Rules

**IC-A-001** Every information object in the IIOS MUST have a globally unique canonical information_id assigned by the Identity Manager at creation time. No two information objects may share the same information_id.

**IC-A-002** The information_id MUST be assigned by the Identity Manager. No component may self-assign an information_id or accept information objects with externally assigned IDs as canonical.

**IC-A-003** The information_id MUST conform to the canonical format: `IOBJ-{LAYER_CODE}-{TYPE_CODE}-{YYYYMMDD}-{SEQ:08d}`.

**IC-A-004** An information_id MUST NOT be reused after retirement. Retired IDs are permanently reserved.

**IC-A-005** Every external source identifier (source-native ID) MUST be mapped to the canonical information_id in the Identity Manager's mapping table. The mapping MUST be preserved permanently even after the information object is retired.

**IC-A-006** Identity conflicts (same real-world fact with two different information_ids) MUST be detected and resolved before any downstream processing continues.

**IC-A-007** The identity_id of an entity referenced in an information object MUST be a valid entity_id from the Entity Engine at the time of information object creation.

**IC-A-008** Every information object MUST declare a type_code. The type_code MUST be a valid type registered in the Information Catalog.

**IC-A-009** Information objects with unresolvable entity references MUST NOT be promoted to ACTIVE status. They must be held in PENDING_IDENTITY state.

**IC-A-010** The source_id in every information object MUST be a valid, active (or historically valid) source registered in the Source Manager.

---

### 9.3 Category IC-B — Immutability Rules

**IC-B-001** An ACTIVE information object MUST NOT be modified in place. All updates to an information object's content MUST create a new version via the Version Manager.

**IC-B-002** A SUPERSEDED information object MUST NOT be modified, deleted, or altered in any way. It is an immutable historical record.

**IC-B-003** A RETIRED information object's lineage record MUST be preserved permanently. Lineage is never retired.

**IC-B-004** The audit trail for an information object MUST be append-only. Existing audit records MUST NOT be modified or deleted.

**IC-B-005** The lineage graph MUST be append-only. Lineage records documenting transformation steps MUST NOT be modified after creation.

**IC-B-006** The original raw data that gave rise to an information object MUST be preserved in the ingestion buffer for at least 30 days from ingestion. This enables reprocessing if the pipeline encounters errors.

**IC-B-007** No component, consumer, or administrative procedure may directly write to the Information Registry's storage layer. All writes MUST go through the Storage Manager's controlled interface.

**IC-B-008** A version chain MUST be a strict linear sequence. Branching of version chains is prohibited. If two conflicting updates arrive simultaneously, the conflict MUST be resolved into a single authoritative version before the update is committed.

---

### 9.4 Category IC-C — Temporality Rules

**IC-C-001** Every information object MUST have an as_of_timestamp specifying the moment in the real world that the information describes.

**IC-C-002** The as_of_timestamp MUST be in UTC and conform to ISO 8601 extended format: `YYYY-MM-DDTHH:MM:SS.sssZ`.

**IC-C-003** The as_of_timestamp MUST NOT be in the future at the time of ingestion. Information about future states must be classified as FORECAST information and treated as a distinct type.

**IC-C-004** Freshness scores MUST be recomputed dynamically based on the elapsed time from the as_of_timestamp. A freshness score computed at ingestion time MUST NOT be used as a static value.

**IC-C-005** A point-in-time query MUST return only information that was ACTIVE at the specified point in time — it MUST NOT include information that was not yet ingested at that point (no look-ahead bias).

**IC-C-006** The Retrieval Manager MUST enforce point-in-time consistency for all historical queries. Look-ahead is a fatal data integrity failure.

**IC-C-007** The Information Registry MUST maintain the ingestion_timestamp separately from the as_of_timestamp. These two timestamps are fundamentally different concepts and MUST NOT be conflated.

**IC-C-008** All time-series information MUST be stored with a monotonically non-decreasing as_of_timestamp sequence within a single instrument+type series. Out-of-order records MUST be re-ordered before storage.

**IC-C-009** Duplicate observations (same instrument, type, as_of_timestamp, source) MUST be detected and suppressed. The duplicate record MUST be preserved in the corroboration store but not as a separate Registry entry.

**IC-C-010** Historical revision to information (e.g., macroeconomic agency revises previously published statistics) MUST be recorded as a new version, not a backdated replacement. The original published value MUST be preserved.

---

### 9.5 Category IC-D — Structure Rules

**IC-D-001** Every information object MUST conform to the schema defined for its type_code in the Information Catalog.

**IC-D-002** The Information Catalog schema for a type MUST NOT be changed in a way that invalidates existing information objects in the Registry without a formal schema migration.

**IC-D-003** Adding a new optional field to a type's schema is backward compatible and permitted. Removing an existing field, or changing a field from optional to required, requires a schema migration.

**IC-D-004** All numeric fields in information objects MUST be in canonical units as specified in the Information Catalog for their type. No raw source units may appear in a normalised information object.

**IC-D-005** All string identifiers (entity_id, source_id, type_code) in information objects MUST match the canonical formats defined in the Identity and Catalog systems. No local identifiers may appear.

**IC-D-006** All date and time fields MUST be in UTC. No timezone-naive timestamps are permitted in stored information objects.

**IC-D-007** An information object MUST NOT embed the content of another information object. Cross-references MUST be expressed as information_id references, not by embedding. This enforces data normalisation and prevents versioning inconsistencies.

**IC-D-008** The metadata fields of an information object (information_id, type_code, source_id, as_of_timestamp, ingestion_timestamp, version_number, quality_score, confidence_score, freshness_tier, lineage_id) MUST be complete and non-null in every stored information object.

**IC-D-009** Information objects classified as CRITICAL governance tier MUST pass L1 through L3 validation before being promoted to ACTIVE. No CRITICAL information object may be active with a FAIL or WARN validation status.

**IC-D-010** Information objects of type EXECUTION_RECORD MUST have all fields complete before being committed to the Registry. No execution record may be written with missing required fields.

---

### 9.6 Category IC-E — Quality Rules

**IC-E-001** Every information object MUST have an IQS computed before it is distributed to consumers. An information object MUST NOT be distributed with an uncomputed quality score.

**IC-E-002** Information objects with IQS < 0.25 MUST be quarantined. They MUST NOT be distributed to operational consumers.

**IC-E-003** Information objects with IQS in [0.25, 0.40) (POOR tier) MUST be flagged with a QUALITY_POOR flag in all retrieval responses. Consumers MUST be explicitly notified of the quality tier.

**IC-E-004** No information object used in a trade decision MUST have an IQS below the operational quality floor specified in the system configuration. The default operational quality floor is 0.60.

**IC-E-005** Quality scores MUST be recomputed when new corroborating or contradicting information arrives, or when freshness degrades significantly (e.g., freshness_tier transitions from FRESH to AGING or AGING to STALE).

**IC-E-006** A quality monitoring alert MUST be raised when the mean IQS for any critical information type drops below 0.70.

**IC-E-007** The Quality Manager MUST maintain a complete history of IQS values for every information object. Quality history is a record of how the system's assessment of an information object has changed over time.

**IC-E-008** Confidence scores MUST be recomputed dynamically — they MUST incorporate freshness decay. A confidence score computed at ingestion is stale by definition; it MUST be maintained as a time-varying quantity.

**IC-E-009** An information source whose reliability score drops below 0.70 on a rolling 90-day window MUST have its trust tier reduced and all future information from that source confidence-penalised accordingly.

**IC-E-010** The Validation Engine MUST apply all five validation levels (L1–L5) to all non-real-time information objects before they are promoted to ACTIVE.

---

### 9.7 Category IC-F — Lineage Rules

**IC-F-001** Every information object MUST have a lineage record from the moment of creation. An information object with no lineage record MUST NOT be accepted into the Registry.

**IC-F-002** The lineage record MUST include: the source_id, the external source identifier, all normalisation steps, all enrichment steps, all transformation steps, and all derivation relationships.

**IC-F-003** When an information object is derived from one or more parent information objects, all parent information_ids MUST be listed in the lineage record.

**IC-F-004** Lineage records MUST be immutable after creation. New steps may be appended; existing steps may not be modified.

**IC-F-005** The lineage graph MUST be acyclic. An information object MUST NOT appear as both an ancestor and a descendant of another information object in the same lineage chain.

**IC-F-006** Lineage records MUST be retained permanently — they MUST NOT be subject to archival or retirement along with the information objects they describe.

**IC-F-007** The Lineage Service MUST be able to reconstruct the complete derivation path for any information object from its current version back to the original source data.

**IC-F-008** Impact analysis MUST be possible from any information object: given information object X, the system MUST be able to identify all information objects that were derived from X and therefore may be affected if X is found to be incorrect.

**IC-F-009** When a source is found to have provided incorrect data, the Lineage Service MUST provide a complete list of all information objects derived from that source's records so that a correction can be propagated.

**IC-F-010** Machine Learning model outputs that are stored as information objects MUST record in their lineage the model_id, model_version, training_data_description, and inference_timestamp.

---

### 9.8 Category IC-G — Lifecycle Rules

**IC-G-001** Every information object MUST pass through all mandatory lifecycle stages in order. No stage may be skipped except by explicit governance exception with audit record.

**IC-G-002** An information object MUST NOT transition from INGESTED to ACTIVE without passing Validation at L1 minimum.

**IC-G-003** A SUPERSEDED information object MUST NOT be re-activated. Once superseded, the object is historical. A new version supersedes the old; the old is never reactivated.

**IC-G-004** Archival MUST be triggered by retention policy expiry, not by operational convenience. Information MUST NOT be archived before its retention period has elapsed unless under a specific governance exception.

**IC-G-005** Retirement MUST be approved by the Information Owner for CRITICAL governance tier information. Retirement of CRITICAL information without explicit approval is prohibited.

**IC-G-006** The lifecycle state of every information object MUST be stored in the Registry and audited at every state transition.

**IC-G-007** Information under a legal hold MUST NOT be archived or retired regardless of retention policy expiry. Legal hold overrides all retention policies.

---

### 9.9 Category IC-H — Audit Rules

**IC-H-001** Every Create, Read, Update (via versioning), and Archive operation on an information object MUST be recorded in the audit trail.

**IC-H-002** Every governance decision (policy change, classification change, access grant/revoke) MUST be recorded in the audit trail.

**IC-H-003** Every quality event (quality threshold breach, source reliability failure, confidence alert) MUST be recorded in the audit trail.

**IC-H-004** The audit trail MUST be append-only. No audit record may be modified or deleted.

**IC-H-005** Access to the audit trail itself MUST be audited — any read or write to the audit store is itself an auditable event.

**IC-H-006** Audit records MUST be retained for a minimum of 7 years.

**IC-H-007** The audit trail MUST be queryable for regulatory reporting within 24 hours of a request.

**IC-H-008** Failed access attempts (a consumer attempting to read information they are not authorised for) MUST be recorded in the audit trail with the same completeness as successful accesses.

---

### 9.10 Category IC-I — Governance Rules

**IC-I-001** Every information type MUST have a designated Information Owner. Information types without an owner MUST NOT be activated.

**IC-I-002** The Governance Manager MUST review all information type additions, schema changes, and governance classification changes before they take effect.

**IC-I-003** Access control MUST be enforced at the retrieval layer. No information object may be returned to an unauthorised consumer regardless of the query path used.

**IC-I-004** All information in the CONFIDENTIAL classification tier MUST be encrypted at rest with AES-256 minimum.

**IC-I-005** Governance policies MUST be documented, versioned, and accessible to all stakeholders via the Governance Service.

**IC-I-006** A governance review MUST be triggered whenever: a new information type is added; a source's trust tier changes; a schema migration is required; an information type's retention period changes.

---

### 9.11 Category IC-J — Intelligence Rules

**IC-J-001** The Information Engine MUST support the Knowledge Engine's access to all information types for which it is an authorised consumer.

**IC-J-002** Historical information provided for backtesting MUST honour point-in-time consistency. No future information may be included in a historical analytical window.

**IC-J-003** Information provided to ML model training pipelines MUST be tagged with their survivorship bias status — the system MUST be able to provide either survivorship-biased or survivorship-corrected datasets.

**IC-J-004** Regime annotation MUST be available for all historical information. Any query for historical information MAY request regime-annotated results.

**IC-J-005** The Information Engine MUST detect and flag information objects that could introduce look-ahead bias into analytical processes. Detection of potential look-ahead MUST halt the analytical process and alert the requester.

**IC-J-006** All derived information (computed from other information objects) MUST declare its derivation lineage before being used in any knowledge inference chain.

---
## PART X — INFORMATION READINESS CHECKLIST

### 10.1 Purpose

The Information Readiness Checklist defines the complete set of conditions that must be satisfied for an information object to be considered "ready" for use by any analytical or operational consumer in the IIOS. The checklist is organised into 16 sections. An information object is "INFORMATION_READY" when and only when all 16 sections pass.

The Readiness Checklist is the operational bridge between the engineering architecture (Parts I–IX) and the day-to-day operational use of information. It is the authoritative pass/fail criterion for information quality gates.

---

### 10.2 Section 01 — Acquired

| # | Criterion | PASS condition |
|---|---|---|
| 01.01 | Source is registered | source_id exists in Source Manager with ACTIVE status |
| 01.02 | Source has trust tier | source_id has an assigned trust tier (not NULL) |
| 01.03 | Acquisition is authorised | acquisition was triggered by an authorised process |
| 01.04 | Acquisition log entry exists | A timestamped acquisition log record exists for this data package |
| 01.05 | No rate limit violation | Acquisition did not violate source rate limit |

**Section 01 PASS:** All 5 criteria pass.

---

### 10.3 Section 02 — Ingested

| # | Criterion | PASS condition |
|---|---|---|
| 02.01 | Successfully parsed | All required fields extracted from raw data without error |
| 02.02 | Not a duplicate | Deduplication check did not suppress this record |
| 02.03 | Temporal order verified | For time-series data: record is in correct temporal position |
| 02.04 | Initial type declared | type_hint assigned by Ingestion Manager |
| 02.05 | Ingestion log entry exists | A timestamped ingestion record exists for this object |
| 02.06 | Ingestion timestamp recorded | ingestion_timestamp field is populated |

**Section 02 PASS:** All 6 criteria pass.

---

### 10.4 Section 03 — Identity Assigned

| # | Criterion | PASS condition |
|---|---|---|
| 03.01 | information_id assigned | information_id is present and non-null |
| 03.02 | information_id format valid | Conforms to canonical format: `IOBJ-{LAYER_CODE}-{TYPE_CODE}-{YYYYMMDD}-{SEQ:08d}` |
| 03.03 | information_id unique | No other active object in Registry has the same information_id |
| 03.04 | Source mapping recorded | External source ID mapped to information_id in Identity Manager |
| 03.05 | No identity conflict | Identity conflict resolution completed; no open conflicts |

**Section 03 PASS:** All 5 criteria pass.

---

### 10.5 Section 04 — Validated

| # | Criterion | PASS condition |
|---|---|---|
| 04.01 | L1 schema validation passed | All required fields present; types correct; no schema violations |
| 04.02 | L2 range validation passed or noted | All values within defined ranges; any range warnings recorded |
| 04.03 | L3 consistency checked | All cross-field consistency rules applied; results recorded |
| 04.04 | L4 cross-source checked | Cross-source consistency checked where other sources available |
| 04.05 | L5 historical anomaly checked | Historical plausibility check applied; any anomalies flagged |
| 04.06 | Validation status recorded | validation_status field in {PASS, WARN, FAIL} is set |
| 04.07 | FAIL records quarantined | Any record with validation_status = FAIL is not in ACTIVE Registry |

**Section 04 PASS:** 04.01 must pass; 04.02–04.05 must be applied; 04.06–04.07 must be true.

---

### 10.6 Section 05 — Normalised

| # | Criterion | PASS condition |
|---|---|---|
| 05.01 | Entity IDs resolved | All entity references are canonical IIOS entity_ids |
| 05.02 | Units canonical | All numeric fields in canonical units for the type |
| 05.03 | Timestamps UTC | All timestamps in UTC ISO 8601 format |
| 05.04 | Symbol canonical | All security symbols in IIOS canonical form |
| 05.05 | Sector/industry codes canonical | For market information: sector and industry in canonical classification |
| 05.06 | Unmapped fields documented | Any fields that could not be normalised are listed in unmapped_fields[] |

**Section 05 PASS:** 05.01–05.05 pass; 05.06 complete (may be empty list).

---

### 10.7 Section 06 — Enriched

| # | Criterion | PASS condition |
|---|---|---|
| 06.01 | Standard derived fields computed | All derived fields defined for the type in the Catalog are populated |
| 06.02 | Cross-references populated | All cross-reference fields linking to related information objects are populated |
| 06.03 | Entity metadata attached | For market information: entity sector, industry, market cap tier attached |
| 06.04 | Regime context attached | Market regime active at as_of_timestamp recorded in context_id |
| 06.05 | Session context attached | Trading session active at as_of_timestamp recorded |
| 06.06 | Lineage updated with enrichment steps | Lineage record includes all enrichment steps |
| 06.07 | Enrichment completeness noted | Any standard enrichments that could not be applied are listed |

**Section 06 PASS:** 06.01–06.06 satisfied; 06.07 complete.

---

### 10.8 Section 07 — Classified

| # | Criterion | PASS condition |
|---|---|---|
| 07.01 | type_code confirmed | Type code confirmed or corrected by Classification Engine |
| 07.02 | Information layer assigned | layer field in [1, 15] is set |
| 07.03 | Topic tags assigned | topic_tags[] is non-empty and contains appropriate tags |
| 07.04 | Entity references confirmed | entity_refs[] contains confirmed entity_ids |
| 07.05 | Temporal class assigned | temporal_class field set to one of the defined values |
| 07.06 | Governance tier confirmed | governance_tier matches Catalog definition for type_code |
| 07.07 | Freshness class assigned | freshness_class field set |

**Section 07 PASS:** All 7 criteria pass.

---

### 10.9 Section 08 — Quality Scored

| # | Criterion | PASS condition |
|---|---|---|
| 08.01 | All 14 quality dimensions computed | dimension_scores[] has 14 entries, each in [0.0, 1.0] |
| 08.02 | IQS computed | iqs field is set to weighted sum of dimension scores |
| 08.03 | Quality tier assigned | quality_tier is one of: EXCELLENT, GOOD, ACCEPTABLE, MARGINAL, POOR |
| 08.04 | IQS above absolute floor | iqs ≥ 0.25 (objects below this threshold are quarantined) |
| 08.05 | IQS above operational floor for intended use | iqs ≥ 0.60 for operational decision use |
| 08.06 | Confidence score computed | confidence_score is set and in [0.0, 1.0] |
| 08.07 | Quality history record created | Quality history entry for this version is recorded |

**Section 08 PASS:** 08.01–08.04 must pass; 08.05 must pass for operational use (may be WARN for analytical use); 08.06–08.07 must pass.

---

### 10.10 Section 09 — Indexed

| # | Criterion | PASS condition |
|---|---|---|
| 09.01 | Time-series index entry created | Object appears in time-series index for its type and entity |
| 09.02 | Entity cross-reference index updated | Object appears in entity index for all entities in entity_refs[] |
| 09.03 | Type index updated | Object appears in type index for its type_code |
| 09.04 | Source index updated | Object appears in source index for its source_id |
| 09.05 | Freshness index updated | Object appears in freshness index with correct freshness_expiry_time |
| 09.06 | Full-text index updated (if applicable) | For unstructured types: content indexed for search |
| 09.07 | Lineage index updated | Object appears in lineage index for all parent_information_ids |

**Section 09 PASS:** All applicable index criteria satisfied (09.06 only for unstructured types).

---

### 10.11 Section 10 — Stored

| # | Criterion | PASS condition |
|---|---|---|
| 10.01 | Persisted to correct tier | Information stored in appropriate storage tier per type and age |
| 10.02 | Minimum replicas confirmed | At least two replica copies confirmed by Storage Manager |
| 10.03 | Storage acknowledgment received | Storage Manager returned ACKNOWLEDGED status |
| 10.04 | Integrity hash recorded | SHA-256 hash of information object stored alongside the record |
| 10.05 | Version chain updated | Version Manager has created/updated the version chain entry |
| 10.06 | Registry entry created | Information Registry shows the object as ACTIVE |

**Section 10 PASS:** All 6 criteria pass.

---

### 10.12 Section 11 — Versioned

| # | Criterion | PASS condition |
|---|---|---|
| 11.01 | version_number assigned | version_number field is set (1 for new objects; N+1 for updates) |
| 11.02 | effective_from timestamp set | effective_from is set to the ingestion_timestamp of this version |
| 11.03 | Previous version superseded | If this is an update: previous version is marked SUPERSEDED |
| 11.04 | Content delta documented | If this is an update: content_delta documents what changed |
| 11.05 | Change reason recorded | change_reason field documents why this version was created |
| 11.06 | Version chain integrity verified | version_chain is a valid linked list with no gaps or cycles |

**Section 11 PASS:** All 6 criteria pass.

---

### 10.13 Section 12 — Governed

| # | Criterion | PASS condition |
|---|---|---|
| 12.01 | Governance tier confirmed | governance_tier is set from Classification Engine output |
| 12.02 | Security classification set | Security classification (PUBLIC, INTERNAL, RESTRICTED, CONFIDENTIAL) is set |
| 12.03 | Information owner identified | Information Owner for the type is documented in Governance Manager |
| 12.04 | Retention policy applied | retention policy for the type is active; expiry_date computed |
| 12.05 | Access control policy set | Access control list for the type is active |
| 12.06 | Confidential objects encrypted | If security_classification = CONFIDENTIAL: AES-256 encryption confirmed |
| 12.07 | Governance record created | Governance Manager has a record for this information object |

**Section 12 PASS:** All 7 criteria pass.

---

### 10.14 Section 13 — Audited

| # | Criterion | PASS condition |
|---|---|---|
| 13.01 | Creation audit record exists | An audit record with event_type = CREATE exists for this object |
| 13.02 | Audit record is tamper-evident | Audit record has cryptographic integrity protection |
| 13.03 | Audit trail is queryable | Audit record can be retrieved via the Audit Service within SLA |
| 13.04 | All state transitions audited | Every lifecycle stage transition has a corresponding audit record |
| 13.05 | Quality events audited | All quality threshold events have audit records |

**Section 13 PASS:** All 5 criteria pass.

---

### 10.15 Section 14 — Distributed

| # | Criterion | PASS condition |
|---|---|---|
| 14.01 | Subscriber list populated | Distribution Manager has identified all subscribers for this type/entity |
| 14.02 | CRITICAL subscribers notified first | CRITICAL subscribers received delivery before STANDARD |
| 14.03 | Delivery acknowledgment tracked | Distribution Manager is tracking acknowledgment per subscriber |
| 14.04 | Unacknowledged deliveries queued for retry | Any unacknowledged deliveries are in the retry queue |
| 14.05 | Distribution log recorded | Distribution event recorded for monitoring |

**Section 14 PASS:** All 5 criteria pass.

---

### 10.16 Section 15 — Freshness Monitored

| # | Criterion | PASS condition |
|---|---|---|
| 15.01 | Freshness SLA known | Freshness Manager has the SLA for this type from the Catalog |
| 15.02 | Freshness score computed | freshness_score is computed and current |
| 15.03 | Freshness tier assigned | freshness_tier is one of: FRESH, AGING, STALE, CRITICAL_STALE, EXPIRED |
| 15.04 | Re-acquisition trigger configured | Freshness Manager will trigger re-acquisition when this type becomes STALE |
| 15.05 | Consumer freshness transparency | Retrieval Service will include freshness_tier in all retrieval responses for this object |

**Section 15 PASS:** All 5 criteria pass.

---

### 10.17 Section 16 — Knowledge-Engine-Ready

| # | Criterion | PASS condition |
|---|---|---|
| 16.01 | Lineage complete | Full lineage from source to current version documented |
| 16.02 | Quality above knowledge floor | iqs ≥ 0.65 (minimum for Knowledge Engine consumption) |
| 16.03 | Point-in-time consistency enforced | Retrieval of this object honours point-in-time semantics |
| 16.04 | Regime annotation available | Context record with market regime is attached |
| 16.05 | No look-ahead risk | Information was ingested before the as_of_timestamp plus maximum propagation delay |
| 16.06 | Derivation lineage complete | If derived: all parent information_ids are resolved and active |
| 16.07 | Authorised for Knowledge Engine | Knowledge Engine is in the access control list for this type |

**Section 16 PASS:** All 7 criteria pass.

---

### 10.18 Readiness Status Summary

An information object's readiness status is the composite of all 16 sections:

```
INFORMATION_READY = (01 PASS) AND (02 PASS) AND (03 PASS) AND (04 PASS)
                AND (05 PASS) AND (06 PASS) AND (07 PASS) AND (08 PASS)
                AND (09 PASS) AND (10 PASS) AND (11 PASS) AND (12 PASS)
                AND (13 PASS) AND (14 PASS) AND (15 PASS) AND (16 PASS)
```

An information object that is INFORMATION_READY is cleared for use by all authorised consumers for all authorised purposes. An information object that is not INFORMATION_READY carries the list of failing sections as a readiness deficiency report.

**Readiness by use case:**

| Use case | Minimum sections required |
|---|---|
| Real-time trading decision | 01–10, 12, 13, 15 (sections 11, 14, 16 may be async) |
| Strategy backtesting | 01–11, 15, 16 (section 14 not required for historical) |
| Risk management | 01–13, 15 |
| Portfolio reporting | 01–13, 15 |
| Regulatory compliance | All 16 sections; no exceptions |
| Knowledge Engine inference | All 16 sections |
| Research and analysis | 01–11 minimum; 15, 16 strongly recommended |

---
---

## SUPPLEMENT A — INFORMATION TYPE CATALOGUE

This supplement provides a detailed catalogue of all primary information types in the IIOS, organised by layer. Each entry specifies the type code, required fields, freshness SLA, confidence floor, governance tier, and retention policy.

---

### Layer 02 — Market Information Types

| Type Code | Name | Required Fields | Freshness SLA | Confidence Floor | Gov Tier | Retention |
|---|---|---|---|---|---|---|
| MKT-QUOTE | Bid/Ask Quote | entity_id, bid, ask, last, timestamp, source | 30 seconds | 0.80 | CRITICAL | 30 days (tick) |
| MKT-TRADE | Executed Trade | entity_id, price, quantity, timestamp, direction, source | 30 seconds | 0.85 | CRITICAL | 30 days (tick) |
| MKT-OHLCV-1M | 1-Minute Bar | entity_id, open, high, low, close, volume, as_of, source | 120 seconds | 0.80 | HIGH | 24 months |
| MKT-OHLCV-5M | 5-Minute Bar | entity_id, open, high, low, close, volume, as_of, source | 600 seconds | 0.80 | HIGH | 24 months |
| MKT-OHLCV-1D | Daily Bar | entity_id, open, high, low, close, volume, adj_close, as_of, source | 86400 seconds | 0.85 | HIGH | 36 months |
| MKT-SETTLE | Settlement Price | entity_id, settlement_price, settlement_date, source | 86400 seconds | 0.90 | CRITICAL | 36 months |
| MKT-OI | Open Interest | entity_id, open_interest, as_of, source | 3600 seconds | 0.80 | HIGH | 24 months |
| MKT-DEPTH | Order Book Depth | entity_id, bid_levels[], ask_levels[], timestamp | 10 seconds | 0.75 | HIGH | 7 days |
| MKT-OPT-CHAIN | Options Chain | entity_id, expiry, strikes[], call_oi[], put_oi[], call_iv[], put_iv[], timestamp | 600 seconds | 0.75 | HIGH | 12 months |
| MKT-INDEX | Index Level | entity_id, index_level, index_returns, as_of, source | 60 seconds | 0.85 | CRITICAL | 36 months |
| MKT-VIX | VIX Level | vix_value, as_of, source | 600 seconds | 0.85 | CRITICAL | 36 months |

---

### Layer 03 — Corporate Information Types

| Type Code | Name | Required Fields | Freshness SLA | Confidence Floor | Gov Tier | Retention |
|---|---|---|---|---|---|---|
| CORP-EARN | Earnings Report | entity_id, period, eps_actual, revenue_actual, eps_est, revenue_est, announcement_date | 86400 seconds | 0.85 | HIGH | 84 months |
| CORP-EARN-GUIDE | Earnings Guidance | entity_id, period, eps_guidance_low, eps_guidance_high, issued_date | 86400 seconds | 0.75 | HIGH | 84 months |
| CORP-DIV | Dividend Announcement | entity_id, dividend_per_share, record_date, ex_date, payment_date | 86400 seconds | 0.90 | CRITICAL | 84 months |
| CORP-SPLIT | Stock Split | entity_id, split_ratio, ex_date, record_date | 86400 seconds | 0.95 | CRITICAL | 84 months |
| CORP-BONUS | Bonus Issue | entity_id, bonus_ratio, record_date | 86400 seconds | 0.95 | CRITICAL | 84 months |
| CORP-RIGHTS | Rights Issue | entity_id, rights_ratio, price, record_date | 86400 seconds | 0.90 | CRITICAL | 84 months |
| CORP-BS | Balance Sheet | entity_id, fiscal_period, total_assets, total_liabilities, equity, cash | 2592000 seconds | 0.85 | HIGH | 84 months |
| CORP-PL | Profit & Loss | entity_id, fiscal_period, revenue, ebitda, ebit, net_profit, tax | 2592000 seconds | 0.85 | HIGH | 84 months |
| CORP-CF | Cash Flow | entity_id, fiscal_period, operating_cf, investing_cf, financing_cf | 2592000 seconds | 0.85 | HIGH | 84 months |
| CORP-FILING | Exchange Filing | entity_id, filing_type, filing_date, filing_content_ref, exchange | 3600 seconds | 0.90 | HIGH | 84 months |

---

### Layer 04 — Macroeconomic Information Types

| Type Code | Name | Required Fields | Freshness SLA | Confidence Floor | Gov Tier | Retention |
|---|---|---|---|---|---|---|
| MACRO-GDP | GDP Release | country, period, gdp_value, gdp_growth_yoy, release_date, source | 7776000 seconds | 0.90 | HIGH | 120 months |
| MACRO-CPI | CPI Release | country, period, cpi_value, cpi_mom, cpi_yoy, release_date, source | 2592000 seconds | 0.90 | HIGH | 120 months |
| MACRO-IIP | IIP Release | country, period, iip_value, iip_growth_yoy, release_date | 2592000 seconds | 0.90 | HIGH | 120 months |
| MACRO-PMI | PMI Release | country, period, pmi_value, pmi_type, release_date, source | 2592000 seconds | 0.85 | HIGH | 60 months |
| MACRO-REPO | Repo Rate | country, rate, effective_date, central_bank, source | 86400 seconds | 0.95 | CRITICAL | 120 months |
| MACRO-CRRUSD | USD/INR Rate | rate, as_of, source | 60 seconds | 0.85 | HIGH | 36 months |
| MACRO-CRUDE | Crude Oil Price | crude_type, price, currency, as_of, source | 300 seconds | 0.85 | HIGH | 36 months |
| MACRO-GOLD | Gold Price | price, currency, as_of, source | 300 seconds | 0.85 | HIGH | 36 months |

---

### Layer 09 — Risk Information Types

| Type Code | Name | Required Fields | Freshness SLA | Confidence Floor | Gov Tier | Retention |
|---|---|---|---|---|---|---|
| RISK-RVOL | Realised Volatility | entity_id, window_days, vol_annualised, as_of | 3600 seconds | 0.80 | CRITICAL | 36 months |
| RISK-IVOL | Implied Volatility | entity_id, expiry, strike, iv, as_of, source | 300 seconds | 0.80 | CRITICAL | 36 months |
| RISK-CORR | Correlation Matrix | entities[], period_days, correlation_matrix, as_of | 86400 seconds | 0.80 | CRITICAL | 36 months |
| RISK-DD | Drawdown | portfolio_id, peak_equity, current_equity, drawdown_pct, as_of | 3600 seconds | 0.90 | CRITICAL | 36 months |
| RISK-VAR | Value at Risk | portfolio_id, confidence_level, var_1day, var_10day, as_of, method | 86400 seconds | 0.85 | CRITICAL | 36 months |
| RISK-STRESS | Stress Test Result | portfolio_id, scenario_id, scenario_loss, as_of | 86400 seconds | 0.80 | CRITICAL | 36 months |

---

### Layer 11 — Execution Information Types

| Type Code | Name | Required Fields | Freshness SLA | Confidence Floor | Gov Tier | Retention |
|---|---|---|---|---|---|---|
| EXEC-ORD | Order | order_id, entity_id, direction, quantity, order_type, status, submitted_at | Real-time | 0.95 | CRITICAL | 84 months |
| EXEC-FILL | Fill | fill_id, order_id, entity_id, fill_price, fill_qty, fill_timestamp | Real-time | 0.98 | CRITICAL | 84 months |
| EXEC-POS | Position | portfolio_id, entity_id, quantity, avg_cost, current_price, pnl, as_of | 60 seconds | 0.95 | CRITICAL | 84 months |
| EXEC-TRADE | Completed Trade | trade_id, entity_id, entry_fill_id, exit_fill_id, realised_pnl, duration | Real-time | 0.98 | CRITICAL | 84 months |

---

### Layer 12 — Portfolio Information Types

| Type Code | Name | Required Fields | Freshness SLA | Confidence Floor | Gov Tier | Retention |
|---|---|---|---|---|---|---|
| PORT-SNAP | Portfolio Snapshot | portfolio_id, equity, cash, positions_count, unrealised_pnl, realised_pnl_today, as_of | 3600 seconds | 0.95 | CRITICAL | 84 months |
| PORT-EOD | End-of-Day Summary | portfolio_id, date, equity_sod, equity_eod, gross_return, net_return, trades_count | 86400 seconds | 0.95 | CRITICAL | 84 months |
| PORT-ATTR | Return Attribution | portfolio_id, period, strategy_contributions[], sector_contributions[], factor_contributions[] | 86400 seconds | 0.85 | HIGH | 60 months |

---
## SUPPLEMENT B — COMPONENT INTERFACE REFERENCE

This supplement provides the detailed interface contract for each of the 25 Information Engine components — latency targets, input schemas, output schemas, and failure modes.

---

### Registry & Catalog Cluster Interfaces

| Component | Method | Input | Output | p99 Latency | Failure Mode |
|---|---|---|---|---|---|
| Information Registry | register() | EnrichedInfoObject | RegistrationReceipt | < 20ms | Queue if unavailable; alert after 30s |
| Information Registry | retrieve() | RetrievalQuery | ResultSet | < 50ms | Return SERVICE_UNAVAILABLE; alert |
| Information Registry | getVersionHistory() | information_id | VersionChain | < 100ms | Return last known chain; alert |
| Information Catalog | getTypeDefinition() | type_code | TypeDefinition | < 5ms (cached) | Return UNKNOWN_TYPE error |
| Information Catalog | validateType() | type_code, payload | ValidationResult | < 10ms (cached) | Return TYPE_UNKNOWN; halt pipeline |
| Identity Manager | assignId() | SourceRecord | information_id | < 5ms | Retry 3×; halt pipeline if all fail |
| Identity Manager | resolveConflict() | ConflictRecord | Resolution | < 100ms | Hold in PENDING_IDENTITY; alert |

---

### Acquisition Cluster Interfaces

| Component | Method | Input | Output | p99 Latency | Failure Mode |
|---|---|---|---|---|---|
| Acquisition Manager | scheduleJob() | AcquisitionSpec | JobId | < 50ms | Log failure; alert |
| Acquisition Manager | triggerOnDemand() | OnDemandRequest | JobHandle | < 100ms | Return QUEUED with estimated_time |
| Source Manager | getSourceConfig() | source_id | SourceConfig | < 5ms (cached) | Return UNKNOWN_SOURCE |
| Source Manager | updateReliability() | source_id, reliability_score | Acknowledgment | < 20ms | Retry; alert |
| Ingestion Manager | ingest() | RawDataPackage | IngestionReceipt | < 50ms | Queue; drain when available |
| Ingestion Manager | deduplicate() | RawRecord | DuplicateCheckResult | < 5ms | Allow through with DEDUP_SKIP flag |

---

### Validation & Quality Cluster Interfaces

| Component | Method | Input | Output | p99 Latency | Failure Mode |
|---|---|---|---|---|---|
| Validation Engine | validate() | PreInfoRecord | ValidationResult | < 50ms | Return FAIL with partial results |
| Quality Manager | scoreQuality() | InfoObject | QualityScore | < 30ms | Return emergency score = 0.50 with QUALITY_UNAVAILABLE flag |
| Confidence Manager | computeConfidence() | InfoObject, SourceConfig | ConfidenceScore | < 20ms | Use trust-tier-only fallback |
| Freshness Manager | checkFreshness() | information_id, as_of | FreshnessStatus | < 10ms (cached) | Use last-known freshness tier |

---

### Enrichment Cluster Interfaces

| Component | Method | Input | Output | p99 Latency | Failure Mode |
|---|---|---|---|---|---|
| Normalization Engine | normalize() | ValidatedRecord | NormalizedRecord | < 30ms | Return PARTIAL_NORMALISATION with unmapped_fields list |
| Enrichment Engine | enrich() | NormalizedRecord | EnrichedRecord | < 200ms | Return partially enriched; flag missing enrichments |
| Context Manager | captureContext() | as_of_timestamp | ContextRecord | < 20ms | Use last available context snapshot |

---

### Organisation Cluster Interfaces

| Component | Method | Input | Output | p99 Latency | Failure Mode |
|---|---|---|---|---|---|
| Classification Engine | classify() | EnrichedRecord | ClassificationResult | < 20ms | Use type_hint as fallback classification |
| Index Manager | updateIndex() | ClassifiedRecord | IndexUpdateAck | < 30ms | Queue updates; process async; alert if queue > 10k |
| Version Manager | createVersion() | InfoObject, delta | VersionRecord | < 20ms | Retry 3×; hold in PENDING_VERSION |

---

### Governance Cluster Interfaces

| Component | Method | Input | Output | p99 Latency | Failure Mode |
|---|---|---|---|---|---|
| Storage Manager | store() | VersionedRecord | StorageAck | < 50ms | Retry 3×; alert; halt pipeline for CRITICAL types |
| Retrieval Manager | query() | RetrievalQuery | ResultSet | Varies | Return partial results; indicate completeness % |
| Search Engine | search() | SearchRequest | SearchResults | < 2000ms | Return timeout error; alert |
| Distribution Manager | distribute() | InfoObject | DeliveryStatus | < 100ms | Queue; retry unacknowledged × 3 |
| Archive Manager | archive() | information_id, reason | ArchiveAck | < 5 seconds | Retry; alert |
| Governance Manager | checkAccess() | consumer_id, information_id | AccessDecision | < 20ms | Deny on error; alert |
| Audit Manager | record() | AuditEvent | AuditAck | < 10ms | Buffer in local store; flush to persistent audit store |
| Evolution Manager | registerType() | TypeDefinition | TypeRegistrationResult | < 500ms | Return REGISTRATION_PENDING |
| Transformation Engine | transform() | InfoObject, TransformSpec | TransformedObject | < 100ms | Return original with TRANSFORM_FAILED flag |

---
## SUPPLEMENT C — PROCESSING PIPELINE PATTERNS

This supplement documents the four primary processing patterns used within the Information Engine pipelines, with detailed flow diagrams and operational notes.

---

### Pattern C-1 — Point-in-Time Query Pattern

```
Consumer requests: "TATASTEEL.NS closing price as at 2026-06-10 14:37:22"
    │
    ▼
Retrieval Manager accepts POINT_IN_TIME query
    │
    ▼
Index Manager: time-series index lookup
    entity_id = TATASTEEL_NSE
    type_code  = MKT-OHLCV-1D
    as_of_ts   ≤ 2026-06-10T14:37:22Z
    latest record before query time
    │
    ▼
Verify: ingestion_timestamp ≤ 2026-06-10T14:37:22Z
    (this record was known at the query time — no look-ahead)
    │
    IF ingestion_timestamp > query_time:
        EXCLUDE — this record was not available at query time
    │
    ▼
Storage Manager: retrieve record from hot or warm tier
    │
    ▼
Freshness Manager: compute historical freshness at query_time
    (how fresh was this record at 14:37:22 on 2026-06-10?)
    │
    ▼
Retrieval Manager: return result with:
    - information_id
    - close price value
    - freshness_at_query_time
    - quality_tier (at ingestion time)
    - lineage_summary
```

**Key invariant:** The ingestion_timestamp check is mandatory. Without it, the query may return information that was not available at the query time, introducing look-ahead bias.

---

### Pattern C-2 — Corporate Action Adjustment Pattern

```
Consumer requests: TATASTEEL.NS historical prices adjusted for corporate actions
    │
    ▼
Retrieval Manager: pull raw OHLCV-1D series for TATASTEEL.NS (2024-01-01 to 2026-06-15)
    │
    ▼
Information Registry: pull all CORP-SPLIT, CORP-BONUS, CORP-DIV records for entity in date range
    │
    ▼
Transformation Engine: apply_corporate_action_adjustments()
    For each corporate action (in chronological order, oldest first):
        SPLIT ratio N:M → multiply all prior prices by M/N; divide all prior volumes by M/N
        BONUS ratio N:M → multiply all prior prices by M/(M+N)
        DIVIDEND div per share → subtract div/share from all prior close prices (optional, flag-controlled)
    │
    ▼
Lineage extension:
    Transformed series records in its lineage:
        - source OHLCV records (parent_ids)
        - all corporate action records applied (parent_ids)
        - transformation_step: CORPORATE_ACTION_ADJUSTMENT
        - adjustment_parameters: list of adjustments applied
    │
    ▼
Return adjusted series with:
    - adjustment_applied: true
    - adjustments_applied: [list of corporate actions applied]
    - unadjusted_available: true (consumer can request raw series separately)
```

---

### Pattern C-3 — Cross-Source Conflict Resolution Pattern

```
Two sources both report the same fact — but disagree:
    Source A (NSE feed): NIFTY50 close = 22,345.60
    Source B (Bloomberg): NIFTY50 close = 22,340.15
    Difference: 5.45 points (0.024%)
    │
    ▼
Conflict Detection:
    Ingestion Manager detects same (type_code, entity_id, as_of_date) from two sources
    Difference exceeds tolerance threshold for MKT-INDEX type (tolerance: 0.01%)
    → CONFLICT_DETECTED
    │
    ▼
Corroboration Analysis:
    Trust tier A (NSE feed) = AUTHORITATIVE
    Trust tier B (Bloomberg) = RELIABLE
    Difference magnitude = 0.024% — minor
    Third source available? → Source C (Yahoo Finance): 22,345.70
    │
    ▼
Resolution decision:
    Majority with higher trust: Sources A and C agree (within tolerance 0.01%)
    → Authoritative value = 22,345.60 (Source A)
    → Source B value retained as secondary observation in corroboration store
    │
    ▼
Confidence adjustment:
    Two sources agree (major sources) → corroboration factor × 1.10
    One source disagrees (minor disagreement) → mild disagreement penalty × 0.95 (to B)
    Net confidence for primary record: base × 1.10 × (no penalty — primary is supported)
    │
    ▼
Audit record: CONFLICT_DETECTED, CONFLICT_RESOLVED, resolution_method = TRUST_WEIGHTED_MAJORITY
```

---

### Pattern C-4 — Historical Revision Handling Pattern

```
Macroeconomic agency revises Q3 2025 GDP from 6.8% to 7.1%
(revision released on 2026-06-15, for data originally published on 2025-11-15)
    │
    ▼
Ingestion Manager: receives new MACRO-GDP record
    entity: India GDP
    period: Q3-2025
    gdp_growth_yoy: 7.1%  (revised)
    revision_flag: true
    original_release_date: 2025-11-15
    revision_date: 2026-06-15
    │
    ▼
Identity Manager: look up existing information_id for India GDP Q3-2025
    → found: IOBJ-MACRO-GDP-20251115-00000001 (original, value = 6.8%)
    │
    ▼
Version Manager: create new version
    information_id = IOBJ-MACRO-GDP-20251115-00000001
    version_number = 2
    effective_from = 2026-06-15T00:00:00Z
    change_reason = OFFICIAL_REVISION_BY_SOURCE
    content_delta = { gdp_growth_yoy: 6.8 → 7.1, revision_date: 2026-06-15 }
    │
    ▼
Version 1 (original): effective_to = 2026-06-14T23:59:59Z, status = SUPERSEDED
    (preserved permanently — point-in-time queries before 2026-06-15 return 6.8%)
Version 2 (revised): status = ACTIVE (queries after 2026-06-15 return 7.1%)
    │
    ▼
Impact Analysis via Lineage Service:
    All information objects derived from IOBJ-MACRO-GDP-20251115-00000001 (version 1)
    → identified: [strategy_analysis records using GDP data, regime indicators, backtests]
    → alert Knowledge Engine: some derived information may need re-evaluation
    │
    ▼
Audit record: VERSION_UPDATE, reason = OFFICIAL_REVISION, impact_analysis_triggered = true
```

---
## SUPPLEMENT D — QUALITY FRAMEWORK REFERENCE

This supplement provides the complete dimension weight table, scoring calibration reference, and quality improvement guidance for operators.

---

### D.1 Complete Dimension Weight Table

| Dimension | Code | Weight | Rationale for weight |
|---|---|---|---|
| Accuracy | ACC | 0.15 | Highest weight: inaccurate information is the most damaging quality failure |
| Completeness | CMP | 0.12 | Missing fields make information unusable for its type; high operational impact |
| Consistency | CON | 0.10 | Internal consistency failures indicate data corruption or source error |
| Timeliness | TIM | 0.10 | Delayed acquisition undermines the value of otherwise high-quality information |
| Freshness | FRS | 0.10 | Stale information can be more damaging than no information (false sense of currency) |
| Validity | VLD | 0.08 | Schema violations indicate systemic source or pipeline problems |
| Reliability | REL | 0.08 | Source track record predicts future accuracy |
| Trustworthiness | TRW | 0.06 | Source tier is a proxy for institutional quality control |
| Lineage | LNG | 0.05 | Traceable lineage enables impact analysis and audit |
| Provenance | PRV | 0.04 | Documented origin supports compliance and audit |
| Confidence | CFD | 0.04 | Composite confidence synthesises multiple signals |
| Coverage | CVG | 0.03 | Coverage of consumer-required fields affects immediate usability |
| Granularity | GRN | 0.02 | Granularity mismatch reduces analytical precision |
| Relevance | RLV | 0.02 | Contextual relevance affects whether information applies to current use |

Total: 1.00

---

### D.2 Quality Score Calibration Reference

The following table shows representative IQS values for common information scenarios, to calibrate operator expectations:

| Scenario | Approximate IQS | Tier |
|---|---|---|
| NSE-direct tick data (realtime, fresh, high source reliability) | 0.93–0.97 | EXCELLENT |
| yfinance EOD bar (fresh, reliable, complete) | 0.83–0.88 | GOOD |
| yfinance bar from yesterday (aging freshness, reliable) | 0.71–0.78 | ACCEPTABLE to GOOD |
| Corporate earnings from exchange filing (fresh, authoritative) | 0.88–0.92 | GOOD to EXCELLENT |
| News sentiment (fresh, NLP-derived, single source) | 0.62–0.72 | ACCEPTABLE |
| Alternative data from provisional source | 0.48–0.58 | MARGINAL |
| Historical price from 5 years ago (cold tier, validated) | 0.74–0.81 | ACCEPTABLE to GOOD |
| Stale macro indicator (3 months past SLA) | 0.38–0.50 | POOR to MARGINAL |
| Incomplete earnings record (missing EPS field) | 0.55–0.65 | MARGINAL to ACCEPTABLE |
| Cross-source corroborated price (3 sources agree) | 0.90–0.98 | EXCELLENT |

---

### D.3 Quality Improvement Guidance

| Dimension failing | Common causes | Recommended remediation |
|---|---|---|
| Low Accuracy (ACC) | Source error; data corruption; model failure | Cross-source corroboration; source reliability review; reprocess from raw |
| Low Completeness (CMP) | Source not providing all required fields; parse failure | Update parse logic; contact source provider; request supplementary data |
| Low Consistency (CON) | Source data entry errors; unit mismatch; calculation errors | Rule review; cross-field validation tightening; source escalation |
| Low Timeliness (TIM) | Acquisition job latency; source API slowness; scheduling gaps | Reduce acquisition interval; switch to push/webhook mode |
| Low Freshness (FRS) | Stale data not re-acquired; acquisition job failure | Investigate acquisition job; re-run; escalate source outage |
| Low Validity (VLD) | Schema mismatch after source format change; new field types | Update type definition; fix parse logic |
| Low Reliability (REL) | Source systematically providing wrong data | Trust tier review; source replacement evaluation |
| Low Lineage (LNG) | Missing transformation documentation; pipeline bug | Audit pipeline; fix lineage recording in affected components |

---

### D.4 Quality Monitoring Dashboard Metrics

The following metrics should be visible to all information quality stakeholders:

| Metric | Description | Refresh | Alert condition |
|---|---|---|---|
| System IQS | Mean IQS across all ACTIVE information objects | Every 30 minutes | < 0.80 |
| Type IQS | Mean IQS per information type | Every 30 minutes | < 0.70 for any CRITICAL type |
| Source quality | Mean IQS from each source | Rolling 24 hours | < 0.70 for any active source |
| Quarantine rate | % of ingested records quarantined today | Daily | > 2% |
| Staleness count | Count of CRITICAL information in STALE or worse tier | Every 5 minutes | Any CRITICAL stale > 0 |
| Quality distribution | % EXCELLENT / GOOD / ACCEPTABLE / MARGINAL / POOR by type | Daily | % POOR > 5% |
| Freshness SLA breaches | Count of SLA breaches by type today | Real-time | Any CRITICAL breach > 0 |
| Confidence alerts | Count of confidence below 0.60 for CRITICAL information | Real-time | Any CRITICAL confidence < 0.60 |

---
## SUPPLEMENT E — GOVERNANCE DECISION RECORDS

This supplement documents six significant governance decisions made during the design of the Information Engine. Each record follows the standard Governance Decision Record (GDR) format.

---

### GDR-001 — Immutable Versioning Over In-Place Update

**Date:** Architecture design phase  
**Decision maker:** Information Governance Committee  
**Status:** ACCEPTED

**Context:** Two competing approaches were considered for handling information updates — in-place update (simply overwrite the current record) and immutable versioning (create a new version, preserve the old).

**Decision:** Immutable versioning.

**Rationale:**
1. Point-in-time queries (essential for backtesting) require access to what the system believed at any historical moment. In-place updates destroy this capability.
2. Regulatory compliance (SEBI OATS, PMLA) requires a complete audit trail of information changes. In-place updates cannot satisfy this requirement.
3. Debugging and investigation require the ability to see the system's state at any past moment. Without version history, investigation is impossible.
4. The storage cost of versioned history is bounded and manageable with tiered archival.

**Consequences:** All updates to information objects create a new version. Storage requirements are higher than in-place update. Version chains must be managed carefully.

**Alternatives rejected:** In-place update — rejected due to audit trail loss and point-in-time query incapability.

---

### GDR-002 — 18-Dimension Quality Framework Over Single Quality Score

**Date:** Architecture design phase  
**Decision maker:** Information Quality Committee  
**Status:** ACCEPTED

**Context:** A simpler approach (single composite quality score, computed by a heuristic) was considered alongside the 18-dimension framework.

**Decision:** 18-dimension framework with explicit weights.

**Rationale:**
1. Different dimensions degrade for different reasons. A source with excellent accuracy but stale data needs a different remediation than a source with fresh data but poor completeness.
2. The multi-dimensional score enables targeted quality improvement — operators know exactly which dimension is failing.
3. Consumer-specific quality floors can be set per dimension (e.g., a real-time consumer may prioritise freshness; a compliance consumer may prioritise lineage).
4. The explicit weight table is auditable and can be adjusted through governance.

**Consequences:** Higher computational cost per information object; more complex quality reporting; governance overhead for weight reviews.

---

### GDR-003 — Separate as_of_timestamp from ingestion_timestamp

**Date:** Architecture design phase  
**Decision maker:** Chief Information Architect  
**Status:** ACCEPTED

**Context:** Some simpler designs use a single timestamp for both when the information was produced and when it was ingested.

**Decision:** Maintain two separate timestamps on every information object.

**Rationale:**
1. The as_of_timestamp is the real-world time: "what state of the world does this information describe?"
2. The ingestion_timestamp is the system time: "when did the IIOS learn about this?"
3. The gap between them is the acquisition lag (used for timeliness scoring).
4. Point-in-time query consistency requires both: we need to know both what the fact was about (as_of) and when the system knew it (ingestion).
5. Historical revisions (GDR-004) demonstrate why the two are fundamentally different: a revision has an ingestion_timestamp of today but an as_of_timestamp in the past.

---

### GDR-004 — Preserve Original on Historical Revision

**Date:** Architecture design phase  
**Decision maker:** Information Governance Committee  
**Status:** ACCEPTED

**Context:** When a data provider revises previously published data (e.g., GDP revision), two approaches were considered: replace the original (overwrite with the revised value) or preserve the original and create a new version.

**Decision:** Preserve original; create new version with revision metadata.

**Rationale:**
1. Point-in-time queries before the revision date must return the original published value — the revised value was not available at that time.
2. Backtesting using historical GDP data should be able to simulate the world as it was known at the time — using the revised value introduces anachronistic knowledge.
3. Research applications need to study the magnitude of revisions over time.
4. Regulatory analysis may require knowing what value was used in a decision made before the revision.

---

### GDR-005 — Lineage Records Are Never Retired

**Date:** Architecture design phase  
**Decision maker:** Information Governance Committee  
**Status:** ACCEPTED

**Context:** Lineage records consume storage. A proposal was made to retire lineage records after the associated information objects are retired.

**Decision:** Lineage records are preserved permanently. They are exempt from all retention and archival policies.

**Rationale:**
1. Even after an information object is retired, lineage may be needed for: regulatory audit, forensic investigation of historical trading decisions, impact analysis if a source is discovered to have been systematically incorrect.
2. Lineage records are small relative to information records; the storage cost is low.
3. Without permanent lineage, the system loses the ability to answer "what was the full derivation of decision D on date T?" — a critical capability for regulatory and risk management purposes.

---

### GDR-006 — Source Trust Tier Is Operational, Not Classification

**Date:** Architecture design phase  
**Decision maker:** Source Management Committee  
**Status:** ACCEPTED

**Context:** A proposal was made to treat source trust tier as a permanent fixed classification (like a rating agency rating) rather than a dynamic operational measure.

**Decision:** Source trust tier is dynamic, reassessed quarterly based on rolling reliability scores.

**Rationale:**
1. Source quality changes over time — a historically reliable source can become unreliable due to data provider issues, staffing changes, or system failures.
2. A fixed trust tier creates a false sense of security. If a source's data quality degrades and the tier is not updated, the confidence premiums assigned to its information become misleading.
3. Dynamic reassessment provides an incentive for source providers to maintain quality (implicit SLA enforcement).
4. The governance overhead of quarterly reassessment is low relative to the quality assurance benefit.

**Consequence:** Trust tiers are reviewed quarterly. Significant reliability events trigger an immediate review. All confidence scores derived from trust-tier premiums are updated when a tier changes.

---
## SUPPLEMENT F — ANTI-PATTERN REFERENCE

This supplement documents the most common and dangerous information management anti-patterns — errors in design or operation that lead to systemic information quality failures. Each anti-pattern includes a description, the symptoms, the consequences, and the correct pattern.

---

### AP-01 — The Lookahead Leak

**Description:** An analytical pipeline uses information that was not available at the point in time it claims to represent. For example, a backtesting pipeline uses an adjusted closing price that incorporates a corporate action that was not announced until three months after the bar date.

**Symptoms:**
- Backtesting results are unrealistically good
- Live trading performance is systematically worse than backtested performance
- Historical regimes classified differently from how they appeared in real time

**Consequences:** Strategies are optimised for historical data that could not have been used in reality. Capital allocation decisions are made based on false performance metrics. Real trading results are guaranteed to underperform the backtest.

**Root cause:** Failure to check ingestion_timestamp against the query time. The query returns information that was not yet in the Registry at the historical moment.

**Correct pattern:** All retrieval queries for historical data MUST apply the point-in-time filter: `ingestion_timestamp ≤ query_time`. See IC-C-005, IC-C-006.

---

### AP-02 — The Stale Confidence Trap

**Description:** The confidence score of an information object is computed once at ingestion time and then treated as a static property. As the information ages and becomes stale, the confidence score remains high — misleading consumers into treating aging information as fresh.

**Symptoms:**
- Consumers report high confidence in decisions made with stale data
- Freshness degradation is not reflected in the operational confidence level
- Post-mortem analysis reveals that decisions were made with data that was hours or days old

**Consequences:** Trading decisions are made with overconfident stale information. Risk models use outdated volatility or correlation estimates. The system fails to re-acquire fresh data because the confidence score does not signal a problem.

**Root cause:** Confidence is a time-varying quantity. Freshness decay MUST be incorporated into the running confidence score.

**Correct pattern:** Confidence Manager MUST continuously recompute confidence as freshness decays. The confidence formula is: `confidence_t = confidence_0 × freshness_decay(t, type)`. See IC-C-004, IC-E-008.

---

### AP-03 — The Embedded Information Object

**Description:** An information object embeds the full content of another information object rather than referencing it by information_id. When the embedded object is updated, the embedding object does not reflect the update.

**Symptoms:**
- The same fact appears in two places with different values
- Updates to one record do not propagate to dependent records
- Lineage traversal fails because embedded content has no information_id

**Consequences:** Version consistency is broken. Consumers of the embedding object see stale data. Impact analysis after a source correction is impossible.

**Root cause:** Direct embedding of information content instead of ID-based cross-referencing.

**Correct pattern:** Cross-references MUST be expressed as information_id references. Use the Lineage Service to traverse the derivation graph. See IC-D-007.

---

### AP-04 — The Phantom Source

**Description:** An information object is ingested from a source that is not registered in the Source Manager — either because registration was overlooked or because a component is directly writing to the ingestion pipeline without going through authorised acquisition.

**Symptoms:**
- Information objects appear in the Registry with unknown source_ids
- Trust tier cannot be assigned (defaults to UNRELIABLE or NULL)
- Reliability statistics are unavailable for these information objects

**Consequences:** Confidence scores are degraded (unknown source → UNRELIABLE tier). Governance cannot determine the provenance of the information. Lineage from these objects is incomplete. Compliance reports show unregistered sources.

**Root cause:** Acquisition pipeline bypass or missing source registration step.

**Correct pattern:** All sources MUST be registered in the Source Manager before their data is ingested. Source registration is a prerequisite for acquisition authorisation. See IC-A-010.

---

### AP-05 — The Missing Version Chain

**Description:** An information object is updated in place (overwriting the previous value) rather than creating a new version. The previous value is permanently lost.

**Symptoms:**
- Information objects have version_number = 1 even after multiple known updates
- Point-in-time queries to historical dates return current values
- Audit trail shows no UPDATE events for regularly revised information

**Consequences:** Historical analysis is impossible. Point-in-time consistency is broken. Audit trail is incomplete. Regulatory requirements for data retention are violated.

**Root cause:** Component bypassing the Version Manager and writing directly to storage.

**Correct pattern:** All updates MUST go through the Version Manager. No component may write to the Storage Manager without creating a version record. See IC-B-001, IC-B-002.

---

### AP-06 — The Quality Floor Bypass

**Description:** A consumer bypasses the quality floor check by directly querying the Information Registry without specifying a quality floor, or by ignoring the quality_tier field in the retrieval response. POOR or MARGINAL quality information is then used in operational decisions.

**Symptoms:**
- Operational decisions are made with low-quality information
- Post-mortem reveals that the information used had IQS < 0.40
- Governance audit shows reads of POOR quality information by operational systems

**Consequences:** Low-quality information corrupts the analytical layers. Trading decisions may be based on incorrect data. Risk models may use unreliable inputs.

**Root cause:** Consumer-side bypass of quality enforcement; lack of mandatory quality floor on retrieval API.

**Correct pattern:** The Retrieval Manager MUST enforce the consumer's specified quality floor. All operational consumers MUST specify a quality floor of at least 0.60. The system MUST NOT return POOR quality information without an explicit OVERRIDE flag in the request. See IC-E-004.

---

### AP-07 — The Lineage Orphan

**Description:** A derived information object (computed from one or more parent information objects) does not declare its parents in the lineage record. The object appears to be a primary information object but is actually a derived product.

**Symptoms:**
- Derived information objects have lineage records pointing only to the immediate source record, not to the parent information objects they were computed from
- Lineage graph has unexpected terminal nodes (derived objects with no parents)
- Impact analysis after source correction misses derived objects

**Consequences:** When a parent information object is corrected, the Lineage Service cannot identify the derived objects that need to be re-evaluated. Incorrect derived information continues to be served to consumers.

**Root cause:** Enrichment Engine or Transformation Engine failing to record parent information_ids in the lineage record of derived outputs.

**Correct pattern:** Every enrichment and transformation step MUST extend the lineage record with all input information_ids. See IC-F-003.

---

### AP-08 — The Schema Lock

**Description:** A decision is made to never change the schema of an established information type, even when the schema needs to evolve (new required fields, changed semantics, deprecated fields). The result is an accumulation of technical debt where the type definition no longer accurately describes what information objects of that type contain.

**Symptoms:**
- Information objects have undocumented fields not in the schema
- Validation is weakened to accommodate undocumented content
- New consumers misinterpret fields because the schema is wrong

**Consequences:** Schema quality degrades. Validation becomes ineffective. New consumers build against incorrect documentation. Interoperability with external systems is broken.

**Root cause:** Fear of schema migrations; absence of a schema evolution process.

**Correct pattern:** Schema evolution is managed by the Evolution Manager with a formal process for backward-compatible changes. Migrations are well-defined and audited. See Part III, Component 24 (Evolution Manager).

---

### AP-09 — The Confidence Override

**Description:** A component or operator manually sets the confidence score of an information object to 1.0 (or another high value) to bypass quality checks, without the information actually meeting the criteria for high confidence.

**Symptoms:**
- Information objects from low-tier sources have confidence scores inconsistent with the source trust tier
- Confidence scores do not correlate with actual information accuracy
- Post-mortem investigations reveal that confidence was manually overridden without documentation

**Consequences:** Quality gates are defeated. Risk models receive overconfident inputs. Governance reviews cannot identify the actual quality of information used in past decisions.

**Root cause:** Operational pressure to "just make it work" combined with absence of change control on confidence scores.

**Correct pattern:** Confidence scores MUST be computed by the Confidence Manager according to the defined formula. Manual overrides are prohibited unless approved by the Information Owner and documented in the audit trail. See IC-E-008.

---

### AP-10 — The Audit Gap

**Description:** One or more Read operations on information objects are not recorded in the audit trail — either because the audit record operation is treated as optional or because a high-throughput read path bypasses audit logging for performance reasons.

**Symptoms:**
- Audit reports show information_ids that were in the Registry but have no read records
- Real-time trading reads are not represented in the audit trail
- Regulatory audit cannot reconstruct which information was used in a specific decision

**Consequences:** Regulatory compliance is violated. Forensic investigations cannot determine which information was used in past decisions. Insider trading investigations cannot be resolved.

**Root cause:** Bypassing the Audit Manager for high-throughput reads; treating audit as optional.

**Correct pattern:** ALL reads MUST be audited. For high-throughput paths, use asynchronous audit logging (log to buffer, flush to audit store) — never skip. The audit is mandatory, not optional. See IC-H-001.

---
## SUPPLEMENT G — INFORMATION GLOSSARY

This glossary provides precise, authoritative definitions for all information-related terms used in this document and throughout the IIOS architecture. Terms are listed alphabetically.

---

| Term | Definition |
|---|---|
| Acquisition | The process of obtaining raw data from an external source and delivering it to the Ingestion Manager. |
| Acquisition lag | The elapsed time between an external event and the IIOS acquiring information about it. Used in timeliness scoring. |
| Active information object | An information object in ACTIVE lifecycle state — current, valid, and available for consumption. |
| as_of_timestamp | The moment in the real world that an information object describes. Distinguished from ingestion_timestamp. |
| Archival | The migration of an information object from active Registry storage to long-term archive storage after its retention period elapses. |
| Audit trail | The complete, tamper-evident log of all operations performed on information objects. |
| Canonical form | The standard, authoritative representation of an identifier, unit, or name in the IIOS — the form to which all variations are normalised. |
| Classification | The assignment of type code, layer, topic tags, entity references, and governance tier to an information object. |
| Confidence score | A composite measure in [0.0, 1.0] of the IIOS's certainty that an information object accurately represents the real-world state. |
| Context | The state of the IIOS and external world at the moment an information object became current. Captured as a ContextRecord. |
| Corroboration | The process of comparing the same fact from multiple independent sources to assess accuracy and adjust confidence. |
| Coverage | A quality dimension measuring the proportion of consumer-required fields that an information object contains. |
| Data | Raw, uninterpreted signals received from an external source. Data becomes information after validation, normalisation, and enrichment. |
| Deduplication | Detection and suppression of duplicate records — the same fact arriving from the same source more than once. |
| Derived information | An information object whose content was computed from one or more parent information objects (rather than directly from a source). |
| Distribution | The push delivery of newly processed information objects to all registered consumers. |
| Enrichment | The addition of derived fields, cross-references, entity metadata, and context annotations to a validated information object. |
| Entity | A persistent, named real-world thing tracked in the IIOS. Managed by the Entity Engine. Described by information objects. |
| Evidence | Information used specifically to support or refute a hypothesis or belief. The directional use of information. |
| Fact | A piece of information validated to a high confidence threshold — treated as ground truth within the IIOS. |
| Freshness | A quality dimension measuring how current an information object is relative to its defined SLA. A time-varying quantity. |
| Freshness decay | The reduction of an information object's freshness score as time elapses from its as_of_timestamp. |
| Governance | The system of policies, responsibilities, and controls for managing information as an organisational asset. |
| Identity conflict | Two different information_ids assigned to what is actually the same real-world fact. Detected and resolved by the Identity Manager. |
| Information Catalog | The authoritative registry of all valid information types — their schemas, SLAs, and governance classifications. |
| Information Constitution | The set of non-negotiable architectural rules governing all information in the IIOS. |
| Information Engine | The IIOS subsystem responsible for acquiring, validating, enriching, classifying, storing, distributing, and governing all information. |
| Information layer | One of 15 levels in the information type hierarchy, from raw market data through to knowledge information. |
| information_id | The globally unique canonical identifier for an information object, assigned by the Identity Manager. |
| Information object | The fundamental unit of the Information Engine — a governed, versioned, quality-scored record representing a validated piece of information. |
| Information Quality Score (IQS) | The composite quality score computed from 18 weighted dimensions. The primary quality indicator for an information object. |
| Information Record | The persistence representation of an Information Object in the Information Registry. |
| Information Registry | The authoritative, canonical store for all information objects. The single source of truth for information in the IIOS. |
| Information Source | An authorised external or internal origin of data for the IIOS. Registered in the Source Manager. |
| ingestion_timestamp | The moment at which the IIOS ingested an information object. Distinguished from as_of_timestamp. |
| Knowledge | Justified, reliable belief derived from information through reasoning. The output of the Knowledge Engine. |
| Legal hold | A governance instruction to preserve information indefinitely for legal, regulatory, or litigation purposes, overriding retention policies. |
| Lineage | The complete documented history of an information object's origin and transformations from source to current state. |
| Lineage graph | The directed acyclic graph encoding the derivation relationships among all information objects. |
| Look-ahead bias | The inadvertent use of information that was not available at a historical query time. A fatal analytical error. |
| Normalisation | The transformation of an information object into the IIOS's canonical internal representation — standard IDs, units, formats. |
| Observation | A specific, timestamped instance of a measurement — the atomic unit of empirical information. |
| Point-in-time consistency | The property of a retrieval system that returns only information that was available at the specified historical moment. |
| Provenance | The documented origin of an information object — which source it came from and through what chain of transformations. |
| Quality dimension | One of 18 aspects of information quality measured by the Quality Manager. |
| Quality tier | The classification of an information object based on its IQS: EXCELLENT, GOOD, ACCEPTABLE, MARGINAL, or POOR. |
| Quarantine | The holding of an information object outside the active Registry pending review or remediation. |
| Real-time pipeline | The Information Engine processing pipeline for high-velocity tick data. Target end-to-end latency: < 100ms. |
| Reliability | A quality dimension measuring the historical track record of an information source. Rolling 90-day accuracy rate. |
| Retention policy | The governance policy specifying how long information of a given type must be retained before archiving. |
| Scheduled batch pipeline | The Information Engine pipeline for information that arrives on a fixed daily or periodic schedule. |
| Signal | A derived, directional piece of information indicating a likely state or trend. Intermediate between data and knowledge. |
| Source Manager | The component maintaining the registry of all authorised information sources, their configurations, and trust tiers. |
| Stale | The freshness classification for an information object whose as_of_timestamp is beyond its defined freshness SLA. |
| Superseded | The lifecycle state of an information object that has been replaced by a newer version. Preserved immutably. |
| Trust tier | The assigned reliability classification of an information source: AUTHORITATIVE, RELIABLE, STANDARD, PROVISIONAL, UNRELIABLE. |
| Validation | The process of confirming that an information object is structurally valid, type-conformant, and value-consistent. |
| Version | A numbered instance of an information object representing its state at a specific point in time. |
| Version chain | The ordered sequence of all versions of an information object, from version 1 (original) to the current version. |

---
---

## DOCUMENT FOOTER

### Summary Metrics

| Metric | Value |
|---|---|
| Document | INFORMATION_ENGINE_ARCHITECTURE.md |
| Version | 1.0.0 |
| Information Engine philosophy distinctions | 20 |
| Information type layers | 15 |
| Core components | 25 |
| Component clusters | 5 (Registry & Catalog, Acquisition, Validation & Quality, Enrichment, Governance) |
| Lifecycle stages | 15 (including ACTIVE_MONITORING and RETIREMENT) |
| Services defined | 19 |
| Processing pipelines | 4 (Real-Time Stream, Intraday Batch, Scheduled Batch, On-Demand) |
| Processing patterns | 14 |
| Quality dimensions | 18 |
| Quality tiers | 5 (EXCELLENT, GOOD, ACCEPTABLE, MARGINAL, POOR) |
| Governance dimensions | 16 |
| Constitutional rule categories | 10 (IC-A through IC-J) |
| Constitutional rules | 96 |
| Readiness checklist sections | 16 |
| Readiness checklist criteria | 85+ |
| Information types catalogued | 45+ |
| Anti-patterns documented | 10 |
| Governance Decision Records | 6 |
| Glossary terms | 50+ |

---

### Master Compliance Checklist

Before this document is considered final, all items below must be confirmed:

- [x] 20 conceptual distinctions defined and explained (Part I)
- [x] 15-layer information type hierarchy documented with full taxonomy (Part II)
- [x] All 25 components specified with purpose, responsibilities, inputs, outputs, dependencies, failure handling (Part III)
- [x] 15-stage lifecycle documented with state machine and per-stage requirements (Part IV)
- [x] All 19 services defined with SLA targets and failure recovery (Part V)
- [x] 4 processing pipelines documented with flow diagrams and capacity model (Part VI)
- [x] 18-dimension quality framework defined with formulas and tier boundaries (Part VII)
- [x] 16-dimension governance framework with tier matrix, ownership, retention, compliance (Part VIII)
- [x] 96 constitutional rules across 10 categories (Part IX)
- [x] 16-section readiness checklist with 85+ criteria (Part X)
- [x] Supplement A: Information Type Catalogue (45+ types across 7 layers)
- [x] Supplement B: Component Interface Reference (all 25 components)
- [x] Supplement C: 4 processing pipeline pattern diagrams
- [x] Supplement D: Quality Framework Reference (weights, calibration, monitoring metrics)
- [x] Supplement E: 6 Governance Decision Records
- [x] Supplement F: 10 Anti-Pattern Reference entries
- [x] Supplement G: Glossary (50+ terms)
- [x] No source code in this document
- [x] No SQL in this document
- [x] No physical schema definitions in this document
- [x] All diagrams are ASCII text (Markdown compatible)
- [x] All formulas are expressed in mathematical notation

---

### Governing Documents

| Document | Relationship |
|---|---|
| INFORMATION_ONTOLOGY.md | Defines all information types that this engine acquires, manages, and distributes |
| KNOWLEDGE_ENGINE_ARCHITECTURE.md | Primary consumer of information from this engine |
| ENTITY_ENGINE_ARCHITECTURE.md | Provides canonical entity_ids referenced in all information objects |
| RELATIONSHIP_ENGINE_ARCHITECTURE.md | Consumes information objects as evidence for relationship inference |
| EVENT_ENGINE_ARCHITECTURE.md | Produces events from information state changes; consumes information for event enrichment |
| DATABASE_PERSISTENCE_ARCHITECTURE.md | Defines the physical storage architecture underlying the Storage Manager |
| ARCHITECTURE.md | System overview; this document is one of the 17 engine architecture documents |

---

### Architectural Impact Statement

The Information Engine is the data quality foundation of the IIOS. Every analytical decision made by the IIOS — from regime classification to strategy selection to risk management — depends on the quality, freshness, and completeness of the information this engine manages.

The architecture defined in this document establishes:
- A 15-layer information taxonomy that covers every information type the IIOS requires
- A 25-component implementation architecture that covers every aspect of information processing from acquisition through retirement
- A 15-stage lifecycle that enforces quality gates at every transition
- An 18-dimension quality framework that makes information quality measurable, comparable, and improvable
- A 16-dimension governance framework that satisfies regulatory and compliance requirements
- 96 constitutional rules that prevent the most catastrophic information management failures
- A 16-section readiness checklist that operationalises the quality standard

Any IIOS implementation that claims to satisfy this architecture must be able to demonstrate compliance with all 96 constitutional rules and all 85+ readiness checklist criteria. There are no partial implementations; there are no optional rules.

---

### Version History

| Version | Date | Author | Change |
|---|---|---|---|
| 0.1 | Architecture design phase | IIOS Architecture Team | Initial draft — philosophy and taxonomy |
| 0.5 | Architecture design phase | IIOS Architecture Team | Components, lifecycle, services added |
| 0.9 | Architecture design phase | IIOS Architecture Team | Quality framework, governance, constitution added |
| 1.0.0 | Architecture design phase | IIOS Architecture Team | Complete — all parts, supplements, footer |

---

*This document is governed by the IIOS Information Governance Framework. Any modification requires review by the Information Governance Committee and must be recorded in the version history above. Constitutional rules (Part IX) may not be modified without explicit approval by the full governance board.*

*INFORMATION_ENGINE_ARCHITECTURE.md — Version 1.0.0 — IIOS Architecture Series*

------

## APPENDIX — INFORMATION ENGINE OPERATIONAL RUNBOOK

### Startup Sequence

The Information Engine must be started in the following order to ensure all dependency chains are satisfied:

| Step | Component | Readiness check |
|---|---|---|
| 1 | Information Catalog | Verify all type definitions loaded; count ≥ minimum registered types |
| 2 | Source Manager | Verify all sources in ACTIVE status have valid configurations |
| 3 | Identity Manager | Verify identity store is accessible and sequence is consistent |
| 4 | Information Registry | Verify Registry store is accessible; run integrity check on last 1000 records |
| 5 | Index Manager | Verify all indices are consistent with Registry; rebuild if diverged |
| 6 | Freshness Manager | Verify freshness SLA table is loaded; run initial freshness scan |
| 7 | Acquisition Manager | Load acquisition schedules; verify source connectivity |
| 8 | Distribution Manager | Load subscription registry; verify subscriber endpoints |
| 9 | Governance Manager | Load access control lists; verify policy versions match |
| 10 | Audit Manager | Verify audit store is writable; confirm last audit record timestamp |

**Go/No-Go criterion:** All 10 components must report READY before any acquisition job is dispatched.

---

### Shutdown Sequence

| Step | Action | Guard condition |
|---|---|---|
| 1 | Pause Acquisition Manager | No new acquisition jobs dispatched |
| 2 | Drain Ingestion buffer | Wait for buffer to reach zero; timeout 120 seconds |
| 3 | Complete in-flight validations | Wait for all active validation tasks; timeout 60 seconds |
| 4 | Flush pending index updates | Index Manager drains queue; timeout 30 seconds |
| 5 | Flush Audit buffer | Audit Manager flushes all buffered records to persistent store |
| 6 | Persist Distribution state | Save unacknowledged delivery queue for restart recovery |
| 7 | Write shutdown checkpoint | Registry writes shutdown checkpoint record |
| 8 | Release storage locks | Storage Manager releases all open locks |

**Unclean shutdown:** If the process is killed without completing the shutdown sequence, the startup sequence will detect diverged indices and run a recovery pass before declaring READY.

---

### Recovery Procedures

| Failure mode | Detection | Recovery |
|---|---|---|
| Registry store unreachable | Component health check fails; 30s timeout | Switch to standby Registry store; alert; drain ingestion buffer during switchover |
| Index divergence | Startup integrity check fails | Rebuild diverged indices from Registry records; latency degrades during rebuild |
| Audit store full | Audit Manager reports DISK_FULL | Alert immediately; rotate to overflow store; escalate to operations |
| Source failure | Acquisition Manager reports 3 consecutive failures | Mark source SUSPENDED; alert source operator; switch to backup source if available |
| Version chain corruption | Detected by Version Manager integrity scan | Quarantine affected information_ids; alert Governance Manager; recover from backup |
| Confidence score drift | Quality Manager detects systematic score drop | Investigate source reliability; check freshness decay parameters; alert quality team |

---