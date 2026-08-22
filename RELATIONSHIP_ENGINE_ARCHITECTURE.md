# RELATIONSHIP ENGINE ARCHITECTURE

**Document Series:** Investment Intelligence Operating System — Engineering Document Library
**Document Number:** 9 of 10
**Document Class:** Relationship Engineering Architecture
**Status:** Authoritative
**Version:** 1.0.0
**Date:** 2026-07-02
**Authors:** Human Principal / Engineering Foundation
**Governs:** Every relationship type, component, lifecycle, service, graph model, quality standard, and governance policy for all relationships in the IIOS

---

## Scope and Authority

This document is the authoritative engineering design for the Relationship Engine of the Investment Intelligence Operating System. The Relationship Engine is the component responsible for creating, maintaining, validating, evolving, querying, indexing, governing, and reasoning over every relationship that connects entities in the IIOS.

Relationships are the connective tissue of intelligence. A system that knows about Strategy entities and Trade entities but does not know that Strategy A *generated* Trade B — and that Trade B *contributed to* KnowledgeRecord C — cannot learn, cannot trace, and cannot reason intelligently. The Relationship Engine transforms a collection of isolated entities into a connected knowledge graph that enables multi-hop reasoning, influence propagation, causal analysis, and intelligent decision-making.

This document does **NOT** contain:
- Source code or implementation details
- Graph database schema definitions (no Cypher, no Gremlin, no SQL)
- ORM relationship definitions
- API endpoint specifications

This document **DOES** contain:
- The philosophical foundation of relationships as first-class citizens in the IIOS
- The complete 15-layer relationship hierarchy
- Design of all 17 relationship engine components with full specifications
- The complete 12-stage relationship lifecycle with diagrams
- All 15 relationship services with 6-attribute specifications
- The relationship graph architecture (node model, edge model, traversal, influence propagation)
- The 12-dimension relationship quality framework
- Relationship governance policies across 12 pillars
- 75 mandatory Relationship Constitution rules
- A comprehensive 12-section Relationship Readiness Checklist

---

## Parent Documents

| Document | Authority |
|---|---|
| `INVESTMENT_INTELLIGENCE_OPERATING_SYSTEM.md` | Supreme constitutional authority |
| `RELATIONSHIP_ONTOLOGY.md` | Relationship type definitions |
| `ENTITY_ONTOLOGY.md` | Entity type definitions |
| `MASTER_KNOWLEDGE_ARCHITECTURE.md` | Knowledge domain authority |
| `EVENT_ONTOLOGY.md` | Event type definitions |
| `INFORMATION_ONTOLOGY.md` | Information layer design |
| `KNOWLEDGE_ENGINE_ARCHITECTURE.md` | Knowledge Engine authority |
| `ENTITY_ENGINE_ARCHITECTURE.md` | Entity Engine authority |
| `CORE_FRAMEWORK_ARCHITECTURE.md` | Core framework authority |
| `ENGINEERING_STANDARDS.md` | Engineering standards authority |

---

## Relationship Engine Position in the IIOS

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    IIOS SYSTEM ARCHITECTURE                                 │
│                                                                             │
│  L17 ControlTower     L15-16 Research + Validation     L14 Analytics       │
│  L13 LearningSystem   L10-12 Decision + Execution      L1-9 Intelligence   │
│                                                                             │
│  Every layer QUERIES and WRITES relationships through the Relationship Eng  │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    RELATIONSHIP ENGINE (This Document)               │   │
│  │                                                                      │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────┐  ┌─────────────────┐ │   │
│  │  │ Registry │  │ Catalog  │  │   Factory    │  │   Validator     │ │   │
│  │  └──────────┘  └──────────┘  └──────────────┘  └─────────────────┘ │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────┐  ┌─────────────────┐ │   │
│  │  │ Lifecycle│  │Versioner │  │    Index     │  │     Cache       │ │   │
│  │  └──────────┘  └──────────┘  └──────────────┘  └─────────────────┘ │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────┐  ┌─────────────────┐ │   │
│  │  │ Reasoning│  │Discovery │  │  Evolution   │  │   Governance    │ │   │
│  │  └──────────┘  └──────────┘  └──────────────┘  └─────────────────┘ │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                              │                                              │
│  ┌───────────────────────────▼──────────────────────────────────────────┐   │
│  │         ENTITY ENGINE  (source and target of all relationships)      │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                              │                                              │
│  ┌───────────────────────────▼──────────────────────────────────────────┐   │
│  │   PERSISTENCE LAYER  (trading_brain.db / knowledge.db / audit.db)   │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Relationship Engine Data Flow

```
Event / Signal / Discovery
        │
        ▼
[Relationship Discovery Manager]
        │ candidate relationship detected
        ▼
[Relationship Validator]
        │ validation passes
        │── FAIL ──► Rejection log
        ▼
[Relationship Factory]
        │ creates relationship record
        ▼
[Relationship Registry]          [Relationship Index]
[Relationship Catalog lookup]    [Relationship Cache]
[Identity Manager]               [Audit Manager]
        │
        ▼
[Relationship Lifecycle Manager]
        │ ACTIVE state
        ▼
┌────────────────────────────────────┐
│   Relationship Graph (adjacency)   │
│   Source Entity ──edge──► Target   │
│   Entity                           │
└──────────────┬─────────────────────┘
               │
    ┌──────────┼───────────────┐
    ▼          ▼               ▼
[Traversal] [Reasoning]  [Influence
[Service]   [Manager]    Propagation]
               │
               ▼
     All 17 IIOS Layers (consumers)
```

---

## Relationship Graph Conceptual Model

```
ENTITY A                    RELATIONSHIP                     ENTITY B
────────    ═══════════════════════════════════════════    ────────
Strategy  ──GENERATES──────────────────────────────────► Hypothesis
Strategy  ──VALIDATED_BY───────────────────────────────► BacktestResult
Hypothesis──EVALUATED_BY───────────────────────────────► Agent (×62)
Hypothesis──PRODUCES────────────────────────────────────► DecisionRecord
DecisionRecord─TRIGGERS──────────────────────────────────► Order
Order     ──FILLS_AT──────────────────────────────────────► Fill
Fill      ──CONTRIBUTES_TO─────────────────────────────────► Trade
Trade     ──GENERATES_LEARNING──────────────────────────────► LearningRecord
LearningRecord─UPDATES──────────────────────────────────────► KnowledgeRecord
KnowledgeRecord─INFLUENCES──────────────────────────────────► Strategy

         Every arrow is a managed relationship in the Relationship Engine.
```

---

## Table of Contents

- [Part I — Relationship Engine Philosophy](#part-i)
- [Part II — Relationship Architecture](#part-ii)
- [Part III — Relationship Components](#part-iii)
- [Part IV — Relationship Lifecycle](#part-iv)
- [Part V — Relationship Services](#part-v)
- [Part VI — Relationship Graph Architecture](#part-vi)
- [Part VII — Relationship Quality Framework](#part-vii)
- [Part VIII — Relationship Governance](#part-viii)
- [Part IX — Relationship Constitution](#part-ix)
- [Part X — Relationship Readiness Checklist](#part-x)
- [Document Footer](#document-footer)
- [Supplement A — Relationship Type Catalogue](#supplement-a)
- [Supplement B — Component Interface Reference](#supplement-b)
- [Supplement C — Graph Traversal Patterns](#supplement-c)
- [Supplement D — Quality Scoring Reference](#supplement-d)
- [Supplement E — Governance Decision Records](#supplement-e)
- [Supplement F — Anti-Pattern Reference](#supplement-f)
- [Supplement G — Relationship Glossary](#supplement-g)

---
## PART I — RELATIONSHIP ENGINE PHILOSOPHY

### 1.1 Relationships as First-Class Citizens

In most information systems, relationships are afterthoughts — foreign keys in a relational table, pointers in an object graph, implicit connections inferred by proximity in a document. The IIOS takes a fundamentally different stance: **relationships are first-class citizens, equal in importance to entities, and managed by a dedicated engine with the same rigour as any entity.**

What does it mean for a relationship to be a first-class citizen?

It means that every relationship in the IIOS has:
- **Its own identity** — a permanent UUID4 assigned at creation
- **Its own lifecycle** — it is discovered, validated, created, activated, evolved, deprecated, and retired
- **Its own version history** — every change to a relationship is recorded as a new version
- **Its own quality score** — strength, confidence, reliability, and freshness are all computed and tracked
- **Its own audit trail** — every event in a relationship's life is permanently recorded
- **Its own metadata** — rich contextual information about when and why the relationship exists
- **Its own governance** — a defined owner, classification, and policy set

Without relationship-as-first-class-citizen, the following intelligence capabilities become impossible or severely degraded:

| Intelligence Capability | How Relationships Enable It |
|---|---|
| Causal attribution | "This loss was caused by this strategy, which was trained on this knowledge, which came from this data source" — traceable because every CAUSED_BY link is a managed relationship |
| Influence analysis | "This regime change will affect these strategies because they have SENSITIVE_TO relationships with this regime type" |
| Knowledge provenance | "This rule was derived from these trades, which were executed by these strategies, which were active in this regime" |
| Risk propagation | "This position's risk AFFECTS the portfolio, which CONSTRAINS all other allocations" |
| Learning attribution | "This agent's opinion CONTRIBUTED_TO this decision, which RESULTED_IN this trade, which GENERATED this loss — the agent's calibration should be updated" |

None of these capabilities are possible without managed relationships. The Relationship Engine is the intelligence infrastructure that elevates the IIOS from a trading system that executes orders to an intelligent system that understands why it makes the decisions it does.

---

### 1.2 Foundational Concept Distinctions

Understanding the precise meaning of each relationship concept is essential to understanding why the Relationship Engine is architecturally distinct from entity management.

---

**Entity vs Relationship:**

An entity is a named, uniquely identified, persistent domain object — the *noun* of the IIOS. A relationship is a named, uniquely identified, persistent connection between two entities — the *verb*. The entity "Strategy" exists independently. The entity "Trade" exists independently. But the intelligence claim that "Strategy GENERATED Trade" is a relationship — and that claim is as important to manage as either entity.

The critical architectural decision: relationships are not stored as attributes on entities (e.g., `trade.strategy_id`). They are managed as independent records with their own identity, lifecycle, and quality score. This enables:
- Multiple relationships of different types between the same two entities
- Temporal relationships that hold for a bounded time window
- Probabilistic relationships with confidence scores
- Relationship evolution (strengthening, weakening) over time

---

**Relationship vs Association:**

An association is a loose, informal connection between two entities — typically a shared attribute or contextual proximity. Associations are not necessarily managed as persistent records.

A relationship, in the IIOS, is a formally defined, managed, versioned connection of a specific named type between two specific entities. It has a defined direction (or is explicitly undirected), a strength, a confidence score, and a lifecycle.

The distinction matters because associations can be computed on demand (e.g., "all strategies active in the BULL regime are associated with each other"), whereas relationships are first-class facts that persist, evolve, and are reasoned over.

---

**Relationship vs Dependency:**

A dependency is a specific type of relationship that expresses a requirement: entity A requires entity B to function correctly. Dependencies are directional (A depends on B, not the other way around) and carry semantic weight beyond mere connection: if B is unavailable, A is affected.

Dependency relationships in the IIOS are treated with special significance:
- They are used to determine safe archival order (archive B only after A is archived or the dependency is removed)
- They are used to propagate health signals (if B is degraded, A's health may be degraded)
- They are used in risk analysis (circular dependencies are flagged as risks)

---

**Relationship vs Ownership:**

Ownership is a governance relationship — it expresses that one entity (the owner) has responsibility and authority over another entity. Ownership relationships are directional and exclusive (each entity has exactly one owner at any time).

In the IIOS, ownership is maintained by the Entity Engine's Governance Manager, but the Relationship Engine maintains the *OWNS* relationship type in the relationship graph. This allows the governance layer to use the Relationship Engine's traversal capabilities to answer questions like "what does the Entity Engine own?" or "what entities does the OrderManager own?"

---

**Relationship vs Influence:**

Influence is a probabilistic relationship that expresses that a change in one entity is likely to affect the state of another entity, with a quantified probability and direction of effect. Influence relationships are:
- Weighted (degree of influence: 0.0 to 1.0)
- Directional (A influences B does not imply B influences A)
- Temporal (the influence may only hold within certain time windows or regime conditions)
- Probabilistic (the influence holds with a defined confidence, not with certainty)

Influence relationships are the most analytically powerful relationship type in the IIOS. They power the Influence Service, which can answer: "If the VIX spikes above 35, which strategies will be most affected and by how much?"

---

**Relationship vs Correlation:**

Correlation is a statistical relationship between two measurable entities that expresses the degree to which their values move together. Correlation is:
- Symmetric (A correlates with B equally in both directions)
- Quantified (Pearson or Spearman coefficient: −1.0 to +1.0)
- Temporally bounded (correlation windows have specific lookback periods)
- Regime-conditional (correlation in BULL markets may differ from BEAR markets)

Correlation relationships are distinct from influence: correlation is descriptive (they move together), influence is causal (A causes changes in B). The IIOS maintains both types of relationships and uses them for different reasoning tasks.

---

**Relationship vs Causation:**

Causation is the strongest relationship type — it expresses that entity A is the direct cause of entity B or a change in entity B. Causal relationships are:
- Directional (A causes B; reverse causation is a different relationship)
- Temporally ordered (cause precedes effect)
- Evidenced (the causal claim is supported by evidence stored in the relationship record)
- Falsifiable (the causal claim can be updated when new evidence contradicts it)

Establishing causation is the hardest intelligence task in the IIOS. The Relationship Engine maintains causal hypotheses (HYPOTHETICALLY_CAUSED_BY) and causal facts (CAUSED_BY), where the latter requires sufficient evidence to cross the causal confidence threshold (default: 0.85).

---

**Relationship vs Composition:**

Composition is a structural relationship that expresses that entity A is physically composed of entity B — B is a component of A, and B cannot meaningfully exist without A. This is the "whole-part" relationship where the whole controls the lifecycle of the parts.

Example: A Portfolio entity is COMPOSED_OF Position entities. Positions do not have an independent lifecycle outside the portfolio — they are created when added to the portfolio and retire when removed.

Composition is the strongest structural relationship type. It establishes lifecycle dependency: when the aggregate root (Portfolio) is archived, all its constituent Position entities are archived with it.

---

**Relationship vs Aggregation:**

Aggregation is a weaker form of composition — entity A AGGREGATES entity B, meaning B is a component of A, but B can exist independently of A. When A is archived, B is not necessarily archived with it.

Example: A Sector entity AGGREGATES Symbol entities. The BANKING sector aggregates HDFC, ICICI, KOTAK, etc. But if the BANKING sector entity is removed or restructured, the Symbol entities remain — they simply lose this association.

---

**Relationship Instance vs Relationship Type:**

A relationship type is the definition of a kind of connection: `GENERATES`, `CAUSES`, `COMPOSED_OF`, `INFLUENCES`. A relationship type is defined in the Relationship Catalog with its allowed source entity types, allowed target entity types, directionality, and quality dimensions.

A relationship instance is a specific connection between two specific entities of the correct types. The instance "Strategy:MomentumBreakoutV3 GENERATES Hypothesis:HYP-20260702-0001" is a relationship instance. Every instance has its own `relationship_id` (UUID4), its own lifecycle, its own confidence score, and its own version history.

---

**Relationship Strength:**

Relationship strength is the quantified degree to which the relationship is meaningful or significant. It answers: "How strongly are these two entities connected?"

Strength is entity-type-specific in how it is computed:
- For CORRELATION relationships: the absolute value of the Pearson coefficient
- For INFLUENCES relationships: a composite of effect size, directionality, and evidence count
- For GENERATED_BY relationships: 1.0 (binary — either a strategy generated a hypothesis or it did not)
- For SIMILAR_TO relationships: a cosine similarity or other distance metric

Strength ranges from 0.0 (no meaningful connection) to 1.0 (perfectly strong connection).

---

**Relationship Confidence:**

Relationship confidence is the system's degree of certainty that the relationship claim is true. It answers: "How sure are we that this relationship actually exists?"

Confidence is separate from strength: a relationship can be strong (high degree of influence) but low-confidence (not enough evidence to be sure). Conversely, a weak relationship can be high-confidence (we are very sure this small influence exists).

Confidence is maintained as a running estimate that updates as new evidence accumulates. When confidence drops below a threshold (default: 0.30), the relationship is automatically flagged for deprecation review.

---

### 1.3 Design Principles of the Relationship Engine

| Principle | Description |
|---|---|
| **First-class identity** | Every relationship has its own UUID4 — it is not a derived key or a table row |
| **Explicit over implicit** | Relationships are explicitly created and managed; implicit foreign keys are not relationships |
| **Direction by design** | Every relationship has an explicit direction unless explicitly declared undirected |
| **Confidence is mandatory** | Every relationship carries a confidence score — no relationship exists without a confidence estimate |
| **Evidence-backed** | Every relationship has a provenance record — the evidence that established it |
| **Evolution is expected** | Relationships are expected to strengthen, weaken, and change over time |
| **Graph-native** | The Relationship Engine is designed for graph traversal, not just point lookups |
| **Audit by default** | Every relationship creation, update, and retirement is permanently audited |

---

## PART II — RELATIONSHIP ARCHITECTURE

### 2.1 Relationship Hierarchy Overview

The IIOS defines 15 relationship categories organised in a hierarchy. Every relationship type in the system belongs to one of these categories. Category membership determines default governance policies, audit levels, quality dimension weights, and lifecycle rules.

```
RELATIONSHIP ROOT (abstract base for all relationships)
│
├── STRUCTURAL RELATIONSHIPS
│   ├── COMPOSED_OF
│   ├── AGGREGATES
│   ├── CONTAINS
│   └── INHERITS_FROM
│
├── OWNERSHIP RELATIONSHIPS
│   ├── OWNS
│   ├── MANAGES
│   ├── RESPONSIBLE_FOR
│   └── DELEGATES_TO
│
├── FINANCIAL RELATIONSHIPS
│   ├── GENERATES (Strategy → Hypothesis)
│   ├── TRIGGERS (DecisionRecord → Order)
│   ├── FILLS_AT (Order → Fill)
│   ├── CONTRIBUTES_TO (Fill → Trade)
│   └── RESULTS_IN_PNL (Trade → Portfolio)
│
├── CORPORATE RELATIONSHIPS
│   ├── LISTED_AS (Company → Symbol)
│   ├── CONSTITUENT_OF (Symbol → Index)
│   ├── CLASSIFIED_IN (Symbol → Sector)
│   └── PARENT_OF (Company → Company, for conglomerates)
│
├── MARKET RELATIONSHIPS
│   ├── TRACKS (DataFeed → Symbol)
│   ├── PRICES (MarketSession → Symbol)
│   ├── EXPIRES_ON (Option → ExpirySchedule)
│   └── BENCHMARKS_AGAINST (Strategy → Index)
│
├── ECONOMIC RELATIONSHIPS
│   ├── CHARACTERISED_BY (Regime → MacroIndicator)
│   ├── TRIGGERED_BY (Regime → EconomicEvent)
│   ├── CORRELATED_WITH (MacroIndicator ↔ Symbol)
│   └── LEADS (MacroIndicator → Market effect)
│
├── KNOWLEDGE RELATIONSHIPS
│   ├── DERIVED_FROM (KnowledgeRecord → Trade)
│   ├── VALIDATES (KnowledgeRule → Strategy)
│   ├── SUPERSEDES (KnowledgeRecord → KnowledgeRecord)
│   └── EVIDENCED_BY (KnowledgeFact → LearningRecord)
│
├── AI RELATIONSHIPS
│   ├── EVALUATED_BY (Hypothesis → Agent)
│   ├── OPINES_ON (Agent → Hypothesis)
│   ├── DECIDED_BY (Hypothesis → DecisionRecord)
│   └── CALIBRATED_BY (Agent → LearningRecord)
│
├── RISK RELATIONSHIPS
│   ├── CONSTRAINED_BY (Position → RiskThreshold)
│   ├── BREACHES (Position → RiskThreshold)
│   ├── HEDGES (Position ↔ Position)
│   └── CORRELATED_WITH (Position ↔ Position)
│
├── PORTFOLIO RELATIONSHIPS
│   ├── ALLOCATED_FROM (BudgetEnvelope → Strategy)
│   ├── HELD_IN (Position → Portfolio)
│   ├── FUNDED_BY (Allocation → BudgetEnvelope)
│   └── BELONGS_TO (Strategy → Portfolio)
│
├── TEMPORAL RELATIONSHIPS
│   ├── PRECEDES (Event → Event)
│   ├── FOLLOWED_BY (Regime → Regime)
│   ├── CONCURRENT_WITH (Trade ↔ Regime)
│   └── OVERLAPS_WITH (Position ↔ Position)
│
├── EVENT RELATIONSHIPS
│   ├── CAUSED_BY (Trade outcome → EconomicEvent)
│   ├── COINCIDES_WITH (Signal → EconomicEvent)
│   ├── TRIGGERED_BY (KillSwitch → Event)
│   └── PRODUCES (Cycle → DecisionRecord)
│
├── DERIVED RELATIONSHIPS
│   ├── SIMILAR_TO (Strategy ↔ Strategy)
│   ├── OUTPERFORMS (Strategy → Strategy)
│   ├── ANTI-CORRELATED_WITH (Symbol ↔ Symbol)
│   └── REGIME_FITTED_TO (Strategy → Regime)
│
├── CROSS-DOMAIN RELATIONSHIPS
│   ├── INFLUENCES (MacroIndicator → Strategy)
│   ├── SENSITIVE_TO (Strategy → Regime)
│   ├── CONFIRMS (EconomicEvent → Hypothesis)
│   └── CONTRADICTS (EconomicEvent → Hypothesis)
│
└── STRUCTURAL GOVERNANCE RELATIONSHIPS
    ├── GOVERNED_BY (Entity → GovernancePolicy)
    ├── APPROVED_BY (Entity → Human Principal)
    ├── AUDITED_BY (Entity → AuditRecord)
    └── VERSIONED_AS (Entity → VersionRecord)
```

---

### 2.2 Relationship Root

**Definition:** The Relationship Root is the abstract base from which all concrete relationship types are derived. It defines the universal set of fields and behaviours that every relationship instance must have.

**Root relationship fields (every relationship instance has these):**

| Field | Type | Description |
|---|---|---|
| `relationship_id` | UUID4 | Globally unique, permanent identifier |
| `relationship_type` | RelationshipType enum | Specific type (e.g., GENERATES, CAUSES) |
| `relationship_category` | RelationshipCategory enum | One of the 15 categories |
| `source_entity_id` | UUID4 | The origin entity of the relationship |
| `source_entity_type` | EntityType enum | Type of the source entity |
| `target_entity_id` | UUID4 | The destination entity |
| `target_entity_type` | EntityType enum | Type of the target entity |
| `direction` | Direction enum | DIRECTED, UNDIRECTED, BIDIRECTIONAL |
| `strength` | float [0.0–1.0] | Quantified connection strength |
| `confidence` | float [0.0–1.0] | Confidence that this relationship is true |
| `status` | RelationshipStatus enum | Current lifecycle state |
| `version` | int | Monotonically increasing version number |
| `created_at` | UTC datetime | Creation timestamp |
| `created_by` | string | Service that established this relationship |
| `updated_at` | UTC datetime | Last update timestamp |
| `valid_from` | UTC datetime | When this relationship began (may differ from created_at) |
| `valid_until` | UTC datetime | When this relationship ends (null = indefinite) |
| `provenance_ref` | UUID4 | Reference to the evidence record |
| `owner_id` | string | Responsible owner of this relationship |
| `quality_score` | float | Composite quality score |
| `metadata` | JSON | Type-specific additional attributes |
| `lineage_id` | UUID4 | Lineage record |
| `schema_version` | int | Schema version at creation |
| `tags` | List[string] | Searchable tags |

---

### 2.3 Structural Relationships

**Purpose:** Structural relationships define how entities are assembled into composites, aggregates, and hierarchies. They are the architectural relationships that determine entity boundaries and consistency rules.

**Structural relationship types:**

| Type | Source | Target | Direction | Description |
|---|---|---|---|---|
| `COMPOSED_OF` | Aggregate root | Component | DIRECTED | The component is part of the composite; lifecycle coupled |
| `AGGREGATES` | Collection | Member | DIRECTED | The member is part of the collection; lifecycle independent |
| `CONTAINS` | Container | Contained | DIRECTED | Logical containment (e.g., Index CONTAINS Symbol) |
| `INHERITS_FROM` | Child type | Parent type | DIRECTED | Type hierarchy relationship |

**Structural relationship invariants:**
- `COMPOSED_OF` relationships are the strongest structural type. They create lifecycle coupling — composing entity retirement implies component retirement.
- `AGGREGATES` relationships are weaker — aggregating entity changes do not automatically affect members.
- No circular `COMPOSED_OF` chains are permitted (no entity can be composed of itself through any chain length).

---

### 2.4 Financial Relationships

**Purpose:** Financial relationships form the primary chain of evidence linking strategies to decisions to orders to trades to P&L to learning. They are the most critical relationships for audit, accountability, and performance attribution.

**The primary financial chain:**

```
Strategy
   │ GENERATES
   ▼
Hypothesis
   │ EVALUATED_BY (×62 agents)
   ▼
DecisionRecord
   │ TRIGGERS
   ▼
Order
   │ FILLED_BY
   ▼
Fill (×N partial fills)
   │ CONTRIBUTES_TO
   ▼
Trade
   │ RESULTS_IN_PNL (of)
   ▼
Portfolio (P&L impact)
   │ GENERATES_LEARNING
   ▼
LearningRecord
   │ UPDATES
   ▼
KnowledgeRecord
   │ CALIBRATES
   ▼
Agent (calibration update)
   │ INFLUENCES
   ▼
Strategy (parameter or weight evolution)
```

This chain is the core intelligence loop of the IIOS. Every link in this chain is a managed relationship with its own identity, lifecycle, and quality score.

**Financial relationship governance:** Financial relationships follow the highest governance standard — Full audit, REGULATORY retention, Human Principal notification for any anomalies in the chain.

---

### 2.5 Corporate Relationships

**Purpose:** Corporate relationships model the real-world structure of the companies and securities that the system trades — their organisational hierarchy, index memberships, and sector classifications.

**Corporate relationship examples:**

| Relationship | Description |
|---|---|
| TATA STEEL `LISTED_AS` TATASTEEL (NSE Symbol) | The company is listed under this exchange symbol |
| TATASTEEL `CONSTITUENT_OF` NIFTY50 (Index) | The symbol is a constituent of this index |
| TATASTEEL `CLASSIFIED_IN` METALS (Sector) | The symbol belongs to this sector |
| TATA STEEL `PARENT_OF` TATA METALIKS | Conglomerate structure |

**Corporate relationship stability:** Corporate relationships are among the most stable in the IIOS — they change infrequently and only when external corporate events occur (index rebalancing, sector reclassification, mergers). When they do change, the change is significant and must be propagated to dependent relationships (e.g., all strategies that have `BENCHMARKS_AGAINST` NIFTY50 relationships).

---

### 2.6 Economic Relationships

**Purpose:** Economic relationships connect market regimes to the macroeconomic indicators and events that characterise them, and to the market instruments and strategies that are sensitive to them.

**Key economic relationships:**

| Relationship | Source | Target | Notes |
|---|---|---|---|
| `CHARACTERISED_BY` | Regime:BULL | MacroIndicator:VIX (low) | VIX below threshold characterises this regime |
| `TRIGGERED_BY` | Regime:CRISIS | EconomicEvent:RBI_EMERGENCY_CUT | Rate cut triggered this regime transition |
| `CORRELATED_WITH` | MacroIndicator:VIX | Symbol:NIFTY50 | Negative correlation |
| `LEADS` | MacroIndicator:US10Y_YIELD | MacroIndicator:INDIA_10Y_YIELD | US yield leads India yield by avg 2 weeks |

**Economic relationship confidence:** Economic relationships are probabilistic — correlations change, leading indicators sometimes fail. Every economic relationship carries both a strength (the historical degree of relationship) and a confidence (our current certainty that the relationship holds).

---

### 2.7 Knowledge Relationships

**Purpose:** Knowledge relationships form the provenance chain of the IIOS's knowledge base — connecting knowledge records back to the evidence that established them.

**Knowledge relationship chain:**

```
LearningRecord (from closed Trade)
     │ EVIDENCED_BY
     ▼
KnowledgeFact (specific factual claim)
     │ AGGREGATES_INTO
     ▼
KnowledgePattern (a recurring pattern)
     │ SUPPORTS
     ▼
KnowledgeRule (a validated rule)
     │ VALIDATES / INVALIDATES
     ▼
Strategy (the rule supports or contradicts this strategy's parameters)
```

---

### 2.8 AI Relationships

**Purpose:** AI relationships connect the 62 AI agents to the hypotheses they evaluate and the decisions they influence, creating a complete record of AI reasoning that can be analysed, audited, and used for agent calibration.

| Relationship | Source | Target | Strength basis |
|---|---|---|---|
| `EVALUATED_BY` | Hypothesis | Agent | Binary (all hypotheses are evaluated by all agents) |
| `OPINES_ON` | Agent | Hypothesis | Weighted by agent calibration score |
| `DECIDED_BY` | Hypothesis | DecisionRecord | Binary (one decision per hypothesis) |
| `CALIBRATED_BY` | Agent | LearningRecord | Updates agent accuracy over time |
| `DISSENTED_FROM` | Agent | DecisionRecord | Agent voted against the final decision |

**AI relationship significance:** `DISSENTED_FROM` relationships are analytically critical. A pattern where a specific agent consistently dissents from decisions that later prove to be losses is a signal that this agent's viewpoint is systematically more accurate. The Reasoning Manager uses dissent relationship patterns to identify consistently prescient agents.

---

### 2.9 Risk Relationships

**Purpose:** Risk relationships model how risk propagates through the portfolio — how individual position risks constrain overall portfolio capacity, how positions hedge each other, and how threshold breaches interact.

**Risk relationship types:**

| Type | Description | Direction | Lifecycle |
|---|---|---|---|
| `CONSTRAINED_BY` | Position is constrained by a RiskThreshold | Directed | Exists while both entities are ACTIVE |
| `BREACHES` | Position has exceeded a RiskThreshold | Directed | Created at breach; closed at resolution |
| `HEDGES` | Position A partially hedges Position B | Bidirectional | Exists while both positions are OPEN |
| `CORRELATED_WITH` | Position A is correlated with Position B (risk concentration) | Undirected | Maintained continuously |

---

### 2.10 Temporal Relationships

**Purpose:** Temporal relationships express time-based connections between entities — which events precede others, which market sessions were concurrent with which trades, which regimes followed which.

**Temporal relationship types:**

| Type | Description | Direction |
|---|---|---|
| `PRECEDES` | A happened before B (with the causal direction implied) | Directed |
| `FOLLOWED_BY` | B came immediately after A (tighter than PRECEDES) | Directed |
| `CONCURRENT_WITH` | A and B overlapped in time | Undirected |
| `OVERLAPS_WITH` | A started before B ended, but also ended before B ended | Bidirectional |
| `BOUNDED_BY` | A occurred entirely within B's time window | Directed |

Temporal relationships are the backbone of causal chain analysis. The Reasoning Manager uses temporal relationship chains to establish the sequence of events that led to a specific trade outcome.

---

### 2.11 Derived Relationships

**Purpose:** Derived relationships are computed by the system's analytical layer — they are not directly observed but are inferred from patterns in entity data.

**Key derived relationships:**

| Type | Basis | Description |
|---|---|---|
| `SIMILAR_TO` | Parameter cosine similarity | Two strategies have similar parameter vectors |
| `OUTPERFORMS` | Win rate and Sharpe ratio comparison | Strategy A demonstrably outperforms Strategy B in regime R |
| `ANTI_CORRELATED_WITH` | Pearson coefficient < −0.7 | Two symbols' price series move in opposite directions |
| `REGIME_FITTED_TO` | Backtest performance | Strategy was designed / evolved for this specific regime |

**Derived relationship confidence decay:** Derived relationships are statistical — they are based on historical patterns that may not hold in the future. They carry a temporal confidence decay: if a `SIMILAR_TO` relationship has not been reconfirmed within 30 days, its confidence decays toward the threshold (0.30) and triggers recomputation.

---

### 2.12 Cross-Domain Relationships

**Purpose:** Cross-domain relationships express connections that cut across the traditional entity category boundaries — connecting macroeconomic entities to AI entities, financial events to knowledge records, and regime states to strategy behaviour.

**Key cross-domain relationships:**

| Type | Source Domain | Target Domain | Description |
|---|---|---|---|
| `INFLUENCES` | MacroIndicator | Strategy | Rising VIX influences strategy selection |
| `SENSITIVE_TO` | Strategy | Regime | This strategy performs differently across regimes |
| `CONFIRMS` | EconomicEvent | Hypothesis | Event evidence confirms this hypothesis was correct |
| `CONTRADICTS` | EconomicEvent | Hypothesis | Event evidence contradicts this hypothesis |
| `INFORMS` | LearningRecord | Agent | This learning record should update this agent's prior |

Cross-domain relationships are the most analytically rich — they reveal the connections between macroeconomic reality, strategy design, and trading outcomes that enable genuine market intelligence.

---
## PART III — RELATIONSHIP COMPONENTS

### 3.1 Component Architecture Overview

The Relationship Engine is composed of seventeen components. These components are cohesive sub-systems within the Relationship Engine that collaborate through well-defined internal interfaces. Unlike entity management, the Relationship Engine has three additional components that reflect its unique analytical responsibilities: the Reasoning Manager, the Discovery Manager, and the Evolution Manager.

```
RELATIONSHIP ENGINE COMPONENT MAP

┌──────────────────────────────────────────────────────────────────────────────┐
│                         RELATIONSHIP ENGINE                                  │
│                                                                              │
│  ┌──────────────────┐  ┌───────────────────┐  ┌───────────────────────────┐  │
│  │ Relationship     │  │ Relationship      │  │ Relationship Factory     │  │
│  │ Registry         │  │ Catalog           │  │                          │  │
│  └──────────────────┘  └───────────────────┘  └───────────────────────────┘  │
│                                                                              │
│  ┌──────────────────┐  ┌───────────────────┐  ┌───────────────────────────┐  │
│  │ Relationship     │  │ Identity          │  │ Lifecycle Manager        │  │
│  │ Validator        │  │ Manager           │  │                          │  │
│  └──────────────────┘  └───────────────────┘  └───────────────────────────┘  │
│                                                                              │
│  ┌──────────────────┐  ┌───────────────────┐  ┌───────────────────────────┐  │
│  │ Version Manager  │  │ Metadata Manager  │  │ Relationship Index       │  │
│  └──────────────────┘  └───────────────────┘  └───────────────────────────┘  │
│                                                                              │
│  ┌──────────────────┐  ┌───────────────────┐  ┌───────────────────────────┐  │
│  │ Cache            │  │ Search Engine     │  │ Audit Manager            │  │
│  └──────────────────┘  └───────────────────┘  └───────────────────────────┘  │
│                                                                              │
│  ┌──────────────────┐  ┌───────────────────┐  ┌───────────────────────────┐  │
│  │ Integrity Mgr    │  │ Governance Mgr    │  │ Reasoning Manager        │  │
│  └──────────────────┘  └───────────────────┘  └───────────────────────────┘  │
│                                                                              │
│  ┌──────────────────┐  ┌───────────────────┐                                 │
│  │ Discovery Mgr    │  │ Evolution Manager │                                 │
│  └──────────────────┘  └───────────────────┘                                 │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

### 3.2 Relationship Registry

**Purpose:** The Relationship Registry is the single authoritative index of all relationships that exist or have ever existed in the IIOS. It answers the question: "Does this relationship exist between these two entities?"

**Responsibilities:**

| Responsibility | Description |
|---|---|
| Relationship enrollment | Record a new relationship into the registry at creation time |
| Relationship lookup by ID | Resolve a `relationship_id` to confirm existence and return current status |
| Source-to-target lookup | Find all relationships from a given source entity |
| Target-to-source lookup | Find all relationships pointing to a given target entity |
| Type-filtered lookup | Find all relationships of a given type |
| Entity-pair lookup | Find all relationships between two specific entities (any type) |
| Existence check | Confirm whether a specific relationship type exists between two entities |
| Count queries | Count relationships by type, category, or status |

**Registry design:** The Registry maintains a dual representation:
- **Persistent store:** Full relationship record in the relationship table (via DATABASE_PERSISTENCE)
- **In-memory adjacency index:** A dictionary structure mapping `(source_entity_id, relationship_type, target_entity_id)` → `relationship_id` for hot-path existence checks

The adjacency index is the primary data structure for graph traversal — it enables O(1) lookup of whether a specific relationship type exists between two entities, and O(E) traversal of all outgoing edges from a node.

**Inputs:** Entity IDs, relationship types, status filters
**Outputs:** RelationshipRecord, List[relationship_id], bool (existence), int (count)
**Dependencies:** Entity Registry (to verify source and target entities exist)
**Failure handling:** Registry write failures roll back the Factory creation sequence. Registry read failures on hot-path lookups fall back to the persistence layer.

---

### 3.3 Relationship Catalog

**Purpose:** The Relationship Catalog is the definition store — the record of every relationship type that the system is authorised to create, including which entity types may be connected, what the valid direction is, and what invariants apply.

**Responsibilities:**

| Responsibility | Description |
|---|---|
| Relationship type registration | Register the definition of each relationship type |
| Schema version management | Track schema changes to relationship type definitions |
| Allowed endpoint validation | Define which entity types may be source and target for each relationship type |
| Cardinality definition | Define whether a relationship type is 1:1, 1:N, or N:M |
| Directionality definition | Define whether each type is DIRECTED, UNDIRECTED, or BIDIRECTIONAL |
| Quality dimension weights | Define the quality weight profile for each relationship type |
| Lifecycle definition | Define allowed lifecycle states for each type |
| Constraint definition | Define structural constraints (e.g., no circular COMPOSED_OF) |

**Catalog structure per relationship type:**

| Field | Description |
|---|---|
| `relationship_type` | The type identifier (e.g., GENERATES) |
| `category` | The relationship category |
| `allowed_source_types` | List of entity types that may be the source |
| `allowed_target_types` | List of entity types that may be the target |
| `direction` | DIRECTED / UNDIRECTED / BIDIRECTIONAL |
| `cardinality` | ONE_TO_ONE / ONE_TO_MANY / MANY_TO_MANY |
| `strength_computation` | How strength is computed for this type |
| `confidence_basis` | How confidence is established |
| `lifecycle_states` | Valid states |
| `invariants` | Constraint rule IDs that apply |
| `audit_level` | MINIMAL / STANDARD / FULL |
| `schema_version` | Current schema version |

**Inputs:** RelationshipTypeDefinition structs
**Outputs:** RelationshipTypeDefinition, validation schemas, cardinality rules
**Dependencies:** Entity Catalog (for valid entity type references)
**Failure handling:** Unknown relationship types cause `UnknownRelationshipTypeError`; no relationship can be created for an unregistered type.

---

### 3.4 Relationship Factory

**Purpose:** The Relationship Factory is the standardised creation mechanism for all relationships. No relationship may be created by directly writing to the persistence layer — all relationship creation goes through the Factory.

**Responsibilities:**

| Responsibility | Description |
|---|---|
| Identity assignment | Generate and assign a permanent `relationship_id` (UUID4) |
| Catalog lookup | Retrieve the type definition to apply defaults and validate cardinality |
| Cardinality enforcement | Check whether creating this relationship would violate cardinality constraints |
| Default application | Apply default confidence, strength, and metadata for the type |
| Version initialisation | Create the initial version record (v1) |
| Provenance initialisation | Create the initial provenance/lineage record |
| Registry enrollment | Enroll the relationship in the Registry and update the adjacency index |
| Audit record creation | Create the `RELATIONSHIP_CREATED` audit event |
| Cache population | Add the relationship to the active relationship cache |

**Factory creation sequence:**

```
Caller provides creation parameters (source_id, target_id, type, strength, confidence, evidence)
         │
         ▼
[Factory: Lookup Catalog for type definition]
         │
         ▼
[Factory: Validate source entity exists and is ACTIVE]
         │
         ▼
[Factory: Validate target entity exists and is ACTIVE]
         │
         ▼
[Factory: Check cardinality constraints]
         │
         ├──► [VIOLATION] → CardinalityViolationError; no relationship created
         │
         ▼
[Factory: Check for duplicate relationship (same type, same pair)]
         │
         ├──► [DUPLICATE] → Return existing or raise DuplicateRelationshipError
         │
         ▼
[Factory: Generate relationship_id (UUID4)]
         │
         ▼
[Factory: Apply type defaults and initialise all Root fields]
         │
         ▼
[Factory: Create Version 1 record]
         │
         ▼
[Factory: Create provenance record]
         │
         ▼
[Factory: Enroll in Registry + update adjacency index]
         │
         ▼
[Factory: Create RELATIONSHIP_CREATED audit event]
         │
         ▼
[Factory: Populate cache]
         │
         ▼
Return created relationship to caller
```

**Inputs:** Source entity_id, target entity_id, relationship_type, strength, confidence, evidence, metadata
**Outputs:** RelationshipRecord (fully created relationship)
**Dependencies:** Relationship Catalog, Relationship Registry, Entity Registry, Version Manager, Audit Manager
**Failure handling:** Any failure in the creation sequence triggers a full rollback. The relationship_id is released, Registry enrollment is reversed, and a `CREATION_FAILED` event is logged.

---

### 3.5 Relationship Validator

**Purpose:** The Relationship Validator enforces all relationship invariants at creation time, update time, and on-demand during integrity checks.

**Responsibilities:**

| Responsibility | Description |
|---|---|
| Type validity | Confirm relationship_type is registered in the Catalog |
| Endpoint type validation | Confirm source and target entity types match allowed types for this relationship type |
| Endpoint existence validation | Confirm source and target entities exist and are in valid states |
| Cardinality validation | Confirm cardinality constraints are not violated |
| Direction validation | Confirm the direction is consistent with the type definition |
| Strength validation | Confirm strength is in [0.0, 1.0] |
| Confidence validation | Confirm confidence is in [0.0, 1.0] |
| Invariant validation | Check all relationship-type-specific invariants |
| Circular dependency detection | Detect cycles in COMPOSED_OF and DEPENDS_ON chains |
| Self-referential validation | Block relationships where source = target (unless explicitly permitted for this type) |
| Temporal validity | Confirm valid_from and valid_until are logically ordered |

**Validation layers:**

| Layer | Description |
|---|---|
| Structural | Type, direction, strength range, confidence range, field types |
| Referential | Endpoint entities exist and are ACTIVE |
| Cardinality | Constraints not violated |
| Graph integrity | No cycles, no self-references (unless permitted), no invalid chains |
| Business rules | Type-specific domain invariants |

**Inputs:** Relationship creation or update parameters, existing relationship record (for updates)
**Outputs:** ValidationResult with is_valid, violated_rules, severity breakdown
**Dependencies:** Relationship Catalog, Entity Registry, Relationship Registry (for cycle detection)
**Failure handling:** Validation failures raise `RelationshipValidationError` containing the entity IDs, relationship type, and the specific violated invariant rule ID. Validation failures never create partial relationship records.

---

### 3.6 Relationship Identity Manager

**Purpose:** The Identity Manager maintains the complete identity record of every relationship — its canonical UUID4, all aliases, all external system references, and its complete version ID chain.

**Responsibilities:**

| Responsibility | Description |
|---|---|
| Canonical identity maintenance | Maintain the relationship_id as the permanent canonical identifier |
| Relationship alias registration | Register human-readable names for specific relationship instances |
| External reference mapping | Map external system relationship IDs to canonical relationship_id |
| Duplicate detection | Detect when a proposed new relationship is a duplicate of an existing one |
| Identity resolution | Given any identifier, return the canonical relationship_id |
| Conflict resolution | Resolve identity conflicts for relationships that may represent the same connection |

**Relationship alias examples:**
- "the primary leverage between VIX and NIFTY" → relationship_id of VIX `CORRELATED_WITH` NIFTY50
- "strategy-3 generation chain" → relationship_id of MomentumBreakoutV3 `GENERATES` Hypothesis

**Inputs:** Any identifier (UUID4, alias, external ref), new relationship record (for duplicate check)
**Outputs:** Canonical relationship_id, DuplicateCandidate list, IdentityRecord
**Dependencies:** Relationship Registry
**Failure handling:** `IdentityResolutionError` when identifier cannot be resolved to any registered relationship. Duplicate conflicts escalate to Governance Manager.

---

### 3.7 Relationship Lifecycle Manager

**Purpose:** The Lifecycle Manager governs all relationship state transitions, enforcing the defined state machine and coordinating all side effects of lifecycle changes.

**Responsibilities:**

| Responsibility | Description |
|---|---|
| State transition execution | Move a relationship from one lifecycle state to another |
| Precondition validation | Verify all preconditions for a transition are met |
| Adjacency index update | Update the in-memory graph index on every state change |
| Side effect coordination | Trigger version increment, audit record, downstream event |
| Blocked transition handling | Record blocked transitions with reason |
| Lifecycle event publishing | Publish lifecycle events to IIOS EventBus |
| Cascade management | When an entity is archived, cascade to all its relationships |

**Cascade archival:** When an entity is archived, the Lifecycle Manager receives a cascade signal and transitions all relationships where the entity is a participant to ARCHIVED status. This preserves the historical graph structure while removing the relationships from active query paths.

**Inputs:** relationship_id, target_state, reason, (optional) auth_token
**Outputs:** Updated RelationshipRecord
**Dependencies:** Lifecycle state machine (from Catalog), Version Manager, Audit Manager, EventBus
**Failure handling:** Precondition failures raise `LifecyclePreConditionError`. Cascade failures are logged and retried up to 3 times before raising a governance alert.

---

### 3.8 Relationship Version Manager

**Purpose:** The Version Manager records every state of every relationship over time. Relationships evolve — their strength changes, their confidence changes, their validity window extends or contracts — and every change is permanently archived.

**Responsibilities:**

| Responsibility | Description |
|---|---|
| Version creation | Create a new version record on every relationship update |
| Version numbering | Assign monotonically increasing version numbers |
| Version storage | Persist version records to the relationship version store |
| Version retrieval | Retrieve the state of a relationship at any past version |
| Strength history | Provide a time series of strength values for a relationship |
| Confidence history | Provide a time series of confidence values for a relationship |
| Version diff | Compute the difference between two versions |

**Version record fields:**

| Field | Description |
|---|---|
| `version_id` | UUID4 for this specific version |
| `relationship_id` | Reference to parent relationship |
| `version_number` | Monotonically increasing integer |
| `strength` | Strength value at this version |
| `confidence` | Confidence value at this version |
| `status` | Lifecycle status at this version |
| `state_snapshot` | Complete relationship state (JSON) |
| `diff_from_previous` | Changed fields only |
| `changed_by` | Service or actor |
| `change_reason` | Human-readable reason |
| `changed_at` | UTC timestamp |

**Inputs:** relationship_id, complete state snapshot, changed_by, reason
**Outputs:** VersionRecord
**Dependencies:** Persistence layer
**Failure handling:** Version write failures are retried 3 times before raising `VersionWriteError`. Duplicate version numbers cause immediate alerting and investigation.

---

### 3.9 Relationship Metadata Manager

**Purpose:** The Metadata Manager maintains all supplementary information about a relationship — context, annotations, custom attributes, and temporal metadata that is not part of the core relationship record.

**Responsibilities:**

| Responsibility | Description |
|---|---|
| Evidence metadata | Store the evidence record that supports this relationship |
| Temporal context | Store regime context, market session context, and cycle context at relationship creation |
| Annotation management | Store human-added notes and labels |
| Custom attribute management | Store relationship-type-specific computed attributes |
| External context | Links to external sources that support this relationship |
| Statistical metadata | Historical strength distribution, confidence intervals |

**Metadata is append-friendly:** New metadata attributes may be added without schema migration (JSON blob storage). Attributes that need to be searched or indexed must be declared and indexed.

**Inputs:** relationship_id, key-value attribute pairs
**Outputs:** MetadataRecord
**Dependencies:** Persistence layer
**Failure handling:** Metadata write failures are non-fatal — they are logged and retried asynchronously.

---

### 3.10 Relationship Index

**Purpose:** The Relationship Index provides high-performance structured lookups for the most common relationship access patterns. It is distinct from the Search Engine, which handles flexible discovery queries.

**Indices maintained:**

| Index | Key | Description |
|---|---|---|
| Outgoing edges by source | source_entity_id → List[relationship_id] | All relationships originating from an entity |
| Incoming edges by target | target_entity_id → List[relationship_id] | All relationships pointing to an entity |
| Type index | relationship_type → List[relationship_id] | All relationships of a given type |
| Type + source | (relationship_type, source_id) → List[relationship_id] | All relationships of a type from a source |
| Type + target | (relationship_type, target_id) → List[relationship_id] | All relationships of a type to a target |
| Entity pair | (source_id, target_id) → List[relationship_id] | All relationships between two entities |
| Status index | status → List[relationship_id] | All relationships in a given lifecycle state |
| Strength range | (type, strength_min, strength_max) → List[relationship_id] | Relationships above a strength threshold |
| Confidence range | confidence_min → List[relationship_id] | Relationships above a confidence threshold |
| Temporal | valid_from / valid_until ranges | Relationships active at a point in time |

**Index update policy:** Indices are updated synchronously on relationship creation and status change. Strength and confidence updates trigger asynchronous index refreshes (batched every 30 seconds during market hours).

**Inputs:** Query parameters (source_id, target_id, type, status, strength range, confidence range)
**Outputs:** List[relationship_id], with optional full record hydration
**Dependencies:** Relationship Registry, Persistence layer
**Failure handling:** Index unavailability falls back to full persistence scan with a WARNING log.

---

### 3.11 Relationship Cache

**Purpose:** The Relationship Cache provides fast in-memory access to active relationships, primarily for graph traversal during cycle-time intelligence operations.

**Cache tiers:**

| Tier | Contents | Access time | Size limit |
|---|---|---|---|
| L1 — Critical graph | Core financial chain relationships; risk relationships; kill switch relationships | < 1 ms | Fixed, small |
| L2 — Active operational | All ACTIVE relationships for ACTIVE entities | < 2 ms | Dynamic |
| L3 — Recent traversal | Recently traversed relationship paths (LRU cache) | < 5 ms | Configurable |
| L4 — Persistence | Full relationship store | 10–50 ms | Unlimited |

**Cache structure:** The cache stores lightweight relationship summaries (source, target, type, strength, confidence, status) for the L1/L2 tiers. Full relationship records are loaded on demand.

**Cache warm-up:** The Cache Service pre-loads L1 and L2 cache tiers at system startup (pre-market warm-up). Critical relationships are always in L1.

**Inputs:** relationship_id (point lookup), entity_id + type (graph traversal lookup)
**Outputs:** RelationshipRecord or RelationshipSummary
**Dependencies:** Relationship Registry, Relationship Index
**Failure handling:** Cache misses for L1 (critical) relationships trigger immediate persistence reads and re-population. L1 cache population failures trigger a system health alert.

---

### 3.12 Relationship Search Engine

**Purpose:** The Search Engine provides flexible relationship discovery — finding relationships that match complex criteria across the full relationship population.

**Responsibilities:**

| Responsibility | Description |
|---|---|
| Full-text search | Search relationship types, metadata descriptions, and annotations |
| Attribute search | Search by source entity type, target entity type, strength range, confidence range |
| Graph pattern search | Find relationships matching a graph pattern (e.g., A → B → C pattern) |
| Temporal search | Find relationships active during a specific time window |
| Category search | Find all relationships of a specific category |
| Combined criteria | Multiple criteria with AND/OR operators |

**Inputs:** SearchQuery (criteria, filters, ordering, limit, offset)
**Outputs:** List[RelationshipSummary] with total count, query time, index used
**Dependencies:** Relationship Index, Relationship Cache
**Failure handling:** Timeout returns partial results with `truncated = True`. Full index unavailability falls back to slow scan with WARNING.

---

### 3.13 Relationship Audit Manager

**Purpose:** The Audit Manager records every significant event in the life of every relationship — creation, updates, strength changes, lifecycle transitions, and governance actions.

**Responsibilities:**

| Responsibility | Description |
|---|---|
| Event recording | Record all audit-eligible relationship events |
| Event immutability | Ensure audit records cannot be modified or deleted |
| Audit chain integrity | Hash-chain all relationship audit records |
| Compliance reporting | Generate compliance audit reports for relationship history |
| Event querying | Allow authorised queries against the audit log |

**Audit event types:**

| Event type | Trigger |
|---|---|
| `RELATIONSHIP_CREATED` | New relationship created |
| `RELATIONSHIP_STRENGTH_CHANGED` | Strength updated (with old and new values) |
| `RELATIONSHIP_CONFIDENCE_CHANGED` | Confidence updated |
| `RELATIONSHIP_TRANSITION` | Lifecycle state transition |
| `RELATIONSHIP_OWNERSHIP_CHANGED` | Owner changed |
| `RELATIONSHIP_MERGED` | Relationship merged with another |
| `RELATIONSHIP_DEPRECATED` | Relationship deprecated |
| `RELATIONSHIP_RETIRED` | Relationship retired |
| `RELATIONSHIP_INTEGRITY_VIOLATION` | Integrity checker found a violation |

**Inputs:** Relationship event data (event type, entity IDs, old/new state, actor, timestamp)
**Outputs:** AuditRecord with audit_id
**Dependencies:** Audit persistence store (write-once, append-only)
**Failure handling:** Audit write failures raise `AuditWriteError`. No relationship operation completes if its audit record cannot be written (for FULL audit level relationships).

---

### 3.14 Relationship Integrity Manager

**Purpose:** The Integrity Manager performs scheduled and on-demand cross-relationship consistency checks — verifying that the relationship graph as a whole satisfies all defined invariants.

**Responsibilities:**

| Responsibility | Description |
|---|---|
| Dangling edge detection | Find relationships where source or target entity no longer exists in ACTIVE state |
| Circular dependency detection | Find circular chains of COMPOSED_OF or DEPENDS_ON relationships |
| Cardinality violation detection | Find relationships that violate cardinality constraints |
| Orphan relationship detection | Find relationships not connected to any valid entity |
| Temporal consistency checks | Find relationships with logically inconsistent valid_from / valid_until |
| Cascade completeness | Verify that all relationships for archived entities are also archived |
| Integrity reporting | Produce a report of all violations found |

**Scheduled scans:**

| Scan | Frequency | Scope |
|---|---|---|
| Hot relationship health check | Every cycle | L1 + L2 cache relationships |
| Operational integrity scan | Daily (after market close) | All ACTIVE relationships |
| Full population integrity scan | Weekly | Full relationship population |
| Graph cycle detection | Daily | COMPOSED_OF and DEPENDS_ON chains |

**Inputs:** Triggered automatically on schedule, or by explicit call from Governance Service
**Outputs:** IntegrityReport (violations list, severity breakdown, affected relationship IDs)
**Dependencies:** Relationship Registry, Relationship Index, Entity Registry
**Failure handling:** Integrity scan failures are logged and retried. CRITICAL integrity violations (dangling edges for financial entities) trigger immediate governance alerts.

---

### 3.15 Relationship Governance Manager

**Purpose:** The Governance Manager enforces ownership policies, approval workflows, compliance requirements, and governance rules across the relationship population.

**Responsibilities:**

| Responsibility | Description |
|---|---|
| Ownership assignment and tracking | Maintain the owner record for each relationship |
| Policy application | Apply governance policies by relationship type |
| Compliance monitoring | Monitor for governance violations |
| Approval workflow management | Manage approval chains for relationships requiring sign-off |
| Conflict resolution routing | Route identity conflicts to appropriate resolution authority |
| Governance reporting | Generate governance health reports |

**Inputs:** Relationship governance events, policy definitions, compliance check requests
**Outputs:** GovernanceStatus, GovernanceReport, approval/rejection records
**Dependencies:** Governance Manager (Entity Engine), Human Principal notification (via Telegram)
**Failure handling:** Governance enforcement failures generate governance events. CRITICAL violations generate immediate Telegram alerts to the Human Principal.

---

### 3.16 Relationship Reasoning Manager

**Purpose:** The Reasoning Manager is the analytical intelligence core of the Relationship Engine. It provides higher-order intelligence capabilities: path analysis, influence propagation, causal chain reconstruction, and relationship pattern detection.

**Responsibilities:**

| Responsibility | Description |
|---|---|
| Multi-hop path analysis | Find and rank paths between two entities across multiple relationship hops |
| Influence propagation | Compute how a change in one entity propagates through influence relationships to other entities |
| Causal chain reconstruction | Given a trade outcome, reconstruct the complete causal chain of entities and relationships |
| Pattern detection | Detect recurring relationship patterns that may have analytical significance |
| Relationship strength inference | Infer missing relationship strengths from known relationships using graph completion |
| Contradiction detection | Detect relationship pairs that contradict each other |
| Transitivity reasoning | Apply transitive closure to infer indirect relationships |

**Influence propagation design:**

```
INFLUENCE PROPAGATION MODEL

Starting entity (e.g., MacroIndicator:VIX, value spike)
         │
         ▼
Find all INFLUENCES relationships from this entity
         │
    ┌────┴─────┬──────────────┐
    ▼          ▼              ▼
Strategy A  Strategy B   Strategy C
(strength: (strength:   (strength:
   0.8)       0.45)        0.7)
    │
    ▼
Find all INFLUENCES from influenced entities (2nd hop)
    │
    ▼
Risk thresholds, portfolio limits affected at 2nd hop
(strength attenuated: 0.8 × 0.6 = 0.48 effective)
    │
    ▼
Continue until max_hops exceeded or strength < 0.05 threshold
```

The propagation model uses strength multiplication to attenuate influence over hops — a 0.8-strength first-hop influence followed by a 0.6-strength second-hop influence produces a 0.48-effective second-hop influence on the terminal entity.

**Causal chain reconstruction:**

```
Trade outcome: LOSS of ₹12,400
         │ GENERATED_LEARNING (reversed)
         ▼
Trade entity
         │ RESULTED_FROM (reversed)
         ▼
Order (entry)
         │ TRIGGERED_BY (reversed)
         ▼
DecisionRecord
         │ DECIDED_BY (reversed)
         ▼
Hypothesis
         │ GENERATED_BY (reversed)
         ▼
Strategy: MomentumBreakoutV3
         │ VALIDATED_BY (reversed)
         ▼
BacktestResult (what regime was assumed?)
         │ CONCURRENT_WITH (time lookup)
         ▼
Regime at trade time: BEAR_VOLATILE
         │ (strategy was designed for BULL_TRENDING)
         ▼
ROOT CAUSE: Regime mismatch — strategy active in non-fitted regime
```

**Inputs:** Source entity_id, target entity_id (for path finding); event entity (for propagation); outcome entity (for causal reconstruction)
**Outputs:** PathList with scores, InfluenceMap, CausalChain, PatternMatch
**Dependencies:** Relationship Index, Relationship Cache, Entity Engine Query Service
**Failure handling:** Reasoning operations are best-effort and never block operational decisions. Timeouts return partial results. Reasoning results are advisory — they do not directly control system behaviour.

---

### 3.17 Relationship Discovery Manager

**Purpose:** The Discovery Manager proactively identifies potential new relationships that have not been explicitly created — by analysing entity data, event streams, and statistical patterns.

**Responsibilities:**

| Responsibility | Description |
|---|---|
| Statistical correlation discovery | Compute correlations between entity metrics and propose CORRELATED_WITH relationships |
| Causal hypothesis generation | Propose HYPOTHETICALLY_CAUSED_BY relationships when event sequences suggest causation |
| Similarity discovery | Compute strategy parameter similarity and propose SIMILAR_TO relationships |
| Regime sensitivity discovery | Analyse strategy performance across regimes and propose SENSITIVE_TO relationships |
| Influence discovery | Identify macro indicators that statistically precede market moves |
| Discovery confidence scoring | Assign confidence scores to all discovered relationship candidates |
| Human Principal notification | Notify Human Principal of high-confidence discoveries for approval |

**Discovery schedule:**

| Discovery type | Frequency | Minimum data required |
|---|---|---|
| Correlation discovery | Daily (post-close) | 30 trading days |
| Causal hypothesis generation | Daily (post-close) | 20 correlated events |
| Similarity discovery | Weekly | 5 active strategies |
| Regime sensitivity discovery | Weekly | 20 trades per regime |
| Influence discovery | Weekly | 60 trading days |

**Inputs:** Entity metrics (price history, performance statistics, classification changes), Event streams
**Outputs:** List[DiscoveredRelationshipCandidate] with confidence scores and evidence summaries
**Dependencies:** Relationship Search Engine, Entity Engine Query Service, Data Feeds
**Failure handling:** Discovery failures are non-critical — they are logged and retried in the next scheduled window. Discovery never creates relationships directly — all discovered candidates go through the Factory after Human Principal review or automatic approval (if confidence > 0.90 for approved discovery types).

---

### 3.18 Relationship Evolution Manager

**Purpose:** The Evolution Manager monitors existing relationships over time and manages their evolution — strengthening relationships supported by accumulating evidence, weakening relationships whose evidence is fading, and triggering deprecation when relationships fall below viability thresholds.

**Responsibilities:**

| Responsibility | Description |
|---|---|
| Strength evolution | Update relationship strength based on new evidence |
| Confidence evolution | Update confidence based on prediction outcomes vs actuals |
| Temporal decay | Apply confidence decay to relationships that have not been recently reconfirmed |
| Automatic weakening | Flag and weaken relationships whose evidence contradicts the relationship claim |
| Strengthening | Increase strength and confidence for relationships whose claims are consistently confirmed |
| Deprecation trigger | Flag relationships whose confidence has decayed below the deprecation threshold |
| Evolution history | Record the full evolution history of each relationship |

**Strength evolution model:**

$$\text{strength}_{t+1} = \alpha \cdot \text{strength}_{t} + (1 - \alpha) \cdot \text{new\_evidence\_strength}$$

Where $\alpha$ is the decay factor (default: 0.85 — weights recent evidence at 15% and historical at 85%). This exponential moving average prevents wild swings in relationship strength while allowing it to adapt to new evidence.

**Confidence decay model:**

$$\text{confidence}_{t} = \text{confidence}_{0} \cdot e^{-\lambda \cdot \text{days\_since\_confirmation}}$$

Where $\lambda$ is the decay rate (default: 0.01 per day, equivalent to 50% confidence decay in 69 days if not reconfirmed).

**Inputs:** New evidence (closed trade outcomes, regime changes, economic events), schedule triggers
**Outputs:** Updated RelationshipRecord (via Factory), DeprecationCandidateList
**Dependencies:** Learning System (closed trade data), Relationship Version Manager, Relationship Lifecycle Manager
**Failure handling:** Evolution update failures are retried 3 times. Persistent failures generate governance alerts but do not block operational decisions.

---
## PART IV — RELATIONSHIP LIFECYCLE

### 4.1 Lifecycle Overview

Every relationship in the IIOS follows a defined lifecycle. The lifecycle for relationships is richer than for entities — it includes discovery (relationships are often found before they are created), evolution (strength and confidence change over time), strengthening and weakening stages, and a decay-triggered retirement path that reflects the probabilistic nature of most relationship types.

The relationship lifecycle has twelve stages. Not all relationship types pass through all stages — structural relationships (COMPOSED_OF) do not have a Discovery stage (they are always created explicitly), while derived relationships (CORRELATED_WITH) always go through Discovery.

---

### 4.2 The Twelve Lifecycle Stages

**Stage 1: Discovery**

A potential relationship is identified — by the Discovery Manager (statistical analysis), by an event that implies a connection (a trade outcome implies a RESULTED_FROM relationship), or by a human principal observation. At this stage, the relationship is a *candidate* — it has not yet been validated or created.

Discovery produces a `DiscoveredRelationshipCandidate` record with:
- Source and target entity IDs (and types)
- Proposed relationship type
- Initial confidence score (based on discovery evidence)
- Evidence summary
- Discovery method (STATISTICAL, EVENT_IMPLIED, HUMAN_OBSERVED, PATTERN_MATCHED)

The candidate is not a relationship yet — it has no `relationship_id`. It is a proposal awaiting validation.

**Stage 2: Creation**

Creation is the transition from candidate to registered relationship. The Factory executes the full creation sequence: identity assigned, Catalog validated, cardinality checked, version 1 created, Registry enrolled, audit event written.

For event-implied relationships (e.g., `Strategy GENERATES Hypothesis`), creation is automatic — the Factory is called directly by the originating service without a prior discovery stage.

For statistically discovered relationships, creation requires either:
- Automatic approval (if confidence > 0.90 and the discovery type is in the auto-approve list), or
- Human Principal approval (if confidence ≤ 0.90 or the relationship type requires manual approval)

**Stage 3: Validation**

The Validator performs full validation checks. For newly created relationships, this occurs within the Factory sequence before Registry enrollment. For re-validation (periodic integrity checks), it occurs as a standalone Validation Service call.

If validation fails:
- The relationship is not created (if during Factory sequence)
- The relationship is flagged VALIDATION_FAILED and a governance alert is created (if during re-validation of an existing relationship)
- A `VALIDATION_FAILED` audit event is created

**Stage 4: Activation**

Activation transitions the relationship from CREATED to ACTIVE. An ACTIVE relationship:
- Appears in the adjacency index (visible to graph traversal)
- Is loaded into the relationship cache (L2 tier or higher)
- Is included in Search Engine results
- May be used by the Reasoning Manager
- May be used by the Influence Service

Not all relationship types have a distinct activation step. For automatically-created relationships (event-implied), CREATED and ACTIVE are reached in the same Factory call. For relationships requiring approval, the approval event triggers the transition to ACTIVE.

**Stage 5: Monitoring**

Monitoring is not a discrete state — it is the ongoing process of the Evolution Manager and Integrity Manager that runs throughout the relationship's ACTIVE life. During monitoring:
- Strength is updated when new evidence arrives
- Confidence is updated based on prediction accuracy
- Temporal decay is applied to probabilistic relationships
- Integrity checks verify the relationship remains valid

If monitoring detects that strength has fallen below the minimum threshold (0.05) or confidence has fallen below the minimum threshold (0.30), the relationship enters the Weakening stage.

**Stage 6: Evolution**

Evolution is the stage during which a relationship is being actively updated based on new evidence. A relationship that enters the Evolution stage has its strength and/or confidence significantly updated by the Evolution Manager.

Evolution events are versioned — every significant evolution update creates a new version record with the reason for the evolution (e.g., `CONFIDENCE_UPDATED: closed 15 trades, 10 confirmed relationship direction`).

**Stage 7: Strengthening**

Strengthening is a specific evolution direction — the relationship's strength and/or confidence is increasing based on accumulating confirming evidence. Strengthening occurs when:
- Correlation coefficient increases in magnitude
- More trade outcomes confirm the causal hypothesis
- More regime observations confirm the sensitivity claim
- Agent opinions consistently align with the relationship direction

A relationship in the Strengthening stage may have its classification upgraded (e.g., from HYPOTHETICALLY_CAUSED_BY to CAUSED_BY) when confidence crosses the causal threshold (0.85).

**Stage 8: Weakening**

Weakening is the opposite evolution direction — the relationship's strength and/or confidence is decreasing. Weakening occurs when:
- Contradicting evidence accumulates
- The correlation coefficient moves toward zero
- Trade outcomes contradict the causal hypothesis
- Temporal decay is not offset by new confirming evidence

A relationship in the Weakening stage is placed on the deprecation watch list. If it continues to weaken toward the deprecation threshold, it enters the Deprecation stage.

**Stage 9: Versioning**

Versioning is a parallel process, not a lifecycle state. Every update to a relationship — every strength change, every confidence change, every metadata update — creates a new version record. The Version Manager handles this transparently.

Versioning is the mechanism that makes relationship evolution traceable: at any time, the history of a relationship's strength and confidence can be retrieved as a time series.

**Stage 10: Deprecation**

Deprecation is the formal notice that a relationship is approaching retirement. A deprecated relationship is still ACTIVE — it appears in the graph and may be traversed — but it is flagged to consumers and the Governance Manager.

Deprecation triggers:
- Confidence below 0.30 for 7 consecutive days
- Source or target entity deprecated
- Human Principal deprecation instruction
- Superseded by a higher-quality relationship of the same type

A deprecated relationship includes:
- `deprecated_at` timestamp
- `deprecation_reason` (CONFIDENCE_DECAY, ENTITY_DEPRECATED, SUPERSEDED, MANUAL)
- `successor_relationship_id` (where applicable)

**Stage 11: Archiving**

Archival transitions a relationship from ACTIVE or DEPRECATED to ARCHIVED. An archived relationship:
- Is removed from the adjacency index (no longer visible to graph traversal)
- Is evicted from the active cache
- Is excluded from Search results by default (unless `include_archived=True`)
- Is preserved permanently for audit and historical analysis

Archival triggers:
- Parent entity archived (cascade)
- Relationship manually archived (Human Principal instruction)
- Scheduled archival after the archival policy window

**Stage 12: Retirement**

Retirement is the final lifecycle stage — permanent, irreversible. A retired relationship is preserved for audit but has no operational role.

Retirement differs from archival in the same way as for entities: archive = temporarily inactive, retire = permanently done.

---

### 4.3 Relationship Lifecycle State Machine

```
                    RELATIONSHIP LIFECYCLE STATE MACHINE

                ┌─────────────────────────┐
                │  DISCOVERY CANDIDATE    │ ─── Proposed by Discovery Manager
                └──────────┬──────────────┘
                           │ Approved / Auto-approved
                ┌──────────▼──────────────┐
                │      CREATED            │ ─── Factory creation complete
                └──────────┬──────────────┘
                           │ Validation passes
          ┌────────────────┤
          │                │ Activated
          ▼                ▼
VALIDATION           ┌─────────────────────┐
FAILED               │      ACTIVE         │◄──────────────────┐
                     └───────────┬──┬───────┘                  │
                                 │  │                          │
              ┌──────────────────┘  └────────────────────┐     │
              ▼                                          ▼     │
         WEAKENING                               STRENGTHENING │
              │                                          │     │
              │  (confidence < 0.30 for 7 days)          │     │
              ▼                                          └──►  │
         DEPRECATED                                      ACTIVE│
              │                                               │
              ▼
         ARCHIVED ◄────── cascade (entity archived)
              │
              │ Restore (Human Principal)
              └────────────────────────────────────────────────┘
              │
              ▼
         RETIRED (terminal — irreversible)
```

---

### 4.4 Lifecycle State Definitions

| State | Description | Graph visibility | Cache tier |
|---|---|---|---|
| `DISCOVERY_CANDIDATE` | Proposed but not yet created | None | None |
| `VALIDATION_FAILED` | Failed validation | None | None |
| `CREATED` | Created, awaiting activation | None | None |
| `ACTIVE` | Fully operational | Full | L1/L2 |
| `WEAKENING` | Confidence/strength declining | Full | L2 |
| `STRENGTHENING` | Confidence/strength increasing | Full | L2 |
| `DEPRECATED` | Scheduled for archival | Full (flagged) | L2 |
| `ARCHIVED` | Inactive; historical access only | None | L4 only |
| `RETIRED` | Permanently inactive | None | Historical only |

---

### 4.5 Lifecycle Transitions Table

| From | To | Trigger | Preconditions |
|---|---|---|---|
| DISCOVERY_CANDIDATE | CREATED | Approval or auto-approval | Validation passes; cardinality satisfied |
| DISCOVERY_CANDIDATE | VALIDATION_FAILED | Validation fails | — |
| CREATED | ACTIVE | Activation (auto or manual) | Entity preconditions satisfied |
| ACTIVE | WEAKENING | Evidence contradicts; confidence decays | confidence < 0.50 for 3 days |
| ACTIVE | STRENGTHENING | Confirming evidence accumulates | confidence > 0.80 and strength increasing |
| ACTIVE | DEPRECATED | Deprecation trigger | Deprecation reason recorded |
| WEAKENING | DEPRECATED | Confidence below threshold | confidence < 0.30 for 7 days |
| WEAKENING | ACTIVE | Evidence improves | confidence >= 0.50 again |
| STRENGTHENING | ACTIVE | Evidence stabilises | Normal monitoring resumes |
| DEPRECATED | ARCHIVED | Archival trigger | No blocking dependencies |
| ARCHIVED | ACTIVE | Restore operation | Human Principal approval |
| ACTIVE | RETIRED | Retirement | Human Principal approval + auth token |
| DEPRECATED | RETIRED | Retirement | Human Principal approval + auth token |
| ARCHIVED | RETIRED | Retirement | Human Principal approval + auth token |

---

### 4.6 Relationship Lifecycle Diagrams by Category

**Financial Relationship Lifecycle (Strategy GENERATES Hypothesis):**

```
Strategy entity enters decision cycle
         │ (event-implied creation)
         ▼
Factory creates GENERATES relationship (CREATED → ACTIVE in single call)
         │
         ▼
ACTIVE: Hypothesis evaluated by agents
         │ Hypothesis APPROVED → Order submitted
         ▼
Trade closed → learning extracted
         │ LearningRecord created
         ▼
Evolution Manager: GENERATES relationship confidence updated
   Trade profitable? → strength slight increase
   Trade at loss? → strength slight decrease
         │ (exponential moving average update)
         ▼
ACTIVE continues monitoring...
         │ Strategy retired (Human Principal instruction)
         ▼
Cascade: GENERATES relationship → DEPRECATED → ARCHIVED
```

**Derived Relationship Lifecycle (CORRELATED_WITH):**

```
Discovery Manager analyses 30 days of price data
         │ Pearson coefficient = -0.72 (VIX vs NIFTY50)
         ▼
Discovery Candidate: VIX CORRELATED_WITH NIFTY50
(confidence = 0.88 based on sample size and coefficient magnitude)
         │ Auto-approve (confidence > 0.90 threshold not met → WARN)
         ▼
Human Principal approves (or auto-approves if > 0.90)
         │
         ▼
Factory creates relationship (CREATED → ACTIVE)
         │
         ▼
ACTIVE: Used by Influence Service in regime change analysis
         │
         ▼
Daily Evolution: Pearson coefficient recomputed on rolling 30d window
   Coefficient strengthens? → STRENGTHENING
   Coefficient weakens to -0.30? → WEAKENING
         │ Continues to decay → confidence falls
         ▼
DEPRECATED: Correlation no longer reliable
         ▼
ARCHIVED: Preserved for historical analysis
```

---

### 4.7 Lifecycle Event Publishing

Every relationship lifecycle transition publishes an event to the IIOS EventBus:

| Event | When published | Consumers |
|---|---|---|
| `relationship.created` | ACTIVE state reached | Reasoning Manager, Dashboard, Knowledge Engine |
| `relationship.strengthened` | Strength threshold crossed upward | Strategy selection, Knowledge Engine |
| `relationship.weakened` | Strength threshold crossed downward | Strategy selection, Governance |
| `relationship.deprecated` | Deprecated | All consumers of this relationship |
| `relationship.archived` | Archived | Learning System, Dashboard |
| `relationship.retired` | Retired | Dashboard, Audit |
| `relationship.restored` | Restored from archive | All components |
| `relationship.integrity_violation` | Integrity check finds violation | Governance Manager, Human Principal |

---
## PART V — RELATIONSHIP SERVICES

### 5.1 Service Architecture Overview

Relationship Services are the external interface through which all other IIOS components interact with the Relationship Engine. No component accesses relationship data directly — all relationship interactions go through one of the fifteen Relationship Services.

```
RELATIONSHIP SERVICE CONSUMER MAP

Consumer Component          Service                     Engine Component
──────────────────    ─────────────────────────    ──────────────────────────
OrderManager       ──► Registration Service    ──►  Factory + Registry + Validator
All systems        ──► Validation Service      ──►  Validator + Catalog
All layers         ──► Search Service          ──►  Search Engine + Index
All layers         ──► Traversal Service       ──►  Index + Cache + Adjacency
Reasoning layer    ──► Reasoning Service       ──►  Reasoning Manager
All layers         ──► Influence Service       ──►  Reasoning Manager + Index
All layers         ──► Dependency Service      ──►  Index + Reasoning Manager
All layers         ──► Similarity Service      ──►  Discovery + Reasoning Manager
Discovery cycle    ──► Discovery Service       ──►  Discovery Manager + Factory
Integrity system   ──► Merge Service           ──►  Identity + Lifecycle Managers
Admin              ──► Split Service           ──►  Lifecycle + Factory
All writers        ──► Version Service         ──►  Version Manager
Audit system       ──► Audit Service           ──►  Audit Manager
Governance         ──► Governance Service      ──►  Governance Manager
Integrity cycle    ──► Integrity Service       ──►  Integrity Manager
```

---

### 5.2 Relationship Registration Service

**Purpose:** The Registration Service is the entry point for all new relationship creation. It is the only authorised path for creating relationships in the IIOS.

**Service specification:**

| Attribute | Detail |
|---|---|
| **Purpose** | Create and register a new relationship between two specified entities |
| **Operation** | WRITE — creates persistent records |
| **Idempotency** | Idempotent when called with an idempotency_key |
| **Transactional** | Fully atomic — complete creation or full rollback |
| **Authorization** | All callers; approval-required types require auth_token |

**Inputs:**

| Input | Type | Required | Description |
|---|---|---|---|
| `source_entity_id` | UUID4 | Yes | Source entity of the relationship |
| `target_entity_id` | UUID4 | Yes | Target entity of the relationship |
| `relationship_type` | RelationshipType enum | Yes | The relationship type to create |
| `strength` | float [0.0–1.0] | Conditional | Required for typed relationships |
| `confidence` | float [0.0–1.0] | Yes | Minimum confidence for creation |
| `evidence` | EvidenceRecord | Conditional | Required for non-binary relationships |
| `valid_from` | datetime | No | Start of validity window (default: now) |
| `valid_until` | datetime | No | End of validity window (null = indefinite) |
| `owner_id` | string | Yes | Responsible owner |
| `idempotency_key` | string | No | Prevents duplicate creation |
| `metadata` | dict | No | Additional type-specific context |
| `auth_token` | string | Conditional | Required for approval-required types |

**Outputs:**

| Output | Type | Description |
|---|---|---|
| `relationship` | RelationshipRecord | The fully created relationship |
| `relationship_id` | UUID4 | Permanent identifier |
| `was_idempotent` | bool | True if existing relationship returned |
| `validation_errors` | List[str] | Populated only on failure |

**Dependencies:** Relationship Factory, Validator, Registry, Catalog, Audit Manager
**Consumers:** OrderManager (order chains), StrategyLab (strategy-hypothesis chains), TradeMonitor (trade chains), Learning System (learning chains), Discovery Manager (after approval)

**Failure handling:**

| Failure | Response |
|---|---|
| ValidationError | Return error list; no relationship created |
| CardinalityViolation | Return CardinalityError with existing relationship_id |
| DuplicateRelationship | Return existing or raise DuplicateError |
| EntityNotFound | Return EntityNotFoundError with missing entity_id |
| EntityNotActive | Return EntityNotActiveError |
| RegistryWriteFailure | Raise RegistryWriteError; full rollback |

---

### 5.3 Relationship Validation Service

**Purpose:** The Validation Service provides standalone relationship validation — for pre-flight checks before update, for re-validation of existing relationships, and for integrity audits.

| Attribute | Detail |
|---|---|
| **Purpose** | Validate relationship data against all defined constraints |
| **Operation** | READ — no relationships modified |

**Inputs:**

| Input | Type | Required | Description |
|---|---|---|---|
| `relationship_id` | UUID4 | No | Re-validate an existing relationship |
| `relationship_type` | RelationshipType | Conditional | Required when relationship_id not provided |
| `data` | dict | Yes | Relationship data or update parameters to validate |
| `validation_level` | ValidationLevel | No | STRUCTURAL, REFERENTIAL, BUSINESS (default: ALL) |

**Outputs:**

| Output | Type | Description |
|---|---|---|
| `is_valid` | bool | True if all checks pass |
| `validation_results` | List[ValidationResult] | Detailed per-check results |
| `violated_rules` | List[str] | Rule IDs that were violated |
| `severity_breakdown` | dict | Count of ERROR, WARNING, INFO findings |

**Dependencies:** Relationship Validator, Relationship Catalog, Entity Registry
**Consumers:** All components that create or update relationships; scheduled integrity checks

**Failure handling:** Service errors (connectivity, timeout) are raised as `ValidationServiceError` and retried with exponential backoff. Validation failures are never raised as service errors — they are returned as structured results.

---

### 5.4 Relationship Search Service

**Purpose:** The Search Service provides flexible discovery of relationships based on arbitrary criteria. Designed for analytical and governance use, not cycle-time hot paths.

**Inputs:**

| Input | Type | Required | Description |
|---|---|---|---|
| `query` | RelationshipSearchQuery | Yes | Criteria, filters, ordering |
| `relationship_types` | List[RelationshipType] | No | Restrict to specific types |
| `source_entity_types` | List[EntityType] | No | Restrict by source entity type |
| `target_entity_types` | List[EntityType] | No | Restrict by target entity type |
| `min_strength` | float | No | Minimum strength threshold |
| `min_confidence` | float | No | Minimum confidence threshold |
| `include_archived` | bool | No | Include archived relationships |
| `limit` | int | No | Max results (default 100) |
| `offset` | int | No | Pagination offset |

**Outputs:**

| Output | Type | Description |
|---|---|---|
| `results` | List[RelationshipSummary] | Matching relationships |
| `total_count` | int | Total before limit/offset |
| `query_time_ms` | float | Execution time |

**Dependencies:** Relationship Search Engine, Relationship Index
**Consumers:** Dashboard, Telegram bot relationship queries, Knowledge Engine, ResearchLab

**Failure handling:** Timeouts return partial results with `truncated = True`. No failure in Search blocks operational decisions.

---

### 5.5 Relationship Traversal Service

**Purpose:** The Traversal Service provides graph traversal capabilities — starting from a given entity and following relationships to reach connected entities, with support for multi-hop traversal, type filtering, and direction control.

**Traversal operations:**

| Operation | Description | Max hops | Time limit |
|---|---|---|---|
| `get_neighbors(entity_id, types, direction)` | Direct neighbours (1 hop) | 1 | < 5 ms |
| `traverse(entity_id, types, direction, max_hops)` | Multi-hop traversal | Configurable (max 10) | < 50 ms |
| `find_path(source_id, target_id, types)` | Shortest path between two entities | Auto | < 100 ms |
| `get_subgraph(entity_id, radius)` | Full subgraph within radius hops | Configurable | < 200 ms |
| `find_all_paths(source_id, target_id, max_hops)` | All paths within max_hops | Configurable | < 500 ms |
| `get_descendants(entity_id, type)` | All entities reachable following a type | Auto | < 100 ms |
| `get_ancestors(entity_id, type)` | All entities that reach this entity via a type | Auto | < 100 ms |

**Inputs:**

| Input | Type | Required | Description |
|---|---|---|---|
| `start_entity_id` | UUID4 | Yes | Starting node |
| `target_entity_id` | UUID4 | Conditional | Required for path-finding |
| `relationship_types` | List[RelationshipType] | No | Restrict traversal to these types |
| `direction` | TraversalDirection | No | OUTGOING, INCOMING, BOTH |
| `max_hops` | int | No | Maximum traversal depth (default 3) |
| `min_strength` | float | No | Prune edges below this strength |
| `min_confidence` | float | No | Prune edges below this confidence |
| `include_entity_data` | bool | No | Return full entity records at each node |

**Outputs:**

| Output | Type | Description |
|---|---|---|
| `traversal_result` | TraversalResult | Nodes and edges visited |
| `path` | List[entity_id] | For path-finding operations |
| `total_nodes` | int | Count of nodes in result |
| `total_edges` | int | Count of edges in result |
| `traversal_time_ms` | float | Execution time |

**Dependencies:** Relationship Cache, Relationship Index, Entity Engine Query Service
**Consumers:** Reasoning Manager, Knowledge Engine, ControlTower dashboard, Telegram bot graph queries

**Failure handling:** Traversal loops are detected and broken (visited-node tracking). Traversal that exceeds max_hops returns the partial result. Traversal timeout returns partial result with `truncated = True`.

---

### 5.6 Relationship Reasoning Service

**Purpose:** The Reasoning Service exposes the Reasoning Manager's analytical intelligence capabilities to external consumers — causal chain reconstruction, pattern detection, and transitivity inference.

**Reasoning operations:**

| Operation | Description | Latency |
|---|---|---|
| `reconstruct_causal_chain(outcome_entity_id)` | Trace the causal chain leading to this outcome | < 2 seconds |
| `find_pattern(pattern_definition)` | Find entities and relationships matching a graph pattern | < 1 second |
| `infer_transitive(entity_id, rel_type, max_hops)` | Infer indirect relationships via transitivity | < 500 ms |
| `detect_contradictions(entity_id)` | Find relationship pairs that contradict each other | < 500 ms |
| `rank_paths(source_id, target_id)` | Rank all paths by evidence strength | < 1 second |
| `find_analogues(entity_id, entity_type)` | Find structurally similar entity-relationship patterns | < 2 seconds |

**Inputs:** Outcome entity ID, pattern definition, entity IDs, reasoning parameters
**Outputs:** CausalChain, PatternMatch, TransitivityInference, ContradictionList, RankedPaths
**Consumers:** LearningEngine (causal attribution), ResearchLab (pattern analysis), Human Principal (investigation)
**Dependencies:** Reasoning Manager, Traversal Service, Entity Engine Query Service

**Failure handling:** Reasoning operations are best-effort and time-bounded. Timeouts return the best partial result available. Reasoning failures never block operational cycle execution.

---

### 5.7 Relationship Influence Service

**Purpose:** The Influence Service quantifies how changes propagate through the influence graph — which entities are affected when a specific entity changes, and with what effective strength.

**Influence operations:**

| Operation | Description |
|---|---|
| `compute_influence(source_id, max_hops, min_strength)` | Compute influence map from source entity |
| `find_influencers(target_id, min_strength)` | Find all entities that influence a target |
| `estimate_impact(entity_id, change_magnitude)` | Estimate impact of a change on all influenced entities |
| `rank_influencers(entity_type)` | Rank all entities by their total influence over a given target type |

**Influence propagation model:** See Section 3.16 (Reasoning Manager). Strength is multiplied across hops; propagation stops at max_hops or when effective strength < 0.05.

**Inputs:**

| Input | Type | Description |
|---|---|---|
| `source_entity_id` | UUID4 | Starting entity for propagation |
| `max_hops` | int | Maximum propagation depth (default 3) |
| `min_effective_strength` | float | Prune when effective strength below this |
| `relationship_types` | List[RelationshipType] | Restrict to influence-type relationships |
| `change_magnitude` | float | For impact estimation: magnitude of change |

**Outputs:** InfluenceMap (entity_id → effective_strength), InfluencerRanking, ImpactEstimate
**Consumers:** RiskGuardian (VIX influence on portfolio), MetaLearning (regime influence on strategies), MarketIntelligence

**Failure handling:** Influence computation failures return an empty map with a `computation_failed` flag. This never blocks cycle execution — influence analysis is advisory.

---

### 5.8 Relationship Dependency Service

**Purpose:** The Dependency Service manages and queries dependency relationships — determining what depends on what, and using dependencies to make safe decisions about entity lifecycle operations.

**Dependency operations:**

| Operation | Description |
|---|---|
| `get_dependencies(entity_id)` | Find all entities this entity depends on |
| `get_dependents(entity_id)` | Find all entities that depend on this entity |
| `check_safe_archive(entity_id)` | Verify that archiving this entity will not break dependents |
| `compute_dependency_chain(entity_id)` | Compute the full transitive dependency chain |
| `find_circular_dependencies(entity_type)` | Detect circular dependency loops |
| `get_critical_path(entity_id)` | Find the chain of dependencies most critical to this entity |

**Safe archive check:** Before any entity is archived, the Lifecycle Manager (Entity Engine) calls `check_safe_archive()`. If any ACTIVE entities have a DEPENDS_ON or REQUIRES relationship to the entity being archived, the archive is blocked until those relationships are resolved.

**Inputs:** entity_id, dependency relationship types to include
**Outputs:** DependencyList, DependentList, SafeArchiveResult, CircularDependencyList
**Consumers:** Entity Lifecycle Manager (safe archive check), Integrity Manager (circular dependency detection)

**Failure handling:** If the dependency graph cannot be computed (index unavailability), the safe archive check defaults to UNSAFE (blocking the archive) until the dependency graph is restored.

---

### 5.9 Relationship Similarity Service

**Purpose:** The Similarity Service computes and queries similarity relationships between entities — particularly between strategies, between knowledge records, and between market regimes.

**Similarity operations:**

| Operation | Description |
|---|---|
| `find_similar(entity_id, entity_type, threshold)` | Find entities similar to the given entity |
| `compute_similarity(entity_id_a, entity_id_b)` | Compute pairwise similarity score |
| `get_similarity_cluster(entity_id)` | Return the similarity cluster this entity belongs to |
| `rank_by_similarity(entity_id, entity_type)` | Rank all entities of a type by similarity to given entity |

**Similarity basis by entity type:**

| Entity type | Similarity basis | Metric |
|---|---|---|
| Strategy | Parameter vector | Cosine similarity |
| KnowledgeRecord | Semantic content embedding | Cosine similarity |
| Regime | Indicator value vector | Euclidean distance normalised |
| Agent | Opinion pattern vector | Pearson correlation |
| Symbol | Price return correlation | Pearson correlation |
| BacktestResult | Performance metric vector | Euclidean distance normalised |

**Inputs:** entity_id, entity_type, threshold, metric specification
**Outputs:** SimilarityResult (entity_id, similarity_score, relationship_id if managed)
**Consumers:** StrategyLab (find similar strategies for ensemble), ResearchLab (strategy clustering), MetaLearning (regime similarity for regime-fitting)

**Failure handling:** Similarity computation failures return an empty result with a warning. No failure blocks operational decisions.

---

### 5.10 Relationship Discovery Service

**Purpose:** The Discovery Service exposes the Discovery Manager's capabilities for external callers — triggering discovery runs, querying discovery candidates, and approving or rejecting discovered relationships.

**Discovery operations:**

| Operation | Description |
|---|---|
| `run_discovery(discovery_type, entity_type)` | Trigger a discovery run for a specific type |
| `get_candidates(status, confidence_min)` | Retrieve pending discovery candidates |
| `approve_candidate(candidate_id, approver)` | Approve a candidate → triggers Registration Service |
| `reject_candidate(candidate_id, reason)` | Reject a candidate with a rejection reason |
| `get_discovery_history(entity_id)` | Retrieve all past discovery candidates involving this entity |
| `configure_auto_approve(discovery_type, confidence_threshold)` | Configure automatic approval thresholds |

**Inputs:** Discovery type, entity types, confidence threshold, approver
**Outputs:** DiscoveredRelationshipCandidate, CandidateList, ApprovalResult
**Consumers:** Human Principal (approval workflow), MasterOrchestrator (scheduled discovery triggers), Governance Manager

**Failure handling:** Discovery run failures are retried in the next scheduled window. Candidates that fail approval (after 3 rejected attempts for the same entity pair and type) are permanently rejected and archived.

---

### 5.11 Relationship Merge Service

**Purpose:** The Merge Service combines two relationships that represent the same connection into a single canonical relationship.

| Attribute | Detail |
|---|---|
| **Purpose** | Resolve relationship duplicates by merging into one canonical relationship |
| **Operation** | WRITE — modifies both relationships and updates all references |
| **Authorization** | Requires Human Principal approval |
| **Transactional** | Fully atomic |

**Inputs:**

| Input | Type | Required | Description |
|---|---|---|---|
| `primary_relationship_id` | UUID4 | Yes | Survives the merge |
| `secondary_relationship_id` | UUID4 | Yes | Absorbed by the merge |
| `merge_strategy` | MergeStrategy | Yes | How to reconcile strength/confidence differences |
| `merge_reason` | string | Yes | Human-readable reason |
| `auth_token` | string | Yes | Always required |

**Merge strategy options:**

| Strategy | Behaviour |
|---|---|
| `PREFER_PRIMARY` | Primary's strength and confidence win |
| `PREFER_SECONDARY` | Secondary's values win |
| `MAX_VALUES` | Take the higher of each numeric field |
| `WEIGHTED_AVERAGE` | Weight by evidence count |

**Outputs:** MergedRelationshipRecord, references_updated count, merge_id
**Consumers:** Identity Manager (post-duplicate-detection), Human Principal
**Failure handling:** Any failure triggers full rollback. The primary relationship remains ACTIVE if merge fails.

---

### 5.12 Relationship Split Service

**Purpose:** The Split Service divides one relationship into two separate relationships when it is discovered that a single relationship record was representing two distinct connections.

| Attribute | Detail |
|---|---|
| **Purpose** | Divide one relationship into two distinct relationship records |
| **Authorization** | Always requires Human Principal approval |
| **Transactional** | Fully atomic |

**Inputs:** source_relationship_id, split_definition_a, split_definition_b, auth_token, split_reason
**Outputs:** RelationshipRecord (A), RelationshipRecord (B), original status (SPLIT)
**Consumers:** Human Principal only
**Failure handling:** Any failure leaves source relationship ACTIVE and does not create successors. Full rollback guaranteed.

---

### 5.13 Relationship Version Service

**Purpose:** The Version Service provides structured access to relationship versioning — querying historical versions, computing diffs, and creating explicit milestone versions.

**Version operations:**

| Operation | Description |
|---|---|
| `get_version(relationship_id, version_number)` | Retrieve a specific version |
| `get_current_version(relationship_id)` | Current (latest) version |
| `list_versions(relationship_id)` | All version summaries |
| `diff_versions(relationship_id, v1, v2)` | Field-level diff between versions |
| `get_strength_history(relationship_id, date_range)` | Time series of strength values |
| `get_confidence_history(relationship_id, date_range)` | Time series of confidence values |
| `create_milestone(relationship_id, label, reason)` | Create a named milestone version |

**Inputs:** relationship_id, version numbers, date ranges
**Outputs:** VersionRecord, VersionDiff, TimeSeriesData, MilestoneRecord
**Consumers:** LearningSystem (evolution analysis), ResearchLab (relationship analytics), Human Principal
**Failure handling:** Version read failures fall back to partial history. Version creation failures are retried 3 times.

---

### 5.14 Relationship Audit Service

**Purpose:** The Audit Service provides access to the relationship audit log for querying, compliance reporting, and integrity verification.

**Audit operations:**

| Operation | Description |
|---|---|
| `get_audit_log(relationship_id)` | All audit events for a relationship |
| `get_events_by_type(event_type, date_range)` | All events of a specific type |
| `get_events_by_actor(actor_id, date_range)` | All events by a specific actor |
| `generate_compliance_report(category, date_range)` | Compliance-formatted audit report |
| `verify_chain_integrity(relationship_id)` | Verify audit hash chain integrity |
| `get_daily_summary(date)` | Summary count by event type |

**Inputs:** relationship_id, event type, actor, date range
**Outputs:** AuditLog, ComplianceReport, IntegrityVerificationResult
**Consumers:** Human Principal, ControlTower dashboard, compliance reporting
**Failure handling:** Always served from persistence layer. Integrity failures raise `AuditIntegrityError`.

---

### 5.15 Relationship Governance Service

**Purpose:** The Governance Service enforces ownership, applies policies, monitors compliance, and generates governance reports for the relationship population.

**Governance operations:**

| Operation | Description |
|---|---|
| `get_owner(relationship_id)` | Return current owner |
| `transfer_ownership(relationship_id, new_owner, reason)` | Transfer ownership |
| `get_governance_status(relationship_id)` | Full governance health |
| `enforce_policies(relationship_type)` | Apply policies and report violations |
| `generate_governance_report(date_range)` | Governance health report |
| `flag_relationship(relationship_id, reason, severity)` | Flag for governance review |

**Inputs:** relationship_id, owner, date ranges, severity
**Outputs:** GovernanceStatus, GovernanceReport, policy violation records
**Consumers:** Human Principal, ControlTower dashboard, scheduled governance checks
**Failure handling:** Policy enforcement failures are recorded as governance events. CRITICAL violations trigger immediate Telegram notifications.

---

### 5.16 Relationship Integrity Service

**Purpose:** The Integrity Service provides on-demand and scheduled integrity checks across the relationship population, detecting violations and producing actionable reports.

**Integrity operations:**

| Operation | Description |
|---|---|
| `run_hot_check()` | Check L1 + L2 relationships only (cycle-time) |
| `run_operational_check()` | Check all ACTIVE relationships (daily) |
| `run_full_scan()` | Check full population (weekly) |
| `check_entity_relationships(entity_id)` | Check all relationships for a specific entity |
| `detect_cycles(relationship_type)` | Detect cyclic chains of a specified type |
| `generate_integrity_report()` | Full integrity report with violation counts |

**Inputs:** Trigger type, entity_id (for targeted checks), relationship_type (for cycle detection)
**Outputs:** IntegrityReport (violations, severity, affected IDs, recommended actions)
**Consumers:** Governance Manager, MasterOrchestrator (scheduled triggers), Human Principal
**Failure handling:** Integrity scan failures are retried. CRITICAL violations discovered during operational checks trigger immediate governance alerts.

---
## PART VI — RELATIONSHIP GRAPH ARCHITECTURE

### 6.1 Graph Architecture Overview

The Relationship Engine is fundamentally a graph system. The entities of the IIOS are nodes, and the relationships are edges. The graph is the first-class data structure — not a secondary view derived from relational tables, but the primary representation of the system's understanding of the world.

The IIOS relationship graph has several key architectural properties that shape its design:

| Property | Value | Rationale |
|---|---|---|
| **Directed** | Primarily directed | Most relationships have a source and target; directionality is semantically meaningful |
| **Weighted** | Yes | Every edge has a strength weight (0.0–1.0) |
| **Probabilistic** | Yes | Every edge has a confidence score (0.0–1.0) |
| **Temporal** | Yes | Edges have validity windows (valid_from, valid_until) |
| **Multi-edge** | Yes | Multiple edges of different types may connect the same two nodes |
| **Heterogeneous** | Yes | Nodes are of different entity types; edges are of different relationship types |
| **Dynamic** | Yes | The graph changes continuously as relationships are created, evolved, and retired |
| **Persistent** | Yes | The complete graph history is preserved |

---

### 6.2 Node Model

In the IIOS relationship graph, every node corresponds to an entity managed by the Entity Engine. Nodes are not independently managed by the Relationship Engine — the Entity Engine is the authoritative record of all nodes.

The Relationship Engine maintains a **node shadow record** for each entity that has at least one relationship. This shadow record contains:

| Field | Description |
|---|---|
| `entity_id` | The canonical entity identifier (from Entity Engine) |
| `entity_type` | The entity type |
| `entity_category` | The entity category |
| `node_degree` | Total number of relationships (in + out) |
| `in_degree` | Number of incoming relationships |
| `out_degree` | Number of outgoing relationships |
| `relationship_type_count` | Dict of relationship_type → count |
| `active_since` | When this node first had a relationship |
| `last_active` | When the last relationship was created or updated |
| `centrality_score` | Computed graph centrality score |

**Node centrality:** The Relationship Engine computes graph centrality scores for all nodes using the degree centrality metric (normalized degree). Highly central nodes — entities with many relationships — are flagged for special monitoring, as they represent high-leverage points in the graph. A failure or degradation in a high-centrality entity (e.g., a Portfolio entity or a heavily-used Strategy) has wide-reaching graph effects.

**Node isolation detection:** The Integrity Manager detects isolated nodes — entities that have no relationships. An isolated entity is either:
- A reference entity that has not yet been connected (acceptable for new reference data)
- An entity whose relationships have been incorrectly archived (a governance violation)
The Integrity Manager reports isolated nodes as part of the weekly full scan.

---

### 6.3 Edge Model

Every edge in the IIOS relationship graph corresponds to a relationship record. The edge model captures the full semantics of the relationship:

| Field | Graph role | Description |
|---|---|---|
| `relationship_id` | Edge identifier | UUID4 — permanent edge identity |
| `relationship_type` | Edge label | The semantic type of the connection |
| `source_entity_id` | Source node | Starting entity |
| `target_entity_id` | Target node | Ending entity |
| `strength` | Edge weight | Primary traversal weight |
| `confidence` | Secondary weight | Certainty of the edge's existence |
| `direction` | Edge direction | DIRECTED / UNDIRECTED / BIDIRECTIONAL |
| `valid_from` | Temporal attribute | When this edge became active |
| `valid_until` | Temporal attribute | When this edge expires (null = indefinite) |
| `status` | Traversal filter | Only ACTIVE edges included in standard traversal |

**Effective edge weight:** The Traversal Service computes an effective edge weight for each edge used in path-finding and influence propagation:

$$\text{effective\_weight} = \text{strength} \times \text{confidence}$$

This penalises edges that are strong but uncertain, ensuring that well-evidenced relationships are preferred over uncertain ones in path scoring.

---

### 6.4 Edge Types

**Directed Edges:** The source entity has a relationship to the target entity, but the reverse is not implied. Example: Strategy `GENERATES` Hypothesis — the strategy generates the hypothesis, but the hypothesis does not generate the strategy.

For directed edges, traversal respects direction: following OUTGOING edges from Strategy reaches Hypothesis; following INCOMING edges from Hypothesis reaches Strategy.

**Undirected Edges:** The relationship is symmetric — if A has the relationship to B, then B has the same relationship to A. Example: Position `HEDGES` Position — if position A hedges position B, then position B also hedges position A by definition.

Undirected edges are stored as a single relationship record (not two directed records). The Traversal Service handles undirected edges by including them in both OUTGOING and INCOMING traversal directions.

**Bidirectional Edges:** There are two separate directed relationships between the same entities in both directions, each with its own strength and confidence. Example: MacroIndicator A `CORRELATED_WITH` MacroIndicator B (positive correlation), and MacroIndicator B `CORRELATED_WITH` MacroIndicator A — each may have different strengths in each direction if the correlation is asymmetric.

**Weighted Edges:** All edges in the IIOS graph are weighted (strength). The weight is used in path scoring, influence propagation, and traversal prioritization.

**Probabilistic Edges:** All edges carry a confidence score in addition to strength. The confidence score is used to filter edges below a minimum certainty threshold during traversal, and is used in the effective weight calculation.

---

### 6.5 Hierarchical Relationships

Hierarchical relationships form trees or DAGs (Directed Acyclic Graphs) in the relationship graph. The key hierarchical relationship types are:

| Type | Structure | Constraint |
|---|---|---|
| `COMPOSED_OF` | Tree (strict hierarchy) | No cycles; exactly one parent per node |
| `CONTAINS` | DAG | No cycles; multiple parents permitted |
| `INHERITS_FROM` | DAG (type hierarchy) | No cycles; multiple inheritance permitted |
| `DEPENDS_ON` | DAG | No cycles enforced by Integrity Manager |
| `PARENT_OF` | Tree | Used for corporate conglomerates |

**Hierarchical traversal:** The Traversal Service provides specialised hierarchical traversal that navigates up or down a hierarchical chain, returning the complete ancestry or descendancy at each level. This is used, for example, to find all positions in a portfolio (Portfolio `COMPOSED_OF` ... following the chain).

**Cycle detection:** The Integrity Manager runs daily cycle detection on all DAG-constrained relationship types. A cycle in a `DEPENDS_ON` chain is a CRITICAL integrity violation — it implies circular dependency.

---

### 6.6 Temporal Relationships

Temporal relationships in the IIOS graph have an explicit time dimension — they are valid only within a defined window.

**Temporal edge representation:**

```
TIME ──────────────────────────────────────────────────────────────────►

Entity A ──────────────────── [CONCURRENT_WITH] ──────────────────── Entity B
          valid_from: T1                                  valid_until: T2

Entity C ────────────── [PRECEDES] ──────────────────────────────────► Entity D
          happened_at: T3            effect_at: T3+lag
```

**Temporal query model:** The Traversal Service supports temporal graph queries — finding the relationship graph as it existed at a specific point in time. This enables:

- "What did the relationship graph look like at 09:30 on 2026-07-01?" → point-in-time graph snapshot
- "What relationships were active during the BEAR_VOLATILE regime period?" → temporal window query
- "Which strategies were active when this trade was executed?" → entity + temporal intersection

**Temporal validity enforcement:** The Relationship Engine automatically marks relationships as expired when their `valid_until` timestamp is reached. Expired relationships transition to ARCHIVED status and are removed from the active graph.

---

### 6.7 Multi-Hop Relationships

Multi-hop relationships are paths through the graph that connect two entities via intermediate entities. The Traversal Service computes and scores multi-hop paths.

**Multi-hop path scoring:**

For a path: A → B → C → D, the path score is:

$$\text{path\_score} = \prod_{i=1}^{n} \text{effective\_weight}(e_i)$$

Where $n$ is the number of edges in the path and $\text{effective\_weight}(e_i) = \text{strength}(e_i) \times \text{confidence}(e_i)$.

This multiplicative scoring naturally penalises longer paths (each additional hop reduces the score) and rewards high-quality edges (high strength × high confidence contributes more to the path score).

**Multi-hop path types:**

| Path type | Description | Use case |
|---|---|---|
| Shortest path | Minimum number of hops | Finding the most direct connection |
| Highest-scored path | Maximum product of effective weights | Finding the strongest evidence chain |
| All paths | All paths within max_hops | Full relationship chain analysis |
| Critical path | Path with highest minimum edge weight | Finding the weakest link in a chain |

---

### 6.8 Graph Traversal

The IIOS relationship graph supports four traversal algorithms, each optimised for specific intelligence tasks:

**Breadth-First Traversal (BFS):**

Used when the goal is finding the shortest path between two entities, or finding all entities within a specific hop count of a starting entity.

```
Start at entity A (hop 0)
    │
    ├──► All direct neighbours of A (hop 1)
    │         │
    │         ├──► All neighbours of each hop-1 entity (hop 2)
    │         │              │
    │         │              └──► Continue until target found or max_hops reached
```

**Depth-First Traversal (DFS):**

Used when exploring a full lineage chain — following a single COMPOSED_OF or DERIVED_FROM chain to its deepest level before backtracking.

**Weighted Traversal (Dijkstra-style):**

Used for finding the highest-scored path between two entities. Paths are scored by the product of effective edge weights, and the traversal always extends the highest-scored partial path next.

**Influence Propagation Traversal:**

A specialised traversal that follows INFLUENCES-type relationships, multiplying the effective strength at each hop to compute attenuated influence scores at each reached entity. This is the traversal algorithm used by the Influence Service.

---

### 6.9 Shortest Path Algorithm

The Traversal Service implements shortest path search using BFS for unweighted paths and a modified Dijkstra for weighted paths.

**Shortest path use cases in IIOS:**

| Use case | Source | Target | Edge types |
|---|---|---|---|
| "How is VIX connected to this strategy?" | VIX MacroIndicator | MomentumBreakoutV3 Strategy | Any influence-type edges |
| "What is the most direct evidence chain for this knowledge rule?" | KnowledgeRule | LearningRecord (evidence) | EVIDENCED_BY, DERIVED_FROM |
| "How did this economic event affect this trade?" | EconomicEvent | Trade | TRIGGERED_BY, CAUSED_BY, CONCURRENT_WITH, RESULTED_IN |
| "What connects these two strategies?" | Strategy A | Strategy B | SIMILAR_TO, OUTPERFORMS, CALIBRATED_BY, VALIDATED_BY |

**Shortest path output:**

```
Path found: VIX MacroIndicator → NIFTY50 Symbol → TATASTEEL Position → Portfolio
Via edges: CORRELATED_WITH (strength: 0.72) → CONTAINED_IN (strength: 1.0) → HELD_IN (strength: 1.0)
Path score: 0.72 × 1.0 × 1.0 = 0.72
Interpretation: VIX has 0.72-effective influence on the portfolio through the correlation with NIFTY50
```

---

### 6.10 Neighborhood Search

Neighborhood search finds all entities within a specified hop radius of a starting entity, returning them as a subgraph.

**Neighborhood search use cases:**

| Use case | Radius | Description |
|---|---|---|
| Entity context lookup | 1 hop | What directly connects to this strategy? |
| Risk concentration analysis | 2 hops | What does this position's risk propagate to? |
| Knowledge provenance | 3 hops | What evidence supports this knowledge record? |
| Agent impact assessment | 2 hops | Which strategies and trades has this agent influenced? |

**Neighborhood search output:** A `SubgraphResult` containing all nodes within the radius, all edges between them, and a boundary node list (nodes reached but not further expanded because radius was exceeded).

---

### 6.11 Influence Propagation Diagram

```
INFLUENCE PROPAGATION EXAMPLE

Scenario: VIX spike to 38 (above threshold 30)

VIX (MacroIndicator)  strength: 1.0 (direct trigger)
    │
    │ INFLUENCES (strength: 0.85, confidence: 0.91)
    ▼
NIFTY50 (Index)  effective: 0.85 × 0.91 = 0.77
    │
    │ INFLUENCES (strength: 0.60, confidence: 0.85)
    ▼
TATASTEEL (Symbol)  effective: 0.77 × 0.60 × 0.85 = 0.39
    │
    │ CONSTRAINED_BY (strength: 1.0, confidence: 1.0)
    ▼
RiskThreshold:VIX-35  effective: triggers kill-switch evaluation
    │
    │ TRIGGERS (strength: 1.0)
    ▼
KillSwitch evaluation ── VIX 38 > threshold 35 ──► TRIGGERED

Parallel path:
VIX (MacroIndicator)
    │ CHARACTERISES (strength: 0.90)
    ▼
Regime:BEAR_VOLATILE  effective: 0.90 × 0.91 = 0.82
    │ SENSITIVE_TO (strength: 0.75, confidence: 0.88)
    ▼
MomentumBreakoutV3 (Strategy)  effective: 0.82 × 0.75 × 0.88 = 0.54
    ── strategy performance expected to degrade by proportional factor
```

---

### 6.12 Relationship Clustering

Relationship clustering groups entities into clusters based on their relationship patterns. The Discovery Manager performs clustering as part of the weekly discovery cycle.

**Clustering algorithms:**

| Algorithm | Relationship basis | Use case |
|---|---|---|
| Community detection | All relationship types | Find communities of strongly inter-related entities |
| Similarity clustering | SIMILAR_TO relationships | Group similar strategies for ensemble analysis |
| Regime clustering | SENSITIVE_TO relationships | Find strategies with similar regime sensitivity profiles |
| Correlation clustering | CORRELATED_WITH relationships | Group highly correlated symbols (concentration risk) |

**Clustering output:** A `ClusterMap` mapping `cluster_id → List[entity_id]`, with cluster quality metrics (intra-cluster density, inter-cluster separation).

**Clustering governance:** Clusters are not persisted as permanent relationship records — they are analytical outputs. However, when a cluster is used to drive a decision (e.g., "we won't open more than N positions in this correlation cluster"), the cluster analysis result is recorded as a `DerivedRelationshipCandidate` for potential promotion to a managed `CORRELATED_CLUSTER_MEMBER` relationship.

---

### 6.13 Subgraph Extraction

Subgraph extraction retrieves a coherent portion of the full graph — centred on a specific entity or spanning a specified entity set — for analysis, visualisation, or export.

**Subgraph extraction modes:**

| Mode | Description | Use case |
|---|---|---|
| Entity-centred | All entities within N hops of a start entity | Entity context exploration |
| Entity-set spanning | Minimal subgraph connecting a set of entities | "What connects these 5 strategies?" |
| Type-filtered | All edges of specific types, all their nodes | "Show me all GENERATES relationships" |
| Temporal window | Subgraph as it existed at a point in time | Historical graph reconstruction |
| Category-filtered | All relationships of a category | "Show me all financial relationships" |

**Subgraph output format:**
- Node list (entity IDs, entity types, metadata)
- Edge list (relationship IDs, types, strengths, confidences, directions)
- Adjacency representation for visualisation
- Export-ready format for ControlTower dashboard

---
## PART VII — RELATIONSHIP QUALITY FRAMEWORK

### 7.1 Quality Philosophy

The quality of a relationship determines its trustworthiness as a basis for decisions. A Strategy `INFLUENCES` Hypothesis relationship with a confidence of 0.95 is a reliable input to the Influence Service. The same relationship with a confidence of 0.28 is a noise source — it should not be used to make decisions, and it should be on the deprecation watch list.

The Relationship Quality Framework defines twelve quality dimensions, a composite scoring methodology, and a quality governance process. Twelve dimensions are necessary because relationships have properties that entities do not: strength (how strong is the connection?), stability (does it hold consistently over time?), persistence (does it hold across different time windows?), and importance (is this relationship consequential to the system's intelligence?).

---

### 7.2 Quality Dimension 1: Strength

**Definition:** Strength measures the quantified degree of the relationship — how meaningful and significant the connection is.

**Strength computation by relationship type:**

| Relationship type | Strength formula |
|---|---|
| CORRELATED_WITH | |Pearson coefficient| over lookback window |
| INFLUENCES | Effect size × directionality coefficient |
| SIMILAR_TO | Cosine similarity of parameter vectors |
| CAUSED_BY | Causal confidence (proportion of cases where cause preceded effect) |
| GENERATES | 1.0 (binary — a strategy either generates a hypothesis or it does not) |
| SENSITIVE_TO | Abs(performance_in_regime − average_performance) / average_performance |
| DEPENDS_ON | 1.0 (binary — either depends or does not) |

**Strength scoring:** Strength is in [0.0, 1.0]. Strength below 0.05 triggers automatic weakening. Strength below 0.01 triggers deprecation nomination.

---

### 7.3 Quality Dimension 2: Confidence

**Definition:** Confidence measures the system's certainty that the relationship is real and will continue to hold.

**Confidence update model:** Confidence is a running estimate that starts at the initial discovery confidence and updates based on:
- New evidence that confirms the relationship → confidence increases (by increment proportional to evidence strength)
- New evidence that contradicts the relationship → confidence decreases
- Time without new evidence → confidence decays (temporal decay model)

$$\text{confidence}_{t+1} = \text{confidence}_{t} + \Delta_{\text{evidence}} - \Delta_{\text{decay}}$$

**Confidence thresholds:**

| Threshold | Value | Action |
|---|---|---|
| Causal promotion threshold | 0.85 | HYPOTHETICALLY_CAUSED_BY promoted to CAUSED_BY |
| High confidence | 0.70 | Used in all analytical operations |
| Minimum operational | 0.50 | Below this: flagged for review |
| Weakening trigger | 0.45 | WEAKENING lifecycle state |
| Deprecation trigger | 0.30 | DEPRECATED lifecycle state |
| Auto-retire | 0.10 | Automatically proposed for retirement |

---

### 7.4 Quality Dimension 3: Reliability

**Definition:** Reliability measures the historical consistency of the relationship — does it hold in the majority of cases when tested?

**Reliability computation:**

$$\text{reliability} = \frac{\text{confirmed instances}}{\text{confirmed instances + contradicted instances}}$$

A relationship that has been confirmed 80 times and contradicted 20 times has a reliability of 0.80. Reliability is separate from confidence: confidence reflects the system's current certainty; reliability reflects the historical track record.

**Reliability and confidence interaction:** If reliability falls significantly below confidence, it suggests the confidence estimate is optimistic. The Evolution Manager applies a reliability correction factor to confidence when the two diverge significantly.

---

### 7.5 Quality Dimension 4: Stability

**Definition:** Stability measures the variability of the relationship's strength over time — a stable relationship maintains approximately consistent strength; an unstable relationship fluctuates widely.

**Stability computation:**

$$\text{stability} = 1 - \frac{\text{std}(\text{strength\_history})}{\text{mean}(\text{strength\_history})}$$

This is the coefficient of variation, inverted. A perfectly stable relationship (no variation) has stability 1.0. A highly variable relationship has stability approaching 0.0.

**Stability significance:** A high-strength but low-stability relationship is dangerous to rely on — it may be strong right now but has historically varied widely. The Influence Service weights effective influence by stability for sensitive applications.

---

### 7.6 Quality Dimension 5: Persistence

**Definition:** Persistence measures the duration over which the relationship has been maintained — longer persistence is indicative of a relationship that is not an artefact of a specific market condition.

**Persistence scoring:**

$$\text{persistence} = \min\left(1.0, \frac{\text{relationship\_age\_days}}{\text{persistence\_target\_days}}\right)$$

Where `persistence_target_days` is the entity-type-pair-specific target for full persistence credit. Default targets:

| Relationship type | Persistence target |
|---|---|
| CORRELATED_WITH | 90 days |
| INFLUENCES | 60 days |
| SENSITIVE_TO | 60 days |
| SIMILAR_TO | 30 days |
| CAUSED_BY | 30 confirmed instances |
| COMPOSED_OF | Indefinite (full credit from creation) |

---

### 7.7 Quality Dimension 6: Validity

**Definition:** Validity measures whether the relationship's attributes are within their defined valid ranges and logically consistent with the Catalog definition.

**Validity checks:**

| Check | Description |
|---|---|
| Strength in [0.0, 1.0] | Required |
| Confidence in [0.0, 1.0] | Required |
| valid_from ≤ valid_until | Required if valid_until is set |
| Source entity type matches Catalog | Required |
| Target entity type matches Catalog | Required |
| Direction matches Catalog | Required |
| Cardinality not violated | Required |
| Source and target are ACTIVE | Required for ACTIVE relationships |

**Validity scoring:**

$$\text{validity} = \frac{\text{checks passed}}{\text{total checks applied}}$$

---

### 7.8 Quality Dimension 7: Consistency

**Definition:** Consistency measures whether the relationship is consistent with related relationships and entity states — not just structurally valid, but logically coherent with the wider graph.

**Consistency checks:**

| Check | Description |
|---|---|
| Direction consistency | Directed relationship does not have an implicit reverse in conflict |
| Strength chain consistency | In a chain A→B→C, the strength of A→C should be bounded by the weakest link |
| Temporal consistency | Temporal relationships are chronologically ordered |
| Aggregate consistency | COMPOSED_OF chains correctly represent the entity hierarchy |
| Contradiction check | No two relationships of the same type between the same entities with contradictory strengths |

---

### 7.9 Quality Dimension 8: Traceability

**Definition:** Traceability measures the degree to which the relationship's origin, evidence, and history can be fully reconstructed from available records.

**Traceability elements:**

| Element | Description |
|---|---|
| Provenance record | Evidence that established this relationship |
| Discovery record | How the relationship was discovered (if Discovery stage was used) |
| Version history | Complete version chain from creation |
| Audit trail | All audit events |
| Evidence references | Entity IDs of the evidence entities (trades, events, measurements) |
| Evolution record | History of all strength and confidence updates |

**Traceability scoring:**

$$\text{traceability} = \frac{\text{available elements}}{\text{required elements for this type}}$$

Binary relationships (COMPOSED_OF, GENERATES) require fewer evidence elements; derived relationships (CORRELATED_WITH, CAUSED_BY) require full evidence documentation.

---

### 7.10 Quality Dimension 9: Freshness

**Definition:** Freshness measures whether the relationship's strength and confidence have been recently validated or are based on stale evidence.

**Freshness standards by relationship type:**

| Relationship type | Fresh threshold | Stale threshold | Critical stale |
|---|---|---|---|
| CORRELATED_WITH | 1 day (daily recompute) | 7 days | 30 days |
| INFLUENCES | 1 week | 30 days | 90 days |
| SENSITIVE_TO | 1 week | 30 days | 90 days |
| CAUSED_BY | 1 month | 3 months | 6 months |
| COMPOSED_OF | Indefinite (structural) | N/A | N/A |
| SIMILAR_TO | 1 week | 30 days | 60 days |
| HEDGES | Session-based | Next session | > 2 sessions |

**Freshness scoring:**

$$\text{freshness} = \max\left(0, 1 - \frac{\text{days\_since\_last\_recompute}}{\text{stale\_threshold}}\right)$$

---

### 7.11 Quality Dimension 10: Importance

**Definition:** Importance measures how consequential this relationship is to the system's intelligence and decision-making. A relationship connecting two rarely-used entities is less important than one connecting the portfolio to a major risk threshold.

**Importance computation:**

$$\text{importance} = 0.4 \cdot \text{source\_centrality} + 0.4 \cdot \text{target\_centrality} + 0.2 \cdot \text{type\_importance\_weight}$$

Where source_centrality and target_centrality are the normalised graph centrality scores of the connected entities, and type_importance_weight is a catalog-defined weight for the relationship type (financial chain types have high weight, reference types have low weight).

---

### 7.12 Quality Dimension 11: Criticality

**Definition:** Criticality measures the operational impact if this relationship were incorrect, missing, or failed — the worst-case consequence of a quality failure.

**Criticality classification:**

| Class | Description | Examples |
|---|---|---|
| CRITICAL | System may make dangerous financial decisions without this relationship | Risk threshold connections, kill switch triggers |
| HIGH | Significant intelligence degradation or incorrect attribution | Strategy-hypothesis chains, agent-calibration links |
| MEDIUM | Reduced analytical capability | Regime-sensitivity relationships, correlation clusters |
| LOW | Informational value only | Similarity relationships, reference classifications |

**Criticality and governance:** CRITICAL relationships receive FULL audit, are permanently retained, and require Human Principal authorisation for any lifecycle change (including update).

---

### 7.13 Quality Dimension 12: Quality Scoring

**Composite Relationship Quality Score (RQS):**

$$\text{RQS} = \sum_{i=1}^{11} w_i \cdot d_i$$

Where $d_i$ is the score for dimension $i$ and $w_i$ is the dimension weight.

**Default dimension weights:**

| Dimension | Default weight | Rationale |
|---|---|---|
| Strength | 0.15 | Core relationship property |
| Confidence | 0.20 | Certainty is paramount for reliable reasoning |
| Reliability | 0.12 | Historical track record |
| Stability | 0.08 | Consistency over time |
| Persistence | 0.06 | Long-term relationship evidence |
| Validity | 0.12 | Structural correctness |
| Consistency | 0.08 | Graph-level coherence |
| Traceability | 0.05 | Audit and provenance |
| Freshness | 0.08 | Currency of evidence |
| Importance | 0.03 | Contextual significance |
| Criticality | 0.03 | Operational impact (advisory) |
| **Total** | **1.00** | |

**RQS thresholds:**

| Score | Classification | System action |
|---|---|---|
| 0.85–1.00 | EXCELLENT | No action |
| 0.70–0.84 | GOOD | Monitor |
| 0.55–0.69 | ACCEPTABLE | Flag for improvement |
| 0.35–0.54 | POOR | Governance alert; reduce operational weight |
| 0.00–0.34 | CRITICAL | Governance alert; do not use in decisions |

---

## PART VIII — RELATIONSHIP GOVERNANCE

### 8.1 Governance Overview

Relationship governance ensures that every relationship is managed responsibly throughout its lifetime. The twelve governance pillars mirror the Entity Engine's governance framework but are extended with relationship-specific concerns: conflict resolution (two relationships that say opposite things), duplicate detection (two relationship records that represent the same connection), and backward compatibility (ensuring that relationship type changes do not break dependent consumers).

---

### 8.2 Pillar 1: Relationship Ownership

**Ownership rules:**

| Rule | Description |
|---|---|
| Single owner | Every relationship has exactly one owner at any given time |
| Owner accountability | The owner is responsible for relationship quality, accuracy, and appropriate lifecycle management |
| Inherited ownership | Relationships created by a service are owned by that service |
| Approval changes ownership | When a discovered relationship is approved, ownership transfers to the approver |

**Ownership assignment by relationship category:**

| Category | Primary owner | Secondary |
|---|---|---|
| Financial | OrderManager / TradeMonitor | Human Principal |
| Market | DataFeedManager | Human Principal |
| Economic | MarketIntelligence | Human Principal |
| Risk | RiskGuardian | Human Principal |
| AI | DecisionEngine | Human Principal |
| Knowledge | KnowledgeEngine | LearningEngine |
| Portfolio | PortfolioAllocation | Human Principal |
| Derived | Discovery Manager | Human Principal |
| Structural | Entity Engine | Human Principal |

---

### 8.3 Pillar 2: Relationship Approval

**Approval-required relationship types:**

| Relationship type | Approval required | Approver | Rationale |
|---|---|---|---|
| CAUSED_BY | Yes (always) | Human Principal | Causal claims are high-stakes assertions |
| INFLUENCES (new) | Yes if confidence < 0.90 | Human Principal | Influence relationships drive strategy selection |
| SENSITIVE_TO (new) | Yes | Human Principal | Regime sensitivity affects capital allocation |
| CORRELATED_WITH (new) | Yes if confidence < 0.90 | Human Principal | Correlations used in risk management |
| Any Financial type | Yes | Human Principal | All financial chain relationships require oversight |
| OUTPERFORMS | Yes | Human Principal | Performance claims drive capital allocation |

**Approval workflow:** See Entity Engine Approval Workflow (same pattern — PENDING_APPROVAL → APPROVED/REJECTED → ACTIVE/RETIRED).

---

### 8.4 Pillar 3: Relationship Versioning Policy

**Version creation triggers for relationships:**

| Trigger | Version type | Note |
|---|---|---|
| Strength update > 0.05 change | AUTOMATIC | Small fluctuations are batched |
| Confidence update > 0.05 change | AUTOMATIC | |
| Lifecycle transition | AUTOMATIC | |
| Status change | AUTOMATIC | |
| Ownership transfer | AUTOMATIC | |
| Significant evidence addition | AUTOMATIC | |
| Evolution milestone | EXPLICIT | Named milestone |
| Schema migration | STRUCTURAL | |

**Batching policy:** Strength and confidence updates < 0.05 are batched and stored as a single version record at the end of each trading session. This prevents version explosion for frequently-updated relationships (e.g., correlations that are recomputed every hour).

---

### 8.5 Pillar 4: Conflict Resolution

Relationship conflicts arise when two relationship records make claims that are logically inconsistent.

**Types of relationship conflicts:**

| Conflict type | Example | Resolution |
|---|---|---|
| Directional conflict | A CAUSES B (strength: 0.8) AND B CAUSES A (strength: 0.7) | Review; determine if bidirectional causation is correct or one is erroneous |
| Strength conflict | Two CORRELATED_WITH relationships between same entities with different lookback windows showing different strengths | Keep both; clearly label with lookback window in metadata |
| Existence conflict | SUPPORTS relationship with strength 0.9 AND CONTRADICTS relationship between same entities | Escalate to Human Principal; cannot both be true |
| Cardinality conflict | A ONE_TO_ONE relationship has two relationships to different targets | Block second relationship; raise CardinalityViolation |

**Conflict resolution authority:**

| Conflict type | Resolution authority | Timeline |
|---|---|---|
| Existence conflict (SUPPORTS vs CONTRADICTS) | Human Principal | Within 24 hours |
| Directional conflict | Reasoning Manager (automated) + Human Principal notification | Within 48 hours |
| Cardinality conflict | Registration Service (blocks automatically) | Immediate |
| Strength conflict from different computation windows | Keep both (label clearly) | Immediate |

---

### 8.6 Pillar 5: Duplicate Detection

**Relationship duplicate scenarios:**

| Scenario | Detection method | Resolution |
|---|---|---|
| Same type, same source, same target | Exact match in Registry | Block second creation (idempotency check) |
| Same type, same pair, different validity window | Temporal overlap check | Merge or split based on business intent |
| Same semantic meaning, different type names | Semantic similarity check | Human Principal review |
| Multiple discovery candidates for same connection | Candidate deduplication in Discovery Manager | Merge into one candidate |

**Duplicate handling:**
- For exact duplicates: Block creation; return existing relationship
- For near-duplicates: Flag for Human Principal review; do not auto-merge
- For financial relationships: Never auto-merge — always escalate

---

### 8.7 Pillar 6: Relationship Merge Governance

Relationship merge (combining two relationships into one) requires:
- A documented merge reason
- A defined merge strategy (PREFER_PRIMARY, MAX_VALUES, WEIGHTED_AVERAGE)
- Human Principal authorisation (always — no automatic merge for relationships)
- A full audit record of the merge decision
- All references updated from secondary to primary

---

### 8.8 Pillar 7: Relationship Split Governance

Relationship split (dividing one relationship into two) requires:
- Human Principal authorisation (always)
- A documented split reason
- Definition of how source relationship attributes are divided
- A full audit record

---

### 8.9 Pillar 8: Retirement Policy

**Retirement triggers:**

| Trigger | Description |
|---|---|
| Confidence < 0.10 for 30 days | Evidence has collapsed |
| Source entity RETIRED | Parent entity retired |
| Target entity RETIRED | Parent entity retired |
| Human Principal instruction | Manual retirement |
| Superseded by a CAUSED_BY with confidence > 0.90 | A stronger version of this relationship has been established |

**Retirement records:** Every retirement includes a retirement reason, the final quality score at retirement, and the final version snapshot. Retired relationships are permanently accessible via the Audit Service.

---

### 8.10 Pillar 9: Backward Compatibility

**Schema change policy for relationship types:**

| Change type | Compatibility | Migration |
|---|---|---|
| Add optional field | FULLY_COMPATIBLE | None |
| Add required field (with default) | READ_COMPATIBLE | No migration if default is sufficient |
| Remove field | BREAKING | Migration period of 90 days minimum |
| Change allowed endpoint types | BREAKING | Full review and migration |
| Change cardinality | BREAKING | Requires full governance approval |
| Change directionality | BREAKING | Requires Human Principal approval + migration |

---

### 8.11 Pillar 10: Audit Policy

**Audit requirements by relationship category:**

| Category | Audit level | Retention |
|---|---|---|
| Financial | FULL | Relationship lifetime + 7 years |
| Risk | FULL | Relationship lifetime + 10 years |
| AI | STANDARD | Relationship lifetime + 2 years |
| Knowledge | STANDARD | Relationship lifetime + 2 years |
| Derived | STANDARD | Relationship lifetime + 1 year |
| Market/Corporate | MINIMAL | Relationship lifetime |
| Structural | MINIMAL | Relationship lifetime |

---

### 8.12 Pillar 11: Security

**Access control for relationships:**

| Relationship sensitivity | Read | Write | Admin |
|---|---|---|---|
| PUBLIC | All services | Owner only | Human Principal |
| INTERNAL | All services | Owner only | Human Principal |
| CONFIDENTIAL | Owner + authorised | Owner only | Human Principal |
| RESTRICTED | Authorised only | Owner only | Human Principal |

Relationship sensitivity inherits from the higher of the source and target entity sensitivity classifications.

---

### 8.13 Pillar 12: Compliance

**Compliance monitoring schedule:**

| Check | Frequency |
|---|---|
| Ownership validation | Every cycle (for financial and risk relationships) |
| Quality score review | Daily |
| Integrity scan | Weekly |
| Audit chain verification | Weekly |
| Retention compliance | Monthly |
| Full governance report | Monthly |

**Compliance violation escalation:**

| Severity | Response |
|---|---|
| INFO | Logged; included in monthly report |
| WARNING | Logged; weekly Telegram summary |
| ERROR | Governance flag; Telegram alert |
| CRITICAL | Immediate Telegram alert; Human Principal review required |

---
## PART IX — RELATIONSHIP CONSTITUTION

### 9.1 Overview

The Relationship Constitution is the supreme set of mandatory rules governing every relationship in the IIOS. These rules are non-negotiable. No exception, override, or workaround to a Constitutional rule is permitted without an explicit amendment recorded as a Governance Decision Record.

Rules are organised into eight categories: Identity (RC-A), Connectivity (RC-B), Quality (RC-C), Lifecycle (RC-D), Audit (RC-E), Governance (RC-F), Service (RC-G), and Graph (RC-H).

---

### 9.2 Category A: Identity Rules

| Rule ID | Rule | Rationale |
|---|---|---|
| RC-A-01 | Every relationship has exactly one permanent canonical identity (UUID4 relationship_id) assigned at creation. | Identity is the foundation of all relationship operations. |
| RC-A-02 | A relationship's canonical identity never changes after assignment. | Changing identity breaks all references and audit chains. |
| RC-A-03 | A retired relationship's relationship_id is never reused. | Reuse breaks historical audit continuity. |
| RC-A-04 | Every relationship has exactly one Reference ID assigned at creation. | Reference IDs provide human-readable identification. |
| RC-A-05 | All aliases for relationships must be unique within the relationship type. | Duplicate aliases cause identity ambiguity. |
| RC-A-06 | Identity resolution must return the canonical relationship_id for any valid identifier (UUID4, alias, reference ID). | All identifier types must be resolvable. |
| RC-A-07 | No two relationship records may represent exactly the same connection (same type, same source, same target) — one must be a duplicate and resolved. | Duplicate relationships corrupt graph traversal. |
| RC-A-08 | In a merge, the primary relationship_id becomes the canonical identity. | Merge preserves the older entity's identity. |

---

### 9.3 Category B: Connectivity Rules

| Rule ID | Rule | Rationale |
|---|---|---|
| RC-B-01 | Every relationship connects exactly two entities — one source and one target. | No hyperedges (multi-entity edges) in the IIOS graph. |
| RC-B-02 | Both the source entity and the target entity must be registered in the Entity Registry before a relationship between them can be created. | Relationships between non-existent entities are invalid. |
| RC-B-03 | Both entities must be in ACTIVE or CREATED lifecycle state when a new relationship is created. | Relationships to archived or retired entities are invalid at creation time. |
| RC-B-04 | Every relationship type has a defined direction (DIRECTED, UNDIRECTED, or BIDIRECTIONAL) in the Catalog. No relationship may exist without a defined direction. | Ambiguous direction makes traversal undefined. |
| RC-B-05 | Directed relationships have a source (origin) and a target (destination). The direction is semantically meaningful and may not be reversed arbitrarily. | Direction encodes domain semantics. |
| RC-B-06 | Self-referential relationships (source = target) are prohibited for all relationship types unless explicitly permitted in the Catalog. | Self-loops cause graph algorithm failures. |
| RC-B-07 | Every relationship type defines allowed source entity types and allowed target entity types. A relationship instance violating these type constraints is rejected at creation. | Type safety at the relationship level. |
| RC-B-08 | Cardinality constraints (ONE_TO_ONE, ONE_TO_MANY, MANY_TO_MANY) are enforced at creation time. A relationship that would violate its type's cardinality is rejected. | Cardinality constraints enforce domain invariants. |
| RC-B-09 | COMPOSED_OF relationships must form a strict tree (no node may have more than one COMPOSED_OF parent). | Multiple parents in a composition chain is a domain modelling error. |
| RC-B-10 | COMPOSED_OF and DEPENDS_ON chains must be acyclic. A circular chain in either of these types is a CRITICAL integrity violation. | Cycles in composition/dependency chains cause infinite recursion in traversal. |
| RC-B-11 | When a source or target entity is archived, all relationships involving that entity as source or target must be cascade-archived within the same session. | Dangling edges corrupt graph integrity. |
| RC-B-12 | Relationships between entities of incompatible lifecycle states (e.g., source RETIRED, target ACTIVE) are flagged as integrity violations during the next integrity scan. | Inconsistent lifecycle states signal a lifecycle management failure. |

---

### 9.4 Category C: Quality Rules

| Rule ID | Rule | Rationale |
|---|---|---|
| RC-C-01 | Every relationship has a strength value in [0.0, 1.0] at all times. | Strength is a mandatory relationship attribute. |
| RC-C-02 | Every relationship has a confidence value in [0.0, 1.0] at all times. | Confidence is the primary quality indicator. |
| RC-C-03 | Binary relationship types (where strength is always 1.0 by definition) must document this in the Catalog. | Binary relationships are not exempt from strength — the value is 1.0, not absent. |
| RC-C-04 | Every relationship has a computed Relationship Quality Score (RQS). | Quality without measurement is aspiration, not assurance. |
| RC-C-05 | RQS is recomputed whenever any quality dimension input changes. | Stale quality scores are misleading. |
| RC-C-06 | A relationship with RQS < 0.35 generates a CRITICAL governance alert. | Critical-quality relationships are dangerous inputs to reasoning. |
| RC-C-07 | A relationship with RQS < 0.35 is not used in operational influence propagation or causal chain analysis. | Low-quality relationships must not drive live decisions. |
| RC-C-08 | Strength below 0.05 for more than 3 days triggers a transition to WEAKENING lifecycle state. | Negligible-strength relationships should be reviewed for retirement. |
| RC-C-09 | Confidence below 0.30 for more than 7 days triggers automatic deprecation nomination. | Low-confidence relationships must be formally retired or revalidated. |
| RC-C-10 | Every non-binary relationship must have a provenance record documenting the evidence that established it. | Evidenceless relationships cannot be validated or challenged. |
| RC-C-11 | Derived relationships (CORRELATED_WITH, SIMILAR_TO, SENSITIVE_TO) have a mandatory freshness schedule. If the scheduled recompute does not occur, the relationship's freshness score decays until it triggers a governance alert. | Derived relationships are time-limited; stale correlations are dangerous. |
| RC-C-12 | Relationship strength and confidence histories are maintained for the full relationship lifetime. | Evolution analysis requires complete history. |

---

### 9.5 Category D: Lifecycle Rules

| Rule ID | Rule | Rationale |
|---|---|---|
| RC-D-01 | Every relationship follows a defined lifecycle state machine. | Unmanaged relationship lifecycle = ungoverned system state. |
| RC-D-02 | A relationship in DISCOVERY_CANDIDATE state does not have a relationship_id and does not appear in the graph. | Candidates are proposals, not relationships. |
| RC-D-03 | A relationship in CREATED state does not appear in the adjacency index. | Inactive relationships must not pollute graph traversal. |
| RC-D-04 | A relationship in ACTIVE state appears in the adjacency index and is available for all graph operations. | ACTIVE is the only state with full operational visibility. |
| RC-D-05 | A relationship in WEAKENING or STRENGTHENING state remains in the adjacency index but is flagged for monitoring. | Evolution states are still operational. |
| RC-D-06 | A relationship in DEPRECATED state remains in the adjacency index (flagged) but its confidence decrement may reduce its effective contribution to reasoning. | Deprecated relationships provide declining signal. |
| RC-D-07 | A relationship in ARCHIVED state is removed from the adjacency index and from active cache tiers. | Archived relationships must not affect live graph operations. |
| RC-D-08 | A RETIRED relationship cannot transition to any other state. | Retirement is irreversible. |
| RC-D-09 | Every lifecycle transition is recorded as an audit event. | Lifecycle events are governance events. |
| RC-D-10 | No relationship may skip a required lifecycle stage without an explicit justification recorded in the audit log. | Stage skipping bypasses validation and governance. |
| RC-D-11 | Cascade archival (when an entity is archived) must complete within the same session as the entity archival. | Graph integrity requires synchronous cascade. |
| RC-D-12 | A relationship may only be restored from ARCHIVED to ACTIVE with Human Principal authorisation. | Restoration of archived relationships requires accountability. |

---

### 9.6 Category E: Audit Rules

| Rule ID | Rule | Rationale |
|---|---|---|
| RC-E-01 | Every relationship creation generates a RELATIONSHIP_CREATED audit event. | Birth of every relationship must be permanently recorded. |
| RC-E-02 | Every lifecycle state transition generates a RELATIONSHIP_TRANSITION audit event. | State transitions are governance events. |
| RC-E-03 | Every strength change greater than 0.05 generates a RELATIONSHIP_STRENGTH_CHANGED audit event. | Significant strength changes affect downstream reasoning. |
| RC-E-04 | Every confidence change greater than 0.05 generates a RELATIONSHIP_CONFIDENCE_CHANGED audit event. | Significant confidence changes affect operational use. |
| RC-E-05 | Audit records are never deleted, modified, or overwritten. | Tampered audit logs are worthless. |
| RC-E-06 | Audit records are hash-chained to enable tamper detection. | Chain breaks reveal tampering attempts. |
| RC-E-07 | Every audit record includes: relationship_id, event_type, actor_id, timestamp, previous state, new state, reason. | Incomplete audit records are not audit records. |
| RC-E-08 | Financial relationship audit records are retained for the relationship lifetime plus 7 years. | Regulatory compliance. |
| RC-E-09 | Risk relationship audit records are retained for the relationship lifetime plus 10 years. | Risk management compliance. |
| RC-E-10 | The Audit Service never caches relationship audit records — all reads are from the persistence layer. | Audit records must always be current. |
| RC-E-11 | Audit chain integrity verification runs weekly for all CONFIDENTIAL and RESTRICTED relationships. | Regular integrity checks detect tampering proactively. |

---

### 9.7 Category F: Governance Rules

| Rule ID | Rule | Rationale |
|---|---|---|
| RC-F-01 | Every relationship has exactly one owner at all times after creation. | Ownerless relationships have no accountability. |
| RC-F-02 | The owner of a relationship must be an authorised owner for this relationship type. | Unauthorised ownership breaks accountability. |
| RC-F-03 | CAUSED_BY relationships require Human Principal approval before activation. | Causal claims have significant downstream impact. |
| RC-F-04 | Financial chain relationships require Human Principal approval before activation. | Live-trading relationships demand explicit oversight. |
| RC-F-05 | Relationship conflicts (existence conflicts — SUPPORTS vs CONTRADICTS between same entities) are escalated to Human Principal within 24 hours. | Contradictory relationships corrupt the knowledge graph. |
| RC-F-06 | Duplicate relationships (same type, same entity pair) are never silently merged automatically for financial or risk relationships. | Financial duplicates must be explicitly resolved. |
| RC-F-07 | Relationship governance policies are defined per relationship type in the Governance Policy Catalog. | Generic policies are insufficient for domain-specific governance. |
| RC-F-08 | CRITICAL governance violations generate immediate Telegram notifications to the Human Principal. | Critical violations demand immediate human awareness. |
| RC-F-09 | The Governance Manager generates a monthly relationship governance health report. | Regular reporting enables proactive governance. |
| RC-F-10 | Every schema change to a relationship type definition requires a formal migration plan with Human Principal approval. | Schema changes affect all existing relationship records. |
| RC-F-11 | Relationship merge operations are never performed automatically for any relationship category. | Identity changes require human accountability. |
| RC-F-12 | Every relationship retirement records a final quality score snapshot and a retirement reason. | Retirement without documentation loses valuable analytics. |
| RC-F-13 | Backward-incompatible changes to relationship type definitions require a migration period of at least 90 days. | Consumers need time to adapt to breaking changes. |
| RC-F-14 | The Integrity Manager runs a full graph integrity scan at least once per week. | Regular integrity scans catch systemic problems before they affect decisions. |

---

### 9.8 Category G: Service Rules

| Rule ID | Rule | Rationale |
|---|---|---|
| RC-G-01 | No relationship may be created, updated, or deleted except through an authorised Relationship Service. | Direct persistence access bypasses validation and audit. |
| RC-G-02 | The Registration Service is the only authorised path for relationship creation. | All creation must go through the Factory sequence. |
| RC-G-03 | The Traversal Service must complete 1-hop neighbor queries in under 5 ms during market hours. | Traversal is on the cycle-time critical path. |
| RC-G-04 | The Influence Service is best-effort and time-bounded — its results are advisory and never block cycle execution. | Influence computation failures must not halt trading. |
| RC-G-05 | The Reasoning Service is best-effort and time-bounded — its results are advisory only. | Reasoning failures must not halt trading. |
| RC-G-06 | All Relationship Services enforce rate limits per calling component. | Runaway relationship creation can destabilise the persistence layer. |
| RC-G-07 | Every Relationship Service failure is logged with full context (relationship_id, type, operation, error, caller, timestamp). | Service failures without context cannot be diagnosed. |
| RC-G-08 | Relationship Services do not expose direct persistence layer access to consumers. | All access is through services. |
| RC-G-09 | The Traversal Service detects and breaks traversal loops using visited-node tracking. | Cycles in the graph must not cause infinite traversal loops. |
| RC-G-10 | The Discovery Service never creates relationships without authorisation — all discoveries go through the approval workflow. | Automatic relationship creation must be explicitly permitted. |
| RC-G-11 | The Evolution Manager does not change relationship lifecycle states — it calls the Lifecycle Manager. | Single responsibility: Evolution manages data, Lifecycle manages state. |
| RC-G-12 | Cache invalidation for a relationship must complete before the update response is returned to the caller. | Stale cache after write causes stale reads by subsequent callers. |

---

### 9.9 Category H: Graph Rules

| Rule ID | Rule | Rationale |
|---|---|---|
| RC-H-01 | The adjacency index is the primary data structure for graph traversal — not the persistence layer. | Persistence-layer traversal is orders of magnitude slower. |
| RC-H-02 | The adjacency index is updated synchronously on every relationship lifecycle change. | Stale adjacency index corrupts traversal results. |
| RC-H-03 | Only ACTIVE relationships (and WEAKENING, STRENGTHENING, DEPRECATED) appear in the adjacency index. | CREATED, ARCHIVED, and RETIRED relationships must not pollute live traversal. |
| RC-H-04 | The maximum hop depth for any traversal operation is 10 hops. Requests for deeper traversal are rejected. | Deep traversal of large graphs is computationally intractable. |
| RC-H-05 | Traversal prioritisation uses effective weight (strength × confidence) for weighted graph algorithms. | High-uncertainty edges should contribute less to traversal decisions. |
| RC-H-06 | Influence propagation stops when effective strength (accumulated through hops) falls below 0.05. | Negligible influence should not propagate to terminal nodes. |
| RC-H-07 | Graph cycle detection for COMPOSED_OF and DEPENDS_ON chains runs daily. | Cycles in these chains are structural errors that must be caught early. |
| RC-H-08 | The Relationship Engine maintains node shadow records for all entities with at least one relationship. | Node shadows enable graph-level analytics without querying the Entity Engine. |
| RC-H-09 | Centrality scores are recomputed for all nodes at least weekly. | Stale centrality scores lead to incorrect importance calculations. |
| RC-H-10 | Temporal graph queries (point-in-time graph state) are supported for all dates within the retention period. | Historical graph state is required for audit and causal analysis. |
| RC-H-11 | Subgraph extraction results include a boundary node list identifying nodes reached but not further expanded. | Consumers need to know where the subgraph is bounded. |
| RC-H-12 | The graph index maintains multi-edge support — multiple relationships of different types between the same entity pair are all indexed independently. | Collapsing multi-edges destroys relationship type semantics. |
| RC-H-13 | Undirected edges appear in both OUTGOING and INCOMING traversals from both endpoints. | Undirected edge symmetry must be implemented at the index level. |

---

### 9.10 Total Rule Count

| Category | Rule count |
|---|---|
| RC-A: Identity | 8 |
| RC-B: Connectivity | 12 |
| RC-C: Quality | 12 |
| RC-D: Lifecycle | 12 |
| RC-E: Audit | 11 |
| RC-F: Governance | 14 |
| RC-G: Service | 12 |
| RC-H: Graph | 13 |
| **TOTAL** | **94 rules** |

---
## PART X — RELATIONSHIP READINESS CHECKLIST

### 10.1 Checklist Purpose and Structure

The Relationship Readiness Checklist (RRC) is the definitive gate used to determine whether a relationship is fully operational within the IIOS. A relationship that passes all required checks (PASS) is Ready. A relationship with any FAIL is Not Ready. A relationship with warnings (WARN) is Conditionally Ready and must be reviewed within 7 calendar days.

The RRC is organised into twelve sections. Sections 1 through 8 cover structural and operational readiness. Sections 9 through 12 cover analytical and reasoning readiness.

---

### 10.2 Section 1: Registration Readiness

**Purpose:** Confirms the relationship has been correctly registered in the Relationship Registry and all identity attributes are valid.

| Check ID | Check | Level |
|---|---|---|
| RRC-1.01 | Relationship has a valid UUID4 relationship_id | REQUIRED |
| RRC-1.02 | Relationship has a valid Reference ID | REQUIRED |
| RRC-1.03 | Relationship is registered in the active Registry partition | REQUIRED |
| RRC-1.04 | Relationship type is found in the Catalog | REQUIRED |
| RRC-1.05 | Source entity_id resolves to an existing, ACTIVE entity | REQUIRED |
| RRC-1.06 | Target entity_id resolves to an existing, ACTIVE entity | REQUIRED |
| RRC-1.07 | Direction attribute matches Catalog definition | REQUIRED |
| RRC-1.08 | Cardinality constraint is not violated | REQUIRED |
| RRC-1.09 | Self-referential rule is satisfied (source ≠ target) | REQUIRED |
| RRC-1.10 | Relationship is not a duplicate of an existing relationship | REQUIRED |
| RRC-1.11 | All required metadata fields are present and non-null | REQUIRED |
| RRC-1.12 | created_at timestamp is set | REQUIRED |
| RRC-1.13 | created_by is set to a recognised actor | REQUIRED |
| RRC-1.14 | Aliases (if any) are unique within relationship type | ADVISORY |

**Section 1 Result:** PASS if RRC-1.01 through RRC-1.13 all pass. WARN if RRC-1.14 fails. FAIL if any REQUIRED check fails.

---

### 10.3 Section 2: Validation Readiness

**Purpose:** Confirms the relationship has passed the required validation checks — structural, semantic, and contextual.

| Check ID | Check | Level |
|---|---|---|
| RRC-2.01 | Structural validation: all required fields present | REQUIRED |
| RRC-2.02 | Structural validation: all fields within valid ranges | REQUIRED |
| RRC-2.03 | Semantic validation: source entity type matches Catalog allowed source types | REQUIRED |
| RRC-2.04 | Semantic validation: target entity type matches Catalog allowed target types | REQUIRED |
| RRC-2.05 | Semantic validation: strength is in [0.0, 1.0] | REQUIRED |
| RRC-2.06 | Semantic validation: confidence is in [0.0, 1.0] | REQUIRED |
| RRC-2.07 | Semantic validation: valid_from date is logically correct | REQUIRED |
| RRC-2.08 | Contextual validation: evidence/provenance present (for non-binary types) | REQUIRED |
| RRC-2.09 | Contextual validation: relationship is coherent with neighbouring relationships in graph | ADVISORY |
| RRC-2.10 | Existence conflict check: no SUPPORTS/CONTRADICTS pair with same entity pair | REQUIRED |
| RRC-2.11 | Validation record stored and accessible | REQUIRED |

**Section 2 Result:** PASS if RRC-2.01 through RRC-2.08, RRC-2.10, RRC-2.11 all pass. WARN if RRC-2.09 fails. FAIL if any REQUIRED check fails.

---

### 10.4 Section 3: Typing Readiness

**Purpose:** Confirms that the relationship type is correctly assigned and the relationship behaves according to type constraints.

| Check ID | Check | Level |
|---|---|---|
| RRC-3.01 | Relationship type is from a permitted category | REQUIRED |
| RRC-3.02 | Relationship type is from the approved Relationship Catalog | REQUIRED |
| RRC-3.03 | Type version matches current Catalog version | REQUIRED |
| RRC-3.04 | Source entity category matches allowed source categories | REQUIRED |
| RRC-3.05 | Target entity category matches allowed target categories | REQUIRED |
| RRC-3.06 | Direction mode (DIRECTED/UNDIRECTED/BIDIRECTIONAL) matches Catalog | REQUIRED |
| RRC-3.07 | Cardinality mode matches Catalog | REQUIRED |
| RRC-3.08 | Temporal mode (HISTORICAL, CURRENT, PROJECTED) is set | REQUIRED |
| RRC-3.09 | Strength basis (STATISTICAL, BINARY, COMPUTED, etc.) matches Catalog | REQUIRED |
| RRC-3.10 | Binary relationship has strength = 1.0 | REQUIRED for binary types |
| RRC-3.11 | Type-specific metadata fields populated (e.g., lookback_window for CORRELATED_WITH) | REQUIRED |
| RRC-3.12 | Type-specific freshness schedule defined | ADVISORY |

**Section 3 Result:** PASS if all applicable REQUIRED checks pass. WARN if RRC-3.12 fails. FAIL if any REQUIRED check fails.

---

### 10.5 Section 4: Indexing Readiness

**Purpose:** Confirms the relationship is correctly indexed for efficient lookup and traversal.

| Check ID | Check | Level |
|---|---|---|
| RRC-4.01 | Relationship appears in adjacency index (outgoing from source) | REQUIRED |
| RRC-4.02 | Relationship appears in adjacency index (incoming to target) | REQUIRED |
| RRC-4.03 | Undirected relationship appears in both OUTGOING and INCOMING indices for both endpoints | REQUIRED for undirected |
| RRC-4.04 | Relationship appears in type index (type→relationship_id) | REQUIRED |
| RRC-4.05 | Relationship appears in entity pair index (source_id:target_id→relationship_id) | REQUIRED |
| RRC-4.06 | Relationship appears in temporal index (for temporal relationship types) | REQUIRED for temporal |
| RRC-4.07 | Effective weight (strength × confidence) is computed and stored in the edge record | REQUIRED |
| RRC-4.08 | Relationship cache entry exists in L1 or L2 (or is scheduled for lazy population) | ADVISORY |
| RRC-4.09 | Index consistency check: all index entries point to the same relationship version | REQUIRED |

**Section 4 Result:** PASS if all applicable REQUIRED checks pass. WARN if RRC-4.08 fails. FAIL if any REQUIRED check fails.

---

### 10.6 Section 5: Versioning Readiness

**Purpose:** Confirms the relationship has correct version history and versioning state.

| Check ID | Check | Level |
|---|---|---|
| RRC-5.01 | Relationship has a version number ≥ 1 | REQUIRED |
| RRC-5.02 | Relationship has a version_created_at timestamp | REQUIRED |
| RRC-5.03 | First version (v1) corresponds to the creation event | REQUIRED |
| RRC-5.04 | Version chain is contiguous (no missing version numbers) | REQUIRED |
| RRC-5.05 | Latest version record exists in the Version Manager | REQUIRED |
| RRC-5.06 | Strength history record exists (at least initial value) | REQUIRED |
| RRC-5.07 | Confidence history record exists (at least initial value) | REQUIRED |
| RRC-5.08 | Version chain is accessible for audit (not compressed or truncated) | REQUIRED |
| RRC-5.09 | Changelog entry exists for every version change | ADVISORY |
| RRC-5.10 | Batched strength/confidence updates do not exceed 30-day batch window | ADVISORY |

**Section 5 Result:** PASS if RRC-5.01 through RRC-5.08 all pass. WARN if RRC-5.09 or RRC-5.10 fail. FAIL if any REQUIRED check fails.

---

### 10.7 Section 6: Governance Readiness

**Purpose:** Confirms the relationship satisfies all governance requirements appropriate for its type and category.

| Check ID | Check | Level |
|---|---|---|
| RRC-6.01 | Relationship has an assigned owner | REQUIRED |
| RRC-6.02 | Owner is authorised for this relationship type | REQUIRED |
| RRC-6.03 | Approval workflow completed (for approval-required types) | REQUIRED |
| RRC-6.04 | Governance policy exists for this relationship type | REQUIRED |
| RRC-6.05 | Lifecycle state is consistent with governance requirements | REQUIRED |
| RRC-6.06 | CRITICAL relationships have Human Principal as secondary owner | REQUIRED |
| RRC-6.07 | Conflict check completed (no open conflicts) | REQUIRED |
| RRC-6.08 | Duplicate check completed (no open duplicates) | REQUIRED |
| RRC-6.09 | Governance metadata is complete (category, sensitivity, lifecycle policy) | REQUIRED |
| RRC-6.10 | Schema version matches current Catalog schema version | REQUIRED |
| RRC-6.11 | Backward compatibility impact assessment completed (for schema changes) | ADVISORY |
| RRC-6.12 | Compliance schedule assigned for this relationship category | ADVISORY |

**Section 6 Result:** PASS if RRC-6.01 through RRC-6.10 all pass. WARN if RRC-6.11 or RRC-6.12 fail. FAIL if any REQUIRED check fails.

---

### 10.8 Section 7: Audit Readiness

**Purpose:** Confirms the relationship has a complete and valid audit trail.

| Check ID | Check | Level |
|---|---|---|
| RRC-7.01 | RELATIONSHIP_CREATED audit event exists | REQUIRED |
| RRC-7.02 | RELATIONSHIP_CREATED event has all required fields | REQUIRED |
| RRC-7.03 | Audit chain starts at v1 | REQUIRED |
| RRC-7.04 | All lifecycle transitions have corresponding audit events | REQUIRED |
| RRC-7.05 | Audit events are hash-chained | REQUIRED |
| RRC-7.06 | Hash chain is unbroken (integrity check passes) | REQUIRED |
| RRC-7.07 | Retention policy is set and enforced | REQUIRED |
| RRC-7.08 | RESTRICTED relationship audit records are stored in the RESTRICTED tier | REQUIRED |
| RRC-7.09 | Audit trail is accessible via the Audit Service | REQUIRED |
| RRC-7.10 | Provenance record is linked in audit trail | REQUIRED |
| RRC-7.11 | Last audit read timestamp is tracked | ADVISORY |

**Section 7 Result:** PASS if RRC-7.01 through RRC-7.10 all pass. WARN if RRC-7.11 fails. FAIL if any REQUIRED check fails.

---

### 10.9 Section 8: Searchability Readiness

**Purpose:** Confirms the relationship is discoverable through all required search channels.

| Check ID | Check | Level |
|---|---|---|
| RRC-8.01 | Relationship appears in the full-text search index | REQUIRED |
| RRC-8.02 | Relationship is retrievable by type | REQUIRED |
| RRC-8.03 | Relationship is retrievable by entity pair (source_id, target_id) | REQUIRED |
| RRC-8.04 | Relationship is retrievable by source entity | REQUIRED |
| RRC-8.05 | Relationship is retrievable by target entity | REQUIRED |
| RRC-8.06 | Search results include lifecycle state filter capability | REQUIRED |
| RRC-8.07 | Temporal search is available (for temporal relationship types) | REQUIRED |
| RRC-8.08 | Relationship metadata is available in search results | ADVISORY |
| RRC-8.09 | Search cache TTL is appropriate for this relationship's freshness standard | ADVISORY |

**Section 8 Result:** PASS if RRC-8.01 through RRC-8.07 all pass. WARN if RRC-8.08 or RRC-8.09 fail. FAIL if any REQUIRED check fails.

---

### 10.10 Section 9: Traversability Readiness

**Purpose:** Confirms the relationship is correctly integrated into the graph for traversal operations.

| Check ID | Check | Level |
|---|---|---|
| RRC-9.01 | Relationship edge appears in adjacency list for BFS traversal from source | REQUIRED |
| RRC-9.02 | Relationship edge appears in adjacency list for DFS traversal from source | REQUIRED |
| RRC-9.03 | Effective weight is available for weighted (Dijkstra) traversal | REQUIRED |
| RRC-9.04 | Multi-hop path scoring is correct: effective_weight is included in path score computation | REQUIRED |
| RRC-9.05 | Relationship is reachable in neighborhood search from source entity | REQUIRED |
| RRC-9.06 | Relationship is reachable in neighborhood search from target entity | REQUIRED |
| RRC-9.07 | Traversal depth limits are enforced (max 10 hops) | REQUIRED |
| RRC-9.08 | Cycle detection is active for COMPOSED_OF and DEPENDS_ON relationship types | REQUIRED for those types |
| RRC-9.09 | Traversal visited-node tracker prevents infinite loops | REQUIRED |
| RRC-9.10 | Traversal filter by type is applied correctly | ADVISORY |
| RRC-9.11 | Subgraph extraction includes this relationship when the source entity is the root | ADVISORY |

**Section 9 Result:** PASS if applicable REQUIRED checks pass. WARN if ADVISORY checks fail. FAIL if any REQUIRED check fails.

---

### 10.11 Section 10: Reasoning Readiness

**Purpose:** Confirms the relationship can be used as input to the Reasoning Manager's analytical operations.

| Check ID | Check | Level |
|---|---|---|
| RRC-10.01 | Relationship confidence ≥ 0.50 (minimum for reasoning input) | REQUIRED |
| RRC-10.02 | Relationship RQS ≥ 0.35 (minimum for operational reasoning use) | REQUIRED |
| RRC-10.03 | Relationship is resolvable via the Reasoning Manager's context materialisation | REQUIRED |
| RRC-10.04 | Causal chain uses only CAUSED_BY relationships with confidence ≥ 0.85 | REQUIRED for causal |
| RRC-10.05 | Influence chain propagation is computed correctly through this relationship's effective weight | REQUIRED |
| RRC-10.06 | Pattern matching is possible (relationship appears in the Reasoning Manager's pattern registry) | ADVISORY |
| RRC-10.07 | Analogical reasoning is possible (if the relationship type participates in similarity computation) | ADVISORY |
| RRC-10.08 | Deductive inference includes this relationship as a valid premise | ADVISORY |
| RRC-10.09 | Inductive generalisation includes this relationship in training data for analogies | ADVISORY |
| RRC-10.10 | Confidence meets the Reasoning Manager's minimum threshold for the operation type | REQUIRED |

**Section 10 Result:** PASS if RRC-10.01 through RRC-10.05, RRC-10.10 all pass. WARN if ADVISORY checks fail. FAIL if any REQUIRED check fails.

---

### 10.12 Section 11: Graph Readiness

**Purpose:** Confirms the relationship is correctly integrated at the graph level, including clustering, centrality, and subgraph operations.

| Check ID | Check | Level |
|---|---|---|
| RRC-11.01 | Node shadow records exist for both source and target entities | REQUIRED |
| RRC-11.02 | Node shadow centrality scores include contributions from this relationship | REQUIRED |
| RRC-11.03 | Relationship is included in graph clustering operations | REQUIRED |
| RRC-11.04 | Relationship appears in the correct cluster (type-based, strength-based, or structural) | ADVISORY |
| RRC-11.05 | Relationship is included in graph partitioning logic | REQUIRED |
| RRC-11.06 | Temporal graph index includes this relationship for its full temporal range | REQUIRED for temporal |
| RRC-11.07 | Point-in-time graph reconstruction correctly includes this relationship for its valid_from period | REQUIRED |
| RRC-11.08 | Influence propagation path includes this relationship when expected | REQUIRED |
| RRC-11.09 | Subgraph extraction for root entity correctly includes or excludes this relationship based on depth and type filters | REQUIRED |
| RRC-11.10 | Multi-edge index supports multiple relationship types between same entity pair | REQUIRED |
| RRC-11.11 | Graph consistency check has been run within the last 7 days | ADVISORY |

**Section 11 Result:** PASS if applicable REQUIRED checks pass. WARN if ADVISORY checks fail. FAIL if any REQUIRED check fails.

---

### 10.13 Section 12: Evolution Readiness

**Purpose:** Confirms the relationship has been correctly configured for ongoing evolution, maintenance, and lifecycle management.

| Check ID | Check | Level |
|---|---|---|
| RRC-12.01 | Strength update schedule is defined and active | REQUIRED |
| RRC-12.02 | Confidence decay model is active | REQUIRED |
| RRC-12.03 | Freshness schedule is defined and active (for non-structural types) | REQUIRED |
| RRC-12.04 | Evolution Manager has registered this relationship for monitoring | REQUIRED |
| RRC-12.05 | Lifecycle Manager thresholds are configured (WEAKENING, DEPRECATION, RETIREMENT triggers) | REQUIRED |
| RRC-12.06 | Evolution milestones are defined for this relationship type | ADVISORY |
| RRC-12.07 | EMA smoothing parameter (α) is set to the type-appropriate value (default 0.85) | REQUIRED |
| RRC-12.08 | Confidence decay rate (λ) is set to the type-appropriate value (default 0.01/day) | REQUIRED |
| RRC-12.09 | Strengthening trigger conditions are defined | ADVISORY |
| RRC-12.10 | Weakening trigger conditions are defined | REQUIRED |
| RRC-12.11 | Retirement trigger conditions are defined | REQUIRED |
| RRC-12.12 | Evolution audit events will be generated for significant strength/confidence changes | REQUIRED |
| RRC-12.13 | Version batch window (max 30 days) is configured | ADVISORY |

**Section 12 Result:** PASS if RRC-12.01, 12.02, 12.03, 12.04, 12.05, 12.07, 12.08, 12.10, 12.11, 12.12 all pass. WARN if ADVISORY checks fail. FAIL if any REQUIRED check fails.

---

### 10.14 Overall Readiness Classification

| Classification | Criteria | Operational status |
|---|---|---|
| FULLY READY | All 12 sections PASS | Full operational use permitted |
| CONDITIONALLY READY | 12 sections PASS or WARN; no FAIL | Operational use permitted; WARN items must be resolved within 7 days |
| NOT READY | Any REQUIRED check FAIL in any section | Relationship must not be used operationally until FAIL resolved |
| CRITICALLY NOT READY | 3 or more FAIL in governance, quality, or audit sections | Immediate Human Principal notification required |

**Critical path note:** Sections 1 (Registration), 2 (Validation), 4 (Indexing), and 6 (Governance) are always evaluated first. A FAIL in any of these four sections constitutes a blocking defect and automatically triggers NOT READY classification regardless of other sections.

---
---

## SUPPLEMENT A — RELATIONSHIP TYPE CATALOGUE

This supplement provides the complete taxonomy of all relationship types across all 15 architectural categories. For each type, the table records direction, cardinality, strength basis, and the entity types that may serve as source and target.

### A.1 Category 1: Structural Relationships

| Type | Direction | Cardinality | Strength basis | Source types | Target types |
|---|---|---|---|---|---|
| COMPOSED_OF | DIRECTED | ONE_TO_MANY | BINARY (1.0) | Portfolio, Strategy, Index | Strategy, Hypothesis, Instrument |
| CONTAINS | DIRECTED | ONE_TO_MANY | BINARY (1.0) | Sector, Category, Portfolio | Entity (any category) |
| PART_OF | DIRECTED | MANY_TO_ONE | BINARY (1.0) | Strategy, Hypothesis, Instrument | Portfolio, Sector, Category |
| BELONGS_TO | DIRECTED | MANY_TO_ONE | BINARY (1.0) | Instrument, Strategy | Category, Sector, Portfolio |
| REFERENCES | DIRECTED | MANY_TO_MANY | BINARY (1.0) | Any | Any |
| CLASSIFIES | DIRECTED | MANY_TO_MANY | BINARY (1.0) | Category, Sector | Any |

### A.2 Category 2: Ownership Relationships

| Type | Direction | Cardinality | Strength basis | Source types | Target types |
|---|---|---|---|---|---|
| OWNED_BY | DIRECTED | MANY_TO_ONE | BINARY (1.0) | Instrument, Position | Portfolio, Account |
| MANAGES | DIRECTED | ONE_TO_MANY | BINARY (1.0) | Portfolio, Agent | Strategy, Position |
| ALLOCATES | DIRECTED | ONE_TO_MANY | COMPUTED | Portfolio | Instrument, Strategy |
| CONTROLS | DIRECTED | ONE_TO_MANY | BINARY (1.0) | RiskGuardian | Position, Strategy |

### A.3 Category 3: Financial Relationships

| Type | Direction | Cardinality | Strength basis | Source types | Target types |
|---|---|---|---|---|---|
| GENERATES | DIRECTED | ONE_TO_MANY | BINARY (1.0) | Strategy | Hypothesis |
| EXECUTES | DIRECTED | ONE_TO_MANY | BINARY (1.0) | OrderManager | Trade |
| FILLS | DIRECTED | ONE_TO_ONE | BINARY (1.0) | Order | Trade |
| CLOSES | DIRECTED | MANY_TO_ONE | BINARY (1.0) | Trade | Position |
| FUNDS | DIRECTED | ONE_TO_MANY | COMPUTED | Account | Trade |
| HEDGES | DIRECTED | MANY_TO_MANY | COMPUTED | Position | Position |
| SETTLES | DIRECTED | ONE_TO_ONE | BINARY (1.0) | Trade | Settlement |

### A.4 Category 4: Corporate Relationships

| Type | Direction | Cardinality | Strength basis | Source types | Target types |
|---|---|---|---|---|---|
| SUBSIDIARY_OF | DIRECTED | MANY_TO_ONE | BINARY (1.0) | Company | Company |
| ACQUIRES | DIRECTED | MANY_TO_MANY | BINARY (1.0) | Company | Company |
| COMPETES_WITH | UNDIRECTED | MANY_TO_MANY | COMPUTED | Company | Company |
| SUPPLIES_TO | DIRECTED | MANY_TO_MANY | COMPUTED | Company | Company |
| DEPENDS_ON | DIRECTED | MANY_TO_MANY | BINARY (1.0) | Company | Company |
| JOINT_VENTURE_WITH | UNDIRECTED | MANY_TO_MANY | BINARY (1.0) | Company | Company |
| PARTNERS_WITH | UNDIRECTED | MANY_TO_MANY | COMPUTED | Company | Company |

### A.5 Category 5: Market Relationships

| Type | Direction | Cardinality | Strength basis | Source types | Target types |
|---|---|---|---|---|---|
| LISTED_ON | DIRECTED | MANY_TO_MANY | BINARY (1.0) | Instrument | Exchange |
| TRADED_IN | DIRECTED | MANY_TO_MANY | BINARY (1.0) | Instrument | Sector |
| COMPONENT_OF | DIRECTED | MANY_TO_MANY | COMPUTED | Instrument | Index |
| LEADS | DIRECTED | MANY_TO_MANY | STATISTICAL | Index, Instrument | Index, Instrument |
| LAGS | DIRECTED | MANY_TO_MANY | STATISTICAL | Index, Instrument | Index, Instrument |
| CORRELATED_WITH | UNDIRECTED | MANY_TO_MANY | STATISTICAL | Any market entity | Any market entity |

### A.6 Category 6: Economic Relationships

| Type | Direction | Cardinality | Strength basis | Source types | Target types |
|---|---|---|---|---|---|
| INFLUENCES | DIRECTED | MANY_TO_MANY | COMPUTED | MacroIndicator, Index | Any |
| CAUSED_BY | DIRECTED | MANY_TO_MANY | STATISTICAL | Any | Any |
| HYPOTHETICALLY_CAUSED_BY | DIRECTED | MANY_TO_MANY | COMPUTED | Any | Any |
| SENSITIVE_TO | DIRECTED | MANY_TO_MANY | COMPUTED | Instrument, Strategy | MacroIndicator, Regime |
| AMPLIFIED_BY | DIRECTED | MANY_TO_MANY | COMPUTED | Volatility, Trend | MacroIndicator |
| DAMPENED_BY | DIRECTED | MANY_TO_MANY | COMPUTED | Volatility, Trend | MacroIndicator |

### A.7 Category 7: Knowledge Relationships

| Type | Direction | Cardinality | Strength basis | Source types | Target types |
|---|---|---|---|---|---|
| SUPPORTS | DIRECTED | MANY_TO_MANY | COMPUTED | Evidence, Observation | Hypothesis |
| CONTRADICTS | DIRECTED | MANY_TO_MANY | COMPUTED | Evidence, Observation | Hypothesis |
| VALIDATES | DIRECTED | MANY_TO_MANY | BINARY (1.0) | Observation | Hypothesis |
| REFUTES | DIRECTED | MANY_TO_MANY | COMPUTED | Observation | Hypothesis |
| REFINES | DIRECTED | MANY_TO_MANY | COMPUTED | Hypothesis | Hypothesis |
| DERIVED_FROM | DIRECTED | MANY_TO_MANY | COMPUTED | Hypothesis | Hypothesis |
| SUPERSEDES | DIRECTED | ONE_TO_ONE | BINARY (1.0) | Hypothesis | Hypothesis |

### A.8 Category 8: AI / Agent Relationships

| Type | Direction | Cardinality | Strength basis | Source types | Target types |
|---|---|---|---|---|---|
| TRAINED_ON | DIRECTED | MANY_TO_MANY | COMPUTED | Agent | Dataset |
| CALIBRATED_BY | DIRECTED | MANY_TO_MANY | COMPUTED | Agent | Dataset, Observation |
| INFORMS | DIRECTED | MANY_TO_MANY | COMPUTED | Agent | Agent |
| DELEGATES_TO | DIRECTED | ONE_TO_MANY | BINARY (1.0) | Orchestrator | Agent |
| VALIDATES_OUTPUT_OF | DIRECTED | MANY_TO_MANY | COMPUTED | Agent | Agent |
| DEBATED_BY | UNDIRECTED | MANY_TO_MANY | BINARY (1.0) | Hypothesis | Agent |

### A.9 Category 9: Risk Relationships

| Type | Direction | Cardinality | Strength basis | Source types | Target types |
|---|---|---|---|---|---|
| THREATENS | DIRECTED | MANY_TO_MANY | COMPUTED | RiskFactor | Position, Strategy |
| MITIGATED_BY | DIRECTED | MANY_TO_MANY | COMPUTED | RiskFactor | Hedge, Control |
| TRIGGERS | DIRECTED | MANY_TO_MANY | COMPUTED | RiskFactor | KillSwitch, Alert |
| CORRELATED_RISK | UNDIRECTED | MANY_TO_MANY | STATISTICAL | Position | Position |
| STRESS_TESTED_BY | DIRECTED | MANY_TO_MANY | BINARY (1.0) | Position, Portfolio | StressScenario |

### A.10 Category 10: Portfolio Relationships

| Type | Direction | Cardinality | Strength basis | Source types | Target types |
|---|---|---|---|---|---|
| WEIGHTED_IN | DIRECTED | MANY_TO_MANY | COMPUTED | Instrument | Portfolio |
| REBALANCED_BY | DIRECTED | MANY_TO_MANY | BINARY (1.0) | Portfolio | RebalancingEvent |
| BENCHMARKED_AGAINST | DIRECTED | MANY_TO_MANY | BINARY (1.0) | Portfolio | Index |
| CONTRIBUTES_ALPHA | DIRECTED | MANY_TO_MANY | COMPUTED | Strategy | Portfolio |
| CONTRIBUTES_BETA | DIRECTED | MANY_TO_MANY | COMPUTED | Strategy | Portfolio |
| DIVERSIFIES | UNDIRECTED | MANY_TO_MANY | COMPUTED | Position | Position |

### A.11 Category 11: Temporal Relationships

| Type | Direction | Cardinality | Strength basis | Source types | Target types |
|---|---|---|---|---|---|
| PRECEDES | DIRECTED | MANY_TO_MANY | BINARY (1.0) | Event, Trade | Event, Trade |
| FOLLOWS | DIRECTED | MANY_TO_MANY | BINARY (1.0) | Event, Trade | Event, Trade |
| CONCURRENT_WITH | UNDIRECTED | MANY_TO_MANY | COMPUTED | Event | Event |
| SCHEDULED_AT | DIRECTED | MANY_TO_ONE | BINARY (1.0) | Event | TimeSlot |
| RECURS_AS | DIRECTED | ONE_TO_MANY | BINARY (1.0) | Event | Event |

### A.12 Category 12: Event Relationships

| Type | Direction | Cardinality | Strength basis | Source types | Target types |
|---|---|---|---|---|---|
| RESPONDS_TO | DIRECTED | MANY_TO_MANY | COMPUTED | Strategy, Agent | Event |
| TRIGGERED_BY | DIRECTED | MANY_TO_MANY | COMPUTED | Trade, Alert | Event |
| CAUSED_EVENT | DIRECTED | MANY_TO_MANY | COMPUTED | Event | Event |
| NOTIFIES | DIRECTED | MANY_TO_MANY | BINARY (1.0) | Event | Agent |

### A.13 Category 13: Derived Relationships

| Type | Direction | Cardinality | Strength basis | Source types | Target types |
|---|---|---|---|---|---|
| SIMILAR_TO | UNDIRECTED | MANY_TO_MANY | COMPUTED | Strategy, Instrument | Strategy, Instrument |
| ANALOGOUS_TO | UNDIRECTED | MANY_TO_MANY | COMPUTED | Hypothesis | Hypothesis |
| OUTPERFORMS | DIRECTED | MANY_TO_MANY | COMPUTED | Strategy | Strategy |
| UNDERPERFORMS | DIRECTED | MANY_TO_MANY | COMPUTED | Strategy | Strategy |
| REGIME_MATCHED | DIRECTED | MANY_TO_MANY | COMPUTED | Strategy | MarketRegime |

### A.14 Category 14: Cross-Domain Relationships

| Type | Direction | Cardinality | Strength basis | Source types | Target types |
|---|---|---|---|---|---|
| MACRO_LINKED | DIRECTED | MANY_TO_MANY | COMPUTED | MacroEvent | Instrument |
| SECTOR_SPILL | DIRECTED | MANY_TO_MANY | COMPUTED | Sector | Sector |
| CROSS_ASSET_FLOW | DIRECTED | MANY_TO_MANY | COMPUTED | Asset class | Asset class |
| REGIME_DRIVEN | DIRECTED | MANY_TO_MANY | COMPUTED | MarketRegime | Strategy, Position |

### A.15 Category 15: Root / Meta Relationships

| Type | Direction | Cardinality | Strength basis | Source types | Target types |
|---|---|---|---|---|---|
| GOVERNED_BY | DIRECTED | MANY_TO_MANY | BINARY (1.0) | Any | GovernancePolicy |
| ARCHIVED_WITH | DIRECTED | MANY_TO_MANY | BINARY (1.0) | Any | ArchiveRecord |
| SUPERSEDED_BY | DIRECTED | ONE_TO_ONE | BINARY (1.0) | Any | Any |
| ASSOCIATED_WITH | UNDIRECTED | MANY_TO_MANY | COMPUTED | Any | Any |

---
## SUPPLEMENT B — COMPONENT INTERFACE REFERENCE

This supplement provides the key operational interface summary for each of the 17 Relationship Engine components. For full specifications see Part III.

| Component | Primary input | Primary output | Latency target | Failure mode |
|---|---|---|---|---|
| Registry | relationship_id / registration request | Relationship record / registration confirmation | < 1 ms (lookup); < 5 ms (write) | FAIL_FAST on duplicate; FAIL_SAFE on read |
| Catalog | type_name / category | Type definition / allowed types list | < 1 ms | Static read — never fails |
| Factory | relationship specification | Relationship record draft | < 5 ms | FAIL_FAST on invalid spec |
| Validator | relationship record | Validation result (PASS/FAIL + details) | < 10 ms | FAIL_FAST on type violation; FAIL_SAFE on contextual checks |
| Identity Manager | any identifier | Canonical relationship_id | < 2 ms | FAIL_FAST on unresolvable identifier |
| Lifecycle Manager | relationship_id + target_state | Transition confirmation | < 5 ms | FAIL_FAST on invalid transition |
| Version Manager | relationship_id | Version record / history | < 3 ms (latest); < 20 ms (full history) | FAIL_SAFE — return partial history |
| Metadata Manager | relationship_id + metadata update | Updated metadata record | < 5 ms | FAIL_FAST on invalid key |
| Index | relationship_id / query | Index entries / traversal results | < 1 ms (point lookup); < 5 ms (1-hop) | FAIL_SAFE — stale cache fallback |
| Cache | relationship_id | Cached relationship record | < 0.5 ms (L1); < 2 ms (L2) | FAIL_SAFE — miss falls through to persistence |
| Search Engine | query spec | Ranked result list | < 50 ms | FAIL_SAFE — return partial results |
| Audit Manager | relationship_id / event | Audit record | < 10 ms | NEVER_FAIL — audit writes are queued |
| Integrity Manager | scan scope | Integrity report | < 5 min (weekly scan) | FAIL_SAFE — partial results |
| Governance Manager | relationship_id / governance action | Governance result | < 10 ms | FAIL_FAST on policy violation |
| Reasoning Manager | context_spec | Reasoning result | < 500 ms | FAIL_SAFE — return null result, log |
| Discovery Manager | discovery config | Candidate relationships | < 30 min (full scan) | FAIL_SAFE — partial candidates |
| Evolution Manager | evolution trigger | Updated strength/confidence | < 50 ms | FAIL_SAFE — retain previous value |

---

### B.2 Key Operation Latency Targets

| Operation | Latency target | Notes |
|---|---|---|
| 1-hop neighbor query | < 5 ms | On adjacency index |
| 5-hop traversal | < 25 ms | BFS with early termination |
| Full-text search | < 50 ms | On search index |
| Causal chain reconstruction | < 200 ms | Up to 10 hops |
| Influence propagation | < 100 ms | On pre-warmed cache |
| Point-in-time graph | < 1 s | From temporal index |
| Full graph integrity scan | < 5 min | Weekly batch |
| Discovery scan | < 30 min | Nightly batch |

---

### B.3 Service Circuit Breaker Configuration

| Service | Failure threshold | Reset timeout | Fallback |
|---|---|---|---|
| Registration Service | 10 failures / 60 sec | 30 sec | Reject; queue for retry |
| Traversal Service | 5 failures / 10 sec | 15 sec | Return cached subgraph |
| Reasoning Service | 3 failures / 30 sec | 60 sec | Return null; log |
| Influence Service | 3 failures / 30 sec | 60 sec | Return null; log |
| Discovery Service | 5 failures / 60 sec | 5 min | Skip discovery cycle |
| Search Service | 5 failures / 30 sec | 30 sec | Return empty result set |

---

## SUPPLEMENT C — GRAPH TRAVERSAL PATTERNS

This supplement provides reference traversal patterns with ASCII diagrams illustrating how the Relationship Engine handles key traversal scenarios.

### C.1 Pattern 1: Financial Impact Chain

**Use case:** Determine the full downstream impact of a macroeconomic event on portfolio positions.

**Starting entity:** MacroIndicator (e.g., VIX)
**Traversal type:** Directed BFS — following INFLUENCES edges
**Depth:** Up to 5 hops
**Filter:** All INFLUENCES edges with effective_weight > 0.10

```
VIX (MacroIndicator)
  ──[INFLUENCES: 0.85]──► NIFTY50 (Index)
       ──[INFLUENCES: 0.75]──► TATASTEEL.NS (Instrument)
            ──[SENSITIVE_TO: 0.70]──► TrendStrategy (Strategy)
                 ──[GENERATES: 1.00]──► TataSteelHypothesis (Hypothesis)
```

**Result format:** Ordered path list with cumulative effective weight at each hop.

---

### C.2 Pattern 2: Causal Chain Reconstruction

**Use case:** Given an unexpected trade outcome, reconstruct the causal chain that led to it.

**Starting entity:** Trade
**Traversal type:** Reverse directed BFS — following CAUSED_BY edges backwards
**Depth:** Up to 8 hops
**Filter:** Only CAUSED_BY edges with confidence ≥ 0.85

```
TradeLoss (Trade) ◄──[CAUSED_BY: 0.92]── RegimeMismatch (Event)
  ◄──[CAUSED_BY: 0.88]── RegimeTransition (MacroEvent)
       ◄──[CAUSED_BY: 0.87]── FedRateChange (MacroEvent)
```

**Result:** Complete causal chain with confidence at each link and weakest-link confidence as summary.

---

### C.3 Pattern 3: Portfolio Similarity Search

**Use case:** Find all strategies that are similar to a given strategy for diversification analysis.

**Starting entity:** Strategy
**Traversal type:** SIMILAR_TO edges (undirected — traversed from both ends)
**Depth:** 1 hop only
**Filter:** SIMILAR_TO edges with strength > 0.70

```
TrendStrategy (Strategy)
  ──[SIMILAR_TO: 0.85]── MomentumStrategy (Strategy)
  ──[SIMILAR_TO: 0.78]── BreakoutStrategy (Strategy)
  ──[SIMILAR_TO: 0.72]── VWAPStrategy (Strategy)
```

**Result:** Similarity cluster — used to detect over-concentration in correlated strategies.

---

### C.4 Pattern 4: Risk Propagation Tree

**Use case:** Determine which positions are at risk if a given risk factor materialises.

**Starting entity:** RiskFactor (e.g., NIFTY_CORRECTION)
**Traversal type:** Directed BFS — following THREATENS edges
**Depth:** Up to 3 hops
**Filter:** THREATENS edges with effective_weight > 0.20

```
NIFTY_CORRECTION (RiskFactor)
  ──[THREATENS: 0.80]──► TATASTEEL_LONG (Position)
  ──[THREATENS: 0.75]──► RELIANCE_LONG (Position)
  ──[THREATENS: 0.65]──► BANKNIFTY_CALL (Position)
       ──[MITIGATED_BY: 0.90]──► BANKNIFTY_PUT_HEDGE (Hedge)
```

**Result:** Full threat tree with mitigation edges included.

---

### C.5 Pattern 5: Composition Tree

**Use case:** Determine the full composition of a portfolio — all contained strategies and instruments.

**Starting entity:** Portfolio
**Traversal type:** Directed DFS — following COMPOSED_OF and CONTAINS edges
**Depth:** Full depth (tree is acyclic by Rule RC-B-09)
**Filter:** Only COMPOSED_OF and CONTAINS edges (binary, strength 1.0)

```
MyPortfolio (Portfolio)
  ──[COMPOSED_OF]──► TrendStrategy (Strategy)
  │    ──[GENERATES]──► TrendHypothesis (Hypothesis)
  ──[COMPOSED_OF]──► MomentumStrategy (Strategy)
  ──[CONTAINS]──► TATASTEEL.NS (Instrument)
  ──[CONTAINS]──► RELIANCE.NS (Instrument)
```

**Result:** Full composition tree — used for NAV computation, risk aggregation, and reporting.

---

## SUPPLEMENT D — QUALITY SCORING REFERENCE

This supplement provides quality scoring reference tables including dimension weight overrides for specific relationship categories.

### D.1 Default vs Category-Override Weights

| Dimension | Default | Financial override | Risk override | Derived override |
|---|---|---|---|---|
| Strength | 0.15 | 0.20 | 0.15 | 0.10 |
| Confidence | 0.20 | 0.25 | 0.25 | 0.20 |
| Reliability | 0.12 | 0.15 | 0.12 | 0.15 |
| Stability | 0.08 | 0.05 | 0.10 | 0.12 |
| Persistence | 0.06 | 0.05 | 0.06 | 0.08 |
| Validity | 0.12 | 0.15 | 0.12 | 0.10 |
| Consistency | 0.08 | 0.05 | 0.10 | 0.08 |
| Traceability | 0.05 | 0.05 | 0.05 | 0.05 |
| Freshness | 0.08 | 0.05 | 0.05 | 0.12 |
| Importance | 0.03 | 0.00 | 0.00 | 0.00 |
| Criticality (advisory) | 0.03 | 0.00 | 0.00 | 0.00 |
| **Total** | **1.00** | **1.00** | **1.00** | **1.00** |

---

### D.2 Confidence Decay Rate Reference

| Relationship type | λ (per day) | Half-life |
|---|---|---|
| CORRELATED_WITH | 0.10 | 6.9 days |
| INFLUENCES | 0.03 | 23.1 days |
| SENSITIVE_TO | 0.03 | 23.1 days |
| CAUSED_BY | 0.01 | 69.3 days |
| SIMILAR_TO | 0.05 | 13.9 days |
| HEDGES | 0.30 | 2.3 days |
| COMPOSED_OF | 0.00 | Indefinite |
| GENERATES | 0.00 | Indefinite |

The confidence decay formula:

$$\text{confidence}(t) = \text{confidence}(t_0) \cdot e^{-\lambda \cdot (t - t_0)}$$

---

### D.3 EMA Smoothing Reference

| Relationship type | α (EMA weight) | Effective lookback |
|---|---|---|
| CORRELATED_WITH | 0.90 | ~10 periods |
| INFLUENCES | 0.85 | ~13 periods |
| SENSITIVE_TO | 0.85 | ~13 periods |
| CAUSED_BY | 0.70 | ~3 periods (slow-moving) |
| SIMILAR_TO | 0.80 | ~5 periods |
| OUTPERFORMS | 0.75 | ~4 periods |
| All other types | 0.85 | ~13 periods |

---

### D.4 RQS Scoring Worked Example

**Relationship:** TATASTEEL.NS CORRELATED_WITH NIFTY50 (using Financial override weights)

| Dimension | Score | Weight (Financial) | Weighted |
|---|---|---|---|
| Strength | 0.82 | 0.20 | 0.164 |
| Confidence | 0.88 | 0.25 | 0.220 |
| Reliability | 0.90 | 0.15 | 0.135 |
| Stability | 0.72 | 0.05 | 0.036 |
| Persistence | 0.95 | 0.05 | 0.048 |
| Validity | 1.00 | 0.15 | 0.150 |
| Consistency | 1.00 | 0.05 | 0.050 |
| Traceability | 0.85 | 0.05 | 0.043 |
| Freshness | 0.95 | 0.05 | 0.048 |
| **RQS** | | | **0.893** |

**Classification: EXCELLENT** — No action required.

---

## SUPPLEMENT E — GOVERNANCE DECISION RECORDS

Governance Decision Records (GDR) document significant architectural or policy decisions made during the design and evolution of the Relationship Engine.

### GDR-001: Causal Relationships Require Human Approval

**Date:** 2026-Q1  
**Decision:** CAUSED_BY relationships require explicit Human Principal approval before activation.  
**Rationale:** Causal claims have a materially higher downstream impact than correlational claims. A CAUSED_BY relationship appearing in the Reasoning Manager's context causes the agent to assert causation, not mere correlation. Incorrect causal assertions can drive repeated, systematic errors in strategy selection. The additional latency of human approval is acceptable given the high-impact nature of causal assertions.  
**Alternatives considered:** Automatic activation if confidence > 0.90 (rejected — confidence metric does not capture semantic correctness); automatic activation with Telegram notification only (rejected — notification is not approval).  
**Implications:** A discovery pipeline that surfaces strong causal candidates will need a human review queue. The Approval Service must support asynchronous approval with notification.

---

### GDR-002: Effective Weight = Strength × Confidence

**Date:** 2026-Q1  
**Decision:** The effective weight of an edge in graph traversal algorithms is defined as `strength × confidence`.  
**Rationale:** A relationship that is very strong but uncertain (strength 0.95, confidence 0.30) should not have the same traversal weight as a relationship that is somewhat strong and very certain (strength 0.60, confidence 0.95). The product formulation ensures that both dimensions contribute proportionally. Alternatives (additive, max, min) were evaluated. Additive overcounts uncertainty. Max ignores the weaker dimension. Min is too conservative.  
**Implications:** All traversal algorithms (Dijkstra, influence propagation, path scoring) must use effective_weight, not raw strength.

---

### GDR-003: Version Batching for High-Frequency Relationships

**Date:** 2026-Q1  
**Decision:** Strength and confidence updates smaller than 0.05 are batched and stored as a single version record per trading session (up to 30-day maximum batch window).  
**Rationale:** Correlations are recomputed daily. Without batching, a CORRELATED_WITH relationship with 365 days of history would accumulate 365 version records — most representing trivial fluctuations. This creates audit log bloat and performance degradation. The 0.05 threshold was determined to capture meaningful evolution while batching noise.  
**Implications:** The Version Manager needs a pending-updates buffer per relationship. Batches are committed at session close.

---

### GDR-004: Maximum Traversal Depth = 10 Hops

**Date:** 2026-Q1  
**Decision:** No traversal operation may exceed 10 hops from the starting node.  
**Rationale:** Practical influence analysis shows that effective weight at 10 hops (assuming average effective weight per hop of 0.6) is approximately 0.6^10 ≈ 0.006 — negligible. Beyond 10 hops, computational cost is high and analytical value is near zero. Traversal depth limits also protect against accidental runaway traversal in dense subgraphs.  
**Implications:** The Traversal Service must enforce the limit and return a `max_depth_reached` flag in results.

---

### GDR-005: Adjacency Index is Source of Truth for Live Traversal

**Date:** 2026-Q1  
**Decision:** All live graph traversal uses the in-memory adjacency index, not the persistence layer.  
**Rationale:** Persistence-layer traversal (graph queries via SQL or document store) is 100x–1000x slower than adjacency index traversal. The Traversal Service must meet a 5 ms latency target for 1-hop queries and 25 ms for 5-hop traversal. These targets are impossible without an in-memory index.  
**Implications:** The adjacency index must be kept synchronously consistent with the Registry. Any Registry write must immediately update the adjacency index before returning. Index rebuilds (on startup) must complete before the Relationship Engine is considered operational.

---

### GDR-006: Self-Referential Relationships Prohibited by Default

**Date:** 2026-Q1  
**Decision:** Self-referential relationships (source = target) are prohibited unless explicitly permitted in the Catalog.  
**Rationale:** Self-loops cause infinite loops in all recursive graph algorithms (DFS, BFS, influence propagation). The only valid domain use case for self-referential relationships would be a "recursive composition" (e.g., a ConglomerateStrategy composed of itself) which is not a valid modelling pattern in the IIOS domain.  
**Implications:** The Validator must check source_id ≠ target_id for all relationship types not explicitly marked `self_referential_allowed` in the Catalog.

---
## SUPPLEMENT F — RELATIONSHIP ANTI-PATTERN REFERENCE

This supplement documents the known anti-patterns in relationship modelling and management. Each anti-pattern is documented with a description, symptoms, root cause, and resolution.

---

### F.1 Anti-Pattern: The Phantom Relationship

**Description:** A relationship is created between two entities where one or both entities do not actually exist, or exist but in an incompatible lifecycle state (RETIRED, ARCHIVED).

**Symptoms:**
- Graph traversal returns relationship edges that lead to null entity records
- Influence propagation terminates unexpectedly mid-chain
- Integrity scan reports DANGLING_EDGE violations

**Root cause:** Relationship creation was not guarded by the mandatory entity existence and lifecycle state checks. Direct persistence insertion bypassed the Registration Service and Validator.

**Resolution:** All relationship creation must go through the Registration Service. The Registration Service enforces entity existence checks (Rule RC-B-02) and lifecycle state checks (Rule RC-B-03) before creating any relationship. Never insert relationship records directly into the persistence layer.

---

### F.2 Anti-Pattern: The Stale Correlation

**Description:** A CORRELATED_WITH relationship with a strong historical correlation is used in reasoning and risk management long after the correlation has broken down due to regime change or structural market shift.

**Symptoms:**
- CORRELATED_WITH relationship has a high strength (0.85) but low freshness score
- The relationship's last recompute date is more than 7 days ago
- Risk models are using outdated correlation assumptions

**Root cause:** The freshness schedule for CORRELATED_WITH relationships was not configured, or the Discovery Service's daily recompute cycle was skipped or failed without being detected.

**Resolution:** All CORRELATED_WITH relationships must have a freshness schedule (daily recompute per Table 7.10). Freshness monitoring must alert if a recompute cycle is missed. Stale correlations (freshness < 0.20) must be flagged as operationally unreliable (Rule RC-C-11).

---

### F.3 Anti-Pattern: The Causal Shortcut

**Description:** A CORRELATED_WITH relationship is promoted to CAUSED_BY based on observation count alone, without meeting the confidence threshold (0.85) or the Human Principal approval requirement.

**Symptoms:**
- CAUSED_BY relationship with confidence < 0.85 is in ACTIVE state
- No approval record exists for this relationship
- Reasoning Manager is using this relationship to make causal assertions

**Root cause:** The approval workflow was bypassed. A service directly created a CAUSED_BY relationship without going through the Approval Service or waiting for Human Principal confirmation.

**Resolution:** The Registration Service must enforce that CAUSED_BY relationships require approval before activation (Rule RC-F-03). The Lifecycle Manager must block CREATED → ACTIVE transition for CAUSED_BY relationships without an approval record (Rule RC-D-10).

---

### F.4 Anti-Pattern: The Identity Crisis

**Description:** Two relationship records exist that represent the same connection (same type, same source, same target) — a duplicate that has not been detected or resolved.

**Symptoms:**
- Graph traversal returns duplicate edges between the same entity pair
- Influence propagation counts the relationship twice (artificial strength amplification)
- Audit trail has two separate creation records for the same logical relationship

**Root cause:** Duplicate detection was not run at creation time. Race condition during concurrent creation requests created two records. Or: data migration from an external source introduced duplicates.

**Resolution:** The Registration Service must perform an idempotency check at creation time (Rule RC-A-07). The Integrity Manager must detect duplicates in its weekly scan. Duplicates must be resolved through the Merge workflow — never silently dropped (Rule RC-F-06).

---

### F.5 Anti-Pattern: The Infinite Composition Loop

**Description:** COMPOSED_OF relationships form a cycle — Entity A is composed of Entity B which is composed of Entity A — creating an infinite loop in composition tree traversal.

**Symptoms:**
- Composition tree traversal hangs or stack-overflows
- Portfolio NAV computation cannot complete
- Cycle detection scan reports a COMPOSITION_CYCLE violation

**Root cause:** A COMPOSED_OF relationship was created without checking if it would create a cycle in the composition tree. This is typically caused by direct persistence insertion or a validator that does not perform cycle detection.

**Resolution:** The Validator must perform a cycle detection check before creating any COMPOSED_OF relationship (Rule RC-B-09, Rule RC-B-10). Cycle detection is an O(V+E) DFS operation and must complete synchronously before relationship creation is confirmed.

---

### F.6 Anti-Pattern: The Confidence Mirage

**Description:** A relationship maintains a high confidence score (0.90+) not because of strong evidence, but because the confidence decay model is not active — the confidence has simply not decayed from its initial creation value.

**Symptoms:**
- High-confidence relationships that have never been re-evaluated
- last_recompute_date is the same as created_at
- Freshness score is low, but confidence score is high

**Root cause:** The Evolution Manager was not configured to monitor this relationship type. Or: the confidence decay model has a decay rate of λ = 0.0 for a type that should be decaying.

**Resolution:** Every non-binary, non-structural relationship must be registered with the Evolution Manager with an appropriate decay rate λ (Supplement D.2). The Governance Manager must detect relationships where confidence is high but freshness is low and raise a CONFIDENCE_STALENESS governance alert.

---

### F.7 Anti-Pattern: The Audit Gap

**Description:** A relationship has been through multiple lifecycle transitions or strength updates, but the audit log has missing or incomplete records — creating gaps in the accountability chain.

**Symptoms:**
- Version chain has missing version numbers (e.g., v1, v2, v4 — missing v3)
- Hash chain integrity check fails
- Audit trail shows lifecycle transitions with no corresponding audit event

**Root cause:** Direct persistence writes bypassed the Audit Manager. Or: an error during audit event persistence was swallowed without retry. Or: audit records were incorrectly pruned during retention cleanup.

**Resolution:** The Audit Manager must use a write-through queue that retries on failure (Rule RC-E-01 through RC-E-10). The hash chain integrity check (Rule RC-E-06) must run weekly and alert immediately on failure. Retention cleanup must preserve the full audit chain for the relationship's minimum retention period.

---

### F.8 Anti-Pattern: The Ghost Influence

**Description:** A relationship that has been deprecated or retired continues to contribute to influence propagation and reasoning because it was not removed from the adjacency index.

**Symptoms:**
- DEPRECATED or RETIRED relationship edges appear in traversal results
- Influence propagation includes relationships with confidence < 0.10
- Reasoning context includes relationships that should be excluded

**Root cause:** The adjacency index update that should have occurred on lifecycle transition was not executed. Or: the cache retained the old edge state and the index was not invalidated.

**Resolution:** The Lifecycle Manager must synchronously update the adjacency index on every lifecycle transition (Rule RC-H-02). Cache invalidation must be synchronous with lifecycle state changes (Rule RC-G-12). DEPRECATED relationships remain in the index but are flagged — RETIRED relationships must be removed.

---

### F.9 Anti-Pattern: The Governance Orphan

**Description:** A relationship exists with no owner, no governance policy, and no compliance schedule — effectively outside the governance framework.

**Symptoms:**
- Relationship record has owner_id = null
- Governance Manager does not have a policy record for this relationship type
- The monthly governance health report does not include this relationship

**Root cause:** The relationship was created by a component that was not authorised to own relationships of this type. Or: the relationship type was added to the Catalog without a corresponding governance policy.

**Resolution:** All relationship types must have a governance policy defined before the type can be used in production (Rule RC-F-07). The Registration Service must reject relationship creation if no governance policy exists for the type. Ownership assignment is mandatory (Rule RC-F-01).

---

### F.10 Anti-Pattern: The Transient Causation Claim

**Description:** A CAUSED_BY relationship is created based on a single observed co-occurrence and then used immediately in reasoning without the required evidence accumulation.

**Symptoms:**
- CAUSED_BY relationship has reliability = 0.10 (1 confirmed instance / 1 total)
- Relationship is ACTIVE and used in causal chain reconstruction
- Reasoning Manager's causal chains all trace back to this single-observation relationship

**Root cause:** The CAUSED_BY type was not correctly configured to require a minimum number of confirmed instances before activation. Or: the Human Principal approval was completed too quickly without reviewing the evidence quality.

**Resolution:** The Catalog definition for CAUSED_BY must require a minimum confirmed instance count (e.g., 10) before Human Principal approval can be granted. The approval workflow must display the reliability score and confirmed instance count as context for the approver's decision.

---

## SUPPLEMENT G — RELATIONSHIP GLOSSARY

| Term | Definition |
|---|---|
| Adjacency Index | In-memory graph data structure mapping entity IDs to their connected edges — the primary data structure for graph traversal operations. |
| Audit Chain | The complete, hash-linked sequence of audit events for a relationship from creation through the current state. |
| Backward Compatibility | The property of a change to a relationship type definition that does not break existing consumers or existing relationship records. |
| Binary Relationship | A relationship type where strength is always exactly 1.0 (the relationship either exists or it does not, with no partial strength). |
| Causal Chain | A directed sequence of CAUSED_BY relationships linking a cause entity to an effect entity through one or more intermediate causal steps. |
| Confidence | The system's certainty that a relationship is real and will continue to hold — a measure of epistemic certainty rather than connection magnitude. |
| Criticality | The operational impact if a relationship were incorrect, missing, or failed — a governance-level classification (CRITICAL, HIGH, MEDIUM, LOW). |
| Decay Rate (λ) | The exponential decay constant controlling how quickly a relationship's confidence decays in the absence of confirming evidence. |
| Discovery Candidate | A proposed relationship surfaced by automated analysis that has not yet been validated or approved — it does not have a relationship_id and does not appear in the graph. |
| Effective Weight | The edge weight used in weighted graph traversal algorithms — computed as strength × confidence. |
| EMA (α) | The Exponential Moving Average smoothing factor used to update relationship strength — higher α gives more weight to recent observations. |
| Entity Registry | The master registry of all entities in the IIOS — the Relationship Engine requires both source and target entities to be registered before a relationship can be created. |
| Graph Partition | A logical division of the relationship graph by category, type, or entity class — used to scope traversal operations and index segments. |
| Governance Decision Record (GDR) | A permanent record documenting a significant architectural or policy decision and its rationale. |
| Hyperedge | An edge connecting more than two nodes — explicitly prohibited in the IIOS relationship model. All relationships are binary (two endpoints). |
| Identity Manager | The Relationship Engine component responsible for resolving any valid identifier (UUID4, reference ID, alias) to a canonical relationship_id. |
| Influence Propagation | The graph algorithm that traces how a change at one node propagates through INFLUENCES edges to downstream nodes, attenuating at each hop by the effective weight. |
| Lifecycle State Machine | The defined set of lifecycle states and valid transitions for relationships — the Lifecycle Manager enforces this state machine. |
| Multi-edge | Multiple relationship edges of different types between the same entity pair — supported by the IIOS adjacency index. |
| Node Shadow | A lightweight proxy record for an entity maintained in the Relationship Engine's graph layer — contains the entity's centrality scores and relationship counts but not full entity attributes. |
| Provenance | The documented evidence that established a relationship — required for all non-binary relationship types. |
| Relationship Catalog | The authoritative registry of all permitted relationship types, their definitions, constraints, and governance policies. |
| Relationship Constitution | The supreme set of mandatory rules governing all relationships in the IIOS — 94 rules across 8 categories. |
| Relationship Quality Score (RQS) | The composite quality score computed from 11 weighted quality dimensions — the primary quality indicator for operational use decisions. |
| Relationship Readiness Checklist (RRC) | The 12-section checklist used to certify that a relationship is fully operational within the IIOS. |
| Reliability | The historical track record of a relationship — the proportion of tested instances where the relationship held. |
| Retirement | The terminal lifecycle state for a relationship — irreversible, permanently recorded, never reused. |
| Self-Referential Relationship | A relationship where source and target are the same entity — prohibited by default in the IIOS (Rule RC-B-06). |
| Stability | A quality dimension measuring the variability of a relationship's strength over time — computed as the inverse of the coefficient of variation. |
| Strength | The quantified magnitude of a relationship connection — a value in [0.0, 1.0] representing the degree of the connection. |
| Temporal Graph | The graph state at a specific historical point in time — reconstructable from the temporal index for any date within the retention period. |
| Traversal | The graph algorithm that follows relationship edges from a starting entity to discover connected entities — the primary graph operation. |
| Version Chain | The ordered sequence of version records for a relationship from creation to the current state — the complete evolution history. |

---
---

## DOCUMENT SUMMARY AND MASTER COMPLIANCE CHECKLIST

### Summary Metrics

| Metric | Value |
|---|---|
| Document title | RELATIONSHIP_ENGINE_ARCHITECTURE.md |
| Version | 1.0 |
| Status | FINAL |
| Total parts | 10 (I–X) |
| Total supplements | 7 (A–G) |
| Relationship categories | 15 |
| Relationship types catalogued | 94+ across all categories |
| Lifecycle stages defined | 12 |
| Engine components specified | 17 |
| Services specified | 15 |
| Constitutional rules | 94 (across 8 categories) |
| Readiness checklist items | 127 (across 12 sections) |
| Quality dimensions | 12 |
| Governance pillars | 12 |
| Graph algorithms specified | 7 |
| Anti-patterns documented | 10 |
| Glossary terms | 30 |
| Governance Decision Records | 6 |

---

### Master Compliance Checklist

The following checklist is used during Relationship Engine audits to confirm that the implementation satisfies all architectural requirements of this document.

| Category | Requirement | Status |
|---|---|---|
| Identity | UUID4 relationship_id assigned at creation | ☐ |
| Identity | Identity resolution returns canonical ID for all identifier types | ☐ |
| Connectivity | Entity existence checked before relationship creation | ☐ |
| Connectivity | Entity lifecycle state checked before relationship creation | ☐ |
| Connectivity | Cardinality constraints enforced at creation | ☐ |
| Connectivity | Self-referential prohibition enforced | ☐ |
| Connectivity | COMPOSED_OF and DEPENDS_ON cycle detection active | ☐ |
| Quality | Strength in [0.0, 1.0] at all times | ☐ |
| Quality | Confidence in [0.0, 1.0] at all times | ☐ |
| Quality | RQS computed and stored | ☐ |
| Quality | Confidence decay model active for non-structural types | ☐ |
| Quality | Freshness schedule defined for derived relationships | ☐ |
| Lifecycle | Lifecycle state machine enforced | ☐ |
| Lifecycle | DISCOVERY_CANDIDATE not assigned relationship_id | ☐ |
| Lifecycle | CREATED not in adjacency index | ☐ |
| Lifecycle | ACTIVE in adjacency index | ☐ |
| Lifecycle | ARCHIVED not in adjacency index | ☐ |
| Lifecycle | RETIRED transition is irreversible | ☐ |
| Lifecycle | Cascade archival runs synchronously | ☐ |
| Audit | RELATIONSHIP_CREATED event generated at creation | ☐ |
| Audit | Audit events hash-chained | ☐ |
| Audit | Audit records never deleted or modified | ☐ |
| Audit | Financial relationship audit retained for lifetime + 7 years | ☐ |
| Governance | Every relationship has an owner | ☐ |
| Governance | CAUSED_BY requires Human Principal approval | ☐ |
| Governance | Financial chain relationships require Human Principal approval | ☐ |
| Governance | Duplicate detection enforced at creation | ☐ |
| Graph | Adjacency index updated synchronously on lifecycle change | ☐ |
| Graph | Traversal depth limit of 10 hops enforced | ☐ |
| Graph | Effective weight = strength × confidence stored per edge | ☐ |
| Graph | Influence propagation stops at effective weight < 0.05 | ☐ |
| Services | All relationship creation through Registration Service only | ☐ |
| Services | Cache invalidation synchronous with writes | ☐ |
| Constitution | All 94 constitutional rules implemented | ☐ |
| Readiness | RRC evaluated before relationship declared operational | ☐ |

---

### Version History

| Version | Date | Change | Author |
|---|---|---|---|
| 1.0 | 2026-Q2 | Initial release | IIOS Architecture Board |

---

### Governing Documents

This document is governed by and must be read in conjunction with:

| Document | Role |
|---|---|
| DATABASE_PERSISTENCE_ARCHITECTURE.md | Storage contracts — all relationship persistence |
| KNOWLEDGE_ENGINE_ARCHITECTURE.md | Consumer architecture — Reasoning Manager and Knowledge Engine |
| ENTITY_ENGINE_ARCHITECTURE.md | Provider architecture — all entity records that relationships connect |
| ARCHITECTURE.md | System-level architecture — 17-layer IIOS hierarchy |

---

### Closing Statement

The Relationship Engine Architecture defined in this document is the authoritative design for all relationship management in the IIOS. Every implementation decision, every service interface, every index design, and every governance policy for relationships must conform to this document.

The Relationship Engine is the intelligence substrate of the IIOS: it transforms a registry of isolated entities into a connected, reasoned, governed knowledge graph. The quality of the relationships it manages is the quality of the system's intelligence. A Relationship Engine that admits phantom edges, stale correlations, causal shortcuts, and governance orphans is not a foundation for reliable financial decision-making — it is a sophisticated source of systematic error.

This document exists to prevent that outcome.

Every relationship in the IIOS deserves:
- An identity it can never lose
- A lifecycle that is always managed
- A quality score that is always honest
- An audit trail that is always complete
- A governance policy that is always enforced

This is the Relationship Constitution. It does not bend.

---

*RELATIONSHIP_ENGINE_ARCHITECTURE.md — Investment Intelligence Operating System (IIOS)*  
*Classification: INTERNAL — Architecture Board Confidential*  
*Next review: 2026-Q4*
